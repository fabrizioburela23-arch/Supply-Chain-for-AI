"""F5 — interfaz ADAPTATIVA (2026-11-20): la IA elige QUÉ bloques y en QUÉ orden (Plan del esquema kblocks/1); las
cifras siguen saliendo del servidor y lo que no casa se ignora (orden automático de respaldo)."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import genui  # noqa: E402
from core.genui import validate as V  # noqa: E402
from test_genui_sim_report import _sim  # noqa: E402


def _build(plan, mode='pro'):
    env, _ = genui.build_ui('¿NVDA ya tocó fondo?', [('simulate_price', None, True, _sim())],
                            [{'id': 'nvidia', 'label': 'Nvidia'}], plan, 'es',
                            {'answer': 'Todavía no.\n\nMás.', 'mode': mode, 'fact_of': ['F1']})
    pub = genui.public(env)
    assert V.errors(pub) == []
    return env, [b['type'] for b in pub['blocks'] if b['type'] not in ('text', 'actions', 'sources', 'callout')]


def test_sin_plan_queda_el_orden_automatico():
    env, vis = _build(None)
    assert env['layout'] == 'auto' and vis[:2] == ['metric.tiles', 'chart.line']


def test_la_ia_elige_que_y_en_que_orden():
    env, vis = _build([{'block': 'table', 'from': 'F1'}, {'block': 'chart.bar', 'from': 'F1'},
                       {'block': 'metric.tiles', 'from': 'F1'}])
    assert env['layout'] == 'plan' and vis == ['table', 'chart.bar', 'metric.tiles']
    env, vis = _build([{'block': 'table', 'from': 'F1'}, {'block': 'chart.bar', 'from': 'F1'},
                       {'block': 'metric.tiles', 'from': 'F1'}], mode='simple')
    assert vis == ['table', 'chart.bar']                    # modo simple: máximo 2 visuales


def test_plan_invalido_cae_al_automatico():
    for bad in ([{'block': 'html', 'from': 'F1'}], [{'block': 'table', 'from': 'F9'}],
                [{'block': 'table', 'from': '<script>'}], 'cualquier cosa', [{'text': 'hola'}]):
        env, vis = _build(bad)
        assert env['layout'] == 'auto' and vis[:2] == ['metric.tiles', 'chart.line'], bad


def test_clean_plan():
    assert genui.clean_plan([{'block': 'chart.line', 'from': 'F1,F2', 'opts': {'x': 1}}, {'block': 'nope', 'from': 'F1'}]) \
        == [{'block': 'chart.line', 'facts': ['F1', 'F2']}]
    assert genui.clean_plan(None) is None and genui.clean_plan([]) is None


def test_el_chat_pasa_el_layout_de_la_ia():
    from core import khipu_chat as kc
    kind, f = kc.parse_step('{"final":{"answer":"Hola","layout":[{"block":"table","from":"F1"}]}}')
    assert kind == 'final' and f['layout'][0]['block'] == 'table'
    assert '"layout"' in kc.build_system('es', 'simple') and 'INTERFAZ ADAPTATIVA' in kc.build_system('es', 'simple')
