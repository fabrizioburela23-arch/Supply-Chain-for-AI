// engine/khipu_lang.js — Fase 4 del roadmap de ontología: lenguaje de
// comandos KHIPU, corto y componible: <ENTIDAD> <FUNCIÓN> [ARGS].
// Se intenta ANTES de mandar el texto a la IA (Bixby): si no calza con esta
// gramática, devuelve null y Bixby sigue su camino normal (lenguaje natural,
// sin round-trip a Claude — más rápido para comandos exactos). Cada función
// es un atajo a la MISMA API que usan los paneles — cero lógica duplicada.
//
// Gramática (ver ROADMAP_KHIPUS_ONTOLOGIA.md Fase 4):
//   NVDA DES · NVDA GP 1Y · NVDA SUP · NVDA CLI · NVDA RISK · NVDA SIM ·
//   NVDA NEWS · NVDA FA · NVDA THESIS [texto]
//   PORT VAR · PORT PL
//   GRAPH ASOF <YYYY-MM-DD> · GRAPH DIFF <Nd>
//   ALERT <TICKER> PX|NRS > <valor> · ALERT REGION <región> NEWS · ALERT LIST

(function () {
  'use strict';

  function _base() { return (typeof BASE !== 'undefined') ? BASE : ''; }

  function resolveEntity(token) {
    const NB = window.NODE_BY_ID || {};
    if (!token) return null;
    const up = token.toUpperCase();
    if (NB[token]) return NB[token];
    let byId = null, byTicker = null;
    for (const n of Object.values(NB)) {
      if (!byId && n.id && n.id.toUpperCase() === up) byId = n;
      if (!byTicker && n.mkt && n.mkt.toUpperCase() === up) byTicker = n;
      if (byId && byTicker) break;
    }
    return byId || byTicker || null;
  }

  const FUNCS = new Set(['DES', 'GP', 'SUP', 'CLI', 'RISK', 'SIM', 'NEWS', 'FA', 'THESIS']);
  const KEYWORDS = new Set(['PORT', 'GRAPH', 'ALERT']);

  function tryParse(text) {
    const raw = (text || '').trim();
    if (!raw) return null;
    const parts = raw.split(/\s+/);
    if (parts.length < 2) return null;
    const first = parts[0].toUpperCase();

    if (KEYWORDS.has(first)) return _handleKeyword(first, parts.slice(1));

    const fn = (parts[1] || '').toUpperCase();
    if (!FUNCS.has(fn)) return null;
    const entity = resolveEntity(parts[0]);
    if (!entity) return null;  // no es ticker/id conocido → que la IA lo interprete como lenguaje natural
    return _handleEntityFunc(entity, fn, parts.slice(2));
  }

  function _getActorKhipu() {
    try {
      let a = localStorage.getItem('khipu_actor');
      if (!a) { a = (window.prompt('¿Cómo te identificamos?') || '').trim(); if (a) localStorage.setItem('khipu_actor', a); }
      return a || 'anónimo';
    } catch (e) { return 'anónimo'; }
  }

  async function _handleEntityFunc(entity, fn, args) {
    const id = entity.id, label = entity.label;
    switch (fn) {
      case 'DES':
        return { answer: `Abriendo ficha de ${label}.`, actions: [{ type: 'second_brain', arg: id }] };
      case 'GP':
        return { answer: `Gráfico de ${label}${args[0] ? ' (' + args[0] + ')' : ''}.`, actions: [{ type: 'navigate', arg: id }] };
      case 'SUP':
        return { answer: `${label} — proveedores en ◈ Grafo Temporal.`, actions: [{ type: 'tkg_object', arg: id }] };
      case 'CLI':
        return { answer: `${label} — clientes en ◈ Grafo Temporal.`, actions: [{ type: 'tkg_object', arg: id }] };
      case 'RISK':
        return { answer: `${label} — riesgo NRS en ◈ Grafo Temporal.`, actions: [{ type: 'tkg_object', arg: id }] };
      case 'NEWS':
        return { answer: `${label} — noticias (abre 📰 en su ficha).`, actions: [{ type: 'tkg_object', arg: id }] };
      case 'SIM':
        return { answer: `Simulando la caída de ${label}.`, actions: [{ type: 'stress', arg: id }] };
      case 'FA':
        return _fetchFundamentals(entity);
      case 'THESIS': {
        const texto = args.join(' ');
        if (!texto) return { answer: `${label} — abriendo su ficha (tesis registradas).`, actions: [{ type: 'tkg_object', arg: id }] };
        return _createThesis(id, label, texto);
      }
    }
    return null;
  }

  async function _fetchFundamentals(entity) {
    try {
      const r = await fetch(`${_base()}/api/fundamentals/${encodeURIComponent(entity.mkt || entity.id)}`);
      if (!r.ok) return { answer: `Sin datos financieros disponibles para ${entity.label}.`, actions: [{ type: 'second_brain', arg: entity.id }] };
      const d = await r.json();
      const bits = [];
      if (d.revenue) bits.push(`ingresos ${d.revenue}`);
      if (d.grossMarginTTM || d.margin) bits.push(`margen ${d.grossMarginTTM || d.margin}`);
      if (d.peRatio || d.pe) bits.push(`P/E ${d.peRatio || d.pe}`);
      return { answer: `${entity.label} — ${bits.join(' · ') || 'ver ficha completa'}.`, actions: [{ type: 'second_brain', arg: entity.id }] };
    } catch (e) { return { answer: `Error al consultar fundamentales de ${entity.label}.`, actions: [] }; }
  }

  async function _createThesis(id, label, texto) {
    const actor = _getActorKhipu();
    try {
      const r = await fetch(`${_base()}/api/ontology/actions/CrearTesis`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ actor, company_id: id, stance: 'watch', confidence: 0.6, rationale: texto }),
      });
      const d = await r.json();
      if (r.ok) return { answer: `Tesis registrada sobre ${label}: "${texto}".`, actions: [{ type: 'tkg_object', arg: id }] };
      return { answer: `No se pudo registrar la tesis: ${d.error || 'error'} (¿está la ontología configurada?)`, actions: [] };
    } catch (e) { return { answer: 'Error de red al registrar la tesis.', actions: [] }; }
  }

  function _handleKeyword(kw, args) {
    if (kw === 'PORT') return _handlePort(args);
    if (kw === 'GRAPH') return _handleGraph(args);
    if (kw === 'ALERT') return _handleAlert(args);
    return null;
  }

  async function _handlePort(args) {
    const sub = (args[0] || '').toUpperCase();
    const pos = (window.MKT && window.MKT.pos) || {};
    if (sub === 'VAR') {
      const positions = {};
      Object.entries(pos).forEach(([nid, p]) => {
        const n = (window.NODE_BY_ID || {})[nid];
        if (n && n.mkt) positions[n.mkt] = { shares: p.sh || p.shares, buy_price: p.bp };
      });
      if (!Object.keys(positions).length) return { answer: 'No tienes posiciones en tu portafolio todavía.', actions: [] };
      try {
        const r = await fetch(`${_base()}/api/portfolio-risk`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ positions }),
        });
        const d = await r.json();
        if (!r.ok) return { answer: `No se pudo calcular VaR: ${d.error || 'error'}`, actions: [] };
        const v95 = d.var_95 != null ? (d.var_95 * 100).toFixed(1) + '%' : '—';
        const c95 = d.cvar_95 != null ? (d.cvar_95 * 100).toFixed(1) + '%' : '—';
        return { answer: `VaR 95%: ${v95} · CVaR 95%: ${c95}.`, actions: [] };
      } catch (e) { return { answer: 'Error de red al calcular VaR.', actions: [] }; }
    }
    if (sub === 'PL') {
      const quotes = (window.MKT && window.MKT.quotes) || {};
      let pl = 0, has = false;
      Object.entries(pos).forEach(([nid, p]) => {
        const n = (window.NODE_BY_ID || {})[nid];
        const q = n && n.mkt ? quotes[n.mkt] : null;
        if (q && q.close != null && p.bp != null && p.sh) { pl += (q.close - p.bp) * p.sh; has = true; }
      });
      if (!has) return { answer: 'No hay suficientes datos de precio en caché para calcular P&L.', actions: [] };
      return { answer: `P&L de tu cartera: ${pl >= 0 ? '+' : ''}$${pl.toFixed(2)}.`, actions: [] };
    }
    return { answer: 'Comandos de PORT: VAR, PL.', actions: [] };
  }

  async function _handleGraph(args) {
    const sub = (args[0] || '').toUpperCase();
    if (sub === 'ASOF') {
      const date = args[1];
      if (!date) return { answer: 'Uso: GRAPH ASOF <YYYY-MM-DD>', actions: [] };
      if (typeof switchTab === 'function') switchTab('tkg');
      const ok = window.__tkgSetDate ? window.__tkgSetDate(date) : false;
      return { answer: ok ? `Grafo Temporal movido a ${date}.` : 'No se pudo mover la línea de tiempo (¿fecha inválida?).', actions: [] };
    }
    if (sub === 'DIFF') {
      const nStr = (args[1] || '30D').toUpperCase().replace('D', '');
      const days = parseInt(nStr, 10) || 30;
      const to = new Date(); const from = new Date(to.getTime() - days * 86400000);
      const fmt = dt => dt.toISOString().slice(0, 10);
      try {
        const r = await fetch(`${_base()}/api/ontology/graph/diff?from=${fmt(from)}&to=${fmt(to)}`);
        if (!r.ok) return { answer: 'La ontología no está configurada — no se puede calcular el diff.', actions: [] };
        const d = await r.json();
        return { answer: `Últimos ${days} días: +${d.counts.added} relaciones nuevas, -${d.counts.removed} expiradas.`, actions: [{ type: 'switch_tab', arg: 'tkg' }] };
      } catch (e) { return { answer: 'Error de red al calcular el diff.', actions: [] }; }
    }
    return { answer: 'Comandos de GRAPH: ASOF <fecha>, DIFF <Nd>.', actions: [] };
  }

  async function _handleAlert(args) {
    const sub = (args[0] || '').toUpperCase();
    const actor = _getActorKhipu();
    if (sub === 'LIST') {
      try {
        const r = await fetch(`${_base()}/api/ontology/alerts?owner=${encodeURIComponent(actor)}`);
        const d = await r.json();
        if (!d.alerts || !d.alerts.length) return { answer: 'No tienes alertas configuradas.', actions: [] };
        const lines = d.alerts.map((a, i) => `${i + 1}. ${a.rule.entity || a.rule.region || ''} ${a.rule.metric || ''} ${a.rule.op || ''} ${a.rule.value != null ? a.rule.value : ''}${a.last_fired_at ? ' (disparada)' : ''}`);
        return { answer: 'Tus alertas:\n' + lines.join('\n'), actions: [] };
      } catch (e) { return { answer: 'Error al listar alertas.', actions: [] }; }
    }
    if (sub === 'REGION') {
      const region = args[1]; const kind = (args[2] || '').toUpperCase();
      if (!region || kind !== 'NEWS') return { answer: 'Uso: ALERT REGION <región> NEWS', actions: [] };
      return _createAlert(actor, { metric: 'news_region', region });
    }
    const entity = resolveEntity(args[0] || '');
    const metricTok = (args[1] || '').toUpperCase();
    const op = args[2]; const value = parseFloat(args[3]);
    if (!entity || !['PX', 'NRS'].includes(metricTok) || !op || isNaN(value)) {
      return { answer: 'Uso: ALERT <TICKER> PX|NRS > <valor>  ·  ALERT LIST  ·  ALERT REGION <región> NEWS', actions: [] };
    }
    return _createAlert(actor, { entity: entity.id, metric: metricTok === 'PX' ? 'price' : 'nrs', op, value });
  }

  async function _createAlert(owner, rule) {
    try {
      const r = await fetch(`${_base()}/api/ontology/alerts`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ owner, rule }),
      });
      const d = await r.json();
      if (r.ok) return { answer: `Alerta creada: ${rule.entity || rule.region} ${rule.metric} ${rule.op || ''} ${rule.value != null ? rule.value : ''}.`, actions: [] };
      return { answer: `No se pudo crear la alerta: ${d.error || 'error'} (¿está la ontología configurada?)`, actions: [] };
    } catch (e) { return { answer: 'Error de red al crear la alerta.', actions: [] }; }
  }

  window.KHIPU = { tryParse, resolveEntity };
})();
