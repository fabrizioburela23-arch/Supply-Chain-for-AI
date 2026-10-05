# ESTADO — Khipus AI Finance Intelligence · Ontología (Palantir-style)

Archivo vivo. Cada sesión de trabajo en la ontología lee esto primero y lo
actualiza al terminar. Ver `ROADMAP_KHIPUS_ONTOLOGIA.md` (adjuntado por el
usuario) para el plan completo por fases, y `docs/AUDITORIA.md` para las
correcciones de arquitectura respecto al roadmap original (backend real =
Flask/Python, no Node; `/v1/*` ya es la API pública monetizada; Neo4j Aura ya
está conectado).

---

# SESIÓN 2026-10-05 (dd) — "RENDIMIENTO DE MI CARTERA" COMO GRÁFICO SIN IA (sw v238-v239)

- Mapa (sw v239): tooltip con ingresos 12 m EN VIVO (●) y empleados en vivo; tamaño de las privadas de la
  tabla MKT_CAP_EST (OpenAI, Anthropic, SpaceX…) con la valuación verificada. Las demás NO se agrandaron a
  propósito (cambiaría densidad/etiquetas del mapa): decisión pendiente de Fabrizio.

- core/live_fundamentals: tras un redeploy (memoria vacía) la tanda es 3× (CATCHUP) mientras haya empresas
  nunca pedidas → las 568 en ~25 min en vez de ~1 h. Producción: 38/40 con dato por tanda.

- engine/localcharts.js: `RE.perf` (rendimiento/ganancia/pérdida/retorno/cómo va/performance) + cartera →
  `P.pfPerf` → intención 'trend' → `buildPortfolioPerfAsync`: Σ acciones × cierre REAL de cada día
  (/api/candles; cada posición arrastra su último cierre si su bolsa no abrió) + efectivo; subtítulo con el %
  del periodo y "hoy vs lo que pagaste" (precio EN VIVO con quotePx, si no el último cierre). Cartera = la del
  chip del chat (kh_chat_pf_src, vía KhipuPortfolioCommittee._positionsFor) o Mercado → Mi cartera; NUNCA el
  bróker (pediría PIN). Posiciones sin cotización se nombran en la nota. "¿Por qué perdió…?" sigue a la IA.
  El reparto de "mi cartera" usa quotePx (antes q.close).
- Test: tests/test_localcharts_intents.py (+ tests/js/localcharts_pfperf.js).

# SESIÓN 2026-10-05 (cc) — GRÁFICOS: DATOS EN VIVO + MÁS PREGUNTAS SIN IA (sw v237)

- engine/localcharts.js: ingresos = revenue_ttm_usd_b en vivo (KhipuLiveFund) antes que revenue_2025;
  fuente rotulada "datos EN VIVO … donde ya llegaron; si no, catálogo". Parser: STOP + promedio/media/
  desglosado/semiconductores…; filtro por SECTOR (`SECTOR_WORDS` → P.sectors, aplicado en pool() y en el
  título); MATERIAS PRIMAS e ÍNDICES (`COMMODITIES`: oro GC=F, WTI, Brent, cobre, gas, plata, uranio URA,
  S&P 500, Nasdaq, SOX) → `buildCommodityAsync` vía /api/candles. Banco de 25 preguntas probado.
- También hoy: expediente cripto con cifras vivas (liveIntelLine), Insights con crecimiento real, Guía con
  conteos del catálogo cargado.
- Tests: tests/test_localcharts_intents.py (+ tests/js/localcharts_intents.js), tests/test_live_labels_misc.py.

# SESIÓN 2026-10-05 (bb) — SIMULACIÓN "IA SIMPLE" CON DATOS EN VIVO (sw v235)

- El informe de "IA simple" (app.html `_runClaudeSim`) mandaba a la IA SOLO la frase del escenario: decía
  "no tengo el dato en vivo de Microsoft/Nvidia". Ahora agrega `buildLiveReportContext(ids)` (sim/
  scenario_builder.js): empresas del preset (o las escritas) con precio, capitalización, margen, crecimiento e
  ingresos EN VIVO (/api/company/live), privadas con su valuación verificada, + geopolítica en vivo. El
  "seed" (buildScenarioSeed) usa el mismo `buildPlayers`. La parte de arriba del War Room (motor estructural,
  sin IA) es determinista: mismo escenario → mismo gráfico.

# SESIÓN 2026-10-05 (aa) — FUNDAMENTALES EN VIVO DE TODO EL GRAFO (sw v234)

- Regla de Fabrizio: "en vivo siempre lo que varía; fijo solo lo que no cambia (fundación, productos)".
- core/live_fundamentals.py: tarea del reloj `live_fundamentals` (cada 5 min, tandas de 40 vía
  company_data.get_live_profile; faltantes primero, cada empresa ≥ 1×/día; un fallo no borra lo bueno).
  GET /api/market/live_fundamentals. `live_margin(nid)` lo usan client_nrs, portfolio_ai.nrs y
  ontology/agents._compute_server_nrs.
- app.html `window.KhipuLiveFund`: aplica margen operativo (n.margin; catálogo en n.margin_catalog,
  n.margin_live {source, as_of}), crecimiento trimestral (n.growth_live), empleados e ingresos 12 m a TODO el
  catálogo → NRS, rankings, comparador, gráficos, Insights y simulación usan lo real; invalida el NRS.
  Rótulos "en vivo"/"catálogo" en ficha, X-Ray, Terminal y comparador según haya dato vivo.
- live_facts: "AI" ya no es C3.ai; "Microsoft (Azure)" casa por "Microsoft"; hasta 6 empresas.
- Tests: tests/test_live_fundamentals.py, tests/test_live_facts_entities.py.

# SESIÓN 2026-10-05 (z) — SIMULACIÓN CON CONTEXTO EN VIVO + RÓTULOS DE ORIGEN (sw v233)

- sim/scenario_builder.js: `buildGeopoliticalContext()` ahora es async y EN VIVO (/api/world/brief 7d,
  /api/world/gpr, /api/world/policy) + un "fondo estructural" rotulado como tal; `buildSocialContext` ya no
  inventa narrativas (solo tono GDELT real, o dice que no hay datos). Presets: OpenAI sin "$250B" (usa la
  valuación verificada), Starshield sin "$500B" (SPCX + capitalización en vivo) vía `_sbValuation()`.
- Pies de página: Mercado ya no dice "EOD de Marketstack" (es Finnhub/Yahoo en vivo); disclaimer explica
  ● en vivo vs «catálogo». Comparador: Mkt cap con origen (● vivo / ✓ verificada / catálogo), margen
  rotulado "catálogo". OpenAI: rol sin "IPO ~sept 2026" (snapshot regenerado).
- Test: tests/test_scenario_live.py.

# SESIÓN 2026-10-05 (y) — NRS ACOTADO + BÚSQUEDA DEL MAPA (sw v232)

- NRS: término de margen acotado a [0,20] también en el CLIENTE (OpenAI daba 100, ahora 67) y países
  normalizados (`_nrsCountry` en app.html ≡ `core.world.nrs_country/nrs_geo/nrs_concentrated`, que usan
  client_nrs, portfolio_ai.nrs y ontology/agents._compute_server_nrs): Japón/Corea/Estados Unidos/Taiwán
  ya cuentan como Japan/Korea/EEUU/Taiwan. Se cierra la divergencia documentada cliente↔servidor.
- Mapa: pickSugg ahora llama invalidateFilterCache() — al deseleccionar quedaba encendida solo la
  empresa buscada hasta recargar.
- Tests: tests/test_map_search_reset.py; test_world (fórmula NRS) actualizado.

# SESIÓN 2026-10-05 (x) — CIFRAS VIEJAS → VERIFICADAS / EN VIVO (sw v231)

- Auditoría (agente Explore) de cifras fijas en la UI: ~40 hallazgos. Hechos los de mayor riesgo:
  · app.html `applyVerifiedValuations()` (al cargar y en DOMContentLoaded, idempotente): NODE_META.mktcap_b,
    PREIPO_INTEL.valuation e INVEST_PATH.note de privadas = nodes/private_valuations.js (mktcap_verified
    {as_of,label,source_url}; mktcap_catalog/valuation_catalog guardan lo viejo); cotizadas → nota de
    listing_status; fusionadas (xAI) sin valuación propia. Corrige ficha, panel pre-IPO, carteras
    (estimatedPrice), comparador, simulación. liveCapDot muestra "✓ fecha" para verificadas.
  · Ficha del mapa: margen y crecimiento REALES vía fillLiveMeta (operating_margin, revenue_growth_q del
    perfil en vivo); capex/backlog/proyección rotulados "catálogo". X-Ray (fundamentales) y Terminal (ficha)
    usan el mismo relleno en vivo.
- Pendientes de la auditoría: NRS geoMap con claves que no casan (Japan/Korea vs Japon/Corea; "Estados
  Unidos" 15 vs EEUU 8) — cambiaría los NRS, consultarlo; presets de simulación anclados a cifras viejas
  (OpenAI $250B, SpaceX $500B); contexto geopolítico fijo en scenario_builder; textos de nodos vencidos
  (OpenAI "IPO ~sept 2026"); pie "estimaciones (jun. 2026)".
- Pruebas locales de UI: d3/three bajados con `npm pack` al scratchpad y servidos con page.route (el CDN
  está bloqueado en el sandbox).
- Test: tests/test_verified_valuations.py.

# SESIÓN 2026-10-05 (w) — REVISIÓN DEL WORLD MONITOR CON DATOS REALES (sw v229)

- GDELT: relleno en SEGUNDO PLANO (`_backfill_loop`, hilo único, de a un lote, 24 h y luego 7 d;
  WORLD_GDELT_BACKFILL=off en tests) — cada despliegue dejaba la capa en "2 h" durante horas.
- La cinta de titulares ya no muestra los avisos de viaje (riesgo país permanente tapaba las noticias).
- "Lo más relevante": el estrecho curado lleva el tráfico vivo en el título ("· ▼ 64 % buques") y se quita
  la fila duplicada de `shipping` de ese estrecho.

# SESIÓN 2026-10-05 (v) — "ABRE MI CUENTA" OFRECE BRÓKER + TUS CARTERAS (sw v228)

- "abre mi cuenta / mi cuenta / mi portafolio" abría SIEMPRE el bróker (Alpaca: un solo ETF) y nunca las
  carteras simuladas (kh_portfolios, que sí se veían en Carteras). Ahora classify devuelve un 'command' con
  botones: 🔒 Cuenta del bróker (Alpaca) + 🧪 cada cartera (acción nueva `open_portfolio` → kh_pf_active +
  pestaña Carteras) + posiciones de Mercado. "mi bróker" sigue yendo directo al bróker.

# SESIÓN 2026-10-05 (u) — ÍNDICE GPR (Caldara-Iacoviello) EN VIVO (sw v227)

- core/gpr.py: diario (data_gpr_daily_recent.xls → valor, medias 7/30/365, percentil 1 año, 120 días) y
  mensual por país (data_gpr_export.xls → GPRC_<ISO3> vs su último año). Requiere `xlrd` (añadido a
  requirements + constraints). Caché 12 h, lo último bueno si cae (stale), prewarm lo refresca.
- GET /api/world/gpr; MCP get_world_events `gpr_index`; World Monitor: tarjeta 🌍 con valor, tendencia,
  mini-gráfico y "suben en la prensa"; países con GPR ≥ 1,5× su año suben +5 en inestabilidad.

# SESIÓN 2026-10-05 (t) — ESTRECHOS Y PAÍSES: CURADO + EN VIVO (sw v226)

- `_blend_live_chokepoint` / `_blend_live_country` (core/world.py): las capas curadas leen la caché de las
  capas vivas (sin descargar): estrecho = máx(curado, caída de buques FMI PortWatch) + `live_shipping`;
  país = máx(curado, aviso oficial nivel 3-4) + hasta +10 por eventos de conflicto/protesta GDELT 24 h en
  el país (`advisory_level`, `live_events`). Estado de la capa: `live_inputs` → la UI dice "curado + vivo".
- Índice GPR (Caldara-Iacoviello) pendiente: solo publica .xls y no hay lector en requirements.

# SESIÓN 2026-10-05 (s) — CARTERA = CONTEXTO, AGENTE = QUIÉN RESPONDE (sw v225)

- Feedback: "selecciono mi cartera y todo el comité la analiza; me quitó al @geo; ¿para qué me dice si la
  cartera está adaptada si no le pregunto? la app no se centra en lo valioso".
- engine/pickers.js: DOS chips independientes y persistentes (hasta ✕): 💼 contexto (`input._ctxPf`, selector
  de cartera) y 🤖 agente (`input._agentTok`; sin agente se muestra "💬 Khipu"). Al enviar se traducen:
  cartera+analista → "/cartera @geo …", cartera sola → "/cartera …", cartera+comité → "/cartera @comite …".
- Modos en /api/committee/portfolio/ask: sin seat → Khipu responde SOLO la pregunta con los datos (sin
  veredicto, sin tarjeta, no se guarda); seat analista → ese analista; seat 'committee' → comité con
  tarjeta (se guarda). classify: "/cartera …" = Khipu; "/comite mi cartera" y "que el comité analice…" =
  committee. Respaldo sin IA sin veredicto (`portfolio_fallback(verdict=False)`): pesos y riesgo + geopolítica.

# SESIÓN 2026-10-05 (r) — RESPUESTA ENFOCADA EN LA CARTERA + UN ANALISTA CONCRETO SOBRE TU CARTERA (sw v224)

- Bug real (captura de Fabrizio): "/cartera ¿cuáles son los riesgos geopolíticos de mi cartera?" respondió
  "se me acabó el tiempo" + conflictos genéricos del mundo. Causa: run_chat (bucle de herramientas) se iba a
  get_world_events y se quedaba sin tiempo. Ahora /api/committee/portfolio/ask usa `khipu_chat.synthesize`
  (una sola redacción con el análisis) y, si la IA falla, `portfolio_fallback()` (sobre LA CARTERA).
- `_geo_exposure()`: exposición estructural (peso por país + riesgo-país curado; estrechos de los que
  dependen las posiciones) → notes/fallback; las notes SIEMPRE dicen si hay o no geopolítica en vivo.
- Pedido: "preguntarle a un agente específico sobre mi cartera… sin todo el comité". `seat` en
  /portfolio/ask (fundamental/technical/news/supply_chain/geopolitical/macro): responde ese analista, sin
  tarjeta del comité, no se guarda como análisis. Cliente: "/cartera @geopolitico …", "@geopolitico … mi
  cartera…", y en el chip del analista un selector "sobre: empresa o tema | sobre: <cartera>".
- Tests: tests/test_chat_portfolio_agent.py ampliado.

# SESIÓN 2026-10-05 (q) — COMITÉ DE CARTERA × GEOPOLÍTICA EN VIVO (sw v223)

- `core/world.entity_geo_risks(ids)`: por empresa, solo capas en vivo/oficiales (no curadas):
  regla/sanción que la NOMBRA (policy), estrecho del que depende con caída (shipping, sev ≥ 40),
  conflicto/protesta/sismo/natural/desastre cerca de su sede CONOCIDA (hq/city), riesgo país
  oficial o corte de internet en su país. Usa la caché del World Monitor (wait 3 s).
- research/committee_api `_attach_geo` en /portfolio y /portfolio/ask → `geo_risks`; entra en
  portfolio_notes (el cerebro lo usa), en la tarjeta del chat (🌐) y en el comité (engine/pfcommittee.js
  `geoHtml`, con enlace a la fuente).
- Test: test_world_feeds::test_geopolitica_en_vivo_por_empresa_para_el_comite.

# SESIÓN 2026-10-05 (p) — GEOPOLÍTICA: CAPAS "EN PAUSA" REVIVIDAS + RIESGO PAÍS + CORTES (sw v219)

- conflict/unrest/trade ya NO usan la API GEO retirada: `core/gdelt_events.py` lee los ARCHIVOS
  CRUDOS de eventos GDELT 2.0 (data.gdeltproject.org/gdeltv2, cada 15 min, sin clave). CAMEO:
  18/19/20 (+15 con ≥3 fuentes) = conflicto, 14 = protestas, 163 = sanciones; filtro ≥2 fuentes o
  ≥5 artículos; agrupado a ~0,1°; severidad = cobertura normalizada a la ventana; descarga
  incremental (4 lotes al arrancar, luego 16/refresco, guarda 7 días); estado `coverage_hours`.
  `press_signal: true` (la UI lo dice). WORLD_GDELT_EVENTS=off vuelve a la API GEO (tests).
- `advisories` = avisos de viaje del Dpto. de Estado (nivel 3-4; país → capital vía
  core/country_geo.py), relevancia como inestabilidad (país entero).
- `outages` = Cloudflare Radar (cortes de internet) — NECESITA `CLOUDFLARE_RADAR_TOKEN` (gratis);
  sin él la capa dice "🔑 falta clave" (err_info `needs_key:<VAR>`).
- MCP get_world_events: enum + maxItems 12 + campos. Tests: tests/test_gdelt_events.py (3),
  test_world_feeds (+2).

- Afinado con datos reales (mismo día): conflicto exige actor ARMADO (MIL/REB/INS/SEP/UAF), solo
  IsRootEvent=1, fuera "solo país" con < 5 fuentes, y CORROBORACIÓN por punto (≥ 2 notas distintas o
  un evento con ≥ 4 fuentes). Severidad `gdelt_events.severity(artículos, fuentes)` (sin extrapolar).

# SESIÓN 2026-10-05 (o) — AGENTES CON CHIP EN EL CHAT: EL COMITÉ DE CARTERA RESPONDE AHÍ (sw v218)

- Feedback: "/cartera dime si debería reducir…" solo ABRÍA el comité y no respondía; pidió que
  llamar a un agente se vea "como un conector de ChatGPT con favicon" y elegir la cartera desde el chat.
- Servidor: POST /api/committee/portfolio/ask (research/committee_api.py) = portfolio_advisor.analyze
  (precios reales) → se guarda en el historial (kind='committee') → khipu_chat.run_chat con
  context.portfolio_notes (`portfolio_notes()`); devuelve agent{💼}, `portfolio` (tarjeta: score,
  veredicto, cobertura, 4 acciones) y la acción `open_pf_committee`.
- Cliente: classify → kind 'agentask' para /cartera, /portfolio, @cartera, "/comite mi cartera" y
  frases ("que el comité analice mi cartera"); KhipuChat.askAgent/agentInfo/pfSources/pfSelected/
  pfSelect (cartera elegida en localStorage 'kh_chat_pf_src'); fillReply pinta la tarjeta; burbuja
  del usuario con chip del agente. Cockpit `chatAgent()`; command_center delega 'agentask' en la Cabina.
- engine/pickers.js: CHIP de agente en el campo (ícono + nombre + selector de cartera + ✕); al elegir
  un agente sin empresa (comité de cartera, analistas) el token sale del texto y queda como chip; al
  enviar (Enter/➤) vuelve al texto (`flushTok`). `KhipuPick.agentOf(text)` para la burbuja.
- Tests: tests/test_chat_portfolio_agent.py (2); test_chat_commands actualizado (ya no abre pantalla).

# SESIÓN 2026-10-05 (n) — GEOPOLÍTICA CON FUENTES OFICIALES (sw v216)

- Pedido: "que dé más info, pero fiable". Diagnóstico: GDELT GEO (conflicto/protestas/
  comercio) está RETIRADO (HTTP 404) y estrechos/inestabilidad eran fichas curadas de julio.
- NUEVO `core/world_feeds.py` (capas `shipping`, `policy`, `disasters`, en LIVE_LAYERS y
  EVENT_LAYERS de core/world.py; misma caché/estado/pausa por fuente `source_down`):
  · shipping = FMI PortWatch (ArcGIS Daily_Chokepoints_Data): buques/día 7 d vs 90 d previos
    por estrecho; severidad = caída (−25 % ≈ 40, −50 % ≈ 80); hereda `affected` de
    core/geosit.CHOKEPOINTS. TTL 6 h. URL: WORLD_PORTWATCH_URL.
  · policy = Federal Register API (BIS + OFAC, 30 días): país objetivo (country_key = None a
    propósito: la exposición son las empresas NOMBRADAS, `companies`/`affected`), severidad =
    ESTIMACIÓN por palabras clave (`severity_kind: keyword_estimate`). Lista completa (también
    sin país) en GET /api/world/policy. URL: WORLD_FEDREG_URL.
  · disasters = GDACS (alertas Naranja/Roja, 10 días; 404 de GDACS = "cero alertas").
    URL: WORLD_GDACS_URL.
- MCP get_world_events: enum + maxItems 10 + campos nuevos (solo se AGREGAN).
- UI engine/worldmonitor.js: grupo "Fuentes oficiales", paneles "⛴ Tráfico por los
  estrechos" y "📜 Reglas de chips y sanciones" (marca 💼 si nombra empresas de tu cartera),
  fichas de detalle, "?" wm_official/wm_shipping/wm_policy.
- Ninguna fuente pide clave ni cuesta. NO verificado desde el sandbox (red bloqueada):
  verificar en producción con MCP get_world_events layers=[shipping,policy,disasters].
- Tests: tests/test_world_feeds.py (6) + tests/world_feed_fixtures.py.

# SESIÓN 2026-10-05 (m) — EL COMITÉ ANALIZA TODAS LAS POSICIONES (sw v215)

- "No analizó todas mis posiciones, solo algunas": había un tope OCULTO de 30
  (core/portfolio_advisor `_resolve_positions` y core/risk_report `build_report`); lo demás
  se descartaba sin aviso. Ahora `MAX_POSITIONS = 60` (build_report acepta `max_positions`;
  el MCP sigue en 30), lo que pase del tope y las privadas sin ticker van a `excluded` con
  motivo ES/EN, y la respuesta trae `coverage {requested, analyzed, researched, not_researched}`.
- UI (engine/pfcommittee.js `coverageHtml`): "Analizadas X de Y · Z con opinión de los
  analistas", qué quedó fuera y por qué, y botón "🔬 Investigar las que faltan" (máx. 3,
  POST /api/research/jobs con only_missing; respeta el presupuesto diario).
- Test: tests/test_portfolio_persist.py::test_comite_analiza_todas_las_posiciones_y_dice_cuales_no.

# SESIÓN 2026-10-05 (l) — CARTERAS QUE "DESAPARECÍAN" + COMITÉ DE CARTERA REGISTRADO (sw v214)

- Pedido: "que analice mi cartera, que se registre… puse como 3 carteras y luego no las encuentro".
- Causas: (1) Comité → 💼 Mi cartera listaba SOLO carteras con posiciones (las vacías no
  aparecían); (2) engine/sync.js, si ganaba la versión del servidor (409 o pull), pisaba
  carteras locales recién creadas que aún no subían; (3) `saveAll` fallaba EN SILENCIO si el
  navegador no dejaba guardar; (4) el análisis del comité de cartera no se guardaba.
- Arreglos: `sources()` lista todas (vacías = "· vacía", mensaje claro al analizar);
  `KhipuSync._merge` conserva las carteras locales creadas después de la versión del servidor
  (las borradas en otro equipo no reviven) y las vuelve a subir; `saveAll` libera cachés
  desechables y, si igual falla, AVISA; POST /api/committee/portfolio guarda cada análisis
  como `portfolio_reports.kind='committee'` por dueño (X-Khipu-Owner, `source_label`,
  `saved_id`); `/api/portfolio-report/list?kind=committee` lo lista (la lista normal lo
  excluye). UI: tarjeta "🗂 Análisis anteriores del comité" en el Diagnóstico.
- Test: tests/test_portfolio_persist.py (2, fallaban antes).
- DESPLIEGUE: Railway quedó atascado en "deploying" con 8541bce (14:44 UTC) y no tomó el
  commit vacío 95173c1; producción siguió en 68d18e7. Fabrizio debe cancelar/redeploy en Railway.

# SESIÓN 2026-10-05 (k) — OPCIONES FIJAS Y MENÚ "/" "@" EN EL CHAT (sw v213)

Pedido: "cuando ponga / o @ me salgan ya las opciones" + "el comité pueda analizar mi cartera desde
el apartado de comité" + "donde se escriban cosas fijas (tickers…) no quiero que te deje escribir sino
que te vaya recomendando y sean fixed options". `engine/pickers.js` (`window.KhipuPick`):
`chatMenu(input)` (menú de comandos/analistas y luego empresas; Enter/Tab completa; en la Cabina y en
command_center) y `attach(input,{kind:'entity'|'symbol', multi, extras, onPick})` (sugiere y SOLO
acepta opciones de la lista; texto libre → borde rojo). Aplicado a: Comité (empresa + opción fija
"💼 Mi cartera" + botón "Analizar mi cartera"), selector de la Cabina (estricto), Clientes (símbolo de
orden y listas permitidos/prohibidos). Riesgo ya era solo-lista. Campos de texto libre a propósito: el
chat, "Excluir" de Carteras (acepta países/sectores), búsquedas de navegación. Tests: tests/test_pickers.py.

# SESIÓN 2026-10-05 (j) — COMANDOS Y AGENTES EN EL CHAT (sw v212)

Pedido de Fabrizio: "que el comité pueda analizar mi cartera y que en el chat de Khipu puedas llamar a
los agentes y que haya comandos". `engine/khipu_chat.js` `agentCommand()` (antes de todo el ruteo):
`/ayuda` (lista bilingüe), `/investigar <empresa>` (= @investigación X, "llama al agente de investigación
para X" → el equipo de 8 analistas), `/comite <empresa>`, `/cartera` (= "/comite cartera", "@comité mi
cartera", "que el comité analice mi cartera" → Comité → 💼 Mi cartera). Los @analistas (@fundamental,
@noticias, @todos…) siguen en el cerebro (research/ask_agent). Pista en el campo del chat. Tests:
tests/test_chat_commands.py. Producción: alias + repetidos aplicados por Fabrizio (corrida
20261005T032149Z-dce54c, verificada); AlphaSenseFin → AlphaSense en el catálogo.

# SESIÓN 2026-10-04 (i) — MISIÓN DE REPARACIÓN · P1 GRAFO + P2 WORLD MONITOR Y OPERACIÓN (sw v210)

Causa raíz de casi todo P1: DOS verdades del grafo. El mapa y el MCP leen el catálogo (limpio desde
julio); el motor de shocks, el NRS del servidor y el Grafo Temporal leen Postgres, que conserva el grafo
PRE-limpieza (empresas repetidas, vínculos dobles, ~400 flechas al revés hacia TSMC/Nvidia…).
- G1 auditoría automática (`scripts/audit_graph.py`, línea base + trinquete). G1b/G1d 11 alias nuevos
  (misma empresa dos veces). G1c `NODE_BY_ID[alias]` siempre lleva al canónico (antes AWS y 30+ no).
- G2/G2b ontología append-only de verdad: dedupe de LinkCreated (`dedup_of`), retracción DIRIGIDA y
  retroactiva (`retracts_event_id` + `links.event_id`), Acciones RetractarVinculo / FusionarEntidad.
- G3 reconciliación catálogo ↔ Postgres SOLO con eventos (ontology/reconcile.py, CLI, /api/ontology/
  reconcile/*, panel 🩺 → Diagnóstico → "Grafo: base vs catálogo"). Ensayo con una base migrada desde
  el snapshot de julio (como producción): 56 alias · 31 repetidos · 393 direcciones · 53 pesos · 273
  faltantes · 4 sobrantes → todo aplicado en ~6 s, 0 diferencias, tablas == replay, deshacer exacto.
  **En producción NO se aplicó nada**: Fabrizio hace copia de seguridad → "Aplicar lo seguro" (alias +
  repetidos) → revisa la lista de direcciones (decisión D5) antes de marcarlas.
- G4 (agente): MCP proveedores/clientes = solo relaciones de FLUJO (socios/inversores en `related`),
  `relation_class`/`verified`/`confidence` por arista, fecha centinela 2000-01-01 marcada
  `valid_from_known:false`, confianza por link en matrices (w×conf), NRS estructural (pares de flujo
  distintos: varios NRS bajan), cifras del catálogo con unidad y sin fecha propia.
- Snapshot regenerado: 949 → 938 nodos, 2.526 → 2.524 enlaces. Suite completa verde con base local.
- Revisión adversarial antes de desplegar (3 lentes): 31 hallazgos → G5/G5b (ontología: emparejamiento,
  ascenso de duplicados solo al deshacer, candados, plan revisado, PIN obligatorio, arranque sin candado
  exclusivo) y G6 (mismo NRS en chat/carteras/Second Brain, chat sin cortar clientes, confirmado no se
  descuenta, ids viejos → canónico, "% exacto no verificado" ya no marca la relación). Límite conocido: con
  un proveedor ÚNICO no verificado el descuento no actúa en el motor de matrices (documentado en REPAIR_LOG G6).
- P2 hecho en la misma sesión: W1 (GDELT 404 → pausa honesta 1 h, capas curadas declaradas, precalentado),
  O1 (chequeo del sistema tras cada arranque y diario: `/api/ops/last_check`; humo del MCP solo lectura
  `scripts/smoke_mcp.py` + CI opcional con el secreto `KHIPU_MCP_TOKEN`), O2 (`LOG_JSON=on`).
- Pendiente para Fabrizio: AlphaSense ≈ AlphaSenseFin (¿misma empresa?), Envicool margin 20.25
  (¿0.2025?), Sterling→Eaton (nota de duplicado), revisar "direcciones al revés" en el informe del 🩺 y,
  ANTES de aplicar nada, copia de seguridad de Postgres en Railway.

# SESIÓN 2026-10-04 (h) — MISIÓN DE REPARACIÓN · P0 INVESTIGACIÓN (R1-R6, sw v201)

Fabrizio: "dejar Khipus Finance confiable y a punto, sin gastar dinero; no agregues features; estoy a
días de usarlo para invertir dinero ajeno". Regla 1 cumplida: primero `docs/REPARACION_DIAGNOSTICO.md`
(mapa del sistema, reproducción por MCP de cada hallazgo: confirmado/distinto/no confirmado, plan de
21 commits y 7 decisiones) → OK de Fabrizio ("todo como recomiendas, empieza por P0"). Registro por
arreglo en `REPAIR_LOG.md`; tests en `tests/test_repair_research.py` (26, fallaban antes de cada commit).
- R1 corta-circuito por proveedor de IA (sin saldo 60 min / clave 30 / modelo retirado 30; el 🩺 lo
  reactiva con un ping). R2 "IA ocupada" espera 3/6/12/24 s y reintenta el MISMO proveedor;
  429/5xx/red con backoff+jitter en Claude/Gemini/NVIDIA. R3 cola FIFO de jobs (2 hilos) + pool de
  agentes compartido (2) + recuperación de huérfanos tras deploy. R4 estado `partial` + `coverage`
  (síntesis, API, MCP, franja ⚠ y botón "Completar lo que falta"; `only_missing`). R5 presupuesto
  agotado → `deferred` y reanudación automática al día siguiente (solo pedidos de personas, máx 3;
  eventos automáticos se descartan), `core/scheduler.py` (reloj del servidor), runs fallidos cuentan
  tokens, UNA tabla de precios. R6 `/api/research/health` + bloque en `/api/health` + tarjeta 🔬 en
  🩺 + MCP `get_research_health`.
- Decisiones tomadas (Fabrizio): validado = 5 calificaciones y tope 50 % mientras no; cobertura
  fundamental + 3 de 4; checkpoints hábiles 5/20 (corto), 20/60/180 (medio), 60/180/365 (largo);
  Postgres es la verdad del grafo; lista de direcciones al revés antes de aplicar; GDELT apagado con
  aviso si pide clave. Pendiente de Fabrizio en Railway: `AI_ORDER=gemini,claude,nvidia` y
  `RESEARCH_MODEL_DEFAULT=gemini,claude:deep,nvidia` mientras Anthropic no tenga saldo.
- Revisión adversarial (workflow, 6 lentes) sobre R1-R6 + precios → R7 (cola: reclamo atómico del
  job, huérfanos al arrancar y cada 10 min, runs cerrados al fallar, diferidos duplicados, Pizarra =
  pedido humano; IA: circuito de Claude solo por errores definitivos y con código HTTP explícito,
  API_KEY_INVALID de Gemini, límite de 💰 corta la cascada, el chat es INTERACTIVO) y R8 (contratos:
  only_missing honesto, cobertura solo si corrió, tope 0 = apagada (503), Pizarra por la cola y
  diferible, hints por estado en MCP, chat conoce get_research_health, docs/MCP.md).
- P0 COMITÉ (C6-C10, `tests/test_repair_committee.py`, 19 tests): C6 "no validado" (ningún analista
  con ≥5 calificaciones) → insignia + tamaño a la MITAD (`compute_sizing(validated=)`,
  `memo.track_validation`); C7 quórum fundamental + 3 de 4 analistas o `decision_code=
  INSUFFICIENT_DATA` (HOLD "DATOS INSUFICIENTES", sin debate ni presidente IA; encarga solo a los que
  faltan; puestos ausentes en la sala); C8 falsadores estructurados `{metric, op, threshold, by}`
  (`research/falsifiers.py`; columna `research_claims.falsifier_rules`; un falsador no puede
  confirmar la tesis; el job diario los verifica → claim `falsified` = fallo del analista; el memo
  avisa `falsified_claims`); C9 conf-v2 (`computed` no es fuente independiente; `khipus:*` = una
  referencia; cifras de dinero sin fuente externa → tope 0,5); C10 checkpoints en días hábiles de NYSE
  (5b/20b/60b + 180d/365d) y evaluación diaria robusta desde el reloj (`research_outcomes_daily`).
  Los tests de Phase 3 que fijaban 5 %/$5.000 pasan a 2,5 %/$2.500 (decisión D1).
- El commit de precios en vivo (cc1dfed, agente de la sesión (g)) entró en la misma revisión
  adversarial antes de desplegar. SIGUIENTE: P1 grafo (auditoría, fusión por eventos, lista de
  direcciones para Fabrizio), P1 riesgo, P2.
- P1 GRAFO · G4 (contratos y cálculos, `tests/test_repair_graph.py`, 21 tests; commit 14 del plan):
  G4a proveedores/clientes = solo relaciones de FLUJO (vocabulary.json `flow:true`), partner/invest
  aparte en `related`, `relation_class` + `verified`/`confidence` por arista, `include_partners`;
  G4b centinela 2000-01-01 (`GENESIS_SENTINEL`/`is_genesis`) marcado `valid_from_known:false` en
  API/timeline/MCP (+ nota bilingüe) y `provenance_note` cuando no hay fuente; UI "desde que se
  rastrea"; G4c `conf`/`verified` por link desde el texto curado ("no verificado"/"posible" → 0,3)
  en merge_graph.js → snapshot → migración → `matrix/engine._eff_weight(…, confidence)` y
  statematrix.js; G4d NRS estructural (grado = pares distintos de flujo; cliente, servidor y
  catálogo; los NRS visibles bajan); G4e `catalog.operating_margin_pct` + `figures_as_of:null` +
  `figures_note`. Pendiente al integrar: regenerar `data/grafo_v0.json` (traerá conf/verified). Los informes de los investigadores de fondo con tests
  propuestos están en el journal del workflow wf_0017fa17-625.

---

# SESIÓN 2026-10-04 (g) — KHIPU COMO ASISTENTE: ANALISTAS EN EL CHAT, PROMPT, MEMORIA, TIEMPOS (sw v196)

Fabrizio: "no me responde bien, no me entiende, está empeorando; tiene que ser mi asistente; quiero
invocar a los agentes dentro de la conversación". Verificado por MCP (la app conectada a esta sesión):
datos en vivo OK (Yahoo), investigación y comité OK con gemini-3.5-flash → el problema era el CHAT con
Gemini como único proveedor. Auditoría (workflow) + arreglos:
- `core/ai`: `want_json` (JSON estricto en Gemini para los pasos del chat), pensamiento APAGADO en
  flash para nivel rápido y JSON (GEMINI_THINKING=on lo devuelve), nivel profundo con presupuesto de
  pensamiento 1024 SUMADO a maxOutputTokens (no se come la respuesta), `timeout_s` acotado al
  presupuesto del chat (antes el hilo seguía 90 s ocupando cupo), json_mode 2500 tokens (8192 solo
  research), `live_facts=False` por paso (el bloque DATOS EN VIVO se calcula una vez por pregunta).
- `core/khipu_chat`: build_system en ≤25 líneas (persona + RECETAS de una ronda + formato con fuente y
  fecha en la misma frase); build_prompt reordenado (contexto → historial → resultados → PREGUNTA al
  FINAL + empresas detectadas); contexto `open_windows` y `recent_entities` ("ella/su/este");
  pre-consulta especulativa de get_company en paralelo con la 1.ª llamada; synthesize en nivel rápido
  (2200 tokens); SYNTH_GRACE 4 s / SYNTH 20 s / TOOL 14 s (45+4+20 < 70 s del cliente); catálogo sin
  get_ontology_object ni get_option_greeks; motivo humano (`ai_detail_es/en` vía research.errors).
- `research/ask_agent.py` (NUEVO): `parse_mention` ("@fundamental …", "@todos …", "pregúntale al
  analista técnico: …"), `ask()` = paquete del puesto (claims activos + evidencia, como seat_package)
  → respuesta EN PERSONA con guardián de cifras; `ask_all()` en paralelo (máx. 4 puestos). Ruta directa
  `_mention_route` en run_chat (sin bucle) + herramienta `ask_agent` para el cerebro; sin investigación
  → ofrece `open_research`. UI: avatar + nombre (KhipuCommittee.avatar expuesto), `.kc-agent`.
- Cliente (khipu_chat.js/cockpit.js): historial 24 h en localStorage, atajos recordados ("desármame X"
  + "¿y sus proveedores?"), respuestas sin IA no se memorizan, `noteEntity` al abrir escenas,
  `open_windows` en el contexto, motivo humano + botón ↻ Reintentar, pie con modelo/consultas/segundos.
- Escritorio: ventanas movidas a mano se respetan (w.manual) hasta "Ordenar ahora"; chips X-Ray/Simular/
  Comparar/Investigar sin empresa → ventana "Elegir empresa" con sugerencias. Canvas: "precio de bitcoin
  de los últimos N años" → línea con historial (CoinGecko, tope 365 d avisado).
- Tests: test_ask_agent (6), test_ai_gemini_fast (3), test_ai_json (4). Pendiente en paralelo (agente):
  auditoría de precios en vivo (lotes de 100, q.live numérico, merge Marketstack, Terminal, chips de
  fuente, live_caps como respaldo, circuito 429) y, del workflow: diseño del renderizador del Canvas,
  estética profesional y ontología tensorial.

---

# SESIÓN 2026-10-04 (f) — "EXPECTING VALUE" EN INVESTIGAR: JSON ESTRICTO + MENSAJES PARA PERSONAS

Fabrizio tiene saldo en Gemini pero Investigar daba "IA falló · Expecting value: line 1 column 1":
un proveedor SÍ respondió, pero sin JSON (Gemini 2.5 flash "pensando" se come los tokens y corta,
o contesta en prosa). `core.ai._ai_json(system, prompt, …)`: _ai_complete + _extract_json y, si no
hay JSON y existe GEMINI_KEY, UN reintento con `_complete_gemini(json_mode=True)` (JSON estricto,
sin pensamiento, 8k tokens). Lo usan /api/research/deep y /api/crypto/analyze. `server._ai_friendly_error`
traduce la excepción a texto ES/EN ("La IA respondió, pero no en el formato esperado…" / "La IA no
respondió (sin saldo o proveedor caído)…"). Ventanas del escritorio opacas (#070B14) — el inicio
nuevo se transparentaba detrás. Tests: tests/test_ai_json.py (4). sw v192.

---

# SESIÓN 2026-10-04 (e) — INICIO DE LA CABINA REDISEÑADO + FEED SIN NOTICIAS VIEJAS (sw v190)

- Inicio de la Cabina (stageEmpty, cockpit.js) rediseñado con el skill frontend-design: saludo en
  Fraunces según la hora, UNA frase viva ("Nuevo:" / "Estructural, no es noticia nueva:" + fecha de
  los factores), tu cartera en una línea (con PIN), dos columnas de texto plano "Pregúntame" / "Abre",
  recorrido de un minuto al pie. Sin tarjetas, píldoras ni mayúsculas decorativas; alineado a la
  izquierda, máx. 760 px; móvil en una columna. Las ventanas del escritorio flotan encima.
- 📡 "Lo último en el grafo" (/api/ontology/feed): por defecto solo lo registrado en los últimos 14
  días (?days=); si no hay nada, devuelve last_at y el panel dice "Sin novedades en las últimas 2
  semanas. Lo último entró hace N días" (ES/EN) en vez de reciclar noticias viejas como "lo último"
  (origen de "crisis de gobernanza en Samsung" que Fabrizio veía siempre).
- Jev funciona sin clave: si no hay TYPESAFE_API_KEY simplemente no se usa (available() false).

---

# SESIÓN 2026-10-04 (d) — ESCRITORIO: ORDEN AUTOMÁTICO + 📌 FIJAR A LOS COSTADOS (sw v189)

Pedido: "que cuando se abre una pestaña se organicen las cosas, que no se vea saturado, fácil de
ordenar, y fijarlas en los costados del chat para seguir viéndolas mientras escribes".
- `arrange()` en engine/desktop.js: al abrir/cerrar/minimizar/fijar (y al cambiar el tamaño del
  escritorio, p. ej. cuando aparece el dock del chat) las ventanas se reparten solas: 1 = todo,
  2 = mitades, 3 = la nueva grande a la izquierda + dos cuartos; la 4ª suelta manda a la barra a
  la más antigua (MAX_CENTER=3). kh_desk_auto=off lo apaga (⊞ → "Ordenar automáticamente").
- 📌 (kd-b-pin): ventana FIJADA a una columna lateral (izq./der., 32 % del ancho, apiladas); no se
  arrastra ni redimensiona; sigue visible con la conversación abierta. Recordado por tipo
  (kh_desk_pins). Maximizar o arrastrar la suelta.
- cockpit `_chatBeside`: con orden automático solo enfoca 💬 (ya quedan lado a lado).
- Guía actualizada; Playwright +13 comprobaciones (orden 1-4 ventanas, barra, fijar der./izq.,
  re-ajuste con el dock, soltar, apagar).

---

# SESIÓN 2026-10-04 (c) — JEV (TYPESAFE) EN MODO SOMBRA: PORTERO DEL CHAT (sw v188)

Fabrizio quiere usar Jev (modelo "System One" de TypeSafe: decisiones tipadas con
probabilidades calibradas, sin texto) como optimizador de costos, revisor y primera capa
de decisión. Hecho: `core/decide.py` (única puerta; registra en 💰 Gasto IA como
proveedor 'typesafe'; respeta límites), `core/decide_api.py` (/api/decide/status,
/api/decide/shadow con PIN), tabla decision_shadow, y el PRIMER uso: portero del chat
de Khipu — en paralelo a cada pregunta Jev decide ruta (local_fact / needs_tools /
needs_deep_reasoning / offtopic), si menciona empresa, si pide una orden, si es sobre la
cartera y la urgencia; al terminar se compara con lo que el chat hizo (ruta real por
pasos/herramientas) y se guarda el acuerdo. NO cambia la respuesta hasta que
DECIDE_CONTROL incluya 'chat_gate'. Tarjeta 🧭 Jev en 🩺 → 💰 Gasto IA. Tests:
tests/test_decide.py (8). Docs: docs/JEV.md. Precio de Jev no publicado al integrar:
fijar AI_PRICES_JSON cuando se sepa. Pendiente de Fabrizio: TYPESAFE_API_KEY en Railway.
Nota de red: docs.typesafe.ai/api.typesafe.ai están bloqueados desde el entorno de desarrollo
(Fabrizio pegó las páginas quickstart/primitives/confidence/patterns).

---

# SESIÓN 2026-10-04 (b) — ESCRITORIO: REVISIÓN ADVERSARIAL Y CORRECCIONES (sw v187)

Workflow de revisión (5 lentes × 2 refutadores por hallazgo, 61 agentes): 20 hallazgos confirmados,
8 rechazados. Corregido TODO lo confirmado (engine/desktop.js reescrito; cockpit.js):
- GRAVE: bucle de `resize` sintético a 5 Hz (onResize → fireResize → resize → onResize…) que seguía
  con la Cabina cerrada y hacía settleGraph del mapa sin parar. Ahora onResize ignora `isTrusted=false`
  y no reemite; el escritorio se re-adapta con un ResizeObserver sobre #kd-wins (también cuando
  aparece el dock del chat: las ventanas pegadas se re-ajustan a su zona).
- GRAVE: `place()` medía el escenario oculto (0×0) al cerrar la Cabina y encogía todo a 320×220.
  `deskSize()` → null si está oculto; nunca se recorta geometría contra una medida inválida.
- Cerrar/reabrir la Cabina ya NO re-inicializa las ventanas adoptadas: `parkAdopted()` recuerda
  ventana+caja de cada panel y `readopt()` devuelve el MISMO nodo (la terminal conserva sus gráficos,
  el mapa su zoom). Scalping se re-pinta (resumeKinds) para que vuelva el polling.
- Despegar una ventana pegada a la derecha ya no la lanza lejos del cursor (fx relativo a la ventana);
  pointercancel REVIERTE (no "suelta" en 0,0); el borde superior no empuja el inferior.
- Chat: con la ventana 💬 abierta, la respuesta que abre otra ventana (X-Ray…) la pone LADO A LADO
  (resultado izq., conversación der.) en ≥1100 px, o trae 💬 al frente; si 💬 está minimizada o
  detrás de otra hoja, se enfoca al llegar la respuesta. Chrome compacto en el escritorio
  (#bcp-ov.desk: orbe 44 px, dock 22vh / 18vh en pantallas bajas).
- Tablet (dedo, ≥761 px): controles de 40×36, manijas de 16 px, selector de acomodo al TOCAR ▢.
- Móvil: hojas ocultas con display:none (kd-hide) → globos/burbujas/timers se duermen de verdad.
- Esc cierra primero el menú ⊞ / selector; giro teléfono↔tablet re-etiqueta (✕ ↔ ‹ Volver); barra de
  tareas no se reconstruye si nada cambió; kh_desk_geom inválido tolerado; títulos/íconos = chips;
  interruptor de modo solo en clásico (en el escritorio vive en ⊞); pista de la primera ventana (toast,
  una vez); role=dialog + aria-label; timers y listeners limpios en unmount.
- Prueba Playwright ampliada (50 comprobaciones): sin bucle de resize, geometría conservada al cerrar/
  reabrir, mismo nodo de terminal, Esc con menú, lado a lado, kd-hide en móvil. Nota: la franja roja
  #srv-down (APIs 503 en la prueba) tapa el alto del teléfono; se quita en el setup del test.

---

# SESIÓN 2026-10-04 — ESCRITORIO KHIPU K1: VENTANAS DENTRO DE LA CABINA (sw v186)

Pedido de Fabrizio: "la vista general sea como el interfaz de Khipu; poco a poco será el ÚNICO
interfaz; todo lo que se genere o abra, como una ventana que se mueve y cambia de tamaño; punto
medio entre ChatGPT y Windows 11". Primer paso (K1 del plan "VISIÓN PRÓXIMA ETAPA"):
- `engine/desktop.js` (NUEVO, window.KhipuDesk): el escenario de la Cabina (#bcp-stage) pasa a ser un
  escritorio: fondo = pantalla de inicio (chips), capa de ventanas, fantasma de snap, barra de tareas
  (#kd-bar: ⊞ menú mosaico/cascada/minimizar todo/cerrar todo/modo clásico + un botón por ventana).
  Ventana = barra de título (ícono · título · – ▢ ✕) + cuerpo + 8 manijas. Arrastre y redimensión por
  pointer events (táctil incluido); arrastrar al borde = mitad/cuarto/maximizar (estilo Windows 11, con
  previsualización); pasar por ▢ = selector de acomodo; doble clic = maximizar/restaurar; una ventana
  maximizada/pegada se "despega" al arrastrarla. Geometría recordada por tipo (kh_desk_geom). Móvil
  (≤760 px) = hojas a pantalla completa, botón "‹ Volver", chips en la barra para cambiar.
- `engine/cockpit.js`: `stage(kind,arg,opts)` = política (escritorio → KhipuDesk.open; clásico → como
  antes) y `render(s,kind,arg)` = despacho de escenas (pinta en el cuerpo de la ventana). Adopción de
  paneles reales POR VENTANA (`_adoptCtx`, `restoreAdopted(winId)`): cerrar la ventana devuelve el
  panel; cerrar la Cabina devuelve todo y `suspend()`; reabrir → `resume()` re-adopta. Ganchos:
  configure({render,title,icon,beforeRender,onClose,onFocus,onModeChange,adoptKinds,multiKinds}).
  Multi-instancia solo 'xray' y 'sim' (render con s.querySelector); el resto singleton por tipo (usan
  ids globales bcp-*: broker, scalp, deep, compare, research…) — con argumento nuevo se re-pinta.
  Chat: en el escritorio la respuesta va SIEMPRE al dock de abajo (sin dejar de ser un chatbot); la
  ventana 💬 ('chat', botón ⤢ Ampliar) adopta el hilo y al cerrarse el hilo vuelve al dock. Demo = una
  ventana a la vez, maximizada; al terminar cierra todo. Interruptor "🪟 Modo ventanas · usar una sola
  pantalla" en el inicio (kh_desk_mode=off → Cabina clásica intacta, red de seguridad).
- `app.html`: `resize()` del mapa ignora 0×0 (ventana minimizada → no re-centrar en cero).
- Guía: entrada 🪟 Escritorio Khipu (ES/EN). sw v186 (+ engine/desktop.js en SHELL).
- Verificado con Playwright (/tmp pw/desk.js, 40 comprobaciones): abrir grafo/terminal/2 X-Ray, arrastrar,
  snap, redimensionar, maximizar, selector de acomodo, minimizar/restaurar desde la barra, cerrar, mosaico
  sin solapes, chat al dock / ventana 💬, cerrar y reabrir la Cabina (re-adopción), idioma, modo clásico y
  vuelta, demo, Esc, móvil (hojas, Volver, chips). Medido: dibujar enlaces en canvas NO ayuda (sesión previa).
- LECCIONES: (1) nunca usar las mismas clases para botones y estados de ventana (kd-min/kd-max eran
  ambas → en móvil `#bcp-stage.kd-mobile .kd-max{display:none}` ocultaba la hoja maximizada; ahora los
  botones son kd-b-min/kd-b-max/kd-b-x); (2) listeners del escenario se registran UNA vez (`_kdWired`):
  el escritorio se desmonta/monta al cambiar de modo; (3) `resize` global solo cuando cambia una ventana
  que aloja un motor (adoptKinds) — el mapa hace settleGraph en cada resize.
- SIGUIENTE (K2-K4): botones "abrir en ventana" explícitos en las respuestas de Khipu (hoy las acciones
  ya abren ventanas), Dossier/Comité/Cartera/Clientes como ventanas (hoy son overlays por encima),
  espacios guardados (kh_desk_layout sincronizado) + "Khipu, pon el comité al lado de mi cartera" por voz,
  pausar motores de ventanas minimizadas (WebGL/WebSocket), retirar las pestañas clásicas al final.

---

# SESIÓN 2026-10-03 (g) — SINCRONIZACIÓN ENTRE DISPOSITIVOS (sw v184)

- `engine/sync.js` (NUEVO, window.KhipuSync): sincroniza kh_portfolios, kh_pf_active, kh_investor_profile
  y eco_pos (MKT.pos) con el servidor; parchea Storage.prototype.setItem para subir cada cambio (1,5 s),
  baja al abrir, cada 2 min y al volver a la pestaña; último que escribe gana (kh_sync_meta). Vincular otro
  dispositivo = pegar el código (la llave kh_owner_key) en Comité → 💼 Mi cartera → 📱 Otros dispositivos.
- Servidor: GET/PUT /api/user-state (tabla user_state, por owner_hash; 409 si la escritura es más vieja;
  máx. 300 KB) en core/portfolio_reports_api.py. `current_positions()`: los reportes PROGRAMADOS usan la
  cartera sincronizada de HOY (pf:<id> o market), no la guardada al programar.
- Nota: MKT.pos ya no vive solo en el navegador (CLAUDE.md "Portafolio del usuario" actualizado).

# SESIÓN 2026-10-03 (f) — PANEL DE TRADING BILINGÜE Y MÓVIL + APROBACIÓN DEL COMITÉ CON POP-UP (sw v183)

- app.html #trade-panel: todos los textos ES/EN (`_TPT` + `_tpt()`, atributos data-tpt*, `window._tpRelabel()`
  enganchado a applyLang como _termRelabel); responsive (≤900 px 2 columnas, ≤600 px una columna con el
  ticket primero; controles ≥40 px; inputs 16 px en móvil); estilos con tokens --kt-*; datos guardados en
  _tp.acct/positions/history/agent y pintados por _tpPaint*. Lógica de envío/PIN/duplicados intacta.
- engine/committee.js: "Aprobar" usa KhipuToast.confirm (casilla obligatoria si DINERO REAL); sendDecision().
- engine/guide.js: Pizarra, Sala del comité, Mi cartera, simulación estructural, 💰 Gasto IA, avisos de órdenes.

# SESIÓN 2026-10-03 (e) — RESPUESTAS CORTADAS + HERRAMIENTA DE ESCENARIOS EN EL CHAT

Captura: "3 empresas más expuestas a una guerra en Taiwán" → respuesta cortada ("NRS), son Hon Hai…
**Hon Hai (Fox") y pobre (Kneron, por ranking genérico de riesgo).
- core/ai.py `strip_reasoning()`: quita <think>…</think> de TODOS los proveedores (sin cerrar → '');
  NVIDIA recibe max_tokens ×2 (mín. 2048) por los modelos de razonamiento.
- core/khipu_chat.py `truncated()` (negrita/paréntesis sin cerrar u oración larga sin final; exime
  línea de fuentes e ítems de lista): respuesta cortada → `synthesize()` la reescribe; synthesize
  reintenta 1 vez si sale sucia o cortada.
- Herramienta NUEVA `scenario_exposure` (core/scenario_engine): golpe directo, posibles ganadores,
  impactos con CAMINO en la cadena y qué vigilar; regla 11 del sistema: usarla para "qué pasaría si /
  más expuestas a…" en vez de un ranking genérico.

# SESIÓN 2026-10-03 (d) — KHIPU YA NO FILTRA SU BORRADOR; EL AGENTE REDACTA SIEMPRE

Captura: "¿cuáles son las 3 empresas más expuestas a una guerra en Taiwán?" respondió con restos del
protocolo ('"actions": [...]', '```', "Wait, is simulate arg a string?"). Causa: cuando el modelo
"pensaba en voz alta" o escribía varios JSON, parse_step fallaba y se mostraba el texto crudo; si se
acababa el tiempo, salía la plantilla sin IA.
- core/khipu_chat.py: `_json_objects()` (todos los JSON balanceados; se usa el ÚLTIMO que cumple el
  protocolo), `leaked()` (restos de JSON/código o "Wait/Hmm/Let me…" al inicio de línea) y
  `synthesize()`: si el protocolo falla, la respuesta trae restos o se acaban las rondas, el AGENTE
  (tier deep) redacta la respuesta final en prosa con los datos ya consultados. La plantilla sin IA
  queda solo si la IA no responde (o respondió lento: no se le pide otra redacción).
  SYNTH_TIMEOUT_S 25 · SYNTH_GRACE_S 10.

# SESIÓN 2026-10-03 (c) — TERMINAL REDISEÑADA + POP-UPS DE COMPRA/VENTA (sw v182)

- Terminal (app.html + engine/termdata.js): nuevo layout con tokens --kt-* (oscuro/claro), cabecera por
  panel (ticker, precio, cambio, periodos, Operar), línea de stats del periodo, filtro por los 13 sectores,
  📋 Datos como TERCERA columna (BUG arreglado: en escritorio el panel de datos aplastaba los gráficos a 0 px),
  cajón en 820-1180 px y Lista/Gráficos en móvil; prellenado con tu cartera + NVDA/TSM/ASML/AVGO
  (`_termSeed`); textos bilingües (_TT/_tt, window._termRelabel).
- `engine/toast.js` (NUEVO): window.KhipuToast — show/update/dismiss, confirm(), confirmOrder() (lado,
  activo, cantidad, tipo, vigencia, monto estimado = cantidad × precio real; DINERO REAL exige casilla),
  order.sending/result/watch/filled (sondeo de /api/trade/history ≤ 60 s, evento `khipu:order`).
  Conectado en: panel de trading (paso de confirmación NUEVO), voice._executeTradeOrder, tarjeta del bróker
  en la Cabina, scalping (insignia real del modo), crypto.js, clients.js (aprobaciones), portfolios.js
  (simulado) y "Aplicar en simulación" del comité de cartera. Ninguna ruta nueva envía órdenes.
- Pendiente: textos fijos del panel de trading solo en español y su layout de 3 columnas en teléfono.

# SESIÓN 2026-10-03 (b) — REPORTES DE CARTERA, "PREGÚNTALE A TU CARTERA", NOTICIAS DE TU CARTERA

Pedido: reportes diarios/mensuales/a pedido vs posición inicial con gráficos, "como un NotebookLM con el
contexto de tu cartera", nivel de involucramiento, noticias en vivo según tu cartera (no emergencias viejas).
- `core/portfolio_report.py`: rendimiento del periodo y desde la posición INICIAL (capital de partida o
  costo), vs S&P 500, curva diaria base 100 (supone mismas acciones; se rotula), contribución por posición,
  peor caída, acciones del comité de cartera, noticias del periodo y resumen (IA con guardián / plantilla).
- `core/news_feed.py`: noticias de las posiciones (Finnhub con resumen + GDELT), SOLO con fecha y dentro de
  la ventana, sin duplicados (agrupa empresas), relevancia = peso × frescura; etiquetas 🆕 hoy / hace N días.
- `core/portfolio_reports_api.py` (blueprint): POST /api/portfolio-report/generate · GET /list · GET|DELETE
  /<id> · POST /watch (reportes automáticos off|daily|weekly|monthly) · GET /watches · POST
  /api/news/portfolio · POST /api/portfolio-report/ask (cerebro de Khipu con context.portfolio_notes).
  Dueño = llave aleatoria del navegador (localStorage kh_owner_key → X-Khipu-Owner; solo se guarda el
  SHA-256). Hilo programador cada 20 min (daily ≥21:00 UTC, weekly viernes, monthly día 1). Tablas
  portfolio_watches / portfolio_reports (research/models.py).
- UI: Comité → 💼 Mi cartera ahora tiene secciones 🩺 Diagnóstico · 📄 Reportes · 📰 Noticias · 💬 Pregúntale
  (engine/pfreports.js, window.KhipuPortfolioExtras). Programación sugerida por el nivel de involucramiento
  (piloto→mensual, informado→semanal, activo→diario). Imprimir/PDF. Aviso al abrir la app si hay reportes nuevos.

# SESIÓN 2026-10-03 — GASTO DE IA, SIM. ESTRUCTURAL, AVATARES, CANVAS, COMITÉ DE CARTERA (sw v181)

Pedidos: sim "China prohíbe exportar HBM" sin info útil (semilla XPO por "eXPOrtar"); comité con
personajes 2D; Canvas sin IA flojo (criterio de gráfico + IA cuando no hay precisión); "saber el saldo
del API, controlar el gasto y de dónde"; comité de CARTERAS con acciones concretas; noticias viejas
repetidas ("crisis de Samsung" desde hace meses).
- `core/scenario_engine.py` (NUEVO): tema (HBM, CoWoS, EUV, GPUs, tierras raras, galio, litio, cobre,
  uranio, energía, gases, obleas…) → productores; actor (país) y evento (veto de exportación, arancel,
  disrupción, impulso); golpeados vs ganadores (sustitutos), propagación por la cadena con caminos,
  timeline, qué vigilar. `core/sim_agents.py` lo usa como elenco/base de la IA y como respaldo sin IA
  (impactos por canal: directo/sustituto/cliente/2º orden/proveedor). Semillas: se descarta solo la que
  aparece DENTRO de otra palabra. UI (cockpit agentsim): Lo esencial, ganadoras/perdedoras, citas de
  agentes, cómo se desarrolla, qué vigilar, camino de cada impacto. extractSeeds con palabra completa.
  BUG arreglado: app.html definía otra `_runAgentSim` global que pisaba la de cockpit.js (la voz
  llamaba a la equivocada) → ahora `_runAgentSimTab`.
- GASTO DE IA: `core/ai_usage.py` (registro por llamada: proveedor, modelo, tokens REALES del proveedor,
  costo estimado por lista de precios, FUNCIÓN de la app y QUIÉN; en memoria + tabla `ai_usage` en lotes;
  límites diario/mensual/por función/por persona en `ai_settings` editables con PIN; AIBudgetError antes de
  llamar = no cobra; la cascada se detiene). core/ai.py: check() + record() en los 3 proveedores.
  Contexto: ai_context()/bind() (research, comité, debate). GET /api/ai/usage, POST /api/ai/usage/limits
  (PIN). UI: 🩺 Sistema → 💰 Gasto IA (engine/aispend.js). SALDO: ningún proveedor lo publica por API;
  con ANTHROPIC_ADMIN_KEY (sk-ant-admin…, solo organizaciones) se muestra lo FACTURADO por Anthropic
  (cost_report). Env: AI_DAILY_LIMIT_USD (10), AI_MONTHLY_LIMIT_USD (150), AI_PER_USER_DAILY_USD (0),
  AI_PRICES_JSON.
- Comité: avatares SVG 2D por puesto (Valeria, Kenji, Amara, Diego, Leila, Henrik, Noa, Ingrid, Priya,
  Kwame, Mei, Isabel=Presidenta, Alex), en engine/committee.js (CAST/avatarSvg).
- CANVAS IA (subagente): router intención+confianza en engine/localcharts.js (local solo con confianza
  ≥0.75; si no → IA con hints; sin IA → tarjeta honesta + respuesta parcial correcta), criterio de tipo de
  gráfico (core/canvas_spec.py validate_spec corrige lo que elige la IA), renderers nuevos (KPI, donut,
  histograma, barras agrupadas, heatmap, treemap squarified). tests/test_canvas.py.
- COMITÉ DE CARTERA: `core/portfolio_advisor.py` (riesgo medido + PERFIL conservador/moderado/agresivo +
  convicción de la Pizarra → acciones: vender, reducir, consolidar, aumentar, añadir nueva para
  diversificar; salud 0-100; explicación IA con guardián o determinista; disclaimer IA). POST
  /api/committee/portfolio. UI: Comité → 💼 Mi cartera (engine/pfcommittee.js): perfil de 4 preguntas
  (incluye NIVEL DE INVOLUCRAMIENTO; localStorage kh_investor_profile, window.KhipuProfile), fuentes
  MKT.pos / carteras simuladas / bróker (PIN), gráficos, "Aplicar en simulación" (KhipuPortfolios._buy/_sell).
- FRESCURA: matrix/engine.active_factors devuelve since/updated; insights prefieren factores ≤45 días y
  marcan los viejos como ESTRUCTURALES con su fecha (la IA no puede presentarlos como noticia); el banner
  de inicio dice NUEVO vs ESTRUCTURAL y "desde <mes año>".
- PENDIENTE (pedidos 2026-10-02): reportes diarios/mensuales/a pedido vs posición inicial con gráficos y
  "notebook" sobre la cartera; noticias en vivo según la cartera; terminal más estética; pop-ups al
  comprar/vender.

# SESIÓN 2026-10-02 (noche) — ANÁLISIS MÁS PROFUNDO + CONCLUSIONES EN TODAS PARTES (sw v179)

Pedido: "mientras duermo, dale con todo, haz algo grande" (tema: análisis mejores, conclusiones ya).
- `research/analytics.py` (NUEVO, puro): fundamental_ratios (crecimiento interanual y compuesto,
  márgenes y su tendencia, caja/deuda neta, deuda/EBITDA, rendimiento FCF y P/FCF con la capitalización en
  vivo, ROIC/ROE, dilución), technical_indicators (1 año: medias 50/200, RSI14, máximo/mínimo 52s, máxima
  caída, rendimientos 1/3/6/12 m, fuerza relativa vs SPY), peer_table (P/E, márgenes, crecimiento vs mediana
  de pares del grafo con perfiles en vivo). Entran como evidencia source_type='analysis' (fresca).
- `research/context.py`: noticias de la empresa con RESUMEN (Finnhub company-news, 30 días) + GDELT;
  velas de 1 año + SPY; fundamental/risk_observation reciben ratios; fundamental recibe pares (no QUICK).
- `research/runner.py`: agentes EN PARALELO (_prepare_run / _agent_work en hilos / _finish_run en el hilo
  del job; RESEARCH_PARALLEL=3). run_agent sigue existiendo (secuencial).
- `research/errors.py`: errores en lenguaje simple con qué hacer (saldo, clave, modelo retirado, límite,
  presupuesto, timeout, validación) → hint_es/en en /api/research (runs) y en la sala del comité.
- `core/numbers`: porcentajes/múltiplos ("1.38 %", "12.5x") y fechas ya no respaldan cifras de dinero.
- Comité → 📋 Pizarra (pestaña por defecto sin empresa): GET /api/committee/board (convicción, mejor
  argumento a favor/en contra, contradicciones, última decisión y conclusión) + POST /board/refresh
  (hasta 3 empresas viejas >7 días o clave si está vacía; en serie en un hilo; 4/h).
- Khipu chat/voz y MCP: herramienta get_conclusions_board; get_committee_memo resume el debate.
- Brief matinal: tarjeta 🏛 Conclusiones (abre la Pizarra) y textos bilingües.

# SESIÓN 2026-10-02 (b) — COMITÉ CON ANÁLISIS REAL DE IA + INVESTIGACIÓN QUE NO SE CAE (sw v176)

Feedback: "la investigación falló; el comité se siente falso, no tarda nada, casi no hay análisis real;
quiero que la IA haga lo suyo y que ya salgan conclusiones".
- `research/debate.py` (NUEVO): Ronda 1 = cada puesto RAZONA con IA (SeatStatement: postura, titular,
  argumento 3-6 frases, qué vigila, qué le haría cambiar de idea, convicción, refs) sobre SUS claims +
  razonamiento + extractos de evidencia + D1/R1 + resumen de los otros; Ronda 2 = hasta 3 réplicas entre
  posturas opuestas (Rebuttal: respuesta, qué concede, postura final). 3 en paralelo; la base solo se toca
  en el hilo del comité (AgentRun committee_seat/committee_rebuttal → cuenta para el presupuesto).
  Guardián de cifras + refs válidas; si un puesto falla → su plantilla. El debate entra al paquete del
  presidente como S# (citables). Sin IA/presupuesto → aviso ⚠ honesto en la sala y en el memo.
- `research/committee.py`: si hay < 2 claims activas y hay IA → ENCARGA la investigación (4 analistas por
  defecto, etapa 'research', narrada en la sala vía execute_job(on_start/on_done)). ChairMemo +
  key_conclusions (3-5 conclusiones; el determinista también las arma). memo.memo.debate =
  {ai, n_ai, n_rebuttals, reason, seconds}. No se reutiliza un memo SIN debate de IA. RUNNING_STALE_MIN 20.
- `research/agents/base.py`: RESCATE en el último intento — se quitan refs inexistentes y se descartan
  SOLO las claims con cifras sin respaldo (antes una cifra mala tiraba todo el agente → "falló").
- `core/numbers.evidence_numbers`: ignora fechas (el "09" de 2026-09-29 respaldaba "$9,999 mil millones").
- UI: etapas 🔬 Investigación y 🗣 Debate, insignia 🧠 IA · N s en cada burbuja, titular en negrita,
  "✅ Conclusiones del comité" arriba, nota de debate (o aviso ⚠ sin IA), sondeo hasta 15 min.
- Pendiente: NO pude ver el error real de la investigación en producción (el sandbox no llega a Railway):
  si sigue fallando, mirar 🩺 Sistema → IA (proveedor/saldo/modelo retirado) o el error por agente en 🔬.

# SESIÓN 2026-10-02 — SALA DEL COMITÉ: PUESTOS + DEBATE EN VIVO (sw v175)

Pedido: "que el comité esté más claro y en vivo, que tenga puestos, que se vea su comunicación".
- `research/deliberation.py` (NUEVO, puro): puestos = un analista por agent_type con conclusiones
  (postura neta a favor/en contra/neutral, fiabilidad, aciertos) + mesa fija (📡 mercado, 🛡️ riesgo,
  👤 mandato, 🧮 núcleo cuantitativo, 🏛 presidente). Mensajes = PLANTILLAS sobre datos reales: el
  texto de la claim de mayor peso + su fuente principal (ResearchEvidence), réplicas a partir de las
  contradicciones X#, precio D1, riesgo R1, la cuenta Q1 y el veredicto/respuestas al disenso del
  presidente. NO hay llamadas extra a la IA (cero costo, cero cifras inventadas).
- `research/committee.py`: `progress_say` publica los mensajes EN VIVO en el registro de progreso
  (GET /api/committee/memo/<id> → progress.messages + progress.seats); al terminar quedan en
  memo.memo['transcript'|'seats'|'tally'] (JSON, sin migración). MCP y modo sync limpian el progreso.
- `engine/committee.js`: "🏛 Sala del comité" — mesa con avatares (anillo verde/rojo/gris al hablar,
  el que habla brilla), chat con burbujas (postura, tipo, refs [C#], 📎 fuente), "● EN VIVO",
  revelado de 1 mensaje/s, ▶ Repetir la sesión, tira compacta de etapas. Memo: decisión + votos
  (👍/👎/✋) arriba → sala → "Tu decisión" → detalle técnico. "?" committee_room. Bilingüe, 375px OK.
- Tests: test_sala_del_comite_puestos_y_conversacion + test_deliberacion_sin_conclusiones (755).
- Memos viejos (sin transcript) muestran "vuelve a correrlo para ver el debate".

# SESIÓN 2026-09-30 → 10-02 — MONITORES, RIESGO FÁCIL, ASISTENTE, CEREBRO DE KHIPU (sw v174)

- Espacio = Space Monitor (core/space.py /api/space2/*, engine/spacemonitor.js):
  globo con satélites reales + lanzamientos dinámicos (arcos, cuenta
  regresiva, línea de tiempo, empresas del grafo por misión).
- Reporte de riesgo fácil (engine/riskreport.js): "no me deja" era MKT.pos
  vacío → callejón sin salida. Ahora pantalla guiada (mis posiciones / cartera
  rápida en USD / ejemplos), semáforo y frases simples; detalle plegable.
- Carteras → 🤖 Asistente (core/portfolio_ai.py): preguntas + propuestas de
  2–3 carteras (determinista con precios reales + explicación IA); crea
  carteras SIMULADAS.
- Comité: pantalla de progreso por pasos (progress en memoria, GET /memo);
  bug: el sondeo pedía PIN sin tenerlo → giraba para siempre; memo huérfano
  tras reinicio → failed.
- Khipu "tonto": el router de la Cabina secuestraba preguntas con regex y lo
  no reconocido lo convertía en GRÁFICO; /api/ai/command solo veía nombres.
  Ahora core/khipu_chat.py (POST /api/khipu/chat, herramientas de solo
  lectura del MCP + noticias/movers/espacio, memoria, fuentes) +
  engine/khipu_chat.js (solo atajos explícitos). La VOZ usa el mismo cerebro
  vía la herramienta cliente ask_khipu_brain (ElevenLabs se re-sincroniza solo
  al arrancar el server).
- Railway: tras pagar seguía caído; se quitó drainingSeconds de railway.toml
  (no verificado en su esquema) y volvió. Recordar: Custom Start Command vacío.
- Tests: 753.
- PENDIENTE: verificar en prod GDELT/LL2/Alpaca OAuth; velocidad del mapa
  (#9); decidir trading agent / portfolio advice "comprar/vender";
  /api/ai/command quedó sin uso (borrable).

---

# SESIÓN 2026-09-30 — PHASE 3 + WORLD MONITOR + CORRETAJE + MCP + ENDURECIMIENTO (sw v170)

Pedido: "algo enorme mientras duermo": geopolítica como World Monitor en UN
globo 3D; Phase 3 avanzada para la reunión con Diego; invertir dinero de
otros vía Alpaca desde la próxima semana; MCP para que IAs inviertan con la
info de la ontología; "resueltos los detalles estructurales".
Hecho con 2 workflows (27 agentes: construir → 2 revisiones → corregir):
- World Monitor (core/world.py, engine/worldmonitor.js): GDELT/USGS/EONET +
  estrechos/inestabilidad, exposición de la cadena por evento, brief
  determinista, capas de referencia rotuladas; coordenadas de sede
  corregidas (~150 nodos estaban en Singapur); colores NRS del globo
  estaban invertidos. RIESGO: queries de GDELT GEO no verificadas en vivo →
  ajustables por env WORLD_GDELT_*.
- Phase 3 (research/outcomes, committee, committee_api, engine/committee.js):
  ver docs/PHASE3.md. El track record se llena con el tiempo (1×/día).
- Corretaje multi-cliente (brokerage/, engine/clients.js): ver
  docs/BROKERAGE.md. Falta en Railway: BROKERAGE_ENC_KEY (obligatoria para
  guardar llaves), OAuth de Alpaca (app registrada) si se usa.
- MCP (mcp_server/, engine/mcpconnect.js): ver docs/MCP.md. Verificado de
  punta a punta local (initialize → tools/list → get_company).
- Legal: docs/INVERSION_TERCEROS.md — NO juntar dinero de terceros en la
  cuenta propia (Alpaca ToS; Perú: Ley 26702 art. 11, CP art. 246); cada
  persona en SU cuenta, papel primero, abogado antes de dinero real.
- Endurecimiento (auditoría de 25 hallazgos): PIN único con bloqueo
  (core/pin.py), validación de trade_order/close (un símbolo malo podía
  cerrar TODO), client_order_id, el agente registraba órdenes rechazadas como
  éxito, SW ya no cachea API/errores, errores JSON, timeouts de IA y DB,
  Dockerfile exec, railway.toml ALWAYS, constraints.txt, REMIGRATE seguro,
  escrituras de ontología con PIN, XSS en enlaces, reclamo atómico de
  propuestas en auto_cycle. Tests: 668.
- PENDIENTE: verificar en prod GDELT GEO, Alpaca OAuth y drainingSeconds en
  Railway; backups de Postgres (activar en Railway); monitor externo de
  /api/health; decidir si /api/matrix/simulations exige PIN; UI para 409
  agent_stopping / 423 trading_halted; el kill switch es solo por env (y
  bloquea también cierres).

---

# SESIÓN 2026-09-29 (día) — REPORTE DE RIESGO: VaR + VEGA/KAPPA (sw v164)

Pedido (curso MIT): "reporte Vega" para medir la sensibilidad a la volatilidad
+ Delta, Gamma, Theta. Hecho:
- core/risk_report.py + POST /api/portfolio/risk_report: precios diarios
  REALES 1 año (Yahoo ajustado) → volatilidad, VaR 95/99 histórico y
  paramétrico (1 d y 10 d √N), CVaR, contribución al riesgo, beta/corr vs SPY,
  correlaciones, drawdown, Sharpe (rf 0), diversificación, peores días,
  backtest del VaR. Lo sin datos se EXCLUYE y se dice.
- core/options.py + POST /api/portfolio/vega_report + GET
  /api/options/chain/<sym>: Black-Scholes (verificado con Hull: 4,76/0,81),
  griegas por contrato ×100, IV EN VIVO del contrato (si no, histórica
  rotulada), tasa ^IRX, escenarios de volatilidad con revaluación completa.
- engine/riskreport.js (KhipuRisk.open): pestañas VaR / Vega-Kappa, fuentes
  Mercado (MKT.pos) / Carteras simuladas / manual; opciones en localStorage
  'kh_options' (no ejecuta órdenes); griegas por empresa (acciones = Delta);
  imprimir/PDF; "?" de cada métrica (explain.js: delta/gamma/theta/vega/iv…).
- Accesos: botón en Mercado, 📉 Riesgo en Carteras, PORT VAR (antes mostraba
  NaN%) y PORT VEGA. /api/portfolio-risk y /v1 intactos. Tests: 277.

---

# SESIÓN 2026-09-29 (noche) — TODO EN VIVO + AUDITORÍA DE DATOS FALSOS (sw v161)

Pedido: "dale con todo mientras duermo". Hecho y desplegado:
- CAPITALIZACIÓN EN VIVO DE TODO EL GRAFO: core/quotes.fetch_quotes_batch_yahoo
  (lote v7) + core/live_caps (hilo, caché 15 min, no borra lo último bueno) +
  GET /api/market/live_caps + KhipuLiveCaps (app.html) que pisa
  NODE_META.mktcap_b (guarda mktcap_catalog, mktcap_live={as_of,source}).
  window.liveCapDot(meta): ● verde si vivo, "cat." gris si es del catálogo.
- SEC como evidencia primaria (core/sec.py): 10-K/10-Q/8-K + Risk Factors/MD&A
  para agentes fundamental/noticias/riesgo.
- War Room: signos de impacto estaban INVERTIDOS (server pct con signo vs
  "daño positivo"); debate fijo con cifras inventadas y "Corto NVDA" borrado →
  rondas/razones reales; respaldo sin IA = KhipuState (determinista,
  severidad 0-100 rotulada); trayectorias Math.random fuera; banner 🧪.
- sim_agents: sin empresas en el escenario ya no inventa chokepoints (las toma
  del texto o responde no_seeds); fallback=True + seeds → el cliente usa el
  motor estructural.
- PRICE_ANOMALY automático (research/auto_events.py; RESEARCH_AUTO_EVENTS=on,
  RESEARCH_ANOMALY_PCT=8, _MAX=3). Contradicciones entre temas relacionados.
- Auditoría (agente): análisis IA ya no da "FUERTE COMPRA/VENDER" (salud del
  negocio); consenso de analistas con conteos reales; prompt de Khipu sin
  estadísticas inventadas; Espacio sin "$630B/7,200+" fijos; gráfico 3D sin
  CAP_B fija; Cabina "Dónde invertir" → "Empresas resilientes"; brief sin
  "conclusión accionable"; portafolio sin "$10 simbólico".
- PENDIENTE de la auditoría (decisión de Fabrizio): el agente de trading da
  buy/sell (lo arranca el usuario, modo papel); /api/portfolio/advice propone
  "Incluir/Reducir"; tesis del investigador autónomo usan long/short; chips
  "Cartera 1/2"; MKT_CAP_EST del radio de nodos; nodes/*.js estáticos
  (revenue_2025, growth, margin) sin fecha.

---

# SESIÓN 2026-09-28 (e) — PHASE 2: AGENT RESEARCH SWARM (sw v153)

Pedido: la especificación completa de Phase 2 ("dale con la Fase 2").
Hecho (vertical slice NVIDIA → Investigar → agentes → claims/evidencia → UI):
- `research/` nuevo: models (5 tablas), schemas (salida estructurada con
  vocabulario cerrado; refs E# inventadas → rechazo), llm (LLMProvider
  multi-modelo con reintento/reparación y fallback; env RESEARCH_MODEL_*),
  context (paquete de evidencia numerado + defensa anti-inyección), confidence
  (calculada, componentes guardados, tope 0.6 con una sola fuente),
  contradictions (POTENTIALLY_CONTRADICTS solo mismo tema+horizonte),
  runner (jobs, dedupe, presupuesto diario, supersesión, síntesis sin
  COMPRA/VENTA), router (evento → entidades relevantes acotadas → agentes),
  api (/api/research/*: jobs, entity, claims/<id> = ¿POR QUÉ?, activity,
  agents, budget, events).
- UI: `engine/research.js` (overlay 🔬 por agente, vista ¿Por qué?, choques,
  síntesis por horizonte, actividad REAL), sección en la ficha del mapa,
  botón en el X-Ray, comando `NVDA RESEARCH`, "?" de confianza y horizonte.
- Eventos automáticos: /ingest/news dispara NEWS solo si
  `RESEARCH_AUTO_EVENTS=on` (apagado por defecto para cuidar costo).
- Tests: tests/test_research.py (16) → suite 249.
- VERIFICADO EN PRODUCCIÓN (28-sep, Fabrizio): investigación real de Nvidia
  OK con Gemini. Arreglos que hicieron falta en prod: (1) SQLAlchemy 2.1 →
  psycopg 3 por defecto → fijado <2.1 + _normalize_url(+psycopg2); (2) Gemini
  2.5-flash cortaba el JSON (el pensamiento consume maxOutputTokens) →
  json_mode (responseMimeType, thinkingBudget 0, 8192); (3) job con todos
  los agentes fallidos queda 'failed' y el dedupe no lo reutiliza; (4) sin
  ventana de nombre (actor = khipu_actor o 'usuario'); (5) errores visibles
  con código+detalle en el panel. Claude sin saldo; NVIDIA_MODEL retirado
  (410) — Fabrizio iba a poner uno nuevo de build.nvidia.com.
- GUARDIÁN DE CIFRAS (research/numbers.py): "Broadcom ~$350B" (memoria del
  modelo) vs >$1T en vivo → toda cifra de dinero debe estar en la evidencia o
  se rechaza/reintenta; claims viejas con cifras sin respaldo → 'retracted'.
  Extendido a TODA la IA: core/ai._ai_complete (tesis/veredicto, brief,
  War Room, Canvas, Khipu, deep research, cripto, portafolio, matrix
  insights…) → regla en el system + verificación contra el input + 1
  reintento + marca "(⚠ cifra no verificada)". + core/live_facts.py: a todo
  prompt se le anexan DATOS EN VIVO (cap. y precio) de las empresas
  mencionadas; privadas → última valuación verificada con fecha. PENDIENTE:
  NODE_META.mktcap_b del catálogo sigue estático (la UI lo pisa en vivo).
- Pendiente: verificar en producción una investigación REAL (Claude sin
  saldo → correrá con Gemini); contradicciones semánticas; eventos
  EARNINGS/PRICE_ANOMALY/FACTOR_FIRED automáticos; evidencia SEC; calibrar
  la confianza con resultados reales. Ver docs/ROADMAP.md.

---

# SESIÓN 2026-09-28 (d) — Valuación de PRIVADAS en vivo (sw v152)

"OpenAI dice $500B y está por $1T — la idea es que siempre sea en vivo".
Una privada no tiene precio de bolsa → dos capas, siempre con fecha y fuente:
- VERIFICADA: `nodes/private_valuations.js` (GENERADO por
  scripts/build_private_valuations.py desde data/private_valuations/*.json;
  54 empresas: OpenAI $852B mar-2026 (+ negociación ~$1.2T), Anthropic $965B,
  Anduril $61B, ShieldAI $12.7B, ElevenLabs $11B, Databricks $190B, Groq
  $3.5B (bajó)…). Actualiza PREIPO_INTEL[id].valuation y (merge_graph, env
  PRIVATE_VALUATIONS) el texto "Pre-IPO ~$XB" del ticker.
- EN VIVO: `/api/company/valuation/<nombre>` → core/company_data.
  get_valuation_news: GDELT (6 meses) + extracción por PATRÓN en titulares
  (sin IA; en/es, "billones"=trillion), separa "reportada" de "en
  negociación"; caché 30 min. El Dossier de privadas lo muestra (medio,
  fecha, titular) y lo revisa cada 30 min; la ronda verificada va primera en
  "Rondas".
- Sin verificar (quedan con el catálogo): 1X, TerraPower, CFS, Axiom, Zap,
  Waabi, AgiBot, Tenstorrent, Poolside, Physical Intelligence… y ~70 no
  revisadas (Bluefors, Zeiss, Trumpf, Rapidus, DeepSeek…).

---

# SESIÓN 2026-09-28 (c) — DOSSIER PARA TODAS LAS EMPRESAS + DATOS EN VIVO (sw v151)

Pedido: "que todas las empresas tengan dossier y que la info se actualice en
vivo". Hecho con workflow (3 implementadores en paralelo → 4 revisores →
2-3 escépticos por hallazgo → fixers) + segunda revisión de regresiones.
Hallazgo GRAVE previo: el Dossier de Análisis (`_dossierSynthetic`)
INVENTABA ingresos/márgenes/ROE con Math.random cada vez que /api/dossier
fallaba — y fallaba siempre (usaba FMP /api/v3, que el plan de prod no da).
ELIMINADO: sin datos → mensaje honesto con las fuentes probadas.

- `core/company_data.py` (nuevo): `get_annual_financials` (FMP /stable →
  Yahoo fundamentals-timeseries → Alpha Vantage solo EE.UU.; montos a USD con
  el tipo de cambio ACTUAL — la UI lo dice; caché 12 h completos / 1 h
  parciales / 10 min fallos; candado por ticker + candado global de caché) y
  `get_live_profile` (Yahoo quoteSummary con crumb → Finnhub → Yahoo chart;
  caché 90 s). Transformaciones puras testeadas (tests/test_company_data.py).
- Rutas: `/api/findossier` y `/api/dossier` reescritas sobre eso (mismas
  claves/unidades; `synthetic:false` siempre; sin datos → 200
  available:false). NUEVA `/api/company/live/<ticker>`. GDELT: caché manual
  5 min solo de éxitos (antes 30 min incluyendo fallos).
- engine/fincard.js ("📊 Dossier"): franja EN VIVO (precio, cap., empleados,
  ingresos 12 m, márgenes, rango 52 sem., objetivo, P/E) refrescada cada 60 s
  y que dice la hora REAL del precio y si el mercado está abierto; 8 gráficos
  con la fuente real; sin estados → franja + acción + nota (nunca vacío).
  No cotizadas (privada, filial, comprada, organismo) → dossier con ficha,
  nota verificada, franja del DUEÑO rotulada "cifras del dueño", noticias
  GDELT en vivo (5 min) e Historia. "⇄ Comparar en Análisis" para cotizadas.
- app.html: botón 📊 Dossier para TODOS los nodos (vía `_surface('dossier')`,
  queda al frente de la Cabina); `window.KhipuLive.profile(t)` (caché 60 s;
  live.js ahora FUSIONA su tick/cycle en el mismo objeto); ficha del mapa y
  X-Ray pintan empleados/ingresos/cap. EN VIVO con fuente y hora; precio del
  X-Ray se refresca cada 60 s (se salta si está oculto, se apaga si se
  desconecta); Dossier de Análisis bilingüe y redibujo diferido si la pestaña
  está oculta. cockpit.js/localcharts.js dicen la fuente real.
- DATOS: divisiones que usaban el ticker del dueño (IBMQuantum→IBM,
  Qwen/AlibabaCloud→BABA, SiemensEDA→SIE.DE, CyrusOne→KKR, DataBank→DBRG,
  ABB_Robotics→ABBN.SW) pasan a `subsidiary` (listing_verification/
  2026-09-28_divisiones.json) — antes el "en vivo" les pintaba empleados e
  ingresos de IBM/Alibaba como propios. merge_graph.js: una pre-IPO sin
  estado "public" verificado NO cotiza → mkt=null (31 tickers de relleno
  tipo FIGURE/GROQ/PERPLEXITY). Quedan 578 nodos con ticker real.
- Pendiente: ver en producción con Yahoo real (Tokio, Londres, EE.UU.); el
  sandbox no llega a Yahoo — todo probado con respuestas simuladas. War Room
  (_wrRenderPrices) aún genera trayectorias de precio simuladas sin rótulo.
- 231 tests.

---

# SESIÓN 2026-09-28 (b) — Estado en bolsa VERIFICADO (sw v142-143)

Fabrizio: "SpaceX me dice que no cotiza, y así con varias". El catálogo es
estático y envejece. Auditoría de 339 "privadas" + 565 cotizadas con 6
agentes (WebSearch; el cupo de 200 búsquedas de la sesión se agotó a mitad —
los hallazgos sin fuente abierta quedaron en confianza media/baja).
- `nodes/listing_status.js` (GENERADO por `scripts/build_listing_status.py`
  desde los JSON de verificación; solo cambios con fuente y confianza
  alta/media). Lo aplica `nodes/merge_graph.js` (env.LISTING_STATUS) en el
  navegador Y en el snapshot: public → mkt/ticker/preipo=false; acquired/
  merged/subsidiary → mkt=null + dueño; defunct → mkt=null. Rastro en
  `n.listing` {status, note_es/en, source_url, as_of…}; el X-Ray lo muestra
  ("✓ … · verificado 2026-09-28 · fuente ↗").
- 148 entradas. Ej.: SpaceX SPCX (IPO 12-jun-2026), xAI fusionada en SpaceX,
  Quantinuum QNT, Pasqal PSQL, IQM IQMX, Infleqtion INFQ, Xanadu XNDU, Zhipu
  2513.HK, Firefly FLY, General Fusion GFUZ, Enflame 688801.SS; compradas:
  Ansys→SNPS, Juniper→HPE, HashiCorp→IBM, Infinera→NOK, Altium→Renesas,
  Capella→IonQ, Hailo→MCHP, Calpine→CEG, Ampere→SoftBank…; tickers
  corregidos (PetroChina 0857.HK, SAIC Motor 600104.SS — "SAIC" era otra
  empresa —, Nanya 2408.TW, Powerchip 6770.TW, Eni ENI.MI); Aramco 2222.SR,
  MediaTek 2454.TW, SoftBank 9984.T… que figuraban sin ticker.
- Descartadas por falta de fuente: Luminar (quiebra dic-2025?), Rain AI,
  Unitree (salió a bolsa ago-2026 pero sin ticker confirmado).
- Pendiente de verificar con cupo de búsqueda nuevo: 18 "privadas" de
  confianza baja (Bluefors, Apptronik, Cognition…), Cerebras (¿cotiza?),
  X-energy, tickers sin sufijo de bolsa (4004, 8411, BARC, AM=Antero ≠
  Dassault…), Confluent→IBM, Verint, Axcelis+Veeco, ABB Robotics→SoftBank,
  Northern Data→Rumble. Eventos pendientes (OpenAI/Anthropic S-1
  confidencial, Westinghouse IPO oct-2026, Nscale NSCL, Hugging Face→Nvidia)
  NO se aplicaron: siguen "privada" hasta que cierren.
- Para refrescar: nueva verificación → build_listing_status.py → export.
- v144: "SpaceX me sigue saliendo pre-IPO" — la marca ya estaba apagada pero
  los TEXTOS de la ficha lo decían ("⭐ PRE-IPO ~$350B", "Mayor empresa
  privada", "(privada, estimado)"). merge_graph.js ahora reescribe growth/
  growth_en al aplicar el estado (public → "🟢 En bolsa (SPCX) desde …";
  comprada/fusionada → "🔄 <nota>"); rol e ingresos de SpaceX corregidos en
  la fuente (nodes_spacex.js / meta_fill.js).
- v145: 47 tickers SIN sufijo de bolsa corregidos (4004→4004.T, BOE→BOE.AX
  — "BOE" en EE.UU. es un fondo de BlackRock —, ADV→ADV.DE — ADV es
  Advantage Solutions —, AM→AM.PA — AM es Antero Midstream —, BARC→BARC.L…).
  core/quotes.py ya enruta símbolos con "." a Yahoo con conversión a USD, así
  que ahora traen precio real. Entradas de verificación guardadas en
  data/listing_verification/ (auditoría + tickers_sin_bolsa); regenerar con
  `python3 scripts/build_listing_status.py data/listing_verification/*.json`.
- v146-147: "Mizuho es privada" → Mkt Cap mostraba "Privada" si faltaba el
  dato (505 de 618 cotizadas no lo tienen en NODE_META). Ahora "—" si cotiza,
  y /api/fundamentals devuelve `marketCapB` EN VIVO (Finnhub
  metric.marketCapitalization — se pedía y se descartaba — o perfil FMP ×
  tipo de cambio). `window.fillLiveMcap(el, n)` lo pinta en la ficha del mapa
  (#d-mcap) y el X-Ray (.xr-mcap). Caché cliente renombrada fund_→fund2_.
  Comparador (compare.js) bilingüe.
- v148 ("todavía no sale"): tres causas más. (1) caché del SERVIDOR de
  /api/fundamentals (24 h) seguía entregando la respuesta vieja → clave
  fund2_; (2) FMP free no cubre Tokio/HK/Europa → tercera vía
  `core/quotes.fetch_market_cap_yahoo` (v7/quote con crumb de sesión, caché
  6 h, moneda de cotización → USD; GBp→GBP); (3) la ficha del mapa y el X-Ray
  solo pintaban la rejilla con `meta.founded` → ahora también si cotiza.
  Caché cliente fund3_. Ojo al probar con Playwright: el service worker
  salta page.route → usar serviceWorkers:'block'.
- v149: pendientes verificados con búsquedas (data/listing_verification/
  2026-09-28_pendientes.json): Cerebras CBRS (IPO 14-may-2026; el catálogo
  decía "IPO 2024"), X-energy XE en Nasdaq (24-abr-2026), Unitree 688836.SS
  (19-ago-2026), Confluent→IBM (17-mar-2026), Verint→Thoma Bravo, Luminar
  liquidada (abr-2026), Northern Data→RUM, CommScope: su negocio y marca →
  Amphenol (APH; el resto cotiza como VISN), SMIC→0981.HK, Moog→MOG-A,
  Globalstar en Nasdaq. Fusiones ANUNCIADAS sin cerrar (Axcelis+Veeco,
  Qorvo+Skyworks, SLAB→TI, AES→GIP/EQT, Globalstar→Amazon, ABB Robotics→
  SoftBank) siguen cotizando con nota. Las 20 startups dudosas: siguen
  privadas.

---

# SESIÓN 2026-09-28 — X-Ray pulido (sw v139)

A partir de la captura de Fabrizio (X-Ray de la Reserva Federal, ya en prod):
- engine/xray.js BILINGÜE completo (helper `L(es,en)`); los términos del NRS
  (computeNRSBreakdown en app.html) también.
- `growth` que es una FRASE (capa macro) ya no se mete en el cuadrito de 3
  columnas (salía una torre ilegible): va como nota debajo; `geo_risk` en
  texto normal (antes MAYÚSCULAS vía .tcap).
- "Calculando propagación…" podía quedarse PARA SIEMPRE (0 vínculos o el
  servidor respondía sin impactos): ahora siempre cierra con un mensaje
  (actor macro → se simula con FACTOR LIST).
- Sin ticker: "no cotiza en bolsa" en vez de "— · —". Sin vínculos: se dice.
- v140-141: BILINGÜE también la Cabina (cockpit.js: `actChips()` +
  `relabelShell()` re-etiquetan al abrir; matchers aceptan "break down",
  "compare … and/with", "opportunit", "blank canvas"), el panel ◉ En vivo
  (livesim.js: TYPES/PRESETS con es/en, `applyLang()` al abrir), el Dossier
  (fincard.js), la Guía (reescrita: 949 empresas, ⏱, 📡, teléfono; quitado el
  aviso "Nueva versión" que ya no existe; se rehace al cambiar idioma), las
  pestañas primarias y el subtítulo del botón Khipu. `window.sectorName(key,
  byCat)` da el nombre de sector en el idioma activo (SECTORS9 ya traía `en`).
- Queda en español: CONTENIDO del catálogo (descripciones, geo_risk, hitos) —
  es dato, no UI; traducirlo sería otro proyecto. graph3d.js (solo ?webgl3d=1).

---

# SESIÓN 2026-09-27 (c) — Feed global "📡 Lo último en el grafo" (sw v138)

- `global_feed()` en ontology/timeline.py + `GET /api/ontology/feed`
  (?limit&lang&since). Por `recorded_at` desc (desempate valid_from). Filtra
  migración/precios/Fuentes/vínculos de procedencia; una noticia = una
  entrada con las empresas sobre las que informa (`reports_on`).
- Títulos de relación legibles y bilingües ("suministra a Nvidia" en vez de
  "supply → Nvidia") — también en la Historia de cada empresa.
- UI: sección 📡 en el panel derecho del mapa cuando no hay empresa elegida
  (V8feed en app.html; se refresca como mucho 1/min al deseleccionar; se
  oculta sin ontología). Empresa clicable → jumpTo.
- KHIPU `FEED [n]`; además FEED/INSIGHTS/MATRIX/PORT funcionan como UNA sola
  palabra (antes exigía 2 y caían a la IA).
- M2 cerrado también: nombres DUDOSOS del tejedor de hiperaristas → propuesta
  para humano (ver ROADMAP_PHASE1). 202 tests.
- Pendientes de Phase 1 que quedan (ninguno bloquea): persistir aliases/
  external_ids en props, CIK/ISIN/LEI, migrar /api/quote a la capa de
  proveedores, FMP+get_history, CorporateEvent N-ario, SEC EDGAR como fuente,
  bus de eventos, frescura por dato en más sitios. Y Velocidad paso 2
  (enlaces a canvas), aplazado por riesgo.

---

# SESIÓN 2026-09-27 (b) — Nombres: búsqueda por nombre legal + etiquetas legibles (sw v137)

- `nodes/legal_names.js` (nuevo): 159 nombres legales/alternativos → id
  ("Taiwan Semiconductor Manufacturing Company"→TSMC, "Google"→Alphabet,
  "Hon Hai"→Foxconn, "Aramco"→SaudiAramco…). Una tabla, dos resolvedores:
  engine/resolve.js (window.LEGAL_NAMES) y core/entities.py (`legal_names` del
  snapshot, que ahora exporta scripts/export_graph_v0.js). Cierra el pendiente
  de M2. Test que vigila ids rotos.
- 148 etiquetas VISIBLES de nodes_multicapa.js estaban pegadas
  ("GoldmanSachs", "NextEraEnergy", "RioTinto"): ahora "Goldman Sachs"… Los
  ids NO cambian. Marcas reales (OpenAI, SpaceX, CoreWeave…) intactas.
- IGO tenía de etiqueta una nota interna ("IGO (inicio — continúa en
  archivo…)") → "IGO".
- OJO: la base de producción (original, 1.294 objetos) conserva las etiquetas
  viejas en la ontología hasta que alguien las actualice; el mapa y los
  resolvedores ya usan las nuevas. NO usar REMIGRATE para esto.
- 198 tests.

---

# SESIÓN 2026-09-27 — La app en el TELÉFONO (sw v136)

Probado con Playwright en iPhone SE (320), iPhone 13 (390), Pixel 5 (393) e
iPad Mini (768). Causa raíz: la fila de botones del header medía 445px en un
iPhone de 390 → el navegador encogía TODA la app a 476px (letra diminuta, todo
cortado a la derecha). Arreglos (bloques `@media` 820/560 en app.html):
- ≤560: se ocultan ⟲ y el reloj LIVE (`#hdr-live`); Khipu = solo orbe
  (`.bixby-btn-txt` oculto); título con elipsis. Resultado: ancho = pantalla.
- ≤560: pestañas primarias y sub-pestañas en UNA fila deslizable (antes 3
  filas + "❓ Guía" cortada); nav4.js desliza hasta el modo activo.
- ≤820: ◱ Capas bajo la franja de sectores, ◉ En vivo arriba-der, zoom/🪐/⏱
  en columna derecha sobre el ❓; barra ⏱ sin tapar el ❓; al abrir ⏱ se oculta
  el aviso "toca una empresa".
- Ficha: la fila NRS/Second Brain/Dossier/SEC hace wrap (se cortaba).
- Simulación: 1 columna (`.sim-grid`). Terminal: lista arriba (44%), gráficos
  abajo, arranca con 1 panel; y TOCAR una empresa la abre en el primer panel
  libre (antes solo arrastrar → inútil en táctil). La regla móvil de
  termdata.js (lista 150px al costado) queda pisada por `#terminal-panel #term-sidebar`.
- Cabina: decía "BIXBY" (marca de Samsung) → "KHIPU".
- Escritorio verificado sin cambios.

---

# SESIÓN 2026-09-25 — El Grafo Temporal se fusiona con el mapa principal

Fabrizio: "el grafo temporal y el normal deberían ser uno; el temporal no da
mucho por sí solo". Elegido "Todo a la vez". **engine/maptime.js** (nuevo):
- Botón **⏱** en `.zoom-ctrl` (debajo de + − ⤢ 🪐 — la barra de filtros queda
  tapada en pantallas chicas). Abre una barra de tiempo sobre el mapa: ▶,
  slider 1970→hoy, fecha, **⚡ Eventos**, **☰ Hechos**, **⬗ 3D**, ✕ (vuelve a hoy).
- En la fecha T se apagan las empresas aún no fundadas (`NODE_META.founded`) y
  los vínculos cuyo par tiene un hecho fechado posterior a T. Vínculo sin fecha
  = presente si existen sus dos empresas (NO se inventan fechas).
- ⚡ Eventos: hechos de `TEMPORAL_SEED_FACTS` con ambos extremos en el mapa (31
  hoy) como líneas punteadas color-relación, visibles solo en su ventana;
  `<title>` = fecha + titular; clic → jumpTo. Con ⚡ activo los vínculos
  normales bajan a .1 para que resalten.
- Enganches en app.html: `window._mapLayers`, `_paintGraph` llama
  `_mapTimePaint`, `_refreshStylesCore` consulta `KhipuMapTime.nodeOk/linkOk`,
  `window.refreshStyles`, `applyLang` → `KhipuMapTime.relabel()`.
- Pestaña ◈ Grafo Temporal QUITADA de la barra; `#tkg-panel` sigue vivo como
  vista (`window.__tkgShow('facts'|'t3d'|'viz')`, botón "← Mapa"), igual que
  `__tkgOpenObj`, `_xrayTKG`, cockpit stage 'tkg'. `GRAPH ASOF` mueve el MAPA.
- Probado en Chromium headless (jun 2005: 622/949 empresas, 1.380 vínculos;
  jun 2024: 16 eventos vigentes). 195 tests. sw v134.
- v135: hechos empresa↔CONCEPTO (EUV, Ley CHIPS, China, galio… = ONT_*) y
  atributos literales se anclan como ANILLO punteado alrededor de la empresa
  (apilados +4px). Dibujables: 31 → 94 de 105 (los 11 restantes son
  concepto↔concepto, p.ej. SMR→Red eléctrica; siguen en ☰ Hechos). Colores
  de verbos desde ONTOLOGY.rels. El filtro de fecha también aplica con una
  empresa seleccionada.

---

# SESIÓN 2026-09-22/24 — PHASE 1 "Live Investment Graph" COMPLETA + velocidad + 3D temporal

Spec de Fabrizio ("Live Investment Graph V1"). Auditoría primero
(`docs/ARCHITECTURE.md`): el 60-70 % ya existía — event store bitemporal,
hipergrafo real, motor de matrices, Acciones auditadas. Faltaban tres capas.
Plan y estado en `docs/ROADMAP_PHASE1.md`. **193 tests.** sw v131.

**Decisiones de fondo (no reabrir sin razón nueva):**
- **Seguir en PostgreSQL**, sin Neo4j como fuente de verdad ni Apache AGE: el
  modelo temporal ya vive ahí y la propagación es álgebra matricial, no
  traversals. Neo4j Aura se borró sola por inactividad — prueba de que otro
  almacén es otra cosa que se cae.
- **No reorganizar el repo ni reescribir la UI a React**: la separación que pide
  el spec ya existe con otros nombres (core/ = shared+providers, ontology/ +
  matrix/ = domain+graph, server.py = api, app.html+engine/ = web).

**Milestones:**
- **M1 Procedencia** (`ontology/provenance.py`): `Source` como ENTIDAD (el tipo
  ya estaba en vocabulary.json sin código), id = `src_<sha1(url normalizada)>`,
  `trust` del `source_kinds` del vocabulario, `Event.source_id` + `confidence`.
  `GET /api/ontology/sources`, `/objects/<id>/provenance`.
- **M2 Identidad** (`core/entities.py`): EL resolvedor server-side (sustituye a
  3 divergentes). `NODE_ID_ALIAS` ahora se EXPORTA al snapshot (antes moría en
  la frontera cliente→servidor). Umbrales ESCRITURA 85 / BÚSQUEDA 60.
  `agents._resolve` lo usa → "NVIDIA Corporation" ya no se pierde en silencio.
- **M3 Proveedores** (`core/providers/base.py` + `market.py` + `news.py`): el
  `base.py` que el docstring citaba desde julio y nunca existió. Esquema único
  con `as_of`/`age_seconds`; "sin configurar" ≠ "falló"; `subscribe_*` lanza
  NotImplementedError A PROPÓSITO (no hay streaming, no se finge).
  `GET /api/market/quote/<sym>`, `/api/market/providers`.
- **M4 Noticias al grafo** (`ontology/ingest_news.py`): `NewsItem` + `Source` +
  `reports_on`/`published_by` (declarados sin código). `valid_from` = fecha de
  PUBLICACIÓN. Vínculo por construcción, no por adivinanza. Una noticia NO crea
  empresas. `POST /api/ontology/ingest/news`, `GET /objects/<id>/news`.
- **M5 Graph API**: `/search` server-side, `/events/<id>`,
  `/objects/<id>/timeline` (`ontology/timeline.py`: eventos + noticias, por
  validez, con fuente, bilingüe).
- **M6 UI**: la ficha del Grafo Temporal muestra la línea de tiempo con
  enlaces a la evidencia y punto de confiabilidad; SUSTITUYE al mini-registro
  de acciones (lo contiene) en vez de añadir botón.

**Producción — lo que pasó y cómo se arregló:**
- La base NO se había borrado: se había roto el cable (`DATABASE_URL` apuntaba
  a `postgres.railway.internal` y el servicio no resolvía). Al reconectar volvió
  la base ORIGINAL: **1.294 objetos, último evento 2026-08-27**. ⚠️ **NO correr
  REMIGRATE_ON_BOOT sobre ella**: tiene ~216 objetos (empresas históricas,
  tesis, anotaciones) que el repo no puede reconstruir.
- Bug de arranque (mío, M1): Railway lanza app y Postgres EN PARALELO;
  `init_schema` fallaba en el boot y no se reintentaba → `column
  events.source_id does not exist`. Ahora reintenta 6 veces y `_diag_ontologia`
  AUTO-REPARA (`schema_outdated()`): pulsar "Re-probar" en el 🩺 lo arregla.
- El 🩺 traduce errores a acciones (`_ai_error_hint`, `_db_error_hint`).
  Gemini funciona con `GEMINI_MODEL=gemini-3.5-flash` (puesto por Fabrizio).
  NVIDIA sigue con modelo retirado (mi `llama-3.3-70b` también lo estaba).
- Bugs latentes corregidos: `as_of_graph`/`diff_graph` reventaban con fecha en
  texto; `_log_action` no pasaba `source_id`; la re-migración perdía los 69
  factores y 28 asientos (viven en `data/multicapa_factors_seats.json`).

**Velocidad del mapa (confirmado por Fabrizio: "ta mejor"):** el mapa es SVG +
d3.forceSimulation — ~11.000 escrituras al DOM por fotograma × ~150 fotogramas
por arranque. Ahora `settleGraph()` adelanta la física en memoria
(`sim.tick()` no emite 'tick') y pinta UNA vez; solo el arrastre pinta en vivo
(`_liveTick`). `resize` amortiguado a 150 ms (en móvil llega en ráfaga).
Efecto visible buscado: los nodos aparecen colocados, sin baile inicial.

**3D temporal** (`engine/timeline3d.js`, modo "⬗ Tiempo 3D" de la pestaña
Temporal, sin pestaña nueva): Z = fecha de inicio de cada relación. Anillo de
empresas + cuerdas a la profundidad de su fecha. Solo hechos con fecha real
(86 relaciones, 71 empresas, 1926→2025, 1.862 vértices). Montaje perezoso y
dibujo bajo demanda (sin bucle continuo). Decisión explícita: **3D solo donde
la profundidad significa algo**; el 3D decorativo del mapa NO vuelve.

**Pendiente:**
- ✅ Velocidad paso 2 (2026-10-03) — RESUELTO DE OTRA FORMA, MEDIDO:
  se probó pasar los enlaces a `<canvas>` (shim con la misma API de linkSel)
  y NO mejoró (wheel-zoom 41→55 ms CPU/paso: redibujar el lienzo entero cuesta
  más que la transformación SVG compuesta) → REVERTIDO, no reintentar sin
  medir. El costo real eran las ~930 etiquetas `.node-label` con opacity:0
  (invisibles pero maquetadas/pintadas con halo). Ahora `.lbl-off` =
  display:none → wheel-zoom ~40 → ~19 ms CPU/paso, layout 12 → 3.4 ms, misma
  vista (21 etiquetas visibles, hover idéntico). Ojo: layers.js oculta capas
  con selectores `#graph line` / `#graph .node-label` (dependen del SVG).
- Sub-pendientes de cada milestone listados en `docs/ROADMAP_PHASE1.md`.
- Manual de Fabrizio: recargar Claude (opcional, Gemini cubre), `NVIDIA_MODEL`
  vigente (opcional), Neo4j (opcional de verdad).

---

# SESIÓN 2026-09-21 — Limpieza estructural: Track A Fase 2 + Track B completos

Pedido de Fabrizio: "avanza con todo eso… esto solo es estructura, no
modalidades". Cero features nuevas para el usuario; se cierran los pendientes
de arquitectura que arrastraban las sesiones anteriores. **118 tests** (eran
107 al empezar; 56 según CLAUDE.md, que estaba desactualizado). sw v128.

**Track A Fase 2 — stack 3D viejo BORRADO.** `engine/geoglobe.js` y
`engine/planetarium.js` estaban huérfanos desde que se creó `engine/globe.js`:
ningún `<script src>` los cargaba ni estaban en el SHELL del SW. `graph3d.js`
NO se borra (es el motor WebGL de `?webgl3d=1` y hypergraph/voice/Scatter 3D
dependen de su instancia). **Bug latente corregido de paso**:
`getCatColorHex`/`getLinkColorHex` estaban definidas DOS veces (app.html desde
Fase 0 + la copia original en graph3d.js) y, al ser ambas `function` de nivel
superior, la de graph3d.js pisaba en silencio a la de app.html — editar la de
app.html no habría tenido efecto. Ahora la definición es única.

**`rate_limit` → `core/http.py`.** Vivía en server.py, lo que dejaba a los
blueprints (matrix/, ontology/) sin poder limitarse sin importar el server —
justo la circularidad que core/ existe para romper. Las 46 rutas de server.py
no cambian.

**ActivarFactor / DesactivarFactor** (ontology/actions.py, catálogo 11→13).
Los ~70 factores viven LATENTES (severity 1.0) con `severity_crisis` en props;
hasta ahora solo existía el what-if efímero (`/api/matrix/factor/fire`). Estas
dos Acciones mueven la línea base de forma persistente y auditada.
`severity_latente` guarda el punto de retorno y **solo se captura en la PRIMERA
activación** (reactivar a otro nivel no debe sobrescribirlo — hay test de
regresión). El motor lo recoge solo: `active_factors()` lee `severity` y el
caché de matrices se invalida por época del grafo, que estos ObjectUpdated
mueven. La API las expone sin tocar rutas (el endpoint es dirigido por catálogo).

**Historial de insights.** Tabla `InsightSnapshot` + `GET
/api/matrix/insights/history?limit&lang`. Los insights son DERIVADOS, no
hechos de dominio: tabla propia, no eventos bitemporales (ensuciarían la
ontología con conclusiones en vez de observaciones). Una fila por CAMBIO REAL
del grafo (dedupe por graph_epoch+as_of+lang), no por visita; los shocks
manuales no se persisten (son exploración). Bug encontrado por los tests:
`insights` no es texto sino lista de tarjetas `[{kind,title,detail}]` → JSONB.

**MiroFish RETIRADO por completo.** Era un microservicio EXTERNO. Borrados el
proxy `/api/mirofish/*`, `_diag_mirofish`, el campo de `/api/health`,
`MIROFISH_URL/TOKEN`, `sim/mirofish_client.js` y su entrada del SHELL.
- `/api/health` pasó de **~2000 ms a 1 ms**: sondeaba MiroFish con timeout de
  2s en CADA llamada. Y como `MIROFISH_URL` traía una URL de Railway
  hardcodeada como default, el 🩺 reportaba 🔴 FALLA permanente (no "no
  configurado") y bajaba el contador ok/total para siempre.
- El selector de motor pasa de `🤖 IA Simple / 🧬 MiroFish` a
  `🤖 IA Simple / 🧬 Agentes`: el segundo es `_runAgentSim()` → `POST
  /api/sim/agents` (core/sim_agents.py, motor INTERNO), resuelve semillas con
  KhipuResolve y mapea `impacts` → `nodeImpacts`/`cascadeNodes` del War-Room.
  Cae al narrativo si falla. Se eligió `/api/sim/agents` y no
  `/api/matrix/impact` porque el primero funciona **sin DATABASE_URL** (lee el
  snapshot JSON) — el matrix devuelve 503 y habría dejado el War-Room peor.
- `_wrChatSend` dependía del `reportId` de MiroFish, así que estaba **muerto**
  desde que el motor interno es el default (nunca produce ese id). Ahora
  conversa sobre el TEXTO del informe en pantalla vía `/api/ai/analyze`, con
  instrucción de no inventar fuera del informe. Bilingüe.
- `buildMiroFishSeed` → `buildScenarioSeed` (no tenía llamadores externos).

**Historial de lecturas en la UI — DECISIÓN: no se creó una pestaña nueva.**
El roadmap pedía "pestaña INSIGHTS", pero CLAUDE.md registra la instrucción
explícita de Fabrizio de que la interfaz debe SIMPLIFICARSE y de evaluar
fusionar antes de añadir. La pestaña 🔬 Análisis de Red ya era el hogar del
feed (`#an-insights`) y ya está en el grupo "insights" de la barra. Se le
añadió `🕘 Historial de lecturas` (`#an-history`, `window.renderInsightsHistory()`
en engine/insights.js, bilingüe). Resultado: feed + historial en un solo sitio,
cero pestañas nuevas. **Si Fabrizio prefiere una pestaña propia, es revertible
en minutos** — el render ya está aislado en su función.

**Pendiente inmediato tras esta sesión:** sigue el checklist manual de
Fabrizio (REMIGRATE_ON_BOOT en Railway para re-migrar la ontología limpia en
prod, verificar TRADE_PIN, Opera borrar datos del sitio) y el rework de escala
del cliente antes de superar ~2.500 nodos.

---

# SESIÓN 2026-08-02 — Expansión multicapa COMPLETA (olas 1-6): 949 nodos, 13 sectores, 70 factores latentes

Archivo fuente de Fabrizio: `khipus_ai_finance_grafo_completo.md` (393 nodos +
69 FACTORs + 28 ASIENTOs en 6 capas: energía, materiales, macro/crédito,
actores, inmobiliario, logística). Todo desplegado y verificado en prod (sw v122).

**Cliente:** 949 nodos / 2.526 links / 13 sectores (4 nuevos en SECTORS9 con
colores) vía `nodes/nodes_multicapa.js` generado por `scripts/ingest_multicapa.py`
(dedupe + auto-exclusión de su propia salida; las 5 alertas de reconciliación
del doc aplicadas; sufijos Yahoo mundiales → 205 cotizables).

**Ontología (Postgres):** espejo COMPLETO — 1.037 objetos económicos. Incluye
188 empresas históricas que NUNCA se habían espejado (la Etapa B de 148 solo
vivía en el cliente; se descubrió por los links en cuarentena "target
inexistente"). 28 Seats (type no-económico nuevo en vocabulary.json). Links
881/882 (1 cuarentena legítima). `POST /api/ontology/bulk/import` nuevo
(objects no-económicos + links, actor obligatorio, límites 200/1000).

**Los 70 factores viven LATENTES — lección de modelado:** cargarlos a
severidad de crisis (doc/2) puso ρ(T) en 2.63 con cascadas saturadas
(todo-100%): "todas las crisis a la vez" es un escenario irreal. Curación:
severity=1.0 (latente) + `severity_crisis` en props (nivel si se dispara) +
tope `FRAGILITY_CAP=2.5` por nodo en `matrix/engine.py::fragility()`.
Resultado: ρ base 1.553 → 1.939 latente (damped 1.16, casi-crítico — hallazgo
honesto de la tesis multicapa, no bug), cascadas con gradiente informativo
(TSMC → Nvidia 100 / Oracle 89 / Tesla 79). Los 13 factores de PARTE 2 traían
members como JSON inline con comillas — regex del parser corregida.

**Disparo de factores (what-if):** `POST /api/matrix/factor/fire`
{factor_id} — recalcula fragilidad y ρ con ESE factor en su severity_crisis
sobre el fondo latente, SIN mutar la ontología. `active_factors()` ahora
expone severity_crisis. Comando KHIPU `FACTOR LIST` / `FACTOR <id|texto> FIRE`
(ambigüedad → dispara el de mayor severity_crisis y lista alternativas;
feedback visual livesim). Guía ❓ actualizada (949 empresas, comandos FACTOR).

**Pendiente inmediato:** Track B restante (pestaña INSIGHTS, presets →
factores reales, /insights/history), Track A Fase 2 (borrar stack 3D viejo),
rework de escala cliente antes de superar ~2.500 nodos. Nota de curación:
existen 2 factores "Taiwán" legítimos (tensión militar y ciclo cambiario,
miembros distintos) — no fusionar sin revisar.

---

# SESIÓN 2026-08-01 — Prompt frontend+IA (Cowork): Tracks C y D implementados

Del documento `khipus_prompt_frontend_ia_inversion.md` (4 tracks). Orden de la
sección 6 respetado: sync verificado (ya éramos origin/main), referencias
re-grepeadas, Track D pasos 1-2 ya estaban (PIN + papel confirmados en prod).

**Track D — endurecimiento del auto-trader (desplegado):** FIX del bug del
circuit-breaker (bloquea solo entradas nuevas; el stop-loss YA NO se apaga con
el breaker activo), freno max_orders_per_cycle, no acumular sobre el tope por
ticker, no vender sin tenencia, min_confidence y universe configurables en
caliente, `_diag_alpaca()` en /api/diagnostics con el MODO visible (verificado
en prod: "Cuenta PAPEL (simulada) — sin dinero real"). La Capa 3 (puente
propuesta aprobada→orden real, TRADE_BRIDGE_ENABLED) NO se construye hasta que
Fabrizio la pida explícitamente.

**Track C — Investigador Autónomo (desplegado):** agente 7 con búsqueda web
real (Tavily, `core/websearch.py`), anti-alucinación en 2 capas (REGLAS
INNEGOCIABLES + `_verificar_citas` server-side), confianza determinista,
CrearTesis extendida con fuentes citables (aditiva), endpoint
`POST /api/ontology/agents/investigar` (bg, throttle 3 min), UI en 🔔
Propuestas (fuentes como links + campo "Investiga en la web…").
`INVESTIGADOR_AUTO='off'` (decisión Fabrizio 2026-08-02) — reactivo construido
y apagado. 7 tests DB-free incl. regresión SAFE_AUTO.

**Pendiente que necesita a Fabrizio:** crear cuenta gratis en tavily.com y
pegar `TAVILY_KEY` en Railway (sin eso el botón avisa y no gasta).

**Tracks A y B del mismo doc: PENDIENTES** (siguiente ola, en este orden):
A Fase 0 (reubicar getCatColorHex/getLinkColorHex fuera de graph3d.js) →
A Fase 1 (engine/globe.js = geoglobe+planetarium) → B (rate_limit a core/http,
insights/War-Room sin MiroFish, ActivarFactor/DesactivarFactor, pestaña
INSIGHTS). OJO al implementar B: `/api/matrix/insights` YA EXISTE (sim narrada
del hipergrafo) — las rutas nuevas del doc deben renombrarse (p.ej.
`/insights/history`). Y el inventario de renderers del Track A no incluye
`engine/geosituation.js` (Sala de Situación, posterior a su investigación).

---

# SESIÓN 2026-07-19 — Motor de matrices DISPERSAS + centralidad (rama `feature/sparse-matrix-centrality`, NO desplegada)

Implementación del `spec_matrices_dispersas_centralidad`. **NO fusionada a main
ni desplegada**: el propio spec exige correr denso y disperso en paralelo antes
del corte a producción. Todo está detrás de un flag; el default sigue DENSO.

**Qué cambió (`matrix/engine.py`):**
- Motor **denso ↔ disperso** con UN SOLO kernel polimórfico (helpers que
  despachan por `scipy.sparse.issparse`). Flag `MATRIX_ENGINE=dense|sparse`
  (default `dense`). scipy es OPCIONAL: sin él, cae a denso sin romper nada.
- El camino DENSO es **idéntico bit a bit** al histórico (verificado: propagate
  max abs diff = 0.0 vs la versión previa) → los 5 tests con DB pasan sin tocar
  sus aserciones. El DISPERSO se valida por un test de **equivalencia**
  (`numpy.allclose`) DB-free.
- Pitfall clave resuelto: el denso hace `max()` en pares repetidos; COO→CSR los
  SUMA → se deduplica por MÁXIMO en un dict antes de armar la COO.
- **Centralidad PageRank** (ponderada, sobre el grafo de dependencia, con
  teleportación → robusta a componentes desconectados; maneja nodos colgantes) +
  **Personalized PageRank** por portafolio. Complementa (no reemplaza)
  `chokepoint_rank`.
- **Radio espectral ρ(T)** (Perron-Frobenius: eigs con fallback a power
  iteration) → condición de estabilidad `damping·ρ(T)<1`; loguea si supercrítico.
- **Procedencia**: `LinkRecord.properties.source` marca bulto (wikidata/gleif);
  el motor descuenta su peso (`IMPORT_BULK_WEIGHT_FACTOR`, default 0.5) en la
  LECTURA (una sola vez). Sin migración de esquema (JSONB).
- **Caché** del índice de nodos por "época del grafo" (MAX recorded_at de events)
  → invalidación real, no se reconstruye desde cero en cada request.
- Extensiones bajo flag (default OFF): **Monte Carlo** `propagate_bands`
  (p5/p50/p95, semilla fija) y **kernel no-lineal** (`nonlinear=True`).

**API (`matrix/api.py`):** nuevos campos aditivos (no se quitó nada):
`/status` → `spectral_radius`/`systemically_stable`; `/metrics` →
`central_pagerank_top25` + `spectral`; `/impact` → `bands` (opt-in `n_samples>1`)
+ `nonlinear`; **`/parity`** (nuevo) corre ambos motores y alerta si difieren
(mecanismo de corte seguro). `matrix_get` ahora es sparse-safe (COO).

**Ingesta masiva (`ontology/bulk_import.py`, nuevo):** `validate_bulk_links`
(pura, DB-free, testeada) valida integridad (source/target existen, rel_type
canónico) y pone en CUARENTENA (no descarta en silencio); `import_links_bulk` es
idempotente (clave por external_id o triple) y por LOTES, marca procedencia.

**Tests nuevos DB-free:** `tests/test_matrix_sparse.py` (23: equivalencia,
invariantes, PageRank, ρ, benchmark) + `tests/test_bulk_import.py` (6). Todos
verdes. Benchmark scale-free: **50k nodos en 1.17s** (build+propagate+PageRank+ρ);
denso a esa escala serían ~180 GB.

**Desviación documentada (spec §invariantes):** la monotonicidad "aumentar
CUALQUIER arista nunca reduce el impacto de NINGÚN nodo" **no puede** sostenerse
bajo normalización columna-estocástica (subir una arista entrante a j diluye a
los demás proveedores de j → baja el impacto de otro origen). Se testea la
versión que SÍ sostiene la normalización (arista SALIENTE del nodo en shock →
su destino no decrece), que es la que detecta errores de signo/normalización.

**Corte a producción (pendiente, requiere Postgres):** correr `/api/matrix/parity`
un periodo; si `within_tolerance` se mantiene, poner `MATRIX_ENGINE=sparse` y
`scipy` ya está en requirements.txt. La ingesta Wikidata/GLEIF real usa
`import_links_bulk` por lotes.

---

# SESIÓN 2026-07-14 (madrugada, autónoma) — víspera de la demo · app en v95

Trabajo nocturno pedido por Fabrizio ("perfecciona todo, asegúrate que corra en
cualquier compu, no tarde mucho"). Auditoría de regresión final: **12/12 verde,
0 bloqueadores**; carga ~1s; sin errores de consola. Cambios:

- **Sim con Sonnet 5**: era un falso negativo (mi curl `-d` con acentos rompía el
  JSON → 400 "scenario requerido"). La sim SIEMPRE razonó con claude-sonnet-5.
  Probar SIEMPRE con `--data-binary @archivo.json`.
- **Ontología 500** (propuestas/alertas): `init_schema()` no corría en boot →
  tablas `proposed_actions`/`alerts` nunca creadas. Fix: `init_schema()` en boot
  (idempotente, no destructivo). Los 3 endpoints → 200.
- **Grafo Temporal**: empresas/conexiones ahora APARECEN por año de fundación
  (`NODE_META[id].founded`, en 554/555 nodos). Aristas del backbone ya no salen
  "siempre presentes"; timeline arranca en 1900.
- **Informe de portafolio** (Cabina 💼): rendimiento + mejor/peor + concentración
  por sector + comentario cauto (Sonnet 5, `/api/portfolio/comment`) + pulso
  proactivo al abrir. `_computePortfolioSummary` compartido con voice.js.
- **Cripto y más DENTRO de la Cabina** (unificación progresiva, elección de
  Fabrizio): `stageCrypto` + adoptador genérico para `tkg`/`guia`
  (`ADOPT_TABS`). Pedir cripto por voz ya NO cierra la Cabina (bug: `ck.close()`
  en `surfaceTabInCockpit` para pestañas sin escenario → cortaba la voz).
- **Khipu sabe de espacio**: tool `get_space_summary` (voz) + inyección en
  `/api/ai/command` (texto) con conteos reales de CelesTrak (Starlink 10.734).
  Helpers `_space_constellations`/`_space_facts_str` cacheados + piso de respaldo.
- **Alpaca 404**: `_norm_alpaca_base` quita sufijo `/v2` y barra. Nuevo
  `/api/trade/status` (público, sin PIN, sin secretos) para diagnosticar. Ahora
  account → 200 (paper).
- **Comparar fundamentals** (Cabina "Comparar" → pestaña 📊): tabla lado a lado
  NVDA/AMD con quién gana cada fila, desde `/api/findossier`.
- **Rendimiento**: `/api/findossier` cachea parcial 1h (antes ~7s por vista);
  `/api/space/launches` con timeout 8s + respaldo (antes caché fría lenta).
- 3 hallazgos de revisión adversaria corregidos: cripto mal clasificada
  ("BTCUSD" sin barra → asset_class + sufijo USD), pnlPct 0% en cortas (|cost|),
  comentario que decía "papel" en cuentas reales (flag `paper`).

Pendiente sugerido (post-demo): adoptar space/geo (globos 3D) en la Cabina;
aplicar migración FMP para las tablas secundarias del dossier; warm de cachés
persistente (Redis) para que sobrevivan reinicios de Railway.

---

# REDISEÑO MAYOR 2026-07 — mapa único con capas + motor de matrices

Decisiones de Fabrizio (2026-07-03, no reabrir sin razón nueva): UN solo mapa
con capas activables; app final de 4 pestañas (MAPA/MERCADO/INSIGHTS/GUÍA) con
Khipu/terminal flotante; motor de predicción INTERNO (adiós MiroFish) centrado
en insights de inversión; matrices numéricas por tipo de relación moduladas
por hiperaristas (todo bitemporal en la ontología); 40 categorías → ~9
macro-sectores sin perder detalle; SOLO Railway (se elimina el modo
standalone); frecuencia de actualización configurable con automático APAGADO
por defecto; gasto de IA moderado; despliegue por etapas siempre verde;
limpieza agresiva de código muerto.

Auditoría multi-agente completa del repo hecha el 2026-07-03 (9 lectores):
hallazgos clave — 7 renderers de mapa independientes; 4 propagaciones de shock
inconsistentes; 31 empresas duplicadas; direcciones de arista opuestas
(546 vs 577); 67% de pesos w en default; ~700+ líneas visuales muertas;
rag/ y litellm/ nunca desplegados; hypergraph.js con node_impacts siempre
vacío (el slot del motor nuevo); contrato MiroFish a replicar =
{node_impacts, cascade_nodes, price_trajectories, report, chat, progress_pct}.

## Etapa 0 — Seguridad y cimientos: ✅ CÓDIGO COMPLETO (2026-07-03)

- [x] /api/trade/* (11 rutas) protegidas con PIN (X-Trade-Pin == env
      TRADE_PIN); sin TRADE_PIN el trading queda deshabilitado. El panel de
      trading pide el PIN una vez (localStorage.khipu_trade_pin). ANTES:
      cualquiera con la URL podía operar la cuenta Alpaca real.
- [x] /v1/auth/key: tiers de pago exigen X-Admin-Secret (KHIPU_ADMIN_SECRET).
- [x] Auto-trader: daily_pnl_pct real (equity vs last_equity de Alpaca) →
      el circuit-breaker diario ya puede saltar; stop-loss por posición
      implementado (cierra posiciones bajo el umbral). Antes: decorativos.
- [x] gunicorn 2 workers → 1 worker + 8 threads (el estado en memoria vivía
      duplicado y divergía por worker).
- [x] Ontología, 2 bugs de replay corregidos: RechazarVinculo ahora emite
      LinkRemoved (antes mutaba tablas sin evento → time-travel mostraba
      vínculos rechazados como vigentes); _links_active_at casa remociones
      comodín (sin rel_type) y respeta re-creaciones. +3 tests de regresión
      (isomorfismo replay==tablas). **51/51 tests contra Postgres real.**
- [x] sw.js SHELL sincronizado (faltaban 3 nodes/* y 4 vendor) + bump v28.
- [ ] PENDIENTE (paso manual de Fabrizio): variable TRADE_PIN en Railway
      (y KHIPU_ADMIN_SECRET si va a emitir claves de pago).
- Diferido a Etapa 1: extraer _ai_complete/_fetch_quote_raw a core/ (rompe
  la dependencia circular ontology→server).

## Etapa 1 — Limpieza masiva: ✅ COMPLETA (2026-07-05, 4 batches publicados)

- [x] Batch 1 (a2b09ff, −2,200 ln): rag/ + litellm/ + redis compose +
      nodes_core.js + PriceAlerts no-op + cadena Aladdin muerta + _mfChatSend
      + _drawWorldMap + _activateHypergraph roto + botón 🕸 + timeline
      duplicado + initSpaceOrbitCanvas + métodos muertos de graph3d +
      hypergraph save/load + 9 rutas Flask sin caller + paleta .dark
      duplicada + docs stale → docs/archive/.
- [x] Batch 2 (c24e85b): paquete core/ (config/http/ai/quotes) — server.py y
      ontology/agents.py importan de ahí; dependencia circular
      ontology→server ROTA (prerrequisito del motor de matrices).
- [x] Batch 3 (41beb40, −281 ln): modo standalone ELIMINADO — SERVER_MODE
      constante true, DataLayer solo-server, fuera todas las llamadas
      directas del navegador a Finnhub/FMP/Anthropic/Marketstack y el UI de
      keys (⚙ solo preferencias + salud). voice.js y secondbrain.js migrados
      al proxy. Smoke test real en navegador local: arranque limpio.
- [x] Batch 4: /v1/risk/portfolio y /api/portfolio-risk comparten
      _portfolio_risk_impl (antes duplicado verbatim de ~60 ln, contrato /v1
      intacto); _fetch_quote_raw(timeout=) reutilizado en los 3 loops batch;
      CLAUDE.md y este archivo actualizados.
- ⏸️ Diferido A PROPÓSITO a Etapa 4: consolidar los 3 pipelines de quotes del
  cliente (fetchQuotes/LivePrices/initLiveData) y los 2 sistemas de alertas
  vivos — el store único del mapa unificado los subsume; consolidarlos dos
  veces sería trabajo tirado.

## Etapa 2 — Datos limpios: ✅ COMPLETA (2026-07-06, 5 batches publicados)

**El grafo canónico ahora es: 407 empresas · 1,028 links · 9 tipos de
relación · 9 macro-sectores · dirección ÚNICA (source PROVEE a target).**

- [x] Batch 1 (e73be4f): ~2,550 líneas de datos inline salen de app.html →
      nodes/nodes_seed.js (extracción determinista, isomorfa 463/1163).
      Hechos temporales concat-safe (el orden de <script> ya no pierde datos).
- [x] Batch 2a (0df080b): RESOLUCIÓN DE ENTIDADES — 56 ids duplicados
      fusionados (463→407). NODE_ID_ALIAS = tabla canónica; el merge absorbe
      campos, redirige links, y NODE_BY_ID[alias] → nodo canónico (ids viejos
      siguen resolviendo). Dedupe (s,t,type). NO fusionados (ticker≠entidad):
      HashiCorp≠IBM, Qwen≠AlibabaCloud, Aerojet⊂L3Harris, Altium⊂Renesas.
- [x] Batch 2b (f9a4282): DIRECCIÓN ÚNICA — 1,168 filas reescritas
      físicamente, 425 volteadas, 66 re-tipadas (customer→supply,
      investor→invest → 9 tipos). Adjudicación arista por arista
      (clasificador de categorías+verbos en español + revisión manual de 375
      ambiguas + auditoría de 286 flips). 10/10 verdades de cadena en
      navegador; la cascada de TSMC ahora alcanza 112 empresas (incl. Nvidia
      y Apple — antes invisibles por direcciones opuestas).
- [x] Batch 3: MACRO-SECTORES — SECTORS9 + CAT_TO_SECTOR (40 cats → 9
      sectores con los colores NEXUS) en nodes_seed.js; 5 países faltantes
      añadidos a COUNTRIES (Israel/Australia/Europa/India/Canadá) + typo
      Japan→Japon; pase de pesos por señal textual (7×w6 monopolios,
      10×w5 principales, 5×w1 pilotos).
- [x] Batch 3 (cont.): MERGE ÚNICO — nodes/merge_graph.js
      (buildKhipusGraph) usado por app.html Y por el exportador; el
      export_graph_v0.js por rangos de línea hardcodeados fue reemplazado.
      data/grafo_v0.json regenerado canónico (407/1028/9 sectores) y
      migración a Postgres validada end-to-end (439 objetos, 0 ids sin
      resolver, 85 hechos fechados). 51/51 tests.
- ⏸️ Los pesos siguen siendo un prior débil (mayoría w=2): la re-derivación
  profunda (dependency-share por fundamentals) queda para la ingesta (12k) y
  el motor de matrices, que los recalculará con datos vivos.

## Etapa 3 — Motor de matrices + hiperaristas: ✅ NÚCLEO COMPLETO (2026-07-07)

Paquete **matrix/** (opcional y defensivo, como ontology/ — sin DATABASE_URL
responde 503 y la app sigue). Importa de core/ y de la ontología; NO toca
server.py salvo el registro del blueprint.

- [x] `matrix/engine.py`:
  - `build_matrices(session, as_of=)`: una matriz N×N por rel_type (9 tipos)
    desde los links VIGENTES o, con `as_of`, reconstruidos por VALIDEZ desde
    events (time-travel real, reusa `_links_active_at`). A[i,j] = i PROVEE a j
    (convención canónica Etapa 2); partner reflejado simétrico.
  - `active_factors()`: HIPERARISTAS = objetos type='Factor' + links 'affects'
    (weight = coeficiente). Cero cambio de esquema — reusa ObjectCreated/
    LinkCreated, así heredan bitemporalidad, auditoría y time-travel.
  - `fragility()` + `propagate()`: UN kernel de propagación de shocks
    (reemplaza las 4 implementaciones BFS divergentes del cliente).
    Modelo económico: transmisión normalizada POR TIPO de relación (un
    proveedor ÚNICO en su tipo transmite ~todo el shock; ser 1 de N pega
    poco), combinada por criticidad (fab≈supply > invest); impacto = máximo
    por ruta (no suma). Las hiperaristas aumentan la FRAGILIDAD del afectado
    (se aplica tras normalizar — por eso no se cancela).
  - `compute_metrics()`: grado in/out ponderado + tamaño de cascada +
    ranking de chokepoints por nodo.
- [x] `matrix/api.py` (blueprint /api/matrix/*): `/status`, `/<rel_type>`,
  `POST /impact {shock, magnitude, damping, max_hops, rel_weights, as_of}`,
  `/metrics`. Registrado defensivo en server.py.
- [x] Tests `tests/test_matrix.py` (5): verdades de cadena en las matrices,
  propagación TSMC→clientes con hops, hiperarista amplifica + time-travel la
  desactiva, chokepoints, endpoints HTTP. **56/56 tests totales.**
- [x] Validado end-to-end contra Postgres real: los chokepoints detectados
  son los reales de la industria — TSMC(265), PDF_Solutions, ARM, Amazon,
  Broadcom, Synopsys. El NRS server-side (computeNRS réplica) sigue en
  ontology/agents.py; la unificación NRS↔matriz (computed_metrics servido)
  se hará al conectar el frontend (Etapa 4/5).
- ⏸️ Diferido: tabla cache `matrix_snapshots` con watermark (hoy se computa
  on-demand; N≈440 → <30ms por matriz, no urge). Agente MatrixSentinel →
  ProposedAction cuando un chokepoint cruza umbral: se cablea en Etapa 5
  junto con el resto de auto-insights.

## Etapa 4 — Mapa unificado con capas: 🔄 EN CURSO (batches publicados)

- [x] Batch 1 (51c9f21): mapa por 9 MACRO-SECTORES NEXUS (40 colores → 9,
      colorMode='sector' por defecto, toggle "▸ detalle" a las 40 en la
      leyenda; SECTORS9/CAT_TO_SECTOR/sectorColorFor en window).
- [x] Batch 2 (6225eb5): SISTEMA DE CAPAS (engine/layers.js) — botón "◱ Capas"
      arriba-izq del mapa; enciende/apaga conexiones, nombres, anillos de
      riesgo, marcas ⚠/IPO, países vía hoja CSS dedicada (instantáneo, sin
      re-render); persiste en localStorage; window._layersApply re-aplica.
- ⏸️ PENDIENTE: unificar los 7 renderers en 2 motores (grafo+globo), las 4
      pestañas finales, y el globo unificado (geoglobe+planetarium).

## Etapa 5 — Predicciones + Insights: 🔄 EN CURSO

- [x] Batch 1 (33438e3): INSIGHTS automáticos (engine/insights.js) — llena el
      slot #an-insights (chokepoints ponderados de /api/matrix/metrics con
      fallback cliente, riesgo, factores, geo); tarjetas con chips clicables.
- [x] Batch 2 (ec4aebe): BRIEF MATINAL (engine/brief.js) — overlay al abrir
      (1×/día, casilla silenciar, ❓ flotante para reabrir); chokepoint +
      riesgo + factores + conclusión IA (opcional, degrada). Salta al mapa.
- ⏸️ PENDIENTE: adiós MiroFish (reemplazo interno completo), pestaña INSIGHTS
      con historial navegable, control de frecuencia visible.

## Wow desplegados (fuera de la secuencia de etapas)

- [x] **X-Ray de empresa** (engine/xray.js, 026d23e): overlay que desarma
      cualquier empresa — anatomía, NRS término a término, hilos clicables,
      onda de impacto (motor de matrices con fallback), acciones. Botón 🔬 en
      la ficha. Primera pieza con piel NEXUS.
- [x] **Motor de estados reactivo** (engine/statematrix.js, dffd5a6): vector
      de estado por nodo (salud/riesgo/momentum propagan; valor/crecim/señal/
      potencial derivan) + matrices de acoplamiento dispersas + kernel
      "eslabón más débil" (MAX, decae por distancia). 100% cliente, ~7ms/sim,
      60fps. Núcleo puro testeable en Node. MISMOS pesos que matrix/engine.py.
- [x] **Simulación EN VIVO v2** (engine/livesim.js, 08d6ee0): botón "◉ En
      vivo" en el mapa → escenarios/severidad → nodos Y conexiones se tiñen en
      tiempo real; capital $ expuesto, impacto en cartera, desglose por sector,
      GANADORES (rivales que capturan demanda), y ▶ reproducir cascada
      (frames por salto). rAF con fallback setTimeout (pestaña oculta).
- [x] Artifact "El Sistema de Matrices" (fuera del repo): las 9 matrices
      reales interactivas — heatmaps, vector de estado, propagación.

## Ampliaciones 2026-07 (tras feedback "simulaciones muy cerradas, más info")

- [x] **Simulación EN VIVO v3** (livesim.js): constructor de escenarios —
      4 TIPOS de golpe (corte↓, demanda↑=auge/verde, precio, sanción; el motor
      statematrix propaga en 2 direcciones vía adyacencia customers) +
      OBJETIVOS libres (presets, sector entero, país entero, empresas elegidas
      con "＋ añadir del mapa"). 💾 Guardar + 📁 Historial que reproduce.
- [x] **Guardar simulaciones** (matrix/api.py): POST/GET
      /api/matrix/simulations → objetos ontología type='Simulation' (fecha,
      bitemporal). Requiere Postgres.
- [x] **Comparar dos empresas** (compare.js): overlay lado a lado (NRS,
      margen, cap, conexiones, NRS término a término), ganador resaltado.
      Botón "⇄ Comparar" en el X-Ray.
- [x] **X-Ray enriquecido**: "Quién sufre ↓" + "Quién GANA ↑" (rivales que
      capturan demanda).
- [x] **Insights más ricos** (insights.js): OPORTUNIDADES (resilientes con
      potencial) + panorama por sector (más frágil/más sólido).
- [x] **Las 9 matrices dentro de la app** (matrixview.js): small-multiples +
      heatmap grande con tooltip, en la pestaña Análisis, 100% cliente.
- [x] **Khipu agente de voz total** (voice.js + server.py, 589cabd): Khipu ya
      dispara las funciones nuevas por voz. Camino de TOKENS en su propio texto
      (no requiere configurar herramientas en el panel de ElevenLabs, igual que
      NAV/TAB/STRESS): `[XRAY:id]` · `[COMPARE:a,b]` · `[SHOCK:id:kind]`
      (collapse|demand|price|sanction) · `[OPPS]` · `[INSIGHTS]`. Además client
      tools nuevos en `_handleToolCall` (open_xray, run_live_simulation,
      compare_companies, get_opportunities, show_insights) por si algún día se
      registran en ElevenLabs — devuelven datos reales. Resolvedor
      `_resolveNode` case-insensitive (id/ticker/nombre): Khipu dice "NVIDIA"
      pero el id real es "Nvidia" (NVDA). BIXBY_SYSTEM_PROMPT enseña cuándo usar
      cada token. Verificado en navegador con 407 empresas (X-Ray poblado,
      SHOCK TSMC→252 afectados, COMPARE TSMC vs Samsung).
- [x] **Cabina de Khipu — modo pantalla completa** (engine/cockpit.js, 0660527):
      Khipu deja de ser un botón y SE VUELVE la pantalla. El botón de Khipu y
      ⌘K abren una vista full-screen: orbe/logo arriba + una barra para pedir
      por texto o 🎙 voz + un ESCENARIO grande abajo. El enrutador `ask(texto)`
      manda lo que pides a escenas: X-Ray a pantalla completa · simulación de
      shock (víctimas+ganadores+sectores, KhipuState) · comparar 2 empresas
      lado a lado · insights (riesgo+oportunidades) · lienzo de datos (Canvas
      IA) · lienzo en blanco. Voz y texto van al MISMO escenario (xray.js
      detecta la cabina abierta y pinta ahí, no en el cajón).
      - xray.js refactor: `buildXRayHTML(id,{full})` reusable (cajón lateral Y
        escenario). Modo full = TODOS los hilos (no 6) + multi-columna +
        fundamentales + ranking de riesgo + desglose por tipo de relación.
        Onda de impacto INSTANTÁNEA con KhipuState (~7ms) → arregla "tarda
        mucho". CSS scoped a `.xray-scope` (antes `#xray`).
      - Responde al feedback de Fabrizio: "no me destripa la empresa" (muestra
        TODO), "tarda mucho" (instantáneo), "no hay modo Khipu pantalla entera".
      - Orbe plasma optimizado: el bucle salta canvas invisibles y escala el
        detalle al tamaño (antes dibujaba el orbe oculto de 200px en cada frame).
      - PENDIENTE conocido: el system prompt con los tokens nuevos solo llega a
        Khipu si ELEVENLABS_ALLOW_OVERRIDE=true + "Allow overrides" ON en el
        panel de ElevenLabs. La cabina por TEXTO funciona siempre (no depende
        de eso). La cabina por VOZ ejecuta acciones vía los tokens de voice.js.

## Sesión "modo máximo" 2026-07-10 (feedback: perfeccionar Khipu, 555 empresas, vivo, 3D)

Decisiones de Fabrizio (AskUserQuestion): sync ElevenLabs automático vía API ·
altas/bajas de empresas automáticas con registro reversible · caché interno
Redis-ready · el 3D nuevo REEMPLAZA al actual.

- [x] **Etapa A** (e92cf6e): fix DEFINITIVO del "veo lo mismo" — index() inyecta
      `?v=<versión SW>` en cada `<script src>` (bump de sw.js → URLs nuevas →
      código fresco siempre) + auto-reload en controllerchange (una vez, con
      guardas). Khipu 100% silencioso: BIXBY_SYSTEM_PROMPT reescrito (GOLDEN
      RULES: jamás decir comandos/tokens/herramientas, actuar y narrar),
      `_bixby_client_tools()` (23 tools) + `_sync_bixby_agent()` + POST
      /api/voice/sync-agent con autosync al boot (BIXBY_AUTOSYNC=0 apaga);
      voice.js `_cleanSpeech()` limpia tokens del transcript; tools nuevas
      create_visualization y open_cockpit; sim/compare/insights van al
      escenario de la Cabina si está abierta.
- [x] **Etapa B** (35734dd): informe de Fabrizio ingerido → **555 empresas,
      1,623 links, 0 huérfanos, 43 categorías** (antes 407/1,028/88 huérfanos).
      scripts/ingest_enrichment_md.py = parser determinista REUTILIZABLE para
      futuros informes (resolución de entidades + fuzzy + mapeo de categorías;
      3 cats nuevas: power_ipp/osat/defense_prime). Verificación adversarial
      con Workflow (18 agentes, 626 links revisados, 126 direcciones
      corregidas a la canónica). data/grafo_v0.json regenerado — para llevar
      producción a 555 hace falta correr REMIGRATE_ON_BOOT (pendiente de
      Fabrizio, pasos ya entregados).
- [x] **Etapa C** (35734dd): caché — REDIS_URL → RedisCache automático (cero
      pasos); canvas 30min/consulta; ai/analyze 30min; matrix/metrics TTL 5min
      (corría una propagación POR NODO por request). Bug real corregido:
      node_index excluye Simulation/Factor (simulaciones guardadas se colaban
      como filas fantasma en las matrices).
- [x] **Etapa D**: la app se mantiene relevante SOLA. Acciones nuevas
      IncorporarEmpresa/RetirarEmpresa (auditadas, reversibles) en
      ontology/actions.py. Agente 5 📡 RadarEmpresas (ontology/agents.py):
      lee GDELT de los nodos más conectados, la IA detecta empresas nuevas
      relevantes y las incorpora con link al grafo. auto_cycle(): las
      propuestas SEGURAS (anotar/marcar riesgo/proponer vínculo/incorporar)
      se auto-aprueban con actor 'agent:auto'; lo que toca dinero queda para
      el humano. POST /api/ontology/agents/cycle corre en HILO de background
      (GDELT+IA tardan 30-60s; jamás atar un worker) — responde al instante
      con la última corrida. engine/live.js: latido de insights (invalida NRS
      y re-dibuja al llegar precios), dispara el ciclo cada 10 min, badge
      "● EN VIVO" en el pie + toasts del radar. Robustez: SAVEPOINT por
      agente y por propuesta (un fallo SQL ya no envenena la transacción —
      bug real InFailedSqlTransaction visto en pruebas). Verificado local con
      Postgres migrado a 555: ciclo aplicó 6 propuestas solo (MarcarRiesgo
      SMIC/Lenovo/Foxconn/Quanta/Huawei por agent:auto), endpoint 320ms.
- [x] **Etapa E** (49b60e7): 3D cinemático — halos aditivos por nodo (pseudo-
      bloom, laten con NRS), 1,623 aristas CURVAS (bezier 11 pts), 260
      partículas de flujo por las aristas fuertes, niebla FogExp2, respiración
      de cámara, auto-ajuste de rendimiento (modo ligero < 28fps). 66 fps.
- [x] **Etapa F**: arquitectura de 4 capas FORMALIZADA (docs/ARQUITECTURA_
      CAPAS.md). Capa 2: core/semantic.py — build_context() = subgrafo
      hiper-filtrado (foco + vecinos top + chokepoints) desde data/grafo_v0
      .json (555, caché de módulo), extract_companies() sin IA, resolve_ids
      (id/ticker/label). Capa 4: POST /api/deep/analyze + GET /api/deep/status
      (server.py _deep_run, hilo background): PLAN (IA) → REUNIR (capa 2) →
      SIMULAR (matrices con hiperaristas) → SINTETIZAR (tesis/evidencia/
      riesgos/vigilar). Cabina: escena stageDeep con pasos en vivo + polling
      2.5s (chip "Investigación profunda", regex investiga/a fondo/tesis).
      Khipu: tool deep_analysis (23+1 registradas vía sync).
- **Khipu sync VERIFICADO en producción**: ok:true, mode:full, 22 tools
  registradas (tras el fix del modelo TTS flash v2.5 para agentes en español
  — 652cb7e). Khipu ya no dice comandos.
- [x] **Etapa G** (4de15f9, feedback 2 con referencia investingvisuals):
      1) localcharts.js — gráficos DETERMINISTAS sin IA para pedidos comunes
      (0 ms; la IA solo para lo exótico); enganchado en Cabina y Canvas.
      2) La Cabina ADOPTA el grafo (<main>) y la terminal (#terminal-panel)
      EN su escenario (placeholder + devolución al salir) + barra de 8
      botones; tools de voz enrutadas dentro (antes cambiaban una pestaña
      tapada por el overlay). 3) Pestaña 💡 Insights → 🖥️ Terminal (abre la
      terminal por defecto). 4) Dossier financiero: /api/findossier/<t>
      (FMP stable→v3, series anuales 6y, caché 24h) + fincard.js (overlay
      NEXUS con 8 small-multiples Chart.js); botón 📊 DOSSIER en las celdas
      de la terminal, en el X-Ray, ruta "dossier de X" y tool open_dossier.
      OJO: /api/fundamentals/<t> YA existía (P/E+ratings del Second Brain) —
      por eso el nuevo se llama findossier.
- [x] **Feedback 3** (23c3dac): get_company_info devuelve la FICHA COMPLETA
      (empleados/fundación/ingresos/cap/moat/geo_risk/desc/grados) — Khipu ya
      no dice "no sé" con datos que la app tiene; el CONTEXT_UPDATE de la
      empresa seleccionada también. Anti-glitch: al adoptar/devolver el grafo
      de la Cabina se re-encuadra con fitToView() (quedaba clavado en una
      empresa).
- [x] **Fluidez** (6af5db0): flask-compress+brotli (~73% menos descarga:
      muestra 1,362KB→388KB; OJO: flask-compress salta streaming y
      send_from_directory streamea — _js_cache_headers bufferiza con
      get_data()); JS versionado (?v=N) → Cache-Control immutable 1 año
      (recargas sin bajar código); fundido de 160ms al cambiar pestaña
      (nav4) y escena de Cabina (prefers-reduced-motion respetado).
      REDIS: no necesario — 1 worker + 8 threads (Dockerfile), caché interno
      ya compartido; con REDIS_URL se activa solo.
- [x] **3D perfeccionado** (14a865c): aristas fusionadas en UNA LineSegments
      con color por vértice (1.623 Line → 1 draw call; resaltado de cadena =
      base atenuada + ~155 líneas dedicadas encima); partículas de flujo en
      UNA nube Points; etiquetas LOD (19 visibles de 555: cercanas/grandes/
      seleccionada/hover/cadena, refresco cada 8 frames); inercia de órbita
      al soltar (decae 0.93, mouse y táctil); zoom de rueda con easing;
      anillo de selección orbitando; halo reforzado en hover; modo ligero
      además baja pixelRatio a 1. Medido: ~3.500 → 1.377 draw calls (-61%).
      OJO: _linkRecs/_linkMerged/_flowPoints/_pointOnRec reemplazan a
      linkLines/_createLinkLine/_pointOnLink (linkLines queda [] legado).
- [x] **3D "otro planeta" + UI limpia** (926239a): la CAUSA de "no se ven
      todos" era el Scatter de inversión AUTO-ACTIVÁNDOSE al entrar al 3D
      (reposicionaba a sus ejes y su filtro dejaba nodos en opacity 0.05
      escondiendo hijos). Ya no se auto-activa: vista semántica con las 555
      SIEMPRE. Scatter = lente opcional en HUD [🕸 Cadena | 🎯 Inversión]
      dentro del 3D. Sub-pestaña 🪐 3D en grupo Mapa (window._go3D);
      eliminados el botón header "◈ Temporal" (duplicado de la sub-pestaña
      ◈ — "hay 2 temporal") y el botón clonado del scatter. Halos GPU: los
      555 sprites → UNA nube Points+ShaderMaterial (pulso/hover/tamaño en
      vertex shader; posiciones sync con meshes por frame; setHaloDim/
      setAllHalos para scatter y cadena). Atmósfera: doble campo de
      estrellas + 4 nebulosas + resplandor central. Draw calls acumulado:
      ~3.500 → 1.043 (-70%).
      FIX POSTERIOR (54942ac, "directamente no da el 3D"): el motor SÍ
      renderizaba — el ACCESO estaba tapado: (a) botón 🪐 extra en los
      controles del mapa (+ − ⤢ 🪐) con estado sincronizado; (b) BUG
      preexistente: .start-hint del panel se solapaba sobre .zoom-ctrl y
      comía los clics (también bloqueaba + − ⤢) → z-index:30; (c) _toggle3D
      con try/catch+toast; (d) chip 🪐 con glow; (e) "3d"/"universo" en la
      Cabina abre el universo. Verificado con clic REAL: 83/100 píxeles.
      + AUTO-REPARACIÓN (23447bb): _selfCheck lee píxeles a los 2s; si negro →
      _haloFallback (PointsMaterial estándar) → _ultraSafeMode (solo esferas+
      aristas, sin fog/partículas, toast con GPU). Render inmortal (try/catch
      con escalera). Verificada la escalera forzada: 48/60 píxeles en ambos.
- [x] **Feedback 4** (fe37c28): (1) "se reinicia a cada rato" — el auto-reload
      recargaba en CADA deploy; ahora recarga silenciosa solo <10s de abierta,
      después un avisito clicable "⬆ Nueva versión" (anti-bucle 1/min).
      (2) Panel 📋 Datos en la Terminal (engine/termdata.js, hook en
      _termLoadCell): ficha + valuación/analistas (P/E, objetivo, upside,
      barra buy/hold/sell) + fundamentales anuales 5y + cadena clicable.
      (3) Guía reescrita al día (555, 4 pestañas, superpoderes, KHIPU
      vigente, FAQ de actualizaciones y 3D compatible).
- [x] **Feedback 5** (b25df9b + 5fda95b): (1) dossier "nunca una celda
      vacía" — plan B por indicador (ingresos $B, acciones en circulación,
      margen bruto anual…) y nota clara si el dato no existe; serie 'shares'
      nueva en /api/findossier; verificado 8/8 celdas con Nvidia en prod.
      (2) nodes/meta_fill.js: fichas para las 187 empresas sin metadata
      (workflow 26 agentes con verificación cruzada) → 0/555 sin ficha.
      (3) Dossier PRE-IPO para privadas (renderPrivate: valuación/rondas/
      hitos de PREIPO_INTEL). (4) Detector de páginas viejas: versión
      visible en el pie (v71) + live.js compara server vs cliente → pill
      (que ahora limpia cachés al tocar). CAUSA RAÍZ del "3d no sirve":
      el navegador de Fabrizio corre una versión vieja (0 beacons llegaron).
      PENDIENTE: leer /api/diag/recent cuando Fabrizio pruebe el 3D en v71+
      (cada deploy borra el buffer — leer ANTES de desplegar).
- [x] **Feedback 6 — camino a la versión final** (5d3ffde, v73): (1) DESC_FILL
      — 135 descripciones por workflow de 9 agentes → 0/555 sin ficha y
      0/555 sin desc (cobertura TOTAL de datos). (2) Terminal móvil: sidebar
      150px, grid 1 columna, panel 📋 como overlay completo (auditoría 375px).
      (3) /api/diag persistente en Postgres (client_diags) — los beacons ya
      SOBREVIVEN deploys (antes se perdieron 3 veces). PARA LA VERSIÓN FINAL
      faltan: REMIGRATE_ON_BOOT (acción de Fabrizio, BD prod sigue vieja),
      confirmar 3D en su dispositivo (leer diag/recent — ya persistente),
      prueba de voz Khipu end-to-end, y opcionales (workspace drag&drop,
      unificación renderers, 12k, SaaS).
- [x] **Gráficos rápidos v2** (e8f1341, "tardan full"): el prompt del Canvas
      IA mandaba las 555 empresas (~150KB) — ahora la Capa 2 lo adelgaza
      (solo las mencionadas, o top 80 + sector_summary agregado; quotes
      filtradas; max_tokens 1200). +7 patrones locales sin IA en
      localcharts.js: proveedores/clientes de X (grafo), empleados,
      fundación, scatter riesgo-vs-margen, treemap sectores, mi cartera, y
      PRECIO HISTÓRICO async desde /api/candles ("precio de Nvidia" o solo
      "AMD" → línea 90d, ~300ms). tryAsync() en Cabina y Canvas.

## Etapa H — Feedback 7 (2026-07-12): explicabilidad + regla bilingüe + cripto

Feedback de Fabrizio: (a) 3D sigue fallando en SU equipo tras 3-4 rondas +
comparar 2 empresas no le funcionó → simplificar; (b) un inversionista
preguntó "¿qué es el NRS?" y la app no lo explica; (c) REGLA NUEVA
PERMANENTE: todo en ES+EN vía botón de idioma (está en CLAUDE.md);
(d) 12k empresas era un número lanzado — pidió recomendación; (e) pegó el
prompt del "módulo de datos Bloomberg-depth" (adapters, cripto, Alpaca paper).

- [x] **CLAUDE.md**: regla bilingüe + regla de explicabilidad (permanentes).
- [x] **engine/explain.js** (nuevo): `explainMetric(key)` — modal bilingüe
      que explica NRS (4 componentes con puntos), peso w, chokepoint, VaR y
      dilución en lenguaje simple con ejemplos (TSMC, ASML). `explainChip(key)`
      devuelve el botoncito "?" reutilizable. Cableado en: X-Ray (cabecera
      NRS), Terminal→📋 Datos (fila Riesgo NRS + cabecera cadena), Mercado
      (NRS Top 10 + th del portafolio), badge NRS de la ficha del mapa.
      FAQ de la Guía actualizada con "¿Qué es el NRS?".
- [x] **3D → beta**: chip 🪐 marcado "β" (no iterar más hasta leer
      /api/diag/recent con beacons reales de su equipo — tarea #20).
- [x] **Módulo de datos Fase 1 — cripto** (del prompt que pegó, adaptado al
      stack Python): `core/providers/` (patrón adapter, esquema unificado
      CryptoAsset) + `coingecko.py` (SIN API key; COINGECKO_KEY opcional por
      env — NUNCA hardcodear, regla verbatim del usuario). Endpoints:
      `/api/crypto/markets` (cache 120s), `/api/crypto/<id>` (300s),
      `/api/crypto/<id>/history` (600s). UI: sub-tab **₿ Cripto** en Mercado
      (engine/crypto.js, bilingüe vía claves cr_* de I18N): top 100 con
      precio/24h/7d/mcap/volumen, detalle con gráfico Chart.js 90d + ficha.
      Verificado en local: BTC/ETH datos reales, 100 filas, ES↔EN, 0 errores
      de consola. PENDIENTE Fase 2: adapter FMP equities unificado
      (CompanyProfile), Alpaca paper trading (keys ya en Railway env),
      stub bloomberg_sapi.
- [x] sw.js → **v74** (+ explain.js y crypto.js en SHELL).
- Recomendación de tamaño dada a Fabrizio: ~2.000-3.000 empresas curadas en
  el grafo + búsqueda on-demand de CUALQUIER ticker público vía el módulo de
  datos (la cobertura deja de ser el límite del producto).

## Etapas I+J — Feedback 8 + Expediente Cripto (2026-07-12, sw v76)

Feedback: 3D pantalla negra otra vez, Khipu no entiende "nvidia" por voz,
resultados quedan detrás de la interfaz, gráficos lentos, quiere Sonnet 5
(eligió HÍBRIDO), NO quiere avisos de versión (siempre lo último al abrir),
"no veo nada de cripto". + Pegó KHIPUS_CRIPTO_TOP50_EXPEDIENTE.md.

DIAGNÓSTICO CLAVE: su footer dice v74 (SÍ recibe lo último) pero sus beacons
NUNCA llegan (canal verificado OK con beacon de prueba → puede que pruebe en
OTRO dispositivo). Hueco real encontrado en graph3d: canvas que nace 0×0
(pestaña oculta/carrera de layout) NUNCA se recuperaba (_onResize retornaba
en silencio y _selfCheck ignoraba buffer 0×0) = pantalla negra sin error.

- [x] **3D blindado** (graph3d.js): _ensureSized() + _startSizeWatch()
      (reintento por rAF hasta ~20s) + ResizeObserver en canvas y padre +
      _selfCheck v2 (buffer 0×0 → beacon '3d_zero_size' con medidas + watch;
      document.hidden → reprograma en vez de abandonar). Beacons con versión
      REAL (window._appVersion, antes 'v68+' hardcodeado).
- [x] **Actualizaciones invisibles** (pedido explícito): _showUpdatePill ya
      NO muestra pill — recarga silenciosa al abrir (<10s), con pestaña
      oculta, o al ocultarla (visibilitychange). Anti-bucle 1/min.
- [x] **Khipu entiende nombres** (agente A): engine/resolve.js NUEVO —
      KhipuResolve.find() con ~150 aliases de transcripción de voz española
      ('en vidia'/'envidia'/'video'→Nvidia, 'te ese eme ce'→TSMC), fuzzy
      Levenshtein, sugerencias top-3; integrado en voice/command_center/
      cockpit/khipu_lang con fallback. notFound() bilingüe (Khipu DICE las
      sugerencias). VERIFICADO: 8/8 variantes de voz resuelven.
- [x] **Todo al frente** (agente A): window._surface(kind,arg) — Cabina
      abierta → renderiza EN su escenario (dossier fc-ov z→7600 sobre el
      cockpit z7000); cerrada → cierra overlays y switchTab ANTES de pintar.
      Todas las acciones visuales de Khipu pasan por _surface.
- [x] **IA híbrida** (agente B): core/ai.py _ai_complete(tier='fast'|'deep');
      AI_MODEL_FAST (haiku) / AI_MODEL_DEEP (claude-sonnet-5, env override).
      DEEP: síntesis deep research, veredicto/tesis IA (aiComplete tier),
      Canvas, War Room (tier:'deep' max 2500), brief matinal. FAST: todo lo
      demás. Bonus: bug de _diag_gemini/_diag_nvidia sin import corregido.
      Sonnet 5 intro $2/$10 MTok hasta 2026-08-31 — deep ~2-3x el costo de
      fast, acotado a síntesis/tesis/canvas/brief. Sin cambios en Railway.
- [x] **Gráficos rápidos** (agente D): esqueleto instantáneo bilingüe cuando
      va a la IA; caché cliente localStorage (TTL 1h, LRU 30, interceptor
      scoped SOLO para POST /api/canvas/generate); patrones locales nuevos
      ('compara X y Y' barras, 'riesgo de X' desglose NRS, 'cripto' top 10);
      prefetch de velas (nodo enfocado + portafolio, máx 4). De paso: bug de
      'mi cartera' (leía pos.qty inexistente; forma real {sh,bp}).
- [x] **Etapa J — Expediente Cripto Top 50** (2 agentes): nodes/crypto_intel.js
      (+CRYPTO_CATS 11 categorías con blurbs simples bilingües) y
      crypto_intel2.js — 50 fichas {what,mech,tok,cats,risks,pos} ES+EN,
      50/50 ids CoinGecko VÁLIDOS (verificado contra la API). warn en:
      zcash, monero, usd1-wlfi, aster-2, world-liberty-financial.
      UI engine/crypto.js reescrita: vista 🗺 Mapa (tarjetas por categoría,
      chips con 24h% y ⚠, default), ☰ Lista (filtros por tesis, badges 📋/⚠),
      Detalle (gráfico 90d + Expediente Khipus de 6 bloques + banner ⚠ +
      disclaimer). Fuente: KHIPUS_CRIPTO_TOP50_EXPEDIENTE.md — capa estática
      jul-2026, REFRESCAR CADA 3-6 MESES (recordatorio del propio doc).
- [x] Khipu prompt: sabe del tab 'crypto' + lee errores did_you_mean tal cual.
- [x] Gates: node --check 13 archivos, py_compile 5, 8 bloques inline OK,
      pytest 56 passed. Verificación en vivo local: resolver 8/8, _surface,
      caché/prefetch de charts, mapa cripto, detalle EN con banner Aster.

## Etapa K — Burbujas cripto + universo 2D + caso Opera (2026-07-12, sw v77)

Feedback: "lo de cripto quisiera algo más visual, investiga alternativas y
propónme cosas" + "el 3D sigue sin dar, hay que hacer algo".

- Investigación: CryptoBubbles (burbujas), Coin360/TradingView (mosaico
  térmico). Artifact con 3 maquetas interactivas (burbujas / mosaico /
  galaxia): https://claude.ai/code/artifact/d8f2317b-11ca-42af-b999-f0a9bc15c59f
  **Fabrizio eligió 🫧 BURBUJAS VIVAS.**
- [x] engine/crypto.js: vista Burbujas como DEFAULT (canvas, física suave,
      tamaño=√mcap, color=24h%, anillo rojo punteado=⚠ del expediente,
      drag, tap=tarjeta con "Ver ficha"→detalle). Vistas: Burbujas|Lista
      (la vista tarjetas "Mapa" se eliminó — regla de simplificar; los blurbs
      educativos ahora aparecen al filtrar por categoría). rAF se pausa con
      document.hidden o panel oculto.
- [x] engine/universe2d.js (agente, ~700 líneas): respaldo TOTAL del 3D en
      Canvas 2D puro — mismo layout semántico (X=cadena, Y=NRS, Z=parallax
      3 capas), 555 nodos + 1600 links a 60fps, estrellas+nebulosas, glow
      pre-renderizado, clic=cadena verde/naranja, doble clic=jumpTo, pan/
      zoom/pellizco, modo lite si cae de 22fps, vigilante 0×0. OJO: si
      three.js ya reclamó #graph-canvas crea gemelo #graph-canvas-2d encima
      (un canvas solo admite UN tipo de contexto — hueco real descubierto).
- [x] app.html: _startUniverse2D(reason) + 3 enganches: catch de init 3D
      (3d_init_fail→2D), webgl_missing en _go3D (entra el 2D igual, nunca
      más "no pasa nada"), y monkey-patch de _ultraSafeMode (pantalla negra
      del selfcheck → escala a 2D). Beacons: universe2d_fallback/fail/on.
- **CASO OPERA (dato de Fabrizio vía AskUserQuestion)**: prueba el 3D en una
  COMPUTADORA DE ESCRITORIO CON OPERA — no la laptop Chrome v74. Esa Opera
  corre copia vieja (0 beacons, sin cripto, 3D viejo). Instrucciones dadas:
  ventana privada → verificar pie v77 → si funciona, borrar datos del sitio
  en la Opera normal. Sus beacons desde Opera confirmarán (tarea #20).
- [x] Gates: node --check, 8 bloques inline, 0 errores consola; verificado
      en vivo: burbujas dibujadas y dimensionadas, universe2d init/focus/
      destroy OK.

## Etapa L — 🪐 Universo 2D como motor PRINCIPAL (2026-07-12, sw v78)

Fabrizio, tras 5+ rondas: "mano no da el grafo 3d, no importa q hagas nada
cambia, lo puedes arreglar o lo borramos nomas?". Beacons: SIGUEN en cero
desde sus equipos → su máquina Opera corre copia vieja que ningún deploy
alcanza. DECISIÓN (ni arreglar WebGL a ciegas ni borrar la feature):

- [x] El botón 🪐 (chip + zoom) abre SIEMPRE el Universo 2D (universe2d.js,
      Canvas puro) — no puede fallar en ningún equipo con código actual.
      Segundo tap = volver al mapa SVG. Chip renombrado "🪐 Universo" (sin β).
- [x] El motor WebGL (graph3d.js) NO se borró: queda tras la bandera
      ?webgl3d=1 en la URL para retomarlo con diagnóstico real algún día.
      Sus integraciones (hypergraph/SecondBrain/scatter) solo viven en ese
      camino legado.
- [x] Guía actualizada (Universo funciona en cualquier equipo; FAQ con el
      remedio de la copia vieja: borrar datos del sitio).
- [x] Verificado en vivo: entrar (universo activo, svg oculto, chip on,
      beacon universe2d_fallback reason=primary v78) y salir (svg vuelve).
      0 errores de consola.
- CHECKLIST FINAL DE FABRIZIO (lo único que falta de SU lado):
  1. Opera desktop: borrar datos del sitio UNA vez (candado → Datos del
     sitio → Borrar) o probar primero en ventana privada. Sin esto esa
     máquina seguirá congelada en la versión vieja PARA SIEMPRE.
  2. Railway: REMIGRATE_ON_BOOT=1 (una vez) para re-migrar la ontología
     limpia en prod; quitarla después.
  3. Probar Khipu por voz end-to-end una vez.

## Etapa M — Trading cripto en papel, integrado en Khipu (2026-07-13, sw v80)

Pedido: "haz que se pueda tradear cripto… la idea es que todo se vaya
integrando en el bixby y en su pantalla… super integrado". 3 agentes en
paralelo contra contrato fijo + integración del orquestador:

- [x] SERVER (server.py): /api/trade/order acepta notional (1..100000, USD)
      o qty; símbolos cripto 'BTC/USD' → valida contra catálogo + fuerza
      tif='gtc'; GET /api/trade/crypto/assets (cache 1h en módulo, nunca
      cachea 401/403); /api/trade/account devuelve paper:bool; tools Khipu
      place_paper_trade + get_portfolio_status registrados + sección PAPER
      TRADING en el prompt (confirmación verbal obligatoria, sin consejos).
      Los tools llegan a ElevenLabs en el próximo arranque (BIXBY_AUTOSYNC).
- [x] BIXBY/CABINA (voice/cockpit/command_center): flujo confirmado-primero
      (confirmed=false → resumen hablable bilingüe → sí → confirmed=true);
      helpers compartidos _resolveTradeSymbol / _tradeAccountInfo /
      _executeTradeOrder (clamp $1-100k, anti-doble-envío 90s) /
      _openBrokerStage; stage 'broker' en Cabina (cuenta + badge 🧪/🔴,
      posiciones con P&L, órdenes, botón 💼 Bróker); comandos "compra 100
      dólares de bitcoin"/"vende 20 de solana"/"mi cuenta" por voz y texto
      con tarjeta de confirmación. 37 asserts del harness en verde.
- [x] FICHA CRIPTO (engine/crypto.js): caja 💼 Operar en el detalle de
      monedas tradeables (badge, monto USD, Comprar/Vender, confirmación
      inline, resultado con id o error verbatim, enlace al broker).
- [x] INTEGRACIÓN (orquestador): window._tradeFetch expuesto (PIN en UN
      lugar); FIX de contrato: voice.js ahora lee también notional_usd (el
      server declara ese nombre — sin el fix la voz preguntaría el monto en
      bucle); _surface('trade') SIN arg → _openBrokerStage; FIX prompt():
      el stage broker carga NO-interactivo y en 401 pinta formulario de PIN
      inline (nunca prompt() del navegador — bloqueado en móvil/PWA);
      CLAUDE.md: contrato de trading + 56 tests.
- [x] Gates: node --check ×6, py_compile, 8 bloques, pytest 56 passed.
      Local verificado: parser sí/no-falsos-positivos, 403 sin PIN se
      muestra verbatim sin romper, sin prompt() al abrir el broker.
- FABRIZIO para activarlo: (1) TRADE_PIN en Railway Variables (sin él todo
  trading queda bloqueado a propósito); (2) en app.alpaca.markets modo
  Paper + aceptar el acuerdo de cripto si lo pide; (3) ALPACA_BASE debe
  seguir siendo paper-api.alpaca.markets hasta probar semanas en papel.

## Etapa N — CAUSA RAÍZ del "3D no da" ENCONTRADA Y CORREGIDA (2026-07-13, sw v84)

Tras 6+ rondas, verificando EN VIVO con el panel a 1280×800 (no 0×0) y
manejando el botón como usuario, aparecieron DOS bugs reales (NO era la caché
de Opera, aunque eso también contribuía):

1. **onclick del chip 🪐 pisado** (app.html:4327): un bucle
   `querySelectorAll('.tabs .tab').forEach(b=>b.onclick=()=>switchTab(b.dataset.tab))`
   sobrescribía el onclick inline del chip. Como el chip NO tiene data-tab,
   ejecutaba `switchTab(undefined)` → NUNCA llamaba a _go3D → "no pasa nada".
   ESTA era la causa raíz real de todas las rondas. FIX: el bucle solo cablea
   los que tienen data-tab (`if(b.dataset.tab)`).
2. **Canvas 0×0**: el canvas del universo vivía dentro de <main>, que se
   oculta al cambiar de pestaña → 0×0 → negro. FIX: el 🪐 ahora abre un
   OVERLAY position:fixed a pantalla completa (#uni-ov con #uni-canvas),
   SIEMPRE dimensionado, independiente de <main>/SVG/WebGL/pestañas.

- [x] app.html: _ensureUniverseOverlay/_openUniverse/_closeUniverse; _go3D
      reescrito (overlay primario; WebGL solo con ?webgl3d=1); fix del bucle
      de onclick (4327); primer pintado con redraw().
- [x] engine/universe2d.js: método público redraw() (pinta 1 frame sincrónico,
      con guard U.inRedraw para NO crear loops rAF paralelos) — sirve de
      primer pintado y de verificación cuando rAF está estrangulado.
- **VERIFICADO objetivamente** (lo que faltó siempre): con viewport real, clic
  REAL en el chip → overlay abre; canvas 1280×800; redraw() pinta 97.5% del
  canvas, 90k px brillantes (estrellas+nodos), focus('Nvidia') OK; ✕ cierra y
  desactiva. Nota de método: el panel de preview corre con document.hidden →
  rAF casi congelado (1 tick/600ms); por eso las "pantallas negras" de mis
  verificaciones ANTERIORES eran artefacto del panel, no del app. redraw()
  sortea eso. En el navegador real de Fabrizio (con foco) rAF corre a 60fps.
- Gates: node --check, 8 bloques inline OK. sw v84.
- Opera de Fabrizio: si AÚN ve negro, es la copia vieja cacheada — borrar
  datos del sitio una vez (sigue pendiente de su lado).

## Etapa O — Khipus Finance AI: 9 frentes + rebrand + Cabina inicial (2026-07-13, sw v85)

Presentación mañana en OTRA máquina. Workflow de 9 agentes (archivos disjuntos)
+ integración del orquestador en app.html/sw.js. Rebrand a **Khipus Finance AI**.

- [x] SERVER (server.py/config/ai): **Sonnet 5 en TODO** (fast y deep;
      thinking desactivado para que no trunque el JSON/comandos); **fix Alpaca
      404** (normaliza ALPACA_BASE con rstrip('/') — la barra final causaba
      //v2/account) + GET /api/trade/diag; POST /api/crypto/analyze (cauto);
      POST /api/research/deep (más allá del nodo); ruta /api/sim/agents;
      prompt Khipu cauto con postura + tools run_agent_simulation/deep_research.
- [x] SIM (core/sim_agents.py NUEVO): motor por AGENTES estilo MiroFish — cada
      empresa un agente + Gobierno EE.UU./China + Geopolítica/Taiwán + Mercado
      + sectores; 2 rondas con Sonnet 5; magnitudes REALISTAS clampeadas por
      tamaño (mega 12% / mid 20% / small 35%) — mata el "AGI=+30% a todos";
      fallback determinista si no hay IA (la demo nunca se cae). Verificado
      local: ok, 5 impactos, 10 agentes.
- [x] TIMEFRAME de la Terminal ARREGLADO (server /api/candles ignoraba
      range/interval → siempre 90d diario): ahora Yahoo primario respeta el
      timeframe. Verificado: 1d=79 puntos intradía vs 1y=251 diarios.
- [x] UNIVERSE: ejes/leyenda + categoría al seleccionar. ORB (engine/orb.js
      NUEVO): orbe de voz sin fondo, reacciona a niveles. CRYPTO-UI: botón
      Analizar con IA + insights + carga robusta. TERMINAL: fallback 402 (nunca
      celda vacía) + más claro + gráficos. TEMPORAL: arranca en 'Relevante'
      (~267 nodos) con botón 'Todas (585)' + onda de shock animada. BIXBY:
      barra de chat ABAJO, orbe conectado, muestra-en-pantalla, sim/research
      desde su terminal, consejo cauto.
- [x] CARTERAS SIMULADAS (engine/portfolios.js NUEVO): sub-tab 💼 Carteras en
      Mercado; crea carteras, dinero virtual, añade cualquiera de las 555
      empresas, P&L en vivo. Se quitaron las C1/C2 mediano/largo de la ficha →
      botón "💼 Añadir a cartera". Verificado montando en vivo.
- [x] REBRAND → **Khipus Finance AI** (solo VISIBLE: título, cabecera, boot, pie,
      guía, prompts, dossier). Internos intactos (caché sw, localStorage,
      globals Khipu*, /v1/*).
- [x] **Cabina de Khipu = PANTALLA INICIAL**: abre sola tras el boot, 1 vez por
      sesión (sessionStorage kh_bixby_landed), robusto (espera datos+cabina,
      si falla queda en el mapa). Verificado: abre con el orbe montado.
- [x] Gates: node --check 12 JS, 8 bloques inline, py_compile, **pytest 61
      passed**. Local: v85, 0 errores de consola, todas las piezas cargan.
- PENDIENTE: deploy + auditoría cross-device (dispositivo nuevo, contexto
  limpio, barrido de botones) antes de la presentación.

## Pendiente que necesita a Fabrizio / decisión

- ⚠️ **Postgres de PRODUCCIÓN tiene la migración VIEJA** (495 objetos con
      duplicados). El motor y el guardado funcionan, pero para los 407
      canónicos limpios hay que re-migrar en prod (1 comando; requiere el
      DATABASE_URL de Railway — no accesible desde el entorno de desarrollo).
- ⏸️ Ingesta a 12k: decisión de gasto de IA para el enriquecimiento.
- ⏸️ SaaS: decisión de producto (gratis vs pago, pasarela).

## Etapas siguientes (plan en las tareas de la sesión)
2. **Etapa 2 — Datos limpios**: resolución de entidades (31 duplicados),
   dirección única de aristas, taxonomía tipada, pesos re-derivados (LLM
   batch), datos fuera del monolito → JSON servido, swap frontend a la API.
3. **Etapa 3 — Motor de matrices + hiperaristas**: blueprint matrix/ (NumPy,
   sparse por rel_type, snapshots con watermark, computed_metrics para NRS
   servido), hiperaristas como Factor+affects (cero cambio de esquema),
   UN kernel de propagación, agente MatrixSentinel → ProposedAction.
4. **Etapa 4 — Mapa unificado con capas**: 7 renderers → 2 motores
   (grafo 2D + globo), LayerRegistry, 4 pestañas, 9 macro-sectores, un solo
   store de estado, borrar stack 3D conservando datos, regenerar Guía+Khipu.
5. **Etapa 5 — Predicciones internas + INSIGHTS**: kernel de matrices +
   presets como hiperaristas nombradas, War-Room como visualización,
   pestaña INSIGHTS (feed + brief + panel junto al mapa), control único de
   frecuencia (manual por defecto).

### Cierre de Phase 3 (2026-10-03)
- ✅ Segundo candado del dinero: `brokerage.service._execute` exige memo del
  comité `approved` (y que sea el memo que preparó ESA orden) para toda orden
  `source='committee'` — falla cerrado (`memo_not_approved`). Ver PHASE3.md.
- ✅ Velocidad del mapa (etiquetas display:none; ver nota de Velocidad paso 2).
- Queda para Fabrizio: probar en producción, llaves de Railway
  (BROKERAGE_ENC_KEY, TRADE_PIN fuerte, FINNHUB_WS_KEY, opc. ANTHROPIC_ADMIN_KEY),
  backups de Postgres, decidir el tono del agente de trading.

### 🪟 VISIÓN PRÓXIMA ETAPA (pedido 2026-10-03, NO es parte de Phase 3)

"La vista general sea como el interfaz de Khipu; poco a poco será el ÚNICO
interfaz. Todo lo que se genere o abra, como una pestaña/ventana que se puede
mover y cambiar de tamaño. Punto medio entre ChatGPT y Windows 11: ajustar la
información que se muestra sin dejar de ser un chatbot."

Plan acordado (escritorio Khipu = evolución de la Cabina, engine/cockpit.js):
- **K1 — Gestor de ventanas** (`engine/desktop.js`, `window.KhipuDesk`):
  `open(kind,arg)`, ventanas con barra (título, minimizar, maximizar, cerrar),
  arrastrar/redimensionar, foco/z-index, snap a mitades/cuartos (estilo Win 11),
  barra de tareas con lo abierto. `_surface()` pasa a abrir ventanas en vez de
  reemplazar el stage (una sola puerta: no crear otra).
- **K2 — Chat siempre presente**: el chat de Khipu es el "fondo"/panel fijo;
  las respuestas traen botones "abrir en ventana" (dossier, gráfico, comité,
  cartera…). Mobile: ventanas = hojas apiladas a pantalla completa (sin
  arrastre).
- **K3 — Migrar vistas**: cada pestaña vieja (mapa, mercado, análisis, geo,
  espacio, terminal, canvas, comité, cartera) como contenido de ventana;
  las pestañas clásicas quedan como modo "clásico" hasta retirarlas.
- **K4 — Espacios guardados**: disposición de ventanas persistida
  (`kh_desk_layout`, sincronizada por engine/sync.js) + layouts predefinidos
  ("Mañana", "Trading", "Investigación"); Khipu puede ordenar ventanas por voz/texto.
- Riesgos: vistas que asumen ser únicas en el DOM (ids fijos, globo/mapa
  WebGL único) → al inicio, 1 instancia por vista pesada; rendimiento con
  varias ventanas vivas (pausar las ocultas/minimizadas).

Entorno de desarrollo local (Windows, PC de Fabrizio, instalado 2026-07-03):
Python 3.11 (winget) + PostgreSQL 16 (winget, postgres/devpass, DB
khipus_test). Correr tests completos:
`DATABASE_URL=postgresql://postgres:devpass@localhost:5432/khipus_test pytest tests/ -q`

---

## Decisiones tomadas (no reabrir sin razón nueva)

1. **Base de datos de la ontología: Postgres en Railway.** Neo4j Aura se
   conserva como espejo de solo lectura del Grafo Temporal — no se apaga.
2. **Backend: Flask/Python**, no Node.js. SQLAlchemy en vez de Prisma,
   Pydantic en vez de Zod, APScheduler en vez de node-cron, pytest en vez de
   Vitest/Jest.
3. **Prefijo de API: `/api/ontology/*`** — NO `/v1/*` (ese ya es el producto
   de API pública monetizado por tiers, `khipu_auth()`).
4. **Despliegue incremental a `main`**: cambios aditivos, producción siempre
   verde. El switch del frontend a leer desde la API se hace solo tras
   verificar en producción que el grafo se ve idéntico.
5. **Migración del portafolio**: `MKT.pos` vive hoy en `localStorage`. Migra a
   la ontología (`Position`) en Fase 1/2 sin romper la UX mientras tanto.

## Fase 0 — AUDITORÍA Y PREPARACIÓN

**Estado: ✅ COMPLETA**

- [x] `docs/AUDITORIA.md` — inventario completo (dónde vive cada dato, APIs
      externas, tipos de objeto/relación implícitos, corrección de supuestos
      del roadmap).
- [x] `docs/ESTADO.md` — este archivo.
- [x] `scripts/export_graph_v0.js` — exportador fiel (replica merge/alias del
      navegador vía Node `vm`, mismo orden de carga que `<script src>`).
- [x] `data/grafo_v0.json` — snapshot: 463 nodos, 1163 links (100% resuelven),
      40 categorías, 14 pre-IPO, 105 hechos temporales, 32 objetos de
      ontología. Validado isomorfo con los contadores de producción.
- [x] Test desactualizado corregido (`test_health_has_app_name` afirmaba el
      nombre de marca antiguo). Suite: **18/18 pasan**.
- [x] Producción intacta (no se tocó `server.py` ni `app.html` de cara al
      usuario en esta fase, salvo el fix del test).

## Fase 1 — LA ONTOLOGÍA COMO BACKEND

**Estado: ✅ COMPLETA (el núcleo bitemporal + API) · ⏸️ un paso a propósito diferido**

- [x] Esquema SQLAlchemy (`ontology/models.py`): `events` (append-only,
      bitemporal `valid_from/valid_to` + `recorded_at`) + `objects`/`links`
      materializados para lectura rápida.
- [x] `ontology/service.py`: `apply_event()` (inserta + materializa),
      `as_of_graph()` (time-travel real por VALIDEZ, reconstruido desde
      `events`, no desde la tabla materializada), `diff_graph()` (qué
      apareció/desapareció entre dos fechas), `object_history()`.
- [x] API `/api/ontology/*` (`ontology/api.py`, registrada como blueprint):
      `/status`, `/objects`, `/objects/:id`, `/objects/:id/links`,
      `/objects/:id/history`, `/graph?as_of=`, `/graph/diff?from=&to=`,
      `POST /events` (escritura de bajo nivel; Fase 2 la envuelve con el
      catálogo de Acciones).
- [x] **Prefijo `/api/ontology/*`**, no `/v1/*` (ese es el producto de API
      pública monetizado — ver `docs/AUDITORIA.md`).
- [x] Degradación elegante: sin `DATABASE_URL`, todo el resto de la app sigue
      funcionando igual (mismo patrón que Neo4j); `server.py` importa el
      blueprint en un try/except defensivo.
- [x] Script de migración `scripts/migrate_v0_to_ontology.py`: lee
      `data/grafo_v0.json` → genera eventos reales. **Reglas de fecha
      documentadas en el propio script** (empresas y links crudos sin fecha
      propia → GENESIS 2000-01-01; los 86 hechos temporales curados usan su
      `valid_from/valid_until` real).
- [x] **Validado end-to-end contra Postgres real** (local, para desarrollo):
      463 empresas + 32 objetos de ontología = 495 objetos; 0 ids sin
      resolver en la migración; time-travel correcto en ambas direcciones
      (ej. `as_of` antes/después de la sanción a Huawei 2019-05-16 y de la
      pérdida de Qualcomm-Huawei 2021-06-30); `diff()` detecta ambos cambios.
- [x] Tests: `tests/test_ontology.py` (8 tests: creación/actualización de
      objeto, links, time-travel antes/después, cierre de intervalo con
      LinkRemoved, diff añadido/quitado, historia ordenada, **migración
      isomorfa** — corre el script real y compara conteos con el snapshot).
      Se auto-saltan (skip) si no hay `DATABASE_URL` — no rompen CI sin DB.
- [x] `docs/AUDITORIA.md` documenta la corrección de arquitectura (Flask no
      Node, prefijo de API, Neo4j ya conectado se mantiene como espejo).

### ⏸️ Diferido a propósito (no es un olvido — es una decisión registrada)

**El swap completo del frontend** ("cambiar UNA línea para que TODO el grafo
cargue desde la API en vez del JSON embebido") se hizo de forma **parcial y
seguridad-primero**: el Grafo Temporal (`engine/temporal-graph.js`) ahora
consulta `/api/ontology/status` y muestra un badge "◈ ontología: N objetos"
cuando está configurada (verificación cruzada visible), pero **NO reemplaza**
`window.NODE_BY_ID`/`window.LINKS` como fuente de datos — de esos dependen
directamente 7 pestañas más (mapa, mercado, análisis, geopolítica,
simulación, Second Brain, Canvas) en un archivo de 12,568 líneas. Reemplazar
la fuente de datos central el mismo día de una reunión de inversión, sin
poder hacer regresión completa de cada pestaña, era un riesgo desproporcionado
frente al beneficio inmediato. **Recomendación:** hacer el swap completo en
una sesión dedicada, con checklist de regresión de las 8 pestañas, cuando no
haya una demo en vivo horas después.

## Fase 2 — ACCIONES: WRITE-BACK AUDITADO

**Estado: ✅ COMPLETA**

- [x] `ontology/actions.py`: catálogo de 9 Acciones con validación Pydantic
      (equivalente a Zod del roadmap): `CrearTesis`, `AnotarObjeto`,
      `MarcarRiesgo`, `ProponerVinculo`, `ConfirmarVinculo`, `RechazarVinculo`,
      `RegistrarDecision`, `AjustarPosicion`, `CorregirDato`.
- [x] Cada Acción ejecuta su efecto de dominio con eventos normales
      (`ObjectCreated`/`Updated`, `LinkCreated`) Y deja siempre un evento
      `ActionExecuted` — el rastro auditable (`actor` obligatorio: "toda
      Acción queda atribuida a alguien").
- [x] `execute_action()`: punto de entrada único, valida con el esquema del
      catálogo y rechaza actor vacío u objeto inexistente antes de escribir
      nada (rollback automático vía `session_scope`).
- [x] API: `POST /api/ontology/actions/<tipo>` (body: `{actor, ...campos}`),
      `GET /api/ontology/actions?actor=&type=&object_id=` (para el Registro).
- [x] Tests: `tests/test_ontology_actions.py` (10 tests: creación de tesis +
      vínculo automático, rechazo de stance/actor inválidos, objeto
      inexistente, `MarcarRiesgo` actualiza propiedades, propuesta→confirmación
      de vínculo, propuesta→rechazo cierra el intervalo de validez, decisión +
      ajuste de posición vinculados, corrección de dato con antes/después
      auditado, registro filtrable y ordenado). 36/36 tests totales del repo.
- [x] **UI real** (no solo backend):
      - Botón **"＋ Acción"** en la ficha de objeto del Grafo Temporal
        (`engine/temporal-graph.js`): formulario compacto según el tipo de
        objeto (empresas: crear tesis / marcar riesgo / registrar decisión /
        anotar; objetos de ontología: solo anotar). Pide el nombre del autor
        una vez (se recuerda en `localStorage`) — sin sistema de login, fuera
        de alcance de esta fase.
      - Panel **"📋 Registro"** (overlay global, mismo patrón que 🩺
        diagnóstico): timeline de todas las Acciones ejecutadas, filtrable
        por autor, con ícono/etiqueta por tipo y el detalle (razón/rationale).
      - Debajo de cada ficha de objeto: mini-registro de las últimas acciones
        sobre ESE objeto específico.
- [x] **Validado con un caso real**: se usó `CorregirDato` para arreglar el
      dato de SpaceX (`preipo: true → false`) que motivó gran parte de esta
      sesión — con auditoría de quién lo corrigió y por qué, en vez de un
      edit manual silencioso en el código fuente.

## Fase 3 — AGENTES QUE PROPONEN, HUMANO QUE APRUEBA

**Estado: ✅ COMPLETA**

- [x] `ontology/agents.py`: contrato `observe(session)->signals` /
      `propose(session, signal)->dict|None`. 4 agentes v1 (no 5 — Cronista se
      implementó como reporte de solo-lectura, ver abajo, no como agente que
      propone Acciones):
      - **Centinela NRS**: recalcula riesgo (fórmula geo+grado+margen+
        concentración, réplica server-side de `computeNRS`) y propone
        `MarcarRiesgo` si cruza el umbral (70).
      - **Lector GDELT**: muestrea las 5 empresas más conectadas, busca
        noticias reales vía GDELT, propone `AnotarObjeto` con resumen (IA).
      - **Guardián de Cartera**: deriva holdings de `PositionAdjustment`
        (Fase 2) — **limitación honesta documentada**: el portafolio
        "real" del usuario vive en `localStorage`, este agente solo ve
        posiciones registradas EN la ontología vía la Acción
        `AjustarPosicion`.
      - **Cartógrafo**: detecta empresas sin ningún vínculo vigente
        (nodos aislados), propone `AnotarObjeto` señalando la brecha.
- [x] Runtime: **sin scheduler interno** (gunicorn 2 workers duplicaría cada
      corrida) — `POST /api/ontology/agents/run` bajo demanda (botón manual
      o cron externo), con deduplicación por agente+tipo+objeto+ventana de
      tiempo para no repetir la misma propuesta en cada corrida.
- [x] Cola de aprobación: `ProposedAction` (pending/approved/rejected).
      `GET /api/ontology/agents/proposals`, `POST .../approve` (ejecuta la
      Acción real, actor='<agente> → aprobado por <humano>'),
      `POST .../reject`. Doble-aprobación bloqueada (409).
- [x] **Cronista** (Brief Matinal): `GET /api/ontology/agents/brief` —
      resumen en lenguaje natural de acciones + propuestas + nuevos
      vínculos en las últimas N horas. Informativo, sin cola de aprobación.
- [x] UI: botón **"🔔 Propuestas"** (overlay) — lista, permite EDITAR los
      campos antes de aprobar (inputs editables en cada card), Aprobar/
      Rechazar, botón "🔍 Revisar ahora" dispara `agents/run`.
- [x] Tests: `tests/test_ontology_agents.py` (7 tests) — Centinela detecta
      riesgo alto, Cartógrafo detecta aislamiento, dedupe entre corridas,
      aprobar ejecuta la Acción, rechazar no ejecuta nada, brief matinal,
      endpoints Flask.
- [x] Bug encontrado y corregido en el camino: la fórmula NRS (heredada del
      cliente, `app.html:computeNRS`) no tiene límite inferior en el término
      de margen — empresas pre-revenue con márgenes muy negativos (ej.
      Rigetti -2.5) inflaban el score muy por encima de 100 antes de
      truncar. En la réplica server-side SÍ se acotó `[0,20]`; **el cliente
      original conserva el mismo comportamiento sin corregir** — se dejó así
      a propósito (no se tocó una fórmula que el usuario ve en producción
      sin que lo pida), queda anotado aquí como candidato a revisar.

## Fase 4 — LENGUAJE DE COMANDOS + MOTOR DE ALERTAS

**Estado: ✅ COMPLETA**

- [x] `engine/khipu_lang.js`: parser de `<ENTIDAD> <FUNCIÓN> [ARGS]`.
      Se intenta ANTES de llamar a la IA en `command_center.js` (Khipu) — si
      no calza con la gramática, `tryParse()` devuelve `null` y Khipu sigue
      su flujo normal de lenguaje natural. Comandos exactos no gastan tokens
      ni tiempo de red a Claude.
      - `<TICKER> DES/GP/SUP/CLI/RISK/NEWS/SIM/FA/THESIS [texto]` — cada uno
        despacha a funcionalidad YA CONSTRUIDA (Second Brain, mapa,
        `__tkgOpenObj` del Grafo Temporal, `activateStress`,
        `/api/fundamentals`, o crea una tesis vía `/api/ontology/actions/CrearTesis`).
      - `PORT VAR` / `PORT PL` — usa `/api/portfolio-risk` y las posiciones
        de `MKT.pos` (localStorage) + cotizaciones cacheadas.
      - `GRAPH ASOF <fecha>` / `GRAPH DIFF <Nd>` — mueve la línea de tiempo
        del Grafo Temporal (nuevo hook `window.__tkgSetDate`) o consulta
        `/api/ontology/graph/diff`.
      - `ALERT <TICKER> PX|NRS > <valor>` / `ALERT REGION <región> NEWS` /
        `ALERT LIST` — crea/lista alertas en la ontología.
      - Resolución de entidad case-insensitive por id o por ticker (`.mkt`).
- [x] Motor de alertas: modelo `Alert` (Postgres) + `ontology.agents.
      evaluate_alert()`/`check_alerts()` — soporta `price` (Finnhub, reusa
      `server._fetch_quote_raw`, extraído de la ruta `/api/quote/<ticker>`
      con el mismo cambio ya cubierto por los smoke tests existentes),
      `nrs` (override o calculado), `news_region` (anotaciones recientes
      que mencionan la región). CRUD: `POST/GET/DELETE /api/ontology/alerts`,
      evaluación bajo demanda: `GET /api/ontology/alerts/check`.
- [x] Cliente: `OntologyAlerts` (en `app.html`) sondea cada 2 min (si el
      usuario activó notificaciones en Preferencias) y dispara
      `Notification` del navegador — **deduplicado por sesión** (una alerta
      no vuelve a notificar mientras la pestaña siga abierta, para no
      spamear si la condición sigue vigente). Coexiste con el `PriceAlerts`
      preexistente (cliente, solo-precio, solo-localStorage) sin
      reemplazarlo — resuelven necesidades distintas.
- [x] Tests: `tests/test_ontology_alerts.py` (5 tests) — dispara con NRS
      alto, no dispara bajo el umbral, no truena sin `FINNHUB_KEY`, CRUD +
      evaluación completa vía API, rechaza métrica inválida.
- [x] Verificado en Node (sin DOM) el parser completo: reconoce comandos
      válidos, devuelve `null` para lenguaje natural (sin falsos positivos
      con frases como "comprar 10 NVDA"), maneja bien la ausencia de
      `__tkgSetDate`/red sin romper.

## Fase 5 — PROFUNDIDAD DE DATO + LINAJE

**Estado: ✅ COMPLETA (alcance recortado a propósito, ver nota)**

Buena parte de los entregables de esta fase (precios en vivo, fundamentales
FMP, diagnóstico de pipelines) ya existían antes de esta sesión de
ontología — no se reconstruyeron. Lo que sí se añadió:

- [x] Ficha de objeto (Grafo Temporal): linaje visible con ⓘ —
      precio: "Finnhub/FMP · hace Ns/min/h"; NRS: "calculado (fórmula)" o,
      si se fijó vía la Acción `MarcarRiesgo`, "fijado manualmente por
      <quién> — <razón>" (consulta aparte a `/api/ontology/objects/<id>`,
      no bloquea el render inicial de la ficha).
- [x] 🩺 diagnóstico → "Ontología": ahora incluye el evento más reciente
      (fecha + fuente) — primera señal de "qué tan fresca" está la ontología.
- ⏸️ **Diferido a propósito**: el "dato alternativo nuevo" (calendario de
  capex/fabs, o cruce CelesTrak↔contratos de lanzamiento) — el roadmap
  mismo lo marca como "sesión aparte al final", no parte de la secuencia
  principal. WebSocket de precios en tiempo real tampoco se implementó
  (la infraestructura de polling ya existente cubre la necesidad sin
  añadir una pieza de infraestructura nueva el mismo día).

## Roadmap completo: Fases 0-5 implementadas (con las notas de alcance de
## arriba). Ver también la sección "Fase 3" para el detalle del framework de
## agentes y "Fase 4" para el lenguaje KHIPU + alertas.

## Contexto de sesión previo a la ontología (para no reconstruir)

Antes de este roadmap, ya se había construido (y sigue en pie, se reusa como
semilla):
- **Grafo de Conocimiento Temporal** (`engine/temporal-graph.js`): timeline
  con validez, D3 force-graph, ficha de objeto con precio en vivo + NRS +
  Khipu análisis + noticias, microsimulación de shocks (BFS con dirección
  semántica), chokepoints, exposición de portafolio. Persiste opcionalmente
  en Neo4j Aura (ya conectado, badge "neo4j 🟢").
- **Ontología cliente** (`nodes/ontology.js` + `ontology_facts.js`): 8 tipos
  de objeto, 12 tipos de relación, 32 objetos no-empresa, 58 relaciones
  tipadas reales. Esto se convierte en parte de la semilla de migración de
  Fase 1, no se descarta.

## Cómo continuar en la próxima sesión

1. Lee este archivo + `docs/AUDITORIA.md` + `ROADMAP_KHIPUS_ONTOLOGIA.md`.
2. Confirma con el usuario si ya provisionó Postgres en Railway (paso manual
   suyo, como con Neo4j Aura).
3. Arranca Fase 1 en el orden del roadmap: esquema → migración → API de
   lectura → switch del frontend. Actualiza este archivo al cerrar.
