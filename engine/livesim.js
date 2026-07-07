/* ============================================================================
   engine/livesim.js — SIMULACIÓN EN VIVO v2 (deslizador → el mapa reacciona)
   El payoff del motor de estados (engine/statematrix.js), edición WOW:
   - los 407 nodos Y las conexiones se tiñen en tiempo real (~7ms → 60 fps)
   - capital de mercado expuesto en $, impacto en TU cartera, afectadas
   - desglose por macro-sector (barras)
   - GANADORES: los rivales del caído que capturan su demanda (verde ↑)
   - ▶ la cascada se reproduce como película, salto a salto por la red
   Piel NEXUS. Botón "◉ En vivo" en el mapa. rAF con fallback setTimeout
   cuando la pestaña está oculta (patrón voice.js).
   ============================================================================ */
(function () {
  'use strict';

  var SCENARIOS = [
    { id: 'taiwan',  label: 'Conflicto en Taiwán',        shock: ['TSMC'] },
    { id: 'hbm',     label: 'Escasez de memoria HBM',      shock: ['SKHynix', 'Micron', 'Samsung'] },
    { id: 'euv',     label: 'Sanción a equipos EUV',       shock: ['ASML'] },
    { id: 'cloud',   label: 'Caída de un hyperscaler',     shock: ['Amazon'] },
    { id: 'chipban', label: 'Veto total de chips a China', shock: ['Nvidia', 'AMD'] },
  ];

  var active = false, shockIds = ['TSMC'], severity = 100, factors = [], raf = 0;
  var playing = false, playTimer = 0, lastResult = null;

  function ensureStyles() {
    if (document.getElementById('livesim-styles')) return;
    var css = ''
      + '#ls-btn{position:absolute;left:12px;bottom:52px;z-index:20;display:flex;align-items:center;gap:6px;'
      + 'padding:7px 13px;border-radius:9px;cursor:pointer;font-family:Inter,system-ui,sans-serif;font-size:12px;font-weight:600;'
      + 'background:rgba(15,21,34,.85);border:1px solid rgba(0,224,255,.35);color:#00E0FF;backdrop-filter:blur(6px)}'
      + '#ls-btn:hover{border-color:#00E0FF;box-shadow:0 0 12px rgba(0,224,255,.3)}'
      + '#ls-btn.on{background:#00E0FF;color:#03141C}'
      + '#ls-panel{position:absolute;left:12px;bottom:96px;z-index:21;width:322px;display:none;flex-direction:column;gap:10px;'
      + 'padding:15px 16px;border-radius:13px;background:radial-gradient(420px 260px at 60% -10%,#0d1424,#06090F);'
      + 'border:1px solid rgba(122,158,255,.2);box-shadow:0 18px 50px rgba(0,0,0,.5);color:#E8EDFB;'
      + 'font-family:Inter,system-ui,sans-serif;max-height:calc(100% - 150px);overflow-y:auto}'
      + '#ls-panel.show{display:flex}'
      + '#ls-panel h4{margin:0;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#7C87A3;font-weight:600;display:flex;justify-content:space-between;align-items:center}'
      + '#ls-panel .lsx{cursor:pointer;color:#7C87A3;font-size:15px;line-height:1}'
      + '#ls-scn{display:flex;flex-wrap:wrap;gap:5px}'
      + '.ls-chip{font-size:11px;padding:4px 9px;border-radius:20px;cursor:pointer;border:1px solid rgba(122,158,255,.2);'
      + 'background:rgba(21,28,45,.6);color:#c8d0e0;transition:all .12s}'
      + '.ls-chip:hover{border-color:rgba(0,224,255,.5)}.ls-chip.on{background:rgba(0,224,255,.15);border-color:#00E0FF;color:#00E0FF}'
      + '#ls-panel .lsrow{font-size:11px;color:#9BA6C4;display:flex;justify-content:space-between;align-items:center;font-family:"JetBrains Mono",monospace}'
      + '#ls-sev{width:100%;accent-color:#00E0FF;cursor:pointer}'
      + '#ls-stats{display:grid;grid-template-columns:1fr 1fr 1fr;gap:7px;text-align:center}'
      + '.ls-cell{border:1px solid rgba(122,158,255,.12);border-radius:9px;padding:8px 3px;background:rgba(21,28,45,.6)}'
      + '.ls-cell b{display:block;font-family:"JetBrains Mono",monospace;font-size:15px;font-weight:600;color:#FF4D6A}'
      + '.ls-cell span{font-size:8.5px;color:#7C87A3;text-transform:uppercase;letter-spacing:.05em;display:block;margin-top:2px}'
      + '#ls-sect{display:flex;flex-direction:column;gap:4px}'
      + '.ls-sbar{display:flex;align-items:center;gap:7px;font-size:10.5px;color:#9BA6C4}'
      + '.ls-sbar .sb{flex:1;height:5px;border-radius:4px;background:rgba(122,158,255,.08);overflow:hidden}'
      + '.ls-sbar .sb i{display:block;height:100%;border-radius:4px}'
      + '.ls-sbar .sp{font-family:"JetBrains Mono",monospace;font-size:9.5px;width:32px;text-align:right}'
      + '#ls-cols{display:grid;grid-template-columns:1fr 1fr;gap:10px}'
      + '#ls-cols .lsh{font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:#7C87A3;margin-bottom:4px}'
      + '.ls-victim,.ls-winner{display:flex;align-items:center;gap:6px;font-size:10.5px;cursor:pointer;padding:2px 0}'
      + '.ls-victim:hover span:nth-child(1),.ls-winner:hover span:nth-child(1){color:#00E0FF}'
      + '.ls-victim .p{font-family:"JetBrains Mono",monospace;font-size:9.5px;color:#FF4D6A;margin-left:auto}'
      + '.ls-winner .p{font-family:"JetBrains Mono",monospace;font-size:9.5px;color:#2BE38B;margin-left:auto}'
      + '.ls-victim span:first-child,.ls-winner span:first-child{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:100px}'
      + '#ls-play{display:flex;align-items:center;gap:8px}'
      + '#ls-play button{flex:1;padding:7px 0;border-radius:8px;cursor:pointer;font-family:Inter,sans-serif;font-size:11.5px;font-weight:600;'
      + 'background:rgba(0,224,255,.12);border:1px solid rgba(0,224,255,.4);color:#00E0FF;transition:all .12s}'
      + '#ls-play button:hover{background:rgba(0,224,255,.22)}'
      + '#ls-hop{font-family:"JetBrains Mono",monospace;font-size:10px;color:#7C87A3;min-width:52px;text-align:right}';
    var st = document.createElement('style'); st.id = 'livesim-styles'; st.textContent = css;
    document.head.appendChild(st);
  }

  function nm(id) { var n = window.NODE_BY_ID && window.NODE_BY_ID[id]; return n ? n.label : id; }
  function fmtB(v) { return v >= 1000 ? '$' + (v / 1000).toFixed(1) + 'T' : '$' + Math.round(v) + 'B'; }

  function paint(impactMap) {
    if (window._liveRecolorByImpact) window._liveRecolorByImpact(impactMap);
    if (window._liveTintLinks) window._liveTintLinks(impactMap);
  }

  // ── GANADORES: rivales (misma categoría) de los golpeados, poco afectados,
  // capturan la demanda que el caído deja huérfana ──
  function computeWinners(impact) {
    var damaged = [];
    impact.forEach(function (v, id) { if (v >= 40) damaged.push({ id: id, v: v }); });
    var gains = new Map();
    damaged.forEach(function (d) {
      var dn = window.NODE_BY_ID[d.id]; if (!dn) return;
      (window.NODES || []).forEach(function (n) {
        if (n.id === d.id || n.cat !== dn.cat) return;
        if ((impact.get(n.id) || 0) > 15) return;              // también golpeado → no gana
        var g = (gains.get(n.id) || 0) + d.v / 100;
        gains.set(n.id, g);
      });
    });
    var arr = [];
    gains.forEach(function (g, id) { arr.push({ id: id, up: Math.min(45, Math.round(g * 14)) }); });
    return arr.filter(function (x) { return x.up >= 4; })
      .sort(function (a, b) { return b.up - a.up; }).slice(0, 5);
  }

  function run() {
    if (!window.KhipuState) return;
    var shocks = {};
    shockIds.forEach(function (id) { shocks[id] = { salud: 1 - severity / 100 }; });
    var r = window.KhipuState.simulate(shocks, factors, 8, 0.6, true);
    lastResult = r;
    paint(r.impact);

    // víctimas / stats
    var arr = [], capExp = 0, sectorDmg = {}, pos = (window.MKT && window.MKT.pos) || {};
    var portTotal = 0, portHit = 0;
    r.impact.forEach(function (v, id) {
      if (shockIds.indexOf(id) < 0) arr.push({ id: id, v: v });
      var meta = (window.NODE_META || {})[id];
      if (meta && isFinite(+meta.mktcap_b)) capExp += (+meta.mktcap_b) * v / 100;
      var n = window.NODE_BY_ID[id];
      if (n && window.CAT_TO_SECTOR) {
        var s = window.CAT_TO_SECTOR[n.cat] || 'cloud_ia';
        sectorDmg[s] = (sectorDmg[s] || 0) + v;
      }
    });
    Object.keys(pos).forEach(function (id) { portTotal++; portHit += (r.impact.get(id) || 0); });
    arr.sort(function (a, b) { return b.v - a.v; });
    var winners = computeWinners(r.impact);

    var stats = document.getElementById('ls-stats');
    if (stats) stats.innerHTML =
      '<div class="ls-cell"><b>' + arr.length + '</b><span>afectadas</span></div>' +
      '<div class="ls-cell"><b>' + fmtB(capExp) + '</b><span>cap expuesta</span></div>' +
      '<div class="ls-cell"><b>' + (portTotal ? '−' + Math.round(portHit / portTotal) + '%' : '—') + '</b><span>tu cartera</span></div>';

    var sect = document.getElementById('ls-sect');
    if (sect && window.SECTORS9) {
      var top3 = Object.keys(sectorDmg).sort(function (a, b) { return sectorDmg[b] - sectorDmg[a]; }).slice(0, 3);
      var mx = sectorDmg[top3[0]] || 1;
      sect.innerHTML = top3.map(function (s) {
        var S = window.SECTORS9[s] || {};
        return '<div class="ls-sbar"><span style="width:88px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + (S.label || s) + '</span>' +
          '<span class="sb"><i style="width:' + Math.round(sectorDmg[s] / mx * 100) + '%;background:' + (S.color || '#FF4D6A') + '"></i></span>' +
          '<span class="sp">' + Math.round(sectorDmg[s] / 100 * 10) / 10 + '</span></div>';
      }).join('');
    }

    var vict = document.getElementById('ls-vict');
    if (vict) vict.innerHTML = arr.slice(0, 6).map(function (x) {
      return '<div class="ls-victim" onclick="window.jumpTo&&window.jumpTo(\'' + x.id + '\')">' +
        '<span>' + nm(x.id) + '</span><span class="p">−' + Math.round(x.v) + '%</span></div>';
    }).join('') || '<div style="font-size:10px;color:#7C87A3">—</div>';

    var win = document.getElementById('ls-win');
    if (win) win.innerHTML = winners.map(function (x) {
      return '<div class="ls-winner" onclick="window.jumpTo&&window.jumpTo(\'' + x.id + '\')">' +
        '<span>' + nm(x.id) + '</span><span class="p">↑' + x.up + '%</span></div>';
    }).join('') || '<div style="font-size:10px;color:#7C87A3">sin ganadores claros</div>';

    var read = document.getElementById('ls-read');
    if (read) read.innerHTML = 'Fuente: <b style="color:#00E0FF">' + shockIds.map(nm).join(', ') + '</b> al ' + severity + '%';
  }

  function schedule() {
    if (raf) { cancelAnimationFrame(raf); clearTimeout(raf); }
    raf = (typeof document !== 'undefined' && document.hidden)
      ? setTimeout(run, 16) : requestAnimationFrame(run);
  }

  // ── película de la cascada: reproduce los frames salto a salto ──
  function playCascade() {
    if (!lastResult || !lastResult.frames || playing) { run(); if (!lastResult || !lastResult.frames) return; }
    stopCascade();
    playing = true;
    var frames = lastResult.frames, k = 0;
    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var stepMs = reduce ? 0 : 420;
    var hopEl = document.getElementById('ls-hop');
    var btn = document.getElementById('ls-playbtn');
    if (btn) btn.textContent = '■ Detener';
    if (reduce) { paint(frames[frames.length - 1]); stopCascade(); return; }
    function step() {
      if (!playing) return;
      paint(frames[Math.min(k, frames.length - 1)]);
      if (hopEl) hopEl.textContent = 'salto ' + Math.min(k, frames.length - 1) + '/' + (frames.length - 1);
      k++;
      if (k >= frames.length + 1) { stopCascade(); return; }
      playTimer = setTimeout(step, stepMs);
    }
    step();
  }
  function stopCascade() {
    playing = false;
    if (playTimer) clearTimeout(playTimer);
    var btn = document.getElementById('ls-playbtn');
    if (btn) btn.textContent = '▶ Reproducir cascada';
    var hopEl = document.getElementById('ls-hop');
    if (hopEl && lastResult && lastResult.frames) hopEl.textContent = 'salto ' + (lastResult.frames.length - 1) + '/' + (lastResult.frames.length - 1);
    if (lastResult) paint(lastResult.impact);
  }

  function setScenario(scn) {
    shockIds = scn.shock.filter(function (id) { return window.NODE_BY_ID && window.NODE_BY_ID[id]; });
    if (!shockIds.length) shockIds = ['TSMC'];
    document.querySelectorAll('#ls-scn .ls-chip').forEach(function (c) { c.classList.toggle('on', c.dataset.id === scn.id); });
    schedule();
  }

  function toggle() {
    active = !active;
    var btn = document.getElementById('ls-btn'), panel = document.getElementById('ls-panel');
    btn.classList.toggle('on', active);
    panel.classList.toggle('show', active);
    btn.innerHTML = active ? '<span>◉</span> En vivo · ON' : '<span>◉</span> En vivo';
    if (active) {
      window.KhipuState && window.KhipuState.build();
      var sel = window._liveSelectedNode && window._liveSelectedNode();
      if (sel) { shockIds = [sel]; document.querySelectorAll('#ls-scn .ls-chip').forEach(function (c) { c.classList.remove('on'); }); }
      schedule();
    } else {
      stopCascade();
      if (window._liveResetColors) window._liveResetColors();
    }
  }

  function mount() {
    var wrap = document.querySelector('.graph-wrap');
    if (!wrap || document.getElementById('ls-btn')) return;
    ensureStyles();
    var btn = document.createElement('div');
    btn.id = 'ls-btn'; btn.innerHTML = '<span>◉</span> En vivo';
    btn.title = 'Simulación en vivo — arrastra la severidad y ve reaccionar la red';
    btn.onclick = toggle;
    var panel = document.createElement('div');
    panel.id = 'ls-panel';
    panel.innerHTML = ''
      + '<h4>Simulación en vivo <span class="lsx" onclick="window._lsToggle()">✕</span></h4>'
      + '<div id="ls-scn">' + SCENARIOS.map(function (s) {
          return '<span class="ls-chip" data-id="' + s.id + '">' + s.label + '</span>';
        }).join('') + '</div>'
      + '<div class="lsrow"><span>Severidad</span><span id="ls-sevv">100%</span></div>'
      + '<input type="range" id="ls-sev" min="0" max="100" value="100">'
      + '<div id="ls-read" style="font-size:11px;color:#9BA6C4"></div>'
      + '<div id="ls-stats"></div>'
      + '<div id="ls-sect"></div>'
      + '<div id="ls-cols">'
      +   '<div><div class="lsh">Más golpeadas</div><div id="ls-vict"></div></div>'
      +   '<div><div class="lsh" style="color:#2BE38B">Ganadores ↑</div><div id="ls-win"></div></div>'
      + '</div>'
      + '<div id="ls-play"><button id="ls-playbtn">▶ Reproducir cascada</button><span id="ls-hop"></span></div>';
    wrap.appendChild(btn); wrap.appendChild(panel);
    panel.querySelectorAll('#ls-scn .ls-chip').forEach(function (c) {
      c.onclick = function () { var scn = SCENARIOS.find(function (s) { return s.id === c.dataset.id; }); if (scn) setScenario(scn); };
    });
    var sev = panel.querySelector('#ls-sev');
    sev.oninput = function () { severity = +sev.value; document.getElementById('ls-sevv').textContent = severity + '%'; schedule(); };
    panel.querySelector('#ls-playbtn').onclick = function () { playing ? stopCascade() : playCascade(); };
  }

  window._lsToggle = toggle;
  if (document.querySelector('.graph-wrap')) mount();
  else document.addEventListener('DOMContentLoaded', mount);
  setTimeout(mount, 1500);
})();
