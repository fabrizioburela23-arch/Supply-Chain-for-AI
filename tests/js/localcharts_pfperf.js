// Rendimiento de mi cartera (engine/localcharts.js): Σ acciones × cierre real, sin IA.
global.window = { LANG: 'es', NODES: [{id:'Nvidia',label:'Nvidia',mkt:'NVDA',cat:'fabless'},{id:'Lockheed',label:'Lockheed Martin',mkt:'LMT',cat:'defense_prime'},{id:'OpenAI',label:'OpenAI',cat:'lab'}],
  CAT_TO_SECTOR: {}, SECTORS9: {}, NODE_META: {},
  MKT: { pos: { Nvidia: { sh: 2, bp: 100 }, Lockheed: { sh: 1, bp: 400 }, OpenAI: { sh: 1, bp: 10 } }, quotes: { NVDA: { close: 130, src: 'finnhub' } } } };
window.quotePx = q => q.close;
window.NODE_BY_ID = {}; window.NODES.forEach(n => window.NODE_BY_ID[n.id] = n);
global.document = { head: null, getElementById: () => null, querySelectorAll: () => [] };
global.localStorage = { getItem: () => null, setItem: () => {} };
const D = 86400, T0 = 1.75e9 - (1.75e9 % D);
const CANDLES = {
  NVDA: { s: 'ok', c: [100, 110, 120], t: [T0, T0 + D, T0 + 2 * D] },
  LMT:  { s: 'ok', c: [400, 410], t: [T0, T0 + 2 * D] },          // falta el día 2 → arrastra 400
};
global.fetch = async (u) => ({ json: async () => { const m = /candles\/([^?]+)/.exec(u); return CANDLES[decodeURIComponent(m[1])] || { s: 'no_data' }; } });
require(process.argv[2] + '/engine/localcharts.js');
const K = window.KhipuLocalCharts;
(async () => {
  const out = {};
  for (const q of ['rendimiento de mi cartera', 'cuánto ganó mi cartera este año', 'how is my portfolio doing', 'mi cartera', 'por qué perdió mi cartera']) {
    const r = K.route(q); out[q] = { intent: r.intent, local: r.local, pfPerf: !!r.pfPerf };
  }
  const g = await K.tryAsync('rendimiento de mi cartera 3 meses');
  out.chart = g ? { type: g.type, title: g.title, sub: g.subtitle, vals: g.data[0].values, note: g.note } : null;
  process.stdout.write(JSON.stringify(out), () => process.exit(0));
})();
