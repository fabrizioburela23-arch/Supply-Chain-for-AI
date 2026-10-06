# KHIPUS OS — especificación v1 (2026-10-06)

Pedido de Fabrizio (video "Khipus OS", 32 s; cuadros en
`/tmp/claude-0/-home-user-Supply-Chain-for-AI/1983bd6e-7249-5410-8590-a3ad8207e492/scratchpad/vid/`:
`full_14.png` = pantalla de referencia exacta, `sheet_01..08.jpg` = recorrido completo, `agents.png` = las 6 mascotas):

> "Que el chatbot sea como este, texto al medio y gráficos y otros a los costados. Las pestañas de hoy:
> desplegables mucho más discretas o directamente no estén. Primar la velocidad y la estética. Todo lo que
> construimos es el motor de la nueva estética. Más info o personalización de los agentes (tipos de tablas,
> datos, capacidades) para que tenga sentido tenerlos como usuario. Que pueda invertir el más pro y alguien
> que no sabe nada. Piensa como desarrollador en Apple y como inversionista experto: velocidad y veracidad;
> los errores cuestan dinero, el tiempo es dinero." Tema OSCURO por defecto + botón para cambiar al CLARO
> (el claro = el look del video). Ventanas ordenadas solas (movibles si el usuario quiere). Mascotas burbuja: SÍ.

Khipus OS = la Cabina (engine/cockpit.js + engine/desktop.js) EVOLUCIONADA. No se reescribe desde cero:
todas las escenas, ventanas, adopción de paneles y reglas de dinero siguen igual.

## 1. Lenguaje visual

Referencia: `full_14.png`. Estilo Apple: mucho aire, tarjetas con esquinas grandes, sombras suaves,
tipografía sobria (Geist, ya cargada; números en `font-variant-numeric: tabular-nums`), sin neón.

### Tokens (CSS custom properties) — definidos UNA vez por la Cabina sobre `#bcp-ov`
Claro = `body:not(.dark) #bcp-ov`; oscuro = `body.dark #bcp-ov` (oscuro es el PREDETERMINADO de la app).

| token | claro (video) | oscuro | uso |
|---|---|---|---|
| `--os-bg` | `#EDEDF5` | `#0E0F14` | fondo del escritorio |
| `--os-surface` | `#FFFFFF` | `#17181F` | tarjetas, ventanas, barra superior, chat |
| `--os-surface-2` | `#F2F2F7` | `#1F2029` | rellenos sutiles: burbuja del usuario, chips, pistas de barras |
| `--os-surface-3` | `#E7E7EF` | `#2A2B36` | hover |
| `--os-ink` | `#111216` | `#F2F2F5` | texto principal |
| `--os-ink-2` | `#5B5E6B` | `#A6A8B5` | secundario |
| `--os-ink-3` | `#8D90A0` | `#6E7080` | terciario, ejes |
| `--os-line` | `rgba(17,18,22,.08)` | `rgba(255,255,255,.07)` | bordes |
| `--os-shadow` | `0 1px 2px rgba(17,18,40,.04), 0 8px 28px rgba(17,18,40,.06)` | `0 1px 2px rgba(0,0,0,.4), 0 10px 30px rgba(0,0,0,.35)` | tarjetas |
| `--os-accent` | `#2F6BEA` | `#4C8DF6` | número grande, links, foco |
| `--os-pos` | `#2F6BEA` | `#4C8DF6` | barras a favor |
| `--os-neg` | `#E8623A` | `#F07A52` | barras en contra fuertes / riesgo |
| `--os-mute` | `#C9CAD6` | `#3A3C4A` | barras pequeñas / neutras |
| `--os-good` | `#0ca30c` | `#2fbf5b` | estado bueno (siempre con texto) |
| `--os-bad` | `#d03b3b` | `#f06565` | estado malo (siempre con texto) |
| `--os-btn` | `#111216` | `#F2F2F5` | botón primario (fondo) |
| `--os-btn-ink` | `#FFFFFF` | `#111216` | botón primario (texto) |
| `--os-r` | `18px` | `18px` | radio de tarjetas/ventanas |
| `--os-r-sm` | `12px` | `12px` | radio de chips/botones |
| `--os-font` | `'Geist', system-ui, -apple-system, 'Segoe UI', sans-serif` | idem | |

Reglas: textos SIEMPRE con tokens de tinta (nunca el color de una serie); estados (bueno/malo) siempre
con texto o ícono, nunca solo color; atributos SVG no leen `var()` → leer el token con
`getComputedStyle(el).getPropertyValue('--os-…')` o usar `style="fill:var(--os-…)"` (propiedad CSS sí).

### Mascotas (engine/mascot.js, YA HECHO)
`KhipuMascot.svg(id|seat, size, {state:'idle'|'think'|'talk'})`, `.stack(ids,size)`, `.agents()`, `.of(seat)`,
`.name(id)`, `.color(id)`. Ids: `khipu`, `analista`, `radar`, `cadena`, `tecnico`, `comite`.
Preferencias: `KhipuAgentPrefs.get()/set(patch)/mode()/enabled()/auto(id)`; evento `khipu:agentprefs`.
Mapa puesto→mascota: fundamental/macro→analista · news/geopolitical/crypto→radar · supply_chain→cadena ·
technical/risk/risk_observation/risk_officer/market→tecnico · committee/chair/quant/mandate/all→comite.

## 2. Estructura de pantalla (escritorio ≥ 1100 px)

```
┌ barra superior (#bcp-top, superficie, radio, sombra) ─────────────────────────────────────────┐
│ ◉ Khipus      [ ⌘K  Busca una empresa o abre una pantalla… ]   Más ▾   (●●●●●) 🧪$50.218 ES ☾ FN │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
┌ flanco izq. ─────────┐ ┌ CHAT (columna central, 38 % ancho, 440–680 px) ┐ ┌ flanco der. ─────────┐
│ ventanas en mosaico  │ │ encabezado: mascota Khipu · "5 agentes         │ │ ventanas en mosaico  │
│ (se ordenan solas)   │ │ trabajando contigo" · pila de mascotas          │ │                      │
│                      │ │ hilo (burbuja del usuario a la derecha, gris;   │ │                      │
│                      │ │ Khipu con su mascota a la izquierda)            │ │                      │
│                      │ │ [ Pregúntale a Khipu …                 (◉) ]    │ │                      │
└──────────────────────┘ └─────────────────────────────────────────────────┘ └──────────────────────┘
```
- Sin fila de chips (#bcp-actions oculta): todo se abre con el chat, la paleta ⌘K o "Más ▾".
- Estado vacío del chat (sin mensajes): mascota Khipu grande, "Khipus", "Pregúntale lo que quieras, como a un
  analista.", 4–6 sugerencias, las líneas vivas de hoy (_homeHyper/_homePulse) y la pila de agentes.
- Ventanas: la PRIMERA respuesta abre en el flanco DERECHO, la siguiente en el IZQUIERDO, etc. (equilibrio por
  alto ocupado). Hasta 3 por flanco; las más viejas pasan a la barra (minimizadas). Movibles; "Ordenar" las
  devuelve. Pantallas grandes adoptadas (mapa, terminal, globo) pueden maximizarse sobre todo el escritorio.
- < 1100 px: se vuelve al diseño actual (chat abajo, ventanas al centro). ≤ 760 px: hojas (como hoy).
- Barra superior derecha: pila de mascotas (abre la ventana "Tus agentes"), saldo de práctica con insignia
  🧪/🔴 obligatoria (sin PIN: carteras simuladas; NUNCA pedir PIN desde la barra), ES/EN, ☾/☀ (alterna
  `body.dark` vía `#theme-toggle.click()` para que el mapa también se recoloree), iniciales (de
  `localStorage.khipu_actor`) con menú: modo Simple/Pro, Tus agentes, 🩺 Sistema, Vista clásica.
- Esc NO cierra Khipus OS (cierra la paleta/menú o la ventana enfocada).

## 3. Contratos entre piezas

### 3.1 Registro de ventanas nativas (cockpit.js → otros módulos)
```js
BixbyCockpit.registerKind(kind, {
  icon: '◉',               // emoji o texto corto (la barra de tareas usa textContent)
  es: 'En una mirada', en: 'At a glance',
  multi: true,              // una ventana por empresa (arg.id) → se agrega a multiKinds
  title: function (arg) { return 'Nvidia en una mirada'; },   // opcional (bilingüe por dentro)
  render: function (body, arg) { … }   // pinta SOLO con body.querySelector; puede re-llamarse con otro arg
});
BixbyCockpit.stage(kind, arg)            // abre/enfoca (ya existe)
```
Las ventanas nativas usan los tokens `--os-*` y se ven bien en claro y oscuro. Las escenas viejas con colores
fijos oscuros (broker, scalp, insights, screener, deep, research, agentsim, compare, sim, pick, xray) llevan la
clase `kd-legacy-dark` en el cuerpo de su ventana: en tema claro se ven como una tarjeta oscura (isla), legible.

### 3.2 Respuesta del chat (core/khipu_chat.py) — SOLO SE AGREGAN CAMPOS
Pedido: `{message, history, lang, context:{…, mode:'simple'|'pro', agents_enabled:[ids]}, req_id?}`.
- `GET /api/khipu/chat/progress/<req_id>` → `{req_id, done, elapsed_ms, agents:[{agent, tool, state:'working'|'done'|'error'}]}`
  (en memoria, TTL 5 min, límite de tasa propio, NO usa el de /chat).
- Respuesta suma: `req_id`, `entities:[{id,label}]`, `agents_used:[{agent, tools:[…], ok, note_es, note_en}]`
  (nota DETERMINISTA, armada con datos de las herramientas, nunca texto del modelo), `cards:{company?, committee?}`,
  y `sources[].as_of`.
  - `cards.company = {id,label,symbol,price,change_pct,market_cap_usd_b,source,as_of,nrs,top_suppliers:[{id,label,weight,type}],top_customers:[…],structure:{…}}`
  - `cards.committee = {entity_id,memo_id,status,decision,decision_label_es,decision_label_en,decision_code,overall_conviction,thesis_es:[…],thesis_en:[…],risks_es:[…],risks_en:[…],created_at,expired}`
- Herramienta → agente (cliente y servidor IGUALES): get_company/search_companies/get_research/get_claim_evidence
  → analista; get_supply_chain/rank_companies → cadena; get_news/get_world_events/web_search/scenario_exposure
  → radar; market_movers/get_option_greeks/get_risk_report → tecnico; get_committee_memo/get_conclusions_board/
  get_track_record → comite; ask_agent → según el puesto; el resto → khipu.
- `mode:'simple'` → el prompt pide lenguaje llano, definir cada término y una conclusión clara; `'pro'` → denso,
  cifras, rangos, horizonte. `agents_enabled` → el prompt prioriza herramientas de esos agentes.

### 3.3 Perfiles de agentes
`GET /api/agents/profiles?lang=` (core/agents_api.py, funciona SIN base de datos; con base suma historial):
`{agents:[{id, es, en, role_es, role_en, does_es, does_en, data_es:[…], data_en:[…], outputs_es:[…], outputs_en:[…],
research_types:[…], tools:[…], windows:[kinds], track:{n_scored,hits,hit_rate,brier,reliability,sufficient,note_es,note_en}|null,
stats_30d:{runs,claims,cost_usd,avg_latency_ms}|null}], db:bool, as_of}`.
"Datos que usa" sale de `research/context.py AGENT_NEEDS` (lo que REALMENTE se trae), no de `permitted_tools`.

### 3.4 Ventanas nativas v1 (engine/oswindows.js)
- `glance` (multi) — "<Empresa> en una mirada": número grande = convicción del comité si hay memo vigente
  (cuenta animada desde 0) con píldora "Comité: comprar/mantener/…" o "sin veredicto aún"; si no hay comité,
  el número grande es el PRECIO EN VIVO con su variación y fuente/hora. Pros/contras de memo (thesis/key_risks)
  o del tablero (best_for/best_against); si no hay investigación, de la estructura (tensor: dependencia, riesgo
  aguas arriba) con su fuente rotulada. Botones: "Revisar propuesta" (memo propuesto → KhipuCommittee.open(id)) /
  "Pedir opinión al comité" (sin memo → KhipuCommittee.open(id)), "Ver evidencia" (KhipuResearch.open(id)), "X-Ray".
- `conviction` — "Convicción de tus agentes": barras divergentes −100..+100 de `/api/committee/board` (overall por
  empresa), la empresa pedida resaltada; azul a favor, gris pequeño, naranja en contra fuerte; vacío honesto con
  "Investigar <empresa>" si no hay datos.
- `supplychain` (multi) — "Cadena de suministro de X": proveedores ← empresa (círculo oscuro) → clientes, desde
  window.LINKS (solo tipos de FLUJO, `lid()`, `_canonId`), instantáneo; el riesgo (naranja) = mayores fuentes de
  riesgo del tensor (`/api/tensor/node/<id>`), cargado después.
- `agents` — "Tus agentes": las 6 mascotas con qué hacen, qué datos usan, qué te muestran, historial honesto
  ("sin historial suficiente todavía"), costo 30 d; interruptores "participa" y "abre su ventana sola", modo
  Simple/Pro, botón "Pregúntale" (pone `@agente` en el chat).

### 3.5 Chat (engine/khipu_chat.js)
- Mientras piensa: fila de mascotas que trabajan + "Analista, Cadena y Comité están investigando…"; primero
  una predicción por intención, reemplazada en vivo por el progreso real del servidor; al llegar la respuesta,
  la lista REAL (`agents_used`).
- Respuesta: mascota de Khipu, texto, y debajo una tarjeta con lo que aportó cada agente (mascota + nombre en
  negrita + nota). Fuentes con su hora (`as_of`).
- Ventanas automáticas: si hay `entities[0]` y la Cabina está en modo flancos: `glance` (si auto Analista),
  `supplychain` (si auto Cadena y Cadena participó o la pregunta habla de riesgo/proveedores), `conviction`
  (si auto Comité y hay datos de comité). En ese caso NO se auto-abre además el X-Ray.

## 4. Velocidad y veracidad
- El mapa d3 no se calcula mientras está tapado por Khipus OS (se asienta al mostrarse).
- Sin llamadas duplicadas al arrancar; el brief matinal no se abre solo encima del OS (queda en la paleta).
- Toda cifra viene con fuente y hora; nada inventado; vacíos honestos.

## 5. Reglas que NO se rompen
Dinero (preview→confirm, PIN, insignia 🧪/🔴, el comité solo propone), `kh_desk_mode=off` (Cabina clásica),
bilingüe ES/EN en todo texto nuevo, explicador "?" para métricas nuevas, bump de `sw.js` + SHELL para archivos
nuevos, paneles dentro de `.app`, `/v1` intocable, contratos de respuesta: solo agregar campos.
