"""UN SOLO LUGAR DONDE GUARDAR (Fabrizio, 2026-10-15: «que solo haya uno donde guardar, no 3, elimina o las carteras o
las posiciones»).

Antes: «Mis posiciones» de Mercado (localStorage 'eco_pos'), las carteras de práctica ('kh_portfolios') y la cuenta del
bróker. Ahora lo que guarda el usuario vive SOLO en 'kh_portfolios' (engine/pfstore.js); MKT.pos es la VISTA de la
cartera ACTIVA y 'eco_pos' queda como copia escrita (nunca se vuelve a leer como fuente). La cuenta del bróker sigue
aparte (es la cuenta real).

Casos (node + vm, los archivos REALES del navegador):
  · solo eco_pos → «Mi cartera» (id fijo pf_main) ACTIVA, mismas acciones, P&L = valor − costo (caja 0);
  · eco_pos + carteras de práctica con una activa → se agrega «Mi cartera» y pasa a ser la activa; las otras intactas;
  · repetir es idempotente (con y sin la bandera); eco_pos ya igual a una cartera (otro dispositivo migró) → no duplica;
  · eco_pos vacío → no se crea nada; sin espacio → eco_pos intacto y se reintenta;
  · comprar/vender/borrar en Mercado (MKT.pos + savePos) escribe en la cartera ACTIVA; sin cartera se crea una;
  · cambiar la activa cambia MKT.pos, la copia eco_pos, KhipuHot.myPositions, el contexto del chat, el comité y el
    reporte de riesgo; nada se cuenta dos veces (el chat manda la activa con su nombre y de las otras SOLO nombres).
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
NODE = shutil.which('node')
pytestmark = pytest.mark.skipif(not NODE, reason='requiere node')

HARNESS = r"""
const fs = require('fs'), vm = require('vm');
const ROOT = process.argv[1];
const INIT = JSON.parse(process.argv[2] || '{}');
const store = Object.assign({}, INIT.store || {});
const events = [];
const ctx = { console, Date, Math, JSON, Promise, Number, String, Object, Array, isFinite, encodeURIComponent,
  setTimeout: (fn) => setTimeout(fn, 0), clearTimeout, setInterval: () => 0, clearInterval: () => {},
  localStorage: { getItem: k => (k in store ? store[k] : null),
                  setItem: (k, v) => { if (INIT.full && k === 'kh_portfolios') throw new Error('QuotaExceededError'); store[k] = String(v); },
                  removeItem: k => { delete store[k]; } },
  addEventListener: (t, fn) => { (ctx._ls[t] = ctx._ls[t] || []).push(fn); }, _ls: {},
  dispatchEvent: (e) => { events.push(e.type); (ctx._ls[e.type] || []).forEach(fn => fn(e)); },
  CustomEvent: function (type, o) { this.type = type; this.detail = (o || {}).detail; },
  LANG: 'es',
};
ctx.window = ctx; ctx.globalThis = ctx;
ctx.document = { createElement: () => ({}), getElementById: () => null, querySelectorAll: () => [], addEventListener: () => {} };
const NODES = [{ id: 'Nvidia', label: 'Nvidia', mkt: 'NVDA' }, { id: 'AMD', label: 'AMD', mkt: 'AMD' },
               { id: 'TSMC', label: 'TSMC', mkt: 'TSM' }, { id: 'OpenAI', label: 'OpenAI', mkt: null }];
ctx.NODES = NODES; ctx.NODE_BY_ID = {}; NODES.forEach(n => { ctx.NODE_BY_ID[n.id] = n; });
ctx.quotePx = q => (q ? (typeof q.live === 'number' ? q.live : q.close) || 0 : 0);
vm.createContext(ctx);
const load = f => vm.runInContext(fs.readFileSync(ROOT + '/' + f, 'utf8'), ctx, { filename: f });
const tick = () => new Promise(r => setTimeout(r, 5));
const out = {};
const S = () => ctx.KhipuPfStore;
const pfs = () => JSON.parse(store.kh_portfolios || '[]');
// lo mismo que hace app_main.js al definir MKT (después de pfstore.js) y savePos()
function boot() {
  load('engine/pfstore.js');
  ctx.MKT = { quotes: { NVDA: { close: 200, src: 'yahoo' }, AMD: { close: 100, src: 'yahoo' }, TSM: { close: 50, src: 'yahoo' } },
              pos: S().view() };
  ctx.savePos = () => S().applyView(ctx.MKT.pos);
}
"""


def _run(body, store=None, full=False):
    js = HARNESS + '(async () => {\n' + body + '\nprocess.stdout.write(JSON.stringify(out));\n})().catch(e => { process.stderr.write(String(e && e.stack || e)); process.exit(1); });'
    p = subprocess.run([NODE, '-e', js, ROOT, json.dumps({'store': store or {}, 'full': full})],
                       capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr[-3000:]
    return json.loads(p.stdout)


ECO = json.dumps({'Nvidia': {'sh': 10, 'bp': 100}, 'AMD': {'sh': 2.5, 'bp': 150}})
TECH = {'id': 'p1', 'name': 'Tecnología', 'cash': 5000, 'startCash': 10000, 'createdAt': 1,
        'positions': [{'nodeId': 'TSMC', 'shares': 100, 'avgPrice': 50, 'ts': 1}]}


def test_solo_eco_pos_pasa_a_mi_cartera_activa():
    o = _run("""
boot();
out.pfs = pfs(); out.active = store.kh_pf_active; out.flag = !!store.kh_pos_migrated;
out.view = ctx.MKT.pos; out.mirror = JSON.parse(store.eco_pos); out.name = S().name();
""", store={'eco_pos': ECO})
    assert len(o['pfs']) == 1
    pf = o['pfs'][0]
    assert pf['id'] == 'pf_main' and pf['name'] == 'Mi cartera' and o['active'] == 'pf_main' and o['flag']
    assert pf['cash'] == 0 and pf['startCash'] == pytest.approx(10 * 100 + 2.5 * 150)       # P&L = valor − costo
    assert {p['nodeId']: (p['shares'], p['avgPrice']) for p in pf['positions']} == {'Nvidia': (10, 100), 'AMD': (2.5, 150)}
    # Mercado y el chat siguen mostrando LO MISMO que antes; eco_pos queda como copia idéntica
    assert o['view'] == {'Nvidia': {'sh': 10, 'bp': 100}, 'AMD': {'sh': 2.5, 'bp': 150}} == o['mirror']
    assert o['name'] == 'Mi cartera'


def test_eco_pos_con_carteras_de_practica_se_suma_y_queda_activa():
    o = _run("""
boot();
out.pfs = pfs(); out.active = store.kh_pf_active; out.view = ctx.MKT.pos; out.others = S().others();
""", store={'eco_pos': ECO, 'kh_portfolios': json.dumps([TECH]), 'kh_pf_active': 'p1'})
    ids = [p['id'] for p in o['pfs']]
    assert ids == ['p1', 'pf_main'] and o['active'] == 'pf_main'
    assert o['pfs'][0] == TECH                                                # la de práctica, intacta
    assert set(o['view']) == {'Nvidia', 'AMD'} and o['others'] == ['Tecnología']


def test_repetir_no_duplica_ni_con_ni_sin_bandera():
    o = _run("""
boot(); const first = store.kh_portfolios;
boot(); out.same1 = store.kh_portfolios === first;                       // con bandera: no hace nada
delete store.kh_pos_migrated;                                            // bandera perdida: eco_pos = copia de pf_main
boot(); out.n = pfs().length; out.active = store.kh_pf_active; out.flag = !!store.kh_pos_migrated;
""", store={'eco_pos': ECO, 'kh_portfolios': json.dumps([TECH]), 'kh_pf_active': 'p1'})
    assert o['same1'] and o['n'] == 2 and o['active'] == 'pf_main' and o['flag']


def test_eco_pos_igual_a_una_cartera_sincronizada_no_duplica_y_la_activa():
    eco = json.dumps({'TSMC': {'sh': 100, 'bp': 50}})              # otro dispositivo ya migró: eco_pos = copia de p1
    other = dict(TECH, id='p2', name='Otra', positions=[])
    o = _run("""
boot(); out.pfs = pfs().map(p => p.id); out.active = store.kh_pf_active;
""", store={'eco_pos': eco, 'kh_portfolios': json.dumps([other, TECH]), 'kh_pf_active': 'p2'})
    assert o['pfs'] == ['p2', 'p1'] and o['active'] == 'p1'


def test_eco_pos_vacio_no_crea_nada_y_sin_espacio_no_pierde_nada():
    o = _run("""
boot(); out.pfs = store.kh_portfolios || null; out.flag = !!store.kh_pos_migrated; out.view = ctx.MKT.pos;
out.mirror = store.eco_pos;
""", store={'eco_pos': '{}'})
    assert o['pfs'] is None and o['flag'] and o['view'] == {} and o['mirror'] == '{}'
    o = _run("""
boot(); out.flag = !!store.kh_pos_migrated; out.eco = store.eco_pos; out.pfs = store.kh_portfolios || null;
""", store={'eco_pos': ECO}, full=True)
    assert not o['flag'] and o['eco'] == ECO and o['pfs'] is None                 # se reintenta la próxima carga


def test_sin_cartera_anotar_en_mercado_crea_mi_cartera():
    o = _run("""
boot();
ctx.MKT.pos.Nvidia = { sh: 4, bp: 150 }; ctx.savePos();
out.created = pfs().map(p => [p.id, p.name, p.cash, p.startCash]); out.active = store.kh_pf_active;
out.view = ctx.MKT.pos; out.mirror = JSON.parse(store.eco_pos);
await tick(); out.events = events.filter(e => e === 'khipu:portfolio').length;
""", store={'kh_portfolios': '[]'})
    assert o['created'] == [['pf_main', 'Mi cartera', 0, 600]] and o['active'] == 'pf_main'
    assert o['view'] == o['mirror'] == {'Nvidia': {'sh': 4, 'bp': 150}}
    assert o['events'] >= 1                                   # Mercado / la barra de saldo / Carteras se repintan


def test_mercado_escribe_en_la_cartera_de_practica_activa():
    o = _run("""
boot();
out.view_p1 = JSON.parse(JSON.stringify(ctx.MKT.pos));
ctx.MKT.pos.AMD = { sh: 10, bp: 100 }; ctx.savePos();
let p1 = pfs().find(p => p.id === 'p1');
out.after_add = { cash: p1.cash, start: p1.startCash, pos: p1.positions.map(p => [p.nodeId, p.shares, p.avgPrice]) };
ctx.MKT.pos.TSMC = { sh: 50, bp: 50 }; ctx.savePos();
delete ctx.MKT.pos.AMD; ctx.savePos();
p1 = pfs().find(p => p.id === 'p1');
out.after_edit = { cash: p1.cash, start: p1.startCash, pos: p1.positions.map(p => [p.nodeId, p.shares, p.avgPrice]) };
out.n = pfs().length; out.mirror = JSON.parse(store.eco_pos);
""", store={'kh_portfolios': json.dumps([TECH]), 'kh_pf_active': 'p1'})
    assert o['view_p1'] == {'TSMC': {'sh': 100, 'bp': 50}}
    # anotar en Mercado = «la tengo a este precio»: no gasta la caja, sube el capital inicial en lo que costó
    assert o['after_add'] == {'cash': 5000, 'start': 11000, 'pos': [['TSMC', 100, 50], ['AMD', 10, 100]]}
    assert o['after_edit'] == {'cash': 5000, 'start': 7500, 'pos': [['TSMC', 50, 50]]}   # 11000 − 2500 − 1000
    assert o['n'] == 1 and o['mirror'] == {'TSMC': {'sh': 50, 'bp': 50}}


def test_cambiar_la_activa_cambia_lo_que_ven_mercado_hot_chat_y_comite():
    main = {'id': 'pf_main', 'name': 'Mi cartera', 'cash': 0, 'startCash': 2000, 'createdAt': 2,
            'positions': [{'nodeId': 'Nvidia', 'shares': 10, 'avgPrice': 200}]}
    o = _run("""
boot();
load('engine/agents_registry.js'); load('engine/hotclient.js'); load('engine/khipu_chat.js'); load('engine/pfcommittee.js');
const snap = () => {
  const c = ctx.KhipuChat.context();
  return { mkt: Object.keys(ctx.MKT.pos), hot: ctx.KhipuHot.myPositions().positions.map(p => [p.symbol, p.usd]),
           pf: c.portfolio || null, others: c.other_portfolios || null, empty: c.portfolio_empty || null,
           srcs: ctx.KhipuPortfolioCommittee._sources().map(s => s.key), mirror: Object.keys(JSON.parse(store.eco_pos)) };
};
out.a = snap();
S().setActive('p1'); out.b = snap();
// la activa vacía: el chat la nombra, sin posiciones (nunca las de otra)
const l = pfs(); l.push({ id: 'p3', name: 'Vacía', cash: 1000, startCash: 1000, positions: [] }); S().save(l); S().setActive('p3');
out.c = snap();
""", store={'kh_portfolios': json.dumps([main, TECH]), 'kh_pf_active': 'pf_main', 'kh_pos_migrated': '1'})
    a, b, c = o['a'], o['b'], o['c']
    assert a['mkt'] == ['Nvidia'] and a['hot'] == [['NVDA', 2000]] and a['mirror'] == ['Nvidia']
    assert a['pf'] == {'positions': [{'symbol': 'NVDA', 'shares': 10, 'usd': 2000}], 'name': 'Mi cartera'}
    assert a['others'] == ['Tecnología'] and a['srcs'][0] == 'pf:pf_main' and 'market' not in a['srcs']
    assert b['mkt'] == ['TSMC'] and b['hot'] == [['TSM', 5000]] and b['mirror'] == ['TSMC']
    assert b['pf'] == {'positions': [{'symbol': 'TSM', 'shares': 100, 'usd': 5000}], 'name': 'Tecnología'}
    assert b['others'] == ['Mi cartera'] and b['srcs'][0] == 'pf:p1'
    assert c['pf'] is None and c['empty'] == 'Vacía' and c['mkt'] == [] and c['hot'] == []
    # ninguna posición aparece dos veces: el chat lleva la activa y de las otras SOLO nombres
    for s in (a, b):
        assert all(isinstance(x, str) for x in s['others'])


def test_reporte_de_riesgo_usa_la_activa_sin_lista_de_mercado_aparte():
    s = open(os.path.join(ROOT, 'engine', 'riskreport.js'), encoding='utf-8').read()
    assert "srcBtn('market'" not in s and "L('Mi portafolio (Mercado)'" not in s
    assert "function activeSrc()" in s and "src === 'market' ? (activeSrc()" in s
    html = open(os.path.join(ROOT, 'app.html'), encoding='utf-8').read()
    assert "source:'market'" not in html                                       # Mercado abre el riesgo de la activa


def test_carga_y_servicio_offline():
    html = open(os.path.join(ROOT, 'app.html'), encoding='utf-8').read()
    assert html.index('<script src="engine/pfstore.js"></script>') < html.index('<script src="engine/app_main.js"></script>')
    sw = open(os.path.join(ROOT, 'sw.js'), encoding='utf-8').read()
    assert "'/engine/pfstore.js'" in sw[sw.index('const SHELL'):sw.index('];', sw.index('const SHELL'))]
    # Mercado: «Mi cartera: <nombre>» + enlace a Carteras (sin botones nuevos), bilingüe
    assert 'id="mk-pf-name"' in html and 'id="mk-pf-switch"' in html and 'data-i18n="mk_pf_switch"' in html
    from tests._app_source import app_source
    src = app_source()
    assert "mk_fpos:'Mi cartera', mk_pf_switch:'Cambiar de cartera ›'" in src
    assert "mk_fpos:'My portfolio', mk_pf_switch:'Switch portfolio ›'" in src
    assert "localStorage.setItem('eco_pos'" not in src and "localStorage.getItem('eco_pos')" not in src
    # nadie más lee eco_pos como fuente en el navegador
    for f in os.listdir(os.path.join(ROOT, 'engine')):
        if f.endswith('.js') and f != 'pfstore.js':
            body = open(os.path.join(ROOT, 'engine', f), encoding='utf-8').read()
            assert "getItem('eco_pos')" not in body, f


def test_servidor_no_cuenta_dos_veces_la_copia():
    from core import prices_store as ps
    pf = [{'id': 'p1', 'positions': [{'nodeId': 'Nvidia', 'shares': 4}, {'nodeId': 'Nvidia', 'shares': 6}]}]
    assert ps._is_mirror({'Nvidia': {'sh': 10, 'bp': 1}}, pf)                  # copia de la activa → no se cuenta
    assert not ps._is_mirror({'Nvidia': {'sh': 9, 'bp': 1}}, pf)               # lista distinta (cliente viejo) → sí
    assert not ps._is_mirror({'AMD': {'sh': 10}}, pf) and not ps._is_mirror({}, pf) and not ps._is_mirror({'x': 1}, None)


SYNC_JS = r"""
const fs = require('fs'), vm = require('vm');
const ROOT = process.argv[1];
const store = { eco_pos: JSON.stringify({ Nvidia: { sh: 3, bp: 10 } }),
                kh_sync_meta: JSON.stringify({ kh_portfolios: '2026-10-01T00:00:00.000Z' }) };
const puts = [];
function Storage() {}
Storage.prototype.getItem = function (k) { return k in store ? store[k] : null; };
Storage.prototype.setItem = function (k, v) { store[k] = String(v); };
Storage.prototype.removeItem = function (k) { delete store[k]; };
const ctx = { console, Date, Math, JSON, Promise, Uint8Array, Storage, setInterval: () => 0, clearTimeout,
  setTimeout: (fn) => setTimeout(fn, 0), addEventListener: () => {}, dispatchEvent: () => {},
  CustomEvent: function (t) { this.type = t; }, LANG: 'es',
  fetch: (url, o) => { if (o && o.method === 'PUT') puts.push(JSON.parse(o.body).key);
    return Promise.resolve({ status: 200, json: () => Promise.resolve(o && o.method === 'PUT' ? { ok: true } : { available: true, state: {} }) }); } };
ctx.localStorage = new Storage(); ctx.window = ctx; ctx.globalThis = ctx;
ctx.document = { addEventListener: () => {}, hidden: false };
vm.createContext(ctx);
const load = f => vm.runInContext(fs.readFileSync(ROOT + '/' + f, 'utf8'), ctx, { filename: f });
load('engine/pfstore.js');            // como en app.html: ANTES que sync.js (la migración no marca la clave como nueva)
const metaBefore = JSON.parse(store.kh_sync_meta).kh_portfolios;
load('engine/sync.js');
setTimeout(() => {}, 0);
new Promise(r => setTimeout(r, 30)).then(() => new Promise(r => setTimeout(r, 1700))).then(() => {
  process.stdout.write(JSON.stringify({ metaBefore, metaAfter: JSON.parse(store.kh_sync_meta).kh_portfolios, puts,
    pfs: JSON.parse(store.kh_portfolios).map(p => p.id) }));
});
"""


def test_la_migracion_sube_al_servidor_despues_de_la_primera_sincronizacion():
    """La migración corre antes de sync.js (no pisa una lista más nueva del servidor); tras la primera bajada,
    afterSync vuelve a guardar la lista ya mezclada para que «Mi cartera» suba a los otros dispositivos."""
    p = subprocess.run([NODE, '-e', SYNC_JS, ROOT], capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr[-3000:]
    o = json.loads(p.stdout)
    assert o['pfs'] == ['pf_main'] and o['metaBefore'] == '2026-10-01T00:00:00.000Z'
    assert o['metaAfter'] > o['metaBefore'] and 'kh_portfolios' in o['puts']


# ── revisión 2026-10-15 b: lo que llega de OTRO dispositivo nunca se pierde ────────────────────────────────────────
SYNC2_JS = r"""
const fs = require('fs'), vm = require('vm');
const ROOT = process.argv[1];
const CASE = JSON.parse(process.argv[2]);
const store = Object.assign({}, CASE.local);
const srv = JSON.parse(JSON.stringify(CASE.server));
const timers = [];
function Storage() {}
Storage.prototype.getItem = function (k) { return k in store ? store[k] : null; };
Storage.prototype.setItem = function (k, v) { store[k] = String(v); };
Storage.prototype.removeItem = function (k) { delete store[k]; };
const ctx = { console, Date, Math, JSON, Promise, Number, String, Object, Array, isFinite, Uint8Array, Storage,
  setTimeout: (fn) => { timers.push(fn); return timers.length; }, clearTimeout: () => {}, setInterval: () => 0,
  addEventListener: () => {}, dispatchEvent: () => {}, CustomEvent: function (t) { this.type = t; }, LANG: 'es',
  crypto: { getRandomValues: a => a },
  fetch: (url, o) => {
    if (o.method === 'GET') return Promise.resolve({ status: 200, json: () => Promise.resolve({ available: true, state: JSON.parse(JSON.stringify(srv)) }) });
    const b = JSON.parse(o.body); srv[b.key] = { value: b.value, updated_at: b.updated_at };
    return Promise.resolve({ status: 200, json: () => Promise.resolve({ ok: true }) });
  } };
ctx.localStorage = new Storage(); ctx.window = ctx; ctx.globalThis = ctx;
ctx.document = { addEventListener: () => {}, hidden: false };
vm.createContext(ctx);
const load = f => vm.runInContext(fs.readFileSync(ROOT + '/' + f, 'utf8'), ctx, { filename: f });
const flush = async () => { for (let i = 0; i < 25; i++) { timers.splice(0).forEach(f => { try { f(); } catch (e) { console.error(e); } }); await new Promise(r => setImmediate(r)); } };
(async () => {
  load('engine/pfstore.js'); ctx.MKT = { pos: ctx.KhipuPfStore.view() };
  load('engine/sync.js');
  if (CASE.link) { await new Promise(r => setImmediate(r)); await ctx.KhipuSync.link(CASE.link); }
  await flush(); await flush();
  const view = pf => { const o = {}; (pf.positions || []).forEach(p => { o[p.nodeId] = (o[p.nodeId] || 0) + p.shares; }); return o; };
  const pfs = JSON.parse(store.kh_portfolios || '[]');
  process.stdout.write(JSON.stringify({ pfs: pfs.map(p => ({ id: p.id, v: view(p) })), active: store.kh_pf_active || null,
    mkt: Object.keys(ctx.MKT.pos), srv_pfs: ((srv.kh_portfolios || {}).value || []).map(p => ({ id: p.id, v: view(p) })),
    srv_eco: (srv.eco_pos || {}).value || null }));
})().catch(e => { process.stderr.write(String(e && e.stack || e)); process.exit(1); });
"""
T1, T2, T3 = '2026-10-15T10:00:00.000Z', '2026-10-15T12:00:00.000Z', '2026-10-15T13:00:00.000Z'
MAIN_NV = {'id': 'pf_main', 'name': 'Mi cartera', 'cash': 0, 'startCash': 1000, 'createdAt': 1,
           'origin': {'kind': 'eco_pos'}, 'positions': [{'nodeId': 'Nvidia', 'shares': 10, 'avgPrice': 100}]}


def _sync(case):
    p = subprocess.run([NODE, '-e', SYNC2_JS, ROOT, json.dumps(case)], capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr[-3000:]
    return json.loads(p.stdout)


def _all_shares(pfs):
    tot = {}
    for pf in pfs:
        for k, v in pf['v'].items():
            tot[k] = max(tot.get(k, 0), v)
    return tot


def test_eco_pos_de_una_pestana_vieja_se_adopta_en_mi_cartera():
    """Otro dispositivo con el código viejo agregó Intel a eco_pos: al bajar, Intel queda en «Mi cartera» (aquí y en
    el servidor), sin duplicar Nvidia; antes la copia de la activa lo pisaba."""
    o = _sync({'local': {'kh_owner_key': 'a' * 32, 'kh_pos_migrated': T1, 'kh_portfolios': json.dumps([MAIN_NV]),
                         'kh_pf_active': 'pf_main', 'eco_pos': json.dumps({'Nvidia': {'sh': 10, 'bp': 100}}),
                         'kh_sync_meta': json.dumps({'kh_portfolios': T1, 'kh_pf_active': T1, 'eco_pos': T1})},
               'server': {'eco_pos': {'value': {'Nvidia': {'sh': 10, 'bp': 100}, 'Intel': {'sh': 7, 'bp': 30}}, 'updated_at': T2},
                          'kh_portfolios': {'value': [MAIN_NV], 'updated_at': T1}}})
    assert o['pfs'] == [{'id': 'pf_main', 'v': {'Nvidia': 10, 'Intel': 7}}]
    assert o['srv_pfs'] == o['pfs'] and set(o['mkt']) == {'Nvidia', 'Intel'} and 'Intel' in o['srv_eco']


def test_vincular_un_navegador_nuevo_no_borra_el_eco_pos_del_servidor():
    o = _sync({'local': {}, 'link': 'b' * 32,
               'server': {'eco_pos': {'value': {'Nvidia': {'sh': 10, 'bp': 100}}, 'updated_at': T1}}})
    assert o['pfs'] == [{'id': 'pf_main', 'v': {'Nvidia': 10}}] and o['active'] == 'pf_main'
    assert o['srv_eco'] == {'Nvidia': {'sh': 10, 'bp': 100}} and o['srv_pfs'] == o['pfs']


def test_mi_cartera_migrada_que_choca_por_id_vuelve_con_otro_id():
    """A tenía un cambio sin conexión (AMD:3) y B ya subió su «Mi cartera» (pf_main, Nvidia:10): A no pierde AMD."""
    o = _sync({'local': {'kh_owner_key': 'a' * 32, 'eco_pos': json.dumps({'AMD': {'sh': 3, 'bp': 100}}),
                         'kh_sync_meta': json.dumps({'eco_pos': T3})},
               'server': {'kh_portfolios': {'value': [dict(MAIN_NV, createdAt=1760529600000)], 'updated_at': T2},
                          'kh_pf_active': {'value': 'pf_main', 'updated_at': T2},
                          'eco_pos': {'value': {'Nvidia': {'sh': 10, 'bp': 100}}, 'updated_at': T2}}})
    views = [p['v'] for p in o['pfs']]
    assert {'Nvidia': 10} in views and {'AMD': 3} in views and len(views) == 2
    rescued = next(p for p in o['pfs'] if p['v'] == {'AMD': 3})
    assert rescued['id'] != 'pf_main' and o['active'] == rescued['id'] and o['mkt'] == ['AMD']
    assert sorted(map(str, (p['v'] for p in o['srv_pfs']))) == sorted(map(str, views))   # y sube


def test_copia_atrasada_de_la_activa_no_se_adopta():
    """Una copia eco_pos que este navegador ya vio (versión anterior de la activa) llega tarde: no crea nada."""
    pf = dict(MAIN_NV, positions=[{'nodeId': 'Nvidia', 'shares': 12, 'avgPrice': 100}])
    o = _sync({'local': {'kh_owner_key': 'a' * 32, 'kh_pos_migrated': T1, 'kh_portfolios': json.dumps([pf]),
                         'kh_pf_active': 'pf_main', 'eco_pos': json.dumps({'Nvidia': {'sh': 12, 'bp': 100}}),
                         'kh_pos_seen': json.dumps(['Nvidia:10.0000@100.000', 'Nvidia:12.0000@100.000']),
                         'kh_sync_meta': json.dumps({'kh_portfolios': T2, 'kh_pf_active': T2, 'eco_pos': T1})},
               'server': {'eco_pos': {'value': {'Nvidia': {'sh': 10, 'bp': 100}}, 'updated_at': T2},
                          'kh_portfolios': {'value': [pf], 'updated_at': T1}}})
    assert o['pfs'] == [{'id': 'pf_main', 'v': {'Nvidia': 12}}]


def test_chat_no_dice_vacia_si_solo_tiene_privadas():
    priv = {'id': 'p9', 'name': 'Privadas', 'cash': 0, 'startCash': 100, 'createdAt': 3,
            'positions': [{'nodeId': 'OpenAI', 'shares': 1, 'avgPrice': 100}]}
    o = _run("""
boot();
load('engine/agents_registry.js'); load('engine/hotclient.js'); load('engine/khipu_chat.js');
const c = ctx.KhipuChat.context();
out.c = { pf: c.portfolio || null, empty: c.portfolio_empty || null, unl: c.portfolio_unlisted || null };
""", store={'kh_portfolios': json.dumps([priv]), 'kh_pf_active': 'p9', 'kh_pos_migrated': '1'})
    assert o['c'] == {'pf': None, 'empty': None, 'unl': {'name': 'Privadas', 'n': 1}}
    from core import khipu_chat as K
    r = K.validate_request({'message': '¿qué tengo?', 'lang': 'es', 'context': {'portfolio_unlisted': {'name': 'Privadas', 'n': 1}}})
    c = r['context']
    assert c['portfolio_unlisted'] == 1 and c['portfolio_name'] == 'Privadas' and 'portfolio_empty' not in c
    p = K.build_prompt('¿qué tengo?', [], 'es', c, [], 2, False)
    assert '«Privadas»' in p and 'NO cotizadas' in p and 'VACÍA' not in p and 'REGLA DE CARTERAS' in p
