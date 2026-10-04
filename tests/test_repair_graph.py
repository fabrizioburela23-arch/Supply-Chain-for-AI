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
