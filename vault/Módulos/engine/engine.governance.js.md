---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/governance.js"
lenguaje: "javascript"
lineas: 212
aliases: ["engine/governance.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/governance.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 212 líneas · `engine/governance.js`

## Para qué sirve

🩺 Sistema → Gobernanza (INFRA_OPERATIVA paso 12; pieza mínima del paso 25). Muestra el RELEASE vigente (reglas y números versionados), «Ratificar (PIN)» si el de arranque aún no lo está, y cada versión DISPONIBLE de un artefacto con «¿Qué cambia?» (contrafactual del servidor, sin tocar el motor vivo: GET /api/governance/preview) y «Activar (PIN)» (POST /api/governance/activate). Deshacer = activar la anterior. TODO por window._tradeFetch (PIN) y window.KhipuToast.confirm (nunca window.confirm). Textos ES/EN. API: window.KhipuGovernance.mount(containerId)

## API pública (globales que define)

`window.KhipuGovernance`

## Depende de

- [[app.html]] — usa `BASE`, `LANG`, `_tradeFetch`
- [[engine.explain.js]] — usa `explainChip`
- [[engine.toast.js]] — usa `KhipuToast`

Se carga en [[app.html]] en la posición **78 de 95** (línea 7943), después de [[engine.reconcile.js]] y antes de [[engine.pricehist.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 78)
- [[app.html]] — usa `KhipuGovernance`

## Endpoints que llama

- `GET /api/governance/preview` → [[core.governance_api.py]] ([[API governance]])
- `GET /api/governance/status` → [[core.governance_api.py]] ([[API governance]])
- `POST /api/governance/activate` → [[core.governance_api.py]] ([[API governance]])
- `POST /api/governance/ratify` → [[core.governance_api.py]] ([[API governance]])

## Pruebas que lo cubren

- [[tests.test_review_batch_e.py]]
