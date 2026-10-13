"""V6 GeoRisk (INFRA_OPERATIVA §4.2; paso 14): ≤ 3 hechos geopolíticos VIVOS por empresa (reglas/sanciones que la
nombran, rutas con caída de las que depende, eventos cerca de su sede, riesgo país oficial), armados UNA vez por
versión del World Monitor en vez de re-escanear ~300 eventos en cada llamada (@cadena, asesor de cartera,
get_company del MCP, World Monitor).

Clave = (generación del grafo, huella de las fuentes del mundo: capa → as_of). Usa la caché del World Monitor
(nunca fuerza descargas: wait=0). Vista VIVA: lleva su propia versión (`world_version`).
"""
import hashlib
import threading
import time

_LOCK = threading.Lock()
_CUR = {'key': None, 'index': None, 'built_at': None, 'build_ms': None, 'world_version': None, 'items': 0}


def _world_version(ev):
    srcs = ev.get('sources') or {}
    fp = sorted((str(k), str((v or {}).get('as_of')), int((v or {}).get('count') or 0)) for k, v in srcs.items())
    ids = [(i.get('id'), i.get('layer'), i.get('severity'), i.get('time')) for i in ev.get('items') or []]
    return hashlib.sha256(repr((fp, ids)).encode()).hexdigest()[:12]


def index(wait=0):
    """{entity_id: [hechos]} de TODAS las empresas, para la versión vigente del mundo (construido a pedido)."""
    from core import world
    from core.hotviews import hot
    try:
        ev = world.world_events(window='24h', wait=wait)
    except Exception:  # noqa: BLE001
        return {}, None
    wv = _world_version(ev)
    gv = hot.graph()
    key = (gv.generation if gv is not None else None, wv)
    if _CUR['key'] == key and _CUR['index'] is not None:
        return _CUR['index'], wv
    with _LOCK:
        if _CUR['key'] == key and _CUR['index'] is not None:
            return _CUR['index'], wv
        t0 = time.perf_counter()
        ids = list(gv.by_id) if gv is not None else []
        idx = world.entity_geo_risks(ids, wait=0) or {}
        _CUR.update(key=key, index=idx, built_at=time.time(), build_ms=round((time.perf_counter() - t0) * 1000, 1),
                    world_version=wv, items=len(ev.get('items') or []))
        return idx, wv


def facts(ids, wait=0):
    """{id: [≤3 hechos]} solo de las empresas pedidas (las que tienen alguno)."""
    idx, wv = index(wait=wait)
    return {k: idx[k] for k in dict.fromkeys(ids or []) if k in idx}, wv


def status():
    return {k: v for k, v in _CUR.items() if k not in ('index', 'key')} | {
        'entities_with_facts': len(_CUR['index'] or {})}


def reset():
    with _LOCK:
        _CUR.update(key=None, index=None)
