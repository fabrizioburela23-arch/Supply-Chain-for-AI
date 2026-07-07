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
  function lid(v) { return (typeof v === 'object' && v !== null) ? v.id : v; }
  function nm(id) { var n = window.NODE_BY_ID && window.NODE_BY_ID[id]; return n ? n.label : id; }
  function secColor(id) {
    var n = window.NODE_BY_ID && window.NODE_BY_ID[id];
    if (!n || !window.SECTORS9) return '#00E0FF';
    var s = window.SECTORS9[(window.CAT_TO_SECTOR || {})[n.cat] || 'cloud_ia'];
    return s ? s.color : '#00E0FF';
  }

  var KIND = {
    shock:  { label: 'CHOKEPOINT', color: '#FF4D6A' },
    risk:   { label: 'RIESGO',     color: '#FFB300' },
    factor: { label: 'FACTOR',     color: '#9D6BFF' },
    geo:    { label: 'GEO',        color: '#4D7CFE' },
    oport:  { label: 'OPORTUNIDAD', color: '#2BE38B' },
  };

  function card(ins) {
    var k = KIND[ins.kind] || KIND.shock;
    var chips = (ins.nodes || []).slice(0, 4).map(function (id) {
      return '<span onclick="window._insJump&&window._insJump(\'' + esc(id) + '\')" ' +
        'style="cursor:pointer;font-size:10.5px;padding:2px 8px;border-radius:20px;background:rgba(122,158,255,.08);' +
        'border-left:3px solid ' + secColor(id) + ';color:var(--ink-2,#c8d0e0);white-space:nowrap">' + esc(nm(id)) + '</span>';
    }).join('');
    return '<div class="ins-card" style="border:1px solid rgba(122,158,255,.14);border-radius:12px;padding:13px 15px;' +
      'background:rgba(15,21,34,.5);display:flex;flex-direction:column;gap:8px">' +
      '<div style="display:flex;align-items:center;gap:8px;font-family:\'JetBrains Mono\',monospace;font-size:9.5px;letter-spacing:.1em">' +
        '<span style="padding:2px 8px;border-radius:20px;font-weight:700;background:' + k.color + '22;color:' + k.color + '">' + k.label + '</span>' +
        '<span style="color:var(--ink-3,#7C87A3)">' + esc(ins.tag || '') + '</span></div>' +
      '<div style="font-size:12.5px;line-height:1.45;color:var(--ink,#E8EDFB)">' + ins.text + '</div>' +
      (chips ? '<div style="display:flex;gap:5px;flex-wrap:wrap">' + chips + '</div>' : '') +
      (ins.action ? '<div onclick="' + ins.action + '" style="cursor:pointer;color:#00E0FF;font-size:10.5px;font-family:\'JetBrains Mono\',monospace;margin-top:1px">▸ ' + esc(ins.actionLabel || 'ver') + '</div>' : '') +
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
        out.push({ kind: 'shock', tag: 'topología', nodes: casc.slice(0, 4).map(function (x) { return x.id; }),
          text: '<b>' + esc(nm(top.id)) + '</b> es el mayor punto único de fallo: si cae, arrastra a <b>' + top.aff + ' empresas</b> del grafo.',
          action: "window._insShock('" + top.id + "')", actionLabel: 'simular su caída' });
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
        out.push({ kind: 'risk', tag: inPort ? 'tu cartera' : 'universo', nodes: risky.slice(0, 4).map(function (x) { return x.id; }),
          text: (inPort ? '<b>' + risky.length + '</b> posiciones de tu cartera tienen' : '<b>' + risky.length + '</b> empresas del universo tienen') +
            ' riesgo NRS ≥ 65. La más expuesta: <b>' + esc(nm(risky[0].id)) + '</b> (' + risky[0].nrs + '/100).',
          action: "window.openXRay&&window.openXRay('" + risky[0].id + "')", actionLabel: 'abrir X-Ray' });
      }
    }

    // 3) concentración geográfica
    var byCountry = {};
    NODES.forEach(function (n) { if (n.country) byCountry[n.country] = (byCountry[n.country] || 0) + 1; });
    var tw = (byCountry['Taiwan'] || 0), cn = (byCountry['China'] || 0);
    if (tw + cn > 0) {
      var pct = Math.round((tw + cn) / NODES.length * 100);
      out.push({ kind: 'geo', tag: 'concentración', nodes: [],
        text: '<b>' + pct + '%</b> del grafo depende de Taiwán (' + tw + ') o China (' + cn + ') — el eje geopolítico más sensible de la cadena.' });
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
        out.push({ kind: 'shock', tag: 'matriz · ponderado', nodes: cp.slice(0, 4).map(function (x) { return x.id; }),
          text: 'Chokepoints reales de la red: <b>' + esc(nm(cp[0].id)) + '</b> arrastra a <b>' + cp[0].cascade_size + '</b> empresas; le siguen ' +
            cp.slice(1, 3).map(function (x) { return esc(nm(x.id)); }).join(' y ') + '.',
          action: "window._insShock('" + cp[0].id + "')", actionLabel: 'ver onda de impacto' });
      }
      if (status && status.active_factors && status.active_factors.length) {
        var f = status.active_factors;
        out.push({ kind: 'factor', tag: 'hiperaristas activas', nodes: [],
          text: '<b>' + f.length + '</b> factor(es) externo(s) modulando la red ahora: ' +
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
    el.innerHTML = '<div style="grid-column:1/-1;color:var(--ink-3,#7C87A3);font-size:11.5px;font-style:italic">Generando lecturas de la red…</div>';
    var base = clientInsights();
    serverInsights().then(function (srv) {
      var list;
      if (srv && srv.length) {
        // el server manda en chokepoints/factores; el cliente aporta riesgo+geo
        var noShock = base.filter(function (b) { return b.kind !== 'shock'; });
        list = srv.concat(noShock);
      } else {
        list = base;
        if (base.length) list.push({ kind: 'oport', tag: 'sugerencia', nodes: [],
          text: 'Configura <b>DATABASE_URL</b> en Railway para insights ponderados por el motor de matrices (impacto real, no estimación de topología).' });
      }
      el.innerHTML = list.length ? list.map(card).join('')
        : '<div style="grid-column:1/-1;color:var(--ink-3,#7C87A3);font-size:11.5px">Sin lecturas por ahora — el grafo aún carga.</div>';
    });
  };
})();
