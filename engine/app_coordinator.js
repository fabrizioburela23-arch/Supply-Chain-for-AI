
// ── Khipu Core Coordinator ──────────────────────────────────────
(function initKhipuCore() {
  'use strict';

  // 2D/3D toggle
  let _is3D = false;
  let _graph3d = null;
  let _hypergraph = null;
  let _secondBrain = null;

  // ── Diagnóstico remoto: beacons técnicos (GPU/WebGL/errores) para poder
  // depurar "no pasa nada" sin ver la pantalla del usuario. Máx 8 por sesión.
  let _diagCount = 0;
  window._diag = function (kind, data) {
    try {
      if (_diagCount++ > 8) return;
      fetch('/api/diag', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kind, ver: window._appVersion ? 'v' + window._appVersion : 'v?', ua: navigator.userAgent, data: data || {} }),
      }).catch(() => {});
    } catch (e) {}
  };

  // ── HUD de VISTA del 3D: [🕸 Cadena] [🎯 Inversión] ──────────────────────
  // El Scatter de inversión YA NO se auto-activa (escondía nodos sin datos de
  // mercado — feedback real "no se ven todos"). Ahora es una LENTE opcional.
  function _ensure3DModeHUD() {
    let hud = document.getElementById('g3d-mode');
    if (hud) return hud;
    hud = document.createElement('div');
    hud.id = 'g3d-mode';
    hud.style.cssText = 'position:absolute;top:14px;right:14px;z-index:9;display:flex;gap:6px;' +
      'background:rgba(8,12,22,.82);border:1px solid rgba(80,130,200,.3);border-radius:10px;padding:5px;backdrop-filter:blur(8px)';
    const mk = (id, txt, title) => `<button id="${id}" title="${title}" style="border:none;cursor:pointer;font-size:11px;font-weight:700;` +
      `padding:5px 12px;border-radius:7px;background:transparent;color:#9bb;transition:all .13s;font-family:inherit">${txt}</button>`;
    hud.innerHTML = mk('g3d-mode-chain', '🕸 Cadena', 'Vista semántica: TODAS las empresas (X=cadena de valor, Y=riesgo, Z=región)') +
                    mk('g3d-mode-invest', '🎯 Inversión', 'Lente de inversión: tiempo al mercado × tamaño × riesgo (con filtros)');
    document.querySelector('.graph-wrap')?.appendChild(hud);
    const paint = (investOn) => {
      const c = document.getElementById('g3d-mode-chain'), i = document.getElementById('g3d-mode-invest');
      if (c) { c.style.background = investOn ? 'transparent' : 'rgba(0,224,255,.18)'; c.style.color = investOn ? '#9bb' : '#00E0FF'; }
      if (i) { i.style.background = investOn ? 'rgba(79,195,247,.2)' : 'transparent'; i.style.color = investOn ? '#4fc3f7' : '#9bb'; }
    };
    document.getElementById('g3d-mode-chain').onclick = () => {
      try {
        if (window._khipuScatter?.isActive()) window._khipuScatter.deactivate(_graph3d);
        // volver al layout semántico con TODO visible
        _graph3d._staticLayout(window.NODES || []);
        _graph3d._updateLinkPositions();
        _graph3d._clearChainHighlight && _graph3d._clearChainHighlight();
      } catch (e) {}
      paint(false);
    };
    document.getElementById('g3d-mode-invest').onclick = () => {
      try { if (window._khipuScatter && !window._khipuScatter.isActive()) window._khipuScatter.activate(_graph3d); } catch (e) {}
      paint(true);
    };
    paint(false);
    return hud;
  }

  // Motor WebGL viejo (engine/graph3d.js + engine/hypergraph.js, ~1.500 líneas): solo lo usa el camino
  // ?webgl3d=1, así que se descarga AL PEDIRLO (limpieza 2026-10-11: antes se cargaba en cada arranque).
  let _legacy3D = null;
  function _loadLegacy3D() {
    if (window.KhipuGraph3D && window.TemporalHypergraph) return Promise.resolve();
    if (_legacy3D) return _legacy3D;
    const one = (src) => new Promise((ok, ko) => {
      const el = document.createElement('script'); el.src = src; el.onload = ok; el.onerror = () => ko(new Error(src));
      document.head.appendChild(el);
    });
    _legacy3D = one('engine/graph3d.js').then(() => one('engine/hypergraph.js')).catch((e) => { _legacy3D = null; throw e; });
    return _legacy3D;
  }
  window._toggle3D = function() {
    _loadLegacy3D().then(_toggle3DSafe, (e) => {
      if (typeof toast === 'function') toast((typeof LANG !== 'undefined' && LANG === 'en' ? '⚠ Could not load the 3D: ' : '⚠ No se pudo cargar el 3D: ') + (e.message || e));
    });
  };
  function _toggle3DSafe() {
    try {
      _toggle3DInner();
    } catch (e) {
      // si el 3D falla en ESTE dispositivo, el usuario debe saberlo — no
      // quedarse mirando una pantalla que "directamente no da" (feedback real)
      _is3D = false;
      if (typeof toast === 'function') toast((typeof LANG !== 'undefined' && LANG === 'en' ? '⚠ The 3D could not start: ' : '⚠ El 3D no pudo iniciar: ') + (e.message || e));
      console.error('[3D]', e);
    }
  };

  // Respaldo TOTAL sin WebGL (engine/universe2d.js): si el 3D real no puede
  // pintar en ESTE equipo, el universo se dibuja igual en Canvas 2D dentro
  // del mapa (usado SOLO por el camino legado WebGL bajo ?webgl3d=1).
  function _startUniverse2D(reason) {
    if (!window.KhipuUniverse2D) return false;
    try {
      if (_graph3d && _graph3d.pause) _graph3d.pause();
      const svg2 = document.getElementById('graph');
      const cnv2 = document.getElementById('graph-canvas');
      if (svg2) svg2.style.display = 'none';
      if (cnv2) cnv2.style.display = 'block';
      window.KhipuUniverse2D.init('graph-canvas');
      window.KhipuUniverse2D.loadData(window.NODES || [], window.LINKS || []);
      window._diag && window._diag('universe2d_fallback', { reason: String(reason || '').slice(0, 60) });
      return true;
    } catch (e) {
      window._diag && window._diag('universe2d_fail', { err: String(e && e.message || e).slice(0, 120) });
      return false;
    }
  }

  // ── Universo en PANTALLA COMPLETA (fix definitivo 2026-07-13) ──────────────
  // El bug repetido "el 3D no da": el canvas vivía DENTRO de <main>, que se
  // ocultaba al cambiar de pestaña → canvas 0×0 → pantalla negra. La cura:
  // un overlay position:fixed que SIEMPRE tiene tamaño real de ventana, con su
  // propio canvas, independiente del SVG / pestañas / WebGL. No puede medir 0.
  function _ensureUniverseOverlay() {
    let ov = document.getElementById('uni-ov');
    if (ov) return ov;
    const en = (window.LANG === 'en');
    ov = document.createElement('div');
    ov.id = 'uni-ov';
    ov.style.cssText = 'position:fixed;inset:0;z-index:9500;display:none;background:#05070e';
    ov.innerHTML =
      '<canvas id="uni-canvas" style="position:absolute;inset:0;width:100%;height:100%;display:block"></canvas>' +
      '<div style="position:absolute;top:14px;left:16px;z-index:2;pointer-events:none;font-family:Inter,system-ui,sans-serif">' +
        '<div style="font-size:13px;font-weight:750;color:#E8EDFB;letter-spacing:.02em">🪐 ' +
          (en ? 'Universe' : 'Universo') + '</div>' +
        '<div style="font-size:10.5px;color:#7C87A3;margin-top:2px">' +
          (en ? '555 companies · click to light up a chain' : '555 empresas · clic para iluminar una cadena') + '</div></div>' +
      '<button id="uni-close" title="' + (en ? 'Close' : 'Cerrar') + '" ' +
        'style="position:absolute;top:12px;right:14px;z-index:3;width:38px;height:38px;border-radius:10px;cursor:pointer;' +
        'border:1px solid rgba(122,158,255,.3);background:rgba(11,18,34,.9);color:#E8EDFB;font-size:18px;line-height:1">✕</button>';
    document.body.appendChild(ov);
    ov.querySelector('#uni-close').onclick = _closeUniverse;
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && ov.style.display !== 'none') _closeUniverse();
    });
    return ov;
  }

  function _closeUniverse() {
    try { if (window.KhipuUniverse2D) window.KhipuUniverse2D.destroy(); } catch (e) {}
    const ov = document.getElementById('uni-ov');
    if (ov) ov.style.display = 'none';
    _is3D = false;
    const chip = document.getElementById('tab-3d');
    if (chip) chip.classList.remove('active');
  }

  function _openUniverse() {
    const ov = _ensureUniverseOverlay();
    ov.style.display = 'block';
    _is3D = true;
    const chip = document.getElementById('tab-3d');
    if (chip) chip.classList.add('active');
    // dos frames para que el overlay tenga layout (tamaño real) antes de init
    requestAnimationFrame(function () { requestAnimationFrame(function () {
      let ok = false;
      try {
        ok = window.KhipuUniverse2D && window.KhipuUniverse2D.init('uni-canvas');
        if (ok) {
          window.KhipuUniverse2D.loadData(window.NODES || [], window.LINKS || []);
          // primer pintado inmediato (sin esperar a rAF → sin flash negro)
          if (window.KhipuUniverse2D.redraw) window.KhipuUniverse2D.redraw();
        }
      } catch (e) {
        window._diag && window._diag('universe_fail', { err: String(e && e.message || e).slice(0, 120) });
      }
      window._diag && window._diag('universe_open', { ok: !!ok, w: ov.clientWidth, h: ov.clientHeight });
      if (!ok) {
        _closeUniverse();
        if (typeof toast === 'function') toast(window.LANG === 'en'
          ? '⚠ The universe could not draw. Reload the page and try again.'
          : '⚠ El universo no pudo dibujarse. Recarga la página e inténtalo de nuevo.');
      }
    }); });
  }

  function _toggle3DInner() {
    _is3D = !_is3D;
    const svg = document.getElementById('graph');
    const canvas = document.getElementById('graph-canvas');
    const timeline = document.getElementById('hypergraph-timeline');
    const legend3d = document.getElementById('graph3d-legend');
    const chip = document.getElementById('tab-3d');
    if (chip) chip.classList.toggle('active', _is3D);
    const zbtn = document.getElementById('zoom-3d');
    if (zbtn) { zbtn.style.background = _is3D ? 'var(--violet,#8e5aff)' : ''; zbtn.style.color = _is3D ? '#fff' : ''; }
    if (_is3D) {
      svg.style.display = 'none';
      canvas.style.display = 'block';
      timeline.style.display = 'flex';
      if (legend3d) legend3d.style.display = 'block';
      _ensure3DModeHUD().style.display = 'flex';
      if (!_graph3d && window.KhipuGraph3D) {
        // Show loading overlay while Three.js initializes
        const g3dLdr = document.getElementById('graph3d-loader');
        if (g3dLdr) { g3dLdr.style.display = 'flex'; g3dLdr.classList.remove('hidden'); }
        setTimeout(() => {
          // HUECO REAL tapado (feedback "no pasa nada"): si WebGLRenderer
          // revienta aquí (aceleración de hardware apagada, GPU bloqueada),
          // este setTimeout quedaba SIN protección → cargador girando para
          // siempre, sin aviso. Ahora: aviso claro + beacon + volver al 2D.
          try {
            _graph3d = new KhipuGraph3D('graph-canvas');
            _graph3d.init();
            _graph3d.loadData(window.NODES || [], window.LINKS || []);
            // The hypergraph was constructed before _graph3d existed (it captured
            // null), so re-point its graph reference before draining the queue —
            // otherwise renderPending() dereferences a null scene and no hyperedge
            // spheres ever appear.
            if (_hypergraph) _hypergraph.graph3d = _graph3d;
            _hypergraph?.renderPending();
            window.khipuGraph3D = _graph3d;
            if (window._secondBrain) window._secondBrain.graph3d = _graph3d;
            else if (window.SecondBrain) { window._secondBrain = new SecondBrain(_graph3d); }
            window._diag && window._diag('3d_init_ok', { nodes: _graph3d.nodeMeshes.size });
            // Pantalla negra detectada por _selfCheck → escalar al universo 2D
            // (el modo ultra-seguro del 3D es el último peldaño WebGL; si aun
            // así no se ve, el 2D SIEMPRE se ve).
            try {
              const _origUltra = _graph3d._ultraSafeMode.bind(_graph3d);
              _graph3d._ultraSafeMode = (r) => {
                try { _origUltra(r); } catch (e2) {}
                _startUniverse2D('3d_black:' + (r || ''));
              };
            } catch (e3) {}
            // Hide loader once first frame is likely rendered (~600ms)
            setTimeout(() => {
              if (g3dLdr) { g3dLdr.classList.add('hidden'); setTimeout(() => { g3dLdr.style.display = 'none'; }, 450); }
            }, 600);
          } catch (e) {
            window._diag && window._diag('3d_init_fail', { err: String(e && e.message || e).slice(0, 180) });
            _graph3d = null;
            if (g3dLdr) { g3dLdr.classList.add('hidden'); g3dLdr.style.display = 'none'; }
            // el motor WebGL no pudo — pero el universo 2D SIEMPRE puede
            if (_startUniverse2D('3d_init_fail')) return;
            if (typeof toast === 'function') {
              toast('⚠ El 3D no pudo iniciar en este equipo: ' + String(e && e.message || e).slice(0, 90) +
                    ' — En Chrome: Configuración → Sistema → activa "aceleración de gráficos".');
            }
            if (_is3D) _toggle3DInner();   // volver al 2D limpio
          }
        }, 50); // brief yield so spinner renders before heavy work
      } else if (_graph3d) {
        _graph3d.resume && _graph3d.resume();
        if (window.KhipuUniverse2D && window.KhipuUniverse2D.isActive()) window.KhipuUniverse2D.resume();
      }
      if (!_hypergraph && window.TemporalHypergraph) {
        _hypergraph = new TemporalHypergraph(_graph3d);
        _hypergraph.seedHistoricalEvents();
        window._hypergraph = _hypergraph; // expose for GDELT auto-hyperedge
      }
    } else {
      svg.style.display = '';
      canvas.style.display = 'none';
      timeline.style.display = 'none';
      if (legend3d) legend3d.style.display = 'none';
      const hud = document.getElementById('g3d-mode');
      if (hud) hud.style.display = 'none';
      if (_graph3d) _graph3d.pause && _graph3d.pause();
      try { if (window.KhipuUniverse2D) window.KhipuUniverse2D.pause(); } catch (e) {}
      try {
        if (window._khipuScatter && window._khipuScatter.isActive()) window._khipuScatter.deactivate(_graph3d);
      } catch (e) {}
    }
  };

  // El botón 🪐 Universo abre un OVERLAY a pantalla completa (position:fixed),
  // que SIEMPRE tiene tamaño real → jamás pantalla negra por canvas 0×0.
  // FIX 2026-07-13: antes el canvas vivía dentro de <main> y medía 0 cuando la
  // pestaña estaba oculta — causa raíz de "el 3D no da". El motor WebGL
  // (graph3d.js) queda accesible solo con ?webgl3d=1 en la URL.
  window._go3D = function() {
    window._diag && window._diag('3d_click', { is3D: _is3D, tab: (typeof activeTab !== 'undefined' ? activeTab : '?') });
    // camino legado WebGL, solo bajo bandera explícita
    let wantWebGL = false;
    try { wantWebGL = new URLSearchParams(location.search).get('webgl3d') === '1'; } catch (e) {}
    if (wantWebGL) {
      if (typeof activeTab !== 'undefined' && activeTab !== 'map' && typeof switchTab === 'function') switchTab('map');
      window._toggle3D();
      return;
    }
    const ov = document.getElementById('uni-ov');
    if (ov && ov.style.display !== 'none') { _closeUniverse(); return; }  // segundo toque = cerrar
    _openUniverse();
  };

  // Hypergraph timeline slider
  document.addEventListener('DOMContentLoaded', function() {
    const slider = document.getElementById('hg-year');
    const label = document.getElementById('hg-year-label');
    if (slider) {
      slider.addEventListener('input', function() {
        label.textContent = this.value;
        const yr = +this.value;
        if (label) label.textContent = yr >= (+slider.max||2030) ? 'HOY' : String(yr);
        if (_hypergraph && _hypergraph.setTimelinePosition) {
          const pos = (yr - (+slider.min||2015)) / ((+slider.max||2030) - (+slider.min||2015));
          _hypergraph.setTimelinePosition(Math.max(0, Math.min(1, pos)));
        }
      });
    }
    const hgAdd = document.getElementById('hg-add');
    if (hgAdd) {
      hgAdd.addEventListener('click', async function() {
        const year = +(document.getElementById('hg-year')?.value || 2026);
        const KT = window.KhipuToast; if (!KT || !KT.prompt) return;
        const en = (typeof LANG !== 'undefined' && LANG === 'en');
        const name = await KT.prompt({ title: en ? 'New hyperedge event' : 'Nuevo evento hipervínculo', label: en ? 'Event name' : 'Nombre del evento' });
        if (!name) return;
        const nodeIds = await KT.prompt({ title: name, label: en ? 'Affected node ids (comma-separated)' : 'IDs de nodos afectados (separados por coma)' });
        if (!nodeIds) return;
        if (_hypergraph) {
          _hypergraph.addEvent({ id: 'evt_' + Date.now(), name, year, nodes: nodeIds.split(',').map(s => s.trim()), type: 'custom' });
        }
      });
    }
    const hgToggle = document.getElementById('hg-toggle');
    if (hgToggle) {
      hgToggle.addEventListener('click', function() {
        const tl = document.getElementById('hypergraph-timeline');
        if (tl) tl.style.display = 'none';
      });
    }

    // Second Brain init
    if (window.SecondBrain) {
      _secondBrain = new SecondBrain(_graph3d);
      window._secondBrain = _secondBrain;
    }
  });

  // Hook into renderDetail to add NRS badge + Second Brain button
  const _origRender = window.renderDetail;
  if (typeof _origRender === 'function') {
    window.renderDetail = function(id) {
      _origRender(id);
      // NRS badge
      try {
        const nrs = computeNRS(id);
        let existing = document.getElementById('khipu-nrs-badge');
        if (!existing) {
          existing = document.createElement('div');
          existing.id = 'khipu-nrs-badge';
          existing.style.cssText = 'margin:8px 0;padding:8px 12px;border-radius:6px;border:1px solid var(--line);background:var(--surface-2);display:flex;flex-wrap:wrap;align-items:center;gap:8px 10px;font-size:12px';
          const detail = document.getElementById('detail');
          if (detail) detail.insertBefore(existing, detail.firstChild);
        }
        const color = nrs < 30 ? '#22c55e' : nrs < 60 ? '#f59e0b' : '#ef4444';
        const mkt = (window.NODE_BY_ID||{})[id]?.mkt || '';
        const nrsLbl = LANG==='en' ? (nrs<30?'Low risk':nrs<60?'Medium risk':'High risk') : (nrs<30?'Bajo riesgo':nrs<60?'Riesgo medio':'Riesgo alto');
        existing.innerHTML = `<span style="font-weight:700;color:var(--ink)">NRS</span><span style="font-size:16px;font-weight:800;color:${color}">${nrs}</span><span style="color:var(--ink-3)">/ 100</span>${window.explainChip?window.explainChip('nrs'):''}<span style="margin-left:auto;font-size:10px;color:var(--ink-3)">${nrsLbl}</span><button onclick="window._openSecondBrain&&window._openSecondBrain('${id}')" style="margin-left:8px;padding:3px 10px;border:1px solid var(--violet);border-radius:4px;background:none;color:var(--violet);cursor:pointer;font-size:11px;font-weight:600">🧠 Second Brain</button><button onclick="window.openFinCard?(window._surface?window._surface('dossier','${id}'):window.openFinCard('${id}')):(window._openDossier&&window._openDossier('${id}','${mkt}'))" title="${LANG==='en'?(mkt?'Dossier: live price, market cap, employees, revenue + yearly financials':'Dossier: profile, owner quote and live news'):(mkt?'Dossier: precio, capitalización, empleados e ingresos en vivo + estados anuales':'Dossier: ficha, cotización del dueño y noticias en vivo')}" style="margin-left:4px;padding:3px 10px;border:1px solid var(--blue);border-radius:4px;background:none;color:var(--blue);cursor:pointer;font-size:11px;font-weight:600">📊 Dossier</button>${mkt ? `<button onclick="window._openResearch&&window._openResearch('${mkt}','${id}')" style="margin-left:4px;padding:3px 10px;border:1px solid #34d399;border-radius:4px;background:none;color:#34d399;cursor:pointer;font-size:11px;font-weight:600">📄 SEC</button>` : ''}`;
      } catch(e) {}
    };
  }

  // Open Second Brain panel
  window._openSecondBrain = function(nodeId) {
    const panel = document.getElementById('second-brain-panel');
    if (!panel) return;
    panel.style.display = 'block';
    const nameEl = document.getElementById('sb-company-name');
    const n = window.NODE_BY_ID && window.NODE_BY_ID[nodeId];
    if (nameEl) nameEl.textContent = n ? n.label : nodeId;
    if (window._secondBrain) window._secondBrain.showNodeLayers(nodeId);
  };

  // Expose NRS globally for Khipu y los motores de simulación
  window.computeNRS = computeNRS;
  // Expose quote loader so the Grafo Temporal / ontología puede precargar precios en vivo
  if (typeof fetchQuotes === 'function') window.fetchQuotes = fetchQuotes;
  if (typeof catLabel === 'function') window.catLabel = catLabel;

})();

// ── GDELT News Search ─────────────────────────────────────────────────────────
let _gdeltInited = false;
function initGdelt() {
  if (_gdeltInited) return;
  _gdeltInited = true;
  const btn = document.getElementById('gdelt-search');
  const inp = document.getElementById('gdelt-query');
  const out = document.getElementById('gdelt-results');
  if (!btn || !inp || !out) return;
  async function doSearch() {
    const q = inp.value.trim();
    if (!q) return;
    // Save to history
    const _hist = JSON.parse(localStorage.getItem('gdelt_history') || '[]');
    if (!_hist.includes(q)) { _hist.unshift(q); localStorage.setItem('gdelt_history', JSON.stringify(_hist.slice(0,10))); }
    out.innerHTML = '<span style="color:var(--ink-3)">Buscando…</span>';
    try {
      const r = await fetch('/api/news/gdelt/' + encodeURIComponent(q));
      if (!r.ok) throw new Error(r.statusText);
      const data = await r.json();
      const articles = data.articles || data.results || [];
      if (!articles.length) { out.innerHTML = '<span style="color:var(--ink-3)">Sin resultados para "'+esc(q)+'"</span>'; return; }
      out.innerHTML = articles.slice(0, 8).map(a => {
        const title = esc(a.title || a.url || 'Artículo');
        const src = esc(a.domain || a.source || '');
        const ts = a.seendate ? new Date(a.seendate.replace(/(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z/,'$1-$2-$3T$4:$5:$6Z')).toLocaleDateString('es-ES',{day:'numeric',month:'short'}) : '';
        const url = safeUrl(a.url);
        return `<div style="padding:7px 0;border-bottom:1px solid var(--line)"><a href="${url}" target="_blank" rel="noopener noreferrer" style="color:var(--violet);font-size:12px;font-weight:600;text-decoration:none">${title}</a><div style="font-size:10px;color:var(--ink-3);margin-top:2px">${src}${ts?' · '+ts:''}</div></div>`;
      }).join('');
      // Auto-create hyperedge in TemporalHypergraph if 3D is active
      if (window._hypergraph && articles.length >= 2) {
        const affectedNodes = [];
        (window.NODES || []).forEach(n => {
          const needle = (n.label || '').toLowerCase();
          const hasHit = articles.slice(0, 5).some(a => (a.title || '').toLowerCase().includes(needle) || needle.length > 4 && (a.title||'').toLowerCase().includes(needle.slice(0,5)));
          if (hasHit) affectedNodes.push(n.id);
        });
        if (affectedNodes.length >= 2) {
          const topArticle = articles[0];
          window._hypergraph.fromNewsItem(
            { headline: topArticle.title, summary: topArticle.title, url: topArticle.url, datetime: Date.now()/1000 },
            affectedNodes.slice(0, 15)
          );
        }
      }
    } catch(e) {
      out.innerHTML = '<span style="color:var(--danger)">Error: '+esc(e.message)+'</span>';
    }
  }
  btn.addEventListener('click', doSearch);
  inp.addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });
  // Load saved searches
  const _gdeltHistory = JSON.parse(localStorage.getItem('gdelt_history') || '[]');
  if (_gdeltHistory.length) {
    const hist = document.createElement('div');
    hist.style.cssText = 'display:flex;flex-wrap:wrap;gap:4px;margin-bottom:8px';
    hist.innerHTML = _gdeltHistory.slice(0,5).map(h => `<button onclick="document.getElementById('gdelt-query').value=${esc(JSON.stringify(String(h)))};initGdelt&&document.getElementById('gdelt-search').click()" style="padding:2px 8px;border:1px solid var(--line);border-radius:10px;background:var(--surface-2);font-size:10px;cursor:pointer;color:var(--ink-3)">${esc(h)}</button>`).join('');
    out.parentElement.insertBefore(hist, out);
  }
}
window.initGdelt = initGdelt;

// ── NRS Top 10 ───────────────────────────────────────────────────────────────
function renderNrsTop10() {
  const el = document.getElementById('nrs-top-list');
  if (!el) return;
  try {
    const scored = (window.NODES || []).map(n => {
      try { return { n, v: computeNRS(n.id) }; } catch(e) { return null; }
    }).filter(Boolean).sort((a, b) => b.v - a.v).slice(0, 10);
    if (!scored.length) { el.innerHTML = '<span style="color:var(--ink-3)">Sin datos de riesgo</span>'; return; }
    el.innerHTML = scored.map((item, i) => {
      const { n, v } = item;
      const color = v >= 70 ? '#ef4444' : v >= 50 ? '#f59e0b' : '#22c55e';
      const bar = Math.round(v);
      return `<div style="display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid var(--line);cursor:pointer" onclick="switchTab('map');setTimeout(()=>jumpTo('${n.id}'),80)">
        <span style="font-size:10px;color:var(--ink-3);width:14px;text-align:right">${i+1}</span>
        <span style="font-weight:600;font-size:12px;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(n.label)}</span>
        <div style="width:60px;height:6px;background:var(--surface-2);border-radius:3px;overflow:hidden"><div style="width:${bar}%;height:100%;background:${color};border-radius:3px"></div></div>
        <span style="font-weight:700;font-size:12px;color:${color};min-width:24px;text-align:right">${bar}</span>
      </div>`;
    }).join('');
  } catch(e) { el.innerHTML = '<span style="color:var(--ink-3)">Calculando…</span>'; }
}
window.renderNrsTop10 = renderNrsTop10;

// ── Simulation Tab ───────────────────────────────────────────────────────────
let _simInited = false;

function _simSetStatus(status, text, color) {
  status.textContent = text;
  const bg = { violet:'rgba(155,79,232,.1)', green:'rgba(34,197,94,.1)', red:'rgba(214,59,59,.1)', gray:'var(--surface-2)' };
  const fg = { violet:'var(--violet)', green:'#22c55e', red:'var(--danger)', gray:'var(--ink-3)' };
  status.style.background = bg[color]||bg.gray;
  status.style.color = fg[color]||fg.gray;
}

// Ancla del motor de matrices: si el preset tiene factorId (Factor REAL de la
// ontología), lo dispara como what-if (/api/matrix/factor/fire) y muestra el
// contagio DETERMINISTA encima de la narrativa de la IA — números contra
// relato. Presets hipotéticos (sin factorId) no muestran nada. window.* para
// ser visible desde el handler del botón (otro bloque de script).
window._simGroundFactor = async function (presetId) {
  let box = document.getElementById('sim-ground');
  const out = document.getElementById('sim-output');
  if (!box) {
    if (!out || !out.parentNode) return;
    box = document.createElement('div');
    box.id = 'sim-ground';
    out.parentNode.insertBefore(box, out);
  }
  const fid = presetId && window.ScenarioBuilder?.PRESETS?.[presetId]?.factorId;
  if (!fid) { box.innerHTML = ''; return; }
  const h = s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  box.innerHTML = `<div style="margin:0 0 10px;padding:9px 12px;border:1px solid var(--line);border-radius:8px;background:var(--surface);font-size:12px;color:var(--ink-3)">📐 Anclando con el motor de matrices…</div>`;
  try {
    const r = await fetch((typeof BASE !== 'undefined' ? BASE : '') + '/api/matrix/factor/fire', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ factor_id: fid })
    }).then(x => x.json());
    if (!r || r.error) { box.innerHTML = ''; return; }
    const top = (r.top_contagio || []).slice(0, 6).map(t => `<b>${h(t.id)}</b> ${t.impact}%`).join(' · ');
    const estab = r.rho && r.rho.estable_en_crisis === false ? '⚠ régimen supercrítico' : 'estable';
    box.innerHTML = `<div style="margin:0 0 10px;padding:10px 12px;border:1px solid var(--line);border-left:3px solid var(--violet);border-radius:8px;background:var(--surface);font-size:12px;line-height:1.65">
      <b>📐 Ancla del motor de matrices</b> — factor real disparado: <b>${h(r.factor.label)}</b> (severidad ${h(r.factor.severity_crisis)}/${h(r.factor.severity_scale || 5)})<br>
      Contagio determinista, sin IA: alcanza <b>${r.affected}</b> empresas · ${top}<br>
      ρ(T) en crisis: ${h(r.rho && r.rho.crisis)} (${estab}). Contrasta la narrativa de abajo con estos números.</div>`;
  } catch (e) { box.innerHTML = ''; }
};

// Motor multi-agente INTERNO (core/sim_agents.py vía POST /api/sim/agents):
// cada empresa relevante es un agente, más agentes externos (gobiernos,
// reguladores), y debaten el escenario. Sustituye al pipeline de MiroFish —
// mismo rol, sin microservicio externo. Devuelve true si logró pintar el
// War-Room; false para que el llamador caiga al motor narrativo.
async function _runAgentSimTab(text, presetId, output, status) {
  const en = (window.LANG === 'en');
  _simSetStatus(status, en ? '🧬 Convening agents…' : '🧬 Convocando agentes…', 'violet');
  _renderWarRoom({
    scenarioTitle: text.slice(0, 70),
    nodeImpacts: {}, priceTrajs: {}, cascadeNodes: [],
    reportText: en ? 'Agents are debating the scenario…' : 'Los agentes están debatiendo el escenario…',
    reportId: null, simId: null, presetId,
  });
  try {
    // Semillas: los nodos que el escenario menciona (las resuelve el server si
    // van vacías). Reusamos el mismo resolutor que todo lo demás.
    let seeds = [];
    try {
      if (window.KhipuResolve && window.NODES) {
        seeds = text.split(/[\s,.;:()]+/).map(w => w.trim()).filter(w => w.length > 2)
          .map(w => { const r = window.KhipuResolve.find(w); return (r && r.node && r.score >= 70) ? r.node.id : null; })
          .filter(Boolean);
        seeds = [...new Set(seeds)].slice(0, 12);
      }
    } catch (e) { seeds = []; }

    const r = await fetch((typeof BASE !== 'undefined' ? BASE : '') + '/api/sim/agents', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(Object.assign({ scenario: text, seeds, lang: en ? 'en' : 'es' }, (() => {
        // tu cartera (valor en USD por posición) → «tu cartera en este escenario» del informe completo
        try { const mp = window.KhipuHot && window.KhipuHot.myPositions ? window.KhipuHot.myPositions() : null;
          return mp && mp.positions && mp.positions.length ? { positions: mp.positions.slice(0, 60) } : {}; } catch (e) { return {}; }
      })())),
    });
    const d = await r.json().catch(() => null);
    if (d && d.ok && d.no_seeds) {
      // el escenario no nombra empresas: se dice, no se inventa un elenco
      _renderWarRoom({ scenarioTitle: text.slice(0, 70), nodeImpacts: {}, priceTrajs: {}, cascadeNodes: [],
        reportText: d.narrative || '', reportId: null, simId: null, presetId: null, impactSource: 'none' });
      const rep = document.getElementById('wr-report'); if (rep && rep.parentElement) rep.parentElement.open = true;
      _simSetStatus(status, en ? 'ℹ️ Name at least one company' : 'ℹ️ Nombra al menos una empresa', 'violet');
      return true;
    }
    if (d && d.ok && d.fallback && Array.isArray(d.seeds) && d.seeds.length) {
      // sin IA: motor ESTRUCTURAL del cliente (severidad 0-100) desde las semillas
      _renderWarRoom({ scenarioTitle: text.slice(0, 70), nodeImpacts: {}, priceTrajs: {}, cascadeNodes: d.seeds,
        reportText: d.narrative || '', reportId: null, simId: null, presetId, impactSource: 'structural' });
      _simSetStatus(status, en ? '✅ Structural simulation (no AI)' : '✅ Simulación estructural (sin IA)', 'green');
      return true;
    }
    if (!r.ok || !d || d.ok === false || !Array.isArray(d.impacts) || !d.impacts.length) return false;

    // El motor devuelve pct CON SIGNO (− pierde valor, + gana). El War-Room usa
    // la convención "daño positivo" → se invierte el signo (antes quedaban
    // ganadores y perdedores al revés).
    const nodeImpacts = {};
    d.impacts.forEach(i => { if (i && i.id != null && isFinite(+i.pct)) nodeImpacts[i.id] = -(+i.pct); });
    // cascadeNodes espera ids ordenados por magnitud (ya vienen así del server)
    const cascadeNodes = d.impacts.map(i => i.id).filter(Boolean).slice(0, 40);

    const roster = Array.isArray(d.agents) && d.agents.length
      ? (en ? `\n\nAGENTS (${d.agents.length}): ` : `\n\nAGENTES (${d.agents.length}): `) +
        d.agents.slice(0, 12).map(a => a.label || a.id).join(', ')
      : '';
    _renderWarRoom({
      scenarioTitle: text.slice(0, 70),
      nodeImpacts, priceTrajs: {}, cascadeNodes,
      reportText: (d.narrative || '') + roster,
      reportId: null, simId: null, presetId,
      impactSource: 'agents',
      debate: { rounds: d.rounds || [], impacts: d.impacts || [], model: d.model || '' },
    });
    // informe completo (engine/simreport.js): cifras clave, tu cartera, sectores, tabla con datos en vivo, metodología
    try {
      const rep = document.getElementById('wr-report');
      if (rep && window.KhipuSimReport && d.report) {
        d.scenario = d.scenario || text;
        rep.style.whiteSpace = 'normal';
        rep.innerHTML = window.KhipuSimReport.render(d, en);
        window.KhipuSimReport.bind(rep, d, en, id => { try { if (window._surface) window._surface('xray', id); } catch (e) {} });
        if (rep.parentElement) rep.parentElement.open = true;
      }
    } catch (e) {}
    _simSetStatus(status, en ? '✅ Agent simulation ready' : '✅ Simulación por agentes lista', 'green');
    return true;
  } catch (e) {
    return false;
  }
}

async function _runClaudeSim(text, nodeStr, output, status) {
  _simSetStatus(status, '🔄 Analizando con Claude...', 'violet');
  // Show War-Room canvas immediately with fallback cascade while Claude thinks
  const activeBtn = document.querySelector('.sim-preset-btn[data-active="1"]');
  const presetId = activeBtn?.dataset?.preset || null;
  _renderWarRoom({
    scenarioTitle: text.slice(0, 70),
    nodeImpacts: {}, priceTrajs: {}, cascadeNodes: [],
    reportText: 'Generando análisis con Claude…', reportId: null, simId: null, presetId,
  });
  try {
    // empresas del escenario: las del preset o las que escribió el usuario → sus datos EN VIVO + geopolítica en vivo
    const _pre = presetId && window.ScenarioBuilder && ScenarioBuilder.PRESETS[presetId];
    const _ids = (_pre && _pre.nodeIds) || String(nodeStr || '').split(/[,;]\s*/).map(x => x.trim()).filter(x => x && NODE_BY_ID[x]);
    let _live = '';
    try { if (window.buildLiveReportContext) _live = await window.buildLiveReportContext(_ids.slice(0, 10)); } catch (e) { _live = ''; }
    const resp = await fetch('/api/ai/analyze', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        system: 'Eres un analista experto en cadenas de valor de semiconductores, IA y espacio. Analiza el escenario HIPOTÉTICO y proporciona: 1) Empresas más afectadas (con % de impacto ESTIMADO, rotulado como estimación), 2) Efectos dominó en la cadena de suministro, 3) Quiénes podrían beneficiarse y por qué, 4) Riesgos a vigilar. USA las cifras EN VIVO del contexto (precio, capitalización, margen, crecimiento, eventos de hoy) y cítalas; no digas que un dato no está si aparece en el contexto. NO des recomendaciones de compra, venta ni mantener. Sé específico.',
        prompt: `ESCENARIO: ${text}\nNodos relevantes: ${_ids.length ? _ids.join(', ') : (nodeStr||'toda la cadena de valor semiconductores/IA/espacio')}\n\nCONTEXTO EN VIVO:\n${_live}`,
        max_tokens: 2500, tier: 'deep'
      })
    });
    if (!resp.ok) throw new Error('API error ' + resp.status);
    const d = await resp.json();
    const reportText = d.result || d.error || 'Sin respuesta';
    // Update War-Room with Claude report
    _renderWarRoom({
      scenarioTitle: text.slice(0, 70),
      nodeImpacts: {}, priceTrajs: {}, cascadeNodes: [],
      reportText, reportId: null, simId: null, presetId,
    });
    _simSetStatus(status, '✅ War-Room Claude', 'green');
  } catch(e) {
    const reportEl = document.getElementById('wr-report');
    if (reportEl) reportEl.innerHTML = 'No se pudo ejecutar la simulación: ' + esc(e.message) +
      '.<br><br>Revisa el panel 🩺 <b>Estado del Sistema</b>: necesitas al menos una IA en verde ' +
      '(Claude, Gemini o NVIDIA). Si Claude está rojo, añade GEMINI_KEY o NVIDIA_KEY como respaldo.';
    _simSetStatus(status, '❌ Error', 'red');
  }
}

// ════════════════════════════════════════════════════════════════════════════
// WAR-ROOM DE SIMULACIÓN — 2D animated cascade visualization
// ════════════════════════════════════════════════════════════════════════════
let _wrAnimId = null;
let _wrRoundIvl = null;   // intervalo de rondas: se limpia al redibujar (antes seguía escribiendo en el badge nuevo)
// El chat del War-Room trabaja sobre el TEXTO del informe que está en pantalla.
// (Antes dependía de un reportId de MiroFish; al retirarse ese servicio el
// chat quedaba muerto, porque el motor interno nunca produce ese id.)
let _wrReportText = '';

async function _wrChatSend() {
  const input = document.getElementById('wr-chat-input');
  const log = document.getElementById('wr-chat-log');
  const msg = (input?.value || '').trim(); if (!msg) return;
  input.value = '';
  log.insertAdjacentHTML('beforeend',
    `<div style="font-size:12px;color:var(--ink-2);padding:5px 10px;background:rgba(96,165,250,.08);border-radius:6px;align-self:flex-end">${msg.replace(/</g,'&lt;')}</div>`);
  try {
    const en = (window.LANG === 'en');
    const r = await fetch((typeof BASE !== 'undefined' ? BASE : '') + '/api/ai/analyze', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        system: en
          ? 'You are an analyst discussing a supply-chain scenario report. Answer ONLY from the report below; if it does not cover the question, say so plainly instead of inventing. Be brief and concrete.'
          : 'Eres un analista comentando el informe de un escenario de cadena de suministro. Responde SOLO con lo que dice el informe de abajo; si no lo cubre, dilo claramente en vez de inventar. Sé breve y concreto.',
        prompt: `INFORME:\n${(_wrReportText || '').slice(0, 6000)}\n\nPREGUNTA: ${msg}`,
        max_tokens: 700, tier: 'fast',
      }),
    });
    const d = await r.json();
    const reply = d.result || d.error || (en ? 'No answer.' : 'Sin respuesta.');
    log.insertAdjacentHTML('beforeend',
      `<div style="font-size:12px;color:var(--ink-1);padding:5px 10px;background:var(--surface-2);border-radius:6px">${String(reply).replace(/</g,'&lt;')}</div>`);
  } catch(e) {
    log.insertAdjacentHTML('beforeend',
      `<div style="font-size:12px;color:#f87171">Error: ${e.message}</div>`);
  }
  log.scrollTop = log.scrollHeight;
}
window._wrChatSend = _wrChatSend;

// Main entry — builds War-Room UI and starts animation
function _renderWarRoom({ scenarioTitle, nodeImpacts, priceTrajs, cascadeNodes, reportText, reportId, simId, presetId, impactSource, debate }) {
  const _en = (window.LANG === 'en');
  const WL = (es, en) => _en ? en : es;
  if (_wrAnimId) { cancelAnimationFrame(_wrAnimId); _wrAnimId = null; }
  if (_wrRoundIvl) { clearInterval(_wrRoundIvl); _wrRoundIvl = null; }
  _wrReportText = reportText || '';

  const simStatus = document.getElementById('sim-status');
  if (simStatus) _simSetStatus(simStatus, '✅ War-Room activo', 'green');

  const output = document.getElementById('sim-output');
  if (!output) return;
  output.style.textAlign = 'left';
  output.style.padding = '0';

  const safeTitle = (scenarioTitle || '').replace(/</g, '&lt;').slice(0, 90);

  output.innerHTML = `
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
      <div>
        <div style="font-size:14px;font-weight:700;color:#ef4444;letter-spacing:.02em">🚨 ${WL('WAR ROOM ACTIVO','WAR ROOM ACTIVE')}</div>
        <div style="font-size:11px;color:var(--ink-3);margin-top:2px">${safeTitle}</div>
      </div>
      <div id="wr-round" style="font-size:11px;padding:4px 12px;background:rgba(155,79,232,.12);border:1px solid rgba(155,79,232,.3);border-radius:12px;color:var(--violet)">${WL('Iniciando…','Starting…')}</div>
    </div>
    <div id="wr-sim-banner" style="margin-bottom:10px;padding:8px 12px;border:1px dashed #f59e0b;border-radius:8px;background:rgba(245,158,11,.08);font-size:11.5px;color:#fbbf24;line-height:1.5">
      🧪 ${WL('SIMULACIÓN de un escenario hipotético. Los porcentajes son ESTIMACIONES del modelo, no precios reales ni recomendaciones de compra o venta.','SIMULATION of a hypothetical scenario. Percentages are model ESTIMATES, not real prices nor buy or sell recommendations.')}
      <span id="wr-src"></span>
    </div>
    <div style="display:grid;grid-template-columns:1fr 230px;gap:10px;margin-bottom:10px">
      <div style="position:relative;background:#070b14;border-radius:8px;overflow:hidden">
        <canvas id="wr-canvas"></canvas>
        <div style="position:absolute;bottom:8px;left:10px;display:flex;gap:12px;pointer-events:none">
          <span style="font-size:10px;color:#ef4444">● ${WL('Alto impacto','High impact')}</span>
          <span style="font-size:10px;color:#f97316">● ${WL('Medio','Medium')}</span>
          <span style="font-size:10px;color:#22c55e">● ${WL('Se beneficia','Benefits')}</span>
          <span style="font-size:10px;color:rgba(140,160,200,.7)">● ${WL('No afectada','Not affected')}</span>
        </div>
      </div>
      <div style="display:flex;flex-direction:column;gap:8px;overflow-y:auto;max-height:460px">
        <div id="wr-winners" style="background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:12px;font-size:12px;flex-shrink:0"></div>
        <div id="wr-prices" style="background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:12px;font-size:12px;flex-shrink:0"></div>
      </div>
    </div>
    <div style="background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:12px;margin-bottom:10px">
      <div class="wr-panel-head">💬 ${WL('Debate de los agentes (real, de esta simulación)','Agent debate (real, from this simulation)')}</div>
      <div id="wr-agents" style="display:grid;grid-template-columns:1fr 1fr;gap:6px"></div>
    </div>
    <details style="margin-bottom:10px">
      <summary style="cursor:pointer;font-size:12px;color:var(--ink-3);padding:6px 0;list-style:none;user-select:none">📄 ${WL('Ver informe completo','See full report')} ▾</summary>
      <div id="wr-report" style="font-size:12px;line-height:1.75;color:var(--ink-2);padding:12px 0;white-space:pre-wrap;border-top:1px solid var(--line);margin-top:6px"></div>
    </details>
    <div style="background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:12px">
      <div class="wr-panel-head">💬 ${WL('Chat con el informe','Chat with the report')}</div>
      <div id="wr-chat-log" style="max-height:160px;overflow-y:auto;display:flex;flex-direction:column;gap:6px;margin-bottom:8px"></div>
      <div style="display:flex;gap:6px">
        <input id="wr-chat-input" placeholder="${WL('Pregunta sobre la simulación…','Ask about the simulation…')}" style="flex:1;padding:7px 10px;border:1px solid var(--line);border-radius:6px;background:var(--surface-2);font-size:12px;font-family:inherit">
        <button onclick="_wrChatSend()" style="padding:7px 12px;background:var(--violet);color:#fff;border:none;border-radius:6px;font-size:12px;cursor:pointer;font-weight:600">${WL('Enviar','Send')}</button>
      </div>
    </div>`;

  // Set report text
  const reportEl = document.getElementById('wr-report');
  if (reportEl) reportEl.textContent = reportText || '';

  // Setup canvas
  const canvas = document.getElementById('wr-canvas');
  if (!canvas) return;
  const parentW = canvas.parentElement.clientWidth || 640;
  const canvasH = Math.round(parentW * 0.56);
  canvas.width = parentW;
  canvas.height = canvasH;
  canvas.style.width = '100%';
  canvas.style.height = canvasH + 'px';

  // Select nodes
  const allNodes = (window.NODES || []).filter(n => n.id && n.cat);
  const rankedNodes = allNodes
    .map(n => ({ n, nrs: typeof computeNRS === 'function' ? computeNRS(n.id) : 50 }))
    .sort((a, b) => b.nrs - a.nrs)
    .slice(0, 130)
    .map(x => x.n);

  const selectedIds = new Set(rankedNodes.map(n => n.id));
  const allLinks = window.LINKS || [];
  const selectedEdges = allLinks
    .filter(l => {
      const s = typeof lid === 'function' ? lid(l.source) : (l.source?.id || l.source);
      const t = typeof lid === 'function' ? lid(l.target) : (l.target?.id || l.target);
      return selectedIds.has(s) && selectedIds.has(t);
    })
    .slice(0, 500)
    .map(l => ({
      s: typeof lid === 'function' ? lid(l.source) : (l.source?.id || l.source),
      t: typeof lid === 'function' ? lid(l.target) : (l.target?.id || l.target),
    }));

  const nodePos = _wrComputeLayout(canvas.width, canvas.height, rankedNodes);

  // Compute cascade (with fallback)
  let finalImpacts = Object.keys(nodeImpacts).length ? { ...nodeImpacts } : {};
  let finalCascade = cascadeNodes.length ? [...cascadeNodes] : [];
  // unidad: 'pct' = % de valor estimado por los agentes; 'sev' = severidad
  // 0-100 del motor estructural (sin IA, misma matemática que el servidor)
  let unit = 'pct';
  const needStructural = !Object.keys(finalImpacts).length && impactSource !== 'none';
  if (needStructural) {
    // motor ÚNICO del servidor (/api/hot/scenario, factores activos): la sala de guerra ya no corre su
    // propia propagación con otros parámetros (PROP-11). Se pinta cuando llega la respuesta.
    unit = 'sev';
    impactSource = impactSource || 'structural';
    _wrFallbackCascade(rankedNodes, selectedEdges, finalCascade, reportText, presetId).then(fb => {
      if (!document.getElementById('wr-canvas') || canvas !== document.getElementById('wr-canvas')) return;
      const srcEl2 = document.getElementById('wr-src');
      if (fb.error && srcEl2) srcEl2.textContent = ' ' + fb.error;
      else if (srcEl2 && window.KhipuHot) srcEl2.textContent = srcEl2.textContent + ' ' + window.KhipuHot.stamp(fb.view);
      _wrFinish(canvas, nodePos, selectedEdges, fb.cascade, fb.impacts, unit, priceTrajs, reportText, presetId, debate, scenarioTitle);
    });
  }
  const srcEl = document.getElementById('wr-src');
  if (srcEl) srcEl.textContent = impactSource === 'none'
    ? WL(' Sin impactos: el escenario no nombra ninguna empresa.', ' No impacts: the scenario names no company.')
    : impactSource === 'agents'
    ? WL(' Impactos: agentes de IA (' + ((debate && debate.model) || 'IA') + '), cada uno con su razón.', ' Impacts: AI agents (' + ((debate && debate.model) || 'AI') + '), each with its rationale.')
    : WL(' Impactos: motor único del servidor (sin IA, factores activos) — severidad 0-100 del golpe, no % de precio.', ' Impacts: single server engine (no AI, active factors) — hit severity 0-100, not % price.');

  if (needStructural) return;   // _wrFinish lo hace cuando responde el servidor
  _wrFinish(canvas, nodePos, selectedEdges, finalCascade, finalImpacts, unit, priceTrajs, reportText, presetId, debate, scenarioTitle);
}

function _wrFinish(canvas, nodePos, selectedEdges, finalCascade, finalImpacts, unit, priceTrajs, reportText, presetId, debate, scenarioTitle) {
  // Start animation
  _wrStartAnimation(canvas, nodePos, selectedEdges, finalCascade, finalImpacts, unit);

  // Render side panels
  _wrRenderWinners(finalImpacts, unit);
  _wrRenderPrices(priceTrajs, finalImpacts);
  _wrRenderAgents(reportText, presetId, debate);

  // Ingest as hyperedge for 3D map
  try {
    if (window._hypergraph && finalCascade.length >= 2) {
      const he = {
        id: 'he_wr_' + Date.now(),
        type: 'simulation',
        timestamp: new Date().toISOString(),
        title: scenarioTitle || 'War-Room',
        severity: 8,
        nodes_affected: finalCascade.slice(0, 20),
        node_impacts: finalImpacts,
        duration_days: 120,
      };
      window._hypergraph.addHyperedge(he);
    }
  } catch(_) {}
}

// Deterministic polar layout by category
function _wrComputeLayout(W, H, nodes) {
  const cx = W / 2, cy = H / 2;
  const cats = [...new Set(nodes.map(n => n.cat).filter(Boolean))];
  const catAngle = {};
  cats.forEach((c, i) => { catAngle[c] = (i / cats.length) * Math.PI * 2 - Math.PI / 2; });

  const R = Math.min(W, H) * 0.37;
  const nodePos = {};

  const fnv = s => {
    let h = 2166136261;
    for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619) >>> 0;
    return h;
  };

  nodes.forEach(n => {
    const baseAngle = catAngle[n.cat] ?? 0;
    const h1 = fnv(n.id), h2 = fnv(n.id + '~r');
    const jA = baseAngle + ((h1 & 0xFF) / 255 - 0.5) * 0.48;
    const jR = R + ((h2 & 0xFF) / 255 - 0.5) * 62;
    const nrs = typeof computeNRS === 'function' ? computeNRS(n.id) : 50;
    nodePos[n.id] = {
      x: cx + Math.cos(jA) * jR,
      y: cy + Math.sin(jA) * jR,
      r: 2.5 + nrs * 0.065,
      label: n.label || n.id,
    };
  });
  return nodePos;
}

// Cascada ESTRUCTURAL cuando los agentes no dieron impactos → Promise<{impacts, cascade, view?, error?}>
function _wrFallbackCascade(nodes, edges, initialCascade, reportText, presetId) {
  // Motor ESTRUCTURAL determinista (sin IA, sin azar): los nodos semilla se golpean y el daño se propaga
  // con EL kernel del servidor (/api/hot/scenario, factores activos, parámetros del servidor). Resultado:
  // severidad 0-100 por empresa. (2026-09-29: sin Math.random; 2026-10-13: sin motor propio en el navegador.)
  const impacts = {}, cascade = [];
  const NBI = window.NODE_BY_ID || {};
  const seedIds = new Set(initialCascade.filter(id => NBI[id]).slice(0, 8));
  if (!seedIds.size && reportText) {
    // palabra COMPLETA (antes "Intel" calzaba en "inteligencia", "Meta" en "metal")
    const txt = reportText.toLowerCase();
    nodes.forEach(n => {
      const lbl = (n.label || '').toLowerCase();
      if (lbl.length <= 3 || seedIds.size >= 8) return;
      const rx = new RegExp('(^|[^\\p{L}\\p{N}])' + lbl.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '($|[^\\p{L}\\p{N}])', 'u');
      if (rx.test(txt)) seedIds.add(n.id);
    });
  }
  if (!seedIds.size && presetId) {
    const presetSeeds = {
      taiwan_conflict: ['TSMC'], china_chip_ban_total: ['Nvidia', 'AMD'],
      hbm_shortage_2027: ['SKHynix', 'Micron', 'Samsung'], openai_ipo_impact: ['OpenAI'],
      starshield_reveal: ['SpaceX'],
    };
    (presetSeeds[presetId] || []).forEach(q => {
      const r = window.KhipuResolve ? window.KhipuResolve.find(q) : null;
      const id = (r && r.node && r.node.id) || (NBI[q] ? q : null);
      if (id) seedIds.add(id);
    });
  }
  if (!seedIds.size) return Promise.resolve({ impacts, cascade });
  if (!window.KhipuHot) return Promise.resolve({ impacts, cascade, error: window.LANG === 'en' ? 'Impact engine unavailable.' : 'Motor de impacto no disponible.' });
  return window.KhipuHot.simulate({ targets: [...seedIds], kind: 'collapse', severity: 100 }).then(res => {
    if (!res.ok) return { impacts, cascade, error: res.error };   // sin servidor no hay cifra (nunca una inventada)
    [...res.impact.entries()].filter(([, v]) => v >= 2).sort((x, y) => y[1] - x[1]).slice(0, 60)
      .forEach(([id, v]) => { impacts[id] = v; cascade.push(id); });
    return { impacts, cascade, view: res.view };
  });
}

// Start RAF cascade animation
function _wrStartAnimation(canvas, nodePos, edges, cascadeOrder, nodeImpacts, unit) {
  const TH = unit === 'sev' ? [55, 25] : [12, 5];   // % estimado (agentes) vs severidad 0-100
  if (_wrAnimId) cancelAnimationFrame(_wrAnimId);
  const ctx = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;
  const nodeStates = {};

  // Also include nodes from nodeImpacts not in cascadeOrder
  const allImpacted = [...new Set([
    ...cascadeOrder,
    ...Object.keys(nodeImpacts),
  ])];

  const totalRounds = 20;
  const perRound = Math.max(1, Math.ceil(allImpacted.length / totalRounds));
  let currentRound = 0;

  const revealRound = () => {
    if (currentRound >= totalRounds) return;
    const start = currentRound * perRound;
    for (let i = start; i < Math.min(start + perRound, allImpacted.length); i++) {
      const id = allImpacted[i];
      if (!id) continue;
      if (nodeImpacts[id] === undefined) continue;   // sin dato → no se inventa
      const imp = nodeImpacts[id];
      nodeStates[id] = { impact: imp, t0: performance.now() };
    }
    currentRound++;
    const badge = document.getElementById('wr-round');
    if (badge) badge.textContent = `${window.LANG === 'en' ? 'Round' : 'Ronda'} ${currentRound}/${totalRounds}`;
  };

  revealRound();
  if (_wrRoundIvl) clearInterval(_wrRoundIvl);
  const ivl = _wrRoundIvl = setInterval(() => {
    revealRound();
    if (currentRound >= totalRounds) clearInterval(ivl);
  }, 1400);

  const draw = (now) => {
    // Background
    ctx.fillStyle = '#070b14';
    ctx.fillRect(0, 0, W, H);

    // Edges
    edges.forEach(({s, t}) => {
      const sp = nodePos[s], tp = nodePos[t];
      if (!sp || !tp) return;
      const sl = !!nodeStates[s], tl = !!nodeStates[t];
      ctx.beginPath();
      ctx.moveTo(sp.x, sp.y); ctx.lineTo(tp.x, tp.y);
      ctx.strokeStyle = sl && tl ? 'rgba(155,79,232,.32)' : sl || tl ? 'rgba(155,79,232,.1)' : 'rgba(70,90,130,.07)';
      ctx.lineWidth = sl && tl ? 1 : 0.5;
      ctx.stroke();
    });

    // Nodes
    Object.entries(nodePos).forEach(([id, pos]) => {
      const st = nodeStates[id];
      const r = pos.r || 4;
      let fill, glow;

      if (!st) {
        fill = 'rgba(80,110,165,.38)'; glow = null;
      } else {
        const imp = st.impact;
        if (imp > TH[0])       { fill = '#ef4444'; glow = 'rgba(239,68,68,.3)'; }
        else if (imp > TH[1])  { fill = '#f97316'; glow = 'rgba(249,115,22,.25)'; }
        else if (imp > 0)   { fill = '#facc15'; glow = 'rgba(250,204,21,.2)'; }
        else                { fill = '#22c55e'; glow = 'rgba(34,197,94,.28)'; }
      }

      if (glow) {
        const age = now - (st.t0 || now);
        const pulse = Math.sin(age / 620) * 0.15 + 0.85;
        const gr = ctx.createRadialGradient(pos.x, pos.y, 0, pos.x, pos.y, r * 4.5);
        gr.addColorStop(0, glow.replace(/[\d.]+\)$/, m => (parseFloat(m) * pulse).toFixed(2) + ')'));
        gr.addColorStop(1, 'transparent');
        ctx.beginPath(); ctx.arc(pos.x, pos.y, r * 4.5, 0, Math.PI * 2);
        ctx.fillStyle = gr; ctx.fill();
      }

      ctx.beginPath(); ctx.arc(pos.x, pos.y, r, 0, Math.PI * 2);
      ctx.fillStyle = fill; ctx.fill();

      if (st || r >= 5.5) {
        ctx.fillStyle = st ? 'rgba(230,242,255,.88)' : 'rgba(120,145,200,.55)';
        ctx.font = `${st ? 9 : 8}px Inter,system-ui,sans-serif`;
        ctx.fillText((pos.label || id).slice(0, 14), pos.x + r + 2, pos.y + 3.5);
      }
    });

    _wrAnimId = requestAnimationFrame(draw);
  };
  _wrAnimId = requestAnimationFrame(draw);
}

// Winners/Losers panel
function _wrRenderWinners(nodeImpacts, unit) {
  const el = document.getElementById('wr-winners');
  if (!el) return;
  const en = window.LANG === 'en', WL = (es, e) => en ? e : es;
  const NBI = window.NODE_BY_ID || {};
  const esc2 = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const entries = Object.entries(nodeImpacts)
    .map(([id, imp]) => ({ id, imp, label: (NBI[id]?.label || id).slice(0, 18) }))
    .sort((a, b) => b.imp - a.imp);
  const losers  = entries.filter(e => e.imp > 0).slice(0, 5);
  const winners = entries.filter(e => e.imp < 0).sort((a, b) => a.imp - b.imp).slice(0, 3);
  const fmt = (v, neg) => unit === 'sev' ? Math.round(Math.abs(v)) + '/100' : (neg ? '−' : '+') + Math.abs(v).toFixed(1) + '%';
  const row = (e, col, neg) => `<div style="display:flex;justify-content:space-between;align-items:center;padding:4px 0;border-bottom:1px solid var(--line)">
        <span style="color:var(--ink-2);font-size:11px;cursor:pointer" onclick="jumpTo('${esc2(e.id)}')">${esc2(e.label)}</span>
        <span style="color:${col};font-weight:700;font-size:11px">${fmt(e.imp, neg)}</span></div>`;
  el.innerHTML = `<div class="wr-panel-head">${unit === 'sev' ? WL('💥 Severidad del golpe (0-100)', '💥 Hit severity (0-100)') : WL('🏆 Impacto estimado en valor', '🏆 Estimated value impact')}</div>`
    + `<div style="font-size:10px;color:var(--ink-3);margin-bottom:4px">${unit === 'sev' ? WL('Estructural, sin IA — no es % de precio', 'Structural, no AI — not % price') : WL('Estimación de los agentes — no es precio real', 'Agents estimate — not a real price')}</div>`
    + (losers.length ? `<div style="font-size:10px;color:var(--ink-3);font-weight:700;text-transform:uppercase;letter-spacing:.06em">${WL('Más afectadas', 'Most affected')}</div>` : '')
    + losers.map(e => row(e, '#ef4444', true)).join('')
    + (winners.length ? `<div style="margin-top:6px;font-size:10px;color:var(--ink-3);font-weight:700;text-transform:uppercase;letter-spacing:.06em">${WL('Se benefician', 'Benefit')}</div>` : '')
    + winners.map(e => row(e, '#22c55e', false)).join('');
}

// Price trajectories panel with sparklines
function _wrRenderPrices(priceTrajs, nodeImpacts) {
  const el = document.getElementById('wr-prices');
  if (!el) return;
  // SOLO trayectorias reales que traiga el motor. Antes se fabricaban con
  // Math.random y se rotulaban "Trayectorias (6M)" como si fueran precios —
  // eliminado (2026-09-29): un dato inventado perjudica al inversionista.
  const trajs = {};
  if (priceTrajs && typeof priceTrajs === 'object') {
    Object.entries(priceTrajs).forEach(([k, v]) => {
      trajs[k] = Array.isArray(v) ? v : (v?.values || null);
    });
  }
  const entries = Object.entries(trajs).filter(([,v]) => v).slice(0, 6);
  if (!entries.length) { el.style.display = 'none'; return; }

  el.style.display = '';
  el.innerHTML = `<div class="wr-panel-head">📉 ${window.LANG === 'en' ? 'Simulated paths' : 'Trayectorias simuladas'}</div>`
    + entries.map(([tk, vals]) => {
      const chg = ((vals[vals.length-1] - vals[0]) / vals[0] * 100).toFixed(1);
      const col = parseFloat(chg) >= 0 ? '#22c55e' : '#ef4444';
      const sid = 'wrs' + tk.replace(/[^a-zA-Z0-9]/g,'');
      return `<div style="display:flex;align-items:center;justify-content:space-between;padding:4px 0;border-bottom:1px solid var(--line)">
        <span style="color:var(--ink-2);font-size:11px;min-width:44px;overflow:hidden">${tk.slice(0,10)}</span>
        <canvas id="${sid}" width="68" height="26"></canvas>
        <span style="color:${col};font-weight:700;font-size:11px;min-width:38px;text-align:right">${parseFloat(chg)>=0?'+':''}${chg}%</span>
      </div>`;
    }).join('');

  requestAnimationFrame(() => {
    entries.forEach(([tk, vals]) => {
      const sid = 'wrs' + tk.replace(/[^a-zA-Z0-9]/g,'');
      const c = document.getElementById(sid); if (!c) return;
      const ctx2 = c.getContext('2d');
      const W2 = c.width, H2 = c.height;
      const mn = Math.min(...vals), mx = Math.max(...vals), rng = mx - mn || 1;
      const chg = vals[vals.length-1] - vals[0];
      ctx2.clearRect(0,0,W2,H2);
      ctx2.strokeStyle = chg >= 0 ? '#22c55e' : '#ef4444';
      ctx2.lineWidth = 1.5;
      ctx2.beginPath();
      vals.forEach((v, i) => {
        const x = (i / (vals.length-1)) * (W2-2) + 1;
        const y = H2 - ((v - mn) / rng) * (H2-4) - 2;
        i === 0 ? ctx2.moveTo(x,y) : ctx2.lineTo(x,y);
      });
      ctx2.stroke();
    });
  });
}

// Agent debate panel with scenario-specific content
function _wrRenderAgents(reportText, presetId, debate) {
  // Debate REAL de esta simulación (rondas y razones de core/sim_agents.py).
  // Antes: textos fijos con cifras inventadas y recomendaciones de compra/venta
  // ("Corto NVDA", "P(bloqueo)=34%") mostrados para CUALQUIER escenario —
  // eliminado (2026-09-29).
  const el = document.getElementById('wr-agents');
  if (!el) return;
  const en = window.LANG === 'en', WL = (es, e) => en ? e : es;
  const esc2 = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const NBI = window.NODE_BY_ID || {};
  const cards = [];
  const rounds = (debate && debate.rounds) || [];
  rounds.slice(0, 4).forEach(r => {
    const evs = (r.events || []).slice(0, 3).map(e => '• ' + esc2(e)).join('<br>');
    if (evs) cards.push({ role: WL('Ronda ', 'Round ') + r.round, c: '#a78bfa', html: evs });
  });
  const imps = ((debate && debate.impacts) || []).filter(i => i && i.rationale).slice(0, 6);
  imps.forEach(i => {
    const pct = +i.pct;
    cards.push({ role: (pct >= 0 ? '🟢 ' : '🔴 ') + esc2(i.label || (NBI[i.id] || {}).label || i.id) + ' ' + (pct >= 0 ? '+' : '−') + Math.abs(pct).toFixed(1) + '%',
                 c: pct >= 0 ? '#22c55e' : '#ef4444', html: esc2(i.rationale) });
  });
  if (!cards.length) {
    el.innerHTML = `<div style="grid-column:1/-1;font-size:12px;color:var(--ink-3)">${WL(
      'Sin debate de agentes: esta simulación usó el motor estructural del grafo (sin IA). Cuando la IA está disponible, aquí aparece lo que cada agente argumentó.',
      'No agent debate: this simulation used the structural graph engine (no AI). When AI is available, what each agent argued appears here.')}</div>`;
    return;
  }
  el.innerHTML = cards.map(({ role, c, html }) =>
    `<div class="wr-agent-card" style="border-left-color:${c}">
       <div class="wr-agent-role" style="color:${c}">${role}</div>
       <div>${html}</div>
     </div>`).join('');
}


// ════════════════════════════════════════════════════════════════════════════
// DOSSIER FINANCIERO — 8 paneles, comparación hasta 3 empresas
// ════════════════════════════════════════════════════════════════════════════
const _dossier = {
  slots: [],          // [{nodeId, ticker, label, color, data}] up to 3
  COLORS: ['#7c3aed','#ef4444','#22c55e'],
  LABELS: { revenue:'Revenue ($B)', shares:'Dilution (B acc)', fcf:'FCF ($B)',
    stock:'Precio acción', ev_revenue:'EV/Revenue', pe_ratio:'P/E Ratio',
    gross_margin:'Márgenes (%)', roe:'ROE / ROIC (%)' },
};

// ── Autocomplete ─────────────────────────────────────────────────────────────
function _dossierAutocomplete(q) {
  const box = document.getElementById('dossier-ac');
  if (!box) return;
  q = q.toLowerCase().trim();
  if (q.length < 2) { box.style.display = 'none'; return; }
  const hits = (window.NODES || [])
    .filter(n => n.mkt && (
      (n.label||'').toLowerCase().includes(q) ||
      (n.mkt||'').toLowerCase().includes(q) ||
      n.id.toLowerCase().includes(q)))
    .slice(0, 8);
  if (!hits.length) { box.style.display = 'none'; return; }
  box.innerHTML = hits.map(n =>
    `<div onclick="_dossierPickAC('${n.id}','${n.mkt}','${(n.label||n.id).replace(/'/g,"\\'")}');event.stopPropagation()"
      style="padding:7px 10px;font-size:12px;cursor:pointer;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center"
      onmouseover="this.style.background='var(--surface-2)'" onmouseout="this.style.background=''">
      <span>${n.label||n.id}</span>
      <span style="font-size:10px;color:var(--ink-3)">${n.mkt}</span>
    </div>`).join('');
  box.style.display = 'block';
}

function _dossierPickAC(nodeId, ticker, label) {
  const inp = document.getElementById('dossier-search');
  if (inp) inp.value = label;
  document.getElementById('dossier-ac').style.display = 'none';
  _dossierLoadCompany(nodeId, ticker, label);
}

function _dossierLoad() {
  document.getElementById('dossier-ac').style.display = 'none';
  const q = (document.getElementById('dossier-search')?.value || '').trim().toLowerCase();
  if (!q) return;
  const n = (window.NODES || []).find(nd =>
    nd.mkt && ((nd.mkt||'').toLowerCase() === q ||
    (nd.label||'').toLowerCase().includes(q) ||
    nd.id.toLowerCase().includes(q)));
  if (n) { _dossierLoadCompany(n.id, n.mkt, n.label || n.id); return; }
  // ¿existe pero no cotiza? → su Dossier universal (toda empresa tiene uno)
  const p = (window.NODES || []).find(nd =>
    (nd.label||'').toLowerCase().includes(q) || nd.id.toLowerCase().includes(q));
  if (p && window.openFinCard) {
    if (typeof toast === 'function') toast(_dsL(`${p.label||p.id} no cotiza en bolsa: abrimos su Dossier.`, `${p.label||p.id} is not publicly traded: opening its Dossier.`));
    window.openFinCard(p.id);
  } else if (typeof toast === 'function') toast(_dsL('Empresa no encontrada con ticker/nombre: ', 'No company found for ticker/name: ') + q);
}
document.addEventListener('click', () => { const b=document.getElementById('dossier-ac'); if(b)b.style.display='none'; });

function _dossierAddCompare() {
  const inp = document.getElementById('dossier-search');
  if (inp) { inp.value = ''; inp.focus(); }
}

// ── Load company dossier ─────────────────────────────────────────────────────
/* 2026-09-28: HONESTIDAD. Antes, si /api/dossier fallaba, el cliente INVENTABA
   ingresos, márgenes, ROE y FCF con Math.random() (_dossierSynthetic, borrado).
   Ahora: datos reales de la cascada del servidor (FMP → Yahoo → Alpha Vantage)
   o un aviso claro y bilingüe de que no hay estados públicos — jamás números
   inventados. Las empresas sin cotización van al 📊 Dossier universal. */
const _dsL = (es, en) => (typeof LANG !== 'undefined' && LANG === 'en') ? en : es;
const _DS_SRC = { fmp:'Financial Modeling Prep', yahoo:'Yahoo Finance', alphavantage:'Alpha Vantage' };
const _dsNoData = d => !d || d.error || d.available === false;

async function _dossierLoadCompany(nodeId, ticker, label) {
  if (!ticker) {                       // no cotiza → su Dossier universal (fincard)
    if (window.openFinCard) window.openFinCard(nodeId);
    return;
  }
  const slot = _dossier.slots.findIndex(s => s.nodeId === nodeId);
  const idx  = slot >= 0 ? slot : (_dossier.slots.length < 3 ? _dossier.slots.length : 0);
  // color libre (al quitar una empresa, dos podían quedar del mismo color)
  const used = new Set(_dossier.slots.filter((s, i) => i !== idx).map(s => s.color));
  const color = _dossier.COLORS.find(c => !used.has(c)) || _dossier.COLORS[idx];
  const slotObj = { nodeId, ticker, label, color, data: null };
  _dossier.slots[idx] = slotObj;
  _dossierRenderBadges();

  const panels = document.getElementById('dossier-panels');
  if (panels && !_dossier.slots.some(s => s.data)) {
    panels.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:24px 0;font-size:12px;color:var(--ink-3)">
      ${_dsL('Cargando dossier de ', 'Loading dossier for ')}${esc(label)}…</div>`;
  }

  // Un fallo de TRANSPORTE (límite de consultas 429, servidor reiniciándose
  // 5xx, sin red, respuesta ilegible) NO es "esta empresa no publica estados":
  // se marca `transient` y la tarjeta ofrece reintentar. Solo un 200 con
  // available:false del servidor dice que las fuentes no tienen los datos.
  let data, transient = false, httpStatus = null;
  try {
    const r = await fetch(`${BASE}/api/dossier/${encodeURIComponent(ticker)}`);
    data = await r.json().catch(() => null);
    if (!r.ok || !data || typeof data !== 'object') { transient = true; httpStatus = r.status; }
  } catch (e) {
    transient = true;
  }
  if (transient) {
    data = { available: false, transient: true, ticker, status: httpStatus };
  } else if (_dsNoData(data)) {
    data = { available: false, ticker,
      reason: data.reason || data.error || 'sin datos',
      reason_en: data.reason_en || data.reason || data.error || 'no data',
      tried: data.tried || [] };
  }
  if (!_dossier.slots.includes(slotObj)) return;   // lo quitaron mientras cargaba
  slotObj.data = data;
  _dossierRenderPanels();

  const actions = document.getElementById('dossier-actions');
  if (actions) actions.style.display = 'flex';
}

// ── Render badges ─────────────────────────────────────────────────────────────
function _dossierRenderBadges() {
  const el = document.getElementById('dossier-badges');
  if (!el) return;
  el.innerHTML = _dossier.slots.map((s,i) =>
    `<span class="dossier-badge" style="background:${s.color}22;border:1px solid ${s.color}55;color:${s.color}">
       ${esc(s.label.split(' ')[0])} <span class="rm" onclick="_dossierRemove(${i});event.stopPropagation()">✕</span>
     </span>`).join('');
}

function _dossierRemove(idx) {
  _dossier.slots.splice(idx, 1);
  _dossierRenderBadges();
  if (_dossier.slots.length) _dossierRenderPanels();
  else {
    document.getElementById('dossier-panels').innerHTML =
      `<div style="grid-column:1/-1;text-align:center;padding:24px 0;font-size:12px;color:var(--ink-3)">${_dsL('Busca una empresa para ver su dossier', 'Search for a company to see its dossier')}</div>`;
    document.getElementById('dossier-actions').style.display = 'none';
  }
}

// ── helpers de datos ─────────────────────────────────────────────────────────
// años: unión de los años de todas las empresas con datos (ascendente, máx. 7)
// y cada serie se ALINEA por año — antes se alineaba por posición y dos
// empresas con años fiscales distintos quedaban desfasadas.
function _dsYears(okSlots) {
  return [...new Set(okSlots.flatMap(s => s.data.years || []).map(String))].sort().slice(-7);
}
function _dsAlign(s, field, years) {
  const ys = (s.data.years || []).map(String), v = s.data[field] || [];
  return years.map(y => { const i = ys.indexOf(y); return (i >= 0 && v[i] != null && isFinite(v[i])) ? +v[i] : null; });
}
function _dsLast(s, field) {          // último valor NO nulo + su año
  const ys = s.data.years || [], v = s.data[field] || [];
  for (let i = v.length - 1; i >= 0; i--) if (v[i] != null && isFinite(v[i])) return { v: +v[i], y: String(ys[i] || '') };
  return null;
}
function _dsFmtB(v, sign) {           // miles de millones USD → $1.2T / $3.4B / $560M
  const a = Math.abs(v), s = v < 0 ? '-' : (sign ? '+' : '');
  return s + '$' + (a >= 1000 ? (a / 1000).toFixed(2) + 'T' : a >= 1 ? a.toFixed(1) + 'B' : Math.round(a * 1000) + 'M');
}
// reintentar una empresa cuyo dossier falló por un problema pasajero
function _dossierRetry(nodeId, btn) {
  const s = _dossier.slots.find(x => x.nodeId === nodeId);
  if (!s) return;
  if (btn) { btn.disabled = true; btn.textContent = _dsL('Reintentando…', 'Retrying…'); }
  _dossierLoadCompany(s.nodeId, s.ticker, s.label);
}
// fallo pasajero: el servidor no respondió AHORA (no es falta de datos)
function _dsTransientCard(s) {
  const d = s.data || {};
  const why = d.status === 429
    ? _dsL('Hubo demasiadas consultas seguidas; el servidor pide esperar un momento.', 'Too many requests in a row; the server asks us to wait a moment.')
    : d.status
      ? _dsL('El servidor está ocupado o reiniciándose.', 'The server is busy or restarting.')
      : _dsL('No hubo conexión con el servidor (revisa tu internet).', 'There was no connection to the server (check your internet).');
  return `<div style="grid-column:1/-1;padding:12px 14px;border:1px solid var(--line);border-left:3px solid ${s.color};border-radius:8px;background:var(--surface-2);font-size:12px;line-height:1.5;color:var(--ink-2)">
      <div style="font-weight:700;color:var(--ink)">⏳ ${esc(s.label)} <span style="font-family:'JetBrains Mono',monospace;font-size:10.5px;color:var(--ink-3)">${esc(s.ticker)}</span></div>
      <div>${_dsL('No pudimos consultar las fuentes ahora. Reintenta en un minuto.', 'We could not reach the sources right now. Try again in a minute.')}</div>
      <div style="font-size:11px;color:var(--ink-3)">${why} ${_dsL('Esto NO significa que la empresa no tenga estados financieros.', 'This does NOT mean the company has no financial statements.')}</div>
      <button onclick="_dossierRetry('${esc(s.nodeId)}', this)" style="margin-top:8px;padding:5px 12px;border:1px solid var(--blue);border-radius:6px;background:none;color:var(--blue);cursor:pointer;font-size:11.5px;font-weight:600">↻ ${_dsL('Reintentar', 'Try again')}</button>
    </div>`;
}
function _dsEmptyCard(s) {
  const d = s.data || {};
  if (d.transient) return _dsTransientCard(s);
  // el servidor antepone "Sin estados… para X — "; aquí ya lo dice la 1ª línea → solo el detalle
  const raw = String(_dsL(d.reason, d.reason_en || d.reason) || '');
  const reason = raw.includes(' — ') ? raw.split(' — ').slice(1).join(' — ') : raw;
  const tried = (d.tried || []).map(k => _DS_SRC[k] || k).join(' · ');
  return `<div style="grid-column:1/-1;padding:12px 14px;border:1px solid var(--line);border-left:3px solid ${s.color};border-radius:8px;background:var(--surface-2);font-size:12px;line-height:1.5;color:var(--ink-2)">
      <div style="font-weight:700;color:var(--ink)">📭 ${esc(s.label)} <span style="font-family:'JetBrains Mono',monospace;font-size:10.5px;color:var(--ink-3)">${esc(s.ticker)}</span></div>
      <div>${_dsL('Sin estados financieros públicos para ', 'No public financial statements for ')}${esc(s.label)}${_dsL(' en las fuentes consultadas.', ' in the sources we checked.')}</div>
      ${tried ? `<div style="font-size:11px;color:var(--ink-3)">${_dsL('Fuentes probadas: ', 'Sources tried: ')}${esc(tried)}</div>` : ''}
      ${reason ? `<div style="font-size:11px;color:var(--ink-3)">${_dsL('Detalle: ', 'Details: ')}${esc(reason)}</div>` : ''}
      <div style="font-size:11px;color:var(--ink-3);margin-top:2px">${_dsL('No mostramos cifras estimadas ni inventadas: este espacio queda vacío hasta que una fuente pública las publique.', 'We never show estimated or made-up figures: this stays empty until a public source publishes them.')}</div>
      ${window.openFinCard ? `<button onclick="window.openFinCard('${esc(s.nodeId)}')" style="margin-top:8px;padding:5px 12px;border:1px solid var(--blue);border-radius:6px;background:none;color:var(--blue);cursor:pointer;font-size:11.5px;font-weight:600">📊 ${_dsL('Ver su Dossier en vivo (precio, capitalización y gráfico de la acción)', 'See its live Dossier (price, market cap and stock chart)')}</button>` : ''}
    </div>`;
}

// ── Render all 8 panels ──────────────────────────────────────────────────────
function _dossierRenderPanels() {
  const panels = document.getElementById('dossier-panels');
  if (!panels || !_dossier.slots.some(s => s.data)) return;

  const okSlots = _dossier.slots.filter(s => s.data && !_dsNoData(s.data));
  const noSlots = _dossier.slots.filter(s => s.data && _dsNoData(s.data));
  const emptyHTML = noSlots.map(_dsEmptyCard).join('');
  if (!okSlots.length) { panels.innerHTML = emptyHTML; return; }

  const years = _dsYears(okSlots);
  const d0 = okSlots[0];
  const yTag = x => x && x.y ? ` <span style="font-size:10px;font-weight:500;opacity:.55">FY${esc(x.y.slice(-2))}</span>` : '';
  const mkPanel = (id, head, valStr, legend) =>
    `<div class="dossier-panel">
       <div class="dossier-phead">${head}${legend ? ` <span style="opacity:.5;font-weight:500;font-size:9px">${legend}</span>` : ''}</div>
       <div class="dossier-pval" id="dp-val-${id}">${valStr}</div>
       <canvas id="dp-${id}" height="90"></canvas>
     </div>`;
  const pct = x => x ? x.v.toFixed(1) + '%' + yTag(x) : '—';

  const rev = _dsLast(d0, 'revenue'), sh = _dsLast(d0, 'shares'), fcf = _dsLast(d0, 'fcf');
  const gm = _dsLast(d0, 'gross_margin'), ev = _dsLast(d0, 'ev_revenue'), nd = _dsLast(d0, 'net_debt');
  const nm = _dsLast(d0, 'net_margin'), roe = _dsLast(d0, 'roe');

  // fuente de cada empresa, dicha tal cual (y la moneda original si no es USD)
  const srcLine = okSlots.map(s => {
    const src = _DS_SRC[s.data.source] || s.data.source || '—';
    const cur = s.data.currency && s.data.currency !== 'USD'
      ? _dsL(` · montos en USD convertidos desde ${esc(s.data.currency)} al tipo de cambio ACTUAL (todos los años; puede diferir de lo que la empresa reportó en dólares ese año)`,
             ` · amounts in USD converted from ${esc(s.data.currency)} at the CURRENT exchange rate (every year; may differ from the dollar figure the company reported that year)`) : '';
    return `<span style="color:${s.color}">●</span> ${esc(s.label)} — ${esc(src)}${cur}`;
  }).join(' &nbsp; ');

  panels.innerHTML = emptyHTML +
    mkPanel('revenue',  _dsL('Ingresos', 'Revenue'),                 rev ? _dsFmtB(rev.v) + yTag(rev) : '—') +
    mkPanel('shares',   _dsL('Acciones (dilución)', 'Shares (dilution)'), sh ? sh.v.toFixed(2) + _dsL(' mil M acc.', 'B shares') + yTag(sh) : '—') +
    mkPanel('fcf',      'Free Cash Flow',                             fcf ? _dsFmtB(fcf.v, true) + yTag(fcf) : '—') +
    mkPanel('margins',  _dsL('Márgenes', 'Margins'),                  gm ? gm.v.toFixed(0) + _dsL('% bruto', '% gross') + yTag(gm) : '—', _dsL('— bruto · - - FCF', '— gross · - - FCF')) +
    mkPanel('ev',       _dsL('EV/Ventas', 'EV/Sales'),                ev ? ev.v.toFixed(1) + 'x' + yTag(ev) : '—') +
    mkPanel('balance',  _dsL('Balance', 'Balance sheet'),             nd ? (nd.v > 0 ? _dsL('Deuda neta ', 'Net debt ') + _dsFmtB(nd.v) : _dsL('Caja neta ', 'Net cash ') + _dsFmtB(-nd.v)) + yTag(nd) : '—') +
    mkPanel('margins2', _dsL('Margen neto', 'Net margin'),            pct(nm), _dsL('— bruto · - - neto', '— gross · - - net')) +
    mkPanel('roe',      'ROE / ROIC',                                 pct(roe), '— ROE · - - ROIC') +
    `<div style="grid-column:1/-1;font-size:10.5px;color:var(--ink-3);line-height:1.6">${_dsL('Fuente: ', 'Source: ')}${srcLine}</div>`;

  requestAnimationFrame(() => {
    const series = (field) => okSlots.map(s => ({ vals: _dsAlign(s, field, years), color: s.color }));
    const pair = (a, b) => [
      ...okSlots.map(s => ({ vals: _dsAlign(s, a, years), color: s.color, dash:false })),
      ...okSlots.map(s => ({ vals: _dsAlign(s, b, years), color: s.color, dash:true })),
    ];
    _dsDrawBars('dp-revenue',  series('revenue'), years, { unit:'$B', zeroBase:true });
    _dsDrawBars('dp-shares',   series('shares'),  years, { unit:'B', zeroBase:true });
    _dsDrawBars('dp-fcf',      series('fcf'),     years, { unit:'B', zeroBase:false });
    _dsDrawLines('dp-margins', pair('gross_margin', 'fcf_margin'), years, { unit:'%' });
    _dsDrawLines('dp-ev',      series('ev_revenue'), years, { unit:'x' });
    _dsDrawBalance('dp-balance', okSlots, years);
    _dsDrawLines('dp-margins2', pair('gross_margin', 'net_margin'), years, { unit:'%' });
    _dsDrawLines('dp-roe',     pair('roe', 'roic'), years, { unit:'%' });
  });
}
// al cambiar de idioma (applyLang) se redibuja con los textos nuevos
window._dossierRelabel = function () {
  const set = (id, es, en) => { const el = document.getElementById(id); if (el) el.textContent = _dsL(es, en); };
  set('dossier-h', '📊 Dossier Financiero', '📊 Financial Dossier');
  set('dossier-sub', 'Estados anuales · compara hasta 3 empresas · FMP → Yahoo Finance → Alpha Vantage · nada inventado',
    'Annual statements · compare up to 3 companies · FMP → Yahoo Finance → Alpha Vantage · nothing made up');
  set('dossier-go', 'Analizar', 'Analyze');
  set('dossier-wr-btn', '🚨 Stress en War-Room', '🚨 Stress in War-Room');
  set('dossier-compare-btn', '+ Comparar empresa', '+ Compare company');
  const inp = document.getElementById('dossier-search');
  if (inp) inp.placeholder = _dsL('Empresa o ticker…', 'Company or ticker…');
  if (_dossier.slots.some(s => s.data)) {
    // con la pestaña Análisis oculta los canvas miden 0 px y los gráficos
    // saldrían rotos: se marca y se redibuja al volver (switchTab)
    const ap = document.getElementById('analysis-panel');
    if (ap && ap.offsetParent === null) _dossier.needsRedraw = true;
    else _dossierRenderPanels();
  }
  else if (!_dossier.slots.length) {
    const p = document.getElementById('dossier-panels');
    if (p) p.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:24px 0;font-size:12px;color:var(--ink-3)">${_dsL('Busca una empresa para ver su dossier financiero completo', 'Search for a company to see its full financial dossier')}</div>`;
  }
};
try { window._dossierRelabel(); } catch (e) {}   // arranque en inglés: textos fijos del bloque
window._dossierRedrawIfNeeded = function () {
  if (!_dossier.needsRedraw) return;
  _dossier.needsRedraw = false;
  if (_dossier.slots.some(s => s.data)) _dossierRenderPanels();
};
// aviso sobre el canvas cuando la fuente no trae esa serie (en vez de un hueco mudo)
function _dsNoSeries(ctx, W, H) {
  ctx.fillStyle = 'rgba(120,140,180,.6)';
  ctx.font = '9px Inter,sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText(_dsL('— la fuente no publica este dato —', '— not reported by the source —'), W / 2, H / 2 + 3);
}

// ── Canvas drawing helpers ────────────────────────────────────────────────────
function _dsSetup(canvas) {
  const dpr = window.devicePixelRatio || 1;
  const W = canvas.parentElement.clientWidth - 24;
  const H = 90;
  canvas.width = W * dpr;
  canvas.height = H * dpr;
  canvas.style.width = W + 'px';
  canvas.style.height = H + 'px';
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);
  return { ctx, W, H };
}

function _dsDrawBars(id, series, years, opts = {}) {
  const canvas = document.getElementById(id); if (!canvas) return;
  const { ctx, W, H } = _dsSetup(canvas);
  const { unit='', zeroBase=true } = opts;
  const PAD = { top:16, right:4, bottom:18, left:28 };
  const cW = W - PAD.left - PAD.right;
  const cH = H - PAD.top - PAD.bottom;

  // Flatten all values
  const allVals = series.flatMap(s => s.vals).filter(v => v !== null && v !== undefined);
  if (!allVals.length) { _dsNoSeries(ctx, W, H); return; }
  const rawMin = zeroBase ? Math.min(0, ...allVals) : Math.min(...allVals);
  const rawMax = Math.max(...allVals);
  const range = rawMax - rawMin || 1;

  // Y axis labels
  ctx.fillStyle = 'rgba(120,140,180,.6)';
  ctx.font = '8px Inter,sans-serif';
  ctx.textAlign = 'right';
  [0, 0.5, 1].forEach(t => {
    const v = rawMin + t * range;
    const y = PAD.top + cH - (t * cH);
    ctx.fillText(Math.abs(v) >= 1 ? v.toFixed(0) : v.toFixed(1), PAD.left - 3, y + 3);
    ctx.strokeStyle = 'rgba(100,120,160,.08)';
    ctx.lineWidth = 0.5;
    ctx.beginPath(); ctx.moveTo(PAD.left, y); ctx.lineTo(PAD.left+cW, y); ctx.stroke();
  });

  const nSeries = series.length;
  const nYears = years.length;
  const groupW = cW / nYears;
  const barW = Math.min(groupW / (nSeries + 1), 16);

  series.forEach((s, si) => {
    s.vals.forEach((v, i) => {
      if (v === null || v === undefined) return;
      const x = PAD.left + groupW * i + groupW / (nSeries + 1) * (si + 0.5);
      const barH = Math.abs(v - rawMin) / range * cH;
      const y = PAD.top + cH - ((v - rawMin) / range * cH);
      ctx.fillStyle = v >= 0 ? s.color : '#ef4444';
      ctx.globalAlpha = si === 0 ? 1 : 0.75;
      ctx.beginPath();
      if (ctx.roundRect) ctx.roundRect(x, y, barW, barH > 1 ? barH : 1, 2);
      else ctx.rect(x, y, barW, barH > 1 ? barH : 1);
      ctx.fill();
    });
  });
  ctx.globalAlpha = 1;

  // X labels
  ctx.fillStyle = 'rgba(100,120,160,.7)';
  ctx.font = '8px Inter,sans-serif';
  ctx.textAlign = 'center';
  years.forEach((yr, i) => {
    ctx.fillText(yr.slice(2), PAD.left + groupW * i + groupW / 2, H - 3);
  });
}

function _dsDrawLines(id, series, years, opts = {}) {
  const canvas = document.getElementById(id); if (!canvas) return;
  const { ctx, W, H } = _dsSetup(canvas);
  const { unit = '' } = opts;
  const PAD = { top: 14, right: 6, bottom: 18, left: 28 };
  const cW = W - PAD.left - PAD.right;
  const cH = H - PAD.top - PAD.bottom;

  const allVals = series.flatMap(s => s.vals).filter(v => v !== null && v !== undefined);
  if (!allVals.length) { _dsNoSeries(ctx, W, H); return; }
  const rawMin = Math.min(...allVals);
  const rawMax = Math.max(...allVals);
  const range = rawMax - rawMin || 1;

  // Grid
  [0, 0.5, 1].forEach(t => {
    const v = rawMin + t * range;
    const y = PAD.top + cH - t * cH;
    ctx.fillStyle = 'rgba(120,140,180,.55)';
    ctx.font = '8px Inter,sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText((v >= 100 ? v.toFixed(0) : v.toFixed(1)) + unit, PAD.left - 3, y + 3);
    ctx.strokeStyle = 'rgba(100,120,160,.07)';
    ctx.lineWidth = 0.5;
    ctx.beginPath(); ctx.moveTo(PAD.left, y); ctx.lineTo(PAD.left+cW, y); ctx.stroke();
  });

  series.forEach(s => {
    if (!s.vals.length) return;
    ctx.strokeStyle = s.color;
    ctx.lineWidth = s.dash ? 1 : 1.5;
    ctx.globalAlpha = s.dash ? 0.55 : 1;
    if (s.dash) ctx.setLineDash([3, 3]);
    ctx.beginPath();
    let started = false;
    s.vals.forEach((v, i) => {
      if (v === null || v === undefined) return;
      const x = PAD.left + (i / (years.length - 1 || 1)) * cW;
      const y = PAD.top + cH - ((v - rawMin) / range) * cH;
      started ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
      started = true;
    });
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.globalAlpha = 1;
  });

  ctx.fillStyle = 'rgba(100,120,160,.7)';
  ctx.font = '8px Inter,sans-serif';
  ctx.textAlign = 'center';
  years.forEach((yr, i) => {
    ctx.fillText(yr.slice(2), PAD.left + (i / (years.length - 1 || 1)) * cW, H - 3);
  });
}

function _dsDrawBalance(id, okSlots, years) {
  const canvas = document.getElementById(id); if (!canvas) return;
  const { ctx, W, H } = _dsSetup(canvas);
  const PAD = { top:14, right:6, bottom:18, left:28 };
  const cW = W - PAD.left - PAD.right;
  const cH = H - PAD.top - PAD.bottom;
  okSlots = okSlots || [];
  years = years || [];

  // deuda (rojo) vs caja (color de la empresa) por empresa y año — alineado por año
  const debt = okSlots.map(s => _dsAlign(s, 'total_debt', years));
  const cash = okSlots.map(s => _dsAlign(s, 'cash', years));
  const allVals = [...debt.flat(), ...cash.flat()].filter(v => v != null);
  if (!allVals.length || !years.length) { _dsNoSeries(ctx, W, H); return; }
  const maxV = Math.max(...allVals) || 1;

  const nSeries = okSlots.length;
  const groupW = cW / years.length;
  const barW = Math.min(groupW / (nSeries + 1), 14);

  ctx.fillStyle = 'rgba(120,140,180,.55)';
  ctx.font = '8px Inter,sans-serif';
  ctx.textAlign = 'right';
  ctx.fillText(maxV.toFixed(0)+'B', PAD.left-3, PAD.top+3);
  ctx.fillText('0', PAD.left-3, PAD.top+cH+3);

  okSlots.forEach((s, si) => {
    debt[si].forEach((d, i) => {
      if (d == null || d < 0) return;
      const x = PAD.left + groupW*i + groupW/(nSeries+1)*(si+0.5);
      const debtH = (d/maxV)*cH;
      ctx.fillStyle = '#ef444488';
      ctx.fillRect(x, PAD.top+cH-debtH, barW, debtH);
    });
    cash[si].forEach((c, i) => {
      if (c == null || c < 0) return;
      const x = PAD.left + groupW*i + groupW/(nSeries+1)*(si+0.5);
      const cashH = (c/maxV)*cH;
      ctx.fillStyle = s.color + '99';
      ctx.fillRect(x+barW/2, PAD.top+cH-cashH, barW/2, cashH);
    });
  });

  ctx.fillStyle = 'rgba(100,120,160,.7)';
  ctx.font = '8px Inter,sans-serif';
  ctx.textAlign = 'center';
  years.forEach((yr, i) => {
    ctx.fillText(String(yr).slice(2), PAD.left+groupW*i+groupW/2, H-3);
  });

  // Legend
  const lDebt = _dsL('Deuda', 'Debt'), lCash = _dsL('Caja', 'Cash');
  ctx.font = '8px Inter,sans-serif';
  ctx.textAlign = 'left';
  ctx.fillStyle = '#ef4444'; ctx.fillRect(PAD.left, 4, 8, 4);
  ctx.fillStyle = 'rgba(120,140,180,.7)'; ctx.fillText(lDebt, PAD.left+11, 9);
  const x2 = PAD.left + 11 + ctx.measureText(lDebt).width + 8;
  ctx.fillStyle = (okSlots[0] ? okSlots[0].color : '#7c3aed') + 'cc'; ctx.fillRect(x2, 4, 8, 4);
  ctx.fillStyle = 'rgba(120,140,180,.7)'; ctx.fillText(lCash, x2+11, 9);
}

// ── War-Room from dossier ─────────────────────────────────────────────────────
function _dossierToWarRoom() {
  const companies = _dossier.slots.filter(s=>s.data).map(s=>s.label).join(', ');
  const tickers   = _dossier.slots.filter(s=>s.data).map(s=>s.ticker).join(' ');
  const txt = `Análisis de impacto en la cadena de valor: ${companies} (${tickers}). Evalúa vulnerabilidades, concentración de riesgo, y escenarios de shock para estas empresas.`;
  switchTab('simulation');
  setTimeout(() => {
    const ta = document.getElementById('sim-custom-text');
    const ni = document.getElementById('sim-custom-nodes');
    if (ta) ta.value = txt;
    if (ni) ni.value = _dossier.slots.map(s=>s.nodeId).join(',');
    document.getElementById('sim-run-btn')?.click();
  }, 350);
}

// Public: open dossier from node panel
window._openDossier = function(nodeId, ticker) {
  const n = (window.NODE_BY_ID||{})[nodeId];
  if (!n) return;
  // sin cotización no hay estados que comparar → su Dossier universal (fincard)
  if (!(ticker||n.mkt)) { if (window.openFinCard) window.openFinCard(nodeId); return; }
  switchTab('analysis');
  setTimeout(() => _dossierLoadCompany(nodeId, ticker||n.mkt, n.label||nodeId), 300);
};

/* ── Research SEC 10-K (Fase 2): modal con síntesis de Claude ──────────────── */
window._openResearch = async function(ticker, nodeId){
  ticker = (ticker||'').split(/[ ·]/)[0].trim();
  if(!ticker) return;
  let ov = document.getElementById('research-overlay');
  if(!ov){
    ov = document.createElement('div'); ov.id='research-overlay';
    ov.style.cssText='position:fixed;inset:0;z-index:1200;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center;padding:20px;backdrop-filter:blur(3px)';
    ov.onclick=e=>{ if(e.target===ov) ov.remove(); };
    document.body.appendChild(ov);
  }
  const rh='font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--ink-3);margin:14px 0 6px';
  ov.innerHTML = `<div style="background:var(--surface);border:1px solid var(--line);border-radius:14px;max-width:560px;width:100%;max-height:85vh;overflow:auto;padding:22px 24px;box-shadow:0 12px 48px rgba(0,0,0,.45)">
    <div style="display:flex;justify-content:space-between;align-items:center">
      <h2 style="font-family:'Fraunces',serif;font-size:18px;margin:0">📄 Research SEC · ${esc(ticker)}</h2>
      <button onclick="document.getElementById('research-overlay').remove()" style="background:none;border:none;font-size:18px;cursor:pointer;color:var(--ink-3)">✕</button>
    </div>
    <p style="font-size:11.5px;color:var(--ink-3);margin:4px 0 8px">Análisis del último 10-K/20-F oficial de SEC EDGAR, sintetizado por Claude.</p>
    <div id="research-body"><div style="padding:34px;text-align:center;color:var(--ink-3);font-size:13px">⟳ Descargando filing de SEC EDGAR y analizando…<br><span style="font-size:11px;opacity:.7">(puede tardar 10-20s la primera vez)</span></div></div>
  </div>`;
  try{
    const base=(typeof BASE!=='undefined')?BASE:'';
    const r = await fetch(`${base}/api/company/research/${encodeURIComponent(ticker)}`);
    const d = await r.json();
    const body = document.getElementById('research-body'); if(!body) return;
    if(d.error){ body.innerHTML=`<div style="padding:16px;color:#f59e0b;font-size:13px">⚠ ${esc(d.error)}</div>`; return; }
    const a=d.analysis||{};
    const sevCol=s=>/alta|high/i.test(s)?'#f87171':/media|med/i.test(s)?'#f59e0b':'#34d399';
    const bullets=arr=>(arr||[]).map(x=>`<div style="font-size:12.5px;line-height:1.45;margin-bottom:5px;padding-left:14px;position:relative"><span style="position:absolute;left:0;color:var(--blue)">•</span>${esc(x)}</div>`).join('');
    body.innerHTML = `
      <div style="font-size:11px;color:var(--ink-3);margin-bottom:6px">${esc(d.form_type||'')} · ${esc(d.filing_date||'')} · <a href="${safeUrl(d.source_url)}" target="_blank" rel="noopener noreferrer" style="color:var(--blue)">ver filing ↗</a></div>
      ${(a.resumen&&a.resumen.length)?`<div style="${rh}">Resumen del negocio</div>${bullets(a.resumen)}`:''}
      ${(a.riesgos&&a.riesgos.length)?`<div style="${rh}">Riesgos clave</div>${a.riesgos.map(rk=>`<div style="display:flex;gap:8px;align-items:baseline;padding:4px 0"><span style="font-size:9px;font-weight:800;color:${sevCol(rk.severidad||'')};min-width:46px">${esc((rk.severidad||'').toUpperCase())}</span><span style="font-size:12.5px;line-height:1.4">${esc(rk.riesgo||'')}</span></div>`).join('')}`:''}
      ${(a.tendencias&&a.tendencias.length)?`<div style="${rh}">Tendencias (MD&A)</div>${bullets(a.tendencias)}`:''}
      ${(a.confianza&&a.confianza.score!=null)?`<div style="margin-top:14px;padding:12px;background:var(--surface-2);border-radius:8px;display:flex;align-items:center;gap:12px"><div style="font-size:24px;font-weight:800;color:var(--ink-1)">${esc(a.confianza.score)}<span style="font-size:13px;color:var(--ink-3)">/10</span></div><div style="font-size:12px;color:var(--ink-2)">${esc(a.confianza.justificacion||'Confianza inversor')}</div></div>`:''}`;
  }catch(e){
    const body=document.getElementById('research-body');
    if(body) body.innerHTML=`<div style="padding:16px;color:#f87171;font-size:13px">No se pudo cargar: ${esc(e.message||e)}</div>`;
  }
};

function initSimTab() {
  if (_simInited) return;
  _simInited = true;

  // Ya no hay sonda de disponibilidad: ambos motores son INTERNOS (no
  // dependen de ningún microservicio externo que pueda estar caído).

  document.querySelectorAll('.sim-preset-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.sim-preset-btn').forEach(b => { b.style.borderColor=''; b.style.borderWidth=''; });
      btn.style.borderColor = 'var(--violet)'; btn.style.borderWidth = '2px';
      btn.dataset.active = '1';
      let scenarioText = '';
      if (window.ScenarioBuilder && ScenarioBuilder.PRESETS) {
        const preset = ScenarioBuilder.PRESETS[btn.dataset.preset];
        if (preset) scenarioText = preset.description || preset.title || preset.question || '';
      }
      // Fallback to the button's own descriptive text so the textarea is never
      // empty — otherwise the auto-run below aborts on the `if(!text)` guard.
      if (!scenarioText) scenarioText = btn.textContent.replace(/\s+/g, ' ').trim();
      const txtEl = document.getElementById('sim-custom-text');
      if (txtEl) txtEl.value = scenarioText;
      clearTimeout(btn._autoRun);
      btn._autoRun = setTimeout(() => {
        document.getElementById('sim-run-btn')?.click();
      }, 250);
    });
  });

  document.getElementById('sim-run-btn').addEventListener('click', async () => {
    const text = document.getElementById('sim-custom-text').value.trim();
    const nodeStr = document.getElementById('sim-custom-nodes').value.trim();
    const output = document.getElementById('sim-output');
    const status = document.getElementById('sim-status');
    const activeBtn = document.querySelector('.sim-preset-btn[data-active="1"]');
    const presetId = activeBtn?.dataset?.preset || null;
    if (!text) { toast('Escribe un escenario o selecciona un preset'); return; }
    // ancla determinista (no bloquea): factor real del preset, si lo tiene
    try { window._simGroundFactor && window._simGroundFactor(presetId); } catch (e) {}

    document.getElementById('sim-run-btn').disabled = true;
    const engine = document.querySelector('#sim-engine-seg button.active')?.dataset?.engine || 'simple';

    if (engine === 'agentes') {
      // Motor multi-agente INTERNO (core/sim_agents.py). Si falla, cae al
      // narrativo — igual que antes, pero sin depender de nada externo.
      const ok = await _runAgentSimTab(text, presetId, output, status);
      if (!ok) {
        _simSetStatus('run', window.LANG === 'en' ? 'Agent engine failed — using AI narrative'
                                                  : 'El motor de agentes falló — usando IA narrativa', '#f59e0b');
        await _runClaudeSim(text, nodeStr, output, status);
      }
    } else {
      await _runClaudeSim(text, nodeStr, output, status);   // motor IA Simple (multi-proveedor)
    }
    document.getElementById('sim-run-btn').disabled = false;
  });

  // Selector de motor + pista de estado
  document.querySelectorAll('#sim-engine-seg button').forEach(b => {
    b.addEventListener('click', () => {
      document.querySelectorAll('#sim-engine-seg button').forEach(x => x.classList.remove('active'));
      b.classList.add('active');
      const hint = document.getElementById('sim-engine-hint');
      const en = (window.LANG === 'en');
      if (hint) hint.textContent = b.dataset.engine === 'agentes'
        ? (en ? 'Each company debates as an agent · internal engine'
              : 'Cada empresa debate como agente · motor interno')
        : (en ? 'AI narrative · works with any provider'
              : 'Narrativa con IA · funciona con cualquier proveedor');
    });
  });
  document.getElementById('var-calc-btn').addEventListener('click', async () => {
    const positions = Object.entries(MKT.pos || {});
    if (!positions.length) { toast(LANG === 'en' ? 'Your active portfolio is empty: add stocks in Portfolios or in Market' : 'Tu cartera activa está vacía: agrega acciones en Carteras o en Mercado'); return; }
    const varResults = document.getElementById('var-results');
    const varLoading = document.getElementById('var-loading');
    const varContent = document.getElementById('var-content');
    varResults.style.display = 'block'; varLoading.style.display = 'block'; varContent.style.display = 'none';
    try {
      const posMap = {};
      // solo empresas que cotizan (con ticker): una privada/pre-IPO de la cartera (p. ej. OpenAI) no tiene precio de mercado
      positions.forEach(([id,p]) => { const n=NODE_BY_ID[id]; const tk=n?.mkt; if(tk&&p.sh>0) posMap[tk]={shares:p.sh,buy_price:p.bp}; });
      if (!Object.keys(posMap).length) {
        varResults.style.display = 'none';
        toast(LANG === 'en' ? 'Your active portfolio has no listed stocks (private companies have no market price)' : 'Tu cartera activa no tiene acciones que coticen en bolsa (las empresas privadas no tienen precio de mercado)');
        return;
      }
      const resp = await fetch('/api/portfolio-risk', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({positions: posMap})
      });
      if (!resp.ok) { const err=await resp.json(); throw new Error(err.error||resp.statusText); }
      const data = await resp.json();
      varLoading.style.display = 'none'; varContent.style.display = 'block';
      document.getElementById('var-95').textContent = data.var_95?.pct!=null?data.var_95.pct.toFixed(1)+'%':'—';
      document.getElementById('cvar-95').textContent = data.cvar_95?.pct!=null?data.cvar_95.pct.toFixed(1)+'%':'—';
      document.getElementById('sharpe-ratio').textContent = data.sharpe_ratio!=null?data.sharpe_ratio.toFixed(2):'—';
      document.getElementById('max-drawdown').textContent = data.max_drawdown_pct!=null?data.max_drawdown_pct.toFixed(1)+'%':'—';
    } catch(e) { varLoading.textContent = 'Error: '+e.message; varLoading.style.color='var(--danger)'; }
  });
}

// ── Terminal — lista + multi-gráfico (rediseño 2026-10-02) ─────────────────
// Pedido de Fabrizio: que la terminal "dé la impresión correcta". Misma lógica
// de siempre (lista → paneles con gráfico → 📋 datos → Operar), con jerarquía
// clara, textos ES/EN (_TT) y, en el teléfono, Lista y Gráficos alternados.
const _term = {
  layout: 4,
  cells: [],       // array of {nodeId, ticker, tf, chartInst}
  inited: false,
  _lastQuery: '',  // last sidebar filter query
  _lastCat: '',    // last sidebar sector/category filter
  view: 'list',    // teléfono: 'list' | 'charts'
};

// textos de la Terminal (regla bilingüe ES/EN)
const _TT = {
  es: {
    list: 'Empresas', listAria: 'Lista de empresas', search: 'Empresa o ticker…', searchAria: 'Buscar empresa o ticker',
    colName: 'Empresa', colPx: 'Precio · Día', allSectors: 'Todos los sectores', sectorAria: 'Filtrar por sector',
    panels: 'Paneles', l1: '1 gráfico', l2: '2 gráficos', l4: '4 gráficos', l6: '6 gráficos', l9: '9 gráficos',
    clear: 'Limpiar', clearTip: 'Vaciar todos los paneles',
    hint: 'Toca o arrastra una empresa de la lista para ver su gráfico',
    cmdPh: 'NVDA · /chart NVDA AMD · /sim taiwan · /geo', cmdAria: 'Línea de comandos', cmdHint: '↵ ejecutar',
    mList: 'Lista', mCharts: 'Gráficos',
    qLoading: 'Cargando precios…', qNone: 'Sin precios', qNoneTip: 'No llegaron precios de Finnhub ni de Yahoo: abre 🩺',
    qOk: '{n} con precio', qOkTip: 'Último precio disponible y su variación frente al cierre anterior. Pasa el cursor sobre el punto de cada fila para ver la fuente y la antigüedad.',
    qOkSrc: '{n} con precio · {src} · {ago}', qQuota: 'cuota de Finnhub agotada: precios vía Yahoo',
    qNoPx: 'sin precio ({ex})', qNoPxTip: 'Sin precio en vivo para esta bolsa ({ex})',
    noMatch: 'Ninguna empresa coincide con «{q}».',
    emptyT: 'Panel libre', emptyB: 'Toca una empresa de la lista o arrástrala aquí.',
    dossier: 'Dossier financiero: ingresos, márgenes, flujo de caja…', trade: 'Operar', tradeTip: 'Abrir el panel de compra / venta',
    close: 'Cerrar este panel', tfAria: 'Periodo del gráfico', loading: 'Cargando gráfico…', noData: 'Sin datos de precio para este periodo',
    hi: 'Máx', lo: 'Mín', dragTip: 'Toca para abrir · arrastra a un panel',
    unknownCmd: 'Comando no reconocido: ', noTickers: 'Sin tickers reconocidos: ',
    presets: 'Escenarios: taiwan · china · hbm · openai · star',
  },
  en: {
    list: 'Companies', listAria: 'Company list', search: 'Company or ticker…', searchAria: 'Search company or ticker',
    colName: 'Company', colPx: 'Price · Day', allSectors: 'All sectors', sectorAria: 'Filter by sector',
    panels: 'Panels', l1: '1 chart', l2: '2 charts', l4: '4 charts', l6: '6 charts', l9: '9 charts',
    clear: 'Clear', clearTip: 'Empty every panel',
    hint: 'Tap or drag a company from the list to see its chart',
    cmdPh: 'NVDA · /chart NVDA AMD · /sim taiwan · /geo', cmdAria: 'Command line', cmdHint: '↵ run',
    mList: 'List', mCharts: 'Charts',
    qLoading: 'Loading prices…', qNone: 'No prices', qNoneTip: 'No prices arrived from Finnhub or Yahoo: open 🩺',
    qOk: '{n} priced', qOkTip: 'Latest available price and its change versus the previous close. Hover the dot on each row for the source and age.',
    qOkSrc: '{n} priced · {src} · {ago}', qQuota: 'Finnhub quota exhausted: prices via Yahoo',
    qNoPx: 'no price ({ex})', qNoPxTip: 'No live price for this exchange ({ex})',
    noMatch: 'No company matches “{q}”.',
    emptyT: 'Empty panel', emptyB: 'Tap a company in the list or drag it here.',
    dossier: 'Financial dossier: revenue, margins, cash flow…', trade: 'Trade', tradeTip: 'Open the buy / sell panel',
    close: 'Close this panel', tfAria: 'Chart period', loading: 'Loading chart…', noData: 'No price data for this period',
    hi: 'High', lo: 'Low', dragTip: 'Tap to open · drag to a panel',
    unknownCmd: 'Unknown command: ', noTickers: 'No recognized tickers: ',
    presets: 'Scenarios: taiwan · china · hbm · openai · star',
  },
};
function _tt(k) {
  const d = _TT[(typeof LANG !== 'undefined' && LANG === 'en') ? 'en' : 'es'];
  return d[k] != null ? d[k] : (_TT.es[k] != null ? _TT.es[k] : k);
}
const _termIsPhone = () => window.innerWidth <= 560;
const _TERM_ICON = {
  chart: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 3v18h18"/><path d="m7 15 4-4 3 3 5-6"/></svg>',
  doc: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></svg>',
  x: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg>',
};

// Re-etiqueta los textos fijos (data-tt / -ph / -title / -aria) al cambiar de idioma
window._termRelabel = function() {
  const root = document.getElementById('terminal-panel');
  if (!root) return;
  root.querySelectorAll('[data-tt]').forEach(el => { el.textContent = _tt(el.dataset.tt); });
  root.querySelectorAll('[data-tt-ph]').forEach(el => { el.placeholder = _tt(el.dataset.ttPh); });
  root.querySelectorAll('[data-tt-title]').forEach(el => { el.title = _tt(el.dataset.ttTitle); });
  root.querySelectorAll('[data-tt-aria]').forEach(el => { el.setAttribute('aria-label', _tt(el.dataset.ttAria)); });
  if (_term.inited) {
    _termBuildSidebar();
    try { if (window.TermData && window.TermData.relabel) window.TermData.relabel(); } catch (e) {}
  }
};
if (typeof applyLang === 'function') {
  const _applyLangTerm = applyLang;
  applyLang = function() { _applyLangTerm.apply(this, arguments); try { window._termRelabel(); } catch (e) {} };
}

function initTerminalTab() {
  if (!_term.inited) {
    _term.inited = true;
    // teléfono: 4 gráficos en 390px no se leen — arranca con uno grande
    if (_termIsPhone() && _term.layout > 1) _term.layout = 1;
    // panel 📋 Datos montado desde el inicio: su interruptor queda SIEMPRE en la barra
    try { if (window.TermData && window.TermData.mount) window.TermData.mount(); } catch (e) {}
    window._termRelabel();   // textos ES/EN + arma la lista (sectores y empresas)
    // Tocar/clic (o Enter) en una empresa la abre en el primer panel libre;
    // arrastrarla la deja en el panel que elijas.
    const tl = document.getElementById('term-list');
    if (tl) {
      tl.addEventListener('click', e => { const it = e.target.closest('.term-item'); if (it) _termOpenFromList(it); });
      tl.addEventListener('keydown', e => {
        if (e.key !== 'Enter' && e.key !== ' ') return;
        const it = e.target.closest('.term-item'); if (!it) return;
        e.preventDefault(); _termOpenFromList(it);
      });
      tl.addEventListener('dragstart', e => { const it = e.target.closest('.term-item'); if (it) window._termDragStart(e, it.dataset.id, it.dataset.mkt); });
      tl.addEventListener('dragend', e => { const it = e.target.closest('.term-item'); if (it) it.classList.remove('dragging'); });
    }
    const grid = document.getElementById('term-grid');
    if (grid) grid.addEventListener('click', _termGridClick);
    // cambio de tema claro/oscuro: los gráficos (canvas) toman los colores nuevos
    try { new MutationObserver(_termRecolor).observe(document.body, { attributes: true, attributeFilter: ['class'] }); } catch (e) {}
    let rt = null;
    window.addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(() => _termApplyGrid(_term.layout), 120); });
  }
  const hadCharts = _term.cells.some(c => c && c.nodeId);   // antes de reconstruir la grilla
  _termSetLayout(_term.layout, true);
  _initTermCmdBar();
  if (!_term.seeded) { _term.seeded = true; setTimeout(_termSeed, 400); }
  // teléfono: respeta la última vista elegida; si no, gráficos cuando hay alguno abierto
  if (_termIsPhone()) window._termView(_term.userView ? _term.view : (hadCharts ? 'charts' : 'list'));
  // If quotes are absent or stale (>10 min), refresh them now so the sidebar
  // can show live prices.  MKT.ts is null until the first successful fetch.
  const STALE_MS = 10 * 60 * 1000;
  if (!MKT.ts || Date.now() - MKT.ts > STALE_MS) {
    if (typeof fetchQuotes === 'function') fetchQuotes();
  }
}

// Primera apertura: los paneles VACÍOS se llenan con tus posiciones (MKT.pos = tu
// cartera activa, engine/pfstore.js) y luego con anclas de la cadena de IA — así la Terminal nunca
// abre como cuatro cajas vacías. Solo gráficos de datos reales (/api/candles).
const _TERM_SEED = ['NVDA', 'TSM', 'ASML', 'AVGO', 'AMD', 'MSFT', 'GOOGL', 'MU', 'META'];
function _termSeed() {
  const NDS = window.NODES || [];
  const byMkt = {}; NDS.forEach(n => { if (n.mkt && !byMkt[n.mkt]) byMkt[n.mkt] = n; });
  const mine = Object.keys((window.MKT && MKT.pos) || {}).map(id => (window.NODE_BY_ID || {})[id]).filter(n => n && n.mkt);
  const pool = mine.concat(_TERM_SEED.map(t => byMkt[t]).filter(Boolean));
  const seen = new Set(_term.cells.filter(c => c && c.nodeId).map(c => c.nodeId));
  let any = false;
  _term.cells.forEach((c, i) => {
    if (c && c.nodeId) return;
    const n = pool.find(x => !seen.has(x.id));
    if (!n) return;
    seen.add(n.id); any = true;
    _termLoadCell(i, n.id, n.mkt, '1M');
  });
  if (any && _termIsPhone() && _term.view === 'list' && !_term.userView) window._termView('charts');
}

// teléfono: alterna Lista / Gráficos (en pantallas anchas ambas se ven siempre)
window._termView = function(v, byUser) {
  const sh = document.getElementById('term-shell');
  if (!sh) return;
  if (byUser) _term.userView = true;
  _term.view = v === 'charts' ? 'charts' : 'list';
  sh.dataset.view = _term.view;
  sh.querySelectorAll('.kt-mtab').forEach(b => b.setAttribute('aria-selected', b.dataset.v === _term.view ? 'true' : 'false'));
  if (_term.view === 'charts') setTimeout(() => _term.cells.forEach(c => { try { if (c && c.chartInst) c.chartInst.resize(); } catch (e) {} }), 40);
};

function _termOpenFromList(it) {
  const id = it.dataset.id, mkt = it.dataset.mkt;
  const open = _term.cells.findIndex(c => c && c.nodeId === id);
  if (open >= 0) {
    // ya está abierta: no duplicarla — se resalta su panel y se muestran sus datos
    try { window.TermData && window.TermData.load(id, mkt); } catch (e) {}
    _termFlash(open);
  } else {
    let idx = _term.cells.findIndex(c => !c.nodeId);
    if (idx < 0) idx = 0;
    _termLoadCell(idx, id, mkt, (_term.cells[idx] && _term.cells[idx].tf) || '1M');
  }
  if (_termIsPhone()) window._termView('charts');
}

function _initTermCmdBar() {
  const input = document.getElementById('term-cmd');
  if (!input || input._wired) return;
  input._wired = true;
  input.addEventListener('keydown', e => {
    if (e.key !== 'Enter') return;
    const cmd = input.value.trim(); if (!cmd) return;
    input.value = '';
    _execTermCmd(cmd);
  });
}

function _execTermCmd(cmd) {
  const lower = cmd.toLowerCase().trim();
  const NDS = window.NODES || [];
  const findNode = sym => NDS.find(n =>
    n.id === sym || n.mkt === sym ||
    (n.mkt || '').split('·')[0].trim().toUpperCase() === sym ||
    (n.label || '').toUpperCase() === sym);

  // /sim <preset>
  if (lower.startsWith('/sim')) {
    const presetMap = { taiwan: 'taiwan_conflict', china: 'china_chip_ban_total', hbm: 'hbm_shortage_2027', openai: 'openai_ipo_impact', star: 'starshield_reveal' };
    const key = Object.keys(presetMap).find(k => lower.includes(k));
    if (key && window.nexusCore?.runPreset) { window.nexusCore.runPreset(presetMap[key]); return; }
    if (typeof toast === 'function') toast(_tt('presets'));
    return;
  }
  // /geo
  if (lower.startsWith('/geo')) { switchTab('geo'); return; }

  // /chart TK1 TK2 …  — or 2+ bare uppercase tickers ("NVDA AMD")
  const upperTickers = cmd.match(/\b[A-Z]{2,6}\b/g) || [];
  if (lower.startsWith('/chart') || upperTickers.length >= 2) {
    const syms = (lower.startsWith('/chart')
      ? (cmd.replace(/\/chart/i, '').match(/\b[A-Z]{2,6}\b/g) || [])
      : upperTickers);
    let loaded = 0;
    syms.slice(0, _term.cells.length || 4).forEach((sym, i) => {
      const n = findNode(sym);
      if (n && _term.cells[i] !== undefined) {
        _termLoadCell(i, n.id, n.mkt || sym, _term.cells[i]?.tf || '1M');
        loaded++;
      }
    });
    if (!loaded && typeof toast === 'function') toast(_tt('noTickers') + syms.join(', '));
    else if (loaded && _termIsPhone()) window._termView('charts');
    return;
  }

  // Single ticker lookup: NVDA, TSMC, "NVDA Equity"…
  const sym = (cmd.trim().toUpperCase().split(/\s+/)[0]) || '';
  const n = findNode(sym);
  if (n) { window._termLoadToFirstEmpty(n.id, n.mkt); if (_termIsPhone()) window._termView('charts'); return; }

  // Fallback: send to Claude analysis
  switchTab('analysis');
  const ai = document.getElementById('ai-input');
  if (ai) { ai.value = cmd; document.getElementById('ai-ask-btn')?.click(); }
  else if (typeof toast === 'function') toast(_tt('unknownCmd') + cmd);
}

// panel que ya muestra esa empresa → se resalta (no se duplica)
function _termFlash(idx) {
  const cell = document.getElementById('term-grid')?.children[idx];
  if (cell) { cell.classList.add('drag-over'); setTimeout(() => cell.classList.remove('drag-over'), 650); }
}
window._termLoadToFirstEmpty = function(nodeId, ticker) {
  const node = (window.NODES || []).find(n => n.id === nodeId);
  const tk = ticker || node?.mkt || nodeId;
  const open = _term.cells.findIndex(c => c && c.nodeId === nodeId);
  if (open >= 0) { _termFlash(open); try { window.TermData && window.TermData.load(nodeId, tk); } catch (e) {} return; }
  let idx = _term.cells.findIndex(c => !c.nodeId);
  if (idx < 0) idx = 0; // grid full → overwrite first panel
  _termLoadCell(idx, nodeId, tk, _term.cells[idx]?.tf || '1M');
};

// macro-sector (SECTORS9) de una empresa: 13 grupos legibles en vez de 40 categorías
const _termSectorOf = n => (window.CAT_TO_SECTOR || {})[n.cat] || 'cloud_ia';
window._termCat = () => _term._lastCat || '';

function _termBuildSidebar() {
  const nodes = (window.NODES || []).filter(n => n.mkt);
  const cnt = {};
  nodes.forEach(n => { const k = _termSectorOf(n); cnt[k] = (cnt[k] || 0) + 1; });
  const keys = Object.keys(cnt).sort((a, b) => cnt[b] - cnt[a]);
  const catEl = document.getElementById('term-cats');
  if (catEl) {
    const cur = _term._lastCat || '';
    catEl.innerHTML = `<select class="kt-select" id="term-sector" aria-label="${esc(_tt('sectorAria'))}">` +
      `<option value="">${esc(_tt('allSectors'))} · ${nodes.length}</option>` +
      keys.map(k => `<option value="${esc(k)}"${k === cur ? ' selected' : ''}>${esc(window.sectorName ? window.sectorName(k) : k)} · ${cnt[k]}</option>`).join('') +
      `</select>`;
    catEl.querySelector('select').onchange = e => window._termFilter(document.getElementById('term-search')?.value || '', e.target.value);
  }
  window._termFilter(_term._lastQuery, _term._lastCat);
}

// Re-render sidebar prices after a quote refresh without a full rebuild.
// Called by _processMktData so any tab that triggers fetchQuotes()
// (Market refresh, Terminal auto-fetch, etc.) keeps the Terminal in sync.
window._termRefreshPrices = function() {
  if (!_term.inited) return; // Terminal never opened — nothing to update
  const filter = document.getElementById('term-search')?.value || _term._lastQuery || '';
  window._termFilter(filter, _term._lastCat || '');
  // cabeceras de los paneles abiertos (precio/variación del día)
  _term.cells.forEach((c, i) => { if (c && c.nodeId) _termPaintQuote(i, c.ticker); });
};

// cotización de MKT.quotes (contrato: live NUMÉRICO o close; src + as_of = fuente y antigüedad)
function _termQuote(tk) {
  const q = (window.MKT && MKT.quotes && MKT.quotes[tk]) || null;
  const px = window.quotePx ? quotePx(q) : 0;
  const prev = q ? (parseFloat(q.prev || 0) || 0) : 0;
  return { px, pct: px && prev ? (px - prev) / prev * 100 : null, q };
}
function _termFmtPx(v) {
  if (!v || !isFinite(v)) return '—';
  const d = Math.abs(v) < 1 ? 4 : 2;
  return '$' + v.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
}
// variación: color SOLO con significado (sube / baja / sin dato)
function _termFmtPct(p, arrow) {
  if (p == null || !isFinite(p)) return { t: '—', c: 'kt-flat' };
  const c = p > 0.0049 ? 'kt-up' : p < -0.0049 ? 'kt-down' : 'kt-flat';
  const a = arrow ? (c === 'kt-up' ? '▲ ' : c === 'kt-down' ? '▼ ' : '') : '';
  return { t: a + (p > 0 ? '+' : p < 0 ? '−' : '') + Math.abs(p).toFixed(2) + '%', c };
}

function _termRenderList(nodes) {
  const el = document.getElementById('term-list');
  if (!el) return;
  // estado de precios (sobre TODO el catálogo con ticker, no solo el filtro)
  const st = document.getElementById('term-qstatus');
  if (st) {
    // El estado se basa en CUÁNTOS tickers tienen precio y de qué fuente (no en
    // MKT.ts, que el lote en vivo antes nunca fijaba → "Cargando precios…" eterno).
    const all = (window.NODES || []).filter(n => n.mkt);
    let withPrice = 0, newest = null; const srcs = {};
    all.forEach(n => { const q = _termQuote(n.mkt); if (!(q.px > 0)) return; withPrice++;
      const s = (q.q && q.q.src) || 'cache'; srcs[s] = (srcs[s] || 0) + 1;
      const a = window.quoteAge ? quoteAge(q.q) : null; if (a != null && (newest == null || a < newest)) newest = a; });
    const lm = (window.MKT && MKT.liveMeta) || null;
    const loading = !!window._liveLoading || (!lm && !withPrice);
    if (!withPrice && loading) { st.className = 'kt-qs'; st.title = ''; st.innerHTML = '<i></i>' + esc(_tt('qLoading')); }
    else if (!withPrice) { st.className = 'kt-qs warn'; st.title = _tt('qNoneTip'); st.innerHTML = '<i></i>' + esc(_tt('qNone')); }
    else {
      const names = Object.keys(srcs).sort((a, b) => srcs[b] - srcs[a]).map(k => window.quoteSrcName ? quoteSrcName(k) : k).filter(Boolean);
      const src = names.slice(0, 2).join('/') || '—';
      const ago = newest != null && window.quoteAgoText ? quoteAgoText(newest) : '';
      const quota = !!(lm && lm.finnhub_quota);
      st.className = 'kt-qs ' + (quota ? 'warn' : 'ok');
      st.title = (quota ? _tt('qQuota') + ' · ' : '') + _tt('qOkTip');
      st.innerHTML = '<i></i>' + esc(ago ? _tt('qOkSrc').replace('{n}', withPrice).replace('{src}', src).replace('{ago}', ago)
                                         : _tt('qOk').replace('{n}', withPrice) + ' · ' + src);
    }
  }
  const open = new Set(_term.cells.filter(c => c && c.nodeId).map(c => c.nodeId));
  const tip = esc(_tt('dragTip'));
  el.innerHTML = nodes.length ? nodes.map(n => {
    const q = _termQuote(n.mkt), f = _termFmtPct(q.pct);
    const chip = window.quoteSrcChip ? quoteSrcChip(q.q, n.mkt) : '';
    const ex = window.quoteExchange ? quoteExchange(n.mkt) : '';
    const chg = q.px > 0 ? `<div class="kt-chg ${f.c}">${f.t}</div>`
      : `<div class="kt-chg kt-flat kt-nopx" title="${esc(_tt('qNoPxTip').replace('{ex}', ex))}">${esc(_tt('qNoPx').replace('{ex}', ex))}</div>`;
    return `<div class="term-item${open.has(n.id) ? ' on' : ''}" role="listitem" tabindex="0" draggable="true" data-id="${esc(n.id)}" data-mkt="${esc(n.mkt)}" title="${tip}">` +
      `<span class="kt-dot" style="background:${sectorColorFor(n.cat)}"></span>` +
      `<div style="min-width:0"><div class="kt-nm">${esc(n.label)}</div><div class="kt-tk">${esc(n.mkt)}</div></div>` +
      `<div class="kt-q"><div class="kt-px">${_termFmtPx(q.px)}${chip}</div>${chg}</div></div>`;
  }).join('') : `<div class="kt-empty-list">${esc(_tt('noMatch').replace('{q}', _term._lastQuery || ''))}</div>`;
}
// marca en la lista las empresas abiertas en algún panel + contador del teléfono
function _termMarkOpen() {
  const open = new Set(_term.cells.filter(c => c && c.nodeId).map(c => c.nodeId));
  document.querySelectorAll('#term-list .term-item').forEach(it => it.classList.toggle('on', open.has(it.dataset.id)));
  const mc = document.getElementById('term-mcount');
  if (mc) mc.textContent = open.size ? String(open.size) : '';
}

window._termFilter = function(query, cat) {
  _term._lastQuery = query || '';
  _term._lastCat = cat || '';
  let nodes = (window.NODES || []).filter(n => n.mkt);
  if (cat) {
    // acepta un macro-sector (SECTORS9) o, por compatibilidad, una categoría
    const isSector = !!(window.SECTORS9 || {})[cat];
    nodes = nodes.filter(n => isSector ? _termSectorOf(n) === cat : n.cat === cat);
  }
  if (query) {
    const q = query.toLowerCase().trim();
    nodes = nodes.filter(n => n.label.toLowerCase().includes(q) || n.mkt.toLowerCase().includes(q));
  }
  nodes.sort((a,b) => a.label.localeCompare(b.label));
  _termRenderList(nodes);
};

// columnas/filas de la grilla (teléfono: siempre una columna)
function _termApplyGrid(n) {
  const grid = document.getElementById('term-grid');
  if (!grid) return;
  const cols = _termIsPhone() ? 1 : n <= 1 ? 1 : n <= 4 ? 2 : 3;
  const rows = Math.max(1, Math.ceil(n / cols));
  grid.style.gridTemplateColumns = `repeat(${cols}, minmax(0, 1fr))`;
  grid.style.gridTemplateRows = `repeat(${rows}, minmax(0, 1fr))`;
}

window._termSetLayout = function(n, silent) {
  _term.layout = n;
  document.querySelectorAll('.term-layout-btn').forEach(b => {
    const isActive = +b.dataset.l === n;
    b.classList.toggle('active-layout', isActive);
    b.setAttribute('aria-pressed', isActive ? 'true' : 'false');
  });
  const grid = document.getElementById('term-grid');
  if (!grid) return;
  _termApplyGrid(n);

  // Preserve existing assignments
  const existing = _term.cells.slice(0, n);
  _term.cells.forEach(c => { try { if (c && c.chartInst) c.chartInst.destroy(); } catch (e) {} });
  _term.cells = [];
  grid.innerHTML = '';
  for (let i = 0; i < n; i++) {
    const cell = _termMakeCell(i);
    grid.appendChild(cell);
    _term.cells.push({ nodeId: null, ticker: null, tf: '1M', chartInst: null });
    if (existing[i]?.nodeId) {
      setTimeout(() => _termLoadCell(i, existing[i].nodeId, existing[i].ticker, existing[i].tf), 50);
    }
  }
  _termMarkOpen();
};

function _termMakeCell(idx) {
  const div = document.createElement('div');
  div.className = 'term-cell';
  div.dataset.idx = idx;
  div.innerHTML = `<div class="term-cell-empty">${_TERM_ICON.chart}` +
    `<b data-tt="emptyT">${esc(_tt('emptyT'))}</b><span data-tt="emptyB">${esc(_tt('emptyB'))}</span></div>`;
  div.addEventListener('dragover', e => { e.preventDefault(); div.classList.add('drag-over'); });
  div.addEventListener('dragleave', () => div.classList.remove('drag-over'));
  div.addEventListener('drop', e => {
    e.preventDefault();
    div.classList.remove('drag-over');
    const id = e.dataTransfer.getData('nodeId');
    const mkt = e.dataTransfer.getData('ticker');
    if (id && mkt) _termLoadCell(idx, id, mkt, _term.cells[idx]?.tf || '1M');
  });
  return div;
}

window._termDragStart = function(e, id, mkt) {
  e.dataTransfer.setData('nodeId', id);
  e.dataTransfer.setData('ticker', mkt);
  const it = (e.target && e.target.closest && e.target.closest('.term-item')) || e.currentTarget;
  if (it && it.classList) it.classList.add('dragging');
};

// botones de los paneles (delegado): periodo, dossier, operar, cerrar; panel vacío → buscar
function _termGridClick(e) {
  const b = e.target.closest('[data-act]');
  const cellEl = e.target.closest('.term-cell');
  if (!cellEl) return;
  const idx = +cellEl.dataset.idx;
  const c = _term.cells[idx];
  if (!b) {
    if (!c || !c.nodeId) {
      if (_termIsPhone()) window._termView('list');
      else document.getElementById('term-search')?.focus();
    }
    return;
  }
  const act = b.dataset.act;
  if (act === 'tf') return window._termChangeTf(idx, b.dataset.tf);
  if (act === 'close') return window._termClearCell(idx);
  if (!c || !c.nodeId) return;
  if (act === 'dossier') { if (window.openFinCard) window.openFinCard(c.ticker); return; }
  if (act === 'trade') {
    const node = (window.NODES || []).find(n => n.id === c.nodeId);
    if (typeof openTradeModal === 'function') openTradeModal(c.nodeId, c.ticker, node?.label || c.ticker);
  }
}

// precio y variación del día en la cabecera de un panel
function _termPaintQuote(idx, ticker, fallbackPx) {
  const q = _termQuote(ticker);
  const pxEl = document.getElementById(`term-px-${idx}`), chEl = document.getElementById(`term-chg-${idx}`);
  const px = q.px || fallbackPx || 0;
  if (pxEl) pxEl.textContent = _termFmtPx(px);
  if (chEl) { const f = _termFmtPct(q.px ? q.pct : null, true); chEl.className = 'kt-ch-chg ' + f.c; chEl.textContent = f.t; }
}

// color del token CSS de la Terminal (los gráficos de canvas no leen var())
function _termTok(name, dflt) {
  try { const v = getComputedStyle(document.getElementById('terminal-panel')).getPropertyValue(name).trim(); return v || dflt; }
  catch (e) { return dflt; }
}
function _termAlpha(color, a) {
  const m = /^#([0-9a-f]{6})$/i.exec(color || '');
  if (!m) return color;
  const n = parseInt(m[1], 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}

async function _termLoadCell(idx, nodeId, ticker, tf) {
  const grid = document.getElementById('term-grid');
  if (!grid) return;
  const cell = grid.children[idx];
  if (!cell) return;

  if (_term.cells[idx]?.chartInst) { try { _term.cells[idx].chartInst.destroy(); } catch (e) {} }
  const slot = { nodeId, ticker, tf, chartInst: null };
  _term.cells[idx] = slot;
  // panel de datos (📋): ficha + valuación + fundamentales + cadena
  try { window.TermData?.load(nodeId, ticker); } catch (e) {}

  const node = (window.NODES || []).find(n => n.id === nodeId);
  const label = node?.label || ticker;
  const dot = node ? sectorColorFor(node.cat) : 'var(--kt-accent)';
  const tfs = ['1D','1W','1M','3M','1Y'];

  cell.innerHTML =
    `<div class="term-cell-header">` +
      `<div class="kt-ch-id"><span class="kt-dot" style="background:${dot}"></span>` +
        `<span class="kt-ch-tk">${esc(ticker)}</span><span class="kt-ch-nm" title="${esc(label)}">${esc(label)}</span></div>` +
      `<div class="kt-ch-q"><span class="kt-ch-px" id="term-px-${idx}">—</span><span class="kt-ch-chg kt-flat" id="term-chg-${idx}">—</span></div>` +
      `<div class="kt-ch-ctl">` +
        `<div class="kt-tf" role="group" data-tt-aria="tfAria" aria-label="${esc(_tt('tfAria'))}">` +
          tfs.map(t => `<button type="button" class="term-tf-btn${t === tf ? ' active' : ''}" aria-pressed="${t === tf}" data-act="tf" data-tf="${t}">${t}</button>`).join('') +
        `</div>` +
        `<button type="button" class="kt-ic" data-act="dossier" data-tt-title="dossier" data-tt-aria="dossier" title="${esc(_tt('dossier'))}" aria-label="${esc(_tt('dossier'))}">${_TERM_ICON.doc}</button>` +
        `<button type="button" class="kt-trade" data-act="trade" data-tt-title="tradeTip" title="${esc(_tt('tradeTip'))}"><span data-tt="trade">${esc(_tt('trade'))}</span></button>` +
        `<button type="button" class="kt-ic" data-act="close" data-tt-title="close" data-tt-aria="close" title="${esc(_tt('close'))}" aria-label="${esc(_tt('close'))}">${_TERM_ICON.x}</button>` +
      `</div>` +
    `</div>` +
    `<div class="kt-stats" id="term-stats-${idx}" aria-live="polite"></div>` +
    `<div class="term-chart-wrap">` +
      `<canvas id="term-canvas-${idx}" role="img" aria-label="${esc(label)} · ${tf}"></canvas>` +
      `<div class="kt-loading" id="term-loading-${idx}"><span class="kt-spin" aria-hidden="true"></span><span data-tt="loading">${esc(_tt('loading'))}</span></div>` +
    `</div>`;
  _termPaintQuote(idx, ticker);
  _termMarkOpen();

  // Load chart data
  try {
    const BASE = '';
    const rangeMap = {'1D':'1d','1W':'5d','1M':'1mo','3M':'3mo','1Y':'1y'};
    const res = await fetch(`${BASE}/api/candles/${encodeURIComponent(ticker)}?range=${rangeMap[tf]||'1mo'}&interval=${tf==='1D'?'5m':tf==='1W'?'30m':'1d'}`);
    const data = await res.json();
    if (_term.cells[idx] !== slot) return;          // otro ticker/periodo tomó el panel mientras cargaba
    const loader = document.getElementById(`term-loading-${idx}`);
    const canvas = document.getElementById(`term-canvas-${idx}`);
    const closes = (data && Array.isArray(data.c)) ? data.c.map(Number) : [];
    const pts = closes.filter(v => isFinite(v) && v > 0);
    if (!canvas || pts.length < 2) {
      if (loader) { loader.className = 'kt-loading err'; loader.innerHTML = `<span data-tt="noData">${esc(_tt('noData'))}</span>`; }
      return;
    }
    if (loader) loader.style.display = 'none';

    // estadísticas del periodo (de la serie real): variación, máximo, mínimo
    const first = pts[0], last = pts[pts.length - 1];
    const chg = (last / first - 1) * 100, f = _termFmtPct(chg);
    const stats = document.getElementById(`term-stats-${idx}`);
    if (stats) stats.innerHTML =
      `<span>${tf}<b class="${f.c}">${f.t}</b></span>` +
      `<span><i data-tt="hi">${esc(_tt('hi'))}</i><b>${_termFmtPx(Math.max(...pts))}</b></span>` +
      `<span><i data-tt="lo">${esc(_tt('lo'))}</i><b>${_termFmtPx(Math.min(...pts))}</b></span>`;
    if (!_termQuote(ticker).px) _termPaintQuote(idx, ticker, last);   // sin cotización: último cierre de la serie

    const loc = (typeof LANG !== 'undefined' && LANG === 'en') ? 'en-US' : 'es';
    const labels = data.t ? data.t.map(t => {
      const d = new Date(t * 1000);
      return tf === '1D' ? d.toLocaleTimeString(loc, { hour: '2-digit', minute: '2-digit' })
           : d.toLocaleDateString(loc, { month: 'short', day: 'numeric' });
    }) : closes.map((_, i) => i);

    const color = chg >= 0 ? _termTok('--kt-up', '#2EBD85') : _termTok('--kt-down', '#F6465D');
    const TICK = _termTok('--kt-ink-3', '#6E7586'), GRIDC = _termTok('--kt-line', 'rgba(255,255,255,.07)');
    const TIPBG = _termTok('--kt-panel-2', '#171B25'), INK = _termTok('--kt-ink', '#E7E9EF'), LINE2 = _termTok('--kt-line-2', 'rgba(255,255,255,.13)');
    const MONO = "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";   // sin la fuente → monoespaciada del sistema, nunca serif
    const inst = new Chart(canvas, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          data: closes,
          borderColor: color,
          borderWidth: 1.6,
          pointRadius: 0,
          pointHoverRadius: 3,
          pointHoverBackgroundColor: color,
          fill: true,
          backgroundColor: (ctx) => {
            const g = ctx.chart.ctx.createLinearGradient(0, 0, 0, ctx.chart.height || 200);
            g.addColorStop(0, _termAlpha(color, 0.18));
            g.addColorStop(1, _termAlpha(color, 0));
            return g;
          },
          tension: 0.25,
          spanGaps: true,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false, animation: false,
        interaction: { mode: 'index', intersect: false },
        // panel bajo (6/9 paneles): sin fechas abajo → la línea usa todo el alto
        onResize: (ch, size) => { const show = size.height > 150; if (ch.options.scales.x.ticks.display !== show) { ch.options.scales.x.ticks.display = show; ch.update('none'); } },
        plugins: { legend: { display: false }, tooltip: {
          backgroundColor: TIPBG, borderColor: LINE2, borderWidth: 1, titleColor: TICK, bodyColor: INK,
          titleFont: { family: MONO, size: 10 }, bodyFont: { family: MONO, size: 12, weight: '600' },
          displayColors: false, padding: 8,
          callbacks: { label: ctx => _termFmtPx(ctx.parsed.y) }
        }},
        scales: {
          x: { grid: { display: false }, border: { display: false },
            ticks: { display: (canvas.parentElement?.clientHeight || 0) > 150, color: TICK, font: { family: MONO, size: 10 }, maxTicksLimit: 5, maxRotation: 0, autoSkip: true } },
          y: {
            position: 'right',
            grid: { color: GRIDC }, border: { display: false },
            ticks: { color: TICK, font: { family: MONO, size: 10 }, maxTicksLimit: 5,
              callback: v => '$' + (Math.abs(v) >= 100 ? v.toFixed(0) : Math.abs(v) >= 1 ? v.toFixed(2) : v.toFixed(4)) }
          }
        }
      }
    });
    if (_term.cells[idx] === slot) slot.chartInst = inst; else inst.destroy();
    _term._themeDark = document.body.classList.contains('dark');
  } catch(e) {
    try { console.warn('[terminal] gráfico', ticker, tf, e); } catch (e2) {}
    if (_term.cells[idx] !== slot) return;
    const loader = document.getElementById(`term-loading-${idx}`);
    if (loader) { loader.className = 'kt-loading err'; loader.innerHTML = `<span data-tt="noData">${esc(_tt('noData'))}</span>`; }
  }
}

// re-pinta los gráficos abiertos con los tokens del tema activo (sin pedir datos otra vez)
function _termRecolor() {
  const dark = document.body.classList.contains('dark');
  if (_term._themeDark === dark) return;
  _term._themeDark = dark;
  const UP = _termTok('--kt-up', '#2EBD85'), DOWN = _termTok('--kt-down', '#F6465D');
  const TICK = _termTok('--kt-ink-3', '#6E7586'), GRIDC = _termTok('--kt-line', 'rgba(255,255,255,.07)');
  const TIPBG = _termTok('--kt-panel-2', '#171B25'), INK = _termTok('--kt-ink', '#E7E9EF'), LINE2 = _termTok('--kt-line-2', 'rgba(255,255,255,.13)');
  _term.cells.forEach(c => {
    const ch = c && c.chartInst; if (!ch) return;
    try {
      const ds = ch.data.datasets[0], v = (ds.data || []).filter(x => isFinite(x) && x > 0);
      const col = v.length > 1 && v[v.length - 1] < v[0] ? DOWN : UP;
      ds.borderColor = col; ds.pointHoverBackgroundColor = col;
      ds.backgroundColor = (ctx) => { const g = ctx.chart.ctx.createLinearGradient(0, 0, 0, ctx.chart.height || 200); g.addColorStop(0, _termAlpha(col, 0.18)); g.addColorStop(1, _termAlpha(col, 0)); return g; };
      ch.options.scales.x.ticks.color = TICK; ch.options.scales.y.ticks.color = TICK; ch.options.scales.y.grid.color = GRIDC;
      Object.assign(ch.options.plugins.tooltip, { backgroundColor: TIPBG, borderColor: LINE2, titleColor: TICK, bodyColor: INK });
      ch.update('none');
    } catch (e) {}
  });
}

window._termChangeTf = function(idx, tf) {
  const c = _term.cells[idx];
  if (!c?.nodeId) return;
  if (c.chartInst) { c.chartInst.destroy(); c.chartInst = null; }
  _termLoadCell(idx, c.nodeId, c.ticker, tf);
};

window._termClearCell = function(idx) {
  if (_term.cells[idx]?.chartInst) _term.cells[idx].chartInst.destroy();
  _term.cells[idx] = { nodeId: null, ticker: null, tf: '1M', chartInst: null };
  const grid = document.getElementById('term-grid');
  if (!grid) return;
  const old = grid.children[idx];
  if (old) {
    const fresh = _termMakeCell(idx);
    grid.replaceChild(fresh, old);
  }
  _termMarkOpen();
};

window._termClearAll = function() {
  const n = _term.layout;
  for (let i = 0; i < n; i++) _termClearCell(i);
};

// Khipu integration — load a ticker into the next free Terminal cell
window._termOpenTicker = function(ticker) {
  const node = (window.NODES || []).find(n => n.mkt === ticker || n.id === ticker);
  if (!node?.mkt) return false;
  // Switch to terminal tab first
  if (typeof switchTab === 'function') switchTab('terminal');
  setTimeout(() => {
    if (!_term.inited) initTerminalTab();
    window._termLoadToFirstEmpty(node.id, node.mkt);   // ya abierta → se resalta, no se duplica
    if (_termIsPhone()) window._termView('charts');
  }, 300);
  return true;
};

// ── Space Tab = SPACE MONITOR (engine/spacemonitor.js, 2026-09-30) ─────────
// mount() es idempotente: la 1ª vez arma el globo (plataformas, arcos de ascenso,
// satélites CelesTrak con telemetría al clic) y carga /api/space2/*; después
// re-etiqueta, redimensiona y reanuda el render. Lo llaman switchTab('space') y
// la Cabina (ADOPT_TABS.space). La lista de lanzamientos, las tarjetas y el
// Planetarium sueltos se retiraron (todo vive en el Space Monitor).
function initSpaceTab() {
  const root = document.getElementById('sp-root');
  if (root && window.KhipuSpace) window.KhipuSpace.mount(root);
}

// ── Globo geopolítico 3D → ahora es el World Monitor (engine/worldmonitor.js).
// Alias de compatibilidad por si algún llamador externo aún lo usa.

// ── NexusCore: simulation orchestrator ───────────────────────────────────────
window.nexusCore = {
  async runPreset(presetId) {
    switchTab('simulation');
    await new Promise(r => setTimeout(r, 300));
    const btn = document.querySelector(`.sim-preset-btn[data-preset="${presetId}"]`);
    if (btn) {
      // Clicking the preset selects it, fills the textarea AND auto-runs
      // (see the .sim-preset-btn handler). Don't also click sim-run-btn here
      // or the simulation fires twice.
      btn.click();
    } else {
      await new Promise(r => setTimeout(r, 100));
      document.getElementById('sim-run-btn')?.click();
    }
  },
  async runPresetForNode(nodeId, mode) {
    switchTab('simulation');
    await new Promise(r => setTimeout(r, 200));
    const n = NODE_BY_ID[nodeId];
    if (!n) return;
    const txt = document.getElementById('sim-custom-text');
    const nodeInp = document.getElementById('sim-custom-nodes');
    if (txt) txt.value = mode === 'collapse'
      ? `Colapso catastrófico de ${n.label}: quiebra repentina, interrupción total de producción. ¿Qué empresas sufren más?`
      : `Éxito masivo de ${n.label}: breakthrough tecnológico, cuota de mercado se triplica. ¿Quién gana y quién pierde?`;
    if (nodeInp) nodeInp.value = nodeId;
    const runBtn = document.getElementById('sim-run-btn');
    if (runBtn) runBtn.click();
  },
};

// ── Live Data Manager ──────────────────────────────────────────────────────────
(function initLiveData() {
  'use strict';

  const REFRESH_INTERVAL = 5 * 60 * 1000; // 5 min
  let _countdown = REFRESH_INTERVAL / 1000;

  // (2026-10-04) Antes pedía SOLO los primeros 100 de 569 tickers en una sola
  // llamada y pisaba MKT.quotes sin avisar a la Terminal. Ahora delega en el
  // cargador por lotes (window.loadLiveQuotes: TODO el catálogo, merge, repinta
  // Terminal/Mercado/3D, fija MKT.ts) — un solo camino para los precios.
  async function refreshLiveData() {
    if (typeof NODES === 'undefined' || !NODES.length || !window.loadLiveQuotes) return;
    try {
      const r = await window.loadLiveQuotes();
      _setLiveStatus(r && r.got ? 'live' : 'error');
    } catch(e) {
      _setLiveStatus('error');
    }
    _countdown = REFRESH_INTERVAL / 1000;
  }

  function _setLiveStatus(state) {
    const el = document.getElementById('live-status-dot');
    if (!el) return;
    if (state === 'live') {
      el.style.background   = '#00ff88';
      el.style.boxShadow    = '0 0 6px #00ff88';
    } else {
      el.style.background   = '#ff4444';
      el.style.boxShadow    = '0 0 6px #ff4444';
    }
  }

  function _startCountdown() {
    const el = document.getElementById('live-countdown');
    setInterval(() => {
      _countdown--;
      if (_countdown <= 0) refreshLiveData();
      if (el) el.textContent = _countdown > 0 ? `${_countdown}s` : '···';
    }, 1000);
  }

  function _init() {
    if (typeof NODES === 'undefined' || !NODES.length) {
      setTimeout(_init, 1000);
      return;
    }
    refreshLiveData();
    _startCountdown();
  }

  setTimeout(_init, 3000);
})();

// ── Investor Tools: FRED macro + 13F + Trade Flows + Price Targets ─────────────
async function loadFredMacro() {
  const el = document.getElementById('fred-macro-wrap');
  if (!el) return;
  el.innerHTML = '<div style="color:var(--ink-3);font-size:12px">Cargando FRED...</div>';
  try {
    const BASE = '';
    const r = await fetch(`${BASE}/api/macro/fred?series=T10Y2Y,FEDFUNDS,DGS10`);
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const data = await r.json();
    const labels = {T10Y2Y: '10Y-2Y Spread', FEDFUNDS: 'Fed Funds', DGS10: '10Y Treasury'};
    const rows = Object.entries(data).map(([sid, pts]) => {
      const last = pts.length ? pts[pts.length - 1] : null;
      const prev = pts.length > 1 ? pts[pts.length - 2] : null;
      const val  = last ? last.value.toFixed(2) : '—';
      const chg  = (last && prev) ? (last.value - prev.value) : null;
      const chgStr = chg != null ? (chg >= 0 ? `+${chg.toFixed(2)}` : chg.toFixed(2)) : '';
      const chgColor = chg == null ? 'var(--ink-3)' : chg >= 0 ? '#22c55e' : '#ef4444';
      return `<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid var(--line)">
        <span style="font-size:11px;color:var(--ink-2)">${labels[sid] || sid}</span>
        <span style="font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:600">${val}%</span>
        <span style="font-size:10px;color:${chgColor}">${chgStr}</span>
      </div>`;
    }).join('');
    el.innerHTML = rows || '<div style="color:var(--ink-3);font-size:12px">Sin datos</div>';
  } catch(e) {
    el.innerHTML = `<div style="color:var(--danger);font-size:12px">Error: ${esc(e.message)}</div>`;
  }
}
window.loadFredMacro = loadFredMacro;

async function loadInvestor13F(ticker) {
  const el = document.getElementById('investor-13f-wrap');
  if (!el || !ticker) return;
  el.innerHTML = '<div style="color:var(--ink-3);font-size:12px">Buscando en SEC EDGAR 13F...</div>';
  try {
    const BASE = '';
    const r = await fetch(`${BASE}/api/investors/13f/${encodeURIComponent(ticker)}`);
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const data = await r.json();
    const holders = data.holders || [];
    if (!holders.length) {
      el.innerHTML = '<div style="color:var(--ink-3);font-size:12px">Sin filings 13F recientes para ' + esc(ticker) + '</div>';
      return;
    }
    el.innerHTML = holders.map((h, i) => `
      <div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid var(--line)">
        <div>
          <div style="font-size:11px;font-weight:600;color:var(--ink-1)">${esc(h.name)}</div>
          <div style="font-size:10px;color:var(--ink-3)">${esc(h.form)} · ${esc(h.filed || '')}</div>
        </div>
        <span style="font-size:10px;color:var(--ink-3)">#${i + 1}</span>
      </div>`).join('');
  } catch(e) {
    el.innerHTML = `<div style="color:var(--danger);font-size:12px">Error: ${esc(e.message)}</div>`;
  }
}
window.loadInvestor13F = loadInvestor13F;

async function loadTradeFlows() {
  const el = document.getElementById('trade-flows-wrap');
  if (!el) return;
  const reporter = document.getElementById('tf-reporter')?.value || 'USA';
  const partner  = document.getElementById('tf-partner')?.value  || 'CHN';
  el.innerHTML = '<div style="color:var(--ink-3);font-size:12px">Consultando UN Comtrade...</div>';
  try {
    const BASE = '';
    const r = await fetch(`${BASE}/api/supply-chain/trade-flows?reporter=${reporter}&partner=${partner}`);
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const data = await r.json();
    const flows = data.flows || [];
    if (!flows.length) {
      el.innerHTML = '<div style="color:var(--ink-3);font-size:12px">Sin datos de flujo disponibles.</div>';
      return;
    }
    const HS_NAMES = {'8541': 'Semiconductores', '8542': 'Circuitos integrados', '8471': 'Computadoras', '8473': 'Partes PC'};
    el.innerHTML = flows.map(f => {
      const val = f.value_usd ? '$' + (f.value_usd / 1e9).toFixed(2) + 'B' : '—';
      return `<div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid var(--line)">
        <div>
          <div style="font-size:11px;font-weight:600">${esc(HS_NAMES[f.hs_code] || 'HS ' + f.hs_code)}</div>
          <div style="font-size:10px;color:var(--ink-3)">${esc(f.flow)} · ${f.year || '2023'}</div>
        </div>
        <span style="font-family:'JetBrains Mono',monospace;font-size:12px;font-weight:600;color:var(--violet)">${val}</span>
      </div>`;
    }).join('');
  } catch(e) {
    el.innerHTML = `<div style="color:var(--danger);font-size:12px">Error: ${esc(e.message)}</div>`;
  }
}
window.loadTradeFlows = loadTradeFlows;

// Hook renderDetail to update investor tools panel
(function() {
  const _origRD = window.renderDetail;
  window.renderDetail = function(id) {
    if (_origRD) _origRD.apply(this, arguments);
    const n = (typeof NODE_BY_ID !== 'undefined') ? NODE_BY_ID[id] : null;
    if (!n) return;

    // Price targets panel
    const ptWrap = document.getElementById('investor-pt-wrap');
    if (ptWrap && n.mkt) {
      const q = (typeof MKT !== 'undefined' && MKT.quotes) ? MKT.quotes[n.mkt] : null;
      const current = quotePx(q) || null;
      ptWrap.innerHTML = `
        <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:2px;padding:12px">
          <div style="font-size:9px;letter-spacing:0.1em;color:rgba(255,255,255,0.3);text-transform:uppercase;margin-bottom:8px">PRICE TARGETS · CONSENSO</div>
          <div style="display:flex;justify-content:space-between;align-items:center">
            <div>
              <div style="font-family:'JetBrains Mono',monospace;font-size:20px;font-weight:600" id="pt-consensus">—</div>
              <div style="font-size:10px;color:rgba(255,255,255,0.4)">Consenso analistas</div>
              ${current ? `<div style="font-size:10px;color:rgba(255,255,255,0.4);margin-top:2px">Precio actual: <span style="color:var(--neon)">${current.toFixed(2)}</span></div>` : ''}
            </div>
            <div style="text-align:right">
              <div style="font-family:'JetBrains Mono',monospace;font-size:13px" id="pt-high">High: —</div>
              <div style="font-family:'JetBrains Mono',monospace;font-size:13px" id="pt-low">Low: —</div>
              <div style="font-size:10px;color:rgba(255,255,255,0.4)" id="pt-analysts">— analistas</div>
            </div>
          </div>
          <div style="margin-top:8px;font-size:10px;color:var(--ink-3)">Empresa: <b>${esc(n.label)}</b> (${esc(n.mkt)})</div>
        </div>`;
      // Fetch FMP price target if available
      const BASE = '';
      fetch(`${BASE}/api/fundamentals/${n.mkt}`)
        .then(r => r.ok ? r.json() : null)
        .then(data => {
          if (!data) return;
          const pt = data.priceTarget || data.targetHigh || data.targetLow;
          if (pt || data.targetConsensus) {
            const cons = document.getElementById('pt-consensus');
            const high = document.getElementById('pt-high');
            const low  = document.getElementById('pt-low');
            const ana  = document.getElementById('pt-analysts');
            if (cons) cons.textContent = data.targetConsensus ? '$' + data.targetConsensus : '—';
            if (high) high.textContent = data.targetHigh ? 'High: $' + data.targetHigh : 'High: —';
            if (low)  low.textContent  = data.targetLow  ? 'Low: $'  + data.targetLow  : 'Low: —';
            if (ana)  ana.textContent  = data.numberOfAnalysts ? data.numberOfAnalysts + ' analistas' : '—';
          }
        })
        .catch(() => {});
    } else if (ptWrap) {
      ptWrap.innerHTML = '<div style="color:var(--ink-3);font-size:12px">Nodo sin ticker de mercado</div>';
    }

    // 13F holders
    if (n.mkt) loadInvestor13F(n.mkt);
  };
})();

// Auto-load investor tools when analysis tab is activated
(function() {
  const _origST = window.switchTab;
  if (!_origST) return;
  window.switchTab = function(tab) {
    _origST.apply(this, arguments);
    if (tab === 'analysis') {
      setTimeout(() => {
        loadFredMacro();
        loadTradeFlows();
      }, 200);
    }
  };
})();
