"""tests/test_mcp_contract.py — contrato común de las respuestas MCP (mcp_server/contract.py; BRECHAS L4-08):
detail (summary|standard|full) y max_chars en TODAS las herramientas, recorte ORDENADO con marcas, campos del contrato
y tamaños acotados (get_supply_chain de Nvidia a 2 saltos: antes 112k caracteres ×2). Sin red, sin base."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server import contract, protocol  # noqa: E402
from mcp_server import tools as T  # noqa: E402
from mcp_server.auth import Principal  # noqa: E402


@pytest.fixture
def ctx(monkeypatch):
    monkeypatch.setattr(T, '_live_profile', lambda sym: {'available': False, 'reason': 'offline'})
    monkeypatch.setattr(T._auth, 'db_available', lambda: False)
    return T.Ctx(principal=Principal(token_id='t', name='t', scopes=frozenset({'read'})))


def _call(ctx, name, args):
    r, _audit = protocol.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                                 'params': {'name': name, 'arguments': args}}, ctx)
    res = r['result']
    return res, res['content'][0]['text'], res['structuredContent']


def test_todas_las_herramientas_aceptan_detail_y_max_chars():
    for name, t in T.REGISTRY.items():
        props = t.input_schema['properties']
        assert props['detail']['enum'] == ['summary', 'standard', 'full'], name
        assert props['max_chars']['minimum'] == contract.MIN_MAX_CHARS, name
        assert t.input_schema['additionalProperties'] is False, name
    with pytest.raises(T.InvalidParams):
        T.validate(T.REGISTRY['get_company'].input_schema, {'id_or_ticker': 'x', 'detail': 'gigante'})
    with pytest.raises(T.InvalidParams):
        T.validate(T.REGISTRY['get_company'].input_schema, {'id_or_ticker': 'x', 'max_chars': 10})


def test_el_catalogo_del_chat_no_crece():
    from core import khipu_chat as kc
    for name, sig, _desc in kc.tool_catalog():
        assert 'detail' not in sig and 'max_chars' not in sig, name


def test_campos_del_contrato_y_texto_igual_a_estructurado(ctx):
    res, txt, sc = _call(ctx, 'search_companies', {'query': 'NVDA', 'limit': 3})
    assert json.loads(txt) == sc and ', ' not in txt[:40]                    # JSON compacto
    for k in ('detail', 'as_of', 'known_at', 'sources', 'method', 'truncated', 'tokens_estimate', 'max_chars'):
        assert k in sc, k
    assert sc['detail'] == 'standard' and sc['truncated'] is False and sc['results'][0]['id'] == 'Nvidia'
    assert sc['tokens_estimate'] == pytest.approx(len(txt) / 4, rel=0.05)
    assert sc['sources'] == [sc['source']]


def test_get_company_summary_chico(ctx):
    _res, txt, sc = _call(ctx, 'get_company', {'id_or_ticker': 'Nvidia', 'include_live': False, 'detail': 'summary'})
    assert len(txt) <= 1500                                                   # BRECHAS: brief ≤ 1.500
    assert sc['id'] == 'Nvidia' and sc['network_risk_score']['value'] is not None
    assert len(sc['top_suppliers']) == 5 and len(sc['top_customers']) == 5 and sc['counts']['customers'] > 5
    _res, full_txt, full = _call(ctx, 'get_company', {'id_or_ticker': 'Nvidia', 'include_live': False})
    assert len(full_txt) <= contract.DEFAULT_MAX_CHARS and full['top_suppliers'] and 'catalog' in full


def test_get_supply_chain_profundidad_2_acotada_y_por_relevancia(ctx):
    _r, txt, sc = _call(ctx, 'get_supply_chain', {'id': 'Nvidia', 'depth': 2})
    assert len(txt) <= contract.DEFAULT_MAX_CHARS                             # antes 112.354
    assert sc['counts']['edges'] == 282 and sc['truncated'] is True and sc['tail']['omitted_edges'] > 0
    assert any(e['hop'] == 2 for e in sc['edges'])
    assert sum(1 for e in sc['edges'] if e['target'] == 'Nvidia') >= 5
    assert sum(1 for e in sc['edges'] if e['source'] == 'Nvidia') >= 5
    ids = {n['id'] for n in sc['nodes']}
    assert all(e['source'] in ids and e['target'] in ids for e in sc['edges'])
    _r, txt_s, s2 = _call(ctx, 'get_supply_chain', {'id': 'Nvidia', 'depth': 2, 'detail': 'summary'})
    assert len(txt_s) <= 8000 and s2['edges']                                 # BRECHAS: depth 2 brief ≤ 8k
    _r, txt_f, f = _call(ctx, 'get_supply_chain', {'id': 'Nvidia', 'depth': 2, 'detail': 'full'})
    assert len(f['edges']) == 282 and not f.get('truncation')                 # full = todo (cabe en el tope)
    _r, txt_m, m = _call(ctx, 'get_supply_chain', {'id': 'Nvidia', 'depth': 2, 'detail': 'full', 'max_chars': 20000})
    assert len(txt_m) <= 20000 and m['truncated'] is True
    assert any(t['path'] == 'edges' and t['total'] == 282 for t in m['truncation'])
    assert m['edges'] == f['edges'][:len(m['edges'])]                         # recorte ORDENADO: se conserva la cabeza


def test_fit_conserva_la_cabeza_y_marca_el_recorte():
    payload = {'items': [{'i': i, 'txt': 'x' * 50} for i in range(400)], 'note': 'y' * 3000}
    out, trunc = contract.fit(payload, 4000)
    assert len(json.dumps(out, separators=(',', ':'))) <= 4000
    assert [x['i'] for x in out['items']] == list(range(len(out['items'])))
    assert any(t['path'] == 'items' and t['total'] == 400 for t in trunc)
    assert payload['items'][399]['i'] == 399                                  # no muta el original


def test_fit_cola_para_series_de_tiempo():
    payload = {'points': [{'date': f'2020-01-{i:04d}', 'close': i} for i in range(500)]}
    out, trunc = contract.fit(payload, 3000, tail_paths=('points',))
    assert out['points'][-1]['close'] == 499 and out['points'][0]['close'] > 0
    assert trunc[0]['kept_end'] == 'newest' and trunc[0]['total'] == 500


@pytest.mark.parametrize('name,args', [
    ('get_company', {'id_or_ticker': 'Nvidia', 'include_live': False}),
    ('get_company', {'id_or_ticker': 'Nvidia', 'include_live': False, 'detail': 'summary'}),
    ('get_supply_chain', {'id': 'Nvidia', 'depth': 2}),
    ('get_supply_chain', {'id': 'Nvidia', 'depth': 1, 'detail': 'summary'}),
])
@pytest.mark.parametrize('mc', [1000, 1500, 3000])
def test_max_chars_se_cumple_o_se_dice(ctx, name, args, mc):
    """Revisión: get_company devolvía 4.400 caracteres con max_chars 1.000-3.000 y a veces truncated=False. Ahora el
    cuerpo entra en max_chars (sacando claves de poco valor) o, si lo esencial ya pesa más, lo DICE (over_budget)."""
    _res, txt, sc = _call(ctx, name, dict(args, max_chars=mc))
    assert sc['max_chars'] == mc
    if len(txt) > mc:
        assert sc['over_budget'] is True and sc['truncated'] is True
    else:
        assert 'over_budget' not in sc
    assert sc['id' if name == 'get_company' else 'root'] == 'Nvidia' and sc['sources']
    if name == 'get_company' and mc >= 1500:
        assert len(txt) <= mc


def test_el_chat_sigue_recibiendo_el_resultado_crudo(ctx):
    r = T.call('get_supply_chain', {'id': 'Nvidia', 'depth': 2}, ctx)        # sin shape: lo compacta el chat
    assert len(r['edges']) == 282 and 'detail' not in r
    r2 = T.call('get_supply_chain', {'id': 'Nvidia', 'depth': 2, 'detail': 'summary'}, ctx)
    assert len(r2['edges']) == 282                                            # el chat ignora detail/max_chars
