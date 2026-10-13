---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/decisions.py"
lenguaje: "python"
lineas: 758
aliases: ["core/decisions.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/decisions.py

> Módulo · capa [[Capa Infraestructura]] · 758 líneas · `core/decisions.py`

## Para qué sirve

EL servicio de decisiones (docs/INFRA_OPERATIVA.md §2.2-§2.7; paso 6 del plan).

## API pública

- clase `LedgerUnavailable` — El libro no se pudo escribir (base caída / tablas ausentes): el efecto NO debe confirmarse. _(línea 72)_
- `canonical(obj)` — bytes canónicos: claves ordenadas, separadores compactos, UTF-8, sin NaN/Infinity. _(línea 77)_
- `sha256_hex(b)` _(línea 95)_
- `pii_key()` — (clave, key_id, débil). k_pii = HKDF(SECRET_KEY, 'khipus-ledger-pii'); key_id NO revela la clave. _(línea 110)_
- `pii_hmac(text, lang=…)` — Huella de un texto personal: {hmac, key_id, len, lang}. En producción con SECRET_KEY por defecto no se calcula (sería forjable): … _(línea 122)_
- `code_sha()` _(línea 146)_
- `stamp()` — graph_version y linaje del grafo (en memoria, sin SQL), release_hash y code_sha. _(línea 151)_
- `default_durability(kind)` _(línea 167)_
- clase `DecisionCtx` — Se llena desde los puntos instrumentados (apply_event → effect) o a mano. Nunca escribe por sí solo. _(línea 172)_
- `current()` _(línea 276)_
- `note_event(ev)` — Hook de ontology.service.apply_event: cada evento escrito dentro de un scope es un EFECTO de la decisión. _(línea 280)_
- `record(session, ctx, status=…, output=…, expires_at=…)` — Escribe la decisión. sync: en la MISMA sesión que el efecto (si falla, lanza y el caller revierte todo). async: sesión autónoma, nunca … _(línea 423)_
- `safe_error(exc)` — Resumen del error SIN valores de entrada (Pydantic incluye el input del usuario en sus errores). _(línea 478)_
- `record_rejection(ctx, status=…, error=…, report=…)` — Rechazo/bloqueo/fallo en una sesión AUTÓNOMA: queda aunque el caller revierta su transacción. Nunca lanza (devuelve None si ni siquiera se … _(línea 499)_
- `decision_scope(kind, principal, session, subject=…, durability=…, parent_id=…, supersedes_id=…, correlation_id=…, valid_at=…, rejection_status=…)` — Reserva decision_id, marca la transacción (`khipus.decision_id`, guardia del paso 22) y abre el contexto. Al salir: … _(línea 538)_
- `approve(session, target_id, principal, verdict=…, effective_from=…, note=…)` — approval.grant | approval.deny con parent_id = la decisión aprobada. Exige un HUMANO con PIN; si quien pidió fue un agente, una IA (MCP) o … _(línea 577)_
- `link(session, decision_id, role, ref_kind, ref_id, ref_hash=…, as_of=…, **note)` — Añade una referencia DESPUÉS (solo INSERT; repetirla es un no-op). _(línea 617)_
- `link_effect(session, decision_id, ref_kind, ref_id, **note)` _(línea 626)_
- `outcome(session, decision_id, outcome_kind, result, observed_at, source)` — Resultado posterior (nunca se pisa; el vigente es el último). Con result['dedup_key'] no se repite. _(línea 630)_
- `supersede(session, old_id, principal, reason, kind=…, output=…)` — Corrección: decisión NUEVA con supersedes_id (nunca un UPDATE). 'superseded' se deriva, no es un estado. _(línea 641)_
- `list_decisions(session, kind=…, principal=…, status=…, entity=…, since=…, limit=…, redact=…)` _(línea 682)_
- `get(session, decision_id, redact=…, with_blobs=…)` _(línea 701)_
- `explain(d, lang=…)` — Explicación de una línea en lenguaje simple (ES/EN) a partir de get(..., redact=False). _(línea 740)_
- `stats()` _(línea 756)_

**Internas** (empiezan con `_`): `_json_default`, `_hkdf`, `_tables`, `_manifest`, `_rows`, `_dumps`, `_insert`, `_lineage`, `_autonomous`, `_set_guc`, `_uuid`, `_row_dict`

## Depende de

- [[core.__init__.py]] — importa `signals`
- [[core.ledger.py]] — importa `ledger`
- [[core.pin.py]] — importa `DEFAULT_SECRET_KEY`, `in_production`, `secret_key_default`
- [[ontology.bulk_import.py]] — importa `(dinámico: ontology.bulk_import)`
- [[ontology.db.py]] — importa `get_session_factory`
- [[ontology.ledger_models.py]] — importa `Decision`, `DecisionBlob`, `DecisionOutcome`, `DecisionRef`, `DecisionViolation`

## Lo usan

- [[core.ledger.py]] — lo importa
- [[core.ledger_api.py]] — lo importa
- [[ontology.actions.py]] — lo importa
- [[ontology.api.py]] — lo importa
- [[ontology.service.py]] — lo importa

_Además lo importan 4 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV RAILWAY_GIT_COMMIT_SHA]]
- [[ENV SECRET_KEY]]

## Pruebas que lo cubren

- [[tests.test_ledger_core.py]]
- [[tests.test_ledger_privacy.py]]
- [[tests.test_ops_identity.py]]
- [[tests.test_ops_review_steps568.py]]
