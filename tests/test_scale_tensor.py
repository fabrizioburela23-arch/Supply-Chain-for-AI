"""tests/test_scale_tensor.py — E1.2 (docs/expansion/EXPANSION_5K.md): el tensor DISPERSO da las MISMAS cifras que el
denso de antes sobre el snapshot real (937 empresas), con kernel.params 1.0.0 y 2.0.0.

La referencia es una COPIA del código denso (matrix/tensor.py hasta 2026-10-14: Ψ y perfil N×N densos, segunda
pasada del kernel siempre). Cambios deliberados: el ORDEN de los empates; en el corte de N_PEERS de suggest_links un
grupo empatado entra ENTERO con peso fraccionario (antes un sorteo de np.argsort; sin empate en el borde = igual,
test_sin_empate_en_el_borde_igual_al_codigo_de_siempre); Ψᵀc con math.fsum (exacta). Antes lo decidía np.argsort (no
estable: con AVX-512 cambia el orden de los iguales; en 937 empresas, 629 listas de comparables salían distintas
de un orden estable). Ahora: de mayor a menor y, en empate, por id; las SUMAS (parecido, Ψᵀc) se comparan
redondeadas (12 decimales / 12 cifras) porque BLAS (denso) y la suma dispersa difieren en la última cifra binaria.
Por eso la referencia ordena con esa misma regla (`_ref_order`) y, aparte, se comprueba contra el np.argsort de
siempre que los VALORES rango por rango son los mismos (solo cambió qué empatado va primero).
Tolerancia de las cifras: 1e-12 (relativa para las capitalizaciones).
"""
import math
import os
import sys
from collections import Counter, defaultdict
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

TOL = 1e-12


# ════════════════════════════════════════════════════════════════════════════
# referencia: el código DENSO de antes (copia; solo el orden de empates es `_ref_order`)
# ════════════════════════════════════════════════════════════════════════════
def _ref_round_sig(v, digits=12):
    v = np.asarray(v, dtype=float)
    out = np.zeros_like(v)
    for i, x in enumerate(v.tolist()):
        if x != 0:
            e = math.floor(math.log10(abs(x)))
            s = 10.0 ** (digits - 1 - e)
            out[i] = np.round(x * s) / s
    return out


def _ref_order(v, stable=True):
    """stable=True: la regla nueva (mayor a menor, empates por posición = id). False: el np.argsort de antes."""
    v = np.asarray(v, dtype=float)
    return np.argsort(-v, kind='stable') if stable else np.argsort(-v)


def _ref_flow_impact(core, T, E, vocab):
    flow = set(vocab.flow_relation_types())
    mats = {r: m for r, m in core.mats.items() if r in flow}
    out = {}
    res = E.propagate_many(mats, core.idx, core.ids, list(core.ids), damping=T.DAMPING, max_hops=T.MAX_HOPS,
                           threshold=T.THRESHOLD, frag=core.frag, dt=E.dependency_transpose(mats))
    for oid in core.ids:
        impacts, hops = res.get(oid, ({}, {}))
        if not impacts:
            continue
        order = sorted(impacts.items(), key=lambda kv: (-kv[1], hops.get(kv[0], 0), kv[0]))
        out[oid] = (tuple(k for k, _ in order), tuple(p for _, p in order), tuple(hops.get(k, 0) for k, _ in order))
    return out


class _DenseRef:
    """matrix.tensor.Model de antes (denso)."""

    def __init__(self, snap, caps_live, caps_private, core, T, E, vocab):
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
        self.A = {r: mats[r].tocsr() for r in self.rels}
        self.cap = np.zeros(n)
        self.cap_src = [None] * n
        for i, k in enumerate(self.ids):
            if k in caps_live:
                self.cap[i], self.cap_src[i] = caps_live[k], 'live'
            elif k in caps_private:
                self.cap[i], self.cap_src[i] = caps_private[k], 'verified_valuation'
        victims = _ref_flow_impact(core, T, E, vocab)
        psi = np.zeros((n, n))
        for s, si in self.idx.items():
            hit = victims.get(s)
            if not hit:
                continue
            vids, pct, _hop = hit
            for k, p in zip(vids, pct):
                j = self.idx.get(k)
                if j is not None and j != si and p > 0:
                    psi[j, si] = p / 100.0
        self.psi = psi
        S = None
        for r in T.SUPPLIER_RELS:
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
        self.down_cap = psi.T @ self.cap
        self.up_exposure = psi.max(axis=1)
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
        prof = np.hstack([Abin.toarray(), Abin.T.toarray()])
        nrm = np.linalg.norm(prof, axis=1)
        nrm[nrm == 0] = 1.0
        self.prof = prof / nrm[:, None]
        self.cat = [self.node[k].get('cat') or '?' for k in self.ids]
        self.sector = [self.node[k].get('sector') or '?' for k in self.ids]
        self.country = [T._country(self.node[k].get('country')) for k in self.ids]
        self.n_cat = Counter(self.cat)
        self.block = defaultdict(float)
        for r in self.rels:
            co = self.A[r].tocoo()
            for i, j in zip(co.row, co.col):
                self.block[(self.cat[i], self.cat[j], r)] += 1.0
        self.tok = [T._tokens(self.node[k].get('label'), self.node[k].get('role'), self.node[k].get('supplies'))
                    for k in self.ids]

    def label(self, k):
        return (self.node.get(k) or {}).get('label') or k

    def cat_prior(self, cs, ct, r):
        a, b = self.n_cat.get(cs, 0), self.n_cat.get(ct, 0)
        if not a or not b:
            return 0.0
        return self.block.get((cs, ct, r), 0.0) / float(a * b)


def _conc_label(h, n):
    if n <= 0:
        return None
    if n == 1 or h >= 0.5:
        return 'alta'
    if h >= 0.25:
        return 'media'
    return 'baja'


def _ref_peers(m, j, n=5, stable=True):
    sim = m.prof @ m.prof[j]
    dx = np.linalg.norm(m.X - m.X[j], axis=1)
    sim = 0.6 * sim + 0.25 * np.exp(-dx / 2.0) + 0.15 * (np.array(m.cat) == m.cat[j])
    sim[j] = -1
    order = _ref_order(np.round(sim, 12) if stable else sim, stable)
    return [{'id': m.ids[i], 'label': m.label(m.ids[i]), 'similarity': round(float(sim[i]), 3)} for i in order[:n]]


def _ref_structure(m, j, top=5, stable=True):
    k = m.ids[j]
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
    row = m.psi[j]
    src = [int(i) for i in _ref_order(row, stable)[:top] if row[i] > 0]
    col = m.psi[:, j]
    dn = [int(i) for i in _ref_order(col * np.maximum(m.cap, 1e-9), stable)[:top] if col[i] > 0]
    n_down = int((col > 0).sum())
    dk = _ref_round_sig(m.down_cap) if stable else m.down_cap
    rank = int((dk > dk[j]).sum()) + 1
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
        'peers': _ref_peers(m, j, 5, stable),
        'cap_usd_b': round(float(m.cap[j]), 1) if m.cap[j] > 0 else None,
        'cap_source': m.cap_src[j],
    }


def _ref_ranking(m, by, limit, stable=True):
    if by == 'concentration':
        order = [i for i in _ref_order(np.round(m.hhi, 12) if stable else m.hhi, stable) if m.n_sup[i] >= 1]
        val = lambda i: round(float(m.hhi[i]), 3)  # noqa: E731
    elif by == 'exposure':
        order = list(_ref_order(m.up_exposure, stable))
        val = lambda i: round(float(m.up_exposure[i]) * 100, 1)  # noqa: E731
    else:
        order = list(_ref_order(_ref_round_sig(m.down_cap) if stable else m.down_cap, stable))
        val = lambda i: round(float(m.down_cap[i]), 1)  # noqa: E731
    return [{'id': m.ids[i], 'label': m.label(m.ids[i]), 'value': val(i)} for i in order[:max(1, min(100, limit))]]


def _ref_peer_weights(m, T, j=None, new=None, k=None):
    if j is not None:
        sim = m.prof @ m.prof[j]
        sim = 0.7 * sim + 0.3 * (np.array(m.cat) == m.cat[j])
        sim[j] = 0
    else:
        cat, sec, ctry = new.get('cat'), new.get('sector'), T._country(new.get('country'))
        tk = T._tokens(new.get('label'), new.get('role'), new.get('supplies'))
        sim = np.zeros(m.n)
        for i in range(m.n):
            s = 1.0 if (cat and m.cat[i] == cat) else (0.35 if (sec and m.sector[i] == sec) else 0.0)
            if tk and m.tok[i]:
                s += 0.8 * len(tk & m.tok[i]) / len(tk | m.tok[i])
            if ctry and m.country[i] == ctry:
                s += 0.1
            sim[i] = s
    return _ref_cut(sim, k or T.N_PEERS)


def _ref_cut(sim, k, legacy=False):
    """legacy=True: el np.argsort NO estable de antes (k al azar entre los empatados del borde). Si no, la regla
    nueva: el grupo empatado en el borde entra entero con peso × lugares/tamaño (el valor esperado de ese sorteo)."""
    if legacy:
        top = np.argsort(-sim)[:k]
        return [(int(i), float(sim[i])) for i in top if sim[i] > 0]
    key = np.round(sim, 12)
    top = list(_ref_order(key)[:k])
    if len(top) == k and k < len(key) and key[top[-1]] > 0:
        edge = key[top[-1]]
        group = [i for i in range(len(key)) if key[i] == edge]
        inside = [i for i in top if key[i] != edge]
        slots = k - len(inside)
        if len(group) > slots:
            f = slots / len(group)
            return ([(int(i), float(sim[i])) for i in inside if sim[i] > 0]
                    + [(int(i), float(sim[i]) * f) for i in group if sim[i] > 0])
    return [(int(i), float(sim[i])) for i in top if sim[i] > 0]


def _boundary_tie(sim, k):
    """¿El corte de las k primeras cae dentro de un grupo de empatados (a 12 decimales)?"""
    key = np.round(sim, 12)
    if k >= len(key):
        return False
    srt = np.sort(key)[::-1]
    return bool(srt[k - 1] > 0 and srt[k - 1] == srt[k])


def _ref_sim(m, T, j):
    sim = m.prof @ m.prof[j]
    sim = 0.7 * sim + 0.3 * (np.array(m.cat) == m.cat[j])
    sim[j] = 0
    return sim


def _ref_suggest(m, T, j=None, new=None, n=10, legacy=False):
    me = m.ids[j] if j is not None else None
    cat_s = m.cat[j] if j is not None else (new.get('cat') or '?')
    if legacy:
        pw = _ref_cut(_ref_sim(m, T, j), T.N_PEERS, legacy=True)
    else:
        pw = _ref_peer_weights(m, T, j=j, new=None if j is not None else new)
    tot = sum(w for _, w in pw) or 1.0
    have = set()
    if j is not None:
        for r in m.rels:
            have |= {(m.ids[t], r, 'out') for t in m.A[r][j].indices}
            have |= {(m.ids[s], r, 'in') for s in m.A[r][:, j].tocoo().row}
    cand = defaultdict(lambda: {'p': 0.0, 'via': []})
    for i, w in pw:
        for r in m.rels:
            for t in m.A[r][i].indices:
                if t != j:
                    c = cand[(int(t), r, 'out')]; c['p'] += w / tot; c['via'].append(m.ids[i])  # noqa: E702
            for s in m.A[r][:, i].tocoo().row:
                if s != j:
                    c = cand[(int(s), r, 'in')]; c['p'] += w / tot; c['via'].append(m.ids[i])  # noqa: E702
    rows = []
    for (o, r, d), c in cand.items():
        other = m.ids[o]
        if (other, r, d) in have:
            continue
        prior = m.cat_prior(cat_s, m.cat[o], r) if d == 'out' else m.cat_prior(m.cat[o], cat_s, r)
        score = T.W_PEERS * c['p'] + T.W_CAT * min(1.0, prior * 10)
        via = list(dict.fromkeys(c['via']))[:3]
        rows.append({'direction': 'customer' if d == 'out' else 'supplier', 'id': other, 'label': m.label(other),
                     'rel': r, 'score': round(score, 3), 'peers_with_link': len(set(c['via'])),
                     'via': [{'id': v, 'label': m.label(v)} for v in via],
                     'source': me if d == 'out' else other, 'target': other if d == 'out' else me})
    rows.sort(key=lambda x: -x['score'])
    return {'id': me, 'suppliers': [x for x in rows if x['direction'] == 'supplier'][:n],
            'customers': [x for x in rows if x['direction'] == 'customer'][:n],
            'peers': [{'id': m.ids[i], 'label': m.label(m.ids[i]), 'weight': round(w, 3)} for i, w in pw[:5]]}


# ════════════════════════════════════════════════════════════════════════════
# utilidades
# ════════════════════════════════════════════════════════════════════════════
def _close(a, b, path='$', bad=None):
    """Igualdad profunda; los números con tolerancia TOL (relativa si son grandes)."""
    bad = [] if bad is None else bad
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            bad.append((path, 'keys', sorted(set(a) ^ set(b))))
        for k in set(a) & set(b):
            _close(a[k], b[k], f'{path}.{k}', bad)
    elif isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if len(a) != len(b):
            bad.append((path, 'len', len(a), len(b)))
        for i, (x, y) in enumerate(zip(a, b)):
            _close(x, y, f'{path}[{i}]', bad)
    elif isinstance(a, bool) or isinstance(b, bool) or a is None or b is None or isinstance(a, str):
        if a != b:
            bad.append((path, a, b))
    elif isinstance(a, (int, float, np.integer, np.floating)) and isinstance(b, (int, float, np.integer, np.floating)):
        if abs(float(a) - float(b)) > TOL * max(1.0, abs(float(b))):
            bad.append((path, a, b))
    elif a != b:
        bad.append((path, a, b))
    return bad


def _caps(ids):
    """Capitalizaciones sintéticas fijas (sin red): 60 % en vivo, 15 % valuación verificada, el resto sin dato."""
    rng = np.random.default_rng(1234)
    live, priv = {}, {}
    for k in ids:
        u = rng.random()
        v = float(rng.lognormal(2.0, 2.2))
        if u < 0.60:
            live[k] = v
        elif u < 0.75:
            priv[k] = v
    return live, priv


@pytest.fixture(scope='module', params=['1.0.0', '2.0.0'])
def pair(request):
    """(semver, nuevo, referencia densa) sobre el snapshot real, con la generación armada con ESE kernel."""
    from core import governance
    from core.hotviews import source
    from core.hotviews.views import graph_core, impact
    from matrix import engine as E
    from matrix import tensor as T
    from ontology import vocabulary as vocab
    sem = request.param
    with governance.counterfactual({'kernel.params': sem}):
        data = source.load_snapshot()
        core = graph_core.build(data)
        imp = impact.build(core)
        snap = {'nodes': data.nodes, 'links': data.links}
        live, priv = _caps([n['id'] for n in data.nodes])
        view = SimpleNamespace(core=core, impact=imp, generation=f'test-scale-tensor-{sem}', graph_version=0,
                               snapshot=snap)
        new = T.Model(snap, live, priv, 'test', view=view)
        ref = _DenseRef(snap, live, priv, core, T, E, vocab)
    return sem, new, ref                # el contrafactual NO queda activo para las pruebas


# ════════════════════════════════════════════════════════════════════════════
# pruebas
# ════════════════════════════════════════════════════════════════════════════
def test_psi_y_vectores_iguales_al_denso(pair):
    sem, m, r = pair
    assert m.n == r.n >= 900 and m.ids == r.ids
    assert m.psi_source == ('impact_view' if sem.startswith('2.') else 'flow_pass')   # 2.x: sin segunda pasada
    assert np.array_equal(m.psi.toarray(), r.psi)                                       # Ψ: bit a bit
    assert m.psi.nnz == int(np.count_nonzero(r.psi))
    assert np.array_equal(m.up_exposure, r.up_exposure)
    assert np.array_equal(m.n_sup, r.n_sup) and np.array_equal(m.n_cus, r.n_cus)
    assert np.array_equal(m.hhi, r.hhi)                                                 # HHI: bit a bit
    assert np.allclose(m.down_cap, r.down_cap, rtol=TOL, atol=TOL)
    assert np.allclose(m.X, r.X, rtol=0, atol=1e-9)        # z-normalizado de lo anterior (escala ≤ ~1e3)
    assert np.array_equal(m.prof.csr.toarray(), r.prof)                                 # perfil: bit a bit
    assert m.country == r.country and m.cat == r.cat and dict(m.block) == dict(r.block)
    for j in range(0, m.n, 7):                                                          # el coseno disperso
        assert np.allclose(m.prof @ m.prof[j], r.prof @ r.prof[j], rtol=0, atol=TOL)
    # la compatibilidad de índice que usan otras pruebas y el MCP (psi[j, s], psi[:, s], prof @ prof[j])
    s = m.idx['TSMC']
    assert np.array_equal(m.psi[:, s], r.psi[:, s]) and np.array_equal(m.psi[s], r.psi[s])
    j = int(np.flatnonzero(r.psi[:, s])[0])
    assert m.psi[j, s] == r.psi[j, s] > 0


def test_ficha_estructural_de_todas_las_empresas(pair):
    from matrix import tensor as T
    sem, m, r = pair
    bad = {}
    for j, k in enumerate(m.ids):
        new = T.structure(k, m, top=5)
        for key in ('method', 'caps_as_of'):
            new.pop(key)
        diff = _close(new, _ref_structure(r, j, 5, stable=True))
        if diff:
            bad[k] = diff[:3]
    assert not bad, (sem, len(bad), list(bad.items())[:5])


def test_solo_cambio_el_orden_de_los_empatados(pair):
    """Contra el np.argsort de antes (verbatim): rango por rango, los MISMOS valores (de las matrices densas de la
    referencia); fuera de las listas, todo idéntico. Solo cambió qué empatado va primero."""
    from matrix import tensor as T
    sem, m, r = pair
    catarr = np.array(r.cat)
    for j, k in enumerate(m.ids):
        new = T.structure(k, m, top=5)
        old = _ref_structure(r, j, 5, stable=False)
        up = lambda lst: [r.psi[j, r.idx[x['id']]] for x in lst]  # noqa: E731
        assert up(new['upstream_risk_sources']) == up(old['upstream_risk_sources']), k
        dn = lambda lst: [r.psi[r.idx[x['id']], j] * max(r.cap[r.idx[x['id']]], 1e-9) for x in lst]  # noqa: E731
        assert dn(new['downstream']['top']) == dn(old['downstream']['top']), k
        sim = r.prof @ r.prof[j]
        sim = 0.6 * sim + 0.25 * np.exp(-np.linalg.norm(r.X - r.X[j], axis=1) / 2.0) + 0.15 * (catarr == r.cat[j])
        pv = lambda lst: [sim[r.idx[x['id']]] for x in lst]  # noqa: E731
        assert np.allclose(pv(new['peers']), pv(old['peers']), rtol=0, atol=TOL), k
        for key in ('supplier_concentration', 'supplier_countries', 'cap_usd_b', 'cap_source'):
            assert new[key] == old[key], (k, key)
        nd, od = dict(new['downstream']), dict(old['downstream'])
        nd.pop('top'), od.pop('top')
        assert nd == od, k


def test_ranking_igual(pair):
    from matrix import tensor as T
    sem, m, r = pair
    for by in ('cap_at_risk', 'concentration', 'exposure'):
        assert T.ranking(m, by, 100) == _ref_ranking(r, by, 100), (sem, by)
        assert [x['value'] for x in T.ranking(m, by, 100)] == [x['value'] for x in _ref_ranking(r, by, 100, False)]


def test_suggest_links_igual(pair):
    from matrix import tensor as T
    sem, m, r = pair
    for j in range(0, m.n, 5):
        new = T.suggest_links(m.ids[j], m=m, n=10)
        ref = _ref_suggest(r, T, j=j, n=10)
        assert not _close({k: new[k] for k in ref}, ref), (sem, m.ids[j], _close({k: new[k] for k in ref}, ref)[:3])
    for nd in ({'label': 'Nueva HBM Corp', 'cat': 'memory', 'country': 'Corea'},
               {'label': 'Andes Lithium', 'cat': 'materials', 'sector': 'materiales', 'country': 'Chile'},
               {'label': 'GPU Cloud Perú', 'role': 'nube de GPUs para IA', 'country': 'Perú'}):
        new = T.suggest_links(new=nd, m=m, n=10)
        ref = _ref_suggest(r, T, new=nd, n=10)
        assert not _close({k: new[k] for k in ref}, ref), (sem, nd['label'])


def test_sin_empate_en_el_borde_igual_al_codigo_de_siempre(pair):
    """Contra el np.argsort NO estable de antes, tal cual: toda empresa cuyo corte de N_PEERS no cae en un grupo de
    empatados da EXACTAMENTE las mismas propuestas y puntajes. Las que sí (≈1/3) eran un sorteo dependiente de la CPU:
    ahora entra el grupo entero con peso fraccionario (el valor esperado de ese sorteo)."""
    from matrix import tensor as T
    sem, m, r = pair
    clean = tied = 0
    diff_n = [0]
    for j in range(0, m.n, 3):
        if _boundary_tie(_ref_sim(r, T, j), T.N_PEERS):
            tied += 1
            continue
        clean += 1
        new = T.suggest_links(m.ids[j], m=m, n=10)
        old = _ref_suggest(r, T, j=j, n=10, legacy=True)
        # mismos pares con el mismo peso (los empatados DENTRO del corte entran igual; solo cambia el orden)
        pa = sorted((i, round(w, 12)) for i, w in T._peer_weights(m, j=j))
        pb = sorted((i, round(w, 12)) for i, w in _ref_cut(_ref_sim(r, T, j), T.N_PEERS, legacy=True))
        assert pa == pb, (sem, m.ids[j])
        for side in ('suppliers', 'customers'):
            fa = sorted((x['id'], x['rel'], x['score'], x['peers_with_link']) for x in new[side])
            fb = sorted((x['id'], x['rel'], x['score'], x['peers_with_link']) for x in old[side])
            if fa != fb:      # el corte de n=10 puede caer entre puntajes iguales: mismos puntajes
                diff_n[0] += 1
                assert sorted(x['score'] for x in new[side]) == sorted(x['score'] for x in old[side]), \
                    (sem, m.ids[j], side, fa, fb)
    assert clean > 100 and tied > 0 and diff_n[0] <= clean // 10, (clean, tied, diff_n)


def test_corte_con_empates_sin_sesgo_por_id():
    """El grupo empatado en el borde entra entero (peso × lugares/tamaño); el resultado no depende de los ids."""
    from matrix import tensor as T
    sim = np.array([0.9, 0.5, 0.5, 0.5, 0.5, 0.2, 0.0])
    assert T._cut_with_ties(sim, 3) == [(0, 0.9), (1, 0.25), (2, 0.25), (3, 0.25), (4, 0.25)]
    assert T._cut_with_ties(sim, 5) == [(0, 0.9), (1, 0.5), (2, 0.5), (3, 0.5), (4, 0.5)]   # sin empate en el borde
    assert T._cut_with_ties(np.array([1.0, 0.0, 0.0]), 2) == [(0, 1.0)]                       # ceros: nunca entran
    # una empresa NUEVA cuyo rubro empata entero: las mismas propuestas aunque los ids se ordenen al revés
    mk = lambda pre: {'nodes': [{'id': f'{pre}{c}', 'label': f'Peer {c}', 'cat': 'memory', 'country': 'Corea'}  # noqa: E731
                                for c in 'abcdefgh'] + [{'id': f'{pre}S{c}', 'label': f'Sup {c}', 'cat': 'fab'}
                                                         for c in 'abcdefgh'],
                      'links': [{'source': f'{pre}S{c}', 'target': f'{pre}{c}', 'w': 3, 'type': 'supply', 'conf': 1}
                                for c in 'abcdefgh']}
    out = []
    for pre in ('a_', 'Z_'):
        m = T.Model(mk(pre))
        res = T.suggest_links(new={'label': 'Nueva', 'cat': 'memory'}, m=m, n=10)
        out.append(sorted((x['id'][2:], x['rel'], x['score']) for x in res['suppliers']))
    assert out[0] == out[1] and len(out[0]) == 8


def test_tokens_a_pedido_y_con_cache():
    """Los tokens de texto (0,67 s a 5k) ya no se arman al construir: solo si suggest_links recibe una empresa NUEVA."""
    from matrix import tensor as T
    n = lambda i, cat: {'id': i, 'label': f'{i} Chips', 'cat': cat, 'sector': 'x', 'country': 'EEUU'}  # noqa: E731
    snap = {'nodes': [n('A', 'fab'), n('B', 'chip'), n('C', 'chip')],
            'links': [{'source': 'A', 'target': 'B', 'w': 3, 'type': 'supply', 'conf': 1},
                      {'source': 'A', 'target': 'C', 'w': 3, 'type': 'supply', 'conf': 1}]}
    m = T.Model(snap)
    assert m._tok is None
    T.suggest_links('B', m=m)
    assert m._tok is None                                   # una existente no los necesita
    r = T.suggest_links(new={'label': 'D Chips', 'cat': 'chip'}, m=m)
    assert m._tok is not None and r['suppliers'][0]['id'] == 'A'
    assert T._TOK['B'][1] == frozenset({'chips'})
    m2 = T.Model(snap)
    assert m2.tok[1] is m.tok[1]                            # misma empresa, mismo texto → la misma tupla de tokens


def test_un_solo_constructor_por_clave(monkeypatch):
    """El prewarm y un lector que llega a la vez esperan UNA construcción (antes: dos modelos en paralelo)."""
    import threading
    from matrix import tensor as T
    n = lambda i: {'id': i, 'label': i, 'cat': 'x', 'sector': 'x', 'country': 'EEUU'}  # noqa: E731
    snap = {'nodes': [n('A'), n('B')], 'links': [{'source': 'A', 'target': 'B', 'w': 3, 'type': 'supply'}]}
    view = SimpleNamespace(core=None, impact=None, generation='test-single-flight', graph_version=0, snapshot=snap)
    monkeypatch.setattr(T, '_caps_live', lambda: ({}, 'caps-x'))
    monkeypatch.setattr(T, '_caps_private', lambda: {})
    built, gate = [], threading.Event()
    real = T.Model

    class Slow(real):
        def __init__(self, *a, **k):
            built.append(1)
            gate.wait(5)
            super().__init__(*a, **k)
    monkeypatch.setattr(T, 'Model', Slow)
    monkeypatch.setitem(T._MODEL, 'm', None)
    monkeypatch.setitem(T._MODEL, 'key', None)
    out = []
    ths = [threading.Thread(target=lambda: out.append(T.model(view=view))) for _ in range(3)]
    for t in ths:
        t.start()
    for _ in range(100):
        if built:
            break
        threading.Event().wait(0.01)
    gate.set()
    for t in ths:
        t.join(10)
    assert len(built) == 1 and len(out) == 3 and out[0] is out[1] is out[2]
    assert not T._BUILDING


def test_empates_por_id():
    from matrix import tensor as T
    v = np.array([0.5, 0.7, 0.5, 0.7, 0.1, 0.0, 0.7])
    assert T._order(v).tolist() == [1, 3, 6, 0, 2, 4, 5]
    assert T._order(v, 2).tolist() == [1, 3] and T._order(v, 4).tolist() == [1, 3, 6, 0]
    big = np.repeat([3.0, 2.0, 1.0], 400)
    assert T._order(big, 5).tolist() == [0, 1, 2, 3, 4]
    assert T._round_sig(np.array([0.0, 123456.7890123456, 1e-7 + 1e-20])).tolist() == [0.0, 123456.789012, 1e-07]


def test_api_eval_y_status(monkeypatch):
    """/api/tensor/eval leía T.SNAPSHOT (borrado en el paso 8) y respondía 500; ahora se guarda por generación.
    /api/tensor/status dice de dónde salió Ψ y cuánto ocupa."""
    from flask import Flask
    from matrix import tensor as T
    from matrix.tensor_api import _EVAL, tensor_bp
    calls = []
    monkeypatch.setattr(T, 'evaluate', lambda seed=7, **k: calls.append(seed) or {
        'cases': 60, 'k': 10, 'hit_rate': 0.4, 'baseline_popularity': 0.2, 'seed': seed, 'frac': 0.1})
    monkeypatch.setitem(_EVAL, 'key', None)
    monkeypatch.setitem(_EVAL, 'data', None)
    app = Flask(__name__)
    app.register_blueprint(tensor_bp)
    c = app.test_client()
    r = c.get('/api/tensor/eval')
    assert r.status_code == 200 and r.get_json()['hit_rate'] == 0.4 and calls == [7, 11, 23]
    assert c.get('/api/tensor/eval').status_code == 200 and calls == [7, 11, 23]     # misma generación: no repite
    st = c.get('/api/tensor/status').get_json()
    assert st['psi_source'] in ('impact_view', 'flow_pass') and st['psi_nnz'] > 1000 and 0 < st['memory_kb'] < 20000
