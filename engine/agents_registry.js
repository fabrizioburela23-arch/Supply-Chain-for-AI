/* ============================================================================
   engine/agents_registry.js — EL registro de agentes de Khipus (limpieza 2026-10-11)

   ÚNICA fuente de: las 6 mascotas (nombre, rol, colores, puestos que les pertenecen), los
   puestos del comité/investigación (ícono y nombres), las palabras de una mención (@radar,
   @cadena…) y qué mascota "hace" cada herramienta del chat. Antes el mismo mapa estaba
   copiado a mano en ~12 sitios (mascot.js, khipu_chat.js, committee.js, core/khipu_chat.py,
   research/agent_skills.py, deliberation.py, ask_agent.py, runner.py…) y podían divergir.

   Lo leen: el navegador (window.KHIPU_AGENTS, cargado ANTES de mascot.js), las pruebas en Node
   (globalThis) y Python (core/agents_registry.py extrae el objeto JSON de abajo). Por eso lo que va
   entre `KHIPU_AGENTS = ` y el `;` final debe ser JSON ESTRICTO (comillas dobles, sin
   comentarios ni comas colgantes) — tests/test_agents_registry.py lo verifica.
   ============================================================================ */
(typeof window !== 'undefined' ? window : globalThis).KHIPU_AGENTS = {
  "agents": [
    {"id": "khipu", "es": "Khipu", "en": "Khipu", "role_es": "Te responde", "role_en": "Answers you",
     "colors": ["#f07fa0", "#7a4ce8", "#ff8746", "#c23a8c"], "ink": "#c23a8c",
     "seats": ["khipu", "brain"]},
    {"id": "analista", "es": "Analista", "en": "Analyst", "role_es": "Fundamentales", "role_en": "Fundamentals",
     "colors": ["#7d8be6", "#5b81e4", "#4054cf", "#6b9ff4"], "ink": "#4054cf",
     "seats": ["fundamental", "fundamentals", "macro", "valuation"]},
    {"id": "radar", "es": "Radar", "en": "Radar", "role_es": "Noticias y eventos", "role_en": "News & events",
     "colors": ["#f78189", "#f26570", "#e63e52", "#f6808a"], "ink": "#e63e52",
     "seats": ["news", "sentiment", "geopolitical", "geo", "events", "crypto"]},
    {"id": "cadena", "es": "Cadena", "en": "Chain", "role_es": "Cadena de suministro", "role_en": "Supply chain",
     "colors": ["#4cb1ab", "#56b87c", "#1b9386", "#83cd70"], "ink": "#1b9386",
     "seats": ["supply_chain", "chain", "supply"]},
    {"id": "tecnico", "es": "Técnico", "en": "Technical", "role_es": "Precio y momento", "role_en": "Price & momentum",
     "colors": ["#f7cc63", "#f2bc3a", "#e6a117", "#f5c54a"], "ink": "#e6a117",
     "seats": ["technical", "momentum", "risk", "risk_observation", "risk_officer", "market"]},
    {"id": "comite", "es": "Comité", "en": "Committee", "role_es": "Decisiones", "role_en": "Decisions",
     "colors": ["#bc78e5", "#9f60e5", "#7a3fe0", "#d88ae6"], "ink": "#7a3fe0",
     "seats": ["committee", "chair", "portfolio", "president", "quant", "mandate", "all"]}
  ],
  "seats": {
    "fundamental": {"icon": "📊", "es": "Analista fundamental", "en": "Fundamental analyst", "short_es": "Fundamental", "short_en": "Fundamental",
                    "badge_es": "Fundamental", "badge_en": "Fundamental", "call_es": "fundamental", "call_en": "fundamentals"},
    "technical": {"icon": "📈", "es": "Analista técnico", "en": "Technical analyst", "short_es": "Técnico", "short_en": "Technical",
                  "badge_es": "Precio", "badge_en": "Price"},
    "news": {"icon": "📰", "es": "Analista de noticias", "en": "News analyst", "short_es": "Noticias", "short_en": "News",
             "badge_es": "Noticias", "badge_en": "News", "call_es": "noticias", "call_en": "news"},
    "supply_chain": {"icon": "🔗", "es": "Analista de cadena de suministro", "en": "Supply-chain analyst", "short_es": "Cadena de suministro", "short_en": "Supply chain",
                     "badge_es": "Suministro", "badge_en": "Supply"},
    "geopolitical": {"icon": "🗺️", "es": "Analista geopolítico", "en": "Geopolitical analyst", "short_es": "Geopolítico", "short_en": "Geopolitical",
                     "badge_es": "Geopolítica", "badge_en": "Geopolitics", "call_es": "geopolítica", "call_en": "geopolitics"},
    "macro": {"icon": "🌐", "es": "Analista macro", "en": "Macro analyst", "short_es": "Macro", "short_en": "Macro",
              "badge_es": "Macro", "badge_en": "Macro", "call_es": "macro", "call_en": "macro"},
    "crypto": {"icon": "₿", "es": "Analista cripto", "en": "Crypto analyst", "short_es": "Cripto", "short_en": "Crypto",
               "badge_es": "Cripto", "badge_en": "Crypto", "call_es": "cripto", "call_en": "crypto"},
    "risk_observation": {"icon": "⚠️", "es": "Analista de riesgos", "en": "Risk analyst", "short_es": "Riesgos", "short_en": "Risk",
                         "badge_es": "Riesgos", "badge_en": "Risks", "call_es": "riesgos", "call_en": "risks"},
    "chair": {"icon": "🏛", "es": "Presidente", "en": "Chair", "desk": true, "badge_es": "Presidencia", "badge_en": "Chair"},
    "market": {"icon": "📡", "es": "Mesa de mercado", "en": "Market desk", "desk": true, "badge_es": "Mesa de mercado", "badge_en": "Market desk"},
    "risk_officer": {"icon": "🛡️", "es": "Oficial de riesgo", "en": "Risk officer", "desk": true, "badge_es": "Oficial de riesgo", "badge_en": "Risk officer"},
    "quant": {"icon": "🧮", "es": "Núcleo cuantitativo", "en": "Quant core", "desk": true, "badge_es": "Cuantitativo", "badge_en": "Quant"},
    "mandate": {"icon": "👤", "es": "Mandato del cliente", "en": "Client mandate", "desk": true, "badge_es": "Mandato", "badge_en": "Mandate"}
  },
  "mention_words": {
    "fundamental": "fundamental", "fundamentales": "fundamental", "financiero": "fundamental", "financiera": "fundamental",
    "balance": "fundamental", "contable": "fundamental", "analista": "fundamental", "analyst": "fundamental",
    "tecnico": "technical", "tecnica": "technical", "technical": "technical", "grafico": "technical", "chartista": "technical",
    "noticias": "news", "news": "news", "prensa": "news", "periodista": "news", "radar": "news",
    "cadena": "supply_chain", "suministro": "supply_chain", "supply": "supply_chain", "supply_chain": "supply_chain",
    "proveedores": "supply_chain", "chain": "supply_chain",
    "geopolitico": "geopolitical", "geopolitica": "geopolitical", "geopolitical": "geopolitical", "geo": "geopolitical",
    "macro": "macro", "macroeconomico": "macro", "economista": "macro",
    "cripto": "crypto", "crypto": "crypto",
    "todos": "all", "todas": "all", "all": "all", "comite": "all", "committee": "all", "analistas": "all", "everyone": "all"
  },
  "tool_agent": {
    "get_company": "analista", "search_companies": "analista", "get_research": "analista", "get_claim_evidence": "analista",
    "get_supply_chain": "cadena", "rank_companies": "cadena", "run_scenario": "cadena",
    "get_news": "radar", "get_world_events": "radar", "web_search": "radar", "scenario_exposure": "radar",
    "market_movers": "tecnico", "get_option_greeks": "tecnico", "get_risk_report": "tecnico", "get_history": "tecnico",
    "get_committee_memo": "comite", "get_conclusions_board": "comite", "get_track_record": "comite"
  }
};
