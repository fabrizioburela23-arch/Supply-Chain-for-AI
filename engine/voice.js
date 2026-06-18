// engine/voice.js — Bixby, el asistente de voz de Khipu Finance
// Cliente WebSocket de ElevenLabs Conversational AI. Bixby es el "Jarvis de las
// finanzas": escucha por micrófono, responde por voz, y puede controlar la terminal.
//
// Depende de app.html: Keys, BASE, NODES, NODE_BY_ID, MKT, selected, stressId,
//   stressAffected, activateStress, jumpTo, computeNRS, catLabel, toast, LANG, activeTab

const BixbyVoice = {
  ws: null,
  isConnected: false,
  audioCtx: null,
  audioQueue: [],
  isPlaying: false,

  async init() {
    if (this.audioCtx) return;
    try {
      this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    } catch {}
  },

  async toggle() {
    this.isConnected ? this.disconnect() : await this.connect();
  },

  stop() { this.disconnect(); },

  async connect() {
    const isServerMode = typeof SERVER_MODE !== 'undefined' && SERVER_MODE;
    const elKey = (typeof Keys !== 'undefined' && Keys.get('elevenlabs')) || localStorage.getItem('key_elevenlabs');
    const agentId = localStorage.getItem('elevenlabs_agent_id');
    if (!isServerMode && !elKey && !agentId) {
      this._setStatus('Configura ElevenLabs (key + Agent ID) en ⚙ para activar Bixby', true);
      if (window.V8?.openSettings) window.V8.openSettings();
      return;
    }

    // ── Step 1: request microphone NOW while the user gesture is still active ──
    // Mobile browsers (Chrome Android, Safari iOS) revoke the gesture context
    // after the first await. Asking here ensures the permission dialog appears
    // immediately and the stream is ready when the WebSocket opens.
    this._showOverlay('Bixby — pidiendo micrófono…');
    let preStream = null;
    if (navigator.mediaDevices?.getUserMedia) {
      try {
        preStream = await navigator.mediaDevices.getUserMedia({
          audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1, sampleRate: { ideal: 16000 } },
          video: false,
        });
        this._showOverlay('Bixby — conectando…');
      } catch (e) {
        const msg = (e.name === 'NotAllowedError' || e.name === 'PermissionDeniedError')
          ? 'Permiso de micrófono denegado — actívalo en el navegador'
          : 'Micrófono no disponible: ' + (e?.message || e);
        this._setStatus(msg, true);
        return; // Can't proceed without mic
      }
    } else {
      this._setStatus('getUserMedia no disponible (¿HTTPS?)', true);
      return;
    }

    // ── Step 2: init AudioContext (user gesture still active) ──────────────────
    await this.init();
    if (this.audioCtx?.state === 'suspended') await this.audioCtx.resume();

    // ── Step 3: fetch credentials from server ──────────────────────────────────
    const base = (typeof BASE !== 'undefined') ? BASE : '';
    try {
      const pr = await fetch(`${base}/api/voice/bixby-prompt`);
      if (pr.ok) {
        const pd = await pr.json();
        this._systemPrompt = pd.system_prompt || null;
        // Server sets allow_override: true only when the ElevenLabs agent has
        // "Allow overrides" enabled in its dashboard settings.
        this._allowPromptOverride = !!pd.allow_override;
      }
    } catch { this._systemPrompt = null; this._allowPromptOverride = false; }

    let signedUrl;
    try {
      const r = await fetch(`${base}/api/voice/session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_id: agentId }),
      });
      const data = await r.json();
      if (data.error) throw new Error(data.error);
      signedUrl = data.signed_url || data.signedUrl;
      if (!signedUrl) throw new Error('No signed_url devuelto por el servidor');
    } catch (e) {
      this._setStatus('Bixby: ' + e.message, true);
      preStream.getTracks().forEach(t => t.stop()); // release mic if no WS
      return;
    }

    // ── Step 4: open WebSocket and wire up audio ───────────────────────────────
    this.ws = new WebSocket(signedUrl);

    this.ws.onopen = () => {
      this.isConnected = true;
      this._showOverlay('Bixby — iniciando sesión…');
      this._sendInitContext();
      this._startMicWithStream(preStream);
    };

    this.ws.onmessage = e => {
      try { this._handleMessage(JSON.parse(e.data)); } catch {}
    };
    this.ws.onerror = (ev) => {
      // onerror fires before onclose — don't call disconnect() here because
      // that triggers ws.close() → onclose fires again and double-hides.
      this._setStatus('Error de red con Bixby — reintenta', true);
    };
    this.ws.onclose = (ev) => {
      // Skip if disconnect() already cleaned up (isConnected already false)
      if (!this.isConnected && !this._micStream) return;
      this.isConnected = false;
      this._stopMic();
      this.ws = null;
      this.audioQueue = [];
      this.isPlaying = false;
      if (ev.code === 1000 || ev.code === 1001) {
        this._hideOverlay();
      } else {
        // Unexpected close — show reason so user can diagnose
        const reason = ev.reason
          ? ev.reason.slice(0, 120)
          : `Bixby desconectado (código ${ev.code})`;
        this._setStatus(reason, true);
      }
    };
  },

  disconnect() {
    this.isConnected = false;
    this._stopMic();
    this.audioQueue = [];
    this.isPlaying = false;
    if (this.ws) {
      // Closing with code 1000 (normal) prevents onclose from showing an error
      try { this.ws.close(1000, 'user disconnected'); } catch {}
      this.ws = null;
    }
    this._hideOverlay();
  },

  _stopMic() {
    try { this._micSource?.disconnect(); } catch {}
    try { this._micProcessor?.disconnect(); } catch {}
    try { this._micMute?.disconnect(); } catch {}
    try { this._micStream?.getTracks().forEach(t => t.stop()); } catch {}
    this._micSource = null;
    this._micProcessor = null;
    this._micMute = null;
    this._micStream = null;
  },

  _startMicWithStream(stream) {
    if (this._micStream) return; // already running
    const TARGET_RATE = 16000;
    try {
      const actualRate = this.audioCtx.sampleRate; // 44100 or 48000 typically

      const srcNode = this.audioCtx.createMediaStreamSource(stream);

      // ScriptProcessor: deprecated but universally supported (AudioWorklet needs
      // a module worker which complicates deployment). Buffer size 2048 is smaller
      // so latency is lower; still large enough to avoid glitches.
      const bufSize = 2048;
      const processor = this.audioCtx.createScriptProcessor(bufSize, 1, 1);

      processor.onaudioprocess = (ev) => {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
        const f32 = ev.inputBuffer.getChannelData(0);

        // Jarvis visualizer: drive bars from live mic RMS
        let sum = 0;
        for (let i = 0; i < f32.length; i++) sum += f32[i] * f32[i];
        this._setMicLevel(Math.sqrt(sum / f32.length));

        // Downsample to 16 kHz and convert to Int16 PCM
        let i16;
        if (actualRate !== TARGET_RATE) {
          const ratio = actualRate / TARGET_RATE;
          const outLen = Math.floor(f32.length / ratio);
          i16 = new Int16Array(outLen);
          for (let i = 0; i < outLen; i++) {
            // Linear interpolation for better quality than nearest-neighbor
            const srcIdx = i * ratio;
            const lo = Math.floor(srcIdx), hi = Math.min(lo + 1, f32.length - 1);
            const frac = srcIdx - lo;
            const s = Math.max(-1, Math.min(1, f32[lo] * (1 - frac) + f32[hi] * frac));
            i16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
          }
        } else {
          i16 = new Int16Array(f32.length);
          for (let i = 0; i < f32.length; i++) {
            const s = Math.max(-1, Math.min(1, f32[i]));
            i16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
          }
        }

        // Send as base64-encoded raw PCM
        const bytes = new Uint8Array(i16.buffer);
        let bin = '';
        // Process in chunks to avoid stack overflow on large buffers
        for (let i = 0; i < bytes.length; i += 512) {
          bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 512));
        }
        this.ws.send(JSON.stringify({ user_audio_chunk: btoa(bin) }));
      };

      // Must connect processor to destination for onaudioprocess to fire.
      // Route through a muted gain node to avoid echo feedback.
      const mute = this.audioCtx.createGain();
      mute.gain.value = 0;
      srcNode.connect(processor);
      processor.connect(mute);
      mute.connect(this.audioCtx.destination);

      this._micSource = srcNode;
      this._micProcessor = processor;
      this._micMute = mute;
      this._micStream = stream;

      this._showOverlay('🎙️ Bixby te escucha — habla');
    } catch (e) {
      this._setStatus('Error al iniciar micrófono: ' + (e?.message || e), true);
    }
  },

  // Map RMS mic level (0..~0.3) to the Jarvis visualizer bars
  _setMicLevel(rms) {
    const now = performance.now();
    if (now - (this._lastVizUpdate || 0) < 50) return; // ~20fps
    this._lastVizUpdate = now;
    const bars = document.querySelectorAll('#bixby-viz .bvbar');
    if (!bars.length) return;
    const level = Math.min(1, rms * 8);
    if (level > 0.06 && typeof window !== 'undefined') {
      window.__bixbyEnergy = Math.max(window.__bixbyEnergy || 0, level * 0.8);
    }
    bars.forEach((b, i) => {
      const jitter = 0.35 + 0.65 * Math.abs(Math.sin(now / 110 + i * 0.7));
      b.style.height = (3 + level * 22 * jitter).toFixed(1) + 'px';
      b.style.animationPlayState = level > 0.05 ? 'paused' : 'running';
    });
  },

  _sendInitContext() {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    const ctx = this._buildContext();
    // ElevenLabs ConvAI init message — dynamic_variables must be strings
    const msg = {
      type: 'conversation_initiation_client_data',
      dynamic_variables: {
        selected_company: ctx.selected_company?.label || 'ninguna',
        active_tab: ctx.active_tab || 'mapa',
        total_nodes: String(ctx.total_nodes || 0),
        portfolio_count: String(ctx.portfolio_count || 0),
        stress_active: ctx.stress_active ? 'sí' : 'no',
        stressed_company: ctx.stressed_company || 'ninguna',
      },
    };
    // Prompt override only works if the ElevenLabs agent has "Allow overrides" on.
    // Sending it when overrides are OFF causes ElevenLabs to close the WebSocket.
    // Only attach it when the server explicitly provides a prompt AND override is
    // enabled (checked via the allow_override flag in the bixby-prompt response).
    if (this._systemPrompt && this._allowPromptOverride) {
      msg.conversation_config_override = {
        agent: {
          prompt: { prompt: this._systemPrompt },
          language: (typeof LANG !== 'undefined') ? LANG : 'es',
        },
      };
    }
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

  _handleMessage(msg) {
    switch (msg.type) {
      case 'conversation_initiation_metadata':
        // Session confirmed — mic was already started on ws.onopen
        this._showOverlay('🎙️ Bixby te escucha — habla');
        break;
      case 'audio': {
        const chunk = msg.audio_event?.audio_base_64;
        if (chunk) this._enqueueAudio(chunk);
        break;
      }
      case 'agent_response': {
        const text = msg.agent_response_event?.agent_response || '';
        if (text) {
          this._showOverlay('Bixby: ' + text.slice(0, 80));
          this._onAgentResponse(text);
        }
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
    if (typeof window !== 'undefined') window.__bixbyEnergy = 1;
    if (!this.isPlaying) this._playNext();
  },

  async _playNext() {
    if (!this.audioQueue.length) { this.isPlaying = false; return; }
    this.isPlaying = true;
    const chunk = this.audioQueue.shift();
    try {
      if (this.audioCtx?.state === 'suspended') await this.audioCtx.resume();
      const bytes = Uint8Array.from(atob(chunk), c => c.charCodeAt(0));
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
    const nav    = text.match(/\[NAV:([A-Za-z0-9_]+)\]/);
    const stress = text.match(/\[STRESS:([A-Za-z0-9_]+)\]/);
    const sim    = text.match(/\[SIM:([a-z_]+)\]/);
    if (nav    && typeof jumpTo === 'function') jumpTo(nav[1]);
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
            price: q?.close || null,
            change_pct: (q?.close && q?.prev) ? ((q.close - q.prev) / q.prev * 100).toFixed(2) : null,
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
            respond({ success: true, company: n.label, nrs,
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
