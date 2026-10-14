"""tests/test_scale_search.py — EXPANSION_5K E1.5: búsqueda por índice (prefijos + trigramas) = recorrido lineal.

core/entities arma por generación un índice de prefijos y trigramas sobre id/etiqueta/ticker/alias/alias de voz (+ la
descripción normalizada) y resolve() / search_scores() / MCP search_companies lo usan para ELEGIR candidatos; el
puntaje es la misma escalera de siempre. Aquí vive la implementación LINEAL de antes (copiada tal cual, con el norm()
viejo) como referencia: en 200+ consultas variadas (ids, tickers, etiquetas, minúsculas, acentos, erratas, palabras a
medias, alias de voz, alias del merge y nombres legales, palabras de descripción) el resultado es IDÉNTICO — ids,
puntajes y métodos —, a 937 empresas y a 5k (grafo levantado de scripts/gen_synth_graph.py). Umbral de ESCRITURA 85 /
BÚSQUEDA 60 sin cambios. No requiere Postgres.
"""
import functools
import os
import random
import re
import statistics
import sys
import time
import types
import unicodedata

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


# ── referencia: el código de ANTES (lineal), copiado tal cual ────────────────────────────────────────────────────
_PUNCT = re.compile(r'[^\w\s]', re.UNICODE)
_WS = re.compile(r'\s+')
_SUFIJOS = ('corporation', 'corp', 'incorporated', 'inc', 'limited', 'ltd', 'llc', 'plc', 'sa', 'sas', 'ag', 'nv',
            'bv', 'co', 'company', 'holdings', 'holding', 'group', 'technologies', 'technology', 'systems')


def _norm_viejo(txt):
    if not txt:
        return ''
    s = unicodedata.normalize('NFD', str(txt))
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = _PUNCT.sub(' ', s.lower())
    return _WS.sub(' ', s).strip()


_norm_ref = functools.lru_cache(maxsize=None)(_norm_viejo)    # función pura: la caché no cambia el resultado


def _strip_suffix_ref(txt):
    palabras = _norm_ref(txt).split()
    while len(palabras) > 1 and palabras[-1] in _SUFIJOS:
        palabras.pop()
    return ' '.join(palabras)


def _resolve_lineal(idx, texto, umbral=60):
    if not texto or not str(texto).strip():
        return None
    crudo = str(texto).strip()
    n = _norm_ref(crudo)
    if not n:
        return None

    def hit(nid, score, method, matched):
        if score < umbral:
            return None
        nodo = idx['nodos'].get(nid) or {}
        return {'id': nid, 'label': nodo.get('label') or nid, 'score': score, 'method': method, 'matched': matched}

    if n in idx['por_id']:
        return hit(idx['por_id'][n], 100, 'id', crudo)
    up = crudo.upper().strip()
    if up in idx['por_ticker']:
        return hit(idx['por_ticker'][up], 98, 'ticker', up)
    if n in idx['por_label']:
        return hit(idx['por_label'][n], 95, 'label', crudo)
    if n in idx['por_alias']:
        return hit(idx['por_alias'][n], 92, 'alias', crudo)
    corto = _strip_suffix_ref(crudo)
    if corto and corto in idx['por_alias']:
        return hit(idx['por_alias'][corto], 90, 'alias_sufijo', corto)
    if corto and corto in idx['por_label_corto']:
        return hit(idx['por_label_corto'][corto], 88, 'label_sufijo', corto)
    if corto and corto in idx['por_label']:
        return hit(idx['por_label'][corto], 88, 'label_sufijo', corto)
    voz = idx.get('por_voz') or {}
    if voz:
        sin_stop = ' '.join(w for w in n.split() if w not in (idx.get('stopwords') or ())) or n
        for k in (n, sin_stop):
            if k in voz:
                return hit(voz[k], 80, 'voice_alias', k)
    if len(n) >= 4:
        claves = list(idx['por_label'].items()) + list(idx['por_label_corto'].items())
        pref = {nid for k, nid in claves if k.startswith(n)}
        if len(pref) == 1:
            return hit(pref.pop(), 70, 'prefijo', n)
        sub = {nid for k, nid in claves if n in k}
        if len(sub) == 1:
            return hit(sub.pop(), 60, 'subcadena', n)
        if voz and not pref and not sub:
            vp = {nid for k, nid in voz.items() if k.startswith(n)}
            if len(vp) == 1:
                return hit(vp.pop(), 70, 'voice_prefijo', n)
    return None


def _search_lineal(idx, nodes, query):
    """mcp_server/tools._search de antes (sin el armado de la ficha): {id: (puntaje, método)}."""
    q = str(query or '').strip()
    n = _norm_ref(q)
    if not n:
        return {}
    cands = {}

    def add(nid, score, method):
        if nid in nodes and score > cands.get(nid, (0, ''))[0]:
            cands[nid] = (score, method)
    top = _resolve_lineal(idx, str(q or '')[:120], umbral=60)
    if top:
        add(top['id'], top['score'], top['method'])
    up = q.upper()
    for alias, nid in idx['por_alias'].items():
        if alias == n:
            add(nid, 92, 'alias')
        elif len(n) >= 3 and alias.startswith(n):
            add(nid, 78, 'alias_prefix')
    for nid, node in nodes.items():
        lab = _norm_ref(node.get('label') or '')
        sym = (node.get('mkt') or '').upper()
        if sym and sym == up:
            add(nid, 98, 'ticker')
        elif lab == n:
            add(nid, 95, 'label')
        elif lab.startswith(n):
            add(nid, 75, 'prefix')
        elif _norm_ref(nid).startswith(n):
            add(nid, 72, 'id_prefix')
        elif len(n) >= 3 and re.search(r'(^|\s)' + re.escape(n), lab):
            add(nid, 66, 'word')
        elif len(n) >= 3 and n in lab:
            add(nid, 60, 'substring')
        elif len(n) >= 4:
            desc = _norm_ref(' '.join(str(node.get(k) or '') for k in ('role_en', 'supplies_en', 'role', 'supplies')))
            if n in desc:
                add(nid, 40, 'description')
    return cands


def _ranked(cands, deg, k):
    return [(nid, s) for nid, (s, _m) in sorted(cands.items(), key=lambda kv: (-kv[1][0], -deg.get(kv[0], 0),
                                                                               kv[0]))[:k]]


# ── las consultas ─────────────────────────────────────────────────────────────────────────────────────────────────
_ACENTOS = str.maketrans({'a': 'á', 'e': 'é', 'i': 'í', 'o': 'ó', 'u': 'ü', 'n': 'ñ'})


def _consultas(idx, seed=7):
    """≥ 200 consultas variadas y deterministas a partir del grafo vigente."""
    rng = random.Random(seed)
    nodos = list(idx['nodos'].values())
    muestra = rng.sample(nodos, 60)
    qs = []
    qs += [n['id'] for n in muestra[:25]]                                         # ids exactos
    con_mkt = [n for n in nodos if n.get('mkt')]
    tk = rng.sample(con_mkt, 20)
    qs += [n['mkt'] for n in tk[:12]] + [n['mkt'].lower() for n in tk[12:]]       # tickers (y en minúsculas)
    qs += [n.get('label') or n['id'] for n in muestra[25:50]]                     # etiquetas
    qs += [(n.get('label') or n['id']).lower() for n in muestra[50:60]]           # minúsculas
    qs += [(n.get('label') or n['id']).translate(_ACENTOS) for n in muestra[:15]]  # con acentos
    for n in muestra[15:35]:                                                      # erratas
        lab = n.get('label') or n['id']
        if len(lab) < 4:
            qs.append(lab + 'x')
            continue
        i = rng.randrange(1, len(lab) - 1)
        kind = rng.choice(('del', 'swap', 'sub'))
        if kind == 'del':
            qs.append(lab[:i] + lab[i + 1:])
        elif kind == 'swap':
            qs.append(lab[:i - 1] + lab[i] + lab[i - 1] + lab[i + 1:])
        else:
            qs.append(lab[:i] + 'z' + lab[i + 1:])
    for n in muestra[35:55]:                                                      # palabras a medias
        palabras = (n.get('label') or n['id']).split()
        w = rng.choice(palabras)
        qs.append(w[:rng.randint(2, max(2, min(6, len(w))))])
        lab = _norm_ref(n.get('label') or '')
        if len(lab) > 6:
            a = rng.randrange(0, len(lab) - 4)
            qs.append(lab[a:a + rng.randint(3, 5)])
    voz = sorted(idx.get('por_voz') or {})
    if voz:
        for k in rng.sample(voz, min(15, len(voz))):                             # alias de voz (+ sus prefijos)
            qs.append(k)
            qs.append(k[:max(4, len(k) - 3)])
    alias = sorted(idx['por_alias'])
    qs += rng.sample(alias, min(15, len(alias)))                                  # alias del merge / nombres legales
    qs += ['semiconductor', 'battery', 'lithium', 'hbm', 'cloud', 'power', 'memoria', 'foundry', 'fab', 'gpu',
           'data center', 'energía', 'cobre', 'logistics', 'litio']                # palabras de descripción
    qs += ['Nvidia', 'NVDA', 'NVIDIA Corporation', 'nvidia corp', 'AWS', 'Azure', 'Taiwan Semiconductor', 'taiwan semi',
           'en vidia', 'open ai', 'TSMC', 'tsm', 'Goldman Sachs', 'Nvidia, Inc.', 'nv', 'ab', 'x', '3750', '  ',
           'no-existe-esta-empresa-xyz-123', 'micro', 'quantum', 'samsung elec', 'asml holding', 'microsof', 'amazn',
           'semi', '!!', 'Ñandú', '宁德时代']                                       # casos conocidos y bordes
    return qs


def _comparar(idx, nodes, deg, qs):
    from core import entities
    malos = []
    for q in qs:
        ref = _search_lineal(idx, nodes, q)
        got = {nid: v for nid, v in entities.search_scores(q).items() if nid in nodes}
        if got != ref or _ranked(got, deg, 5) != _ranked(ref, deg, 5):
            malos.append(('search', q))
        for umbral in (entities.UMBRAL_BUSQUEDA, entities.UMBRAL_ESCRITURA):
            if entities.resolve(q, umbral=umbral) != _resolve_lineal(idx, q, umbral=umbral):
                malos.append(('resolve', umbral, q))
    return malos


def _p50_ms(fn, qs):
    ts = []
    for q in qs:
        t0 = time.perf_counter()
        fn(q)
        ts.append((time.perf_counter() - t0) * 1000)
    return statistics.median(ts)


# ── pruebas ───────────────────────────────────────────────────────────────────────────────────────────────────────
def test_norm_rapido_igual_al_de_antes():
    """El atajo ASCII y la limpieza de marcas solo en lo no ASCII dan EXACTAMENTE el norm() de antes."""
    from core import entities
    from core.hotviews import hot
    snap = hot.graph().snapshot
    textos = []
    for n in snap['nodes']:
        textos += [v for v in n.values() if isinstance(v, str)]
    textos += list(snap.get('legal_names') or {}) + list(snap.get('voice_aliases') or {})
    rng = random.Random(1)
    for _ in range(5000):
        textos.append(''.join(chr(rng.choice((rng.randint(0, 0x2ff), rng.randint(0x300, 0x36f),
                                              rng.randint(0x370, 0xffff), rng.randint(0x10000, 0x1ffff))))
                              for _ in range(rng.randint(0, 12))))
    textos += ['宁德时代', 'Ñandú', 'ﬁ', 'İstanbul', 'ǅ', 'e\u0301', '\u00a0x', 'Straße', 'ﾃｽﾄ', None, '', 0, 12.5]
    assert [t for t in textos if entities.norm(t) != _norm_viejo(t)] == []


def test_indice_igual_al_recorrido_lineal_937():
    from core import entities
    from mcp_server import tools as T
    entities.get_index(force=True)
    idx = entities.get_index()
    snap = T._snapshot()
    qs = _consultas(idx)
    assert len(qs) >= 200 and len(set(qs)) >= 180
    assert _comparar(idx, snap['nodes'], snap['deg'], qs) == []


def test_search_companies_usa_el_indice_y_ordena_igual():
    """La herramienta MCP devuelve el mismo top-5 (ids + puntajes) que el recorrido de antes."""
    from core import entities
    from mcp_server import tools as T
    idx = entities.get_index()
    snap = T._snapshot()
    for q in ('TSMC', 'NVDA', 'taiwan semi', 'semi', 'battery', 'micro', 'Goldman Sachs', 'litio'):
        ref = _ranked(_search_lineal(idx, snap['nodes'], q), snap['deg'], 5)
        got = [(r['id'], r['match']['score']) for r in T._search(q, 5)]
        assert got == ref, q
    assert '_ix_busqueda' in idx and '_ix_resolver' in idx      # el índice se armó (una vez por generación)
    ix = idx['_ix_busqueda']
    assert entities._indice_busqueda(idx) is ix                  # no se rearma en la misma generación


def test_umbrales_de_escritura_y_busqueda_sin_cambios():
    from core import entities
    assert (entities.UMBRAL_ESCRITURA, entities.UMBRAL_BUSQUEDA) == (85, 60)
    assert entities.resolve('NVDA', umbral=85)['method'] == 'ticker'
    assert entities.resolve('en vidia')['method'] == 'voice_alias'
    assert entities.resolve('en vidia', umbral=85) is None        # alias de voz (80) nunca alcanza la escritura
    r = entities.resolve('taiwan semi')
    assert r and r['id'] == 'TSMC'


def test_indice_nuevo_con_cada_generacion(monkeypatch):
    """Una empresa nueva en otra generación aparece en la búsqueda (el índice no queda viejo)."""
    from core import entities
    from core.hotviews import hot
    from core.hotviews.views import graph as graph_view
    from mcp_server import tools as T
    base = hot.graph()
    snap = dict(base.snapshot)
    snap['nodes'] = tuple(base.snapshot['nodes']) + ({'id': 'ZetaNueva', 'label': 'Zeta Nueva Robotics',
                                                       'mkt': 'ZNRB', 'role_en': 'humanoid actuators'},)
    data = types.SimpleNamespace(nodes=snap['nodes'], links=base.snapshot['links'],
                                 catalog={k: snap.get(k) for k in ('node_id_alias', 'legal_names', 'voice_aliases',
                                                                   'resolve_stopwords', 'sectors9')})
    gv = graph_view.build(data)
    gv.attach(types.SimpleNamespace(id='prueba-scale-search', graph_version=None, source='snapshot', lineage=None,
                                    built_at=None, views={}))
    monkeypatch.setattr(hot, 'graph', lambda wait=True, timeout=None: gv)
    assert entities.search_scores('zeta nueva')['ZetaNueva'] == (75, 'prefix')
    assert entities.resolve('zeta nueva')['method'] == 'prefijo'
    assert entities.search_scores('ZNRB')['ZetaNueva'][0] == 98
    assert 'ZetaNueva' in entities.search_scores('humanoid actuators')
    assert [r['id'] for r in T._search('Zeta Nueva Robotics', 1)] == ['ZetaNueva']


@pytest.fixture(scope='module')
def grafo_5k():
    """GraphView del grafo levantado a 5.000 empresas (scripts/gen_synth_graph.py); si el generador no está, copias
    del catálogo con sufijos deterministas."""
    from core.hotviews import hot
    from core.hotviews.views import graph as graph_view
    try:
        sys.path.insert(0, os.path.join(ROOT, 'scripts'))
        import gen_synth_graph as G
        data = G.synth_graphdata(5000)
    except ImportError:
        g = hot.graph().snapshot
        nodes = list(g['nodes'])
        extra = []
        k = 0
        while len(nodes) + len(extra) < 5000:
            n = dict(nodes[k % len(nodes)])
            n['id'] = f"S{k:05d}_{n['id'][:12]}"
            n['label'] = f"{n.get('label') or n['id']} Synth {k}"
            if n.get('mkt'):
                n['mkt'] = f'SY{k:04d}'
            extra.append(n)
            k += 1
        data = types.SimpleNamespace(nodes=tuple(nodes + extra), links=g['links'],
                                     catalog={k2: g.get(k2) for k2 in ('node_id_alias', 'legal_names',
                                                                        'voice_aliases', 'resolve_stopwords')})
    gv = graph_view.build(data)
    gv.attach(types.SimpleNamespace(id='synth-5k-scale-search', graph_version=None, source='snapshot', lineage=None,
                                    built_at=None, views={}))
    return gv


def test_indice_igual_al_recorrido_lineal_5k_y_p50(monkeypatch, grafo_5k):
    from core import entities
    from core.hotviews import hot
    from mcp_server import tools as T
    monkeypatch.setattr(hot, 'graph', lambda wait=True, timeout=None: grafo_5k)
    idx = entities.get_index()
    assert len(idx['nodos']) >= 5000
    snap = T._snapshot()
    qs = _consultas(idx, seed=11)
    assert len(qs) >= 200
    assert _comparar(idx, snap['nodes'], snap['deg'], qs) == []
    T._search(qs[0], 10)                                          # índice ya armado (una vez por generación)
    p50 = _p50_ms(lambda q: T._search(q, 10), qs)
    assert p50 <= 20, f'search_companies p50 {p50:.1f} ms a 5k (meta ≤ 20 ms)'
