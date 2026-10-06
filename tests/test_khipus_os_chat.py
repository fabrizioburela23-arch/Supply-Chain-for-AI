"""tests/test_khipus_os_chat.py — Khipus OS (2026-10-06, docs/KHIPUS_OS.md §3.2/§3.5): el chat
con agentes en el cliente (engine/khipu_chat.js, engine/pickers.js, engine/sync.js).

Corre el JS REAL en node (vm) con un DOM falso mínimo:
  · predictAgents — quién va a investigar según la pregunta (y las preferencias)
  · TOOL_AGENT    — herramienta → mascota, IGUAL al del servidor
  · planWindows   — qué ventanas nativas se abren solas (y que el X-Ray queda como botón)
  · replyHTML     — la tarjeta "lo que aportó cada agente" (agents_used / tools_used), fuentes con hora
  · send + appendPending — req_id en el pedido, mode/agents_enabled en el contexto y el progreso
    en vivo reemplaza la predicción; servidor viejo (404) → deja de preguntar
  · pickers       — @analista/@radar con mascota; al enviar se escriben como el puesto del servidor
"""
import json
import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = shutil.which('node')
pytestmark = pytest.mark.skipif(not NODE, reason='requiere node')

# DOM falso: lo justo para appendPending/_paintThinking/fillReply. querySelector('.x') devuelve un hijo
# agregado con appendChild o, si el innerHTML trae class="… x …", un nodo stub estable para esa clase.
HARNESS = r"""
const fs = require('fs'), vm = require('vm');
const ROOT = process.argv[1];
function ClassList(el) { this.el = el; }
ClassList.prototype._get = function () { return (this.el._cls || '').split(/\s+/).filter(Boolean); };
ClassList.prototype.add = function (c) { const a = this._get(); if (a.indexOf(c) < 0) a.push(c); this.el._cls = a.join(' '); };
ClassList.prototype.remove = function (c) { this.el._cls = this._get().filter(x => x !== c).join(' '); };
ClassList.prototype.contains = function (c) { return this._get().indexOf(c) >= 0; };
ClassList.prototype.toggle = function (c, on) { if (on === undefined) on = !this.contains(c); if (on) this.add(c); else this.remove(c); return on; };
class El {
  constructor(tag) { this.tagName = String(tag || 'div').toUpperCase(); this.children = []; this.parentNode = null; this._cls = '';
    this._html = ''; this._text = ''; this._stubs = {}; this.attrs = {}; this.listeners = {}; this.style = {}; this.classList = new ClassList(this); }
  get className() { return this._cls; } set className(v) { this._cls = String(v); }
  get parentElement() { return this.parentNode; }
  get innerHTML() { return this._html + this.children.map(c => c.outer()).join(''); }
  set innerHTML(v) { this._html = String(v); this.children.forEach(c => { c.parentNode = null; }); this.children = []; this._stubs = {}; }
  get textContent() { return this._text || this._html.replace(/<[^>]+>/g, ''); } set textContent(v) { this._text = String(v); this._html = ''; this.children = []; }
  outer() { return '<' + this.tagName.toLowerCase() + ' class="' + this._cls + '">' + (this._text || this.innerHTML) + '</' + this.tagName.toLowerCase() + '>'; }
  appendChild(c) { if (c.parentNode) c.parentNode.removeChild(c); c.parentNode = this; this.children.push(c); return c; }
  insertBefore(c, ref) { if (c.parentNode) c.parentNode.removeChild(c); c.parentNode = this; const i = ref ? this.children.indexOf(ref) : -1;
    if (i < 0) this.children.push(c); else this.children.splice(i, 0, c); return c; }
  removeChild(c) { const i = this.children.indexOf(c); if (i >= 0) this.children.splice(i, 1); c.parentNode = null; return c; }
  setAttribute(k, v) { this.attrs[k] = String(v); } getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  addEventListener(t, fn) { (this.listeners[t] = this.listeners[t] || []).push(fn); }
  click() { (this.listeners.click || []).forEach(fn => fn({})); }
  scrollIntoView() {}
  querySelector(sel) {
    const cls = sel.replace(/^\./, '');
    const walk = (n) => { for (const c of n.children) { if (c.classList.contains(cls)) return c; const r = walk(c); if (r) return r; } return null; };
    const hit = walk(this); if (hit) return hit;
    if (this._stubs[cls]) return this._stubs[cls];
    for (const k in this._stubs) { const r = this._stubs[k].querySelector(sel); if (r) return r; }
    if (new RegExp('class="[^"]*\\b' + cls + '\\b').test(this._html)) {
      const s = new El('div'); s.className = cls; s.parentNode = this; this._stubs[cls] = s; return s;
    }
    return null;
  }
  querySelectorAll() { return []; }
}
const store = {};
const timers = [];
const ctx = { console, Date, Math, JSON, Promise, Uint8Array, encodeURIComponent,
  setTimeout: (fn, ms) => setTimeout(fn, Math.min(ms || 0, 5)), clearTimeout,
  setInterval: () => 0, clearInterval: () => {},
  localStorage: { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; } },
  getComputedStyle: () => ({ overflowY: 'visible' }),
};
ctx.window = ctx; ctx.globalThis = ctx;
ctx.document = { createElement: t => new El(t), createTextNode: t => { const e = new El('#text'); e._text = String(t); return e; },
  getElementById: () => null, head: new El('head'), querySelectorAll: () => [] };
const snap = JSON.parse(fs.readFileSync(ROOT + '/data/grafo_v0.json', 'utf8'));
ctx.NODE_BY_ID = {}; snap.nodes.forEach(n => { ctx.NODE_BY_ID[n.id] = n; });
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(ROOT + '/engine/khipu_chat.js', 'utf8'), ctx);
const K = ctx.KhipuChat;
const out = {};
"""


def _run(body, *args, timeout=60):
    js = HARNESS + body
    p = subprocess.run([NODE, '-e', js, ROOT, *args], capture_output=True, text=True, timeout=timeout)
    assert p.returncode == 0, p.stderr[-3000:]
    return json.loads(p.stdout.strip().splitlines()[-1])


# ── herramienta → mascota: el contrato §3.2 (y el mismo mapa que el servidor) ──
SPEC_TOOL_AGENT = {
    'get_company': 'analista', 'search_companies': 'analista', 'get_research': 'analista', 'get_claim_evidence': 'analista',
    'get_supply_chain': 'cadena', 'rank_companies': 'cadena',
    'get_news': 'radar', 'get_world_events': 'radar', 'web_search': 'radar', 'scenario_exposure': 'radar',
    'market_movers': 'tecnico', 'get_option_greeks': 'tecnico', 'get_risk_report': 'tecnico',
    'get_committee_memo': 'comite', 'get_conclusions_board': 'comite', 'get_track_record': 'comite',
}


def test_tool_agent_igual_al_contrato_y_al_servidor():
    o = _run(r"""
out.map = K.TOOL_AGENT;
out.ask = [K.toolAgent('ask_agent', 'fundamental, ¿cómo va?, Nvidia'), K.toolAgent('ask_agent', {seat: 'technical'}),
           K.toolAgent('ask_agent', 'news'), K.toolAgent('ask_agent', 'supply_chain'), K.toolAgent('ask_agent', 'all'),
           K.toolAgent('ask_agent', ''), K.toolAgent('get_space_summary'), K.toolAgent('get_research_health')];
console.log(JSON.stringify(out));
""")
    assert o['map'] == SPEC_TOOL_AGENT
    assert o['ask'] == ['analista', 'tecnico', 'radar', 'cadena', 'comite', 'analista', 'khipu', 'khipu']
    from core import khipu_chat as kc
    srv = getattr(kc, 'TOOL_AGENT', None)
    if srv is not None:          # el servidor de Khipus OS ya está integrado → deben ser idénticos
        assert dict(srv) == SPEC_TOOL_AGENT


# ── predicción de quién investiga ──
def test_predict_agents_por_intencion_y_preferencias():
    o = _run(r"""
const P = (t, o) => K.predictAgents(t, o);
out.nv = P('¿Cómo está Nvidia y cuál es su mayor riesgo?');
out.dep = P('¿De quién depende TSMC?');
out.px = P('¿Cómo va NVDA hoy, sube el precio?');
out.com = P('¿Qué opina el comité de Meta?');
out.vale = P('¿Vale la pena invertir en memoria?');          // "Vale" es una palabra, no la minera
out.meta = P('¿Cuál es la meta de la Fed?');                  // "meta" en minúscula: palabra
out.hbm = P('explícame qué es el HBM');                       // HBM: sigla, no el ticker de Hudbay
out.hola = P('hola');
out.war = P('What if China invades Taiwan?');
out.supp = P('Who are Nvidia suppliers?');
out.ment = P('@fundamental ¿cómo va AMD?');
out.ment2 = P('/cartera @geo ¿qué riesgos tengo?');
out.pf = P('/cartera ¿cuánto gané?');
out.rs = P('/investigar NVDA');
out.off = P('¿Cómo está Nvidia y cuál es su mayor riesgo?', { enabled: ['khipu', 'analista'] });
out.offAll = P('¿Cómo está Nvidia?', { enabled: ['khipu'] });
out.forced = P('¿y su mayor riesgo?', { hasCompany: true });
console.log(JSON.stringify(out));
""")
    assert o['nv'] == ['analista', 'radar']
    assert o['dep'] == ['analista', 'cadena']
    assert o['px'] == ['analista', 'tecnico']
    assert o['com'] == ['analista', 'comite']
    assert o['vale'] == ['comite']
    assert o['meta'] == ['khipu'] and o['hbm'] == ['khipu'] and o['hola'] == ['khipu']
    assert o['war'] == ['radar']
    assert o['supp'] == ['analista', 'cadena']
    assert o['ment'] == ['analista'] and o['ment2'] == ['radar'] and o['pf'] == ['khipu']
    assert o['rs'] == ['analista', 'radar', 'cadena', 'tecnico']
    assert o['off'] == ['analista']                 # Radar apagado por el usuario
    assert o['offAll'] == ['khipu']
    assert o['forced'] == ['analista', 'radar']


def test_texto_de_pensando_bilingue():
    o = _run(r"""
const W = s => ({ id: s, state: 'working' }), D = s => ({ id: s, state: 'done' });
out.es = [K.thinkingText([W('analista'), W('cadena'), W('comite')]), K.thinkingText([W('radar')]),
          K.thinkingText([W('khipu')]), K.thinkingText([D('analista'), D('cadena')]), K.thinkingText([D('analista'), W('cadena')])];
ctx.LANG = 'en';
out.en = [K.thinkingText([W('analista'), W('cadena'), W('comite')]), K.thinkingText([W('radar')]),
          K.thinkingText([W('khipu')]), K.thinkingText([D('analista')])];
out.prog = K.progressAgents({ agents: [{ agent: 'comite', tool: 'get_committee_memo', state: 'working' },
  { agent: 'analista', tool: 'get_company', state: 'done' }, { agent: 'analista', tool: 'get_research', state: 'working' },
  { agent: 'cadena', tool: 'get_supply_chain', state: 'error' }, { agent: 'zzz', tool: 'x', state: 'working' }] });
console.log(JSON.stringify(out));
""")
    assert o['es'] == ['Analista, Cadena y Comité están investigando…', 'Radar está investigando…', 'Khipu está pensando…',
                       'Khipu está redactando la respuesta…', 'Cadena está investigando…']
    assert o['en'] == ['Analyst, Chain and Committee are researching…', 'Radar is researching…', 'Khipu is thinking…',
                       'Khipu is writing the answer…']
    assert o['prog'] == [{'id': 'analista', 'state': 'working'}, {'id': 'cadena', 'state': 'error'}, {'id': 'comite', 'state': 'working'}]


# ── ventanas automáticas (§3.5) ──
def test_plan_windows():
    o = _run(r"""
const full = { entities: [{ id: 'Nvidia', label: 'Nvidia' }], agents_used: [{ agent: 'analista' }, { agent: 'cadena' }],
               cards: { committee: { decision: 'buy' } } };
const all = { auto: () => true };
out.full = K.planWindows(full, '¿Cómo está Nvidia?', all, true);
out.notCentered = K.planWindows(full, '¿Cómo está Nvidia?', all, false);
out.noEnt = K.planWindows({ agents_used: [{ agent: 'analista' }] }, 'hola', all, true);
out.onlyGlance = K.planWindows({ entities: [{ id: 'Nvidia' }], agents_used: [{ agent: 'analista' }] }, '¿Cómo está Nvidia?', all, true);
out.riskQ = K.planWindows({ entities: [{ id: 'Nvidia' }], agents_used: [{ agent: 'analista' }] }, '¿y su mayor riesgo?', all, true);
out.fromTools = K.planWindows({ entities: [{ id: 'TSMC' }], tools_used: [{ name: 'get_company' }, { name: 'get_committee_memo' }] }, '¿qué tal?', all, true);
out.prefsObj = K.planWindows(full, '¿Cómo está Nvidia?', { agents: { analista: { on: true, auto: false }, cadena: { on: false, auto: true }, comite: { on: true, auto: true } } }, true);
out.defaults = K.planWindows(full, '¿Cómo está Nvidia?', null, true);
console.log(JSON.stringify(out));
""")
    assert o['full'] == [{'kind': 'glance', 'arg': {'id': 'Nvidia'}, 'agent': 'analista'},
                         {'kind': 'supplychain', 'arg': {'id': 'Nvidia'}, 'agent': 'cadena'},
                         {'kind': 'conviction', 'arg': {'id': 'Nvidia'}, 'agent': 'comite'}]
    assert o['notCentered'] == [] and o['noEnt'] == []
    assert [w['kind'] for w in o['onlyGlance']] == ['glance']
    assert [w['kind'] for w in o['riskQ']] == ['glance', 'supplychain']       # la pregunta habla de riesgo
    assert [w['kind'] for w in o['fromTools']] == ['glance', 'conviction']    # servidor viejo: deriva de tools_used
    assert [w['kind'] for w in o['prefsObj']] == ['conviction']               # analista sin auto, cadena apagada
    assert [w['kind'] for w in o['defaults']] == ['glance', 'supplychain', 'conviction']


# ── la respuesta: lo que aportó cada agente + fuentes con hora ──
def test_reply_html_agents_used_fuentes_y_escape():
    o = _run(r"""
const now = Date.now();
const d = { answer: 'Tus agentes le dan **+42** <img src=x onerror=alert(1)>', ai: true, model: 'claude-haiku-4-5', steps: 2, elapsed_ms: 8000,
  agents_used: [
    { agent: 'khipu', tools: [], ok: true, note_es: 'orquesta', note_en: 'orchestrates' },
    { agent: 'analista', tools: ['get_company'], ok: true, note_es: 'Precio $182,40 <b>vivo</b>', note_en: 'Price $182.40 live', source: 'Finnhub', as_of: new Date(now - 180000).toISOString() },
    { agent: 'cadena', tools: ['get_supply_chain', 'rank_companies'], ok: true, note_es: 'Consultó get_supply_chain, rank_companies', note_en: 'Checked get_supply_chain, rank_companies' },
    { agent: 'comite', tools: ['get_committee_memo'], ok: false, note_es: 'No pudo obtener los datos ahora', note_en: 'Could not get the data right now' },
  ],
  sources: [{ label: 'Finnhub (en vivo)', url: 'https://finnhub.io/x', tool: 'get_company', as_of: new Date(now - 180000).toISOString() },
            { label: 'Catálogo Khipus', url: null, tool: 'get_company', as_of: '2026-09-29' },
            { label: 'Malo', url: 'javascript:alert(1)', tool: 'web_search' }] };
ctx.KhipuAgentPrefs = { mode: () => 'simple', enabled: () => [], auto: () => false };
out.simple = K.replyHTML(d, {});
ctx.KhipuAgentPrefs.mode = () => 'pro';
out.es = K.replyHTML(d, {});
out.rows = K.contribRows(d).map(r => r.id);
ctx.LANG = 'en';
out.en = K.replyHTML(d, {});
ctx.LANG = 'es';
// servidor viejo: sin agents_used → derivado de tools_used, con las consultas como detalle
out.old = K.replyHTML({ answer: 'ok', tools_used: [{ name: 'get_company', args_summary: 'Nvidia', ok: true },
  { name: 'get_news', args_summary: 'Nvidia', ok: true }, { name: 'get_supply_chain', args_summary: 'Nvidia', ok: false, error: 'timeout' }] }, {});
out.oldRows = K.contribRows({ tools_used: [{ name: 'get_company', ok: true }, { name: 'get_news', ok: true }, { name: 'get_supply_chain', ok: false }] }).map(r => r.id);
// respondió un analista en persona: su mascota, su nombre; sin tarjeta repetida
out.agent = K.replyHTML({ answer: 'Hola', agent: { seat: 'fundamental', name: 'Analista fundamental', emoji: '📊', label: 'Nvidia' },
  tools_used: [{ name: 'ask_agent', args_summary: 'fundamental', ok: true }] }, {});
out.degraded = K.replyHTML({ answer: 'datos', degraded: 'no_ai', ai_detail_es: 'sin saldo' }, { retry: true });
console.log(JSON.stringify(out));
""")
    es, en = o['es'], o['en']
    assert o['rows'] == ['analista', 'cadena', 'comite']            # Khipu no se lista si aportaron otros
    assert 'kc-contrib' in es and '<b>Analista</b>' in es and '<b>Cadena</b>' in es and '<b>Comité</b>' in es
    assert '<b>Khipu</b>' not in es
    assert 'Precio $182,40 &lt;b&gt;vivo&lt;/b&gt;' in es           # la nota se escapa
    assert '<img' not in es and '&lt;img' in es and '<b>+42</b>' in es
    # la nota genérica del servidor ("Consultó get_supply_chain, …") se muestra con nombres legibles
    assert '<b>Cadena</b>Cadena de suministro, Ranking del grafo' in es and 'Consultó get_supply_chain' not in es
    assert 'No pudo obtener los datos ahora' in es and 'kc-ag off' in es
    assert 'class="kc-mf"' in es and 'class="kc-av"' in es           # sin engine/mascot.js: burbuja de respaldo, nunca un hueco
    # fuentes con su hora (as_of) y enlaces seguros
    assert 'data-asof=' in es and 'hace 3 min' in es and '29 sept' in es
    assert 'href="https://finnhub.io/x"' in es and 'href="javascript' not in es and 'Malo' in es
    assert 'Claude haiku-4-5' in es and '2 consultas' in es and '8 s' in es
    # modo Pro: fuente y hora del dato junto a la nota del agente
    assert 'Finnhub, hace 3 min' in es
    assert 'Finnhub, hace 3 min' not in o['simple'] and 'kc-agt' not in o['simple']   # Simple: la hora va en la fuente y el tooltip
    # inglés
    assert '<b>Analyst</b>' in en and '<b>Chain</b>' in en and '<b>Committee</b>' in en
    assert 'Price $182.40 live' in en and 'Sources' in en and '3 min ago' in en and 'Sep 29' in en
    # servidor viejo
    assert o['oldRows'] == ['analista', 'radar', 'cadena']
    old = o['old']
    assert 'Ficha de empresa (Nvidia)' in old and 'Noticias (Nvidia)' in old and '✕' in old
    # analista en persona
    ag = o['agent']
    assert 'Analista fundamental' in ag and 'kc-agent-ent' in ag and 'kc-contrib' not in ag
    # respuesta degradada: nota + reintentar (lo que ya existía sigue igual)
    assert 'Respuesta sin IA (solo datos).' in o['degraded'] and 'kc-retry' in o['degraded'] and 'sin saldo' in o['degraded']


def test_rel_time():
    o = _run(r"""
const now = Date.parse('2026-10-06T15:00:00');
out.es = [K.relTime(new Date(now - 20000).toISOString(), now), K.relTime(new Date(now - 600000).toISOString(), now),
          K.relTime('2026-10-06T09:05:00', now), K.relTime('2026-09-29', now), K.relTime('2025-12-01', now), K.relTime('basura', now), K.relTime(null, now)];
ctx.LANG = 'en';
out.en = [K.relTime(new Date(now - 20000).toISOString(), now), K.relTime(new Date(now - 600000).toISOString(), now), K.relTime('2026-09-29', now)];
console.log(JSON.stringify(out));
""")
    assert o['es'] == ['ahora', 'hace 10 min', '09:05', '29 sept', '1 dic 2025', '', '']
    assert o['en'] == ['just now', '10 min ago', 'Sep 29']


# ── flujo completo: pensando → progreso real → respuesta → ventanas (con fetch y Cabina falsos) ──
FLOW = r"""
const scenario = process.argv[2];
const calls = [], staged = [], ran = [];
let chatBody = null, progressHits = 0;
ctx.LANG = 'es';
ctx.KhipuAgentPrefs = { mode: () => 'pro', enabled: () => ['khipu', 'analista', 'radar', 'cadena', 'comite'], auto: () => true, get: () => ({}) };
ctx.KhipuOSWin = { kinds: { glance: {}, supplychain: {}, conviction: {}, agents: {} } };
ctx.BixbyCockpit = { isOpen: () => true, isCentered: () => scenario !== 'narrow', stage: (k, a) => staged.push([k, a]) };
let release;
const chatReply = new Promise(r => { release = r; });
ctx.fetch = (url, opts) => {
  calls.push(url);
  if (url.indexOf('/api/khipu/chat/progress/') >= 0) {
    progressHits++;
    if (scenario === 'old') return Promise.resolve({ status: 404, ok: false, headers: { get: () => 'text/html' }, json: () => Promise.resolve({}) });
    const p = { req_id: url.split('/').pop(), done: false, agents: [
      { agent: 'analista', tool: 'get_company', state: 'done' },
      { agent: 'cadena', tool: 'get_supply_chain', state: 'working' },
      { agent: 'comite', tool: 'get_committee_memo', state: 'working' }] };
    return Promise.resolve({ status: 200, ok: true, headers: { get: () => 'application/json' }, json: () => Promise.resolve(p) });
  }
  chatBody = JSON.parse(opts.body);
  return chatReply.then(d => ({ status: 200, ok: true, headers: { get: () => 'application/json' }, json: () => Promise.resolve(d) }));
};
const thread = new El('div');
const q = '¿Cómo está Nvidia y cuál es su mayor riesgo?';
K.appendUser(thread, q, null);
const pend = K.appendPending(thread);
const tm = pend.querySelector('.kc-tm'), tt = pend.querySelector('.kc-tt');
out.predicted = { ags: tm.children.map(c => c.getAttribute('data-ag')), text: tt.textContent };
const sent = K.send(q);
const wait = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  await wait(120);
  out.live = { ags: tm.children.map(c => c.getAttribute('data-ag') + ':' + c.getAttribute('data-st') + (c.classList.contains('kc-done') ? ':done' : '')),
               text: tt.textContent, hits: progressHits };
  release({ answer: 'Tus agentes le dan +42.', ai: true, model: 'claude-haiku-4-5', steps: 2, elapsed_ms: 9000,
    entities: [{ id: 'Nvidia', label: 'Nvidia' }], cards: { committee: { decision: 'buy' } },
    agents_used: [{ agent: 'analista', tools: ['get_company'], ok: true, note_es: 'Precio en vivo' },
                  { agent: 'cadena', tools: ['get_supply_chain'], ok: true, note_es: 'TSMC y SK Hynix no tienen reemplazo hoy.' },
                  { agent: 'comite', tools: ['get_committee_memo'], ok: true, note_es: 'Propone comprar. Espera tu revisión.' }],
    actions: [{ type: 'open_xray', arg: 'Nvidia', label: 'Nvidia' }], tools_used: [], sources: [] });
  const d = await sent;
  K.fillReply(pend, d, { onAction: a => ran.push(a.type), autoRun: scenario !== 'mobile', retry: true });
  const hitsAtReply = progressHits;
  await wait(150);
  out.body = { req_id: chatBody.req_id, mode: chatBody.context.mode, agents_enabled: chatBody.context.agents_enabled, message: chatBody.message };
  out.progressUrlId = (calls.filter(u => u.indexOf('/progress/') >= 0)[0] || '').split('/').pop();
  out.staged = staged; out.ran = ran; out.pending = pend.classList.contains('kc-pending');
  out.html = pend.innerHTML; out.hitsAfter = progressHits - hitsAtReply; out.totalHits = progressHits;
  out.acts = (pend.querySelector('.kc-main') || pend).children.map(c => c.className);
  console.log(JSON.stringify(out));
})();
"""


def test_flujo_pensando_progreso_respuesta_y_ventanas():
    o = _run(FLOW, 'wide')
    assert o['predicted']['ags'] == ['analista', 'radar']
    assert o['predicted']['text'] == 'Analista y Radar están investigando…'
    # el progreso REAL reemplaza la predicción: Analista ya terminó, Cadena y Comité trabajan
    assert o['live']['ags'] == ['analista:done:done', 'cadena:working', 'comite:working']
    assert o['live']['text'] == 'Cadena y Comité están investigando…'
    assert o['live']['hits'] >= 1
    # el pedido lleva req_id (el mismo que se consulta), modo y agentes
    assert o['body']['req_id'].startswith('kc') and len(o['body']['req_id']) == 34
    assert o['progressUrlId'] == o['body']['req_id']
    assert o['body']['mode'] == 'pro' and o['body']['agents_enabled'] == ['khipu', 'analista', 'radar', 'cadena', 'comite']
    # respuesta: ya no está pendiente, deja de preguntar el progreso y abre las 3 ventanas de los agentes
    assert o['pending'] is False and o['hitsAfter'] <= 1
    assert [s[0] for s in o['staged']] == ['glance', 'supplychain', 'conviction']
    assert all(s[1] == {'id': 'Nvidia'} for s in o['staged'])
    assert o['ran'] == []                                   # el X-Ray NO se auto-abre: queda como botón
    assert 'kc-acts' in o['acts']
    assert 'TSMC y SK Hynix no tienen reemplazo hoy.' in o['html'] and '<b>Comité</b>' in o['html']


def test_sin_flancos_se_mantiene_el_auto_xray():
    o = _run(FLOW, 'narrow')
    assert o['staged'] == [] and o['ran'] == ['open_xray']


def test_movil_sin_auto_nada():
    o = _run(FLOW, 'mobile')
    assert o['staged'] == [] and o['ran'] == []


def test_servidor_viejo_sin_progreso_no_rompe():
    o = _run(FLOW, 'old')
    assert o['live']['ags'] == ['analista', 'radar'] or o['live']['ags'] == ['analista:working', 'radar:working']
    assert o['live']['text'] == 'Analista y Radar están investigando…'
    assert o['totalHits'] <= 8                              # 404 seguidos → deja de preguntar
    assert [s[0] for s in o['staged']] == ['glance', 'supplychain', 'conviction']


# ── pickers: @analista / @radar con mascota; al enviar, el puesto que entiende el servidor ──
PICK = r"""
const fs = require('fs');
const L = {};
global.window = { LANG: 'es', addEventListener: () => {}, KhipuMascot: { svg: (id, s) => '<span class="km" data-m="' + id + '"></span>' } };
global.document = { addEventListener: () => {}, getElementById: () => null };
global.localStorage = { getItem: () => null };
global.setInterval = () => 0;
require(process.argv[1] + '/engine/pickers.js');
const P = window.KhipuPick;
function fakeInput(v) {
  const ls = {};
  return { value: v, selectionStart: v.length, dataset: {}, classList: { add() {}, remove() {}, toggle() {} },
    setAttribute() {}, addEventListener(t, fn) { (ls[t] = ls[t] || []).push(fn); }, dispatchEvent() {}, focus() {},
    parentNode: { querySelector: () => null, insertBefore() {} }, _ls: ls };
}
const enter = inp => (inp._ls.keydown || []).forEach(fn => fn({ key: 'Enter', preventDefault() {}, stopImmediatePropagation() {} }));
const out = {};
const a = fakeInput('@analista ¿cómo va Nvidia?'); P.chatMenu(a); enter(a); out.typed = a.value;
const b = fakeInput('¿qué pasa con TSMC?'); P.chatMenu(b); b._agentTok = '@radar'; enter(b); out.chip = b.value;
const c = fakeInput('@cadena ¿de quién depende AMD?'); P.chatMenu(c); enter(c); out.same = c.value;
const d = fakeInput('mis riesgos'); P.chatMenu(d); d._agentTok = '@analyst'; d._ctxPf = 'market'; enter(d); out.pf = d.value;
out.canon = [P.canonical('@analista'), P.canonical('@Analyst'), P.canonical('@radar'), P.canonical('@tecnico'), P.canonical('@comite')];
out.agentOf = [P.agentOf('@analista hola'), P.agentOf('@noticias hola'), P.agentOf('@comite NVDA')];
out.mascots = P.ANALYSTS.filter(x => x.m).map(x => x.c + ':' + x.m);
process.stdout.write(JSON.stringify(out));
"""


def test_pickers_alias_y_mascotas():
    p = subprocess.run([NODE, '-e', PICK, ROOT], capture_output=True, text=True, timeout=30)
    assert p.returncode == 0, p.stderr
    o = json.loads(p.stdout)
    assert o['typed'] == '@fundamental ¿cómo va Nvidia?'
    assert o['chip'] == '@noticias ¿qué pasa con TSMC?'
    assert o['same'] == '@cadena ¿de quién depende AMD?'
    assert o['pf'] == '/cartera @fundamental mis riesgos'
    assert o['canon'] == ['@fundamental', '@fundamental', '@noticias', '@tecnico', '@comite']
    assert o['agentOf'][0] == {'name': 'Analista', 'emoji': '📊', 'mascot': 'analista'}
    assert o['agentOf'][1]['mascot'] == 'radar' and o['agentOf'][2]['mascot'] == 'comite'
    for x in ('@analista:analista', '@radar:radar', '@cadena:cadena', '@tecnico:tecnico', '@comite:comite',
              '@fundamental:analista', '@noticias:radar', '@geopolitico:radar'):
        assert x in o['mascots']


def test_cartera_con_analista_alias_en_el_enrutador():
    o = _run(r"""
const deps = { resolve: () => null };
out.a = K.classify('@analista ¿qué riesgos tiene mi cartera?', deps);
out.b = K.classify('/cartera @radar ¿algo que vigilar?', deps);
console.log(JSON.stringify(out));
""")
    assert o['a']['kind'] == 'agentask' and o['a']['seat'] == 'fundamental'
    assert o['b']['kind'] == 'agentask' and o['b']['seat'] == 'news'


def test_estilos_con_tokens_y_sync_de_preferencias():
    kc = open(os.path.join(ROOT, 'engine', 'khipu_chat.js'), encoding='utf-8').read()
    pk = open(os.path.join(ROOT, 'engine', 'pickers.js'), encoding='utf-8').read()
    sy = open(os.path.join(ROOT, 'engine', 'sync.js'), encoding='utf-8').read()
    css = kc.split('var CSS = ')[1].split('function ensureStyles')[0]
    # burbujas con tokens (y respaldo oscuro para el Command Center viejo)
    assert 'var(--os-surface-2,' in css and 'var(--os-ink,' in css and 'border-radius:18px' in css
    assert 'rgba(0,224,255' not in css            # el cian neón del chat viejo ya no se usa
    pcss = pk.split('var css = ')[1].split('function ensureCss')[0]
    assert 'var(--os-surface,' in pcss and 'la app es siempre oscura' not in pk
    assert "'kh_agent_prefs'" in sy.split('var KEYS = ')[1].split(';')[0]


def test_respuesta_de_un_agente_abre_solo_la_ventana_de_su_rol():
    """@cadena → la ventana «Cadena de suministro» (acción open_window), no la mirada general del Analista."""
    o = _run(r"""
ctx.LANG = 'es';
const staged = [], opened = [];
ctx.KhipuAgentPrefs = { mode: () => 'simple', enabled: () => ['khipu', 'analista', 'radar', 'cadena', 'comite'], auto: () => true, get: () => ({}) };
ctx.KhipuOSWin = { kinds: { glance: {}, supplychain: {}, conviction: {}, agents: {} }, open: (k, a) => { opened.push([k, a.id]); return true; } };
ctx.BixbyCockpit = { isOpen: () => true, isCentered: () => true, stage: (k, a) => staged.push([k, a]) };
const reply = { answer: 'Depende de Microsoft [S1].', answer_source: 'agent', agent: { seat: 'supply_chain' },
  entities: [{ id: 'OpenAI', label: 'OpenAI' }], agents_used: [{ agent: 'cadena', tools: ['ask_agent'], ok: true, note_es: 'x' }],
  actions: [{ type: 'open_window', arg: { kind: 'supplychain', id: 'OpenAI' }, label: 'OpenAI' }, { type: 'open_research', arg: 'OpenAI', label: 'OpenAI' }],
  tools_used: [], sources: [] };
out.plan = K.planWindows ? K.planWindows(reply, 'analiza open ai', null, true) : 'n/a';
out.label = [K.actionLabel(reply.actions[0]), (ctx.LANG = 'en', K.actionLabel(reply.actions[0]))];
ctx.LANG = 'es';
const thread = new El('div'); const pend = K.appendPending(thread);
K.fillReply(pend, reply, { autoRun: true });
setTimeout(() => { out.staged = staged; out.opened = opened; out.direct = K.runAction({ type: 'open_window', arg: { kind: 'glance', id: 'Nvidia' } });
  console.log(JSON.stringify(out)); }, 1200);
""")
    if o['plan'] != 'n/a':
        assert o['plan'] == []
    assert o['label'] == ['⛓ Cadena de suministro: OpenAI', '⛓ Supply chain: OpenAI']
    assert o['staged'] == [] and o['opened'][0] == ['supplychain', 'OpenAI']
    assert o['direct'] is True and o['opened'][-1] == ['glance', 'Nvidia']


def test_pie_dice_cuando_jev_respondio_sin_ia():
    o = _run(r"""
ctx.LANG = 'es';
out.local = K.replyHTML({ answer: '**Nvidia** — x', answer_source: 'local', ai: false, elapsed_ms: 420,
  router: { by: 'jev', route: 'local_fact', confidence: 0.9 }, tools_used: [], sources: [] }, {});
out.fast = K.replyHTML({ answer: 'ok', ai: true, model: 'gemini:gemini-3.8-flash', steps: 2, elapsed_ms: 3000,
  router: { by: 'jev', route: 'needs_tools', confidence: 0.8 }, tools_used: [], sources: [] }, {});
ctx.LANG = 'en';
out.en = K.replyHTML({ answer: 'x', answer_source: 'local', ai: false, router: { by: 'jev', route: 'local_fact' }, tools_used: [], sources: [] }, {});
out.plain = K.replyHTML({ answer: 'ok', ai: true, model: 'fake', steps: 1, router: { by: 'default' }, tools_used: [], sources: [] }, {});
console.log(JSON.stringify(out));
""")
    assert 'Respondido con datos locales, sin IA · ⚡ Jev: sin IA' in o['local'] and '0.4 s' in o['local']
    assert '⚡ Jev: consulta corta' in o['fast'] and 'Gemini gemini-3.8-flash' in o['fast']
    assert 'Answered from local data, no AI · ⚡ Jev: no AI' in o['en']
    assert 'Jev' not in o['plain']
