# Jev (TypeSafe AI) en Khipus — modelo de DECISIÓN en modo sombra

Jev no escribe: recibe un **estado** + **preguntas tipadas** y devuelve respuestas
que el código usa directo, con probabilidades calibradas y confianza.
`choice` (elige una opción) · `score` (nivel en una rúbrica) · `noul` (¿es verdad?, 0-1).
Muchas preguntas por llamada se evalúan en paralelo → se piden todas las que el
código pueda necesitar y se combinan en código (speculative fan-out).

## Dónde vive
- `core/decide.py` — única puerta (`ask`, `chat_gate_start/finish`, `shadow`, `shadow_report`).
- `core/decide_api.py` — `GET /api/decide/status`, `GET /api/decide/shadow?days=` (PIN de operador).
- Tabla `decision_shadow` (research/models.py) + memoria (sirve sin Postgres).
- 💰 Gasto IA: proveedor `typesafe` (precio por fijar con `AI_PRICES_JSON={"typesafe:jev":[in,out]}`).

## Reglas
1. **Sombra primero** (`DECIDE_SHADOW=on`): Jev decide, el sistema sigue igual, se mide el acuerdo.
2. **Control por función** (`DECIDE_CONTROL=chat_gate,…`): solo cuando el acuerdo medido lo merezca.
3. **Nunca dinero**: ninguna orden ni aprobación pasa por Jev.
4. Sin clave / sin red / error → `None` y todo sigue como hoy.

## Jev AL MANDO del chat (2026-10-06) — `DECIDE_CONTROL=chat_gate`
Jev piensa en paralelo con la pre-consulta (no frena) y `chat_plan()` devuelve la ruta que el chat OBEDECE
(si llega en `DECIDE_WAIT_S`=1,5 s extra y con confianza ≥ `DECIDE_MIN_CONF`=0,6; si no, camino de siempre):
- `local_fact` → ficha de la empresa con datos en vivo **sin IA** (0 tokens); sin ficha → 1 sola consulta.
- `needs_tools` → máx. 2 rondas de herramientas. `offtopic` → 1 llamada. `needs_deep_reasoning` → igual que hoy.
- @agente: `local` (sus datos S# tal cual, sin IA) · `fast` (modelo rápido) · `deep` (modelo profundo).
- Nunca la ruta barata si parece una orden (asks_trade ≥ 0,5) o una pregunta de cartera.
- `out.router = {by:'jev'|'default', route, confidence, …}`; el pie del chat dice "⚡ Jev: sin IA / consulta corta…".
- Se sigue guardando la sombra (decision_shadow) para medir acuerdo y ahorro.

## Usos previstos (en orden)
1. Portero del chat (hecho, sombra): ruta local_fact / needs_tools / needs_deep_reasoning / offtopic + empresa, orden, cartera, urgencia.
2. Selector de nivel de modelo por pedido (investigación, comité, canvas).
3. ¿Vale la pena investigar? (movimientos anómalos / resultados).
4. ¿Esta afirmación tiene respaldo en la evidencia? (noul por claim).
5. Semáforo del comité (score por horizonte vs historial Brier).
6. Vigilante de órdenes (noul "atípica para este cliente" → solo marca).
7. Noticias de cartera: relevancia/urgencia por posición.

## Variables
`TYPESAFE_API_KEY` · `TYPESAFE_MODEL` (jev-latest) · `TYPESAFE_API_URL` · `DECIDE_ENABLED` (on) ·
`DECIDE_SHADOW` (on) · `DECIDE_CONTROL` (vacío; `chat_gate` = Jev manda en el chat) · `DECIDE_TIMEOUT_S` (6) ·
`DECIDE_WAIT_S` (1.5) · `DECIDE_MIN_CONF` (0.6).
