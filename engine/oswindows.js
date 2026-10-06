/* ============================================================================
   engine/oswindows.js — VENTANAS NATIVAS de Khipus OS (2026-10-06)

   «…y la respuesta llega en ventanas que entiendes de un vistazo» (video
   "Khipus OS", cuadro full_14). Cuatro ventanas, pintadas SOLO con tokens
   --os-* (claro y oscuro), bilingües ES/EN y multi-instancia:

     glance      (multi, {id})  «<Empresa> en una mirada»: número grande =
                                 convicción del comité si hay memo vigente
                                 (cuenta animada desde 0) o, si no, el PRECIO
                                 EN VIVO con su variación, fuente y hora.
                                 Pros/contras del memo, de la pizarra o de la
                                 estructura de la cadena (siempre rotulado).
     conviction  ({id?})         «Convicción de tus agentes»: barras −100..+100
                                 de /api/committee/board, la empresa pedida
                                 resaltada; vacío honesto si no hay datos.
     supplychain (multi, {id})   «Cadena de suministro de X»: proveedores ←
                                 empresa → clientes desde window.LINKS (solo
                                 relaciones de FLUJO), instantáneo; el riesgo
                                 aguas arriba (tensor) llega después.
     agents      ()              «Tus agentes»: las 6 mascotas, qué hacen, qué
                                 datos usan, qué te muestran, historial honesto,
                                 costo 30 d y preferencias (KhipuAgentPrefs).

   Contrato (docs/KHIPUS_OS.md §3.1): se registran solas con
     BixbyCockpit.registerKind(kind, {icon, es, en, multi, title(arg), render(body, arg)})
   (cockpit.js puede cargar antes o después: se reintenta ~10 s) y se abren con
     KhipuOSWin.open(kind, arg)  → BixbyCockpit.stage(kind, arg) (abre la Cabina si hace falta).
   KhipuOSWin.render(kind, body, arg) pinta en cualquier contenedor (pruebas).

   Reglas que NO se rompen aquí:
   · Cifras SOLO de fuentes reales con su fuente y hora; nada inventado.
   · Dinero: «Revisar propuesta» abre el comité (KhipuCommittee.open), que exige
     aprobación humana con PIN. Este archivo no envía órdenes ni pide el PIN.
   · Solo body.querySelector (sin ids globales): varias ventanas a la vez.
   ============================================================================ */
(function () {
  'use strict';
  if (window.KhipuOSWin && window.KhipuOSWin.__v) return;

  /* ── idioma, escape ─────────────────────────────────────────────────────── */
  function lang() {
    var l = null;
    try { l = window.LANG; } catch (e) { l = null; }
    if (l !== 'en' && l !== 'es') { try { l = localStorage.getItem('eco_lang'); } catch (e) { l = null; } }
    return l === 'en' ? 'en' : 'es';
  }
  function L(es, en) { return lang() === 'en' ? en : es; }
  function pick(o, base) {
    if (!o) return '';
    var es = o[base + '_es'], en = o[base + '_en'];
    return lang() === 'en' ? (en || es || '') : (es || en || '');
  }
  var ESC = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return ESC[c]; }); }
  function clean(s) {   // quita referencias [C1] [E2, R1] del texto (la evidencia está en «Ver evidencia»)
    return String(s == null ? '' : s).replace(/\s*\[(?:[A-Z]{1,2}\d+(?:\s*,\s*)?)+\]/g, '').replace(/\s+/g, ' ').trim();
  }

  /* ── formato de cifras (determinista: sin depender del ICU del navegador) ── */
  var MINUS = '−';
  function group(intStr, sep) {
    var out = '';
    for (var i = intStr.length; i > 0; i -= 3) out = intStr.slice(Math.max(0, i - 3), i) + (out ? sep + out : '');
    return out;
  }
  // es: 50.218,49 · en: 50,218.49 · signo opcional (+/−); −0,0 nunca se muestra
  function fmtNum(v, dec, lg, opts) {
    if (v === null || v === undefined || v === '') return '—';
    v = Number(v);
    if (!isFinite(v)) return '—';
    dec = dec == null ? 0 : dec;
    lg = lg === 'en' || lg === 'es' ? lg : lang();
    var fixed = Math.abs(v).toFixed(dec), zero = Number(fixed) === 0, parts = fixed.split('.');
    var s = group(parts[0], lg === 'en' ? ',' : '.') + (parts[1] ? (lg === 'en' ? '.' : ',') + parts[1] : '');
    var sign = '';
    if (!zero) { if (v < 0) sign = MINUS; else if (opts && opts.sign) sign = '+'; }
    return sign + s;
  }
  function fmtConv(v, lg) { return fmtNum(v, 1, lg, { sign: true }); }
  function fmtPct(v, lg, dec, signed) {
    lg = lg === 'en' || lg === 'es' ? lg : lang();
    var s = fmtNum(v, dec == null ? 1 : dec, lg, { sign: signed !== false });
    if (s === '—') return s;
    return lg === 'en' ? s + '%' : s + ' %';
  }
  // regla de color de las barras de convicción (spec §3.4 / video):
  // |v| < 5 → gris · a favor → azul · en contra fuerte (≤ −15) → naranja · otro en contra → gris
  function barTone(v) {
    v = Math.round(Number(v) * 10) / 10;
    if (!isFinite(v) || Math.abs(v) < 5) return 'mute';
    if (v > 0) return 'pos';
    return v <= -15 ? 'neg' : 'mute';
  }
  // geometría: el eje 0 está al 50 % de la pista; ±100 llena media pista
  function barGeom(v) {
    v = Number(v);
    if (!isFinite(v)) v = 0;
    var a = Math.min(100, Math.abs(v));
    return { side: v < 0 ? 'neg' : 'pos', pct: Math.round(a / 2 * 100) / 100 };
  }
  var CUR = { USD: '$', EUR: '€', GBP: '£', JPY: '¥', CNY: 'CN¥', KRW: '₩', TWD: 'NT$', HKD: 'HK$', INR: '₹',
    CAD: 'C$', AUD: 'A$', CHF: 'CHF ', SEK: 'SEK ', NOK: 'NOK ', DKK: 'DKK ', BRL: 'R$', MXN: 'MX$', ILS: '₪', SGD: 'S$' };
  function fmtMoney(v, cur, lg) {
    v = Number(v);
    if (!isFinite(v) || v <= 0) return '—';
    cur = String(cur || 'USD').toUpperCase();
    var dec = (cur === 'JPY' || cur === 'KRW') ? 0 : (v < 1 ? 4 : 2);
    return (CUR[cur] != null ? CUR[cur] : cur + ' ') + fmtNum(v, dec, lg);
  }
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  var MON = { es: ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sept', 'oct', 'nov', 'dic'],
    en: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'] };
  function fmtWhen(iso, withTime) {
    if (!iso) return '';
    var d = new Date(iso);
    if (isNaN(d.getTime())) return '';
    var lg = lang(), now = new Date(), s;
    if (d.toDateString() === now.toDateString()) s = lg === 'en' ? 'today' : 'hoy';
    else s = lg === 'en' ? MON.en[d.getMonth()] + ' ' + d.getDate() : d.getDate() + ' ' + MON.es[d.getMonth()];
    if (d.getFullYear() !== now.getFullYear()) s += ' ' + d.getFullYear();
    if (withTime !== false) s += (lg === 'en' ? ', ' : ', ') + pad(d.getHours()) + ':' + pad(d.getMinutes());
    return s;
  }
  function agoText(sec) {
    if (sec == null || !isFinite(sec)) return '';
    if (typeof window.quoteAgoText === 'function') { try { return window.quoteAgoText(sec); } catch (e) {} }
    if (sec < 60) return L('hace ' + sec + ' s', sec + 's ago');
    if (sec < 3600) return L('hace ' + Math.round(sec / 60) + ' min', Math.round(sec / 60) + ' min ago');
    if (sec < 86400) return L('hace ' + Math.round(sec / 3600) + ' h', Math.round(sec / 3600) + ' h ago');
    return L('hace ' + Math.round(sec / 86400) + ' d', Math.round(sec / 86400) + ' d ago');
  }

  /* ── catálogo (cliente) ─────────────────────────────────────────────────── */
  function canon(id) { try { return typeof window._canonId === 'function' ? window._canonId(id) : id; } catch (e) { return id; } }
  function lidv(v) { return (v && typeof v === 'object') ? v.id : v; }
  function argId(arg) {
    if (arg == null) return null;
    if (typeof arg === 'string' || typeof arg === 'number') return String(arg);
    var a = arg.id || arg.entity || arg.entity_id || arg.a || arg.ticker || null;
    return a == null || typeof a === 'object' ? null : String(a);
  }
  function nodeOf(id) {
    if (id == null || id === '') return null;
    var raw = String(id), NB = window.NODE_BY_ID || {}, n = NB[raw] || null;
    if (!n) {
      var low = raw.toLowerCase(), N = window.NODES || [];
      for (var i = 0; i < N.length; i++) {
        var x = N[i];
        if (!x) continue;
        if (String(x.id).toLowerCase() === low || (x.mkt && String(x.mkt).toLowerCase() === low) || (x.label && String(x.label).toLowerCase() === low)) { n = x; break; }
      }
    }
    if (!n && window.KhipuResolve && typeof window.KhipuResolve.find === 'function') {
      try { var r = window.KhipuResolve.find(raw); if (r && r.node && r.score >= 85) n = r.node; } catch (e) {}
    }
    return n || null;
  }
  function labelOf(n, fallback) { return n ? (n.label || n.id) : (fallback || ''); }
  function labelById(id) { var n = (window.NODE_BY_ID || {})[id]; return n ? labelOf(n) : String(id); }

  var FLOW = { supply: 1, fab: 1, cloud: 1, license: 1, ppa: 1, owns: 1, deploy: 1 };
  // proveedores (X → id) y clientes (id → X) por relaciones de FLUJO, sin pares
  // repetidos; peso efectivo = w × conf (igual que matrix/engine.py _eff_weight)
  function chainOf(id, links, canonFn) {
    var cf = typeof canonFn === 'function' ? canonFn : function (x) { return x; };
    var me = cf(id), S = {}, C = {};
    function add(map, k, l, w) {
      var e = map[k];
      if (!e) e = map[k] = { id: k, w: 0, types: [], rel: '', verified: false, n: 0 };
      e.n++;
      if (w > e.w) { e.w = w; e.rel = l.rel || e.rel; }
      var ty = l.type || 'supply';
      if (e.types.indexOf(ty) < 0) e.types.push(ty);
      if (l.verified !== false) e.verified = true;
    }
    links = links || [];
    for (var i = 0; i < links.length; i++) {
      var l = links[i];
      if (!l || !FLOW[l.type || 'supply']) continue;
      var s = cf(lidv(l.source)), t = cf(lidv(l.target));
      if (s == null || t == null || s === t) continue;
      var conf = (l.conf != null && isFinite(+l.conf)) ? +l.conf : 1;
      var w = Math.max(0, (+l.w || 0) * conf);
      if (t === me) add(S, s, l, w);
      else if (s === me) add(C, t, l, w);
    }
    function sorted(map) {
      return Object.keys(map).map(function (k) { return map[k]; })
        .sort(function (a, b) { return (b.w - a.w) || String(a.id).localeCompare(String(b.id)); });
    }
    return { id: me, suppliers: sorted(S), customers: sorted(C) };
  }

  /* ── mascotas ───────────────────────────────────────────────────────────── */
  var MCOLOR = { khipu: '#c23a8c', analista: '#4054cf', radar: '#e63e52', cadena: '#1b9386', tecnico: '#e6a117', comite: '#7a3fe0' };
  var SEAT = { fundamental: 'analista', fundamentals: 'analista', macro: 'analista', valuation: 'analista',
    news: 'radar', geopolitical: 'radar', crypto: 'radar', sentiment: 'radar',
    supply_chain: 'cadena', technical: 'tecnico', risk_observation: 'tecnico', risk: 'tecnico', market: 'tecnico',
    committee: 'comite', chair: 'comite', quant: 'comite', mandate: 'comite', all: 'comite' };
  function mascot(id, size, state) {
    var M = window.KhipuMascot;
    if (M && typeof M.svg === 'function') { try { return M.svg(id, size, { state: state || 'idle' }); } catch (e) {} }
    return '<span class="osw-mdot" style="width:' + size + 'px;height:' + size + 'px;background:' + (MCOLOR[id] || '#8D90A0') + '" aria-hidden="true"></span>';
  }
  function mascotOf(agentType) {
    var M = window.KhipuMascot, id = null;
    if (M && typeof M.of === 'function') { try { id = M.of(agentType); } catch (e) { id = null; } }
    return id || SEAT[String(agentType || '').toLowerCase()] || 'khipu';
  }
  function stackOf(ids, size) {
    var M = window.KhipuMascot;
    if (M && typeof M.stack === 'function') { try { return M.stack(ids, size); } catch (e) {} }
    return '<span class="osw-mstack">' + ids.map(function (i) { return mascot(i, size); }).join('') + '</span>';
  }

  /* ── perfiles de agentes: respaldo estático (mismo contrato que /api/agents/profiles,
        sin historial). "Datos que usa" = research/context.py AGENT_NEEDS (lo que de
        verdad se trae), no la lista declarativa de herramientas. ─────────────── */
  var AGENTS = [
    { id: 'khipu', es: 'Khipu', en: 'Khipu', role_es: 'Te responde', role_en: 'Answers you',
      does_es: 'Conversa contigo, entiende qué preguntas y llama a los demás agentes y herramientas. Arma la respuesta con sus fuentes y abre las ventanas que la explican.',
      does_en: 'Talks with you, understands what you ask and calls the other agents and tools. Builds the answer with its sources and opens the windows that explain it.',
      data_es: ['Catálogo y cadena de suministro', 'Precios en vivo', 'Conclusiones de los agentes', 'Memos del comité', 'Noticias y eventos del mundo'],
      data_en: ['Catalog and supply chain', 'Live prices', 'Agent conclusions', 'Committee memos', 'News and world events'],
      outputs_es: ['Respuesta con fuentes', 'Ventanas de la respuesta', 'Gráficos'], outputs_en: ['Answer with sources', 'Answer windows', 'Charts'],
      research_types: [], tools: [], windows: [] },
    { id: 'analista', es: 'Analista', en: 'Analyst', role_es: 'Fundamentales', role_en: 'Fundamentals',
      does_es: 'Lee los estados financieros y calcula crecimiento, márgenes, flujo de caja, valuación y dilución; compara con empresas parecidas.',
      does_en: 'Reads the financial statements and computes growth, margins, cash flow, valuation and dilution; compares with similar companies.',
      data_es: ['Estados financieros anuales (FMP / Yahoo / Alpha Vantage)', 'Perfil en vivo (Yahoo / Finnhub)', 'Ratios calculados', 'Comparables', 'Presentaciones a la SEC', 'Noticias'],
      data_en: ['Annual financial statements (FMP / Yahoo / Alpha Vantage)', 'Live profile (Yahoo / Finnhub)', 'Computed ratios', 'Peers', 'SEC filings', 'News'],
      outputs_es: ['Conclusiones con evidencia', 'En una mirada'], outputs_en: ['Evidence-backed conclusions', 'At a glance'],
      research_types: ['fundamental', 'macro'], tools: [], windows: ['glance'] },
    { id: 'radar', es: 'Radar', en: 'Radar', role_es: 'Noticias y eventos', role_en: 'News & events',
      does_es: 'Vigila noticias, presentaciones a la SEC y eventos geopolíticos, y separa lo que de verdad mueve a la empresa del ruido.',
      does_en: 'Watches news, SEC filings and geopolitical events, and separates what really moves the company from the noise.',
      data_es: ['Noticias (GDELT / Finnhub)', 'Presentaciones a la SEC', 'Catálogo y cadena de suministro'],
      data_en: ['News (GDELT / Finnhub)', 'SEC filings', 'Catalog and supply chain'],
      outputs_es: ['Conclusiones de corto plazo', 'Eventos que la afectan'], outputs_en: ['Short-term conclusions', 'Events that affect it'],
      research_types: ['news', 'geopolitical', 'crypto'], tools: [], windows: [] },
    { id: 'cadena', es: 'Cadena', en: 'Chain', role_es: 'Cadena de suministro', role_en: 'Supply chain',
      does_es: 'Recorre la cadena de suministro: de quién depende la empresa, a quién le vende y por dónde le puede llegar un golpe.',
      does_en: 'Walks the supply chain: who the company depends on, who it sells to and where a shock could come from.',
      data_es: ['Grafo de la cadena de suministro', 'Catálogo de empresas', 'Noticias', 'Perfil en vivo'],
      data_en: ['Supply-chain graph', 'Company catalog', 'News', 'Live profile'],
      outputs_es: ['Cadena de suministro', 'Riesgos de dependencia'], outputs_en: ['Supply chain', 'Dependency risks'],
      research_types: ['supply_chain'], tools: [], windows: ['supplychain'] },
    { id: 'tecnico', es: 'Técnico', en: 'Technical', role_es: 'Precio y momento', role_en: 'Price & momentum',
      does_es: 'Mira el precio: tendencia (medias de 50 y 200 días), RSI, máximos y mínimos de 52 semanas, caídas máximas y fuerza frente al S&P 500.',
      does_en: 'Looks at price: trend (50- and 200-day averages), RSI, 52-week highs and lows, max drawdowns and strength vs the S&P 500.',
      data_es: ['Precios diarios de 1 año (Yahoo)', 'Indicadores calculados', 'Perfil en vivo', 'Noticias'],
      data_en: ['1-year daily prices (Yahoo)', 'Computed indicators', 'Live profile', 'News'],
      outputs_es: ['Tendencia y momento', 'Riesgo de precio'], outputs_en: ['Trend and momentum', 'Price risk'],
      research_types: ['technical', 'risk_observation'], tools: [], windows: [] },
    { id: 'comite', es: 'Comité', en: 'Committee', role_es: 'Decisiones', role_en: 'Decisions',
      does_es: 'Reúne las conclusiones de todos, las pesa por confianza e historial real y propone una decisión con un tamaño según la volatilidad. Solo propone: tú apruebas.',
      does_en: 'Gathers everyone\'s conclusions, weighs them by confidence and real track record and proposes a decision sized by volatility. It only proposes: you approve.',
      data_es: ['Conclusiones de los analistas', 'Historial de aciertos', 'Precio en vivo', 'Riesgo (volatilidad, caída máxima, VaR)', 'Tu mandato'],
      data_en: ['Analyst conclusions', 'Hit record', 'Live price', 'Risk (volatility, max drawdown, VaR)', 'Your mandate'],
      outputs_es: ['Convicción −100 a +100', 'Memo del comité', 'Propuesta para aprobar'], outputs_en: ['Conviction −100 to +100', 'Committee memo', 'Proposal to approve'],
      research_types: ['committee'], tools: [], windows: ['conviction'] }
  ];
  var AGENT_ORDER = AGENTS.map(function (a) { return a.id; });
  // menciones que el servidor entiende (research/ask_agent.SEAT_WORDS)
  var MENTION = { analista: ['@fundamental', '@fundamental'], radar: ['@noticias', '@news'], cadena: ['@cadena', '@supply'],
    tecnico: ['@tecnico', '@technical'], comite: ['@comite', '@committee'], khipu: ['', ''] };
  var WIN_NAME = { glance: ['En una mirada', 'At a glance'], supplychain: ['Cadena de suministro', 'Supply chain'],
    conviction: ['Convicción de tus agentes', 'Your agents\' conviction'], agents: ['Tus agentes', 'Your agents'] };

  /* ── red: JSON con tiempo límite, caché corta y peticiones en vuelo compartidas
        (la pizarra la piden a la vez «en una mirada» y «convicción»: una sola llamada) ── */
  var CACHE = {};
  function getJSON(url, ttl, timeoutMs) {
    var now = Date.now(), c = CACHE[url];
    if (c && (c.pending || now - c.t < c.ttl)) return c.p;
    var ctl = typeof AbortController !== 'undefined' ? new AbortController() : null;
    var timer = ctl ? setTimeout(function () { try { ctl.abort(); } catch (e) {} }, timeoutMs || 15000) : null;
    var entry = { t: now, ttl: ttl || 30000, pending: true };
    entry.p = fetch(url, { headers: { Accept: 'application/json' }, credentials: 'same-origin', signal: ctl ? ctl.signal : undefined })
      .then(function (r) {
        return r.text().then(function (txt) {
          var data = null;
          try { data = txt ? JSON.parse(txt) : null; } catch (e) { data = null; }
          if (r.ok && data && typeof data === 'object') return { ok: true, status: r.status, data: data };
          return { ok: false, status: r.status, data: data, offline: !!(data && data.offline),
            error: (data && (lang() === 'en' ? (data.error_en || data.error) : data.error)) || ('HTTP ' + r.status) };
        });
      }, function (e) {
        return { ok: false, status: 0, error: (e && e.name === 'AbortError') ? L('el servidor tardó demasiado', 'the server took too long') : L('sin conexión con el servidor', 'no connection to the server') };
      })
      .then(function (res) {
        if (timer) clearTimeout(timer);
        entry.pending = false; entry.t = Date.now();
        if (!res.ok) entry.ttl = Math.min(entry.ttl, 5000);   // un error no se recuerda más de 5 s
        return res;
      });
    CACHE[url] = entry;
    return entry.p;
  }
  function apiEntity(id) { return getJSON('/api/committee/entity/' + encodeURIComponent(id), 30000); }
  function apiMemo(mid) { return getJSON('/api/committee/memo/' + encodeURIComponent(mid), 30000); }
  function apiBoard() { return getJSON('/api/committee/board?limit=80', 60000); }       // el servidor topa en 80
  function apiTensor(id) { return getJSON('/api/tensor/node/' + encodeURIComponent(id), 600000); }
  function apiProfiles() { return getJSON('/api/agents/profiles?lang=' + lang(), 60000); }
  function noDb(r) { return r && !r.ok && r.status === 503; }

  function boardItem(items, id) {
    if (!items || id == null) return null;
    var c = canon(id), low = String(c).toLowerCase();
    for (var i = 0; i < items.length; i++) {
      var e = items[i] && items[i].entity_id;
      if (e == null) continue;
      if (e === c || canon(e) === c || String(e).toLowerCase() === low) return items[i];
    }
    return null;
  }
  // qué filas de la pizarra mostrar sin expandir: las 6 de mayor convicción, la
  // empresa pedida con 2 vecinas a cada lado y las 3 más en contra (con saltos)
  function visibleRows(n, hi, expanded, cap) {
    cap = cap || 14;
    var out = [], i;
    if (expanded || n <= cap) { for (i = 0; i < n; i++) out.push(i); return out; }
    var keep = {};
    for (i = 0; i < 6; i++) keep[i] = 1;
    for (i = n - 3; i < n; i++) keep[i] = 1;
    if (hi != null && hi >= 0) for (i = hi - 2; i <= hi + 2; i++) if (i >= 0 && i < n) keep[i] = 1;
    var gap = 0;
    for (i = 0; i < n; i++) {
      if (keep[i]) { if (gap) { out.push({ gap: gap }); gap = 0; } out.push(i); } else gap++;
    }
    if (gap) out.push({ gap: gap });
    return out;
  }
  // pros/contras ESTRUCTURALES (tensor de flujo) — no son opiniones: se rotulan así
  function structPC(t, lg) {
    var pros = [], cons = [];
    if (!t) return { pros: pros, cons: cons };
    lg = lg === 'en' || lg === 'es' ? lg : lang();
    var en = lg === 'en';
    var sc = t.supplier_concentration || {}, top = (sc.top || [])[0];
    if (top && +top.share_pct >= 25) {
      cons.push({ t: en ? 'Relies ' + fmtPct(top.share_pct, lg, 0, false) + ' on ' + top.label + ' among its suppliers.'
                        : 'Depende en ' + fmtPct(top.share_pct, lg, 0, false) + ' de ' + top.label + ' entre sus proveedores.',
                  who: en ? 'supplier concentration' : 'concentración de proveedores' });
    }
    var ups = (t.upstream_risk_sources || []).filter(function (u) { return u && +u.exposure_pct >= 10; })
      .sort(function (a, b) { return b.exposure_pct - a.exposure_pct; });
    for (var i = 0; i < ups.length && cons.length < 2; i++) {
      var u = ups[i];
      if (top && +top.share_pct >= 25 && u.id === top.id) continue;
      cons.push({ t: en ? 'If ' + u.label + ' fails, ' + fmtPct(u.exposure_pct, lg, 0, false) + ' of the shock reaches it.'
                        : 'Si ' + u.label + ' falla, le llega el ' + fmtPct(u.exposure_pct, lg, 0, false) + ' del golpe.',
                  who: u.direct ? (en ? 'direct supplier' : 'proveedor directo') : (en ? 'indirect risk' : 'riesgo indirecto') });
    }
    if (sc.level === 'baja' && +sc.n_suppliers >= 3) {
      var mx = top && isFinite(+top.share_pct) ? fmtPct(Math.max(1, Math.ceil(+top.share_pct)), lg, 0, false) : null;
      pros.push({ t: en ? sc.n_suppliers + ' suppliers' + (mx ? ' and none weighs more than ' + mx + ' of its supplier network.' : '; none dominates.')
                        : sc.n_suppliers + ' proveedores' + (mx ? ' y ninguno pesa más del ' + mx + ' de su red de proveedores.' : '; ninguno domina.'),
                  who: en ? 'supplier concentration: low' : 'concentración de proveedores: baja' });
    }
    return { pros: pros, cons: cons };
  }

  /* ── explicadores "?" (engine/explain.js) ───────────────────────────────── */
  var EXPL = {
    os_conviction: {
      es: { t: 'Convicción de tus agentes (−100 a +100)',
        b: 'Resume lo que concluyeron tus agentes de IA sobre una empresa, cada conclusión con su evidencia citada. ' +
           '<b>A favor suma y en contra resta</b>; cada conclusión pesa según su confianza y el historial REAL del agente que la escribió. ' +
           'Con poca evidencia el número se queda cerca de 0, y si las conclusiones se contradicen se recorta.' +
           '<ul style="margin:10px 0;padding-left:20px;line-height:1.7"><li><b>+35 o más</b>: el comité puede proponer comprar.</li>' +
           '<li><b>Entre −20 y +35</b>: mantener o esperar.</li><li><b>−20 o menos</b>: reducir · <b>−50 o menos</b>: vender.</li></ul>' +
           'Cuando dice <b>«sin comité aún»</b> es el cálculo con las conclusiones vigentes, sin que el comité haya deliberado. ' +
           '<b>No es la probabilidad de ganar dinero ni una recomendación personal</b>, y nada se compra sin tu aprobación.' },
      en: { t: 'Your agents\' conviction (−100 to +100)',
        b: 'Summarizes what your AI agents concluded about a company, each conclusion with its cited evidence. ' +
           '<b>For adds and against subtracts</b>; each conclusion weighs by its confidence and the REAL track record of the agent that wrote it. ' +
           'With little evidence the number stays near 0, and if conclusions contradict each other it is cut.' +
           '<ul style="margin:10px 0;padding-left:20px;line-height:1.7"><li><b>+35 or more</b>: the committee may propose buying.</li>' +
           '<li><b>Between −20 and +35</b>: hold or wait.</li><li><b>−20 or less</b>: trim · <b>−50 or less</b>: sell.</li></ul>' +
           'When it says <b>"no committee yet"</b> it is computed from the current conclusions, before the committee deliberated. ' +
           '<b>It is not the probability of making money nor a personal recommendation</b>, and nothing is bought without your approval.' } },
    os_track: {
      es: { t: 'Historial de un agente (tasa de acierto)',
        b: 'Cada conclusión de un agente se califica con <b>precios reales</b> cuando vence su plazo: se compara el retorno de la acción con el del S&amp;P 500 (SPY). ' +
           'Las de corto plazo se miden a los <b>20 días hábiles</b> de la bolsa de Nueva York; las de mediano y largo plazo tardan meses. ' +
           '<b>Tasa de acierto</b> = cuántas se cumplieron de las ya calificadas. Hasta tener al menos <b>5</b> calificaciones finales decimos ' +
           '<b>«sin historial suficiente todavía»</b>: con tan pocos casos un porcentaje engaña. Mientras tanto el comité usa a ese agente con peso neutral ' +
           'y propone la mitad del tamaño.' },
      en: { t: 'An agent\'s track record (hit rate)',
        b: 'Each of an agent\'s conclusions is scored with <b>real prices</b> when its horizon comes due: the stock\'s return is compared with the S&amp;P 500 (SPY). ' +
           'Short-term ones are measured after <b>20 NYSE business days</b>; medium- and long-term ones take months. ' +
           '<b>Hit rate</b> = how many came true among those already scored. Until there are at least <b>5</b> final scores we say ' +
           '<b>"not enough history yet"</b>: with so few cases a percentage misleads. Meanwhile the committee gives that agent a neutral weight ' +
           'and proposes half the size.' } }
  };
  var _explOK = false;
  function ensureExplain() {
    if (_explOK || typeof window.explainRegister !== 'function') return;
    try { Object.keys(EXPL).forEach(function (k) { window.explainRegister(k, EXPL[k]); }); _explOK = true; } catch (e) {}
  }
  function qChip(key) {
    var tip = L('¿Qué es esto?', 'What is this?');
    return '<button type="button" class="osw-q" data-act="explain" data-key="' + esc(key) + '" aria-label="' + esc(tip) + '" title="' + esc(tip) + '">?</button>';
  }

  /* ── estilos (solo tokens --os-*; el tema lo pone la Cabina sobre #bcp-ov) ── */
  var CSS = '' +
    '.osw{--km-ring:var(--os-surface);position:relative;display:flex;flex-direction:column;gap:14px;min-width:0;font-family:var(--os-font);font-size:14px;line-height:1.45;' +
      'color:var(--os-ink);font-variant-numeric:tabular-nums;-webkit-font-smoothing:antialiased;text-align:left}' +
    '.osw *{box-sizing:border-box}.osw [hidden]{display:none!important}' +
    '.osw.osw-solo{width:100%;max-width:780px;margin:0 auto;padding:22px 20px}' +
    '.osw button{font-family:inherit}' +
    '.osw-hd{display:flex;align-items:center;gap:10px;min-width:0}' +
    /* dentro de una ventana del escritorio la barra de la ventana YA muestra mascota + título (como la tarjeta del
       video): se oculta el título repetido de adentro y queda solo lo extra (p. ej. "X-Ray ›"), alineado a la derecha */
    '.kd-body.kos-native .osw-hd>h3,.kd-body.kos-native .osw-hd>.km,.kd-body.kos-native .osw-hd>.km-stack,.kd-body.kos-native .osw-hd>.osw-mstack,.kd-body.kos-native .osw-hd>.osw-dot,.kd-body.kos-native .osw-hd>.osw-mdot{display:none!important}' +
    '.kd-body.kos-native .osw-hd{justify-content:flex-end;min-height:0}' +
    '.kd-body.kos-native .osw-hd:not(:has(>:not(h3):not(.km):not(.km-stack):not(.osw-mstack):not(.osw-dot):not(.osw-mdot))){display:none!important}' +
    '.kd-win:has(>.kd-body.kos-native) .kd-name{font-size:16px;color:var(--os-ink);font-weight:600}' +
    '.osw-hd h3{margin:0;flex:1;min-width:0;font-size:16px;font-weight:600;letter-spacing:-.01em;color:var(--os-ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
    '.osw[data-w=xs] .osw-hd h3{white-space:normal;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;line-height:1.25}' +
    '.osw-hd .km-stack,.osw-hd .osw-mstack{flex:none}' +
    // mascot.js solapa con margin-left:-28% (relativo al CONTENEDOR): en una fila flexible eso
    // se va al ancho del encabezado; aquí se fija en píxeles
    '.osw .km-stack .km{margin-left:-7px}.osw .km-stack .km:first-child{margin-left:0}' +
    '.osw-tip .km-stack .km{margin-left:-5px}.osw-tip .km-stack .km:first-child{margin-left:0}' +
    '.osw-mdot{display:inline-block;border-radius:50%;flex:none;vertical-align:middle}' +
    '.osw-mstack{display:inline-flex}.osw-mstack .osw-mdot{margin-left:-6px;box-shadow:0 0 0 2px var(--os-surface)}.osw-mstack .osw-mdot:first-child{margin-left:0}' +
    '.osw-sub{font-size:12.5px;color:var(--os-ink-2);margin-top:-6px}' +
    '.osw-kick{display:flex;align-items:center;gap:6px;font-size:12.5px;color:var(--os-ink-2);font-weight:500}' +
    '.osw-mut{color:var(--os-ink-3)}' +
    '.osw-q{appearance:none;-webkit-appearance:none;display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;padding:0;border-radius:50%;' +
      'border:1px solid var(--os-line);background:var(--os-surface-2);color:var(--os-ink-3);font-size:10px;font-weight:700;line-height:1;cursor:pointer;flex:none}' +
    '.osw-q:hover{color:var(--os-accent);border-color:var(--os-accent)}' +
    '.osw-foot .osw-q,.osw-sub .osw-q,.osw-gl-conv2 .osw-q{margin-left:3px;vertical-align:-3px;display:inline-flex}' +
    '.osw-q:focus-visible,.osw-btn:focus-visible,.osw-link:focus-visible,.osw-sw:focus-visible,.osw-seg button:focus-visible,.osw-cv-row:focus-visible,.osw-sc-pill:focus-visible{outline:2px solid var(--os-accent);outline-offset:2px}' +
    '.osw-vh{position:absolute!important;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}' +
    // botones
    '.osw-btns{display:flex;flex-wrap:wrap;align-items:center;gap:10px}' +
    '.osw-btn{appearance:none;-webkit-appearance:none;border:0;cursor:pointer;height:42px;padding:0 20px;border-radius:999px;font-size:14px;font-weight:600;letter-spacing:-.005em;' +
      'background:var(--os-surface-2);color:var(--os-ink);transition:background-color .15s ease,transform .1s ease,opacity .15s ease;white-space:nowrap}' +
    '.osw-btn:hover{background:var(--os-surface-3)}.osw-btn:active{transform:scale(.98)}' +
    '.osw-btn.pri{background:var(--os-btn);color:var(--os-btn-ink)}.osw-btn.pri:hover{opacity:.88}' +
    '.osw-btn.sm{height:32px;padding:0 14px;font-size:12.5px}' +
    '.osw-btns .osw-btn{flex:1 1 auto;padding:0 18px}' +
    '.osw-btns .osw-btn.auto{flex:0 0 auto}' +
    '.osw-link{appearance:none;-webkit-appearance:none;border:0;background:none;padding:6px 4px;cursor:pointer;color:var(--os-accent);font-size:13px;font-weight:600;white-space:nowrap}' +
    '.osw-link:hover{text-decoration:underline}' +
    // píldoras
    '.osw-pill{display:inline-flex;align-items:center;gap:6px;padding:7px 14px;border-radius:999px;font-size:13px;font-weight:600;white-space:nowrap;' +
      'color:var(--os-accent);background:var(--os-surface-2);background:color-mix(in srgb,var(--os-accent) 12%,transparent)}' +
    '.osw-pill.neu{color:var(--os-ink-2);background:var(--os-surface-2)}' +
    '.osw-pill.neg{color:var(--os-neg);background:var(--os-surface-2);background:color-mix(in srgb,var(--os-neg) 12%,transparent)}' +
    // esqueletos
    '.osw-sk{display:block;border-radius:8px;background:var(--os-surface-2);background:linear-gradient(90deg,var(--os-surface-2) 0%,var(--os-surface-3) 50%,var(--os-surface-2) 100%);' +
      'background-size:200% 100%;animation:osw-sh 1.3s ease-in-out infinite}' +
    '@keyframes osw-sh{0%{background-position:100% 0}100%{background-position:-100% 0}}' +
    '.osw-skl{display:flex;flex-direction:column;gap:10px}' +
    // pie
    '.osw-foot{font-size:11.5px;line-height:1.55;color:var(--os-ink-3);border-top:1px solid var(--os-line);padding-top:10px}' +
    '.osw-foot b{font-weight:600;color:var(--os-ink-2)}' +
    '.osw-empty{padding:14px 2px 4px;color:var(--os-ink-2);font-size:14px;line-height:1.55}' +
    '.osw-empty b{color:var(--os-ink)}' +
    // ── en una mirada
    '.osw-gl-quote{display:flex;flex-wrap:wrap;align-items:center;gap:4px 8px;font-size:12.5px;color:var(--os-ink-2);margin-top:-4px}' +
    '.osw-gl-quote .tk{font-weight:600;color:var(--os-ink)}' +
    '.osw-gl-quote .px{font-weight:600;color:var(--os-ink)}' +
    '.osw-up{color:var(--os-good)}.osw-dn{color:var(--os-bad)}.osw-flat{color:var(--os-ink-2)}' +
    '.osw-gl-main{display:flex;align-items:center;justify-content:space-between;gap:12px 16px;flex-wrap:wrap;min-height:96px;padding-top:4px}' +
    '.osw-gl-l{display:flex;flex-direction:column;gap:2px;min-width:0}' +
    '.osw-gl-r{display:flex;flex-direction:column;align-items:flex-end;gap:6px;min-width:0}' +
    '.osw-gl-cap{font-size:11.5px;color:var(--os-ink-3);text-align:right}' +
    '.osw-big{font-size:68px;font-weight:700;letter-spacing:-.045em;line-height:1;color:var(--os-accent);white-space:nowrap}' +
    '.osw-big.ink{color:var(--os-ink);font-size:48px;letter-spacing:-.035em}' +
    '.osw-big.mut{color:var(--os-ink-2)}' +
    '.osw-big.txt{font-size:24px;letter-spacing:-.01em;font-weight:600;color:var(--os-ink-2);white-space:normal}' +
    '.osw-gl-chg{font-size:13px;font-weight:600;margin-top:4px}' +
    '.osw-gl-chg .osw-mut{font-weight:500}' +
    '.osw-gl-conv2{display:flex;flex-wrap:wrap;align-items:center;gap:6px;font-size:13px;color:var(--os-ink-2);padding:9px 12px;border-radius:var(--os-r-sm);background:var(--os-surface-2)}' +
    '.osw-gl-conv2 b{color:var(--os-ink);font-weight:700}' +
    '.osw-pc-lab{font-size:11.5px;color:var(--os-ink-3);margin:0 0 8px}' +
    '.osw-pc{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:14px}' +
    '.osw-pc li{display:flex;align-items:flex-start;gap:12px;font-size:14px;line-height:1.45;color:var(--os-ink)}' +
    '.osw-sg{flex:none;display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:50%;font-size:14px;font-weight:700;line-height:1;margin-top:-1px}' +
    '.osw-sg.p{color:var(--os-accent);background:var(--os-surface-2);background:color-mix(in srgb,var(--os-accent) 13%,transparent)}' +
    '.osw-sg.m{color:var(--os-neg);background:var(--os-surface-2);background:color-mix(in srgb,var(--os-neg) 13%,transparent)}' +
    '.osw-pc-t{min-width:0;display:flex;flex-direction:column;gap:2px}' +
    '.osw-clamp{display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}' +
    '.osw-pc-who{font-size:11.5px;color:var(--os-ink-3)}' +
    // ── convicción
    '.osw-cv-axis,.osw-cv-row{display:grid;grid-template-columns:minmax(72px,.95fr) minmax(150px,2.6fr) 54px;align-items:center;gap:10px}' +
    '.osw-cv-axis{font-size:11px;color:var(--os-ink-3);padding:0 10px;margin-bottom:-4px}' +
    '.osw-cv-axis .ax{position:relative;height:16px}' +
    '.osw-cv-axis .ax span{position:absolute;top:0;white-space:nowrap}' +
    '.osw-cv-axis .ax .a0{left:50%;transform:translateX(-50%)}' +
    '.osw-cv-axis .ax .al{right:calc(50% + 14px)}' +
    '.osw-cv-axis .ax .ar{left:calc(50% + 14px)}' +
    '.osw-cv-rows{display:flex;flex-direction:column;gap:2px;position:relative}' +
    '.osw-cv-row{appearance:none;-webkit-appearance:none;width:100%;border:0;background:none;color:inherit;font-size:13.5px;text-align:left;height:31px;padding:0 10px;border-radius:10px;cursor:pointer}' +
    '.osw-cv-row:hover{background:var(--os-surface-2)}' +
    '.osw-cv-row.hi{background:var(--os-surface-2)}' +
    '.osw-cv-row.hi .osw-cv-name,.osw-cv-row.hi .osw-cv-val{font-weight:700;color:var(--os-ink)}' +
    '.osw-cv-name{min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--os-ink)}' +
    '.osw-cv-val{text-align:right;color:var(--os-ink-2);white-space:nowrap}' +
    '.osw-cv-track{position:relative;height:31px}' +
    '.osw-cv-track:before{content:"";position:absolute;left:50%;top:-1px;bottom:-1px;width:1px;background:var(--os-line)}' +
    '.osw-cv-bar{position:absolute;top:7px;height:17px;border-radius:4px;width:0;min-width:2px;transition:width .7s cubic-bezier(.2,.8,.2,1)}' +
    '.osw-cv-bar.pos{left:50%}.osw-cv-bar.neg{right:50%}' +
    '.osw-cv-rows.on .osw-cv-bar{width:var(--w)}' +
    '.osw-cv-bar.t-pos{background:var(--os-pos)}.osw-cv-bar.t-neg{background:var(--os-neg)}.osw-cv-bar.t-mute{background:var(--os-mute)}' +
    '.osw-cv-gap{font-size:11.5px;color:var(--os-ink-3);padding:2px 10px;letter-spacing:.2em}' +
    '.osw-cv-gap span{letter-spacing:0;margin-left:6px}' +
    '.osw-cv-miss{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px 12px;padding:10px 12px;border-radius:var(--os-r-sm);background:var(--os-surface-2);font-size:13px;color:var(--os-ink-2)}' +
    '.osw-cv-miss b{color:var(--os-ink)}' +
    '.osw-tip{position:absolute;z-index:5;pointer-events:none;min-width:190px;max-width:270px;padding:10px 12px;border-radius:12px;background:var(--os-surface);' +
      'border:1px solid var(--os-line);box-shadow:var(--os-shadow);font-size:12px;line-height:1.5;color:var(--os-ink-2)}' +
    '.osw-tip b{color:var(--os-ink)}' +
    '.osw-tip .r{display:flex;justify-content:space-between;gap:12px}.osw-tip .r span:last-child{color:var(--os-ink);font-weight:600}' +
    '.osw-tip .hd{display:flex;justify-content:space-between;gap:12px;margin-bottom:4px;font-size:12.5px}' +
    '.osw-tip .ag{display:flex;align-items:center;gap:6px;margin-top:6px}' +
    '.osw-lg{display:inline-flex;align-items:center;gap:5px;margin-right:12px;white-space:nowrap}' +
    '.osw-lg i{display:inline-block;width:14px;height:6px;border-radius:3px}' +
    '.osw-lg i.pos{background:var(--os-pos)}.osw-lg i.mute{background:var(--os-mute)}.osw-lg i.neg{background:var(--os-neg)}' +
    '.osw-lg i.dash{height:0;border-top:2px dashed var(--os-mute);border-radius:0}' +
    // ── cadena de suministro
    '.osw-sc{display:grid;grid-template-columns:minmax(0,1fr) 120px minmax(0,1fr);align-items:start;gap:10px}' +
    '.osw-sc-col{display:flex;flex-direction:column;gap:8px;min-width:0}' +
    '.osw-sc-h{display:flex;align-items:baseline;gap:6px;font-size:11.5px;color:var(--os-ink-3);font-weight:500}' +
    '.osw-sc-col.c .osw-sc-h{justify-content:flex-end}' +
    '.osw-sc-row{display:flex;align-items:center;gap:10px;min-width:0;height:34px}' +
    '.osw-sc-pill{appearance:none;-webkit-appearance:none;border:0;flex:0 1 auto;min-width:0;max-width:62%;height:34px;padding:0 14px;border-radius:999px;cursor:pointer;' +
      'background:var(--os-surface-2);color:var(--os-ink);font-size:13.5px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;transition:background-color .15s ease}' +
    '.osw-sc-pill:hover{background:var(--os-surface-3)}' +
    '.osw-sc-pill.risk{color:var(--os-neg);background:var(--os-surface-2);background:color-mix(in srgb,var(--os-neg) 13%,transparent)}' +
    '.osw-sc-wire{position:relative;flex:1 1 auto;min-width:28px;height:12px}' +
    '.osw-sc-wire:before{content:"";position:absolute;left:0;right:0;top:50%;height:1px;background:var(--os-line)}' +
    '.osw-sc-wire.unv:before{height:0;border-top:1px dashed var(--os-mute);background:none}' +
    '.osw-sc-seg{position:absolute;top:50%;height:5px;margin-top:-2.5px;border-radius:3px;background:var(--os-mute);min-width:6px}' +
    '.osw-sc-col.s .osw-sc-seg{right:0}.osw-sc-col.c .osw-sc-seg{left:0}' +
    '.osw-sc-seg.risk{background:var(--os-neg)}' +
    '.osw-sc-mid{display:flex;align-items:center;justify-content:center;align-self:stretch;min-height:120px}' +
    '.osw-sc-core{appearance:none;-webkit-appearance:none;border:0;cursor:pointer;width:108px;height:108px;border-radius:50%;display:flex;align-items:center;justify-content:center;text-align:center;' +
      'padding:12px;background:var(--os-btn);color:var(--os-btn-ink);font-size:15px;font-weight:600;line-height:1.2;letter-spacing:-.01em;box-shadow:var(--os-shadow);overflow:hidden;word-break:break-word}' +
    '.osw-sc-more{align-self:flex-start}.osw-sc-col.c .osw-sc-more{align-self:flex-end}' +
    // oscuro: un disco blanco encandila; se eleva con la superficie 3 y un anillo sutil
    'body.dark .osw-sc-core{background:var(--os-surface-3);color:var(--os-ink);box-shadow:0 0 0 1px var(--os-line),var(--os-shadow)}' +
    '.osw-sc-note{font-size:12.5px;color:var(--os-ink-2);display:flex;flex-wrap:wrap;align-items:center;gap:6px}' +
    '.osw-sc-note b{color:var(--os-ink)}' +
    // apilado (ventanas angostas / móvil)
    '.osw[data-w=xs] .osw-sc,.osw[data-w=sm] .osw-sc{grid-template-columns:minmax(0,1fr);gap:14px}' +
    '.osw[data-w=xs] .osw-sc-mid,.osw[data-w=sm] .osw-sc-mid{order:0}' +
    '.osw[data-w=xs] .osw-sc-col.s,.osw[data-w=sm] .osw-sc-col.s{order:-1}' +
    '.osw[data-w=xs] .osw-sc-col.c,.osw[data-w=sm] .osw-sc-col.c{order:1}' +
    '.osw[data-w=xs] .osw-sc-core,.osw[data-w=sm] .osw-sc-core{width:88px;height:88px;font-size:14px}' +
    '.osw[data-w=xs] .osw-sc-row.r,.osw[data-w=sm] .osw-sc-row.r{flex-direction:row-reverse}' +
    '.osw[data-w=xs] .osw-sc-col.c .osw-sc-h,.osw[data-w=sm] .osw-sc-col.c .osw-sc-h{justify-content:flex-start}' +
    '.osw[data-w=xs] .osw-sc-col.s .osw-sc-seg,.osw[data-w=sm] .osw-sc-col.s .osw-sc-seg{left:0;right:auto}' +
    '.osw[data-w=xs] .osw-sc-col.c .osw-sc-more,.osw[data-w=sm] .osw-sc-col.c .osw-sc-more{align-self:flex-start}' +
    '.osw[data-w=xs] .osw-big{font-size:56px}.osw[data-w=xs] .osw-big.ink{font-size:40px}' +
    '.osw[data-w=xs] .osw-gl-r{align-items:flex-start}.osw[data-w=xs] .osw-gl-cap{text-align:left}' +
    '.osw[data-w=xs] .osw-cv-axis,.osw[data-w=xs] .osw-cv-row{grid-template-columns:minmax(64px,1fr) minmax(120px,1.8fr) 48px;gap:8px}' +
    '.osw[data-w=xs] .osw-cv-axis .ax .al,.osw[data-w=xs] .osw-cv-axis .ax .ar{font-size:10px}' +
    // ── tus agentes
    '.osw-seg{display:inline-flex;flex:none;padding:3px;border-radius:999px;background:var(--os-surface-2)}' +
    '.osw-seg button{appearance:none;-webkit-appearance:none;border:0;background:none;cursor:pointer;height:28px;padding:0 14px;border-radius:999px;font-size:12.5px;font-weight:600;color:var(--os-ink-2)}' +
    '.osw-seg button[aria-checked=true]{background:var(--os-surface);color:var(--os-ink);box-shadow:var(--os-shadow)}' +
    '.osw-ag-mode{display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;font-size:12.5px;color:var(--os-ink-2)}' +
    '.osw-ag-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:12px}' +
    '.osw-ag{display:flex;flex-direction:column;gap:10px;padding:16px;border-radius:16px;border:1px solid var(--os-line);background:var(--os-surface);min-width:0}' +
    '.osw-ag.off{opacity:.62}' +
    '.osw-ag-top{display:flex;align-items:center;gap:12px;min-width:0}' +
    '.osw-ag-id{flex:1;min-width:0}' +
    '.osw-ag-n{font-size:16px;font-weight:700;letter-spacing:-.01em;color:var(--os-ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
    '.osw-ag-r{font-size:12.5px;color:var(--os-ink-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
    '.osw-ag .osw-ask{width:100%;margin-top:2px}' +
    '.osw-ag-does{margin:0;font-size:13px;line-height:1.5;color:var(--os-ink)}' +
    '.osw-ag-k{display:flex;align-items:center;gap:6px;font-size:10.5px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--os-ink-3);margin-bottom:-4px}' +
    '.osw-chips{display:flex;flex-wrap:wrap;gap:6px}' +
    '.osw-chip{display:inline-block;padding:4px 10px;border-radius:10px;background:var(--os-surface-2);color:var(--os-ink-2);font-size:12px;line-height:1.35}' +
    '.osw-chip.out{color:var(--os-accent);background:var(--os-surface-2);background:color-mix(in srgb,var(--os-accent) 10%,transparent)}' +
    '.osw-chip.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px}' +
    '.osw-ag-track{font-size:12.5px;line-height:1.5;color:var(--os-ink-2)}' +
    '.osw-ag-track b{color:var(--os-ink)}' +
    '.osw-ag-cost{font-size:12px;color:var(--os-ink-3)}' +
    '.osw-ag-sws{display:flex;flex-direction:column;gap:8px;border-top:1px solid var(--os-line);padding-top:10px;margin-top:auto}' +
    '.osw-sw{appearance:none;-webkit-appearance:none;display:flex;align-items:center;gap:10px;width:100%;padding:0;border:0;background:none;cursor:pointer;text-align:left;color:var(--os-ink);font-size:13px}' +
    '.osw-sw[disabled]{cursor:default;opacity:.55}' +
    '.osw-sw-t{position:relative;flex:none;width:36px;height:22px;border-radius:999px;background:var(--os-surface-3);transition:background-color .2s ease}' +
    '.osw-sw-t:after{content:"";position:absolute;top:2px;left:2px;width:18px;height:18px;border-radius:50%;background:var(--os-surface);box-shadow:0 0 0 .5px var(--os-line),0 1px 3px var(--os-line);transition:transform .2s ease}' +
    '.osw-sw[aria-checked=true] .osw-sw-t{background:var(--os-accent)}' +
    '.osw-sw[aria-checked=true] .osw-sw-t:after{transform:translateX(14px)}' +
    '.osw-sw-l{min-width:0}' +
    '.osw-sw-l small{display:block;font-size:11.5px;color:var(--os-ink-3)}' +
    '@media (prefers-reduced-motion:reduce){.osw-sk{animation:none}.osw-cv-bar,.osw-sw-t,.osw-sw-t:after,.osw-btn{transition:none}}';
  function ensureCss() {
    if (document.getElementById('osw-css')) return;
    var st = document.createElement('style');
    st.id = 'osw-css';
    st.textContent = CSS;
    (document.head || document.documentElement).appendChild(st);
  }

  /* ── instancias (una por cuerpo de ventana) ─────────────────────────────── */
  var INST = [];
  var SEQ = 0;
  var SIZES = [400, 560, 820], SIZE_N = ['xs', 'sm', 'md', 'lg'];
  function sizeIdx(w) { for (var i = 0; i < SIZES.length; i++) if (w < SIZES[i]) return i; return SIZES.length; }
  // con histéresis: una barra de desplazamiento que aparece/desaparece no hace oscilar el diseño
  function sizeClass(root, w) {
    if (!w) return;
    var cur = SIZE_N.indexOf(root.getAttribute('data-w')), ni = sizeIdx(w);
    if (cur >= 0 && ni !== cur) {
      var b = SIZES[Math.min(ni, cur)];
      if (Math.abs(w - b) < 14) return;
    }
    if (ni !== cur) root.setAttribute('data-w', SIZE_N[ni]);
  }
  var RO = null;
  try {
    if (typeof ResizeObserver !== 'undefined') {
      // el cambio de clase va FUERA de la entrega del observador (siguiente cuadro):
      // cambiar el diseño dentro del callback dispara «ResizeObserver loop…» (la app lo
      // muestra como error)
      var pend = [], sched = false;
      var flush = function () {
        sched = false;
        var list = pend; pend = [];
        for (var i = 0; i < list.length; i++) if (list[i].t.isConnected) sizeClass(list[i].t, list[i].w);
      };
      RO = new ResizeObserver(function (ents) {
        for (var i = 0; i < ents.length; i++) pend.push({ t: ents[i].target, w: ents[i].contentRect.width });
        if (sched) return;
        sched = true;
        if (!document.hidden && typeof requestAnimationFrame === 'function') requestAnimationFrame(flush); else setTimeout(flush, 0);
      });
    }
  } catch (e) { RO = null; }

  function prune() {
    for (var i = INST.length - 1; i >= 0; i--) {
      if (!alive(INST[i])) { try { if (RO) RO.unobserve(INST[i].root); } catch (e) {} INST.splice(i, 1); }
    }
  }
  function alive(inst) { return !!(inst && inst.root && inst.root.isConnected && inst.root.parentNode === inst.body && inst.body.__oswInst === inst); }
  function mount(kind, body, arg) {
    ensureCss(); ensureExplain(); prune();
    var prev = body.__oswInst, quiet = !!(prev && prev.kind === kind && sameArg(prev.arg, arg) && body.__oswQuiet);
    body.__oswQuiet = false;
    body.innerHTML = '';
    var root = document.createElement('div');
    var solo = !(body.classList && body.classList.contains('kd-body'));
    root.className = 'osw osw-' + kind + (solo ? ' osw-solo' : '');
    root.setAttribute('data-osw', kind);
    body.appendChild(root);
    var inst = { body: body, root: root, kind: kind, arg: arg, tok: ++SEQ, quiet: quiet, st: {} };
    body.__oswInst = inst;
    INST.push(inst);
    // tamaño: se hereda del repintado anterior (medir aquí, con la ventana vacía, forzaría
    // un layout que lleva el scroll a 0); el ResizeObserver lo corrige enseguida
    var pw = prev && prev.root && prev.root.getAttribute('data-w');
    if (pw) root.setAttribute('data-w', pw);
    else sizeClass(root, body.clientWidth || 600);
    if (RO) { try { RO.observe(root); } catch (e) {} }
    wire(inst);
    return inst;
  }
  function sameArg(a, b) { return argId(a) === argId(b); }
  function q(inst, sel) { return inst.root.querySelector(sel); }
  function put(el, html) { if (el && el.__oswH !== html) { el.__oswH = html; el.innerHTML = html; } }
  function header(mid, title, extra) {
    return '<div class="osw-hd">' + mascot(mid, 22) + '<h3 title="' + esc(title) + '">' + esc(title) + '</h3>' + (extra || '') + '</div>';
  }
  function skLines(n, h) {
    var s = '<div class="osw-skl" aria-hidden="true">';
    for (var i = 0; i < n; i++) s += '<span class="osw-sk" style="height:' + (h || 14) + 'px;width:' + (92 - i * 17) + '%"></span>';
    return s + '</div>';
  }

  /* ── acciones (delegadas por ventana) ───────────────────────────────────── */
  function ck() { return window.BixbyCockpit || null; }
  function ckOpen() { var c = ck(); try { return !!(c && typeof c.isOpen === 'function' && c.isOpen()); } catch (e) { return false; } }
  function openXRay(id) {
    var c = ck();
    if (c && ckOpen() && typeof c.stage === 'function') { c.stage('xray', id); return; }
    if (typeof window.openXRay === 'function') window.openXRay(id);
  }
  function openCommittee(id) { if (window.KhipuCommittee && typeof window.KhipuCommittee.open === 'function') window.KhipuCommittee.open(id); }
  function openResearch(id) { if (window.KhipuResearch && typeof window.KhipuResearch.open === 'function') window.KhipuResearch.open(id); }
  function askAgent(aid) {
    var m = MENTION[aid], txt = m ? (lang() === 'en' ? m[1] : m[0]) : '';
    function put() {
      var inp = document.getElementById('bcp-input');
      if (!inp) return false;
      inp.value = txt ? txt + ' ' : '';
      try { inp.dispatchEvent(new Event('input', { bubbles: true })); } catch (e) {}
      try { inp.focus(); var n = inp.value.length; inp.setSelectionRange(n, n); } catch (e) {}
      return true;
    }
    if (put()) return;
    var c = ck();
    if (c && typeof c.open === 'function') { try { c.open(); } catch (e) {} setTimeout(put, 120); }
  }
  function wire(inst) {
    var root = inst.root;
    root.addEventListener('click', function (ev) {
      var t = ev.target && ev.target.closest ? ev.target.closest('[data-act]') : null;
      if (!t || !root.contains(t) || t.disabled) return;
      var act = t.getAttribute('data-act'), id = t.getAttribute('data-id') || (inst.st && inst.st.id);
      if (act === 'explain') { ensureExplain(); if (typeof window.explainMetric === 'function') window.explainMetric(t.getAttribute('data-key')); return; }
      if (act === 'committee') { if (id) openCommittee(id); return; }
      if (act === 'research') { if (id) openResearch(id); return; }
      if (act === 'xray') { if (id) openXRay(id); return; }
      if (act === 'glance') { if (id) open('glance', { id: id }); return; }
      if (act === 'chain') { if (id) open('supplychain', { id: id }); return; }
      if (act === 'retry') { CACHE = {}; render(inst.kind, inst.body, inst.arg); return; }
      if (act === 'expand') { inst.st.expanded = !inst.st.expanded; paintConviction(inst); return; }
      if (act === 'more') { var sd = t.getAttribute('data-side'); inst.st.exp[sd] = !inst.st.exp[sd]; paintChain(inst); return; }
      if (act === 'mode') { if (window.KhipuAgentPrefs) window.KhipuAgentPrefs.set({ mode: t.getAttribute('data-mode') }); return; }
      if (act === 'pref') {
        var P = window.KhipuAgentPrefs, aid = t.getAttribute('data-agent'), key = t.getAttribute('data-pref');
        if (!P || !aid || !key) return;
        var patch = { agents: {} };
        patch.agents[aid] = {};
        patch.agents[aid][key] = t.getAttribute('aria-checked') !== 'true';
        P.set(patch);
        return;
      }
      if (act === 'ask') { askAgent(t.getAttribute('data-agent')); return; }
    });
  }

  /* ════════════════════════ «<Empresa> en una mirada» ═══════════════════════ */
  function quoteOfNode(n) {
    var tk = n && n.mkt, MK = window.MKT;
    if (!tk || !MK || !MK.quotes) return { tk: tk || null, q: null, px: 0 };
    var qq = MK.quotes[tk] || null, px = 0;
    if (qq) {
      if (typeof window.quotePx === 'function') { try { px = +window.quotePx(qq) || 0; } catch (e) { px = 0; } }
      else px = +(typeof qq.live === 'number' ? qq.live : qq.close) || 0;
    }
    var pct = null;
    if (qq && qq.pct != null && isFinite(+qq.pct)) pct = +qq.pct;
    else if (qq && px > 0 && +qq.prev > 0) pct = (px - qq.prev) / qq.prev * 100;
    return { tk: tk, q: qq, px: px, pct: pct };
  }
  var _askedQuote = {};
  function ensureQuote(n) {   // sin cotización en memoria: se pide UNA vez (lote de 1, mismo camino que el resto)
    var tk = n && n.mkt;
    if (!tk || _askedQuote[tk] || typeof window.loadLiveQuotes !== 'function') return;
    var qq = quoteOfNode(n);
    if (qq.px > 0) return;
    _askedQuote[tk] = 1;
    try { window.loadLiveQuotes({ tickers: [tk] }); } catch (e) {}
  }
  // Moneda del MONTO de una cotización (contrato de MKT.quotes, igual que xray.js): core/quotes convierte
  // las bolsas no estadounidenses a USD y deja en «currency» la moneda ORIGINAL con converted:true. Un monto
  // convertido se pinta en USD — antes «CN¥14,00» para un precio de ~$14 (≈ CN¥100).
  var MINOR_CUR = { GBp: 'GBP', GBX: 'GBP', ZAc: 'ZAR', ZAC: 'ZAR', ILA: 'ILS' };   // Yahoo: peniques/centavos/agorot
  function quoteCur(q0) { return (q0 && q0.converted) ? 'USD' : String((q0 && q0.currency) || 'USD'); }
  function quoteOrigCur(q0) {   // moneda de la bolsa si el monto se convirtió a USD; '' si no hubo conversión
    if (!q0 || !q0.converted || !q0.currency) return '';
    var c = String(q0.currency);
    c = MINOR_CUR[c] || c.toUpperCase();
    return c === 'USD' ? '' : c;
  }
  function quoteMoney(qq) { return fmtMoney(qq && qq.px, quoteCur(qq && qq.q)); }
  function srcText(qq) {
    var q0 = qq.q;
    if (!q0) return '';
    var name = typeof window.quoteSrcName === 'function' ? window.quoteSrcName(q0.src) : (q0.src || '');
    var sec = null;
    if (typeof window.quoteAge === 'function') { try { sec = window.quoteAge(q0); } catch (e) { sec = null; } }
    else if (q0.as_of) { var t = Date.parse(q0.as_of); if (!isNaN(t)) sec = Math.max(0, Math.round((Date.now() - t) / 1000)); }
    var when = q0.src === 'marketstack' ? L('cierre (EOD)', 'close (EOD)') : agoText(sec);
    var oc = quoteOrigCur(q0), conv = oc ? L('convertido de ' + oc, 'converted from ' + oc) : '';
    return [name, when, conv].filter(Boolean).join(' · ');
  }
  function chgHTML(pct) {
    if (pct == null || !isFinite(pct)) return '';
    var r = Math.round(pct * 100) / 100, cls = r > 0 ? 'osw-up' : r < 0 ? 'osw-dn' : 'osw-flat', ar = r > 0 ? '▲' : r < 0 ? '▼' : '=';
    return '<span class="' + cls + '">' + ar + ' ' + esc(fmtPct(pct, null, 2)) + '</span>';
  }
  // El veredicto de «en una mirada» es el GENERAL de la empresa (client_id nulo: la misma regla que la
  // Pizarra). Un memo corrido para un cliente del corretaje (HOLD por no operable en Alpaca, TRIM por
  // sobrepeso, AVOID por su mandato) es de ESE cliente y nunca se muestra como el veredicto de todos.
  var MEMO_DONE = { proposed: 1, approved: 1, rejected: 1, executed: 1 };   // = latest_memo del servidor
  function isGeneralMemo(m) { return !!(m && typeof m === 'object' && !m.client_id); }
  function generalMemoOf(d) {   // → { memo } o { memo: null, fetchId } (hay que pedir ese memo general)
    if (!d) return { memo: null };
    if (d.latest_general !== undefined) return { memo: isGeneralMemo(d.latest_general) ? d.latest_general : null };
    if (!d.latest || isGeneralMemo(d.latest)) return { memo: d.latest || null };
    var h = d.history || [];
    for (var i = 0; i < h.length; i++) {
      var x = h[i];
      if (x && x.memo_id && x.has_client === false && MEMO_DONE[x.status]) return { memo: null, fetchId: String(x.memo_id) };
    }
    return { memo: null };
  }
  function glanceTitle(label) { return L(label + ' en una mirada', label + ' at a glance'); }

  function renderGlance(body, arg) {
    var inst = mount('glance', body, arg);
    var id0 = argId(arg), node = nodeOf(id0), id = node ? node.id : (id0 || null);
    var st = inst.st = { id: id, node: node, label: labelOf(node, id0 || ''), ent: null, board: null, tensor: null, memo: null, item: null, mainSig: '' };
    var R = inst.root;
    if (!id) {
      R.innerHTML = header('analista', L('En una mirada', 'At a glance')) +
        '<div class="osw-empty">' + esc(L('Dime qué empresa quieres ver: escríbela en el chat («¿Cómo está Nvidia?»).', 'Tell me which company to show: type it in the chat ("How is Nvidia doing?").')) + '</div>';
      return;
    }
    var xr = '<button type="button" class="osw-link" data-act="xray" title="' + esc(L('Radiografía completa de la empresa', 'Full company X-ray')) + '">X-Ray ›</button>';
    R.innerHTML = header('analista', glanceTitle(st.label), xr) +
      '<div class="osw-gl-quote" data-r="quote"></div>' +
      '<div class="osw-gl-main" data-r="main"></div>' +
      '<div class="osw-gl-conv2" data-r="conv2" hidden></div>' +
      '<div data-r="pc"></div>' +
      '<div class="osw-btns" data-r="btns"></div>' +
      '<div class="osw-foot" data-r="foot"></div>';
    ensureQuote(node);
    paintGlance(inst);
    apiEntity(id).then(function (r) {
      if (!alive(inst)) return;
      var g = generalMemoOf(r.ok && r.data ? r.data : null);
      if (!g.fetchId) { setGlanceMemo(inst, r, g.memo); return; }
      apiMemo(g.fetchId).then(function (r2) {   // el último es de un cliente: se trae el último GENERAL
        if (!alive(inst)) return;
        setGlanceMemo(inst, r, r2.ok && isGeneralMemo(r2.data) ? r2.data : null);
      });
    });
    apiBoard().then(function (r) {
      if (!alive(inst)) return;
      st.board = r;
      st.item = r.ok && r.data ? boardItem(r.data.items, id) : null;
      paintGlance(inst);
    });
    apiTensor(id).then(function (r) {
      if (!alive(inst)) return;
      st.tensor = r;
      paintGlance(inst);
    });
  }
  function setGlanceMemo(inst, r, m) {
    var st = inst.st;
    st.ent = r;
    if (m && !m.expired && m.overall_conviction != null && isFinite(+m.overall_conviction)) st.memo = m;
    else st.oldMemo = m || null;
    paintGlance(inst);
  }
  function paintGlance(inst) {
    if (!alive(inst)) return;
    paintGlanceQuote(inst); paintGlanceMain(inst); paintGlanceConv2(inst); paintGlancePC(inst); paintGlanceBtns(inst); paintGlanceFoot(inst);
  }
  function bigIsPrice(st) { return !!(st.ent && !st.memo); }
  function paintGlanceQuote(inst) {
    var st = inst.st, el = q(inst, '[data-r=quote]');
    if (!el) return;
    var qq = quoteOfNode(st.node);
    if (bigIsPrice(st) || !qq.tk) { el.hidden = true; return; }
    el.hidden = false;
    if (!(qq.px > 0)) {
      el.innerHTML = '<span class="tk">' + esc(qq.tk) + '</span><span class="osw-mut">' + esc(L('sin precio en vivo ahora', 'no live price right now')) + '</span>';
      return;
    }
    var chip = typeof window.quoteSrcChip === 'function' ? window.quoteSrcChip(qq.q, qq.tk) : '';
    el.innerHTML = '<span class="tk">' + esc(qq.tk) + '</span><span class="px">' + esc(quoteMoney(qq)) + '</span>' +
      chgHTML(qq.pct) + '<span class="osw-mut">' + chip + ' ' + esc(srcText(qq)) + '</span>';
  }
  function decInfo(m) {
    var b = (m && m.memo) || {}, d = m && (m.decision || b.decision);
    if (b.decision_code === 'INSUFFICIENT_DATA') return { txt: L('Datos insuficientes', 'Insufficient data'), tone: 'neu', insufficient: true };
    var DEC = { BUY: ['comprar', 'buy'], ADD: ['aumentar', 'add'], HOLD: ['mantener / esperar', 'hold / wait'], TRIM: ['reducir', 'trim'], SELL: ['vender', 'sell'], AVOID: ['evitar', 'avoid'] };
    var x = DEC[d], lab = x ? L(x[0], x[1]) : String(pick(b, 'decision_label') || d || '').toLowerCase();
    return { txt: L('Comité: ', 'Committee: ') + lab, tone: (d === 'SELL' || d === 'AVOID' || d === 'TRIM') ? 'neg' : (d === 'HOLD' ? 'neu' : ''), insufficient: false };
  }
  var MSTATUS = { proposed: ['propuesta · espera tu revisión', 'proposal · awaiting your review'], approved: ['aprobada por una persona', 'approved by a person'],
    rejected: ['rechazada por una persona', 'rejected by a person'], executed: ['ejecutada', 'executed'] };
  function paintGlanceMain(inst) {
    var st = inst.st, el = q(inst, '[data-r=main]');
    if (!el) return;
    if (!st.ent) {   // esperando al comité: el precio ya está arriba, el número grande todavía no
      if (st.mainSig === 'sk') return;
      st.mainSig = 'sk';
      el.innerHTML = '<div class="osw-gl-l" style="flex:1"><span class="osw-sk" style="height:13px;width:90px"></span><span class="osw-sk" style="height:62px;width:150px;margin-top:8px;border-radius:12px"></span></div>' +
        '<span class="osw-sk" style="height:32px;width:150px;border-radius:999px"></span>';
      return;
    }
    var html, sig;
    if (st.memo) {
      var m = st.memo, v = +m.overall_conviction, di = decInfo(m), stt = MSTATUS[m.status];
      var fin = fmtNum(Math.round(v), 0, null, { sign: true });
      sig = 'memo|' + m.memo_id + '|' + lang();
      if (sig === st.mainSig) return;
      html = '<div class="osw-gl-l"><div class="osw-kick">' + esc(L('Convicción', 'Conviction')) + qChip('os_conviction') + '</div>' +
        '<div class="osw-big' + (di.insufficient ? ' mut' : '') + '"><span aria-hidden="true" data-r="num">' + esc(inst.quiet ? fin : (v > 0 ? '+0' : v < 0 ? MINUS + '0' : '0')) + '</span><span class="osw-vh">' + esc(fin) + '</span></div></div>' +
        '<div class="osw-gl-r"><span class="osw-pill' + (di.tone ? ' ' + di.tone : '') + '">' + esc(di.txt) + '</span>' +
        (di.insufficient ? '<div class="osw-gl-cap">' + esc(L('faltan analistas para decidir', 'not enough analysts to decide')) + '</div>'
          : (stt ? '<div class="osw-gl-cap">' + esc(L(stt[0], stt[1])) + '</div>' : '')) + '</div>';
      st.mainSig = sig;
      el.innerHTML = html;
      var num = el.querySelector('[data-r=num]');
      if (!inst.quiet) countUp(num, Math.round(v));
      inst.quiet = true;   // un repintado (idioma, precio) no vuelve a animar
      return;
    }
    // sin comité vigente: el número grande es el PRECIO EN VIVO
    var qq = quoteOfNode(st.node), node = st.node;
    // con un memo VENCIDO no se dice «aún»: hubo veredicto, pero ya no vale (TTL del comité)
    var pill = '<span class="osw-pill neu">' + esc(st.oldMemo ? L('Sin veredicto vigente', 'No current verdict') : L('Sin veredicto aún', 'No verdict yet')) + '</span>';
    if (qq.px > 0) {
      var chip = typeof window.quoteSrcChip === 'function' ? window.quoteSrcChip(qq.q, qq.tk) : '';
      html = '<div class="osw-gl-l"><div class="osw-kick">' + esc(L('Precio', 'Price')) + ' · ' + esc(qq.tk) + ' ' + chip + '</div>' +
        '<div class="osw-big ink">' + esc(quoteMoney(qq)) + '</div>' +
        (qq.pct != null ? '<div class="osw-gl-chg">' + chgHTML(qq.pct) + ' <span class="osw-mut">' + esc(L('vs. cierre anterior', 'vs. previous close')) + '</span></div>' : '') +
        '</div><div class="osw-gl-r">' + pill + '<div class="osw-gl-cap">' + esc(srcText(qq)) + '</div></div>';
    } else {
      var priv = !!(node && !node.mkt);
      var lst = node && node.listing, note = lst ? pick(lst, 'note') : '';
      html = '<div class="osw-gl-l"><div class="osw-kick">' + esc(L('Precio', 'Price')) + '</div>' +
        '<div class="osw-big txt">' + esc(!node ? L('No está en el catálogo', 'Not in the catalog') : priv ? L('No cotiza en bolsa', 'Not publicly listed') : L('Sin precio en vivo ahora', 'No live price right now')) + '</div>' +
        (priv && note ? '<div class="osw-gl-cap" style="text-align:left;margin-top:4px">' + esc(note) + '</div>' : '') +
        '</div><div class="osw-gl-r">' + pill + '</div>';
    }
    sig = 'px|' + html;
    if (sig === st.mainSig) return;
    st.mainSig = sig;
    el.innerHTML = html;
  }
  function paintGlanceConv2(inst) {
    var st = inst.st, el = q(inst, '[data-r=conv2]');
    if (!el) return;
    var it = st.item;
    if (st.memo || !st.ent || !it || !isFinite(+it.overall_conviction)) { el.hidden = true; return; }
    el.hidden = false;
    el.innerHTML = '<span>' + esc(L('Convicción de tus agentes:', 'Your agents\' conviction:')) + '</span> <b>' + esc(fmtConv(+it.overall_conviction)) + '</b> ' +
      '<span class="osw-mut">' + esc(st.oldMemo ? L('(sin comité vigente)', '(no current committee)') : L('(sin comité aún)', '(no committee yet)')) + '</span>' + qChip('os_conviction');
  }
  function pcList(pros, cons) {
    function li(sg, x) {
      var t = clean(x.t);
      return '<li><span class="osw-sg ' + sg + '" aria-label="' + esc(sg === 'p' ? L('a favor', 'in favor') : L('en contra', 'against')) + '">' + (sg === 'p' ? '+' : MINUS) + '</span>' +
        '<span class="osw-pc-t"><span class="osw-clamp" title="' + esc(t) + '">' + esc(t) + '</span>' + (x.who ? '<span class="osw-pc-who">' + esc(x.who) + '</span>' : '') + '</span></li>';
    }
    return '<ul class="osw-pc">' + pros.map(function (x) { return li('p', x); }).join('') + cons.map(function (x) { return li('m', x); }).join('') + '</ul>';
  }
  function hzName(h) {
    var HZ = { INTRADAY: ['intradía', 'intraday'], SHORT_TERM: ['corto plazo', 'short term'], MEDIUM_TERM: ['mediano plazo', 'medium term'],
      LONG_TERM: ['largo plazo', 'long term'], STRUCTURAL: ['estructural', 'structural'] };
    var x = HZ[h];
    return x ? L(x[0], x[1]) : '';
  }
  function agentLabel(agentType) {
    var mid = mascotOf(agentType), a = null;
    for (var i = 0; i < AGENTS.length; i++) if (AGENTS[i].id === mid) a = AGENTS[i];
    return a ? L(a.es, a.en) : String(agentType || '');
  }
  function paintGlancePC(inst) {
    var st = inst.st, el = q(inst, '[data-r=pc]');
    if (!el) return;
    var pros = [], cons = [], lab = '', mode = '';
    if (st.memo) {
      var b = st.memo.memo || {};
      (b.thesis || []).slice(0, 2).forEach(function (x) { var t = pick(x, 'thesis'); if (t) pros.push({ t: t, who: hzName(x.horizon) }); });
      (b.key_risks || []).slice(0, 2).forEach(function (x) { var t = pick(x, 'risk'); if (t) cons.push({ t: t }); });
      if (pros.length || cons.length) mode = 'memo';
    }
    if (!mode && st.memo === null && !st.ent) { put(el, skLines(2, 15)); return; }
    if (!mode && st.board == null) { put(el, skLines(2, 15)); return; }
    if (!mode && st.item) {
      var bf = st.item.best_for, ba = st.item.best_against;
      if (bf && pick(bf, 'text')) pros.push({ t: pick(bf, 'text'), who: [agentLabel(bf.agent_type), hzName(bf.horizon)].filter(Boolean).join(' · ') });
      if (ba && pick(ba, 'text')) cons.push({ t: pick(ba, 'text'), who: [agentLabel(ba.agent_type), hzName(ba.horizon)].filter(Boolean).join(' · ') });
      if (pros.length || cons.length) { mode = 'board'; lab = L('Lo más fuerte a favor y en contra, según tus agentes', 'The strongest points for and against, per your agents'); }
    }
    if (!mode) {
      if (st.tensor == null) { put(el, skLines(2, 15)); return; }
      var sp = st.tensor.ok ? structPC(st.tensor.data) : { pros: [], cons: [] };
      if (sp.pros.length || sp.cons.length) {
        pros = sp.pros; cons = sp.cons; mode = 'struct';
        lab = L('De la estructura de su cadena de suministro — no es una opinión de tus agentes', 'From its supply-chain structure — not an opinion of your agents');
      }
    }
    if (!mode) {
      var nodb = noDb(st.ent) || noDb(st.board);
      put(el, '<div class="osw-empty" style="padding-top:0">' + (nodb
        ? esc(L('Tus agentes no pueden opinar en este servidor: la base de investigación no está conectada.', 'Your agents cannot weigh in on this server: the research database is not connected.'))
        : esc(L('Tus agentes todavía no investigaron ', 'Your agents have not researched ')) + '<b>' + esc(st.label) + '</b>' + esc(L('. Pide la opinión del comité y lo harán con evidencia citada.', ' yet. Ask the committee and they will, with cited evidence.'))) + '</div>');
      return;
    }
    put(el, (lab ? '<div class="osw-pc-lab">' + esc(lab) + '</div>' : '') + pcList(pros, cons));
  }
  function paintGlanceBtns(inst) {
    var st = inst.st, el = q(inst, '[data-r=btns]');
    if (!el) return;
    var proposed = !!(st.memo && st.memo.status === 'proposed');
    var hasRes = !!(st.memo || st.item), known = !!(st.memo || (st.ent && st.board));
    var h = '';
    if (window.KhipuCommittee) h += '<button type="button" class="osw-btn pri" data-act="committee">' + esc(proposed ? L('Revisar propuesta', 'Review proposal') : L('Pedir opinión al comité', 'Ask the committee')) + '</button>';
    if (window.KhipuResearch) h += '<button type="button" class="osw-btn" data-act="research">' + esc(hasRes || !known ? L('Ver evidencia', 'See evidence') : L('Investigar', 'Research it')) + '</button>';
    put(el, h);
  }
  function paintGlanceFoot(inst) {
    var st = inst.st, el = q(inst, '[data-r=foot]');
    if (!el) return;
    var parts = [], qq = quoteOfNode(st.node);
    if (qq.tk) parts.push('<b>' + esc(L('Precio', 'Price')) + '</b> ' + esc(qq.px > 0 ? srcText(qq) || L('caché', 'cached') : L('sin cotización en vivo', 'no live quote')));
    else if (st.node) parts.push('<b>' + esc(L('Precio', 'Price')) + '</b> ' + esc(L('no cotiza', 'not listed')));
    if (st.memo) {
      var tv = (st.memo.memo || {}).track_validation || {};
      parts.push('<b>' + esc(L('Comité', 'Committee')) + '</b> ' + esc(fmtWhen(st.memo.created_at)) +
        (st.memo.expires_at ? esc(L(' · vigente hasta ', ' · valid until ') + fmtWhen(st.memo.expires_at, false)) : '') +
        (tv.status && tv.status !== 'validated' ? esc(' · ' + (pick(tv, 'label') || L('historial no validado', 'track record not validated'))) : ''));
    } else if (st.oldMemo) {
      parts.push('<b>' + esc(L('Último comité', 'Last committee')) + '</b> ' + esc(fmtWhen(st.oldMemo.created_at) + L(' (vencido)', ' (expired)')));
    }
    if (!st.memo && st.item) parts.push('<b>' + esc(L('Pizarra', 'Board')) + '</b> ' + esc((st.item.n_claims || 0) + L(' conclusiones vigentes · ', ' current conclusions · ') + fmtWhen(st.item.last_research)));
    var usedStruct = !st.memo && !st.item && st.tensor && st.tensor.ok;
    if (usedStruct) parts.push('<b>' + esc(L('Estructura', 'Structure')) + '</b> ' + esc(L('catálogo Khipus · tensor de flujo', 'Khipus catalog · flow tensor')) + qChip('tensor_struct'));
    if (st.ent && noDb(st.ent)) parts.push(esc(L('Comité e investigación: no disponibles en este servidor', 'Committee and research: unavailable on this server')));
    else if (st.ent && !st.ent.ok) parts.push(esc(L('Comité: ', 'Committee: ') + (st.ent.error || '')));
    parts.push(esc(L('No es una recomendación personal.', 'Not a personal recommendation.')));
    put(el, parts.join(' &middot; '));
  }
  function countUp(el, target) {
    if (!el) return;
    var fin = fmtNum(target, 0, null, { sign: true });
    var reduce = false;
    try { reduce = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches); } catch (e) { reduce = false; }
    if (reduce || document.hidden || typeof requestAnimationFrame !== 'function' || !isFinite(target) || target === 0) { el.textContent = fin; return; }
    var t0 = null, D = 900, sg = target > 0 ? '+' : MINUS, a = Math.abs(target);
    function step(ts) {
      if (!el.isConnected) return;
      if (t0 == null) t0 = ts;
      var p = Math.min(1, (ts - t0) / D), e = 1 - Math.pow(1 - p, 3);
      el.textContent = p < 1 ? sg + fmtNum(Math.round(a * e), 0) : fin;
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
    setTimeout(function () { if (el.isConnected) el.textContent = fin; }, D + 450);   // rAF se congela en pestañas ocultas
  }

  /* ═══════════════════════ «Convicción de tus agentes» ══════════════════════ */
  function renderConviction(body, arg) {
    var inst = mount('conviction', body, arg);
    var id0 = argId(arg), node = id0 ? nodeOf(id0) : null, id = node ? node.id : (id0 || null);
    inst.st = { id: id, node: node, label: labelOf(node, id0 || ''), res: null, expanded: false };
    inst.root.innerHTML = header('comite', L('Convicción de tus agentes', 'Your agents\' conviction'), qChip('os_conviction')) +
      '<div data-r="body">' + skLines(8, 18) + '</div><div class="osw-foot" data-r="foot"></div>';
    apiBoard().then(function (r) { if (!alive(inst)) return; inst.st.res = r; paintConviction(inst); });
  }
  function convItems(r) {
    var items = (r && r.ok && r.data && r.data.items) || [];
    return items.filter(function (x) { return x && x.overall_conviction != null && isFinite(+x.overall_conviction); })
      .slice().sort(function (a, b) { return (+b.overall_conviction) - (+a.overall_conviction); });
  }
  function paintConviction(inst) {
    var st = inst.st, R = inst.root, bodyEl = R.querySelector('[data-r=body]'), foot = R.querySelector('[data-r=foot]');
    if (!bodyEl) return;
    var oldTip = R.querySelector('.osw-tip');
    if (oldTip) oldTip.hidden = true;
    var r = st.res, lbl = st.label || '';
    var research = st.id && window.KhipuResearch ? '<button type="button" class="osw-btn sm pri auto" data-act="research">' + esc(L('Investigar ', 'Research ') + lbl) + '</button>' : '';
    if (!r.ok) {
      var msg = noDb(r)
        ? L('Tus agentes todavía no pueden opinar aquí: este servidor no tiene conectada la base de investigación. No hay convicción que mostrar.', 'Your agents cannot weigh in here yet: this server has no research database connected. There is no conviction to show.')
        : L('No pude leer la convicción de tus agentes (' + (r.error || '') + ').', 'Could not read your agents\' conviction (' + (r.error || '') + ').');
      bodyEl.innerHTML = '<div class="osw-empty">' + esc(msg) + '</div><div class="osw-btns" style="margin-top:12px">' + research +
        (noDb(r) ? '' : '<button type="button" class="osw-btn sm auto" data-act="retry">' + esc(L('Reintentar', 'Retry')) + '</button>') + '</div>';
      foot.innerHTML = esc(L('Fuente: pizarra del comité (las conclusiones vigentes de tus analistas).', 'Source: committee board (your analysts\' current conclusions).'));
      return;
    }
    var items = convItems(r);
    if (!items.length) {
      bodyEl.innerHTML = '<div class="osw-empty">' + esc(L('Tus agentes aún no investigaron ninguna empresa. Cuando lo hagan, aquí verás cuánto confían en cada una, de −100 (en contra) a +100 (a favor).',
        'Your agents have not researched any company yet. When they do, you will see here how confident they are in each one, from −100 (against) to +100 (for).')) + '</div>' +
        (research ? '<div class="osw-btns" style="margin-top:12px">' + research + '</div>' : '');
      foot.innerHTML = esc(L('Fuente: pizarra del comité — conclusiones vigentes de tus analistas.', 'Source: committee board — your analysts\' current conclusions.'));
      return;
    }
    var hi = -1;
    if (st.id) { var it = boardItem(items, st.id); if (it) hi = items.indexOf(it); }
    var vis = visibleRows(items.length, hi, st.expanded);
    var rows = '';
    vis.forEach(function (x) {
      if (typeof x === 'object') { rows += '<div class="osw-cv-gap" aria-hidden="true">···<span>' + esc(L(x.gap + ' más', x.gap + ' more')) + '</span></div>'; return; }
      rows += convRow(items[x], x === hi, x);
    });
    var miss = (st.id && hi < 0) ? '<div class="osw-cv-miss"><span><b>' + esc(lbl) + '</b> ' + esc(L('— tus agentes aún no tienen conclusiones sobre esta empresa.', '— your agents have no conclusions on this company yet.')) + '</span>' + research + '</div>' : '';
    var more = items.length > vis.filter(function (x) { return typeof x !== 'object'; }).length || st.expanded
      ? '<button type="button" class="osw-link" data-act="expand" style="align-self:flex-start">' + esc(st.expanded ? L('Ver menos', 'Show less') : L('Ver las ' + items.length + ' empresas', 'See all ' + items.length + ' companies')) + '</button>' : '';
    bodyEl.innerHTML = miss +
      '<div class="osw-cv-axis" aria-hidden="true"><span></span><span class="ax"><span class="al">' + esc(MINUS + '100 ' + L('en contra', 'against')) + '</span>' +
      '<span class="a0">0</span><span class="ar">' + esc(L('a favor +100', 'for +100')) + '</span></span><span></span></div>' +
      '<div class="osw-cv-rows" data-r="rows">' + rows + '</div>' + more;
    bodyEl.style.display = 'flex'; bodyEl.style.flexDirection = 'column'; bodyEl.style.gap = '10px';
    var rowsEl = bodyEl.querySelector('[data-r=rows]');
    setTimeout(function () { if (rowsEl.isConnected) rowsEl.classList.add('on'); }, inst.quiet ? 0 : 30);
    inst.quiet = true;
    wireTips(inst, rowsEl, items);
    var gen = r.data.generated_at;
    foot.innerHTML = '<span class="osw-lg"><i class="pos"></i>' + esc(L('a favor', 'for')) + '</span><span class="osw-lg"><i class="mute"></i>' + esc(L('leve o neutral', 'mild or neutral')) + '</span>' +
      '<span class="osw-lg"><i class="neg"></i>' + esc(L('en contra fuerte (≤ −15)', 'strongly against (≤ −15)')) + '</span><br>' +
      '<b>' + esc(L('Fuente', 'Source')) + '</b> ' + esc(L('pizarra del comité: conclusiones vigentes de tus analistas, ponderadas por confianza e historial', 'committee board: your analysts\' current conclusions, weighted by confidence and track record')) +
      (gen ? esc(' · ' + L('calculado ', 'computed ') + fmtWhen(gen)) : '') + ' &middot; ' + esc(L('No es una recomendación.', 'Not a recommendation.'));
  }
  function convRow(it, isHi, idx) {
    var v = Math.round(+it.overall_conviction * 10) / 10, g = barGeom(v), tone = barTone(v), lab = it.label || labelById(it.entity_id);
    return '<button type="button" class="osw-cv-row' + (isHi ? ' hi' : '') + '" data-act="glance" data-id="' + esc(it.entity_id) + '" data-i="' + idx + '"' +
      (isHi ? ' aria-current="true"' : '') + ' aria-label="' + esc(lab + ': ' + fmtConv(v)) + '">' +
      '<span class="osw-cv-name">' + esc(lab) + '</span>' +
      '<span class="osw-cv-track"><span class="osw-cv-bar ' + g.side + ' t-' + tone + '" style="--w:' + g.pct + '%"></span></span>' +
      '<span class="osw-cv-val">' + esc(fmtConv(v)) + '</span></button>';
  }
  // revisión #8 (2026-10-06): un memo vencido, rechazado o sin datos suficientes NO es un veredicto vigente
  function memoLine(memo, DEC) {
    var when = fmtWhen(memo.created_at, false);
    if (memo.decision_code === 'INSUFFICIENT_DATA') return L('Comité: datos insuficientes · ', 'Committee: insufficient data · ') + when;
    var dec = DEC[memo.decision] ? L(DEC[memo.decision][0], DEC[memo.decision][1]) : memo.decision;
    if (memo.expired) return L('Comité (vencido): ', 'Committee (expired): ') + dec + ' · ' + when;
    if (memo.status === 'rejected') return L('Comité: ', 'Committee: ') + dec + L(' — rechazado por ti · ', ' — rejected by you · ') + when;
    return L('Comité: ', 'Committee: ') + dec + ' · ' + when;
  }
  window.KhipuOSWin_memoLine = memoLine;   // pruebas
  function tipHTML(it) {
    var v = +it.overall_conviction, by = it.by_horizon || {}, rows = '';
    ['SHORT_TERM', 'MEDIUM_TERM', 'LONG_TERM', 'STRUCTURAL', 'INTRADAY'].forEach(function (h) {
      if (by[h] == null || !isFinite(+by[h])) return;
      var nm = hzName(h);
      rows += '<div class="r"><span>' + esc(nm.charAt(0).toUpperCase() + nm.slice(1)) + '</span><span>' + esc(fmtConv(+by[h])) + '</span></div>';
    });
    var mids = [];
    (it.agents || []).forEach(function (a) { var m = mascotOf(a); if (mids.indexOf(m) < 0) mids.push(m); });
    var names = mids.map(function (m) { for (var i = 0; i < AGENTS.length; i++) if (AGENTS[i].id === m) return L(AGENTS[i].es, AGENTS[i].en); return m; });
    var memo = it.memo, DEC = { BUY: ['comprar', 'buy'], ADD: ['aumentar', 'add'], HOLD: ['mantener', 'hold'], TRIM: ['reducir', 'trim'], SELL: ['vender', 'sell'], AVOID: ['evitar', 'avoid'] };
    return '<div class="hd"><b>' + esc(it.label || it.entity_id) + '</b><b>' + esc(fmtConv(v)) + '</b></div>' +
      (rows || '<div>' + esc(L('Sin desglose por plazo', 'No breakdown by horizon')) + '</div>') +
      '<div class="ag">' + (mids.length ? stackOf(mids, 16) : '') + '<span>' + esc((it.n_claims || 0) + L(' conclusiones', ' conclusions') + (names.length ? ' · ' + names.join(', ') : '')) + '</span></div>' +
      (it.n_contradictions ? '<div>' + esc(it.n_contradictions + L(' contradicción(es) entre agentes', ' contradiction(s) between agents')) + '</div>' : '') +
      (memo && memo.decision ? '<div>' + esc(memoLine(memo, DEC)) + '</div>' : '') +
      (it.last_research ? '<div class="osw-mut">' + esc(L('Investigado ', 'Researched ') + fmtWhen(it.last_research)) + '</div>' : '');
  }
  function wireTips(inst, rowsEl, items) {
    var R = inst.root, tip = R.querySelector('.osw-tip');
    if (!tip) { tip = document.createElement('div'); tip.className = 'osw-tip'; tip.hidden = true; tip.setAttribute('role', 'tooltip'); R.appendChild(tip); }
    function show(row) {
      var i = +row.getAttribute('data-i'), it = items[i];
      if (!it) return;
      tip.innerHTML = tipHTML(it);
      tip.hidden = false;
      var rr = row.getBoundingClientRect(), rb = R.getBoundingClientRect();
      var top = rr.bottom - rb.top + 4, tw = tip.offsetWidth || 220, th = tip.offsetHeight || 120;
      if (rr.bottom + th + 8 > window.innerHeight && rr.top - th - 8 > 0) top = rr.top - rb.top - th - 4;
      var left = Math.max(0, Math.min(rb.width - tw, rr.left - rb.left + rr.width * 0.42));
      tip.style.top = Math.round(top) + 'px';
      tip.style.left = Math.round(left) + 'px';
    }
    function hide() { tip.hidden = true; }
    var hover = true;
    try { hover = !window.matchMedia || window.matchMedia('(hover: hover)').matches; } catch (e) { hover = true; }
    if (hover) {
      rowsEl.addEventListener('mouseover', function (ev) { var row = ev.target.closest && ev.target.closest('.osw-cv-row'); if (row) show(row); });
      rowsEl.addEventListener('mouseleave', hide);
    }
    rowsEl.addEventListener('focusin', function (ev) { var row = ev.target.closest && ev.target.closest('.osw-cv-row'); if (row) show(row); });
    rowsEl.addEventListener('focusout', hide);
  }

  /* ═════════════════════ «Cadena de suministro de X» ════════════════════════ */
  var TYPE_NAME = { supply: ['suministro', 'supply'], fab: ['fabricación', 'manufacturing'], cloud: ['nube', 'cloud'], license: ['licencia', 'license'],
    ppa: ['energía', 'power'], owns: ['propiedad', 'ownership'], deploy: ['despliegue', 'deployment'] };
  function renderSupply(body, arg) {
    var inst = mount('supplychain', body, arg);
    var id0 = argId(arg), node = nodeOf(id0), id = node ? node.id : (id0 || null);
    var st = inst.st = { id: id, node: node, label: labelOf(node, id0 || ''), ch: null, tensor: null, risk: {}, flagged: [], exp: { s: false, c: false } };
    var R = inst.root;
    if (!id) {
      R.innerHTML = header('cadena', L('Cadena de suministro', 'Supply chain')) +
        '<div class="osw-empty">' + esc(L('Dime de qué empresa quieres ver la cadena («cadena de suministro de TSMC»).', 'Tell me which company\'s chain to show ("TSMC supply chain").')) + '</div>';
      return;
    }
    st.ch = chainOf(id, window.LINKS || [], canon);
    R.innerHTML = header('cadena', scTitle(st.label)) + '<div class="osw-sub" data-r="sub"></div><div data-r="sc"></div>' +
      '<div class="osw-sc-note" data-r="note" hidden></div><div class="osw-foot" data-r="foot"></div>';
    paintChain(inst);
    if (st.ch.suppliers.length) {
      apiTensor(id).then(function (r) {
        if (!alive(inst)) return;
        st.tensor = r;
        if (r.ok && r.data) {
          var ups = (r.data.upstream_risk_sources || []).slice().sort(function (a, b) { return b.exposure_pct - a.exposure_pct; });
          ups.forEach(function (u) { st.risk[canon(u.id)] = { pct: +u.exposure_pct, direct: !!u.direct, label: u.label }; });
          st.flagged = ups.filter(function (u) { return u.direct && +u.exposure_pct >= 10; }).slice(0, 3).map(function (u) { return canon(u.id); });
        }
        paintChain(inst);
      });
    }
  }
  function scTitle(label) { return L('Cadena de suministro de ' + label, label + ' supply chain'); }
  function paintChain(inst) {
    var st = inst.st, R = inst.root, ch = st.ch;
    var sub = R.querySelector('[data-r=sub]'), box = R.querySelector('[data-r=sc]'), note = R.querySelector('[data-r=note]'), foot = R.querySelector('[data-r=foot]');
    if (!box) return;
    var ns = ch.suppliers.length, nc = ch.customers.length;
    var conc = st.tensor && st.tensor.ok && st.tensor.data.supplier_concentration;
    var CL = { alta: ['alta', 'high'], media: ['media', 'medium'], baja: ['baja', 'low'] };
    sub.innerHTML = esc(ns + L(ns === 1 ? ' proveedor' : ' proveedores', ns === 1 ? ' supplier' : ' suppliers') + ' · ' + nc + L(nc === 1 ? ' cliente' : ' clientes', nc === 1 ? ' customer' : ' customers')) +
      (conc && conc.level && CL[conc.level] ? esc(' · ' + L('concentración de proveedores: ', 'supplier concentration: ') + L(CL[conc.level][0], CL[conc.level][1])) + ' ' + qChip('tensor_struct') : '');
    if (!ns && !nc) {
      box.innerHTML = '<div class="osw-empty">' + esc(L('Todavía no tenemos relaciones de suministro registradas para ', 'We have no supply relationships recorded for ')) + '<b>' + esc(st.label) + '</b>' +
        esc(L(' en el catálogo (solo cuentan suministro, fabricación, nube, licencias, energía, propiedad y despliegue).', ' in the catalog yet (only supply, manufacturing, cloud, licenses, power, ownership and deployment count).')) + '</div>';
      note.hidden = true;
      foot.innerHTML = esc(L('Fuente: catálogo Khipus.', 'Source: Khipus catalog.'));
      return;
    }
    function side(list, key) {
      var lim = st.exp[key] ? 24 : 5, shown = list.slice(0, lim);
      if (key === 's' && st.flagged.length) {   // los proveedores de mayor riesgo SIEMPRE a la vista
        st.flagged.forEach(function (fid) {
          if (shown.some(function (x) { return x.id === fid; })) return;
          var x = list.filter(function (y) { return y.id === fid; })[0];
          if (x) shown.push(x);
        });
      }
      var max = 0;
      list.forEach(function (x) { if (x.w > max) max = x.w; });
      var rows = shown.map(function (x) { return scRow(st, x, key, max); }).join('');
      var rest = list.length - shown.length;
      var more = (list.length > 5) ? '<button type="button" class="osw-link osw-sc-more" data-act="more" data-side="' + key + '">' +
        esc(st.exp[key] ? L('Ver menos', 'Show less') : L('+' + rest + ' más', '+' + rest + ' more')) + '</button>' : '';
      var h = '<div class="osw-sc-h">' + (key === 's' ? esc(L('Proveedores', 'Suppliers')) + ' <span class="osw-mut">' + esc(L('le venden', 'sell to it')) + '</span>'
        : esc(L('Clientes', 'Customers')) + ' <span class="osw-mut">' + esc(L('le compran', 'buy from it')) + '</span>') + '</div>';
      if (!list.length) rows = '<div class="osw-mut" style="font-size:12.5px;padding:8px 0">' + esc(key === 's' ? L('Sin proveedores registrados', 'No suppliers recorded') : L('Sin clientes registrados', 'No customers recorded')) + '</div>';
      return '<div class="osw-sc-col ' + key + '">' + h + rows + more + '</div>';
    }
    box.innerHTML = '<div class="osw-sc">' + side(ch.suppliers, 's') +
      '<div class="osw-sc-mid"><button type="button" class="osw-sc-core" data-act="glance" data-id="' + esc(st.id) + '" title="' + esc(glanceTitle(st.label)) + '">' + esc(st.label) + '</button></div>' +
      side(ch.customers, 'c') + '</div>';
    // riesgo indirecto (no es proveedor directo) y estado del tensor
    var nh = '';
    if (st.tensor && st.tensor.ok) {
      var ind = (st.tensor.data.upstream_risk_sources || []).filter(function (u) { return !u.direct && +u.exposure_pct >= 10; }).slice(0, 2);
      if (ind.length) nh = esc(L('También expuesta, sin ser proveedor directo: ', 'Also exposed, though not a direct supplier: ')) +
        ind.map(function (u) { return '<b>' + esc(u.label) + '</b> ' + esc(fmtPct(u.exposure_pct, null, 0, false)); }).join(', ');
    } else if (st.tensor && !st.tensor.ok && ns) {
      nh = esc(L('El riesgo aguas arriba no está disponible ahora (' + (st.tensor.error || '') + ').', 'Upstream risk is unavailable right now (' + (st.tensor.error || '') + ').'));
    }
    note.hidden = !nh;
    note.innerHTML = nh;
    var anyUnv = ch.suppliers.concat(ch.customers).some(function (x) { return !x.verified; });
    foot.innerHTML = '<span class="osw-lg"><i class="mute"></i>' + esc(L('largo = peso de la relación', 'length = relationship weight')) + '</span>' +
      (st.flagged.length ? '<span class="osw-lg"><i class="neg"></i>' + esc(L('mayor riesgo aguas arriba', 'largest upstream risk')) + '</span>' : '') +
      (anyUnv ? '<span class="osw-lg"><i class="dash"></i>' + esc(L('sin verificar', 'unverified')) + '</span>' : '') + '<br>' +
      '<b>' + esc(L('Fuente', 'Source')) + '</b> ' + esc(L('catálogo Khipus, solo relaciones de flujo (suministro, fabricación, nube, licencia, energía, propiedad, despliegue)',
        'Khipus catalog, flow relationships only (supply, manufacturing, cloud, license, power, ownership, deployment)')) +
      (st.tensor && st.tensor.ok ? esc(' · ' + L('riesgo: tensor de flujo', 'risk: flow tensor') + (st.tensor.data.caps_as_of ? ' (' + fmtWhen(st.tensor.data.caps_as_of, false) + ')' : '')) : '');
  }
  function scRow(st, x, key, max) {
    var lab = labelById(x.id), rk = key === 's' ? st.risk[x.id] : null, flag = key === 's' && st.flagged.indexOf(x.id) >= 0;
    var pct = max > 0 ? Math.max(8, Math.round(x.w / max * 100)) : 8;
    var types = x.types.map(function (t) { var n = TYPE_NAME[t]; return n ? L(n[0], n[1]) : t; }).join(', ');
    var tip = lab + ' — ' + (key === 's' ? L('le vende a ', 'sells to ') + st.label : L('le compra a ', 'buys from ') + st.label) + ' (' + types + ')' +
      (x.rel ? ': ' + x.rel : '') + (x.verified ? '' : ' · ' + L('sin verificar', 'unverified')) +
      (rk ? ' · ' + L('riesgo: ', 'risk: ') + fmtPct(rk.pct, null, 0, false) + L(' (cuánto la golpearía un problema allí)', ' (how hard a problem there would hit it)') : '');
    var pill = '<button type="button" class="osw-sc-pill' + (flag ? ' risk' : '') + '" data-act="glance" data-id="' + esc(x.id) + '" title="' + esc(tip) + '">' + esc(lab) + '</button>';
    var wire = '<span class="osw-sc-wire' + (x.verified ? '' : ' unv') + '" aria-hidden="true"><i class="osw-sc-seg' + (flag ? ' risk' : '') + '" style="width:' + pct + '%"></i></span>';
    return '<div class="osw-sc-row' + (key === 'c' ? ' r' : '') + '">' + (key === 'c' ? wire + pill : pill + wire) + '</div>';
  }

  /* ════════════════════════════ «Tus agentes» ═══════════════════════════════ */
  function renderAgents(body, arg) {
    var inst = mount('agents', body, arg);
    inst.st = { res: null };
    paintAgents(inst);
    apiProfiles().then(function (r) { if (!alive(inst)) return; inst.st.res = r; paintAgents(inst); });
  }
  function mergedAgents(res) {
    var srv = {};
    if (res && res.ok && res.data && res.data.agents && res.data.agents.length) res.data.agents.forEach(function (a) { if (a && a.id) srv[a.id] = a; });
    return AGENTS.map(function (base) {
      var s = srv[base.id], out = {};
      Object.keys(base).forEach(function (k) { out[k] = base[k]; });
      if (s) Object.keys(s).forEach(function (k) {
        var v = s[k];
        if (v == null || (Array.isArray(v) && !v.length && base[k] && base[k].length)) return;
        out[k] = v;
      });
      out.fromServer = !!s;
      return out;
    });
  }
  function prefsNow() { var P = window.KhipuAgentPrefs; try { return P ? P.get() : null; } catch (e) { return null; } }
  function swHTML(aid, key, on, label, small, disabled) {
    return '<button type="button" class="osw-sw" role="switch" aria-checked="' + (on ? 'true' : 'false') + '" data-act="pref" data-agent="' + esc(aid) + '" data-pref="' + key + '"' + (disabled ? ' disabled' : '') + '>' +
      '<span class="osw-sw-t" aria-hidden="true"></span><span class="osw-sw-l">' + esc(label) + (small ? '<small>' + esc(small) + '</small>' : '') + '</span></button>';
  }
  function isPooledTrack(a) { return !!(a && (a.id === 'comite' || (a.track && a.track.scope === 'overall'))); }
  function trackHTML(a, res) {
    var t = a.track;
    if (a.id === 'khipu') return esc(L('Khipu no hace predicciones: arma las respuestas con lo que traen los demás.', 'Khipu makes no predictions: it builds answers from what the others bring.'));
    if (res == null) return '<span class="osw-sk" style="height:12px;width:80%"></span>';
    var pro = (prefsNow() || {}).mode === 'pro';
    if (!t) {
      if (!(res && res.ok)) return esc(L('Historial no disponible ahora (el servidor no respondió).', 'Track record unavailable right now (the server did not respond).'));
      return esc(L('Sin historial suficiente todavía — se mide contra el precio real a 20 días hábiles.', 'Not enough history yet — measured against the real price after 20 business days.'));
    }
    var n = +t.n_scored || 0, hr = t.hit_rate;
    if (hr != null && isFinite(+hr)) hr = +hr <= 1 ? +hr * 100 : +hr;
    if (t.sufficient && hr != null && isFinite(hr)) {
      // el comité NO se califica solo: su «historial» es el COMBINADO de los analistas (scope 'overall');
      // se rotula así y no se le atribuye Brier ni fiabilidad propios
      var pooled = isPooledTrack(a);
      var s = (pooled ? esc(L('Historial combinado de los analistas (el comité no se califica solo): ', 'Combined record of the analysts (the committee is not scored on its own): ')) : '') +
        '<b>' + esc(fmtPct(hr, null, 0, false)) + '</b> ' + esc(L('de aciertos', 'hit rate')) + ' · ' + esc(n + L(' predicciones calificadas', ' scored predictions'));
      if (pro && !pooled) {
        if (t.brier != null && isFinite(+t.brier)) s += ' · Brier ' + esc(fmtNum(+t.brier, 3));
        if (t.reliability != null && isFinite(+t.reliability)) s += ' · ' + esc(L('fiabilidad ', 'reliability ') + fmtPct(+t.reliability <= 1 ? +t.reliability * 100 : +t.reliability, null, 0, false));
      }
      return s;
    }
    var note = pick(t, 'note') || L('Sin historial suficiente todavía — se mide contra el precio real a 20 días hábiles.', 'Not enough history yet — measured against the real price after 20 business days.');
    return esc(note) + (n > 0 ? ' ' + esc(L('(' + n + ' de 5 calificaciones)', '(' + n + ' of 5 scored)')) : '');
  }
  function costHTML(a) {
    var s = a.stats_30d;
    if (!s) return '';
    var runs = +s.runs || 0;
    if (!runs) return '<div class="osw-ag-cost">' + esc(L('Sin actividad en los últimos 30 días.', 'No activity in the last 30 days.')) + '</div>';
    var parts = [runs + L(runs === 1 ? ' corrida' : ' corridas', runs === 1 ? ' run' : ' runs')];
    if (s.claims != null) parts.push((+s.claims || 0) + L(' conclusiones', ' conclusions'));
    if (s.cost_usd != null && isFinite(+s.cost_usd)) parts.push('≈ US$' + fmtNum(+s.cost_usd, 2) + L(' (estimado)', ' (estimate)'));
    if (s.avg_latency_ms != null && isFinite(+s.avg_latency_ms) && (prefsNow() || {}).mode === 'pro') parts.push(fmtNum(+s.avg_latency_ms / 1000, 1) + L(' s promedio', ' s average'));
    return '<div class="osw-ag-cost">' + esc(L('Últimos 30 días: ', 'Last 30 days: ') + parts.join(' · ')) + '</div>';
  }
  function paintAgents(inst) {
    var st = inst.st, R = inst.root, res = st.res, P = prefsNow(), pro = !!(P && P.mode === 'pro');
    var list = mergedAgents(res), lg = lang();
    var seg = P ? '<div class="osw-seg" role="radiogroup" aria-label="' + esc(L('Cómo te hablan', 'How they talk to you')) + '">' +
      '<button type="button" role="radio" aria-checked="' + (!pro) + '" data-act="mode" data-mode="simple">Simple</button>' +
      '<button type="button" role="radio" aria-checked="' + pro + '" data-act="mode" data-mode="pro">Pro</button></div>' : '';
    var cards = list.map(function (a) {
      var pa = P && P.agents ? P.agents[a.id] : null, on = pa ? pa.on !== false : true, auto = pa ? !!pa.auto : false;
      var data = lg === 'en' ? (a.data_en || a.data_es || []) : (a.data_es || a.data_en || []);
      var outs = lg === 'en' ? (a.outputs_en || a.outputs_es || []) : (a.outputs_es || a.outputs_en || []);
      var wins = (a.windows || []).filter(function (k) { return WIN_NAME[k]; });
      var winTxt = wins.map(function (k) { return L(WIN_NAME[k][0], WIN_NAME[k][1]); }).join(', ');
      var sws = '';
      if (P) {
        sws = a.id === 'khipu'
          ? swHTML(a.id, 'on', true, L('Siempre participa', 'Always takes part'), L('es quien te responde', 'it is the one answering you'), true)
          : swHTML(a.id, 'on', on, L('Participa en mis respuestas', 'Takes part in my answers'), '', false);
        if (wins.length) sws += swHTML(a.id, 'auto', on && auto, L('Abre su ventana sola', 'Opens its window by itself'), winTxt, !on);
      }
      var pro2 = pro && ((a.research_types || []).length || (a.tools || []).length)
        ? '<div class="osw-ag-k">' + esc(L('Detalle técnico', 'Technical detail')) + '</div><div class="osw-chips">' +
          (a.research_types || []).map(function (t) { return '<span class="osw-chip mono">' + esc(t) + '</span>'; }).join('') +
          (a.tools || []).slice(0, 8).map(function (t) { return '<span class="osw-chip mono">' + esc(t) + '</span>'; }).join('') + '</div>' : '';
      var ask = a.id === 'khipu' ? L('Escríbele a Khipu', 'Message Khipu') : L('Pregúntale a ' + a.es, 'Ask ' + a.en);
      return '<article class="osw-ag' + (on ? '' : ' off') + '" data-agent="' + esc(a.id) + '">' +
        '<div class="osw-ag-top">' + mascot(a.id, 48) + '<div class="osw-ag-id"><div class="osw-ag-n">' + esc(L(a.es, a.en)) + '</div><div class="osw-ag-r">' + esc(pick(a, 'role')) + '</div></div></div>' +
        '<p class="osw-ag-does">' + esc(pick(a, 'does')) + '</p>' +
        '<div class="osw-ag-k">' + esc(L('Datos que usa', 'Data it uses')) + '</div><div class="osw-chips">' + data.map(function (d) { return '<span class="osw-chip">' + esc(d) + '</span>'; }).join('') + '</div>' +
        '<div class="osw-ag-k">' + esc(L('Qué te muestra', 'What it shows you')) + '</div><div class="osw-chips">' + outs.map(function (d) { return '<span class="osw-chip out">' + esc(d) + '</span>'; }).join('') + '</div>' +
        pro2 +
        '<div class="osw-ag-k">' + esc(L('Historial', 'Track record')) + (a.id === 'khipu' ? '' : qChip('os_track')) + '</div><div class="osw-ag-track">' + trackHTML(a, res) + '</div>' +
        costHTML(a) +
        (sws ? '<div class="osw-ag-sws">' + sws + '</div>' : '') +
        '<button type="button" class="osw-btn sm osw-ask" data-act="ask" data-agent="' + esc(a.id) + '">' + esc(ask) + '</button></article>';
    }).join('');
    var srvOk = res && res.ok && res.data && res.data.agents && res.data.agents.length;
    var foot = res == null ? esc(L('Cargando historial y costos…', 'Loading track record and costs…'))
      : srvOk ? esc(L('Historial: predicciones calificadas con precios reales vs. S&P 500', 'Track record: predictions scored with real prices vs the S&P 500') +
          (res.data.db === false ? L(' (sin base de datos en este servidor: sin historial ni costos)', ' (no database on this server: no track record or costs)') : '') +
          (res.data.as_of ? ' · ' + fmtWhen(res.data.as_of) : '') + L(' · Costos estimados.', ' · Costs are estimates.'))
      : esc(L('Perfiles locales: el servidor no respondió, así que no hay historial ni costos para mostrar.', 'Local profiles: the server did not respond, so there is no track record or cost to show.'));
    R.innerHTML = '<div class="osw-hd">' + stackOf(AGENT_ORDER, 22) + '<h3>' + esc(L('Tus agentes', 'Your agents')) + '</h3></div>' +
      '<div class="osw-sub">' + esc(L('Seis agentes. Una sola conversación. Elige quién participa y cómo te hablan.', 'Six agents. One conversation. Choose who takes part and how they talk to you.')) + '</div>' +
      '<div class="osw-ag-mode">' + seg + '<span>' + esc(!P ? L('Las preferencias no están disponibles en esta versión.', 'Preferences are unavailable in this version.')
        : pro ? L('Pro: respuestas densas, con cifras, rangos y horizonte.', 'Pro: dense answers, with figures, ranges and horizon.')
        : L('Simple: lenguaje llano, cada término explicado y una conclusión clara.', 'Simple: plain language, every term explained and a clear conclusion.')) + '</span></div>' +
      '<div class="osw-ag-grid">' + cards + '</div><div class="osw-foot">' + foot + '</div>';
  }

  /* ── registro en la Cabina + API pública ────────────────────────────────── */
  var KINDS = {
    glance: { mascot: 'analista', icon: '◉', es: 'En una mirada', en: 'At a glance', multi: true, render: renderGlance,
      title: function (arg) { var id = argId(arg), n = nodeOf(id); return id ? glanceTitle(labelOf(n, id)) : L('En una mirada', 'At a glance'); } },
    conviction: { mascot: 'comite', icon: '±', es: 'Convicción de tus agentes', en: 'Your agents\' conviction', multi: false, render: renderConviction,
      title: function () { return L('Convicción de tus agentes', 'Your agents\' conviction'); } },
    supplychain: { mascot: 'cadena', icon: '⛓', es: 'Cadena de suministro', en: 'Supply chain', multi: true, render: renderSupply,
      title: function (arg) { var id = argId(arg), n = nodeOf(id); return id ? scTitle(labelOf(n, id)) : L('Cadena de suministro', 'Supply chain'); } },
    agents: { mascot: 'khipu', icon: '✦', es: 'Tus agentes', en: 'Your agents', multi: false, render: renderAgents,
      title: function () { return L('Tus agentes', 'Your agents'); } }
  };
  function spec(kind) {
    var k = KINDS[kind];
    return { icon: k.icon, es: k.es, en: k.en, multi: k.multi, title: k.title, mascot: k.mascot,
      render: function (body, arg) { return render(kind, body, arg); } };
  }
  var _regTarget = null;
  function ensureRegistered() {
    var c = ck();
    if (!c || typeof c.registerKind !== 'function') return false;
    if (_regTarget === c) return true;
    try {
      Object.keys(KINDS).forEach(function (k) { c.registerKind(k, spec(k)); });
      _regTarget = c;
      return true;
    } catch (e) { return false; }
  }
  function render(kind, body, arg) {
    if (!KINDS[kind] || !body) return false;
    try { KINDS[kind].render(body, arg); return true; }
    catch (e) {
      try { console.warn('[KhipuOSWin] ' + kind + ':', e); } catch (x) {}
      try { body.innerHTML = '<div class="osw osw-solo"><div class="osw-empty">' + esc(L('No pude abrir esta ventana.', 'Could not open this window.')) + '</div></div>'; } catch (x) {}
      return false;
    }
  }
  function open(kind, arg) {
    if (!KINDS[kind]) return false;
    var c = ck();
    if (!c || !ensureRegistered()) return false;
    try {
      if (ckOpen()) c.stage(kind, arg);
      else if (typeof c.open === 'function') c.open({ kind: kind, arg: arg });
      return true;
    } catch (e) { return false; }
  }
  function rerenderAll(filter) {
    prune();
    INST.slice().forEach(function (i) {
      if (filter && !filter(i)) return;
      var sc = i.body.scrollTop, a = document.activeElement, sel = null;
      if (a && i.root.contains(a) && a.getAttribute('data-act')) {
        sel = '[data-act="' + a.getAttribute('data-act') + '"]' +
          ['data-agent', 'data-pref', 'data-mode', 'data-id', 'data-side'].map(function (k) { var v = a.getAttribute(k); return v != null ? '[' + k + '="' + String(v).replace(/["\\]/g, '') + '"]' : ''; }).join('');
      }
      i.body.__oswQuiet = true;   // mismo contenido (otro idioma / preferencia): sin volver a animar
      render(i.kind, i.body, i.arg);
      try { i.body.scrollTop = sc; } catch (e) {}
      if (sel) { try { var f = i.body.querySelector(sel); if (f) f.focus({ preventScroll: true }); } catch (e) {} }
    });
  }

  // registro: cockpit.js puede cargar antes o después; se reintenta hasta ~10 s
  (function boot() {
    if (ensureRegistered()) return;
    var tries = 0, iv = setInterval(function () { if (ensureRegistered() || ++tries > 40) clearInterval(iv); }, 250);
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { ensureRegistered(); ensureExplain(); });
  })();
  ensureExplain();
  setTimeout(ensureExplain, 0);

  // idioma: applyLang() pone <html lang>; además 'khipu:lang' y cambios de otra pestaña
  var _lastLang = lang();
  function onLang() {
    var l = lang();
    if (l === _lastLang) return;
    _lastLang = l;
    rerenderAll();
  }
  try { new MutationObserver(onLang).observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] }); } catch (e) {}
  window.addEventListener('khipu:lang', onLang);
  window.addEventListener('storage', function (e) { if (e && e.key === 'eco_lang') onLang(); });
  // precios en vivo: repinta el precio de «en una mirada» (agrupado)
  var _qT = 0;
  window.addEventListener('khipu:quotes', function () {
    if (_qT) return;
    _qT = setTimeout(function () {
      _qT = 0;
      prune();
      INST.forEach(function (i) { if (i.kind === 'glance' && i.st && i.st.id) { paintGlanceQuote(i); paintGlanceMain(i); paintGlanceFoot(i); } });
    }, 400);
  });
  // preferencias de agentes: la ventana «Tus agentes» refleja interruptores y modo
  window.addEventListener('khipu:agentprefs', function () { rerenderAll(function (i) { return i.kind === 'agents'; }); });

  window.KhipuOSWin = {
    __v: 1,
    kinds: KINDS,
    render: render,
    open: open,
    register: ensureRegistered,
    // funciones puras (pruebas: tests/test_khipus_os_windows.py)
    _h: { fmtNum: fmtNum, fmtConv: fmtConv, fmtPct: fmtPct, fmtMoney: fmtMoney, barTone: barTone, barGeom: barGeom,
      visibleRows: visibleRows, chainOf: chainOf, boardItem: boardItem, structPC: structPC, clean: clean, argId: argId,
      quoteCur: quoteCur, quoteOrigCur: quoteOrigCur, generalMemoOf: generalMemoOf, isPooledTrack: isPooledTrack }
  };
})();
