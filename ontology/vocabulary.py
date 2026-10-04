"""ontology/vocabulary.py — REGISTRO ÚNICO del vocabulario del grafo.

Problema que resuelve (auditoría de escalabilidad 2026-07-19): el vocabulario
estaba copiado en 5 sitios y YA había divergido (engine/graph3d.js tenía un
'customer' inexistente; app.html omitía 'owns' y 'ppa'), y todo lo que caía
fuera de las listas se degradaba EN SILENCIO ('supply', 'Company', 'cloud_ia').
A escala eso corrompe datos sin avisar.

Aquí hay UNA fuente de verdad (vocabulary.json) y dos reglas:

1. **Lista BLANCA, no negra.** `economic_types()` dice qué tipos de objeto son
   nodos del grafo económico. Antes era una lista negra ('Simulation','Factor'),
   así que cada tipo NUEVO (Nota, Tesis, Noticia, Fuente…) se colaba como nodo
   fantasma en las matrices. Con noticias persistidas eso habría explotado.
2. **Nada se clasifica en silencio.** Lo que no está en el registro se registra
   en `unknown_report()` (y se loguea UNA vez) para que aparezca en diagnóstico,
   en vez de convertirse calladamente en el valor por defecto.

Añadir un sector / tipo / relación = editar vocabulary.json. No código.
Si el JSON falta o está roto, se cae a FALLBACK (los valores históricos exactos)
para no romper el arranque — patrón "todo opcional" del proyecto.
"""
import json
import logging
import os
import re
import threading

log = logging.getLogger('ontology.vocabulary')

_LOCK = threading.Lock()
_CACHE = {'data': None, 'mtime': None}
_UNKNOWN = {'object_type': {}, 'relation_type': {}}

# Valores históricos EXACTOS (matrix/engine.py antes del registro). Solo se usan
# si vocabulary.json no se puede leer — así el motor nunca queda sin vocabulario.
_FALLBACK = {
    'object_types': {
        'Company': {'economic': True}, 'Tech': {'economic': True},
        'Country': {'economic': True}, 'Policy': {'economic': True},
        'Material': {'economic': True}, 'Energy': {'economic': True},
        'Product': {'economic': True}, 'Org': {'economic': True},
        'Factor': {'economic': False}, 'Simulation': {'economic': False},
    },
    'relation_types': {
        'supply': {'weight': 1.0, 'symmetric': False, 'structural': True, 'flow': True},
        'fab': {'weight': 1.0, 'symmetric': False, 'structural': True, 'flow': True},
        'cloud': {'weight': 0.9, 'symmetric': False, 'structural': True, 'flow': True},
        'license': {'weight': 0.8, 'symmetric': False, 'structural': True, 'flow': True},
        'ppa': {'weight': 0.7, 'symmetric': False, 'structural': True, 'flow': True},
        'owns': {'weight': 0.6, 'symmetric': False, 'structural': True, 'flow': True},
        'deploy': {'weight': 0.4, 'symmetric': False, 'structural': True, 'flow': True},
        'partner': {'weight': 0.3, 'symmetric': True, 'structural': True},
        'invest': {'weight': 0.25, 'symmetric': False, 'structural': True},
    },
    'source_kinds': {},
}


def _path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vocabulary.json')


def load(force=False):
    """Carga vocabulary.json (cacheado por mtime → recarga sola al editarlo)."""
    p = _path()
    try:
        mtime = os.path.getmtime(p)
    except OSError:
        mtime = None
    with _LOCK:
        if not force and _CACHE['data'] is not None and _CACHE['mtime'] == mtime:
            return _CACHE['data']
        data = None
        if mtime is not None:
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception as e:  # noqa: BLE001
                log.error('vocabulary.json ilegible (%s) — uso FALLBACK histórico', e)
        if not isinstance(data, dict) or not data.get('relation_types'):
            data = dict(_FALLBACK)
        _CACHE['data'] = data
        _CACHE['mtime'] = mtime
        return data


# ── tipos de objeto ────────────────────────────────────────────────────────
def object_types():
    return load().get('object_types') or {}


def economic_types():
    """Lista BLANCA de tipos que SÍ son nodos del grafo económico."""
    return tuple(sorted(k for k, v in object_types().items() if (v or {}).get('economic')))


def non_economic_types():
    return tuple(sorted(k for k, v in object_types().items() if not (v or {}).get('economic')))


def is_economic(otype):
    """¿Este tipo es nodo del grafo? Lo DESCONOCIDO se excluye (seguro para el
    grafo) pero se REPORTA — nunca se cuela ni se degrada en silencio."""
    ot = object_types()
    if otype in ot:
        return bool((ot[otype] or {}).get('economic'))
    note_unknown('object_type', otype)
    return False


# ── tipos de relación ──────────────────────────────────────────────────────
def relation_types_all():
    return load().get('relation_types') or {}


def relation_types():
    """Relaciones ESTRUCTURALES (las que propagan daño y forman las matrices).

    Se respeta el ORDEN del JSON, que debe seguir siendo el histórico: la suma
    de las matrices por tipo en coma flotante NO es asociativa, así que
    reordenar introduciría deriva numérica frente al motor histórico (y el
    endpoint /api/matrix/parity la detectaría como discrepancia)."""
    return [k for k, v in relation_types_all().items() if (v or {}).get('structural')]


def relation_weights():
    rt = relation_types_all()
    return {k: float((v or {}).get('weight') or 0) for k, v in rt.items() if (v or {}).get('structural')}


# ── relaciones de FLUJO (G4, misión de reparación 2026-10-04) ──────────────
# "Proveedor" y "cliente" solo tienen sentido para relaciones que MUEVEN algo
# del source al target (suministro, fabricación, nube, licencia, energía,
# propiedad, despliegue). partner/invest son estructurales para las matrices
# pero NO son cadena de suministro: Equinix listaba a Colliers/Fitch/Carlyle
# como "top_suppliers" por ser `partner`, y el NRS contaba socios y duplicados
# como si fueran proveedores. Este es el ÚNICO registro de ese conjunto: el
# MCP (mcp_server/tools.py), el NRS del servidor (ontology/agents.py) y el
# grado del catálogo (core/world.py) lo leen de aquí; el cliente (app.html
# `_buildNrsDegree`) lleva la misma lista con un comentario que apunta acá.
_FLOW_FALLBACK = ('supply', 'fab', 'cloud', 'license', 'ppa', 'owns', 'deploy')


def flow_relation_types():
    """Relaciones de FLUJO (flow=true en vocabulary.json), en el orden del
    JSON. Si el JSON no marca ninguna (versión vieja), cae a la lista histórica
    para que proveedor/cliente nunca queden vacíos."""
    rt = relation_types_all()
    flow = [k for k, v in rt.items() if (v or {}).get('structural') and (v or {}).get('flow')]
    return flow or list(_FLOW_FALLBACK)


# Confianza de un vínculo según su TEXTO curado (G4c). ÚNICA definición en
# Python: la usan mcp_server/tools._link_trust y matrix/engine.link_confidence.
# Su gemela JS vive en nodes/merge_graph.js (UNVERIFIED_RX) — cambiar las dos.
UNVERIFIED_RX = re.compile(r'no verificad|no revisad|posible(mente)?|sin confirmar', re.I)
UNVERIFIED_CONF = 0.3


def text_says_unverified(text):
    """¿El texto curado de la relación dice que no está verificada?"""
    return bool(UNVERIFIED_RX.search(str(text or '')))


def is_flow_relation(rel):
    return (rel or 'supply') in flow_relation_types()


def flow_degree(links):
    """Grado ESTRUCTURAL por nodo: número de pares distintos source→target
    unidos por una relación de flujo (un par con supply+fab cuenta UNA vez;
    partner/invest/affects/about no cuentan). Acepta dicts {source,target,type}
    o {s,t,type}. Es la misma regla que app.html `_buildNrsDegree` y que
    `ontology.agents._compute_server_nrs` (COUNT DISTINCT en SQL)."""
    flow = set(flow_relation_types())
    deg, seen = {}, set()
    for lk in links or []:
        s = lk.get('source', lk.get('s'))
        t = lk.get('target', lk.get('t'))
        if not s or not t or s == t:
            continue
        if (lk.get('type') or 'supply') not in flow:
            continue
        if (s, t) in seen:
            continue
        seen.add((s, t))
        deg[s] = deg.get(s, 0) + 1
        deg[t] = deg.get(t, 0) + 1
    return deg


def symmetric_relations():
    rt = relation_types_all()
    return {k for k, v in rt.items() if (v or {}).get('symmetric')}


def is_known_relation(rel):
    if rel in relation_types_all():
        return True
    note_unknown('relation_type', rel)
    return False


def source_kinds():
    return load().get('source_kinds') or {}


# ── reporte de desconocidos (en vez de degradar en silencio) ───────────────
def note_unknown(kind, value):
    """Registra un valor fuera del vocabulario. Loguea la PRIMERA vez y lleva
    la cuenta, para que aparezca en /api/vocabulary/unknown y en diagnóstico."""
    if not value:
        return
    bucket = _UNKNOWN.setdefault(kind, {})
    if value not in bucket:
        log.warning('Vocabulario: %s desconocido %r — se excluye y se reporta '
                    '(añádelo a ontology/vocabulary.json si es legítimo)', kind, value)
        bucket[value] = 0
    bucket[value] += 1


def unknown_report():
    return {k: dict(v) for k, v in _UNKNOWN.items() if v}


def reset_unknown():
    for v in _UNKNOWN.values():
        v.clear()


def snapshot():
    """Vocabulario completo para servir al cliente (mata las copias duplicadas)."""
    d = load()
    return {
        'version': d.get('version', 0),
        'object_types': object_types(),
        'economic_types': list(economic_types()),
        'relation_types': relation_types_all(),
        'structural_relations': relation_types(),
        'flow_relations': flow_relation_types(),
        'relation_weights': relation_weights(),
        'symmetric_relations': sorted(symmetric_relations()),
        'source_kinds': source_kinds(),
    }
