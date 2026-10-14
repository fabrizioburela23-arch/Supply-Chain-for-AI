# Chat con interfaz generativa: especificación v1 (kblocks/1)

- **Fecha:** 2026-10-13
- **Estado:** fase **F0 (contrato) hecha** el 2026-10-13: el esquema, los ejemplos y su prueba están en el repo, y las decisiones D-1…D-5 quedaron con la opción recomendada (§12, reversibles). **F1 (constructores en sombra) hecha** el 2026-10-13: `core/genui/` arma el sobre en el servidor detrás de `GENUI` (off por defecto); notas para F2 en §16.
- **Pedido de Fabrizio:** «integrar el canvas UI en el chat normal… un interfaz fluido que no solo te muestra texto sino gráficos, imágenes, números, formas, todo integrado».
- **Insumos** (de la sesión de diseño; **no** están en el repo):
  - `1_inventory.md`: qué hay hoy en el chat y en el Canvas.
  - `2_patterns.md`: qué hacen ChatGPT, Claude, Google A2UI, Vercel, Perplexity y Bloomberg, con fuentes en el apéndice C.
  - Prototipo `prototipo.html` y capturas en `shots/` (todas sus cifras son de muestra).
- **Archivos en el repo (F0):**
  - `governance/schemas/kblocks-1.schema.json`: el contrato, JSON Schema 2020-12. Es la **fuente de verdad** (D-4: archivo versionado, sin PIN; no es un artefacto de `governance/artifacts/` porque no cambia números).
  - `tests/fixtures/genui/examples.kblocks.json`: 3 sobres válidos, 14 inválidos, 2 planes válidos y 7 inválidos.
  - `tests/test_genui_schema.py`: la prueba de esquema (sale del borrador `check_schema.py`). `jsonschema` es el oráculo y vive solo en `requirements-dev.txt` (versiones exactas en `constraints.txt`); fuera de CI la parte que lo usa se salta sola, en CI es obligatoria.
  - Un cambio del contrato que rompa clientes viejos **no** edita este archivo: nace `kblocks-2.schema.json` (y `v: "kblocks/2"`).

> Regla de lectura: los módulos y funciones se nombran por nombre, nunca por número de línea, porque app.html se está partiendo en `engine/app_*.js` mientras se escribe esto.

---

## 0. En una mirada

1. **Qué cambia:** la respuesta del chat deja de ser «un texto más botones». Pasa a ser una **lista ordenada de bloques**: texto, cifras, gráfico, tabla, ficha, mini-grafo, cascada de choque, línea de tiempo, mini-mapa, avisos, forma o imagen, y botones.
2. **Dónde se dibuja:** en `engine/genui.js`, con un catálogo **cerrado** de 17 tipos. La IA **nunca** escribe HTML, SVG ni cifras.
3. **Quién pone las cifras:** el **servidor**. Lo hace con constructores deterministas a partir de los **resultados de herramientas** que la respuesta ya usó. Cada cifra lleva `src` y `as_of`. Sin dato, el bloque muestra «— sin dato en vivo» con su motivo. Nunca se muestra un 0 falso.
4. **Qué hace la IA:** solo **elige y ordena**, con un `layout` (Plan) dentro de su paso final, del tipo `{"block":"chart.line","from":"F2"}` (`F2` = el resultado de herramienta que la IA ya vio etiquetado `[F2]` en su prompt). El servidor valida el plan contra el esquema, resuelve las referencias y descarta lo que no cumpla. Si no hay plan, el servidor aplica un **orden automático** con reglas fijas.
5. **Fluidez:**
   - Los esqueletos ya tienen la forma y la altura finales, así que la pantalla no salta.
   - Los bloques aparecen **mientras las herramientas terminan**, usando el sondeo de progreso que ya existe.
   - Entrada escalonada de 55–90 ms, gráficos que se dibujan solos y «📌 Fijar» que lleva el bloque a una ventana de Khipus OS.
   - Con «reducir movimiento» activado, todo aparece de golpe.
6. **No cambia:**
   - Solo se **añaden** campos a la respuesta: el sobre nuevo `ui`, y `answer` sigue igual.
   - La voz sigue leyendo `answer`.
   - El chat sigue sin enviar órdenes.
   - El impacto de un choque sale solo del kernel del servidor.
7. **Cómo se activa:**
   - Detrás de la bandera `kh_genui` en el navegador y de la variable de servidor `GENUI` (`off|shadow|on`).
   - Va en 9 fases (F0–F8), 42 pasos pequeños, unos **22 días-agente** (tras la revisión crítica: se sumó el trabajo nuevo que el código todavía no tiene, ver §15).
   - El primer valor visible llega en la F2: las fichas que el servidor **ya devuelve** (`cards.company`) y hoy nadie dibuja.

---

## 1. Objetivo y no-objetivos

**Objetivo.** Que una pregunta como «Desármame Nvidia» o «¿Qué pasa si cae TSMC?» se responda con una composición fluida: texto breve, el gráfico correcto, cifras con su fuente, la cadena en miniatura y la cascada animada. Todo dentro del hilo del chat central de Khipus OS y con la misma calidad que el Canvas. Cada pieza se puede «fijar» como ventana.

**No-objetivos (v1):**
- Que la IA escriba código de interfaz (HTML/JS/SVG), como Gemini dynamic view o el `show_widget` de Claude. **Prohibido** (§9).
- Imágenes «generadas por IA» o traídas de URLs elegidas por la IA. Solo hay formas del vocabulario cerrado y archivos del mismo origen.
- Streaming de tokens de la IA. El bucle de herramientas es JSON por pasos y no streamea. El texto final puede **revelarse** progresivamente en el cliente (§6.3), pero ya está completo cuando llega.
- Botones de dinero dentro de los bloques. Comprar y vender siguen por `KhipuToast.confirmOrder` → `brokerage.service`, y solo por los atajos explícitos que existen hoy.

---

## 2. Principios (no negociables)

1. **Datos, no código.** Un bloque es JSON con `type` de un catálogo cerrado. El cliente lo dibuja con `createElement`/`textContent` y SVG construido en código. No usa `innerHTML` con nada que venga del servidor o de la IA, salvo plantillas constantes.
2. **Toda cifra tiene dueño.** Cada número de un bloque vive en un `Figure`, que lleva su propio `src`/`as_of`, o en un `ValueSet`, que comparte la procedencia de un grupo. Una cifra sin `as_of` **no valida**. El bloque cita la llamada que lo alimentó (`prov`); si la referencia no resuelve, el bloque se descarta.
3. **La IA elige, el servidor llena.** El `layout` de la IA no admite números libres: el esquema solo permite `top` 1–20 y enumeraciones.
4. **Honestidad visible.**
   - Una cifra vacía es «—» con su motivo (`missing_reason`).
   - Una cifra vieja se marca `stale` (ámbar, con «hace 3 h»).
   - Si la calibración es débil, la cartera muestra «no damos cifra» (`portfolio.state = no_figure`).
5. **La prosa dice lo mismo que los bloques.**
   - El guardián (`core/numbers.py`) revisa todo el texto de la IA contra los mismos datos que llenaron los bloques. Eso incluye los textos del `layout` y los pros/contras con `origin: model`.
   - Los textos `alt` de los bloques los escribe el servidor con plantillas, no la IA.
6. **El bloque es la respuesta y el texto la explica.**
   - El texto no repite las cifras del bloque, siguiendo la regla de las tarjetas en línea de ChatGPT.
   - Las preguntas simples se responden **solo con texto**. Un bloque aparece únicamente si ayuda a entender.
7. **Un solo kernel y una sola fórmula.**
   - El impacto sale de `/api/hot/impact` o de `run_scenario`.
   - El NRS sale de `core/world.client_nrs`.
   - Los «ganadores» son rivales poco golpeados, con su **% de daño**.
   - El navegador no recalcula nada (`tests/test_no_client_engine.py`).
8. **Sencillo por defecto.**
   - Cada bloque muestra como máximo 2 acciones visibles; el resto va en «⋯».
   - Una respuesta lleva como máximo 4 bloques visuales, más textos y fuentes.
   - Hay como máximo 1 gráfico grande por respuesta en el modo `simple`.
9. **Bilingüe y explicable.** Cada rótulo es `{es,en}`, y el esquema lo exige. Cada métrica lleva su `explain`, que se muestra como el «?» de `engine/explain.js`.
10. **Movimiento que explica, no que adorna.**
    - Solo se anima `transform` y `opacity`.
    - Nada se anima en bucle.
    - Precios, capitalización y P&L **nunca** cuentan desde 0.
    - «Reducir movimiento» apaga toda animación.

---

## 3. Punto de partida (resumen del inventario)

- **Servidor:** `core/khipu_chat.py` hace el bucle JSON de herramientas con un máximo de 5 rondas. La respuesta ya trae:
  - `answer`, `actions`, `sources[].as_of`, `facts[]` ([F#]) y `entities[]`;
  - `agents_used`, con notas deterministas `_note_*`;
  - `cards.company` y `cards.committee`, que arma `chat_cards()`.
- **Progreso:** `GET /api/khipu/chat/progress/<req_id>` publica `phase` y `agents[]`, guardados en memoria en `_PROG`. **No** publica resultados parciales.
- **Cliente:**
  - `engine/khipu_chat.js`: `replyHTML()` dibuja `md(answer)`, las contribuciones, las fuentes y la meta. **No** dibuja `cards` ni `facts`.
  - El único gráfico dentro del chat es la acción `chart`, de texto libre. `fillReply` → `BixbyCockpit.canvasInto` → `KhipuLocalCharts`, y si eso falla, `/api/canvas/generate`: una **segunda llamada a la IA** con un contexto que manda el navegador, y donde la IA escribe los valores.
- **Brechas principales:**
  - G1: las fichas no se ven.
  - G3: el gráfico está desacoplado de los datos de la respuesta.
  - G4: la IA no conoce el vocabulario de acciones.
  - G5: no hay revelado progresivo.
  - G6: `get_history`, `run_scenario`, `get_exposure`, `get_subgraph`, `calculate_correlation` y `find_similar_entities` existen en el MCP pero **no** están en `MCP_READ_TOOLS`.
  - G11: el hilo visual se pierde al recargar.
  - G16: el pipeline de Canvas está duplicado (`canvasGenerate` y `canvasInto`).
- **Piezas reutilizables:**
  - Los renderizadores del Canvas (`cvBody`, `_cvLine`, `_cvBar`, `_cvKpi`, `_cvTable`, `_cvRadar`… en `engine/app_canvas.js`) y la paleta `cvCol`.
  - `KhipuOSWin.render(kind, body, arg)`, para `glance`, `supplychain` y `conviction`.
  - `chainOf(id, links, canon)` y `KhipuHot.*`, con `stampHTML` y `pnlLine`.
  - `KhipuState.frames()`: la película salto a salto que alimenta la cascada.
  - `explainChip`, `KhipuMascot` y `KhipuToast`.

---

## 4. El contrato: sobre `ui` (kblocks/1)

### 4.1 Dónde viaja

| Lugar | Campo | Cuándo |
|---|---|---|
| `POST /api/khipu/chat` (respuesta) | `ui` (Envelope, `state:"final"`) | Solo si `GENUI=on` **y** la petición trae `context.genui: 1` (la bandera del cliente). Los clientes viejos no lo reciben. |
| `GET /api/khipu/chat/progress/<req_id>?since=<seq>` | `ui` (Envelope, `state:"partial"`, solo los bloques con `seq > since`) | Mientras la respuesta está en curso. |
| `POST /api/genui/block` (nuevo) | Un `Block` | Rehacer un bloque con otro rango o vista, o ⟳ refrescar. Solo herramientas de lectura y sin IA (§5.9). |
| Libro de decisiones (`chat.answer`) | Blob `ui_blocks` + `ui_sha` | Siempre que se construye un sobre, también en `shadow` (§5.8). |

`answer` **no cambia de significado**: es el texto completo y la unión de los segmentos `text` del plan. Lo siguen usando la voz, el historial, el libro y el guardián.

### 4.2 Sobre (Envelope)

```json
{ "v":"kblocks/1", "lang":"es", "state":"final", "layout":"plan|auto", "as_of":"…Z", "seq":7,
  "impl":"genui.build@1", "spoken":{"es":"…","en":"…"}, "blocks":[ … ≤14 … ], "dropped":[{"index":2,"reason":"bad_ref"}] }
```

- `blocks` está **en orden de pantalla**. Es una lista plana con ids, igual que la lista de adyacencia de A2UI, así que un bloque puede llegar antes que otro y ocupar su lugar reservado.
- `spoken` sirve para la voz. Dice **qué** quedó en pantalla y **sin cifras nuevas**, por ejemplo «Te dejé el precio y la cadena».
- `dropped` es diagnóstico, no se muestra. Alimenta la métrica «planes descartados» del 🩺.

### 4.3 Tipos base (detalle en el apéndice A)

| Tipo | Qué es | Reglas |
|---|---|---|
| `I18n` | `{es, en}` | Ambos son obligatorios: así el esquema impone la regla bilingüe. |
| `Label` | Texto plano (nombre propio) o `I18n` (rótulo de interfaz) | Los nombres de empresa no se traducen. |
| `Figure` | `{v, unit, currency?, src, as_of, fact?, stale?, live?, precision?, explain?, missing_reason?}` | Si `v` es número, `as_of` es obligatorio. Si `v` es `null`, `missing_reason` es obligatorio. Si `unit` es `CCY`, `currency` es obligatorio. |
| `ValueSet` | Procedencia compartida `{label?, unit, src, as_of, fact?, stale?, explain?}` | Para barras, rankings, columnas numéricas de tabla y series. Un ítem puede pisar su `as_of`. |
| `Prov` | `{kind: tool\|view, name, call?, fact?, args?, generation?, graph_version?, decision_id?}` | `kind:tool` exige `call`, que es el índice (desde 0) en `tools_used`; la ficha pre-consultada también cuenta, porque el bucle la añade a `tools_used`. `fact` es el `[F#]` con el que ese resultado se mostró a la IA. El servidor comprueba que `name` esté en `GENUI_SOURCES`. `generation` es el id de la vista rápida (texto, p. ej. `g0.r1d6ee563.c03225529.snapshot`) o un contador ($defs/Generation, corregido en F1). |
| `Entity` | `{id, label, symbol?}` | `id` es el canónico de `core/entities`, nunca un alias. Los ids canónicos llevan mayúsculas, espacios y «&» («Nvidia», «Boyd Thermal», «Cushman & Wakefield»): el patrón del esquema se corrigió en F1 (antes exigía minúsculas y rechazaba 815 de 937 ids). |
| `Action` | `{kind, label, …}` | Ver §4.5. |
| Unidades | `USD, USD_B, USD_T, CCY, pct, pp, pts, x, nrs, count, index, score, ratio, days, years, none` | El formato visual (`$1,2 B`, `+3,4 %`, `40×`) lo decide el cliente. El servidor manda el número crudo. |

Comunes a todo bloque (`BlockBase`):
- Siempre: `id`, `type`, `state ∈ planned|ready|error|stale`.
- Según el estado: `data` es obligatorio si el bloque está `ready` o `stale`, y `error` (I18n) si está en `error`.
- Opcionales: `title`, `subtitle`, `alt`, `prov`, `sources[F#]`, `entity`, `pinnable`, `menu ⊂ {table, where_from, ask, csv, refresh}`, `actions[≤2]` y `seq`.
- Los bloques con cifras **exigen** `title`, `alt` y `prov`.

### 4.4 Catálogo v1: 17 tipos

| # | `type` | Para qué | Lo alimenta (servidor) | Límites | Interacción | Al fijar |
|---|---|---|---|---|---|---|
| 1 | `text` | Prosa de la IA en markdown-lite, con `marks` deterministas (nombre de empresa → chip al Dossier; `[F#]` → chip de fuente; `unverified` → tramo marcado por el guardián) | Segmentos `text` del plan, o `answer` partido en párrafos | ≤ 4.000 caracteres; sin HTML | Chips | — (no se fija) |
| 2 | `metric.tiles` | 1–6 cifras grandes con delta ▲▼, mini-sparkline y «?» | `get_company` (en vivo), `/api/hot/card`, `/api/hot/quote`, `get_risk_report` | 6 tiles | Hover → fuente y hora | Ventana `genui` |
| 3 | `chart.line` (`variant: full\|spark`) | Precio o métrica en el tiempo; hasta 4 series (`rebased` = índice 100) | `get_history` (cierres ajustados con fuente y `as_of`; rangos 1mo…5y = `Range` 1M…5Y) | ≤ 1.000 puntos por serie; 400 por defecto. **Nuevo:** hoy `get_history` recorta los más viejos (`dropped_oldest`); el reductor LTTB (elige puntos que existen, así la procedencia sigue valiendo) se añade en el constructor | Píldoras de rango (§7.9), cruz y tooltip, «ver tabla» | Ventana `genui` |
| 4 | `chart.bar` | Comparar magnitudes (h/v, divergentes) | `market_movers`, `rank_companies`, métricas del catálogo | ≤ 30 barras | Hover; clic → Dossier | `genui` |
| 5 | `chart.candles` | Velas OHLC(+volumen) | **Nuevo:** `get_history` solo devuelve cierres (`{date, close}`), sin apertura/máximo/mínimo. Hace falta `ohlc: true` en `get_history` (misma fuente `prices_eod`/Yahoo) **o** una herramienta de lectura que envuelva `/api/candles/<ticker>`. Hasta entonces el constructor no produce este tipo | ≤ 400 velas | Rango, línea ↔ velas | `genui` |
| 6 | `ranking` | Lista ordenada con barra y delta | `rank_companies`, `market_movers`, `get_conclusions_board` | ≤ 20 | Clic → Dossier | `genui` |
| 7 | `table` | Datos tabulares (texto, entidad, número, fecha, insignia) | Cualquier lista de herramienta | ≤ 8 columnas; ≤ 50 filas (8 en línea, «ver todo» → ventana) | Ordenar por columna; CSV en «⋯» | `genui` |
| 8 | `company.card` | Ficha: precio, cambio, capitalización, NRS, top 5 proveedores y clientes, estructura, valuación privada verificada | `chat_cards.company` (ya existe: `_company_card`). `spark` solo si en la misma respuesta hubo `get_history` (la ficha no trae serie) | 5 + 5 vínculos | Dossier, X-Ray | `glance` (ventana nativa) |
| 9 | `graph.mini` | Proveedores → centro → clientes; grosor = peso; naranja = riesgo; **solo flujo** | `get_supply_chain`, `get_subgraph`, `chainOf` | ≤ 25 nodos, ≤ 40 aristas | Hover resalta el camino; clic → mapa | `supplychain` (ventana nativa) |
| 10 | `impact.cascade` | El golpe salto a salto, el total ≥ umbral, los rivales menos golpeados (% de daño) y la línea de la cartera | `run_scenario` (`by_hop`, `victims[].hop`, `kernel`, `generation`, `graph_version`) o la vista `hot.impact` (`src` **debe** ser `hot_kernel`; `severity` 0–100 como `/api/hot/impact`). Cartera: `run_scenario(positions)` ya trae `portfolio.calibrated` (`core/scenario_pnl.translate`). **Nuevo:** rivales en el servidor (hoy `KhipuHot.rivals` es solo del navegador) | ≤ 6 saltos × 8 empresas | Animación salto a salto; «Simular» → ventana `sim` | `sim` |
| 11 | `timeline` | Hechos y noticias en el tiempo (`date_known:false` = «desde que se rastrea») | `get_world_events`, `get_news`, hechos temporales | ≤ 20 | Clic → fuente (`safeUrl`) o World Monitor | `genui` |
| 12 | `geo.mini` | Mapa SVG estático con puntos y arcos (sin teselas ni WebGL) | Puntos de empresa: `core/world.geo_coord(node)` (réplica de `engine/geo_coords.js`, con `precision` hq/city/country). Eventos: `get_world_events` (`lat`/`lon`). `/api/hot/geo` da **hechos** por empresa (reglas, rutas, eventos cerca), no coordenadas propias: van como `risk:true` sobre el punto de la empresa | ≤ 60 puntos, ≤ 30 arcos | Clic → `open_world {lat,lon}` | `geo` (World Monitor enfocado en el punto) |
| 13 | `callout` | `pros_cons`, `warning`, `info`, `unavailable` y `disclaimer` | Claims de investigación y tesis/riesgos del comité (`origin:tool`); textos del plan (`origin:model`, con guardián); sistema | 5 + 5 ítems | Chips [F#] | — |
| 14 | `image` | `shape` (forma del vocabulario cerrado o diagrama de hasta 6 pasos forma → forma) o `asset` (archivo del **mismo origen**) | El cliente dibuja las formas; los archivos están en `/static/genui/*` o `/api/genui/img/<sha>` | Rutas por lista blanca | — | — |
| 15 | `comparison` | 2–4 empresas × 1–10 métricas, con marca al mejor por fila; vistas `table\|bars\|radar` | `get_company` ×N (precio, cambio, capitalización, NRS, vínculos). **Nuevo:** márgenes, P/E, EV/ventas… no salen de ninguna herramienta del chat; hace falta `get_fundamentals` (lectura, envuelve `core/company_data`, lo mismo que usa `/api/findossier`). `calculate_correlation` para la vista de correlación | 4 × 10 | Cambiar vista (radar siempre con «Barras» al lado) | `compare` |
| 16 | `actions` | Fila final de botones | Constructor + plan | ≤ 4 | Ver §4.5 | — |
| 17 | `sources` | Fuentes [F#] con hora; **siempre al final** | `sources[]` + `facts[]` | ≤ 12 | Enlaces `safeUrl` | — |

Los requisitos pedidos quedan cubiertos así:
- **sparkline:** `chart.line` con `variant: spark`, o `spark` dentro de un tile o de la ficha.
- **mapa/globo:** `geo.mini`. Tiene el botón «abrir en World Monitor» para ir al globo de verdad.
- **formas:** `image.shape`.

### 4.5 Acciones: solo abrir o sugerir

Permitidas (`Action.kind`):
- `open_window`, con `window` ∈ `glance, supplychain, conviction, agents, xray, compare, canvas, sim, geo, genui`. Son los nombres **reales** de `KIND_META` en cockpit.js y de `registerKind` en oswindows.js: el Gráfico es `canvas` y el World Monitor es `geo`. `chart`, `world`, `research` y `committee` **no** son ventanas hoy, y en cockpit.js `research` es la Tesis rápida, que gasta IA.
- `open_dossier`, `open_xray`, `open_map` y `open_world`.
- `open_research` y `open_committee` (con `entity`) solo **abren** el panel: `KhipuResearch.open(id)` y `KhipuCommittee.open(id)` muestran lo guardado y no corren nada. Correr una investigación o un comité sigue pidiendo un clic dentro del panel.
- `prefill_chat`: deja el texto **escrito en la caja sin enviarlo**.
- `set_range` y `set_view`, que son locales al bloque.
- `pin`.

**No existen:** `broker`, `trade`, `order`, `place_order`, `approve` ni escrituras de ontología o alertas. El esquema los rechaza; la regla está en `examples.kblocks.json` → `invalid`. Si la conversación lleva a operar, el camino sigue siendo el de hoy: el atajo explícito del clasificador → panel de la Cabina → `KhipuToast.confirmOrder` → PIN → `brokerage.service`.

### 4.6 Imágenes y formas

- **`shape`:** 17 formas en un vocabulario cerrado (`chip, wafer, fab, datacenter, gpu, memory, battery, mine, ship, strait, satellite, rocket, power, cable, bank, globe, flow_arrow`). Las dibuja `engine/genui_shapes.js` como SVG en código, con colores de tokens `--os-*` y sin datos. Un diagrama `steps` es una fila de formas con rótulo, por ejemplo «oblea → TSMC → Nvidia → nube».
- **`asset`:** solo rutas `^/static/genui/<nombre>.(svg|png|webp)$` o `^/api/genui/img/<sha>$`. Ese proxy, futuro y opcional, solo sirve imágenes ya descargadas desde una lista blanca del servidor; por ejemplo, logos. **Nunca** una URL elegida por la IA, porque `img-src https:` permitiría exfiltrar contexto en la query (§9).

---

## 5. Servidor: cómo se construyen los bloques

### 5.1 Módulos nuevos (`core/genui/`, solo biblioteca estándar)

| Archivo | Responsabilidad |
|---|---|
| `core/genui/__init__.py` | `build_ui(message, calls, entities, plan, lang, ctx) -> (envelope, answer_text)`, `enabled(req)` (lee `GENUI` + `context.genui`), constantes de límites |
| `core/genui/schema.py` | Carga `governance/schemas/kblocks-1.schema.json` (decisión D-4) |
| `core/genui/validate.py` | **Validador compilado en stdlib** que espeja el esquema. Es el mismo patrón que `core/gates` frente a pySHACL: `jsonschema` solo en `requirements-dev.txt`, como oráculo en CI |
| `core/genui/builders.py` | Un constructor por herramienta (§5.2): `BUILDERS[name](args, result, ctx) -> [Block]`. Puros y deterministas |
| `core/genui/plan.py` | `parse_plan(raw)`, `resolve(plan, calls) -> blocks, dropped` |
| `core/genui/layout.py` | `auto_layout(blocks, answer, question)` (§5.5) |
| `core/genui/provenance.py` | `figures_of(block)` y `assert_from(block, result)`: el «caminante» que comprueba que cada número del bloque está en el resultado de la herramienta citada (§5.6) |
| `core/genui/alt.py` | Plantillas ES/EN para `alt` y `spoken`, solo con valores del bloque |
| `core/genui/api.py` | Blueprint: `POST /api/genui/block` (§5.9) y `GET /api/genui/catalog` (tipos y versión, para el cliente y el 🩺) |

### 5.2 Constructores deterministas (herramienta → bloques)

| Herramienta / vista | Bloques que produce | Notas |
|---|---|---|
| `get_company` | `metric.tiles` (**solo** precio, cambio, capitalización, NRS) + `company.card` | Reusa `_company_card`. Sin precio en vivo, el tile queda con `v:null` y su `live_reason`. `get_company` **no** trae márgenes ni P/E: esos tiles salen de `get_fundamentals` (nuevo) |
| `get_fundamentals` (**herramienta nueva**, lectura) | `metric.tiles` de fundamentales, `table`, `comparison` | Envuelve `core/company_data` (FMP → Yahoo → AV en USD, con fuente), lo mismo que `/api/findossier`; resultado con `source`/`as_of` por métrica |
| `get_history` (**nuevo en el chat**) | `chart.line` (`chart.candles` cuando exista `ohlc`, ver §4.4) | Devuelve `points[{date, close}]`, `source`, `as_of`, `currency`, `adjusted`, `change_pct`. LTTB a ≤ 400 puntos en el constructor |
| `get_supply_chain` / `get_subgraph` (**nuevo**) | `graph.mini` | Solo `relation_class` de flujo; socios e inversores van a `related`, no a aristas |
| `run_scenario` (**nuevo**) / vista `hot.impact` | `impact.cascade` | Los saltos salen de `victims[].hop` y `by_hop` (ya están en el servidor; el cliente no usa `KhipuState.frames` para las cifras). `generation`, `graph_version` y `kernel.semver` vienen en el resultado. `severity` = `magnitude` × 100. **Nuevo:** `least_hit_rivals` necesita portar `KhipuHot.rivals` (filtro sobre cifras del kernel: rubro con caídas ≥ 40 %, rival < 15 %) a `core/genui/rivals.py`, con prueba de paridad contra el JS |
| `run_scenario(positions)` (si hay posiciones) | `impact.cascade.portfolio` | El resultado ya trae `portfolio.calibrated` de `core/scenario_pnl.translate`. Mapeo: `ok` → `figure` (`pnl_usd` ± `band_usd`); `uncalibrated` / `weak` / `kernel_mismatch` → `no_figure` con `note_es/en`; `no_positions` → `no_positions`. **Nuevo:** `run_scenario` pide `{symbol, usd}` pero el chat manda `{symbol, shares}`; el cliente debe mandar también `usd` por posición con la misma valoración que ya usa `KhipuHot.pnlLine` (acciones × precio mostrado en USD). Sin `usd`, `no_positions` |
| `get_exposure` (**nuevo**) | `metric.tiles` (exposición) o `chart.bar` | |
| `rank_companies`, `market_movers` | `ranking` o `chart.bar` | |
| `get_world_events`, `get_news` | `timeline` (+ `geo.mini` si hay ≥ 3 puntos con lat/lon: solo `get_world_events` los trae) | |
| `get_committee_memo`, `get_conclusions_board` | `callout pros_cons` (`origin:tool`) + `chart.bar` divergente de convicción | Lleva siempre el `callout disclaimer` «Información, no consejo» |
| `get_research` / `get_claim_evidence` | `callout pros_cons` con `claim_id` y [F#] | |
| `get_risk_report` | `metric.tiles` (VaR/CVaR con «?») + `chart.bar` de contribuciones | |
| `calculate_correlation` (**nuevo**) | `comparison` o `table` | |
| `find_similar_entities` (**nuevo**) | `ranking` | |
| `get_company` × 2–4 (+ `get_fundamentals` × 2–4) en la misma respuesta | `comparison` | Métricas comunes, `better` según el diccionario de métricas. Solo con `get_company` la comparación queda en precio, cambio, capitalización, NRS y conteo de vínculos |
| siempre | `sources` (último), `actions` (prefills sugeridos + abrir) | |

**Herramientas que se abren al chat (G6), de a poco:** `get_history`, `run_scenario`, `get_exposure`, `get_subgraph`, `calculate_correlation` y `find_similar_entities` existen en `mcp_server/ops.py` (`scope read`), y `get_fundamentals` es nueva. Ojo: `core/khipu_chat.py` dejó escrito «menos herramientas = decisiones mejores y más rápidas» al sacar dos del catálogo. Por eso se abren en dos tandas: **F1** solo `get_history` y `run_scenario` (las que alimentan los bloques principales); **F5**, el resto, una por una, y solo si el conjunto de evaluación (§10.3) no empeora la elección de herramientas. Hoy solo `tests/test_repair_research.py` mira `MCP_READ_TOOLS` (exige `get_research_health`); añadir es compatible. Usan el contrato MCP `detail` + `max_chars`; para un bloque, el servidor pide `detail: standard` y guarda el resultado **completo** en la caché por pedido (`execute_tool`/`_cache_key`), separado del recorte que ve la IA.

### 5.3 Plan de la IA (`layout`)

- **Dónde va:** en el paso final del bucle JSON, que hoy es `{"final":{"answer","actions"}}` y pasa a ser `{"final":{"answer","actions","layout":[…]}}`. El esquema es `$defs/Plan`.
  - Lleva hasta 12 ítems.
  - Un ítem `{"text":…}` es prosa.
  - Un ítem `{"block":<tipo>,"from":"F2"|"F1,F3"|"view:impact:<id>","opts":{range, metric, metrics[], top, view, highlight, variant, shape}}` pide un bloque; un `callout` de la IA lleva además `pros[]` y `cons[]` (cada uno ≤ 200 caracteres).
  - **Por qué `F#` y no un índice de llamada:** la IA nunca ve índices. Cada resultado le llega con el prefijo `[F#]` (`_fact_prefix` → `FactBook.add(…, key=_cache_key(tool, args))`), incluida la ficha pre-consultada. El servidor resuelve `F#` → clave de caché → la entrada de `calls`. Si el mismo resultado se repite, `FactBook` devuelve el mismo `F#` («ya consultado arriba: ver [F#]»). Un `F#` cuyo `kind` termina en `:error` resuelve a `bad_ref`.
- **Qué se añade al prompt** (`build_system`, unos 350 tokens, cacheados con `cache_control` en Claude):
  - El catálogo de tipos, con una línea de «cuándo usarlo» cada uno.
  - La regla «nunca escribas cifras dentro de un bloque; `from` es el `[F#]` del resultado que quieres mostrar».
  - «Preguntas simples = solo texto; máximo 4 bloques».
  - De paso, el **vocabulario de acciones** que hoy falta (G4).
- **Validación (`plan.parse_plan`)**, en este orden:
  1. Esquema `Plan`.
  2. Tipo en el catálogo.
  3. `from` resuelve (vía `FactBook`) a una llamada **exitosa** de esta respuesta, o a una vista permitida.
  4. El constructor de esa herramienta sabe producir ese tipo.
  5. Un `opts` desconocido se descarta.
  6. Duplicados fuera.
  7. Presupuesto (≤ 4 visuales).
  - Lo que falla va a `dropped` con su `reason`. **No se repara con IA.**
- **Respuesta:** `answer` pasa a ser la unión de los `text` del plan (si hay plan) o el `answer` del paso (si no). Esto garantiza que el guardián y la voz vean **todo** el texto.

### 5.4 Orden automático (`layout:"auto"`): también el respaldo

Aplica cuando no hay plan, el plan es inválido, la IA no está disponible (`fallback_answer`) o la ruta es `local_fact` de Jev o `@agente`:
1. El primer párrafo del texto, como titular.
2. El bloque «principal» según la intención: impacto → `impact.cascade`; comparar → `comparison`; precio o «cómo va» → `chart.line`; empresa → `metric.tiles` + `company.card`; cadena o riesgo → `graph.mini`; noticias → `timeline`.
3. El resto del texto.
4. Hasta 2 bloques secundarios, por relevancia: herramientas de la entidad principal primero.
5. `callout disclaimer` si hubo comité.
6. `actions`.
7. `sources`.

En el modo `simple` se omiten los secundarios.

### 5.5 Guardián de cifras: cuatro capas

1. **Esquema:** una cifra sin `src`/`as_of` no valida.
2. **Procedencia:** `provenance.assert_from(block, result)` recorre cada número del bloque (los `Figure.v`, los `ValueSet` con sus ítems, los puntos de las series y las celdas) y exige que **exista** en el resultado citado. Se permiten transformaciones **declaradas** del constructor: rebase a índice 100, LTTB, redondeo a la precisión mostrada y conversión de unidad `USD → USD_B`. Cada transformación queda en el `impl` y en su prueba dorada. Si falla, el bloque se descarta y queda `dropped: invalid`, con un aviso en el log.
3. **Prosa:** `core/numbers.py` revisa la prosa con el comportamiento de hoy: un reintento con feedback y, si persiste, «(⚠ cifra no verificada)». Revisa los `text` del plan y los `pros`/`cons` con `origin:model`, contra los **mismos** datos (resultados de herramientas + DATOS EN VIVO). El tramo marcado viaja como `marks[kind=unverified]` y el cliente lo subraya en ámbar.
4. **Plan:** el esquema del plan no admite números libres, así que la IA no puede «dictar» un valor.

Comprobado contra el código de hoy: el guardián corre sobre el texto **crudo** del paso JSON (`_ai_complete` → `unsupported_in`), así que también ve el `layout`. Con `core/numbers.unsupported_in`, un paso con `"range":"6M"`, `"1Y"` o `"top":5` no marca nada (no son dinero, % ni múltiplos). Un `pros` con «75 %» que no está en los datos sí se marca. No hace falta tocar el guardián.

### 5.6 Degradación (cada caso tiene interfaz)

| Caso | Qué ve el usuario |
|---|---|
| Herramienta caída o lenta (> 14 s) | El bloque queda `error` con su mensaje bilingüe y ⟳ (que llama a `/api/genui/block`); el resto de la respuesta sigue. |
| Dato parcial (sin precio en vivo) | Tile «— sin dato en vivo» + motivo; nunca un 0. |
| Plan inválido | Orden automático; el usuario no nota nada. |
| Sin IA (crédito, caída) | `fallback_answer` + orden automático con los bloques de `get_company` (hoy ya se prefetchea). Pasa a ser **mejor** que hoy. |
| Cliente viejo o sin bandera | No recibe `ui`; ve exactamente lo de hoy. |
| Cliente con un tipo desconocido (versión futura) | Muestra `alt` como texto (regla A2UI/MCP Apps: «la UI siempre tiene equivalente en texto»). |
| `GENUI=off` | No se construye nada (costo 0). |

### 5.7 Libro de decisiones y repetición (replay)

- La decisión `chat.answer`, que ya existe (`ledger_answer`, asíncrona), suma el blob `ui_blocks` (el sobre final, 90 días como el texto) y `ui_sha`. **Sin** texto personal adicional.
- `impl: genui.build@1` va a `core/impls.py` STAMPS (`tests/test_impl_registry.py`) con su salida dorada `tests/golden/impl_genui_build.json`. Si cambia el constructor, nace `@2`; nunca se edita `@1`.
- **Repetible:** dado `calls` (resultados guardados como `replay_inputs`) + plan, `build_ui` debe dar el **mismo** sobre: `identical` / `differs`.

### 5.8 Presupuesto de servidor

- Construir un bloque cuesta ≤ 5 ms; el sobre completo, ≤ 25 ms (p95). Sin E/S: usa solo lo que ya está en `calls`.
- El sobre pesa ≤ 48 KB en JSON. Por encima de eso, el servidor recorta: primero las series (puntos) y después los bloques secundarios, y lo deja en `dropped: over_budget`.
- **Sin** llamadas extra a la IA por la interfaz: el plan viaja en el mismo paso final, sumando unos 150 tokens de salida.

### 5.9 `POST /api/genui/block` (refinar sin IA)

- **Cuerpo:** `{type, tool, args, opts, lang}`. `opts` usa las mismas claves del Plan. `tool` ∈ `GENUI_REFRESH_TOOLS`, una lista cerrada de lectura **sin IA**:
  - `get_company`, `get_history`, `get_supply_chain`, `get_subgraph`, `run_scenario`, `rank_companies`, `market_movers`, `get_world_events`, `get_news`, `get_fundamentals`, `calculate_correlation`, `find_similar_entities` y `get_exposure`.
  - **Nunca** `ask_agent`, `web_search`, `run_research`, `run_committee` ni `scenario_exposure`, porque gastan IA o cupo externo.
- **Proceso:** `execute_tool` → constructor → validación → `Block`.
- **Límite:** 30 pedidos/min por IP. Sin PIN, porque es lectura.
- **Libro:** aunque lea, es un `POST`, y `tests/test_cierre_infra.py` exige clasificar **toda** ruta de escritura. Va a `CON_DECISION` como `'whatif.shock (async, solo con run_scenario)'`, igual que `POST /api/hot/scenario`. Con otra herramienta no deja decisión. Si se prefiere no dejar ninguna, va a `SIN_DECISION` con categoría `'lectura'`.
- **Uso:** cambiar el rango 1M/6M/1A, velas ↔ línea, ⟳ refrescar un bloque `stale` o en `error`, y repintar al reabrir el historial.
- La IA **no** participa: es el patrón de Perplexity «refinar el mismo gráfico», pero sin modelo.

---

## 6. Revelado progresivo («streaming») dentro de 1 worker

### 6.1 Transporte: sondeo del progreso que ya existe

- Hoy `_PROG[req_id]` guarda `phase` y `agents`. Se añaden `seq` (contador) y `blocks` (lista de bloques `planned|ready|error` con su `seq`).
- **Cuándo se escribe:**
  - Al **empezar** cada herramienta, el bloque correspondiente pasa a `planned`, con el tipo que su constructor producirá por defecto. Así el cliente dibuja el esqueleto con la forma y la altura correctas.
  - Al **terminar** cada herramienta, el constructor corre y el bloque pasa a `ready` o `error`.
- **Cómo pide el cliente:** `GET …/progress/<req_id>?since=<seq>` devuelve solo los bloques nuevos (≤ 64 KB por respuesta).
- **Frecuencia:** el cliente sigue con **0,7 s**. El límite del endpoint es `@rate_limit(600, 300)`: 600 consultas por IP cada 300 s. Una pestaña que sondea sin parar hace unas 430 en 300 s, así que cabe. Dos pestañas sondeando **a la vez durante 300 s** pasarían el tope, aunque en la práctica solo se sondea mientras hay una respuesta en curso (≤ 45 s, unas 64 consultas). No hace falta subirlo; si el 🩺 muestra 429 en el progreso, el cliente pasa a 1,4 s.
- **Orden provisional:** el del §5.4. Al llegar la respuesta final con el plan, los bloques que cambian de lugar se mueven con FLIP (≤ 220 ms). Un bloque ya visible que el plan **no** usa no desaparece de golpe: pasa al final, plegado bajo «Más datos de esta respuesta», para no borrar algo que el usuario ya estaba mirando. En la práctica casi nunca se mueven, porque el orden automático y la IA suelen coincidir. Si hace falta, el texto final se inserta **entre** bloques ya visibles sin moverlos de altura: el espacio se reserva.

### 6.2 ¿SSE? Más adelante y con topes

- Un stream SSE retiene un hilo de gunicorn por chat abierto, y hay 12 hilos en total. Además, el bucle de herramientas no produce tokens de texto que streamear.
- Por eso, en v1 **no**. Si en el futuro la IA streamea el texto final, iría como `GET /api/khipu/chat/stream/<req_id>` con un máximo de 3 streams simultáneos (`GENUI_SSE_MAX`) y 60 s cada uno. Si está lleno, se vuelve al sondeo.

### 6.3 El texto

- La prosa llega **completa** con la respuesta final. El cliente la **revela** rápido: unos 60 caracteres por fotograma, con un tope de 900 ms y un leve fundido de desenfoque, como en el prototipo.
- No inventa nada. Con «reducir movimiento» se muestra completa al instante.
- **No** se finge escritura antes de tener el texto.

### 6.4 Coreografía (medida en el prototipo)

| t | Qué pasa |
|---|---|
| 0 | Burbuja del usuario. Fila de pasos con las mascotas que trabajan (`appendPending`, ya existe). |
| ~0,7 s | Paso «Simulando el choque · run_scenario» ✓; esqueleto del bloque principal con el **tamaño final**. |
| 1–3 s | El bloque pasa a `ready`: fundido cruzado esqueleto → contenido (220 ms) y el gráfico se dibuja (380 ms). |
| final | Revelado del texto; bloques secundarios escalonados 55–90 ms (máx. 6); la fila de pasos se pliega a «2 pasos · 1,9 s». |

Ver `shots/strip_c.png` (10 fotogramas con tiempos) y `shots/motion_c.gif`.

---

## 7. Cliente: `engine/genui.js` (+ `genui_charts.js`, `genui_shapes.js`)

### 7.1 API pública (`window.KhipuGenUI`)

```js
KhipuGenUI.enabled()                         // bandera kh_genui (localStorage, try/catch) && servidor la anuncia
KhipuGenUI.renderAnswer(host, envelope, {compact, onAction, lang, reduced})  // pinta un sobre completo
KhipuGenUI.update(host, partialEnvelope)     // aplica bloques nuevos por seq (esqueleto → listo)
KhipuGenUI.renderBlock(el, block, opts)      // un bloque suelto (ventana fijada, historial)
KhipuGenUI.register(type, {render, skeleton, toTable, height})  // registro de renderizadores
KhipuGenUI.toTable(block)                    // vista accesible / CSV
KhipuGenUI.pin(block, fromEl)                // → BixbyCockpit.stage('genui', {id: req_id+':'+block.id, block}) con FLIP
KhipuGenUI.catalog()                         // tipos soportados (para avisar al servidor: context.genui_types)
```

`engine/khipu_chat.js` cambia poco. En `fillReply`, si la respuesta trae `d.ui` y `KhipuGenUI.enabled()`, se pinta `KhipuGenUI.renderAnswer(...)` **en lugar de** `md(answer)` + el gráfico `chart`. Contribuciones, fuentes y meta siguen igual. Los dos consumidores, la Cabina (`chatAsk`/`chatVoice`) y `command_center.js`, heredan el cambio sin tocarlos. `compact` se decide con `ResizeObserver` (< 520 px).

**F3 (hecho, 2026-10-14):** `_pollProgress` NO usa `KhipuGenUI.update`: pasa `p.ui` a `KhipuChat.progressBlocks` (un `renderBlock` por bloque, reconciliado por identidad `keyOf` = `core/khipu_chat._ui_key`). El motor (`progressBlocks`, `land`, «Más datos», revelado, `keepOnError`) vive en `engine/genui_progress.js` (`window.KhipuGenUIProgress`), que `loadExtras` carga con los gráficos solo con la bandera: sin ella nadie lo descarga. Las acciones de los bloques ya a la vista se enlazan TARDE (`el._kcAct`, fijado por `fillReply`) y llegan al `onAction` de la Cabina. `renderAnswer` acepta `reuse` (`reuse.has(b)`: una fila de fichas que ya se veían se pinta sin entrada).

### 7.2 Registro de renderizadores (qué se reutiliza)

| Tipo | Renderizador | Base existente |
|---|---|---|
| `text` | `md()` de khipu_chat.js ampliado con chips de `marks` | `md`/`inline` (escapa primero) |
| `metric.tiles` | `tiles()` | `_cvKpi` + sparkline nueva |
| `chart.line` / `spark` | `genui_charts.line()` | `_cvLine`, portado a tokens `--os-*` y a un contenedor arbitrario (hoy busca la tarjeta por id global) |
| `chart.bar`, `ranking` | `genui_charts.bar()` | `_cvBar` |
| `chart.candles` | `genui_charts.candles()` | nuevo (SVG; sin Chart.js en el chat) |
| `table` | `table()` | `_cvTable` + `buildFundTable` (ganador por fila) |
| `company.card` | `card()` | datos de `_company_card`; aspecto de la ventana `glance` |
| `graph.mini` | `graph()` | `paintChain`/`chainOf` de oswindows.js (nodos como **píldoras**, no círculos) |
| `impact.cascade` | `cascade()` | prototipo (c) + `KhipuHot.stampHTML`. La línea de cartera se pinta desde `data.portfolio` del bloque, sin llamar a `KhipuHot.pnlLine`, para no pedir la cifra dos veces |
| `timeline` | `timeline()` | nuevo |
| `geo.mini` | `geo()` | TopoJSON `/vendor/world-110m.json`: es el proxy del mismo origen de server.py hacia `unpkg.com/world-atlas@2.0.2`, con caché del servidor; el primer pedido depende de unpkg. Se decodifica una vez y se usa proyección equirectangular, con la ruta SVG cacheada por región. Sin TopoJSON, los puntos se dibujan sobre una retícula de coordenadas |
| `callout` | `callout()` | prototipo (b) |
| `image` | `genui_shapes.draw()` / `<img>` del mismo origen | nuevo |
| `comparison` | `compare()` | `_cvRadar` + `compareTable`/`radarSpec` de localcharts |
| `actions`, `sources` | `actions()`, `sources()` | `actionLabel`, `_timeTag`, `quoteSrcChip` |

**Fin de la duplicación (G16):** en la F7, la pestaña Canvas pasa a usar `genui_charts` y se borra el camino `chart` → `canvasInto` dentro del chat.

### 7.3 DOM seguro

- Solo `createElement`, `textContent`, `setAttribute` (lista blanca: `class`, `role`, `aria-*`, `data-tip`, `tabindex`, atributos SVG numéricos) y `addEventListener`. **Sin** `onclick=` en línea, para no complicar el día en que se quite `'unsafe-inline'`.
- `innerHTML` solo con cadenas **constantes** del propio módulo. Un test lo escanea (§10).
- Enlaces solo con `window.safeUrl(u)` y `rel="noopener noreferrer"`. Imágenes solo si la ruta pasa la expresión regular del esquema.
- Multi-instancia: siempre `root.querySelector`, nunca ids globales. Así se pueden fijar 2 copias del mismo bloque.

### 7.4 Sistema de movimiento

Tokens nuevos en el bloque `--os-*` de cockpit.js (`docs/KHIPUS_OS.md` §1):

```css
--os-dur-1:120ms;  /* hover, presionar */
--os-dur-2:220ms;  /* entrada de bloque, fundido esqueleto→contenido */
--os-dur-3:380ms;  /* dibujo de gráfico, fijar en ventana */
--os-ease-out:cubic-bezier(.2,0,0,1);    /* M3 "emphasized" */
--os-ease-inout:cubic-bezier(.4,0,.2,1);
@media (prefers-reduced-motion:reduce){ :root{--os-dur-1:0ms;--os-dur-2:0ms;--os-dur-3:0ms} }
```

| Momento | Animación | Reglas |
|---|---|---|
| Entrada de bloque | opacidad 0→1, `translateY(6px→0)`, escala .98→1 | Escalonado 55–90 ms, máx. 6, total < 400 ms |
| Esqueleto → contenido | Fundido cruzado **en el mismo sitio** | Esqueleto con la **forma real**: filas para ranking, curva para línea, nodos para el grafo. Altura reservada = `register().height(block, width)` |
| Línea | `stroke-dashoffset` | `--os-dur-3` |
| Barras | `scaleX`/`scaleY` desde la base | |
| Cascada | El origen pulsa 3 veces y para; cada salto se enciende con su barra, su conteo y sus chips | El conteo muestra «…» hasta llegar, **nunca** «0 empresas» |
| Conteos | Cuenta hacia arriba ≤ 600 ms **solo** para `count` y `score` | **Nunca** para `USD*`, `pct` de precio, P&L ni capitalización: esos aparecen con fundido. El valor final está en `aria-label` desde el primer fotograma |
| Cambio en vivo | Destello verde o rojo (convención del ticker) | Sin dígitos rodando |
| 📌 Fijar | FLIP del rectángulo en línea al de la ventana; `document.startViewTransition` si existe, FLIP manual si no | Móvil: hoja inferior |
| Desplazamiento | Si el bloque mide > 70 % de la vista, se para en su borde superior (desplazamiento suave) | Evita el «salto» visto en el prototipo |

Prohibido: bucles, parallax, animar `width`/`height`/`top` y más de 6 animaciones simultáneas.

### 7.5 Accesibilidad

- El hilo lleva `role="log"`, `aria-live="off"` para el flujo de bloques y un `role="status"` oculto aparte, que anuncia «Khipu está respondiendo…» y luego «Respuesta lista: 1 gráfico, 1 tabla / Answer ready: 1 chart, 1 table». El mensaje lleva `aria-busy="true"` mientras llega.
- Cada gráfico es `role="img"` con `aria-label` = `alt` del servidor y lleva «Ver como tabla» en «⋯» (`toTable`).
- Arriba y abajo se marcan con color **y** forma (▲▼). El foco es visible y todo se puede usar con el teclado: tab a los chips, Enter abre y Esc cierra el menú.
- Contraste en claro y en oscuro. La serie B se validó con el script de dataviz: `#E8623A` en claro y `#E06640` en oscuro. **No** usar `--os-neg` oscuro (`#F07A52`) como serie, porque falla la banda de luminosidad.

### 7.6 Tema, idioma y «?»

- Solo tokens `--os-*`. Los atributos SVG no leen `var()`, así que se usa `el.style.setProperty('fill', 'var(--os-…)')` (CSSOM: la CSP lo permite aun el día que se quite `'unsafe-inline'`, a diferencia del atributo `style="…"`) o se lee `getComputedStyle` una vez por tema. La paleta categórica sale de `cvCol` (validada), con su orden fijo.
- Los rótulos `I18n` se eligen con `window.LANG` **en el momento de pintar**. Al cambiar ES/EN, los bloques visibles se repintan desde su JSON. La prosa queda en el idioma en que se respondió, como hoy.
- Si un `Figure.explain` existe, se muestra `explainChip(key)`. Las métricas nuevas (`pe`, `ev_sales`, `max_drawdown`…) se registran con `explainRegister`.

### 7.7 Fijar en ventana

```js
// Por la cola de arranque que ya usa oswindows.js (cockpit.js drena window.__kosKindQueue al iniciar),
// así genui.js puede cargarse antes o después de cockpit.js.
(window.__kosKindQueue = window.__kosKindQueue || []).push(['genui', {
  icon: '📌', es: 'Bloque', en: 'Block', multi: true,
  title: function (arg) { var t = arg && arg.block && arg.block.title;
    return !t ? '' : (typeof t === 'string' ? t : (t[window.LANG === 'en' ? 'en' : 'es'] || t.es)); },
  render: function (body, arg) { KhipuGenUI.renderBlock(body, arg.block, {compact: true, pinned: true}); }
}]);
```

- `registerKind` ya lo añade a `KIND_META` y a `MULTI_KINDS` (con `multi: true`); no hay que editar la tabla a mano. Ojo: el escritorio distingue ventanas del mismo tipo por `arg.id` (`desktop.js keyFor`). Si `arg` no trae `id`, todas las ventanas `genui` comparten la clave `genui:` y cada 📌 **reemplaza** al anterior. Por eso `pin` abre con `stage('genui', {id: req_id + ':' + block.id, block})`.
- La ventana **vuelve a pintar el mismo JSON**, no clona el DOM. Así los tooltips y el diseño compacto siguen funcionando.
- `company.card`, `graph.mini`, `impact.cascade` y `comparison` se fijan en sus **ventanas nativas** (`glance`, `supplychain`, `sim` y `compare`), que tienen más detalle.

### 7.8 Interacción dentro del bloque

- **Píldoras de rango y vistas:** `set_range` y `set_view` → `POST /api/genui/block` → se reemplaza el mismo bloque con un fundido. No se crea una respuesta nueva.
- **Menú «⋯»:**
  - Ver como tabla.
  - ¿De dónde sale?: herramienta, argumentos, `as_of`, generación y enlace a `/api/ledger/why/<decision_id>` si existe.
  - Preguntar sobre esto: hace `prefill_chat` con «Sobre <título>: » y añade `context.ref_block = {id, prov}`, para que la siguiente pregunta use los mismos datos.
  - Descargar CSV.
  - ⟳ Refrescar.
- **Chips de empresa en el texto:** `_surface('dossier', id)`. **Chips [F#]:** resaltan la fuente en `sources`.
- **Fabrizio:** como máximo 2 botones visibles por bloque.

### 7.9 Historial que no se pierde (G11)

- `saveHistory` guarda, además del texto, el `ui` final de las últimas 12 respuestas en `localStorage` (`kh_chat_ui`). Cada lectura y escritura va en try/catch. Tope de 400 KB; si se supera, se descartan primero las series.
- Al recargar, los bloques se repintan con una franja «datos del 13-oct 15:02 / data as of …» y ⟳.
- Va solo en el navegador del usuario. La copia auditable es el libro.

### 7.10 Voz

- `chatVoice` devuelve `d` con `d.ui`. La voz lee `answer` + `ui.spoken[lang]`, que dice **qué** hay en pantalla sin cifras nuevas.
- Si el usuario dice «léeme la tabla», es una pregunta normal del chat. La respuesta lleva el `alt`, que sale de los mismos datos.
- No se crea ninguna herramienta de voz nueva: el contrato de 17 se mantiene.

---

## 8. Presupuestos de rendimiento

| Qué | Presupuesto |
|---|---|
| `genui.js` + `genui_charts.js` + `genui_shapes.js` (sin minificar) | ≤ 90 KB en total; en `sw.js` SHELL |
| Sobre `ui` | ≤ 48 KB; parcial por sondeo ≤ 64 KB |
| Pintar un bloque (portátil medio, 1440 px) | ≤ 8 ms; gráfico con 400 puntos ≤ 16 ms |
| Respuesta completa (≤ 6 bloques) | ≤ 60 ms de JS en el hilo principal en total; nada de > 50 ms seguido (troceado con `requestAnimationFrame`) |
| Nodos DOM por respuesta | ≤ 1.500 |
| Animaciones simultáneas | ≤ 6; solo `transform`/`opacity` |
| Saltos de diseño (CLS) dentro del hilo | 0 (altura reservada) |
| Mapa `geo.mini` | TopoJSON una vez por sesión (caché del SW); ruta SVG por región memorizada |
| Servidor | ≤ 25 ms p95 por sobre; 0 llamadas extra a IA; 0 E/S extra salvo `/api/genui/block` |
| Latencia total de la respuesta | ≤ +150 ms p95 frente a hoy (medido con el conjunto de evaluación, §10) |
| Historial | ≤ 400 KB en `localStorage` |

---

## 9. Seguridad

| Amenaza | Defensa |
|---|---|
| La IA mete HTML/JS (p. ej. `<img onerror>`) y, como CSP aún permite `'unsafe-inline'`, se ejecutaría | Bloques = datos; `additionalProperties:false` / `unevaluatedProperties:false` en todo el esquema; el texto pasa por `md()`, que escapa primero; prueba de «sin innerHTML con datos» |
| Exfiltración por imagen (`img-src https:` abierto) | `image.asset.path` solo del mismo origen (expresión regular); enlaces de noticias son `<a>` con `safeUrl`, nunca `<img>` |
| La IA dicta cifras falsas | Plan sin números; procedencia comprobada; guardián sobre toda la prosa |
| Inyección desde datos de herramientas (noticias, web) | Los textos de herramientas se pintan como texto (`textContent`); nunca se convierten en acciones; `actions` solo del constructor o del plan validado |
| Botón de dinero | No existe en el esquema (`Action.kind` y `WindowKind` cerrados); `tests/test_order_single_path.py` sigue vigilando |
| Abuso de `/api/genui/block` | Solo herramientas de lectura en lista blanca, 30/min por IP, mismo `rate_limit` |
| Bloque gigante (denegación de servicio del navegador) | Límites del esquema (`maxItems`, `maxLength`) + presupuesto de 48 KB en el servidor + validación otra vez en el cliente |

**CSP:** la interfaz generativa **no necesita cambios**, porque todo va por `/api/*` y `/vendor/*`. Como mejora aparte, se propone cerrar `img-src` a `'self' data: blob:` más los hosts que la app usa de verdad: hoy `logo.clearbit.com` y las imágenes de lanzamientos de Launch Library 2 en `engine/spacemonitor.js`. Antes de cerrarlo, conviene una semana con `CSP_REPORT_ONLY` para medirlo. Es la decisión D-3.

---

## 10. Plan de pruebas

### 10.1 Nuevas

| Archivo | Qué prueba |
|---|---|
| `tests/test_genui_schema.py` | Que el esquema es Draft 2020-12 válido y sin claves duplicadas; los ejemplos válidos pasan y los inválidos fallan (borrador: `check_schema.py`); **conformidad**: el validador compilado (`core/genui/validate.py`) coincide con `jsonschema` (oráculo, `requirements-dev.txt`) en ≥ 1.000 mutaciones aleatorias, con 0 diferencias |
| `tests/test_genui_builders.py` | Que cada constructor, con resultados de herramienta grabados (`tests/fixtures/genui/*.json`), produce su salida dorada (`tests/golden/genui_*.json`); `assert_from` acepta todos los números; una cifra quitada del resultado hace que el bloque se descarte; `v:null` lleva motivo; cascada solo con `src: hot_kernel`; «ganadores» con `damage_pct` |
| `tests/test_genui_plan.py` | Los casos de §5.3: cifra literal → rechazo; tipo desconocido; `from` que no resuelve o apunta a una llamada fallida; > 4 visuales → recorte; `opts` desconocido; HTML en `text` sale escapado; ruta de imagen externa; acción `broker`/`order` → `forbidden_action` |
| `tests/test_genui_guardian.py` | Prosa del plan y `pros`/`cons` con `origin:model` pasan por `core/numbers.py`; una cifra que no está en los datos queda marcada (`marks.unverified`); `alt`/`spoken` sin cifras ajenas a los datos (`spoken` sin ninguna) |
| `tests/test_genui_contract.py` | Con `GENUI=off` o sin `context.genui` la respuesta es **idéntica** a la de hoy (campo a campo); con `on`, solo se **añade** `ui`; `answer` = unión de los `text`; el progreso con `since` devuelve solo lo nuevo; `/api/genui/block` rechaza herramientas fuera de la lista |
| `tests/test_genui_ledger.py` | El blob `ui_blocks` y `ui_sha` en `chat.answer`; `genui.build@1` en STAMPS; replay `identical` |
| `tests/test_genui_client_static.py` | Escaneo de `engine/genui*.js`: sin `innerHTML =` con valores no constantes, sin `onclick=`, sin `eval`/`new Function`, sin `window.confirm`; todo texto visible en un diccionario `{es,en}`; los tipos registrados coinciden con el enum del esquema |
| `tests/test_genui_render_node.py` | Arnés de node (como los existentes: carga `agents_registry.js` primero): funciones puras `KhipuGenUI._vm(block)` (modelo de vista: formato de unidades, precisión, «—», `stale`), `height()` estable, `toTable()` |
| `tests/test_genui_browser.py` | Chromium real (se salta sin Playwright; ruta `/opt/pw-browsers/...` como `tests/test_scenario_pnl_browser.py`) sobre los 3 sobres válidos de `examples.kblocks.json` más uno de ranking (la 4.ª pregunta del prototipo), que hay que añadir: 4 respuestas × {1440, 390} × {claro, oscuro} × {ES, EN}; capturas comparadas con `tests/golden/shots/genui_*.png` (≤ 0,5 % de píxeles distintos); 0 errores de consola; sin desplazamiento horizontal a 390; con `reducedMotion: 'reduce'`, todo visible en t = 0 y `document.getAnimations().length === 0`; `role=log` + `role=status`; cada gráfico con `role=img` y `aria-label`; orden de tabulación; 📌 abre una ventana `genui` con el mismo contenido |

### 10.2 Deben seguir verdes

`test_khipu_chat.py`, `test_khipus_os_chat.py` y el resto de `test_khipus_os_*`; `test_canvas*.py`; `test_no_client_engine.py`; `test_order_single_path.py`; `test_cleanup_dialogs.py` / `test_cleanup_client.py`; `test_impl_registry.py`; `test_agents_registry.py`; `test_vault.py` (regenerar la bóveda); `test_cierre_infra.py`: **toda** ruta POST cuenta como escritura, así que `POST /api/genui/block` hay que clasificarlo en el mismo paso que lo crea (ver §5.9); si no, la CI se pone roja. También `test_repair_research.py` (lee `MCP_READ_TOOLS`) y `test_world.py` (paridad de coordenadas, si el constructor de `geo.mini` usa `core/world.geo_coord`).

### 10.3 Conjunto de evaluación (antes de abrir a todos)

Son 30 preguntas ES/EN: empresa, comparar, choque, noticias, cartera, simple y fuera de tema. Se miden:
- % de respuestas con bloque cuando corresponde (meta ≥ 80 %) y sin bloque cuando no (meta ≥ 90 %).
- **0** cifras sin procedencia.
- % de planes descartados (meta < 10 %).
- Latencia p50/p95 frente a hoy.
- Peso del sobre.

Lo corre `scripts/genui_eval.py` contra el servidor local con las herramientas grabadas.

---

## 11. Despliegue por fases (bandera `kh_genui` + `GENUI`)

**Banderas:**
- `GENUI`, en el servidor: `off` por defecto.
  - `shadow`: construye el sobre, lo mide y lo guarda en el libro, **sin enviarlo**.
  - `on`: lo envía a quien lo pida.
- `kh_genui`, en el navegador (`localStorage`): se activa en 🩺 o en el menú del avatar → «Respuestas visuales (beta) / Visual answers (beta)». La petición manda `context.genui: 1` y `context.genui_types` (los tipos que sabe pintar).

**Cada fase cumple las reglas de despliegue del repo:**
- `node --check` y `py_compile`; `pytest`.
- Subir la versión de `sw.js` y añadir los archivos nuevos a `SHELL`.
- Regenerar la bóveda (`scripts/build_vault.py`).
- Actualizar `CLAUDE.md` y `docs/ESTADO.md`.
- Las variables nuevas van en la lista de entorno de `CLAUDE.md`.
- **Coordinación:** la partición de app.html ya terminó (commit `a0ebf30`, sw v268), así que las etiquetas `<script src>` de los archivos nuevos se añaden a app.html en el paso 15. Todo lo nuevo vive en `engine/genui*.js` y `core/genui/`.

| Fase | Pasos (cada uno = 1 commit desplegable, detrás de la bandera) | Archivos | Estimación | Sale cuando |
|---|---|---|---|---|
| **F0 Contrato** | ✅ 1. Copiar esta especificación a `docs/CHAT_UI_GENERATIVA.md`. ✅ 2. Esquema a `governance/schemas/kblocks-1.schema.json` (D-4) y ejemplos a `tests/fixtures/genui/`. ✅ 3. `jsonschema` a `requirements-dev.txt` + `constraints.txt`. ✅ 4. `tests/test_genui_schema.py` (a partir de `check_schema.py`). ✅ 5. Decisiones de Fabrizio (§12: por defecto, reversibles) | docs, governance, tests | 0,5 d | Esquema en el repo; test verde |
| **F1 Constructores en sombra** | ✅ 6. `core/genui/__init__.py` + `validate.py` (validador compilado) + conformidad con `jsonschema`. ✅ 7. Constructor `get_company` → `metric.tiles` + `company.card`, más `sources`/`actions`, con salidas doradas. ✅ 8. Constructores `get_supply_chain` → `graph.mini`; `rank_companies`/`market_movers` → `ranking`/`chart.bar`; `get_world_events`/`get_news` → `timeline` (+ `geo.mini` con `core/world.geo_coord`). ✅ 9. Constructores de comité, pizarra, investigación y riesgo → `callout`/`chart.bar`/`metric.tiles`. ✅ 10. `provenance.py` (`assert_from`) + `alt.py`. ✅ 11. `get_history` y `run_scenario` a `MCP_READ_TOOLS` + sus constructores (`chart.line` con LTTB; `impact.cascade`) + `core/genui/rivals.py` con paridad contra `KhipuHot.rivals`. ✅ 12. El cliente manda `usd` por posición en `context.portfolio` (misma valoración que `KhipuHot.pnlLine`) → línea de cartera de la cascada. ✅ 13. `enrich_answer` → `build_ui` con `GENUI=shadow`; métricas en el 🩺 (ms, KB, descartes); `GENUI` en la lista de entorno de `CLAUDE.md`. ✅ 14. Blob `ui_blocks` + `ui_sha` en `chat.answer`; `genui.build@1` en STAMPS con su dorada | core/genui/*, core/khipu_chat.py, core/impls.py, engine/khipu_chat.js (paso 12), tests | 4 d | En sombra: 0 cifras sin procedencia en 1 día de tráfico real; ≤ 25 ms p95 |
| **F2 Renderizador** | ✅ 15. `engine/genui.js`: registro, `renderAnswer`/`renderBlock`, estados, `toTable`, a11y, ES/EN, DOM seguro; renderizadores `text`, `metric.tiles`, `company.card`, `callout`, `actions`, `sources`. `<script src>` en app.html + `SHELL` de sw.js. ✅ 16. `engine/genui_charts.js`: línea/spark y barra/ranking, portados de `_cvLine`/`_cvBar` a `--os-*` y a cualquier contenedor. ✅ 17. Renderizadores `graph.mini`, `impact.cascade`, `timeline`, `table` y `comparison`. ✅ 18. `engine/genui_shapes.js` + `image` + `geo.mini`. ✅ 19. Tokens de movimiento en cockpit.js. ✅ 20. Gancho en `fillReply` (si hay `d.ui` + bandera) + interruptor «Respuestas visuales (beta)» + `GENUI=on`. ✅ 21. Tests static, node y browser + capturas doradas | engine/genui*.js, engine/khipu_chat.js, engine/cockpit.js, sw.js, app.html | 4 d | Fabrizio, con la bandera, ve fichas, gráficos y cadena en el chat; capturas aprobadas |
| **F3 Progresivo** | ✅ 22. `_PROG` con `seq` + `blocks`; `progress_get(since)` (bloques solo para el navegador que preguntó, `X-Khipu-Owner`; `seq` solo con provisionales; la ficha pre-consultada espera a la herramienta PRINCIPAL de la intención). ✅ 23. Esqueletos con forma real + altura reservada (height() medido en Chromium, ±6 %); fundido cruzado; revelado del texto; plegado de la fila de pasos. ✅ 24. Desplazamiento inteligente (> 70 %) + reordenar por el plan con FLIP + «Más datos de esta respuesta»; un error tras los bloques los deja a la vista. Motor en `engine/genui_progress.js` (perezoso, con los gráficos) | core/khipu_chat.py, engine/genui.js, engine/genui_progress.js, engine/khipu_chat.js | 2 d | Primer bloque visible antes que el texto en ≥ 70 % de las respuestas con herramientas; CLS 0 — ✅ (Chromium 1440 ES oscuro y 390 EN claro: CLS 0) |
| **F4 Interacción** | 25. `POST /api/genui/block` + `GENUI_REFRESH_TOOLS` + clasificación en `tests/test_cierre_infra.py` + píldoras de rango y vistas. 26. Menú «⋯»: tabla, «¿de dónde sale?» con `/api/ledger/why`, «preguntar sobre esto» con `context.ref_block`, CSV y ⟳. 27. 📌 tipo `genui` por `__kosKindQueue` + FLIP / View Transitions + hoja móvil; ventanas nativas para ficha, grafo, cascada y comparación. 28. Chips de empresa y [F#] en el texto | core/genui/api.py, server.py (registrar blueprint), engine/genui.js, tests | 3 d | Las 4 preguntas del prototipo funcionan de punta a punta con datos reales |
| **F5 Composición por la IA + herramientas nuevas** | 29. Catálogo + vocabulario de acciones en `build_system` (con `cache_control`). 30. `layout` en el paso final; `plan.py` (resolver `F#` con `FactBook`, validar, `dropped`). 31. Prosa del plan por el guardián + `marks.unverified`. 32. `scripts/genui_eval.py` + 30 preguntas, con Gemini **y** Claude. 33. Abrir `get_subgraph`, `get_exposure`, `calculate_correlation` y `find_similar_entities` de a una, solo si la evaluación no empeora. 34. Herramienta nueva `get_fundamentals` (`core/company_data`) + tiles de fundamentales y `comparison` completa. 35. `get_history` con `ohlc: true` (o herramienta de velas) + renderizador `chart.candles` | core/khipu_chat.py, core/genui/plan.py, mcp_server/ops.py, scripts/, tests | 4 d | Evaluación: metas de §10.3 cumplidas |
| **F6 Voz + historial** | 36. `spoken` en `chatVoice`/voice.js (sin cifras nuevas). 37. `kh_chat_ui` (12 respuestas, 400 KB) + franja «datos del…» + ⟳ | engine/voice.js, engine/khipu_chat.js, engine/genui.js | 1,5 d | Recargar no pierde gráficos; la voz dice qué dejó en pantalla |
| **F7 Unificar Canvas** | 38. La pestaña Canvas usa `genui_charts` (un solo juego de gráficos con `--os-*`). 39. Borrar el camino `chart` → `canvasInto` del chat y unificar `canvasGenerate`/`canvasInto`. 40. Decidir `/api/canvas/generate` (D-2) | engine/app_canvas.js, engine/cockpit.js, engine/khipu_chat.js, server.py | 2 d | Un solo renderizador; `test_canvas.py` y `test_canvas_charts.py` verdes |
| **F8 Abrir a todos** | 41. Una semana con Fabrizio → bandera encendida por defecto (el usuario puede apagarla) → `GENUI=on` fijo. 42. Ayuda en ❓ Guía + recorrido de un minuto si corresponde | engine/guide.js, docs | 1 d | Sin regresiones en el 🩺; Fabrizio aprueba |
**Total: unos 22 días-agente** (antes 20: se sumaron `get_fundamentals`, velas OHLC, rivales en el servidor y `usd` por posición, que el código de hoy no tiene). F1 y F2 pueden ir en paralelo cuando el esquema esté fijado en F0. Los pasos 33–35 son independientes entre sí.

---

## 12. Decisiones que necesita Fabrizio

Fabrizio no las contestó todavía. Rige la recomendación: **decidido por defecto 2026-10-13, reversible** (si él elige otra cosa, se cambia sin perder nada).

| # | Pregunta | Recomendación | Estado |
|---|---|---|---|
| D-1 | ¿La IA puede escribir sus propios «pros y contras» (revisados por el guardián), o solo se muestran los que vienen de la investigación con evidencia? | Ambos, pero los de la IA marcados «opinión de Khipu» y sin cifras nuevas | Decidido por defecto 2026-10-13, reversible: **ambos**; `origin:model` se muestra como «opinión de Khipu / Khipu's opinion» y pasa por el guardián |
| D-2 | ¿Retiramos `/api/canvas/generate`, donde la IA escribe los valores de un gráfico? | Sí en el chat (F7); en la pestaña Canvas, dejarlo solo como último recurso con aviso «✦ IA», o retirarlo | Decidido por defecto 2026-10-13, reversible: **se retira del chat en F7**; la pestaña Canvas lo conserva como último recurso con el aviso «✦ IA» |
| D-3 | ¿Cerramos `img-src` a los hosts que usamos? | Sí, tras una semana en modo informe | Decidido por defecto 2026-10-13, reversible: **sí**, después de una semana en modo informe (`CSP_REPORT_ONLY`) midiendo qué hosts se usan |
| D-4 | ¿El esquema es un artefacto de gobernanza (con versión y PIN) o un archivo de docs? | Archivo versionado `kblocks/1` en `governance/schemas/` **sin** PIN (no cambia números) | Decidido por defecto 2026-10-13, reversible: **`governance/schemas/kblocks-1.schema.json`**, sin PIN y fuera de `governance/artifacts/` y del `manifest.json` (no cambia números; `scripts/build_governance.py` solo lee `artifacts/`) |
| D-5 | ¿Guardamos los gráficos del chat en el navegador (12 respuestas, 24 h)? | Sí | Decidido por defecto 2026-10-13, reversible: **sí**, 12 respuestas y 24 h en `localStorage` (`kh_chat_ui`, §7.9) |

---

## 13. Riesgos y preguntas abiertas

- **Gemini y el JSON más largo:** el paso final crece unos 150 tokens. Los pasos JSON ya fallan a veces (de ahí `synthesize()`). Mitigación: el plan es **opcional**; si el JSON falla, se usa el orden automático.
- **Hilos:** cada sondeo cuesta un hilo unos milisegundos, así que el riesgo es bajo. SSE solo con topes (§6.2).
- **Peso de `get_history` en el chat:** la caché por pedido guarda la serie completa y la IA ve solo el resumen (`detail` / `max_chars`). Así se evita inflar el `scratch` de 26.000 caracteres.
- **Más herramientas en el catálogo del chat:** `core/khipu_chat.py` ya quitó herramientas porque «menos = decisiones mejores». Abrir 7 de golpe (6 del MCP + `get_fundamentals`) puede empeorar la elección. Por eso se abren en dos tandas (§5.2) y cada una pasa por la evaluación.
- **Posiciones en USD que manda el navegador:** la línea de cartera usa el valor en USD que calcula el cliente, igual que hoy `KhipuHot.pnlLine`. La cifra final sigue saliendo del servidor (κ calibrado), pero el valor de entrada es del navegador. Se marca `src: client_positions` en la procedencia.
- **Parecerse a ChatGPT o Claude sin su HTML libre:** la expresividad está acotada a 17 tipos. Es a propósito, porque la confianza en las cifras es el diferencial. Se crece añadiendo tipos (`kblocks/1` → `/2`) con su constructor y su prueba.
- **Partición de app.html:** ya terminó (commit `a0ebf30`). El gancho del cliente va en `engine/khipu_chat.js`; en app.html solo se añaden las etiquetas `<script src>`.
- **A2UI literal:** no lo adoptamos aún (v1.0 es RC, «expect changes»). Mantenemos la misma separación entre árbol de componentes y datos, así que mapearlo más adelante es trivial.

---

## 14. Lecciones del prototipo (para quien lo implemente)

1. Sin conteo animado en precios ni P&L: solo en conteos y puntajes.
2. Nunca un «0» provisional: «…» hasta que llega el dato.
3. Desplazamiento: parar en el borde superior del bloque si mide > 70 % de la vista.
4. Diseño **compacto propio** por ancho (< 520 px), no escalar un SVG de 600 px.
5. Nodos del grafo como **píldoras**: los círculos cortan los nombres. En tablas, `overflow-wrap: normal`, porque `anywhere` partía «Crecimien-to».
6. El radar siempre con la vista «Barras» al lado; la tabla es el bloque principal.
7. Los toasts tapan contenido a 390 px: usar el estado del propio botón 📌 o `KhipuToast` arriba.
8. Nada en bucle: el pulso del origen se repite 3 veces y el cursor desaparece al terminar.
9. Esqueletos con la forma real del bloque, no barras grises genéricas.
10. El borde punteado del flanco vacío casi no se ve en modo claro: usar `--os-ink-3` al 40 %.

Capturas: `shots/b_light_1440.png` (Nvidia), `shots/c_dark_1440_pinned.png` (cascada + 📌), `shots/c_dark_390_sheet.png` (hoja móvil), `shots/d_dark_1440.png` (comparar), `shots/a_dark_1440.png` (ranking + fichas), `shots/b_light_1440_menu.png` (menú ⋯), `shots/b_light_1440_hover_line.png` (cruz y tooltip), `shots/c_dark_1440_reduced_motion.png`, `shots/c_dark_1440_EN.png`, `shots/strip_c.png` y `shots/strip_b.png` (fotogramas con tiempos), y `shots/motion_c.gif` y `shots/motion_b.gif`. El prototipo autocontenido es `prototipo.html`, con parámetros `?theme=light&lang=en&instant=1&q=abcd`. **Todas sus cifras son de muestra (DEMO).**

---

## 15. Verificación contra el código (revisión crítica, 2026-10-13)

Cada constructor se cotejó con el código del repo en el commit `a0ebf30`. ✅ = el dato ya existe tal cual; 🛠 = trabajo nuevo, ya incluido en los pasos de §11.

| Bloque / pieza | Lo alimenta | Estado | Prueba en el código |
|---|---|---|---|
| `company.card`, `metric.tiles` (precio, cambio, cap., NRS) | `get_company` → `_company_card` | ✅ | `core/khipu_chat._company_card`: `price`, `change_pct`, `market_cap_usd_b`, `nrs`, `top_suppliers/customers`, `live_reason`, `private_valuation` |
| `metric.tiles` / `comparison` de fundamentales (margen, P/E…) | `get_fundamentals` | 🛠 paso 34 | Ninguna herramienta del chat ni del MCP devuelve márgenes ni P/E; viven en `core/company_data` (lo usa `/api/findossier`) |
| `chart.line` | `get_history` | ✅ datos · 🛠 abrirla al chat (paso 11) | `mcp_server/ops.t_get_history`: `points[{date, close}]`, `source`, `as_of`, `currency`, `adjusted`; `RANGES = 1mo…5y` → el enum `Range` se recortó a 1M…5Y |
| LTTB | constructor | 🛠 paso 11 | Hoy `get_history` corta lo más viejo (`dropped_oldest`) |
| `chart.candles` | `get_history ohlc` o herramienta de velas | 🛠 paso 35 | `get_history` solo da cierres; `/api/candles/<ticker>` existe pero no es herramienta |
| `graph.mini` | `get_supply_chain` / `get_subgraph` | ✅ (`get_subgraph` 🛠 paso 33) | Aristas con `relation_class`; socios e inversores en `related` |
| `impact.cascade` (saltos, total) | `run_scenario` / `hot.impact` | ✅ datos · 🛠 abrirla (paso 11) | `victims[{id, label, impact_pct, hop}]`, `by_hop`, `reach_1pct`, `kernel.semver`, `generation`, `graph_version`. `severity` de `/api/hot/impact` es 0–100 (el esquema decía 0–10: corregido) |
| `impact.cascade.least_hit_rivals` | rivales en el servidor | 🛠 paso 11 | Hoy solo existe en el navegador (`engine/hotclient.js` `rivals`) |
| `impact.cascade.portfolio` | `run_scenario(positions)` | ✅ cálculo · 🛠 `usd` (paso 12) | `portfolio.calibrated` ← `core/scenario_pnl.translate` (`ok`/`weak`/`uncalibrated`/`kernel_mismatch`/`no_positions`); el chat manda `shares`, la herramienta pide `usd` |
| `ranking` / `chart.bar` | `rank_companies`, `market_movers` | ✅ | `_extra` en `core/khipu_chat.py` |
| `timeline` | `get_world_events`, `get_news` | ✅ | `t_get_world_events` guarda `lat`, `lon`, `time`, `source`, `url` |
| `geo.mini` | `core/world.geo_coord` + `get_world_events` (+ hechos de `/api/hot/geo`) | ✅ | `/api/hot/geo` da hechos por empresa, **no** coordenadas; el punto de la empresa sale de `geo_coord` (con precisión) |
| `callout pros_cons` | `get_research`, `get_committee_memo` | ✅ | `_committee_card`: `thesis_es/en`, `risks_es/en` |
| Plan `from` | `[F#]` del prompt | ✅ | `_fact_prefix` / `FactBook.add(key=_cache_key)`: la IA ve `[F#]`, nunca índices (antes el plan usaba `cN`: corregido) |
| Guardián sobre el plan | `core/numbers.unsupported_in` | ✅ | Probado: `"6M"`, `"1Y"`, `"top":5` no se marcan; «75 %» sin dato sí |
| Ventanas del `Action` | `KIND_META` / `registerKind` | ✅ tras corregir | `chart`→`canvas`, `world`→`geo`; `research`/`committee` pasan a `open_research`/`open_committee` |
| 📌 varias ventanas | `desktop.js keyFor` | ✅ tras corregir | Hace falta `arg.id` único |
| «¿De dónde sale?» | `GET /api/ledger/why/<id>` | ✅ | Sin PIN da el resumen; con PIN, todo |
| `POST /api/genui/block` | — | 🛠 paso 25 | `tests/test_cierre_infra.py` obliga a clasificar todo POST |
| Mapa base | `/vendor/world-110m.json` | ✅ | Proxy del mismo origen en server.py hacia `unpkg.com/world-atlas@2.0.2` |
| CSP | — | ✅ sin cambios | `img-src 'self' data: blob: https:`; `script-src 'self' 'unsafe-inline'` + cdnjs/jsdelivr; `connect-src` cerrado: todo va por `/api` |

### 15.1 Cobertura del prototipo por el esquema

| Prototipo (`prototipo.html`) | Esquema `kblocks/1` |
|---|---|
| `kpi.row` | `metric.tiles` |
| `chart.line` | `chart.line` |
| `chart.bar` («Ranking de baterías») | `ranking` o `chart.bar` |
| `company.card` con 3 empresas («Las 3 primeras») | 3 × `company.card` cuentan contra el tope de 4 visuales. En `simple`, el constructor usa `table` con entidades |
| `graph.mini` | `graph.mini` |
| `callout.pair` | `callout` `pros_cons` |
| `impact.bars` | `impact.cascade` |
| `exposure.line` («Impacto en tu cartera») | `impact.cascade.portfolio`, que sale de `run_scenario(positions)`, no de `get_exposure` como dice el prototipo |
| `table.compare` | `comparison` con `view: table` |
| `chart.radar` | `comparison` con `view: radar` (siempre con «Barras» al lado) |

Todos los tipos del prototipo tienen equivalente. El esquema además tiene `timeline`, `geo.mini`, `image`, `chart.candles`, `table`, `text`, `actions` y `sources`, que el prototipo no dibuja; esos se prueban con `examples.kblocks.json` y con el test de navegador del paso 21.

---

## 16. F1 hecha (2026-10-13): qué hay y qué necesita la F2

**Servidor (`core/genui/`, solo biblioteca estándar):**
- `__init__.py`: `mode()` (`GENUI` off|shadow|on), `wants(context)`, `build_ui(...)` → (sobre, texto), `rebuild(inputs)` (replay), `stats()` (🩺). El texto del sobre es `answer` partido en párrafos (sin Plan hasta F5: siempre `layout: "auto"`).
- `builders.py`: un constructor por herramienta (§5.2) + `history_compare` (2–4 `get_history` → una línea en índice 100) + `company_comparison` (2–4 `get_company`; una fila solo si todas las cifras comparten fuente y moneda).
- `provenance.py`: `figures_of` + `assert_from` con transformaciones declaradas (`round`, `usd_b`, `scale100`, `rebase`). Un bloque con una cifra sin dueño se descarta (`dropped: invalid`) y queda en el log.
- `validate.py`: validador compilado; `tests/test_genui_validate.py` = 0 diferencias con `jsonschema` en 1.300+ mutaciones.
- `layout.py`: intención por reglas (impacto, comparar, riesgo de cartera, noticias, precio, cadena, comité); simple = el bloque principal (empresa = cifras + ficha); pro = + hasta 2 secundarios, ≤ 4 visuales, ≤ 2 grandes. Aviso «información, no consejo» si hubo comité o investigación.
- `rivals.py`: porte exacto de `KhipuHot.rivals` (paridad en node, `tests/test_genui_rivals.py`). `run_scenario` devuelve ahora `least_hit_rivals` (+ `least_hit_rivals_rule`) calculado sobre **todos** los impactos del kernel; el constructor solo los copia.
- `core/khipu_chat.py`: `get_history` y `run_scenario` en `MCP_READ_TOOLS` (con su receta en el prompt y su nota de agente); `validate_request` guarda `context.genui` y `context.genui_types` **solo si vienen**; `_genui_attach` arma el sobre y lo añade como `ui` solo con `GENUI=on` + `context.genui=1`.
- Libro: `chat.answer` lleva `ui_blocks` (blob 90 días) = `ui_sha`, `ui: {mode, sent, n_blocks, dropped, replay_blob}` (las entradas del cálculo, sin el mensaje del usuario) e `impl.ui = genui.build@1`. `core/replay.py` rehace el sobre (paso `ui_blocks`): no vuelve «identical» una respuesta de IA, pero delata un cambio de código sin `@2`.
- Medido en esta máquina: p95 ≈ 3 ms por sobre con 4 herramientas y ≈ 14 ms con 18 (meta ≤ 25 ms p95); ≤ 48 KB (recorte LTTB y luego secundarios).

**Para la F2 (cliente):**
1. `marks[].s/e` van en **unidades UTF-16** (las de `String.prototype.slice`): con emojis fuera del plano básico no se corren.
2. La tarjeta del 🩺 es `services.genui` en `/api/diagnostics`; hay que sumar `'genui'` a la lista `order` de `openDiagnostics` (engine/app_main.js) para que se vea.
3. `get_history` y `run_scenario` todavía no tienen mascota en `engine/agents_registry.js` (`TOOL_AGENT`): caen en `khipu`. Sugerido: `get_history` → técnico, `run_scenario` → cadena.
4. El menú de los bloques aún no trae `refresh` (llega con `POST /api/genui/block`, F4).
5. Los ids de `Entity` son los canónicos del grafo (mayúsculas y espacios): usarlos tal cual con `_surface('dossier', id)` / `window._canonId`.

**Revisión F2 (2026-10-14), hecho:** los puntos 1-3 de arriba; el cliente indexa las marcas con `slice` (UTF-16);
`run_scenario.positions` lo pone el SERVIDOR desde `context.portfolio[].usd` (`khipu_chat._server_args`; lo del modelo se
descarta y el argumento no aparece en su catálogo) y sin cartera la cascada dice `no_positions`; la fila de la comparación
lleva la hora MÁS VIEJA y sale si sus cifras se separan > 6 h; transformación `scale100_round` para la severidad;
`ui_inputs` sin argumentos de texto libre; `context.ref_block` validado → línea del prompt; `genui_charts.js` y
`genui_shapes.js` se cargan perezosos (`KhipuGenUI.loadExtras`).

## Apéndice B: ejemplo mínimo de respuesta con `ui`

```json
{
  "answer": "Nvidia diseña los chips, pero no los fabrica: depende de pocos proveedores clave.",
  "actions": [], "sources": [ … ], "facts": [ … ], "entities": [{"id":"nvidia","label":"Nvidia"}],
  "cards": { "company": { … } },
  "ui": {
    "v": "kblocks/1", "lang": "es", "state": "final", "layout": "plan", "as_of": "2026-10-13T15:02:11Z",
    "impl": "genui.build@1",
    "blocks": [
      {"id":"t1","type":"text","state":"ready","data":{"md":"**Nvidia** diseña los chips, pero **no los fabrica**…","lang":"es"}},
      {"id":"b1","type":"chart.line","state":"ready","title":{"es":"Precio","en":"Price"},
       "alt":{"es":"Precio de NVDA en 6 meses…","en":"NVDA price over 6 months…"},
       "prov":{"kind":"tool","name":"get_history","call":1},
       "data":{"variant":"full","range":"6M","ranges":["1M","6M","1Y"],
               "series":[{"name":"NVDA","values":{"unit":"USD","src":"prices_eod","as_of":"2026-10-12"},"points":[ … ]}]}},
      {"id":"s1","type":"sources","state":"ready","data":{"items":[{"id":"F1","label":"Precios EOD","as_of":"2026-10-12"}]}}
    ]
  }
}
```

Los ejemplos completos (válidos e inválidos) están en `examples.kblocks.json`. Los números del ejemplo son de relleno.

---

## Apéndice C: fuentes externas

- Claude, visuales en línea: https://claude.com/resources/articles/claude-builds-visuals · https://www.theregister.com/2026/03/13/claude_charts_a_new_course/
- MCP Apps (SEP-1865): https://modelcontextprotocol.io/seps/1865-mcp-apps-interactive-user-interfaces-for-mcp · https://blog.modelcontextprotocol.io/posts/2025-11-21-mcp-apps/
- OpenAI Apps SDK, pautas de interfaz: https://developers.openai.com/apps-sdk/concepts/ui-guidelines · https://developers.openai.com/apps-sdk/build/custom-ux
- ChatGPT, gráficos interactivos: https://help.openai.com/en/articles/8437071-data-analysis-in-chatgpt
- Google A2UI: https://github.com/google/A2UI · https://a2ui.org/specification/v0.9-a2ui/ · https://a2ui.org/reference/messages/
- Google, interfaz generativa: https://research.google/blog/generative-ui-a-rich-custom-visual-interactive-user-experience-for-any-prompt/
- Vercel AI SDK, interfaz generativa: https://app.unpkg.com/ai@7.0.40/files/docs/04-ai-sdk-ui/04-generative-user-interfaces.mdx · https://vercel.com/blog/ai-sdk-3-generative-ui
- CopilotKit, niveles: https://copilotkit.ai/blog/the-developer-s-guide-to-generative-ui-in-2026
- Perplexity, gráficos financieros: https://alphasignal.ai/news/perplexity-computer-now-renders-live-financial-charts-inside-your-research · https://fxnewsgroup.com/forex-news/platforms/perplexity-computer-integrates-tradingviews-lightweight-charts/
- Bloomberg ASKB: https://www.marketsmedia.com/bloomberg-introduces-agentic-ai-to-the-terminal/
- FLIP / View Transitions: https://aerotwist.com/blog/flip-your-animations/ · https://developer.mozilla.org/en-US/docs/Web/API/Document/startViewTransition · https://developer.chrome.com/blog/view-transitions-in-2025
- WCAG 2.3.3 (animación por interacción): https://w3c.github.io/wcag/understanding/animation-from-interactions.html
- Chat accesible con streaming: https://azukiazusa.dev/en/blog/accessible-streaming-chat-ui

(Algunas páginas oficiales no se pudieron abrir desde el sandbox. Sus datos vienen de extractos de búsqueda; ver `2_patterns.md` §9.)

---

## Apéndice A: JSON Schema completo

La fuente de verdad es **`governance/schemas/kblocks-1.schema.json`** (JSON Schema 2020-12, `$id` `urn:khipus:kblocks:1`). En el repo este documento **no** lleva copia, para que no haya dos versiones que se separen: la entrega de diseño sí la traía, y era idéntica al archivo (lo comprobaba `check_schema.py`).

- Ejemplos válidos e inválidos: `tests/fixtures/genui/examples.kblocks.json`.
- Prueba: `tests/test_genui_schema.py` (esquema válido y sin claves duplicadas, cada ejemplo válido pasa, cada inválido falla, planes válidos e inválidos contra `$defs/Plan`, y que este documento y el esquema digan los mismos 17 tipos).
- Nota sobre `format: "date-time"`: `jsonschema` solo lo comprueba si está instalado `rfc3339-validator`. La prueba no depende de eso: registra su propio comprobador (biblioteca estándar, RFC 3339 con hora y zona). El validador compilado de F1 (`core/genui/validate.py`) debe aplicar la misma regla.
