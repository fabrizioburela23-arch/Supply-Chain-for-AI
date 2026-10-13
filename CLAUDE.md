# Khipus Finance Intelligence — CLAUDE.md

Terminal financiero (estilo Bloomberg + ontología estilo Palantir) para la
cadena de suministro de IA + capas macro. 937 nodos en el catálogo (la base de
producción tiene 1.294 objetos), 2.510 relaciones (dirección ÚNICA: source PROVEE
a target; 9 tipos de relación; 13 macro-sectores en SECTORS9 — expansión
multicapa 2026-08-02: energía, materiales, macro_credito, inmobiliario,
logistica). ~70 Factores sistémicos LATENTES (severity 1.0) con
`severity_crisis` en props — se disparan como what-if vía
`POST /api/matrix/factor/fire`, nunca dejarlos todos en severidad de crisis
(satura: ρ 2.63). Tope FRAGILITY_CAP=2.5 por nodo (artefacto `kernel.params` de governance/, leído por matrix/engine.py).
Desplegado en Railway (push a `main` auto-deploya, ~2 min).

**Al iniciar una sesión de trabajo: lee `docs/ESTADO.md`** — es la memoria
entre sesiones (qué se construyó, decisiones tomadas, qué falta).
`docs/AUDITORIA.md` = inventario de dónde vive cada dato.
**Arquitectura objetivo: `docs/ARQUITECTURA_V2.md`** (2026-10-11) — grafo = identidad/relaciones, vectores = estado,
tensores = solo cálculo derivado y versionado; Postgres como única base (sin base de grafos ni vectorial aparte);
un solo kernel, un solo NRS, un solo motor de contexto ($R(v\mid Q)$ + presupuesto). Antes de construir algo
"avanzado", ver su sección 19 (qué NO hacer) y la Fase 1 (20.1, orden de implementación).
**Brechas verificadas: `docs/BRECHAS_V2.md`** (2026-10-12) — 99 hallazgos medidos en el código contra la v2 (4 críticos:
7 motores de contagio con 164-315 empresas para el mismo choque, guardián de cifras que deja pasar "233,95 USD" y ±15 %,
sin historia de precios/FX/posiciones, ordenes por 3 caminos con controles distintos), lo que necesita decidir
Fabrizio (sección 2) y el orden de trabajo (bloques 0-5, sección 3). Empezar por ahí antes de la Fase 1.
**Infraestructura operativa: `docs/INFRA_OPERATIVA.md`** (2026-10-12) — los 4 pilares pedidos por Fabrizio: Objetos de
Decisión (libro mayor append-only con cadena de hashes, `core/decisions.py`), Puertas SHACL (TTL versionados compilados a
validadores Python de 0,01-0,3 ms; pySHACL solo como oráculo en CI), Hot Path Views (vistas en memoria versionadas por
`graph_version` tomado al confirmar, `/api/hot/*`, UN kernel) y Gobernanza (artefactos con hash, release aprobado con PIN,
G(t,κ) y replay). Plan de 26 pasos desplegables en su §10; decisiones nuevas D1-D7.
**CIERRE (2026-10-13): los 26 pasos están hechos** — `docs/CIERRE_INFRA.md` (español simple) dice qué hace cada pilar,
el estado de los 99 hallazgos de BRECHAS con su prueba, las 10 rutas de escritura que aún no dejan decisión (fijadas en
tests/test_cierre_infra.py: la lista solo puede ACHICARSE) y los clics exactos que solo Fabrizio puede hacer (ratificar,
activar kernel 2.0.0 / shapes / gates / guard con PIN, Railway). Empezar por ahí antes de la "Fase 2+".
**PASOS 1-4 HECHOS (2026-10-13)**: `events` es append-only DE VERDAD (disparador `kh_append_only`, `core/ledger_ddl.py`;
nunca UPDATE/DELETE: una corrección es un evento nuevo); `graph_version` se toma AL CONFIRMAR (hooks before/after_commit
en `core/hotviews/signals.py`, tablas `kh_versions`/`kh_tx_versions`, NOTIFY `khipu_graph` + sondeo 30 s) y reemplaza a
`_graph_epoch` (borrado) como clave de caché — notas/noticias/simulaciones NO la mueven; Confirmar/RechazarVinculo emiten
`LinkStatusChanged`; vistas rápidas v1 en `core/hotviews/` (GraphCore + Impact, mismo kernel `propagate_many`, paridad 0
diferencias en 969 choques) con `/api/hot/status|impact/<id>|chokepoints|factors|scenario` (sobre con graph_version,
generation, source, stale; ETag) y `/api/matrix/status|impact|metrics|factors|factor/fire` DELEGAN en ellas (impacto
98 ms → 0,6 ms). Env: `HOTVIEWS` (on), `HOT_WAIT_S` (2), `HOTVIEWS_COALESCE_S` (1), `HOTVIEWS_LISTEN` (on).
**PASOS 5, 6 y 8 (2026-10-13)**: IDENTIDAD — `core/identity.principal()` decide QUIÉN actúa: PIN válido = `op:fabrizio`
(D1), token MCP = `mcp:<id>`, agentes `agent:<id>@<ver>` (solo del registro), reloj `system:<tarea>`, sin PIN `ui:anon`; el
`actor` que manda el cliente es SOLO `declared_name` (etiqueta); `X-Khipu-Channel` (ui|voice|crypto|terminal|mcp…) se
anota pero nunca autoriza; `require_operator` ESTRICTO en producción (sin TRADE_PIN → 403). LIBRO DE DECISIONES —
`ontology/ledger_models.py` (decisions, decision_refs, decision_outcomes, decision_violations, decision_blobs,
ledger_seals, ledger_meta; todas append-only) + `core/decisions.py` (`decision_scope` en la MISMA transacción del
efecto; `record_rejection` en sesión propia que sobrevive al rollback; `approve`; texto personal solo como HMAC) +
`core/ledger.py` (sellador cada 30 s con cadena de hashes sobre events/kh_tx_versions/decisions/broker_audit; sesión
canónica UTC; columnas tardías SIEMPRE nulas o el verify fallaría) + `/api/ledger/status|decisions|decision/<id>|verify`.
Toda acción de ontología deja UNA decisión (`ActionExecuted.decision_id`); sin libro → 503 `ledger_unavailable`.
UN SOLO GRAFO — `core/hotviews/hot.graph()`: los 12 lectores del servidor (world, entities, screener, sim_agents,
semantic, portfolio_ai, research/router|context, tensor, MCP, chat) leen la generación vigente (Postgres o snapshot);
solo reconcile lee el catálogo a propósito. Desde Postgres se EXCLUYEN vínculos propuestos/rechazados y los hechos
temporales migrados. Ψ del tensor = kernel restringido a FLUJO (sin socios/inversores) hasta el paso 12.
**PASOS 7, 9, 10 y 13 (2026-10-13)**: ANCLA — `ledger_anchors` (1 fila/día UTC, tarea `ledger_anchor`), `GET
/api/ledger/anchor` PÚBLICO (solo día/sello/hash) que smoke-mcp.yml guarda cada día como artefacto de Actions (D7);
`verify` compara las últimas anclas con los sellos (`anchor_mismatch`); una ruptura registra `ledger.chain_break` y
BLOQUEA SOLO DINERO REAL (`ledger.money_gate()`: brokerage preview/confirm de cuentas live + /api/trade/order|close de la
casa en vivo → 423 `ledger_chain_broken`; papel nunca) hasta `POST /api/ledger/chain_ack` con PIN; sin base o con
estado ilegible = no hay dinero real (falla cerrado); `check_lineage` detecta una base restaurada. GOBERNANZA —
`governance/artifacts/*.json` (11 artefactos 1.0.0 con los valores de HOY: kernel.params, nrs.formula,
policy.broker_risk|committee|numbers_guard|auto_apply|decide|gates, ledger.kinds, ontology.schema|shapes) +
`governance/manifest.json` (los mantiene `scripts/build_governance.py`; `--check` en CI exige semver honesto y espejos
con vocabulary.json/decisions.KINDS/IR) + tablas append-only `gov_artifacts`/`gov_releases` + `core/governance.py`
(`param(aid, key)`, bootstrap 1.0.0 SIN ratificar en el primer arranque con base, `ratify` con PIN → decisión
`governance.ratify`, refresco cada 60 s) + `/api/governance/active|status|ratify`. Editar un artefacto/TTL/vocabulario
SIN subir versión = el import falla (CI lo atrapa). Env SOLO elige un release aprobado (D2: `GOV_RELEASE`,
`KERNEL_PARAMS=<semver>`…); `FRAGILITY_CAP`, `IMPORT_BULK_WEIGHT_FACTOR`, `DECIDE_MIN_CONF`, `DECIDE_WAIT_S` y
`COMMITTEE_MEMO_TTL_HOURS` ya NO cambian números (el 🩺 avisa). Paridad 0 diferencias
(tests/test_governance_seed_parity.py + tests/golden/). Un cambio de release reconstruye las vistas rápidas. PUERTAS
SHACL EN SOMBRA — `governance/shapes/*.ttl` (31 reglas) → `scripts/build_shapes.py` → `compiled.ir.json` →
`core/gates/` (solo stdlib, p95 61-117 µs) en G1 apply_event, G2 execute_action, G-PROP propuestas de agentes
(`proposed_actions.gate_report`), G-BULK importación y G8 decisiones; TODO solo avisa y queda en
`decision_violations` (GateReport/1 ES/EN; sin decisión en curso → una `audit.gates` por transacción);
`GET /api/ontology/gates`; `KHIPU_GATES=off` = solo emergencia. pySHACL/rdflib SOLO en requirements-dev.txt (CI:
conformidad 0 diferencias en ≥1.000 focos). UN KERNEL EN EL CLIENTE — `engine/hotclient.js` (`window.KhipuHot`:
`simulate`, `scenario`, `chokepoints`, `factors`, `rivals`, `stamp`; caché por generación + ETag, 8 s de tope,
errores bilingües, demanda `'up'` = mensaje honesto SIN cifras hasta PROP-17); borrados computeDownstream,
clientInsights/clientChokepoint, el 55 % fijo del X-Ray y el 4/0,85 de la sala de guerra; X-Ray, Cabina, livesim, voz
(`run_live_simulation` con `engine_generation`), insights, brief, secondbrain y el Grafo Temporal muestran el MISMO
número que /api/hot/impact (TSMC: 318 empresas ≥1 %). "Ganadores" = rivales poco golpeados con su % de DAÑO (nunca un
% de ganancia). tests/test_no_client_engine.py lo vigila.
**PASOS 12, 14, 15-17 y BLOQUE 2 (2026-10-13)**: VISTAS DERIVADAS (paso 14) — `core/hotviews/derived.py` + views
card/quote/geo/alerts/account: `/api/hot/card/<id>` (NRS con sus 5 términos = la fórmula única, proveedores/clientes
como PARES distintos de flujo, socios/inversores aparte, impacto, valuación privada verificada, estructura),
`/api/hot/nrs` (lote), `/api/hot/geo`, `/api/hot/quote` (con sello de fuente/edad); MCP get_company, chat, voz
(`_flow`, comparar), oswindows, agent_skills, World Monitor, Centinela/Guardián y el evaluador de alertas leen la
ficha (NRS de todos 22 ms; Centinela 1.049 → 35 ms). KERNEL 2.0.0 (paso 12) — `governance/artifacts/kernel.params@2.0.0.json`
(`"activation": "pin"`: NUNCA entra solo al release del repo): socios/inversores sin daño (#4), severidad de factores
0-10 (#5), dirección 'up' con el piso, estrés severo que amplifica, ranking por Σ impacto, scenario_engine solo siembra y
sim_agents toma los % del kernel. TODO es parámetro: con 1.0.0 (el vigente) los números son idénticos. Se activa con
`POST /api/governance/activate {artifact, semver}` (PIN → decisión governance.activate de op:fabrizio; deshacer = activar
la versión anterior) tras ver `GET /api/governance/preview` ("¿qué cambia?" sin tocar el kernel vivo); UI: 🩺 →
Gobernanza (engine/governance.js: ¿Qué cambia? / Activar (PIN) / Ratificar (PIN)). Con 2.0.0: TSMC 318 → 254 empresas,
ρ 1,21 → 0,91. UN CAMINO DE ÓRDENES (pasos 15-17) — `brokerage/alpaca.py` es el ÚNICO archivo que hace POST/DELETE a
`/v2/orders|positions` (tests/test_order_single_path.py lo escanea); /api/trade/order|close → `brokerage.service.house_order|
house_close` (cliente house, mismos run_checks con los límites de HOY — US$100.000 por orden, política `house_today`; cerrar
o reducir una posición por cantidad no tiene ese tope: `house_reduce`), decisiones order.preview/confirm/submit
(submit se escribe ANTES de llamar a Alpaca; sin libro → 503), approval.grant/deny, order.cancel; fallo tras enviar →
`order_unknown_after_send` + 502 con el client_order_id. Dinero real de la casa = `BROKERAGE_LIVE_ENABLED=on` +
"dinero real habilitado" en 👥 Clientes (si no → 403 live_not_enabled). Agente de trading: `trade.agent_signal` antes de
actuar, sus órdenes por el mismo camino (source='agent', aprobación salvo papel), config como `policy.change`; tras un
despliegue queda APAGADO con aviso (#14). Voz: `readback_sha` del resumen leído. Fills → `broker_fills` (append-only) +
decision_outcomes (tarea cada 60 s). Puertas de órdenes: `governance/shapes/order.ttl` (62 reglas en total) + vista
AccountRisk (Σw·Ψ) en SOMBRA; en producción corren cuando Fabrizio active ontology.shapes 3.0.0 + policy.gates 1.1.0
con PIN. MEMORIA DE LOS NÚMEROS (bloque 2) — `ontology/history_models.py` (instruments, prices_eod, price_adjustments,
fx_daily, metrics_eod, positions_eod; append-only salvo instruments) + `core/instruments.py` (empresa ≠ instrumento; el
ticker de hoy es el principal; 16 multi-listados + 28 OTC/ADR en docs/REVISION_INSTRUMENTOS.md para que Fabrizio marque)
+ `core/prices_store.py` (carga diaria tras las 22:00 UTC en su hilo; splits/dividendos como factores, nunca reescritura;
historia con huecos >12 días = incompleta; relleno de 5 años SOLO con PIN, reanudable, decisión data.backfill) +
`/api/prices/*`, `/api/instruments/review` + 🩺 "📈 Historia de precios" (engine/pricehist.js). Riesgo: cierres
ajustados alineados por fecha, FX diario por fecha, beta de Dimson para bolsas que cierran a otra hora; RSI de Wilder.
`/v1/*` sigue con su cálculo (decisión #12 pendiente).
**PASOS 18-21 Y BLOQUES 4-5 (2026-10-13)**: DECISIONES EN CADA SITIO — `core/decision_sites.py` (ayudantes: principal,
huellas, citar política, `reserve_id`, trabajo después de la respuesta con `decisions.submit_async`): committee.run (en la
MISMA transacción que el memo) + approval.grant/deny + puerta G5 (`governance/shapes/committee.ttl`, 7 reglas, sombra;
corre cuando se active ontology.shapes 4.0.0), committee.portfolio_advice, policy.change (límites de clientes y de IA con
valor anterior), research.job/research.run/claim.status (falsadores y calificaciones → decision_outcomes), proposal.create /
proposal.auto_apply (D6: igual que hoy, policy.auto_apply 1.0.0), alert.rule (dueño en HMAC) y alert.fire (máx 1 cada
10 min por alerta), chat.answer (async: [F#], fuentes con as_of, herramientas, modelo; texto solo como blob de 90 días),
chat.route de Jev (decision_shadow.key = HMAC), mcp.tool_call (principal mcp:<id>, HMAC de argumentos, hash del resultado,
solo el código de error), whatif.shock / whatif.factor_fire / insight.snapshot. Sin libro → la acción se deshace (503
ledger_unavailable). AI_CALLS (paso 21) — `core/ai_calls.py`: UNA fila por pedido a la IA escrita SOLO desde core/ai.py
(`_ai_complete_raw` y `_complete_single`, que usa research/llm.CoreProvider), en cola con hilo escritor (0,02 ms en el hilo
del pedido); system/prompt/salida como blobs por hash; tabla append-only y SELLADA. CACHÉ DE PROMPT (L4-06): Claude
`cache_control` en system ≥2.000 caracteres; ai_usage separa cache_read/cache_write con sus precios (`cache_price_for`).
MOTOR DE CONTEXTO (bloque 4) — `core/context_engine.py`: UN detector de entidades (se reconstruye por graph_version; países
y palabras comunes no son empresas), R(v|Q), empaquetado con presupuesto y tabla [F#]; lo usan chat, live_facts, semantic,
research/context (fuentes una vez por job, noticias 10 min). Contrato MCP `mcp_server/contract.py`: `detail`
(summary|standard|full) + `max_chars` (12.000 por defecto) en TODA herramienta, recorte marcado (`truncated`,
`over_budget`; series de tiempo conservan lo más NUEVO); get_supply_chain Nvidia prof. 2: 112k → 10k caracteres.
Operaciones nuevas `mcp_server/ops.py` (solo lectura): run_scenario, get_subgraph, get_exposure, find_similar_entities,
calculate_correlation, get_history. LISTAS DE REVISIÓN (bloque 5) — `scripts/build_graph_review.py` →
docs/REVISION_GRAFO.md + docs/revision_grafo.json (cada ítem con `mark: null` y las acciones que se aplicarían; NADA
aplicado): 27 vínculos con fecha, 17 direcciones que el texto contradice (ratchet `text_direction` en audit_graph), escala de
pesos (462 con peso 1), 58 verbos fuera del vocabulario + 12 márgenes, 200 vínculos pesados sin fecha. Puertas compiladas:
69 reglas.
**PASOS 22, 23, 25, 26 Y 11 (2026-10-13)**: G(t,κ) — `ontology/bitemporal.py` (`known_at` = ISO o versión del grafo;
visible = versión ≤ κ, o recorded_at ≤ κ para eventos sin versión; `props_at` pliega en orden de REGISTRO) en
/api/ontology/graph|graph/diff|objects/<id>, /api/hot/impact (`core/hotviews/views/asof.py`, LRU 16, 503 asof_busy) y MCP
get_ontology_object; sin `known_at` el camino es el de siempre. GOBERNANZA COMPLETA — `core/governance_flow.py`
(proponer con PIN solo lo de `governance/tunables.json`, regresión en hilo → decisión governance.validate, programar con
effective_from / cancelar / deshacer, atribución), `core/governance_lint.py` (el MISMO lint que build_governance),
`core/governance_shadow.py` (formas propuestas en sombra), /api/governance/propose|validate|validation|cancel|history|
attribution; un MAYOR nuevo exige regresión (409 regression_required); una programada vencida se aplica antes de otra
activación; env NUNCA enciende una versión `activation: pin`. GUARDIA — `core/ledger_guard.py`: disparadores en
research_claims, committee_memos, broker_orders, proposed_actions, alerts, broker_clients, ai_settings que al COMMIT
exigen decisión (GUC `khipus.decision_id` o fila en decisions/decision_outcomes con el mismo txid); modo de
policy.guard (1.0.0 warn; 2.0.0 enforce con PIN); columnas de observación exentas. RETENCIÓN — `core/retention.py`
(ledger.retention 1.0.0, D3): purga diaria del CUERPO de blobs vencidos que nada citó en la ventana (decision_blobs solo
admite ese UPDATE, con una decisión retention.purge de la misma transacción); `verify_blobs` comprueba hashes.
`ontology/checkpoints.py` apagado bajo 20.000 eventos. PUERTAS EN BLOQUEO — policy.gates 2.0.0 (PIN): G1/G2/G-PROP/G-BULK
devuelven 422 (`GateViolation`, GateReport ES/EN); órdenes, comité y libro siguen en sombra; acciones con
`extra='forbid'` (lista blanca: `dudosos`); reconcile exige `expect` con `plan_sha`.
**PASO 24 (2026-10-13) — REPETIR DECISIONES**: `core/replay.py` `replay(decision_id)` (solo modo 'audit'): integridad
(hashes, blobs PURGADOS se dicen, sello, linaje) → release de ENTONCES por hash (gov_artifacts) → G(t,κ) con la versión del
grafo que se leyó → implementación RETENIDA (`core/impls.py`: IMPLS/STAMPS por versión; `module_view` = mismo código con los
números de otro release sin tocar el módulo vivo; `governance.pinned(arts)` por hilo) → `identical | differs` (rutas de
campo) `| not_replayable` (texto de IA nunca se re-pide: se verifican prompt/output_sha y el guardián; blob purgado; datos
en vivo no guardados; anterior al paso 24). Repetibles: whatif.shock/factor_fire, committee.run (umbrales→tamaño, blob
`replay_inputs`), order.preview/confirm (run_checks, blob `replay_inputs`), governance.validate y las PUERTAS de toda
decisión (blob `gate_focus`). Salidas doradas `tests/golden/impl_*.json` (`scripts/build_impl_goldens.py --check`): si
cambian, nace `@2` (nunca editar `@1`). Toda etiqueta `impl` nueva va a STAMPS (tests/test_impl_registry.py).
`/api/ledger/replay/<id>` (sin PIN = resumen sin valores, 10/min, un grafo a la vez → 503 replay_busy) · `/why/<id>` ·
`/audit`; MCP `replay_decision` (read); reloj `ledger_replay_sample` (1×/día UTC: 50 al azar + todas las de dinero →
`audit.replay`; un 'differs' pone ⚖ Gobernanza del 🩺 en rojo). UI: 🩺 → 📋 Registro → ⚖ Auditoría (engine/audit.js,
`openSistema('auditoria')`). Determinismo: ρ con `v0` fijo y factores en orden canónico (`_canonical_factors`).
**FASE 2+ LOTE I (2026-10-13)**: rutas de escritura sin decisión = 0 (tests/test_cierre_infra.py; revocar tokens nunca
depende del libro). `/api/trade/status` y `/api/diagnostics` sin PIN NO dicen papel/real (`mode_hidden`; UI 🔴 ante la
duda). CSP sin 'unsafe-eval' y `connect-src` CERRADO (self, wss://ws.finnhub.io, *.elevenlabs.io, CDNs del SW): un host
nuevo del navegador hay que añadirlo ahí (`CSP_REPORT_ONLY=true` = emergencia). Alias de voz ÚNICOS: `nodes/legal_names.js`
(`VOICE_ALIASES`, `RESOLVE_STOPWORDS`) → snapshot → core/entities (`voice_alias` 80 < 85 de escritura). Precios de IA con
vigencia (`core/ai_usage.PRICE_WINDOWS`). Riesgo: `core/risk_models.py` (EWMA, Ledoit-Wolf, covarianza por pares, Cornish-
Fisher con `cf_valid`, VaR/CVaR a N días, Sharpe aritmético, ADV) + `policy.risk` (1.0.0 = números de hoy; 2.0.0 con PIN).
Escenario → dinero: `core/scenario_pnl.py` + `kernel.calibration@*` (κ por versión del motor; con ajuste débil NO hay cifra)
+ `POST /api/hot/scenario_pnl` + `KhipuHot.pnlLine`. ⏱ del mapa = servidor (`/api/ontology/graph?as_of=&known_at=`).
Módulos nuevos: `core/voice_api.py` (todo /api/voice/* y el prompt de voz), `core/trading_agent.py` (/api/trade/agent/*),
`engine/trade.js` (`window._executeTradeOrder`, se carga ANTES de voice.js). Variables de modelo con `.strip()`.

## Arquitectura

- **BÓVEDA OBSIDIAN + GRAFO DEL CÓDIGO (2026-10-11)**: `vault/` es el repo visto como bóveda de Obsidian
  (una nota por módulo, grupo de API → módulo → quién la llama, herramienta MCP, variable de entorno —SOLO
  nombres— y sesión de este ESTADO; capas con colores; `01 Reporte del grafo` = cosas sueltas: sin pruebas,
  globales/rutas sin uso, variables sin documentar) + `vault/_grafo/graph.json` y `mapa.html` (mapa
  interactivo, d3 de cdnjs). La genera `python scripts/build_vault.py` (determinista, stdlib, sin IA ni red;
  la tabla de capas `REGLAS_CAPA` vive ahí). REGLA: regenerarla antes de commitear cambios que agreguen/quiten/
  renombren módulos, endpoints o variables de entorno — y como `tests/test_vault.py` corre `--check` (bóveda
  vieja = suite roja), en la práctica antes de todo commit que toque código o docs. Conflicto de merge dentro de
  `vault/` → NO resolver a mano: quedarse con cualquiera de los dos lados y regenerar. No editar notas generadas;
  lo personal va en `vault/Mis notas/` (el generador no la toca); `.obsidian/app.json`/`graph.json` se crean si
  faltan y después son de Fabrizio (solo se refrescan los colores de capa). `vault` está en .dockerignore.
- `app.html` (~3,460 líneas): el HTML/CSS de TODA la UI, 4 bloques `<script>`
  inline + su JS propio en `engine/app_*.js` (G5-06, 2026-10-13: PARTIDO SIN CAMBIAR COMPORTAMIENTO — cada archivo
  es, byte a byte, un bloque inline de antes, cargado con `<script src="engine/app_X.js"></script>` EXACTAMENTE donde
  estaba; scripts clásicos que comparten el ámbito global como antes, NUNCA defer/async/module). Orden:
  `app_main.js` (núcleo: i18n, tema, NRS, mapa d3, pestañas, precios, 🩺, arranque) → … → `app_coordinator.js`
  (Coordinator + Análisis/Terminal/Simulación) → `app_trade_panel.js` → `app_preflight.js` → `app_canvas.js` →
  `app_scatter.js` (lista fija en tests/test_app_split.py). Siguen INLINE a propósito: el 1.º bloque (arranque de
  emergencia + seguridad compartida + franja "servidor no disponible": debe correr aunque falle un archivo externo),
  el orbe (diminuto), el vigía de /api/health (red de seguridad del servidor caído) y la insignia de 👥 Clientes
  (diminuta); el CSS sigue inline (/engine se sirve como JS y el ?v= solo versiona .js). Código nuevo de app.html
  va al engine/app_*.js que corresponda, NUNCA a un bloque inline nuevo. Las pruebas leen el texto de antes con
  `tests/_app_source.app_source()` (vuelve a poner cada archivo en su `<script>`); solo las del orden de carga,
  el SHELL de sw.js y la cuenta de bloques leen app.html crudo. Esos archivos van con ?v=N INMUTABLES (antes iban en
  el HTML, siempre fresco): editarlos = subir CACHE de sw.js Y añadir una entrada a `tests/app_js_fingerprint.json`
  (la prueba imprime las huellas; sin las dos cosas la suite falla). Un shell guardado sin copia de sus app_*.js no
  se sirve offline (sw.js `shellCanBoot` → página offline). Tabs: map, market, analysis, geo, simulation, space, terminal,
  canvas, crypto, portfolios, tkg (◈ Grafo Temporal — ya SIN botón de pestaña: se abre como vista
  desde ⏱ del mapa, engine/maptime.js), guia (❓ Guía). La MISMA lista vive en core/khipu_chat.TABS
  (lo que el chat puede abrir; tests/test_cleanup_server.py las compara).
- `server.py` (~5,800 líneas): Flask sync + gunicorn **1 worker + GUNICORN_THREADS (12)**, `exec` + `--graceful-timeout 25`
  (NO subir workers: el estado en memoria — caché, rate limits, agente de
  trading — divergiría entre workers). Proxy de todas las APIs externas.
- `core/` (paquete Python): helpers compartidos server/ontology/matrix —
  `config.py` (keys IA/Finnhub/timeout), `http.py` (_safe_get/_safe_ticker +
  `rate_limit`, el decorador que usan server/matrix/ontology),
  `ai.py` (cascada Claude→Gemini→NVIDIA + _extract_json), `quotes.py`
  (_fetch_quote_raw), `entities.py` (Phase 1 M2: EL resolvedor server-side —
  id/ticker/label/alias/sufijo, devuelve {id,score,method,matched}; dos
  umbrales: ESCRITURA 85 vs BÚSQUEDA 60). Rompe la circularidad ontology→server.
  `company_data.py` (estados anuales FMP→Yahoo→AV en USD y perfil EN VIVO
  Yahoo/Finnhub; lo usan /api/findossier, /api/dossier y /api/company/live —
  NUNCA inventar cifras: el viejo `_dossierSynthetic` con Math.random se borró).
- `matrix/` (paquete Python, opcional): motor de matrices — `engine.py`
  (build_matrices por rel_type + as_of, active_factors=hiperaristas,
  fragility, propagate=EL kernel de shocks, compute_metrics/chokepoints),
  `api.py` (blueprint /api/matrix/*: status, /<rel_type>, POST /impact,
  /metrics, POST /insights, GET /insights/history, POST /factor/fire).
  Convención A[i,j]=i PROVEE a j. Sin DATABASE_URL → 503. `SOLE_LINK_FLOOR=6` (2026-10-06): la
  columna de cada tipo se normaliza por max(suma, 6) — un proveedor único transmite según su peso.
  Los números del kernel viven en `governance/artifacts/kernel.params@*.json` (paso 9); el navegador
  NO propaga (paso 13): lee /api/hot/* con engine/hotclient.js.
  `tensor.py` + `tensor_api.py` (ONTOLOGÍA NIVEL 2, 2026-10-06, sin BD): tensor de flujo R×N×N,
  influencia Ψ (misma semántica que propagate), métricas por empresa (concentración, países de
  proveedores, cap. aguas abajo en riesgo, fuentes de riesgo, comparables) y `suggest_links` para
  empresas nuevas (IncorporarEmpresa las PROPONE con confidence 0 → revisión). /api/tensor/*.
- `ontology/` (paquete Python): ontología Palantir-style —
  `models.py` (events bitemporal + objects/links materializados +
  ProposedAction + Alert + InsightSnapshot), `provenance.py` (Phase 1 M1:
  Source como ENTIDAD, id derivado de la URL, trust del vocabulario),
  `service.py` (apply_event con source_id/confidence, as_of_graph, diff_graph),
  `actions.py` (catálogo de 17 Acciones auditadas, Pydantic — incluye
  Activar/DesactivarFactor, RetractarVinculo, FusionarEntidad), `agents.py`
  (7 agentes + brief matinal + evaluador de alertas), `api.py` (blueprint).
- `engine/`: temporal-graph.js (~1,050 líneas, Grafo Temporal), khipu_lang.js
  (parser de comandos), guide.js (Guía), voice.js (Khipu voz/ElevenLabs),
  command_center.js (Khipu texto), graph3d.js (WebGL, ?webgl3d=1, carga perezosa), globe.js
  (motor de globo unificado; reemplazó a geoglobe.js+planetarium.js, borrados
  en Track A Fase 2), universe2d.js (camino sin WebGL, el default),
  secondbrain.js, canvas-data.js, hypergraph.js, geo_coords.js, timeline3d.js
  (Grafo Temporal en 3D: Z = fecha de inicio de la relación; modo "⬗ Tiempo 3D"
  de la pestaña tkg; solo hechos con fecha; montaje perezoso, dibujo bajo demanda).
  maptime.js (⏱ TIEMPO EN EL MAPA PRINCIPAL: slider de fecha + capa ⚡ Eventos;
  window.KhipuMapTime, __tkgShow(vista); GRAPH ASOF mueve el mapa).
  **KHIPUS OS v1 (2026-10-06) — LA interfaz** (spec y contratos: `docs/KHIPUS_OS.md`): la Cabina
  evolucionada. Arranca SIEMPRE al cargar (salvo `sessionStorage kh_os_classic='1'` = "Vista clásica").
  Tokens `--os-*` en `#bcp-ov` (claro = look del video, `body:not(.dark)`; oscuro = predeterminado).
  Barra superior mínima (mascota+Khipus, paleta ⌘K, "Herramientas / Tools" con TODAS las pantallas, mascotas de
  agentes, saldo de práctica 🧪/🔴 sin pedir PIN, ES/EN, ☾/☀, iniciales). ≥1100 px: chat en la columna
  central (`#kd-center`) y ventanas en FLANCOS (desktop.js `kh_desk_flank`, `isCentered()`); <1100 px:
  "solo chat" (`kd-solo`, `chatInCenter()`), ventanas encima. Esc NO cierra el OS. Ventanas nativas
  (`engine/oswindows.js`, `BixbyCockpit.registerKind`): glance ("en una mirada"), conviction,
  supplychain, agents. Mascotas y preferencias: `engine/mascot.js` (`KhipuMascot`, `KhipuAgentPrefs`,
  `kh_agent_prefs` sincronizado; SOLO presentación, nunca decide dinero). Chat: progreso real
  `GET /api/khipu/chat/progress/<req_id>`, respuesta con `agents_used`/`entities`/`cards`/`sources[].as_of`,
  `context.mode` simple|pro; perfiles `GET /api/agents/profiles` (core/agents_api.py). Mapa: no se
  calcula tapado (`window._ensureMapSettled()`). Escenas viejas con colores fijos llevan `kd-legacy-dark`.
  **ESCRITORIO KHIPU (2026-10-04, K1)**: desktop.js (`window.KhipuDesk`): dentro
  de la Cabina (cockpit.js) cada escena es una VENTANA (– ▢ ✕, arrastre,
  redimensión, snap a mitades/cuartos, barra de tareas; móvil = hojas). UNA
  sola puerta: `BixbyCockpit.stage(kind,arg,opts)` → `KhipuDesk.open`;
  `render(s,kind,arg)` pinta en el cuerpo de la ventana. Adopción de paneles
  (adoptInto) es POR VENTANA (`_adoptCtx`/`restoreAdopted(winId)`). Nuevas
  escenas: añadir a KIND_META (ícono/título ES-EN) y, si adoptan un panel, a
  adoptKinds; solo multi-instancia si pintan con `s.querySelector` (no ids
  globales). Clases de botones kd-b-* ≠ estados kd-min/kd-max. kh_desk_mode=off
  = Cabina clásica (no quitar: red de seguridad). Visión: será el ÚNICO interfaz.
  REDISEÑO 2026-07 (piel NEXUS): xray.js (X-Ray de empresa), statematrix.js
  (desde el paso 13 SOLO estado visual: `frames()` = película salto a salto con el `hop` del servidor,
  `baseline()`; NADA de propagación — las cifras salen de `window.KhipuHot`, engine/hotclient.js),
  livesim.js (simulación en vivo sobre el mapa), layers.js (capas del mapa),
  insights.js (tarjetas #an-insights), brief.js (brief matinal). Todos leen
  window.NODES/LINKS/computeNRS/SECTORS9 y degradan sin DATABASE_URL.
- `nodes/`: catálogo de empresas (nodes_*.js) + links (links_*.js) +
  ontology.js/ontology_facts.js (tipos y hechos tipados) +
  temporal_seed_facts*.js (105 hechos con fechas reales) + preipo_intel.js +
  legal_names.js (nombres legales → id; la usan resolve.js Y core/entities.py
  vía el snapshot — tras editarla, regenerar data/grafo_v0.json) +
  listing_status.js (GENERADO: estado en bolsa verificado con fuente — IPOs,
  compras, quiebras — que pisa al catálogo en merge_graph.js; regenerar con
  scripts/build_listing_status.py + export; nunca editar a mano).
- `scripts/`: export_graph_v0.js (snapshot) · migrate_v0_to_ontology.py.
- `data/grafo_v0.json`: snapshot canónico (937 nodos / 2.510 links + la tabla
  `node_id_alias`, que antes NO se exportaba y por eso el servidor no podía
  resolver alias) — se regenera con `node scripts/export_graph_v0.js` (usa nodes/merge_graph.js,
  la MISMA implementación de merge que el navegador; nunca duplicar).
- `research/` (Phase 2 — Agent Research Swarm): 8 agentes producen CLAIMS
  con evidencia citada (E#), horizonte, confianza CALCULADA y falsadores;
  tablas research_claims/research_evidence/claim_relations/agent_runs/
  research_jobs; blueprint `/api/research/*` (jobs, entity, claims/<id> =
  ¿Por qué?, activity, agents, budget, events). UI: engine/research.js
  (`window.KhipuResearch.open(id)`), comando `<TICKER> RESEARCH`. NUNCA
  COMPRA/VENTA. Env: RESEARCH_MODEL_DEFAULT / RESEARCH_MODEL_<TIPO>,
  RESEARCH_DAILY_BUDGET_USD (2.0), RESEARCH_AUTO_EVENTS (off). Docs:
  AGENT_ARCHITECTURE, CLAIM_MODEL, MODEL_ROUTING, AGENT_SECURITY.
- **PHASE 3 (2026-09-30)** — ver docs/PHASE3.md, BROKERAGE.md, MCP.md, INVERSION_TERCEROS.md:
  - `research/outcomes.py` (línea base de precio por claim → evaluación por
    horizonte vs SPY, track record, Brier, confianza calibrada; `evaluate_due`
    corre 1×/día desde core/live_caps) · `research/committee.py` +
    `committee_api.py` (/api/committee/*: comité de inversión — convicción por
    horizonte, tamaño por volatilidad objetivo, memo IA con guardián de cifras o
    determinista; SIEMPRE aprobación humana) · UI `engine/committee.js`
    (`KhipuCommittee.open(id)`, Mercado → 🏛 Comité, X-Ray, `NVDA COMITE`).
    KHIPUS OS (2026-10-09): el overlay #cm-ov usa los tokens --os-* (mismos valores que cockpit.js, test) y
    MASCOTAS por puesto (no hay personajes humanos: no reintroducir Valeria/Kenji/…); la sala nombra a los puestos por
    mascota (`research/committee._mascot_voice`, `agent_skills.SEAT_MASCOT/WORKING`).
    SALA DEL COMITÉ (2026-10-02): `research/deliberation.py` arma puestos + debate
    con PLANTILLAS sobre claims/evidencia/X#/D1/R1/Q1 reales (sin IA extra);
    en vivo vía progress.messages, guardado en memo.memo.transcript.
    DEBATE CON IA (2026-10-02 b): `research/debate.py` — cada puesto razona con IA
    + réplicas (guardián de cifras; S# al presidente; AgentRun por llamada); sin
    claims el comité ENCARGA la investigación primero; key_conclusions en el memo.
    PIZARRA (Comité → 📋, GET /api/committee/board, POST /board/refresh) +
    herramienta get_conclusions_board (MCP/Khipu) + tarjeta en el brief matinal.
    `research/analytics.py`: ratios/pares/técnico CALCULADOS como evidencia
    'analysis'; agentes en paralelo (RESEARCH_PARALLEL); research/errors.py.
    COMITÉ DE CARTERA (2026-10-03): core/portfolio_advisor.py + POST
    /api/committee/portfolio + engine/pfcommittee.js (Comité → 💼 Mi cartera; perfil
    kh_investor_profile). Consejo de IA, nunca órdenes.
    REPORTES/NOTICIAS/PREGÚNTALE de la cartera: core/portfolio_report.py, core/news_feed.py,
    core/portfolio_reports_api.py (/api/portfolio-report/*, /api/news/portfolio; dueño =
    X-Khipu-Owner) + engine/pfreports.js.
  - **GASTO DE IA**: `core/ai_usage.py` registra TODA llamada (core/ai.py check/record),
    límites con PIN (/api/ai/usage, /api/ai/usage/limits), UI 🩺 → 💰 Gasto IA
    (engine/aispend.js). Atribuir trabajo de fondo con `ai_context(feature, who)` /
    `bind(fn)` para hilos. No crear llamadas a proveedores fuera de core/ai.py.
  - **JEV / TypeSafe (2026-10-04)**: `core/decide.py` = ÚNICA puerta al modelo
    de DECISIÓN Jev (POST api.typesafe.ai/v1/systemone; choice/score/noul con
    probabilidades calibradas; no genera texto). Registra en 💰 Gasto IA
    (proveedor 'typesafe'). MODO SOMBRA por defecto (DECIDE_SHADOW=on): decide
    y se compara con lo que hizo el sistema (tabla decision_shadow,
    GET /api/decide/shadow con PIN de operador); manda solo si DECIDE_CONTROL
    lista la función. Primer uso: portero del chat (`chat_gate_*` en
    khipu_chat.run_chat). Nunca decide dinero. Ver docs/JEV.md. AL MANDO (2026-10-06, `DECIDE_CONTROL=chat_gate`):
    `decide.chat_plan` → local_fact = ficha SIN IA, needs_tools = ≤2 rondas, @agente local/fast/deep;
    `out.router` dice quién decidió. Desde 2026-10-10: con clave y DECIDE_CONTROL vacío, chat_gate manda por defecto (off/none/0 lo apaga).
  - `core/scenario_engine.py`: análisis estructural de escenarios (tema/actor/evento →
    golpeados/ganadores/caminos) para la simulación por agentes.
  - `brokerage/` (/api/brokerage/*): clientes con SU cuenta Alpaca (env / llaves
    cifradas Fernet BROKERAGE_ENC_KEY / OAuth), papel por defecto, dinero real
    = BROKERAGE_LIVE_ENABLED=on + client.live_enabled, controles previos
    (risk.py), preview→confirm, cola de aprobación, auditoría append-only,
    kill switch BROKERAGE_TRADING_ENABLED. UI `engine/clients.js`
    (`KhipuClients.open()`, Mercado → 👥 Clientes con insignia de pendientes).
  - `mcp_server/` (POST /mcp JSON-RPC, MCP 2025-06-18/2025-03-26; /api/mcp/*
    tokens kmcp_ con scopes read|research|trade hasheados; OAuth 2.1+PKCE en
    /oauth/* y /.well-known/*). UI `engine/mcpconnect.js` (🩺 → 🤖 Conectar IAs).
  - `core/world.py` (/api/world/*: events GDELT/USGS/EONET + estrechos +
    inestabilidad, exposure, brief, reference) + `engine/worldmonitor.js`
    (`KhipuWorld`): la pestaña Geopolítica ES el World Monitor (un solo globo;
    el alias geosituation.js se borró en la limpieza 2026-10-11).
  - `core/celestrak.py` (2026-10-13): ÚNICO cliente de CelesTrak para /api/space/tle y el chat (copia por grupo, nunca
    repite un grupo antes de 2 h — CelesTrak bloquea IPs insistentes —, última copia buena hasta 7 días, sin copia →
    órbitas de REFERENCIA rotuladas). No volver a llamar a celestrak.org desde otro sitio.
  - `core/space.py` (/api/space2/*: Launch Library 2 normalizado, caché con
    presupuesto de 12 req/h, stale honesto) + `engine/spacemonitor.js`
    (`KhipuSpace`): la pestaña Espacio ES el Space Monitor (globo + lanzamientos).
  - `core/portfolio_ai.py` (/api/portfolio-ai/ask|propose|themes): asistente de
    carteras (construcción determinista + explicación IA con guardián) dentro de
    engine/portfolios.js; crea carteras SIMULADAS, nunca órdenes.
  - engine/riskreport.js: pantalla guiada (mis posiciones / cartera rápida en
    USD / ejemplo) y resultado en lenguaje simple; build_report acepta {symbol, usd}.
  - **MISIÓN DE REPARACIÓN (2026-10-04, `REPAIR_LOG.md` + `docs/REPARACION_DIAGNOSTICO.md`)**:
    reparación sin features ni gasto nuevo; cada arreglo = 1 commit + test que
    fallaba antes (`tests/test_repair_*.py`). P0 investigación (R1-R6):
    `core/ai.py` corta-circuito por proveedor (`provider_available`,
    `circuit_open`, `ai_circuit_state`, `last_errors`; el 🩺 lo cierra con un ping)
    + `_retry_transient` (429/5xx/red); `research/llm.py` espera y reintenta el
    MISMO proveedor ante `AIBusyError` (nunca salta de proveedor por eso);
    `research/runner.py` cola FIFO de jobs (`execute_job_async` encola; workers
    `RESEARCH_JOB_CONCURRENCY`) + pool de agentes COMPARTIDO (`_AGENT_POOL`) +
    `_recover_orphans` tras reinicio; estados de ResearchJob: queued/running/done/
    **partial** (faltan analistas; `synthesis.coverage`; el siguiente pedido corre
    solo lo que falta, `only_missing`)/**deferred** (presupuesto agotado;
    `trigger.resume_after`; `resume_deferred` solo pedidos de personas, máx 3/día)/
    failed. Todo consumidor nuevo de jobs DEBE tratar partial y deferred.
    `core/scheduler.py` = ÚNICO reloj del servidor (registrar tareas en server.py;
    nunca IA). `research/health.py` → `/api/research/health`, bloque `research`
    en `/api/health`, tarjeta 🔬 del 🩺 y MCP `get_research_health`. Una sola
    tabla de precios de IA (`core/ai_usage.PRICES`; `research.llm.estimate_cost`
    delega). NO reintroducir: hilo por job, pool por job, `CLAUDE_RETRY_SLEEP_S`,
    `_PRICE` en research, ni "skipped por presupuesto". P0 comité (C6-C10):
    `validation_status`/`compute_sizing(validated=)` (sin ≥MIN_N calificaciones
    por analista → tamaño a la MITAD y "no validado"), `quorum_check` (fundamental
    + 3 de 4 o `decision_code='INSUFFICIENT_DATA'`, sin debate ni presidente IA),
    `research/falsifiers.py` (reglas `{metric, op, threshold, by}`; estado de claim
    `falsified`; `direction_errors` en agentes y presidente), conf-v2 en
    `research/confidence.py` (`computed` y `khipus:*` no son fuentes independientes;
    cifras de dinero sin fuente externa → tope 0.5), checkpoints en días hábiles NYSE
    (`business_days_after`, etiquetas `interim_5b`/`final_20b`…) y
    `core/live_caps._daily_outcomes` (marca el día solo si corrió bien; tarea
    `research_outcomes_daily`). Columnas nuevas van en
    `ontology/db._COLUMNAS_TARDIAS` (ALTER … IF NOT EXISTS), nunca a mano.
    P1 grafo (G1-G4): `scripts/audit_graph.py` + `data/graph_audit_baseline.json`
    (trinquete en tests/test_graph_audit.py: tras cambiar el catálogo, exportar y
    `--write-baseline` si MEJORA). Ontología append-only de verdad: `links.event_id`
    + `LinkCreated` idéntico vigente → `dedup_of` (no-op; `allow_duplicate` para
    hechos con ventana) + `LinkRemoved` con `properties.retracts_event_id` =
    retracción DIRIGIDA y RETROACTIVA (es una corrección: valid_from = el de la
    creación). Acciones `RetractarVinculo` / `FusionarEntidad` (alias → retired +
    merged_into; vínculos re-creados en el canónico con su fecha). Para "la
    relación terminó" seguir usando RechazarVinculo/LinkRemoved con fecha.
    `ontology/reconcile.py` (+ scripts/reconcile_v0_to_ontology.py, `/api/ontology/
    reconcile/plan|apply|rollback`, panel 🩺 engine/reconcile.js): catálogo ↔
    Postgres SOLO con eventos (canal `reconcile_v0:<run_id>`), aplicar = PIN +
    nombre exacto de la base; direcciones/pesos/faltantes/sobrantes solo si
    Fabrizio los marca; deshacer por corrida (de la más nueva a la más vieja).
    `NODE_BY_ID[alias]` SIEMPRE lleva al canónico (merge_graph.js): quien
    enumere NODE_BY_ID para listar nodos filtra `NODE_BY_ID[k].id === k`, y quien
    busque grado/vínculos por id usa `window._canonId(id)`. Revisión G5/G5b: un
    LinkCreated deduplicado SOLO "asciende" cuando su gemela se retracta con
    `promote_dedups: true` (lo emite solo `rollback_run`), si es de otro canal y
    no queda copia viva — misma regla en tablas y replay (`_promotion_choice`);
    el replay mata una creación con una remoción no dirigida solo si se REGISTRÓ
    antes. Reconcile: candado `pg_try_advisory_lock`, `expect` (plan revisado),
    PIN configurado OBLIGATORIO (sin TRADE_PIN → 403). Columnas tardías: solo se
    alteran si faltan (`lock_timeout`). P2: `core/world.source_down` (fuente con
    404/403 seguidos en pausa 1 h), `core/ops_check.py` (`/api/ops/last_check`),
    `scripts/smoke_mcp.py` (solo lectura), `core/logjson.py` (`LOG_JSON=on`).
  - **Khipu chat (2026-10-01)**: `core/khipu_chat.py` (POST /api/khipu/chat):
    cerebro con herramientas (bucle JSON, máx 5 rondas, ~45 s; reutiliza
    mcp_server/tools.py — SOLO lectura, nunca órdenes) + `engine/khipu_chat.js`
    (router compartido por la Cabina y command_center). Regla: SOLO atajos
    explícitos (gramática KHIPU, demo, compra/venta con confirmación,
    "gráfico:", nombres exactos de pantallas); toda pregunta va al cerebro.
    NO reintroducir el router de regex sueltos ni el "fallback = gráfico".
    Nunca mostrar texto crudo del modelo: si el paso JSON falla o trae restos
    (`leaked()`), `synthesize()` hace que el agente redacte la respuesta en prosa.
  - **VOZ PARA KHIPUS OS (2026-10-11)** — contrato v2 de 17 herramientas (antes 31): server.py `_bixby_client_tools`
    (+ `_VOICE_TOOL_TIMEOUTS` = `VOICE_TOOL_TIMEOUT_S` de engine/voice.js, test), `VOICE_SCREENS` = ids de
    `BixbyCockpit.screens()` con su nombre VISIBLE (test), `RETIRED_VOICE_TOOLS` (25) que cada sync SUELTA del agente
    (`voice_agent.ensure_tools(retired_names)`, sin borrar recursos ni webhooks del dueño; el 🩺 avisa si siguen) y
    voice.js conserva ALIAS para ellas. La pregunta hablada va al chat CENTRAL (`BixbyCockpit.chatVoice`); cada pantalla
    se abre como ventana; `@cadena: …` invoca a una mascota. RECORRIDO DE UN MINUTO: guion ÚNICO `engine/tour_script.js`
    (`window.KHIPU_TOUR`, JSON estricto; `core/tour.py`) — con la voz conectada lo NARRA el agente
    (`run_guided_demo` start/next/stop, `BixbyCockpit.tour`), sin conversación suena con la MISMA voz del agente
    (`GET /api/voice/tour/<lang>/<paso>`: solo frases del guion, caché) y sin voz queda escrito. Nunca reintroducir el
    texto del recorrido dentro de cockpit.js ni "cuenta simulada" fija (puede ser dinero real).
    BOTÓN DEL RECORRIDO (2026-10-12, "usa la voz antigua"): con la voz contratada (`BixbyVoice.isConfigured()` lee
    `window.V8.Keys`, NO un `Keys` global que no existe) abre una sesión de SOLO ESCUCHAR (`BixbyVoice.narrateTour()`,
    sin micrófono, `user_message` con el pedido, CONTEXT_UPDATE `listen_only:true`) y narra el AGENTE — la misma voz que
    hablando; 🎙 en esa sesión = hablarle (`upgradeToMic`, mismo socket); vigía de 35 s y respaldo local (9 s/20 s).
    NO mandar `user_activity` (ElevenLabs no deja hablar al agente ~2 s tras cada uno). Los clips son solo respaldo y
    usan la voz REAL (`voice_agent.tour_voice`: variante del idioma + ajustes + modelo) con ETag/no-cache.
    LA APP MARCA EL RITMO (2026-10-12 b, conversación real: el agente decía la frase 1 y terminaba su turno sin pedir
    `next` → "solo dice el primer paso"): tras `start`, cuando la frase terminó de sonar, voice.js avanza la pantalla y le
    manda la siguiente como `user_message` "[TOUR n/N] <frase>" (bucle `_driveTick`, máx. 2 envíos por paso, luego
    respaldo local / pausa); si el agente llama `next` igual, una sola entrega por paso. Nunca volver a depender de que
    el modelo encadene herramientas solo.
  - **Habilidades por agente (2026-10-06)**: `research/agent_skills.py` — al hablarle a un agente (@cadena,
    @tecnico…) responde DESDE SU ROL con su paquete en vivo (`skill_packet`: evidencia E# + extras S#: Cadena =
    tensor/países/riesgo/eventos; Técnico = indicadores; Fundamental = estados/ratios/pares…) sin exigir
    investigación previa ni base de datos; abre la ventana de su rol (acción `open_window` {kind, id}). Nunca
    volver a "sin conclusiones → investigación general". `FOCUS`/`SKILLS` bilingües; SKILLS se repite en
    oswindows.js (un test lo compara).
  - **LIMPIEZA "sin cosas sueltas" (2026-10-11)** — no reintroducir copias:
    - **Registro ÚNICO de agentes**: `engine/agents_registry.js` (`window.KHIPU_AGENTS`; JSON estricto entre
      `KHIPU_AGENTS = ` y el `;`) = mascotas (nombre, rol, colores, `ink`, puestos), puestos (ícono, nombres,
      `short_*`, `badge_*`, `call_*`, `desk`), palabras de mención (`@radar`, `@analista`, `@chain`… también en el
      servidor) y herramienta → mascota. Python lo lee con `core/agents_registry.py`; mascot.js, khipu_chat.js,
      committee.js, core/khipu_chat.py, research/agent_skills|deliberation|ask_agent|runner y core/agents_api
      derivan de ahí. Se carga ANTES de mascot.js (app.html + SHELL); los arneses de node de los tests lo cargan
      primero. Nueva mascota/puesto → SOLO ese archivo (tests/test_agents_registry.py).
    - Diálogos: `KhipuToast.prompt({password})` y `window.khipuActor({ask})` (engine/toast.js) — ningún
      `window.confirm/prompt/alert` en engine/ ni app.html (el PIN se pide OCULTO; tests/test_cleanup_dialogs.py,
      tests/test_cleanup_client.py). Actor por defecto: 'usuario'.
    - Investigación: `agent_runs.open_questions` (las preguntas abiertas ya NO van en `errors`; leer con
      `research.models.open_questions_of/errors_of`); `permitted_tools` se DERIVA de `context.AGENT_NEEDS`; el
      agente de noticias recibe el perfil en vivo; sin "skipped por presupuesto" por analista (el job se difiere).
    - Tres productos, tres nombres: **Investigación con evidencia** (equipo de analistas, engine/research.js),
      **Tesis rápida** (UNA respuesta de IA, `POST /api/thesis/quick`, antes /api/research/deep) y **Búsqueda
      profunda** (pregunta libre, `/api/deep/analyze`).
    - Borrados: `/api/ai/command` (sin llamadores), `engine/geosituation.js`, `run_agent`, `GEO_RISK`; graph3d.js e
      hypergraph.js se descargan solo con `?webgl3d=1`. `/api/voice/voices` y `/api/diag/recent` piden PIN de operador.
  - `core/pin.py`: EL verificador del PIN de operador (X-Trade-Pin) con bloqueo
    por IP (último salto XFF) y global compartido — `require_pin` (trading) /
    `require_operator` (escrituras de ontología). Nunca reimplementar.
- `sim/`: scenario_builder.js (seeds de escenario; `buildScenarioSeed`).
- ELIMINADOS (no recrear): `rag/` (nunca desplegado), `litellm/`,
  `nodes/nodes_core.js` (duplicado), el modo standalone y el stack de keys en
  el navegador (2026-07); `engine/geoglobe.js`, `engine/planetarium.js` y
  `sim/mirofish_client.js` + todo el proxy/diagnóstico de MiroFish (2026-09:
  era un microservicio EXTERNO; lo reemplazan los motores internos
  core/sim_agents.py y matrix/engine.py).

## Una base de datos: Postgres

- **Postgres** (`DATABASE_URL`, plugin de Railway): FUENTE ÚNICA DE VERDAD de
  la ontología. Eventos inmutables con `valid_from/valid_to` (validez) +
  `recorded_at` (sistema). Time-travel: `GET /api/ontology/graph?as_of=`.
  El Grafo Temporal es NATIVO (cliente + esta base; `/api/grafo/estado` → `store: 'native'`).
- **Neo4j se RETIRÓ el 2026-10-13** (decisión #6 de Fabrizio, docs/BRECHAS_V2.md): nadie lo leía. NO
  reintroducirlo (ni driver, ni `NEO4J_*`, ni `/api/grafo/seed`; tests/test_neo4j_retirado.py lo vigila).
- OPCIONAL: sin `DATABASE_URL` el server arranca igual (patrón
  try/except + `*_available()`). Nunca romper ese patrón.

## Namespaces de API — CRÍTICO

- `/api/*` — endpoints internos de la app.
- `/api/ontology/*` — ontología (objects, graph, actions, agents, alerts).
- `/v1/*` — **API pública MONETIZADA por tiers (JWT, `khipu_auth`). NO tocar,
  NO usar para features internas.**
- `/mcp` (+ `/oauth/*`, `/.well-known/*`) — servidor MCP para IAs externas
  (tokens kmcp_ propios, NO los JWT de /v1). `/api/brokerage/*`,
  `/api/committee/*`, `/api/world/*` — Phase 3.
- **DINERO — regla de oro**: toda orden de clientes pasa por
  `brokerage.service.preview_order → confirm_order/approve_preview`. Lo que
  proponen `mcp` o `committee` SIEMPRE espera aprobación humana (PIN) salvo
  BROKERAGE_AUTO_APPROVE_PAPER=on en cuentas de papel. Nunca crear otro camino
  que envíe órdenes a Alpaca: desde el paso 15 también el panel, la voz, cripto, la terminal, el cierre y el
  agente de trading van por `brokerage.service` (house_order/house_close) y SOLO brokerage/alpaca.py habla con
  /v2/orders|positions (un test lo escanea).

## Convenciones de datos críticas

- `computeNRS(nodeId)` → NUMBER 0-100, NO objeto. Memoizado (`_nrsCache`);
  llamar `window._invalidateNRS()` si LINKS cambia. **UNA fórmula (limpieza 2026-10-11)**: cliente =
  `_nrsTerms` (engine/app_main.js; computeNRS y computeNRSBreakdown la usan; secondbrain.js lee el desglose);
  Python = `core/world.client_nrs` (servidor `_compute_server_nrs`, MCP y `portfolio_ai.nrs` delegan ahí,
  con el grado de la ontología o del catálogo). Margen acotado [0,20] en las dos; redondeo como JS.
  tests/test_cleanup_nrs_parity.py corre la del navegador sobre TODO el catálogo y exige el mismo número
  que Python. Nunca re-escribir la fórmula en otro archivo. **El grado es ESTRUCTURAL (G4d, 2026-10-04)**: cuenta
  pares distintos source→target unidos por una relación de FLUJO
  (`vocabulary.json` `flow: true`: supply/fab/cloud/license/ppa/owns/deploy);
  partner/invest/affects/about y los pares duplicados NO cuentan. Misma regla
  en cliente (`_buildNrsDegree`, lista `NRS_FLOW_TYPES`), servidor
  (`server_flow_degree`, COUNT DISTINCT en SQL), catálogo
  (`ontology.vocabulary.flow_degree`: MCP `_nrs` y core/world). Consecuencia:
  los NRS visibles BAJAN para empresas con muchos socios/accionistas (el término
  "cadena" ya no se infla con 753 partner + 192 invest + 48 pares repetidos).
- **Confianza por link (G4c)**: `LINKS[i].conf` (0-1) y `.verified` salen del
  merge (`linkTrust` en nodes/merge_graph.js: texto "no verificado/no revisado/
  posible/sin confirmar" → 0.3/false; un 6.º elemento `{conf, verified, since}`
  en la fila del catálogo manda). El snapshot los exporta; `matrix/engine.py
  _eff_weight` multiplica el peso por conf (el navegador ya no propaga, paso 13); el MCP
  (`_link_trust`) los deriva del texto si el snapshot aún no los trae.
- **Proveedor/cliente = solo FLUJO (G4a)**: `get_company.top_suppliers/
  top_customers` y `get_supply_chain.edges` excluyen partner/invest (van en
  `related`; `include_partners: true` los devuelve a `edges`). Cada arista lleva
  `relation_class` (mapa cerrado en mcp_server/tools.py RELATION_CLASS).
- **Fecha centinela (G4b)**: `valid_from` = 2000-01-01 es `GENESIS_SENTINEL`
  (ontology/service.py, `is_genesis`): "desde que se rastrea", NO una fecha
  real. API/timeline/MCP la marcan `valid_from_known: false`; la UI muestra
  "desde que se rastrea / since tracked". Al serializar un valid_from nuevo,
  marcarlo igual.
- `RAW_LINKS`: arrays `[s, t, w, rel, type]`; los `{s,t,type}` de
  links_expand.js se convierten en el merge; `NODE_ID_ALIAS` normaliza ids.
- `LINKS` (post-merge): objetos `{source, target, w, rel, type}` — usar
  `lid(l.source)` para el id.
- `MKT.quotes[ticker] = {close, prev, pct?, live?, src, as_of, currency?, converted?}`
  (contrato 2026-10-04): `live` es el precio NUMÉRICO o está AUSENTE — NUNCA un
  booleano (LivePrices escribía `live:true` y `parseFloat(q.live)` daba NaN → "—" en
  la Terminal y precio 0 al operar). `src` ∈ finnhub|yahoo|marketstack (+ `via:'live_caps'`)
  y `as_of` (ISO) dicen fuente y antigüedad. Leer el precio SIEMPRE con
  `window.quotePx(q)`; chip de fuente `quoteSrcChip(q, ticker)`; "en vivo" = `quoteIsLive(q)`.
  NO usar `q.c` ni `q.pc`. Los precios de TODO el catálogo (569 tickers, todas las
  bolsas) llegan por `window.loadLiveQuotes()` (lotes de 100 → POST /api/quotes/live →
  `core/quotes.fetch_quotes_live`: cascada Finnhub→Yahoo en paralelo, caché 15 s,
  circuito de 60 s tras HTTP 429 de Finnhub → `finnhub_quota:true`). Marketstack es
  solo respaldo EOD opcional y nunca pisa una cotización más nueva (merge por as_of).
  `/api/quote/<t>` y `/api/quotes` delegan en la misma función (devuelven además `c/pc/dp/t`
  crudos por compatibilidad). `LivePrices.seed()` se ELIMINÓ (1.090 req/min → 429): no recrear.
  Portafolio del usuario: `MKT.pos` en localStorage `eco_pos`, SINCRONIZADO con el
  server por engine/sync.js (junto a kh_portfolios / kh_investor_profile; /api/user-state).
- `window.NODE_BY_ID` SÍ está expuesto (antes era undefined — rompía el Grafo
  Temporal en silencio; no quitar la línea `window.NODE_BY_ID = NODE_BY_ID`).
- `window.TEMPORAL_SEED_FACTS` + `window.ONTOLOGY` ({types, rels, objects})
  alimentan el Grafo Temporal cliente.
- Acciones de ontología: `actor` SIEMPRE obligatorio; el nombre del usuario se
  guarda en `localStorage.khipu_actor`.
- **API keys: SOLO en el server** (env vars de Railway). El modo standalone y
  el UI de keys en el navegador se ELIMINARON (2026-07); `SERVER_MODE` es
  constante `true` (se conserva la var porque engine/*.js la consulta) y
  `Keys.has(svc)` solo refleja `/api/health`. El PIN de trading del usuario
  vive en `localStorage.khipu_trade_pin` (header `X-Trade-Pin`).

## Funciones globales clave

- `switchTab(tab)`: tab ∈ {map, market, analysis, geo, simulation, space,
  terminal, canvas, tkg, guia} — `'sim'` NO existe, es `'simulation'`.
- `jumpTo(nodeId)` · `activateStress(nodeId)` · `renderMarket()` ·
  `computeNodeRadius(nodeId)`.
- `window.initTKGTab()` / `window.initGuiaTab()`: init perezoso de pestañas.
- `window.__tkgOpenObj(id)`: ficha de objeto del Grafo Temporal.
- `window.__tkgSetDate(fecha)`: mueve la línea de tiempo (lo usa KHIPU).
- `window.openSistema(tab?)`: overlay unificado 🩺 con tabs internas
  (diag / registro / propuestas). openDiagnostics/openRegistro/openPropuestas
  existen pero ya NO gestionan su propio panel — no recrear paneles sueltos.
- `window.KHIPU.tryParse(texto)`: parser de comandos — se intenta ANTES de
  llamar a la IA en command_center.js (devuelve null si no es comando).
- `window.openFinCard(idOrTicker)`: EL Dossier (📊) — funciona para TODO nodo
  (cotizada: franja en vivo + estados; no cotizada: ficha + dueño + noticias).
  Abrir desde botones con `_surface('dossier', id)` (queda sobre la Cabina).
  `window.KhipuLive.profile(ticker)`: perfil en vivo (caché 60 s).
- `window._openSecondBrain(nodeId)` · `window.BixbyVoice.toggle()` ·
  `window.nexusCore.runPreset(presetId)`.
- `window.KhipuResolve.find(texto)` (engine/resolve.js): resolutor robusto de
  empresas (aliases de transcripción de voz, fuzzy, sugerencias top-3) —
  TODO camino de entrada de nombres (voice/command_center/cockpit/khipu_lang)
  pasa por él. `KhipuResolve.notFound(q)` da el mensaje bilingüe.
- `window._surface(kind, arg)`: lo que Khipu muestra queda SIEMPRE al frente
  (dentro de la Cabina si está abierta; si no, switchTab + cierra overlays).
  No mostrar resultados sin pasar por _surface.
- `window.KhipuToast` (engine/toast.js): EL sistema de pop-ups/confirmaciones —
  `show({kind,title,body,mode})`, `confirm(opts)`, `confirmOrder(order)` y
  `order.sending/result/watch/filled`. Toda compra/venta (real o simulada) debe
  confirmar y notificar por aquí; no volver a `window.confirm` para dinero.
- `window.CRYPTO_INTEL` + `window.CRYPTO_CATS` (nodes/crypto_intel*.js):
  expediente cripto Top 50 bilingüe, capa estática jul-2026 (refrescar cada
  3-6 meses). UI en engine/crypto.js — tab 'crypto', vistas Mapa/Lista/Detalle.
- Actualizaciones de versión SIEMPRE silenciosas: _showUpdatePill ya NO
  muestra aviso (recarga al abrir o al ocultar pestaña — pedido explícito).
  No reintroducir pills/avisos de versión.
- Trading (papel por defecto): TODAS las rutas /api/trade/* exigen
  X-Trade-Pin (env TRADE_PIN; sin él → 403 y la UI muestra ese error tal
  cual). Cliente: usar SIEMPRE `window._tradeFetch(url, opts, interactive)`
  — nunca reimplementar el PIN. Cripto = símbolos 'BTC/USD' + notional USD;
  el server fuerza tif='gtc'. Badge obligatorio 🧪 SIMULADO / 🔴 DINERO REAL
  según `account.paper`. NINGUNA orden sin confirmación explícita (clic o
  sí verbal). Khipu (voz): place_order (flujo confirmed=false→resumen→sí→
  confirmed=true; `mode` paper|live sale de la cuenta REAL, nunca se asume papel) y get_account_status; broker en Cabina:
  `window._openBrokerStage()` / `_surface('trade')` sin arg.

## Lenguaje KHIPU (engine/khipu_lang.js)

`<TICKER|id> DES/GP/SUP/CLI/RISK/NEWS/SIM/FA/THESIS/XRAY [texto]` ·
`PORT VAR` (reporte de riesgo: engine/riskreport.js → POST /api/portfolio/risk_report, core/risk_report.py) / `PORT VEGA` (griegas de opciones: POST /api/portfolio/vega_report, core/options.py, Black-Scholes + IV en vivo) / `PORT PL` · `GRAPH ASOF <fecha>` / `GRAPH DIFF <Nd>` · `FEED [n]` (lo último del grafo) ·
`ALERT <ticker> PX|NRS > <valor>` / `ALERT REGION <región> NEWS` / `ALERT LIST` ·
`COMPARE <A> <B>` (comparador) · `SHOCK <ticker> [sev]` (sim en vivo) ·
`INSIGHTS` / `MATRIX` (pestaña Análisis) ·
`FACTOR LIST` / `FACTOR <id|texto> FIRE` (what-if de crisis de un factor
sistémico; ambigüedad → mayor severity_crisis + alternativas). Acciones
nuevas en command_center: xray, compare, insights, livesim.

## ScenarioBuilder / categorías

- `ScenarioBuilder.PRESETS` (objeto, no array): taiwan_conflict,
  china_chip_ban_total, hbm_shortage_2027, openai_ipo_impact, starshield_reveal.
- 40 categorías: CATS + CATS_NEW merged con Object.assign. CSS vars `--c-{cat}`.

## Reglas de despliegue — NO SALTARSE

1. **Bump del SW cache en CADA cambio de JS/HTML**: `sw.js` línea 6
   (`khipu-finance-vN` → vN+1). Sin esto los usuarios ven código viejo
   ("no veo los cambios" → pedir incógnito / Ctrl+Shift+R). Archivo JS nuevo →
   añadirlo también al array SHELL de sw.js.
2. Paneles de pestaña DENTRO de `<div class="app">` (cierra en
   `<!-- /.app -->`) — fuera quedan invisibles (bug real que ya pasó).
3. Flujo git: desarrollar en `claude/friendly-curie-moauj9` → commit →
   `git checkout main && git merge --ff-only` → push AMBAS ramas (con
   retry/backoff) → volver a la rama.
4. Verificar antes de commit: `node --check` en cada .js tocado;
   `py_compile` de los .py tocados; `node --check` de cada engine/app_*.js y los 4
   bloques inline que quedan en app.html con `new vm.Script()` (tests/test_app_split.py lo hace); `pytest tests/ -q` (~1.800 tests; los de ontología se
   auto-saltan sin DATABASE_URL). En la PC de Fabrizio (Windows) hay entorno
   completo instalado (2026-07): Python 3.11
   (`C:\Users\Dell\AppData\Local\Programs\Python\Python311\python.exe`) y
   PostgreSQL 16 local — correr TODO con:
   `DATABASE_URL=postgresql://postgres:devpass@localhost:5432/khipus_test pytest tests/ -q`

## Variables de entorno

```
SECRET_KEY, FINNHUB_KEY, ANTHROPIC_KEY, GEMINI_KEY, NVIDIA_KEY, AI_ORDER (solo nivel rápido; mejor borrarla), AI_ORDER_FAST, AI_ORDER_DEEP,
AI_MODEL_FAST, AI_MODEL_DEEP (AI_MODEL ya no existe),
ELEVENLABS_KEY, ELEVENLABS_AGENT_ID, ELEVENLABS_ALLOW_OVERRIDE,
AV_KEY, FMP_KEY, MARKETSTACK_KEY, ALPACA_KEY/SECRET/BASE,
TRADE_PIN            ← SIN esto el trading queda deshabilitado (X-Trade-Pin)
KHIPU_ADMIN_SECRET   ← emite claves /v1 de tiers de pago (X-Admin-Secret)
DATABASE_URL                              ← Ontología (Postgres en Railway)
RESEARCH_DAILY_BUDGET_USD, RESEARCH_AUTO_EVENTS, RESEARCH_MODEL_DEFAULT  ← Phase 2
RESEARCH_ANOMALY_PCT (8), RESEARCH_ANOMALY_MAX (3)  ← movimientos anómalos → investigación auto
RESEARCH_EARNINGS_MAX (5)  ← resultados trimestrales (Finnhub, requiere FINNHUB_KEY) → investigación auto
RESEARCH_OUTCOME_BAND (0.02), RESEARCH_CALIBRATION_K (10), COMMITTEE_MAX_CONCURRENT  ← Phase 3 (COMMITTEE_MEMO_TTL_HOURS ya no: vive en policy.committee)
BROKERAGE_ENC_KEY (Fernet; OBLIGATORIA para guardar llaves de clientes), BROKERAGE_TRADING_ENABLED (on),
BROKERAGE_LIVE_ENABLED (off), BROKERAGE_AUTO_APPROVE_PAPER (off), BROKERAGE_APPROVAL_TTL_MIN,
ALPACA_OAUTH_CLIENT_ID / ALPACA_OAUTH_CLIENT_SECRET / ALPACA_OAUTH_REDIRECT_URI  ← corretaje multi-cliente
MCP_ENABLED, MCP_TRADING_ENABLED, MCP_OAUTH_ENABLED, MCP_PUBLIC_URL, MCP_ALLOWED_ORIGINS/HOSTS  ← MCP
WORLD_GDELT_QUERY_CONFLICT / _UNREST / _TRADE, WORLD_GDELT_GEO_URL  ← World Monitor (ajustar sin tocar código)
FINNHUB_WS_KEY (clave Finnhub separada para el navegador), GUNICORN_THREADS (12), GUNICORN_MAX_REQUESTS (0 — dejar en 0),
AI_MAX_CONCURRENCY (4), AI_INTERACTIVE_RESERVE (1), AI_CLAUDE_TIMEOUT_S, DB_POOL_SIZE/DB_MAX_OVERFLOW (10/10),
DB_STATEMENT_TIMEOUT_MS, MATRIX_HEAVY_CONCURRENCY (1), REMIGRATE_ON_BOOT=<nombre de la base>  ← estructura
GEMINI_MODEL (gemini-3.8-flash), GEMINI_FALLBACK_MODEL (gemini-3.5-flash,gemini-3.1-pro)  ← Gemini
TYPESAFE_API_KEY (Jev), TYPESAFE_MODEL (jev-latest), DECIDE_SHADOW (on), DECIDE_CONTROL (vacío; 'chat_gate,…' o 'all'), DECIDE_TIMEOUT_S (6)  ← decisiones Jev
WORLD_SOURCE_DOWN_AFTER (3), WORLD_SOURCE_DOWN_TTL (3600)  ← W1: fuente con 404/403 seguidos en pausa 1 h
LOG_JSON (off)  ← O2: logs JSON con job_id/agente/proveedor/costo/latencia
KHIPU_MCP_TOKEN (secreto de GitHub Actions, NO de Railway)  ← O1: humo del MCP tras cada push (scope read)
AI_CIRCUIT_CREDIT_S (3600) / AI_CIRCUIT_AUTH_S (1800) / AI_CIRCUIT_MODEL_S (1800)  ← R1: pausa del proveedor tras error definitivo
AI_TRANSIENT_RETRIES (3), AI_TRANSIENT_BASE_S (1.5), AI_TRANSIENT_CAP_S (8)  ← R2: reintentos 429/5xx con backoff+jitter
RESEARCH_BUSY_RETRIES (4)  ← R2: esperas ante "IA ocupada" (3/6/12/24 s) antes de fallar el agente
RESEARCH_PARALLEL (2; nunca más que los cupos de fondo), RESEARCH_JOB_CONCURRENCY (2), RESEARCH_STALE_MIN (30), RESEARCH_RESUME_MAX (3)  ← R3/R5: cola de investigación
KHIPU_SCHEDULER (on; off en tests)  ← R5: reloj del servidor (core/scheduler.py) para lo diario
HOTVIEWS (on), HOT_WAIT_S (2), HOTVIEWS_COALESCE_S (1), HOTVIEWS_LISTEN (on)  ← vistas rápidas (core/hotviews)
PRICES_EOD (on), PRICES_REQ_INTERVAL_S (0.6)  ← historia de precios (core/prices_store: carga diaria tras las 22:00 UTC; el relleno de 5 años SOLO con PIN)
GOV_RELEASE (vacío = el vigente de la base), <ARTEFACTO>=<semver> p. ej. KERNEL_PARAMS  ← SOLO eligen un release aprobado (D2)
KHIPU_GATES (on; 'off' = emergencia: apaga las puertas SHACL en sombra)
── G5-14 (lote I4, 2026-10-13): TODA variable que el código lee está aquí (la bóveda: 0 sin documentar) ──
CLAUDE_KEY / ALPHA_VANTAGE_KEY / GOOGLE_API_KEY / NVIDIA_API_KEY / TYPESAFE_KEY  ← nombres ALTERNATIVOS de ANTHROPIC_KEY / AV_KEY / GEMINI_KEY / NVIDIA_KEY / TYPESAFE_API_KEY
ANTHROPIC_ADMIN_KEY (gasto real de Claude en 💰), AI_PRICES_JSON (precios extra por modelo), AI_DAILY_LIMIT_USD (10), AI_MONTHLY_LIMIT_USD (150), AI_PER_USER_DAILY_USD (0 = sin tope)  ← 💰 Gasto IA (los límites con PIN mandan)
AI_BUSY_WAIT_S (20), AI_CLAUDE_TIMEOUT_DEEP_S (110), GEMINI_HOT_S (180), GEMINI_THINKING (off)  ← IA: espera de cupo, tope del nivel profundo, pausa del modelo saturado, "pensar" en el nivel rápido
DECIDE_ENABLED (on), TYPESAFE_API_URL  ← Jev: apagarlo sin borrar la clave / otra URL
ELEVENLABS_LLM (vacío = el recomendado), BIXBY_AUTOSYNC (1; 0 = no sincronizar el agente de voz al arrancar)  ← voz
CSP_ENABLED (true), CSP_REPORT_ONLY (false)  ← seguridad del navegador (emergencia)
REDIS_URL (opcional: caché compartida), DB_POOL_TIMEOUT_S (10), DB_CONNECT_TIMEOUT_S (5), MATRIX_ENGINE (sparse|dense), MATRIX_BUSY_WAIT_S (3), INSIGHTS_INFLIGHT_WAIT_S (45), LIVE_DEADLINE_S (8)  ← estructura
COMMITTEE_MAX_SEATS, RESEARCH_DEDUPE_MINUTES (30), RESEARCH_HEARTBEAT_STALE_MIN (3), RESEARCH_MAX_AGENTS_PER_JOB (4), INVESTIGADOR_AUTO (off), INVESTIGADOR_AUTO_CUTOFF_HORAS (6), TAVILY_KEY, SEC_USER_AGENT  ← investigación/comité
MCP_RATE_PER_MIN (60), MCP_RESEARCH_PER_HOUR (10), MCP_TRADE_PER_HOUR (30), MCP_MAX_INFLIGHT (3), MCP_MAX_INFLIGHT_TOTAL (5), MCP_PIN_MAX_FAILS (10), MCP_PIN_LOCK_MIN (30), MCP_OAUTH_TTL_HOURS, MCP_STATIC_TOKEN, MCP_TRUSTED_PROXY_HOPS (1)  ← MCP
COINGECKO_KEY, CLOUDFLARE_RADAR_TOKEN, SPACE_LL2_BASE, WORLD_GDELT_EVENTS (on), WORLD_GDELT_BACKFILL (on), WORLD_GDELT_EVENTS_BASE, WORLD_GPR_DAILY_URL, WORLD_GPR_MONTHLY_URL, WORLD_PORTWATCH_URL, WORLD_FEDREG_URL, WORLD_GDACS_URL, WORLD_ADVISORIES_URL  ← fuentes en vivo (URLs: solo si el proveedor se muda)
RAILWAY_GIT_COMMIT_SHA, RAILWAY_PUBLIC_DOMAIN, RAILWAY_ENVIRONMENT, RAILWAY_ENVIRONMENT_NAME, RAILWAY_PROJECT_ID  ← las pone Railway solo (sello del código; URL del MCP; "estamos en producción")
GUNICORN_MAX_REQUESTS_JITTER (0; solo Dockerfile) · OPENAI_KEY: solo un comentario de docker-compose (no se usa) · ANTHROPIC_API_KEY / TAVILY_API_KEY: solo en la lista de secretos que se tapan en los logs
KHIPU_URL, SMOKE_RETRIES, GITHUB_OUTPUT, GITHUB_STEP_SUMMARY  ← SOLO scripts de GitHub Actions (humo del MCP, ancla del libro), no Railway
KH_GUARD_TRACE  ← solo diagnóstico/pruebas de la guardia del libro
(BROKERAGE_APPROVAL_TTL_MIN, RESEARCH_CALIBRATION_K, RESEARCH_OUTCOME_BAND: ya NO cambian números — viven en policy.*; el 🩺 avisa si siguen puestas)
```

## Multi-IA — HÍBRIDA (2026-07-12)

`core.ai._ai_complete(system, prompt, max_tokens, tier='fast')` intenta
los proveedores en cascada según el orden DEL NIVEL (ver abajo; el alias `_claude_complete` y la
variable `AI_MODEL` se borraron en la limpieza 2026-10-11). Dos niveles (el tier cambia el orden de
proveedores y el modelo Claude): `AI_MODEL_FAST` (env, default claude-haiku-4-5) para
comandos/noticias/alertas/radar; `AI_MODEL_DEEP` (env, default
claude-sonnet-5-5) para síntesis de deep research, tesis/veredicto IA, Canvas,
War Room y brief matinal. `/api/ai/analyze` acepta `tier:'deep'` en el body
(el tier forma parte de la cache key). Cliente:
`DataLayer.aiComplete(system, prompt, maxTokens, tier)`.
`_extract_json()` tolera JSON envuelto en prosa/fences (Gemini/NVIDIA).
**Orden por nivel (2026-10-10)**: `AI_ORDER_DEEP` (defecto claude,gemini,nvidia; ignora AI_ORDER) y `AI_ORDER_FAST` >
`AI_ORDER` > gemini,claude,nvidia (`provider_order`, `ai_route_state`). Claude por modelo con `claude_attempts`: Sonnet 5.5
NUNCA thinking disabled ni temperature; Opus 5.5/Fable nunca disabled; un 400 de parámetros reintenta el MISMO modelo.
El 🩺 muestra la ruta REAL por nivel (`/api/diagnostics` → `routing`). Voz: `core/voice_agent.py` es el ÚNICO
cliente REST de ElevenLabs (desde 2026-10-11 también `list_voices`/`adopt_shared_voice`; server.py ya no llama a
api.elevenlabs.io — un test lo vigila). Las instrucciones de la voz (`BIXBY_SYSTEM_PROMPT`) describen Khipus OS
y toman los agentes del registro único.
**Gemini 3+ (2026-10-06, default `gemini-3.8-flash`)**: NO acepta `thinkingBudget` (ni 0 ni "minimal" → 400);
`_complete_gemini_inner` manda `thinkingLevel` low (chat/rápido) o medium (profundo, también investigación JSON) con margen de tokens.
Precio en `core/ai_usage.PRICES` (0,75/3,75 hasta 31-dic-2026; luego 1,5/7,5 → actualizar).
Si Google satura (503/429/5xx) o retira (404) el principal, el mismo pedido va a `GEMINI_FALLBACK_MODEL`
(lista con comas; default gemini-3.5-flash,gemini-3.1-pro; 'off' lo apaga; un respaldo con 404 se salta 6 h y nunca pausa todo Gemini) antes de saltar a NVIDIA;
entre modelos no se reintenta (salta al instante) y los saturados van al final 3 min (`gemini_state()`, salud).
server.py y ontology/agents.py importan de core/ — no redefinir en el server.
**GUARDIÁN DE CIFRAS (2026-09-28, pedido explícito "todo en vivo, los datos
falsos perjudican al inversionista")**: `_ai_complete` añade NUMBERS_RULE al
system y verifica (core/numbers.py) que toda cifra de la respuesta esté en los DATOS del prompt (no en el system ni
en sus ejemplos); si no → 1 reintento con feedback y, si persiste,
la marca "(⚠ cifra no verificada)" en el tramo exacto. BLOQUE 0 (2026-10-12): compara por TIPO (dinero, %, múltiplos,
indicadores) con tolerancia por la precisión mostrada (precio ≤0,5 %), entiende "233,95 USD", "dólares", €/£/¥/NT$/S/
y separadores es/en, respeta el signo, exime fechas/años/condicionales y no tiene regex cuadráticas (50k dígitos
0,05 s). La simulación por agentes solo revisa dinero. Las cifras DERIVADAS (sumas, distancia al máximo) se marcan:
la IA debe copiar, no calcular. `_ai_complete_raw` = sin guardián (solo
lo usa el guardián). research/ usa check_numbers (rechazo estricto). Para que
la IA dé cifras correctas, `core/live_facts.py` anexa a TODO prompt un
bloque "DATOS EN VIVO" (capitalización+precio del perfil en vivo; privadas:
última valuación VERIFICADA con fecha) de las empresas mencionadas (máx 4,
6 s, nunca rompe la llamada).

## Errores comunes

- **NO correr `REMIGRATE_ON_BOOT` sobre la base de producción**: es la base
  ORIGINAL (1.294 objetos, reconectada 2026-09-22), con ~216 objetos que el
  repo no puede reconstruir. Es destructiva. Solo para bases nuevas y vacías.
- **ENDURECIMIENTO 2026-09-30 (auditoría estructural, no revertir)**:
  - PIN: `core/pin.py` es el ÚNICO verificador (trade, brokerage, MCP, comité,
    escrituras de ontología con `require_operator`). En el cliente el PIN dura
    12 h (`khipu_trade_pin` + `khipu_trade_pin_exp`): leer SIEMPRE con
    `window._tradePinStored()` / guardar con `_tradePinSave()`; llamadas con
    PIN SIEMPRE por `window._tradeFetch(url, opts, interactive)` (acepta
    `opts.timeout`).
  - Órdenes: `client_order_id` en todo envío (`_tradeOrderId`/`_tradeOrderSettle`/
    `_tradeOrderIsDup`, pendientes en `khipu_coid_pending` 24 h); el panel ya NO
    simula en silencio si falla (solo con trading_disabled/broker_not_configured).
  - Enlaces externos: `window.safeUrl(u)` (solo http/https, escapado) + guard de
    clic que bloquea javascript:/vbscript:/data:. `esc()` escapa `'`.
  - Service worker: NUNCA cachea /api, /v1, /mcp, /oauth, /.well-known (offline
    → JSON 503 {offline:true}); estático solo si res.ok && basic; navegación con
    10 s de límite → shell guardado con `window.__KHIPU_STALE_SHELL=1`; la
    franja roja de "servidor no disponible" vive en el PRIMER bloque inline.
    `const CACHE` debe quedar en los primeros 2048 caracteres de sw.js
    (server._sw_version los lee para el ?v=N).
  - `window.khJSON(r)` valida que la respuesta sea JSON; `window.LANG` ahora es
    un getter (antes los módulos engine/* leían undefined).
  - Server: errores JSON en /api; `@cache.cached` no guarda errores (fallbacks
    60 s); IA con timeout y semáforo (AI_MAX_CONCURRENCY 4, reserva interactiva
    1); DB con pool/statement timeout; matrix con topes y semáforo pesado.
  - `REMIGRATE_ON_BOOT` ahora debe ser EXACTAMENTE el nombre de la base (una
    vez; `<nombre>:2` para repetir) y NUNCA borra tablas broker_*/mcp_*/research_*.
  - requirements + `constraints.txt` (versiones exactas) — no quitar.
- **Mapa principal**: la física se asienta SIN dibujar (`settleGraph()`); solo
  el arrastre pinta en vivo (`_liveTick`). No reintroducir `sim.alpha().restart()`
  fuera del drag: son ~11.000 escrituras al DOM por fotograma.

- **Los proveedores de IA RETIRAN modelos.** En sept-2026 Gemini (404) y NVIDIA
  (410) cayeron a la vez por eso, justo cuando Claude se quedó sin saldo: cero
  red de seguridad. El arreglo NUNCA es tocar código — es `GEMINI_MODEL` /
  `NVIDIA_MODEL` en Railway. El 🩺 ya lo dice explícitamente (`_ai_error_hint`).

- **SQLAlchemy 2.1 usa psycopg 3 por defecto** (no instalado) → en sept-2026
  un redeploy la instaló y TODA la ontología dio "No module named 'psycopg'".
  requirements fija `<2.1` y `ontology/db._normalize_url` fuerza `+psycopg2`.
  No quitar ninguna de las dos.

- `switchTab('sim')` → INCORRECTO, es `'simulation'`.
- Olvidar el bump de sw.js → los usuarios ven código viejo.
- Panel de pestaña fuera de `.app` → pantalla negra.
- Usar `/v1/*` para features internas → colisiona con la API monetizada.
- `getCatColorHex()`/`getLinkColorHex()` viven en engine/app_main.js (antes inline en app.html) y son las
  ÚNICAS definiciones: la copia de graph3d.js se borró en Track A Fase 2
  porque pisaba a la de app.html en silencio. No reintroducirla.
- Atributos SVG no resuelven `var(--css)` — usar hex directo.
- rAF se congela en pestañas ocultas — voice.js usa `_defer()` con fallback a
  setTimeout cuando `document.hidden` (no revertir).
- MAX_CONTENT_LENGTH es 1 MB — payloads de contexto grandes (Canvas) lo rozan.

## Nombres y usuario

- App: **Khipus Finance Intelligence** (2026-10-10; antes "Khipus Finance AI", renombrada 2026-08-03 — "Bixby" es marca de
  Samsung y Fabrizio no puede usarla; antes fue "Bixby Finance" y
  originalmente "Khipus AI Finance Inteligence"). Asistente/voz: **Khipu**
  (nombre PROVISIONAL — Fabrizio buscará el definitivo; cuando llegue,
  repetir el sed protegido: blindar primero los identificadores
  Bixby(CC|Cockpit|Level|Orb|Thinking|Voice), que NO se renombraron, y las
  clases CSS/ids 'bixby-*' minúsculas tampoco; el matcher de transcripción en
  voice.js acepta 'khipu:' y 'bixby:'). SOLO se renombra lo VISIBLE;
  identificadores internos NO cambian (caché sw 'khipu-finance-vN',
  localStorage 'khipu_*'/'kh_*', globals Bixby*/KhipuResolve/KhipuLocalCharts/
  KhipuPortfolios/KhipuUniverse2D, window.KHIPU DSL, engine/khipu_lang.js,
  /v1/* monetizada) — cambiarlos rompería estados/caché.
- Usuario (Fabrizio): hispanohablante, no técnico. Explicar en español simple,
  sin jerga; pasos con clics exactos para Railway/etc.; siempre cerrar
  con "qué hacer ahora" concreto. La pestaña ❓ Guía de la app existe para él.
  **Mensajes CORTOS estilo TDAH (pedido 2026-10-13: "los mensajes largos me quitan atención")**: viñetas breves con
  emoji de sección, lo esencial primero, máximo ~10 líneas, sin párrafos largos.
- La interfaz debe tender a SIMPLIFICARSE: antes de añadir un botón/ícono
  nuevo, evaluar fusionarlo con uno existente (pidió esto explícitamente).
- **REGLA BILINGÜE (2026-07-12, pedido explícito)**: TODO texto de UI nuevo
  debe existir en español E inglés, conmutado por el botón de idioma
  (`LANG`/`t()`/`I18N` en engine/app_main.js; módulos engine/* usan su propio dict
  {es,en} leyendo `window.LANG` o `localStorage.eco_lang`). Nunca shippear
  strings solo en un idioma.
- **EXPLICABILIDAD (2026-07-12)**: la app la usan inversionistas NO expertos —
  toda métrica (NRS, VaR, w, chokepoint…) debe tener su "?" que la explique
  en lenguaje simple (engine/explain.js, `window.explainMetric(key)`).
