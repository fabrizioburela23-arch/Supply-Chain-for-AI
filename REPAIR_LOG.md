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
