/* ============================================================================
   engine/xray.js — X-RAY DE EMPRESA · "desarmar el alma" (Etapa 4, wow #1)
   Overlay NEXUS-styled que abre para cualquier nodo:
   - anatomía (sector, país, precio en vivo, fundamentales)
   - NRS descompuesto término a término (auditabilidad Palantir) + ranking
   - los HILOS entrantes/salientes con peso, clicables → saltan al mapa
   - simulación de impacto INSTANTÁNEA (motor de estados client-side KhipuState,
     ~7ms; el servidor /api/matrix/impact solo refina después si está)

   Dos modos de render sobre el MISMO HTML (buildXRayHTML):
   - cajón lateral (#xray, 560px) — abre desde el mapa
   - escenario grande (.xr-full, multi-columna) — la Cabina de Khipu lo usa a
     pantalla completa para "destripar la empresa por completo".

   Estilos scoped a .xray-scope — no tocan el resto de la app. Piel NEXUS.
   ============================================================================ */
(function () {
  'use strict';

  var SECTORS9 = (typeof window.SECTORS9 !== 'undefined') ? window.SECTORS9 : {};
  var CAT_TO_SECTOR = (typeof window.CAT_TO_SECTOR !== 'undefined') ? window.CAT_TO_SECTOR : {};
  function sectorOf(cat) { return CAT_TO_SECTOR[cat] || 'cloud_ia'; }
  function sectorColor(cat) { var s = SECTORS9[sectorOf(cat)]; return s ? s.color : '#00E0FF'; }
  function sectorLabel(cat) {
    if (window.sectorName) return window.sectorName(sectorOf(cat));
    var s = SECTORS9[sectorOf(cat)]; return s ? s.label : 'Cloud & IA';
  }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function lid(v) { return (typeof v === 'object' && v !== null) ? v.id : v; }
  function fmtPct(v) { return (v >= 0 ? '+' : '') + v.toFixed(1) + '%'; }
  // REGLA BILINGÜE: todo texto visible pasa por L(es, en)
  function isEn() {
    var l = window.LANG;
    if (!l) { try { l = localStorage.getItem('eco_lang'); } catch (e) { l = null; } }
    return l === 'en';
  }
  function L(es, en) { return isEn() ? en : es; }

  // ── estilos (inyectados una vez) ──
  function ensureStyles() {
    if (document.getElementById('xray-styles')) return;
    var css = `
#xray-ov{position:fixed;inset:0;z-index:6000;display:none;align-items:stretch;justify-content:flex-end;
  background:rgba(3,6,12,.62);backdrop-filter:blur(3px);font-family:'Inter',system-ui,sans-serif}
#xray-ov.show{display:flex;animation:xrFade .18s ease}
@keyframes xrFade{from{opacity:0}to{opacity:1}}
#xray{width:min(560px,100%);height:100%;overflow-y:auto;color:#E8EDFB;
  background:radial-gradient(900px 500px at 70% -5%,#0B1222 0%,#06090F 60%);
  border-left:1px solid rgba(122,158,255,.18);box-shadow:-24px 0 60px rgba(0,0,0,.5);
  transform:translateX(24px);animation:xrSlide .22s ease forwards}
@keyframes xrSlide{to{transform:translateX(0)}}
@media(prefers-reduced-motion:reduce){#xray{animation:none;transform:none}#xray-ov.show{animation:none}}
.xray-scope{color:#E8EDFB;font-family:'Inter',system-ui,sans-serif}
.xray-scope .xr-mono{font-family:'JetBrains Mono','Cascadia Mono',monospace;font-variant-numeric:tabular-nums}
.xray-scope .xr-hd{position:sticky;top:0;z-index:2;padding:16px 20px 13px;
  background:linear-gradient(#0a1120ee,#0a1120cc);border-bottom:1px solid rgba(122,158,255,.14);backdrop-filter:blur(6px)}
.xray-scope .xr-close{position:absolute;top:13px;right:16px;width:30px;height:30px;border-radius:8px;cursor:pointer;
  border:1px solid rgba(122,158,255,.2);background:rgba(21,28,45,.7);color:#7C87A3;font-size:16px;line-height:1}
.xray-scope .xr-close:hover{color:#E8EDFB;border-color:rgba(122,158,255,.4)}
.xray-scope .xr-name{font-size:20px;font-weight:650;display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;padding-right:34px}
.xray-scope .xr-tk{font-size:12px;color:#7C87A3;font-weight:400}
.xray-scope .xr-sec{display:inline-flex;align-items:center;gap:7px;font-size:11px;color:#9BA6C4;margin-top:6px}
.xray-scope .xr-dot{width:9px;height:9px;border-radius:50%;box-shadow:0 0 7px currentColor}
.xray-scope .xr-px{margin-top:11px;display:flex;align-items:baseline;gap:9px}
.xray-scope .xr-px .p{font-size:23px;font-weight:600}
.xray-scope .xr-px .chg{font-size:13px}
.xray-scope .xr-lin{font-size:10px;color:#5b6580;margin-top:3px}
.xray-scope .xr-sect{padding:15px 20px;border-bottom:1px solid rgba(122,158,255,.08)}
.xray-scope .xr-h{font-size:10.5px;letter-spacing:.15em;text-transform:uppercase;color:#7C87A3;font-weight:600;
  margin:0 0 11px;display:flex;justify-content:space-between;align-items:center}
.xray-scope .xr-h .v{letter-spacing:0}
.xray-scope .nrsrow{display:grid;grid-template-columns:104px 1fr 62px;gap:9px;align-items:center;font-size:11.5px;color:#9BA6C4;margin:5px 0}
.xray-scope .nrsbar{height:6px;border-radius:5px;background:rgba(21,28,45,.9);overflow:hidden;border:1px solid rgba(122,158,255,.1)}
.xray-scope .nrsbar i{display:block;height:100%;background:#00E0FF;border-radius:5px}
.xray-scope .nrsrow.hot i{background:#FF4D6A}
.xray-scope .nrsrow .nv{text-align:right;color:#E8EDFB}
.xray-scope .nrsrow .nd{font-size:9.5px;color:#5b6580}
.xray-scope .thread{display:flex;align-items:center;gap:9px;font-size:12px;padding:6px 9px;margin:3px 0;cursor:pointer;
  border:1px solid rgba(122,158,255,.1);border-radius:8px;background:rgba(21,28,45,.55);transition:border-color .12s,transform .12s}
.xray-scope .thread:hover{border-color:rgba(122,158,255,.42);transform:translateX(-3px)}
.xray-scope .thread .tdir{font-family:'JetBrains Mono',monospace;flex:none;width:14px;text-align:center}
.xray-scope .thread .tnm{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.xray-scope .thread .trel{font-size:9px;color:#5b6580;flex:none;max-width:90px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.xray-scope .thread .tw{font-family:'JetBrains Mono',monospace;font-size:10px;color:#7C87A3;flex:none}
.xray-scope .tcap{font-size:10px;color:#7C87A3;margin:9px 0 5px;text-transform:uppercase;letter-spacing:.08em}
.xray-scope .relchips{display:flex;flex-wrap:wrap;gap:5px}
.xray-scope .relchip{font-size:10px;color:#9BA6C4;padding:3px 9px;border-radius:999px;
  background:rgba(21,28,45,.7);border:1px solid rgba(122,158,255,.14)}
.xray-scope .relchip b{color:#E8EDFB;font-family:'JetBrains Mono',monospace}
.xray-scope .impact-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:9px;text-align:center}
.xray-scope .icell{border:1px solid rgba(122,158,255,.12);border-radius:9px;padding:10px 5px;background:rgba(21,28,45,.6)}
.xray-scope .icell b{display:block;font-family:'JetBrains Mono',monospace;font-size:17px;font-weight:600;color:#FF4D6A}
.xray-scope .icell span{font-size:9px;color:#7C87A3;text-transform:uppercase;letter-spacing:.06em;margin-top:2px;display:block}
.xray-scope .xr-btns{display:flex;gap:7px;flex-wrap:wrap;padding:14px 20px}
.xray-scope .xrb{border:1px solid rgba(122,158,255,.2);background:rgba(21,28,45,.7);color:#E8EDFB;
  font-family:'Inter',sans-serif;font-size:11.5px;padding:7px 13px;border-radius:8px;cursor:pointer;transition:all .12s}
.xray-scope .xrb:hover{border-color:rgba(122,158,255,.5)}
.xray-scope .xrb.pri{background:#00E0FF;color:#03141C;border-color:#00E0FF;font-weight:600;box-shadow:0 0 14px rgba(0,224,255,.4)}
.xray-scope .xr-victim{display:flex;align-items:center;gap:8px;font-size:11.5px;padding:4px 0;cursor:pointer}
.xray-scope .xr-victim:hover .vn{color:#00E0FF}
.xray-scope .xr-victim .vn{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.xray-scope .xr-victim .vbar{flex:1;height:4px;border-radius:3px;background:rgba(255,77,106,.15);overflow:hidden}
.xray-scope .xr-victim .vbar i{display:block;height:100%;background:#FF4D6A}
.xray-scope .xr-victim .vp{font-family:'JetBrains Mono',monospace;font-size:10px;color:#FF4D6A;width:40px;text-align:right;flex:none}
.xray-scope .xr-loading{color:#7C87A3;font-size:11px;font-style:italic}
.xray-scope .xr-note{font-size:11.5px;line-height:1.55;color:#AEB7CF;margin-top:11px}
.xray-scope .thread-scroll{max-height:none}
/* ── modo escenario (pantalla completa, Cabina de Khipu) ── */
.xray-scope.xr-full{padding:0 4px 24px}
.xray-scope.xr-full .xr-hd{position:relative;background:transparent;border-bottom:1px solid rgba(122,158,255,.14);padding:6px 8px 16px}
.xray-scope.xr-full .xr-name{font-size:26px}
.xray-scope.xr-full .xr-cols{column-width:340px;column-gap:18px;padding:16px 8px 0}
.xray-scope.xr-full .xr-cols .xr-sect{break-inside:avoid;border:1px solid rgba(122,158,255,.12);border-radius:14px;
  margin:0 0 16px;background:rgba(11,18,34,.5)}
.xray-scope.xr-full .thread-scroll{max-height:280px;overflow-y:auto}
.xray-scope.xr-full .xr-btns{padding:8px}
#xray-fab{position:fixed;left:0;top:0;z-index:5999}
`;
    var st = document.createElement('style');
    st.id = 'xray-styles';
    st.textContent = css;
    document.head.appendChild(st);
  }

  // ── HILOS entrantes / salientes ──
  function threadsFor(id) {
    var up = [], down = [];
    (window.LINKS || []).forEach(function (l) {
      var s = lid(l.source), t = lid(l.target);
      if (t === id && window.NODE_BY_ID[s]) up.push({ n: window.NODE_BY_ID[s], w: l.w || 2, rel: l.rel, type: l.type });
      if (s === id && window.NODE_BY_ID[t]) down.push({ n: window.NODE_BY_ID[t], w: l.w || 2, rel: l.rel, type: l.type });
    });
    up.sort(function (a, b) { return b.w - a.w; });
    down.sort(function (a, b) { return b.w - a.w; });
    return { up: up, down: down };
  }

  function threadRow(t, dir) {
    var arrow = dir === 'up' ? '←' : '→';
    return '<div class="thread" onclick="window._xrayJump(\'' + esc(t.n.id) + '\')" title="' + esc(t.rel || '') + '">' +
      '<span class="tdir" style="color:' + sectorColor(t.n.cat) + '">' + arrow + '</span>' +
      '<span class="tnm">' + esc(t.n.label) + '</span>' +
      (t.rel ? '<span class="trel">' + esc(t.rel) + '</span>' : '') +
      '<span class="tw">w' + t.w + '</span></div>';
  }

  // conteo por tipo de relación (para el desglose "de qué está hecha")
  function relBreakdown(th) {
    var counts = {};
    th.up.concat(th.down).forEach(function (t) { var k = t.type || 'supply'; counts[k] = (counts[k] || 0) + 1; });
    return Object.keys(counts).sort(function (a, b) { return counts[b] - counts[a]; })
      .map(function (k) { return '<span class="relchip">' + esc(k) + ' <b>' + counts[k] + '</b></span>'; }).join('');
  }

  // ranking de riesgo entre las 407 (barato: NODES ~407)
  function nrsRank(id, total) {
    if (typeof window.computeNRS !== 'function' || !window.NODES) return null;
    var worse = 0, n = 0;
    window.NODES.forEach(function (x) { var s = window.computeNRS(x.id); if (s != null) { n++; if (s > total) worse++; } });
    return { rank: worse + 1, of: n };
  }

  // Estado en bolsa VERIFICADO (nodes/listing_status.js): salió a bolsa, la
  // compraron, cerró… con fecha de verificación y fuente clicable.
  function listingLine(n) {
    var e = n && n.listing;
    if (!e || e.status === 'private' || e.status === 'unknown') return '';
    var txt = L(e.note_es || '', e.note_en || e.note_es || '');
    if (!txt) return '';
    var src = e.source_url ? ' · <a href="' + esc(e.source_url) + '" target="_blank" rel="noopener noreferrer" style="color:#7C87A3">' + L('fuente', 'source') + ' ↗</a>' : '';
    return '<div class="xr-note" style="margin-top:6px">✓ ' + esc(txt) +
      '<span style="color:#7C87A3;font-size:10.5px"> · ' + L('verificado', 'verified') + ' ' + esc(e.as_of || '') + src + '</span></div>';
  }

  // ── construye el HTML interno del X-Ray (lo usan el cajón y el escenario) ──
  function buildXRayHTML(id, opts) {
    opts = opts || {};
    var full = !!opts.full;
    var n = window.NODE_BY_ID ? window.NODE_BY_ID[id] : null;
    if (!n) return '<div class="xr-loading" style="padding:24px">' + L('Sin datos para ', 'No data for ') + esc(id) + '</div>';
    var col = sectorColor(n.cat);
    var bd = window.computeNRSBreakdown ? window.computeNRSBreakdown(id) : null;
    var th = threadsFor(id);
    var meta = (window.NODE_META || {})[id] || {};
    var tk = (n.ticker || '').split(' · ')[0];
    var rank = bd ? nrsRank(id, bd.total) : null;

    var nrsHTML = bd ? bd.terms.map(function (t) {
      return '<div class="nrsrow' + (t.hot ? ' hot' : '') + '">' +
        '<span>' + t.key + '<div class="nd">' + esc(t.detail) + '</div></span>' +
        '<div class="nrsbar"><i style="width:' + Math.round(t.val / t.max * 100) + '%"></i></div>' +
        '<span class="nv xr-mono">' + t.val + '/' + t.max + '</span></div>';
    }).join('') : '<div class="xr-loading">' + L('NRS no disponible', 'NRS not available') + '</div>';

    // Anatomía: Empleados / Mkt Cap / Ingresos se reemplazan por el dato EN
    // VIVO (window.fillLiveMeta, en wire) cuando hay perfil; si no, catálogo.
    var mm = (meta.founded || n.mkt) ? '<div class="xr-sect"><div class="xr-h">' + L('Anatomía', 'Anatomy') + '</div>' +
      '<div class="impact-grid" style="grid-template-columns:1fr 1fr">' +
      '<div class="icell"><b style="color:#E8EDFB" class="xr-mono">' + esc(meta.founded || '—') + '</b><span>' + L('Fundada', 'Founded') + '</span></div>' +
      '<div class="icell"><b style="color:#E8EDFB" class="xr-mono xr-emp" data-live="employees" data-live-fmt="k">' + (meta.employees ? esc(meta.employees >= 1000 ? Math.round(meta.employees / 1000) + 'K' : meta.employees) : '—') + '</b><span>' + L('Empleados', 'Employees') + '</span></div>' +
      '<div class="icell"><b style="color:#E8EDFB" class="xr-mono xr-mcap" data-live="mcap">' + (meta.mktcap_b ? (isFinite(+meta.mktcap_b) ? '$' + esc(meta.mktcap_b) + 'B' + (window.liveCapDot ? window.liveCapDot(meta) : '') : esc(meta.mktcap_b)) : (n.mkt ? '—' : L('Priv.', 'Priv.'))) + '</b><span>Mkt Cap</span></div>' +
      '<div class="icell"><b style="color:#E8EDFB;font-size:15px;overflow-wrap:anywhere" class="xr-mono xr-rev" data-live="revenue">' + esc(meta.revenue_2025 || '—') + '</b><span class="xr-rev-l" data-live-label="revenue">' + L('Ingresos 2025', 'Revenue 2025') + '</span></div>' +
      '</div>' + (meta.geo_risk ? '<div class="xr-note">🌐 ' + esc(meta.geo_risk) + '</div>' : '') + '</div>' : '';

    // fundamentales extra (margen / crecimiento / puerto) si existen
    var funds = '';
    if (full && (n.margin != null || n.growth || n.country)) {
      // `growth` a veces es un número corto ("+35%") y a veces una FRASE
      // entera (bancos centrales, capa macro): la frase no cabe en un cuadrito
      // de 3 columnas y se volvía una torre ilegible — va como nota debajo.
      var g = String(n.growth || '').trim();
      var gCorto = g && g.length <= 14;
      funds = '<div class="xr-sect"><div class="xr-h">' + L('Fundamentales', 'Fundamentals') + '</div><div class="impact-grid">' +
        '<div class="icell"><b style="color:#E8EDFB" class="xr-mono">' + (n.margin != null ? Math.round(n.margin * 100) + '%' : '—') + '</b><span>' + L('Margen', 'Margin') + '</span></div>' +
        '<div class="icell"><b style="color:#E8EDFB;font-size:14px" class="xr-mono">' + (gCorto ? esc(g) : '—') + '</b><span>' + L('Crecim.', 'Growth') + '</span></div>' +
        '<div class="icell"><b style="color:#E8EDFB" class="xr-mono">' + esc(n.country || '—') + '</b><span>' + L('País', 'Country') + '</span></div>' +
        '</div>' + (g && !gCorto ? '<div class="xr-note">' + esc(g) + '</div>' : '') + '</div>';
    }

    // hilos: en escenario mostramos TODOS (scroll); en cajón, los 6 top
    var upList = full ? th.up : th.up.slice(0, 6);
    var downList = full ? th.down : th.down.slice(0, 6);
    var threadsHTML = '<div class="xr-sect"><div class="xr-h">' + L('Hilos — a quién provee / de quién depende', 'Threads — who it supplies / who it depends on') + '</div>' +
      (full && (th.up.length + th.down.length) ? '<div class="relchips" style="margin-bottom:10px">' + relBreakdown(th) + '</div>' : '') +
      (!th.up.length && !th.down.length ? '<div class="xr-loading">' + L('Sin vínculos de suministro en el mapa (su efecto llega por los factores macro).', 'No supply links on the map (its effect travels through macro factors).') + '</div>' : '') +
      (th.up.length ? '<div class="tcap">' + L('Depende de', 'Depends on') + ' (' + th.up.length + ')</div><div class="thread-scroll">' + upList.map(function (t) { return threadRow(t, 'up'); }).join('') + '</div>' : '') +
      (th.down.length ? '<div class="tcap">' + L('Provee a', 'Supplies') + ' (' + th.down.length + ')</div><div class="thread-scroll">' + downList.map(function (t) { return threadRow(t, 'down'); }).join('') + '</div>' : '') +
      '</div>';

    var header =
      '<div class="xr-hd">' +
        '<button class="xr-close" onclick="window._xrayClose()">✕</button>' +
        '<div class="xr-name">' + esc(n.label) + ' <span class="xr-tk xr-mono">' + esc(tk) + '</span></div>' +
        '<div class="xr-sec"><span class="xr-dot" style="background:' + col + ';color:' + col + '"></span>' +
          sectorLabel(n.cat) + ' · ' + esc(n.country || '—') + ' · ' + (th.up.length + th.down.length) + ' ' + L('vínculos', 'links') + '</div>' +
        '<div class="xr-px xr-mono" id="xr-px"><span class="p" style="color:#7C87A3">' + (n.mkt ? '— · —' : L('no cotiza en bolsa', 'not publicly traded')) + '</span></div>' +
        '<div class="xr-lin" id="xr-lin"></div>' + listingLine(n) +
      '</div>';

    var nrsSection =
      '<div class="xr-sect"><div class="xr-h"><span>' + L('Riesgo NRS — por qué ', 'NRS risk — why ') + (bd ? bd.total : '?') +
        (window.explainChip ? window.explainChip('nrs') : '') + '</span>' +
        '<span class="v xr-mono" style="color:' + (bd && bd.total >= 60 ? '#FF4D6A' : bd && bd.total >= 35 ? '#FFB300' : '#2BE38B') + '">' +
        (bd ? bd.total : '?') + '/100</span></div>' + nrsHTML +
        (rank ? '<div class="xr-lin" style="margin-top:8px">' + L('Ranking de riesgo: ', 'Risk ranking: ') + '<b style="color:#E8EDFB">#' + rank.rank + '</b> ' + L('de', 'of') + ' ' + rank.of + ' ' + L('empresas', 'companies') + '</div>' : '') +
        '<div class="xr-lin" style="margin-top:4px">' + L('ⓘ fórmula NRS · el motor de matrices puede fijarlo con datos vivos', 'ⓘ NRS formula · the matrix engine can refine it with live data') + '</div></div>';

    var impactSection =
      '<div class="xr-sect"><div class="xr-h">' + L('Si ', 'If ') + esc(n.label) + L(' cae — onda de impacto', ' fails — impact wave') + '</div>' +
        '<div id="xr-impact"><div class="xr-loading">' + L('Calculando propagación…', 'Computing propagation…') + '</div></div></div>';

    var btns =
      '<div class="xr-btns">' +
        '<span class="xrb pri" onclick="window._xrayShock(\'' + esc(id) + '\')">⚡ ' + L('Ver onda en el mapa', 'See wave on the map') + '</span>' +
        (window.openFinCard ? '<span class="xrb" onclick="window._surface ? window._surface(\'dossier\', \'' + esc(id) + '\') : window.openFinCard(\'' + esc(id) + '\')">📊 Dossier</span>' : '') +
        (window.openCompare ? '<span class="xrb" onclick="window._xrayCompare(\'' + esc(id) + '\')">⇄ ' + L('Comparar', 'Compare') + '</span>' : '') +
        (window.__tkgOpenObj ? '<span class="xrb" onclick="window._xrayTKG(\'' + esc(id) + '\')">◈ ' + L('En el tiempo', 'Over time') + '</span>' : '') +
        (window.KhipuResearch ? '<span class="xrb" onclick="window.KhipuResearch.open(\'' + esc(id) + '\')">🔬 ' + L('Investigación IA', 'AI research') + '</span>' : '') +
        (window.KhipuCommittee ? '<span class="xrb" onclick="window.KhipuCommittee.open(\'' + esc(id) + '\')">🏛 ' + L('Comité', 'Committee') + '</span>' : '') +
        (window._openSecondBrain ? '<span class="xrb" onclick="window._openSecondBrain(\'' + esc(id) + '\')">🧠 ' + L('Análisis IA', 'AI analysis') + '</span>' : '') +
      '</div>';

    var body = nrsSection + mm + funds + threadsHTML + impactSection + btns;
    if (full) return header + '<div class="xr-cols">' + body + '</div>';
    return header + body;
  }

  // ── precio en vivo (scoped al root) ──
  // 1º Finnhub (/api/quote, EE.UU.); si no responde o es de otra bolsa, el
  // perfil en vivo (KhipuLive: Yahoo, cualquier bolsa, en su moneda). Se
  // refresca cada 60 s mientras el X-Ray está a la vista (startPriceTimer).
  var PRICE_MS = 60 * 1000;
  function hhmmss(d) {
    try { return d.toLocaleTimeString(isEn() ? 'en-US' : 'es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' }); }
    catch (e) { return ''; }
  }
  // Estado del mercado → etiqueta honesta (misma regla que engine/fincard.js):
  // "en vivo" SOLO si la sesión está en curso. Yahoo quoteSummary trae
  // marketState; Finnhub y el gráfico de Yahoo no → se deduce por la
  // antigüedad del precio (`t` de Finnhub / market_time), nunca por el reloj
  // de la consulta. live: true = sesión en curso · false = último cierre ·
  // null = la fuente no dice ni estado ni hora.
  var STALE_UNKNOWN_MS = 30 * 60 * 1000, STALE_OPEN_MS = 6 * 3600 * 1000;
  function mktState(st) {
    st = String(st || '').toUpperCase();
    if (!st) return null;
    if (st === 'REGULAR') return { open: true, es: 'mercado abierto', en: 'market open' };
    if (st.indexOf('PRE') === 0) return { open: false, es: 'pre-apertura', en: 'pre-market' };
    if (st.indexOf('POST') === 0) return { open: false, es: 'después del cierre', en: 'after hours' };
    return { open: false, es: 'mercado cerrado', en: 'market closed' };
  }
  function quoteInfo(state, qt, asOf) {
    var ms = mktState(state);
    if (qt && isNaN(qt.getTime())) qt = null;
    var ref = asOf && !isNaN(asOf.getTime()) ? asOf.getTime() : Date.now();
    var age = qt ? Math.max(0, ref - qt.getTime()) : null;
    var live;
    if (ms) live = ms.open && !(age != null && age > STALE_OPEN_MS);
    else live = age != null ? age <= STALE_UNKNOWN_MS : null;
    return { ms: ms, qt: qt, live: live };
  }
  // hora del precio: "14:32:05" si es de hoy; "26 sep, 22:00" si es de otro día
  function whenTxt(d) {
    if (!d) return '';
    if (d.toDateString() === new Date().toDateString()) return hhmmss(d);
    try { return d.toLocaleString(isEn() ? 'en-US' : 'es-ES', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false }); }
    catch (e) { return d.toISOString().slice(0, 16).replace('T', ' '); }
  }
  // `els` = {px, lin} capturados ANTES de la consulta: si el cajón ya muestra
  // otra empresa (render() reemplaza su innerHTML), esos nodos quedaron fuera
  // del documento y la respuesta vieja se descarta — nunca pinta el precio de
  // A en la ficha de B.
  function priceEls(root) {
    return { px: root.querySelector('#xr-px'), lin: root.querySelector('#xr-lin') };
  }
  function paintPrice(els, price, pct, cur, src, qi) {
    var el = els && els.px;
    if (!el || !el.isConnected || !(price > 0)) return;
    qi = qi || { live: null, qt: null, ms: null };
    var p = (!cur || cur === 'USD') ? '$' + price.toFixed(2)
      : price.toLocaleString(isEn() ? 'en-US' : 'es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' ' + esc(cur);
    // la variación dice de CUÁNDO es: "hoy" solo con sesión en curso
    var chgWhen = qi.live === true ? '' : qi.live === false ? ' ' + L('última sesión', 'last session') : '';
    el.innerHTML = '<span class="p">' + p + '</span>' +
      (pct != null && isFinite(pct) ? '<span class="chg" style="color:' + (pct >= 0 ? '#2BE38B' : '#FF4D6A') + '">' + fmtPct(pct) +
        (chgWhen ? '<small style="color:#7C87A3;font-size:10px">' + esc(chgWhen) + '</small>' : '') + '</span>' : '');
    var lin = els.lin;
    if (!lin || !lin.isConnected) return;
    var parts = ['ⓘ ' + src];
    if (qi.live === true) {
      parts.push(L('en vivo', 'live'));
      if (qi.qt) parts.push(L('precio de las ', 'price as of ') + whenTxt(qi.qt));
    } else if (qi.live === false) {
      parts.push(qi.ms ? L(qi.ms.es, qi.ms.en) : L('mercado cerrado', 'market closed'));
      if (qi.qt) parts.push(L('último precio: ', 'last price: ') + whenTxt(qi.qt));
    } else {
      parts.push(L('consultado ', 'checked ') + hhmmss(new Date()));
      parts.push(L('la fuente no indica la hora del precio', 'the source does not give the price time'));
    }
    parts.push(L('se revisa cada minuto', 'checked every minute'));
    lin.textContent = parts.join(' · ');
  }
  function loadPriceLive(els, n) {
    var K = window.KhipuLive;
    if (!K || !K.profile) return;
    K.profile(n.mkt).then(function (p) {
      if (!p || !p.available || p.price == null || !els.px || !els.px.isConnected) return;
      var qt = p.market_time ? new Date(p.market_time) : null;
      var asOf = p.as_of ? new Date(p.as_of) : null;
      paintPrice(els, +p.price, p.change_pct, p.currency, (K.sourceName && K.sourceName(p)) || p.source || '—',
        quoteInfo(p.market_state, qt, asOf));
    }).catch(function () {});
  }
  function loadPrice(root, n) {
    if (!n.mkt) return;
    var els = priceEls(root);          // capturados AHORA (ver priceEls)
    if (!els.px) return;
    if (!window.DataLayer) { loadPriceLive(els, n); return; }
    window.DataLayer.quote(n.mkt).then(function (q) {
      if (!els.px.isConnected) return;   // el cajón ya muestra otra empresa
      if (!q || !(q.c > 0)) { loadPriceLive(els, n); return; }   // Finnhub da c=0 si no conoce el símbolo
      var pct = q.pc ? (q.c - q.pc) / q.pc * 100 : null;
      // `t` de Finnhub = hora (unix) del último precio; sin ella no se afirma "en vivo"
      var qt = q.t > 0 ? new Date(q.t * 1000) : null;
      paintPrice(els, q.c, pct, 'USD', 'Finnhub', quoteInfo(null, qt, null));
    }).catch(function () { if (els.px.isConnected) loadPriceLive(els, n); });
  }
  function stopPriceTimer(root) {
    if (root && root._xrPxTimer) { clearInterval(root._xrPxTimer); root._xrPxTimer = null; }
  }
  function startPriceTimer(root, n) {
    stopPriceTimer(root);
    if (!n.mkt) return;
    root._xrPxTimer = setInterval(function () {
      // cerrado, re-renderizado o escondido (cajón / Cabina) → se apaga solo
      // desconectado (re-render / cerrado de verdad) → se apaga; solo OCULTO
      // (Cabina cerrada, pestaña Fundamentales) → se salta el tick y sigue
      if (!root.isConnected) { stopPriceTimer(root); return; }
      if (document.hidden || !root.getClientRects().length) return;
      loadPrice(root, n);
    }, PRICE_MS);
  }

  function renderVictims(root, id, n, impacts, note) {
    var arr = Object.keys(impacts)
      .filter(function (k) { return k !== id; })
      .map(function (k) { return { id: k, v: impacts[k] }; })
      .sort(function (a, b) { return b.v - a.v; });
    var totalCap = 0, portHit = 0;
    var pos = (window.MKT && window.MKT.pos) || {};
    arr.forEach(function (x) {
      var node = window.NODE_BY_ID[x.id]; if (!node) return;
      var meta = (window.NODE_META || {})[x.id] || {};
      var cap = Number(meta.mktcap_b);
      if (isFinite(cap) && cap > 0) totalCap += cap * (x.v / 100);
      if (pos[x.id]) portHit += x.v;
    });
    var isFull = root.classList && root.classList.contains('xr-full');
    var topN = isFull ? 12 : 6;
    var top = arr.slice(0, topN).map(function (x) {
      var node = window.NODE_BY_ID[x.id]; if (!node) return '';
      return '<div class="xr-victim" onclick="window._xrayJump(\'' + esc(x.id) + '\')">' +
        '<span class="xr-dot" style="width:7px;height:7px;background:' + sectorColor(node.cat) + '"></span>' +
        '<span class="vn">' + esc(node.label) + '</span>' +
        '<span class="vbar"><i style="width:' + Math.round(x.v) + '%"></i></span>' +
        '<span class="vp xr-mono">' + Math.round(x.v) + '%</span></div>';
    }).join('');
    var winners = computeWinners(id, impacts);
    var winHTML = winners.length ? '<div class="xr-h" style="margin:13px 0 6px;color:#2BE38B">' + L('Quién gana ↑', 'Who wins ↑') + '</div>' +
      winners.map(function (w) {
        var node = window.NODE_BY_ID[w.id];
        return '<div class="xr-victim" onclick="window._xrayJump(\'' + esc(w.id) + '\')">' +
          '<span class="xr-dot" style="width:7px;height:7px;background:' + sectorColor(node.cat) + '"></span>' +
          '<span class="vn">' + esc(node.label) + '</span>' +
          '<span class="vbar" style="background:rgba(43,227,139,.15)"><i style="width:' + w.up * 2 + '%;background:#2BE38B"></i></span>' +
          '<span class="vp xr-mono" style="color:#2BE38B">+' + w.up + '%</span></div>';
      }).join('') : '';
    var el = root.querySelector('#xr-impact');
    if (!el) return;
    el.innerHTML =
      '<div class="impact-grid" style="margin-bottom:11px">' +
        '<div class="icell"><b>' + arr.length + '</b><span>' + L('empresas', 'companies') + '</span></div>' +
        '<div class="icell"><b>$' + (totalCap >= 1000 ? (totalCap / 1000).toFixed(1) + 'T' : Math.round(totalCap) + 'B') + '</b><span>' + L('cap expuesta', 'exposed cap') + '</span></div>' +
        '<div class="icell"><b>' + (portHit > 0 ? '−' + Math.round(portHit / Math.max(1, Object.keys(pos).length)) + '%' : '—') + '</b><span>' + L('tu cartera', 'your portfolio') + '</span></div>' +
      '</div>' +
      '<div class="xr-h" style="margin:2px 0 6px">' + L('Quién sufre ↓', 'Who suffers ↓') + '</div>' + top + winHTML +
      (note ? '<div class="xr-lin" style="margin-top:8px">' + note + '</div>' : '');
  }

  // rivales (misma categoría) poco afectados que capturan la demanda huérfana
  function computeWinners(shockId, impacts) {
    var dn = window.NODE_BY_ID[shockId]; if (!dn) return [];
    var damaged = [];
    Object.keys(impacts).forEach(function (k) { if (impacts[k] >= 40) damaged.push({ id: k, v: impacts[k] }); });
    var gains = {};
    damaged.forEach(function (d) {
      var d0 = window.NODE_BY_ID[d.id]; if (!d0) return;
      (window.NODES || []).forEach(function (n) {
        if (n.id === d.id || n.cat !== d0.cat) return;
        if ((impacts[n.id] || 0) > 15) return;
        gains[n.id] = (gains[n.id] || 0) + d.v / 100;
      });
    });
    return Object.keys(gains).map(function (id) { return { id: id, up: Math.min(45, Math.round(gains[id] * 14)) }; })
      .filter(function (x) { return x.up >= 5; }).sort(function (a, b) { return b.up - a.up; }).slice(0, 4);
  }

  // impacto INSTANTÁNEO con el motor de estados client-side (KhipuState, ~7ms)
  function impactViaState(id) {
    if (!window.KhipuState || !window.KhipuState.simulate) return null;
    try {
      var shock = {}; shock[id] = { salud: 0 };
      var r = window.KhipuState.simulate(shock, [], 8, 0.6, false, { direction: 'down', kind: 'collapse' });
      if (!r || !r.impact) return null;
      var obj = {}; obj[id] = 100;
      r.impact.forEach(function (v, k) { if (k !== id && v > 0) obj[k] = v; });
      return obj;
    } catch (e) { return null; }
  }

  function loadImpact(root, id, n) {
    // 1) INSTANTÁNEO: motor de estados en el navegador (adiós "tarda mucho")
    var instant = impactViaState(id);
    var shown = !!(instant && Object.keys(instant).length > 1);
    if (shown) renderVictims(root, id, n, instant, L('ⓘ motor de estados en vivo (instantáneo)', 'ⓘ live state engine (instant)'));
    // Cierre SIEMPRE con un mensaje: antes, si nadie caía detrás (p.ej. la
    // Reserva Federal, 0 vínculos de suministro) o el servidor respondía sin
    // impactos, la sección se quedaba en "Calculando propagación…" para siempre.
    function finish() {
      if (shown) return;
      var el = root.querySelector('#xr-impact');
      if (typeof window.computeDownstream === 'function') {
        try {
          var affected = window.computeDownstream(id);
          var list = affected instanceof Set ? Array.from(affected) : (affected || []);
          if (list.length) {
            var impacts = {}; impacts[id] = 100;
            list.forEach(function (aid) { impacts[aid] = 55; });
            renderVictims(root, id, n, impacts, L('ⓘ estimación local', 'ⓘ local estimate'));
            return;
          }
        } catch (e) {}
      }
      if (el) el.innerHTML = '<div class="xr-loading">' + L(
        'Su caída no arrastra a ninguna empresa por la cadena de suministro. Si es un actor macro (banco central, regulador), su efecto se simula con los factores sistémicos (FACTOR LIST).',
        'Its failure does not drag any company down the supply chain. If it is a macro actor (central bank, regulator), its effect is simulated through systemic factors (FACTOR LIST).') + '</div>';
    }
    // 2) refinar en segundo plano con el motor de matrices del servidor (si está)
    fetch('/api/matrix/impact', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ shock: [id] }),
    }).then(function (r) { return r.ok ? r.json() : null; }).then(function (d) {
      if (d && d.impacts && Object.keys(d.impacts).length > 1) {
        shown = true;
        renderVictims(root, id, n, d.impacts, L('ⓘ motor de matrices (servidor · ponderado)', 'ⓘ matrix engine (server · weighted)'));
      } else finish();
    }).catch(finish);
  }

  // conecta precio + impacto a un root ya renderizado con buildXRayHTML
  function wire(root, id) {
    var n = window.NODE_BY_ID ? window.NODE_BY_ID[id] : null;
    if (!n) return;
    loadPrice(root, n);
    startPriceTimer(root, n);   // precio del encabezado: cada 60 s mientras esté abierto
    loadImpact(root, id, n);
    // Empleados / Mkt Cap / Ingresos EN VIVO (KhipuLive) con title "en vivo · fuente · hora"
    if (window.fillLiveMeta) window.fillLiveMeta(root, n);
    else if (window.fillLiveMcap) window.fillLiveMcap(root.querySelector('.xr-mcap'), n);
  }

  // ── cajón lateral (abre desde el mapa) ──
  function render(id) {
    var n = window.NODE_BY_ID ? window.NODE_BY_ID[id] : null;
    if (!n) return;
    // si la Cabina de Khipu está abierta, el X-Ray va al escenario grande
    if (window.BixbyCockpit && window.BixbyCockpit.isOpen && window.BixbyCockpit.isOpen()) {
      window.BixbyCockpit.stage('xray', id);
      return;
    }
    ensureStyles();
    var ov = document.getElementById('xray-ov');
    if (!ov) {
      ov = document.createElement('div');
      ov.id = 'xray-ov';
      ov.innerHTML = '<div id="xray" class="xray-scope"></div>';
      ov.addEventListener('click', function (e) { if (e.target === ov) close(); });
      document.body.appendChild(ov);
    }
    var box = document.getElementById('xray');
    box.innerHTML = buildXRayHTML(id, { full: false });
    ov.classList.add('show');
    wire(box, id);
  }

  function close() {
    var ov = document.getElementById('xray-ov');
    if (ov) ov.classList.remove('show');
    stopPriceTimer(document.getElementById('xray'));
  }

  window._xrayJump = function (id) {
    if (window.BixbyCockpit && window.BixbyCockpit.isOpen && window.BixbyCockpit.isOpen()) { window.BixbyCockpit.stage('xray', id); return; }
    close();
    if (typeof window.switchTab === 'function') window.switchTab('map');
    setTimeout(function () { if (typeof window.jumpTo === 'function') window.jumpTo(id); }, 90);
  };
  window._xrayClose = function () {
    if (window.BixbyCockpit && window.BixbyCockpit.isOpen && window.BixbyCockpit.isOpen()) { window.BixbyCockpit.stage('empty'); return; }
    close();
  };
  window._xrayShock = function (id) {
    if (window.BixbyCockpit && window.BixbyCockpit.isOpen && window.BixbyCockpit.isOpen()) { window.BixbyCockpit.stage('sim', { id: id, kind: 'collapse' }); return; }
    window._xrayJump(id); setTimeout(function () { if (typeof window.activateStress === 'function') window.activateStress(id); }, 220);
  };
  window._xrayTKG = function (id) { close(); if (typeof window.switchTab === 'function') window.switchTab('tkg'); setTimeout(function () { if (window.__tkgOpenObj) window.__tkgOpenObj(id); }, 200); };
  window._xrayCompare = function (id) {
    if (window.BixbyCockpit && window.BixbyCockpit.isOpen && window.BixbyCockpit.isOpen()) { window.BixbyCockpit.stage('compare', { a: id }); return; }
    close(); if (window.openCompare) window.openCompare(id);
  };
  window.openXRay = function (id) { render(id); };

  // API para la Cabina de Khipu
  window.buildXRayHTML = buildXRayHTML;
  window.wireXRay = wire;
  window.xrayEnsureStyles = ensureStyles;
  window.xrayImpactViaState = impactViaState;
  window.xrayComputeWinners = computeWinners;

  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });
})();
