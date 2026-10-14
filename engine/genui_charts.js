/* engine/genui_charts.js — GRÁFICOS de las respuestas visuales (kblocks/1, docs/CHAT_UI_GENERATIVA.md §7.2).
   Portados del Canvas (_cvLine/_cvBar) a tokens --os-* y a CUALQUIER contenedor (sin ids globales): chart.line ·
   chart.bar (h|v) · ranking · chart.candles · comparison · graph.mini · impact.cascade. SVG en código; los números
   llegan del servidor con su unidad (aquí solo se escalan y formatean); el impacto sale SOLO del kernel del servidor.
   Se registra en window.KhipuGenUI (genui.js, cargado ANTES). */
(function (root) {
  'use strict';
  var W = root, G = W.KhipuGenUI;
  if (!G || !G._u) return;
  var U = G._u, h = U.h, sv = U.sv, tip = U.tip, btn = U.btn, T = U.T, fmt = U.fmt, when = U.when, lang = U.lang;
  var gid = 0;

  var CS = {
    es: { idx: 'Índice (inicio = 100)', last: 'último', today: 'hoy', table: 'Tabla', bars: 'Barras', radar: 'Forma', best: 'mejor en esta fila',
      hop: 'Salto ', companies: ' empresas', total: 'empresas golpeadas ≥ {t} % en total', least: 'Menos golpeados (% de daño): ',
      pf: 'Tu cartera', pfHit: 'Golpe estimado', band: '± ', nopos: 'No hay posiciones en tu cartera para estimar el golpe.',
      kernel: 'Motor ', gen: 'generación ', sup: 'Proveedores', cus: 'Clientes', peers: 'Parecidas: ', more: '+{n} más',
      open: 'abrir en el mapa', o: 'Apertura', hi: 'Máx.', lo: 'Mín.', c: 'Cierre', vol: 'Volumen', date: 'Fecha', hopCol: 'Salto', cos: 'Empresas',
      maxp: 'Máx. %', ex: 'Ejemplos', metric: 'Métrica', rank: '#', company: 'Empresa', label: 'Etiqueta', value: 'Valor', from: 'De', to: 'A',
      rel: 'Relación', w: 'Peso', damage: ' de daño', unverified: 'vínculo sin verificar', hopRow: 'Salto {n}: {c} empresas' },
    en: { idx: 'Index (start = 100)', last: 'last', today: 'today', table: 'Table', bars: 'Bars', radar: 'Shape', best: 'best in this row',
      hop: 'Hop ', companies: ' companies', total: 'companies hit ≥ {t}% in total', least: 'Least hit (% damage): ',
      pf: 'Your portfolio', pfHit: 'Estimated hit', band: '± ', nopos: 'There are no positions in your portfolio to estimate the hit.',
      kernel: 'Engine ', gen: 'generation ', sup: 'Suppliers', cus: 'Customers', peers: 'Similar: ', more: '+{n} more',
      open: 'open on the map', o: 'Open', hi: 'High', lo: 'Low', c: 'Close', vol: 'Volume', date: 'Date', hopCol: 'Hop', cos: 'Companies',
      maxp: 'Max %', ex: 'Examples', metric: 'Metric', rank: '#', company: 'Company', label: 'Label', value: 'Value', from: 'From', to: 'To',
      rel: 'Relation', w: 'Weight', damage: ' damage', unverified: 'unverified link', hopRow: 'Hop {n}: {c} companies' }
  };
  function c(k) { var d = CS[lang()]; return d[k] != null ? d[k] : CS.es[k]; }

  // «?» de las cifras (engine/explain.js): aquí por el presupuesto de genui.js (§8); se registran al cargar y en cada pintado
  G._explains = {
    genui_na: { es: { t: 'Sin dato en vivo', b: 'Cuando no hay una fuente confiable en este momento, Khipu muestra «—» y el motivo, en vez de inventar un número.' },
      en: { t: 'No live data', b: 'When there is no reliable source right now, Khipu shows “—” and the reason instead of inventing a number.' } },
    genui_hops: { es: { t: 'Saltos del choque', b: 'Salto 1 = los clientes directos de la empresa que cae. Salto 2 = los clientes de esos clientes. Y así. Las cifras salen del motor de choques del servidor (el mismo de toda la app).' },
      en: { t: 'Shock hops', b: 'Hop 1 = the direct customers of the company that fails. Hop 2 = their customers. And so on. The figures come from the server shock engine (the same one used across the app).' } },
    genui_pf: { es: { t: 'Golpe a tu cartera', b: 'Estimación del motor de choques sobre TUS posiciones, con su banda de error. No es una predicción del precio. Si la calibración es débil, Khipu no da cifra.' },
      en: { t: 'Hit to your portfolio', b: 'Shock-engine estimate on YOUR positions, with its error band. It is not a price forecast. If the calibration is weak, Khipu gives no figure.' } },
    genui_index: { es: { t: 'Índice (inicio = 100)', b: 'Pone todo en la misma escala: el primer día vale 100 y el resto se compara con él. Sirve para comparar formas, no precios.' },
      en: { t: 'Index (start = 100)', b: 'Puts everything on one scale: the first day is 100 and the rest compare to it. Good for comparing shapes, not prices.' } },
    genui_revenue: { es: { t: 'Ingresos', b: 'Todo lo que la empresa vendió en el período, antes de restar costos. Sale de sus estados financieros publicados (la fuente va en cada cifra), convertido a dólares. No es una estimación.' },
      en: { t: 'Revenue', b: 'Everything the company sold in the period, before subtracting costs. It comes from its published financial statements (the source is on each figure), converted to US dollars. Not an estimate.' } },
    genui_net_income: { es: { t: 'Utilidad neta', b: 'Lo que queda después de TODOS los costos, intereses e impuestos. Puede ser negativa (pérdida). Tal como la reportó la empresa, en dólares.' },
      en: { t: 'Net income', b: 'What is left after ALL costs, interest and taxes. It can be negative (a loss). As reported by the company, in US dollars.' } },
    genui_margin: { es: { t: 'Márgenes', b: 'Qué parte de cada dólar de ingresos queda como ganancia: bruto (tras el costo de lo vendido), operativo (tras los gastos de operar) y neto (tras intereses e impuestos). Se calculan dividiendo la cifra reportada entre los ingresos del mismo período.' },
      en: { t: 'Margins', b: 'How much of each dollar of revenue is kept as profit: gross (after the cost of goods), operating (after operating expenses) and net (after interest and taxes). Each is the reported figure divided by the revenue of the same period.' } },
    genui_growth: { es: { t: 'Crecimiento', b: 'Cuánto cambió la cifra frente al período anterior de la lista (año fiscal anterior, o trimestre anterior). Si falta un período en medio, no se calcula.' },
      en: { t: 'Growth', b: 'How much the figure changed vs. the previous period in the list (previous fiscal year, or previous quarter). If a period is missing in between, it is not computed.' } },
    genui_market_share: { es: { t: 'Cuota de mercado', b: 'Parte del mercado que vende esta empresa, según quien lo midió (va en cada fila con su fuente y fecha). Lo investigó una persona para la ficha; distintas fuentes miden distinto.' },
      en: { t: 'Market share', b: 'The slice of the market this company sells, according to whoever measured it (each row shows the source and date). A person researched it for the company card; different sources measure differently.' } },
    genui_market_rank: { es: { t: 'Puesto en el mercado', b: 'Posición (1.º, 2.º…) en ese mercado según la fuente de cada fila. Solo aparecen las empresas cuya ficha investigada lo registra.' },
      en: { t: 'Market rank', b: 'Position (1st, 2nd…) in that market according to each row\'s source. Only companies whose researched card records it appear.' } }
  };
  if (typeof W.explainRegister === 'function') Object.keys(G._explains).forEach(function (k) { try { W.explainRegister(k, G._explains[k]); } catch (e) {} });

  var CSS = '' +
    '.kg-ch{width:100%;display:block;overflow:visible}' +
    '.kg-ch .grid{stroke:var(--os-line);stroke-width:1}' +
    '.kg-ch .axl{fill:var(--os-ink-2);font-size:11px;font-family:inherit}' +
    '.kg-ch .ln{fill:none;stroke-width:2;stroke-linejoin:round;stroke-linecap:round}' +
    '.kg-ch .ar{opacity:0;transition:opacity var(--kg-d3) var(--kg-e) 200ms}.kg-ch.on .ar{opacity:1}' +
    '.kg-ch .xh{stroke:var(--os-ink-3);stroke-width:1;stroke-dasharray:3 3;opacity:0}' +
    '.kg-ch .dt{stroke:var(--os-surface);stroke-width:2;opacity:0}.kg-ch.hov .xh,.kg-ch.hov .dt{opacity:1}' +
    '.kg-ch .an{stroke:var(--os-warn);stroke-dasharray:2 3}' +
    '.kg-lt{display:flex;align-items:flex-end;gap:12px;flex-wrap:wrap;margin-bottom:6px}' +
    '.kg-lt .kg-sub{display:block}.kg-lv{display:flex;align-items:baseline;gap:8px;margin-top:4px}' +
    '.kg-lv .kg-big{margin:0;font-size:28px}.kg-lv .dd{font-size:12px;color:var(--os-ink-2)}' +
    '.kg-seg{margin-left:auto;display:flex;background:var(--os-surface-2);border-radius:10px;padding:3px;gap:2px}' +
    '.kg-seg button{border:0;background:transparent;border-radius:8px;padding:5px 10px;font-size:12px;font-weight:600;color:var(--os-ink-2);cursor:pointer;font-family:inherit}' +
    '.kg-seg button.on{background:var(--os-surface);color:var(--os-ink);box-shadow:0 1px 2px rgba(0,0,0,.12)}' +
    '.kg-lg{display:flex;gap:14px;font-size:12px;font-weight:700;color:var(--os-ink-2);flex-wrap:wrap;align-items:center}' +
    '.kg-lg i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px;vertical-align:-1px}' +
    /* barras / ranking */
    '.kg-rk{display:flex;flex-direction:column;gap:2px}' +
    '.kg-rkr{display:grid;grid-template-columns:var(--kg-lw,128px) minmax(0,1fr) 64px;align-items:center;gap:10px;padding:6px;border-radius:10px}' +
    '.kg-rkr:hover{background:var(--os-surface-2)}.kg-rkr.ent{cursor:pointer}' +
    '.kg-rkl{font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:flex;align-items:center;gap:7px;min-width:0}' +
    '.kg-rkl .n{color:var(--os-ink-2);font-weight:700;min-width:14px}.kg-rkl span{overflow:hidden;text-overflow:ellipsis}' +
    '.kg-rkt{height:14px;position:relative}' +
    '.kg-rkf{position:absolute;top:0;bottom:0;border-radius:0 4px 4px 0;background:var(--kg-a-soft);transform-origin:left center;transform:scaleX(0);transition:transform var(--kg-d3) var(--kg-e)}' +
    '.kg-rkf.neg{border-radius:4px 0 0 4px;transform-origin:right center;background:var(--os-neg)}' +
    '.kg-rkr.lead .kg-rkf:not(.neg),.kg-rkr.hl .kg-rkf:not(.neg){background:var(--kg-a)}' +
    '.kg-go .kg-rkf{transform:scaleX(1)}' +
    '.kg-rkz{position:absolute;top:-3px;bottom:-3px;width:1px;background:var(--os-ink-3)}' +
    '.kg-rkv{font-size:13px;font-weight:700;text-align:right;white-space:nowrap}.kg-rkv small{display:block;font-size:11px;font-weight:600}' +
    '.kg-rka{display:grid;grid-template-columns:var(--kg-lw,128px) minmax(0,1fr) 64px;gap:10px;padding:2px 6px 0;font-size:11px;color:var(--os-ink-2)}' +
    '.kg-rka div:nth-child(2){border-top:1px solid var(--os-line);display:flex;justify-content:space-between;padding-top:3px}' +
    '.kg-cols{display:flex;align-items:flex-end;gap:6px;height:170px;padding-top:16px}' +
    '.kg-col{flex:1;min-width:0;display:flex;flex-direction:column;align-items:center;gap:4px;height:100%;justify-content:flex-end}' +
    '.kg-colb{width:70%;max-width:44px;max-height:calc(100% - 36px);border-radius:5px 5px 0 0;background:var(--kg-a);transform-origin:bottom;transform:scaleY(0);transition:transform var(--kg-d3) var(--kg-e)}' +
    '.kg-colb.neg{background:var(--os-neg)}.kg-go .kg-colb{transform:scaleY(1)}' +
    '.kg-col .v{font-size:11.5px;font-weight:700;flex-shrink:0}.kg-col .l{font-size:11px;color:var(--os-ink-2);max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex-shrink:0}' +
    /* comparar */
    '.kg-cmh{display:flex;align-items:center;gap:10px;margin-bottom:8px;flex-wrap:wrap}' +
    '.kg-cell{display:flex;align-items:center;gap:8px}.kg-cell .bv{font-weight:800;min-width:30px;text-align:right;white-space:nowrap}' +
    '.kg-cell .bt{flex:1;height:8px;background:var(--os-surface-2);border-radius:999px;position:relative;min-width:36px}' +
    '.kg-cell .bt i{position:absolute;left:0;top:0;bottom:0;border-radius:999px;transform-origin:left;transform:scaleX(0);transition:transform var(--kg-d3) var(--kg-e)}' +
    '.kg-go .kg-cell .bt i{transform:scaleX(1)}' +
    '.kg-win-dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--os-ink);flex-shrink:0}' +
    '.kg-gb{display:flex;flex-direction:column;gap:9px}.kg-gbr{display:grid;grid-template-columns:150px minmax(0,1fr);gap:10px;align-items:center}' +
    '.kg-gbr .l{font-size:12.5px;font-weight:600}.kg-gbr .bb{display:flex;flex-direction:column;gap:2px}' +
    '.kg-gbr .bb div{display:flex;align-items:center;gap:8px;font-size:11.5px;font-weight:800}' +
    '.kg-gbr .bb i{height:10px;border-radius:0 4px 4px 0;transform-origin:left;transform:scaleX(0);transition:transform var(--kg-d3) var(--kg-e)}' +
    '.kg-go .kg-gbr .bb i{transform:scaleX(1)}' +
    '.kg-rd .ring{fill:none;stroke:var(--os-line)}.kg-rd .spoke{stroke:var(--os-line)}' +
    '.kg-rd .axl{fill:var(--os-ink-2);font-size:11.5px;font-weight:700}' +
    '.kg-rd .poly{transform-box:view-box;transform-origin:50% 50%;transform:scale(0);transition:transform 600ms cubic-bezier(.3,1.25,.5,1)}' +
    '.kg-go .kg-rd .poly{transform:none}' +
    /* mini grafo */
    '.kg-gm .ed{fill:none;stroke:var(--os-ink-3);opacity:.45;stroke-linecap:round;transition:opacity var(--kg-d1),stroke var(--kg-d1)}' +
    '.kg-gm .ed.hi{stroke:var(--kg-a);opacity:1}.kg-gm .ed.unv{stroke-dasharray:4 4}' +
    '.kg-gm .nd rect{fill:var(--os-surface);stroke:var(--os-ink-3);stroke-width:1.5}' +
    '.kg-gm .nd.risk rect{stroke:var(--os-neg);stroke-width:2}' +
    '.kg-gm .nd.ctr rect{fill:var(--kg-a);stroke:var(--os-surface);stroke-width:3}' +
    '.kg-gm .nd text{fill:var(--os-ink);font-size:12px;font-weight:700}.kg-gm .nd.ctr text{fill:#fff}' +
    '.kg-gm .nd .r{fill:var(--os-ink-2);font-size:10.5px;font-weight:600}' +
    '.kg-gm .nd{cursor:pointer;transform-box:fill-box;transform-origin:center}.kg-gm .nd:hover rect{stroke:var(--kg-a);stroke-width:2.5}' +
    '.kg-gm .nd:focus{outline:none}.kg-gm .nd:focus rect{stroke:var(--kg-a);stroke-width:3}' +
    '.kg-gm .cap{fill:var(--os-ink-2);font-size:11px;font-weight:700;letter-spacing:.04em;text-transform:uppercase}' +
    '.kg-gm .pp{opacity:0;transform:scale(.6);transition:opacity var(--kg-d2) var(--kg-e),transform var(--kg-d3) cubic-bezier(.3,1.4,.5,1)}' +
    '.kg-go .kg-gm .pp,.kg-gm.kg-go .pp{opacity:1;transform:none}' +
    '.kg-gmx{font-size:12px;color:var(--os-ink-2);margin-top:4px}' +
    /* cascada */
    '.kg-cas .seg{stroke:var(--os-surface-3);stroke-width:3;stroke-linecap:round}' +
    '.kg-cas .segf{stroke:var(--os-neg);stroke-width:3;stroke-linecap:round;stroke-dasharray:1;stroke-dashoffset:1;transition:stroke-dashoffset 420ms var(--os-ease-inout,cubic-bezier(.4,0,.2,1))}' +
    '.kg-cas .segf.on{stroke-dashoffset:0}' +
    '.kg-cas .hop circle{fill:var(--os-surface-2);stroke:var(--os-surface-3);stroke-width:2;transition:fill 300ms,stroke 300ms}' +
    '.kg-cas .hop.on circle{fill:color-mix(in srgb,var(--os-neg) 22%,var(--os-surface));stroke:var(--os-neg)}' +
    '.kg-cas text{font-size:11.5px;font-weight:700;fill:var(--os-ink-2);text-anchor:middle}' +
    '.kg-cas .org circle.c{fill:var(--os-neg)}.kg-cas .org text{fill:#fff;font-weight:800}' +
    '.kg-cas .ring{fill:none;stroke:var(--os-neg);stroke-width:2;opacity:0;transform-box:fill-box;transform-origin:center}' +
    '.kg-cas.go .ring{animation:kgRing 1.4s var(--kg-e) 3}.kg-cas.go .ring.r2{animation-delay:.45s}' +
    '@keyframes kgRing{0%{opacity:.7;transform:scale(1)}100%{opacity:0;transform:scale(2.4)}}' +
    '.kg-hops{display:flex;flex-direction:column;gap:8px;margin-top:8px}' +
    '.kg-hp{display:grid;grid-template-columns:118px minmax(0,1fr);gap:4px 12px;align-items:center;opacity:.35;transition:opacity var(--kg-d3)}.kg-hp.on{opacity:1}' +
    '.kg-hpl{font-size:12.5px;font-weight:700}.kg-hpl small{display:block;color:var(--os-ink-2);font-weight:600;font-size:11px}' +
    '.kg-hpb{display:flex;align-items:center;gap:10px;min-width:0}.kg-hpt{flex:1;height:16px;position:relative}' +
    '.kg-hpf{position:absolute;left:0;top:0;bottom:0;border-radius:0 4px 4px 0;background:var(--os-neg);transform-origin:left;transform:scaleX(0);transition:transform 520ms var(--kg-e)}' +
    '.kg-hp.on .kg-hpf{transform:scaleX(1)}.kg-hpv{font-size:13px;font-weight:800;min-width:96px;white-space:nowrap;text-align:right}' +
    '.kg-hpc{grid-column:2;display:flex;flex-wrap:wrap;gap:5px}' +
    '.kg-hpc span{font-size:11.5px;font-weight:600;background:var(--os-surface-2);border-radius:999px;padding:2px 9px;opacity:0;transform:translateY(4px);transition:opacity var(--kg-d2),transform var(--kg-d2)}' +
    '.kg-hp.on .kg-hpc span{opacity:1;transform:none}' +
    '.kg-cast{display:flex;align-items:baseline;gap:8px;margin-top:12px;padding-top:10px;border-top:1px solid var(--os-line);font-size:13px;color:var(--os-ink-2);flex-wrap:wrap}' +
    '.kg-cast b{font-size:22px;color:var(--os-ink);font-weight:800}' +
    '.kg-casx{font-size:12px;color:var(--os-ink-2);margin-top:6px;line-height:1.5}' +
    '.kg-pf{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:12px;align-items:center;margin-top:12px;padding-top:12px;border-top:1px solid var(--os-line)}' +
    '.kg-pfi{width:36px;height:36px;border-radius:11px;background:var(--os-surface-2);display:flex;align-items:center;justify-content:center;font-size:17px}' +
    '.kg-pfn{font-weight:700;font-size:13.5px;display:flex;align-items:center;gap:6px}.kg-pfs{font-size:12px;color:var(--os-ink-2)}' +
    '.kg-pfv{font-size:22px;font-weight:800;letter-spacing:-.02em;white-space:nowrap;text-align:right}.kg-pfv small{display:block;font-size:12px;font-weight:600;color:var(--os-ink-2)}' +
    '.kg-pfv.bad{color:var(--os-bad-ink)}' +
    '.kg-compact .kg-rkr,.kg-compact .kg-rka{grid-template-columns:var(--kg-lw) minmax(0,1fr) minmax(54px,auto);gap:8px}' +
    '.kg-compact .kg-hp{grid-template-columns:1fr}.kg-compact .kg-hpc{grid-column:1}.kg-compact .kg-gbr{grid-template-columns:1fr}' +
    '.kg-compact .kg-cell{gap:5px}.kg-compact .kg-cell .bt{display:none}.kg-compact .kg-win-dot{display:none}' +
    '.kg-compact .kg-lv .kg-big{font-size:24px}.kg-compact .kg-pf{grid-template-columns:auto minmax(0,1fr)}.kg-compact .kg-pfv{grid-column:1/-1;text-align:left}';
  (function () {
    var d = W.document; if (!d || !d.head || d.getElementById('kg-styles-charts')) return;
    var st = d.createElement('style'); st.id = 'kg-styles-charts'; st.textContent = CSS; d.head.appendChild(st);
  })();

  // color de la serie i: A y B validados (--kg-a / --kg-b); 3.ª+ de la paleta categórica del Canvas (cvCol)
  function col(i) { return i === 0 ? 'var(--kg-a)' : i === 1 ? 'var(--kg-b)' : (typeof W.cvCol === 'function' ? W.cvCol(i) : '#8a8577'); }
  function paint(el, prop, v) { el.style.setProperty(prop, v); return el; }   // CSSOM (la CSP lo permite siempre)
  function ts(s) { s = String(s || ''); var x = Date.parse(/^\d{4}-\d{2}-\d{2}$/.test(s) ? s + 'T00:00:00Z' : s.replace(' ', 'T')); return isFinite(x) ? x : null; }
  function niceTicks(mn, mx, n) {
    var span = mx - mn; if (!(span > 0)) return [mn];
    var raw = span / n, p = Math.pow(10, Math.floor(Math.log10(raw))), m = raw / p;
    var step = (m < 1.5 ? 1 : m < 3 ? 2 : m < 7 ? 5 : 10) * p, out = [];
    for (var v = Math.ceil(mn / step) * step; v <= mx + step * 1e-9; v += step) out.push(+v.toFixed(10));
    return out;
  }
  function short(v, unit) {   // etiqueta de eje: sin decimales de más
    if (unit === 'USD' || unit === 'CCY' || unit === 'index' || unit === 'none' || unit === 'ratio') return fmt(v, 'none', { precision: Math.abs(v) >= 100 ? 0 : Math.abs(v) >= 10 ? 1 : 2 });
    return fmt(v, unit, { precision: Math.abs(v) >= 100 ? 0 : 1 });
  }
  function entClick(el, e, b, ctx, kind) {
    if (!e || !U.entId(e)) return;
    U.linkify(el, function () { U.runAction({ kind: kind || 'open_dossier', entity: e }, b, ctx); });
  }
  function grad(svg, color) {
    var id = 'kgG' + (++gid), defs = sv('defs'), lg = sv('linearGradient', { id: id, x1: 0, y1: 0, x2: 0, y2: 1 });
    lg.appendChild(paint(paint(sv('stop', { offset: '0', 'stop-opacity': '.22' }), 'stop-color', color), 'stop-opacity', '.22'));
    lg.appendChild(paint(paint(sv('stop', { offset: '1', 'stop-opacity': '0' }), 'stop-color', color), 'stop-opacity', '0'));
    defs.appendChild(lg); svg.appendChild(defs);
    return 'url(#' + id + ')';
  }
  function lastPoint(s) {
    var p = s.points || [];
    for (var i = p.length - 1; i >= 0; i--) if (Array.isArray(p[i]) && typeof p[i][1] === 'number') return p[i];
    return null;
  }

  /* ── chart.line (full | spark): cierres o métrica en el tiempo; hasta 4 series ── */
  G.register('chart.line', {
    render: function (el, b, ctx) {
      var d = b.data || {}, series = (d.series || []).slice(0, 4), spark = d.variant === 'spark', narrow = ctx.compact;
      var unit = d.rebased ? 'index' : ((series[0] && series[0].values && series[0].values.unit) || 'none');
      var cur = (series[0] && series[0].values) || {};
      if (!spark) {
        var top = h('div', 'kg-lt'), left = h('div');
        left.appendChild(h('span', 'kg-sub', d.rebased ? c('idx') : (T(cur.label) || T(series[0] && series[0].name))));
        var lp = series[0] && lastPoint(series[0]);
        if (lp) {
          var lv = h('div', 'kg-lv'), big = h('div', 'kg-big kg-n'), pp = U.parts(lp[1], unit, { currency: cur.currency });
          big.appendChild(h('span', null, pp.pre + pp.num)); if (pp.suf.trim()) big.appendChild(h('small', null, pp.suf.trim()));
          big.setAttribute('aria-label', pp.text);
          lv.appendChild(big); lv.appendChild(h('span', 'dd', c('last') + ' · ' + when(lp[0])));
          if (d.rebased) { var q = U.qBtn('genui_index'); if (q) lv.appendChild(q); }
          left.appendChild(lv);
        }
        top.appendChild(left);
        if (series.length > 1) {
          var lg = h('div', 'kg-lg');
          series.forEach(function (s, i) { var sp = h('span'); sp.appendChild(paint(h('i'), 'background', col(i))); sp.appendChild(W.document.createTextNode(T(s.name))); lg.appendChild(sp); });
          top.appendChild(lg);
        }
        var rg = (d.ranges || []).filter(function (r) { return /^(1M|3M|6M|1Y|2Y|5Y)$/.test(r); });
        if (rg.length > 1) {
          var seg = h('div', 'kg-seg'); seg.setAttribute('role', 'group');
          rg.forEach(function (r) {
            var lab = lang() === 'es' ? r.replace('Y', 'A') : r;
            var x = btn(r === d.range ? 'on' : '', lab, function () { if (r !== d.range) U.runAction({ kind: 'set_range', range: r, label: { es: r, en: r } }, b, ctx); });
            x.setAttribute('aria-pressed', r === d.range ? 'true' : 'false'); seg.appendChild(x);
          });
          top.appendChild(seg);
        }
        el.appendChild(top);
      }
      var Wd = narrow ? 360 : 600, Hd = spark ? 64 : (narrow ? 180 : 200), P = spark ? { l: 2, r: 2, t: 6, b: 6 } : { l: 6, r: 44, t: 10, b: 22 };
      var all = [], tmin = Infinity, tmax = -Infinity;
      var S = series.map(function (s) {
        var pts = (s.points || []).map(function (p) { return Array.isArray(p) ? [ts(p[0]), typeof p[1] === 'number' && isFinite(p[1]) ? p[1] : null, p[0]] : null; })
          .filter(function (p) { return p && p[0] != null; });
        pts.forEach(function (p) { if (p[0] < tmin) tmin = p[0]; if (p[0] > tmax) tmax = p[0]; if (p[1] != null) all.push(p[1]); });
        return pts;
      });
      var svg = sv('svg', { viewBox: '0 0 ' + Wd + ' ' + Hd, role: 'img', 'aria-label': T(b.alt) || T(b.title) }, 'kg-ch');
      if (!all.length) { el.appendChild(svg); return null; }
      var mn = Math.min.apply(null, all), mx = Math.max.apply(null, all), pad = (mx - mn) * 0.08 || Math.abs(mx) * 0.04 || 1;
      mn -= pad; mx += pad;
      var X = function (t0) { return P.l + (tmax > tmin ? (t0 - tmin) / (tmax - tmin) : 0.5) * (Wd - P.l - P.r); };
      var Y = function (v) { return P.t + (1 - (v - mn) / (mx - mn || 1)) * (Hd - P.t - P.b); };
      if (!spark) {
        niceTicks(mn, mx, 3).forEach(function (v) {
          svg.appendChild(sv('line', { x1: P.l, x2: Wd - P.r, y1: Y(v).toFixed(1), y2: Y(v).toFixed(1) }, 'grid'));
          var tx = sv('text', { x: Wd - P.r + 6, y: (Y(v) + 4).toFixed(1) }, 'axl'); tx.textContent = short(v, unit); svg.appendChild(tx);
        });
        var t0 = sv('text', { x: P.l, y: Hd - 4 }, 'axl'); t0.textContent = when(S[0][0] ? S[0][0][2] : ''); svg.appendChild(t0);
        var t1 = sv('text', { x: Wd - P.r, y: Hd - 4, 'text-anchor': 'end' }, 'axl'); var lpp = S[0][S[0].length - 1]; t1.textContent = lpp ? when(lpp[2]) : ''; svg.appendChild(t1);
      }
      var lines = [], areas = [];
      S.forEach(function (pts, si) {
        var dd = '', on = false, first = null, lastX = null;
        pts.forEach(function (p) { if (p[1] == null) { on = false; return; } var x = X(p[0]).toFixed(1); dd += (on ? 'L' : 'M') + x + ' ' + Y(p[1]).toFixed(1) + ' '; if (first == null) first = x; lastX = x; on = true; });
        if (!dd) return;
        if (S.length === 1 && !spark) {
          var ar = sv('path', { d: dd + 'L' + lastX + ' ' + (Hd - P.b) + ' L' + first + ' ' + (Hd - P.b) + ' Z', fill: grad(svg, col(0)) }, 'ar');
          svg.appendChild(ar); areas.push(ar);
        }
        var ln = paint(sv('path', { d: dd.trim(), pathLength: '1', 'stroke-dasharray': '1', 'stroke-dashoffset': '1' }, 'ln'), 'stroke', col(si));
        svg.appendChild(ln); lines.push(ln);
      });
      (d.annotations || []).slice(0, 6).forEach(function (a) {
        var x = ts(a.x); if (x == null || x < tmin || x > tmax) return;
        var al = sv('line', { x1: X(x).toFixed(1), x2: X(x).toFixed(1), y1: P.t, y2: Hd - P.b }, 'an'); tip(al, T(a.label), when(a.x));
        svg.appendChild(al);
      });
      if (!spark) {
        var xh = sv('line', { x1: 0, x2: 0, y1: P.t, y2: Hd - P.b }, 'xh'); svg.appendChild(xh);
        var dots = S.map(function (p, si) { var dt = paint(sv('circle', { r: 4.5, cx: -10, cy: -10 }, 'dt'), 'fill', col(si)); svg.appendChild(dt); return dt; });
        var hit = sv('rect', { x: P.l, y: 0, width: Wd - P.l - P.r, height: Hd, fill: 'transparent' }); paint(hit, 'cursor', 'crosshair'); svg.appendChild(hit);
        hit.addEventListener('pointermove', function (e) {
          var r = svg.getBoundingClientRect(), tt = tmin + ((e.clientX - r.left) / (r.width || 1) * Wd - P.l) / (Wd - P.l - P.r) * (tmax - tmin);
          var rows = [], X0 = null;
          S.forEach(function (pts, si) {
            var best = null; pts.forEach(function (p) { if (p[1] != null && (best == null || Math.abs(p[0] - tt) < Math.abs(best[0] - tt))) best = p; });
            if (!best) { dots[si].setAttribute('cx', -10); return; }
            if (X0 == null) X0 = X(best[0]);
            dots[si].setAttribute('cx', X(best[0]).toFixed(1)); dots[si].setAttribute('cy', Y(best[1]).toFixed(1));
            rows.push((S.length > 1 ? T(series[si].name) + ': ' : '') + fmt(best[1], unit, { currency: cur.currency }) + (si === 0 ? ' · ' + when(best[2]) : ''));
          });
          if (X0 != null) { xh.setAttribute('x1', X0.toFixed(1)); xh.setAttribute('x2', X0.toFixed(1)); }
          svg.classList.add('hov');
          hit.setAttribute('data-kg-tip', rows.join(' · ')); hit.setAttribute('data-kg-tip2', (cur.src || '') + (cur.as_of ? ' · ' + when(cur.as_of) : ''));
        });
        hit.addEventListener('pointerleave', function () { svg.classList.remove('hov'); });
      } else {
        var lp2 = series[0] && lastPoint(series[0]);
        if (lp2) tip(svg, fmt(lp2[1], unit, { currency: cur.currency }) + ' · ' + when(lp2[0]), cur.src || '');
      }
      el.appendChild(svg);
      return { go: function (inst) { svg.classList.add('on'); lines.forEach(function (l, i) { if (inst) U.draw(l, true); else setTimeout(function () { U.draw(l, false, 800); }, i * 80); }); } };
    },
    toTable: function (b) {
      var series = ((b.data || {}).series || []).slice(0, 4), rows = {}, order = [];
      series.forEach(function (s, si) { (s.points || []).forEach(function (p) { var k = String(p[0]); if (!rows[k]) { rows[k] = []; order.push(k); } rows[k][si] = p[1]; }); });
      var unit = (b.data || {}).rebased ? 'index' : ((series[0] && series[0].values || {}).unit);
      return { columns: [c('date')].concat(series.map(function (s) { return T(s.name); })), rows: order.map(function (k) { return [k].concat(series.map(function (s, si) { return rows[k][si] == null ? '—' : fmt(rows[k][si], unit); })); }) };
    },
    // alto real medido en Chromium (lote J): cabecera ~135 px + el SVG, que escala con el ancho (360×180 angosto, 600×200)
    height: function (b, w) { return (b.data && b.data.variant === 'spark') ? 110 : Math.round(w < 520 ? 133 + w / 2 : 141 + w / 3); }
  });

  /* ── chart.bar (h: filas como _cvBar; v: columnas; divergente con línea de cero) ── */
  function barRows(el, items, unit, b, ctx, opt) {
    opt = opt || {};
    var vals = items.map(function (it) { return typeof it.v === 'number' && isFinite(it.v) ? it.v : null; });
    var maxPos = Math.max.apply(null, [0].concat(vals.filter(function (v) { return v != null; }))), maxNeg = Math.max.apply(null, [0].concat(vals.filter(function (v) { return v != null; }).map(function (v) { return -v; })));
    var span = (maxPos + maxNeg) || 1, zero = maxNeg / span * 100, any = items.some(function (it) { return it.highlight; });
    var wrap = h('div', 'kg-rk'), longest = 0;
    items.forEach(function (it, i) {
      var v = vals[i], lab = it.entity ? it.entity.label : T(it.label);
      longest = Math.max(longest, String(lab).length);
      var row = h('div', 'kg-rkr' + ((opt.lead && i === 0) || it.highlight || (!any && !opt.lead) ? ' hl' : '') + (it.entity ? ' ent' : ''));
      var l = h('div', 'kg-rkl'); if (opt.rank) l.appendChild(h('span', 'n', String(it.rank != null ? it.rank : i + 1))); l.appendChild(h('span', null, lab)); row.appendChild(l);
      var tr = h('div', 'kg-rkt');
      if (maxNeg) tr.appendChild(paint(h('div', 'kg-rkz'), 'left', zero.toFixed(2) + '%'));
      if (v != null) {
        var w = Math.max(.6, Math.abs(v) / span * 100), f = h('i', 'kg-rkf' + (v < 0 ? ' neg' : ''));
        paint(f, 'width', w.toFixed(2) + '%'); paint(f, 'left', (v < 0 ? zero - w : zero).toFixed(2) + '%');
        paint(f, 'transition-delay', Math.min(i, 8) * 60 + 'ms');
        tr.appendChild(f);
      }
      row.appendChild(tr);
      var vv = h('div', 'kg-rkv kg-n', v == null ? '—' : fmt(v, unit.unit, { currency: unit.currency, compact: true }));
      if (it.delta && typeof it.delta.v === 'number') vv.appendChild(h('small', it.delta.v > 0 ? 'kg-up' : it.delta.v < 0 ? 'kg-dn' : null, (it.delta.v > 0 ? '▲ ' : it.delta.v < 0 ? '▼ ' : '') + U.parts(it.delta.v, it.delta.unit, { sign: true }).text));
      row.appendChild(vv);
      tip(row, lab + ': ' + (v == null ? '—' : fmt(v, unit.unit, { currency: unit.currency })), (it.note ? T(it.note) + ' · ' : '') + (unit.src || '') + ' · ' + when(it.as_of || unit.as_of));
      entClick(row, it.entity, b, ctx);
      wrap.appendChild(row);
    });
    var lw = Math.min(ctx.compact ? 118 : 150, Math.max(70, longest * 8 + (opt.rank ? 32 : 10)));
    paint(wrap, '--kg-lw', Math.round(lw) + 'px');
    var ax = h('div', 'kg-rka'); paint(ax, '--kg-lw', Math.round(lw) + 'px');
    ax.appendChild(h('div')); var mid = h('div'); mid.appendChild(h('span', null, maxNeg ? short(-maxNeg, unit.unit) : '0')); mid.appendChild(h('span', null, T(unit.label) || short(maxPos, unit.unit))); ax.appendChild(mid); ax.appendChild(h('div'));
    wrap.appendChild(ax);
    wrap.setAttribute('role', 'img'); wrap.setAttribute('aria-label', T(b.alt) || T(b.title));
    el.appendChild(wrap);
    return wrap;
  }
  G.register('chart.bar', {
    render: function (el, b, ctx) {
      var d = b.data || {}, items = (d.items || []).slice(0, 30), unit = d.values || {};
      if (d.sort === 'desc' || d.sort === 'asc') items.sort(function (a, z) { var x = typeof a.v === 'number' ? a.v : -Infinity, y = typeof z.v === 'number' ? z.v : -Infinity; return d.sort === 'desc' ? y - x : x - y; });
      if (d.orientation === 'v' && !ctx.compact) {
        var vals = items.map(function (it) { return typeof it.v === 'number' ? Math.abs(it.v) : 0; }), mx = Math.max.apply(null, [0].concat(vals)) || 1;
        var cols = h('div', 'kg-cols'); cols.setAttribute('role', 'img'); cols.setAttribute('aria-label', T(b.alt) || T(b.title));
        items.forEach(function (it, i) {
          var cc = h('div', 'kg-col'), lab = it.entity ? it.entity.label : T(it.label);
          cc.appendChild(h('div', 'v kg-n', typeof it.v === 'number' ? fmt(it.v, unit.unit, { currency: unit.currency, compact: true }) : '—'));
          var bar = h('div', 'kg-colb' + (it.v < 0 ? ' neg' : '')); paint(bar, 'height', (vals[i] / mx * 100).toFixed(1) + '%'); paint(bar, 'transition-delay', Math.min(i, 8) * 50 + 'ms');
          cc.appendChild(bar); cc.appendChild(h('div', 'l', lab));
          tip(cc, lab + ': ' + fmt(it.v, unit.unit, { currency: unit.currency }), (unit.src || '') + ' · ' + when(it.as_of || unit.as_of));
          entClick(cc, it.entity, b, ctx);
          cols.appendChild(cc);
        });
        el.appendChild(cols);
        return { go: function () { el.classList.add('kg-go'); } };
      }
      barRows(el, items, unit, b, ctx, {});
      return { go: function () { el.classList.add('kg-go'); } };
    },
    toTable: function (b) {
      var d = b.data || {}, u = d.values || {};
      return { columns: [c('label'), T(u.label) || c('value')], rows: (d.items || []).map(function (it) { return [it.entity ? it.entity.label : T(it.label), fmt(it.v, u.unit, { currency: u.currency })]; }) };
    }
  });

  /* ── ranking: lista ordenada con barra, delta y nota ── */
  G.register('ranking', {
    render: function (el, b, ctx) {
      var d = b.data || {}, items = (d.items || []).slice(0, 20).slice().sort(function (a, z) { return (a.rank || 0) - (z.rank || 0); });
      barRows(el, items, d.metric || {}, b, ctx, { rank: true, lead: true });
      return { go: function () { el.classList.add('kg-go'); } };
    },
    toTable: function (b) {
      var d = b.data || {}, m = d.metric || {};
      return { columns: [c('rank'), c('company'), T(m.label) || c('value')], rows: (d.items || []).map(function (it) { return [String(it.rank), (it.entity || {}).label || '', fmt(it.v, m.unit, { currency: m.currency })]; }) };
    },
    height: function (b) { return 70 + Math.min(20, ((b.data || {}).items || []).length) * 34; }
  });

  /* ── chart.candles: velas OHLC (+ volumen) ── */
  G.register('chart.candles', {
    render: function (el, b, ctx) {
      var d = b.data || {}, s = d.series || {}, u = s.values || {}, pts = (s.points || []).slice(-400).filter(function (p) { return Array.isArray(p) && p.length >= 5; });
      var Wd = ctx.compact ? 360 : 600, Hd = ctx.compact ? 190 : 220, P = { l: 6, r: 44, t: 10, b: 22 };
      var svg = sv('svg', { viewBox: '0 0 ' + Wd + ' ' + Hd, role: 'img', 'aria-label': T(b.alt) || T(b.title) }, 'kg-ch');
      if (!pts.length) { el.appendChild(svg); return null; }
      var lo = Math.min.apply(null, pts.map(function (p) { return p[3]; })), hi = Math.max.apply(null, pts.map(function (p) { return p[2]; }));
      var pad = (hi - lo) * 0.06 || 1; lo -= pad; hi += pad;
      var vh = d.volume ? 34 : 0, ph = Hd - P.t - P.b - vh, n = pts.length, step = (Wd - P.l - P.r) / n, bw = Math.max(1.5, Math.min(12, step * 0.62));
      var Y = function (v) { return P.t + (1 - (v - lo) / (hi - lo)) * ph; };
      niceTicks(lo, hi, 3).forEach(function (v) {
        svg.appendChild(sv('line', { x1: P.l, x2: Wd - P.r, y1: Y(v).toFixed(1), y2: Y(v).toFixed(1) }, 'grid'));
        var tx = sv('text', { x: Wd - P.r + 6, y: (Y(v) + 4).toFixed(1) }, 'axl'); tx.textContent = short(v, u.unit); svg.appendChild(tx);
      });
      var vmax = Math.max.apply(null, [1].concat(pts.map(function (p) { return typeof p[5] === 'number' ? p[5] : 0; })));
      pts.forEach(function (p, i) {
        var x = P.l + step * (i + 0.5), up = p[4] >= p[1], colr = up ? 'var(--os-good)' : 'var(--os-bad)';
        var g = sv('g'); tip(g, when(p[0]), c('o') + ' ' + fmt(p[1], u.unit) + ' · ' + c('hi') + ' ' + fmt(p[2], u.unit) + ' · ' + c('lo') + ' ' + fmt(p[3], u.unit) + ' · ' + c('c') + ' ' + fmt(p[4], u.unit));
        g.appendChild(paint(sv('line', { x1: x.toFixed(1), x2: x.toFixed(1), y1: Y(p[2]).toFixed(1), y2: Y(p[3]).toFixed(1), 'stroke-width': 1 }), 'stroke', colr));
        var y0 = Y(Math.max(p[1], p[4])), y1 = Y(Math.min(p[1], p[4]));
        g.appendChild(paint(sv('rect', { x: (x - bw / 2).toFixed(1), y: y0.toFixed(1), width: bw.toFixed(1), height: Math.max(1, y1 - y0).toFixed(1), rx: 1 }), 'fill', colr));
        if (vh && typeof p[5] === 'number') g.appendChild(paint(paint(sv('rect', { x: (x - bw / 2).toFixed(1), y: (Hd - P.b - p[5] / vmax * vh).toFixed(1), width: bw.toFixed(1), height: (p[5] / vmax * vh).toFixed(1) }), 'fill', colr), 'opacity', '.35'));
        svg.appendChild(g);
      });
      var a = sv('text', { x: P.l, y: Hd - 4 }, 'axl'); a.textContent = when(pts[0][0]); svg.appendChild(a);
      var z = sv('text', { x: Wd - P.r, y: Hd - 4, 'text-anchor': 'end' }, 'axl'); z.textContent = when(pts[n - 1][0]); svg.appendChild(z);
      el.appendChild(svg);
      return null;
    },
    toTable: function (b) {
      var s = (b.data || {}).series || {}, u = (s.values || {}).unit;
      return { columns: [c('date'), c('o'), c('hi'), c('lo'), c('c'), c('vol')], rows: (s.points || []).map(function (p) { return [String(p[0]), fmt(p[1], u), fmt(p[2], u), fmt(p[3], u), fmt(p[4], u), p[5] == null ? '' : fmt(p[5], 'count')]; }) };
    }
  });

  /* ── comparison: 2–4 empresas × 1–10 métricas; tabla (principal) · barras · forma (siempre con Barras al lado) ── */
  G.register('comparison', {
    render: function (el, b, ctx) {
      var d = b.data || {}, ents = (d.entities || []).slice(0, 4), mets = (d.metrics || []).slice(0, 10);
      var views = (d.views || ['table']).filter(function (v) { return v === 'table' || v === 'bars' || (v === 'radar' && mets.length >= 3); });
      if (views.indexOf('radar') >= 0 && views.indexOf('bars') < 0) views.push('bars');
      if (!views.length) views = ['table'];
      var view = views.indexOf(d.default_view) >= 0 ? d.default_view : views[0];
      var head = h('div', 'kg-cmh'), lg = h('div', 'kg-lg');
      ents.forEach(function (e, i) { var sp = h('span'); sp.appendChild(paint(h('i'), 'background', col(i))); sp.appendChild(W.document.createTextNode(e.label)); lg.appendChild(sp); });
      head.appendChild(lg);
      var seg = null;
      ctx._cmpLg = lg;
      if (views.length > 1) { seg = h('div', 'kg-seg'); seg.setAttribute('role', 'group'); head.appendChild(seg); }
      var area = h('div');
      el.appendChild(head); el.appendChild(area);
      var rowMax = mets.map(function (m) { return Math.max.apply(null, [0].concat((m.cells || []).map(function (v) { return typeof v === 'number' ? Math.abs(v) : 0; }))) || 1; });
      var best = mets.map(function (m) {
        if (m.better === 'none') return -1;
        var bi = -1; (m.cells || []).forEach(function (v, i) { if (typeof v !== 'number') return; if (bi < 0 || (m.better === 'lower' ? v < m.cells[bi] : v > m.cells[bi])) bi = i; });
        var ties = (m.cells || []).filter(function (v) { return bi >= 0 && v === m.cells[bi]; }).length;
        return ties > 1 ? -1 : bi;
      });
      var mlab = function (m) { return T(m.values && m.values.label) || m.key; };
      var val = function (m, v) { return typeof v === 'number' ? fmt(v, (m.values || {}).unit, { currency: (m.values || {}).currency }) : '—'; };
      function table() {
        var w = h('div', 'kg-tbw'), tb = h('table', 'kg-tb'), th = h('thead'), tr = h('tr'), body = h('tbody');
        var h0 = h('th', null, ''); h0.setAttribute('scope', 'col'); tr.appendChild(h0);
        ents.forEach(function (e, i) { var x = h('th'); x.setAttribute('scope', 'col'); var s = h('span', 'kg-lg'), sp = h('span'); sp.appendChild(paint(h('i'), 'background', col(i))); sp.appendChild(W.document.createTextNode(e.label)); s.appendChild(sp); x.appendChild(s); tr.appendChild(x); });
        th.appendChild(tr); tb.appendChild(th);
        mets.forEach(function (m, ri) {
          var row = h('tr'), l = h('td', 'm'); l.appendChild(W.document.createTextNode(mlab(m)));
          var q = U.qBtn(m.values && m.values.explain); if (q) { l.appendChild(W.document.createTextNode(' ')); l.appendChild(q); }
          row.appendChild(l);
          ents.forEach(function (e, i) {
            var v = (m.cells || [])[i], td = h('td'), cell = h('div', 'kg-cell');
            cell.appendChild(h('span', 'bv kg-n', val(m, v)));
            var bt = h('span', 'bt');
            if (typeof v === 'number') { var bar = paint(paint(h('i'), 'width', (Math.abs(v) / rowMax[ri] * 100).toFixed(1) + '%'), 'background', col(i)); paint(bar, 'transition-delay', Math.min(ri, 8) * 60 + 'ms'); bt.appendChild(bar); }
            cell.appendChild(bt);
            if (best[ri] === i) cell.appendChild(tip(h('span', 'kg-win-dot'), c('best')));
            tip(cell, mlab(m) + ' · ' + e.label + ': ' + val(m, v), ((m.values || {}).src || '') + ' · ' + when((m.values || {}).as_of));
            td.appendChild(cell); row.appendChild(td);
          });
          body.appendChild(row);
        });
        tb.appendChild(body); w.appendChild(tb);
        return w;
      }
      function bars() {
        var g = h('div', 'kg-gb');
        mets.forEach(function (m, ri) {
          var r = h('div', 'kg-gbr'); r.appendChild(h('div', 'l', mlab(m)));
          var bb = h('div', 'bb');
          ents.forEach(function (e, i) {
            var v = (m.cells || [])[i], row = h('div');
            var bar = paint(paint(h('i'), 'width', (typeof v === 'number' ? Math.abs(v) / rowMax[ri] * 85 : 0).toFixed(1) + '%'), 'background', col(i));
            paint(bar, 'transition-delay', Math.min(ri, 8) * 50 + 'ms');
            row.appendChild(bar); row.appendChild(h('span', 'kg-n', val(m, v)));
            tip(row, mlab(m) + ' · ' + e.label + ': ' + val(m, v), (m.values || {}).src || '');
            bb.appendChild(row);
          });
          r.appendChild(bb); g.appendChild(r);
        });
        return g;
      }
      function radar() {
        var narrow = ctx.compact, Wd = narrow ? 380 : 520, Hd = narrow ? 270 : 300, cx = Wd / 2, cy = Hd / 2, R0 = narrow ? 78 : 108, n = mets.length;
        var pt = function (i, f) { var a = -Math.PI / 2 + i * 2 * Math.PI / n; return [cx + Math.cos(a) * R0 * f, cy + Math.sin(a) * R0 * f]; };
        var svg = sv('svg', { viewBox: '0 0 ' + Wd + ' ' + Hd, role: 'img', 'aria-label': T(b.alt) || T(b.title) }, 'kg-ch kg-rd');
        paint(svg, 'max-width', '520px'); paint(svg, 'margin', '0 auto');
        [0.25, 0.5, 0.75, 1].forEach(function (f) { svg.appendChild(sv('polygon', { points: mets.map(function (m, i) { return pt(i, f).join(','); }).join(' ') }, 'ring')); });
        mets.forEach(function (m, i) {
          var p = pt(i, 1), l = pt(i, 1.22);
          svg.appendChild(sv('line', { x1: cx, y1: cy, x2: p[0], y2: p[1] }, 'spoke'));
          var tx = sv('text', { x: l[0].toFixed(1), y: (l[1] + 4).toFixed(1), 'text-anchor': Math.abs(l[0] - cx) < 8 ? 'middle' : l[0] > cx ? 'start' : 'end' }, 'axl');
          var words = mlab(m).split(' '), l1 = mlab(m), l2 = '';
          if (l1.length > 12 && words.length > 1) { var cut = Math.ceil(words.length / 2); l1 = words.slice(0, cut).join(' '); l2 = words.slice(cut).join(' '); }
          tx.textContent = l1; svg.appendChild(tx);
          if (l2) { var tx2 = sv('text', { x: l[0].toFixed(1), y: (l[1] + 18).toFixed(1), 'text-anchor': tx.getAttribute('text-anchor') }, 'axl'); tx2.textContent = l2; svg.appendChild(tx2); }
        });
        ents.forEach(function (e, ei) {
          var g = sv('g', null, 'poly');
          paint(g, 'transition-delay', ei * 120 + 'ms');
          var ptsS = mets.map(function (m, i) { var v = (m.cells || [])[ei]; return pt(i, typeof v === 'number' ? Math.abs(v) / rowMax[i] : 0); });
          g.appendChild(paint(paint(paint(sv('polygon', { points: ptsS.map(function (p) { return p.join(','); }).join(' '), 'stroke-width': 2, 'stroke-linejoin': 'round' }), 'fill', col(ei)), 'fill-opacity', '.14'), 'stroke', col(ei)));
          ptsS.forEach(function (p, i) {
            var v = (mets[i].cells || [])[ei];
            var dot = paint(paint(sv('circle', { cx: p[0].toFixed(1), cy: p[1].toFixed(1), r: 5, 'stroke-width': 2 }), 'fill', col(ei)), 'stroke', 'var(--os-surface)');
            tip(dot, mlab(mets[i]) + ' · ' + e.label + ': ' + val(mets[i], v), (mets[i].values || {}).src || '');
            g.appendChild(dot);
          });
          svg.appendChild(g);
        });
        return svg;
      }
      var VL = { table: c('table'), bars: c('bars'), radar: c('radar') };
      function show(v, anim) {
        view = v;
        if (seg) {
          seg.textContent = '';
          views.forEach(function (k) { var x = btn(k === view ? 'on' : '', VL[k], function () { show(k, true); }); x.setAttribute('aria-pressed', k === view ? 'true' : 'false'); seg.appendChild(x); });
        }
        area.textContent = ''; area.classList.remove('kg-go');
        lg.style.visibility = v === 'table' ? 'hidden' : '';
        if (v === 'table' && !seg) head.style.display = 'none'; else head.style.display = '';
        area.appendChild(v === 'radar' ? radar() : v === 'bars' ? bars() : table());
        if (anim && !ctx.reduced && W.requestAnimationFrame) W.requestAnimationFrame(function () { W.requestAnimationFrame(function () { area.classList.add('kg-go'); }); });
        else if (anim) area.classList.add('kg-go');
      }
      ctx._setView = function (v) { if (views.indexOf(v) < 0) return false; show(v, true); return true; };
      show(view, false);
      return { go: function () { area.classList.add('kg-go'); } };
    },
    toTable: function (b) {
      var d = b.data || {}, ents = d.entities || [];
      return { columns: [c('metric')].concat(ents.map(function (e) { return e.label; })),
        rows: (d.metrics || []).map(function (m) { return [T(m.values && m.values.label) || m.key].concat((m.cells || []).map(function (v) { return typeof v === 'number' ? fmt(v, (m.values || {}).unit) : '—'; })); }) };
    }
  });

  /* ── graph.mini: proveedores → empresa → clientes (SOLO flujo); grosor = peso; naranja = riesgo; píldoras ── */
  G.register('graph.mini', {
    render: function (el, b, ctx) {
      var d = b.data || {}, ce = d.center || {}, nodes = (d.nodes || []).slice(0, 25), edges = (d.edges || []).slice(0, 40);
      var sup = nodes.filter(function (n) { return n.role === 'supplier'; }), cus = nodes.filter(function (n) { return n.role === 'customer'; });
      var peers = nodes.filter(function (n) { return n.role === 'peer'; });
      var MAXS = ctx.compact ? 4 : 6, extraS = Math.max(0, sup.length - MAXS), extraC = Math.max(0, cus.length - MAXS);
      sup = sup.slice(0, MAXS); cus = cus.slice(0, MAXS);
      var narrow = ctx.compact, Wd = narrow ? 360 : 600, rows = Math.max(sup.length, cus.length, 1), Hd = Math.max(narrow ? 220 : 240, 70 + rows * (narrow ? 46 : 52));
      var CW = narrow ? 7.4 : 8.4, PMAX = narrow ? 120 : 172, MAXCH = Math.floor((PMAX - 24) / CW);
      var short = function (txt) { txt = String(txt || ''); return txt.length > MAXCH ? txt.slice(0, MAXCH - 1).replace(/\s+$/, '') + '…' : txt; };
      var ph = 38, pwOf = function (n) { var l = Math.max(short((n.entity || {}).label).length, String(T(n.sub)).length * 0.85); return Math.max(narrow ? 70 : 84, Math.min(PMAX, l * CW + 24)); };
      var pwL = Math.max.apply(null, [narrow ? 70 : 84].concat(sup.map(pwOf))), pwR = Math.max.apply(null, [narrow ? 70 : 84].concat(cus.map(pwOf)));
      var xL = pwL / 2 + 4, xR = Wd - pwR / 2 - 4, cx = Wd / 2, cy = Hd / 2 + 8;
      var cw = Math.max(narrow ? 76 : 92, Math.min(150, String(ce.label || '').length * 8 + 30));
      var Hs = Hd + (extraS || extraC ? 18 : 0);
      var svg = sv('svg', { viewBox: '0 0 ' + Wd + ' ' + Hs, role: 'img', 'aria-label': T(b.alt) || T(b.title) }, 'kg-ch kg-gm');
      var cap = function (x, txt) { var tx = sv('text', { x: x, y: 16, 'text-anchor': 'middle' }, 'cap'); tx.textContent = txt; svg.appendChild(tx); };
      if (sup.length) cap(xL, c('sup')); if (cus.length) cap(xR, c('cus'));
      var ys = function (n) { var out = []; for (var i = 0; i < n; i++) out.push(n === 1 ? cy : 52 + i * (Hd - 84) / Math.max(1, n - 1)); return out; };
      var eOf = function (s, t0) { for (var i = 0; i < edges.length; i++) if (edges[i].s === s && edges[i].t === t0) return edges[i]; return null; };
      var paths = [], k = 0;
      function side(list, x, dir, pw) {
        ys(list.length).forEach(function (y, i) {
          var n = list[i], e = n.entity || {}, ed = dir < 0 ? eOf(e.id, ce.id) : eOf(ce.id, e.id);
          var x1 = dir < 0 ? x + pw / 2 : cx + cw / 2, x2 = dir < 0 ? cx - cw / 2 : x - pw / 2, y1 = dir < 0 ? y : cy, y2 = dir < 0 ? cy : y;
          var wgt = ed && typeof ed.weight === 'number' ? ed.weight : 3;
          var p = sv('path', { d: 'M' + x1.toFixed(1) + ' ' + y1.toFixed(1) + ' C' + ((x1 + x2) / 2).toFixed(1) + ' ' + y1.toFixed(1) + ' ' + ((x1 + x2) / 2).toFixed(1) + ' ' + y2.toFixed(1) + ' ' + x2.toFixed(1) + ' ' + y2.toFixed(1),
            'stroke-width': (1.2 + wgt * 0.55).toFixed(1), pathLength: '1', 'stroke-dasharray': '1', 'stroke-dashoffset': '1' }, 'ed' + (ed && ed.verified === false ? ' unv' : ''));
          if (ed && typeof ed.conf === 'number') paint(p, 'opacity', String(Math.max(0.25, Math.min(1, ed.conf)) * 0.6 + 0.2));
          svg.insertBefore(p, svg.firstChild); paths.push(p);
          var g = sv('g', null, 'nd pp' + (n.risk ? ' risk' : ''));
          paint(g, 'transition-delay', 240 + (k++) * 70 + 'ms');
          g.appendChild(sv('rect', { x: (x - pw / 2).toFixed(1), y: (y - ph / 2).toFixed(1), width: pw.toFixed(1), height: ph, rx: ph / 2 }));
          var t1 = sv('text', { x: x.toFixed(1), y: (n.sub ? y - 1 : y + 4).toFixed(1), 'text-anchor': 'middle' }); t1.textContent = short(e.label); g.appendChild(t1);
          if (n.sub) { var t2 = sv('text', { x: x.toFixed(1), y: (y + 12).toFixed(1), 'text-anchor': 'middle' }, 'r'); t2.textContent = T(n.sub); g.appendChild(t2); }
          tip(g, (dir < 0 ? (e.label + ' → ' + ce.label) : (ce.label + ' → ' + e.label)) + (ed ? ' · ' + ed.rel_type : ''),
            (ed && typeof ed.weight === 'number' ? c('w') + ' ' + fmt(ed.weight, 'none', { precision: 1 }) : '') + (ed && ed.verified === false ? ' · ' + c('unverified') : '') + ' · ' + c('open'));
          g.addEventListener('pointerenter', function () { p.classList.add('hi'); });
          g.addEventListener('pointerleave', function () { p.classList.remove('hi'); });
          g.addEventListener('focus', function () { p.classList.add('hi'); }); g.addEventListener('blur', function () { p.classList.remove('hi'); });
          entClick(g, e, b, ctx, 'open_map');
          svg.appendChild(g);
        });
      }
      side(sup, xL, -1, pwL); side(cus, xR, 1, pwR);
      var mk = function (x, n) { if (!n) return; var tx = sv('text', { x: x, y: Hs - 4, 'text-anchor': 'middle' }, 'cap'); tx.textContent = c('more').replace('{n}', n); svg.appendChild(tx); };
      mk(xL, extraS); mk(xR, extraC);
      var cg = sv('g', null, 'nd ctr pp');
      cg.appendChild(sv('rect', { x: (cx - cw / 2).toFixed(1), y: (cy - 22).toFixed(1), width: cw.toFixed(1), height: 44, rx: 22 }));
      var ct = sv('text', { x: cx, y: cy + 4, 'text-anchor': 'middle' }); ct.textContent = ce.label || ''; cg.appendChild(ct);
      entClick(cg, ce, b, ctx, 'open_map');
      svg.appendChild(cg);
      el.appendChild(svg);
      if (peers.length) el.appendChild(h('div', 'kg-gmx', c('peers') + peers.map(function (n) { return (n.entity || {}).label; }).join(' · ')));
      return { go: function (inst) { svg.classList.add('kg-go'); paths.forEach(function (p, i) { if (inst) U.draw(p, true); else setTimeout(function () { U.draw(p, false, 650); }, i * 40); }); } };
    },
    toTable: function (b) {
      var d = b.data || {}, lab = {};
      (d.nodes || []).forEach(function (n) { if (n.entity) lab[n.entity.id] = n.entity.label; });
      return { columns: [c('from'), c('to'), c('rel'), c('w')], rows: (d.edges || []).map(function (e) { return [lab[e.s] || e.s, lab[e.t] || e.t, e.rel_type, e.weight == null ? '' : fmt(e.weight, 'none', { precision: 1 })]; }) };
    },
    // el SVG escala con el ancho (360 angosto / 600 ancho, como el renderizador) + ~44 px de cabecera y pie (medido, lote J)
    height: function (b, w) {
      var n = ((b.data || {}).nodes || []).length, nar = w < 520, rows = Math.max(4, Math.ceil(n / 2));
      return Math.round(44 + Math.max(nar ? 220 : 240, 70 + rows * (nar ? 46 : 52)) * w / (nar ? 360 : 600));
    }
  });

  /* ── impact.cascade: el golpe salto a salto (kernel del servidor), total ≥ umbral, rivales menos golpeados y cartera ── */
  G.register('impact.cascade', {
    render: function (el, b, ctx) {
      var d = b.data || {}, hops = (d.hops || []).slice(0, 6), o = d.origin || {}, narrow = ctx.compact;
      if (d.src !== 'hot_kernel') { el.appendChild(h('div', 'kg-unk', T(b.alt))); return null; }
      var box = h('div', 'kg-cas'), n = hops.length, Wd = narrow ? 360 : 600, Hd = 92, y = 40;
      var xs = []; for (var i = 0; i <= n; i++) xs.push((narrow ? 34 : 60) + i * ((Wd - (narrow ? 68 : 120)) / Math.max(1, n)));
      var svg = sv('svg', { viewBox: '0 0 ' + Wd + ' ' + Hd, role: 'img', 'aria-label': T(b.alt) || T(b.title) });
      paint(svg, 'width', '100%'); paint(svg, 'height', 'auto'); paint(svg, 'display', 'block');
      var segs = [], hopG = [];
      for (i = 0; i < n; i++) {
        svg.appendChild(sv('line', { x1: xs[i] + 26, x2: xs[i + 1] - 22, y1: y, y2: y }, 'seg'));
        var sf = sv('line', { x1: xs[i] + 26, x2: xs[i + 1] - 22, y1: y, y2: y, pathLength: '1' }, 'segf'); svg.appendChild(sf); segs.push(sf);
      }
      var og = sv('g', null, 'org');
      og.appendChild(sv('circle', { cx: xs[0], cy: y, r: 24 }, 'ring')); og.appendChild(sv('circle', { cx: xs[0], cy: y, r: 24 }, 'ring r2'));
      og.appendChild(sv('circle', { cx: xs[0], cy: y, r: 26 }, 'c'));
      var ot = sv('text', { x: xs[0], y: y + 4 }); ot.textContent = String(o.symbol || o.label || '').slice(0, 7); og.appendChild(ot);
      tip(og, o.label || '', d.severity != null ? (lang() === 'en' ? 'severity ' : 'severidad ') + fmt(d.severity, 'none', { precision: 0 }) + '/100' : '');
      svg.appendChild(og);
      hops.forEach(function (hp, j) {
        var g = sv('g', null, 'hop');
        g.appendChild(sv('circle', { cx: xs[j + 1], cy: y, r: 20 }));
        var tx = sv('text', { x: xs[j + 1], y: y + 4 }); tx.textContent = String(hp.hop || j + 1); g.appendChild(tx);
        var tl = sv('text', { x: xs[j + 1], y: y + 38 }); paint(tl, 'font-weight', '600'); tl.textContent = (lang() === 'en' ? 'hop ' : 'salto ') + (hp.hop || j + 1); g.appendChild(tl);
        svg.appendChild(g); hopG.push(g);
      });
      box.appendChild(svg);
      var max = Math.max.apply(null, [1].concat(hops.map(function (x) { return x.count || 0; })));
      var rowsEl = h('div', 'kg-hops'), counters = [];
      hops.forEach(function (hp) {
        var r = h('div', 'kg-hp'), l = h('div', 'kg-hpl', c('hop') + (hp.hop));
        // la etiqueta del constructor suele ser «Salto 1» otra vez: solo se agrega si dice algo más
        if (hp.label && String(T(hp.label)).trim() !== String(l.textContent).trim()) l.appendChild(h('small', null, T(hp.label)));
        r.appendChild(l);
        var bb = h('div', 'kg-hpb'), tr = h('div', 'kg-hpt');
        tr.appendChild(paint(h('i', 'kg-hpf'), 'width', ((hp.count || 0) / max * 100).toFixed(1) + '%'));
        bb.appendChild(tr);
        // el conteo sube «…» → número: el ancho del número FINAL queda reservado (si no, la barra se encoge mientras
        // cuenta y la cifra se corre: salto de diseño en angosto)
        var v = h('div', 'kg-hpv kg-n'), num = h('span', null, '…');
        paint(paint(paint(num, 'display', 'inline-block'), 'text-align', 'right'), 'min-width', String(fmt(hp.count || 0, 'count')).length + 'ch');
        v.appendChild(num); v.appendChild(W.document.createTextNode(c('companies'))); bb.appendChild(v);
        counters.push([num, hp.count || 0]);
        r.appendChild(bb);
        var chips = h('div', 'kg-hpc');
        (hp.entities || []).slice(0, 8).forEach(function (x, ci) {
          var s = h('span', null, (x.entity || {}).label || ''); paint(s, 'transition-delay', 180 + ci * 60 + 'ms');
          tip(s, (x.entity || {}).label, fmt(x.impact_pct, 'pct') + c('damage'));
          entClick(s, x.entity, b, ctx); chips.appendChild(s);
        });
        if (chips.firstChild) r.appendChild(chips);
        r.setAttribute('aria-label', c('hopRow').replace('{n}', hp.hop).replace('{c}', fmt(hp.count || 0, 'count')));
        tip(r, c('hopRow').replace('{n}', hp.hop).replace('{c}', fmt(hp.count || 0, 'count')), hp.max_pct != null ? c('maxp') + ': ' + fmt(hp.max_pct, 'pct') : '');
        rowsEl.appendChild(r);
      });
      box.appendChild(rowsEl);
      var tot = h('div', 'kg-cast'), tb = h('b', 'kg-n', '…');
      paint(paint(paint(tb, 'display', 'inline-block'), 'text-align', 'right'), 'min-width', String(fmt(d.total || 0, 'count')).length + 'ch');
      tot.appendChild(tb); tot.appendChild(h('span', null, c('total').replace('{t}', fmt(d.threshold_pct != null ? d.threshold_pct : 1, 'none', { precision: d.threshold_pct % 1 ? 1 : 0 }))));
      var q = U.qBtn('genui_hops'); if (q) tot.appendChild(q);
      box.appendChild(tot);
      if ((d.least_hit_rivals || []).length) {
        box.appendChild(h('div', 'kg-casx', c('least') + d.least_hit_rivals.slice(0, 6).map(function (r) { return (r.entity || {}).label + ' ' + fmt(r.damage_pct, 'pct'); }).join(' · ')));
      }
      var meta = [];
      if (d.kernel) meta.push(c('kernel') + d.kernel);
      if (d.generation != null) meta.push(c('gen') + d.generation);
      if (d.as_of) meta.push(when(d.as_of));
      if (meta.length) box.appendChild(h('div', 'kg-casx', meta.join(' · ')));
      var pf = d.portfolio;
      if (pf && pf.state) {
        var pr = h('div', 'kg-pf'); pr.appendChild(h('div', 'kg-pfi', '💼'));
        var pn = h('div'), pnh = h('div', 'kg-pfn', pf.state === 'figure' ? c('pfHit') : c('pf'));
        var q2 = U.qBtn('genui_pf'); if (q2) pnh.appendChild(q2);
        pn.appendChild(pnh);
        pn.appendChild(h('div', 'kg-pfs', pf.state === 'no_positions' ? (T(pf.reason) || c('nopos')) : (T(pf.reason) || '')));
        pr.appendChild(pn);
        if (pf.state === 'figure' && pf.value && typeof pf.value.v === 'number') {
          // P&L: aparece con fundido, NUNCA cuenta desde 0
          var whole = Math.abs(pf.value.v) >= 100 ? { precision: 0 } : {};   // dinero grande: sin centavos (valor y banda iguales)
          var vm = U.vmFigure(Object.assign({}, pf.value, whole)), bv = pf.band ? U.vmFigure(Object.assign({}, pf.band, whole)) : null;
          var pv = h('div', 'kg-pfv kg-n' + (pf.value.v < 0 ? ' bad' : ''), vm.text);
          if (bv && !bv.na) pv.appendChild(h('small', null, c('band') + bv.text));
          tip(pv, vm.text + (bv && !bv.na ? ' ' + c('band') + bv.text : ''), (vm.src || '') + (vm.as_of ? ' · ' + when(vm.as_of) : ''));
          pr.appendChild(pv);
        }
        box.appendChild(pr);
      }
      el.appendChild(box);
      var total = d.total || 0;
      function lightAll() {
        box.classList.add('go');
        segs.forEach(function (s) { s.classList.add('on'); }); hopG.forEach(function (g) { g.classList.add('on'); });
        Array.prototype.forEach.call(rowsEl.children, function (r) { r.classList.add('on'); });
        counters.forEach(function (x) { U.countUp(x[0], x[1], 'count', null, true); });
        U.countUp(tb, total, 'count', null, true);
      }
      return { go: function (inst) {
        if (inst || ctx.reduced) { lightAll(); return; }
        box.classList.add('go');
        var tms = 0;
        hops.forEach(function (hp, j) {
          tms += j ? 520 : 380;
          setTimeout(function () { if (segs[j]) segs[j].classList.add('on'); }, tms);
          setTimeout(function () {
            if (hopG[j]) hopG[j].classList.add('on');
            if (rowsEl.children[j]) rowsEl.children[j].classList.add('on');
            U.countUp(counters[j][0], counters[j][1], 'count', null, false);
          }, tms + 260);
        });
        setTimeout(function () { U.countUp(tb, total, 'count', null, false); }, tms + 360);
      } };
    },
    toTable: function (b) {
      var d = b.data || {};
      var rows = (d.hops || []).map(function (hp) { return [String(hp.hop), fmt(hp.count || 0, 'count'), hp.max_pct == null ? '' : fmt(hp.max_pct, 'pct'), (hp.entities || []).map(function (x) { return (x.entity || {}).label + ' ' + fmt(x.impact_pct, 'pct'); }).join(', ')]; });
      rows.push(['Σ', fmt(d.total || 0, 'count'), '', '']);
      return { columns: [c('hopCol'), c('cos'), c('maxp'), c('ex')], rows: rows };
    },
    // alto real medido en Chromium (lote J, error ≤ 6 % de 316 a 700 px): cabecera + SVG que escala con el ancho, una fila
    // por salto (+ líneas de chips, ~85 px cada uno), la línea de rivales (se parte en angosto) y la cartera
    height: function (b, w) {
      var d = b.data || {}, nar = w < 520, cpl = Math.max(1, Math.floor((w - 40) / 85)), hg = 172 + 92 * w / (nar ? 360 : 600);
      (d.hops || []).slice(0, 6).forEach(function (hp) { var n = Math.min(8, (hp.entities || []).length); hg += (nar ? 55 : 35) + (n ? 21 * Math.ceil(n / cpl) : 0); });
      var r = Math.min(6, (d.least_hit_rivals || []).length);
      if (r) hg += 6 + 18 * Math.ceil((22 + r * 13) * 6.6 / Math.max(120, w - 40));
      if (d.portfolio) hg += w < 360 ? 72 : 61;
      return Math.round(hg);
    }
  });
})(typeof window !== 'undefined' ? window : globalThis);
