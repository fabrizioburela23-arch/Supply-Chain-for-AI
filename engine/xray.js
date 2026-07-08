/* ============================================================================
   engine/xray.js — X-RAY DE EMPRESA · "desarmar el alma" (Etapa 4, wow #1)
   Overlay NEXUS-styled que abre para cualquier nodo:
   - anatomía (sector, país, precio en vivo, fundamentales)
   - NRS descompuesto término a término (auditabilidad Palantir)
   - los HILOS entrantes/salientes con peso, clicables → saltan al mapa
   - simulación de impacto: si el nodo cae, ¿a quién arrastra? (motor de
     matrices /api/matrix/impact, con fallback client-side computeDownstream)

   Diseño = piel NEXUS elegida (2026-07): fondo espacial, cristal, neón con
   intención, JetBrains Mono para cifras. Estilos scoped a #xray-* — no tocan
   el resto de la app. Semilla del rediseño visual (Etapa 4).
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
#xray .xr-mono{font-family:'JetBrains Mono','Cascadia Mono',monospace;font-variant-numeric:tabular-nums}
#xray .xr-hd{position:sticky;top:0;z-index:2;padding:16px 20px 13px;
  background:linear-gradient(#0a1120ee,#0a1120cc);border-bottom:1px solid rgba(122,158,255,.14);backdrop-filter:blur(6px)}
#xray .xr-close{position:absolute;top:13px;right:16px;width:30px;height:30px;border-radius:8px;cursor:pointer;
  border:1px solid rgba(122,158,255,.2);background:rgba(21,28,45,.7);color:#7C87A3;font-size:16px;line-height:1}
#xray .xr-close:hover{color:#E8EDFB;border-color:rgba(122,158,255,.4)}
#xray .xr-name{font-size:20px;font-weight:650;display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;padding-right:34px}
#xray .xr-tk{font-size:12px;color:#7C87A3;font-weight:400}
#xray .xr-sec{display:inline-flex;align-items:center;gap:7px;font-size:11px;color:#9BA6C4;margin-top:6px}
#xray .xr-dot{width:9px;height:9px;border-radius:50%;box-shadow:0 0 7px currentColor}
#xray .xr-px{margin-top:11px;display:flex;align-items:baseline;gap:9px}
#xray .xr-px .p{font-size:23px;font-weight:600}
#xray .xr-px .chg{font-size:13px}
#xray .xr-lin{font-size:10px;color:#5b6580;margin-top:3px}
#xray .xr-sect{padding:15px 20px;border-bottom:1px solid rgba(122,158,255,.08)}
#xray .xr-h{font-size:10.5px;letter-spacing:.15em;text-transform:uppercase;color:#7C87A3;font-weight:600;
  margin:0 0 11px;display:flex;justify-content:space-between;align-items:center}
#xray .xr-h .v{letter-spacing:0}
#xray .nrsrow{display:grid;grid-template-columns:104px 1fr 62px;gap:9px;align-items:center;font-size:11.5px;color:#9BA6C4;margin:5px 0}
#xray .nrsbar{height:6px;border-radius:5px;background:rgba(21,28,45,.9);overflow:hidden;border:1px solid rgba(122,158,255,.1)}
#xray .nrsbar i{display:block;height:100%;background:#00E0FF;border-radius:5px}
#xray .nrsrow.hot i{background:#FF4D6A}
#xray .nrsrow .nv{text-align:right;color:#E8EDFB}
#xray .nrsrow .nd{font-size:9.5px;color:#5b6580}
#xray .thread{display:flex;align-items:center;gap:9px;font-size:12px;padding:6px 9px;margin:3px 0;cursor:pointer;
  border:1px solid rgba(122,158,255,.1);border-radius:8px;background:rgba(21,28,45,.55);transition:border-color .12s,transform .12s}
#xray .thread:hover{border-color:rgba(122,158,255,.42);transform:translateX(-3px)}
#xray .thread .tdir{font-family:'JetBrains Mono',monospace;flex:none;width:14px;text-align:center}
#xray .thread .tnm{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#xray .thread .tw{font-family:'JetBrains Mono',monospace;font-size:10px;color:#7C87A3;flex:none}
#xray .tcap{font-size:10px;color:#7C87A3;margin:9px 0 5px;text-transform:uppercase;letter-spacing:.08em}
#xray .impact-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:9px;text-align:center}
#xray .icell{border:1px solid rgba(122,158,255,.12);border-radius:9px;padding:10px 5px;background:rgba(21,28,45,.6)}
#xray .icell b{display:block;font-family:'JetBrains Mono',monospace;font-size:17px;font-weight:600;color:#FF4D6A}
#xray .icell span{font-size:9px;color:#7C87A3;text-transform:uppercase;letter-spacing:.06em;margin-top:2px;display:block}
#xray .xr-btns{display:flex;gap:7px;flex-wrap:wrap;padding:14px 20px}
#xray .xrb{border:1px solid rgba(122,158,255,.2);background:rgba(21,28,45,.7);color:#E8EDFB;
  font-family:'Inter',sans-serif;font-size:11.5px;padding:7px 13px;border-radius:8px;cursor:pointer;transition:all .12s}
#xray .xrb:hover{border-color:rgba(122,158,255,.5)}
#xray .xrb.pri{background:#00E0FF;color:#03141C;border-color:#00E0FF;font-weight:600;box-shadow:0 0 14px rgba(0,224,255,.4)}
#xray .xr-victim{display:flex;align-items:center;gap:8px;font-size:11.5px;padding:4px 0;cursor:pointer}
#xray .xr-victim:hover .vn{color:#00E0FF}
#xray .xr-victim .vbar{flex:1;height:4px;border-radius:3px;background:rgba(255,77,106,.15);overflow:hidden}
#xray .xr-victim .vbar i{display:block;height:100%;background:#FF4D6A}
#xray .xr-victim .vp{font-family:'JetBrains Mono',monospace;font-size:10px;color:#FF4D6A;width:40px;text-align:right;flex:none}
#xray .xr-loading{color:#7C87A3;font-size:11px;font-style:italic}
#xray-fab{position:fixed;left:0;top:0;z-index:5999}
`;
    var st = document.createElement('style');
    st.id = 'xray-styles';
    st.textContent = css;
    document.head.appendChild(st);
  }

  function fmtPct(v) { return (v >= 0 ? '+' : '') + v.toFixed(1) + '%'; }

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
      '<span class="tw">w' + t.w + '</span></div>';
  }

  window._xrayJump = function (id) {
    close();
    if (typeof window.switchTab === 'function') window.switchTab('map');
    setTimeout(function () { if (typeof window.jumpTo === 'function') window.jumpTo(id); }, 90);
  };

  function close() {
    var ov = document.getElementById('xray-ov');
    if (ov) ov.classList.remove('show');
  }

  function render(id) {
    var n = window.NODE_BY_ID ? window.NODE_BY_ID[id] : null;
    if (!n) return;
    ensureStyles();
    var ov = document.getElementById('xray-ov');
    if (!ov) {
      ov = document.createElement('div');
      ov.id = 'xray-ov';
      ov.innerHTML = '<div id="xray"></div>';
      ov.addEventListener('click', function (e) { if (e.target === ov) close(); });
      document.body.appendChild(ov);
    }
    var col = sectorColor(n.cat);
    var bd = window.computeNRSBreakdown ? window.computeNRSBreakdown(id) : null;
    var th = threadsFor(id);
    var meta = (window.NODE_META || {})[id] || {};
    var tk = (n.ticker || '').split(' · ')[0];

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

    document.getElementById('xray').innerHTML =
      '<div class="xr-hd">' +
        '<button class="xr-close" onclick="window._xrayClose()">✕</button>' +
        '<div class="xr-name">' + esc(n.label) + ' <span class="xr-tk xr-mono">' + esc(tk) + '</span></div>' +
        '<div class="xr-sec"><span class="xr-dot" style="background:' + col + ';color:' + col + '"></span>' +
          sectorLabel(n.cat) + ' · ' + esc(n.country || '—') + ' · ' + (th.up.length + th.down.length) + ' vínculos</div>' +
        '<div class="xr-px xr-mono" id="xr-px"><span class="p" style="color:#7C87A3">— · —</span></div>' +
        '<div class="xr-lin" id="xr-lin"></div>' +
      '</div>' +
      '<div class="xr-sect"><div class="xr-h"><span>Riesgo NRS — por qué ' + (bd ? bd.total : '?') + '</span>' +
        '<span class="v xr-mono" style="color:' + (bd && bd.total >= 60 ? '#FF4D6A' : bd && bd.total >= 35 ? '#FFB300' : '#2BE38B') + '">' +
        (bd ? bd.total : '?') + '/100</span></div>' + nrsHTML +
        '<div class="xr-lin" style="margin-top:8px">ⓘ calculado por la fórmula NRS · el motor de matrices puede fijarlo con datos vivos</div></div>' +
      mm +
      '<div class="xr-sect"><div class="xr-h">Hilos — a quién provee / de quién depende</div>' +
        (th.up.length ? '<div class="tcap">Depende de (' + th.up.length + ')</div>' + th.up.slice(0, 6).map(function (t) { return threadRow(t, 'up'); }).join('') : '') +
        (th.down.length ? '<div class="tcap">Provee a (' + th.down.length + ')</div>' + th.down.slice(0, 6).map(function (t) { return threadRow(t, 'down'); }).join('') : '') +
      '</div>' +
      '<div class="xr-sect"><div class="xr-h">Si ' + esc(n.label) + ' cae — onda de impacto</div>' +
        '<div id="xr-impact"><div class="xr-loading">Calculando propagación…</div></div></div>' +
      '<div class="xr-btns">' +
        '<span class="xrb pri" onclick="window._xrayShock(\'' + esc(id) + '\')">⚡ Ver onda en el mapa</span>' +
        (window.__tkgOpenObj ? '<span class="xrb" onclick="window._xrayTKG(\'' + esc(id) + '\')">◈ En el tiempo</span>' : '') +
        (window._openSecondBrain ? '<span class="xrb" onclick="window._openSecondBrain(\'' + esc(id) + '\');window._xrayClose()">🧠 Análisis IA</span>' : '') +
      '</div>';

    ov.classList.add('show');
    loadPrice(n);
    loadImpact(id, n);
  }

  function loadPrice(n) {
    if (!n.mkt || !window.DataLayer) return;
    window.DataLayer.quote(n.mkt).then(function (q) {
      if (!q || q.c == null) return;
      var pct = q.pc ? (q.c - q.pc) / q.pc * 100 : 0;
      var el = document.getElementById('xr-px');
      if (el) el.innerHTML = '<span class="p">$' + q.c.toFixed(2) + '</span>' +
        '<span class="chg" style="color:' + (pct >= 0 ? '#2BE38B' : '#FF4D6A') + '">' + fmtPct(pct) + '</span>';
      var lin = document.getElementById('xr-lin');
      if (lin) lin.textContent = 'ⓘ Finnhub · en vivo';
    }).catch(function () {});
  }

  function renderVictims(id, n, impacts) {
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
    var top = arr.slice(0, 6).map(function (x) {
      var node = window.NODE_BY_ID[x.id]; if (!node) return '';
      return '<div class="xr-victim" onclick="window._xrayJump(\'' + esc(x.id) + '\')">' +
        '<span class="xr-dot" style="width:7px;height:7px;background:' + sectorColor(node.cat) + '"></span>' +
        '<span class="vn">' + esc(node.label) + '</span>' +
        '<span class="vbar"><i style="width:' + Math.round(x.v) + '%"></i></span>' +
        '<span class="vp xr-mono">' + Math.round(x.v) + '%</span></div>';
    }).join('');
    // GANADORES: rivales del caído (misma categoría, poco afectados) que capturan la demanda
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
    var el = document.getElementById('xr-impact');
    if (!el) return;
    el.innerHTML =
      '<div class="impact-grid" style="margin-bottom:11px">' +
        '<div class="icell"><b>' + arr.length + '</b><span>empresas</span></div>' +
        '<div class="icell"><b>$' + (totalCap >= 1000 ? (totalCap / 1000).toFixed(1) + 'T' : Math.round(totalCap) + 'B') + '</b><span>cap expuesta</span></div>' +
        '<div class="icell"><b>' + (portHit > 0 ? '−' + Math.round(portHit / Math.max(1, Object.keys(pos).length)) + '%' : '—') + '</b><span>tu cartera</span></div>' +
      '</div>' +
      '<div class="xr-h" style="margin:2px 0 6px">Quién sufre ↓</div>' + top + winHTML;
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

  function loadImpact(id, n) {
    // 1) motor de matrices en el server (preferido)
    fetch('/api/matrix/impact', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ shock: [id] }),
    }).then(function (r) { return r.ok ? r.json() : null; }).then(function (d) {
      if (d && d.impacts && Object.keys(d.impacts).length > 1) { renderVictims(id, n, d.impacts); return; }
      throw new Error('sin motor');
    }).catch(function () {
      // 2) fallback client-side: computeDownstream (binario) → % por profundidad
      var el = document.getElementById('xr-impact');
      if (typeof window.computeDownstream !== 'function') { if (el) el.innerHTML = '<div class="xr-loading">Propagación no disponible</div>'; return; }
      try {
        var affected = window.computeDownstream(id);
        var impacts = {}; impacts[id] = 100;
        (affected instanceof Set ? Array.from(affected) : affected || []).forEach(function (aid) { impacts[aid] = 55; });
        renderVictims(id, n, impacts);
        if (el) { var note = document.createElement('div'); note.className = 'xr-lin'; note.style.marginTop = '8px';
          note.textContent = 'ⓘ estimación local (configura DATABASE_URL en Railway para la propagación ponderada)'; el.appendChild(note); }
      } catch (e) { if (el) el.innerHTML = '<div class="xr-loading">Propagación no disponible</div>'; }
    });
  }

  window._xrayClose = close;
  window._xrayShock = function (id) { window._xrayJump(id); setTimeout(function () { if (typeof window.activateStress === 'function') window.activateStress(id); }, 220); };
  window._xrayTKG = function (id) { close(); if (typeof window.switchTab === 'function') window.switchTab('tkg'); setTimeout(function () { if (window.__tkgOpenObj) window.__tkgOpenObj(id); }, 200); };
  window.openXRay = function (id) { render(id); };

  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });
})();
