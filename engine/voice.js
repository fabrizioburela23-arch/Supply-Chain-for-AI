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
    const isServerMode = typeof SERVER_MODE !== 'undefined' && SERVER_MODE;
    // In server mode, keys live in .env — no client key required
    if (!isServerMode && !elKey && !agentId) {
      this._setStatus('Configura ElevenLabs (key + Agent ID) en ⚙ para activar Bixby', true);
      if (window.V8?.openSettings) window.V8.openSettings();
      return;
    }

    if (!this.audioCtx) await this.init();
    if (this.audioCtx?.state === 'suspended') this.audioCtx.resume();

    // Fetch Bixby system prompt from server (non-blocking — fallback to null)
    const base = (typeof BASE !== 'undefined') ? BASE : '';
    try {
      const pr = await fetch(`${base}/api/voice/bixby-prompt`);
      if (pr.ok) { const pd = await pr.json(); this._systemPrompt = pd.system_prompt || null; }
    } catch { this._systemPrompt = null; }

    try {
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
        this._showOverlay('Bixby conectado — pidiendo micrófono…');
        this._sendInitContext();
        // Start the mic right away so the browser shows the permission prompt
        // immediately on the user gesture. ElevenLabs buffers our chunks until
        // the session is ready; we don't need to wait for the metadata event.
        // (We also retry on conversation_initiation_metadata as a safety net.)
        if (!this._micStream) this._startMic();
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
    // Stop ScriptProcessor mic path
    try { this._micSource?.disconnect(); } catch {}
    try { this._micProcessor?.disconnect(); } catch {}
    try { this._micMute?.disconnect(); } catch {}
    try { this._micStream?.getTracks().forEach(t => t.stop()); } catch {}
    this._micSource = null;
    this._micProcessor = null;
    this._micMute = null;
    this._micStream = null;
    this._micStarting = false;
    // Stop MediaRecorder path (legacy fallback)
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
    // ElevenLabs ConvAI initiation message — fields go at the TOP LEVEL of the
    // message (NOT nested under a conversation_initiation_client_data key).
    // The agent's audio formats (input pcm_16000) are set in the dashboard;
    // we don't override them here (override needs to be enabled per-agent and
    // an invalid field can reject the whole init).
    const msg = {
      type: 'conversation_initiation_client_data',
      custom_llm_extra_body: { khipu_context: ctx },
      dynamic_variables: {
        selected_company: ctx.selected_company?.label || 'ninguna',
        active_tab: ctx.active_tab || 'mapa',
        total_nodes: ctx.total_nodes || 0,
      },
    };
    // Only send a prompt/language override if we actually have a prompt.
    // (If the agent doesn't allow overrides ElevenLabs just ignores it.)
    const override = {};
    if (this._systemPrompt) {
      override.agent = {
        prompt: { prompt: this._systemPrompt },
        language: (typeof LANG !== 'undefined') ? LANG : 'es',
      };
    }
    if (Object.keys(override).length) msg.conversation_config_override = override;
    this.ws.send(JSON.stringify(msg));
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
        nrs: (typeof computeNRS === 'function' ? computeNRS(sel.id) : null),
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
    if (this._micStarting || this._micStream) return; // guard against double-start
    this._micStarting = true;
    const TARGET_RATE = 16000;
    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error('getUserMedia no disponible (¿HTTPS?)');
      }
      // ElevenLabs ConvAI requires raw PCM 16-bit 16kHz mono — NOT webm/opus from MediaRecorder.
      // We use ScriptProcessor to capture Float32 samples, downsample to 16kHz, and send Int16 PCM.
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 },
        video: false,
      });

      if (!this.audioCtx) await this.init();
      if (this.audioCtx.state === 'suspended') await this.audioCtx.resume();
      const actualRate = this.audioCtx.sampleRate; // typically 44100 or 48000

      const srcNode = this.audioCtx.createMediaStreamSource(stream);
      // ScriptProcessor is deprecated but universally supported; AudioWorklet requires HTTPS+module
      const processor = this.audioCtx.createScriptProcessor(4096, 1, 1);
      this._chunksSent = 0;

      processor.onaudioprocess = (ev) => {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
        const f32 = ev.inputBuffer.getChannelData(0);

        // Drive the Jarvis visualizer with live mic level (RMS)
        let sum = 0;
        for (let i = 0; i < f32.length; i++) sum += f32[i] * f32[i];
        this._setMicLevel(Math.sqrt(sum / f32.length));

        let i16;
        if (actualRate !== TARGET_RATE) {
          // Downsample via averaging window (better than nearest-neighbor for VAD)
          const step = actualRate / TARGET_RATE;
          const outLen = Math.floor(f32.length / step);
          i16 = new Int16Array(outLen);
          for (let i = 0; i < outLen; i++) {
            const s = Math.max(-1, Math.min(1, f32[Math.floor(i * step)]));
            i16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
          }
        } else {
          i16 = new Int16Array(f32.length);
          for (let i = 0; i < f32.length; i++) {
            const s = Math.max(-1, Math.min(1, f32[i]));
            i16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
          }
        }
        const bytes = new Uint8Array(i16.buffer);
        let bin = '';
        for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
        this.ws.send(JSON.stringify({ user_audio_chunk: btoa(bin) }));
        this._chunksSent++;
      };

      srcNode.connect(processor);
      // ScriptProcessor must connect to destination to fire onaudioprocess in
      // some browsers. Route through a muted gain so we don't create feedback.
      const mute = this.audioCtx.createGain();
      mute.gain.value = 0;
      processor.connect(mute);
      mute.connect(this.audioCtx.destination);

      this._micSrc = srcNode;
      this._micSource = srcNode;
      this._micProcessor = processor;
      this._micMute = mute;
      this._micStream = stream;
      this.mediaRecorder = null;
      this._micStarting = false;
      this._showOverlay('🎙️ Bixby te escucha — habla');
    } catch (e) {
      this._micStarting = false;
      const msg = (e && (e.name === 'NotAllowedError' || e.name === 'PermissionDeniedError'))
        ? 'Permiso de micrófono denegado — actívalo en el navegador'
        : 'Micrófono no disponible: ' + (e?.message || e);
      this._setStatus(msg, true);
      // Keep the WS open so the agent can still talk; just no mic input.
    }
  },

  // Map RMS mic level (0..~0.3) to the height of the visualizer bars
  _setMicLevel(rms) {
    const now = performance.now();
    if (now - (this._lastVizUpdate || 0) < 60) return; // throttle to ~16fps
    this._lastVizUpdate = now;
    const bars = document.querySelectorAll('#bixby-viz .bvbar');
    if (!bars.length) return;
    const level = Math.min(1, rms * 6); // scale up; speech RMS is small
    // Jarvis effect: the brain also reacts to the user's voice
    if (level > 0.08 && typeof window !== 'undefined') {
      window.__bixbyEnergy = Math.max(window.__bixbyEnergy || 0, level);
    }
    bars.forEach((b, i) => {
      // pseudo-random spread so bars look lively, scaled by real level
      const jitter = 0.4 + 0.6 * Math.abs(Math.sin(now / 120 + i));
      const h = 3 + level * 22 * jitter;
      b.style.height = h.toFixed(1) + 'px';
      b.style.animationPlayState = level > 0.05 ? 'paused' : 'running';
    });
  },

  _handleMessage(msg) {
    switch (msg.type) {
      case 'conversation_initiation_metadata': {
        // Server confirmed session is ready. Mic normally started on ws.onopen;
        // this is a safety net in case the permission prompt was dismissed/raced.
        if (!this._micStream && !this._micStarting) this._startMic();
        else this._showOverlay('🎙️ Bixby te escucha — habla');
        break;
      }
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
    // Jarvis effect: make the 3D brain react while Bixby speaks
    if (typeof window !== 'undefined') window.__bixbyEnergy = 1;
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
        const scores = ids.map(id => {
          const v = typeof computeNRS === 'function' ? computeNRS(id) : 50;
          return { label: NODE_BY_ID[id]?.label || id, nrs: v };
        });
        const avg = scores.length ? Math.round(scores.reduce((s, x) => s + x.nrs, 0) / scores.length) : 0;
        respond({ portfolio_count: scores.length, avg_nrs: avg,
          companies: scores.map(x => ({ label: x.label, nrs: x.nrs, level: x.nrs >= 70 ? 'high' : x.nrs >= 40 ? 'medium' : 'low' })) });
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
      case 'get_company_info': {
        const n = NODES.find(n => n.mkt === params.ticker || n.id === params.ticker
          || n.label.toLowerCase().includes((params.company_name || '').toLowerCase()));
        if (n) {
          const q = (typeof MKT !== 'undefined' && n.mkt) ? MKT.quotes[n.mkt] : null;
          respond({
            id: n.id, label: n.label, ticker: n.mkt || null,
            category: (typeof catLabel === 'function') ? catLabel(n.cat) : n.cat,
            geo: n.loc || n.country || null,
            price: q?.close || null, change_pct: (q?.close && q?.prev) ? ((q.close - q.prev) / q.prev * 100).toFixed(2) : null,
            role: n.role || null,
          });
        } else respond({ success: false, error: 'Company not found' });
        break;
      }
      case 'get_risk_score': {
        const n = NODES.find(n => n.mkt === params.ticker || n.id === params.ticker
          || n.label.toLowerCase().includes((params.company_name || '').toLowerCase()));
        if (n && typeof computeNRS === 'function') {
          try {
            const nrs = computeNRS(n.id);
            respond({ success: true, company: n.label, nrs: nrs,
              level: nrs >= 70 ? 'high' : nrs >= 40 ? 'medium' : 'low' });
          } catch(e) { respond({ success: false, error: e.message }); }
        } else respond({ success: false, error: 'Company not found or NRS unavailable' });
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
