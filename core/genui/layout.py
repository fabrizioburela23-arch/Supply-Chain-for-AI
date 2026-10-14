"""core/genui/layout.py — ORDEN AUTOMÁTICO (`layout: "auto"`, docs/CHAT_UI_GENERATIVA.md §5.4) y las piezas que pone
siempre el servidor: texto (con marcas deterministas), acciones y fuentes.

    intent_of(message)                       → 'impact' | 'compare' | 'price' | 'chain' | 'news' | 'committee' |
                                                'risk' | 'company' | None   (reglas fijas, ES/EN, sin IA)
    auto_layout(cands, answer, intent, …)    → (bloques en orden de pantalla, descartados)

Orden: 1) el primer párrafo como titular · 2) el bloque PRINCIPAL según la intención · 3) el resto del texto ·
4) hasta 2 secundarios (los de la empresa principal primero; en modo simple ninguno) · 5) aviso «información, no
consejo» si hubo comité/investigación · 6) acciones · 7) fuentes. Máximo 4 bloques visuales; en simple, 1 grande.
"""
import re

from core.genui.util import clip, entity, i18n, norm_dt

MAX_VISUAL = 4
MAX_SECONDARY = 2
TEXT_MAX = 4000
BIG = ('chart.line', 'chart.candles', 'impact.cascade', 'graph.mini', 'comparison', 'geo.mini')
NON_VISUAL = ('text', 'actions', 'sources')

_INTENTS = (
    ('impact', re.compile(r'qu[eé] pasa(r[ií]a)? si|what (would happen|happens) if|what if|\bsi (cae|cayera|falla|fallara|'
                          r'se cae|deja de)|\bif .{0,40}\b(fails?|falls?|collapses?|goes down|stops)|choque|shock|'
                          r'impacto|impact|bloque[oa]|blockade|cascad|contagi', re.I)),
    ('compare', re.compile(r'compar|\bvs\.?\b|versus|frente a|\bo\b .{0,30}\bcu[aá]l\b|which is better|mejor entre', re.I)),
    ('risk', re.compile(r'\bvar\b|volatil|riesgo de (mi|la) cartera|portfolio risk|drawdown|\bbeta\b', re.I)),
    ('news', re.compile(r'noticia|news|qu[eé] pas[oó]|happened|evento|event|mundo|world|geopol', re.I)),
    ('price', re.compile(r'precio|cotiza|c[oó]mo (le )?(va|fue|ha ido)|how (is|did|has) .{0,40}(doing|done|perform)|'
                         r'\bprice|gr[aá]fic|chart|rendimiento|performance|meses|months|\ba[nñ]o\b|year|semana|week|'
                         r'hist[oó]ri', re.I)),
    ('chain', re.compile(r'proveed|supplier|cadena|supply chain|chain|clientes|customers|depend|riesg|\brisk|'
                         r'qui[eé]n le (vende|compra)', re.I)),
    ('committee', re.compile(r'comit[eé]|committee|analistas|analysts|investigaci[oó]n|research|conclusi|tesis|thesis|'
                             r'pros? y contras?|pros and cons', re.I)),
)

# tipo de bloque principal por intención (en orden de preferencia)
_MAIN = {
    'impact': ('cascade',),
    'compare': ('comparison', 'line'),
    'price': ('line',),
    'chain': ('graph.mini',),
    'news': ('timeline',),
    'committee': ('pros_cons', 'chart.bar'),
    'risk': ('risk_tiles',),
    'company': ('company',),
}
# prioridad por defecto (sin intención clara)
_DEFAULT = ('cascade', 'line', 'graph.mini', 'risk_tiles', 'pros_cons', 'ranking', 'chart.bar', 'timeline', 'company')


def intent_of(message):
    m = str(message or '')
    for name, rx in _INTENTS:
        if rx.search(m):
            return name
    return None


def _key(blk):
    """Clave de selección: el `kind` del constructor o el tipo del bloque."""
    m = blk.get('_meta') or {}
    if m.get('group') == 'company':
        return 'company'
    return m.get('kind') or blk['type']


def _matches(blk, k):
    return _key(blk) == k or blk['type'] == k


def _pick(cands, keys, primary):
    for k in keys:
        hits = [b for b in cands if _matches(b, k)]
        if hits:
            hits.sort(key=lambda b: 0 if (b.get('_meta') or {}).get('entity') in (primary, None) else 1)
            return hits[0]
    return None


def select(cands, intent, primary, mode='simple'):
    """→ (principales, secundarios, descartados por presupuesto)."""
    cands = [b for b in cands if not (_key(b) == 'comparison' and intent != 'compare')]
    main = None
    if intent in _MAIN:
        main = _pick(cands, _MAIN[intent], primary)
    if main is None:
        main = _pick(cands, _DEFAULT, primary)
    if main is None:
        return [], [], []
    mains = [main]
    if _key(main) == 'company':                  # empresa → cifras + ficha (de la MISMA empresa)
        ent = (main.get('_meta') or {}).get('entity')
        mains = [b for b in cands if _key(b) == 'company' and (b.get('_meta') or {}).get('entity') == ent]
        mains.sort(key=lambda b: 0 if (b.get('_meta') or {}).get('kind') == 'tiles' else 1)
    used = {id(b) for b in mains}
    rest = [b for b in cands if id(b) not in used]
    # de secundario, una empresa va con su FICHA (las cifras ya están dentro): sin el bloque de cifras repetido
    rest = [b for b in rest if not ((b.get('_meta') or {}).get('kind') == 'tiles'
                                    and (b.get('_meta') or {}).get('group') == 'company')]
    order = {k: i for i, k in enumerate(_DEFAULT)}
    rest.sort(key=lambda b: (0 if (b.get('_meta') or {}).get('entity') in (primary, None) else 1,
                             1 if (b.get('_meta') or {}).get('role') == 'secondary' else 0,
                             order.get(_key(b), 50)))
    secs, dropped = [], []
    if mode != 'pro':
        return mains, [], []
    big = sum(1 for b in mains if b['type'] in BIG)
    for b in rest:
        if len(secs) >= MAX_SECONDARY or len(mains) + len(secs) >= MAX_VISUAL:
            dropped.append(b)
            continue
        if b['type'] in BIG and big >= 2:
            dropped.append(b)
            continue
        big += 1 if b['type'] in BIG else 0
        secs.append(b)
    return mains, secs, dropped


# ── texto ────────────────────────────────────────────────────────────────────────────────────────────────────────
_FACT_RX = re.compile(r'\[F\d{1,3}\]')
_UNVERIFIED_RX = re.compile(r'\(⚠ (cifra no verificada|unverified figure)\)')


def paragraphs(answer):
    parts = [p.strip() for p in re.split(r'\n\s*\n', str(answer or '').strip()) if p.strip()]
    return parts


def _chunks(text, n=TEXT_MAX):
    out, cur = [], ''
    for p in paragraphs(text):
        while len(p) > n:
            out.append(p[:n])
            p = p[n:]
        if cur and len(cur) + 2 + len(p) > n:
            out.append(cur)
            cur = p
        else:
            cur = (cur + '\n\n' + p) if cur else p
    if cur:
        out.append(cur)
    return out


def marks_of(md, entities):
    """Marcas DETERMINISTAS: nombre de empresa → chip al Dossier; [F#] → chip de fuente; tramo que el guardián
    marcó como no verificado. Sin solapes, ≤ 60."""
    marks, taken = [], []

    def free(s, e):
        return all(e <= a or s >= b for a, b in taken)
    for m in _UNVERIFIED_RX.finditer(md):
        marks.append({'s': m.start(), 'e': m.end(), 'kind': 'unverified'})
        taken.append((m.start(), m.end()))
    for m in _FACT_RX.finditer(md):
        if free(m.start(), m.end()):
            marks.append({'s': m.start(), 'e': m.end(), 'kind': 'fact', 'ref': m.group(0)[1:-1]})
            taken.append((m.start(), m.end()))
    for ent in sorted(entities or [], key=lambda e: -len(e.get('label') or '')):
        lab = ent.get('label') or ''
        if len(lab) < 2:
            continue
        for m in re.finditer(r'(?<![\w])' + re.escape(lab) + r'(?![\w])', md):
            if free(m.start(), m.end()):
                marks.append({'s': m.start(), 'e': m.end(), 'kind': 'entity', 'ref': str(ent['id'])[:64]})
                taken.append((m.start(), m.end()))
            if len(marks) >= 60:
                break
    marks.sort(key=lambda x: (x['s'], x['e']))
    marks = marks[:60]
    if any(ord(c) > 0xFFFF for c in md):
        # posiciones en unidades UTF-16 (las de String.prototype.slice en el navegador): un emoji fuera del plano
        # básico ocupa 2 y correría todas las marcas que vienen después
        def u16(i):
            return len(md[:i].encode('utf-16-le')) // 2
        for x in marks:
            x['s'], x['e'] = u16(x['s']), u16(x['e'])
    return marks


def text_blocks(answer, lang, entities, start=1):
    out = []
    for i, ch in enumerate(_chunks(answer)):
        d = {'md': ch, 'lang': lang}
        mk = marks_of(ch, entities)
        if mk:
            d['marks'] = mk
        out.append({'id': f't{start + i}', 'type': 'text', 'state': 'ready', 'data': d})
    return out


# ── acciones y fuentes ───────────────────────────────────────────────────────────────────────────────────────────
_ACTION_MAP = {
    'open_xray': ('open_xray', 'Radiografía', 'X-Ray'), 'dossier': ('open_dossier', 'Dossier', 'Dossier'),
    'open_research': ('open_research', 'Investigación', 'Research'),
    'open_committee': ('open_committee', 'Comité', 'Committee'),
    'navigate': ('open_map', 'Ver en el mapa', 'Show on the map'),
}
_WINDOW_LABEL = {'glance': ('En una mirada', 'At a glance'), 'supplychain': ('Cadena de suministro', 'Supply chain')}


def actions_block(chat_actions, primary_ent):
    """Fila final: las acciones de pantalla YA validadas por el chat (validate_actions), traducidas al contrato, y el
    Dossier de la empresa principal. Solo abrir o sugerir: nunca dinero (broker/simular quedan fuera)."""
    items = []

    def add(a):
        if len(items) < 4 and not any(x['kind'] == a['kind'] and x.get('entity') == a.get('entity')
                                      and x.get('window') == a.get('window') for x in items):
            items.append(a)
    for a in chat_actions or []:
        if not isinstance(a, dict):
            continue
        t, arg = a.get('type'), a.get('arg')
        if t in _ACTION_MAP and isinstance(arg, str):
            ent = entity(arg, a.get('label'))
            if ent:
                k, es, en = _ACTION_MAP[t]
                add({'kind': k, 'label': i18n(f'{es}: {ent["label"]}', f'{en}: {ent["label"]}'), 'entity': ent})
        elif t == 'open_window' and isinstance(arg, dict) and arg.get('kind') in _WINDOW_LABEL:
            ent = entity(arg.get('id'), a.get('label'))
            if ent:
                es, en = _WINDOW_LABEL[arg['kind']]
                add({'kind': 'open_window', 'window': arg['kind'], 'entity': ent,
                     'label': i18n(f'{es}: {ent["label"]}', f'{en}: {ent["label"]}')})
        elif t == 'open_world' and isinstance(arg, dict):
            la, lo = arg.get('lat'), arg.get('lon')
            if isinstance(la, (int, float)) and isinstance(lo, (int, float)) and not isinstance(la, bool) \
                    and -90 <= la <= 90 and -180 <= lo <= 180:
                add({'kind': 'open_world', 'lat': la, 'lon': lo,
                     'label': i18n('Abrir el World Monitor', 'Open the World Monitor')})
    if primary_ent:
        add({'kind': 'open_dossier', 'entity': primary_ent,
             'label': i18n(f'Dossier: {primary_ent["label"]}', f'Dossier: {primary_ent["label"]}')})
    if not items:
        return None
    return {'id': 'act', 'type': 'actions', 'state': 'ready', 'data': {'items': items}}


def sources_block(facts, sources):
    """[F#] con su fuente y hora (los hechos que la IA vio) + enlaces de noticias. Siempre al final."""
    items, seen = [], set()
    for f in facts or []:
        if not isinstance(f, dict) or str(f.get('kind') or '').endswith(':error'):
            continue
        when = norm_dt(f.get('as_of'))
        label = clip(f.get('source') or f.get('kind'), 120)
        fid = f.get('id') if isinstance(f.get('id'), str) and re.fullmatch(r'F\d{1,3}', f.get('id')) else None
        if not when or not label or fid in seen:
            continue
        seen.add(fid)
        it = {'label': label, 'as_of': when}
        if fid:
            it['id'] = fid
        if f.get('kind'):
            it['tool'] = str(f['kind'])[:40]
        items.append(it)
    for s in sources or []:
        if len(items) >= 12:
            break
        if not isinstance(s, dict) or not s.get('url'):
            continue
        url = s['url']
        when = norm_dt(s.get('as_of'))
        label = clip(s.get('label'), 120)
        if not (isinstance(url, str) and url.startswith(('http://', 'https://')) and len(url) <= 500) or not when \
                or not label:
            continue
        it = {'label': label, 'url': url, 'as_of': when}
        if s.get('tool'):
            it['tool'] = str(s['tool'])[:40]
        pub = norm_dt(s.get('published'))
        if pub:
            it['published'] = pub
        items.append(it)
    if not items:
        return None
    return {'id': 'src', 'type': 'sources', 'state': 'ready', 'data': {'items': items[:12]}}


def disclaimer_block():
    t = i18n('Información, no consejo de inversión. Las conclusiones de los analistas y del comité no son '
             'recomendaciones de compra o venta.',
             'Information, not investment advice. The analysts\' and committee\'s conclusions are not buy or sell '
             'recommendations.')
    return {'id': 'disc', 'type': 'callout', 'state': 'ready', 'alt': t,
            'data': {'variant': 'disclaimer', 'origin': 'system', 'text': t}}
