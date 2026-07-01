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
    this._preStream = preStream;
    this.ws = new WebSocket(signedUrl);

    this.ws.onopen = () => {
      this.isConnected = true;
      this._showOverlay('Bixby — iniciando sesión…');
      this._sendInitContext();
      // Mic starts on conversation_initiation_metadata (not here)
      // ElevenLabs requires that exchange before audio can be sent
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
      this._stopScheduled();
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
    if (this._preStream) {
      try { this._preStream.getTracks().forEach(t => t.stop()); } catch {}
      this._preStream = null;
    }
    this._stopScheduled();
    if (this.ws) {
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
    // Minimal init — dynamic_variables require agent config in ElevenLabs dashboard
    // and cause a close if the placeholders don't exist in the agent's system prompt
    const msg = { type: 'conversation_initiation_client_data' };
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
    const positions = Object.entries((typeof MKT !== 'undefined' && MKT.pos) || {});
    const hasStress = typeof stressId !== 'undefined' && !!stressId;

    let topRisk = [];
    if (typeof computeNRS === 'function' && typeof NODES !== 'undefined') {
      try {
        topRisk = NODES.map(n => ({ id: n.id, label: n.label, ticker: n.mkt || null, nrs: computeNRS(n.id) }))
          .sort((a, b) => b.nrs - a.nrs).slice(0, 10);
      } catch {}
    }

    let selLinks = [];
    if (sel && typeof LINKS !== 'undefined') {
      try {
        selLinks = LINKS.filter(l => lid(l.source) === sel.id || lid(l.target) === sel.id)
          .slice(0, 8).map(l => ({
            from: NODE_BY_ID[lid(l.source)]?.label,
            to: NODE_BY_ID[lid(l.target)]?.label,
            type: l.type || l.rel,
          }));
      } catch {}
    }

    const portfolio = positions.map(([id, p]) => {
      const n = NODE_BY_ID[id];
      const q = n?.mkt ? ((typeof MKT !== 'undefined') ? MKT.quotes[n.mkt] : null) : null;
      return {
        id, label: n?.label || id, ticker: n?.mkt || null,
        shares: p.sh, buy_price: p.bp,
        current_price: q?.close || null,
        nrs: typeof computeNRS === 'function' ? computeNRS(id) : null,
      };
    });

    // Category breakdown
    const cats = {};
    if (typeof NODES !== 'undefined') NODES.forEach(n => { cats[n.cat] = (cats[n.cat] || 0) + 1; });

    return {
      app: 'Khipu Finance', assistant: 'Bixby',
      active_tab: (typeof activeTab !== 'undefined') ? activeTab : null,
      language: (typeof LANG !== 'undefined') ? LANG : 'es',
      total_nodes: (typeof NODES !== 'undefined') ? NODES.length : 0,
      total_links: (typeof LINKS !== 'undefined') ? LINKS.length : 0,
      categories: cats,
      selected_company: sel ? {
        id: sel.id, label: sel.label, ticker: sel.mkt || null,
        category: typeof catLabel === 'function' ? catLabel(sel.cat) : sel.cat,
        nrs: typeof computeNRS === 'function' ? computeNRS(sel.id) : null,
        price: sel.mkt ? ((typeof MKT !== 'undefined') ? MKT.quotes[sel.mkt]?.close || null : null) : null,
        role: sel.role || null,
        supply_chain_links: selLinks,
      } : null,
      portfolio,
      portfolio_count: positions.length,
      stress_active: hasStress,
      stressed_company: hasStress ? { id: stressId, label: NODE_BY_ID[stressId]?.label } : null,
      top_risk_companies: topRisk,
    };
  },

  _handleMessage(msg) {
    switch (msg.type) {
      case 'conversation_initiation_metadata':
        // Session confirmed — NOW safe to start sending audio
        this._showOverlay('🎙️ Bixby te escucha — habla');
        if (this._preStream) {
          this._startMicWithStream(this._preStream);
          this._preStream = null;
        }
        break;
      case 'audio': {
        const chunk = msg.audio_event?.audio_base_64;
        if (chunk) {
          if (window.setBixbyThinking) window.setBixbyThinking(false);
          this._enqueueAudio(chunk);
        }
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
        if (t) {
          this._showOverlay('Tú: ' + t.slice(0, 80));
          if (window.setBixbyThinking) window.setBixbyThinking(true);
        }
        break;
      }
      case 'client_tool_call':
        this._handleToolCall(msg.client_tool_call);
        break;
      case 'interruption':
        this._stopScheduled();
        break;
      case 'ping':
        if (msg.ping_event?.event_id != null && this.ws?.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({ type: 'pong', event_id: msg.ping_event.event_id }));
        }
        break;
    }
  },

  // Reproducción SIN CORTES: cada chunk se agenda contiguo al anterior usando un
  // cursor de tiempo del AudioContext (_playCursor). Así el audio suena seguido
  // aunque el hilo principal se trabe un instante (p.ej. al mostrar una empresa),
  // porque el buffer ya quedó agendado en el hilo de audio. No dependemos de
  // onended (que corre en el hilo principal y llega tarde bajo jank).
  _enqueueAudio(b64chunk) {
    if (typeof window !== 'undefined') window.__bixbyEnergy = 1;
    this._scheduleChunk(b64chunk);
  },

  _scheduleChunk(b64chunk) {
    const ctx = this.audioCtx;
    if (!ctx) return;
    if (ctx.state === 'suspended') { try { ctx.resume(); } catch {} }
    let buffer;
    try {
      const bytes = Uint8Array.from(atob(b64chunk), c => c.charCodeAt(0));
      const pcm = new Int16Array(bytes.buffer);
      const f32 = new Float32Array(pcm.length);
      for (let i = 0; i < pcm.length; i++) f32[i] = pcm[i] / 32768;
      buffer = ctx.createBuffer(1, f32.length, 16000);
      buffer.getChannelData(0).set(f32);
    } catch { return; }
    const src = ctx.createBufferSource();
    src.buffer = buffer;
    src.connect(ctx.destination);
    const now = ctx.currentTime;
    let start = this._playCursor || 0;
    if (start < now + 0.02) start = now + 0.02;  // colchón anti-glitch si nos atrasamos
    try { src.start(start); } catch { return; }
    this._playCursor = start + buffer.duration;
    this.isPlaying = true;
    (this._activeSources || (this._activeSources = [])).push(src);
    src.onended = () => {
      const i = this._activeSources.indexOf(src);
      if (i >= 0) this._activeSources.splice(i, 1);
      if (!this._activeSources.length) { this.isPlaying = false; this._playCursor = 0; }
    };
  },

  // Corta TODO el audio agendado (para interrupciones y desconexión).
  _stopScheduled() {
    (this._activeSources || []).forEach(s => { try { s.stop(); } catch {} });
    this._activeSources = [];
    this._playCursor = 0;
    this.isPlaying = false;
    this.audioQueue = [];
  },

  _onAgentResponse(text) {
    const nav      = text.match(/\[NAV:([A-Za-z0-9_]+)\]/);
    const stress   = text.match(/\[STRESS:([A-Za-z0-9_]+)\]/);
    const sim      = text.match(/\[SIM:([a-z_]+)\]/);
    const tab      = text.match(/\[TAB:([a-z]+)\]/);
    const chart    = text.match(/\[CHART:([A-Za-z0-9._^[\]]+)\]/);
    const trade    = text.match(/\[TRADE:([A-Za-z0-9._^[\]]+)\]/);
    const terminal = text.match(/\[TERMINAL:([A-Za-z0-9._^[\]]+)\]/);
    const sb       = text.match(/\[SECOND_BRAIN:([A-Za-z0-9_]+)\]/);
    const canvas   = text.match(/\[CANVAS:([^\]]+)\]/);
    const nrsTop   = /\[NRS_TOP\]/.test(text);
    const filter   = text.match(/\[FILTER:([A-Za-z0-9_]+)\]/);

    if (tab && typeof switchTab === 'function') this._defer(() => switchTab(tab[1]));
    if (nav && typeof jumpTo === 'function') this._defer(() => jumpTo(nav[1]));
    if (stress) {
      const n = NODES.find(n => n.mkt === stress[1] || n.id === stress[1]);
      if (n && typeof activateStress === 'function') this._defer(() => activateStress(n.id));
    }
    if (sim && window.nexusCore?.runPreset) window.nexusCore.runPreset(sim[1]);
    if (chart) {
      const n = NODES.find(n => n.mkt === chart[1] || n.id === chart[1]);
      if (n) {
        if (typeof jumpTo === 'function') jumpTo(n.id);
        if (n.mkt && typeof loadStockChart === 'function') setTimeout(() => loadStockChart(n.id, n.mkt), 350);
      }
    }
    if (trade) {
      const n = NODES.find(n => n.mkt === trade[1] || n.id === trade[1]);
      if (n?.mkt && typeof openTradeModal === 'function') setTimeout(() => openTradeModal(n.id, n.mkt, n.label), 400);
    }
    if (terminal) {
      if (window._termOpenTicker) window._termOpenTicker(terminal[1]);
    }
    if (sb) {
      const n = NODES.find(n => n.id === sb[1]);
      if (n && typeof window._openSecondBrain === 'function') setTimeout(() => window._openSecondBrain(n.id), 300);
    }
    if (canvas && typeof switchTab === 'function') {
      switchTab('canvas');
      setTimeout(() => {
        const qi = document.getElementById('canvas-query');
        if (qi) { qi.value = canvas[1].trim(); if (typeof window.canvasGenerate === 'function') window.canvasGenerate(); }
      }, 280);
    }
    if (nrsTop && typeof switchTab === 'function') switchTab('analysis');
    if (filter) {
      const catKey = filter[1].toLowerCase();
      const match = (typeof CATS !== 'undefined') ? Object.entries(CATS).find(([k]) => k === catKey || k.includes(catKey)) : null;
      if (match && typeof setFilter === 'function') setFilter(match[0]);
    }
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
          respond({ success: true, company: n.label, ticker: n.mkt });  // responde YA
          this._defer(() => {                                            // visual diferido
            if (typeof jumpTo === 'function') jumpTo(n.id);
            if (window.khipuGraph3D?.active) window.khipuGraph3D.selectNode(n.id);
            this._updateContextSoon();
          });
        } else respond({ success: false, error: 'Company not found' });
        break;
      }
      case 'run_stress_test': {
        const n = NODES.find(n => n.mkt === params.ticker || n.id === params.ticker);
        if (n && typeof activateStress === 'function') {
          // cascada pesada diferida; respondemos DENTRO del defer para leer el
          // conteo real ya calculado (no antes de que activateStress corra).
          this._defer(() => {
            try { activateStress(n.id); } catch {}
            const cascade = (typeof stressAffected !== 'undefined') ? stressAffected.size : 0;
            respond({ success: true, company: n.label, affected_count: cascade,
              affected_pct: Math.round(cascade / NODES.length * 100) });
          });
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
      case 'switch_tab': {
        const validTabs = ['map', 'market', 'analysis', 'geo', 'simulation', 'space', 'terminal', 'canvas'];
        const t = params.tab || '';
        if (validTabs.includes(t) && typeof switchTab === 'function') {
          this._defer(() => { try { switchTab(t); } catch {} });
          respond({ success: true, tab: t });
        } else respond({ success: false, error: `Tab inválida: ${t}` });
        break;
      }
      case 'show_chart': {
        const n = NODES.find(n => n.mkt === params.ticker || n.id === params.ticker
          || n.label.toLowerCase().includes((params.company_name || '').toLowerCase()));
        if (n?.mkt) {
          if (typeof jumpTo === 'function') jumpTo(n.id);
          if (typeof loadStockChart === 'function') setTimeout(() => loadStockChart(n.id, n.mkt), 350);
          respond({ success: true, company: n.label, ticker: n.mkt });
        } else respond({ success: false, error: 'Empresa o ticker no encontrado' });
        break;
      }
      case 'open_terminal': {
        const n = NODES.find(n => n.mkt === params.ticker || n.id === params.ticker
          || n.label.toLowerCase().includes((params.company_name || '').toLowerCase()));
        if (n?.mkt) {
          if (window._termOpenTicker) window._termOpenTicker(n.mkt);
          respond({ success: true, company: n.label, ticker: n.mkt, action: 'Terminal abierto' });
        } else respond({ success: false, error: 'Empresa no encontrada' });
        break;
      }
      case 'place_trade': {
        const n = NODES.find(n => n.mkt === params.ticker || n.id === params.ticker
          || n.label.toLowerCase().includes((params.company_name || '').toLowerCase()));
        if (n?.mkt && typeof openTradeModal === 'function') {
          setTimeout(() => openTradeModal(n.id, n.mkt, n.label), 300);
          respond({ success: true, company: n.label, ticker: n.mkt, note: 'Modal de trading abierto — el usuario debe confirmar la orden' });
        } else respond({ success: false, error: 'Empresa no encontrada o trading no disponible' });
        break;
      }
      case 'get_market_summary': {
        const quotes = Object.entries((typeof MKT !== 'undefined' ? MKT.quotes : {}) || {})
          .filter(([, q]) => q.close)
          .map(([t, q]) => ({
            ticker: t,
            price: q.close,
            change_pct: (q.close && q.prev) ? ((q.close - q.prev) / q.prev * 100).toFixed(2) : null,
          }));
        respond({ total_tickers: quotes.length, quotes });
        break;
      }
      case 'list_companies': {
        const catFilter = (params.category || '').toLowerCase();
        const filtered = NODES.filter(n =>
          !catFilter ||
          n.cat === params.category ||
          (typeof catLabel === 'function' && catLabel(n.cat).toLowerCase().includes(catFilter))
        ).slice(0, params.limit || 50);
        respond({
          count: filtered.length,
          companies: filtered.map(n => ({
            id: n.id, label: n.label, ticker: n.mkt || null,
            category: typeof catLabel === 'function' ? catLabel(n.cat) : n.cat,
          })),
        });
        break;
      }
      case 'get_supply_chain_links': {
        const n = NODES.find(n => n.id === params.company_id || n.mkt === params.ticker
          || n.label.toLowerCase().includes((params.company_name || '').toLowerCase()));
        if (n) {
          const allLinks = (typeof LINKS !== 'undefined' ? LINKS : [])
            .filter(l => lid(l.source) === n.id || lid(l.target) === n.id);
          const upstream   = allLinks.filter(l => lid(l.target) === n.id)
            .map(l => ({ company: NODE_BY_ID[lid(l.source)]?.label, type: l.type || l.rel }));
          const downstream = allLinks.filter(l => lid(l.source) === n.id)
            .map(l => ({ company: NODE_BY_ID[lid(l.target)]?.label, type: l.type || l.rel }));
          respond({
            company: n.label, ticker: n.mkt || null,
            upstream_count: upstream.length, downstream_count: downstream.length,
            upstream: upstream.slice(0, 15), downstream: downstream.slice(0, 15),
          });
        } else respond({ success: false, error: 'Empresa no encontrada' });
        break;
      }
      case 'get_nrs_top10': {
        if (typeof computeNRS !== 'function') { respond({ success: false, error: 'NRS no disponible' }); break; }
        const top = NODES.map(n => ({
          id: n.id, label: n.label, ticker: n.mkt || null, nrs: computeNRS(n.id),
        })).sort((a, b) => b.nrs - a.nrs).slice(0, 10);
        respond({ companies: top });
        break;
      }
      case 'open_second_brain': {
        const n = NODES.find(n => n.id === params.company_id || n.mkt === params.ticker
          || n.label.toLowerCase().includes((params.company_name || '').toLowerCase()));
        if (n) {
          if (typeof window._openSecondBrain === 'function') this._defer(() => window._openSecondBrain(n.id));
          respond({ success: true, company: n.label });
        } else respond({ success: false, error: 'Empresa no encontrada' });
        break;
      }
      case 'get_news': {
        const n = NODES.find(n => n.mkt === params.ticker || n.id === params.ticker
          || n.label.toLowerCase().includes((params.company_name || '').toLowerCase()));
        if (n?.mkt) {
          const base = (typeof BASE !== 'undefined') ? BASE : '';
          fetch(`${base}/api/news/${n.mkt}`)
            .then(r => r.json())
            .then(data => {
              const articles = Array.isArray(data) ? data.slice(0, 5) : [];
              respond({
                success: true, company: n.label, ticker: n.mkt,
                articles: articles.map(a => ({ headline: a.headline, source: a.source, sentiment: a.sentiment })),
              });
            })
            .catch(() => respond({ success: false, error: 'Error fetching news' }));
        } else respond({ success: false, error: 'Empresa o ticker no encontrado' });
        break;
      }
      default:
        respond({ success: false, error: `Unknown tool: ${tool_name}` });
    }
  },

  // Ejecuta una acción visual pesada FUERA del hilo crítico del WebSocket, para
  // no bloquear el procesamiento/agendado del audio mientras Bixby habla.
  _defer(fn) {
    if (typeof requestAnimationFrame === 'function') requestAnimationFrame(() => { try { fn(); } catch {} });
    else setTimeout(() => { try { fn(); } catch {} }, 0);
  },

  updateContext() {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    this.ws.send(JSON.stringify({
      type: 'contextual_update',
      text: `[CONTEXT_UPDATE] ${JSON.stringify(this._buildContext())}`,
    }));
  },

  // Versión con debounce: construir el contexto mapea ~460 nodos; si varios
  // tool-calls llegan seguidos, lo hacemos una sola vez y diferido.
  _updateContextSoon() {
    if (this._ctxTimer) clearTimeout(this._ctxTimer);
    this._ctxTimer = setTimeout(() => { this._ctxTimer = null; this.updateContext(); }, 400);
  },

  _showOverlay(text) {
    const el = document.getElementById('bixby-status');
    if (el) { el.style.display = 'block'; this._setStatus(text); }
    const btn = document.getElementById('bixby-btn');
    if (btn) btn.classList.add('bixby-active');
  },
  _hideOverlay() {
    const el = document.getElementById('bixby-status');
    if (el) el.style.display = 'none';
    const btn = document.getElementById('bixby-btn');
    if (btn) btn.classList.remove('bixby-active');
    this._setBadge('OFF', false);
  },
  _setBadge(label, active) {
    const b = document.getElementById('bixby-state-badge');
    if (!b) return;
    b.textContent = label;
    if (active) {
      b.style.background = 'rgba(0,204,255,.15)';
      b.style.color = '#00ccff';
      b.style.borderColor = 'rgba(0,204,255,.4)';
    } else {
      b.style.background = 'rgba(138,90,255,.2)';
      b.style.color = '#cabeff';
      b.style.borderColor = 'rgba(138,90,255,.3)';
    }
  },
  _setStatus(text, isError) {
    const t = document.getElementById('bixby-text');
    if (t) t.textContent = text;
    // update badge + thinking widget based on text content
    const badge = document.getElementById('bixby-state-badge');
    if (badge && text) {
      const lower = text.toLowerCase();
      if (lower.includes('escucha') || lower.includes('habla')) {
        this._setBadge('ESCUCHANDO', true);
        if (window.setBixbyThinking) window.setBixbyThinking(false);
      } else if (lower.includes('conectando') || lower.includes('iniciando') || lower.includes('sesión')) {
        this._setBadge('CONECTANDO', false);
        if (window.setBixbyThinking) window.setBixbyThinking(false);
      } else if (lower.includes('bixby:') || lower.includes('speaking')) {
        this._setBadge('HABLANDO', true);
        if (window.setBixbyThinking) window.setBixbyThinking(false);
      } else if (lower.includes('procesando') || lower.includes('pensando') || lower.includes('tú:')) {
        this._setBadge('PENSANDO', true);
        if (window.setBixbyThinking) window.setBixbyThinking(true);
      } else if (isError) {
        this._setBadge('ERROR', false);
        if (window.setBixbyThinking) window.setBixbyThinking(false);
      }
    }
    if (isError) {
      const el = document.getElementById('bixby-status');
      if (el) el.style.display = 'block';
      if (typeof toast === 'function') toast(text);
    }
  },
};

window.BixbyVoice = BixbyVoice;
