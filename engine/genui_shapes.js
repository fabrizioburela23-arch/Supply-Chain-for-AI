/* ============================================================================
   engine/genui_shapes.js — FORMAS, IMÁGENES y MINI-MAPA de las respuestas visuales
   (kblocks/1, docs/CHAT_UI_GENERATIVA.md §4.6 y §7.2).

   · image.shape: 17 formas de un vocabulario CERRADO (chip, oblea, fábrica, centro de datos, GPU, memoria,
     batería, mina, barco, estrecho, satélite, cohete, energía, cable, banco, globo, flecha) dibujadas como SVG
     en código con los colores de Khipus OS (--os-*). Sin datos: son pictogramas. Un diagrama `steps` es una
     fila de formas con rótulo («oblea → TSMC → Nvidia → nube»).
   · image.asset: SOLO archivos del mismo origen que pasan la expresión regular del esquema
     (/static/genui/<nombre>.svg|png|webp o /api/genui/img/<sha>). Nunca una URL elegida por la IA (§9).
   · geo.mini: mapa SVG estático (equirectangular) con puntos y arcos; el contorno de tierra sale del TopoJSON
     del mismo origen /vendor/world-110m.json (una vez por sesión, ruta memorizada por región); sin él, una
     retícula de coordenadas. Clic en un punto → World Monitor enfocado ahí.
   Se registra en window.KhipuGenUI (engine/genui.js, que se carga ANTES).
   ============================================================================ */
(function (root) {
  'use strict';
  var W = root, G = W.KhipuGenUI;
  if (!G || !G._u) return;
  var U = G._u, h = U.h, sv = U.sv, tip = U.tip, T = U.T, lang = U.lang, when = U.when;

  var CSS = '' +
    '.kg-sh{display:block;flex-shrink:0;--kg-tone:var(--kg-a)}' +
    '.kg-sh .s{fill:none;stroke:var(--kg-tone);stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}' +
    '.kg-sh .f{fill:var(--kg-tone)}.kg-sh .f2{fill:color-mix(in srgb,var(--kg-tone) 20%,transparent)}' +
    '.kg-tone-neutral{--kg-tone:var(--os-ink-2)}.kg-tone-positive{--kg-tone:var(--os-good)}' +
    '.kg-tone-negative{--kg-tone:var(--os-neg)}.kg-tone-warning{--kg-tone:var(--os-warn)}' +
    '.kg-steps{display:flex;align-items:flex-start;justify-content:center;gap:4px;flex-wrap:wrap;padding:4px 0}' +
    '.kg-step{display:flex;flex-direction:column;align-items:center;gap:6px;min-width:64px;max-width:110px;text-align:center}' +
    '.kg-step .lb{font-size:12px;font-weight:700;line-height:1.25;overflow-wrap:normal}.kg-step.ent{cursor:pointer}.kg-step.ent:hover .lb{color:var(--kg-a)}' +
    '.kg-step .bg{width:58px;height:58px;border-radius:16px;background:var(--os-surface-2);display:flex;align-items:center;justify-content:center}' +
    '.kg-arrow{align-self:center;margin-top:-18px;color:var(--os-ink-2)}' +
    '.kg-step,.kg-arrow{opacity:0;transform:translateY(5px);transition:opacity var(--kg-d2) var(--kg-e),transform var(--kg-d2) var(--kg-e)}' +
    '.kg-go .kg-step,.kg-go .kg-arrow{opacity:1;transform:none}' +
    '.kg-one{display:flex;align-items:center;gap:14px}.kg-one .bg{width:76px;height:76px;border-radius:20px;background:var(--os-surface-2);display:flex;align-items:center;justify-content:center;flex-shrink:0}' +
    '.kg-cap{font-size:12.5px;color:var(--os-ink-2);margin-top:8px;text-align:center}.kg-one .kg-cap{text-align:left;margin:0}' +
    '.kg-img{display:block;max-width:100%;height:auto;border-radius:12px;margin:0 auto}.kg-cred{font-size:11px;color:var(--os-ink-2);text-align:center;margin-top:4px}' +
    '.kg-geo{width:100%;display:block;border-radius:12px;background:color-mix(in srgb,var(--kg-a) 6%,var(--os-surface-2))}' +
    '.kg-geo .land{fill:var(--os-surface-3);stroke:var(--os-surface);stroke-width:.6}' +
    '.kg-geo .grat{fill:none;stroke:var(--os-line);stroke-width:1}' +
    '.kg-geo .pt{stroke:var(--os-surface);stroke-width:1.5;cursor:pointer;transform-box:fill-box;transform-origin:center;opacity:0;transform:scale(.4);transition:opacity var(--kg-d2) var(--kg-e),transform var(--kg-d3) cubic-bezier(.3,1.4,.5,1)}' +
    '.kg-go .kg-geo .pt{opacity:1;transform:none}.kg-geo .pt:hover{stroke:var(--os-ink)}' +
    '.kg-geo .lbl{fill:var(--os-ink);font-size:11px;font-weight:700;paint-order:stroke;stroke:var(--os-surface);stroke-width:3px}' +
    '.kg-geo .arc{fill:none;stroke:var(--kg-a);stroke-linecap:round;opacity:.7}' +
    '.kg-geof{display:flex;align-items:center;gap:8px;margin-top:8px;flex-wrap:wrap;font-size:11.5px;color:var(--os-ink-2)}';
  (function () {
    var d = W.document; if (!d || !d.head || d.getElementById('kg-styles-shapes')) return;
    var st = d.createElement('style'); st.id = 'kg-styles-shapes'; st.textContent = CSS; d.head.appendChild(st);
  })();

  /* ── el vocabulario cerrado: primitivas [etiqueta, atributos, clase] en una cuadrícula de 48×48 ── */
  var P = function (d, cls) { return ['path', { d: d }, cls || 's']; };
  var SHAPES = {
    chip: [['rect', { x: 12, y: 12, width: 24, height: 24, rx: 4 }, 'f2'], ['rect', { x: 12, y: 12, width: 24, height: 24, rx: 4 }, 's'],
      ['rect', { x: 19, y: 19, width: 10, height: 10, rx: 2 }, 'f'], P('M18 12V6M24 12V6M30 12V6M18 42v-6M24 42v-6M30 42v-6M12 18H6M12 24H6M12 30H6M42 18h-6M42 24h-6M42 30h-6')],
    wafer: [['circle', { cx: 24, cy: 24, r: 17 }, 'f2'], ['circle', { cx: 24, cy: 24, r: 17 }, 's'], P('M13 18h22M10 24h28M13 30h22M18 12v24M24 8v32M30 12v24'), P('M21 41h6', 's')],
    fab: [P('M6 41V23l9 6v-6l9 6v-6l9 6V11h7v30z', 'f2'), P('M6 41V23l9 6v-6l9 6v-6l9 6V11h7v30z'), ['rect', { x: 11, y: 33, width: 5, height: 4 }, 'f'], ['rect', { x: 21, y: 33, width: 5, height: 4 }, 'f']],
    datacenter: [['rect', { x: 9, y: 8, width: 30, height: 9, rx: 2 }, 's'], ['rect', { x: 9, y: 20, width: 30, height: 9, rx: 2 }, 's'], ['rect', { x: 9, y: 32, width: 30, height: 9, rx: 2 }, 's'],
      ['circle', { cx: 15, cy: 12.5, r: 1.8 }, 'f'], ['circle', { cx: 15, cy: 24.5, r: 1.8 }, 'f'], ['circle', { cx: 15, cy: 36.5, r: 1.8 }, 'f'], P('M22 12.5h12M22 24.5h12M22 36.5h12')],
    gpu: [['rect', { x: 5, y: 13, width: 38, height: 21, rx: 3 }, 'f2'], ['rect', { x: 5, y: 13, width: 38, height: 21, rx: 3 }, 's'],
      ['circle', { cx: 17, cy: 23.5, r: 6 }, 's'], ['circle', { cx: 31, cy: 23.5, r: 6 }, 's'], ['circle', { cx: 17, cy: 23.5, r: 1.6 }, 'f'], ['circle', { cx: 31, cy: 23.5, r: 1.6 }, 'f'], P('M11 34v5M16 34v5M21 34v5M26 34v5')],
    memory: [['rect', { x: 5, y: 15, width: 38, height: 16, rx: 2 }, 'f2'], ['rect', { x: 5, y: 15, width: 38, height: 16, rx: 2 }, 's'],
      ['rect', { x: 9, y: 19, width: 7, height: 8, rx: 1 }, 'f'], ['rect', { x: 20.5, y: 19, width: 7, height: 8, rx: 1 }, 'f'], ['rect', { x: 32, y: 19, width: 7, height: 8, rx: 1 }, 'f'], P('M9 31v5M14 31v5M19 31v5M24 31v5M29 31v5M34 31v5M39 31v5')],
    battery: [['rect', { x: 7, y: 14, width: 31, height: 20, rx: 4 }, 's'], ['rect', { x: 38, y: 20, width: 4, height: 8, rx: 1 }, 'f'], ['rect', { x: 11, y: 18, width: 17, height: 12, rx: 2 }, 'f'], P('M33 21v6')],
    mine: [P('M9 19Q24 6 39 19'), P('M24 13v25'), P('M6 41h36'), P('M14 41l5-7 5 4 5-6 5 9', 'f2')],
    ship: [P('M5 30h38l-6 9H11z', 'f2'), P('M5 30h38l-6 9H11z'), ['rect', { x: 12, y: 21, width: 8, height: 9 }, 'f'], ['rect', { x: 21, y: 21, width: 8, height: 9 }, 'f2'], ['rect', { x: 21, y: 21, width: 8, height: 9 }, 's'], ['rect', { x: 30, y: 14, width: 6, height: 16, rx: 1 }, 's'], P('M4 44q4-3 8 0t8 0 8 0 8 0 8 0')],
    strait: [P('M4 6h13q-3 9 0 18t-2 18H4z', 'f2'), P('M44 6H31q3 9 0 18t2 18h11z', 'f2'), P('M17 6q-3 9 0 18t-2 18M31 6q3 9 0 18t2 18'), P('M21 16q3-2 6 0M21 26q3-2 6 0M21 36q3-2 6 0')],
    satellite: [['rect', { x: 19, y: 19, width: 10, height: 10, rx: 2, transform: 'rotate(45 24 24)' }, 'f'], P('M6 14l8 8M14 6l8 8M6 14l8-8', 's'), P('M34 26l8 8M26 34l8 8M42 34l-8 8', 's'),
      ['rect', { x: 5, y: 7, width: 9, height: 9, transform: 'rotate(45 10 11)' }, 'f2'], ['rect', { x: 34, y: 32, width: 9, height: 9, transform: 'rotate(45 38 36)' }, 'f2'], P('M30 18q5 0 5-5')],
    rocket: [P('M24 5c7 7 9 16 7 26H17c-2-10 0-19 7-26z', 'f2'), P('M24 5c7 7 9 16 7 26H17c-2-10 0-19 7-26z'), ['circle', { cx: 24, cy: 18, r: 3.5 }, 's'],
      P('M17 25l-6 8v4l7-4M31 25l6 8v4l-7-4'), P('M20 36q4 8 4 8t4-8', 'f')],
    power: [P('M27 4L11 27h11l-3 17 17-24H25z', 'f'), P('M27 4L11 27h11l-3 17 17-24H25z')],
    cable: [P('M4 32c8 0 8-16 16-16s8 16 16 16'), ['rect', { x: 34, y: 26, width: 8, height: 12, rx: 2 }, 'f2'], ['rect', { x: 34, y: 26, width: 8, height: 12, rx: 2 }, 's'], P('M42 29h3M42 35h3')],
    bank: [P('M6 18L24 8l18 10z', 'f2'), P('M6 18L24 8l18 10z'), P('M11 22v13M19 22v13M29 22v13M37 22v13'), P('M6 40h36M8 36h32')],
    globe: [['circle', { cx: 24, cy: 24, r: 17 }, 'f2'], ['circle', { cx: 24, cy: 24, r: 17 }, 's'], ['ellipse', { cx: 24, cy: 24, rx: 7.5, ry: 17 }, 's'], P('M7 24h34M10 15h28M10 33h28')],
    flow_arrow: [P('M6 24h33'), P('M30 15l9 9-9 9')]
  };
  var TONES = { accent: 1, neutral: 1, positive: 1, negative: 1, warning: 1 };
  /* draw(name, tone, size) → <svg> de la forma (sin datos); null si la forma no existe */
  function draw(name, tone, size) {
    var prim = SHAPES[name]; if (!prim) return null;
    var s = sv('svg', { viewBox: '0 0 48 48', width: size || 48, height: size || 48, 'aria-hidden': 'true' }, 'kg-sh' + (TONES[tone] && tone !== 'accent' ? ' kg-tone-' + tone : ''));
    prim.forEach(function (p) { s.appendChild(sv(p[0], p[1], p[2])); });
    return s;
  }

  G.register('image', {
    render: function (el, b, ctx) {
      var d = b.data || {}, wrap = h('div');
      wrap.setAttribute('role', 'img'); wrap.setAttribute('aria-label', T(b.alt));
      if (d.kind === 'shape' && d.shape) {
        var sh = d.shape, steps = (sh.steps || []).slice(0, 6);
        if (steps.length) {
          var row = h('div', 'kg-steps');
          steps.forEach(function (st, i) {
            if (i) { var ar = h('div', 'kg-arrow'), as = draw('flow_arrow', 'neutral', 26); if (as) ar.appendChild(as); U.add(row, ar); }
            var cell = h('div', 'kg-step'), bg = h('div', 'bg'), shp = draw(st.shape, sh.tone, 34);
            if (shp) bg.appendChild(shp);
            cell.appendChild(bg); cell.appendChild(h('div', 'lb', T(st.label)));
            if (st.entity && U.entId(st.entity)) {
              cell.classList.add('ent');
              U.linkify(cell, function () { U.runAction({ kind: 'open_dossier', entity: st.entity }, b, ctx); });
            }
            row.appendChild(cell);
          });
          wrap.appendChild(row);
        } else {
          var one = h('div', 'kg-one'), bg1 = h('div', 'bg'), s1 = draw(sh.name, sh.tone, 48);
          if (s1) bg1.appendChild(s1);
          one.appendChild(bg1);
          if (d.caption) one.appendChild(h('div', 'kg-cap', T(d.caption)));
          wrap.appendChild(one);
          el.appendChild(wrap);
          return null;
        }
      } else if (d.kind === 'asset' && d.asset && U.IMG_RX.test(String(d.asset.path || ''))) {
        var img = h('img', 'kg-img');
        img.setAttribute('src', d.asset.path); img.setAttribute('alt', T(b.alt));
        img.setAttribute('width', String(d.asset.w)); img.setAttribute('height', String(d.asset.h));
        img.setAttribute('loading', 'lazy'); img.setAttribute('decoding', 'async'); img.setAttribute('referrerpolicy', 'no-referrer');
        wrap.appendChild(img);
        if (d.asset.credit) wrap.appendChild(h('div', 'kg-cred', String(d.asset.credit)));
      } else {
        wrap.appendChild(h('div', 'kg-unk', T(b.alt)));
      }
      if (d.caption) wrap.appendChild(h('div', 'kg-cap', T(d.caption)));
      el.appendChild(wrap);
      return { go: function () { wrap.classList.add('kg-go'); } };
    },
    toTable: function (b) {
      var sh = (b.data || {}).shape || {};
      return { columns: [U.t('item'), U.t('text')], rows: (sh.steps || []).map(function (s, i) { return [String(i + 1), T(s.label)]; }).concat([[U.t('text'), T(b.alt)]]) };
    }
  });

  /* ── geo.mini ── */
  var REGIONS = { world: [-180, 180, -58, 84], asia: [25, 150, -12, 60], east_asia: [95, 150, 0, 50], americas: [-170, -30, -58, 72],
    europe: [-25, 45, 34, 72], middle_east: [25, 65, 10, 42], africa: [-20, 55, -37, 38], oceania: [105, 180, -50, 5] };
  var _topo = null, _paths = {};
  function topo() {
    if (_topo) return _topo;
    var base = typeof W.BASE === 'string' ? W.BASE : '';
    _topo = (typeof fetch === 'function' ? fetch(base + '/vendor/world-110m.json').then(function (r) { if (!r.ok) throw new Error('topo'); return r.json(); }) : Promise.reject(new Error('nofetch')))
      .then(decode).catch(function () { return null; });
    return _topo;
  }
  // TopoJSON → anillos [lon,lat] (arcos cuantizados con delta; índice negativo = arco al revés)
  function decode(tp) {
    if (!tp || !tp.arcs || !tp.objects) return null;
    var tr = tp.transform || { scale: [1, 1], translate: [0, 0] }, sx = tr.scale[0], sy = tr.scale[1], tx = tr.translate[0], ty = tr.translate[1];
    var arcs = tp.arcs.map(function (a) { var x = 0, y = 0; return a.map(function (p) { x += p[0]; y += p[1]; return [x * sx + tx, y * sy + ty]; }); });
    var obj = tp.objects.land || tp.objects.countries; if (!obj) return null;
    var rings = [];
    var ring = function (ids) {
      var out = [];
      ids.forEach(function (i, k) { var a = i < 0 ? arcs[~i].slice().reverse() : arcs[i]; if (!a) return; out = out.concat(k ? a.slice(1) : a); });
      if (out.length > 2) rings.push(out);
    };
    var geom = function (g) {
      if (!g) return;
      if (g.type === 'GeometryCollection') (g.geometries || []).forEach(geom);
      else if (g.type === 'Polygon') (g.arcs || []).forEach(ring);
      else if (g.type === 'MultiPolygon') (g.arcs || []).forEach(function (pg) { pg.forEach(ring); });
    };
    geom(obj);
    return rings;
  }
  function proj(region, Wd) {
    var bb = REGIONS[region] || REGIONS.world, mid = (bb[2] + bb[3]) / 2 * Math.PI / 180;
    var k = Math.max(0.55, Math.cos(mid)), lonSpan = bb[1] - bb[0], latSpan = bb[3] - bb[2];
    var Hd = Math.round(Math.max(170, Math.min(330, Wd * latSpan / (lonSpan * k))));
    return { W: Wd, H: Hd, x: function (lon) { return (lon - bb[0]) / lonSpan * Wd; }, y: function (lat) { return (bb[3] - lat) / latSpan * Hd; }, bb: bb };
  }
  function landPath(rings, pr, key) {
    if (_paths[key]) return _paths[key];
    var d = '';
    rings.forEach(function (r) {
      var prev = null;
      r.forEach(function (p) {
        var jump = prev && Math.abs(p[0] - prev[0]) > 180;
        d += (prev && !jump ? 'L' : 'M') + pr.x(p[0]).toFixed(1) + ' ' + pr.y(p[1]).toFixed(1);
        prev = p;
      });
      d += 'Z';
    });
    _paths[key] = d;
    return d;
  }
  var KIND_COL = { company: 'var(--kg-a)', fab: 'var(--kg-a)', datacenter: 'var(--kg-a)', port: 'var(--os-ink-2)', strait: 'var(--os-warn)',
    event: 'var(--os-warn)', mine: 'var(--os-ink-2)' };
  G.register('geo.mini', {
    render: function (el, b, ctx) {
      var d = b.data || {}, region = REGIONS[d.region] ? d.region : 'world', pr = proj(region, ctx.compact ? 360 : 600);
      var svg = sv('svg', { viewBox: '0 0 ' + pr.W + ' ' + pr.H, role: 'img', 'aria-label': T(b.alt) || T(b.title) }, 'kg-geo');
      var base = sv('g'); svg.appendChild(base);
      var grat = sv('g');
      for (var lo = Math.ceil(pr.bb[0] / 30) * 30; lo <= pr.bb[1]; lo += 30) grat.appendChild(sv('line', { x1: pr.x(lo).toFixed(1), x2: pr.x(lo).toFixed(1), y1: 0, y2: pr.H }, 'grat'));
      for (var la = Math.ceil(pr.bb[2] / 30) * 30; la <= pr.bb[3]; la += 30) grat.appendChild(sv('line', { x1: 0, x2: pr.W, y1: pr.y(la).toFixed(1), y2: pr.y(la).toFixed(1) }, 'grat'));
      base.appendChild(grat);
      topo().then(function (rings) {
        if (!rings) return;
        base.insertBefore(sv('path', { d: landPath(rings, pr, region + ':' + pr.W) }, 'land'), base.firstChild);
      });
      (d.arcs || []).slice(0, 30).forEach(function (a) {
        if (!Array.isArray(a.from) || !Array.isArray(a.to)) return;
        var x1 = pr.x(a.from[1]), y1 = pr.y(a.from[0]), x2 = pr.x(a.to[1]), y2 = pr.y(a.to[0]), mx = (x1 + x2) / 2, my = Math.min(y1, y2) - Math.abs(x2 - x1) * 0.18;
        svg.appendChild(sv('path', { d: 'M' + x1.toFixed(1) + ' ' + y1.toFixed(1) + ' Q' + mx.toFixed(1) + ' ' + my.toFixed(1) + ' ' + x2.toFixed(1) + ' ' + y2.toFixed(1), 'stroke-width': (1 + (a.weight || 0.3) * 3).toFixed(1) }, 'arc'));
      });
      var pts = (d.points || []).slice(0, 60);
      pts.forEach(function (p, i) {
        var x = pr.x(p.lon), y = pr.y(p.lat); if (!(x >= -2 && x <= pr.W + 2 && y >= -2 && y <= pr.H + 2)) return;
        var c = sv('circle', { cx: x.toFixed(1), cy: y.toFixed(1), r: (3.5 + (p.weight || 0) * 4).toFixed(1) }, 'pt');
        c.style.setProperty('fill', p.risk ? 'var(--os-neg)' : (KIND_COL[p.kind] || 'var(--kg-a)'));
        c.style.setProperty('transition-delay', Math.min(i, 12) * 40 + 'ms');
        tip(c, T(p.label), (p.precision ? (lang() === 'en' ? 'location: ' : 'ubicación: ') + p.precision : '') + (lang() === 'en' ? ' · click: World Monitor' : ' · clic: World Monitor'));
        U.linkify(c, function () { U.runAction({ kind: 'open_world', lat: p.lat, lon: p.lon }, b, ctx); });
        svg.appendChild(c);
        if (i < 8) { var l = sv('text', { x: (x + 7).toFixed(1), y: (y + 4).toFixed(1) }, 'lbl'); l.textContent = T(p.label); svg.appendChild(l); }
      });
      el.appendChild(svg);
      var f = h('div', 'kg-geof');
      if (pts.length) {
        var p0 = pts[0];
        f.appendChild(U.actBtn({ kind: 'open_world', lat: p0.lat, lon: p0.lon, label: { es: '🌐 Abrir en World Monitor', en: '🌐 Open in World Monitor' } }, b, ctx));
      }
      f.appendChild(h('span', null, (d.src || '') + (d.as_of ? ' · ' + when(d.as_of) : '')));
      el.appendChild(f);
      return { go: function () { el.classList.add('kg-go'); } };
    },
    toTable: function (b) {
      return { columns: [U.t('company'), 'Lat', 'Lon', U.t('item')], rows: ((b.data || {}).points || []).map(function (p) { return [T(p.label), String(p.lat), String(p.lon), p.kind + (p.risk ? ' ⚠' : '')]; }) };
    },
    height: function (b, w) { return 120 + proj(((b.data || {}).region) || 'world', w < 520 ? 360 : 600).H * Math.min(1, (w - 30) / (w < 520 ? 360 : 600)); }
  });

  G.shapes = { draw: draw, NAMES: Object.keys(SHAPES), decode: decode, REGIONS: REGIONS };
})(typeof window !== 'undefined' ? window : globalThis);
