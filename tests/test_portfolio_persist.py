"""Carteras que "desaparecían" y análisis del comité que no quedaba registrado (2026-10-05).

· engine/pfcommittee.js listaba solo carteras CON posiciones → una cartera nueva (vacía)
  no aparecía en Comité → 💼 Mi cartera.
· engine/sync.js, cuando ganaba la versión del servidor, pisaba las carteras locales
  recién creadas que aún no habían subido.
· POST /api/committee/portfolio no guardaba nada: ahora queda como reporte
  kind='committee' por dueño (X-Khipu-Owner) y se lista con ?kind=committee.
"""
import json
import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = shutil.which('node')
needs_db = pytest.mark.skipif(not os.getenv('DATABASE_URL'), reason='requiere DATABASE_URL')

JS = r"""
const store = {};
global.Storage = function () {};
Storage.prototype.getItem = function (k) { return k in store ? store[k] : null; };
Storage.prototype.setItem = function (k, v) { store[k] = String(v); };
Storage.prototype.removeItem = function (k) { delete store[k]; };
global.localStorage = new Storage();
global.window = { LANG: 'es', localStorage: localStorage, NODE_BY_ID: {} };
global.document = { addEventListener: () => {}, getElementById: () => null, hidden: false };
global.fetch = () => new Promise(() => {});
global.setInterval = () => 0;
require(process.argv[1] + '/engine/sync.js');
require(process.argv[1] + '/engine/pfcommittee.js');
const srvTs = '2026-10-05T12:00:00.000Z', cut = Date.parse(srvTs);
localStorage.setItem('kh_portfolios', JSON.stringify([
  { id: 'old', name: 'Vieja (borrada en otro equipo)', createdAt: cut - 86400000, positions: [] },
  { id: 'n1', name: 'Nueva 1', createdAt: cut + 1000, positions: [] },
  { id: 'n2', name: 'Nueva 2', createdAt: cut + 2000, positions: [{ nodeId: 'Nvidia', shares: 1, avgPrice: 1 }] }]));
const m = window.KhipuSync._merge([{ id: 'srv', name: 'Del servidor', createdAt: cut - 5000, positions: [] }], srvTs);
window.KhipuPortfolios = { _list: () => JSON.parse(localStorage.getItem('kh_portfolios')) };
const src = window.KhipuPortfolioCommittee._sources().map(s => s.label);
process.stdout.write(JSON.stringify({ ids: m.value.map(p => p.id), kept: m.kept, src }));
"""


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_carteras_nuevas_no_se_pierden_y_las_vacias_se_ven_en_el_comite():
    r = subprocess.run([NODE, '-e', JS, ROOT], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    o = json.loads(r.stdout)
    assert o['ids'] == ['srv', 'n1', 'n2'] and o['kept'] == 2     # nuevas se conservan; la borrada no revive
    assert any('Nueva 1' in s and 'vacía' in s for s in o['src'])    # la vacía aparece (antes se ocultaba)
    assert any('Nueva 2' in s for s in o['src'])


@needs_db
def test_analisis_del_comite_de_cartera_queda_registrado(monkeypatch):
    from ontology.db import init_schema
    init_schema(retries=1)
    import server
    from core import portfolio_advisor as pa
    monkeypatch.setattr(pa, 'analyze', lambda positions, **k: {'ok': True, 'health': {'score': 71, 'verdict': 'Bien', 'tone': 'good'},
                                                                'kpis': {'value_usd': 1000}, 'positions': [], 'actions': []})
    monkeypatch.setattr(pa, 'explain', lambda out, lang='es': {'text': 'ok', 'ai': False})
    server.app.config['TESTING'] = True
    c = server.app.test_client()
    H = {'X-Khipu-Owner': 'c' * 24}
    body = {'positions': [{'symbol': 'NVDA', 'shares': 1}], 'profile': {'risk': 'moderado'}, 'source_label': 'Mi tesis'}
    d = c.post('/api/committee/portfolio', json=body, headers=H).get_json()
    assert d['ok'] and d.get('saved_id')
    lst = c.get('/api/portfolio-report/list?kind=committee', headers=H).get_json()['reports']
    assert lst[0]['id'] == d['saved_id'] and 'Mi tesis' in lst[0]['title'] and lst[0]['summary'].startswith('71/100')
    assert all(x['kind'] != 'committee' for x in c.get('/api/portfolio-report/list', headers=H).get_json()['reports'])
    one = c.get(f"/api/portfolio-report/{d['saved_id']}", headers=H).get_json()
    assert one['health']['score'] == 71 and one['kind'] == 'committee'
    # sin llave del navegador: el análisis sale igual, solo no se guarda
    d2 = c.post('/api/committee/portfolio', json=body).get_json()
    assert d2['ok'] and not d2.get('saved_id')


def _risk_all(positions, horizon=10, max_positions=30):
    ps = positions[:max_positions]
    return {'ok': True, 'portfolio_value_usd': 100.0 * len(ps), 'vol_ann_pct': 20.0, 'max_drawdown_pct': -10.0,
            'var95': {'hist_1d_pct': 1.0, 'hist_1d_usd': 1.0}, 'as_of': '2026-10-01', 'source': 'test',
            'positions': [{'symbol': p['symbol'], 'shares': 1, 'price': 100, 'value_usd': 100.0, 'weight_pct': 100 / len(ps),
                           'vol_ann_pct': 20.0, 'risk_contrib_pct': 100 / len(ps)} for p in ps],
            'correlation': {}, 'excluded': []}


def test_comite_analiza_todas_las_posiciones_y_dice_cuales_no():
    """'No analizó todas mis posiciones': antes había un tope oculto de 30 y lo demás se descartaba sin aviso."""
    from core import portfolio_advisor as pa
    pos = [{'symbol': f'T{i:02d}', 'label': f'Empresa {i}', 'shares': 1} for i in range(40)] + \
          [{'id': 'OpenAI', 'label': 'OpenAI', 'shares': 1}]          # privada: sin ticker
    a = pa.analyze(pos, risk_fn=_risk_all, board_fn=lambda: ({}, []))
    assert a['ok'] and a['kpis']['n_positions'] == 40
    assert a['coverage']['requested'] == 41 and a['coverage']['analyzed'] == 40 and a['coverage']['researched'] == 0
    assert any(x['symbol'] == 'OpenAI' and 'privada' in x['reason'] for x in a['excluded'])
    big = [{'symbol': f'T{i:02d}', 'shares': 1} for i in range(pa.MAX_POSITIONS + 5)]
    b = pa.analyze(big, risk_fn=_risk_all, board_fn=lambda: ({}, []))
    assert any(x['symbol'] == '+5' for x in b['excluded'])                # lo que pasa del tope se AVISA
