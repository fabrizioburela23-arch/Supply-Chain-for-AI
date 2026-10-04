"""research/errors.py — traduce errores técnicos de la IA a lenguaje simple.

Pedido (2026-10-02): "la investigación falló" sin saber por qué. Cada agente
guarda su error técnico (lo necesita el diagnóstico); la UI muestra además
esta explicación con QUÉ HACER, en español e inglés.
"""
import re

_RULES = (
    (r'IA ocupada|AI busy',
     'La IA estaba ocupada atendiendo otras consultas (comité, chat u otras investigaciones) y se agotaron las esperas. Vuelve a intentarlo en un minuto.',
     'The AI was busy with other requests (committee, chat or other research) and the waits ran out. Try again in a minute.'),
    (r'respuesta vac[ií]a|empty response|sin candidates',
     'La IA (Gemini) gastó su espacio "pensando" y no alcanzó a escribir la respuesta. Vuelve a intentarlo; si se repite, avísame.',
     'The AI (Gemini) used up its space "thinking" and did not get to write the answer. Try again; if it repeats, tell me.'),
    (r'404|NOT_FOUND|410|not found',
     'El modelo de IA configurado ya no existe en el proveedor (fue retirado). Cambia GEMINI_MODEL / NVIDIA_MODEL en Railway → Variables.',
     'The configured AI model no longer exists at the provider (retired). Change GEMINI_MODEL / NVIDIA_MODEL in Railway → Variables.'),
    (r'429|RESOURCE_EXHAUSTED|rate limit|too many',
     'El proveedor de IA limitó las llamadas por un momento (cuota). Espera un minuto y reintenta.',
     'The AI provider throttled calls for a moment (quota). Wait a minute and retry.'),
    (r'timeout|tard[oó] demasiado|no respondi[oó] a tiempo',
     'La IA tardó demasiado en responder. Reintenta; si pasa seguido, prueba un modelo más rápido en Railway.',
     'The AI took too long to answer. Retry; if it keeps happening, try a faster model in Railway.'),
    (r'l[ií]mite (diario|mensual) de gasto|lleg[oó] a su l[ií]mite|spend limit|AI limit',
     'Se alcanzó un límite de gasto de IA que tú configuraste. Míralo y ajústalo en 🩺 Sistema → 💰 Gasto IA.',
     'An AI spend limit you configured was reached. Review and adjust it in 🩺 System → 💰 AI spend.'),
    (r'presupuesto diario agotado|budget',
     'Se acabó el presupuesto diario de IA. Espera a mañana o sube RESEARCH_DAILY_BUDGET_USD en Railway → Variables.',
     'The daily AI budget is used up. Wait until tomorrow or raise RESEARCH_DAILY_BUDGET_USD in Railway → Variables.'),
    (r'credit balance|insufficient_quota|billing|payment|402',
     'El proveedor de IA no tiene saldo. Recarga en console.anthropic.com → Billing (o el panel del proveedor).',
     'The AI provider has no credit. Top up at console.anthropic.com → Billing (or the provider dashboard).'),
    (r'\b401\b|invalid.{0,12}api.?key|api key not valid|unauthori[sz]ed|sin clave|permission',
     'La clave de la IA falta o es inválida. Revisa ANTHROPIC_KEY / GEMINI_KEY / NVIDIA_KEY en Railway.',
     'The AI key is missing or invalid. Check ANTHROPIC_KEY / GEMINI_KEY / NVIDIA_KEY in Railway.'),
    (r'\b(404|410)\b|not.?found|deprecated|decommission|no longer (available|supported)|retired',
     'El modelo de IA fue retirado por el proveedor. Cambia GEMINI_MODEL / NVIDIA_MODEL en Railway (🩺 Sistema → IA lo dice).',
     'The AI model was retired by the provider. Change GEMINI_MODEL / NVIDIA_MODEL in Railway (🩺 System → AI says which).'),
    (r'\b429\b|rate.?limit|too many requests|quota|overloaded|\b529\b',
     'El proveedor de IA está saturado o llegó a su límite. Espera unos minutos y vuelve a intentar.',
     'The AI provider is overloaded or hit its limit. Wait a few minutes and try again.'),
    (r'time.?out|timed out|read timeout',
     'La IA tardó demasiado en responder. Vuelve a intentar (o usa profundidad Rápida).',
     'The AI took too long to answer. Try again (or use Quick depth).'),
    (r'salida inválida|invalid output|validation',
     'La IA respondió con un formato que no pasó la validación (cifras sin respaldo o JSON roto) tras reintentar. Vuelve a intentar.',
     'The AI answered in a format that failed validation (unsupported figures or broken JSON) after retrying. Try again.'),
    (r'sin evidencia',
     'No encontré datos sobre esta empresa para este analista (no cotiza o no hay noticias/estados). Es normal en privadas.',
     'No data found on this company for this analyst (unlisted or no news/statements). Normal for private companies.'),
    (r'ningún proveedor|sin proveedores|no provider',
     'No hay ningún proveedor de IA disponible. Revisa 🩺 Sistema → IA.',
     'No AI provider is available. Check 🩺 System → AI.'),
)


def friendly(err):
    """(es, en) o (None, None) si no se reconoce."""
    t = str(err or '')
    if not t:
        return None, None
    for rx, es, en in _RULES:
        if re.search(rx, t, re.I):
            return es, en
    return None, None


def run_hint(errors):
    for e in errors or []:
        if isinstance(e, str):
            es, en = friendly(e)
            if es:
                return es, en
    return None, None
