/* ============================================================================
   engine/xray.js — X-RAY DE EMPRESA · "desarmar el alma" (Etapa 4, wow #1)
   Overlay NEXUS-styled que abre para cualquier nodo:
   - anatomía (sector, país, precio en vivo, fundamentales)
   - NRS descompuesto término a término (auditabilidad Palantir) + ranking
   - los HILOS entrantes/salientes con peso, clicables → saltan al mapa
   - simulación de impacto INSTANTÁNEA (motor de estados client-side KhipuState,
     ~7ms; el servidor /api/matrix/impact solo refina después si está)

   Dos modos de render sobre el MISMO HTML (buildXRayHTML):
   - cajón lateral (#xray, 560px) — abre desde el mapa
   - escenario grande (.xr-full, multi-columna) — la Cabina de Khipu lo usa a
     pantalla completa para "destripar la empresa por completo".

   Estilos scoped a .xray-scope — no tocan el resto de la app.
   KHIPUS OS (2026-10-10): tema claro/oscuro con los tokens --os-* de engine/cockpit.js
   (ventana = dentro de #bcp-ov; cajón = #xray-ov.kos-themed). Nada de colores oscuros
   fijos: semánticos = --os-good/bad (rellenos) y --os-good-ink/bad-ink/warn-ink (texto AA).
   Los agentes (Comité, Investigación, Análisis IA) son las MASCOTAS de engine/mascot.js.
   ============================================================================ */
(function () {
  'use strict';

  var SECTORS9 = (typeof window.SECTORS9 !== 'undefined') ? window.SECTORS9 : {};
  var CAT_TO_SECTOR = (typeof window.CAT_TO_SECTOR !== 'undefined') ? window.CAT_TO_SECTOR : {};
  function sectorOf(cat) { return CAT_TO_SECTOR[cat] || 'cloud_ia'; }
  // color de DATOS del sector (solo para puntos de relleno, nunca para texto)
  function sectorColor(cat) { var s = SECTORS9[sectorOf(cat)]; return s ? s.color : '#4C8DF6'; }
  function sectorLabel(cat) {
    if (window.sectorName) return window.sectorName(sectorOf(cat));
    var s = SECTORS9[sectorOf(cat)]; return s ? s.label : 'Cloud & IA';
  }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function lid(v) { return (typeof v === 'object' && v !== null) ? v.id : v; }
  function fmtPct(v) { return (v >= 0 ? '+' : '') + v.toFixed(1) + '%'; }
  // REGLA BILINGÜE: todo texto visible pasa por L(es, en)
  function isEn() {
    var l = window.LANG;
    if (!l) { try { l = localStorage.getItem('eco_lang'); } catch (e) { l = null; } }
    return l === 'en';
  }
  function L(es, en) { return isEn() ? en : es; }

  // Colores SEMÁNTICOS de Khipus OS (siempre con respaldo oscuro). *_INK = texto (contraste AA);
  // los vivos (--os-good / --os-bad) quedan para barras y rellenos.
  var C_GOOD = 'var(--os-good-ink,#2fbf5b)', C_BAD = 'var(--os-bad-ink,#F47C7C)', C_WARN = 'var(--os-warn-ink,#F2C46D)';
  // mascota del agente (engine/mascot.js); sin el módulo, el emoji de antes
  function mascot(id, size, emo) {
    var M = window.KhipuMascot;
    if (M && M.svg) { try { return M.svg(id, size || 16); } catch (e) {} }
    return '<span class="xr-ic" aria-hidden="true">' + (emo || '🤖') + '</span>';
  }
  function mascotStack(ids, size, emo) {
    var M = window.KhipuMascot;
    if (M && M.stack) { try { return M.stack(ids, size || 16); } catch (e) {} }
    return '<span class="xr-ic" aria-hidden="true">' + (emo || '🤖') + '</span>';
  }

  // ── estilos (inyectados una vez) ──
  function ensureStyles() {
    if (document.getElementById('xray-styles')) return;
    var css = `
/* KHIPUS OS (2026-10-10): sin colores oscuros fijos — solo tokens --os-* (claro = body sin .dark,
   oscuro = body.dark). Valen en las ventanas (#bcp-ov) y en el cajón (#xray-ov lleva .kos-themed).
   Siempre var(--token, respaldo-oscuro): sin cockpit.js el X-Ray se ve como antes (oscuro). */
#xray-ov{position:fixed;inset:0;z-index:6000;display:none;align-items:stretch;justify-content:flex-end;
  background:var(--kos-scrim,rgba(0,0,0,.5));-webkit-backdrop-filter:blur(6px) saturate(1.1);backdrop-filter:blur(6px) saturate(1.1);
  font-family:var(--os-font,'Nunito',system-ui,-apple-system,'Segoe UI',sans-serif)}
#xray-ov.show{display:flex;animation:xrFade .18s ease}
@keyframes xrFade{from{opacity:0}to{opacity:1}}
#xray{width:min(560px,100%);height:100%;overflow-y:auto;overflow-x:hidden;overscroll-behavior:contain;box-sizing:border-box;
  color:var(--os-ink,#F2F2F5);background:var(--os-bg,#0E0F14);padding-bottom:18px;
  border-radius:var(--os-r,18px) 0 0 var(--os-r,18px);box-shadow:var(--kos-shadow-lg,0 2px 8px rgba(0,0,0,.45),0 22px 56px rgba(0,0,0,.55));
  transform:translateX(24px);animation:xrSlide .22s ease forwards;scrollbar-width:thin;scrollbar-color:var(--os-surface-3,#2A2B36) transparent}
@keyframes xrSlide{to{transform:translateX(0)}}
@media(max-width:760px){#xray{width:100%;border-radius:0}}
@media(prefers-reduced-motion:reduce){#xray{animation:none;transform:none}#xray-ov.show{animation:none}}
/* --xr-card = fondo de cada sección · --xr-cell = celdas/filas dentro de ella. En una ventana (fondo
   --os-surface) las secciones son --os-surface-2; en el cajón (fondo --os-bg) son tarjetas --os-surface. */
/* --xr-link: el acento como TEXTO (enlaces): mezclado con la tinta para llegar a ≥5:1 sobre cualquier superficie
   (el --os-accent puro da 4.3:1 sobre --os-surface-2 en el tema claro) */
.xray-scope{--xr-card:var(--os-surface-2,#1F2029);--xr-cell:var(--os-surface,#17181F);--xr-sh:none;
  --xr-link:var(--os-accent,#4C8DF6);--xr-link:color-mix(in srgb,var(--os-accent,#4C8DF6) 82%,var(--os-ink,#F2F2F5));
  color:var(--os-ink,#F2F2F5);font-family:var(--os-font,'Nunito',system-ui,-apple-system,'Segoe UI',sans-serif);
  font-size:13px;line-height:1.45;-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale}
#xray.xray-scope{--xr-card:var(--os-surface,#17181F);--xr-cell:var(--os-surface-2,#1F2029);
  --xr-sh:var(--os-shadow,0 1px 2px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.35))}
.xray-scope *{box-sizing:border-box}
.xray-scope button{font-family:inherit}
.xray-scope .xr-mono{font-variant-numeric:tabular-nums;letter-spacing:-.005em}
.xray-scope .xr-hd{position:relative;padding:18px 20px 14px}
#xray .xr-hd{position:sticky;top:0;z-index:2;background:var(--os-bg,#0E0F14)}
.xray-scope .xr-close{appearance:none;-webkit-appearance:none;position:absolute;top:14px;right:14px;width:40px;height:40px;padding:0;border:0;
  border-radius:999px;cursor:pointer;background:transparent;color:var(--os-ink-2,#A6A8B5);font-size:15px;font-weight:600;line-height:1;
  display:inline-flex;align-items:center;justify-content:center;transition:background-color .15s,color .15s}
.xray-scope .xr-close:hover{background:var(--os-surface-2,#1F2029);color:var(--os-ink,#F2F2F5)}
.xray-scope .xr-name{font-size:22px;font-weight:800;letter-spacing:-.015em;line-height:1.2;display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;
  padding-right:44px;overflow-wrap:anywhere}
.xray-scope .xr-tk{font-size:13px;color:var(--os-ink-2,#A6A8B5);font-weight:700}
.xray-scope .xr-sec{display:flex;align-items:center;flex-wrap:wrap;gap:7px;font-size:12.5px;color:var(--os-ink-2,#A6A8B5);margin-top:6px}
.xray-scope .xr-dot{display:inline-block;flex:none;width:9px;height:9px;border-radius:50%}
.xray-scope .xr-px{margin-top:12px;display:flex;align-items:baseline;flex-wrap:wrap;gap:10px}
.xray-scope .xr-px .p{font-size:26px;font-weight:800;letter-spacing:-.02em;color:var(--os-ink,#F2F2F5)}
.xray-scope .xr-px .p.xr-pending{font-size:15px;font-weight:600;color:var(--os-ink-2,#A6A8B5);letter-spacing:0}
.xray-scope .xr-px .chg{font-size:14px;font-weight:700}
.xray-scope .xr-px .chg small{font-size:11px;font-weight:600;color:var(--os-ink-2,#A6A8B5);margin-left:5px}
.xray-scope .xr-lin{font-size:11.5px;line-height:1.5;color:var(--os-ink-2,#A6A8B5);margin-top:4px}
.xray-scope .xr-strong{color:var(--os-ink,#F2F2F5);font-weight:700}
.xray-scope .xr-sect{background:var(--xr-card);border-radius:var(--os-r,18px);box-shadow:var(--xr-sh);padding:14px 16px;margin:0 12px 12px;min-width:0}
#xray .xr-sect{margin:0 14px 12px}
.xray-scope .xr-h{font-size:13px;font-weight:700;letter-spacing:-.005em;color:var(--os-ink,#F2F2F5);
  margin:0 0 10px;display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap}
.xray-scope .xr-h .v{font-size:15px;font-weight:800}
.xray-scope .xr-h.bad{color:var(--os-bad-ink,#F47C7C)}
.xray-scope .xr-h.win{color:var(--os-good-ink,#2fbf5b)}
.xray-scope .nrsrow{display:grid;grid-template-columns:112px minmax(0,1fr) 58px;gap:10px;align-items:center;font-size:12.5px;color:var(--os-ink-2,#A6A8B5);margin:7px 0}
.xray-scope .nrsrow>span:first-child{min-width:0;overflow-wrap:break-word;hyphens:auto;color:var(--os-ink,#F2F2F5);font-weight:600}
.xray-scope .nrsbar{height:8px;border-radius:999px;background:var(--os-surface-3,#2A2B36);overflow:hidden}
.xray-scope .nrsbar i{display:block;height:100%;background:var(--os-accent,#4C8DF6);border-radius:999px}
.xray-scope .nrsrow.hot i{background:var(--os-bad,#f06565)}
.xray-scope .nrsrow .nv{text-align:right;color:var(--os-ink,#F2F2F5);font-weight:700}
.xray-scope .nrsrow .nd{font-size:11px;font-weight:400;line-height:1.35;color:var(--os-ink-2,#A6A8B5)}
.xray-scope .thread{display:flex;align-items:center;gap:9px;font-size:13px;padding:8px 11px;margin:4px 0;cursor:pointer;
  border-radius:var(--os-r-sm,12px);background:var(--xr-cell);transition:background-color .15s,transform .15s}
.xray-scope .thread:hover{background:var(--os-surface-3,#2A2B36);transform:translateX(-2px)}
.xray-scope .thread .tdir{flex:none;width:14px;text-align:center;color:var(--os-ink-2,#A6A8B5);font-weight:700}
.xray-scope .thread .xr-dot{width:8px;height:8px}
.xray-scope .thread .tnm{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--os-ink,#F2F2F5);font-weight:600}
.xray-scope .thread .trel{font-size:11px;color:var(--os-ink-2,#A6A8B5);flex:none;max-width:100px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.xray-scope .thread .tw{font-size:11.5px;color:var(--os-ink-2,#A6A8B5);flex:none;font-variant-numeric:tabular-nums}
.xray-scope .tcap{font-size:12px;font-weight:700;color:var(--os-ink-2,#A6A8B5);margin:12px 0 4px}
.xray-scope .relchips{display:flex;flex-wrap:wrap;gap:6px}
.xray-scope .relchip{font-size:11.5px;font-weight:600;color:var(--os-ink-2,#A6A8B5);padding:4px 10px;border-radius:999px;background:var(--xr-cell)}
.xray-scope .relchip b{color:var(--os-ink,#F2F2F5);font-variant-numeric:tabular-nums}
.xray-scope .impact-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;text-align:center}
.xray-scope .icell{border-radius:var(--os-r-sm,12px);padding:11px 6px;background:var(--xr-cell);min-width:0}
.xray-scope .icell b{display:block;font-size:18px;font-weight:800;letter-spacing:-.015em;color:var(--os-ink,#F2F2F5);font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
.xray-scope .icell.hot b{color:var(--os-bad-ink,#F47C7C)}
.xray-scope .icell b.neg{color:var(--os-bad-ink,#F47C7C)}
.xray-scope .icell span{font-size:11px;line-height:1.3;color:var(--os-ink-2,#A6A8B5);margin-top:3px;display:block}
.xray-scope .xr-btns{display:flex;gap:8px;flex-wrap:wrap;padding:6px 12px 12px}
#xray .xr-btns{padding:4px 14px}
.xray-scope .xrb{appearance:none;-webkit-appearance:none;border:0;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:7px;
  height:38px;padding:0 15px;border-radius:999px;font-size:13px;font-weight:600;white-space:nowrap;
  background:var(--xr-card);color:var(--os-ink,#F2F2F5);box-shadow:var(--xr-sh);transition:background-color .15s,opacity .15s,transform .1s}
.xray-scope .xrb:hover{background:var(--os-surface-3,#2A2B36)}
.xray-scope .xrb:active{transform:scale(.98)}
.xray-scope .xrb.pri{background:var(--os-btn,#F2F2F5);color:var(--os-btn-ink,#111216);font-weight:700}
.xray-scope .xrb.pri:hover{opacity:.88}
.xray-scope .xrb .xr-ic{font-size:14px;line-height:1}
.xray-scope .xrb .km-stack{--km-ring:var(--xr-card)}
.xray-scope .xr-victim{display:flex;align-items:center;gap:9px;font-size:12.5px;padding:6px 4px;margin:0 -4px;border-radius:8px;cursor:pointer}
.xray-scope .xr-victim:hover .vn{color:var(--xr-link)}
.xray-scope .xr-victim .xr-dot{width:7px;height:7px}
.xray-scope .xr-victim .vn{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--os-ink,#F2F2F5);font-weight:600;transition:color .15s}
.xray-scope .xr-victim .vbar{flex:1;height:6px;border-radius:999px;overflow:hidden;
  background:var(--os-surface-3,#2A2B36);background:color-mix(in srgb,var(--os-bad,#f06565) 16%,transparent)}
.xray-scope .xr-victim .vbar i{display:block;height:100%;border-radius:999px;background:var(--os-bad,#f06565)}
.xray-scope .xr-victim .vp{font-size:12px;font-weight:700;color:var(--os-bad-ink,#F47C7C);width:44px;text-align:right;flex:none;font-variant-numeric:tabular-nums}
.xray-scope .xr-victim.win .vbar{background:var(--os-surface-3,#2A2B36);background:color-mix(in srgb,var(--os-good,#2fbf5b) 16%,transparent)}
.xray-scope .xr-victim.win .vbar i{background:var(--os-good,#2fbf5b)}
.xray-scope .xr-victim.win .vp{color:var(--os-good-ink,#2fbf5b)}
.xray-scope .xr-loading{color:var(--os-ink-2,#A6A8B5);font-size:12.5px;font-style:italic;line-height:1.5}
.xray-scope .xr-note{font-size:12.5px;line-height:1.55;color:var(--os-ink-2,#A6A8B5);margin-top:11px;overflow-wrap:anywhere}
.xray-scope a,.xray-scope .xr-tj{color:var(--xr-link);font-weight:600;text-decoration:none}
.xray-scope a:hover{text-decoration:underline}
.xray-scope .thread-scroll{max-height:none}
/* foco de teclado VISIBLE (WCAG 2.4.7) */
.xray-scope .xrb:focus-visible,.xray-scope .xr-close:focus-visible,.xray-scope .thread:focus-visible,.xray-scope .xr-victim:focus-visible,.xray-scope a:focus-visible{
  outline:2px solid var(--os-accent,#4C8DF6);outline-offset:2px}
/* puentes: piezas de OTROS módulos que llegan con colores fijos de la piel vieja (explain.js "?",
   app.html liveCapDot ✓) — dentro del X-Ray se leen con los tokens */
.xray-scope span[onclick*="explainMetric"]{color:var(--xr-link)!important;border-color:var(--os-line,rgba(255,255,255,.07))!important;background:var(--xr-cell)}
.xray-scope span[style*="#7ecbff" i]{color:var(--xr-link)!important}
/* ── modo escenario (ventana de Khipus OS / Cabina) ── */
.xray-scope.xr-full{padding:0 2px 20px}
.xray-scope.xr-full .xr-hd{padding:4px 4px 16px}
.xray-scope.xr-full .xr-name{font-size:26px}
.xray-scope.xr-full .xr-cols{column-width:330px;column-gap:14px;padding:0}
.xray-scope.xr-full .xr-cols .xr-sect{break-inside:avoid;-webkit-column-break-inside:avoid;margin:0 0 14px}
.xray-scope.xr-full .thread-scroll{max-height:300px;overflow-y:auto;overscroll-behavior:contain;scrollbar-width:thin;scrollbar-color:var(--os-surface-3,#2A2B36) transparent}
.xray-scope.xr-full .xr-btns{padding:2px 0}
@media(max-width:420px){.xray-scope .nrsrow{grid-template-columns:112px minmax(0,1fr) 52px;gap:8px}.xray-scope .xr-px .p{font-size:23px}}
@media(prefers-reduced-motion:reduce){.xray-scope .thread,.xray-scope .xrb,.xray-scope .xr-victim .vn{transition:none}.xray-scope .thread:hover{transform:none}.xray-scope .xrb:active{transform:none}}
#xray-fab{position:fixed;left:0;top:0;z-index:5999}
`;
    var st = document.createElement('style');
    st.id = 'xray-styles';
    st.textContent = css;
    document.head.appendChild(st);
  }

  // ── HILOS entrantes / salientes ──
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
    return '<div class="thread" role="button" tabindex="0" onclick="window._xrayJump(\'' + esc(t.n.id) + '\')" title="' + esc(t.rel || '') + '">' +
      '<span class="tdir" aria-hidden="true">' + arrow + '</span>' +
      '<span class="xr-dot" style="background:' + sectorColor(t.n.cat) + '"></span>' +
      '<span class="tnm">' + esc(t.n.label) + '</span>' +
      (t.rel ? '<span class="trel">' + esc(t.rel) + '</span>' : '') +
      '<span class="tw">w' + t.w + '</span></div>';
  }

  // conteo por tipo de relación (para el desglose "de qué está hecha")
  function relBreakdown(th) {
    var counts = {};
    th.up.concat(th.down).forEach(function (t) { var k = t.type || 'supply'; counts[k] = (counts[k] || 0) + 1; });
    return Object.keys(counts).sort(function (a, b) { return counts[b] - counts[a]; })
      .map(function (k) { return '<span class="relchip">' + esc(k) + ' <b>' + counts[k] + '</b></span>'; }).join('');
  }

  // ranking de riesgo entre las 407 (barato: NODES ~407)
  function nrsRank(id, total) {
    if (typeof window.computeNRS !== 'function' || !window.NODES) return null;
    var worse = 0, n = 0;
    window.NODES.forEach(function (x) { var s = window.computeNRS(x.id); if (s != null) { n++; if (s > total) worse++; } });
    return { rank: worse + 1, of: n };
  }

  // Estado en bolsa VERIFICADO (nodes/listing_status.js): salió a bolsa, la
  // compraron, cerró… con fecha de verificación y fuente clicable.
  function listingLine(n) {
    var e = n && n.listing;
    if (!e || e.status === 'private' || e.status === 'unknown') return '';
    var txt = L(e.note_es || '', e.note_en || e.note_es || '');
    if (!txt) return '';
    var src = (e.source_url && /^https?:\/\//i.test(e.source_url)) ? ' · <a href="' + esc(e.source_url) + '" target="_blank" rel="noopener noreferrer">' + L('fuente', 'source') + ' ↗</a>' : '';
    return '<div class="xr-note" style="margin-top:6px">✓ ' + esc(txt) +
      '<span style="font-size:11.5px"> · ' + L('verificado', 'verified') + ' ' + esc(e.as_of || '') + src + '</span></div>';
  }

  // ── construye el HTML interno del X-Ray (lo usan el cajón y el escenario) ──
  function buildXRayHTML(id, opts) {
    opts = opts || {};
    var full = !!opts.full;
    var n = window.NODE_BY_ID ? window.NODE_BY_ID[id] : null;
    if (!n) return '<div class="xr-loading" style="padding:24px">' + L('Sin datos para ', 'No data for ') + esc(id) + '</div>';
    var col = sectorColor(n.cat);
    var bd = window.computeNRSBreakdown ? window.computeNRSBreakdown(id) : null;
    var th = threadsFor(id);
    var meta = (window.NODE_META || {})[id] || {};
    var tk = (n.ticker || '').split(' · ')[0];
    var rank = bd ? nrsRank(id, bd.total) : null;

    var nrsHTML = bd ? bd.terms.map(function (t) {
      return '<div class="nrsrow' + (t.hot ? ' hot' : '') + '">' +
        '<span>' + t.key + '<div class="nd">' + esc(t.detail) + '</div></span>' +
        '<div class="nrsbar"><i style="width:' + Math.round(t.val / t.max * 100) + '%"></i></div>' +
        '<span class="nv xr-mono">' + t.val + '/' + t.max + '</span></div>';
    }).join('') : '<div class="xr-loading">' + L('NRS no disponible', 'NRS not available') + '</div>';

    // Anatomía: Empleados / Mkt Cap / Ingresos se reemplazan por el dato EN
    // VIVO (window.fillLiveMeta, en wire) cuando hay perfil; si no, catálogo.
    var mm = (meta.founded || n.mkt) ? '<div class="xr-sect"><div class="xr-h">' + L('Anatomía', 'Anatomy') + '</div>' +
      '<div class="impact-grid" style="grid-template-columns:1fr 1fr">' +
      '<div class="icell"><b class="xr-mono">' + esc(meta.founded || '—') + '</b><span>' + L('Fundada', 'Founded') + '</span></div>' +
      '<div class="icell"><b class="xr-mono xr-emp" data-live="employees" data-live-fmt="k">' + (meta.employees ? esc(meta.employees >= 1000 ? Math.round(meta.employees / 1000) + 'K' : meta.employees) : '—') + '</b><span>' + L('Empleados', 'Employees') + '</span></div>' +
      '<div class="icell"><b class="xr-mono xr-mcap" data-live="mcap">' + (meta.mktcap_b ? (isFinite(+meta.mktcap_b) ? '$' + esc(meta.mktcap_b) + 'B' + (window.liveCapDot ? window.liveCapDot(meta) : '') : esc(meta.mktcap_b)) : (n.mkt ? '—' : L('Priv.', 'Priv.'))) + '</b><span>Mkt Cap</span></div>' +
      '<div class="icell"><b style="font-size:15px" class="xr-mono xr-rev" data-live="revenue">' + esc(meta.revenue_2025 || '—') + '</b><span class="xr-rev-l" data-live-label="revenue">' + L('Ingresos 2025', 'Revenue 2025') + '</span></div>' +
      '</div>' + (meta.geo_risk ? '<div class="xr-note">🌐 ' + esc(meta.geo_risk) + '</div>' : '') + '</div>' : '';

    // fundamentales extra (margen / crecimiento / puerto) si existen
    var funds = '';
    if (full && (n.margin != null || n.growth || n.country)) {
      // `growth` a veces es un número corto ("+35%") y a veces una FRASE
      // entera (bancos centrales, capa macro): la frase no cabe en un cuadrito
      // de 3 columnas y se volvía una torre ilegible — va como nota debajo.
      var g = String(n.growth || '').trim();
      var gCorto = g && g.length <= 14;
      funds = '<div class="xr-sect"><div class="xr-h">' + L('Fundamentales', 'Fundamentals') + '</div><div class="impact-grid">' +
        '<div class="icell"><b class="xr-mono" data-live="margin">' + (n.margin != null ? Math.round(n.margin * 100) + '%' : '—') + '</b><span data-live-sub="margin">' + (n.margin_live ? L('Margen · en vivo', 'Margin · live') : L('Margen · catálogo', 'Margin · catalog')) + '</span></div>' +
        '<div class="icell"><b style="font-size:14px" class="xr-mono" data-live="growth">' + (gCorto ? esc(g) : '—') + '</b><span data-live-label="growth">' + L('Crecim. · catálogo', 'Growth · catalog') + '</span></div>' +
        '<div class="icell"><b class="xr-mono">' + esc(n.country || '—') + '</b><span>' + L('País', 'Country') + '</span></div>' +
        '</div>' + (g && !gCorto ? '<div class="xr-note">' + esc(g) + '</div>' : '') + '</div>';
    }

    // hilos: en escenario mostramos TODOS (scroll); en cajón, los 6 top
    var upList = full ? th.up : th.up.slice(0, 6);
    var downList = full ? th.down : th.down.slice(0, 6);
    var threadsHTML = '<div class="xr-sect"><div class="xr-h">' + L('Hilos — a quién provee / de quién depende', 'Threads — who it supplies / who it depends on') + '</div>' +
      (full && (th.up.length + th.down.length) ? '<div class="relchips" style="margin-bottom:10px">' + relBreakdown(th) + '</div>' : '') +
      (!th.up.length && !th.down.length ? '<div class="xr-loading">' + L('Sin vínculos de suministro en el mapa (su efecto llega por los factores macro).', 'No supply links on the map (its effect travels through macro factors).') + '</div>' : '') +
      (th.up.length ? '<div class="tcap">' + L('Depende de', 'Depends on') + ' (' + th.up.length + ')</div><div class="thread-scroll">' + upList.map(function (t) { return threadRow(t, 'up'); }).join('') + '</div>' : '') +
      (th.down.length ? '<div class="tcap">' + L('Provee a', 'Supplies') + ' (' + th.down.length + ')</div><div class="thread-scroll">' + downList.map(function (t) { return threadRow(t, 'down'); }).join('') + '</div>' : '') +
      '</div>';

    var header =
      '<div class="xr-hd">' +
        '<button type="button" class="xr-close" onclick="window._xrayClose()" title="' + L('Cerrar', 'Close') + '" aria-label="' + L('Cerrar', 'Close') + '">✕</button>' +
        '<div class="xr-name">' + esc(n.label) + ' <span class="xr-tk xr-mono">' + esc(tk) + '</span></div>' +
        '<div class="xr-sec"><span class="xr-dot" style="background:' + col + '"></span>' +
          sectorLabel(n.cat) + ' · ' + esc(n.country || '—') + ' · ' + (th.up.length + th.down.length) + ' ' + L('vínculos', 'links') + '</div>' +
        '<div class="xr-px xr-mono" id="xr-px"><span class="p xr-pending">' + (n.mkt ? '— · —' : L('no cotiza en bolsa', 'not publicly traded')) + '</span></div>' +
        '<div class="xr-lin" id="xr-lin"></div>' + listingLine(n) +
      '</div>';

    var nrsSection =
      '<div class="xr-sect"><div class="xr-h"><span>' + L('Riesgo NRS — por qué ', 'NRS risk — why ') + (bd ? bd.total : '?') +
        (window.explainChip ? window.explainChip('nrs') : '') + '</span>' +
        '<span class="v xr-mono" style="color:' + (bd && bd.total >= 60 ? C_BAD : bd && bd.total >= 35 ? C_WARN : C_GOOD) + '">' +
        (bd ? bd.total : '?') + '/100</span></div>' + nrsHTML +
        (rank ? '<div class="xr-lin" style="margin-top:8px">' + L('Ranking de riesgo: ', 'Risk ranking: ') + '<b class="xr-strong">#' + rank.rank + '</b> ' + L('de', 'of') + ' ' + rank.of + ' ' + L('empresas', 'companies') + '</div>' : '') +
        '<div class="xr-lin" style="margin-top:4px">' + L('ⓘ fórmula NRS · el motor de matrices puede fijarlo con datos vivos', 'ⓘ NRS formula · the matrix engine can refine it with live data') + '</div></div>';

    var impactSection =
      '<div class="xr-sect"><div class="xr-h">' + L('Si ', 'If ') + esc(n.label) + L(' cae — onda de impacto', ' fails — impact wave') + '</div>' +
        '<div id="xr-impact"><div class="xr-loading">' + L('Calculando propagación…', 'Computing propagation…') + '</div></div></div>';

    // botones de verdad (<button>: se alcanzan con el teclado); los AGENTES llevan su mascota
    var btns =
      '<div class="xr-btns">' +
        '<button type="button" class="xrb pri" onclick="window._xrayShock(\'' + esc(id) + '\')"><span class="xr-ic" aria-hidden="true">⚡</span>' + L('Ver onda en el mapa', 'See wave on the map') + '</button>' +
        (window.openFinCard ? '<button type="button" class="xrb" onclick="window._surface ? window._surface(\'dossier\', \'' + esc(id) + '\') : window.openFinCard(\'' + esc(id) + '\')"><span class="xr-ic" aria-hidden="true">📊</span>Dossier</button>' : '') +
        (window.openCompare ? '<button type="button" class="xrb" onclick="window._xrayCompare(\'' + esc(id) + '\')"><span class="xr-ic" aria-hidden="true">⇄</span>' + L('Comparar', 'Compare') + '</button>' : '') +
        (window.__tkgOpenObj ? '<button type="button" class="xrb" onclick="window._xrayTKG(\'' + esc(id) + '\')"><span class="xr-ic" aria-hidden="true">◈</span>' + L('En el tiempo', 'Over time') + '</button>' : '') +
        (window.KhipuResearch ? '<button type="button" class="xrb" onclick="window.KhipuResearch.open(\'' + esc(id) + '\')">' + mascotStack(['analista', 'radar', 'cadena'], 18, '🔬') + L('Investigación IA', 'AI research') + '</button>' : '') +
        (window.KhipuCommittee ? '<button type="button" class="xrb" onclick="window.KhipuCommittee.open(\'' + esc(id) + '\')">' + mascot('comite', 18, '🏛') + L('Comité', 'Committee') + '</button>' : '') +
        (window._openSecondBrain ? '<button type="button" class="xrb" onclick="window._openSecondBrain(\'' + esc(id) + '\')">' + mascot('khipu', 18, '🧠') + L('Análisis IA', 'AI analysis') + '</button>' : '') +
      '</div>';

    // ONTOLOGÍA NIVEL 2 (matrix/tensor.py vía /api/tensor/node): concentración, países, valor arrastrado
    var structSection =
      '<div class="xr-sect"><div class="xr-h"><span>🧮 ' + L('Estructura', 'Structure') + '</span>' +
        (window.explainChip ? window.explainChip('tensor_struct') : '') + '</div>' +
        '<div id="xr-struct"><div class="xr-loading">' + L('Calculando…', 'Computing…') + '</div></div></div>';

    var body = nrsSection + mm + funds + threadsHTML + structSection + impactSection + btns;
    if (full) return header + '<div class="xr-cols">' + body + '</div>';
    return header + body;
  }

  // ── precio en vivo (scoped al root) ──
  // 1º Finnhub (/api/quote, EE.UU.); si no responde o es de otra bolsa, el
  // perfil en vivo (KhipuLive: Yahoo, cualquier bolsa, en su moneda). Se
  // refresca cada 60 s mientras el X-Ray está a la vista (startPriceTimer).
  var PRICE_MS = 60 * 1000;
  function hhmmss(d) {
    try { return d.toLocaleTimeString(isEn() ? 'en-US' : 'es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' }); }
    catch (e) { return ''; }
  }
  // Estado del mercado → etiqueta honesta (misma regla que engine/fincard.js):
  // "en vivo" SOLO si la sesión está en curso. Yahoo quoteSummary trae
  // marketState; Finnhub y el gráfico de Yahoo no → se deduce por la
  // antigüedad del precio (`t` de Finnhub / market_time), nunca por el reloj
  // de la consulta. live: true = sesión en curso · false = último cierre ·
  // null = la fuente no dice ni estado ni hora.
  var STALE_UNKNOWN_MS = 30 * 60 * 1000, STALE_OPEN_MS = 6 * 3600 * 1000;
  function mktState(st) {
    st = String(st || '').toUpperCase();
    if (!st) return null;
    if (st === 'REGULAR') return { open: true, es: 'mercado abierto', en: 'market open' };
    if (st.indexOf('PRE') === 0) return { open: false, es: 'pre-apertura', en: 'pre-market' };
    if (st.indexOf('POST') === 0) return { open: false, es: 'después del cierre', en: 'after hours' };
    return { open: false, es: 'mercado cerrado', en: 'market closed' };
  }
  function quoteInfo(state, qt, asOf) {
    var ms = mktState(state);
    if (qt && isNaN(qt.getTime())) qt = null;
    var ref = asOf && !isNaN(asOf.getTime()) ? asOf.getTime() : Date.now();
    var age = qt ? Math.max(0, ref - qt.getTime()) : null;
    var live;
    if (ms) live = ms.open && !(age != null && age > STALE_OPEN_MS);
    else live = age != null ? age <= STALE_UNKNOWN_MS : null;
    return { ms: ms, qt: qt, live: live };
  }
  // hora del precio: "14:32:05" si es de hoy; "26 sep, 22:00" si es de otro día
  function whenTxt(d) {
    if (!d) return '';
    if (d.toDateString() === new Date().toDateString()) return hhmmss(d);
    try { return d.toLocaleString(isEn() ? 'en-US' : 'es-ES', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false }); }
    catch (e) { return d.toISOString().slice(0, 16).replace('T', ' '); }
  }
  // `els` = {px, lin} capturados ANTES de la consulta: si el cajón ya muestra
  // otra empresa (render() reemplaza su innerHTML), esos nodos quedaron fuera
  // del documento y la respuesta vieja se descarta — nunca pinta el precio de
  // A en la ficha de B.
  function priceEls(root) {
    return { px: root.querySelector('#xr-px'), lin: root.querySelector('#xr-lin') };
  }
  function paintPrice(els, price, pct, cur, src, qi) {
    var el = els && els.px;
    if (!el || !el.isConnected || !(price > 0)) return;
    qi = qi || { live: null, qt: null, ms: null };
    var p = (!cur || cur === 'USD') ? '$' + price.toFixed(2)
      : price.toLocaleString(isEn() ? 'en-US' : 'es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' ' + esc(cur);
    // la variación dice de CUÁNDO es: "hoy" solo con sesión en curso
    var chgWhen = qi.live === true ? '' : qi.live === false ? ' ' + L('última sesión', 'last session') : '';
    el.innerHTML = '<span class="p">' + p + '</span>' +
      (pct != null && isFinite(pct) ? '<span class="chg" style="color:' + (pct >= 0 ? C_GOOD : C_BAD) + '">' + fmtPct(pct) +
        (chgWhen ? '<small>' + esc(chgWhen) + '</small>' : '') + '</span>' : '');
    var lin = els.lin;
    if (!lin || !lin.isConnected) return;
    var parts = ['ⓘ ' + src];
    if (qi.live === true) {
      parts.push(L('en vivo', 'live'));
      if (qi.qt) parts.push(L('precio de las ', 'price as of ') + whenTxt(qi.qt));
    } else if (qi.live === false) {
      parts.push(qi.ms ? L(qi.ms.es, qi.ms.en) : L('mercado cerrado', 'market closed'));
      if (qi.qt) parts.push(L('último precio: ', 'last price: ') + whenTxt(qi.qt));
    } else {
      parts.push(L('consultado ', 'checked ') + hhmmss(new Date()));
      parts.push(L('la fuente no indica la hora del precio', 'the source does not give the price time'));
    }
    parts.push(L('se revisa cada minuto', 'checked every minute'));
    lin.textContent = parts.join(' · ');
  }
  function loadPriceLive(els, n) {
    var K = window.KhipuLive;
    if (!K || !K.profile) return;
    K.profile(n.mkt).then(function (p) {
      if (!p || !p.available || p.price == null || !els.px || !els.px.isConnected) return;
      var qt = p.market_time ? new Date(p.market_time) : null;
      var asOf = p.as_of ? new Date(p.as_of) : null;
      paintPrice(els, +p.price, p.change_pct, p.currency, (K.sourceName && K.sourceName(p)) || p.source || '—',
        quoteInfo(p.market_state, qt, asOf));
    }).catch(function () {});
  }
  function loadPrice(root, n) {
    if (!n.mkt) return;
    var els = priceEls(root);          // capturados AHORA (ver priceEls)
    if (!els.px) return;
    if (!window.DataLayer) { loadPriceLive(els, n); return; }
    window.DataLayer.quote(n.mkt).then(function (q) {
      if (!els.px.isConnected) return;   // el cajón ya muestra otra empresa
      if (!q || !(q.c > 0)) { loadPriceLive(els, n); return; }   // Finnhub da c=0 si no conoce el símbolo
      var pct = q.pc ? (q.c - q.pc) / q.pc * 100 : null;
      // `t` de Finnhub = hora (unix) del último precio; sin ella no se afirma "en vivo"
      var qt = q.t > 0 ? new Date(q.t * 1000) : null;
      // R9: /api/quote responde Finnhub O Yahoo (cascada): fuente y moneda reales, no un rótulo fijo
      var src = (window.quoteSrcName && q.provider) ? window.quoteSrcName(q.provider) : (q.provider === 'yahoo' ? 'Yahoo' : 'Finnhub');
      var cur = q.converted ? 'USD' : (q.currency || 'USD');
      if (q.converted && q.currency && q.currency !== 'USD') src += ' · ' + L('convertido de ' + q.currency, 'converted from ' + q.currency);
      paintPrice(els, q.c, pct, cur, src, quoteInfo(null, qt, null));
    }).catch(function () { if (els.px.isConnected) loadPriceLive(els, n); });
  }
  function stopPriceTimer(root) {
    if (root && root._xrPxTimer) { clearInterval(root._xrPxTimer); root._xrPxTimer = null; }
  }
  function startPriceTimer(root, n) {
    stopPriceTimer(root);
    if (!n.mkt) return;
    root._xrPxTimer = setInterval(function () {
      // cerrado, re-renderizado o escondido (cajón / Cabina) → se apaga solo
      // desconectado (re-render / cerrado de verdad) → se apaga; solo OCULTO
      // (Cabina cerrada, pestaña Fundamentales) → se salta el tick y sigue
      if (!root.isConnected) { stopPriceTimer(root); return; }
      if (document.hidden || !root.getClientRects().length) return;
      loadPrice(root, n);
    }, PRICE_MS);
  }

  function renderVictims(root, id, n, impacts, note) {
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
    var isFull = root.classList && root.classList.contains('xr-full');
    var topN = isFull ? 12 : 6;
    var top = arr.slice(0, topN).map(function (x) {
      var node = window.NODE_BY_ID[x.id]; if (!node) return '';
      return '<div class="xr-victim" role="button" tabindex="0" onclick="window._xrayJump(\'' + esc(x.id) + '\')">' +
        '<span class="xr-dot" style="background:' + sectorColor(node.cat) + '"></span>' +
        '<span class="vn">' + esc(node.label) + '</span>' +
        '<span class="vbar"><i style="width:' + Math.round(x.v) + '%"></i></span>' +
        '<span class="vp xr-mono">' + Math.round(x.v) + '%</span></div>';
    }).join('');
    var winners = computeWinners(id, impacts);
    var winHTML = winners.length ? '<div class="xr-h win" style="margin:14px 0 6px">' + L('Quién gana ↑', 'Who wins ↑') + '</div>' +
      winners.map(function (w) {
        var node = window.NODE_BY_ID[w.id];
        return '<div class="xr-victim win" role="button" tabindex="0" onclick="window._xrayJump(\'' + esc(w.id) + '\')">' +
          '<span class="xr-dot" style="background:' + sectorColor(node.cat) + '"></span>' +
          '<span class="vn">' + esc(node.label) + '</span>' +
          '<span class="vbar"><i style="width:' + w.up * 2 + '%"></i></span>' +
          '<span class="vp xr-mono">+' + w.up + '%</span></div>';
      }).join('') : '';
    var el = root.querySelector('#xr-impact');
    if (!el) return;
    el.innerHTML =
      '<div class="impact-grid" style="margin-bottom:11px">' +
        '<div class="icell hot"><b>' + arr.length + '</b><span>' + L('empresas', 'companies') + '</span></div>' +
        '<div class="icell hot"><b>$' + (totalCap >= 1000 ? (totalCap / 1000).toFixed(1) + 'T' : Math.round(totalCap) + 'B') + '</b><span>' + L('cap expuesta', 'exposed cap') + '</span></div>' +
        '<div class="icell hot"><b>' + (portHit > 0 ? '−' + Math.round(portHit / Math.max(1, Object.keys(pos).length)) + '%' : '—') + '</b><span>' + L('tu cartera', 'your portfolio') + '</span></div>' +
      '</div>' +
      '<div class="xr-h bad" style="margin:2px 0 6px">' + L('Quién sufre ↓', 'Who suffers ↓') + '</div>' + top + winHTML +
      (note ? '<div class="xr-lin" style="margin-top:8px">' + note + '</div>' : '');
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

  // impacto INSTANTÁNEO con el motor de estados client-side (KhipuState, ~7ms)
  function impactViaState(id) {
    if (!window.KhipuState || !window.KhipuState.simulate) return null;
    try {
      var shock = {}; shock[id] = { salud: 0 };
      var r = window.KhipuState.simulate(shock, [], 8, 0.6, false, { direction: 'down', kind: 'collapse' });
      if (!r || !r.impact) return null;
      var obj = {}; obj[id] = 100;
      r.impact.forEach(function (v, k) { if (k !== id && v > 0) obj[k] = v; });
      return obj;
    } catch (e) { return null; }
  }

  function _usdB(v) { return v >= 1000 ? '$' + (v / 1000).toFixed(1) + 'T' : '$' + Math.round(v) + 'B'; }
  var CONC = { alta: ['alta', 'high', C_BAD], media: ['media', 'medium', C_WARN], baja: ['baja', 'low', C_GOOD] };
  function loadStructure(root, id) {
    var el = root.querySelector('#xr-struct');
    if (!el) return;
    fetch('/api/tensor/node/' + encodeURIComponent(id)).then(function (r) { return r.ok ? r.json() : null; }).then(function (d) {
      if (!d) { el.innerHTML = '<div class="xr-loading">' + L('Sin datos estructurales para esta empresa.', 'No structural data for this company.') + '</div>'; return; }
      var sc = d.supplier_concentration || {}, dn = d.downstream || {}, c0 = (d.supplier_countries || [])[0];
      var cc = CONC[sc.level] || null, top = (sc.top || [])[0];
      var tiles =
        '<div class="impact-grid" style="margin-bottom:10px">' +
        '<div class="icell"><b' + (cc ? ' style="color:' + cc[2] + '"' : '') + '>' + (cc ? L(cc[0], cc[1]) : '—') + '</b><span>' +
          L('Concentración de proveedores', 'Supplier concentration') + (sc.n_suppliers ? ' · ' + sc.n_suppliers : '') + '</span></div>' +
        '<div class="icell"><b>' + (c0 ? esc(c0.country) + ' ' + Math.round(c0.share_pct) + '%' : '—') + '</b><span>' +
          L('País principal de sus proveedores', 'Main supplier country') + '</span></div>' +
        '<div class="icell"><b>' + (dn.cap_at_risk_usd_b > 0 ? _usdB(dn.cap_at_risk_usd_b) : '—') + '</b><span>' +
          L('Valor arrastrado si cae', 'Value dragged if it fails') + (dn.systemic_rank ? ' · #' + dn.systemic_rank : '') + '</span></div>' +
        '</div>';
      var lines = [];
      if (top) lines.push(L('Mayor dependencia: ', 'Biggest dependency: ') + '<b class="xr-strong">' + esc(top.label) + '</b> (' + top.share_pct + '% ' + L('del peso de sus vínculos con proveedores', 'of the weight of its supplier links') + ')');
      var ups = (d.upstream_risk_sources || []).slice(0, 3);
      if (ups.length) lines.push(L('Su riesgo viene de: ', 'Its risk comes from: ') + ups.map(function (u) {
        return '<a href="#" class="xr-tj" data-id="' + esc(u.id) + '">' + esc(u.label) + '</a> ' + u.exposure_pct + '%' + (u.direct ? '' : L(' (indirecto)', ' (indirect)'));
      }).join(' · '));
      var ps = (d.peers || []).slice(0, 4);
      if (ps.length) lines.push(L('Comparables: ', 'Peers: ') + ps.map(function (p) {
        return '<a href="#" class="xr-tj" data-id="' + esc(p.id) + '">' + esc(p.label) + '</a>';
      }).join(' · '));
      var note = dn.cap_coverage_pct != null && dn.cap_coverage_pct < 60
        ? '<div class="xr-lin" style="margin-top:6px">' + L('ⓘ capitalización conocida de ', 'ⓘ known market cap for ') + dn.cap_coverage_pct + '% ' +
          L('de las empresas arrastradas: el valor real es mayor.', 'of the companies dragged: the real value is higher.') + '</div>' : '';
      el.innerHTML = tiles + lines.map(function (x) { return '<div class="xr-lin" style="margin-top:4px">' + x + '</div>'; }).join('') + note;
      el.querySelectorAll('.xr-tj').forEach(function (a) {
        a.addEventListener('click', function (e) { e.preventDefault(); if (window._xrayJump) window._xrayJump(a.getAttribute('data-id')); });
      });
    }).catch(function () { el.innerHTML = '<div class="xr-loading">' + L('Sin datos estructurales ahora.', 'No structural data right now.') + '</div>'; });
  }

  function loadImpact(root, id, n) {
    // 1) INSTANTÁNEO: motor de estados en el navegador (adiós "tarda mucho")
    var instant = impactViaState(id);
    var shown = !!(instant && Object.keys(instant).length > 1);
    if (shown) renderVictims(root, id, n, instant, L('ⓘ motor de estados en vivo (instantáneo)', 'ⓘ live state engine (instant)'));
    // Cierre SIEMPRE con un mensaje: antes, si nadie caía detrás (p.ej. la
    // Reserva Federal, 0 vínculos de suministro) o el servidor respondía sin
    // impactos, la sección se quedaba en "Calculando propagación…" para siempre.
    function finish() {
      if (shown) return;
      var el = root.querySelector('#xr-impact');
      if (typeof window.computeDownstream === 'function') {
        try {
          var affected = window.computeDownstream(id);
          var list = affected instanceof Set ? Array.from(affected) : (affected || []);
          if (list.length) {
            var impacts = {}; impacts[id] = 100;
            list.forEach(function (aid) { impacts[aid] = 55; });
            renderVictims(root, id, n, impacts, L('ⓘ estimación local', 'ⓘ local estimate'));
            return;
          }
        } catch (e) {}
      }
      if (el) el.innerHTML = '<div class="xr-loading">' + L(
        'Su caída no arrastra a ninguna empresa por la cadena de suministro. Si es un actor macro (banco central, regulador), su efecto se simula con los factores sistémicos (FACTOR LIST).',
        'Its failure does not drag any company down the supply chain. If it is a macro actor (central bank, regulator), its effect is simulated through systemic factors (FACTOR LIST).') + '</div>';
    }
    // 2) refinar en segundo plano con el motor de matrices del servidor (si está)
    fetch('/api/matrix/impact', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ shock: [id] }),
    }).then(function (r) { return r.ok ? r.json() : null; }).then(function (d) {
      if (d && d.impacts && Object.keys(d.impacts).length > 1) {
        shown = true;
        renderVictims(root, id, n, d.impacts, L('ⓘ motor de matrices (servidor · ponderado)', 'ⓘ matrix engine (server · weighted)'));
      } else finish();
    }).catch(finish);
  }

  // filas clicables (hilos, quién sufre/gana) con role="button": Enter/Espacio = clic (teclado).
  // Delegado UNA vez por root (el cajón #xray se re-pinta con otra empresa sin re-crearse).
  function wireKeys(root) {
    if (!root || root._xrKeys || !root.addEventListener) return;
    root._xrKeys = true;
    root.addEventListener('keydown', function (e) {
      if (e.key !== 'Enter' && e.key !== ' ') return;
      var t = e.target;
      if (!t || !t.getAttribute || t.getAttribute('role') !== 'button' || typeof t.click !== 'function') return;
      e.preventDefault(); t.click();
    });
  }

  // conecta precio + impacto a un root ya renderizado con buildXRayHTML
  function wire(root, id) {
    var n = window.NODE_BY_ID ? window.NODE_BY_ID[id] : null;
    if (!n) return;
    wireKeys(root);
    loadPrice(root, n);
    startPriceTimer(root, n);   // precio del encabezado: cada 60 s mientras esté abierto
    loadImpact(root, id, n);
    loadStructure(root, id);
    // Empleados / Mkt Cap / Ingresos EN VIVO (KhipuLive) con title "en vivo · fuente · hora"
    if (window.fillLiveMeta) window.fillLiveMeta(root, n);
    else if (window.fillLiveMcap) window.fillLiveMcap(root.querySelector('.xr-mcap'), n);
  }

  // ── cajón lateral (abre desde el mapa) ──
  function render(id) {
    var n = window.NODE_BY_ID ? window.NODE_BY_ID[id] : null;
    if (!n) return;
    // si la Cabina de Khipu está abierta, el X-Ray va al escenario grande
    if (window.BixbyCockpit && window.BixbyCockpit.isOpen && window.BixbyCockpit.isOpen()) {
      window.BixbyCockpit.stage('xray', id);
      return;
    }
    ensureStyles();
    var ov = document.getElementById('xray-ov');
    if (!ov) {
      ov = document.createElement('div');
      ov.id = 'xray-ov';
      ov.className = 'kos-themed';   // tokens --os-* de Khipus OS (claro/oscuro) fuera de #bcp-ov
      ov.innerHTML = '<div id="xray" class="xray-scope" role="dialog" aria-modal="true" aria-label="X-Ray"></div>';
      ov.addEventListener('click', function (e) { if (e.target === ov) close(); });
      document.body.appendChild(ov);
    }
    var box = document.getElementById('xray');
    box.innerHTML = buildXRayHTML(id, { full: false });
    ov.classList.add('show');
    wire(box, id);
  }

  function close() {
    var ov = document.getElementById('xray-ov');
    if (ov) ov.classList.remove('show');
    stopPriceTimer(document.getElementById('xray'));
  }

  window._xrayJump = function (id) {
    if (window.BixbyCockpit && window.BixbyCockpit.isOpen && window.BixbyCockpit.isOpen()) { window.BixbyCockpit.stage('xray', id); return; }
    close();
    if (typeof window.switchTab === 'function') window.switchTab('map');
    setTimeout(function () { if (typeof window.jumpTo === 'function') window.jumpTo(id); }, 90);
  };
  window._xrayClose = function () {
    if (window.BixbyCockpit && window.BixbyCockpit.isOpen && window.BixbyCockpit.isOpen()) { window.BixbyCockpit.stage('empty'); return; }
    close();
  };
  window._xrayShock = function (id) {
    if (window.BixbyCockpit && window.BixbyCockpit.isOpen && window.BixbyCockpit.isOpen()) { window.BixbyCockpit.stage('sim', { id: id, kind: 'collapse' }); return; }
    window._xrayJump(id); setTimeout(function () { if (typeof window.activateStress === 'function') window.activateStress(id); }, 220);
  };
  window._xrayTKG = function (id) { close(); if (typeof window.switchTab === 'function') window.switchTab('tkg'); setTimeout(function () { if (window.__tkgOpenObj) window.__tkgOpenObj(id); }, 200); };
  window._xrayCompare = function (id) {
    if (window.BixbyCockpit && window.BixbyCockpit.isOpen && window.BixbyCockpit.isOpen()) { window.BixbyCockpit.stage('compare', { a: id }); return; }
    close(); if (window.openCompare) window.openCompare(id);
  };
  window.openXRay = function (id) { render(id); };

  // API para la Cabina de Khipu
  window.buildXRayHTML = buildXRayHTML;
  window.wireXRay = wire;
  window.xrayEnsureStyles = ensureStyles;
  window.xrayImpactViaState = impactViaState;
  window.xrayComputeWinners = computeWinners;

  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });
})();
