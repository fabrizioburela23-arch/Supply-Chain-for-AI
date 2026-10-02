"""core/numbers.py — guardián de CIFRAS (anti-alucinación numérica).

Problema real (2026-09-28): un agente escribió que Broadcom "vale ~$350B"
cuando su capitalización en vivo superaba $1T — el modelo usó su MEMORIA
de entrenamiento, no el paquete de evidencia. Un dato así perjudica la
tesis del inversionista.

Regla: toda cifra de dinero (o precio) que un agente escriba en una claim
debe aparecer —con tolerancia de redondeo— en el paquete de evidencia.
Si no aparece, la salida se rechaza y el modelo recibe el error como
feedback para corregirla (research/llm.structured_generate).
"""
import re

# número: 1.100 / 1,100 / 1100.5 / 1,1 / 350
_NUM = r'(\d{1,3}(?:[.,]\d{3})+(?![.,]?\d)|\d+(?:[.,]\d+)?)'

# multiplicador a MILES DE MILLONES (B) de USD
_UNITS = [
    (r'billones|billón|billon(?:es)?|trillions?|tn|t\b', 1000.0),
    (r'mil\s+millones|billions?|bn|b\b', 1.0),
    (r'millones|millón|millions?|mm|m\b', 0.001),
]
_UNIT_RE = '|'.join(u for u, _ in _UNITS)

# con moneda delante: $350B · US$ 1,1 billones · USD 57 mil millones · $150
_MONEY_PREFIX = re.compile(r'(?:US\s?\$|USD\s?|\$)\s?' + _NUM + r'(?:\s?(' + _UNIT_RE + r'))?', re.I)
# sin moneda pero con unidad pegada o en palabra: 350B · 1.1T · 350 mil millones de dólares
_MONEY_SUFFIX = re.compile(r'(?<![\w$.,])' + _NUM + r'\s?(' + _UNIT_RE + r')\s*(?:de\s+)?(?:d[oó]lares|usd|dollars)', re.I)
_MONEY_GLUED = re.compile(r'(?<![\w$.,])' + _NUM + r'(B|T|bn|tn)\b')

# números de la evidencia: cualquier número, con unidad opcional
_ANY_NUM = re.compile(r'(?<![\w])' + r'(-?\d+(?:[.,]\d+)*)' + r'\s?(' + _UNIT_RE + r')?', re.I)

_RATIO_RX = re.compile(r'[-+]?\d+(?:[.,]\d+)?\s?(?:%|x\b|puntos\b|points\b)', re.I)
_DATE_RX = re.compile(r'\b\d{4}-\d{2}-\d{2}(?:[T ][\d:.]+(?:Z|[+-]\d{2}:?\d{2})?)?\b')
TOLERANCE = 0.15   # redondeos tipo "~$1,1 billones" o "más de $1T" sobre 1.100B


def _to_float(s):
    s = s.strip()
    if re.fullmatch(r'\d{1,3}(?:[.,]\d{3})+', s):          # separadores de miles
        return float(re.sub(r'[.,]', '', s))
    if s.count(',') == 1 and s.count('.') == 0:
        s = s.replace(',', '.')                              # decimal en español
    s = s.replace(',', '')
    try:
        return float(s)
    except ValueError:
        return None


def _mult(unit):
    if not unit:
        return None
    u = unit.strip().lower()
    for pat, m in _UNITS:
        if re.fullmatch(pat, u, re.I):
            return m
    return None


def money_mentions(text):
    """[(texto_original, valor_en_B | None si es cifra suelta tipo precio, valor_crudo)]"""
    out, seen = [], set()
    for rx in (_MONEY_PREFIX, _MONEY_SUFFIX, _MONEY_GLUED):
        for m in rx.finditer(text or ''):
            if m.span() in seen:
                continue
            seen.add(m.span())
            raw = _to_float(m.group(1))
            if raw is None:
                continue
            mult = _mult(m.group(2) if m.lastindex and m.lastindex >= 2 else None)
            if mult is None:
                # "$150" (precio) o "$57,000,000,000" (dólares crudos)
                b = raw / 1e9 if raw >= 1e6 else None
                out.append((m.group(0).strip(), b, raw))
            else:
                out.append((m.group(0).strip(), raw * mult, raw))
    return out


def evidence_numbers(evidence):
    """Todos los valores numéricos del paquete: crudos y normalizados a B."""
    vals = set()
    for e in evidence or []:
        txt = f"{e.get('title') or ''} {e.get('excerpt') or ''}"
        # las fechas (2026-09-29, 2026-09-30T12:00:00Z) no son cifras: su "09" o "29"
        # respaldaba cifras inventadas como "$9,999 mil millones" (tolerancia 15 % × 1000)
        txt = _DATE_RX.sub(' ', txt)
        # porcentajes y múltiplos (55.9 %, 1.38 %, 12.5x) no son dinero: con la
        # escala ×1000 un "1.38 %" respaldaba "$1.2T" inventado
        txt = _RATIO_RX.sub(' ', txt)
        for m in _ANY_NUM.finditer(txt):
            v = _to_float(m.group(1).lstrip('-'))
            if v is None:
                continue
            vals.add(v)
            mult = _mult(m.group(2))
            if mult is not None:
                vals.add(v * mult)
            if v >= 1e6:
                vals.add(v / 1e9)
    return vals


def _close(a, b):
    return b > 0 and abs(a - b) / max(a, b) <= TOLERANCE


def _supported(value_b, raw, vals):
    for c in vals:
        if value_b is not None and (_close(value_b, c) or _close(value_b, c * 1000) or _close(value_b, c / 1000)):
            return True
        if value_b is None and _close(raw, c):
            return True
    return False


def unsupported_money(text, vals):
    return [t for t, b, raw in money_mentions(text) if not _supported(b, raw, vals)]


def check_numbers(result, evidence):
    """Errores (lista vacía = ok) por cifras que NO están en la evidencia."""
    vals = evidence_numbers(evidence)
    errs = []
    for i, c in enumerate(result.claims):
        txt = ' '.join(filter(None, [c.statement_es, c.statement_en, c.reasoning_summary, c.object]))
        bad = unsupported_money(txt, vals)
        if bad:
            errs.append(f'claim[{i}] usa cifras que NO están en la evidencia: {sorted(set(bad))}. '
                        'Usa SOLO cifras del paquete (la capitalización actual es la del perfil de '
                        'mercado en vivo) o quita la cifra; nunca cifras de memoria.')
    for fld in ('summary_es', 'summary_en'):
        bad = unsupported_money(getattr(result, fld, '') or '', vals)
        if bad:
            errs.append(f'{fld} usa cifras que NO están en la evidencia: {sorted(set(bad))}.')
    return errs


# ── Guardián GENERAL para toda llamada de IA (core/ai._ai_complete) ─────────

NUMBERS_RULE = (
    '\n\nREGLA DE CIFRAS (obligatoria): toda cifra de dinero o precio (capitalización, valuación, '
    'ingresos, deuda, precio de acción, rondas) debe COPIARSE de los datos que te doy en este mensaje. '
    'NUNCA uses cifras de tu memoria: están desactualizadas y un dato falso perjudica al inversionista. '
    'Si no tienes el dato, dilo ("no tengo el dato en vivo") en vez de estimarlo. '
    '/ FIGURES RULE: every money figure or price must be COPIED from the data given in this message; '
    'never from memory. If you lack it, say so instead of estimating.')

_ES = re.compile(r'\b(el|la|los|las|de|que|para|con|una|por)\b', re.I)
_EN = re.compile(r'\b(the|of|and|to|with|for|is|are|that)\b', re.I)


def unsupported_in(text, source_text):
    """Cifras de dinero de `text` que NO aparecen en `source_text` (el input)."""
    vals = evidence_numbers([{'title': '', 'excerpt': source_text or ''}])
    return sorted(set(unsupported_money(text, vals)))


def mark_unsupported(text, bad):
    """Marca en el texto cada cifra sin respaldo (no la borra: el lector ve
    que NO está verificada). Seguro dentro de strings JSON."""
    if not bad:
        return text
    es = len(_ES.findall(text or '')) >= len(_EN.findall(text or ''))
    tag = ' (⚠ cifra no verificada)' if es else ' (⚠ unverified figure)'
    for b in sorted(bad, key=len, reverse=True):
        text = re.sub(re.escape(b) + r'(?! \(⚠)', lambda m: m.group(0) + tag, text)
    return text
