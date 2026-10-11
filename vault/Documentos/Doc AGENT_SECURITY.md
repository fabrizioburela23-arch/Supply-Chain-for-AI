---
tipo: "documento"
capa: "Documentación"
ruta: "docs/AGENT_SECURITY.md"
lenguaje: "markdown"
lineas: 27
aliases: ["docs/AGENT_SECURITY.md"]
tags: ["capa/documentacion", "tipo/documento"]
---

# docs/AGENT_SECURITY.md

> Documento · capa [[Capa Documentación]] · 27 líneas · `docs/AGENT_SECURITY.md`

## De qué trata

AGENT SECURITY — - \*\*Contenido externo = DATO.\*\* Noticias, web y documentos entran al prompt dentro de `&lt;data>…&lt;/data>`; el system prompt declara que nunca son instrucciones. `context._clean` neutraliza patrones típicos de inyección ("ignore previous instructions", "you are now"…) y recorta longitud. Test: `test_context_builder_numera_evidencia_y_neutraliza_inyeccion`. - \*\*Citas cerradas.\*\* El modelo solo puede citar ids E# del paquete; cualquier otra ref invalida la salida. - \*\*Permisos de escritura\*\* …

## Menciona

- [[research.agents.base.py]]
