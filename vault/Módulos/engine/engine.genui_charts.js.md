---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/genui_charts.js"
lenguaje: "javascript"
lineas: 739
aliases: ["engine/genui_charts.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/genui_charts.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 739 líneas · `engine/genui_charts.js`

## Para qué sirve

GRÁFICOS de las respuestas visuales (kblocks/1, docs/CHAT_UI_GENERATIVA.md §7.2). Portados del Canvas (_cvLine/_cvBar) a tokens --os-\* y a CUALQUIER contenedor (sin ids globales): chart.line · chart.bar (h|v) · ranking · chart.candles · comparison · graph.mini · impact.cascade. SVG en código; los números llegan del servidor con su unidad (aquí solo se escalan y formatean); el impacto sale SOLO del kernel del servidor. Se registra en window.KhipuGenUI (genui.js, cargado ANTES).

## API pública (globales que define)

_No define globales (código encapsulado)._

## Depende de

- [[engine.app_canvas.js]] — usa `cvCol`
- [[engine.explain.js]] — usa `explainRegister`
- [[engine.genui.js]] — usa `KhipuGenUI`

## Lo usan

_Nadie dentro de la app (ver_ [[01 Reporte del grafo]]_)._

## Pruebas que lo cubren

- [[tests.test_genui_browser.py]]
- [[tests.test_genui_client_static.py]]
- [[tests.test_genui_f3_client_static.py]]
- [[tests.test_genui_render_node.py]]
- [[tests.test_lotek_fixer.py]]
