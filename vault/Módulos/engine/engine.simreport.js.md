---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/simreport.js"
lenguaje: "javascript"
lineas: 230
aliases: ["engine/simreport.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/simreport.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 230 líneas · `engine/simreport.js`

## Para qué sirve

INFORME DE ESCENARIO (2026-10-21, «que parezca un producto») Pinta la salida de POST /api/sim/agents (core/sim_agents + core/sim_report) como un informe completo: titular · cifras clave · resumen ejecutivo · TU CARTERA · ganadoras/perdedoras · por sector · por país · tabla completa (ticker, sector, país, canal, %, capitalización y precio en vivo, valor en juego, camino) · cómo se desarrolla · lo que dicen los agentes · qué vigilar · metodología y fuentes · aviso. Botones: 🖨 PDF (ventana de impresión clara) y 📋 copiar el resumen. Cifras SOLO del servidor (sin dato «—»). window.KhipuSimReport.render(d, en) → HTML · .bind(root, d, en, onCompany) → engancha clics y botones.

## API pública (globales que define)

`window.KhipuSimReport`

## Depende de

_Nada interno._

Se carga en [[app.html]] en la posición **94 de 104** (línea 3248), después de [[engine.desktop.js]] y antes de [[engine.cockpit.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 94)
- [[engine.app_coordinator.js]] — usa `KhipuSimReport`
- [[engine.cockpit.js]] — usa `KhipuSimReport`

## Pruebas que lo cubren

- [[tests.test_sim_report.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-16 — PRÓXIMA SESIÓN — EMPEZAR AQUÍ]]
