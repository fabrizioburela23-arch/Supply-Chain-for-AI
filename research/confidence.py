"""research/confidence.py — confianza de una claim (metodología conf-v2).

conf-v2 (C9, misión de reparación 2026-10-04): lo que Khipus produce
INTERNAMENTE (catálogo, grafo, ratios y pares calculados) es UNA sola familia
de referencia 'khipus' (antes 'analysis:khipus:ratios:X' y 'catalog:khipus:
catalog:X' contaban como fuentes independientes y esquivaban el tope 0.6); la
evidencia 'computed' no suma independencia (sus insumos ya cuentan); y una
conclusión con CIFRAS DE DINERO sin ninguna fuente primaria externa (http) queda
topada en 0.5. Las claims conf-v1 existentes no se recalculan (append-only).

NO es "el LLM dijo 0.91". Se combina, con pesos explícitos y guardados:
  source_quality   confiabilidad media de la evidencia de apoyo (0-1)
  independence     cuántas referencias DISTINTAS la sostienen (satura en 3)
  recency          qué tan reciente es la evidencia (noticia vieja pesa menos)
  agreement        1 − 0.5·(contra / (a favor + contra))
  agent_certainty  lo que declara el agente (peso bajo a propósito)
  completeness     qué fracción de las fuentes que ese agente necesita llegó
Topes: una sola referencia → ≤ 0.6; nunca > 0.95. Todo queda en
`confidence_components` para auditar (docs/CLAIM_MODEL.md).
"""
from datetime import datetime, timezone
from urllib.parse import urlparse

METHOD = 'conf-v2'
MONEY_NO_EXTERNAL_CAP = 0.5
WEIGHTS = {'source_quality': 0.30, 'independence': 0.20, 'recency': 0.15,
           'agreement': 0.15, 'agent_certainty': 0.10, 'completeness': 0.10}


def _parse(ts):
    if not ts:
        return None
    s = str(ts)
    try:
        if len(s) == 16 and s[8] == 'T' and s.endswith('Z'):          # GDELT 20260927T120000Z
            return datetime.strptime(s, '%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)
        d = datetime.fromisoformat(s.replace('Z', '+00:00'))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _recency(item, now):
    if item.get('source_type') in ('financials', 'market', 'graph', 'analysis', 'computed'):
        return 1.0          # recuperado/calculado ahora mismo del proveedor/grafo
    if item.get('source_type') == 'catalog':
        return 0.5          # curado a mano, fecha incierta
    d = _parse(item.get('published_at'))
    if not d:
        return 0.5
    days = max(0.0, (now - d).total_seconds() / 86400)
    if days <= 30:
        return 1.0
    if days >= 365:
        return 0.3
    return round(1.0 - 0.7 * (days - 30) / 335, 3)


def _is_external(item):
    ref = str(item.get('reference') or item.get('ref') or '')
    return ref.startswith('http://') or ref.startswith('https://')


def _key(item):
    ref = str(item.get('reference') or item.get('ref') or '')
    if ref.startswith('khipus:'):
        return 'khipus'                     # catálogo + grafo + ratios + pares = UNA referencia interna
    try:
        host = urlparse(ref).netloc
        if host:
            return item.get('source_type', '') + ':' + host
    except Exception:  # noqa: BLE001
        pass
    return item.get('source_type', '') + ':' + ref


def compute_confidence(support, counter, agent_certainty, completeness, now=None, statement=None):
    """support/counter: listas de items del paquete de evidencia. statement
    (opcional): texto de la claim, para el tope de cifras sin fuente externa."""
    now = now or datetime.now(timezone.utc)
    if not support:
        return 0.0, {'method': METHOD, 'reason': 'sin evidencia de apoyo'}
    q = sum(float(x.get('reliability') or 0) for x in support) / len(support)
    # lo 'computed' no aporta independencia: sus insumos (estados, perfil) ya cuentan
    distinct = len({_key(x) for x in support if x.get('source_type') != 'computed'}) or 1
    indep = min(1.0, distinct / 3.0)
    rec = sum(_recency(x, now) for x in support) / len(support)
    n_s, n_c = len(support), len(counter or [])
    agree = 1.0 - 0.5 * (n_c / (n_s + n_c))
    cert = max(0.0, min(1.0, float(agent_certainty or 0)))
    comp = max(0.0, min(1.0, float(completeness or 0)))
    comps = {'source_quality': round(q, 3), 'independence': round(indep, 3), 'recency': round(rec, 3),
             'agreement': round(agree, 3), 'agent_certainty': round(cert, 3), 'completeness': round(comp, 3)}
    score = sum(comps[k] * w for k, w in WEIGHTS.items())
    caps = []
    if distinct <= 1:
        score = min(score, 0.6)
        caps.append('una sola referencia → tope 0.6')
    external = any(_is_external(x) for x in support)
    if statement and not external:
        try:
            from core.numbers import money_mentions
            if money_mentions(statement):
                score = min(score, MONEY_NO_EXTERNAL_CAP)
                caps.append(f'cifras de dinero sin fuente primaria externa → tope {MONEY_NO_EXTERNAL_CAP}')
        except Exception:  # noqa: BLE001
            pass
    score = min(score, 0.95)
    return round(score, 3), {'method': METHOD, 'weights': WEIGHTS, 'components': comps,
                             'distinct_sources': distinct, 'n_support': n_s, 'n_counter': n_c,
                             'external_sources': external, 'caps': caps}
