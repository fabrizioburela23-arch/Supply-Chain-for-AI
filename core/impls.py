"""core/impls.py — IMPLEMENTACIONES RETENIDAS (docs/INFRA_OPERATIVA.md §5.2 «Implementaciones retenidas»; paso 24).

Una decisión se repite con LO MISMO que la produjo: las entradas (libro), el grafo G(t, κ) (ontology/bitemporal), los
NÚMEROS del release que regía (gov_artifacts por hash) y el CÓDIGO determinista que la calculó. Este módulo es el
registro de ese código, por (tipo de cálculo, versión de la implementación):

    IMPLS['kernel.propagate'][1]   matrix.engine.propagate / propagate_block   (kernel.params por semver)
    IMPLS['nrs.formula'][1]        core.world.nrs_terms                        (nrs.formula)
    IMPLS['committee.*'][1]        research.committee (convicción, quórum, decisión, tamaño)  (policy.committee)
    IMPLS['broker.run_checks'][1]  brokerage.risk.run_checks                   (policy.broker_risk)
    IMPLS['numbers.guard'][1]      core.numbers.unsupported_in                 (policy.numbers_guard)
    IMPLS['gates.eval'][1]         core.gates.engine.run + report.build        (ontology.shapes: IR por hash)

Cada decisión anota en su manifiesto `impl` (p. ej. {'risk': 'run_checks@1', 'sizing': 'compute_sizing@1'}); STAMPS
traduce esa etiqueta a la entrada del registro. Así el replay NO depende de git.

Regla de versiones (§5.2): si un cambio de código altera una salida DORADA (tests/golden/impl_*.json,
tests/test_impl_registry.py), nace `@2` y `@1` se queda (copiado a core/impls_legacy/ con su prueba dorada). Mientras
eso no pase, `@1` = la función de hoy. Nunca IA.

Las constantes de política que los módulos asignan con `governance.bind` (umbrales del comité, topes del corretaje,
tolerancias del guardián, constantes NRS) NO siguen al contrafactual por hilo (son globales del módulo). `module_view`
arma una VISTA del módulo —copia de sus globales con esas constantes recalculadas desde los cuerpos del release
pedido + clones de sus funciones atados a esa copia—: el MISMO código corre con los números de entonces, sin tocar
el módulo vivo ni los demás hilos. Los parámetros que el código lee con `governance.param` (kernel) siguen a
`governance.pinned(arts)` en este hilo.
"""
import copy
import hashlib
import importlib
import json
import logging
import types
from contextlib import contextmanager
from dataclasses import dataclass, field

log = logging.getLogger('khipu')


@dataclass(frozen=True)
class Impl:
    key: str                      # tipo de cálculo
    version: int
    module: str
    attr: str
    artifact: str = None          # artefacto de gobernanza cuyos números usa (None = ninguno)
    reads: str = 'bind'           # 'bind' (constantes de módulo → module_view) | 'param' (governance.param → pinned)
    deterministic: bool = True
    es: str = ''
    en: str = ''
    stamps: tuple = field(default_factory=tuple)


_R = (
    Impl('kernel.propagate', 1, 'matrix.engine', 'propagate', 'kernel.params', 'param',
         es='Propagación de un choque por la red (el kernel): mismo cálculo que el mapa y las vistas rápidas.',
         en='Shock propagation through the network (the kernel): the same computation as the map and fast views.',
         stamps=('propagate@1',)),
    Impl('kernel.propagate_block', 1, 'matrix.engine', 'propagate_block', 'kernel.params', 'param',
         es='El mismo kernel en lote (varias fuentes o un factor disparado).',
         en='The same kernel in batch (several sources or a fired factor).'),
    Impl('nrs.formula', 1, 'core.world', 'nrs_terms', 'nrs.formula', 'bind',
         es='La fórmula NRS (riesgo de red de 0 a 100) con sus cinco términos.',
         en='The NRS formula (network risk 0-100) with its five terms.'),
    Impl('committee.conviction', 1, 'research.committee', 'conviction_by_horizon', 'policy.committee', 'bind',
         es='Convicción del comité por horizonte a partir de las conclusiones de los analistas.',
         en="Committee conviction per horizon from the analysts' conclusions.",
         stamps=('conviction_by_horizon@1',)),
    Impl('committee.quorum', 1, 'research.committee', 'quorum_check', 'policy.committee', 'bind',
         es='Quórum: analista fundamental + mínimo de analistas.', en='Quorum: fundamental analyst + minimum analysts.'),
    Impl('committee.decide', 1, 'research.committee', 'decide', 'policy.committee', 'bind',
         es='Decisión por umbrales (comprar, mantener, reducir, vender).', en='Threshold decision (buy, hold, trim, sell).',
         stamps=('committee-v1',)),
    Impl('committee.sizing', 1, 'research.committee', 'compute_sizing', 'policy.committee', 'bind',
         es='Tamaño de la posición por volatilidad (mitad si no está validado, topes del mandato).',
         en='Position size by volatility (half if not validated, mandate caps).', stamps=('compute_sizing@1',)),
    Impl('broker.run_checks', 1, 'brokerage.risk', 'run_checks', 'policy.broker_risk', 'bind',
         es='Controles de riesgo de una orden (topes, saldo, duplicados, horario…).',
         en='Risk checks of an order (caps, funds, duplicates, market hours…).', stamps=('run_checks@1',)),
    Impl('numbers.guard', 1, 'core.numbers', 'unsupported_in', 'policy.numbers_guard', 'bind',
         es='Guardián de cifras: ¿cada cifra del texto está en los datos que recibió la IA?',
         en='Figures guard: is every figure in the text present in the data the AI received?'),
    Impl('gates.eval', 1, 'core.gates.engine', 'run', 'ontology.shapes', 'param',
         es='Puertas de validación (reglas SHACL compiladas) sobre el grafo foco guardado.',
         en='Validation gates (compiled SHACL rules) over the stored focus graph.', stamps=('gate_eval@1',)),
    Impl('ledger.record', 1, 'core.decisions', 'record', None, 'bind',
         es='Escritura de la ficha en el libro (no es un cálculo: se verifica por hash).',
         en='Writing the record to the ledger (not a computation: verified by hash).', stamps=('record@1',)),
    Impl('governance.regression', 1, 'core.governance_flow', 'regress', 'kernel.params', 'param',
         es='Regresión contrafactual de gobernanza (choques de una empresa con y sin el cambio).',
         en='Governance counterfactual regression (single-company shocks with and without the change).',
         stamps=('gov-regression@1',)),
    Impl('portfolio.advice', 1, 'core.portfolio_advisor', 'analyze', None, 'bind', deterministic=False,
         es='Consejo de cartera: usa precios en vivo que no se guardan enteros (no repetible).',
         en='Portfolio advice: uses live prices that are not fully stored (not replayable).',
         stamps=('portfolio_advisor.analyze@1',)),
)

IMPLS = {}
STAMPS = {}
for _i in _R:
    IMPLS.setdefault(_i.key, {})[_i.version] = _i
    for _s in _i.stamps:
        STAMPS[_s] = (_i.key, _i.version)
del _i


def get(key, version=1):
    """El Impl registrado o LookupError (una decisión que cita una implementación que este código ya no tiene)."""
    try:
        return IMPLS[key][int(version)]
    except (KeyError, ValueError, TypeError):
        raise LookupError(f'implementación no retenida: {key}@{version}') from None


def resolve_stamp(stamp):
    """'run_checks@1' → Impl. Las acciones de la ontología ('CrearTesis@1') son escrituras, no cálculos: None."""
    if not stamp:
        return None
    ent = STAMPS.get(str(stamp))
    return get(*ent) if ent else None


def missing_for(manifest):
    """Etiquetas `impl` de un manifiesto que este código NO retiene (las de acciones de la ontología, 'CrearTesis@1',
    son escrituras y no cuentan; tampoco 'replay@1', la propia auditoría audit.replay, que es un registro y no un cálculo:
    antes caía en 'impl_missing' = «este despliegue no conserva el código», falso). Lo usa el replay y el 🩺 (§5.3: sin
    sus impl, el replay no puede repetir)."""
    out = []
    for role, stamp in sorted(((manifest or {}).get('impl') or {}).items()):
        s = str(stamp or '')
        if role in ('action', 'replay') or not s or s in STAMPS:
            continue
        out.append({'role': role, 'stamp': s})
    return out


def catalog(lang='es'):
    """Lista pública (para el 🩺 y las pruebas): qué implementaciones retiene este despliegue."""
    en = lang == 'en'
    return [{'key': i.key, 'version': i.version, 'function': f'{i.module}.{i.attr}', 'artifact': i.artifact,
             'deterministic': i.deterministic, 'stamps': list(i.stamps), 'about': i.en if en else i.es}
            for i in _R]


# ── vista de un módulo con los números de OTRO release ──────────────────────────────────────────────────────────
def _bindings_for(mod_name):
    from core import governance
    with governance._LOCK:
        return [(aid, spec) for (m, aid, spec) in governance._STATE['bindings'] if m == mod_name]


def module_view(mod_name, arts, notes=None):
    """SimpleNamespace con las funciones del módulo `mod_name` atadas a una COPIA de sus globales en la que las
    constantes de `governance.bind` salen de `arts` ({artifact_id: {params, …}}). Lo que `arts` no trae (o una clave
    que esa versión no tenía) queda con el valor vivo y se anota en `notes` (lista) — nunca se inventa."""
    mod = importlib.import_module(mod_name)
    g = dict(mod.__dict__)
    for aid, spec in _bindings_for(mod_name):
        a = (arts or {}).get(aid)
        if a is None:
            if notes is not None:
                notes.append({'module': mod_name, 'artifact': aid, 'note': 'artifact_not_in_release'})
            continue
        params = a.get('params') or {}
        for const, (key, conv) in spec.items():
            if key not in params:
                if notes is not None:
                    notes.append({'module': mod_name, 'artifact': aid, 'key': key, 'note': 'key_not_in_version'})
                continue
            v = copy.deepcopy(params[key])
            g[const] = conv(v) if conv else v
    for name, val in list(g.items()):
        if isinstance(val, types.FunctionType) and val.__module__ == mod_name:
            f = types.FunctionType(val.__code__, g, val.__name__, val.__defaults__, val.__closure__)
            f.__kwdefaults__ = copy.copy(val.__kwdefaults__)
            f.__dict__.update(val.__dict__)
            g[name] = f
    return types.SimpleNamespace(**{k: v for k, v in g.items() if not k.startswith('__')}, __globals__=g)


def view_with(view, **overrides):
    """La misma vista con nombres reemplazados (p. ej. `trading_enabled` → el valor que regía): las funciones de la
    vista leen sus globales en `view.__globals__`, así que el cambio las alcanza a todas."""
    g = view.__globals__
    g.update(overrides)
    for k, v in overrides.items():
        setattr(view, k, v)
    return view


@contextmanager
def under(arts):
    """Este hilo lee `governance.param` desde `arts` (kernel.params, ontology.shapes, policy.gates…)."""
    from core import governance
    with governance.pinned(arts or {}):
        yield


# ── huellas de salida (comparación exacta, rtol = 0) ────────────────────────────────────────────────────────────
def sha(obj):
    from core.decisions import canonical
    from core.decision_sites import clean
    return hashlib.sha256(canonical(clean(obj))).hexdigest()


def diff(a, b, path='', out=None, limit=40):
    """Diferencias campo a campo entre lo REGISTRADO (a) y lo REPETIDO (b): [{path, recorded, replayed}]."""
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            diff(a.get(k, '∅'), b.get(k, '∅'), f'{path}.{k}' if path else str(k), out, limit)
        return out
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if len(a) != len(b):
            out.append({'path': path + '.length', 'recorded': len(a), 'replayed': len(b)})
        for i, (x, y) in enumerate(zip(a, b)):
            diff(x, y, f'{path}[{i}]', out, limit)
        return out
    if _norm(a) != _norm(b):
        out.append({'path': path, 'recorded': _short(a), 'replayed': _short(b)})
    return out


def _norm(v):
    if isinstance(v, bool) or v is None or isinstance(v, str):
        return v
    if isinstance(v, (int, float)):
        return float(v)
    return json.dumps(v, sort_keys=True, default=str)


def _short(v):
    s = v if isinstance(v, (int, float, bool)) or v is None else str(v)
    return s[:160] if isinstance(s, str) else s


# ── corridas doradas (tests/test_impl_registry.py) ──────────────────────────────────────────────────────────────
GOLDEN_CASES = ('kernel.propagate', 'nrs.formula', 'committee.conviction', 'committee.quorum', 'committee.decide',
                'committee.sizing', 'broker.run_checks', 'numbers.guard', 'gates.eval')


def golden_run(key, version, arts):
    """Salida de `key@version` sobre entradas FIJAS (sin base, sin red) con los cuerpos `arts`. La prueba dorada
    compara su huella con tests/golden/impl_<key>@<v>.json: si cambia, el código cambió el resultado → @2."""
    get(key, version)
    from core.decision_sites import clean
    if key == 'kernel.propagate':
        import numpy as np

        from matrix import engine as E
        ids = ['A', 'B', 'C', 'D']
        idx = {k: i for i, k in enumerate(ids)}
        tri = [('A', 'B', 'supply', 6.0), ('B', 'C', 'fab', 4.0), ('A', 'C', 'cloud', 2.0), ('C', 'D', 'supply', 3.0),
               ('D', 'B', 'partner', 1.0)]
        with under(arts):
            mats, _, _ = E.build_matrices_from_triples(tri, idx, sparse=None)
            frag = E.fragility(idx, [{'id': 'F', 'severity': 4.0, 'members': {'B': 0.8}}])
            imp, order = E.propagate(mats, idx, ids, ['A'], frag=frag)
            dt = E.dependency_transpose(mats)
            tot, first = E.propagate_block(dt, frag, np.array([1.0, 0.0, 0.5, 0.0]))
        return clean({'impacts': imp, 'order': order, 'block': [round(float(x), 12) for x in tot[:, 0]],
                      'first': [int(x) for x in first[:, 0]]})
    if key == 'nrs.formula':
        w = module_view('core.world', arts)
        nodes = [({'id': 'X1', 'country': 'Taiwan', 'margin': 0.12, 'growth': 'red', 'preipo': False}, 7),
                 ({'id': 'X2', 'country': 'EEUU', 'margin': 0.4, 'cat': 'foundry'}, 2),
                 ({'id': 'X3', 'country': 'Japón'}, 0)]
        return clean([w.nrs_terms(n, d, params=None) for n, d in nodes])
    if key.startswith('committee.'):
        c = module_view('research.committee', arts)
        if key == 'committee.conviction':
            claims = [{'id': 'c1', 'agent_type': 'fundamental', 'stance': 'positive', 'horizon': 'LONG_TERM',
                       'confidence': 0.7},
                      {'id': 'c2', 'agent_type': 'technical', 'stance': 'negative', 'horizon': 'SHORT_TERM',
                       'confidence': 0.6},
                      {'id': 'c3', 'agent_type': 'news', 'stance': 'positive', 'horizon': 'MEDIUM_TERM',
                       'confidence': 0.55}]
            return clean(c.conviction_by_horizon(claims, contradicted_ids={'c2'}))
        if key == 'committee.quorum':
            return clean([c.quorum_check({'fundamental', 'technical', 'news'}), c.quorum_check({'technical'})])
        if key == 'committee.decide':
            return clean([c.decide(40.0, target_w=0.05), c.decide(-30.0, has_position=True, current_w=0.04,
                                                                  target_w=0.05), c.decide(10.0)])
        mandate = {'risk_budget': 0.01, 'max_position': 0.1, 'min_vol': 0.15, 'max_order_usd': 5000.0,
                   'daily_remaining_usd': 20000.0}
        return clean([c.compute_sizing('BUY', 35.0, mandate, equity=100000.0, price=120.0, validated=False),
                      c.compute_sizing('TRIM', 25.0, mandate, equity=50000.0, current_value=9000.0, current_qty=50,
                                       price=180.0, trim_reason='conviction'),
                      c.compute_sizing('HOLD', None, mandate)])
    if key == 'broker.run_checks':
        r = module_view('brokerage.risk', arts)
        view_with(r, trading_enabled=lambda: True, live_env_enabled=lambda: False)
        ctx = {'client': {'status': 'active', 'mode': 'paper', 'live_enabled': False, 'connected': True,
                          'risk_profile': 'moderado', 'risk_limits': {}, 'mandate': {}, 'hwm_equity': 100000.0},
               'order': {'symbol': 'AMD', 'side': 'buy', 'notional': 6000.0, 'qty': None, 'order_type': 'market',
                         'limit_price': None},
               'account': {'equity': 100000.0, 'cash': 50000.0, 'buying_power': 50000.0}, 'account_error': None,
               'positions': [], 'price': 150.0, 'ref_price': 150.0, 'est_usd': 6000.0, 'daily_used_usd': 0.0,
               'recent_duplicate': False, 'unresolved_order': False, 'market_open': True, 'clock_source': 'alpaca',
               'policy': {}}
        return clean([{k: x.get(k) for k in ('name', 'ok', 'severity', 'detail')} for x in r.run_checks(ctx)])
    if key == 'numbers.guard':
        nmod = module_view('core.numbers', arts)
        data = 'Nvidia cotiza a 182,40 USD; capitalización de 4,4 billones; margen bruto 74 %.'
        text = 'Nvidia vale 182 USD, su margen es 74 % y crece 35 % al año; cotiza a 233,95 USD.'
        return clean(nmod.unsupported_in(text, data))
    if key == 'gates.eval':
        from core.gates import engine as GE
        from core.gates import focus as F
        from core.gates import report as GR
        art = (arts or {}).get('ontology.shapes')
        comp = GE.compile_ir(art['params']['ir'])
        comp.semver = art['semver']
        t, foc = F.link_triples({'id': 'L1', 'source': 'TSMC', 'target': 'TSMC', 'rel_type': 'supply', 'weight': 9,
                                 'valid_from': '2020-01-01T00:00:00+00:00', 'valid_to': '2019-01-01T00:00:00+00:00'})
        rep = GR.build('ontology.g1.link', GE.run(comp, t), comp, 'shadow', {}, focus=foc)
        return clean({k: rep[k] for k in ('outcome', 'conforms', 'by_rule', 'n_results')} |
                     {'results': [{k: r[k] for k in ('rule', 'severity', 'effective', 'value', 'limit')}
                                  for r in rep['results']]})
    raise LookupError(f'sin caso dorado para {key}')


def repo_arts(selection=None):
    """Cuerpos del repositorio (verificados por hash) del release propuesto (manifest.json, sin selección por entorno),
    con `selection` {aid: semver} encima. Lo usan las pruebas doradas (sin base)."""
    from core import governance
    governance.repo_bundle()
    arts = {aid: dict(v) for aid, v in (governance._STATE.get('repo_plain') or {}).items()}
    for aid, sv in (selection or {}).items():
        arts[aid] = governance.available_artifact(aid, sv)
    return arts
