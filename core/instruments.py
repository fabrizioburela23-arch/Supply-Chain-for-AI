"""core/instruments.py — EMPRESA ≠ INSTRUMENTO (docs/BRECHAS_V2.md L3-13; ARQUITECTURA_V2 §3.2, §17.3, §20.1 #3).

Hasta hoy cada empresa tenía UN campo `mkt` y Khipus trataba a la empresa y a su acción como la misma cosa: sin bolsa,
sin moneda, sin saber que Samsung se mide con un certificado OTC poco negociado (SSNLF) o que Baidu cotiza en Nasdaq y
en Hong Kong. Este módulo:

  · `from_catalog(nodes)` deriva un instrumento por empresa cotizada: el `mkt` de HOY es el PRIMARIO (BRECHAS #9 sin
    responder: nada se cambia solo), con bolsa, moneda y tipo (equity/adr/otc) deducidos del símbolo;
  · marca para REVISIÓN los 16 casos con varios listados declarados (texto 'ticker' con « / ») y los 28 que usan un
    certificado OTC/ADR (símbolo de 5 letras terminado en F/Y, o 'OTC' en el texto) → `review_list()` alimenta
    docs/REVISION_INSTRUMENTOS.md (scripts/build_instrument_review.py) para que Fabrizio elija;
  · `seed(session)` los inserta en la tabla `instruments` (ON CONFLICT DO NOTHING: nunca pisa nada) junto con los
    de referencia (SPY, ^IRX) y los pares de FX ({CUR}USD=X) que necesita la historia en dólares;
  · `nonsync(symbol)` dice si la bolsa cierra en otro horario que Nueva York (Asia/Europa/Oceanía): el riesgo usa beta
    de Dimson para ellas (L2-M1).

  · LISTADOS SECUNDARIOS (lote 2026-10-14): una empresa del catálogo puede traer `listings` [{symbol, mic,
    yahoo_symbol, is_primary, kind, currency, source_url, as_of, note, home?, ordinary_per_depositary?}] (la MISMA
    forma que escribe el importador E2). El `mkt` sigue siendo el primario (= el listado con is_primary) y los
    demás se siembran como instrumentos `is_primary = False` (`secondary_from_catalog`) — p. ej. TSMC: TSM (ADR,
    el que cotiza la UI) primario y 2330.TW (bolsa de origen, `home`) secundario; TEL: 8035.T primario y TOELY
    secundario. `classify` toma el tipo del listado primario y marca `multi_listed` si hay otro con símbolo.
    `LOT_2026_10_14` = qué se hizo con cada uno de los 19 símbolos revisados (y qué debe decidir Fabrizio).

  · UNIVERSO ÚNICO (lote L, 2026-10-15): `universe()` recorre el grafo VIGENTE una sola vez (`_scan`: catálogo +
    empresas importadas a Postgres; primario = `mkt`, o el listado `is_primary` de props.listings[], o
    ids.yahoo_symbol si la ficha no declara listados; un símbolo de Yahoo una sola vez —el primer dueño gana y el
    conflicto se lista—; símbolos imposibles fuera; listados «dado de baja» / `delisted_at` vencido marcados).
    `live_symbols()` alimenta la capitalización/precio en vivo (core/live_caps) y los fundamentales en vivo
    (core/live_fundamentals); `eod_symbols()` la historia diaria (core/prices_store); la siembra de `instruments`
    usa el mismo recorrido. `phase_in()` mete los símbolos NUEVOS por tandas (el catálogo del repo entra siempre).

Sin red, sin IA. Funciona sin base (las funciones puras); `seed` solo con DATABASE_URL.
"""
import re

# sufijo de Yahoo → (bolsa, moneda en la que Yahoo da el precio, ¿cierra con Nueva York?)
SUFFIX = {
    '': ('NYSE/Nasdaq', 'USD', True),
    'T': ('Tokyo (TSE)', 'JPY', False), 'HK': ('Hong Kong (HKEX)', 'HKD', False),
    'AX': ('Australia (ASX)', 'AUD', False), 'SS': ('Shanghái (SSE)', 'CNY', False),
    'SZ': ('Shenzhen (SZSE)', 'CNY', False), 'TW': ('Taiwán (TWSE)', 'TWD', False),
    'TWO': ('Taiwán (TPEx)', 'TWD', False), 'KS': ('Corea (KRX)', 'KRW', False), 'KQ': ('Corea (KOSDAQ)', 'KRW', False),
    'DE': ('Fráncfort (Xetra)', 'EUR', False), 'F': ('Fráncfort', 'EUR', False), 'L': ('Londres (LSE)', 'GBp', False),
    'IL': ('Londres (LSE IOB, GDR)', 'USD', False),
    'PA': ('Euronext París', 'EUR', False), 'AS': ('Euronext Ámsterdam', 'EUR', False),
    'BR': ('Euronext Bruselas', 'EUR', False), 'MI': ('Milán', 'EUR', False), 'MC': ('Madrid', 'EUR', False),
    'LS': ('Lisboa', 'EUR', False), 'HE': ('Helsinki', 'EUR', False), 'IR': ('Dublín', 'EUR', False),
    'VI': ('Viena', 'EUR', False), 'ST': ('Estocolmo', 'SEK', False), 'CO': ('Copenhague', 'DKK', False),
    'OL': ('Oslo', 'NOK', False), 'SW': ('Suiza (SIX)', 'CHF', False), 'WA': ('Varsovia', 'PLN', False),
    'ME': ('Moscú', 'RUB', False), 'NS': ('India (NSE)', 'INR', False), 'BO': ('India (BSE)', 'INR', False),
    'SI': ('Singapur (SGX)', 'SGD', False), 'JK': ('Indonesia (IDX)', 'IDR', False), 'QA': ('Qatar', 'QAR', False),
    'SR': ('Arabia Saudita (Tadawul)', 'SAR', False), 'TA': ('Tel Aviv (TASE)', 'ILA', False),
    'JO': ('Johannesburgo (JSE)', 'ZAc', False), 'NZ': ('Nueva Zelanda (NZX)', 'NZD', False),
    'TO': ('Toronto (TSX)', 'CAD', True), 'V': ('TSX Venture', 'CAD', True), 'NE': ('Cboe Canadá', 'CAD', True),
    'MX': ('México (BMV)', 'MXN', True), 'SA': ('São Paulo (B3)', 'BRL', True),
}
# subunidades que Yahoo usa para algunas bolsas: precio en peniques/centavos/agorot
MINOR_UNITS = {'GBp': ('GBP', 0.01), 'GBX': ('GBP', 0.01), 'ZAc': ('ZAR', 0.01), 'ILA': ('ILS', 0.01)}
OTC_RX = re.compile(r'^[A-Z]{4}[FY]$')
REFERENCE = (('SPY', 'etf', 'USD', 'NYSE Arca'), ('^IRX', 'rate', 'USD', 'Cboe (T-bill 13 semanas)'))

# texto de bolsa del catálogo → sufijo de Yahoo (para proponer la ALTERNATIVA local en la lista de revisión)
_VENUE_SUFFIX = (('Tokyo', 'T'), ('TSE', 'T'), ('HKEX', 'HK'), ('Hong Kong', 'HK'), ('KRX', 'KS'),
                 ('Bolsa de Corea', 'KS'), ('TWSE', 'TW'), ('LSE', 'L'), ('Frankfurt', 'DE'), ('Xetra', 'DE'),
                 ('STAR', 'SS'), ('SSE', 'SS'), ('Shanghai', 'SS'), ('Shenzhen', 'SZ'), ('TSXV', 'V'), ('TSX', 'TO'),
                 ('ASX', 'AX'), ('B3', 'SA'), ('BMV', 'MX'), ('JSE', 'JO'), ('NSE', 'NS'), ('Oslo', 'OL'),
                 ('TASE', 'TA'), ('BVL', 'LM'))
_EURONEXT = {'ASM': 'AS', 'BESI': 'AS', 'AI': 'PA', 'SU': 'PA', 'AIR': 'PA', 'MT': 'AS', 'TTE': 'PA'}


def suffix_of(symbol):
    s = str(symbol or '').upper()
    if '=' in s or s.startswith('^'):
        return None
    if '.' not in s:
        return ''
    return s.rsplit('.', 1)[1]


def exchange_info(symbol):
    """(bolsa, moneda, sincroniza_con_NY) para un símbolo de Yahoo; sufijo desconocido → (None, None, True)."""
    suf = suffix_of(symbol)
    if suf is None:
        return (None, 'USD', True)
    return SUFFIX.get(suf, (None, None, True))


def nonsync(symbol):
    """¿Cierra en otro horario que Nueva York? (Asia, Europa, Oceanía, Medio Oriente) → beta de Dimson (L2-M1)."""
    return not exchange_info(symbol)[2]


def major_ccy(ccy):
    """'GBp' → ('GBP', 0.01); 'JPY' → ('JPY', 1.0); None/'' → ('USD', 1.0)."""
    if not ccy:
        return 'USD', 1.0
    if ccy in MINOR_UNITS:
        return MINOR_UNITS[ccy]
    return str(ccy).upper(), 1.0


_KIND_MAP = {'gdr': 'adr', 'a_share': 'equity', 'h_share': 'equity', 'dual_class': 'equity', 'preferred': 'equity'}
# símbolo de Yahoo utilizable (mayúsculas): NVDA, 2330.TW, MAERSK-B.CO, BRK-B, ^IRX, JPYUSD=X — nunca espacios ni [ ]
SYMBOL_RX = re.compile(r'^[A-Z0-9^][A-Z0-9.\-=&]{0,31}$')


def primary_symbol(node):
    """EL símbolo principal de una empresa del grafo: `mkt` (catálogo, o el que escribe el importador = el listado
    principal); si no hay `mkt`, el listado con `is_primary` true de sus `listings` (propiedades de Postgres); si la
    empresa no declara listados, su `ids.yahoo_symbol`. None si no cotiza. Nunca inventa: solo lee la ficha."""
    mkt = str(node.get('mkt') or '').strip().upper()
    if mkt:
        return mkt
    lst = node.get('listings') if isinstance(node.get('listings'), (list, tuple)) else []
    for raw in lst:
        if isinstance(raw, dict) and raw.get('is_primary') is True:
            ys = str(raw.get('yahoo_symbol') or '').strip().upper()
            if ys:
                return ys
    if not lst:
        ids = node.get('ids') if isinstance(node.get('ids'), dict) else {}
        ys = str(ids.get('yahoo_symbol') or '').strip().upper()
        if ys:
            return ys
    return None


def listings_of(node):
    """Los listados declarados en la ficha del catálogo (`listings`), normalizados: símbolo de Yahoo en mayúsculas,
    `is_primary` = coincide con el símbolo principal (`primary_symbol`: el `mkt`; sin `mkt`, el que la ficha marca
    `is_primary`). Lista vacía si la empresa no los declara (la mayoría del catálogo, hoy)."""
    prim = primary_symbol(node)
    out = []
    for raw in node.get('listings') or []:
        if not isinstance(raw, dict):
            continue
        ys = str(raw.get('yahoo_symbol') or '').strip().upper() or None
        kind = _KIND_MAP.get(str(raw.get('kind') or 'equity').lower(), str(raw.get('kind') or 'equity').lower())
        out.append({'symbol': str(raw.get('symbol') or (ys or '').split('.')[0]).upper(), 'mic': raw.get('mic'),
                    'yahoo_symbol': ys, 'is_primary': bool(ys and ys == prim), 'kind': kind,
                    'currency': raw.get('currency'), 'source_url': raw.get('source_url'), 'as_of': raw.get('as_of'),
                    'note': raw.get('note'), 'home': bool(raw.get('home')),
                    'ordinary_per_depositary': raw.get('ordinary_per_depositary'),
                    'delisted_at': raw.get('delisted_at')})
    return out


def listing_delisted(listing, today=None):
    """¿Listado DADO DE BAJA? — nota «dado de baja» (catálogo, lote 2026-10-14) o `delisted_at` (ficha importada)
    en una fecha ya pasada; una fecha parcial ('2025', '2025-06') cuenta desde su primer día. Una baja anunciada
    para el futuro todavía cotiza."""
    if not isinstance(listing, dict):
        return False
    if 'dado de baja' in str(listing.get('note') or '').lower():
        return True
    raw = str(listing.get('delisted_at') or '').strip()
    if not raw:
        return False
    from datetime import date, datetime, timezone
    today = today or datetime.now(timezone.utc).date()
    m = re.match(r'^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?', raw)
    if not m:
        return True                    # algo dice que se dio de baja pero sin fecha legible: no se baja a diario
    try:
        d = date(int(m.group(1)), int(m.group(2) or 1), int(m.group(3) or 1))
    except ValueError:
        return True
    return d <= today


def declared_exchange(node, symbol):
    """Bolsa de un listado DECLARADO: el MIC manda (OTCM = certificado OTC en EE.UU., no NYSE/Nasdaq); si no, el
    sufijo de Yahoo. None si la empresa no declara ese símbolo."""
    sym = str(symbol or '').upper()
    for l in listings_of(node):
        if l['yahoo_symbol'] == sym:
            if str(l['mic'] or '').upper() == 'OTCM':
                return 'OTC (EE.UU.)'
            return exchange_info(sym)[0] or (l['mic'] and f"MIC {l['mic']}") or None
    return None


def secondary_listings(node):
    """Listados declarados que NO son el primario y sí tienen símbolo de Yahoo (los sin símbolo solo se anotan)."""
    return [l for l in listings_of(node) if not l['is_primary'] and l['yahoo_symbol']]


def classify(node):
    """{kind, review} de una empresa del catálogo (mkt + texto 'ticker'; si declara `listings`, mandan esos)."""
    mkt = str(node.get('mkt') or '').strip()
    txt = str(node.get('ticker') or '')
    decl = listings_of(node)
    if decl:
        prim = next((l for l in decl if l['is_primary']), None)
        kind = prim['kind'] if prim else 'equity'
        if kind not in ('equity', 'adr', 'otc'):
            kind = 'equity'
        return {'kind': kind, 'review': 'multi_listed' if secondary_listings(node) else None}
    multi = ' / ' in txt
    otc = bool(OTC_RX.match(mkt)) or 'OTC' in txt.upper()
    parts = [p.strip() for p in txt.split('/')]
    mine = next((p for p in parts if p.upper().startswith(mkt.split('.')[0] + ' ')), '')   # el tramo de ESTE símbolo
    if 'OTC' in mine.upper():
        kind = 'otc'
    elif OTC_RX.match(mkt):
        kind = 'otc' if mkt.endswith('F') else 'adr'       # F = acción extranjera en OTC · Y = ADR patrocinado
    elif '(ADR)' in mine.upper() or 'ADR' in mine.upper().split():
        kind = 'adr'
    else:
        kind = 'equity'
    review = 'multi_listed' if multi else ('otc_adr' if otc else None)
    return {'kind': kind, 'review': review}


def local_alternative(node):
    """Para un caso de revisión: el símbolo de Yahoo del OTRO listado que declara el texto del catálogo (la acción
    local, o el listado de origen) — o None si no se puede deducir."""
    mkt = str(node.get('mkt') or '').strip().upper()
    sec = secondary_listings(node)
    if sec:
        return sec[0]['yahoo_symbol']           # listado declarado (bolsa de origen primero, luego el resto)
    base = mkt.split('.')[0]
    txt = str(node.get('ticker') or '')
    for part in [p.strip() for p in re.split(r'\s/\s|/|;', txt) if p.strip()]:
        m = re.match(r'^([0-9A-Z][0-9A-Z.\-]*)\s*·\s*(.+)$', part)
        code, venue = (m.group(1).upper(), m.group(2)) if m else (base, part)
        if 'OTC' in venue.upper() or venue.strip().upper().startswith(('NYSE', 'NASDAQ')):
            continue
        cand = None
        if 'Euronext' in venue and code in _EURONEXT:
            cand = f'{code}.{_EURONEXT[code]}'
        else:
            for key, suf in _VENUE_SUFFIX:
                if key in venue:
                    cand = f'{code.zfill(4) if suf == "HK" and code.isdigit() else code}.{suf}'
                    break
        if cand and cand != mkt:
            return cand
    return None


def _scan(nodes):
    """EL recorrido único del grafo (lote L, 2026-10-15) — lo usan la siembra de `instruments`, el universo en vivo y
    la historia diaria, así nunca divergen. En el orden del grafo (catálogo primero, lo nuevo después por id):
      · primarios: uno por SÍMBOLO (el primer dueño gana; otro nodo que declare el mismo símbolo es un conflicto);
      · secundarios: listados declarados que no son el primario de nadie, una vez cada uno;
      · inválidos: símbolos que Yahoo no puede pedir (espacios, corchetes, demasiado largos) → fuera, listados.
    → (primarios [(nodo, símbolo, listado|None)], secundarios [(nodo, símbolo, listado)], conflictos, inválidos)."""
    prim, sec, conflicts, invalid = [], [], [], []
    owner = {}
    for n in nodes or []:
        if not isinstance(n, dict) or not n.get('id'):
            continue
        sym = primary_symbol(n)
        if not sym:
            continue
        if not SYMBOL_RX.match(sym):
            invalid.append({'company_id': str(n['id']), 'symbol': sym, 'role': 'primary'})
            continue
        if sym in owner:
            if owner[sym] != n['id']:
                conflicts.append({'symbol': sym, 'owner': owner[sym], 'other': str(n['id'])})
            continue
        owner[sym] = n['id']
        lst = next((l for l in listings_of(n) if l['yahoo_symbol'] == sym), None)
        prim.append((n, sym, lst))
    seen = set()
    for n in nodes or []:
        if not isinstance(n, dict) or not n.get('id') or not primary_symbol(n):
            continue
        for l in secondary_listings(n):
            ys = l['yahoo_symbol']
            if ys in owner or ys in seen:
                continue
            if not SYMBOL_RX.match(ys):
                invalid.append({'company_id': str(n['id']), 'symbol': ys, 'role': 'secondary'})
                continue
            seen.add(ys)
            sec.append((n, ys, l))
    return prim, sec, conflicts, invalid


def _origin_source(n, sym):
    """'import' para la cotización de una empresa que entró por el importador y no está en el catálogo del repo."""
    base = baseline_symbols()
    return 'import' if (n.get('imported') is True and base and sym not in base) else 'catalog'


def from_catalog(nodes):
    """Instrumentos primarios (uno por empresa cotizada; el `mkt` de hoy o, en una empresa importada sin `mkt`, su
    listado principal) — dicts listos para insertar."""
    out = []
    for n, mkt, lst in _scan(nodes)[0]:
        exch, ccy, _sync = exchange_info(mkt)
        c = classify(n)
        note = {'catalog_ticker': str(n.get('ticker') or '')[:200]}
        sec = secondary_listings(n)
        if sec:
            note['secondaries'] = [l['yahoo_symbol'] for l in sec]
        if lst and lst.get('delisted_at'):
            note['delisted_at'] = str(lst['delisted_at'])
        out.append({'id': mkt[:32], 'company_id': str(n['id'])[:120], 'ticker': mkt[:32],
                    'exchange': exch or (declared_exchange(n, mkt) if lst else None),
                    # sufijo que la tabla SUFFIX no conoce (.BK, .SN…): la moneda DECLARADA en la ficha, nunca inventada
                    'currency': ccy or (lst or {}).get('currency'), 'kind': c['kind'], 'is_primary': True,
                    'review': c['review'], 'note': note, 'source': _origin_source(n, mkt)})
    return out


def secondary_from_catalog(nodes):
    """Instrumentos SECUNDARIOS (is_primary False) de las empresas que declaran `listings` — nunca el primario, nunca
    un símbolo que ya sea primario de alguien; el precio de referencia sigue siendo el primario."""
    out = []
    for n, ys, l in _scan(nodes)[1]:
        mkt = primary_symbol(n)
        _e, ccy, _s = exchange_info(ys)
        out.append({'id': ys[:32], 'company_id': str(n['id'])[:120], 'ticker': ys[:32],
                    'exchange': declared_exchange(n, ys),
                    'currency': ccy or l['currency'], 'kind': l['kind'] if l['kind'] in ('equity', 'adr', 'otc') else 'equity',
                    'is_primary': False, 'review': None,
                    'note': {k: v for k, v in (('primary', mkt), ('mic', l['mic']), ('home', l['home'] or None),
                                               ('note', l['note']), ('source_url', l['source_url']),
                                               ('as_of', l['as_of']),
                                               ('delisted_at', str(l['delisted_at']) if l.get('delisted_at') else None))
                             if v},
                    'source': _origin_source(n, ys)})
    return out


def reference_instruments(currencies=()):
    """SPY e ^IRX (referencias del riesgo) + un par {CUR}USD=X por moneda extranjera."""
    out = [{'id': s, 'company_id': None, 'ticker': s, 'exchange': ex, 'currency': c, 'kind': k, 'is_primary': True,
            'review': None, 'note': None, 'source': 'reference'} for s, k, c, ex in REFERENCE]
    for ccy in sorted({major_ccy(c)[0] for c in currencies if c} - {'USD'}):
        out.append({'id': f'{ccy}USD=X', 'company_id': None, 'ticker': f'{ccy}USD=X', 'exchange': 'FX',
                    'currency': 'USD', 'kind': 'fx', 'is_primary': True, 'review': None, 'note': {'ccy': ccy},
                    'source': 'reference'})
    return out


def catalog_nodes():
    """Los nodos vigentes por EL accesor único (core/hotviews/hot.graph(): Postgres o, sin base, el snapshot)."""
    from core.hotviews import hot
    return list((hot.graph().snapshot or {}).get('nodes') or [])


def all_instruments(nodes=None):
    nodes = catalog_nodes() if nodes is None else nodes
    prim = from_catalog(nodes)
    sec = secondary_from_catalog(nodes)
    return prim + sec + reference_instruments(i['currency'] for i in prim + sec)


# ── EL UNIVERSO DE COTIZACIONES (lote L, 2026-10-15) ─────────────────────────────────────────────────────────────
# Hasta el lote L, la capitalización/precio en vivo (core/live_caps), los fundamentales en vivo (core/live_fundamentals,
# que lee el mismo mapa) y la historia diaria (core/prices_store) se armaban cada uno a su manera sobre el catálogo
# (~570 símbolos). Ahora los tres leen `universe()`: el grafo VIGENTE (catálogo + empresas importadas a Postgres, con
# su listado principal en props.listings[] / mkt / ids.yahoo_symbol), un símbolo de Yahoo una sola vez, los listados
# dados de baja fuera. La capitalización y las acciones en circulación salen SIEMPRE del perfil en vivo (Yahoo): la
# ficha nunca trae cifras de mercado (el esquema las prohíbe) y aquí no se lee ninguna.
# Los símbolos NUEVOS (los que el catálogo del repo no tiene) entran POR TANDAS (`phase_in`): el primer ciclo después
# de importar 4.000 empresas no puede salir en ráfaga.
_BASELINE = {'sha': None, 'set': frozenset()}


def baseline_symbols():
    """Símbolos que la app ya seguía ANTES de importar: los del catálogo del repo (data/grafo_v0.json: primarios y
    listados declarados) + SPY/^IRX. Entran siempre, sin tandas. Vacío si el snapshot no se puede leer (entonces
    `phase_in` no frena nada: mejor seguir como hoy que dejar el mapa sin precios)."""
    try:
        from core.hotviews.source import _snapshot_parsed
        g, sha = _snapshot_parsed()
    except Exception:  # noqa: BLE001
        return frozenset()
    if _BASELINE['sha'] != sha:
        out = {s for s, _k, _c, _e in REFERENCE}
        for n in g.get('nodes') or []:
            p = primary_symbol(n)
            if p:
                out.add(p)
            for l in listings_of(n):
                if l['yahoo_symbol']:
                    out.add(l['yahoo_symbol'])
        _BASELINE.update(sha=sha, set=frozenset(out))
    return _BASELINE['set']


def universe(nodes=None, today=None):
    """EL universo de cotizaciones del grafo vigente. → {
         'primary':   [{symbol, company_id, kind, currency, origin, imported, delisted}]  (uno por símbolo; orden de
                      prioridad: catálogo del repo → otros nodos de la base → importados, cada grupo en el orden del grafo),
         'secondary': [ídem, role secundario] (listados declarados no primarios),
         'conflicts': [{symbol, owner, other}]  (dos empresas con el mismo símbolo: gana la primera; la otra se lista),
         'invalid':   [{company_id, symbol, role}],
         'nodes': cuántos nodos se miraron}.
    `origin` = 'catalog' si el símbolo ya estaba en el catálogo del repo (baseline), 'new' si no."""
    nodes = catalog_nodes() if nodes is None else nodes
    prim, sec, conflicts, invalid = _scan(nodes)
    base = baseline_symbols()

    def entry(n, sym, l, role, idx):
        exch_ccy = exchange_info(sym)[1]
        new = bool(base) and sym not in base
        imported = n.get('imported') is True
        return {'symbol': sym, 'company_id': str(n['id']), 'role': role,
                'kind': (l or {}).get('kind') or classify(n)['kind'],
                'currency': exch_ccy or (l or {}).get('currency'),
                'origin': 'new' if new else 'catalog', 'imported': imported,
                'delisted': listing_delisted(l, today) if l else False,
                '_rank': (0 if not new else (2 if imported else 1), idx)}
    P = [entry(n, s, l, 'primary', i) for i, (n, s, l) in enumerate(prim)]
    S = [entry(n, s, l, 'secondary', i) for i, (n, s, l) in enumerate(sec)]
    for lst in (P, S):
        lst.sort(key=lambda e: e['_rank'])
        for e in lst:
            e.pop('_rank', None)
    return {'primary': P, 'secondary': S, 'conflicts': conflicts, 'invalid': invalid, 'nodes': len(nodes or [])}


def live_symbols(nodes=None, today=None):
    """{company_id: símbolo} para lo EN VIVO (capitalización, precio, fundamentales): los primarios vigentes del
    universo, uno por símbolo, en orden de prioridad (catálogo → base → importados)."""
    u = universe(nodes, today)
    return {e['company_id']: e['symbol'] for e in u['primary'] if not e['delisted']}


def eod_symbols(nodes=None, today=None):
    """Lo que la historia DIARIA baja (core/prices_store): {'equities': [símbolos en orden de prioridad: primarios y
    luego secundarios, sin los dados de baja], 'currencies': {monedas mayores que piden un par FX}}."""
    u = universe(nodes, today)
    eq = [e['symbol'] for e in u['primary'] + u['secondary'] if not e['delisted']]
    ccys = {major_ccy(e['currency'])[0] for e in u['primary'] + u['secondary'] if not e['delisted'] and e['currency']}
    return {'equities': eq, 'currencies': ccys - {'USD'}}


def phase_in(symbols, admitted, limit, baseline=None, offset=0):
    """Tandas para los símbolos NUEVOS. `symbols` en orden de prioridad (sin repetidos); `admitted` = los nuevos que
    ya entraron (en memoria, o con historia guardada); `limit` = cuántos nuevos pueden entrar en este ciclo; `offset`
    rota la ventana (la historia diaria la mueve con el día: un símbolo que nunca trae datos no tapa a los demás).
    Los del catálogo (`baseline`) y los ya admitidos entran SIEMPRE. Puro.
    → (incluidos en este ciclo, nuevos admitidos ahora, nuevos que siguen esperando)."""
    base = baseline_symbols() if baseline is None else baseline
    syms = list(dict.fromkeys(symbols or []))
    if not base:                      # sin catálogo legible no se frena nada (nunca dejar el mapa sin precios)
        return syms, [], []
    adm = set(admitted or ())
    fresh = [s for s in syms if s not in base and s not in adm]
    window = fresh
    if fresh and offset:
        k = int(offset) % len(fresh)
        window = fresh[k:] + fresh[:k]
    take = set(window[:max(0, int(limit or 0))])
    inc = [s for s in syms if s in base or s in adm or s in take]
    return inc, [s for s in fresh if s in take], [s for s in fresh if s not in take]


def review_list(nodes=None):
    """Los casos que Fabrizio debe revisar (BRECHAS #9), en el orden: varios listados, luego OTC/ADR."""
    nodes = catalog_nodes() if nodes is None else nodes
    rows = []
    for n in nodes:
        mkt = str(n.get('mkt') or '').strip().upper()
        if not mkt:
            continue
        if _origin_source(n, mkt) == 'import':
            # lote L: la cotización principal de una empresa IMPORTADA la eligió su ficha (con fuente); no es una
            # duda del catálogo. Las fusionadas con el catálogo (su `mkt` es el de siempre) sí siguen en la lista.
            continue
        c = classify(n)
        if not c['review']:
            continue
        alt = local_alternative(n)
        alt_exch, alt_ccy, _s = exchange_info(alt) if alt else (None, None, True)
        alt_exch = declared_exchange(n, alt) or alt_exch
        cur_exch, cur_ccy, _s2 = exchange_info(mkt)
        cur_exch = declared_exchange(n, mkt) or cur_exch
        rows.append({'id': n['id'], 'label': n.get('label') or n['id'], 'current': mkt, 'current_kind': c['kind'],
                     'current_exchange': cur_exch, 'current_currency': cur_ccy,
                     'catalog_ticker': str(n.get('ticker') or ''), 'review': c['review'],
                     'alternative': alt, 'alternative_exchange': alt_exch,
                     'alternative_currency': major_ccy(alt_ccy)[0] if alt_ccy else None,
                     'declared': [l['yahoo_symbol'] for l in secondary_listings(n)],
                     'recommend': _recommend(c, mkt, alt)})
    rows.sort(key=lambda r: (0 if r['review'] == 'multi_listed' else 1, r['label'].lower()))
    return rows


def _recommend(c, mkt, alt):
    """Recomendación simple (Fabrizio decide): un certificado OTC → la acción local (más negociada, precio de
    referencia real); un listado en NYSE/Nasdaq que ya es el de hoy → mantenerlo."""
    if alt is None:
        return 'keep'
    if c['review'] == 'otc_adr' or c['kind'] == 'otc':
        return 'local'
    return 'keep'


def primary_conflicts(session):
    """Empresas con MÁS de un instrumento primario en la base (pasa cuando el catálogo cambia de símbolo: la siembra
    nunca pisa, así que el viejo sigue marcado primario hasta que Fabrizio lo decida). Solo lectura."""
    from sqlalchemy import text
    rows = session.execute(text("SELECT company_id, array_agg(id ORDER BY created_at, id) FROM instruments "
                                "WHERE is_primary AND company_id IS NOT NULL GROUP BY company_id "
                                "HAVING count(*) > 1 ORDER BY company_id")).all()
    return [{'company_id': r[0], 'primaries': list(r[1])} for r in rows]


# ── Lote 2026-10-14: los 19 símbolos revisados (data/import/lotes/2026-10-14/existentes_simbolos_revisar.csv) ─────
# action: applied = corregido en nodes/*.js · confirmed = el catálogo ya estaba bien (fuente en listing_status.js)
#         · fabrizio = la investigación contradice un dato GENERADO (nodes/listing_status.js) o no se pudo verificar
LOT_2026_10_14 = (
    ('SiTime', 'SiTime', 'SITT / SITS', 'SITM', 'applied', 'https://investor.sitime.com/',
     'SITT no existía (y nodes_spacex.js decía SITS); el ticker de SiTime en Nasdaq es SITM.'),
    ('SKHynix', 'SK Hynix', 'HXSCL', '000660.KS', 'applied', 'https://www.skhynix.com/ir/',
     'HXSCL era incorrecto; la cotización principal es 000660 en la Bolsa de Corea (KRX).'),
    ('qinetiq', 'QinetiQ', 'QQ.', 'QQ.L', 'applied', 'https://www.qinetiq.com/en/investors',
     'Símbolo mal escrito; en Yahoo la acción de Londres es QQ.L.'),
    ('TEL', 'Tokyo Electron', 'TOELY', '8035.T (+ TOELY secundario)', 'applied', 'https://www.tel.com/ir/stock/',
     'La acción de Tokio pasa a primaria; el ADR TOELY queda como listado secundario (el agregador lo da de baja).'),
    ('Ajinomoto', 'Ajinomoto', 'AJINY', '2802.T (+ AJINY secundario)', 'applied',
     'https://www.ajinomoto.co.jp/company/en/ir/stock/',
     'La acción de Tokio pasa a primaria; el ADR AJINY queda como secundario (el agregador lo da de baja).'),
    ('SiemensEnergy', 'Siemens Energy', 'SMNEY', 'ENR.DE (+ SMNEY secundario)', 'applied',
     'https://www.siemens-energy.com/global/en/home/investor-relations/share.html',
     'La acción de Xetra pasa a primaria; el ADR SMNEY queda como secundario (el agregador lo da de baja).'),
    ('VulcanEnergy', 'Vulcan Energy', 'VUL.DE', 'VUL.AX (+ Fráncfort sin símbolo)', 'applied',
     'https://v-er.eu/investors/',
     'VUL.DE no existe en el agregador; la principal es la ASX (VUL.AX). El listado de Fráncfort queda anotado sin '
     'símbolo de Yahoo verificado.'),
    ('TSMC', 'TSMC', 'TSM', 'TSM (ADR, sigue cotizando en la UI) + 2330.TW secundario', 'applied',
     'https://investor.tsmc.com/english/stock-information',
     'Se registra la bolsa de origen 2330.TW como listado secundario (home); el ADR TSM (1 ADR = 5 acciones) sigue '
     'siendo el primario porque hoy es el que cotiza la app (nada cambia solo).'),
    ('astroscale', 'Astroscale', '5034.T', '186A.T (en la fila cruda; listing_status.js sigue diciendo 5034.T)',
     'fabrizio', 'https://astroscale.com/ir/',
     '5034.T es unerry, Inc. Astroscale Holdings cotiza en TSE Growth como 186A desde jun-2024. La fila del catálogo '
     'ya dice 186A.T, pero nodes/listing_status.js (GENERADO el 2026-09-29) la pisa con 5034.T: hay que corregir '
     'data/listing_verification/ (astroscale → 186A.T, fuente astroscale.com/ir) y regenerar con '
     'scripts/build_listing_status.py.'),
    ('Kazatomprom', 'Kazatomprom', 'KAP.L', 'KAP.L (sin cambio)', 'fabrizio', 'https://www.kazatomprom.kz/en/investors',
     'El GDR cotiza en Londres (IOB); el agregador no conoce KAP.L y en Yahoo el GDR suele ir como KAP.IL (USD). '
     'La acción local es KAP en AIX/KASE (KZT). listing_status.js impone KAP.L: decidir KAP.IL o KAP (AIX) y '
     'regenerar.'),
    ('enflame', 'Enflame Technology', '688801.SS', '688801.SS (sin cambio)', 'confirmed',
     'https://www.cnbc.com/2026/09/11/chinese-nvidia-rival-enflame-stock-market-debut-ai.html',
     'Salida a bolsa reciente (STAR, 11-sep-2026): el agregador aún no la tiene; la fuente primaria confirma el código.'),
    ('moorethreads', 'Moore Threads', '688795.SS', '688795.SS (sin cambio)', 'confirmed', 'https://english.sse.com.cn/',
     'Salida a bolsa reciente (STAR, 2026): el agregador aún no la tiene.'),
    ('Meeza', 'Meeza', 'MEZA.QA', 'MEZA.QA (sin cambio)', 'confirmed',
     'https://www.meeza.net/meeza-successfully-listed-on-qatar-stock-exchange-main-market/',
     'Cotiza en la Bolsa de Catar desde ago-2023 (fuente primaria); sufijo .QA correcto.'),
    ('Mindspace Business Parks REIT', 'Mindspace Business Parks REIT', 'MINDSPACE.NS', 'MINDSPACE.NS (sin cambio)',
     'confirmed', 'https://www.mindspacereit.com/investors', 'REIT listado en NSE/BSE; símbolo de Yahoo correcto.'),
    ('Uniper', 'Uniper', 'UN01.DE', 'UN01.DE (sin cambio)', 'fabrizio',
     'https://www.bloomberg.com/news/articles/2026-05-19/german-government-launches-privatization-of-energy-firm-uniper-mpc7nu4l',
     'El agregador lo marca dado de baja; listing_status.js (fuente Bloomberg, may-2026) dice que cotiza en Xetra con '
     '~99 % del Estado (flotante mínimo). Confirmar si sigue listado.'),
    ('northern-data', 'Northern Data Group', 'NB2.DE', 'NB2.DE (sin cambio)', 'fabrizio',
     'https://www.boerse-frankfurt.de/en',
     'El agregador lo marca dado de baja (posible cierre de la compra por Rumble); listing_status.js lo da por cotizado '
     'con fuente genérica. Confirmar antes de cambiar.'),
    ('Qorvo', 'Qorvo', 'QRVO', 'QRVO (sin cambio)', 'fabrizio',
     'https://finance.yahoo.com/technology/articles/skyworks-solutions-sees-qorvo-deal-140319451.html',
     'El agregador lo marca dado de baja (fusión con Skyworks); listing_status.js (sep-2026) decía pendiente de China y '
     'Corea. Si la fusión cerró, Qorvo pasa a "acquired" por Skyworks (SWKS).'),
    ('Asetek', 'Asetek', 'ASTK.CO', 'ASTK.CO (sin cambio)', 'fabrizio', 'https://www.nasdaqomxnordic.com/',
     'El agregador lo marca dado de baja; listing_status.js lo da por cotizado en Nasdaq Copenhague con fuente '
     'genérica. Confirmar.'),
    ('AustralianStrategicMaterials', 'Australian Strategic Materials', 'ASM.AX', 'ASM.AX (sin cambio)', 'fabrizio',
     'https://asm-au.com/investors/',
     'El agregador lo marca dado de baja (compra por Energy Fuels anunciada en ene-2026, cierre pospuesto). Si cerró, '
     'pasa a "acquired" por Energy Fuels (UUUU).'),
)
_ACTION = {'applied': 'corregido en el catálogo', 'confirmed': 'confirmado (sin cambio)',
           'fabrizio': 'decide Fabrizio'}


def lot_review_markdown():
    """Sección del documento de revisión con los 19 símbolos del lote 2026-10-14 (docs/REVISION_INSTRUMENTOS.md)."""
    n_app = sum(1 for r in LOT_2026_10_14 if r[4] == 'applied')
    n_ok = sum(1 for r in LOT_2026_10_14 if r[4] == 'confirmed')
    n_fab = sum(1 for r in LOT_2026_10_14 if r[4] == 'fabrizio')
    out = ['', f'## 3. Lote 2026-10-14: los {len(LOT_2026_10_14)} símbolos que no cuadraban con el agregador', '',
           'La investigación externa (`data/import/lotes/2026-10-14/existentes_simbolos_revisar.csv`) comparó el '
           'catálogo con una base de cotizaciones. Regla aplicada: **la cotización principal es la de la bolsa de '
           'origen; los ADR/OTC son secundarios** (quedan registrados en `listings` de la ficha y en la tabla '
           '`instruments` como secundarios, nunca se borran).',
           '',
           f'- **{n_app} corregidos** en `nodes/*.js` (con su fuente en `listings[].source_url`).',
           f'- **{n_ok} confirmados** (el catálogo ya estaba bien; el agregador no conocía el símbolo).',
           f'- **{n_fab} para que decidas tú** (la investigación contradice `nodes/listing_status.js`, que es GENERADO '
           'y no se toca a mano, o no se pudo verificar sin red).',
           '',
           '| # | Empresa | Antes | Ahora | Qué pasó | Fuente | Nota |', '|---|---|---|---|---|---|---|']
    for i, (cid, label, before, after, action, src, note) in enumerate(LOT_2026_10_14, 1):
        out.append(f'| {i} | **{label}** (`{cid}`) | `{before}` | {after} | {_ACTION[action]} | {src} | {note} |')
    out += ['',
            'Ojo con la base: la siembra de `instruments` nunca pisa filas, así que los símbolos viejos (TOELY, AJINY, '
            'SMNEY, HXSCL, SITT, QQ., VUL.DE) siguen marcados como primarios hasta que se decida; '
            '`core.instruments.primary_conflicts()` los lista.']
    return out


def seed(session, nodes=None):
    """Inserta los instrumentos que falten (nunca actualiza). Devuelve cuántos insertó."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from ontology.history_models import Instrument
    rows = all_instruments(nodes)
    if not rows:
        return 0
    res = session.execute(pg_insert(Instrument.__table__).values(rows).on_conflict_do_nothing()
                          .returning(Instrument.__table__.c.id))
    return len(res.fetchall())
