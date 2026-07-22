// engine/geosituation.js — SALA DE SITUACIÓN geopolítica (estilo World Monitor,
// pedido de Fabrizio 2026-07-22: "así de avanzado, incluso más").
// El "más": cada punto de estrangulamiento se puede SIMULAR sobre el grafo de
// suministro real (POST /api/matrix/impact) — WM muestra el riesgo, Bixby lo simula.
//
// Mapa 2D canvas (d3-geo, proyección Natural Earth) + capas activables:
//   empresas (HQ por sector), arcos de suministro, fabs críticas, chokepoints,
//   inestabilidad por país (choropleth). Panel derecho: nivel sistémico REAL
//   (damping·ρ(T) del motor), chokepoints rankeados con "Simular cierre",
//   inestabilidad por país y materias primas vía ETF proxy (etiquetado honesto).
// Datos: /api/geo/situation (+ /api/matrix/status + /api/quotes/live).
// Todo defensivo: sin server/DB el mapa base y las empresas siguen funcionando.
(function () {
  'use strict';

  const BASEURL = (typeof BASE !== 'undefined' && BASE) ? BASE : '';
  const en = () => {
    try { return (window.LANG || localStorage.getItem('eco_lang') || 'es') === 'en'; }
    catch (e) { return false; }
  };
  const t = (es, enTxt) => (en() ? enTxt : es);

  // ── estado del módulo ──────────────────────────────────────────────────────
  const S = {
    inited: false, topo: null, countries: null, land: null,
    situation: null, systemic: null, quotes: null,
    layers: { companies: true, arcs: false, fabs: true, choke: true, instab: true },
    transform: { k: 1, x: 0, y: 0 },
    proj: null, path: null, canvas: null, ctx: null, W: 0, H: 0,
    hover: null, raf: null, pulse: 0,
    nodePts: [], fabPts: [], chokePts: [],   // puntos proyectados para hit-test
  };

  // ── estilos (inyectados; no tocan el CSS global) ───────────────────────────
  function ensureStyles() {
    if (document.getElementById('geosit-css')) return;
    const st = document.createElement('style');
    st.id = 'geosit-css';
    st.textContent = `
#geosit-root{margin-bottom:20px}
.gs-grid{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:14px}
@media(max-width:1100px){.gs-grid{grid-template-columns:1fr}}
.gs-mapcard{position:relative;border:1px solid rgba(122,158,255,.18);border-radius:14px;overflow:hidden;background:#04060B}
#geosit-canvas{width:100%;height:560px;display:block;cursor:grab;touch-action:none}
#geosit-canvas:active{cursor:grabbing}
.gs-hd{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:10px 14px;border-bottom:1px solid rgba(122,158,255,.12)}
.gs-title{font-size:13px;font-weight:800;letter-spacing:.06em;color:#E8EDFB}
.gs-live{font-size:9px;font-weight:800;letter-spacing:.1em;color:#00E0FF;border:1px solid rgba(0,224,255,.4);border-radius:999px;padding:2px 8px;display:inline-flex;align-items:center;gap:5px}
.gs-live::before{content:"";width:6px;height:6px;border-radius:50%;background:#00E0FF;box-shadow:0 0 8px #00E0FF;animation:gsPulse 1.6s ease-in-out infinite}
@keyframes gsPulse{0%,100%{opacity:1}50%{opacity:.25}}
.gs-defcon{margin-left:auto;font-size:10.5px;font-weight:800;letter-spacing:.08em;padding:3px 10px;border-radius:8px;border:1px solid}
.gs-layers{position:absolute;left:12px;top:12px;z-index:5;background:rgba(6,11,22,.92);border:1px solid rgba(122,158,255,.22);border-radius:12px;padding:10px 12px;backdrop-filter:blur(10px);max-width:200px}
.gs-layers .lt{font-size:9.5px;font-weight:800;letter-spacing:.12em;color:#7C87A3;margin:0 0 7px}
.gs-lay{display:flex;align-items:center;gap:7px;font-size:11.5px;color:#C7D0EA;padding:3px 0;cursor:pointer;user-select:none}
.gs-lay input{accent-color:#00E0FF;cursor:pointer}
.gs-legend{position:absolute;left:12px;bottom:12px;z-index:5;display:flex;gap:10px;flex-wrap:wrap;font-size:10px;color:#9BA6C4;background:rgba(6,11,22,.85);border:1px solid rgba(122,158,255,.16);border-radius:9px;padding:5px 10px}
.gs-legend i{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:4px;vertical-align:-1px}
.gs-tip{position:absolute;z-index:6;pointer-events:none;background:rgba(6,11,22,.95);border:1px solid rgba(0,224,255,.35);border-radius:9px;padding:7px 10px;font-size:11.5px;color:#E8EDFB;max-width:240px;display:none}
.gs-rail{display:flex;flex-direction:column;gap:12px;min-width:0}
.gs-panel{border:1px solid rgba(122,158,255,.16);border-radius:13px;background:rgba(11,18,34,.5);padding:11px 13px}
.gs-ph{font-size:10px;text-transform:uppercase;letter-spacing:.12em;color:#7C87A3;font-weight:700;margin:0 0 9px;display:flex;align-items:center;gap:7px}
.gs-ph .src{margin-left:auto;font-size:9px;letter-spacing:.02em;text-transform:none;color:#5E6884;font-weight:600}
.gs-gauge{display:flex;align-items:center;gap:14px}
.gs-gnum{font-family:'JetBrains Mono',monospace;font-size:26px;font-weight:800}
.gs-glbl{font-size:11px;color:#9BA6C4;line-height:1.45}
.gs-row{padding:7px 0;border-bottom:1px solid rgba(122,158,255,.08)}
.gs-row:last-child{border-bottom:none}
.gs-rtop{display:flex;align-items:center;gap:8px;font-size:12px;color:#E8EDFB;cursor:pointer}
.gs-rtop:hover .nm{color:#00E0FF}
.gs-rtop .nm{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:650}
.gs-score{font-family:'JetBrains Mono',monospace;font-size:11.5px;width:34px;text-align:right}
.gs-bar{height:4px;border-radius:3px;background:rgba(122,158,255,.12);overflow:hidden;margin-top:5px}
.gs-bar i{display:block;height:100%}
.gs-meta{font-size:10.5px;color:#7C87A3;margin-top:4px;display:flex;gap:8px;flex-wrap:wrap}
.gs-meta .fx{color:#FFD27A}
.gs-simbtn{font-size:10.5px;font-weight:700;padding:3px 10px;border-radius:999px;cursor:pointer;color:#00E0FF;background:rgba(0,224,255,.1);border:1px solid rgba(0,224,255,.45);font-family:inherit}
.gs-simbtn:hover{background:rgba(0,224,255,.2)}
.gs-simres{margin-top:7px;border:1px solid rgba(255,77,106,.3);border-radius:9px;padding:8px 10px;background:rgba(255,77,106,.06)}
.gs-simres .sh{font-size:10.5px;color:#FF8FA3;font-weight:700;margin-bottom:5px}
.gs-vrow{display:flex;align-items:center;gap:7px;font-size:11px;color:#C7D0EA;padding:2px 0}
.gs-vrow .vb{flex:1;height:4px;border-radius:3px;background:rgba(122,158,255,.1);overflow:hidden}
.gs-vrow .vb i{display:block;height:100%;background:linear-gradient(90deg,#FF4D6A,#FFB300)}
.gs-vrow .vp{font-family:'JetBrains Mono',monospace;font-size:10.5px;width:38px;text-align:right;color:#FF8FA3}
.gs-com{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px}
.gs-cbox{border:1px solid rgba(122,158,255,.12);border-radius:9px;padding:7px 9px;background:rgba(4,6,11,.4)}
.gs-cbox .ck{font-size:9px;letter-spacing:.08em;color:#7C87A3;font-weight:700}
.gs-cbox .cv{font-family:'JetBrains Mono',monospace;font-size:13px;color:#E8EDFB;margin-top:2px}
.gs-cbox .cd{font-family:'JetBrains Mono',monospace;font-size:10px;margin-top:1px}
.gs-load{color:#7C87A3;font-size:12.5px;font-style:italic;text-align:center;padding:34px}
.gs-load::before{content:"";display:block;width:24px;height:24px;margin:0 auto 10px;border-radius:50%;border:2.5px solid rgba(122,158,255,.18);border-top-color:#00E0FF;animation:gsSpin .7s linear infinite}
@keyframes gsSpin{to{transform:rotate(360deg)}}
.gs-note{font-size:9.5px;color:#5E6884;margin-top:8px;line-height:1.4}`;
    document.head.appendChild(st);
  }

  // ── topojson mínimo (feature de world-atlas) — sin dependencias nuevas ─────
  function topoFeature(topo, obj) {
    const tr = topo.transform;
    const sx = tr ? tr.scale[0] : 1, sy = tr ? tr.scale[1] : 1;
    const tx = tr ? tr.translate[0] : 0, ty = tr ? tr.translate[1] : 0;
    const arcs = topo.arcs.map(arc => {
      let x = 0, y = 0;
      return arc.map(p => {
        x += p[0]; y += p[1];
        return [x * sx + tx, y * sy + ty];
      });
    });
    function ring(idxs) {
      let out = [];
      idxs.forEach(i => {
        let a = i >= 0 ? arcs[i].slice() : arcs[~i].slice().reverse();
        if (out.length) a = a.slice(1);
        out = out.concat(a);
      });
      return out;
    }
    function geom(g) {
      if (g.type === 'Polygon') return { type: 'Polygon', coordinates: g.arcs.map(ring) };
      if (g.type === 'MultiPolygon') return { type: 'MultiPolygon', coordinates: g.arcs.map(p => p.map(ring)) };
      return null;
    }
    return {
      type: 'FeatureCollection',
      features: (obj.geometries || []).map(g => ({
        type: 'Feature', properties: g.properties || {}, geometry: geom(g),
      })).filter(f => f.geometry),
    };
  }

  // ── colores ────────────────────────────────────────────────────────────────
  function scoreColor(s) {
    return s >= 75 ? '#FF4D6A' : s >= 55 ? '#FFB300' : s >= 35 ? '#EAD24B' : '#2BE38B';
  }
  function sectorColorOf(node) {
    try { if (typeof window.sectorColorFor === 'function') return window.sectorColorFor(node.cat); } catch (e) {}
    try { if (typeof window.sectorColor === 'function') return window.sectorColor(node.cat); } catch (e) {}
    return '#7A9EFF';
  }

  // ── carga de datos ─────────────────────────────────────────────────────────
  async function loadAll() {
    const jobs = [
      fetch(BASEURL + '/vendor/world-110m.json').then(r => r.json())
        .then(tp => { S.topo = tp; S.countries = topoFeature(tp, tp.objects.countries); S.land = topoFeature(tp, tp.objects.land); })
        .catch(() => {}),
      fetch(BASEURL + '/api/geo/situation').then(r => r.json())
        .then(d => { if (d && d.chokepoints) S.situation = d; }).catch(() => {}),
      fetch(BASEURL + '/api/matrix/status').then(r => r.json())
        .then(d => { if (d && d.available) S.systemic = d; }).catch(() => {}),
      fetch(BASEURL + '/api/quotes/live', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tickers: ['URA', 'LIT', 'COPX', 'REMX', 'SMH', 'GLD'] }),
      }).then(r => r.json()).then(d => { S.quotes = d && d.quotes ? d.quotes : d; }).catch(() => {}),
    ];
    await Promise.allSettled(jobs);
  }

  // ── proyección y dibujo ────────────────────────────────────────────────────
  function setupProjection() {
    const d3 = window.d3;
    S.proj = d3.geoNaturalEarth1();
    if (S.land) S.proj.fitExtent([[8, 8], [S.W - 8, S.H - 8]], S.land);
    else { S.proj.scale(S.W / 6.2).translate([S.W / 2, S.H / 2]); }
    S.path = d3.geoPath(S.proj, S.ctx);
  }

  function project(lat, lon) {
    const p = S.proj([lon, lat]);
    if (!p) return null;
    const { k, x, y } = S.transform;
    return [p[0] * k + x, p[1] * k + y];
  }

  function instabilityByTopoName() {
    const out = {};
    if (!S.situation) return out;
    const map = S.situation.topo_name_map || {};
    const byId = {};
    (S.situation.instability || []).forEach(c => { byId[c.id] = c; });
    Object.entries(map).forEach(([topoName, id]) => { if (byId[id]) out[topoName] = byId[id]; });
    return out;
  }

  function draw() {
    const ctx = S.ctx; if (!ctx) return;
    const { k, x, y } = S.transform;
    const dpr = window.devicePixelRatio || 1;
    ctx.save();
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, S.W, S.H);
    ctx.fillStyle = '#04060B';
    ctx.fillRect(0, 0, S.W, S.H);
    ctx.translate(x, y); ctx.scale(k, k);

    // países (choropleth de inestabilidad si la capa está activa)
    const instab = S.layers.instab ? instabilityByTopoName() : {};
    if (S.countries) {
      S.countries.features.forEach(f => {
        const name = f.properties && f.properties.name;
        const c = instab[name];
        ctx.beginPath(); S.path(f);
        if (c) {
          const s = c.score;
          const al = Math.min(0.5, 0.10 + s / 220);
          ctx.fillStyle = s >= 70 ? `rgba(255,77,106,${al})` : s >= 45 ? `rgba(255,179,0,${al})` : `rgba(122,158,255,${al * 0.6})`;
        } else {
          ctx.fillStyle = 'rgba(24,34,56,.85)';
        }
        ctx.fill();
        ctx.strokeStyle = 'rgba(122,158,255,.14)';
        ctx.lineWidth = 0.5 / k;
        ctx.stroke();
      });
    }

    S.nodePts = []; S.fabPts = []; S.chokePts = [];

    // arcos de suministro (top links por peso)
    if (S.layers.arcs && window.LINKS && window.NODE_BY_ID && window.GeoCoords) {
      const lid = v => (typeof v === 'object' && v !== null) ? v.id : v;
      const links = window.LINKS.slice().sort((a, b) => (b.w || 0) - (a.w || 0)).slice(0, 140);
      ctx.lineWidth = 0.7 / k;
      links.forEach(l => {
        const a = window.NODE_BY_ID[lid(l.source)], b = window.NODE_BY_ID[lid(l.target)];
        if (!a || !b) return;
        const ca = window.GeoCoords.geoCoord(a), cb = window.GeoCoords.geoCoord(b);
        const p1 = S.proj([ca.lng, ca.lat]), p2 = S.proj([cb.lng, cb.lat]);
        if (!p1 || !p2) return;
        const mx = (p1[0] + p2[0]) / 2, my = (p1[1] + p2[1]) / 2 - Math.min(60, Math.hypot(p2[0] - p1[0], p2[1] - p1[1]) * 0.22);
        ctx.beginPath();
        ctx.moveTo(p1[0], p1[1]);
        ctx.quadraticCurveTo(mx, my, p2[0], p2[1]);
        ctx.strokeStyle = 'rgba(0,224,255,.14)';
        ctx.stroke();
      });
    }

    // empresas (HQ por sector)
    if (S.layers.companies && window.NODES && window.GeoCoords) {
      window.NODES.forEach(n => {
        const c = window.GeoCoords.geoCoord(n);
        const p = S.proj([c.lng, c.lat]);
        if (!p) return;
        const r = 1.5 / Math.sqrt(k);
        ctx.beginPath();
        ctx.arc(p[0], p[1], r, 0, Math.PI * 2);
        ctx.fillStyle = sectorColorOf(n);
        ctx.globalAlpha = 0.85;
        ctx.fill();
        ctx.globalAlpha = 1;
        S.nodePts.push([p[0] * k + x, p[1] * k + y, n]);
      });
    }

    // fabs críticas (rombos)
    if (S.layers.fabs && S.situation) {
      (S.situation.fabs || []).forEach(f => {
        const p = S.proj([f.lon, f.lat]); if (!p) return;
        const r = 3.4 / Math.sqrt(k);
        ctx.save();
        ctx.translate(p[0], p[1]); ctx.rotate(Math.PI / 4);
        ctx.fillStyle = f.kind === 'euv' ? '#8e5aff' : f.kind === 'hbm' ? '#FFB300' : '#00E0FF';
        ctx.fillRect(-r / 2, -r / 2, r, r);
        ctx.restore();
        S.fabPts.push([p[0] * k + x, p[1] * k + y, f]);
      });
    }

    // chokepoints (anillos pulsantes por score)
    if (S.layers.choke && S.situation) {
      (S.situation.chokepoints || []).forEach(c => {
        const p = S.proj([c.lon, c.lat]); if (!p) return;
        const col = scoreColor(c.score);
        const base = 4.2 / Math.sqrt(k);
        ctx.beginPath();
        ctx.arc(p[0], p[1], base, 0, Math.PI * 2);
        ctx.fillStyle = col; ctx.globalAlpha = 0.9; ctx.fill(); ctx.globalAlpha = 1;
        const pr = base * (1.5 + 0.9 * Math.abs(Math.sin(S.pulse + c.lat)));
        ctx.beginPath();
        ctx.arc(p[0], p[1], pr, 0, Math.PI * 2);
        ctx.strokeStyle = col; ctx.globalAlpha = 0.5; ctx.lineWidth = 1.1 / k; ctx.stroke(); ctx.globalAlpha = 1;
        S.chokePts.push([p[0] * k + x, p[1] * k + y, c]);
      });
    }

    ctx.restore();
  }

  function animate() {
    S.pulse += 0.05;
    draw();
    S.raf = requestAnimationFrame(animate);
  }
  function stopAnim() { if (S.raf) cancelAnimationFrame(S.raf); S.raf = null; }

  // ── interacción (zoom/pan d3 + hover/click) ────────────────────────────────
  function wireInteraction() {
    const d3 = window.d3;
    const sel = d3.select(S.canvas);
    sel.call(d3.zoom()
      .scaleExtent([1, 14])
      .on('zoom', (ev) => { S.transform = ev.transform; }));

    const tip = document.getElementById('geosit-tip');
    S.canvas.addEventListener('mousemove', (ev) => {
      const r = S.canvas.getBoundingClientRect();
      const mx = ev.clientX - r.left, my = ev.clientY - r.top;
      const hit = hitTest(mx, my);
      S.hover = hit;
      if (hit && tip) {
        tip.style.display = 'block';
        tip.style.left = Math.min(mx + 14, r.width - 220) + 'px';
        tip.style.top = (my + 12) + 'px';
        tip.innerHTML = hit.html;
        S.canvas.style.cursor = 'pointer';
      } else if (tip) {
        tip.style.display = 'none';
        S.canvas.style.cursor = 'grab';
      }
    });
    S.canvas.addEventListener('mouseleave', () => { if (tip) tip.style.display = 'none'; });
    S.canvas.addEventListener('click', () => {
      const h = S.hover;
      if (!h) return;
      if (h.kind === 'node' && window._openSecondBrain) window._openSecondBrain(h.obj.id);
      if (h.kind === 'fab' && h.obj.company_known && window._openSecondBrain) window._openSecondBrain(h.obj.company);
      if (h.kind === 'choke') {
        const el = document.getElementById('gs-ck-' + h.obj.id);
        if (el) { el.scrollIntoView({ behavior: 'smooth', block: 'center' }); el.style.outline = '1px solid rgba(0,224,255,.6)'; setTimeout(() => { el.style.outline = ''; }, 1600); }
      }
    });
  }

  function hitTest(mx, my) {
    const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    for (const [px, py, c] of S.chokePts) {
      if (Math.hypot(px - mx, py - my) < 11) {
        return { kind: 'choke', obj: c, html: `<b>⚓ ${esc(en() ? c.en : c.es)}</b><br>${t('riesgo', 'risk')}: <b style="color:${scoreColor(c.score)}">${c.score}</b>/100${c.news ? `<br>📰 ${c.news.count} ${t('artículos 7d', 'articles 7d')}` : ''}${c.factors && c.factors.length ? `<br>⚡ ${esc(c.factors[0])}` : ''}` };
      }
    }
    for (const [px, py, f] of S.fabPts) {
      if (Math.hypot(px - mx, py - my) < 9) {
        return { kind: 'fab', obj: f, html: `<b>🏭 ${esc(f.site)}</b><br>${esc(f.c)} · ${esc(f.kind.toUpperCase())}` };
      }
    }
    let best = null, bd = 8;
    for (const [px, py, n] of S.nodePts) {
      const d = Math.hypot(px - mx, py - my);
      if (d < bd) { bd = d; best = n; }
    }
    if (best) return { kind: 'node', obj: best, html: `<b>${esc(best.label)}</b><br>${esc(best.loc || best.country || '')}` };
    return null;
  }

  // ── panel derecho ──────────────────────────────────────────────────────────
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); }

  function systemicHTML() {
    const sy = S.systemic;
    if (!sy || sy.spectral_radius == null) return '';
    const dr = sy.damping_rho != null ? sy.damping_rho : (0.6 * sy.spectral_radius);
    const lvl = dr >= 1 ? [t('SUPERCRÍTICO', 'SUPERCRITICAL'), '#FF4D6A']
      : dr >= 0.9 ? [t('CRÍTICO', 'CRITICAL'), '#FF7A45']
        : dr >= 0.75 ? [t('TENSO', 'STRAINED'), '#FFB300'] : [t('ESTABLE', 'STABLE'), '#2BE38B'];
    const nf = (sy.active_factors || []).length;
    return `<div class="gs-panel"><div class="gs-ph">🧮 ${t('Nivel sistémico', 'Systemic level')}<span class="src">ρ(T) · ${t('motor real', 'live engine')}</span></div>
      <div class="gs-gauge"><div class="gs-gnum" style="color:${lvl[1]}">${dr.toFixed(2)}</div>
      <div class="gs-glbl"><b style="color:${lvl[1]}">${lvl[0]}</b> — ${t('qué tan cerca está la red de que un shock se auto-sostenga (≥1 = se auto-sostiene)', 'how close the network is to a self-sustaining shock (≥1 = self-sustaining)')}${nf ? `<br>⚡ ${nf} ${t('factor(es) sistémico(s) activo(s)', 'active systemic factor(s)')}` : ''}</div></div></div>`;
  }

  function chokeHTML() {
    const d = S.situation;
    if (!d) return '';
    const rows = (d.chokepoints || []).map(c => {
      const col = scoreColor(c.score);
      const news = c.news ? `<span>📰 ${c.news.count} ${t('art. 7d', 'art. 7d')}${c.news.tone < -3 ? ` · ${t('tono', 'tone')} ${c.news.tone}` : ''}</span>` : `<span>${t('noticias: cargando…', 'news: warming…')}</span>`;
      const fx = (c.factors && c.factors.length) ? `<span class="fx">⚡ ${esc(c.factors[0])}</span>` : '';
      const sim = (c.affected && c.affected.length)
        ? `<button class="gs-simbtn" data-ck="${esc(c.id)}">◉ ${t('Simular cierre', 'Simulate closure')}</button>` : '';
      return `<div class="gs-row" id="gs-ck-${esc(c.id)}">
        <div class="gs-rtop" data-focus="${c.lat},${c.lon}"><span>⚓</span><span class="nm">${esc(en() ? c.en : c.es)}</span><span class="gs-score" style="color:${col}">${Math.round(c.score)}</span></div>
        <div class="gs-bar"><i style="width:${Math.min(100, c.score)}%;background:${col}"></i></div>
        <div class="gs-meta">${news}${fx}${sim}</div>
        <div class="gs-meta" style="color:#8B96B5">${esc(en() ? c.why_en : c.why_es)}</div>
        <div class="gs-simout" id="gs-simout-${esc(c.id)}"></div></div>`;
    }).join('');
    const src = d.news_sources ? `GDELT ${d.news_sources.warm}/${d.news_sources.total}` : '';
    return `<div class="gs-panel"><div class="gs-ph">⚓ ${t('Puntos de estrangulamiento', 'Chokepoints')}<span class="src">${src}</span></div>${rows}
      <div class="gs-note">${esc(d.method_es || '')}</div></div>`;
  }

  function instabHTML() {
    const d = S.situation;
    if (!d) return '';
    const rows = (d.instability || []).slice(0, 9).map(c => {
      const col = scoreColor(c.score);
      const delta = c.news && c.news.count ? `📰 ${c.news.count}` : '';
      return `<div class="gs-row"><div class="gs-rtop"><span class="nm">${esc(en() ? c.en : c.es)}</span><span style="font-size:10px;color:#7C87A3">${delta}</span><span class="gs-score" style="color:${col}">${Math.round(c.score)}</span></div>
        <div class="gs-bar"><i style="width:${Math.min(100, c.score)}%;background:${col}"></i></div></div>`;
    }).join('');
    return `<div class="gs-panel"><div class="gs-ph">🌡 ${t('Inestabilidad por país', 'Country instability')}<span class="src">${t('estructural + noticias', 'structural + news')}</span></div>${rows}</div>`;
  }

  function commoditiesHTML() {
    const q = S.quotes;
    if (!q) return '';
    const DEF = [['URA', t('Uranio', 'Uranium')], ['LIT', t('Litio', 'Lithium')], ['COPX', t('Cobre', 'Copper')],
      ['REMX', t('T. raras', 'Rare earths')], ['SMH', t('Semis', 'Semis')], ['GLD', t('Oro', 'Gold')]];
    const boxes = DEF.map(([tk, lbl]) => {
      const d = q[tk];
      if (!d || d.live == null && d.close == null) return '';
      const px = d.live != null ? d.live : d.close;
      const pct = d.pct != null ? d.pct : (d.prev ? ((px - d.prev) / d.prev * 100) : null);
      const col = pct == null ? '#9BA6C4' : pct >= 0 ? '#2BE38B' : '#FF4D6A';
      return `<div class="gs-cbox"><div class="ck">${esc(lbl)}</div><div class="cv">$${Number(px).toFixed(2)}</div>
        <div class="cd" style="color:${col}">${pct == null ? '—' : (pct >= 0 ? '+' : '') + pct.toFixed(1) + '%'}</div></div>`;
    }).join('');
    if (!boxes) return '';
    return `<div class="gs-panel"><div class="gs-ph">⛏ ${t('Materias primas', 'Commodities')}<span class="src">${t('vía ETF proxy', 'via ETF proxy')}</span></div>
      <div class="gs-com">${boxes}</div></div>`;
  }

  function renderRail() {
    const rail = document.getElementById('geosit-rail');
    if (!rail) return;
    rail.innerHTML = systemicHTML() + chokeHTML() + instabHTML() + commoditiesHTML();
    rail.querySelectorAll('.gs-simbtn').forEach(b => {
      b.addEventListener('click', () => runSim(b.getAttribute('data-ck')));
    });
    rail.querySelectorAll('[data-focus]').forEach(el => {
      el.addEventListener('click', () => {
        const [lat, lon] = el.getAttribute('data-focus').split(',').map(Number);
        focusOn(lat, lon);
      });
    });
  }

  function focusOn(lat, lon) {
    const p = S.proj([lon, lat]);
    if (!p) return;
    const k = 4;
    const d3 = window.d3;
    const tr = d3.zoomIdentity.translate(S.W / 2 - p[0] * k, S.H / 2 - p[1] * k).scale(k);
    d3.select(S.canvas).transition().duration(650).call(d3.zoom().scaleExtent([1, 14]).on('zoom', (ev) => { S.transform = ev.transform; }).transform, tr);
    S.transform = { k, x: S.W / 2 - p[0] * k, y: S.H / 2 - p[1] * k };
  }

  // ── el "más" que World Monitor no tiene: simular el cierre sobre el grafo ──
  async function runSim(ckId) {
    const d = S.situation; if (!d) return;
    const c = (d.chokepoints || []).find(x => x.id === ckId);
    const out = document.getElementById('gs-simout-' + ckId);
    if (!c || !out || !c.affected || !c.affected.length) return;
    out.innerHTML = `<div class="gs-load" style="padding:14px">${t('Propagando el shock por la cadena…', 'Propagating the shock through the chain…')}</div>`;
    try {
      const r = await fetch(BASEURL + '/api/matrix/impact', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ shock: c.affected, magnitude: 1.0 }),
      });
      const res = await r.json();
      if (!r.ok || !res.impacts) throw new Error(res.error || 'sin motor');
      const shocked = new Set(c.affected);
      const victims = Object.entries(res.impacts)
        .filter(([id]) => !shocked.has(id))
        .sort((a, b) => b[1] - a[1]).slice(0, 7);
      const nm = id => (window.NODE_BY_ID && window.NODE_BY_ID[id] && window.NODE_BY_ID[id].label) || id;
      out.innerHTML = `<div class="gs-simres"><div class="sh">◉ ${t('Cierre simulado', 'Simulated closure')}: ${esc(en() ? c.en : c.es)} — ${res.affected} ${t('empresas alcanzadas', 'companies reached')}</div>` +
        victims.map(([id, v]) => `<div class="gs-vrow"><span style="flex:0 0 118px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(nm(id))}</span><span class="vb"><i style="width:${Math.min(100, v)}%"></i></span><span class="vp">${Math.round(v)}%</span></div>`).join('') +
        `<div class="gs-note">${t('Motor de matrices sobre el grafo real (mismo kernel que la pestaña Simulación). Análisis, no asesoría.', 'Matrix engine over the real graph (same kernel as the Simulation tab). Analysis, not advice.')}</div></div>`;
    } catch (e) {
      out.innerHTML = `<div class="gs-note" style="color:#FF8FA3">${t('No se pudo simular (¿ontología no configurada?).', 'Could not simulate (ontology not configured?).')}</div>`;
    }
  }

  // ── montaje ────────────────────────────────────────────────────────────────
  function markup() {
    return `<div class="gs-grid">
      <div class="gs-mapcard">
        <div class="gs-hd"><span class="gs-title">🌐 ${t('SALA DE SITUACIÓN', 'SITUATION ROOM')}</span><span class="gs-live">${t('EN VIVO', 'LIVE')}</span><span id="geosit-defcon" class="gs-defcon" style="display:none"></span></div>
        <div style="position:relative">
          <canvas id="geosit-canvas"></canvas>
          <div class="gs-layers"><div class="lt">${t('CAPAS', 'LAYERS')}</div>
            <label class="gs-lay"><input type="checkbox" data-layer="companies" checked> 🏢 ${t('Empresas', 'Companies')}</label>
            <label class="gs-lay"><input type="checkbox" data-layer="arcs"> 🔗 ${t('Arcos de suministro', 'Supply arcs')}</label>
            <label class="gs-lay"><input type="checkbox" data-layer="fabs" checked> 🏭 ${t('Fabs críticas', 'Critical fabs')}</label>
            <label class="gs-lay"><input type="checkbox" data-layer="choke" checked> ⚓ ${t('Estrangulamientos', 'Chokepoints')}</label>
            <label class="gs-lay"><input type="checkbox" data-layer="instab" checked> 🌡 ${t('Inestabilidad', 'Instability')}</label>
          </div>
          <div class="gs-legend"><span><i style="background:#2BE38B"></i>&lt;35</span><span><i style="background:#EAD24B"></i>35-54</span><span><i style="background:#FFB300"></i>55-74</span><span><i style="background:#FF4D6A"></i>75+</span><span style="opacity:.7">🏭 ${t('rombo=fab', 'diamond=fab')} · ◆${t('morado=EUV', 'purple=EUV')}</span></div>
          <div id="geosit-tip" class="gs-tip"></div>
        </div>
      </div>
      <div id="geosit-rail" class="gs-rail"><div class="gs-panel"><div class="gs-load">${t('Cargando situación global…', 'Loading global situation…')}</div></div></div>
    </div>`;
  }

  function sizeCanvas() {
    const c = S.canvas;
    const dpr = window.devicePixelRatio || 1;
    S.W = c.clientWidth || 900;
    S.H = c.clientHeight || 560;
    c.width = S.W * dpr;
    c.height = S.H * dpr;
  }

  async function init() {
    const root = document.getElementById('geosit-root');
    if (!root || !window.d3) return;
    ensureStyles();
    if (!S.inited) {
      S.inited = true;
      root.innerHTML = markup();
      S.canvas = document.getElementById('geosit-canvas');
      S.ctx = S.canvas.getContext('2d');
      sizeCanvas();
      root.querySelectorAll('[data-layer]').forEach(cb => {
        cb.addEventListener('change', () => { S.layers[cb.getAttribute('data-layer')] = cb.checked; });
      });
      await loadAll();
      setupProjection();
      wireInteraction();
      renderRail();
      window.addEventListener('resize', () => {
        if (!S.canvas || !S.canvas.clientWidth) return;
        sizeCanvas(); setupProjection();
      });
      // refresco periódico suave (noticias se calientan solas server-side)
      setInterval(async () => {
        if (document.hidden) return;
        try {
          const r = await fetch(BASEURL + '/api/geo/situation');
          const d = await r.json();
          if (d && d.chokepoints) { S.situation = d; renderRail(); }
        } catch (e) {}
      }, 120000);
    } else {
      sizeCanvas(); setupProjection();
    }
    stopAnim(); animate();
  }

  // init perezoso: se engancha a renderGeoPanel (que switchTab('geo') y la
  // Cabina ya llaman) — sin tocar los bloques inline de app.html.
  document.addEventListener('DOMContentLoaded', () => {
    const orig = window.renderGeoPanel;
    if (typeof orig === 'function') {
      window.renderGeoPanel = function () {
        try { orig.apply(this, arguments); } catch (e) {}
        try { init(); } catch (e) { console.warn('[GeoSit]', e); }
      };
    }
  });

  window.GeoSituation = { init, state: S };
})();
