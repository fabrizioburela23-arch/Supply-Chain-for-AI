"""tests/test_repair_graph.py — Misión de reparación · P1 Grafo y ontología (G4).

Contratos y cálculos sobre el grafo:
  G4a  proveedores/clientes = solo relaciones de FLUJO; partner/invest aparte
       (`related`); `relation_class` + `verified`/`confidence` por arista;
       `include_partners` en get_supply_chain.
  G4b  fechas centinela (2000-01-01 = "desde que se rastrea") marcadas con
       `valid_from_known: false`; procedencia vacía explicada.
  G4c  confianza derivada del texto ("no verificado", "posible"…): merge
       (nodes/merge_graph.js), snapshot, MCP y motor de matrices.
  G4d  NRS estructural: el grado cuenta pares distintos de flujo (cliente y
       servidor), no socios, inversores, 'affects' ni duplicados.
  G4e  cifras del catálogo con unidad y sin fecha propia (honesto).

Sin red. Los tests con base se saltan sin DATABASE_URL:
    DATABASE_URL=postgresql://postgres:devpass@localhost:5432/khipus_g4 \
        python -m pytest tests/test_repair_graph.py -q
"""
import json
import os
import subprocess
import sys
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')


@pytest.fixture
def nodb(monkeypatch):
    """Herramientas MCP sobre el catálogo, sin tocar Postgres aunque exista."""
    from mcp_server import auth
    monkeypatch.setattr(auth, 'db_available', lambda: False)


def _node(script, payload):
    r = subprocess.run(['node', '-e', script], input=json.dumps(payload), capture_output=True, text=True,
                       cwd=ROOT, timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


# ════════════════════════════════════════════════════════════════════════════
# G4a — proveedores/clientes = flujo; partner/invest aparte; clase y confianza
# ════════════════════════════════════════════════════════════════════════════
def test_g4a_edges_filtra_por_tipo_y_mantiene_el_default(nodb):
    from mcp_server import tools
    todos = tools._edges('Equinix', 'up')
    assert any(e['type'] == 'partner' for e in todos)           # el helper sin filtro sigue trayendo todo
    flujo = tools._edges('Equinix', 'up', kinds=tools.flow_types())
    assert flujo and all(e['type'] in tools.flow_types() for e in flujo)
    assert not any(e['type'] in ('partner', 'invest') for e in flujo)
    for e in flujo:
        assert set(e) >= {'source', 'target', 'w', 'rel', 'type', 'relation_class', 'verified', 'confidence'}
    assert tools._edges('Equinix', 'up', kinds=()) == []


def test_g4a_get_company_separa_socios_de_proveedores(nodb):
    """Equinix (producción): Colliers/Fitch/Carlyle/C&W salían como
    top_suppliers por ser `partner`. Ahora van en `related`."""
    from mcp_server import tools
    c = tools.t_get_company(None, id_or_ticker='Equinix', include_live=False)
    tipos_sup = {x['type'] for x in c['top_suppliers']}
    assert tipos_sup and tipos_sup <= set(tools.flow_types())
    assert not {x['id'] for x in c['top_suppliers']} & {'Colliers', 'FitchRatings', 'Carlyle'}
    rel_ids = {x['id'] for x in c['related']}
    assert {'Colliers', 'FitchRatings', 'Carlyle'} <= rel_ids
    assert {x['type'] for x in c['related']} <= {'partner', 'invest'}
    # misma forma que top_suppliers + dirección
    for x in c['related'][:3]:
        assert set(x) >= {'id', 'label', 'weight', 'relation', 'type', 'relation_class', 'verified',
                          'confidence', 'direction'}
    assert set(c['counts']) == {'suppliers', 'customers', 'related'}
    assert c['counts']['related'] == len(tools._edges('Equinix', 'up', kinds=tools.RELATED_TYPES)) + \
        len(tools._edges('Equinix', 'down', kinds=tools.RELATED_TYPES))
    # contrato viejo intacto
    assert c['top_customers'] and all('weight' in x and 'relation' in x for x in c['top_customers'])


def test_g4a_get_supply_chain_related_e_include_partners(nodb):
    from mcp_server import tools
    d = tools.t_get_supply_chain(None, id='Equinix', direction='up')
    assert d['edges'] and all(e['type'] in tools.flow_types() for e in d['edges'])
    assert d['related'] and all(e['type'] in ('partner', 'invest') for e in d['related'])
    assert all(e['target'] == 'Equinix' and e['hop'] == 1 and e['direction'] == 'up' for e in d['related'])
    assert d['counts'] == {'nodes': len(d['nodes']), 'edges': len(d['edges']), 'related': len(d['related'])}
    assert d['include_partners'] is False and d['convention'] == 'edge source SUPPLIES target'
    d2 = tools.t_get_supply_chain(None, id='Equinix', direction='up', include_partners=True)
    assert d2['include_partners'] is True
    assert {e['source'] for e in d['related']} <= {e['source'] for e in d2['edges']}
    assert len(d2['edges']) > len(d['edges'])
    # el esquema acepta el parámetro nuevo (opcional) y rechaza lo desconocido
    sch = tools.REGISTRY['get_supply_chain'].input_schema
    assert tools.validate(sch, {'id': 'x', 'include_partners': True}) == {'id': 'x', 'include_partners': True}
    assert 'include_partners' not in sch.get('required', [])
    with pytest.raises(tools.InvalidParams):
        tools.validate(sch, {'id': 'x', 'partners': True})


def test_g4a_relation_class_es_un_mapa_cerrado():
    from mcp_server.tools import relation_class
    assert relation_class('supply') == 'supply' and relation_class('cloud') == 'supply'
    assert relation_class('license') == 'supply'
    assert relation_class('fab') == 'fab' and relation_class('deploy') == 'customer'
    assert relation_class('invest') == 'invest' and relation_class('owns') == 'invest'
    assert relation_class('ppa') == 'ppa' and relation_class('partner') == 'partner'
    assert relation_class('reports_on') == 'coverage' and relation_class('about') == 'coverage'
    assert relation_class('compite') == 'competitor'
    assert relation_class(None) == 'supply'                     # tipo ausente = supply (merge_graph)
    assert relation_class('justified_by') == 'other'            # nunca se adivina


def test_g4a_aristas_no_verificadas_llevan_confianza_baja(nodb):
    """FedEx→TSMC ('… contrato específico no verificado públicamente', w1):
    verified False y confidence 0.3 en cada contrato del MCP."""
    from mcp_server import tools
    e = [e for e in tools._edges('TSMC', 'up') if e['source'] == 'FedEx'][0]
    assert e['verified'] is False and e['confidence'] == 0.3 and e['relation_class'] == 'supply'
    asml = [e for e in tools._edges('TSMC', 'up') if e['source'] == 'ASML'][0]
    assert asml['verified'] is True and asml['confidence'] == 1.0
    d = tools.t_get_supply_chain(None, id='FedEx', direction='down', limit=60)
    fx = [x for x in d['edges'] if x['target'] == 'TSMC']
    assert fx and fx[0]['verified'] is False and fx[0]['confidence'] == 0.3


# ════════════════════════════════════════════════════════════════════════════
# base compartida (G4b/G4c/G4d): esquema propio, semilla mínima
# ════════════════════════════════════════════════════════════════════════════
@pytest.fixture(scope='module')
def db():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    from ontology.db import _get_engine, init_schema, session_scope
    from ontology.models import Base
    from ontology.service import GENESIS_SENTINEL, apply_event
    import mcp_server.models  # noqa: F401
    import research.models  # noqa: F401
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    assert init_schema(retries=1)
    with session_scope() as s:
        def obj(oid, typ='Company', props=None, when=GENESIS_SENTINEL):
            apply_event(s, 'ObjectCreated', {'label': oid, 'type': typ, 'properties': props or {}},
                        valid_from=when, source='migration_v0', actor='script:migrate_v0_to_ontology', object_id=oid)

        def link(src, tgt, rel='supply', w=2, when=GENESIS_SENTINEL, props=None, source='migration_v0_links'):
            apply_event(s, 'LinkCreated', {'rel_type': rel, 'weight': w, 'properties': props or {}},
                        valid_from=when, source=source, actor='script:migrate_v0_to_ontology',
                        object_id=src, target_id=tgt)
        # G4b: empresa migrada (centinela), un vínculo centinela sin fuente y un hecho con fecha real
        obj('Acme', props={'country': 'EEUU', 'margin': 0.2})
        obj('Prov')
        link('Prov', 'Acme')
        apply_event(s, 'ObjectUpdated', {'properties': {'margin': 0.25}}, valid_from='2024-05-01',
                    source='manual', actor='ana', object_id='Acme')
        # G4d: supply duplicado ×2 (mismo par) + socio + inversor + factor 'affects' → grado de flujo 1
        obj('Dup', props={'country': 'EEUU', 'margin': 0.2})
        obj('S1'); obj('P1'); obj('I1'); obj('F1', typ='Factor')
        link('S1', 'Dup'); link('S1', 'Dup', w=3)
        link('P1', 'Dup', rel='partner'); link('I1', 'Dup', rel='invest')
        link('F1', 'Dup', rel='affects', w=0.5)
        # G4c: vínculo con confianza declarada en properties → peso efectivo = w × conf
        obj('Cx'); obj('Cy')
        link('Cx', 'Cy', w=2, props={'confidence': 0.5})
    yield
    Base.metadata.drop_all(engine)


# ════════════════════════════════════════════════════════════════════════════
# G4b — fechas centinela y procedencia vacía
# ════════════════════════════════════════════════════════════════════════════
def test_g4b_is_genesis_acepta_todas_las_formas():
    from ontology.service import GENESIS_SENTINEL, is_genesis
    assert GENESIS_SENTINEL == '2000-01-01'
    assert is_genesis('2000-01-01') and is_genesis('2000-01-01T00:00:00+00:00')
    assert is_genesis(datetime(2000, 1, 1, tzinfo=timezone.utc)) and is_genesis(datetime(2000, 1, 1))
    assert is_genesis(date(2000, 1, 1))
    assert not is_genesis('2000-01-02') and not is_genesis(datetime(2024, 5, 1, tzinfo=timezone.utc))
    assert not is_genesis(None) and not is_genesis('')
    # el script de migración usa EL MISMO centinela (no una copia)
    import importlib.util
    spec = importlib.util.spec_from_file_location('mig', os.path.join(ROOT, 'scripts', 'migrate_v0_to_ontology.py'))
    mig = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig)
    assert mig.GENESIS == GENESIS_SENTINEL


def test_g4b_api_marca_el_centinela_en_links_y_eventos():
    from ontology.api import _event_to_dict, _link_to_dict
    gen = datetime(2000, 1, 1, tzinfo=timezone.utc)
    real = datetime(2021, 6, 1, tzinfo=timezone.utc)
    lk = SimpleNamespace(id='l1', source_id='Prov', target_id='Acme', rel_type='supply', weight=2, properties={},
                         valid_from=gen, valid_to=None)
    d = _link_to_dict(lk)
    assert d['valid_from'].startswith('2000-01-01') and d['valid_from_known'] is False
    lk.valid_from = real
    assert 'valid_from_known' not in _link_to_dict(lk)          # fecha real: no se marca nada
    ev = SimpleNamespace(id='e1', event_type='LinkCreated', object_id='Prov', target_id='Acme', payload={},
                         valid_from=gen, valid_to=None, recorded_at=real, source='migration_v0_links', actor='x')
    assert _event_to_dict(ev)['valid_from_known'] is False
    ev.valid_from = real
    assert 'valid_from_known' not in _event_to_dict(ev)


@needs_db
def test_g4b_mcp_ontology_object_explica_centinela_y_procedencia_vacia(db):
    from mcp_server import tools
    d = tools.t_get_ontology_object(None, id='Acme')
    inc = d['active_links']['incoming']
    assert inc and inc[0]['source'] == 'Prov' and inc[0]['valid_from_known'] is False
    assert inc[0]['valid_from_note_es'] == 'desde que se rastrea; fecha de inicio real desconocida'
    assert inc[0]['valid_from_note_en'] and inc[0]['relation_class'] == 'supply'
    evs = {e['event_type']: e for e in d['recent_events']}
    assert evs['ObjectCreated']['valid_from_known'] is False and evs['ObjectCreated']['valid_from_note_en']
    assert 'valid_from_known' not in evs['ObjectUpdated']          # 2024-05-01 es real
    assert d['provenance'] == []
    assert d['provenance_note'] == 'catalog-only: curated by Khipus, no primary source document recorded'
    assert d['provenance_note_es'].startswith('solo catálogo')


@needs_db
def test_g4b_timeline_y_time_travel_marcan_el_centinela(db):
    from ontology.db import session_scope
    from ontology.service import as_of_graph
    from ontology.timeline import entity_timeline
    with session_scope() as s:
        tl = entity_timeline(s, 'Acme', include_news=False)
        por_tipo = {e['event_type']: e for e in tl}
        assert por_tipo['LinkCreated']['at'].startswith('2000-01-01')
        assert por_tipo['LinkCreated']['valid_from_known'] is False
        assert 'valid_from_known' not in por_tipo['ObjectUpdated']
        g = as_of_graph(s, '2026-01-01')
        lk = [l for l in g['links'] if l['source'] == 'Prov' and l['target'] == 'Acme'][0]
        assert lk['valid_from_known'] is False
