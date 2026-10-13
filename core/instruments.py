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


def classify(node):
    """{kind, review} de una empresa del catálogo (mkt + texto 'ticker')."""
    mkt = str(node.get('mkt') or '').strip()
    txt = str(node.get('ticker') or '')
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


def from_catalog(nodes):
    """Instrumentos primarios (uno por empresa cotizada; el `mkt` de hoy) — dicts listos para insertar."""
    out, seen = [], set()
    for n in nodes or []:
        mkt = str(n.get('mkt') or '').strip().upper()
        if not mkt or not n.get('id') or mkt in seen:
            continue
        seen.add(mkt)
        exch, ccy, _sync = exchange_info(mkt)
        c = classify(n)
        out.append({'id': mkt[:32], 'company_id': str(n['id'])[:120], 'ticker': mkt[:32], 'exchange': exch,
                    'currency': ccy, 'kind': c['kind'], 'is_primary': True, 'review': c['review'],
                    'note': {'catalog_ticker': str(n.get('ticker') or '')[:200]}, 'source': 'catalog'})
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
    return prim + reference_instruments(i['currency'] for i in prim)


def review_list(nodes=None):
    """Los casos que Fabrizio debe revisar (BRECHAS #9), en el orden: varios listados, luego OTC/ADR."""
    nodes = catalog_nodes() if nodes is None else nodes
    rows = []
    for n in nodes:
        mkt = str(n.get('mkt') or '').strip().upper()
        if not mkt:
            continue
        c = classify(n)
        if not c['review']:
            continue
        alt = local_alternative(n)
        alt_exch, alt_ccy, _s = exchange_info(alt) if alt else (None, None, True)
        cur_exch, cur_ccy, _s2 = exchange_info(mkt)
        rows.append({'id': n['id'], 'label': n.get('label') or n['id'], 'current': mkt, 'current_kind': c['kind'],
                     'current_exchange': cur_exch, 'current_currency': cur_ccy,
                     'catalog_ticker': str(n.get('ticker') or ''), 'review': c['review'],
                     'alternative': alt, 'alternative_exchange': alt_exch,
                     'alternative_currency': major_ccy(alt_ccy)[0] if alt_ccy else None,
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
