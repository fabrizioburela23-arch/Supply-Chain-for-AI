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
    // La key de ElevenLabs vive en el server (.env); agent_id opcional es solo
    // una preferencia local que el server puede aceptar como override.
    const agentId = localStorage.getItem('elevenlabs_agent_id');

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
      this._orbOff();   // apaga el orbe de voz (vuelve a respirar / se destruye si era flotante)
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
    this._orbOff();
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
    const level = Math.min(1, rms * 8);
    // Orbe de voz de Bixby (engine/orb.js): energía del USUARIO (cian/teal).
    // Se alimenta SIEMPRE, aunque no exista el visualizador de barras.
    if (window.BixbyOrb) { try { window.BixbyOrb.setUserLevel(level); } catch (e) {} }
    const bars = document.querySelectorAll('#bixby-viz .bvbar');
    if (!bars.length) return;
    if (level > 0.06 && typeof window !== 'undefined') {
      window.__bixbyEnergy = Math.max(window.__bixbyEnergy || 0, level * 0.8);
    }
    bars.forEach((b, i) => {
      const jitter = 0.35 + 0.65 * Math.abs(Math.sin(now / 110 + i * 0.7));
      b.style.height = (3 + level * 22 * jitter).toFixed(1) + 'px';
      b.style.animationPlayState = level > 0.05 ? 'paused' : 'running';
    });
  },

  // ── Orbe de voz de Bixby (engine/orb.js) ───────────────────────────────────
  // La Cabina monta el orbe en su header y lo hace respirar; aquí solo lo
  // ALIMENTAMOS: setUserLevel desde el micrófono (_setMicLevel) y setBixbyLevel
  // mientras Bixby reproduce audio (_startOrbDrive). En reposo, el orbe respira.
  _orbOn() {
    const orb = (typeof window !== 'undefined') ? window.BixbyOrb : null;
    if (orb) {
      try {
        // Si la voz se activó FUERA de la Cabina, montamos un orbe flotante
        // propio (lo destruimos al terminar). Si la Cabina ya lo montó, no dupl.
        if (!orb.isMounted || !orb.isMounted()) { orb.mount(); this._orbFloating = true; }
        orb.start();
      } catch (e) {}
    }
    this._startOrbDrive();
  },
  _orbOff() {
    this._stopOrbDrive();
    const orb = (typeof window !== 'undefined') ? window.BixbyOrb : null;
    if (orb) {
      try { orb.setUserLevel(0); orb.setBixbyLevel(0); } catch (e) {}
      if (this._orbFloating) { try { orb.destroy(); } catch (e) {} this._orbFloating = false; }
    }
    this._speakLevel = 0;
  },
  _startOrbDrive() {
    if (this._orbRAF) return;
    const tick = () => {
      if (!this.isConnected) { this._orbRAF = 0; return; }
      const orb = (typeof window !== 'undefined') ? window.BixbyOrb : null;
      if (orb) {
        const ctx = this.audioCtx;
        // "hablando" = todavía hay audio agendado por delante del cursor de reproducción
        const speaking = !!(ctx && this._playCursor && ctx.currentTime < this._playCursor - 0.02);
        if (speaking) {
          const base = this._speakLevel || 0.5;
          const osc = 0.72 + 0.28 * Math.abs(Math.sin(performance.now() / 90));
          try { orb.setBixbyLevel(Math.min(1, base * osc)); } catch (e) {}
        }
      }
      this._orbRAF = requestAnimationFrame(tick);
    };
    this._orbRAF = requestAnimationFrame(tick);
  },
  _stopOrbDrive() {
    if (this._orbRAF) { cancelAnimationFrame(this._orbRAF); this._orbRAF = 0; }
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
      selected_company: sel ? (function () {
        const m = (window.NODE_META || {})[sel.id] || {};
        return {
          id: sel.id, label: sel.label, ticker: sel.mkt || null,
          category: typeof catLabel === 'function' ? catLabel(sel.cat) : sel.cat,
          nrs: typeof computeNRS === 'function' ? computeNRS(sel.id) : null,
          price: sel.mkt ? ((typeof MKT !== 'undefined') ? MKT.quotes[sel.mkt]?.close || null : null) : null,
          role: sel.role || null,
          // la ficha completa: Bixby debe saber lo que la pantalla muestra
          employees: m.employees || null, founded: m.founded || null,
          revenue: m.revenue_2025 || null, market_cap_billions: m.mktcap_b || null,
          geo_risk: m.geo_risk || null, country: sel.country || null,
          margin_pct: sel.margin != null ? Math.round(sel.margin * 100) : null,
          growth: sel.growth || null,
          supply_chain_links: selLinks,
        };
      })() : null,
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
        this._orbOn();   // arranca/alimenta el orbe de voz de la Cabina
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
          // El usuario NUNCA debe ver los tokens internos ([XRAY:...], [NAV:...])
          const clean = this._cleanSpeech(text);
          if (clean) this._showOverlay('Bixby: ' + clean.slice(0, 80));
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
      let _sum = 0;
      for (let i = 0; i < pcm.length; i++) { const v = pcm[i] / 32768; f32[i] = v; _sum += v * v; }
      // energía de la voz de BIXBY (violeta) para el orbe — la lee _startOrbDrive
      this._speakLevel = Math.max(0.35, Math.min(1, Math.sqrt(_sum / (f32.length || 1)) * 5));
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
    const xray     = text.match(/\[XRAY:([A-Za-z0-9_]+)\]/);
    const compare  = text.match(/\[COMPARE:([A-Za-z0-9_]+),([A-Za-z0-9_]+)\]/);
    const shock    = text.match(/\[SHOCK:([A-Za-z0-9_]+)(?::([a-z]+))?\]/);
    const opps     = /\[OPPS\]/.test(text);
    const insights = /\[INSIGHTS\]/.test(text);

    if (tab) this._defer(() => this._show('tab', tab[1]));
    if (nav) {
      const n = this._resolveNode(nav[1]);
      if (n) this._defer(() => this._show('graph', n.id));
    }
    if (stress) {
      const n = this._resolveNode(stress[1]);
      if (n) this._defer(() => this._show('stress', n.id));
    }
    if (sim && window.nexusCore?.runPreset) window.nexusCore.runPreset(sim[1]);
    if (chart) {
      const n = this._resolveNode(chart[1]);
      if (n) this._defer(() => this._show('chart', { id: n.id, ticker: n.mkt }));
    }
    if (trade) {
      const n = this._resolveNode(trade[1]);
      if (n?.mkt) this._defer(() => this._show('trade', { id: n.id, ticker: n.mkt, label: n.label }));
    }
    if (terminal) {
      this._defer(() => this._show('terminal', { ticker: terminal[1] }));
    }
    if (sb) {
      const n = this._resolveNode(sb[1]);
      if (n) this._defer(() => this._show('secondbrain', n.id));
    }
    if (canvas) {
      this._defer(() => this._show('canvas', canvas[1].trim()));
    }
    if (nrsTop) this._defer(() => this._show('insights'));
    if (filter) {
      const catKey = filter[1].toLowerCase();
      const match = (typeof CATS !== 'undefined') ? Object.entries(CATS).find(([k]) => k === catKey || k.includes(catKey)) : null;
      if (match && typeof setFilter === 'function') setFilter(match[0]);
    }
    // ── Tokens nuevos (X-Ray, comparar, shock/sim en vivo, oportunidades, insights) ──
    if (xray) {
      const n = this._resolveNode(xray[1]);
      if (n) this._defer(() => this._show('xray', n.id));
    }
    if (compare) {
      const a = this._resolveNode(compare[1]);
      const b = this._resolveNode(compare[2]);
      if (a && b) this._defer(() => this._show('compare', { a: a.id, b: b.id }));
    }
    if (shock && window.KhipuState) {
      const n = this._resolveNode(shock[1]);
      if (n) {
        const kind = ['collapse', 'demand', 'price', 'sanction'].includes(shock[2]) ? shock[2] : 'collapse';
        const dir = kind === 'demand' ? 'up' : 'down';
        this._defer(() => {
          try {
            const r = window.KhipuState.simulate({ [n.id]: { salud: 0 } }, [], 8, 0.6, false, { direction: dir, kind });
            this._show('sim', { id: n.id, kind, after: () => {
              if (window._liveRecolorByImpact) window._liveRecolorByImpact(r.impact, dir);
            } });
          } catch (_) {}
        });
      }
    }
    if (opps || insights) {
      this._defer(() => this._show('insights'));
    }
  },

  // Quita los tokens de comando internos del texto hablado/mostrado.
  // Bixby los emite para actuar, pero el usuario jamás debe verlos ni oírlos.
  _cleanSpeech(text) {
    return String(text || '')
      .replace(/\[[A-Z_]+:[^\]]*\]/g, '')   // [NAV:x] [XRAY:x] [SHOCK:x:y] [CANVAS:...]
      .replace(/\[[A-Z_]+\]/g, '')          // [NRS_TOP] [OPPS] [INSIGHTS]
      .replace(/\s{2,}/g, ' ').trim();
  },

  // Resuelve una empresa desde lo que diga el agente (id, ticker o nombre).
  // Usa el resolutor robusto compartido (engine/resolve.js): sin acentos,
  // alias de transcripción de voz ("en vidia" → Nvidia), typos (Levenshtein).
  // La búsqueda débil de antes queda solo de fallback si resolve.js no cargó.
  _resolveNode(q) {
    if (q == null || typeof NODES === 'undefined') return null;
    const s = String(q).trim();
    if (!s) return null;
    if (window.KhipuResolve) {
      const r = window.KhipuResolve.find(s);
      if (r && r.node) return r.node;
    }
    const lc = s.toLowerCase();
    return NODES.find(n => n.id === s || n.mkt === s)                        // exacto (rápido)
      || NODES.find(n => (n.id || '').toLowerCase() === lc || (n.mkt || '').toLowerCase() === lc)  // id/ticker sin casing
      || NODES.find(n => (n.label || '').toLowerCase() === lc)              // nombre exacto
      || NODES.find(n => (n.label || '').toLowerCase().includes(lc))        // nombre contiene
      || null;
  },

  // Prueba ticker → nombre → id (los tools de ElevenLabs mandan cualquiera).
  _resolveAny(params) {
    params = params || {};
    return this._resolveNode(params.ticker) || this._resolveNode(params.company_name)
      || this._resolveNode(params.company_id) || null;
  },

  // Respuesta bilingüe de "no encontrado" CON sugerencias, para que Bixby
  // las DIGA en voz alta ("¿Quisiste decir NVIDIA, AMD o Micron?") en vez
  // del seco "Company not found" (feedback real del usuario).
  _notFound(q) {
    if (window.KhipuResolve) {
      const nf = window.KhipuResolve.notFound(q == null ? '' : q);
      return { success: false, error: nf.spoken, did_you_mean: nf.suggestions.map(s => s.label) };
    }
    return { success: false, error: 'Company not found' };
  },

  // Muestra un resultado AL FRENTE, siempre: dentro de la Cabina si está
  // abierta, o cambiando a la pestaña dueña y cerrando overlays que tapen.
  // Un solo camino compartido (window._surface, engine/resolve.js).
  _show(kind, arg) {
    if (window._surface) return window._surface(kind, arg);
    // fallback mínimo si resolve.js no cargó (comportamiento anterior)
    try {
      if (kind === 'xray' && window.openXRay) window.openXRay(arg);
      else if (kind === 'compare' && window.openCompare && arg) window.openCompare(arg.a, arg.b);
      else if (kind === 'graph' && typeof jumpTo === 'function') jumpTo(arg);
      else if (kind === 'insights' && typeof switchTab === 'function') switchTab('analysis');
      else if (kind === 'tab' && typeof switchTab === 'function') switchTab(arg);
      else if (kind === 'terminal' && window._termOpenTicker && arg) window._termOpenTicker(arg.ticker || arg);
      else if (kind === 'dossier' && window.openFinCard) window.openFinCard(arg);
      else if (kind === 'secondbrain' && window._openSecondBrain) window._openSecondBrain(arg);
      else if (kind === 'stress' && typeof activateStress === 'function') activateStress(arg);
      else return false;
      return true;
    } catch (e) { return false; }
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
        const n = this._resolveAny(params);
        if (n) {
          respond({ success: true, company: n.label, ticker: n.mkt });  // responde YA
          this._defer(() => {                                            // visual diferido
            this._show('graph', n.id);   // Cabina o mapa, siempre AL FRENTE
            if (window.khipuGraph3D?.active) window.khipuGraph3D.selectNode(n.id);
            this._updateContextSoon();
          });
        } else respond(this._notFound(params.ticker || params.company_name));
        break;
      }
      case 'run_stress_test': {
        const n = this._resolveAny(params);
        if (n && typeof activateStress === 'function') {
          // cascada pesada diferida; respondemos DENTRO del defer para leer el
          // conteo real ya calculado (no antes de que activateStress corra).
          this._defer(() => {
            try { this._show('stress', n.id); } catch {}
            // _surface difiere activateStress (~200-320ms); leemos el conteo
            // real después de que la cascada ya corrió.
            setTimeout(() => {
              const cascade = (typeof stressAffected !== 'undefined') ? stressAffected.size : 0;
              respond({ success: true, company: n.label, affected_count: cascade,
                affected_pct: Math.round(cascade / NODES.length * 100) });
            }, 600);
          });
        } else respond(this._notFound(params.ticker || params.company_name));
        break;
      }
      case 'run_simulation': {
        const preset = window.ScenarioBuilder?.PRESETS?.[params.scenario_id];
        if (preset && window.nexusCore) {
          respond({ success: true, message: 'Simulation starting...', scenario: preset.title });
          // El preset se pinta en la pestaña Simulación; si la Cabina la tapa,
          // la cerramos para que el resultado quede VISIBLE (muestra-en-pantalla).
          this._defer(() => {
            try { if (window.BixbyCockpit?.isOpen && window.BixbyCockpit.isOpen()) window.BixbyCockpit.close(); } catch (e) {}
          });
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
      case 'get_company_info': {
        // TODO lo que la app sabe de la empresa — Bixby nunca debe decir
        // "no sé" si el dato está en la ficha (feedback real: empleados de TSMC)
        const n = this._resolveAny(params);
        if (n) {
          const q = (typeof MKT !== 'undefined' && n.mkt) ? MKT.quotes[n.mkt] : null;
          const meta = (window.NODE_META || {})[n.id] || {};
          let inDeg = 0, outDeg = 0;
          try {
            (window.LINKS || []).forEach(l => {
              const s = lid(l.source), t = lid(l.target);
              if (t === n.id) inDeg++;
              if (s === n.id) outDeg++;
            });
          } catch (e) {}
          respond({
            id: n.id, label: n.label, ticker: n.mkt || null,
            category: (typeof catLabel === 'function') ? catLabel(n.cat) : n.cat,
            country: n.country || n.loc || null,
            price: q?.close || null,
            change_pct: (q?.close && q?.prev) ? ((q.close - q.prev) / q.prev * 100).toFixed(2) : null,
            nrs_risk: (typeof computeNRS === 'function') ? computeNRS(n.id) : null,
            role: n.role || null,
            supplies: n.supplies || null,
            moat: n.moat || null,
            growth: n.growth || null,
            margin_pct: n.margin != null ? Math.round(n.margin * 100) : null,
            employees: meta.employees || null,
            founded: meta.founded || null,
            revenue: meta.revenue_2025 || null,
            market_cap_billions: meta.mktcap_b || null,
            geo_risk: meta.geo_risk || null,
            description: meta.desc || null,
            suppliers_count: inDeg, customers_count: outDeg,
            is_preipo: !!n.preipo,
          });
        } else respond(this._notFound(params.ticker || params.company_name));
        break;
      }
      case 'get_risk_score': {
        const n = this._resolveAny(params);
        if (n && typeof computeNRS === 'function') {
          try {
            const nrs = computeNRS(n.id);
            respond({ success: true, company: n.label, nrs,
              level: nrs >= 70 ? 'high' : nrs >= 40 ? 'medium' : 'low' });
          } catch(e) { respond({ success: false, error: e.message }); }
        } else respond(this._notFound(params.ticker || params.company_name));
        break;
      }
      case 'switch_tab': {
        const validTabs = ['map', 'market', 'analysis', 'geo', 'simulation', 'space', 'terminal', 'canvas', 'tkg', 'guia'];
        const t = params.tab || '';
        if (!validTabs.includes(t)) { respond({ success: false, error: `Tab inválida: ${t}` }); break; }
        respond({ success: true, tab: t });
        // _surface enruta: Cabina abierta → escenario propio; cerrada →
        // switchTab con overlays cerrados (antes quedaba tapado y "no hacía nada").
        this._defer(() => this._show('tab', t));
        break;
      }
      case 'show_chart': {
        const n = this._resolveAny(params);
        if (n?.mkt) {
          respond({ success: true, company: n.label, ticker: n.mkt });
          this._defer(() => this._show('chart', { id: n.id, ticker: n.mkt }));
        } else respond(this._notFound(params.ticker || params.company_name));
        break;
      }
      case 'open_terminal': {
        const n = this._resolveAny(params);
        if (n?.mkt) {
          respond({ success: true, company: n.label, ticker: n.mkt, action: 'Terminal abierta en pantalla' });
          this._defer(() => this._show('terminal', { ticker: n.mkt }));
        } else respond(this._notFound(params.ticker || params.company_name));
        break;
      }
      case 'place_trade': {
        const n = this._resolveAny(params);
        if (n?.mkt && typeof openTradeModal === 'function') {
          this._defer(() => this._show('trade', { id: n.id, ticker: n.mkt, label: n.label }));
          respond({ success: true, company: n.label, ticker: n.mkt, note: 'Modal de trading abierto — el usuario debe confirmar la orden' });
        } else respond(this._notFound(params.ticker || params.company_name));
        break;
      }
      // ── Trading Bixby (Etapa M): orden por voz con confirmación explícita ──
      case 'place_paper_trade': {
        // NUNCA envía sin confirmed=true — ver _toolPlacePaperTrade
        this._toolPlacePaperTrade(params)
          .then(respond)
          .catch(e => respond({ success: false, error: 'trade tool error: ' + ((e && e.message) || e) }));
        break;
      }
      case 'get_portfolio_status': {
        this._toolPortfolioStatus(params)
          .then(respond)
          .catch(e => respond({ success: false, error: 'portfolio tool error: ' + ((e && e.message) || e) }));
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
        const n = this._resolveAny(params);
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
        } else respond(this._notFound(params.ticker || params.company_name || params.company_id));
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
        const n = this._resolveAny(params);
        if (n) {
          this._defer(() => this._show('secondbrain', n.id));
          respond({ success: true, company: n.label });
        } else respond(this._notFound(params.ticker || params.company_name || params.company_id));
        break;
      }
      case 'get_news': {
        const n = this._resolveAny(params);
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
        } else respond(this._notFound(params.ticker || params.company_name));
        break;
      }
      // ── Herramientas nuevas (2026-07): X-Ray, sim en vivo, comparar, insights ──
      case 'open_xray': {
        const n = this._resolveAny(params);
        if (n && (window.openXRay || window.BixbyCockpit)) {
          respond({ success: true, company: n.label });
          this._defer(() => this._show('xray', n.id));
        } else respond(this._notFound(params.ticker || params.company_name));
        break;
      }
      case 'run_live_simulation': {
        // params: {ticker/company_name, kind?: collapse|demand|price|sanction, severity?}
        const n = this._resolveAny(params);
        if (n && window.KhipuState) {
          const kind = ['collapse', 'demand', 'price', 'sanction'].includes(params.kind) ? params.kind : 'collapse';
          const dir = kind === 'demand' ? 'up' : 'down';
          const sev = Math.max(0, Math.min(100, +params.severity || 100));
          try {
            const r = window.KhipuState.simulate({ [n.id]: { salud: 1 - sev / 100 } }, [], 8, 0.6, false, { direction: dir, kind });
            let affected = 0, top = [];
            r.impact.forEach((v, id) => { if (id !== n.id) { affected++; top.push({ id, v }); } });
            top.sort((a, b) => b.v - a.v);
            respond({ success: true, company: n.label, kind, direction: dir, affected,
              most_impacted: top.slice(0, 5).map(x => ({ company: (NODE_BY_ID[x.id] || {}).label || x.id, impact_pct: Math.round(x.v) })) });
            this._defer(() => this._show('sim', { id: n.id, kind, after: () => {
              if (window._liveRecolorByImpact) window._liveRecolorByImpact(r.impact, dir);
            } }));
          } catch (e) { respond({ success: false, error: 'sim failed' }); }
        } else respond(this._notFound(params.ticker || params.company_name));
        break;
      }
      case 'compare_companies': {
        const a = this._resolveNode(params.a || params.company_a), b = this._resolveNode(params.b || params.company_b);
        if (a && b && (window.openCompare || window.BixbyCockpit)) {
          const nrsA = computeNRS ? computeNRS(a.id) : 50, nrsB = computeNRS ? computeNRS(b.id) : 50;
          respond({ success: true, a: a.label, b: b.label, nrs_a: nrsA, nrs_b: nrsB,
            lower_risk: nrsA < nrsB ? a.label : b.label });
          this._defer(() => this._show('compare', { a: a.id, b: b.id }));
        } else respond(this._notFound(!a ? (params.a || params.company_a) : (params.b || params.company_b)));
        break;
      }
      case 'get_opportunities': {
        // empresas resilientes con potencial (mismo criterio que los insights)
        const opps = NODES.map(n => {
          const nrs = computeNRS ? computeNRS(n.id) : 50;
          const g = (n.growth || '').toLowerCase();
          const growth = g.indexOf('🟢') >= 0 ? 2 : g.indexOf('🟡') >= 0 ? 1 : 0;
          const margin = n.margin != null ? n.margin : 0;
          return { label: n.label, nrs, margin: Math.round(margin * 100), score: growth * 22 + Math.min(30, margin * 60) + (50 - nrs) * 0.5, growth, marginRaw: margin };
        }).filter(x => x.nrs < 55 && x.growth >= 1 && x.marginRaw > 0.15).sort((a, b) => b.score - a.score).slice(0, 6);
        respond({ success: true, count: opps.length, opportunities: opps.map(o => ({ company: o.label, nrs: o.nrs, margin_pct: o.margin })) });
        this._defer(() => this._show('insights'));
        break;
      }
      case 'show_insights': case 'show_matrices': {
        respond({ success: true });
        this._defer(() => this._show('insights'));
        break;
      }
      case 'create_visualization': {
        // dibuja un gráfico/tabla por IA (Canvas) con lo que pida el usuario
        const q = (params.query || params.description || '').trim();
        if (!q) { respond({ success: false, error: 'query required' }); break; }
        respond({ success: true, rendering: q });
        this._defer(() => this._show('canvas', q));
        break;
      }
      case 'open_cockpit': {
        respond({ success: true });
        this._defer(() => { if (window.BixbyCockpit) window.BixbyCockpit.open(); });
        break;
      }
      case 'open_dossier': {
        // dossier financiero estilo investingvisuals (ingresos/dilución/FCF/ROE…)
        // _show('dossier') lo sube POR ENCIMA de la Cabina si está abierta
        // (z 6500 vs 7000 — antes quedaba atrás y "no se veía").
        const n = this._resolveAny(params);
        if (n && n.mkt) {
          respond({ success: true, company: n.label, ticker: n.mkt });
          this._defer(() => this._show('dossier', n.mkt));
        } else respond(this._notFound(params.ticker || params.company_name));
        break;
      }
      case 'deep_analysis': {
        // Capa 4: investigación profunda multi-paso — el resultado se pinta
        // en el escenario de la Cabina (tarda 30-90s; Bixby avisa y espera)
        const q = (params.question || '').trim();
        if (!q) { respond({ success: false, error: 'question required' }); break; }
        respond({ success: true, started: true, eta_seconds: 60 });
        this._defer(() => this._show('deep', q));
        break;
      }
      // ── Simulación POR AGENTES (MiroFish desde la terminal de Bixby) ──
      // Corre en el servidor (varios agentes debaten) y se MUESTRA en la Cabina.
      // Bixby narra el consenso y los mayores impactos.
      case 'run_agent_simulation': {
        const scenario = String(params.scenario || params.query || '').trim();
        if (!scenario) { respond({ success: false, error: 'scenario required' }); break; }
        const seedNames = Array.isArray(params.companies) ? params.companies
          : (Array.isArray(params.seeds) ? params.seeds : []);
        const seedIds = [];
        seedNames.forEach(c => { const nn = this._resolveNode(c); if (nn && seedIds.indexOf(nn.id) < 0) seedIds.push(nn.id); });
        const lang = (typeof LANG !== 'undefined') ? LANG : (localStorage.getItem('eco_lang') || 'es');
        if (!window._runAgentSim) { respond({ success: false, error: 'agent simulation not available' }); break; }
        window._runAgentSim(scenario, seedIds, lang)
          .then(d => {
            if (!d || d.ok === false) { respond({ success: false, error: (d && d.error) || 'simulation failed' }); return; }
            const impacts = Array.isArray(d.impacts) ? d.impacts.slice(0, 5).map(x => ({
              company: x.label || x.id, pct: x.pct, why: x.rationale })) : [];
            const agents = Array.isArray(d.agents) ? d.agents.map(a => a && a.name).filter(Boolean) : [];
            respond({ success: true, on_screen: true,
              narrative: String(d.narrative || '').slice(0, 700),
              top_impacts: impacts, agents });
          })
          .catch(e => respond({ success: false, error: 'agent sim error: ' + ((e && e.message) || e) }));
        break;
      }
      // ── Investigación profunda (más allá del nodo): sector, competidores,
      // geopolítica, chokepoints y tesis. Se MUESTRA en la Cabina. ──
      case 'deep_research': {
        const n = this._resolveAny(params);
        if (!n) { respond(this._notFound(params.company || params.company_name || params.ticker)); break; }
        const lang = (typeof LANG !== 'undefined') ? LANG : (localStorage.getItem('eco_lang') || 'es');
        if (!window._openDeepResearch) { respond({ success: false, error: 'deep research not available' }); break; }
        window._openDeepResearch(n.id, lang)
          .then(d => {
            if (!d || d.ok === false) { respond({ success: false, error: (d && d.error) || 'research failed' }); return; }
            respond({ success: true, on_screen: true, company: n.label,
              thesis: String(d.thesis || '').slice(0, 500),
              sector: String(d.sector || '').slice(0, 300),
              competitors: Array.isArray(d.competitors) ? d.competitors.slice(0, 6) : [],
              chokepoints: Array.isArray(d.chokepoints) ? d.chokepoints.slice(0, 5) : [] });
          })
          .catch(e => respond({ success: false, error: 'research error: ' + ((e && e.message) || e) }));
        break;
      }
      default:
        respond({ success: false, error: `Unknown tool: ${tool_name}` });
    }
  },

  // ── Trading Bixby (Etapa M) ────────────────────────────────────────────────
  // place_paper_trade: resuelve el activo (cripto primero, luego equity vía
  // KhipuResolve) y SOLO envía la orden cuando confirmed===true. Sin confirmar
  // devuelve needs_confirmation con un resumen hablable (ES/EN) para que Bixby
  // lo LEA en voz alta y pida el sí explícito del usuario. Regla innegociable:
  // ninguna orden sale sin confirmación.
  async _toolPlacePaperTrade(params) {
    params = params || {};
    const en = (((typeof LANG !== 'undefined') ? LANG : (localStorage.getItem('eco_lang') || 'es')) === 'en');
    if (!window._resolveTradeSymbol || !window._executeTradeOrder || !window._tradeFetch) {
      return { success: false, error: en ? 'Trading module not loaded.' : 'El módulo de trading no está cargado.' };
    }
    const q = String(params.symbol_or_name || params.symbol || params.asset || params.company_name || '').trim();
    if (!q) {
      return { success: false, error: en
        ? 'Which asset? For example: "buy $100 of Bitcoin".'
        : 'No entendí el activo. Dime, por ejemplo: "compra 100 dólares de Bitcoin".' };
    }
    const res = await window._resolveTradeSymbol(q);
    if (!res.ok) return { success: false, error: res.error, did_you_mean: res.suggestions || [] };

    const side = /^(sell|vend|venta)/i.test(String(params.side || '')) ? 'sell' : 'buy';
    let notional = (params.amount_usd != null && params.amount_usd !== '') ? Number(params.amount_usd)
      : (params.notional_usd != null && params.notional_usd !== '') ? Number(params.notional_usd)
      : (params.notional != null && params.notional !== '') ? Number(params.notional) : null;
    if (notional != null && !isFinite(notional)) notional = null;
    let qty = (params.qty != null && params.qty !== '') ? Number(params.qty) : null;
    if (qty != null && (!isFinite(qty) || qty <= 0)) qty = null;
    if (notional == null && qty == null) {
      return { success: false, needs_amount: true, error: en
        ? `How much? For example "$100 of ${res.label}".`
        : `¿Por cuánto? Por ejemplo "100 dólares de ${res.label}".` };
    }
    if (notional != null && !(notional >= 1 && notional <= 100000)) {
      return { success: false, error: en
        ? 'The amount must be between $1 and $100,000 per order.'
        : 'El monto debe estar entre $1 y $100,000 por orden.' };
    }

    const amountTxt = notional != null
      ? '$' + notional.toLocaleString('en-US', { maximumFractionDigits: 2 })
      : qty + (en ? ' units' : ' unidades');
    const verb = side === 'buy' ? (en ? 'buy' : 'comprar') : (en ? 'sell' : 'vender');

    // modo papel/real para el aviso — SIN prompt de PIN en esta fase (no bloquear)
    let paper = null;
    try {
      const acct = await window._tradeAccountInfo(false);
      if (acct && typeof acct.paper === 'boolean') paper = acct.paper;
    } catch (e) {}

    const orderObj = { symbol: res.symbol, side, label: res.label, kind: res.kind };
    if (notional != null) orderObj.notional = notional; else orderObj.qty = qty;

    const confirmed = params.confirmed === true || params.confirmed === 'true';
    if (!confirmed) {
      // tarjeta de confirmación visual en la Cabina (también se puede confirmar
      // con un clic) + resumen hablable para el sí verbal. NADA se envía aquí.
      this._defer(() => { if (window._openBrokerStage) window._openBrokerStage({ confirm: orderObj }); });
      const mode = paper === false
        ? (en ? 'REAL-MONEY order' : 'Orden con DINERO REAL')
        : paper === true ? (en ? 'PAPER (simulated) order' : 'Orden SIMULADA (papel)')
          : (en ? 'Order' : 'Orden');
      const summary = en
        ? `${mode}: ${verb} ${amountTxt} of ${res.label} (${res.symbol}). Do you confirm?`
        : `${mode}: ${verb} ${amountTxt} de ${res.label} (${res.symbol}). ¿Confirmas?`;
      return { success: false, needs_confirmation: true, summary, symbol: res.symbol, side, amount_usd: notional, qty, paper };
    }

    // confirmed=true → enviar de verdad (con guard anti-doble-envío compartido)
    const r = await window._executeTradeOrder(orderObj);
    this._defer(() => { if (window._openBrokerStage) window._openBrokerStage({}); });
    if (!r.ok) return { success: false, error: r.error };
    if (paper === null) {
      try {
        const a2 = await window._tradeAccountInfo(false);
        if (a2 && typeof a2.paper === 'boolean') paper = a2.paper;
      } catch (e) {}
    }
    if (r.dedup) {
      return { success: true, already_sent: true, symbol: res.symbol, paper, summary: en
        ? 'That same order was already sent a moment ago — I did not send it twice.'
        : 'Esa misma orden ya se envió hace un momento — no la envié dos veces.' };
    }
    const st = (r.data && r.data.status) || 'accepted';
    const modeDone = paper === false
      ? (en ? 'with REAL MONEY' : 'con DINERO REAL')
      : paper === true ? (en ? 'simulated (paper)' : 'simulada (papel)') : '';
    const summary = en
      ? `Done — order ${modeDone} sent: ${verb} ${amountTxt} of ${res.label}. Broker status: ${st}. It is on screen.`
      : `Listo — orden ${modeDone} enviada: ${verb} ${amountTxt} de ${res.label}. Estado en el bróker: ${st}. La tienes en pantalla.`;
    return { success: true, status: st, symbol: res.symbol, side, amount_usd: notional, qty, paper, summary };
  },

  // get_portfolio_status: cuenta + posiciones del bróker en texto hablable
  // (ES/EN) y abre el stage 'broker' de la Cabina para verlo en pantalla.
  async _toolPortfolioStatus() {
    const en = (((typeof LANG !== 'undefined') ? LANG : (localStorage.getItem('eco_lang') || 'es')) === 'en');
    if (!window._tradeAccountInfo || !window._tradeFetch) {
      return { success: false, error: en ? 'Trading module not loaded.' : 'El módulo de trading no está cargado.' };
    }
    // interactivo: puede pedir el PIN una vez (lo gestiona window._tradeFetch)
    const acct = await window._tradeAccountInfo(true, true);
    if (!acct || acct.error) {
      // 403 sin TRADE_PIN → el mensaje del server ya viene en español; leerlo tal cual
      return { success: false, error: (acct && acct.error) || (en ? 'Could not reach the broker.' : 'No pude conectar con el bróker.') };
    }
    let positions = [];
    try {
      const r = await window._tradeFetch('/api/trade/positions/detail', {}, false);
      const d = await r.json();
      if (Array.isArray(d)) positions = d;
    } catch (e) {}

    this._defer(() => { if (window._openBrokerStage) window._openBrokerStage({}); });

    const equity = +acct.equity || 0, cash = +acct.cash || 0, bp = +acct.buying_power || 0;
    const fmt = v => '$' + (+v || 0).toLocaleString('en-US', { maximumFractionDigits: 0 });
    const pct = p => ((+p || 0) >= 0 ? '+' : '') + (+p || 0).toFixed(1) + '%';
    let best = null, worst = null;
    positions.forEach(p => {
      if (!best || (+p.unrealized_pct || 0) > (+best.unrealized_pct || 0)) best = p;
      if (!worst || (+p.unrealized_pct || 0) < (+worst.unrealized_pct || 0)) worst = p;
    });
    const paper = (typeof acct.paper === 'boolean') ? acct.paper : null;
    const mode = paper === false
      ? (en ? 'REAL-MONEY account' : 'Cuenta con DINERO REAL')
      : paper === true ? (en ? 'Paper (simulated) account' : 'Cuenta SIMULADA (papel)')
        : (en ? 'Broker account' : 'Cuenta del bróker');
    let summary;
    if (en) {
      summary = `${mode}. Equity ${fmt(equity)}, cash ${fmt(cash)}, buying power ${fmt(bp)}. `
        + (positions.length ? `${positions.length} open position${positions.length > 1 ? 's' : ''}.` : 'No open positions.');
      if (best && positions.length > 1 && best !== worst) summary += ` Best: ${best.symbol} ${pct(best.unrealized_pct)}. Worst: ${worst.symbol} ${pct(worst.unrealized_pct)}.`;
      else if (best) summary += ` ${best.symbol}: ${pct(best.unrealized_pct)}.`;
      summary += ' It is on screen.';
    } else {
      summary = `${mode}. Valor total ${fmt(equity)}, efectivo ${fmt(cash)}, poder de compra ${fmt(bp)}. `
        + (positions.length ? `Tienes ${positions.length} ${positions.length === 1 ? 'posición abierta' : 'posiciones abiertas'}.` : 'No tienes posiciones abiertas.');
      if (best && positions.length > 1 && best !== worst) summary += ` La mejor: ${best.symbol} ${pct(best.unrealized_pct)}. La peor: ${worst.symbol} ${pct(worst.unrealized_pct)}.`;
      else if (best) summary += ` ${best.symbol}: ${pct(best.unrealized_pct)}.`;
      summary += ' La tienes en pantalla.';
    }
    return {
      success: true, paper, equity, cash, buying_power: bp, positions_count: positions.length,
      best: best ? { symbol: best.symbol, pnl_pct: +(+best.unrealized_pct || 0).toFixed(2) } : null,
      worst: worst ? { symbol: worst.symbol, pnl_pct: +(+worst.unrealized_pct || 0).toFixed(2) } : null,
      summary,
    };
  },

  // Ejecuta una acción visual pesada FUERA del hilo crítico del WebSocket, para
  // no bloquear el procesamiento/agendado del audio mientras Bixby habla.
  // OJO: requestAnimationFrame se CONGELA en pestañas ocultas. Si la pestaña
  // está en background usamos setTimeout (sí dispara), para que ni las acciones
  // ni el respond() de run_stress_test queden colgados y cuelguen a ElevenLabs.
  _defer(fn) {
    const run = () => { try { fn(); } catch {} };
    if (typeof document !== 'undefined' && document.hidden) { setTimeout(run, 0); return; }
    if (typeof requestAnimationFrame === 'function') requestAnimationFrame(run);
    else setTimeout(run, 0);
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
    // reflejar el estado en la Cabina de Bixby (si está abierta)
    if (window.BixbyCockpit && window.BixbyCockpit.setState && text) {
      const lo = text.toLowerCase();
      const mode = (lo.includes('procesando') || lo.includes('pensando') || lo.includes('tú:')) ? 'think'
        : (lo.includes('escucha') || lo.includes('habla') || lo.includes('bixby:')) ? 'live' : '';
      const label = lo.includes('bixby:') ? 'Hablando' : lo.includes('escucha') ? 'Escuchando'
        : mode === 'think' ? 'Pensando' : lo.includes('conectando') || lo.includes('iniciando') ? 'Conectando' : 'Listo';
      window.BixbyCockpit.setState(mode, label);
    }
    if (isError) {
      const el = document.getElementById('bixby-status');
      if (el) el.style.display = 'block';
      if (typeof toast === 'function') toast(text);
    }
  },
};

window.BixbyVoice = BixbyVoice;

/* ============================================================================
   TRADING COMPARTIDO (Etapa M) — helpers usados por voice.js (tools de Bixby),
   engine/cockpit.js (stage 'broker') y engine/command_center.js. UN solo lugar
   para: resolver el símbolo (cripto → equity), leer la cuenta, ejecutar la
   orden (con guard anti-doble-envío) y abrir el stage del bróker. NO duplicar.
   Contrato server: POST /api/trade/order {symbol, side, notional|qty,
   type:'market'} — cripto usa 'BTC/USD' y el server fuerza time_in_force=gtc.
   Todas las rutas /api/trade/* van por window._tradeFetch (PIN X-Trade-Pin).
   ============================================================================ */
(function () {
  'use strict';

  function tlang() {
    try { return (window.LANG || localStorage.getItem('eco_lang') || 'es'); } catch (e) { return 'es'; }
  }
  function tnorm(s) {
    if (window.KhipuResolve && window.KhipuResolve.norm) return window.KhipuResolve.norm(s);
    return String(s == null ? '' : s).toLowerCase().replace(/\s+/g, ' ').trim();
  }

  // Alias estáticos de cripto (fallback si la lista de Alpaca aún no cargó) —
  // clave normalizada (como la dicta/escribe el usuario) → símbolo base;
  // el par tradeable siempre es <BASE>/USD.
  var CRYPTO_ALIAS = {
    'btc': 'BTC', 'bitcoin': 'BTC', 'bit coin': 'BTC', 'bitcoin core': 'BTC',
    'eth': 'ETH', 'ethereum': 'ETH', 'ether': 'ETH', 'etherium': 'ETH', 'eterium': 'ETH', 'iterium': 'ETH',
    'sol': 'SOL', 'solana': 'SOL',
    'doge': 'DOGE', 'dogecoin': 'DOGE', 'doge coin': 'DOGE', 'dogue coin': 'DOGE',
    'ltc': 'LTC', 'litecoin': 'LTC', 'lite coin': 'LTC',
    'xrp': 'XRP', 'ripple': 'XRP',
    'ada': 'ADA', 'cardano': 'ADA',
    'avax': 'AVAX', 'avalanche': 'AVAX',
    'link': 'LINK', 'chainlink': 'LINK', 'chain link': 'LINK',
    'dot': 'DOT', 'polkadot': 'DOT',
    'shib': 'SHIB', 'shiba': 'SHIB', 'shiba inu': 'SHIB',
    'uni': 'UNI', 'uniswap': 'UNI',
    'aave': 'AAVE',
    'bch': 'BCH', 'bitcoin cash': 'BCH',
    'usdt': 'USDT', 'tether': 'USDT',
    'usdc': 'USDC', 'usd coin': 'USDC',
    'mkr': 'MKR', 'maker': 'MKR',
    'crv': 'CRV', 'curve': 'CRV',
    'xtz': 'XTZ', 'tezos': 'XTZ',
    'bat': 'BAT', 'basic attention token': 'BAT',
    'sushi': 'SUSHI', 'sushiswap': 'SUSHI',
    'grt': 'GRT', 'the graph': 'GRT',
    'pepe': 'PEPE',
  };
  var CRYPTO_LABEL = {
    BTC: 'Bitcoin', ETH: 'Ethereum', SOL: 'Solana', DOGE: 'Dogecoin', LTC: 'Litecoin',
    XRP: 'XRP', ADA: 'Cardano', AVAX: 'Avalanche', LINK: 'Chainlink', DOT: 'Polkadot',
    SHIB: 'Shiba Inu', UNI: 'Uniswap', AAVE: 'Aave', BCH: 'Bitcoin Cash', USDT: 'Tether',
    USDC: 'USD Coin', MKR: 'Maker', CRV: 'Curve', XTZ: 'Tezos', BAT: 'BAT',
    SUSHI: 'SushiSwap', GRT: 'The Graph', PEPE: 'Pepe',
  };

  var _assetsCache = null;   // { ts, list: [{symbol:'BTC/USD', name:'Bitcoin'}, …] }
  async function cryptoAssets() {
    if (_assetsCache && (Date.now() - _assetsCache.ts) < 3600000) return _assetsCache.list;
    if (!window._tradeFetch) return null;
    try {
      // interactive=false: NUNCA pedir el PIN solo para resolver un nombre
      var r = await window._tradeFetch('/api/trade/crypto/assets', {}, false);
      if (!r.ok) return null;
      var d = await r.json();
      var list = (d && Array.isArray(d.assets)) ? d.assets : null;
      if (list && list.length) _assetsCache = { ts: Date.now(), list: list };
      return list;
    } catch (e) { return null; }
  }

  // window._resolveTradeSymbol(texto) → Promise<
  //   {ok:true, kind:'crypto'|'equity', symbol:'BTC/USD'|'NVDA', label, node?} |
  //   {ok:false, error (bilingüe, hablable), suggestions:[labels]}>
  // Orden del contrato: cripto primero (alias estático + lista real de Alpaca),
  // después equity vía KhipuResolve → ticker.
  window._resolveTradeSymbol = async function (q) {
    var en = tlang() === 'en';
    var raw = String(q == null ? '' : q).trim().replace(/[?!.]+$/, '').trim();
    if (!raw) return { ok: false, error: en ? 'Which asset?' : '¿Qué activo?', suggestions: [] };

    // ¿ya viene como par cripto? ("BTC/USD", "eth/usd")
    var pair = raw.toUpperCase().match(/^([A-Z0-9]{2,10})\s*\/\s*(USD[TC]?)$/);
    if (pair) return { ok: true, kind: 'crypto', symbol: pair[1] + '/USD', label: CRYPTO_LABEL[pair[1]] || pair[1] };

    var nq = tnorm(raw).replace(/^(de |del |el |la )/, '').trim();
    if (!nq) return { ok: false, error: en ? 'Which asset?' : '¿Qué activo?', suggestions: [] };

    // 1) alias estático de cripto
    var base = CRYPTO_ALIAS[nq] || null;

    // 2) lista real de activos cripto tradeables en Alpaca
    if (!base) {
      var assets = await cryptoAssets();
      if (assets && assets.length) {
        var up = nq.toUpperCase();
        for (var i = 0; i < assets.length; i++) {
          var sym = String(assets[i].symbol || '');
          var b = sym.split('/')[0];
          if (b === up || tnorm(assets[i].name || '') === nq) { base = b; break; }
        }
        if (!base && nq.length >= 4) {
          for (var j = 0; j < assets.length; j++) {
            var nm = tnorm(assets[j].name || '');
            if (nm && (nm.indexOf(nq) === 0 || nq.indexOf(nm) === 0)) {
              base = String(assets[j].symbol || '').split('/')[0];
              break;
            }
          }
        }
      }
    }
    if (base) return { ok: true, kind: 'crypto', symbol: base + '/USD', label: CRYPTO_LABEL[base] || base };

    // 3) equity vía el resolutor compartido (alias de voz, fuzzy, sugerencias)
    if (window.KhipuResolve) {
      var r = window.KhipuResolve.find(raw);
      if (r && r.node) {
        if (r.node.mkt) return { ok: true, kind: 'equity', symbol: r.node.mkt, label: r.node.label, node: r.node };
        return { ok: false, suggestions: [], error: en
          ? (r.node.label + ' is not publicly traded — I cannot place orders on it.')
          : (r.node.label + ' no cotiza en bolsa — no puedo operarla.') };
      }
      var nf = window.KhipuResolve.notFound(raw);
      return { ok: false, error: nf.spoken, suggestions: (nf.suggestions || []).map(function (n) { return n.label; }) };
    }
    return { ok: false, error: en ? ('I could not find "' + raw + '".') : ('No encontré «' + raw + '».'), suggestions: [] };
  };

  // window._tradeAccountInfo(interactive, force) → JSON de la cuenta de Alpaca
  // (+ campo paper) con caché de 30 s. En error devuelve {error, status}: el
  // 403 sin TRADE_PIN trae el mensaje del server TAL CUAL (ya en español).
  window._tradeAccountInfo = async function (interactive, force) {
    var c = window.__tradeAcctCache;
    if (!force && c && (Date.now() - c.ts) < 30000) return c.data;
    if (!window._tradeFetch) return { error: 'trading no disponible' };
    try {
      var r = await window._tradeFetch('/api/trade/account', {}, !!interactive);
      var d = await r.json().catch(function () { return {}; });
      if (!r.ok) return { error: (d && d.error) || ('HTTP ' + r.status), status: r.status };
      window.__tradeAcctCache = { ts: Date.now(), data: d };
      return d;
    } catch (e) { return { error: String((e && e.message) || e) }; }
  };

  // window._executeTradeOrder({symbol, side, notional?|qty?, kind?, label?})
  // → POST /api/trade/order (PIN interactivo). Montos: $1–$100,000 por orden.
  // Guard anti-doble-envío: la MISMA orden (símbolo+lado+monto) en <90 s no se
  // re-envía (la voz y el clic de la Cabina pueden confirmar a la vez).
  window._executeTradeOrder = async function (o) {
    o = o || {};
    var en = tlang() === 'en';
    if (!window._tradeFetch) return { ok: false, error: 'trading no disponible' };
    if (!o.symbol) return { ok: false, error: en ? 'Missing symbol.' : 'Falta el símbolo.' };
    var side = o.side === 'sell' ? 'sell' : 'buy';
    var body = { symbol: o.symbol, side: side, type: 'market' };
    if (o.notional != null && isFinite(+o.notional)) {
      var amt = Math.round(+o.notional * 100) / 100;
      if (!(amt >= 1 && amt <= 100000)) {
        return { ok: false, error: en
          ? 'The amount must be between $1 and $100,000 per order.'
          : 'El monto debe estar entre $1 y $100,000 por orden.' };
      }
      body.notional = amt;
    } else if (o.qty != null && +o.qty > 0) {
      body.qty = +o.qty;
    } else {
      return { ok: false, error: en ? 'Missing order amount.' : 'Falta el monto de la orden.' };
    }
    // el server fuerza gtc para cripto; day para acciones
    body.time_in_force = (o.kind === 'crypto' || o.symbol.indexOf('/') >= 0) ? 'gtc' : 'day';

    var key = body.symbol + '|' + side + '|' + (body.notional || '') + '|' + (body.qty || '');
    var last = window.__lastTradeExec;
    if (last && last.key === key && (Date.now() - last.ts) < 90000) {
      return { ok: true, dedup: true, data: last.data };
    }
    try {
      var r = await window._tradeFetch('/api/trade/order', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      }, true);
      var d = await r.json().catch(function () { return { error: 'respuesta inválida del servidor' }; });
      if (r.ok && (d.id || d.status)) {
        window.__lastTradeExec = { key: key, ts: Date.now(), data: d };
        window.__tradeAcctCache = null;   // la cuenta cambió — invalidar caché
        return { ok: true, data: d };
      }
      return { ok: false, status: r.status, error: (d && (d.error || d.message)) || ('HTTP ' + r.status) };
    } catch (e) { return { ok: false, error: String((e && e.message) || e) }; }
  };

  // Abre el stage 'broker' de la Cabina (y abre la Cabina si está cerrada).
  // arg: {} · {confirm:{symbol,side,notional|qty,label,kind}} · etc.
  window._openBrokerStage = function (arg) {
    var ck = window.BixbyCockpit;
    if (!ck) return false;
    try {
      if (ck.isOpen && ck.isOpen()) ck.stage('broker', arg || {});
      else ck.open({ kind: 'broker', arg: arg || {} });
      return true;
    } catch (e) { return false; }
  };
})();
