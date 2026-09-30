# 👥 Clientes e inversión — corretaje multi-cliente con Alpaca

**Fecha:** 30-sep-2026 · **Módulo:** `brokerage/` + `engine/clients.js` · **API:** `/api/brokerage/*`

> ⚖ **Antes de nada:** operar el dinero de otras personas requiere autorización
> o registro. Lee **[docs/INVERSION_TERCEROS.md](INVERSION_TERCEROS.md)** (memo legal).
> Resumen: cada persona con **SU propia cuenta**, **dinero simulado (papel)** hasta
> que un abogado diga "sí" por escrito, y **sin cobrar** mientras tanto. Esta
> herramienta está hecha para trabajar así: papel por defecto, cada cliente con
> su cuenta, y nada se ejecuta sin que una persona lo apruebe.

---

## 1. Qué es (en simple)

Una pantalla para manejar **varias cuentas de Alpaca a la vez** (una por persona):

- Ves el **patrimonio y las posiciones EN VIVO** de cada cliente.
- Le pones a cada cliente sus **límites** (cuánto por orden, cuánto por día, cuánto
  puede pesar una acción…) y su **mandato** (qué puede y qué no puede comprar).
- Preparas una orden, Khipus la **revisa contra esos límites con la cuenta en vivo**,
  y solo se envía si **marcas «confirmo»**.
- Lo que proponen los **agentes de IA (MCP)** o el **comité de inversión** NO se
  ejecuta solo: espera en **Aprobaciones** a que tú lo apruebes o rechaces.
- Todo queda en un **registro de auditoría** que no se puede borrar.
- Hay un **interruptor general** para frenar todo lo que pasa por este módulo en un segundo.

**Papel 🧪 vs dinero real 🔴.** Papel = cuenta de práctica de Alpaca (dinero
simulado, precios reales). Dinero real necesita **dos candados** a la vez:
(1) en Railway `BROKERAGE_LIVE_ENABLED=on`; (2) en el cliente, «Habilitar dinero
real» (con casilla + confirmación). Si falta uno, la orden se bloquea.

---

## 2. Qué hacer ahora (paso a paso)

### 2.1 Una sola vez, en Railway

1. Entra a **railway.app** → tu proyecto → el servicio de la app → pestaña **Variables**.
2. Verifica que existan **`TRADE_PIN`** (tu PIN de trading) y **`DATABASE_URL`** (la
   pone Railway al tener Postgres). Sin ellas la pantalla muestra el error tal cual.
3. Crea la clave de cifrado de credenciales **`BROKERAGE_ENC_KEY`**. En tu PC
   (Windows, PowerShell) pega:
   ```
   C:\Users\Dell\AppData\Local\Programs\Python\Python311\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
   (si dice que falta `cryptography`: primero
   `C:\Users\Dell\AppData\Local\Programs\Python\Python311\python.exe -m pip install cryptography`).
   Copia el texto que sale (44 caracteres) → en Railway **New Variable** →
   nombre `BROKERAGE_ENC_KEY`, valor = ese texto → **Add**.
   **Guárdalo también en un lugar seguro**: si se pierde, hay que volver a conectar
   las cuentas de todos los clientes. **Sin esta variable (y sin `SECRET_KEY`) la
   app NO deja conectar ninguna cuenta** (ni claves ni OAuth): se cifrarían con una
   clave pública que está en el repositorio.
   Aprovecha y revisa que **`TRADE_PIN` sea largo** (10+ caracteres, no 4 dígitos):
   es lo único que protege aprobar órdenes con dinero de otros.
4. No toques `BROKERAGE_LIVE_ENABLED` (queda apagado = solo papel). Railway
   redespliega solo (~2 min).

### 2.2 Agregar un cliente (en la app)

1. Abre **👥 Clientes e inversión** (botón «👥 Ir a Clientes» del comité, o
   `window.KhipuClients.open()`). Te pedirá tu PIN de trading.
2. **+ Nuevo cliente** → nombre, email, **perfil de riesgo** (conservador /
   moderado / agresivo), **Modo: Papel** → **Crear cliente**.
3. Te lleva a **Detalle**. En **Conectar Alpaca** hay dos caminos:
   - **A. OAuth (recomendado)**: botón «Conectar con Alpaca (OAuth)» → se abre
     Alpaca → la persona entra con SU usuario y autoriza → ve "Cuenta conectada"
     → vuelve a Khipus y pulsa **↻ Actualizar**. (Requiere configurar OAuth, §4.)
   - **B. Claves API**: la persona entra a su Alpaca → cuenta **Paper** →
     *API Keys* → *Generate* → te pasa **API Key ID** y **Secret Key** → las pegas
     → **Guardar claves (cifradas)**. Khipus las verifica con Alpaca y las guarda
     cifradas; nunca más se muestran (solo `****1234`). Las claves de papel solo
     sirven en papel.
4. Pulsa **Leer cuenta en vivo**: verás patrimonio, efectivo, poder de compra y
   posiciones.
5. En **Límites y mandato** ajusta lo que el cliente pidió (o deja el perfil).

La **Cuenta principal** (la tuya, con `ALPACA_KEY`/`ALPACA_SECRET` de Railway)
aparece sola como cliente; su modo lo decide `ALPACA_BASE`.

### 2.3 Hacer una orden

**➕ Nueva orden** → cliente, símbolo (`NVDA`, o cripto `BTC/USD`), comprar/vender,
monto en US$ (o cantidad) → **Previsualizar**. Verás un resumen en palabras
simples y la lista de controles (✓ / ✗ / ⚠). Si todo está ✓: marca **«confirmo»** →
**Enviar orden**. La previsualización caduca en **5 minutos**; al confirmar, los
controles se revisan **otra vez** con datos en vivo, y si la cuenta del cliente
cambió desde la previsualización (otras claves, papel → dinero real) **no se envía**.

- **Vender** lo que el cliente tiene no está limitado por «orden máx.» ni «diario
  máx.» (salir de una posición en una caída no debe tomar varios días).
- **Órdenes límite**: el monto se estima con el precio de MERCADO si es mayor que
  el límite (una venta con límite muy bajo se ejecuta a mercado). Un límite más de
  10 % "del lado caro" (vender muy por debajo / comprar muy por encima del mercado)
  se bloquea como probable error de tipeo; del otro lado solo avisa.
- Si al enviar **se corta la conexión con Alpaca**, la orden queda en **«estado
  desconocido»** (no «falló»): puede haber llegado. NO la repitas: en **🧾 Órdenes**
  pulsa **⇅ Sincronizar**. Khipus la busca en Alpaca por su identificador único y
  la actualiza; si nunca llegó, pasa a «falló» a los 2 minutos y ya se puede repetir.

### 2.4 Aprobar lo que proponen los agentes o el comité

**✅ Aprobaciones** (el número naranja = pendientes). Cada tarjeta dice quién lo
propuso (🤖 agente MCP / 🏛 comité), el resumen, el motivo y los controles.
**Aprobar y enviar** o **Rechazar** (con motivo). Las propuestas caducan a las
24 h (`BROKERAGE_APPROVAL_TTL_MIN`).

### 2.5 Seguir las órdenes

**🧾 Órdenes** → filtra por cliente → **Sincronizar con Alpaca** actualiza los
estados (enviada → ejecutada…). **Cancelar** en las que siguen abiertas.

### 2.6 Emergencia: apagar todo

Railway → Variables → `BROKERAGE_TRADING_ENABLED` = `off`. Desde ese momento
**ninguna orden nueva sale de 👥 Clientes, de agentes (MCP) ni del comité**. Las ya
enviadas a Alpaca se cancelan a mano en **Órdenes**. Para volver: `on`.
Para frenar a UN solo cliente: **Detalle → ⏸ Pausar**.

⚠ **Alcance:** las rutas clásicas `/api/trade/*` (panel de trading de la cuenta
principal, voz de Khipu, ficha cripto) y el **agente de trading automático** de
`server.py` NO pasan por este módulo: este interruptor solo los frena si
`server.py` consulta `brokerage.risk.trading_enabled()` en `trade_order` y
`_agent_place` (pendiente de conectar por quien mantiene `server.py`). Hasta
entonces, para frenarlos también: detén el agente desde su panel y quita
`TRADE_PIN` (sin PIN, todas las rutas de trading responden 403).

---

## 3. Límites de riesgo (se revisan en cada orden)

| Control | Qué revisa | Bloquea |
|---|---|---|
| Interruptor general | `BROKERAGE_TRADING_ENABLED` ≠ off | sí |
| Modo | papel, o dinero real con los dos candados | sí |
| Estado del cliente | activo (no pausado) | sí |
| Cuenta | conectada, legible en vivo, no bloqueada por Alpaca | sí |
| Símbolo | válido (`NVDA`, `BRK.B`, `BTC/USD`) y clase de activo permitida por el mandato | sí |
| Mandato | no está en «prohibidos»; si hay lista cerrada, está en ella | sí |
| Tamaño de orden | compras: entre US$1 y «orden máx.» (tope absoluto US$100.000); ventas: mínimo US$1, sin tope (el tope es lo que se tiene) | sí |
| Límite diario | COMPRAS enviadas hoy + esta compra ≤ «diario máx.» (día de mercado de Nueva York); las ventas no cuentan | sí (compras) |
| Dinero disponible | la compra cabe en el EFECTIVO: mín(efectivo, poder de compra); cripto: `non_marginable_buying_power`. Solo con «Permitir margen» en el mandato se usa el poder de compra con préstamo de Alpaca | sí (compras) |
| Tamaño de posición | después de comprar, la acción pesa ≤ «posición máx.» % del patrimonio | sí (compras) |
| Stop por caída | patrimonio no cayó más de X % desde su máximo | sí (solo compras; vender sigue permitido) |
| Tenencia | no se vende lo que no se tiene (sin cortos) | sí (ventas) |
| Duplicado | no hubo la misma orden (cliente/símbolo/lado) en los últimos 60 s | sí |
| Orden sin confirmar | no hay una orden igual en «estado desconocido» (hay que sincronizar antes) | sí |
| Precio límite | límite a ≤ 10 % del mercado del lado caro | sí (del lado barato solo aviso ⚠) |
| Horario | mercado de EE.UU. abierto (reloj de Alpaca) | no — solo aviso ⚠ |

**Perfiles** (rellenan lo que no pongas a mano):

| Perfil | Posición máx. | Orden máx. | Diario máx. | Stop por caída | Activos |
|---|---|---|---|---|---|
| Conservador | 10 % | US$1.000 | US$2.500 | 10 % | acciones EE.UU. |
| Moderado | 20 % | US$5.000 | US$15.000 | 20 % | acciones + cripto |
| Agresivo | 35 % | US$25.000 | US$75.000 | 35 % | acciones + cripto |

El «máximo» del stop por caída es el patrimonio más alto que Khipus vio. Se
**reinicia solo** cuando cambia la cuenta conectada (claves nuevas, OAuth, papel →
real, cambio de `ALPACA_BASE`/`ALPACA_KEY` en la cuenta principal). Un **retiro** de
dinero también lo baja → usa «Reiniciar máximo».

---

## 4. Configurar OAuth de Alpaca ("Alpaca Connect")

Así la persona autoriza a Khipus desde SU cuenta, sin darte claves, y puede
revocar el acceso cuando quiera.

1. Entra a **app.alpaca.markets** con tu usuario.
2. Busca la sección de **OAuth Apps / Alpaca Connect** (en el menú de la cuenta;
   *los nombres de menú pueden cambiar — verificar*) → **Create New App**.
3. Completa nombre ("Khipus"), descripción, sitio web, y en **Redirect URI** pon
   EXACTAMENTE: `https://<tu-dominio-de-railway>/api/brokerage/oauth/callback`
   (tu dominio lo ves en Railway → Settings → Domains).
4. Alpaca te da un **Client ID** y un **Client Secret**. En Railway → Variables:
   - `ALPACA_OAUTH_CLIENT_ID` = el Client ID
   - `ALPACA_OAUTH_CLIENT_SECRET` = el Client Secret
   - `ALPACA_OAUTH_REDIRECT_URI` = la MISMA URL del paso 3
5. Tras el redespliegue, en 👥 Clientes la píldora dice «OAuth Alpaca: listo».

⚠ Para **papel** funciona de inmediato. Para operar **dinero real de otras
personas**, Alpaca debe **aprobar tu app** (ver memo legal, opción D).

---

## 5. Auditoría

Tabla `broker_audit` (solo se AGREGA, nunca se modifica ni se borra — lo IMPONE
un trigger de Postgres: cualquier `UPDATE`, `DELETE` o `TRUNCATE`, incluso desde una
consola, da error; solo el dueño de la base podría quitar el trigger a propósito): creación
y cambios de cliente, conexión de credenciales (solo `****1234`, jamás la clave),
OAuth, previsualizaciones, aprobaciones, rechazos, envíos a Alpaca, fallos,
cancelaciones, sincronizaciones, habilitar/deshabilitar dinero real. Se ve en
**Detalle → Registro de auditoría** o `GET /api/brokerage/audit`.

---

## Apéndice técnico

### Archivos

| Archivo | Rol |
|---|---|
| `brokerage/models.py` | tablas `broker_clients`, `broker_orders`, `broker_audit`, `broker_oauth_states` (en `ontology.models.Base`; `init_schema` las crea) |
| `brokerage/crypto.py` | Fernet (`BROKERAGE_ENC_KEY` o derivada de `SECRET_KEY` con aviso), `mask()`, firma HMAC del `state` OAuth |
| `brokerage/alpaca.py` | cliente `requests` (timeouts 12 s), auth `APCA-API-KEY-ID/SECRET` o `Bearer`, **solo hosts `paper-api`/`api.alpaca.markets`**, OAuth authorize/exchange |
| `brokerage/risk.py` | controles pre-orden, perfiles, interruptores por entorno |
| `brokerage/service.py` | contrato compartido (lo usan api, comité y MCP) |
| `brokerage/api.py` | blueprint `/api/brokerage/*` (registrado en server.py) |
| `engine/clients.js` | UI `window.KhipuClients.open(tab?, clientId?)` |
| `tests/test_brokerage.py` | 47 tests (bróker falso + respuestas grabadas) |

### Variables de entorno

| Variable | Default | Efecto |
|---|---|---|
| `DATABASE_URL` | — | obligatoria (sin ella: 503) |
| `TRADE_PIN` | — | obligatoria para toda ruta salvo `/status` y `/oauth/callback` (sin ella: 403; PIN malo: 401). Usa 10+ caracteres |
| `BROKERAGE_ENC_KEY` | derivada de `SECRET_KEY` | clave Fernet de las credenciales. Si tampoco hay `SECRET_KEY` (clave pública por defecto) NO se guardan credenciales (`encryption_key_missing`) |
| `BROKERAGE_TRADING_ENABLED` | `on` | `off` = interruptor general de este módulo (👥 Clientes, MCP, comité; ver §2.6 para `/api/trade/*`) |
| `BROKERAGE_LIVE_ENABLED` | `off` | primer candado del dinero real |
| `BROKERAGE_AUTO_APPROVE_PAPER` | `off` | `on` = propuestas MCP/comité de clientes **en papel** no esperan humano (dinero real SIEMPRE espera). Se vuelve a comprobar AL CONFIRMAR: si ya no aplica (variable apagada, cuenta cambiada), pasa a la cola humana o se rechaza |
| `BROKERAGE_APPROVAL_TTL_MIN` | `1440` | caducidad de propuestas pendientes |
| `ALPACA_OAUTH_CLIENT_ID` / `_SECRET` / `_REDIRECT_URI` | — | activan OAuth |
| `ALPACA_KEY` / `ALPACA_SECRET` / `ALPACA_BASE` | — | cuenta de la casa → cliente `house` «Cuenta principal» |

### Endpoints (`/api/brokerage`)

`GET /status` (sin PIN: solo `{available, trading_enabled}`) · `GET /status/detail` (PIN: dinero real, OAuth, cifrado, auto-aprobación) ·
`GET|POST /clients` · `GET|PATCH /clients/<id>` ·
`POST /clients/<id>/credentials` `{api_key, api_secret, env}` ·
`POST /clients/<id>/oauth/start` `{env}` → `{url}` · `GET /oauth/callback` (sin PIN; HTML bilingüe) ·
`GET /clients/<id>/account` · `POST /clients/<id>/sync` · `GET /clients/<id>/audit` · `GET /audit` ·
`POST /orders/preview` · `POST /orders/<id>/confirm` `{confirm:true, actor}` · `GET /orders?client_id=&status=&limit=` ·
`POST /orders/<id>/cancel` · `GET /approvals` · `POST /approvals/<id>/approve` `{actor}` · `POST /approvals/<id>/reject` `{actor, reason}`.
Códigos: 400 datos inválidos · 404 no existe · 409 ya usada / requiere aprobación / estado inválido / cuenta cambiada /
nombre ambiguo o repetido · 410 caducada · 403 origen distinto · 422 bloqueada al confirmar · 429 PIN bloqueado ·
502 error de Alpaca o estado desconocido (`code: unknown_state`). Todo error trae `error` (es) y `error_en` (en).

### Contrato `brokerage.service` (para comité y MCP; importarlo perezoso y tolerar ImportError)

`available()` · `list_clients(s)` · `get_client(s, id_o_nombre)` · `account_snapshot(s, id)` ·
`preview_order(s, client_id, symbol, side, notional=None, qty=None, order_type='market', limit_price=None, source='ui'|'mcp'|'committee', requested_by='', proposal_id=None, rationale=None)` ·
`confirm_order(s, preview_id, approved_by, source='ui')` · `approve_preview(s, id, approved_by)` ·
`reject_preview(s, id, actor, reason='')` · `pending_approvals(s)` · `list_orders(s, client_id=None, status=None, limit=50)` ·
`cancel_order(s, order_id, actor)` · `sync_orders(s, client_id=None)` · extras: `create_client`, `update_client`,
`pause_client`, `resume_client`, `set_credentials`, `oauth_start`, `oauth_callback`, `list_audit`, `status_info`,
`public_status`, `daily_used(s, id)` (US$ COMPRADOS hoy; lo lee el comité), `account_fingerprint(rec)`.

Reglas del contrato:
- `source` `mcp`/`committee` → `status='pending_approval'` y `requires_human_approval=True`,
  salvo `BROKERAGE_AUTO_APPROVE_PAPER=on` **y** cliente en papel.
- `confirm_order` con `source != 'ui'` sobre algo pendiente → `{ok: False, error: 'requires human approval', status: 'pending_approval'}` (no ejecuta).
- `confirm_order` con `source != 'ui'` sobre una previsualización de OTRO origen → `code: 'source_mismatch'`.
- Previsualizaciones bloqueadas por riesgo → `ok: True, blocked: True, status: 'rejected'` (quedan en el historial).
- Con `source='committee'` y `proposal_id`, al enviarse se llama `research.committee.mark_executed` (opcional,
  en SAVEPOINT: si falla no deshace el registro de una orden que ya está en Alpaca).
- Si la propuesta del comité se CIERRA sin ejecutarse (rechazada, caducada, bloqueada al confirmar, cancelada,
  fallida, cuenta cambiada) se llama, si existe, `research.committee.mark_preview_closed(session, memo_id,
  preview_id=, status=, reason=, actor=)` (SAVEPOINT; debe ser idempotente y no esperar bloqueos — SKIP LOCKED —
  porque también se llama desde `reject_memo` con el memo ya bloqueado en la misma transacción).
- Un nombre de cliente que coincide con varios → `code: 'ambiguous'` (nunca se elige uno); los nombres son únicos
  sin distinguir mayúsculas.
- Cada previsualización guarda `account_fp` (huella de modo + URL + credenciales). Si al ejecutar no coincide
  (o cambió el modo) → `code: 'account_changed'`, no se envía nada. Cambiar credenciales/OAuth/modo caduca las
  previsualizaciones y propuestas abiertas de ese cliente y reinicia su máximo.
- `positions[].unrealized_plpc` es FRACCIÓN como en Alpaca (0.05 = 5 %).

### Máquina de estados de `broker_orders`

`previewed` (5 min) · `pending_approval` (24 h) → ¿misma cuenta? → controles otra vez → `approved` → Alpaca →
`submitted` → (`sync_orders`) `partially_filled` / `filled` / `canceled` / `expired` / `rejected`.
Bloqueos → `rejected`; rechazo DEFINITIVO de Alpaca (4xx) → `failed`; sin confirmar a tiempo → `expired`.
Red caída / tiempo agotado / 5xx sin poder confirmar por `client_order_id` → `submitted` con
`alpaca_status='unknown'` (`order.unknown=true`): cuenta para duplicados y límite diario, bloquea repetir la misma
orden, y `sync_orders` (o cancelar) la reconcilia por `client_order_id`; si Alpaca responde 404 pasados 120 s →
`failed` ("nunca llegó").

**Idempotencia:** `client_order_id` = id de la previsualización. Si el envío da
tiempo agotado o Alpaca responde "client_order_id must be unique" (reintento tras
una caída), se consulta `GET /v2/orders:by_client_order_id` y se adopta la orden
existente: la misma previsualización nunca crea dos órdenes. La fila se bloquea
con `SELECT … FOR UPDATE` al confirmar (dos clics simultáneos → una sola orden).

### Seguridad

- Credenciales cifradas con Fernet; ninguna respuesta, log ni auditoría las
  contiene (tests lo verifican sobre todas las rutas GET).
- Base URL restringida a `paper-api.alpaca.markets` / `api.alpaca.markets`
  (una base manipulada no puede mandar las claves a otro servidor).
- `state` OAuth: aleatorio + HMAC-SHA256 (clave derivada de la de cifrado),
  guardado en `broker_oauth_states`, **un solo uso**, caduca a los 15 min.
- El `client_secret` de OAuth viaja en el CUERPO del canje (lo exige Alpaca),
  desde el servidor, nunca desde el navegador.
- Rate limits por ruta (`core.http.rate_limit`) y freno al PIN: 10 intentos fallidos en 10 min por IP → 429
  (`pin_locked`). La IP es el **último** salto de `X-Forwarded-For` (lo añade el proxy de Railway; el primero lo
  escribe el cliente y se podía falsificar para esquivar el freno o bloquear al fundador). Respaldo global: 30
  fallos en 10 min desde cualquier IP → 429 para todos (`pin_locked_global`) + fila `pin_lockout` en la auditoría.
  Estructuras acotadas (solo IPs con fallos recientes, tope 5.000) y con lock (8 hilos). ⚠ `core.http.rate_limit`
  (no es de este módulo) todavía usa el PRIMER salto de `X-Forwarded-For`.
- Compras sin préstamo por defecto (ver «Dinero disponible»); `mandate.allow_margin=true` solo si el cliente lo
  pidió por escrito.

### Qué se verificó y qué NO

- ✅ 47 tests con Postgres local (bróker falso + respuestas HTTP grabadas):
  cifrado y no-fuga de secretos, cada control de riesgo, previsualizar→confirmar,
  caducadas/usadas, candados de dinero real, interruptor, cola de aprobación
  (MCP/comité no pueden ejecutar; aprobar sí), idempotencia por
  `client_order_id`, OAuth (state firmado/un uso/caducado, canje), PIN (403/401),
  cancelar/sincronizar, 503 sin base. Revisión 30-sep: estado desconocido (envío
  y consulta caídos → nunca 2 órdenes; reconciliación; 404 tras la gracia →
  falló), ventas sin topes de orden/diario, sin margen por defecto (cripto:
  no marginable), precio límite vs. mercado, papel→real entre previsualizar y
  ejecutar (caduca + huella), auto-aprobación recalculada al confirmar, máximo
  reiniciado al cambiar de cuenta, longitudes/NaN → 400, errores bilingües,
  ganchos del comité en SAVEPOINT, clave de cifrado por defecto rechazada,
  nombres únicos/ambiguos, trigger append-only, PIN por último salto + respaldo global.
- ✅ UI revisada en navegador sin cabeza a 375 px y 1280 px en la primera versión; los
  cambios de la revisión (casilla de margen, estado desconocido, /status/detail)
  solo se verificaron con `node --check` y carga en Node (sin navegador en este entorno).
- ⚠ **NO probado en vivo contra Alpaca** (la red de este entorno bloquea
  alpaca.markets). Formatos de `/v2/account`, `/v2/positions`, `/v2/orders`,
  `/v2/orders:by_client_order_id`, `/v2/clock` y de datos de mercado se
  implementaron según la documentación pública conocida y el código existente
  de `/api/trade/*`. Detalles de OAuth verificados solo con extractos de buscador
  de docs.alpaca.markets y del repo público `alpacahq/alpaca-docs`.
  **Primera prueba real recomendada:** un cliente en papel con claves de papel →
  Leer cuenta → orden de US$1 → Sincronizar.
- ⚠ El horario de mercado usa el reloj de Alpaca; si falla, una aproximación
  (9:30–16:00 Nueva York, sin feriados) y lo dice.
