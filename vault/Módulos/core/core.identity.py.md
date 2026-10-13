---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/identity.py"
lenguaje: "python"
lineas: 227
aliases: ["core/identity.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/identity.py

> Módulo · capa [[Capa Infraestructura]] · 227 líneas · `core/identity.py`

## Para qué sirve

QUIÉN actúa (docs/INFRA_OPERATIVA.md §1.2 paso 1, §2.2 y §8.1; paso 5 del plan).

## API pública

- clase `Principal` _(línea 47)_
- `slug(s, n=…)` _(línea 73)_
- `clean_declared(s, n=…)` — Etiqueta libre → texto de una línea sin controles, ≤ n caracteres; '' → None. _(línea 78)_
- `normalize_channel(ch, default=…)` _(línea 86)_
- `hash_id(value, purpose=…, n=…)` — Hash con clave (HMAC-SHA256 de SECRET_KEY) de un identificador del cliente (dueño, IP): nunca en claro. _(línea 99)_
- `operator(channel=…, declared=…, pin_source=…, op_id=…)` _(línea 108)_
- `anon(channel=…, declared=…, owner=…)` _(línea 113)_
- `system(task, declared=…)` _(línea 118)_
- `mcp(token_id, client_name=…, oauth=…)` _(línea 122)_
- `registry_agent_ids()` _(línea 127)_
- `agent(name, version=…, declared=…)` — `agent:&lt;id>@&lt;versión>` SOLO para ids del registro único (mascotas y puestos). Otro nombre → ValueError (un agente no se inventa su … _(línea 135)_
- `legacy(actor, channel=…)` — Llamadas de BIBLIOTECA anteriores al paso 5 (scripts, tests, ciclos internos) que solo traen un texto: queda `legacy:&lt;texto>` sin … _(línea 148)_
- `current()` — Principal activo: el de `use()` en este contexto, o el que una ruta ató a la petición (MCP). _(línea 156)_
- `use(principal)` _(línea 171)_
- `bind_request(principal)` — Ata un principal a la petición Flask actual (lo usa /mcp tras validar el token). _(línea 179)_
- `note_pin_ok(op_id=…)` — core/pin.check lo llama al aceptar el PIN: la petición queda autenticada como ese operador. _(línea 186)_
- `operator_for_pin_env(env_name=…)` _(línea 196)_
- `channel_from_request(default=…)` _(línea 203)_
- `principal_from_request(declared=…, channel=…)` — Principal de la petición Flask actual. `declared` = el 'actor' del cuerpo (solo etiqueta). El PIN solo cuenta si un decorador … _(línea 211)_

**Internas** (empiezan con `_`): `_secret`

## Depende de

- [[core.agents_registry.py]] — importa `AGENT_IDS`, `SEATS`
- [[core.pin.py]] — importa `DEFAULT_SECRET_KEY`

## Lo usan

- [[brokerage.api.py]] — lo importa
- [[brokerage.service.py]] — lo importa
- [[core.ai_calls.py]] — lo importa
- [[core.decide.py]] — lo importa
- [[core.decision_sites.py]] — lo importa
- [[core.governance.py]] — lo importa
- [[core.governance_api.py]] — lo importa
- [[core.khipu_chat.py]] — lo importa
- [[core.ledger.py]] — lo importa
- [[core.ledger_api.py]] — lo importa
- [[core.pin.py]] — lo importa
- [[core.prices_api.py]] — lo importa
- [[core.prices_store.py]] — lo importa
- [[core.scheduler.py]] — lo importa
- [[matrix.api.py]] — lo importa
- [[mcp_server.api.py]] — lo importa
- [[mcp_server.tools.py]] — lo importa
- [[ontology.actions.py]] — lo importa
- [[ontology.agents.py]] — lo importa
- [[ontology.api.py]] — lo importa
- [[research.committee_api.py]] — lo importa
- [[server.py]] — lo importa
- herramienta MCP `run_committee` → [[API herramientas MCP]]

_Además lo importan 14 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV SECRET_KEY]]

## Pruebas que lo cubren

- [[tests.test_ai_calls.py]]
- [[tests.test_gates_resulting_state.py]]
- [[tests.test_governance.py]]
- [[tests.test_ledger_callsites.py]]
- [[tests.test_ledger_callsites_committee.py]]
- [[tests.test_ledger_chain.py]]
- [[tests.test_ledger_core.py]]
- [[tests.test_ledger_privacy.py]]
- [[tests.test_ledger_review_fixes.py]]
- [[tests.test_ops_identity.py]]
- [[tests.test_ops_review_steps568.py]]
- [[tests.test_order_single_path.py]]
- [[tests.test_prices_eod.py]]
- [[tests.test_review_infra_c.py]]
