// engine/secondbrain.js — Second Brain de 5 capas para Khipu Finance
// Al seleccionar una empresa, abre un panel con 5 capas de conocimiento:
//   1. Mercado (precio + sparkline + NRS)   2. Noticias (+ RAG insight)
//   3. Tesis (catalizadores + riesgos + IA)  4. Simulación (presets MiroFish)
//   5. Red (betweenness + cascada + desglose NRS)
//
// Depende de app.html: NODE_BY_ID, NODE_META, MKT, Keys, DataLayer, computeNRS,
//   getBetweenness, computeDownstream, LINKS, NODES, lid, esc, fmtN, fmtPct,
//   relTime, sentiment, nf, today, catColor/getCatColorHex, BASE

class SecondBrain {
  constructor(graph3d) {
    this.graph3d = graph3d;
    this.activeLayer = 1;
    this.activeNodeId = null;
  }

  _rag(path, body) {
    const base = (typeof BASE !== 'undefined') ? BASE : '';
    return fetch(`${base}/api/rag/${path}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  }

  async showNodeLayers(nodeId) {
    this.activeNodeId = nodeId;
    const n = NODE_BY_ID[nodeId];
    const el = document.getElementById('second-brain-panel');
    if (!el || !n) return;

    el.innerHTML = `
      <div style="padding:16px">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px">
          <span style="width:12px;height:12px;border-radius:50%;background:${typeof getCatColorHex==='function'?getCatColorHex(n.cat):typeof catColor==='function'?catColor(n.cat):'#888'};flex-shrink:0"></span>
          <h3 style="font-family:'Fraunces',serif;font-size:17px;font-weight:600;margin:0">${esc(n.label)}</h3>
          <span style="font-size:11px;color:var(--ink-3);font-family:'JetBrains Mono',monospace">${esc((n.ticker || '').split(' · ')[0] || '')}</span>
        </div>
        <div style="display:flex;gap:4px;margin-bottom:16px;flex-wrap:wrap">
          ${[['📊', 'Mercado', 1], ['📰', 'Noticias', 2], ['💡', 'Tesis', 3], ['🔮', 'Simulación', 4], ['🕸️', 'Red', 5]]
            .map(([icon, label, layer]) =>
              `<button class="sb-chip${this.activeLayer === layer ? ' active' : ''}"
                onclick="window.secondBrain.setNodeLayer('${nodeId}',${layer})"
                style="padding:5px 10px;font-size:12px;border:1px solid var(--line-2);border-radius:7px;background:${this.activeLayer === layer ? 'var(--surface-2)' : 'var(--surface)'};color:var(--ink-2);cursor:pointer">${icon} ${label}</button>`
            ).join('')}
        </div>
        <div id="brain-layer-content"></div>
      </div>
    `;
    await this._renderLayerContent(nodeId, this.activeLayer);
  }

  async setNodeLayer(nodeId, layer) {
    this.activeLayer = layer;
    document.querySelectorAll('#second-brain-panel .sb-chip').forEach((b, i) => {
      const on = i + 1 === layer;
      b.classList.toggle('active', on);
      b.style.background = on ? 'var(--surface-2)' : 'var(--surface)';
    });
    await this._renderLayerContent(nodeId, layer);
  }

  async _renderLayerContent(nodeId, layer) {
    const el = document.getElementById('brain-layer-content');
    if (!el) return;
    switch (layer) {
      case 1: await this._renderMarket(nodeId, el); break;
      case 2: await this._renderNews(nodeId, el); break;
      case 3: await this._renderThesis(nodeId, el); break;
      case 4: await this._renderSim(nodeId, el); break;
      case 5: await this._renderNetwork(nodeId, el); break;
    }
  }

  _nrsInfo(nodeId) {
    const v = (typeof computeNRS === 'function') ? computeNRS(nodeId) : 50;
    const total = typeof v === 'object' ? (v.total || 50) : v;
    const color = total >= 70 ? '#ef4444' : total >= 40 ? '#f59e0b' : '#22c55e';
    const label = total >= 70 ? 'ALTO' : total >= 40 ? 'MEDIO' : 'BAJO';
    return { total, color, label };
  }

  async _renderMarket(nodeId, el) {
    const n = NODE_BY_ID[nodeId];
    const meta = NODE_META[nodeId] || {};
    const q = n.mkt ? (MKT.quotes[n.mkt] || {}) : {};
    const chg = (q.close != null && q.prev) ? (q.close - q.prev) / q.prev : null;
    const nrs = this._nrsInfo(nodeId);

    el.innerHTML = `
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
        <div class="sb-card"><div class="sb-l">Precio Live</div>
          <div class="sb-v" style="color:${chg > 0 ? 'var(--up,#3DE0C8)' : chg < 0 ? 'var(--down,#FF6577)' : 'var(--ink)'}">${q.close != null ? '$' + fmtN(q.close) : n.preipo ? 'PRIVADA' : '—'}</div>
          <div class="sb-s">${chg != null ? (chg >= 0 ? '▲ ' : '▼ ') + fmtPct(Math.abs(chg)) : ''}</div></div>
        <div class="sb-card"><div class="sb-l">Market Cap</div>
          <div class="sb-v" style="font-size:15px">${meta.mktcap_b ? '$' + meta.mktcap_b + 'B' : (n.preipo ? n.ticker : '—')}</div></div>
        <div class="sb-card"><div class="sb-l">Revenue 2025</div>
          <div class="sb-v" style="font-size:13px">${esc(n.revenue_2025 || meta.revenue_2025 || '—')}</div></div>
        <div class="sb-card"><div class="sb-l">NRS Risk</div>
          <div class="sb-v" style="font-size:15px;color:${nrs.color}">${nrs.total}/100</div>
          <div class="sb-s" style="color:${nrs.color}">${nrs.label}</div></div>
      </div>
      <canvas id="sparkline-${nodeId}" height="80" style="width:100%;margin-top:12px"></canvas>
      ${n.mkt && typeof Keys !== 'undefined' && Keys.has('finnhub') ? '' : '<div style="font-size:11px;color:var(--ink-3);margin-top:8px">Configura Finnhub en ⚙ para ver el gráfico</div>'}
    `;
    if (n.mkt && typeof Keys !== 'undefined' && Keys.has('finnhub') && typeof Chart !== 'undefined') {
      this._drawSparkline(nodeId, n.mkt);
    }
  }

  async _drawSparkline(nodeId, ticker) {
    try {
      const now = Math.floor(Date.now() / 1000);
      const from = now - 90 * 86400;
      const r = await DataLayer._json(
        `https://finnhub.io/api/v1/stock/candle?symbol=${ticker}&resolution=W&from=${from}&to=${now}&token=${Keys.get('finnhub')}`
      );
      if (!r?.c?.length) return;
      const cv = document.getElementById(`sparkline-${nodeId}`);
      if (!cv) return;
      new Chart(cv.getContext('2d'), {
        type: 'line',
        data: {
          labels: r.t.map(t => new Date(t * 1000).toLocaleDateString()),
          datasets: [{
            data: r.c, borderColor: '#3DE0C8', borderWidth: 2, fill: true,
            backgroundColor: 'rgba(61,224,200,0.08)', pointRadius: 0, tension: 0.4,
          }],
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: { x: { display: false }, y: { display: false } },
        },
      });
    } catch {}
  }

  async _renderNews(nodeId, el) {
    const n = NODE_BY_ID[nodeId];
    el.innerHTML = '<div style="color:var(--ink-3);font-size:12px;padding:8px">Cargando noticias…</div>';
    try {
      let news = n.mkt && typeof Keys !== 'undefined' && Keys.has('finnhub') ? await DataLayer.news(n.mkt) : [];

      let ragInsight = '';
      try {
        const ragR = await this._rag('query/ai', {
          query: `Latest news and market sentiment for ${n.label}`,
          system: 'Summarize key recent developments in 2 sentences.',
        });
        if (ragR.ok) { const rj = await ragR.json(); ragInsight = rj.answer || ''; }
      } catch {}

      el.innerHTML = `
        ${ragInsight ? `<div style="background:var(--surface-2);border-radius:8px;padding:10px;font-size:12.5px;margin-bottom:10px"><b>🧠 RAG:</b> ${esc(ragInsight)}</div>` : ''}
        ${news.length === 0 ? '<div style="color:var(--ink-3);font-size:12px">Sin noticias disponibles</div>' :
          news.slice(0, 8).map(item => {
            const s = (typeof sentiment === 'function') ? sentiment(item.headline) : { cls: '', icon: '' };
            return `<a href="${esc(item.url)}" target="_blank" rel="noopener" style="display:block;padding:8px 0;border-bottom:1px solid var(--line);text-decoration:none;color:inherit">
              <div style="display:flex;gap:8px;font-size:10.5px;color:var(--ink-3);margin-bottom:3px">
                <span>${esc(item.source || '')}</span><span>${typeof relTime === 'function' ? relTime(item.datetime) : ''}</span>
                <span class="${s.cls}">${s.icon}</span></div>
              <div style="font-size:12.5px;color:var(--ink);line-height:1.4">${esc(item.headline)}</div></a>`;
          }).join('')}
      `;

      // Indexar noticias en RAG para futuras consultas (best-effort)
      if (news.length > 0) {
        this._rag('index/news', { items: news.map(i => ({ ...i, related: n.mkt })) }).catch(() => {});
      }
    } catch (e) {
      el.innerHTML = `<div style="color:var(--down,#FF6577);font-size:12px">${esc(String(e.message))}</div>`;
    }
  }

  async _renderThesis(nodeId, el) {
    const n = NODE_BY_ID[nodeId];
    el.innerHTML = `
      <div style="background:var(--surface-2);border-radius:8px;padding:12px;margin-bottom:10px">
        <div style="font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--ink-3);margin-bottom:4px">Tesis de Inversión</div>
        <div style="font-size:13px;line-height:1.5">${esc(n.thesis || (typeof nf === 'function' ? nf(n, 'moat') : n.moat) || '—')}</div>
      </div>
      ${(n.catalysts_2026 || []).length ? `
        <div style="margin-bottom:10px"><h4 style="font-size:12px;margin:0 0 4px">Catalizadores 2026</h4>
        ${n.catalysts_2026.map(c => `<div style="padding:2px 0;font-size:12.5px;color:var(--ink-2)">▸ ${esc(c)}</div>`).join('')}</div>` : ''}
      ${(n.risk_factors || []).length ? `
        <div style="margin-bottom:10px"><h4 style="font-size:12px;margin:0 0 4px">Factores de Riesgo</h4>
        ${n.risk_factors.map(r => `<div style="padding:2px 0;font-size:12.5px;color:var(--down,#FF6577)">⚠ ${esc(r)}</div>`).join('')}</div>` : ''}
      <button onclick="window.V8detail?.enrich?.('${nodeId}')" style="padding:7px 12px;border:1px solid var(--line-2);border-radius:8px;background:var(--surface);color:var(--ink-2);cursor:pointer;font-size:12px">✨ Analizar con IA</button>
    `;
  }

  async _renderSim(nodeId, el) {
    const n = NODE_BY_ID[nodeId];
    el.innerHTML = `
      <div style="text-align:center;padding:12px 0">
        <p style="color:var(--ink-3);font-size:13px;margin-bottom:14px">Simula un escenario con <b>${esc(n.label)}</b> como protagonista</p>
        <div style="display:flex;flex-direction:column;gap:8px;align-items:stretch">
          <button onclick="window.nexusCore?.runPresetForNode('${nodeId}','collapse')" style="padding:9px;border:1px solid var(--line-2);border-radius:8px;background:var(--surface);cursor:pointer;font-size:12.5px;color:var(--ink)">💥 Simular colapso de ${esc(n.label)}</button>
          <button onclick="window.nexusCore?.runPresetForNode('${nodeId}','boom')" style="padding:9px;border:1px solid var(--line-2);border-radius:8px;background:var(--surface);cursor:pointer;font-size:12.5px;color:var(--ink)">🚀 Simular éxito masivo de ${esc(n.label)}</button>
          <button onclick="window.switchTab&&window.switchTab('sim')" style="padding:9px;border:1px solid var(--line-2);border-radius:8px;background:var(--surface);cursor:pointer;font-size:12.5px;color:var(--ink-2)">🔬 Ver todas las simulaciones</button>
        </div>
      </div>
      <div id="sim-mini-result-${nodeId}"></div>
    `;
  }

  async _renderNetwork(nodeId, el) {
    const bc = (typeof getBetweenness === 'function') ? getBetweenness() : {};
    const inDeg = LINKS.filter(l => lid(l.target) === nodeId).length;
    const outDeg = LINKS.filter(l => lid(l.source) === nodeId).length;
    const cascade = (typeof computeDownstream === 'function') ? computeDownstream(nodeId) : new Set();
    const nrs = this._nrsInfo(nodeId);
    // NRS breakdown derived from factors
    const n = NODE_BY_ID[nodeId] || {};
    const geoMap = { 'China': 28, 'Taiwan': 25, 'Korea': 15, 'Japan': 12, 'EEUU': 8, 'Europa': 10, 'Israel': 18 };
    const geo = geoMap[n.country] ?? 15;
    const chain = Math.min(25, LINKS.filter(l => lid(l.source) === nodeId || lid(l.target) === nodeId).length * 2.5);
    const margin = n.margin != null ? n.margin : 0.15;
    const market = Math.round((1 - Math.min(1, margin / 0.4)) * 20);
    const fundamental = Math.min(15, (n.preipo ? 10 : 0) + ((n.growth || '').includes('🔴') ? 5 : (n.growth || '').includes('🟡') ? 2 : 0));
    const concentration = (n.country === 'Taiwan' || n.country === 'China') ? 10 : 4;
    const breakdown = { 'Geo': Math.round(geo), 'Cadena': Math.round(chain), 'Mercado': market, 'Fundamental': fundamental, 'Concentración': concentration };

    el.innerHTML = `
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px">
        <div class="sb-card"><div class="sb-l">NRS Score</div><div class="sb-v" style="color:${nrs.color}">${nrs.total}/100</div></div>
        <div class="sb-card"><div class="sb-l">Betweenness</div><div class="sb-v">${(bc[nodeId] || 0).toFixed(3)}</div></div>
        <div class="sb-card"><div class="sb-l">Proveedores</div><div class="sb-v">${inDeg}</div></div>
        <div class="sb-card"><div class="sb-l">Clientes</div><div class="sb-v">${outDeg}</div></div>
      </div>
      <div style="margin-bottom:12px"><h4 style="font-size:12px;margin:0 0 6px">Desglose NRS Risk Score</h4>
        ${Object.entries(breakdown).map(([k, v]) =>
          `<div style="display:flex;justify-content:space-between;align-items:center;padding:3px 0;font-size:12px">
            <span style="color:var(--ink-2)">${k}</span>
            <div style="display:flex;align-items:center;gap:6px">
              <div style="width:${Math.round(v * 3)}px;height:5px;background:${nrs.color};border-radius:2px"></div>
              <span style="font-family:'JetBrains Mono',monospace;font-size:11px">${v}</span>
            </div></div>`).join('')}
      </div>
      <div><h4 style="font-size:12px;margin:0 0 4px">Si colapsa…</h4>
        <p style="font-size:12.5px;color:var(--ink-2);margin-bottom:8px">${cascade.size} empresas afectadas (${Math.round(cascade.size / NODES.length * 100)}% de la cadena)</p>
        <button onclick="window.activateStress&&window.activateStress('${nodeId}')" style="padding:8px 12px;border:1px solid var(--down,#FF6577);border-radius:8px;background:var(--surface);color:var(--down,#FF6577);cursor:pointer;font-size:12px">💥 Ver cascada en el grafo</button>
      </div>
    `;
  }
}

window.SecondBrain = SecondBrain;
