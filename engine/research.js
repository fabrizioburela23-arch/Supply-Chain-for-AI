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
  var STANCE = { positive: ['#2BE38B', 'a favor', 'positive'], negative: ['#FF4D6A', 'en contra', 'negative'],
    neutral: ['#9BA6C4', 'neutral', 'neutral'], mixed: ['#FFB300', 'mixta', 'mixed'] };
  var ST = { running: ['investigando…', 'investigating…'], done: ['listo', 'done'], failed: ['falló', 'failed'],
    skipped: ['omitido', 'skipped'], queued: ['en cola', 'queued'] };
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
  function ag(t) { var a = AG[t] || ['🤖', t, t]; return a[0] + ' ' + L(a[1], a[2]); }
  function hz(h) { var x = HZ[h] || [h, h]; return L(x[0], x[1]); }

  function ensureStyles() {
    if (document.getElementById('rs-styles')) return;
    var css = '' +
      '#rs-ov{position:fixed;inset:0;z-index:7700;display:none;align-items:center;justify-content:center;background:rgba(3,6,12,.72);backdrop-filter:blur(4px);font-family:Inter,system-ui,sans-serif}' +
      '#rs-ov.show{display:flex}' +
      '#rs{width:min(1100px,96vw);max-height:92vh;overflow-y:auto;border-radius:18px;color:#E8EDFB;background:radial-gradient(1000px 500px at 50% -10%,#0B1222 0%,#06090F 60%);border:1px solid rgba(122,158,255,.2);box-shadow:0 30px 80px rgba(0,0,0,.6);padding:20px 22px}' +
      '#rs .rs-hd{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:6px}' +
      '#rs .rs-name{font-size:21px;font-weight:750}' +
      '#rs .rs-x{margin-left:auto;width:32px;height:32px;border-radius:9px;cursor:pointer;border:1px solid rgba(122,158,255,.2);background:rgba(21,28,45,.7);color:#7C87A3;font-size:16px}' +
      '#rs .rs-sub{font-size:11.5px;color:#7C87A3;margin-bottom:12px;line-height:1.5}' +
      '#rs .rs-btn{border:1px solid #00E0FF;background:rgba(0,224,255,.12);color:#00E0FF;font-weight:700;font-size:12.5px;padding:7px 14px;border-radius:9px;cursor:pointer}' +
      '#rs .rs-btn[disabled]{opacity:.5;cursor:default}' +
      '#rs select{background:#0B1222;color:#E8EDFB;border:1px solid rgba(122,158,255,.25);border-radius:8px;padding:6px 8px;font-size:12px}' +
      '#rs .rs-grid{display:grid;grid-template-columns:minmax(0,2fr) minmax(0,1fr);gap:14px}' +
      '#rs .rs-cell{border:1px solid rgba(122,158,255,.14);border-radius:13px;background:rgba(11,18,34,.55);padding:12px 14px}' +
      '#rs .rs-t{font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#7C87A3;margin-bottom:8px}' +
      '#rs .rs-tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}' +
      '#rs .rs-tab{font-size:12px;padding:5px 10px;border-radius:999px;border:1px solid rgba(122,158,255,.2);background:none;color:#9BA6C4;cursor:pointer}' +
      '#rs .rs-tab.on{border-color:#00E0FF;color:#00E0FF;background:rgba(0,224,255,.08)}' +
      '#rs .rs-claim{border:1px solid rgba(122,158,255,.12);border-radius:11px;padding:10px 12px;margin-bottom:8px;background:rgba(6,9,15,.5)}' +
      '#rs .rs-st{font-size:13.5px;line-height:1.5;color:#E8EDFB}' +
      '#rs .rs-meta{display:flex;gap:8px;flex-wrap:wrap;align-items:center;font-size:11px;color:#9BA6C4;margin-top:6px}' +
      '#rs .rs-badge{font-size:10.5px;padding:2px 8px;border-radius:999px;border:1px solid rgba(122,158,255,.25)}' +
      '#rs .rs-bar{display:inline-block;width:70px;height:6px;border-radius:4px;background:rgba(122,158,255,.15);overflow:hidden;vertical-align:middle}' +
      '#rs .rs-bar i{display:block;height:100%;background:#00E0FF}' +
      '#rs .rs-why{font-size:11.5px;color:#00E0FF;cursor:pointer;background:none;border:none;padding:0;margin-left:auto}' +
      '#rs .rs-act{font-size:11.5px;padding:6px 0;border-bottom:1px solid rgba(122,158,255,.07);line-height:1.45}' +
      '#rs .rs-note{font-size:12px;color:#9BA6C4;line-height:1.55}' +
      '#rs a{color:#5FC6E8;text-decoration:none}#rs a:hover{text-decoration:underline}' +
      '#rs .rs-ev{border-left:3px solid #2BE38B;padding:6px 10px;margin:6px 0;background:rgba(43,227,139,.05);border-radius:0 8px 8px 0;font-size:12px;line-height:1.5}' +
      '#rs .rs-ev.cnt{border-left-color:#FF4D6A;background:rgba(255,77,106,.05)}' +
      '#rs .rs-node{display:inline-block;font-size:11.5px;padding:3px 9px;border-radius:999px;border:1px solid rgba(122,158,255,.25);margin:3px 4px 0 0;cursor:pointer}' +
      '#rs .rs-kv{display:flex;justify-content:space-between;gap:10px;font-size:11.5px;padding:3px 0;border-bottom:1px solid rgba(122,158,255,.06)}' +
      '@media(max-width:760px){#rs .rs-grid{grid-template-columns:minmax(0,1fr)}#rs{padding:16px 14px}}';
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
      : '<span style="color:#7C87A3">🎯 ' + esc(L('calibrada: sin historial suficiente', 'calibrated: not enough history')) + '</span>' + chip('calibration');
  }
  function trBadge(t) {
    var a = S.tr && S.tr.by[t];
    if (!S.tr) return '';
    if (!a || a.n_scored < S.tr.min_n) return ' <span style="font-size:10px;color:#7C87A3">· ' + esc(L('sin historial', 'no track record')) + (a && a.n_scored ? ' (n=' + a.n_scored + ')' : '') + '</span>';
    return ' <span style="font-size:10px;color:#9BA6C4" title="' + esc(L('aciertos reales · Brier', 'real hit rate · Brier')) + '">· 🎯 ' + Math.round(a.hit_rate * 100) + '% n=' + a.n_scored + (a.brier != null ? ' · B ' + a.brier.toFixed(2) : '') + '</span>';
  }

  function shell() {
    ensureStyles();
    var ov = document.getElementById('rs-ov');
    if (!ov) {
      ov = document.createElement('div'); ov.id = 'rs-ov';
      ov.innerHTML = '<div id="rs"></div>';
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
      '<div class="rs-st"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:' + s[0] + ';margin-right:7px"></span>' +
        esc(isEn() ? (c.statement_en || c.statement_es) : c.statement_es) + '</div>' +
      '<div class="rs-meta">' +
        '<span class="rs-badge">' + esc(hz(c.horizon)) + '</span>' + chip('horizon') +
        '<span title="' + esc(L('confianza calculada', 'computed confidence')) + '"><span class="rs-bar"><i style="width:' + pct + '%"></i></span> ' + pct + '%</span>' + chip('claim_conf') +
        calHtml(c) +
        (compact ? '' : '<span>' + esc(ag(c.agent_type)) + '</span>') +
        '<span>📎 ' + (c.n_supporting || 0) + ' ' + esc(L('a favor', 'for')) + ' · ' + (c.n_counter || 0) + ' ' + esc(L('en contra', 'against')) + '</span>' +
        '<span>' + esc(clock(c.created_at)) + '</span>' +
        '<button class="rs-why" onclick="window.KhipuResearch.why(\'' + esc(c.claim_id) + '\')">' + esc(L('¿Por qué? →', 'Why? →')) + '</button>' +
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
      '<div class="rs-hd"><span class="rs-name">🔬 ' + esc(L('Investigación IA', 'AI research')) + ' · ' + esc(nodeLabel(S.entity)) + '</span>' +
        '<select id="rs-depth"><option value="QUICK">' + esc(L('Rápida', 'Quick')) + '</option><option value="STANDARD" selected>' + esc(L('Normal', 'Standard')) + '</option><option value="DEEP">' + esc(L('Profunda', 'Deep')) + '</option></select>' +
        '<button class="rs-btn" id="rs-go"' + (S.job ? ' disabled' : '') + '>' + esc(S.job ? L('Investigando…', 'Researching…') : L('Investigar', 'Research')) + '</button>' +
        (window.KhipuCommittee ? '<button class="rs-btn" style="border-color:#FFB300;color:#FFB300;background:rgba(255,179,0,.08)" onclick="window.KhipuCommittee.open(\'' + esc(S.entity) + '\')" title="' + esc(L('Comité de inversión: propuesta con aprobación humana', 'Investment committee: proposal with human approval')) + '">🏛 ' + esc(L('Comité', 'Committee')) + '</button>' : '') +
        '<button class="rs-x" onclick="window.KhipuResearch.close()" title="' + esc(L('Cerrar', 'Close')) + '">✕</button></div>' +
      '<div class="rs-sub">' + esc(L('Agentes especializados leen datos reales (estados financieros, mercado, noticias, grafo) y escriben conclusiones con evidencia a favor y en contra. No son recomendaciones de compra o venta. Los agentes pueden discrepar: se muestran ambas posturas.',
        'Specialized agents read real data (financial statements, market, news, graph) and write conclusions with evidence for and against. Not buy or sell recommendations. Agents may disagree: both views are shown.')) + '</div>' +
      (S.msg ? '<div class="rs-cell" style="margin-bottom:10px;border-color:' + (S.msg.bad ? '#FFB300' : '#2BE38B') + ';color:' + (S.msg.bad ? '#FFB300' : '#2BE38B') + ';font-size:13px">' + esc(S.msg.text) + '</div>' : '') +
      '<div class="rs-grid"><div>' +
        '<div class="rs-cell"><div class="rs-t">' + esc(L('Conclusiones por perspectiva', 'Conclusions by perspective')) + '</div>' +
          (types.length ? '<div class="rs-tabs">' + types.map(function (t) {
            return '<button class="rs-tab' + (t === S.tab ? ' on' : '') + '" data-t="' + t + '">' + esc(ag(t)) + ' (' + by[t].length + ')' + trBadge(t) + '</button>'; }).join('') + '</div>' +
            claims.map(function (c) { return claimCard(c, true); }).join('')
            : '<div class="rs-note">' + esc(S.data === null ? L('Cargando investigación…', 'Loading research…')
              : d._status === 503 ? L('La investigación necesita la base de datos (DATABASE_URL en Railway).', 'Research needs the database (DATABASE_URL on Railway).')
              : L('Todavía no hay investigación de esta empresa. Pulsa «Investigar».', 'No research for this company yet. Press “Research”.')) + '</div>') +
        '</div>' +
        (d.contradictions && d.contradictions.length ? '<div class="rs-cell" style="margin-top:12px"><div class="rs-t">⚖️ ' + esc(L('Señales en conflicto (no se resuelven aquí)', 'Conflicting signals (not resolved here)')) + '</div>' +
          d.contradictions.map(function (x) { return '<div class="rs-note" style="margin-bottom:6px">' + esc(conflictText(x)) + ' <button class="rs-why" onclick="window.KhipuResearch.why(\'' + esc(x.a) + '\')">A →</button> <button class="rs-why" onclick="window.KhipuResearch.why(\'' + esc(x.b) + '\')">B →</button></div>'; }).join('') + '</div>' : '') +
        (syn ? synthesisHtml(syn) : '') +
      '</div><div>' +
        '<div class="rs-cell"><div class="rs-t">📡 ' + esc(L('Actividad de agentes (real)', 'Agent activity (real)')) + '</div><div id="rs-act"><div class="rs-note">…</div></div></div>' +
      '</div></div>';
    rs.querySelectorAll('.rs-tab').forEach(function (b) { b.onclick = function () { S.tab = b.getAttribute('data-t'); render(); loadActivity(); }; });
    var go = document.getElementById('rs-go');
    if (go) go.onclick = function () { run(S.entity, (document.getElementById('rs-depth') || {}).value || 'STANDARD'); };
    loadActivity();
  }

  function synthesisHtml(syn) {
    var order = ['SHORT_TERM', 'MEDIUM_TERM', 'LONG_TERM', 'STRUCTURAL', 'INTRADAY'];
    var hs = order.filter(function (h) { return syn.by_horizon && syn.by_horizon[h]; });
    if (!hs.length) return '';
    var li = function (arr) { return arr.map(function (x) { return '<li>' + esc(isEn() ? (x.en || x.es) : x.es) + ' <span style="color:#7C87A3">(' + esc(ag(x.agent)) + ', ' + Math.round(x.confidence * 100) + '%)</span></li>'; }).join(''); };
    return '<div class="rs-cell" style="margin-top:12px"><div class="rs-t">🧭 ' + esc(L('Síntesis de investigación', 'Research synthesis')) + '</div>' +
      hs.map(function (h) {
        var b = syn.by_horizon[h];
        return '<div style="margin-bottom:10px"><div style="font-weight:700;font-size:12.5px;margin-bottom:4px">' + esc(hz(h)) + '</div>' +
          (b.positive.length ? '<div class="rs-note"><b style="color:#2BE38B">' + esc(L('Evidencia positiva', 'Positive evidence')) + '</b><ul style="margin:3px 0 6px 18px;padding:0">' + li(b.positive) + '</ul></div>' : '') +
          (b.risks.length ? '<div class="rs-note"><b style="color:#FF4D6A">' + esc(L('Riesgos', 'Risks')) + '</b><ul style="margin:3px 0 6px 18px;padding:0">' + li(b.risks) + '</ul></div>' : '') +
          (b.neutral.length ? '<div class="rs-note"><b>' + esc(L('Observaciones', 'Observations')) + '</b><ul style="margin:3px 0 6px 18px;padding:0">' + li(b.neutral) + '</ul></div>' : '') + '</div>';
      }).join('') +
      (syn.open_questions && syn.open_questions.length ? '<div class="rs-note"><b>' + esc(L('Preguntas abiertas', 'Open questions')) + '</b><ul style="margin:3px 0 6px 18px;padding:0">' + syn.open_questions.map(function (q) { return '<li>' + esc(q) + '</li>'; }).join('') + '</ul></div>' : '') +
      '<div class="rs-note" style="font-size:11px">' + esc(L('Esto es investigación, no una recomendación de compra, venta o mantener.', 'This is research, not a buy, sell or hold recommendation.')) + '</div></div>';
  }

  function loadActivity() {
    getJSON('/api/research/activity?limit=12&entity=' + encodeURIComponent(S.entity)).then(function (d) {
      var el = document.getElementById('rs-act'); if (!el) return;
      var rows = d.activity || [];
      if (!rows.length) { el.innerHTML = '<div class="rs-note">' + esc(L('Sin ejecuciones todavía para esta empresa.', 'No runs yet for this company.')) + '</div>'; return; }
      el.innerHTML = rows.map(function (r) {
        var st = ST[r.status] || [r.status, r.status];
        var trig = r.trigger && r.trigger.kind === 'event' ? L('por evento', 'by event') : L('pedido por ', 'requested by ') + ((r.trigger && r.trigger.by) || '—');
        return '<div class="rs-act"><b>' + esc(clock(r.started_at)) + '</b> · ' + esc(ag(r.agent_type)) + ' · ' + esc(L(st[0], st[1])) +
          (r.status === 'done' ? ' · ' + (r.agent_type === 'committee' ? esc(L('memo del comité', 'committee memo')) : (r.claims_generated || 0) + ' ' + esc(L('conclusiones', 'conclusions'))) : '') +
          '<div style="color:#7C87A3">' + esc(trig) + (r.model ? ' · ' + esc(r.model) : '') + (r.latency_ms ? ' · ' + (r.latency_ms / 1000).toFixed(1) + ' s' : '') +
          (r.est_cost_usd != null ? ' · ≈$' + Number(r.est_cost_usd).toFixed(4) + ' ' + esc(L('est.', 'est.')) : '') + '</div>' +
          (r.status === 'failed' || r.status === 'skipped' ? ((isEn() ? r.hint_en : r.hint_es) ? '<div style="color:#FFB300;font-weight:600">💡 ' + esc(isEn() ? r.hint_en : r.hint_es) + '</div>' : '') +
            '<div style="color:#FFB300">' + esc(String((r.errors || [])[0] || '')) + '</div>' : '') + '</div>';
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
    document.getElementById('rs').innerHTML = '<div class="rs-note" style="padding:30px">' + esc(L('Cargando investigación…', 'Loading research…')) + '</div>';
    load(entityId);
  }

  function run(entityId, depth) {
    var who = actor();
    S.entity = entityId; S.msg = null;
    if (depth === 'DEEP' && !window.confirm(L('La investigación profunda usa más IA (y más costo). ¿Continuar?', 'Deep research uses more AI (and cost). Continue?'))) return;
    getJSON('/api/research/jobs', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entity: entityId, depth: depth || 'STANDARD', actor: who }) }).then(function (d) {
      if (!d.job_id) { S.msg = { bad: true, text: friendlyError(d) }; render(); return; }
      S.job = d.job_id; render();
      if (S.poll) clearInterval(S.poll);
      S.poll = setInterval(function () {
        getJSON('/api/research/jobs/' + encodeURIComponent(S.job)).then(function (j) {
          loadActivity();
          if (j.status === 'done' || j.status === 'failed' || j._status === 404) {
            clearInterval(S.poll); S.poll = null; S.job = null;
            var errs = runErrors(j), n = (j.claims || []).length;
            if (!n) S.msg = { bad: true, text: L('La investigación no produjo conclusiones.', 'The research produced no conclusions.') + (errs.length ? ' ' + L('Motivo: ', 'Reason: ') + errs.join(' · ') : '') };
            else if (errs.length) S.msg = { bad: false, text: n + ' ' + L('conclusiones nuevas. Algunos agentes fallaron: ', 'new conclusions. Some agents failed: ') + errs.join(' · ') };
            else S.msg = { bad: false, text: n + ' ' + L('conclusiones nuevas.', 'new conclusions.') };
            load(S.entity);
          }
        });
      }, 3000);
    }).catch(function () { S.msg = { bad: true, text: L('Sin conexión con el servidor.', 'No connection to the server.') }; render(); });
  }

  // Nombre legible del tipo de evidencia (es/en)
  var SRC = { filing: ['reporte oficial SEC', 'official SEC filing'], earnings: ['resultados trimestrales', 'quarterly results'], financials: ['estados financieros', 'financial statements'],
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
          '<div style="color:#9BA6C4">' + esc(e.excerpt || '') + '</div>' +
          '<div style="color:#7C87A3;font-size:11px">' + esc(srcName(e.source_type)) + ' · ' + esc(L('confiabilidad ', 'reliability ')) + Math.round((e.reliability || 0) * 100) + '%' +
          (e.published_at ? ' · ' + esc(clock(e.published_at)) : '') + (u ? ' · <a href="' + esc(u) + '" target="_blank" rel="noopener">' + esc(L('fuente original', 'original source')) + ' ↗</a>' : ' · ' + esc(e.source_reference || '')) + '</div></div>';
      };
      var comps = (c.confidence_components || {}).components || {};
      var r = d.run || {};
      rs.innerHTML =
        '<div class="rs-hd"><button class="rs-btn" onclick="window.KhipuResearch.back()">← ' + esc(L('Volver', 'Back')) + '</button>' +
          '<span class="rs-name" style="font-size:17px">' + esc(L('¿Por qué?', 'Why?')) + '</span>' +
          '<button class="rs-x" onclick="window.KhipuResearch.close()">✕</button></div>' +
        claimCard(Object.assign({}, c, { n_supporting: d.supporting.length, n_counter: d.counter.length })) +
        '<div class="rs-grid"><div>' +
          '<div class="rs-cell"><div class="rs-t">🧠 ' + esc(L('Resumen del razonamiento (auditable)', 'Reasoning summary (auditable)')) + '</div><div class="rs-note">' + esc(d.reasoning_summary || '—') + '</div>' +
            '<div class="rs-t" style="margin-top:10px">' + esc(L('Qué la demostraría incorrecta', 'What would prove it wrong')) + '</div><ul class="rs-note" style="margin:0 0 0 18px;padding:0">' + (c.falsifiers || []).map(function (f) { return '<li>' + esc(f) + '</li>'; }).join('') + '</ul></div>' +
          '<div class="rs-cell" style="margin-top:12px"><div class="rs-t">✅ ' + esc(L('Evidencia a favor', 'Supporting evidence')) + '</div>' + (d.supporting.map(function (e) { return ev(e, false); }).join('') || '—') + '</div>' +
          '<div class="rs-cell" style="margin-top:12px"><div class="rs-t">⛔ ' + esc(L('Evidencia en contra', 'Counter-evidence')) + '</div>' + (d.counter.map(function (e) { return ev(e, true); }).join('') || '<div class="rs-note">' + esc(L('El agente no encontró evidencia en contra en el paquete.', 'The agent found no counter-evidence in the package.')) + '</div>') + '</div>' +
          (d.contradicts && d.contradicts.length ? '<div class="rs-cell" style="margin-top:12px"><div class="rs-t">⚖️ ' + esc(L('Posibles contradicciones', 'Potential contradictions')) + '</div>' +
            d.contradicts.map(function (x) { return '<div class="rs-note" style="margin-bottom:6px">' + esc(ag(x.agent_type)) + ': «' + esc(isEn() ? (x.statement_en || x.statement_es) : x.statement_es) + '» <button class="rs-why" onclick="window.KhipuResearch.why(\'' + esc(x.claim_id) + '\')">→</button></div>'; }).join('') + '</div>' : '') +
        '</div><div>' +
          '<div class="rs-cell"><div class="rs-t">🕸 ' + esc(L('Nodos del grafo afectados', 'Affected graph nodes')) + '</div>' +
            (d.affected_nodes || []).map(function (n) { return '<span class="rs-node" onclick="window.KhipuResearch.close();window.jumpTo&&window.jumpTo(\'' + esc(n.id) + '\')">' + esc(n.label) + '</span>'; }).join('') + '</div>' +
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
          return '<div style="padding:5px 0;border-bottom:1px solid var(--line);font-size:11.5px;line-height:1.4">' +
            '<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:' + s[0] + ';margin-right:5px"></span>' +
            esc(isEn() ? (c.statement_en || c.statement_es) : c.statement_es) +
            '<div style="font-size:10.5px;color:var(--ink-3)">' + esc(ag(c.agent_type)) + ' · ' + esc(hz(c.horizon)) + ' · ' + Math.round(c.confidence * 100) + '%</div></div>';
        }).join('') : '<div style="font-size:11.5px;color:var(--ink-3)">' + esc(L('Sin investigación todavía.', 'No research yet.')) + '</div>') +
        '<div style="display:flex;gap:6px;margin-top:8px;flex-wrap:wrap">' +
          '<button onclick="window.KhipuResearch.open(\'' + esc(entityId) + '\');window.KhipuResearch.run(\'' + esc(entityId) + '\',\'STANDARD\')" style="padding:4px 10px;border:1px solid #00E0FF;border-radius:6px;background:none;color:#00E0FF;cursor:pointer;font-size:11px;font-weight:700">🔬 ' + esc(L('Investigar', 'Research')) + '</button>' +
          (top.length ? '<button onclick="window.KhipuResearch.open(\'' + esc(entityId) + '\')" style="padding:4px 10px;border:1px solid var(--line);border-radius:6px;background:none;color:var(--ink-2);cursor:pointer;font-size:11px">' + esc(L('Ver todo (' + all.length + ')', 'See all (' + all.length + ')')) + '</button>' : '') +
        '</div>';
    }).catch(function () { el.innerHTML = ''; });
  }

  window.KhipuResearch = { open: open, close: close, run: run, why: why, renderInline: renderInline,
    back: function () { render(); } };
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });
})();
