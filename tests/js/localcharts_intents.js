global.window = { LANG: 'es', NODES: [{id:'Nvidia',label:'Nvidia',mkt:'NVDA',cat:'fabless',margin:0.6,country:'EEUU'},{id:'Lockheed',label:'Lockheed Martin',mkt:'LMT',cat:'defense_prime',margin:0.1,country:'EEUU'}],
  CAT_TO_SECTOR: {fabless:'diseno', defense_prime:'defensa'}, SECTORS9: {diseno:{label:'Diseño & IP'}, defensa:{label:'Defensa'}}, NODE_META: {} };
window.NODE_BY_ID = {}; window.NODES.forEach(n => window.NODE_BY_ID[n.id] = n);
global.document = { head: null, getElementById: () => null, querySelectorAll: () => [] };
global.localStorage = { getItem: () => null, setItem: () => {} };
global.fetch = async (u) => ({ json: async () => (u.includes('GC%3DF') ? { s: 'ok', c: [2000, 2100, 2200, 2300, 2400, 2500], t: [1, 2, 3, 4, 5, 6].map(x => 1.7e9 + x * 86400) } : { s: 'no_data' }) });
require(process.argv[2] + '/engine/localcharts.js');
const K = window.KhipuLocalCharts;
(async () => {
  const out = {};
  for (const q of ['precio del oro último año', 'top 5 semiconductores por margen', 'margen promedio por sector']) {
    const r = K.route(q); out[q] = { intent: r.intent, local: r.local, sectors: r.sectors || null, commodity: r.commodity ? r.commodity.sym : null };
  }
  const g = await K.tryAsync('precio del oro último año');
  out.gold = g ? { type: g.type, title: g.title, n: g.data[0].values.length } : null;
  process.stdout.write(JSON.stringify(out), () => process.exit(0));
})();
