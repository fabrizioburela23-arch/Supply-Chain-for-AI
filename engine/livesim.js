/* ============================================================================
   engine/livesim.js — SIMULACIÓN EN VIVO v3 (abierta, no cerrada)
   Constructor de escenarios: eliges el TIPO de golpe (corte↓, demanda↑,
   precio, sanción) y el OBJETIVO (preset, sector entero, país entero, o las
   empresas que tú elijas). Los nodos y conexiones reaccionan: rojo=daño.
   Las cifras salen del motor ÚNICO del servidor (/api/hot/* vía engine/hotclient.js,
   factores activos incluidos; paso 13 INFRA_OPERATIVA): las mismas que el X-Ray,
   la Cabina y la voz. Aquí solo queda el estado VISUAL (película por salto con
   window.KhipuState.frames). Stats en $, rivales poco golpeados, desglose por
   sector, ▶ película de la cascada. Botón "◉ En vivo". El auge de demanda (hacia
   proveedores) todavía no lo calcula el servidor: se dice, sin cifras inventadas.
   KHIPUS OS (2026-10-11): botón y panel llevan .kos-themed → tokens --os-* de
   engine/cockpit.js (claro = body sin .dark, oscuro = body.dark); el valor tras
   la coma de cada var() es el respaldo (la piel NEXUS vieja). El tinte de cada
   TIPO de golpe es un dato (rojo daño, verde auge…): como texto va en .ls-c y en
   el tema claro se oscurece para leerse. Re-etiqueta al cambiar de idioma.
   ============================================================================ */
(function () {
  'use strict';

  // bilingüe (regla del proyecto): idioma activo = window.LANG → eco_lang
  function isEn() { var l = window.LANG; if (!l) { try { l = localStorage.getItem('eco_lang'); } catch (e) { l = null; } } return l === 'en'; }
  function L(es, en) { return isEn() ? en : es; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }

  // tipos de golpe → {direction, kind} para el motor
  var TYPES = [
    { id: 'corte',   es: 'Corte ↓',   en: 'Cutoff ↓',   dir: 'down', kind: 'collapse', tint: '#FF4D6A', descEs: 'corte de suministro', descEn: 'supply cutoff' },
    { id: 'demanda', es: 'Demanda ↑', en: 'Demand ↑',   dir: 'up',   kind: 'demand',   tint: '#2BE38B', descEs: 'salto de demanda',    descEn: 'demand spike' },
    { id: 'precio',  es: 'Precio',    en: 'Price',      dir: 'down', kind: 'price',    tint: '#FFB300', descEs: 'shock de precio',     descEn: 'price shock' },
    { id: 'sancion', es: 'Sanción',   en: 'Sanction',   dir: 'down', kind: 'sanction', tint: '#9D6BFF', descEs: 'sanción / veto',      descEn: 'sanction / ban' },
  ];
  function tLabel(t) { return L(t.es, t.en); }
  function tDesc(t) { return L(t.descEs, t.descEn); }
  var PRESETS = [
    { id: 'taiwan',  es: 'Taiwán',   en: 'Taiwan',    shock: ['TSMC'] },
    { id: 'hbm',     es: 'Memoria',  en: 'Memory',    shock: ['SKHynix', 'Micron', 'Samsung'] },
    { id: 'euv',     es: 'EUV',      en: 'EUV',       shock: ['ASML'] },
    { id: 'cloud',   es: 'Cloud',    en: 'Cloud',     shock: ['Amazon'] },
    { id: 'ia',      es: 'Boom IA',  en: 'AI boom',   shock: ['Nvidia'], type: 'demanda' },
  ];

  var active = false, typeId = 'corte', targets = ['TSMC'], severity = 100, raf = 0, runSeq = 0;
  var playing = false, playTimer = 0, lastResult = null, addMode = false;

  function T() { return TYPES.find(function (t) { return t.id === typeId; }) || TYPES[0]; }
  function nm(id) { var n = window.NODE_BY_ID && window.NODE_BY_ID[id]; return n ? n.label : id; }
  function fmtB(v) { return v >= 1000 ? '$' + (v / 1000).toFixed(1) + 'T' : '$' + Math.round(v) + 'B'; }

  function ensureStyles() {
    if (document.getElementById('livesim-styles')) return;
    var css = ''
      + '#ls-btn{position:absolute;left:12px;bottom:52px;z-index:20;display:flex;align-items:center;gap:6px;'
      + 'padding:7px 13px;border-radius:9px;cursor:pointer;font-family:var(--os-font,Inter,system-ui,sans-serif);font-size:12px;font-weight:600;'
      + 'background:var(--os-surface,rgba(15,21,34,.85));border:1px solid var(--os-line,rgba(0,224,255,.35));color:var(--os-accent,#00E0FF);'
      + 'box-shadow:var(--os-shadow,none);backdrop-filter:blur(6px)}'
      + '#ls-btn:hover{border-color:var(--os-accent,#00E0FF)}#ls-btn.on{background:var(--os-btn,#00E0FF);color:var(--os-btn-ink,#03141C);border-color:var(--os-btn,#00E0FF)}'
      + '#ls-panel{position:absolute;left:12px;bottom:96px;z-index:21;width:330px;display:none;flex-direction:column;gap:9px;'
      + 'padding:15px 16px;border-radius:13px;background:var(--os-surface,radial-gradient(430px 280px at 60% -10%,#0d1424,#06090F));'
      + 'border:1px solid var(--os-line,rgba(122,158,255,.2));box-shadow:var(--kos-shadow-lg,0 18px 50px rgba(0,0,0,.5));color:var(--os-ink,#E8EDFB);'
      + 'font-family:var(--os-font,Inter,system-ui,sans-serif);max-height:calc(100% - 150px);overflow-y:auto}'
      + '#ls-panel.show{display:flex}'
      + '#ls-panel h4{margin:0;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--os-ink-2,#7C87A3);font-weight:600;display:flex;justify-content:space-between;align-items:center}'
      + '.ls-lbl{font-size:9.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--os-ink-2,#5c657f);margin:3px 0 1px}'
      + '#ls-panel .lsx{cursor:pointer;color:var(--os-ink-2,#7C87A3);font-size:15px;line-height:1}'
      + '.ls-chips{display:flex;flex-wrap:wrap;gap:5px}'
      + '.ls-chip{font-size:11px;padding:4px 9px;border-radius:20px;cursor:pointer;border:1px solid var(--os-line,rgba(122,158,255,.2));'
      + 'background:var(--os-surface-2,rgba(21,28,45,.6));color:var(--os-ink-2,#c8d0e0);transition:all .12s}'
      + '.ls-chip:hover{border-color:var(--os-accent,rgba(0,224,255,.5))}.ls-chip.on{background:var(--kos-accent-soft,rgba(0,224,255,.15));border-color:var(--os-accent,#00E0FF);color:var(--os-ink,#00E0FF)}'
      + '.ls-tchip.on{background:var(--os-surface-3,rgba(255,255,255,.06))}'
      + '.ls-sel{width:100%;background:var(--os-surface-2,rgba(21,28,45,.85));color:var(--os-ink,#E8EDFB);border:1px solid var(--os-line,rgba(122,158,255,.2));border-radius:8px;padding:6px 8px;font-family:inherit;font-size:11.5px}'
      + '.ls-picks{display:flex;flex-wrap:wrap;gap:4px}'
      + '.ls-pick{font-size:10.5px;padding:3px 7px;border-radius:6px;background:var(--kos-accent-soft,rgba(0,224,255,.12));border:1px solid var(--os-accent,rgba(0,224,255,.3));color:var(--os-ink,#00E0FF);display:inline-flex;align-items:center;gap:5px}'
      + '.ls-pick b{cursor:pointer;opacity:.7}.ls-pick b:hover{opacity:1}'
      + '.ls-addbtn{font-size:10.5px;padding:3px 8px;border-radius:6px;cursor:pointer;border:1px dashed var(--os-ink-3,rgba(122,158,255,.35));background:none;color:var(--os-ink-2,#8791AC);font-family:inherit}'
      + '.ls-addbtn.on{border-color:var(--os-accent,#00E0FF);color:var(--os-accent,#00E0FF);border-style:solid}'
      + '#ls-panel .lsrow{font-size:11px;color:var(--os-ink-2,#9BA6C4);display:flex;justify-content:space-between;align-items:center;font-family:"JetBrains Mono",monospace}'
      + '#ls-sev{width:100%;accent-color:var(--os-accent,#00E0FF);cursor:pointer}'
      + '#ls-stats{display:grid;grid-template-columns:1fr 1fr 1fr;gap:7px;text-align:center}'
      + '.ls-cell{border:1px solid var(--os-line,rgba(122,158,255,.12));border-radius:9px;padding:8px 3px;background:var(--os-surface-2,rgba(21,28,45,.6))}'
      + '.ls-cell b{display:block;font-family:"JetBrains Mono",monospace;font-size:15px;font-weight:600}'
      + '.ls-cell span{font-size:8.5px;color:var(--os-ink-2,#7C87A3);text-transform:uppercase;letter-spacing:.05em;display:block;margin-top:2px}'
      + '#ls-sect{display:flex;flex-direction:column;gap:4px}'
      + '.ls-sbar{display:flex;align-items:center;gap:7px;font-size:10.5px;color:var(--os-ink-2,#9BA6C4)}'
      + '.ls-sbar .sb{flex:1;height:5px;border-radius:4px;background:var(--os-surface-3,rgba(122,158,255,.08));overflow:hidden}'
      + '.ls-sbar .sb i{display:block;height:100%;border-radius:4px}'
      + '.ls-sbar .sp{font-family:"JetBrains Mono",monospace;font-size:9.5px;width:32px;text-align:right}'
      + '#ls-cols{display:grid;grid-template-columns:1fr 1fr;gap:10px}'
      + '#ls-cols .lsh{font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:var(--os-ink-2,#7C87A3);margin-bottom:4px}'
      + '.ls-v{display:flex;align-items:center;gap:6px;font-size:10.5px;cursor:pointer;padding:2px 0}'
      + '.ls-v:hover span:first-child{color:var(--os-accent,#00E0FF)}.ls-v span:first-child{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:100px}'
      + '.ls-v .p{font-family:"JetBrains Mono",monospace;font-size:9.5px;margin-left:auto}'
      + '.ls-v .p.up{color:var(--os-good-ink,#2BE38B)}.ls-v .p.mute{color:var(--os-ink-2,#7C87A3)}'
      + '.ls-hrow{border:1px solid var(--os-line,rgba(122,158,255,.1));border-radius:7px;padding:5px 8px}'
      + '.ls-msg{font-size:10px;color:var(--os-ink-2,#7C87A3)}'
      + '.ls-read{font-size:11px;color:var(--os-ink-2,#9BA6C4)}'
      + '.ls-up{color:var(--os-good-ink,#2BE38B)!important}.ls-down{color:var(--os-bad-ink,#FF4D6A)!important}'
      // tinte del tipo de golpe (dato) como texto: igual en oscuro; en claro se mezcla con la tinta para leerse
      // (!important = la precedencia del style="color:…" que reemplaza)
      + '.ls-c{color:var(--ls-c)!important}'
      + '@supports (color:color-mix(in srgb,red 50%,blue)){body:not(.dark) .ls-c{color:color-mix(in srgb,var(--ls-c) 50%,var(--os-ink,#111216))!important}}'
      + '#ls-save{display:flex;gap:7px}'
      + '#ls-save button{flex:1;padding:6px 0;border-radius:8px;cursor:pointer;font-family:inherit;font-size:11px;font-weight:600;'
      + 'background:var(--os-surface-2,rgba(122,158,255,.1));border:1px solid var(--os-line,rgba(122,158,255,.3));color:var(--os-ink,#c8d0e0)}'
      + '#ls-save button:hover{border-color:var(--os-accent,#00E0FF)}'
      + '#ls-play{display:flex;align-items:center;gap:8px}'
      + '#ls-play button{flex:1;padding:7px 0;border-radius:8px;cursor:pointer;font-family:inherit;font-size:11.5px;font-weight:600;'
      + 'background:var(--kos-accent-soft,rgba(0,224,255,.12));border:1px solid var(--os-accent,rgba(0,224,255,.4));color:var(--os-ink,#00E0FF)}'
      + '#ls-play button:hover{background:var(--os-surface-3,rgba(0,224,255,.22))}'
      + '#ls-hop{font-family:"JetBrains Mono",monospace;font-size:10px;color:var(--os-ink-2,#7C87A3);min-width:52px;text-align:right}';
    var st = document.createElement('style'); st.id = 'livesim-styles'; st.textContent = css;
    document.head.appendChild(st);
  }

  function paint(impactMap, dir) {
    if (window._liveRecolorByImpact) window._liveRecolorByImpact(impactMap, dir);
    if (window._liveTintLinks) window._liveTintLinks(impactMap, dir);
  }

  // sin cifras: el motor del servidor no respondió o no calcula este tipo de golpe → se DICE, no se inventa
  function clearPanel(msg) {
    ['ls-sect', 'ls-vict', 'ls-win', 'ls-pnl'].forEach(function (k) { var el = document.getElementById(k); if (el) el.innerHTML = ''; });
    var st = document.getElementById('ls-stats');
    if (st) { st.style.display = 'block'; st.innerHTML = '<div class="ls-msg ls-err">' + esc(msg) + '</div>'; }
  }

  function run() {
    if (!targets.length) return;
    var ty = T();
    var seq = ++runSeq;
    if (!window.KhipuHot) { clearPanel(L('Motor de simulación no disponible.', 'Simulation engine unavailable.')); return; }
    var read = document.getElementById('ls-read');
    if (read) read.innerHTML = tDesc(ty) + ' · <b class="ls-c" style="--ls-c:' + ty.tint + '">' + esc(targets.slice(0, 3).map(nm).join(', ')) + (targets.length > 3 ? '…' : '') + '</b> ' + L('al', 'at') + ' ' + severity + '% · ' + L('calculando…', 'computing…');
    window.KhipuHot.simulate({ targets: targets, kind: ty.kind, severity: severity }).then(function (r) {
      if (seq !== runSeq) return;   // llegó tarde: ya se pidió otro escenario
      paintResult(ty, r);
    });
  }

  function paintResult(ty, r) {
    var read = document.getElementById('ls-read');
    var head = tDesc(ty) + ' · <b class="ls-c" style="--ls-c:' + ty.tint + '">' + esc(targets.slice(0, 3).map(nm).join(', ')) + (targets.length > 3 ? '…' : '') + '</b> ' + L('al', 'at') + ' ' + severity + '%';
    if (!r || !r.ok) {
      lastResult = null;
      if (window._liveResetColors) window._liveResetColors();
      if (read) read.innerHTML = head;
      clearPanel((r && r.error) || L('No se pudo simular.', 'Could not simulate.'));
      return;
    }
    lastResult = r;
    paint(r.impact, r.direction);
    if (read) read.innerHTML = head + (r.note ? '<div class="ls-msg" style="margin-top:3px">' + esc(r.note) + '</div>' : '') +
      '<div style="margin-top:3px">' + window.KhipuHot.stampHTML(r.view) + '</div>';

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
    var isUp = r.direction === 'up';

    var stats = document.getElementById('ls-stats');
    if (stats) { stats.style.display = ''; stats.innerHTML =
      '<div class="ls-cell"><b class="ls-c" style="--ls-c:' + ty.tint + '">' + r.reach_1 + '</b><span>' + (isUp ? L('benefician', 'benefit') : L('afectadas ≥1 %', 'affected ≥1%')) + '</span></div>' +
      '<div class="ls-cell"><b class="ls-c" style="--ls-c:' + ty.tint + '">' + fmtB(capExp) + '</b><span>' + L('cap movida', 'cap moved') + '</span></div>' +
      '<div class="ls-cell"><b class="' + (isUp ? 'ls-up' : 'ls-down') + '">' + (portTotal ? (isUp ? '+' : '−') + Math.round(portHit / portTotal) + '%' : '—') + '</b><span>' + L('golpe medio a tu cartera', 'avg hit to your portfolio') + '</span></div>'; }
    // batch I3: "Tu cartera: −X ± Y USD" — cifra del SERVIDOR (κ calibrado; débil → lo dice), solo con posiciones
    if (stats && window.KhipuHot.pnlLine) {
      var pnlEl = document.getElementById('ls-pnl');
      if (!pnlEl) {
        pnlEl = document.createElement('div');
        pnlEl.id = 'ls-pnl'; pnlEl.className = 'ls-msg'; pnlEl.style.cssText = 'display:none;margin:4px 0 2px';
        stats.parentNode.insertBefore(pnlEl, stats.nextSibling);
      }
      // record:false (revisión lote I): la decisión de la simulación sale de UN sitio (/api/hot/scenario con 2+
      // semillas); antes cada ajuste del deslizador dejaba DOS whatif.shock si el usuario tenía posiciones
      window.KhipuHot.pnlLine(pnlEl, { targets: targets.slice(), severity: severity, kind: ty.kind, record: false });
    }

    var sect = document.getElementById('ls-sect');
    if (sect && window.SECTORS9) {
      var top3 = Object.keys(sectorDmg).sort(function (a, b) { return sectorDmg[b] - sectorDmg[a]; }).slice(0, 3);
      var mx = sectorDmg[top3[0]] || 1;
      sect.innerHTML = top3.map(function (s) {
        var S = window.SECTORS9[s] || {};
        return '<div class="ls-sbar"><span style="width:88px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + (window.sectorName ? window.sectorName(s) : (S.label || s)) + '</span>' +
          '<span class="sb"><i style="width:' + Math.round(sectorDmg[s] / mx * 100) + '%;background:' + (S.color || ty.tint) + '"></i></span>' +
          '<span class="sp">' + Math.round(sectorDmg[s] / 100 * 10) / 10 + '</span></div>';
      }).join('');
    }

    var vict = document.getElementById('ls-vict');
    if (vict) vict.innerHTML = arr.slice(0, 6).map(function (x) {
      return '<div class="ls-v" onclick="window.jumpTo&&window.jumpTo(\'' + esc(x.id) + '\')"><span>' + esc(nm(x.id)) + '</span>' +
        '<span class="p ls-c" style="--ls-c:' + ty.tint + '">' + (isUp ? '+' : '−') + Math.round(x.v) + '%</span></div>';
    }).join('') || '<div class="ls-msg">—</div>';

    // segunda columna: rivales del mismo rubro poco golpeados según el servidor (sin % de ganancia inventado)
    var win = document.getElementById('ls-win'), winH = document.getElementById('ls-winh');
    if (win) {
      if (winH) winH.textContent = S('win');
      var winners = isUp ? [] : window.KhipuHot.rivals(targets, r.impact, 5);
      win.innerHTML = winners.map(function (x) {
        return '<div class="ls-v" onclick="window.jumpTo&&window.jumpTo(\'' + esc(x.id) + '\')"><span>' + esc(nm(x.id)) + '</span>' +
          '<span class="p up">' + L('golpe ', 'hit ') + Math.round(x.hit) + '%</span></div>';
      }).join('') || '<div class="ls-msg">' + L('sin rivales claros', 'no clear rivals') + '</div>';
    }
  }

  // el servidor calcula: se le pide UNA vez cuando el deslizador se detiene (no en cada píxel; respeta su límite)
  function schedule() {
    if (raf) clearTimeout(raf);
    raf = setTimeout(run, 250);
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
    if (!lastResult || !window.KhipuState || !window.KhipuState.frames) { run(); return; }
    stopCascade(); playing = true;
    var frames = window.KhipuState.frames(lastResult), dir = lastResult.direction, k = 0;
    if (!frames.length) { stopCascade(); return; }
    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var btn = document.getElementById('ls-playbtn'), hopEl = document.getElementById('ls-hop');
    if (btn) btn.textContent = L('■ Detener', '■ Stop');
    if (reduce) { paint(frames[frames.length - 1], dir); stopCascade(); return; }
    function step() {
      if (!playing) return;
      paint(frames[Math.min(k, frames.length - 1)], dir);
      if (hopEl) hopEl.textContent = L('salto ', 'hop ') + Math.min(k, frames.length - 1) + '/' + (frames.length - 1);
      k++; if (k >= frames.length + 1) { stopCascade(); return; }
      playTimer = setTimeout(step, 420);
    }
    step();
  }
  function stopCascade() {
    playing = false; if (playTimer) clearTimeout(playTimer);
    var btn = document.getElementById('ls-playbtn'); if (btn) btn.textContent = L('▶ Reproducir cascada', '▶ Play cascade');
    if (lastResult) paint(lastResult.impact, lastResult.direction);
  }

  function toggle() {
    active = !active;
    var btn = document.getElementById('ls-btn'), panel = document.getElementById('ls-panel');
    btn.classList.toggle('on', active); panel.classList.toggle('show', active);
    btn.innerHTML = active ? '<span>◉</span> ' + L('En vivo', 'Live') + ' · ON' : '<span>◉</span> ' + L('En vivo', 'Live');
    if (active) { applyLang(); schedule(); }
    else { stopCascade(); addMode = false; if (window._liveResetColors) window._liveResetColors(); }
  }

  // añadir al escenario la empresa seleccionada en el mapa (clic en un nodo → clic aquí)
  function addSelected() {
    var sel = window._liveSelectedNode && window._liveSelectedNode();
    var b = document.getElementById('ls-addbtn');
    if (!sel) { if (b) { b.textContent = L('＋ primero clic en un nodo del mapa', '＋ first click a node on the map'); setTimeout(function () { b.textContent = L('＋ añadir empresa seleccionada', '＋ add selected company'); }, 1600); } return; }
    if (targets.indexOf(sel) < 0) { targets.push(sel); renderPicks(); schedule(); }
    if (b) { b.textContent = '✓ ' + nm(sel) + L(' añadida', ' added'); setTimeout(function () { b.textContent = L('＋ añadir empresa seleccionada', '＋ add selected company'); }, 1400); }
  }

  // textos estáticos del panel: se re-aplican al abrirlo (cambio de idioma)
  var STR = {
    title: ['Simulación en vivo', 'Live simulation'],
    type: ['Tipo de golpe', 'Shock type'],
    target: ['Objetivo — escenario', 'Target — scenario'],
    sector: ['Sector entero…', 'Whole sector…'],
    country: ['País entero…', 'Whole country…'],
    add: ['＋ añadir empresa seleccionada', '＋ add selected company'],
    sev: ['Severidad', 'Severity'],
    vict: ['Más afectadas', 'Most affected'],
    win: ['Rivales poco golpeados', 'Barely hit rivals'],
    play: ['▶ Reproducir cascada', '▶ Play cascade'],
    save: ['💾 Guardar', '💾 Save'],
    hist: ['📁 Historial', '📁 History'],
  };
  function S(k) { return L(STR[k][0], STR[k][1]); }
  function applyLang() {
    var panel = document.getElementById('ls-panel'); if (!panel) return;
    panel.querySelectorAll('[data-l]').forEach(function (el) { el.textContent = S(el.getAttribute('data-l')); });
    panel.querySelectorAll('#ls-types .ls-chip').forEach(function (c) {
      var t = TYPES.find(function (x) { return x.id === c.dataset.t; }); if (t) c.textContent = tLabel(t);
    });
    panel.querySelectorAll('#ls-presets .ls-chip').forEach(function (c) {
      var p = PRESETS.find(function (x) { return x.id === c.dataset.p; }); if (p) c.textContent = L(p.es, p.en);
    });
    var sec = panel.querySelector('#ls-sector');
    if (sec && window.sectorName) Array.prototype.forEach.call(sec.options, function (o) { if (o.value) o.textContent = window.sectorName(o.value); });
    if (!playing) { var pb = document.getElementById('ls-playbtn'); if (pb) pb.textContent = S('play'); }
    var bt = document.getElementById('ls-btn'); if (bt) bt.title = L('Simulación en vivo — arma tu escenario y ve reaccionar la red', 'Live simulation — build your scenario and watch the network react');
  }

  function mount() {
    var wrap = document.querySelector('.graph-wrap');
    if (!wrap || document.getElementById('ls-btn')) return;
    ensureStyles();
    var btn = document.createElement('div'); btn.id = 'ls-btn'; btn.className = 'kos-themed'; btn.innerHTML = '<span>◉</span> ' + L('En vivo', 'Live');
    btn.title = L('Simulación en vivo — arma tu escenario y ve reaccionar la red', 'Live simulation — build your scenario and watch the network react'); btn.onclick = toggle;
    var sectors = window.SECTORS9 || {};
    // países agrupados por clave del catálogo (GeoCoords.countryGroup: 'Taiwán' + 'Taiwan' = uno) con nombre ES/EN
    var cg = function (c) { var G = window.GeoCoords; return (G && G.countryGroup) ? G.countryGroup(c) : c; };
    var cName = function (k) { var KC = window.KhipuCountries; return (KC && KC.label) ? KC.label(k, isEn() ? 'en' : 'es') : k; };
    var countries = {}; (window.NODES || []).forEach(function (n) { if (n.country) { var k = cg(n.country); countries[k] = (countries[k] || 0) + 1; } });
    var panel = document.createElement('div'); panel.id = 'ls-panel'; panel.className = 'kos-themed';   // tokens --os-* (claro/oscuro)
    panel.innerHTML = ''
      + '<h4><span data-l="title">' + S('title') + '</span> <span class="lsx" onclick="window._lsToggle()">✕</span></h4>'
      + '<div class="ls-lbl" data-l="type">' + S('type') + '</div>'
      + '<div class="ls-chips" id="ls-types">' + TYPES.map(function (t) { return '<span class="ls-chip' + (t.id === 'corte' ? ' on' : '') + '" data-t="' + t.id + '">' + tLabel(t) + '</span>'; }).join('') + '</div>'
      + '<div class="ls-lbl" data-l="target">' + S('target') + '</div>'
      + '<div class="ls-chips" id="ls-presets">' + PRESETS.map(function (p) { return '<span class="ls-chip" data-p="' + p.id + '">' + L(p.es, p.en) + '</span>'; }).join('') + '</div>'
      + '<div class="ls-chips" style="gap:6px">'
      +   '<select class="ls-sel" id="ls-sector" style="flex:1"><option value="" data-l="sector">' + S('sector') + '</option>' + Object.keys(sectors).map(function (s) { return '<option value="' + s + '">' + (window.sectorName ? window.sectorName(s) : sectors[s].label) + '</option>'; }).join('') + '</select>'
      +   '<select class="ls-sel" id="ls-country" style="flex:1"><option value="" data-l="country">' + S('country') + '</option>' + Object.keys(countries).sort(function (a, b) { return cName(a).localeCompare(cName(b)); }).map(function (c) { return '<option value="' + esc(c) + '">' + esc(cName(c)) + ' (' + countries[c] + ')</option>'; }).join('') + '</select>'
      + '</div>'
      + '<div class="ls-picks" id="ls-picks"></div>'
      + '<button class="ls-addbtn" id="ls-addbtn" data-l="add">' + S('add') + '</button>'
      + '<div class="lsrow"><span data-l="sev">' + S('sev') + '</span><span id="ls-sevv">100%</span></div>'
      + '<input type="range" id="ls-sev" min="0" max="100" value="100">'
      + '<div id="ls-read" class="ls-read"></div>'
      + '<div id="ls-stats"></div><div id="ls-sect"></div>'
      + '<div id="ls-cols"><div><div class="lsh" id="ls-victh" data-l="vict">' + S('vict') + '</div><div id="ls-vict"></div></div>'
      +   '<div><div class="lsh" id="ls-winh">' + S('win') + '</div><div id="ls-win"></div></div></div>'
      + '<div id="ls-play"><button id="ls-playbtn">' + S('play') + '</button><span id="ls-hop"></span></div>'
      + '<div id="ls-save"><button id="ls-savebtn" data-l="save">' + S('save') + '</button>'
      +   '<button id="ls-histbtn" data-l="hist">' + S('hist') + '</button></div>'
      + '<div id="ls-hist" style="display:none;flex-direction:column;gap:3px;margin-top:2px"></div>';
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
    panel.querySelector('#ls-savebtn').onclick = saveSim;
    panel.querySelector('#ls-histbtn').onclick = toggleHist;
    renderPicks();
  }

  function saveSim() {
    var btn0 = document.getElementById('ls-savebtn');
    if (!lastResult) { if (btn0) { btn0.textContent = L('⚠ nada que guardar', '⚠ nothing to save'); setTimeout(function () { btn0.textContent = S('save'); }, 1600); } return; }
    var ty = T();
    var top = [];
    lastResult.impact.forEach(function (v, id) { if (targets.indexOf(id) < 0) top.push({ id: id, v: v }); });
    top.sort(function (a, b) { return b.v - a.v; });
    var btn = document.getElementById('ls-savebtn');
    if (btn) btn.textContent = L('Guardando…', 'Saving…');
    fetch('/api/matrix/simulations', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        actor: window.khipuActor ? window.khipuActor() : 'usuario',   // EL helper único (engine/toast.js)
        name: tDesc(ty) + ' · ' + targets.slice(0, 2).map(nm).join(', ') + (targets.length > 2 ? '…' : ''),
        targets: targets, kind: ty.kind, direction: ty.dir, severity: severity,
        affected: lastResult.reach_1, top: top.slice(0, 8),
        engine_generation: lastResult.view ? lastResult.view.generation : null,
      }),
    }).then(function (r) { return r.ok ? r.json() : null; }).then(function (d) {
      if (btn) { btn.textContent = d && d.id ? L('✓ Guardada', '✓ Saved') : L('⚠ requiere Postgres', '⚠ requires Postgres'); setTimeout(function () { btn.textContent = S('save'); }, 1600); }
    }).catch(function () { if (btn) { btn.textContent = L('⚠ sin conexión', '⚠ offline'); setTimeout(function () { btn.textContent = S('save'); }, 1600); } });
  }

  function toggleHist() {
    var el = document.getElementById('ls-hist');
    if (el.style.display === 'flex') { el.style.display = 'none'; return; }
    el.style.display = 'flex'; el.innerHTML = '<div class="ls-msg">' + L('Cargando historial…', 'Loading history…') + '</div>';
    fetch('/api/matrix/simulations?limit=20').then(function (r) { return r.ok ? r.json() : null; }).then(function (d) {
      if (!d || !d.simulations) { el.innerHTML = '<div class="ls-msg">' + L('Historial requiere Postgres (Railway).', 'History requires Postgres (Railway).') + '</div>'; return; }
      if (!d.simulations.length) { el.innerHTML = '<div class="ls-msg">' + L('Sin simulaciones guardadas aún.', 'No saved simulations yet.') + '</div>'; return; }
      el.innerHTML = d.simulations.map(function (s) {
        var when = ''; try { when = new Date(s.saved_at).toLocaleDateString(isEn() ? 'en' : 'es', { day: 'numeric', month: 'short' }); } catch (e) {}
        return '<div class="ls-v ls-hrow" ' +
          'onclick=\'window._lsReplay(' + JSON.stringify(JSON.stringify({ targets: s.targets, kind: s.kind, dir: s.direction, sev: s.severity })) + ')\'>' +
          '<span style="max-width:150px">' + esc(s.label || 'sim') + '</span>' +
          '<span class="p mute">' + when + '</span></div>';
      }).join('');
    }).catch(function () { el.innerHTML = '<div class="ls-msg">' + L('No se pudo cargar.', 'Could not load.') + '</div>'; });
  }

  window._lsReplay = function (json) {
    try {
      var s = JSON.parse(json);
      var ty = TYPES.find(function (t) { return t.kind === s.kind && t.dir === s.dir; }) || TYPES[0];
      typeId = ty.id; syncTypeChips();
      severity = s.sev != null ? s.sev : 100;
      var sv = document.getElementById('ls-sev'); if (sv) { sv.value = severity; document.getElementById('ls-sevv').textContent = severity + '%'; }
      document.querySelectorAll('#ls-presets .ls-chip').forEach(function (o) { o.classList.remove('on'); });
      setTargets(s.targets || ['TSMC']);
      document.getElementById('ls-hist').style.display = 'none';
    } catch (e) {}
  };

  window._lsToggle = toggle;
  // idioma: applyLang() (app.html) fija <html lang> → re-etiqueta el botón y, si está abierto, el panel
  function onLang() {
    var bt = document.getElementById('ls-btn'); if (!bt) return;
    bt.innerHTML = active ? '<span>◉</span> ' + L('En vivo', 'Live') + ' · ON' : '<span>◉</span> ' + L('En vivo', 'Live');
    applyLang();
    if (active) schedule();   // estadísticas, columnas y lectura en el idioma nuevo
    var h = document.getElementById('ls-hist');
    if (h && h.style.display === 'flex') { h.style.display = 'none'; toggleHist(); }
  }
  try { new MutationObserver(onLang).observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] }); } catch (e) {}
  window.addEventListener('khipu:lang', onLang);
  if (document.querySelector('.graph-wrap')) mount(); else document.addEventListener('DOMContentLoaded', mount);
  setTimeout(mount, 1500);
})();
