# 🤖 Conectar IAs a Khipus (servidor MCP)

> **Para Fabrizio, en simple:** MCP es un «enchufe» estándar. Con él, Claude
> (en la web, en el escritorio o en la terminal), ChatGPT, Cursor o un agente
> que programes tú pueden **usar Khipus desde su propia ventana**: buscar
> empresas en el grafo, ver la ficha en vivo, leer la investigación de los
> agentes, calcular el riesgo de una cartera… y, si le das permiso, **proponer**
> órdenes para un cliente. **Ninguna orden de una IA se ejecuta sola**: queda
> esperando que TÚ la apruebes en **👥 Clientes → Aprobaciones**.

---

## 1. Qué hacer ahora (paso a paso)

### Paso 0 — Railway (una sola vez)

Ya deberías tener estas variables; revísalas en Railway → tu servicio →
**Variables**:

| Variable | Para qué | ¿Obligatoria? |
|---|---|---|
| `DATABASE_URL` | Guarda los tokens, el registro y OAuth (Postgres) | **Sí** |
| `TRADE_PIN` | Tu PIN: sin él no se pueden crear conexiones. **Usa 8 caracteres o más, con letras y números** (p. ej. `Khipu-7Rq2m`): un PIN de 4 cifras se puede adivinar | **Sí** |
| `SECRET_KEY` | Firma el formulario de OAuth (pon algo largo y secreto) | Muy recomendado |
| `MCP_PUBLIC_URL` | La dirección pública exacta, p. ej. `https://tu-app.up.railway.app` (si no, se deduce sola). También es el origen de confianza para navegadores | Recomendada |

Después de guardar, Railway redepliega solo (~2 min).

### Paso 1 — Crear una conexión en Khipus

1. Abre Khipus → botón **🩺** (arriba a la derecha, «Sistema») → pulsa la fila
   **🤖 Conectar IAs (MCP)** que está debajo de las pestañas
   Diagnóstico / Registro / Propuestas. (Por consola: `window.KhipuMCP.open()`.)
2. Escribe un nombre, por ejemplo «Claude de Fabrizio».
3. Marca los permisos (ver sección 3). Para empezar: solo **read**.
4. Pulsa **Crear token** → te pide tu PIN de trading.
5. **Copia el token AHORA** (empieza por `kmcp_…`). No se vuelve a mostrar:
   Khipus solo guarda su huella (sha256). Si lo pierdes, revócalo y crea otro.
6. Debajo aparecen las instrucciones ya listas para cada IA, con el token pegado.

### Paso 2 — Pegarlo en tu IA

**Claude Code (terminal):**

```bash
claude mcp add --transport http khipus https://TU-APP/mcp \
  --header "Authorization: Bearer kmcp_TU_TOKEN"
```

**Claude Desktop** (Ajustes → Desarrollador → Editar config →
`claude_desktop_config.json`; necesita Node.js instalado). Reinicia Claude Desktop:

```json
{
  "mcpServers": {
    "khipus": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://TU-APP/mcp", "--header", "Authorization:${KHIPUS_AUTH}"],
      "env": { "KHIPUS_AUTH": "Bearer kmcp_TU_TOKEN" }
    }
  }
}
```

**Cursor** (Settings → MCP → *Add new global MCP server*, archivo `~/.cursor/mcp.json`):

```json
{ "mcpServers": { "khipus": { "url": "https://TU-APP/mcp",
  "headers": { "Authorization": "Bearer kmcp_TU_TOKEN" } } } }
```

**claude.ai (web) o ChatGPT — conector personalizado (usa OAuth, no el token):**

1. claude.ai: **Ajustes → Conectores → Añadir conector personalizado**.
   ChatGPT: **Ajustes → Conectores** (modo desarrollador) → **Crear**.
2. Pega SOLO la URL: `https://TU-APP/mcp`.
3. Se abre una página de Khipus: escribe tu **PIN**, elige los permisos (y el
   cliente si das «trade») y pulsa **Autorizar**.
4. Listo. La conexión aparece en **🩺 → 🤖 Conectar IAs → Conexiones** como
   «OAuth» y puedes revocarla cuando quieras.

**Prueba rápida (curl)** — debe devolver la lista de herramientas:

```bash
curl -s -X POST https://TU-APP/mcp \
  -H "Authorization: Bearer kmcp_TU_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

**Un agente propio con la API de Claude** (el conector MCP de la API: Anthropic
se conecta a Khipus desde sus servidores):

```python
import anthropic

client = anthropic.Anthropic()
resp = client.beta.messages.create(
    model="claude-opus-5-5",
    max_tokens=16000,
    betas=["mcp-client-2025-11-20"],
    mcp_servers=[{"type": "url", "url": "https://TU-APP/mcp", "name": "khipus",
                  "authorization_token": "kmcp_TU_TOKEN"}],
    tools=[{"type": "mcp_toolset", "mcp_server_name": "khipus"}],
    messages=[{"role": "user", "content": "¿Qué proveedores críticos tiene Nvidia y qué riesgo tienen?"}],
)
```

---

## 2. Qué puede hacer la IA (herramientas)

Todo resultado trae `source` (de dónde sale) y `as_of` (cuándo). Si un dato no
existe o no se pudo leer, la herramienta **lo dice** (resultado con
`isError: true`) en vez de inventarlo.

### read — consultar (siempre incluido)

| Herramienta | Qué hace | Fuente |
|---|---|---|
| `search_companies` | Busca empresas por nombre, ticker, alias o palabra clave | Grafo curado (949 nodos) |
| `get_company` | Ficha: rol, foso, estado en bolsa verificado, valuación privada verificada (con URL), **perfil en vivo** (precio, capitalización), NRS y principales proveedores/clientes. `top_suppliers`/`top_customers` = SOLO relaciones de flujo (suministro, fabricación, nube, licencia, energía, propiedad, despliegue); socios e inversores van en `related` (misma forma); cada arista trae `relation_class`, `verified` y `confidence` (0,3 si el texto curado dice "no verificado"/"posible"). `catalog.operating_margin_pct` (misma unidad que `live_market`), `catalog.figures_as_of: null` + `figures_note`: las cifras del catálogo no tienen fecha propia — preferir `live_market` | Catálogo + Yahoo/Finnhub en vivo |
| `get_supply_chain` | Proveedores (`up`), clientes (`down`) o ambos, hasta 2 saltos. `edges` = solo flujo; `related` = partner/invest de la raíz; `include_partners: true` (opcional) los mete también en `edges`; `counts {nodes, edges, related}` | Grafo (source PROVEE a target) |
| `get_ontology_object` | Objeto de la ontología: propiedades, eventos recientes (bitemporales), vínculos y fuentes con confianza. `valid_from_known: false` (+ `valid_from_note_es/en`) cuando la fecha es el centinela 2000-01-01 de la migración ("desde que se rastrea"); `provenance_note`/`provenance_note_es` cuando no hay documento fuente (solo catálogo) | Postgres |
| `get_research` | Claims activas por agente: postura, horizonte, confianza calculada, falsadores, contradicciones y última síntesis (se ocultan las que citan cifras sin respaldo) | Enjambre de investigación |
| `get_claim_evidence` | El «¿por qué?» de una claim: evidencia a favor/en contra con fuente y fecha | Enjambre de investigación |
| `get_research_job` | Estado de una investigación lanzada: `queued` (con `queue_position`) / `running` / `done` / `partial` (algún analista no respondió: `coverage` dice cuáles; la síntesis es incompleta) / `deferred` (sin presupuesto; `resume_after`) / `failed`; `next` dice qué hacer | Enjambre de investigación |
| `get_research_health` | ¿Puedo investigar ahora? Proveedores de IA con clave y en pausa (sin saldo / clave inválida / modelo retirado), cupos en uso, cola, presupuesto diario, reloj del servidor, últimos errores. Sin gasto de IA | Pipeline de investigación |
| `get_risk_report` | VaR 95/99 %, volatilidad, beta, correlaciones de una cartera | Precios diarios reales (Yahoo) |
| `get_option_greeks` | Delta, gamma, vega, theta y escenarios de volatilidad | Black-Scholes + IV en vivo |
| `get_world_events` | Eventos del World Monitor (conflicto, protestas, comercio, sismos, desastres, estrechos, inestabilidad) | GDELT, USGS, NASA EONET… |
| `get_committee_memo` | Último memo del comité de inversión (montos de un cliente ocultos salvo que el token opere ese cliente) | Comité (Phase 3) |
| `get_track_record` | Aciertos, Brier y calibración de cada agente | Predicciones calificadas contra precios reales |

### research — investigar (gasta presupuesto de IA)

| Herramienta | Qué hace |
|---|---|
| `run_research` | Lanza (o reutiliza) una investigación QUICK/STANDARD. `only_missing: true` (opcional) corre SOLO los analistas que faltaron en el último job parcial (`nothing_missing: true` si no falta nadie). Presupuesto diario agotado ⇒ `status: deferred` + `resume_after` (se reanuda solo al día siguiente, máx. 3/día, solo pedidos de personas); con `RESEARCH_DAILY_BUDGET_USD=0` la investigación está apagada y la herramienta lo dice (`budget_exhausted`). |
| `run_committee` | Corre el comité de inversión (en segundo plano) → memo con decisión y tamaño. **Un memo no es una orden.** Si la misma empresa/cliente ya está deliberando (o se decidió hace < 2 min) devuelve ese memo (`reused: true`); como la app, respeta el tope de comités simultáneos (`COMMITTEE_MAX_CONCURRENT`, 2) → `busy`. |

### trade — operar UN cliente, con aprobación humana

Solo aparece si el token tiene `trade` **y** un cliente de corretaje ligado.
La IA solo ve y toca **ese** cliente.

| Herramienta | Qué hace |
|---|---|
| `get_account` / `get_positions` | Patrimonio, efectivo, poder de compra, modo (🧪 PAPEL / 🔴 DINERO REAL) y posiciones, en vivo desde Alpaca |
| `preview_order` | **Propone** una orden: corre los controles de riesgo del cliente (mandato, límites por orden/día/posición, poder de compra, horario, duplicados, interruptor) y la deja **pendiente de aprobación humana**. Exige `rationale` (el porqué, que tú lees antes de aprobar). |
| `submit_order` | Confirma la propuesta. Para una IA **no salta la aprobación**: responde `pending_human_approval` — *«Order queued for human approval in Khipus (👥 Clientes → Aprobaciones)»*. Si la cuenta cambió de modo desde la propuesta (papel → dinero real) no confirma nada (`account_changed`); el corretaje además vuelve a comprobar la auto-aprobación de papel al enviar. |
| `list_orders` / `get_order_status` | Seguimiento (solo del cliente ligado) |
| `cancel_order` | Cancela **solo lo que esa misma conexión propuso**. Una orden puesta por una persona (quizá una orden límite de protección), una propuesta del comité o la de otro agente **no** se cancela desde la IA: la cancela una persona en 👥 Clientes |

---

## 3. Permisos (alcances)

| Alcance | Qué permite | Consejo |
|---|---|---|
| `read` | Consultar todo lo de la tabla «read» | Siempre incluido |
| `research` | Además, lanzar investigación y comité | Cuesta dinero de IA: dáselo a quien lo necesite |
| `trade` | Ver la cuenta y **proponer** órdenes de UN cliente | Exige elegir el cliente; nunca puede aprobar |

Principio: **a cada IA, el mínimo que necesite.** Revocar es inmediato.

---

## 4. Modelo de seguridad

1. **Aprobación humana obligatoria.** Toda orden que venga de MCP (o del comité)
   queda `pending_approval` en **👥 Clientes → Aprobaciones**. Solo una persona
   con el PIN la aprueba o rechaza; recién ahí se envía a Alpaca. Las propuestas
   caducan (`BROKERAGE_APPROVAL_TTL_MIN`, 24 h por defecto).
   - Única excepción, opcional: `BROKERAGE_AUTO_APPROVE_PAPER=on` deja que las
     órdenes de cuentas de **PAPEL** se envíen sin esperar. El **dinero real
     siempre** requiere aprobación.
2. **Controles de riesgo del cliente** antes de proponer y otra vez al ejecutar
   (brokerage/risk.py). El dinero real además exige `BROKERAGE_LIVE_ENABLED=on`
   y «dinero real habilitado» en el cliente.
3. **Interruptores (kill switches):**
   - `MCP_ENABLED=off` → apaga todo el servidor MCP (503).
   - `MCP_TRADING_ENABLED=off` → oculta y bloquea las herramientas de trading por MCP.
   - `BROKERAGE_TRADING_ENABLED=off` → bloquea TODA orden nueva (MCP, comité y UI).
4. **Tokens:** `kmcp_…` de 256 bits; en la base solo su sha256. Revocación
   inmediata (se verifica en cada llamada). Los de OAuth caducan
   (`MCP_OAUTH_TTL_HOURS`, 168 h) y se renuevan con refresh token rotativo.
5. **Límites:** por token `MCP_RATE_PER_MIN` (60/min, contado **por mensaje**:
   un lote de 20 cuenta 20), `MCP_RESEARCH_PER_HOUR` (10/h), `MCP_TRADE_PER_HOUR`
   (30/h en preview/submit/cancel); peticiones **simultáneas** por token
   `MCP_MAX_INFLIGHT` (3) y en total `MCP_MAX_INFLIGHT_TOTAL` (5: el servidor
   tiene 8 hilos y así la app nunca se queda sin ellos) → `429` + `Retry-After`;
   por IP, 30 autenticaciones fallidas / 10 min; 256 KB por petición; lotes ≤ 20
   mensajes y solo con la versión 2025-03-26; `NaN`/`Infinity` se rechazan.
   **PIN** (paneles de MCP y página de OAuth): 5 intentos / 10 min por IP **y un
   bloqueo GLOBAL**: tras `MCP_PIN_MAX_FAILS` (10) PIN incorrectos en una hora,
   TODA comprobación de PIN de MCP se bloquea `MCP_PIN_LOCK_MIN` (30) minutos
   —también con el PIN correcto—, queda en el registro (`pin_check` /
   `pin_lockout`) y en los logs como ALERTA. Rotar IPs o cabeceras no sirve: la
   IP se toma del proxy de confianza (`MCP_TRUSTED_PROXY_HOPS`, 1 = Railway),
   no del primer valor de `X-Forwarded-For`. Si ves un bloqueo que no causaste,
   **cambia `TRADE_PIN`**. Ojo: las rutas de trading de la app (`/api/trade/*`) y
   del corretaje aún usan su propia comprobación de PIN (ver sección 6).
6. **Auditoría:** tabla `mcp_audit` (append-only): hora, conexión, método,
   herramienta, resumen de argumentos **sin secretos** (claves tipo
   token/pin/secret/password/api_key se guardan como `***`), resultado y
   latencia. Visible en **🤖 Conectar IAs → Registro**. El corretaje además
   registra cada orden en `broker_audit`.
7. **Origin (DNS rebinding):** si llega la cabecera `Origin`, debe estar en una
   lista FIJA: el origen de `MCP_PUBLIC_URL`, `https://` + `RAILWAY_PUBLIC_DOMAIN`
   (Railway la pone sola) o `MCP_ALLOWED_ORIGINS` (lista separada por comas;
   `*` = todos). `http://localhost:*` solo se acepta si el propio servidor se
   alcanzó por localhost (desarrollo). **Nunca** se compara con la cabecera
   `Host`: en un ataque de DNS rebinding Origin y Host son ambos el dominio del
   atacante. Opcional: `MCP_ALLOWED_HOSTS` (lista de Host válidos). Los
   conectores de claude.ai/ChatGPT/Claude Code no envían Origin; el MCP
   Inspector del navegador sí (`http://localhost:6274` → añádelo a
   `MCP_ALLOWED_ORIGINS` si lo usas contra producción).
8. **Base caída ≠ token inválido:** si Postgres no responde al validar un token
   (p. ej. mientras Railway lo reinicia) la respuesta es `503` + `Retry-After`,
   nunca `401 invalid_token`: así claude.ai no descarta la conexión.
9. **OAuth:** errores de la petición ANTES del PIN (tipo de respuesta o PKCE
   inválidos) no redirigen solos a la app: se muestra una página con un enlace
   rotulado con el dominio destino (evita usar Khipus como «rebote» hacia
   páginas de phishing). El formulario de permisos se canjea una sola vez; el
   código se consume con un `UPDATE` atómico y, si alguien lo reutiliza, se
   revocan los tokens que ya emitió (OAuth 2.1).
10. **Datos a terceros:** lo que la IA lee (p. ej. el nombre del cliente y sus
   posiciones) viaja al proveedor de esa IA. Los emails y notas del cliente no
   se envían.

---

## 5. Referencia técnica

**Transporte:** MCP *Streamable HTTP* en `POST /mcp`, respuestas
`application/json` (sin SSE). Versiones: **2025-06-18** y **2025-03-26**
(si el cliente pide una soportada se devuelve esa; si no, la más nueva).

| Petición | Respuesta |
|---|---|
| `POST /mcp` `initialize` | `protocolVersion`, `capabilities: {tools: {listChanged: false}}`, `serverInfo {name: "khipus-finance"}`, `instructions`; cabecera `Mcp-Session-Id` |
| `POST /mcp` notificación (`notifications/initialized`) | `202` sin cuerpo |
| `ping`, `tools/list`, `tools/call`, `resources/list`, `resources/templates/list`, `prompts/list` | JSON-RPC 2.0 |
| `GET /mcp` | `405` + `Allow: POST, DELETE, OPTIONS` |
| `DELETE /mcp` | cierra la sesión → `204`; después ese `Mcp-Session-Id` → `404` (el cliente vuelve a `initialize`) |
| sin token / token inválido | `401` + `WWW-Authenticate: Bearer resource_metadata="…/.well-known/oauth-protected-resource/mcp"` |
| base de datos caída al validar el token | `503` + `Retry-After: 30` |
| `MCP-Protocol-Version` no soportada | `400` |
| lote (array) con versión 2025-06-18, o `initialize` dentro de un lote | `400` |
| Origin / Host no permitido | `403` |
| demasiadas peticiones (por minuto o simultáneas) | `429` + `Retry-After` |

`tools/call` devuelve `content: [{type: "text", text: <JSON>}]` +
`structuredContent` (el mismo objeto). Errores de ejecución → `isError: true`
(el modelo los lee). Errores de protocolo → JSON-RPC: `-32700` JSON inválido,
`-32600` petición inválida, `-32601` método inexistente, `-32602` parámetros
inválidos / herramienta desconocida, `-32603` interno. Se aceptan lotes (array)
solo con 2025-03-26 (la 2025-06-18 los eliminó); cada mensaje del lote cuenta
para el límite por minuto y los que se pasan reciben `-32000`.
`Mcp-Session-Id` es opcional: el servidor es sin estado (una sesión
desconocida, p. ej. tras un redeploy, se acepta; una de otro token o ya cerrada
con DELETE → 404).

**Administración** (cabecera `X-Trade-Pin` = `TRADE_PIN`; sin `TRADE_PIN` → 403,
PIN malo → 401, PIN bloqueado → 429 `pin_locked` + `Retry-After`, sin base → 503;
los errores traen `error` (es) y `error_en` (en)):

| Ruta | Qué hace |
|---|---|
| `GET /api/mcp/status` (sin PIN) | disponibilidad, endpoint, versiones, OAuth, límites, orígenes de confianza, `pin_strong` / `pin_locked_s` |
| `GET /api/mcp/tools` (sin PIN) | catálogo de herramientas con su alcance |
| `GET /api/mcp/tokens` | conexiones (sin secretos) |
| `POST /api/mcp/tokens` `{name, scopes[], client_id?}` | crea → devuelve `token` **una vez** (201) |
| `POST /api/mcp/tokens/<id>/revoke` | revoca |
| `GET /api/mcp/audit?limit=&token_id=` | registro de llamadas |

**OAuth 2.1** (para conectores remotos):

| Ruta | Norma |
|---|---|
| `GET /.well-known/oauth-protected-resource[/mcp]` | RFC 9728 |
| `GET /.well-known/oauth-authorization-server` | RFC 8414 |
| `POST /oauth/register` | RFC 7591 (registro dinámico; `redirect_uris` https, http solo loopback, o esquema privado de app) |
| `GET/POST /oauth/authorize` | página bilingüe: PIN → permisos + cliente → código (10 min, un solo uso). PKCE **S256 obligatorio** |
| `POST /oauth/token` | `authorization_code` (+`code_verifier`) y `refresh_token` (rotativo) |
| `POST /oauth/revoke` | RFC 7009 |

Tras aprobar no se hace un 302 desde el POST (la CSP global `form-action 'self'`
lo bloquearía en Chrome): se responde una página que navega al `redirect_uri`.

**Tablas** (en el mismo Base de la ontología; `init_schema` las crea):
`mcp_tokens`, `mcp_audit`, `mcp_oauth_clients`, `mcp_oauth_codes`. Columnas
añadidas después (`mcp_tokens.oauth_code_hash`, `mcp_oauth_codes.consent_nonce`)
se aplican solas con `ADD COLUMN IF NOT EXISTS` la primera vez que hacen falta
(`auth.with_schema`).

**Sin `DATABASE_URL`:** no hay tokens ni OAuth. Opcionalmente
`MCP_STATIC_TOKEN` (≥ 24 caracteres) da acceso de **solo lectura** a las
herramientas que no necesitan base (búsqueda, ficha, cadena de suministro,
riesgo, opciones, eventos mundiales).

**Variables de entorno del MCP:** `MCP_ENABLED`, `MCP_TRADING_ENABLED`,
`MCP_PUBLIC_URL`, `MCP_ALLOWED_ORIGINS`, `MCP_ALLOWED_HOSTS`, `MCP_RATE_PER_MIN`,
`MCP_RESEARCH_PER_HOUR`, `MCP_TRADE_PER_HOUR`, `MCP_MAX_INFLIGHT`,
`MCP_MAX_INFLIGHT_TOTAL`, `MCP_PIN_MAX_FAILS`, `MCP_PIN_LOCK_MIN`,
`MCP_TRUSTED_PROXY_HOPS`, `MCP_OAUTH_ENABLED`, `MCP_OAUTH_TTL_HOURS`,
`MCP_STATIC_TOKEN` (+ `TRADE_PIN`, `SECRET_KEY`, `DATABASE_URL`,
`RAILWAY_PUBLIC_DOMAIN` que pone Railway, y las del corretaje `BROKERAGE_*`).

**Código:** `mcp_server/` (protocol.py, tools.py, auth.py, oauth.py, models.py,
api.py) · UI `engine/mcpconnect.js` · tests `tests/test_mcp.py`.

---

## 6. Qué está verificado y qué NO

**Verificado (en el entorno de desarrollo):**
- `tests/test_mcp.py`: 59 pruebas (protocolo, versiones, errores JSON-RPC,
  auth/401, base caída → 503, revocación, alcances, Origin/DNS rebinding,
  límites por mensaje y simultáneos, bloqueo global del PIN, cierre de sesión,
  NaN/Infinity, auditoría sin secretos, herramientas con datos simulados,
  comité con cupos y reutilización, flujo de trading con un corretaje falso **y
  con el `brokerage/service.py` real** + Alpaca simulado (incluye que un agente
  no puede cancelar órdenes de una persona), OAuth completo con
  PKCE/refresh/revocación, canje simultáneo del código, reutilización →
  revocación, consentimiento de un solo uso, sin «open redirect»).
- Interoperabilidad con el **SDK oficial de MCP para Python (v2.2.0)**: modo
  `auto` y `legacy`, `tools/list`, `tools/call`, errores, y el **flujo OAuth
  completo del SDK** (401 → metadatos → registro dinámico → autorización con PIN
  → token → llamadas). El SDK ofrece 2025-11-25 y acepta nuestra contraoferta
  2025-06-18; su sonda moderna `server/discover` (2026-07-28) recibe
  `-32022` + versiones soportadas y vuelve al `initialize` sin problemas.
- UI en Chromium a 375 px y 1280 px sin scroll horizontal.

**NO verificado todavía:**
- Contra claude.ai, ChatGPT o Cursor reales (requiere la app desplegada con
  HTTPS): hacerlo tras el deploy siguiendo la sección 1.
- Cifras en vivo (Yahoo, GDELT, Alpaca): la red estaba bloqueada en el entorno
  de pruebas; las herramientas lo informan con `available: false` + motivo.
- Sin stream SSE (`GET /mcp` → 405): suficiente para herramientas; no hay
  notificaciones del servidor ni barras de progreso.
- Revisiones 2025-11-25 / 2026-07-28 del protocolo no implementadas (los
  clientes nuevos negocian 2025-06-18). Tampoco «Client ID Metadata Documents»:
  los clientes usan registro dinámico.
- El bloqueo global del PIN vive en memoria (1 worker): un redeploy lo reinicia.
- **Pendiente fuera de este módulo:** `/api/trade/*` (server.py) y las rutas
  del corretaje (brokerage/api.py) comprueban el PIN por su cuenta, sin bloqueo
  global; y `core.http.rate_limit` usa el PRIMER valor de `X-Forwarded-For`
  (lo controla el cliente). Recomendado: que usen `mcp_server.auth.check_pin`
  y `mcp_server.auth.client_ip`.
