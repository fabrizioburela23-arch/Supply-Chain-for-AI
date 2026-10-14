"""matrix/tensor.py — ONTOLOGÍA NIVEL 2: el grafo como TENSORES, con números útiles para invertir.

Pedido de Fabrizio (2026-10): "el siguiente nivel de la ontología, totalmente matematizado y
sistematizado con tensores, listo para que todos los nodos nuevos se conecten de la misma forma de
inmediato; lo más eficiente posible y que genere datos de verdad, que den valor real como inversionista".

Objetos matemáticos (TODO disperso: E1.2 de docs/expansion/EXPANSION_5K.md — antes Ψ y el perfil eran N×N
densos: +634 MB y ~7 s a 5.000 empresas). Paso 8 (INFRA_OPERATIVA §4.7): el grafo es la vista `graph` de la
generación vigente (core/hotviews/hot.graph(): Postgres si existe, el snapshot data/grafo_v0.json si no) y el
modelo se recalcula cuando cambia la generación:

  A  ∈ ℝ^{R×N×N}  tensor de relaciones de FLUJO (supply, fab, cloud, license, ppa, owns, deploy;
                  vocabulary.json `flow: true`). A[r,i,j] = peso × confianza del vínculo i → j
                  (i PROVEE a j). Socios e inversores NO transmiten daño de suministro (regla G4).
  D  = Σ_r α_r · colnorm(A_r)   matriz de transmisión (matrix.engine._dependency_matrix, la MISMA
                  del kernel de shocks: un proveedor único transmite casi todo).
  Ψ  ∈ [0,1]^{N×N}  INFLUENCIA (dispersa, csc + csr): Ψ[j,s] = impacto sobre j del colapso unitario de s con EL
                  kernel del servidor (matrix.engine.propagate_many, damping 0.6, máx. 6 saltos, umbral 1 %, máximo
                  por ruta, fragilidad de los factores activos) sobre la GraphCore de la generación vigente, con las
                  relaciones de FLUJO solamente (BRECHAS #4: socios e inversores NO transmiten daño). Si el kernel
                  vigente ya es "solo flujo" (kernel.params 2.x: damage_rels = flujo) Ψ = las víctimas de la vista
                  Impact tal cual, sin una segunda pasada del kernel; si no (1.0.0), una pasada solo de flujo.
  c  ∈ ℝ^N        capitalización (USD B): en vivo (core.live_caps) → valuación VERIFICADA de privadas
                  (nodes/private_valuations.js) → sin dato (0, y se dice).
  X  ∈ ℝ^{N×F}    tensor de rasgos (FEATURES), z-normalizado, + perfil estructural disperso (filas y columnas
                  de A, normalizado por fila) para medir parecido.

Métricas por empresa (lo que un inversionista no ve en una planilla):
  · concentración de proveedores (HHI de la columna de A sobre proveedores directos): "depende en
    un 62 % de TSMC";
  · países de sus proveedores (participación por país de origen);
  · capitalización AGUAS ABAJO en riesgo: Σ_j Ψ[j,s]·c_j = Ψᵀc — cuánto valor de mercado de clientes y
    clientes-de-clientes queda expuesto si esta empresa falla (importancia sistémica en dólares);
  · fuentes de riesgo AGUAS ARRIBA: las s con mayor Ψ[j,s] (no solo proveedores directos);
  · comparables: vecinos más cercanos en X (mismos proveedores/clientes + rasgos), no solo "mismo sector".

ORDEN DE LAS LISTAS (E1.2): de mayor a menor y, en EMPATE, por id (los ids están ordenados: posición = id). Antes
el orden de los empates lo decidía np.argsort (no estable; depende de la CPU). Las sumas (parecido, Ψᵀc) se
comparan redondeadas (12 decimales / 12 cifras): una diferencia de redondeo de la máquina no cambia el orden.
Ψᵀc se suma con math.fsum (exacta: no depende del orden de la suma). EXCEPCIÓN — los pares de suggest_links: si el
corte de N_PEERS cae dentro de un grupo de empatados, entra el grupo ENTERO con peso × lugares/tamaño (el valor
esperado del sorteo de antes, sin sesgo por id: `_cut_with_ties`); sin empate en el borde, lo de siempre.

AUTO-CONEXIÓN de nodos nuevos (`suggest_links`): para una empresa nueva (o una existente con
vínculos faltantes) propone proveedores/clientes con un puntaje explicable:
  score(s→t, r) = 0.7·P_peers + 0.3·P_cat
  P_peers = Σ_{s'∈peers(s)} sim(s,s')·[s' →r t] / Σ sim   ("3 de 5 empresas parecidas le venden a T")
  P_cat   = densidad del bloque (cat_s → cat_t, r) del tensor (cuán típico es ese tipo de vínculo).
Las propuestas NUNCA se escriben solas: van a revisión de Fabrizio (regla: lo ambiguo, a revisión).
`evaluate()` mide la calidad con vínculos REALES ocultos (Hit@10 vs. la línea base de popularidad):
el número se publica tal cual, sea bueno o malo.
"""
import logging
import math
import re
import threading
import time
import unicodedata
from collections import Counter, defaultdict

import numpy as np
import scipy.sparse as sp

from matrix import engine as E
from ontology import vocabulary as vocab

log = logging.getLogger('khipu')

# INFRA_OPERATIVA paso 9: los números del tensor salen de `kernel.params` (el MISMO kernel que matrix/engine):
#   DAMPING, MAX_HOPS, THRESHOLD — propagación de daño (= propagate);
#   SUPPLIER_RELS — relaciones que hacen a alguien PROVEEDOR (concentración / países): ni propiedad ni despliegue;
#   W_PEERS, W_CAT — mezcla pares/categoría de suggest_links; N_PEERS — pares (medido con evaluate(), 3 semillas:
#   4→0.31 · 8→0.41 · 15→0.44 · 30→0.43).
from core import governance as _gov  # noqa: E402
DAMPING, MAX_HOPS, THRESHOLD, SUPPLIER_RELS, W_PEERS, W_CAT, N_PEERS = _gov.bind(globals(), 'kernel.params', {
    'DAMPING': 'damping', 'MAX_HOPS': 'max_hops', 'THRESHOLD': 'threshold',
    'SUPPLIER_RELS': ('supplier_rels', tuple), 'W_PEERS': 'tensor_w_peers', 'W_CAT': 'tensor_w_cat',
    'N_PEERS': 'tensor_n_peers'})
FEATURES = ('log_cap', 'n_suppliers', 'n_customers', 'supplier_hhi', 'log_down_cap', 'up_exposure')

_LOCK = threading.Lock()
_MODEL = {'m': None, 'key': None}
_BUILDING = {}        # clave del modelo → Event: UNA construcción a la vez por clave (el prewarm y un lector esperan la misma)
_PSI = {'key': None, 'val': None}   # Ψ de la última generación: un cambio de caps no repite el kernel
_TOK = {}             # id → ((etiqueta, rol, provee), tokens): no se re-tokeniza lo que no cambió entre generaciones
_TOK_MAX = 50000


# ─────────────────────────── orden estable ───────────────────────────
def _round_sig(v, digits=12):
    """v redondeado a `digits` cifras significativas (para COMPARAR sumas: Ψᵀc). 0 queda 0."""
    v = np.asarray(v, dtype=float)
    out = np.zeros_like(v)
    nz = np.flatnonzero(v)
    if nz.size:
        x = v[nz]
        scale = 10.0 ** (digits - 1 - np.floor(np.log10(np.abs(x))))
        out[nz] = np.round(x * scale) / scale
    return out


def _order(v, k=None):
    """Posiciones de `v` de MAYOR a menor; los empates, por posición (= por id). Solo las k primeras si k."""
    key = -np.asarray(v, dtype=float)
    n = key.shape[0]
    if k is None or k >= n:
        return np.argsort(key, kind='stable')
    if k <= 0:
        return np.zeros(0, dtype=np.intp)
    part = np.argpartition(key, k - 1)[:k]
    cand = np.flatnonzero(key <= key[part].max())          # incluye todos los empatados en el borde
    return cand[np.argsort(key[cand], kind='stable')][:k]


def _colsum_exact(csc, w):
    """Σ_j M[j,s]·w_j por columna con math.fsum: la suma CORRECTAMENTE redondeada de los productos, sin depender
    del orden (BLAS denso y la suma dispersa diferían en la última cifra binaria: un 9,85 exacto salía 9,850…01 →
    «9,9» en la ficha). ~5 ms a 5.000 empresas."""
    prod = csc.data * np.asarray(w, dtype=float)[csc.indices]
    ip = csc.indptr
    fs = math.fsum
    return np.array([fs(prod[ip[s]:ip[s + 1]]) for s in range(csc.shape[1])], dtype=float)


# ─────────────────────────── matrices dispersas ───────────────────────────
class SparsePsi:
    """Ψ dispersa (n×n). Se indexa como la densa de antes: psi[j, s] → número, psi[:, s] / psi[j] → vector denso
    (copia). `col_nz(s)` / `row_nz(j)` dan (posiciones, valores) sin densificar (lo que usa la ficha)."""
    __slots__ = ('csc', 'csr', 'shape', 'nnz')

    def __init__(self, csc):
        self.csc = csc                       # canónica (_psi_sparse): sin duplicados, índices ordenados; no se modifica
        self.csr = csc.tocsr()
        self.csr.sort_indices()
        self.shape = csc.shape
        self.nnz = int(csc.nnz)

    def col_nz(self, s):
        a, b = self.csc.indptr[s], self.csc.indptr[s + 1]
        return self.csc.indices[a:b], self.csc.data[a:b]

    def row_nz(self, j):
        a, b = self.csr.indptr[j], self.csr.indptr[j + 1]
        return self.csr.indices[a:b], self.csr.data[a:b]

    def col(self, s):
        out = np.zeros(self.shape[0])
        i, v = self.col_nz(s)
        out[i] = v
        return out

    def row(self, j):
        out = np.zeros(self.shape[1])
        i, v = self.row_nz(j)
        out[i] = v
        return out

    def get(self, j, s):
        i, v = self.col_nz(s)
        p = int(np.searchsorted(i, j))
        return float(v[p]) if p < len(i) and i[p] == j else 0.0

    def __getitem__(self, key):
        if isinstance(key, tuple) and len(key) == 2:
            a, b = key
            if isinstance(a, slice) and a == slice(None) and not isinstance(b, slice):
                return self.col(int(b))
            if isinstance(b, slice) and b == slice(None) and not isinstance(a, slice):
                return self.row(int(a))
            if not isinstance(a, slice) and not isinstance(b, slice):
                return self.get(int(a), int(b))
            raise TypeError('SparsePsi: índice no soportado / unsupported index')
        if isinstance(key, slice):
            raise TypeError('SparsePsi: índice no soportado / unsupported index')
        return self.row(int(key))

    def toarray(self):
        return self.csc.toarray()

    def nbytes(self):
        return int(sum(x.nbytes for m in (self.csc, self.csr) for x in (m.data, m.indices, m.indptr)))


class SparseProfile:
    """Perfil estructural [A | Aᵀ] (n×2n) disperso y normalizado por fila. `prof @ prof[j]` da el coseno de j con
    todas (vector denso de n), igual que con la matriz densa de antes."""
    __slots__ = ('csr', 'shape')

    def __init__(self, csr):
        self.csr = csr
        self.shape = csr.shape

    def __getitem__(self, j):
        a, b = self.csr.indptr[j], self.csr.indptr[j + 1]
        out = np.zeros(self.shape[1])
        out[self.csr.indices[a:b]] = self.csr.data[a:b]
        return out

    def __matmul__(self, v):
        return np.asarray(self.csr @ np.asarray(v, dtype=float)).ravel()

    def sim(self, j):
        """Coseno de j con todas: suma SOLO sobre los vínculos compartidos (sin densificar el perfil)."""
        return self @ self[j]

    def nbytes(self):
        m = self.csr
        return int(m.data.nbytes + m.indices.nbytes + m.indptr.nbytes)


# ─────────────────────────── carga ───────────────────────────
def _load_snapshot():
    """El grafo vigente con la forma del snapshot (Mapping de solo lectura de la vista `graph`)."""
    from core.hotviews import hot
    return hot.graph().snapshot


def _psi_sparse(victims, ids, idx):
    """Ψ[j,s] (0-1) dispersa desde víctimas {fuente: (ids, pct, salto)} (pct/100; sin la diagonal ni ceros)."""
    n = len(ids)
    rows, cols, vals = [], [], []
    get = idx.get
    for s, si in idx.items():
        hit = victims.get(s)
        if not hit:
            continue
        vids, pct, _hop = hit
        rows.extend([get(k, -1) for k in vids])
        cols.extend([si] * len(vids))
        vals.extend(pct)
    if not rows:
        return sp.csc_matrix((n, n))
    r = np.asarray(rows, dtype=np.int64)
    c = np.asarray(cols, dtype=np.int64)
    v = np.asarray(vals, dtype=float) / 100.0
    keep = (r >= 0) & (r != c) & (v > 0)
    out = sp.csc_matrix((v[keep], (r[keep], c[keep])), shape=(n, n))
    out.sum_duplicates()                     # forma canónica (no hay duplicados: víctimas = claves de un dict)
    out.sort_indices()
    return out


def _core_for(snap):
    """La GraphCore de un grafo dado (evaluate() y pruebas): MISMO código que el constructor de las vistas."""
    from core.hotviews import source
    from core.hotviews.views import graph_core
    return graph_core.build(source.from_snapshot(snap))


def _impact_for(snap):
    """La vista Impact de un grafo dado (MISMO código que el constructor de las vistas)."""
    from core.hotviews.views import impact
    return impact.build(_core_for(snap))


class _FlowImpact:
    __slots__ = ('victims',)


def _flow_impact(core):
    """La vista Impact con el MISMO kernel (propagate_many: damping, saltos, umbral, máximo por ruta, fragilidad
    de los factores activos) pero SOLO sobre las relaciones de FLUJO: socios e inversores no transmiten daño
    (BRECHAS #4). Con kernel.params 2.x la vista Impact ya es así y el modelo la lee tal cual (_impact_is_flow_only);
    esta pasada queda para 1.0.0 y para grafos armados a mano (evaluate, pruebas)."""
    out = _FlowImpact()
    out.victims = {}
    if core is None or not core.mats:
        return out
    flow = set(vocab.flow_relation_types())
    mats = {r: m for r, m in core.mats.items() if r in flow}
    if not mats:
        return out
    sources = [oid for oid in core.ids]
    res = E.propagate_many(mats, core.idx, core.ids, sources, damping=DAMPING, max_hops=MAX_HOPS,
                           threshold=THRESHOLD, frag=core.frag, dt=E.dependency_transpose(mats))
    for oid in sources:
        impacts, hops = res.get(oid, ({}, {}))
        if not impacts:
            continue
        order = sorted(impacts.items(), key=lambda kv: (-kv[1], hops.get(kv[0], 0), kv[0]))
        out.victims[oid] = (tuple(k for k, _ in order), tuple(p for _, p in order),
                            tuple(hops.get(k, 0) for k, _ in order))
    return out


def _flow_psi(core, ids, idx):
    """Ψ de la pasada de FLUJO (la misma de _flow_impact) armada directo desde los impactos, sin ordenar víctimas por
    fuente (el orden no cambia una matriz dispersa canónica: mismos valores, mismas posiciones). ~25 ms menos a 5k."""
    n = len(ids)
    if core is None or not core.mats:
        return sp.csc_matrix((n, n))
    flow = set(vocab.flow_relation_types())
    mats = {r: m for r, m in core.mats.items() if r in flow}
    if not mats:
        return sp.csc_matrix((n, n))
    res = E.propagate_many(mats, core.idx, core.ids, list(core.ids), damping=DAMPING, max_hops=MAX_HOPS,
                           threshold=THRESHOLD, frag=core.frag, dt=E.dependency_transpose(mats))
    rows, cols, vals = [], [], []
    get = idx.get
    for s, si in idx.items():
        impacts = (res.get(s) or ({}, {}))[0]
        if not impacts:
            continue
        rows.extend([get(k, -1) for k in impacts])
        cols.extend([si] * len(impacts))
        vals.extend(impacts.values())
    if not rows:
        return sp.csc_matrix((n, n))
    r = np.asarray(rows, dtype=np.int64)
    c = np.asarray(cols, dtype=np.int64)
    v = np.asarray(vals, dtype=float) / 100.0
    keep = (r >= 0) & (r != c) & (v > 0)
    out = sp.csc_matrix((v[keep], (r[keep], c[keep])), shape=(n, n))
    out.sum_duplicates()
    out.sort_indices()
    return out


def _kernel_semver():
    try:
        return _gov.artifact_semver('kernel.params')
    except Exception:  # noqa: BLE001
        return None


def _impact_is_flow_only(core, imp):
    """¿La vista Impact de la generación ya es "solo flujo" con los MISMOS números que usaría _flow_impact? Lo es con
    kernel.params 2.x (damage_rels = relaciones de flujo, BRECHAS #4), sin leer ninguna versión fija: lo dice el
    parámetro con que se construyó la vista. Entonces Ψ = sus víctimas y no hace falta una segunda pasada."""
    k = getattr(imp, 'kernel', None) if imp is not None else None
    if core is None or not k or not core.mats:
        return False
    dr = k.get('damage_rels')
    if dr is None or k.get('method') != 'propagate@1':
        return False
    if k.get('semver') is None or k.get('semver') != _kernel_semver():
        return False                       # la generación se armó con otro release (o un contrafactual)
    flow, damage = set(vocab.flow_relation_types()), set(dr)
    present = set(core.mats)
    if {r for r in present if r in damage} != {r for r in present if r in flow}:
        return False
    try:
        return (k.get('damping'), k.get('max_hops'), k.get('threshold'), k.get('magnitude')) == (
            DAMPING, MAX_HOPS, THRESHOLD, E._P('magnitude'))
    except Exception:  # noqa: BLE001
        return False


def _psi_for(core, imp, ids, idx, gen=None):
    """(Ψ dispersa csc, de dónde salió). Con la generación conocida se guarda: un cambio de caps no repite el kernel."""
    key = None
    if gen is not None:
        key = (gen, _kernel_semver(), DAMPING, MAX_HOPS, THRESHOLD, len(ids))
        with _LOCK:
            if _PSI['key'] == key:
                return _PSI['val']
    if _impact_is_flow_only(core, imp):
        val = (_psi_sparse(imp.victims, ids, idx), 'impact_view')
    else:
        val = (_flow_psi(core, ids, idx), 'flow_pass')
    if key is not None:
        with _LOCK:
            _PSI.update(key=key, val=val)
    return val


def _caps_live():
    """{id: mcap_b} en vivo + versión para la caché. Si están vencidas (p. ej. recién reiniciado el
    servidor) lanza el refresco EN SEGUNDO PLANO (no bloquea): la siguiente lectura ya las usa."""
    try:
        from core import live_caps
        st = live_caps.get_caps(start=True)
        caps = {k: float(v['mcap_b']) for k, v in (st.get('caps') or {}).items()
                if isinstance(v, dict) and v.get('mcap_b') is not None and float(v['mcap_b']) > 0}
        return caps, st.get('as_of')
    except Exception:  # noqa: BLE001
        return {}, None


def _caps_private():
    try:
        from mcp_server.tools import _private_valuations
        ent = (_private_valuations() or {}).get('entries') or {}
        return {k: float(e['valuation_usd_b']) for k, e in ent.items()
                if isinstance(e, dict) and float(e.get('valuation_usd_b') or 0) > 0}
    except Exception:  # noqa: BLE001
        return {}


def _country(raw):
    """País del catálogo normalizado ('Estados Unidos (manufactura…)' → 'EEUU'), como core/world."""
    if not raw:
        return '?'
    try:
        from core.world import country_key
        k = country_key(raw)
        if k:
            return k
    except Exception:  # noqa: BLE001
        pass
    return re.split(r'[/(,;—–]', str(raw))[0].strip() or '?'


def _norm_txt(s):
    s = unicodedata.normalize('NFD', str(s or ''))
    s = ''.join(ch for ch in s if not (0x300 <= ord(ch) <= 0x36F)).lower()
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


_STOP = set('de la el los las y en para con por a an the of and for to in on with del al su sus que un una'.split())


def _tokens(*parts):
    return {w for p in parts for w in _norm_txt(p).split() if len(w) > 2 and w not in _STOP}


def _tokens_cached(k, node):
    """Tokens de texto de una empresa, guardados por id (los de una empresa que no cambió no se recalculan)."""
    txt = (node.get('label'), node.get('role'), node.get('supplies'))
    hit = _TOK.get(k)
    if hit is not None and hit[0] == txt:
        return hit[1]
    tk = frozenset(_tokens(*txt))
    if len(_TOK) >= _TOK_MAX:
        _TOK.clear()
    _TOK[k] = (txt, tk)
    return tk


# ─────────────────────────── modelo ───────────────────────────
class Model:
    """Tensores del grafo ya calculados (inmutable; se reemplaza entero al cambiar la entrada)."""

    def __init__(self, snap, caps_live=None, caps_private=None, caps_as_of=None, view=None):
        t0 = time.perf_counter()
        self.generation = view.generation if view is not None else None
        self.graph_version = view.graph_version if view is not None else None
        nodes = [n for n in snap['nodes'] if n.get('id')]
        self.ids = sorted(n['id'] for n in nodes)
        self.idx = {k: i for i, k in enumerate(self.ids)}
        self.node = {n['id']: n for n in nodes}
        self.n = n = len(self.ids)
        self.rels = [r for r in vocab.flow_relation_types() if r in E.REL_TYPES]
        triples = []
        for l in snap['links']:
            if l.get('type') not in self.rels:
                continue
            w = E._eff_weight(l.get('w') or 2, None, l.get('conf'))
            triples.append((l['source'], l['target'], l['type'], float(w)))
        mats, _, _ = E.build_matrices_from_triples(triples, self.idx, sparse=True)
        self.A = {r: mats[r].tocsr() for r in self.rels}                     # tensor R×N×N
        self.D = E._dependency_matrix(self.A)                                 # transmisión
        # ── capitalización: en vivo → valuación verificada → 0 (sin dato)
        caps_live = caps_live or {}
        caps_private = caps_private or {}
        self.cap = np.zeros(n)
        self.cap_src = [None] * n
        for i, k in enumerate(self.ids):
            if k in caps_live:
                self.cap[i], self.cap_src[i] = caps_live[k], 'live'
            elif k in caps_private:
                self.cap[i], self.cap_src[i] = caps_private[k], 'verified_valuation'
        self.caps_as_of = caps_as_of
        # ── Ψ = EL kernel del servidor (factores activos incluidos) solo por FLUJO, dispersa: la vista Impact de la
        #    generación si ya es solo flujo; si no, una pasada de flujo (guardada por generación)
        t1 = time.perf_counter()
        core = view.core if view is not None else None
        if core is None:
            core = _core_for(snap)
        imp = view.impact if view is not None else None
        psi_csc, self.psi_source = _psi_for(core, imp, self.ids, self.idx,
                                            gen=self.generation if view is not None else None)
        self.psi_method = 'impact_kernel_flow_only:propagate@1'
        self.psi = SparsePsi(psi_csc)                                         # psi[j, s]
        self.psi_ms = round((time.perf_counter() - t1) * 1000, 1)
        # ── proveedores directos (columna de A sobre SUPPLIER_RELS)
        S = None
        for r in SUPPLIER_RELS:
            if r in self.A:
                S = self.A[r] if S is None else S + self.A[r]
        if S is None:
            S = sp.csr_matrix((n, n))
        self.S = S.tocsc()
        Sr = S.tocsr()
        self.n_sup = np.diff(self.S.indptr)
        self.n_cus = np.diff(Sr.indptr)
        self.hhi = np.zeros(n)
        nzc = np.flatnonzero(self.n_sup)
        cnt = self.n_sup[nzc]
        for c in np.unique(cnt).tolist():                                     # Σ (w/Σw)² por columna, en bloques
            cols = nzc[cnt == c]                                              # de igual nº de proveedores: la suma
            W = self.S.data[self.S.indptr[cols][:, None] + np.arange(c)]      # por fila es bit a bit la de w.sum()
            sh = W / W.sum(axis=1)[:, None]
            self.hhi[cols] = (sh ** 2).sum(axis=1)
        self.down_cap = _colsum_exact(self.psi.csc, self.cap)                # Σ_j psi[j,s]·c_j = Ψᵀc (exacta)
        self.up_exposure = np.asarray(self.psi.csr.max(axis=1).todense()).ravel() if n else np.zeros(0)
        self._down_key = _round_sig(self.down_cap)                            # para ordenar / rango sistémico
        # ── X: rasgos z-normalizados + perfil estructural disperso para parecido (coseno)
        X = np.column_stack([
            np.log10(1 + self.cap), np.log1p(self.n_sup), np.log1p(self.n_cus),
            self.hhi, np.log10(1 + self.down_cap), self.up_exposure])
        mu, sd = X.mean(axis=0), X.std(axis=0)
        sd[sd == 0] = 1.0
        self.X = (X - mu) / sd
        Abin = None
        for r in self.rels:
            m = (self.A[r] > 0).astype(float)
            Abin = m if Abin is None else Abin + m
        if Abin is None:
            Abin = sp.csr_matrix((n, n))
        self.Abin = Abin.tocsr()
        P = sp.hstack([self.Abin, self.Abin.T.tocsr()], format='csr')        # [clientes | proveedores]
        P.sum_duplicates()
        P.sort_indices()
        cnt = np.diff(P.indptr)
        nrm = np.sqrt(np.bincount(np.repeat(np.arange(n), cnt), weights=P.data ** 2, minlength=n))
        nrm[nrm == 0] = 1.0
        P.data = P.data / np.repeat(nrm, cnt)
        self.prof = SparseProfile(P)
        # ── bloques por categoría del tensor (prior de auto-conexión)
        self.cat = [self.node[k].get('cat') or '?' for k in self.ids]
        self.sector = [self.node[k].get('sector') or '?' for k in self.ids]
        cmemo = {}
        self.country = []
        for k in self.ids:
            raw = self.node[k].get('country')
            c = cmemo.get(raw)
            if c is None:
                c = cmemo[raw] = _country(raw)
            self.country.append(c)
        cats = sorted(set(self.cat))
        ccode = {c: i for i, c in enumerate(cats)}
        self.cat_code = np.fromiter((ccode[c] for c in self.cat), dtype=np.int64, count=n)
        self.n_cat = Counter(self.cat)
        self.block = defaultdict(float)                                       # (cat_s, cat_t, r) → nº
        nc = len(cats)
        for r in self.rels:
            co = self.A[r].tocoo()
            if not co.nnz:
                continue
            u, c = np.unique(self.cat_code[co.row] * nc + self.cat_code[co.col], return_counts=True)
            for kk, cc in zip(u.tolist(), c.tolist()):
                self.block[(cats[kk // nc], cats[kk % nc], r)] += float(cc)
        self._tok = None
        self.ms = round((time.perf_counter() - t0) * 1000)

    # ── utilidades
    @property
    def tok(self):
        """Tokens de texto por empresa (solo los usa suggest_links de una empresa NUEVA): a pedido y con caché por id."""
        if self._tok is None:
            self._tok = [_tokens_cached(k, self.node[k]) for k in self.ids]
        return self._tok

    def label(self, k):
        return (self.node.get(k) or {}).get('label') or k

    def i_of(self, nid):
        if nid in self.idx:
            return self.idx[nid]
        try:
            from core.entities import resolve
            r = resolve(nid)
            if r and r.get('id') in self.idx and (r.get('score') or 0) >= 85:
                return self.idx[r['id']]
        except Exception:  # noqa: BLE001
            pass
        return None

    def cat_prior(self, cs, ct, r):
        a, b = self.n_cat.get(cs, 0), self.n_cat.get(ct, 0)
        if not a or not b:
            return 0.0
        return self.block.get((cs, ct, r), 0.0) / float(a * b)

    def nbytes(self):
        """Memoria aproximada de lo disperso + vectores (🩺 / pruebas de escala)."""
        mats = list(self.A.values()) + [self.D, self.S, self.Abin]
        b = sum(int(m.data.nbytes + m.indices.nbytes + m.indptr.nbytes) for m in mats if hasattr(m, 'indptr'))
        return b + self.psi.nbytes() + self.prof.nbytes() + int(self.X.nbytes + 5 * self.n * 8)


def model(force=False, snap=None, view=None):
    """Modelo vigente (caché). Se reconstruye si cambia la GENERACIÓN del grafo (paso 8: antes, la fecha del
    archivo del snapshot) o la versión de las caps en vivo. `view` (GraphView): el de UNA generación concreta (la
    tarjeta V3 de esa generación, paso 14) — sin pasar por hot.graph() (que puede esperar al constructor).
    Una sola construcción por clave: quien llega mientras otro hilo la arma (el prewarm) la espera."""
    caps_live, caps_as_of = _caps_live()
    if snap is not None:
        return Model(snap, caps_live, _caps_private(), caps_as_of)
    if view is None:
        from core.hotviews import hot
        view = hot.graph()
    key = (view.generation, caps_as_of, len(caps_live))
    waited = False
    while True:
        with _LOCK:
            m = _MODEL['m']
            if m is not None and _MODEL['key'] == key and (not force or waited):
                return m
            ev = _BUILDING.get(key)
            if ev is None:
                ev = _BUILDING[key] = threading.Event()
                break
        ev.wait(120.0)
        waited = True
    try:
        m = Model(view.snapshot, caps_live, _caps_private(), caps_as_of, view=view)
        with _LOCK:
            _MODEL.update(m=m, key=key)
        return m
    finally:
        with _LOCK:
            _BUILDING.pop(key, None)
        ev.set()


def graph_version():
    """La generación del grafo del modelo vigente (tests/test_ops_single_source.py)."""
    return model().generation


# ─────────────────────────── métricas por empresa ───────────────────────────
def _conc_label(h, n):
    if n <= 0:
        return None
    if n == 1 or h >= 0.5:
        return 'alta'
    if h >= 0.25:
        return 'media'
    return 'baja'


def structure(nid, m=None, top=5):
    """Ficha estructural de una empresa (contrato estable; solo se agregan campos)."""
    m = m or model()
    j = m.i_of(nid)
    if j is None:
        return None
    k = m.ids[j]
    # proveedores directos y su participación
    a, b = m.S.indptr[j], m.S.indptr[j + 1]
    rows, w = m.S.indices[a:b], m.S.data[a:b]
    tot = float(w.sum()) or 1.0
    sups = sorted(({'id': m.ids[i], 'label': m.label(m.ids[i]), 'share_pct': round(float(x) / tot * 100, 1)}
                   for i, x in zip(rows, w)), key=lambda d: -d['share_pct'])
    ctry = defaultdict(float)
    for i, x in zip(rows, w):
        ctry[m.country[i]] += float(x) / tot
    countries = sorted(({'country': c, 'share_pct': round(v * 100, 1)} for c, v in ctry.items()),
                       key=lambda d: -d['share_pct'])
    # aguas arriba: de dónde le llega el riesgo (Ψ fila j, solo lo no nulo)
    ri, rv = m.psi.row_nz(j)
    so = _order(rv, top)
    # aguas abajo: a quién arrastra (Ψ columna j) y cuánta capitalización
    ci, cv = m.psi.col_nz(j)
    capc = m.cap[ci]
    do = _order(cv * np.maximum(capc, 1e-9), top)
    n_down = int(len(ci))
    rank = int((m._down_key > m._down_key[j]).sum()) + 1
    covered = float((capc > 0).sum()) / max(1, n_down) if n_down else None
    direct = set(rows.tolist())
    return {
        'id': k, 'label': m.label(k),
        'supplier_concentration': {
            'hhi': round(float(m.hhi[j]), 3), 'level': _conc_label(m.hhi[j], len(sups)),
            'n_suppliers': len(sups), 'top': sups[:top]},
        'supplier_countries': countries[:6],
        'downstream': {
            'cap_at_risk_usd_b': round(float(m.down_cap[j]), 1), 'n_companies': n_down,
            'systemic_rank': rank, 'of': m.n,
            'cap_coverage_pct': round(covered * 100) if covered is not None else None,
            'top': [{'id': m.ids[ci[p]], 'label': m.label(m.ids[ci[p]]), 'impact_pct': round(float(cv[p]) * 100, 1),
                     'cap_usd_b': round(float(capc[p]), 1) if capc[p] > 0 else None} for p in do]},
        'upstream_risk_sources': [{'id': m.ids[ri[p]], 'label': m.label(m.ids[ri[p]]),
                                   'exposure_pct': round(float(rv[p]) * 100, 1),
                                   'direct': bool(int(ri[p]) in direct)} for p in so],
        'peers': peers(k, m=m, n=5),
        'cap_usd_b': round(float(m.cap[j]), 1) if m.cap[j] > 0 else None,
        'cap_source': m.cap_src[j],
        'method': ('flow tensor (supply/fab/cloud/license/ppa/owns/deploy, conf-weighted) · influence Ψ = Impact '
                   'view (server kernel propagate@1: damping 0.6 · 6 hops · active factors)'),
        'caps_as_of': m.caps_as_of,
    }


def peers(nid, m=None, n=5):
    """Comparables: mismos proveedores/clientes (coseno del perfil) + rasgos (X) + misma categoría.
    Empates (a 12 decimales), por id."""
    m = m or model()
    j = m.i_of(nid)
    if j is None:
        return []
    sim = m.prof @ m.prof[j]
    dx = np.linalg.norm(m.X - m.X[j], axis=1)
    sim = 0.6 * sim + 0.25 * np.exp(-dx / 2.0) + 0.15 * (m.cat_code == m.cat_code[j])
    sim[j] = -1
    out = []
    for i in _order(np.round(sim, 12), n):
        out.append({'id': m.ids[i], 'label': m.label(m.ids[i]), 'similarity': round(float(sim[i]), 3)})
    return out


def ranking(m=None, by='cap_at_risk', limit=20):
    m = m or model()
    k = max(1, min(100, limit))
    if by == 'concentration':
        cand = np.flatnonzero(m.n_sup >= 1)
        order = cand[_order(np.round(m.hhi[cand], 12), k)]
        val = lambda i: round(float(m.hhi[i]), 3)  # noqa: E731
    elif by == 'exposure':
        order = _order(m.up_exposure, k)
        val = lambda i: round(float(m.up_exposure[i]) * 100, 1)  # noqa: E731
    else:
        order = _order(m._down_key, k)
        val = lambda i: round(float(m.down_cap[i]), 1)  # noqa: E731
    return [{'id': m.ids[i], 'label': m.label(m.ids[i]), 'value': val(i)} for i in order[:k]]


# ─────────────────────────── auto-conexión ───────────────────────────
def _peer_weights(m, j=None, new=None, k=None):
    """Pesos de parecido con el resto: existente (perfil+rasgos) o NUEVA (cat/sector/país/texto)."""
    if j is not None:
        sim = m.prof @ m.prof[j]
        sim = 0.7 * sim + 0.3 * (m.cat_code == m.cat_code[j])
        sim[j] = 0
    else:
        cat, sec, ctry = new.get('cat'), new.get('sector'), _country(new.get('country'))
        tk = _tokens(new.get('label'), new.get('role'), new.get('supplies'))
        sim = np.zeros(m.n)
        tok = m.tok
        for i in range(m.n):
            s = 1.0 if (cat and m.cat[i] == cat) else (0.35 if (sec and m.sector[i] == sec) else 0.0)
            if tk and tok[i]:
                s += 0.8 * len(tk & tok[i]) / len(tk | tok[i])
            if ctry and m.country[i] == ctry:
                s += 0.1
            sim[i] = s
    return _cut_with_ties(sim, k or N_PEERS)


def _cut_with_ties(sim, k):
    """Las k más parecidas. Si el corte cae DENTRO de un grupo de empatados (a 12 decimales), entra TODO el grupo con
    su peso escalado por (lugares que quedan / tamaño del grupo): el valor esperado del sorteo de antes (np.argsort no
    estable elegía k al azar entre los empatados, según la CPU) y sin sesgo por id — antes de esta regla una empresa
    nueva tomaba como «pares» las primeras de su categoría por orden alfabético. Sin empate en el borde: lo de siempre."""
    key = np.round(sim, 12)
    top = _order(key, k)
    if len(top) and len(top) == k and k < key.shape[0]:
        edge = key[top[-1]]
        if edge > 0:
            group = np.flatnonzero(key == edge)                   # en posición (= id): mismo orden que _order
            inside = [int(i) for i in top if key[i] != edge]
            slots = k - len(inside)
            if len(group) > slots:
                frac = slots / len(group)
                return ([(i, float(sim[i])) for i in inside if sim[i] > 0]
                        + [(int(i), float(sim[i]) * frac) for i in group if sim[i] > 0])
    return [(int(i), float(sim[i])) for i in top if sim[i] > 0]


def suggest_links(nid=None, new=None, m=None, n=10, exclude_existing=True):
    """Proveedores y clientes PROBABLES de una empresa (existente o nueva). Solo propuestas."""
    m = m or model()
    j = m.i_of(nid) if nid else None
    if j is None and not new:
        return None
    me = m.ids[j] if j is not None else None
    cat_s = m.cat[j] if j is not None else (new.get('cat') or '?')
    pw = _peer_weights(m, j=j, new=None if j is not None else new)
    tot = sum(w for _, w in pw) or 1.0
    have = set()
    if j is not None:
        for r in m.rels:
            have |= {(m.ids[t], r, 'out') for t in m.A[r][j].indices}
            have |= {(m.ids[s], r, 'in') for s in m.A[r][:, j].tocoo().row}
    cand = defaultdict(lambda: {'p': 0.0, 'via': []})
    for i, w in pw:
        for r in m.rels:
            for t in m.A[r][i].indices:                    # parecida i → t  ⇒  yo → t (soy proveedor)
                if t != j:
                    c = cand[(int(t), r, 'out')]; c['p'] += w / tot; c['via'].append(m.ids[i])
            for s in m.A[r][:, i].tocoo().row:             # s → parecida i  ⇒  s → yo (es mi proveedor)
                if s != j:
                    c = cand[(int(s), r, 'in')]; c['p'] += w / tot; c['via'].append(m.ids[i])
    rows = []
    for (o, r, d), c in cand.items():
        other = m.ids[o]
        if exclude_existing and (other, r, d) in have:
            continue
        prior = m.cat_prior(cat_s, m.cat[o], r) if d == 'out' else m.cat_prior(m.cat[o], cat_s, r)
        score = W_PEERS * c['p'] + W_CAT * min(1.0, prior * 10)
        via = list(dict.fromkeys(c['via']))[:3]
        rows.append({'direction': 'customer' if d == 'out' else 'supplier', 'id': other, 'label': m.label(other),
                     'rel': r, 'score': round(score, 3), 'peers_with_link': len(set(c['via'])),
                     'via': [{'id': v, 'label': m.label(v)} for v in via],
                     'source': me if d == 'out' else other, 'target': other if d == 'out' else me})
    rows.sort(key=lambda x: -x['score'])
    sup = [x for x in rows if x['direction'] == 'supplier'][:n]
    cus = [x for x in rows if x['direction'] == 'customer'][:n]
    return {'id': me, 'new': None if me else {k: new.get(k) for k in ('label', 'cat', 'sector', 'country')},
            'suppliers': sup, 'customers': cus,
            'peers': [{'id': m.ids[i], 'label': m.label(m.ids[i]), 'weight': round(w, 3)} for i, w in pw[:5]],
            'review_required': True,
            'note_es': 'Propuestas calculadas por parecido estructural; NO se agregan solas: revísalas antes.',
            'note_en': 'Proposals computed from structural similarity; they are NOT added automatically: review them first.'}


def evaluate(frac=0.1, seed=7, k=10, snap=None, max_cases=400):
    """Calidad REAL de la auto-conexión: se ocultan vínculos de flujo reales y se mide si vuelven
    a aparecer entre las k primeras propuestas (Hit@k), contra la línea base de popularidad
    (proponer siempre a los más conectados). Sin maquillaje: se devuelve lo que salga."""
    snap = snap or _load_snapshot()
    rng = np.random.default_rng(seed)
    flow = [i for i, l in enumerate(snap['links']) if l.get('type') in vocab.flow_relation_types()]
    outdeg = Counter(snap['links'][i]['source'] for i in flow)
    elig = [i for i in flow if outdeg[snap['links'][i]['source']] >= 3]
    hide = set(rng.choice(elig, size=min(max_cases, max(1, int(len(elig) * frac))), replace=False).tolist())
    train = dict(snap, links=[l for i, l in enumerate(snap['links']) if i not in hide])
    m = Model(train)
    indeg = Counter(l['target'] for l in train['links'] if l.get('type') in m.rels)
    popular = [t for t, _ in indeg.most_common()]
    hits = base = tot = 0
    for i in hide:
        l = snap['links'][i]
        s = suggest_links(l['source'], m=m, n=k)
        if not s:
            continue
        tot += 1
        if l['target'] in {x['id'] for x in s['customers']}:
            hits += 1
        have = {l2['target'] for l2 in train['links'] if l2['source'] == l['source']}
        if l['target'] in [t for t in popular if t not in have and t != l['source']][:k]:
            base += 1
    return {'cases': tot, 'k': k, 'hit_rate': round(hits / tot, 3) if tot else None,
            'baseline_popularity': round(base / tot, 3) if tot else None, 'seed': seed, 'frac': frac}


def status():
    m = model()
    return {'nodes': m.n, 'relations': m.rels, 'features': list(FEATURES),
            'nnz': {r: int(m.A[r].nnz) for r in m.rels}, 'caps_live': int(sum(1 for s in m.cap_src if s == 'live')),
            'caps_verified': int(sum(1 for s in m.cap_src if s == 'verified_valuation')),
            'build_ms': m.ms, 'caps_as_of': m.caps_as_of, 'generation': m.generation,
            'graph_version': m.graph_version, 'psi': m.psi_method, 'psi_source': m.psi_source,
            'psi_nnz': m.psi.nnz, 'psi_ms': m.psi_ms, 'memory_kb': round(m.nbytes() / 1024)}
