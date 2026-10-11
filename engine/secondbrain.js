// engine/secondbrain.js — Second Brain de 5 capas para Khipu Finance
// Al seleccionar una empresa, abre un panel con 5 capas de conocimiento:
//   1. Mercado (precio + sparkline + NRS)   2. Noticias
//   3. Tesis (catalizadores + riesgos + IA)  4. Simulación (presets de escenario)
//   5. Red (betweenness + cascada + desglose NRS)
//
// Depende de app.html: NODE_BY_ID, NODE_META, MKT, quotePx, DataLayer, computeNRS, NRS_FLOW_TYPES,
//   getBetweenness, computeDownstream, LINKS, NODES, lid, esc, fmtN, fmtPct,
//   relTime, sentiment, nf, today, catColor/getCatColorHex, BASE

// Bilingüe (limpieza 2026-10-11: era solo español): textos con L(es, en) según window.LANG / eco_lang.
function _sbEn() { try { return (window.LANG || localStorage.getItem('eco_lang') || 'es') === 'en'; } catch (e) { return false; } }
function _sbL(es, en) { return _sbEn() ? en : es; }
// proveedores / clientes = SOLO relaciones de FLUJO (regla G4a; misma lista que el NRS: window.NRS_FLOW_TYPES)
function _sbFlow(l) { var F = window.NRS_FLOW_TYPES; return !F || !!F[l.type || 'supply']; }

class SecondBrain {
  constructor(graph3d) {
    this.graph3d = graph3d;
    this.activeLayer = 1;
    this.activeNodeId = null;
  }

  async showNodeLayers(nodeId) {
    this.activeNodeId = nodeId;
    const n = NODE_BY_ID[nodeId];
    const panel = document.getElementById('second-brain-panel');
    if (!n) return;
    if (panel) panel.style.display = 'block';
    const nameEl = document.getElementById('sb-company-name');
    if (nameEl) nameEl.textContent = n.label + (n.mkt ? ' · ' + n.mkt.split(' · ')[0] : '');

    const el = document.getElementById('sb-content');
    if (!el) return;

    el.innerHTML = `
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
        <span style="width:10px;height:10px;border-radius:50%;background:${typeof getCatColorHex==='function'?getCatColorHex(n.cat):typeof catColor==='function'?catColor(n.cat):'#888'};flex-shrink:0"></span>
        <span style="font-size:13px;font-weight:700">${esc(n.label)}</span>
        <span style="font-size:11px;color:var(--ink-3);font-family:'JetBrains Mono',monospace">${esc((n.ticker || '').split(' · ')[0] || '')}</span>
      </div>
      <div style="display:flex;gap:4px;margin-bottom:16px;flex-wrap:wrap">
        ${[['📊', _sbL('Mercado', 'Market'), 1], ['📰', _sbL('Noticias', 'News'), 2], ['💡', _sbL('Tesis', 'Thesis'), 3], ['🔮', _sbL('Simulación', 'Simulation'), 4], ['🕸️', _sbL('Red', 'Network'), 5]]
          .map(([icon, label, layer]) =>
            `<button class="sb-chip${this.activeLayer === layer ? ' active' : ''}"
              onclick="window._secondBrain&&window._secondBrain.setNodeLayer('${nodeId}',${layer})"
              style="padding:5px 10px;font-size:12px;border:1px solid var(--line-2);border-radius:7px;background:${this.activeLayer === layer ? 'var(--surface-2)' : 'var(--surface)'};color:var(--ink-2);cursor:pointer">${icon} ${label}</button>`
          ).join('')}
      </div>
      <div id="brain-layer-content"></div>
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
    const label = total >= 70 ? _sbL('ALTO', 'HIGH') : total >= 40 ? _sbL('MEDIO', 'MEDIUM') : _sbL('BAJO', 'LOW');
    return { total, color, label };
  }

  async _renderMarket(nodeId, el) {
    const n = NODE_BY_ID[nodeId];
    const meta = NODE_META[nodeId] || {};
    const q = n.mkt ? (MKT.quotes[n.mkt] || null) : null;
    // precio SIEMPRE con window.quotePx (contrato de MKT.quotes: `live` numérico o ausente)
    const px = q ? (window.quotePx ? window.quotePx(q) : +q.close || 0) : 0;
    const chg = (px && q && q.prev) ? (px - q.prev) / q.prev : null;
    const nrs = this._nrsInfo(nodeId);

    el.innerHTML = `
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
        <div class="sb-card"><div class="sb-l">${_sbL('Precio', 'Price')}</div>
          <div class="sb-v" style="color:${chg > 0 ? 'var(--up,#3DE0C8)' : chg < 0 ? 'var(--down,#FF6577)' : 'var(--ink)'}">${px ? '$' + fmtN(px) : n.preipo ? _sbL('PRIVADA', 'PRIVATE') : '—'}</div>
          <div class="sb-s">${chg != null ? (chg >= 0 ? '▲ ' : '▼ ') + fmtPct(Math.abs(chg)) : ''}</div></div>
        <div class="sb-card"><div class="sb-l">${_sbL('Capitalización', 'Market cap')}</div>
          <div class="sb-v" style="font-size:15px">${meta.mktcap_b ? '$' + meta.mktcap_b + 'B' + (window.liveCapDot ? window.liveCapDot(meta) : '') : (n.preipo ? n.ticker : '—')}</div></div>
        <div class="sb-card"><div class="sb-l">${_sbL('Ingresos 2025', 'Revenue 2025')}</div>
          <div class="sb-v" style="font-size:13px">${esc(n.revenue_2025 || meta.revenue_2025 || '—')}</div></div>
        <div class="sb-card"><div class="sb-l">${_sbL('Riesgo NRS', 'NRS risk')}</div>
          <div class="sb-v" style="font-size:15px;color:${nrs.color}">${nrs.total}/100</div>
          <div class="sb-s" style="color:${nrs.color}">${nrs.label}</div></div>
      </div>
      <canvas id="sparkline-${nodeId}" height="80" style="width:100%;margin-top:12px"></canvas>
      ${n.mkt ? '' : '<div style="font-size:11px;color:var(--ink-3);margin-top:8px">' + _sbL('No cotiza en bolsa: sin gráfico de precio.', 'Not listed: no price chart.') + '</div>'}
    `;
    // velas por el servidor (/api/candles: Yahoo primero, Finnhub de respaldo) — antes se exigía Finnhub
    if (n.mkt && typeof Chart !== 'undefined') {
      this._drawSparkline(nodeId, n.mkt);
    }
  }

  async _drawSparkline(nodeId, ticker) {
    try {
      // Velas vía el proxy del server (misma forma {s,c,o,h,l,t} de Finnhub);
      // la key nunca llega al navegador.
      const r = await DataLayer._json(`/api/candles/${encodeURIComponent(ticker)}`);
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
    el.innerHTML = '<div style="color:var(--ink-3);font-size:12px;padding:8px">' + _sbL('Cargando noticias…', 'Loading news…') + '</div>';
    try {
      let news = n.mkt ? await DataLayer.news(n.mkt) : [];
      if (!Array.isArray(news)) news = [];

      el.innerHTML = `
        ${news.length === 0 ? '<div style="color:var(--ink-3);font-size:12px">' + _sbL('Sin noticias disponibles', 'No news available') + '</div>' :
          news.slice(0, 8).map(item => {
            const s = (typeof sentiment === 'function') ? sentiment(item.headline) : { cls: '', icon: '' };
            return `<a href="${window.safeUrl ? window.safeUrl(item.url) : esc(/^https?:\/\//i.test(item.url || '') ? item.url : '#')}" target="_blank" rel="noopener" style="display:block;padding:8px 0;border-bottom:1px solid var(--line);text-decoration:none;color:inherit">
              <div style="display:flex;gap:8px;font-size:10.5px;color:var(--ink-3);margin-bottom:3px">
                <span>${esc(item.source || '')}</span><span>${typeof relTime === 'function' ? relTime(item.datetime) : ''}</span>
                <span class="${s.cls}">${s.icon}</span></div>
              <div style="font-size:12.5px;color:var(--ink);line-height:1.4">${esc(item.headline)}</div></a>`;
          }).join('')}
      `;
    } catch (e) {
      el.innerHTML = `<div style="color:var(--down,#FF6577);font-size:12px">${esc(String(e.message))}</div>`;
    }
  }

  async _renderThesis(nodeId, el) {
    const n = NODE_BY_ID[nodeId];
    el.innerHTML = `
      <div style="background:var(--surface-2);border-radius:8px;padding:12px;margin-bottom:10px">
        <div style="font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--ink-3);margin-bottom:4px">${_sbL('Tesis de inversión', 'Investment thesis')}</div>
        <div style="font-size:13px;line-height:1.5">${esc(n.thesis || (typeof nf === 'function' ? nf(n, 'moat') : n.moat) || '—')}</div>
      </div>
      ${(n.catalysts_2026 || []).length ? `
        <div style="margin-bottom:10px"><h4 style="font-size:12px;margin:0 0 4px">${_sbL('Catalizadores 2026', '2026 catalysts')}</h4>
        ${n.catalysts_2026.map(c => `<div style="padding:2px 0;font-size:12.5px;color:var(--ink-2)">▸ ${esc(c)}</div>`).join('')}</div>` : ''}
      ${(n.risk_factors || []).length ? `
        <div style="margin-bottom:10px"><h4 style="font-size:12px;margin:0 0 4px">${_sbL('Factores de riesgo', 'Risk factors')}</h4>
        ${n.risk_factors.map(r => `<div style="padding:2px 0;font-size:12.5px;color:var(--down,#FF6577)">⚠ ${esc(r)}</div>`).join('')}</div>` : ''}
      <button onclick="window.V8detail?.enrich?.('${nodeId}')" style="padding:7px 12px;border:1px solid var(--line-2);border-radius:8px;background:var(--surface);color:var(--ink-2);cursor:pointer;font-size:12px">✨ ${_sbL('Analizar con IA', 'Analyze with AI')}</button>
    `;
  }

  async _renderSim(nodeId, el) {
    const n = NODE_BY_ID[nodeId];
    el.innerHTML = `
      <div style="text-align:center;padding:12px 0">
        <p style="color:var(--ink-3);font-size:13px;margin-bottom:14px">${_sbL('Simula un escenario con', 'Simulate a scenario with')} <b>${esc(n.label)}</b> ${_sbL('como protagonista', 'at the center')}</p>
        <div style="display:flex;flex-direction:column;gap:8px;align-items:stretch">
          <button onclick="window.nexusCore?.runPresetForNode('${nodeId}','collapse')" style="padding:9px;border:1px solid var(--line-2);border-radius:8px;background:var(--surface);cursor:pointer;font-size:12.5px;color:var(--ink)">💥 ${_sbL('Simular colapso de', 'Simulate the collapse of')} ${esc(n.label)}</button>
          <button onclick="window.nexusCore?.runPresetForNode('${nodeId}','boom')" style="padding:9px;border:1px solid var(--line-2);border-radius:8px;background:var(--surface);cursor:pointer;font-size:12.5px;color:var(--ink)">🚀 ${_sbL('Simular éxito masivo de', 'Simulate a massive success of')} ${esc(n.label)}</button>
          <button onclick="window.switchTab&&window.switchTab('simulation')" style="padding:9px;border:1px solid var(--line-2);border-radius:8px;background:var(--surface);cursor:pointer;font-size:12.5px;color:var(--ink-2)">🔬 ${_sbL('Ver todas las simulaciones', 'See all simulations')}</button>
        </div>
      </div>
      <div id="sim-mini-result-${nodeId}"></div>
    `;
  }

  async _renderNetwork(nodeId, el) {
    const bc = (typeof getBetweenness === 'function') ? getBetweenness() : {};
    const inDeg = new Set(LINKS.filter(l => lid(l.target) === nodeId && _sbFlow(l)).map(l => lid(l.source))).size;
    const outDeg = new Set(LINKS.filter(l => lid(l.source) === nodeId && _sbFlow(l)).map(l => lid(l.target))).size;
    const cascade = (typeof computeDownstream === 'function') ? computeDownstream(nodeId) : new Set();
    const nrs = this._nrsInfo(nodeId);
    // Desglose NRS = el MISMO de computeNRSBreakdown (app.html _nrsTerms; limpieza 2026-10-11: aquí había
    // una 6.ª copia de la fórmula con el margen sin acotar y el país sin normalizar → no sumaba el NRS mostrado)
    const _bd = (typeof window.computeNRSBreakdown === 'function') ? window.computeNRSBreakdown(nodeId) : null;
    const breakdown = {};
    ((_bd && _bd.terms) || []).forEach(t => { breakdown[t.key] = t.val; });

    el.innerHTML = `
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px">
        <div class="sb-card"><div class="sb-l">NRS Score</div><div class="sb-v" style="color:${nrs.color}">${nrs.total}/100</div></div>
        <div class="sb-card"><div class="sb-l">Betweenness</div><div class="sb-v">${(bc[nodeId] || 0).toFixed(3)}</div></div>
        <div class="sb-card"><div class="sb-l">${_sbL('Proveedores', 'Suppliers')}</div><div class="sb-v">${inDeg}</div></div>
        <div class="sb-card"><div class="sb-l">${_sbL('Clientes', 'Customers')}</div><div class="sb-v">${outDeg}</div></div>
      </div>
      <div style="margin-bottom:12px"><h4 style="font-size:12px;margin:0 0 6px">${_sbL('Desglose del riesgo NRS', 'NRS risk breakdown')}</h4>
        ${Object.entries(breakdown).map(([k, v]) =>
          `<div style="display:flex;justify-content:space-between;align-items:center;padding:3px 0;font-size:12px">
            <span style="color:var(--ink-2)">${k}</span>
            <div style="display:flex;align-items:center;gap:6px">
              <div style="width:${Math.round(v * 3)}px;height:5px;background:${nrs.color};border-radius:2px"></div>
              <span style="font-family:'JetBrains Mono',monospace;font-size:11px">${v}</span>
            </div></div>`).join('')}
      </div>
      <div><h4 style="font-size:12px;margin:0 0 4px">${_sbL('Si colapsa…', 'If it collapses…')}</h4>
        <p style="font-size:12.5px;color:var(--ink-2);margin-bottom:8px">${cascade.size} ${_sbL('empresas afectadas', 'companies affected')} (${Math.round(cascade.size / NODES.length * 100)}% ${_sbL('de la cadena', 'of the chain')})</p>
        <button onclick="window.activateStress&&window.activateStress('${nodeId}')" style="padding:8px 12px;border:1px solid var(--down,#FF6577);border-radius:8px;background:var(--surface);color:var(--down,#FF6577);cursor:pointer;font-size:12px">💥 ${_sbL('Ver cascada en el grafo', 'See the cascade on the graph')}</button>
      </div>
    `;
  }
}

window.SecondBrain = SecondBrain;
