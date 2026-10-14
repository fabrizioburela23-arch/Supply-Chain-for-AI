# EXPANSIÓN A ~5.000 EMPRESAS — plan técnico

Fecha: 2026-10-13 · Estado: E0, E1 y E2 (salvo E2.7, el panel) HECHOS el 2026-10-14 (lotes J y K, ver §3); E3-E5 en plan · Base: 4 informes de trabajo medidos sobre el código real
(A = inventario de campos, B = prueba de escala con grafos sintéticos de 5k/10k/20k, C = "en vivo al segundo",
D = tubería de importación). Archivos que acompañan este plan: `company.schema.json`, `plantilla_empresa.json`,
`ejemplo_CATL.json`, `INVESTIGAR_POR_EMPRESA.md`, `PROMPT_INVESTIGACION.md`, `empresas_existentes.csv`.

Origen del pedido: el chat no pudo contestar "¿cuál es la empresa de baterías más grande del mundo?". La causa es
que CATL no es un nodo. Además, no hay categoría de celdas de batería ni un campo de cuota o ranking de mercado.
Medido: el resolvedor devuelve `None` para CATL, 300750.SZ, BYD, LG Energy Solution, Panasonic y Samsung SDI.
Fabrizio pide:

- llegar a ~5.000 empresas;
- una ficha "con todo";
- que lo que cambia sea "en vivo, al segundo".

---

## 0. En corto

- 🟢 **El modelo de datos aguanta 5k sin cambiar de base.** Son 49 MB en Postgres. Ya escalan los eventos
  append-only, el libro, las puertas, las vistas rápidas y el contrato MCP de 12 KB.
- 🔴 **Hay 2 cuellos de servidor**, los dos con arreglo prototipado y medido:
  - kernel en bloques densos: Impact 84 ms → 1,6 s a 5k;
  - tensor con N×N denso: +634 MB y 7 s en la primera ficha tras cada escritura.
- 🔴 **Hay 2 cuellos de navegador**:
  - mapa SVG + d3-force: abrir el mapa tarda 6,4 s, y 27 s en un celular medio;
  - catálogo de 7,5 MB en JS.

  La solución es servir el catálogo por API, calcular el layout en el servidor y dibujar en canvas/WebGL con nivel
  de detalle.
- 🟠 **"Al segundo" es posible solo en parte.**
  - Sí: EE.UU. con Alpaca SIP a US$99/mes, cripto gratis y Europa con plan pago.
  - Asia (TSMC, CATL) llega 20-30 min tarde en las fuentes gratis.
  - Nunca: valuación de privadas ni fundamentales. Se mantienen frescos con disparadores y calendario, con su
    fecha visible.
- 🧾 **Ficha única `khipus.company/1`**: cada dato lleva fuente, fecha y confianza. Los campos en vivo están
  prohibidos (los rechaza el esquema).
- 📥 **Entrada por lotes JSONL**: ensayo → plan con `plan_sha` → PIN → UNA decisión → se puede deshacer.

---

## 1. Línea base medida (937 → 5k sintético, mismo código)

| Pieza | 937 | 5k | Meta 5k | Arreglo |
|---|---|---|---|---|
| Construir Impact (todos los choques) | 84 ms | 1.607 ms | ≤ 150 ms | E1.1 (prototipo: 96 ms, 0 diferencias) |
| Modelo de estructura (tensor) | 422 ms | 6.658 ms / +634 MB | ≤ 150 ms / ≤ 10 MB | E1.2 (prototipo: 85 ms / 4,6 MB) |
| Primera `/api/hot/card` tras una escritura | 316 ms | 6.989 ms | ≤ 500 ms | E1.2 |
| MCP `get_company`, primera llamada | 452 ms | 2.948 ms | ≤ 500 ms | E1.2 |
| Ficha p50 | 0,74 ms | 10,3 ms | ≤ 1 ms | E1.2 (prototipo: 0,31 ms) |
| Pico de memoria del proceso | 168 MB | 1.213 MB | ≤ 350 MB | E1.2 + E1.3 |
| MCP `search_companies` p50 | 50 ms | 224 ms | ≤ 20 ms | E1.5 |
| `build_once` desde Postgres | 397 ms | 2.957 ms | ≤ 1.200 ms | E1.1 + E1.4 |
| Migrar/importar 5k (eventos) | 28 s | 144 s | ≤ 30 s | E2.8 |
| JS del catálogo | 2,1 MB | 7,5 MB | ≤ 250 KB gz por API | E3.1 |
| Khipus OS visible (escritorio / CPU ×4) | 1,34 / 2,76 s | 1,87 / 5,85 s | ≤ 1,6 / ≤ 3,5 s | E3.1 + E3.3 |
| Abrir el mapa (escritorio / CPU ×4) | 0,9 / 3,0 s | 6,4 / 27,4 s | ≤ 1 / ≤ 3 s | E3.4 + E3.5 |
| Arrastrar un nodo | 22 fps | 4 fps | ≥ 30 fps | E3.5 + E3.6 |
| Universo 2D (escritorio / CPU ×4) | 60 / 21 fps | 19 / 5 fps | ≥ 50 / ≥ 20 fps | E3.7 |
| Lo que ya está bien a 5k | impacto precalculado 0,014 ms · escenario 0,2 ms · NRS de todas 159 ms · ρ 14 ms · PageRank 7 ms · detector de contexto 0,34 ms · MCP recortado a ~12 KB | | | — |

Límites honestos de la prueba:

- El grafo sintético es un "levantamiento" del real: conserva ρ = 1,2107. Un 5k real puede encadenar más; la
  variante "hubs crecen" llega a 1.162 empresas afectadas.
- Chromium headless dibuja por software. Los fps solo valen para comparar 937 contra 5k.

---

## 2. Arquitectura objetivo a 5k

```
          investigación (JSONL khipus.company/1)                  proveedores de mercado
                       │                                    Alpaca WS · Finnhub WS · Coinbase WS
                       ▼                                    Alpaca snapshots · Yahoo (lotes)
   /api/ontology/import/plan → apply (PIN, 1 decisión)                    │
                       │                                                   ▼
                       ▼                                       core/live_hub.py (memoria, seq/s)
   Postgres (events append-only, objects/links, instruments,   sellos: src·feed·t_exch·age·
   fundamentals_q, shares_eod, import_*)  ── graph_version ──►  market_state·delay_min·fx.as_of
                       │                                                   │
                       ▼                                                   │
   core/hotviews (UN grafo, UN kernel DISPERSO, tensor disperso,           │
   layout por generación, catálogo compacto)                               │
                       │                                                   │
      /api/hot/catalog|links|card|impact|…  (ETag = generación)    /api/live/delta (1 s, ETag)
                       │                                           /api/live/stream (SSE, opcional, con tope)
                       ▼                                                   ▼
   navegador: adaptador NODES/LINKS ← catálogo compacto · mapa canvas/WebGL con LOD · MKT.quotes ← hub
```

### 2.1 Servidor: un grafo, un kernel disperso

- **Un grafo de lectura.** `core/hotviews/hot.graph()` ya lo es, y ya incluye las empresas que solo están en
  Postgres (`source._reader_graph_pg`). Las importadas aparecen en el MCP, el chat, la ficha y el NRS sin tocar el
  navegador.
- **Kernel disperso.** `propagate_block` trabaja con `csc_matrix` n×k (k = 2.048), en el MISMO orden de operaciones:
  `DT@cur` → `*damping` → `*frag[idx]` → tope 1 → umbral → `eliminate_zeros`.
  - La igualdad es exacta: medido 0 diferencias de impacto y de salto en 937, 5k, 10k y 20k.
  - Una variante que pre-multiplicaba `diag(frag)·Tᵀ·damping` dio diferencias de hasta 1 punto (en el umbral) en 25
    fuentes. **El orden de las operaciones se respeta.**
- **Tensor disperso.**
  - Ψ se arma desde las víctimas de Impact, sin bucle por celda.
  - El perfil `[A|Aᵀ]` es disperso y normalizado por fila.
  - `down_cap = Ψᵀ·cap`, `up_exposure = max(Ψ, axis=1)`, `peers = prof @ prof[j]ᵀ`.
  - Con el kernel 2.0.0 (solo flujo) se borra la segunda pasada `_flow_impact`.
- **El almacenamiento de Impact ya es disperso** (56.546 tuplas, 7 MB a 5k): no se cambia. El top-k por fuente solo
  hace falta si alguna fuente llega a miles de víctimas.
- **Reconstrucción agrupada.** Un lote de importación produce UNA generación, no una por evento.

### 2.2 Datos: la empresa como ficha con procedencia

- **Esquema `khipus.company/1`** (`company.schema.json`, JSON Schema 2020-12, validado):
  - Cada dato es un `fact` `{value, source_url, as_of, confidence, source_kind, quote}`.
  - `additionalProperties:false` rechaza precio, capitalización, EV, múltiplos, volumen, FX, acciones en circulación
    de cotizadas, valuación "en negociación" y NRS.
  - La dirección de los vínculos la deriva el importador desde `this_role`, que se fuerza con `if/then`.
  - La criticidad es de 1 a 6 (la escala de hoy, `max_weight = 6`).
  - **Dependencia por PLANTA y por PIEZA (2026-10-14, pedido de Fabrizio: «no simplificar»)**: cada planta lleva
    `facility_id` (fac-001…) y cada producto `product_id`; `dependency` admite `supplier_facility` /
    `customer_facility` (`facility_ref`: planta concreta con `share_of_flow_pct` — «el 3 nm sale solo de Hsinchu»),
    `component` (la pieza exacta), `product_affected`, `bom_share_pct`, `tier` (1 = directo, 2 = proveedor del
    proveedor…) y `alternatives`. El importador (E2) los guarda como propiedades del vínculo; el kernel sigue usando
    la criticidad como peso (una propagación por planta sería un kernel nuevo: decisión aparte).
  - Secciones: identidad, cotizaciones, clasificación, perfil, estructura, posición de mercado, productos,
    instalaciones, financieros (solo lo que las APIs no dan), rondas, exposición, regulación, riesgos, innovación,
    ESG, línea de tiempo, vínculos y `live_hooks`.
- **Empresa ≠ instrumento.** Las cotizaciones van a la tabla `instruments`, que ya existe. La capitalización se
  calcula sobre el instrumento PRINCIPAL.
- **Unidades explícitas.** Hoy el catálogo mezcla escalas:
  - empleados en miles (211 de 240 en `META_MULTICAPA`);
  - `w` en dos escalas;
  - `margin` 20,25 en Envicool.

  La ficha nueva usa dinero en unidades de su moneda + ISO 4217 + período, % de 0 a 100 y empleados en personas. El
  importador convierte a la convención interna.
- **Fundamentales persistentes.** Tabla `fundamentals_q`, append-only, para que no se pierdan en cada deploy.
  Medido: a 5k el ciclo completo de `live_fundamentals` tarda 10,4 h, y llenarlo de nuevo tras cada push, 3,5 h.

### 2.3 Navegador: catálogo por API

- `GET /api/hot/catalog?gv=` en columnas: `[id, label, cat, sector, country, ticker, grado, x, y, aliases]`. Pesa
  ~120 KB gz a 5k.
- `GET /api/hot/links?gv=` con `[s, t, tipo, w, conf]`: ~81 KB gz.
- ETag = generación, igual que `engine/hotclient.js`. El texto (rol, foso, provee ES/EN) se pide al abrir la ficha
  (`/api/hot/card/<id>`, que ya existe).
- Un **adaptador** mantiene `window.NODES / NODE_BY_ID / LINKS`, porque los leen resolve.js, livesim, xray y otros.
  Funciona así:
  - la semilla JS sigue sirviendo sin conexión;
  - el compacto **añade** ids (nunca pisa);
  - llama a `_invalidateNRS()`.

### 2.4 Mapa: layout en el servidor + canvas/WebGL con nivel de detalle

- Layout calculado UNA vez por `graph_version` en el servidor (por sector y etapa, o el mismo d3-force en node). Va
  como `x, y` en el catálogo, así que el navegador solo dibuja.
- Vista lejana: **13 burbujas de sector** + hubs (top-300 = 38,8 % de los extremos de vínculos; top-600 = 49,2 %).
  Al acercar se abren las empresas del sector visible, y los vínculos se dibujan solo para el vecindario
  seleccionado o el que está bajo el cursor. La escena queda en ~1.000-1.500 elementos, el rango que hoy funciona.
- Física local al arrastrar: solo el nodo y sus vecinos.
- No construir el SVG mientras Khipus OS tapa el mapa. Hoy son 608 ms y 36.000 nodos DOM al arrancar.

### 2.5 En vivo: un centro de cotizaciones en el servidor

- `core/live_hub.py`: UN socket por proveedor, en hilos de fondo (Alpaca stocks, Finnhub trades+FX, Coinbase
  ticker), con barridos REST para los huecos (Alpaca snapshots para todo EE.UU., Yahoo para el resto).
- Guarda el último trade por símbolo, coalescido. La "foto" se publica cada 1 s (`seq`). Medido: ~950k trades/s por
  hilo, así que la CPU no limita.
- **Planificador de suscripciones** (cada 5 s), por prioridad:
  - P0: posiciones, órdenes y alertas;
  - P1: lo visible en pantalla;
  - P2: listas vigiladas;
  - P3: rotación del resto.
- **Entrega por defecto: sondeo de deltas de 1 s** (`GET /api/live/delta?since=<seq>&w=<watch>`, con ETag/304) +
  `POST /api/live/watch` (TTL 30 s). Medido:
  - 50 visores: p95 66 ms;
  - 200 visores: p95 446 ms.
- **SSE solo opcional y con tope.** Medido: cada SSE ocupa un hilo de gunicorn. Con 12 hilos, 12 SSE congelan TODA
  la app. Reglas:
  - `LIVE_SSE_MAX` ≤ `GUNICORN_THREADS/2`;
  - vida de 120 s con `Last-Event-ID`;
  - al pasar el tope → 429 y el cliente vuelve al sondeo;
  - sin gevent.
- **Sello en cada valor**: `{src, feed (sip|iex|delayed15|delayed20|delayed30|eod), t_exch, t_recv, age_s,
  market_state, delay_min, fx:{rate, as_of}}`.
  - `as_of` es la hora del TRADE, nunca la del pedido.
  - `market_state` sale de un calendario de bolsas por MIC.
- **Capitalización = precio local del instrumento principal × acciones del día × FX en vivo.** Se compara a diario
  con el `marketCap` de Yahoo y se marca si difiere más de 2 %.
- **Lo que no puede ser en vivo:**
  - valuación de privadas: un titular (noticias Alpaca/Benzinga + GDELT) crea una PROPUESTA y Fabrizio la aprueba
    con PIN;
  - fundamentales: se refrescan por calendario de resultados;
  - acciones en circulación: a diario.
- **Coherente con ARQUITECTURA_V2 §20.2:** el hub es SOLO una capa de visualización en memoria. No se guardan ticks
  intradía (la historia sigue siendo EOD), hay un solo camino de precios y las órdenes usan la cotización sellada
  (`views/quote.stamped()` lee del hub).

### 2.6 Qué NO hacer (coherente con ARQUITECTURA_V2 §19)

- No sumar una base de grafos ni una vectorial "por escala": 5k = 49 MB. Los cuellos son matrices densas y DOM.
- No subir los workers de gunicorn: duplica la memoria del tensor y rompe el estado en memoria.
- No "arreglarlo" con un plan de Railway más grande. Hobby permite hasta 48 GB / 48 vCPU por servicio, pero a 10k
  serían ~4 GB y a 20k ~10 GB solo para matrices 99,9 % vacías.
- No volver a propagar en el navegador (paso 13).
- No cada cosa como nodo: plantas, productos y personas son propiedades (§19.1). Solo se agregan vínculos a
  objetos que ya existen (Tech, Material, Factor).
- No guardar correlaciones ni ticks intradía.
- No poner cifras vivas en la ficha.

---

## 3. Pasos numerados (cada uno desplegable, con su prueba)

Leyenda: **Archivos** · **Prueba** (fija el comportamiento) · **Meta** (medida a alcanzar) · **Riesgo**.

### Bloque E0 — Medir y blindar (sin cambiar números)

**E0.1 Banco de escala dentro del repo** — ✅ 2026-10-14. `scripts/bench_scale.py` + `scripts/gen_synth_graph.py`
(levanta el catálogo a 5.000: 5.032 ids, 13.487 vínculos, 368 factores; nunca escribe en data/) +
`tests/test_scale_budget.py` (`KH_SCALE=1`) + humo de 2 s a 937 en la suite (`tests/test_scale_hot_bench.py`).

- **Archivos**:
  - `scripts/gen_synth_graph.py` (port de `gen5k.py`: levantamiento + variante de hubs);
  - `scripts/bench_scale.py` (port de `bench_hot.py`);
  - `tests/test_scale_budget.py`, marcado como lento y fuera de la suite rápida.
- **Prueba**: con 5k sintético, las metas de la tabla 1 que ya cumplimos no empeoran.
- **Meta**: reproducir los números de B ±20 %.
- **Riesgo**: tests lentos en CI. Mitigación: correrlo solo con `KH_SCALE=1` o en un job nocturno.

**E0.2 `MATRIX_ENGINE=dense` prohibido por encima de 2.000 nodos** — ✅ 2026-10-14. `DENSE_MAX_NODES`,
`engine.dense_refused()` → aviso en 🩺 Gobernanza; `/api/matrix/parity` (ahora con PIN) tampoco arma el denso arriba
del tope (`dense_refused`).

- **Archivos**: `matrix/engine.py` y el aviso en el 🩺 (`/api/diagnostics`).
- **Prueba**: con 2.001 nodos y `dense`, usa `sparse` y avisa.
- **Meta**: evitar el caso medido de 15 s y 3,6 GB a 5k.
- **Riesgo**: ninguno.

### Bloque E1 — Servidor a 5k

**E1.1 Kernel `propagate_block` disperso** — ✅ 2026-10-14. `_propagate_many_sparse` (bloques CSR n×k de 2.048,
mismo orden de operaciones, modos persistente y no lineal): 0 diferencias en impactos, saltos y orden de inserción
a 937/5k/10k/20k × kernel 1.0.0/2.0.0/2.1.0 (`tests/test_scale_kernel.py`). Medido: kernel 937 46 → 8,5 ms; 5k
1.347 → 42 ms; Impact 5k 1.542 → 105-137 ms ✓. A 20k la vista Impact tardaba ~630-743 ms (meta 500): el bucle de
orden/huella por fuente de `core/hotviews/views/impact.py` se vectorizó en el lote K (orden global con clave compuesta +
argsort estable, conteos por cumsum, GC apagado durante la construcción) → 20k 451-465 ms, 5k 100-104 ms, 937 17-25 ms,
`content_sha` idéntico (tests/test_resolve_ids_impact_perf.py) ✓.

- **Archivos**: `matrix/engine.py` (portar también los modos `persistent`/PROP-08 y `nonlinear`, que el prototipo no
  cubre).
- **Prueba**:
  - `tests/test_hot_views_parity.py` (0 diferencias);
  - `scripts/build_impl_goldens.py --check` (salidas doradas idénticas, así que NO nace `@2`);
  - paridad nueva 5k/10k contra el kernel actual.
- **Meta**: Impact ≤ 150 ms a 5k y ≤ 500 ms a 20k.
- **Riesgo**: cambiar el orden de operaciones da diferencias de ±1 punto en el umbral. Por eso la prueba compara
  impactos Y saltos.

**E1.2 Tensor disperso** — ✅ 2026-10-14. Ψ `SparsePsi`, perfil disperso, HHI por bloques, Ψ de la vista Impact si
ya es solo flujo (`psi_source`), Ψᵀc exacta (math.fsum), empates por id; en suggest_links un grupo empatado en el
corte de N_PEERS entra entero con peso fraccionario (el valor esperado del sorteo de antes, sin sesgo por id).
Medido a 5k: construir 0,9-5,1 s → 96-141 ms ✓; ficha p50 17,4 → 0,40-0,48 ms ✓; primera ficha tras una
escritura 1,3-3,7 s → 213-297 ms ✓; pico del proceso tras 4 generaciones 1.771 → 262-278 MB ✓.

- **Archivos**: `matrix/tensor.py`:
  - Ψ `csc` desde las víctimas;
  - perfil disperso;
  - `peers` disperso;
  - caché de tokens por id;
  - `_flow_impact` se omite si el kernel vigente es solo flujo.
- **Prueba**: con 937, las métricas del tensor (concentración, HHI, país top, `downstream_cap_at_risk`, peers
  top-5) son idénticas al denso (tolerancia 1e-12).
- **Meta**:
  - construir ≤ 150 ms;
  - ficha p50 ≤ 1 ms;
  - primera ficha tras una escritura ≤ 500 ms;
  - RSS +≤ 10 MB.
- **Riesgo**: diferencias por redondeo en los empates de peers. Mitigación: desempate estable por id.

**E1.3 Memoria entre generaciones** — ✅ 2026-10-14. `_KEEP = 2` contando la que se arma; la generación de los
LECTORES (la privada del snapshot si la publicada no sirve) nunca se suelta. Pico del banco a 5k: 177 MB ✓.

- **Archivos**: `core/hotviews/derived.py` (`_KEEP = 2`).
- **Prueba**: dos generaciones seguidas a 5k con pico ≤ 350 MB.
- **Meta**: pico ≤ 350 MB.
- **Riesgo**: ninguno tras E1.2.

**E1.4 Reconstrucción agrupada en escrituras masivas** — ✅ 2026-10-14. Una señal de una versión ya cubierta no
reconstruye; un lector que llega DURANTE la construcción de su versión tampoco; `builder.coalesced()` para lotes en
varias transacciones; sobre con `rebuilding`. 250 vínculos en una transacción = 1 versión, 1 NOTIFY, 1 construcción.

- **Archivos**: `core/hotviews/signals.py`, `builder.py` (un solo NOTIFY por transacción de lote).
- **Prueba**: un lote de 250 fichas = 1 generación.
- **Meta**: ≤ 1 rebuild por lote.
- **Riesgo**: vistas viejas durante el lote. Ya está cubierto por `stale` en el sobre.

**E1.5 Búsqueda por índice** — ✅ 2026-10-14. Índice de prefijos + trigramas por generación en core/entities.py
(`search_scores`); mismos resultados que el recorrido lineal en 213 consultas a 937 y a 5k. `search_companies` p50:
937 39,8 → 0,8 ms; 5k 216 → 2,1-2,6 ms ✓ (p95 3,3-3,6 ms).

- **Archivos**: `core/entities.py` (trigramas + prefijos por generación) y `mcp_server` `search_companies`.
- **Prueba**: en 200 consultas, el top-5 es igual al del recorrido lineal.
- **Meta**: p50 ≤ 20 ms a 5k.
- **Riesgo**: memoria del índice (~5 MB, aceptable).

**E1.6 Resolver por identificadores** (defectos D-5 y D-6) — ✅ 2026-10-14 (lote K). `core/entities.resolve_ids(ids, name)`
(orden lei 100 > isin/cik/qid 99 > figi 98 > símbolo Yahoo 97 > ticker@MIC 96 > dominio solo candidato > nombre ≥ 85; un
ticker a secas nunca; `other_names`/`aliases` entran como alias → «宁德时代» resuelve; un identificador reclamado por dos
empresas = `ambiguous_id`, nunca se elige en silencio). Medido: p50 0,009 ms a 937 y 0,002 ms a 5k (índice por generación,
68 ms a 5k). MCP `search_companies` acepta lei/isin/cik/qid/yahoo_symbol/ticker+mic (también dentro de `query`). El
importador delega siempre en este resolvedor cuando la vista es la vigente. Los listados secundarios declarados (TOELY,
AJINY, SMNEY) siguen resolviendo como ticker blando.

- **Archivos**: `core/entities.py`. Índices `lei/isin/cik/qid/yahoo_symbol` + `aliases` leídos de Postgres; el ticker
  solo resuelve con su bolsa.
- **Prueba**:
  - "3750" sin MIC no resuelve; `3750.HK` sí;
  - "宁德时代" resuelve si está en `other_names`.
- **Meta**: 0 coincidencias entre bolsas.
- **Riesgo**: algún alias de voz deja de resolver. Mitigación: `VOICE_ALIASES` sigue igual.

**E1.7 Paginación y campos a pedido** — ✅ 2026-10-14. `/api/hot/factors?limit&offset&fields` (429 → 51 KB),
`/api/matrix/metrics?top=` (745 → 51 KB), `/api/hot/nrs?ids=` con ETag y tope de 250 ids por GET (línea de pedido
de gunicorn); `KhipuHot.nrs` parte el lote en trozos de 200.

- **Archivos**:
  - `/api/hot/factors?limit&offset` (414 KB a 5k);
  - `/api/matrix/metrics?top=` (745 KB);
  - el cliente usa `/api/hot/nrs?ids=` (lote).
- **Prueba**: forma compatible.
- **Meta**: ninguna respuesta del arranque supera 150 KB.
- **Riesgo**: llamadores viejos. Mitigación: sin parámetros, la respuesta es la de hoy.

**E1.8 Arreglar D-1 y D-2** — ✅ 2026-10-14 (+ parte de D-3). D-1: la propuesta de IncorporarEmpresa lleva
`status: proposed` y confianza 0 (ni lectores ni kernel la cuentan hasta confirmarla) y la respuesta trae su
`link_id`. D-2: la puerta del lote recibe el mismo contexto que G1. D-3 (parcial): la fuente PRINCIPAL citada (la
de más trust) va al evento (`source_id`) con la confianza; la lista queda en el vínculo (`evidenced_by`).

- **Archivos**:
  - `ontology/actions.py` `incorporar_empresa`: `status: 'proposed'`;
  - `ontology/bulk_import._gate_bulk`: pasa evidencia, tipos de extremos, inversos y `dated`.
- **Prueba**:
  - el vínculo propuesto no aparece en `hot.graph()`;
  - 1.000 vínculos con fuente de trust 2 → 0 avisos `high_conf_trusted_source`; hoy hay 19.756 avisos falsos cada
    50.000 vínculos;
  - un País como proveedor → 1 aviso `flow_supplier_type`.
- **Meta**: 0 avisos falsos.
- **Riesgo**: ninguno.

### Bloque E2 — Importación de empresas (diseño D)

**E2.1 Esquema como artefacto** — ✅ 2026-10-14 (lote K). `ontology.import_schema@1.0.0` = company.schema.json; espejo
Pydantic v2 `ontology/company_schema.py` (equivalencia en forma normalizada + 13 negativos: tests/test_import_schema.py).

- **Archivos**:
  - `governance/artifacts/ontology.import_schema@1.0.0.json` (= `company.schema.json`);
  - espejo Pydantic v2 en `ontology/company_schema.py` (`jsonschema` NO está en requirements).
- **Prueba**:
  - `build_governance --check`;
  - `model_json_schema()` es equivalente al artefacto;
  - los 13 negativos (precio, `market_cap`, `shares_outstanding`, criticidad 7, `this_role` incoherente, sin fuente,
    sin fecha, sin inglés, participación de 150 %, puesto de mercado sin rango ni cuota, capacidad sin unidad…) se
    rechazan, y un margen de -250 % se acepta.
- **Meta**: —
- **Riesgo**: que Pydantic y el esquema se separen. Mitigación: la prueba de igualdad.

**E2.2 Normalizar** — ✅ 2026-10-14. `core/import_normalize.py` (países vía `core/countries`; MIC → sufijo Yahoo + moneda;
fechas parciales → inicio/fin sin inventar el día; dinero en unidades; ids CamelCase). Las 136 grafías mapean.

- **Archivos**: `core/import_normalize.py`:
  - una tabla ÚNICA de países ISO → convención del catálogo (hoy hay 136 grafías y `COUNTRY_MAP` está duplicado);
  - MIC → sufijo Yahoo (`core/instruments.SUFFIX`);
  - fechas parciales;
  - moneda.
- **Prueba**: las 136 grafías actuales mapean a ISO.
- **Meta**: —
- **Riesgo**: "Europa"/"RestoMundo" no son países. Se marcan para revisión.

**E2.3 Resolver, planear, aplicar, deshacer** — ✅ 2026-10-14. `ontology/company_import.py` (`resolve_batch`, `plan` PURO con
`plan_sha`, `apply_run` = UNA decisión ontology.bulk_import + UNA transacción + UNA generación, `rollback_run` =
ontology.import_rollback con retracciones dirigidas) + tablas append-only `import_files/import_runs/import_pending_links`
(ontology/import_models.py). Plan del lote 1 (4.174 fichas): 3 s.

- **Archivos**:
  - `ontology/company_import.py` (`resolve_batch` y `plan` PUROS; `apply_run`; `rollback_run`);
  - tablas append-only `import_files`, `import_runs`, `import_pending_links` (`_COLUMNAS_TARDIAS` + `core/ledger_guard`).
- **Prueba**:
  - orden de deduplicación LEI > ISIN/CIK/QID > `yahoo_symbol`/ticker@MIC > dominio (solo candidato) > nombre ≥85;
    con 60-84 = "posible duplicado";
  - ruteo de vínculos (vivo / propuesta / pendiente / cuarentena / variante);
  - deshacer de la corrida más nueva a la más vieja.
- **Meta**: plan de 250 fichas ≤ 10 s.
- **Riesgo**: conflicto con datos curados. Política: listar, nunca pisar (I-2).

**E2.4 Rutas y script** — ✅ 2026-10-14. `/api/ontology/import/files|plan|apply|rollback|runs` (PIN estricto, rate_limit,
`expect.plan_sha` → 409, mismo candado que reconcile, subida en trozos ≤ 900 KB) + `scripts/import_companies.py`
(--lote1 / --plan / --apply --server|--db / --rollback / --runs).

- **Archivos**:
  - `/api/ontology/import/files|plan|apply|rollback|runs` (PIN, `rate_limit`, `expect = plan_sha`, mismo candado
    consultivo que reconcile);
  - `scripts/import_companies.py`;
  - subida en trozos ≤ 900 KB gz (por `MAX_CONTENT_LENGTH` de 1 MB, defecto D-4).
- **Prueba**:
  - si el grafo cambió → 409;
  - sin libro → 503;
  - toda escritura deja UNA decisión `ontology.bulk_import` (`tests/test_cierre_infra.py` no crece).
- **Meta**: —
- **Riesgo**: lote a medias. Mitigación: una transacción por lote.

**E2.5 Gobernanza** — ✅ 2026-10-14. `policy.import@1.0.0`, `ledger.kinds@5.0.0` (ontology.import_rollback),
`ontology.shapes@7.0.0` con `company.ttl` (puerta G-IMPORT, 14 reglas, SOMBRA; conformidad pySHACL en tests/test_import_shapes.py).

- **Archivos**:
  - `policy.import@1.0.0`: umbrales 0,5 / trust 2, lote máx. 250, conflictos = listar, `owns` ≥ 50 %;
  - `ledger.kinds@5.0.0`: `ontology.import_rollback`;
  - `ontology.shapes@7.0.0`: `company.ttl` en sombra.
- **Prueba**: `build_shapes` + conformidad pySHACL ≥ 1.000 focos.
- **Meta**: —
- **Riesgo**: ninguno (sombra).

**E2.6 "¿Qué cambia?" del GRAFO en el plan** — ✅ 2026-10-14. `company_import.kernel_what_changes` (mismo `propagate_many`
sobre una copia: ρ, top-20 cuellos, TSMC antes/después, aviso de kernel.calibration viejo; lote vacío = idéntico; 50 ms a 5k).

- **Archivos**: `company_import.plan`, sobre una copia en memoria con el mismo `propagate_many`. Muestra ρ, el top-20
  de cuellos de botella y a cuántas empresas golpea TSMC, antes y después, y avisa que `kernel.calibration` queda
  viejo.
- **Prueba**: con un lote vacío, el antes y el después son iguales.
- **Meta**: ≤ 3 s a 5k (tras E1.1).
- **Riesgo**: ρ puede subir con los hubs. Hay que verlo antes de aplicar.

**E2.7 Panel 🩺 → 📥 Importar**

- **Archivos**: `engine/importer.js` (subir, plan, aplicar con PIN, deshacer; bilingüe, con "?") + bump de `sw.js` +
  `SHELL`.
- **Prueba**: `node --check` + humo de Playwright.
- **Meta**: —
- **Riesgo**: ninguno.

**E2.8 Escritura por lotes** (arregla también D-3) — ✅ 2026-10-14. `bulk_import.write_events_fast` (executemany por bloques,
mismos eventos que apply_event campo a campo, valid_from/valid_to REALES, source_id/confidence, puertas G-BULK/G1 en bloque).
Medido: 21.000 eventos en 11 s (tests/test_import_fast_path.py con KH_SCALE=1; meta ≤ 30 s); 134 eventos en 0,3 s.

- **Archivos**: `executemany` de eventos en una transacción por bloque (siguen siendo eventos append-only, con UNA
  decisión). Cada vínculo lleva su fecha real: `valid_from` = `start` de la ficha (sin `start` → `GENESIS_SENTINEL`
  con `valid_from_known: false`, nunca "ahora"), `valid_to` = `end`, y `source_id` + `confidence` de su evidencia.
  Hoy `bulk_import._flush_batch` pone `valid_from = ahora` a todo y pierde la fecha (D-3).
- **Prueba**:
  - mismos eventos que el camino `apply_event`, comparados campo a campo;
  - un vínculo con `start: 2021-07` sale en el Grafo Temporal desde 2021-07; uno sin `start` dice "desde que se
    rastrea".
- **Meta**: 21k eventos ≤ 30 s (hoy 144 s).
- **Riesgo**: saltarse las puertas G1. Mitigación: se evalúan en bloque antes de escribir.

**E2.9 Posición de mercado al chat y al MCP** (el motivo del pedido) — ✅ 2026-10-14 (lote K). `views/card.py`
`market_position_of`/`facilities_of` en toda ficha (`/api/hot/card/<id>`, MCP `get_company`); herramienta de lectura
`rank_by_market(market, metric share_pct|rank, region, limit)` en `mcp_server/ops.py` (sinónimos ES/EN, región por
`core/countries`, sin datos → «no tengo ese ranking»); el chat la usa para «¿cuál es la más grande en X?» y la pinta como
`ranking` (intención `market`). Prueba con Postgres en tests/test_genui_k_server.py.

- **Archivos**:
  - `views/card.py` expone `market_position[]` y `facilities[]` con `[F#]`;
  - MCP `get_company`;
  - herramienta de solo lectura `rank_by_market(mercado, métrica, región)`;
  - el `core/context_engine` la usa para preguntas del tipo "la más grande en X".
- **Prueba**: con una ficha de prueba que trae `market_position` rank 1, la pregunta "¿cuál es la empresa de baterías
  más grande?" responde con esa empresa y su fuente y fecha. Sin datos dice "no tengo ese ranking", nunca inventa.
- **Meta**: —
- **Riesgo**: rankings de fuentes distintas que se contradicen. Se muestran todos, con su fuente y métrica.

### Bloque E3 — Navegador a 5k

**E3.1 Catálogo compacto por API + adaptador**

- **Archivos**:
  - `/api/hot/catalog|links` en `core/hotviews/views/`;
  - `engine/catalog.js` (adaptador NODES/LINKS, fusión que solo añade, `aliases` para `engine/resolve.js`);
  - bump de `sw.js`.
- **Prueba**:
  - con 937, NODES/LINKS son idénticos a hoy;
  - una empresa que solo está en Postgres aparece en la búsqueda y en el mapa;
  - `tests/test_no_client_engine.py` sigue verde.
- **Meta**: ≤ 150 KB gz de nodos + ≤ 100 KB gz de vínculos a 5k.
- **Riesgo**: muchos módulos leen las globales. Mitigación: el adaptador las llena antes de `app_main`.

**E3.2 Postgres manda sobre el catálogo** (decisión #7)

- **Archivos**:
  - `scripts/export_catalog_from_pg.py` genera la semilla offline y `data/grafo_v0.json`;
  - una prueba que impide editar `nodes/*.js` a mano;
  - se retiran los `ingest_*.py` que escriben JS.
- **Prueba**: paridad del snapshot generado contra el actual.
- **Meta**: —
- **Riesgo**: producción tiene ~216 objetos que el repo no reconstruye. Por eso es Postgres → repo, nunca al revés.

**E3.3 No construir el mapa tapado**

- **Archivos**: `engine/app_main.js` (las capas SVG o canvas se crean en el primer `_ensureMapSettled`).
- **Prueba**: al arrancar el OS hay 0 elementos del mapa.
- **Meta**: OS visible ≤ 1,6 s (escritorio) / ≤ 3,5 s (CPU ×4) a 5k.
- **Riesgo**: ninguno.

**E3.4 Layout en el servidor**

- **Archivos**: `core/hotviews/views/layout.py` (por generación; coordenadas por sector/etapa + relajación;
  determinista) → `x, y` en el catálogo.
- **Prueba**: misma generación = mismas posiciones.
- **Meta**: abrir el mapa ≤ 1 s (escritorio) / ≤ 3 s (CPU ×4).
- **Riesgo**: el estilo visual cambia. Mitigación: misma paleta y sectores.

**E3.5 Mapa canvas/WebGL con LOD**

- **Archivos**: `engine/app_main.js` (o un módulo de mapa nuevo); base WebGL en `graph3d.js`. Vista lejana = 13
  burbujas + hubs; al acercar se abre el sector visible; vínculos solo del vecindario.
- **Regla del tamaño (Fabrizio, 2026-10-14: «el tamaño de los nodos debe representar su market cap, no ser
  aleatorio»)**: el radio sigue siendo el de `computeNodeRadius` — capitalización EN VIVO (cotizadas), valuación
  VERIFICADA con fecha (privadas) o, si no hay dato, un radio mínimo fijo y marcado «sin capitalización». Nunca por
  grado, nunca aleatorio. Las 5.000 nuevas entran con sus acciones en circulación / capitalización de la fuente (E2)
  para que el mapa las dimensione desde el primer día; las burbujas de sector suman las capitalizaciones conocidas.
- **Prueba**: Playwright — clic en una empresa abre su ficha, y "jumpTo", "activateStress" y livesim siguen
  funcionando.
- **Meta**:
  - ≤ 1.500 elementos dibujados;
  - pintar ≤ 8 ms;
  - arrastre ≥ 30 fps.
- **Riesgo**: es el cambio de interfaz más grande. Mitigación: bandera `kh_map_engine=svg|canvas` como red de
  seguridad (como `kh_desk_mode`).

**E3.6 Física local al arrastrar**

- **Archivos**: `engine/app_main.js`.
- **Prueba**: arrastrar no mueve los nodos lejanos.
- **Meta**: ≥ 30 fps.
- **Riesgo**: ninguno.

**E3.7 Universo 2D con recorte y LOD**

- **Archivos**: `engine/universe2d.js`.
- **Prueba**: dibuja solo lo visible.
- **Meta**: ≥ 50 fps (escritorio) / ≥ 20 fps (CPU ×4).
- **Riesgo**: ninguno.

### Bloque E4 — En vivo (diseño C)

**E4.1 Sellos honestos** (sin proveedor nuevo)

- **Archivos**:
  - `as_of` = hora del precio en `core/company_data.py:1218` y en el resumen MCP (`mcp_server/contract.py:72`
    conserva `market_time`);
  - `core/market_calendar.py`: horarios y feriados por MIC (tabla propia versionada o la dependencia
    `exchange_calendars` con versión fija);
  - `delay_min` por bolsa (.TW/.KS 20, .SZ 30, .AS 15 vía Yahoo);
  - FX con su propio sello;
  - el rótulo "EN VIVO" real en `engine/live.js:123` (verde/ámbar/gris/rojo).
- **Prueba**:
  - un cierre de ayer nunca sale `live: true`;
  - NVDA con la bolsa cerrada → `market_state: closed`.
- **Meta**: 0 sellos con la hora del pedido.
- **Riesgo**: feriados mal cargados. Mitigación: probar contra el calendario oficial de cada bolsa.

**E4.2 Cachés a escala**

- **Archivos**: `core/quotes.py:148` (se vacía con >500) y `:414` (con >5.000) → LRU ≥ 2× el universo.
- **Prueba**: 6.000 símbolos sintéticos → 0 vaciados.
- **Meta**: —
- **Riesgo**: memoria (pequeña).

**E4.3 Fundamentales persistentes**

- **Archivos**:
  - tabla `fundamentals_q` append-only (en `ontology/history_models.py`), con fin de período y fecha de publicación;
  - `core/live_fundamentals.py` lee de ella al arrancar y refresca según el calendario de resultados (Finnhub
    earnings, ya usado en `dispatch_earnings`).
- **Prueba**: tras un reinicio los datos están, sin esperar una tanda.
- **Meta**: 0 h sin márgenes tras un deploy (hoy 3,5 h a 5k).
- **Riesgo**: ninguno.

**E4.4 `core/live_hub.py` + delta**

- **Archivos**:
  - `GET /api/live/delta` y `POST /api/live/watch`;
  - `views/quote.stamped()` lee del hub;
  - barrido REST (Alpaca snapshots + Yahoo) como fuente P3.
- **Prueba**:
  - forma compatible con `/api/quotes/live`;
  - un símbolo sin dato = ausente (nunca inventado);
  - sin claves, el hub arranca igual (patrón opcional).
- **Meta**: con 200 visores, `/api/ping` p95 < 50 ms.
- **Riesgo**: un segundo camino de precios. Mitigación: `/api/quotes/live` delega en el hub.

**E4.5 Sockets en el servidor + planificador P0-P3**

- **Archivos**:
  - `core/live_hub.py`;
  - borrar el WebSocket del navegador (`engine/app_main.js:3637-3660`), `/api/ws-key`, `/api/ws-token` y
    `wss://ws.finnhub.io` del CSP;
  - nueva dependencia `websocket-client` con versión fija en `constraints.txt`.
- **Prueba**:
  - dos navegadores reciben el mismo tick;
  - un 406 de Alpaca espera ≥ 90 s.
- **Meta**: edad ≤ 2 s para P0/P1 con la bolsa abierta.
- **Riesgo**: una sola conexión por cuenta (Alpaca y Finnhub). Mitigación: el hub es el único que conecta.

**E4.6 Capitalización = precio × acciones × FX**

- **Archivos**:
  - `shares_eod` append-only;
  - ADR por `ordinary_per_depositary`;
  - el control diario contra Yahoo (>2 % → bandera).
- **Prueba**: GOOGL+GOOG suman; TSM usa 2330.TW.
- **Meta**: —
- **Riesgo**: datos de acciones de baja calidad fuera de EE.UU. Mitigación: la bandera, no la corrección automática.

**E4.7 SSE opcional con tope**

- **Archivos**: `/api/live/stream`, `LIVE_SSE_MAX` (por defecto 0 = apagado).
- **Prueba**: con el tope lleno, `/api/ping` sigue < 50 ms y la conexión siguiente recibe 429.
- **Meta**: —
- **Riesgo**: congelar la app (medido). Mitigación: el tope ≤ hilos/2.

**E4.8 Valuación de privadas por titulares**

- **Archivos**: filtro de noticias (Alpaca news + GDELT) → propuesta `private_valuations` con URL (PIN).
- **Prueba**: un titular sin cifra no genera propuesta.
- **Meta**: —
- **Riesgo**: falsos positivos. Mitigación: siempre pasan por revisión humana.

**E4.9 Bóveda y documentación**

- **Archivos**:
  - `python scripts/build_vault.py` (rutas y variables nuevas: `LIVE_HUB`, `LIVE_SSE_MAX`, `ALPACA_DATA_FEED`,
    `OPENFIGI_KEY`; tarea `screening_hourly`);
  - `CLAUDE.md` / `docs/ESTADO.md`.
- **Prueba**: `tests/test_vault.py`.
- **Meta**: —
- **Riesgo**: ninguno.

**E4.10 Listas de sanciones cada hora**

- **Archivos**: `core/screening.py` (tarea del `core/scheduler`): baja la Consolidated Screening List de trade.gov (JSON,
  se actualiza cada hora) y la cruza con nombres, `other_names` y país de las 5k.
- **Prueba**: una entrada nueva que nombra a una empresa del grafo crea una PROPUESTA de `regulatory.restricted_lists`
  con fecha y URL (nunca un cambio directo); sin red, la tarea no rompe nada y el 🩺 lo avisa.
- **Meta**: aviso ≤ 1 h después de que la lista cambie.
- **Riesgo**: homónimos (nombres parecidos). Mitigación: nombre + país iguales = propuesta; solo nombre = "posible",
  y siempre lo confirma una persona.

### Bloque E5 — Datos (lo hace la investigación; el código ya está)

| # | Lote | Qué | Prueba de éxito |
|---|---|---|---|
| E5.1 | Lote 0 | Identificadores (LEI/ISIN/CIK/QID/`yahoo_symbol`/dominio) de las 937 existentes, ficha nivel A con `khipus_id_hint` | 0 duplicados en el lote 1 |
| E5.2 | Lote 1 | 🔋 Baterías (250; CATL, BYD, LGES, Panasonic, Samsung SDI…) | El chat responde "la más grande en baterías" con fuente y fecha |
| E5.3 | Lotes 2-15 | Bloques del Prompt B (energía, materiales, equipos…) hasta ~4.000 | Cada lote: plan revisado → aplicar → propuestas revisadas |
| E5.4 | — | Recalibrar `kernel.calibration` (escenario → dinero) tras +4.000 nodos (`/api/governance/propose` + validar) | Ajuste con R² informado; con ajuste débil no se muestra cifra |
| E5.5 | — | Revisar ρ y los cuellos de botella tras cada lote grande | Sin saltos inexplicados |

**Orden recomendado**: E0 → E1 (servidor) → E1.6/E1.8 + E2 (importación) → E5.1 + E5.2 (primer lote real) → E4.1-E4.3
(sellos y persistencia, sin gastar) → E3 (navegador, antes de pasar ~1.500 empresas) → E4.4-E4.6 (hub) + E4.10
(sanciones) → lotes E5.3.
El navegador puede esperar al lote 2 porque el chat, el MCP y las fichas ya ven las empresas importadas.

---

## 4. Lo que decide Fabrizio (con el valor recomendado)

| # | Decisión | Opciones | Recomendado |
|---|---|---|---|
| F-1 | **Plan de datos en vivo** | A gratis · B Alpaca Algo Trader Plus US$99/mes · C B + Finnhub Professional (+US$199,99, ≈US$300/mes en total; verificar) · D C + proveedor Asia (Twelve Data Pro/Ultra +US$229-999; ≈US$530-1.300/mes en total; tiempo real por bolsa NO confirmado) | **A ya; B cuando el hub (E4.5) esté listo** (todo EE.UU. al segundo, sin código nuevo). C/D solo si operas esas bolsas a diario |
| F-2 | **Mostrar precios en vivo a clientes de pago** (/v1, corretaje) | Es redistribución → licencia de negocio (p. ej. Massive Business ~US$2.499/mes) | **No**, hasta tener licencia |
| F-3 | **Excepción a ARQUITECTURA_V2 §20.2** (streaming) | Solo capa de visualización en memoria, sin guardar ticks / No | **Sí, acotada así** |
| F-4 | **#7: Postgres manda sobre el catálogo** | Sí / No | **Sí, antes del lote 2** (sin esto, las importadas no salen en el mapa del navegador salvo con E3.1) |
| F-5 | I-1 Umbral para que un vínculo entre "vivo" | confianza ≥ 0,5 y fuente con trust ≥ 2 | **Ese** (lo demás va a Propuestas) |
| F-6 | I-2 Conflicto con un dato ya curado | listar / pisar si la fuente es más nueva | **Listar siempre** |
| F-7 | I-3 Escala de importancia de los vínculos | 1-6 (la de hoy) / 0-1 | **1-6** por ahora; 0-1 cuando haya % de dependencia suficientes |
| F-8 | I-4 Categorías nuevas (`cat_proposed`) | por lote / una por una | **Por lote**, en el plan |
| F-9 | Vista inicial del mapa a 5k | 13 burbujas de sector / todas las empresas | **Burbujas** (todas = 6-27 s para abrir) |
| F-10 | Claves gratis nuevas | OpenFIGI (clave gratis), `SEC_USER_AGENT` con tu correo | **Sí** (solo identificadores) |
| F-11 | Kernel 2.0.0 antes de la expansión | activar / esperar | **Revisar `/api/governance/preview` tras el lote 1**; con 2.0.0 el tensor ahorra una pasada completa |

---

## 5. Riesgos globales

- **Calidad de la investigación con IA.** Mitigación: el esquema exige fuente, fecha y cita en cada dato; lo dudoso
  entra como propuesta; el guardián de cifras ya existe; `not_found` separa "no hay" de "no buscado".
- **ρ y cascadas más largas con hubs reales.** Medido: con hubs, el alcance máximo es de 1.162 empresas. El
  "¿qué cambia?" de E2.6 lo muestra antes de aplicar; la calibración se rehace (E5.4).
- **Cuotas de proveedores.**
  - Yahoo es no oficial y bloquea por IP. A 5k, el sondeo de hoy haría ~5.000 llamadas cada 5 min por navegador.
    Por eso el hub hace un barrido por servidor, no por navegador.
  - Finnhub y Alpaca permiten 1 conexión por clave.
- **Retraso de origen en Asia/Europa** (20-30 min). No se arregla consultando más seguido. Se dice con `delay_min` en
  la pantalla.
- **Producción tiene ~216 objetos que el repo no reconstruye.** Nunca `REMIGRATE_ON_BOOT`: todo entra por eventos.

---

## 6. Fuentes externas (límites y precios)

Las cifras marcadas "verificar" vienen de páginas oficiales que se contradicen entre sí. Desde este entorno no se
pudo abrir finnhub.io: los límites gratis de Finnhub están confirmados por terceros.

- **Alpaca**: Basic = IEX, 30 símbolos por WebSocket, 1 conexión, 200 llamadas/min; Algo Trader Plus = SIP con
  símbolos ilimitados, US$99/mes.
  - https://docs.alpaca.markets/docs/about-market-data-api
  - https://docs.alpaca.markets/us/docs/streaming-market-data
  - https://docs.alpaca.markets/us/reference/stocksnapshots-1
  - https://docs.alpaca.markets/us/docs/market-data-faq
  - https://forum.alpaca.markets/t/t-error-code-406-msg-connection-limit-exceeded/10896
  - https://forum.alpaca.markets/t/subscribing-for-sip-real-time-data-for-business-account/9860
- **Finnhub**: gratis = 50 símbolos por WebSocket, 1 conexión por clave, ~60 llamadas/min REST. Pagos: US$49,99,
  129,99 y 199,99 al mes (verificar).
  - https://finnhub.io/pricing
  - https://finnhub.io/docs/api/websocket-trades
  - https://github.com/Finnhub-Stock-API/finnhub-js/issues/2
  - https://metacpan.org/pod/Finance::Quote::Finnhub
  - https://nexusfi.com/d/data-providers/finnhub/
- **Massive (ex-Polygon)**: tiempo real en Advanced, US$199/mes; Business US$2.499/mes.
  - https://massive.com/pricing
- **Twelve Data**: Pro US$229 / Ultra US$999 (actualización de mar-2026; verificar).
  - https://twelvedata.com/pricing
  - https://twelvedata.com/news/march-2026-updates
- **Alpaca noticias (Benzinga) por WebSocket** (disparador de valuaciones de privadas, E4.8):
  - https://docs.alpaca.markets/us/docs/streaming-real-time-news
- **Coinbase**: WebSocket público sin autenticación.
  - https://docs.cdp.coinbase.com/coinbase-app/advanced-trade-apis/websocket/websocket-channels
- **Yahoo**: retrasos por bolsa (Taiwán y Corea 20 min, Shenzhen 30 min, Ámsterdam 15 min).
  - https://help.yahoo.com/kb/SLN2310.html
- **OpenFIGI**: anónimo 25 pedidos/min y 10 trabajos por pedido; con clave, 25 cada 6 s y 100 trabajos.
  - https://www.openfigi.com/api/documentation
- **SEC EDGAR**: ≤ 10 pedidos/s con User-Agent declarado.
  - https://www.sec.gov/os/accessing-edgar-data
- **GLEIF**: API gratis del LEI, matrices (nivel 2) y mapeo ISIN↔LEI.
  - https://www.gleif.org/en/lei-data/gleif-api
  - https://www.gleif.org/en/lei-data/lei-mapping/download-isin-to-lei-relationship-files
- **Consolidated Screening List**: JSON, actualización cada hora.
  - https://www.trade.gov/data
- **Railway**: Hobby hasta 48 GB / 48 vCPU por servicio.
  - https://docs.railway.com/reference/pricing/plans
- **Códigos y formatos**:
  - MIC (ISO 10383): https://www.iso20022.org/market-identifier-codes
  - JSON Schema 2020-12: https://json-schema.org/draft/2020-12/release-notes
