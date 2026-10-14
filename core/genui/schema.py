"""core/genui/schema.py — el contrato kblocks/1 (docs/CHAT_UI_GENERATIVA.md §4, decisión D-4).

La fuente de verdad es `governance/schemas/kblocks-1.schema.json` (JSON Schema 2020-12, versionado SIN PIN: no cambia
números). Este módulo solo lo CARGA (una vez por proceso) y expone sus listas cerradas; el validador compilado vive en
core/genui/validate.py. Un cambio que rompa clientes viejos no edita el archivo: nace kblocks-2.schema.json.
Solo biblioteca estándar.
"""
import json
import os
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCHEMA_PATH = os.path.join(ROOT, 'governance', 'schemas', 'kblocks-1.schema.json')
VERSION = 'kblocks/1'

_LOCK = threading.Lock()
_STATE = {'schema': None}


def load():
    """El esquema (dict). Se lee una sola vez; no se modifica (las llamadas reciben la MISMA instancia)."""
    s = _STATE['schema']
    if s is not None:
        return s
    with _LOCK:
        if _STATE['schema'] is None:
            with open(SCHEMA_PATH, encoding='utf-8') as fh:
                _STATE['schema'] = json.load(fh)
        return _STATE['schema']


def defs():
    return load()['$defs']


def block_types():
    """{type: nombre de la definición} en el orden de Block.oneOf (el catálogo cerrado de 17 tipos)."""
    d = defs()
    out = {}
    for ref in d['Block']['oneOf']:
        name = ref['$ref'].rsplit('/', 1)[1]
        out[d[name]['properties']['type']['const']] = name
    return out


def enum(def_name):
    return list(defs()[def_name]['enum'])


def action_kinds():
    return list(defs()['Action']['properties']['kind']['enum'])
