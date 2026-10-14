"""core/genui/provenance.py — el «caminante» de PROCEDENCIA (docs/CHAT_UI_GENERATIVA.md §5.5, capa 2).

Toda cifra de un bloque tiene que EXISTIR en el resultado de la herramienta que el bloque cita (`prov`). Si una no
está, el bloque se descarta (`dropped: invalid`) y queda en el log: nunca se muestra un número sin dueño.

    figures_of(block)                → [(ruta, valor)]  los números que el usuario VE (no los índices, rangos ni
                                                         versiones: rank, hop, generation, graph_version…)
    assert_from(block, results, transforms=(), bases=None) → [(ruta, valor)] de las cifras SIN procedencia
                                                         ([] = todas tienen dueño)

Transformaciones DECLARADAS por el constructor (y fijadas en su prueba dorada):
    round      el valor es el de la fuente redondeado a 0–4 decimales
    usd_b      USD → miles de millones (x / 1e9)
    scale100   fracción → porcentaje (x × 100: magnitud 0–1 del choque, umbral del kernel)
    scale100_round  fracción → porcentaje redondeado a 0–4 decimales (solo esa composición; no afloja el resto)
    rebase     serie llevada a índice 100 (v = 100 · p / base; `bases` = {índice de serie: base}, base en la fuente)
    absent_zero  0 % para una empresa que el resultado deja FUERA de una lista que declara estar completa
LTTB no necesita transformación: elige puntos que existen.
"""
import bisect
import math

TRANSFORMS = ('round', 'usd_b', 'scale100', 'scale100_round', 'rebase', 'absent_zero')


def _n(v):
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)) and math.isfinite(float(v)):
        return float(v)
    return None


def numbers_in(obj, out=None, depth=0):
    """Todos los números (no booleanos) de un resultado de herramienta, en cualquier nivel."""
    out = [] if out is None else out
    if depth > 40:
        return out
    if isinstance(obj, dict):
        for v in obj.values():
            numbers_in(v, out, depth + 1)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            numbers_in(v, out, depth + 1)
    else:
        x = _n(obj)
        if x is not None:
            out.append(x)
    return out


# ── qué números de cada tipo de bloque son CIFRAS (lo que se ve) ─────────────────────────────────────────────────
def _fig(out, path, f):
    if isinstance(f, dict):
        v = _n(f.get('v'))
        if v is not None:
            out.append((path + ('v',), v))


def _series(out, path, s):
    if not isinstance(s, dict):
        return
    for i, p in enumerate(s.get('points') or []):
        if isinstance(p, list):
            for j in range(1, len(p)):
                v = _n(p[j])
                if v is not None:
                    out.append((path + ('points', i, j), v))


def _links(out, path, links, keys=('weight', 'conf')):
    for i, ln in enumerate(links or []):
        if isinstance(ln, dict):
            for k in keys:
                v = _n(ln.get(k))
                if v is not None:
                    out.append((path + (i, k), v))


def figures_of(block):
    t = block.get('type')
    d = block.get('data') if isinstance(block.get('data'), dict) else {}
    out = []
    P = ('data',)
    if t == 'metric.tiles':
        for i, it in enumerate(d.get('items') or []):
            _fig(out, P + ('items', i, 'value'), it.get('value'))
            _fig(out, P + ('items', i, 'delta'), it.get('delta'))
            _series(out, P + ('items', i, 'spark'), it.get('spark'))
    elif t == 'chart.line':
        for i, s in enumerate(d.get('series') or []):
            _series(out, P + ('series', i), s)
    elif t == 'chart.candles':
        _series(out, P + ('series',), d.get('series'))
    elif t in ('chart.bar', 'ranking'):
        for i, it in enumerate(d.get('items') or []):
            v = _n(it.get('v'))
            if v is not None:
                out.append((P + ('items', i, 'v'), v))
            _fig(out, P + ('items', i, 'delta'), it.get('delta'))
    elif t == 'table':
        nums = [c.get('key') for c in d.get('columns') or [] if c.get('kind') == 'number']
        for i, r in enumerate(d.get('rows') or []):
            for k in nums:
                v = _n((r or {}).get(k))
                if v is not None:
                    out.append((P + ('rows', i, k), v))
    elif t == 'company.card':
        for k in ('price', 'change', 'market_cap', 'nrs'):
            _fig(out, P + (k,), d.get(k))
        pv = d.get('private_valuation')
        if isinstance(pv, dict):
            _fig(out, P + ('private_valuation', 'value'), pv.get('value'))
        _series(out, P + ('spark',), d.get('spark'))
        _links(out, P + ('top_suppliers',), d.get('top_suppliers'))
        _links(out, P + ('top_customers',), d.get('top_customers'))
    elif t == 'graph.mini':
        _links(out, P + ('edges',), d.get('edges'))
    elif t == 'impact.cascade':
        for k in ('severity', 'total', 'threshold_pct'):
            v = _n(d.get(k))
            if v is not None:
                out.append((P + (k,), v))
        for i, h in enumerate(d.get('hops') or []):
            for k in ('count', 'max_pct'):
                v = _n(h.get(k))
                if v is not None:
                    out.append((P + ('hops', i, k), v))
            for j, e in enumerate(h.get('entities') or []):
                v = _n(e.get('impact_pct'))
                if v is not None:
                    out.append((P + ('hops', i, 'entities', j, 'impact_pct'), v))
        for i, r in enumerate(d.get('least_hit_rivals') or []):
            v = _n(r.get('damage_pct'))
            if v is not None:
                out.append((P + ('least_hit_rivals', i, 'damage_pct'), v))
        pf = d.get('portfolio')
        if isinstance(pf, dict):
            _fig(out, P + ('portfolio', 'value'), pf.get('value'))
            _fig(out, P + ('portfolio', 'band'), pf.get('band'))
    elif t == 'geo.mini':
        for i, p in enumerate(d.get('points') or []):
            for k in ('lat', 'lon', 'weight'):
                v = _n(p.get(k))
                if v is not None:
                    out.append((P + ('points', i, k), v))
    elif t == 'timeline':
        for i, it in enumerate(d.get('items') or []):
            for k in ('lat', 'lon'):
                v = _n(it.get(k))
                if v is not None:
                    out.append((P + ('items', i, k), v))
    elif t == 'comparison':
        for i, m in enumerate(d.get('metrics') or []):
            for j, c in enumerate(m.get('cells') or []):
                v = _n(c)
                if v is not None:
                    out.append((P + ('metrics', i, 'cells', j), v))
    return out


# ── comprobación ─────────────────────────────────────────────────────────────────────────────────────────────────
class _Pool:
    """Números de la fuente, ordenados, con búsqueda por tolerancia."""

    def __init__(self, results):
        xs = []
        for r in results:
            numbers_in(r, xs)
        self.xs = sorted(set(xs))

    def near(self, v, tol):
        i = bisect.bisect_left(self.xs, v - tol)
        return i < len(self.xs) and self.xs[i] <= v + tol

    def has(self, v):
        return self.near(v, 1e-9 * max(1.0, abs(v)))


def _ok(v, pool, transforms, path, bases):
    if pool.has(v):
        return True
    if 'round' in transforms:
        for p in range(0, 5):
            if round(v, p) == v and pool.near(v, 0.5 * 10 ** -p + 1e-12):
                return True
    if 'usd_b' in transforms and pool.near(v * 1e9, max(1.0, abs(v) * 1e9 * 1e-9)):
        return True
    if 'scale100' in transforms and pool.has(v / 100.0):
        return True
    if 'scale100_round' in transforms:
        for p in range(0, 5):
            if round(v, p) == v and pool.near(v / 100.0, (0.5 * 10 ** -p + 1e-12) / 100.0):
                return True
    if 'rebase' in transforms and bases:
        # ruta …('series', i, 'points', k, 1) → la base de la serie i
        si = None
        for a, b in zip(path, path[1:]):
            if a == 'series' and isinstance(b, int):
                si = b
        base = bases.get(si) if si is not None else None
        if base:
            raw = v * base / 100.0
            if pool.near(raw, max(1e-6, abs(raw) * 2e-6)):
                return True
    if 'absent_zero' in transforms and v == 0:
        return True
    return False


def assert_from(block, results, transforms=(), bases=None):
    """Cifras del bloque que NO están en `results` (lista de resultados de herramienta citados). [] = todo en orden.
    Además, toda base de rebase tiene que estar en la fuente."""
    if isinstance(results, dict):
        results = [results]
    pool = _Pool(results or [])
    bad = []
    tr = set(transforms or ())
    for si, b in (bases or {}).items():
        if not pool.has(float(b)):
            bad.append((('rebase_base', si), b))
    for path, v in figures_of(block):
        if not _ok(v, pool, tr, path, bases):
            bad.append((path, v))
    return bad
