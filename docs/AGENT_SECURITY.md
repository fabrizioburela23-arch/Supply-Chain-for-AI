# AGENT SECURITY

- **Contenido externo = DATO.** Noticias, web y documentos entran al prompt dentro de `<data>…</data>`; el system
  prompt declara que nunca son instrucciones. `context._clean` neutraliza patrones típicos de inyección
  ("ignore previous instructions", "you are now"…) y recorta longitud. Test: `test_context_builder_numera_evidencia_y_neutraliza_inyeccion`.
- **Citas cerradas.** El modelo solo puede citar ids E# del paquete; cualquier otra ref invalida la salida.
- **Permisos de escritura** (`research/agents/base.WRITE_PERMISSIONS`): solo tablas `research_*` + registrar Source.
  Los hechos originales nunca se sobrescriben.
- **Herramientas por agente**: `permitted_tools` + `context.AGENT_NEEDS` definen qué datos recibe cada uno.
- **Política de modelos**: rutas por agente vía env; claves solo en el servidor.
- **Rate limits**: `POST /api/research/jobs` 12/h por IP; `POST /events` 30/h; presupuesto diario.
- **Auditoría**: cada ejecución en `agent_runs` (disparador, modelo, contexto usado, tokens, costo, errores);
  `actor` obligatorio para pedir investigación.
- **Sin decisiones de inversión**: el prompt prohíbe comprar/vender/mantener y precios objetivo propios.
- **Sin chain-of-thought**: solo `reasoning_summary` breve y auditable.

## Guardián de cifras (anti-alucinación numérica) — 2026-09-28

Caso real: un agente escribió "Broadcom vale ~$350B" con capitalización en
vivo >$1T (cifra de la memoria del modelo). `research/numbers.py`:
toda cifra de dinero/precio en una claim o resumen debe aparecer (±15%,
tolerando unidades B/T/M y es/en: "mil millones", "billones") en el paquete
de evidencia; si no, la salida se RECHAZA y el modelo recibe el error como
feedback (hasta 3 intentos). El paquete siempre intenta incluir la
capitalización EN VIVO (perfil; si falla, fetch_market_cap_yahoo).
Retroactivo: GET /api/research/entity/<id> retira (status 'retracted') las
claims activas cuyas cifras no están en su evidencia guardada.
