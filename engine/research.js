/* ============================================================================
   engine/research.js — PHASE 2 · INVESTIGACIÓN IA (Agent Research Swarm)

   window.KhipuResearch.open(entityId)            overlay completo
   window.KhipuResearch.renderInline(el, id)      bloque compacto (ficha del mapa)
   window.KhipuResearch.run(entityId, depth)      lanza un ResearchJob

   Muestra SOLO lo que existe en el servidor (/api/research/*):
   · conclusiones (claims) por perspectiva: horizonte, confianza calculada
     (con su "?"), postura, agente, hora, # evidencia a favor / en contra
   · "¿Por qué?": resumen de razonamiento → evidencia → fuentes → nodos
     afectados → contra-evidencia → contradicciones → ejecución que la produjo
   · síntesis por horizonte (sin comprar/vender/mantener)
   · LIVE AGENT ACTIVITY: ejecuciones reales (agent_runs); nunca actividad fingida
   Bilingüe (L(es,en)). Sin DATABASE_URL el servidor responde 503 y se dice.
   KHIPUS OS (2026-10-10): #rs-ov lleva .kos-themed → tokens --os-* de engine/cockpit.js
   (claro = body sin .dark, oscuro = body.dark), siempre con respaldo oscuro en var().
   Los AGENTES se dibujan con sus mascotas (engine/mascot.js: Analista, Radar, Cadena,
   Técnico, Comité); sin el módulo, el emoji de antes.
   ============================================================================ */
(function () {
  'use strict';

  function isEn() { var l = window.LANG; if (!l) { try { l = localStorage.getItem('eco_lang'); } catch (e) { l = null; } } return l === 'en'; }
  function L(es, en) { return isEn() ? en : es; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function base() { return window.BASE || ''; }
  function safeUrl(u) { return (typeof u === 'string' && /^https?:\/\//i.test(u)) ? u : null; }
  function nodeLabel(id) { var n = (window.NODE_BY_ID || {})[id]; return (n && n.label) || id; }
  function clock(iso) { var d = new Date(iso); return isNaN(d) ? '' : d.toLocaleString(isEn() ? 'en' : 'es', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }); }
  function chip(k) { return window.explainChip ? window.explainChip(k) : ''; }

  var AG = {
    fundamental: ['📊', 'Fundamental', 'Fundamental'], technical: ['📈', 'Técnico', 'Technical'],
    news: ['📰', 'Noticias', 'News'], supply_chain: ['🔗', 'Cadena de suministro', 'Supply chain'],
    geopolitical: ['🗺️', 'Geopolítica', 'Geopolitics'], macro: ['🌐', 'Macro', 'Macro'],
    crypto: ['₿', 'Cripto', 'Crypto'], risk_observation: ['⚠️', 'Riesgos', 'Risks'],
    committee: ['🏛', 'Comité', 'Committee'],
  };
  var HZ = {
    INTRADAY: ['Intradía', 'Intraday'], SHORT_TERM: ['Corto plazo', 'Short term'],
    MEDIUM_TERM: ['Mediano plazo', 'Medium term'], LONG_TERM: ['Largo plazo', 'Long term'],
    STRUCTURAL: ['Estructural', 'Structural'],
  };
  // Colores SEMÁNTICOS de Khipus OS: STANCE[x][0] es un RELLENO (puntos); los textos usan C.* (contraste AA)
  var STANCE = { positive: ['var(--os-good,#2fbf5b)', 'a favor', 'positive'], negative: ['var(--os-bad,#f06565)', 'en contra', 'negative'],
    neutral: ['var(--os-ink-3,#6E7080)', 'neutral', 'neutral'], mixed: ['var(--os-warn,#F2C46D)', 'mixta', 'mixed'] };
  var C = { good: 'var(--os-good-ink,#2fbf5b)', bad: 'var(--os-bad-ink,#F47C7C)', warn: 'var(--os-warn-ink,#F2C46D)' };
  var ST = { running: ['investigando…', 'investigating…'], done: ['listo', 'done'], failed: ['falló', 'failed'],
    skipped: ['omitido', 'skipped'], queued: ['en cola', 'queued'], partial: ['parcial', 'partial'],
    deferred: ['en espera (presupuesto)', 'waiting (budget)'] };
  // R4 (misión de reparación): etiqueta corta del analista para la cobertura
  var AGL = { fundamental: ['Fundamental', 'Fundamental'], news: ['Noticias', 'News'], technical: ['Técnico', 'Technical'],
    supply_chain: ['Cadena de suministro', 'Supply chain'], geopolitical: ['Geopolítico', 'Geopolitical'], macro: ['Macro', 'Macro'],
    crypto: ['Cripto', 'Crypto'], risk_observation: ['Riesgos', 'Risk'] };
  function agl(t) { var a = AGL[t] || [t, t]; return L(a[0], a[1]); }
  // Franja de cobertura: qué analistas respondieron y cuáles faltan (nunca se esconde un parcial)
  function coverageHtml(cov, withButton) {
    if (!cov) return '';
    if (cov.complete) {
      return cov.note_es ? '<div class="rs-note" style="font-size:12px;margin-bottom:8px">ℹ️ ' + esc(isEn() ? (cov.note_en || cov.note_es) : cov.note_es) + '</div>' : '';
    }
    return '<div class="rs-msg bad">⚠️ ' +
      esc(isEn() ? (cov.note_en || cov.note_es || '') : (cov.note_es || '')) +
      (withButton ? ' <button type="button" class="rs-btn warn" id="rs-complete"' + (S.job ? ' disabled' : '') + '>↻ ' +
        esc(L('Completar lo que falta', 'Complete the missing part')) + ' (' + esc((cov.missing || []).map(agl).join(', ')) + ')</button>' : '') + '</div>';
  }
  var TOPIC = { revenue_growth: ['crecimiento de ingresos', 'revenue growth'], margins: ['márgenes', 'margins'],
    profitability: ['rentabilidad', 'profitability'], cash_flow: ['flujo de caja', 'cash flow'], balance_sheet: ['balance', 'balance sheet'],
    valuation: ['valuación', 'valuation'], demand: ['demanda', 'demand'], competition: ['competencia', 'competition'],
    supply_chain: ['cadena de suministro', 'supply chain'], regulation: ['regulación', 'regulation'], geopolitics: ['geopolítica', 'geopolitics'],
    macro: ['macro', 'macro'], technology: ['tecnología', 'technology'], management: ['gestión', 'management'],
    capital_allocation: ['asignación de capital', 'capital allocation'], momentum: ['impulso del precio', 'price momentum'],
    volatility: ['volatilidad', 'volatility'], sentiment: ['sentimiento', 'sentiment'], other: ['otro', 'other'] };
  var COMP = { source_quality: ['Calidad de las fuentes', 'Source quality'], independence: ['Fuentes independientes', 'Independent sources'],
    recency: ['Qué tan recientes', 'Recency'], agreement: ['Poca evidencia en contra', 'Little counter-evidence'],
    agent_certainty: ['Seguridad del agente', 'Agent certainty'], completeness: ['Datos completos', 'Data completeness'] };
  function tp(t) { var x = TOPIC[t] || [t, t]; return L(x[0], x[1]); }
  function conflictText(x) {
    var a = x.a_info, b = x.b_info;
    if (!a || !b) return x.reason || '';
    var st = function (v) { var q = STANCE[v] || [0, v, v]; return L(q[1], q[2]); };
    var tEs = a.topic === b.topic ? tp(a.topic) : tp(a.topic) + ' / ' + tp(b.topic);
    // choque detectado por la revisión con IA: mostrar su razón en el idioma
    var rs = String(x.reason || '');
    if (rs.indexOf('(revisión IA)') === 0) {
      var parts = rs.replace('(revisión IA) ', '').split(' | EN: ');
      var why = isEn() ? (parts[1] || parts[0]) : parts[0];
      return ag(a.agent_type) + ' ↔ ' + ag(b.agent_type) + ' · ' + tEs + ' (' + hz(a.horizon) + '): ' + why +
        ' ' + L('(detectado por revisión con IA; no se decide quién tiene razón)', '(detected by AI review; who is right is not decided)');
    }
    return L(ag(a.agent_type) + ' ve «' + st(a.stance) + '» y ' + ag(b.agent_type) + ' ve «' + st(b.stance) + '» sobre ' + tEs + ' en el mismo plazo (' + hz(a.horizon) + '). No se decide aquí quién tiene razón.',
      ag(a.agent_type) + ' sees “' + st(a.stance) + '” and ' + ag(b.agent_type) + ' sees “' + st(b.stance) + '” on ' + tEs + ' over the same horizon (' + hz(a.horizon) + '). Who is right is not decided here.');
  }
  // ag(t) = nombre del agente en TEXTO (sin emoji: va dentro de frases y errores);
  // agH(t) = el mismo nombre con su MASCOTA delante (HTML, para pestañas, tarjetas y actividad)
  function ag(t) { var a = AG[t] || ['🤖', t, t]; return L(a[1], a[2]); }
  function mascotId(t) {
    var M = window.KhipuMascot, id = null;
    try { id = (M && M.of) ? M.of(t) : null; } catch (e) { id = null; }
    return id;
  }
  function mascot(t, size) {
    var M = window.KhipuMascot, id = mascotId(t);
    if (id && M && M.svg) { try { return M.svg(id, size || 18); } catch (e) {} }
    var a = AG[t] || ['🤖'];
    return '<span class="rs-mfb" aria-hidden="true">' + a[0] + '</span>';
  }
  // el equipo de investigación (encabezado y "actividad de agentes")
  var TEAM = ['analista', 'radar', 'cadena', 'tecnico'];
  function agH(t, size) { return '<span class="rs-ag">' + mascot(t, size) + '<span>' + esc(ag(t)) + '</span></span>'; }
  function stackH(ids, size, emo) {
    var M = window.KhipuMascot;
    if (M && M.stack) { try { return M.stack(ids, size || 22); } catch (e) {} }
    return '<span class="rs-mfb" aria-hidden="true">' + (emo || '🔬') + '</span>';
  }
  function hz(h) { var x = HZ[h] || [h, h]; return L(x[0], x[1]); }

  function ensureStyles() {
    if (document.getElementById('rs-styles')) return;
    // Look de Khipus OS (como engine/committee.js): tarjetas sin borde, píldoras, control segmentado,
    // foco visible de 2 px, pantalla completa en el teléfono. Solo tokens --os-* (con respaldo oscuro).
    var F = "var(--os-font,'Nunito',system-ui,-apple-system,'Segoe UI',sans-serif)";
    var css = '' +
      '#rs-ov{position:fixed;inset:0;z-index:7700;display:none;align-items:center;justify-content:center;background:var(--kos-scrim,rgba(0,0,0,.5));' +
        '-webkit-backdrop-filter:blur(10px) saturate(1.1);backdrop-filter:blur(10px) saturate(1.1);font-family:' + F + '}' +
      '#rs-ov.show{display:flex}' +
      '#rs{width:min(1100px,96vw);max-height:92vh;overflow-y:auto;overflow-x:hidden;overscroll-behavior:contain;box-sizing:border-box;border-radius:24px;' +
        'background:var(--os-bg,#0E0F14);color:var(--os-ink,#F2F2F5);box-shadow:var(--kos-shadow-lg,0 2px 8px rgba(0,0,0,.45),0 22px 56px rgba(0,0,0,.55));' +
        // --rs-link: acento como TEXTO, mezclado con la tinta (≥5:1 en todas las superficies, claro y oscuro)
        '--rs-link:var(--os-accent,#4C8DF6);--rs-link:color-mix(in srgb,var(--os-accent,#4C8DF6) 82%,var(--os-ink,#F2F2F5));' +
        'padding:22px 26px 26px;font-family:' + F + ';font-size:14px;line-height:1.5;-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;' +
        'animation:rsPop .22s ease;scrollbar-width:thin;scrollbar-color:var(--os-surface-3,#2A2B36) transparent}' +
      '@keyframes rsPop{from{opacity:0;transform:translateY(6px) scale(.985)}to{opacity:1;transform:none}}' +
      '#rs *{box-sizing:border-box}' +
      '#rs button,#rs select{font-family:inherit}' +
      // encabezado: mascotas + título · controles · cerrar redondo
      '#rs .rs-hd{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:6px}' +
      '#rs .rs-name{display:flex;align-items:center;gap:10px;flex:1 1 260px;min-width:0;font-size:20px;font-weight:800;letter-spacing:-.015em;line-height:1.25;overflow-wrap:anywhere}' +
      '#rs .rs-name .rs-ent{color:var(--os-ink-2,#A6A8B5);font-weight:700}' +
      '#rs .rs-ctl{display:flex;align-items:center;gap:8px;flex-wrap:wrap}' +
      '#rs .rs-x{margin-left:auto;width:40px;height:40px;padding:0;border:0;border-radius:999px;cursor:pointer;background:transparent;color:var(--os-ink-2,#A6A8B5);' +
        'font-size:15px;font-weight:600;flex:0 0 auto;display:inline-flex;align-items:center;justify-content:center;transition:background-color .15s,color .15s}' +
      '#rs .rs-x:hover{background:var(--os-surface-2,#1F2029);color:var(--os-ink,#F2F2F5)}' +
      '#rs .rs-sub{font-size:13px;color:var(--os-ink-2,#A6A8B5);margin:0 0 16px;line-height:1.55;max-width:860px}' +
      // botones = píldoras (principal según el tema; .ghost suave; .warn ámbar suave)
      '#rs .rs-btn{appearance:none;-webkit-appearance:none;border:0;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:7px;' +
        'height:40px;padding:0 18px;border-radius:999px;font-size:13.5px;font-weight:700;white-space:nowrap;' +
        'background:var(--os-btn,#F2F2F5);color:var(--os-btn-ink,#111216);transition:opacity .15s,background-color .15s,transform .1s}' +
      '#rs .rs-btn:hover{opacity:.88}#rs .rs-btn:active{transform:scale(.98)}' +
      '#rs .rs-btn[disabled]{opacity:.45;cursor:default;transform:none}' +
      '#rs .rs-btn.ghost{background:var(--os-surface,#17181F);color:var(--os-ink,#F2F2F5);font-weight:600;box-shadow:var(--os-shadow,0 1px 2px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.35))}' +
      '#rs .rs-btn.ghost:hover{background:var(--os-surface-3,#2A2B36);opacity:1}' +
      // dentro del aviso ámbar: píldora de superficie con texto ámbar oscuro (6.8:1; sobre el ámbar teñido daba 4.3:1)
      '#rs .rs-btn.warn{height:34px;padding:0 14px;font-size:12.5px;color:' + C.warn + ';background:var(--os-surface,#17181F);box-shadow:var(--os-shadow,0 1px 2px rgba(0,0,0,.4))}' +
      '#rs .rs-btn.warn:hover{opacity:1;background:var(--os-surface-2,#1F2029)}' +
      '#rs select{height:40px;border:0;border-radius:var(--os-r-sm,12px);padding:0 10px 0 14px;font-size:13.5px;color:var(--os-ink,#F2F2F5);cursor:pointer;' +
        'background:var(--os-surface,#17181F);box-shadow:var(--os-shadow,0 1px 2px rgba(0,0,0,.4));outline:none}' +
      '#rs select:focus{box-shadow:0 0 0 3px var(--kos-accent-soft,rgba(76,141,246,.16))}' +
      '#rs .rs-btn:focus-visible,#rs .rs-x:focus-visible,#rs .rs-tab:focus-visible,#rs .rs-why:focus-visible,#rs .rs-node:focus-visible,#rs select:focus-visible,#rs a:focus-visible{' +
        'outline:2px solid var(--os-accent,#4C8DF6);outline-offset:2px}' +
      '#rs .rs-grid{display:grid;grid-template-columns:minmax(0,2fr) minmax(0,1fr);gap:14px;align-items:start}' +
      // tarjetas de Khipus OS: superficie, radio 18, sombra suave, sin bordes
      '#rs .rs-cell{background:var(--os-surface,#17181F);border-radius:var(--os-r,18px);box-shadow:var(--os-shadow,0 1px 2px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.35));' +
        'padding:16px 18px;min-width:0}' +
      '#rs .rs-t{display:flex;align-items:center;gap:7px;flex-wrap:wrap;font-size:13px;font-weight:700;letter-spacing:-.005em;color:var(--os-ink,#F2F2F5);margin-bottom:10px}' +
      // mensajes (aviso ámbar / listo verde): píldora teñida, texto con contraste AA
      '#rs .rs-msg{border-radius:var(--os-r-sm,12px);padding:11px 14px;font-size:13px;font-weight:600;line-height:1.5;margin-bottom:12px;overflow-wrap:anywhere;' +
        'color:' + C.good + ';background:var(--os-surface-2,#1F2029);background:color-mix(in srgb,var(--os-good,#2fbf5b) 12%,transparent)}' +
      '#rs .rs-msg.bad{color:' + C.warn + ';background:var(--os-surface-2,#1F2029);background:color-mix(in srgb,var(--os-warn,#F2C46D) 14%,transparent)}' +
      '#rs .rs-msg .rs-btn.warn{margin:6px 0 0 8px;vertical-align:middle;max-width:100%;height:auto;min-height:34px;padding:7px 14px;white-space:normal;text-align:left;line-height:1.35}' +
      // pestañas por agente = control segmentado (con mascota)
      '#rs .rs-tabs{display:flex;gap:2px;flex-wrap:wrap;width:fit-content;max-width:100%;padding:3px;border-radius:20px;background:var(--os-surface-2,#1F2029);margin-bottom:12px}' +
      '#rs .rs-tab{appearance:none;-webkit-appearance:none;display:inline-flex;align-items:center;gap:6px;height:34px;padding:0 12px 0 8px;border:0;border-radius:999px;' +
        'background:none;color:var(--os-ink-2,#A6A8B5);font-size:13px;font-weight:600;white-space:nowrap;cursor:pointer;transition:background-color .15s,color .15s,box-shadow .15s}' +
      '#rs .rs-tab:hover{color:var(--os-ink,#F2F2F5)}' +
      '#rs .rs-tab.on{background:var(--os-surface,#17181F);color:var(--os-ink,#F2F2F5);box-shadow:var(--os-shadow,0 1px 2px rgba(0,0,0,.4))}' +
      '#rs .rs-tab .rs-n{font-variant-numeric:tabular-nums;color:var(--os-ink-2,#A6A8B5)}' +
      '#rs .rs-trb{font-size:11px;font-weight:600;color:var(--os-ink-2,#A6A8B5)}' +
      '#rs .rs-ag{display:inline-flex;align-items:center;gap:6px;min-width:0}' +
      '#rs .rs-mfb{display:inline-flex;align-items:center;justify-content:center;flex:none;width:18px;height:18px;font-size:13px;line-height:1}' +
      // conclusiones: tarjeta interior suave
      '#rs .rs-claim{border-radius:var(--os-r-sm,12px);padding:12px 14px;margin-bottom:8px;background:var(--os-surface-2,#1F2029)}' +
      '#rs>.rs-claim{background:var(--os-surface,#17181F);box-shadow:var(--os-shadow,0 1px 2px rgba(0,0,0,.4));border-radius:var(--os-r,18px);padding:16px 18px;margin-bottom:14px}' +
      '#rs .rs-st{font-size:14px;line-height:1.55;color:var(--os-ink,#F2F2F5);overflow-wrap:anywhere}' +
      '#rs .rs-dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:8px;vertical-align:1px}' +
      '#rs .rs-meta{display:flex;gap:6px 10px;flex-wrap:wrap;align-items:center;font-size:12px;color:var(--os-ink-2,#A6A8B5);margin-top:8px}' +
      '#rs .rs-badge{font-size:11.5px;font-weight:600;padding:3px 10px;border-radius:999px;background:var(--os-surface,#17181F);color:var(--os-ink-2,#A6A8B5)}' +
      '#rs>.rs-claim .rs-badge{background:var(--os-surface-2,#1F2029)}' +
      '#rs .rs-bar{display:inline-block;width:70px;height:6px;border-radius:999px;background:var(--os-surface-3,#2A2B36);overflow:hidden;vertical-align:middle}' +
      '#rs .rs-bar i{display:block;height:100%;border-radius:999px;background:var(--os-accent,#4C8DF6)}' +
      '#rs .rs-pct{font-variant-numeric:tabular-nums;font-weight:700;color:var(--os-ink,#F2F2F5)}' +
      '#rs .rs-why{appearance:none;-webkit-appearance:none;font-size:12.5px;font-weight:700;color:var(--rs-link);cursor:pointer;background:none;border:none;padding:2px 4px;border-radius:6px;margin-left:auto}' +
      '#rs .rs-why:hover{text-decoration:underline}' +
      '#rs .rs-note .rs-why{margin-left:0}' +
      '#rs .rs-act{font-size:12.5px;padding:9px 0;border-bottom:1px solid var(--os-line,rgba(255,255,255,.07));line-height:1.5}' +
      '#rs .rs-act:last-child{border-bottom:0}' +
      '#rs .rs-act .rs-ah{display:flex;align-items:flex-start;gap:7px;color:var(--os-ink,#F2F2F5)}#rs .rs-act .rs-ah>span:last-child{min-width:0;flex:1 1 auto}' +
      '#rs .rs-act .rs-as{color:var(--os-ink-2,#A6A8B5)}' +
      '#rs .rs-act .rs-hint{color:' + C.warn + ';font-weight:700}' +
      '#rs .rs-act .rs-err{color:' + C.warn + ';overflow-wrap:anywhere}' +
      '#rs .rs-note{font-size:13px;color:var(--os-ink-2,#A6A8B5);line-height:1.55;overflow-wrap:anywhere}' +
      '#rs .rs-note ul,#rs ul.rs-note{margin:4px 0 8px 18px;padding:0}#rs .rs-note li{margin-bottom:3px}' +
      '#rs .rs-mut{color:var(--os-ink-2,#A6A8B5)}' +
      '#rs .rs-good{color:' + C.good + '}#rs .rs-bad{color:' + C.bad + '}#rs .rs-warn{color:' + C.warn + '}' +
      '#rs .rs-hz{font-weight:700;font-size:13px;margin-bottom:4px;color:var(--os-ink,#F2F2F5)}' +
      '#rs a{color:var(--rs-link);text-decoration:none;font-weight:600}#rs a:hover{text-decoration:underline}' +
      // evidencia: barra de color a la izquierda (verde a favor, rojo en contra) sobre tarjeta suave
      '#rs .rs-ev{border-radius:6px var(--os-r-sm,12px) var(--os-r-sm,12px) 6px;padding:9px 12px;margin:8px 0;background:var(--os-surface-2,#1F2029);' +
        'box-shadow:inset 3px 0 0 var(--os-good,#2fbf5b);font-size:13px;line-height:1.5;overflow-wrap:anywhere}' +
      '#rs .rs-ev.cnt{box-shadow:inset 3px 0 0 var(--os-bad,#f06565)}' +
      '#rs .rs-ev .rs-ex{color:var(--os-ink-2,#A6A8B5);margin-top:2px}' +
      '#rs .rs-ev .rs-src{color:var(--os-ink-2,#A6A8B5);font-size:11.5px;margin-top:3px}' +
      '#rs .rs-node{appearance:none;-webkit-appearance:none;display:inline-flex;align-items:center;font-size:12.5px;font-weight:600;padding:5px 12px;border:0;border-radius:999px;' +
        'background:var(--os-surface-2,#1F2029);color:var(--os-ink,#F2F2F5);margin:4px 5px 0 0;cursor:pointer;transition:background-color .15s}' +
      '#rs .rs-node:hover{background:var(--os-surface-3,#2A2B36)}' +
      '#rs .rs-kv{display:flex;justify-content:space-between;align-items:center;gap:12px;font-size:13px;padding:7px 0;border-bottom:1px solid var(--os-line,rgba(255,255,255,.07))}' +
      '#rs .rs-kv:last-child{border-bottom:0}' +
      '#rs .rs-kv span:first-child{color:var(--os-ink-2,#A6A8B5)}' +
      '#rs .rs-kv span:last-child{text-align:right;font-variant-numeric:tabular-nums;font-weight:600;color:var(--os-ink,#F2F2F5);overflow-wrap:anywhere;min-width:0}' +
      // puente: el "?" de engine/explain.js llega con colores fijos de la piel vieja
      '#rs span[onclick*="explainMetric"]{color:var(--rs-link)!important;border-color:var(--os-line,rgba(255,255,255,.07))!important;background:var(--os-surface,#17181F)}' +
      '@media(max-width:760px){#rs-ov{align-items:stretch}' +
        '#rs{width:100%;max-height:none;height:100%;border-radius:0;padding:16px 14px 28px}' +
        '#rs .rs-grid{grid-template-columns:minmax(0,1fr)}' +
        '#rs .rs-name{order:1;flex:1 1 0;font-size:18px}#rs .rs-x{order:2}#rs .rs-ctl{order:3;flex-basis:100%}' +
        '#rs .rs-ctl select{flex:1 1 auto}#rs .rs-tabs{width:auto}#rs .rs-tab{padding:0 10px 0 6px}#rs .rs-msg .rs-btn.warn{display:flex;margin:8px 0 0}}' +
      '@media(prefers-reduced-motion:reduce){#rs{animation:none}#rs .rs-btn,#rs .rs-tab,#rs .rs-node,#rs .rs-x{transition:none}#rs .rs-btn:active{transform:none}}';
    var st = document.createElement('style'); st.id = 'rs-styles'; st.textContent = css;
    document.head.appendChild(st);
  }

  var S = { entity: null, tab: null, data: null, poll: null, job: null, tr: null, cal: null };

  // ── PHASE 3: historial real por agente + confianza calibrada ───────────────
  // /api/committee/* (research/outcomes.py). Si no existe (sin base, módulo
  // ausente) no se muestra nada: la investigación funciona igual.
  function loadLearning() {
    getJSON('/api/committee/track-record').then(function (d) {
      if (d._status !== 200) return;
      var by = {}; (d.agents || []).forEach(function (a) { by[a.agent_type] = a; });
      S.tr = { by: by, min_n: d.min_n || 5 }; if (S.data && S.view === 'main') render();
    }).catch(function () {});
    getJSON('/api/committee/calibration').then(function (d) {
      if (d._status !== 200) return;
      S.cal = { table: d.table || {}, k: d.k == null ? 10 : d.k, min_n: d.min_n || 5 }; if (S.data && S.view === 'main') render();
    }).catch(function () {});
  }
  // misma fórmula que research/outcomes.calibration_detail:
  // (aciertos_tramo + k·cruda) / (n_tramo + k), tramos de 0.2
  function calibrated(c) {
    var raw = Math.max(0, Math.min(1, Number(c.confidence) || 0));
    if (S.cal) {
      var a = S.cal.table[c.agent_type] || {};
      var i = Math.min(4, Math.floor(raw * 5));
      var b = (a.buckets || [])[i] || [0, 0];
      var k = S.cal.k;
      return { value: (b[1] + k * raw) / (b[0] + k), n: b[0], ok: b[0] >= S.cal.min_n };
    }
    var st = (c.confidence_components || {}).calibration;
    return st ? { value: st.calibrated, n: st.n_bucket, ok: !!st.sufficient } : null;
  }
  function calHtml(c) {
    var k = calibrated(c);
    if (!k) return '';
    return k.ok
      ? '<span title="' + esc(L('confianza calibrada con resultados reales (n=' + k.n + ')', 'confidence calibrated with real outcomes (n=' + k.n + ')')) + '">🎯 ' + esc(L('calibrada ', 'calibrated ')) + Math.round(k.value * 100) + '%</span>' + chip('calibration')
      : '<span class="rs-mut">🎯 ' + esc(L('calibrada: sin historial suficiente', 'calibrated: not enough history')) + '</span>' + chip('calibration');
  }
  function trBadge(t) {
    var a = S.tr && S.tr.by[t];
    if (!S.tr) return '';
    if (!a || a.n_scored < S.tr.min_n) return ' <span class="rs-trb">· ' + esc(L('sin historial', 'no track record')) + (a && a.n_scored ? ' (n=' + a.n_scored + ')' : '') + '</span>';
    return ' <span class="rs-trb" title="' + esc(L('aciertos reales · Brier', 'real hit rate · Brier')) + '">· 🎯 ' + Math.round(a.hit_rate * 100) + '% n=' + a.n_scored + (a.brier != null ? ' · B ' + a.brier.toFixed(2) : '') + '</span>';
  }

  function shell() {
    ensureStyles();
    var ov = document.getElementById('rs-ov');
    if (!ov) {
      ov = document.createElement('div'); ov.id = 'rs-ov';
      ov.className = 'kos-themed';   // tokens --os-* de Khipus OS (claro/oscuro) fuera de #bcp-ov
      ov.innerHTML = '<div id="rs" role="dialog" aria-modal="true" aria-label="' + esc(L('Investigación IA', 'AI research')) + '"></div>';
      ov.addEventListener('click', function (e) { if (e.target === ov) close(); });
      document.body.appendChild(ov);
    }
    return ov;
  }
  function close() {
    var ov = document.getElementById('rs-ov'); if (ov) ov.classList.remove('show');
    if (S.poll) { clearInterval(S.poll); S.poll = null; }
  }

  // Sin ventana de "¿cómo te identificamos?": bloqueaba la investigación (y en
  // el teléfono a veces ni aparece). Se usa el nombre guardado si existe.
  function actor() {
    var a = null;
    try { a = localStorage.getItem('khipu_actor'); } catch (e) {}
    return (a && a.trim()) || 'usuario';
  }

  // Mensaje visible y claro dentro del panel (no un aviso que se pierde).
  function friendlyError(d) {
    var st = d && d._status;
    if (st === 429) return L('Hiciste muchas investigaciones en poco tiempo. Espera unos minutos y reintenta.', 'Too many research requests in a short time. Wait a few minutes and try again.');
    if (st === 404) return L('No encontré esa empresa en el catálogo.', 'That company is not in the catalog.');
    if (st === 503 && /IA|proveedor/i.test((d && d.error) || '')) return L('No hay ningún servicio de IA disponible ahora (revisa 🩺 Sistema → IA).', 'No AI service is available right now (check 🩺 System → AI).');
    if (st === 503) return L('La investigación necesita la base de datos (DATABASE_URL en Railway).', 'Research needs the database (DATABASE_URL on Railway).');
    var base = (d && d.error) || L('No se pudo iniciar la investigación.', 'Could not start research.');
    // Mostrar SIEMPRE el código y el detalle técnico: con eso se diagnostica.
    return base + ' [' + (st || '?') + (d && d.detail ? ' · ' + d.detail : '') + (d && d._raw ? ' · ' + d._raw : '') + ']';
  }
  function runErrors(j) {
    var out = [];
    (j.runs || []).forEach(function (r) {
      if (r.status === 'failed' || r.status === 'skipped') {
        var e = (r.errors || [])[0];
        var hint = isEn() ? r.hint_en : r.hint_es;
        out.push(ag(r.agent_type) + ': ' + (hint ? hint + ' — ' : '') + (typeof e === 'string' ? e : L('sin detalle', 'no detail')));
      }
    });
    if (j.error) out.push(j.error);
    return out;
  }

  function getJSON(url, opts) {
    return fetch(base() + url, opts).then(function (r) {
      return r.text().then(function (t) {
        var d; try { d = JSON.parse(t); } catch (e) { d = { _raw: String(t || '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 160) }; }
        if (!d || typeof d !== 'object') d = {};
        d._status = r.status; return d;
      });
    });
  }

  function claimCard(c, compact) {
    var s = STANCE[c.stance] || STANCE.neutral;
    var pct = Math.round((c.confidence || 0) * 100);
    return '<div class="rs-claim">' +
      '<div class="rs-st"><span class="rs-dot" style="background:' + s[0] + '" title="' + esc(L(s[1], s[2])) + '"></span>' +
        esc(isEn() ? (c.statement_en || c.statement_es) : c.statement_es) + '</div>' +
      '<div class="rs-meta">' +
        '<span class="rs-badge">' + esc(hz(c.horizon)) + '</span>' + chip('horizon') +
        '<span title="' + esc(L('confianza calculada', 'computed confidence')) + '"><span class="rs-bar"><i style="width:' + pct + '%"></i></span> <span class="rs-pct">' + pct + '%</span></span>' + chip('claim_conf') +
        calHtml(c) +
        (compact ? '' : agH(c.agent_type, 18)) +
        '<span>📎 ' + (c.n_supporting || 0) + ' ' + esc(L('a favor', 'for')) + ' · ' + (c.n_counter || 0) + ' ' + esc(L('en contra', 'against')) + '</span>' +
        '<span>' + esc(clock(c.created_at)) + '</span>' +
        '<button type="button" class="rs-why" onclick="window.KhipuResearch.why(\'' + esc(c.claim_id) + '\')">' + esc(L('¿Por qué? →', 'Why? →')) + '</button>' +
      '</div></div>';
  }

  function render() {
    var rs = document.getElementById('rs'); if (!rs) return;
    S.view = 'main';
    var d = S.data || {};
    var by = d.by_agent || {};
    var types = Object.keys(AG).filter(function (t) { return by[t] && by[t].length; });
    if (!S.tab || types.indexOf(S.tab) < 0) S.tab = types[0] || null;
    var claims = S.tab ? by[S.tab] : [];
    var syn = d.last_job && d.last_job.synthesis;
    rs.innerHTML =
      '<div class="rs-hd"><span class="rs-name">' + stackH(TEAM, 26, '🔬') + '<span>' + esc(L('Investigación IA', 'AI research')) + ' · <span class="rs-ent">' + esc(nodeLabel(S.entity)) + '</span></span></span>' +
        '<span class="rs-ctl">' +
        '<select id="rs-depth" aria-label="' + esc(L('Profundidad', 'Depth')) + '"><option value="QUICK">' + esc(L('Rápida', 'Quick')) + '</option><option value="STANDARD" selected>' + esc(L('Normal', 'Standard')) + '</option><option value="DEEP">' + esc(L('Profunda', 'Deep')) + '</option></select>' +
        '<button type="button" class="rs-btn" id="rs-go"' + (S.job ? ' disabled' : '') + '>' + esc(S.job ? L('Investigando…', 'Researching…') : L('Investigar', 'Research')) + '</button>' +
        (window.KhipuCommittee ? '<button type="button" class="rs-btn ghost" onclick="window.KhipuCommittee.open(\'' + esc(S.entity) + '\')" title="' + esc(L('Comité de inversión: propuesta con aprobación humana', 'Investment committee: proposal with human approval')) + '">' + mascot('committee', 20) + esc(L('Comité', 'Committee')) + '</button>' : '') +
        '</span>' +
        '<button type="button" class="rs-x" onclick="window.KhipuResearch.close()" title="' + esc(L('Cerrar', 'Close')) + '" aria-label="' + esc(L('Cerrar', 'Close')) + '">✕</button></div>' +
      '<div class="rs-sub">' + esc(L('Agentes especializados leen datos reales (estados financieros, mercado, noticias, grafo) y escriben conclusiones con evidencia a favor y en contra. No son recomendaciones de compra o venta. Los agentes pueden discrepar: se muestran ambas posturas.',
        'Specialized agents read real data (financial statements, market, news, graph) and write conclusions with evidence for and against. Not buy or sell recommendations. Agents may disagree: both views are shown.')) + '</div>' +
      (S.msg ? '<div class="rs-msg' + (S.msg.bad ? ' bad' : '') + '" role="status">' + esc(S.msg.text) + '</div>' : '') +
      (d.last_job && d.last_job.status === 'partial' && d.last_job.coverage && !d.last_job.coverage.complete ? coverageHtml(d.last_job.coverage, true) : '') +
      (d.last_job && d.last_job.status === 'deferred' ? '<div class="rs-msg bad">⏳ ' +
        esc(L('Investigación en espera por presupuesto: se reanuda sola el ', 'Research waiting for budget: resumes automatically on ') + String(((d.last_job || {}).resume_after || '')).slice(0, 16).replace('T', ' ') + ' UTC.') + '</div>' : '') +
      '<div class="rs-grid"><div>' +
        '<div class="rs-cell"><div class="rs-t">' + esc(L('Conclusiones por perspectiva', 'Conclusions by perspective')) + '</div>' +
          (types.length ? '<div class="rs-tabs">' + types.map(function (t) {
            return '<button type="button" class="rs-tab' + (t === S.tab ? ' on' : '') + '" data-t="' + t + '" aria-pressed="' + (t === S.tab) + '">' + agH(t, 20) + ' <span class="rs-n">(' + by[t].length + ')</span>' + trBadge(t) + '</button>'; }).join('') + '</div>' +
            claims.map(function (c) { return claimCard(c, true); }).join('')
            : '<div class="rs-note">' + esc(S.data === null ? L('Cargando investigación…', 'Loading research…')
              : d._status === 503 ? L('La investigación necesita la base de datos (DATABASE_URL en Railway).', 'Research needs the database (DATABASE_URL on Railway).')
              : L('Todavía no hay investigación de esta empresa. Pulsa «Investigar».', 'No research for this company yet. Press “Research”.')) + '</div>') +
        '</div>' +
        (d.contradictions && d.contradictions.length ? '<div class="rs-cell" style="margin-top:12px"><div class="rs-t">⚖️ ' + esc(L('Señales en conflicto (no se resuelven aquí)', 'Conflicting signals (not resolved here)')) + '</div>' +
          d.contradictions.map(function (x) { return '<div class="rs-note" style="margin-bottom:8px">' + esc(conflictText(x)) + ' <button type="button" class="rs-why" onclick="window.KhipuResearch.why(\'' + esc(x.a) + '\')">A →</button> <button type="button" class="rs-why" onclick="window.KhipuResearch.why(\'' + esc(x.b) + '\')">B →</button></div>'; }).join('') + '</div>' : '') +
        (syn ? synthesisHtml(syn) : '') +
      '</div><div>' +
        '<div class="rs-cell"><div class="rs-t">' + stackH(TEAM, 20, '📡') + ' ' + esc(L('Actividad de agentes (real)', 'Agent activity (real)')) + '</div><div id="rs-act"><div class="rs-note">…</div></div></div>' +
      '</div></div>';
    rs.querySelectorAll('.rs-tab').forEach(function (b) { b.onclick = function () { S.tab = b.getAttribute('data-t'); render(); loadActivity(); }; });
    var go = document.getElementById('rs-go');
    if (go) go.onclick = function () { run(S.entity, (document.getElementById('rs-depth') || {}).value || 'STANDARD'); };
    var comp = document.getElementById('rs-complete');
    if (comp) comp.onclick = function () { run(S.entity, (document.getElementById('rs-depth') || {}).value || 'STANDARD', true); };
    loadActivity();
  }

  function synthesisHtml(syn) {
    var order = ['SHORT_TERM', 'MEDIUM_TERM', 'LONG_TERM', 'STRUCTURAL', 'INTRADAY'];
    var hs = order.filter(function (h) { return syn.by_horizon && syn.by_horizon[h]; });
    if (!hs.length) return '';
    var li = function (arr) { return arr.map(function (x) { return '<li>' + esc(isEn() ? (x.en || x.es) : x.es) + ' <span class="rs-mut">(' + esc(ag(x.agent)) + ', ' + Math.round(x.confidence * 100) + '%)</span></li>'; }).join(''); };
    return '<div class="rs-cell" style="margin-top:12px"><div class="rs-t">🧭 ' + esc(L('Síntesis de investigación', 'Research synthesis')) +
      (syn.coverage && !syn.coverage.complete ? ' <span class="rs-warn" style="font-size:11.5px">· ' + esc(L('PARCIAL', 'PARTIAL')) + '</span>' : '') + '</div>' +
      coverageHtml(syn.coverage, false) +
      hs.map(function (h) {
        var b = syn.by_horizon[h];
        return '<div style="margin-bottom:10px"><div class="rs-hz">' + esc(hz(h)) + '</div>' +
          (b.positive.length ? '<div class="rs-note"><b class="rs-good">' + esc(L('Evidencia positiva', 'Positive evidence')) + '</b><ul>' + li(b.positive) + '</ul></div>' : '') +
          (b.risks.length ? '<div class="rs-note"><b class="rs-bad">' + esc(L('Riesgos', 'Risks')) + '</b><ul>' + li(b.risks) + '</ul></div>' : '') +
          (b.neutral.length ? '<div class="rs-note"><b style="color:var(--os-ink,#F2F2F5)">' + esc(L('Observaciones', 'Observations')) + '</b><ul>' + li(b.neutral) + '</ul></div>' : '') + '</div>';
      }).join('') +
      (syn.open_questions && syn.open_questions.length ? '<div class="rs-note"><b style="color:var(--os-ink,#F2F2F5)">' + esc(L('Preguntas abiertas', 'Open questions')) + '</b><ul>' + syn.open_questions.map(function (q) { return '<li>' + esc(q) + '</li>'; }).join('') + '</ul></div>' : '') +
      '<div class="rs-note" style="font-size:12px">' + esc(L('Esto es investigación, no una recomendación de compra, venta o mantener.', 'This is research, not a buy, sell or hold recommendation.')) + '</div></div>';
  }

  function loadActivity() {
    getJSON('/api/research/activity?limit=12&entity=' + encodeURIComponent(S.entity)).then(function (d) {
      var el = document.getElementById('rs-act'); if (!el) return;
      var rows = d.activity || [];
      if (!rows.length) { el.innerHTML = '<div class="rs-note">' + esc(L('Sin ejecuciones todavía para esta empresa.', 'No runs yet for this company.')) + '</div>'; return; }
      el.innerHTML = rows.map(function (r) {
        var st = ST[r.status] || [r.status, r.status];
        var trig = r.trigger && r.trigger.kind === 'event' ? L('por evento', 'by event') : L('pedido por ', 'requested by ') + ((r.trigger && r.trigger.by) || '—');
        return '<div class="rs-act"><div class="rs-ah">' + mascot(r.agent_type, 18) + '<span><b>' + esc(clock(r.started_at)) + '</b> · ' + esc(ag(r.agent_type)) + ' · ' + esc(L(st[0], st[1])) +
          (r.status === 'done' ? ' · ' + (r.agent_type === 'committee' ? esc(L('memo del comité', 'committee memo')) : (r.claims_generated || 0) + ' ' + esc(L('conclusiones', 'conclusions'))) : '') + '</span></div>' +
          '<div class="rs-as">' + esc(trig) + (r.model ? ' · ' + esc(r.model) : '') + (r.latency_ms ? ' · ' + (r.latency_ms / 1000).toFixed(1) + ' s' : '') +
          (r.est_cost_usd != null ? ' · ≈$' + Number(r.est_cost_usd).toFixed(4) + ' ' + esc(L('est.', 'est.')) : '') + '</div>' +
          (r.status === 'failed' || r.status === 'skipped' ? ((isEn() ? r.hint_en : r.hint_es) ? '<div class="rs-hint">💡 ' + esc(isEn() ? r.hint_en : r.hint_es) + '</div>' : '') +
            '<div class="rs-err">' + esc(String((r.errors || [])[0] || '')) + '</div>' : '') + '</div>';
      }).join('');
    }).catch(function () {});
  }

  // Si mientras carga se abrió «¿Por qué?» (p. ej. desde un [C#] del comité), no se pisa esa vista.
  function load(entity) {
    return getJSON('/api/research/entity/' + encodeURIComponent(entity)).then(function (d) {
      if (d.entity_id) S.entity = d.entity_id;
      S.data = d; if (S.view !== 'why') render(); return d;
    }).catch(function () { S.data = {}; if (S.view !== 'why') render(); });
  }

  function open(entityId) {
    S.entity = entityId; S.data = null; S.tab = null; S.msg = null; S.view = 'loading';
    var ov = shell(); ov.classList.add('show');
    loadLearning();
    document.getElementById('rs').innerHTML = '<div class="rs-hd"><span class="rs-name">' + stackH(TEAM, 26, '🔬') + '<span>' + esc(L('Investigación IA', 'AI research')) + '</span></span>' +
      '<button type="button" class="rs-x" onclick="window.KhipuResearch.close()" title="' + esc(L('Cerrar', 'Close')) + '" aria-label="' + esc(L('Cerrar', 'Close')) + '">✕</button></div>' +
      '<div class="rs-note" style="padding:24px 2px">' + esc(L('Cargando investigación…', 'Loading research…')) + '</div>';
    load(entityId);
  }

  function run(entityId, depth, onlyMissing) {
    var who = actor();
    S.entity = entityId; S.msg = null;
    if (depth === 'DEEP' && !window.confirm(L('La investigación profunda usa más IA (y más costo). ¿Continuar?', 'Deep research uses more AI (and cost). Continue?'))) return;
    getJSON('/api/research/jobs', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entity: entityId, depth: depth || 'STANDARD', actor: who, only_missing: !!onlyMissing }) }).then(function (d) {
      if (!d.job_id) { S.msg = { bad: true, text: friendlyError(d) }; render(); return; }
      if (d.status === 'deferred') {
        S.msg = { bad: true, text: L('Se acabó el presupuesto diario de IA. Tu pedido quedó guardado y se reanuda solo mañana (00:05 UTC). Las conclusiones que ya existen siguen abajo.',
          'The daily AI budget is used up. Your request is saved and resumes automatically tomorrow (00:05 UTC). Existing conclusions remain below.') };
        render(); return;
      }
      if (d.reused && d.nothing_missing) {
        S.msg = { bad: false, text: L('Nada que completar: la última investigación respondió con todos los analistas (' + clock(d.created_at) + '). Para una nueva, pulsa «Investigar».',
          'Nothing to complete: the last research answered with every analyst (' + clock(d.created_at) + '). For a fresh one, press “Research”.') };
        load(S.entity); return;
      }
      if (d.reused && (d.status === 'done' || d.status === 'partial')) {
        S.msg = { bad: d.status === 'partial', text: L('Ya hay una investigación reciente (' + clock(d.created_at) + ')' + (d.status === 'partial' ? ', parcial: mira la cobertura abajo.' : '.'),
          'There is already a recent research job (' + clock(d.created_at) + ')' + (d.status === 'partial' ? ', partial: see the coverage below.' : '.')) };
        load(S.entity); return;
      }
      S.job = d.job_id; render();
      if (S.poll) clearInterval(S.poll);
      S.poll = setInterval(function () {
        getJSON('/api/research/jobs/' + encodeURIComponent(S.job)).then(function (j) {
          loadActivity();
          if (j.status === 'deferred') {
            clearInterval(S.poll); S.poll = null; S.job = null;
            S.msg = { bad: true, text: L('Se acabó el presupuesto diario de IA: la investigación se reanuda sola mañana (00:05 UTC).', 'The daily AI budget is used up: the research resumes automatically tomorrow (00:05 UTC).') };
            load(S.entity); return;
          }
          if (j.status === 'done' || j.status === 'partial' || j.status === 'failed' || j._status === 404) {
            clearInterval(S.poll); S.poll = null; S.job = null;
            var errs = runErrors(j), n = (j.claims || []).length, cov = j.coverage;
            if (!n) S.msg = { bad: true, text: L('La investigación no produjo conclusiones.', 'The research produced no conclusions.') + (errs.length ? ' ' + L('Motivo: ', 'Reason: ') + errs.join(' · ') : '') };
            else if (j.status === 'partial' && cov) S.msg = { bad: true, text: n + ' ' + L('conclusiones nuevas, pero la cobertura es PARCIAL: ', 'new conclusions, but coverage is PARTIAL: ') + (isEn() ? (cov.note_en || cov.note_es) : cov.note_es) };
            else if (errs.length) S.msg = { bad: false, text: n + ' ' + L('conclusiones nuevas. Algunos agentes fallaron: ', 'new conclusions. Some agents failed: ') + errs.join(' · ') };
            else S.msg = { bad: false, text: n + ' ' + L('conclusiones nuevas.', 'new conclusions.') };
            load(S.entity);
          } else if (j.status === 'queued' && j.queue_position) {
            S.msg = { bad: false, text: L('En cola: posición ', 'Queued: position ') + j.queue_position + (j.jobs_running ? ' · ' + j.jobs_running + ' ' + L('en curso', 'running') : '') };
            render();
          }
        });
      }, 3000);
    }).catch(function () { S.msg = { bad: true, text: L('Sin conexión con el servidor.', 'No connection to the server.') }; render(); });
  }

  // Nombre legible del tipo de evidencia (es/en)
  var SRC = { analysis: ['cálculo de Khipus (ratios, pares, técnico)', 'Khipus calculation (ratios, peers, technicals)'],
    computed: ['calculado por Khipus con los estados/perfil (no es fuente externa)', 'computed by Khipus from the statements/profile (not an external source)'], filing: ['reporte oficial SEC', 'official SEC filing'], earnings: ['resultados trimestrales', 'quarterly results'], financials: ['estados financieros', 'financial statements'],
    market: ['mercado en vivo', 'live market'], news: ['noticia', 'news'], catalog: ['ficha Khipus', 'Khipus profile'],
    graph: ['grafo de la cadena', 'supply-chain graph'], web: ['web', 'web'] };
  function srcName(t) { return SRC[t] ? L(SRC[t][0], SRC[t][1]) : (t || ''); }

  function why(claimId) {
    getJSON('/api/research/claims/' + encodeURIComponent(claimId)).then(function (d) {
      var rs = document.getElementById('rs'); if (!rs || !d.claim) return;
      S.view = 'why';
      var c = d.claim;
      var ev = function (e, cnt) {
        var u = safeUrl(e.source_reference) || safeUrl(e.source && e.source.url);
        return '<div class="rs-ev' + (cnt ? ' cnt' : '') + '"><b>' + esc(e.ref || '') + '</b> · ' + esc(e.title || '') +
          '<div class="rs-ex">' + esc(e.excerpt || '') + '</div>' +
          '<div class="rs-src">' + esc(srcName(e.source_type)) + ' · ' + esc(L('confiabilidad ', 'reliability ')) + Math.round((e.reliability || 0) * 100) + '%' +
          (e.published_at ? ' · ' + esc(clock(e.published_at)) : '') + (u ? ' · <a href="' + esc(u) + '" target="_blank" rel="noopener">' + esc(L('fuente original', 'original source')) + ' ↗</a>' : ' · ' + esc(e.source_reference || '')) + '</div></div>';
      };
      var comps = (c.confidence_components || {}).components || {};
      var r = d.run || {};
      rs.innerHTML =
        '<div class="rs-hd"><button type="button" class="rs-btn ghost" onclick="window.KhipuResearch.back()">← ' + esc(L('Volver', 'Back')) + '</button>' +
          '<span class="rs-name" style="font-size:18px">' + mascot(c.agent_type, 26) + '<span>' + esc(L('¿Por qué?', 'Why?')) + '</span></span>' +
          '<button type="button" class="rs-x" onclick="window.KhipuResearch.close()" title="' + esc(L('Cerrar', 'Close')) + '" aria-label="' + esc(L('Cerrar', 'Close')) + '">✕</button></div>' +
        claimCard(Object.assign({}, c, { n_supporting: d.supporting.length, n_counter: d.counter.length })) +
        '<div class="rs-grid"><div>' +
          '<div class="rs-cell"><div class="rs-t">🧠 ' + esc(L('Resumen del razonamiento (auditable)', 'Reasoning summary (auditable)')) + '</div><div class="rs-note">' + esc(d.reasoning_summary || '—') + '</div>' +
            '<div class="rs-t" style="margin-top:12px">' + esc(L('Qué la demostraría incorrecta', 'What would prove it wrong')) + '</div><ul class="rs-note">' + (c.falsifiers || []).map(function (f) { return '<li>' + esc(f) + '</li>'; }).join('') + '</ul></div>' +
          '<div class="rs-cell" style="margin-top:12px"><div class="rs-t">✅ ' + esc(L('Evidencia a favor', 'Supporting evidence')) + '</div>' + (d.supporting.map(function (e) { return ev(e, false); }).join('') || '—') + '</div>' +
          '<div class="rs-cell" style="margin-top:12px"><div class="rs-t">⛔ ' + esc(L('Evidencia en contra', 'Counter-evidence')) + '</div>' + (d.counter.map(function (e) { return ev(e, true); }).join('') || '<div class="rs-note">' + esc(L('El agente no encontró evidencia en contra en el paquete.', 'The agent found no counter-evidence in the package.')) + '</div>') + '</div>' +
          (d.contradicts && d.contradicts.length ? '<div class="rs-cell" style="margin-top:12px"><div class="rs-t">⚖️ ' + esc(L('Posibles contradicciones', 'Potential contradictions')) + '</div>' +
            d.contradicts.map(function (x) { return '<div class="rs-note" style="margin-bottom:8px">' + agH(x.agent_type, 18) + ': «' + esc(isEn() ? (x.statement_en || x.statement_es) : x.statement_es) + '» <button type="button" class="rs-why" onclick="window.KhipuResearch.why(\'' + esc(x.claim_id) + '\')">→</button></div>'; }).join('') + '</div>' : '') +
        '</div><div>' +
          '<div class="rs-cell"><div class="rs-t">🕸 ' + esc(L('Nodos del grafo afectados', 'Affected graph nodes')) + '</div>' +
            (d.affected_nodes || []).map(function (n) { return '<button type="button" class="rs-node" onclick="window.KhipuResearch.close();window.jumpTo&&window.jumpTo(\'' + esc(n.id) + '\')">' + esc(n.label) + '</button>'; }).join('') + '</div>' +
          '<div class="rs-cell" style="margin-top:12px"><div class="rs-t">📐 ' + esc(L('Cómo se calculó la confianza', 'How confidence was computed')) + chip('claim_conf') + '</div>' +
            Object.keys(comps).map(function (k) { var lb = COMP[k] ? L(COMP[k][0], COMP[k][1]) : k; return '<div class="rs-kv"><span>' + esc(lb) + '</span><span>' + Math.round(comps[k] * 100) + '%</span></div>'; }).join('') +
            ((c.confidence_components || {}).caps || []).map(function () { return '<div class="rs-note">' + esc(L('Una sola referencia → tope de 60%', 'Single reference → capped at 60%')) + '</div>'; }).join('') + '</div>' +
          '<div class="rs-cell" style="margin-top:12px"><div class="rs-t">🧾 ' + esc(L('Quién y cuándo', 'Who and when')) + '</div>' +
            [[L('Agente', 'Agent'), ag(c.agent_type) + ' v' + (c.agent_version || '')], [L('Modelo', 'Model'), c.model || '—'],
             [L('Versión del prompt', 'Prompt version'), c.prompt_version || '—'], [L('Profundidad', 'Depth'), c.depth],
             [L('Creada', 'Created'), clock(c.created_at)], [L('Disparador', 'Trigger'), r.trigger ? (r.trigger.kind === 'event' ? L('evento', 'event') + ': ' + ((r.trigger.event || {}).headline || '') : L('pedido de ', 'requested by ') + (r.trigger.by || '—')) : '—'],
             [L('Duración', 'Duration'), r.latency_ms ? (r.latency_ms / 1000).toFixed(1) + ' s' : '—'],
             [L('Tokens (est.)', 'Tokens (est.)'), (r.tokens_in || 0) + ' / ' + (r.tokens_out || 0)],
             [L('Costo (est.)', 'Cost (est.)'), r.est_cost_usd != null ? '$' + Number(r.est_cost_usd).toFixed(4) : '—']]
              .map(function (kv) { return '<div class="rs-kv"><span>' + esc(kv[0]) + '</span><span>' + esc(kv[1]) + '</span></div>'; }).join('') + '</div>' +
        '</div></div>';
    });
  }

  // bloque compacto para la ficha del mapa
  function renderInline(el, entityId) {
    if (!el) return;
    getJSON('/api/research/entity/' + encodeURIComponent(entityId)).then(function (d) {
      if (!el.isConnected) return;
      if (d._status === 503) { el.innerHTML = '<div class="v8-loading" style="font-style:normal">' + esc(L('Requiere la base de datos.', 'Requires the database.')) + '</div>'; return; }
      var all = [];
      Object.keys(d.by_agent || {}).forEach(function (k) { all = all.concat(d.by_agent[k]); });
      all.sort(function (a, b) { return (b.confidence || 0) - (a.confidence || 0); });
      var top = all.slice(0, 3);
      el.innerHTML =
        (top.length ? top.map(function (c) {
          var s = STANCE[c.stance] || STANCE.neutral;
          // ficha del mapa: dentro de una ventana de Khipus OS manda --os-*; en la vista clásica, las variables de app.html
          return '<div style="padding:6px 0;border-bottom:1px solid var(--os-line,var(--line,rgba(255,255,255,.07)));font-size:12px;line-height:1.45">' +
            '<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:' + s[0] + ';margin-right:6px"></span>' +
            esc(isEn() ? (c.statement_en || c.statement_es) : c.statement_es) +
            '<div style="display:flex;align-items:center;gap:5px;flex-wrap:wrap;margin-top:2px;font-size:11px;color:var(--os-ink-2,var(--ink-2,#A6A8B5))">' + mascot(c.agent_type, 14) + esc(ag(c.agent_type)) + ' · ' + esc(hz(c.horizon)) + ' · ' + Math.round(c.confidence * 100) + '%</div></div>';
        }).join('') : '<div style="font-size:12px;color:var(--os-ink-2,var(--ink-2,#A6A8B5))">' + esc(L('Sin investigación todavía.', 'No research yet.')) + '</div>') +
        '<div style="display:flex;gap:6px;margin-top:8px;flex-wrap:wrap">' +
          '<button type="button" onclick="window.KhipuResearch.open(\'' + esc(entityId) + '\');window.KhipuResearch.run(\'' + esc(entityId) + '\',\'STANDARD\')" style="display:inline-flex;align-items:center;gap:6px;height:30px;padding:0 12px;border:0;border-radius:999px;background:var(--os-btn,var(--ink,#F2F2F5));color:var(--os-btn-ink,var(--surface,#111216));cursor:pointer;font:inherit;font-size:12px;font-weight:700">' + stackH(TEAM.slice(0, 3), 14, '🔬') + esc(L('Investigar', 'Research')) + '</button>' +
          (top.length ? '<button type="button" onclick="window.KhipuResearch.open(\'' + esc(entityId) + '\')" style="height:30px;padding:0 12px;border:0;border-radius:999px;background:var(--os-surface-2,var(--surface-2,#1F2029));color:var(--os-ink,var(--ink,#F2F2F5));cursor:pointer;font:inherit;font-size:12px;font-weight:600">' + esc(L('Ver todo (' + all.length + ')', 'See all (' + all.length + ')')) + '</button>' : '') +
        '</div>';
    }).catch(function () { el.innerHTML = ''; });
  }

  window.KhipuResearch = { open: open, close: close, run: run, why: why, renderInline: renderInline,
    back: function () { render(); } };
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });
})();
