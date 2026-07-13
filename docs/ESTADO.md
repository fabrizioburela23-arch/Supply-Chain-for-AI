# ESTADO — Khipus AI Finance Intelligence · Ontología (Palantir-style)

Archivo vivo. Cada sesión de trabajo en la ontología lee esto primero y lo
actualiza al terminar. Ver `ROADMAP_KHIPUS_ONTOLOGIA.md` (adjuntado por el
usuario) para el plan completo por fases, y `docs/AUDITORIA.md` para las
correcciones de arquitectura respecto al roadmap original (backend real =
Flask/Python, no Node; `/v1/*` ya es la API pública monetizada; Neo4j Aura ya
está conectado).

---

# REDISEÑO MAYOR 2026-07 — mapa único con capas + motor de matrices

Decisiones de Fabrizio (2026-07-03, no reabrir sin razón nueva): UN solo mapa
con capas activables; app final de 4 pestañas (MAPA/MERCADO/INSIGHTS/GUÍA) con
Bixby/terminal flotante; motor de predicción INTERNO (adiós MiroFish) centrado
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
- [x] **Bixby agente de voz total** (voice.js + server.py, 589cabd): Bixby ya
      dispara las funciones nuevas por voz. Camino de TOKENS en su propio texto
      (no requiere configurar herramientas en el panel de ElevenLabs, igual que
      NAV/TAB/STRESS): `[XRAY:id]` · `[COMPARE:a,b]` · `[SHOCK:id:kind]`
      (collapse|demand|price|sanction) · `[OPPS]` · `[INSIGHTS]`. Además client
      tools nuevos en `_handleToolCall` (open_xray, run_live_simulation,
      compare_companies, get_opportunities, show_insights) por si algún día se
      registran en ElevenLabs — devuelven datos reales. Resolvedor
      `_resolveNode` case-insensitive (id/ticker/nombre): Bixby dice "NVIDIA"
      pero el id real es "Nvidia" (NVDA). BIXBY_SYSTEM_PROMPT enseña cuándo usar
      cada token. Verificado en navegador con 407 empresas (X-Ray poblado,
      SHOCK TSMC→252 afectados, COMPARE TSMC vs Samsung).
- [x] **Cabina de Bixby — modo pantalla completa** (engine/cockpit.js, 0660527):
      Bixby deja de ser un botón y SE VUELVE la pantalla. El botón de Bixby y
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
        TODO), "tarda mucho" (instantáneo), "no hay modo Bixby pantalla entera".
      - Orbe plasma optimizado: el bucle salta canvas invisibles y escala el
        detalle al tamaño (antes dibujaba el orbe oculto de 200px en cada frame).
      - PENDIENTE conocido: el system prompt con los tokens nuevos solo llega a
        Bixby si ELEVENLABS_ALLOW_OVERRIDE=true + "Allow overrides" ON en el
        panel de ElevenLabs. La cabina por TEXTO funciona siempre (no depende
        de eso). La cabina por VOZ ejecuta acciones vía los tokens de voice.js.

## Sesión "modo máximo" 2026-07-10 (feedback: perfeccionar Bixby, 555 empresas, vivo, 3D)

Decisiones de Fabrizio (AskUserQuestion): sync ElevenLabs automático vía API ·
altas/bajas de empresas automáticas con registro reversible · caché interno
Redis-ready · el 3D nuevo REEMPLAZA al actual.

- [x] **Etapa A** (e92cf6e): fix DEFINITIVO del "veo lo mismo" — index() inyecta
      `?v=<versión SW>` en cada `<script src>` (bump de sw.js → URLs nuevas →
      código fresco siempre) + auto-reload en controllerchange (una vez, con
      guardas). Bixby 100% silencioso: BIXBY_SYSTEM_PROMPT reescrito (GOLDEN
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
      Bixby: tool deep_analysis (23+1 registradas vía sync).
- **Bixby sync VERIFICADO en producción**: ok:true, mode:full, 22 tools
  registradas (tras el fix del modelo TTS flash v2.5 para agentes en español
  — 652cb7e). Bixby ya no dice comandos.
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
      (empleados/fundación/ingresos/cap/moat/geo_risk/desc/grados) — Bixby ya
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
      prueba de voz Bixby end-to-end, y opcionales (workspace drag&drop,
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

Feedback: 3D pantalla negra otra vez, Bixby no entiende "nvidia" por voz,
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
- [x] **Bixby entiende nombres** (agente A): engine/resolve.js NUEVO —
      KhipuResolve.find() con ~150 aliases de transcripción de voz española
      ('en vidia'/'envidia'/'video'→Nvidia, 'te ese eme ce'→TSMC), fuzzy
      Levenshtein, sugerencias top-3; integrado en voice/command_center/
      cockpit/khipu_lang con fallback. notFound() bilingüe (Bixby DICE las
      sugerencias). VERIFICADO: 8/8 variantes de voz resuelven.
- [x] **Todo al frente** (agente A): window._surface(kind,arg) — Cabina
      abierta → renderiza EN su escenario (dossier fc-ov z→7600 sobre el
      cockpit z7000); cerrada → cierra overlays y switchTab ANTES de pintar.
      Todas las acciones visuales de Bixby pasan por _surface.
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
- [x] Bixby prompt: sabe del tab 'crypto' + lee errores did_you_mean tal cual.
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
  3. Probar Bixby por voz end-to-end una vez.

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
   store de estado, borrar stack 3D conservando datos, regenerar Guía+Bixby.
5. **Etapa 5 — Predicciones internas + INSIGHTS**: kernel de matrices +
   presets como hiperaristas nombradas, War-Room como visualización,
   pestaña INSIGHTS (feed + brief + panel junto al mapa), control único de
   frecuencia (manual por defecto).

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
      Se intenta ANTES de llamar a la IA en `command_center.js` (Bixby) — si
      no calza con la gramática, `tryParse()` devuelve `null` y Bixby sigue
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
  Bixby análisis + noticias, microsimulación de shocks (BFS con dirección
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
