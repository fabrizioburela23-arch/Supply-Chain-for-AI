"""core/genui/builders.py — CONSTRUCTORES deterministas: resultado de herramienta → bloques kblocks/1 (§5.2).

    BUILDERS[nombre](res, b) → [bloque]      (b = contexto de la llamada: idioma, índice, [F#], metadatos)

Reglas (docs/CHAT_UI_GENERATIVA.md §2):
  · PUROS: sin E/S, sin IA, sin reloj (la hora viene en `b`). Mismo resultado → mismo bloque (replay).
  · Toda cifra sale del resultado CITADO (`prov.call`) y lleva `src`/`as_of`; sin dato → `v: null` con su motivo
    (nunca un 0 falso). core/genui/provenance.py lo comprueba después: lo que no cumpla se descarta.
  · El servidor manda el número CRUDO; el cliente decide el formato.
  · Cada bloque lleva una clave interna `_meta` (llamadas citadas, transformaciones declaradas, empresa, papel) que
    build_ui quita antes de enviar.
"""
from core.genui.util import clip, entity, i18n, lttb, norm_dt, num, src_id

FLOW_TYPES = ('supply', 'fab', 'cloud', 'license', 'ppa', 'owns', 'deploy')
REL_LABEL = {'supply': ('suministro', 'supply'), 'fab': ('fabrica', 'foundry'), 'cloud': ('nube', 'cloud'),
             'license': ('licencia', 'license'), 'ppa': ('energía (PPA)', 'power (PPA)'),
             'owns': ('propiedad', 'ownership'), 'deploy': ('despliegue', 'deployment')}
RANGE_MAP = {'1mo': '1M', '3mo': '3M', '6mo': '6M', '1y': '1Y', '2y': '2Y', '5y': '5Y'}
RANGES = ['1M', '3M', '6M', '1Y', '2Y', '5Y']
HORIZON_LABEL = {'SHORT_TERM': ('Corto plazo', 'Short term'), 'MEDIUM_TERM': ('Mediano plazo', 'Medium term'),
                 'LONG_TERM': ('Largo plazo', 'Long term')}
LINE_MAX_POINTS = 400
MENU_DATA = ['table', 'where_from', 'ask', 'csv']
MENU_BASIC = ['where_from', 'ask']


class Ctx:
    """Contexto de UNA llamada a herramienta para su constructor."""

    def __init__(self, lang='es', call=0, fact=None, args='', now=None, meta=None):
        self.lang = 'en' if lang == 'en' else 'es'
        self.call = int(call)
        self.fact = fact
        self.args = args or ''
        self.now = now
        self.meta = meta or {}

    def label_of(self, eid, default=None):
        return (self.meta.get('labels') or {}).get(eid) or default or eid


# ── piezas comunes ───────────────────────────────────────────────────────────────────────────────────────────────
def _missing(es, en):
    return i18n(es, en)


NO_LIVE = ('sin dato en vivo ahora', 'no live data right now')
NOT_REQUESTED = ('no se pidió el dato en vivo', 'live data was not requested')
NOT_LISTED = ('no cotiza en bolsa', 'not listed on an exchange')
NO_TIME = ('la fuente no dice la hora del dato', 'the source does not say when')


def figure(v, unit, src, as_of, b=None, currency=None, missing=NO_LIVE, **kw):
    """Figure del contrato. Un número sin hora de la fuente NO se muestra como cifra (vacío honesto)."""
    x = num(v)
    when = norm_dt(as_of)
    if unit == 'CCY' and not currency:
        unit = 'USD'
    f = {'v': None, 'unit': unit, 'src': src}
    if unit == 'CCY':
        f['currency'] = currency
    if x is not None and when:
        f['v'] = x
        f['as_of'] = when
        if b is not None and b.fact:
            f['fact'] = b.fact
        for k, val in kw.items():
            if val is not None:
                f[k] = val
        return f
    f['as_of'] = None
    f['missing_reason'] = _missing(*(missing if x is None else NO_TIME))
    if kw.get('explain'):
        f['explain'] = kw['explain']
    return f


def _prov(b, name, **extra):
    p = {'kind': 'tool', 'name': name, 'call': b.call}
    if b.fact:
        p['fact'] = b.fact
    if b.args:
        p['args'] = clip(b.args, 200)
    for k, v in extra.items():
        if v is not None:
            p[k] = v
    return p


def _block(btype, b, name, title, data, *, subtitle=None, entity_=None, actions=None, menu=None, pinnable=True,
           meta=None, prov_extra=None):
    blk = {'id': 'x', 'type': btype, 'state': 'ready', 'title': title, 'prov': _prov(b, name, **(prov_extra or {})),
           'data': data}
    if subtitle:
        blk['subtitle'] = subtitle
    if b.fact:
        blk['sources'] = [b.fact]
    if entity_:
        blk['entity'] = entity_
    if pinnable:
        blk['pinnable'] = True
    if menu:
        blk['menu'] = list(menu)
    if actions:
        blk['actions'] = actions[:2]
    m = {'calls': [b.call], 'transforms': (), 'role': None, 'entity': (entity_ or {}).get('id'), 'tool': name}
    m.update(meta or {})
    blk['_meta'] = m
    return blk


def _act(kind, es, en, **kw):
    a = {'kind': kind, 'label': i18n(es, en)}
    for k, v in kw.items():
        if v is not None:
            a[k] = v
    return a


def _chain_link(x):
    e = entity(x.get('id'), x.get('label'))
    if not e:
        return None
    out = {'entity': e}
    w = num(x.get('weight', x.get('w')))
    if w is not None and 0 <= w <= 10:
        out['weight'] = w
    rt = x.get('type') or x.get('relation_class')
    if rt in FLOW_TYPES:
        out['rel_type'] = rt
    if isinstance(x.get('verified'), bool):
        out['verified'] = x['verified']
    c = num(x.get('confidence', x.get('conf')))
    if c is not None and 0 <= c <= 1:
        out['conf'] = c
    return out


# ── get_company → metric.tiles + company.card ───────────────────────────────────────────────────────────────────
_CONC = {'baja': ('baja', 'low'), 'media': ('media', 'medium'), 'alta': ('alta', 'high'),
         'low': ('baja', 'low'), 'medium': ('media', 'medium'), 'high': ('alta', 'high')}


def company_figures(res, b):
    lm = res.get('live_market') if isinstance(res.get('live_market'), dict) else {}
    live = bool(lm.get('available')) and num(lm.get('price')) is not None
    listed = bool(res.get('listed'))
    reason = NOT_LISTED if not listed else (NOT_REQUESTED if 'not requested' in str(lm.get('reason') or '') else NO_LIVE)
    src = src_id(lm.get('source') or ('yahoo' if listed else 'khipus_graph'))
    when = (lm.get('market_time') if isinstance(lm.get('market_time'), str) else None) or lm.get('as_of')
    if isinstance(lm.get('market_time'), (int, float)) and not isinstance(lm.get('market_time'), bool):
        when = lm.get('market_time')
    cur = str(lm.get('currency') or 'USD').upper()
    unit = 'USD' if cur == 'USD' else 'CCY'
    out = {
        'price': figure(lm.get('price') if live else None, unit, src, when, b, currency=cur if unit == 'CCY' else None,
                        missing=reason, live=True if live else None),
        'change': figure(lm.get('change_pct') if live else None, 'pct', src, when, b, missing=reason,
                         live=True if live else None),
        'market_cap': figure(lm.get('market_cap_usd_b') if live else None, 'USD_B', src, when, b, missing=reason),
    }
    nrs = res.get('network_risk_score') if isinstance(res.get('network_risk_score'), dict) else {}
    out['nrs'] = figure(nrs.get('value'), 'nrs', 'khipus_nrs', res.get('as_of'), b,
                        missing=('sin NRS para esta empresa', 'no NRS for this company'), explain='nrs')
    pv = res.get('private_valuation') if isinstance(res.get('private_valuation'), dict) else None
    if pv and num(pv.get('valuation_usd_b')) is not None:
        out['private'] = figure(pv.get('valuation_usd_b'), 'USD_B', 'verified_round', pv.get('as_of'), b)
    out['_live'] = live
    out['_market_state'] = lm.get('market_state') if live else None
    return out


def b_get_company(res, b):
    cid = res.get('id')
    ent = entity(cid, res.get('label'), res.get('symbol'))
    if not ent:
        return []
    F = company_figures(res, b)
    name = ent['label']
    items = []
    if res.get('listed'):
        items.append({'label': i18n('Precio', 'Price'), 'value': F['price']})
        items.append({'label': i18n('Cambio', 'Change'), 'value': F['change']})
        items.append({'label': i18n('Capitalización', 'Market cap'), 'value': F['market_cap']})
    elif 'private' in F:
        items.append({'label': i18n('Última valuación (ronda cerrada)', 'Last valuation (closed round)'),
                      'value': F['private']})
    else:
        items.append({'label': i18n('Precio', 'Price'), 'value': F['price']})
    items.append({'label': i18n('Riesgo de red (NRS)', 'Network risk (NRS)'), 'value': F['nrs']})
    acts = [_act('open_dossier', 'Dossier', 'Dossier', entity=ent), _act('open_xray', 'Radiografía', 'X-Ray', entity=ent)]
    tiles = _block('metric.tiles', b, 'get_company', i18n(f'{name}: cifras clave', f'{name}: key figures'),
                   {'items': items}, entity_=ent, menu=MENU_BASIC, meta={'group': 'company', 'kind': 'tiles'})
    data = {'company': ent, 'listed': bool(res.get('listed'))}
    ms = F['_market_state']
    if isinstance(ms, str) and ms.strip():
        data['market_state'] = ms.strip()[:20]
    for k in ('price', 'change', 'market_cap', 'nrs'):
        if k == 'nrs' or res.get('listed'):
            data[k] = F[k]
    pv = res.get('private_valuation') if isinstance(res.get('private_valuation'), dict) else None
    if 'private' in F:
        p = {'value': F['private']}
        if pv.get('round'):
            p['round'] = clip(pv['round'], 60)
        if isinstance(pv.get('source_url'), str) and pv['source_url'].startswith('https://') \
                and len(pv['source_url']) <= 300:
            p['source_url'] = pv['source_url']
        data['private_valuation'] = p
    sup = [x for x in (_chain_link(x) for x in (res.get('top_suppliers') or [])[:5] if isinstance(x, dict)) if x]
    cus = [x for x in (_chain_link(x) for x in (res.get('top_customers') or [])[:5] if isinstance(x, dict)) if x]
    if sup:
        data['top_suppliers'] = sup
    if cus:
        data['top_customers'] = cus
    st = res.get('structure') if isinstance(res.get('structure'), dict) else None
    if st:
        conc = _CONC.get(str(st.get('supplier_concentration') or '').lower())
        ctry = (st.get('top_supplier_country') or {}).get('country') if isinstance(st.get('top_supplier_country'), dict) else None
        es, en = [], []
        if conc:
            es.append(f'concentración de proveedores {conc[0]}')
            en.append(f'supplier concentration {conc[1]}')
        if ctry:
            es.append(f'país principal de sus proveedores: {clip(ctry, 40)}')
            en.append(f'main supplier country: {clip(ctry, 40)}')
        if es:
            data['structure'] = i18n('Estructura: ' + '; '.join(es), 'Structure: ' + '; '.join(en))
    gao = norm_dt((res.get('catalog') or {}).get('as_of') if isinstance(res.get('catalog'), dict) else None)
    if gao:
        data['graph_as_of'] = gao
    card = _block('company.card', b, 'get_company', i18n(f'Ficha de {name}', f'{name} card'), data, entity_=ent,
                  actions=acts, menu=MENU_BASIC, meta={'group': 'company', 'kind': 'card'})
    return [tiles, card]


# ── get_supply_chain → graph.mini ────────────────────────────────────────────────────────────────────────────────
def b_get_supply_chain(res, b):
    root = res.get('root')
    labels = {n.get('id'): (n.get('label'), n.get('symbol')) for n in res.get('nodes') or [] if isinstance(n, dict)}
    center = entity(root, res.get('label') or (labels.get(root) or (None,))[0], (labels.get(root) or (None, None))[1])
    if not center:
        return []
    edges = [e for e in res.get('edges') or [] if isinstance(e, dict) and (e.get('type') or e.get('relation_class'))
             in FLOW_TYPES]
    sup = sorted((e for e in edges if e.get('target') == root and e.get('source') != root),
                 key=lambda e: (-(num(e.get('w')) or 0), str(e.get('source'))))
    cus = sorted((e for e in edges if e.get('source') == root and e.get('target') != root),
                 key=lambda e: (-(num(e.get('w')) or 0), str(e.get('target'))))
    nodes, seen, out_edges = [{'entity': center, 'role': 'center'}], {root}, []

    def add(e, other, role):
        if other in seen or len(nodes) >= 25:
            return
        lab, sym = labels.get(other, (None, None))
        ent = entity(other, lab or other, sym)
        if not ent:
            return
        rt = e.get('type') if e.get('type') in FLOW_TYPES else e.get('relation_class')
        node = {'entity': ent, 'role': role}
        if rt in REL_LABEL:
            node['sub'] = i18n(*REL_LABEL[rt])
        nodes.append(node)
        seen.add(other)
        ed = {'s': e['source'], 't': e['target'], 'rel_type': rt}
        w = num(e.get('w'))
        if w is not None and 0 <= w <= 10:
            ed['weight'] = w
        if isinstance(e.get('verified'), bool):
            ed['verified'] = e['verified']
        c = num(e.get('confidence'))
        if c is not None and 0 <= c <= 1:
            ed['conf'] = c
        if len(ed['s']) <= 64 and len(ed['t']) <= 64 and len(out_edges) < 40:
            out_edges.append(ed)
    for k in range(max(len(sup), len(cus))):          # intercalados: al recortar se ven los dos lados
        if k < len(sup) and sum(1 for n in nodes if n['role'] == 'supplier') < 12:
            add(sup[k], sup[k]['source'], 'supplier')
        if k < len(cus) and sum(1 for n in nodes if n['role'] == 'customer') < 12:
            add(cus[k], cus[k]['target'], 'customer')
    as_of = norm_dt(res.get('as_of'))
    if not as_of or len(nodes) < 2:
        return []
    data = {'center': center, 'src': 'khipus_graph', 'as_of': as_of, 'nodes': nodes, 'edges': out_edges}
    name = center['label']
    return [_block('graph.mini', b, 'get_supply_chain', i18n(f'Cadena de suministro de {name}', f'{name} supply chain'),
                   data, subtitle=i18n('solo flujo: proveedores → empresa → clientes',
                                       'flow only: suppliers → company → customers'),
                   entity_=center, menu=MENU_BASIC,
                   actions=[_act('open_window', 'Abrir la cadena', 'Open the chain', window='supplychain', entity=center)])]


# ── rank_companies → ranking ─────────────────────────────────────────────────────────────────────────────────────
def b_rank_companies(res, b):
    by_risk = res.get('by') == 'risk'
    as_of = norm_dt(res.get('as_of'))
    if not as_of:
        return []
    items = []
    for i, r in enumerate((res.get('items') or [])[:20]):
        if not isinstance(r, dict):
            continue
        ent = entity(r.get('id'), r.get('label'), r.get('symbol'))
        v = num(r.get('nrs') if by_risk else r.get('degree'))
        if not ent:
            continue
        items.append({'rank': i + 1, 'entity': ent, 'v': v})
    if not items:
        return []
    metric = ({'label': i18n('Riesgo de red (NRS)', 'Network risk (NRS)'), 'unit': 'nrs', 'src': 'khipus_nrs',
               'as_of': as_of, 'explain': 'nrs'} if by_risk else
              {'label': i18n('Vínculos de suministro', 'Supply links'), 'unit': 'count', 'src': 'khipus_graph',
               'as_of': as_of})
    if b.fact:
        metric['fact'] = b.fact
    title = (i18n('Mayor riesgo de red', 'Highest network risk') if by_risk else
             i18n('Empresas más conectadas', 'Most connected companies'))
    f = res.get('filters') or {}
    sub = ' · '.join(clip(x, 40) for x in (f.get('sector'), f.get('country')) if x)
    return [_block('ranking', b, 'rank_companies', title,
                   {'metric': metric, 'direction': 'lower_better' if by_risk else 'neutral', 'items': items},
                   subtitle=i18n(sub, sub) if sub else None, menu=MENU_DATA)]


# ── market_movers → chart.bar ────────────────────────────────────────────────────────────────────────────────────
def b_market_movers(res, b):
    as_of = norm_dt(res.get('as_of'))
    if not as_of:
        return []
    items = []
    for r in (res.get('items') or [])[:30]:
        if not isinstance(r, dict):
            continue
        v = num(r.get('change_pct'))
        name = clip(r.get('symbol') or r.get('label') or r.get('id'), 80)
        if not name:
            continue
        it = {'label': name, 'v': v}
        ent = entity(r.get('id'), r.get('label'), r.get('symbol'))
        if ent:
            it['entity'] = ent
        t = norm_dt(r.get('market_time'))
        if t:
            it['as_of'] = t
        items.append(it)
    if not items:
        return []
    down = res.get('direction') == 'down'
    vs = {'label': i18n('Cambio de hoy', 'Change today'), 'unit': 'pct', 'src': src_id(res.get('source'), 'yahoo'),
          'as_of': as_of}
    if b.fact:
        vs['fact'] = b.fact
    sec = res.get('sector_filter')
    return [_block('chart.bar', b, 'market_movers',
                   i18n('Las que más caen hoy', 'Biggest fallers today') if down else
                   i18n('Las que más suben hoy', 'Biggest gainers today'),
                   {'orientation': 'h', 'values': vs, 'diverging': True, 'sort': 'asc' if down else 'desc',
                    'items': items},
                   subtitle=i18n(clip(sec, 60), clip(sec, 60)) if sec else None, menu=MENU_DATA)]


# ── get_world_events → timeline (+ geo.mini) · get_news → timeline ─────────────────────────────────────────────
def _latlon(x):
    la, lo = num(x.get('lat')), num(x.get('lon'))
    if la is None or lo is None or not (-90 <= la <= 90 and -180 <= lo <= 180):
        return None
    return la, lo


def b_get_world_events(res, b):
    as_of = norm_dt(res.get('as_of'))
    if not as_of:
        return []
    items, pts = [], []
    for x in res.get('items') or []:
        if not isinstance(x, dict):
            continue
        title = clip(x.get('title') or x.get('place'), 80)
        if not title:
            continue
        ll = _latlon(x)
        if ll and len(pts) < 60:
            pts.append({'lat': ll[0], 'lon': ll[1], 'label': title, 'kind': 'event'})
        d = norm_dt(x.get('time'))
        if not d or len(items) >= 20:
            continue
        it = {'date': d, 'title': title, 'kind': 'event', 'src': src_id(x.get('source'), 'world_monitor')}
        url = x.get('url')
        if isinstance(url, str) and url.startswith(('http://', 'https://')) and len(url) <= 500:
            it['url'] = url
        if ll:
            it['lat'], it['lon'] = ll
        if b.fact:
            it['fact'] = b.fact
        items.append(it)
    out = []
    win = res.get('window')
    sub = i18n('últimas 24 horas' if win == '24h' else 'últimos 7 días',
               'last 24 hours' if win == '24h' else 'last 7 days') if win in ('24h', '7d') else None
    if items:
        out.append(_block('timeline', b, 'get_world_events', i18n('Eventos en el mundo', 'World events'),
                          {'as_of': as_of, 'items': items}, subtitle=sub, menu=MENU_BASIC,
                          meta={'kind': 'timeline'}))
    if len(pts) >= 3:
        acts = [_act('open_world', 'Abrir el World Monitor', 'Open the World Monitor', lat=pts[0]['lat'],
                     lon=pts[0]['lon'])]
        out.append(_block('geo.mini', b, 'get_world_events', i18n('Dónde pasa', 'Where it happens'),
                          {'region': 'world', 'src': 'world_monitor', 'as_of': as_of, 'points': pts},
                          subtitle=sub, actions=acts, menu=MENU_BASIC, meta={'kind': 'geo', 'role': 'secondary'}))
    return out


def b_get_news(res, b):
    as_of = norm_dt(res.get('as_of'))
    comp = res.get('company') if isinstance(res.get('company'), dict) else {}
    ent = entity(comp.get('id'), comp.get('label'), comp.get('symbol'))
    if not as_of:
        return []
    src = src_id(res.get('source'), 'news')
    items = []
    for x in (res.get('items') or [])[:20]:
        if not isinstance(x, dict):
            continue
        d = norm_dt(x.get('date'))
        title = clip(x.get('title'), 80)
        if not d or not title:
            continue
        it = {'date': d, 'title': title, 'kind': 'news', 'src': src}
        url = x.get('url')
        if isinstance(url, str) and url.startswith(('http://', 'https://')) and len(url) <= 500:
            it['url'] = url
        if ent:
            it['entity'] = ent
        if b.fact:
            it['fact'] = b.fact
        items.append(it)
    if not items:
        return []
    items.sort(key=lambda it: it['date'], reverse=True)
    name = (ent or {}).get('label') or ''
    return [_block('timeline', b, 'get_news', i18n(f'Noticias de {name}'.strip(), f'{name} news'.strip()),
                   {'as_of': as_of, 'items': items}, entity_=ent, menu=MENU_BASIC, meta={'kind': 'timeline'})]


# ── comité · pizarra · investigación → callout / chart.bar ──────────────────────────────────────────────────────
def _items(texts, lang, b, claim_ids=None):
    out = []
    for i, (es, en) in enumerate(texts[:5]):
        txt, tl = (en, 'en') if (lang == 'en' and en) else ((es, 'es') if es else (en, 'en'))
        txt = clip(txt, 300)
        if not txt:
            continue
        it = {'text': txt, 'lang': tl}
        if b.fact:
            it['facts'] = [b.fact]
        if claim_ids and i < len(claim_ids) and claim_ids[i]:
            it['claim_id'] = str(claim_ids[i])[:64]
        out.append(it)
    return out


def b_get_committee_memo(res, b):
    body = res.get('memo') if isinstance(res.get('memo'), dict) else {}
    ent = entity(res.get('entity_id'), res.get('label'))
    th = [x for x in body.get('thesis') or [] if isinstance(x, dict)]
    rk = [x for x in body.get('key_risks') or [] if isinstance(x, dict)]
    pros = _items([(x.get('thesis_es'), x.get('thesis_en')) for x in th], b.lang, b)
    cons = _items([(x.get('risk_es'), x.get('risk_en')) for x in rk], b.lang, b)
    les = body.get('decision_label_es') or res.get('decision') or ''
    len_ = body.get('decision_label_en') or res.get('decision') or ''
    name = (ent or {}).get('label') or ''
    out = []
    if pros or cons:
        out.append(_block('callout', b, 'get_committee_memo',
                          i18n(f'Comité sobre {name}: {les}'.strip(), f'Committee on {name}: {len_}'.strip()),
                          {'variant': 'pros_cons', 'origin': 'tool', 'pros': pros, 'cons': cons},
                          entity_=ent, pinnable=False,
                          actions=[_act('open_committee', 'Abrir el comité', 'Open the committee', entity=ent)] if ent else None,
                          menu=MENU_BASIC, meta={'disclaimer': True, 'kind': 'pros_cons'}))
    conv = res.get('conviction') if isinstance(res.get('conviction'), dict) else {}
    when = norm_dt(res.get('created_at')) or norm_dt(res.get('as_of'))
    items = []
    for h in ('SHORT_TERM', 'MEDIUM_TERM', 'LONG_TERM'):
        r = conv.get(h)
        if isinstance(r, dict) and num(r.get('score')) is not None:
            items.append({'label': i18n(*HORIZON_LABEL[h]), 'v': num(r.get('score'))})
    if items and when:
        vs = {'label': i18n('Convicción del comité', 'Committee conviction'), 'unit': 'score', 'src': 'committee',
              'as_of': when}
        if b.fact:
            vs['fact'] = b.fact
        out.append(_block('chart.bar', b, 'get_committee_memo',
                          i18n(f'Convicción por horizonte: {name}', f'Conviction by horizon: {name}'),
                          {'orientation': 'h', 'values': vs, 'diverging': True, 'sort': 'none', 'items': items},
                          entity_=ent, menu=MENU_DATA, meta={'disclaimer': True, 'role': 'secondary'}))
    return out


def b_get_conclusions_board(res, b):
    as_of = norm_dt(res.get('as_of'))
    if not as_of:
        return []
    items = []
    for x in (res.get('items') or [])[:20]:
        if not isinstance(x, dict):
            continue
        v = num(x.get('conviction'))
        name = clip(x.get('label') or x.get('entity_id'), 80)
        if not name:
            continue
        it = {'label': name, 'v': v}
        ent = entity(x.get('entity_id'), x.get('label'))
        if ent:
            it['entity'] = ent
        items.append(it)
    if not items:
        return []
    vs = {'label': i18n('Convicción de los analistas', "Analysts' conviction"), 'unit': 'score', 'src': 'research',
          'as_of': as_of}
    if b.fact:
        vs['fact'] = b.fact
    return [_block('chart.bar', b, 'get_conclusions_board', i18n('Pizarra de conclusiones', 'Conclusions board'),
                   {'orientation': 'h', 'values': vs, 'diverging': True, 'sort': 'desc', 'items': items},
                   subtitle=i18n('de más favorable a menos', 'from most to least favorable'), menu=MENU_DATA,
                   meta={'disclaimer': True})]


def b_get_research(res, b):
    claims = []
    for lst in (res.get('claims_by_agent') or {}).values():
        claims.extend(c for c in lst or [] if isinstance(c, dict))
    claims.sort(key=lambda c: (-(num(c.get('confidence')) or 0), str(c.get('claim_id'))))
    pos = [c for c in claims if c.get('stance') == 'positive'][:5]
    neg = [c for c in claims if c.get('stance') == 'negative'][:5]
    if not pos and not neg:
        return []

    def texts(cs):
        return [(c.get('statement_es') or c.get('statement'), c.get('statement') if c.get('statement') != c.get('statement_es')
                 else None) for c in cs]
    ent = entity(res.get('entity_id'), res.get('label'))
    name = (ent or {}).get('label') or ''
    pros = _items(texts(pos), b.lang, b, [c.get('claim_id') for c in pos])
    cons = _items(texts(neg), b.lang, b, [c.get('claim_id') for c in neg])
    return [_block('callout', b, 'get_research', i18n(f'Lo que concluyó la investigación: {name}',
                                                      f'What research concluded: {name}'),
                   {'variant': 'pros_cons', 'origin': 'tool', 'pros': pros, 'cons': cons}, entity_=ent,
                   pinnable=False,
                   actions=[_act('open_research', 'Ver la evidencia', 'See the evidence', entity=ent)] if ent else None,
                   menu=MENU_BASIC, meta={'disclaimer': True, 'kind': 'pros_cons'})]


# ── get_risk_report → metric.tiles + chart.bar ──────────────────────────────────────────────────────────────────
def b_get_risk_report(res, b):
    when = res.get('as_of')
    v95 = res.get('var95') if isinstance(res.get('var95'), dict) else {}
    spec = (
        (('Valor de la cartera', 'Portfolio value'), res.get('portfolio_value_usd'), 'USD', None),
        (('VaR 95 % (1 día)', 'VaR 95% (1 day)'), v95.get('hist_1d_pct'), 'pct', 'var'),
        (('CVaR 95 % (1 día)', 'CVaR 95% (1 day)'), v95.get('cvar_1d_pct'), 'pct', 'cvar'),
        (('Volatilidad anual', 'Annual volatility'), res.get('vol_ann_pct'), 'pct', 'vol_ann'),
        (('Caída máxima', 'Max drawdown'), res.get('max_drawdown_pct'), 'pct', 'drawdown'),
        (('Beta vs S&P 500', 'Beta vs S&P 500'), res.get('beta_spy'), 'ratio', 'beta'),
    )
    items = [{'label': i18n(*lab), 'value': figure(v, unit, 'khipus_risk', when, b,
                                                   missing=('sin dato suficiente', 'not enough data'), explain=ex)}
             for lab, v, unit, ex in spec]
    out = [_block('metric.tiles', b, 'get_risk_report', i18n('Riesgo de tu cartera', 'Your portfolio risk'),
                  {'items': items}, subtitle=i18n('estimación con precios reales del último año; no es un pronóstico',
                                                  "estimate from the last year's real prices; not a forecast"),
                  menu=MENU_BASIC, meta={'kind': 'risk_tiles'})]
    as_of = norm_dt(when)
    bars = []
    for p in (res.get('positions') or [])[:30]:
        if isinstance(p, dict) and p.get('symbol') and num(p.get('risk_contrib_pct')) is not None:
            bars.append({'label': clip(p['symbol'], 80), 'v': num(p['risk_contrib_pct'])})
    if bars and as_of:
        vs = {'label': i18n('Aporte al riesgo', 'Risk contribution'), 'unit': 'pct', 'src': 'khipus_risk',
              'as_of': as_of, 'explain': 'risk_contrib'}
        if b.fact:
            vs['fact'] = b.fact
        out.append(_block('chart.bar', b, 'get_risk_report', i18n('Quién aporta más riesgo', 'Who adds the most risk'),
                          {'orientation': 'h', 'values': vs, 'sort': 'desc', 'items': bars}, menu=MENU_DATA,
                          meta={'role': 'secondary'}))
    return out


# ── get_history → chart.line (una o varias series) ──────────────────────────────────────────────────────────────
def history_series(res, b, rebase=False):
    """(serie, base) de UN resultado de get_history, o (None, None)."""
    pts = [[norm_dt(p.get('date')), num(p.get('close'))] for p in res.get('points') or [] if isinstance(p, dict)]
    pts = [p for p in pts if p[0] and p[1] is not None]
    as_of = norm_dt(res.get('as_of'))
    if len(pts) < 2 or not as_of:
        return None, None
    pts = lttb(pts, LINE_MAX_POINTS)
    sym = str(res.get('symbol') or res.get('id') or '')[:20]
    cur = str(res.get('currency') or 'USD').upper()
    base = None
    if rebase:
        base = pts[0][1]
        if not base:
            return None, None
        pts = [[d, round(100.0 * v / base, 4)] for d, v in pts]
        values = {'label': i18n('Índice (base 100)', 'Index (base 100)'), 'unit': 'index',
                  'src': src_id(res.get('source'), 'yahoo'), 'as_of': as_of}
    else:
        values = {'unit': 'USD' if cur == 'USD' else 'CCY', 'src': src_id(res.get('source'), 'yahoo'), 'as_of': as_of}
        if cur != 'USD':
            values['currency'] = cur
    if b.fact:
        values['fact'] = b.fact
    name = clip(sym or b.label_of(res.get('id')) or '', 80)
    if not name:
        return None, None
    s = {'name': name, 'values': values, 'points': pts}
    ent = entity(res.get('id'), b.label_of(res.get('id'), sym), sym)
    if ent:
        s['entity'] = ent
    if isinstance(res.get('adjusted'), bool):
        s['adjusted'] = res['adjusted']
    return s, base


def b_get_history(res, b):
    s, _ = history_series(res, b)
    if not s:
        return []
    rng = RANGE_MAP.get(str(res.get('range') or '').lower())
    data = {'variant': 'full', 'series': [s], 'ranges': list(RANGES)}
    if rng:
        data['range'] = rng
    name = s['name'] if isinstance(s['name'], str) else ''
    ent = s.get('entity')
    return [_block('chart.line', b, 'get_history', i18n(f'Precio de {name}', f'{name} price'), data,
                   subtitle=i18n('cierres ajustados', 'adjusted closes') if s.get('adjusted') else None,
                   entity_=ent, menu=MENU_DATA, meta={'kind': 'line'})]


def history_compare(pairs, b0):
    """2–4 resultados de get_history → UNA línea con las series llevadas a índice 100 (comparar empresas)."""
    series, bases, calls, facts = [], {}, [], []
    for res, b in pairs[:4]:
        s, base = history_series(res, b, rebase=True)
        if not s:
            continue
        bases[len(series)] = base
        series.append(s)
        calls.append(b.call)
        if b.fact:
            facts.append(b.fact)
    if len(series) < 2:
        return []
    names = ' vs '.join(s['name'] for s in series if isinstance(s['name'], str))
    rng = RANGE_MAP.get(str(pairs[0][0].get('range') or '').lower())
    data = {'variant': 'full', 'series': series, 'rebased': True, 'ranges': list(RANGES)}
    if rng:
        data['range'] = rng
    blk = _block('chart.line', b0, 'get_history', i18n(f'Comparación: {names}', f'Comparison: {names}'), data,
                 subtitle=i18n('índice 100 al inicio del periodo', 'index 100 at the start of the period'),
                 menu=MENU_DATA, meta={'calls': calls, 'transforms': ('rebase',), 'bases': bases, 'kind': 'line'})
    if facts:
        blk['sources'] = facts[:8]
    return [blk]


# ── run_scenario → impact.cascade ────────────────────────────────────────────────────────────────────────────────
_PF_REASON = {
    'uncalibrated': ('todavía no hay calibración para convertir el golpe en dinero', 'there is no calibration yet to turn the hit into money'),
    'weak': ('la calibración es débil: no damos cifra', 'the calibration is weak: we give no figure'),
    'kernel_mismatch': ('la calibración es de otro motor: no damos cifra', 'the calibration is for another engine: we give no figure'),
}


def b_run_scenario(res, b):
    shocks = [s for s in res.get('shocks') or [] if isinstance(s, dict) and s.get('id')]
    if not shocks:
        return []
    origin = entity(shocks[0]['id'], shocks[0].get('label'))
    as_of = norm_dt(res.get('as_of'))
    gen = res.get('generation')
    if not origin or not as_of or gen is None:
        return []
    mags = [num(s.get('magnitude')) for s in shocks if num(s.get('magnitude')) is not None]
    victims = [v for v in res.get('victims') or [] if isinstance(v, dict) and v.get('id')]
    by_hop = res.get('by_hop') if isinstance(res.get('by_hop'), dict) else {}
    hops = []
    for hk in sorted(by_hop, key=lambda k: int(k) if str(k).isdigit() else 99):
        if not str(hk).isdigit() or not 1 <= int(hk) <= 6:
            continue
        h = int(hk)
        cnt = num(by_hop[hk])
        if cnt is None:
            continue
        vs = sorted((v for v in victims if v.get('hop') == h and num(v.get('impact_pct')) is not None),
                    key=lambda v: (-v['impact_pct'], str(v['id'])))
        ents = []
        for v in vs[:8]:
            e = entity(v['id'], v.get('label'))
            if e and 0 <= v['impact_pct'] <= 100:
                ents.append({'entity': e, 'impact_pct': v['impact_pct']})
        hop = {'hop': h, 'label': i18n(f'Salto {h}', f'Hop {h}'), 'count': int(cnt)}
        if ents:
            hop['max_pct'] = max(x['impact_pct'] for x in ents)
            hop['entities'] = ents
        hops.append(hop)
    data = {'origin': origin, 'severity': round(max(mags) * 100, 4) if mags else 100.0, 'direction': 'down',
            'src': 'hot_kernel', 'as_of': as_of, 'generation': gen, 'hops': hops[:6],
            'total': int(num(res.get('reach_1pct')) or 0)}
    transforms = ['scale100', 'scale100_round']     # severidad = magnitud × 100 redondeada a 4 decimales
    if isinstance(res.get('graph_version'), int) and not isinstance(res.get('graph_version'), bool):
        data['graph_version'] = res['graph_version']
    k = res.get('kernel') if isinstance(res.get('kernel'), dict) else {}
    if isinstance(k.get('semver'), str):
        data['kernel'] = k['semver']
    if num(k.get('threshold')) == 0.01:
        data['threshold_pct'] = 1
    # «ganadores» = rivales poco golpeados con su % de DAÑO: los calcula run_scenario sobre TODOS los impactos del
    # kernel (core/genui/rivals.py = porte exacto de KhipuHot.rivals); aquí solo se copian
    riv = []
    for r in res.get('least_hit_rivals') or []:
        if not isinstance(r, dict):
            continue
        e = entity(r.get('id'), r.get('label'))
        d = num(r.get('impact_pct'))
        if e and d is not None and 0 <= d <= 100:
            riv.append({'entity': e, 'damage_pct': d})
    if riv:
        data['least_hit_rivals'] = riv[:6]
    pf = res.get('portfolio') if isinstance(res.get('portfolio'), dict) else None
    if pf is None:
        # el servidor pone las posiciones (khipu_chat._server_args): sin cartera con valor en USD no hay golpe que
        # estimar, y se dice (§5.2: «sin usd, no_positions»)
        data['portfolio'] = {'state': 'no_positions'}
    else:
        cal = pf.get('calibrated') if isinstance(pf.get('calibrated'), dict) else {}
        st = cal.get('status')
        if st == 'ok' and num(cal.get('pnl_usd')) is not None and num(cal.get('band_usd')) is not None:
            data['portfolio'] = {'state': 'figure',
                                 'value': figure(cal.get('pnl_usd'), 'USD', 'kernel_calibration', res.get('as_of'), b),
                                 'band': figure(cal.get('band_usd'), 'USD', 'kernel_calibration', res.get('as_of'), b)}
        elif st == 'no_positions' or not pf.get('positions'):
            data['portfolio'] = {'state': 'no_positions'}
        else:
            data['portfolio'] = {'state': 'no_figure',
                                 'reason': i18n(*_PF_REASON.get(st, _PF_REASON['uncalibrated']))}
    name = origin['label']
    title = (i18n(f'Choque en {name}', f'Shock at {name}') if len(shocks) == 1 else
             i18n(f'Choque en {name} y otras', f'Shock at {name} and others'))
    return [_block('impact.cascade', b, 'run_scenario', title, data,
                   subtitle=i18n('motor único del servidor · no es un pronóstico de precios',
                                 'single server kernel · not a price forecast'),
                   entity_=origin, menu=MENU_BASIC,
                   actions=[_act('open_window', 'Simular', 'Simulate', window='sim', entity=origin)],
                   prov_extra={'graph_version': data.get('graph_version'), 'generation': gen},
                   meta={'transforms': tuple(transforms), 'kind': 'cascade'})]


# las cifras de una fila de la comparación comparten UNA hora (la más vieja); si se separan más de esto, la fila sale
ROW_ASOF_SPREAD_S = 6 * 3600


def _ts(v):
    """as_of → segundos UTC (fecha sola = medianoche UTC), o None."""
    from datetime import datetime, timezone
    n = norm_dt(v)
    if not n:
        return None
    try:
        d = datetime.fromisoformat(n.replace('Z', '+00:00')) if 'T' in n else datetime.fromisoformat(n[:10])
    except ValueError:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.timestamp()


# ── varias get_company → comparison ──────────────────────────────────────────────────────────────────────────────
def company_comparison(pairs, b0):
    """2–4 fichas de empresas distintas → comparison (métricas que comparten fuente)."""
    seen, rows = set(), []
    for res, b in pairs:
        cid = res.get('id')
        ent = entity(cid, res.get('label'), res.get('symbol'))
        if ent and cid not in seen:
            seen.add(cid)
            rows.append((ent, res, b, company_figures(res, b)))
    rows = rows[:4]
    if len(rows) < 2:
        return []
    metrics = []

    def add(key, label, unit, better, getter, explain=None):
        figs = [getter(r) for r in rows]
        vals = [f for f in figs if isinstance(f, dict) and f.get('v') is not None]
        if len(vals) < 2:
            return
        srcs = {f['src'] for f in vals}
        curs = {f.get('currency') for f in vals}
        if len(srcs) != 1 or len(curs) != 1:
            return                               # cifras de fuentes o monedas distintas no van en una misma fila
        # UNA hora por fila: la MÁS VIEJA (en UTC, nunca comparando textos). Si las cifras de la fila están a más de
        # ROW_ASOF_SPREAD_S entre sí, la fila no va: una cifra vieja no puede mostrarse con la hora de otra fresca
        ts = [_ts(f.get('as_of')) for f in vals]
        if any(t is None for t in ts) or max(ts) - min(ts) > ROW_ASOF_SPREAD_S:
            return
        old = vals[ts.index(min(ts))]
        vs = {'label': i18n(*label), 'unit': vals[0]['unit'], 'src': vals[0]['src'], 'as_of': old['as_of']}
        if vals[0].get('currency'):
            vs['currency'] = vals[0]['currency']
        if explain:
            vs['explain'] = explain
        metrics.append({'key': key, 'values': vs, 'better': better,
                        'cells': [f.get('v') if isinstance(f, dict) else None for f in figs]})
    add('price', ('Precio', 'Price'), 'USD', 'none', lambda r: r[3]['price'])
    add('change', ('Cambio', 'Change'), 'pct', 'none', lambda r: r[3]['change'])
    add('market_cap', ('Capitalización', 'Market cap'), 'USD_B', 'none', lambda r: r[3]['market_cap'])
    add('nrs', ('Riesgo de red (NRS)', 'Network risk (NRS)'), 'nrs', 'lower', lambda r: r[3]['nrs'], 'nrs')

    def cnt(key):
        def g(r):
            c = r[1].get('counts') if isinstance(r[1].get('counts'), dict) else {}
            return figure(c.get(key), 'count', 'khipus_graph', (r[1].get('catalog') or {}).get('as_of')
                          if isinstance(r[1].get('catalog'), dict) else r[1].get('as_of'), r[2])
        return g
    add('suppliers', ('Proveedores', 'Suppliers'), 'count', 'none', cnt('suppliers'))
    add('customers', ('Clientes', 'Customers'), 'count', 'none', cnt('customers'))
    if not metrics:
        return []
    ents = [r[0] for r in rows]
    names = ' vs '.join(e['label'] for e in ents)
    blk = _block('comparison', rows[0][2], 'get_company', i18n(f'Comparación: {names}', f'Comparison: {names}'),
                 {'entities': ents, 'views': ['table', 'bars'], 'default_view': 'table', 'metrics': metrics},
                 menu=MENU_DATA,
                 meta={'calls': [r[2].call for r in rows], 'kind': 'comparison', 'group': 'compare'})
    facts = [r[2].fact for r in rows if r[2].fact]
    if facts:
        blk['sources'] = facts[:8]
    return [blk]


# ── get_fundamentals → chart.bar (ingresos por período) + metric.tiles (márgenes) [+ chart.bar utilidad] ─────────
FUND_MAX_BARS = 8


def _period_label(r):
    """Rótulo corto del período: 'FY2025' tal cual; trimestre 'Q 2025-07-31' → '2025-07'."""
    p = str(r.get('period') or '')
    if p.startswith('Q ') and len(p) >= 9:
        return p[2:9]
    return clip(p, 12) or clip(r.get('period_end'), 12)


def _fund_bar(res, b, key, title_es, title_en, kind, role=None):
    items = []
    for r in (res.get('periods') or [])[-FUND_MAX_BARS:]:
        if not isinstance(r, dict):
            continue
        lab = _period_label(r)
        if not lab:
            continue
        items.append({'label': lab, 'v': num(r.get(key))})
    if not items or all(it['v'] is None for it in items):
        return None
    as_of = norm_dt(res.get('as_of'))
    if not as_of:
        return None
    src = src_id(res.get('source'), 'yahoo')
    vs = {'label': i18n(title_es, title_en), 'unit': 'USD', 'src': src, 'as_of': as_of, 'explain': 'genui_' + key}
    if b.fact:
        vs['fact'] = b.fact
    ent = entity(res.get('id'), res.get('label'), res.get('symbol'))
    name = (ent or {}).get('label') or clip(res.get('symbol'), 20) or ''
    q = res.get('period') == 'quarterly'
    sub = i18n('por trimestre, en USD como lo reporta la fuente' if q else 'por año fiscal, en USD como lo reporta la fuente',
               'by quarter, in USD as reported' if q else 'by fiscal year, in USD as reported')
    meta = {'group': 'fundamentals', 'kind': kind}
    if role:
        meta['role'] = role
    return _block('chart.bar', b, 'get_fundamentals', i18n(f'{title_es} de {name}', f'{name} {title_en.lower()}'),
                  {'orientation': 'v', 'values': vs, 'diverging': key != 'revenue', 'sort': 'none', 'items': items},
                  subtitle=sub, entity_=ent, menu=MENU_DATA, meta=meta)


def b_get_fundamentals(res, b):
    out = []
    bar = _fund_bar(res, b, 'revenue', 'Ingresos', 'Revenue', 'fund_bar')
    if bar is None:
        return []
    out.append(bar)
    last = res.get('latest') if isinstance(res.get('latest'), dict) else None
    ent = entity(res.get('id'), res.get('label'), res.get('symbol'))
    name = (ent or {}).get('label') or clip(res.get('symbol'), 20) or ''
    when = res.get('as_of')
    src = src_id(res.get('source'), 'yahoo')
    if last:
        miss = ('la fuente no reporta este dato', 'the source does not report this figure')
        spec = ((('Ingresos', 'Revenue'), last.get('revenue'), 'USD', 'genui_revenue'),
                (('Utilidad neta', 'Net income'), last.get('net_income'), 'USD', 'genui_net_income'),
                (('Margen bruto', 'Gross margin'), last.get('gross_margin_pct'), 'pct', 'genui_margin'),
                (('Margen operativo', 'Operating margin'), last.get('operating_margin_pct'), 'pct', 'genui_margin'),
                (('Margen neto', 'Net margin'), last.get('net_margin_pct'), 'pct', 'genui_margin'),
                (('Crecimiento de ingresos', 'Revenue growth'), last.get('revenue_growth_pct'), 'pct', 'genui_growth'))
        items = [{'label': i18n(*lab), 'value': figure(v, unit, src, when, b, missing=miss, explain=ex)}
                 for lab, v, unit, ex in spec]
        per = _period_label(last)
        out.append(_block('metric.tiles', b, 'get_fundamentals', i18n(f'{name}: último período ({per})',
                                                                      f'{name}: latest period ({per})'),
                          {'items': items}, entity_=ent, menu=MENU_BASIC,
                          meta={'group': 'fundamentals', 'kind': 'fund_tiles'}))
    bar2 = _fund_bar(res, b, 'net_income', 'Utilidad neta', 'Net income', 'fund_bar2', role='secondary')
    if bar2 is not None:
        out.append(bar2)
    return out


# ── rank_by_market → ranking (posición de mercado investigada, E2.9) ─────────────────────────────────────────────
def b_rank_by_market(res, b):
    as_of = norm_dt(res.get('as_of'))
    if not as_of:
        return []
    by = 'rank' if res.get('sorted_by') == 'rank' else 'share_pct'
    items = []
    for r in (res.get('items') or [])[:20]:
        if not isinstance(r, dict):
            continue
        ent = entity(r.get('id'), r.get('label'), r.get('symbol'))
        if not ent:
            continue
        v = num(r.get(by))
        it = {'rank': len(items) + 1, 'entity': ent, 'v': v}
        when = norm_dt(r.get('as_of'))
        if when:
            it['as_of'] = when
        bits = [clip(r.get(k), 40) for k in ('market', 'period', 'measured_by') if r.get(k)]
        if bits:
            it['note'] = i18n(' · '.join(bits), ' · '.join(bits))
        items.append(it)
    if not items:
        return []
    metric = ({'label': i18n('Cuota de mercado', 'Market share'), 'unit': 'pct', 'src': 'khipus_graph', 'as_of': as_of,
               'explain': 'genui_market_share'} if by == 'share_pct' else
              {'label': i18n('Puesto en el mercado', 'Market rank'), 'unit': 'none', 'src': 'khipus_graph',
               'as_of': as_of, 'explain': 'genui_market_rank'})
    if b.fact:
        metric['fact'] = b.fact
    mkt = clip(res.get('market'), 50)
    reg = str(res.get('region') or 'GLOBAL')
    sub = i18n('posición investigada por empresa, con su fuente · ' + ('mundial' if reg == 'GLOBAL' else reg),
               'researched position per company, with its source · ' + ('global' if reg == 'GLOBAL' else reg))
    return [_block('ranking', b, 'rank_by_market', i18n(f'Las más grandes en {mkt}', f'Largest in {mkt}'),
                   {'metric': metric, 'direction': 'higher_better' if by == 'share_pct' else 'lower_better',
                    'items': items}, subtitle=sub, menu=MENU_DATA, meta={'kind': 'market_rank'})]


BUILDERS = {
    'get_company': b_get_company,
    'get_supply_chain': b_get_supply_chain,
    'rank_companies': b_rank_companies,
    'market_movers': b_market_movers,
    'get_world_events': b_get_world_events,
    'get_news': b_get_news,
    'get_committee_memo': b_get_committee_memo,
    'get_conclusions_board': b_get_conclusions_board,
    'get_research': b_get_research,
    'get_risk_report': b_get_risk_report,
    'get_history': b_get_history,
    'run_scenario': b_run_scenario,
    'get_fundamentals': b_get_fundamentals,
    'rank_by_market': b_rank_by_market,
}
