---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/governance.js"
lenguaje: "javascript"
lineas: 538
aliases: ["engine/governance.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/governance.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 538 líneas · `engine/governance.js`

## Para qué sirve

🩺 Sistema → Gobernanza (INFRA_OPERATIVA paso 12; pieza mínima del paso 25). Muestra el RELEASE vigente (reglas y números versionados), «Ratificar (PIN)» si el de arranque aún no lo está, y cada versión DISPONIBLE de un artefacto con «¿Qué cambia?» (contrafactual del servidor, sin tocar el motor vivo: GET /api/governance/preview) y «Activar (PIN)» (POST /api/governance/activate). Deshacer = activar la anterior. TODO por window._tradeFetch (PIN) y window.KhipuToast.confirm (nunca window.confirm). Textos ES/EN. Paso 25 (flujo completo, core/governance_flow.py): «¿Qué cambia para mí?» con TUS posiciones (MKT.pos = la cartera ACTIVA; sin ellas, las 10 empresas más …

## API pública (globales que define)

`window.KhipuGovernance`

## Depende de

- [[app.html]] — usa `_tradeFetch`
- [[engine.app_main.js]] — usa `BASE`, `LANG`, `MKT`
- [[engine.explain.js]] — usa `explainChip`
- [[engine.toast.js]] — usa `KhipuToast`

Se carga en [[app.html]] en la posición **83 de 103** (línea 3208), después de [[engine.reconcile.js]] y antes de [[engine.audit.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 83)
- [[engine.app_main.js]] — usa `KhipuGovernance`

## Endpoints que llama

- `GET /api/governance/history` → [[core.governance_api.py]] ([[API governance]])
- `GET /api/governance/preview` → [[core.governance_api.py]] ([[API governance]])
- `GET /api/governance/status` → [[core.governance_api.py]] ([[API governance]])
- `GET /api/governance/validation` → [[core.governance_api.py]] ([[API governance]])
- `POST /api/governance/activate` → [[core.governance_api.py]] ([[API governance]])
- `POST /api/governance/cancel` → [[core.governance_api.py]] ([[API governance]])
- `POST /api/governance/propose` → [[core.governance_api.py]] ([[API governance]])
- `POST /api/governance/ratify` → [[core.governance_api.py]] ([[API governance]])
- `POST /api/governance/validate` → [[core.governance_api.py]] ([[API governance]])

## Pruebas que lo cubren

- [[tests.test_review_batch_e.py]]
