# Carteras + agentes programables + conectores (plan, 2026-11-10)

Pedido de Fabrizio: «no me gusta que haya carteras simuladas y mi cuenta, siempre me confundo… que todo esté en uno;
una persona debería manejar las carteras falsas y reales que desee, con diferentes objetivos; se debería poder programar
agentes». Lineamiento del proyecto: **cada vez más simple por fuera y más capaz por dentro.**

## 1. Hoy (por qué confunde)

| Lo que existe | Dónde vive | Dinero |
|---|---|---|
| Carteras de práctica (`kh_portfolios`, engine/pfstore.js) | navegador + /api/user-state | ninguno (anotaciones) |
| Mi cuenta (bróker) — cliente `house` | Alpaca (papel o real) | simulado o real |
| 👥 Clientes (brokerage multi-cliente) | Alpaca, una cuenta por persona | simulado o real |
| Agente de trading | core/trading_agent.py, UNO solo, sobre `house` | el de `house` |

## 2. Objetivo: UNA lista «Carteras»

Cada cartera = **nombre + objetivo + tipo de dinero + (opcional) un agente**.

- Tipo de dinero, siempre visible con su insignia:
  - 📝 **Seguimiento** — anotas lo que tienes en otro lado (lo que hoy es «práctica»); sin órdenes.
  - 🧪 **Papel** — órdenes simuladas en Alpaca papel.
  - 🔴 **Real** — órdenes reales (PIN + confirmación, como hoy).
- Objetivo (crecimiento, ingresos, especulación, cobertura…) + perfil de riesgo + límites propios (tope por posición,
  pérdida diaria, universo de acciones). Los chequeos de `brokerage.service` leen los límites DE ESA cartera.
- Muchas carteras de cada tipo. Mercado, Terminal, riesgo, chat y brief leen la cartera ACTIVA (como hoy MKT.pos).

### Varias carteras de papel/reales sobre UNA cuenta de Alpaca — DECIDIDO por Fabrizio (2026-11-10)
Khipus lleva la contabilidad de cada cartera: efectivo asignado, posiciones atribuidas por orden (cada orden lleva el id
de la cartera en `client_order_id` y en `broker_orders`), P&L propio. Reglas duras: una cartera no vende más de lo que
ES SUYO ni gasta más del efectivo asignado; la suma de las carteras = la cuenta de Alpaca (conciliación diaria,
`core/reconcile` / 🩺 avisa si no cuadra). Alternativa: una cuenta de Alpaca por cartera (más limpia, más claves).

## 3. Agentes programables (uno por cartera)

Un agente = la cartera + reglas escritas en lenguaje simple que se guardan como configuración VALIDADA (no código
libre): universo, cuándo comprar/vender (técnico + convicción de analistas + escenarios), tamaños, stops, horario,
modo (manual = propone, automático = solo en papel). La IA traduce «compra las de HBM cuando caigan 10 % y el comité
esté a favor» a esa configuración y la muestra para aprobar con PIN. Cada agente deja decisiones en el libro y su
historial vs SPY. Regla de oro intacta: dinero real NUNCA en automático; todo por `brokerage.service`.

## 4. Conectores: Composio + repos de GitHub como skills (Khipus OS)

- **Composio**: una puerta a cientos de apps (Gmail, Slack, Notion, Sheets…). Se conecta desde el servidor con la
  clave `COMPOSIO_API_KEY` (Railway) y aparece en el chat como dos herramientas: «buscar acción» y «ejecutar acción».
  Leer = libre; ESCRIBIR (enviar un correo, crear un documento) = confirmación con KhipuToast (el chat sigue sin
  poder operar dinero). Cada conexión de app la autoriza el usuario en Composio.
- **Skills desde GitHub**: ver docs/ESTADO.md (catálogo curado, instalación con PIN, fijada a un commit).
- Ambos viven en Khipus OS como «🧩 Conectores» (una sola ventana), no como botones sueltos.

## 5. Fases (cada una desplegable sola)

1. **Una sola ventana «Carteras»** que lista las de seguimiento (las de práctica de hoy) y la cuenta del bróker con su
   insignia 📝/🧪/🔴; «Mi cuenta» y «Carteras de práctica» desaparecen como entradas separadas. Sin tocar el dinero.
2. **Carteras de papel/reales múltiples** sobre la cuenta de Alpaca (contabilidad por cartera + conciliación).
3. **Agente por cartera** (la configuración del agente actual pasa a vivir en cada cartera; varios agentes a la vez).
4. **🧩 Conectores**: Composio (lectura primero, escritura con confirmación) + skills de GitHub.
