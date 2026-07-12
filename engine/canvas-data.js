// engine/canvas-data.js — Enriquecimiento de Canvas IA con datos en vivo (Khipu)
// Detecta empresas/tickers mencionados en una consulta y trae precios REALES
// de Finnhub (vía /api/quotes) para inyectarlos al contexto del Canvas, de modo
// que las tablas/gráficos comparativos usen datos de mercado reales, no estimados.
// Expone window.canvasEnrichData(query) → {tickers, live:{SYM:{price,change_pct}}}
//
// Rendimiento (Etapa I "que no tarden", 2026-07-12): este paso corre ANTES de
// cada llamada a la IA, así que NO puede añadir latencia:
//   · caché en memoria 60 s por combinación de tickers (repetir = 0 fetches)
//   · timeout duro de 1500 ms — si /api/quotes va lento, seguimos sin `live`
//     en vez de retrasar el gráfico.

(function () {
  'use strict';

  const TTL = 60 * 1000;          // caché de quotes: 60 s
  const TIMEOUT_MS = 1500;        // nunca bloquear el pipeline del gráfico
  const _cache = {};              // key (tickers ordenados) → {t, live}

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

  function fetchWithTimeout(url, ms) {
    if (typeof AbortController !== 'function') return fetch(url);
    const ctrl = new AbortController();
    const timer = setTimeout(() => { try { ctrl.abort(); } catch (e) {} }, ms);
    return fetch(url, { signal: ctrl.signal }).finally(() => clearTimeout(timer));
  }

  window.canvasEnrichData = async function (query) {
    try {
      const tickers = matchTickers(query);
      if (!tickers.length) return {};
      const key = tickers.slice().sort().join(',');
      const hit = _cache[key];
      if (hit && Date.now() - hit.t < TTL) return { tickers, live: hit.live };
      const base = (typeof BASE !== 'undefined') ? BASE : '';
      const r = await fetchWithTimeout(
        `${base}/api/quotes?symbols=${encodeURIComponent(tickers.join(','))}`, TIMEOUT_MS);
      if (!r.ok) return { tickers };
      const raw = await r.json();
      if (raw.error) return { tickers };
      const live = {};
      for (const [sym, q] of Object.entries(raw)) {
        if (q && typeof q.c === 'number' && q.c > 0) {
          live[sym] = { price: q.c, change_pct: (typeof q.dp === 'number' ? q.dp : null) };
        }
      }
      _cache[key] = { t: Date.now(), live };
      return { tickers, live };
    } catch (e) {
      return {};   // timeout o red caída: el gráfico sigue, solo sin precios live
    }
  };
})();
