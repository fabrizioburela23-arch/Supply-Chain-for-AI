"""tests/test_voice_os_client.py — la voz de Khipu dentro de Khipus OS (contrato de herramientas v2, 2026-10-11).

Dos niveles:
1. engine/voice.js en Node (vm) con el arnés de tests/test_overnight_voice_client.py (WebSocket, audio, micrófono
   y RELOJ falsos) + dobles de Khipus OS (BixbyCockpit, KhipuDesk, KhipuOSWin, KhipuChat, motor de estados,
   bróker…): las 17 herramientas, TODOS los nombres retirados como alias, recortes de citas, sin nombres internos,
   dinero en dos pasos (nada se envía sin confirmed=true; DINERO REAL cuando la cuenta es real), CONTEXT_UPDATE.
2. La Cabina REAL en Chromium (Playwright) con voice.js + cockpit.js + khipu_chat.js + desktop.js + statematrix.js:
   una pregunta hablada se ve en el chat del centro (burbuja 🎙 + respuesta), la voz dice el MISMO número que la
   ventana (motor único del servidor, /api/hot/*; el auge de demanda aún no se calcula y se dice) y «Ver en el
   mapa» ya no cierra Khipus OS.
Se salta lo que necesite `node` o Chromium si no están.
"""
import json
import os
import re
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = shutil.which('node')
VOICE_PATH = os.path.join(ROOT, 'engine', 'voice.js')
COCKPIT_PATH = os.path.join(ROOT, 'engine', 'cockpit.js')


def _r(*p):
    with open(os.path.join(ROOT, *p), encoding='utf-8') as f:
        return f.read()


# Contrato v2: tabla de topes (server _VOICE_TOOL_TIMEOUTS == voice.js VOICE_TOOL_TIMEOUT_S)
CONTRACT_TIMEOUTS = {'ask_khipu_brain': 60, 'open_company': 15, 'get_company_info': 15, 'run_agent_simulation': 90,
                     'quick_thesis': 90, 'show_opportunities': 15, 'place_order': 45, 'get_account_status': 45,
                     'get_space_summary': 20,
                     'run_guided_demo': 30}   # el recorrido de 1 minuto (2026-10-11) pide 30 s en el servidor
TOOLS = ['ask_khipu_brain', 'open_company', 'get_company_info', 'open_screen', 'compare_companies', 'run_live_simulation',
         'run_agent_simulation', 'show_opportunities', 'create_visualization', 'quick_thesis', 'deep_search', 'place_order',
         'open_order_ticket', 'get_account_status', 'get_space_summary', 'run_guided_demo', 'control_interface']
RETIRED = ['open_cockpit', 'switch_tab', 'show_chart', 'open_terminal', 'navigate_to_company', 'open_xray',
           'open_second_brain', 'open_dossier', 'get_risk_score', 'get_supply_chain_links', 'get_news',
           'get_market_summary', 'get_portfolio_risk', 'list_companies', 'get_opportunities', 'show_insights',
           'run_stress_test', 'run_simulation', 'deep_research', 'deep_analysis', 'place_paper_trade', 'place_trade',
           'get_portfolio_status', 'get_nrs_top10', 'show_matrices']


# ═══════════════════════════════ estáticas ═══════════════════════════════
def test_timeouts_equal_contract_table():
    js = _r('engine', 'voice.js')
    m = re.search(r'const VOICE_TOOL_TIMEOUT_S = \{(.*?)\};', js, re.S)
    assert m
    assert dict((k, int(v)) for k, v in re.findall(r'(\w+):\s*(\d+)', m.group(1))) == CONTRACT_TIMEOUTS
    assert 'const VOICE_TOOL_TIMEOUT_DEFAULT_S = 10;' in js


def test_every_tool_and_retired_alias_has_a_case():
    js = _r('engine', 'voice.js')
    for name in TOOLS + RETIRED:
        assert f"case '{name}'" in js, name
    assert 'window.KhipuChat.send(q, { timeout: 55000 })' in js          # literal fijado por otro test


def test_legacy_text_token_router_is_gone():
    js = _r('engine', 'voice.js')
    assert '_onAgentResponse' not in js
    for tok in (r'\[NAV:', r'\[XRAY:', r'\[SHOCK:', r'\[SIM:', r'\[TAB:'):
        assert tok not in js, tok
    assert 'active_tab' not in js                                         # CONTEXT_UPDATE sin pestaña activa
    assert "'consulted'" not in js and 'consulted:' not in js


def test_cockpit_sim_uses_severity_for_every_kind_and_map_sim_keeps_os():
    ck = _r('engine', 'cockpit.js')
    assert '{ salud: 100 }' not in ck                                     # el auge de demanda ya no es "sin daño"
    i = ck.index('window._cockpitMapSim = function')
    body = ck[i:ck.index('\n  };', i)]
    assert 'close()' not in body and "switchTab('map')" not in body and "stage('graph', n.id)" in body
    assert "chatVoice: chatVoice" in ck


# ═══════════════════════════════ voice.js en Node ═══════════════════════════════
MAIN = r"""
let CALLN = 0;
async function call(E, ws, name, params, ms) {
  const id = 'tc_' + (++CALLN);
  ws._msg({ type: 'client_tool_call', client_tool_call: { tool_name: name, tool_call_id: id, parameters: params || {} } });
  await E.advance(ms == null ? 60 : ms);
  const m = ws.sent.filter(x => x.type === 'client_tool_result' && x.tool_call_id === id);
  return { n: m.length, raw: m.length ? m[0].result : null, body: m.length ? JSON.parse(m[0].result) : null };
}

function osFakes(E, o) {
  o = o || {};
  const W = E.ctx, rec = { stage: [], osw: [], screens: [], chatVoice: [], send: [], runAction: [], research: [], committee: [],
    sim: [], agentSim: [], thesis: [], trade: [], prefs: [], desk: [], theme: 0, lang: 0, newConv: 0, closed: 0, demo: 0, opened: 0,
    fetch: [], recolor: [] };
  W.__rec = rec;
  const N = [
    { id: 'nvidia', label: 'NVIDIA', mkt: 'NVDA', cat: 'fabless', country: 'EEUU', margin: 0.55, growth: '🟢 fuerte', role: 'GPUs', moat: 'CUDA' },
    { id: 'tsmc', label: 'TSMC', mkt: 'TSM', cat: 'foundry', country: 'Taiwan', margin: 0.4, growth: '🟢' },
    { id: 'openai', label: 'OpenAI', cat: 'lab', country: 'EEUU', margin: -0.5, growth: '🟢', preipo: true },
    { id: 'amd', label: 'AMD', mkt: 'AMD', cat: 'fabless', country: 'EEUU', margin: 0.2, growth: '🟡' },
    { id: 'msft', label: 'Microsoft', mkt: 'MSFT', cat: 'cloud', country: 'EEUU', margin: 0.45, growth: '🟢' },
  ];
  W.NODES = N; W.NODE_BY_ID = {}; N.forEach(n => { W.NODE_BY_ID[n.id] = n; });
  W.LINKS = [
    { source: 'tsmc', target: 'nvidia', type: 'supply', w: 9 },
    { source: 'tsmc', target: 'nvidia', type: 'fab', w: 8 },          // par repetido → una sola vez
    { source: 'msft', target: 'nvidia', type: 'invest', w: 5 },       // NO es proveedor (G4a)
    { source: 'openai', target: 'nvidia', type: 'partner', w: 5 },    // NO es proveedor
    { source: 'nvidia', target: 'openai', type: 'supply', w: 7 },
    { source: 'nvidia', target: 'msft', type: 'supply', w: 6 },
    { source: 'nvidia', target: 'amd', type: 'partner', w: 9 },       // NO es cliente
  ];
  W.NRS_FLOW_TYPES = { supply: 1, fab: 1, cloud: 1, license: 1, ppa: 1, owns: 1, deploy: 1 };
  W.computeNRS = (id) => ({ nvidia: 42, amd: 42, tsmc: 71, openai: 50, msft: 30 }[id] ?? 50);
  W.computeNRSBreakdown = (id) => ({ total: W.computeNRS(id), terms: [{ key: 'Geopolítica', val: 8, max: 30, hot: false, detail: 'x' },
    { key: 'Cadena', val: 10, max: 25, hot: false, detail: 'grado 4' }] });
  W.MKT = { pos: {}, quotes: { NVDA: { close: 100, live: 101.5, src: 'finnhub', as_of: '2026-10-11T14:00:00Z', currency: 'USD' } } };
  W.quotePx = (q) => (q && typeof q.live === 'number') ? q.live : (q && q.close);
  W.quoteIsLive = (q) => !!(q && typeof q.live === 'number');
  W.SECTORS9 = { semis: { label: 'Semiconductores' } }; W.CAT_TO_SECTOR = { fabless: 'semis', foundry: 'semis' };
  W.NODE_META = { nvidia: { employees: 36000, founded: 1993, mktcap_b: 999 } };
  W.PRIVATE_VALUATIONS = { entries: { openai: { valuation_usd_b: 500, label: '$500B (2026-03)', as_of: '2026-03', source_url: 'https://ex.test/oa' } } };
  const norm = s => String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').trim();
  W.KhipuResolve = {
    find: (q) => { const k = norm(q); const n = N.find(x => norm(x.id) === k || norm(x.label) === k || norm(x.mkt) === k); return n ? { node: n, score: 100 } : null; },
    notFound: (q) => ({ spoken: 'No encontré «' + q + '». ¿Quisiste decir NVIDIA?', suggestions: [{ label: 'NVIDIA' }] }),
  };
  let isOpen = o.osOpen !== false;
  const SCREENS = [['graph', 'Mapa de la cadena', 'Supply-chain map'], ['market', 'Mercado', 'Market'], ['terminal', 'Terminal', 'Terminal'],
    ['portfolios', 'Carteras de práctica', 'Practice portfolios'], ['broker', 'Mi cuenta (bróker)', 'My account (broker)'],
    ['risk', 'Riesgo de cartera', 'Portfolio risk'], ['insights', 'Oportunidades', 'Opportunities'], ['guia', 'Guía', 'Guide'],
    ['xray', 'X-Ray de una empresa', 'Company X-Ray'], ['swarm', 'Investigación con evidencia', 'Evidence-based research']];
  const TITLE = { xray: ['X-Ray', 'X-Ray'], graph: ['Grafo', 'Graph'], terminal: ['Terminal', 'Terminal'], compare: ['Comparar', 'Compare'],
    insights: ['Oportunidades', 'Opportunities'], canvas: ['Gráfico', 'Chart'], research: ['Tesis rápida', 'Quick thesis'],
    deep: ['Búsqueda profunda', 'Deep search'], agentsim: ['Simulación por agentes', 'Agent simulation'], broker: ['Mi cuenta', 'My account'],
    sim: ['Caída simulada', 'Simulated failure'] };
  const SIMT = { demand: ['Auge de demanda', 'Demand boom'], price: ['Shock de precio', 'Price shock'], sanction: ['Sanción', 'Sanction'] };
  const en = () => W.LANG === 'en';
  W.BixbyCockpit = {
    isOpen: () => isOpen,
    open: (init) => { isOpen = true; rec.opened++; if (init && init.kind) rec.stage.push([init.kind, init.arg]); },
    close: () => { isOpen = false; rec.closed++; },
    stage: (k, a) => { rec.stage.push([k, a]); },
    screens: () => SCREENS.map(s => ({ id: s[0], es: s[1], en: s[2] })),
    openScreen: (id) => { rec.screens.push(id); return true; },
    title: (k, a) => {
      let m = TITLE[k]; if (k === 'sim' && a && SIMT[a.kind]) m = SIMT[a.kind];
      if (!m) return k;
      const id = (a && typeof a === 'object') ? (a.id || a.ticker || a.a) : a;
      const n = id && (W.NODE_BY_ID[id] || N.find(x => x.mkt === id));
      return (en() ? m[1] : m[0]) + (n ? ' · ' + n.label : (typeof a === 'string' && (k === 'deep' || k === 'canvas') ? ' · ' + a.slice(0, 40) : ''));
    },
    chatVoice: (text, opts) => { rec.chatVoice.push([text, opts]); return Promise.resolve(Object.assign({}, W.__reply, { opened: ['NVIDIA en una mirada'] })); },
    deepStart: () => W.__deepStart || null,
    matrixInsights: () => Promise.resolve({ insights: [{ title: 'Factor **Taiwán** activo [S1]', detail: 'TSMC concentra [E2, E3] el riesgo.' }] }),
    newConversation: () => { rec.newConv++; },
    toggleTheme: () => { rec.theme++; W.document.body.classList.toggle('dark'); },
    toggleLang: () => { rec.lang++; },
    invoked: () => 'cadena',
    demo: () => { rec.demo++; },
  };
  const wins = [{ id: 'kd1', kind: 'glance', min: false }, { id: 'kd2', kind: 'xray', min: false }, { id: 'kd3', kind: 'graph', min: true }];
  W.KhipuDesk = { enabled: () => true, active: () => true, list: () => wins.map(w => Object.assign({}, w)), focused: () => 'kd2',
    arrange: (f) => rec.desk.push(['arrange', f]), closeAll: () => rec.desk.push(['closeAll']), minimize: (id) => rec.desk.push(['min', id]) };
  W.KhipuOSWin = { open: (k, a) => { rec.osw.push([k, a]); return true; } };
  W.KhipuResearch = { open: (id) => rec.research.push(id) };
  W.KhipuCommittee = { open: (id) => rec.committee.push(id) };
  W.KhipuAgentPrefs = { set: (p) => rec.prefs.push(p), mode: () => 'simple' };
  W.KhipuChat = {
    send: (q, opts) => { rec.send.push([q, opts]); return Promise.resolve(W.__reply); },
    runAction: (a) => { rec.runAction.push(a); return true; },
    agentName: (id) => ({ cadena: 'Cadena', analista: 'Analista', radar: 'Radar', khipu: 'Khipu' }[id] || id),
    actionLabel: (a) => a.type,
  };
  W.__reply = { answer: '**Nvidia** depende de TSMC [E1] y de HBM [S2, S3].', agents_used: [{ agent: 'khipu', ok: true }, { agent: 'cadena', ok: true }, { agent: 'radar', ok: false }],
    sources: [1, 2, 3, 4, 5, 6, 7].map(i => ({ label: 'Fuente ' + i, as_of: '2026-10-1' + (i % 10), url: 'https://s/' + i })),
    tools_used: [{ name: 'get_supply_chain' }], actions: [{ type: 'open_xray', arg: 'nvidia' }] };
  // paso 13 INFRA_OPERATIVA: el motor del servidor por window.KhipuHot (doble); el auge de demanda aún no lo calcula
  W.KhipuHot = { simulate: (o) => {
    rec.sim.push(o);
    if (o.kind === 'demand') return Promise.resolve({ ok: false, code: 'unsupported_direction', unsupported: true,
      error: 'El auge de demanda hacia los proveedores todavía no lo calcula el motor único del servidor. No mostramos cifras inventadas.' });
    const id = o.targets[0], hit = o.severity / 100, m = new Map();
    m.set(id, o.severity);
    if (hit > 0) { m.set('amd', 30 * hit); m.set('openai', 10 * hit); }
    return Promise.resolve({ ok: true, kind: o.kind, direction: 'down', severity: o.severity, targets: [id], impact: m,
      reach_1: hit > 0 ? 2 : 0, note: o.kind === 'price' ? 'intensidad transmitida' : '', view: { generation: 'g0.rA.c1.snapshot' } });
  }, rivals: () => [{ id: 'msft', hit: 0 }] };
  W._runAgentSim = (sc, seeds, lang) => { rec.agentSim.push([sc, seeds, lang]); return Promise.resolve({ ok: true, narrative: 'El **suministro** cae [E1].',
    impacts: [{ label: 'TSMC', pct: -30, rationale: 'Planta parada [S1]' }], agents: [{ name: 'Gobierno' }] }); };
  W._openDeepResearch = (id, lang) => { rec.thesis.push([id, lang]); return Promise.resolve({ thesis: 'Tesis **fuerte** [E1].', sector: 'Semis', competitors: ['AMD', { name: 'Intel' }],
    geopolitics: 'Taiwán [C2]', chokepoints: ['CoWoS'], risks: ['Export [F1]'] }); };
  W.ScenarioBuilder = { PRESETS: { taiwan_conflict: { title: 'Crisis en Taiwán', description: 'TSMC se detiene.', question: '¿Qué pasa?', nodeIds: ['tsmc'] } } };
  W.KhipuLive = { profile: (t) => Promise.resolve({ available: true, price: 101.5, change_pct: 1.2, market_cap_usd_b: 2500, currency: 'USD', as_of: '2026-10-11T14:00:00Z', source: 'yahoo' }) };
  W._liveRecolorByImpact = (m, dir) => rec.recolor.push(dir);
  W.document.body = { classList: (function () { const s = new Set(); return { contains: c => s.has(c), toggle: (c, f) => { const on = f === undefined ? !s.has(c) : !!f; on ? s.add(c) : s.delete(c); return on; }, add: c => s.add(c), remove: c => s.delete(c) }; })() };
  // bróker: cuenta de DINERO REAL (paper:false) — la voz NUNCA debe decir "simulada"
  W._tradeFetch = async (url, opts, interactive) => {
    rec.trade.push([url, (opts && opts.method) || 'GET', !!interactive]);
    const J = (st, d) => ({ ok: st < 400, status: st, json: async () => d });
    if (url === '/api/trade/account') return J(200, { paper: o.paper === undefined ? false : o.paper, equity: '1000', cash: '500', buying_power: '500' });
    if (url === '/api/trade/positions/detail') return J(200, []);
    if (url === '/api/trade/order') return J(200, { id: 'o1', status: 'accepted' });
    return J(404, {});
  };
  const f0 = W.fetch;
  W.fetch = async (url, init) => {
    rec.fetch.push(url);
    if (String(url).endsWith('/api/space/tle')) return { ok: true, status: 200, json: async () => W.__tle };
    if (String(url).endsWith('/api/space/launches')) return { ok: true, status: 200, json: async () => [{ name: 'Falcon 9 | Starlink' }] };
    return f0(url, init);
  };
  return rec;
}

async function session(E) {
  await E.V.connect();
  const ws = E.sockets[0]; ws._open();
  ws._msg(META('pcm_16000', 'pcm_16000'));
  return ws;
}

async function main() {
  const R = {};
  const S = { data: { signed_url: 'wss://api.elevenlabs.io/v1/convai/conversation?agent_id=a&conversation_signature=s', overrides: {}, language: 'es' } };
  // ═══ A) Khipus OS abierto, en español ═══
  {
    const E = makeEnv({ session: S }); const rec = osFakes(E); const ws = await session(E);
    const brain = await call(E, ws, 'ask_khipu_brain', { question: '¿de quién depende Nvidia?', agent: 'cadena' });
    R.brain = { body: brain.body, raw: brain.raw, chatVoice: rec.chatVoice.slice(), send: rec.send.length };
    const brainAg = {};
    for (const [ag, tok] of [['analista', '@fundamental'], ['radar', '@noticias'], ['tecnico', '@tecnico'], ['comite', '@comite'], ['Técnico', '@tecnico']]) {
      rec.chatVoice.length = 0;
      await call(E, ws, 'ask_khipu_brain', { question: '¿y Nvidia?', agent: ag });
      brainAg[ag] = rec.chatVoice[0] && rec.chatVoice[0][0];
    }
    R.brainAgents = brainAg;
    // sin empresa en la pregunta, la mención @agente NO se agrega (iría a "¿sobre qué empresa?" o a la última que viste)
    const brainGen = {};
    for (const [ag, q] of [['radar', 'Últimas noticias relevantes del mercado'], ['radar', '¿qué noticias hay sobre el conflicto en Taiwán?'],
                           ['comite', '¿qué piensa el equipo?'], ['radar', 'what is new now on the net'], ['radar', '¿qué pasa con tsmc hoy?'],
                           ['tecnico', '¿cómo viene NVDA?'], ['cadena', 'proveedores de Microsoft']]) {
      rec.chatVoice.length = 0;
      await call(E, ws, 'ask_khipu_brain', { question: q, agent: ag });
      brainGen[ag + ' | ' + q] = rec.chatVoice[0] && rec.chatVoice[0][0];
    }
    R.brainGeneral = brainGen;
    R.brainEmpty = (await call(E, ws, 'ask_khipu_brain', { question: '  ' })).body;
    // open_company: cada vista
    const views = {};
    for (const v of ['glance', 'xray', 'supply_chain', 'map', 'chart', 'dossier', 'research', 'committee']) {
      rec.stage.length = 0; rec.osw.length = 0; E.surfaces.length = 0; rec.research.length = 0; rec.committee.length = 0;
      const r = await call(E, ws, 'open_company', { company_name: 'nvidia', view: v });
      views[v] = { body: r.body, stage: rec.stage.slice(), osw: rec.osw.slice(), surf: E.surfaces.slice(), research: rec.research.slice(), committee: rec.committee.slice() };
    }
    R.views = views;
    rec.stage.length = 0; rec.osw.length = 0;
    R.privChart = { body: (await call(E, ws, 'open_company', { company_name: 'OpenAI', view: 'chart' })).body, osw: rec.osw.slice(), stage: rec.stage.slice() };
    R.ocMissing = (await call(E, ws, 'open_company', { company_name: 'Nvidiaa' })).body;
    // get_company_info (sin ventanas)
    rec.stage.length = 0; rec.osw.length = 0; E.surfaces.length = 0;
    R.info = (await call(E, ws, 'get_company_info', { company_name: 'NVIDIA' })).body;
    R.infoPriv = (await call(E, ws, 'get_company_info', { company_name: 'openai' })).body;
    R.infoOpened = rec.stage.length + rec.osw.length + E.surfaces.length;
    // open_screen
    rec.screens.length = 0;
    R.scr = {};
    for (const s of ['market', 'map', 'analysis', 'portfolios', 'xray', 'swarm', 'nope', '']) R.scr[s] = (await call(E, ws, 'open_screen', { screen: s })).body;
    R.scrCalls = rec.screens.slice();
    // compare
    rec.stage.length = 0;
    R.cmp = (await call(E, ws, 'compare_companies', { company_a: 'NVIDIA', company_b: 'AMD' })).body;
    R.cmp2 = (await call(E, ws, 'compare_companies', { company_a: 'TSMC', company_b: 'msft' })).body;
    R.cmpStage = rec.stage.slice();
    // run_live_simulation
    rec.stage.length = 0; rec.sim.length = 0;
    R.sim = (await call(E, ws, 'run_live_simulation', { company_name: 'NVIDIA', kind: 'price', severity: 60 })).body;
    R.simShock = rec.sim.slice(); R.simStage = rec.stage.slice();
    rec.stage.length = 0; rec.sim.length = 0;
    R.simUp = (await call(E, ws, 'run_live_simulation', { company_name: 'NVIDIA', kind: 'demand', severity: 60 })).body;
    R.simUpShock = rec.sim.slice(); R.simUpStage = rec.stage.slice();
    R.sevs = {};
    for (const sv of [0, 250, 'abc', -5, 1, 33.4]) { rec.sim.length = 0; const b = (await call(E, ws, 'run_live_simulation', { company_name: 'nvidia', severity: sv })).body; R.sevs[String(sv)] = [b.severity, rec.sim[0].severity, b.kind]; }
    // agent sim
    rec.agentSim.length = 0;
    R.asim = (await call(E, ws, 'run_agent_simulation', { preset: 'taiwan_conflict' })).body;
    R.asim2 = (await call(E, ws, 'run_agent_simulation', { scenario: 'China corta el galio', companies: 'NVIDIA, tsmc' })).body;
    R.asimBad = (await call(E, ws, 'run_agent_simulation', {})).body;
    R.asimCalls = rec.agentSim.slice();
    rec.stage.length = 0;
    R.opps = (await call(E, ws, 'show_opportunities', {})).body; R.oppsStage = rec.stage.slice();
    rec.stage.length = 0;
    R.viz = (await call(E, ws, 'create_visualization', { query: 'márgenes de Nvidia' })).body; R.vizStage = rec.stage.slice();
    R.vizBad = (await call(E, ws, 'create_visualization', {})).body;
    R.thesis = (await call(E, ws, 'quick_thesis', { company_name: 'NVIDIA' })).body; R.thesisCalls = rec.thesis.slice();
    // deep_search: arranca / ocupado
    E.surfaces.length = 0;
    E.ctx.__deepStart = Promise.resolve({ started: true });
    R.deep = (await call(E, ws, 'deep_search', { question: '¿Qué pasa si sube el cobre?' })).body;
    E.ctx.__deepStart = Promise.resolve({ busy: true, status: 409 });
    R.deepBusy = (await call(E, ws, 'deep_search', { question: 'otra' })).body;
    R.deepSurf = E.surfaces.slice();
    // dinero: vista previa (nada se envía) y luego confirmado
    rec.trade.length = 0; rec.stage.length = 0;
    R.orderPrev = (await call(E, ws, 'place_order', { symbol_or_name: 'NVIDIA', side: 'buy', notional_usd: 100 })).body;
    R.orderPrevPosts = rec.trade.filter(t => t[0] === '/api/trade/order').length;
    R.orderPrevStage = rec.stage.slice();
    R.orderConf = (await call(E, ws, 'place_order', { symbol_or_name: 'NVIDIA', side: 'buy', notional_usd: 100, confirmed: true })).body;
    R.orderConfPosts = rec.trade.filter(t => t[0] === '/api/trade/order' && t[1] === 'POST').length;
    // el sí se usa UNA vez: otro confirmed=true igual vuelve a ser un resumen
    R.orderConfAgain = (await call(E, ws, 'place_order', { symbol_or_name: 'NVIDIA', side: 'buy', notional_usd: 100, confirmed: true })).body;
    R.orderConfAgainPosts = rec.trade.filter(t => t[0] === '/api/trade/order' && t[1] === 'POST').length;
    E.surfaces.length = 0; rec.stage.length = 0; rec.trade.length = 0;
    R.ticket = (await call(E, ws, 'open_order_ticket', { company_name: 'NVIDIA' })).body;
    R.ticketStage = rec.stage.slice(); R.ticketPosts = rec.trade.filter(t => t[0] === '/api/trade/order').length;
    E.ctx.openTradeModal = () => {};
    R.ticket2 = (await call(E, ws, 'open_order_ticket', { company_name: 'NVIDIA' })).body; R.ticket2Surf = E.surfaces.slice();
    R.ticketPriv = (await call(E, ws, 'open_order_ticket', { company_name: 'OpenAI' })).body;
    R.acct = (await call(E, ws, 'get_account_status', {})).body;
    // espacio: respaldo sintético → no se leen cifras; CelesTrak → sí, con fuente
    E.ctx.__tle = { source: 'fallback', constellations: [{ name: 'Starlink', count: 7134 }] };
    R.spaceFb = (await call(E, ws, 'get_space_summary', {})).body;
    E.ctx.__tle = { source: 'celestrak', total_real: 9000, constellations: [{ name: 'Starlink', count: 8800 }, { name: 'GPS', count: 31 }] };
    R.space = (await call(E, ws, 'get_space_summary', { query: 'starlink' })).body;
    R.demo = (await call(E, ws, 'run_guided_demo', {})).body; R.demoCalls = rec.demo;
    // control_interface
    R.ctl = {};
    for (const a of ['new_conversation', 'arrange_windows', 'close_all_windows', 'minimize_all_windows', 'simple_mode', 'pro_mode',
                     'dark_theme', 'dark_theme', 'light_theme', 'english', 'spanish', 'classic_view']) {
      R.ctl[a + (R.ctl[a] ? '_2' : '')] = (await call(E, ws, 'control_interface', { action: a })).body;
    }
    R.ctlRec = { newConv: rec.newConv, desk: rec.desk.slice(), prefs: rec.prefs.slice(), theme: rec.theme, lang: rec.lang, closed: rec.closed };
    // CONTEXT_UPDATE
    const n0 = ws.sent.length; E.V.updateContext();
    R.ctx = ws.sent.slice(n0).map(m => m.text)[0];
    R.errors = E.errors;
  }
  // ═══ B) Alias de TODOS los nombres retirados ═══
  {
    const E = makeEnv({ session: S }); const rec = osFakes(E); const ws = await session(E);
    E.ctx.__deepStart = Promise.resolve({ started: true });
    E.ctx.__tle = { source: 'celestrak', total_real: 9000, constellations: [{ name: 'Starlink', count: 8800 }] };
    const P = { company_name: 'NVIDIA' };
    const cases = [
      ['open_cockpit', {}], ['switch_tab', { tab: 'map' }], ['switch_tab', { tab: 'portfolios' }], ['show_chart', P], ['open_terminal', P],
      ['navigate_to_company', P], ['open_xray', P], ['open_second_brain', P], ['open_dossier', { company_name: 'OpenAI' }],
      ['get_risk_score', { company_name: 'nvidia' }], ['get_supply_chain_links', P], ['get_news', P], ['get_market_summary', {}],
      ['get_portfolio_risk', {}], ['list_companies', { category: 'semis' }], ['get_opportunities', {}], ['show_insights', {}],
      ['show_matrices', {}], ['get_nrs_top10', {}], ['run_stress_test', P], ['run_simulation', { scenario_id: 'taiwan_conflict' }],
      ['deep_research', P], ['deep_analysis', { question: 'cobre' }], ['place_paper_trade', { symbol_or_name: 'NVIDIA', side: 'buy', amount_usd: 50 }],
      ['place_trade', P], ['get_portfolio_status', {}],
    ];
    R.alias = [];
    for (const [name, p] of cases) {
      const before = { stage: rec.stage.length, osw: rec.osw.length, scr: rec.screens.length, cv: rec.chatVoice.length, sim: rec.sim.length,
        asim: rec.agentSim.length, th: rec.thesis.length, surf: E.surfaces.length, opened: rec.opened };
      const r = await call(E, ws, name, p);
      R.alias.push({ name, p, n: r.n, body: r.body, raw: r.raw,
        stage: rec.stage.slice(before.stage), osw: rec.osw.slice(before.osw), scr: rec.screens.slice(before.scr),
        cv: rec.chatVoice.slice(before.cv), sim: rec.sim.slice(before.sim), asim: rec.agentSim.slice(before.asim),
        th: rec.thesis.slice(before.th), surf: E.surfaces.slice(before.surf), opened: rec.opened - before.opened });
    }
    R.aliasPosts = rec.trade.filter(t => t[0] === '/api/trade/order').length;
    R.aliasClosed = rec.closed;
    // un alias lento usa el tope VIEJO del agente (get_news 20 s), no el de 10 s
    E.ctx.BixbyCockpit.chatVoice = () => new Promise(() => {});
    const id = 'slow_news';
    ws._msg({ type: 'client_tool_call', client_tool_call: { tool_name: 'get_news', tool_call_id: id, parameters: P } });
    await E.advance(17000);
    R.newsBefore = ws.sent.filter(x => x.tool_call_id === id).length;
    await E.advance(2000);
    R.newsAfter = ws.sent.filter(x => x.tool_call_id === id).map(x => JSON.parse(x.result));
    R.errors = E.errors;
  }
  // ═══ D) dinero: confirmed=true SIN su resumen no envía; lado explícito; modo del bróker sin PIN ═══
  {
    const E = makeEnv({ session: S }); const rec = osFakes(E); const ws = await session(E);
    const posts = () => rec.trade.filter(t => t[0] === '/api/trade/order' && t[1] === 'POST').length;
    R.d = {};
    R.d.noPrev = (await call(E, ws, 'place_order', { symbol_or_name: 'NVIDIA', side: 'buy', notional_usd: 100, confirmed: true })).body;
    R.d.noPrevPosts = posts();
    R.d.aliasNoPrev = (await call(E, ws, 'place_paper_trade', { symbol_or_name: 'TSMC', side: 'sell', amount_usd: 300, confirmed: 'true' })).body;
    R.d.aliasNoPrevPosts = posts();
    // resumen de $100 → "sí" con OTRO monto: no se envía
    await call(E, ws, 'place_order', { symbol_or_name: 'AMD', side: 'buy', notional_usd: 100, confirmed: false });
    R.d.otherAmount = (await call(E, ws, 'place_order', { symbol_or_name: 'AMD', side: 'buy', notional_usd: 1000, confirmed: true })).body;
    R.d.otherAmountPosts = posts();
    // resumen viejo (más de 3 min) → no vale
    await call(E, ws, 'place_order', { symbol_or_name: 'AMD', side: 'buy', notional_usd: 100, confirmed: false });
    if (E.V._orderPreview) E.V._orderPreview.at -= 4 * 60 * 1000;
    R.d.stale = (await call(E, ws, 'place_order', { symbol_or_name: 'AMD', side: 'buy', notional_usd: 100, confirmed: true })).body;
    R.d.stalePosts = posts();
    // resumen → sí con los MISMOS parámetros → se envía una vez
    R.d.okPrev = (await call(E, ws, 'place_order', { symbol_or_name: 'AMD', side: 'buy', notional_usd: 100, confirmed: false })).body;
    R.d.ok = (await call(E, ws, 'place_order', { symbol_or_name: 'AMD', side: 'buy', notional_usd: 100, confirmed: true })).body;
    R.d.okPosts = posts();
    // lado: nada que no sea comprar o vender se adivina
    R.d.sides = {};
    for (const sd of ['short', 'close', 'cerrar', 'liquidar', '', 'comprar', 'Venta', 'BUY']) {
      R.d.sides[sd] = (await call(E, ws, 'place_order', { symbol_or_name: 'AMD', side: sd, notional_usd: 200, confirmed: false })).body;
    }
    R.d.shortConf = (await call(E, ws, 'place_order', { symbol_or_name: 'AMD', side: 'short', notional_usd: 200, confirmed: true })).body;
    R.d.finalPosts = posts();
    // money_mode: con carteras de práctica y SIN la cuenta leída, el modo real del bróker sale de /api/trade/status
    E.ctx.localStorage.setItem('kh_portfolios', JSON.stringify([{ id: 'p1' }]));
    E.ctx.__tradeAcctCache = null;
    let n0 = ws.sent.length; E.V.updateContext();
    R.d.mmBefore = JSON.parse(ws.sent.slice(n0)[0].text.slice('[CONTEXT_UPDATE] '.length)).money_mode;
    E.ctx._tradeStatusInfo = () => Promise.resolve({ pin_set: true, paper: false });
    n0 = ws.sent.length; E.V.updateContext();
    await E.advance(600);
    R.d.mm = ws.sent.slice(n0).filter(m => m.type === 'contextual_update').map(m => JSON.parse(m.text.slice('[CONTEXT_UPDATE] '.length)).money_mode);
    // el alias viejo deep_research mandaba {company}
    R.d.dr = (await call(E, ws, 'deep_research', { company: 'NVIDIA' })).body;
    R.d.drCalls = rec.thesis.slice();
    // get_news sin empresa → al cerebro sin @noticias
    rec.chatVoice.length = 0;
    await call(E, ws, 'get_news', {});
    R.d.newsGeneral = rec.chatVoice[0] && rec.chatVoice[0][0];
    // Universo 3D: si ya está a la vista, pedirlo no lo cierra (el mismo botón abre y cierra)
    const scr0 = E.ctx.BixbyCockpit.screens;
    E.ctx.BixbyCockpit.screens = () => scr0().concat([{ id: 'universe', es: 'Universo 3D', en: '3D universe' }]);
    E.els['uni-ov'] = { id: 'uni-ov', style: { display: 'block' } };
    rec.screens.length = 0;
    R.d.uniOpen = (await call(E, ws, 'open_screen', { screen: 'universe' })).body;
    R.d.uniOpenCalls = rec.screens.slice();
    E.els['uni-ov'].style.display = 'none';
    R.d.uniClosed = (await call(E, ws, 'open_screen', { screen: 'universe' })).body;
    R.d.uniClosedCalls = rec.screens.slice();
    R.errorsD = E.errors;
  }
  // ═══ C) OS cerrado (vista clásica) + inglés + cuenta de papel ═══
  {
    const E = makeEnv({ session: S, lang: 'en' }); const rec = osFakes(E, { osOpen: false, paper: true }); const ws = await session(E);
    R.brainClassic = (await call(E, ws, 'ask_khipu_brain', { question: 'who supplies Nvidia?' })).body;
    R.brainClassicSend = rec.send.slice(); R.brainClassicRun = rec.runAction.slice(); R.brainClassicCV = rec.chatVoice.length;
    R.scrEn = (await call(E, ws, 'open_screen', { screen: 'market' })).body;
    R.enOpened = rec.opened;
    R.simEn = (await call(E, ws, 'run_live_simulation', { company_name: 'TSMC', kind: 'sanction', severity: 40 })).body;
    R.orderPaper = (await call(E, ws, 'place_order', { symbol_or_name: 'NVIDIA', side: 'sell', qty: 2 })).body;
    R.orderPaperPosts = rec.trade.filter(t => t[0] === '/api/trade/order').length;
    R.acctPaper = (await call(E, ws, 'get_account_status', {})).body;
    R.unknownEn = (await call(E, ws, 'nope_tool', {})).body;
    R.errorsC = E.errors;
  }
  // ═══ D) modo DESCONOCIDO (sin PIN guardado el estado ya no dice papel/real, G5-18) → ante la duda, DINERO REAL ═══
  {
    const E = makeEnv({ session: S }); const rec = osFakes(E, { paper: null }); const ws = await session(E);
    E.ctx._tradeStatusInfo = () => Promise.resolve({ pin_set: true, paper: null });
    R.orderUnknown = (await call(E, ws, 'place_order', { symbol_or_name: 'NVIDIA', side: 'buy', notional_usd: 500 })).body;
    R.orderUnknownPosts = rec.trade.filter(t => t[0] === '/api/trade/order').length;
  }
  process.stdout.write(JSON.stringify(R));
  process.exit(0);
}
main().catch(e => { process.stdout.write(JSON.stringify({ fatal: String(e && e.stack || e) })); process.exit(0); });
"""


@pytest.fixture(scope='module')
def R():
    if not NODE:
        pytest.skip('node no instalado')
    from tests import test_overnight_voice_client as vc
    harness = vc.HARNESS.split('async function main()')[0] + MAIN
    p = subprocess.run([NODE, '-e', harness, VOICE_PATH], capture_output=True, text=True, timeout=180)
    assert p.returncode == 0, p.stderr[-3000:]
    out = json.loads(p.stdout)
    assert 'fatal' not in out, out.get('fatal')
    assert out['errors'] == [] and out['errorsC'] == [] and out['errorsD'] == [], (out['errors'], out['errorsC'], out['errorsD'])
    return out


INTERNAL = re.compile(r'\b(' + '|'.join(TOOLS + RETIRED + ['get_supply_chain', 'tools_used', 'consulted']) + r')\b')
CITE = re.compile(r'\[[A-Z]{1,2}\d')


def _clean_text(raw):
    assert raw is not None
    assert not INTERNAL.search(raw), raw
    assert not CITE.search(raw), raw
    assert '**' not in raw, raw


# ── 1) ask_khipu_brain ──
def test_brain_in_os_goes_to_center_chat_with_agent_prefix(R):
    b = R['brain']
    assert b['send'] == 0 and len(b['chatVoice']) == 1                     # por el chat del centro, no por send()
    text, opts = b['chatVoice'][0]
    assert text == '@cadena: ¿de quién depende Nvidia?' and opts == {'timeout': 55000}
    body = b['body']
    assert body['success'] is True and 'consulted' not in body
    assert body['answer'] == 'Nvidia depende de TSMC y de HBM.'
    assert body['agents'] == ['Cadena']                                     # solo las mascotas que aportaron (sin Khipu, sin la que falló)
    assert len(body['sources']) == 5 and set(body['sources'][0]) == {'label', 'as_of'}
    assert body['opened'] == ['NVIDIA en una mirada']
    _clean_text(b['raw'])
    assert R['brainAgents'] == {'analista': '@fundamental: ¿y Nvidia?', 'radar': '@noticias: ¿y Nvidia?', 'tecnico': '@tecnico: ¿y Nvidia?',
                                'comite': '@comite: ¿y Nvidia?', 'Técnico': '@tecnico: ¿y Nvidia?'}
    e = R['brainEmpty']
    assert e['success'] is False and 'pregunta' in e['error']


def test_brain_classic_view_uses_khipuchat_send_and_first_action(R):
    assert R['brainClassicCV'] == 0
    assert R['brainClassicSend'] == [['who supplies Nvidia?', {'timeout': 55000}]]
    assert R['brainClassicRun'] == [{'type': 'open_xray', 'arg': 'nvidia'}]
    b = R['brainClassic']
    assert b['success'] and b['opened'] == ['X-Ray · NVIDIA'] and 'consulted' not in b


# ── 2) open_company ──
def test_open_company_each_view_calls_its_opener(R):
    v = R['views']
    assert v['glance']['osw'] == [['glance', {'id': 'nvidia'}]]
    assert v['xray']['stage'] == [['xray', 'nvidia']]
    assert v['supply_chain']['osw'] == [['supplychain', {'id': 'nvidia'}]]
    assert v['map']['stage'] == [['graph', 'nvidia']]
    assert v['chart']['stage'] == [['terminal', {'ticker': 'NVDA'}]]
    assert v['dossier']['surf'] == [['dossier', 'NVDA']]
    assert v['research']['research'] == ['nvidia']
    assert v['committee']['committee'] == ['nvidia']
    assert v['xray']['body']['opened'] == 'X-Ray · NVIDIA' and v['map']['body']['opened'] == 'Grafo · NVIDIA'
    assert v['research']['body']['opened'] == 'Investigación con evidencia · NVIDIA'
    for k, x in v.items():
        assert x['body']['success'] is True and x['body']['company'] == 'NVIDIA' and x['body']['listed'] is True, k


def test_open_company_facts_flow_only_suppliers_and_live_price(R):
    f = R['views']['glance']['body']['facts']
    assert f['suppliers'] == ['TSMC']                                       # sin socio (OpenAI) ni inversor (Microsoft), sin repetir
    assert f['customers'] == ['OpenAI', 'Microsoft']                        # sin el socio AMD; los más pesados primero
    assert f['nrs'] == 42 and f['nrs_level'] == 'medio'
    assert f['nrs_terms'][0] == {'key': 'Geopolítica', 'val': 8, 'max': 30}
    assert f['price'] == {'value': 101.5, 'currency': 'USD', 'as_of': '2026-10-11T14:00:00Z', 'src': 'finnhub', 'live': True}
    sc = R['views']['supply_chain']['body']
    assert sc['suppliers_count'] == 1 and sc['customers_count'] == 2


def test_open_company_private_chart_falls_back_to_glance(R):
    p = R['privChart']
    assert p['body']['listed'] is False and p['body']['ticker'] is None and 'no cotiza' in p['body']['note']
    assert p['osw'] == [['glance', {'id': 'openai'}]] and p['stage'] == []
    assert 'price' not in p['body']['facts']
    m = R['ocMissing']
    assert m['success'] is False and m['did_you_mean'] == ['NVIDIA']


# ── 3) get_company_info ──
def test_company_info_live_catalog_and_private_valuation(R):
    i = R['info']
    assert i['success'] and i['live'] == {'price': 101.5, 'market_cap_b': 2500, 'currency': 'USD', 'change_pct': 1.2,
                                          'as_of': '2026-10-11T14:00:00Z', 'src': 'yahoo'}
    assert i['catalog_role'] == 'GPUs' and i['catalog_employees'] == 36000 and i['catalog_sector'] == 'Semiconductores'
    assert 'catálogo' in i['catalog_note'] and 'market_cap_billions' not in i
    assert i['suppliers_count'] == 1 and i['customers_count'] == 2 and i['nrs'] == 42
    p = R['infoPriv']
    assert p['listed'] is False and p['live'] is None and p['listing_status'] == 'private'
    assert p['private_valuation'] == {'value_usd_b': 500, 'label': '$500B (2026-03)', 'as_of': '2026-03', 'source': 'https://ex.test/oa'}
    assert R['infoOpened'] == 0                                             # no abre ventanas


# ── 4) open_screen ──
def test_open_screen_accepts_screens_and_aliases_only(R):
    s = R['scr']
    assert s['market'] == {'success': True, 'opened': 'Mercado'}
    assert s['map'] == {'success': True, 'opened': 'Mapa de la cadena'}
    assert s['analysis']['opened'] == 'Oportunidades' and s['portfolios']['success']
    for bad in ('xray', 'swarm', 'nope', ''):
        assert s[bad]['success'] is False and s[bad]['error'], bad
    assert 'Mercado' in s['nope']['available'] and 'X-Ray de una empresa' not in s['nope']['available']
    assert R['scrCalls'] == ['market', 'graph', 'insights', 'portfolios']
    assert R['scrEn'] == {'success': True, 'opened': 'Market'} and R['enOpened'] >= 1   # OS cerrado → se abre primero


# ── 5) compare ──
def test_compare_tie_and_lower_risk(R):
    assert R['cmp']['lower_risk'] == 'tie' and R['cmp']['nrs_a'] == R['cmp']['nrs_b'] == 42
    assert R['cmp2']['lower_risk'] == 'Microsoft' and R['cmp']['opened'] == 'Comparar · NVIDIA'
    assert R['cmpStage'][0] == ['compare', {'a': 'nvidia', 'b': 'amd'}]


# ── 6) run_live_simulation ──
def test_live_sim_uses_the_server_engine_and_same_severity_in_window(R):
    s = R['sim']
    assert s['success'] and s['kind'] == 'price' and s['severity'] == 60 and s['hypothetical'] is True
    assert s['affected'] == 2 and s['most_impacted'][0] == {'company': 'AMD', 'impact_pct': 18}
    assert s['engine_generation'] == 'g0.rA.c1.snapshot' and 'intensidad transmitida' in s['note']
    assert s['barely_hit_rivals'] == [{'company': 'Microsoft', 'hit_pct': 0}]           # sin % de ganancia inventado
    assert R['simShock'][0] == {'targets': ['nvidia'], 'kind': 'price', 'severity': 60}
    assert R['simStage'] == [['sim', {'id': 'nvidia', 'kind': 'price', 'severity': 60}]]
    assert s['opened'] == 'Shock de precio · NVIDIA'
    sv = R['sevs']
    assert sv['0'][0] == 100 and sv['0'][1] == 100 and sv['0'][2] == 'collapse'
    assert sv['250'][0] == 100 and sv['abc'][0] == 100 and sv['-5'][0] == 100 and sv['1'][0] == 1 and sv['33.4'][0] == 33
    assert sv['33.4'][1] == 33
    e = R['simEn']
    assert e['kind'] == 'sanction' and e['severity'] == 40 and e['opened'] == 'Sanction · TSMC'


def test_live_sim_demand_boom_is_honest_without_numbers(R):
    u = R['simUp']
    assert u['success'] is False and u['unsupported'] is True and u['kind'] == 'demand' and u['severity'] == 60
    assert 'No mostramos cifras inventadas' in u['error'] and 'most_impacted' not in u and 'affected' not in u
    assert R['simUpShock'][0] == {'targets': ['nvidia'], 'kind': 'demand', 'severity': 60}
    assert R['simUpStage'] == []                                      # no abre una ventana con números


# ── 7) run_agent_simulation ──
def test_agent_sim_preset_and_free_scenario(R):
    sc, seeds, lang = R['asimCalls'][0]
    assert sc == 'Crisis en Taiwán. TSMC se detiene. ¿Qué pasa?' and seeds == ['tsmc'] and lang == 'es'
    a = R['asim']
    assert a['success'] and a['hypothetical'] and a['narrative'] == 'El suministro cae.' and a['top_impacts'][0]['why'] == 'Planta parada'
    assert a['opened'].startswith('Simulación por agentes')
    assert R['asimCalls'][1][1] == ['nvidia', 'tsmc']
    assert R['asimBad']['success'] is False


# ── 8-11) oportunidades, gráfico, tesis, búsqueda profunda ──
def test_opportunities_visualization_thesis_deep(R):
    o = R['opps']
    assert R['oppsStage'] == [['insights', None]] or R['oppsStage'][0][0] == 'insights'
    assert o['insights'] == [{'title': 'Factor Taiwán activo', 'text': 'TSMC concentra el riesgo.'}]
    assert {'company': 'NVIDIA', 'nrs': 42} in o['resilient'] and 'asesoría' in o['note'] and o['opened'] == 'Oportunidades'
    assert R['vizStage'] == [['canvas', 'márgenes de Nvidia']] and R['viz']['opened'].startswith('Gráfico')
    assert R['vizBad']['success'] is False
    t = R['thesis']
    assert R['thesisCalls'] == [['nvidia', 'es']]
    assert t['thesis'] == 'Tesis fuerte.' and t['competitors'] == ['AMD', 'Intel'] and t['risks'] == ['Export']
    assert t['geopolitics'] == 'Taiwán' and t['opened'] == 'Tesis rápida · NVIDIA' and 'evidencia' in t['note']
    assert R['deep'] == {'success': True, 'started': True, 'eta_seconds': 60, 'opened': 'Búsqueda profunda · ¿Qué pasa si sube el cobre?'}
    db = R['deepBusy']
    assert db['success'] is False and db['busy'] is True and 'en curso' in db['error']
    assert R['deepSurf'][0] == ['deep', '¿Qué pasa si sube el cobre?']


# ── 12-14) dinero ──
def test_place_order_preview_sends_nothing_and_says_real_money(R):
    p = R['orderPrev']
    assert p['success'] is False and p['needs_confirmation'] is True and p['paper'] is False and p['mode'] == 'live'
    assert 'DINERO REAL' in p['summary'] and 'SIMULADA' not in p['summary']
    assert R['orderPrevPosts'] == 0
    assert R['orderPrevStage'][0][0] == 'broker' and R['orderPrevStage'][0][1]['confirm']['symbol'] == 'NVDA'
    c = R['orderConf']
    assert R['orderConfPosts'] == 1 and c['success'] is True and c['mode'] == 'live' and 'DINERO REAL' in c['summary']
    pp = R['orderPaper']
    assert pp['needs_confirmation'] and pp['mode'] == 'paper' and 'PAPER' in pp['summary'] and R['orderPaperPosts'] == 0
    a2 = R['orderConfAgain']                                                    # el sí se usó: otro confirmed=true = resumen
    assert a2['needs_confirmation'] is True and a2['success'] is False and R['orderConfAgainPosts'] == 1


def test_place_order_unknown_mode_says_real_money(R):
    """Revisión lote I: sin PIN el modo es desconocido → el resumen hablado dice DINERO REAL (nunca solo «Orden»)."""
    u = R['orderUnknown']
    assert u['needs_confirmation'] is True and u['paper'] is None and u['mode'] == 'unknown'
    assert u['summary'].startswith('Orden con DINERO REAL') and 'PIN' in u['summary'] and R['orderUnknownPosts'] == 0


def test_place_order_confirmed_without_its_summary_sends_nothing(R):
    d = R['d']
    for k in ('noPrev', 'aliasNoPrev', 'otherAmount', 'stale'):
        b = d[k]
        assert b['success'] is False and b['needs_confirmation'] is True, (k, b)
        assert 'Nothing was sent' in b['note'] and b['mode'] == 'live' and 'DINERO REAL' in b['summary'], (k, b)
    assert d['noPrevPosts'] == 0 and d['aliasNoPrevPosts'] == 0 and d['otherAmountPosts'] == 0 and d['stalePosts'] == 0
    assert d['okPrev']['needs_confirmation'] is True and 'note' not in d['okPrev']
    assert d['ok']['success'] is True and d['okPosts'] == 1                       # resumen → sí con lo mismo → UNA orden


def test_place_order_side_is_never_guessed(R):
    sides = R['d']['sides']
    for sd in ('short', 'close', 'cerrar', 'liquidar', ''):
        b = sides[sd]
        assert b['success'] is False and b.get('needs_side') is True and 'needs_confirmation' not in b, (sd, b)
        assert b['error'] == '¿Comprar o vender? Dime cuál para AMD.'
    assert sides['comprar']['side'] == 'buy' and sides['BUY']['side'] == 'buy' and sides['Venta']['side'] == 'sell'
    assert R['d']['shortConf'].get('needs_side') is True and R['d']['finalPosts'] == 1   # 'short' confirmado tampoco envía


def test_money_mode_uses_the_broker_flag_not_the_practice_portfolios(R):
    d = R['d']
    assert d['mmBefore'] == 'practice'                                          # sin NADA del bróker: solo las carteras
    assert d['mm'] and d['mm'][-1] == 'live', d['mm']                            # /api/trade/status (sin PIN) dice real → 'live'


def test_retired_deep_research_company_param_general_news_and_universe(R):
    d = R['d']
    assert d['dr']['success'] is True and d['drCalls'] == [['nvidia', 'es']]
    assert d['newsGeneral'] == 'Últimas noticias relevantes del mercado'
    assert d['uniOpen']['success'] is True and d['uniOpenCalls'] == []         # ya abierto: no se toca (no se cierra)
    assert d['uniClosed']['success'] is True and d['uniClosedCalls'] == ['universe']


def test_brain_agent_mention_only_with_a_company(R):
    g = R['brainGeneral']
    assert g['radar | Últimas noticias relevantes del mercado'] == 'Últimas noticias relevantes del mercado'
    assert g['radar | ¿qué noticias hay sobre el conflicto en Taiwán?'] == '¿qué noticias hay sobre el conflicto en Taiwán?'
    assert g['comite | ¿qué piensa el equipo?'] == '¿qué piensa el equipo?'
    assert g['radar | what is new now on the net'] == 'what is new now on the net'      # palabras, no tickers
    assert g['radar | ¿qué pasa con tsmc hoy?'] == '@noticias: ¿qué pasa con tsmc hoy?'
    assert g['tecnico | ¿cómo viene NVDA?'] == '@tecnico: ¿cómo viene NVDA?'
    assert g['cadena | proveedores de Microsoft'] == '@cadena: proveedores de Microsoft'


def test_order_ticket_and_account_status(R):
    t = R['ticket']
    assert t['success'] and 'No se envía nada' in t['note'] and R['ticketStage'][0][0] == 'broker' and R['ticketPosts'] == 0
    assert R['ticket2Surf'] == [['trade', {'id': 'nvidia', 'ticker': 'NVDA', 'label': 'NVIDIA'}]]
    assert R['ticketPriv']['success'] is False and 'no cotiza' in R['ticketPriv']['error']
    a = R['acct']
    assert a['success'] and a['mode'] == 'live' and a['paper'] is False and 'DINERO REAL' in a['summary']
    assert R['acctPaper']['mode'] == 'paper' and 'Paper (simulated)' in R['acctPaper']['summary']


# ── 15-17) espacio, demo, interfaz ──
def test_space_summary_never_reads_fallback_numbers(R):
    f = R['spaceFb']
    assert f['success'] is False and f['unavailable'] is True and '7134' not in json.dumps(f) and '7.134' not in json.dumps(f)
    s = R['space']
    assert s['success'] and s['source'] == 'celestrak' and 'as_of' in s and s['focus'] == {'name': 'Starlink', 'count': 8800}
    assert R['demo']['success'] and R['demoCalls'] == 1


def test_control_interface_actions_never_leave_the_os(R):
    c, rec = R['ctl'], R['ctlRec']
    for k in ('new_conversation', 'arrange_windows', 'close_all_windows', 'minimize_all_windows', 'simple_mode', 'pro_mode',
              'dark_theme', 'dark_theme_2', 'light_theme', 'english', 'spanish'):
        assert c[k]['success'] is True and c[k]['done'], k
    assert c['classic_view']['success'] is False
    assert rec['newConv'] == 1 and rec['closed'] == 0
    assert ['arrange', True] in rec['desk'] and ['closeAll'] in rec['desk']
    assert ['min', 'kd1'] in rec['desk'] and ['min', 'kd2'] in rec['desk'] and ['min', 'kd3'] not in rec['desk']
    assert rec['prefs'] == [{'mode': 'simple'}, {'mode': 'pro'}]
    assert rec['theme'] == 2                                                # oscuro (cambia), oscuro otra vez (no), claro (cambia)
    assert rec['lang'] == 1                                                 # inglés (cambia); español ya activo → nada
    assert c['english']['done'] == 'The app is now in English.' and c['spanish']['done'] == 'La app quedó en español.'


def test_context_update_payload(R):
    t = R['ctx']
    assert t.startswith('[CONTEXT_UPDATE] ')
    d = json.loads(t[len('[CONTEXT_UPDATE] '):])
    assert set(d) == {'app', 'interface', 'lang', 'open_windows', 'focused_window', 'selected_company', 'invoked_agent',
                      'explain_mode', 'money_mode'}
    assert d['app'] == 'Khipus Finance Intelligence' and d['interface'] == 'Khipus OS' and d['lang'] == 'es'
    assert d['open_windows'] == ['En una mirada', 'X-Ray'] and d['focused_window'] == 'X-Ray'   # sin DOM: su título; minimizadas fuera
    assert d['invoked_agent'] == 'Cadena' and d['explain_mode'] == 'simple' and d['money_mode'] in ('live', 'paper', 'practice', 'none')


# ── alias de nombres retirados ──
def _alias(R, name, i=0):
    hits = [a for a in R['alias'] if a['name'] == name]
    return hits[i]


def test_every_retired_alias_still_works(R):
    names = {a['name'] for a in R['alias']}
    assert names == set(RETIRED)
    for a in R['alias']:
        assert a['n'] == 1, a['name']
        assert 'Unknown tool' not in a['raw'] and 'desconocida' not in a['raw'], a['name']
        _clean_text(a['raw'])
    assert R['aliasPosts'] == 0 and R['aliasClosed'] == 0                   # ningún alias envía órdenes ni cierra el OS


def test_retired_aliases_map_to_closest_new_handler(R):
    assert _alias(R, 'open_cockpit')['body'] == {'success': True, 'opened': 'Khipus OS'}
    assert _alias(R, 'switch_tab', 0)['scr'] == ['graph'] and _alias(R, 'switch_tab', 1)['scr'] == ['portfolios']
    assert _alias(R, 'show_chart')['stage'] == [['terminal', {'ticker': 'NVDA'}]]
    assert _alias(R, 'open_terminal')['stage'] == [['terminal', {'ticker': 'NVDA'}]]
    assert _alias(R, 'navigate_to_company')['stage'] == [['graph', 'nvidia']]
    assert _alias(R, 'open_xray')['stage'] == [['xray', 'nvidia']] and _alias(R, 'open_second_brain')['stage'] == [['xray', 'nvidia']]
    assert _alias(R, 'open_dossier')['surf'] == [['dossier', 'openai']]   # privadas también
    rs = _alias(R, 'get_risk_score')['body']
    assert rs['success'] is True and rs['company'] == 'NVIDIA' and rs['nrs'] == 42
    sc = _alias(R, 'get_supply_chain_links')
    assert sc['osw'] == [['supplychain', {'id': 'nvidia'}]] and sc['body']['facts']['suppliers'] == ['TSMC']
    assert _alias(R, 'get_news')['cv'][0][0] == '@noticias: Últimas noticias de NVIDIA'
    assert _alias(R, 'get_market_summary')['scr'] == ['market'] and _alias(R, 'get_portfolio_risk')['scr'] == ['risk']
    assert 'semis' in _alias(R, 'list_companies')['cv'][0][0]
    for n in ('get_opportunities', 'show_insights', 'show_matrices', 'get_nrs_top10'):
        assert _alias(R, n)['stage'][0][0] == 'insights', n
    top = _alias(R, 'get_nrs_top10')['body']['highest_risk']
    assert top[0] == {'company': 'TSMC', 'nrs': 71} and len(top) == 5
    st = _alias(R, 'run_stress_test')
    assert st['sim'][0] == {'targets': ['nvidia'], 'kind': 'collapse', 'severity': 100}
    assert st['body']['kind'] == 'collapse' and st['body']['severity'] == 100
    assert _alias(R, 'run_simulation')['asim'][0][0].startswith('Crisis en Taiwán.')
    assert _alias(R, 'deep_research')['th'] == [['nvidia', 'es']]
    assert _alias(R, 'deep_analysis')['surf'] == [['deep', 'cobre']]
    pt = _alias(R, 'place_paper_trade')['body']
    assert pt['needs_confirmation'] is True and pt['mode'] == 'live' and 'DINERO REAL' in pt['summary']
    assert _alias(R, 'place_trade')['body']['success'] is True
    assert _alias(R, 'get_portfolio_status')['body']['mode'] == 'live'


def test_slow_alias_uses_the_old_agent_timeout(R):
    assert R['newsBefore'] == 0
    assert len(R['newsAfter']) == 1 and R['newsAfter'][0]['pending'] is True


def test_unknown_tool_is_bilingual(R):
    u = R['unknownEn']
    assert u['success'] is False and u['error'] == 'Unknown tool: nope_tool'


# ═══════════════════════════════ la Cabina REAL en Chromium ═══════════════════════════════
PAGE = r"""<!doctype html><html lang="es"><head><meta charset="utf-8"><style>html,body{margin:0;height:100%;font-family:system-ui}</style>
</head><body><main id="mainmap" style="display:flex"><div>mapa</div></main>
<script>
window.LANG = 'es';
window.NODES = [
  { id: 'Nvidia', label: 'Nvidia', mkt: 'NVDA', cat: 'gpu', margin: 0.55, growth: '🟢' },
  { id: 'TSMC', label: 'TSMC', mkt: 'TSM', cat: 'foundry', margin: 0.4, growth: '🟢' },
  { id: 'OpenAI', label: 'OpenAI', cat: 'lab', margin: -0.2, growth: '🟢' },
  { id: 'Microsoft', label: 'Microsoft', mkt: 'MSFT', cat: 'cloud', margin: 0.45, growth: '🟢' },
  { id: 'AMD', label: 'AMD', mkt: 'AMD', cat: 'gpu', margin: 0.2, growth: '🟡' }];
window.NODE_BY_ID = {}; window.NODES.forEach(function (n) { window.NODE_BY_ID[n.id] = n; });
window.LINKS = [
  { source: 'TSMC', target: 'Nvidia', type: 'supply', w: 9 },
  { source: 'Nvidia', target: 'OpenAI', type: 'supply', w: 8 },
  { source: 'Nvidia', target: 'Microsoft', type: 'supply', w: 7 },
  { source: 'Microsoft', target: 'OpenAI', type: 'cloud', w: 8 }];
window.SECTORS9 = {}; window.CAT_TO_SECTOR = {};
window.computeNRS = function () { return 40; };
window.__recolor = [];
window._liveRecolorByImpact = function (m, dir) { window.__recolor.push({ dir: dir, n: m && m.size }); };
window.jumpTo = function () {};
window.__chatBodies = [];
</script></body></html>"""

REPLY = {'answer': '**Nvidia** depende de TSMC [E1] para fabricar sus chips [S2, S3].', 'actions': [],
         'agents_used': [{'agent': 'cadena', 'ok': True, 'note_es': 'Miró la cadena', 'note_en': 'Checked the chain'}],
         'sources': [{'label': 'Catálogo', 'as_of': '2026-10-11'}], 'tools_used': [{'name': 'get_supply_chain', 'ok': True}]}


def _chromium(p):
    for kw in ({}, {'executable_path': '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', 'args': ['--no-sandbox']}):
        try:
            return p.chromium.launch(**kw)
        except Exception:  # noqa: BLE001
            continue
    return None


@pytest.fixture(scope='module')
def browser():
    pw = pytest.importorskip('playwright.sync_api')
    with pw.sync_playwright() as p:
        b = _chromium(p)
        if not b:
            pytest.skip('Chromium no disponible')
        yield b
        b.close()


HOT_VIEW = {'name': 'impact', 'generation': 'g7.rA.c1.pg', 'graph_version': 7, 'source': 'pg', 'age_ms': 4000, 'stale': False}


def _hot_reply(route, path):
    """/api/hot/* con el contrato del servidor (paso 13): impacto del motor único; 'up' aún no → 400 direction."""
    req = route.request
    if path == '/api/hot/scenario':
        body = json.loads(req.post_data or '{}')
        if body.get('direction') == 'up':
            return route.fulfill(status=400, content_type='application/json', body=json.dumps(
                {'error': "direction 'up' todavía no está disponible", 'error_en': "direction 'up' is not available yet", 'param': 'direction'}))
    if path.startswith('/api/hot/impact/'):
        oid = path.rsplit('/', 1)[1]
        m = re.search(r'severity=(\d+)', req.url)
        k = int(m.group(1)) / 100 if m else 1.0
        vict = [v for v in ({'id': 'OpenAI', 'label': 'OpenAI', 'pct': round(60 * k, 2), 'hop': 1},
                            {'id': 'Microsoft', 'label': 'Microsoft', 'pct': round(30 * k, 2), 'hop': 1},
                            {'id': 'AMD', 'label': 'AMD', 'pct': round(2 * k, 2), 'hop': 2}) if v['id'] != oid]
        data = {'id': oid, 'severity': round(k * 100), 'affected': len(vict), 'reach_1': sum(1 for v in vict if v['pct'] >= 1),
                'reach_10': sum(1 for v in vict if v['pct'] >= 10), 'sum_impact': round(sum(v['pct'] for v in vict) / 100, 4),
                'by_hop': {'1': 2, '2': 1}, 'victims': vict}
        return route.fulfill(status=200, content_type='application/json', body=json.dumps({'data': data, 'view': HOT_VIEW}),
                             headers={'ETag': '"impact:%s"' % HOT_VIEW['generation'], 'X-Khipu-Graph-Version': '7'})
    return route.fulfill(status=503, content_type='application/json', body='{"error":"sin servidor"}')


def _page(browser, lang='es'):
    c = browser.new_context(viewport={'width': 1440, 'height': 900}, service_workers='block')
    seen = []

    def handler(route):
        path = route.request.url[len('http://khipu.test'):].split('?')[0]
        if path in ('', '/'):
            return route.fulfill(status=200, content_type='text/html', body=PAGE.replace("window.LANG = 'es'", "window.LANG = '%s'" % lang))
        if path == '/api/khipu/chat':
            seen.append(json.loads(route.request.post_data or '{}'))
            return route.fulfill(status=200, content_type='application/json', body=json.dumps(REPLY))
        if path.startswith('/api/hot/'):
            return _hot_reply(route, path)
        return route.fulfill(status=503, content_type='application/json', body='{"error":"sin servidor"}')
    c.route('http://khipu.test/**', handler)
    pg = c.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://khipu.test/')
    for p in ('toast.js', 'agents_registry.js', 'hotclient.js', 'mascot.js', 'desktop.js', 'khipu_chat.js', 'statematrix.js',
              'trade.js', 'voice.js', 'cockpit.js'):
        pg.add_script_tag(content=_r('engine', p))
    pg.evaluate('BixbyCockpit.open()')
    pg.wait_for_timeout(250)
    # socket de voz falso (la herramienta responde por aquí)
    pg.evaluate("""() => { BixbyVoice.ws = { readyState: 1, sent: [], send(d) { this.sent.push(JSON.parse(d)); }, close() {} }; }""")
    return c, pg, errs, seen


_CALL = """async ([name, params]) => {
  const id = 'b' + Math.random().toString(36).slice(2);
  BixbyVoice._handleToolCall({ tool_name: name, tool_call_id: id, parameters: params });
  for (let i = 0; i < 100; i++) {
    const m = BixbyVoice.ws.sent.find(x => x.tool_call_id === id);
    if (m) return JSON.parse(m.result);
    await new Promise(r => setTimeout(r, 50));
  }
  return null;
}"""


def test_navegador_pregunta_hablada_se_ve_en_el_chat_del_centro(browser):
    c, pg, errs, seen = _page(browser)
    body = pg.evaluate(_CALL, ['ask_khipu_brain', {'question': '¿de quién depende Nvidia?', 'agent': 'cadena'}])
    assert body and body['success'] is True and 'consulted' not in body
    assert body['answer'] == 'Nvidia depende de TSMC para fabricar sus chips.'
    assert body['agents'] == ['Cadena']
    assert seen and seen[-1]['message'].startswith('@cadena: ') and seen[-1]['deadline_s'] == 55
    pg.wait_for_timeout(200)
    th = pg.evaluate("""() => { const t = document.getElementById('bcp-thread');
      const u = t.querySelector('.kc-user.kc-voice'), mk = u && u.querySelector('.kc-vmark'), bot = t.querySelector('.kc-bot:not(.kc-pending)');
      return { inCenter: !!t.closest('#kd-center'), user: u ? u.textContent : null, mark: mk ? mk.getAttribute('aria-label') : null,
               bot: bot ? bot.textContent : null, pending: t.querySelectorAll('.kc-pending').length }; }""")
    assert th['inCenter'] is True
    assert th['user'] and '¿de quién depende Nvidia?' in th['user'] and th['mark'] == 'Pregunta dicha por voz'
    assert th['bot'] and 'depende de TSMC' in th['bot'] and th['pending'] == 0
    assert pg.evaluate('BixbyCockpit.isOpen()') is True
    assert not errs, errs
    c.close()


def test_navegador_la_voz_y_la_ventana_dicen_el_mismo_numero_del_motor_del_servidor(browser):
    c, pg, errs, _ = _page(browser)
    body = pg.evaluate(_CALL, ['run_live_simulation', {'company_name': 'Nvidia', 'kind': 'price', 'severity': 60}])
    assert body['success'] and body['severity'] == 60 and body['affected'] == 3 and body['engine_generation'] == 'g7.rA.c1.pg'
    assert body['opened'] == 'Shock de precio · Nvidia'
    assert body['most_impacted'][0] == {'company': 'OpenAI', 'impact_pct': 36}            # 60 % × 0,6 del servidor
    pg.wait_for_timeout(300)
    w = pg.evaluate("""() => { const w = document.querySelector('.kd-win[data-kind="sim"]'); if (!w) return null;
      const sev = w.querySelector('.kos-sim-sev'), stat = w.querySelector('.kos-sim-reach'), st = w.querySelector('.kos-sim-stamp');
      const task = [...document.querySelectorAll('.kd-task .tx')].map(x => x.textContent);
      return { title: w.querySelector('.kd-name').textContent, sev: sev && sev.getAttribute('data-sev'), affected: stat && stat.textContent,
               stamp: st && st.textContent, task }; }""")
    assert w, 'no se abrió la ventana de la simulación'
    assert w['title'] == 'Shock de precio · Nvidia' and w['sev'] == '60'
    assert int(w['affected']) == body['affected'] == 3                         # la voz dice lo que muestra la ventana
    assert w['stamp'].startswith('g7 · base')                                  # versión del grafo y edad, discreto
    assert 'Shock de precio · Nvidia' in w['task']
    # «Ver en el mapa»: NO cierra Khipus OS — abre la ventana del grafo y re-colorea con la MISMA respuesta
    pg.evaluate("() => window._cockpitMapSim('Nvidia', 'price', 60)")
    pg.wait_for_timeout(600)
    assert pg.evaluate('BixbyCockpit.isOpen()') is True
    assert pg.evaluate("""() => !!document.querySelector('.kd-win[data-kind="graph"]')""") is True
    rc = pg.evaluate('window.__recolor')
    assert rc and rc[-1]['dir'] == 'down' and rc[-1]['n'] == 4             # Nvidia + 3 del servidor
    # auge de demanda: el servidor aún no lo calcula → se dice, sin cifras ni ventana con números
    n0 = len(rc)
    up = pg.evaluate(_CALL, ['run_live_simulation', {'company_name': 'Nvidia', 'kind': 'demand', 'severity': 60}])
    assert up['success'] is False and up['unsupported'] is True and 'No mostramos cifras inventadas' in up['error']
    pg.evaluate("() => window._cockpitMapSim('Nvidia', 'demand', 60)")
    pg.wait_for_timeout(600)
    assert len(pg.evaluate('window.__recolor')) == n0                          # nada que pintar
    assert not errs, errs
    c.close()


def test_navegador_ingles_titulo_y_control_de_interfaz(browser):
    c, pg, errs, _ = _page(browser, lang='en')
    body = pg.evaluate(_CALL, ['run_live_simulation', {'company_name': 'TSMC', 'kind': 'price', 'severity': 30}])
    assert body['opened'] == 'Price shock · TSMC' and body['severity'] == 30
    pg.wait_for_timeout(300)
    r = pg.evaluate(_CALL, ['control_interface', {'action': 'close_all_windows'}])
    assert r['success'] is True and 'chat' in r['done']
    pg.wait_for_timeout(150)
    assert pg.evaluate("document.querySelectorAll('.kd-win').length") == 0
    assert pg.evaluate('BixbyCockpit.isOpen()') is True                     # nunca sale del OS
    assert not errs, errs
    c.close()


def test_zoom_del_mapa_ignora_transformaciones_no_finitas():
    """control_interface minimize_all_windows justo después de abrir el mapa: la transición del zoom de d3 daba
    translate(NaN,NaN) (~20-30 errores en la consola). El manejador ignora ese fotograma."""
    html = open(os.path.join(ROOT, 'app.html'), encoding='utf-8').read()
    i = html.index("const zoom = d3.zoom().scaleExtent([.3,3.5])")
    line = html[i:html.index('\n', i)]
    assert 'isFinite(t.x)&&isFinite(t.y)&&isFinite(t.k)' in line and "root.attr('transform',t)" in line


# ── L4-12 (lote I1): el agente de voz recibe la orden de repetir las cifras TAL CUAL ──
def test_brain_and_company_info_tell_the_agent_to_say_figures_exactly(R):
    es = R['brain']['body']['say_figures']
    assert 'EXACTAMENTE' in es and 'no redondees' in es and 'answer' in es
    assert 'EXACTLY' in R['brainClassic']['say_figures']                    # vista clásica, en inglés
    for i in (R['info'], R['infoPriv']):
        assert 'EXACTAMENTE' in i['say_figures'] and 'si falta un dato' in i['say_figures']
