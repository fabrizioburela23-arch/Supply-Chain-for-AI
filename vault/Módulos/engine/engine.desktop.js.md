---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/desktop.js"
lenguaje: "javascript"
lineas: 1161
aliases: ["engine/desktop.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/desktop.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 1.161 líneas · `engine/desktop.js`

## Para qué sirve

ESCRITORIO KHIPU (K1, 2026-10-04)

## API pública (globales que define)

`window.KhipuDesk`

## Depende de

- [[engine.app_main.js]] — usa `LANG`
- [[engine.toast.js]] — usa `KhipuToast`

Se carga en [[app.html]] en la posición **89 de 98** (línea 3148), después de [[engine.khipu_chat.js]] y antes de [[engine.cockpit.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 89)
- [[engine.cockpit.js]] — usa `KhipuDesk`
- [[engine.khipu_chat.js]] — usa `KhipuDesk`
- [[engine.voice.js]] — usa `KhipuDesk`

## Pruebas que lo cubren

- [[tests.test_cleanup_modules_theme_i18n.py]]
- [[tests.test_genui_browser.py]]
- [[tests.test_khipus_os_fixes_shell.py]]
- [[tests.test_khipus_os_integration.py]]
- [[tests.test_khipus_os_shell.py]]
- [[tests.test_no_client_engine.py]]
- [[tests.test_overnight2_fixer_review.py]]
- [[tests.test_overnight2_scenes_tokens.py]]
- [[tests.test_overnight3_mic_voice_state.py]]
- [[tests.test_overnight3_toast_tokens.py]]
- [[tests.test_overnight_ui_xray_research.py]]
- [[tests.test_scenario_pnl_browser.py]]
- [[tests.test_voice_os_client.py]]
- [[tests.test_voice_tour_client.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-04 (d) — ESCRITORIO - ORDEN AUTOMÁTICO + FIJAR A LOS COSTADOS (sw v189)]]
- [[Sesión 2026-10-04 (b) — ESCRITORIO - REVISIÓN ADVERSARIAL Y CORRECCIONES (sw v187)]]
- [[Sesión 2026-10-04 — ESCRITORIO KHIPU K1 - VENTANAS DENTRO DE LA CABINA (sw v186)]]
- [[Sesión 2026-10-03 — VISIÓN PRÓXIMA ETAPA (pedido, NO es parte de Phase 3)]]
