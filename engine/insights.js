/* ============================================================================
   engine/insights.js — INSIGHTS AUTOMÁTICOS (Etapa 5, piel NEXUS)
   Genera tarjetas de lectura desde la topología + el motor de matrices:
   - chokepoints (quién arrastra a más empresas si cae)
   - riesgo alto (NRS) — con foco en tu cartera
   - factores externos activos (hiperaristas)
   - concentración geográfica

   Fuente preferida: /api/matrix/metrics + /impact (ponderado, server).
   Fallback 100% cliente (computeDownstream + computeNRS) si no hay
   DATABASE_URL — así SIEMPRE hay insights, con nota honesta.
   Rellena #an-insights (el slot que existía vacío) y expone
   window.renderKhipuInsights() para el botón "Recalcular".
   ============================================================================ */
(function () {
  'use strict';

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function isEn() { var l = window.LANG; if (!l) { try { l = localStorage.getItem('eco_lang'); } catch (e) { l = null; } } return l === 'en'; }
  function L(es, en) { return isEn() ? en : es; }
  function lid(v) { return (typeof v === 'object' && v !== null) ? v.id : v; }
  function nm(id) { var n = window.NODE_BY_ID && window.NODE_BY_ID[id]; return n ? n.label : id; }
  // color del SECTOR (dato del catálogo): solo como relleno del punto de la empresa, nunca como color de texto
  function secColor(id) {
    var n = window.NODE_BY_ID && window.NODE_BY_ID[id];
    if (!n || !window.SECTORS9) return 'var(--os-accent,#4C8DF6)';
    var s = window.SECTORS9[(window.CAT_TO_SECTOR || {})[n.cat] || 'cloud_ia'];
    return s ? s.color : 'var(--os-accent,#4C8DF6)';
  }

  // Colores SEMÁNTICOS de Khipus OS: col = TEXTO (contraste AA en claro y oscuro), fill = relleno vivo de la píldora.
  var KIND = {
    shock:  { label: 'CHOKEPOINT', col: 'var(--os-bad-ink,#F47C7C)', fill: 'var(--os-bad,#f06565)' },
    risk:   { label: 'RIESGO', label_en: 'RISK', col: 'var(--os-warn-ink,#F2C46D)', fill: 'var(--os-warn,#F2C46D)' },
    factor: { label: 'FACTOR', col: 'var(--os-ai,#B48CFF)', fill: 'var(--os-ai,#B48CFF)' },
    // texto en --os-ink: el azul de acento sobre su propia píldora teñida no llega a 4.5:1 en el tema claro
    geo:    { label: 'GEO', col: 'var(--os-ink,#F2F2F5)', fill: 'var(--os-accent,#4C8DF6)' },
    oport:  { label: 'OPORTUNIDAD', label_en: 'OPPORTUNITY', col: 'var(--os-good-ink,#2fbf5b)', fill: 'var(--os-good,#2fbf5b)' },
  };

  /* ── estilos: Khipus OS (2026-10-10) ───────────────────────────────────────
     1) Tarjetas de #an-insights / #an-history (pestaña Análisis): el contenedor lleva .kos-themed → tokens --os-*
        de engine/cockpit.js (claro = body sin .dark, oscuro = body.dark). Tarjetas sin bordes, píldoras teñidas.
     2) La VENTANA «💡 Oportunidades» de Khipus OS (kind 'insights') la pinta engine/cockpit.js (stageInsights)
        con clases .bcp-* de colores oscuros fijos. Aquí se re-tematizan SOLO dentro de esa ventana
        (.kd-win[data-kind="insights"]) con los mismos tokens: así la ventana se ve nativa en claro y oscuro y
        ya no necesita la isla oscura (LEGACY_DARK). Si la ventana sigue marcada .kd-legacy-dark, los tokens
        valen los oscuros y se ve igual que antes. Los colores fijos que stageInsights escribe en style=""
        (#FF4D6A / #2BE38B / var(--ink-3)) se puentean con [style*=…] + !important (mismo patrón que el comité).
     Solo tokens; el valor tras la coma es el respaldo oscuro. */
  function ensureStyles() {
    if (document.getElementById('ins-styles')) return;
    var W = '.kd-win[data-kind="insights"] ';
    var css = '' +
      '.ins-root{color:var(--os-ink,#F2F2F5);font-family:var(--os-font,\'Nunito\',\'Geist\',system-ui,-apple-system,\'Segoe UI\',sans-serif);' +
        '-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale}' +
      '.ins-root .ins-card{border-radius:var(--os-r,18px);padding:14px 16px;background:var(--os-surface,#17181F);min-width:0;' +
        'box-shadow:var(--os-shadow,0 1px 2px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.35));display:flex;flex-direction:column;gap:9px}' +
      '.ins-root .ins-hd{display:flex;align-items:center;gap:8px;flex-wrap:wrap}' +
      '.ins-root .ins-k{display:inline-flex;align-items:center;padding:2px 9px;border-radius:999px;font-size:10.5px;font-weight:800;letter-spacing:.08em}' +
      '.ins-root .ins-tag{font-size:11.5px;color:var(--os-ink-2,#A6A8B5)}' +
      '.ins-root .ins-tx{font-size:13px;line-height:1.5;color:var(--os-ink,#F2F2F5);overflow-wrap:anywhere}.ins-root .ins-tx b{font-weight:800}' +
      '.ins-root .ins-chips{display:flex;gap:6px;flex-wrap:wrap}' +
      '.ins-root .ins-chip{appearance:none;-webkit-appearance:none;border:0;cursor:pointer;display:inline-flex;align-items:center;gap:6px;max-width:100%;' +
        'font-family:inherit;font-size:11.5px;font-weight:600;padding:3px 10px;border-radius:999px;background:var(--os-surface-2,#1F2029);color:var(--os-ink,#F2F2F5);' +
        'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;transition:background-color .15s}' +
      '.ins-root .ins-chip:hover{background:var(--os-surface-3,#2A2B36)}' +
      '.ins-root .ins-chip i{width:7px;height:7px;border-radius:50%;flex:none}' +
      '.ins-root .ins-act{appearance:none;-webkit-appearance:none;border:0;background:none;padding:0;cursor:pointer;align-self:flex-start;' +
        'font-family:inherit;font-size:12px;font-weight:700;color:var(--os-accent,#4C8DF6)}' +
      '.ins-root .ins-act:hover{text-decoration:underline}' +
      '.ins-root .ins-chip:focus-visible,.ins-root .ins-act:focus-visible{outline:2px solid var(--os-accent,#4C8DF6);outline-offset:2px}' +
      '.ins-root .ins-msg{grid-column:1/-1;color:var(--os-ink-2,#A6A8B5);font-size:12px}' +
      '.ins-root .ins-hist{border-radius:var(--os-r-sm,12px);padding:11px 14px;margin-bottom:9px;background:var(--os-surface,#17181F);' +
        'box-shadow:var(--os-shadow,0 1px 2px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.35))}' +
      '.ins-root .ins-hist .ins-hh{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:3px}' +
      '.ins-root .ins-hist .ins-hh b{font-size:13px;flex:1;min-width:0;overflow-wrap:anywhere}' +
      '.ins-root .ins-hist .ins-when{font-size:11px;color:var(--os-ink-2,#A6A8B5);font-variant-numeric:tabular-nums}' +
      '.ins-root .ins-hist .ins-meta{font-size:11.5px;color:var(--os-ink-2,#A6A8B5)}.ins-root .ins-hist .ins-meta b{color:var(--os-ink,#F2F2F5)}' +
      '.ins-root .ins-hist .ins-lead{font-size:12.5px;color:var(--os-ink-2,#A6A8B5);margin-top:5px;line-height:1.5;overflow-wrap:anywhere}' +
      '@media(prefers-reduced-motion:reduce){.ins-root .ins-chip{transition:none}}' +
      // ── ventana «Oportunidades» de Khipus OS (markup de cockpit.js stageInsights) ──
      W + '.bcp-lh{color:var(--os-ink-2,#A6A8B5);font-weight:800}' +
      W + '.bcp-lh[style*="#FF4D6A" i]{color:var(--os-bad-ink,#F47C7C)!important}' +
      W + '.bcp-lh[style*="#2BE38B" i]{color:var(--os-good-ink,#2fbf5b)!important}' +
      W + '[style*="var(--ink-3"]{color:var(--os-ink-2,#A6A8B5)!important}' +
      W + '.bcp-two{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}' +
      '@media(max-width:760px){' + W + '.bcp-two{grid-template-columns:minmax(0,1fr)}}' +
      W + '.bcp-row{border-radius:10px;padding:5px 6px;transition:background-color .15s;min-width:0}' +
      W + '.bcp-row:hover{background:var(--os-surface-2,#1F2029)}' +
      W + '.bcp-row .nm,' + W + '.bcp-row:hover .nm{color:var(--os-ink,#F2F2F5)}' +
      W + '.bcp-row .pv{font-family:inherit;font-variant-numeric:tabular-nums;font-weight:800;font-size:12px;width:auto;min-width:42px;white-space:nowrap}' +
      W + '.bcp-row .pv[style*="#FF4D6A" i]{color:var(--os-bad-ink,#F47C7C)!important}' +
      W + '.bcp-row .pv[style*="#2BE38B" i]{color:var(--os-good-ink,#2fbf5b)!important}' +
      W + '.bcp-dot{box-shadow:none}' +
      W + '.bcp-loading{color:var(--os-ink-2,#A6A8B5)}' +
      W + '.bcp-loading::before{border-color:var(--os-surface-3,#2A2B36);border-top-color:var(--os-accent,#4C8DF6)}' +
      W + '.bcp-hyper-hd .t{color:var(--os-ink,#F2F2F5);font-weight:800}' +
      W + '.bcp-hyper-hd .live{color:var(--os-ink,#F2F2F5);border:0;background:var(--os-surface-2,#1F2029);background:color-mix(in srgb,var(--os-accent,#4C8DF6) 13%,transparent)}' +
      W + '.bcp-hyper-hd .live::before{background:var(--os-accent,#4C8DF6);box-shadow:none}' +
      W + '.bcp-fact{color:var(--os-warn-ink,#F2C46D);border:0;background:var(--os-surface-2,#1F2029);background:color-mix(in srgb,var(--os-warn,#F2C46D) 14%,transparent)}' +
      W + '.bcp-fact b{color:inherit}' +
      W + '.bcp-icard{border:0;border-radius:var(--os-r-sm,12px);background:var(--os-surface-2,#1F2029);box-shadow:inset 3px 0 0 var(--os-accent,#4C8DF6)}' +
      W + '.bcp-icard.k-riesgo{box-shadow:inset 3px 0 0 var(--os-bad,#f06565)}' +
      W + '.bcp-icard.k-oportunidad{box-shadow:inset 3px 0 0 var(--os-good,#2fbf5b)}' +
      W + '.bcp-icard .it{color:var(--os-ink,#F2F2F5)}' +
      W + '.bcp-icard .id{color:var(--os-ink-2,#A6A8B5)}' +
      W + '.bcp-casc{border:0;border-radius:var(--os-r-sm,12px);background:var(--os-surface-2,#1F2029)}' +
      W + '.bcp-casc .ch{color:var(--os-ink-2,#A6A8B5);font-weight:800}' +
      W + '.bcp-cascrow .nm{color:var(--os-ink,#F2F2F5)}' +
      W + '.bcp-cascrow:hover .nm{color:var(--os-accent,#4C8DF6)}' +
      W + '.bcp-cascrow .bar{background:var(--os-surface-3,#2A2B36)}' +
      W + '.bcp-cascrow .bar i{background:linear-gradient(90deg,var(--os-bad,#f06565),var(--os-warn,#F2C46D))}' +
      W + '.bcp-cascrow .pv{color:var(--os-bad-ink,#F47C7C);font-family:inherit;font-variant-numeric:tabular-nums;font-weight:800}' +
      W + '.bcp-hyper-foot{color:var(--os-ink-2,#A6A8B5)}' +
      '@media(prefers-reduced-motion:reduce){' + W + '.bcp-hyper-hd .live::before,' + W + '.bcp-loading::before{animation:none}' + W + '.bcp-row{transition:none}}';
    var st = document.createElement('style'); st.id = 'ins-styles'; st.textContent = css;
    (document.head || document.documentElement).appendChild(st);
  }
  try { ensureStyles(); } catch (e) {}   // la ventana del OS no llama a este módulo: los estilos van desde la carga

  function themeRoot(el) { if (el && el.classList) { el.classList.add('kos-themed'); el.classList.add('ins-root'); } }

  function card(ins) {
    var k = KIND[ins.kind] || KIND.shock;
    var chips = (ins.nodes || []).slice(0, 4).map(function (id) {
      return '<button type="button" class="ins-chip" onclick="window._insJump&&window._insJump(\'' + esc(id) + '\')">' +
        '<i style="background:' + secColor(id) + '"></i>' + esc(nm(id)) + '</button>';
    }).join('');
    return '<div class="ins-card">' +
      '<div class="ins-hd"><span class="ins-k" style="color:' + k.col + ';background:var(--os-surface-2,#1F2029);background:color-mix(in srgb,' + k.fill + ' 14%,transparent)">' +
        (isEn() && k.label_en ? k.label_en : k.label) + '</span>' +
        '<span class="ins-tag">' + esc(ins.tag || '') + '</span></div>' +
      '<div class="ins-tx">' + ins.text + '</div>' +
      (chips ? '<div class="ins-chips">' + chips + '</div>' : '') +
      (ins.action ? '<button type="button" class="ins-act" onclick="' + ins.action + '">▸ ' + esc(ins.actionLabel || L('ver', 'see')) + '</button>' : '') +
    '</div>';
  }

  window._insJump = function (id) {
    if (typeof window.switchTab === 'function') window.switchTab('map');
    setTimeout(function () { if (window.jumpTo) window.jumpTo(id); }, 90);
  };

  // ── generación cliente (siempre disponible) ──
  function clientInsights() {
    var out = [];
    var NODES = window.NODES || [], LINKS = window.LINKS || [];
    if (!NODES.length) return out;

    // 1) chokepoints por tamaño de cascada (computeDownstream)
    if (typeof window.computeDownstream === 'function') {
      var casc = NODES.map(function (n) {
        var aff = 0;
        try { var r = window.computeDownstream(n.id); aff = (r instanceof Set ? r.size : (r || []).length); } catch (e) {}
        return { id: n.id, aff: aff };
      }).filter(function (x) { return x.aff > 0; }).sort(function (a, b) { return b.aff - a.aff; });
      if (casc.length) {
        var top = casc[0];
        out.push({ kind: 'shock', tag: L('topología', 'topology'), nodes: casc.slice(0, 4).map(function (x) { return x.id; }),
          text: '<b>' + esc(nm(top.id)) + '</b>' + L(' es el mayor punto único de fallo: si cae, arrastra a <b>', ' is the biggest single point of failure: if it falls, it drags down <b>') +
            top.aff + L(' empresas</b> del grafo.', ' companies</b> in the graph.'),
          action: "window._insShock('" + top.id + "')", actionLabel: L('simular su caída', 'simulate its fall') });
      }
    }

    // 2) riesgo NRS alto (foco en cartera si hay posiciones)
    if (typeof window.computeNRS === 'function') {
      var pos = (window.MKT && window.MKT.pos) || {};
      var pool = Object.keys(pos).length ? Object.keys(pos) : NODES.map(function (n) { return n.id; });
      var risky = pool.map(function (id) { return { id: id, nrs: window.computeNRS(id) }; })
        .filter(function (x) { return x.nrs >= 65; }).sort(function (a, b) { return b.nrs - a.nrs; });
      if (risky.length) {
        var inPort = Object.keys(pos).length > 0;
        out.push({ kind: 'risk', tag: inPort ? L('tu cartera', 'your portfolio') : L('universo', 'universe'), nodes: risky.slice(0, 4).map(function (x) { return x.id; }),
          text: '<b>' + risky.length + '</b>' + (inPort ? L(' posiciones de tu cartera tienen', ' positions in your portfolio have') : L(' empresas del universo tienen', ' companies in the universe have')) +
            L(' riesgo NRS ≥ 65. La más expuesta: <b>', ' NRS risk ≥ 65. The most exposed: <b>') + esc(nm(risky[0].id)) + '</b> (' + risky[0].nrs + '/100).',
          action: "window.openXRay&&window.openXRay('" + risky[0].id + "')", actionLabel: L('abrir X-Ray', 'open X-Ray') });
      }
    }

    // 3) OPORTUNIDADES: resilientes con potencial (bajo riesgo + crecimiento +
    //    valoración atractiva), que NO son chokepoints frágiles
    if (typeof window.computeNRS === 'function') {
      var opps = NODES.map(function (n) {
        var nrs = window.computeNRS(n.id);
        var g = (n.growth || '').toLowerCase();
        var growth = g.indexOf('🟢') >= 0 ? 2 : g.indexOf('🟡') >= 0 ? 1 : 0;
        // crecimiento REAL si ya llegó (KhipuLiveFund): ventas del último trimestre vs hace un año
        if (n.growth_live && isFinite(n.growth_live.pct)) growth = n.growth_live.pct >= 15 ? 2 : n.growth_live.pct > 0 ? 1 : 0;
        var margin = n.margin != null ? n.margin : 0;
        // score: recompensa margen alto + crecimiento, penaliza riesgo
        var score = growth * 22 + Math.min(30, margin * 60) + (50 - nrs) * 0.5;
        return { id: n.id, score: score, nrs: nrs, margin: margin, growth: growth };
      }).filter(function (x) { return x.nrs < 55 && x.growth >= 1 && x.margin > 0.15; })
        .sort(function (a, b) { return b.score - a.score; });
      if (opps.length) {
        var mLive = !!((window.NODE_BY_ID || {})[opps[0].id] && window.NODE_BY_ID[opps[0].id].margin_live);
        out.push({ kind: 'oport', tag: L('estructural', 'structural'), nodes: opps.slice(0, 4).map(function (x) { return x.id; }),
          text: '<b>' + opps.length + '</b>' + L(' empresas combinan riesgo bajo, crecimiento y margen sano. Destaca <b>', ' companies combine low risk, growth and a healthy margin. Standing out: <b>') +
            esc(nm(opps[0].id)) + '</b> (NRS ' + opps[0].nrs + L(', margen ', ', margin ') + Math.round(opps[0].margin * 100) + '% ' +
            (isEn() ? (mLive ? 'live' : 'from the catalog') : (mLive ? 'en vivo' : 'del catálogo')) + ').',
          action: "window.openXRay&&window.openXRay('" + opps[0].id + "')", actionLabel: L('abrir X-Ray', 'open X-Ray') });
      }
    }

    // 4) PANORAMA POR SECTOR: cuál es el más frágil y el más fuerte
    if (typeof window.computeNRS === 'function' && window.SECTORS9) {
      var sec = {};
      NODES.forEach(function (n) {
        var s = (window.CAT_TO_SECTOR || {})[n.cat] || 'cloud_ia';
        (sec[s] = sec[s] || { sum: 0, n: 0 });
        sec[s].sum += window.computeNRS(n.id); sec[s].n++;
      });
      var rows = Object.keys(sec).filter(function (s) { return sec[s].n >= 3; })
        .map(function (s) { return { s: s, avg: sec[s].sum / sec[s].n, n: sec[s].n }; })
        .sort(function (a, b) { return b.avg - a.avg; });
      if (rows.length >= 2) {
        var frag = rows[0], fuerte = rows[rows.length - 1];
        var lbl = function (s) { return window.sectorName ? window.sectorName(s) : ((window.SECTORS9[s] || {}).label || s); };
        out.push({ kind: 'geo', tag: L('panorama sectorial', 'sector overview'), nodes: [],
          text: L('Sector más frágil: <b>', 'Most fragile sector: <b>') + esc(lbl(frag.s)) + L('</b> (NRS medio ', '</b> (average NRS ') + Math.round(frag.avg) +
            L('). El más sólido: <b>', '). The most solid: <b>') + esc(lbl(fuerte.s)) + '</b> (' + Math.round(fuerte.avg) + ').' });
      }
    }

    // 5) concentración geográfica
    var byCountry = {};
    NODES.forEach(function (n) { if (n.country) byCountry[n.country] = (byCountry[n.country] || 0) + 1; });
    var tw = (byCountry['Taiwan'] || 0), cn = (byCountry['China'] || 0);
    if (tw + cn > 0) {
      var pct = Math.round((tw + cn) / NODES.length * 100);
      out.push({ kind: 'geo', tag: L('concentración', 'concentration'), nodes: [],
        text: '<b>' + pct + '%</b>' + L(' del grafo depende de Taiwán (', ' of the graph depends on Taiwan (') + tw + L(') o China (', ') or China (') + cn +
          L(') — el eje geopolítico más sensible de la cadena.', ') — the most sensitive geopolitical axis of the chain.') });
    }
    return out;
  }

  // ── enriquecimiento server (motor de matrices) ──
  function serverInsights() {
    return Promise.all([
      fetch('/api/matrix/metrics').then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; }),
      fetch('/api/matrix/status').then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; }),
    ]).then(function (res) {
      var metrics = res[0], status = res[1];
      if (!metrics || !metrics.chokepoints_top25) return null;
      var out = [];
      var cp = metrics.chokepoints_top25;
      if (cp.length) {
        out.push({ kind: 'shock', tag: L('matriz · ponderado', 'matrix · weighted'), nodes: cp.slice(0, 4).map(function (x) { return x.id; }),
          text: L('Chokepoints reales de la red: <b>', 'Real chokepoints of the network: <b>') + esc(nm(cp[0].id)) + L('</b> arrastra a <b>', '</b> drags down <b>') +
            cp[0].cascade_size + L('</b> empresas; le siguen ', '</b> companies; next come ') +
            cp.slice(1, 3).map(function (x) { return esc(nm(x.id)); }).join(L(' y ', ' and ')) + '.',
          action: "window._insShock('" + cp[0].id + "')", actionLabel: L('ver onda de impacto', 'see the impact wave') });
      }
      if (status && status.active_factors && status.active_factors.length) {
        var f = status.active_factors;
        out.push({ kind: 'factor', tag: L('hiperaristas activas', 'active hyperedges'), nodes: [],
          text: '<b>' + f.length + '</b>' + L(' factor(es) externo(s) modulando la red ahora: ', ' external factor(s) shaping the network now: ') +
            f.slice(0, 3).map(function (x) { return esc(x.label); }).join(', ') + '.' });
      }
      return out;
    });
  }

  window._insShock = function (id) {
    if (typeof window.switchTab === 'function') window.switchTab('map');
    setTimeout(function () { if (window.jumpTo) window.jumpTo(id); if (window.activateStress) setTimeout(function () { window.activateStress(id); }, 150); }, 90);
  };

  window.renderKhipuInsights = function () {
    var el = document.getElementById('an-insights');
    if (!el) return;
    themeRoot(el); ensureStyles();
    el.innerHTML = '<div class="ins-msg" style="font-style:italic">' + L('Generando lecturas de la red…', 'Generating network readings…') + '</div>';
    var base = clientInsights();
    serverInsights().then(function (srv) {
      var list;
      if (srv && srv.length) {
        // el server manda en chokepoints/factores; el cliente aporta riesgo+geo
        var noShock = base.filter(function (b) { return b.kind !== 'shock'; });
        list = srv.concat(noShock);
      } else {
        list = base;
        if (base.length) list.push({ kind: 'oport', tag: L('sugerencia', 'suggestion'), nodes: [],
          text: L('Configura <b>DATABASE_URL</b> en Railway para insights ponderados por el motor de matrices (impacto real, no estimación de topología).',
            'Set <b>DATABASE_URL</b> on Railway for insights weighted by the matrix engine (real impact, not a topology estimate).') });
      }
      el.innerHTML = list.length ? list.map(card).join('')
        : '<div class="ins-msg">' + L('Sin lecturas por ahora — el grafo aún carga.', 'No readings yet — the graph is still loading.') + '</div>';
    });
  };

  /* ── Historial de lecturas (GET /api/matrix/insights/history) ─────────────
     El feed de arriba dice cómo está la red AHORA; esto dice cómo fue
     cambiando. El server guarda una fila por CAMBIO REAL del grafo (dedupe
     por época), no por visita, así que cada entrada es una lectura distinta.
     Sin DATABASE_URL la sección no se dibuja: no hay historia que mostrar. */
  function whenStr(iso) {
    if (!iso) return '';
    var d = new Date(iso);
    if (isNaN(d)) return '';
    return d.toLocaleString(L('es', 'en'), { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
  }

  function historyRow(h) {
    var cards = Array.isArray(h.insights) ? h.insights : [];
    var lead = cards.length ? (cards[0].title || cards[0].detail || '') : '';
    var trig = h.trigger || L('sin disparador', 'no trigger');
    var asOf = h.as_of ? ' · as_of ' + esc(h.as_of) : '';
    return '<div class="ins-hist">'
      + '<div class="ins-hh">'
      +   '<b>' + esc(trig) + '</b>'
      +   '<span class="ins-when">' + esc(whenStr(h.created_at)) + esc(asOf) + '</span>'
      + '</div>'
      + '<div class="ins-meta">'
      +   L('alcanzó ', 'reached ') + '<b>' + (h.affected || 0) + '</b>'
      +   L(' empresas', ' companies')
      +   (cards.length ? ' · ' + cards.length + L(' lecturas', ' readings') : '')
      +   (h.model ? ' · ' + esc(h.model) : '')
      + '</div>'
      + (lead ? '<div class="ins-lead">' + esc(String(lead).slice(0, 220)) + '</div>' : '')
      + '</div>';
  }

  window.renderInsightsHistory = function () {
    var el = document.getElementById('an-history');
    if (!el) return;
    var base = (typeof window.BASE !== 'undefined' && window.BASE) ? window.BASE : '';
    var lang = L('es', 'en');
    themeRoot(el); ensureStyles();
    el.innerHTML = '<div class="ins-msg" style="font-style:italic">'
      + L('Cargando historial…', 'Loading history…') + '</div>';
    fetch(base + '/api/matrix/insights/history?limit=12&lang=' + lang)
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (!d || !d.available) {
          // sin ontología no hay historial — se dice, no se finge
          el.innerHTML = '<div class="ins-msg">'
            + L('El historial necesita la ontología (DATABASE_URL) — sin ella solo hay lectura del momento.',
                'History needs the ontology (DATABASE_URL) — without it only the live reading is available.')
            + '</div>';
          return;
        }
        if (!d.history || !d.history.length) {
          el.innerHTML = '<div class="ins-msg">'
            + L('Aún no hay historial: se guarda una entrada cada vez que el grafo cambia de verdad.',
                'No history yet: one entry is stored each time the graph actually changes.')
            + '</div>';
          return;
        }
        el.innerHTML = d.history.map(historyRow).join('');
      })
      .catch(function () {
        el.innerHTML = '<div class="ins-msg">'
          + L('No se pudo cargar el historial.', 'Could not load the history.') + '</div>';
      });
  };
})();
