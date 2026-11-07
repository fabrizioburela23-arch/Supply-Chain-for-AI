"""core/model_router.py — ROUTER DE MODELOS del chat (2026-11-07, pedido de Fabrizio: «request → router → modelo
pequeño / mediano / frontera, y que ese router sea Jev»).

    choose(plan, message, context) → {'lane', 'by', 'step_model', 'final_model', 'label_es', 'label_en'}

Carriles:
  · local     — un dato guardado: responde sin IA (ya existía: Jev local_fact → _local_answer)
  · small     — consulta de 1-2 datos (precio, noticias, proveedores…): todo con el modelo PEQUEÑO (Haiku 5.5)
  · mid       — lo normal (escenarios, simulación, comparar dos): el modelo del nivel rápido configurado
  · frontier  — análisis de verdad (tesis, plan, varias empresas, «a fondo»): las herramientas se eligen con el
                modelo del nivel rápido y la RESPUESTA FINAL la escribe el modelo FRONTERA (Opus 5.5)

Quién decide: JEV (core/decide.chat_plan, TypeSafe) cuando contesta a tiempo y con confianza; si no, REGLAS
deterministas e instantáneas (sin IA, sin costo) — el router nunca deja la pregunta sin carril. Nunca toca dinero:
una orden sigue su camino de siempre (brokerage.service con PIN). AI_ROUTER=off apaga el router (todo como antes).
Modelos: AI_MODEL_SMALL (claude-haiku-5-5) y AI_MODEL_FRONTIER (claude-opus-5-5); el medio = AI_MODEL_FAST.
"""
import os
import re

LANE_LABEL = {
    'local': ('⚡ datos guardados', '⚡ stored data'),
    'small': ('🟢 modelo pequeño', '🟢 small model'),
    'mid': ('🟡 modelo mediano', '🟡 mid-size model'),
    'frontier': ('🔴 modelo frontera', '🔴 frontier model'),
}

# análisis que merece el modelo frontera (ES/EN)
_DEEP_RX = re.compile(
    r'a fondo|en profundidad|an[aá]lisis (completo|profundo|detallado)|tesis|thesis|estrategia|strategy|'
    r'plan de (inversi[oó]n|cartera)|arma(me)? una cartera|build (me )?a portfolio|due diligence|'
    r'(deber[ií]a|conviene|vale la pena) (invertir|comprar|entrar)|should i (invest|buy)|'
    r'pros? y contras?|pros and cons|por qu[eé] .{0,60} y qu[eé]|in depth|deep dive|informe completo|full report', re.I)
# consulta corta de un dato o una lista
_LOOKUP_RX = re.compile(
    r'precio|cotiza|cu[aá]nto (vale|est[aá]|cuesta)|capitalizaci|empleados|cu[aá]ndo reporta|noticias|news|'
    r'proveedores|clientes|suppliers|customers|qui[eé]n (es|fabrica)|qu[eé] es\b|what is\b|price|market cap|'
    r'se movieron|movers|hola|hello|gracias|thanks', re.I)
_COMPARE_RX = re.compile(r'compar|\bvs\.?\b|versus|frente a', re.I)


def enabled():
    return (os.getenv('AI_ROUTER') or 'on').strip().lower() not in ('off', '0', 'false', 'no')


def models():
    from core.config import AI_MODEL_FAST
    return {'small': (os.getenv('AI_MODEL_SMALL') or '').strip() or 'claude-haiku-5-5',
            'mid': AI_MODEL_FAST,
            'frontier': (os.getenv('AI_MODEL_FRONTIER') or '').strip() or 'claude-opus-5-5'}


def from_jev(plan):
    """Ruta de Jev → carril (None si Jev no decidió)."""
    if not plan or not plan.get('route'):
        return None
    r = plan['route']
    if r == 'local_fact':
        return 'local'
    if r in ('needs_tools', 'offtopic'):
        return 'mid' if (plan.get('about_portfolio') or 0) >= 0.5 else 'small'
    if r == 'needs_deep_reasoning':
        return 'frontier' if (plan.get('confidence') or 0) >= 0.8 else 'mid'
    return None


def from_rules(message, context=None):
    """Respaldo instantáneo cuando Jev no llega: reglas fijas sobre el texto (sin IA)."""
    m = str(message or '')
    words = len(m.split())
    if _DEEP_RX.search(m) or words > 45:
        return 'frontier'
    if _COMPARE_RX.search(m):
        return 'mid'
    if _LOOKUP_RX.search(m) and words <= 14:
        return 'small'
    return 'mid'


def choose(plan, message, context=None):
    lane, by = from_jev(plan), 'jev'
    if lane is None:
        lane, by = from_rules(message, context), 'reglas'
    md = models()
    out = {'lane': lane, 'by': by, 'step_model': md['small'] if lane == 'small' else None,
           'final_model': md['frontier'] if lane == 'frontier' else None}
    out['label_es'], out['label_en'] = LANE_LABEL[lane]
    out['model'] = md['small'] if lane == 'small' else md['frontier'] if lane == 'frontier' else md['mid']
    return out
