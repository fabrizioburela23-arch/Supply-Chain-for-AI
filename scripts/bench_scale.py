"""scripts/bench_scale.py — banco de ESCALA de las vistas rápidas (EXPANSION_5K E0.1; port de exp5k/bench_hot.py).

Construye las vistas con el código REAL (GraphCore → Impact de todos los choques → grafo de lectores → tarjeta → NRS de
todas → modelo de estructura) sobre el grafo sintético de scripts/gen_synth_graph.py (levantamiento del catálogo a N
empresas) o sobre el catálogo real (--n 0, o N ≤ empresas del catálogo). SIN base de datos y SIN tocar data/: es una
medición, no cambia ningún número. Imprime UN objeto JSON en stdout (los avisos van a stderr):

    ms       tiempos de construcción (graph_core, impact = todos los choques, graph_view, card_build, structure =
             modelo del tensor, first_card_total = primera ficha tras una escritura, nrs_all, chokepoints,
             payloads, rho, pagerank, entities_index, detect_first)
    p        p50/p95/max por pedido (impact_payload precalculado, scenario, card, search = MCP search_companies,
             detect = detector del motor de contexto)
    bytes    tamaño JSON de /api/hot/factors, /api/matrix/metrics, /api/hot/nrs (todas), impacto y ficha p50
    rss_mb   memoria del proceso: start, imports, after_build, end y peak (VmHWM)

Uso:  python scripts/bench_scale.py [--n 5000] [--hub 0.0] [--seed 42] [--samples 200] [--repeat 1] [--no-structure]
                                    [--out x.json]
tests/test_scale_budget.py lo corre (solo con KH_SCALE=1) y compara con las metas de la tabla 1 del plan.
"""
import argparse
import gc
import json
import os
import platform
import random
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Antes de importar nada del repo: sin base, sin reloj, sin LISTEN (la medición no escribe ni escucha).
os.environ['KHIPU_SCHEDULER'] = 'off'
os.environ['HOTVIEWS_LISTEN'] = 'off'
os.environ.pop('DATABASE_URL', None)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _proc(key):
    try:
        with open('/proc/self/status', encoding='ascii') as fh:
            for line in fh:
                if line.startswith(key):
                    return round(int(line.split()[1]) / 1024, 1)
    except OSError:
        pass
    return None


def rss_mb():
    return _proc('VmRSS:')


def peak_mb():
    v = _proc('VmHWM:')
    if v is None:
        try:
            import resource
            v = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
        except Exception:  # noqa: BLE001
            v = None
    return v


def _pct(xs):
    if not xs:
        return None
    xs = sorted(xs)
    return {'p50': round(xs[len(xs) // 2], 3), 'p95': round(xs[min(len(xs) - 1, int(len(xs) * 0.95))], 3),
            'max': round(xs[-1], 3), 'n': len(xs)}


def _timed(fn):
    t = time.perf_counter()
    v = fn()
    return v, (time.perf_counter() - t) * 1000.0


def run(n=5000, hub=0.0, seed=42, samples=200, structure=True, repeat=1):
    """Mide y devuelve el dict del banco. `repeat` > 1: graph_core, impact, rho y pagerank se repiten y se informa el
    MÍNIMO (`ms_runs` trae todas las corridas); los p50/p95 por pedido, la corrida de p50 más bajo (menos ruido de
    otros procesos)."""
    repeat = max(1, int(repeat))
    R = {'n_requested': n, 'hub_bias': hub, 'seed': seed, 'repeat': repeat, 'python': platform.python_version(),
         'engine': os.getenv('MATRIX_ENGINE', 'sparse'), 'ms': {}, 'p': {}, 'bytes': {}, 'rss_mb': {}, 'errors': {}}
    R['rss_mb']['start'] = rss_mb()
    import numpy as np

    from core.hotviews import registry, signals, source
    from core.hotviews.views import graph as graph_view
    from core.hotviews.views import graph_core, impact
    from matrix import engine as E
    # lo que el servidor ya tiene importado (tensor._country → core.world → flask…, ~170 ms en frío): fuera de los
    # tiempos medidos, si no «structure» y «first_card_total» sumaban la importación
    import core.world  # noqa: F401
    from core.hotviews.views import card as _card  # noqa: F401
    from matrix import tensor as _tensor  # noqa: F401
    R['rss_mb']['imports'] = rss_mb()

    def stage(name, fn, reps=1):
        runs, v = [], None
        for _ in range(reps):
            gc.collect()
            v, ms = _timed(fn)
            runs.append(round(ms, 3))
        R['ms'][name] = min(runs)
        if reps > 1:
            R.setdefault('ms_runs', {})[name] = runs
        return v

    def best(loop, reps=None):
        """La corrida (de `repeat`) con el p50 más bajo: (_pct, extra de esa corrida)."""
        out = None
        for _ in range(repeat if reps is None else reps):
            ts, extra = loop()
            pc = _pct(ts)
            if out is None or (pc and pc['p50'] < out[0]['p50']):
                out = (pc, extra)
        return out

    n_catalog = len((source._snapshot_parsed()[0] or {}).get('nodes') or [])
    if not n or n <= n_catalog:
        data, R['graph'] = stage('read', source.load_snapshot), 'snapshot'
    else:
        sys.path.insert(0, os.path.join(ROOT, 'scripts'))
        import gen_synth_graph
        data = stage('read', lambda: gen_synth_graph.synth_graphdata(n, seed=seed, hub_bias=hub))
        R['graph'] = 'synthetic'
    R['n_ids'], R['n_triples'], R['n_factors'] = len(data.ids), len(data.triples), len(data.factors)

    core = stage('graph_core', lambda: graph_core.build(data), repeat)
    R['rho'] = (core.rho or {}).get('rho')
    imp = stage('impact', lambda: impact.build(core), repeat)
    R['impact_sources'] = len(imp.sources)
    gv = stage('graph_view', lambda: graph_view.build(data))
    rel, label = signals.release_hash()                  # el release VIGENTE: hot.graph() sirve esta generación
    g = registry.make(data, {'graph_core': core, 'impact': imp, 'graph': gv}, rel, label, dict(R['ms']),
                      {'graph_core': core.content_sha, 'impact': imp.content_sha})
    gv.attach(g)
    registry.publish(g)
    R['ms']['build_total'] = round(sum(R['ms'].get(k, 0.0) for k in ('graph_core', 'impact', 'graph_view')), 1)
    R['rss_mb']['after_build'] = rss_mb()

    rng = random.Random(1)
    srcs = list(imp.sources)
    sample = rng.sample(srcs, min(samples, len(srcs)))

    # ── ficha (tarjeta V3 + NRS + estructura) ──
    from core.hotviews import hot
    from core.hotviews.views import card
    rv = hot.graph(wait=False)
    R['reader_nodes'] = len(rv.nodes) if rv is not None else None      # los lectores ven ESTE grafo
    cv = stage('card_build', lambda: card.view(g))
    if structure:
        def fresh_structure():          # una construcción COMPLETA cada vez (sin el Ψ ni el modelo guardados)
            from matrix import tensor as _T
            with _T._LOCK:
                _T._PSI.update(key=None, val=None)
                _T._MODEL.update(m=None, key=None)
            return cv.structure_model()
        stage('structure', fresh_structure, repeat)                     # el tensor de flujo de la generación
    first = next((oid for oid in sample if oid in cv.cards), None)
    if first is not None:
        stage('first_card', lambda: cv.card(first, structure=structure))
        # = primera /api/hot/card tras una escritura: tarjetas + estructura + una ficha
        R['ms']['first_card_total'] = round(R['ms']['card_build'] + R['ms'].get('structure', 0.0)
                                            + R['ms']['first_card'], 1)
    nrs = stage('nrs_all', cv.nrs_all)
    R['nrs_n'] = len(nrs)
    def loop_card():
        ts, sz = [], []
        for oid in sample[:100]:
            if oid not in cv.cards:
                continue
            c, ms = _timed(lambda: cv.card(oid, structure=structure))
            ts.append(ms)
            sz.append(len(json.dumps(c, default=str)))
        return ts, sz
    R['p']['card'], sz = best(loop_card, reps=1)      # la 1.ª pasada: la ficha guarda lo ya armado
    R['bytes']['card_p50'] = sorted(sz)[len(sz) // 2] if sz else None

    # ── lecturas de la vista Impact ──
    def loop_impact():
        ts, sz = [], []
        for oid in sample:
            pl, ms = _timed(lambda: impact.impact_payload(core, imp, oid))
            ts.append(ms)
            sz.append(len(json.dumps(pl)))
        return ts, sz
    R['p']['impact_payload'], sz = best(loop_impact)
    R['bytes']['impact_p50'] = sorted(sz)[len(sz) // 2] if sz else None

    def loop_scenario():
        ts = []
        for oid in sample[:100]:
            x0 = np.zeros(len(core.ids))
            x0[core.idx[oid]] = 1.0
            x0[core.idx[sample[0]]] = 0.5
            _r, ms = _timed(lambda: impact.scenario(core, x0))
            ts.append(ms)
        return ts, None
    R['p']['scenario'], _sz = best(loop_scenario)
    _r, R['ms']['chokepoints'] = _timed(lambda: impact.chokepoints_payload(core, imp))
    mp, R['ms']['metrics_payload'] = _timed(lambda: impact.metrics_payload(core, imp))
    R['bytes']['metrics'] = len(json.dumps(mp, default=str))
    fp, R['ms']['factors_payload'] = _timed(lambda: graph_core.factors_payload(core))
    R['bytes']['factors'] = len(json.dumps(fp, default=str))
    R['bytes']['nrs_all'] = len(json.dumps({k: v['total'] for k, v in nrs.items()}))
    # E1.7: lo que pide el arranque con paginación (/api/hot/factors?limit=50, /api/matrix/metrics?top=100)
    R['bytes']['factors_limit50'] = len(json.dumps(fp[:50], default=str))
    try:
        from matrix.api import _metrics_top
        R['bytes']['metrics_top100'] = len(json.dumps(_metrics_top(mp, 100), default=str))
    except Exception as e:  # noqa: BLE001
        R['errors']['metrics_top'] = f'{type(e).__name__}: {e}'[:160]
    for name, fn in (('rho', lambda: E.spectral_radius(core.mats, factors=core.factors, idx=core.idx)),
                     ('pagerank', lambda: E.pagerank(core.agg))):
        try:
            stage(name, fn, repeat)
        except Exception as e:  # noqa: BLE001 — una firma movida no tumba el banco
            R['errors'][name] = f'{type(e).__name__}: {e}'[:160]

    # ── búsqueda (MCP search_companies, el camino real con contrato) y detector de contexto ──
    try:
        from core import entities
        from mcp_server import tools as T

        class _P:
            kind, id = 'mcp', 'bench'

            def has(self, _scope):
                return True

        class _Ctx:
            principal = _P()
        ctx = _Ctx()
        _r, R['ms']['entities_index'] = _timed(entities.get_index)
        qs = ['semi', 'battery', 'power', 'Nvidia', 'cloud']
        T.call('search_companies', {'query': 'warmup', 'limit': 10}, ctx, shape=True)
        def loop_search():
            ts = []
            for _rep in range(2):
                for q in qs:
                    _r, ms = _timed(lambda: T.call('search_companies', {'query': q, 'limit': 10}, ctx, shape=True))
                    ts.append(ms)
            return ts, None
        R['p']['search'], _sz = best(loop_search)
    except Exception as e:  # noqa: BLE001
        R['errors']['search'] = f'{type(e).__name__}: {e}'[:160]
    try:
        from core import context_engine as ce
        qs = ['¿Qué pasa con TSMC y Nvidia si China bloquea Taiwán?',
              '¿cuál es la empresa de baterías más grande del mundo?',
              'Compare ASML vs Applied Materials exposure to export controls',
              'how exposed is Microsoft to power shortages in Virginia data centers?']
        _r, R['ms']['detect_first'] = _timed(lambda: ce.detect(qs[0]))
        def loop_detect():
            ts = []
            for q in qs * 5:
                _r, ms = _timed(lambda: ce.detect(q))
                ts.append(ms)
            return ts, None
        R['p']['detect'], _sz = best(loop_detect)
    except Exception as e:  # noqa: BLE001
        R['errors']['detect'] = f'{type(e).__name__}: {e}'[:160]

    R['ms'] = {k: round(v, 3) for k, v in R['ms'].items()}
    R['rss_mb']['end'] = rss_mb()
    R['rss_mb']['peak'] = peak_mb()
    return R


def main(argv=None):
    ap = argparse.ArgumentParser(description='Banco de escala de las vistas rápidas (sin base, sin tocar data/).')
    ap.add_argument('--n', type=int, default=5000, help='empresas (0 o ≤ catálogo = el catálogo real)')
    ap.add_argument('--hub', type=float, default=0.0, help='variante "los hubs crecen" (0-1)')
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--samples', type=int, default=200)
    ap.add_argument('--repeat', type=int, default=1, help='repetir construcciones y lecturas; se toma la mejor')
    ap.add_argument('--no-structure', action='store_true', help='fichas sin el modelo de estructura (tensor)')
    ap.add_argument('--out', help='además, guardar el JSON en este archivo (nunca en data/)')
    a = ap.parse_args(argv)
    if a.out:
        out = os.path.abspath(a.out)
        if out.startswith(os.path.join(ROOT, 'data') + os.sep):
            ap.error('--out no puede estar en data/')
    R = run(n=a.n, hub=a.hub, seed=a.seed, samples=a.samples, structure=not a.no_structure, repeat=a.repeat)
    txt = json.dumps(R, indent=1, default=str, ensure_ascii=False)
    if a.out:
        with open(os.path.abspath(a.out), 'w', encoding='utf-8') as fh:
            fh.write(txt)
    print(txt)
    return 0


if __name__ == '__main__':
    sys.exit(main())
