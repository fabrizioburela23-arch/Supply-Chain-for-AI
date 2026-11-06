"""Examen de oro del chat (scripts/eval_chat.py) + cifras derivadas de get_company (2026-11-06)."""
import importlib.util
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _ev():
    spec = importlib.util.spec_from_file_location('eval_chat', os.path.join(ROOT, 'scripts', 'eval_chat.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_casos_bien_formados():
    d = json.load(open(os.path.join(ROOT, 'data', 'eval', 'preguntas_oro.json'), encoding='utf-8'))
    ids = [c['id'] for c in d['casos']]
    assert len(ids) == len(set(ids)) >= 15
    from core.khipu_chat import tool_names
    from mcp_server.tools import REGISTRY
    known = set(tool_names()) | set(REGISTRY) | {'web_search', 'read_url'}   # solo existen con clave de IA web
    for c in d['casos']:
        assert c['q'].strip() and c['tools']
        for g in c['tools']:
            assert set(g) <= known, (c['id'], set(g) - known)


def test_grade_aprueba_y_reprueba():
    ev = _ev()
    case = {'id': 'x', 'tools': [['simulate_price']]}
    good = {'answer': 'a' * 200, 'answer_source': 'ai', 'tools_used': [{'name': 'simulate_price'}]}
    assert ev.grade(case, good, 10)['ok']
    r = ev.grade(case, {'answer': 'No pude leer la página, reintenta luego. ' + 'b' * 150,
                        'tools_used': [{'name': 'get_company'}]}, 90, max_s=60)
    assert not r['ok'] and len(r['fallas']) == 3      # herramienta, se rindió, lenta
    r = ev.grade(case, {**good, 'answer': good['answer'] + ' 61,77 USD (⚠ cifra no verificada)'}, 5)
    assert any('no verificada' in f for f in r['fallas'])
    assert not ev.grade(case, {'error': 'HTTP 500'}, 1)['ok']
    r = ev.grade(case, {**good, 'answer': 'palabra ' * 300}, 5)
    assert any('muy larga' in f for f in r['fallas'])


def test_get_company_trae_cifras_derivadas():
    from mcp_server.tools import _with_derived
    p = _with_derived({'available': True, 'price': 181.6, 'week52_high': 243.37, 'week52_low': 164.27,
                       'target_mean': 250.0})
    d = p['derived']
    assert d['from_52w_high_pct'] == -25.4 and d['below_52w_high_amount'] == 61.77
    assert d['above_52w_low_pct'] == 10.5 and d['upside_to_target_pct'] == 37.7
    assert 'derived' not in _with_derived({'available': True, 'price': None, 'week52_high': 10})
