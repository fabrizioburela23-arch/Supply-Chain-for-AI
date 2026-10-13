# CIERRE — infraestructura operativa y plan de BRECHAS v2

*Auditoría de cierre del 2026-10-13 (lote H). Todo lo de aquí se comprobó leyendo el CÓDIGO y corriendo pruebas y
mediciones sobre una base nueva con el catálogo migrado (1.066 objetos, 3.041 vínculos vigentes, 69 factores), no
copiando lo que dicen otros documentos. Donde algo no se pudo medir, se dice. La prueba que vigila este documento es
`tests/test_cierre_infra.py`.*

---

## 0. En una frase

Los cuatro pilares que pediste están construidos y funcionando: cada acción importante deja su **ficha** en un libro
que no se puede borrar, las **reglas** revisan cada escritura en una décima de milisegundo, los **números rápidos**
salen de vistas en memoria en menos de 1 ms, y las **reglas y el motor tienen versión** y solo cambian con tu PIN.
Los **8 defectos** que encontró esta auditoría (E1-E8) y los 5 que encontró la revisión del «Repetir» (R2-R6, U1)
**ya están corregidos**, cada uno con su prueba (sección 4). Quedan **10 acciones que todavía no dejan ficha** (lista en
la sección 3: credenciales de IAs externas, voz y simulación por agentes; ninguna toca el grafo ni el dinero; la 11.ª,
la carga a Neo4j, desapareció al retirarlo el 2026-10-13, decisión #6) y
varias cosas que solo tú puedes encender o decidir (sección 6). Lo más importante que falta es tuyo: **activar el motor
2.0.0** (cierra 14 hallazgos de golpe) y **descargar los 5 años de precios**.

---

## 1. Qué hace hoy cada pilar (sin jerga)

**1. Objetos de Decisión — "el libro de decisiones".** Cada vez que alguien hace algo que importa (tú con tu PIN, una
IA conectada por MCP, un agente, o el reloj del servidor), Khipus escribe una **ficha**: quién fue (por ejemplo
`op:fabrizio`; el nombre que se teclea es solo una etiqueta), qué hizo, con qué datos lo hizo (la versión del grafo,
la versión de las reglas, los precios con su fuente y hora), qué reglas avisaron y cómo terminó. La ficha se escribe
**junto con** el cambio: si la ficha no se puede guardar, el cambio no ocurre (con la base caída no salen órdenes:
decisión D4). Las fichas no se pueden editar ni borrar (lo impide la propia base), cada 30 segundos se encadenan con
huellas digitales y una vez al día se guarda una copia de la cabeza de la cadena fuera de la base (GitHub). Si alguien
manipulara la base, se nota y **el dinero real se bloquea** hasta que tú lo reconozcas con PIN (el papel sigue). El
texto privado (preguntas del chat, carteras) se guarda solo como huella; lo del chat y los qué-pasaría-si se vacía a
los 90 días (D3). De las 92 rutas de escritura, hoy 53 dejan ficha: órdenes (las 3 que había + cierre, voz, agente,
MCP y comité, todas por un solo camino), acciones de la ontología (también los eventos crudos, las noticias y la
reconciliación), comité, investigación, propuestas, alertas, gobernanza, chat, MCP, qué-pasaría-si, simulaciones
guardadas e insights. Costo medido: **1,9 ms por acción** (p95 3,0 ms).

**2. Puertas de validación (SHACL).** Las reglas del grafo (un vínculo no puede apuntarse a sí mismo, el peso tiene
que estar en su escala, una orden no puede pasar el tope, un memo del comité tiene que tener quórum…) están escritas
en SHACL, el estándar para describir formas de un grafo, y se convierten a código Python que corre en **0,07 ms**
(p95 0,12 ms; órdenes 0,09 / 0,14 ms). Con pySHACL (la herramienta de referencia) dan 0 diferencias en 7.500 casos.
Hoy están en **SOMBRA**: revisan todo, anotan lo que habrían rechazado (🩺 → «Puertas (7 días)») y no rechazan nada.
Pasan a **bloquear** cuando tú actives `policy.gates 2.0.0` (ver sección 6). Las de órdenes y comité ya están escritas;
corren en sombra cuando actives `ontology.shapes 5.0.0`.

**3. Vistas de camino crítico (hot path views).** El grafo grande (eventos con fecha, procedencia, confianza) sigue
siendo la verdad en Postgres; encima hay **vistas en memoria** con número de versión (el "graph_version", que solo sube
cuando de verdad cambia la estructura) para lo que tiene que ser instantáneo: impacto de una caída, ficha de empresa,
NRS de todas, cuellos de botella, exposición de una cuenta. Medido hoy: **impacto 0,5-0,7 ms** (antes 98 ms), ficha
**0,7 ms**, y todas las pantallas (mapa, X-Ray, Cabina, voz, insights, brief) muestran **el mismo número** porque el
navegador ya no tiene un motor propio (TSMC: 318 empresas golpeadas ≥1 % con el motor 1.0.0). Si una vista se atrasa,
la respuesta lo dice (`stale`) en vez de inventar.

**4. Gobernanza — versiones de las reglas y del motor.** Los números que deciden (el motor de contagio, la fórmula NRS,
los límites del bróker, el tamaño del comité, el guardián de cifras, las puertas, los tipos de ficha, la retención y la
guardia de la base) son **13 artefactos con versión** (1.0.0 = los valores de hoy). Un cambio se propone en la app, se calcula **qué cambiaría**
sobre decisiones reales («¿Qué cambia para mí?», «Regresión»), y solo entra en vigor con tu PIN; deshacer es activar la
versión anterior. Las variables de Railway ya no pueden fijar números (D2): las 3 que todavía lo hacían (E5) pasaron a
`policy.committee 1.1.0` y `policy.broker_risk 1.1.0` con los mismos valores. Cada ficha lleva la versión de reglas que regía, y se puede preguntar **"cómo era el grafo en la
fecha t según lo que sabíamos en el momento κ"** (G(t, κ)). La última pieza — **repetir una decisión pasada y comprobar
que da lo mismo** (paso 24, «Repetir» en 🩺 ⚖ Auditoría) — se terminó en este mismo lote y funciona: los qué-pasaría-si y
el comité se repiten idénticos, y cuando una repetición es «aproximada» la pantalla dice por qué (sección 5).

---

## 2. Cifras medidas de nuevo (base con el catálogo migrado, un proceso, 12 hilos)

| Qué | Medido hoy (2 corridas) | Tope del diseño | ¿Cumple? |
|---|---|---|---|
| Impacto de una caída `GET /api/hot/impact/<id>` (150 empresas) | p50 **0,59-0,71 ms**, p95 0,94-0,98 ms | < 1 ms | ✅ |
| `POST /api/matrix/impact` (delega en la vista + ficha async) | p50 3,9-4,4 ms, p95 7,0-8,8 ms | — (antes 98 ms) | ✅ |
| Ficha `GET /api/hot/card/<id>` repetida | p50 **0,62-0,74 ms**, p95 0,81-1,16 ms | < 1 ms (p50) | ✅ |
| Ficha, primera vez por empresa (vista aún sin precalentar) | p50 1,4-1,9 ms, p95 2,4-8,6 ms, **máx 418-527 ms** (solo la 1.ª tras arrancar) | — | ⚠ arranque en frío |
| Puerta de vínculo compilada | p50 **0,06-0,07 ms**, p95 0,10-0,12 ms | < 1 ms | ✅ |
| Puerta de orden compilada | p50 0,07-0,09 ms, p95 0,12-0,14 ms | < 1 ms | ✅ |
| Puerta de vínculo + lectura del foco en la base | p50 2,4-2,8 ms, p95 3,4-3,9 ms | — | ✅ |
| Costo del libro por acción (`decisions.record` dentro de AnotarObjeto) | p50 **1,9-2,1 ms**, p95 2,8-3,0 ms | p95 < 6 ms | ✅ |
| Acción de ontología completa (AnotarObjeto con PIN) | p50 19-20 ms, p95 26-28 ms | — | — |
| Chat con IA falsa, con libro (async) | p50 **75 ms**, p95 103-145 ms | sin latencia extra | ✅ (+3-4 ms p50, ruido de hilos) |
| Chat con IA falsa, sin escribir fichas | p50 71-72 ms, p95 98-110 ms | — | — |
| «Repetir» un qué-pasaría-si (paso 24), 1.ª vez tras arrancar (reconstruye el grafo de esa versión) | 353 ms | — (no está en el camino del usuario) | ✅ |
| «Repetir» después (grafo ya en memoria) | 32-50 ms; acciones y cambios de reglas 28-36 ms | — | ✅ |
| Muestra nocturna de repeticiones (medida con 20) | 0,45-0,53 s (20 de 20 «idéntico») | — (una vez al día: el reloj mira cada hora y corre en el primer chequeo del día UTC; en producción repite **50 al azar de las últimas 24 h + hasta 300 de dinero**, en su hilo y de a una reconstrucción de grafo por vez: de ~10 s a ~2 min de CPU según cuántas versiones distintas del grafo haya que reconstruir (0,35 s cada una); nunca en el camino del usuario) | ✅ |
| «¿Por qué?» y lista de ⚖ Auditoría | 7 ms cada una | — | ✅ |

Notas honestas: (1) el chat mide ~71 ms y no los "3,4-3,7 ms" que anotó la sesión del paso 20: aquella prueba apagaba
la base de las herramientas; aquí las herramientas leen la base real y esperan en su grupo de hilos. El libro agrega
~4 ms p50 (se escribe después de responder). (2) Todo se midió con el cliente de pruebas de Flask, sin red ni gunicorn.
(3) Las cifras de producción (1.294 objetos) no se pudieron medir: no hay acceso a esa base desde aquí. (4) El sellador
del libro solo sella filas de transacciones ya terminadas en TODO el servidor de Postgres: mientras una transacción larga
siga abierta (una reconciliación grande, una migración) el sellado espera, y sigue solo al terminar. En producción la base
es solo de Khipus, así que no molesta; en las pruebas, con otras bases en el mismo servidor, explica un fallo
intermitente de `tests/test_ai_calls.py` (pasa 4 de 4 veces en una base sola).

Pruebas: tras corregir los defectos de la sección 4, la suite completa con una base nueva da **2.656 aprobadas, 0
fallos** (sin «xfail»: las dos brechas que se probaban así ya dejan su ficha); la única que faltaba era
`tests/test_vault.py`, porque la bóveda se regenera al final, y pasa tras regenerarla. `tests/test_cierre_infra.py`
(ver sección 3) y `tests/test_cierre_defectos.py` (sección 4) son nuevas.

---

## 3. Acciones que todavía NO dejan ficha

Se recorrieron las **92 rutas** que escriben (POST/PUT/PATCH/DELETE) del servidor, de los blueprints y del MCP (hoy
**91**: `POST /api/grafo/seed` se borró con Neo4j el 2026-10-13, decisión #6). A 64
se las llamó de verdad contra la base (sin red ni IA) contando fichas antes y después; las demás (aprobaciones,
gobernanza, OAuth…) se clasificaron leyendo su código y sus pruebas. Resultado:

- **53 dejan ficha** (órdenes, acciones, comité, investigación, alertas, gobernanza, chat, MCP, qué-pasaría-si…; las
  5 últimas —eventos crudos, noticias, reconciliar, deshacer una reconciliación y guardar una simulación— se cerraron al
  final de este lote, defectos E1-E4);
- **28 no la necesitan**: solo leen o calculan (precios en vivo, reportes de riesgo), son respuestas de IA que ya quedan
  en `ai_calls` (análisis, tesis rápida, canvas, consejos de cartera), son tus datos privados del navegador
  (`/api/user-state`, reportes de cartera), sesiones técnicas (`/api/voice/session`, `/api/ws-key`), el chequeo de
  salud `/api/ops/check` (telemetría: escribe su propia fila de control, no toca el libro) o la API pública `/v1/*`
  (intocable);
- **10 cambian algo y NO dejan ficha** (brechas; eran 11 — la 11.ª, `POST /api/grafo/seed`, se borró con Neo4j).
  Ninguna toca el grafo ni el dinero. Están fijadas en
  `tests/test_cierre_infra.py`: una ruta nueva sin ficha rompe la CI, y esta lista solo puede achicarse.

| Ruta | Qué cambia sin ficha | Tipo de ficha que le falta |
|---|---|---|
| `POST /api/sim/agents` | simulación por agentes (qué-pasaría-si con IA) | `whatif.*` |
| `POST /api/mcp/tokens`, `POST /api/mcp/tokens/<token_id>/revoke` | crea/revoca credenciales para IAs externas (pueden tener permiso de órdenes) | nueva (p. ej. `policy.change mcp.tokens`) |
| `POST /oauth/authorize`, `POST /oauth/register`, `POST /oauth/token`, `POST /oauth/revoke` | alta y acceso de IAs externas por OAuth | ídem |
| `POST /api/voice/adopt`, `POST /api/voice/agent-tune`, `POST /api/voice/sync-agent` | cambia la voz, instrucciones y herramientas del agente de ElevenLabs | `policy.change voice.agent` |

Además, 1 tipo de ficha del vocabulario (`core/decisions.KINDS`) no lo escribe ningún código: `reconcile.plan` (ver el
plan es una lectura; también fijado en la prueba, que solo deja achicar esa lista). La guardia de la base
(`kh_require_decision`) vigila 7 tablas pero **no** `events`: que toda escritura del grafo tenga su ficha lo vigila
esta prueba, no la base.

---

## 4. Defectos reales encontrados — todos corregidos al cierre del lote

*(E1-E8 = defectos de esta auditoría; R2-R6 y U1 = de la revisión del «Repetir»; D1-D7 = las decisiones del diseño en
`docs/INFRA_OPERATIVA.md`; #1-#15 = las preguntas de BRECHAS §2.)* Cada arreglo tiene una prueba que fallaba antes;
casi todas están en `tests/test_cierre_defectos.py`.

**E1 · `POST /api/ontology/events` cambiaba el grafo sin ficha.** ✅ Ahora el evento y su ficha `ontology.raw_event`
van en la MISMA transacción (`ontology/api.py events_create`; sin libro → 503 y el evento no se escribe; una puerta
que bloquea → 422 con su ficha). Prueba: `test_cierre_infra.py::test_la_muestra_con_decision_la_deja_de_verdad`
(antes era «xfail») y `test_cierre_defectos.py::test_e1_e3_e4_escrituras_con_su_decision`.

**E2 · Reconciliación sin ficha.** ✅ `ontology/reconcile.py`: cada categoría aplicada deja su `reconcile.apply` en la
transacción de esa categoría (los eventos escritos quedan como sus efectos), y deshacer deja `reconcile.rollback`; un
intento rechazado (otra base, orden equivocado, ya deshecha) también queda, como rechazo. Quien actúa es
`op:fabrizio` desde la app y `system:reconcile_cli` desde la terminal. Prueba:
`tests/test_reconcile.py::test_g3_aplicar_rollback_ida_y_vuelta`.

**E3 · Ingesta de noticias sin ficha.** ✅ `POST /api/ontology/ingest/news` deja `ontology.news_ingest` (misma
transacción; `noop` si todo ya estaba). Prueba: `test_cierre_defectos.py::test_e1_e3_e4_escrituras_con_su_decision`.

**E4 · `POST /api/matrix/simulations` escribía en el grafo sin ficha.** ✅ Deja `simulation.save` en la misma
transacción que el objeto Simulation (sin libro → 503, no se guarda). Sigue sin pedir PIN (guardar una simulación es una
nota, no mueve la versión del grafo y tiene límite de 30 por 10 min), pero ahora queda quién (`ui:anon`) y cuándo.
Prueba: la muestra de `test_cierre_infra.py` y `test_cierre_defectos.py`.

**E5 · Tres variables de Railway todavía fijaban números (contra D2).** ✅ `RESEARCH_CALIBRATION_K` (k = 10),
`RESEARCH_OUTCOME_BAND` (banda 2 %) y `BROKERAGE_APPROVAL_TTL_MIN` (24 h) pasaron a `policy.committee 1.1.0`
(`calibration_k`, `outcome_band`) y `policy.broker_risk 1.1.0` (`approval_ttl_min`), dos versiones MINOR que solo
agregan esas claves con los valores de hoy. Mientras rija la 1.0.0 el código usa ese mismo valor; las variables ya no
cambian nada y el 🩺 avisa si siguen puestas (`core/governance.LEGACY_NUMERIC_ENV`). Prueba:
`test_cierre_defectos.py::test_e5_variables_viejas_no_mandan_y_el_diagnostico_avisa` (+ la del release anterior).

**E6 · Importación circular del libro.** ✅ Los tipos `XID8`/`txid_default` viven en un módulo hoja
(`ontology/sqltypes.py`); `import ontology.ledger_models` primero ya funciona. Prueba:
`test_cierre_defectos.py::test_e6_ledger_models_se_importa_primero`.

**E7 · Todo qué-pasaría-si salía «difiere» por 1 ulp.** ✅ (ya en la primera pasada; sección 5).

**E8 · Leer «Repetir» sin PIN (GET **o** POST, el botón de la pantalla usa POST) escribía una ficha nueva cada vez.** ✅
`core/replay.py _record`: un pedido sin autenticar ya **no** deja `audit.replay` (es una lectura; solo queda el
resultado `replay` deduplicado por decisión, veredicto, código y día). Con PIN, MCP o el reloj: **una** `audit.replay`
por auditor, decisión, veredicto, código y día, también si la respuesta sale de la caché, y aunque el servidor se haya
reiniciado (lo mira en la base). Prueba: `test_cierre_defectos.py::test_e8_replay_anonimo_no_deja_audit_replay_y_con_pin_una_sola`.

**R2 · «¿Por qué?» sin PIN mostraba el ticker de órdenes y memos.** ✅ Sin PIN solo se dice cuántas cotizaciones citó
(`n_quotes`); el detalle (`quotes`) solo con PIN, igual que `/api/ledger/decision/<id>`. Prueba:
`test_cierre_defectos.py::test_r2_por_que_sin_pin_no_muestra_el_ticker`.

**R3 · Un qué-pasaría-si por el camino directo (GRAPH ASOF, vistas apagadas o atrasadas) tomaba la versión del grafo
del sello del libro**, que se escribe después en su hilo: un hecho confirmado entre medio daba un falso «difiere» (y el
🩺 en rojo). ✅ `matrix/api.py _read_version_rr`: el cálculo directo fija su foto de la base y lee la versión del grafo
en esa misma foto; la ficha la guarda (`computed_on`) y el replay la usa. Prueba:
`test_cierre_defectos.py::test_r3_camino_directo_guarda_la_version_leida_al_calcular`.

**R5 · Fichas sin texto de IA explicadas como «texto escrito por la IA».** ✅ Solo se dice «texto de IA» si hay
llamadas de IA registradas (o una ficha vieja que cita su modelo). `mcp.tool_call` es una lectura registrada
(«no es un cálculo»), `chat.route` la decidió Jev (motivo nuevo `external_model`) y el consejo de cartera dice además
que usó datos en vivo. Prueba: `test_cierre_defectos.py::test_r5_sin_llamadas_de_ia_no_se_dice_texto_de_ia`.

**R6 · Un blob de desborde purgado daba «difiere».** ✅ Si las entradas que el replay necesita estaban en el blob de
desborde y se vació (90 días, D3), el veredicto es «no repetible» con su motivo, sin comparar nada. Prueba:
`test_cierre_defectos.py::test_r6_desborde_purgado_es_no_repetible`.

**U1 · «Idéntica» + «aproximada» decía «se reproduce EXACTAMENTE» y no explicaba lo aproximado.** ✅ El texto ahora
dice «mismo resultado, pero aproximada porque …» con el motivo en ES/EN (`core/replay.APPROX_LABELS`), ⚖ Auditoría lo
muestra debajo del veredicto y la etiqueta tiene su «?» (`audit_approx` en `engine/explain.js`). Prueba:
`test_cierre_defectos.py::test_u1_audit_js_explica_la_aproximacion_en_dos_idiomas` y `test_r3_…`.

Menores ya conocidos y verificados de nuevo: el servidor no entiende «en vidia» / «open ai» / «taiwan semi»
(`core.entities.resolve` → None; G5-19); el precio de Gemini 3.8 cambia el 1-ene-2027 y está escrito a mano
(`core/ai_usage.py:48`; L3-16/G5-17); la función de órdenes del navegador sigue dentro de `engine/voice.js:2959`
(M-code-04; ya pasa por el camino único).

---

## 5. Paso 24 (repetir decisiones + ⚖ Auditoría): hecho en este lote

Lo construyó otra sesión en paralelo y se revisó otra vez al final de esta auditoría. **Está en el código**:
`core/impls.py` (las implementaciones retenidas: motor de contagio, NRS, tamaño y decisión del comité, controles del
bróker, guardián de cifras y puertas, cada una con su versión), `core/replay.py`, `GET|POST /api/ledger/replay/<id>`
(sin PIN da un resumen sin datos de clientes y no deja ficha; con PIN el detalle y UNA ficha `audit.replay` por día), `/api/ledger/why/<id>`
(«¿Por qué?»), `/api/ledger/audit` (la lista), la herramienta MCP `replay_decision` (permiso de lectura), la pantalla
🩺 ⚖ Auditoría (`engine/audit.js`, en `sw.js` v263, con sus «?» en `engine/explain.js`) y la muestra periódica
(`ledger_replay_sample` en el reloj del servidor: mira cada hora y corre una vez al día UTC — 50 al azar de las últimas
24 h + hasta 300 de dinero). Cuando una repetición es «aproximada» (por ejemplo, un viaje a una fecha pasada, o una
base restaurada), el veredicto lo dice y explica por qué debajo, con su «?».

Probado a mano sobre la base con el catálogo, repitiendo la última decisión de cada tipo:

| Decisión repetida | Veredicto | Tiempo |
|---|---|---|
| `POST /api/matrix/impact` (TSMC), `POST /api/hot/scenario` (Nvidia), `POST /api/matrix/factor/fire` | **idéntico** (vista reconstruida = la publicada, cálculo 0 diferencias) | 353 ms la 1.ª, luego 32-50 ms |
| Acción de ontología (AnotarObjeto) | **idéntico** (huellas y puertas repetidas; no hay cálculo que repetir) | 35 ms |
| Cambio de límites de IA, importación masiva | **no repetible** con su motivo («no hay un cálculo determinista que repetir; se verificaron sus huellas») | 28-30 ms |
| Comité (`committee.run`, tamaño y decisión) | **idéntico** (primera pasada de la auditoría; aquí no se repitió porque necesita claims de IA) | — |
| Muestra de 20 al azar | 20 de 20 idénticas, 0 «difiere» | 0,45-0,53 s |

El defecto **E7** de la primera pasada de esta auditoría (todo qué-pasaría-si salía «difiere» por una diferencia de
1 ulp en la vista reconstruida, lo que habría puesto el 🩺 en alerta falsa cada día) **ya está corregido**: el orden de los
factores es canónico (`matrix/engine.py`) y una huella de vista distinta queda como «aproximación» visible, no como
veredicto (`core/replay.py` `_view_check`). Queda una nota menor: la ficha `whatif.*` guarda como huella de la vista
`impact` la del vector de resultados del pedido (`matrix/api.py:305-307`), no la de la vista; no produce falsas alarmas.
**E8** (leer «Repetir» sin PIN escribía una ficha cada vez) y los demás defectos de la revisión del replay (R2-R6, U1)
se corrigieron al cierre (sección 4).

---

## 6. Lo que solo tú puedes hacer

**En Railway (variables del servicio):**
1. **`TRADE_PIN`** debe existir. Sin ella, en producción, las escrituras de operador y las órdenes dan 403.
2. **`SECRET_KEY`** larga y aleatoria (G5-18). Ojo: también es la llave de las huellas privadas del libro; ponla una
   sola vez y no la cambies después (las huellas viejas dejarían de compararse con las nuevas).
3. **«Wait for CI»**: Railway → tu servicio → *Settings* → sección *Source* → activa **Wait for CI** (así nada llega a
   producción sin pasar las pruebas de `.github/workflows/ci.yml`; G5-02).
4. Borra las variables numéricas viejas que ya no mandan (el 🩺 avisa si siguen): `FRAGILITY_CAP`,
   `IMPORT_BULK_WEIGHT_FACTOR`, `DECIDE_MIN_CONF`, `DECIDE_WAIT_S`, `COMMITTEE_MEMO_TTL_HOURS`, `RESEARCH_CALIBRATION_K`,
   `RESEARCH_OUTCOME_BAND` y `BROKERAGE_APPROVAL_TTL_MIN` (estas tres últimas desde E5: viven en `policy.committee` y
   `policy.broker_risk` 1.1.0).
5. **Neo4j ya no existe en Khipus** (tu decisión #6, 2026-10-13): en Railway → tu servicio → *Variables* borra
   **`NEO4J_URI`**, **`NEO4J_USER`** y **`NEO4J_PASSWORD`** (nadie las lee; el Grafo Temporal sigue funcionando igual,
   en modo nativo). Opcional: entra a **console.neo4j.io** y pausa o borra la instancia de Aura (no se pierde nada:
   solo recibía copias y nadie la consultaba).
6. En GitHub → *Settings* → *Secrets and variables* → *Actions*: el secreto **`KHIPU_MCP_TOKEN`** (scope read) para que
   la prueba de humo del MCP corra después de cada despliegue. El ancla diaria del libro (decisión D7) NO lo necesita:
   `/api/ledger/anchor` es público y se guarda sola cada día como artefacto de GitHub Actions.

**En la app (el círculo con tus iniciales, arriba a la derecha → «🩺 Sistema» → pestaña «🩺 Diagnóstico» → baja hasta la
caja «⚖ Gobernanza: reglas y motor versionados»; también lo encuentras con ⌘K / Ctrl+K escribiendo «Sistema». En la vista
clásica es el botón 🩺 de la barra):**
1. **«Ratificar (PIN)»** — confirma que los números 1.0.0 vigentes son los aprobados (no cambia ningún número).
2. **Motor 2.0.0** (fila `kernel.params 2.0.0`): «¿Qué cambia para mí?» → «Regresión (PIN)» (espera a que termine) →
   **«Activar (PIN)»**. Cierra 14 hallazgos: socios e inversores dejan de contagiar (tu decisión #4 por defecto),
   severidad 0-10 (#5), un solo motor también para escenarios, auges y simulación por agentes. TSMC pasa de 318 a 254
   empresas golpeadas. Deshacer: «Volver a esta versión (PIN)» en la 1.0.0.
3. **Vocabulario, formas y reglas nuevas, en sombra (no bloquean nada ni cambian números):** activa `ledger.kinds 3.0.0`,
   `ontology.shapes 5.0.0`, `policy.gates 1.1.0`, `policy.committee 1.1.0` y `policy.broker_risk 1.1.0` (cada una:
   «Regresión (PIN)» si la pide → «Activar (PIN)»). Hazlo **antes** de descargar precios: así las puertas de órdenes y
   del comité empiezan a anotar (solo ANOTAN: para que una orden se frene por sector, país o cadena hace falta además que
   fijes esos topes, tu decisión #1, en una versión nueva de las reglas del bróker), y las fichas citan los números de la
   calibración del comité y de la cola de aprobación.
4. **Historia de precios**: en la misma pestaña, caja «📈 Historia de precios» → **«Descargar 5 años (PIN)»** (~115 MB,
   unas horas, gratis; es tu decisión #3). Sin esto el riesgo cambiario, la beta y la calibración usan poca historia.
5. **Una semana después**, si «Puertas (7 días)» no muestra rechazos que te parezcan injustos: activa
   **`policy.gates 2.0.0`** (las puertas de la ontología pasan a bloquear).
6. Cuando la línea **«Guardia»** lleve 7 días en 0: activa **`policy.guard 2.0.0`** (la base rechaza escrituras sin
   ficha en esas 7 tablas).
7. Agente de trading: quedó apagado con aviso tras el despliegue (#14 por defecto). Si lo quieres: abre el panel de
   operar (botón «💹 Operar …» en la ficha de una empresa que cotiza, o dile a Khipu «operar Nvidia») → tarjeta
   «AGENTE IA» → **«▶ INICIAR»** una vez.

**Decisiones y revisiones que siguen abiertas** (BRECHAS §2): #1 topes de tu cuenta (hoy US$100.000 por orden y nada
más), #7 que Postgres mande sobre el catálogo, #8 las listas de `docs/REVISION_GRAFO.md`, #9 las de
`docs/REVISION_INSTRUMENTOS.md`, #10 las fechas propuestas, #11 episodios para calibrar, #12 OK para corregir los números
de `/v1/risk/portfolio`, #13 recalificar predicciones con un método v2, #15 si faltan `find_anomalies` y
`project_portfolio` en el MCP.

---

## 7. Fase 2+ y mi recomendación

Ya hecho de lo que estaba en "Fase 2+": el grafo bitemporal G(t, κ), la historia de propiedades, Δθ en el diff y el
disparador append-only. Lo que queda, en el orden en que lo haría:

1. **Cerrar las 10 brechas que quedan** (≈1 día, sin decisiones tuyas): credenciales MCP y OAuth
   (`policy.change mcp.tokens`), voz (`policy.change voice.agent`) y simulación por agentes (`whatif.*`). Los defectos
   E1-E8 ya están cerrados (sección 4).
2. **Tus dos clics grandes**: motor 2.0.0 y descarga de 5 años (sección 6).
3. **Riesgo con estadística robusta** (L2-14/15/16): EWMA, contracción de Ledoit-Wolf (hoy con muchas posiciones la
   covarianza queda singular), excluir posiciones con poca historia, CVaR a varios días. Necesita la historia del paso 2.
4. **Escenario → pérdida en dinero calibrada** (L2-13, PROP-16): ajustar κ con episodios reales (#11) y con la historia;
   recién ahí "TSMC cae" se traduce a "tu cartera pierde X ± Y".
5. **Dividir los archivos gigantes** (G5-05/06/07): `server.py` 6.529 líneas, `app.html` 12.700, `cockpit.js` 5.007,
   `voice.js` 3.078 — crecieron en este ciclo. Empezar por sacar de `server.py` el agente de trading y las rutas de voz
   a sus blueprints (con pruebas), y dejar `app.html` para el final.

---

## 8. Los 99 hallazgos de BRECHAS v2, uno por uno

Leyenda: ✅ cerrado (con su prueba) · 🟡 listo en el código, **espera tu PIN** (activar una versión) · 🔶 parcial ·
👤 necesita tu decisión o revisión (#n de BRECHAS §2) · ⬜ abierto (Fase 2+ o pendiente).

**Resumen: ✅ 43 cerrados · 🟡 14 listos, esperan tu PIN · 🔶 9 parciales · 👤 10 esperan tu decisión o revisión · ⬜ 23 abiertos (total 99).** Si activas el motor 2.0.0, los 14 🟡 pasan a ✅. L2-M3 (topes por sector, país y cadena) es 👤 #1: sus reglas ya corren en sombra con ontology.shapes 5.0.0, pero ninguna versión existente las hace bloquear hasta que fijes esos topes.

| Id | Qué era | Estado | Evidencia (código / prueba) |
|---|---|---|---|
| PROP-01 | Siete motores daban siete números para la misma caída | 🟡 | Navegador sin motor propio (test_no_client_engine). Con 1.0.0 vigente aún difieren el tensor Ψ (solo flujo), la BFS de escenarios y los % de la simulación por agentes; con kernel.params 2.0.0 todo sale del mismo kernel (test_kernel_reference_figures, test_scenario_kernel) |
| PROP-02 | statematrix.js calculaba distinto que el servidor | ✅ | statematrix.js solo anima; los números vienen de /api/hot/* (test_no_client_engine::test_statematrix_solo_anima) |
| PROP-03 | computeDownstream (cascada sí/no) en banner, brief e insights | ✅ | borrado (test_no_client_engine::test_no_quedan_motores_de_contagio_en_el_cliente) |
| PROP-05 | Severidad 0-10 dividida por 5 → golpes de 160 % | 🟡 | kernel.params 2.0.0: severity_divisor 10 y entradas ≤ 1 (test_kernel_monotone_severity); 1.0.0 vigente conserva /5 |
| PROP-04 | X-Ray con un 55 % inventado | ✅ | quitado (test_no_client_engine::test_sin_cifras_inventadas_ni_parametros_propios) |
| PROP-06 | Ranking de cuellos de botella por conteo, no por golpe | 🟡 | 2.0.0: chokepoint_rank_by=sum (test_kernel_reference_figures::test_escala_0_10_y_ranking_por_suma) |
| PROP-07 | Socios e inversores transmiten daño | 🟡 | 2.0.0: damage_rels solo flujo (test_kernel_reference_figures::test_socios_e_inversores_no_transmiten_dano); decisión #4 por defecto = NO |
| PROP-09 | Escenarios con su propia BFS | 🟡 | 2.0.0: scenario_mode=kernel (test_scenario_kernel); 1.0.0 conserva la BFS |
| PROP-10 | En la simulación por agentes los % los escribe la IA | 🟡 | 2.0.0: sim_pct_source=kernel (test_scenario_kernel::test_2_0_0_simulacion_por_agentes_toma_los_porcentajes_del_kernel) |
| PROP-11 | Sala de guerra con parámetros propios | ✅ | borrada del cliente (test_no_client_engine) |
| PROP-14 | Pesos en dos escalas (400 vínculos) | 👤 #8 | lista de revisión en docs/REVISION_GRAFO.md (test_review_lists); nada aplicado |
| PROP-17 | Auge de demanda sin piso de proveedor único | 🟡 | 2.0.0: direction_up con SOLE_LINK_FLOOR (test_kernel_reference_figures::test_auge_up_con_piso); con 1.0.0 la UI no muestra cifras de auge |
| PROP-18 | Motores leyendo grafos distintos | ✅ | un solo grafo en el servidor: hot.graph() (test_ops_single_source) |
| PROP-08 | Kernel no monótono al agregar aristas | ⬜ | sin cambio en 1.0.0 ni 2.0.0 (x0 sigue sin persistir, matrix/engine.py propagate) |
| PROP-12 | Sin tope de fragilidad en el cliente | ✅ | el cliente ya no calcula; el servidor mantiene FRAGILITY_CAP 2,5 del artefacto (con 2.0.0 ρ 1,21 → 0,91) |
| PROP-13 | Cabina y X-Ray sin factores | ✅ | todas las pantallas leen el kernel del servidor con factores (test_no_client_engine::test_las_pantallas_leen_el_motor_del_servidor) |
| PROP-15 | «Estrés severo» atenuaba | 🟡 | 2.0.0: nonlinear_mode=amplify (test_kernel_monotone_severity::test_estres_severo_amplifica_en_2_0_0_y_satura_en_1_0_0) |
| PROP-16 | Parámetros del kernel sin calibrar | ⬜ | Fase 4: ya existe la tabla de precios, falta la historia (descarga de 5 años) y la calibración |
| PROP-19 | La regla escrita del kernel no coincidía con el código | ✅ | docstring corregido y probado (test_kernel_monotone_severity::test_regla_escrita_suma_dentro_del_salto_maximo_entre_saltos) |
| PROP-20 | Severidad 0 y coeficiente 0 mal tratados | 🟡 | 2.0.0: factor_inputs_strict (test_kernel_monotone_severity::test_entradas_de_factores_cero_y_ausente); 1.0.0 los conserva |
| L2-01 | FX de hoy aplicado a toda la historia | ✅ | FX diario fx_daily + align_fx (test_risk_on_history); la historia larga llega con la descarga de 5 años |
| L2-02 | VaR de /v1/risk/portfolio con pesos al costo | 👤 #12 | server.py _portfolio_risk_impl sin cambios: /v1 es intocable sin tu OK |
| L2-04 | El guardián solo revisaba dinero | ✅ | core/numbers.py por tipo de cifra (test_block0_numbers, test_block0_guardian_corpus) |
| L2-05 | La mitad por historial no validado no siempre se aplicaba | ✅ | tamaño → mitad → tope (test_block0_committee) |
| L2-M1 | Beta de acciones asiáticas ~0 (mismo día calendario) | ✅ | beta de Dimson (test_risk_on_history) |
| L2-06 | Convicción contaba claims, no analistas | ✅ | test_block0_committee |
| L2-07 | Banda fija ±2 % y Brier sobre algo que no es probabilidad | 👤 #13 | research/outcomes.py sin método v2 |
| L2-08 | Dos endpoints de Yahoo = dos fuentes | ✅ | fuentes por proveedor (test_block0_committee, test_block0_review) |
| L2-10 | Totales de griegas mezclan subyacentes; sin dividendos | ⬜ | core/options.py:196-207 sigue sumando delta de todos; q=0 |
| L2-11 | RSI simple en vez de Wilder | ✅ | test_rsi_wilder |
| L2-12 | Sin tabla de precios EOD | ✅ | prices_eod + carga diaria (test_prices_eod); 5 años solo con tu PIN |
| L2-13 | Choques del grafo no se traducen a dinero | ⬜ | Fase 2; necesita episodios (#11) y la historia de precios |
| L2-14 | Una posición corta recorta la ventana de toda la cartera | ⬜ | core/risk_report.py:254 sigue con la intersección de fechas |
| L2-M2 | Deslistadas quedan n/a (sesgo de supervivencia) | ⬜ | research/outcomes.py:403 sigue en n/a |
| L2-M3 | Cada compra se dimensiona sola (sin correlación/sector) | 👤 #1 | reglas de sector/país/cadena con la vista AccountRisk escritas (governance/shapes/order.ttl; test_gates_orders_parity): solo CORREN EN SOMBRA cuando actives ontology.shapes 5.0.0 + policy.gates 1.1.0, y la regla de sector compara contra `kh:maxSectorWeight`, un tope que no existe hasta que respondas #1. Ninguna versión hace bloquear las puertas de órdenes (policy.gates 2.0.0 bloquea solo las de la ontología): bloquear necesita una versión nueva de policy.gates/policy.broker_risk con tus topes |
| L2-03 | Cierres sin ajustar en técnicos y screener | ✅ | adjclose en core/screener.py:83 y research/analytics.py (test_rsi_wilder) |
| L2-09 | Topes rompen la paridad de riesgo pero se rotula risk_parity | ⬜ | core/portfolio_ai.py:704 sin cambio |
| L2-15 | CVaR/VaR solo a 1 día | ⬜ | Fase 2 |
| L2-16 | Faltan EWMA, Ledoit-Wolf, factores, liquidez | ⬜ | Fase 3 |
| L2-17 | Contribución al riesgo vs peso con bases distintas | ✅ | test_block0_committee (portfolio_advisor) |
| L2-18 | Sharpe con retorno geométrico | ⬜ | core/risk_report.py:358 sigue geométrico |
| L2-19 | Se adivinaba si un ratio venía en % o fracción | ✅ | test_analytics, test_block0_committee |
| L3-01 | No existía ninguna tabla de historia | ✅ | prices_eod, fx_daily, metrics_eod, positions_eod, instruments (test_prices_eod, append-only) |
| DT-M1 | Las fechas «since» del catálogo no llegan a valid_from | 👤 #10 | scripts/migrate_v0_to_ontology.py:391 guarda since solo como propiedad |
| DT-M3 | Dos viajes en el tiempo incompatibles (mapa vs servidor) | 🔶 | servidor G(t,κ) listo (test_bitemporal); el deslizador del mapa (engine/maptime.js) sigue con su regla por fundación |
| L3-02 | 27 vínculos fechados entran como supply | 👤 #8 | lista en docs/REVISION_GRAFO.md |
| L3-04 | 97 % de vínculos con fecha centinela | 👤 #10 | fechas propuestas en docs/REVISION_GRAFO.md; nada aplicado |
| L3-05 | No existía G(t,κ) | ✅ | ontology/bitemporal.py, ?known_at= (test_bitemporal, test_bitemporal_review) |
| L3-09 | Tres copias vivas del grafo + Neo4j | 🔶 | el servidor lee una sola (hot.graph); Neo4j retirado el 2026-10-13 (#6, test_neo4j_retirado); catálogo y Postgres siguen separados (#7) |
| L3-11 | Pesos mezclados en dos escalas | 👤 #8 | lista en docs/REVISION_GRAFO.md |
| L3-12 | Direcciones invertidas por texto no detectadas | 👤 #8 | detector en scripts/audit_graph.py + lista (test_review_lists) |
| L3-13 | Empresa = acción | 🔶 #9 | tabla instruments (test_instruments) + docs/REVISION_INSTRUMENTOS.md para que marques |
| L3-14 | Sin historia de tipo de cambio | ✅ | fx_daily (test_prices_eod, test_risk_on_history) |
| DT-M2 | Los nodos no tenían tiempo | ✅ | existencia de nodos en G(t,κ) (test_bitemporal) |
| L3-03 | 58 verbos en español fuera del vocabulario | 👤 #8 | lista en docs/REVISION_GRAFO.md; la migración los sigue excluyendo |
| L3-06 | Propiedades sin historia | ✅ | props_at (test_bitemporal) |
| L3-07 | diff_graph no veía cambios de peso | ✅ | diff con changed (Δθ) (test_bitemporal) |
| L3-08 | events append-only solo por convención | ✅ | disparador kh_append_only (test_ops_events_append_only) |
| L3-15 | Órdenes sin tabla de ejecuciones; posiciones sin historia | ✅ | broker_fills + positions_eod (test_trading_agent_ledger, test_prices_eod) |
| L3-10 | Neo4j recibe escrituras y nadie lo lee | ✅ | retirado el 2026-10-13 por tu decisión #6: sin driver, sin `NEO4J_*`, sin `POST /api/grafo/seed`; el Grafo Temporal es nativo (test_neo4j_retirado) |
| L3-16 | Precio de IA sin fecha de vigencia | ⬜ | core/ai_usage.py:48 (Gemini 3.8 sube el 1-ene-2027; hay que editar a mano) |
| L4-02 | El guardián no veía «233,95 USD» | ✅ | test_block0_numbers, corpus 102 respuestas |
| L4-M1 | El guardián aceptaba ±15 % contra todo el prompt | ✅ | test_block0_numbers |
| L4-01 | Sin motor de contexto único | ✅ | core/context_engine.py (test_context_engine) |
| L4-03 | scenario_exposure propaga por socios/inversores | 🟡 | 2.0.0 (test_scenario_kernel::test_2_0_0_ningun_camino_usa_una_arista_que_no_es_de_flujo) |
| L4-04 | La IA decide los % por empresa | 🟡 | 2.0.0 (igual que PROP-10) |
| L4-05 | Resultados de herramientas duplicados en el prompt | ✅ | test_context_engine |
| L4-08 | MCP sin detail/max_chars (112 k caracteres) | ✅ | contrato MCP (test_mcp_contract): Nvidia prof. 2 = 10 k |
| L4-09 | Faltaban 7 de las 11 operaciones MCP | 🔶 | hay 9 de 11 (get_subgraph, get_history, get_exposure, run_scenario, calculate_correlation, find_similar_entities…); faltan find_anomalies y project_portfolio |
| L4-06 | Sin caché de prompt | ✅ | test_ai_usage_cache, test_ai_calls (solo el nivel profundo llega al mínimo) |
| L4-07 | Respuesta escrita dos veces | ✅ | test_context_engine |
| L4-10 | Compactación sin relevancia | ✅ | test_context_engine |
| L4-11 | Sin pool de evidencia compartido | ✅ | test_context_engine |
| L4-M2 | scenario_engine usa el grado total | 🟡 | 2.0.0 (test_scenario_kernel) |
| L4-12 | La voz repite cifras sin guardián | 🔶 | órdenes por voz con lectura confirmada (readback_sha); las cifras habladas siguen sin guardián |
| G5-01 | Tres caminos de órdenes con controles distintos | ✅ | todo por brokerage.service (test_order_single_path) |
| G5-02 | Se desplegaba sin pruebas | 🔶 #2 | .github/workflows/ci.yml existe (test_block0_ci); falta que actives «Wait for CI» en Railway |
| G5-03 | statematrix.js decía «idéntica» y no lo era | ✅ | test_no_client_engine |
| G5-05 | server.py gigante | ⬜ | 6.529 líneas (antes 5.977): creció |
| G5-06 | app.html gigante | ⬜ | 12.700 líneas (antes 12.665) |
| G5-07 | cockpit.js y voice.js gigantes | ⬜ | 5.007 y 3.078 líneas |
| G5-08 | Tres copias del código que envía órdenes en el navegador | ✅ | test_order_single_path |
| G5-09 | CSP débil con el PIN en localStorage | ⬜ | server.py:691 sigue con unsafe-inline/unsafe-eval |
| G5-10 | El agente de trading se apagaba en silencio | ✅ | queda apagado con aviso y su configuración guardada (test_trading_agent_ledger; decisión #14 por defecto) |
| G5-11 | Tres mecanismos de migración sin versión | 🔶 | columnas tardías + safe_ddl (idempotentes); sigue sin número de versión de esquema |
| G5-12 | Neo4j cableado; la UI no lee Postgres | 🔶 | Neo4j retirado (#6, test_neo4j_retirado); la UI sigue dibujando el catálogo y no /api/ontology/graph (#7) |
| M-code-01 | Ψ decía usar la misma semántica que propagate | 🟡 | Ψ = la vista Impact restringida a flujo; coincide con el impacto solo con 2.0.0 (test_kernel_reference_figures::test_psi_del_tensor_es_la_vista_impact) |
| M-code-02 | Al menos 5 variantes del contagio | 🟡 | con 2.0.0 queda una (test_kernel_reference_figures) |
| M-code-03 | /api/trade/close sin controles | ✅ | test_order_single_path::test_close_leaves_the_same_trail |
| G5-04 | Pesos y lista de flujo copiados a mano en el cliente | ✅ | statematrix sin pesos; NRS_FLOW_TYPES comparado con vocabulary.json (test_cleanup_server) |
| G5-13 | Mapa sin pruebas de comportamiento | ⬜ | 25 módulos sin pruebas (vault/01 Reporte del grafo.md; engine/audit.js de este lote ya tiene la suya en tests/test_cierre_defectos.py) |
| G5-14 | Variables de entorno sin documentar | ⬜ | 64 (antes 63) según la bóveda |
| G5-15 | Globales y rutas sin uso | ⬜ | 9 rutas y 40 globales según la bóveda |
| G5-16 | 37 selectores de idioma propios | ⬜ | Fase 3 |
| G5-17 | Precio de Gemini con vencimiento a mano | ⬜ | igual que L3-16 |
| G5-18 | SECRET_KEY por defecto; /api/trade/status sin PIN | 🔶 #2 | aviso fuerte en producción (server.py:666); /api/trade/status sigue diciendo papel/real sin PIN; confirma SECRET_KEY en Railway |
| G5-19 | El servidor no entiende alias de voz («en vidia») | ⬜ | verificado: core.entities.resolve("en vidia") → None |
| G5-20 | Dos pruebas de navegador de 30 s | ⬜ | Fase 3 |
| M-code-04 | La función de órdenes del navegador vive en voice.js | ⬜ | engine/voice.js:2959 window._executeTradeOrder (ya pasa por el servicio único) |
