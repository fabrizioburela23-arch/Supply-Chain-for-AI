---
tipo: "modulo"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
ruta: "core/world.py"
lenguaje: "python"
lineas: 2083
aliases: ["core/world.py"]
tags: ["capa/datos-vivo", "tipo/modulo"]
---

# core/world.py

> Módulo · capa [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] · 2.083 líneas · `core/world.py`

## Para qué sirve

WORLD MONITOR geopolítico: /api/world/\*.

## API pública

- `err_info(err)` — Código de error interno → {error_code, error_es, error_en} (regla bilingüe: el cliente elige el idioma; 'error' = texto en inglés para … _(línea 153)_
- `country_key(raw)` — Texto libre de país → clave del catálogo ('Estados Unidos (HQ…)' → 'EEUU'). _(línea 612)_
- `geo_coord(node)` — Réplica de GeoCoords.geoCoord(node): {lat, lng, label, precision, country, precise}. _(línea 650)_
- `place_country(text)` — País (clave del catálogo) desde el texto de lugar de un evento: 'Kyiv, Kyyiv, Misto, Ukraine' → 'Ucrania'; '12 km SE of Hualien City, … _(línea 678)_
- `haversine_km(lat1, lon1, lat2, lon2)` _(línea 695)_
- `nrs_country(country)` — Clave de la tabla NRS para un país escrito de cualquier forma (o None). _(línea 716)_
- `nrs_geo(country)` _(línea 725)_
- `nrs_concentrated(country)` _(línea 729)_
- `client_nrs(node, degree)` — MISMA fórmula que computeNRS() de app.html (margen acotado a [0,20] desde 2026-10-05: antes una empresa sin ganancias — OpenAI, margen muy … _(línea 733)_
- `graph_version()` — La generación del grafo que usa el World Monitor (tests/test_ops_single_source.py). _(línea 818)_
- `source_down(name, now=…)` — 'source_down:&lt;fuente>:&lt;error>' si la fuente está en pausa; None si se puede consultar (también cuando la pausa venció: UNA consulta de … _(línea 842)_
- `source_result(name, err, now=…)` — Registra el resultado de una consulta. Éxito → reinicia. Solo los errores DEFINITIVOS (404/410/401/403) cuentan; los pasajeros (timeout, … _(línea 853)_
- `source_retry_at(name)` _(línea 876)_
- `sources_state()` — Estado de las fuentes con pausa (para /api/world/events, el 🩺 y tests). _(línea 882)_
- `gdelt_throttle(max_wait=…)` — Espaciado COMPARTIDO de GDELT (World Monitor + Sala de Situación): cada llamador RESERVA un turno (slot = max(ahora, último + … _(línea 892)_
- `gdelt_severity(count, window=…)` — 0-100 por intensidad de cobertura: nº de artículos por día en ese lugar (escala log: 1/día≈31, 3≈47, 7≈63, 15≈79, 31+≈95). _(línea 967)_
- `parse_gdelt_geo(payload, layer, window=…, now=…, limit=…)` — GeoJSON de GDELT GEO 2.0 (mode=PointData) → items. Cada feature: geometry.coordinates=[lon,lat], properties={name, count, html…}. _(línea 975)_
- `quake_severity(mag, alert=…, tsunami=…)` — 0-100: magnitud (M4.5≈13, M5.5≈38, M6.5≈63, M7.5≈88) + alerta PAGER de USGS (amarilla +10, naranja +20, roja +30) + aviso de tsunami (+10). _(línea 1015)_
- `parse_usgs(payload)` — GeoJSON de USGS (feeds summary) → items. coordinates=[lon, lat, depth_km], properties={mag, place, time(ms), url, title, alert, tsunami, … _(línea 1029)_
- `natural_severity(cat_id, mag_value=…, mag_unit=…)` — 0-100 ESTIMADA por categoría (volcán 55, tormenta/inundación 45, incendio 30…) + magnitud cuando EONET la da: viento en nudos (kts × 0.7) o … _(línea 1068)_
- `parse_eonet(payload)` — EONET v3 /events → items (última geometría de cada evento abierto). _(línea 1097)_
- `gdelt_query(layer)` _(línea 1145)_
- `prewarm(window=…)` — W1: tarea del reloj del servidor — refresca en segundo plano las capas vencidas para que el primer visitante no vea 'cargando'. No espera … _(línea 1393)_
- `max_age_s(layer, window)` — Edad máxima de los datos cacheados de una capa POR VENTANA (GDELT) antes de descartarlos: más viejos ya no describen 'las últimas 24h/7d' … _(línea 1481)_
- `world_events(layers=…, window=…, wait=…)` — CONTRATO: {items:[{id, layer, lat, lon, title, severity, time, source, url, …}], sources:{layer:{ok, count, as_of, error?, provider, …}}, … _(línea 1498)_
- `reference_layers()` _(línea 1641)_
- `item_radius_km(item)` _(línea 1676)_
- `exposure(lat, lon, radius_km=…, country=…, limit=…, affected=…)` — Empresas del grafo expuestas a un punto: near → sede conocida (HQ curado o ciudad) a ≤ radius_km, affected → lista explícita (p.ej. las … _(línea 1702)_
- `item_exposure(item, limit=…)` _(línea 1783)_
- `relevance(severity, exposure_index)` — 0-100 = 0.55·severidad + 0.45·exposición de la cadena. _(línea 1788)_
- `item_relevance(item, ex)` — Relevancia de un ítem del brief. La inestabilidad por país es un índice de TODO el país (no un evento puntual): cuenta con exposición 0 en … _(línea 1796)_
- `compose_brief(ranked, n)` — Top-n por relevancia RESERVANDO al menos la mitad de los lugares (si los hay) a eventos en vivo: los estrechos y países curados cambian … _(línea 1810)_
- `brief(window=…, n=…, wait=…)` — Top-N ítems por RELEVANCIA (severidad + exposición de la cadena). Determinista: sin IA. Cacheado 60 s por ventana. _(línea 1872)_
- `api_world_events()` — GET /api/world/events?layers=conflict,quakes&window=24h|7d _(línea 1948)_
- `api_world_exposure()` — GET /api/world/exposure?lat=&lon=&radius_km=500[&country=Taiwan][&limit=25] [&affected=TSMC,Nvidia] — affected = dependientes curados de un … _(línea 1965)_
- `api_world_brief()` — GET /api/world/brief?window=24h&n=10 — lo más relevante con su exposición. _(línea 1987)_
- `api_world_reference()` — GET /api/world/reference — rutas marítimas, cables y fabs (NO en vivo). _(línea 2001)_
- `api_world_policy()` — GET /api/world/policy — reglas del BIS (controles de exportación, Entity List) y de la OFAC (sanciones) de los últimos 30 días, del Federal … _(línea 2010)_
- `entity_geo_risks(entity_ids, window=…, wait=…, per_entity=…, min_severity=…)` — {entity_id: [{layer, title_es, title_en, severity, why, why_es, why_en, distance_km?, time, url, source}]} Solo capas EN VIVO u oficiales … _(línea 2036)_
- `api_world_gpr()` — GET /api/world/gpr — índice de riesgo geopolítico (Caldara-Iacoviello): diario global + por país (mensual). _(línea 2080)_

**Internas** (empiezan con `_`): `_now`, `_iso`, `_parse_iso`, `_safe_url`, `_js_norm`, `_fnv`, `_jitter`, `_city_hint`, `_norm_country`, `_js_round`, `_graph`, `_env_int`, `_http_get_json`, `_articles_from_html`, `_stable_id`, `_valid_ll`, `_centroid`, `_gdelt_events_on`, `_fetch_gdelt_events`, `_fetch_gdelt`, `_fetch_quakes`, `_fetch_natural`, `_situation`, `_curated_source`, `_cached_items`, `_blend_live_chokepoint`, `_blend_live_country`, `_fetch_chokepoints`, `_fetch_instability`, `_feeds`, `_curated_as_of`, `_news_live`, `_reset_cache`, `_fetch_key`, `_refresh`, `_ttl`, `_ensure`, `_window_filter`, `_expired`, `_co`, `_rank_key`, `_why`, `_bad`, `_float_arg`

## Depende de

- [[core.__init__.py]] — importa `hot`
- [[core.gdelt_events.py]] — importa `gdelt_events`
- [[core.geosit.py]] — importa `CURATED_AS_OF`, `FABS`, `situation_data`
- [[core.gpr.py]] — importa `gpr`, `gpr_cached`
- [[core.http.py]] — importa `rate_limit`
- [[core.live_fundamentals.py]] — importa `live_margin`
- [[core.world_feeds.py]] — importa `FEED_META`, `world_feeds`
- [[ontology.vocabulary.py]] — importa `vocabulary`

## Lo usan

- [[core.geosit.py]] — lo importa
- [[core.khipu_chat.py]] — lo importa
- [[core.ops_check.py]] — lo importa
- [[core.portfolio_ai.py]] — lo importa
- [[core.sim_agents.py]] — lo importa
- [[core.space.py]] — lo importa
- [[core.world_feeds.py]] — lo importa
- [[matrix.tensor.py]] — lo importa
- [[mcp_server.tools.py]] — lo importa
- [[ontology.agents.py]] — lo importa
- [[research.agent_skills.py]] — lo importa
- [[research.committee_api.py]] — lo importa
- [[server.py]] — lo importa
- herramienta MCP `get_company` → [[API herramientas MCP]]
- herramienta MCP `get_world_events` → [[API herramientas MCP]]

_Además lo importan 13 pruebas (lista abajo)._

## Endpoints que define

| Método | Ruta | Función | Lo llaman |
|---|---|---|---|
| `GET` | `/api/world/brief` | `api_world_brief` | [[engine.worldmonitor.js]], [[sim.scenario_builder.js]], 1 prueba |
| `GET` | `/api/world/events` | `api_world_events` | [[engine.worldmonitor.js]], 1 prueba |
| `GET` | `/api/world/exposure` | `api_world_exposure` | [[engine.worldmonitor.js]], 1 prueba |
| `GET` | `/api/world/gpr` | `api_world_gpr` | [[engine.worldmonitor.js]], [[sim.scenario_builder.js]] |
| `GET` | `/api/world/policy` | `api_world_policy` | [[engine.worldmonitor.js]], [[sim.scenario_builder.js]] |
| `GET` | `/api/world/reference` | `api_world_reference` | [[engine.worldmonitor.js]], 1 prueba |

Grupos: [[API world]]

## Endpoints que llama

- `GET /api/geo/situation` → [[core.geosit.py]] ([[API geo]])

## Variables de entorno que lee (solo nombres)

- [[ENV WORLD_GDELT_EVENTS]]
- [[ENV WORLD_GDELT_GEO_URL]]
- [[ENV WORLD_GDELT_QUERY_{X}]]
- [[ENV WORLD_SOURCE_DOWN_AFTER]]
- [[ENV WORLD_SOURCE_DOWN_TTL]]

## Pruebas que lo cubren

- [[tests.test_cleanup_nrs_parity.py]]
- [[tests.test_cleanup_server.py]]
- [[tests.test_gdelt_events.py]]
- [[tests.test_gpr.py]]
- [[tests.test_live_fundamentals.py]]
- [[tests.test_mcp.py]]
- [[tests.test_ops_single_source.py]]
- [[tests.test_repair_graph.py]]
- [[tests.test_repair_ops.py]]
- [[tests.test_repair_world.py]]
- [[tests.test_world.py]]
- [[tests.test_world_feeds.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-11 (b) — LIMPIEZA QUE NO QUEDEN COSAS SUELTAS (sw v254)]]
- [[Sesión 2026-10-06 (ff) — ONTOLOGÍA NIVEL 2 - TENSORES + AUTO-CONEXIÓN (sw v241)]]
- [[Sesión 2026-10-05 (y) — NRS ACOTADO + BÚSQUEDA DEL MAPA (sw v232)]]
- [[Sesión 2026-10-05 (t) — ESTRECHOS Y PAÍSES - CURADO + EN VIVO (sw v226)]]
- [[Sesión 2026-10-05 (q) — COMITÉ DE CARTERA GEOPOLÍTICA EN VIVO (sw v223)]]
- [[Sesión 2026-10-05 (n) — GEOPOLÍTICA CON FUENTES OFICIALES (sw v216)]]
- [[Sesión 2026-09-30 — PHASE 3 + WORLD MONITOR + CORRETAJE + MCP + ENDURECIMIENTO (sw v170)]]
