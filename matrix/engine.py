"""matrix/engine.py — construcción, modulación y propagación de matrices.

Todo opera sobre la ontología (Postgres) como fuente de verdad:
- build_matrices(): matrices por rel_type desde los links VIGENTES
  (o vigentes en una fecha `as_of` — mismo time-travel que la ontología).
- active_factors()/modulate(): hiperaristas como moduladores M'=M∘(1+Σc·mask).
- propagate(): EL kernel de propagación de shocks (reemplaza a las 4
  implementaciones BFS divergentes del cliente).
- compute_metrics(): métricas por nodo (grado, cascada, chokepoints, PageRank).

── DENSO vs DISPERSO (spec_matrices_dispersas_centralidad) ──
El motor soporta DOS representaciones de las matrices NxN con UN SOLO kernel:
- Densa (numpy)  — viable con cientos/miles de nodos; comportamiento histórico.
- Dispersa (scipy.sparse CSR) — para escalar a decenas de miles de nodos, donde
  una NxN densa (50k×50k = 20 GB) es inviable.
La representación se elige por `MATRIX_ENGINE` (env: 'dense' por defecto,
'sparse' para activar el motor disperso) o por el parámetro `sparse=` explícito.
El camino DENSO es idéntico bit a bit al histórico (los tests con DB son el
árbitro); el DISPERSO se valida contra el denso por un test de equivalencia
(numpy.allclose) — ver tests/test_matrix_sparse.py. Regla de oro del port a
sparse: NADA de .toarray()/.todense() en rutas calientes; la normalización por
columna se hace con escalado diagonal (m @ diags(1/col)), no con broadcasting.
"""
import logging
import os
from datetime import datetime, timezone

import numpy as np
from sqlalchemy import select

# scipy es OPCIONAL (patrón "todo opcional" del proyecto): el camino DENSO
# funciona sin él; el DISPERSO lo requiere. Sin scipy, _use_sparse() → False y
# el motor sigue en modo denso sin romper nada.
try:
    import scipy.sparse as sp
except Exception:  # noqa: BLE001
    sp = None

from ontology.models import LinkRecord, ObjectRecord
from ontology.service import _links_active_at, _parse_dt

log = logging.getLogger('matrix.engine')

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

# Fuentes de importación EN BULTO (capa ancha Wikidata/GLEIF): sus relaciones
# binarias no traen un peso equivalente al de las relaciones curadas a mano, así
# que reciben un peso descontado y parametrizable (spec §"Ponderación de datos
# importados en bulto"). Se marca la procedencia en LinkRecord.properties.source.
BULK_SOURCES = {'wikidata', 'gleif'}


def _utcnow():
    return datetime.now(timezone.utc)


# ── configuración por entorno ──────────────────────────────────────────────
def _use_sparse():
    """¿Usar matrices dispersas? Flag de corte (spec §"Plan de despliegue
    seguro"): default DENSO en producción hasta validar el motor disperso en
    paralelo; se activa con MATRIX_ENGINE=sparse sin quitar el motor denso."""
    return sp is not None and os.getenv('MATRIX_ENGINE', 'dense').strip().lower() == 'sparse'


def bulk_weight_factor():
    """Factor de descuento para links importados en bulto (default 0.5 = 50%
    del peso de una relación curada del mismo tipo). Parametrizable, NO
    hardcodeado: env IMPORT_BULK_WEIGHT_FACTOR ∈ [0,1]."""
    try:
        v = float(os.getenv('IMPORT_BULK_WEIGHT_FACTOR', '0.5'))
    except (TypeError, ValueError):
        v = 0.5
    return min(1.0, max(0.0, v))


def _eff_weight(raw, source):
    """Peso efectivo de un link: preserva EXACTO el histórico `float(w or 2)`
    (peso por defecto 2 si es None/0), y aplica el descuento de bulto SOLO a
    fuentes importadas — las curadas no se tocan, así el camino denso sigue
    idéntico y la equivalencia con el sparse se mantiene."""
    w = float(raw or 2)
    if source in BULK_SOURCES:
        w *= bulk_weight_factor()
    return w


# ── helpers polimórficos densa (numpy) ↔ dispersa (scipy CSR) ──────────────
# Un solo kernel para ambas representaciones. Para la densa hacen exactamente
# lo que hacía el código histórico; para la dispersa evitan densificar.
def _issparse(m):
    return sp is not None and sp.issparse(m)


def _colsum(m):
    """Suma por columna → vector 1D denso (sparse.sum devuelve np.matrix)."""
    return np.asarray(m.sum(axis=0)).ravel()


def _rowsum(m):
    """Suma por fila → vector 1D denso."""
    return np.asarray(m.sum(axis=1)).ravel()


def _scale_cols(m, v):
    """Columna j escalada por v[j]. Denso: m * v[None,:] (idéntico al histórico).
    Sparse: m @ diags(v) — escalado diagonal, SIN broadcasting (que densificaría)."""
    if _issparse(m):
        return (m @ sp.diags(np.asarray(v, dtype=float))).tocsr()
    return m * np.asarray(v)[None, :]


def _scale_rows(m, v):
    """Fila i escalada por v[i]. Denso: v[:,None]*m. Sparse: diags(v) @ m."""
    if _issparse(m):
        return (sp.diags(np.asarray(v, dtype=float)) @ m).tocsr()
    return np.asarray(v)[:, None] * m


def _transpose_csr(m):
    """Transpuesta lista para producto: CSR (sparse) o vista .T (densa).
    En el kernel se precalcula UNA vez por reconstrucción, no dentro del loop."""
    if _issparse(m):
        return m.T.tocsr()
    return m.T


# ── índice de nodos + caché con invalidación por época del grafo ───────────
def node_index(session, as_of=None):
    """Índice estable id→posición (orden alfabético de ids de objetos).

    Excluye tipos que NO son nodos del grafo económico: 'Simulation' (historial
    de simulaciones guardadas) y 'Factor' (hiperaristas moduladoras) — antes se
    colaban como filas/columnas fantasma en las matrices.

    Cacheado por (época del grafo, as_of): a escala grande, reconstruir el
    índice desde Postgres en CADA request es el cuello de botella real, no la
    matemática (spec §"Estabilidad estructural"). La época cambia con cualquier
    escritura de eventos → invalida sin tocar nada más."""
    ck = ('nodeidx', _graph_epoch(session), as_of or 'now')
    hit = _cache_get(ck)
    if hit is not None:
        return hit
    ids = [r for (r,) in session.execute(
        select(ObjectRecord.id)
        .where(ObjectRecord.type.notin_(('Simulation', 'Factor')))
        .order_by(ObjectRecord.id)).all()]
    out = ({oid: i for i, oid in enumerate(ids)}, ids)
    _cache_set(ck, out)
    return out


def build_matrices_from_triples(triples, idx, sparse=None):
    """NÚCLEO NUMÉRICO puro (sin DB): {rel_type: matriz NxN} desde triples
    (source, target, rel, weight). Igual semántica que el histórico —
    A[i,j]=peso i→j, MÁXIMO en colisiones de par, simetría para 'partner'.

    CRÍTICO para la equivalencia densa/sparse: el histórico hace `max(existing,
    w)` sobre pares repetidos. COO→CSR SUMA los duplicados. Por eso se deduplica
    por MÁXIMO en un dict ANTES de construir la COO (una sola conversión), no se
    inserta elemento por elemento (O(n) por inserción en CSR/LIL)."""
    if sparse is None:
        sparse = _use_sparse()
    n = len(idx)
    # dedupe-por-máximo: best[rel][(i,j)] = mayor peso visto (preserva `max`)
    best = {r: {} for r in REL_TYPES}
    for s, t, rel, w in triples:
        d = best.get(rel)
        if d is None or s not in idx or t not in idx:
            continue
        i, j = idx[s], idx[t]
        if (i, j) not in d or w > d[(i, j)]:
            d[(i, j)] = w
        if rel in SYMMETRIC and ((j, i) not in d or w > d[(j, i)]):
            d[(j, i)] = w
    mats = {}
    for rel in REL_TYPES:
        d = best[rel]
        if sparse:
            if d:
                ij = np.fromiter((c for pair in d for c in pair), dtype=np.int64).reshape(-1, 2)
                data = np.fromiter(d.values(), dtype=float, count=len(d))
                m = sp.coo_matrix((data, (ij[:, 0], ij[:, 1])), shape=(n, n)).tocsr()
                m.sum_duplicates()   # no-op (claves únicas) pero deja forma canónica
                m.eliminate_zeros()
            else:
                m = sp.csr_matrix((n, n))
        else:
            m = np.zeros((n, n))
            for (i, j), w in d.items():
                m[i, j] = w
        mats[rel] = m
    ids = [None] * n
    for oid, i in idx.items():
        ids[i] = oid
    return mats, idx, ids


def build_matrices(session, as_of=None, sparse=None):
    """{rel_type: matriz NxN} con A[i,j]=peso i→j (i PROVEE a j).

    Sin as_of: lee la vista materializada (links vigentes ahora) — rápido.
    Con as_of: reconstruye por VALIDEZ desde events (time-travel real).
    `sparse`: None → flag MATRIX_ENGINE; True/False fuerza la representación.
    Aplica el descuento de procedencia (bulto vs curado) en la lectura, así el
    núcleo numérico permanece agnóstico al peso y ambos caminos coinciden."""
    idx, ids = node_index(session, as_of=as_of)
    if as_of is None:
        rows = session.scalars(
            select(LinkRecord).where(LinkRecord.valid_to.is_(None))).all()
        triples = ((l.source_id, l.target_id, l.rel_type,
                    _eff_weight(l.weight, (l.properties or {}).get('source')))
                   for l in rows)
    else:
        as_of_dt = _parse_dt(as_of)
        links = _links_active_at(session, as_of_dt)
        triples = ((l['source'], l['target'], l['rel_type'],
                    _eff_weight(l.get('weight'), (l.get('properties') or {}).get('source')))
                   for l in links)
    return build_matrices_from_triples(triples, idx, sparse=sparse)


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
    return {r: _scale_cols(m, f) for r, m in mats.items()}


def _dependency_matrix(mats, rel_weights=None):
    """Matriz de transmisión de daño T[i,j] = cuánto del shock de i llega a j.

    Se normaliza POR TIPO de relación (no en agregado): dentro de cada tipo,
    la columna de j suma 1, así un proveedor ÚNICO en su tipo transmite ~todo
    (perder tu única fab pega fuerte; ser 1 de 10 proveedores pega poco).
    Luego se combinan los tipos ponderados por su criticidad (fab≈supply >
    invest). No se re-normaliza el agregado — un nodo puede depender de fab Y
    supply Y cloud a la vez; la propagación clampa a 1 por hop.

    Denso: (m / col[None,:]) * w — histórico. Sparse: m @ diags(w/col) — mismo
    resultado sin densificar (spec §"Detalles numéricos obligatorios")."""
    w = dict(DEFAULT_REL_WEIGHTS)
    if rel_weights:
        w.update(rel_weights)
    T = None
    for r, m in mats.items():
        col = _colsum(m)
        col[col == 0] = 1.0
        Dr = _scale_cols(m, w.get(r, 0.5) / col)   # columna normalizada × criticidad
        T = Dr if T is None else T + Dr
    return T


def propagate(mats, idx, ids, shock_ids, magnitude=1.0, damping=0.6,
              max_hops=6, threshold=0.01, rel_weights=None, frag=None,
              nonlinear=False, eps=None):
    """EL kernel de propagación: shock en `shock_ids` → impacto 0..1 por nodo.

    impacto(hop k) = damping · Tᵀ·x_{k-1} · fragilidad; el impacto total por
    nodo es el MÁXIMO alcanzado por cualquier ruta (no la suma — evita doble
    conteo en diamantes). `frag`: vector de fragilidad por hiperaristas (de
    fragility()); si None, sin modulación. Devuelve (impactos dict id→pct
    0..100, orden de cascada). Funciona con matrices densas o dispersas (Tᵀ se
    precalcula UNA vez, no dentro del loop de hops).

    Flags ADITIVOS (default apagados → comportamiento idéntico al histórico):
    - nonlinear: kernel no-lineal estilo Bardoscia 2015 (el daño transmitido
      satura con el distress del origen: x' = 1-exp(-x)); escenario estrés severo.
    - eps: criterio de convergencia explícito — corta cuando ‖Δ‖∞ < eps (con
      damping·ρ(T)<1 la convergencia geométrica está garantizada)."""
    n = len(ids)
    D = _dependency_matrix(mats, rel_weights)
    DT = _transpose_csr(D)
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
        prev = cur
        cur = damping * (DT @ cur) * fvec
        if nonlinear:
            cur = 1.0 - np.exp(-cur)     # saturación no-lineal (flag)
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
        if eps is not None and np.max(np.abs(cur - prev)) < eps:
            break
    impacts = {ids[i]: round(float(min(1.0, total[i])) * 100, 2)
               for i in range(n) if total[i] > 0}
    return impacts, order


def propagate_bands(mats, idx, ids, shock_ids, n_samples=200, seed=0,
                    mag_sigma=0.10, frag_sigma=0.10, frag=None, **kw):
    """BANDAS DE INCERTIDUMBRE Monte Carlo (spec §extensiones avanzadas, aditivo).
    Corre el kernel N veces perturbando la magnitud del shock y los coeficientes
    de fragilidad (ruido gaussiano relativo, semilla FIJA reproducible) y
    devuelve percentiles p5/p50/p95 por nodo además del punto estimado.

    Convierte "el impacto es 36" en "36 [28–45 al 90%]" — el lenguaje VaR/CVaR
    que espera un cliente quant. NO cambia `propagate()`: es una función aparte
    (opt-in), así los tests y callers existentes no se afectan."""
    rng = np.random.default_rng(seed)
    n = len(ids)
    base_frag = frag if frag is not None else np.ones(n)
    point, order = propagate(mats, idx, ids, shock_ids, frag=base_frag, **kw)
    samples = np.zeros((max(1, int(n_samples)), n))
    for s in range(samples.shape[0]):
        mag = float(kw.get('magnitude', 1.0)) * float(max(0.0, rng.normal(1.0, mag_sigma)))
        fs = base_frag * rng.normal(1.0, frag_sigma, size=n)
        fs = np.maximum(fs, 0.0)
        kw2 = dict(kw)
        kw2['magnitude'] = mag
        imp, _ = propagate(mats, idx, ids, shock_ids, frag=fs, **kw2)
        for oid, v in imp.items():
            samples[s, idx[oid]] = v
    p5, p50, p95 = np.percentile(samples, [5, 50, 95], axis=0)
    bands = {}
    for oid, i in idx.items():
        if point.get(oid, 0) > 0 or p95[i] > 0:
            bands[oid] = {'point': point.get(oid, 0.0),
                          'p5': round(float(p5[i]), 2),
                          'p50': round(float(p50[i]), 2),
                          'p95': round(float(p95[i]), 2)}
    return {'point': point, 'order': order, 'bands': bands, 'n_samples': samples.shape[0]}


# ── centralidad (PageRank) + estabilidad sistémica (radio espectral) ────────
def pagerank(agg, alpha=0.85, tol=1e-10, max_iter=200, personalization=None):
    """PageRank ponderado sobre el grafo de DEPENDENCIA (agg.T): un nodo es
    central si MUCHOS (transitivamente) dependen de él — alinea con el
    chokepoint_rank existente. Se usa PageRank (no eigenvector centrality pura)
    porque su término de teleportación evita valores degenerados cuando el
    grafo tiene componentes desconectados — esperable al mezclar datos curados
    con datos importados en bulto aún no conectados (spec §"Corrección...").

    Maneja nodos colgantes (dangling: sin salientes en el grafo de dependencia)
    redistribuyendo su masa al vector de teleportación (tratamiento estándar).
    `personalization`: vector de teleportación NO uniforme (Personalized
    PageRank — centralidad relativa a un portafolio); si None, uniforme."""
    A = _transpose_csr(agg)                      # grafo de dependencia (customer→supplier)
    n = A.shape[0]
    if n == 0:
        return np.zeros(0)
    outdeg = _rowsum(A)
    dangling = outdeg == 0
    inv = np.zeros(n)
    nz = ~dangling
    inv[nz] = 1.0 / outdeg[nz]
    W = _scale_rows(A, inv)                       # transición fila-estocástica i→j
    WT = _transpose_csr(W)
    if personalization is None:
        tele = np.full(n, 1.0 / n)
    else:
        tele = np.asarray(personalization, dtype=float)
        s = tele.sum()
        tele = tele / s if s > 0 else np.full(n, 1.0 / n)
    pr = np.full(n, 1.0 / n)
    for _ in range(max_iter):
        dmass = pr[dangling].sum()
        pr_new = alpha * (WT @ pr) + (alpha * dmass + (1.0 - alpha)) * tele
        s = pr_new.sum()
        if s > 0:
            pr_new = pr_new / s
        if np.abs(pr_new - pr).sum() < tol:
            pr = pr_new
            break
        pr = pr_new
    return pr


def spectral_radius(mats, factors=None, idx=None, rel_weights=None, damping=0.6):
    """ρ(T): radio espectral de la matriz de transmisión EFECTIVA por hop
    (incluida la modulación por fragilidad si hay Factores activos). El operador
    de un hop es M = damping·diag(frag)·Tᵀ; se reporta ρ(diag(frag)·Tᵀ) = ρ(T).

    Dos usos (spec §"Radio espectral"):
    1. Garantía de estabilidad: damping·ρ(T) < 1 ⇒ las cascadas decaen
       geométricamente en vez de auto-sostenerse. Si ≥ 1, régimen supercrítico.
    2. Métrica de producto: "qué tan cerca está la red de que un shock se vuelva
       auto-sostenido" — riesgo sistémico macro de toda la economía mapeada.

    M ≥ 0 (todo no-negativo) ⇒ por Perron-Frobenius el autovalor dominante es
    real no-negativo. Se intenta scipy.sparse.linalg.eigs (LM); si falla o el
    grafo es diminuto, se usa power iteration (robusto para matrices ≥ 0)."""
    D = _dependency_matrix(mats, rel_weights)
    T = _transpose_csr(D)                         # Tᵀ (transmisión efectiva)
    n = T.shape[0]
    if n == 0:
        return {'rho': 0.0, 'damping': damping, 'stable': True, 'method': 'empty'}
    if factors and idx is not None:
        frag = fragility(idx, factors)
        M = _scale_rows(T, frag)                  # diag(frag) · Tᵀ
    else:
        M = T
    rho, method = None, None
    if _issparse(M) and n >= 3:
        try:
            from scipy.sparse.linalg import eigs
            vals = eigs(M.astype(float), k=1, which='LM',
                        maxiter=n * 20, return_eigenvectors=False)
            rho, method = float(np.abs(vals[0])), 'eigs'
        except Exception as e:  # noqa: BLE001
            log.debug('eigs falló, uso power iteration: %s', e)
    if rho is None:
        rho, method = _spectral_power_iter(M), 'power_iter'
    stable = damping * rho < 1.0
    if not stable:
        log.warning('Motor de matrices en régimen SUPERCRÍTICO: damping·ρ(T) = '
                    '%.3f ≥ 1 (las cascadas podrían auto-sostenerse).', damping * rho)
    return {'rho': round(rho, 6), 'damping': damping,
            'damping_rho': round(damping * rho, 6), 'stable': bool(stable),
            'method': method}


def _spectral_power_iter(M, iters=1000, tol=1e-9):
    """Radio espectral por power iteration. Válido porque M ≥ 0 (Perron-
    Frobenius: autovalor dominante real no-negativo). Denso o disperso."""
    n = M.shape[0]
    if n == 0:
        return 0.0
    v = np.ones(n) / np.sqrt(n)
    rho = 0.0
    for _ in range(iters):
        w = M @ v
        nrm = np.linalg.norm(w)
        if nrm < 1e-300:
            return 0.0
        v = w / nrm
        new = float(v @ (M @ v))               # cociente de Rayleigh
        if abs(new - rho) < tol:
            rho = new
            break
        rho = new
    return max(0.0, rho)


def compute_metrics(session, as_of=None):
    """Métricas por nodo: grado in/out ponderado, tamaño de cascada
    (¿a cuántos arrastra si cae?), ranking de chokepoints y PageRank
    (centralidad complementaria robusta a componentes desconectados)."""
    mats, idx, ids = build_matrices(session, as_of=as_of)
    factors = active_factors(session, as_of=as_of)
    frag = fragility(idx, factors)
    agg = None
    for m in mats.values():
        agg = m.copy() if agg is None else agg + m
    if agg is None:
        return {}, factors
    out_w = _rowsum(agg)
    in_w = _colsum(agg)
    pr = pagerank(agg)
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
            'pagerank': round(float(pr[i]), 6),
        }
    ranked = sorted(metrics.items(), key=lambda kv: -kv[1]['cascade_size'])
    for rank, (oid, m) in enumerate(ranked, 1):
        m['chokepoint_rank'] = rank
    # ranking de PageRank (1 = más central) como campo complementario
    pr_ranked = sorted(metrics.items(), key=lambda kv: -kv[1]['pagerank'])
    for rank, (oid, m) in enumerate(pr_ranked, 1):
        m['pagerank_rank'] = rank
    return metrics, factors


# ── caché en proceso del índice/matrices con invalidación por época ─────────
# A escala grande NO se puede reconstruir el índice ni las matrices desde cero
# en cada request. Se cachean por "época del grafo" = MAX(recorded_at) de events
# (consulta indexada barata) que cambia con CUALQUIER escritura → invalidación
# automática y correcta, sin listeners frágiles. TTL como respaldo.
_CACHE = {}
_CACHE_MAX = 24


# Solo los eventos que cambian la ESTRUCTURA del grafo mueven la época. Se
# EXCLUYE PriceObserved (se escribe muy seguido con la ingesta de precios) y
# ActionExecuted: el índice, las matrices, las métricas y ρ(T) NO dependen del
# precio → incluirlo haría trillar la caché sin ninguna razón de correctitud.
_STRUCTURAL_EVENTS = ('ObjectCreated', 'ObjectUpdated', 'LinkCreated', 'LinkRemoved')


def _graph_epoch(session):
    """Token que cambia con cualquier cambio ESTRUCTURAL del grafo (MAX
    recorded_at de eventos de objetos/links). Barato (índices sobre event_type y
    recorded_at). Captura altas/bajas de nodos y links, cambios de peso y de
    severidad/coeficiente de Factores (todo pasa por ObjectUpdated/LinkCreated)
    sin enumerar nada. Si falla, época volátil → no cachea de más."""
    try:
        from ontology.models import Event
        v = session.execute(select(Event.recorded_at)
                            .where(Event.event_type.in_(_STRUCTURAL_EVENTS))
                            .order_by(Event.recorded_at.desc()).limit(1)).scalar()
        return v.isoformat() if v is not None else '0'
    except Exception:  # noqa: BLE001
        return _utcnow().isoformat()


def _cache_get(key):
    e = _CACHE.get(key)
    if e and (_utcnow().timestamp() - e[0]) < 600:
        return e[1]
    return None


def _cache_set(key, value):
    if len(_CACHE) > _CACHE_MAX:
        _CACHE.clear()
    _CACHE[key] = (_utcnow().timestamp(), value)
