"""core/world.py — WORLD MONITOR geopolítico: /api/world/*.

Pedido de Fabrizio (2026-09-30): la pestaña Geopolítica tenía un globo 3D Y un
mapa de eventos 2D aparte ("muy grande y da poca info"). Ahora hay UNA sola
vista: un "World Monitor" (estilo worldmonitor.app) dentro del globo 3D
(engine/worldmonitor.js). Este módulo es su backend.

Qué agrega (TODO fuente pública real, cada capa con su estado honesto):
- conflict / unrest / trade → GDELT GEO 2.0 (PointData, GeoJSON): lugares con
  cobertura de noticias sobre conflicto armado, protestas y comercio/sanciones
  en la ventana (24h / 7d). GDELT agrega por ventana: los puntos NO traen hora
  exacta (time_kind='window').
- quakes → USGS (sismos M4.5+ de la última semana, filtrados por ventana).
- natural → NASA EONET v3 (eventos naturales ABIERTOS: incendios, tormentas,
  volcanes…; filtrados por ventana según su ÚLTIMA actualización).
- chokepoints / instability → la Sala de Situación existente (core/geosit.py):
  severidad estructural curada + noticias GDELT + factores activos del grafo.
- referencia (NO en vivo): rutas marítimas principales, corredores de cables
  submarinos y fabs críticas — GET /api/world/reference, etiquetadas como tal.

Exposición de la cadena (GET /api/world/exposure, y dentro de /api/world/brief):
qué empresas del grafo están cerca de un punto. Las coordenadas de las empresas
salen de una réplica EXACTA de engine/geo_coords.js (tests/test_world.py compara
ambas sobre los 949 nodos). Solo cuentan como "cerca" las empresas con sede
conocida (HQ curado o ciudad del catálogo); las de ubicación aproximada entran
por "mismo país" y solo en países compactos (en EE.UU./China/Rusia… un evento
local NO expone a todo el país).

Robustez: caché por capa (5-15 min), timeouts, stale-while-revalidate en hilos
de fondo, errores AISLADOS por capa (una fuente caída no tumba a las demás), y
un acelerador COMPARTIDO de GDELT (~1 consulta / 5 s por IP) que también usa
core/geosit.py. Nunca inventa: si una fuente cae, su capa dice por qué.
"""
import hashlib
import html as _html
import json
import logging
import math
import os
import re
import threading
import time
import unicodedata
from datetime import datetime, timezone

import requests
from flask import Blueprint, jsonify, request

from core.http import rate_limit

log = logging.getLogger('world')

world_bp = Blueprint('world', __name__, url_prefix='/api/world')

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SNAPSHOT = os.path.join(_ROOT, 'data', 'grafo_v0.json')
_UA = 'KhipuFinance/1.0 (+world-monitor)'

WINDOWS = {'24h': 86400, '7d': 7 * 86400}
GDELT_LAYERS = ('conflict', 'unrest', 'trade')
# 2026-10-05: fuentes OFICIALES nuevas (core/world_feeds.py) — tráfico marítimo
# (FMI PortWatch), controles de exportación/sanciones (Federal Register BIS·OFAC)
# y alertas de desastres (GDACS).
FEED_LAYERS = ('shipping', 'policy', 'disasters', 'outages')
OFFICIAL_COUNTRY_LAYERS = ('advisories',)      # riesgo país oficial (no es un evento puntual)
LIVE_LAYERS = GDELT_LAYERS + ('quakes', 'natural') + FEED_LAYERS + OFFICIAL_COUNTRY_LAYERS + ('chokepoints', 'instability')
REF_LAYERS = ('lanes', 'cables', 'fabs')
DEFAULT_WAIT = 4.5          # s que un request espera a una capa FRÍA (sin caché)

# TTL por capa (s). Tras un fallo se reintenta antes (ERROR_TTL).
LAYER_TTL = {'conflict': 900, 'unrest': 900, 'trade': 900, 'quakes': 300,
             'natural': 900, 'chokepoints': 120, 'instability': 120,
             'shipping': 6 * 3600, 'policy': 3600, 'disasters': 900, 'advisories': 6 * 3600, 'outages': 900}
ERROR_TTL = 90
BUSY_TTL = 20               # GDELT "ocupado" (acelerador): reintento pronto, no es una caída
# W1 (misión de reparación 2026-10-04): una fuente que responde 404/410 (API
# retirada o movida) o 401/403 (ahora pide credenciales) N veces SEGUIDAS queda
# "en pausa" WORLD_SOURCE_DOWN_TTL segundos: no se la vuelve a consultar cada
# 90 s ni ocupa el acelerador compartido de GDELT, y la UI/MCP dicen la verdad
# (error_code 'source_unavailable' + retry_at). Decisión D7: si GDELT pide
# clave, la capa queda apagada — no se contratan servicios nuevos.
SOURCE_DOWN_AFTER = 3
SOURCE_DOWN_TTL = 3600
_DEFINITIVE_HTTP = ('401', '403', '404', '410')
SOURCE_LABEL = {'gdelt_geo': 'GDELT GEO 2.0', 'gdelt_doc': 'GDELT DOC 2.0', 'gdelt_events': 'GDELT 2.0 Events', 'portwatch': 'IMF PortWatch',
                'fedreg': 'US Federal Register', 'gdacs': 'GDACS'}

LAYER_META = {
    'conflict': dict(provider='GDELT GEO 2.0', es='Conflicto armado', en='Armed conflict',
                     feed='https://api.gdeltproject.org/api/v2/geo/geo'),
    'unrest': dict(provider='GDELT GEO 2.0', es='Protestas / disturbios', en='Protests / unrest',
                   feed='https://api.gdeltproject.org/api/v2/geo/geo'),
    'trade': dict(provider='GDELT GEO 2.0', es='Comercio / sanciones', en='Trade / sanctions',
                  feed='https://api.gdeltproject.org/api/v2/geo/geo'),
    'quakes': dict(provider='USGS', es='Sismos M4.5+', en='Earthquakes M4.5+',
                   feed='https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.geojson'),
    'natural': dict(provider='NASA EONET v3', es='Eventos naturales (actualizados en la ventana)',
                    en='Natural events (updated within the window)',
                    feed='https://eonet.gsfc.nasa.gov/api/v3/events'),
    'chokepoints': dict(provider='Khipu (curated) + GDELT + graph', provider_es='Khipu (curado) + GDELT + grafo',
                        es='Estrechos y canales', en='Straits & canals', feed='/api/geo/situation'),
    'instability': dict(provider='Khipu (curated) + GDELT + graph', provider_es='Khipu (curado) + GDELT + grafo',
                        es='Inestabilidad por país', en='Country instability', feed='/api/geo/situation'),
}
from core.world_feeds import FEED_META as _FEED_META  # noqa: E402
LAYER_META.update(_FEED_META)


# Consultas GDELT (temas GKG). Sobrescribibles SIN tocar código:
# WORLD_GDELT_QUERY_CONFLICT / _UNREST / _TRADE (lección sept-2026: los
# proveedores cambian; el arreglo debe ser una variable de entorno).
_GDELT_Q = {
    'conflict': '(theme:ARMEDCONFLICT OR theme:TERROR)',
    'unrest': 'theme:PROTEST',
    'trade': '(theme:SANCTIONS OR "export controls" OR "trade war")',
}
GDELT_GEO_URL = 'https://api.gdeltproject.org/api/v2/geo/geo'
USGS_URL = 'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.geojson'
EONET_URL = 'https://eonet.gsfc.nasa.gov/api/v3/events'


def _now():
    return time.time()


def _iso(ts):
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _parse_iso(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace('Z', '+00:00')).timestamp()
    except (TypeError, ValueError):
        return None


_URL_OK = re.compile(r'^https?://', re.I)


def _safe_url(u):
    """Solo enlaces http(s): un feed alterado/proxy no puede colar un
    javascript: o data: que el cliente pinte como <a href> (el origen de la app
    guarda el PIN de trading en localStorage)."""
    if not isinstance(u, str):
        return None
    u = u.strip()
    return u if _URL_OK.match(u) else None


def err_info(err):
    """Código de error interno → {error_code, error_es, error_en} (regla
    bilingüe: el cliente elige el idioma; 'error' = texto en inglés para
    consumidores máquina como el MCP). Códigos: timeout · conn:<host> ·
    rate_limited · http:<n> · nonjson:<fragmento> · bad_payload:<fuente> ·
    busy · pending · refreshing · no_data · exc:<Tipo: msg>."""
    e = str(err or 'no_data')
    head, _, rest = e.partition(':')
    if e == 'timeout':
        c, es, en = 'timeout', 'tiempo de espera agotado', 'timed out'
    elif head == 'conn':
        c, es, en = 'no_connection', f'sin conexión con {rest}', f'no connection to {rest}'
    elif e == 'rate_limited':
        c, es, en = 'rate_limited', 'la fuente limitó las consultas (429)', 'source rate-limited us (429)'
    elif head == 'http':
        c, es, en = f'http_{rest}', f'la fuente respondió HTTP {rest}', f'source returned HTTP {rest}'
    elif head == 'nonjson':
        c, es, en = 'non_json', f'respuesta no-JSON: {rest}', f'non-JSON response: {rest}'
    elif head == 'bad_payload':
        c, es, en = 'bad_payload', f'formato de respuesta inesperado ({rest})', f'unexpected response format ({rest})'
    elif e == 'busy':
        c, es, en = 'busy', 'GDELT ocupado (acelerador compartido): se reintenta en breve', \
            'GDELT busy (shared rate limiter): retrying shortly'
    elif head == 'source_down':
        src, _, why = rest.partition(':')
        code = why.rpartition(':')[2]
        name = SOURCE_LABEL.get(src, src)
        if src.startswith('gdelt'):
            live_es = ('Sismos (USGS), eventos naturales (NASA), tráfico marítimo (FMI), reglas y sanciones '
                       '(EE.UU.), alertas GDACS y estrechos siguen funcionando.')
            live_en = ('Earthquakes (USGS), natural events (NASA), shipping (IMF), rules & sanctions (US), '
                       'GDACS alerts and straits keep working.')
        else:
            live_es, live_en = 'Las demás capas siguen funcionando.', 'The other layers keep working.'
        if code in ('401', '403'):
            c = 'source_unavailable'
            es = (f'{name} ahora exige credenciales (HTTP {code}): capa apagada — no se contratan servicios '
                  f'nuevos. Se reintenta cada hora. {live_es}')
            en = (f'{name} now requires credentials (HTTP {code}): layer switched off — no new paid services. '
                  f'Retried every hour. {live_en}')
        else:
            c = 'source_unavailable'
            es = (f'{name} no responde en su dirección (HTTP {code}: la API parece retirada o movida). Capa en '
                  f'pausa; se reintenta cada hora. {live_es}')
            en = (f'{name} does not answer at its address (HTTP {code}: the API looks retired or moved). Layer '
                  f'paused; retried every hour. {live_en}')
    elif head == 'needs_key':
        var, _, inv = rest.partition(':')
        c = 'needs_key'
        if inv:
            es, en = (f'La clave {var} no es válida o venció: créala de nuevo (gratis) y pégala en Railway → Variables.',
                      f'The key {var} is invalid or expired: create it again (free) and paste it in Railway → Variables.')
        else:
            es, en = (f'Falta una clave GRATUITA: crea {var} y pégala en Railway → Variables. Las demás capas siguen funcionando.',
                      f'A FREE key is missing: create {var} and paste it in Railway → Variables. The other layers keep working.')
    elif e == 'pending':
        c, es, en = 'pending', 'primera consulta en curso', 'first fetch in progress'
    elif e == 'refreshing':
        c, es, en = 'refreshing', 'actualizando datos viejos', 'refreshing outdated data'
    elif e == 'no_data':
        c, es, en = 'no_data', 'sin datos', 'no data'
    elif head == 'exc':
        c, es, en = 'internal', f'error interno: {rest.strip()}', f'internal error: {rest.strip()}'
    else:
        c, es, en = 'other', e, e
    return {'error_code': c, 'error_es': es, 'error_en': en, 'error': en}


# ═══════════════════════════════════════════════════════════════════════════
# 1. Coordenadas de empresas — RÉPLICA EXACTA de engine/geo_coords.js
#    (tablas generadas desde el JS; tests/test_world.py verifica la paridad)
# ═══════════════════════════════════════════════════════════════════════════
# Tablas copiadas de engine/geo_coords.js (COUNTRY, ALIAS, CITY, HQ, US_HUBS).
# Si editas una aquí, edítala allá (y viceversa): el test de paridad lo exige.
_COUNTRY = {
    "EEUU": (37.77, -122.42),
    "Japon": (35.68, 139.69),
    "Japan": (35.68, 139.69),
    "China": (31.23, 121.47),
    "Taiwan": (24.8, 120.97),
    "Corea": (37.57, 126.98),
    "Alemania": (51.05, 13.74),
    "Francia": (45.18, 5.72),
    "PaisesBajos": (51.41, 5.42),
    "ReinoUnido": (51.51, -0.13),
    "Israel": (32.08, 34.78),
    "India": (12.97, 77.59),
    "Australia": (-33.87, 151.21),
    "Europa": (50.11, 8.68),
    "RestoEuropa": (52.52, 13.4),
    "RestoMundo": (1.35, 103.82),
    "Canada": (45.5, -73.57),
    "Finlandia": (60.17, 24.94),
    "Noruega": (59.91, 10.75),
    "Chile": (-33.45, -70.67),
    "Rusia": (55.76, 37.62),
    "EAU": (25.2, 55.27),
    "Singapur": (1.29, 103.85),
    "HongKong": (22.32, 114.17),
    "Suiza": (47.37, 8.54),
    "Dinamarca": (55.68, 12.57),
    "Brasil": (-23.55, -46.63),
    "Catar": (25.29, 51.53),
    "Sudafrica": (-26.2, 28.05),
    "Panama": (8.98, -79.52),
    "Irlanda": (53.35, -6.26),
    "Italia": (45.46, 9.19),
    "Kazajistan": (51.17, 71.45),
    "Tailandia": (13.76, 100.5),
    "Lituania": (54.69, 25.28),
    "Malasia": (3.14, 101.69),
    "Argelia": (36.75, 3.06),
    "Polonia": (52.23, 21.01),
    "Indonesia": (-6.21, 106.85),
    "Kuwait": (29.38, 47.99),
    "Espana": (40.42, -3.7),
    "Uganda": (0.35, 32.58),
    "Mexico": (19.43, -99.13),
    "Suecia": (59.33, 18.07),
    "Egipto": (30.04, 31.24),
    "Belgica": (50.85, 4.35),
    "Luxemburgo": (49.61, 6.13),
    "Ucrania": (50.45, 30.52),
    "Azerbaiyan": (40.41, 49.87),
    "Iran": (35.69, 51.39),
    "Argentina": (-34.6, -58.38),
    "NuevaZelanda": (-36.85, 174.76),
    "ArabiaSaudita": (24.71, 46.68),
    "Turquia": (41.01, 28.98),
    "Vietnam": (21.03, 105.85),
    "Filipinas": (14.6, 120.98),
    "Pakistan": (24.86, 67.01),
    "Nigeria": (6.52, 3.38),
    "Kenia": (-1.29, 36.82),
    "Colombia": (4.71, -74.07),
    "Peru": (-12.05, -77.04),
    "Austria": (48.21, 16.37),
    "Portugal": (38.72, -9.14),
    "Grecia": (37.98, 23.73),
    "Chequia": (50.08, 14.44),
    "Hungria": (47.5, 19.04),
    "Rumania": (44.43, 26.1),
}
_ALIAS = {
    "eeuu": "EEUU",
    "ee uu": "EEUU",
    "estados unidos": "EEUU",
    "united states": "EEUU",
    "united states of america": "EEUU",
    "usa": "EEUU",
    "us": "EEUU",
    "u s": "EEUU",
    "u s a": "EEUU",
    "japon": "Japon",
    "japan": "Japon",
    "china": "China",
    "prc": "China",
    "taiwan": "Taiwan",
    "corea": "Corea",
    "corea del sur": "Corea",
    "south korea": "Corea",
    "korea": "Corea",
    "republic of korea": "Corea",
    "alemania": "Alemania",
    "germany": "Alemania",
    "francia": "Francia",
    "france": "Francia",
    "paisesbajos": "PaisesBajos",
    "paises bajos": "PaisesBajos",
    "netherlands": "PaisesBajos",
    "the netherlands": "PaisesBajos",
    "holanda": "PaisesBajos",
    "reinounido": "ReinoUnido",
    "reino unido": "ReinoUnido",
    "united kingdom": "ReinoUnido",
    "uk": "ReinoUnido",
    "gran bretana": "ReinoUnido",
    "great britain": "ReinoUnido",
    "england": "ReinoUnido",
    "inglaterra": "ReinoUnido",
    "israel": "Israel",
    "india": "India",
    "australia": "Australia",
    "europa": "Europa",
    "europe": "Europa",
    "eurozone": "Europa",
    "union europea": "Europa",
    "eu": "Europa",
    "restoeuropa": "RestoEuropa",
    "restomundo": "RestoMundo",
    "canada": "Canada",
    "finlandia": "Finlandia",
    "finland": "Finlandia",
    "noruega": "Noruega",
    "norway": "Noruega",
    "chile": "Chile",
    "rusia": "Rusia",
    "russia": "Rusia",
    "russian federation": "Rusia",
    "emiratos arabes unidos": "EAU",
    "united arab emirates": "EAU",
    "uae": "EAU",
    "eau": "EAU",
    "emiratos": "EAU",
    "singapur": "Singapur",
    "singapore": "Singapur",
    "hong kong": "HongKong",
    "suiza": "Suiza",
    "switzerland": "Suiza",
    "dinamarca": "Dinamarca",
    "denmark": "Dinamarca",
    "brasil": "Brasil",
    "brazil": "Brasil",
    "catar": "Catar",
    "qatar": "Catar",
    "sudafrica": "Sudafrica",
    "south africa": "Sudafrica",
    "panama": "Panama",
    "irlanda": "Irlanda",
    "ireland": "Irlanda",
    "italia": "Italia",
    "italy": "Italia",
    "kazajistan": "Kazajistan",
    "kazakhstan": "Kazajistan",
    "tailandia": "Tailandia",
    "thailand": "Tailandia",
    "lituania": "Lituania",
    "lithuania": "Lituania",
    "malasia": "Malasia",
    "malaysia": "Malasia",
    "argelia": "Argelia",
    "algeria": "Argelia",
    "polonia": "Polonia",
    "poland": "Polonia",
    "indonesia": "Indonesia",
    "kuwait": "Kuwait",
    "espana": "Espana",
    "spain": "Espana",
    "uganda": "Uganda",
    "mexico": "Mexico",
    "suecia": "Suecia",
    "sweden": "Suecia",
    "egipto": "Egipto",
    "egypt": "Egipto",
    "belgica": "Belgica",
    "belgium": "Belgica",
    "luxemburgo": "Luxemburgo",
    "luxembourg": "Luxemburgo",
    "ucrania": "Ucrania",
    "ukraine": "Ucrania",
    "azerbaiyan": "Azerbaiyan",
    "azerbaijan": "Azerbaiyan",
    "iran": "Iran",
    "argentina": "Argentina",
    "nueva zelanda": "NuevaZelanda",
    "new zealand": "NuevaZelanda",
    "nz": "NuevaZelanda",
    "arabia saudita": "ArabiaSaudita",
    "saudi arabia": "ArabiaSaudita",
    "turquia": "Turquia",
    "turkey": "Turquia",
    "turkiye": "Turquia",
    "vietnam": "Vietnam",
    "viet nam": "Vietnam",
    "filipinas": "Filipinas",
    "philippines": "Filipinas",
    "pakistan": "Pakistan",
    "nigeria": "Nigeria",
    "kenia": "Kenia",
    "kenya": "Kenia",
    "colombia": "Colombia",
    "peru": "Peru",
    "austria": "Austria",
    "portugal": "Portugal",
    "grecia": "Grecia",
    "greece": "Grecia",
    "chequia": "Chequia",
    "czech republic": "Chequia",
    "czechia": "Chequia",
    "hungria": "Hungria",
    "hungary": "Hungria",
    "rumania": "Rumania",
    "romania": "Rumania",
}
_CITY = {
    "denver": (39.74, -104.99, "Denver", "EEUU"),
    "dallas": (32.78, -96.8, "Dallas", "EEUU"),
    "san francisco": (37.77, -122.42, "San Francisco", "EEUU"),
    "nueva york": (40.71, -74.01, "Nueva York", "EEUU"),
    "new york": (40.71, -74.01, "New York", "EEUU"),
    "atlanta": (33.75, -84.39, "Atlanta", "EEUU"),
    "omaha": (41.26, -95.93, "Omaha", "EEUU"),
    "las vegas": (36.17, -115.14, "Las Vegas", "EEUU"),
    "boulder": (40.01, -105.27, "Boulder", "EEUU"),
    "herndon": (38.97, -77.39, "Herndon", "EEUU"),
    "kansas city": (39.1, -94.58, "Kansas City", "EEUU"),
    "chicago": (41.88, -87.63, "Chicago", "EEUU"),
    "minneapolis": (44.98, -93.27, "Minneapolis", "EEUU"),
    "portland": (45.52, -122.68, "Portland", "EEUU"),
    "redwood city": (37.49, -122.24, "Redwood City", "EEUU"),
    "fort worth": (32.76, -97.33, "Fort Worth", "EEUU"),
    "jacksonville": (30.33, -81.66, "Jacksonville", "EEUU"),
    "palm beach gardens": (26.82, -80.14, "Palm Beach Gardens", "EEUU"),
    "reston": (38.96, -77.36, "Reston", "EEUU"),
    "greeley": (40.42, -104.71, "Greeley", "EEUU"),
    "ypsilanti": (42.24, -83.61, "Ypsilanti", "EEUU"),
    "carrollton": (32.95, -96.89, "Carrollton", "EEUU"),
    "milwaukee": (43.04, -87.91, "Milwaukee", "EEUU"),
    "toronto": (43.65, -79.38, "Toronto", "Canada"),
    "montreal": (45.5, -73.57, "Montreal", "Canada"),
    "calgary": (51.05, -114.07, "Calgary", "Canada"),
    "sidney": (-33.87, 151.21, "Sídney", "Australia"),
    "sydney": (-33.87, 151.21, "Sydney", "Australia"),
    "canberra": (-35.28, 149.13, "Canberra", "Australia"),
    "dubai": (25.2, 55.27, "Dubái", "EAU"),
    "abu dhabi": (24.45, 54.38, "Abu Dabi", "EAU"),
    "basel": (47.56, 7.59, "Basilea", "Suiza"),
    "schindellegi": (47.17, 8.71, "Schindellegi", "Suiza"),
    "frankfurt": (50.11, 8.68, "Fráncfort", "Alemania"),
    "hamburgo": (53.55, 9.99, "Hamburgo", "Alemania"),
    "hamburg": (53.55, 9.99, "Hamburg", "Alemania"),
    "leipzig": (51.34, 12.37, "Leipzig", "Alemania"),
    "londres": (51.51, -0.13, "Londres", "ReinoUnido"),
    "london": (51.51, -0.13, "London", "ReinoUnido"),
    "kent": (51.28, 0.52, "Kent", "ReinoUnido"),
    "kingston upon thames": (51.41, -0.3, "Kingston upon Thames", "ReinoUnido"),
    "la haya": (52.08, 4.3, "La Haya", "PaisesBajos"),
    "shenzhen": (22.54, 114.06, "Shenzhen", "China"),
    "shanghai": (31.23, 121.47, "Shanghái", "China"),
    "pekin": (39.9, 116.4, "Pekín", "China"),
    "beijing": (39.9, 116.4, "Beijing", "China"),
    "hefei": (31.82, 117.23, "Hefei", "China"),
    "tianjin": (39.34, 117.36, "Tianjín", "China"),
    "hong kong": (22.32, 114.17, "Hong Kong", "HongKong"),
    "singapur": (1.29, 103.85, "Singapur", "Singapur"),
    "singapore": (1.29, 103.85, "Singapore", "Singapur"),
    "baku": (40.41, 49.87, "Bakú", "Azerbaiyan"),
    "ulyanovsk": (54.32, 48.4, "Uliánovsk", "Rusia"),
    "moscu": (55.76, 37.62, "Moscú", "Rusia"),
    "reggio emilia": (44.7, 10.63, "Reggio Emilia", "Italia"),
    "kista": (59.4, 17.95, "Kista", "Suecia"),
    "estocolmo": (59.33, 18.07, "Estocolmo", "Suecia"),
    "swords": (53.46, -6.22, "Swords", "Irlanda"),
    "cork": (51.9, -8.47, "Cork", "Irlanda"),
}
_HQ = {
    "Nvidia": (37.37, -121.96),
    "AMD": (37.4, -121.98),
    "Intel": (45.53, -122.93),
    "Apple": (37.33, -122.03),
    "Microsoft": (47.64, -122.13),
    "Alphabet": (37.42, -122.08),
    "Google": (37.42, -122.08),
    "Meta": (37.48, -122.15),
    "Amazon": (47.62, -122.34),
    "Oracle": (30.55, -97.69),
    "Dell": (30.3, -97.69),
    "Broadcom": (37.41, -121.97),
    "Qualcomm": (32.9, -117.2),
    "OpenAI": (37.77, -122.42),
    "Anthropic": (37.77, -122.42),
    "Micron": (43.61, -116.21),
    "Marvell": (37.41, -121.97),
    "SpaceX": (33.92, -118.33),
    "RocketLab": (33.83, -118.15),
    "AST_SpaceMobile": (31.99, -102.08),
    "Anduril": (33.65, -117.74),
    "ShieldAI": (32.9, -117.2),
    "Kratos_Defense": (32.9, -117.2),
    "Iridium": (38.93, -77.18),
    "TSMC": (24.77, 120.99),
    "Samsung": (37.27, 127.05),
    "SKHynix": (37.21, 127.1),
    "SMIC": (31.21, 121.59),
    "HiSilicon": (22.58, 114.06),
    "Huawei": (22.65, 114.06),
    "Cambricon": (39.98, 116.31),
    "Foxconn": (25.01, 121.46),
    "TokyoOhka": (35.53, 139.7),
    "SonySemi": (35.63, 139.74),
    "ASML": (51.41, 5.42),
    "ASM": (52.34, 4.86),
    "Infineon": (48.21, 11.62),
    "STMicro": (45.78, 4.88),
    "Zeiss": (48.45, 9.95),
    "Trumpf": (48.8, 9.06),
    "Nokia": (60.21, 24.81),
    "Ericsson": (59.4, 17.95),
    "QuantumMachines": (32.08, 34.78),
    "SaudiAramco": (26.29, 50.11),
    "Petrobras": (-22.91, -43.17),
    "QatarEnergy": (25.29, 51.53),
    "Trafigura": (1.28, 103.85),
    "Vale": (-22.91, -43.17),
    "GrupoMexico": (19.43, -99.13),
    "Cemex": (25.65, -100.4),
    "PIF_SaudiArabia": (24.71, 46.68),
    "Temasek": (1.28, 103.85),
    "GIC_Singapore": (1.28, 103.85),
    "QIA": (25.29, 51.53),
    "Qatar_Airways_Cargo": (25.26, 51.61),
}
_US_HUBS = [
    (37.39, -122.08, "Silicon Valley"),
    (47.61, -122.33, "Seattle"),
    (30.27, -97.74, "Austin"),
    (40.71, -74.01, "New York"),
    (42.36, -71.06, "Boston"),
    (33.45, -112.07, "Phoenix"),
    (32.78, -96.8, "Dallas"),
    (34.05, -118.24, "Los Angeles"),
    (45.52, -122.68, "Portland"),
]

_CITY_KEYS = sorted(_CITY, key=lambda k: -len(k))   # estable, igual que el sort del JS
_GENERIC = {'RestoMundo', 'RestoEuropa'}
# Países demasiado grandes para exponer "a todo el país" por un evento local.
_BIG_COUNTRIES = {'EEUU', 'China', 'Rusia', 'Canada', 'Australia', 'Brasil', 'India', 'Europa',
                  'RestoMundo', 'RestoEuropa', 'Kazajistan', 'Argentina', 'Mexico', 'Indonesia',
                  'Argelia', 'ArabiaSaudita', 'Iran'}
# Solo para leer el país del TEXTO de un evento ("…, CA", "…, Alaska").
_PLACE_EXTRA = {
    'alaska': 'EEUU', 'california': 'EEUU', 'ca': 'EEUU', 'hawaii': 'EEUU', 'texas': 'EEUU',
    'nevada': 'EEUU', 'oklahoma': 'EEUU', 'washington': 'EEUU', 'oregon': 'EEUU', 'idaho': 'EEUU',
    'montana': 'EEUU', 'wyoming': 'EEUU', 'utah': 'EEUU', 'arizona': 'EEUU', 'new mexico': 'EEUU',
    'colorado': 'EEUU', 'puerto rico': 'EEUU', 'district of columbia': 'EEUU', 'mx': 'Mexico',
    'b c': 'Mexico', 'japan region': 'Japon', 'taiwan region': 'Taiwan',
    'gaza strip': 'Israel', 'west bank': 'Israel', 'republic of china': 'Taiwan',
    'south korea region': 'Corea', 'north korea': None,
}


def _js_norm(s):
    """Igual que norm() del JS: NFD, sin U+0300–U+036F, minúsculas, [^a-z0-9]→espacio."""
    s = unicodedata.normalize('NFD', '' if s is None else str(s))
    s = ''.join(ch for ch in s if not (0x300 <= ord(ch) <= 0x36F))
    return re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()


def _fnv(s):
    """FNV-1a sobre unidades UTF-16 (como str.charCodeAt en JS) → uint32."""
    h = 2166136261
    b = str(s).encode('utf-16-le', 'surrogatepass')
    for i in range(0, len(b), 2):
        h ^= b[i] | (b[i + 1] << 8)
        h = (h * 16777619) & 0xFFFFFFFF
    return h


def _jitter(seed, amp):
    a = ((seed % 1000) / 1000) * 2 - 1
    x = seed - 0x100000000 if seed >= 0x80000000 else seed   # ToInt32
    x >>= 10                                                 # >> aritmético
    r = abs(x) % 1000
    r = -r if x < 0 else r                                   # % de JS (signo del dividendo)
    b = (r / 1000) * 2 - 1
    return a * amp, b * amp


def country_key(raw):
    """Texto libre de país → clave del catálogo ('Estados Unidos (HQ…)' → 'EEUU')."""
    if not raw:
        return None
    raw = str(raw)
    if raw in _COUNTRY:
        return raw
    n = _js_norm(raw)
    if n in _ALIAS:
        return _ALIAS[n]
    first = _js_norm(re.split(r'[/(,;—–]', raw)[0])
    if first and first in _ALIAS:
        return _ALIAS[first]
    return None


def _city_hint(raw):
    s = ' ' + _js_norm(raw) + ' '
    if len(s) <= 2:
        return None
    best, bi = None, float('inf')
    for k in _CITY_KEYS:
        i = s.find(' ' + k + ' ')
        if 0 <= i < bi:
            bi, best = i, k
    return best


def _norm_country(node):
    k = country_key(node.get('country'))
    if k and k not in _GENERIC:
        return k
    k2 = country_key(node.get('loc'))
    if k2 and not (k and k2 in _GENERIC):
        return k2
    return k or k2 or 'RestoMundo'


def geo_coord(node):
    """Réplica de GeoCoords.geoCoord(node): {lat, lng, label, precision, country, precise}."""
    if not node:
        return {'lat': 0, 'lng': 0, 'label': '?', 'precision': 'unknown', 'precise': False}
    nid = node.get('id') or node.get('label') or ''
    if nid in _HQ:
        la, lo = _HQ[nid][0], _HQ[nid][1]
        return {'lat': la, 'lng': lo, 'label': node.get('loc') or nid, 'precise': True,
                'precision': 'hq', 'country': _norm_country(node)}
    ck = _city_hint((node.get('country') or '') + ' | ' + (node.get('loc') or ''))
    if ck:
        c = _CITY[ck]
        dj, dk = _jitter(_fnv(nid + 'c'), 0.08)
        return {'lat': c[0] + dj, 'lng': c[1] + dk, 'label': c[2], 'precise': True,
                'precision': 'city', 'country': c[3]}
    country = _norm_country(node)
    if country == 'EEUU':
        hub = _US_HUBS[_fnv(nid) % len(_US_HUBS)]
        dj, dk = _jitter(_fnv(nid + 'us'), 1.1)
        return {'lat': hub[0] + dj, 'lng': hub[1] + dk, 'label': hub[2], 'precise': False,
                'precision': 'hub', 'country': country}
    base = _COUNTRY.get(country) or _COUNTRY['RestoMundo']
    dj, dk = _jitter(_fnv(nid), 2.2 if country in ('China', 'Europa') else 1.1)
    return {'lat': base[0] + dj, 'lng': base[1] + dk, 'label': node.get('loc') or country,
            'precise': False, 'precision': 'country' if country != 'RestoMundo' else 'unknown',
            'country': country}


def place_country(text):
    """País (clave del catálogo) desde el texto de lugar de un evento:
    'Kyiv, Kyyiv, Misto, Ukraine' → 'Ucrania'; '12 km SE of Hualien City, Taiwan'
    → 'Taiwan'; 'Ridgecrest, CA' → 'EEUU'. None si no se reconoce."""
    if not text:
        return None
    parts = [p.strip() for p in str(text).split(',') if p.strip()]
    for cand in (parts[-1:] if parts else []) + [str(text)]:
        n = _js_norm(re.sub(r'\(.*?\)', ' ', cand))
        if n in _PLACE_EXTRA:
            return _PLACE_EXTRA[n]
        k = country_key(cand)
        if k:
            return k
    return None


def haversine_km(lat1, lon1, lat2, lon2):
    rad = math.pi / 180
    dlat, dlon = (lat2 - lat1) * rad, (lon2 - lon1) * rad
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1 * rad) * math.cos(lat2 * rad) * math.sin(dlon / 2) ** 2
    return 2 * 6371.0088 * math.asin(min(1.0, math.sqrt(a)))


def _js_round(x):
    return int(math.floor(x + 0.5))


_NRS_GEO = {'China': 28, 'Taiwan': 25, 'Korea': 15, 'Japan': 12, 'EEUU': 8, 'Europa': 10, 'Israel': 18}


def client_nrs(node, degree):
    """MISMA fórmula que computeNRS() de app.html (sin el acotado de margen de
    ontology/agents.py) para que el número coincida con el que ve el usuario."""
    geo = _NRS_GEO.get(node.get('country'), 15)
    chain = min(25, degree * 2.5)
    margin = node.get('margin')
    try:
        margin = 0.15 if margin is None else float(margin)
    except (TypeError, ValueError):
        margin = 0.15
    market = _js_round((1 - min(1, margin / 0.4)) * 20)
    growth = str(node.get('growth') or '').lower()
    fundamental = min(15, (10 if node.get('preipo') else 0) +
                      (5 if '🔴' in growth else 2 if '🟡' in growth else 0))
    conc = 10 if node.get('country') in ('Taiwan', 'China') else 4
    return min(100, max(0, _js_round(geo + chain + market + fundamental + conc)))


_GRAPH = {'data': None}
_GRAPH_LOCK = threading.Lock()


def _graph():
    """Snapshot del grafo (data/grafo_v0.json) con coordenadas + NRS, una vez."""
    if _GRAPH['data'] is not None:
        return _GRAPH['data']
    with _GRAPH_LOCK:
        if _GRAPH['data'] is not None:
            return _GRAPH['data']
        try:
            with open(_SNAPSHOT, encoding='utf-8') as fh:
                snap = json.load(fh)
        except Exception as e:  # noqa: BLE001
            log.warning('world: snapshot no disponible: %s', e)
            snap = {'nodes': [], 'links': []}
        deg = {}
        for lk in snap.get('links') or []:
            s, t = lk.get('source'), lk.get('target')
            deg[s] = deg.get(s, 0) + 1
            if t != s:
                deg[t] = deg.get(t, 0) + 1
        # G4d: el NRS usa el grado ESTRUCTURAL (pares distintos de flujo), la
        # misma regla que app.html computeNRS; `degree` (todas las filas) se
        # conserva para ordenar.
        from ontology import vocabulary as _vocab
        flow_deg = _vocab.flow_degree(snap.get('links') or [])
        sectors = snap.get('sectors9') or {}
        nodes, by_id, by_country = [], {}, {}
        for n in snap.get('nodes') or []:
            if not n.get('id'):
                continue
            g = geo_coord(n)
            sec = sectors.get(n.get('sector')) or {}
            rec = {
                'id': n['id'], 'label': n.get('label') or n['id'],
                'ticker': n.get('mkt') or None, 'sector': n.get('sector'),
                'sector_es': sec.get('label'), 'sector_en': sec.get('en'), 'cat': n.get('cat'),
                'lat': g['lat'], 'lng': g['lng'], 'precision': g['precision'],
                'place': g.get('label'), 'country_key': g.get('country'),
                'degree': deg.get(n['id'], 0), 'flow_degree': flow_deg.get(n['id'], 0),
                'nrs': client_nrs(n, flow_deg.get(n['id'], 0)),
            }
            nodes.append(rec)
            by_id[rec['id']] = rec
            by_country.setdefault(rec['country_key'], []).append(rec)
        for lst in by_country.values():
            lst.sort(key=lambda r: (-r['degree'], r['id']))
        _GRAPH['data'] = {'nodes': nodes, 'by_id': by_id, 'by_country': by_country,
                          'precise': [r for r in nodes if r['precision'] in ('hq', 'city')]}
        return _GRAPH['data']


# ═══════════════════════════════════════════════════════════════════════════
# 2. HTTP + acelerador compartido de GDELT
# ═══════════════════════════════════════════════════════════════════════════
GDELT_MIN_GAP = 5.5
_GDELT_LOCK = threading.Lock()
_GDELT_LAST = [0.0]


_SRC = {}
_SRC_LOCK = threading.Lock()


def _env_int(name, default):
    try:
        return max(1, int(os.environ.get(name) or default))
    except ValueError:
        return default


def source_down(name, now=None):
    """'source_down:<fuente>:<error>' si la fuente está en pausa; None si se
    puede consultar (también cuando la pausa venció: UNA consulta de prueba)."""
    now = _now() if now is None else now
    with _SRC_LOCK:
        st = _SRC.get(name)
        if st and st.get('until', 0) > now:
            return f"source_down:{name}:{st['err']}"
    return None


def source_result(name, err, now=None):
    """Registra el resultado de una consulta. Éxito → reinicia. Solo los
    errores DEFINITIVOS (404/410/401/403) cuentan; los pasajeros (timeout, 429,
    5xx, red) ni cuentan ni reinician."""
    now = _now() if now is None else now
    with _SRC_LOCK:
        st = _SRC.setdefault(name, {'fails': 0, 'until': 0.0, 'err': None, 'last_ok': None, 'down_since': None})
        if err is None:
            st.update(fails=0, until=0.0, err=None, last_ok=now, down_since=None)
            return
        head, _, code = str(err).partition(':')
        if head != 'http' or code not in _DEFINITIVE_HTTP:
            return
        st['fails'] += 1
        st['err'] = str(err)
        if st['fails'] >= _env_int('WORLD_SOURCE_DOWN_AFTER', SOURCE_DOWN_AFTER):
            st['until'] = now + _env_int('WORLD_SOURCE_DOWN_TTL', SOURCE_DOWN_TTL)
            if st['down_since'] is None:
                st['down_since'] = now
                log.warning('world: fuente %s en pausa (%s) — se reintenta cada %ss', name, err,
                            _env_int('WORLD_SOURCE_DOWN_TTL', SOURCE_DOWN_TTL))


def source_retry_at(name):
    with _SRC_LOCK:
        st = _SRC.get(name)
        return st.get('until') if st and st.get('until') else None


def sources_state():
    """Estado de las fuentes con pausa (para /api/world/events, el 🩺 y tests)."""
    with _SRC_LOCK:
        return {n: {'fails': st['fails'], 'paused': bool(st.get('until', 0) > _now()), 'error': st['err'],
                    'retry_at': _iso(st['until']) if st.get('until') else None,
                    'down_since': _iso(st['down_since']) if st.get('down_since') else None,
                    'last_ok': _iso(st['last_ok']) if st.get('last_ok') else None}
                for n, st in _SRC.items()}


def gdelt_throttle(max_wait=20.0):
    """Espaciado COMPARTIDO de GDELT (World Monitor + Sala de Situación): cada
    llamador RESERVA un turno (slot = max(ahora, último + GDELT_MIN_GAP)) bajo
    el candado y duerme FUERA de él. Si su turno cae a más de max_wait s,
    devuelve False sin reservar (el llamador no consulta). Así max_wait se
    respeta también con varios hilos a la vez (antes cada uno esperaba el
    candado sin límite y la rama 'ocupado' nunca se daba)."""
    with _GDELT_LOCK:
        now = _now()
        slot = max(now, _GDELT_LAST[0] + GDELT_MIN_GAP)
        if slot - now > max_wait:
            return False
        _GDELT_LAST[0] = slot
    delay = slot - now
    if delay > 0:
        time.sleep(delay)
    return True


def _http_get_json(url, params=None, timeout=10):
    """GET → (json, código_de_error). GDELT a veces responde JSON con
    content-type de texto, así que se parsea el cuerpo directamente. Los
    errores son CÓDIGOS (ver err_info) para poder mostrarlos en es/en."""
    try:
        r = requests.get(url, params=params, timeout=timeout,
                         headers={'User-Agent': _UA, 'Accept': 'application/json'})
    except requests.exceptions.Timeout:
        return None, 'timeout'
    except requests.exceptions.ConnectionError:
        host = re.sub(r'^https?://([^/]+).*$', r'\1', url)
        return None, f'conn:{host}'
    except Exception as e:  # noqa: BLE001
        return None, f'exc:{type(e).__name__}: {str(e)[:100]}'
    if r.status_code == 429:
        return None, 'rate_limited'
    if r.status_code != 200:
        return None, f'http:{r.status_code}'
    try:
        return json.loads(r.text), None
    except ValueError:
        return None, 'nonjson:' + (r.text or '')[:80].strip()


# ═══════════════════════════════════════════════════════════════════════════
# 3. Parsers (formas de payload reales de cada fuente)
# ═══════════════════════════════════════════════════════════════════════════
_A_RE = re.compile(r'<a\s[^>]*href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
_TITLE_RE = re.compile(r'title\s*=\s*["\']([^"\']*)["\']', re.I)
_TAG_RE = re.compile(r'<[^>]+>')


def _articles_from_html(h, limit=3):
    """El 'html' de un punto GDELT trae enlaces <a href=… title=…>…</a>."""
    out = []
    for m in _A_RE.finditer(h or ''):
        url = _safe_url(_html.unescape(m.group(1)))
        if not url:
            continue
        tm = _TITLE_RE.search(m.group(0))
        title = _html.unescape(tm.group(1) if tm and tm.group(1).strip() else _TAG_RE.sub('', m.group(2)))
        title = re.sub(r'\s+', ' ', title).strip()
        out.append({'url': url, 'title': title[:220]})
        if len(out) >= limit:
            break
    return out


def _stable_id(*parts):
    return hashlib.md5('|'.join(str(p) for p in parts).encode('utf-8')).hexdigest()[:12]


def _valid_ll(lat, lon):
    return lat is not None and lon is not None and -90 <= lat <= 90 and -180 <= lon <= 180


def gdelt_severity(count, window='24h'):
    """0-100 por intensidad de cobertura: nº de artículos por día en ese lugar
    (escala log: 1/día≈31, 3≈47, 7≈63, 15≈79, 31+≈95)."""
    days = WINDOWS.get(window, 86400) / 86400
    per_day = max(0.0, float(count or 0)) / days
    return int(min(100, round(15 + 16 * math.log2(1 + per_day))))


def parse_gdelt_geo(payload, layer, window='24h', now=None, limit=150):
    """GeoJSON de GDELT GEO 2.0 (mode=PointData) → items.
    Cada feature: geometry.coordinates=[lon,lat], properties={name, count, html…}."""
    now = _now() if now is None else now
    if not isinstance(payload, dict) or not isinstance(payload.get('features'), list):
        raise ValueError('bad_payload:GDELT')
    items = []
    for f in payload['features']:
        try:
            g = f.get('geometry') or {}
            c = g.get('coordinates') or []
            if g.get('type') != 'Point' or len(c) < 2:
                continue
            lon, lat = float(c[0]), float(c[1])
            if not _valid_ll(lat, lon):
                continue
            p = f.get('properties') or {}
            name = _html.unescape(str(p.get('name') or '')).strip()
            count = int(float(p.get('count') or p.get('numarts') or 0))
            arts = _articles_from_html(p.get('html') or '')
            items.append({
                'id': f'{layer}:{_stable_id(name, round(lat, 3), round(lon, 3))}',
                'layer': layer, 'lat': round(lat, 4), 'lon': round(lon, 4),
                'title': (arts[0]['title'] if arts and arts[0]['title'] else name) or '?',
                'place': name, 'country_key': place_country(name),
                'severity': gdelt_severity(count, window), 'count': count,
                # GDELT agrega por ventana: NO hay hora del evento. 'time' va
                # vacío (antes era la hora de la consulta y un agente lo leía
                # como "ahora"); fetched_at = cuándo lo consultamos.
                'time': None, 'ts': None, 'time_kind': 'window', 'window': window,
                'fetched_at': _iso(now),
                'source': 'GDELT', 'url': arts[0]['url'] if arts else None,
                'articles': arts,
            })
        except (TypeError, ValueError, AttributeError):
            continue
    items.sort(key=lambda i: (-i['count'], i['id']))
    return items[:limit]


def quake_severity(mag, alert=None, tsunami=False):
    """0-100: magnitud (M4.5≈13, M5.5≈38, M6.5≈63, M7.5≈88) + alerta PAGER de
    USGS (amarilla +10, naranja +20, roja +30) + aviso de tsunami (+10)."""
    try:
        m = float(mag)
    except (TypeError, ValueError):
        return 0
    s = (m - 4.0) * 25
    s += {'yellow': 10, 'orange': 20, 'red': 30}.get((alert or '').lower(), 0)
    if tsunami:
        s += 10
    return int(max(0, min(100, round(s))))


def parse_usgs(payload):
    """GeoJSON de USGS (feeds summary) → items. coordinates=[lon, lat, depth_km],
    properties={mag, place, time(ms), url, title, alert, tsunami, sig…}."""
    if not isinstance(payload, dict) or not isinstance(payload.get('features'), list):
        raise ValueError('bad_payload:USGS')
    items = []
    for f in payload['features']:
        try:
            p = f.get('properties') or {}
            c = (f.get('geometry') or {}).get('coordinates') or []
            if len(c) < 2:
                continue
            lon, lat = float(c[0]), float(c[1])
            if not _valid_ll(lat, lon):
                continue
            ts = float(p['time']) / 1000.0 if p.get('time') is not None else None
            mag = p.get('mag')
            place = p.get('place') or ''
            title = p.get('title') or (f'M {mag} - {place}' if mag is not None else place)
            items.append({
                'id': 'quakes:' + str(f.get('id') or _stable_id(lat, lon, ts)),
                'layer': 'quakes', 'lat': round(lat, 4), 'lon': round(lon, 4),
                'title': title, 'place': place, 'country_key': place_country(place),
                'severity': quake_severity(mag, p.get('alert'), bool(p.get('tsunami'))),
                'mag': mag, 'depth_km': round(float(c[2]), 1) if len(c) > 2 and c[2] is not None else None,
                'alert': p.get('alert'), 'tsunami': bool(p.get('tsunami')),
                'time': _iso(ts), 'ts': ts, 'time_kind': 'exact',
                'source': 'USGS', 'url': _safe_url(p.get('url')),
            })
        except (TypeError, ValueError, KeyError, AttributeError):
            continue
    return items


_NAT_BASE = {'volcanoes': 55, 'severeStorms': 45, 'floods': 45, 'earthquakes': 40, 'wildfires': 30,
             'landslides': 35, 'manmade': 35, 'drought': 30, 'tempExtremes': 30, 'dustHaze': 15,
             'snow': 15, 'seaLakeIce': 8, 'waterColor': 8}


def natural_severity(cat_id, mag_value=None, mag_unit=None):
    """0-100 ESTIMADA por categoría (volcán 55, tormenta/inundación 45,
    incendio 30…) + magnitud cuando EONET la da: viento en nudos (kts × 0.7)
    o área de incendio en acres (+8·log10(1+acres), tope +40)."""
    s = float(_NAT_BASE.get(cat_id, 25))
    try:
        v = float(mag_value) if mag_value is not None else None
    except (TypeError, ValueError):
        v = None
    unit = (mag_unit or '').lower()
    if v is not None and v > 0:
        if unit == 'kts':
            s = max(s, v * 0.7)
        elif unit == 'acres':
            s += min(40.0, 8 * math.log10(1 + v))
    return int(max(0, min(100, round(s))))


def _centroid(coords):
    """Centroide simple del primer anillo de un Polygon GeoJSON."""
    ring = coords[0] if coords and isinstance(coords[0], list) and coords[0] and isinstance(coords[0][0], list) else coords
    pts = [(float(p[0]), float(p[1])) for p in ring if isinstance(p, (list, tuple)) and len(p) >= 2]
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]              # el anillo GeoJSON repite el primer vértice al cerrar
    if not pts:
        return None
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


def parse_eonet(payload):
    """EONET v3 /events → items (última geometría de cada evento abierto)."""
    if not isinstance(payload, dict) or not isinstance(payload.get('events'), list):
        raise ValueError('bad_payload:EONET')
    items = []
    for ev in payload['events']:
        try:
            geoms = ev.get('geometry') or ev.get('geometries') or []
            if not geoms:
                continue
            geoms = sorted(geoms, key=lambda g: _parse_iso(g.get('date')) or 0)
            g = geoms[-1]
            coords = g.get('coordinates') or []
            if g.get('type') == 'Point' and len(coords) >= 2:
                lon, lat = float(coords[0]), float(coords[1])
            elif g.get('type') == 'Polygon':
                cc = _centroid(coords)
                if not cc:
                    continue
                lon, lat = cc
            else:
                continue
            if not _valid_ll(lat, lon):
                continue
            cats = ev.get('categories') or [{}]
            cat_id = str(cats[0].get('id') or '')
            srcs = ev.get('sources') or []
            url = _safe_url(srcs[0].get('url') if srcs else None) or _safe_url(ev.get('link'))
            ts = _parse_iso(g.get('date'))
            items.append({
                'id': 'natural:' + str(ev.get('id') or _stable_id(lat, lon)),
                'layer': 'natural', 'lat': round(lat, 4), 'lon': round(lon, 4),
                'title': ev.get('title') or cats[0].get('title') or '?',
                'place': ev.get('title') or '', 'country_key': place_country(ev.get('title') or ''),
                'category': cat_id, 'category_title': cats[0].get('title'),
                'severity': natural_severity(cat_id, g.get('magnitudeValue'), g.get('magnitudeUnit')),
                'magnitude': g.get('magnitudeValue'), 'magnitude_unit': g.get('magnitudeUnit'),
                'time': _iso(ts), 'ts': ts, 'time_kind': 'last_update',
                'source': 'NASA EONET', 'url': url,
            })
        except (TypeError, ValueError, AttributeError, IndexError):
            continue
    return items


# ═══════════════════════════════════════════════════════════════════════════
# 4. Fetchers por capa
# ═══════════════════════════════════════════════════════════════════════════
def gdelt_query(layer):
    return os.environ.get('WORLD_GDELT_QUERY_' + layer.upper()) or _GDELT_Q[layer]


def _gdelt_events_on():
    return os.environ.get('WORLD_GDELT_EVENTS', 'on').lower() not in ('off', '0', 'no')


def _fetch_gdelt_events(layer, window):
    """2026-10-05: conflicto/protestas/sanciones desde los ARCHIVOS CRUDOS de eventos de
    GDELT 2.0 (cada 15 min, core/gdelt_events.py) — la API GEO fue retirada."""
    from core import gdelt_events as GE
    down = source_down('gdelt_events')
    if down:
        return None, down
    err = GE.refresh()
    if err and not GE._STORE['batches']:
        source_result('gdelt_events', err)
        return None, source_down('gdelt_events') or err
    source_result('gdelt_events', None)
    win = WINDOWS[window]
    now = _now()
    items = []
    for g in GE.aggregate(layer, win, gdelt_severity):
        code = max(g['codes'], key=g['codes'].get) if g['codes'] else ''
        les, len_ = GE.label_of(code, True), GE.label_of(code, False)
        place = g['place'] or f"{g['lat']:.1f}, {g['lon']:.1f}"
        arts = [{'url': u, 'title': re.sub(r'^https?://(www\.)?', '', u).split('/')[0]} for u in g['urls'] if _safe_url(u)]
        items.append({
            'id': f"{layer}:{_stable_id(round(g['lat'], 1), round(g['lon'], 1))}",
            'layer': layer, 'lat': round(g['lat'], 4), 'lon': round(g['lon'], 4),
            'title': f"{les or ''} · {place}".strip(' ·'), 'title_es': f"{les or ''} · {place}".strip(' ·'),
            'title_en': f"{len_ or ''} · {place}".strip(' ·'), 'place': place, 'country_key': place_country(place),
            'severity': GE.severity(g['articles'], g['sources']), 'count': g['articles'], 'events': g['events'],
            'sources_n': g['sources'], 'distinct_articles': g.get('distinct_articles'), 'precision': 'country' if g['geo_type'] == 1 else 'city',
            'goldstein': round(sum(g['gold']) / len(g['gold']), 1) if g['gold'] else None,
            'time': _iso(g['last']), 'ts': g['last'], 'time_kind': 'last_update', 'window': window,
            'fetched_at': _iso(now), 'source': 'GDELT 2.0 Events', 'source_es': 'GDELT 2.0 · eventos (15 min)',
            'source_en': 'GDELT 2.0 · events (15 min)', 'url': arts[0]['url'] if arts else None, 'articles': arts,
            'press_signal': True,
        })
    return items, None


def _fetch_gdelt(layer, window):
    if _gdelt_events_on():
        return _fetch_gdelt_events(layer, window)
    down = source_down('gdelt_geo')
    if down:
        return None, down            # en pausa: ni red ni turno del acelerador compartido
    if not gdelt_throttle():
        return None, 'busy'
    url = os.environ.get('WORLD_GDELT_GEO_URL') or GDELT_GEO_URL
    data, err = _http_get_json(url, params={
        'query': gdelt_query(layer), 'mode': 'PointData', 'format': 'GeoJSON',
        'timespan': window, 'maxpoints': 250}, timeout=12)
    source_result('gdelt_geo', err)
    if err:
        return None, source_down('gdelt_geo') or err
    return parse_gdelt_geo(data, layer, window), None


def _fetch_quakes(_window):
    data, err = _http_get_json(USGS_URL, timeout=10)
    if err:
        return None, err
    return parse_usgs(data), None


def _fetch_natural(_window):
    data, err = _http_get_json(EONET_URL, params={'status': 'open', 'days': 8, 'limit': 400}, timeout=12)
    if err:
        return None, err
    items = parse_eonet(data)
    items.sort(key=lambda i: (-(i['severity'] or 0), i['id']))
    return items[:300], None


def _situation():
    from core.geosit import situation_data
    return situation_data()


def _curated_source(news):
    """Etiqueta de fuente de las capas curadas, en es/en ('source' = inglés)."""
    if news:
        return {'source': 'Khipu (curated) + GDELT', 'source_es': 'Khipu (curado) + GDELT',
                'source_en': 'Khipu (curated) + GDELT'}
    return {'source': 'Khipu (curated)', 'source_es': 'Khipu (curado)', 'source_en': 'Khipu (curated)'}


def _cached_items(layer, window='*'):
    """Ítems YA en caché de otra capa (no dispara descargas): para mezclar lo curado con lo vivo."""
    with _LOCK:
        e = _CACHE.get((layer, window)) or (_CACHE.get((layer, '24h')) if window == '*' else None)
    return list((e or {}).get('items') or []) if e and e.get('ok') else []


def _blend_live_chokepoint(item):
    """2026-10-05: el estrecho curado suma el tránsito REAL de buques (FMI PortWatch) si lo hay:
    severidad = máx(curada, caída medida). Antes Ormuz decía 55 con el tráfico −64 %."""
    live = next((x for x in _cached_items('shipping') if x.get('ref_id') == item['ref_id']), None)
    if not live:
        return item
    item['live_shipping'] = {k: live.get(k) for k in ('change_pct', 'transits_7d_avg', 'transits_base_avg', 'time', 'data_caveat')}
    if (live.get('severity') or 0) > (item['severity'] or 0):
        item['severity'] = live['severity']
        item['live_driven'] = True
    return item


def _blend_live_country(item):
    """País curado + riesgo-país OFICIAL (Dpto. de Estado) + eventos de conflicto en vivo (GDELT) en el país."""
    ck = item.get('country_key')
    adv = next((x for x in _cached_items('advisories') if ck and x.get('country_key') == ck), None)
    evs = [x for x in _cached_items('conflict', '24h') + _cached_items('unrest', '24h') if ck and x.get('country_key') == ck]
    if adv:
        item['advisory_level'] = adv.get('level')
        if (adv.get('severity') or 0) > (item['severity'] or 0):
            item['severity'], item['live_driven'] = adv['severity'], True
    if evs:
        item['live_events'] = {'count': len(evs), 'max_severity': max(x.get('severity') or 0 for x in evs),
                               'top': (evs[0].get('title_es') or evs[0].get('title'))}
        bump = min(10, 2 * len(evs))
        if bump:
            item['severity'] = int(min(100, (item['severity'] or 0) + bump))
            item['live_driven'] = True
    return item


def _fetch_chokepoints(_window):
    d = _situation()
    g = _graph()
    now = _now()
    items = []
    for c in d.get('chokepoints') or []:
        news = c.get('news') or None
        affected = [a for a in (c.get('affected') or []) if a in g['by_id']]
        items.append({
            'id': 'chokepoints:' + c['id'], 'ref_id': c['id'], 'layer': 'chokepoints',
            'lat': c['lat'], 'lon': c['lon'], 'title': c.get('es'), 'title_es': c.get('es'),
            'title_en': c.get('en'), 'place': c.get('en'), 'country_key': None,
            'severity': int(round(c.get('score') or 0)), 'score': c.get('score'), 'base': c.get('base'),
            'news': news, 'factors': c.get('factors') or [], 'affected': affected,
            'why_es': c.get('why_es'), 'why_en': c.get('why_en'), 'sectors': c.get('sectors') or [],
            'time': None, 'ts': None, 'time_kind': 'current', 'fetched_at': _iso(now),
            **_curated_source(news), 'url': None,
        })
    items = [_blend_live_chokepoint(i) for i in items]
    items.sort(key=lambda i: -(i['severity'] or 0))
    return items, None


def _fetch_instability(_window):
    d = _situation()
    now = _now()
    items = []
    for c in d.get('instability') or []:
        if c.get('lat') is None or c.get('lon') is None:
            continue
        news = c.get('news') or None
        items.append({
            'id': 'instability:' + c['id'], 'ref_id': c['id'], 'layer': 'instability',
            'lat': c['lat'], 'lon': c['lon'], 'title': c.get('es'), 'title_es': c.get('es'),
            'title_en': c.get('en'), 'place': c.get('en'), 'country_key': c.get('country_key'),
            'severity': int(round(c.get('score') or 0)), 'score': c.get('score'), 'base': c.get('base'),
            'news': news, 'factors': c.get('factors') or [],
            'time': None, 'ts': None, 'time_kind': 'current', 'fetched_at': _iso(now),
            **_curated_source(news), 'url': None,
        })
    items = [_blend_live_country(i) for i in items]
    items.sort(key=lambda i: -(i['severity'] or 0))
    return items, None


_FETCHERS = {
    'conflict': lambda w: _fetch_gdelt('conflict', w),
    'unrest': lambda w: _fetch_gdelt('unrest', w),
    'trade': lambda w: _fetch_gdelt('trade', w),
    'quakes': _fetch_quakes,
    'natural': _fetch_natural,
    'chokepoints': _fetch_chokepoints,
    'instability': _fetch_instability,
    'shipping': lambda w: _feeds().fetch_shipping(w),
    'policy': lambda w: _feeds().fetch_policy(w),
    'disasters': lambda w: _feeds().fetch_disasters(w),
    'advisories': lambda w: _feeds().fetch_advisories(w),
    'outages': lambda w: _feeds().fetch_outages(w),
}


def _feeds():
    from core import world_feeds
    return world_feeds
_SYNC_LAYERS = ('chokepoints', 'instability')   # cálculo local: sin hilo
CURATED_LAYERS = _SYNC_LAYERS


def _curated_as_of():
    try:
        from core.geosit import CURATED_AS_OF
        return CURATED_AS_OF
    except Exception:  # noqa: BLE001
        return None


def _news_live():
    """¿La parte de noticias (GDELT DOC) de las capas curadas está respondiendo?"""
    return source_down('gdelt_doc') is None


# ═══════════════════════════════════════════════════════════════════════════
# 5. Caché por capa — stale-while-revalidate con errores aislados
# ═══════════════════════════════════════════════════════════════════════════
_CACHE = {}
_INFLIGHT = {}
_LOCK = threading.Lock()


def _reset_cache():
    """Solo para tests."""
    with _LOCK:
        _CACHE.clear()
        _INFLIGHT.clear()
    _BRIEF_CACHE.clear()
    with _SRC_LOCK:
        _SRC.clear()


def prewarm(window='24h'):
    """W1: tarea del reloj del servidor — refresca en segundo plano las capas
    vencidas para que el primer visitante no vea 'cargando'. No espera (wait=0)
    ni consulta una fuente en pausa."""
    res = world_events(window=window, wait=0)
    return {k: ('ok' if v.get('ok') else v.get('error_code') or 'pending') for k, v in res['sources'].items()}


def _fetch_key(layer, window):
    # GDELT se consulta por ventana; USGS/EONET/curados, una vez y se filtra.
    return (layer, window) if layer in GDELT_LAYERS else (layer, '*')


def _refresh(layer, key, window):
    try:
        items, err = _FETCHERS[layer](window)
    except ValueError as e:
        msg = str(e)
        items, err = None, (msg if msg.startswith('bad_payload:') else f'exc:ValueError: {msg[:140]}')
    except Exception as e:  # noqa: BLE001 — una capa rota NO tumba a las demás
        items, err = None, f'exc:{type(e).__name__}: {str(e)[:140]}'
    now = _now()
    with _LOCK:
        prev = _CACHE.get(key) or {}
        if items is None:
            # se conservan los últimos datos buenos (con su as_of ORIGINAL);
            # world_events los marca 'stale' y los descarta si son demasiado viejos
            keep = prev.get('items') or []
            _CACHE[key] = {'ts': now, 'ok': False, 'error': err or 'no_data', 'busy': err == 'busy',
                           'items': keep, 'as_of': prev.get('as_of'), 'as_of_ts': prev.get('as_of_ts'),
                           'stale': bool(keep)}
            if str(err or '').startswith('source_down:'):
                _CACHE[key]['retry_at_ts'] = source_retry_at(str(err).split(':')[1])
            log.info('world: capa %s falló: %s', layer, err)
        else:
            _CACHE[key] = {'ts': now, 'ok': True, 'error': None, 'busy': False, 'items': items,
                           'as_of': _iso(now), 'as_of_ts': now, 'stale': False}
        _INFLIGHT.pop(key, None)


def _ttl(layer, e):
    if e and e.get('ok'):
        return LAYER_TTL[layer]
    if e and e.get('retry_at_ts'):
        return max(ERROR_TTL, e['retry_at_ts'] - e['ts'])     # W1: fuente en pausa
    return BUSY_TTL if (e and e.get('busy')) else ERROR_TTL


def _ensure(layer, window):
    """Devuelve (entrada_cacheada|None, hilo_de_refresco|None)."""
    key = _fetch_key(layer, window)
    if layer in _SYNC_LAYERS:
        with _LOCK:
            e = _CACHE.get(key)
        ttl = _ttl(layer, e)
        if e is None or _now() - e['ts'] >= ttl:
            _refresh(layer, key, window)
            with _LOCK:
                e = _CACHE.get(key)
        return e, None
    with _LOCK:
        e = _CACHE.get(key)
        ttl = _ttl(layer, e)
        th = _INFLIGHT.get(key)
        if (e is None or _now() - e['ts'] >= ttl) and th is None:
            th = threading.Thread(target=_refresh, args=(layer, key, window),
                                  name=f'world-{layer}', daemon=True)
            _INFLIGHT[key] = th
            th.start()
    return e, th


def _window_filter(layer, items, window, now):
    """Sismos y eventos naturales se filtran por su hora (exacta / última
    actualización de EONET). GDELT ya viene por ventana; los curados son
    valores actuales."""
    if layer not in ('quakes', 'natural', 'disasters', 'outages'):
        return list(items)
    lim = now - WINDOWS[window]
    return [i for i in items if (i.get('ts') or 0) >= lim]


def max_age_s(layer, window):
    """Edad máxima de los datos cacheados de una capa POR VENTANA (GDELT) antes
    de descartarlos: más viejos ya no describen 'las últimas 24h/7d' (con la
    fuente caída se mostraban hotspots de hace días como de hoy). 24h → 6 h,
    7d → 42 h. Sismos/naturales no la necesitan: su hora es real y se filtran
    por ventana. None = sin tope."""
    if layer not in GDELT_LAYERS:
        return None
    return max(2 * LAYER_TTL[layer], 0.25 * WINDOWS[window])


def _expired(layer, window, e, now):
    ma = max_age_s(layer, window)
    t = (e or {}).get('as_of_ts')
    return ma is not None and t is not None and now - t > ma


def world_events(layers=None, window='24h', wait=DEFAULT_WAIT):
    """CONTRATO: {items:[{id, layer, lat, lon, title, severity, time, source, url, …}],
    sources:{layer:{ok, count, as_of, error?, provider, …}}, window, as_of}.
    'time' es la hora REAL del evento o None cuando la fuente no la da
    (time_kind 'window' = GDELT por ventana, 'current' = valor curado actual;
    ver fetched_at). Ítems de una fuente caída llevan stale=True + as_of."""
    window = window if window in WINDOWS else '24h'
    req = [lyr for lyr in (layers or LIVE_LAYERS) if lyr in LIVE_LAYERS]
    req = list(dict.fromkeys(req))
    deadline = _now() + max(0.0, float(wait or 0))
    entries, threads = {}, {}
    for lyr in req:
        entries[lyr], threads[lyr] = _ensure(lyr, window)
    for lyr in req:
        th = threads.get(lyr)
        # capa fría, o con datos demasiado viejos: se espera al refresco (acotado)
        if th is not None and (entries[lyr] is None or _expired(lyr, window, entries[lyr], _now())):
            th.join(max(0.0, deadline - _now()))
            with _LOCK:
                entries[lyr] = _CACHE.get(_fetch_key(lyr, window))
    now = _now()
    items, sources = [], {}
    for lyr in req:
        meta = LAYER_META[lyr]
        if lyr in GDELT_LAYERS and _gdelt_events_on():
            meta = dict(meta, provider='GDELT 2.0 Events (15 min)', provider_es='GDELT 2.0 · eventos (15 min)',
                        feed='http://data.gdeltproject.org/gdeltv2/lastupdate.txt')
        e = entries[lyr]
        base = {'provider': meta['provider'], 'provider_es': meta.get('provider_es', meta['provider']),
                'provider_en': meta['provider'], 'es': meta['es'], 'en': meta['en'],
                'live': lyr not in CURATED_LAYERS, 'ttl_s': LAYER_TTL[lyr]}
        if lyr in CURATED_LAYERS:
            # W1: valores CURADOS (juicio humano) + noticias si GDELT responde; no es un feed en vivo
            base.update(static=True, curated_as_of=_curated_as_of(), news_live=_news_live(),
                        live_inputs=[x for x in (['FMI PortWatch'] if lyr == 'chokepoints' and _cached_items('shipping') else []) +
                                     (['Dpto. de Estado', 'GDELT'] if lyr == 'instability' and _cached_items('advisories') else [])])
        if e is None:
            sources[lyr] = {**base, 'ok': False, 'pending': True, 'count': 0, 'as_of': None,
                            **err_info('pending')}
            continue
        its = _window_filter(lyr, e['items'], window, now)
        expired = _expired(lyr, window, e, now)
        dropped = 0
        if expired and its:
            dropped, its = len(its), []
        stale = (not e['ok']) and bool(its)
        if stale:
            its = [dict(i, stale=True, as_of=e.get('as_of')) for i in its]
        items.extend(its)
        src = {**base, 'ok': bool(e['ok']) and not expired, 'count': len(its), 'as_of': e['as_of'],
               'stale': stale}
        if dropped:
            src['expired_dropped'] = dropped
        if lyr in GDELT_LAYERS and _gdelt_events_on():
            try:
                from core import gdelt_events as _GE
                have, want = _GE.coverage(WINDOWS[window])
                src['coverage_hours'], src['window_hours'] = have, want
                src['press_signal'] = True
            except Exception:  # noqa: BLE001
                pass
        err = e.get('error')
        if expired and e['ok']:
            err = 'refreshing'          # datos viejos y el refresco no terminó a tiempo
            src['pending'] = True
        if err:
            src.update(err_info(err))
            if str(err).startswith('source_down:') and e.get('retry_at_ts'):
                src['retry_at'] = _iso(e['retry_at_ts'])
        sources[lyr] = src
    items.sort(key=lambda i: (-(i.get('severity') or 0), i['id']))
    return {'items': items, 'sources': sources, 'window': window, 'as_of': _iso(now)}


# ═══════════════════════════════════════════════════════════════════════════
# 6. Capas de REFERENCIA (estáticas, NO en vivo) — etiquetadas como tal
# ═══════════════════════════════════════════════════════════════════════════
# Rutas marítimas principales: waypoints (lat, lon) en agua; el cliente
# interpola por gran círculo entre ellos. Trazado ESQUEMÁTICO.
SHIPPING_LANES = [
    dict(id='asia_europe_suez', es='Asia–Europa (Malaca · Suez)', en='Asia–Europe (Malacca · Suez)',
         path=[(31.0, 122.6), (27.5, 121.6), (24.5, 119.8), (21.5, 117.0), (15.0, 113.5), (8.0, 108.5),
               (3.5, 105.5), (1.25, 104.1), (2.4, 101.4), (4.0, 99.6), (6.2, 95.5), (5.4, 80.6),
               (12.5, 60.0), (12.8, 48.0), (12.6, 43.4), (15.5, 41.8), (20.5, 38.6), (25.0, 35.6),
               (27.6, 34.0), (29.9, 32.55), (31.3, 32.35), (33.5, 28.0), (36.0, 15.5), (37.6, 10.5),
               (37.8, 5.0), (36.0, -5.4), (36.8, -9.6), (43.2, -10.2), (48.3, -6.0), (50.1, -1.0),
               (51.0, 1.5), (51.95, 3.9)]),
    dict(id='transpacific', es='Transpacífico (Asia–EE.UU. Oeste)', en='Transpacific (Asia–US West)',
         path=[(31.0, 123.2), (30.0, 131.5), (33.5, 141.0), (33.6, -118.4)]),
    dict(id='asia_panama_useast', es='Asia–EE.UU. Este (Canal de Panamá)', en='Asia–US East (Panama Canal)',
         path=[(33.5, 141.0), (8.3, -79.6), (9.1, -79.7), (9.4, -79.9), (12.5, -77.5), (19.9, -73.8),
               (26.0, -73.0), (40.3, -73.7)]),
    dict(id='cape_route', es='Ruta del Cabo (alternativa a Suez)', en='Cape route (Suez alternative)',
         path=[(1.25, 104.1), (2.4, 101.4), (4.0, 99.6), (6.2, 95.5), (-8.0, 80.0), (-25.0, 50.0),
               (-36.0, 20.0), (-30.0, 12.0), (-10.0, 0.0), (10.0, -19.0), (28.0, -19.0), (36.8, -10.0),
               (43.2, -10.2), (48.3, -6.0), (50.1, -1.0), (51.0, 1.5), (51.95, 3.9)]),
    dict(id='gulf_asia_oil', es='Golfo Pérsico–Asia (crudo)', en='Persian Gulf–Asia (crude)',
         path=[(26.7, 50.3), (26.0, 53.0), (26.5, 56.4), (24.5, 58.8), (20.0, 62.0), (8.0, 76.0),
               (5.4, 80.6), (6.2, 95.5), (4.0, 99.6), (2.4, 101.4), (1.25, 104.1), (3.5, 105.5),
               (8.0, 108.5), (15.0, 113.5), (21.5, 117.0), (24.5, 119.8), (27.5, 121.6), (31.0, 122.6)]),
    dict(id='transatlantic', es='Transatlántico (Europa–EE.UU.)', en='Transatlantic (Europe–US)',
         path=[(51.95, 3.9), (51.0, 1.5), (50.1, -1.0), (49.3, -5.5), (41.0, -50.0), (40.3, -73.7)]),
    dict(id='black_sea', es='Mar Negro–Mediterráneo (grano, crudo)', en='Black Sea–Mediterranean (grain, crude)',
         path=[(46.4, 30.9), (44.0, 30.6), (41.3, 29.1), (40.9, 28.0), (40.2, 26.4), (39.0, 25.3),
               (35.8, 24.0), (35.5, 21.0), (36.0, 15.5)]),
]

# Corredores de cables submarinos: trazado SIMPLIFICADO entre puntos de
# aterrizaje reales conocidos (no es el recorrido exacto del cable).
CABLE_CORRIDORS = [
    dict(id='marea', es='MAREA (Virginia Beach–Bilbao)', en='MAREA (Virginia Beach–Bilbao)',
         path=[(36.85, -75.98), (43.38, -2.98)]),
    dict(id='ny_uk', es='Corredor Nueva York–Cornualles (Bude)', en='New York–Cornwall (Bude) corridor',
         path=[(40.1, -74.0), (41.0, -50.0), (50.83, -4.55)]),
    dict(id='faster', es='FASTER (Oregón–Japón)', en='FASTER (Oregon–Japan)',
         path=[(43.12, -124.41), (34.95, 139.95)]),
    dict(id='transpac_guam', es='Corredor transpacífico vía Hawái y Guam', en='Transpacific corridor via Hawaii & Guam',
         path=[(33.9, -118.4), (21.3, -158.1), (13.4, 144.7), (24.85, 121.82)]),
    dict(id='seamewe', es='Corredor SEA-ME-WE (Marsella–Singapur)', en='SEA-ME-WE corridor (Marseille–Singapore)',
         path=[(43.3, 5.37), (38.0, 9.0), (34.0, 24.0), (31.2, 29.9), (29.1, 32.65), (20.0, 38.5),
               (11.6, 43.15), (19.0, 72.8), (6.9, 79.85), (1.3, 103.85)]),
    dict(id='intra_asia', es='Corredor intra-Asia (Japón–Taiwán–Hong Kong–Singapur)',
         en='Intra-Asia corridor (Japan–Taiwan–Hong Kong–Singapore)',
         path=[(34.95, 139.95), (24.85, 121.82), (20.6, 121.0), (22.25, 114.2), (10.0, 110.0), (1.3, 103.85)]),
    dict(id='ellalink', es='EllaLink (Fortaleza–Sines)', en='EllaLink (Fortaleza–Sines)',
         path=[(-3.72, -38.54), (37.95, -8.87)]),
    dict(id='sacs', es='SACS (Fortaleza–Luanda)', en='SACS (Fortaleza–Luanda)',
         path=[(-3.72, -38.54), (-8.84, 13.23)]),
    dict(id='us_brazil', es='Corredor Florida–Fortaleza', en='Florida–Fortaleza corridor',
         path=[(26.35, -80.07), (-3.72, -38.54)]),
]

CABLE_LANDINGS = [
    ('Virginia Beach', 36.85, -75.98), ('Bude', 50.83, -4.55), ('Sopelana (Bilbao)', 43.38, -2.98),
    ('Marsella', 43.30, 5.37), ('Fortaleza', -3.72, -38.54), ('Sines', 37.95, -8.87),
    ('Luanda', -8.84, 13.23), ('Singapur', 1.30, 103.85), ('Bombay', 19.00, 72.80),
    ('Yibuti', 11.60, 43.15), ('Zafarana (Suez)', 29.10, 32.65), ('Chikura', 34.95, 139.95),
    ('Bandon (Oregón)', 43.12, -124.41), ('Los Ángeles', 33.90, -118.40), ('Guam', 13.40, 144.70),
    ('Oahu', 21.30, -158.10), ('Toucheng (Taiwán)', 24.85, 121.82), ('Hong Kong', 22.25, 114.20),
    ('Boca Ratón', 26.35, -80.07),
]


def reference_layers():
    fabs = []
    try:
        from core.geosit import FABS
        g = _graph()
        for f in FABS:
            fabs.append({**f, 'company_known': f.get('company') in g['by_id']})
    except Exception:  # noqa: BLE001
        fabs = []
    return {
        'ref': True, 'live': False,
        'lanes': [{'id': x['id'], 'es': x['es'], 'en': x['en'], 'path': [list(p) for p in x['path']]}
                  for x in SHIPPING_LANES],
        'cables': [{'id': x['id'], 'es': x['es'], 'en': x['en'], 'path': [list(p) for p in x['path']]}
                   for x in CABLE_CORRIDORS],
        'landings': [{'name': n, 'lat': la, 'lon': lo} for n, la, lo in CABLE_LANDINGS],
        'fabs': fabs,
        'note_es': 'Capas de REFERENCIA (no en vivo): rutas marítimas y corredores de cables '
                   'trazados de forma esquemática entre puntos reales conocidos; fabs críticas '
                   'curadas a nivel ciudad. No hay tráfico AIS ni estado de cables en tiempo real.',
        'note_en': 'REFERENCE layers (not live): shipping lanes and cable corridors drawn '
                   'schematically between known real points; critical fabs curated at city '
                   'level. No live AIS traffic or cable status.',
    }


# ═══════════════════════════════════════════════════════════════════════════
# 7. Exposición de la cadena + resumen (brief) determinista
# ═══════════════════════════════════════════════════════════════════════════
LAYER_RADIUS_KM = {'conflict': 300, 'unrest': 250, 'trade': 300, 'natural': 250,
                   'chokepoints': 600, 'instability': 0, 'shipping': 600, 'policy': 0, 'disasters': 400,
                   'advisories': 0, 'outages': 0}
_NAT_RADIUS = {'wildfires': 150, 'severeStorms': 500, 'volcanoes': 200, 'floods': 300}


def item_radius_km(item):
    lyr = item.get('layer')
    if lyr == 'quakes':
        try:
            m = float(item.get('mag') or 4.5)
        except (TypeError, ValueError):
            m = 4.5
        return int(min(800, round(60 * 2 ** (m - 4.5))))
    if lyr == 'natural':
        return _NAT_RADIUS.get(item.get('category'), LAYER_RADIUS_KM['natural'])
    return LAYER_RADIUS_KM.get(lyr, 300)


def _co(rec, d=None):
    out = {'id': rec['id'], 'label': rec['label'], 'ticker': rec['ticker'], 'sector': rec['sector'],
           'sector_es': rec['sector_es'], 'sector_en': rec['sector_en'], 'nrs': rec['nrs'],
           'precision': rec['precision'], 'place': rec['place'], 'country_key': rec['country_key']}
    if d is not None:
        out['distance_km'] = int(round(d))
    return out


COUNTRY_W_MAX = 3.0         # tope del aporte "mismo país" (ubicación aprox.) al índice
COUNTRY_W_SCALE = 15.0      # nº de empresas con el que ese aporte llega a ~63% del tope


def exposure(lat, lon, radius_km=500.0, country=None, limit=25, affected=None):
    """Empresas del grafo expuestas a un punto:
      near     → sede conocida (HQ curado o ciudad) a ≤ radius_km,
      affected → lista explícita (p.ej. las empresas curadas de un estrecho),
      country  → registradas en el país del evento (solo países compactos,
                 o siempre si radius_km == 0: la capa de inestabilidad ES el país),
      fabs     → fabs críticas (curadas) a ≤ radius_km.
    Índice 0-100 (index_kind):
      'proximity' → 100·(1−e^(−W/8)), W = Σ cercanía de empresas + 3·Σ fabs
                    + 1·afectadas + 3·(1−e^(−n_país/15)) (el "mismo país" satura:
                    un conteo de todo el país NO sustituye a la cercanía);
      'share'     → radio 0 + país (inestabilidad): % del grafo registrado allí."""
    g = _graph()
    r = max(0.0, float(radius_km or 0))
    near = []
    if r > 0:
        for rec in g['precise']:
            d = haversine_km(lat, lon, rec['lat'], rec['lng'])
            if d <= r:
                near.append((d, rec))
    near.sort(key=lambda x: (x[0], -x[1]['nrs'], x[1]['id']))
    seen = {rec['id'] for _, rec in near}
    aff = []
    for aid in affected or []:
        rec = g['by_id'].get(aid)
        if rec and rec['id'] not in seen:
            aff.append(rec)
            seen.add(rec['id'])
    ck = country_key(country) if country else None
    same = []
    if ck and (r == 0 or ck not in _BIG_COUNTRIES):
        same = [rec for rec in g['by_country'].get(ck, []) if rec['id'] not in seen]
    fabs = []
    if r > 0:
        try:
            from core.geosit import FABS
            for f in FABS:
                d = haversine_km(lat, lon, f['lat'], f['lon'])
                if d <= r:
                    fabs.append({'site': f['site'], 'company': f.get('company'), 'kind': f.get('kind'),
                                 'lat': f['lat'], 'lon': f['lon'], 'distance_km': int(round(d)),
                                 'company_known': f.get('company') in g['by_id']})
        except Exception:  # noqa: BLE001
            fabs = []
        fabs.sort(key=lambda f: f['distance_km'])
    total = max(1, len(g['nodes']))
    share_pct = round(100.0 * len(same) / total, 1)
    if r == 0 and not aff:
        # todo un país (inestabilidad): índice = qué parte de TU grafo está allí
        index_kind = 'share'
        index = int(round(min(100.0, share_pct)))
    else:
        index_kind = 'proximity'
        w = sum(1 - 0.5 * d / r for d, _ in near) if r > 0 else 0.0
        w += sum(3 * (1 - 0.5 * f['distance_km'] / r) for f in fabs) if r > 0 else 0.0
        w += 1.0 * len(aff)
        w += COUNTRY_W_MAX * (1 - math.exp(-len(same) / COUNTRY_W_SCALE))
        index = int(round(100 * (1 - math.exp(-w / 8.0))))
    limit = max(1, min(50, int(limit or 25)))
    return {
        'lat': lat, 'lon': lon, 'radius_km': int(round(r)), 'country_key': ck,
        'index': index, 'index_kind': index_kind, 'share_pct': share_pct,
        'count': len(near) + len(aff) + len(same),
        'near_count': len(near), 'affected_count': len(aff), 'country_count': len(same),
        'companies': [_co(rec, d) for d, rec in near[:limit]],
        'affected': [_co(rec) for rec in aff[:limit]],
        'same_country': [_co(rec) for rec in same[:limit]],
        'fabs': fabs[:10],
        'method_es': ('Índice = % de tu grafo registrado en ese país.' if index_kind == 'share' else
                      'Cerca = sede o sitio principal conocido (curado o ciudad del catálogo) dentro del '
                      'radio. Mismo país = empresas registradas allí (ubicación exacta no disponible; '
                      'solo en países compactos; su aporte al índice satura). Índice 0-100 pondera '
                      'cercanía, fabs críticas y país.'),
        'method_en': ('Index = % of your graph registered in that country.' if index_kind == 'share' else
                      'Near = known HQ or main site (curated or catalog city) within the radius. Same '
                      'country = companies registered there (exact location unknown; compact countries '
                      'only; their weight saturates). Index 0-100 weighs proximity, critical fabs and '
                      'country.'),
    }


def item_exposure(item, limit=5):
    return exposure(item['lat'], item['lon'], item_radius_km(item), country=item.get('country_key'),
                    limit=limit, affected=item.get('affected') if item.get('layer') in ('chokepoints', 'shipping', 'policy') else None)


def relevance(severity, exposure_index):
    """0-100 = 0.55·severidad + 0.45·exposición de la cadena."""
    return int(round(0.55 * (severity or 0) + 0.45 * (exposure_index or 0)))


EVENT_LAYERS = GDELT_LAYERS + ('quakes', 'natural') + FEED_LAYERS     # eventos EN VIVO (vs. estructurales)


def item_relevance(item, ex):
    """Relevancia de un ítem del brief. La inestabilidad por país es un índice de
    TODO el país (no un evento puntual): cuenta con exposición 0 en el ranking,
    para que los países con muchas empresas (EE.UU., Japón…) no aparezcan
    siempre arriba aunque estén estables. Su exposición se muestra igual."""
    if item.get('layer') in ('instability', 'advisories'):
        return relevance(item.get('severity'), 0)
    return relevance(item.get('severity'), ex.get('index'))


def _rank_key(i):
    return (-i['relevance'], -(i.get('severity') or 0), i['id'])


def compose_brief(ranked, n):
    """Top-n por relevancia RESERVANDO al menos la mitad de los lugares (si los
    hay) a eventos en vivo: los estrechos y países curados cambian poco y, sin
    cupo, tapaban cada día lo nuevo (un evento sev. 60 lejos del grafo no
    entraba nunca)."""
    top = ranked[:n]
    live_all = [i for i in ranked if i['layer'] in EVENT_LAYERS]
    quota = min(len(live_all), (n + 1) // 2)
    have = sum(1 for i in top if i['layer'] in EVENT_LAYERS)
    if have >= quota:
        return top
    # copia (no se mutan los ítems cacheados): live_slot = entró por el cupo
    extra = [dict(i, live_slot=True) for i in ranked[n:] if i['layer'] in EVENT_LAYERS][:quota - have]
    struct = [i for i in top if i['layer'] not in EVENT_LAYERS]
    out = [i for i in top if i['layer'] in EVENT_LAYERS] + struct[:len(struct) - len(extra)] + extra
    out.sort(key=_rank_key)
    return out


_LAYER_LABEL = {
    'conflict': ('Conflicto', 'Conflict'), 'unrest': ('Protestas', 'Unrest'),
    'trade': ('Comercio/sanciones', 'Trade/sanctions'), 'quakes': ('Sismo', 'Earthquake'),
    'natural': ('Evento natural', 'Natural event'), 'chokepoints': ('Estrecho', 'Strait'),
    'instability': ('Inestabilidad', 'Instability'),
    'shipping': ('Tráfico marítimo', 'Shipping traffic'), 'policy': ('Regla/sanción de EE.UU.', 'US rule/sanction'),
    'disasters': ('Alerta GDACS', 'GDACS alert'), 'advisories': ('Riesgo país (EE.UU.)', 'Country risk (US)'),
    'outages': ('Corte de internet', 'Internet outage'),
}


def _why(item, ex):
    es_l, en_l = _LAYER_LABEL.get(item['layer'], (item['layer'], item['layer']))
    names = [c['label'] for c in (ex['companies'] + ex['affected'] + ex['same_country'])[:3]]
    tail_es, tail_en = [], []
    if ex['near_count']:
        tail_es.append(f"{ex['near_count']} empresa(s) del grafo a ≤{ex['radius_km']} km")
        tail_en.append(f"{ex['near_count']} graph compan(ies) within {ex['radius_km']} km")
    if ex['affected_count']:
        tail_es.append(f"{ex['affected_count']} dependiente(s) directa(s)")
        tail_en.append(f"{ex['affected_count']} direct dependent(s)")
    if ex['country_count']:
        if ex.get('index_kind') == 'share':
            tail_es.append(f"{ex['country_count']} registrada(s) en el país ({ex['share_pct']}% de tu grafo)")
            tail_en.append(f"{ex['country_count']} registered in the country ({ex['share_pct']}% of your graph)")
        else:
            tail_es.append(f"{ex['country_count']} registrada(s) en el país")
            tail_en.append(f"{ex['country_count']} registered in the country")
    if ex['fabs']:
        tail_es.append(f"{len(ex['fabs'])} fab(s) crítica(s) cerca")
        tail_en.append(f"{len(ex['fabs'])} critical fab(s) nearby")
    if not tail_es:
        tail_es.append('sin empresas del grafo cerca')
        tail_en.append('no graph companies nearby')
    ns = (' (' + ', '.join(names) + ')') if names else ''
    return (f"{es_l} · severidad {item.get('severity', 0)} · " + '; '.join(tail_es) + ns,
            f"{en_l} · severity {item.get('severity', 0)} · " + '; '.join(tail_en) + ns)


_BRIEF_CACHE = {}
BRIEF_TTL = 60


def brief(window='24h', n=10, wait=DEFAULT_WAIT):
    """Top-N ítems por RELEVANCIA (severidad + exposición de la cadena).
    Determinista: sin IA. Cacheado 60 s por ventana."""
    window = window if window in WINDOWS else '24h'
    n = max(1, min(25, int(n or 10)))
    hit = _BRIEF_CACHE.get(window)
    if hit and _now() - hit['ts'] < BRIEF_TTL and not hit['pending']:
        out = dict(hit['data'])
        out['items'] = compose_brief(hit['ranked'], n)
        return out
    ev = world_events(window=window, wait=wait)
    cands = sorted(ev['items'], key=lambda i: (-(i.get('severity') or 0), i['id']))[:150]
    ranked = []
    for it in cands:
        # VISTA PREVIA (limit 5): el detalle del cliente pide /api/world/exposure completo
        ex = item_exposure(it, limit=5)
        why_es, why_en = _why(it, ex)
        slim = {k: v for k, v in it.items() if k not in ('articles',)}
        slim['articles'] = (it.get('articles') or [])[:2]
        slim.update({'relevance': item_relevance(it, ex),
                     'why_es': why_es, 'why_en': why_en,
                     'exposure': {k: ex[k] for k in ('index', 'index_kind', 'share_pct', 'count', 'near_count',
                                                     'affected_count', 'country_count', 'radius_km',
                                                     'country_key', 'companies', 'affected',
                                                     'same_country', 'fabs')},
                     'exposure_preview': True})
        ranked.append(slim)
    ranked.sort(key=_rank_key)
    counts = {}
    for it in ev['items']:
        counts[it['layer']] = counts.get(it['layer'], 0) + 1
    data = {
        'as_of': ev['as_of'], 'window': window, 'counts': counts,
        'sources': ev['sources'],
        'method_es': 'Relevancia 0-100 = 0,55·severidad del evento + 0,45·exposición de la cadena '
                     '(empresas del grafo cerca, fabs críticas, país). La inestabilidad por país '
                     'cuenta con exposición 0 (es todo un país, no un evento). Al menos la mitad de '
                     'la lista se reserva a eventos en vivo. Determinista, sin IA.',
        'method_en': 'Relevance 0-100 = 0.55·event severity + 0.45·supply-chain exposure '
                     '(graph companies nearby, critical fabs, country). Country instability counts '
                     'with exposure 0 (a whole country, not an event). At least half of the list is '
                     'reserved for live events. Deterministic, no AI.',
    }
    pending = any(s.get('pending') for s in ev['sources'].values())
    _BRIEF_CACHE[window] = {'ts': _now(), 'data': data, 'ranked': ranked, 'pending': pending}
    out = dict(data)
    out['items'] = compose_brief(ranked, n)
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 8. Endpoints
# ═══════════════════════════════════════════════════════════════════════════
def _bad(code, es, en, status=400, **extra):
    """Error de API bilingüe: 'error' (inglés) + error_es/error_en + código."""
    return jsonify({'error': en, 'error_code': code, 'error_es': es, 'error_en': en, **extra}), status


_BAD_WINDOW = ('bad_window', 'window debe ser 24h o 7d', 'window must be 24h or 7d')


def _float_arg(name, lo, hi, default=None):
    raw = request.args.get(name)
    if raw is None or raw == '':
        return default
    v = float(raw)          # ValueError → 400 en el llamador
    if not (lo <= v <= hi) or math.isnan(v):
        raise ValueError(name)
    return v


@world_bp.get('/events')
@rate_limit(400, 3600)
def api_world_events():
    """GET /api/world/events?layers=conflict,quakes&window=24h|7d"""
    window = request.args.get('window', '24h')
    if window not in WINDOWS:
        return _bad(*_BAD_WINDOW)
    raw = request.args.get('layers') or ''
    layers = [x.strip() for x in raw.split(',') if x.strip()] or None
    if layers:
        bad = [x[:40] for x in layers if x not in LIVE_LAYERS]
        if bad:
            return _bad('bad_layers', f'capas desconocidas: {bad[:5]}', f'unknown layers: {bad[:5]}',
                        valid=list(LIVE_LAYERS))
    return jsonify(world_events(layers=layers, window=window))


@world_bp.get('/exposure')
@rate_limit(900, 3600)
def api_world_exposure():
    """GET /api/world/exposure?lat=&lon=&radius_km=500[&country=Taiwan][&limit=25]
    [&affected=TSMC,Nvidia] — affected = dependientes curados de un estrecho
    (así el índice coincide con el del brief, que también los cuenta)."""
    try:
        lat = _float_arg('lat', -90, 90)
        lon = _float_arg('lon', -180, 180)
        radius = _float_arg('radius_km', 0, 3000, 500.0)
        limit = int(_float_arg('limit', 1, 50, 25))
    except (TypeError, ValueError):
        return _bad('bad_params', 'parámetros inválidos: lat∈[-90,90], lon∈[-180,180], radius_km∈[0,3000]',
                    'invalid parameters: lat∈[-90,90], lon∈[-180,180], radius_km∈[0,3000]')
    if lat is None or lon is None:
        return _bad('missing_latlon', 'lat y lon son obligatorios', 'lat and lon are required')
    country = (request.args.get('country') or '')[:60] or None
    raw_aff = (request.args.get('affected') or '')[:1200]
    affected = [a.strip()[:80] for a in raw_aff.split(',') if a.strip()][:20] or None
    return jsonify(exposure(lat, lon, radius, country=country, limit=limit, affected=affected))


@world_bp.get('/brief')
@rate_limit(400, 3600)
def api_world_brief():
    """GET /api/world/brief?window=24h&n=10 — lo más relevante con su exposición."""
    window = request.args.get('window', '24h')
    if window not in WINDOWS:
        return _bad(*_BAD_WINDOW)
    try:
        n = int(request.args.get('n', 10))
    except (TypeError, ValueError):
        return _bad('bad_n', 'n inválido', 'invalid n')
    return jsonify(brief(window=window, n=n))


@world_bp.get('/reference')
@rate_limit(200, 3600)
def api_world_reference():
    """GET /api/world/reference — rutas marítimas, cables y fabs (NO en vivo)."""
    resp = jsonify(reference_layers())
    resp.headers['Cache-Control'] = 'public, max-age=3600'
    return resp


@world_bp.get('/policy')
@rate_limit(240, 3600)
def api_world_policy():
    """GET /api/world/policy — reglas del BIS (controles de exportación, Entity List)
    y de la OFAC (sanciones) de los últimos 30 días, del Federal Register (fuente
    oficial), con empresas del grafo nombradas. Incluye los documentos SIN país
    identificable (no salen en el mapa)."""
    try:
        lim = max(1, min(100, int(request.args.get('limit', 40))))
    except (TypeError, ValueError):
        lim = 40
    out = _feeds().policy_feed(lim)
    src = (world_events(layers=['policy'], wait=0)['sources'] or {}).get('policy') or {}
    out['status'] = {k: src.get(k) for k in ('ok', 'as_of', 'error_code', 'error_es', 'error_en', 'retry_at') if k in src}
    return jsonify(out)


# ═══════════════════════════════════════════════════════════════════════════
# 9. Geopolítica EN VIVO por empresa (para el comité de cartera, 2026-10-05:
#    "en todas las etapas la integración con información en vivo es clave")
# ═══════════════════════════════════════════════════════════════════════════
_GEO_WHY = {'named': ('la nombra un documento oficial', 'named in an official document'),
            'route': ('depende de esa ruta marítima', 'depends on that shipping route'),
            'near': ('cerca de su sede/planta', 'near its HQ/plant'),
            'country': ('en su país', 'in its country')}
_GEO_NEAR_LAYERS = ('conflict', 'unrest', 'quakes', 'natural', 'disasters')


def entity_geo_risks(entity_ids, window='24h', wait=3.0, per_entity=3, min_severity=40):
    """{entity_id: [{layer, title_es, title_en, severity, why, why_es, why_en, distance_km?, time, url, source}]}
    Solo capas EN VIVO u oficiales (no las fichas curadas): reglas/sanciones que NOMBRAN la empresa,
    caídas de tráfico en estrechos de los que depende, eventos cerca de su sede conocida y riesgo
    país oficial. Usa la caché del World Monitor (no fuerza descargas)."""
    try:
        ev = world_events(window=window, wait=wait)
    except Exception:  # noqa: BLE001
        return {}
    g = _graph()
    items = [i for i in ev.get('items') or [] if i.get('layer') not in CURATED_LAYERS]
    out = {}
    for eid in dict.fromkeys(entity_ids or []):
        rec = g['by_id'].get(eid)
        if not rec:
            continue
        hits = []
        for it in items:
            lyr, sev, why, dist = it.get('layer'), it.get('severity') or 0, None, None
            if eid in (it.get('affected') or []) and lyr in ('policy', 'shipping'):
                why = 'named' if lyr == 'policy' else 'route'
                if lyr == 'shipping' and sev < min_severity:
                    why = None
            elif lyr in _GEO_NEAR_LAYERS and rec['precision'] in ('hq', 'city') and sev >= min_severity:
                d = haversine_km(it['lat'], it['lon'], rec['lat'], rec['lng'])
                if d <= max(item_radius_km(it), 50):
                    why, dist = 'near', int(round(d))
            elif lyr in ('advisories', 'outages') and it.get('country_key') and it['country_key'] == rec['country_key'] \
                    and rec['country_key'] not in _GENERIC:
                why = 'country'
            if not why:
                continue
            hits.append({'layer': lyr, 'title_es': it.get('title_es') or it.get('title'), 'title_en': it.get('title_en') or it.get('title'),
                         'severity': sev, 'why': why, 'why_es': _GEO_WHY[why][0], 'why_en': _GEO_WHY[why][1],
                         'distance_km': dist, 'time': it.get('time'), 'url': it.get('url'),
                         'source': it.get('source_es') or it.get('source'), 'official': bool(it.get('official'))})
        if hits:
            hits.sort(key=lambda h: (-(h['why'] == 'named'), -h['severity']))
            out[eid] = hits[:per_entity]
    return out
