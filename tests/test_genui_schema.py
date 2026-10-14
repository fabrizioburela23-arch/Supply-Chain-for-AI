"""tests/test_genui_schema.py — contrato kblocks/1 del chat con interfaz generativa (docs/CHAT_UI_GENERATIVA.md, F0).

La fuente de verdad es governance/schemas/kblocks-1.schema.json (JSON Schema 2020-12; decisión D-4: archivo
versionado SIN PIN, fuera de governance/artifacts/ porque no cambia números). Los ejemplos viven en
tests/fixtures/genui/examples.kblocks.json. Sale del borrador check_schema.py de la entrega de diseño.

Comprueba:
  (a) [biblioteca estándar, siempre] los dos archivos son JSON sin claves duplicadas; la identidad del contrato
      ($schema 2020-12, $id urn:khipus:kblocks:1, v = kblocks/1); el catálogo cerrado de 17 tipos es el mismo en el
      esquema, en el Plan de la IA (14: sin text/actions/sources, que pone el servidor) y en el §4.4 del documento;
      ninguna acción ni ventana de dinero; las imágenes solo del mismo origen; gobernanza no lo trata como artefacto;
      el §12 del documento registra D-1…D-5 por defecto.
  (b) [jsonschema = ORÁCULO, requirements-dev.txt; en CI es obligatorio, fuera se salta] el esquema es Draft
      2020-12 válido; cada sobre válido pasa; cada inválido FALLA; planes válidos/inválidos contra $defs/Plan;
      negativos extra (fecha sin hora, demasiados bloques, campo desconocido, otra versión, acción de orden).
  `format: "date-time"` se comprueba con un comprobador PROPIO (stdlib, RFC 3339 con hora y zona): jsonschema solo
  lo hace si está rfc3339-validator, y la prueba no puede depender de un paquete opcional.
La conformidad del validador compilado (core/genui/validate.py) con este oráculo llega en F1 (paso 6).
"""
import copy
import datetime
import json
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

SCHEMA_PATH = os.path.join(ROOT, 'governance', 'schemas', 'kblocks-1.schema.json')
EXAMPLES_PATH = os.path.join(ROOT, 'tests', 'fixtures', 'genui', 'examples.kblocks.json')
DOC_PATH = os.path.join(ROOT, 'docs', 'CHAT_UI_GENERATIVA.md')

IN_CI = (os.getenv('CI') or os.getenv('GITHUB_ACTIONS') or '').lower() in ('1', 'true', 'yes')

try:
    import jsonschema  # noqa: F401
    HAVE = True
except ImportError:
    HAVE = False

needs_oracle = pytest.mark.skipif(not HAVE, reason='jsonschema no instalado (requirements-dev.txt)')

N_TYPES = 17
SERVER_ONLY_TYPES = {'text', 'actions', 'sources'}   # la IA no los pide como bloque: los pone el servidor
MONEY_WORDS = ('broker', 'trade', 'order', 'place_order', 'approve', 'buy', 'sell')


def _no_dups(pairs):
    keys = [k for k, _ in pairs]
    dup = sorted({k for k in keys if keys.count(k) > 1})
    if dup:
        raise ValueError('clave duplicada: %s' % dup)
    return dict(pairs)


def _load(path):
    with open(path, encoding='utf-8') as fh:
        return json.loads(fh.read(), object_pairs_hook=_no_dups)


SCHEMA = _load(SCHEMA_PATH)
EX = _load(EXAMPLES_PATH)
DEFS = SCHEMA['$defs']


def _block_types():
    """{type const: def name} desde Block.oneOf."""
    out = {}
    for ref in DEFS['Block']['oneOf']:
        name = ref['$ref'].rsplit('/', 1)[1]
        d = DEFS[name]
        props = d.get('properties') or {}
        t = (props.get('type') or {}).get('const')
        assert t, f'{name} no fija su type con const'
        out[t] = name
    return out


def _plan_block_enum():
    for alt in DEFS['Plan']['items']['oneOf']:
        if 'block' in alt.get('properties', {}):
            return set(alt['properties']['block']['enum'])
    raise AssertionError('el Plan no tiene la alternativa {block, from}')


# ── (a) biblioteca estándar: siempre ────────────────────────────────────────────────────────────────────────────

def test_guardia_ci_exige_jsonschema():
    if IN_CI:
        assert HAVE, 'en CI jsonschema debe estar instalado (pip install -r requirements-dev.txt -c constraints.txt)'


def test_identidad_del_contrato():
    assert SCHEMA['$schema'] == 'https://json-schema.org/draft/2020-12/schema'
    assert SCHEMA['$id'] == 'urn:khipus:kblocks:1'
    assert SCHEMA['$ref'] == '#/$defs/Envelope'
    env = DEFS['Envelope']
    assert env['properties']['v'] == {'const': 'kblocks/1'}
    # el nombre del archivo dice la versión mayor: un cambio incompatible nace como kblocks-2.schema.json
    assert os.path.basename(SCHEMA_PATH) == 'kblocks-%s.schema.json' % SCHEMA['$id'].rsplit(':', 1)[1]
    assert env.get('additionalProperties') is False
    assert env['properties']['blocks']['maxItems'] == 14


def test_catalogo_cerrado_de_17_tipos():
    types = _block_types()
    assert len(types) == N_TYPES, sorted(types)
    plan = _plan_block_enum()
    assert plan == set(types) - SERVER_ONLY_TYPES, sorted(plan ^ (set(types) - SERVER_ONLY_TYPES))
    # cada bloque concreto cierra sus propiedades (la IA no puede colar campos ni HTML)
    for t, name in types.items():
        assert DEFS[name].get('unevaluatedProperties') is False, f'{name} ({t}) sin unevaluatedProperties:false'


def test_el_documento_y_el_esquema_dicen_los_mismos_tipos():
    with open(DOC_PATH, encoding='utf-8') as fh:
        doc = fh.read()
    i = doc.index('### 4.4 Catálogo v1')
    j = doc.index('### 4.5', i)
    rows = re.findall(r'^\|\s*\d+\s*\|\s*`([a-z][a-z.]*)`', doc[i:j], flags=re.M)
    assert len(rows) == N_TYPES and set(rows) == set(_block_types()), rows
    # el repo no lleva copia del esquema dentro del documento (una sola fuente de verdad)
    k = doc.index('## Apéndice A')
    assert '```json' not in doc[k:], 'el apéndice A no debe copiar el esquema: apunta a governance/schemas/'
    assert 'governance/schemas/kblocks-1.schema.json' in doc[k:]


def test_decisiones_por_defecto_registradas():
    with open(DOC_PATH, encoding='utf-8') as fh:
        doc = fh.read()
    i = doc.index('## 12. Decisiones que necesita Fabrizio')
    sec = doc[i:doc.index('## 13.', i)]
    for d in ('D-1', 'D-2', 'D-3', 'D-4', 'D-5'):
        row = next((ln for ln in sec.splitlines() if ln.startswith('| %s ' % d)), '')
        assert 'decidido por defecto 2026-10-13, reversible' in row.lower(), d


def test_sin_acciones_ni_ventanas_de_dinero():
    action_kinds = set()
    for alt in DEFS['Action'].get('oneOf') or [DEFS['Action']]:
        kind = (alt.get('properties') or {}).get('kind') or {}
        action_kinds |= set(kind.get('enum') or ([kind['const']] if 'const' in kind else []))
    assert action_kinds, 'no se encontró Action.kind'
    windows = set(DEFS['WindowKind']['enum'])
    assert windows == {'glance', 'supplychain', 'conviction', 'agents', 'xray', 'compare', 'canvas', 'sim',
                       'geo', 'genui'}, sorted(windows)
    for w in MONEY_WORDS:
        assert not any(w in k for k in action_kinds | windows), w


def test_imagenes_solo_del_mismo_origen():
    pats = []

    def walk(node):
        if isinstance(node, dict):
            if isinstance(node.get('pattern'), str):
                pats.append(node['pattern'])
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(DEFS['ImageBlock'])
    pats = [p for p in pats if 'genui' in p]
    assert pats, 'no hay patrón de ruta de imagen'
    for p in pats:
        assert p.startswith('^/') and p.endswith('$') and 'http' not in p, p
    rx = [re.compile(p) for p in pats]
    assert any(r.match('/static/genui/chip.svg') for r in rx)
    for bad in ('https://evil.example/x.png', '//evil.example/x.png', '/static/genui/../x.svg',
                'data:image/png;base64,AAAA', '/static/genui/x.svg?q=secret'):
        assert not any(r.match(bad) for r in rx), bad


def test_gobernanza_no_lo_trata_como_artefacto():
    # D-4: sin PIN. scripts/build_governance.py y core/governance solo leen governance/artifacts/.
    from core import governance as G
    assert os.path.dirname(SCHEMA_PATH) != G.ART_DIR
    with open(os.path.join(ROOT, 'governance', 'manifest.json'), encoding='utf-8') as fh:
        assert 'kblocks' not in fh.read()


def test_ejemplos_completos():
    assert len(EX['valid']) >= 3 and len(EX['invalid']) >= 14
    assert len(EX['plans_valid']) >= 2 and len(EX['plans_invalid']) >= 7
    names = [c['name'] for c in EX['valid']]
    assert len(names) == len(set(names))
    assert 'MUESTRA' in EX['_note']        # las cifras de los ejemplos no son datos reales


# ── (b) jsonschema = oráculo ───────────────────────────────────────────────────────────────────────────────────

_RFC3339 = re.compile(r'^\d{4}-\d{2}-\d{2}[Tt ]\d{2}:\d{2}:\d{2}(\.\d+)?([Zz]|[+-]\d{2}:\d{2})$')


def _format_checker():
    from jsonschema import FormatChecker
    fc = FormatChecker()

    @fc.checks('date-time', raises=ValueError)
    def _dt(value):                                   # noqa: ANN001 — mismo criterio que tendrá core/genui/validate.py
        if not isinstance(value, str):
            return True
        if not _RFC3339.match(value):
            raise ValueError('no es RFC 3339 con hora y zona')
        datetime.datetime.fromisoformat(value.replace('z', 'Z'))   # fechas imposibles (2026-02-30) → ValueError
        return True
    return fc


@pytest.fixture(scope='module')
def env_validator():
    if not HAVE:
        pytest.skip('jsonschema no instalado')
    from jsonschema import Draft202012Validator
    Draft202012Validator.check_schema(SCHEMA)
    return Draft202012Validator(SCHEMA, format_checker=_format_checker())


@pytest.fixture(scope='module')
def plan_validator():
    if not HAVE:
        pytest.skip('jsonschema no instalado')
    from jsonschema import Draft202012Validator
    plan_schema = dict(SCHEMA)
    plan_schema['$ref'] = '#/$defs/Plan'
    return Draft202012Validator(plan_schema, format_checker=_format_checker())


@needs_oracle
def test_esquema_es_draft_2020_12_valido():
    from jsonschema import Draft202012Validator
    Draft202012Validator.check_schema(SCHEMA)


@needs_oracle
@pytest.mark.parametrize('case', EX['valid'], ids=[c['name'] for c in EX['valid']])
def test_sobre_valido_pasa(env_validator, case):
    errs = ['%s: %s' % (list(e.absolute_path), e.message[:200]) for e in env_validator.iter_errors(case['envelope'])]
    assert not errs, errs[:3]


@needs_oracle
@pytest.mark.parametrize('case', EX['invalid'], ids=[c['why'] for c in EX['invalid']])
def test_sobre_invalido_falla(env_validator, case):
    assert not env_validator.is_valid(case['envelope']), case['why']


@needs_oracle
@pytest.mark.parametrize('plan', EX['plans_valid'], ids=['plan_valido_%d' % i for i in range(len(EX['plans_valid']))])
def test_plan_valido_pasa(plan_validator, plan):
    errs = ['%s: %s' % (list(e.absolute_path), e.message[:200]) for e in plan_validator.iter_errors(plan)]
    assert not errs, errs[:3]


@needs_oracle
@pytest.mark.parametrize('case', EX['plans_invalid'], ids=[c['why'] for c in EX['plans_invalid']])
def test_plan_invalido_falla(plan_validator, case):
    assert not plan_validator.is_valid(case['plan']), case['why']


def _base():
    return copy.deepcopy(EX['valid'][0]['envelope'])


def _neg_bad_datetime():
    e = _base()
    e['as_of'] = '13/10/2026 15:02'
    return e


def _neg_date_only_envelope():
    e = _base()
    e['as_of'] = '2026-10-13'          # el sobre exige fecha Y hora
    return e


def _neg_impossible_date():
    e = _base()
    e['as_of'] = '2026-02-30T10:00:00Z'
    return e


def _neg_too_many_blocks():
    e = _base()
    b = e['blocks'][0]
    e['blocks'] = [dict(copy.deepcopy(b), id='x%d' % i) for i in range(15)]
    return e


def _neg_unknown_top_key():
    e = _base()
    e['html'] = '<img src=x onerror=alert(1)>'
    return e


def _neg_other_version():
    e = _base()
    e['v'] = 'kblocks/2'
    return e


def _neg_block_unknown_key():
    e = _base()
    e['blocks'][0]['onclick'] = 'alert(1)'
    return e


def _neg_order_action():
    e = _base()
    e['blocks'].append({'id': 'act9', 'type': 'actions', 'state': 'ready',
                        'data': {'items': [{'kind': 'place_order', 'label': {'es': 'Comprar', 'en': 'Buy'}}]}})
    return e


NEGATIVES = {
    'as_of con formato no RFC 3339': _neg_bad_datetime,
    'as_of del sobre sin hora': _neg_date_only_envelope,
    'fecha imposible': _neg_impossible_date,
    'más de 14 bloques': _neg_too_many_blocks,
    'campo desconocido en el sobre': _neg_unknown_top_key,
    'otra versión del contrato': _neg_other_version,
    'campo desconocido en un bloque': _neg_block_unknown_key,
    'acción de orden (dinero)': _neg_order_action,
}


@needs_oracle
@pytest.mark.parametrize('why', sorted(NEGATIVES))
def test_negativos_extra(env_validator, why):
    assert env_validator.is_valid(_base()), 'la base del negativo debe ser válida'
    assert not env_validator.is_valid(NEGATIVES[why]()), why


@needs_oracle
def test_fecha_y_hora_con_zona_valida(env_validator):
    for ok in ('2026-10-13T15:02:11Z', '2026-10-13T15:02:11.250Z', '2026-10-13T10:02:11-05:00'):
        e = _base()
        e['as_of'] = ok
        assert env_validator.is_valid(e), ok
