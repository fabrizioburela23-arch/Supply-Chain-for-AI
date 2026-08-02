"""tests/test_investigador.py — Investigador Autónomo (Track C).

Los tests críticos son DB-free (corren siempre en CI): las regresiones de
seguridad (SAFE_AUTO), la verificación de citas server-side y el gateo del
interruptor INVESTIGADOR_AUTO — la decisión de Fabrizio (2026-08-02: solo
investiga cuando se le pide) queda blindada contra activaciones accidentales.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Regresión de seguridad: lo que JAMÁS debe auto-aprobarse ────────────────
def test_safe_auto_never_includes_money_or_theses():
    from ontology.agents import SAFE_AUTO
    assert 'CrearTesis' not in SAFE_AUTO, 'CrearTesis NUNCA debe auto-aprobarse'
    assert 'AjustarPosicion' not in SAFE_AUTO, 'AjustarPosicion (dinero) NUNCA debe auto-aprobarse'


def test_investigador_registered_in_agents():
    from ontology.agents import AGENTS
    names = [a.name for a in AGENTS]
    assert 'investigador_autonomo' in names
    assert len(names) == len(set(names)), 'nombres de agente duplicados'


# ── Capa 2: verificación de citas server-side (no confía en el LLM) ─────────
def test_verificar_citas_degrades_uncited_data():
    from ontology.agents import InvestigadorAutonomo
    fuentes = [{'content': 'TSMC reported record Q2 revenue of NT$673 billion, up 40% year over year.'}]
    data = {'datos_clave': [
        {'dato': 'ingresos Q2', 'valor': 'NT$673B', 'fuente_idx': 0,
         'cita_textual': 'TSMC reported record Q2 revenue of NT$673 billion'},
        {'dato': 'inventado', 'valor': '$999B', 'fuente_idx': 0,
         'cita_textual': 'revenue reached nine hundred ninety nine billion dollars'},
        {'dato': 'sin fuente', 'valor': '42%', 'fuente_idx': 7,
         'cita_textual': 'margin was forty two percent exactly this quarter'},
    ]}
    out = InvestigadorAutonomo._verificar_citas(data, fuentes)
    assert out['datos_clave'][0]['valor'] == 'NT$673B'          # cita real → sobrevive
    assert out['datos_clave'][1]['valor'] == 'N/D (no verificado)'  # cita falsa → degradada
    assert out['datos_clave'][2]['valor'] == 'N/D (no verificado)'  # índice inválido → degradada
    assert out['datos_clave'][1]['fuente_idx'] is None


def test_score_confidence_is_deterministic_and_bounded():
    from ontology.agents import InvestigadorAutonomo
    f = InvestigadorAutonomo._score_confidence
    assert f(0, False, 0.9) == 0.0            # sin fuentes → cero, diga lo que diga la IA
    assert f(1, False, 0.9) == 0.3            # 1 fuente no primaria → tope bajo
    assert f(3, True, 0.95) <= 0.9            # nunca por encima de 0.9
    assert f(2, False, 0.2) == 0.2            # la IA puede BAJAR la confianza, nunca subirla


# ── El interruptor de Fabrizio: off por defecto, on solo explícito ──────────
def test_observe_gated_off_by_default(monkeypatch):
    import core.config as cfg
    monkeypatch.setattr(cfg, 'INVESTIGADOR_AUTO', 'off')
    from ontology.agents import InvestigadorAutonomo
    # con el interruptor en off, observe() devuelve [] SIN tocar la sesión
    # (le pasamos un objeto que explota si se usa — no debe usarse)
    class Boom:
        def scalars(self, *a, **k):
            raise AssertionError('observe() consultó la BD con INVESTIGADOR_AUTO=off')
    assert InvestigadorAutonomo().observe(Boom()) == []


def test_websearch_unavailable_returns_none(monkeypatch):
    import core.websearch as ws
    monkeypatch.setattr(ws, 'TAVILY_KEY', '')
    assert ws._web_search_available() is False
    assert ws.web_search('cualquier cosa') == []
    from ontology.agents import InvestigadorAutonomo
    # _investigar corta ANTES de tocar la sesión si no hay búsqueda web
    assert InvestigadorAutonomo()._investigar(None, tema_libre='x') is None


def test_crear_tesis_input_backward_compatible():
    """El flujo humano existente (sin fuentes) sigue validando igual."""
    from ontology.actions import CrearTesisInput
    old = CrearTesisInput(company_id='TSMC', stance='watch', confidence=0.5, rationale='test')
    assert old.fuentes == [] and old.autor_tipo == 'humano' and old.datos_no_verificados == []
    new = CrearTesisInput(company_id='TSMC', stance='long', confidence=0.7, rationale='test',
                          autor_tipo='agente',
                          fuentes=[{'url': 'https://x.com/a', 'cita_textual': 'algo textual'}])
    assert new.fuentes[0].url == 'https://x.com/a'
