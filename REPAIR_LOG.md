# REPAIR_LOG — Misión de reparación (desde 2026-10-04)

Un registro por arreglo: problema, causa raíz, cambio, cómo verificarlo. El
diagnóstico completo (mapa del sistema, reproducción, plan y decisiones) está en
`docs/REPARACION_DIAGNOSTICO.md`. Regla: cada entrada tiene un test que fallaba
antes del commit y pasa después (`tests/test_repair_*.py`).

---

## P0 · Investigación

### R1 — Corta-circuito por proveedor de IA (sin saldo / clave inválida / modelo retirado)

- **Problema.** Con Anthropic sin saldo, cada agente de investigación y cada paso
  del chat volvía a llamar a Claude (2 modelos candidatos → 2 HTTP fallidos,
  ~1-2 s y un cupo del semáforo) antes de pasar a Gemini. `available()` solo
  miraba si la clave existía. Visto en producción en los runs de Alphabet
  (`d6874bf1…`): "Anthropic credit balance too low" en cada agente.
- **Causa raíz.** No había memoria de errores DEFINITIVOS por proveedor
  (`core/ai.py` `_AI_PROVIDERS[...][0] = lambda: bool(KEY)`;
  `research/llm.py:96-99`).
- **Cambio.** `core/ai.py`: `_CIRCUIT` por proveedor; `_guarded()` envuelve
  `_complete_claude/_gemini/_nvidia`: un error definitivo (regex credit/auth/
  model) abre la pausa (`AI_CIRCUIT_CREDIT_S` 3600 · `AI_CIRCUIT_AUTH_S` 1800 ·
  `AI_CIRCUIT_MODEL_S` 1800), un éxito la cierra, los pings del 🩺 (≤ 4 tokens)
  la saltan y la cierran si el proveedor responde. 429/5xx/timeout NUNCA la abren.
  `provider_available(name)`, `circuit_open(name)`, `ai_circuit_state()`,
  `observe_diag()`. La cascada `_ai_complete_raw` salta proveedores en pausa sin
  tocar la red (y lo dice en el error). `research/llm.py` `CoreProvider.available()`
  usa `provider_available`. `server.py` 🩺: tarjeta del proveedor con `circuit`
  y "EN PAUSA hasta HH:MM UTC: motivo". `tests/conftest.py` limpia el estado
  entre tests.
- **Verificar.** `pytest tests/test_repair_research.py -k r1` (6 tests: fallaban
  con `AttributeError: _CIRCUIT`). En producción: 🩺 Sistema → IA muestra
  "EN PAUSA" en Claude mientras no haya saldo; `/api/diagnostics?fresh=1` lo
  reactiva solo cuando vuelve a responder.
- **Rollback.** Revertir el commit; no toca datos.

### R2 — "IA ocupada" espera y reintenta el mismo proveedor; 429/5xx con backoff + jitter

- **Problema.** Los agentes `news` y `technical` del job de TSMC (`2ac4552d…`)
  tardaron 70,4 s y 70,5 s y fallaron con "IA ocupada" en claude, gemini y
  nvidia: cada agente probaba los 3 proveedores esperando 20 s de cupo en cada
  uno (3 × AI_BUSY_WAIT_S) y perdía el resultado. Un 503 pasajero de Gemini o un
  429 de NVIDIA tumbaban al agente a la primera (solo Claude tenía 1 reintento).
- **Causa raíz.** `research/llm.py` trataba `AIBusyError` (escasez GLOBAL de
  cupos del semáforo) como fallo del proveedor y saltaba al siguiente;
  `core/ai.py` no reintentaba HTTP pasajeros en Gemini/NVIDIA.
- **Cambio.** `research/llm.py`: `RoutedProvider._with_busy_retry` espera 3/6/12/24 s
  ±30 % (`RESEARCH_BUSY_RETRIES`, default 4) y reintenta el MISMO proveedor;
  agotado → `LLMError('IA ocupada tras N esperas…')` sin probar el siguiente;
  `meta['busy_retries']`. `core/ai.py`: `_retry_transient` (hasta
  `AI_TRANSIENT_RETRIES`=3 intentos, base 1,5 s ×2 con tope 8 s, jitter ±30 %) para
  HTTP 408/409/429/5xx/529 y red caída en Claude, Gemini y NVIDIA; nunca para
  400/401/403/404/410 ni timeouts de lectura. `CLAUDE_RETRY_SLEEP_S` desaparece.
- **Verificar.** `pytest tests/test_repair_research.py -k r2` (5 tests; antes:
  B.calls tenía 1 llamada / 'Gemini HTTP 503' a la primera).
- **Rollback.** Revertir el commit; no toca datos.

### R3 — Cola de investigación: límite global de agentes + cola FIFO de jobs + recuperación tras reinicio

- **Problema.** Cada job abría su propio hilo (sin tope) y su propio pool de 3
  agentes: 5 investigaciones a la vez = 15 agentes peleando por 3 cupos de IA de
  fondo → "IA ocupada" en cadena (TSMC `2ac4552d…`). Un job en espera retenía
  una sesión de base y un hilo. Tras un deploy, los jobs `queued`/`running`
  quedaban huérfanos para siempre.
- **Causa raíz.** `research/runner.py` `execute_job_async` = `threading.Thread`
  por job; `_execute_job` creaba `ThreadPoolExecutor(RESEARCH_PARALLEL=3)` por job.
  Nada serializaba jobs entre sí ni frente al comité.
- **Cambio.** `research/runner.py`: pool de agentes COMPARTIDO (`_AGENT_POOL`,
  `RESEARCH_PARALLEL` default 2, nunca más que los cupos de fondo del semáforo);
  cola FIFO de jobs (`_Q`) atendida por `RESEARCH_JOB_CONCURRENCY` (2) hilos
  demonio; `research_queue_state()` y `queue_position(job_id)`; `_recover_orphans()`
  al primer arranque: `queued` de las últimas 24 h vuelven a la cola, `running`
  más viejos que `RESEARCH_STALE_MIN` (30) → `failed` "interrumpida (reinicio del
  servidor)" junto con sus runs. `/api/research/jobs/<id>` y MCP `get_research_job`
  añaden `queue_position`, `queue_length`, `jobs_running` (solo campos nuevos).
  El comité (`_auto_research`, síncrono) usa el mismo pool: ya no compite.
- **Verificar.** `DATABASE_URL=… pytest tests/test_repair_research.py -k r3`
  (3 tests; antes: `AttributeError: _AGENT_POOL`, máximo simultáneo 2-4).
- **Rollback.** Revertir el commit; no toca datos (los jobs huérfanos marcados
  `failed` ya estaban muertos).

### R4 — Estado honesto `partial`, cobertura visible y "completar solo lo que falta"

- **Problema.** TSMC (`2ac4552d…`) quedó `done` con Noticias y Técnico caídos y su
  síntesis (6 positivas / 1 riesgo) se presentaba como completa en la app y en el
  MCP. El dedupe reutilizaba ese job 30 min y nadie podía completarlo.
- **Causa raíz.** `research/runner.py:431` decidía el estado con un booleano
  (≥1 agente ok → `done`); la cobertura vivía en `agent_runs` y ni la síntesis, ni
  `/api/research/entity`, ni `get_research` la leían.
- **Cambio.** `research/runner.py`: `coverage_of(runs, requested)` (puro) →
  {done, failed(+hint es/en), skipped, not_applicable ("sin evidencia": empresas
  privadas sin noticias/precio), running, missing, complete, note_es/en};
  `job.synthesis['coverage']`; estado `partial` (con `error` "parcial: faltan X")
  cuando falta algún analista pero hubo resultados. `create_job(..., only_missing)`:
  un pedido igual tras un `partial` crea un job SOLO con los analistas que faltan
  (`trigger.completes`); `only_missing=True` lo fuerza fuera de la ventana.
  `research/api.py`: `coverage` en `/jobs/<id>` (en vivo mientras corre) y en
  `/entity/<id>.last_job`; POST `/jobs` acepta `only_missing`. MCP: `get_research.
  last_job.coverage` + `hint`, `get_research_job.coverage` + `next` accionable,
  `run_research(only_missing)` (parámetro opcional; nombres y campos existentes
  intactos). `engine/research.js`: franja ⚠ "Cobertura parcial… faltan …" con
  botón "↻ Completar lo que falta", el sondeo termina también en `partial`,
  posición en cola visible; `research/errors.py` explica "IA ocupada". sw v199.
- **Verificar.** `DATABASE_URL=… pytest tests/test_repair_research.py -k r4`
  (4 tests; antes: `ImportError: coverage_of`, status `done` con agentes caídos).
- **Rollback.** Revertir el commit. Los jobs ya guardados conservan su estado;
  un `partial` nuevo no rompe clientes que solo esperaban `done` (lo tratan como
  "no terminado" → siguen sondeando: por eso la UI y el MCP se actualizan aquí).

### R5 — Presupuesto agotado → el pedido se difiere y se reanuda solo; costo honesto; reloj del servidor

- **Problema.** Con el tope diario (USD 2) alcanzado, cada agente quedaba
  `skipped` y el job `failed`; nadie lo reanudaba y el MCP respondía con error.
  Las corridas fallidas costaban $0 para el tope aunque gastaron tokens, y
  research tenía su propia tabla de precios (claude-sonnet 3/15 vs 2/10 en 💰).
  Lo "diario" dependía de que alguien abriera el mapa.
- **Causa raíz.** `runner._prepare_run` evaluaba el tope por agente con una sola
  salida (`skipped`); no había estado diferido ni reanudador ni reloj.
- **Cambio.** `research/runner.py`: `budget_exhausted`, `defer_job` (estado
  `deferred`, `trigger.resume_after` = 00:05 UTC del día siguiente, sin runs),
  chequeo ÚNICO al inicio de `_execute_job`, `resume_deferred` (solo pedidos de
  personas user/mcp/comité, máx. `RESEARCH_RESUME_MAX`=3 por pasada y solo con
  presupuesto; los de eventos automáticos se descartan con motivo) y
  `resume_deferred_job` (tarea periódica). Dedupe: `deferred` se reutiliza
  ("ya está en cola para mañana"). `core/scheduler.py` (nuevo): hilo demonio con
  `register/tick/state`, arranca en `server.py` (`KHIPU_SCHEDULER=off` lo apaga;
  los tests lo apagan en conftest); tarea `research_resume_deferred` cada 10 min.
  `research/llm.py`: `LLMError.meta` con los tokens gastados antes de fallar y
  `RoutedProvider.spent`; `runner._finish_run` registra tokens y `est_cost_usd`
  en runs fallidos; `estimate_cost` usa `core.ai_usage.cost_of` (UNA tabla).
  `/api/research/jobs` POST y MCP `run_research` devuelven `status: deferred` +
  `resume_after` (ya no `budget_exhausted` salvo con tope 0); `get_research_job.
  next` lo explica. `engine/research.js`: mensaje claro. sw v200.
- **Verificar.** `DATABASE_URL=… pytest tests/test_repair_research.py -k r5`
  (5 tests) + `tests/test_research.py::test_presupuesto_diario_difiere_el_job` +
  `tests/test_mcp.py::test_run_research_budget_and_job` (actualizados: antes
  fijaban `skipped`/`budget_exhausted`).
- **Rollback.** Revertir el commit; los jobs `deferred` existentes quedarían en
  ese estado (no se ejecutan): marcar `failed` a mano si se revierte.

### R6 — Salud del pipeline en una sola foto (API, /api/health, 🩺 y MCP)

- **Problema.** No había un lugar que dijera "¿puedo investigar ahora?":
  `/api/health` solo decía qué claves existen; el 🩺 hace pings (gastan llamadas)
  pero no muestra pausas, cupos, cola ni presupuesto; una IA externa llamaba
  `run_research` y recién ~70 s por agente después descubría la cadena caída.
- **Cambio.** `research/health.py` (nuevo): `research_health()` sin red ni IA
  (caché 5 s) → proveedores (clave + pausa del corta-circuito), cupos del
  semáforo en uso, cola (jobs/agentes, conteos en base), presupuesto research
  (gastado/tope/agotado) y límites de 💰, reloj del servidor (tareas, última
  corrida, errores), última evaluación de predicciones, últimos 10 errores de
  proveedor REDACTADOS (`core.ai.last_errors()`), `hint_es/en` en lenguaje
  simple y `ok`. `GET /api/research/health` (`?fresh=1`), bloque `research` en
  `/api/health`, tarjeta "investigacion" en `/api/diagnostics` (🩺) y herramienta
  MCP `get_research_health` (scope read; herramienta NUEVA, las existentes no
  cambian).
- **Verificar.** `pytest tests/test_repair_research.py -k r6` (3 tests; antes 404
  y herramienta inexistente). En producción: `/api/research/health`.
- **Rollback.** Revertir el commit; no toca datos.

### R7 — Correcciones de la revisión adversarial de R1-R6 (lentes "cola" e "IA")

- **Hallazgos aceptados.** (1) La recuperación de huérfanos corría una sola vez,
  perezosa, e ignoraba los `running` de menos de 30 min: tras un deploy un job
  recién interrumpido quedaba `running` para siempre. (2) Sin reclamo atómico, dos
  ejecutores (cola, Pizarra, comité, recuperación) podían correr el mismo job.
  (3) Una excepción a mitad del job dejaba sus runs `running`. (4) El mismo pedido
  diferido varias veces se reanudaba varias veces; los pedidos de la Pizarra
  (`kind='board'`, clic humano) se descartaban como "evento automático". (5) En
  Claude el corta-circuito se decidía por el ÚLTIMO modelo candidato: Sonnet
  saturado (529) + haiku retirado (404) abría la pausa de todo el proveedor. (6) Una
  clave de Gemini inválida llega como 400 INVALID_ARGUMENT con `reason:
  API_KEY_INVALID` en `details` y nunca abría el circuito. (7) Un límite de 💰
  Gasto IA se trataba como fallo del proveedor y la cascada seguía gastando en el
  siguiente. (8) El chat de Khipu corre sus llamadas de IA en un pool sin contexto
  de petición → contaba como FONDO y recibía "IA ocupada" con el cupo del usuario
  libre.
- **Cambios.** `research/runner.py`: `claim_job` (UPDATE atómico queued→running)
  usado por la cola y por `_execute_job` (un job que ya no está `queued` no se
  re-ejecuta); `_run_job_id` cierra los runs al fallar; `_recover_orphans(boot=)`
  (al arrancar TODO `running` es huérfano; después los > RESEARCH_STALE_MIN que no
  corren en este proceso) como tarea periódica `research_recover_orphans` (cada
  10 min, primera pasada al arrancar); `resume_deferred` descarta duplicados por
  `dedupe_key`; `_HUMAN_KINDS` + 'board'; `create_job` reutiliza sub-jobs
  diferidos. `core/ai.py`: Claude → si algún modelo falló por sobrecarga pasajera
  el error final no es definitivo (no abre circuito) y el código HTTP va explícito;
  Gemini → el `reason` simbólico de `details` entra en el mensaje (API_KEY_INVALID
  → pausa 'auth'). `research/llm.py`: `AIBudgetError` (diario/mensual/función)
  corta la cascada (solo 'provider' desactivado pasa al siguiente). `core/
  khipu_chat.py`: `_ai_interactive` (ai_background(False)) en las llamadas del chat.
- **Descartados / conocidos.** El debate del comité (3 hilos) y las contradicciones
  semánticas no pasan por el pool de agentes: el semáforo de IA (cupos de fondo)
  sigue acotándolos — se deja documentado. "IA ocupada" en el 2.º intento de un
  structured_generate repite el 1.º (raro; tokens ya contados por R5).
- **Verificar.** `pytest tests/test_repair_research.py -k r7` (7 tests).

### R8 — Contratos y consumidores (lente "contratos" de la revisión adversarial)

- **Hallazgos aceptados.** (1) La Pizarra del comité sondeaba hasta 20 min cuando un
  job terminaba `partial`/`deferred`. (2) `only_missing` sobre un job COMPLETO de
  cualquier antigüedad lo reutilizaba y la UI anunciaba "N conclusiones nuevas".
  (3) Los pedidos de la Pizarra corrían en un hilo propio (fuera de la cola) y,
  diferidos, se descartaban como eventos automáticos. (4) Un job `deferred`/`failed`
  se mostraba como "Cobertura parcial: 0 de 4" con botón "Completar" y el MCP
  aconsejaba tratarlo como parcial. (5) Con `RESEARCH_DAILY_BUDGET_USD=0` la API
  web prometía "se reanuda mañana" para siempre. (6) `docs/MCP.md` no reflejaba
  los estados nuevos. (7) El chat de Khipu no conocía `get_research_health`.
- **Cambios.** `runner.create_job(only_missing)`: si no falta nadie → reutiliza
  SOLO si el job completo es reciente y lo marca (`nothing_missing`), si es viejo
  investiga de nuevo; `defer_job` con tope 0 no promete reanudación. `research/
  api.py`: 503 `research_off` con tope 0; `coverage` solo para running/done/partial;
  `nothing_missing`/`created_at` en la respuesta. `research/committee_api.py`
  (Pizarra): 503 con tope 0, difiere sin presupuesto, encola por la cola FIFO
  (visible en salud) en vez de un hilo propio. `mcp_server/tools.py`: `hint`/`next`
  por estado (`_deferred_next`: humano → se reanuda; evento → se descartará),
  `run_research` honesto con `nothing_missing`/`created_at`/reutilizado.
  `engine/research.js`: franja de cobertura solo en `partial`, aviso propio para
  `deferred`, mensajes para "nada que completar"/"ya hay una reciente".
  `engine/committee.js`: la Pizarra termina el sondeo en partial/deferred y lo
  explica. `core/khipu_chat.py`: `get_research_health` en el catálogo + receta.
  `docs/MCP.md` actualizado.
- **Verificar.** `pytest tests/test_repair_research.py -k r8` (5 tests).
---

## P0 · Comité

### C6 — "No validado": etiqueta + tamaño a la mitad mientras ningún analista tenga historial suficiente

- **Problema.** Memo Nvidia `2122eac6…`: 9 conclusiones con fiabilidad 0.5 (= sin
  historial), BUY con 5,30 % del patrimonio y ninguna marca de que nada estaba
  validado. Con fiabilidad 0.5 el peso es la confianza completa (`w = cal·rel/0.5`).
- **Causa raíz.** `research/committee.py`: ni `decide` ni `compute_sizing` miraban
  el historial; MIN_N (5) solo viajaba en la calibración.
- **Cambio.** `validation_status(agent_types, table)` → validated / partial /
  unvalidated (+ `agents{n,hits,sufficient}`, `label_es/en`, `effect_es/en`);
  `compute_sizing(..., validated=True)`: con `validated=False` el presupuesto de
  riesgo se multiplica por `UNVALIDATED_FACTOR` (0.5) → peso objetivo a la mitad,
  `capped_by='unvalidated'`, `unvalidated=True`, paso bilingüe. `_run_committee`
  aplica la validación real a TODOS los tamaños (BUY/ADD/HOLD y rebajas del
  presidente); `memo.track_validation`, `inputs.track_validation` e
  `inputs.track_record[a].sufficient`. UI `engine/committee.js`: insignia
  "⚠ no validado · tamaño ½" / "✓ historial validado" junto a la decisión + nota
  explicativa. Los tests de Phase 3 que fijaban 5 %/$5.000 pasan a 2,5 %/$2.500
  (comportamiento pedido: decisión D1).
- **Verificar.** `pytest tests/test_repair_committee.py -k c6` (3 tests; antes
  `TypeError: validated` / `ImportError: validation_status`).
- **Rollback.** Revertir el commit; los memos nuevos vuelven al tamaño completo.

### C7 — Quórum del comité: fundamental + 3 de 4 analistas, si no "DATOS INSUFICIENTES" (sin deliberar)

- **Problema.** `MIN_CLAIMS = 2` era la única puerta: dos conclusiones de UN solo
  analista bastaban para COMPRAR/EVITAR; con 2 de 4 analistas caídos (TSMC) el
  comité deliberaba igual y el presidente IA redactaba un memo persuasivo.
- **Cambio.** `quorum_check(present)` (`REQUIRED_AGENTS=('fundamental',)`,
  `QUORUM_POOL` = fundamental/news/technical/supply_chain, `MIN_AGENTS=3`) con
  `to_run` (los que faltan) y motivo bilingüe. `_run_committee`: sin quórum y con
  IA disponible encarga SOLO a los que faltan (`_auto_research(..., agents=)`);
  si siguen faltando → `decide(..., quorum=)` devuelve HOLD con motivo "sin quórum…
  → DATOS INSUFICIENTES", `memo.decision_code='INSUFFICIENT_DATA'`, etiqueta
  "MANTENER — DATOS INSUFICIENTES", SIN debate y SIN presidente IA (no gasta ni
  persuade), `memo.quorum` con el detalle. La sala sienta a los analistas que
  faltan como puestos vacíos (`seats[].absent`, `tally.absent`), que la UI pinta en
  gris con "ausente" y un aviso de qué hacer. La decisión sigue siendo un valor del
  vocabulario existente (HOLD) → MCP, corretaje y Pizarra no cambian de contrato.
- **Verificar.** `pytest tests/test_repair_committee.py -k c7` (2 tests; antes
  `ImportError: quorum_check` y BUY con un solo analista).
- **Rollback.** Revertir el commit.

### C8 — Falsadores estructurados y verificables; chequeo diario → conclusión "falsada"

- **Problema.** Los falsadores eran texto libre: nadie los evaluaba, ninguna
  conclusión pasaba nunca a "falsada", y el presidente IA copiaba falsadores de
  conclusiones con OTRA postura (memo Nvidia: "el precio supera el máximo de
  236,54" como falsador de una COMPRA).
- **Cambio.** `research/falsifiers.py` (nuevo): `FalsifierRule{metric: price|
  excess_vs_spy, op: <|>, threshold, by}`, `direction_errors(postura|decisión,
  reglas)` (alcista exige '<', bajista '>'), `check_rules(reglas, fecha_partida,
  serie, spy)` y `apply_falsifiers(session)` (job diario: regla disparada →
  claim `falsified` + `valid_to`, fila `ClaimOutcome('falsifier', miss, final)`
  que cuenta como FALLO del analista, foto de partida `scoreable=False`). Los
  agentes pueden emitir `falsifier_rules` (opcional, máx. 3) validadas en
  `check_refs`; `ResearchClaim.falsifier_rules` (columna JSONB nueva, añadida con
  `ALTER TABLE … IF NOT EXISTS` en `ontology/db._COLUMNAS_TARDIAS`); el
  presidente (`ChairMemo.falsifier_rules`, `chair_checks`, regla 5 del prompt)
  no puede proponer un falsador a favor de la decisión; `CLAIM_STATUSES` +
  'falsified'; `evaluate_due` devuelve `falsified`; `get_memo` añade
  `falsified_claims` (conclusiones del memo ya falsadas) y la UI lo avisa en rojo.
  Los textos libres actuales se conservan (append-only).
- **Verificar.** `pytest tests/test_repair_committee.py -k c8` (5 tests; antes:
  `ImportError: research.falsifiers`, claim nunca 'falsified').
- **Rollback.** Revertir el commit (la columna nueva queda vacía, inocua).

### C9 — Evidencia calculada por Khipus = `computed`; lo interno es UNA referencia; cifras sin fuente externa → tope 0,5

- **Problema.** Claim de Alphabet con una sola evidencia `analysis` "Ratios
  calculados por Khipus" (fiabilidad 0.85, marcada `primary`); la claim de mayor
  peso del BUY de Nvidia (backlog "$500B", 0.726) solo tenía catálogo + grafo
  propios y pasaba el guardián de cifras: la independencia se medía por
  referencia textual y todo lo interno contaba como fuente.
- **Cambio.** `research/context.py`: ratios y pares → `source_type='computed'`,
  `source_kind='computed'`; catálogo y grafo → `source_kind='internal'`.
  `research/confidence.py` **conf-v2**: toda referencia `khipus:*` = una sola
  familia 'khipus'; lo `computed` no suma independencia; `compute_confidence(...,
  statement=)`: cifras de dinero (core.numbers.money_mentions) sin NINGUNA fuente
  http de apoyo → tope `MONEY_NO_EXTERNAL_CAP`=0.5 con la razón en `caps`;
  `external_sources` en los componentes. `runner.persist_result` pasa el texto de
  la claim. UI: etiqueta "calculado por Khipus (no es fuente externa)". Las claims
  conf-v1 existentes NO se recalculan (append-only; `method` lo dice).
  `docs/CLAIM_MODEL.md` actualizado.
- **Verificar.** `pytest tests/test_repair_committee.py -k c9` (4 tests; antes:
  distinct_sources 2 y ≈0.80 sin tope; tipo 'analysis').
- **Rollback.** Revertir el commit; las claims nuevas vuelven a conf-v1.

### C10 — Checkpoints en días hábiles de NYSE y evaluación diaria desde el reloj del servidor

- **Problema.** `n_scored = 0`: la evaluación de predicciones solo corría si
  alguien abría el mapa Y Yahoo devolvía capitalizaciones Y nada fallaba (el día
  se marcaba ANTES de correr, así que un timeout dejaba el día "hecho" sin
  calificar). Los checkpoints eran en días calendario (7/30/90…) y medio/largo
  plazo no tenían señal antes de 30/90 días.
- **Cambio.** `research/outcomes.py`: calendario de NYSE sin dependencias
  (`nyse_holidays`, `is_business_day`, `business_days_after`, Pascua incluida) y
  `CHECKPOINTS` con unidad: INTRADAY 1d · SHORT 5b/20b(final) · MEDIUM 20b/60b/
  180d(final) · LONG 60b/180d/365d(final) (etiquetas `interim_5b`, `final_20b`…;
  las fotos de partida ya guardadas conservan su lista: append-only).
  `core/live_caps._daily_outcomes(now=)`: corre aunque el lote de Yahoo venga
  vacío, marca el día SOLO tras una evaluación exitosa, guarda última corrida /
  error en `_OUT_STATE` (visible en `/api/research/health` → `outcomes`) y no se
  solapa (lock). `server.py` registra `research_outcomes_daily` (cada hora, se
  deduplica por día) en `core/scheduler` junto a `research_resume_deferred`.
  `docs/PHASE3.md` actualizado.
- **Verificar.** `pytest tests/test_repair_committee.py -k c10` (4 tests; antes:
  `ImportError: business_days_after`, el día quedaba marcado tras un fallo, la
  evaluación no corría con lote vacío, el reloj no tenía la tarea).
- **Rollback.** Revertir el commit; las claims nuevas vuelven a 7/30/90 días.

---

## P1 · Motor de riesgo

### D1 — Referencia independiente (numpy), alineación visible, fecha de la bolsa y rótulo "no ajustado"

- **Problema.** Nadie podía demostrar que el emparejamiento con el índice era
  correcto (las correlaciones bajas de LIN–SPY 0,056 sembraban la duda); la
  fecha de la vela se tomaba en UTC (una bolsa que abre antes de medianoche UTC
  quedaba corrida un día) y si Yahoo no entregaba `adjclose` se usaba el cierre
  sin ajustar mientras el reporte decía "ajustados".
- **Cambio.** `tests/test_repair_risk.py`: el motor coincide con numpy (beta,
  correlación, matriz, VaR, CVaR, vol) y la cartera solo-SPY da beta/corr 1,0;
  un índice corrido 1 día hunde la correlación y se VE en `bench_overlap_days`.
  `core/risk_report.py`: `fetch_history` usa `meta.gmtoffset` (fecha del día de la
  bolsa) y guarda `history_meta(sym)` {adjusted, tz}; `compute` publica
  `bench_overlap_days` y `aligned_dates`; `build_report` publica `positions[].
  adjusted/exchange_tz`, `unadjusted_symbols` y un `source` honesto; la UI avisa.
  Conclusión del diagnóstico: el emparejamiento es correcto; las correlaciones
  bajas son las de la serie de Yahoo 2025-10→2026-10 (pendiente contraste externo
  desde la PC de Fabrizio).
- **Verificar.** `pytest tests/test_repair_risk.py -k d1` (5 tests; antes:
  `bench_overlap_days`/`history_meta` inexistentes, fecha corrida en Sídney).

### D2 — Retorno anual compuesto y Sharpe con tasa libre de riesgo real (^IRX)

- **Problema.** `return_ann_pct` componía la media ARITMÉTICA diaria 252 veces
  (MSFT 6,3 % publicado vs ≈0,8 % real compuesto) y el Sharpe usaba rf = 0 con
  esa media: SPY 1,23 publicado vs ≈0,92 con el T-bill del 3,99 % que el propio
  sistema ya baja para opciones. Tres fórmulas distintas en la misma tarjeta.
- **Cambio.** `compute(..., rf, rf_source)`: `return_ann_pct` = compuesto
  (eq^(252/n) − 1), `return_arith_ann_pct` aparte, `sharpe = (compuesto − rf) /
  vol`, `risk_free_pct`, `risk_free_source`, `sharpe_method`. `build_report`
  baja `^IRX` (1 mes) en el mismo pool/caché; sin dato → 0 % y se dice.
  `core/options.risk_free_rate` usa el mismo símbolo. UI: tarjeta "retorno anual
  compuesto X % − tasa libre Y %" y "?" actualizado. **Los Sharpe y retornos BAJAN
  en todas las carteras: hoy estaban inflados** (avisado a Fabrizio).
- **Verificar.** `pytest tests/test_repair_risk.py -k d2` (3 tests).

### D3 — Backtest del VaR fuera de muestra + prueba de Kupiec

- **Problema.** `backtest95` era una tautología: el umbral salía del cuantil 5 %
  de la MISMA muestra → siempre 13 de 250 (SPY, LIN, MSFT, carteras…) y el aviso
  "el VaR subestima" no podía dispararse nunca.
- **Cambio.** `rolling_backtest`: VaR de cada día estimado solo con los W días
  previos (W = max(60, min(125, n//2))), excepciones contadas fuera de muestra,
  `kupiec_pof` (LR y p-valor χ²(1), sin scipy), `verdict` ok/subestima/
  sobreestima, `low_power` si < 100 días; el conteo en muestra queda en
  `in_sample` solo de referencia. UI y "?" explican el método; el aviso ámbar
  sale por veredicto, no por un 1,5× arbitrario. Único consumidor de
  `backtest95`: engine/riskreport.js (el MCP lo pasa tal cual: campos nuevos).
- **Verificar.** `pytest tests/test_repair_risk.py -k d3` (2 tests: Kupiec con
  valores conocidos; iid/tormenta/calma → ok/subestima/sobreestima).
- **Rollback (D1-D3).** Revertir el commit; no toca datos.

---

## Precios en vivo (revisión del commit cc1dfed del agente de la sesión (g))

### R9 — Hallazgos de la lente "precios" de la revisión adversarial

- **Hallazgos aceptados.** (1, ALTA) Londres cotiza en peniques (GBp): `fetch_quote_intl`
  multiplicaba el precio en peniques por el tipo de cambio GBP→USD sin dividir
  por 100 → 12 tickers .L (BAE, Glencore, LSEG…) ×100 en "$". (2) El lote de
  capitalizaciones pisaba la cotización directa fuera de la sesión y la sellaba
  con la hora del lote ("en vivo · hace 1 min" para el cierre de ayer). (3) Un lote
  que no terminaba antes del deadline se guardaba 15 s como lote completo. (4)
  Finnhub se consultaba para los 205 tickers de otras bolsas (quema la cuota de
  60/min; en planes con cobertura internacional etiquetaría JPY como USD). (5)
  El X-Ray rotulaba 'Finnhub · USD' aunque /api/quote respondiera Yahoo en otra
  moneda. (6, baja) Entradas viejas de localStorage con `live:true` alimentaban
  aritmética en spacemonitor.js y graph3d.js.
- **Cambios.** `core/quotes.py`: `_MINOR_UNITS` en `fetch_quote_intl` (÷100 antes
  del FX; `currency` = moneda entera; `minor_unit`); `fetch_quotes_live` no cachea
  lotes truncados (`partial`); el lote Yahoo trae `ts`/`market_state`.
  `core/providers/market.py`: Finnhub devuelve None para tickers con sufijo de
  bolsa (van a Yahoo). `core/live_caps.py`: `price_ts`/`market_state` por nodo.
  `app.html`: `KhipuLiveCaps.apply` solo rellena tickers SIN cotización directa
  y usa la hora real del precio; `MKT.quotes` se sanea al cargar (live no numérico
  se borra). `engine/xray.js`: fuente y moneda reales (+ "convertido de X").
  `engine/spacemonitor.js` y `engine/graph3d.js`: `quotePx`. sw v204.
- **Verificar.** `pytest tests/test_repair_prices.py` (4 tests: antes BA.L ×100,
  Finnhub llamado para BA.L, lote truncado cacheado, sin hora real).

### R10 — Calidad de los tests de la misión (lente "tests")

- **Hallazgos aceptados.** La suite completa tenía 6 tests rotos desde la sesión
  (g) (arreglados en 4156ec8; desde entonces la regla es 0 failed antes de mergear).
  El test FIFO pasaba aunque `execute_job_async` no encolara (la recuperación de
  huérfanos encolaba los jobs del propio test); la posición en cola nunca se
  afirmaba con un valor; el test del pool compartido no detectaba un job muerto;
  una aserción se comparaba consigo misma; el test de salud dependía del entorno;
  el fixture del corta-circuito impedía bisecar el archivo.
- **Cambios.** `tests/test_repair_research.py`: FIFO con hilos arrancados antes,
  `execute_job_async` afirmado True/False, primer job bloqueado con un Event y
  `queue_position` 1/2 verificado en el runner y en `/api/research/jobs/<id>`;
  el test del pool cuenta 4 runs `done`, 2 jobs `done` y 0 excepciones de hilos;
  aserción vacía borrada; `delenv RESEARCH_DAILY_BUDGET_USD`; fixture con
  `raising=False`. Suite completa: 887 passed (fresca, con base).

### R11 — Lente "despliegue" de la revisión adversarial (y restos de "cola")

- **Hallazgos aceptados.** (ALTA) `/api/health` (healthcheck de Railway, monitor
  externo, `Keys.has` de la UI) abría una sesión de Postgres vía el bloque
  `research`: con la base caída tardaba 5-10 s por llamada. (ALTA) Los lotes de
  precios en vivo volvían a encolar tickers que ya estaban en vuelo: backlog sin
  tope y hasta 12 hilos de gunicorn bloqueados 25 s. (media) "Al arrancar, todo
  `running` es huérfano" mataba jobs vivos del contenedor viejo de Railway (los
  dos conviven durante el deploy). (media) Los reintentos pasajeros de Claude se
  repetían por cada modelo candidato reteniendo el cupo del semáforo (hasta ~18 s
  durmiendo) y fabricaban "IA ocupada". (media) El debate del comité (3 hilos)
  ocupaba todos los cupos de fondo. (media) El mismo pedido diferido se acumulaba
  con `force=True` (comité). (media) Una excepción a mitad del job dejaba futuros
  corriendo en el pool.
- **Cambios.** `research/health.py`: `research_health(light=True)` 100 % en
  memoria para `/api/health` (`health_brief`); el endpoint completo recuerda un
  fallo de base 60 s (`_DB_FAIL`) y no vuelve a esperar. `core/quotes.py`:
  registro de futuros en vuelo (`_LIVE_CACHE['inflight']`, callbacks fuera del
  lock), tope `LIVE_BACKLOG_MAX` (400) → `degraded`, `LIVE_DEADLINE_S` 8 s
  (env). `research/runner.py`: latido `trigger.heartbeat_at` (al reclamar y tras
  cada agente); huérfano = `running` sin latido en 3 min (`RESEARCH_HEARTBEAT_STALE_MIN`)
  y no en ejecución aquí (los jobs sin latido, anteriores, por `created_at` >
  30 min); tarea `research_recover_orphans` cada 2 min sin correr al importar;
  futuros cancelados si el job revienta; `job.error` limpio al terminar `done`;
  `defer_job` marca duplicado si ya hay un diferido igual. `core/ai.py`: una
  sobrecarga pasajera de Claude no recorre los otros modelos (pasa a Gemini/
  NVIDIA) y las llamadas interactivas reintentan como máximo 2 veces.
  `research/debate.py`: concurrencia = cupos de fondo − pool de agentes (mín. 1).
  MCP `get_research`: hint de cobertura también para jobs `done` anteriores a R4.
- **Verificar.** `pytest tests/test_repair_research.py -k r11` (5) y
  `tests/test_repair_prices.py -k r11` (1): antes `/api/health` tardaba 5 s con la
  base caída; 3 lotes simultáneos hacían 6 consultas; un job con latido fresco se
  marcaba huérfano; Claude llamaba 3×4 modelos.

## P1 · Grafo y ontología

---

### G1 — Auditoría automática del grafo (`scripts/audit_graph.py`) + trinquete

- **Problema.** Dos verdades del grafo (catálogo `nodes/*.js` → `data/grafo_v0.json`
  y Postgres) sin NINGÚN chequeo de consistencia (C10). El diagnóstico encontró a
  mano entidades duplicadas (C3a), 48 pares con más de un enlace (C3b), enlaces al
  revés (C4), enlaces "no verificados" con peso (C6), taxonomía mezclada (C7), 303
  enlaces sin texto, 526 cifras sin fecha (C8) y Analog Devices ausente (C9). Nada
  impedía que la próxima expansión del catálogo volviera a meter lo mismo.
- **Causa raíz.** No existía un script de auditoría ni una línea base: los
  hallazgos vivían en un documento, no en un test.
- **Cambio.** `scripts/audit_graph.py` (puro: sin red ni base por defecto) lee el
  snapshot y cuenta por categoría — RATCHET: `duplicate_links` (triplas
  source/target/type repetidas), `duplicate_entities` (ids distintos NO cubiertos
  por `node_id_alias` con la misma etiqueta normalizada — sin Inc/Corp/Ltd/Co/
  Company/Group/Trust/Holdings/PLC, espacios ni guiones — o el mismo `mkt`),
  `suspicious_directions` (supply/fab/cloud cuyo `rel` empieza por verbo de consumo
  y nombra al TARGET como proveedor sin nombrar al source; fuentes de servicio no
  industrial — rating, broker inmobiliario, índice, banco, fondo, trader de
  energía; pares A→B y B→A con el MISMO tipo no simétrico, partner es simétrica
  según `ontology/vocabulary.json`), `no_source_text`, `unverified_weighted` ("no
  verificad"/"posible"/"no revisad"/"no confirmad"/"sin confirmar" con w > 1),
  `orphans`, `bad_vocab` (type fuera del vocabulario, cat/sector fuera del
  snapshot); INFORMATIVAS: `undated_figures`, `missing_coverage` (ADI, TXN, MCHP,
  NXPI, ON, STM) y `pairs_multi_type`. Decisión documentada: el texto del catálogo
  suele estar escrito desde el CLIENTE ("TSMC→Achronix fab: Fabrica sus FPGA en
  TSMC" es correcto), así que el verbo de consumo solo cuenta si el target aparece
  como proveedor; quedan 3 reales (Chevron→KinderMorgan, PetroChina→Gazprom,
  CheniereEnergy→KinderMorgan). `--format json|md`, resumen bilingüe ES/EN,
  `--write-baseline` → `data/graph_audit_baseline.json`, salida 1 si una categoría
  ratchet supera la base (`--strict`: si alguna > 0). `--db` (solo con
  DATABASE_URL, transacción READ ONLY) compara links vigentes base vs snapshot
  (faltantes en cada lado, duplicados exactos, % de `valid_from` 2000-01-01 y
  eventos sin `source_id` por canal). Línea base hoy (snapshot 2026-09-29): 0 /
  11 / 59 / 303 / 28 / 25 / 0 · info 556 / 1 / 48.
- **Verificar.** `pytest tests/test_graph_audit.py` (4 tests; antes:
  `ModuleNotFoundError: scripts.audit_graph`): mini-grafo de juguete con un caso
  por categoría + contraejemplos de perspectiva, exit codes y el trinquete sobre el
  snapshot real. `python scripts/audit_graph.py --format md | head -60`.
- **Rollback.** Revertir el commit; no toca datos ni la base.

### G1b — 9 entidades duplicadas sin alias (misma empresa dos veces en el catálogo)

- **Problema.** La auditoría G1 cuenta 11 pares de ids distintos que son la misma
  empresa (mismo `mkt` y/o misma etiqueta) y NO están en `NODE_ID_ALIAS`: Southern
  Company, Kuehne+Nagel, Air Products, Sumitomo Chemical, Iluka, Ucore, Stella
  Chemifa, Mapletree Industrial Trust y ESR Group (+ Kanto Denka, China Northern
  Rare Earth y AlphaSense, fuera de esta tarea). En la app aparecen como dos
  nodos, con sus enlaces repartidos; `SumitomoChemical` quedaba incluso huérfano.
- **Causa raíz.** La misma empresa entró por `nodes/nodes_expand5.js` (ids en
  kebab-case: `air-products`) y por `nodes/nodes_multicapa.js` (CamelCase o con
  espacios: `AirProducts`, `'ESR Group'`); el merge solo fusiona lo que está en la
  tabla de alias y nadie la actualizó (no había auditoría).
- **Cambio.** `nodes/nodes_seed.js` `NODE_ID_ALIAS` (bloque G1b): alias → canónico
  con canónico = el id con MÁS enlaces en `data/grafo_v0.json` (empate → id sin
  espacios / CamelCase, con sufijo de bolsa en `mkt`): SouthernCompany→SouthernCo
  (2 vs 5), Kuehne_Nagel→KuehneNagel (2 vs 5), air-products→AirProducts (2 vs 6),
  SumitomoChemical→sumitomo-chemical (0 vs 3), iluka-resources→IlukaResources
  (2=2), ucore-rare-metals→UcoreRareMetals (2 vs 3), StellaChemifa→stella-chemifa
  (1 vs 2), 'Mapletree Industrial Trust'→MapletreeIndustrialTrust (2=2),
  'ESR Group'→ESR_Group (2=2). `nodes/nodes_multicapa.js`: la etiqueta visible de
  `ESR_Group` pasa de "ESR_Group" a "ESR Group" (el merge conserva la etiqueta del
  nodo que carga primero). Ensayo del merge (misma tubería que
  `scripts/export_graph_v0.js`, sin escribir): 949 → 940 nodos, 2.526 → 2.524
  enlaces, 0 avisos. El snapshot `data/grafo_v0.json` NO se regenera en este commit
  (se regenera al integrar: `node scripts/export_graph_v0.js`); la línea base de G1
  bajará entonces (duplicados 11 → 3, huérfanos 25 → 24) y se vuelve a escribir con
  `--write-baseline`. sw v205 (los nodes/*.js los carga el navegador).
- **Verificar.** `pytest tests/test_graph_audit.py -k g1b` (antes: `'SouthernCompany'
  debería ser alias de 'SouthernCo' (hoy: None)`): lee `NODE_ID_ALIAS` ejecutando
  `nodes/nodes_seed.js` en Node (regex si no hay Node), comprueba las 9 parejas, que
  el canónico exista y no sea alias, que tenga ≥ enlaces, y que con esa tabla la
  auditoría deje de contar los pares. `node --check nodes/nodes_seed.js`.
- **Rollback.** Revertir el commit (y regenerar el snapshot si ya se había
  regenerado); no toca la base — la fusión de los objetos duplicados en Postgres es
  el commit 12 del plan (`ObjectMerged`, append-only).

### G1c — Un id viejo (alias) siempre lleva a la empresa canónica
- **Síntoma (lo destapó la auditoría G1).** `NODE_BY_ID['AWS']`,
  `NODE_BY_ID['SouthernCompany']` y otros 30+ alias no llevaban a ningún nodo:
  `jumpTo` con el id viejo, un hecho temporal o un link escrito con el alias no
  encontraban la empresa (los links sí se resolvían por otro camino).
- **Causa.** `nodes/merge_graph.js::absorbNode` solo mapeaba el alias cuando el
  canónico ya existía; si el nodo alias se cargaba primero, se renombraba y el
  id viejo quedaba huérfano. Los alias que nunca fueron nodo propio (p. ej.
  'AWS') no se mapeaban nunca. En el seed, un alias sin canónico cargado se
  quedaba con su id viejo.
- **Cambios.** `absorbNode` guarda el id original y lo mapea; tras las
  expansiones, todo alias con canónico existente se mapea; el seed renombra al
  canónico. `engine/hypergraph.js` (el único que enumera NODE_BY_ID) filtra las
  claves alias.
- **Verificar.** `pytest tests/test_merge_graph_alias.py`: corre el merge REAL
  en Node; antes fallaba (AWS→Amazon y decenas más sin mapear).

### G2 — La ontología se corrige SIN borrar: dedupe de vínculos, retracción dirigida y fusión de entidades por eventos
- **Síntoma.** El diagnóstico encontró en producción vínculos repetidos (mismo
  par, misma relación, mismo peso: la migración y el bulk import los volvían a
  crear) y tres empresas duplicadas (`Luminar_Lidar`/`Luminar`,
  `Mobileye_Auto`/`Mobileye`, `ButterflyNetwork`/…). No había forma de arreglar
  UNA fila: `LinkRemoved` sin dirección cerraba TODAS las filas del par (y el
  replay `as_of` divergía), y la única "fusión" posible era un UPDATE/DELETE a
  mano, prohibido por la regla 5 (append-only).
- **Causa.** `links` no sabía qué evento creó cada fila; `apply_event` no miraba
  si el `LinkCreated` ya existía vigente; no existía ninguna Acción de fusión.
- **Cambios.** `ontology/models.py` + `ontology/db.py`: columna tardía
  `links.event_id` (nullable: las filas viejas se emparejan al vuelo por
  par/relación/fecha/peso en `_creation_event_for`). `ontology/service.py`:
  un `LinkCreated` idéntico a una fila vigente se REGISTRA (append-only) marcado
  `properties.dedup_of` y es un no-op en tablas y en el replay
  (`allow_duplicate: true` lo desactiva para hechos temporales con otra
  ventana); `LinkRemoved` con `properties.retracts_event_id` cierra SOLO la
  fila de esa creación (también en `_links_active_at`, que ahora expone
  `event_id`). `ontology/actions.py`: `RetractarVinculo{link_id, razon}` y
  `FusionarEntidad{alias_id, canonical_id, razon}` (alias → `retired` +
  `merged_into`, vínculos vigentes retractados y re-creados en el canónico con
  su `valid_from`/peso/propiedades + `merged_from`; alias↔canónico se descarta
  como bucle; `aliases` en el canónico; rastro `ActionExecuted`). Ambas pasan
  por `/api/ontology/actions/<tipo>` con PIN de operador. **Nada se borra**: el
  grafo `as_of` de 2020 sigue mostrando al alias.
- **Verificar.** `DATABASE_URL=… pytest tests/test_repair_ontology.py` (8):
  sin el cambio fallan 6 (segunda fila duplicada, retracción cierra ambas,
  acciones inexistentes). Suites de ontología completas: 58 verdes.
- **Rollback.** Son eventos: revertir una fusión = `FusionarEntidad` al revés
  no existe a propósito (sería otra historia); lo correcto es un
  `ObjectUpdated{retired:false, merged_into:null}` + re-crear los vínculos
  con `allow_duplicate`. La columna `event_id` es inocua si se vuelve al código
  anterior (la ignora).

### G2b — Las correcciones valen para TODO el pasado; un hecho con fecha nunca se toma por duplicado
- **Síntoma (revisión propia de G2).** Con G2 tal cual, retractar un duplicado o
  fusionar `Luminar_Lidar` en `Luminar` dejaba al time-travel mostrando el
  error en fechas pasadas: en 2020 aparecían el alias Y el canónico proveyendo a
  Volvo (doble conteo), y "ayer" seguía el duplicado. Además el dedupe miraba
  solo par/relación/peso: un hecho con ventana propia (p. ej. 2019-2021) o que
  empieza ANTES de la fila vigente se habría marcado como duplicado y perdido.
- **Causa.** La retracción usaba `valid_from = ahora` (semántica de "la relación
  terminó hoy") cuando es una CORRECCIÓN ("esta fila nunca fue cierta").
- **Cambios.** `RetractarVinculo` emite el `LinkRemoved` con `valid_from` = el
  de la creación (retroactivo en tiempo de validez; la hora real queda en
  `recorded_at` y en `properties.retracted_at`): ninguna fecha de `as_of`
  muestra la fila corregida, y la bitácora conserva lo que se creía. El dedupe
  solo aplica si el nuevo `LinkCreated` no trae `valid_to` y la fila vigente ya
  lo cubre (`valid_from` del gemelo ≤ el nuevo).
- **Verificar.** `pytest tests/test_repair_ontology.py` (9): sin el cambio fallan
  3 (ventana deduplicada, duplicado visible ayer, alias visible en 2020).

### G3 — Reconciliación catálogo ↔ base SOLO con eventos: lista para revisar, aplicar por categoría y deshacer
- **Síntoma.** Dos verdades distintas: el mapa y el MCP leen el catálogo
  (limpio desde julio), mientras el motor de shocks, el NRS del servidor y el
  Grafo Temporal leen Postgres, que conserva el grafo PRE-limpieza (empresas
  repetidas como `Mobileye_Auto`/`Mobileye`, vínculos dobles TSMC→Nvidia,
  ~400 flechas al revés X→TSMC). El mismo shock daba resultados distintos según
  la pantalla. La base de producción NO puede re-migrarse (216 objetos únicos).
- **Causa.** La limpieza de Etapa 2 reescribió `nodes/*.js` y el snapshot, pero
  nunca se reprodujo como eventos en Postgres; no existía forma append-only de
  corregir.
- **Cambios.** `ontology/reconcile.py` (lógica) + `scripts/reconcile_v0_to_ontology.py`
  (terminal) + `/api/ontology/reconcile/plan|apply|rollback` + panel 🩺 →
  Diagnóstico → *Grafo: base vs catálogo* (`engine/reconcile.js`, ES/EN, "?").
  El plan (solo lectura) clasifica en: alias, repetidos, direcciones, pesos
  distintos, faltantes y sobrantes; SOLO toca filas vigentes con fecha GENESIS,
  relación del catálogo, sin fuente externa/factor y con extremos del catálogo
  (los hechos con fecha, noticias, factores y objetos propios de la base nunca
  se tocan). Aplicar exige PIN de operador + el nombre EXACTO de la base +
  actor; por defecto solo lo seguro (alias + repetidos); direcciones y demás
  solo si se marcan (decisión D5). Cada corrida usa el canal
  `reconcile_v0:<run_id>`; deshacer emite eventos nuevos
  (`reconcile_v0_rollback:<run_id>`), sigue la cadena si otra corrida re-abrió
  el vínculo, se niega a deshacer dos veces o fuera de orden.
- **Verificar.** `DATABASE_URL=… pytest tests/test_reconcile.py` (5): base
  "vieja" con filas sin event_id → plan exacto por categoría, dry-run sin
  escrituras, `confirm_db` obligatorio, aplicar → 0 diferencias, tablas ==
  replay, fuera-de-alcance intacto, deshacer → estado original exacto, API con
  PIN. Ensayo realista (base migrada desde el snapshot de julio, como
  producción): 56 alias · 31 repetidos · 393 direcciones · 53 pesos · 273
  faltantes · 4 sobrantes → todo aplicado en ~6 s, 0 diferencias, tablas ==
  replay; deshacer ambas corridas → los 1.451 vínculos originales exactos. Una
  base recién migrada desde el catálogo actual → 0 diferencias (sin falsos
  positivos).
- **Producción.** NO se aplicó nada: se espera la revisión de Fabrizio
  (copia de seguridad → *Aplicar lo seguro* → revisar direcciones).
