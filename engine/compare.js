/* ============================================================================
   engine/compare.js — COMPARAR DOS EMPRESAS lado a lado (decidir entre 2)
   Overlay NEXUS: elige dos empresas y ve enfrentadas su NRS (término a
   término), sector, país, margen, precio en vivo, grado de conexión, señal
   de compra/venta y dependencias. El ganador de cada fila se resalta.
   Se abre con window.openCompare(idA, idB) o el botón "⇄ Comparar" del X-Ray.
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

  function ensureStyles() {
    if (document.getElementById('cmp-styles')) return;
    var css = ''
      + '#cmp-ov{position:fixed;inset:0;z-index:6100;display:none;align-items:center;justify-content:center;'
      + 'background:rgba(3,6,12,.72);backdrop-filter:blur(4px);font-family:Inter,system-ui,sans-serif}'
      + '#cmp-ov.show{display:flex;animation:cmpF .18s ease}@keyframes cmpF{from{opacity:0}to{opacity:1}}'
      + '#cmp{width:min(620px,95vw);max-height:90vh;overflow-y:auto;border-radius:16px;color:#E8EDFB;'
      + 'background:radial-gradient(700px 400px at 60% -8%,#0e1626,#06090F);border:1px solid rgba(122,158,255,.22);'
      + 'box-shadow:0 30px 80px rgba(0,0,0,.6);padding:18px 20px 16px}'
      + '#cmp .hd{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px}'
      + '#cmp .eb{font-family:"JetBrains Mono",monospace;font-size:10.5px;letter-spacing:.2em;text-transform:uppercase;color:#00E0FF}'
      + '#cmp .x{cursor:pointer;color:#7C87A3;font-size:17px}'
      + '#cmp .heads{display:grid;grid-template-columns:1fr 34px 1fr;gap:8px;align-items:end;margin-bottom:10px}'
      + '#cmp select{width:100%;background:rgba(21,28,45,.85);color:#E8EDFB;border:1px solid rgba(122,158,255,.25);border-radius:8px;padding:8px;font-family:inherit;font-size:12.5px}'
      + '#cmp .vs{text-align:center;font-family:"JetBrains Mono",monospace;font-size:11px;color:#5c657f}'
      + '#cmp .cdot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px;vertical-align:middle}'
      + '.cmp-row{display:grid;grid-template-columns:1fr 96px 1fr;gap:8px;align-items:center;padding:8px 0;border-bottom:1px solid rgba(122,158,255,.08)}'
      + '.cmp-row .lab{text-align:center;font-size:9.5px;letter-spacing:.06em;text-transform:uppercase;color:#7C87A3}'
      + '.cmp-row .va{font-family:"JetBrains Mono",monospace;font-size:14px;text-align:right;font-weight:600}'
      + '.cmp-row .vb{font-family:"JetBrains Mono",monospace;font-size:14px;text-align:left;font-weight:600}'
      + '.cmp-row .win{color:#2BE38B}.cmp-row .lose{color:#8791AC}'
      + '.cmp-nrs{margin-top:12px}.cmp-nrs .t{font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:#7C87A3;margin-bottom:8px}'
      + '.cmp-nb{display:grid;grid-template-columns:1fr 84px 1fr;gap:8px;align-items:center;font-size:10.5px;color:#9BA6C4;margin:4px 0}'
      + '.cmp-bar{height:6px;border-radius:4px;background:rgba(21,28,45,.9);overflow:hidden;position:relative}'
      + '.cmp-bar i{position:absolute;top:0;height:100%}'
      + '#cmp .foot{font-size:10.5px;color:#5c657f;margin-top:12px;text-align:center}';
    var st = document.createElement('style'); st.id = 'cmp-styles'; st.textContent = css;
    document.head.appendChild(st);
  }

  var A = 'TSMC', B = 'Nvidia';

  function metrics(id) {
    var n = window.NODE_BY_ID[id] || {};
    var meta = (window.NODE_META || {})[id] || {};
    var nrs = window.computeNRS ? window.computeNRS(id) : 50;
    var bd = window.computeNRSBreakdown ? window.computeNRSBreakdown(id) : null;
    var deg = 0; (window.LINKS || []).forEach(function (l) { if (lid(l.source) === id || lid(l.target) === id) deg++; });
    var st = window.KhipuState && window.KhipuState.baseline ? window.KhipuState.baseline(id) : null;
    return { n: n, meta: meta, nrs: nrs, bd: bd, deg: deg,
      margin: n.margin != null ? Math.round(n.margin * 100) : null,
      mktcap: meta.mktcap_b || null, country: n.country || '—',
      senal: st ? st /*placeholder*/ : null };
  }

  // fila comparativa: lowerBetter=true si menor valor = mejor (ej. riesgo)
  function row(lab, a, b, fmt, lowerBetter) {
    var av = a, bv = b, aWin = false, bWin = false;
    if (typeof a === 'number' && typeof b === 'number') {
      if (a !== b) { var aBetter = lowerBetter ? a < b : a > b; aWin = aBetter; bWin = !aBetter; }
    }
    var f = fmt || function (v) { return v == null ? '—' : v; };
    return '<div class="cmp-row"><span class="va ' + (aWin ? 'win' : bWin ? 'lose' : '') + '">' + f(a) + '</span>' +
      '<span class="lab">' + lab + '</span>' +
      '<span class="vb ' + (bWin ? 'win' : aWin ? 'lose' : '') + '">' + f(b) + '</span></div>';
  }

  function render() {
    ensureStyles();
    var ov = document.getElementById('cmp-ov');
    if (!ov) {
      ov = document.createElement('div'); ov.id = 'cmp-ov'; ov.innerHTML = '<div id="cmp"></div>';
      ov.addEventListener('click', function (e) { if (e.target === ov) close(); });
      document.body.appendChild(ov);
    }
    var ids = (window.NODES || []).map(function (n) { return n.id; }).sort(function (x, y) { return nm(x).localeCompare(nm(y)); });
    var opts = function (sel) { return ids.map(function (id) { return '<option value="' + esc(id) + '"' + (id === sel ? ' selected' : '') + '>' + esc(nm(id)) + '</option>'; }).join(''); };
    var ma = metrics(A), mb = metrics(B);
    var pill = function (id) { return '<span class="cdot" style="background:' + secColor(id) + '"></span>'; };

    var nrsRows = '';
    if (ma.bd && mb.bd) {
      nrsRows = '<div class="cmp-nrs"><div class="t">Por qué su riesgo — término a término</div>' +
        ma.bd.terms.map(function (ta, k) {
          var tb = mb.bd.terms[k];
          var pa = Math.round(ta.val / ta.max * 100), pb = Math.round(tb.val / tb.max * 100);
          return '<div class="cmp-nb"><span style="text-align:right">' + ta.val + '</span>' +
            '<div><div style="font-size:8.5px;text-align:center;color:#5c657f;margin-bottom:2px">' + ta.key + '</div>' +
            '<div class="cmp-bar"><i style="right:50%;width:' + (pa / 2) + '%;background:' + (ta.hot ? '#FF4D6A' : '#4D7CFE') + '"></i>' +
            '<i style="left:50%;width:' + (pb / 2) + '%;background:' + (tb.hot ? '#FF4D6A' : '#4D7CFE') + '"></i></div></div>' +
            '<span>' + tb.val + '</span></div>';
        }).join('') + '</div>';
    }

    document.getElementById('cmp').innerHTML =
      '<div class="hd"><span class="eb">Comparar empresas</span><span class="x" onclick="window._cmpClose()">✕</span></div>' +
      '<div class="heads"><select id="cmp-a">' + opts(A) + '</select><div class="vs">vs</div><select id="cmp-b">' + opts(B) + '</select></div>' +
      row('Sector', pill(A) + (window.SECTORS9 ? (window.SECTORS9[(window.CAT_TO_SECTOR || {})[ma.n.cat]] || {}).label || '' : ''),
                    pill(B) + (window.SECTORS9 ? (window.SECTORS9[(window.CAT_TO_SECTOR || {})[mb.n.cat]] || {}).label || '' : ''), null) +
      row('País', ma.country, mb.country, null) +
      row('Riesgo NRS', ma.nrs, mb.nrs, function (v) { return v + '/100'; }, true) +
      row('Margen', ma.margin, mb.margin, function (v) { return v == null ? '—' : v + '%'; }, false) +
      row('Mkt cap', ma.mktcap, mb.mktcap, function (v) { return v == null ? 'Priv.' : (v >= 1000 ? '$' + (v / 1000).toFixed(1) + 'T' : '$' + v + 'B'); }, false) +
      row('Conexiones', ma.deg, mb.deg, null, false) +
      nrsRows +
      '<div class="foot">Verde = mejor en esa fila (menor riesgo, mayor margen…). Barra NRS: izquierda = ' + esc(nm(A)) + ', derecha = ' + esc(nm(B)) + '.</div>';

    document.getElementById('cmp-a').onchange = function (e) { A = e.target.value; render(); };
    document.getElementById('cmp-b').onchange = function (e) { B = e.target.value; render(); };
    ov.classList.add('show');
  }

  function close() { var ov = document.getElementById('cmp-ov'); if (ov) ov.classList.remove('show'); }
  window._cmpClose = close;
  window.openCompare = function (a, b) {
    if (a && window.NODE_BY_ID[a]) A = a;
    if (b && window.NODE_BY_ID[b]) B = b;
    else if (a && A === a) { B = A === 'Nvidia' ? 'TSMC' : 'Nvidia'; }  // segundo por defecto
    render();
  };
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });
})();
