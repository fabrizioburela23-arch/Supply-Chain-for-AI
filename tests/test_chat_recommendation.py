"""Khipu SIEMPRE cierra una pregunta de inversión con «👉 Mi recomendación: …» (2026-11-18, Fabrizio: «la gente quiere
que Khipu le diga qué recomienda hacer»). Si la IA no la escribió, el modelo pequeño la agrega con su aviso."""
from core import ai
from core import khipu_chat as kc


def _out(ans, tools=('simulate_price',)):
    return {'answer': ans, 'answer_source': 'ai', 'tools_used': [{'name': t} for t in tools]}


def test_agrega_la_recomendacion_y_quita_el_no_recomiendo(monkeypatch):
    seen = {}

    def fake(system, prompt, max_tokens=1000, tier='fast', **kw):
        seen['model'] = kw.get('model')
        return '👉 **Mi recomendación: Esperar** — el reporte de febrero puede mover el precio.', 'claude-haiku-5-5'
    monkeypatch.setattr(ai, '_ai_complete', fake)
    ans = kc._ensure_recommendation('¿Nvidia ya tocó fondo? ¿Entro?', _out(
        'Probablemente no. Es una distribución de probabilidades, no un pronóstico ni una recomendación.'), 'es')
    assert ans.endswith('_Información, no asesoría personalizada._') and '👉 **Mi recomendación: Esperar**' in ans
    assert 'ni una recomendación' not in ans and seen['model'] == 'claude-haiku-5-5'


def test_no_toca_lo_que_no_es_inversion_ni_lo_que_ya_recomienda(monkeypatch):
    monkeypatch.setattr(ai, '_ai_complete', lambda *a, **k: (_ for _ in ()).throw(AssertionError('no debe llamar')))
    a = '¿Quiénes son los proveedores de TSMC? Son ASML y otros.'
    assert kc._ensure_recommendation('¿Quiénes son los proveedores de TSMC?', _out(a, ('get_supply_chain',)), 'es') == a
    b = 'Texto.\n\n👉 **Mi recomendación: Comprar poco a poco** — crece fuerte.'
    assert kc._ensure_recommendation('¿Compro AMD?', _out(b), 'es') == b
    assert kc._ensure_recommendation('¿Compro AMD?', dict(_out('x'), degraded='budget'), 'es') == 'x'


def test_si_falla_la_ia_queda_igual(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError('sin IA')
    monkeypatch.setattr(ai, '_ai_complete', boom)
    assert kc._ensure_recommendation('¿Debería invertir en Anthropic?', _out('Respuesta.', ()), 'es') == 'Respuesta.'
    monkeypatch.setattr(ai, '_ai_complete', lambda *a, **k: ('Algo sin acción válida', 'm'))
    assert kc._ensure_recommendation('¿Debería invertir en Anthropic?', _out('Respuesta.', ()), 'es') == 'Respuesta.'
