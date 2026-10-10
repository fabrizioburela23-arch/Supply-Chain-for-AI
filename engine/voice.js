// engine/voice.js — Khipu, el asistente de voz de Khipu Finance
// Cliente WebSocket de ElevenLabs Agents (Conversational AI). Khipu es el "Jarvis de las
// finanzas": escucha por micrófono, responde por voz, y puede controlar la terminal.
//
// Depende de app.html: Keys, BASE, NODES, NODE_BY_ID, MKT, selected, stressId,
//   stressAffected, activateStress, jumpTo, computeNRS, catLabel, toast, LANG, activeTab
//
// PROTOCOLO (verificado oct-2026 contra los SDK oficiales @elevenlabs/client 1.27 y
// @elevenlabs/types 0.24 — se mantiene el WebSocket crudo con URL firmada: es lo
// más pequeño y robusto aquí; WebRTC exigiría cargar LiveKit + worklets):
//   → conversation_initiation_client_data {conversation_config_override?}  (al abrir)
//   ← conversation_initiation_metadata {conversation_id, agent_output_audio_format,
//       user_input_audio_format}  ← AQUÍ se sabe el formato (pcm_8000…pcm_48000 | ulaw_8000).
//       Antes se asumía 16 kHz SIEMPRE: con un agente en pcm_22050/24000/44100 la voz
//       salía lenta y grave ("no estaba dando bien").
//   → {user_audio_chunk: base64}  PCM16 LE mono (o µ-law) a la tasa de user_input_audio_format
//   ← audio {audio_event:{audio_base_64, event_id}}
//   ← interruption {interruption_event:{event_id}} → cortar Y descartar audio viejo (event_id menor)
//   ← ping {ping_event:{event_id}} → pong {event_id}
//   ← client_tool_call {client_tool_call:{tool_name, tool_call_id, parameters}}
//       → client_tool_result {tool_call_id, result: STRING, is_error}
//   ← error {error_event:{error_type, message, code}} (override_error, llm_error, max_duration…)
//   ← agent_response / agent_response_correction / user_transcript / agent_tool_response (end_call)
//   → contextual_update {text}
// Overrides: SOLO los que el agente permite (los dice /api/voice/session); si aun así
// ElevenLabs cierra por override_error, se reconecta UNA vez sin overrides.

function _voiceL(es, en) {
  let l = 'es';
  try { l = (typeof window !== 'undefined' && window.LANG) || localStorage.getItem('eco_lang') || 'es'; } catch (e) {}
  return l === 'en' ? en : es;
}
function _voiceLang() {
  try { return ((typeof window !== 'undefined' && window.LANG) || localStorage.getItem('eco_lang') || 'es') === 'en' ? 'en' : 'es'; }
  catch (e) { return 'es'; }
}

// Tope (s) que el agente espera cada herramienta — ESPEJO de _VOICE_TOOL_TIMEOUTS en
// server.py (un test los compara). Respondemos SIEMPRE ~1.5 s antes para que
// ElevenLabs nunca vea un timeout (el agente quedaba mudo o decía "falló").
const VOICE_TOOL_TIMEOUT_S = { ask_khipu_brain: 60, run_agent_simulation: 90, deep_research: 90,
  get_news: 20, show_insights: 15, place_paper_trade: 45, get_portfolio_status: 45, get_space_summary: 20 };
const VOICE_TOOL_TIMEOUT_DEFAULT_S = 10;

// Precio de una cotización por el contrato único (window.quotePx: live numérico o close).
function _voicePx(q) {
  if (!q) return null;
  try { if (window.quotePx) { const v = window.quotePx(q); return (v && isFinite(v)) ? v : null; } } catch (e) {}
  return (q.close && isFinite(q.close)) ? q.close : null;
}

const VoiceAudio = {
  parseFormat(f) {
    const m = /^(pcm|ulaw)_(\d{4,6})$/.exec(String(f || ''));
    return m ? { format: m[1], sampleRate: +m[2] } : { format: 'pcm', sampleRate: 16000 };
  },
  // µ-law (G.711) — mismo algoritmo que los worklets del SDK oficial
  ulawDecode(u) {
    u = ~u & 0xff;
    const sign = u & 0x80, exp = (u >> 4) & 0x07, man = u & 0x0f;
    let s = [0, 132, 396, 924, 1980, 4092, 8316, 16764][exp] + (man << (exp + 3));
    return sign ? -s : s;
  },
  ulawEncode(sample) {
    const BIAS = 0x84, CLIP = 32635;
    let sign = (sample >> 8) & 0x80;
    if (sign) sample = -sample;
    sample = Math.min(CLIP, sample + BIAS);
    let exp = 7;
    for (let mask = 0x4000; (sample & mask) === 0 && exp > 0; exp--, mask >>= 1) {}
    const man = (sample >> (exp + 3)) & 0x0f;
    return (~(sign | (exp << 4) | man)) & 0xff;
  },
  // base64 → Float32 [-1,1] según formato (PCM16 little-endian o µ-law)
  decode(b64, fmt) {
    const bin = atob(b64);
    if (fmt && fmt.format === 'ulaw') {
      const out = new Float32Array(bin.length);
      for (let i = 0; i < bin.length; i++) out[i] = this.ulawDecode(bin.charCodeAt(i)) / 32768;
      return out;
    }
    const n = bin.length >> 1, out = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      let v = bin.charCodeAt(2 * i) | (bin.charCodeAt(2 * i + 1) << 8);
      if (v >= 0x8000) v -= 0x10000;
      out[i] = v / 32768;
    }
    return out;
  },
  // Float32 → bytes (PCM16 LE o µ-law) → base64
  encode(f32, fmt) {
    const ulaw = fmt && fmt.format === 'ulaw';
    const bytes = new Uint8Array(ulaw ? f32.length : f32.length * 2);
    for (let i = 0; i < f32.length; i++) {
      const s = Math.max(-1, Math.min(1, f32[i]));
      const v = Math.round(s < 0 ? s * 32768 : s * 32767);
      if (ulaw) bytes[i] = this.ulawEncode(v);
      else { bytes[2 * i] = v & 0xff; bytes[2 * i + 1] = (v >> 8) & 0xff; }
    }
    let bin = '';
    for (let i = 0; i < bytes.length; i += 0x2000) bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x2000));
    return btoa(bin);
  },
  // Re-muestreo de UN bloque suelto (largo exacto n·dst/src; lineal, borde sostenido).
  resampleOnce(f32, srcRate, dstRate) {
    if (!srcRate || !dstRate || srcRate === dstRate) return f32;
    const n = Math.max(1, Math.round(f32.length * dstRate / srcRate)), out = new Float32Array(n);
    const step = srcRate / dstRate, last = f32.length - 1;
    for (let i = 0; i < n; i++) {
      const p = i * step, a = Math.min(last, Math.floor(p)), b = Math.min(last, a + 1), fr = p - Math.floor(p);
      out[i] = f32[a] * (1 - fr) + f32[b] * fr;
    }
    return out;
  },
  // Re-muestreo CON ESTADO entre bloques (antes cada bloque se truncaba: 2048 muestras
  // a 48 kHz → 682,67 → se perdía un trocito por bloque = clics y deriva). Bajando de
  // tasa se promedia la ventana (filtro de caja = anti-aliasing simple); subiendo, lineal.
  makeResampler(srcRate, dstRate) {
    if (!srcRate || !dstRate || srcRate === dstRate) return f => f;
    const ratio = srcRate / dstRate;
    let tail = new Float32Array(0), pos = 0;
    return (input) => {
      const buf = new Float32Array(tail.length + input.length);
      buf.set(tail); buf.set(input, tail.length);
      const out = [];
      if (ratio > 1) {
        while (pos + ratio <= buf.length) {
          const a = Math.floor(pos), b = Math.max(a + 1, Math.floor(pos + ratio));
          let s = 0;
          for (let i = a; i < b; i++) s += buf[i];
          out.push(s / (b - a));
          pos += ratio;
        }
      } else {
        while (pos + 1 < buf.length) {
          const a = Math.floor(pos), fr = pos - a;
          out.push(buf[a] * (1 - fr) + buf[a + 1] * fr);
          pos += ratio;
        }
      }
      const used = Math.min(Math.floor(pos), buf.length);
      tail = buf.slice(used); pos -= used;
      return Float32Array.from(out);
    };
  },
};

const BixbyVoice = {
  ws: null,
  isConnected: false,
  audioCtx: null,
  audioQueue: [],
  isPlaying: false,
  _sess: 0,                 // id de intento: eventos de sockets viejos se ignoran
  _inFmt: null,
  _outFmt: null,
  _lastInterruptId: 0,
  _metaReceived: false,
  // ── Estado PÚBLICO de la voz: off | connecting | listening | speaking | thinking | error ──
  // La Cabina pinta su micrófono con esto (getState() o el evento 'khipu:voice' en window) — antes
  // ponía "Escuchando" por su cuenta y quedaba encendido tras cancelar o fallar la conexión.
  state: 'off',
  stateText: '',
  lastError: '',

  getState() {
    return { state: this.state, text: this.stateText, error: this.state === 'error' ? this.lastError : '',
             connected: !!this.isConnected, connecting: this.isConnecting() };
  },

  // ¿hay un intento de conexión VIVO? (uno ya cancelado no cuenta; un reintento agendado sí; y también
  // el saludo del WebSocket: connect() ya terminó pero el socket aún no abrió — antes toggle() abría
  // un SEGUNDO socket ahí y dejaba el primero huérfano)
  isConnecting() {
    return (this._connSess === this._sess && (!!this._connecting || this._handshaking())) || !!this._retryTimer;
  },
  _handshaking() {
    return !!this.ws && !this.isConnected && this.ws.readyState === 0;   // 0 = WebSocket.CONNECTING
  },

  _emitVoice(state, text) {
    const prev = this.state;
    this.state = state;
    this.stateText = String(text || '');
    if (state === 'error') this.lastError = this.stateText;
    else if (state === 'connecting') this.lastError = '';
    try {
      if (typeof window !== 'undefined' && typeof window.dispatchEvent === 'function' && typeof CustomEvent === 'function') {
        window.dispatchEvent(new CustomEvent('khipu:voice', { detail: {
          state, prev, text: this.stateText, error: state === 'error' ? this.stateText : '' } }));
      }
    } catch (e) {}
  },

  async init() {
    if (this.audioCtx) return;
    try {
      this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    } catch {}
  },

  async toggle() {
    (this.isConnected || this.isConnecting()) ? this.disconnect() : await this.connect();
  },

  stop() { this.disconnect(); },

  async connect(opts) {
    opts = opts || {};
    // ya hay un intento vivo, o su socket está saludando (uno cancelado no bloquea)
    if (this._connSess === this._sess && (this._connecting || this._handshaking())) return;
    clearTimeout(this._retryTimer); this._retryTimer = 0;
    const att = this._attempt = (this._attempt || 0) + 1;
    this._connecting = true;
    try { await this._connect(opts); }
    catch (e) {
      // un intento cancelado (o reemplazado por otro) no pinta errores encima del estado actual
      if (att === this._attempt && this._connSess === this._sess) {
        this._fail(_voiceL('Khipu: error inesperado al conectar — ', 'Khipu: unexpected error while connecting — ') + ((e && e.message) || e));
      }
    }
    finally { if (att === this._attempt) this._connecting = false; }
  },

  async _connect(opts) {
    const sess = ++this._sess;
    this._connSess = sess;
    this._closingByUser = false;
    this._lastErrorEvent = null;
    // un socket de un intento anterior (p. ej. quedó abierto tras fallar el micrófono) ya no recibe
    // eventos (sess cambió): se cierra en vez de dejarlo huérfano
    if (this.ws) {
      const old = this.ws;
      this.ws = null; this.isConnected = false; this._metaReceived = false;
      this._stopMic();
      try { old.close(1000, 'replaced'); } catch (e) {}
    }

    // ── Paso 1: AudioContext DENTRO del gesto del usuario (iOS Safari solo deja
    // sonar un contexto creado/reanudado en el gesto; antes se hacía tras await).
    this.init();
    try { if (this.audioCtx && this.audioCtx.state !== 'running' && this.audioCtx.state !== 'closed') this.audioCtx.resume(); } catch (e) {}

    // ── Paso 2: micrófono (también en el gesto: Chrome Android / Safari iOS) ──
    this._showOverlay(_voiceL('Khipu — pidiendo micrófono…', 'Khipu — requesting microphone…'), 'connect');
    let stream = null;
    if (!(typeof navigator !== 'undefined' && navigator.mediaDevices && navigator.mediaDevices.getUserMedia)) {
      this._fail(_voiceL('Este navegador no da acceso al micrófono aquí (¿la página no es HTTPS?).',
        'This browser gives no microphone access here (is the page not HTTPS?).'));
      return;
    }
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 },
        video: false,
      });
    } catch (e) {
      if (sess !== this._sess) return;   // el usuario ya canceló: sin error encima de "apagado"
      this._fail(this._micErrorText(e));
      return;
    }
    if (sess !== this._sess) { this._stopTracks(stream); return; }   // el usuario canceló
    this._releasePre();
    this._preStream = stream;
    // iOS: abrir el micrófono puede dejar el contexto 'suspended' o 'interrupted'
    if (this.audioCtx && this.audioCtx.state !== 'running' && this.audioCtx.state !== 'closed') {
      try { await this.audioCtx.resume(); } catch (e) {}
      // cancelado MIENTRAS se reanudaba el audio: sin esto el intento viejo volvía a pintar
      // "conectando…" encima de "apagado" y el micrófono de la Cabina quedaba trabado
      if (sess !== this._sess) {
        if (this._preStream === stream) this._releasePre(); else this._stopTracks(stream);
        return;
      }
    }

    // ── Paso 3: credenciales del server (la clave NUNCA llega al navegador) ──
    this._showOverlay(_voiceL('Khipu — conectando…', 'Khipu — connecting…'), 'connect');
    const base = (typeof BASE !== 'undefined') ? BASE : '';
    let agentPref = null;
    try { agentPref = localStorage.getItem('elevenlabs_agent_id'); } catch (e) {}
    const [pd, sres] = await Promise.all([
      fetch(`${base}/api/voice/bixby-prompt`).then(r => (r.ok ? r.json() : null)).catch(() => null),
      fetch(`${base}/api/voice/session`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(agentPref ? { agent_id: agentPref } : {}),
      }).then(async r => ({ status: r.status, data: await r.json().catch(() => ({})) }))
        .catch(e => ({ status: 0, data: { error: _voiceL('Sin conexión con el servidor de Khipu.', 'No connection to the Khipu server.') } })),
    ]);
    if (sess !== this._sess) {   // cancelado: suelta SOLO su micrófono (puede haber ya otro intento con el suyo)
      if (this._preStream === stream) this._releasePre(); else this._stopTracks(stream);
      return;
    }
    const sd = (sres && sres.data) || {};
    const signedUrl = sd.signed_url || sd.signedUrl;
    if (!signedUrl) {
      const en = _voiceLang() === 'en';
      let msg = (en ? (sd.error_en || sd.error) : (sd.error || sd.error_en))
        || _voiceL('El servidor no entregó la sesión de voz.', 'The server did not return a voice session.');
      const fix = en ? sd.fix_en : sd.fix_es;
      if (fix) msg += ' — ' + fix;
      this._releasePre();
      this._fail('Khipu: ' + msg);
      return;
    }
    this._systemPrompt = (pd && pd.system_prompt) || null;
    const override = opts.noOverride ? null : this._buildOverride(pd, sd);

    // ── Paso 4: WebSocket ──────────────────────────────────────────────────────
    this._openSocket(signedUrl, override, sess);
  },

  // Qué overrides mandar: solo los que el AGENTE permite (sd.overrides, leído del
  // agente por el server) y solo si cambian algo. Sin esa info → regla vieja
  // (ELEVENLABS_ALLOW_OVERRIDE). Si en esta pestaña ya falló por override → nada.
  _buildOverride(pd, sd) {
    try { if (sessionStorage.getItem('kh_voice_no_override') === '1') return null; } catch (e) {}
    const lang = _voiceLang();
    const known = sd && sd.overrides && typeof sd.overrides === 'object';
    const ov = known ? sd.overrides : null;
    const envOn = !!((pd && pd.allow_override) || (sd && sd.override_env));
    const agentLang = (sd && sd.language) || 'es';
    const agent = {};
    if (known ? ov.language : envOn) { if (!known || agentLang !== lang) agent.language = lang; }
    if (envOn && (known ? ov.prompt : true) && this._systemPrompt) agent.prompt = { prompt: this._systemPrompt };
    if (known && ov.first_message && lang === 'en' && agentLang !== 'en' && sd.has_first_message) {
      agent.first_message = "Hi, I'm Khipu. What would you like to analyze?";
    }
    return Object.keys(agent).length ? { agent } : null;
  },

  _openSocket(url, override, sess) {
    let ws;
    try { ws = new WebSocket(url); }
    catch (e) { this._releasePre(); this._fail(_voiceL('No se pudo abrir la conexión de voz: ', 'Could not open the voice connection: ') + ((e && e.message) || e)); return; }
    this.ws = ws;
    this._metaReceived = false;
    this._lastInterruptId = 0;
    this._overrideSent = override;
    this._inFmt = null; this._outFmt = null;

    ws.onopen = () => {
      if (sess !== this._sess) return;
      this.isConnected = true;
      this._showOverlay(_voiceL('Khipu — iniciando sesión…', 'Khipu — starting session…'), 'connect');
      this._sendInitContext(override);
      // El micrófono arranca con conversation_initiation_metadata (antes NO se puede mandar audio)
      clearTimeout(this._initTimer);
      this._initTimer = setTimeout(() => {
        if (sess === this._sess && !this._metaReceived && this.ws === ws) {
          this._lastErrorEvent = { error_type: 'init_timeout' };
          try { ws.close(4000, 'init timeout'); } catch (e) {}
        }
      }, 15000);
    };
    ws.onmessage = (e) => {
      if (sess !== this._sess) return;
      let msg;
      try { msg = JSON.parse(e.data); } catch { return; }
      try { this._handleMessage(msg); } catch (err) { try { console.warn('[Khipu voz]', err); } catch (_) {} }
    };
    // onerror llega antes que onclose y sin detalle: el diagnóstico lo hace onclose
    ws.onerror = () => { if (sess === this._sess) this._wsErrored = true; };
    ws.onclose = (ev) => this._onSocketClose(ev || {}, sess);
  },

  _onSocketClose(ev, sess) {
    if (sess !== this._sess) return;           // socket viejo (ya hubo reintento o disconnect)
    clearTimeout(this._initTimer);
    const hadMeta = this._metaReceived;
    const errEv = this._lastErrorEvent || {};
    const reason = String(ev.reason || '');
    const override = this._overrideSent;
    // fin normal (el agente colgó con end_call o se cerró limpio): ElevenLabs cierra en cuanto ENVÍA el último
    // audio, que suena por delante del reloj → se deja terminar la despedida antes de limpiar (máx 8 s)
    const cleanEnd = hadMeta && ev.code === 1000 && !errEv.error_type && !this._closingByUser;
    this.ws = null;
    this.isConnected = false;
    this._metaReceived = false;
    this._stopMic();
    if (!cleanEnd) this._stopScheduled();
    this._orbOff();
    if (this._closingByUser) { this._releasePre(); this._hideOverlay(); return; }
    if (cleanEnd) {
      this._releasePre();
      const ctx = this.audioCtx;
      const left = (ctx && this._playCursor) ? Math.max(0, this._playCursor - ctx.currentTime) : 0;
      clearTimeout(this._endTimer);
      this._endTimer = setTimeout(() => {
        if (sess !== this._sess || this.isConnected) return;   // ya empezó otra sesión: no tocar su audio
        this._stopScheduled();
        this._hideOverlay();
      }, Math.min(8000, left * 1000 + 300));
      return;
    }

    // overrides rechazados → reintentar UNA vez sin overrides (no rompe la sesión)
    const overrideErr = errEv.error_type === 'override_error' || /override/i.test(reason);
    if (!hadMeta && override && overrideErr) {
      try { sessionStorage.setItem('kh_voice_no_override', '1'); } catch (e) {}
      this._releasePre();
      this._showOverlay(_voiceL('Khipu — reintentando sin ajustes de idioma…', 'Khipu — retrying without language overrides…'), 'connect');
      this._retryLater(() => this.connect({ noOverride: true, auto: true }), 50);
      return;
    }
    // caída de red a mitad de conversación → 1 reconexión automática por minuto
    const transient = [1001, 1006, 1012, 1013].indexOf(ev.code) >= 0;
    if (hadMeta && transient && !errEv.error_type && this._canAutoReconnect()) {
      this._releasePre();
      this._showOverlay(_voiceL('Khipu — se cortó la conexión, reconectando…', 'Khipu — connection dropped, reconnecting…'), 'connect');
      this._retryLater(() => this.connect({ auto: true, noOverride: !override }), 600);
      return;
    }
    this._releasePre();
    this._fail(this._closeText(ev, hadMeta, errEv));
  },

  // reintento agendado: cuenta como "conectando" y colgar (disconnect) lo cancela
  _retryLater(fn, ms) {
    clearTimeout(this._retryTimer);
    this._retryTimer = setTimeout(() => { this._retryTimer = 0; fn(); }, ms);
  },

  _canAutoReconnect() {
    const now = Date.now();
    if (typeof document !== 'undefined' && document.hidden) return false;
    if (this._lastAutoReconnect && now - this._lastAutoReconnect < 60000) return false;
    this._lastAutoReconnect = now;
    return true;
  },

  // Texto bilingüe y CONCRETO del cierre (antes: "Khipu desconectado (código 1008)").
  _closeText(ev, hadMeta, errEv) {
    const t = (errEv && errEv.error_type) || '';
    const reason = String((ev && ev.reason) || (errEv && (errEv.message || errEv.reason)) || '').slice(0, 160);
    const low = reason.toLowerCase();
    if (t === 'init_timeout') return _voiceL('ElevenLabs no respondió al iniciar la sesión. Reintenta en unos segundos.', 'ElevenLabs did not answer the session start. Retry in a few seconds.');
    if (t === 'max_duration_exceeded') return _voiceL('Se alcanzó la duración máxima de la conversación. Toca el micrófono para seguir.', 'Maximum conversation length reached. Tap the mic to continue.');
    if (t === 'override_error' || /override/.test(low)) return _voiceL('El agente no permite cambiar idioma/instrucciones por sesión. Toca el micrófono de nuevo (ya no se enviarán).', 'The agent does not allow per-session language/instructions. Tap the mic again (they will no longer be sent).');
    if (/^(llm_error|custom_llm_error|cascade_brain_error|llm_timeout)$/.test(t)) return _voiceL('El modelo de IA del agente falló. Revisa 🩺 → Khipu / ElevenLabs (puede ser un LLM retirado).', "The agent's AI model failed. Check 🩺 → Khipu / ElevenLabs (it may be a retired LLM).");
    if (t === 'tts_cascade_error') return _voiceL('Falló la voz del agente (modelo de voz). Revisa 🩺 → Khipu / ElevenLabs.', "The agent's voice (TTS model) failed. Check 🩺 → Khipu / ElevenLabs.");
    if (/^missing_dynamic_variable/.test(t)) return _voiceL('Las instrucciones del agente piden una variable que la app no envía. Reinicia el servidor para re-sincronizar a Khipu.', 'The agent instructions require a variable the app does not send. Restart the server to re-sync Khipu.');
    if (/quota|credit|limit/.test(low)) return _voiceL('Se acabaron los créditos de ElevenLabs. Revisa tu plan en elevenlabs.io → Subscription.', 'ElevenLabs credits are used up. Check your plan at elevenlabs.io → Subscription.');
    if (/concurren|busy|too many/.test(low)) return _voiceL('ElevenLabs está ocupado (límite de conversaciones a la vez). Reintenta en unos segundos.', 'ElevenLabs is busy (concurrent conversation limit). Retry in a few seconds.');
    if (/auth|signature|expired|unauthori/.test(low)) return _voiceL('La sesión de voz venció o no es válida. Toca el micrófono de nuevo.', 'The voice session expired or is invalid. Tap the mic again.');
    if (!hadMeta && (ev.code === 1006 || !ev.code)) return _voiceL('No se pudo abrir la conexión de voz con ElevenLabs (red, firewall o bloqueador). Reintenta.', 'Could not open the voice connection to ElevenLabs (network, firewall or blocker). Retry.');
    const code = (ev && ev.code) || '?';
    return reason
      ? _voiceL(`Khipu se desconectó: ${reason}`, `Khipu disconnected: ${reason}`)
      : _voiceL(`Khipu se desconectó (código ${code}). Reintenta.`, `Khipu disconnected (code ${code}). Retry.`);
  },

  _micErrorText(e) {
    const n = (e && e.name) || '';
    if (n === 'NotAllowedError' || n === 'PermissionDeniedError' || n === 'SecurityError') {
      return _voiceL('Permiso de micrófono denegado: tócalo en el candado de la barra de direcciones → Micrófono → Permitir, y reintenta.',
        'Microphone permission denied: click the lock in the address bar → Microphone → Allow, then retry.');
    }
    if (n === 'NotFoundError' || n === 'DevicesNotFoundError' || n === 'OverconstrainedError') {
      return _voiceL('No se encontró ningún micrófono en este equipo.', 'No microphone was found on this device.');
    }
    if (n === 'NotReadableError' || n === 'TrackStartError' || n === 'AbortError') {
      return _voiceL('El micrófono está ocupado por otra app (Zoom, Meet…). Ciérrala y reintenta.',
        'The microphone is busy in another app (Zoom, Meet…). Close it and retry.');
    }
    return _voiceL('Micrófono no disponible: ', 'Microphone unavailable: ') + ((e && e.message) || e);
  },

  disconnect() {
    this._sess++;                       // invalida eventos pendientes del socket actual
    this._closingByUser = true;
    clearTimeout(this._initTimer);
    clearTimeout(this._endTimer);
    clearTimeout(this._retryTimer); this._retryTimer = 0;   // un reintento agendado tampoco revive la voz
    this.isConnected = false;
    this._metaReceived = false;
    this._orbOff();
    this._stopMic();
    this._releasePre();
    this._stopScheduled();
    if (this.ws) {
      try { this.ws.close(1000, 'user disconnected'); } catch {}
      this.ws = null;
    }
    this._hideOverlay();
  },

  _stopTracks(stream) {
    try { if (stream) stream.getTracks().forEach(t => t.stop()); } catch (e) {}
  },
  _releasePre() {
    if (this._preStream) { this._stopTracks(this._preStream); this._preStream = null; }
  },

  _stopMic() {
    try { this._micSource?.disconnect(); } catch {}
    try { if (this._micProcessor) this._micProcessor.onaudioprocess = null; this._micProcessor?.disconnect(); } catch {}
    try { this._micMute?.disconnect(); } catch {}
    try { this._micStream?.getTracks().forEach(t => t.stop()); } catch {}
    this._micSource = null;
    this._micProcessor = null;
    this._micMute = null;
    this._micStream = null;
  },

  _startMicWithStream(stream) {
    if (this._micStream) return; // already running
    const fmt = this._inFmt || VoiceAudio.parseFormat('pcm_16000');
    try {
      const ctx = this.audioCtx;
      const resample = VoiceAudio.makeResampler(ctx.sampleRate, fmt.sampleRate);
      const srcNode = ctx.createMediaStreamSource(stream);

      // ScriptProcessor: deprecado pero universal (AudioWorklet exige servir un módulo
      // aparte). 2048 muestras ≈ 43 ms a 48 kHz: latencia baja sin cortes.
      const processor = ctx.createScriptProcessor(2048, 1, 1);
      processor.onaudioprocess = (ev) => {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN || !this._metaReceived) return;
        const f32 = ev.inputBuffer.getChannelData(0);

        // Visualizador: nivel RMS del micrófono
        let sum = 0;
        for (let i = 0; i < f32.length; i++) sum += f32[i] * f32[i];
        this._setMicLevel(Math.sqrt(sum / (f32.length || 1)));

        const out = resample(f32);
        if (!out.length) return;
        try { this.ws.send(JSON.stringify({ user_audio_chunk: VoiceAudio.encode(out, fmt) })); } catch (e) {}
      };

      // onaudioprocess solo dispara si el nodo llega al destino: por una ganancia en 0 (sin eco)
      const mute = ctx.createGain();
      mute.gain.value = 0;
      srcNode.connect(processor);
      processor.connect(mute);
      mute.connect(ctx.destination);

      this._micSource = srcNode;
      this._micProcessor = processor;
      this._micMute = mute;
      this._micStream = stream;

      this._showOverlay(_voiceL('🎙️ Khipu te escucha — habla', '🎙️ Khipu is listening — speak'), 'listen');
    } catch (e) {
      this._fail(_voiceL('Error al iniciar el micrófono: ', 'Could not start the microphone: ') + ((e && e.message) || e));
    }
  },

  // Map RMS mic level (0..~0.3) to the Jarvis visualizer bars
  _setMicLevel(rms) {
    const now = performance.now();
    if (now - (this._lastVizUpdate || 0) < 50) return; // ~20fps
    this._lastVizUpdate = now;
    const level = Math.min(1, rms * 8);
    // Orbe de voz de Khipu (engine/orb.js): energía del USUARIO (cian/teal).
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

  // ── Orbe de voz de Khipu (engine/orb.js) ───────────────────────────────────
  // La Cabina monta el orbe en su header y lo hace respirar; aquí solo lo
  // ALIMENTAMOS: setUserLevel desde el micrófono (_setMicLevel) y setBixbyLevel
  // mientras Khipu reproduce audio (_startOrbDrive). En reposo, el orbe respira.
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
    if (typeof requestAnimationFrame !== 'function') return;
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
    if (this._orbRAF) { try { cancelAnimationFrame(this._orbRAF); } catch (e) {} this._orbRAF = 0; }
  },

  _sendInitContext(override) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    // dynamic_variables NO: el agente cierra si su prompt no tiene esos {{placeholders}}.
    const msg = { type: 'conversation_initiation_client_data' };
    if (override) msg.conversation_config_override = override;
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
        current_price: _voicePx(q),
        nrs: typeof computeNRS === 'function' ? computeNRS(id) : null,
      };
    });

    // Category breakdown
    const cats = {};
    if (typeof NODES !== 'undefined') NODES.forEach(n => { cats[n.cat] = (cats[n.cat] || 0) + 1; });

    return {
      app: 'Khipu Finance', assistant: 'Khipu',
      active_tab: (typeof activeTab !== 'undefined') ? activeTab : null,
      language: _voiceLang(),
      total_nodes: (typeof NODES !== 'undefined') ? NODES.length : 0,
      total_links: (typeof LINKS !== 'undefined') ? LINKS.length : 0,
      categories: cats,
      selected_company: sel ? (function () {
        const m = (window.NODE_META || {})[sel.id] || {};
        const sq = (sel.mkt && typeof MKT !== 'undefined') ? MKT.quotes[sel.mkt] : null;
        return {
          id: sel.id, label: sel.label, ticker: sel.mkt || null,
          category: typeof catLabel === 'function' ? catLabel(sel.cat) : sel.cat,
          nrs: typeof computeNRS === 'function' ? computeNRS(sel.id) : null,
          price: _voicePx(sq),
          role: sel.role || null,
          // la ficha completa: Khipu debe saber lo que la pantalla muestra
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
    if (!msg || typeof msg !== 'object') return;
    switch (msg.type) {
      case 'conversation_initiation_metadata': {
        // Sesión confirmada — AHORA sí se puede mandar audio, y sabemos los formatos
        const m = msg.conversation_initiation_metadata_event || {};
        this._metaReceived = true;
        clearTimeout(this._initTimer);
        this._conversationId = m.conversation_id || null;
        this._outFmt = VoiceAudio.parseFormat(m.agent_output_audio_format || 'pcm_16000');
        this._inFmt = VoiceAudio.parseFormat(m.user_input_audio_format || 'pcm_16000');
        this._showOverlay(_voiceL('🎙️ Khipu te escucha — habla', '🎙️ Khipu is listening — speak'), 'listen');
        if (this._preStream) {
          this._startMicWithStream(this._preStream);
          this._preStream = null;
        }
        this._orbOn();   // arranca/alimenta el orbe de voz de la Cabina
        break;
      }
      case 'audio': {
        const ev = msg.audio_event || {};
        // audio de una respuesta YA interrumpida: se descarta (si no, seguía sonando)
        if (ev.event_id != null && +ev.event_id < this._lastInterruptId) break;
        const chunk = ev.audio_base_64;
        if (chunk) {
          // suena la voz del agente → "Hablando" (una vez por respuesta; al terminar vuelve a "Escuchando")
          if (this.state !== 'speaking') this._setState('speak');
          else if (window.setBixbyThinking) window.setBixbyThinking(false);
          this._enqueueAudio(chunk);
        }
        break;
      }
      case 'agent_response': {
        const text = msg.agent_response_event?.agent_response || '';
        if (text) {
          // El usuario NUNCA debe ver los tokens internos ([XRAY:...], [NAV:...])
          const clean = this._cleanSpeech(text);
          if (clean) this._showOverlay('Khipu: ' + clean.slice(0, 80), 'speak');
          this._onAgentResponse(text);
        }
        break;
      }
      case 'agent_response_correction': {
        // la respuesta se cortó (interrupción): mostrar lo que REALMENTE dijo
        const c = msg.agent_response_correction_event || {};
        const clean = this._cleanSpeech(c.corrected_agent_response || '');
        if (clean) this._showOverlay('Khipu: ' + clean.slice(0, 80), 'speak');
        break;
      }
      case 'user_transcript': {
        const t = msg.user_transcription_event?.user_transcript || '';
        if (t) this._showOverlay(_voiceL('Tú: ', 'You: ') + t.slice(0, 80), 'think');   // 'think' ya enciende setBixbyThinking
        break;
      }
      case 'client_tool_call':
        this._handleToolCall(msg.client_tool_call);
        break;
      case 'interruption': {
        const id = +((msg.interruption_event || {}).event_id || 0);
        if (id > this._lastInterruptId) this._lastInterruptId = id;
        this._stopScheduled();
        this._setState('listen');
        break;
      }
      case 'ping': {
        const id = msg.ping_event ? msg.ping_event.event_id : null;
        if (id != null && this.ws?.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({ type: 'pong', event_id: id }));
        }
        break;
      }
      case 'agent_tool_response': {
        // herramienta de sistema end_call: el agente cuelga → dejar terminar la frase y cerrar
        const tr = msg.agent_tool_response || {};
        if (tr.tool_name === 'end_call') this._endAfterSpeech();
        break;
      }
      case 'error': {
        const ev = msg.error_event || {};
        this._lastErrorEvent = ev;
        try { console.warn('[Khipu voz] ElevenLabs error:', ev.error_type, ev.message || ev.reason || ''); } catch (e) {}
        if (ev.error_type === 'max_duration_exceeded') this._setStatus(this._closeText({}, true, ev), true, 'error');
        break;
      }
      default:
        break;   // vad_score, context_usage, internal_*… no se usan
    }
  },

  // end_call: cerrar cuando termine de sonar lo agendado (máx 8 s)
  _endAfterSpeech() {
    const ctx = this.audioCtx;
    const left = (ctx && this._playCursor) ? Math.max(0, this._playCursor - ctx.currentTime) : 0;
    clearTimeout(this._endTimer);
    this._endTimer = setTimeout(() => { if (this.isConnected) this.disconnect(); }, Math.min(8000, left * 1000 + 400));
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
    if (ctx.state !== 'running' && ctx.state !== 'closed') { try { ctx.resume(); } catch {} }   // 'interrupted' en iOS
    const fmt = this._outFmt || VoiceAudio.parseFormat('pcm_16000');
    let buffer;
    try {
      const f32 = VoiceAudio.decode(b64chunk, fmt);
      if (!f32.length) return;
      let _sum = 0;
      for (let i = 0; i < f32.length; i++) _sum += f32[i] * f32[i];
      // energía de la voz de Khipu (violeta) para el orbe — la lee _startOrbDrive
      this._speakLevel = Math.max(0.35, Math.min(1, Math.sqrt(_sum / (f32.length || 1)) * 5));
      try {
        // la tasa REAL del agente (agent_output_audio_format); el navegador re-muestrea
        buffer = ctx.createBuffer(1, f32.length, fmt.sampleRate);
        buffer.getChannelData(0).set(f32);
      } catch (e) {
        // Safari viejo no crea buffers < 22,05 kHz: subimos la tasa nosotros
        const up = VoiceAudio.resampleOnce(f32, fmt.sampleRate, ctx.sampleRate);
        buffer = ctx.createBuffer(1, up.length, ctx.sampleRate);
        buffer.getChannelData(0).set(up);
      }
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
      if (!this._activeSources.length) {
        this.isPlaying = false; this._playCursor = 0;
        if (this.isConnected) this._setState('listen');
      }
    };
  },

  // Corta TODO el audio agendado (para interrupciones y desconexión).
  _stopScheduled() {
    (this._activeSources || []).forEach(s => { try { s.onended = null; s.stop(); } catch {} });
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
  // Khipu los emite para actuar, pero el usuario jamás debe verlos ni oírlos.
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

  // Respuesta bilingüe de "no encontrado" CON sugerencias, para que Khipu
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
    let params = {};
    try { params = typeof parameters === 'string' ? JSON.parse(parameters || '{}') : (parameters || {}); }
    catch (e) { params = {}; }
    // UNA sola respuesta por llamada, SIEMPRE antes del tope del agente: si la
    // acción tarda más, se responde "sigue en pantalla" (antes ElevenLabs veía
    // un timeout y Khipu se quedaba mudo o decía que había fallado).
    let answered = false;
    let guard = null;
    const respond = (result) => {
      if (answered) return;
      answered = true;
      clearTimeout(guard);
      if (this.ws?.readyState === WebSocket.OPEN) {
        let txt;
        try { txt = typeof result === 'string' ? result : JSON.stringify(result == null ? { success: true } : result); }
        catch (e) { txt = '{"success":false}'; }
        this.ws.send(JSON.stringify({
          type: 'client_tool_result',
          tool_call_id,
          result: txt,          // el API exige STRING
          is_error: false,      // los errores van en el texto: con is_error el agente no los ve
        }));
      }
    };
    const limitS = VOICE_TOOL_TIMEOUT_S[tool_name] || VOICE_TOOL_TIMEOUT_DEFAULT_S;
    guard = setTimeout(() => respond(tool_name === 'place_paper_trade'
      ? { success: false, pending: true, error: _voiceL(
        'La orden sigue en proceso: mírala en pantalla antes de repetirla (repetirla no la duplica).',
        'The order is still in progress: check the screen before repeating it (repeating will not duplicate it).') }
      : { success: true, pending: true, note: _voiceL(
        'Sigue procesándose; el resultado aparecerá en pantalla en unos segundos.',
        'Still processing; the result will appear on screen in a few seconds.') }),
    Math.max(2500, limitS * 1000 - 1500));
    try {
      this._dispatchTool(tool_name, params, respond);
    } catch (e) {
      respond({ success: false, error: _voiceL('No pude completar esa acción: ', "I couldn't complete that action: ") + ((e && e.message) || e) });
    }
  },

  _dispatchTool(tool_name, params, respond) {
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
          // LATENCIA (feedback Fabrizio): responder YA para que Khipu hable sin
          // esperar la cascada; el conteo real se manda luego por contextual_update.
          respond({ success: true, company: n.label,
            note: 'Ejecutando el estrés en el mapa; los efectos aparecen en pantalla.' });
          this._defer(() => {
            try { this._show('stress', n.id); } catch {}
            setTimeout(() => {
              try {
                const cascade = (typeof stressAffected !== 'undefined') ? stressAffected.size : 0;
                if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                  this.ws.send(JSON.stringify({ type: 'contextual_update',
                    text: `[STRESS] ${n.label}: ${cascade} empresas afectadas (${Math.round(cascade / NODES.length * 100)}%).` }));
                }
              } catch (e) {}
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
        // TODO lo que la app sabe de la empresa — Khipu nunca debe decir
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
            price: _voicePx(q),
            change_pct: (_voicePx(q) && q?.prev) ? ((_voicePx(q) - q.prev) / q.prev * 100).toFixed(2) : null,
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
        const validTabs = ['map', 'market', 'analysis', 'geo', 'simulation', 'space', 'terminal', 'canvas', 'tkg', 'guia', 'crypto'];
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
      // ── Trading Khipu (Etapa M): orden por voz con confirmación explícita ──
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
      case 'ask_khipu_brain': {
        // El MISMO cerebro con herramientas del chat (POST /api/khipu/chat):
        // consulta datos reales de la app y devuelve una respuesta con fuentes.
        const q = String((params && (params.question || params.query)) || '').trim();
        if (!q || !window.KhipuChat || !window.KhipuChat.send) {
          respond({ success: false, error: 'brain unavailable' });
          break;
        }
        window.KhipuChat.send(q, { timeout: 55000 }).then(d => {
          // abre en pantalla la primera acción útil (X-Ray, mapa…) sin tapar la voz
          try { const a = (d.actions || [])[0]; if (a && window.KhipuChat.runAction) window.KhipuChat.runAction(a); } catch (e) {}
          respond({
            success: true,
            answer: String(d.answer || '').replace(/\*\*/g, '').slice(0, 2500),
            sources: (d.sources || []).slice(0, 5),
            consulted: (d.tools_used || []).map(t => t.name).slice(0, 6),
          });
        }).catch(e => respond({ success: false, error: 'brain error: ' + ((e && e.message) || e) }));
        break;
      }
      case 'get_space_summary': {
        this._toolSpaceSummary(params)
          .then(respond)
          .catch(e => respond({ success: false, error: 'space tool error: ' + ((e && e.message) || e) }));
        break;
      }
      case 'get_market_summary': {
        const quotes = Object.entries((typeof MKT !== 'undefined' ? MKT.quotes : {}) || {})
          .filter(([, q]) => _voicePx(q))
          .map(([t, q]) => ({
            ticker: t,
            price: _voicePx(q),
            change_pct: (_voicePx(q) && q.prev) ? ((_voicePx(q) - q.prev) / q.prev * 100).toFixed(2) : null,
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
      case 'run_guided_demo': {
        // La demostración se narra SOLA en pantalla (y con voz del navegador si
        // no hay voz premium hablando) → Khipu responde corto y se calla.
        respond({ success: true,
          note: 'Demostración guiada en marcha; se narra sola en pantalla. Di UNA frase corta y quédate en silencio.' });
        this._defer(() => { try { if (window.BixbyCockpit) window.BixbyCockpit.demo(); } catch (e) {} });
        break;
      }
      case 'show_insights': case 'show_matrices': {
        // Khipu NARRA lo que ve el hipergrafo: corre la simulación en vivo
        // (factores activos + cascada) y responde con un resumen hablado,
        // además de abrir el panel. Guarda de tiempo → nunca cuelga a ElevenLabs.
        let answered = false;
        const done = (r) => { if (!answered) { answered = true; respond(r); } };
        this._defer(() => this._show('insights'));
        const guard = setTimeout(() => done({ success: true,
          note: 'Abriendo los insights del hipergrafo en pantalla.' }), 2600);
        try {
          fetch('/api/matrix/insights', { method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tier: 'fast' }) })
            .then(r => r.json())
            .then(d => {
              clearTimeout(guard);
              if (!d || d.available === false) return done({ success: true, note: 'Insights en pantalla.' });
              done({ success: true,
                active_factors: (d.factors || []).map(f => f.label),
                top_insights: (d.insights || []).slice(0, 3).map(i => ({ title: i.title, detail: i.detail, kind: i.kind })),
                cascade_trigger: d.trigger || null,
                most_affected: (d.cascade || []).slice(0, 3).map(c => ({ name: c.name, impact: c.impact })),
                nodes_reached: d.affected || 0,
                note: 'Narra estos insights del hipergrafo en 2-3 frases, nombrando empresas; recuerda que es análisis, no asesoría.' });
            })
            .catch(() => { clearTimeout(guard); done({ success: true, note: 'Insights en pantalla.' }); });
        } catch (e) { clearTimeout(guard); done({ success: true }); }
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
        // en el escenario de la Cabina (tarda 30-90s; Khipu avisa y espera)
        const q = (params.question || '').trim();
        if (!q) { respond({ success: false, error: 'question required' }); break; }
        respond({ success: true, started: true, eta_seconds: 60 });
        this._defer(() => this._show('deep', q));
        break;
      }
      // ── Simulación POR AGENTES (motor interno, desde la terminal de Khipu) ──
      // Corre en el servidor (varios agentes debaten) y se MUESTRA en la Cabina.
      // Khipu narra el consenso y los mayores impactos.
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

  // ── Trading Khipu (Etapa M) ────────────────────────────────────────────────
  // place_paper_trade: resuelve el activo (cripto primero, luego equity vía
  // KhipuResolve) y SOLO envía la orden cuando confirmed===true. Sin confirmar
  // devuelve needs_confirmation con un resumen hablable (ES/EN) para que Khipu
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
    // sin PIN guardado la cuenta no carga: el modo sale de /api/trade/status
    // (público) → el resumen hablado SIEMPRE dice papel o DINERO REAL
    if (paper === null && window._tradeStatusInfo) {
      try {
        const s = await window._tradeStatusInfo();
        if (s && typeof s.paper === 'boolean') paper = s.paper;
      } catch (e) {}
    }

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
      if (r.broker_dup) {
        return { success: true, already_sent: true, symbol: res.symbol, paper, summary: en
          ? 'That order had already reached the broker — I did not send it twice. If you want ANOTHER identical order, ask me again.'
          : 'Esa orden ya había llegado al bróker — no la envié dos veces. Si quieres OTRA orden igual, pídemela de nuevo.' };
      }
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
    // concentración por sector (reusa el cálculo de la Cabina) → nota cauta hablada
    let concEn = '', concEs = '';
    try {
      if (window._computePortfolioSummary && positions.length) {
        const pm = window._computePortfolioSummary(acct, positions);
        const top = (pm.sectors && pm.sectors[0]) || null;
        if (top && top.pct >= 40) {
          concEn = ` Heads up: about ${Math.round(top.pct)}% is concentrated in ${top.sector} — some diversification would lower risk. Not financial advice.`;
          concEs = ` Ojo: cerca del ${Math.round(top.pct)}% está concentrado en ${top.sector} — algo de diversificación reduciría el riesgo. No es asesoría financiera.`;
        }
      }
    } catch (e) {}
    let summary;
    if (en) {
      summary = `${mode}. Equity ${fmt(equity)}, cash ${fmt(cash)}, buying power ${fmt(bp)}. `
        + (positions.length ? `${positions.length} open position${positions.length > 1 ? 's' : ''}.` : 'No open positions.');
      if (best && positions.length > 1 && best !== worst) summary += ` Best: ${best.symbol} ${pct(best.unrealized_pct)}. Worst: ${worst.symbol} ${pct(worst.unrealized_pct)}.`;
      else if (best) summary += ` ${best.symbol}: ${pct(best.unrealized_pct)}.`;
      summary += concEn + ' It is on screen.';
    } else {
      summary = `${mode}. Valor total ${fmt(equity)}, efectivo ${fmt(cash)}, poder de compra ${fmt(bp)}. `
        + (positions.length ? `Tienes ${positions.length} ${positions.length === 1 ? 'posición abierta' : 'posiciones abiertas'}.` : 'No tienes posiciones abiertas.');
      if (best && positions.length > 1 && best !== worst) summary += ` La mejor: ${best.symbol} ${pct(best.unrealized_pct)}. La peor: ${worst.symbol} ${pct(worst.unrealized_pct)}.`;
      else if (best) summary += ` ${best.symbol}: ${pct(best.unrealized_pct)}.`;
      summary += concEs + ' La tienes en pantalla.';
    }
    return {
      success: true, paper, equity, cash, buying_power: bp, positions_count: positions.length,
      best: best ? { symbol: best.symbol, pnl_pct: +(+best.unrealized_pct || 0).toFixed(2) } : null,
      worst: worst ? { symbol: worst.symbol, pnl_pct: +(+worst.unrealized_pct || 0).toFixed(2) } : null,
      summary,
    };
  },

  // get_space_summary: satélites REALES por constelación (CelesTrak) + próximo
  // lanzamiento. Arregla "no sé cuántos satélites tiene Starlink" — el dato SÍ
  // existía (/api/space/tle) pero Khipu no tenía tool para leerlo. NO navega
  // (abrir la pestaña 'space' cerraría la Cabina y cortaría la voz).
  async _toolSpaceSummary(params) {
    params = params || {};
    const en = (((typeof LANG !== 'undefined') ? LANG : (localStorage.getItem('eco_lang') || 'es')) === 'en');
    const base = window.BASE || '';
    let tle = null, lch = null;
    try {
      const rs = await Promise.all([
        fetch(base + '/api/space/tle').then(r => r.json()).catch(() => null),
        fetch(base + '/api/space/launches').then(r => r.json()).catch(() => null),
      ]);
      tle = rs[0]; lch = rs[1];
    } catch (e) {
      return { success: false, error: en ? 'Could not load space data.' : 'No pude cargar los datos de espacio.' };
    }
    const cons = (tle && Array.isArray(tle.constellations) ? tle.constellations : []).filter(function (c) { return (c.count || 0) > 0; });
    if (!cons.length) return { success: false, error: en ? 'No satellite data right now.' : 'Sin datos de satélites ahora mismo.' };
    const total = (tle && tle.total_real) || cons.reduce(function (s, c) { return s + (c.count || 0); }, 0);
    const nf = function (n) { return Number(n || 0).toLocaleString(en ? 'en-US' : 'es-ES'); };
    // ¿preguntó por una constelación/operador concreto?
    const q = String(params.query || params.constellation || params.operator || '').toLowerCase().trim();
    let focus = null;
    if (q) {
      focus = cons.find(function (c) {
        const nm = (c.name || '').toLowerCase(), nd = (c.node || '').toLowerCase();
        return nm.indexOf(q) >= 0 || nd.indexOf(q) >= 0 ||
          (/star|spacex/.test(q) && /starlink/.test(nm)) || (/oneweb|eutel/.test(q) && /oneweb/.test(nm)) ||
          (/planet/.test(q) && /planet/.test(nm)) || (/iridium/.test(q) && /iridium/.test(nm)) || (/gps|navstar/.test(q) && /gps/.test(nm));
      });
    }
    const list = cons.map(function (c) { return { name: c.name, count: c.count }; });
    let summary;
    if (focus) {
      summary = en
        ? `${focus.name} has about ${nf(focus.count)} satellites tracked in orbit right now (source CelesTrak).`
        : `${focus.name} tiene alrededor de ${nf(focus.count)} satélites rastreados en órbita ahora mismo (fuente CelesTrak).`;
    } else {
      const top = list.slice(0, 5).map(function (c) { return `${c.name} ${nf(c.count)}`; }).join(' · ');
      summary = en
        ? `About ${nf(total)} tracked satellites across ${list.length} constellations. ${top}.`
        : `Cerca de ${nf(total)} satélites rastreados en ${list.length} constelaciones. ${top}.`;
    }
    // /api/space/launches devuelve un ARRAY (no {launches:[...]})
    const nextL = Array.isArray(lch) ? lch[0] : ((lch && Array.isArray(lch.launches)) ? lch.launches[0] : null);
    if (nextL && nextL.name) summary += en ? ` Next launch: ${nextL.name}.` : ` Próximo lanzamiento: ${nextL.name}.`;
    return {
      success: true, total_satellites: total, constellations: list,
      focus: focus ? { name: focus.name, count: focus.count } : null,
      next_launch: nextL ? nextL.name : null, source: (tle && tle.source) || 'celestrak', summary,
    };
  },

  // Ejecuta una acción visual pesada FUERA del hilo crítico del WebSocket, para
  // no bloquear el procesamiento/agendado del audio mientras Khipu habla.
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

  // ── Estado visible (overlay, badge, Cabina) — bilingüe y con estado EXPLÍCITO ──
  // state ∈ connect | listen | speak | think | error. Antes se adivinaba por
  // palabras del texto en español ("escucha", "conectando"…) y en inglés no andaba.
  _STATE_LABELS: {
    connect: ['CONECTANDO', 'CONNECTING', 'Conectando', 'Connecting'],
    listen: ['ESCUCHANDO', 'LISTENING', 'Escuchando', 'Listening'],
    speak: ['HABLANDO', 'SPEAKING', 'Hablando', 'Speaking'],
    think: ['PENSANDO', 'THINKING', 'Pensando', 'Thinking'],
    error: ['ERROR', 'ERROR', 'Error', 'Error'],
  },
  _guessState(text, isError) {
    if (isError) return 'error';
    const lo = String(text || '').toLowerCase();
    if (lo.includes('escucha') || lo.includes('listening') || lo.includes('habla')) return 'listen';
    if (lo.includes('conectando') || lo.includes('connecting') || lo.includes('iniciando') || lo.includes('starting')) return 'connect';
    if (lo.includes('khipu:') || lo.includes('bixby:')) return 'speak';
    if (lo.includes('tú:') || lo.includes('you:') || lo.includes('pensando') || lo.includes('thinking')) return 'think';
    return null;
  },
  // estado interno → estado PÚBLICO (getState / evento 'khipu:voice')
  _PUBLIC_STATE: { connect: 'connecting', listen: 'listening', speak: 'speaking', think: 'thinking', error: 'error' },
  _setState(state, text) {
    const lab = this._STATE_LABELS[state];
    if (!lab) return;
    const en = _voiceLang() === 'en';
    // setBixbyThinking (app.html) escribe "PENSANDO" fijo en la insignia: va ANTES para que la
    // etiqueta bilingüe de abajo sea la que quede (en inglés se veía "PENSANDO")
    if (window.setBixbyThinking) { try { window.setBixbyThinking(state === 'think'); } catch (e) {} }
    this._setBadge(en ? lab[1] : lab[0], state !== 'connect' && state !== 'error');
    if (window.BixbyCockpit && window.BixbyCockpit.setState) {
      const mode = state === 'think' ? 'think' : (state === 'listen' || state === 'speak') ? 'live' : '';
      try { window.BixbyCockpit.setState(mode, en ? lab[3] : lab[2]); } catch (e) {}
    }
    this._emitVoice(this._PUBLIC_STATE[state], text);
  },

  _showOverlay(text, state) {
    const el = document.getElementById('bixby-status');
    if (el) el.style.display = 'block';
    this._setStatus(text, false, state);
    const btn = document.getElementById('bixby-btn');
    if (btn) btn.classList.add('bixby-active');
  },
  _hideOverlay() {
    clearTimeout(this._hideTimer);
    const el = document.getElementById('bixby-status');
    if (el) el.style.display = 'none';
    const btn = document.getElementById('bixby-btn');
    if (btn) btn.classList.remove('bixby-active');
    this._setBadge('OFF', false);
    if (window.BixbyCockpit && window.BixbyCockpit.setState) {
      try { window.BixbyCockpit.setState('', _voiceL('Listo', 'Ready')); } catch (e) {}
    }
    this._emitVoice('off');
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
  _setStatus(text, isError, state) {
    const t = document.getElementById('bixby-text');
    if (t) t.textContent = text;
    const st = state || this._guessState(text, isError);
    if (st) this._setState(st, text);
    if (isError) {
      const el = document.getElementById('bixby-status');
      if (el) el.style.display = 'block';
      if (typeof toast === 'function') { try { toast(text); } catch (e) {} }
    }
  },

  // Falla visible y LIMPIA: suelta el micrófono, apaga el orbe y deja el mensaje
  // (antes un fallo antes de abrir el socket dejaba el micrófono encendido y
  // "Khipu — conectando…" para siempre).
  _fail(text) {
    clearTimeout(this._initTimer);
    this.isConnected = false;
    this._metaReceived = false;
    this._releasePre();
    this._stopMic();
    this._stopScheduled();
    this._orbOff();
    this._setStatus(text, true, 'error');
    const btn = document.getElementById('bixby-btn');
    if (btn) btn.classList.remove('bixby-active');
    clearTimeout(this._hideTimer);
    this._hideTimer = setTimeout(() => {
      if (!this.isConnected && !this.isConnecting()) {
        const el = document.getElementById('bixby-status');
        if (el) el.style.display = 'none';
        this._setBadge('OFF', false);
        if (this.state === 'error') this._emitVoice('off');   // el aviso de error se apaga solo (12 s)
      }
    }, 12000);
  },
};

window.BixbyVoice = BixbyVoice;
window.KhipuVoiceAudio = VoiceAudio;   // expuesto para pruebas/diagnóstico (sin estado)

// Safari/Chrome móvil suspenden el audio al ocultar la pestaña: al volver, reanudar.
if (typeof document !== 'undefined' && document.addEventListener) {
  document.addEventListener('visibilitychange', () => {
    try {
      const ctx = BixbyVoice.audioCtx;
      if (!document.hidden && BixbyVoice.isConnected && ctx && ctx.state !== 'running') ctx.resume();
    } catch (e) {}
  });
}

/* ============================================================================
   TRADING COMPARTIDO (Etapa M) — helpers usados por voice.js (tools de Khipu),
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
      if (!r.ok) return { error: window._tradeErrText ? window._tradeErrText(d, r.status) : ((d && d.error) || ('HTTP ' + r.status)), status: r.status, code: d && d.code };
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
    // AVISOS pop-up (engine/toast.js): enviando → enviada/rechazada → ejecutada.
    // Solo informan: no cambian qué se envía ni cuándo.
    var KT = window.KhipuToast;
    var info = { side: side, symbol: body.symbol, label: o.label || body.symbol, kind: o.kind,
      notional: body.notional != null ? body.notional : undefined, qty: body.qty != null ? body.qty : undefined };
    var last = window.__lastTradeExec;
    if (last && last.key === key && (Date.now() - last.ts) < 90000) {
      if (KT) KT.order.result(info, { ok: true, dedup: true, data: last.data });
      return { ok: true, dedup: true, data: last.data };
    }
    // La MISMA orden ya en vuelo (sí verbal + clic en la Cabina a la vez) →
    // se espera a esa, no se manda otra.
    var inflight = window.__tradeInflight || (window.__tradeInflight = {});
    if (inflight[key]) {
      return inflight[key].then(function (res) { return res && res.ok ? { ok: true, dedup: true, data: res.data } : res; });
    }
    // client_order_id estable por orden (window._tradeOrderId, app.html): si la
    // respuesta se pierde (red/timeout/5xx) y se reintenta la misma orden,
    // Alpaca rechaza el duplicado en vez de ejecutarla dos veces.
    var sig = 'khipu|' + key;
    if (window._tradeOrderId) body.client_order_id = window._tradeOrderId(sig);
    info.client_order_id = body.client_order_id;
    var settle = function (ambiguous) { if (window._tradeOrderSettle) window._tradeOrderSettle(sig, ambiguous); };
    var tid = KT ? KT.order.sending(info) : null;
    var p = (async function () {
      try {
        var r = await window._tradeFetch('/api/trade/order', {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), timeout: 30000,
        }, true);
        var d = await r.json().catch(function () { return null; });
        // PRIMERO el duplicado: el server responde 200 + duplicate:true con la
        // orden que YA existía (mismo client_order_id) — NO es una orden nueva
        // y no se puede anunciar como "orden enviada".
        var isDup = window._tradeOrderIsDup ? window._tradeOrderIsDup(r.status, d)
          : !!(r.ok && d && d.duplicate === true);
        if (isDup) {
          settle(false);
          window.__tradeAcctCache = null;
          return { ok: true, dedup: true, broker_dup: true, data: d || {} };
        }
        if (r.ok && d && (d.id || d.status)) {
          settle(false);
          window.__lastTradeExec = { key: key, ts: Date.now(), data: d };
          window.__tradeAcctCache = null;   // la cuenta cambió — invalidar caché
          return { ok: true, data: d };
        }
        var amb = window._tradeOrderAmbiguous ? window._tradeOrderAmbiguous(r.status) : r.status >= 500;
        settle(amb);
        var msg = window._tradeErrText ? window._tradeErrText(d, r.status) : ((d && (d.error || d.message)) || ('HTTP ' + r.status));
        if (amb) {
          msg = (en ? 'The order could not be confirmed (' : 'No se pudo confirmar la orden (') + msg + ').' + (en
            ? ' It MAY have reached the broker: check your orders before retrying — retrying this same order will not duplicate it.'
            : ' Puede que SÍ haya llegado al bróker: revisa tus órdenes antes de reintentar — reintentar esta misma orden no la duplica.');
        }
        return { ok: false, status: r.status, ambiguous: amb, error: msg };
      } catch (e) {
        settle(true);   // sin respuesta: pudo haber llegado
        return { ok: false, ambiguous: true, error: en
          ? 'No response from the server (network or timeout). The order MAY have reached the broker: check your orders before retrying — retrying this same order will not duplicate it.'
          : 'Sin respuesta del servidor (red o tiempo agotado). Puede que la orden SÍ haya llegado al bróker: revisa tus órdenes antes de reintentar — reintentar esta misma orden no la duplica.' };
      } finally {
        delete inflight[key];
      }
    })();
    inflight[key] = p;
    if (KT) p.then(function (res) {
      try { KT.order.result(info, res, tid); } catch (e) {}
    });
    return p;
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
