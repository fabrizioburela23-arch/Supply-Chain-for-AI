"""core/gates/rules.py — las implementaciones Python de cada restricción SPARQL de las formas (§3.3 punto 2).

Cada `sh:sparql` de governance/shapes/*.ttl declara `khs:impl "<regla>@<versión>"`; aquí se registra con
`@rule('<regla>', v=<versión>)`. scripts/build_shapes.py y el arranque (core/gates/engine.load) fallan si falta
alguna. La prueba de conformidad (tests/test_gates_conformance.py) corre el TEXTO SPARQL real con pySHACL contra
estas funciones sobre ≥1.000 focos aleatorios: 0 diferencias.

Cada función recibe (g, this) — g = índice del grafo foco (core/gates/engine.Index) — y devuelve una lista de
(valor, límite) por cada fila de la consulta (valor None = la consulta no devuelve ?value). Se imita la lógica de
3 valores de SPARQL (un error de tipo en un FILTER descarta la fila; `||` con un verdadero es verdadero).
"""
import re
from decimal import Decimal

from core.gates.focus import IRI, kh

RULES = {}
ZERO64 = '0' * 64
_TRUE = True


def rule(name, v=1):
    def deco(fn):
        RULES[f'{name}@{v}'] = fn
        return fn
    return deco


# ── lógica de 3 valores (None = error de tipo) ───────────────────────────────
def isnum(x):
    return isinstance(x, Decimal) and not isinstance(x, bool)


def cmp(a, op, b):
    if a is None or b is None:
        return None
    if isnum(a) and isnum(b):
        pass
    elif isinstance(a, str) and isinstance(b, str) and not isinstance(a, IRI) and not isinstance(b, IRI):
        pass
    elif isinstance(a, bool) and isinstance(b, bool) and op in ('=', '!='):
        pass
    else:
        return None
    return {'<': a < b, '<=': a <= b, '>': a > b, '>=': a >= b, '=': a == b, '!=': a != b}[op]


def AND(*xs):
    if any(x is False for x in xs):
        return False
    if any(x is None for x in xs):
        return None
    return True


def OR(*xs):
    if any(x is True for x in xs):
        return True
    if any(x is None for x in xs):
        return None
    return False


def NOT(x):
    return None if x is None else (not x)


def term_eq(a, b):
    """Igualdad de TÉRMINOS (la de un patrón de tripletas): mismo tipo de término y mismo valor."""
    if isinstance(a, IRI) or isinstance(b, IRI):
        return isinstance(a, IRI) and isinstance(b, IRI) and str(a) == str(b)
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if isinstance(a, Decimal) or isinstance(b, Decimal):
        return isinstance(a, Decimal) and isinstance(b, Decimal) and str(a) == str(b)
    return type(a) is type(b) and a == b


def has(g, s, p, o):
    return any(term_eq(x, o) for x in g.vals(s, p))


def lex(x):
    if isinstance(x, bool):
        return 'true' if x else 'false'
    return str(x)


# ── vínculo ──────────────────────────────────────────────────────────────────
@rule('link.flow_supplier_type')
def link_flow_supplier_type(g, this):
    if not has(g, this, kh('flow'), True):
        return []
    out = []
    for v in g.vals(this, kh('source')):
        for t in g.vals(v, kh('objType')):
            if OR(cmp(t, '=', 'Country'), cmp(t, '=', 'Policy')) is True:
                out.append((v, None))
    return out


@rule('link.inverse_flow_live')
def link_inverse_flow_live(g, this):
    if not has(g, this, kh('flow'), True):
        return []
    out = []
    refs = g.subjects_of_type(kh('LinkRef'))
    for s in g.vals(this, kh('source')):
        for t in g.vals(this, kh('target')):
            for r in g.vals(this, kh('relType')):
                for v in refs:
                    if (has(g, v, kh('source'), t) and has(g, v, kh('target'), s) and has(g, v, kh('relType'), r)
                            and has(g, v, kh('live'), True)):
                        out.append((v, None))
    return out


@rule('link.high_conf_trusted_source')
def link_high_conf_trusted_source(g, this):
    if not has(g, this, kh('flow'), True):
        return []
    out = []
    srcs = g.vals(this, kh('evidencedBy'))
    for v in g.vals(this, kh('confidence')):
        for mn in g.vals(this, kh('highConfMin')):
            for mt in g.vals(this, kh('minTrust')):
                if not (isnum(v) and isnum(mn) and v >= mn):
                    continue
                trusted = any(isnum(tr) and isnum(mt) and tr >= mt for s in srcs for tr in g.vals(s, kh('trust')))
                if not trusted:
                    out.append((v, mn))
    return out


_DIR_RX = re.compile(r'(^|[^a-z0-9áéíóúñ])(usa|uses|utiliza|utilizan|usan)([^a-z0-9áéíóúñ]|$)', re.I)


@rule('link.direction_text_suspect')
def link_direction_text_suspect(g, this):
    return [(v, None) for v in g.vals(this, kh('relLabel')) if not isinstance(v, IRI) and _DIR_RX.search(lex(v))]


@rule('link.dated_fact_has_source')
def link_dated_fact_has_source(g, this):
    if has(g, this, kh('datedFact'), True) and not g.vals(this, kh('evidencedBy')):
        return [(None, None)]
    return []


# ── objeto ───────────────────────────────────────────────────────────────────
@rule('object.type_immutable')
def object_type_immutable(g, this):
    return [(v, p) for v in g.vals(this, kh('type')) for p in g.vals(this, kh('prevType'))
            if cmp(p, '!=', v) is True]


# ── factor ───────────────────────────────────────────────────────────────────
@rule('factor.not_retired')
def factor_not_retired(g, this):
    return [(None, None)] if has(g, this, kh('retired'), True) and has(g, this, kh('active'), True) else []


@rule('factor.coef_range')
def factor_coef_range(g, this):
    out = []
    for m in g.vals(this, kh('membership')):
        for mx in g.vals(this, kh('maxCoef')):
            for v in g.vals(m, kh('coef')):
                if isnum(v) and isnum(mx) and not (v > 0 and v <= mx):
                    out.append((v, mx))
    return out


@rule('factor.has_live_members')
def factor_has_live_members(g, this):
    if has(g, this, kh('retired'), True):
        return []
    if any(has(g, m, kh('live'), True) for m in g.vals(this, kh('membership'))):
        return []
    return [(None, None)]


@rule('factor.noop')
def factor_noop(g, this):
    if not has(g, this, kh('touchesSeverity'), True):
        return []
    out = []
    for v in g.vals(this, kh('severity')):
        for p in g.vals(this, kh('prevSeverity')):
            for a in g.vals(this, kh('active')):
                for pa in g.vals(this, kh('prevActive')):
                    if AND(cmp(v, '=', p), cmp(a, '=', pa)) is True:
                        out.append((v, None))
    return out


# ── acción ───────────────────────────────────────────────────────────────────
@rule('action.auto_apply_allowed')
def action_auto_apply_allowed(g, this):
    if not has(g, this, kh('autoApply'), True):
        return []
    out = []
    confs = g.vals(this, kh('confidence')) or [None]
    mins = g.vals(this, kh('autoMinConfidence')) or [None]
    for v in g.vals(this, kh('actionType')):
        not_safe = not has(g, this, kh('safeAutoType'), v)
        for c in confs:
            for mn in mins:
                if not_safe or c is None or (isnum(c) and isnum(mn) and c < mn):
                    out.append((v, mn))
    return out


@rule('action.agent_needs_human')
def action_agent_needs_human(g, this):
    if not has(g, this, kh('principalKind'), 'agent'):
        return []
    return [(v, None) for v in g.vals(this, kh('actionType')) if not has(g, this, kh('safeAutoType'), v)]


@rule('action.retraction_has_reason')
def action_retraction_has_reason(g, this):
    if not has(g, this, kh('actionType'), 'RetractarVinculo'):
        return []
    if any(len(lex(r)) > 0 for r in g.vals(this, kh('reason')) if not isinstance(r, IRI)):
        return []
    return [(None, None)]


# ── decisión ─────────────────────────────────────────────────────────────────
@rule('decision.release_present')
def decision_release_present(g, this):
    ok = any(AND(len(lex(h)) == 64, cmp(h, '!=', ZERO64)) is True
             for h in g.vals(this, kh('releaseHash')) if not isinstance(h, IRI))
    return [] if ok else [(None, None)]


@rule('decision.quotes_have_asof_src')
def decision_quotes_have_asof_src(g, this):
    out = []
    for q in g.vals(this, kh('quote')):
        if g.vals(q, kh('asOf')) and g.vals(q, kh('src')):
            continue
        out.extend((v, None) for v in g.vals(q, kh('ticker')))
    return out


@rule('decision.money_executed_not_blocked')
def decision_money_executed_not_blocked(g, this):
    if not (has(g, this, kh('status'), 'executed') and has(g, this, kh('verdict'), 'block')):
        return []
    return [(v, None) for v in g.vals(this, kh('kind')) if isinstance(v, str) and not isinstance(v, IRI)
            and v.startswith('order.')]
