"""El comité de cartera DENTRO del chat (2026-10-05: "/cartera dime si debería reducir…" solo abría
una pantalla y no respondía). POST /api/committee/portfolio/ask mide la cartera y el cerebro contesta
con ese análisis como contexto verificado."""
import json
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
NODE = shutil.which('node')

ANALYSIS = {'ok': True, 'health': {'score': 58, 'tone': 'warn', 'verdict': 'Algo concentrada'},
            'profile': {'label': 'Moderado', 'target_vol': 20, 'max_position': 20, 'max_sector': 40},
            'kpis': {'value_usd': 10000, 'cash_usd': 0, 'vol_ann_pct': 31, 'max_drawdown_pct': -22, 'var95_1d_usd': 290},
            'coverage': {'requested': 3, 'analyzed': 2, 'researched': 1, 'not_researched': []},
            'positions': [{'label': 'Nvidia', 'symbol': 'NVDA', 'weight_pct': 70, 'risk_contrib_pct': 80, 'vol_ann_pct': 45,
                           'value_usd': 7000, 'sector': 'chips', 'conviction': 30},
                          {'label': 'AMD', 'symbol': 'AMD', 'weight_pct': 30, 'risk_contrib_pct': 20, 'vol_ann_pct': 50,
                           'value_usd': 3000, 'sector': 'chips', 'conviction': None}],
            'actions': [{'id': 'A1', 'kind': 'reduce', 'label': 'Nvidia', 'from_pct': 70, 'to_pct': 20, 'delta_usd': -5000,
                         'priority': 1, 'why_es': 'pesa demasiado', 'why_en': 'too heavy'}],
            'sectors': [{'label': 'Chips', 'weight_pct': 100, 'n': 2}], 'correlated_pairs': [],
            'excluded': [{'symbol': 'OpenAI', 'reason': 'sin ticker cotizado'}], 'source': 'test', 'as_of': '2026-10-01'}


def test_endpoint_mide_la_cartera_y_responde_la_pregunta(monkeypatch):
    import server
    from core import khipu_chat as kc
    from core import portfolio_advisor as pa
    seen = {}
    monkeypatch.setattr(pa, 'analyze', lambda positions, **k: dict(ANALYSIS))

    def fake_chat(message, history=None, lang='es', context=None, app=None, **k):
        seen['message'], seen['ctx'] = message, context
        return {'answer': 'Sí: reduce Nvidia, pesa 70 %.', 'ai': True, 'actions': []}
    monkeypatch.setattr(kc, 'run_chat', fake_chat)
    c = server.app.test_client()
    d = c.post('/api/committee/portfolio/ask', json={'question': '¿debería reducir alguna posición?', 'source_label': 'Mi tesis',
                                                     'positions': [{'symbol': 'NVDA', 'shares': 10}], 'save': False}).get_json()
    assert d['ok'] and d['answer'].startswith('Sí')
    assert d['agent']['seat'] == 'portfolio' and d['agent']['label'] == 'Mi tesis'
    assert d['portfolio']['score'] == 58 and d['portfolio']['actions'][0]['id'] == 'A1'
    assert any(a['type'] == 'open_pf_committee' for a in d['actions'])
    notes = seen['ctx']['portfolio_notes']
    assert seen['message'] == '¿debería reducir alguna posición?'
    assert 'Nvidia (NVDA): peso 70' in notes and 'Acción sugerida A1' in notes and 'No analizada: OpenAI' in notes
    # sin pregunta → pide el análisis general
    c.post('/api/committee/portfolio/ask', json={'positions': [{'symbol': 'NVDA', 'shares': 1}], 'save': False})
    assert 'Analiza mi cartera' in seen['message']


JS = r"""
global.window = { LANG: 'es', localStorage: { getItem: () => null, setItem: () => {} } };
global.localStorage = window.localStorage;
require(process.argv[1] + '/engine/khipu_chat.js');
const K = window.KhipuChat, deps = { resolve: () => null };
const out = {};
for (const t of ['/cartera dime si debería reducir mi posición en alguna empresa', '/cartera', '@cartera ¿cuánto riesgo tengo?',
                 'que el comité analice mi cartera', '/comite mi cartera', '/portfolio should I trim anything?']) {
  const r = K.classify(t, deps); out[t] = { kind: r.kind, agent: r.agent, q: r.question };
}
process.stdout.write(JSON.stringify(out));
"""


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_chat_enruta_cartera_al_agente_con_la_pregunta():
    r = subprocess.run([NODE, '-e', JS, ROOT], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    o = json.loads(r.stdout)
    for t, v in o.items():
        assert v['kind'] == 'agentask' and v['agent'] == 'portfolio', t
    assert o['/cartera dime si debería reducir mi posición en alguna empresa']['q'] == 'dime si debería reducir mi posición en alguna empresa'
    assert o['/cartera']['q'] == '' and o['@cartera ¿cuánto riesgo tengo?']['q'] == '¿cuánto riesgo tengo?'
