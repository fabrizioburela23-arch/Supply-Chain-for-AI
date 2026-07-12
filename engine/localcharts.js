/* ============================================================================
   engine/localcharts.js — GRÁFICOS INSTANTÁNEOS SIN IA (Etapa G, 2026-07-11)
   Feedback de Fabrizio: "los gráficos tardan mucho y muchas veces no los hace
   bien". Causa: TODO pasaba por el LLM (segundos + errores). Solución: los
   pedidos comunes se resuelven AQUÍ, determinísticos, con los datos que ya
   viven en el navegador (NODES, NODE_META, MKT, computeNRS) — 0 ms, 0 errores.
   Solo lo exótico cae al LLM (que además ya tiene caché de 30 min).

   API: window.KhipuLocalCharts.try(query) → spec {type,title,subtitle,data,
   config} compatible con _cvRenderCard, o null si no es un pedido común.
   ============================================================================ */
(function () {
  'use strict';

  var PAL = ['#60a5fa', '#34d399', '#f59e0b', '#f87171', '#a78bfa', '#38bdf8', '#fb923c', '#4ade80'];

  function nrs(id) { try { return (typeof computeNRS === 'function') ? computeNRS(id) : null; } catch (e) { return null; } }
  function meta(id) { return (window.NODE_META || {})[id] || {}; }
  function cap(id) { var c = Number(meta(id).mktcap_b); return isFinite(c) && c > 0 ? c : null; }

  function topN(q, def) {
    var m = q.match(/top\s*(\d{1,2})/) || q.match(/(\d{1,2})\s+(?:empresas|mayores|primer)/);
    var n = m ? parseInt(m[1], 10) : def;
    return Math.max(3, Math.min(20, n || def));
  }

  // extrae empresas mencionadas ("de nvidia, tsmc y asml")
  function companiesIn(q) {
    var out = [];
    if (!window.NODES) return out;
    var resolve = (window.BixbyVoice && window.BixbyVoice._resolveNode)
      ? function (s) { return window.BixbyVoice._resolveNode(s); }
      : function (s) { s = s.toLowerCase(); return NODES.find(function (n) { return (n.label || '').toLowerCase() === s || (n.mkt || '').toLowerCase() === s || n.id.toLowerCase() === s; }); };
    // trocear por separadores típicos
    q.split(/,| y | vs\.? | versus | contra |\bcon\b/).forEach(function (part) {
      part = part.replace(/^.*?\b(?:de|del|entre)\b/, '').replace(/[¿?¡!.]/g, '').trim();
      if (part.length < 2 || part.length > 40) return;
      var n = resolve(part);
      if (n && out.indexOf(n) < 0) out.push(n);
    });
    // pasada completa por si el split no ayudó ("margen de nvidia")
    if (!out.length) {
      var ql = ' ' + q.toLowerCase() + ' ';
      NODES.forEach(function (n) {
        var lbl = (n.label || '').toLowerCase();
        if (lbl.length >= 3 && ql.indexOf(lbl) >= 0 && out.indexOf(n) < 0) out.push(n);
        else if (n.mkt && ql.indexOf(' ' + n.mkt.toLowerCase() + ' ') >= 0 && out.indexOf(n) < 0) out.push(n);
      });
    }
    return out.slice(0, 12);
  }

  function bar(title, subtitle, items, unit) {
    return { type: 'bar', title: title, subtitle: subtitle,
      data: items.map(function (it, i) { return { label: it[0], value: Math.round(it[1] * 100) / 100, color: it[2] || PAL[i % PAL.length] }; }),
      config: { unit: unit || '' } };
  }

  function trySpec(query) {
    if (!window.NODES || !NODES.length) return null;
    var q = ' ' + String(query || '').toLowerCase().trim() + ' ';
    var comps = null;

    // ── 1) top N por riesgo ──
    if (/riesgo|nrs|fr[aá]gil|peligros/.test(q) && /top|mayor|m[aá]s alt|ranking|peores/.test(q)) {
      var n1 = topN(q, 10);
      var rows = NODES.map(function (n) { return [n.label, nrs(n.id)]; })
        .filter(function (r) { return r[1] != null; })
        .sort(function (a, b) { return b[1] - a[1]; }).slice(0, n1)
        .map(function (r) { return [r[0], r[1], r[1] >= 70 ? '#f87171' : r[1] >= 40 ? '#f59e0b' : '#34d399']; });
      return bar('Top ' + n1 + ' por riesgo (NRS)', 'NRS 0-100 · calculado en vivo sobre el grafo', rows, 'NRS');
    }

    // ── 2) márgenes de empresas concretas ──
    if (/margen|márgenes|margins?/.test(q)) {
      comps = companiesIn(q);
      var pool = comps.length >= 2 ? comps
        : NODES.filter(function (n) { return n.margin != null && n.margin > 0; })
            .sort(function (a, b) { return b.margin - a.margin; }).slice(0, topN(q, 10));
      var rows2 = pool.filter(function (n) { return n.margin != null; })
        .map(function (n) { return [n.label, n.margin * 100]; });
      if (rows2.length >= 2) {
        return bar('Márgenes' + (comps.length ? ': ' + pool.map(function (n) { return n.label; }).join(' · ') : ' — top del grafo'),
          'Margen neto/operativo del catálogo (%)', rows2, '%');
      }
    }

    // ── 3) riesgo de empresas concretas ──
    if (/riesgo|nrs/.test(q)) {
      comps = companiesIn(q);
      if (comps.length >= 2) {
        return bar('Riesgo NRS: ' + comps.map(function (n) { return n.label; }).join(' · '),
          'NRS 0-100 · menor es mejor',
          comps.map(function (n) { var v = nrs(n.id) || 0; return [n.label, v, v >= 70 ? '#f87171' : v >= 40 ? '#f59e0b' : '#34d399']; }), 'NRS');
      }
    }

    // ── 4) market cap / capitalización ──
    if (/market ?cap|capitalizaci[oó]n|m[aá]s grandes|mayores empresas/.test(q)) {
      comps = companiesIn(q);
      var pool4 = comps.length >= 2 ? comps
        : NODES.filter(function (n) { return cap(n.id); })
            .sort(function (a, b) { return cap(b.id) - cap(a.id); }).slice(0, topN(q, 10));
      var rows4 = pool4.filter(function (n) { return cap(n.id); }).map(function (n) { return [n.label, cap(n.id)]; });
      if (rows4.length >= 2) return bar('Capitalización de mercado', 'Miles de millones USD ($B)', rows4, '$B');
    }

    // ── 5) por sector (conteo o riesgo medio) ──
    if (/por sector|sectores/.test(q)) {
      var S = window.SECTORS9 || {}, M = window.CAT_TO_SECTOR || {};
      var agg = {};
      NODES.forEach(function (n) {
        var s = M[n.cat] || 'cloud_ia';
        (agg[s] = agg[s] || { n: 0, sum: 0 });
        agg[s].n++;
        var v = nrs(n.id); if (v != null) agg[s].sum += v;
      });
      var wantRisk = /riesgo|nrs/.test(q);
      var rows5 = Object.keys(agg).map(function (k) {
        return [(S[k] || {}).label || k, wantRisk ? agg[k].sum / Math.max(1, agg[k].n) : agg[k].n, (S[k] || {}).color];
      }).sort(function (a, b) { return b[1] - a[1]; });
      return bar(wantRisk ? 'Riesgo medio por sector' : 'Empresas por sector',
        wantRisk ? 'NRS promedio de cada macro-sector' : 'Conteo del catálogo (555)', rows5, wantRisk ? 'NRS' : '');
    }

    // ── 6) por país ──
    if (/por pa[ií]s|pa[ií]ses/.test(q)) {
      var aggP = {};
      NODES.forEach(function (n) { var c = n.country || '—'; aggP[c] = (aggP[c] || 0) + 1; });
      var rows6 = Object.keys(aggP).map(function (k) { return [k, aggP[k]]; })
        .sort(function (a, b) { return b[1] - a[1]; }).slice(0, 12);
      return bar('Empresas por país', 'Concentración geográfica del catálogo', rows6, '');
    }

    // ── 7) comparación general de 2+ empresas (tabla compacta) ──
    if (/compara|comparaci[oó]n|frente a/.test(q)) {
      comps = companiesIn(q);
      if (comps.length >= 2) {
        return { type: 'table', title: 'Comparación: ' + comps.map(function (n) { return n.label; }).join(' vs '),
          subtitle: 'Datos del catálogo en vivo',
          data: comps.map(function (n) {
            var m = meta(n.id);
            return { Empresa: n.label, Ticker: n.mkt || '—', 'NRS riesgo': nrs(n.id),
                     'Margen %': n.margin != null ? Math.round(n.margin * 100) : '—',
                     'Cap $B': cap(n.id) || '—', 'País': n.country || '—',
                     'Fundada': m.founded || '—' };
          }),
          config: { columns: ['Empresa', 'Ticker', 'NRS riesgo', 'Margen %', 'Cap $B', 'País', 'Fundada'] } };
      }
    }

    // ── 8) proveedores / clientes de X (nativo del grafo) ──
    var pc = q.match(/(proveedor(?:es)?|clientes?)\s+(?:de|del)\s+(.+)/);
    if (pc && window.LINKS) {
      var pcn = companiesIn(pc[2]);
      if (pcn.length) {
        var anchor = pcn[0], wantProv = pc[1].indexOf('proveedor') === 0;
        var lid2 = function (v) { return (typeof v === 'object' && v) ? v.id : v; };
        var rows8 = [];
        window.LINKS.forEach(function (l) {
          var s = lid2(l.source), t = lid2(l.target);
          if (wantProv && t === anchor.id && window.NODE_BY_ID[s]) rows8.push([window.NODE_BY_ID[s].label, l.w || 1]);
          if (!wantProv && s === anchor.id && window.NODE_BY_ID[t]) rows8.push([window.NODE_BY_ID[t].label, l.w || 1]);
        });
        rows8.sort(function (a, b) { return b[1] - a[1]; });
        if (rows8.length) {
          return bar((wantProv ? 'Proveedores de ' : 'Clientes de ') + anchor.label + ' (' + rows8.length + ')',
            'Peso de criticidad del vínculo (1-5)', rows8.slice(0, 14), 'w');
        }
      }
    }

    // ── 9) empleados ──
    if (/emplead/.test(q)) {
      comps = companiesIn(q);
      var pool9 = comps.length ? comps
        : NODES.filter(function (n) { return meta(n.id).employees; })
            .sort(function (a, b) { return (meta(b.id).employees || 0) - (meta(a.id).employees || 0); }).slice(0, topN(q, 10));
      var rows9 = pool9.filter(function (n) { return meta(n.id).employees; })
        .map(function (n) { return [n.label, meta(n.id).employees]; });
      if (rows9.length) return bar('Empleados', 'Plantilla según la ficha de cada empresa', rows9, '');
    }

    // ── 10) fundación / más antiguas ──
    if (/fundad|antig/.test(q)) {
      comps = companiesIn(q);
      var pool10 = comps.length ? comps
        : NODES.filter(function (n) { return meta(n.id).founded; })
            .sort(function (a, b) { return (meta(a.id).founded || 3000) - (meta(b.id).founded || 3000); }).slice(0, topN(q, 12));
      var rows10 = pool10.filter(function (n) { return meta(n.id).founded; })
        .map(function (n) { return [n.label, meta(n.id).founded]; });
      if (rows10.length) return bar('Año de fundación', 'Las más antiguas del catálogo', rows10, '');
    }

    // ── 11) scatter riesgo vs margen ──
    if (/(riesgo|nrs).*(margen|márgenes)|(margen|márgenes).*(riesgo|nrs)|scatter|dispersi[oó]n/.test(q)) {
      var pts = NODES.filter(function (n) { return n.margin != null && cap(n.id); })
        .sort(function (a, b) { return cap(b.id) - cap(a.id); }).slice(0, 40)
        .map(function (n) { return { label: n.label, x: Math.round(n.margin * 100), y: nrs(n.id) || 0 }; });
      if (pts.length >= 5) {
        return { type: 'scatter', title: 'Riesgo vs Margen', subtitle: 'Top 40 por capitalización · abajo-derecha = mejor',
          data: pts, config: { x_label: 'Margen %', y_label: 'Riesgo NRS' } };
      }
    }

    // ── 12) treemap por sector ──
    if (/treemap|mapa de (?:sectores|capital)/.test(q)) {
      var S12 = window.SECTORS9 || {}, M12 = window.CAT_TO_SECTOR || {};
      var agg12 = {};
      NODES.forEach(function (n) {
        var s = M12[n.cat] || 'cloud_ia';
        agg12[s] = (agg12[s] || 0) + (cap(n.id) || 0);
      });
      return { type: 'treemap', title: 'Capitalización por sector', subtitle: 'Miles de millones USD',
        data: Object.keys(agg12).map(function (k) {
          return { label: (S12[k] || {}).label || k, value: Math.round(agg12[k]), color: (S12[k] || {}).color };
        }).filter(function (d) { return d.value > 0; }), config: {} };
    }

    // ── 13) mi cartera ──
    if (/cartera|portafolio|portfolio|mis posiciones/.test(q)) {
      var pos = (window.MKT || {}).pos || {};
      var rows13 = Object.keys(pos).map(function (k) {
        var n = NODES.find(function (x) { return x.id === k || x.mkt === k; });
        var tk = (n && n.mkt) || k;
        var qq = ((window.MKT || {}).quotes || {})[tk] || {};
        var qty = typeof pos[k] === 'object' ? (pos[k].qty || pos[k].shares || 0) : pos[k];
        return { Empresa: (n && n.label) || k, Ticker: tk, Cantidad: qty,
                 'Precio': qq.close != null ? '$' + Number(qq.close).toFixed(2) : '—',
                 'Valor': qq.close != null && qty ? '$' + Math.round(qq.close * qty).toLocaleString() : '—' };
      });
      if (rows13.length) {
        return { type: 'table', title: 'Mi cartera', subtitle: rows13.length + ' posiciones · precios en vivo',
          data: rows13, config: { columns: ['Empresa', 'Ticker', 'Cantidad', 'Precio', 'Valor'] } };
      }
    }

    return null;   // no es un pedido común → que lo intente la IA (con caché)
  }

  // ── patrones ASÍNCRONOS (velas del servidor, cacheadas — sin IA) ──────────
  function tryAsync(query) {
    var q = ' ' + String(query || '').toLowerCase().trim() + ' ';
    // precio histórico: "precio de nvidia", "evolución de TSMC", o la consulta
    // ES simplemente una empresa listada
    var m = q.match(/(?:precio|cotizaci[oó]n|evoluci[oó]n|hist[oó]rico|velas|acci[oó]n)\s+(?:de|del)?\s*(.+)/);
    var target = m ? m[1].replace(/[¿?¡!.]/g, '').trim() : String(query || '').trim();
    var comps = companiesIn(target);
    var n = comps.length === 1 ? comps[0] : null;
    if (!n && !m) return Promise.resolve(null);
    if (!n || !n.mkt) return Promise.resolve(null);
    if (!m && target.length > 30) return Promise.resolve(null);   // consulta larga: no es "solo una empresa"
    return fetch((window.BASE || '') + '/api/candles/' + encodeURIComponent(n.mkt))
      .then(function (r) { return r.json(); })
      .then(function (c) {
        if (!c || c.s !== 'ok' || !c.c || c.c.length < 5) return null;
        var up = c.c[c.c.length - 1] >= c.c[0];
        var pct = ((c.c[c.c.length - 1] / c.c[0] - 1) * 100).toFixed(1);
        return { type: 'line',
          title: n.label + ' (' + n.mkt + ') — ~90 días',
          subtitle: (up ? '▲ +' : '▼ ') + pct + '% en el periodo · fuente: mercado en vivo',
          data: [{ label: n.mkt, values: c.c.map(function (v) { return Math.round(v * 100) / 100; }),
                   color: up ? '#34d399' : '#f87171' }],
          config: { series_labels: [n.mkt], unit: '$' } };
      })
      .catch(function () { return null; });
  }

  window.KhipuLocalCharts = {
    try: function (query) {
      try { return trySpec(query); } catch (e) { return null; }
    },
    // patrones que necesitan datos del servidor (velas) — igual sin IA, ~300ms
    tryAsync: function (query) {
      try { return tryAsync(query); } catch (e) { return Promise.resolve(null); }
    },
  };
})();
