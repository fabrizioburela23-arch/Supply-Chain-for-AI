"""core/agents_api.py — PERFILES DE LOS AGENTES de Khipus OS (2026-10-06).

GET /api/agents/profiles?lang=es|en  (docs/KHIPUS_OS.md §3.3)

Pedido de Fabrizio: "más info o personalización de los agentes (tipos de tablas,
datos, capacidades) para que tenga sentido tenerlos como usuario". Este endpoint
dice, para cada una de las 6 mascotas (Khipu, Analista, Radar, Cadena, Técnico,
Comité), en lenguaje simple y en los dos idiomas:

  · qué hace y qué te muestra;
  · qué DATOS usa DE VERDAD — sale de research/context.py AGENT_NEEDS (lo que el
    armador de contexto realmente trae para cada tipo de analista), no de la lista
    declarativa `permitted_tools` del registro, que se queda corta;
  · qué herramientas del chat le corresponden (core/khipu_chat.TOOL_AGENT, el
    MISMO mapa que usa el progreso del chat) y qué ventana abre;
  · su HISTORIAL honesto (research/outcomes.track_record: conclusiones calificadas
    contra precios reales vs el S&P 500) y su actividad de 30 días (AgentRun:
    corridas, conclusiones, costo estimado, latencia) — solo con base de datos.

Funciona SIN base de datos (db:false, track/stats_30d null): nunca 500. Caché 60 s.
Nada de esto alimenta decisiones del comité ni órdenes: es información.
"""
import logging
import threading
import time
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request

from core.http import rate_limit

log = logging.getLogger('khipu')

agents_bp = Blueprint('agents_api', __name__, url_prefix='/api/agents')

CACHE_TTL_S = 60.0
_CACHE = {}                 # lang → (monotonic, payload)
_LOCK = threading.Lock()

# ── qué significa cada fuente de AGENT_NEEDS, en palabras de persona ─────────
NEED_TEXT = {
    'financials': ('Estados financieros anuales: ventas, ganancia, caja libre y deuda (FMP → Yahoo → Alpha Vantage)',
                   'Annual financial statements: revenue, profit, free cash flow and debt (FMP → Yahoo → Alpha Vantage)'),
    'profile': ('Perfil de mercado en vivo: precio, capitalización, márgenes y valuación (Yahoo Finance / Finnhub)',
                'Live market profile: price, market cap, margins and valuation (Yahoo Finance / Finnhub)'),
    'ratios': ('Ratios calculados por Khipus: crecimiento, márgenes, rendimiento de la caja libre, ROIC y dilución',
               'Ratios computed by Khipus: growth, margins, free-cash-flow yield, ROIC and dilution'),
    'peers': ('Comparación con empresas parecidas (sus perfiles en vivo)',
              'Comparison with similar companies (their live profiles)'),
    'sec': ('Últimos reportes oficiales ante la SEC (10-K, 10-Q, 8-K)',
            'Latest official SEC filings (10-K, 10-Q, 8-K)'),
    'news': ('Noticias de la empresa de las últimas 4 semanas (Finnhub) y titulares globales (GDELT)',
             'Company news from the last 4 weeks (Finnhub) and global headlines (GDELT)'),
    'catalog': ('Ficha curada de Khipus: qué hace, qué provee, su ventaja y su país',
                'Khipus curated profile: what it does, what it supplies, its moat and country'),
    'graph': ('Grafo de {n} empresas: sus proveedores y clientes directos',
              'Graph of {n} companies: its direct suppliers and customers'),
    'candles': ('Precios diarios del último año (Yahoo Finance): medias de 50/200 días, RSI, máximo de 52 semanas '
                'y comparación con el S&P 500',
                'Daily prices for the last year (Yahoo Finance): 50/200-day averages, RSI, 52-week high and '
                'comparison with the S&P 500'),
}
NEED_ORDER = ('profile', 'financials', 'ratios', 'peers', 'candles', 'sec', 'news', 'catalog', 'graph')
DEEP_WEB = ('En la investigación profunda, también búsqueda web (Tavily, si está configurada)',
            'In deep research, also web search (Tavily, when configured)')

# ── las 6 mascotas (mismos ids y nombres que engine/mascot.js) ───────────────
PROFILES = (
    {'id': 'khipu', 'es': 'Khipu', 'en': 'Khipu', 'role_es': 'Te responde', 'role_en': 'Answers you',
     'does_es': ('Entiende tu pregunta, decide a qué agentes consultar, junta sus datos y te responde en lenguaje '
                 'claro, con la fuente y la hora de cada cifra. No compra ni vende: te informa y te muestra las '
                 'ventanas que ayudan a entender.'),
     'does_en': ('Understands your question, decides which agents to ask, gathers their data and answers in plain '
                 'language, with the source and time of every figure. It never buys or sells: it informs you and '
                 'opens the windows that help you understand.'),
     'data_es': ['Lo que traen los otros cinco agentes, en el momento de tu pregunta',
                 'Estado de la investigación: cola, presupuesto diario y proveedores de IA disponibles',
                 'Lanzamientos espaciales y satélites (Launch Library 2, CelesTrak)',
                 'Búsqueda web cuando está configurada (Tavily)'],
     'data_en': ['What the other five agents bring, at the moment you ask',
                 'Research status: queue, daily budget and available AI providers',
                 'Space launches and satellites (Launch Library 2, CelesTrak)',
                 'Web search when configured (Tavily)'],
     'outputs_es': ['La respuesta en el chat, con fuentes y hora', 'Qué aportó cada agente',
                    'Las ventanas que abren solas a los costados del chat'],
     'outputs_en': ['The answer in the chat, with sources and time', 'What each agent contributed',
                    'The windows that open by themselves beside the chat'],
     'research_types': [], 'run_types': [], 'windows': []},
    {'id': 'analista', 'es': 'Analista', 'en': 'Analyst', 'role_es': 'Fundamentales', 'role_en': 'Fundamentals',
     'does_es': ('Mira si el negocio es sano: ventas y su crecimiento, márgenes, caja y deuda, y si el precio ya '
                 'refleja todo eso frente a empresas parecidas. También cómo le afectan las tasas de interés y el '
                 'ciclo económico.'),
     'does_en': ('Checks whether the business is healthy: revenue and its growth, margins, cash and debt, and whether '
                 'the price already reflects all that versus similar companies. Also how interest rates and the '
                 'economic cycle affect it.'),
     'chat_es': ['En el chat: la ficha de la empresa con precio y capitalización en vivo, su riesgo de red (NRS) y sus '
                 'conclusiones vigentes'],
     'chat_en': ['In the chat: the company profile with live price and market cap, its network risk (NRS) and its '
                 'current conclusions'],
     'outputs_es': ['Precio, capitalización y riesgo de red de la empresa',
                    'Conclusiones con evidencia citada, plazo y confianza calculada',
                    'La ventana «En una mirada»'],
     'outputs_en': ['Price, market cap and network risk of the company',
                    'Conclusions with cited evidence, horizon and computed confidence',
                    'The "At a glance" window'],
     'research_types': ['fundamental', 'macro'], 'run_types': ['fundamental', 'macro'], 'windows': ['glance']},
    {'id': 'radar', 'es': 'Radar', 'en': 'Radar', 'role_es': 'Noticias y eventos', 'role_en': 'News & events',
     'does_es': ('Vigila lo que pasa en el mundo: noticias de la empresa, conflictos, sanciones, controles de '
                 'exportación, desastres y cripto. Separa lo confirmado de los rumores y te dice qué puede mover '
                 'el precio pronto.'),
     'does_en': ('Watches what happens in the world: company news, conflicts, sanctions, export controls, disasters '
                 'and crypto. It separates what is confirmed from rumors and tells you what may move the price soon.'),
     'chat_es': ['En el chat: titulares recientes con enlace, eventos del World Monitor (GDELT, USGS, NASA, OFAC, '
                 'controles de exportación de EE. UU.) y escenarios «qué pasa si…» sobre el grafo'],
     'chat_en': ['In the chat: recent headlines with links, World Monitor events (GDELT, USGS, NASA, OFAC, US export '
                 'controls) and "what if…" scenarios on the graph'],
     'outputs_es': ['Titulares recientes con su medio y enlace', 'Eventos del mundo que pueden tocar a tus empresas',
                    'Conclusiones de corto y mediano plazo'],
     'outputs_en': ['Recent headlines with outlet and link', 'World events that may touch your companies',
                    'Short- and medium-term conclusions'],
     'research_types': ['news', 'geopolitical', 'crypto'], 'run_types': ['news', 'geopolitical', 'crypto'],
     'windows': []},
    {'id': 'cadena', 'es': 'Cadena', 'en': 'Chain', 'role_es': 'Cadena de suministro', 'role_en': 'Supply chain',
     'does_es': ('Sigue de quién depende cada empresa y a quién abastece: proveedores críticos o únicos, '
                 'concentración por país y cuellos de botella. Si un proveedor falla, te dice quién sufre y cuánto.'),
     'does_en': ('Tracks whom each company depends on and whom it supplies: critical or single suppliers, country '
                 'concentration and bottlenecks. If a supplier fails, it tells you who suffers and how much.'),
     'chat_es': ['En el chat: proveedores y clientes del grafo y el modelo de flujo de Khipus (exposición directa e '
                 'indirecta, capitalización aguas abajo en riesgo)'],
     'chat_en': ['In the chat: graph suppliers and customers and the Khipus flow model (direct and indirect '
                 'exposure, downstream market cap at risk)'],
     'outputs_es': ['Proveedores y clientes clave con su peso', 'De dónde le llega el riesgo (también indirecto)',
                    'La ventana «Cadena de suministro»'],
     'outputs_en': ['Key suppliers and customers with their weight', 'Where its risk comes from (also indirect)',
                    'The "Supply chain" window'],
     'research_types': ['supply_chain'], 'run_types': ['supply_chain'], 'windows': ['supplychain']},
    {'id': 'tecnico', 'es': 'Técnico', 'en': 'Technical', 'role_es': 'Precio y momento', 'role_en': 'Price & momentum',
     'does_es': ('Lee el precio: tendencia, impulso, volatilidad y cuánto cayó desde su máximo, comparado con el '
                 'S&P 500. También observa riesgos medibles como deuda, concentración y volatilidad. Solo plazos '
                 'cortos: no adivina precios a largo plazo.'),
     'does_en': ('Reads the price: trend, momentum, volatility and how far it fell from its high, versus the S&P 500. '
                 'It also watches measurable risks such as debt, concentration and volatility. Short horizons only: '
                 'it does not guess long-term prices.'),
     'chat_es': ['En el chat: los movimientos del día (Yahoo Finance, cada ~15 min) y el riesgo de una cartera con '
                 'precios diarios reales de 1 año (volatilidad, VaR, peor caída)'],
     'chat_en': ['In the chat: today\'s moves (Yahoo Finance, every ~15 min) and the risk of a portfolio with 1 year '
                 'of real daily prices (volatility, VaR, max drawdown)'],
     'outputs_es': ['Qué sube y qué baja hoy', 'Riesgo de tu cartera en números', 'Conclusiones de corto plazo'],
     'outputs_en': ['What is up and down today', 'Your portfolio risk in numbers', 'Short-term conclusions'],
     'research_types': ['technical', 'risk_observation'], 'run_types': ['technical', 'risk_observation'],
     'windows': []},
    {'id': 'comite', 'es': 'Comité', 'en': 'Committee', 'role_es': 'Decisiones', 'role_en': 'Decisions',
     'does_es': ('Reúne las conclusiones de todos los analistas, pesa cada una por su confianza y por el historial '
                 'de aciertos de quien la dijo, y calcula una convicción de −100 (en contra) a +100 (a favor). Si hay '
                 'datos suficientes propone comprar, mantener o vender, y SIEMPRE espera tu aprobación.'),
     'does_en': ('Gathers every analyst\'s conclusions, weighs each one by its confidence and by the track record of '
                 'who said it, and computes a conviction from −100 (against) to +100 (for). With enough data it '
                 'proposes to buy, hold or sell, and it ALWAYS waits for your approval.'),
     'data_es': ['Las conclusiones vigentes de todos los analistas y sus contradicciones',
                 'El historial de aciertos de cada analista frente al S&P 500',
                 'Precio en vivo y riesgo de la acción (volatilidad, peor caída, beta)',
                 'Tu mandato y tu posición, solo si operas con un cliente'],
     'data_en': ['Every analyst\'s current conclusions and their contradictions',
                 'Each analyst\'s track record versus the S&P 500',
                 'Live price and the stock\'s risk (volatility, max drawdown, beta)',
                 'Your mandate and position, only if you trade for a client'],
     'chat_es': ['En el chat: el último memo del comité, la pizarra de conclusiones y el historial de aciertos'],
     'chat_en': ['In the chat: the latest committee memo, the conclusions board and the track record'],
     'outputs_es': ['Convicción de −100 a +100, por plazo', 'Una propuesta que requiere tu aprobación',
                    'La ventana «Convicción de tus agentes»'],
     'outputs_en': ['Conviction from −100 to +100, by horizon', 'A proposal that needs your approval',
                    'The "Your agents\' conviction" window'],
     'research_types': [], 'run_types': ['committee'], 'windows': ['conviction']},
)
AGENT_IDS = tuple(p['id'] for p in PROFILES)

HELP = {
    'hit_rate_es': ('Aciertos: de las conclusiones que ya llegaron a su fecha, cuántas acertaron la dirección del '
                    'precio frente al S&P 500.'),
    'hit_rate_en': ('Hit rate: of the conclusions that reached their date, how many got the price direction right '
                    'versus the S&P 500.'),
    'brier_es': 'Brier: error de la confianza que declaró (0 = perfecto; 0,25 = como tirar una moneda).',
    'brier_en': 'Brier: error of the confidence it stated (0 = perfect; 0.25 = like flipping a coin).',
    'reliability_es': ('Fiabilidad: el peso que el comité le da a sus conclusiones (0,5 = neutral, sin historial; '
                       'sube con aciertos).'),
    'reliability_en': ('Reliability: the weight the committee gives its conclusions (0.5 = neutral, no record; it '
                       'rises with hits).'),
}


def _now():
    return datetime.now(timezone.utc)


def _n_companies():
    try:
        from core.entities import get_index
        n = len(get_index().get('nodos') or {})
        return n or None
    except Exception:  # noqa: BLE001
        return None


def _need_lines(research_types, n):
    """Datos que el armador de contexto REALMENTE trae para estos tipos (research/context.AGENT_NEEDS)."""
    try:
        from research.context import AGENT_NEEDS
    except Exception:  # noqa: BLE001
        AGENT_NEEDS = {}
    needs = set()
    for t in research_types:
        needs.update(AGENT_NEEDS.get(t) or ())
    keys = [k for k in NEED_ORDER if k in needs] + sorted(k for k in needs if k not in NEED_ORDER)
    nn_es = f'{n:,}'.replace(',', '.') if n else '~950'
    nn_en = f'{n:,}' if n else '~950'
    es, en = [], []
    for k in keys:
        a, b = NEED_TEXT.get(k, (k, k))
        es.append(a.replace('{n}', nn_es))
        en.append(b.replace('{n}', nn_en))
    if keys:
        es.append(DEEP_WEB[0])
        en.append(DEEP_WEB[1])
    return keys, es, en


def _tools_for(agent_id):
    """Herramientas del chat de este agente: el MISMO mapa que el progreso del chat."""
    try:
        from core import khipu_chat as kc
        avail = kc.tool_names()
        own = [t for t in avail if kc.tool_agent(t) == agent_id and t != 'ask_agent']
        if agent_id != 'khipu' and 'ask_agent' in avail:
            own.append('ask_agent')      # @analista: el puesto responde con sus propias conclusiones
        return own
    except Exception as e:  # noqa: BLE001
        log.info('agents_api tools: %s', type(e).__name__)
        return []


def _pct_txt(x, lang):
    if x is None:
        return None
    s = f'{x * 100:.0f}'
    return f'{s} %' if lang == 'es' else f'{s}%'


def aggregate_track(tr, research_types, scope='agents'):
    """Historial de una mascota a partir de research/outcomes.track_record (puede agrupar varios analistas).
    scope='overall' usa el historial COMBINADO (el comité no se califica por sí mismo)."""
    try:
        from research.outcomes import MIN_N, reliability
    except Exception:  # noqa: BLE001
        MIN_N = 5

        def reliability(h, n, k=None):
            return round((h + 10 * 0.5) / (n + 10), 4)
    if scope == 'overall':
        ov = dict((tr or {}).get('overall') or {})
        n, hits, brier = int(ov.get('n_scored') or 0), int(ov.get('hits') or 0), ov.get('brier')
        it_n = sum(int((a.get('interim') or {}).get('n_scored') or 0) for a in (tr or {}).get('agents') or [])
        it_h = sum(int((a.get('interim') or {}).get('hits') or 0) for a in (tr or {}).get('agents') or [])
    else:
        rows = [a for a in (tr or {}).get('agents') or [] if a.get('agent_type') in research_types]
        n = sum(int(a.get('n_scored') or 0) for a in rows)
        hits = sum(int(a.get('hits') or 0) for a in rows)
        bw = [(a.get('brier'), int(a.get('n_scored') or 0)) for a in rows if a.get('brier') is not None]
        brier = round(sum(b * w for b, w in bw) / sum(w for _b, w in bw), 4) if bw and sum(w for _b, w in bw) else None
        it_n = sum(int((a.get('interim') or {}).get('n_scored') or 0) for a in rows)
        it_h = sum(int((a.get('interim') or {}).get('hits') or 0) for a in rows)
    min_n = int((tr or {}).get('min_n') or MIN_N)
    rate = round(hits / n, 4) if n else None
    out = {'n_scored': n, 'hits': hits, 'hit_rate': rate, 'brier': brier,
           'reliability': reliability(hits, n) if n else 0.5,
           'sufficient': n >= min_n, 'min_n': min_n, 'interim': {'n_scored': it_n, 'hits': it_h},
           'benchmark': (tr or {}).get('benchmark') or 'SPY'}
    if n == 0:
        es = 'Sin historial suficiente todavía: ninguna de sus conclusiones llegó aún a su fecha de evaluación.'
        en = 'No track record yet: none of its conclusions has reached its evaluation date.'
        if it_n:
            es += f' Señal temprana: {it_h} de {it_n} van bien (no cuenta hasta el cierre).'
            en += f' Early signal: {it_h} of {it_n} on track (does not count until the close).'
    elif n < min_n:
        es = (f'Historial corto: {hits} aciertos de {n} conclusiones calificadas. Hacen falta al menos {min_n} para '
              'confiar en el número.')
        en = (f'Short record: {hits} hits out of {n} scored conclusions. At least {min_n} are needed before trusting '
              'the number.')
    else:
        es = f'Acertó {hits} de {n} conclusiones calificadas ({_pct_txt(rate, "es")}) frente al S&P 500.'
        en = f'Got {hits} of {n} scored conclusions right ({_pct_txt(rate, "en")}) versus the S&P 500.'
    if scope == 'overall':
        es = 'El comité no se califica solo: es el historial combinado de los analistas en que se basa. ' + es
        en = 'The committee is not scored on its own: this is the combined record of the analysts it relies on. ' + en
    out['note_es'], out['note_en'] = es, en
    return out


def _khipu_track():
    return {'applicable': False, 'n_scored': 0, 'hits': 0, 'hit_rate': None, 'brier': None, 'reliability': None,
            'sufficient': False, 'note_es': 'Khipu no hace predicciones propias: reúne y explica lo que dicen los '
                                            'demás agentes, así que no tiene historial que calificar.',
            'note_en': 'Khipu makes no predictions of its own: it gathers and explains what the other agents say, so '
                       'it has no record to score.'}


def _db_ok():
    try:
        from ontology.db import ontology_available
        return bool(ontology_available())
    except Exception:  # noqa: BLE001
        return False


def _db_part():
    """→ (track_record, stats por agent_type, stats de khipu, memos 30 d) desde Postgres (lanza si falla)."""
    from sqlalchemy import case, func

    from ontology.db import session_scope
    from research import outcomes
    from research.models import AgentRun, AIUsage, CommitteeMemo
    since = _now() - timedelta(days=30)
    with session_scope() as s:
        tr = outcomes.track_record(s)
        runs = {}
        for at, n, cl, cost, lat_sum, lat_n, failed in (
                s.query(AgentRun.agent_type, func.count(AgentRun.id),
                        func.coalesce(func.sum(AgentRun.claims_generated), 0),
                        func.coalesce(func.sum(AgentRun.est_cost_usd), 0.0),
                        func.coalesce(func.sum(AgentRun.latency_ms), 0), func.count(AgentRun.latency_ms),
                        func.coalesce(func.sum(case((AgentRun.status == 'failed', 1), else_=0)), 0))
                .filter(AgentRun.started_at >= since).group_by(AgentRun.agent_type).all()):
            runs[at] = {'runs': int(n or 0), 'claims': int(cl or 0), 'cost_usd': float(cost or 0.0),
                        'lat_sum': float(lat_sum or 0.0), 'lat_n': int(lat_n or 0), 'failed': int(failed or 0)}
        k = s.query(func.count(AIUsage.id), func.coalesce(func.sum(AIUsage.cost_usd), 0.0), func.avg(AIUsage.ms)) \
             .filter(AIUsage.at >= since, AIUsage.feature == 'khipu_chat').one()
        khipu = {'runs': int(k[0] or 0), 'claims': None, 'cost_usd': round(float(k[1] or 0.0), 4),
                 'avg_latency_ms': int(k[2]) if k[2] is not None else None, 'failed': None, 'basis': 'ai_usage',
                 'unit_es': 'llamadas de IA del chat', 'unit_en': 'chat AI calls'}
        memos = int(s.query(func.count(CommitteeMemo.id)).filter(CommitteeMemo.created_at >= since).scalar() or 0)
    return tr, runs, khipu, memos


def _stats_for(run_types, runs):
    agg = {'runs': 0, 'claims': 0, 'cost_usd': 0.0, 'lat_sum': 0.0, 'lat_n': 0, 'failed': 0}
    for t in run_types:
        r = runs.get(t)
        if not r:
            continue
        for k in agg:
            agg[k] += r[k]
    return {'runs': agg['runs'], 'claims': agg['claims'], 'cost_usd': round(agg['cost_usd'], 4),
            'avg_latency_ms': int(agg['lat_sum'] / agg['lat_n']) if agg['lat_n'] else None, 'failed': agg['failed'],
            'basis': 'agent_runs', 'unit_es': 'investigaciones', 'unit_en': 'research runs',
            'cost_note_es': 'Costo ESTIMADO por tokens (💰 Gasto IA tiene el detalle).',
            'cost_note_en': 'ESTIMATED cost from tokens (💰 AI spend has the detail).'}


def build_profiles(lang='es'):
    lang = 'en' if str(lang or '').lower().startswith('en') else 'es'
    n = _n_companies()
    db = _db_ok()
    tr = runs = khipu_stats = None
    memos = None
    db_error = None
    if db:
        try:
            tr, runs, khipu_stats, memos = _db_part()
        except Exception as e:  # noqa: BLE001 — sin historial, pero el endpoint responde
            db_error = type(e).__name__
            log.warning('agents_api: historial no disponible (%s)', db_error)
            tr = runs = khipu_stats = None
    agents = []
    for p in PROFILES:
        keys, data_es, data_en = _need_lines(p['research_types'], n)
        if p.get('data_es'):                               # Khipu y el Comité: lo que leen está en su ficha
            data_es, data_en = list(p['data_es']), list(p['data_en'])
        data_es = data_es + list(p.get('chat_es') or [])
        data_en = data_en + list(p.get('chat_en') or [])
        a = {'id': p['id'], 'es': p['es'], 'en': p['en'], 'role_es': p['role_es'], 'role_en': p['role_en'],
             'does_es': p['does_es'], 'does_en': p['does_en'], 'data_es': data_es, 'data_en': data_en,
             'data_keys': keys, 'outputs_es': list(p['outputs_es']), 'outputs_en': list(p['outputs_en']),
             'research_types': list(p['research_types']), 'tools': _tools_for(p['id']),
             'windows': list(p['windows']), 'track': None, 'stats_30d': None}
        if tr is not None:
            if p['id'] == 'khipu':
                a['track'] = _khipu_track()
            elif p['id'] == 'comite':
                a['track'] = aggregate_track(tr, [], scope='overall')
            else:
                a['track'] = aggregate_track(tr, p['research_types'])
        if runs is not None:
            if p['id'] == 'khipu':
                a['stats_30d'] = dict(khipu_stats)
            else:
                a['stats_30d'] = _stats_for(p['run_types'], runs)
                if p['id'] == 'comite':
                    a['stats_30d'].update(memos=memos, unit_es='sesiones del comité (puestos y presidente)',
                                          unit_en='committee sessions (seats and chair)')
        # comodidad para el cliente: los textos en el idioma pedido
        a.update(name=a[lang], role=a['role_' + lang], does=a['does_' + lang], data=a['data_' + lang],
                 outputs=a['outputs_' + lang])
        agents.append(a)
    out = {'agents': agents, 'db': bool(db and tr is not None), 'lang': lang, 'as_of': _now().isoformat(),
           'help': HELP,
           'note_es': ('Información, no recomendación. Las preferencias de los agentes solo cambian lo que ves; '
                       'nunca las decisiones del comité ni el tamaño de una orden.'),
           'note_en': ('Information, not advice. Agent preferences only change what you see; never the committee\'s '
                       'decisions or the size of an order.')}
    if db_error:
        out['db_error'] = db_error
    return out


@agents_bp.route('/profiles', methods=['GET'])
@rate_limit(120, 300)
def agent_profiles_endpoint():
    lang = 'en' if str(request.args.get('lang') or '').lower().startswith('en') else 'es'
    now = time.monotonic()
    with _LOCK:
        hit = _CACHE.get(lang)
    if hit and now - hit[0] < CACHE_TTL_S:
        return jsonify(hit[1])
    try:
        payload = build_profiles(lang)
    except Exception as e:  # noqa: BLE001 — nunca un 500: perfiles estáticos sin historial
        log.warning('agents_api: %s', type(e).__name__)
        return jsonify({'agents': [], 'db': False, 'lang': lang, 'as_of': _now().isoformat(),
                        'error': 'no se pudieron armar los perfiles', 'error_en': 'could not build the profiles'}), 200
    with _LOCK:
        _CACHE[lang] = (time.monotonic(), payload)
    return jsonify(payload)


def clear_cache():
    with _LOCK:
        _CACHE.clear()
