"""Gráficos nativos de simulate_price / screen_stocks (core/genui) + 📄 Informe de cualquier respuesta (2026-11-06)."""
import datetime
import json
import os
import random

from core import genui, price_sim
from core.genui import layout
from core.genui import validate as V

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _sim():
    random.seed(1)
    d, p, prices = datetime.date(2024, 11, 5), 150.0, {}
    while len(prices) < 400:
        d += datetime.timedelta(days=1)
        if d.weekday() < 5:
            p *= 1 + random.gauss(0, 0.03)
            prices[d.isoformat()] = p
    last = datetime.date.fromisoformat(max(prices))
    past = [(datetime.date(2025, 2, 26), 'amc'), (datetime.date(2025, 5, 28), 'amc'), (datetime.date(2025, 8, 27), 'amc')]
    out = price_sim.simulate('NVDA', prices, earnings=(past, (last + datetime.timedelta(days=12), 'amc'), 'finnhub'),
                             fan_days=63, n_paths=3000)
    f = out['fan']
    out['fan'] = f[::3] + ([f[-1]] if (len(f) - 1) % 3 else [])
    out.update(id='nvidia', currency='USD', as_of='2026-11-06T03:00:00Z', source='Khipus price simulation')
    return out


def test_intencion_simulacion():
    for q in ('¿Nvidia ya tocó fondo?', '¿va a seguir cayendo AMD?', 'hasta dónde puede caer TSM', 'has NVDA bottomed?'):
        assert layout.intent_of(q) == 'sim', q


def test_simulacion_dibuja_cifras_y_abanico():
    env, _ = genui.build_ui('¿NVDA ya tocó fondo?', [('simulate_price', None, True, _sim())],
                            [{'id': 'nvidia', 'label': 'Nvidia'}], None, 'es', {'answer': 'Todavía no.\n\nMás.', 'mode': 'pro'})
    pub = genui.public(env)
    assert V.errors(pub) == []
    types = [b['type'] for b in pub['blocks']]
    assert types.index('metric.tiles') < types.index('chart.line')           # cifras arriba, abanico después
    fan = next(b for b in pub['blocks'] if b['type'] == 'chart.line')
    assert len(fan['data']['series']) == 3 and fan['data']['series'][0]['name']['es'] == 'Mediana'
    assert 'chart.bar' in types or 'table' in types                         # niveles o tabla como secundario
    assert not [d for d in env.get('dropped') or [] if d['reason'] != 'over_budget']   # nada inválido ni sin dueño
    # modo simple: solo lo principal
    env2, _ = genui.build_ui('¿NVDA ya tocó fondo?', [('simulate_price', None, True, _sim())],
                             [{'id': 'nvidia', 'label': 'Nvidia'}], None, 'es', {'answer': 'x', 'mode': 'simple'})
    assert [b['type'] for b in genui.public(env2)['blocks'] if b['type'] not in ('text', 'actions', 'sources', 'callout')] == \
        ['metric.tiles', 'chart.line']


def test_filtro_de_acciones_es_tabla():
    res = {'by': 'peg', 'items': [{'id': 'nvidia', 'label': 'Nvidia', 'symbol': 'NVDA', 'pe_forward': 24.1,
                                   'eps_growth_next_year_pct': 40.2, 'peg': 0.6, 'upside_to_target_pct': 30.5,
                                   'from_52w_high_pct': -25.4},
                                  {'id': 'amd', 'label': 'AMD', 'symbol': 'AMD', 'pe_forward': 30.0,
                                   'eps_growth_next_year_pct': 35.0, 'peg': 0.86, 'upside_to_target_pct': None,
                                   'from_52w_high_pct': -12.0}],
           'source': 'Yahoo Finance (live fundamentals, Khipus cache)', 'as_of': '2026-11-06T03:00:00Z'}
    env, _ = genui.build_ui('acciones baratas', [('screen_stocks', None, True, res)], [], None, 'es',
                            {'answer': 'x', 'mode': 'pro'})
    pub = genui.public(env)
    assert V.errors(pub) == []
    t = next(b for b in pub['blocks'] if b['type'] == 'table')
    assert len(t['data']['rows']) == 2 and t['data']['rows'][1]['upside'] is None


def test_informe_conectado():
    js = open(os.path.join(ROOT, 'engine', 'report.js'), encoding='utf-8').read()
    chat = open(os.path.join(ROOT, 'engine', 'khipu_chat.js'), encoding='utf-8').read()
    sw = open(os.path.join(ROOT, 'sw.js'), encoding='utf-8').read()
    app = open(os.path.join(ROOT, 'app.html'), encoding='utf-8').read()
    assert 'W.KhipuReport = { open: open, html: html, button: button }' in js and "Informe PDF', 'PDF report'" in js
    assert 'W.KhipuReport.button(el, d, gui, question)' in chat
    assert "'/engine/report.js'" in sw
    assert app.index('engine/khipu_chat.js') < app.index('engine/report.js')
    # el papel no inventa nada: sin fetch ni IA, y quita los botones de la copia
    assert 'fetch(' not in js and 'aiComplete' not in js and 'button' in js
