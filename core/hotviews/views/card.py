"""V3 Card + NRS (INFRA_OPERATIVA §4.2; paso 14) y V2b DownCap: la ficha COMPACTA de cada empresa, derivada de UNA
generación (GraphView `graph` + GraphCore + Impact) — nunca mezcla versiones.

Por empresa: id, etiqueta, instrumento(s) (el ticker del catálogo es el principal), estado en bolsa, sector, país,
rol/foso/qué provee ES/EN; conteos de FLUJO en PARES DISTINTOS (proveedores, clientes; socios/inversores aparte
como "relacionadas"); top-5 proveedores y clientes {id, w, tipo, clase, conf, verificado}; impacto del colapso
desde V2 (alcance ≥1 % y ≥10 %, Σ impacto, rango sistémico por Σ — PROP-06); valuación privada verificada.

A pedido (y precalentado en segundo plano tras publicar, core/hotviews/derived.prewarm):
  · NRS = LA fórmula (core.world.nrs_terms → client_nrs) con sus 5 términos, para TODAS las empresas a la vez
    (~10 ms; antes 870 ms con una consulta por empresa). Se recalcula solo si cambian los fundamentales en vivo
    (core.live_fundamentals.version(): el margen real entra en la fórmula; el precio NO). Si el vector todavía no
    está, la ficha calcula SOLO el NRS de su empresa (misma función, mismo número: E1.2, la primera ficha tras una
    generación nueva no espera a las 5.000);
  · estructura (concentración HHI, países de proveedores, capitalización aguas abajo en riesgo Ψᵀc = DownCap,
    fuentes de riesgo, comparables) = matrix.tensor.structure sobre el modelo DISPERSO de ESTA generación y las
    caps vigentes (clave caps_as_of).
"""
import hashlib
import json
import threading
import time

RELATED_TYPES = ('partner', 'invest')
TOP = 5


def _trust(l):
    from mcp_server.tools import _link_trust
    return _link_trust(l.get('rel'), l)


def _rclass(t):
    from mcp_server.tools import relation_class
    return relation_class(t)


def _listed(n):
    st = (n.get('listing') or {}).get('status')
    return bool(n.get('mkt')) and st not in ('acquired', 'merged', 'subsidiary', 'private', 'bankrupt', 'delisted')


def _pv():
    try:
        from mcp_server.tools import _private_valuations
        return _private_valuations() or {}
    except Exception:  # noqa: BLE001
        return {}


class CardView:
    __slots__ = ('generation', 'graph_version', 'source', 'g', 'cards', 'n', 'build_ms', '_sha', '_nrs',
                 '_struct', '_lock', 'by_sum_rank')

    @property
    def content_sha(self):
        """Huella del contenido de las tarjetas: se calcula la PRIMERA vez que alguien la pide (el 🩺 / status), no al
        construir (E1.2: ~100 ms a 5.000 empresas fuera del camino de la primera tarjeta). Mismo valor que antes."""
        if self._sha is None:               # sin candado: dos hilos a la vez calculan el MISMO valor (no frena fichas)
            self._sha = hashlib.sha256(json.dumps(self.cards, sort_keys=True, default=str).encode()).hexdigest()
        return self._sha

    # ── NRS (vector completo, una vez por versión de los fundamentales en vivo) ──
    def nrs_all(self):
        from core import live_fundamentals as lf
        from core import world
        fv = lf.version()
        cur = self._nrs
        if cur is not None and cur[0] == fv:
            return cur[1]
        with self._lock:
            cur = self._nrs
            if cur is not None and cur[0] == fv:
                return cur[1]
            gv = self.g.views['graph']
            deg = gv.flow_degree
            out = {}
            for n in gv.nodes:
                try:
                    out[n['id']] = world.nrs_terms(n, deg.get(n['id'], 0))
                except Exception:  # noqa: BLE001
                    continue
            self._nrs = (fv, out)
            return out

    def nrs(self, oid):
        t = self.nrs_all().get(oid)
        return None if t is None else t['total']

    def _nrs_terms_one(self, oid):
        """(términos del NRS de `oid`, versión de fundamentales): del vector si ya está al día; si no, SOLO esta empresa
        con la misma función (la primera tarjeta tras una generación no espera las 5.000; el vector lo arma el
        prewarm). Mismo número: nrs_terms de una empresa no depende de las demás."""
        from core import live_fundamentals as lf
        fv = lf.version()
        cur = self._nrs
        if cur is not None and cur[0] == fv:
            return cur[1].get(oid), fv
        gv = self.g.views['graph']
        n = gv.by_id.get(oid)
        if n is None:
            return None, fv
        from core import world
        try:
            return world.nrs_terms(n, gv.flow_degree.get(oid, 0)), fv
        except Exception:  # noqa: BLE001
            return None, fv

    def nrs_version(self):
        cur = self._nrs
        return cur[0] if cur is not None else None

    # ── estructura (tensor de flujo + DownCap) ──
    def structure_model(self):
        """El modelo del tensor de ESTA generación (y las caps vigentes) — nunca el de otra."""
        from matrix import tensor
        return tensor.model(view=self.g.views['graph'])

    def structure(self, oid):
        from matrix import tensor
        m = self.structure_model()
        key = (getattr(m, 'generation', None), getattr(m, 'caps_as_of', None), id(m))
        cur = self._struct
        if cur is None or cur[0] != key:
            with self._lock:
                if self._struct is None or self._struct[0] != key:
                    self._struct = (key, {})
            cur = self._struct
        memo = cur[1]
        if oid not in memo:
            memo[oid] = tensor.structure(oid, m=m, top=TOP)
        return memo[oid]

    def resolve(self, q):
        if not q:
            return None
        q = str(q).strip()
        if q in self.cards:
            return q
        gv = self.g.views['graph']
        c = gv.canonical(q)
        if c in self.cards:
            return c
        core = self.g.views.get('graph_core')
        r = core.resolve(q) if core is not None else None
        if r in self.cards:
            return r
        try:
            from core.entities import resolve as _er
            hit = _er(q[:120], umbral=85)
            if hit and hit.get('id') in self.cards:
                return hit['id']
        except Exception:  # noqa: BLE001
            pass
        return None

    def card(self, oid, lang='es', structure=True, nrs=True):
        """La tarjeta lista para servir (copia). None si `oid` no es una empresa de esta generación."""
        base = self.cards.get(oid)
        if base is None:
            return None
        en = lang == 'en'
        out = {k: v for k, v in base.items() if k not in ('text',)}
        tx = base['text']
        out.update({'role': (tx['role_en'] if en else tx['role_es']) or tx['role_es'] or tx['role_en'],
                    'moat': (tx['moat_en'] if en else tx['moat_es']) or tx['moat_es'] or tx['moat_en'],
                    'supplies': (tx['supplies_en'] if en else tx['supplies_es']) or tx['supplies_es'] or tx['supplies_en'],
                    'lang': 'en' if en else 'es'})
        if nrs:
            t, fv = self._nrs_terms_one(oid)
            out['nrs'] = None if t is None else {'value': t['total'], 'terms': {k: t[k] for k in (
                'geo', 'chain', 'market', 'fundamental', 'concentration')}, 'degree': t['degree'],
                'fund_version': fv}
        if structure:
            try:
                out['structure'] = self.structure(oid)
            except Exception as e:  # noqa: BLE001
                out['structure'] = None
                out['structure_error'] = type(e).__name__
        return out


def build(g):
    """Generation → CardView (sin red, sin base: todo sale de la foto de la generación)."""
    from ontology import vocabulary as vocab
    t0 = time.perf_counter()
    gv = g.views['graph']
    imp = g.views.get('impact')
    by_id = gv.by_id
    flow = set(vocab.flow_relation_types())
    rel_t = set(RELATED_TYPES)
    sup, cus, rel = {}, {}, {}
    rclass = {}                                    # tipo → clase (9 tipos; antes una llamada por vínculo)

    def put(d, a, b, e):
        cur = d.setdefault(a, {}).get(b)
        if cur is None or (e['w'] or 0) > (cur['w'] or 0):
            d[a][b] = e

    for l in gv.links:
        s, t = l.get('source'), l.get('target')
        if not s or not t or s == t or s not in by_id or t not in by_id:
            continue
        typ = l.get('type') or 'supply'
        if typ not in flow and typ not in rel_t:
            continue
        verified, conf = _trust(l)
        w = l.get('w')
        try:
            w = float(w) if w is not None else None
        except (TypeError, ValueError):
            w = None
        cls = rclass.get(typ)
        if cls is None:
            cls = rclass[typ] = _rclass(typ)
        mk = (lambda other: {'id': other, 'label': (by_id.get(other) or {}).get('label') or other, 'w': w,
                             'type': typ, 'class': cls, 'conf': conf, 'verified': bool(verified)})
        if typ in flow:
            put(sup, t, s, mk(s))
            put(cus, s, t, mk(t))
        else:
            put(rel, s, t, mk(t))
            put(rel, t, s, mk(s))

    def top(d, oid):
        lst = sorted((d.get(oid) or {}).values(), key=lambda e: (-(e['w'] or 0), e['id']))
        return lst[:TOP]

    rank_sum = {}
    if imp is not None:
        for i, k in enumerate(imp.by_sum, 1):
            rank_sum[k] = i
    pv = (_pv().get('entries') or {})
    sectors = gv.catalog.get('sectors9') or {}
    cards = {}
    for n in gv.nodes:
        oid = n['id']
        sec = sectors.get(n.get('sector')) or {}
        st = imp.stats.get(oid) if imp is not None else None
        e = pv.get(oid)
        sym = n.get('mkt') or None
        cards[oid] = {
            'id': oid, 'label': n.get('label') or oid,
            'ticker': sym, 'instruments': ([{'ticker': sym, 'primary': True, 'source': 'catalog'}] if sym else []),
            'listed': _listed(n), 'listing': dict(n['listing']) if n.get('listing') else None,
            'preipo': bool(n.get('preipo')), 'sector': n.get('sector'),
            'sector_label': {'es': sec.get('label'), 'en': sec.get('en')}, 'category': n.get('cat'),
            'country': n.get('country'),
            'text': {'role_es': n.get('role'), 'role_en': n.get('role_en'), 'moat_es': n.get('moat'),
                     'moat_en': n.get('moat_en'), 'supplies_es': n.get('supplies'), 'supplies_en': n.get('supplies_en')},
            'counts': {'suppliers': len(sup.get(oid) or {}), 'customers': len(cus.get(oid) or {}),
                       'related': len(rel.get(oid) or {}), 'flow_degree': gv.flow_degree.get(oid, 0)},
            'top_suppliers': top(sup, oid), 'top_customers': top(cus, oid), 'related': top(rel, oid),
            'impact': None if st is None else {'reach_1': st['reach_1'], 'reach_10': st['reach_10'],
                                               'affected': st['affected'], 'sum_impact': st['sum_impact'],
                                               'rank_by_sum': rank_sum.get(oid), 'of': len(rank_sum)},
            'private_valuation': None if not e else {
                'value_usd_b': e.get('valuation_usd_b'), 'as_of': e.get('as_of'), 'url': e.get('source_url'),
                'round': e.get('round'), 'kind': 'last closed round (verified), not a live price'},
        }
    v = CardView()
    v.g = g
    v.generation, v.graph_version, v.source = g.id, g.graph_version, g.source
    v.cards = cards
    v.n = len(cards)
    v._nrs = None
    v._struct = None
    v._lock = threading.Lock()
    v.by_sum_rank = rank_sum
    v._sha = None                                  # content_sha: a pedido (propiedad)
    v.build_ms = round((time.perf_counter() - t0) * 1000, 1)
    return v


def view(g):
    """La CardView de la generación `g` (una vez por generación; core/hotviews/derived)."""
    from core.hotviews import derived
    return derived.get(g, 'card', build)


def reader_view():
    """La CardView del grafo de los LECTORES (core/hotviews/hot.graph(): la generación publicada o, si todavía no
    sirve, la privada del snapshot). None si no hay grafo."""
    from core.hotviews import hot
    gv = hot.graph()
    if gv is None or gv.generation_obj is None:
        return None
    return view(gv.generation_obj)


def db_view():
    """La CardView solo si viene de POSTGRES (para quien lee objetos de la ontología: Centinela, alertas): con la
    base configurada pero leyendo el snapshot (calentando, o una base sin el catálogo) las propiedades no serían
    las del objeto → None y quien llama usa el cálculo directo."""
    v = reader_view()
    return v if v is not None and v.source == 'pg' else None


def nrs_map(ids=None, db_only=False):
    """{id: NRS} de la generación vigente (todas o `ids`). {} si no hay vista (quien llama decide el respaldo)."""
    v = db_view() if db_only else reader_view()
    if v is None:
        return {}
    allv = v.nrs_all()
    if ids is None:
        return {k: t['total'] for k, t in allv.items()}
    return {k: allv[k]['total'] for k in ids if k in allv}


def status(v):
    if v is None:
        return None
    return {'cards': v.n, 'build_ms': v.build_ms, 'content_sha': v.content_sha, 'nrs_fund_version': v.nrs_version(),
            'structure_cached': len(v._struct[1]) if v._struct else 0}
