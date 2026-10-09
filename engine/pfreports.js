/* ============================================================================
   engine/pfreports.js — 📄 REPORTES · 📰 NOTICIAS · 💬 PREGÚNTALE A TU CARTERA
   (secciones de Comité → 💼 Mi cartera; las monta engine/pfcommittee.js)

   Pedido (2026-10-02): "reportes mensuales, diarios o a pedido, en base a tus
   carteras en relación con tu posición inicial, con gráficos… como un NotebookLM
   pero que el contexto sea tu cartera… noticias en vivo relevantes a tu cartera,
   no las mismas emergencias viejas".
   Server: core/portfolio_reports_api.py. Dueño = llave aleatoria del navegador
   (localStorage 'kh_owner_key', cabecera X-Khipu-Owner).
   window.KhipuPortfolioExtras.render(el, section, ctx)
     section: 'reports' | 'news' | 'ask'
     ctx: { source: {key, label, positions, cash, start, startDate}, profile, analysis }

   Piel Khipus OS (2026-10-09): SOLO tokens --os-* con el valor OSCURO de respaldo
   (var(--x, respaldo)); ámbar = var(--cm-warn). El gráfico SVG lee los tokens al
   pintar (getComputedStyle del contenedor) y los usa como respaldo de var() en
   style="stroke:…" (los atributos de presentación SVG no aceptan var()). Clases
   'pfe-*' (CSS inyectado al pintar, id 'pfe-css'); los ids pfr-… y pfa-… no cambian.
   ============================================================================ */
(function () {
  'use strict';
  function isEn() { var l = window.LANG; if (!l) { try { l = localStorage.getItem('eco_lang'); } catch (e) { l = null; } } return l === 'en'; }
  function L(es, en) { return isEn() ? en : es; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function usd(v) { v = Number(v); if (!isFinite(v)) return '—'; return (v < 0 ? '−$' : '$') + Math.abs(v).toLocaleString('en-US', { maximumFractionDigits: 0 }); }
  function sgn(v, d) { v = Number(v); if (!isFinite(v)) return '—'; return (v >= 0 ? '+' : '') + v.toFixed(d == null ? 1 : d); }

  // ── colores = tokens de Khipus OS (nunca hex sueltos: un test lo verifica) ──
  var INK3 = 'var(--os-ink-3,#6E7080)', ACC = 'var(--os-accent,#4C8DF6)',
    GOOD = 'var(--cm-good,#2fbf5b)', BAD = 'var(--cm-bad,#F47C7C)', WARN = 'var(--cm-warn,#B7791F)', AI = 'var(--cm-ai,#B48CFF)';
  function col(v) { return Number(v) >= 0 ? GOOD : BAD; }
  // respaldo OSCURO de cada token del gráfico (si se abre fuera del comité / la Cabina)
  var DARK = { '--os-ink-3': '#6E7080', '--os-line': 'rgba(255,255,255,.07)', '--os-mute': '#3A3C4A', '--os-accent': '#4C8DF6', '--os-surface': '#17181F' };
  function tok(n) {   // valor del token AHORA (tema claro u oscuro), leído del contenedor donde se pinta
    var v = '';
    try {
      var h = CUR.el || document.getElementById('cm-ov') || document.body;
      if (h && window.getComputedStyle) v = String(window.getComputedStyle(h).getPropertyValue(n) || '').trim();
    } catch (e) {}
    return v || DARK[n] || '';
  }
  function sv(prop, n) { return prop + ':var(' + n + ',' + tok(n) + ')'; }

  function scoped(rules) {   // doble alcance: dentro del comité (#cm) y suelto (p. ej. la ventana de impresión)
    return rules.map(function (r) {
      return r[0].split(',').map(function (s) { s = s.trim(); return '#cm .pfe ' + s + ',.pfe ' + s; }).join(',') + '{' + r[1] + '}';
    }).join('');
  }
  var CSS = '.pfe{font-family:var(--os-font,\'Nunito\',\'Geist\',system-ui,-apple-system,\'Segoe UI\',sans-serif);color:var(--os-ink,#F2F2F5);font-variant-numeric:tabular-nums;-webkit-font-smoothing:antialiased}' +
    scoped([
      ['.pfe-hd', 'display:flex;gap:6px;align-items:center;flex-wrap:wrap'],
      ['.pfe-title', 'font-size:16px;font-weight:800;color:var(--os-ink,#F2F2F5);letter-spacing:-.01em;min-width:0;overflow-wrap:anywhere'],
      ['.pfe-btns', 'margin-left:auto;display:flex;gap:6px;flex-wrap:wrap'],
      ['.cm-btn.pfe-sm', 'height:auto;min-height:30px;padding:5px 13px;font-size:12px;line-height:1.2'],
      ['.pfe-seg', 'display:inline-flex;flex-wrap:wrap;gap:2px;padding:3px;border-radius:20px;background:var(--os-surface-2,#1F2029);max-width:100%'],
      ['.pfe-seg button', 'appearance:none;-webkit-appearance:none;border:0;background:none;cursor:pointer;min-height:30px;padding:5px 14px;border-radius:999px;' +
        'font:inherit;font-size:12.5px;font-weight:600;line-height:1.25;color:var(--os-ink-2,#A6A8B5);transition:background-color .15s ease,color .15s ease,box-shadow .15s ease'],
      ['.pfe-seg button:hover', 'color:var(--os-ink,#F2F2F5)'],
      ['.pfe-seg button.on', 'background:var(--os-surface,#17181F);color:var(--os-ink,#F2F2F5);box-shadow:var(--os-shadow,0 1px 2px rgba(0,0,0,.4), 0 10px 30px rgba(0,0,0,.35))'],
      ['.pfe-seg button:focus-visible,.pfe-row:focus-visible,.pfe-sug:focus-visible', 'outline:2px solid var(--os-accent,#4C8DF6);outline-offset:2px'],
      ['.pfe-tag', 'display:inline-flex;align-items:center;gap:4px;padding:2px 9px;border-radius:999px;font-size:11px;font-weight:700;white-space:nowrap;' +
        'color:var(--c,var(--os-ink-2,#A6A8B5));background:var(--os-surface-2,#1F2029)'],
      ['.pfe-tag.c', 'background:color-mix(in srgb,var(--c,var(--os-ink-2,#A6A8B5)) 13%,transparent)'],
      ['.pfe-kpis', 'display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px;margin-top:14px'],
      ['.pfe-kpi', 'background:var(--os-surface-2,#1F2029);border-radius:var(--os-r-sm,12px);padding:10px 12px;min-width:0'],
      ['.pfe-kpi .k', 'font-size:11.5px;color:var(--os-ink-2,#A6A8B5);line-height:1.3'],
      ['.pfe-kpi .v', 'font-size:18px;font-weight:800;color:var(--c,var(--os-ink,#F2F2F5));margin-top:4px;letter-spacing:-.01em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis'],
      ['.pfe-kpi .s', 'font-size:11.5px;color:var(--os-ink-3,#6E7080);margin-top:2px;line-height:1.3'],
      ['.pfe-say', 'margin-top:14px;font-size:13.5px;line-height:1.65;color:var(--os-ink,#F2F2F5);overflow-wrap:anywhere'],
      ['.pfe-chart', 'margin-top:4px'],
      ['.pfe-chart svg', 'display:block;width:100%;height:auto;overflow:visible'],
      ['.pfe-lg', 'display:flex;gap:16px;flex-wrap:wrap;align-items:center;font-size:12px;color:var(--os-ink-2,#A6A8B5);margin-top:8px'],
      ['.pfe-lg i', 'display:inline-block;width:18px;height:0;border-top:3px solid var(--c,var(--os-accent,#4C8DF6));border-radius:2px;vertical-align:middle;margin-right:6px'],
      ['.pfe-lg i.d', 'border-top:2px dashed var(--os-ink-3,#6E7080)'],
      ['.pfe-lg .m', 'color:var(--os-ink-3,#6E7080)'],
      ['.pfe-div', 'display:grid;grid-template-columns:minmax(0,120px) minmax(0,1fr) 78px;gap:10px;align-items:center;font-size:12.5px;margin:7px 0'],
      ['.pfe-div .n', 'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--os-ink,#F2F2F5)'],
      ['.pfe-div .tr', 'position:relative;height:8px;border-radius:999px;background:var(--os-surface-2,#1F2029)'],
      ['.pfe-div .tr b', 'position:absolute;left:50%;top:-3px;bottom:-3px;width:1px;background:var(--os-ink-3,#6E7080)'],
      ['.pfe-div .tr i', 'position:absolute;top:0;bottom:0;border-radius:999px;background:var(--c,var(--os-accent,#4C8DF6))'],
      ['.pfe-div .v', 'text-align:right;font-weight:700;color:var(--c,var(--os-ink,#F2F2F5))'],
      ['.pfe-news', 'padding:10px 0;border-bottom:1px solid var(--os-line,rgba(255,255,255,.07))'],
      ['.pfe-news:last-child', 'border-bottom:0'],
      ['.pfe-meta', 'display:flex;gap:6px;flex-wrap:wrap;align-items:center;font-size:11.5px;color:var(--os-ink-3,#6E7080);margin-bottom:4px'],
      ['.pfe-meta .f', 'font-weight:800;color:var(--c,var(--os-ink-3,#6E7080))'],
      ['a.pfe-a', 'font-size:13.5px;font-weight:700;color:var(--os-ink,#F2F2F5);text-decoration:none;line-height:1.4'],
      ['a.pfe-a:hover', 'color:var(--os-accent,#4C8DF6)'],
      ['.pfe-row', 'display:flex;gap:10px;align-items:center;padding:9px 10px;border-radius:12px;margin-top:2px;cursor:pointer;font-size:13px;color:var(--os-ink,#F2F2F5);transition:background-color .15s ease'],
      ['.pfe-row:hover', 'background:var(--os-surface-2,#1F2029)'],
      ['.pfe-row .t', 'flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap'],
      ['.pfe-row .p', 'font-weight:700'],
      ['.pfe-dot', 'width:8px;height:8px;border-radius:50%;flex:none;background:var(--os-accent,#4C8DF6)'],
      ['.pfe-log', 'max-height:420px;overflow-y:auto;padding:2px 2px 4px'],
      ['.pfe-msg', 'display:flex;gap:8px;align-items:flex-end;margin:10px 0'],
      ['.pfe-msg.me', 'justify-content:flex-end'],
      ['.pfe-bub', 'max-width:86%;padding:10px 14px;border-radius:18px;font-size:13.5px;line-height:1.55;overflow-wrap:anywhere;' +
        'background:var(--os-surface-2,#1F2029);color:var(--os-ink,#F2F2F5);border-bottom-left-radius:6px'],
      ['.pfe-msg.me .pfe-bub', 'background:var(--kos-accent-soft,rgba(76,141,246,.16));border-bottom-left-radius:18px;border-bottom-right-radius:6px'],
      ['.pfe-think', 'display:flex;gap:10px;align-items:center;font-size:13px;color:var(--os-ink-2,#A6A8B5);margin:10px 0'],
      ['.pfe-sugs', 'display:flex;gap:6px;flex-wrap:wrap;margin:10px 0 4px'],
      ['.pfe-sug', 'appearance:none;-webkit-appearance:none;border:0;cursor:pointer;padding:7px 13px;border-radius:999px;font:inherit;font-size:12.5px;font-weight:600;' +
        'background:var(--os-surface-2,#1F2029);color:var(--os-ink-2,#A6A8B5);text-align:left;transition:background-color .15s ease,color .15s ease'],
      ['.pfe-sug:hover', 'background:var(--os-surface-3,#2A2B36);color:var(--os-ink,#F2F2F5)'],
    ]) +
    '@media (max-width:560px){.pfe .pfe-div{grid-template-columns:minmax(0,88px) minmax(0,1fr) 64px;gap:8px}.pfe .pfe-btns{margin-left:0}.pfe .pfe-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}}' +
    '@media (prefers-reduced-motion:reduce){.pfe .pfe-seg button,.pfe .pfe-row,.pfe .pfe-sug{transition:none}}';
  function ensureCss() {
    if (typeof document === 'undefined' || typeof document.createElement !== 'function' || document.getElementById('pfe-css')) return;
    var st = document.createElement('style'); st.id = 'pfe-css'; st.textContent = CSS;
    (document.head || document.documentElement).appendChild(st);
  }
  function masc(id, size, state) {   // mascota (engine/mascot.js): Khipu te responde; Comité decide
    try { return window.KhipuMascot ? window.KhipuMascot.svg(id, size || 20, state ? { state: state } : null) : ''; } catch (e) { return ''; }
  }
  function tag(text, color) { return '<span class="pfe-tag' + (color ? ' c' : '') + '"' + (color ? ' style="--c:' + color + ';color:' + color + '"' : '') + '>' + text + '</span>'; }
  function kpi(label, value, sub, color) {
    return '<div class="pfe-kpi"><div class="k">' + esc(label) + '</div><div class="v"' + (color ? ' style="--c:' + color + '"' : '') + '>' + value + '</div>' +
      (sub ? '<div class="s">' + esc(sub) + '</div>' : '') + '</div>';
  }
  function day(iso) { var d = new Date(iso); return isNaN(d) ? (iso || '') : d.toLocaleDateString(isEn() ? 'en' : 'es', { day: '2-digit', month: 'short', year: 'numeric' }); }
  function actor() { var a = null; try { a = localStorage.getItem('khipu_actor'); } catch (e) {} return (a && a.trim()) || 'usuario'; }
  function owner() {
    var k = null;
    try { k = localStorage.getItem('kh_owner_key'); } catch (e) {}
    if (!k || k.length < 16) {
      var a = new Uint8Array(16); (window.crypto || {}).getRandomValues ? window.crypto.getRandomValues(a) : a.forEach(function (_, i) { a[i] = Math.random() * 256; });
      k = Array.prototype.map.call(a, function (b) { return ('0' + b.toString(16)).slice(-2); }).join('');
      try { localStorage.setItem('kh_owner_key', k); } catch (e) {}
    }
    return k;
  }
  function api(url, opts) {
    opts = opts || {};
    opts.headers = Object.assign({ 'Content-Type': 'application/json', 'X-Khipu-Owner': owner(), 'X-Khipu-Actor': actor() }, opts.headers || {});
    return fetch((window.BASE || '') + url, opts).then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { j._status = r.status; return j; }); });
  }
  function errOf(d) { return (isEn() ? (d.error_en || d.error) : d.error) || L('Algo falló.', 'Something failed.'); }
  function card(inner) { return '<div class="cm-cell">' + inner + '</div>'; }
  function md(t) {   // markdown mínimo y seguro (negrita, listas, saltos)
    return esc(t).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/^- (.*)$/gm, '• $1').replace(/\n/g, '<br>');
  }

  var S = { reports: null, viewing: null, period: 'month', busy: false, err: null, news: null, newsDays: 7,
    chat: [], asking: false, watches: null };
  var INV_SCHED = { autopilot: 'monthly', informed: 'weekly', active: 'daily' };
  var CUR = { el: null, section: null, ctx: null };

  // ── gráficos SVG (sin librerías; colores = tokens leídos al pintar) ─────────
  var _gid = 0;
  function lineChart(curve) {
    if (!curve || curve.length < 2) return '';
    var W = 640, H = 210, P = 36, R = 12, B = 24;
    var vals = [];
    curve.forEach(function (c) { if (c.idx != null) vals.push(c.idx); if (c.spy_idx != null) vals.push(c.spy_idx); });
    if (!vals.length) return '';
    var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals); if (hi - lo < 1) { hi += 0.5; lo -= 0.5; }
    var x = function (i) { return P + i * (W - P - R) / (curve.length - 1); };
    var y = function (v) { return 10 + (hi - v) * (H - 10 - B) / (hi - lo); };
    var path = function (k) { var d = ''; curve.forEach(function (c, i) { if (c[k] == null) return; d += (d ? 'L' : 'M') + x(i).toFixed(1) + ',' + y(c[k]).toFixed(1); }); return d; };
    var last = curve[curve.length - 1];
    var first = -1, lastI = -1; curve.forEach(function (c, i) { if (c.idx != null) { if (first < 0) first = i; lastI = i; } });
    var pf = path('idx'), gid = 'pfeg' + (++_gid);
    var area = pf && lastI > first ? pf + 'L' + x(lastI).toFixed(1) + ',' + (H - B) + 'L' + x(first).toFixed(1) + ',' + (H - B) + 'Z' : '';
    var ink3 = sv('fill', '--os-ink-3');
    return '<div class="pfe-chart"><svg viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="' + esc(L('Valor de tu cartera vs S&P 500', 'Your portfolio vs S&P 500')) + '">' +
      '<defs><linearGradient id="' + gid + '" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="' + sv('stop-color', '--os-accent') + ';stop-opacity:.20"/>' +
        '<stop offset="1" style="' + sv('stop-color', '--os-accent') + ';stop-opacity:0"/></linearGradient></defs>' +
      [lo, (lo + hi) / 2, hi].map(function (v) {
        return '<line x1="' + P + '" x2="' + (W - R) + '" y1="' + y(v).toFixed(1) + '" y2="' + y(v).toFixed(1) + '" style="' + sv('stroke', '--os-line') + ';stroke-width:1"/>' +
          '<text x="2" y="' + (y(v) + 4).toFixed(1) + '" font-size="10" style="' + ink3 + '">' + v.toFixed(0) + '</text>'; }).join('') +
      '<line x1="' + P + '" x2="' + (W - R) + '" y1="' + y(100).toFixed(1) + '" y2="' + y(100).toFixed(1) + '" style="' + sv('stroke', '--os-mute') + ';stroke-width:1.2;stroke-dasharray:4 4"/>' +
      (area ? '<path d="' + area + '" style="fill:url(#' + gid + ');stroke:none"/>' : '') +
      '<path d="' + path('spy_idx') + '" style="fill:none;' + sv('stroke', '--os-ink-3') + ';stroke-width:1.6;stroke-dasharray:5 4;stroke-linecap:round"/>' +
      '<path d="' + pf + '" style="fill:none;' + sv('stroke', '--os-accent') + ';stroke-width:2.4;stroke-linejoin:round;stroke-linecap:round"/>' +
      (lastI >= 0 ? '<circle cx="' + x(lastI).toFixed(1) + '" cy="' + y(curve[lastI].idx).toFixed(1) + '" r="4.5" style="' + sv('fill', '--os-accent') + ';' + sv('stroke', '--os-surface') + ';stroke-width:2"/>' : '') +
      '<text x="' + P + '" y="' + (H - 6) + '" font-size="10" style="' + ink3 + '">' + esc(day(curve[0].d)) + '</text>' +
      '<text x="' + (W - R) + '" y="' + (H - 6) + '" font-size="10" text-anchor="end" style="' + ink3 + '">' + esc(day(last.d)) + '</text>' +
      '</svg><div class="pfe-lg"><span><i style="--c:' + ACC + '"></i>' + esc(L('tu cartera', 'your portfolio')) + ' (' + sgn(last.idx - 100) + '%)</span>' +
      (last.spy_idx != null ? '<span><i class="d"></i>S&amp;P 500 (' + sgn(last.spy_idx - 100) + '%)</span>' : '') + '<span class="m">' + esc(L('base 100 = inicio del periodo', 'base 100 = start of period')) + '</span></div></div>';
  }
  function bars(rows, key, fmt) {
    if (!rows || !rows.length) return '';
    var mx = Math.max.apply(null, rows.map(function (r) { return Math.abs(r[key]) || 0; }).concat([1e-9]));
    return rows.map(function (r) {
      var v = r[key], w = Math.abs(v) / mx * 50;
      return '<div class="pfe-div" style="--c:' + col(v) + '"><span class="n" title="' + esc(r.label) + '">' + esc(r.label) + '</span>' +
        '<span class="tr"><b></b><i style="' + (v >= 0 ? 'left:50%' : 'right:50%') + ';width:' + w + '%"></i></span>' +
        '<span class="v">' + fmt(v) + '</span></div>';
    }).join('');
  }
  function newsList(items) {
    if (!items || !items.length) return '<div class="cm-note">' + esc(L('Sin noticias recientes sobre tus posiciones en esta ventana.', 'No recent news about your holdings in this window.')) + '</div>';
    return items.map(function (n) {
      var c = n.freshness === 'new' ? GOOD : n.freshness === 'recent' ? ACC : INK3;
      var href = window.safeUrl ? window.safeUrl(n.url) : n.url;
      return '<div class="pfe-news"><div class="pfe-meta">' +
          '<span class="f" style="--c:' + c + '">' + esc(n.label || '') + '</span><span>' + esc(day(n.published_at)) + (n.outlet ? ' · ' + esc(n.outlet) : '') + '</span>' +
          (n.holdings || []).map(function (h) { return tag(esc(h)); }).join('') + '</div>' +
        '<a class="pfe-a" href="' + esc(href) + '" target="_blank" rel="noopener">' + esc(n.title) + '</a>' +
        (n.summary ? '<div class="cm-note" style="margin-top:4px">' + esc(n.summary) + '</div>' : '') + '</div>';
    }).join('');
  }

  // ── 📄 reportes ──────────────────────────────────────────────────────────
  function reportView(r) {
    var p = r.performance || {}, s = r.summary || {}, adv = r.advisor || {};
    return '<div id="pfr-print">' + card('<div class="pfe-hd"><span class="pfe-title">📄 ' + esc(r.title || L('Reporte de tu cartera', 'Your portfolio report')) + '</span>' +
        '<span class="pfe-btns"><button class="cm-btn ghost pfe-sm" id="pfr-print-btn">🖨 ' + esc(L('Imprimir / PDF', 'Print / PDF')) + '</button>' +
        '<button class="cm-btn ghost pfe-sm" id="pfr-back">← ' + esc(L('Volver', 'Back')) + '</button></span></div>' +
        '<div class="pfe-kpis">' +
          kpi(L('Valor hoy', 'Value today'), usd(p.value_now_usd)) +
          kpi(L('En el periodo', 'Over the period'), sgn(p.period_change_pct) + '%', (Number(p.period_change_usd) > 0 ? '+' : '') + usd(p.period_change_usd), col(p.period_change_pct)) +
          (p.spy_period_pct != null ? kpi('S&P 500', sgn(p.spy_period_pct) + '%', p.vs_spy_pts != null ? L('tú ', 'you ') + sgn(p.vs_spy_pts) + L(' pts', ' pts') : '') : '') +
          (p.initial_usd ? kpi(L('Desde tu posición inicial', 'Since your starting position'), sgn(p.since_start_pct) + '%', L('empezaste con ', 'you started with ') + usd(p.initial_usd), col(p.since_start_pct)) : '') +
          (p.period_max_drawdown_pct != null ? kpi(L('Peor caída del periodo', 'Worst drop in the period'), Number(p.period_max_drawdown_pct).toFixed(1) + '%') : '') +
        '</div>' +
        (s.text ? '<div class="pfe-say">' + md(s.text) + (s.ai ? ' ' + tag('🧠 ' + esc(L('IA', 'AI')), AI) : '') + '</div>' : '')) +
      card('<div class="cm-t">📈 ' + esc(L('Tu cartera vs el mercado', 'Your portfolio vs the market')) + '</div>' + lineChart(r.curve) + '<div class="cm-note" style="font-size:11px;margin-top:6px">' + esc(r.assumption || '') + '</div>') +
      '<div class="cm-grid"><div style="min-width:0">' +
        card('<div class="cm-t">🧮 ' + esc(L('Quién sumó y quién restó', 'Who added and who subtracted')) + '</div>' + bars(r.contributions || [], 'contrib_usd', usd)) +
        card('<div class="cm-t">↕ ' + esc(L('Cambio de cada posición en el periodo', 'Change of each position in the period')) + '</div>' + bars(r.contributions || [], 'change_pct', function (v) { return sgn(v) + '%'; })) +
      '</div><div style="min-width:0">' +
        (adv.actions && adv.actions.length ? card('<div class="cm-t pfe-hd">' + masc('comite', 18) + esc(L('Qué revisar · el Comité', 'What to review · the Committee')) + '</div>' + adv.actions.slice(0, 5).map(function (a) {
          return '<div class="cm-note" style="margin:6px 0"><b>' + esc(a.id) + '</b> · ' + esc(isEn() ? a.why_en : a.why_es) + '</div>'; }).join('') +
          (adv.disclaimer ? '<div class="cm-note" style="font-size:11px;margin-top:8px;color:' + WARN + '">🤖 ' + esc(adv.disclaimer) + '</div>' : '')) : '') +
        card('<div class="cm-t pfe-hd">' + masc('radar', 18) + esc(L('Noticias del periodo', 'News of the period')) + '</div>' + newsList(r.news || [])) +
      '</div></div>' +
      '<div class="cm-note" style="font-size:11px">' + esc(L('Fuente: ', 'Source: ') + (r.source || '') + ' · ' + L('generado ', 'generated ') + day(r.generated_at || r.created_at)) + '</div></div>';
  }

  function reportsHtml(ctx) {
    if (S.viewing) return reportView(S.viewing);
    var prof = ctx.profile || {}, sched = currentSchedule(ctx);
    var PER = [['day', 'Hoy', 'Today'], ['week', 'Semana', 'Week'], ['month', 'Mes', 'Month'], ['quarter', 'Trimestre', 'Quarter'], ['since_start', 'Desde el inicio', 'Since start']];
    var SCH = [['off', 'Apagado', 'Off'], ['daily', 'Diario', 'Daily'], ['weekly', 'Semanal', 'Weekly'], ['monthly', 'Mensual', 'Monthly']];
    return card('<div class="cm-t">📄 ' + esc(L('Reporte de tu cartera', 'Your portfolio report')) + '</div>' +
        '<div class="cm-note" style="margin-bottom:12px">' + esc(L('Cómo te fue frente a tu posición inicial y al S&P 500, quién sumó y quién restó, noticias con fecha y qué revisar. Con gráficos.', 'How you did vs your starting position and the S&P 500, who added and who subtracted, dated news and what to review. With charts.')) + '</div>' +
        '<div class="cm-form" style="margin-bottom:8px"><select id="pfr-period" aria-label="' + esc(L('Periodo', 'Period')) + '">' + PER.map(function (o) { return '<option value="' + o[0] + '"' + (S.period === o[0] ? ' selected' : '') + '>' + esc(L(o[1], o[2])) + '</option>'; }).join('') + '</select>' +
          '<button class="cm-btn" id="pfr-gen"' + (S.busy ? ' disabled' : '') + '>' + esc(S.busy ? L('Generando… (10-40 s)', 'Generating… (10-40 s)') : L('📄 Generar reporte ahora', '📄 Generate report now')) + '</button></div>' +
        '<div class="cm-form" style="margin:0"><span class="cm-note">🗓 ' + esc(L('Reportes automáticos de esta cartera:', 'Automatic reports for this portfolio:')) + '</span>' +
          '<select id="pfr-sched" aria-label="' + esc(L('Reportes automáticos', 'Automatic reports')) + '">' + SCH.map(function (o) { return '<option value="' + o[0] + '"' + (sched === o[0] ? ' selected' : '') + '>' + esc(L(o[1], o[2])) + '</option>'; }).join('') + '</select>' +
          (prof.involvement && !hasWatch(ctx) ? '<span class="cm-note" style="font-size:11.5px">' + esc(L('sugerido para tu nivel de involucramiento: ', 'suggested for your involvement level: ')) +
            esc(L({ daily: 'diario', weekly: 'semanal', monthly: 'mensual' }[suggestedSchedule(ctx)], suggestedSchedule(ctx))) + '</span>' : '') + '</div>' +
        (S.err ? '<div class="cm-note" style="color:' + WARN + ';margin-top:8px">' + esc(S.err) + '</div>' : '')) +
      card('<div class="cm-t">🗂 ' + esc(L('Tus reportes', 'Your reports')) + '</div>' +
        (S.reports == null ? '<div class="cm-note"><span class="cm-spin">◌</span></div>' : S.reports.length ? S.reports.map(function (r) {
          return '<div class="pfe-row" data-rid="' + esc(r.id) + '" role="button" tabindex="0">' +
            (r.read ? '' : '<span class="pfe-dot" title="' + esc(L('nuevo', 'new')) + '"></span>') +
            '<span class="t">' + esc(r.title) + '</span>' +
            (r.change_pct != null ? '<span class="p" style="color:' + col(r.change_pct) + '">' + sgn(r.change_pct) + '%</span>' : '') + '</div>';
        }).join('') : '<div class="cm-note">' + esc(L('Todavía no hay reportes. Genera el primero arriba.', 'No reports yet. Generate the first one above.')) + '</div>'));
  }
  function hasWatch(ctx) { return (S.watches || []).some(function (w) { return w.source_key === ctx.source.key; }); }
  function currentSchedule(ctx) {
    var w = (S.watches || []).filter(function (x) { return x.source_key === ctx.source.key; })[0];
    if (w) return w.schedule;
    return 'off';
  }
  function suggestedSchedule(ctx) { return INV_SCHED[(ctx.profile || {}).involvement] || 'weekly'; }

  // ── 💬 pregúntale ───────────────────────────────────────────────────────
  function askHtml() {
    var sug = isEn() ? ['Why did my portfolio move this week?', 'Which position gives me the most risk?', 'What would you change to have fewer scares?', 'Explain my last report as if I were 12']
      : ['¿Por qué se movió mi cartera esta semana?', '¿Qué posición me da más riesgo?', '¿Qué cambiarías para tener menos sustos?', 'Explícame mi último reporte como si tuviera 12 años'];
    return card('<div class="cm-t pfe-hd">' + masc('khipu', 18) + esc(L('Pregúntale a tu cartera', 'Ask your portfolio')) + '</div>' +
      '<div class="cm-note" style="margin-bottom:8px">' + esc(L('Khipu responde usando TU cartera y tu último reporte como contexto, más datos en vivo. Es análisis de IA, no asesoría personalizada.', 'Khipu answers using YOUR portfolio and your latest report as context, plus live data. It is AI analysis, not personalized advice.')) + '</div>' +
      '<div id="pfa-log" class="pfe-log" aria-live="polite">' + S.chat.map(function (m) {
        var me = m.role === 'user';
        return '<div class="pfe-msg' + (me ? ' me' : '') + '">' + (me ? '' : masc('khipu', 26)) + '<div class="pfe-bub">' + md(m.content) +
          (m.sources && m.sources.length ? '<div class="cm-note" style="font-size:11px;margin-top:6px">' + esc(L('Fuentes: ', 'Sources: ') + m.sources.map(function (s) { return s.label || s.name || s; }).join(' · ')) + '</div>' : '') + '</div></div>';
      }).join('') + (S.asking ? '<div class="pfe-think">' + masc('khipu', 26, 'think') + '<span>' + esc(L('Khipu está pensando con tu cartera…', 'Khipu is thinking with your portfolio…')) + '</span></div>' : '') + '</div>' +
      (S.chat.length ? '' : '<div class="pfe-sugs">' + sug.map(function (q) { return '<button type="button" class="pfe-sug" data-sug="' + esc(q) + '">' + esc(q) + '</button>'; }).join('') + '</div>') +
      '<div class="cm-form" style="margin:10px 0 0"><input id="pfa-q" aria-label="' + esc(L('Tu pregunta', 'Your question')) + '" placeholder="' + esc(L('Pregunta lo que sea sobre tu cartera…', 'Ask anything about your portfolio…')) + '"><button class="cm-btn" id="pfa-send"' + (S.asking ? ' disabled' : '') + ' aria-label="' + esc(L('Enviar', 'Send')) + '">➤</button></div>');
  }

  // ── montaje ──────────────────────────────────────────────────────────────
  function paint() {
    var el = CUR.el; if (!el) return;
    var ctx = CUR.ctx;
    ensureCss();
    if (CUR.section === 'news') {
      el.innerHTML = '<div class="pfe">' + card('<div class="cm-t pfe-hd">' + masc('radar', 18) + esc(L('Noticias de tu cartera', 'Your portfolio news')) + '</div>' +
        '<div class="cm-form" style="margin-bottom:6px"><span class="cm-note" id="pfe-nd-l">' + esc(L('Ventana:', 'Window:')) + '</span>' +
          '<div class="pfe-seg" role="radiogroup" aria-labelledby="pfe-nd-l">' + [1, 3, 7, 30].map(function (d) {
            var on = S.newsDays === d;
            return '<button type="button" role="radio" aria-checked="' + on + '"' + (on ? ' class="on"' : '') + ' data-nd="' + d + '">' + d + L(d === 1 ? ' día' : ' días', d === 1 ? ' day' : ' days') + '</button>'; }).join('') + '</div></div>' +
        '<div class="cm-note" style="font-size:11.5px;margin-bottom:6px">' + esc(L('Solo noticias con fecha dentro de la ventana, sin repetir. 🆕 = de hoy.', 'Only dated news within the window, no repeats. 🆕 = today.')) + '</div>' +
        (S.news == null ? '<div class="cm-note"><span class="cm-spin">◌</span> ' + esc(L('Buscando noticias…', 'Fetching news…')) + '</div>' : newsList(S.news.items))) + '</div>';
    } else if (CUR.section === 'ask') {
      el.innerHTML = '<div class="pfe">' + askHtml() + '</div>';
      var lg = document.getElementById('pfa-log'); if (lg) lg.scrollTop = lg.scrollHeight;
    } else {
      el.innerHTML = '<div class="pfe">' + reportsHtml(ctx) + '</div>';
    }
    wire();
  }
  function wire() {
    var el = CUR.el, ctx = CUR.ctx;
    el.querySelectorAll('[data-nd]').forEach(function (b) { b.onclick = function () { S.newsDays = +b.getAttribute('data-nd'); loadNews(); }; });
    var g = document.getElementById('pfr-gen'); if (g) g.onclick = generate;
    var pp = document.getElementById('pfr-period'); if (pp) pp.onchange = function () { S.period = pp.value; };
    var sc = document.getElementById('pfr-sched'); if (sc) sc.onchange = function () { saveWatch(sc.value); };
    el.querySelectorAll('[data-rid]').forEach(function (x) {
      x.onclick = function () { openReport(x.getAttribute('data-rid')); };
      x.onkeydown = function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openReport(x.getAttribute('data-rid')); } };
    });
    var bk = document.getElementById('pfr-back'); if (bk) bk.onclick = function () { S.viewing = null; loadReports(); };
    var pr = document.getElementById('pfr-print-btn'); if (pr) pr.onclick = printReport;
    el.querySelectorAll('[data-sug]').forEach(function (b) { b.onclick = function () { ask(b.getAttribute('data-sug')); }; });
    var sd = document.getElementById('pfa-send'), qi = document.getElementById('pfa-q');
    if (sd && qi) { sd.onclick = function () { ask(qi.value); }; qi.onkeydown = function (e) { if (e.key === 'Enter') ask(qi.value); }; }
  }
  function body(ctx) {
    return { positions: ctx.source.positions, cash_usd: ctx.source.cash || 0, start_value: ctx.source.start || null,
      start_date: ctx.source.startDate || null, profile: Object.assign({ lang: isEn() ? 'en' : 'es' }, ctx.profile || {}),
      lang: isEn() ? 'en' : 'es', actor: actor(), name: ctx.source.label };
  }
  function generate() {
    var ctx = CUR.ctx; if (!ctx || !ctx.source) return;
    S.busy = true; S.err = null; paint();
    api('/api/portfolio-report/generate', { method: 'POST', body: JSON.stringify(Object.assign(body(ctx), { period: S.period })) }).then(function (d) {
      S.busy = false;
      if (!d.ok) { S.err = errOf(d); paint(); return; }
      S.viewing = d; paint(); loadReports(true);
    }).catch(function () { S.busy = false; S.err = L('Sin conexión con el servidor.', 'No connection to the server.'); paint(); });
  }
  function saveWatch(sched) {
    var ctx = CUR.ctx;
    api('/api/portfolio-report/watch', { method: 'POST', body: JSON.stringify(Object.assign(body(ctx), { schedule: sched, source_key: ctx.source.key })) }).then(function (d) {
      if (d.ok) { S.err = null; loadWatches(); if (window.KhipuToast) window.KhipuToast.show({ kind: 'info', title: L('Reportes automáticos', 'Automatic reports'), body: sched === 'off' ? L('Apagados.', 'Turned off.') : L('Programados: ', 'Scheduled: ') + sched }); }
      else { S.err = errOf(d); paint(); }
    });
  }
  function loadReports(silent) {
    api('/api/portfolio-report/list').then(function (d) { S.reports = d.reports || []; if (!silent || CUR.section === 'reports') paint(); });
  }
  function loadWatches() { api('/api/portfolio-report/watches').then(function (d) { S.watches = d.watches || []; paint(); }); }
  function openReport(id) { api('/api/portfolio-report/' + encodeURIComponent(id)).then(function (d) { if (d.performance) { S.viewing = d; paint(); } }); }
  function loadNews() {
    var ctx = CUR.ctx; S.news = null; paint();
    var weights = {};
    ((ctx.analysis && ctx.analysis.positions) || []).forEach(function (p) { weights[p.symbol] = p.weight_pct; });
    api('/api/news/portfolio', { method: 'POST', body: JSON.stringify({ days: S.newsDays, lang: isEn() ? 'en' : 'es',
      holdings: ctx.source.positions.map(function (p) { return { id: p.id, label: p.label, symbol: p.symbol, weight_pct: weights[p.symbol] }; }) }) })
      .then(function (d) { S.news = d; paint(); }).catch(function () { S.news = { items: [] }; paint(); });
  }
  function ask(q) {
    q = String(q || '').trim(); if (!q || S.asking) return;
    var ctx = CUR.ctx;
    S.chat.push({ role: 'user', content: q }); S.asking = true; paint();
    var last = (S.reports || [])[0];
    api('/api/portfolio-report/ask', { method: 'POST', body: JSON.stringify({ question: q, lang: isEn() ? 'en' : 'es', actor: actor(),
      positions: ctx.source.positions, report_id: (S.viewing && S.viewing.id) || (last && last.id) || null,
      notes: ctx.analysis ? notesFrom(ctx.analysis) : '',
      history: S.chat.slice(0, -1).slice(-8).map(function (m) { return { role: m.role, content: m.content }; }) }) }).then(function (d) {
      S.asking = false;
      S.chat.push({ role: 'assistant', content: d.answer || errOf(d), sources: d.sources || [] });
      paint();
    }).catch(function () { S.asking = false; S.chat.push({ role: 'assistant', content: L('Sin conexión con el servidor.', 'No connection to the server.') }); paint(); });
  }
  function notesFrom(a) {
    var k = a.kpis || {}, lines = ['Diagnóstico del comité de cartera: salud ' + (a.health || {}).score + '/100 (' + (a.health || {}).verdict + '); valor ' + k.value_usd +
      ' USD; volatilidad anual ' + k.vol_ann_pct + ' %; peor caída ' + k.max_drawdown_pct + ' %; perfil ' + ((a.profile || {}).label || '') + '.'];
    (a.positions || []).forEach(function (p) { lines.push(p.label + ' (' + p.symbol + '): peso ' + p.weight_pct + ' %, aporta ' + p.risk_contrib_pct + ' % del riesgo, convicción ' + (p.conviction == null ? 'sin investigar' : p.conviction) + '.'); });
    (a.actions || []).slice(0, 5).forEach(function (x) { lines.push('Acción ' + x.id + ': ' + x.why_es); });
    return lines.join('\n').slice(0, 3000);
  }
  // impresión / PDF: papel = tema CLARO de Khipus OS (tokens definidos en :root de la ventana) + las mismas reglas pfe-*
  var PRINT_TOKENS = ':root{--os-surface:#FFFFFF;--os-surface-2:#F2F2F7;--os-surface-3:#E7E7EF;--os-ink:#111216;--os-ink-2:#5B5E6B;--os-ink-3:#8D90A0;' +
    '--os-line:rgba(17,18,22,.14);--os-mute:#C9CAD6;--os-accent:#2F6BEA;--os-good:#0ca30c;--os-bad:#d03b3b;--cm-good:#066B06;--cm-bad:#A82424;--cm-warn:#7F5200;--cm-warn-fill:#B7791F;--cm-ai:#6236C9;--kos-accent-soft:rgba(47,107,234,.12);' +
    '--os-shadow:none;--os-r-sm:12px;--os-font:\'Nunito\',\'Geist\',system-ui,-apple-system,\'Segoe UI\',sans-serif;color-scheme:light}';
  function printReport() {
    var el = document.getElementById('pfr-print'); if (!el) return;
    var w = window.open('', '_blank'); if (!w) return;
    w.document.write('<!doctype html><html><head><meta charset="utf-8"><title>' + esc((S.viewing && S.viewing.title) || L('Reporte', 'Report')) + '</title>' +
      '<style>' + PRINT_TOKENS + 'body{font-family:var(--os-font);background:var(--os-surface);color:var(--os-ink);padding:24px;-webkit-print-color-adjust:exact;print-color-adjust:exact}' +
      '.cm-cell{border:1px solid var(--os-line);border-radius:18px;padding:14px 16px;margin-bottom:12px;break-inside:avoid}' +
      '.cm-note{color:var(--os-ink-2);font-size:12px;line-height:1.55}.cm-t{font-weight:700;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--os-ink-3);margin-bottom:8px;display:flex;align-items:center;gap:4px}' +
      '.cm-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}button{display:none}a{color:var(--os-accent)}' + CSS + '</style></head><body><div class="pfe">' + el.innerHTML + '</div></body></html>');
    w.document.close(); setTimeout(function () { try { w.print(); } catch (e) {} }, 300);
  }

  // aviso al abrir la app: reportes automáticos nuevos (solo si ya hay una llave de dueño)
  setTimeout(function () {
    var k = null; try { k = localStorage.getItem('kh_owner_key'); } catch (e) {}
    if (!k) return;
    api('/api/portfolio-report/list').then(function (d) {
      var n = d.unread || 0; if (!n) return;
      var msg = L('Tienes ' + n + ' reporte(s) nuevo(s) de tu cartera. Ábrelos en Comité → 💼 Mi cartera → 📄 Reportes.',
        'You have ' + n + ' new portfolio report(s). Open them in Committee → 💼 My portfolio → 📄 Reports.');
      if (window.KhipuToast && window.KhipuToast.show) window.KhipuToast.show({ kind: 'info', title: L('📄 Reportes nuevos', '📄 New reports'), body: msg, timeout: 12000,
        onClick: function () { if (window.KhipuCommittee && window.KhipuCommittee.openTab) window.KhipuCommittee.openTab('portfolio'); } });
    }).catch(function () {});
  }, 9000);

  window.KhipuPortfolioExtras = {
    render: function (el, section, ctx) {
      var changed = !CUR.ctx || !ctx || CUR.ctx.source.key !== ctx.source.key;
      CUR.el = el; CUR.section = section; CUR.ctx = ctx;
      if (changed) { S.news = null; S.chat = []; S.viewing = null; }
      paint();
      if (section === 'reports') { if (S.reports == null || changed) loadReports(); if (S.watches == null || changed) loadWatches(); }
      if (section === 'news' && (S.news == null || changed)) loadNews();
    },
    suggestedSchedule: suggestedSchedule,
    syncWatch: function (ctx) {   // mantiene al día las posiciones de una cartera con reportes automáticos
      if (!(S.watches || []).some(function (w) { return w.source_key === ctx.source.key && w.schedule !== 'off'; })) return;
      var w = S.watches.filter(function (x) { return x.source_key === ctx.source.key; })[0];
      api('/api/portfolio-report/watch', { method: 'POST', body: JSON.stringify(Object.assign(body(ctx), { schedule: w.schedule, source_key: ctx.source.key })) });
    },
    unread: function () { return api('/api/portfolio-report/list').then(function (d) { return d.unread || 0; }).catch(function () { return 0; }); },
  };
})();
