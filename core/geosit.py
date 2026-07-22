"""core/geosit.py — Sala de Situación geopolítica: /api/geo/*.

Referencia de producto: World Monitor (pedido de Fabrizio 2026-07-22: "quiero
que sea así de avanzado, incluso más"). El "más" nuestro: cada punto de
estrangulamiento está CONECTADO al grafo de suministro real — el cliente puede
simular su cierre con el motor de matrices (/api/matrix/impact) y ver qué
empresas caen. World Monitor muestra el riesgo; Bixby lo simula.

Datos:
- CHOKEPOINTS/FABS/COUNTRIES: curados a mano (coordenadas reales a nivel
  ciudad/estrecho). Los ids de empresas afectadas se VALIDAN contra la
  ontología si hay DB (los inexistentes se descartan y se reporta el conteo).
- Actividad de noticias: GDELT (7 días) por chokepoint/país, cacheada 1 h y
  calentada PROGRESIVAMENTE (≤4 consultas por request, en paralelo con hilos)
  para no colgar la UI ni golpear el rate-limit de GDELT.
- Factores activos (hiperaristas) que tocan un chokepoint/país: match por
  palabra clave contra la ontología — el tie-in con el hipergrafo.

HONESTIDAD DE DATOS (regla del proyecto): no inventamos AIS ni tráfico
marítimo. Lo que mostramos es: severidad estructural curada + actividad de
noticias medida + factores activos del grafo. Cada cosa etiquetada como lo que es.
Todo opcional/defensivo: sin DB ni GDELT el endpoint responde igual (base).
"""
import logging
import time

import requests
from flask import Blueprint, jsonify

log = logging.getLogger('geosit')

geo_bp = Blueprint('geosit', __name__, url_prefix='/api/geo')

# ── Puntos de estrangulamiento (curados; lat/lon reales) ─────────────────────
# base: severidad ESTRUCTURAL 0-100 (juicio curado, estable). El score final
# = base + actividad de noticias + factores activos, acotado a 100.
# affected: ids de NUESTRO grafo (se validan contra la ontología al servir).
CHOKEPOINTS = [
    dict(id='taiwan_strait', es='Estrecho de Taiwán', en='Taiwan Strait',
         lat=24.6, lon=119.8, base=62,
         why_es='Concentra la fundición avanzada mundial (TSMC). Un bloqueo detiene la cadena de chips de IA entera.',
         why_en='Concentrates the world\'s advanced foundry capacity (TSMC). A blockade halts the entire AI chip chain.',
         sectors=['fabricacion', 'diseno'],
         affected=['TSMC', 'ASE', 'MediaTek', 'Nvidia', 'AMD', 'Apple', 'Qualcomm'],
         q='"Taiwan Strait"'),
    dict(id='luzon_strait', es='Estrecho de Luzón', en='Luzon Strait',
         lat=20.6, lon=121.0, base=45,
         why_es='Corredor de cables submarinos del Pacífico y ruta alternativa a Taiwán.',
         why_en='Pacific submarine-cable corridor and alternate route around Taiwan.',
         sectors=['infra'],
         affected=['TSMC', 'Alphabet (Google Cloud)', 'Microsoft (Azure)', 'Amazon (AWS)'],
         q='"Luzon Strait" OR "Bashi Channel"'),
    dict(id='kerch', es='Estrecho de Kerch', en='Kerch Strait',
         lat=45.3, lon=36.5, base=58,
         why_es='Zona de guerra activa (Rusia-Ucrania); riesgo para grano, energía y sanciones derivadas.',
         why_en='Active war zone (Russia-Ukraine); grain/energy risk and sanction spillovers.',
         sectors=['energia'],
         affected=[],
         q='"Kerch Strait" OR "Sea of Azov"'),
    dict(id='hormuz', es='Estrecho de Ormuz', en='Strait of Hormuz',
         lat=26.6, lon=56.5, base=55,
         why_es='~20% del petróleo mundial. Un cierre dispara el costo energético de fabs y centros de datos.',
         why_en='~20% of world oil. A closure spikes the energy cost of fabs and data centers.',
         sectors=['energia', 'infra'],
         affected=['Vistra', 'Constellation Energy', 'Talen Energy'],
         q='"Strait of Hormuz"'),
    dict(id='malacca', es='Estrecho de Malaca', en='Strait of Malacca',
         lat=2.5, lon=101.0, base=50,
         why_es='Ruta principal Asia-Europa: chips, equipos y materiales pasan por aquí.',
         why_en='Main Asia-Europe route: chips, equipment and materials transit here.',
         sectors=['fabricacion', 'equipos'],
         affected=['TSMC', 'Samsung', 'SKHynix', 'ASML'],
         q='"Strait of Malacca"'),
    dict(id='bab_el_mandeb', es='Bab el-Mandeb (Mar Rojo)', en='Bab el-Mandeb (Red Sea)',
         lat=12.6, lon=43.3, base=52,
         why_es='Los ataques a buques desvían la ruta Asia-Europa por el Cabo: +10-14 días de tránsito.',
         why_en='Attacks on shipping reroute Asia-Europe trade via the Cape: +10-14 days transit.',
         sectors=['equipos', 'fabricacion'],
         affected=['ASML', 'Zeiss SMT', 'Infineon'],
         q='"Bab el-Mandeb" OR "Red Sea shipping"'),
    dict(id='suez', es='Canal de Suez', en='Suez Canal',
         lat=30.5, lon=32.35, base=48,
         why_es='Arteria Asia-Europa; su bloqueo (Ever Given 2021) costó ~$10.000M/día al comercio.',
         why_en='Asia-Europe artery; its 2021 blockage cost ~$10B/day in trade.',
         sectors=['equipos', 'infra'],
         affected=['ASML', 'Siemens Energy', 'Schneider Electric'],
         q='"Suez Canal"'),
    dict(id='panama', es='Canal de Panamá', en='Panama Canal',
         lat=9.1, lon=-79.7, base=38,
         why_es='Ruta América-Asia; las sequías ya restringieron tránsitos en 2023-24.',
         why_en='America-Asia route; droughts already restricted transits in 2023-24.',
         sectors=['infra'],
         affected=[],
         q='"Panama Canal"'),
    dict(id='bosphorus', es='Bósforo', en='Bosphorus',
         lat=41.1, lon=29.05, base=35,
         why_es='Salida del Mar Negro: grano, crudo ruso sancionado y tensión OTAN-Rusia.',
         why_en='Black Sea outlet: grain, sanctioned Russian crude, NATO-Russia tension.',
         sectors=['energia'],
         affected=[],
         q='Bosphorus shipping'),
]

# ── Fabs y sitios críticos (curados; coordenadas a nivel ciudad) ─────────────
# kind: fab | hbm | nand | euv | packaging. company: id del grafo (opcional).
FABS = [
    dict(site='TSMC Fab 18 (3/5nm)', company='TSMC', lat=23.11, lon=120.27, kind='fab', c='Taiwán'),
    dict(site='TSMC Hsinchu (2nm/R&D)', company='TSMC', lat=24.77, lon=121.01, kind='fab', c='Taiwán'),
    dict(site='TSMC Arizona', company='TSMC', lat=33.69, lon=-112.08, kind='fab', c='EE.UU.'),
    dict(site='TSMC/JASM Kumamoto', company='TSMC', lat=32.79, lon=130.74, kind='fab', c='Japón'),
    dict(site='Samsung Pyeongtaek', company='Samsung', lat=36.99, lon=127.11, kind='hbm', c='Corea'),
    dict(site='Samsung Hwaseong', company='Samsung', lat=37.20, lon=127.06, kind='fab', c='Corea'),
    dict(site='Samsung Taylor (constr.)', company='Samsung', lat=30.57, lon=-97.41, kind='fab', c='EE.UU.'),
    dict(site='SK Hynix Icheon (HBM)', company='SKHynix', lat=37.27, lon=127.44, kind='hbm', c='Corea'),
    dict(site='SK Hynix Cheongju', company='SKHynix', lat=36.64, lon=127.49, kind='nand', c='Corea'),
    dict(site='Micron Boise', company='Micron', lat=43.61, lon=-116.20, kind='fab', c='EE.UU.'),
    dict(site='Micron Hiroshima', company='Micron', lat=34.43, lon=132.74, kind='hbm', c='Japón'),
    dict(site='Intel Chandler (AZ)', company='Intel', lat=33.30, lon=-111.84, kind='fab', c='EE.UU.'),
    dict(site='Intel Leixlip', company='Intel', lat=53.37, lon=-6.49, kind='fab', c='Irlanda'),
    dict(site='Intel Kiryat Gat', company='Intel', lat=31.61, lon=34.77, kind='fab', c='Israel'),
    dict(site='SMIC Shanghái', company='SMIC', lat=31.18, lon=121.60, kind='fab', c='China'),
    dict(site='YMTC Wuhan', company='YMTC', lat=30.49, lon=114.51, kind='nand', c='China'),
    dict(site='GlobalFoundries Dresde', company='GlobalFoundries', lat=51.13, lon=13.72, kind='fab', c='Alemania'),
    dict(site='GlobalFoundries Malta (NY)', company='GlobalFoundries', lat=42.97, lon=-73.85, kind='fab', c='EE.UU.'),
    dict(site='Rapidus Chitose (2nm, constr.)', company='Rapidus', lat=42.79, lon=141.66, kind='fab', c='Japón'),
    dict(site='Kioxia Yokkaichi', company='Kioxia', lat=34.94, lon=136.61, kind='nand', c='Japón'),
    dict(site='TI Sherman (300mm)', company='Texas Instruments', lat=33.66, lon=-96.62, kind='fab', c='EE.UU.'),
    dict(site='Infineon Kulim (SiC)', company='Infineon', lat=5.37, lon=100.56, kind='fab', c='Malasia'),
    dict(site='ASML Veldhoven (EUV)', company='ASML', lat=51.41, lon=5.46, kind='euv', c='P. Bajos'),
    dict(site='Zeiss SMT Oberkochen (óptica EUV)', company='Zeiss SMT', lat=48.78, lon=10.10, kind='euv', c='Alemania'),
    dict(site='ASE Kaohsiung (packaging)', company='ASE', lat=22.61, lon=120.30, kind='packaging', c='Taiwán'),
]

# ── Inestabilidad por país (índice ESTRUCTURAL curado 0-100 + noticias) ──────
COUNTRIES = [
    dict(id='ukraine', es='Ucrania', en='Ukraine', base=78, q='Ukraine war'),
    dict(id='russia', es='Rusia', en='Russia', base=74, q='Russia sanctions'),
    dict(id='iran', es='Irán', en='Iran', base=70, q='Iran conflict'),
    dict(id='taiwan', es='Taiwán', en='Taiwan', base=62, q='Taiwan China military'),
    dict(id='china', es='China', en='China', base=58, q='China export controls'),
    dict(id='israel', es='Israel', en='Israel', base=55, q='Israel conflict'),
    dict(id='mexico', es='México', en='Mexico', base=44, q='Mexico security crisis'),
    dict(id='india', es='India', en='India', base=40, q='India Pakistan tension'),
    dict(id='korea', es='Corea del Sur', en='South Korea', base=38, q='"South Korea" "North Korea" tension'),
    dict(id='japan', es='Japón', en='Japan', base=30, q='Japan security'),
    dict(id='usa', es='EE.UU.', en='United States', base=28, q='"United States" trade war'),
    dict(id='germany', es='Alemania', en='Germany', base=24, q='Germany energy crisis'),
    dict(id='netherlands', es='Países Bajos', en='Netherlands', base=22, q='ASML export restrictions'),
    dict(id='singapore', es='Singapur', en='Singapore', base=18, q='Singapore trade'),
]

# nombre del país en el topojson (world-atlas 110m) → id nuestro, para el
# coloreado choropleth del cliente
TOPO_NAME_MAP = {
    'Ukraine': 'ukraine', 'Russia': 'russia', 'Iran': 'iran', 'Taiwan': 'taiwan',
    'China': 'china', 'Israel': 'israel', 'Mexico': 'mexico', 'India': 'india',
    'South Korea': 'korea', 'Japan': 'japan', 'United States of America': 'usa',
    'Germany': 'germany', 'Netherlands': 'netherlands', 'Singapore': 'singapore',
}

# ── caché de actividad de noticias (GDELT) con calentador en segundo plano ──
# GDELT limita a UNA consulta cada 5 s por IP (429 si no). Por eso NADA de
# consultas en el camino del request: un hilo daemon calienta UNA clave cada
# ~11 s (2 workers de gunicorn ≈ una consulta global cada ~5,5 s) y el endpoint
# sirve siempre lo cacheado al instante.
_NEWS_TTL = 3600
_NEWS_CACHE = {}       # key → {'ts', 'count', 'tone'}
_WARM_EVERY = 11       # segundos entre consultas GDELT por worker


def _gdelt_activity(query):
    """Actividad de noticias 7d para una consulta: (nº artículos, tono medio).
    GDELT DOC 2.0 artlist. Falla → None (se mantiene lo cacheado)."""
    try:
        r = requests.get(
            'https://api.gdeltproject.org/api/v2/doc/doc',
            params={'query': query, 'mode': 'artlist', 'maxrecords': 50,
                    'timespan': '7d', 'format': 'json', 'sort': 'datedesc'},
            timeout=5, headers={'User-Agent': 'BixbyFinance/1.0'})
        if not r.ok:
            return None
        arts = (r.json() or {}).get('articles') or []
        tones = []
        for a in arts:
            try:
                tones.append(float(a.get('tone', 0)))
            except (TypeError, ValueError):
                pass
        tone = round(sum(tones) / len(tones), 2) if tones else 0.0
        return {'count': len(arts), 'tone': tone}
    except Exception:  # noqa: BLE001
        return None


_WARMER = {'started': False}


def _next_stale():
    now = time.time()
    for item in CHOKEPOINTS + COUNTRIES:
        e = _NEWS_CACHE.get(item['id'])
        if e is None or now - e['ts'] > _NEWS_TTL:
            return item['id'], item['q']
    return None


def _warmer_loop():
    """Hilo daemon: UNA consulta GDELT cada _WARM_EVERY s. Con 23 claves, todo
    queda caliente en ~4 min tras el arranque y se refresca solo cada hora.
    En 429/fallo, marca con TTL corto y sigue — nunca martilla."""
    while True:
        try:
            nxt = _next_stale()
            if nxt is None:
                time.sleep(30)
                continue
            key, q = nxt
            res = _gdelt_activity(q)
            now = time.time()
            if res is not None:
                _NEWS_CACHE[key] = {'ts': now, **res}
            else:
                # reintento en ~5 min sin bloquear el ciclo de las demás claves
                _NEWS_CACHE[key] = {'ts': now - _NEWS_TTL + 300, 'count': None, 'tone': None}
            time.sleep(_WARM_EVERY)
        except Exception:  # noqa: BLE001
            time.sleep(15)


def _ensure_warmer():
    if _WARMER['started']:
        return
    _WARMER['started'] = True
    try:
        import threading
        threading.Thread(target=_warmer_loop, name='geosit-warmer', daemon=True).start()
    except Exception:  # noqa: BLE001
        _WARMER['started'] = False


def _news_for(key):
    e = _NEWS_CACHE.get(key)
    if not e or e.get('count') is None:
        return None
    return {'count': e['count'], 'tone': e['tone'],
            'age_min': int((time.time() - e['ts']) / 60)}


# ── factores activos (hiperaristas) que tocan un lugar — tie-in hipergrafo ───
_KEYWORDS = {
    'taiwan_strait': ('taiwan', 'taiwán', 'tsmc'),
    'luzon_strait': ('luzon', 'luzón', 'cable'),
    'kerch': ('kerch', 'ucrania', 'ukraine', 'rusia', 'russia', 'azov'),
    'hormuz': ('hormuz', 'ormuz', 'iran', 'irán'),
    'malacca': ('malaca', 'malacca'),
    'bab_el_mandeb': ('mandeb', 'rojo', 'red sea', 'houthi'),
    'suez': ('suez',),
    'panama': ('panama', 'panamá'),
    'bosphorus': ('bosforo', 'bósforo', 'bosphorus', 'mar negro', 'black sea'),
    'ukraine': ('ucrania', 'ukraine'), 'russia': ('rusia', 'russia'),
    'iran': ('iran', 'irán'), 'taiwan': ('taiwan', 'taiwán'),
    'china': ('china',), 'israel': ('israel',), 'korea': ('corea', 'korea', 'samsung'),
    'japan': ('japon', 'japón', 'japan'), 'usa': ('estados unidos', 'eeuu', 'united states'),
    'germany': ('alemania', 'germany'), 'netherlands': ('asml', 'países bajos', 'netherlands'),
    'mexico': ('mexico', 'méxico'), 'india': ('india',), 'singapore': ('singapur', 'singapore'),
}


def _active_factor_matches():
    """{key: [labels de factores activos que lo tocan]} — vacío sin DB."""
    out = {}
    try:
        from ontology.db import ontology_available, session_scope
        if not ontology_available():
            return out
        from matrix.engine import active_factors
        with session_scope() as s:
            factors = active_factors(s)
        for f in factors:
            low = (f.get('label') or '').lower()
            for key, kws in _KEYWORDS.items():
                if any(k in low for k in kws):
                    out.setdefault(key, []).append(f['label'])
    except Exception:  # noqa: BLE001
        pass
    return out


# ── validación de ids afectados contra la ontología (cacheada) ───────────────
_IDS_CACHE = {'ts': 0.0, 'ids': None}


def _known_ids():
    if _IDS_CACHE['ids'] is not None and time.time() - _IDS_CACHE['ts'] < 600:
        return _IDS_CACHE['ids']
    ids = None
    try:
        from ontology.db import ontology_available, session_scope
        if ontology_available():
            from matrix.engine import node_index
            with session_scope() as s:
                idx, _ = node_index(s)
            ids = set(idx.keys())
    except Exception:  # noqa: BLE001
        ids = None
    _IDS_CACHE.update(ts=time.time(), ids=ids)
    return ids


def _score(base, news, factors):
    """Score final 0-100: base estructural + actividad de noticias + factores.
    Componentes acotados y visibles por separado en la respuesta."""
    s = float(base)
    if news and news.get('count'):
        s += min(18.0, news['count'] * 0.4)          # 50 artículos/7d ≈ +18
        if (news.get('tone') or 0) < -4:
            s += 6.0                                  # tono muy negativo
    if factors:
        s += min(14.0, 7.0 * len(factors))
    return round(min(100.0, s), 1)


@geo_bp.get('/situation')
def geo_situation():
    """La foto completa de la Sala de Situación en UNA llamada (instantánea:
    las noticias las calienta el hilo de fondo, nunca este request)."""
    _ensure_warmer()
    fmatch = _active_factor_matches()
    known = _known_ids()

    chokepoints = []
    for c in CHOKEPOINTS:
        news = _news_for(c['id'])
        factors = fmatch.get(c['id'], [])
        affected = c['affected']
        dropped = 0
        if known is not None:
            valid = [a for a in affected if a in known]
            dropped = len(affected) - len(valid)
            affected = valid
        chokepoints.append({
            'id': c['id'], 'es': c['es'], 'en': c['en'],
            'lat': c['lat'], 'lon': c['lon'],
            'base': c['base'], 'news': news, 'factors': factors,
            'score': _score(c['base'], news, factors),
            'why_es': c['why_es'], 'why_en': c['why_en'],
            'sectors': c['sectors'], 'affected': affected,
            'affected_dropped': dropped,
        })
    chokepoints.sort(key=lambda x: -x['score'])

    instability = []
    for c in COUNTRIES:
        news = _news_for(c['id'])
        factors = fmatch.get(c['id'], [])
        instability.append({
            'id': c['id'], 'es': c['es'], 'en': c['en'],
            'base': c['base'], 'news': news, 'factors': factors,
            'score': _score(c['base'], news, factors),
        })
    instability.sort(key=lambda x: -x['score'])

    fabs = []
    for f in FABS:
        fabs.append({**f, 'company_known': bool(known and f.get('company') in known)})

    warm = sum(1 for k in _NEWS_CACHE.values() if k.get('count') is not None)
    return jsonify({
        'chokepoints': chokepoints,
        'instability': instability,
        'topo_name_map': TOPO_NAME_MAP,
        'fabs': fabs,
        'news_sources': {'warm': warm, 'total': len(CHOKEPOINTS) + len(COUNTRIES),
                         'window': '7d', 'provider': 'GDELT'},
        'method_es': 'score = severidad estructural curada + actividad de noticias (GDELT 7d) '
                     '+ factores activos del grafo. Sin datos AIS: no se inventan.',
    })
