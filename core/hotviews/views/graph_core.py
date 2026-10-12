"""V1 GraphCore (INFRA_OPERATIVA §4.2): todo lo que el resto de las vistas y rutas necesitan del grafo,
calculado UNA vez por generación.

  · índice id→posición (el de matrix.engine.node_index) + metadatos (etiqueta, tipo, sector, país, ticker);
  · matrices CSR por relación (build_matrices_from_triples, la misma función que build_matrices);
  · agregado, peso de salida/entrada, Tᵀ de dependencia (dependency_transpose) — antes se recalculaba en
    CADA /impact (70 % de su costo, MAP 1 S6);
  · factores activos y vector de fragilidad (hiperaristas), ρ(T) con factores, PageRank;
  · grado de flujo en pares distintos (vocabulary.flow_degree, la regla del NRS).
"""
import hashlib
import time

import numpy as np


class GraphCore:
    __slots__ = ('ids', 'idx', 'meta', 'mats', 'agg', 'out_w', 'in_w', 'dt', 'factors', 'frag', 'rho',
                 'pagerank', 'flow_degree', 'lookup', 'alias', 'n_links', 'content_sha', 'timings')

    def resolve(self, q):
        """id exacto → alias del catálogo → id/etiqueta sin distinguir mayúsculas. None si no existe."""
        if not q:
            return None
        q = str(q).strip()
        if q in self.idx:
            return q
        a = self.alias.get(q)
        if a in self.idx:
            return a
        return self.lookup.get(q.lower())

    def label(self, oid):
        m = self.meta.get(oid)
        return (m or {}).get('label') or oid

    def nnz(self):
        return int(sum(m.nnz if hasattr(m, 'nnz') else int(np.count_nonzero(m)) for m in self.mats.values()))


def _sha_arrays(*parts):
    h = hashlib.sha256()
    for p in parts:
        if isinstance(p, np.ndarray):
            h.update(np.ascontiguousarray(p).tobytes())
        else:
            h.update(repr(p).encode())
    return h.hexdigest()


def build(data):
    """GraphData → GraphCore (sin tocar la base)."""
    from matrix import engine as E
    from ontology import vocabulary as vocab
    t = {}
    t0 = time.perf_counter()
    c = GraphCore()
    c.ids = list(data.ids)
    c.idx = {oid: i for i, oid in enumerate(c.ids)}
    c.meta = data.meta
    c.mats, _, _ = E.build_matrices_from_triples(data.triples, c.idx, sparse=None)
    c.n_links = len(data.triples)
    t['matrices_ms'] = (time.perf_counter() - t0) * 1000
    t1 = time.perf_counter()
    agg = None
    for m in c.mats.values():
        agg = m.copy() if agg is None else agg + m
    c.agg = agg
    n = len(c.ids)
    c.out_w = E._rowsum(agg) if agg is not None else np.zeros(n)
    c.in_w = E._colsum(agg) if agg is not None else np.zeros(n)
    c.dt = E.dependency_transpose(c.mats) if c.mats else None
    t['transpose_ms'] = (time.perf_counter() - t1) * 1000
    t1 = time.perf_counter()
    c.factors = list(data.factors or [])
    c.frag = E.fragility(c.idx, c.factors)
    try:
        c.rho = E.spectral_radius(c.mats, factors=c.factors, idx=c.idx) if n else None
    except Exception:  # noqa: BLE001
        c.rho = None
    c.pagerank = E.pagerank(agg) if agg is not None and n else np.zeros(n)
    t['factors_rho_pagerank_ms'] = (time.perf_counter() - t1) * 1000
    c.flow_degree = vocab.flow_degree(data.flow_links)
    lk = {}
    for oid in c.ids:
        lk.setdefault(oid.lower(), oid)
    for oid in c.ids:
        lab = (c.meta.get(oid) or {}).get('label')
        if lab:
            lk.setdefault(str(lab).strip().lower(), oid)
    c.lookup = lk
    c.alias = dict((data.extra or {}).get('alias') or {})
    parts = [tuple(c.ids)]
    for r in sorted(c.mats):
        m = c.mats[r]
        if hasattr(m, 'indptr'):
            parts += [r, m.indptr, m.indices, m.data]
        else:
            parts += [r, np.asarray(m)]
    parts += [c.frag]
    c.content_sha = _sha_arrays(*parts)
    c.timings = {k: round(v, 2) for k, v in t.items()}
    return c


def status(c):
    return {'nodes': len(c.ids), 'links_read': c.n_links, 'nnz': c.nnz(), 'factors': len(c.factors),
            'rho': (c.rho or {}).get('rho'), 'damping_rho': (c.rho or {}).get('damping_rho'),
            'stable': (c.rho or {}).get('stable'), 'content_sha': c.content_sha, 'timings': c.timings}


def factors_payload(c):
    """Factores activos con la fragilidad que producen (lo que /api/hot/factors sirve)."""
    out = []
    for f in c.factors:
        mem = f.get('members') or {}
        out.append({'id': f['id'], 'label': f.get('label'), 'severity': f.get('severity'),
                    'severity_crisis': f.get('severity_crisis'), 'rationale': f.get('rationale', ''),
                    'since': f.get('since'), 'updated': f.get('updated'),
                    'members': mem,
                    'members_fragility': {m: round(float(c.frag[c.idx[m]]), 4) for m in mem if m in c.idx}})
    return out
