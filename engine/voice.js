// engine/voice.js — Bixby, el asistente de voz de Khipu Finance
// Cliente WebSocket de ElevenLabs Conversational AI. Bixby es el "Jarvis de las
// finanzas": escucha por micrófono, responde por voz, y puede controlar la terminal
// (navegar a empresas, correr stress-tests, lanzar simulaciones, consultar el RAG).
//
// Referencia en andino: el khipu era el sistema de registro de los Andes; Bixby es
// quien "lee el khipu" de la cadena de valor global por voz.
//
// Depende de app.html: Keys, BASE, NODES, NODE_BY_ID, MKT, selected, stressId,
//   stressAffected, activateStress, jumpTo, computeNRS, catLabel, toast, LANG, activeTab

const BixbyVoice = {
  ws: null,
  isConnected: false,
  mediaRecorder: null,
  audioCtx: null,
  audioQueue: [],
  isPlaying: false,

  async init() {
    try {
      this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    } catch {}
  },

  async toggle() {
    this.isConnected ? this.disconnect() : await this.connect();
  },

  stop() { this.disconnect(); },

  async connect() {
    const elKey = (typeof Keys !== 'undefined' && Keys.get('elevenlabs')) || localStorage.getItem('key_elevenlabs');
    const agentId = localStorage.getItem('elevenlabs_agent_id');
    if (!elKey && !agentId) {
      this._setStatus('Configura ElevenLabs (key + Agent ID) en ⚙ para activar Bixby', true);
      if (window.V8?.openSettings) window.V8.openSettings();
      return;
    }

    if (!this.audioCtx) await this.init();
    if (this.audioCtx?.state === 'suspended') this.audioCtx.resume();

    try {
      const base = (typeof BASE !== 'undefined') ? BASE : '';
      const r = await fetch(`${base}/api/voice/session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_id: agentId }),
      });
      const data = await r.json();
      if (data.error) throw new Error(data.error);
      const signedUrl = data.signed_url || data.signedUrl;
      if (!signedUrl) throw new Error('No signed_url devuelto por el servidor');

      this.ws = new WebSocket(signedUrl);
      this.ws.onopen = () => {
        this.isConnected = true;
        this._showOverlay('Bixby conectado — ¡Habla!');
        this._sendInitContext();
        this._startMic();
      };
      this.ws.onmessage = e => this._handleMessage(JSON.parse(e.data));
      this.ws.onerror = () => { this._setStatus('Error de conexión con Bixby', true); this.disconnect(); };
      this.ws.onclose = () => { this.isConnected = false; this._hideOverlay(); };
    } catch (e) {
      this._setStatus('Bixby: ' + e.message, true);
    }
  },

  disconnect() {
    try { this.ws?.close(); } catch {}
    this.ws = null;
    try { this.mediaRecorder?.stop(); } catch {}
    this.mediaRecorder = null;
    this.isConnected = false;
    this.audioQueue = [];
    this.isPlaying = false;
    this._hideOverlay();
  },

  _sendInitContext() {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    const ctx = this._buildContext();
    this.ws.send(JSON.stringify({
      type: 'conversation_initiation_client_data',
      conversation_initiation_client_data: {
        custom_llm_extra_body: { khipu_context: ctx },
      },
    }));
  },

  _buildContext() {
    const sel = (typeof selected !== 'undefined' && selected) ? NODE_BY_ID[selected] : null;
    const portfolio = Object.keys((typeof MKT !== 'undefined' && MKT.pos) || {}).length;
    const hasStress = typeof stressId !== 'undefined' && !!stressId;
    return {
      app: 'Khipu Finance',
      assistant: 'Bixby',
      selected_company: sel ? {
        id: sel.id, label: sel.label, ticker: sel.mkt,
        cat: (typeof catLabel === 'function' ? catLabel(sel.cat) : sel.cat),
        nrs: (typeof computeNRS === 'function' ? computeNRS(sel.id).total : null),
        price: sel.mkt ? (MKT.quotes[sel.mkt]?.close || null) : null,
      } : null,
      portfolio_count: portfolio,
      stress_active: hasStress,
      stressed_company: hasStress ? NODE_BY_ID[stressId]?.label : null,
      total_nodes: (typeof NODES !== 'undefined') ? NODES.length : 0,
      active_tab: (typeof activeTab !== 'undefined') ? activeTab : null,
      language: (typeof LANG !== 'undefined') ? LANG : 'es',
    };
  },

  async _startMic() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      this.mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
      this.mediaRecorder.ondataavailable = e => {
        if (e.data.size > 0 && this.ws?.readyState === WebSocket.OPEN) {
          e.data.arrayBuffer().then(buf => {
            let bin = '';
            const bytes = new Uint8Array(buf);
            for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
            const b64 = btoa(bin);
            this.ws.send(JSON.stringify({ user_audio_chunk: b64 }));
          });
        }
      };
      this.mediaRecorder.start(250);
    } catch (e) {
      this._setStatus('Micrófono no disponible: ' + e.message, true);
      this.disconnect();
    }
  },

  _handleMessage(msg) {
    switch (msg.type) {
      case 'audio': {
        const chunk = msg.audio_event?.audio_base_64;
        if (chunk) this._enqueueAudio(chunk);
        break;
      }
      case 'agent_response': {
        const text = msg.agent_response_event?.agent_response || '';
        this._showOverlay('Bixby: ' + text.slice(0, 80));
        this._onAgentResponse(text);
        break;
      }
      case 'user_transcript': {
        const t = msg.user_transcription_event?.user_transcript || '';
        if (t) this._showOverlay('Tú: ' + t.slice(0, 80));
        break;
      }
      case 'client_tool_call':
        this._handleToolCall(msg.client_tool_call);
        break;
      case 'interruption':
        this.audioQueue = []; this.isPlaying = false;
        break;
      case 'ping':
        if (msg.ping_event?.event_id != null && this.ws?.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({ type: 'pong', event_id: msg.ping_event.event_id }));
        }
        break;
    }
  },

  _enqueueAudio(b64chunk) {
    this.audioQueue.push(b64chunk);
    if (!this.isPlaying) this._playNext();
  },

  async _playNext() {
    if (!this.audioQueue.length) { this.isPlaying = false; return; }
    this.isPlaying = true;
    const chunk = this.audioQueue.shift();
    try {
      const bytes = Uint8Array.from(atob(chunk), c => c.charCodeAt(0));
      // ElevenLabs convai envía PCM 16kHz mono por defecto
      const pcm = new Int16Array(bytes.buffer);
      const f32 = new Float32Array(pcm.length);
      for (let i = 0; i < pcm.length; i++) f32[i] = pcm[i] / 32768;
      const buffer = this.audioCtx.createBuffer(1, f32.length, 16000);
      buffer.getChannelData(0).set(f32);
      const src = this.audioCtx.createBufferSource();
      src.buffer = buffer;
      src.connect(this.audioCtx.destination);
      src.onended = () => this._playNext();
      src.start();
    } catch { this._playNext(); }
  },

  _onAgentResponse(text) {
    // Comandos embebidos opcionales: [NAV:NVDA] [STRESS:ASML] [SIM:taiwan_conflict]
    const nav = text.match(/\[NAV:([A-Za-z0-9_]+)\]/);
    const stress = text.match(/\[STRESS:([A-Za-z0-9_]+)\]/);
    const sim = text.match(/\[SIM:([a-z_]+)\]/);
    if (nav && typeof jumpTo === 'function') jumpTo(nav[1]);
    if (stress) {
      const n = NODES.find(n => n.mkt === stress[1] || n.id === stress[1]);
      if (n && typeof activateStress === 'function') activateStress(n.id);
    }
    if (sim && window.nexusCore?.runPreset) window.nexusCore.runPreset(sim[1]);
  },

  _handleToolCall(event) {
    const { tool_name, parameters, tool_call_id } = event || {};
    const params = typeof parameters === 'string' ? JSON.parse(parameters || '{}') : (parameters || {});
    const respond = (result) => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({
          type: 'client_tool_result',
          tool_call_id,
          result: JSON.stringify(result),
          is_error: false,
        }));
      }
    };

    switch (tool_name) {
      case 'navigate_to_company': {
        const n = NODES.find(n => n.mkt === params.ticker || n.id === params.ticker
          || n.label.toLowerCase().includes((params.company_name || '').toLowerCase()));
        if (n) {
          if (typeof jumpTo === 'function') jumpTo(n.id);
          if (window.khipuGraph3D?.active) window.khipuGraph3D.selectNode(n.id);
          this.updateContext();
          respond({ success: true, company: n.label, ticker: n.mkt });
        } else respond({ success: false, error: 'Company not found' });
        break;
      }
      case 'run_stress_test': {
        const n = NODES.find(n => n.mkt === params.ticker || n.id === params.ticker);
        if (n && typeof activateStress === 'function') {
          activateStress(n.id);
          const cascade = (typeof stressAffected !== 'undefined') ? stressAffected.size : 0;
          respond({ success: true, company: n.label, affected_count: cascade,
            affected_pct: Math.round(cascade / NODES.length * 100) });
        } else respond({ success: false, error: 'Company not found' });
        break;
      }
      case 'run_simulation': {
        const preset = window.ScenarioBuilder?.PRESETS?.[params.scenario_id];
        if (preset && window.nexusCore) {
          respond({ success: true, message: 'Simulation starting...', scenario: preset.title });
          setTimeout(() => window.nexusCore.runPreset(params.scenario_id), 500);
        } else respond({ success: false, error: 'Unknown scenario' });
        break;
      }
      case 'get_portfolio_risk': {
        const ids = Object.keys((MKT && MKT.pos) || {});
        const scores = ids.map(id => ({ label: NODE_BY_ID[id]?.label, nrs: computeNRS(id) }));
        const avg = scores.length ? Math.round(scores.reduce((s, x) => s + x.nrs.total, 0) / scores.length) : 0;
        respond({ portfolio_count: scores.length, avg_nrs: avg,
          companies: scores.map(x => ({ label: x.label, nrs: x.nrs.total, level: x.nrs.label })) });
        break;
      }
      case 'search_second_brain': {
        const base = (typeof BASE !== 'undefined') ? BASE : '';
        fetch(`${base}/api/rag/query/ai`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: params.query || '' }),
        }).then(r => r.json()).then(d => {
          respond({ success: true, answer: (d.answer || '').slice(0, 500), sources_count: d.context_used });
        }).catch(() => respond({ success: false, error: 'RAG unavailable' }));
        break;
      }
      default:
        respond({ success: false, error: `Unknown tool: ${tool_name}` });
    }
  },

  updateContext() {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    this.ws.send(JSON.stringify({
      type: 'contextual_update',
      text: `[CONTEXT_UPDATE] ${JSON.stringify(this._buildContext())}`,
    }));
  },

  // ── UI overlay ───────────────────────────────────────────────────────────
  _showOverlay(text) {
    const el = document.getElementById('bixby-status');
    if (el) { el.style.display = 'flex'; this._setStatus(text); }
  },
  _hideOverlay() {
    const el = document.getElementById('bixby-status');
    if (el) el.style.display = 'none';
  },
  _setStatus(text, isError) {
    const t = document.getElementById('bixby-text');
    if (t) t.textContent = text;
    if (isError) {
      const el = document.getElementById('bixby-status');
      if (el) el.style.display = 'flex';
      if (typeof toast === 'function') toast(text);
    }
  },
};

window.BixbyVoice = BixbyVoice;
