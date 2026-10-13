
/**
 * KHIPU FINANCE — Scatter 3D Semántico con Medidores
 * Botón 📊: posiciona empresas en ejes semánticos + panel de medidores interactivo
 */
(function khipuScatter() {
  'use strict';

  const TTM = {
    ai_agents:0, aisoft:0, ailab:0, cloud:0,
    ai_finance:0.5, cdn_edge:0.5,
    networking:1, memory:1, foundry:1, dc_reit:1,
    servers:1, connectivity_infra:1,
    eda:2, equip:2, optics:2, substrates:2, chemicals:2,
    materials:2, rare_earth:2, asic_custom:2, edge_ai:2,
    photonics_si:2, fabless:2, power:2, battery_mat:2,
    hpc_super:2, uranium:2,
    ai_health:3, ai_auto:3, ai_defense:3, earth_obs:3,
    satellite:3, quantum_infra:3,
    robotics_physical:5, space_infra:5, space_launch:5,
    neuromorphic:5, nuclear_smr:7,
    quantum_hw:10, nuclear_fusion:15,
  };

  // Capitalización: NODE_META (EN VIVO tras KhipuLiveCaps; si no, catálogo).
  // Antes: tabla CAP_B fija (NVDA 3200, AVGO 750…) + $8B/$1B INVENTADOS para
  // el resto — se mostraban como "Mkt cap" y filtraban "Oportunidades".
  function capOf(node) {
    const v = +((window.NODE_META || {})[node.id] || {}).mktcap_b;
    return isFinite(v) && v > 0 ? v : null;
  }
  const LOG_MAX = Math.log10(6000);
  const SPREAD  = 340;

  function riskNorm(node) {
    if (node.margin == null) {
      const g = (node.growth || '').toLowerCase();
      return (g.includes('pre-ipo') || g.includes('privada')) ? 0.85 : 0.70;
    }
    const m = node.margin * 100;   // margin viene como fracción (0.49 = 49%)
    return m > 30 ? 0.10
         : m > 15 ? 0.25
         : m >  0 ? 0.45
         : m > -50 ? 0.65
         : 0.88;
  }

  function semXYZ(node) {
    const ttm = TTM[node.cat] ?? 5;
    const x   = (Math.min(1, ttm / 15) - 0.5) * SPREAD + (Math.random() - 0.5) * 16;
    const cap = capOf(node) ?? 0.3;   // sin dato → franja baja (solo posición; el medidor dice "s/d")
    const y   = (Math.log10(cap + 1) / LOG_MAX - 0.5) * SPREAD + (Math.random() - 0.5) * 16;
    const zn  = riskNorm(node);
    return { x, y, z: (zn - 0.5) * SPREAD + (Math.random() - 0.5) * 16 };
  }

  const FILTERS = {
    all:      () => true,
    gems:     n => (TTM[n.cat] ?? 5) <= 1 && riskNorm(n) < 0.55 && capOf(n) != null && capOf(n) < 200,
    lowrisk:  n => riskNorm(n) < 0.38,
    emerging: n => (TTM[n.cat] ?? 5) >= 3,
    highrisk: n => riskNorm(n) > 0.60,
  };
  function applyScatterFilter(key) {
    const pred = FILTERS[key] || FILTERS.all;
    const inst = getInst(); if (!inst) return;
    inst.nodeMeshes.forEach(mesh => {
      const node = mesh.userData && mesh.userData.node; if (!node) return;
      const on = pred(node);
      if (mesh.material) { mesh.material.transparent = true; mesh.material.opacity = on ? 0.95 : 0.05; }
      (mesh.children || []).forEach(ch => { ch.visible = on; });
      // los halos ya no son hijos del mesh (nube GPU) — sincronizar el filtro
      if (inst.setHaloDim) inst.setHaloDim(node.id, !on);
    });
  }

  const GAUGE_STYLE = `
    #kg-panel {
      position:fixed; bottom:52px; left:16px; z-index:9999;
      background:rgba(6,12,22,.96); border:1px solid #1e3a4a;
      border-radius:12px; padding:14px 16px; min-width:310px;
      font-family:inherit; color:#b0c8cc; pointer-events:none;
      box-shadow:0 4px 24px rgba(0,0,0,.5);
      backdrop-filter:blur(10px);
    }
    #kg-panel .kg-title {
      font-size:13px; font-weight:700; color:#eee;
      margin-bottom:10px; display:flex; align-items:center; gap:6px;
    }
    #kg-filters { display:flex; flex-wrap:wrap; gap:5px; margin-bottom:12px; pointer-events:auto; }
    #kg-filters .kgf { font-size:10px; padding:3px 8px; border-radius:12px; border:1px solid #2a4a5a;
      background:rgba(255,255,255,.04); color:#bcd; cursor:pointer; transition:.12s; }
    #kg-filters .kgf:hover { background:rgba(79,195,247,.18); }
    #kg-filters .kgf.on { background:#4fc3f7; color:#022; border-color:#4fc3f7; font-weight:700; }
    .kg-axis { margin-bottom:10px; }
    .kg-axis-name { font-size:10.5px; color:#8aa; margin-bottom:4px; display:flex; align-items:center; gap:5px; }
    .kg-track { position:relative; height:9px; background:rgba(255,255,255,.07); border-radius:5px; overflow:hidden; }
    .kg-fill { height:100%; width:0%; border-radius:5px; transition:width .35s cubic-bezier(.4,0,.2,1); }
    .kg-ends { display:flex; justify-content:space-between; margin-top:3px; font-size:9.5px; color:#556; }
    .kg-ends .kg-cur { color:#eee; font-weight:600; font-size:10.5px; }
    #kg-node-name { margin-top:11px; padding-top:10px; border-top:1px solid #1e3a4a; font-size:12px; color:#7a9; text-align:center; min-height:20px; }
    #kg-node-name b { color:#eef; font-size:13px; }
    #kg-node-name .kg-ticker { color:#4fc3f7; font-size:11px; margin-left:5px; }
    #kg-node-name .kg-cat { color:#556; font-size:10px; margin-left:4px; }
  `;

  function injectStyles() {
    if (document.getElementById('kg-styles')) return;
    const s = document.createElement('style'); s.id = 'kg-styles'; s.textContent = GAUGE_STYLE;
    document.head.appendChild(s);
  }

  function createPanel() {
    injectStyles();
    let el = document.getElementById('kg-panel');
    if (el) return el;
    el = document.createElement('div'); el.id = 'kg-panel';
    el.innerHTML = `
      <div class="kg-title">📊 Scatter 3D — Inversión</div>
      <div id="kg-filters">
        <span class="kgf on" data-f="all">Todas</span>
        <span class="kgf" data-f="gems">💎 Oportunidades</span>
        <span class="kgf" data-f="lowrisk">🛡 Bajo riesgo</span>
        <span class="kgf" data-f="emerging">🚀 Tech temprana</span>
        <span class="kgf" data-f="highrisk">⚠ Alto riesgo</span>
      </div>
      <div class="kg-axis">
        <div class="kg-axis-name"><span style="color:#4fc3f7;font-size:14px">━</span> X &nbsp;Tiempo al mercado</div>
        <div class="kg-track"><div class="kg-fill" id="kg-x-fill" style="background:linear-gradient(90deg,#1976d2,#4fc3f7)"></div></div>
        <div class="kg-ends"><span>Hoy</span><span class="kg-cur" id="kg-x-val">—</span><span>15 años</span></div>
      </div>
      <div class="kg-axis">
        <div class="kg-axis-name"><span style="color:#a5d6a7;font-size:14px">━</span> Y &nbsp;Capitalización de mercado</div>
        <div class="kg-track"><div class="kg-fill" id="kg-y-fill" style="background:linear-gradient(90deg,#2e7d32,#a5d6a7)"></div></div>
        <div class="kg-ends"><span>Micro-cap</span><span class="kg-cur" id="kg-y-val">—</span><span>Mega-cap</span></div>
      </div>
      <div class="kg-axis">
        <div class="kg-axis-name"><span style="color:#ff8a65;font-size:14px">━</span> Z &nbsp;Riesgo financiero</div>
        <div class="kg-track"><div class="kg-fill" id="kg-z-fill" style="background:linear-gradient(90deg,#2ecc71,#e67e22,#e74c3c)"></div></div>
        <div class="kg-ends"><span>Bajo riesgo</span><span class="kg-cur" id="kg-z-val">—</span><span>Muy alto</span></div>
      </div>
      <div id="kg-node-name">Pasa el ratón sobre un nodo</div>
    `;
    document.body.appendChild(el);
    el.querySelectorAll('#kg-filters .kgf').forEach(c => c.addEventListener('click', () => {
      el.querySelectorAll('#kg-filters .kgf').forEach(x => x.classList.remove('on'));
      c.classList.add('on');
      applyScatterFilter(c.dataset.f);
    }));
    return el;
  }

  function setGauge(id, pct) { const el = document.getElementById(id); if (el) el.style.width = Math.max(0, Math.min(100, pct)) + '%'; }
  function setText(id, txt)  { const el = document.getElementById(id); if (el) el.textContent = txt; }

  function updateGauges(node) {
    const nameEl = document.getElementById('kg-node-name'); if (!nameEl) return;
    if (!node) {
      setGauge('kg-x-fill', 0); setText('kg-x-val', '—');
      setGauge('kg-y-fill', 0); setText('kg-y-val', '—');
      setGauge('kg-z-fill', 0); setText('kg-z-val', '—');
      nameEl.innerHTML = 'Pasa el ratón sobre un nodo'; return;
    }
    const ttm = TTM[node.cat] ?? 5;
    setGauge('kg-x-fill', (ttm / 15) * 100);
    setText('kg-x-val', ttm === 0 ? 'Disponible hoy' : ttm + ' año' + (ttm === 1 ? '' : 's'));
    const cap = capOf(node);
    setGauge('kg-y-fill', cap == null ? 0 : (Math.log10(cap + 1) / LOG_MAX) * 100);
    const capLabel = cap == null ? (LANG === 'en' ? 'n/a' : 's/d')
      : (cap >= 1000 ? '$' + (cap / 1000).toFixed(1) + 'T' : cap >= 1 ? '$' + Math.round(cap) + 'B' : '$' + (cap * 1000).toFixed(0) + 'M')
        + (((window.NODE_META || {})[node.id] || {}).mktcap_live ? (LANG === 'en' ? ' · live' : ' · en vivo') : (LANG === 'en' ? ' · catalog' : ' · catálogo'));
    setText('kg-y-val', capLabel);
    const zn = riskNorm(node);
    setGauge('kg-z-fill', zn * 100);
    const rLabel = zn < 0.20 ? 'Muy bajo' : zn < 0.38 ? 'Bajo' : zn < 0.55 ? 'Moderado' : zn < 0.75 ? 'Alto' : 'Muy alto';
    setText('kg-z-val', rLabel + (node.margin != null ? ' (' + (node.margin * 100).toFixed(0) + '% margen)' : ' (sin datos)'));
    const label  = node.label || node.ticker || node.id || '—';
    const ticker = node.ticker ? node.ticker.split(/[·\s]/)[0] : '';
    nameEl.innerHTML = '<b>' + label + '</b>' + (ticker ? '<span class="kg-ticker">· ' + ticker + '</span>' : '') + (node.cat ? '<span class="kg-cat">' + node.cat + '</span>' : '');
  }

  let _raycaster = null, _mouse3D = null, _hoveredMesh = null, _mouseCB = null;

  function setupHover(inst) {
    if (_raycaster || !window.THREE) return;
    const T = window.THREE; _raycaster = new T.Raycaster(); _mouse3D = new T.Vector2();
    const canvas = (inst.renderer && inst.renderer.domElement) || document.querySelector('canvas');
    if (!canvas) return;
    _mouseCB = (e) => {
      if (!_scatterActive) return;
      const rect = canvas.getBoundingClientRect();
      _mouse3D.x =  ((e.clientX - rect.left) / rect.width)  * 2 - 1;
      _mouse3D.y = -((e.clientY - rect.top)  / rect.height) * 2 + 1;
      const cam = inst.camera || inst._camera || (inst.controls && inst.controls.object) || null;
      if (!cam) return;
      _raycaster.setFromCamera(_mouse3D, cam);
      const meshes = []; inst.nodeMeshes.forEach(m => meshes.push(m));
      const hits = _raycaster.intersectObjects(meshes, false);
      const hit  = hits.length ? hits[0].object : null;
      if (hit !== _hoveredMesh) { _hoveredMesh = hit; updateGauges(hit ? hit.userData?.node : null); }
    };
    canvas.addEventListener('mousemove', _mouseCB);
  }

  function teardownHover(inst) {
    const canvas = (inst && inst.renderer && inst.renderer.domElement) || document.querySelector('canvas');
    if (_mouseCB && canvas) canvas.removeEventListener('mousemove', _mouseCB);
    _raycaster = null; _mouse3D = null; _mouseCB = null; _hoveredMesh = null;
  }

  let _scatterActive = false, _axisGroup = null, _savedPositions = new Map();

  function activateScatter(inst) {
    _scatterActive = true;
    _savedPositions.clear();
    inst.nodeMeshes.forEach((mesh) => {
      const node = mesh.userData?.node; if (!node) return;
      _savedPositions.set(mesh, mesh.position.clone());
      const p = semXYZ(node); mesh.position.set(p.x, p.y, p.z);
    });
    const T = window.THREE, HALF = SPREAD * 0.58;
    _axisGroup = new T.Group();
    [{d:[1,0,0],c:0x4fc3f7,lo:'◀ Hoy',hi:'Largo plazo ▶'},
     {d:[0,1,0],c:0xa5d6a7,lo:'▼ Micro-cap',hi:'▲ Mega-cap'},
     {d:[0,0,1],c:0xff8a65,lo:'● Bajo riesgo',hi:'● Alto riesgo'}
    ].forEach(({d,c,lo,hi}) => {
      const mat = new T.LineBasicMaterial({color:c,transparent:true,opacity:0.75});
      const geo = new T.BufferGeometry().setFromPoints([new T.Vector3(...d.map(v=>v*-HALF)),new T.Vector3(...d.map(v=>v*HALF))]);
      _axisGroup.add(new T.Line(geo,mat));
    });
    inst.scene.add(_axisGroup);
    createPanel(); setupHover(inst);
  }

  function deactivateScatter(inst) {
    _scatterActive = false;
    _savedPositions.forEach((pos, mesh) => mesh.position.copy(pos)); _savedPositions.clear();
    // restaurar opacidad/visibilidad por si había un filtro activo
    inst.nodeMeshes.forEach(mesh => { if (mesh.material) mesh.material.opacity = 0.9; (mesh.children || []).forEach(ch => ch.visible = true); });
    if (inst.setAllHalos) inst.setAllHalos(1);   // restaurar la nube GPU de halos
    if (_axisGroup) { inst.scene.remove(_axisGroup); _axisGroup = null; }
    teardownHover(inst);
    const panel = document.getElementById('kg-panel'); if (panel) panel.remove();
  }

  function getInst() {
    return window._khipu3DInstance || Object.values(window).find(v => v && typeof v === 'object' && v.constructor?.name === 'KhipuGraph3D' && v.active);
  }

  function _toggle(inst, btn) {
    if (_scatterActive) { deactivateScatter(inst); btn.style.background = ''; btn.style.color = ''; btn.title = 'Activar Scatter 3D'; }
    else { activateScatter(inst); btn.style.background = 'var(--accent, #4fc3f7)'; btn.style.color = '#000'; btn.title = 'Desactivar Scatter 3D'; }
  }

  function insertButton() {
    if (document.getElementById('scatter-3d-btn')) return;
    const btn3d = document.getElementById('toggle-3d-btn'); if (!btn3d) return;
    const btn = document.createElement('button');
    btn.id = 'scatter-3d-btn'; btn.className = 'icon-btn'; btn.title = 'Activar Scatter 3D semántico';
    btn.textContent = '📊'; btn.style.cssText = 'font-size:13px;padding:0 6px;margin-left:2px;';
    btn.addEventListener('click', () => {
      const inst = getInst();
      if (!inst || !inst.active) {
        window._toggle3D && window._toggle3D();
        let tries = 0;
        const poll = setInterval(() => { const i2 = getInst(); if ((i2 && i2.active) || ++tries > 40) { clearInterval(poll); if (i2 && i2.active) _toggle(i2, btn); } }, 150);
        return;
      }
      _toggle(inst, btn);
    });
    btn3d.insertAdjacentElement('afterend', btn);
  }

  if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', insertButton); }
  else {
    const obs = new MutationObserver(() => { if (document.getElementById('toggle-3d-btn')) { obs.disconnect(); insertButton(); } });
    obs.observe(document.body, {childList:true, subtree:true}); insertButton();
  }

  window._khipuScatter = { activate: activateScatter, deactivate: deactivateScatter, getInst, isActive: () => _scatterActive };
})();
