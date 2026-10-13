"""tests/test_review_infra_c.py — revisión de los pasos 9-13 (gobernanza, puertas, ancla/dinero, cliente único).

Cada prueba reproduce un hallazgo verificado y falla con el código anterior:
  · un cambio de release de gobernanza RECONSTRUYE las vistas rápidas (antes /api/hot/impact seguía con el kernel
    viejo y /api/hot/scenario con el nuevo, ambos con el sello viejo); la generación privada del snapshot se clava
    con el release;
  · la puerta G2 ve la confianza de la PROPUESTA en la auto-aplicación (antes marcaba TODA auto-aplicación segura
    como "no se puede aplicar automáticamente");
  · lint de semver: 'initial' solo para la primera versión y el salto de versión debe ser del tamaño declarado;
  · GateReport/1: conteo por regla y desenlace sobre TODOS los resultados, no solo los 200 primeros;
  · un artefacto que el release de la base NO trae (leído del repositorio) queda en el sello de cada decisión y
    en el 🩺;
  · ledger: tras reconocer una ruptura de ≥20 sellos, una alteración NUEVA vuelve a bloquear el dinero real; un
    segundo cambio en una fila ya rota también; alterar + borrar ledger_seals + re-sellar choca con el ancla;
  · cliente: StressAI no le pide a la IA un análisis sin el resultado del motor; la voz no promete "quién gana"
    con un %; el Grafo Temporal toma cifras y ranking del servidor; hotclient.js tiene tope de tiempo y edad viva;
    el mapa no pinta como colapsada a una empresa golpeada al 1 %.
"""
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
NODE = shutil.which('node')
DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')


def _r(*p):
    with open(os.path.join(ROOT, *p), encoding='utf-8') as f:
        return f.read()


# ═════════════════════ 1) release de gobernanza → vistas rápidas ═════════════════════
@pytest.fixture
def snapshot_app(monkeypatch):
    import ontology.db as odb
    import server
    from core import http as h
    from core.hotviews import builder, hot, registry
    monkeypatch.setattr(odb, 'ontology_available', lambda: False)
    registry.reset()
    hot.reset()
    builder.build_once()
    with h._rate_lock:
        h._rate_buckets.clear()
    yield server.app.test_client()
    registry.reset()
    hot.reset()
    with h._rate_lock:
        h._rate_buckets.clear()


def _top(d):
    return {v['id']: v['pct'] for v in d['victims']}


def test_cambio_de_release_reconstruye_las_vistas(snapshot_app, monkeypatch):
    from core import governance as G
    from core.hotviews import hot
    from matrix import engine as E
    c = snapshot_app
    base_i = c.get('/api/hot/impact/TSMC?top=20').get_json()
    rel0 = base_i['view']['release']
    assert rel0 == G.release()[0]
    arts = copy.deepcopy(G.repo_bundle().artifacts)
    arts['kernel.params']['params']['damping'] = 0.5
    arts['kernel.params'].update(semver='2.0.0', hash='f' * 64)
    b = G._bundle(arts, '2.0.0', 'db', 'db', True)
    monkeypatch.setattr(G, '_db_on', lambda: True)
    try:
        G._swap(b)
        assert E.DAMPING == 0.5 and G.release()[0] == b.release_hash
        i = c.get('/api/hot/impact/TSMC?top=20').get_json()
        s = c.post('/api/hot/scenario', json={'shocks': [{'id': 'TSMC', 'magnitude': 1.0}], 'top': 20}).get_json()
        # la generación publicada se rehízo con el kernel NUEVO y lleva su sello
        assert i['view']['release'] == b.release_hash and i['view']['release'] != rel0
        assert s['view']['release'] == b.release_hash
        assert _top(i['data']) == _top(s['data'])                        # un solo kernel: el mismo número
        assert _top(i['data']) != _top(base_i['data'])                   # y no es el del kernel viejo
        # los lectores (hot.graph) tampoco se quedan con la generación privada del release viejo
        g = hot.graph()
        assert g is not None and b.release_hash[:8] in g.generation
    finally:
        G._swap(None)                       # vuelve el release del repositorio (y sus constantes)
    assert E.DAMPING == 0.6 and G.release()[0] == rel0
    i = c.get('/api/hot/impact/TSMC?top=20').get_json()
    assert i['view']['release'] == rel0 and _top(i['data']) == _top(base_i['data'])


def test_stale_si_la_generacion_es_de_otro_release(monkeypatch):
    from core.hotviews import builder, registry
    import ontology.db as odb
    monkeypatch.setattr(odb, 'ontology_available', lambda: False)
    registry.reset()
    try:
        g = builder.build_once()
        assert registry.lag(g)[1] is False and builder.release_current(g)
        monkeypatch.setattr(g, 'release', '0' * 64)
        assert registry.lag(g)[1] is True and not builder.release_current(g)
    finally:
        registry.reset()


# ═════════════════════ 2) G2: confianza de la propuesta en la auto-aplicación ═════════════════════
def _g2_rules(conf):
    import core.gates as gates
    from core import identity
    from core.gates import focus as gf
    from ontology.actions import ACTION_CATALOG
    schema = ACTION_CATALOG['AnotarObjeto'][0]
    payload = {'object_id': 'NVDA', 'texto': 'nota segura'}
    triples, foc = gf.gather_action('AnotarObjeto', payload, identity.system('auto_apply', declared='Cartografo'),
                                    schema, schema(**payload), auto_apply=True, ident='t-g2', confidence=conf)
    rep = gates.evaluate('ontology.g2.action', triples, foc)
    return {r['rule'] for r in (rep or {}).get('results') or ()}


def test_g2_auto_aplicacion_segura_no_es_falso_positivo():
    assert 'khr:action.auto_apply_allowed' not in _g2_rules(0.9)
    assert 'khr:action.auto_apply_allowed' in _g2_rules(0.3)          # bajo AUTO_MIN_CONFIDENCE sí avisa


@pytest.fixture(scope='module')
def db():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    from core import governance, ledger
    from ontology.db import _get_engine, init_schema, session_scope
    from ontology.models import Base
    from ontology.service import apply_event
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    governance._reset_for_tests()
    assert init_schema(retries=1)
    with session_scope() as s:
        for oid in ('TSMC', 'NVDA'):
            apply_event(s, 'ObjectCreated', {'label': oid, 'type': 'Company'}, valid_from='2000-01-01',
                        source='test', actor='pytest', object_id=oid)
    ledger._invalidate_chain()
    yield engine
    ledger._invalidate_chain()
    Base.metadata.drop_all(engine)
    governance._reset_for_tests()


@needs_db
def test_auto_cycle_no_deja_aviso_auto_apply_allowed(db):
    from sqlalchemy import text

    from ontology import agents
    from ontology.db import session_scope
    from ontology.models import ProposedAction
    with session_scope() as s:
        s.add(ProposedAction(agent='Cartografo', action_type='AnotarObjeto',
                             payload={'object_id': 'NVDA', 'texto': 'nota segura'}, object_id='NVDA',
                             confidence=0.9, explanation='x', status='pending'))
    orig = agents.run_agents
    agents.run_agents = lambda s: {}
    try:
        with session_scope() as s:
            out = agents.auto_cycle(s)
    finally:
        agents.run_agents = orig
    assert [a['action'] for a in out['auto_applied']] == ['AnotarObjeto']
    with db.connect() as c:
        rules = [r[0] for r in c.execute(text(
            "SELECT v.rule_iri FROM decisions d JOIN decision_violations v ON v.decision_id = d.id "
            "WHERE d.principal_id = 'system:auto_apply'")).all()]
    assert 'khr:action.auto_apply_allowed' not in rules


# ═════════════════════ 3) lint de semver ═════════════════════
@pytest.fixture()
def repo_copy(tmp_path, monkeypatch):
    from core import governance as G
    dst = tmp_path / 'governance'
    shutil.copytree(os.path.join(ROOT, 'governance', 'artifacts'), dst / 'artifacts')
    shutil.copy(os.path.join(ROOT, 'governance', 'manifest.json'), dst / 'manifest.json')
    monkeypatch.setattr(G, 'ART_DIR', str(dst / 'artifacts'))
    monkeypatch.setattr(G, 'MANIFEST_PATH', str(dst / 'manifest.json'))
    G._STATE['repo'] = None
    yield dst
    G._STATE['repo'] = None


def _kernel_version(repo_copy, semver, **upd):
    with open(repo_copy / 'artifacts' / 'kernel.params@1.0.0.json', encoding='utf-8') as fh:
        d = json.load(fh)
    d['semver'] = semver
    d['params']['damping'] = 0.5
    for k in ('change_kind', 'parent'):
        d.pop(k, None)
    d.update({k: v for k, v in upd.items() if v is not None})
    with open(repo_copy / 'artifacts' / f'kernel.params@{semver}.json', 'w', encoding='utf-8') as fh:
        json.dump(d, fh, ensure_ascii=False, indent=2)


def test_initial_solo_para_la_primera_version(repo_copy):
    from scripts import build_governance as B
    _kernel_version(repo_copy, '1.0.1')                    # sin change_kind (= 'initial') y cambia el kernel
    B.write()
    probs = B.check(verbose=False)
    assert any('kernel.params@1.0.1' in p and 'primera versión' in p for p in probs), probs


@pytest.mark.parametrize('semver,kind', [('1.0.1', 'major'), ('2.0.0', 'minor'), ('1.1.0', 'patch'),
                                         ('2.0.0', 'patch')])
def test_el_salto_debe_ser_del_tamano_declarado(repo_copy, semver, kind):
    from scripts import build_governance as B
    _kernel_version(repo_copy, semver, change_kind=kind, parent='kernel.params@1.0.0')
    probs = B.semver_problems(B.G.scan_repo())
    assert any(f'kernel.params@{semver}' in p and 'no coincide con el salto' in p for p in probs), probs


def test_major_bien_declarado_pasa(repo_copy):
    from scripts import build_governance as B
    # la copia reemplaza kernel.params@2.0.0 por uno falso: sus hijas reales (2.1.0, batch I3) ya no son su MINOR
    for f in (repo_copy / 'artifacts').glob('kernel.params@2.*.json'):
        if f.name != 'kernel.params@2.0.0.json':
            f.unlink()
    _kernel_version(repo_copy, '2.0.0', change_kind='major', parent='kernel.params@1.0.0')
    assert B.semver_problems(B.G.scan_repo()) == []


# ═════════════════════ 4) GateReport/1: conteo completo ═════════════════════
def test_reporte_recortado_conserva_el_conteo_por_regla():
    import core.gates as gates
    from core.gates import focus as gf
    from core.gates import report as gr
    lim, flow = gf._limits(), gf._flow_rels()
    triples = []
    for n in range(600):
        t, _f = gf.link_triples({'id': f'bulk:{n}', 'source': f'S{n}', 'target': f'T{n}', 'rel': 'notarel',
                                 'weight': 9, 'confidence': None, 'valid_from': None},
                                {f'S{n}': {'type': None, 'live': True}, f'T{n}': {'type': None, 'live': True}},
                                (), {}, lim, flow)
        triples += t
    rep = gates.evaluate('ontology.g_bulk', list(dict.fromkeys(triples)), None)
    assert len(rep['results']) == gr.MAX_RESULTS and rep['truncated'] == rep['n_results'] - gr.MAX_RESULTS
    br = gr.by_rule_of(rep)
    assert br['khr:link.rel_in_vocab'] == 600 and br['khr:link.weight_range'] == 600
    assert sum(br.values()) == rep['n_results']


# ═════════════════════ 5) artefacto que el release de la base no trae ═════════════════════
def test_artefacto_fuera_del_release_queda_en_el_sello(monkeypatch):
    from core import decisions
    from core import governance as G
    repo = G.repo_bundle()
    arts = {a: v for a, v in copy.deepcopy(repo.artifacts).items() if a != 'policy.decide'}
    b = G._bundle(arts, '1.0.0', 'db', 'db', True)
    monkeypatch.setattr(G, '_db_on', lambda: True)
    monkeypatch.setitem(G._STATE, 'db', b)
    fb = G.fallbacks()
    assert list(fb) == ['policy.decide'] and fb['policy.decide']['hash'] == repo.artifacts['policy.decide']['hash']
    assert G.param('policy.decide', 'min_conf') == repo.artifacts['policy.decide']['params']['min_conf']
    st = G.status()
    assert st['repo_fallback'] == fb
    assert 'policy.decide' in G.explain('es') and 'policy.decide' in G.explain('en')
    stamp = decisions.stamp()
    assert stamp['release_fallback'] == fb and stamp['release_hash'] == b.release_hash
    monkeypatch.setitem(G._STATE, 'db', None)
    assert G.fallbacks() == {}


# ═════════════════════ 6) ledger: rupturas nuevas tras un reconocimiento grande; ancla ═════════════════════
def _seal_all(engine, table='events'):
    from sqlalchemy import text

    from core import ledger
    for _ in range(80):
        ledger.seal()
        with engine.connect() as c:
            left = c.execute(text(f"SELECT count(*) FROM {table} t WHERE NOT EXISTS (SELECT 1 FROM ledger_seals s "
                                  f"WHERE s.row_table = '{table}' AND s.row_id = t.id::text)")).scalar()
        if not left:
            return
        time.sleep(0.2)


def _tamper(engine, oids, actor='hacker'):
    from sqlalchemy import text
    with engine.begin() as c:
        c.execute(text('ALTER TABLE events DISABLE TRIGGER events_no_modify'))
        c.execute(text('UPDATE events SET actor = :a WHERE object_id = ANY(:o)'), {'a': actor, 'o': list(oids)})
        c.execute(text('ALTER TABLE events ENABLE TRIGGER events_no_modify'))


@pytest.fixture()
def fresh_db():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    from core import governance, ledger
    from ontology.db import _get_engine, init_schema
    from ontology.models import Base
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    governance._reset_for_tests()
    with ledger._LOCK:
        ledger._LINEAGE['id'] = None
    assert init_schema(retries=1)
    ledger._invalidate_chain()
    yield engine
    ledger._invalidate_chain()
    with ledger._LOCK:
        ledger._LINEAGE['id'] = None
    Base.metadata.drop_all(engine)
    governance._reset_for_tests()


@needs_db
def test_ruptura_nueva_tras_reconocer_una_grande_bloquea_el_dinero(fresh_db):
    from sqlalchemy import text

    from core import identity, ledger
    from ontology.db import session_scope
    from ontology.service import apply_event
    eng = fresh_db
    with session_scope() as s:
        for i in range(30):
            apply_event(s, 'ObjectCreated', {'label': f'M{i}', 'type': 'Company'}, valid_from='2000-01-01',
                        source='test', actor='pytest', object_id=f'M{i:02d}')
    _seal_all(eng)
    assert ledger.verify()['ok']
    with eng.connect() as c:
        objs = [r[0] for r in c.execute(text(
            "SELECT e.object_id FROM ledger_seals s JOIN events e ON s.row_id = e.id::text "
            "WHERE s.row_table = 'events' ORDER BY s.seal_no")).all()]
    _tamper(eng, objs[:20])
    v = ledger.verify(record_break=True)
    assert not v['ok'] and v['broken_total'] == 20 and v['break_id']
    ledger._invalidate_chain()
    assert ledger.money_gate()[0] is False
    with session_scope() as s:
        ledger.chain_ack(s, identity.operator(), note='revisado')
    ledger._invalidate_chain()
    assert ledger.money_gate()[0] is True
    # la misma ruptura no se vuelve a registrar
    v = ledger.verify(record_break=True)
    ledger._invalidate_chain()
    assert ledger.money_gate()[0] is True
    # una alteración NUEVA más adelante (fuera de los 20 primeros listados) → bloquea otra vez
    _tamper(eng, [objs[25]])
    v = ledger.verify(record_break=True)
    assert len(v['broken']) == 20 and v['broken_total'] == 21 and v['break_id']
    ledger._invalidate_chain()
    assert ledger.money_gate()[0] is False
    with session_scope() as s:
        ledger.chain_ack(s, identity.operator(), note='revisado 2')
    ledger._invalidate_chain()
    assert ledger.money_gate()[0] is True
    # un SEGUNDO cambio en una fila ya rota y reconocida también es nuevo
    _tamper(eng, [objs[3]], actor='hacker-2')
    v = ledger.verify(record_break=True)
    assert v['break_id']
    ledger._invalidate_chain()
    assert ledger.money_gate()[0] is False


@needs_db
def test_alterar_borrar_sellos_y_resellar_choca_con_el_ancla(fresh_db):
    from sqlalchemy import text

    from core import ledger
    from ontology.db import init_schema, session_scope
    from ontology.service import apply_event
    eng = fresh_db
    with session_scope() as s:
        for i in range(10):
            apply_event(s, 'ObjectCreated', {'label': f'R{i}', 'type': 'Company'}, valid_from='2000-01-01',
                        source='test', actor='pytest', object_id=f'R{i:02d}')
    _seal_all(eng)
    a = ledger.anchor()
    assert a['created'] and a['verify']['ok']
    with eng.begin() as c:
        c.execute(text('ALTER TABLE events DISABLE TRIGGER events_no_modify'))
        c.execute(text("UPDATE events SET actor = 'hacker' WHERE object_id = 'R03'"))
        c.execute(text('ALTER TABLE events ENABLE TRIGGER events_no_modify'))
        c.execute(text('DROP TABLE ledger_seals CASCADE'))
    assert init_schema(retries=1)
    _seal_all(eng)
    v = ledger.verify(record_break=True)
    assert not v['ok'] and any(b['reason'] == 'anchor_mismatch' for b in v['broken']), v['broken']
    ledger._invalidate_chain()
    assert ledger.money_gate()[0] is False


# ═════════════════════ 7) sombras: mensaje de la forma vs política ═════════════════════
def test_mensaje_de_trust_coincide_con_la_politica():
    """link.ttl escribe el umbral de trust en el TEXTO del mensaje (vive dentro del IR gobernado): si
    policy.gates.limits.min_trust cambia, hay que publicar también una versión nueva de las formas."""
    from core import governance
    mt = governance.param('policy.gates', 'limits')['min_trust']
    ttl = _r('governance', 'shapes', 'link.ttl')
    nums = re.findall(r'trust ≥ (\d+(?:[.,]\d+)?)', ttl)
    assert nums and all(float(n.replace(',', '.')) == float(mt) for n in nums), (nums, mt)


# ═════════════════════ 8) cliente ═════════════════════
def test_stressai_no_inventa_sin_resultado_del_motor():
    app = _r('app.html')
    i = app.index('const StressAI = {')
    run = app[i:i + 2600]
    assert 'stressRes' in run and 'r.ok' in run and 'stressId===id' in run
    assert run.index('showAIFloat') < run.index('DataLayer.aiComplete')      # el aviso va antes de la IA
    assert 'StressAI.run(stressId)' in app                                    # el botón reusado sigue a la empresa
    assert "(stressAffected.size)" not in run and "Math.round(v.pct)+'%'" in run
    # mapa: gris "colapsada" solo desde STRESS_DEAD_PCT; el resto se atenúa según su %
    assert 'STRESS_DEAD_PCT' in app and "classed('node-collapsed', d=>stressAffected.has(d.id))" not in app


def test_voz_no_promete_quien_gana_con_un_porcentaje():
    import server
    assert 'who wins' not in server.BIXBY_SYSTEM_PROMPT
    tools = {t['name']: t for t in server._bixby_client_tools()}
    desc = json.dumps(tools['run_live_simulation'], ensure_ascii=False)
    assert 'who wins' not in desc and 'NOT a gain' in desc
    vjs = _r('engine', 'voice.js')
    assert 'rivals_note' in vjs and 'no es una ganancia' in vjs and 'not a gain' in vjs


def test_grafo_temporal_sin_motor_propio_de_cifras():
    tg = _r('engine', 'temporal-graph.js')
    assert 'casSize' not in tg and 'entidades afectadas en cascada' not in tg and '} afectados</span>' not in tg
    assert 'KH.simulate(' in tg and 'KH.chokepoints(' in tg
    # textos nuevos bilingües
    for k in ('hitSrv', 'computing', 'srvLine', 'reachLine', 'portRisk', 'chokeHead', 'chokeSub', 'chokeN', 'chokeTip'):
        m = re.search(k + r":\s*\{ es: '([^']+)', en: '([^']+)' \}", tg)
        assert m and m.group(1) != m.group(2), k


HARNESS = r"""
const fs = require('fs'), vm = require('vm');
let hang = false, now0 = Date.now(), shift = 0;
const W = { LANG: 'es', navigator: { onLine: true }, setTimeout, clearTimeout, NODES: [], NODE_BY_ID: {} };
W.AbortController = AbortController;
let aborted = 0;
W.fetch = (url, init) => {
  if (init && init.signal) init.signal.addEventListener('abort', () => { aborted++; });
  if (hang) return new Promise(() => {});
  const tag = '"e1"';
  if ((init.headers || {})['If-None-Match'] === tag)
    return Promise.resolve({ ok: false, status: 304, headers: { get: (k) => k === 'ETag' ? tag : null }, json: async () => null });
  return Promise.resolve({ ok: true, status: 200, headers: { get: (k) => k === 'ETag' ? tag : (k === 'X-Khipu-Graph-Version' ? '0' : null) },
    json: async () => ({ data: { id: 'TSMC', affected: 1, reach_1: 1, victims: [{ id: 'Nvidia', pct: 50, hop: 1 }] },
      view: { generation: 'g0.r1.c1.snapshot', graph_version: 0, source: 'snapshot', age_ms: 8000, stale: false } }) });
};
W.globalThis = W; W.window = W;
vm.createContext(W);
vm.runInContext('(function(){var n=Date.now;Date.now=function(){return n()+globalThis.__shift;};})()', Object.assign(W, { __shift: 0 }));
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), W);
const KH = W.KhipuHot, R = {};
(async () => {
  let r = await KH.simulate({ targets: ['TSMC'] });
  R.s0 = KH.stamp(r.view);
  W.__shift = 3 * 3600 * 1000;                  // 3 h después: la caché se revalida (304) y la edad crece
  r = await KH.simulate({ targets: ['TSMC'] });
  R.s1 = KH.stamp(r.view);
  W.__shift = 0;
  KH.flush(); hang = true;
  const t0 = Date.now();
  const p1 = KH.impact('Intel'), p2 = KH.impact('Intel');
  const [a, b] = await Promise.all([p1, p2]);
  R.timeout = { code: a.code, same: a === b, ms: Date.now() - t0, aborted, err_es: a.error };
  hang = false;
  r = await KH.impact('Intel');
  R.after = r.ok;
  console.log(JSON.stringify(R));
})().catch(e => console.log(JSON.stringify({ fatal: String(e && e.stack || e) })));
"""


def test_hotclient_tope_de_tiempo_y_edad_viva(tmp_path):
    if not NODE:
        pytest.skip('node no instalado')
    hc = _r('engine', 'hotclient.js')
    hc = hc.replace('var FETCH_TIMEOUT_MS = 8000;', 'var FETCH_TIMEOUT_MS = 300;')   # la prueba no espera 8 s
    assert 'FETCH_TIMEOUT_MS = 300' in hc
    (tmp_path / 'hc.js').write_text(hc, encoding='utf-8')
    (tmp_path / 'h.js').write_text(HARNESS, encoding='utf-8')
    out = subprocess.run([NODE, str(tmp_path / 'h.js'), str(tmp_path / 'hc.js')], capture_output=True, text=True,
                         timeout=60, cwd=str(tmp_path))
    lines = [x for x in out.stdout.splitlines() if x.startswith('{')]
    assert lines, out.stdout + out.stderr
    R = json.loads(lines[-1])
    assert 'fatal' not in R, R
    assert R['s0'].endswith('hace 8 s')
    assert R['s1'].endswith('hace 3 h'), R['s1']                     # antes: "hace 8 s" para siempre
    t = R['timeout']
    assert t['code'] == 'timeout' and t['same'] and t['aborted'] >= 1 and t['ms'] < 5000, t
    assert 'tardó demasiado' in t['err_es']
    assert R['after'] is True                                        # la clave colgada no queda bloqueada
    src = _r('engine', 'hotclient.js')
    assert 'FETCH_TIMEOUT_MS = 8000' in src and 'took too long' in src
