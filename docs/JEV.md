# Jev (TypeSafe AI) en Khipus — modelo de DECISIÓN (manda en el chat por defecto; además en sombra)

Jev no escribe: recibe un **estado** + **preguntas tipadas** y devuelve respuestas
que el código usa directo, con probabilidades calibradas y confianza.
`choice` (elige una opción) · `score` (nivel en una rúbrica) · `noul` (¿es verdad?, 0-1).
Muchas preguntas por llamada se evalúan en paralelo → se piden todas las que el
código pueda necesitar y se combinan en código (speculative fan-out).

## Dónde vive
- `core/decide.py` — única puerta (`ask`, `chat_gate_start/finish`, `shadow`, `shadow_report`).
- `core/decide_api.py` — `GET /api/decide/status`, `GET /api/decide/shadow?days=` (PIN de operador).
- Tabla `decision_shadow` (research/models.py) + memoria (sirve sin Postgres).
- 💰 Gasto IA: proveedor `typesafe` (precio ESTIMADO 0,04 USD/M entrada, salida 0; ajustable con `AI_PRICES_JSON={"typesafe:jev":[in,out]}`).

## Reglas
1. **Sombra siempre** (`DECIDE_SHADOW=on`): cada decisión se compara con lo que hizo el sistema (acuerdo medido).
2. **Control por función** (`DECIDE_CONTROL`): desde 2026-10-10 (Fabrizio pagó TypeSafe), **con clave y
   `DECIDE_CONTROL` sin poner (o vacía) Jev MANDA en el chat** (`chat_gate`). `DECIDE_CONTROL=off` (o `none`/`0`/
   `false`) = solo sombra. Una lista explícita (`chat_gate,news`, `all`) sigue valiendo tal cual.
3. **Nunca dinero**: ninguna orden ni aprobación pasa por Jev; si la pregunta parece una orden (asks_trade ≥ 0,5)
   no se toma la ruta barata.
4. Sin clave / sin red / error / sin respuesta a tiempo / confianza < `DECIDE_MIN_CONF` → `None` y el chat sigue
   por el camino normal.

## Jev AL MANDO del chat (2026-10-06; por defecto desde 2026-10-10) — `chat_gate`
Jev piensa en paralelo con la pre-consulta (no frena) y `chat_plan()` devuelve la ruta que el chat OBEDECE
(si llega en `DECIDE_WAIT_S`=1,5 s extra y con confianza ≥ `DECIDE_MIN_CONF`=0,6; si no, camino de siempre):
- `local_fact` → ficha de la empresa con datos en vivo **sin IA** (0 tokens); sin ficha → 1 sola consulta.
- `needs_tools` → máx. 2 rondas de herramientas. `offtopic` → 1 llamada.
- `needs_deep_reasoning` (2026-10-10) → elegir herramientas sigue en el modelo RÁPIDO, pero la **respuesta final la
  escribe el modelo PROFUNDO** (Claude Sonnet 5.5 primero; `core/khipu_chat._deep_final` y `synthesize(tier='deep')`)
  con todo lo consultado. La respuesta del rápido queda de respaldo: si el profundo no llega a tiempo (techo
  t0+66 s, el cliente corta a los 70 s) o no entrega una respuesta limpia, se usa la del rápido. `out.router.final_tier = 'deep'`.
- @agente: `local` (sus datos S# tal cual, sin IA) · `fast` (modelo rápido) · `deep` (modelo profundo).
- Nunca la ruta barata si parece una orden (asks_trade ≥ 0,5) o una pregunta de cartera.
- `out.router = {by:'jev'|'default', route, confidence, …}`; el pie del chat dice "⚡ Jev: sin IA / consulta corta…".
- Se sigue guardando la sombra (decision_shadow) para medir acuerdo y ahorro.

## Usos previstos (en orden)
1. Portero del chat (hecho; manda por defecto con clave desde 2026-10-10): ruta local_fact / needs_tools / needs_deep_reasoning / offtopic + empresa, orden, cartera, urgencia.
2. Selector de nivel de modelo por pedido (investigación, comité, canvas).
3. ¿Vale la pena investigar? (movimientos anómalos / resultados).
4. ¿Esta afirmación tiene respaldo en la evidencia? (noul por claim).
5. Semáforo del comité (score por horizonte vs historial Brier).
6. Vigilante de órdenes (noul "atípica para este cliente" → solo marca).
7. Noticias de cartera: relevancia/urgencia por posición.

## API de TypeSafe (revisada 2026-10-10)
`POST https://api.typesafe.ai/v1/systemone` · `Authorization: Bearer <TYPESAFE_API_KEY>` · cuerpo
`{state, model: 'jev-latest', questions: {id: {type: choice|score|noul, instructions, criteria?}}}` → respuesta
`{model, answers: {id: {choice|score|noul, probabilities?, confidence?, legend?}}, usage: {input_tokens, output_tokens}}`.
Coincide con lo publicado por terceros (Apidog, LiteLLM pass-through, Netlify AI Gateway; `docs.typesafe.ai/api` no se
pudo abrir desde el entorno de trabajo): mismo endpoint y mismos 3 campos; `jev-latest` ≈ `jev-1.13.0`; estado +
preguntas ≈ 32K tokens máx. (aquí el estado se recorta a 12.000 caracteres); 70-500 ms. Precio reportado por terceros:
~0,04 USD por millón de tokens de entrada, salida gratis → `core/ai_usage.PRICES['typesafe'] = (0.04, 0)` como
ESTIMADO (ajustar con `AI_PRICES_JSON={"typesafe:jev":[in,out]}` al ver la primera factura).

## Variables
`TYPESAFE_API_KEY` · `TYPESAFE_MODEL` (jev-latest) · `TYPESAFE_API_URL` · `DECIDE_ENABLED` (on) ·
`DECIDE_SHADOW` (on) · `DECIDE_CONTROL` (sin poner = `chat_gate` si hay clave; `off` = solo sombra; o una lista) ·
`DECIDE_TIMEOUT_S` (6) · `DECIDE_WAIT_S` (1.5) · `DECIDE_MIN_CONF` (0.6).
