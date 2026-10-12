"""core/numbers.py — guardián de CIFRAS (anti-alucinación numérica).

Problema real (2026-09-28): un agente escribió que Broadcom "vale ~$350B"
cuando su capitalización en vivo superaba $1T — el modelo usó su MEMORIA
de entrenamiento, no el paquete de evidencia. Un dato así perjudica la
tesis del inversionista.

Regla: toda cifra que la IA presente como DATO (dinero, precio, porcentaje,
múltiplo, RSI/NRS/beta/P/E…) debe aparecer —con la tolerancia de redondeo de
su tipo— en los datos que recibió. Si no aparece: en investigación la salida
se rechaza y el modelo recibe el error como feedback (research/llm); en toda
otra llamada (core/ai._ai_complete) hay UN reintento con feedback y, si la
cifra persiste, se MARCA "(⚠ cifra no verificada)" / "(⚠ unverified figure)".

Bloque 0 de docs/BRECHAS_V2.md (2026-10-12) — L4-02, L4-M1, L2-04 y la revisión
del guardián:
  · Formatos: "233,95 USD", "233.95 dólares", "USD 233.95", "US$ 1,2 mil
    millones", "5,7 billones de dólares", "€300.000 millones", "S/ 12,50",
    "¥3.000", "MXN 4,500 millones", "1.1T", "350B"… con separadores es/en
    ("1.234,56" = 1234,56; "1,234.56" = 1234,56; "1,500"/"1.500" ambiguos → se
    prueban las dos lecturas).
  · Comparación POR TIPO, nunca contra "cualquier número del prompt":
      dinero/precio  ← números con moneda, escala o rótulo de dinero
                       (price=, precio, close, cap, ingresos, *_usd_b=…)
      porcentaje     ← números con %, o con rótulo de % (change_pct, margen,
                       crecimiento…; una fracción rotulada 0,75 respalda 75 %)
      múltiplo (x)   ← números con x o rótulo P/E, EV/EBITDA, P/FCF…
      RSI/NRS/beta…  ← el número que sigue a ESE mismo rótulo en los datos
    Un número sin rótulo (un peso de arista, un NRS, un conteo) solo respalda
    un precio si coincide a la precisión mostrada y trae decimales o ≥4 cifras.
  · Tolerancias (documentadas, ver _tol):
      precio unitario: máx(0,5 %, media unidad del último dígito mostrado),
                       la media unidad con techo del 2 % (≈ 5 % si dice "~").
      magnitud grande (B/T/millones): máx(1 %, media unidad del último dígito
                       mostrado) con techo del 10 % (15 % con "~"):
                       "5,7 billones" respalda 5,712e12; "$1T" respalda 1,05T.
      porcentaje: máx(media unidad, 0,05 pp, 0,5 % relativo) (10 % con "~").
      múltiplo / indicador: máx(media unidad, 1 %) (10 % con "~").
      "más de X" / "menos de X": X ≤ dato ≤ 2X / X/2 ≤ dato ≤ X.
  · Fuente: SOLO los datos del mensaje (prompt: bloque DATOS EN VIVO,
    resultados de herramientas, evidencia, la pregunta del usuario). El system
    prompt (reglas y ejemplos como «233,95 USD») NO respalda nada.
  · Signo: un dato con signo explícito ("-12 mil millones", "change_pct=-2.1")
    no respalda la misma cifra presentada con el signo contrario ("positivo de
    $12B", "sube 2,1 %").
  · No se marcan: años y fechas, conteos, 0 % y 100 %, niveles de confianza
    ("VaR 95 %"), cifras en frases condicionales/hipotéticas o umbrales
    ("si cae por debajo de…", "podría subir 15 %", "< 60 %"), ni cifras ya
    marcadas con ⚠ (que tampoco respaldan nada si vuelven en el historial).
  · Expresiones regulares lineales: un número no puede empezar en medio de
    otro ((?<![\\w.,])), así un texto de 50.000 dígitos se revisa en ms (antes
    _RATIO_RX era cuadrática y congelaba el único worker).
  · La marca se inserta en el TRAMO exacto de cada cifra (antes un "$20"
    marcado partía "$200" y "$20.5B").
"""
import re
from bisect import bisect_left

# ════════════════════════════════════════════════════════════════════════════
# Piezas de las expresiones
# ════════════════════════════════════════════════════════════════════════════
# Número: 1.234,56 · 1,234.56 · 1.100 · 233,95 · 12.5 · 350. Nunca empieza en medio
# de otro número/palabra y nunca termina antes de un separador+dígito ("12" de "12.5").
_NEND = r'(?![.,]?\d)'
_NUM = (r'(?<![\w.,])(\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?' + _NEND + r'|\d+(?:[.,]\d+)?' + _NEND + r')')
_SIGN = r'(?:(?<![\w)\]])(?P<sg>[-−–+])\s?)?'

# escalas en palabra (el orden importa: "mil millones" antes que "millones" y "mil")
_SCALES = (
    (r'miles?\s+de\s+millones', 1e9), (r'mil\s+millones', 1e9),
    (r'billones|bill[oó]n', 1e12), (r'trillions?|tn', 1e12),
    (r'billions?|bn|bln', 1e9),
    (r'millones|mill[oó]n|millions?|mm|mln', 1e6),
    (r'thousands?|mil', 1e3),
)
_SCALE_WORD = r'(?:' + '|'.join(p for p, _m in _SCALES) + r')(?![\w])'
_GLUED_CUR = r'(?:bn|tn|mm|[TBMK]|[mk])(?![\w])'      # con moneda: $350B, $5m, €2K
_GLUED_BARE = r'(?:bn|tn|[TB])(?![\w])'                # sin moneda: 350B, 1.1T (no "3M", "5G")
_CODES = ('USD|EUR|GBP|JPY|CNY|RMB|TWD|KRW|INR|HKD|CAD|AUD|BRL|MXN|PEN|CHF|SEK|NOK|DKK|SGD|ILS|ZAR|SAR|AED|'
          'CLP|COP|ARS')
_CUR_PRE = (r'(?:US\s?\$|U\$S|NT\$|HK\$|CA?\$|AU?\$|R\$|MX\$|S/\.?|\$|€|£|¥|₩|₹|₽|(?<![A-Za-z])(?:' + _CODES +
            r')(?![A-Za-z]))')
_CUR_WORD = (r'(?:d[oó]lares|dollars?|euros?|yenes|yen|libras(?:\s+esterlinas)?|pounds?|pesos|soles|reales|reais|'
             r'yuanes|yuan|wons?|rupias|rupees?|francos|francs|coronas|' + _CODES + r')(?![A-Za-z])')

_MONEY_PRE = re.compile(
    r'(?:(?<![\w)\]])(?P<sg>[-−–])\s?)?(?<![A-Za-z])' + _CUR_PRE + r'\s?(?P<sg2>[-−–]\s?)?' + _NUM +
    r'(?:\s?(?P<scale>' + _SCALE_WORD + r')|(?P<glued>' + _GLUED_CUR + r'))?'
    r'(?:\s*(?:de\s+)?' + _CUR_WORD + r')?', re.I)
_MONEY_SUF = re.compile(
    _SIGN + _NUM + r'\s?(?:(?P<scale>' + _SCALE_WORD + r')\s*(?:de\s+)?|(?P<glued>' + _GLUED_BARE + r')\s?)?'
    r'(?<![A-Za-z])' + _CUR_WORD + r'(?:\s?(?P<scale2>' + _SCALE_WORD + r'))?', re.I)
_MONEY_GLUED = re.compile(_SIGN + _NUM + r'(?P<glued>' + _GLUED_BARE + r')')
_PCT = re.compile(_SIGN + _NUM + r'\s?(?:%|por\s?ciento|percent(?:age\s+points?)?|pp(?![\w])|p\.\s?p\.|'
                  r'puntos\s+porcentuales)', re.I)
_MULT = re.compile(_SIGN + _NUM + r'\s?(?:x|×)(?![\w])')

# indicadores con rótulo: RSI 82 · NRS de 88 · beta 1,3 · P/E 35 · EV/EBITDA de 20
_SCORE_KEYS = (
    ('rsi', r'RSI'), ('nrs', r'NRS'), ('beta', r'beta'), ('sharpe', r'Sharpe'), ('sortino', r'Sortino'),
    ('pfcf', r'(?:P|precio|price)\s?/\s?FCF|p_fcf'), ('ev_ebitda', r'EV\s?/\s?EBITDA|ev_ebitda'),
    ('peg', r'(?-i:PEG)|peg_ratio'), ('pe', r'P\s?/\s?E|(?-i:PER)|pe_trailing|pe_forward|pe_ratio'),
    ('ps', r'P\s?/\s?S'),
    ('pb', r'P\s?/\s?B'),
)
_MULT_KEYS = {'pfcf', 'ev_ebitda', 'peg', 'pe', 'ps', 'pb'}
_SCORE_RX = re.compile(
    r'(?<![\w/])(?P<key>' + '|'.join(f'(?P<k_{k}>{p})' for k, p in _SCORE_KEYS) + r')(?![\w])'
    r'(?:\s?\(\d{1,3}\))?(?P<gap>[^\d\n.;!?]{0,14}?)' + _SIGN + _NUM + r'(?!\s?(?:%|x(?![\w])|×))', re.I)
_SCORE_SRC = re.compile(r'(?<![a-z/])(' + '|'.join(f'(?P<k_{k}>{p})' for k, p in _SCORE_KEYS) + r')(?![a-z])', re.I)

_DATE_RX = re.compile(r'\b\d{4}-\d{2}-\d{2}(?:[T ][\d:.]+(?:Z|[+-]\d{2}:?\d{2})?)?\b')
_TAGGED_AFTER = re.compile(r'\s?\(⚠')

# contexto ───────────────────────────────────────────────────────────────────
_HYPO = re.compile(
    r'(?:^|[^\w])(?:si|if|cuando|when(?:ever)?|en\s+caso\s+de|unless|a\s+menos\s+que|podr[ií]an?|could|might|'
    r'would|pueden?|pudieran?|p\.\s?ej\.|por\s+ejemplo|e\.g\.|for\s+example|ejemplo|hipot[eé]tic\w*|'
    r'hypothetic\w*|supon\w*|suppos\w*|imagin\w*|umbral|threshold|stop[- ]loss)'
    r'(?![\w])', re.I)
_THRESH_OP = re.compile(r'[<>≤≥]=?\s*$')
_APPROX = re.compile(
    r'(?:~|≈|aprox\.?|aproximadamente|alrededor\s+de|cerca\s+de|unos|unas|en\s+torno\s+a|around|about|roughly|'
    r'approximately|approx\.?|nearly|almost|casi|some)\s*(?:de\s+|del\s+)?(?:los\s+|las\s+|el\s+|la\s+)?$', re.I)
_GT = re.compile(r'(?:m[aá]s\s+de|over|more\s+than|above|superior\s+a|supera(?:r|ndo)?|exceed(?:s|ing)?|'
                 r'al\s+menos|at\s+least|por\s+encima\s+de)\s*(?:los\s+|las\s+|el\s+|la\s+)?$', re.I)
_LT = re.compile(r'(?:menos\s+de|under|less\s+than|below|inferior\s+a|por\s+debajo\s+de|hasta|up\s+to)\s*'
                 r'(?:los\s+|las\s+|el\s+|la\s+)?$', re.I)
_CONF_BEFORE = re.compile(r'(?<![\w])(?:VaR|CVaR|confianza|confidence|IC|CI)\s*(?:del?|al|at|of)?\s*$', re.I)
_CONF_AFTER = re.compile(r'^\s*(?:de\s+confianza|confidence|VaR|CVaR)', re.I)
_NEG = re.compile(
    r'(?<![\w])(?:ca[yí]ó|caen?|ca[ií]da|baj[óo]|bajan?|bajada|perdi[óo]|pierden?|p[ée]rdidas?|negativ[oa]s?|'
    r'd[ée]ficit|retroce\w*|descen\w*|desplom\w*|hundi\w*|fell|falls?|drop(?:ped|s)?|declin\w*|loss(?:es)?|'
    r'lost|negative|deficit|down|lower|plunge\w*|slump\w*)(?![\w])', re.I)
_POS = re.compile(
    r'(?<![\w])(?:subi[óo]|suben?|alza|gan[óo]|ganan?|ganancias?|positiv[oa]s?|super[áa]vit|creci[óo]|crecen?|'
    r'aument\w*|rose|rises?|rising|risen|gain(?:ed|s)?|profit\w*|positive|surplus|grew|up|higher|jump\w*|'
    r'rall\w*|climb\w*|increas\w*)(?![\w])', re.I)
_AFTER_NEG = re.compile(r'^\W{0,3}(?:a\s+la\s+baja|lower|down)(?![\w])', re.I)
_AFTER_POS = re.compile(r'^\W{0,3}(?:al\s+alza|higher|up)(?![\w])', re.I)

# rótulos de los DATOS (ventana antes del número, en minúsculas)
_MONEY_HINT = re.compile(
    r'(?:price|precio|(?<![a-z])px|close|cierre|prev|open|high|(?<![a-z])low|cotiza|valor|value|(?<![a-z])cap|valuaci|'
    r'valuation|revenue|ingres|ventas|sales|deuda|debt|cash|caja|efectivo|fcf|flujo|(?<![a-z])eps|bpa|dividend|ebitda|income|beneficio|ganancia|'
    r'utilidad|target|objetivo|usd|eur|monto|amount|notional|equity|patrimonio|costo|cost|var95|var_|p&l|pnl|'
    r'p[eé]rdida|loss|profit|compr|vend|bought|sold|invert|invest|pag[oó]|paid|saldo|balance|buying_power|'
    r'week52|52w|ronda|(?<![a-z])round|recaud|raised)', re.I)
_PCT_HINT = re.compile(
    r'(?:pct|percent|porcentaje|margin|margen|growth|crecim|change|cambio|variaci|yield|rendim|retorno|return|'
    r'(?<![a-z])(?:roe|roic|peso|share|cuota|tasa|rate|prob)|drawdown|ca[ií]da|volatil|vol_|weight|'
    r'(?<![a-z])dp(?![a-z])|chg|upside|downside|impact|aporte|contrib)', re.I)
_MULT_HINT = re.compile(r'(?:(?<![a-z])p/?e(?![a-z])|(?<![a-z])per(?![a-z])|pe_|ev/?_?ebitda|ev_to|p/?_?fcf|'
                        r'm[uú]ltiplo|multiple|deuda/ebitda|debt_to|debt/|price_to|p/s|p/b|peg)', re.I)
_B_KEY = re.compile(r'(?:_b|_bn|_usd_b|_billions?)["\']?\s*[:=]\s*["\']?$', re.I)
_M_KEY = re.compile(r'(?:_usd_m|_m_usd|_mm|_millions?)["\']?\s*[:=]\s*["\']?$', re.I)
_HEADER_SCALE = (
    (re.compile(r'\([^)\n]*(?:miles\s+de\s+millones|mil\s+millones|billions?|usd\s?b|bn)\b[^)\n]*\)|'
                r'\b(?:en|in)\s+(?:miles\s+de\s+millones|billions)\b', re.I), 1e9),
    (re.compile(r'\([^)\n]*(?:millones|millions|usd\s?m|mm)\b[^)\n]*\)|\b(?:en|in)\s+(?:millones|millions)\b',
                re.I), 1e6),
)

KINDS = ('money', 'pct', 'mult', 'score')
# funciones cuyo TRABAJO es estimar (la simulación por agentes inventa impactos %
# por diseño): ahí el guardián solo revisa dinero (core/ai._ai_complete).
ESTIMATE_FEATURES = frozenset({'simulacion_agentes'})


# ════════════════════════════════════════════════════════════════════════════
# Lectura de números
# ════════════════════════════════════════════════════════════════════════════
def _cands(tok):
    """'1.234,56' → [(1234.56, 0.005)]; '1,500' → [(1500, .5), (1.5, .0005)].
    Cada lectura con su media unidad del último dígito mostrado."""
    s = (tok or '').strip()
    if not s:
        return []
    try:
        dot, com = '.' in s, ',' in s
        if dot and com:
            if s.rfind('.') > s.rfind(','):                      # 1,234.56 (en)
                ip, _sep, dp = s.replace(',', '').partition('.')
            else:                                                # 1.234,56 (es)
                ip, _sep, dp = s.replace('.', '').partition(',')
            return [(float(ip + '.' + dp), 0.5 * 10 ** -len(dp))]
        sep = '.' if dot else ',' if com else None
        if sep is None:
            return [(float(s), 0.5)]
        parts = s.split(sep)
        if len(parts) > 2:                                       # 1.234.567 / 1,234,567
            return [(float(''.join(parts)), 0.5)]
        a, b = parts
        dec = (float(a + '.' + b), 0.5 * 10 ** -len(b))
        if len(b) == 3 and not a.startswith('0'):                # 1,500 / 1.500: ambiguo
            th = (float(a + b), 0.5)
            return [th, dec] if sep == ',' else [dec, th]
        return [dec]
    except ValueError:
        return []


def _to_float(s):
    """Compatibilidad: primera lectura del número (None si no es número)."""
    c = _cands(s)
    return c[0][0] if c else None


def _scale_of(word):
    if not word:
        return None
    w = word.strip()
    for pat, m in _SCALES:
        if re.fullmatch(pat, w, re.I):
            return m
    g = {'T': 1e12, 'TN': 1e12, 'B': 1e9, 'BN': 1e9, 'M': 1e6, 'MM': 1e6, 'K': 1e3}
    return g.get(w.upper())


def _segment_before(text, start, cap=90):
    """Texto de la MISMA frase antes de `start` (corta en . ! ? ; o salto de línea)."""
    w = text[max(0, start - cap):start]
    cut = max(w.rfind('\n'), *(m.end() for m in re.finditer(r'[.!?;](?=\s)', w)), -1)
    return w[cut + 1:] if cut >= 0 else w


class Mention:
    __slots__ = ('kind', 'text', 'span', 'cands', 'big', 'pol', 'approx', 'ineq', 'key', 'skip')

    def __init__(self, kind, text, span, cands, big=False, key=None):
        self.kind, self.text, self.span, self.cands, self.big, self.key = kind, text, span, cands, big, key
        self.pol, self.approx, self.ineq, self.skip = None, False, None, False

    def __repr__(self):
        return f'Mention({self.kind}, {self.text!r})'


def _ctx(m, text):
    """Polaridad, aproximación, desigualdad y exenciones (hipótesis/umbral/confianza)."""
    s, e = m.span
    seg = _segment_before(text, s)
    near = seg[-24:]
    after = text[e:e + 30]
    sg = None
    lead = re.match(r'\s*([-−–+])', text[s:e])
    if lead:
        sg = lead.group(1)
    else:
        inner = re.search(r'[$€£¥₩₹₽A-Za-z/.]\s?([-−–])\s?\d', text[s:e])
        sg = inner.group(1) if inner else None
    if sg:
        m.pol = 'pos' if sg == '+' else 'neg'
    elif _AFTER_NEG.search(after):
        m.pol = 'neg'
    elif _AFTER_POS.search(after):
        m.pol = 'pos'
    else:
        w = seg[-45:]
        hits = [(x.end(), 'neg') for x in _NEG.finditer(w)] + [(x.end(), 'pos') for x in _POS.finditer(w)]
        m.pol = max(hits)[1] if hits else None
    m.approx = bool(_APPROX.search(near))
    m.ineq = 'gt' if _GT.search(near) else 'lt' if _LT.search(near) else None
    if _HYPO.search(seg) or _THRESH_OP.search(near) or _TAGGED_AFTER.match(after):
        m.skip = True
    if m.kind == 'pct':
        v = m.cands[0][0] if m.cands else None
        if v in (0.0, 100.0) or _CONF_BEFORE.search(near) or _CONF_AFTER.search(after):
            m.skip = True


def _mentions(text, kinds=KINDS):
    """Cifras que el texto presenta como dato, sin solaparse (gana la más larga)."""
    text = text or ''
    found = []
    if 'money' in kinds:
        for rx in (_MONEY_PRE, _MONEY_SUF, _MONEY_GLUED):
            for mt in rx.finditer(text):
                gd = mt.groupdict()
                scale = _scale_of(gd.get('scale') or gd.get('scale2') or gd.get('glued')) or 1.0
                cs = [(v * scale, h * scale) for v, h in _cands(mt.group(_num_group(mt)))]
                if not cs:
                    continue
                big = scale > 1.0 or any(v >= 1e6 for v, _h in cs)
                found.append(Mention('money', mt.group(0).strip(), _strip_span(mt), cs, big=big))
    if 'pct' in kinds:
        for mt in _PCT.finditer(text):
            cs = _cands(mt.group(_num_group(mt)))
            if cs:
                found.append(Mention('pct', mt.group(0).strip(), _strip_span(mt), cs))
    if 'mult' in kinds:
        for mt in _MULT.finditer(text):
            cs = _cands(mt.group(_num_group(mt)))
            if cs:
                found.append(Mention('mult', mt.group(0).strip(), _strip_span(mt), cs))
    if 'score' in kinds or 'mult' in kinds:
        for mt in _SCORE_RX.finditer(text):
            key = next(k for k, _p in _SCORE_KEYS if mt.group('k_' + k))
            if key == 'beta' and not re.search(r'[.,]', mt.group(_num_group(mt))):
                continue                                         # "beta 2" (versión) ≠ beta 1,3
            if key in _MULT_KEYS and 'mult' not in kinds or key not in _MULT_KEYS and 'score' not in kinds:
                continue
            cs = _cands(mt.group(_num_group(mt)))
            if cs:
                found.append(Mention('mult' if key in _MULT_KEYS else 'score', mt.group(0).strip(),
                                     _strip_span(mt), cs, key=key))
    found.sort(key=lambda x: (x.span[0], -(x.span[1] - x.span[0])))
    out, last_end = [], -1
    for m in found:
        if m.span[0] < last_end:
            continue
        out.append(m)
        last_end = m.span[1]
    for m in out:
        _ctx(m, text)
    return out


def _num_group(mt):
    """Índice del grupo del número (el primer grupo sin nombre)."""
    names = set(mt.re.groupindex.values())
    return next(i for i in range(1, mt.re.groups + 1) if i not in names)


def _strip_span(mt):
    s, e = mt.span()
    txt = mt.group(0)
    s += len(txt) - len(txt.lstrip())
    e -= len(txt) - len(txt.rstrip())
    return (s, e)


# ════════════════════════════════════════════════════════════════════════════
# Hechos de la fuente
# ════════════════════════════════════════════════════════════════════════════
_SRC_NUM = re.compile(_SIGN + _NUM)


class Facts:
    """Valores de los DATOS, separados por tipo. Cada valor: (número, signo)."""

    def __init__(self):
        self.money, self.pct, self.mult, self.plain = [], [], [], []
        self.score = {}
        self._idx = {}

    def index(self, name, key=None):
        """(valores absolutos ordenados, signos) sin repetidos — búsqueda por rango
        con bisect: el costo no crece con textos repetitivos ni con miles de cifras."""
        ck = (name, key, len(self))
        if ck not in self._idx:
            if name == 'score':
                rows = self.score.get(key, [])
            elif name == 'mult' and key:
                rows = self.mult + self.score.get(key, [])
            else:
                rows = getattr(self, name)
            uniq = sorted({(abs(c), s) for c, s in rows})
            self._idx[ck] = ([a for a, _s in uniq], [s_ for _a, s_ in uniq])
        return self._idx[ck]

    def __iter__(self):                        # compatibilidad con el viejo set de números
        seen = set()
        for v, _s in self.money + self.pct + self.mult + self.plain:
            if v not in seen:
                seen.add(v)
                yield v

    def __len__(self):
        return len(self.money) + len(self.pct) + len(self.mult) + len(self.plain)

    def add_text(self, txt):
        txt = _DATE_RX.sub(' ', txt or '')
        for mt in _SRC_NUM.finditer(txt):
            s, e = mt.start(_num_group(mt)), mt.end(_num_group(mt))
            after = txt[e:e + 40]
            if re.match(r'[^\d\n]{0,32}?\(⚠', after):
                continue                       # cifra ya marcada ⚠ (historial): no respalda nada
            line_start = max(txt.rfind('\n', max(0, s - 240), s) + 1, s - 240)   # acotado: lineal
            before = txt[max(line_start, s - 40):s]
            low = before.lower()
            sg = mt.group('sg')
            sign = '-' if sg in ('-', '−', '–') else '+' if sg == '+' else None
            tok = mt.group(_num_group(mt))
            cands = _cands(tok)
            if not cands:
                continue
            has_dec = bool(re.search(r'[.,]', tok))
            if re.match(r'\s?(?:%|por\s?ciento|percent|pp(?![\w])|p\.\s?p\.|puntos|points)', after, re.I):
                for v, _h in cands:
                    self.pct.append((v, sign))
                self._keyed(before, cands, sign)
                continue
            if re.match(r'\s?(?:x|×)(?![\w])', after):
                for v, _h in cands:
                    self.mult.append((v, sign))
                self._keyed(before, cands, sign)
                continue
            sc = re.match(r'\s?(' + _SCALE_WORD + r')', after, re.I) or re.match(r'(' + _GLUED_CUR + r')', after)
            scale = _scale_of(sc.group(1)) if sc else None
            if scale is None and _B_KEY.search(low):
                scale = 1e9
            elif scale is None and _M_KEY.search(low):
                scale = 1e6
            cur = bool(re.search(_CUR_PRE + r'\s?[-−–]?\s?$', before, re.I)) or bool(
                re.match(r'\s?(?:' + _SCALE_WORD + r'\s*(?:de\s+)?)?' + _CUR_WORD, after, re.I))
            money_hint = bool(_MONEY_HINT.search(low[-30:]))
            header = None
            line_before = txt[line_start:s]
            for rx, mul in _HEADER_SCALE:
                if rx.search(line_before):
                    header = mul
                    break
            for v, _h in cands:
                if scale:
                    self.money.append((v * scale, sign))
                if cur or money_hint or scale:
                    self.money.append((v, sign))
                if header and not scale:
                    self.money.append((v * header, sign))
                if v >= 1e6:
                    self.money.append((v, sign))
                if _PCT_HINT.search(low[-30:]):
                    self.pct.append((v, sign))
                    if abs(v) <= 1.5 and re.search(r'[.,]\d', tok):
                        self.pct.append((v * 100, sign))      # fracción rotulada: 0,75 → 75 %
                if _MULT_HINT.search(low[-30:]):
                    self.mult.append((v, sign))
                if has_dec or len(re.sub(r'\D', '', tok)) >= 4:
                    self.plain.append((v, sign))
            self._keyed(before, cands, sign)
        return self

    def _keyed(self, before, cands, sign):
        """El número que sigue a un rótulo (RSI 55,3 · "nrs":62 · P/E (12 meses) 35,2)."""
        last = None
        for km in _SCORE_SRC.finditer(before):
            last = km
        if not last:
            return
        rest = before[last.end():]
        rest = re.sub(r'^\s?(?:\(\s?\d{1,3}\s?\)|_?\d{1,3}(?=[\s"\':=]))', '', rest)
        if re.search(r'\d', rest) or len(rest) > 25:
            return
        key = next(k for k, _p in _SCORE_KEYS if last.group('k_' + k))
        for v, _h in cands:
            self.score.setdefault(key, []).append((v, sign))
            if key in _MULT_KEYS:
                self.mult.append((v, sign))


def facts_from_text(text):
    return Facts().add_text(text)


def evidence_numbers(evidence):
    """Hechos (por tipo) del paquete de evidencia [{title, excerpt}]."""
    f = Facts()
    for e in evidence or []:
        f.add_text(f"{e.get('title') or ''}\n{e.get('excerpt') or ''}")
    return f


# ════════════════════════════════════════════════════════════════════════════
# Comparación
# ════════════════════════════════════════════════════════════════════════════
def _tol(kind, c, half, approx):
    """Tolerancia ABSOLUTA para comparar una cifra con el dato c (ver docstring)."""
    a = abs(c)
    if kind == 'money_big':
        return max(0.01 * a, min(half, (0.15 if approx else 0.10) * a))
    if kind == 'price':
        return max(0.005 * a, min(half, (0.05 if approx else 0.02) * a))
    if kind == 'pct':
        return max(half, 0.10 * a, 0.5) if approx else max(half, 0.005 * a, 0.05)
    return max(half, 0.10 * a) if approx else max(half, 0.01 * a)      # múltiplo / indicador


def _sign_ok(pol, sign):
    return not ((sign == '-' and pol == 'pos') or (sign == '+' and pol == 'neg'))


def _close(m, v, half, c, sign, kind):
    if not _sign_ok(m.pol, sign):
        return False
    a = abs(c)
    if m.ineq == 'gt':
        return v * 0.99 <= a <= v * 2.0
    if m.ineq == 'lt':
        return v * 0.5 <= a <= v * 1.01
    return abs(a - v) <= _tol(kind, c, half, m.approx) + 1e-12


def _near(idx, lo, hi):
    vals, signs = idx
    i = bisect_left(vals, lo)
    while i < len(vals) and vals[i] <= hi:
        yield vals[i], signs[i]
        i += 1


def _window(v, half):
    """Rango de datos que PUEDE respaldar v (la tolerancia más ancha de todas)."""
    return min(0.5 * v, (v - half) / 1.2 - 0.5), max(2.0 * v, (v + half) / 0.8 + 0.5)


def supported(m, facts):
    """¿La cifra `m` (Mention) está respaldada por `facts`?"""
    if m.skip:
        return True
    for v, half in m.cands:
        lo, hi = _window(v, half)
        if m.kind == 'money':
            kind = 'money_big' if m.big else 'price'
            if any(_close(m, v, half, c, s, kind) for c, s in _near(facts.index('money'), lo, hi)):
                return True
            if not m.big and not m.ineq and any(_sign_ok(m.pol, s) for _c, s in
                                                _near(facts.index('plain'), v - half - 1e-12, v + half + 1e-12)):
                return True                     # número sin rótulo: solo a la precisión mostrada
        elif m.kind == 'pct':
            if any(_close(m, v, half, c, s, 'pct') for c, s in _near(facts.index('pct'), lo, hi)):
                return True
            if not m.ineq and any(_sign_ok(m.pol, s) and c != int(c) for c, s in
                                  _near(facts.index('plain'), v - half - 1e-12, v + half + 1e-12)):
                return True
        elif m.kind == 'mult':
            if any(_close(m, v, half, c, s, 'mult') for c, s in _near(facts.index('mult', m.key), lo, hi)):
                return True
        elif m.kind == 'score':
            if any(_close(m, v, half, c, s, 'score') for c, s in _near(facts.index('score', m.key), lo, hi)):
                return True
    return False


def unsupported_mentions(text, facts, kinds=KINDS):
    return [m for m in _mentions(text, kinds) if not supported(m, facts)]


def unsupported_figures(text, facts, kinds=KINDS):
    """Cifras (texto tal como aparece) de `text` sin respaldo en `facts`."""
    return [m.text for m in unsupported_mentions(text, facts, kinds)]


def unsupported_money(text, vals):
    """Solo dinero/precios (contrato viejo; lo usan retract/withhold de claims guardadas)."""
    return unsupported_figures(text, vals, ('money',))


def money_mentions(text):
    """[(texto_original, valor_en_B | None si es precio unitario, valor_crudo)]"""
    out = []
    for m in _mentions(text, ('money',)):
        v = m.cands[0][0]
        out.append((m.text, v / 1e9 if m.big else None, v))
    return out


def check_numbers(result, evidence, kinds=KINDS):
    """Errores (lista vacía = ok) por cifras que NO están en la evidencia."""
    vals = evidence_numbers(evidence)
    errs = []
    for i, c in enumerate(result.claims):
        txt = ' '.join(filter(None, [c.statement_es, c.statement_en, c.reasoning_summary, c.object]))
        bad = unsupported_figures(txt, vals, kinds)
        if bad:
            errs.append(f'claim[{i}] usa cifras que NO están en la evidencia: {sorted(set(bad))}. '
                        'Usa SOLO cifras del paquete (la capitalización actual es la del perfil de '
                        'mercado en vivo; porcentajes, múltiplos e indicadores, los calculados en la '
                        'evidencia) o quita la cifra; nunca cifras de memoria.')
    for fld in ('summary_es', 'summary_en'):
        bad = unsupported_figures(getattr(result, fld, '') or '', vals, kinds)
        if bad:
            errs.append(f'{fld} usa cifras que NO están en la evidencia: {sorted(set(bad))}.')
    return errs


# ── Guardián GENERAL para toda llamada de IA (core/ai._ai_complete) ─────────

NUMBERS_RULE = (
    '\n\nREGLA DE CIFRAS (obligatoria): toda cifra de dinero o precio (capitalización, valuación, '
    'ingresos, deuda, precio de acción, rondas), todo porcentaje (márgenes, crecimiento, variaciones, '
    'volatilidad), múltiplo (P/E, 25x) o indicador (RSI, NRS, beta) debe COPIARSE de los datos que te doy '
    'en este mensaje. NUNCA uses cifras de tu memoria: están desactualizadas y un dato falso perjudica al '
    'inversionista. Si no tienes el dato, dilo ("no tengo el dato en vivo") en vez de estimarlo. '
    '/ FIGURES RULE: every money figure, price, percentage, multiple or indicator must be COPIED from the '
    'data given in this message; never from memory. If you lack it, say so instead of estimating.')

_ES = re.compile(r'\b(el|la|los|las|de|que|para|con|una|por)\b', re.I)
_EN = re.compile(r'\b(the|of|and|to|with|for|is|are|that)\b', re.I)


def unsupported_in(text, source_text, kinds=KINDS):
    """Cifras de `text` que NO aparecen en `source_text` (los DATOS del mensaje)."""
    return sorted(set(unsupported_figures(text, facts_from_text(source_text or ''), kinds)))


def mark_unsupported(text, bad, kinds=KINDS):
    """Marca en el texto cada cifra sin respaldo (no la borra: el lector ve que
    NO está verificada), en el TRAMO exacto de la cifra. Seguro dentro de JSON."""
    if not bad or not text:
        return text
    bad = set(bad)
    es = len(_ES.findall(text)) >= len(_EN.findall(text))
    tag = ' (⚠ cifra no verificada)' if es else ' (⚠ unverified figure)'
    spans = [m.span for m in _mentions(text, kinds) if m.text in bad]
    for s, e in sorted(spans, reverse=True):
        if _TAGGED_AFTER.match(text[e:e + 3]):
            continue
        text = text[:e] + tag + text[e:]
    return text
