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
    assert relation_class('invest') == 'invest' and relation_class('owns') == 'ownership'
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
        # G4c: vínculo con la forma de PRODUCCIÓN (migrado antes de conf/verified:
        # solo el texto en rel_label) → la misma regex lo descuenta
        obj('Fx'); obj('Tx')
        link('Fx', 'Tx', w=1, props={'rel_label': 'Transporte; contrato específico no verificado públicamente'})
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


# ════════════════════════════════════════════════════════════════════════════
# G4c — confianza derivada del texto: merge, snapshot, MCP y matrices
# ════════════════════════════════════════════════════════════════════════════
MERGE_HARNESS = r'''
const P = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const { buildKhipusGraph, linkTrust } = require(P.root + '/nodes/merge_graph.js');
const NODES = [{ id: 'FedEx' }, { id: 'TSMC' }, { id: 'A' }, { id: 'B' }, { id: 'C' }];
const NODE_BY_ID = {}; NODES.forEach(n => { NODE_BY_ID[n.id] = n; });
const r = buildKhipusGraph({
  NODES, NODE_BY_ID, NODE_ID_ALIAS: { 'Fed_Ex': 'FedEx' },
  RAW_LINKS: [
    ['Fed_Ex', 'TSMC', 1, 'Transporte express; contrato específico no verificado públicamente', 'supply'],
    ['A', 'B', 2, 'Suministro confirmado', 'supply'],
    ['A', 'C', 2, 'Posible socio', 'partner', { conf: 0.9, verified: true, since: '2024-01-01' }],
    ['B', 'C', 1, 'sin confirmar', 'supply'],
    ['B', 'C', 3, 'Contrato firmado y auditado', 'supply'],
  ],
  linkArrays: [[{ s: 'C', t: 'A', w: 2, rel: 'posiblemente', type: 'cloud', conf: 0.6 }]],
});
const by = {}; r.LINKS.forEach(l => { by[l.source + '>' + l.target + ':' + l.type] = l; });
process.stdout.write(JSON.stringify({ by, trust: [linkTrust('no revisado aún'), linkTrust('ok'), linkTrust('x', { verified: false })] }));
'''


def test_g4c_merge_deriva_confianza_del_texto_y_respeta_el_sexto_elemento():
    out = _node(MERGE_HARNESS, {'root': ROOT})
    by = out['by']
    fx = by['FedEx>TSMC:supply']
    assert fx['conf'] == 0.3 and fx['verified'] is False and fx['w'] == 1
    assert by['A>B:supply']['conf'] == 1 and by['A>B:supply']['verified'] is True
    # 6.º elemento explícito manda sobre el texto ("Posible socio" diría 0.3)
    ac = by['A>C:partner']
    assert ac['conf'] == 0.9 and ac['verified'] is True and ac['since'] == '2024-01-01'
    # objeto {s,t,…,conf}: también explícito
    assert by['C>A:cloud']['conf'] == 0.6 and by['C>A:cloud']['verified'] is False
    # dedupe (s,t,type): gana el peso mayor y la descripción más larga; la
    # confianza se deriva del texto FINAL (el verificado), no del descartado
    bc = by['B>C:supply']
    assert bc['w'] == 3 and bc['rel'] == 'Contrato firmado y auditado' and bc['conf'] == 1 and bc['verified'] is True
    assert out['trust'][0] == {'conf': 0.3, 'verified': False, 'explicit': False}
    assert out['trust'][1] == {'conf': 1, 'verified': True, 'explicit': False}
    assert out['trust'][2] == {'conf': 0.3, 'verified': False, 'explicit': True}


def test_g4c_merge_real_exporta_conf_sin_cambiar_el_grafo():
    """El merge REAL (nodes/*.js, el mismo que usa el navegador y el export):
    FedEx→TSMC sale con conf 0.3 / verified false y el grafo no cambia de
    tamaño. No se escribe data/grafo_v0.json (buildSnapshot solo arma el objeto)."""
    script = r'''
const P = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const { buildSnapshot } = require(P.root + '/scripts/export_graph_v0.js');
const s = buildSnapshot({ quiet: true });
const pick = (a, b) => s.links.find(l => l.source === a && l.target === b) || null;
process.stdout.write(JSON.stringify({ counts: s.counts, fx: pick('FedEx', 'TSMC'), asml: pick('ASML', 'TSMC'),
  n_conf: s.links.filter(l => typeof l.conf === 'number' && typeof l.verified === 'boolean').length }));
'''
    snap_actual = json.load(open(os.path.join(ROOT, 'data', 'grafo_v0.json'), encoding='utf-8'))
    out = _node(script, {'root': ROOT})
    assert out['counts']['nodes'] == snap_actual['counts']['nodes']
    assert out['counts']['links'] == snap_actual['counts']['links']
    assert out['n_conf'] == out['counts']['links']                  # todos los links salen con conf/verified
    assert out['counts']['unverified_links'] >= 10       # revisión G4: '% exacto no verificado' ya no cuenta
    assert out['fx']['conf'] == 0.3 and out['fx']['verified'] is False and out['fx']['w'] == 1
    assert out['asml']['conf'] == 1 and out['asml']['verified'] is True
    # el snapshot en disco NO se tocó (lo regenera quien integra)
    assert json.load(open(os.path.join(ROOT, 'data', 'grafo_v0.json'), encoding='utf-8'))['exported_at'] == \
        snap_actual['exported_at']


def test_g4c_link_trust_respeta_los_campos_del_snapshot_y_deriva_sin_ellos():
    """Funciona con el snapshot ACTUAL (sin conf) y con el futuro (con conf)."""
    from mcp_server.tools import _link_trust
    assert _link_trust('contrato específico no verificado públicamente') == (False, 0.3)
    assert _link_trust('Posible socio de infraestructura') == (False, 0.3)
    assert _link_trust('relación posiblemente activa') == (False, 0.3)
    assert _link_trust('no revisado') == (False, 0.3) and _link_trust('sin confirmar') == (False, 0.3)
    assert _link_trust('Máquinas EUV') == (True, 1.0) and _link_trust(None) == (True, 1.0)
    # el snapshot nuevo manda sobre el texto
    assert _link_trust('texto no verificado', {'conf': 1.0, 'verified': True}) == (True, 1.0)
    assert _link_trust('ok', {'conf': 0.3, 'verified': False}) == (False, 0.3)
    assert _link_trust('ok', {'verified': False}) == (False, 0.3)
    assert _link_trust('ok', {'conf': 0.6}) == (False, 0.6)
    assert _link_trust('ok', {'conf': 'basura', 'verified': True}) == (True, 1.0)


def test_g4c_eff_weight_multiplica_por_la_confianza():
    from matrix.engine import _eff_weight, link_confidence
    assert _eff_weight(3, None, 0.3) == pytest.approx(0.9)
    assert _eff_weight(3, None) == 3.0 and _eff_weight(3, None, None) == 3.0        # histórico intacto
    assert _eff_weight(None, None, 1.0) == 2.0 and _eff_weight(2, None, 1.0) == 2.0
    assert _eff_weight(2, 'wikidata', 0.5) == pytest.approx(0.5)                    # bulto × confianza
    assert _eff_weight(2, None, 'x') == 2.0 and _eff_weight(2, None, float('nan')) == 2.0
    assert link_confidence({'confidence': 0.85}) == 0.85 and link_confidence({'confidence': '0.5'}) == 0.5
    assert link_confidence({'verified': False}) == 0.3 and link_confidence({}) is None
    assert link_confidence({'confidence': 'basura'}) is None and link_confidence(None) is None
    assert link_confidence({'confidence': 7}) == 1.0
    # base de producción: solo rel_label (la migró el script antes de G4c)
    assert link_confidence({'rel_label': 'contrato específico no verificado públicamente'}) == 0.3
    assert link_confidence({'rel_label': 'Máquinas EUV'}) is None
    assert link_confidence({'rel_label': 'no verificado', 'verified': True}) is None      # lo declarado manda
    assert link_confidence({'rel_label': 'no verificado', 'confidence': 0.9}) == 0.9


def test_g4c_una_sola_regex_en_python():
    from matrix import engine
    from mcp_server import tools
    from ontology import vocabulary
    assert tools._UNVERIFIED_RX is vocabulary.UNVERIFIED_RX
    assert tools.UNVERIFIED_CONF == engine.UNVERIFIED_CONF == vocabulary.UNVERIFIED_CONF == 0.3
    js = open(os.path.join(ROOT, 'nodes', 'merge_graph.js'), encoding='utf-8').read()
    assert 'var UNVERIFIED_RX = /' + vocabulary.UNVERIFIED_RX.pattern + '/i;' in js          # gemela JS idéntica
    assert ('var UNVERIFIED_QUALIFIER_RX = /' + vocabulary.UNVERIFIED_QUALIFIER_RX.pattern + '/gi;') in js   # revisión G4


@needs_db
def test_g4c_matrices_descuentan_la_confianza_declarada(db):
    from matrix.engine import build_matrices
    from ontology.db import session_scope
    with session_scope() as s:
        mats, idx, _ = build_matrices(s)
        as_of, idx2, _ = build_matrices(s, as_of='2026-01-01')
    assert mats['supply'][idx['Cx'], idx['Cy']] == pytest.approx(1.0)         # 2 × 0.5
    assert as_of['supply'][idx2['Cx'], idx2['Cy']] == pytest.approx(1.0)      # time-travel: igual
    assert mats['supply'][idx['Prov'], idx['Acme']] == pytest.approx(2.0)     # sin confianza: histórico
    assert mats['supply'][idx['Fx'], idx['Tx']] == pytest.approx(0.3)         # producción: rel_label → 1 × 0.3
    assert as_of['supply'][idx2['Fx'], idx2['Tx']] == pytest.approx(0.3)


def test_g4c_statematrix_cliente_pesa_la_confianza_como_el_servidor():
    script = r'''
const P = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const { KhipuStateCore } = require(P.root + '/engine/statematrix.js');
const core = new KhipuStateCore({
  nodes: [{ id: 'A' }, { id: 'B' }, { id: 'C' }, { id: 'D' }],
  links: [{ source: 'A', target: 'C', w: 2, type: 'supply', conf: 0.5 },
          { source: 'B', target: 'C', w: 2, type: 'supply' },
          { source: 'A', target: 'D', w: 2, type: 'supply', verified: false }],
  baselineFn: () => ({ salud: 1 }),
});
process.stdout.write(JSON.stringify({ C: core.incoming[core.idx.C], D: core.incoming[core.idx.D] }));
'''
    out = _node(script, {'root': ROOT})
    ws = {e['i']: e['w'] for e in out['C']}
    # 2026-10-06 (SOLE_LINK_FLOOR = 6): la columna se normaliza por max(suma, 6) → la confianza cuenta
    # también para un proveedor único (antes "único = todo", aunque el vínculo fuera dudoso)
    assert ws[0] == pytest.approx(1 / 6) and ws[1] == pytest.approx(2 / 6)   # 1 vs 2, sobre el piso 6
    assert out['D'][0]['w'] == pytest.approx(0.6 / 6)                       # único y dudoso (2×0.3): poco


# ════════════════════════════════════════════════════════════════════════════
# G4d — NRS estructural: pares distintos de flujo (cliente, servidor, catálogo)
# ════════════════════════════════════════════════════════════════════════════
NRS_HARNESS = r'''
const vm = require('vm');
const P = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const ctx = { console };
ctx.window = ctx;
ctx.lid = x => (x && typeof x === 'object') ? x.id : x;
ctx.LINKS = P.links; ctx.window.LINKS = P.links;
vm.createContext(ctx);
vm.runInContext(P.src, ctx);
const m = ctx.window._buildNrsDegree();
process.stdout.write(JSON.stringify(Object.fromEntries(m)));
'''


def _nrs_degree_block():
    """El bloque de app.html que define el grado del NRS (desde la lista de
    tipos de flujo hasta su exposición en window), tal cual se sirve."""
    html = open(os.path.join(ROOT, 'app.html'), encoding='utf-8').read()
    i = html.index('const NRS_FLOW_TYPES')
    j = html.index('window._buildNrsDegree = _buildNrsDegree;', i)
    return html[i:j + len('window._buildNrsDegree = _buildNrsDegree;')]


def test_g4d_cliente_grado_solo_flujo_y_pares_distintos():
    links = [
        {'source': 'S1', 'target': 'Dup', 'w': 2, 'type': 'supply'},
        {'source': 'S1', 'target': 'Dup', 'w': 3, 'type': 'supply'},      # duplicado: cuenta una vez
        {'source': 'S1', 'target': 'Dup', 'w': 3, 'type': 'fab'},         # mismo par, otro tipo: no suma
        {'source': 'P1', 'target': 'Dup', 'w': 2, 'type': 'partner'},     # socio: no cuenta
        {'source': 'I1', 'target': 'Dup', 'w': 2, 'type': 'invest'},      # inversor: no cuenta
        {'source': {'id': 'Dup'}, 'target': {'id': 'C1'}, 'w': 2},         # objetos d3 + tipo ausente = supply
        {'source': 'Dup', 'target': 'Dup', 'w': 2, 'type': 'supply'},     # bucle: se ignora
        {'source': 'E1', 'target': 'Dup', 'w': 2, 'type': 'ppa'},
        {'source': 'Dup', 'target': 'S1', 'w': 1, 'type': 'cloud'},        # par inverso: es otro par
    ]
    deg = _node(NRS_HARNESS, {'src': _nrs_degree_block(), 'links': links})
    assert deg['Dup'] == 4            # S1→Dup, Dup→C1, E1→Dup, Dup→S1
    assert deg['S1'] == 2 and deg['C1'] == 1 and deg['E1'] == 1
    assert 'P1' not in deg and 'I1' not in deg


@needs_db
def test_g4d_servidor_grado_distinct_de_flujo(db):
    """Empresa con 1 supply vigente duplicado ×2 + partner + invest + affects → grado 1."""
    from ontology.agents import _compute_server_nrs, server_flow_degree
    from ontology.db import session_scope
    from ontology.models import LinkRecord
    from ontology.service import get_object
    from sqlalchemy import func, select
    with session_scope() as s:
        filas = s.scalar(select(func.count(LinkRecord.id)).where(LinkRecord.target_id == 'Dup')) or 0
        assert filas == 5                                      # 2 supply + partner + invest + affects
        assert server_flow_degree(s, 'Dup') == 1
        assert server_flow_degree(s, 'Acme') == 1 and server_flow_degree(s, 'F1') == 0
        dup = _compute_server_nrs(s, get_object(s, 'Dup'))
        # misma fórmula con grado 1 (chain 2.5); con las 5 filas sería chain 12.5 (+10)
        from ontology.agents import GEO_RISK
        market = max(0, min(20, round((1 - min(1, 0.2 / 0.4)) * 20)))
        assert dup == round(GEO_RISK.get('EEUU', 15) + 2.5 + market + 4)


def test_g4d_catalogo_mcp_y_world_usan_el_grado_estructural(nodb):
    from core.world import _GRAPH, _graph, client_nrs
    from mcp_server import tools
    from ontology.vocabulary import flow_degree
    snap = tools._snapshot()
    fd = flow_degree(e for lst in snap['out'].values() for e in lst)
    assert fd['Equinix'] == snap['flow_deg']['Equinix'] < snap['deg']['Equinix']   # socios ya no cuentan
    # Colliers: 1 relación de flujo y 3 de socio/inversión → el término "cadena" baja de 10 a 2,5
    n = snap['nodes']['Colliers']
    assert fd['Colliers'] == 1 and snap['deg']['Colliers'] > 1
    r = tools._nrs('Colliers', n)
    assert r['value'] == client_nrs(n, 1) and 'distinct pairs' in r['method']
    assert r['value'] < client_nrs(n, snap['deg']['Colliers'])                     # el NRS visible baja
    _GRAPH['data'] = None
    try:
        w = _graph()['by_id']['Colliers']
        assert w['flow_degree'] == 1 and w['nrs'] == r['value'] and w['degree'] == snap['deg']['Colliers']
    finally:
        _GRAPH['data'] = None


def test_g4d_explicacion_bilingue_y_documentacion():
    js = open(os.path.join(ROOT, 'engine', 'explain.js'), encoding='utf-8').read()
    assert 'socios e inversionistas no cuentan' in js and 'partners and investors do not count' in js
    md = open(os.path.join(ROOT, 'CLAUDE.md'), encoding='utf-8').read()
    assert 'El grado es ESTRUCTURAL' in md


# ════════════════════════════════════════════════════════════════════════════
# G4e — cifras del catálogo: unidad explícita, sin fecha propia (honesto)
# ════════════════════════════════════════════════════════════════════════════
def test_g4e_margen_del_catalogo_en_la_misma_unidad_que_live_market(nodb):
    """Equinix (producción): catalog.operating_margin 0.17 (fracción) junto a
    live_market.operating_margin 27.02 (porcentaje), con un as_of que era la
    fecha de exportación del snapshot. Ahora: _pct en la misma unidad, el
    campo viejo se conserva y las cifras se declaran sin fecha propia."""
    from mcp_server import tools
    c = tools.t_get_company(None, id_or_ticker='Equinix', include_live=False)['catalog']
    assert c['operating_margin'] == 0.17                       # contrato viejo intacto
    assert c['operating_margin_pct'] == 17.0
    assert c['figures_as_of'] is None
    assert c['figures_note'] == 'undated curated figures (catalog); prefer live_market when available'
    assert c['figures_note_es'].startswith('cifras curadas sin fecha propia')
    assert c['as_of'] and 'NOT the date of the figures' in c['as_of_note']
    # pre-revenue (fracción negativa) se convierte igual; sin margen → None sin nota
    r = tools.t_get_company(None, id_or_ticker='Rigetti', include_live=False)['catalog']
    assert r['operating_margin'] == -2.5 and r['operating_margin_pct'] == -250.0
    sin_id = sorted(i for i, n in tools._snapshot()['nodes'].items() if n.get('margin') is None)[0]
    sin = tools.t_get_company(None, id_or_ticker=sin_id, include_live=False)['catalog']
    assert sin['operating_margin'] is None and sin['operating_margin_pct'] is None
    assert 'operating_margin_note' not in sin


def test_g4e_margen_fuera_de_rango_no_se_adivina(nodb):
    """Envicool trae margin 20.25 (alguien lo tecleó ya en %): la unidad es
    dudosa → _pct None + nota, nunca 2025 %."""
    from mcp_server import tools
    assert tools._margin_pct(0.17) == 17.0 and tools._margin_pct(-2.5) == -250.0
    assert tools._margin_pct(None) is None and tools._margin_pct('x') is None
    assert tools._margin_pct(20.25) is None and tools._margin_pct(float('nan')) is None
    c = tools.t_get_company(None, id_or_ticker='Envicool', include_live=False)['catalog']
    assert c['operating_margin'] == 20.25 and c['operating_margin_pct'] is None
    assert 'unit unknown' in c['operating_margin_note']


def test_g4_revision_no_verificado_solo_si_habla_de_la_relacion():
    """Revisión adversarial de G4: '% exacto no verificado' (accionista documentado
    por 13F), 'posible duplicado' (nota del nodo) e 'imposible' NO marcan la relación."""
    from ontology.vocabulary import text_says_unverified as t
    assert not t('Accionista institucional relevante de TSMC según 13F; % exacto no verificado.')
    assert not t('instala equipos de Eaton; nota: ver Dudas sobre posible duplicado interno')
    assert not t('Proceso imposible de replicar')
    assert t('Posible socio de infraestructura GPU') and t('vínculo referencial (no verificado)')


def test_g4_revision_confirmado_por_persona_no_se_descuenta():
    from matrix.engine import link_confidence
    assert link_confidence({'rel_label': 'Posible proveedor de gases'}) == 0.3
    assert link_confidence({'rel_label': 'Posible proveedor de gases', 'status': 'confirmed'}) is None
    # G6b: la confirmación de una persona manda también sobre una confianza declarada/heredada
    assert link_confidence({'rel_label': 'Posible proveedor', 'confidence': 0.5, 'status': 'confirmed'}) is None
    assert link_confidence({'rel_label': 'Posible proveedor', 'confidence': 0.5}) == 0.5


def test_g4_revision_chat_ve_todos_los_clientes():
    import json
    from core import khipu_chat as K
    from mcp_server import tools as T
    from mcp_server.auth import Principal
    ctx = T.Ctx(principal=Principal(token_id='x', name='t', scopes=frozenset({'read'})))
    r = T.call('get_company', {'id_or_ticker': 'Nvidia', 'include_live': False}, ctx)
    r['live_market'] = {'price': 1.0, 'summary': 'x' * 3000}
    txt = K._fmt_result(r)
    assert not txt.endswith('[truncated]')
    d = json.loads(txt)
    assert len(d['top_customers']) == len(r['top_customers']) and 'counts' in d and d['related']


def test_g4_revision_nrs_del_chat_y_de_carteras_es_el_de_la_app():
    from core import portfolio_ai as P
    from core.world import client_nrs
    from mcp_server.tools import _snapshot
    snap = _snapshot()
    g = P._graph()
    for nid in ('SoftBank', 'Codelco', 'Nvidia', 'TSMC'):
        n = snap['nodes'].get(nid)
        if not n:
            continue
        assert g['flow_deg'].get(nid, 0) == snap['flow_deg'].get(nid, 0)
        assert P.nrs(n, g['flow_deg'].get(nid, 0)) == client_nrs(n, snap['flow_deg'].get(nid, 0))


def test_g1c_revision_nrs_de_un_id_viejo_es_el_del_canonico():
    """Revisión adversarial: NODE_BY_ID['SouthernCompany'] ya lleva a SouthernCo,
    pero computeNRS/selectNode usaban el id viejo para el grado (0 vínculos)."""
    html = open(os.path.join(ROOT, 'app.html'), encoding='utf-8').read()
    i = html.index('let _nrsDegree = null;')
    j = html.index('window.computeNRSBreakdown = computeNRSBreakdown;', i)
    src = html[i:j] + 'window.computeNRS = computeNRS;'
    harness = r'''
const vm = require('vm');
const P = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const ctx = { console };
ctx.window = ctx;
ctx.lid = x => (x && typeof x === 'object') ? x.id : x;
ctx.LINKS = P.links; ctx.window.LINKS = P.links;
const so = { id: 'SouthernCo', country: 'EEUU', margin: 0.2 };
ctx.NODE_BY_ID = { SouthernCo: so, SouthernCompany: so };
vm.createContext(ctx);
vm.runInContext(P.src, ctx);
process.stdout.write(JSON.stringify({ alias: ctx.computeNRS('SouthernCompany'), canon: ctx.computeNRS('SouthernCo'),
  canonId: ctx._canonId('SouthernCompany') }));
'''
    links = [{'source': 'SouthernCo', 'target': f'C{k}', 'w': 2, 'type': 'ppa'} for k in range(5)]
    out = _node(harness, {'src': src, 'links': links})
    assert out['canonId'] == 'SouthernCo'
    assert out['alias'] == out['canon'] and out['canon'] > 26
