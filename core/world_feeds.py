"""core/world_feeds.py — fuentes OFICIALES nuevas del World Monitor (2026-10-05).

Pedido de Fabrizio: "necesito que [Geopolítica] dé más info de la que da ahora,
pero fiable". GDELT GEO (conflicto/protestas/comercio) fue retirado (HTTP 404)
y la pestaña quedó con poco. Se suman TRES fuentes públicas, gratuitas y sin
clave, cada una con su estado honesto (si cae, su capa lo dice; nunca se
inventa un dato):

  shipping  → FMI PortWatch: tránsitos DIARIOS de buques por estrecho/canal
              (datos satelitales AIS). Se compara el promedio de los últimos 7
              días con el de los 90 días previos: una caída fuerte = disrupción.
  policy    → Federal Register (diario oficial de EE.UU.): reglas y avisos del
              BIS (controles de exportación, Entity List) y de la OFAC
              (sanciones) de los últimos 30 días. Se detecta el país objetivo y
              las empresas del grafo NOMBRADAS en el título/resumen.
  disasters → GDACS (ONU + Comisión Europea): alertas oficiales NARANJA/ROJA de
              sismos, ciclones, inundaciones, volcanes, sequías e incendios.

Cada ítem lleva fuente, fecha real y enlace al documento original. La
"severidad" de policy es una ESTIMACIÓN por palabras clave (se dice así en la
UI); la de shipping sale de la caída medida; la de GDACS, de su nivel oficial.
URLs sobrescribibles por variable de entorno (lección sept-2026: los
proveedores mueven sus APIs; el arreglo no debe requerir tocar código).
"""
import logging
import os
import re
from datetime import datetime, timedelta, timezone

log = logging.getLogger('world')

PORTWATCH_URL = ('https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/'
                 'Daily_Chokepoints_Data/FeatureServer/0/query')
FEDREG_URL = 'https://www.federalregister.gov/api/v1/documents.json'
GDACS_URL = 'https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH'

FEED_META = {
    'shipping': dict(provider='IMF PortWatch', provider_es='FMI PortWatch',
                     es='Tráfico marítimo (estrechos)', en='Shipping traffic (straits)', feed=PORTWATCH_URL),
    'policy': dict(provider='US Federal Register (BIS · OFAC)', provider_es='Diario oficial de EE.UU. (BIS · OFAC)',
                   es='Controles de exportación y sanciones', en='Export controls & sanctions', feed=FEDREG_URL),
    'disasters': dict(provider='GDACS (UN · European Commission)', provider_es='GDACS (ONU · Comisión Europea)',
                      es='Alertas oficiales de desastres', en='Official disaster alerts', feed=GDACS_URL),
}
FEED_TTL = {'shipping': 6 * 3600, 'policy': 3600, 'disasters': 900}
FEED_RADIUS_KM = {'shipping': 600, 'policy': 0, 'disasters': 400}


def _w():
    from core import world
    return world


# ═══════════════════════════════════════════════════════════════════════════
# shipping — FMI PortWatch
# ═══════════════════════════════════════════════════════════════════════════
# Coordenadas de los estrechos/canales de PortWatch (clave = palabra del nombre,
# normalizada). `ref` enlaza con los estrechos curados de core/geosit.py para
# heredar las empresas dependientes del grafo.
STRAITS = [
    ('suez', 30.5, 32.35, 'suez', 'Canal de Suez', 'Suez Canal'),
    ('panama', 9.1, -79.7, 'panama', 'Canal de Panamá', 'Panama Canal'),
    ('bab el mandeb', 12.6, 43.3, 'bab_el_mandeb', 'Bab el-Mandeb', 'Bab el-Mandeb'),
    ('hormuz', 26.6, 56.5, 'hormuz', 'Estrecho de Ormuz', 'Strait of Hormuz'),
    ('malacca', 2.5, 101.0, 'malacca', 'Estrecho de Malaca', 'Strait of Malacca'),
    ('taiwan', 24.6, 119.8, 'taiwan_strait', 'Estrecho de Taiwán', 'Taiwan Strait'),
    ('luzon', 20.6, 121.0, 'luzon_strait', 'Estrecho de Luzón', 'Luzon Strait'),
    ('bosporus', 41.1, 29.05, 'bosphorus', 'Bósforo', 'Bosporus'),
    ('bosphorus', 41.1, 29.05, 'bosphorus', 'Bósforo', 'Bosporus'),
    ('kerch', 45.3, 36.5, 'kerch', 'Estrecho de Kerch', 'Kerch Strait'),
    ('gibraltar', 35.95, -5.6, None, 'Estrecho de Gibraltar', 'Strait of Gibraltar'),
    ('dover', 51.0, 1.45, None, 'Estrecho de Dover', 'Dover Strait'),
    ('oresund', 55.9, 12.7, None, 'Estrecho de Øresund', 'Øresund'),
    ('good hope', -34.6, 18.5, None, 'Cabo de Buena Esperanza', 'Cape of Good Hope'),
    ('korea', 34.5, 129.3, None, 'Estrecho de Corea', 'Korea Strait'),
    ('tsugaru', 41.5, 140.6, None, 'Estrecho de Tsugaru', 'Tsugaru Strait'),
    ('lombok', -8.6, 115.75, None, 'Estrecho de Lombok', 'Lombok Strait'),
    ('sunda', -6.0, 105.8, None, 'Estrecho de la Sonda', 'Sunda Strait'),
    ('makassar', -2.5, 118.0, None, 'Estrecho de Makassar', 'Makassar Strait'),
    ('ombai', -8.4, 125.0, None, 'Estrecho de Ombai', 'Ombai Strait'),
    ('torres', -10.3, 142.2, None, 'Estrecho de Torres', 'Torres Strait'),
    ('balabac', 7.8, 117.0, None, 'Estrecho de Balabac', 'Balabac Strait'),
    ('mindoro', 12.5, 120.6, None, 'Estrecho de Mindoro', 'Mindoro Strait'),
    ('bohai', 38.3, 121.0, None, 'Estrecho de Bohai', 'Bohai Strait'),
    ('magellan', -53.0, -70.5, None, 'Estrecho de Magallanes', 'Strait of Magellan'),
    ('bering', 65.8, -168.8, None, 'Estrecho de Bering', 'Bering Strait'),
    ('mona', 18.3, -67.8, None, 'Paso de la Mona', 'Mona Passage'),
    ('windward', 20.0, -73.8, None, 'Paso de los Vientos', 'Windward Passage'),
    ('yucatan', 21.8, -85.6, None, 'Canal de Yucatán', 'Yucatan Channel'),
    ('florida', 24.4, -80.9, None, 'Estrecho de Florida', 'Florida Strait'),
]


def strait_of(name):
    n = _w()._js_norm(name)
    for key, lat, lon, ref, es, en in STRAITS:
        if key in n:
            return {'key': key, 'lat': lat, 'lon': lon, 'ref': ref, 'es': es, 'en': en}
    return None


def _ci(attrs, *names):
    low = {str(k).lower(): v for k, v in (attrs or {}).items()}
    for n in names:
        if n in low and low[n] not in (None, ''):
            return low[n]
    return None


def _day_of(attrs):
    """Fecha del registro: epoch ms, 'YYYY-MM-DD…' o year/month/day."""
    v = _ci(attrs, 'date')
    if isinstance(v, (int, float)) and v > 1e9:
        return datetime.fromtimestamp(v / 1000 if v > 1e11 else v, timezone.utc).strftime('%Y-%m-%d')
    if isinstance(v, str) and re.match(r'^\d{4}-\d{2}-\d{2}', v):
        return v[:10]
    y, m, d = _ci(attrs, 'year'), _ci(attrs, 'month'), _ci(attrs, 'day')
    try:
        return f'{int(y):04d}-{int(m):02d}-{int(d):02d}'
    except (TypeError, ValueError):
        return None


def _num(v):
    try:
        f = float(v)
        return f if f == f else None
    except (TypeError, ValueError):
        return None


def shipping_severity(change_pct):
    """Caída del tránsito (7 d vs 90 d previos) → 0-100. Subidas = 0.
    −10 % → 16 · −25 % → 40 · −50 % → 80 · ≤ −62 % → 100."""
    if change_pct is None or change_pct >= 0:
        return 0
    return int(min(100, round(-change_pct * 1.6)))


def parse_portwatch(rows, ref_affected=None):
    """rows = [attributes] (varios días × estrechos) → un ítem por estrecho con
    promedio 7 d, base 90 d previa, cambio % y desglose del último día."""
    w = _w()
    by = {}
    for a in rows or []:
        name = _ci(a, 'portname', 'name')
        day = _day_of(a)
        tot = _num(_ci(a, 'n_total'))
        if not name or not day or tot is None:
            continue
        by.setdefault(str(name), {})[day] = a
    items = []
    for name, days in by.items():
        st = strait_of(name)
        if not st:
            continue
        ds = sorted(days)
        last = ds[-1]
        last_d = datetime.strptime(last, '%Y-%m-%d')
        recent = [d for d in ds if (last_d - datetime.strptime(d, '%Y-%m-%d')).days < 7]
        base = [d for d in ds if 7 <= (last_d - datetime.strptime(d, '%Y-%m-%d')).days < 97]
        if len(recent) < 4 or len(base) < 30:
            continue
        avg7 = sum(_num(_ci(days[d], 'n_total')) or 0 for d in recent) / len(recent)
        avgb = sum(_num(_ci(days[d], 'n_total')) or 0 for d in base) / len(base)
        if avgb <= 0:
            continue
        chg = round((avg7 / avgb - 1) * 100, 1)
        la = days[last]
        ts = datetime.strptime(last, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp()
        sev = shipping_severity(chg)
        arrow = '▼' if chg < 0 else '▲'
        if abs(chg) < 1:
            t_es, t_en = f"{st['es']}: tránsito estable (7 d vs 90 d)", f"{st['en']}: steady traffic (7d vs 90d)"
        else:
            t_es = f"{st['es']}: {arrow} {abs(chg):.0f} % tránsitos (7 d vs 90 d)"
            t_en = f"{st['en']}: {arrow} {abs(chg):.0f}% transits (7d vs 90d)"
        items.append({
            'id': 'shipping:' + st['key'].replace(' ', '_'), 'layer': 'shipping', 'ref_id': st['ref'],
            'lat': st['lat'], 'lon': st['lon'], 'place': name,
            'title': t_es, 'title_es': t_es, 'title_en': t_en,
            'severity': sev, 'change_pct': chg, 'transits_7d_avg': round(avg7, 1), 'transits_base_avg': round(avgb, 1),
            'last_day': {'date': last, 'total': _num(_ci(la, 'n_total')), 'tanker': _num(_ci(la, 'n_tanker')),
                         'container': _num(_ci(la, 'n_container')), 'dry_bulk': _num(_ci(la, 'n_dry_bulk'))},
            'affected': list((ref_affected or {}).get(st['ref']) or []),
            'time': w._iso(ts), 'ts': ts, 'time_kind': 'last_update', 'country_key': None,
            'source': 'IMF PortWatch', 'source_es': 'FMI PortWatch', 'source_en': 'IMF PortWatch',
            'url': 'https://portwatch.imf.org/pages/chokepoints', 'official': True,
        })
    items.sort(key=lambda i: (-i['severity'], i['id']))
    return items


def _ref_affected():
    try:
        from core.geosit import CHOKEPOINTS
        return {c['id']: c.get('affected') or [] for c in CHOKEPOINTS}
    except Exception:  # noqa: BLE001
        return {}


def fetch_shipping(_window):
    w = _w()
    down = w.source_down('portwatch')
    if down:
        return None, down
    url = os.environ.get('WORLD_PORTWATCH_URL') or PORTWATCH_URL
    rows, offset = [], 0
    for _page in range(4):           # ~30 estrechos × 100 días ≈ 3.000 filas
        data, err = w._http_get_json(url, params={
            'where': '1=1', 'outFields': '*', 'orderByFields': 'date DESC', 'resultOffset': offset,
            'resultRecordCount': 1000, 'f': 'json'}, timeout=15)
        if err:
            w.source_result('portwatch', err)
            return (None, w.source_down('portwatch') or err) if not rows else (parse_portwatch(rows, _ref_affected()), None)
        if isinstance(data, dict) and data.get('error'):
            w.source_result('portwatch', 'bad_payload:arcgis')
            return None, 'bad_payload:arcgis'
        feats = (data or {}).get('features') or []
        rows.extend(f.get('attributes') or {} for f in feats)
        if len(feats) < 1000 or not (data or {}).get('exceededTransferLimit', len(feats) >= 1000):
            break
        offset += len(feats)
    w.source_result('portwatch', None)
    items = parse_portwatch(rows, _ref_affected())
    if not items and rows:
        return None, 'bad_payload:portwatch_fields'
    return items, None


# ═══════════════════════════════════════════════════════════════════════════
# policy — Federal Register: BIS (controles de exportación) + OFAC (sanciones)
# ═══════════════════════════════════════════════════════════════════════════
AGENCIES = {'industry-and-security-bureau': ('BIS', 'Controles de exportación', 'Export controls'),
            'foreign-assets-control-office': ('OFAC', 'Sanciones', 'Sanctions')}
_KW_CHIPS = re.compile(r'semiconductor|advanced computing|integrated circuit|artificial intelligence|\bAI\b|'
                       r'supercomput|chip|lithograph|high[- ]bandwidth memory|\bHBM\b|data center|model weights', re.I)
_KW_STRONG = re.compile(r'entity list|additions to the entity list|foreign direct product|'
                        r'export administration regulations|designation|blocking|sanctions regulations', re.I)
# países objetivo frecuentes (inglés → clave del catálogo de core/world)
_TARGETS = [('china', 'China'), ('people s republic of china', 'China'), ('prc', 'China'), ('hong kong', 'China'),
            ('russia', 'Rusia'), ('russian federation', 'Rusia'), ('iran', 'Iran'), ('north korea', None),
            ('belarus', None), ('venezuela', None), ('cuba', None), ('syria', None), ('myanmar', None),
            ('taiwan', 'Taiwan'), ('israel', 'Israel'), ('india', 'India'), ('united arab emirates', None),
            ('turkey', None), ('pakistan', None), ('singapore', 'Singapur'), ('malaysia', 'Malasia'),
            ('vietnam', None), ('japan', 'Japon'), ('south korea', 'Corea'), ('netherlands', 'PaisesBajos'),
            ('mexico', 'Mexico'),
            # gentilicios (los títulos de la OFAC dicen "Russian harmful foreign activities", "Iranian…")
            ('chinese', 'China'), ('russian', 'Rusia'), ('iranian', 'Iran'), ('north korean', None),
            ('belarusian', None), ('venezuelan', None), ('cuban', None), ('syrian', None)]
_TARGET_LL = {'venezuela': (7.0, -66.0), 'cuba': (21.5, -79.5), 'syria': (35.0, 38.5), 'myanmar': (21.0, 96.0),
              'north korea': (40.0, 127.0), 'north korean': (40.0, 127.0), 'belarus': (53.7, 27.9),
              'belarusian': (53.7, 27.9), 'venezuelan': (7.0, -66.0), 'cuban': (21.5, -79.5), 'syrian': (35.0, 38.5),
              'united arab emirates': (24.3, 54.4), 'turkey': (39.0, 35.0), 'pakistan': (30.0, 70.0),
              'vietnam': (16.0, 107.5)}


_DISPLAY = {'north korea': 'Corea del Norte', 'north korean': 'Corea del Norte', 'belarus': 'Bielorrusia',
            'belarusian': 'Bielorrusia', 'venezuelan': 'Venezuela', 'cuban': 'Cuba', 'syria': 'Siria',
            'syrian': 'Siria', 'turkey': 'Turquía', 'united arab emirates': 'Emiratos Árabes Unidos'}


def _countries_in(text):
    n = ' ' + _w()._js_norm(text) + ' '
    out = []
    for word, key in _TARGETS:
        i = n.find(' ' + word + ' ')
        if i >= 0:
            out.append((i, word, key))
    out.sort()
    seen, res = set(), []
    for _i, word, key in out:
        k = key or word
        if k not in seen:
            seen.add(k)
            res.append((word, key))
    return res


_NAME_INDEX = {'data': None}
# etiquetas del grafo que chocan con palabras de los propios documentos (el organismo, siglas legales)
_NAME_STOP = {'BIS', 'OFAC', 'EAR', 'AI', 'IA', 'ITAR', 'US', 'USA', 'DOC', 'FR'}


def _company_index():
    """Etiquetas del grafo buscables en texto (≥ 4 letras, o siglas de 3+ en mayúsculas)."""
    if _NAME_INDEX['data'] is not None:
        return _NAME_INDEX['data']
    g = _w()._graph()
    idx = []
    for r in g['nodes']:
        lab = (r.get('label') or '').strip()
        if lab.upper() in _NAME_STOP:
            continue
        if len(lab) >= 4 or (len(lab) >= 3 and lab.isupper()):
            idx.append((re.compile(r'(?<![\w-])' + re.escape(lab) + r'(?![\w-])',
                                   0 if lab.isupper() else re.I), r['id'], lab))
    _NAME_INDEX['data'] = idx
    return idx


def companies_in(text, limit=12):
    out, seen = [], set()
    for rx, nid, lab in _company_index():
        if nid not in seen and rx.search(text or ''):
            seen.add(nid)
            out.append({'id': nid, 'label': lab})
            if len(out) >= limit:
                break
    return out


def policy_severity(doc_type, text, n_companies, age_days):
    """ESTIMACIÓN (palabras clave), no un juicio: base 30; +25 si es Entity List /
    designación / regla de exportación fuerte; +20 si toca chips/IA; +10 si es
    una REGLA (no un aviso); +5 por empresa del grafo nombrada (máx +15);
    −1 por día de antigüedad."""
    s = 30
    if _KW_STRONG.search(text or ''):
        s += 25
    if _KW_CHIPS.search(text or ''):
        s += 20
    if str(doc_type or '').lower() == 'rule':
        s += 10
    s += min(15, 5 * n_companies)
    s -= int(max(0, age_days))
    return int(max(5, min(100, s)))


def parse_fedreg(payload, now=None):
    w = _w()
    now = now or w._now()
    feed = []
    for d in (payload or {}).get('results') or []:
        title = str(d.get('title') or '').strip()
        abstract = str(d.get('abstract') or '').strip()
        text = title + ' ' + abstract
        ags = [a.get('slug') or '' for a in (d.get('agencies') or []) if isinstance(a, dict)]
        ag = next((AGENCIES[s] for s in ags if s in AGENCIES), None)
        if not ag:
            continue
        try:
            pub = datetime.strptime(str(d.get('publication_date'))[:10], '%Y-%m-%d').replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        ts = pub.timestamp()
        comps = companies_in(text)
        ctry = _countries_in(text)
        sev = policy_severity(d.get('type'), text, len(comps), (now - ts) / 86400)
        rec = {
            'id': 'policy:' + str(d.get('document_number') or w._stable_id(title, pub.date())),
            'layer': 'policy', 'agency': ag[0], 'kind_es': ag[1], 'kind_en': ag[2],
            'doc_type': d.get('type'), 'title': title[:300], 'title_es': f"{ag[0]} · {title[:280]}",
            'title_en': f"{ag[0]} · {title[:280]}", 'abstract': abstract[:900],
            'severity': sev, 'severity_kind': 'keyword_estimate', 'companies': comps,
            'affected': [c['id'] for c in comps],
            'countries': list(dict.fromkeys(key or _DISPLAY.get(word, word.title()) for word, key in ctry)),
            'time': w._iso(ts), 'ts': ts, 'time_kind': 'published', 'country_key': None,
            'url': w._safe_url(d.get('html_url')),
            'source': 'US Federal Register', 'source_es': 'Diario oficial de EE.UU. (Federal Register)',
            'source_en': 'US Federal Register', 'official': True,
        }
        # en el mapa: el primer país objetivo con coordenadas (si no hay, queda solo en la lista)
        for word, key in ctry:
            ll = (w._COUNTRY.get(key) if key else None) or _TARGET_LL.get(word)
            if ll:
                # country_key queda en None A PROPÓSITO: una regla contra "China" no expone a las ~70
                # empresas chinas del grafo; la exposición son las empresas que el documento NOMBRA
                rec.update(lat=ll[0], lon=ll[1], target_country=key or _DISPLAY.get(word, word.title()), place=key or _DISPLAY.get(word, word.title()))
                break
        feed.append(rec)
    feed.sort(key=lambda i: (-i['ts'], i['id']))
    return feed


_POLICY_FEED = {'items': [], 'as_of': None}


def fetch_policy(_window):
    w = _w()
    down = w.source_down('fedreg')
    if down:
        return None, down
    since = (datetime.now(timezone.utc) - timedelta(days=30)).strftime('%Y-%m-%d')
    params = [('per_page', 100), ('order', 'newest'), ('conditions[publication_date][gte]', since)]
    params += [('conditions[agencies][]', a) for a in AGENCIES]
    params += [('fields[]', f) for f in ('title', 'abstract', 'html_url', 'publication_date', 'type',
                                          'agencies', 'document_number')]
    data, err = w._http_get_json(os.environ.get('WORLD_FEDREG_URL') or FEDREG_URL, params=params, timeout=15)
    w.source_result('fedreg', err)
    if err:
        return None, w.source_down('fedreg') or err
    if not isinstance(data, dict) or 'results' not in data:
        return None, 'bad_payload:fedreg'
    feed = parse_fedreg(data)
    _POLICY_FEED.update(items=feed, as_of=w._iso(w._now()))
    return [i for i in feed if i.get('lat') is not None], None


def policy_feed(limit=40):
    """Lista COMPLETA (también los documentos sin país identificable) para el panel."""
    if not _POLICY_FEED['as_of']:
        _w().world_events(layers=['policy'], wait=6)
    return {'items': _POLICY_FEED['items'][:limit], 'as_of': _POLICY_FEED['as_of'],
            'source': 'US Federal Register (BIS · OFAC)'}


# ═══════════════════════════════════════════════════════════════════════════
# disasters — GDACS
# ═══════════════════════════════════════════════════════════════════════════
GDACS_TYPES = {'EQ': ('Sismo', 'Earthquake', '◎'), 'TC': ('Ciclón tropical', 'Tropical cyclone', '🌀'),
               'FL': ('Inundación', 'Flood', '🌊'), 'VO': ('Volcán', 'Volcano', '🌋'),
               'DR': ('Sequía', 'Drought', '☀'), 'WF': ('Incendio forestal', 'Wildfire', '🔥'),
               'TS': ('Tsunami', 'Tsunami', '🌊')}
GDACS_SEV = {'red': 85, 'orange': 60}


def _gdacs_ts(s):
    if not s:
        return None
    s = str(s).replace('Z', '')
    for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(s[:26], fmt).replace(tzinfo=timezone.utc).timestamp()
        except ValueError:
            continue
    return None


def parse_gdacs(payload):
    w = _w()
    items = []
    for f in (payload or {}).get('features') or []:
        p = f.get('properties') or {}
        lvl = str(p.get('alertlevel') or '').lower()
        if lvl not in GDACS_SEV:
            continue
        coords = (f.get('geometry') or {}).get('coordinates') or []
        try:
            lon, lat = float(coords[0]), float(coords[1])
        except (TypeError, ValueError, IndexError):
            continue
        if not w._valid_ll(lat, lon):
            continue
        et = str(p.get('eventtype') or '').upper()
        tt = GDACS_TYPES.get(et, (et, et, '⚠'))
        ts = _gdacs_ts(p.get('datemodified') or p.get('todate') or p.get('fromdate'))
        sev_txt = ((p.get('severitydata') or {}).get('severitytext') or '').strip()
        country = str(p.get('country') or '').strip()
        name = str(p.get('name') or p.get('eventname') or '').strip() or f'{tt[1]} · {country}'
        url = (p.get('url') or {}).get('report') if isinstance(p.get('url'), dict) else None
        items.append({
            'id': f"disasters:{et}{p.get('eventid')}", 'layer': 'disasters', 'lat': lat, 'lon': lon,
            'title': f"{tt[2]} {name}", 'title_es': f"{tt[2]} {tt[0]}: {name}", 'title_en': f"{tt[2]} {tt[1]}: {name}",
            'alert': lvl, 'event_type': et, 'severity': GDACS_SEV[lvl] + (5 if p.get('iscurrent') in (True, 'true') else 0),
            'severity_text': sev_txt[:200], 'place': country or None, 'country_key': w.place_country(country) if country else None,
            'time': w._iso(ts) if ts else None, 'ts': ts, 'time_kind': 'last_update',
            'url': w._safe_url(url) if url else 'https://www.gdacs.org/', 'official': True,
            'source': 'GDACS', 'source_es': 'GDACS (ONU · Comisión Europea)', 'source_en': 'GDACS (UN · European Commission)',
        })
    items.sort(key=lambda i: (-i['severity'], i['id']))
    return items


def fetch_disasters(_window):
    w = _w()
    down = w.source_down('gdacs')
    if down:
        return None, down
    today = datetime.now(timezone.utc)
    data, err = w._http_get_json(os.environ.get('WORLD_GDACS_URL') or GDACS_URL, params={
        'alertlevel': 'Orange;Red', 'eventlist': 'EQ;TC;FL;VO;DR;WF',
        'fromdate': (today - timedelta(days=10)).strftime('%Y-%m-%d'), 'todate': today.strftime('%Y-%m-%d')}, timeout=15)
    if err == 'http:404':
        # GDACS responde 404 cuando NO hay eventos que cumplan el filtro: eso es "cero alertas", no una caída
        w.source_result('gdacs', None)
        return [], None
    w.source_result('gdacs', err)
    if err:
        return None, w.source_down('gdacs') or err
    if not isinstance(data, dict) or 'features' not in data:
        return None, 'bad_payload:gdacs'
    return parse_gdacs(data), None


FETCHERS = {'shipping': fetch_shipping, 'policy': fetch_policy, 'disasters': fetch_disasters}
