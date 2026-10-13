"""core/gates/engine.py — el evaluador COMPILADO de las formas SHACL (docs/INFRA_OPERATIVA.md §3.3-§3.5; paso 10).

    governance/shapes/*.ttl ──(scripts/build_shapes.py, rdflib, en CI o a mano)──► compiled.ir.json
    IR del release vigente (artefacto `ontology.shapes`) ──(arranque, solo stdlib)──► validadores Python

Sin rdflib ni pySHACL en producción: pySHACL es el ORÁCULO en las pruebas (tests/test_gates_conformance.py exige
0 diferencias). Semántica de SHACL Core que el compilador soporta (la misma que pySHACL, verificada):
datatype · in · minInclusive/maxInclusive/minExclusive/maxExclusive · minCount/maxCount · pattern · lessThan ·
lessThanOrEquals · disjoint · class; y `sh:sparql` por su `khs:impl` (core/gates/rules.py).

`evaluate(triples, gate, focus)` → GateReport/1 (core/gates/report.py). Presupuesto: ≤ 0,3 ms p95 por puerta.
`load()` verifica el ir_hash del release vigente y que existan TODAS sus impl; si no, las puertas quedan
`unavailable` (🩺 en rojo; en sombra no bloquea nada — en el paso 11 cerrará las escrituras).
"""
import hashlib
import json
import logging
import os
import re
import threading
import time
from decimal import Decimal

from core.gates import focus as F
from core.gates import rules as R

log = logging.getLogger('khipu')

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IR_PATH = os.path.join(ROOT, 'governance', 'shapes', 'compiled.ir.json')
SEVERITY = {F.SH + 'Violation': 'block', F.KHS + 'RequiresApproval': 'requires_approval',
            F.SH + 'Warning': 'warn', F.SH + 'Info': 'info'}
_ORDER = {'pass': 0, 'info': 1, 'warn': 2, 'requires_approval': 3, 'block': 4}
_LOCK = threading.Lock()
_STATE = {'compiled': None, 'ir_hash': None, 'semver': None, 'error': None, 'loaded_at': None}


def ir_canonical_hash(ir):
    """Hash SEMÁNTICO del IR: sin source_sha ni ir_hash (un cambio de formato del TTL no lo mueve)."""
    body = {k: v for k, v in ir.items() if k not in ('ir_hash', 'source_sha')}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
                          .encode('utf-8')).hexdigest()


# ── índice del grafo foco ────────────────────────────────────────────────────
class Index:
    __slots__ = ('_sp', '_types')

    def __init__(self, triples):
        sp, types = {}, {}
        for s, p, o in triples:
            sp.setdefault(s, {}).setdefault(p, []).append(o)
            if p == F.RDF_TYPE:
                types.setdefault(o, []).append(s)
        self._sp, self._types = sp, types

    def vals(self, s, p):
        return (self._sp.get(s) or {}).get(p) or []

    def subjects_of_type(self, cls):
        return list(dict.fromkeys(self._types.get(cls) or ()))

    def has_type(self, s, cls):
        return any(str(t) == cls for t in self.vals(s, F.RDF_TYPE))


# ── restricciones de propiedad ───────────────────────────────────────────────
def _is_num(v):
    return isinstance(v, Decimal) and not isinstance(v, bool)


def _datatype_ok(v, dt):
    if isinstance(v, F.IRI):
        return False
    if dt == F.XSD + 'decimal':
        return _is_num(v)
    if dt == F.XSD + 'boolean':
        return isinstance(v, bool)
    if dt == F.XSD + 'dateTime':
        from datetime import datetime
        return isinstance(v, datetime)
    if dt == F.XSD + 'string':
        return isinstance(v, str) and not isinstance(v, F.IRI)
    return False


def _cmp_num(v, op, x):
    """Comparación de un valor con un parámetro numérico del TTL: no comparable → infringe (como pySHACL)."""
    if not _is_num(v):
        return False
    return {'min_inc': v >= x, 'max_inc': v <= x, 'min_exc': v > x, 'max_exc': v < x}[op]


def _pair_ok(v, w, op):
    """lessThan / lessThanOrEquals entre dos valores del foco: deben ser comparables (número-número, fecha-fecha)."""
    from datetime import datetime
    if _is_num(v) and _is_num(w):
        pass
    elif isinstance(v, datetime) and isinstance(w, datetime):
        pass
    elif (isinstance(v, str) and isinstance(w, str) and not isinstance(v, F.IRI) and not isinstance(w, F.IRI)):
        pass
    else:
        return False
    return v < w if op == 'lt' else v <= w


def _compile_constraint(c):
    """→ fn(g, this, values) -> [(value, limit)] de las infracciones."""
    kind = c['kind']
    if kind == 'datatype':
        dt = F.expand(c['value'])
        return lambda g, this, vs: [(v, None) for v in vs if not _datatype_ok(v, dt)]
    if kind == 'in':
        allowed = list(c['value'])
        return lambda g, this, vs: [(v, None) for v in vs
                                    if not any(R.term_eq(v, a) for a in allowed)]
    if kind in ('minInclusive', 'maxInclusive', 'minExclusive', 'maxExclusive'):
        x = Decimal(str(c['value']))
        op = {'minInclusive': 'min_inc', 'maxInclusive': 'max_inc', 'minExclusive': 'min_exc',
              'maxExclusive': 'max_exc'}[kind]
        return lambda g, this, vs: [(v, x) for v in vs if not _cmp_num(v, op, x)]
    if kind == 'minCount':
        n = int(c['value'])
        return lambda g, this, vs: [(None, n)] if len(vs) < n else []
    if kind == 'maxCount':
        n = int(c['value'])
        return lambda g, this, vs: [(None, n)] if len(vs) > n else []
    if kind == 'pattern':
        rx = re.compile(c['value'], re.I if 'i' in (c.get('flags') or '') else 0)
        return lambda g, this, vs: [(v, None) for v in vs if not rx.search(R.lex(v))]
    if kind in ('lessThan', 'lessThanOrEquals'):
        other = F.expand(c['value'])
        op = 'lt' if kind == 'lessThan' else 'le'

        def _lt(g, this, vs, other=other, op=op):
            ws = g.vals(this, other)
            return [(v, w) for v in vs for w in ws if not _pair_ok(v, w, op)]
        return _lt
    if kind == 'disjoint':
        other = F.expand(c['value'])
        return lambda g, this, vs: [(v, None) for v in vs if any(R.term_eq(v, w) for w in g.vals(this, other))]
    if kind == 'class':
        cls = F.expand(c['value'])
        return lambda g, this, vs: [(v, None) for v in vs if not (isinstance(v, F.IRI) and g.has_type(v, cls))]
    raise ValueError(f'restricción no soportada por el compilador: {kind}')


class Compiled:
    __slots__ = ('by_target', 'ir_hash', 'semver', 'n_rules', 'rules')


def compile_ir(ir):
    """IR → estructura ejecutable. Falla si falta una impl (el arranque y build_shapes también)."""
    missing = sorted({s['impl'] for sh in ir['shapes'] for s in sh.get('sparql') or () if s['impl'] not in R.RULES})
    if missing:
        raise RuntimeError(f'impl de SPARQL sin registrar en core/gates/rules.py: {missing}')
    by_target = {}
    rules = set()
    for sh in ir['shapes']:
        tgt = F.expand(sh['target'])
        entry = by_target.setdefault(tgt, [])
        for p in sh.get('props') or ():
            fns = [_compile_constraint(c) for c in p['constraints']]
            entry.append(('prop', p, F.expand(p['path']), fns))
            rules.add(p['rule'])
        for s in sh.get('sparql') or ():
            entry.append(('sparql', s, None, [R.RULES[s['impl']]]))
            rules.add(s['rule'])
    c = Compiled()
    c.by_target, c.ir_hash, c.semver, c.n_rules, c.rules = by_target, ir['ir_hash'], ir.get('semver'), len(rules), rules
    return c


# ── carga del release vigente ────────────────────────────────────────────────
def read_ir_file(path=IR_PATH):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def load(force=False):
    """Compila el IR del release vigente (artefacto ontology.shapes: params.ir), verificando su hash."""
    from core import governance
    with _LOCK:
        cur = _STATE['compiled']
    try:
        art = governance.param('ontology.shapes', 'ir')
        want = governance.param('ontology.shapes', 'ir_hash')
        if not force and cur is not None and cur.ir_hash == want:
            return cur
        got = ir_canonical_hash(art)
        if got != want or art.get('ir_hash') != want:
            raise RuntimeError(f'el IR de las formas no coincide con su hash ({got[:12]} ≠ {want[:12]})')
        comp = compile_ir(art)
        comp.semver = governance.artifact_semver('ontology.shapes')
        with _LOCK:
            _STATE.update(compiled=comp, ir_hash=want, semver=comp.semver, error=None, loaded_at=time.time())
        return comp
    except Exception as e:  # noqa: BLE001
        with _LOCK:
            _STATE.update(compiled=None, error=f'{type(e).__name__}: {str(e)[:200]}')
        log.error('gates: puertas NO disponibles (%s)', _STATE['error'])
        return None


def state():
    with _LOCK:
        c = _STATE['compiled']
        return {'available': c is not None, 'ir_hash': _STATE['ir_hash'], 'semver': _STATE['semver'],
                'rules': c.n_rules if c else 0, 'error': _STATE['error']}


# ── evaluación ───────────────────────────────────────────────────────────────
def run(compiled, triples):
    """Resultados crudos [(focus, kind, spec, value, limit)] sobre TODOS los nodos objetivo del grafo foco."""
    g = Index(triples)
    out = []
    for tgt, entries in compiled.by_target.items():
        for this in g.subjects_of_type(tgt):
            for kind, spec, path, fns in entries:
                if kind == 'prop':
                    vs = g.vals(this, path)
                    for fn in fns:
                        for v, lim in fn(g, this, vs):
                            out.append((this, kind, spec, v, lim))
                else:
                    for v, lim in fns[0](g, this):
                        out.append((this, kind, spec, v, lim))
    return out


def worst(a, b):
    return a if _ORDER.get(a, 0) >= _ORDER.get(b, 0) else b
