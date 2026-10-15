"""core/import_normalize.py — normalización de la ficha khipus.company/1 a la convención interna (E2.2).

  · países: delega en `core/countries.py` (la tabla ÚNICA ISO-2 ↔ clave del catálogo, dueño "countries"); si ese
    módulo aún no está, un respaldo mínimo con las claves de core/world._COUNTRY (misma convención, nunca otra);
  · MIC (ISO 10383) → sufijo de Yahoo (`core/instruments.SUFFIX` + las bolsas que ese módulo no lista);
  · fechas parciales (AAAA, AAAA-MM, AAAA-MM-DD) → inicio/fin del período en UTC (nunca se inventa el día);
  · dinero: unidades de su moneda + período (el servidor convierte a USD con fx_daily; aquí no);
  · ids de Khipus a partir del nombre corto (CamelCase, el patrón del esquema).

Solo biblioteca estándar. Sin red, sin base, sin IA.
"""
import calendar
import re
import unicodedata
from datetime import datetime, timezone

# ── países ──────────────────────────────────────────────────────────────────────────────────────────────────────
# Respaldo (solo si core/countries no existe): clave del catálogo (core/world._COUNTRY) ↔ ISO-2 y nombres ES/EN.
_FALLBACK = {
    'US': ('EEUU', 'Estados Unidos', 'United States'), 'JP': ('Japon', 'Japón', 'Japan'),
    'CN': ('China', 'China', 'China'), 'TW': ('Taiwan', 'Taiwán', 'Taiwan'), 'KR': ('Corea', 'Corea del Sur', 'South Korea'),
    'DE': ('Alemania', 'Alemania', 'Germany'), 'FR': ('Francia', 'Francia', 'France'),
    'NL': ('PaisesBajos', 'Países Bajos', 'Netherlands'), 'GB': ('ReinoUnido', 'Reino Unido', 'United Kingdom'),
    'IL': ('Israel', 'Israel', 'Israel'), 'IN': ('India', 'India', 'India'), 'AU': ('Australia', 'Australia', 'Australia'),
    'CA': ('Canada', 'Canadá', 'Canada'), 'FI': ('Finlandia', 'Finlandia', 'Finland'), 'NO': ('Noruega', 'Noruega', 'Norway'),
    'CL': ('Chile', 'Chile', 'Chile'), 'RU': ('Rusia', 'Rusia', 'Russia'), 'AE': ('EAU', 'Emiratos Árabes Unidos', 'United Arab Emirates'),
    'SG': ('Singapur', 'Singapur', 'Singapore'), 'HK': ('HongKong', 'Hong Kong', 'Hong Kong'),
    'CH': ('Suiza', 'Suiza', 'Switzerland'), 'DK': ('Dinamarca', 'Dinamarca', 'Denmark'), 'BR': ('Brasil', 'Brasil', 'Brazil'),
    'QA': ('Catar', 'Catar', 'Qatar'), 'ZA': ('Sudafrica', 'Sudáfrica', 'South Africa'), 'PA': ('Panama', 'Panamá', 'Panama'),
    'IE': ('Irlanda', 'Irlanda', 'Ireland'), 'IT': ('Italia', 'Italia', 'Italy'), 'KZ': ('Kazajistan', 'Kazajistán', 'Kazakhstan'),
    'TH': ('Tailandia', 'Tailandia', 'Thailand'), 'LT': ('Lituania', 'Lituania', 'Lithuania'), 'MY': ('Malasia', 'Malasia', 'Malaysia'),
    'DZ': ('Argelia', 'Argelia', 'Algeria'), 'PL': ('Polonia', 'Polonia', 'Poland'), 'ID': ('Indonesia', 'Indonesia', 'Indonesia'),
    'KW': ('Kuwait', 'Kuwait', 'Kuwait'), 'ES': ('Espana', 'España', 'Spain'), 'UG': ('Uganda', 'Uganda', 'Uganda'),
    'MX': ('Mexico', 'México', 'Mexico'), 'SE': ('Suecia', 'Suecia', 'Sweden'), 'EG': ('Egipto', 'Egipto', 'Egypt'),
    'BE': ('Belgica', 'Bélgica', 'Belgium'), 'LU': ('Luxemburgo', 'Luxemburgo', 'Luxembourg'), 'UA': ('Ucrania', 'Ucrania', 'Ukraine'),
    'AZ': ('Azerbaiyan', 'Azerbaiyán', 'Azerbaijan'), 'IR': ('Iran', 'Irán', 'Iran'), 'AR': ('Argentina', 'Argentina', 'Argentina'),
    'NZ': ('NuevaZelanda', 'Nueva Zelanda', 'New Zealand'), 'SA': ('ArabiaSaudita', 'Arabia Saudita', 'Saudi Arabia'),
    'TR': ('Turquia', 'Turquía', 'Turkey'), 'VN': ('Vietnam', 'Vietnam', 'Vietnam'), 'PH': ('Filipinas', 'Filipinas', 'Philippines'),
    'PK': ('Pakistan', 'Pakistán', 'Pakistan'), 'NG': ('Nigeria', 'Nigeria', 'Nigeria'), 'KE': ('Kenia', 'Kenia', 'Kenya'),
    'CO': ('Colombia', 'Colombia', 'Colombia'), 'PE': ('Peru', 'Perú', 'Peru'), 'AT': ('Austria', 'Austria', 'Austria'),
    'PT': ('Portugal', 'Portugal', 'Portugal'), 'GR': ('Grecia', 'Grecia', 'Greece'), 'CZ': ('Chequia', 'Chequia', 'Czechia'),
    'HU': ('Hungria', 'Hungría', 'Hungary'), 'RO': ('Rumania', 'Rumania', 'Romania'),
    # fuera del catálogo de hoy (clave = nombre en inglés sin espacios, como pide el contrato)
    'KY': ('CaymanIslands', 'Islas Caimán', 'Cayman Islands'), 'BM': ('Bermuda', 'Bermudas', 'Bermuda'),
    'CY': ('Cyprus', 'Chipre', 'Cyprus'), 'VG': ('BritishVirginIslands', 'Islas Vírgenes Británicas', 'British Virgin Islands'),
    'JE': ('Jersey', 'Jersey', 'Jersey'), 'GG': ('Guernsey', 'Guernsey', 'Guernsey'), 'MC': ('Monaco', 'Mónaco', 'Monaco'),
    'MU': ('Mauritius', 'Mauricio', 'Mauritius'), 'BH': ('Bahrain', 'Baréin', 'Bahrain'), 'OM': ('Oman', 'Omán', 'Oman'),
    'IQ': ('Iraq', 'Irak', 'Iraq'), 'MA': ('Morocco', 'Marruecos', 'Morocco'), 'GH': ('Ghana', 'Ghana', 'Ghana'),
    'ET': ('Ethiopia', 'Etiopía', 'Ethiopia'), 'ZM': ('Zambia', 'Zambia', 'Zambia'), 'CD': ('DRCongo', 'RD Congo', 'DR Congo'),
    'AO': ('Angola', 'Angola', 'Angola'), 'GA': ('Gabon', 'Gabón', 'Gabon'), 'MN': ('Mongolia', 'Mongolia', 'Mongolia'),
    'UZ': ('Uzbekistan', 'Uzbekistán', 'Uzbekistan'), 'BO': ('Bolivia', 'Bolivia', 'Bolivia'), 'VE': ('Venezuela', 'Venezuela', 'Venezuela'),
    'HR': ('Croatia', 'Croacia', 'Croatia'), 'RS': ('Serbia', 'Serbia', 'Serbia'), 'SK': ('Slovakia', 'Eslovaquia', 'Slovakia'),
    'EE': ('Estonia', 'Estonia', 'Estonia'), 'IS': ('Iceland', 'Islandia', 'Iceland'),
}
REGIONS = ('Europa', 'RestoEuropa', 'RestoMundo')
_ISO2 = re.compile(r'^[A-Z]{2}$')


def _countries_mod():
    try:
        from core import countries
        return countries if hasattr(countries, 'iso2_of') else None
    except Exception:  # noqa: BLE001
        return None


def iso2_of(text):
    """Cualquier grafía del catálogo, ISO-2 o nombre ES/EN → ISO-2. 'Europa'/'RestoMundo' → None."""
    if text is None:
        return None
    m = _countries_mod()
    if m is not None:
        return m.iso2_of(text)
    s = str(text).strip()
    if not s or s in REGIONS:
        return None
    if _ISO2.match(s) and s in _FALLBACK:
        return s
    key = None
    try:
        from core import world
        key = world.country_key(s)
    except Exception:  # noqa: BLE001
        key = None
    if key is None and s in {v[0] for v in _FALLBACK.values()}:
        key = s
    if key is None or key in REGIONS:
        return None
    for iso, (ck, _es, _en) in _FALLBACK.items():
        if ck == key:
            return iso
    if key == 'Japan':
        return 'JP'
    return None


def region_of(text):
    """'Europa' | 'RestoEuropa' | 'RestoMundo' | None (cuando el texto no es un país real)."""
    m = _countries_mod()
    if m is not None and hasattr(m, 'region_of'):
        return m.region_of(text)
    s = str(text or '').strip()
    if s in REGIONS:
        return s
    try:
        from core import world
        k = world.country_key(s)
    except Exception:  # noqa: BLE001
        k = None
    return k if k in REGIONS else None


def catalog_key_of(iso2):
    """ISO-2 → clave del catálogo de hoy ('US' → 'EEUU'); desconocido → nombre en inglés."""
    m = _countries_mod()
    if m is not None and hasattr(m, 'catalog_key_of'):
        return m.catalog_key_of(iso2)
    ent = _FALLBACK.get(str(iso2 or '').upper())
    return ent[0] if ent else str(iso2 or '')


def country_label(iso2, lang='es'):
    m = _countries_mod()
    if m is not None and hasattr(m, 'label'):
        return m.label(iso2, lang)
    ent = _FALLBACK.get(str(iso2 or '').upper())
    if not ent:
        return str(iso2 or '')
    return ent[2] if lang == 'en' else ent[1]


# ── bolsas: MIC → sufijo de Yahoo ────────────────────────────────────────────────────────────────────────────────
# Las que core/instruments.SUFFIX conoce (sufijo → bolsa) más las que ese módulo no lista. Fuente: pares
# (bolsa_mic, simbolo_yahoo) del lote 2026-10-14 y la convención pública de Yahoo. '' = sin sufijo (EE.UU./OTC).
MIC_SUFFIX = {
    'XNAS': '', 'XNYS': '', 'ARCX': '', 'XASE': '', 'BATS': '', 'OTCM': '', 'XNGS': '', 'XNMS': '', 'XNCM': '',
    'XTKS': 'T', 'XJPX': 'T', 'XOSE': 'T', 'XHKG': 'HK', 'XASX': 'AX', 'XSHG': 'SS', 'XSHE': 'SZ', 'XTAI': 'TW',
    'ROCO': 'TWO', 'XKRX': 'KS', 'XKOS': 'KQ', 'XETR': 'DE', 'XFRA': 'F', 'XSTU': 'SG', 'XBER': 'BE', 'XDUS': 'DU',
    'XHAM': 'HM', 'XHAN': 'HA', 'XMUN': 'MU', 'XLON': 'L', 'XPAR': 'PA', 'XAMS': 'AS', 'XBRU': 'BR', 'XMIL': 'MI',
    'XMAD': 'MC', 'XLIS': 'LS', 'XHEL': 'HE', 'XDUB': 'IR', 'XWBO': 'VI', 'XSTO': 'ST', 'XCSE': 'CO', 'XOSL': 'OL',
    'XSWX': 'SW', 'XWAR': 'WA', 'MISX': 'ME', 'XNSE': 'NS', 'XBOM': 'BO', 'XSES': 'SI', 'XIDX': 'JK', 'DSMD': 'QA',
    'XSAU': 'SR', 'XTAE': 'TA', 'XJSE': 'JO', 'XNZE': 'NZ', 'XTSE': 'TO', 'XTSX': 'V', 'NEOE': 'NE', 'XCNQ': 'CN',
    'XMEX': 'MX', 'BVMF': 'SA', 'XKLS': 'KL', 'XBKK': 'BK', 'XSGO': 'SN', 'XIST': 'IS', 'XBUE': 'BA', 'XLIM': 'LM',
    'XBOG': 'CL', 'ASEX': 'AT', 'XPRA': 'PR', 'XBUD': 'BD', 'XLIT': 'VS', 'XDFM': 'AE', 'XADS': 'AD', 'XICE': 'IC',
    'XRIS': 'RG', 'XTAL': 'TL', 'XZAG': 'ZA', 'XBSE': 'RO', 'XLJU': 'LJ', 'XKAR': 'KA', 'XCAI': 'CA', 'XCAS': 'CS',
    'XTUN': 'TN', 'XNAI': 'NR', 'XLUX': 'LU', 'XMAL': 'MT', 'XCYS': 'CY',
}


def suffix_of_mic(mic):
    """MIC → sufijo de Yahoo ('XSHE' → 'SZ'; EE.UU. → ''); desconocido → None."""
    return MIC_SUFFIX.get(str(mic or '').strip().upper())


def exchange_label(mic):
    """Nombre de la bolsa como lo conoce core/instruments (por el sufijo); sin dato → el MIC."""
    suf = suffix_of_mic(mic)
    if suf is None:
        return str(mic or '')
    try:
        from core.instruments import SUFFIX
        ent = SUFFIX.get(suf)
        return ent[0] if ent and ent[0] else str(mic or '')
    except Exception:  # noqa: BLE001
        return str(mic or '')


def yahoo_symbol_for(ticker, mic):
    """Símbolo de Yahoo esperado para (ticker, MIC): 'TSM'+'XNYS' → 'TSM'; '2330'+'XTAI' → '2330.TW'.
    Yahoo escribe el punto de las clases como guion (BRK.B → BRK-B). None si el MIC es desconocido."""
    suf = suffix_of_mic(mic)
    t = str(ticker or '').strip().upper()
    if suf is None or not t:
        return None
    if suf == '':
        return t.replace('.', '-')
    return f'{t}.{suf}'


def yahoo_matches_mic(yahoo_symbol, mic):
    """¿El sufijo del símbolo de Yahoo corresponde al MIC declarado? None si el MIC es desconocido."""
    suf = suffix_of_mic(mic)
    if suf is None:
        return None
    s = str(yahoo_symbol or '').strip().upper()
    got = s.rsplit('.', 1)[1] if '.' in s else ''
    return got == suf


# moneda de cotización de las bolsas que core/instruments.SUFFIX no lista (ISO 4217)
MIC_CURRENCY = {
    'OTCM': 'USD', 'XASE': 'USD', 'ARCX': 'USD', 'BATS': 'USD', 'XNGS': 'USD', 'XNMS': 'USD', 'XNCM': 'USD',
    'XTKS': 'JPY', 'XJPX': 'JPY', 'XOSE': 'JPY', 'XSTU': 'EUR', 'XBER': 'EUR', 'XDUS': 'EUR', 'XHAM': 'EUR', 'XHAN': 'EUR',
    'XMUN': 'EUR', 'XFRA': 'EUR', 'XKLS': 'MYR', 'XBKK': 'THB', 'XSGO': 'CLP', 'XIST': 'TRY', 'XBUE': 'ARS', 'XLIM': 'PEN',
    'XBOG': 'COP', 'ASEX': 'EUR', 'XPRA': 'CZK', 'XBUD': 'HUF', 'XLIT': 'EUR', 'XDFM': 'AED', 'XADS': 'AED', 'XICE': 'ISK',
    'XRIS': 'EUR', 'XTAL': 'EUR', 'XZAG': 'EUR', 'XBSE': 'RON', 'XLJU': 'EUR', 'XKAR': 'PKR', 'XCAI': 'EGP', 'XCAS': 'MAD',
    'XTUN': 'TND', 'XNAI': 'KES', 'XLUX': 'EUR', 'XMAL': 'EUR', 'XCYS': 'EUR', 'XCNQ': 'CAD', 'NEOE': 'CAD',
}


def currency_of_mic(mic):
    """Moneda en que Yahoo da el precio para esa bolsa (core/instruments.SUFFIX o MIC_CURRENCY); None si no se sabe.
    Subunidades (GBp, ZAc, ILA) se devuelven como la moneda mayor (GBP, ZAR, ILS)."""
    m = str(mic or '').strip().upper()
    suf = suffix_of_mic(m)
    if suf is None:
        return None
    try:
        from core.instruments import MINOR_UNITS, SUFFIX
        ent = SUFFIX.get(suf)
        ccy = ent[1] if ent else None
        if ccy in MINOR_UNITS:
            ccy = MINOR_UNITS[ccy][0]
    except Exception:  # noqa: BLE001
        ccy = None
    return ccy or MIC_CURRENCY.get(m)


# ── fechas parciales ─────────────────────────────────────────────────────────────────────────────────────────────
_PARTIAL = re.compile(r'^(19|20)[0-9]{2}(-(0[1-9]|1[0-2])(-(0[1-9]|[12][0-9]|3[01]))?)?$')
# esquema 2.0.0: años 1000-2099 (empresas fundadas en 1867, vínculos que empiezan antes de 1900)
_PARTIAL_WIDE = re.compile(r'^(1[0-9]|20)[0-9]{2}(-(0[1-9]|1[0-2])(-(0[1-9]|[12][0-9]|3[01]))?)?$')


def partial_date(text, wide=False):
    """'2021' | '2021-07' | '2021-07-15' → (inicio, fin_exclusivo, precisión) en UTC. El día nunca se inventa: la
    precisión dice cuánto se sabe ('year' | 'month' | 'day'). None si no es una fecha parcial válida. Por omisión
    solo 1900-2099 (como siempre); `wide=True` acepta 1000-2099 (el patrón del esquema 2.0.0)."""
    s = str(text or '').strip()
    if not (_PARTIAL_WIDE if wide else _PARTIAL).match(s):
        return None
    parts = s.split('-')
    y = int(parts[0])
    if len(parts) == 1:
        return (datetime(y, 1, 1, tzinfo=timezone.utc), datetime(y + 1, 1, 1, tzinfo=timezone.utc), 'year')
    m = int(parts[1])
    if len(parts) == 2:
        ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
        return (datetime(y, m, 1, tzinfo=timezone.utc), datetime(ny, nm, 1, tzinfo=timezone.utc), 'month')
    d = int(parts[2])
    if d > calendar.monthrange(y, m)[1]:
        return None
    start = datetime(y, m, d, tzinfo=timezone.utc)
    nd = d + 1
    if nd > calendar.monthrange(y, m)[1]:
        ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
        end = datetime(ny, nm, 1, tzinfo=timezone.utc)
    else:
        end = datetime(y, m, nd, tzinfo=timezone.utc)
    return (start, end, 'day')


def valid_from_of(start_text):
    """`start` de un vínculo → (valid_from ISO, valid_from_known). Sin start → el centinela GENESIS (2000-01-01,
    "desde que se rastrea") con known=False; NUNCA "ahora" (D-3)."""
    p = partial_date(start_text, wide=True) if start_text else None
    if p is None:
        from ontology.service import GENESIS_SENTINEL
        return GENESIS_SENTINEL, False
    return p[0].isoformat(), True


def valid_to_of(end_text):
    """`end` → valid_to = primer instante DESPUÉS del período conocido ('2021-07' → 2021-08-01). None sin end."""
    p = partial_date(end_text, wide=True) if end_text else None
    return p[1].isoformat() if p else None


# ── dinero ───────────────────────────────────────────────────────────────────────────────────────────────────────
_CCY = re.compile(r'^[A-Z]{3}$')


def money(fact):
    """f_money → {value (unidades), currency, period, as_of, source_url, confidence}. La conversión a USD la hace
    el servidor con fx_daily del as_of (nunca aquí). None si no es un hecho de dinero válido."""
    if not isinstance(fact, dict):
        return None
    try:
        v = float(fact.get('value'))
    except (TypeError, ValueError):
        return None
    ccy = str(fact.get('currency') or '').upper()
    if not _CCY.match(ccy):
        return None
    return {'value': v, 'currency': ccy, 'period': fact.get('period'), 'as_of': fact.get('as_of'),
            'source_url': fact.get('source_url'), 'confidence': fact.get('confidence')}


def pct(value):
    """Porcentaje 0-100 de la ficha → fracción 0-1 que usa el catálogo (margin). None si no es número."""
    try:
        return round(float(value) / 100.0, 6)
    except (TypeError, ValueError):
        return None


# ── ids ──────────────────────────────────────────────────────────────────────────────────────────────────────────
_KHIPUS_ID = re.compile(r'^[A-Za-z][A-Za-z0-9_]{1,79}$')


def ascii_fold(s):
    s = unicodedata.normalize('NFKD', str(s or ''))
    return ''.join(c for c in s if not unicodedata.combining(c))


_LATIN_SPECIAL = str.maketrans({'Ø': 'O', 'ø': 'o', 'Æ': 'AE', 'æ': 'ae', 'Œ': 'OE', 'œ': 'oe', 'ß': 'ss', 'Ł': 'L',
                                'ł': 'l', 'Đ': 'D', 'đ': 'd', 'Þ': 'Th', 'þ': 'th', 'Ŋ': 'N', 'ŋ': 'n', 'ı': 'i'})


def khipus_id_from(name):
    """'LG Energy Solution' → 'LGEnergySolution'; '3M' → 'Co3M'; 'Ørsted' → 'Orsted' (Ø/Æ/ß/Ł no se descomponen con
    NFKD: tabla propia); '宁德时代' → 'CoXXXX' (sin letras latinas: hash)."""
    base = ascii_fold(str(name or '').translate(_LATIN_SPECIAL))
    words = re.split(r'[^A-Za-z0-9]+', base)
    out = ''.join(w[:1].upper() + w[1:] for w in words if w)
    if not out:
        import hashlib
        out = 'Co' + hashlib.sha1(str(name).encode('utf-8')).hexdigest()[:8]
    if not out[0].isalpha():
        out = 'Co' + out
    out = out[:80]
    if not _KHIPUS_ID.match(out):
        out = 'Co' + re.sub(r'[^A-Za-z0-9_]', '', out)[:78] or 'CoX'
    return out


def is_khipus_id(s):
    return bool(_KHIPUS_ID.match(str(s or '')))


# ── SANEADOR de fichas (lote L, 2026-10-15): solo FORMATO, con registro de cada cambio ───────────────────────────
# Reglas (cada cambio deja {path, rule, action, before, after} en el registro; `path` en las coordenadas de la ficha
# ORIGINAL; nada se inventa: un valor que no se puede reparar se QUITA —solo ese campo— y queda en el registro):
#   url_trim / url_percent_encode   espacios en los extremos fuera; espacios y corchetes de ruta/consulta → %20 %5B %5D
#   fiscal_year_text_to_int         "2025" → 2025 (también "FY2025")
#   fiscal_year_split_end           "2025/26" → 2026: un ejercicio partido se nombra por el año en que TERMINA
#   period_fy_split_end             "FY2025/26" → "FY2026" (misma regla); "FY 2025" → "FY2025"
#   ticker_space_to_dash            "ERIC B" → "ERIC-B" (la clase de acción con guion, como Yahoo)
#   counterparty_id_to_hint         counterparty.khipus_id que no cumple el patrón de ids NUEVOS ("lockheed-martin",
#                                   "50Hertz") → counterparty.id_hint (el resolvedor lo usa si existe en el grafo)
#   listing_mic_from_yahoo          sufijo de Yahoo con UNA sola bolsa posible → exchange_mic (".CO" → XCSE)
#   listing_ticker_from_yahoo       símbolo de Yahoo cuyo sufijo es el de la bolsa → ticker ("ABC.BA" en XBUE → ABC)
#   listing_ticker_conflict         un CERTIFICADO (adr/gdr/cedear/bdr) sin ticker cuyo símbolo de Yahoo no es ninguno de
#                                   los tickers que la MISMA ficha declara se quita entero (Boeing traía «BAC.BA», el
#                                   CEDEAR de Bank of America: derivar BAC lo habría hecho pasar por bueno)
#   listing_yahoo_from_ticker_mic   ticker + MIC → símbolo de Yahoo (MIC_SUFFIX; GDR en Londres → ".IL", la convención
#                                   de core/instruments.SUFFIX)
#   listing_currency_from_yahoo     sufijo de Yahoo → moneda (core/instruments.SUFFIX; GBp → GBP); sin sufijo
#                                   conocido y sin certificado: la moneda de la bolsa (currency_of_mic)
#   listing_kind_home_exchange      sin `kind` y la bolsa es la del país de la sede → equity / a_share / h_share / otc
#   drop_forbidden_live_field       un dato EN VIVO (price, market_cap…) se quita: lo trae el servidor
#   drop_unknown_field / drop_invalid  lo que sigue sin cumplir el esquema se quita: el campo opcional o el elemento de
#                                   lista MÁS PEQUEÑO que lo contiene
#   reject                          solo si la IDENTIDAD queda inservible (identity, research_meta, classification,
#                                   profile, record_id): la ficha no entra
SANITIZE_RULES = ('url_trim', 'url_percent_encode', 'fiscal_year_text_to_int', 'fiscal_year_split_end',
                  'period_fy_split_end', 'ticker_space_to_dash', 'counterparty_id_to_hint', 'listing_mic_from_yahoo',
                  'listing_ticker_from_yahoo', 'listing_ticker_conflict', 'listing_yahoo_from_ticker_mic',
                  'listing_currency_from_yahoo',
                  'listing_kind_home_exchange', 'drop_forbidden_live_field', 'drop_unknown_field', 'drop_invalid',
                  'reject')
_URL_KEYS = ('source_url', 'website', 'ir_url')
_URL_LIST_KEYS = ('sources_consulted', 'rss_urls')
_URL_FMT = re.compile(r'^https?://[^\s/]+\.[^\s]+$')
_TICKER_FMT = re.compile(r'^[A-Z0-9][A-Z0-9.\-]{0,14}$')
_YAHOO_FMT = re.compile(r'^[A-Z0-9^][A-Z0-9.=\-^]{0,19}$')
_ID_HINT_FMT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.&()'\-]{0,79}$")
_CP_DICT_KEYS = ('counterparty', 'entity', 'successor', 'merged_into')
_CP_LIST_KEYS = ('lead_investors', 'other_investors')
_PROTECTED_TOP = ('schema', 'record_id', 'research_meta', 'identity', 'classification', 'profile')
_FY_ONE = re.compile(r'^\s*(?:FY\s*)?([12][0-9]{3})\s*$')
_FY_SPLIT = re.compile(r'^\s*(FY)?\s*([12][0-9]{3})\s*[/\-–]\s*([0-9]{2}|[12][0-9]{3})\s*$')
_FY_SPACE = re.compile(r'^FY\s+([12][0-9]{3})$')
_SANITIZE_MAX_DROPS = 400


def _p_key(path, key):
    return f'{path}.{key}' if path else str(key)


def _p_idx(path, i):
    return f'{path}[{i}]'


def _log(log, path, rule, action, before, after=None, **extra):
    ent = {'path': path or '(raíz)', 'rule': rule, 'action': action, 'before': before}
    if action != 'drop' and action != 'reject':
        ent['after'] = after
    ent.update(extra)
    log.append(ent)


def encode_url(url):
    """Repara el FORMATO de un enlace: quita espacios de los extremos y codifica los espacios internos y los corchetes
    de la ruta/consulta (%20, %5B, %5D; otros espacios Unicode en UTF-8). El servidor (host) no se toca; '%' existentes
    no se recodifican → idempotente."""
    from urllib.parse import quote
    s = str(url).strip()
    m = re.match(r'^([A-Za-z][A-Za-z0-9+.\-]*://[^/?#\s]*)(.*)$', s)
    head, tail = (m.group(1), m.group(2)) if m else ('', s)
    out = []
    for ch in tail:
        if ch.isspace():
            out.append(quote(ch, safe=''))
        elif ch == '[':
            out.append('%5B')
        elif ch == ']':
            out.append('%5D')
        else:
            out.append(ch)
    return head + ''.join(out)


def _fiscal_year_of(text):
    """(año, regla) de un fiscal_year escrito como texto; None si no se puede leer sin adivinar."""
    s = str(text)
    m = _FY_ONE.match(s)
    if m:
        return int(m.group(1)), 'fiscal_year_text_to_int'
    m = _FY_SPLIT.match(s)
    if m:
        start, end = int(m.group(2)), m.group(3)
        end_y = int(end) if len(end) == 4 else (start // 100) * 100 + int(end)
        if len(end) == 2 and end_y < start:
            end_y += 100
        if end_y == start + 1:                 # solo un ejercicio de 12 meses partido en dos años calendario
            return end_y, 'fiscal_year_split_end'
    return None


def _period_fixed(text):
    """(período, regla) para 'FY2025/26' → 'FY2026' y 'FY 2025' → 'FY2025'; None si no aplica."""
    s = str(text)
    m = _FY_SPLIT.match(s)
    if m and m.group(1):
        fy = _fiscal_year_of(s)
        if fy is not None:
            return f'FY{fy[0]}', 'period_fy_split_end'
    m = _FY_SPACE.match(s.strip())
    if m and s != f'FY{m.group(1)}':
        return f'FY{m.group(1)}', 'period_fy_split_end'
    return None


def _ticker_fixed(t):
    if not isinstance(t, str):
        return None
    s = re.sub(r'\s+', '-', t.strip()).upper()
    return s if s != t and _TICKER_FMT.match(s) else None


def _suffix_mics(suffix):
    """Bolsas (MIC) cuyo sufijo de Yahoo es `suffix` ('IL' = Londres IOB → XLON)."""
    if suffix == 'IL':
        return ['XLON']
    return sorted(m for m, sf in MIC_SUFFIX.items() if sf == suffix)


def _yahoo_suffix(ys):
    s = str(ys or '').strip().upper()
    return s.rsplit('.', 1)[1] if '.' in s else ''


def _currency_of_suffix(suffix):
    try:
        from core.instruments import MINOR_UNITS, SUFFIX
    except Exception:  # noqa: BLE001
        return None
    ent = SUFFIX.get(suffix)
    if not ent or not ent[1]:
        return None
    ccy = ent[1]
    return MINOR_UNITS[ccy][0] if ccy in MINOR_UNITS else ccy


_CERT_KINDS = ('adr', 'gdr', 'cedear', 'bdr')


def _declared_tickers(listings):
    """Tickers que la ficha DECLARA (antes de derivar nada), en mayúsculas."""
    return {l['ticker'].strip().upper() for l in listings if isinstance(l, dict) and isinstance(l.get('ticker'), str)
            and l['ticker'].strip()}


def _sanitize_listing(l, hq, path, log, own_tickers=None):
    """Deriva lo que falta de UNA cotización a partir de sus otros campos (nunca de fuera de la ficha). Devuelve
    'ticker_conflict' si es un certificado sin ticker cuyo símbolo de Yahoo no corresponde a ningún ticker de la ficha
    (quien llama la quita entera, con registro)."""
    if not isinstance(l, dict):
        return None
    mic = l.get('exchange_mic') if isinstance(l.get('exchange_mic'), str) else None
    ys = l.get('yahoo_symbol') if isinstance(l.get('yahoo_symbol'), str) else None
    if own_tickers and l.get('kind') in _CERT_KINDS and ys and not (isinstance(l.get('ticker'), str) and l['ticker'].strip()):
        suf = _yahoo_suffix(ys)
        base = ys.strip().upper().rsplit('.', 1)[0] if suf else ys.strip().upper()
        if base not in own_tickers:
            return 'ticker_conflict'
    if not mic and ys:
        suf = _yahoo_suffix(ys)
        mics = _suffix_mics(suf) if suf else []
        if len(mics) == 1:
            l['exchange_mic'] = mic = mics[0]
            _log(log, _p_key(path, 'exchange_mic'), 'listing_mic_from_yahoo', 'derive', None, mic, source=ys)
    t = l.get('ticker') if isinstance(l.get('ticker'), str) else None
    if not t and ys and mic:
        suf = _yahoo_suffix(ys)
        ok = yahoo_matches_mic(ys, mic) or (suf == 'IL' and mic == 'XLON')
        base = ys.strip().upper().rsplit('.', 1)[0] if suf else ys.strip().upper()
        if ok and _TICKER_FMT.match(base):
            l['ticker'] = t = base
            _log(log, _p_key(path, 'ticker'), 'listing_ticker_from_yahoo', 'derive', None, t, source=ys)
    if not ys and t and mic and _TICKER_FMT.match(t):
        if l.get('kind') == 'gdr' and mic == 'XLON':
            cand = f'{t.upper()}.IL'                       # GDR en la LSE (IOB): core/instruments.SUFFIX['IL']
        else:
            cand = yahoo_symbol_for(t, mic)
        if cand and _YAHOO_FMT.match(cand):
            l['yahoo_symbol'] = ys = cand
            _log(log, _p_key(path, 'yahoo_symbol'), 'listing_yahoo_from_ticker_mic', 'derive', None, cand,
                 source=f'{t}@{mic}' + (' (gdr)' if l.get('kind') == 'gdr' else ''))
    if not l.get('currency'):
        ccy = None
        if ys and _yahoo_suffix(ys):
            ccy = _currency_of_suffix(_yahoo_suffix(ys))
        if ccy is None and mic and l.get('kind') not in ('adr', 'gdr'):
            ccy = currency_of_mic(mic)
        if ccy:
            l['currency'] = ccy
            _log(log, _p_key(path, 'currency'), 'listing_currency_from_yahoo', 'derive', None, ccy, source=ys or mic)
    if not l.get('kind') and mic and hq:
        try:
            from ontology.company_import import MIC_COUNTRY, _listing_kind
        except Exception:  # noqa: BLE001
            MIC_COUNTRY, _listing_kind = {}, None
        home = MIC_COUNTRY.get(mic) == hq or (hq == 'CN' and mic == 'XHKG')
        if _listing_kind is not None and home:
            kind = _listing_kind(mic, hq, None)
            l['kind'] = kind
            _log(log, _p_key(path, 'kind'), 'listing_kind_home_exchange', 'derive', None, kind, source=f'{mic}/{hq}')


def _sanitize_counterparty(cp, path, log):
    if not isinstance(cp, dict):
        return
    k = cp.get('khipus_id')
    if isinstance(k, str) and not is_khipus_id(k):
        cp.pop('khipus_id')
        if _ID_HINT_FMT.match(k.strip()) and not cp.get('id_hint'):
            cp['id_hint'] = k.strip()
            _log(log, _p_key(path, 'khipus_id'), 'counterparty_id_to_hint', 'move', k, k.strip(),
                 to=_p_key(path, 'id_hint'))
        else:
            _log(log, _p_key(path, 'khipus_id'), 'counterparty_id_to_hint', 'drop', k,
                 reason='ni id nuevo ni id del grafo / neither a new id nor a graph id')


def _repair(node, path, key, log):
    """Recorre la ficha y aplica las reparaciones de FORMATO en su lugar (sin quitar nada). `key` = la clave bajo la
    que cuelga este nodo (para un elemento de lista, la clave de la lista)."""
    if isinstance(node, dict):
        if key in _CP_DICT_KEYS or key in _CP_LIST_KEYS:
            _sanitize_counterparty(node, path, log)
        for k in list(node.keys()):
            v = node[k]
            p = _p_key(path, k)
            if k in _URL_KEYS and isinstance(v, str):
                fixed = encode_url(v)
                if fixed != v:
                    rule = 'url_trim' if fixed == v.strip() else 'url_percent_encode'
                    _log(log, p, rule, 'repair', v, fixed)
                    node[k] = fixed
            elif k in _URL_LIST_KEYS and isinstance(v, list):
                for i, u in enumerate(v):
                    if isinstance(u, str):
                        fixed = encode_url(u)
                        if fixed != u:
                            rule = 'url_trim' if fixed == u.strip() else 'url_percent_encode'
                            _log(log, _p_idx(p, i), rule, 'repair', u, fixed)
                            v[i] = fixed
            elif k == 'fiscal_year' and isinstance(v, str):
                got = _fiscal_year_of(v)
                if got is not None:
                    _log(log, p, got[1], 'repair', v, got[0])
                    node[k] = got[0]
            elif k == 'period' and isinstance(v, str):
                got = _period_fixed(v)
                if got is not None:
                    _log(log, p, got[1], 'repair', v, got[0])
                    node[k] = got[0]
            elif k == 'ticker' and isinstance(v, str) and key in ('ids', 'listings'):
                fixed = _ticker_fixed(v)
                if fixed:
                    _log(log, p, 'ticker_space_to_dash', 'repair', v, fixed)
                    node[k] = fixed
            if isinstance(node.get(k), (dict, list)):
                _repair(node[k], p, k, log)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            if isinstance(v, (dict, list)):
                _repair(v, _p_idx(path, i), key, log)


# ── fase de quitar lo irreparable: guiada por el validador (ontology/company_schema) ──────────────────────────────
def _field_info(cls, name):
    if cls is None:
        return None
    fields = getattr(cls, 'model_fields', None) or {}
    if name in fields:
        return fields[name]
    for fname, fi in fields.items():
        if fi.alias == name:
            return fi
    return None


def _inner_model(ann):
    """Tipo de un campo → (modelo Pydantic | None, es_lista)."""
    import typing
    from pydantic import BaseModel
    is_list = False
    for _ in range(6):
        origin = typing.get_origin(ann)
        if origin is typing.Annotated:
            ann = typing.get_args(ann)[0]
            continue
        if origin in (list, typing.List):
            is_list = True
            ann = typing.get_args(ann)[0]
            continue
        if origin is typing.Union:
            args = [a for a in typing.get_args(ann) if a is not type(None)]
            ann = args[0] if args else ann
            continue
        break
    try:
        return (ann if isinstance(ann, type) and issubclass(ann, BaseModel) else None), is_list
    except TypeError:
        return None, is_list


def _drop_target(loc, err_type):
    """loc de un error → índice (en loc) del nodo MÁS PEQUEÑO que se puede quitar: un campo opcional o un elemento
    de lista. None = la identidad no se puede salvar (habría que quitar la raíz o una parte obligatoria de arriba)."""
    from ontology.company_schema import CompanyRecord
    steps = []          # (paso_en_loc, quitable)
    cls = CompanyRecord
    list_cls = None
    for n, part in enumerate(loc):
        if isinstance(part, int):
            steps.append((n, True))
            cls, list_cls = list_cls, None
            continue
        fi = _field_info(cls, part)
        if fi is None:          # campo desconocido (extra_forbidden) o dentro de un valor libre
            steps.append((n, True))
            cls = None
            continue
        steps.append((n, not fi.is_required()))
        inner, is_list = _inner_model(fi.annotation)
        if is_list:
            list_cls, cls = inner, None
        else:
            cls = inner
    # un campo que FALTA no existe: se empieza por su padre
    usable = steps[:-1] if err_type == 'missing' else steps
    for n, droppable in reversed(usable):
        if not droppable:
            continue
        if n == 0 and str(loc[0]) in _PROTECTED_TOP:
            return None
        return n
    return None


def _orig_paths(rec):
    """id(contenedor) → ruta ORIGINAL; id(lista) → índices originales de sus elementos (se actualizan al quitar)."""
    paths, idxs = {id(rec): ''}, {}

    def walk(x, p):
        if isinstance(x, dict):
            for k, v in x.items():
                if isinstance(v, (dict, list)):
                    paths[id(v)] = _p_key(p, k)
                    walk(v, _p_key(p, k))
        elif isinstance(x, list):
            idxs[id(x)] = list(range(len(x)))
            for i, v in enumerate(x):
                if isinstance(v, (dict, list)):
                    paths[id(v)] = _p_idx(p, i)
                    walk(v, _p_idx(p, i))
    walk(rec, '')
    return paths, idxs


def _drop_order_key(k):
    """Orden total de rutas de error: mismo tipo por posición (números como números, textos como textos)."""
    return [(0, p, '') if isinstance(p, int) else (1, 0, str(p)) for p in k]


def _drop_invalid(rec, log):
    """Valida; quita el nodo quitable más pequeño de cada error; repite. (rec, rechazada?)."""
    import json as _json
    from pydantic import ValidationError
    from ontology.company_schema import FORBIDDEN_KEYS, CompanyRecord
    paths, idxs = _orig_paths(rec)
    dropped = 0
    while True:
        try:
            CompanyRecord.model_validate_json(_json.dumps(rec, ensure_ascii=False, default=str))
            return rec, False
        except ValidationError as e:
            errs = e.errors(include_url=False)
        targets = {}
        for x in errs:
            loc = tuple(x.get('loc') or ())
            n = _drop_target(loc, x.get('type'))
            if n is None:
                _log(log, '.'.join(str(p) for p in loc) or '(raíz)', 'reject', 'reject', None,
                     reason=f"{x.get('type')}: {str(x.get('msg'))[:160]}")
                return rec, True
            key = loc[:n + 1]
            targets.setdefault(key, x)
        # el ancestro manda (quitar un vínculo ya quita su evidencia)
        chosen = []
        for k in sorted(targets, key=lambda k: (len(k), [str(p) for p in k])):
            if not any(k[:len(c)] == c for c in chosen):
                chosen.append(k)
        if not chosen:
            return rec, True
        # quitar de atrás hacia adelante: en una misma lista, el índice MÁS ALTO primero (los pendientes no se mueven);
        # el registro de la ronda queda en el orden de la ficha
        round_log = []
        for k in sorted(chosen, key=_drop_order_key, reverse=True):
            parent = rec
            for part in k[:-1]:
                parent = parent[part]
            last = k[-1]
            x = targets[k]
            et = x.get('type')
            if isinstance(last, int):
                oi = idxs.get(id(parent))
                opath = _p_idx(paths.get(id(parent), '?'), oi[last] if oi and last < len(oi) else last)
                before = parent.pop(last)
                if oi and last < len(oi):
                    oi.pop(last)
            else:
                opath = _p_key(paths.get(id(parent), '?'), last)
                before = parent.pop(last, None)
            if et == 'extra_forbidden' and str(last) in FORBIDDEN_KEYS:
                rule = 'drop_forbidden_live_field'
            elif et == 'extra_forbidden':
                rule = 'drop_unknown_field'
            else:
                rule = 'drop_invalid'
            bad = '.'.join(str(p) for p in (x.get('loc') or ()))
            ent = []
            _log(ent, opath, rule, 'drop', before, reason=f"{et}: {str(x.get('msg'))[:200]}", error_at=bad)
            round_log.append((k, ent[0]))
            dropped += 1
        log.extend(e for _k, e in sorted(round_log, key=lambda t: _drop_order_key(t[0])))
        if dropped > _SANITIZE_MAX_DROPS:
            _log(log, '(raíz)', 'reject', 'reject', None, reason='demasiados campos inválidos / too many invalid fields')
            return rec, True


def sanitize_record(rec):
    """Ficha (dict) → (ficha_saneada, registro). PURA (copia profunda; la entrada no se toca), DETERMINISTA e
    IDEMPOTENTE (sanitize(sanitize(x)) == sanitize(x), registro vacío la segunda vez). Solo cambia el FORMATO (tipos,
    codificación, mayúsculas, espacios y derivaciones desde otros campos de la MISMA ficha); lo irreparable se quita
    (solo ese campo, o el elemento de lista más pequeño que lo contiene) y queda en el registro con su valor. Una ficha
    se rechaza solo si su identidad queda inservible (regla 'reject')."""
    import copy
    log = []
    if not isinstance(rec, dict):
        return rec, [{'path': '(raíz)', 'rule': 'reject', 'action': 'reject', 'before': None,
                      'reason': 'la ficha no es un objeto / the record is not an object'}]
    out = copy.deepcopy(rec)
    _repair(out, '', None, log)
    hq = None
    try:
        hq = out['identity']['hq_country']['value']
    except (KeyError, TypeError):
        hq = None
    lst = out.get('listings') if isinstance(out.get('listings'), list) else []
    own = _declared_tickers(lst)
    bad = []
    for i, l in enumerate(lst):
        if _sanitize_listing(l, hq, _p_idx('listings', i), log, own) == 'ticker_conflict':
            bad.append(i)
    for i in reversed(bad):
        _log(log, _p_idx('listings', i), 'listing_ticker_conflict', 'drop', copy.deepcopy(lst[i]),
             reason=('certificado sin ticker cuyo símbolo de Yahoo no es ningún ticker de la ficha (' +
                     ', '.join(sorted(own)) + ') / certificate without ticker whose Yahoo symbol matches no ticker '
                     'of the record'))
        del lst[i]
    _drop_invalid(out, log)
    return out, log


def sanitize_summary(logs):
    """{regla: n} de uno o varios registros (lista de entradas o lista de listas)."""
    from collections import Counter
    c = Counter()
    for x in logs:
        for e in (x if isinstance(x, list) else [x]):
            c[e.get('rule')] += 1
    return dict(sorted(c.items()))
