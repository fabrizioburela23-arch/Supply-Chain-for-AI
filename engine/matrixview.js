/* ============================================================================
   engine/matrixview.js — LAS 9 MATRICES dentro de la app (pestaña Análisis)
   Calcula en el navegador las 9 matrices de relación desde window.LINKS y las
   dibuja: small-multiples (patrón de dispersión de cada tipo) + un mapa de
   calor grande de las empresas más conectadas, con tooltip al pasar el cursor.
   Piel NEXUS. Se rellena #an-matrix cuando se abre Análisis (renderAnalysis).
   ============================================================================ */
(function () {
  'use strict';

  var REL = ['supply', 'cloud', 'fab', 'license', 'partner', 'invest', 'deploy', 'owns', 'ppa'];
  var SECTOR_ORDER = ['equipos', 'fabricacion', 'diseno', 'cloud_ia', 'infra', 'energia', 'espacio', 'defensa', 'robotica'];
  function lid(v) { return (typeof v === 'object' && v !== null) ? v.id : v; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function nm(id) { var n = window.NODE_BY_ID && window.NODE_BY_ID[id]; return n ? n.label : id; }
  function secOf(id) { var n = window.NODE_BY_ID && window.NODE_BY_ID[id]; return (window.CAT_TO_SECTOR || {})[n ? n.cat : ''] || 'cloud_ia'; }
  function secColor(s) { var S = (window.SECTORS9 || {})[s]; return S ? S.color : '#00E0FF'; }
  function secLabel(s) { var S = (window.SECTORS9 || {})[s]; return S ? S.label : s; }

  var built = null, curRT = 'supply';

  function build() {
    var NODES = window.NODES || [], LINKS = window.LINKS || [];
    if (!NODES.length) return null;
    var deg = {}; NODES.forEach(function (n) { deg[n.id] = 0; });
    LINKS.forEach(function (l) { deg[lid(l.source)] = (deg[lid(l.source)] || 0) + 1; deg[lid(l.target)] = (deg[lid(l.target)] || 0) + 1; });
    // orden completo por sector→grado (para sparsity)
    var bySec = {}; NODES.forEach(function (n) { (bySec[secOf(n.id)] = bySec[secOf(n.id)] || []).push(n.id); });
    Object.keys(bySec).forEach(function (s) { bySec[s].sort(function (a, b) { return deg[b] - deg[a]; }); });
    var fullOrder = []; SECTOR_ORDER.forEach(function (s) { (bySec[s] || []).forEach(function (id) { fullOrder.push(id); }); });
    var fullIdx = {}; fullOrder.forEach(function (id, i) { fullIdx[id] = i; });
    // curado: top 6 por sector
    var CUR = []; SECTOR_ORDER.forEach(function (s) { (bySec[s] || []).slice(0, 6).forEach(function (id) { CUR.push(id); }); });
    var curIdx = {}; CUR.forEach(function (id, i) { curIdx[id] = i; });
    var sparsity = {}, curMat = {}, counts = {};
    REL.forEach(function (r) { sparsity[r] = []; curMat[r] = []; counts[r] = 0; });
    LINKS.forEach(function (l) {
      var s = lid(l.source), t = lid(l.target), r = l.type; if (!sparsity[r]) return;
      counts[r]++;
      if (fullIdx[s] != null && fullIdx[t] != null) sparsity[r].push([fullIdx[s], fullIdx[t]]);
      if (curIdx[s] != null && curIdx[t] != null) curMat[r].push([curIdx[s], curIdx[t], l.w || 2, (l.rel || '').slice(0, 60)]);
    });
    return { N: fullOrder.length, fullSec: fullOrder.map(secOf), sparsity: sparsity, counts: counts,
      CUR: CUR, curSec: CUR.map(secOf), curMat: curMat };
  }

  function ensureStyles() {
    if (document.getElementById('mxv-styles')) return;
    var css = ''
      + '#an-matrix .mxv-h{font-size:15px;font-weight:600;margin:0 0 3px;display:flex;align-items:center;gap:8px}'
      + '#an-matrix .mxv-s{font-size:12.5px;color:var(--ink-3,#8791AC);margin:0 0 14px}'
      + '#an-matrix .mxv-g9{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:9px;margin-bottom:18px}'
      + '#an-matrix .mxv-mm{border:1px solid rgba(122,158,255,.14);border-radius:10px;padding:9px;background:rgba(15,21,34,.4);cursor:pointer;transition:border-color .12s,transform .1s}'
      + '#an-matrix .mxv-mm:hover{border-color:#00E0FF;transform:translateY(-2px)}#an-matrix .mxv-mm.on{border-color:#00E0FF;box-shadow:0 0 0 1px #00E0FF inset}'
      + '#an-matrix .mxv-mm canvas{width:100%;height:auto;display:block;border-radius:5px;background:#070b13;margin-top:6px}'
      + '#an-matrix .mxv-mm .t{display:flex;justify-content:space-between;font-size:11.5px;font-weight:600;text-transform:capitalize}'
      + '#an-matrix .mxv-mm .c{font-family:"JetBrains Mono",monospace;font-size:10.5px;color:#00E0FF}'
      + '#an-matrix .mxv-big{border:1px solid rgba(122,158,255,.16);border-radius:12px;background:rgba(15,21,34,.4);padding:14px 14px 8px}'
      + '#an-matrix .mxv-bh{font-size:13px;font-weight:600;margin-bottom:10px}#an-matrix .mxv-bh .rt{color:#00E0FF;text-transform:capitalize}'
      + '#an-matrix .mxv-scroll{overflow-x:auto}#an-matrix #mxv-hm{display:block;cursor:crosshair}'
      + '#an-matrix .mxv-leg{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}'
      + '#an-matrix .mxv-leg span{display:inline-flex;align-items:center;gap:5px;font-size:10.5px;color:var(--ink-3,#8791AC)}'
      + '#an-matrix .mxv-leg i{width:9px;height:9px;border-radius:2px}'
      + '#mxv-tip{position:fixed;pointer-events:none;z-index:50;background:#0b1220;border:1px solid #00E0FF;border-radius:8px;padding:7px 10px;font-size:11px;max-width:230px;color:#E8EDFB;display:none;line-height:1.4}'
      + '#mxv-tip .a{color:#00E0FF;font-weight:600}#mxv-tip .b{color:#2BE38B;font-weight:600}#mxv-tip .r{color:#8791AC;font-size:10px;margin-top:2px}';
    var st = document.createElement('style'); st.id = 'mxv-styles'; st.textContent = css;
    document.head.appendChild(st);
  }

  function drawSparse(cv, d, rt) {
    var px = 240; cv.width = px; cv.height = px; var ctx = cv.getContext('2d');
    var n = d.N, cell = px / n;
    var acc = 0; ctx.strokeStyle = 'rgba(122,158,255,.05)';
    SECTOR_ORDER.forEach(function (s) { var cnt = d.fullSec.filter(function (x) { return x === s; }).length; acc += cnt; var p = acc * cell; ctx.beginPath(); ctx.moveTo(p, 0); ctx.lineTo(p, px); ctx.moveTo(0, p); ctx.lineTo(px, p); ctx.stroke(); });
    (d.sparsity[rt] || []).forEach(function (e) { ctx.fillStyle = secColor(d.fullSec[e[0]]); ctx.globalAlpha = .9; ctx.fillRect(e[1] * cell, e[0] * cell, Math.max(1.3, cell), Math.max(1.3, cell)); });
    ctx.globalAlpha = 1;
  }

  var bigCells = {}, M = 92, CELL = 11, DIM = 0;
  function drawBig(d, rt) {
    curRT = rt;
    var hm = document.getElementById('mxv-hm'); if (!hm) return;
    var CN = d.CUR.length; DIM = M + CN * CELL + 4;
    hm.width = DIM; hm.height = DIM; hm.style.width = DIM + 'px';
    var ctx = hm.getContext('2d'); ctx.clearRect(0, 0, DIM, DIM);
    document.querySelector('#mxv-brt') && (document.getElementById('mxv-brt').textContent = rt);
    document.querySelector('#mxv-bn') && (document.getElementById('mxv-bn').textContent = (d.curMat[rt] || []).length);
    document.querySelectorAll('#an-matrix .mxv-mm').forEach(function (m) { m.classList.toggle('on', m.dataset.rt === rt); });
    ctx.strokeStyle = 'rgba(122,158,255,.06)';
    for (var k = 0; k <= CN; k++) { var p = M + k * CELL; ctx.beginPath(); ctx.moveTo(p, M); ctx.lineTo(p, M + CN * CELL); ctx.moveTo(M, p); ctx.lineTo(M + CN * CELL, p); ctx.stroke(); }
    ctx.strokeStyle = 'rgba(122,158,255,.12)'; ctx.beginPath(); ctx.moveTo(M, M); ctx.lineTo(M + CN * CELL, M + CN * CELL); ctx.stroke();
    bigCells = {};
    (d.curMat[rt] || []).forEach(function (e) {
      var i = e[0], j = e[1], w = e[2]; var t = Math.min(1, (w - 1) / 5);
      ctx.fillStyle = secColor(d.curSec[i]); ctx.globalAlpha = .3 + t * .7;
      ctx.fillRect(M + j * CELL + 1, M + i * CELL + 1, CELL - 2, CELL - 2); ctx.globalAlpha = 1;
      bigCells[i + '_' + j] = { i: i, j: j, w: w, rel: e[3] };
    });
    ctx.font = '9px sans-serif'; var acc = 0;
    SECTOR_ORDER.forEach(function (s) {
      var cnt = d.curSec.filter(function (x) { return x === s; }).length; if (!cnt) return;
      var mid = M + (acc + cnt / 2) * CELL; ctx.save(); ctx.translate(M - 5, mid); ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
      ctx.fillStyle = secColor(s); ctx.fillText(secLabel(s).slice(0, 9), 0, 0); ctx.restore(); acc += cnt;
    });
  }

  window.renderMatrixView = function () {
    var host = document.getElementById('an-matrix'); if (!host) return;
    built = build(); if (!built) { host.innerHTML = ''; return; }
    ensureStyles();
    host.innerHTML =
      '<div class="mxv-h">◱ Las 9 matrices de relación</div>' +
      '<p class="mxv-s">Cada tipo de vínculo es una matriz N×N: fila <b>provee</b> a columna, ordenadas por sector. Haz clic en una para verla en detalle.</p>' +
      '<div class="mxv-g9" id="mxv-g9"></div>' +
      '<div class="mxv-big"><div class="mxv-bh">Matriz <span class="rt" id="mxv-brt"></span> · <span id="mxv-bn" style="font-family:JetBrains Mono,monospace;color:#8791AC"></span> vínculos · pasa el cursor</div>' +
      '<div class="mxv-scroll"><canvas id="mxv-hm"></canvas></div>' +
      '<div class="mxv-leg" id="mxv-leg"></div></div>';
    var g9 = document.getElementById('mxv-g9');
    REL.forEach(function (r) {
      var div = document.createElement('div'); div.className = 'mxv-mm'; div.dataset.rt = r;
      div.innerHTML = '<div class="t"><span>' + r + '</span><span class="c">' + built.counts[r] + '</span></div>';
      var cv = document.createElement('canvas'); div.appendChild(cv); g9.appendChild(div);
      drawSparse(cv, built, r);
      div.onclick = function () { drawBig(built, r); };
    });
    document.getElementById('mxv-leg').innerHTML = SECTOR_ORDER.filter(function (s) { return built.curSec.indexOf(s) >= 0; })
      .map(function (s) { return '<span><i style="background:' + secColor(s) + '"></i>' + secLabel(s) + '</span>'; }).join('');
    // tooltip
    var hm = document.getElementById('mxv-hm'), tip = document.getElementById('mxv-tip');
    if (!tip) { tip = document.createElement('div'); tip.id = 'mxv-tip'; document.body.appendChild(tip); }
    hm.onmousemove = function (e) {
      var r = hm.getBoundingClientRect(), x = (e.clientX - r.left) * (DIM / r.width), y = (e.clientY - r.top) * (DIM / r.height);
      var j = Math.floor((x - M) / CELL), i = Math.floor((y - M) / CELL), hit = bigCells[i + '_' + j];
      if (hit && i >= 0 && j >= 0) {
        tip.style.display = 'block'; tip.style.left = Math.min(e.clientX + 14, innerWidth - 240) + 'px'; tip.style.top = (e.clientY + 14) + 'px';
        tip.innerHTML = '<div><span class="a">' + esc(nm(built.CUR[hit.i])) + '</span> → <span class="b">' + esc(nm(built.CUR[hit.j])) + '</span></div>' +
          '<div class="r">' + curRT + ' · peso ' + hit.w + (hit.rel ? ' · ' + esc(hit.rel) : '') + '</div>';
      } else tip.style.display = 'none';
    };
    hm.onmouseleave = function () { tip.style.display = 'none'; };
    drawBig(built, 'supply');
  };
})();
