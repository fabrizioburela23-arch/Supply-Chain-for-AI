"""matrix/engine.py — construcción, modulación y propagación de matrices.

Todo opera sobre la ontología (Postgres) como fuente de verdad:
- build_matrices(): matrices por rel_type desde los links VIGENTES
  (o vigentes en una fecha `as_of` — mismo time-travel que la ontología).
- active_factors()/modulate(): hiperaristas como moduladores M'=M∘(1+Σc·mask).
- propagate(): EL kernel de propagación de shocks (reemplaza a las 4
  implementaciones BFS divergentes del cliente).
- compute_metrics(): métricas por nodo (grado, tamaño de cascada, chokepoints).

N≈440 → matrices densas de numpy son triviales en memoria (~1.5 MB c/u).
"""
from datetime import datetime, timezone

import numpy as np
from sqlalchemy import select

from ontology.models import LinkRecord, ObjectRecord
from ontology.service import _links_active_at, _parse_dt

# Tipos de relación canónicos (Etapa 2). 'partner' es simétrico: se refleja.
REL_TYPES = ['supply', 'cloud', 'fab', 'license', 'partner', 'invest',
             'deploy', 'owns', 'ppa']
SYMMETRIC = {'partner'}

# Pesos por tipo para la propagación de DAÑO operativo: perder a tu proveedor
# de fab pega más que perder a un inversor. Ajustables por request.
DEFAULT_REL_WEIGHTS = {
    'supply': 1.0, 'fab': 1.0, 'cloud': 0.9, 'license': 0.8, 'ppa': 0.7,
    'deploy': 0.4, 'partner': 0.3, 'owns': 0.6, 'invest': 0.25,
}


def _utcnow():
    return datetime.now(timezone.utc)


def node_index(session):
    """Índice estable id→posición (orden alfabético de ids de objetos).

    Excluye tipos que NO son nodos del grafo económico: 'Simulation' (historial
    de simulaciones guardadas) y 'Factor' (hiperaristas moduladoras) — antes se
    colaban como filas/columnas fantasma en las matrices."""
    ids = [r for (r,) in session.execute(
        select(ObjectRecord.id)
        .where(ObjectRecord.type.notin_(('Simulation', 'Factor')))
        .order_by(ObjectRecord.id)).all()]
    return {oid: i for i, oid in enumerate(ids)}, ids


def build_matrices(session, as_of=None):
    """{rel_type: matriz NxN} con A[i,j]=peso i→j (i PROVEE a j).

    Sin as_of: lee la vista materializada (links vigentes ahora) — rápido.
    Con as_of: reconstruye por VALIDEZ desde events (time-travel real).
    """
    idx, ids = node_index(session)
    n = len(ids)
    mats = {r: np.zeros((n, n)) for r in REL_TYPES}

    if as_of is None:
        rows = session.scalars(
            select(LinkRecord).where(LinkRecord.valid_to.is_(None))).all()
        triples = ((l.source_id, l.target_id, l.rel_type,
                    float(l.weight or 2)) for l in rows)
    else:
        as_of_dt = _parse_dt(as_of)
        links = _links_active_at(session, as_of_dt)
        triples = ((l['source'], l['target'], l['rel_type'],
                    float(l.get('weight') or 2)) for l in links)

    for s, t, rel, w in triples:
        if rel not in mats or s not in idx or t not in idx:
            continue
        i, j = idx[s], idx[t]
        mats[rel][i, j] = max(mats[rel][i, j], w)
        if rel in SYMMETRIC:
            mats[rel][j, i] = max(mats[rel][j, i], w)
    return mats, idx, ids


def active_factors(session, as_of=None):
    """Hiperaristas activas: objetos type='Factor' + links 'affects' vigentes.

    Devuelve [{id, label, severity, members:{obj_id: coef}}]. El coeficiente
    es el weight del link 'affects' (>0 amplifica el daño, p.ej. 0.5 = +50%
    de sensibilidad de las dependencias del afectado mientras el factor rige).
    """
    factors = []
    if as_of is None:
        rows = session.scalars(select(LinkRecord).where(
            LinkRecord.rel_type == 'affects',
            LinkRecord.valid_to.is_(None))).all()
        links = [{'source': l.source_id, 'target': l.target_id,
                  'weight': float(l.weight or 1)} for l in rows]
    else:
        as_of_dt = _parse_dt(as_of)
        links = [{'source': l['source'], 'target': l['target'],
                  'weight': float(l.get('weight') or 1)}
                 for l in _links_active_at(session, as_of_dt)
                 if l['rel_type'] == 'affects']

    by_factor = {}
    for l in links:
        by_factor.setdefault(l['source'], {})[l['target']] = l['weight']
    if by_factor:
        objs = {o.id: o for o in session.scalars(select(ObjectRecord).where(
            ObjectRecord.id.in_(list(by_factor.keys())),
            ObjectRecord.type == 'Factor')).all()}
        for fid, members in by_factor.items():
            o = objs.get(fid)
            if not o:
                continue  # el source del 'affects' no es un Factor — ignorar
            props = o.properties or {}
            factors.append({'id': fid, 'label': o.label,
                            'severity': float(props.get('severity', 5)),
                            'members': members})
    return factors


def fragility(idx, factors):
    """Vector de FRAGILIDAD por nodo (1.0 baseline). Cada hiperarista activa
    aumenta la fragilidad de sus miembros: f = 1 + Σ coef·(severity/5). Un
    nodo frágil recibe MÁS daño de un mismo shock (se aplica en propagate,
    tras la normalización — por eso no se cancela como escalar una columna
    cruda antes de normalizar)."""
    n = len(idx)
    f = np.ones(n)
    for factor in factors or []:
        for oid, coef in factor['members'].items():
            if oid in idx:
                f[idx[oid]] += coef * (factor['severity'] / 5.0)
    return f


def modulate(mats, idx, factors):
    """Compat: para el endpoint que muestra la matriz 'modulada', devuelve las
    matrices con las columnas de los miembros escaladas por su fragilidad
    (visualmente = aristas más gruesas hacia el nodo frágil). La propagación
    real usa el vector fragility() para no perder el efecto en la
    normalización."""
    f = fragility(idx, factors)
    if (f == 1.0).all():
        return mats
    return {r: m * f[None, :] for r, m in mats.items()}


def _dependency_matrix(mats, rel_weights=None):
    """Matriz de transmisión de daño T[i,j] = cuánto del shock de i llega a j.

    Se normaliza POR TIPO de relación (no en agregado): dentro de cada tipo,
    la columna de j suma 1, así un proveedor ÚNICO en su tipo transmite ~todo
    (perder tu única fab pega fuerte; ser 1 de 10 proveedores pega poco).
    Luego se combinan los tipos ponderados por su criticidad (fab≈supply >
    invest). No se re-normaliza el agregado — un nodo puede depender de fab Y
    supply Y cloud a la vez; la propagación clampa a 1 por hop."""
    w = dict(DEFAULT_REL_WEIGHTS)
    if rel_weights:
        w.update(rel_weights)
    T = None
    for r, m in mats.items():
        col = m.sum(axis=0)
        col[col == 0] = 1.0
        Dr = (m / col[None, :]) * w.get(r, 0.5)   # columna normalizada × criticidad
        T = Dr if T is None else T + Dr
    return T


def propagate(mats, idx, ids, shock_ids, magnitude=1.0, damping=0.6,
              max_hops=6, threshold=0.01, rel_weights=None, frag=None):
    """EL kernel de propagación: shock en `shock_ids` → impacto 0..1 por nodo.

    impacto(hop k) = damping · Tᵀ·x_{k-1} · fragilidad; el impacto total por
    nodo es el MÁXIMO alcanzado por cualquier ruta (no la suma — evita doble
    conteo en diamantes). `frag`: vector de fragilidad por hiperaristas (de
    fragility()); si None, sin modulación. Devuelve (impactos dict id→pct
    0..100, orden de cascada)."""
    n = len(ids)
    D = _dependency_matrix(mats, rel_weights)
    fvec = frag if frag is not None else np.ones(n)
    x = np.zeros(n)
    for sid in shock_ids:
        if sid in idx:
            x[idx[sid]] = magnitude
    total = x.copy()
    order = []
    reached = set(np.nonzero(x)[0].tolist())
    cur = x
    for hop in range(1, max_hops + 1):
        cur = damping * (D.T @ cur) * fvec
        cur = np.minimum(cur, 1.0)
        cur[cur < threshold] = 0.0
        if not cur.any():
            break
        newly = [int(i) for i in np.argsort(-cur)
                 if cur[i] > 0 and i not in reached]
        for i in newly:
            reached.add(i)
            order.append({'id': ids[i], 'hop': hop,
                          'impact': round(float(min(1.0, cur[i])) * 100, 2)})
        total = np.maximum(total, cur)
    impacts = {ids[i]: round(float(min(1.0, total[i])) * 100, 2)
               for i in range(n) if total[i] > 0}
    return impacts, order


def compute_metrics(session, as_of=None):
    """Métricas por nodo: grado in/out ponderado, tamaño de cascada
    (¿a cuántos arrastra si cae?) y ranking de chokepoints."""
    mats, idx, ids = build_matrices(session, as_of=as_of)
    factors = active_factors(session, as_of=as_of)
    frag = fragility(idx, factors)
    agg = None
    for m in mats.values():
        agg = m.copy() if agg is None else agg + m
    out_w = agg.sum(axis=1)
    in_w = agg.sum(axis=0)
    metrics = {}
    for oid, i in idx.items():
        if out_w[i] == 0 and in_w[i] == 0:
            continue
        impacts, _ = propagate(mats, idx, ids, [oid], frag=frag)
        cascade = sum(1 for v in impacts.values() if v >= 1.0) - 1
        metrics[oid] = {
            'out_weight': round(float(out_w[i]), 2),
            'in_weight': round(float(in_w[i]), 2),
            'cascade_size': max(0, cascade),
        }
    ranked = sorted(metrics.items(), key=lambda kv: -kv[1]['cascade_size'])
    for rank, (oid, m) in enumerate(ranked, 1):
        m['chokepoint_rank'] = rank
    return metrics, factors
