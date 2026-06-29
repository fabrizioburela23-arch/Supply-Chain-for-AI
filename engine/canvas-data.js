// engine/canvas-data.js — Enriquecimiento de Canvas IA con datos en vivo (Khipu)
// Detecta empresas/tickers mencionados en una consulta y trae precios REALES
// de Finnhub (vía /api/quotes) para inyectarlos al contexto del Canvas, de modo
// que las tablas/gráficos comparativos usen datos de mercado reales, no estimados.
// Expone window.canvasEnrichData(query) → {tickers, live:{SYM:{price,change_pct}}}

(function () {
  'use strict';

  function matchTickers(query) {
    const NODES = window.NODES || [];
    const q = ' ' + (query || '').toLowerCase() + ' ';
    const syms = new Set();
    for (const n of NODES) {
      const sym = n.mkt;
      if (!sym) continue;
      const label = (n.label || '').toLowerCase();
      const tk = ((n.ticker || '').split(/[ ·]/)[0] || '').toLowerCase();
      // match por nombre de empresa, símbolo de display o símbolo Finnhub
      if ((label.length > 2 && q.includes(label)) ||
          (tk.length > 1 && q.includes(' ' + tk + ' ')) ||
          (q.includes(' ' + sym.toLowerCase() + ' '))) {
        syms.add(sym);
      }
      if (syms.size >= 8) break;
    }
    return [...syms];
  }

  window.canvasEnrichData = async function (query) {
    try {
      const tickers = matchTickers(query);
      if (!tickers.length) return {};
      const base = (typeof BASE !== 'undefined') ? BASE : '';
      const r = await fetch(`${base}/api/quotes?symbols=${encodeURIComponent(tickers.join(','))}`);
      if (!r.ok) return { tickers };
      const raw = await r.json();
      if (raw.error) return { tickers };
      const live = {};
      for (const [sym, q] of Object.entries(raw)) {
        if (q && typeof q.c === 'number' && q.c > 0) {
          live[sym] = { price: q.c, change_pct: (typeof q.dp === 'number' ? q.dp : null) };
        }
      }
      return { tickers, live };
    } catch (e) {
      return {};
    }
  };
})();
