"""scripts/gen_synth_graph.py — grafo SINTÉTICO de N empresas para pruebas de escala (EXPANSION_5K E0.1).

"Levantamiento aleatorio" (random lift) del snapshot real (data/grafo_v0.json): cada empresa real recibe ~N/937
copias (etiqueta inventada única, ticker `SY####`, mismas propiedades de texto → mismo tamaño por nodo); cada
vínculo real se replica entre copias de sus extremos, en ronda, para que cada copia herede el grado de su original.
Factores: los reales + variantes cuyos miembros son copias. Conserva (en esperanza) la distribución de grado, la
mezcla de tipos de relación y la de sectores. Es el port EN MEMORIA de exp5k/scripts/gen5k.py (misma secuencia de
la semilla → el mismo grafo que midió B_scale.md), sin escribir JS.

`hub_bias` > 0: probabilidad de que un extremo del vínculo replicado sea el ORIGINAL (variante "los hubs crecen").
Solo stdlib + json, determinista. NUNCA escribe en data/ (solo en --out).

Uso:  python scripts/gen_synth_graph.py --n 5000 [--hub 0.3] [--seed 42] --out <dir>   → <dir>/grafo.json + factors.json
"""
import argparse
import copy
import json
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

_SYL = ['va', 'ro', 'nex', 'tri', 'sol', 'mar', 'ka', 'lu', 'zen', 'or', 'qui', 'bel', 'tor', 'ix', 'an', 'del', 'fi',
        'gra', 'po', 'ser', 'vy', 'dra', 'mo', 'te', 'lin', 'cu', 'sa', 've', 'rho', 'tam']
_SUF = ['Systems', 'Industries', 'Materials', 'Energy', 'Semicon', 'Holdings', 'Logistics', 'Technologies', 'Robotics',
        'Power', 'Capital', 'Devices', 'Labs', 'Networks', 'Metals']


def _read_factors():
    with open(os.path.join(ROOT, 'data', 'multicapa_factors_seats.json'), encoding='utf-8') as fh:
        return json.load(fh)


def _read_snapshot():
    from core.hotviews import source
    g, _sha = source._snapshot_parsed()           # el accesor único del snapshot (solo lectura)
    return g


def lift(g, n_target=5000, seed=42, hub_bias=0.0, factors=None):
    """(g2, factors2): snapshot y factores levantados a `n_target` empresas. No modifica `g` ni `factors`.
    `g2` tiene la forma del snapshot; `factors2` la de data/multicapa_factors_seats.json."""
    rng = random.Random(seed)
    if factors is None:
        factors = _read_factors()
    nodes = list(g.get('nodes') or [])
    links = list(g.get('links') or [])
    n0 = len(nodes)
    extra = max(0, int(n_target) - n0)
    copies = {n['id']: [n['id']] for n in nodes}
    alloc = [extra // n0] * n0 if n0 else []
    if n0:
        for k in rng.sample(range(n0), extra - sum(alloc)):
            alloc[k] += 1
    used = set(str(n.get('label') or '').lower() for n in nodes)

    def name():
        while True:
            w = ''.join(rng.choice(_SYL) for _ in range(rng.randint(2, 4))).capitalize()
            lab = f'{w} {rng.choice(_SUF)}'
            if lab.lower() not in used:
                used.add(lab.lower())
                return lab

    new_nodes = []
    for k, n in enumerate(nodes):
        for _j in range(alloc[k]):
            c = copy.deepcopy(n)
            nid = f"S{len(new_nodes):05d}_{n['id'][:12]}"
            c['id'] = nid
            c['label'] = name()
            for f in ('listing', 'preipo'):
                c.pop(f, None)
            if c.get('mkt'):
                c['mkt'] = f'SY{len(new_nodes):04d}'
                c['ticker'] = f"{c['mkt']} · SYN"
            new_nodes.append(c)
            copies[n['id']].append(nid)

    # vínculos: réplicas entre copias, en ronda por extremo (cada copia hereda el grado de su original)
    seen = set((l['source'], l['target'], l.get('type') or 'supply') for l in links)
    mult = (n0 + len(new_nodes)) / n0 if n0 else 1.0
    cyc = {}

    def pick(x, side):
        grp = copies.get(x, [x])
        if hub_bias > 0 and rng.random() < hub_bias:
            return x
        clones = grp[1:]
        if not clones:
            return x
        st = cyc.get((x, side))
        if st is None or st[1] >= len(st[0]):
            order = clones[:]
            rng.shuffle(order)
            st = [order, 0]
            cyc[(x, side)] = st
        v = st[0][st[1]]
        st[1] += 1
        return v

    new_links = []
    for l in links:
        reps = int(mult) - 1 + (1 if rng.random() < (mult - int(mult)) else 0)
        for _ in range(reps):
            for _try in range(6):
                s, t = pick(l['source'], 'o'), pick(l['target'], 'i')
                key = (s, t, l.get('type') or 'supply')
                if s != t and key not in seen:
                    seen.add(key)
                    # lo que nodes/merge_graph.js exportaría de la fila [s, t, w, rel, type, {conf, verified}]
                    new_links.append({'source': s, 'target': t, 'w': l.get('w'), 'rel': l.get('rel') or '',
                                      'type': l.get('type') or 'supply', 'conf': l.get('conf', 1),
                                      'verified': bool(l.get('verified', True))})
                    break

    # factores: los reales + variantes sobre las copias (mismo número por empresa que hoy)
    facs = list(factors.get('factors') or [])
    nf_target = round(len(facs) * mult)
    outf = list(facs)
    k = 0
    while facs and len(outf) < nf_target:
        f = facs[k % len(facs)]
        k += 1
        mem = {}
        for m, c in (f.get('members') or {}).items():
            grp = copies.get(m, [m])
            mem[rng.choice(grp[1:] or grp)] = c
        outf.append(dict(f, id=f"{f['id']}_S{k}", label=f"{f['label']} · var {k}", members=mem))

    g2 = dict(g)
    g2['nodes'] = nodes + new_nodes
    g2['links'] = links + new_links
    counts = dict(g.get('counts') or {})
    counts.update({'nodes': len(g2['nodes']), 'links': len(g2['links'])})
    g2['counts'] = counts
    g2['source'] = f'synthetic lift n={n_target} seed={seed} hub={hub_bias} (gen_synth_graph.py)'
    factors2 = dict(factors, factors=outf)
    return g2, factors2


def synth_graphdata(n_target=5000, seed=42, hub_bias=0.0):
    """GraphData de core.hotviews.source del grafo levantado (sin base, sin tocar data/)."""
    from core.hotviews import source
    g2, f2 = lift(_read_snapshot(), n_target=n_target, seed=seed, hub_bias=hub_bias)
    return source.from_snapshot(g2, factors_data=f2)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Grafo sintético por levantamiento aleatorio (pruebas de escala).')
    ap.add_argument('--n', type=int, default=5000)
    ap.add_argument('--hub', type=float, default=0.0)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    out = os.path.abspath(a.out)
    if out == os.path.join(ROOT, 'data') or out.startswith(os.path.join(ROOT, 'data') + os.sep):
        ap.error('--out no puede ser data/ (nunca se pisa el catálogo real)')
    os.makedirs(out, exist_ok=True)
    g2, f2 = lift(_read_snapshot(), n_target=a.n, seed=a.seed, hub_bias=a.hub)
    with open(os.path.join(out, 'grafo.json'), 'w', encoding='utf-8') as fh:
        json.dump(g2, fh, ensure_ascii=False)
    with open(os.path.join(out, 'factors.json'), 'w', encoding='utf-8') as fh:
        json.dump(f2, fh, ensure_ascii=False)
    print(json.dumps({'nodes': len(g2['nodes']), 'links': len(g2['links']), 'factors': len(f2['factors']),
                      'memberships': sum(len(f.get('members') or {}) for f in f2['factors']), 'out': out}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
