"""research/agents/registry.py — los 8 agentes de Phase 2.

Qué lee cada uno lo decide research/context.AGENT_NEEDS (misma clave
agent_type); qué eventos lo activan, research/router.py (subscribed_events).
"""
from research.agents.base import Agent

AGENTS = [
    Agent('fundamental', 'FundamentalAgent', 'fundamentales de empresas',
          focus=('Ingresos y su crecimiento, márgenes (bruto/operativo/neto), flujo de caja libre, balance '
                 '(deuda vs caja), dilución y valuación relativa (P/E) según los estados anuales y el perfil '
                 'de mercado. Distingue tendencias de varios años (LONG_TERM/STRUCTURAL) de lo reciente '
                 '(MEDIUM_TERM). Señala cuando un dato del catálogo contradice los estados financieros.'),
          capabilities=('read:financials', 'read:market_profile', 'read:news', 'read:graph', 'read:claims'),
          permitted_tools=('financials', 'live_profile', 'news', 'graph', 'catalog'),
          subscribed_events=('USER_RESEARCH', 'EARNINGS', 'FILING', 'GUIDANCE_CHANGE'),
          default_horizons=('MEDIUM_TERM', 'LONG_TERM', 'STRUCTURAL')),
    Agent('news', 'NewsAgent', 'noticias y flujo de información',
          focus=('Qué dicen las noticias recientes del paquete: hechos nuevos, cambios de guía, acuerdos, '
                 'litigios, lanzamientos. Separa lo confirmado de rumores; una sola nota de un agregador no '
                 'basta para una conclusión fuerte. Horizontes típicos: SHORT_TERM y MEDIUM_TERM.'),
          capabilities=('read:news', 'read:claims'), permitted_tools=('news', 'catalog'),
          subscribed_events=('USER_RESEARCH', 'NEWS', 'EARNINGS', 'PRICE_ANOMALY'),
          default_horizons=('SHORT_TERM', 'MEDIUM_TERM')),
    Agent('technical', 'TechnicalAgent', 'comportamiento del precio',
          focus=('Momentum, tendencia y volatilidad a partir de los indicadores de precio calculados en el '
                 'paquete (rendimientos, posición en el rango de 52 semanas, volatilidad). Solo INTRADAY o '
                 'SHORT_TERM. No extrapoles el precio a largo plazo.'),
          capabilities=('read:prices', 'read:news'), permitted_tools=('live_profile', 'candles', 'news'),
          subscribed_events=('USER_RESEARCH', 'PRICE_ANOMALY', 'CRYPTO_EVENT'),
          default_horizons=('INTRADAY', 'SHORT_TERM')),
    Agent('supply_chain', 'SupplyChainAgent', 'cadena de suministro',
          focus=('Dependencias de la entidad en el grafo: proveedores críticos o únicos, concentración '
                 'geográfica, clientes grandes, cuellos de botella. Nombra en affected_entities los ids de '
                 'vecinos afectados. Horizontes típicos: MEDIUM_TERM a STRUCTURAL.'),
          capabilities=('read:graph', 'read:news', 'read:market_profile'),
          permitted_tools=('graph', 'catalog', 'news', 'live_profile'),
          subscribed_events=('USER_RESEARCH', 'GEOPOLITICAL_EVENT', 'SUPPLY_SHOCK', 'FACTOR_FIRED'),
          default_horizons=('MEDIUM_TERM', 'LONG_TERM', 'STRUCTURAL')),
    Agent('geopolitical', 'GeopoliticalAgent', 'geopolítica',
          focus=('Exposición a países, sanciones, controles de exportación, conflictos y política industrial '
                 'según la ficha, el grafo y las noticias del paquete.'),
          capabilities=('read:graph', 'read:news'), permitted_tools=('graph', 'catalog', 'news'),
          subscribed_events=('GEOPOLITICAL_EVENT', 'SANCTION', 'FACTOR_FIRED'),
          default_horizons=('SHORT_TERM', 'MEDIUM_TERM', 'STRUCTURAL')),
    Agent('macro', 'MacroAgent', 'macroeconomía',
          focus=('Sensibilidad de la entidad a tasas, inflación, ciclo de inversión y crédito, según su sector '
                 'y relaciones. No inventes datos macro que no estén en el paquete.'),
          capabilities=('read:graph', 'read:news'), permitted_tools=('graph', 'catalog', 'news'),
          subscribed_events=('MACRO_EVENT', 'GEOPOLITICAL_EVENT', 'FACTOR_FIRED'),
          default_horizons=('MEDIUM_TERM', 'LONG_TERM')),
    Agent('crypto', 'CryptoAgent', 'criptoactivos',
          focus='Solo para activos cripto: adopción, regulación y flujo según el paquete.',
          capabilities=('read:news',), permitted_tools=('news', 'catalog'),
          subscribed_events=('CRYPTO_EVENT',), default_horizons=('SHORT_TERM', 'MEDIUM_TERM')),
    Agent('risk_observation', 'RiskObservationAgent', 'observación de riesgos',
          focus=('Riesgos observables (no recomendaciones): concentración, apalancamiento, dependencia de un '
                 'cliente/proveedor, volatilidad, litigios. Cada riesgo con su falsificador.'),
          capabilities=('read:market_profile', 'read:graph', 'read:news'),
          permitted_tools=('live_profile', 'graph', 'news', 'catalog'),
          subscribed_events=('USER_RESEARCH', 'EARNINGS', 'PRICE_ANOMALY'),
          default_horizons=('SHORT_TERM', 'MEDIUM_TERM', 'LONG_TERM')),
]

AGENTS_BY_TYPE = {a.agent_type: a for a in AGENTS}


def get_agent(agent_type):
    return AGENTS_BY_TYPE.get(agent_type)
