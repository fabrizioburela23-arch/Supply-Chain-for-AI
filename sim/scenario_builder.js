// sim/scenario_builder.js — Constructor de seeds para simulaciones MiroFish (Khipu Finance)
// Genera el "seed" textual que alimenta a MiroFish con contexto realista:
//   geopolítica + sentimiento social + precedentes históricos + perfiles de agentes.
// Incluye 5 escenarios predefinidos listos para el demo.
//
// Depende de app.html: NODE_BY_ID, NODE_META, MKT, Keys, DataLayer, nf

// ── A) Contexto geopolítico ──────────────────────────────────────────────────
function buildGeopoliticalContext() {
  return `
## Geopolitical Context (2026)
### Active Tensions
- US-China tech decoupling: SMIC, HiSilicon, YMTC on Entity List
- Taiwan Strait: military exercises, insurance rates for semiconductors elevated
- EU CHIPS Act: €43B committed, TSMC Dresden + Rapidus in ramp
- India PLI: Micron ($2.75B), Samsung, Foxconn attracted
### Export Control Status
- ASML: cannot ship EUV to China (2023), DUV restricted (2024)
- NVIDIA: H20 restricted to China (2024), A800/H800 banned
- AMAT/Lam/KLA: 14nm+ equipment restricted to China
### Energy Geopolitics
- Nuclear PPA surge: Microsoft, Amazon, Google competing for firm power
- Gas turbine backlog: GE Vernova sold out to 2029
### Space Geopolitics
- Starlink: denied service in Iran, North Korea, Russia
- Starshield: classified US DoD constellation
- Chinese space: Landspace/CAS competing in LEO
`;
}

// ── B) Contexto social / sentimiento ─────────────────────────────────────────
async function buildSocialContext(nodeIds) {
  let ctx = `
## Market Social Sentiment
### Key narratives in social media:
- "AI bubble" narrative gaining traction after corrections
- Retail investors buying RKLB / space names on every dip
- Semiconductor stocks oversold by sentiment despite strong fundamentals
- SpaceX IPO speculation driving related stocks (RKLB, ASTS)
`;
  try {
    const base = (typeof BASE !== 'undefined') ? BASE : '';
    const sample = (nodeIds || []).slice(0, 2);
    for (const id of sample) {
      const n = NODE_BY_ID[id];
      if (!n) continue;
      const r = await fetch(`${base}/api/news/gdelt/${encodeURIComponent(n.label)}`);
      if (r.ok) {
        const arts = await r.json();
        if (arts.length) {
          const avgTone = arts.reduce((s, a) => s + (a.sentiment || 0), 0) / arts.length;
          ctx += `\n### GDELT tone for ${n.label}: ${avgTone.toFixed(2)} (${arts.length} articles)\n`;
        }
      }
    }
  } catch {}
  return ctx;
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
async function buildMiroFishSeed(scenarioConfig) {
  const {
    title, description, nodes, question,
    includeGeopolitics = true, includeSocial = true, includeHistory = true,
  } = scenarioConfig;

  let seed = `# ${title}\n## Financial Simulation Scenario — Khipu Finance Platform\n\n`;
  seed += `## Event Description\n${description}\n\n`;
  seed += `## Key Players (Agent Profiles)\n\n`;

  (nodes || []).forEach(n => {
    const meta = (typeof NODE_META !== 'undefined' && NODE_META[n.id]) || {};
    const q = (typeof MKT !== 'undefined' && MKT.quotes[n.mkt]) || {};
    seed += `### ${n.label} (${n.ticker || 'PRIVATE'})\n`;
    seed += `- Role: ${(typeof nf === 'function' ? nf(n, 'role') : n.role) || ''}\n`;
    seed += `- Current price: ${q.close ? '$' + q.close : 'N/A'}\n`;
    seed += `- Market cap: ${meta.mktcap_b ? '$' + meta.mktcap_b + 'B' : (n.preipo ? n.ticker : 'Private')}\n`;
    seed += `- Geo risk: ${n.geo_risk || meta.geo_risk || 'Minimal'}\n`;
    seed += `- Competitive moat: ${((typeof nf === 'function' ? nf(n, 'moat') : n.moat) || '').slice(0, 200)}\n\n`;
  });

  if (includeGeopolitics) seed += buildGeopoliticalContext();
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
    return buildMiroFishSeed({
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
    return buildMiroFishSeed({ title: p.title, description: p.description, nodes, question: p.question });
  },

  PRESETS: {
    taiwan_conflict: {
      title: 'Taiwan Strait Crisis — TSMC Production Halt',
      description: 'Military conflict forces TSMC to halt 3nm/2nm production for 90 days. Starshield/DoD assets on alert.',
      nodeIds: ['TSMC', 'Nvidia', 'Apple', 'AMD', 'ASML', 'SKHynix', 'Samsung', 'SpaceX', 'AST_SpaceMobile'],
      question: 'What happens to GPU supply, AI lab timelines, and stock valuations? Who benefits from reshoring?',
    },
    china_chip_ban_total: {
      title: 'Complete Chip Export Ban — All Nvidia/AMD to China',
      description: 'BIS emergency order bans all Nvidia, AMD, Intel chips to China including previously allowed H20/MI300.',
      nodeIds: ['Nvidia', 'AMD', 'Intel', 'SMIC', 'HiSilicon', 'Cambricon', 'Huawei'],
      question: 'How does China respond? What happens to Nvidia revenue and Chinese AI? Who wins?',
    },
    hbm_shortage_2027: {
      title: 'HBM Memory Severe Shortage — Fab Fire + Qualification Delay',
      description: 'SK Hynix fab fire reduces HBM capacity 40%. Micron HBM4 qualification delayed 2 quarters.',
      nodeIds: ['SKHynix', 'Micron', 'Samsung', 'Nvidia', 'AMD', 'Dell', 'Microsoft'],
      question: 'How does the HBM shortage cascade through AI infrastructure? Impact on Nvidia shipments?',
    },
    openai_ipo_impact: {
      title: 'OpenAI IPO at $250B — Market Revaluation',
      description: 'OpenAI goes public at $250B valuation. Market digests AI profitability timeline.',
      nodeIds: ['OpenAI', 'Microsoft', 'Anthropic', 'Nvidia', 'Oracle', 'Meta', 'Alphabet'],
      question: 'How does the OpenAI IPO reshape capital flows, valuations, and competitive dynamics?',
    },
    starshield_reveal: {
      title: 'Starshield Pentagon Reveal — SpaceX Defense Business',
      description: 'Pentagon reveals Starshield is 3x larger than reported, with $15B classified revenue. SpaceX valued at $500B.',
      nodeIds: ['SpaceX', 'RocketLab', 'Anduril', 'ShieldAI', 'Iridium', 'Kratos_Defense', 'Nvidia'],
      question: 'How does the Starshield revelation affect the space defense sector? Who is threatened vs benefited?',
    },
  },
};

window.ScenarioBuilder = ScenarioBuilder;
window.buildMiroFishSeed = buildMiroFishSeed;
