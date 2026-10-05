// sim/scenario_builder.js — Constructor de seeds para las simulaciones (Khipu Finance)
// Genera el "seed" textual que alimenta a los motores de simulación con contexto realista:
//   geopolítica + sentimiento social + precedentes históricos + perfiles de agentes.
// Incluye 5 escenarios predefinidos listos para el demo.
//
// Depende de app.html: NODE_BY_ID, NODE_META, MKT, Keys, DataLayer, nf

// ── A) Contexto geopolítico EN VIVO (2026-10-05) ─────────────────────────────
// Antes era un bloque FIJO ("Geopolitical Context (2026)") que los agentes de IA leían
// como actual. Ahora sale del World Monitor (eventos de hoy, índice GPR, reglas del
// BIS/OFAC, tráfico por estrechos) con fecha y fuente. Lo estructural (controles de
// exportación vigentes) va aparte y rotulado como "fondo", no como noticia.
const STRUCTURAL_BACKGROUND = `
### Structural background (durable, not news — verify before relying on it)
- US export controls restrict advanced AI chips and EUV/DUV tools to China (Entity List: SMIC, HiSilicon, YMTC…).
- Leading-edge foundry capacity is concentrated in Taiwan (TSMC); HBM memory in Korea (SK Hynix, Samsung) and Micron.
- AI data-center power demand is driving nuclear/gas PPAs and gas-turbine backlogs.
`;

async function _sbJSON(url, ms) {
  const base = (typeof BASE !== 'undefined') ? BASE : '';
  const ctl = typeof AbortController !== 'undefined' ? new AbortController() : null;
  const t = ctl ? setTimeout(() => { try { ctl.abort(); } catch (e) {} }, ms || 6000) : null;
  try {
    const r = await fetch(base + url, ctl ? { signal: ctl.signal } : undefined);
    return r.ok ? await r.json() : null;
  } catch (e) { return null; } finally { if (t) clearTimeout(t); }
}

async function buildGeopoliticalContext() {
  const [brief, gpr, policy] = await Promise.all([
    _sbJSON('/api/world/brief?window=7d&n=10'), _sbJSON('/api/world/gpr'), _sbJSON('/api/world/policy?limit=6')]);
  let ctx = `\n## Geopolitical Context (LIVE, ${new Date().toISOString().slice(0, 10)})\n`;
  if (gpr && gpr.ok && gpr.daily) {
    const d = gpr.daily;
    ctx += `- Geopolitical Risk Index (Caldara-Iacoviello, Fed; 100 = 1985-2019 avg): ${d.value} on ${d.date} (30-day avg ${d.avg30}; higher than ${d.percentile_1y}% of the last year).\n`;
  }
  const items = (brief && brief.items) || [];
  if (items.length) {
    ctx += `### Most relevant events now (World Monitor, severity 0-100)\n`;
    items.slice(0, 8).forEach(it => {
      ctx += `- [${it.layer}] ${it.title_en || it.title} — severity ${it.severity}` + (it.time ? `, ${String(it.time).slice(0, 10)}` : '') +
        (it.source_en || it.source ? `, source: ${it.source_en || it.source}` : '') + `\n`;
    });
  }
  const pol = (policy && policy.items) || [];
  if (pol.length) {
    ctx += `### Latest US export-control / sanctions documents (Federal Register)\n`;
    pol.slice(0, 5).forEach(p => { ctx += `- ${String(p.time || '').slice(0, 10)} ${p.agency}: ${p.title}\n`; });
  }
  if (!items.length && !(gpr && gpr.ok)) ctx += `- (Live geopolitical feeds unavailable right now — do not assume current events.)\n`;
  return ctx + STRUCTURAL_BACKGROUND;
}

// ── B) Sentimiento EN VIVO (GDELT) — antes eran narrativas inventadas ────────
async function buildSocialContext(nodeIds) {
  let ctx = `\n## Market Sentiment (LIVE news tone, GDELT)\n`;
  let any = false;
  try {
    const base = (typeof BASE !== 'undefined') ? BASE : '';
    const sample = (nodeIds || []).slice(0, 3);
    for (const id of sample) {
      const n = NODE_BY_ID[id];
      if (!n) continue;
      const r = await fetch(`${base}/api/news/gdelt/${encodeURIComponent(n.label)}`);
      if (r.ok) {
        const arts = await r.json();
        if (arts.length) {
          any = true;
          const avgTone = arts.reduce((s, a) => s + (a.sentiment || 0), 0) / arts.length;
          ctx += `- ${n.label}: average news tone ${avgTone.toFixed(2)} over ${arts.length} recent articles` +
            (arts[0] && arts[0].title ? ` (latest: "${String(arts[0].title).slice(0, 120)}")` : '') + `\n`;
        }
      }
    }
  } catch {}
  if (!any) ctx += `- (No live sentiment data right now — do not invent social-media narratives.)\n`;
  return ctx;
}

// valuación VERIFICADA / capitalización EN VIVO para los presets (antes: "OpenAI a $250B", "SpaceX a $500B")
function _sbValuation(id) {
  const pv = (window.PRIVATE_VALUATIONS && window.PRIVATE_VALUATIONS.entries || {})[id];
  const meta = (window.NODE_META || {})[id] || {};
  if (meta.mktcap_live && meta.mktcap_b) return `$${Math.round(meta.mktcap_b)}B live market cap`;
  if (pv && pv.label) return `${pv.label.split(' ')[0]} (last verified round, ${pv.as_of})`;
  return null;
}

// ── C) Precedentes históricos ────────────────────────────────────────────────
const HISTORICAL_PRECEDENTS = `
## Historical Precedents for Agent Calibration
### Supply Chain Shocks:
1. Huawei Entity List (May 2019): Qualcomm lost $8B revenue in 2 years; Huawei stockpiled 2 years of chips.
2. TSMC minor disruptions (2021): automotive chip shortage lasted 18 months; GM lost $2B revenue.
3. ASML DUV ban to China (2024): SMIC 7nm yield stayed below 40% vs TSMC 90%+.
4. COVID shortage (2020-22): 2-3 year lead times; automotive lost $210B revenue.
5. HBM shortage (2023-24): SK Hynix had 12-month waiting list; Nvidia Blackwell delayed partly due to HBM.
### Key Behavioral Patterns:
- Institutional investors: sell first, investigate later on supply shocks
- Retail investors: buy dips in established names (Nvidia, TSMC)
- Hedge funds: short downstream, long upstream on supply shocks
- Corporations: build 6-12 month inventory buffers after each shock
- Governments: accelerate reshoring spending after any shock
`;

// ── D) Construcción del seed completo ────────────────────────────────────────
async function buildPlayers(nodes) {
  let seed = '';
  // perfil de cada empresa con datos EN VIVO (2026-10-05: el informe decía "no tengo el dato en vivo de
  // Microsoft/Nvidia" porque aquí iba "Current price: N/A" — se leía q.close, que la cotización viva no trae)
  const lives = await Promise.all((nodes || []).slice(0, 10).map(n => n.mkt && !n.preipo
    ? _sbJSON('/api/company/live/' + encodeURIComponent(n.mkt), 6000) : Promise.resolve(null)));
  (nodes || []).forEach((n, i) => {
    const meta = (typeof NODE_META !== 'undefined' && NODE_META[n.id]) || {};
    const q = (typeof MKT !== 'undefined' && MKT.quotes && MKT.quotes[n.mkt]) || null;
    const lp = (lives[i] && lives[i].available) ? lives[i] : null;
    const px = lp && lp.price_usd != null ? lp.price_usd : (q && window.quotePx ? window.quotePx(q) : null);
    const cap = lp && lp.market_cap_usd_b != null ? lp.market_cap_usd_b : (meta.mktcap_live ? meta.mktcap_b : null);
    const pv = (window.PRIVATE_VALUATIONS && window.PRIVATE_VALUATIONS.entries || {})[n.id];
    const asof = (lp && lp.as_of) ? String(lp.as_of).slice(0, 16).replace('T', ' ') + ' UTC' : '';
    seed += `### ${n.label} (${n.mkt || (n.preipo ? 'PRIVATE' : n.ticker || 'PRIVATE')})\n`;
    seed += `- Role: ${(typeof nf === 'function' ? nf(n, 'role') : n.role) || ''}\n`;
    if (n.mkt && !n.preipo) {
      seed += `- LIVE price: ${px != null ? '$' + (+px).toFixed(2) : 'not available right now'}` +
        (lp && lp.change_pct != null ? ` (${lp.change_pct > 0 ? '+' : ''}${(+lp.change_pct).toFixed(2)}% today)` : '') + (asof ? ` — ${asof}` : '') + `\n`;
      seed += `- LIVE market cap: ${cap != null ? '$' + (+cap).toFixed(1) + 'B' : 'not available right now'}\n`;
      const om = lp && lp.operating_margin != null ? lp.operating_margin : (n.margin_live ? n.margin * 100 : null);
      const gq = lp && lp.revenue_growth_q != null ? lp.revenue_growth_q : (n.growth_live ? n.growth_live.pct : null);
      const rev = lp && lp.revenue_ttm_usd_b != null ? lp.revenue_ttm_usd_b : meta.revenue_ttm_usd_b;
      if (om != null) seed += `- LIVE operating margin (last 12 months): ${(+om).toFixed(1)}%\n`;
      if (gq != null) seed += `- LIVE revenue growth (last quarter vs a year ago): ${(+gq).toFixed(0)}%\n`;
      if (rev != null) seed += `- LIVE revenue (last 12 months): $${(+rev).toFixed(1)}B\n`;
      if (lp && lp.pe_forward != null) seed += `- Forward P/E: ${(+lp.pe_forward).toFixed(1)}\n`;
    } else {
      seed += `- Private: ${pv ? 'last verified valuation ' + pv.label + (pv.round ? ' (' + pv.round + ')' : '') : 'no verified valuation'}\n`;
    }
    seed += `- Geo risk: ${n.geo_risk || meta.geo_risk || 'Minimal'}\n`;
    seed += `- Competitive moat: ${((typeof nf === 'function' ? nf(n, 'moat') : n.moat) || '').slice(0, 200)}\n\n`;
  });

  return seed;
}

// CONTEXTO EN VIVO para el informe de la simulación "IA simple" (2026-10-05): antes la IA recibía SOLO la frase
// del escenario — ni las empresas, ni sus datos en vivo, ni la geopolítica — y respondía "no tengo el dato en vivo".
async function buildLiveReportContext(nodeIds) {
  const nodes = (nodeIds || []).map(id => (typeof NODE_BY_ID !== 'undefined' && NODE_BY_ID[id]) || null).filter(Boolean);
  let ctx = '';
  if (nodes.length) ctx += `## Key players — LIVE data (use these figures; do not say a figure is unavailable if it is here)\n\n` + await buildPlayers(nodes);
  ctx += await buildGeopoliticalContext();
  return ctx;
}

async function buildScenarioSeed(scenarioConfig) {
  const {
    title, description, nodes, question,
    includeGeopolitics = true, includeSocial = true, includeHistory = true,
  } = scenarioConfig;

  let seed = `# ${title}\n## Financial Simulation Scenario — Khipu Finance Platform\n\n`;
  seed += `## Event Description\n${description}\n\n`;
  seed += `## Key Players (Agent Profiles)\n\n`;

  seed += await buildPlayers(nodes);

  if (includeGeopolitics) seed += await buildGeopoliticalContext();
  if (includeSocial) seed += await buildSocialContext((nodes || []).map(n => n.id));
  if (includeHistory) seed += HISTORICAL_PRECEDENTS;

  seed += `
## Agent Personas to Generate
1. Institutional long-only fund manager (horizon 1-3y): sells positions exceeding risk limits, adds to quality dips.
2. Activist hedge fund (6-18m): shorts overleveraged companies, longs undervalued assets.
3. Supply chain executive (now-6m): dual-sources suppliers, builds inventory, renegotiates LTAs.
4. Government official (2-4y): emergency executive orders, ally consultations, CHIPS Act updates.
5. Retail investor (days-weeks): FOMO buying on dips, panic selling on bad news.
6. Corporate strategist (2-5y): CAPEX adjustments, geographic diversification.

## Simulation Objective
${question}

## Expected Outputs
- Price trajectory for each company (6-month forecast)
- Supply chain disruption score (1-10) per week
- Winner/loser identification with rationale
- Government policy response probability
- Probability distribution of outcomes (optimistic/base/pessimistic)
`;
  return seed;
}

// ── Builder principal + presets ──────────────────────────────────────────────
const ScenarioBuilder = {
  async buildFromNodes(nodeIds, question, includeRecentNews = true) {
    const nodes = (nodeIds || []).map(id => NODE_BY_ID[id]).filter(Boolean);
    return buildScenarioSeed({
      title: `Supply Chain Analysis: ${nodes.map(n => n.label).slice(0, 3).join(', ')}`,
      description: 'Analysis of supply chain dynamics and investment implications for the selected companies.',
      nodes,
      question: question || 'What are the investment implications and price trajectories?',
    });
  },

  async buildFromPreset(presetId) {
    const p = this.PRESETS[presetId];
    if (!p) throw new Error('Unknown preset: ' + presetId);
    const nodes = p.nodeIds.map(id => NODE_BY_ID[id]).filter(Boolean);
    return buildScenarioSeed({ title: p.title, description: p.description, nodes, question: p.question });
  },

  // factorId: ancla el preset a un Factor REAL de la ontología (se dispara
  // como what-if vía /api/matrix/factor/fire para contrastar la narrativa de
  // la IA con contagio determinista). Los presets hipotéticos (incendio HBM,
  // revelación Starshield) NO llevan factorId — no inventamos factores.
  PRESETS: {
    taiwan_conflict: {
      title: 'Taiwan Strait Crisis — TSMC Production Halt',
      description: 'Military conflict forces TSMC to halt 3nm/2nm production for 90 days. Starshield/DoD assets on alert.',
      nodeIds: ['TSMC', 'Nvidia', 'Apple', 'AMD', 'ASML', 'SKHynix', 'Samsung', 'SpaceX', 'AST_SpaceMobile'],
      question: 'What happens to GPU supply, AI lab timelines, and stock valuations? Who benefits from reshoring?',
      factorId: 'FACTOR_Taiwan_Tension',
    },
    china_chip_ban_total: {
      title: 'Complete Chip Export Ban — All Nvidia/AMD to China',
      description: 'BIS emergency order bans all Nvidia, AMD, Intel chips to China including previously allowed H20/MI300.',
      nodeIds: ['Nvidia', 'AMD', 'Intel', 'SMIC', 'HiSilicon', 'Cambricon', 'Huawei'],
      question: 'How does China respond? What happens to Nvidia revenue and Chinese AI? Who wins?',
      factorId: 'FACTOR_H20_Whiplash',
    },
    hbm_shortage_2027: {
      title: 'HBM Memory Severe Shortage — Fab Fire + Qualification Delay',
      description: 'SK Hynix fab fire reduces HBM capacity 40%. Micron HBM4 qualification delayed 2 quarters.',
      nodeIds: ['SKHynix', 'Micron', 'Samsung', 'Nvidia', 'AMD', 'Dell', 'Microsoft'],
      question: 'How does the HBM shortage cascade through AI infrastructure? Impact on Nvidia shipments?',
    },
    openai_ipo_impact: {
      title: 'OpenAI IPO — Market Revaluation',
      get description() {
        const v = _sbValuation('OpenAI');
        return 'OpenAI goes public' + (v ? ' near its ' + v : '') + '. Market digests the AI profitability timeline.';
      },
      nodeIds: ['OpenAI', 'Microsoft', 'Anthropic', 'Nvidia', 'Oracle', 'Meta', 'Alphabet'],
      question: 'How does the OpenAI IPO reshape capital flows, valuations, and competitive dynamics?',
      factorId: 'FACTOR_AIDebtLeverageCycle',
    },
    starshield_reveal: {
      title: 'Starshield Pentagon Reveal — SpaceX Defense Business',
      get description() {
        const v = _sbValuation('SpaceX');
        return 'Hypothetical: the Pentagon reveals Starshield is much larger than reported. SpaceX (listed as SPCX since Jun 2026' +
          (v ? ', ' + v : '') + ').';
      },
      nodeIds: ['SpaceX', 'RocketLab', 'Anduril', 'ShieldAI', 'Iridium', 'Kratos_Defense', 'Nvidia'],
      question: 'How does the Starshield revelation affect the space defense sector? Who is threatened vs benefited?',
    },
  },
};

window.ScenarioBuilder = ScenarioBuilder;
window.buildScenarioSeed = buildScenarioSeed;
window.buildLiveReportContext = buildLiveReportContext;
