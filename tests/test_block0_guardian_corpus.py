"""Bloque 0 (docs/BRECHAS_V2.md, L4-02 / L4-M1 / L2-04): el guardián de cifras
medido sobre un CORPUS realista — respuestas en español e inglés escritas sobre
los formatos de datos que la app de verdad le pasa a la IA (bloque DATOS EN
VIVO, resultados JSON de herramientas del chat, evidencia de investigación,
hechos del comité de cartera, noticias, simulación) con un system prompt que
trae reglas y el ejemplo «233,95 USD».

  · CORRECTAS: cifras copiadas (o redondeadas) de los datos → no deben marcarse.
  · INVENTADAS: al menos una cifra que NO está en los datos (de memoria, mal
    redondeada, con el signo cambiado, el ejemplo del system…) → deben marcarse.

Antes (guardián viejo, fuente = system+prompt, ±15 %, solo dinero) vs después
se compara con scratch/b0/corpus_eval.py; aquí se FIJA el resultado nuevo.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.numbers import unsupported_in  # noqa: E402

SYSTEM = (
    'Eres Khipu, el analista de Khipus Finance Intelligence. RESPUESTA: primero la respuesta directa a lo '
    'preguntado (1-2 frases), luego el porqué (3-6 líneas, máx. una lista). Cada cifra con su fuente y fecha en '
    'la misma frase, p. ej. «233,95 USD (Yahoo, hoy)». Nunca inventes cifras ni datos: si no están, dilo. '
    'Acciones de pantalla solo si ayudan (máx. 2). Prosa clara, 80-250 palabras; si la respuesta quedó cortada, '
    'máx. 180 palabras. Universo: 949 empresas, 2.510 relaciones, 13 sectores.')

NVDA = """PREGUNTA: ¿Cómo va Nvidia hoy?
DATOS EN VIVO (consultados ahora, 2026-10-12 14:05 UTC) — tienen PRIORIDAD sobre cualquier otra cifra:
- Nvidia (NVDA, cotiza): capitalización de mercado 4412.6 mil millones USD; precio 181.27 USD [en vivo, yahoo]
DATOS CONSULTADOS:
[1] get_company({"id_or_ticker": "Nvidia"}) → {"id":"Nvidia","ticker":"NVDA","nrs":62,"live":{"price":181.27,\
"prev_close":178.9,"change_pct":1.32,"currency":"USD","market_cap_usd_b":4412.6,"pe_trailing":51.3,\
"gross_margin":75.0,"revenue_growth_q":56.1,"week52_high":212.5,"week52_low":86.6,"source":"yahoo",\
"as_of":"2026-10-12T14:05:00Z"},"top_suppliers":[{"id":"TSMC","w":6},{"id":"SK Hynix","w":6}],"degree":48}"""

AVGO = """ENTIDAD: Broadcom (id Broadcom, ticker AVGO)
[E2] Estados anuales AVGO (yahoo, moneda original USD) | ingresos USD: 2023: 35.8B, 2024: 51.6B, 2025: 63.9B | \
beneficio neto: 2023: 14.1B, 2024: 5.9B, 2025: 23.1B | flujo de caja libre: 2023: 17.6B, 2024: 19.4B, 2025: 26.9B | \
deuda total: 2023: 39.2B, 2024: 67.6B, 2025: 64.2B
[E3] Perfil de mercado EN VIVO AVGO (yahoo) | CAPITALIZACIÓN ACTUAL EN VIVO: 1612.4 miles de millones USD · \
price=342.8, change_pct=-2.35, market_cap_usd_b=1612.4, gross_margin=77.1, operating_margin=40.2, pe_trailing=88.4, \
revenue_growth_q=22.0
[E4] Ratios financieros de Broadcom calculados por Khipus | Ingresos 2025: 63.9 mil millones USD (+23.8 % vs 2024) · \
margen de flujo de caja libre 42.1 % en 2025 · deuda neta 54.9 mil millones USD (2025) · rendimiento del flujo de \
caja libre 1.67 % (FCF 2025 ÷ capitalización en vivo 1612.4 mil millones USD) · precio/FCF 59.9x · ROIC 14.2 % (2025)
[E5] Análisis técnico de AVGO (1 año diario vs S&P 500) | RSI(14) 41.7 · SMA50 355.2 · SMA200 298.4 · caída máxima \
1 año -31.5 % · rendimiento 3 meses -6.2 % vs S&P 500 +4.1 %"""

PORTF = """Valor 25480.5 USD; volatilidad anual 31.2 %; máxima caída -24.8 %; VaR 95 % 1 día 2.9 % (738.9 USD); perfil \
Moderado (tope por posición 25 %, volatilidad objetivo 18 %).
Nvidia (NVDA): peso 46.3 %, volatilidad 48.9 %, aporta 62.1 % del riesgo, convicción 38.
TSMC (TSM): peso 31.5 %, volatilidad 39.4 %, aporta 27.7 % del riesgo, convicción sin investigación.
Apple (AAPL): peso 22.2 %, volatilidad 24.1 %, aporta 10.2 % del riesgo, convicción 12.
A1: reduce Nvidia de 46.3 % a 25 % (-5427.2 USD) — Nvidia pesa 46.3 % de tu cartera; lo prudente es hasta 25 %."""

TSMC = """QUESTION: What happened with TSMC this week?
DATA:
[1] get_news({"company": "TSMC"}) → [{"title":"TSMC September revenue rises 31.2% to NT$331.6 billion",\
"source":"reuters.com","published_at":"2026-10-10"},{"title":"TSMC to raise 2nm wafer prices by 3%-5% in 2027",\
"source":"digitimes.com","published_at":"2026-10-08"}]
[2] get_company({"id_or_ticker": "TSMC"}) → {"ticker":"TSM","live":{"price":301.45,"currency":"USD",\
"change_pct":-0.84,"market_cap_usd_b":1563.2,"pe_trailing":27.9}}"""

SIM = """Pregunta del inversor: ¿Qué pasa si China bloquea Taiwán?
{"contexto": {"semilla": "TSMC"}, "simulacion": {"shock": "Taiwan", "impactos": [{"empresa": "TSMC", "pct": -38.5}, \
{"empresa": "Nvidia", "pct": -21.2}, {"empresa": "Apple", "pct": -14.7}, {"empresa": "Intel", "pct": 6.3}], \
"rho": 1.42}}"""

SAP = """DATOS CONSULTADOS:
[1] get_news({"company": "SAP"}) → [{"title":"SAP eleva su previsión: ingresos en la nube de 21.300 millones de \
euros en 2026","source":"expansion.com"},{"title":"La acción de SAP cierra en 238,40 euros, un 1,8 % más",\
"source":"cincodias.elpais.com"}]
[2] get_company({"id_or_ticker": "SAP"}) → {"ticker":"SAP.DE","live":{"price":238.4,"currency":"EUR",\
"price_usd":277.9,"market_cap_usd_b":341.7,"pe_trailing":44.2}}"""

PFAI = """CONTEXTO:
Cartera «Crecimiento IA»: 5 posiciones, monto 10000 USD; volatilidad anual 28.4 %; VaR 95 % 1 día 254.1 USD; \
beta S&P 500 1.21; correlación media 0.58
- Nvidia 30 % (3000 USD), AMD 20 % (2000 USD), TSMC 20 % (2000 USD), ASML 15 % (1500 USD), Broadcom 15 % (1500 USD)
PREGUNTA: ¿Qué tan arriesgada es mi cartera?"""

AAPL = """CONVERSATION:
User: how much is Apple worth?
Khipu: Apple is worth $5.1T (⚠ unverified figure).
User: and the price?
DATA:
[1] get_company({"id_or_ticker": "Apple"}) → {"ticker":"AAPL","live":{"price":254.63,"prev_close":256.1,\
"change_pct":-0.57,"market_cap_usd_b":3781.4,"pe_trailing":38.6,"dividend_yield":0.41}}"""

NEWS = """Noticias recientes de la cadena de memoria:
- "Micron reports record HBM revenue of $4.2 billion, up 82% year over year" (reuters.com, 2026-10-09)
- "Samsung shares fall 3.1% after weak guidance" (bloomberg.com, 2026-10-10)
- OpenAI (privada, NO cotiza): última valuación VERIFICADA ~$500B — no es un precio en vivo; puede haber cambiado"""

ASML = """PREGUNTA: precio de ASML
[1] get_company({"id_or_ticker": "ASML"}) → {"ticker":"ASML","live":{"price":1034.18,"currency":"USD",\
"change_pct":2.07,"market_cap_usd_b":406.9,"pe_trailing":36.5}}"""

# (fuente, respuesta)
CORRECT = [
    (NVDA, 'Nvidia cotiza a 181,27 USD (Yahoo, hoy), +1,32 % frente al cierre previo de 178,90 USD. Vale unos '
           '4,41 billones de dólares y su P/E es 51,3x.'),
    (NVDA, 'Nvidia trades at $181.27, up 1.32% today; its market cap is about $4.4T. Gross margin is 75% and '
           'quarterly revenue growth was 56%.'),
    (NVDA, 'Su NRS es 62/100 y tiene 48 relaciones de flujo; TSMC y SK Hynix son sus proveedores críticos.'),
    (NVDA, 'El precio (181,27 USD) sigue lejos del máximo de 52 semanas de 212,5 USD y muy por encima del mínimo '
           'de 86,6 USD.'),
    (NVDA, 'Market cap: US$ 4,412.6 billion; P/E 51.3 (Yahoo, as of today).'),
    (NVDA, 'Si cae por debajo de 160 USD, el soporte de largo plazo quedaría en duda.'),
    (AVGO, 'Broadcom vale US$ 1,61 billones; cayó 2,35 % hoy y cotiza a 342,80 USD.'),
    (AVGO, 'Ingresos de $63.9B en 2025 (+23,8 %), flujo de caja libre de $26,9 mil millones y margen de FCF de '
           '42,1 %.'),
    (AVGO, 'Deuda neta de 54,9 mil millones USD; precio/FCF 59,9x; el RSI(14) está en 41,7.'),
    (AVGO, 'La caída máxima en un año fue de 31,5 % y en 3 meses rinde -6,2 % frente a +4,1 % del S&P 500.'),
    (AVGO, "Broadcom's market cap is $1.6T; revenue grew 23.8% to $63.9B and the FCF yield is 1.67%. ROIC 14.2%."),
    (AVGO, 'Gross margin 77.1%, operating margin 40.2%, trailing P/E 88.4x.'),
    (PORTF, 'Tu cartera vale 25.480,50 USD y su volatilidad anual es 31,2 %, por encima del objetivo de 18 %.'),
    (PORTF, 'Nvidia pesa 46,3 % pero aporta 62,1 % del riesgo; A1 propone bajarla a 25 % (vender unos 5.427 USD).'),
    (PORTF, 'Your portfolio is worth $25,480.50; the 1-day 95% VaR is 2.9% ($738.90).'),
    (PORTF, 'TSMC pesa 31,5 % y aporta 27,7 % del riesgo; Apple, con 24,1 % de volatilidad, es la más estable.'),
    (PORTF, 'La peor caída fue de 24,8 %, normal para una cartera con 48,9 % de volatilidad en su mayor posición.'),
    (TSMC, "TSMC's September revenue rose 31.2% to NT$331.6 billion (Reuters). The ADR trades at $301.45, down "
           '0.84% today; market cap $1.56T.'),
    (TSMC, 'It plans to lift 2nm wafer prices by 3%-5% in 2027, with a trailing P/E of 27.9x.'),
    (TSMC, 'Los ingresos de septiembre subieron 31,2 % hasta NT$ 331,6 mil millones; la acción baja 0,84 %.'),
    (SIM, 'En la simulación, TSMC cae 38,5 %, Nvidia 21,2 % y Apple 14,7 %, mientras Intel sube 6,3 %.'),
    (SIM, 'Under the blockade TSMC would fall 38.5% and Intel would gain 6.3%; the spectral radius is 1.42.'),
    (SIM, 'Apple pierde 14,7 % por su dependencia de TSMC, que se desploma 38,5 %.'),
    (SAP, 'SAP cerró en 238,40 euros (+1,8 %) y prevé ingresos en la nube de 21.300 millones de euros en 2026.'),
    (SAP, 'En dólares son unos 277,90 USD por acción; capitalización de US$ 341,7 mil millones y P/E de 44,2.'),
    (SAP, 'SAP closed at €238.40, up 1.8%, and its market cap is about $342B.'),
    (PFAI, 'Tu cartera de 10.000 USD tiene una volatilidad anual de 28,4 % y una beta de 1,21 frente al S&P 500.'),
    (PFAI, 'En un mal día (VaR 95 %) podrías perder unos 254 USD; Nvidia es la mayor posición con 30 % (3.000 USD).'),
    (PFAI, 'ASML y Broadcom pesan 15 % cada una (1.500 USD) y la correlación media es 0,58.'),
    (AAPL, "Apple's market cap is $3.78T and it trades at $254.63, down 0.57% today."),
    (AAPL, 'P/E 38.6 and a dividend yield of 0.41%; it closed yesterday at $256.10.'),
    (AAPL, 'Apple cotiza a 254,63 USD (-0,57 %), con capitalización de 3,78 billones de dólares.'),
    (NEWS, 'Micron reportó ingresos récord de HBM por 4.200 millones de dólares (+82 % interanual), y Samsung cayó '
           '3,1 % tras una guía débil.'),
    (NEWS, 'Micron HBM revenue hit $4.2 billion, up 82% year over year.'),
    (NEWS, 'OpenAI no cotiza; su última valuación verificada ronda los US$ 500 mil millones.'),
    (NEWS, 'Samsung shares fell 3.1% after weak guidance.'),
    (ASML, 'ASML cotiza a 1.034,18 USD (+2,07 %) y vale US$ 406,9 mil millones.'),
    (ASML, 'ASML trades at $1,034.18, up 2.07%; P/E 36.5x and a market cap near $407B.'),
    (ASML, 'Precio: 1034,18 dólares; capitalización de 406.900 millones de USD.'),
    (ASML, 'If it breaks above $1,100 the next resistance would be the 52-week high.'),
    (NVDA, 'Respuesta corta: 3 de 4 analistas son positivos; el comité revisa en 20 días hábiles y la '
           'investigación cubre 5 horizontes.'),
    (AVGO, 'Broadcom: ingresos 2023 de 35,8 mil millones USD, 2024 de 51,6 y 2025 de 63,9 (todo en USD).'),
]

INVENTED = [
    (NVDA, 'Nvidia cotiza a 233,95 USD (Yahoo, hoy), +1,32 %.'),                     # el ejemplo del system
    (NVDA, 'Nvidia sube 2,4 % hoy y cotiza a 181,27 USD.'),
    (NVDA, 'Nvidia vale $3.2T según el dato en vivo.'),
    (NVDA, 'Su P/E es 35x, bastante menos que sus pares.'),
    (NVDA, 'Tiene un NRS de 85/100, de los más altos del grafo.'),
    (NVDA, 'El precio es $195 y el margen bruto 75 %.'),
    (NVDA, 'Revenue grew 94% last quarter and the stock trades at $181.27.'),
    (NVDA, 'Market cap: 5,2 billones de dólares.'),
    (AVGO, 'El margen operativo es de 45 % y el bruto de 77,1 %.'),
    (AVGO, 'Broadcom subió 2,35 % hoy hasta 342,80 USD.'),
    (AVGO, 'El RSI de 72 indica sobrecompra.'),
    (AVGO, 'Su deuda total es de $80B.'),
    (AVGO, 'Cotiza a un P/E de 120x.'),
    (AVGO, 'Flujo de caja libre positivo de US$ 31 mil millones en 2025.'),
    (AVGO, 'Broadcom earns a 60% gross margin on $63.9B of revenue.'),
    (PORTF, 'Nvidia aporta 75 % del riesgo de tu cartera.'),
    (PORTF, 'Tu cartera vale 30.000 USD.'),
    (PORTF, 'La volatilidad anual de tu cartera es de 42 %.'),
    (PORTF, 'A1 propone vender 8.000 USD de Nvidia.'),
    (PORTF, 'Your 1-day VaR is $1,250.'),
    (TSMC, 'TSMC revenue jumped 45% in September.'),
    (TSMC, 'September revenue reached NT$400 billion.'),
    (TSMC, 'The ADR trades at $315.'),
    (TSMC, 'Its market cap is $1.9T.'),
    (SIM, 'En la simulación, TSMC cae 50 % y Nvidia 21,2 %.'),
    (SIM, 'Nvidia sube 21,2 % porque gana cuota.'),
    (SIM, 'Apple cae 25 % por su dependencia de TSMC.'),
    (SAP, 'SAP cotiza a 255 euros.'),
    (SAP, 'SAP vale 500 mil millones de dólares.'),
    (SAP, 'SAP prevé ingresos en la nube de 25.000 millones de euros.'),
    (SAP, 'SAP closed at €238.40, up 4.5%.'),
    (PFAI, 'Tu cartera tiene una beta de 1,8.'),
    (PFAI, 'La volatilidad anual es de 35 %.'),
    (PFAI, 'En un mal día podrías perder 900 USD.'),
    (AAPL, 'Apple is worth $5.1T.'),                                               # sale del historial marcado
    (AAPL, 'Apple trades at $268 with a P/E of 38.6.'),
    (AAPL, 'Dividend yield of 1.2%.'),
    (NEWS, 'Micron HBM revenue grew 95% to $4.2 billion.'),
    (NEWS, 'Samsung cayó 7 % tras la guía.'),
    (NEWS, 'OpenAI is valued at $852B.'),
    (ASML, 'ASML cotiza a 1.150 USD.'),
    (ASML, 'ASML vale US$ 520 mil millones.'),
    (ASML, 'ASML sube 3,5 % hoy.'),
]


# Casos DIFÍCILES escritos después, sin ajustar el guardián a ellos: redondeos,
# desigualdades y cifras DERIVADAS (restas/sumas que la IA calcula bien pero que
# no están en los datos → el guardián las marca: falso positivo conocido).
HARD_CORRECT = [
    (NVDA, 'La acción subió 1,3 % y está en 181 USD.'),
    (NVDA, 'Nvidia vale más de $4T y su P/E está por encima de 50x.'),
    (NVDA, 'Market cap above $4 trillion; gross margin around 75%.'),
    (AAPL, 'Bajó de 256,10 a 254,63 USD, un 0,6 %.'),
    (AVGO, 'Broadcom bajó 2,4 % y el margen bruto ronda el 77 %.'),
    (SIM, 'TSMC pierde más de un tercio de su valor (-38,5 %); Intel es la única ganadora (+6,3 %).'),
    (PORTF, 'El 62 % del riesgo viene de una sola acción: Nvidia.'),
    (PFAI, 'Roughly a fifth of the portfolio (20%) is in AMD.'),
    (NVDA, 'Nvidia está a unos 31 USD de su máximo de 52 semanas.'),                 # derivada: 212,5 − 181,27
    (PFAI, 'Nvidia y AMD suman el 50 % de tu cartera.'),                             # derivada: 30 + 20
    (NVDA, 'La caída desde el máximo anual es de 14,7 %.'),                           # derivada
]
HARD_INVENTED = [
    (NVDA, 'Nvidia vale 4,6 billones de dólares.'),
    (NVDA, 'El margen bruto es de 73 %.'),
    (NVDA, 'Cotiza con un P/E de 47x.'),
    (AVGO, 'Broadcom cotiza a 352 USD.'),
    (ASML, 'ASML trades at $1,061.'),
    (NVDA, 'Nvidia cayó 1,32 % hoy.'),            # signo cambiado frente a un dato SIN signo explícito: no se detecta
]
HARD_KNOWN_FP = 3      # las tres derivadas
HARD_KNOWN_FN = 1      # el signo frente a "change_pct":1.32 (sin '+')


def _flagged(src, ans):
    return bool(unsupported_in(ans, src))


def metrics():
    fp = [a for s, a in CORRECT if _flagged(s, a)]
    tp = [a for s, a in INVENTED if _flagged(s, a)]
    fn = [a for s, a in INVENTED if not _flagged(s, a)]
    prec = len(tp) / (len(tp) + len(fp)) if tp or fp else 1.0
    rec = len(tp) / len(INVENTED)
    return {'fp': fp, 'tp': tp, 'fn': fn, 'precision': prec, 'recall': rec}


def test_corpus_es_suficientemente_grande():
    assert len(CORRECT) >= 40 and len(INVENTED) >= 40


def test_guardian_nuevo_precision_y_recall_en_el_corpus():
    m = metrics()
    assert m['recall'] >= 0.95, m['fn']
    assert len(m['fp']) <= 1, m['fp']
    assert m['precision'] >= 0.97


def test_casos_dificiles_limites_conocidos():
    fp = [a for s, a in HARD_CORRECT if _flagged(s, a)]
    fn = [a for s, a in HARD_INVENTED if not _flagged(s, a)]
    assert len(fp) <= HARD_KNOWN_FP, fp
    assert len(fn) <= HARD_KNOWN_FN, fn


def test_el_system_prompt_no_respalda_cifras():
    """El ejemplo «233,95 USD» del system NO cuenta como dato (core/ai pasa solo el prompt)."""
    assert unsupported_in('Nvidia cotiza a 233,95 USD (Yahoo, hoy).', NVDA) == ['233,95 USD']
