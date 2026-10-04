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
