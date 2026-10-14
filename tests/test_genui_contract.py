"""tests/test_genui_contract.py — el sobre `ui` en POST /api/khipu/chat (docs/CHAT_UI_GENERATIVA.md §4.1, §5.6, §8,
§11 F1 paso 13). Sin red: la IA es un guion falso y las herramientas leen el snapshot local.

  · GENUI=off (por defecto) o sin context.genui → la respuesta es IDÉNTICA a la de hoy, campo a campo;
  · GENUI=shadow → se arma y se mide, NUNCA se envía;
  · GENUI=on + context.genui = 1 → solo se AÑADE `ui` (válido, kblocks/1); el resto no cambia;
  · las entradas internas (`_genui`, `_inputs`) nunca salen; un fallo del armado no rompe el chat;
  · get_history y run_scenario están en el catálogo del chat (F1) y alimentan línea y cascada;
  · presupuestos: ≤ 25 ms p95 por sobre, ≤ 48 KB; 0 cifras sin procedencia.
"""
import json
import os
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import ai as core_ai  # noqa: E402
from core import genui  # noqa: E402
from core import khipu_chat as kc  # noqa: E402
from core.genui import validate as V  # noqa: E402

VOLATILE = ('elapsed_ms', 'as_of', 'req_id', 'ms', 'checked_at', 'known_at')   # relojes: cambian de una corrida a otra


class FakeAI:
    def __init__(self, script):
        self.script = list(script)

    def __call__(self, system, prompt, max_tokens=1000, tier='fast', model=None, verify_numbers=True, **kw):
        item = self.script.pop(0) if self.script else {'final': {'answer': 'Listo.', 'actions': []}}
        return (item if isinstance(item, str) else json.dumps(item)), 'fake:model'


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    from mcp_server import tools as mt
    monkeypatch.setattr(mt, '_live_profile', lambda sym: {'available': False, 'reason': 'test (offline)'})
    monkeypatch.setattr(mt._auth, 'db_available', lambda: False)
    monkeypatch.setattr(core_ai, '_ai_configured', lambda: True)
    genui.reset_stats()


SCRIPT = [
    {'tool': 'run_scenario', 'args': {'shocks': [{'id': 'TSMC'}]}, 'why': 'choque'},
    {'final': {'answer': '**TSMC** fabrica los chips de la mayoría [F1].\n\nSi cae, el golpe llega lejos [F2].',
               'actions': [{'type': 'open_xray', 'arg': 'TSMC'}, {'type': 'broker', 'arg': None}]}},
]


def _ask(monkeypatch, context, genui_env='off', script=SCRIPT, msg='¿Qué pasa si cae TSMC?'):
    monkeypatch.setenv('GENUI', genui_env)
    monkeypatch.setattr(core_ai, '_ai_complete', FakeAI(script))
    return kc.run_chat(msg, [], 'es', dict(context))


def _strip(out):
    """La respuesta sin los relojes (horas y milisegundos), en cualquier nivel."""
    if isinstance(out, dict):
        return {k: _strip(v) for k, v in out.items() if k not in VOLATILE}
    if isinstance(out, list):
        return [_strip(v) for v in out]
    return out


def test_off_y_sin_bandera_identico_campo_a_campo(monkeypatch):
    base = _ask(monkeypatch, {})
    for env, ctx in (('off', {'genui': 1}), ('on', {}), ('shadow', {'genui': 1}), ('shadow', {})):
        out = _ask(monkeypatch, ctx, env)
        assert 'ui' not in out and '_genui' not in out, env
        assert _strip(out) == _strip(base), (env, ctx)
    assert set(base) >= {'answer', 'actions', 'tools_used', 'sources', 'entities', 'agents_used', 'cards', 'facts'}
    assert [t['name'] for t in base['tools_used']] == ['get_company', 'run_scenario']


def test_on_solo_anade_ui(monkeypatch):
    base = _ask(monkeypatch, {})
    out = _ask(monkeypatch, {'genui': 1}, 'on')
    ui = out.pop('ui')
    assert _strip(out) == _strip(base)                      # todo lo demás, igual
    assert V.errors(ui) == [] and ui['v'] == 'kblocks/1' and ui['layout'] == 'auto' and ui['impl'] == genui.IMPL
    assert '_inputs' not in ui and not any(k.startswith('_') for k in ui)
    types = [b['type'] for b in ui['blocks']]
    assert types[0] == 'text' and types[-1] == 'sources' and 'impact.cascade' in types
    casc = next(b for b in ui['blocks'] if b['type'] == 'impact.cascade')
    p = casc['prov']
    assert (p['kind'], p['name'], p['call'], p['fact']) == ('tool', 'run_scenario', 1, 'F2')
    assert p['generation'] == casc['data']['generation'] and casc['sources'] == ['F2']
    assert out['tools_used'][casc['prov']['call']]['name'] == 'run_scenario'
    # el texto de los bloques ES la respuesta (la voz y el guardián siguen leyendo `answer`)
    md = '\n\n'.join(b['data']['md'] for b in ui['blocks'] if b['type'] == 'text')
    assert md == out['answer']
    # nada de dinero: la acción broker del modelo NO llega a los botones
    acts = [a for b in ui['blocks'] if b['type'] == 'actions' for a in b['data']['items']]
    assert acts and all(a['kind'] in ('open_xray', 'open_dossier', 'open_research', 'open_committee', 'open_map',
                                      'open_window', 'open_world', 'prefill_chat') for a in acts)
    assert 'broker' not in json.dumps(ui)
    st = genui.stats()
    assert st['sent'] == 1 and st['built'] >= 1 and st['unprovenanced_blocks'] == 0


def test_shadow_mide_sin_enviar(monkeypatch):
    out = _ask(monkeypatch, {'genui': 1}, 'shadow')
    assert 'ui' not in out
    st = genui.stats()
    assert st['mode'] == 'shadow' and st['built'] == 1 and st['sent'] == 0 and st['ms_p95'] is not None


def test_fallo_del_armado_no_rompe_el_chat(monkeypatch):
    base = _ask(monkeypatch, {})

    def boom(_inputs):
        raise RuntimeError('x')
    monkeypatch.setattr(genui, 'build_core', boom)
    out = _ask(monkeypatch, {'genui': 1}, 'on')
    assert 'ui' not in out and '_genui' not in out and _strip(out) == _strip(base)
    assert genui.stats()['errors'] == 1


def test_sin_ia_tambien_lleva_bloques(monkeypatch):
    """Sin IA (crédito, caída): respuesta de respaldo + orden automático con la ficha que ya se consultó (§5.6)."""
    monkeypatch.setattr(core_ai, '_ai_configured', lambda: False)
    monkeypatch.setenv('GENUI', 'on')
    out = kc.run_chat('Nvidia', [], 'es', {'genui': 1})
    assert out['answer_source'] == 'fallback'
    types = [b['type'] for b in out['ui']['blocks']]
    assert 'company.card' in types and 'metric.tiles' in types
    tiles = next(b for b in out['ui']['blocks'] if b['type'] == 'metric.tiles')
    price = tiles['data']['items'][0]['value']
    assert price['v'] is None and price['missing_reason']['es']     # sin precio en vivo: «—», nunca un 0


def test_validate_request_bandera_y_tipos():
    r = kc.validate_request({'message': 'hola', 'context': {'genui': 1, 'genui_types': ['text', 'chart.line',
                                                                                        '<b>', 'x' * 40, 5]}})
    assert r['context']['genui'] == 1 and r['context']['genui_types'] == ['text', 'chart.line']
    r2 = kc.validate_request({'message': 'hola', 'context': {}})
    assert 'genui' not in r2['context'] and 'genui_types' not in r2['context']
    r3 = kc.validate_request({'message': 'hola', 'context': {'genui': 0}})
    assert 'genui' not in r3['context']


def test_catalogo_del_chat_abre_get_history_y_run_scenario():
    assert {'get_history', 'run_scenario'} <= set(kc.MCP_READ_TOOLS)
    names = kc.tool_names()
    assert 'get_history' in names and 'run_scenario' in names
    for nope in ('get_subgraph', 'get_exposure', 'calculate_correlation', 'find_similar_entities', 'preview_order',
                 'submit_order'):
        assert nope not in names, nope                       # F5 las abre de a una; dinero nunca
    sysmsg = kc.build_system('es')
    assert 'get_history(id_or_ticker, range)' in sysmsg and 'run_scenario(shocks=[{"id":"X"}])' in sysmsg


def test_historia_larga_la_ia_ve_lo_nuevo_y_el_grafico_todo():
    pts = [{'date': f'2024-{1 + i // 28:02d}-{1 + i % 28:02d}', 'close': 100.0 + i} for i in range(300)]
    res = {'symbol': 'NVDA', 'id': 'Nvidia', 'range': '1y', 'points': pts, 'source': 'prices_eod', 'as_of': '2024-11-20',
           'currency': 'USD', 'adjusted': True, 'change_pct': 299.0}
    txt = kc._fmt_result(res)
    assert len(txt) <= kc.MAX_TOOL_RESULT_CHARS + 20 and '"close":399.0' in txt and 'truncat' in txt
    note = kc._note_history(res, {}, {})
    assert note and 'NVDA' in note[0] and '+299,0 %' in note[0]


def _all_fixture_calls():
    import glob
    calls, facts = [], []
    for i, p in enumerate(sorted(glob.glob(os.path.join(ROOT, 'tests', 'fixtures', 'genui', 'tools', '*.json')))):
        with open(p, encoding='utf-8') as fh:
            d = json.load(fh)
        calls.append((d['tool'], d.get('args'), True, d['result']))
        facts.append(f'F{i + 1}')
    return calls, facts


@pytest.mark.parametrize('mode', ['simple', 'pro'])
def test_presupuesto_25ms_p95_y_48kb(mode):
    calls, facts = _all_fixture_calls()
    ents = [{'id': 'Nvidia', 'label': 'Nvidia'}, {'id': 'TSMC', 'label': 'TSMC'}]
    questions = ('¿Qué pasa si cae TSMC?', 'Compara Nvidia y AMD', '¿Cómo le fue a Nvidia en un año?',
                 'proveedores de Nvidia', 'noticias de Nvidia', '¿qué dice el comité?', 'VaR de mi cartera', 'Nvidia')
    ms = []
    for k in range(4):
        for q in questions:
            sub = calls[k:] + calls[:k]                     # distintas combinaciones y órdenes de llamadas
            t0 = time.perf_counter()
            env, _ = genui.build_ui(q, sub, ents, None, 'es' if k % 2 == 0 else 'en',
                                    {'answer': 'Respuesta de prueba.\n\nSegundo párrafo.', 'mode': mode,
                                     'fact_of': facts[k:] + facts[:k]})
            ms.append((time.perf_counter() - t0) * 1000)
            pub = genui.public(env)
            assert V.errors(pub) == []
            assert len(json.dumps(pub, ensure_ascii=False, separators=(',', ':')).encode()) <= genui.MAX_BYTES
            vis = [b for b in pub['blocks'] if b['type'] not in ('text', 'actions', 'sources')
                   and not (b['type'] == 'callout' and b['data']['variant'] == 'disclaimer')]
            assert len(vis) <= (4 if mode == 'pro' else 2)
    ms.sort()
    p95 = ms[int(0.95 * (len(ms) - 1))]
    assert p95 <= 25.0, f'p95 {p95:.1f} ms'
    assert genui.stats()['unprovenanced_blocks'] == 0


def test_sobre_grande_se_recorta_a_48kb():
    import datetime
    calls = []
    for k, sym in enumerate(('NVDA', 'AMD', 'INTC', 'TSM')):
        d0 = datetime.date(2020, 1, 1)
        pts = [{'date': (d0 + datetime.timedelta(days=i)).isoformat(), 'close': 50.0 + k + (i % 50) * 0.37}
               for i in range(1500)]
        calls.append(('get_history', None, True, {'symbol': sym, 'id': sym, 'range': '5y', 'points': pts,
                                                  'source': 'prices_eod', 'as_of': pts[-1]['date'], 'currency': 'USD'}))
    env, _ = genui.build_ui('compara precios', calls, [], None, 'es', {'answer': 'x', 'mode': 'pro'})
    pub = genui.public(env)
    assert V.errors(pub) == []
    assert len(json.dumps(pub, ensure_ascii=False, separators=(',', ':')).encode()) <= genui.MAX_BYTES


def test_endpoint_con_bandera(monkeypatch):
    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(kc.khipu_chat_bp)
    monkeypatch.setenv('GENUI', 'on')
    monkeypatch.setattr(core_ai, '_ai_complete', FakeAI(SCRIPT))
    c = app.test_client()
    r = c.post('/api/khipu/chat', json={'message': '¿Qué pasa si cae TSMC?', 'lang': 'es', 'context': {'genui': 1}})
    assert r.status_code == 200
    d = r.get_json()
    assert d['ui']['v'] == 'kblocks/1' and V.errors(d['ui']) == []
    monkeypatch.setattr(core_ai, '_ai_complete', FakeAI(SCRIPT))
    r2 = c.post('/api/khipu/chat', json={'message': '¿Qué pasa si cae TSMC?', 'lang': 'es'})
    assert 'ui' not in r2.get_json()
