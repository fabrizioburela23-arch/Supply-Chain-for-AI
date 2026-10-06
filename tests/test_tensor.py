"""Ontología nivel 2 (matrix/tensor.py, 2026-10-06): el grafo como tensores con métricas útiles para invertir
y auto-conexión de empresas nuevas. Sin base de datos."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from matrix import engine as E  # noqa: E402
from matrix import tensor as T  # noqa: E402


def _snap():
    n = lambda i, cat, c='EEUU': {'id': i, 'label': i, 'cat': cat, 'sector': 'x', 'country': c}  # noqa: E731
    L = lambda s, t, ty='supply', w=3: {'source': s, 'target': t, 'w': w, 'type': ty, 'conf': 1}  # noqa: E731
    return {'nodes': [n('A', 'fab', 'Taiwan'), n('B', 'fab', 'Corea'), n('C', 'chip'), n('D', 'cloud'),
                      n('P1', 'chip'), n('P2', 'chip'), n('Z', 'misc')],
            'links': [L('A', 'C'), L('B', 'C'), L('C', 'D'), L('A', 'P1'), L('P1', 'D'), L('A', 'P2'),
                      L('P2', 'D'), L('Z', 'C', 'partner')]}


def test_psi_es_el_mismo_kernel_de_shocks_que_propagate():
    m = T.Model(_snap(), caps_live={'D': 100.0, 'C': 10.0})
    for s in m.ids:
        imp, _ = E.propagate(m.A, m.idx, m.ids, [s], damping=T.DAMPING, max_hops=T.MAX_HOPS, threshold=T.THRESHOLD)
        for k, v in imp.items():
            if k != s:
                assert abs(m.psi[m.idx[k], m.idx[s]] * 100 - v) < 0.02, (s, k)


def test_metricas_estructurales_a_mano():
    m = T.Model(_snap(), caps_live={'D': 100.0, 'C': 10.0})
    c = T.structure('C', m)
    assert c['supplier_concentration']['n_suppliers'] == 2 and c['supplier_concentration']['hhi'] == 0.5
    assert {x['country'] for x in c['supplier_countries']} == {'Taiwan', 'Corea'}
    # C arrastra a D (su único... no: D tiene 3 proveedores) → impacto 0.6/3 = 20 % de 100 B = 20 B
    assert c['downstream']['cap_at_risk_usd_b'] == 20.0 and c['downstream']['top'][0]['id'] == 'D'
    d = T.structure('D', m)
    src = {x['id']: x for x in d['upstream_risk_sources']}
    assert 'A' in src and src['A']['direct'] is False          # riesgo INDIRECTO (vía C, P1, P2)
    assert 'Z' not in src                                       # un socio no transmite daño de suministro
    assert T.ranking(m, 'cap_at_risk', 1)[0]['id'] == 'A'       # A es la más sistémica


def test_empresa_nueva_recibe_proveedores_y_clientes_probables():
    m = T.Model(_snap())
    r = T.suggest_links(new={'label': 'P3', 'cat': 'chip', 'country': 'EEUU'}, m=m, n=3)
    assert r['review_required'] is True
    assert r['suppliers'][0]['id'] == 'A' and r['customers'][0]['id'] == 'D'
    assert r['suppliers'][0]['target'] is None and r['customers'][0]['source'] is None  # nueva: aún sin id
    e = T.suggest_links('P1', m=m)                              # existente: no repite lo que ya tiene
    assert not any(x['id'] == 'D' for x in e['customers'])


def test_calidad_medida_con_vinculos_reales_ocultos_supera_la_linea_base():
    r = T.evaluate(seed=7)
    assert r['cases'] >= 50
    assert r['hit_rate'] >= 1.5 * r['baseline_popularity'], r


def test_ficha_real_de_nvidia():
    m = T.model(force=True)
    s = T.structure('Nvidia', m)
    assert s['supplier_concentration']['n_suppliers'] > 10
    assert abs(sum(x['share_pct'] for x in s['supplier_countries']) - 100) < 40   # top-6 países
    assert s['upstream_risk_sources'][0]['id'] == 'TSMC'
    assert len(s['peers']) == 5 and all(p['id'] != 'Nvidia' for p in s['peers'])


def test_api_tensor():
    from flask import Flask
    from matrix.tensor_api import tensor_bp
    app = Flask(__name__)
    app.register_blueprint(tensor_bp)
    c = app.test_client()
    r = c.get('/api/tensor/node/Nvidia')
    assert r.status_code == 200 and r.get_json()['downstream']['n_companies'] > 0
    assert c.get('/api/tensor/node/NoExisteXYZ').status_code == 404
    assert c.post('/api/tensor/suggest', json={}).status_code == 400
    r = c.post('/api/tensor/suggest', json={'node': {'label': 'Nueva HBM', 'cat': 'memory', 'country': 'Corea'}})
    assert r.status_code == 200 and r.get_json()['review_required'] is True and r.get_json()['suppliers']
    assert c.get('/api/tensor/rank?by=nada').status_code == 400
    assert c.get('/api/tensor/rank?by=concentration&limit=3').get_json()['items'][0]['value'] <= 1


def test_mcp_get_company_trae_la_estructura_compacta():
    from mcp_server import tools as M
    from mcp_server.auth import Principal
    ctx = M.Ctx(principal=Principal(token_id='x', name='t', scopes=frozenset({'read'})))
    st = M.call('get_company', {'id_or_ticker': 'Nvidia', 'include_live': False}, ctx)['structure']
    assert st['systemic_rank'] >= 1 and st['risk_sources'][0].startswith('TSMC') and len(st['peers']) == 3


def test_las_caps_en_vivo_se_piden_aunque_nadie_haya_abierto_la_app(monkeypatch):
    # tras un reinicio, sin pedir el refresco el modelo usaba solo valuaciones de privadas (~20 % de cobertura)
    from core import live_caps
    seen = {}

    def fake(start=True):
        seen['start'] = start
        return {'caps': {'Nvidia': {'mcap_b': 4500}}, 'as_of': 'x'}
    monkeypatch.setattr(live_caps, 'get_caps', fake)
    caps, as_of = T._caps_live()
    assert seen['start'] is True and caps == {'Nvidia': 4500.0} and as_of == 'x'
