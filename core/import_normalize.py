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


def partial_date(text):
    """'2021' | '2021-07' | '2021-07-15' → (inicio, fin_exclusivo, precisión) en UTC. El día nunca se inventa: la
    precisión dice cuánto se sabe ('year' | 'month' | 'day'). None si no es una fecha parcial válida."""
    s = str(text or '').strip()
    if not _PARTIAL.match(s):
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
    p = partial_date(start_text) if start_text else None
    if p is None:
        from ontology.service import GENESIS_SENTINEL
        return GENESIS_SENTINEL, False
    return p[0].isoformat(), True


def valid_to_of(end_text):
    """`end` → valid_to = primer instante DESPUÉS del período conocido ('2021-07' → 2021-08-01). None sin end."""
    p = partial_date(end_text) if end_text else None
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
