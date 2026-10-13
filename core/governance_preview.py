"""core/governance_preview.py — "¿qué cambia para mí?" de una versión de artefacto ANTES de activarla (paso 12; pieza
mínima del flujo de gobernanza §5.3 de docs/INFRA_OPERATIVA.md).

    preview({'kernel.params': '2.0.0'}) → contrafactual sobre TODOS los choques de un nodo del grafo vigente:
      cuántos choques cambian, alcance medio antes/después, las 10 diferencias más grandes para las empresas de
      referencia (TSMC, Nvidia, ASML, SK Hynix, Microsoft, Apple), ranking de cuellos de botella antes/después, ρ, si
      el NRS cambia, y un resumen en lenguaje simple ES/EN.

Se calcula SIN cambiar el kernel vivo: `core.governance.counterfactual` hace que SOLO este hilo lea la otra versión
(las vistas publicadas, las decisiones y los demás hilos siguen con el release vigente). Mismo código que el
constructor de vistas (source → GraphCore → Impact), sobre la MISMA fuente (Postgres o el snapshot). Pesado (~0,3-1 s):
un cálculo a la vez y caché por (release vigente, selección, generación del grafo). Nunca IA. Nunca escribe nada.
"""
import threading
import time

REF_IDS = ('TSMC', 'Nvidia', 'ASML', 'SKHynix', 'Microsoft', 'Apple')
DELTA_PP = 0.5            # una víctima "cambia" si su impacto se mueve ≥ 0,5 puntos (o aparece/desaparece)
_LOCK = threading.Lock()
_CACHE = {}               # key → resultado
_CACHE_MAX = 6


def _build():
    from core.hotviews import source
    from core.hotviews.views import graph_core, impact
    data = source.load()
    core = graph_core.build(data)
    return data, core, impact.build(core)


def _params_diff(aid, sel_semver):
    from core import governance
    cur = governance.section(aid) if aid else {}
    new = governance.available_artifact(aid, sel_semver)['params']
    out = []
    for k in sorted(set(cur) | set(new)):
        a, b = cur.get(k, '∅'), new.get(k, '∅')
        if a != b:
            out.append({'key': k, 'before': a, 'after': b})
    return out


def _victims(imp, oid):
    hit = imp.victims.get(oid)
    if not hit:
        return {}
    return {k: p for k, p in zip(hit[0], hit[1]) if k != oid}


def _kernel_compare(before, after):
    (_d0, c0, i0), (_d1, c1, i1) = before, after
    srcs = sorted(set(i0.sources) | set(i1.sources))
    changed = higher = lower = 0
    victims_changed = set()
    for s in srcs:
        v0, v1 = _victims(i0, s), _victims(i1, s)
        diff = False
        for k in set(v0) | set(v1):
            if abs(v0.get(k, 0.0) - v1.get(k, 0.0)) >= DELTA_PP:
                diff = True
                victims_changed.add(k)
        changed += diff
        r0 = (i0.stats.get(s) or {}).get('reach_1', 0)
        r1 = (i1.stats.get(s) or {}).get('reach_1', 0)
        higher += r1 > r0
        lower += r1 < r0
    refs = []
    for oid in REF_IDS:
        if oid not in c0.idx or oid not in c1.idx:
            continue
        v0, v1 = _victims(i0, oid), _victims(i1, oid)
        deltas = sorted(((k, v0.get(k, 0.0), v1.get(k, 0.0)) for k in set(v0) | set(v1)),
                        key=lambda t: (-abs(t[2] - t[1]), t[0]))[:10]
        s0, s1 = i0.stats.get(oid) or {}, i1.stats.get(oid) or {}
        refs.append({'id': oid, 'label': c1.label(oid),
                     'reach_before': s0.get('reach_1', 0), 'reach_after': s1.get('reach_1', 0),
                     'reach10_before': s0.get('reach_10', 0), 'reach10_after': s1.get('reach_10', 0),
                     'sum_before': s0.get('sum_impact', 0.0), 'sum_after': s1.get('sum_impact', 0.0),
                     'top_changes': [{'id': k, 'label': c1.label(k), 'before': a, 'after': b,
                                      'delta': round(b - a, 2)} for k, a, b in deltas if abs(b - a) >= DELTA_PP]})

    def rank(imp):
        return [k for k, _m in sorted(imp.metrics.items(), key=lambda kv: kv[1]['chokepoint_rank'])[:10]]
    n0 = max(1, len(i0.sources))
    n1 = max(1, len(i1.sources))
    return {
        'shocks': len(srcs), 'shocks_changed': changed, 'reach_higher': higher, 'reach_lower': lower,
        'companies_with_changed_impact': len(victims_changed),
        'mean_reach_before': round(sum(st['reach_1'] for st in i0.stats.values()) / n0, 2),
        'mean_reach_after': round(sum(st['reach_1'] for st in i1.stats.values()) / n1, 2),
        'reference': refs,
        'chokepoints_before': [{'id': k, 'label': c0.label(k)} for k in rank(i0)],
        'chokepoints_after': [{'id': k, 'label': c1.label(k)} for k in rank(i1)],
        'rho_before': (c0.rho or {}).get('rho'), 'rho_after': (c1.rho or {}).get('rho'),
        'damping_rho_before': (c0.rho or {}).get('damping_rho'), 'damping_rho_after': (c1.rho or {}).get('damping_rho'),
        'frag_max_before': round(float(c0.frag.max()), 4) if len(c0.frag) else None,
        'frag_max_after': round(float(c1.frag.max()), 4) if len(c1.frag) else None,
    }


def _summary(aid, sv, doc, k, flags):
    es, en = [], []
    if doc.get('summary_es'):
        es.append(doc['summary_es'])
        en.append(doc.get('summary_en') or doc['summary_es'])
    if k:
        t = next((r for r in k['reference'] if r['id'] == 'TSMC'), None) or (k['reference'] or [None])[0]
        if t:
            es.append(f"Ejemplo: si cae {t['label']}, hoy se ven afectadas {t['reach_before']} empresas; con {sv}, "
                      f"{t['reach_after']} (con golpe fuerte, ≥10 %: {t['reach10_before']} → {t['reach10_after']}).")
            en.append(f"Example: if {t['label']} fails, {t['reach_before']} companies are affected today; with {sv}, "
                      f"{t['reach_after']} (hard hit, ≥10%: {t['reach10_before']} → {t['reach10_after']}).")
        es.append(f"Cambian {k['shocks_changed']} de {k['shocks']} simulaciones de caída; el alcance medio pasa de "
                  f"{k['mean_reach_before']} a {k['mean_reach_after']} empresas.")
        en.append(f"{k['shocks_changed']} of {k['shocks']} collapse simulations change; mean reach goes from "
                  f"{k['mean_reach_before']} to {k['mean_reach_after']} companies.")
    es.append('El NRS (riesgo de red) NO cambia.' if not flags['nrs_affected'] else
              'El NRS (riesgo de red) cambia con esta versión.')
    en.append('The NRS (network risk score) does NOT change.' if not flags['nrs_affected'] else
              'The NRS (network risk score) changes with this version.')
    es.append('Nada se borra: para deshacer, activa otra vez la versión anterior (queda registrado).')
    en.append('Nothing is deleted: to undo, activate the previous version again (it is recorded).')
    return ' '.join(es), ' '.join(en)


def preview(selection, focus=None):
    """{selection, release_hash, generation, params_diff, kernel?, nrs_affected, summary_es/en, for_me, compute_ms}.
    `focus` (paso 25): ids de las posiciones del usuario para «¿qué cambia para mí?» (sin ellas, las 10 empresas más
    críticas) — core/governance_flow.for_me."""
    from core import governance
    from core.hotviews import hot
    if not isinstance(selection, dict) or not selection:
        raise ValueError('selection vacía')
    sel = {str(a)[:48]: str(v)[:16] for a, v in selection.items()}
    docs = {a: governance.available_artifact(a, v) for a, v in sel.items()}          # LookupError si no existe
    rel = governance.active().release_hash
    try:
        gen = hot.graph(wait=False)
        gen = gen.generation if gen is not None else None
    except Exception:  # noqa: BLE001
        gen = None
    focus = [str(f)[:120] for f in (focus or ())][:25]
    key = (rel, tuple(sorted(sel.items())), gen, tuple(focus))
    hit = _CACHE.get(key)
    if hit is not None:
        return dict(hit, cached=True)
    with _LOCK:
        hit = _CACHE.get(key)
        if hit is not None:
            return dict(hit, cached=True)
        t0 = time.perf_counter()
        out = {'selection': sel, 'release_hash': rel, 'generation': gen,
               'active': {a: governance.artifact_semver(a) for a in sel},
               'params_diff': {a: _params_diff(a, v) for a, v in sel.items()},
               'changelog': {a: {'es': d['changelog_es'], 'en': d['changelog_en'], 'change_kind': d['change_kind'],
                                 'activation': d['activation']} for a, d in docs.items()}}
        flags = {'nrs_affected': 'nrs.formula' in sel}
        kern = None
        before = after = None
        if 'kernel.params' in sel:
            before = _build()
            with governance.counterfactual(sel):
                after = _build()
                from matrix import engine as E
                up_after = E.direction_up_enabled()
            from matrix import engine as E
            kern = _kernel_compare(before, after)
            kern['direction_up_before'] = E.direction_up_enabled()
            kern['direction_up_after'] = up_after
            kern['source'] = before[0].source
            kern['graph_version'] = before[0].graph_version
            out['kernel'] = kern
        out['nrs_affected'] = flags['nrs_affected']
        try:
            from core import governance_flow
            out['for_me'] = governance_flow.for_me(sel, before, after, focus)
        except Exception:  # noqa: BLE001
            out['for_me'] = None
        aid0 = next(iter(sel))
        out['summary_es'], out['summary_en'] = _summary(aid0, sel[aid0], docs[aid0], kern, flags)
        out['compute_ms'] = round((time.perf_counter() - t0) * 1000, 1)
        if len(_CACHE) >= _CACHE_MAX:
            _CACHE.pop(next(iter(_CACHE)))
        _CACHE[key] = out
        return dict(out, cached=False)


def reset():
    with _LOCK:
        _CACHE.clear()
