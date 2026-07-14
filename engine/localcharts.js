/* ============================================================================
   engine/localcharts.js — GRÁFICOS INSTANTÁNEOS SIN IA (Etapa G, 2026-07-11;
   Etapa I "que no tarden" 2026-07-12).
   Feedback de Fabrizio: "los gráficos tardan full". Estrategia en 4 capas:
   1) PATRONES LOCALES (<100 ms, 0 IA): top riesgo, márgenes, market cap,
      sectores, países, comparar (barras lado a lado), riesgo de X (desglose
      NRS), proveedores/clientes, empleados, fundación, scatter, treemap,
      cartera, cripto top-10 y precio histórico (velas cacheadas).
   2) ESQUELETO INSTANTÁNEO: si el pedido va a la IA, el card muestra al
      instante spinner + "Generando con IA…" (bilingüe ES/EN) — nunca se
      espera "mirando nada".
   3) CACHÉ CLIENTE (localStorage 'kh_chartcache', TTL 1 h, LRU 30): pedir el
      mismo gráfico dos veces = instantáneo. Se implementa interceptando
      fetch('/api/canvas/generate') — así cubre Canvas, Cabina y Bixby sin
      tocar sus archivos. Invalidar: window.KhipuLocalCharts.clearCache().
   4) PREFETCH: al abrir Canvas/Cabina se precalientan /api/candles del
      portafolio (MKT.pos) y del nodo enfocado (máx. 4, silenciosos).

   API pública (NO romper): window.KhipuLocalCharts.try(query) → spec
   {type,title,subtitle,data,config} compatible con _cvRenderCard, o null;
   .tryAsync(query) → Promise<spec|null>; .clearCache(); .prefetch().
   Resolución de empresas: usa window.KhipuResolve.find si existe (guard
   typeof — lo construye otro módulo), con fallback a la búsqueda propia.
   ============================================================================ */
(function () {
  'use strict';

  var PAL = ['#60a5fa', '#34d399', '#f59e0b', '#f87171', '#a78bfa', '#38bdf8', '#fb923c', '#4ade80'];

  /* ── i18n local (regla bilingüe ES/EN — window.LANG / localStorage eco_lang) ── */
  var I18 = {
    es: {
      gen: 'Generando con IA…',
      genHint: 'suele tardar unos segundos · quedará en caché',
      cmpTitle: 'Comparación',
      cmpSub: 'Barra = % del máximo entre comparadas · valor real en la etiqueta · NRS: menor es mejor',
      mRev: 'Ingresos', mMgn: 'Margen', mNrs: 'Riesgo NRS', mEmp: 'Empleados',
      riskOf: 'Riesgo de', riskBd: 'desglose NRS', lowerBetter: 'menor es mejor',
      cryT: 'Top 10 cripto por capitalización',
      cryS: 'Miles de millones USD · verde = subió en 24h',
      riskTopT: 'Top {n} por riesgo (NRS)', riskTopS: 'NRS 0-100 · calculado en vivo sobre el grafo',
      mgnT: 'Márgenes', mgnTop: 'Márgenes — top del grafo', mgnS: 'Margen neto/operativo del catálogo (%)',
      riskCmpT: 'Riesgo NRS', riskCmpS: 'NRS 0-100 · menor es mejor',
      capT: 'Capitalización de mercado', capS: 'Miles de millones USD ($B)',
      secRiskT: 'Riesgo medio por sector', secCntT: 'Empresas por sector',
      secRiskS: 'NRS promedio de cada macro-sector', secCntS: 'Conteo del catálogo',
      ctryT: 'Empresas por país', ctryS: 'Concentración geográfica del catálogo',
      cmpTblS: 'Datos del catálogo en vivo',
      provOf: 'Proveedores de', cliOf: 'Clientes de', pcS: 'Peso de criticidad del vínculo (1-5)',
      empT: 'Empleados', empS: 'Plantilla según la ficha de cada empresa',
      fndT: 'Año de fundación', fndS: 'Las más antiguas del catálogo',
      scT: 'Riesgo vs Margen', scS: 'Top 40 por capitalización · abajo-derecha = mejor', scX: 'Margen %', scY: 'Riesgo NRS',
      tmT: 'Capitalización por sector', tmS: 'Miles de millones USD',
      portT: 'Mi cartera', portS: 'posiciones · precios en vivo',
      lineDays: '~90 días', linePeriod: 'en el periodo · fuente: mercado en vivo',
      radarT: 'Perfil comparado', radarS: '0-100 relativo entre las comparadas · más grande = mejor',
      axRev: 'Ingresos', axMgn: 'Margen', axSafe: 'Seguridad', axEmp: 'Empleados', axCap: 'Cap.',
      colCompany: 'Empresa', colTicker: 'Ticker', colNrs: 'NRS riesgo', colMgn: 'Margen %',
      colCap: 'Cap $B', colCountry: 'País', colFounded: 'Fundada',
      colQty: 'Cantidad', colPrice: 'Precio', colValue: 'Valor',
    },
    en: {
      gen: 'Generating with AI…',
      genHint: 'usually takes a few seconds · will be cached',
      cmpTitle: 'Comparison',
      cmpSub: 'Bar = % of max among compared · real value in label · NRS: lower is better',
      mRev: 'Revenue', mMgn: 'Margin', mNrs: 'NRS risk', mEmp: 'Employees',
      riskOf: 'Risk of', riskBd: 'NRS breakdown', lowerBetter: 'lower is better',
      cryT: 'Top 10 crypto by market cap',
      cryS: 'USD billions · green = up in 24h',
      riskTopT: 'Top {n} by risk (NRS)', riskTopS: 'NRS 0-100 · computed live on the graph',
      mgnT: 'Margins', mgnTop: 'Margins — top of the graph', mgnS: 'Net/operating margin from the catalog (%)',
      riskCmpT: 'NRS risk', riskCmpS: 'NRS 0-100 · lower is better',
      capT: 'Market capitalization', capS: 'USD billions ($B)',
      secRiskT: 'Average risk by sector', secCntT: 'Companies by sector',
      secRiskS: 'Average NRS of each macro-sector', secCntS: 'Catalog count',
      ctryT: 'Companies by country', ctryS: 'Geographic concentration of the catalog',
      cmpTblS: 'Live catalog data',
      provOf: 'Suppliers of', cliOf: 'Customers of', pcS: 'Link criticality weight (1-5)',
      empT: 'Employees', empS: 'Headcount per each company profile',
      fndT: 'Year founded', fndS: 'The oldest in the catalog',
      scT: 'Risk vs Margin', scS: 'Top 40 by market cap · bottom-right = better', scX: 'Margin %', scY: 'NRS risk',
      tmT: 'Market cap by sector', tmS: 'USD billions',
      portT: 'My portfolio', portS: 'positions · live prices',
      lineDays: '~90 days', linePeriod: 'over the period · source: live market',
      radarT: 'Compared profile', radarS: '0-100 relative among compared · bigger = better',
      axRev: 'Revenue', axMgn: 'Margin', axSafe: 'Safety', axEmp: 'Employees', axCap: 'Cap.',
      colCompany: 'Company', colTicker: 'Ticker', colNrs: 'NRS risk', colMgn: 'Margin %',
      colCap: 'Cap $B', colCountry: 'Country', colFounded: 'Founded',
      colQty: 'Qty', colPrice: 'Price', colValue: 'Value',
    },
  };
  function L() {
    try { return String(window.LANG || localStorage.getItem('eco_lang') || 'es').slice(0, 2) === 'en' ? 'en' : 'es'; }
    catch (e) { return 'es'; }
  }
  function TT(k) { var d = I18[L()] || I18.es; return d[k] != null ? d[k] : I18.es[k]; }
  // claves del desglose NRS (app.html las emite en ES) → EN
  var TERM_EN = { 'Geopolítica': 'Geopolitics', 'Cadena': 'Supply chain', 'Margen': 'Margin',
                  'Fundamental': 'Fundamentals', 'Concentración': 'Concentration' };

  function nrs(id) { try { return (typeof computeNRS === 'function') ? computeNRS(id) : null; } catch (e) { return null; } }
  function meta(id) { return (window.NODE_META || {})[id] || {}; }
  function cap(id) { var c = Number(meta(id).mktcap_b); return isFinite(c) && c > 0 ? c : null; }

  // ingresos ($B) parseados de NODE_META.revenue_2025 ("~$21.5B", "$390M (FY2025)")
  // Solo USD: con €/¥/£ devolvemos null para no mezclar monedas.
  function revB(id) {
    var s = String(meta(id).revenue_2025 || '');
    if (!s || /[€¥£]/.test(s)) return null;
    var m = s.match(/\$\s?([\d.,]+)\s?([TBM])/i);
    if (!m) return null;
    var v = parseFloat(m[1].replace(/,/g, ''));
    if (!isFinite(v) || v <= 0) return null;
    var u = m[2].toUpperCase();
    return u === 'T' ? v * 1000 : u === 'M' ? v / 1000 : v;
  }

  function topN(q, def) {
    var m = q.match(/top\s*(\d{1,2})/) || q.match(/(\d{1,2})\s+(?:empresas|mayores|primer)/);
    var n = m ? parseInt(m[1], 10) : def;
    return Math.max(3, Math.min(20, n || def));
  }

  // resolución por el módulo central (si existe) — SIEMPRE con guard typeof
  function _krFind(s) {
    try {
      if (window.KhipuResolve && typeof window.KhipuResolve.find === 'function') {
        var r = window.KhipuResolve.find(s);
        if (r && r.node && r.node.id) r = r.node;
        if (r && r.id && window.NODE_BY_ID && window.NODE_BY_ID[r.id]) return window.NODE_BY_ID[r.id];
        if (r && r.id && r.label) return r;
      }
    } catch (e) {}
    return null;
  }

  // extrae empresas mencionadas ("de nvidia, tsmc y asml")
  function companiesIn(q) {
    var out = [];
    if (!window.NODES) return out;
    var fallback = (window.BixbyVoice && window.BixbyVoice._resolveNode)
      ? function (s) { return window.BixbyVoice._resolveNode(s); }
      : function (s) { s = s.toLowerCase(); return NODES.find(function (n) { return (n.label || '').toLowerCase() === s || (n.mkt || '').toLowerCase() === s || n.id.toLowerCase() === s; }); };
    var resolve = function (s) { return _krFind(s) || fallback(s); };
    // verbos de comando pegados al nombre ("compara nvidia") — quitarlos
    var CMD = /^(?:comp[aá]ra(?:me|r)?|comparaci[oó]n|gr[aá]fic[ao]|graficar?|dibuja|muestra(?:me)?|ens[eé][ñn]ame|ver|riesgo|precio|margen(?:es)?|nrs)\s+/;
    // trocear por separadores típicos
    q.split(/,| y | vs\.? | versus | contra |\bcon\b/).forEach(function (part) {
      part = part.replace(/^.*?\b(?:de|del|entre)\b/, '').replace(/[¿?¡!.]/g, '').trim();
      part = part.replace(CMD, '').trim();
      if (part.length < 2 || part.length > 40) return;
      var n = resolve(part);
      if (n && out.indexOf(n) < 0) out.push(n);
    });
    // pasada completa por si el split no ayudó ("compara nvidia y tsmc")
    if (out.length < 2) {
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

  /* ── comparación lado a lado: ingresos / margen / NRS / empleados ────────── */
  function _compareRows(comps) {
    var mets = [
      { k: TT('mRev'), get: function (n) { return revB(n.id); },
        fmt: function (v) { return '$' + (v >= 100 ? Math.round(v) : v.toFixed(1)) + 'B'; } },
      { k: TT('mMgn'), get: function (n) { return n.margin != null ? n.margin * 100 : null; },
        fmt: function (v) { return Math.round(v) + '%'; } },
      { k: TT('mNrs'), get: function (n) { return nrs(n.id); },
        fmt: function (v) { return String(Math.round(v)); } },
      { k: TT('mEmp'), get: function (n) { var e = meta(n.id).employees; return e && e > 0 ? e : null; },
        fmt: function (v) { return v >= 1000 ? Math.round(v / 1000) + 'k' : String(v); } },
    ];
    var rows = [];
    mets.forEach(function (m) {
      var vals = comps.map(function (n) { return m.get(n); });
      var have = vals.filter(function (v) { return v != null && isFinite(v); });
      if (have.length < 2) return;                       // métrica sin datos suficientes
      var maxAbs = Math.max.apply(null, have.map(Math.abs));
      if (!(maxAbs > 0)) return;
      comps.forEach(function (n, ci) {
        var v = vals[ci];
        if (v == null || !isFinite(v)) return;
        rows.push([m.k + ' · ' + n.label + ' — ' + m.fmt(v),
                   Math.round(v / maxAbs * 100), PAL[ci % PAL.length]]);
      });
    });
    return rows;
  }

  /* ── perfil comparado (radar multi-métrica) — normaliza 5 ejes a 0-100
     relativo entre las empresas comparadas · usa el renderer _cvRadar ────── */
  function _radarSpec(comps) {
    var get = {
      axRev:  function (n) { return revB(n.id); },
      axMgn:  function (n) { return n.margin != null ? Math.max(0, n.margin * 100) : null; },
      axSafe: function (n) { var v = nrs(n.id); return v != null ? Math.max(0, 100 - v) : null; }, // menos riesgo = mejor
      axEmp:  function (n) { var e = meta(n.id).employees; return e && e > 0 ? e : null; },
      axCap:  function (n) { return cap(n.id); },
    };
    var order = ['axRev', 'axMgn', 'axSafe', 'axEmp', 'axCap'];
    var maxByMet = {};
    order.forEach(function (mk) {
      var vals = comps.map(function (n) { return get[mk](n); })
        .filter(function (v) { return v != null && isFinite(v) && v > 0; });
      maxByMet[mk] = vals.length ? Math.max.apply(null, vals) : 0;
    });
    var axesUsed = order.filter(function (mk) { return maxByMet[mk] > 0; });
    if (axesUsed.length < 3) return null;                 // sin datos suficientes → que decida otra vista
    var data = comps.map(function (n) {
      return { label: n.label, values: axesUsed.map(function (mk) {
        var v = get[mk](n);
        if (v == null || !isFinite(v) || maxByMet[mk] <= 0) return 0;
        return Math.round(Math.max(0, v) / maxByMet[mk] * 100);   // 0-100 relativo al grupo
      }) };
    });
    return { type: 'radar',
      title: TT('radarT') + ': ' + comps.map(function (n) { return n.label; }).join(' · '),
      subtitle: TT('radarS'),
      data: data, config: { axes: axesUsed.map(function (mk) { return TT(mk); }) } };
  }

  function trySpec(query) {
    if (!window.NODES || !NODES.length) return null;
    var q = ' ' + String(query || '').toLowerCase().trim() + ' ';
    var comps = null;

    // ── 1) top N por riesgo ──
    if (/riesgo|nrs|risk|fr[aá]gil|peligros/.test(q) && /top|mayor|m[aá]s alt|ranking|peores|highest|riskiest/.test(q)) {
      var n1 = topN(q, 10);
      var rows = NODES.map(function (n) { return [n.label, nrs(n.id)]; })
        .filter(function (r) { return r[1] != null; })
        .sort(function (a, b) { return b[1] - a[1]; }).slice(0, n1)
        .map(function (r) { return [r[0], r[1], r[1] >= 70 ? '#f87171' : r[1] >= 40 ? '#f59e0b' : '#34d399']; });
      return bar(TT('riskTopT').replace('{n}', n1), TT('riskTopS'), rows, 'NRS');
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
        return bar(comps.length ? TT('mgnT') + ': ' + pool.map(function (n) { return n.label; }).join(' · ') : TT('mgnTop'),
          TT('mgnS'), rows2, '%');
      }
    }

    // ── 3) riesgo de empresas concretas ──
    if (/riesgo|nrs|risk/.test(q)) {
      comps = companiesIn(q);
      if (comps.length >= 2) {
        return bar(TT('riskCmpT') + ': ' + comps.map(function (n) { return n.label; }).join(' · '),
          TT('riskCmpS'),
          comps.map(function (n) { var v = nrs(n.id) || 0; return [n.label, v, v >= 70 ? '#f87171' : v >= 40 ? '#f59e0b' : '#34d399']; }), 'NRS');
      }
      // 3b) "riesgo de X" (una sola empresa) → desglose del NRS por componente
      if (comps.length === 1 && typeof window.computeNRSBreakdown === 'function') {
        var bd = null;
        try { bd = window.computeNRSBreakdown(comps[0].id); } catch (e) {}
        if (bd && bd.terms && bd.terms.length) {
          var en = L() === 'en';
          var rowsB = bd.terms.map(function (tm) {
            var k = en ? (TERM_EN[tm.key] || tm.key) : tm.key;
            return [k + ' /' + tm.max + ' — ' + (tm.detail || ''), tm.val, tm.hot ? '#f87171' : '#60a5fa'];
          });
          return bar(TT('riskOf') + ' ' + comps[0].label + ' — ' + TT('riskBd'),
            'NRS ' + bd.total + '/100 · ' + TT('lowerBetter'), rowsB, '');
        }
      }
    }

    // ── 4) market cap / capitalización ──
    if (/market ?cap|capitalizaci[oó]n|m[aá]s grandes|mayores empresas/.test(q)) {
      comps = companiesIn(q);
      var pool4 = comps.length >= 2 ? comps
        : NODES.filter(function (n) { return cap(n.id); })
            .sort(function (a, b) { return cap(b.id) - cap(a.id); }).slice(0, topN(q, 10));
      var rows4 = pool4.filter(function (n) { return cap(n.id); }).map(function (n) { return [n.label, cap(n.id)]; });
      if (rows4.length >= 2) return bar(TT('capT'), TT('capS'), rows4, '$B');
    }

    // ── 5) por sector (conteo o riesgo medio) ──
    if (/por sector|sectores|by sector|sectors/.test(q)) {
      var S = window.SECTORS9 || {}, M = window.CAT_TO_SECTOR || {};
      var agg = {};
      NODES.forEach(function (n) {
        var s = M[n.cat] || 'cloud_ia';
        (agg[s] = agg[s] || { n: 0, sum: 0 });
        agg[s].n++;
        var v = nrs(n.id); if (v != null) agg[s].sum += v;
      });
      var wantRisk = /riesgo|nrs|risk/.test(q);
      var rows5 = Object.keys(agg).map(function (k) {
        return [(S[k] || {}).label || k, wantRisk ? agg[k].sum / Math.max(1, agg[k].n) : agg[k].n, (S[k] || {}).color];
      }).sort(function (a, b) { return b[1] - a[1]; });
      return bar(wantRisk ? TT('secRiskT') : TT('secCntT'),
        wantRisk ? TT('secRiskS') : TT('secCntS') + ' (' + NODES.length + ')', rows5, wantRisk ? 'NRS' : '');
    }

    // ── 6) por país ──
    if (/por pa[ií]s|pa[ií]ses|by countr|countries/.test(q)) {
      var aggP = {};
      NODES.forEach(function (n) { var c = n.country || '—'; aggP[c] = (aggP[c] || 0) + 1; });
      var rows6 = Object.keys(aggP).map(function (k) { return [k, aggP[k]]; })
        .sort(function (a, b) { return b[1] - a[1]; }).slice(0, 12);
      return bar(TT('ctryT'), TT('ctryS'), rows6, '');
    }

    // ── 6·radar) perfil comparado multi-métrica (radar) — bajo pedido ──
    if (/\bradar\b|ara[ñn]a|tela de ara|perfil comparad|multi.?m[eé]tric/.test(q)) {
      comps = companiesIn(q);
      if (comps.length >= 2) {
        var rspec = _radarSpec(comps.slice(0, 5));
        if (rspec) return rspec;
      }
    }

    // ── 7) comparación de 2+ empresas ──
    if (/compara|comparaci[oó]n|frente a|\bvs\b|versus/.test(q)) {
      comps = companiesIn(q);
      // 7a) 2-4 empresas → barras lado a lado (ingresos/margen/NRS/empleados)
      if (comps.length >= 2 && comps.length <= 4) {
        var sideRows = _compareRows(comps);
        if (sideRows.length >= 4) {
          return bar(TT('cmpTitle') + ': ' + comps.map(function (n) { return n.label; }).join(' vs '),
            TT('cmpSub'), sideRows, '%');
        }
      }
      // 7b) fallback: tabla compacta (también para 5+) — columnas bilingües
      if (comps.length >= 2) {
        var cC = TT('colCompany'), cT = TT('colTicker'), cN = TT('colNrs'),
            cM = TT('colMgn'), cP = TT('colCap'), cY = TT('colCountry'), cF = TT('colFounded');
        return { type: 'table', title: TT('cmpTitle') + ': ' + comps.map(function (n) { return n.label; }).join(' vs '),
          subtitle: TT('cmpTblS'),
          data: comps.map(function (n) {
            var m = meta(n.id), o = {};
            o[cC] = n.label; o[cT] = n.mkt || '—'; o[cN] = nrs(n.id);
            o[cM] = n.margin != null ? Math.round(n.margin * 100) : '—';
            o[cP] = cap(n.id) || '—'; o[cY] = n.country || '—'; o[cF] = m.founded || '—';
            return o;
          }),
          config: { columns: [cC, cT, cN, cM, cP, cY, cF] } };
      }
    }

    // ── 8) proveedores / clientes de X (nativo del grafo) ──
    var pc = q.match(/(proveedor(?:es)?|clientes?|suppliers?|customers?)\s+(?:de|del|of)\s+(.+)/);
    if (pc && window.LINKS) {
      var pcn = companiesIn(pc[2]);
      if (pcn.length) {
        var anchor = pcn[0], wantProv = /^(?:proveedor|supplier)/.test(pc[1]);
        var lid2 = function (v) { return (typeof v === 'object' && v) ? v.id : v; };
        var rows8 = [];
        window.LINKS.forEach(function (l) {
          var s = lid2(l.source), t = lid2(l.target);
          if (wantProv && t === anchor.id && window.NODE_BY_ID[s]) rows8.push([window.NODE_BY_ID[s].label, l.w || 1]);
          if (!wantProv && s === anchor.id && window.NODE_BY_ID[t]) rows8.push([window.NODE_BY_ID[t].label, l.w || 1]);
        });
        rows8.sort(function (a, b) { return b[1] - a[1]; });
        if (rows8.length) {
          return bar((wantProv ? TT('provOf') : TT('cliOf')) + ' ' + anchor.label + ' (' + rows8.length + ')',
            TT('pcS'), rows8.slice(0, 14), 'w');
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
      if (rows9.length) return bar(TT('empT'), TT('empS'), rows9, '');
    }

    // ── 10) fundación / más antiguas ──
    if (/fundad|antig/.test(q)) {
      comps = companiesIn(q);
      var pool10 = comps.length ? comps
        : NODES.filter(function (n) { return meta(n.id).founded; })
            .sort(function (a, b) { return (meta(a.id).founded || 3000) - (meta(b.id).founded || 3000); }).slice(0, topN(q, 12));
      var rows10 = pool10.filter(function (n) { return meta(n.id).founded; })
        .map(function (n) { return [n.label, meta(n.id).founded]; });
      if (rows10.length) return bar(TT('fndT'), TT('fndS'), rows10, '');
    }

    // ── 11) scatter riesgo vs margen ──
    if (/(riesgo|nrs).*(margen|márgenes)|(margen|márgenes).*(riesgo|nrs)|scatter|dispersi[oó]n/.test(q)) {
      var pts = NODES.filter(function (n) { return n.margin != null && cap(n.id); })
        .sort(function (a, b) { return cap(b.id) - cap(a.id); }).slice(0, 40)
        .map(function (n) { return { label: n.label, x: Math.round(n.margin * 100), y: nrs(n.id) || 0 }; });
      if (pts.length >= 5) {
        return { type: 'scatter', title: TT('scT'), subtitle: TT('scS'),
          data: pts, config: { x_label: TT('scX'), y_label: TT('scY') } };
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
      return { type: 'treemap', title: TT('tmT'), subtitle: TT('tmS'),
        data: Object.keys(agg12).map(function (k) {
          return { label: (S12[k] || {}).label || k, value: Math.round(agg12[k]), color: (S12[k] || {}).color };
        }).filter(function (d) { return d.value > 0; }), config: {} };
    }

    // ── 13) mi cartera ──
    if (/cartera|portafolio|portfolio|mis posiciones/.test(q)) {
      var pos = (window.MKT || {}).pos || {};
      var pC = TT('colCompany'), pT = TT('colTicker'), pQ = TT('colQty'),
          pP = TT('colPrice'), pV = TT('colValue');
      var rows13 = Object.keys(pos).map(function (k) {
        var n = NODES.find(function (x) { return x.id === k || x.mkt === k; });
        var tk = (n && n.mkt) || k;
        var qq = ((window.MKT || {}).quotes || {})[tk] || {};
        // MKT.pos[id] = {sh, bp} (acciones, precio de compra) — ver savePos()
        var qty = typeof pos[k] === 'object' ? (pos[k].sh || pos[k].qty || pos[k].shares || 0) : pos[k];
        var o = {};
        o[pC] = (n && n.label) || k; o[pT] = tk; o[pQ] = qty;
        o[pP] = qq.close != null ? '$' + Number(qq.close).toFixed(2) : '—';
        o[pV] = qq.close != null && qty ? '$' + Math.round(qq.close * qty).toLocaleString() : '—';
        return o;
      });
      if (rows13.length) {
        return { type: 'table', title: TT('portT'), subtitle: rows13.length + ' ' + TT('portS'),
          data: rows13, config: { columns: [pC, pT, pQ, pP, pV] } };
      }
    }

    return null;   // no es un pedido común → que lo intente la IA (con caché)
  }

  /* ══ CACHÉ EN MEMORIA: velas y cripto (para tryAsync + prefetch) ══════════ */
  var _candles = {};                    // mkt → {t, data} | {t:0, p:Promise}
  var CANDLE_TTL = 5 * 60 * 1000;
  function _getCandles(mkt) {
    var c = _candles[mkt];
    if (c && c.data && Date.now() - c.t < CANDLE_TTL) return Promise.resolve(c.data);
    if (c && c.p) return c.p;
    var p = fetch((window.BASE || '') + '/api/candles/' + encodeURIComponent(mkt))
      .then(function (r) { return r.json(); })
      .then(function (d) { _candles[mkt] = { t: Date.now(), data: d }; return d; })
      .catch(function () { delete _candles[mkt]; return null; });
    _candles[mkt] = { t: 0, p: p };
    return p;
  }

  var _crypto = { t: 0, data: null, p: null };
  function _getCrypto() {
    if (_crypto.data && Date.now() - _crypto.t < 120000) return Promise.resolve(_crypto.data);
    if (_crypto.p) return _crypto.p;
    _crypto.p = fetch((window.BASE || '') + '/api/crypto/markets?per_page=12')
      .then(function (r) { return r.json(); })
      .then(function (d) { _crypto = { t: Date.now(), data: d, p: null }; return d; })
      .catch(function () { _crypto.p = null; return null; });
    return _crypto.p;
  }

  // ── patrones ASÍNCRONOS (datos del servidor, cacheados — sin IA) ──────────
  function tryAsync(query) {
    var q = ' ' + String(query || '').toLowerCase().trim() + ' ';

    // cripto: "cripto", "top cripto", "criptomonedas" → top 10 por market cap
    if (/\bcriptos?\b|\bcryptos?\b|criptomonedas?/.test(q)) {
      return _getCrypto().then(function (d) {
        var assets = (d && d.assets) || [];
        var rowsC = assets.filter(function (a) { return a && a.market_cap > 0; })
          .sort(function (a, b) { return b.market_cap - a.market_cap; }).slice(0, 10)
          .map(function (a) {
            var up = (a.change_24h_pct || 0) >= 0;
            return [(a.rank ? a.rank + '. ' : '') + (a.name || a.id) + ' (' + String(a.symbol || '').toUpperCase() + ')',
                    Math.round(a.market_cap / 1e9), up ? '#34d399' : '#f87171'];
          });
        if (!rowsC.length) return null;
        return bar(TT('cryT'), TT('cryS'), rowsC, '$B');
      });
    }

    // precio histórico: "precio de nvidia", "evolución de TSMC", o la consulta
    // ES simplemente una empresa listada
    var m = q.match(/(?:precio|cotizaci[oó]n|evoluci[oó]n|hist[oó]rico|velas|acci[oó]n)\s+(?:de|del)?\s*(.+)/);
    var target = m ? m[1].replace(/[¿?¡!.]/g, '').trim() : String(query || '').trim();
    var comps = companiesIn(target);
    var n = comps.length === 1 ? comps[0] : null;
    if (!n && !m) return Promise.resolve(null);
    if (!n || !n.mkt) return Promise.resolve(null);
    if (!m && target.length > 30) return Promise.resolve(null);   // consulta larga: no es "solo una empresa"
    return _getCandles(n.mkt)
      .then(function (c) {
        if (!c || c.s !== 'ok' || !c.c || c.c.length < 5) return null;
        var up = c.c[c.c.length - 1] >= c.c[0];
        var pct = ((c.c[c.c.length - 1] / c.c[0] - 1) * 100).toFixed(1);
        return { type: 'line',
          title: n.label + ' (' + n.mkt + ') — ' + TT('lineDays'),
          subtitle: (up ? '▲ +' : '▼ ') + pct + '% ' + TT('linePeriod'),
          data: [{ label: n.mkt, values: c.c.map(function (v) { return Math.round(v * 100) / 100; }),
                   color: up ? '#34d399' : '#f87171' }],
          config: { series_labels: [n.mkt], unit: '$' } };
      })
      .catch(function () { return null; });
  }

  /* ══ 2) ESQUELETO "Generando con IA…" (bilingüe, instantáneo) ═════════════ */
  var _cssDone = false;
  function _injectCSS() {
    if (_cssDone || !document.head) return;
    _cssDone = true;
    var st = document.createElement('style');
    st.id = 'khlc-css';
    st.textContent =
      '.khlc-skel{display:flex;flex-direction:column;gap:7px;width:72%;max-width:340px}' +
      '.khlc-skel-bar{height:9px;border-radius:5px;' +
        'background:linear-gradient(90deg,rgba(122,158,255,.10),rgba(122,158,255,.30),rgba(122,158,255,.10));' +
        'background-size:200% 100%;animation:khlcShimmer 1.2s linear infinite}' +
      '@keyframes khlcShimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}';
    document.head.appendChild(st);
  }

  function _skelHTML(h) {
    return '<div style="height:' + h + 'px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:11px">' +
      '<div class="cv-spinner"></div>' +
      '<div style="font-size:12px;color:#8fa6d4;font-weight:600">✦ ' + TT('gen') + '</div>' +
      '<div style="font-size:10px;color:#5b6b8f">' + TT('genHint') + '</div>' +
      '<div class="khlc-skel">' +
        '<div class="khlc-skel-bar" style="width:92%"></div>' +
        '<div class="khlc-skel-bar" style="width:64%"></div>' +
        '<div class="khlc-skel-bar" style="width:78%"></div>' +
      '</div></div>';
  }

  // localiza los cards pendientes (Canvas / Cabina / Bixby inline) y pinta el
  // esqueleto EN EL MISMO contenedor donde aparecerá el gráfico.
  function _showAISkeleton() {
    try {
      _injectCSS();
      var cards = document.querySelectorAll('.cv-card:not([data-khlc])');
      for (var i = 0; i < cards.length; i++) {
        var card = cards[i];
        var spin = card.querySelector('.cv-spinner');
        if (spin && spin.parentElement && spin.parentElement !== card) {
          // Canvas (app.html) y Cabina (cockpit.js): reemplazar el bloque del spinner
          card.setAttribute('data-khlc', '1');
          spin.parentElement.outerHTML = _skelHTML(180);
        } else if (!spin && card.id && card.id.indexOf('bcc-cv-') === 0 && !card.querySelector('.cv-card-hdr')) {
          // Bixby inline (command_center.js): holder sin header todavía
          card.setAttribute('data-khlc', '1');
          card.innerHTML = _skelHTML(130);
        }
      }
    } catch (e) {}
  }

  /* ══ 3) CACHÉ CLIENTE de respuestas del Canvas IA (localStorage, LRU) ═════ */
  var CK = 'kh_chartcache', CACHE_TTL = 60 * 60 * 1000, CACHE_MAX = 30;

  function _normKey(q) {
    var s = String(q || '').toLowerCase();
    try { s = s.normalize('NFD').replace(new RegExp('[\\u0300-\\u036f]', 'g'), ''); } catch (e) {}
    return s.replace(/[¿?¡!.,;:'"«»()]+/g, ' ').replace(/\s+/g, ' ').trim();
  }
  function _cacheLoad() {
    try { var d = JSON.parse(localStorage.getItem(CK) || 'null'); if (d && d.items && d.items.length !== undefined) return d; } catch (e) {}
    return { v: 1, items: [] };
  }
  function _cacheSave(d) { try { localStorage.setItem(CK, JSON.stringify(d)); } catch (e) { try { localStorage.removeItem(CK); } catch (e2) {} } }
  function _cacheGet(key) {
    var d = _cacheLoad(), now = Date.now(), hit = null, dirty = false;
    var keep = [];
    for (var i = 0; i < d.items.length; i++) {
      var it = d.items[i];
      if (now - (it.t || 0) >= CACHE_TTL) { dirty = true; continue; }   // TTL 1 h
      if (it.k === key) { hit = it; it.last = now; dirty = true; }
      keep.push(it);
    }
    d.items = keep;
    if (dirty) _cacheSave(d);
    return hit;
  }
  function _cachePut(key, spec, model) {
    if (!key || !spec) return;
    var d = _cacheLoad(), now = Date.now();
    d.items = d.items.filter(function (x) { return x.k !== key && now - (x.t || 0) < CACHE_TTL; });
    d.items.push({ k: key, t: now, last: now, spec: spec, model: model || '' });
    while (d.items.length > CACHE_MAX) {                                // LRU: fuera el menos usado
      var oldest = 0;
      for (var i = 1; i < d.items.length; i++) if ((d.items[i].last || 0) < (d.items[oldest].last || 0)) oldest = i;
      d.items.splice(oldest, 1);
    }
    _cacheSave(d);
  }
  function clearCache() {
    try { localStorage.removeItem(CK); } catch (e) {}
    _candles = {};
    _crypto = { t: 0, data: null, p: null };
    return true;
  }

  // Interceptor de fetch SOLO para POST /api/canvas/generate: sirve del caché
  // (instantáneo) o pinta el esqueleto y guarda la respuesta. Cubre Canvas,
  // Cabina y Bixby sin tocar sus archivos. Passthrough para todo lo demás.
  function _wrapFetch() {
    if (window.__khlcFetchWrapped || typeof window.fetch !== 'function') return;
    window.__khlcFetchWrapped = true;
    var _orig = window.fetch;
    window.fetch = function (input, init) {
      try {
        var url = (typeof input === 'string') ? input : ((input && input.url) || '');
        var method = String((init && init.method) || (input && input.method) || 'GET').toUpperCase();
        if (method === 'POST' && /\/api\/canvas\/generate(?:\?|$)/.test(url) &&
            init && typeof init.body === 'string' && typeof Response === 'function') {
          var body = null;
          try { body = JSON.parse(init.body); } catch (e) {}
          var key = body && body.query ? _normKey(body.query) : '';
          if (key) {
            var hit = _cacheGet(key);
            if (hit && hit.spec) {
              return Promise.resolve(new Response(
                JSON.stringify({ spec: hit.spec, model: '⚡ ' + (hit.model || 'cache'), cached: true }),
                { status: 200, headers: { 'Content-Type': 'application/json' } }));
            }
            _showAISkeleton();   // va a la IA: feedback inmediato en el card
            return _orig.apply(this, arguments).then(function (r) {
              try {
                if (r && r.ok && (r.headers.get('content-type') || '').indexOf('application/json') >= 0) {
                  r.clone().json().then(function (d) {
                    if (d && d.spec && !d.error) _cachePut(key, d.spec, d.model);
                  }).catch(function () {});
                }
              } catch (e) {}
              return r;
            });
          }
        }
      } catch (e) {}
      return _orig.apply(this, arguments);
    };
  }
  _wrapFetch();

  /* ══ 4) PREFETCH de velas al abrir Canvas / Cabina (máx. 4, silencioso) ═══ */
  var _lastPrefetch = 0;
  function prefetch() {
    try {
      if (Date.now() - _lastPrefetch < 120000) return;   // throttle 2 min
      _lastPrefetch = Date.now();
      var tickers = [];
      var byId = window.NODE_BY_ID || {};
      // nodo enfocado primero
      var sel = window._selectedNode && byId[window._selectedNode];
      if (sel && sel.mkt) tickers.push(sel.mkt);
      // portafolio del usuario (MKT.pos, claves = ids de nodo)
      var pos = (window.MKT || {}).pos || {};
      Object.keys(pos).forEach(function (id) {
        var n = byId[id];
        var mkt = (n && n.mkt) || null;
        if (mkt && tickers.indexOf(mkt) < 0) tickers.push(mkt);
      });
      tickers = tickers.filter(function (t) {
        var c = _candles[t];
        return !(c && (c.p || (c.data && Date.now() - c.t < CANDLE_TTL)));
      }).slice(0, 4);
      tickers.forEach(function (t) { _getCandles(t).catch(function () {}); });
    } catch (e) {}
  }

  // enganches perezosos: switchTab('canvas') y BixbyCockpit.open se definen
  // DESPUÉS de este archivo → reintentar hasta poder envolverlos.
  var _hooked = { tab: false, cabin: false }, _hookTries = 0;
  function _installHooks() {
    try {
      if (!_hooked.tab && typeof window.switchTab === 'function') {
        var st = window.switchTab;
        window.switchTab = function (tab) {
          if (tab === 'canvas') { try { prefetch(); } catch (e) {} }
          return st.apply(this, arguments);
        };
        _hooked.tab = true;
      }
      if (!_hooked.cabin && window.BixbyCockpit && typeof window.BixbyCockpit.open === 'function') {
        var op = window.BixbyCockpit.open;
        window.BixbyCockpit.open = function () {
          try { prefetch(); } catch (e) {}
          return op.apply(this, arguments);
        };
        _hooked.cabin = true;
      }
    } catch (e) {}
    if ((!_hooked.tab || !_hooked.cabin) && _hookTries++ < 40) setTimeout(_installHooks, 1500);
  }
  _installHooks();

  window.KhipuLocalCharts = {
    try: function (query) {
      try { return trySpec(query); } catch (e) { return null; }
    },
    // patrones que necesitan datos del servidor (velas/cripto) — sin IA.
    // Si tampoco matchean → el pedido va a la IA: pintamos el esqueleto YA.
    tryAsync: function (query) {
      var p;
      try { p = tryAsync(query); } catch (e) { p = Promise.resolve(null); }
      return p.then(
        function (spec) { if (!spec) _showAISkeleton(); return spec; },
        function () { _showAISkeleton(); return null; });
    },
    clearCache: clearCache,
    prefetch: prefetch,
  };
})();
