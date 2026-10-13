---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/mascot.js"
lenguaje: "javascript"
lineas: 136
aliases: ["engine/mascot.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/mascot.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 136 líneas · `engine/mascot.js`

## Para qué sirve

MASCOTAS BURBUJA de Khipus OS (2026-10-06)

## API pública (globales que define)

`window.KhipuAgentPrefs`, `window.KhipuMascot`

## Depende de

- [[app.html]] — usa `LANG`

Se carga en [[app.html]] en la posición **31 de 95** (línea 7832), después de [[engine.tour_script.js]] y antes de [[engine.universe2d.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 31)
- [[engine.brief.js]] — usa `KhipuMascot`
- [[engine.clients.js]] — usa `KhipuMascot`
- [[engine.cockpit.js]] — usa `KhipuAgentPrefs`, `KhipuMascot`
- [[engine.committee.js]] — usa `KhipuMascot`
- [[engine.khipu_chat.js]] — usa `KhipuAgentPrefs`, `KhipuMascot`
- [[engine.oswindows.js]] — usa `KhipuAgentPrefs`, `KhipuMascot`
- [[engine.pfcommittee.js]] — usa `KhipuMascot`
- [[engine.pfreports.js]] — usa `KhipuMascot`
- [[engine.pickers.js]] — usa `KhipuMascot`
- [[engine.portfolios.js]] — usa `KhipuMascot`
- [[engine.research.js]] — usa `KhipuMascot`
- [[engine.riskreport.js]] — usa `KhipuMascot`
- [[engine.sync.js]] — usa `KhipuAgentPrefs`
- [[engine.voice.js]] — usa `KhipuAgentPrefs`
- [[engine.xray.js]] — usa `KhipuMascot`

## Pruebas que lo cubren

- [[tests.test_agents_registry.py]]
- [[tests.test_cleanup_modules_theme_i18n.py]]
- [[tests.test_committee_os_ui.py]]
- [[tests.test_khipus_os_chat.py]]
- [[tests.test_khipus_os_integration.py]]
- [[tests.test_khipus_os_server.py]]
- [[tests.test_no_client_engine.py]]
- [[tests.test_overnight2_fixer_review.py]]
- [[tests.test_overnight2_scenes_tokens.py]]
- [[tests.test_overnight3_mic_voice_state.py]]
- [[tests.test_overnight3_toast_tokens.py]]
- [[tests.test_overnight_ui_dossier_clients.py]]
- [[tests.test_overnight_ui_portfolios_risk.py]]
- [[tests.test_overnight_ui_small_panels.py]]
- [[tests.test_overnight_ui_xray_research.py]]
- [[tests.test_voice_os_client.py]]
- [[tests.test_voice_tour_client.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-11 (b) — LIMPIEZA QUE NO QUEDEN COSAS SUELTAS (sw v254)]]
- [[Sesión 2026-10-09 — EL COMITÉ ENTRA A KHIPUS OS (sw v250)]]
