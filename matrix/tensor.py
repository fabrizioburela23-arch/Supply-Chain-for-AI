"""matrix/tensor.py — ONTOLOGÍA NIVEL 2: el grafo como TENSORES, con números útiles para invertir.

Pedido de Fabrizio (2026-10): "el siguiente nivel de la ontología, totalmente matematizado y
sistematizado con tensores, listo para que todos los nodos nuevos se conecten de la misma forma de
inmediato; lo más eficiente posible y que genere datos de verdad, que den valor real como inversionista".

Objetos matemáticos (todo sparse/numpy). Paso 8 (INFRA_OPERATIVA §4.7): el grafo es la vista `graph` de la
generación vigente (core/hotviews/hot.graph(): Postgres si existe, el snapshot data/grafo_v0.json si no) y el
modelo se recalcula cuando cambia la generación:

  A  ∈ ℝ^{R×N×N}  tensor de relaciones de FLUJO (supply, fab, cloud, license, ppa, owns, deploy;
                  vocabulary.json `flow: true`). A[r,i,j] = peso × confianza del vínculo i → j
                  (i PROVEE a j). Socios e inversores NO transmiten daño de suministro (regla G4).
  D  = Σ_r α_r · colnorm(A_r)   matriz de transmisión (matrix.engine._dependency_matrix, la MISMA
                  del kernel de shocks: un proveedor único transmite casi todo).
  Ψ  ∈ [0,1]^{N×N}  INFLUENCIA: Ψ[j,s] = impacto sobre j del colapso unitario de s con EL kernel del
                  servidor (matrix.engine.propagate_many, damping 0.6, máx. 6 saltos, umbral 1 %, máximo por
                  ruta, fragilidad de los factores activos) sobre la GraphCore de la generación vigente, con
                  las relaciones de FLUJO solamente: BRECHAS #4 (valor por defecto vigente) = socios e
                  inversores NO transmiten daño. Paso 8 (M-code-01): antes el tensor propagaba por su cuenta
                  y sin factores. Cuando el paso 12 lleve BRECHAS #4 al kernel, Ψ = la vista V2 Impact.
  c  ∈ ℝ^N        capitalización (USD B): en vivo (core.live_caps) → valuación VERIFICADA de privadas
                  (nodes/private_valuations.js) → sin dato (0, y se dice).
  X  ∈ ℝ^{N×F}    tensor de rasgos (FEATURES), z-normalizado, + perfil estructural (filas y columnas
                  de A) para medir parecido.

Métricas por empresa (lo que un inversionista no ve en una planilla):
  · concentración de proveedores (HHI de la columna de A sobre proveedores directos): "depende en
    un 62 % de TSMC";
  · países de sus proveedores (participación por país de origen);
  · capitalización AGUAS ABAJO en riesgo: Σ_j Ψ[j,s]·c_j — cuánto valor de mercado de clientes y
    clientes-de-clientes queda expuesto si esta empresa falla (importancia sistémica en dólares);
  · fuentes de riesgo AGUAS ARRIBA: las s con mayor Ψ[j,s] (no solo proveedores directos);
  · comparables: vecinos más cercanos en X (mismos proveedores/clientes + rasgos), no solo "mismo sector".

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


# ─────────────────────────── carga ───────────────────────────
def _load_snapshot():
    """El grafo vigente con la forma del snapshot (Mapping de solo lectura de la vista `graph`)."""
    from core.hotviews import hot
    return hot.graph().snapshot


def _psi_from_impact(imp, ids, idx):
    """Ψ[j,s] (0-1) desde la vista Impact: víctimas del colapso unitario de cada fuente s (pct/100)."""
    n = len(ids)
    psi = np.zeros((n, n))
    if imp is None:
        return psi
    for s, si in idx.items():
        hit = imp.victims.get(s)
        if not hit:
            continue
        vids, pct, _hop = hit
        for k, p in zip(vids, pct):
            j = idx.get(k)
            if j is not None and j != si and p > 0:
                psi[j, si] = p / 100.0
    return psi


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
    (BRECHAS #4, valor por defecto vigente mientras Fabrizio no responda). Cuando el paso 12 lleve esa regla
    al kernel, esta máscara queda igual a la vista Impact y el tensor vuelve a leerla tal cual."""
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


# ─────────────────────────── modelo ───────────────────────────
class Model:
    """Tensores del grafo ya calculados (inmutable; se reemplaza entero al cambiar la entrada)."""

    def __init__(self, snap, caps_live=None, caps_private=None, caps_as_of=None, view=None):
        t0 = time.time()
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
        # ── Ψ = la vista Impact (EL kernel del servidor, factores activos incluidos): la de la generación
        #    vigente, o —para un grafo armado a mano (evaluate, pruebas)— la misma vista calculada sobre él
        core = view.core if view is not None else _core_for(snap)
        imp = _flow_impact(core)
        self.psi_method = 'impact_kernel_flow_only:propagate@1'
        psi = _psi_from_impact(imp, self.ids, self.idx)
        self.psi = psi                                                        # psi[j, s]
        # ── proveedores directos (columna de A sobre SUPPLIER_RELS)
        S = None
        for r in SUPPLIER_RELS:
            if r in self.A:
                S = self.A[r] if S is None else S + self.A[r]
        self.S = S.tocsc()
        Sr = S.tocsr()
        self.n_sup = np.diff(self.S.indptr)
        self.n_cus = np.diff(Sr.indptr)
        self.hhi = np.zeros(n)
        for j in range(n):
            a, b = self.S.indptr[j], self.S.indptr[j + 1]
            if b > a:
                w = self.S.data[a:b]
                sh = w / w.sum()
                self.hhi[j] = float((sh ** 2).sum())
        self.down_cap = psi.T @ self.cap                                      # Σ_j psi[j,s]·c_j
        self.up_exposure = psi.max(axis=1)                                    # peor fuente para j
        # ── X: rasgos z-normalizados + perfil estructural para parecido (coseno)
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
        self.Abin = Abin.tocsr()
        prof = np.hstack([Abin.toarray(), Abin.T.toarray()])                  # [clientes | proveedores]
        nrm = np.linalg.norm(prof, axis=1)
        nrm[nrm == 0] = 1.0
        self.prof = prof / nrm[:, None]
        # ── bloques por categoría del tensor (prior de auto-conexión)
        self.cat = [self.node[k].get('cat') or '?' for k in self.ids]
        self.sector = [self.node[k].get('sector') or '?' for k in self.ids]
        self.country = [_country(self.node[k].get('country')) for k in self.ids]
        self.n_cat = Counter(self.cat)
        self.block = defaultdict(float)                                       # (cat_s, cat_t, r) → nº
        for r in self.rels:
            co = self.A[r].tocoo()
            for i, j in zip(co.row, co.col):
                self.block[(self.cat[i], self.cat[j], r)] += 1.0
        self.tok = [_tokens(self.node[k].get('label'), self.node[k].get('role'), self.node[k].get('supplies'))
                    for k in self.ids]
        self.ms = round((time.time() - t0) * 1000)

    # ── utilidades
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


def model(force=False, snap=None, view=None):
    """Modelo vigente (caché). Se reconstruye si cambia la GENERACIÓN del grafo (paso 8: antes, la fecha del
    archivo del snapshot) o la versión de las caps en vivo. `view` (GraphView): el de UNA generación concreta (la
    tarjeta V3 de esa generación, paso 14) — sin pasar por hot.graph() (que puede esperar al constructor)."""
    caps_live, caps_as_of = _caps_live()
    if snap is not None:
        return Model(snap, caps_live, _caps_private(), caps_as_of)
    if view is None:
        from core.hotviews import hot
        view = hot.graph()
    key = (view.generation, caps_as_of, len(caps_live))
    with _LOCK:
        if not force and _MODEL['m'] is not None and _MODEL['key'] == key:
            return _MODEL['m']
    m = Model(view.snapshot, caps_live, _caps_private(), caps_as_of, view=view)
    with _LOCK:
        _MODEL.update(m=m, key=key)
    return m


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
    # aguas arriba: de dónde le llega el riesgo (Ψ fila j)
    row = m.psi[j]
    src = [int(i) for i in np.argsort(-row)[:top] if row[i] > 0]
    # aguas abajo: a quién arrastra (Ψ columna j) y cuánta capitalización
    col = m.psi[:, j]
    dn = [int(i) for i in np.argsort(-(col * np.maximum(m.cap, 1e-9)))[:top] if col[i] > 0]
    n_down = int((col > 0).sum())
    rank = int((m.down_cap > m.down_cap[j]).sum()) + 1
    covered = float((m.cap[col > 0] > 0).sum()) / max(1, n_down) if n_down else None
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
            'top': [{'id': m.ids[i], 'label': m.label(m.ids[i]), 'impact_pct': round(float(col[i]) * 100, 1),
                     'cap_usd_b': round(float(m.cap[i]), 1) if m.cap[i] > 0 else None} for i in dn]},
        'upstream_risk_sources': [{'id': m.ids[i], 'label': m.label(m.ids[i]),
                                   'exposure_pct': round(float(row[i]) * 100, 1),
                                   'direct': bool(i in set(rows.tolist()))} for i in src],
        'peers': peers(k, m=m, n=5),
        'cap_usd_b': round(float(m.cap[j]), 1) if m.cap[j] > 0 else None,
        'cap_source': m.cap_src[j],
        'method': ('flow tensor (supply/fab/cloud/license/ppa/owns/deploy, conf-weighted) · influence Ψ = Impact '
                   'view (server kernel propagate@1: damping 0.6 · 6 hops · active factors)'),
        'caps_as_of': m.caps_as_of,
    }


def peers(nid, m=None, n=5):
    """Comparables: mismos proveedores/clientes (coseno del perfil) + rasgos (X) + misma categoría."""
    m = m or model()
    j = m.i_of(nid)
    if j is None:
        return []
    sim = m.prof @ m.prof[j]
    dx = np.linalg.norm(m.X - m.X[j], axis=1)
    sim = 0.6 * sim + 0.25 * np.exp(-dx / 2.0) + 0.15 * (np.array(m.cat) == m.cat[j])
    sim[j] = -1
    out = []
    for i in np.argsort(-sim)[:n]:
        out.append({'id': m.ids[i], 'label': m.label(m.ids[i]), 'similarity': round(float(sim[i]), 3)})
    return out


def ranking(m=None, by='cap_at_risk', limit=20):
    m = m or model()
    if by == 'concentration':
        order = [i for i in np.argsort(-m.hhi) if m.n_sup[i] >= 1]
        val = lambda i: round(float(m.hhi[i]), 3)  # noqa: E731
    elif by == 'exposure':
        order = list(np.argsort(-m.up_exposure))
        val = lambda i: round(float(m.up_exposure[i]) * 100, 1)  # noqa: E731
    else:
        order = list(np.argsort(-m.down_cap))
        val = lambda i: round(float(m.down_cap[i]), 1)  # noqa: E731
    return [{'id': m.ids[i], 'label': m.label(m.ids[i]), 'value': val(i)} for i in order[:max(1, min(100, limit))]]


# ─────────────────────────── auto-conexión ───────────────────────────
def _peer_weights(m, j=None, new=None, k=None):
    """Pesos de parecido con el resto: existente (perfil+rasgos) o NUEVA (cat/sector/país/texto)."""
    if j is not None:
        sim = m.prof @ m.prof[j]
        sim = 0.7 * sim + 0.3 * (np.array(m.cat) == m.cat[j])
        sim[j] = 0
    else:
        cat, sec, ctry = new.get('cat'), new.get('sector'), _country(new.get('country'))
        tk = _tokens(new.get('label'), new.get('role'), new.get('supplies'))
        sim = np.zeros(m.n)
        for i in range(m.n):
            s = 1.0 if (cat and m.cat[i] == cat) else (0.35 if (sec and m.sector[i] == sec) else 0.0)
            if tk and m.tok[i]:
                s += 0.8 * len(tk & m.tok[i]) / len(tk | m.tok[i])
            if ctry and m.country[i] == ctry:
                s += 0.1
            sim[i] = s
    top = np.argsort(-sim)[:(k or N_PEERS)]
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
            'graph_version': m.graph_version, 'psi': m.psi_method}
