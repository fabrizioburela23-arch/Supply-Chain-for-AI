// engine/command_center.js — Bixby Command Center (Khipu Finance)
// Guía discreta: por defecto solo un ORBE en la esquina (no tapa nada). Al
// hacer clic se abre la barra + feed; se colapsa de nuevo. Escribe O habla;
// Bixby ejecuta y muestra la respuesta inline. El orbe nunca obstruye.
// Reutiliza: switchTab, jumpTo, activateStress, nexusCore.runPreset,
// _openSecondBrain, canvasGenerate (_cvRenderCard) y BixbyVoice (voz).
// Endpoint: /api/ai/command. Expone window.BixbyCC.

(function () {
  'use strict';

  const css = `
  #bcc-root{position:fixed;right:20px;bottom:20px;z-index:980;
    font-family:'Geist','Inter',system-ui,sans-serif;display:flex;flex-direction:column;
    align-items:flex-end;gap:12px;pointer-events:none}
  #bcc-panel{display:none;flex-direction:column;gap:10px;width:min(420px,92vw);pointer-events:auto}
  #bcc-root.open #bcc-panel{display:flex}
  #bcc-feed{display:flex;flex-direction:column;gap:10px;max-height:54vh;overflow-y:auto}
  #bcc-feed:empty{display:none}
  .bcc-card{background:rgba(12,16,28,.95);border:1px solid rgba(120,150,220,.22);border-radius:14px;
    padding:14px 16px;box-shadow:0 10px 40px rgba(0,0,0,.45);backdrop-filter:blur(14px);
    -webkit-backdrop-filter:blur(14px);color:#e7eefb;animation:bccIn .26s cubic-bezier(.2,.8,.2,1)}
  @keyframes bccIn{from{opacity:0;transform:translateY(12px) scale(.98)}to{opacity:1;transform:none}}
  .bcc-card .bcc-q{font-size:11px;color:#8fa6d4;margin-bottom:6px;display:flex;align-items:center;gap:6px}
  .bcc-card .bcc-a{font-size:14px;line-height:1.5;color:#eef3fc}
  .bcc-acts{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
  .bcc-chip{font-size:11px;padding:4px 10px;border-radius:20px;background:rgba(80,120,210,.18);
    border:1px solid rgba(120,150,220,.3);color:#bcd0f5;display:flex;align-items:center;gap:5px}
  .bcc-chip.go{cursor:pointer}.bcc-chip.go:hover{background:rgba(80,120,210,.35)}
  #bcc-bar{display:flex;align-items:center;gap:8px;pointer-events:auto;
    background:linear-gradient(180deg,rgba(18,22,38,.97),rgba(10,12,22,.97));
    border:1px solid rgba(130,100,255,.4);border-radius:26px;padding:7px 8px 7px 14px;
    box-shadow:0 12px 48px rgba(0,0,0,.5),0 0 26px rgba(130,100,255,.16)}
  #bcc-input{flex:1;min-width:0;background:transparent;border:none;outline:none;color:#eef3fc;
    font-size:14px;font-family:inherit;padding:6px 2px}
  #bcc-input::placeholder{color:#7e8db0}
  .bcc-mini{flex-shrink:0;width:34px;height:34px;border-radius:50%;border:none;cursor:pointer;
    display:flex;align-items:center;justify-content:center;font-size:14px;transition:transform .15s,opacity .15s}
  .bcc-mini:hover{transform:scale(1.08)}
  #bcc-mic{background:rgba(130,100,255,.18);color:#cabeff;border:1px solid rgba(130,100,255,.4)}
  #bcc-send{background:linear-gradient(135deg,#7c3aed,#4f46e5);color:#fff}
  #bcc-collapse{background:rgba(255,255,255,.06);color:#9fb0d0}
  /* Orbe FAB siempre visible */
  #bcc-orb{pointer-events:auto;width:54px;height:54px;border-radius:50%;cursor:pointer;position:relative;
    background:radial-gradient(circle at 35% 30%,#c4b5ff,#7c3aed 55%,#3b1d8f);
    box-shadow:0 6px 22px rgba(0,0,0,.45),0 0 22px rgba(130,100,255,.6);
    transition:transform .15s;display:flex;align-items:center;justify-content:center}
  #bcc-orb:hover{transform:scale(1.07)}
  #bcc-orb::after{content:'';position:absolute;inset:0;border-radius:50%;
    box-shadow:0 0 0 0 rgba(130,100,255,.5);animation:bccRing 2.6s ease-out infinite}
  #bcc-root.open #bcc-orb::after{animation:none}
  @keyframes bccRing{0%{box-shadow:0 0 0 0 rgba(130,100,255,.5)}70%{box-shadow:0 0 0 14px rgba(130,100,255,0)}100%{box-shadow:0 0 0 0 rgba(130,100,255,0)}}
  #bcc-orb.listening{animation:bccPulse 1.1s ease-in-out infinite}
  #bcc-orb.thinking{animation:bccSpin 1s linear infinite}
  @keyframes bccPulse{0%,100%{box-shadow:0 6px 22px rgba(0,0,0,.45),0 0 18px rgba(130,100,255,.7)}50%{box-shadow:0 6px 22px rgba(0,0,0,.45),0 0 34px 8px rgba(130,100,255,.95)}}
  @keyframes bccSpin{to{filter:hue-rotate(360deg)}}
  #bcc-orb .bcc-spark{color:#fff;font-size:22px;line-height:1;filter:drop-shadow(0 0 4px rgba(255,255,255,.5))}
  /* Burbuja de bienvenida (guía) */
  #bcc-welcome{pointer-events:auto;max-width:240px;background:rgba(12,16,28,.96);border:1px solid rgba(130,100,255,.4);
    border-radius:14px;padding:12px 14px;color:#e7eefb;font-size:12.5px;line-height:1.5;
    box-shadow:0 10px 36px rgba(0,0,0,.5);position:relative;animation:bccIn .3s ease}
  #bcc-welcome b{color:#cabeff}
  #bcc-welcome .x{position:absolute;top:6px;right:9px;cursor:pointer;color:#7e8db0;font-size:13px}
  `;

  const CC = {
    inited: false, busy: false, open: false,

    init() {
      if (this.inited) return; this.inited = true;
      const style = document.createElement('style'); style.textContent = css; document.head.appendChild(style);
      const root = document.createElement('div'); root.id = 'bcc-root';
      root.innerHTML = `
        <div id="bcc-panel">
          <div id="bcc-feed"></div>
          <div id="bcc-bar">
            <input id="bcc-input" type="text" autocomplete="off"
              placeholder="Pregúntale a Bixby… (⌘K)">
            <button id="bcc-mic" class="bcc-mini" title="Hablar (voz)">🎙</button>
            <button id="bcc-send" class="bcc-mini" title="Enviar">➤</button>
            <button id="bcc-collapse" class="bcc-mini" title="Minimizar">⌄</button>
          </div>
        </div>
        <div id="bcc-orb" title="Bixby — tu guía (clic para abrir)"><span class="bcc-spark">✦</span></div>`;
      document.body.appendChild(root);
      this.root = root;

      const input = document.getElementById('bcc-input');
      input.addEventListener('keydown', e => { if (e.key === 'Enter') this.submit(input.value); });
      document.getElementById('bcc-send').addEventListener('click', () => this.submit(input.value));
      document.getElementById('bcc-mic').addEventListener('click', () => this._toggleVoice());
      document.getElementById('bcc-collapse').addEventListener('click', () => this.setOpen(false));
      document.getElementById('bcc-orb').addEventListener('click', () => this.setOpen(!this.open));

      window.addEventListener('keydown', e => {
        if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); this.setOpen(true); this.focus(); }
        if (e.key === 'Escape' && this.open) this.setOpen(false);
      });
      window.BixbyCCsetState = (s) => this.setOrbState(s);

      this._maybeWelcome();
    },

    setOpen(v) {
      this.open = v;
      this.root.classList.toggle('open', v);
      this._dismissWelcome();
      if (v) setTimeout(() => this.focus(), 60);
    },

    focus() { const i = document.getElementById('bcc-input'); if (i) { i.focus(); i.select(); } },

    _maybeWelcome() {
      try { if (localStorage.getItem('bcc_welcomed')) return; } catch (e) {}
      const b = document.createElement('div'); b.id = 'bcc-welcome';
      b.innerHTML = `<span class="x">✕</span><b>👋 Soy Bixby, tu guía.</b><br>
        Pídeme que te muestre algo: <i>"compara NVIDIA, TSMC y ASML"</i> o
        <i>"qué pasa si cae TSMC"</i>. Abro el tab, genero el dato y te lo explico.`;
      this.root.insertBefore(b, this.root.lastChild);
      b.querySelector('.x').addEventListener('click', (e) => { e.stopPropagation(); this._dismissWelcome(); });
    },
    _dismissWelcome() {
      const b = document.getElementById('bcc-welcome');
      if (b) b.remove();
      try { localStorage.setItem('bcc_welcomed', '1'); } catch (e) {}
    },

    setOrbState(s) {
      const orb = document.getElementById('bcc-orb'); if (!orb) return;
      orb.classList.remove('listening', 'thinking');
      if (s === 'listening') orb.classList.add('listening');
      if (s === 'thinking') orb.classList.add('thinking');
    },

    _toggleVoice() {
      if (window.BixbyVoice && window.BixbyVoice.toggle) {
        this.setOrbState('listening');
        try { window.BixbyVoice.toggle(); } catch (e) {}
      } else {
        this._toast('La voz necesita ELEVENLABS_KEY configurada. Igual puedes escribirme aquí.');
      }
    },

    _nodesCtx() {
      return (window.NODES || []).slice(0, 400).map(n => ({
        id: n.id, label: n.label, ticker: n.ticker || n.mkt || '',
      }));
    },

    async submit(text) {
      text = (text || '').trim();
      if (!text || this.busy) { if (!text) this.focus(); return; }
      this.busy = true; this.setOpen(true);
      const input = document.getElementById('bcc-input');
      const send = document.getElementById('bcc-send');
      if (input) input.value = '';
      if (send) send.disabled = true;
      this.setOrbState('thinking');

      const card = this._addCard(text);
      const ans = card.querySelector('.bcc-a');

      try {
        const base = (typeof BASE !== 'undefined') ? BASE : '';
        const sel = window._selectedNode || null;
        const r = await fetch(`${base}/api/ai/command`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: text, nodes: this._nodesCtx(), selected: sel }),
        });
        const d = await r.json();
        ans.textContent = d.answer || (d.error ? '⚠ ' + d.error : 'Listo.');
        if (Array.isArray(d.actions) && d.actions.length) await this._runActions(d.actions, card);
      } catch (e) {
        ans.innerHTML = `<span style="color:#f6a">No pude procesar eso: ${this._esc(e.message || e)}</span>`;
      } finally {
        this.busy = false;
        if (send) send.disabled = false;
        this.setOrbState(null);
        this.focus();
      }
    },

    _addCard(query) {
      const feed = document.getElementById('bcc-feed');
      const card = document.createElement('div'); card.className = 'bcc-card';
      card.innerHTML = `<div class="bcc-q">🔮 ${this._esc(query)}</div>
        <div class="bcc-a"><span style="opacity:.6">pensando…</span></div>`;
      feed.appendChild(card);
      while (feed.children.length > 8) feed.removeChild(feed.firstChild);
      feed.scrollTop = feed.scrollHeight;
      return card;
    },

    async _runActions(actions, card) {
      const acts = document.createElement('div'); acts.className = 'bcc-acts'; card.appendChild(acts);
      for (const a of actions) {
        const arg = a.arg;
        try {
          if (a.type === 'switch_tab' && window.switchTab) {
            window.switchTab(arg); this._chip(acts, `📂 ${arg}`);
          } else if (a.type === 'navigate' && window.jumpTo) {
            if (window.switchTab) window.switchTab('map');
            setTimeout(() => window.jumpTo(arg), 120);
            this._chip(acts, `🎯 ${this._label(arg)}`, () => { window.switchTab('map'); setTimeout(() => window.jumpTo(arg), 80); });
          } else if (a.type === 'stress' && window.activateStress) {
            if (window.switchTab) window.switchTab('map');
            setTimeout(() => window.activateStress(arg), 150);
            this._chip(acts, `🚨 Stress: ${this._label(arg)}`);
          } else if (a.type === 'simulate') {
            if (window.switchTab) window.switchTab('simulation');
            setTimeout(() => { try { window.nexusCore && window.nexusCore.runPreset && window.nexusCore.runPreset(arg); } catch (e) {} }, 200);
            this._chip(acts, `🧬 Simular: ${arg}`);
          } else if (a.type === 'second_brain' && window._openSecondBrain) {
            window._openSecondBrain(arg); this._chip(acts, `🧠 ${this._label(arg)}`);
          } else if (a.type === 'chart') {
            this._chip(acts, `📊 generando gráfico…`);
            await this._chartInline(arg, card);
          }
        } catch (e) { /* una acción que falla no rompe las demás */ }
      }
      if (!acts.children.length) acts.remove();
    },

    async _chartInline(query, card) {
      if (typeof window._cvRenderCard !== 'function') {
        if (window.switchTab) window.switchTab('canvas');
        const qi = document.getElementById('canvas-query');
        if (qi) { qi.value = query; if (window.canvasGenerate) window.canvasGenerate(); }
        return;
      }
      const cardId = 'bcc-cv-' + Math.floor(performance.now());
      const holder = document.createElement('div');
      holder.id = cardId; holder.className = 'cv-card';
      holder.style.cssText = 'margin-top:10px;min-width:0;max-width:none;background:rgba(8,12,22,.6)';
      holder.innerHTML = '<div style="height:120px;display:flex;align-items:center;justify-content:center;color:#8fa6d4;font-size:12px">Generando…</div>';
      card.appendChild(holder);
      try {
        const base = (typeof BASE !== 'undefined') ? BASE : '';
        let live = null;
        if (window.canvasEnrichData) { try { const en = await window.canvasEnrichData(query); live = (en && en.live) || null; } catch (e) {} }
        const nodeCtx = (window.NODES || []).slice(0, 300).map(n => ({
          id: n.id, label: n.label, cat: n.cat, mkt: n.mkt || null,
          margin: n.margin ?? null, growth: n.growth || null, port: n.port || null,
          country: n.country || null, preipo: n.preipo || null,
          nrs: typeof window.computeNRS === 'function' ? window.computeNRS(n.id) : null,
        }));
        const quotesCtx = {};
        for (const [t, q] of Object.entries((window.MKT || {}).quotes || {})) if (q) quotesCtx[t] = { close: q.close, prev: q.prev };
        const r = await fetch(`${base}/api/canvas/generate`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query, context: { nodes: nodeCtx, quotes: quotesCtx, live } }),
        });
        const d = await r.json();
        if (d.error) throw new Error(d.error);
        window._cvRenderCard(cardId, query, d.spec, d.model);
      } catch (e) {
        holder.innerHTML = `<div style="padding:14px;color:#f87171;font-size:12px">⚠ ${this._esc(e.message || e)}</div>`;
      }
    },

    _chip(parent, text, onclick) {
      const c = document.createElement('span');
      c.className = 'bcc-chip' + (onclick ? ' go' : '');
      c.textContent = text;
      if (onclick) c.addEventListener('click', onclick);
      parent.appendChild(c);
      return c;
    },

    _label(id) { const n = (window.NODE_BY_ID || {})[id]; return n ? n.label : id; },
    _esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); },
    _toast(m) { if (window.toast) window.toast(m); else { this.setOpen(true); const c = this._addCard('Bixby'); c.querySelector('.bcc-a').textContent = m; } },
  };

  window.BixbyCC = CC;
  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    setTimeout(() => CC.init(), 300);
  } else {
    window.addEventListener('DOMContentLoaded', () => setTimeout(() => CC.init(), 300));
  }
})();
