/* ============================================================================
   engine/livesim.js — SIMULACIÓN EN VIVO v3 (abierta, no cerrada)
   Constructor de escenarios: eliges el TIPO de golpe (corte↓, demanda↑,
   precio, sanción) y el OBJETIVO (preset, sector entero, país entero, o las
   empresas que tú elijas). Los nodos y conexiones reaccionan en tiempo real
   (~7ms → 60fps): rojo=daño, verde=auge. Stats en $, ganadores, desglose por
   sector, ▶ película de la cascada. Piel NEXUS. Botón "◉ En vivo".
   ============================================================================ */
(function () {
  'use strict';

  // tipos de golpe → {direction, kind} para el motor
  var TYPES = [
    { id: 'corte',   label: 'Corte ↓',   dir: 'down', kind: 'collapse', tint: '#FF4D6A', desc: 'corte de suministro' },
    { id: 'demanda', label: 'Demanda ↑', dir: 'up',   kind: 'demand',   tint: '#2BE38B', desc: 'salto de demanda' },
    { id: 'precio',  label: 'Precio',    dir: 'down', kind: 'price',    tint: '#FFB300', desc: 'shock de precio' },
    { id: 'sancion', label: 'Sanción',   dir: 'down', kind: 'sanction', tint: '#9D6BFF', desc: 'sanción / veto' },
  ];
  var PRESETS = [
    { id: 'taiwan',  label: 'Taiwán',   shock: ['TSMC'] },
    { id: 'hbm',     label: 'Memoria',  shock: ['SKHynix', 'Micron', 'Samsung'] },
    { id: 'euv',     label: 'EUV',      shock: ['ASML'] },
    { id: 'cloud',   label: 'Cloud',    shock: ['Amazon'] },
    { id: 'ia',      label: 'Boom IA',  shock: ['Nvidia'], type: 'demanda' },
  ];

  var active = false, typeId = 'corte', targets = ['TSMC'], severity = 100, factors = [], raf = 0;
  var playing = false, playTimer = 0, lastResult = null, addMode = false;

  function T() { return TYPES.find(function (t) { return t.id === typeId; }) || TYPES[0]; }
  function nm(id) { var n = window.NODE_BY_ID && window.NODE_BY_ID[id]; return n ? n.label : id; }
  function fmtB(v) { return v >= 1000 ? '$' + (v / 1000).toFixed(1) + 'T' : '$' + Math.round(v) + 'B'; }

  function ensureStyles() {
    if (document.getElementById('livesim-styles')) return;
    var css = ''
      + '#ls-btn{position:absolute;left:12px;bottom:52px;z-index:20;display:flex;align-items:center;gap:6px;'
      + 'padding:7px 13px;border-radius:9px;cursor:pointer;font-family:Inter,system-ui,sans-serif;font-size:12px;font-weight:600;'
      + 'background:rgba(15,21,34,.85);border:1px solid rgba(0,224,255,.35);color:#00E0FF;backdrop-filter:blur(6px)}'
      + '#ls-btn:hover{border-color:#00E0FF;box-shadow:0 0 12px rgba(0,224,255,.3)}#ls-btn.on{background:#00E0FF;color:#03141C}'
      + '#ls-panel{position:absolute;left:12px;bottom:96px;z-index:21;width:330px;display:none;flex-direction:column;gap:9px;'
      + 'padding:15px 16px;border-radius:13px;background:radial-gradient(430px 280px at 60% -10%,#0d1424,#06090F);'
      + 'border:1px solid rgba(122,158,255,.2);box-shadow:0 18px 50px rgba(0,0,0,.5);color:#E8EDFB;'
      + 'font-family:Inter,system-ui,sans-serif;max-height:calc(100% - 150px);overflow-y:auto}'
      + '#ls-panel.show{display:flex}'
      + '#ls-panel h4{margin:0;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#7C87A3;font-weight:600;display:flex;justify-content:space-between;align-items:center}'
      + '.ls-lbl{font-size:9.5px;letter-spacing:.1em;text-transform:uppercase;color:#5c657f;margin:3px 0 1px}'
      + '#ls-panel .lsx{cursor:pointer;color:#7C87A3;font-size:15px;line-height:1}'
      + '.ls-chips{display:flex;flex-wrap:wrap;gap:5px}'
      + '.ls-chip{font-size:11px;padding:4px 9px;border-radius:20px;cursor:pointer;border:1px solid rgba(122,158,255,.2);'
      + 'background:rgba(21,28,45,.6);color:#c8d0e0;transition:all .12s}'
      + '.ls-chip:hover{border-color:rgba(0,224,255,.5)}.ls-chip.on{background:rgba(0,224,255,.15);border-color:#00E0FF;color:#00E0FF}'
      + '.ls-tchip.on{background:rgba(255,255,255,.06)}'
      + '.ls-sel{width:100%;background:rgba(21,28,45,.85);color:#E8EDFB;border:1px solid rgba(122,158,255,.2);border-radius:8px;padding:6px 8px;font-family:inherit;font-size:11.5px}'
      + '.ls-picks{display:flex;flex-wrap:wrap;gap:4px}'
      + '.ls-pick{font-size:10.5px;padding:3px 7px;border-radius:6px;background:rgba(0,224,255,.12);border:1px solid rgba(0,224,255,.3);color:#00E0FF;display:inline-flex;align-items:center;gap:5px}'
      + '.ls-pick b{cursor:pointer;opacity:.7}.ls-pick b:hover{opacity:1}'
      + '.ls-addbtn{font-size:10.5px;padding:3px 8px;border-radius:6px;cursor:pointer;border:1px dashed rgba(122,158,255,.35);background:none;color:#8791AC;font-family:inherit}'
      + '.ls-addbtn.on{border-color:#00E0FF;color:#00E0FF;border-style:solid}'
      + '#ls-panel .lsrow{font-size:11px;color:#9BA6C4;display:flex;justify-content:space-between;align-items:center;font-family:"JetBrains Mono",monospace}'
      + '#ls-sev{width:100%;accent-color:#00E0FF;cursor:pointer}'
      + '#ls-stats{display:grid;grid-template-columns:1fr 1fr 1fr;gap:7px;text-align:center}'
      + '.ls-cell{border:1px solid rgba(122,158,255,.12);border-radius:9px;padding:8px 3px;background:rgba(21,28,45,.6)}'
      + '.ls-cell b{display:block;font-family:"JetBrains Mono",monospace;font-size:15px;font-weight:600}'
      + '.ls-cell span{font-size:8.5px;color:#7C87A3;text-transform:uppercase;letter-spacing:.05em;display:block;margin-top:2px}'
      + '#ls-sect{display:flex;flex-direction:column;gap:4px}'
      + '.ls-sbar{display:flex;align-items:center;gap:7px;font-size:10.5px;color:#9BA6C4}'
      + '.ls-sbar .sb{flex:1;height:5px;border-radius:4px;background:rgba(122,158,255,.08);overflow:hidden}'
      + '.ls-sbar .sb i{display:block;height:100%;border-radius:4px}'
      + '.ls-sbar .sp{font-family:"JetBrains Mono",monospace;font-size:9.5px;width:32px;text-align:right}'
      + '#ls-cols{display:grid;grid-template-columns:1fr 1fr;gap:10px}'
      + '#ls-cols .lsh{font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:#7C87A3;margin-bottom:4px}'
      + '.ls-v{display:flex;align-items:center;gap:6px;font-size:10.5px;cursor:pointer;padding:2px 0}'
      + '.ls-v:hover span:first-child{color:#00E0FF}.ls-v span:first-child{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:100px}'
      + '.ls-v .p{font-family:"JetBrains Mono",monospace;font-size:9.5px;margin-left:auto}'
      + '#ls-play{display:flex;align-items:center;gap:8px}'
      + '#ls-play button{flex:1;padding:7px 0;border-radius:8px;cursor:pointer;font-family:Inter,sans-serif;font-size:11.5px;font-weight:600;'
      + 'background:rgba(0,224,255,.12);border:1px solid rgba(0,224,255,.4);color:#00E0FF}'
      + '#ls-play button:hover{background:rgba(0,224,255,.22)}'
      + '#ls-hop{font-family:"JetBrains Mono",monospace;font-size:10px;color:#7C87A3;min-width:52px;text-align:right}';
    var st = document.createElement('style'); st.id = 'livesim-styles'; st.textContent = css;
    document.head.appendChild(st);
  }

  function paint(impactMap, dir) {
    if (window._liveRecolorByImpact) window._liveRecolorByImpact(impactMap, dir);
    if (window._liveTintLinks) window._liveTintLinks(impactMap, dir);
  }

  function computeWinners(impact) {
    var damaged = [];
    impact.forEach(function (v, id) { if (v >= 40) damaged.push({ id: id, v: v }); });
    var gains = new Map();
    damaged.forEach(function (d) {
      var dn = window.NODE_BY_ID[d.id]; if (!dn) return;
      (window.NODES || []).forEach(function (n) {
        if (n.id === d.id || n.cat !== dn.cat) return;
        if ((impact.get(n.id) || 0) > 15) return;
        gains.set(n.id, (gains.get(n.id) || 0) + d.v / 100);
      });
    });
    var arr = [];
    gains.forEach(function (g, id) { arr.push({ id: id, up: Math.min(45, Math.round(g * 14)) }); });
    return arr.filter(function (x) { return x.up >= 4; }).sort(function (a, b) { return b.up - a.up; }).slice(0, 5);
  }

  function run() {
    if (!window.KhipuState || !targets.length) return;
    var ty = T();
    var shocks = {};
    targets.forEach(function (id) { shocks[id] = { salud: 1 - severity / 100 }; });
    var r = window.KhipuState.simulate(shocks, factors, 8, 0.6, true, { direction: ty.dir, kind: ty.kind });
    lastResult = r;
    paint(r.impact, ty.dir);

    var arr = [], capExp = 0, sectorDmg = {}, pos = (window.MKT && window.MKT.pos) || {}, portTotal = 0, portHit = 0;
    r.impact.forEach(function (v, id) {
      if (targets.indexOf(id) < 0) arr.push({ id: id, v: v });
      var meta = (window.NODE_META || {})[id];
      if (meta && isFinite(+meta.mktcap_b)) capExp += (+meta.mktcap_b) * v / 100;
      var n = window.NODE_BY_ID[id];
      if (n && window.CAT_TO_SECTOR) { var s = window.CAT_TO_SECTOR[n.cat] || 'cloud_ia'; sectorDmg[s] = (sectorDmg[s] || 0) + v; }
    });
    Object.keys(pos).forEach(function (id) { portTotal++; portHit += (r.impact.get(id) || 0); });
    arr.sort(function (a, b) { return b.v - a.v; });
    var isUp = ty.dir === 'up';

    var stats = document.getElementById('ls-stats');
    if (stats) stats.innerHTML =
      '<div class="ls-cell"><b style="color:' + ty.tint + '">' + arr.length + '</b><span>' + (isUp ? 'benefician' : 'afectadas') + '</span></div>' +
      '<div class="ls-cell"><b style="color:' + ty.tint + '">' + fmtB(capExp) + '</b><span>cap movida</span></div>' +
      '<div class="ls-cell"><b style="color:' + (isUp ? '#2BE38B' : '#FF4D6A') + '">' + (portTotal ? (isUp ? '+' : '−') + Math.round(portHit / portTotal) + '%' : '—') + '</b><span>tu cartera</span></div>';

    var sect = document.getElementById('ls-sect');
    if (sect && window.SECTORS9) {
      var top3 = Object.keys(sectorDmg).sort(function (a, b) { return sectorDmg[b] - sectorDmg[a]; }).slice(0, 3);
      var mx = sectorDmg[top3[0]] || 1;
      sect.innerHTML = top3.map(function (s) {
        var S = window.SECTORS9[s] || {};
        return '<div class="ls-sbar"><span style="width:88px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + (S.label || s) + '</span>' +
          '<span class="sb"><i style="width:' + Math.round(sectorDmg[s] / mx * 100) + '%;background:' + (S.color || ty.tint) + '"></i></span>' +
          '<span class="sp">' + Math.round(sectorDmg[s] / 100 * 10) / 10 + '</span></div>';
      }).join('');
    }

    var vict = document.getElementById('ls-vict');
    if (vict) vict.innerHTML = arr.slice(0, 6).map(function (x) {
      return '<div class="ls-v" onclick="window.jumpTo&&window.jumpTo(\'' + x.id + '\')"><span>' + nm(x.id) + '</span>' +
        '<span class="p" style="color:' + ty.tint + '">' + (isUp ? '+' : '−') + Math.round(x.v) + '%</span></div>';
    }).join('') || '<div style="font-size:10px;color:#7C87A3">—</div>';

    // segunda columna: ganadores (solo en golpes a la baja)
    var win = document.getElementById('ls-win'), winH = document.getElementById('ls-winh');
    if (win) {
      if (isUp) { if (winH) winH.textContent = 'Cadena arriba'; win.innerHTML = '<div style="font-size:10px;color:#7C87A3">el auge sube a proveedores</div>'; }
      else {
        if (winH) winH.textContent = 'Ganadores ↑';
        var winners = computeWinners(r.impact);
        win.innerHTML = winners.map(function (x) {
          return '<div class="ls-v" onclick="window.jumpTo&&window.jumpTo(\'' + x.id + '\')"><span>' + nm(x.id) + '</span>' +
            '<span class="p" style="color:#2BE38B">↑' + x.up + '%</span></div>';
        }).join('') || '<div style="font-size:10px;color:#7C87A3">sin ganadores claros</div>';
      }
    }
    var read = document.getElementById('ls-read');
    if (read) read.innerHTML = ty.desc + ' · <b style="color:' + ty.tint + '">' + targets.slice(0, 3).map(nm).join(', ') + (targets.length > 3 ? '…' : '') + '</b> al ' + severity + '%';
  }

  function schedule() {
    if (raf) { cancelAnimationFrame(raf); clearTimeout(raf); }
    raf = (typeof document !== 'undefined' && document.hidden) ? setTimeout(run, 16) : requestAnimationFrame(run);
  }

  // ── objetivos ──
  function renderPicks() {
    var el = document.getElementById('ls-picks'); if (!el) return;
    el.innerHTML = targets.slice(0, 8).map(function (id) {
      return '<span class="ls-pick">' + nm(id) + ' <b onclick="window._lsRemove(\'' + id + '\')">✕</b></span>';
    }).join('') + (targets.length > 8 ? '<span class="ls-pick">+' + (targets.length - 8) + '</span>' : '');
  }
  window._lsRemove = function (id) { targets = targets.filter(function (t) { return t !== id; }); renderPicks(); schedule(); };
  function setTargets(ids, presetType) {
    targets = ids.filter(function (id) { return window.NODE_BY_ID && window.NODE_BY_ID[id]; });
    if (!targets.length) targets = ['TSMC'];
    if (presetType) { typeId = presetType; syncTypeChips(); }
    renderPicks(); schedule();
  }
  function syncTypeChips() { document.querySelectorAll('#ls-types .ls-chip').forEach(function (c) { c.classList.toggle('on', c.dataset.t === typeId); }); }

  // ── película ──
  function playCascade() {
    if (!lastResult || !lastResult.frames) { run(); if (!lastResult || !lastResult.frames) return; }
    stopCascade(); playing = true;
    var frames = lastResult.frames, dir = lastResult.direction, k = 0;
    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var btn = document.getElementById('ls-playbtn'), hopEl = document.getElementById('ls-hop');
    if (btn) btn.textContent = '■ Detener';
    if (reduce) { paint(frames[frames.length - 1], dir); stopCascade(); return; }
    function step() {
      if (!playing) return;
      paint(frames[Math.min(k, frames.length - 1)], dir);
      if (hopEl) hopEl.textContent = 'salto ' + Math.min(k, frames.length - 1) + '/' + (frames.length - 1);
      k++; if (k >= frames.length + 1) { stopCascade(); return; }
      playTimer = setTimeout(step, 420);
    }
    step();
  }
  function stopCascade() {
    playing = false; if (playTimer) clearTimeout(playTimer);
    var btn = document.getElementById('ls-playbtn'); if (btn) btn.textContent = '▶ Reproducir cascada';
    if (lastResult) paint(lastResult.impact, lastResult.direction);
  }

  function toggle() {
    active = !active;
    var btn = document.getElementById('ls-btn'), panel = document.getElementById('ls-panel');
    btn.classList.toggle('on', active); panel.classList.toggle('show', active);
    btn.innerHTML = active ? '<span>◉</span> En vivo · ON' : '<span>◉</span> En vivo';
    if (active) { window.KhipuState && window.KhipuState.build(); schedule(); }
    else { stopCascade(); addMode = false; if (window._liveResetColors) window._liveResetColors(); }
  }

  // añadir al escenario la empresa seleccionada en el mapa (clic en un nodo → clic aquí)
  function addSelected() {
    var sel = window._liveSelectedNode && window._liveSelectedNode();
    var b = document.getElementById('ls-addbtn');
    if (!sel) { if (b) { b.textContent = '＋ primero clic en un nodo del mapa'; setTimeout(function () { b.textContent = '＋ añadir empresa seleccionada'; }, 1600); } return; }
    if (targets.indexOf(sel) < 0) { targets.push(sel); renderPicks(); schedule(); }
    if (b) { b.textContent = '✓ ' + nm(sel) + ' añadida'; setTimeout(function () { b.textContent = '＋ añadir empresa seleccionada'; }, 1400); }
  }

  function mount() {
    var wrap = document.querySelector('.graph-wrap');
    if (!wrap || document.getElementById('ls-btn')) return;
    ensureStyles();
    var btn = document.createElement('div'); btn.id = 'ls-btn'; btn.innerHTML = '<span>◉</span> En vivo';
    btn.title = 'Simulación en vivo — arma tu escenario y ve reaccionar la red'; btn.onclick = toggle;
    var sectors = window.SECTORS9 || {};
    var countries = {}; (window.NODES || []).forEach(function (n) { if (n.country) countries[n.country] = (countries[n.country] || 0) + 1; });
    var panel = document.createElement('div'); panel.id = 'ls-panel';
    panel.innerHTML = ''
      + '<h4>Simulación en vivo <span class="lsx" onclick="window._lsToggle()">✕</span></h4>'
      + '<div class="ls-lbl">Tipo de golpe</div>'
      + '<div class="ls-chips" id="ls-types">' + TYPES.map(function (t) { return '<span class="ls-chip' + (t.id === 'corte' ? ' on' : '') + '" data-t="' + t.id + '">' + t.label + '</span>'; }).join('') + '</div>'
      + '<div class="ls-lbl">Objetivo — escenario</div>'
      + '<div class="ls-chips" id="ls-presets">' + PRESETS.map(function (p) { return '<span class="ls-chip" data-p="' + p.id + '">' + p.label + '</span>'; }).join('') + '</div>'
      + '<div class="ls-chips" style="gap:6px">'
      +   '<select class="ls-sel" id="ls-sector" style="flex:1"><option value="">Sector entero…</option>' + Object.keys(sectors).map(function (s) { return '<option value="' + s + '">' + sectors[s].label + '</option>'; }).join('') + '</select>'
      +   '<select class="ls-sel" id="ls-country" style="flex:1"><option value="">País entero…</option>' + Object.keys(countries).sort().map(function (c) { return '<option value="' + c + '">' + c + ' (' + countries[c] + ')</option>'; }).join('') + '</select>'
      + '</div>'
      + '<div class="ls-picks" id="ls-picks"></div>'
      + '<button class="ls-addbtn" id="ls-addbtn">＋ añadir empresa seleccionada</button>'
      + '<div class="lsrow"><span>Severidad</span><span id="ls-sevv">100%</span></div>'
      + '<input type="range" id="ls-sev" min="0" max="100" value="100">'
      + '<div id="ls-read" style="font-size:11px;color:#9BA6C4"></div>'
      + '<div id="ls-stats"></div><div id="ls-sect"></div>'
      + '<div id="ls-cols"><div><div class="lsh" id="ls-victh">Más afectadas</div><div id="ls-vict"></div></div>'
      +   '<div><div class="lsh" id="ls-winh">Ganadores ↑</div><div id="ls-win"></div></div></div>'
      + '<div id="ls-play"><button id="ls-playbtn">▶ Reproducir cascada</button><span id="ls-hop"></span></div>';
    wrap.appendChild(btn); wrap.appendChild(panel);

    panel.querySelectorAll('#ls-types .ls-chip').forEach(function (c) {
      c.onclick = function () { typeId = c.dataset.t; syncTypeChips(); schedule(); };
    });
    panel.querySelectorAll('#ls-presets .ls-chip').forEach(function (c) {
      c.onclick = function () {
        var p = PRESETS.find(function (x) { return x.id === c.dataset.p; });
        document.querySelectorAll('#ls-presets .ls-chip').forEach(function (o) { o.classList.toggle('on', o === c); });
        if (p) setTargets(p.shock, p.type);
      };
    });
    panel.querySelector('#ls-sector').onchange = function (e) {
      if (!e.target.value) return;
      document.querySelectorAll('#ls-presets .ls-chip').forEach(function (o) { o.classList.remove('on'); });
      panel.querySelector('#ls-country').value = '';
      setTargets(window.KhipuState.idsInSector(e.target.value));
    };
    panel.querySelector('#ls-country').onchange = function (e) {
      if (!e.target.value) return;
      document.querySelectorAll('#ls-presets .ls-chip').forEach(function (o) { o.classList.remove('on'); });
      panel.querySelector('#ls-sector').value = '';
      setTargets(window.KhipuState.idsInCountry(e.target.value));
    };
    panel.querySelector('#ls-addbtn').onclick = addSelected;
    var sev = panel.querySelector('#ls-sev');
    sev.oninput = function () { severity = +sev.value; document.getElementById('ls-sevv').textContent = severity + '%'; schedule(); };
    panel.querySelector('#ls-playbtn').onclick = function () { playing ? stopCascade() : playCascade(); };
    renderPicks();
  }

  window._lsToggle = toggle;
  if (document.querySelector('.graph-wrap')) mount(); else document.addEventListener('DOMContentLoaded', mount);
  setTimeout(mount, 1500);
})();
