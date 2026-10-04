# PHASE 3 — Aprendizaje + Comité de inversión (con aprobación humana)

> Estado: **v1 entregada el 30-sep-2026**. Construida encima de Phase 2 (Agent
> Research Swarm, `research/`). Phase 2 **investiga** y nunca dice comprar o
> vender. Phase 3 hace dos cosas nuevas:
>
> 1. **Aprende**: califica cada conclusión de los agentes contra lo que de verdad
>    pasó con el precio, y con eso mide qué tan confiable es cada agente.
> 2. **Decide, como propuesta**: un comité automatizado propone
>    COMPRAR / AUMENTAR / MANTENER / REDUCIR / VENDER / EVITAR con un tamaño
>    calculado. **Un humano aprueba siempre**; para dinero de clientes hay una
>    segunda aprobación en el módulo de corretaje.

## 1. El ciclo de aprendizaje (`research/outcomes.py`)

```
claim escrita ──► foto de partida ──► checkpoints vencen ──► calificación con precios reales
   (Phase 2)      (claim_baselines)      (1×/día)              (claim_outcomes, append-only)
                                                                         │
            confianza calibrada ◄── historial por agente ◄────────────────┘
            (próximas claims y comité)   (track_record, calibration_snapshots)
```

**Foto de partida** — al persistir cada claim (`runner.persist_result`) se guarda
en `claim_baselines`: entidad, ticker si cotiza, fecha de mercado (Nueva York),
precio en vivo y SPY en vivo (solo auditoría), horizonte, confianza calculada y
calibrada vigente, y las fechas de revisión:

| Horizonte    | Checkpoints (b = días HÁBILES NYSE, d = calendario) | Final |
|--------------|-----------------------------------------------------|-------|
| INTRADAY     | 1d                                                  | 1d    |
| SHORT_TERM   | 5b (intermedio), 20b                                | 20b   |
| MEDIUM_TERM  | 20b, 60b (intermedios), 180d                        | 180d  |
| LONG_TERM    | 60b, 180d (intermedios), 365d                       | 365d  |
| STRUCTURAL   | — no se califica (n/a)                              | —     |

(C10, misión de reparación 2026-10-04: antes 7/30 · 30/90/180 · 90/180/365 en
días calendario. Las fotos de partida ya guardadas conservan su lista.)

Las claims anteriores a Phase 3 se completan solas (backfill) en la primera
evaluación: no tienen precio en vivo guardado, pero sí fecha, y eso basta.

**Calificación** (`evaluate_due`, sin IA, solo precios):

* retorno del activo y de SPY entre el **cierre del día de la predicción** y el
  **primer cierre en o después del vencimiento**, ambos de la **misma serie de
  cierres ajustados** (Yahoo, `core.risk_report.fetch_history`) → un split o un
  dividendo no producen un falso −90 %;
* exceso = retorno − retorno SPY; banda = ±2 % (`RESEARCH_OUTCOME_BAND`);
* postura **positiva** → acierto si exceso > +banda · **negativa** → si
  exceso < −banda · **neutral** → si |exceso| ≤ banda · **mixta** o **no
  cotiza** → n/a con motivo;
* idempotente (única por claim + checkpoint), append-only; las claims
  **superadas también se califican** (la predicción se hizo);
* si el proveedor no da precios: queda pendiente; 20 días después del
  vencimiento sin cierre → n/a ("¿suspendida o deslistada?");
* **ventana de precios**: por lote se pide a cada símbolo (y a SPY, que
  comparten todas) la ventana **más antigua** que necesite cualquier checkpoint
  del lote — un final de 365 días nunca queda fuera de la serie por culpa de un
  checkpoint corto procesado antes. Si aun así la serie no llega a la fecha de
  partida, queda **pendiente** (se reintenta) y solo pasa a n/a a los 20 días;
* **nunca con la barra en curso**: si la evaluación corre en un día hábil antes
  de las 16:30 de Nueva York, la barra de HOY se descarta (sería un precio
  intradía, no un cierre);
* el motivo de cada calificación se guarda en **español e inglés** (`reason`,
  `reason_en`); las acciones fuera de EE.UU. se califican **en moneda local**
  (sin ajuste cambiario) y el motivo lo dice.

Se ejecuta **1 vez al día** desde el reloj del servidor (`core/scheduler`, tarea
`research_outcomes_daily`, cada hora hasta que corra bien ese día; también la
dispara el refresco de `core/live_caps`) y bajo pedido con
`POST /api/committee/outcomes/evaluate` (PIN). El día se marca SOLO si la
evaluación terminó bien; la última corrida y su error se ven en
`/api/research/health` (C10).

**Historial y calibración** (`track_record`, `calibrated_confidence`):

* base = checkpoints **finales**; los intermedios se muestran aparte como
  "señal temprana" (no cuentan para la calibración);
* tasa de acierto, **Brier** = promedio de (confianza − resultado)², tramos de
  fiabilidad 0-0.2 … 0.8-1.0 con n, confianza media y acierto real;
* **confianza calibrada** = (aciertos del tramo + k·cruda) / (n del tramo + k),
  k = 10 (`RESEARCH_CALIBRATION_K`) — encogimiento bayesiano: con poca historia
  ≈ la cruda. La UI dice "sin historial suficiente" si el tramo tiene < 5 casos;
* **fiabilidad del agente** = (aciertos + k·0.5)/(n + k) — 0.5 sin historia;
* claims **retiradas** (cifras sin respaldo) no cuentan en el historial;
* foto diaria en `calibration_snapshots` (una fila por agente + global).

La calibrada se guarda en cada claim nueva en
`confidence_components.calibration` (auditable: "qué creía el sistema en ese
momento"); la UI de Investigación muestra la calibración **actual**.

## 2. El comité (`research/committee.py`)

`run_committee(session, entity_id, requested_by, client_id=None, provider=None)`

**Reúne**: claims activas de todos los agentes por horizonte, contradicciones,
historial de cada agente, perfil de mercado en vivo, riesgo de la acción sola
(volatilidad anual, máxima caída, beta vs SPY, VaR — `core.risk_report`) y, si
hay cliente y `brokerage.service` está instalado, su mandato, patrimonio y
posición actual.

**Núcleo cuantitativo (determinista — la IA no lo toca)**:

```
peso_i        = confianza_calibrada_i × (fiabilidad_agente_i ÷ 0.5)
convicción_h  = 100 · Σ peso_i·signo_i / (Σ peso_i + 1) · (1 − ½·cuota_en_contradicción_h)
global        = Σ_h w_h·convicción_h / Σ_h w_h     (w: corto 0.20 · mediano 0.35 · largo 0.35 · estructural 0.10 · intradía 0)
peso_objetivo = min(presupuesto_riesgo / max(vol_anual, 10 %), máx_por_posición)   (defaults 2 % y 10 %)
```

| Decisión | Regla |
|---|---|
| BUY | sin posición y global ≥ +35 (y volatilidad medible) |
| ADD | con posición, global ≥ +35 y posición < 80 % del objetivo |
| HOLD | no alcanza umbrales, < 2 conclusiones, tamaño resultante < US$1 (el motivo dice por qué: sin volatilidad, límite diario agotado, sin poder de compra, en el tope), o —con cliente— cotiza fuera de EE.UU. (Alpaca no la opera) |
| TRIM | global ≤ −20, o posición > 125 % del objetivo (riesgo) |
| SELL | global ≤ −50 (vende todo) |
| AVOID | sin posición y global ≤ −20; no cotiza; o el mandato lo restringe |

Topes del tamaño, en orden: máximo por posición del mandato, lo que ya se tiene,
el poder de compra, y los **límites en US$ del corretaje** — máximo por orden
(`max_order_usd`, p. ej. US$5,000 en perfil moderado) y **lo que queda del
límite diario** (`max_daily_usd` − lo enviado hoy) — para que la
previsualización no salga bloqueada por tamaño. Una **venta** mayor que el
máximo por orden se propone como venta PARCIAL por monto. Vender o reducir por
convicción **no necesita volatilidad** (usa la posición actual); comprar sí.
El redondeo es hacia abajo (nunca pasa un tope). "≈ acciones" solo se muestra si
el precio en vivo está en dólares. Sin cliente se muestra como % y "por cada
$10,000" (ilustrativo).

**Cotizaciones fuera de EE.UU.** (2330.TW, 9984.T, BA.L…: 212 de 578 nodos
cotizados): con cliente, una decisión accionable se rebaja a HOLD ("no se
puede operar en Alpaca"); sin cliente se conserva la vista como referencia.
`approve_memo` además nunca manda un ticker no estadounidense al corretaje.
Las acciones de clase (MOG-A, BRK.B) sí son de EE.UU.: se envían como `MOG.A`.

**Presidente IA**: recibe un paquete numerado (C# conclusiones, X#
contradicciones, D# datos en vivo, R# riesgo, Q# núcleo cuantitativo, M#
mandato) y devuelve un JSON validado con Pydantic (`ChairMemo`): tesis por
horizonte, riesgos, **disenso**, falsadores, fecha de revisión, confianza.
Reglas duras (`chair_checks`): solo refs del paquete; la decisión es la del
núcleo **o HOLD** (con motivo) — nunca otra; fecha de revisión 7–400 días;
agentes del disenso reales; **toda cifra de dinero debe estar en el paquete**
(`core.numbers.check_numbers`). Si falla: se reintenta con el error como
feedback; si sigue fallando, o no hay IA, o se agotó el presupuesto diario →
**memo determinista rotulado "sin IA"**. La ejecución del presidente queda en
`agent_runs` (tipo `committee`: costo, modelo, validación) y cuenta en el
presupuesto diario de IA (`RESEARCH_DAILY_BUDGET_USD`). Ruta de modelo:
`RESEARCH_MODEL_COMMITTEE` (o `RESEARCH_MODEL_DEFAULT`).

Todo memo lleva el aviso: *propuesta de un comité automatizado, requiere
aprobación humana, no es asesoría financiera personalizada*.

## 3. Cómo se controla la decisión (gating)

1. **Memo** `committee_memos`: `running → proposed → approved | rejected →
   executed` (o `failed`), con `audit` (quién, cuándo, qué) y el paquete de
   evidencia completo en `inputs`.
2. **Aprobar/rechazar** exige el PIN de trading (`X-Trade-Pin` == `TRADE_PIN`,
   `hmac.compare_digest`; sin `TRADE_PIN` → 403). Un memo vence a las 72 h
   (`COMMITTEE_MEMO_TTL_HOURS`): con precios viejos no se aprueba. Aprobar,
   rechazar y marcar ejecutado **bloquean la fila** del memo (`SELECT … FOR
   UPDATE`): dos clics simultáneos no crean dos órdenes; la UI además
   deshabilita los botones mientras responde.
3. Aprobar con cliente y decisión accionable → `brokerage.service.preview_order(
   source='committee', proposal_id=<memo>)`:
   * `pending_approval` → memo **aprobado**; la orden **también** exige
     aprobación humana en 👥 Clientes → Aprobaciones antes de ejecutarse;
   * `previewed` (`BROKERAGE_AUTO_APPROVE_PAPER=on` y cliente en **papel**) → la
     aprobación con PIN del memo **es** la aprobación humana: se confirma con
     `confirm_order(source='committee')` y el memo queda `executed`;
   * **bloqueada / rechazada / sin corretaje / ticker extranjero** → el memo
     **sigue `proposed`** (se puede volver a aprobar tras corregir el límite) y
     se devuelven los controles que fallaron (es/en). Nunca "aprobado" sin orden.
   El comité nunca ejecuta órdenes por sí mismo.
4. **Rechazar** un memo aprobado **retira** su orden pendiente
   (`brokerage.service.reject_preview`); si la orden ya se envió, el rechazo se
   niega y el memo pasa a `executed` (la verdad), con el aviso de cancelar o
   vender en Clientes. Si no se puede retirar, el rechazo también se niega.
5. Correr el comité **con** cliente exige PIN (lee su cuenta). Sin PIN, un memo
   con cliente se devuelve **redactado**: sin montos en tamaño, pasos, memo,
   nota de decisión, error ni validación (cubre `$1,234`, `US$`, `USD 1,234`,
   `1.234 USD`, `dólares`), sin `inputs.client/mandate/package`, y la
   auditoría solo con acción/fecha/actor y campos no monetarios. Se conserva
   el modo (`client_mode`: 🧪 papel / 🔴 real) para la insignia.
6. El módulo de corretaje marca el memo ejecutado con
   `research.committee.mark_executed(session, memo_id, order)` (con `SKIP
   LOCKED`: nunca espera un bloqueo, así no hay esperas cruzadas con el
   rechazo). Orden de bloqueos: aprobar memo→orden nueva · rechazar memo→orden ·
   corretaje orden→memo (sin esperar).
7. `POST /run`: `sync` solo con PIN válido (o en tests) — sin eso unos pocos
   pedidos llenarían los 8 hilos del servidor; mismo (entidad, cliente)
   deliberando o propuesto hace < 2 min → se **reutiliza** ese memo (no se gasta
   IA dos veces); como máximo `COMMITTEE_MAX_CONCURRENT` (2) comités a la vez
   → 429. Un `running` de más de 10 min se marca fallido (hilo muerto).

## 4. API — `/api/committee/*` (`research/committee_api.py`)

| Método | Ruta | Notas |
|---|---|---|
| POST | `/run` | `{entity, client_id?, actor, sync?}` → 202 `{memo_id, reused?}` (hilo) · PIN si hay cliente · `sync` solo con PIN · 429 si hay 2 corriendo · 10/h |
| GET | `/memo/<id>` | memo completo; montos del cliente solo con PIN |
| GET | `/entity/<id>` | último memo + historial |
| POST | `/memo/<id>/approve` | PIN · `{actor, note?}` → preview en corretaje · 409 `preview_failed`/`not_tradable`/`brokerage_unavailable` (sigue propuesto) |
| POST | `/memo/<id>/reject` | PIN · `{actor, reason?}` → retira la orden pendiente · 409 `order_sent`/`withdraw_failed` |
| GET | `/track-record[?agent=]` | historial por agente |
| GET | `/calibration` | tabla de calibración + fotos |
| POST | `/outcomes/evaluate` | PIN · califica vencidas ahora |
| GET | `/outcomes/recent` | últimas calificaciones |
| GET | `/clients` | PIN · clientes de `brokerage.service.list_clients` (sin secretos) |

Sin `DATABASE_URL` → 503. Sin IA → memo determinista. Todo error trae
`error` (es) y `error_en` (en).

## 5. UI

* `engine/committee.js` — `window.KhipuCommittee.open(entityId?)`: pestañas
  **Comité** (correr, memo con decisión, convicción por horizonte, tamaño con la
  cuenta, riesgo medido, tesis, riesgos, disenso, falsadores, aprobar/rechazar
  con PIN, orden preparada), **Historial** (tabla por agente, Brier,
  fiabilidad, curva de calibración con Chart.js, últimas calificaciones) y
  **Cómo aprende**. Bilingüe (los textos del servidor llegan con `*_en`); "?"
  registrados: `conviction`, `brier`, `calibration`, `hit_rate`,
  `position_sizing`, `committee_decision`, `reliability`, `early_signal`,
  `committee_confidence`. Se registran al cargar el DOM (committee.js carga
  antes que explain.js), así el "?" de "🎯 calibrada" funciona sin abrir el
  comité. Al abrir el comité se cierra Investigación IA (que lo tapaba); cerrar
  el comité mientras delibera ya no deja «Correr comité» bloqueado: al volver a
  abrirlo retoma la consulta. La orden preparada muestra su estado real
  (bloqueada → controles que fallaron; `pending_approval` → falta aprobación en
  Clientes; enviada) y la insignia 🧪 SIMULADO / 🔴 DINERO REAL, también en el
  cuadro de confirmación.
* `engine/research.js` — insignia de historial por agente en cada pestaña,
  "🎯 calibrada NN %" (o "sin historial suficiente") junto a la confianza, y el
  botón **🏛 Comité** en la cabecera de Investigación IA.

## 6. Variables de entorno

```
RESEARCH_OUTCOME_BAND=0.02        banda de acierto (acepta 2 = 2 %)
RESEARCH_CALIBRATION_K=10         fuerza del encogimiento bayesiano
RESEARCH_MODEL_COMMITTEE=...      ruta de modelo del presidente (default: RESEARCH_MODEL_DEFAULT)
COMMITTEE_MEMO_TTL_HOURS=72       un memo más viejo no se puede aprobar
COMMITTEE_MAX_CONCURRENT=2        comités deliberando a la vez (más → 429)
TRADE_PIN                         obligatorio para aprobar/rechazar/evaluar/clientes
```

Mandato del cliente (lo lee el comité de `brokerage.service.get_client`, dentro de
`client['mandate']`, `client['limits']` o arriba; **porcentajes**, 2 = 2 %):
`risk_budget_pct` (2), `max_position_pct` (10), `min_vol_pct` (10),
`blocked_symbols` / `restricted_symbols`, `allowed_symbols`; y en **US$**
`max_order_usd`, `max_daily_usd` (el corretaje los publica en
`client['mandate']`; lo usado hoy se lee de `brokerage.service._daily_used`).

## 7. Limitaciones conocidas (honestas)

* La calificación usa el precio como proxy de "tenía razón": una claim sobre
  márgenes puede ser cierta y la acción caer igual. Se documenta; la banda
  evita contar ruido como acierto.
* Claim creada **durante** la sesión: la base es el cierre de ese día (unas
  horas de ventaja). El precio en vivo al crearla queda guardado para auditoría.
* Las acciones fuera de EE.UU. se miden contra SPY, con fechas de Nueva York y
  en **moneda local** (sin ajuste cambiario): una devaluación cuenta como
  movimiento de la acción. El motivo de la calificación lo advierte.
* El "descarte de la barra en curso" usa el horario 9:30–16:30 de Nueva York sin
  calendario de feriados: en un feriado entre semana antes de las 16:30 solo
  retrasa la calificación, nunca usa un precio intradía.
* El límite diario disponible se lee de una función interna del corretaje
  (`_daily_used`); si no existe, el comité usa el límite diario completo como
  tope y el control del corretaje vuelve a verificarlo con el dato real.
* Segundo candado (HECHO 2026-10-03): `brokerage.service._execute` (camino
  común de `approve_preview` y `confirm_order`) rechaza una orden
  `source='committee'` si su memo no está `approved` o si el memo preparó otra
  orden (`research.committee.memo_allows_order`). Falla CERRADO: sin memo o sin
  módulo de comité → `memo_not_approved`, auditado como `order_blocked`.
* Sin historia (primeras semanas) todo sale "sin historial suficiente": los
  primeros finales de corto plazo llegan a los 30 días.
* El guardián de cifras (`core/numbers.py`) acepta coincidencias con cambio de
  escala (±15 %, ×1000): una cifra inventada puede pasar si casualmente coincide
  con otro número del paquete. El núcleo determinista no depende de él.
* Umbrales (35/−20/−50), pesos por horizonte y W0 son decisiones de diseño v1,
  no optimizadas: revisarlos cuando haya ≥ 100 checkpoints finales.

## 8. Qué sigue

1. Backtest del comité: correr el núcleo determinista "como si" en fechas
   pasadas con las claims de entonces y medir su exceso vs SPY.
2. Calibrar también los **umbrales** del comité con el historial (no solo la
   confianza de los agentes).
3. Política del inversionista (Investor Policy): mandato completo por cliente
   (horizonte, sectores, drawdown máximo) en lugar de 3 números.
4. Riesgo de cartera: dimensionar contra la cartera entera (correlaciones,
   VaR marginal) y no solo la acción sola.
5. Contradicciones: que el comité pida a los agentes en conflicto una réplica
   dirigida antes de decidir.
6. Exponer el memo por MCP (el track MCP puede llamar `run_committee` /
   `latest_memo` / `get_memo`; la ejecución sigue pasando por aprobación humana).
