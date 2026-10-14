"""core/genui/validate.py — VALIDADOR COMPILADO del contrato kblocks/1 (solo biblioteca estándar).

Mismo patrón que core/gates frente a pySHACL: en producción NO se usa `jsonschema` (vive en requirements-dev.txt como
ORÁCULO de las pruebas). Este módulo compila UNA vez el esquema `governance/schemas/kblocks-1.schema.json` a
funciones de Python (cierres) que validan exactamente el subconjunto de JSON Schema 2020-12 que el contrato usa:

    type · enum · const · properties · required · additionalProperties · maxProperties · unevaluatedProperties:false
    items · prefixItems · minItems · maxItems · uniqueItems · minLength · maxLength · pattern · format: date-time
    minimum · maximum · exclusiveMinimum · exclusiveMaximum · allOf · anyOf · oneOf · not · if/then/else · $ref

Semántica = la de jsonschema 4.x: `pattern` con re.search; los booleanos NO son números; un entero puede venir
como 1.0; True ≠ 1 en enum/const; `format: date-time` = RFC 3339 con hora y zona y una fecha que exista (el mismo
comprobador que registra tests/test_genui_schema.py). tests/test_genui_validate.py exige 0 diferencias con el
oráculo en ≥ 1.000 mutaciones.

API:
    errors(instance, def_name='Envelope', limit=1) → [(ruta, palabra_clave)]   ([] = válido)
    is_valid(instance, def_name='Envelope') → bool
"""
import datetime
import math
import re
import threading

from core.genui import schema as _schema

_RFC3339 = re.compile(r'^\d{4}-\d{2}-\d{2}[Tt ]\d{2}:\d{2}:\d{2}(\.\d+)?([Zz]|[+-]\d{2}:\d{2})$')


def is_datetime(value):
    """RFC 3339 con hora y zona, y una fecha que exista (2026-02-30 no)."""
    if not isinstance(value, str):
        return True
    if not _RFC3339.match(value):
        return False
    try:
        datetime.datetime.fromisoformat(value.replace('z', 'Z'))
    except ValueError:
        return False
    return True


# ── tipos y igualdad JSON (como jsonschema) ─────────────────────────────────────────────────────────────────────
def _is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _is_integer(x):
    if isinstance(x, bool):
        return False
    if isinstance(x, int):
        return True
    return isinstance(x, float) and math.isfinite(x) and x.is_integer()


_TYPE = {
    'object': lambda x: isinstance(x, dict),
    'array': lambda x: isinstance(x, list),
    'string': lambda x: isinstance(x, str),
    'number': _is_number,
    'integer': _is_integer,
    'boolean': lambda x: isinstance(x, bool),
    'null': lambda x: x is None,
}


def _eq(a, b):
    """Igualdad de jsonschema: True ≠ 1, listas y objetos por contenido."""
    if a is b:
        return True
    if isinstance(a, str) or isinstance(b, str):
        return a == b
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_eq(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_eq(a[k], b[k]) for k in a)
    if a is None or b is None:
        return a is b
    return a == b


# ── compilación ──────────────────────────────────────────────────────────────────────────────────────────────────
class _Compiler:
    def __init__(self, root):
        self.root = root
        self.defs = root.get('$defs') or {}
        self.cache = {}

    def ref(self, ref):
        if not ref.startswith('#/$defs/'):
            raise ValueError(f'$ref no soportado: {ref}')
        name = ref[len('#/$defs/'):]
        if name in self.cache:
            return self.cache[name]
        box = {}

        def lazy(x, path):          # recursión tolerante (el esquema hoy no tiene ciclos)
            return box['f'](x, path)
        self.cache[name] = lazy
        box['f'] = self.compile(self.defs[name])
        self.cache[name] = box['f']
        return box['f']

    def _evaluated(self, node, seen=None):
        """Propiedades que `node` evalúa (properties + las de allOf/$ref/if/then): para unevaluatedProperties."""
        seen = seen if seen is not None else set()
        out = set((node.get('properties') or {}).keys())
        subs = list(node.get('allOf') or [])
        for k in ('if', 'then', 'else'):
            if isinstance(node.get(k), dict):
                subs.append(node[k])
        if '$ref' in node:
            subs.append({'$ref': node['$ref']})
        for s in subs:
            if '$ref' in s and len(s) == 1:
                name = s['$ref'].rsplit('/', 1)[1]
                if name in seen:
                    continue
                seen.add(name)
                out |= self._evaluated(self.defs[name], seen)
            else:
                out |= self._evaluated(s, seen)
        return out

    def compile(self, node):
        if node is True or node == {}:
            return lambda x, path: None
        if node is False:
            return lambda x, path: (path, 'false')
        checks = []
        add = checks.append

        if '$ref' in node:
            r = self.ref(node['$ref'])
            add(r)

        if 'type' in node:
            ts = node['type'] if isinstance(node['type'], list) else [node['type']]
            fns = [_TYPE[t] for t in ts]

            def c_type(x, path, fns=fns):
                return None if any(f(x) for f in fns) else (path, 'type')
            add(c_type)

        if 'const' in node:
            cv = node['const']
            add(lambda x, path, cv=cv: None if _eq(x, cv) else (path, 'const'))
        if 'enum' in node:
            ev = list(node['enum'])
            if all(isinstance(e, str) for e in ev):
                es = frozenset(ev)
                add(lambda x, path, es=es: None if (isinstance(x, str) and x in es) else (path, 'enum'))
            else:
                add(lambda x, path, ev=ev: None if any(_eq(x, e) for e in ev) else (path, 'enum'))

        # cadenas
        mn, mx = node.get('minLength'), node.get('maxLength')
        pat = re.compile(node['pattern']) if 'pattern' in node else None
        fmt = node.get('format')
        if mn is not None or mx is not None or pat is not None or fmt == 'date-time':
            def c_str(x, path, mn=mn, mx=mx, pat=pat, fmt=fmt):
                if not isinstance(x, str):
                    return None
                n = len(x)
                if mn is not None and n < mn:
                    return (path, 'minLength')
                if mx is not None and n > mx:
                    return (path, 'maxLength')
                if pat is not None and not pat.search(x):
                    return (path, 'pattern')
                if fmt == 'date-time' and not is_datetime(x):
                    return (path, 'format')
                return None
            add(c_str)

        # números
        lo, hi = node.get('minimum'), node.get('maximum')
        xlo, xhi = node.get('exclusiveMinimum'), node.get('exclusiveMaximum')
        if lo is not None or hi is not None or xlo is not None or xhi is not None:
            def c_num(x, path, lo=lo, hi=hi, xlo=xlo, xhi=xhi):
                if not _is_number(x):
                    return None
                if lo is not None and x < lo:
                    return (path, 'minimum')
                if hi is not None and x > hi:
                    return (path, 'maximum')
                if xlo is not None and x <= xlo:
                    return (path, 'exclusiveMinimum')
                if xhi is not None and x >= xhi:
                    return (path, 'exclusiveMaximum')
                return None
            add(c_num)

        # objetos
        props = {k: self.compile(v) for k, v in (node.get('properties') or {}).items()}
        req = list(node.get('required') or [])
        addl = node.get('additionalProperties', True)
        addl_fn = self.compile(addl) if isinstance(addl, dict) else None
        maxp = node.get('maxProperties')
        if props or req or addl is not True or maxp is not None:
            known = frozenset(props)

            def c_obj(x, path, props=props, req=req, addl=addl, addl_fn=addl_fn, known=known, maxp=maxp):
                if not isinstance(x, dict):
                    return None
                for k in req:
                    if k not in x:
                        return (path + (k,), 'required')
                if maxp is not None and len(x) > maxp:
                    return (path, 'maxProperties')
                for k, v in x.items():
                    f = props.get(k)
                    if f is not None:
                        e = f(v, path + (k,))
                        if e:
                            return e
                    elif addl is False:
                        return (path + (k,), 'additionalProperties')
                    elif addl_fn is not None:
                        e = addl_fn(v, path + (k,))
                        if e:
                            return e
                return None
            add(c_obj)

        # arreglos
        pre = [self.compile(s) for s in node.get('prefixItems') or []]
        items = node.get('items')
        items_fn = self.compile(items) if isinstance(items, dict) else None
        mi, ma, uq = node.get('minItems'), node.get('maxItems'), node.get('uniqueItems')
        if pre or items_fn is not None or mi is not None or ma is not None or uq:
            def c_arr(x, path, pre=pre, items_fn=items_fn, mi=mi, ma=ma, uq=uq):
                if not isinstance(x, list):
                    return None
                n = len(x)
                if mi is not None and n < mi:
                    return (path, 'minItems')
                if ma is not None and n > ma:
                    return (path, 'maxItems')
                for i, v in enumerate(x):
                    f = pre[i] if i < len(pre) else items_fn
                    if f is not None:
                        e = f(v, path + (i,))
                        if e:
                            return e
                if uq:
                    for i in range(n):
                        for j in range(i + 1, n):
                            if _eq(x[i], x[j]):
                                return (path, 'uniqueItems')
                return None
            add(c_arr)

        # combinadores
        for s in node.get('allOf') or []:
            add(self.compile(s))
        if 'anyOf' in node:
            alts = [self.compile(s) for s in node['anyOf']]
            add(lambda x, path, alts=alts: None if any(a(x, path) is None for a in alts) else (path, 'anyOf'))
        if 'oneOf' in node:
            alts = [self.compile(s) for s in node['oneOf']]
            disc = self._discriminator(node['oneOf'])

            def c_one(x, path, alts=alts, disc=disc):
                if disc is not None and isinstance(x, dict):
                    # cada alternativa fija `type` con const: solo puede pasar la que coincide (las demás fallan
                    # en const) → misma respuesta que evaluarlas todas, sin el costo
                    i = disc.get(x.get('type')) if isinstance(x.get('type'), str) else None
                    if i is None:
                        return (path, 'oneOf')
                    return alts[i](x, path)          # el error de la alternativa que corresponde (más útil)
                ok = 0
                for a in alts:
                    if a(x, path) is None:
                        ok += 1
                        if ok > 1:
                            return (path, 'oneOf')
                return None if ok == 1 else (path, 'oneOf')
            add(c_one)
        if 'not' in node:
            nf = self.compile(node['not'])
            add(lambda x, path, nf=nf: (path, 'not') if nf(x, path) is None else None)
        if 'if' in node:
            iff = self.compile(node['if'])
            thn = self.compile(node['then']) if 'then' in node else None
            els = self.compile(node['else']) if 'else' in node else None

            def c_if(x, path, iff=iff, thn=thn, els=els):
                if iff(x, path) is None:
                    return thn(x, path) if thn is not None else None
                return els(x, path) if els is not None else None
            add(c_if)

        if node.get('unevaluatedProperties') is False:
            ev = frozenset(self._evaluated(node))

            def c_uneval(x, path, ev=ev):
                if isinstance(x, dict):
                    for k in x:
                        if k not in ev:
                            return (path + (k,), 'unevaluatedProperties')
                return None
            add(c_uneval)

        if len(checks) == 1:
            return checks[0]

        def run(x, path, checks=tuple(checks)):
            for c in checks:
                e = c(x, path)
                if e:
                    return e
            return None
        return run

    def _discriminator(self, alts):
        """{type const: índice} si TODAS las alternativas son $ref a un esquema con properties.type.const único."""
        out = {}
        for i, s in enumerate(alts):
            if not (isinstance(s, dict) and set(s) == {'$ref'}):
                return None
            d = self.defs.get(s['$ref'].rsplit('/', 1)[1]) or {}
            c = ((d.get('properties') or {}).get('type') or {}).get('const')
            # la alternativa debe EXIGIR 'type' (vía BlockBase) para que un objeto sin type falle en todas
            if not isinstance(c, str) or c in out or not self._requires_type(d):
                return None
            out[c] = i
        return out

    def _requires_type(self, d, depth=0):
        if 'type' in (d.get('required') or []):
            return True
        if depth > 3:
            return False
        for s in d.get('allOf') or []:
            if '$ref' in s:
                if self._requires_type(self.defs.get(s['$ref'].rsplit('/', 1)[1]) or {}, depth + 1):
                    return True
            elif self._requires_type(s, depth + 1):
                return True
        return False


_LOCK = threading.Lock()
_VALIDATORS = {}


def validator(def_name='Envelope'):
    """Función compilada f(instancia, ruta) → None | (ruta, palabra_clave) para una definición del esquema."""
    f = _VALIDATORS.get(def_name)
    if f is not None:
        return f
    with _LOCK:
        if def_name not in _VALIDATORS:
            comp = _VALIDATORS.get('__compiler__')
            if comp is None:
                comp = _Compiler(_schema.load())
                _VALIDATORS['__compiler__'] = comp
            _VALIDATORS[def_name] = comp.ref('#/$defs/' + def_name)
        return _VALIDATORS[def_name]


def errors(instance, def_name='Envelope'):
    """[(ruta, palabra_clave)] — vacío si es válido (el primer error encontrado, como en una puerta)."""
    e = validator(def_name)(instance, ())
    return [e] if e else []


def is_valid(instance, def_name='Envelope'):
    return validator(def_name)(instance, ()) is None
