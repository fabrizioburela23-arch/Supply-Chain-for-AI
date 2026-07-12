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
   - escenario grande (.xr-full, multi-columna) — la Cabina de Bixby lo usa a
     pantalla completa para "destripar la empresa por completo".

   Estilos scoped a .xray-scope — no tocan el resto de la app. Piel NEXUS.
   ============================================================================ */
(function () {
  'use strict';

  var SECTORS9 = (typeof window.SECTORS9 !== 'undefined') ? window.SECTORS9 : {};
  var CAT_TO_SECTOR = (typeof window.CAT_TO_SECTOR !== 'undefined') ? window.CAT_TO_SECTOR : {};
  function sectorOf(cat) { return CAT_TO_SECTOR[cat] || 'cloud_ia'; }
  function sectorColor(cat) { var s = SECTORS9[sectorOf(cat)]; return s ? s.color : '#00E0FF'; }
  function sectorLabel(cat) { var s = SECTORS9[sectorOf(cat)]; return s ? s.label : 'Cloud & IA'; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function lid(v) { return (typeof v === 'object' && v !== null) ? v.id : v; }
  function fmtPct(v) { return (v >= 0 ? '+' : '') + v.toFixed(1) + '%'; }

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
.xray-scope .thread-scroll{max-height:none}
/* ── modo escenario (pantalla completa, Cabina de Bixby) ── */
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

  // ── construye el HTML interno del X-Ray (lo usan el cajón y el escenario) ──
  function buildXRayHTML(id, opts) {
    opts = opts || {};
    var full = !!opts.full;
    var n = window.NODE_BY_ID ? window.NODE_BY_ID[id] : null;
    if (!n) return '<div class="xr-loading" style="padding:24px">Sin datos para ' + esc(id) + '</div>';
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
    }).join('') : '<div class="xr-loading">NRS no disponible</div>';

    var mm = meta.founded ? '<div class="xr-sect"><div class="xr-h">Anatomía</div>' +
      '<div class="impact-grid">' +
      '<div class="icell"><b style="color:#E8EDFB" class="xr-mono">' + (meta.founded || '—') + '</b><span>Fundada</span></div>' +
      '<div class="icell"><b style="color:#E8EDFB" class="xr-mono">' + (meta.employees ? (meta.employees >= 1000 ? Math.round(meta.employees / 1000) + 'K' : meta.employees) : '—') + '</b><span>Empleados</span></div>' +
      '<div class="icell"><b style="color:#E8EDFB" class="xr-mono">' + (meta.mktcap_b ? '$' + meta.mktcap_b + 'B' : 'Priv.') + '</b><span>Mkt Cap</span></div>' +
      '</div>' + (meta.geo_risk ? '<div class="tcap" style="margin-top:11px">🌐 ' + esc(meta.geo_risk) + '</div>' : '') + '</div>' : '';

    // fundamentales extra (margen / crecimiento / puerto) si existen
    var funds = '';
    if (full && (n.margin != null || n.growth || n.country)) {
      funds = '<div class="xr-sect"><div class="xr-h">Fundamentales</div><div class="impact-grid">' +
        '<div class="icell"><b style="color:#E8EDFB" class="xr-mono">' + (n.margin != null ? Math.round(n.margin * 100) + '%' : '—') + '</b><span>Margen</span></div>' +
        '<div class="icell"><b style="color:#E8EDFB;font-size:14px" class="xr-mono">' + esc(n.growth || '—') + '</b><span>Crecim.</span></div>' +
        '<div class="icell"><b style="color:#E8EDFB" class="xr-mono">' + esc(n.country || '—') + '</b><span>País</span></div>' +
        '</div></div>';
    }

    // hilos: en escenario mostramos TODOS (scroll); en cajón, los 6 top
    var upList = full ? th.up : th.up.slice(0, 6);
    var downList = full ? th.down : th.down.slice(0, 6);
    var threadsHTML = '<div class="xr-sect"><div class="xr-h">Hilos — a quién provee / de quién depende</div>' +
      (full && (th.up.length + th.down.length) ? '<div class="relchips" style="margin-bottom:10px">' + relBreakdown(th) + '</div>' : '') +
      (th.up.length ? '<div class="tcap">Depende de (' + th.up.length + ')</div><div class="thread-scroll">' + upList.map(function (t) { return threadRow(t, 'up'); }).join('') + '</div>' : '') +
      (th.down.length ? '<div class="tcap">Provee a (' + th.down.length + ')</div><div class="thread-scroll">' + downList.map(function (t) { return threadRow(t, 'down'); }).join('') + '</div>' : '') +
      '</div>';

    var header =
      '<div class="xr-hd">' +
        '<button class="xr-close" onclick="window._xrayClose()">✕</button>' +
        '<div class="xr-name">' + esc(n.label) + ' <span class="xr-tk xr-mono">' + esc(tk) + '</span></div>' +
        '<div class="xr-sec"><span class="xr-dot" style="background:' + col + ';color:' + col + '"></span>' +
          sectorLabel(n.cat) + ' · ' + esc(n.country || '—') + ' · ' + (th.up.length + th.down.length) + ' vínculos</div>' +
        '<div class="xr-px xr-mono" id="xr-px"><span class="p" style="color:#7C87A3">— · —</span></div>' +
        '<div class="xr-lin" id="xr-lin"></div>' +
      '</div>';

    var nrsSection =
      '<div class="xr-sect"><div class="xr-h"><span>Riesgo NRS — por qué ' + (bd ? bd.total : '?') + '</span>' +
        '<span class="v xr-mono" style="color:' + (bd && bd.total >= 60 ? '#FF4D6A' : bd && bd.total >= 35 ? '#FFB300' : '#2BE38B') + '">' +
        (bd ? bd.total : '?') + '/100</span></div>' + nrsHTML +
        (rank ? '<div class="xr-lin" style="margin-top:8px">Ranking de riesgo: <b style="color:#E8EDFB">#' + rank.rank + '</b> de ' + rank.of + ' empresas</div>' : '') +
        '<div class="xr-lin" style="margin-top:4px">ⓘ fórmula NRS · el motor de matrices puede fijarlo con datos vivos</div></div>';

    var impactSection =
      '<div class="xr-sect"><div class="xr-h">Si ' + esc(n.label) + ' cae — onda de impacto</div>' +
        '<div id="xr-impact"><div class="xr-loading">Calculando propagación…</div></div></div>';

    var btns =
      '<div class="xr-btns">' +
        '<span class="xrb pri" onclick="window._xrayShock(\'' + esc(id) + '\')">⚡ Ver onda en el mapa</span>' +
        (window.openFinCard ? '<span class="xrb" onclick="window.openFinCard(\'' + esc(n.mkt || id) + '\')">📊 Dossier</span>' : '') +
        (window.openCompare ? '<span class="xrb" onclick="window._xrayCompare(\'' + esc(id) + '\')">⇄ Comparar</span>' : '') +
        (window.__tkgOpenObj ? '<span class="xrb" onclick="window._xrayTKG(\'' + esc(id) + '\')">◈ En el tiempo</span>' : '') +
        (window._openSecondBrain ? '<span class="xrb" onclick="window._openSecondBrain(\'' + esc(id) + '\')">🧠 Análisis IA</span>' : '') +
      '</div>';

    var body = nrsSection + mm + funds + threadsHTML + impactSection + btns;
    if (full) return header + '<div class="xr-cols">' + body + '</div>';
    return header + body;
  }

  // ── precio en vivo (scoped al root) ──
  function loadPrice(root, n) {
    if (!n.mkt || !window.DataLayer) return;
    window.DataLayer.quote(n.mkt).then(function (q) {
      if (!q || q.c == null) return;
      var pct = q.pc ? (q.c - q.pc) / q.pc * 100 : 0;
      var el = root.querySelector('#xr-px');
      if (el) el.innerHTML = '<span class="p">$' + q.c.toFixed(2) + '</span>' +
        '<span class="chg" style="color:' + (pct >= 0 ? '#2BE38B' : '#FF4D6A') + '">' + fmtPct(pct) + '</span>';
      var lin = root.querySelector('#xr-lin');
      if (lin) lin.textContent = 'ⓘ Finnhub · en vivo';
    }).catch(function () {});
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
    var winHTML = winners.length ? '<div class="xr-h" style="margin:13px 0 6px;color:#2BE38B">Quién gana ↑</div>' +
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
        '<div class="icell"><b>' + arr.length + '</b><span>empresas</span></div>' +
        '<div class="icell"><b>$' + (totalCap >= 1000 ? (totalCap / 1000).toFixed(1) + 'T' : Math.round(totalCap) + 'B') + '</b><span>cap expuesta</span></div>' +
        '<div class="icell"><b>' + (portHit > 0 ? '−' + Math.round(portHit / Math.max(1, Object.keys(pos).length)) + '%' : '—') + '</b><span>tu cartera</span></div>' +
      '</div>' +
      '<div class="xr-h" style="margin:2px 0 6px">Quién sufre ↓</div>' + top + winHTML +
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
    if (instant && Object.keys(instant).length > 1) {
      renderVictims(root, id, n, instant, 'ⓘ motor de estados en vivo (instantáneo)');
    }
    // 2) refinar en segundo plano con el motor de matrices del servidor (si está)
    fetch('/api/matrix/impact', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ shock: [id] }),
    }).then(function (r) { return r.ok ? r.json() : null; }).then(function (d) {
      if (d && d.impacts && Object.keys(d.impacts).length > 1) {
        renderVictims(root, id, n, d.impacts, 'ⓘ motor de matrices (servidor · ponderado)');
      }
    }).catch(function () {
      // sin servidor: si tampoco hubo motor de estados, avisamos
      if (!instant || Object.keys(instant).length <= 1) {
        var el = root.querySelector('#xr-impact');
        if (typeof window.computeDownstream === 'function') {
          try {
            var affected = window.computeDownstream(id);
            var impacts = {}; impacts[id] = 100;
            (affected instanceof Set ? Array.from(affected) : affected || []).forEach(function (aid) { impacts[aid] = 55; });
            renderVictims(root, id, n, impacts, 'ⓘ estimación local');
            return;
          } catch (e) {}
        }
        if (el) el.innerHTML = '<div class="xr-loading">Propagación no disponible</div>';
      }
    });
  }

  // conecta precio + impacto a un root ya renderizado con buildXRayHTML
  function wire(root, id) {
    var n = window.NODE_BY_ID ? window.NODE_BY_ID[id] : null;
    if (!n) return;
    loadPrice(root, n);
    loadImpact(root, id, n);
  }

  // ── cajón lateral (abre desde el mapa) ──
  function render(id) {
    var n = window.NODE_BY_ID ? window.NODE_BY_ID[id] : null;
    if (!n) return;
    // si la Cabina de Bixby está abierta, el X-Ray va al escenario grande
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

  // API para la Cabina de Bixby
  window.buildXRayHTML = buildXRayHTML;
  window.wireXRay = wire;
  window.xrayEnsureStyles = ensureStyles;
  window.xrayImpactViaState = impactViaState;
  window.xrayComputeWinners = computeWinners;

  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });
})();
