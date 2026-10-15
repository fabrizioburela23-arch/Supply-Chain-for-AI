"""tests/test_import_lote2_e2e.py — lote L (2026-10-15) DE PUNTA A PUNTA sobre Postgres, por la API REAL con PIN y con
los MISMOS comandos de terminal que va a usar Fabrizio (`scripts/import_companies.py --plan … --server` y `--apply …
--server`, con el cliente de pruebas de Flask en lugar de la red):

  catálogo migrado → subir `bundle_lote2_completas.json.gz` en trozos → plan del servidor → aplicar con
  expect.plan_sha + confirm_db → comprobar → deshacer → comprobar → volver a aplicar → un lote chico que resuelve un
  pendiente.

Qué garantiza:
  · lo aplicado = lo planeado (eventos, empresas, fusiones, vínculos vivos/propuestos/pendientes); UNA decisión
    ontology.bulk_import en la transacción; UNA versión nueva del grafo y UNA generación de las vistas;
  · el grafo de los lectores (hot.graph) tiene las 372 empresas nuevas y los vínculos vivos; las propuestas y los
    vínculos terminados NO; las 14 fusiones completan la empresa que ya existía (sin duplicados: Boeing, RTX,
    Samsung, Ørsted);
  · la ficha (/api/hot/card) de CATL, ABB y BWX trae market_position[] / facilities[] con su fuente; el MCP real
    (/mcp con token) responde get_company y rank_by_market con lo importado; resolve_ids por LEI/ISIN resuelve;
  · los números del kernel tras aplicar son EXACTAMENTE los del «¿qué cambia?» del plan (ρ, TSMC, top-20 y la
    matriz entera); las puertas (G-BULK / G-IMPORT) no dan avisos falsos;
  · deshacer devuelve el grafo de lectura y el content_sha de Impact EXACTOS; los pendientes de una corrida deshecha
    no se reintentan; volver a aplicar revive las empresas y da el MISMO grafo;
  · un pendiente de participación («X es dueña de esta empresa») se resuelve con la dirección correcta.

Requiere DATABASE_URL (base desechable: se migra el catálogo entero, ~45 s; la ronda completa ~2-3 min). Sin red, sin
IA. Nunca toca producción.
"""
import contextlib
import gzip
import io
import json
import os
import re
import sys
import time
from collections import Counter

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('KHIPU_SCHEDULER', 'off')

DATABASE_URL = os.getenv('DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')
PIN = '4321'
SERVER = 'http://e2e.test'           # nunca se usa la red: _http/_http_text van al cliente de pruebas de Flask
LOTE = os.path.join(ROOT, 'data', 'import', 'lotes', '2026-10-15')
BUNDLE = os.path.join(LOTE, 'bundle_lote2_completas.json.gz')
FUSIONES = {   # las 14 que la entrega marca «fusionar» (las mismas de tests/test_import_lote2.py)
    'fb-2026-boeing': 'Boeing', 'fb-2026-rtx': 'Raytheon', 'fb-2026-brookfield-asset-management': 'Brookfield',
    'fb-2026-prysmian': 'Prysmian', 'fb-2026-samsung-electronics': 'Samsung', 'fb-2026-foxconn': 'Foxconn',
    'fb-2026-dhl-group': 'DHL_Group', 'fb-2026-ge-aerospace': 'GE_Aerospace', 'fb-2026-ericsson': 'Ericsson',
    'fb-2026-shell': 'Shell', 'fb-2026-kazatomprom': 'Kazatomprom', 'fb-2026-rsted': 'Orsted',
    'fb-2026-montage-technology': 'Montage', 'fb-2026-maersk': 'Maersk',
}
FICHAS_CARD = {'fb-2026-catl': 'CATL', 'fb-2026-abb': 'ABB', 'fb-2026-bwx-technologies': 'BWXTechnologies'}
FLOW = ('supply', 'fab', 'cloud', 'license', 'ppa', 'deploy')
HOLDING_IN = ('major_shareholders', 'parent')      # «la contraparte es dueña / accionista de ESTA empresa»


# ── ayudantes ──────────────────────────────────────────────────────────────────────────────────────────────────
def _rebuild():
    from core.hotviews import builder, hot, registry
    registry.reset()
    hot.invalidate()
    g = builder.build_once()
    assert g.source == 'pg'
    return hot.graph()


def _triples(core):
    out = {}
    for rel, m in core.mats.items():
        coo = m.tocoo()
        for i, j, w in zip(coo.row.tolist(), coo.col.tolist(), coo.data.tolist()):
            out[(core.ids[i], core.ids[j], rel)] = float(w)
    return out


def _photo(v):
    """Lo que se compara entre fotos del grafo: lectores (nodos/vínculos) + kernel (Impact, ρ, TSMC, top-20, matriz)."""
    from matrix import engine as E
    imp, core = v.impact, v.core
    rank = imp.by_sum if E._P('chokepoint_rank_by', 'count') == 'sum' else imp.by_count
    return {'gv': v.graph_version, 'generation': v.generation, 'nodes': {n['id'] for n in v.nodes},
            'links': {(l['source'], l['target'], l['type']) for l in v.links}, 'impact_sha': imp.content_sha,
            'core_sha': core.content_sha, 'rho': (core.rho or {}).get('rho'), 'tsmc': imp.stats['TSMC']['reach_1'],
            'top20': list(rank[:20]), 'core_nodes': len(core.ids), 'triples': _triples(core),
            'by_id': {n['id']: dict(n) for n in v.nodes}}


def _counts(s):
    from sqlalchemy import text
    return {'events': s.execute(text('select count(*) from events')).scalar(),
            'decisions': {r[0]: r[1] for r in s.execute(text('select kind, count(*) from decisions group by kind'))},
            'links_open': s.execute(text('select count(*) from links where valid_to is null')).scalar()}


def _plan_links(plan):
    return [(it, l) for it in plan['items'] if it['action'] in ('create', 'merge') for l in it['links']]


def _expected_kernel(v0_triples, plan):
    """La matriz que DEBE quedar: la de antes + los vínculos VIVOS del plan que siguen vigentes (sin valid_to), con el
    mismo peso efectivo y la misma regla de colisión (máximo; partner simétrico) que build_matrices_from_triples."""
    from matrix import engine as E
    exp = dict(v0_triples)
    for _it, l in _plan_links(plan):
        if l['route'] != 'live' or l.get('valid_to') or not l.get('source') or not l.get('target'):
            continue
        p = l.get('properties') or {}
        w = E._eff_weight(l['weight'], p.get('source'), E.link_confidence(p))
        keys = [(l['source'], l['target'], l['rel_type'])]
        if l['rel_type'] in E.SYMMETRIC:
            keys.append((l['target'], l['source'], l['rel_type']))
        for k in keys:
            if w > exp.get(k, -1.0):
                exp[k] = w
    return {k: w for k, w in exp.items() if w != 0}


class _Cli:
    """scripts/import_companies.py con su HTTP desviado al cliente de Flask (mismo cuerpo, mismas cabeceras)."""

    def __init__(self, client):
        self.client = client
        self.last = {}

    def http(self, server, path, body, pin, timeout=600):
        assert server == SERVER
        r = self.client.post(path, json=body, headers={'X-Trade-Pin': pin, 'X-Khipu-Actor': 'import_cli'})
        data = r.get_json(silent=True)
        if data is None:
            data = {'error': r.get_data(as_text=True)[:300]}
        self.last[path] = (r.status_code, data)
        return r.status_code, data

    def http_text(self, server, path, body, pin, timeout=600):
        r = self.client.post(path, json=body, headers={'X-Trade-Pin': pin, 'X-Khipu-Actor': 'import_cli'})
        return r.status_code, r.get_data(as_text=True)

    def run(self, argv):
        from scripts import import_companies as IC
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = IC.main(argv)
        return code, buf.getvalue()


def _mcp(client, token, name, args):
    msg = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': name, 'arguments': args}}
    r = client.post('/mcp', data=json.dumps(msg), headers={
        'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream', 'Authorization': f'Bearer {token}'})
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    res = r.get_json()['result']
    return bool(res.get('isError')), res.get('structuredContent') or {}


def _holding_kind(rec, relation_id):
    """holding-00n de una ficha → de qué lista de `corporate` salió (el MISMO orden que company_import._holding_links)."""
    corp = rec.get('corporate') or {}
    kinds = ['major_shareholders'] * len(corp.get('major_shareholders') or [])
    if corp.get('parent'):
        kinds.append('parent')
    kinds += ['subsidiaries'] * len(corp.get('subsidiaries') or [])
    n = int(relation_id.split('-')[1])
    return kinds[n - 1] if 0 < n <= len(kinds) else None


def _synth_parent(rid, hint, name, lei):
    F = {'source_url': 'https://www.gleif.org/lei/' + lei, 'source_kind': 'primary', 'as_of': '2026-10', 'confidence': 0.9}
    return {'schema': 'khipus.company/1', 'record_id': rid, 'khipus_id_hint': hint,
            'research_meta': {'researcher': 'e2e', 'researched_at': '2026-10-15T00:00:00Z', 'method': 'manual', 'tier': 'B',
                              'batch': 'e2e-parent'},
            'identity': {'legal_name': {'value': name, **F}, 'short_name': name[:60], 'status': {'value': 'private', **F},
                         'hq_country': {'value': 'US', **F}, 'ids': {'lei': lei}},
            'classification': {'cat': 'foundry'},
            'profile': {'summary': {'value': 'Matriz sintética para resolver un pendiente', 'value_en': 'Synthetic parent that '
                                    'resolves a pending link', **F}}}


# ── la ronda completa (una sola vez por módulo; las pruebas solo miran lo que quedó anotado) ──────────────────────
@pytest.fixture(scope='module')
def e2e():
    mp = pytest.MonkeyPatch()
    mp.setenv('TRADE_PIN', PIN)
    from sqlalchemy import text

    from ontology.db import _get_engine, init_schema, session_scope
    from ontology.models import Base
    import brokerage.models  # noqa: F401
    import mcp_server.models  # noqa: F401
    import research.models  # noqa: F401
    from ontology import company_import as CI
    from ontology import import_models
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    import_models._reset_for_tests()
    assert init_schema(retries=1)
    from scripts.migrate_v0_to_ontology import run_migration
    assert run_migration(reset=False, log=lambda *_a: None)
    assert import_models.ensure_tables(engine)
    out = {'t': {}}
    try:
        import server
        from core import http as h
        from core import pin as _pin
        from core.hotviews import builder
        _pin._reset_for_tests()
        with h._rate_lock:
            h._rate_buckets.clear()
        client = server.app.test_client()
        cli = _Cli(client)
        from scripts import import_companies as IC
        mp.setattr(IC, '_http', cli.http)
        mp.setattr(IC, '_http_text', cli.http_text)
        # las puertas: TODOS los reportes (no solo el resumen del último bloque)
        import core.gates as G
        caught = []
        real_eval = G.evaluate

        def _eval(gate, triples, *a, **k):
            rep = real_eval(gate, triples, *a, **k)
            caught.append((gate, rep))
            return rep
        mp.setattr(G, 'evaluate', _eval)
        with session_scope() as s:
            dbname = s.execute(text('SELECT current_database()')).scalar()
        out['db'] = dbname
        with gzip.open(BUNDLE, 'rt', encoding='utf-8') as fh:
            out['records'] = {r['record_id']: r for r in json.load(fh)['records']}

        # 0) antes
        v0 = _rebuild()
        out['v0'] = _photo(v0)
        with session_scope() as s:
            out['c0'] = _counts(s)
        builds0 = builder.state()['builds']

        # 1) plan del SERVIDOR con el comando de Fabrizio (sube en trozos y pide el plan entero)
        import tempfile
        tmp = out['tmp'] = tempfile.mkdtemp(prefix='kh_e2e_')
        code, txt = cli.run(['--plan', BUNDLE, '--server', SERVER, '--pin', PIN, '--out', os.path.join(tmp, 'plan.json'),
                             '--md', os.path.join(tmp, 'plan.md')])
        assert code == 0, txt[-800:]
        with open(os.path.join(tmp, 'plan.json'), encoding='utf-8') as fh:
            plan = json.load(fh)
        with open(os.path.join(tmp, 'plan.md'), encoding='utf-8') as fh:
            out['plan_md'] = fh.read()
        out['plan'], out['cli_plan_out'] = plan, txt
        out['file_sha'] = cli.last['/api/ontology/import/files'][1]['sha256']
        out['upload'] = cli.last['/api/ontology/import/files'][1]

        # 2) aplicar con la huella del servidor (mismo comando que Fabrizio)
        caught.clear()
        t0 = time.perf_counter()
        code, txt = cli.run(['--apply', BUNDLE, '--server', SERVER, '--pin', PIN, '--plan-sha', plan['plan_sha'],
                             '--confirm-db', dbname])
        out['t']['apply_wall_s'] = round(time.perf_counter() - t0, 2)
        st, res = cli.last['/api/ontology/import/apply']
        assert code == 0 and st == 200, (st, json.dumps(res)[:600])
        out['res'], out['gates1'] = res, [(g, r) for g, r in caught if r]
        with session_scope() as s:
            out['c1'] = _counts(s)
            out['apply_tx'] = {
                'decisions_in_tx': s.execute(text('select kind from decisions where txid = (select txid from decisions '
                                                  'where id = cast(:d as uuid))'), {'d': res['decision_id']}).scalars().all(),
                'versions_in_tx': s.execute(text("select version from kh_tx_versions where name = 'graph' and txid = "
                                                 "(select txid from decisions where id = cast(:d as uuid))"),
                                            {'d': res['decision_id']}).scalars().all(),
                'upload_decisions': sorted(s.execute(text("select status from decisions where kind = 'ontology.bulk_import' "
                                                          "and subject->>'stage' = 'upload'")).scalars().all()),
                'apply_decisions': s.execute(text("select count(*) from decisions where kind = 'ontology.bulk_import' "
                                                  "and subject->>'stage' is null")).scalar()}
            out['pending_rows_run1'] = s.execute(text(
                'select count(*) from import_pending_links where run_id = cast(:r as uuid)'),
                {'r': CI._run_uuid(res['run_id'])}).scalar()
            out['dedup_into_proposal'] = s.execute(text(
                "select e.object_id, e.target_id, e.payload->>'rel_type' from events e join links l "
                "on l.id = cast(e.payload->'properties'->>'dedup_of' as uuid) "
                "where e.source = :src and e.event_type = 'LinkCreated' "
                "and e.payload->'properties'->>'dedup_of' is not null "
                "and coalesce(e.payload->'properties'->>'status', '') not in ('proposed', 'rejected') "
                "and l.properties->>'status' in ('proposed', 'rejected')"), {'src': res['source_channel']}).all()
            out['self_loops'] = s.execute(text(
                "select object_id, payload->'properties'->>'record_id' from events where source = :src and "
                "event_type = 'LinkCreated' and object_id = target_id"), {'src': res['source_channel']}).all()
            out['source_trust'] = {r[0]: int(r[1]) for r in s.execute(text(
                "select id, (properties->>'trust')::int from objects where type = 'Source' and properties ? 'trust'"))}
            out['pending_default'] = len(CI.pending_links(s))                   # lo que el plan del servidor reintenta
            out['pending_all'] = len(CI.pending_links(s, limit=100000))
        # 3) UNA generación nueva: el constructor (no una reconstrucción forzada) se pone al día una sola vez
        g = builder.ensure(min_version=res['graph_version_after'], timeout=60)
        assert g is not None, 'las vistas no se pusieron al día'
        out['builds_delta'] = builder.state()['builds'] - builds0
        from core.hotviews import hot
        v1 = hot.graph()
        out['v1'] = _photo(v1)
        with session_scope() as s:
            out['hvb1'] = [tuple(r) for r in s.execute(text('select name, graph_version from hot_view_builds')).all()]
        # ficha, MCP, resolvedor sobre lo aplicado
        out['cards'] = {}
        for rid, cid in FICHAS_CARD.items():
            r = client.get(f'/api/hot/card/{cid}?structure=0')
            out['cards'][cid] = (r.status_code, (r.get_json() or {}).get('data') or {})
        r = client.post('/api/mcp/tokens', headers={'X-Trade-Pin': PIN, 'Content-Type': 'application/json'},
                        data=json.dumps({'name': 'e2e lote L', 'scopes': ['read']}))
        assert r.status_code == 201, r.get_data(as_text=True)[:300]
        tok = r.get_json()['token']
        out['mcp'] = {
            'get_company': _mcp(client, tok, 'get_company', {'id_or_ticker': 'CATL', 'include_live': False, 'detail': 'full'}),
            'search': {q: _mcp(client, tok, 'search_companies', {'query': q, 'limit': 10})
                       for q in ('Boeing', 'RTX', 'Samsung', 'Ørsted')},
            'rank_en': _mcp(client, tok, 'rank_by_market', {'market': 'EV batteries', 'limit': 20}),
            'rank_es': _mcp(client, tok, 'rank_by_market', {'market': 'baterías', 'limit': 20}),
        }
        from core import entities
        out['resolve'] = {}
        for rid in list(FICHAS_CARD) + ['fb-2026-boeing', 'fb-2026-rsted', 'fb-2026-samsung-electronics']:
            ids = (out['records'][rid]['identity'].get('ids') or {})
            for k in ('lei', 'isin'):
                vals = ids.get(k)
                for x in ([vals] if isinstance(vals, str) else (vals or []))[:1]:
                    out['resolve'][(rid, k, x)] = entities.resolve_ids({k: x})
        r = client.get('/api/ontology/import/runs')
        out['runs1'] = r.get_json()

        # 4) deshacer con el comando de Fabrizio
        code, txt = cli.run(['--rollback', res['run_id'], '--confirm-db', dbname, '--server', SERVER, '--pin', PIN])
        st, rb = cli.last['/api/ontology/import/rollback']
        assert code == 0 and st == 200, (st, rb)
        out['rb'] = rb
        with session_scope() as s:
            out['c2'] = _counts(s)
            out['pending_after_rb'] = [p for p in CI.pending_links(s, limit=100000)
                                       if p['run_id'] == CI._run_uuid(res['run_id'])]
        out['runs2'] = client.get('/api/ontology/import/runs').get_json()
        v2 = _rebuild()
        out['v2'] = _photo(v2)

        # 5) volver a aplicar (revive las empresas de la corrida deshecha)
        caught.clear()
        code, txt = cli.run(['--plan', BUNDLE, '--server', SERVER, '--pin', PIN, '--out', os.path.join(tmp, 'plan2.json')])
        assert code == 0, txt[-600:]
        with open(os.path.join(tmp, 'plan2.json'), encoding='utf-8') as fh:
            plan2 = json.load(fh)
        out['plan2'] = plan2
        code, txt = cli.run(['--apply', BUNDLE, '--server', SERVER, '--pin', PIN, '--plan-sha', plan2['plan_sha'],
                             '--confirm-db', dbname])
        st, res2 = cli.last['/api/ontology/import/apply']
        assert code == 0 and st == 200, (st, json.dumps(res2)[:600])
        out['res2'], out['gates2'] = res2, [(g_, r_) for g_, r_ in caught if r_]
        v3 = _rebuild()
        out['v3'] = _photo(v3)

        # 6) un lote chico con la MATRIZ de un pendiente de participación («X es dueña de esta empresa»)
        with session_scope() as s:
            cands = []
            for p in CI.pending_links(s):
                cp = p.get('counterparty') or {}
                lei = (cp.get('ids') or {}).get('lei')
                rec = out['records'].get(p['record_id'])
                if not (lei and rec and str(p['relation_id']).startswith('holding-')):
                    continue
                if _holding_kind(rec, p['relation_id']) in HOLDING_IN and not entities.resolve_ids({'lei': lei}):
                    cands.append(p)
        out['parent_candidates'] = len(cands)
        if cands:
            p = sorted(cands, key=lambda x: (x['record_id'], x['relation_id']))[0]
            cp = p['counterparty']
            # nombre NEUTRO: la matriz tiene que encontrarse por su LEI (el nombre de una matriz suele parecerse al de su
            # filial, «China Hongqiao Holdings» ~ «China Hongqiao», y el plan la fusionaría con la filial)
            rec_p = _synth_parent('e2e-parent-1', 'E2EParentCo', 'Zeta Parent Holdings E2E', cp['ids']['lei'])
            r = client.post('/api/ontology/import/plan', json={'records': [rec_p], 'full': 1, 'batch': 'e2e-parent'},
                            headers={'X-Trade-Pin': PIN})
            assert r.status_code == 200, r.get_data(as_text=True)[:400]
            pl3 = r.get_json()['plan']
            out['parent_case'] = {'pending': p, 'plan': pl3,
                                  'resolved': [x for x in pl3.get('pending_resolved') or [] if x.get('from_pending') == p['id']]}
        yield out
    finally:
        mp.undo()
        if out.get('tmp'):
            import shutil
            shutil.rmtree(out['tmp'], ignore_errors=True)
        from core.hotviews import hot, registry
        registry.reset()
        hot.reset()
        Base.metadata.drop_all(engine)


# ── 1. subir + plan del servidor ───────────────────────────────────────────────────────────────────────────────
def test_subida_en_trozos_y_plan_del_servidor(e2e):
    up, plan = e2e['upload'], e2e['plan']
    assert up['status'] == 'stored' and up['n_records'] == 386 and up['batch'] == 'lote-2026-10-15-completas'
    c = plan['counts']
    assert c['records'] == c['valid'] == 386 and c['invalid'] == 0 and c['create'] == 372 and c['merge'] == 14
    assert plan['graph_source'] == 'pg' and plan['graph_version'] == e2e['v0']['gv'] and len(plan['plan_sha']) == 64
    assert f'huella del plan del servidor: {plan["plan_sha"]}' in e2e['cli_plan_out']
    assert '386' in e2e['plan_md'] or 'Fichas' in e2e['plan_md']
    by = {it['record_id']: it for it in plan['items']}
    for rid, existing in FUSIONES.items():
        assert by[rid]['action'] == 'merge' and by[rid]['id'] == existing, (rid, by[rid]['action'], by[rid]['id'])
    wc = plan['what_changes']
    assert wc['available'] and wc['before']['rho'] == e2e['v0']['rho'] and wc['before']['tsmc_hit'] == e2e['v0']['tsmc']
    assert [x['id'] for x in wc['before']['chokepoints']] == e2e['v0']['top20']


# ── 2. aplicar = lo planeado, una decisión, una versión, una generación ────────────────────────────────────────
def test_aplicar_cuenta_lo_planeado(e2e):
    plan, res, c0, c1 = e2e['plan'], e2e['res'], e2e['c0'], e2e['c1']
    links = plan['counts']['links']
    assert res['status'] == 'ok' and res['plan_sha'] == plan['plan_sha']
    assert res['events'] == plan['counts']['events_estimated'] == c1['events'] - c0['events']
    assert res['objects_created'] == plan['counts']['create'] + plan['counts']['sources_new']     # empresas + fuentes
    assert res['objects_updated'] == plan['counts']['merge']
    assert res['links_created'] + res['links_dedup'] == links['live'] + links['proposed']
    assert res['pending'] == links['pending'] == e2e['pending_rows_run1'] and res['quarantine'] == links['quarantine']
    assert res['elapsed_ms'] < 60000, res['elapsed_ms']


def test_una_decision_una_version_una_generacion(e2e):
    res, tx = e2e['res'], e2e['apply_tx']
    assert tx['decisions_in_tx'] == ['ontology.bulk_import']                 # nada más en esa transacción
    assert tx['versions_in_tx'] == [res['graph_version_after']]
    assert res['graph_version_after'] == res['graph_version_before'] + 1 == e2e['v0']['gv'] + 1
    # aplicar = UNA decisión; cada subida es otra escritura (import_files) con la suya: el comando --plan sube el
    # archivo (se guarda) y --apply lo vuelve a subir (ya estaba: decisión 'noop')
    assert tx['apply_decisions'] == 1 and tx['upload_decisions'] == ['noop', 'recorded']
    assert e2e['v1']['gv'] == res['graph_version_after'] and e2e['builds_delta'] == 1
    assert sorted(n for n, v in e2e['hvb1'] if v == res['graph_version_after']) == ['graph_core', 'impact']


# ── 3. el grafo de los lectores ────────────────────────────────────────────────────────────────────────────────
def test_lectores_tienen_las_empresas_nuevas_y_las_fusiones_sin_duplicar(e2e):
    plan, v0, v1 = e2e['plan'], e2e['v0'], e2e['v1']
    created = {it['id'] for it in plan['items'] if it['action'] == 'create'}
    assert len(created) == 372 and not created & v0['nodes']
    assert v1['nodes'] == v0['nodes'] | created
    for rid, oid in FUSIONES.items():
        n0, n1 = v0['by_id'][oid], v1['by_id'][oid]
        assert n1.get('label') == n0.get('label') and n1.get('cat') == n0.get('cat')      # lo curado no se pisa
        assert n1.get('import_run') == e2e['res']['run_id'], oid                            # …y la ficha sí entró
        name = e2e['records'][rid]['identity']['short_name']
        from core.entities import norm
        twins = [i for i in created if norm(v1['by_id'][i].get('label') or '') == norm(name)]
        assert twins == [], (rid, twins)
    ok, sc = e2e['mcp']['search']['Boeing']
    assert not ok and sc['results'][0]['id'] == 'Boeing'
    assert [x['id'] for x in e2e['mcp']['search']['RTX'][1]['results']][:1] == ['Raytheon']
    assert e2e['mcp']['search']['Samsung'][1]['results'][0]['id'] == 'Samsung'
    assert e2e['mcp']['search']['Ørsted'][1]['results'][0]['id'] == 'Orsted'
    for q, (_err, sc) in e2e['mcp']['search'].items():
        assert not [x['id'] for x in sc['results'] if x['id'] in created and norm(x.get('label') or '') == norm(q)], q


def test_lectores_vinculos_vivos_si_propuestos_y_terminados_no(e2e):
    plan, v0, v1 = e2e['plan'], e2e['v0'], e2e['v1']
    live = {(l['source'], l['target'], l['rel_type']) for _it, l in _plan_links(plan)
            if l['route'] == 'live' and not l.get('valid_to') and l['source'] != l['target']}
    proposed = {(l['source'], l['target'], l['rel_type']) for _it, l in _plan_links(plan) if l['route'] == 'proposed'}
    ended = {(l['source'], l['target'], l['rel_type']) for _it, l in _plan_links(plan) if l['route'] == 'live' and l.get('valid_to')}
    missing = sorted(live - v1['links'])
    assert missing == [], f'{len(missing)} vínculos VIVOS del plan no están en el grafo de lectura: {missing[:6]}'
    assert v1['links'] - v0['links'] <= live
    assert not (proposed - live - v0['links']) & v1['links']
    assert not (ended - live - v0['links']) & v1['links']


def test_un_vivo_nunca_se_deduplica_contra_una_propuesta(e2e):
    """bulk_import._dedup_twin: una fila PROPUESTA (confianza 0, fuera del kernel) no «cubre» un vínculo vivo con el
    mismo peso crudo: si lo cubre, el vivo se pierde (HitachiEnergy→TenneT, NTT→NTTDATA)."""
    assert e2e['dedup_into_proposal'] == []


# ── 4. kernel: lo aplicado = el «¿qué cambia?» del plan ────────────────────────────────────────────────────────
def test_kernel_tras_aplicar_igual_al_plan(e2e):
    wc, v1 = e2e['plan']['what_changes'], e2e['v1']
    after = wc['after']
    assert v1['tsmc'] == after['tsmc_hit'] and v1['top20'] == [x['id'] for x in after['chokepoints']]
    assert v1['core_nodes'] == after['nodes']
    assert round(v1['rho'], 6) == round(after['rho'], 6), (v1['rho'], after['rho'])


def test_kernel_matriz_entera_igual_a_la_esperada(e2e):
    """Cada entrada de las matrices (origen, destino, tipo) = la de antes + los vivos vigentes del plan."""
    exp = _expected_kernel(e2e['v0']['triples'], e2e['plan'])
    real = e2e['v1']['triples']
    falta = sorted(set(exp) - set(real))
    sobra = sorted(set(real) - set(exp))
    peso = sorted(k for k in set(exp) & set(real) if abs(exp[k] - real[k]) > 1e-9)
    assert (falta, sobra, peso) == ([], [], []), (falta[:5], sobra[:5], peso[:5])


# ── 5. ficha, MCP y resolvedor ─────────────────────────────────────────────────────────────────────────────────
def test_ficha_market_position_y_facilities_con_fuente(e2e):
    from core.hotviews.views.card import facilities_of, market_position_of
    by = {it['record_id']: it for it in e2e['plan']['items']}
    for rid, cid in FICHAS_CARD.items():
        st, data = e2e['cards'][cid]
        assert st == 200 and data.get('id', cid) == cid
        props = by[rid]['props']
        assert data['market_position'] == market_position_of(props.get('market_position')) != []
        assert data['facilities'] == facilities_of(props.get('facilities'))
        assert len(data['facilities']) == len(e2e['records'][rid].get('facilities') or [])
        for e in data['market_position'] + data['facilities']:
            assert str(e['source_url']).startswith('http') and e['as_of'], (cid, e)
    assert len(e2e['cards']['CATL'][1]['facilities']) == 2 and len(e2e['cards']['BWXTechnologies'][1]['facilities']) == 6
    assert e2e['cards']['ABB'][1]['facilities'] == []                       # la ficha de ABB no trae plantas


def test_mcp_get_company_con_lo_importado(e2e):
    err, sc = e2e['mcp']['get_company']
    assert not err and sc['id'] == 'CATL' and sc['country'] == 'China'
    assert sc['market_position'] == e2e['cards']['CATL'][1]['market_position']
    assert sc['facilities'] == e2e['cards']['CATL'][1]['facilities']


def test_mcp_rank_by_market_baterias(e2e):
    cat = e2e['records']['fb-2026-catl']['market_position'][0]
    for key in ('rank_en', 'rank_es'):
        err, sc = e2e['mcp'][key]
        assert not err and sc['graph_source'] == 'pg'
        top = sc['items'][0]
        assert top['id'] == 'CATL' and top['share_pct'] == cat['share_pct'] and top['rank'] == cat['rank']
        assert all(str(x['source_url']).startswith('http') and x['as_of'] for x in sc['items'])


def test_mcp_rank_by_market_no_mezcla_mercados(e2e):
    """«EV batteries» no es «celdas para smartphones», «ánodos» ni «reciclaje»: el ranking compara SOLO el mercado
    pedido (mcp_server/ops.py: 'EV' nunca coincidía — token de 2 letras — y todo mercado con «baterías» sacaba 0,5)."""
    err, sc = e2e['mcp']['rank_en']
    otros = [(x['id'], x['market']) for x in sc['items']
             if not re.search(r'veh[ií]cul|\bev\b|el[eé]ctric', str(x['market']), re.I)]
    assert otros == [], otros[:6]


def test_resolve_ids_por_lei_e_isin(e2e):
    want = {'fb-2026-catl': 'CATL', 'fb-2026-abb': 'ABB', 'fb-2026-bwx-technologies': 'BWXTechnologies',
            'fb-2026-boeing': 'Boeing', 'fb-2026-rsted': 'Orsted', 'fb-2026-samsung-electronics': 'Samsung'}
    assert len(e2e['resolve']) >= 8
    for (rid, kind, _x), r in e2e['resolve'].items():
        assert r and r['id'] == want[rid] and r['method'] == kind and not r['conflicts'], (rid, kind, r)


# ── 6. puertas ─────────────────────────────────────────────────────────────────────────────────────────────────
def _by_rule(gates, gate):
    """Conteo COMPLETO por regla de TODOS los reportes de esa puerta (by_rule_of: también lo recortado a 200)."""
    from core.gates.report import by_rule_of
    c = Counter()
    for g, rep in gates:
        if g == gate:
            c.update(by_rule_of(rep))
    return c


def test_g_import_solo_avisos_ciertos(e2e):
    c = _by_rule(e2e['gates1'], 'ontology.g_import')
    links = e2e['plan']['counts']['links']
    dup = sum(1 for it in e2e['plan']['items'] for x in it['conflicts'] if x.get('kind') == 'possible_duplicate')
    assert set(c) <= {'khr:import.counterparty_resolved', 'khr:import.possible_duplicate'}, dict(c)
    assert c.get('khr:import.counterparty_resolved', 0) == links['pending'] and c.get('khr:import.possible_duplicate', 0) == dup
    assert e2e['res']['gate_import']['by_rule'] == dict(c)


def test_g_bulk_sin_avisos_falsos(e2e):
    """Un vínculo VIVO del plan cita (por su propia evidencia) una fuente con trust ≥ 2: la puerta no puede decir lo
    contrario. Hoy lo dice porque la Source se guarda con el tipo de la PRIMERA cita de la URL (a veces una cita sin
    `source_kind` → 'corporate', trust 1) y no con el que declara la evidencia del vínculo. Tampoco hay lazos."""
    c = _by_rule(e2e['gates1'], 'ontology.g_bulk')
    assert c.get('khr:link.high_conf_trusted_source', 0) == 0, dict(c)
    assert c.get('khr:link.no_self_loop', 0) == 0, dict(c)
    assert e2e['self_loops'] == []
    assert set(c) <= {'khr:link.inverse_flow_live', 'khr:link.dated_fact_has_source', 'khr:link.direction_text_suspect'}, dict(c)


def test_la_fuente_guardada_respalda_la_ruta_viva(e2e):
    pol = e2e['plan']['policy']
    srcs = {s['id']: s for s in e2e['plan']['sources']}
    bad = [(it['record_id'], l['relation_id'], l['source_id'], srcs[l['source_id']]['kind'])
           for it, l in _plan_links(e2e['plan'])
           if l['route'] == 'live' and l.get('source_id') in srcs and srcs[l['source_id']]['trust'] < int(pol['live_min_trust'])]
    assert bad == [], f'{len(bad)} vínculos vivos con una Source guardada de trust < {pol["live_min_trust"]}: {bad[:4]}'
    assert all(e2e['source_trust'].get(sid) == s['trust'] for sid, s in srcs.items())


def test_resumen_de_la_puerta_cubre_todos_los_bloques(e2e):
    """write_events_fast escribe por bloques: el resumen `gate_links` de la respuesta debe sumar TODOS, no el último."""
    res = e2e['res']
    full = _by_rule(e2e['gates1'], 'ontology.g_bulk')
    gl = res.get('gate_links') or {}
    assert gl.get('checked') == res['links_created'], gl
    assert {k: v for k, v in (gl.get('by_rule') or {}).items() if v} == {k: v for k, v in full.items() if v}


# ── 7. deshacer ────────────────────────────────────────────────────────────────────────────────────────────────
def test_deshacer_devuelve_el_grafo_exacto(e2e):
    v0, v2, rb = e2e['v0'], e2e['v2'], e2e['rb']
    assert rb['status'] == 'ok' and rb['decision_id'] and rb['objects_retired'] == 372 and rb['objects_restored'] == 14
    assert v2['nodes'] == v0['nodes'] and v2['links'] == v0['links']
    assert v2['impact_sha'] == v0['impact_sha']
    assert v2['rho'] == v0['rho'] and v2['tsmc'] == v0['tsmc'] == 318 and v2['top20'] == v0['top20']
    assert v2['triples'] == v0['triples']
    for oid in FUSIONES.values():
        # las fusionadas vuelven a lo de antes; una clave que la ficha AÑADIÓ queda en null (ObjectUpdated no borra
        # claves: deshacer escribe el valor previo, que era «no estaba») + la marca rollback_run
        def _same(d):
            return {k: v for k, v in d.items() if v is not None and k not in ('import_run', 'rollback_run')}
        assert _same(v2['by_id'][oid]) == _same(v0['by_id'][oid]), oid
    c1, c2 = e2e['c1'], e2e['c2']
    assert c2['events'] > c1['events'] and c2['links_open'] == e2e['c0']['links_open']
    assert c2['decisions'].get('ontology.import_rollback', 0) - c1['decisions'].get('ontology.import_rollback', 0) == 1


def test_pendientes_de_una_corrida_deshecha_no_se_reintentan(e2e):
    assert e2e['pending_after_rb'] == []
    assert e2e['runs2']['pending_links'] == 0


# ── 8. volver a aplicar ────────────────────────────────────────────────────────────────────────────────────────
def test_volver_a_aplicar_revive_y_da_el_mismo_grafo(e2e):
    plan, plan2, res2, v1, v3 = e2e['plan'], e2e['plan2'], e2e['res2'], e2e['v1'], e2e['v3']
    assert res2['status'] == 'ok' and res2['objects_revived'] == 372 and res2['objects_created'] >= 372
    assert plan2['counts'] == plan['counts'], (plan2['counts'], plan['counts'])
    assert not plan2.get('pending_resolved')
    assert v3['nodes'] == v1['nodes'] and v3['links'] == v1['links']
    assert v3['impact_sha'] == v1['impact_sha'] and v3['triples'] == v1['triples'] and v3['rho'] == v1['rho']


# ── 9. pendientes ──────────────────────────────────────────────────────────────────────────────────────────────
def test_el_plan_reintenta_todos_los_pendientes(e2e):
    """_import_plan_for usa pending_links() con su límite por defecto (500): con 2.050 pendientes de este lote, el
    próximo lote solo reintentaría los 500 más nuevos."""
    assert e2e['pending_default'] == e2e['pending_all'] >= e2e['plan']['counts']['links']['pending']


def test_participacion_pendiente_se_resuelve_con_la_direccion_correcta(e2e):
    """Una participación «la contraparte es MATRIZ / accionista de esta empresa» que queda pendiente se resuelve
    cuando llega la ficha de la matriz: la matriz es el ORIGEN (owns/invest: source = dueño). Hoy el pendiente no
    guarda el papel (this_role) y se resuelve al revés («Newport News es dueña de Huntington Ingalls»)."""
    assert e2e['parent_candidates'] > 0
    case = e2e['parent_case']
    p, res = case['pending'], case['resolved']
    assert len(res) == 1, (p['record_id'], p['relation_id'], len(case['plan'].get('pending_resolved') or []))
    link = res[0]
    assert link['rel_type'] in ('owns', 'invest')
    assert (link['source'], link['target']) == ('E2EParentCo', p['company_id']), (link['source'], link['target'])


def test_contraparte_del_mismo_lote_por_identificador_no_queda_pendiente(e2e):
    """Si la contraparte llega en el MISMO lote y se la nombra con un identificador fuerte (LEI/ISIN…) o el nombre
    exacto de su ficha, no es «la otra empresa aún no está en Khipus»: el resolvedor de pendientes ya la encuentra
    (batch_by_ids / batch_by_name) pero el de las relaciones (_resolve_counterparty) no."""
    from core.entities import norm
    recs = e2e['records']
    by_ids, by_name = {}, {}
    for it in e2e['plan']['items']:
        rec = recs[it['record_id']]
        by_name[norm(rec['identity']['short_name'])] = it['id']
        for k, v in (rec['identity'].get('ids') or {}).items():
            if k in ('lei', 'isin', 'cik', 'figi') and v:
                for x in ([v] if isinstance(v, str) else v):
                    by_ids[(k, str(x).upper())] = it['id']
    stuck = []
    for it, l in _plan_links(e2e['plan']):
        if l['route'] != 'pending':
            continue
        cp = l.get('counterparty') or {}
        hit = next((by_ids[(k, str(x).upper())] for k, v in (cp.get('ids') or {}).items()
                    for x in ([v] if not isinstance(v, list) else v) if (k, str(x).upper()) in by_ids), None)
        if hit and hit != it['id']:
            stuck.append((it['record_id'], l['relation_id'], cp.get('name'), hit))
    assert stuck == [], f'{len(stuck)} vínculos pendientes cuya contraparte llega en el mismo lote: {stuck[:5]}'
