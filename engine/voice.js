// engine/voice.js — Khipu, el asistente de voz de Khipu Finance
// Cliente WebSocket de ElevenLabs Agents (Conversational AI). Khipu es el "Jarvis de las
// finanzas": escucha por micrófono, responde por voz, y puede controlar la terminal.
//
// Depende de app.html: BASE, NODES, NODE_BY_ID, LINKS, MKT, computeNRS(+Breakdown), NRS_FLOW_TYPES,
//   quotePx, toast, LANG — y de Khipus OS: BixbyCockpit (chatVoice, stage, screens/openScreen, title),
//   KhipuDesk, KhipuOSWin, KhipuChat. Contrato de herramientas: el bloque «CONTRATO DE VOZ v2» de abajo.
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
// server.py (un test los compara; contrato de voz v2, 2026-10-11). Respondemos SIEMPRE ~1.5 s antes
// para que ElevenLabs nunca vea un timeout (el agente quedaba mudo o decía "falló").
const VOICE_TOOL_TIMEOUT_S = { ask_khipu_brain: 60, open_company: 15, get_company_info: 15, run_agent_simulation: 90,
  quick_thesis: 90, show_opportunities: 15, place_order: 45, get_account_status: 45, get_space_summary: 20,
  run_guided_demo: 30 };
// cuánto vale el resumen leído de una orden para el sí verbal (place_order confirmed=true)
const VOICE_ORDER_PREVIEW_MS = 3 * 60 * 1000;
// recorrido narrado: hueco entre trozos de audio que NO cuenta como fin de la frase, y espera máxima cuando
// el `next` llega antes que el audio de la frase
const TOUR_AUDIO_GAP_MS = 700, TOUR_NO_AUDIO_MS = 4000;
// el botón «Ver el recorrido de un minuto» con la voz REAL de Khipu (2026-10-12): sesión de SOLO ESCUCHAR (sin
// micrófono). Si el agente no empieza el recorrido (run_guided_demo start) a los 9 s de abrir el socket —o a los
// 20 s del clic, si el socket ni abre— va el recorrido local (clips → texto). SIN user_activity: ElevenLabs no deja
// hablar al agente ~2 s tras cada uno (pausas en la narración); durante el recorrido el turno es del agente (encadena
// herramientas) y el vigía de abajo cuelga una sesión trabada.
const NARRATE_START_MS = 9000, NARRATE_TOTAL_MS = 20000;
// vigía: sin herramienta ni audio del agente durante 35 s (tras sonar lo último) → cuelga, el recorrido sigue solo
// (más que el ~25 s que un `next` espera a que termine la frase); 1,5 s para que el AudioContext suene
const NARRATE_STALL_MS = 35000, NARRATE_AUDIO_CHECK_MS = 1500;
// LA APP MARCA EL RITMO del recorrido narrado (2026-10-12 b): el LLM del agente dice la frase de `start` y termina su
// turno SIN llamar `next` (transcripción real: se quedaba en el paso 1). Cuando la frase del paso k terminó de SONAR
// (llegó audio después de entregarla, lo agendado ya sonó —margen 0,15 s— y no llega audio hace TOUR_DRIVE_QUIET_MS)
// y no hay ningún run_guided_demo en curso, se espera TOUR_DRIVE_GAP_MS, la pantalla pasa al paso k+1 y se le manda
// al agente `[TOUR k+1/N] <frase>` (user_message). Sin audio a los TOUR_LINE_WAIT_MS → se reenvía UNA vez; otra vez
// nada → solo escuchar: cuelga y sigue el recorrido local; con micrófono: pausa. TOUR_SELF_INTERRUPT_MS: una
// `interruption` justo después de nuestro mensaje la provocó él, no el usuario (no pausa).
const TOUR_DRIVE_GAP_MS = 600, TOUR_DRIVE_QUIET_MS = 600, TOUR_LINE_WAIT_MS = 8000, TOUR_DRIVE_TICK_MS = 150,
  TOUR_SELF_INTERRUPT_MS = 1500;
// un "¡Claro!" dicho junto con el start puede llegar DESPUÉS del resultado: hasta que sonó al menos una parte de la
// frase (TOUR_LINE_MIN_FRAC de lo que dura a TOUR_SPEECH_CPS letras por segundo, tope TOUR_LINE_MIN_CAP_S) no cuenta
// como dicha, salvo que pase TOUR_SHORT_GRACE_MS en silencio (nunca se traba: una frase de verdad corta igual sigue)
const TOUR_SPEECH_CPS = 15, TOUR_LINE_MIN_FRAC = 0.35, TOUR_LINE_MIN_CAP_S = 2, TOUR_SHORT_GRACE_MS = 2500;
const TOUR_TAG_RE = /^\s*\[TOUR \d+\/\d+\]/;
const VOICE_TOOL_TIMEOUT_DEFAULT_S = 10;
// Nombres RETIRADOS (alias): el tope con el que un agente aún sin re-sincronizar los tiene registrados
// (los que no figuran usaban 10 s). Solo para responder a tiempo durante un despliegue; no se declaran.
const VOICE_ALIAS_TIMEOUT_S = { deep_research: 90, get_news: 20, show_insights: 15, place_paper_trade: 45, get_portfolio_status: 45 };

// Intensidad de una simulación en vivo (1..100 %; 0, vacía o inválida = 100 = caída total) — la MISMA
// regla que engine/cockpit.js (_simSev): la voz y la ventana muestran la misma intensidad.
function _voiceSimSev(v) {
  v = Math.round(+v);
  if (!isFinite(v) || v <= 0) return 100;
  return Math.max(1, Math.min(100, v));
}

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
             connected: !!this.isConnected, connecting: this.isConnecting(), listenOnly: !!this._listenOnly };
  },
  // ¿la sesión de voz abierta (o conectándose) es la del recorrido, de SOLO ESCUCHAR (sin micrófono)?
  isListenOnly() { return !!this._listenOnly; },
  // ¿la voz de Khipu está contratada? (/api/health). En app.html `Keys` vive DENTRO del IIFE de v8 y solo se
  // expone como window.V8.Keys (un `Keys` global no existe: leerlo así dejaba el botón con los clips viejos).
  isConfigured() {
    try {
      const W = (typeof window !== 'undefined') ? window : null;
      const K = (W && W.V8 && W.V8.Keys) || ((typeof Keys !== 'undefined') ? Keys : null);
      if (K && typeof K.has === 'function') return !!K.has('elevenlabs');
    } catch (e) {}
    return false;
  },
  // ¿el botón del recorrido está esperando a que el agente lo empiece? (la sesión que solo termina su frase, no)
  narrationPending() { return !!(this._narr && !this._narr.done && !this._narr.started); },

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
          state, prev, text: this.stateText, error: state === 'error' ? this.stateText : '', listenOnly: !!this._listenOnly } }));
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
    // sesión del recorrido (solo escuchar): tocar el micrófono = HABLARLE (se suma el micrófono), no colgar
    if (this._listenOnly && (this.isConnected || this.isConnecting())) return this.upgradeToMic();
    (this.isConnected || this.isConnecting()) ? this.disconnect() : await this.connect();
  },

  stop() { this.disconnect(); },

  async connect(opts) {
    opts = opts || {};
    // pedir la conversación normal con la sesión del recorrido abierta → se le suma el micrófono (mismo socket)
    if (!opts.listenOnly && this._listenOnly && (this.isConnected || this.isConnecting())) return this.upgradeToMic();
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

    // el recorrido de un minuto con la voz de Khipu: SOLO ESCUCHAR → ni micrófono ni su permiso (sin eco)
    this._listenOnly = !!opts.listenOnly;
    let stream = null;
    if (this._listenOnly) {
      this._showOverlay(_voiceL('Conectando con la voz de Khipu…', "Connecting to Khipu's voice…"), 'connect');
      return this._connectSession(opts, sess, null);
    }

    // reintento de la sesión del recorrido a la que el usuario le sumó el micrófono: el del clic ya está abierto
    if (opts.keepPre && this._preStream) return this._connectSession(opts, sess, this._preStream);

    // ── Paso 2: micrófono (también en el gesto: Chrome Android / Safari iOS) ──
    this._showOverlay(_voiceL('Khipu — pidiendo micrófono…', 'Khipu — requesting microphone…'), 'connect');
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
    return this._connectSession(opts, sess, stream);
  },

  async _connectSession(opts, sess, stream) {
    // ── Paso 3: credenciales del server (la clave NUNCA llega al navegador) ──
    if (!this._listenOnly) this._showOverlay(_voiceL('Khipu — conectando…', 'Khipu — connecting…'), 'connect');
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
      // recorrido con la voz de Khipu: si el agente no lo empieza en 9 s → el recorrido local
      if (this._narr && !this._narr.started) {
        const n = this._narr;
        clearTimeout(this._narrTimer);
        this._narrTimer = setTimeout(() => { if (this._narr === n && !n.started) this._narrateFallback('no_start'); }, NARRATE_START_MS);
      }
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
    this._tourDetach();
    this._driveStop();                         // el ritmo de la app se va con la sesión
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
    // sesión del recorrido (solo escuchar) cerrada limpia ANTES de que el agente lo empiece → el recorrido local
    if (cleanEnd && this.narrationPending()) { this._narrateFallback('closed'); return; }
    if (cleanEnd) {
      this._narrClear();
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
      // se lee AL REINTENTAR (no al cerrar): si en esos 50 ms tocó 🎙, el reintento ya es con micrófono (y reusa
      // el que pidió en el clic)
      this._retryLater(() => {
        const lo = !!this._listenOnly;
        this.connect({ noOverride: true, auto: true, listenOnly: lo, keepPre: !lo && !!this._preStream });
      }, 50);
      return;
    }
    // caída de red a mitad de conversación → 1 reconexión automática por minuto
    const transient = [1001, 1006, 1012, 1013].indexOf(ev.code) >= 0;
    // (la sesión de solo escuchar no se reconecta: el recorrido sigue en pantalla con sus tiempos)
    if (hadMeta && transient && !errEv.error_type && !this._listenOnly && this._canAutoReconnect()) {
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
    this._tourDetach();                 // un recorrido narrado por la voz sigue solo en pantalla
    this._driveStop();                  // y la app deja de marcarle el ritmo al agente
    this._narrClear();                  // la sesión del recorrido (solo escuchar) termina aquí
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

  // [CONTEXT_UPDATE] silencioso para el agente (contrato de voz v2): lo que hay EN PANTALLA en Khipus OS.
  // Ya no hay "pestaña activa": todo se abre como ventana junto al chat.
  _buildContext() {
    const W = (typeof window !== 'undefined') ? window : {};
    const D = W.KhipuDesk, ck = W.BixbyCockpit;
    const titles = [];
    let focused = null;
    try {
      if (D && D.active && D.active() && D.list) {
        const fid = D.focused ? D.focused() : null;
        D.list().forEach(w => {
          if (!w || w.min) return;
          let t = '';
          try {
            const el = document.querySelector && document.querySelector('.kd-win[data-id="' + w.id + '"] .kd-name');
            t = (el && el.textContent) ? el.textContent : '';
          } catch (e) {}
          if (!t) t = this._title(w.kind);
          t = String(t || w.kind).slice(0, 60);
          if (titles.length < 8) titles.push(t);
          if (w.id === fid) focused = t;
        });
      }
    } catch (e) {}
    let sel = null;
    try { sel = (W._liveSelectedNode && W._liveSelectedNode()) || ((typeof selected !== 'undefined') ? selected : null); } catch (e) { sel = null; }
    const sn = sel ? ((W.NODE_BY_ID || {})[sel] || null) : null;
    let inv = null;
    try {
      const id = (ck && ck.invoked) ? ck.invoked() : null;
      if (id) inv = (W.KhipuChat && W.KhipuChat.agentName) ? W.KhipuChat.agentName(id) : id;
    } catch (e) {}
    let mode = 'simple';
    try { if (W.KhipuAgentPrefs && W.KhipuAgentPrefs.mode && W.KhipuAgentPrefs.mode() === 'pro') mode = 'pro'; } catch (e) {}
    const ctx = {
      app: 'Khipus Finance Intelligence', interface: 'Khipus OS', lang: _voiceLang(),
      open_windows: titles, focused_window: focused,
      selected_company: sn ? { id: sn.id, label: sn.label, ticker: sn.mkt || null,
        nrs: (typeof computeNRS === 'function') ? computeNRS(sn.id) : null } : null,
      invoked_agent: inv, explain_mode: mode, money_mode: this._moneyMode(),
    };
    if (this._listenOnly) ctx.listen_only = true;   // el usuario solo escucha el recorrido (sin micrófono)
    try {   // el recorrido de un minuto, solo mientras está en marcha
      const T = this._tour(), ts = T ? T.state() : null;
      if (ts && ts.on) ctx.tour = { on: true, step: ts.i + 1, of: ts.of };
    } catch (e) {}
    return ctx;
  },

  // ¿con qué dinero se opera AHORA? 'live' / 'paper' (cuenta del bróker ya leída, sin pedir PIN),
  // 'practice' (solo carteras de práctica) o 'none'. Nunca se adivina "simulado".
  _moneyMode() {
    try {
      const c = window.__tradeAcctCache;
      if (c && c.data && typeof c.data.paper === 'boolean') return c.data.paper ? 'paper' : 'live';
    } catch (e) {}
    // sin la cuenta leída (no hay PIN guardado): el modo del bróker sale de /api/trade/status (público, sin PIN).
    // Se pide en segundo plano y el próximo CONTEXT_UPDATE lo lleva; 'practice' NUNCA reemplaza a un bróker real.
    if (typeof this._brokerPaper === 'boolean') return this._brokerPaper ? 'paper' : 'live';
    this._primeBrokerMode();
    try {
      const raw = localStorage.getItem('kh_portfolios');
      const v = raw ? JSON.parse(raw) : null;
      const list = Array.isArray(v) ? v : (v && Array.isArray(v.portfolios) ? v.portfolios : (v && typeof v === 'object' ? Object.keys(v) : []));
      if (list.length) return 'practice';
    } catch (e) {}
    return 'none';
  },

  _primeBrokerMode() {
    if (this._brokerModeP || typeof window === 'undefined' || typeof window._tradeStatusInfo !== 'function') return;
    try {
      this._brokerModeP = Promise.resolve(window._tradeStatusInfo()).then(s => {
        if (s && typeof s.paper === 'boolean' && s.paper !== this._brokerPaper) {
          this._brokerPaper = s.paper;
          try { this._updateContextSoon(); } catch (e) {}
        }
      }).catch(() => {}).then(() => { setTimeout(() => { this._brokerModeP = null; }, 60000); });
    } catch (e) { this._brokerModeP = null; }
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
        if (this._listenOnly) {
          // SOLO ESCUCHAR: sin micrófono; se le pide el recorrido al agente (lo narra con run_guided_demo)
          this._showOverlay(this._narrateText(), 'listen');
          this._orbOn();
          this._narrCheckAudio();                     // ¿el navegador deja sonar la voz? (autoplay / iOS)
          this.updateContext();                       // listen_only:true ANTES del pedido
          if (this._narr && !this._narr.asked) { this._narr.asked = true; this.requestTour(); }
          break;
        }
        this._showOverlay(_voiceL('🎙️ Khipu te escucha — habla', '🎙️ Khipu is listening — speak'), 'listen');
        if (this._preStream) {
          this._startMicWithStream(this._preStream);
          this._preStream = null;
        }
        this._orbOn();   // arranca/alimenta el orbe de voz de la Cabina
        // el botón del recorrido abrió esta sesión y el usuario le sumó el micrófono antes de la metadata
        if (this._narr && !this._narr.asked && !this._narr.done) { this._narr.asked = true; this.requestTour(); }
        break;
      }
      case 'audio': {
        const ev = msg.audio_event || {};
        // audio de una respuesta YA interrumpida: se descarta (si no, seguía sonando)
        if (ev.event_id != null && +ev.event_id < this._lastInterruptId) break;
        const chunk = ev.audio_base_64;
        if (chunk) {
          this._lastAudioAt = this._nowMs();   // el recorrido: ¿ya empezó a sonar la frase? ¿sigue llegando audio?
          if (this._listenOnly) this._narrKick();   // el agente sigue narrando
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
          // solo la píldora: el usuario NUNCA ve tokens internos. El viejo enrutador de tokens de texto
          // ([NAV:]/[XRAY:]/…) se retiró (2026-10-11): las instrucciones los prohíben y las herramientas de
          // cliente hacen todo (contrato de voz v2).
          const clean = this._cleanSpeech(text);
          if (clean) this._showOverlay('Khipu: ' + clean.slice(0, 80), 'speak');
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
        // el eco de nuestro propio `[TOUR n/N] …` (si ElevenLabs lo devolviera) no es el usuario hablando
        if (t && TOUR_TAG_RE.test(t)) break;
        if (t) this._showOverlay(_voiceL('Tú: ', 'You: ') + t.slice(0, 80), 'think');   // 'think' ya enciende setBixbyThinking
        if (t) this._tourPauseIfVoice();
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
        // la provocó nuestro `[TOUR n/N]` recién enviado (no el usuario): el recorrido no se pausa
        if (!(this._driveSentAt != null && this._nowMs() - this._driveSentAt < TOUR_SELF_INTERRUPT_MS)) this._tourPauseIfVoice();
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
        if (tr.tool_name === 'end_call') {
          // colgó ANTES de empezar el recorrido del botón: igual hay recorrido (el local)
          if (this.narrationPending()) this._narrateFallback('closed');
          if (this.isConnected) this._endAfterSpeech();
        }
        break;
      }
      case 'error': {
        const ev = msg.error_event || {};
        this._lastErrorEvent = ev;
        try { console.warn('[Khipu voz] ElevenLabs error:', ev.error_type, ev.message || ev.reason || ''); } catch (e) {}
        // (solo escuchando no hay micrófono que tocar: el cierre lo avisa _listenOnlyFail, una vez)
        if (ev.error_type === 'max_duration_exceeded' && !this._listenOnly) this._setStatus(this._closeText({}, true, ev), true, 'error');
        break;
      }
      default:
        break;   // vad_score, context_usage, internal_*… no se usan
    }
  },

  // end_call: cerrar cuando termine de sonar lo agendado (máx 8 s)
  // onlyListen: solo si la sesión sigue siendo de SOLO ESCUCHAR al vencer (el usuario pudo sumarle el micrófono)
  _endAfterSpeech(onlyListen) {
    const ctx = this.audioCtx;
    const left = (ctx && this._playCursor) ? Math.max(0, this._playCursor - ctx.currentTime) : 0;
    clearTimeout(this._endTimer);
    this._endTimer = setTimeout(() => {
      if (this.isConnected && (!onlyListen || this._listenOnly)) this.disconnect();
    }, Math.min(8000, left * 1000 + 400));
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
    this._audioSec = (this._audioSec || 0) + buffer.duration;   // el recorrido: cuánto de la frase llegó a sonar
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
      || this._resolveNode(params.company_id)
      || this._resolveNode(params.company) || null;   // `company`: esquema de los nombres RETIRADOS (deep_research…)
  },

  // ¿la pregunta NOMBRA una empresa del catálogo? (nombre, id, nombre legal o alias EXACTOS dentro de la frase;
  // ticker solo si viene en MAYÚSCULAS: "now", "net", "arm"… son palabras comunes). Sin empresa, la mención
  // @agente no sirve (el servidor pregunta "¿sobre qué empresa?" o responde sobre la última que viste).
  _namesCompany(q) {
    const W = (typeof window !== 'undefined') ? window : {};
    const NODES = Array.isArray(W.NODES) ? W.NODES : [];
    if (!NODES.length) return null;
    const R = W.KhipuResolve;
    const norm = (x) => {
      try { if (R && R.norm) return R.norm(x); } catch (e) {}
      return String(x == null ? '' : x).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')
        .replace(/[^a-z0-9\s]/g, ' ').replace(/\s+/g, ' ').trim();
    };
    if (!this._nameIdx || this._nameIdx.n !== NODES.length) {
      const names = Object.create(null), tick = Object.create(null);
      const NB = W.NODE_BY_ID || {};
      const add = (k, n) => { k = norm(k); if (k.replace(/\s/g, '').length >= 3 && n && !names[k]) names[k] = n; };
      NODES.forEach(n => {
        if (!n || !n.id) return;
        add(n.label, n); add(n.id, n);
        const raw = String(n.label || ''), i = raw.indexOf('(');
        if (i > 0) add(raw.slice(0, i), n);
        if (n.mkt) tick[String(n.mkt)] = n;
      });
      try { Object.keys(W.LEGAL_NAMES || {}).forEach(k => add(k, NB[W.LEGAL_NAMES[k]])); } catch (e) {}
      this._nameIdx = { n: NODES.length, names, tick };
    }
    const { names, tick } = this._nameIdx;
    const raw = String(q || '').split(/[\s¿?¡!.,;:"«»“”()]+/).filter(Boolean);
    for (const w of raw) if (w.length >= 2 && w === w.toUpperCase() && tick[w]) return tick[w];
    const words = norm(q).split(' ').filter(Boolean);
    for (let len = Math.min(5, words.length); len >= 1; len--) {
      for (let i = 0; i + len <= words.length; i++) {
        const hit = names[words.slice(i, i + len).join(' ')];
        if (hit) return hit;
      }
    }
    return null;
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
    if (!params || typeof params !== 'object') params = {};
    // UNA sola respuesta por llamada, SIEMPRE antes del tope del agente: si la
    // acción tarda más, se responde "sigue en pantalla" (antes ElevenLabs veía
    // un timeout y Khipu se quedaba mudo o decía que había fallado).
    let answered = false;
    let guard = null;
    const ws0 = this.ws;                 // el resultado va SOLO al socket por el que llegó la llamada
    const respond = (result) => {
      if (answered) return;
      answered = true;
      clearTimeout(guard);
      if (ws0 && ws0 === this.ws && ws0.readyState === WebSocket.OPEN) {
        let txt;
        try { txt = typeof result === 'string' ? result : JSON.stringify(result == null ? { success: true } : result); }
        catch (e) { txt = '{"success":false}'; }
        ws0.send(JSON.stringify({
          type: 'client_tool_result',
          tool_call_id,
          result: txt,          // el API exige STRING
          is_error: false,      // los errores van en el texto: con is_error el agente no los ve
        }));
      }
    };
    // tope: el del contrato (VOICE_TOOL_TIMEOUT_S) o, para un nombre RETIRADO, el que el agente viejo
    // aún tiene registrado (VOICE_ALIAS_TIMEOUT_S) — así un agente desactualizado nunca ve un timeout
    const limitS = VOICE_TOOL_TIMEOUT_S[tool_name] || VOICE_ALIAS_TIMEOUT_S[tool_name] || VOICE_TOOL_TIMEOUT_DEFAULT_S;
    const isOrder = tool_name === 'place_order' || tool_name === 'place_paper_trade';
    guard = setTimeout(() => respond(isOrder
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

  // ═══ CONTRATO DE VOZ v2 (2026-10-11): 17 herramientas para Khipus OS ═══
  // Las respuestas van al chat del CENTRO y cada pantalla se abre como VENTANA a su lado. Los nombres de
  // herramienta son INTERNOS (nunca se dicen); los textos para el usuario son bilingües (_voiceL) y nunca
  // llevan tokens de cita ([E1], [S2]…). Los nombres RETIRADOS siguen como ALIAS (un agente o un navegador
  // desactualizado durante un despliegue sigue funcionando); no se declaran a ElevenLabs.
  _dispatchTool(tool_name, params, respond) {
    params = params || {};
    const P = (extra) => Object.assign({}, params, extra);
    const run = (p) => Promise.resolve(p).then(respond).catch(e => respond({ success: false,
      error: _voiceL('No pude completar esa acción: ', "I couldn't complete that action: ") + ((e && e.message) || e) }));
    switch (tool_name) {
      // ── las 17 del contrato ──
      case 'ask_khipu_brain': return this._toolBrain(params, respond);
      case 'open_company': return this._toolOpenCompany(params, respond);
      case 'get_company_info': return run(this._toolCompanyInfo(params));
      case 'open_screen': return respond(this._toolOpenScreen(params));
      case 'compare_companies': return this._toolCompare(params, respond);
      case 'run_live_simulation': return this._toolLiveSim(params, respond);
      case 'run_agent_simulation': return this._toolAgentSim(params, respond);
      case 'show_opportunities': return this._toolOpportunities(params, respond);
      case 'create_visualization': return this._toolVisualize(params, respond);
      case 'quick_thesis': return this._toolQuickThesis(params, respond);
      case 'deep_search': return this._toolDeepSearch(params, respond);
      case 'place_order': return run(this._toolPlaceOrder(params));      // NUNCA envía sin confirmed=true
      case 'open_order_ticket': return this._toolOrderTicket(params, respond);
      case 'get_account_status': return run(this._toolAccountStatus(params));
      case 'get_space_summary': return run(this._toolSpaceSummary(params));
      case 'run_guided_demo': return this._toolTour(params, respond);   // el recorrido de un minuto, narrado por Khipu
      case 'control_interface': return respond(this._toolControl(params));

      // ── ALIAS de nombres retirados → el manejador nuevo más parecido ──
      case 'open_cockpit': {
        const ok = this._osOpen();
        return respond(ok ? { success: true, opened: 'Khipus OS' }
          : { success: false, error: _voiceL('Khipus OS no está disponible.', 'Khipus OS is not available.') });
      }
      case 'switch_tab': return respond(this._toolOpenScreen({ screen: params.tab || params.screen }));
      case 'show_chart': case 'open_terminal': return this._toolOpenCompany(P({ view: 'chart' }), respond);
      case 'navigate_to_company': return this._toolOpenCompany(P({ view: 'map' }), respond);
      case 'open_xray': case 'open_second_brain': return this._toolOpenCompany(P({ view: 'xray' }), respond);
      case 'open_dossier': return this._toolOpenCompany(P({ view: 'dossier' }), respond);
      case 'get_supply_chain_links': return this._toolOpenCompany(P({ view: 'supply_chain' }), respond);
      case 'get_risk_score': return respond(this._toolRiskScore(params));
      case 'get_news': {
        const who = String(params.company_name || params.ticker || params.company || '').trim();
        return this._toolBrain({ agent: 'radar', question: who
          ? _voiceL('Últimas noticias de ' + who, 'Latest news on ' + who)
          : _voiceL('Últimas noticias relevantes del mercado', 'Latest relevant market news') }, respond);
      }
      case 'get_market_summary': return respond(this._toolOpenScreen({ screen: 'market' }));
      case 'get_portfolio_risk': return respond(this._toolOpenScreen({ screen: 'risk' }));
      case 'list_companies': {
        const cat = String(params.category || params.sector || '').trim();
        return this._toolBrain({ question: cat
          ? _voiceL('Lista las principales empresas de ' + cat + ' en el catálogo', 'List the main ' + cat + ' companies in the catalog')
          : _voiceL('¿Qué empresas principales hay en el catálogo?', 'Which main companies are in the catalog?') }, respond);
      }
      case 'get_opportunities': case 'show_insights': case 'show_matrices': return this._toolOpportunities(params, respond);
      case 'get_nrs_top10': return this._toolOpportunities(params, respond, { highest_risk: this._topRisk(10) });
      case 'run_stress_test': return this._toolLiveSim(P({ kind: 'collapse', severity: 100 }), respond);
      case 'run_simulation': return this._toolAgentSim({ preset: params.scenario_id || params.preset || params.scenario }, respond);
      case 'deep_research': return this._toolQuickThesis(params, respond);
      case 'deep_analysis': return this._toolDeepSearch(params, respond);
      case 'place_paper_trade': return run(this._toolPlaceOrder(params));
      case 'place_trade': return this._toolOrderTicket(params, respond);
      case 'get_portfolio_status': return run(this._toolAccountStatus(params));
      default:
        respond({ success: false, error: _voiceL(`Herramienta desconocida: ${tool_name}`, `Unknown tool: ${tool_name}`) });
    }
  },

  // ── ayudantes de las herramientas ──
  _ck() { return (typeof window !== 'undefined' && window.BixbyCockpit) || null; },
  // abre Khipus OS si está cerrado (entrar nunca cuelga la voz; SALIR sí — por eso ninguna herramienta lo cierra)
  _osOpen() {
    const ck = this._ck();
    if (!ck || !ck.open) return false;
    try { if (!ck.isOpen || !ck.isOpen()) ck.open(); return true; } catch (e) { return false; }
  },
  // una ventana del OS (abre el OS si hace falta); sin la Cabina, el camino clásico de siempre
  _osStage(kind, arg) {
    const ck = this._ck();
    if (ck && ck.stage) {
      try {
        if (ck.isOpen && !ck.isOpen() && ck.open) ck.open({ kind, arg });
        else ck.stage(kind, arg);
        return true;
      } catch (e) { return false; }
    }
    return this._show(kind, arg);
  },
  _nodes() { return (typeof window !== 'undefined' && window.NODES) || ((typeof NODES !== 'undefined') ? NODES : []); },
  _label(id) { const n = ((typeof window !== 'undefined' && window.NODE_BY_ID) || {})[id]; return (n && n.label) || String(id); },
  // título VISIBLE de una ventana en el idioma de la app (el mismo que muestra su barra)
  _title(kind, arg, label) {
    const ck = this._ck();
    try {
      if (ck && ck.title) {
        const t = String(ck.title(kind, arg) || '');
        if (t && t !== kind && t.indexOf(kind + ' ·') !== 0) return t;
      }
    } catch (e) {}
    const lab = label || '';
    if (kind === 'glance') return lab ? _voiceL(lab + ' en una mirada', lab + ' at a glance') : _voiceL('En una mirada', 'At a glance');
    if (kind === 'supplychain') return lab ? _voiceL('Cadena de suministro de ' + lab, lab + ' supply chain') : _voiceL('Cadena de suministro', 'Supply chain');
    const SIM = { collapse: ['Caída simulada', 'Simulated failure'], demand: ['Auge de demanda', 'Demand boom'],
      price: ['Shock de precio', 'Price shock'], sanction: ['Sanción', 'Sanction'] };
    const M = { xray: ['X-Ray', 'X-Ray'], graph: ['Grafo', 'Graph'], terminal: ['Terminal', 'Terminal'], compare: ['Comparar', 'Compare'],
      insights: ['Oportunidades', 'Opportunities'], canvas: ['Gráfico', 'Chart'], research: ['Tesis rápida', 'Quick thesis'],
      deep: ['Búsqueda profunda', 'Deep search'], agentsim: ['Simulación por agentes', 'Agent simulation'], broker: ['Mi cuenta', 'My account'] };
    const m = (kind === 'sim' && arg && SIM[arg.kind]) ? SIM[arg.kind] : (M[kind] || SIM[kind === 'sim' ? 'collapse' : ''] || [kind, kind]);
    const base = _voiceL(m[0], m[1]);
    let extra = lab;
    if (!extra && (kind === 'deep' || kind === 'canvas') && typeof arg === 'string') extra = arg.slice(0, 40);
    return extra ? base + ' · ' + extra : base;
  },
  // quita lo que el agente no debe leer en voz alta: negritas y tokens de cita ([E1], [S2, S3], [C1][F2]…)
  _voiceClean(s, max) {
    let t = String(s == null ? '' : s)
      .replace(/\*\*/g, '')
      .replace(/\s*\[(?:[A-Z]{1,2}\d+[a-z]?)(?:\s*[,;\/–-]\s*[A-Z]{0,2}\d+[a-z]?)*\]/g, '')
      .replace(/[ \t]{2,}/g, ' ')
      .replace(/ +([.,;:!?])/g, '$1')
      .trim();
    return max ? t.slice(0, max) : t;
  },
  _voiceList(arr, n, max) {
    return (Array.isArray(arr) ? arr : []).slice(0, n).map(x => this._voiceClean(
      (x && typeof x === 'object') ? (x.name || x.label || x.company || x.title || x.text || '') : x, max || 200)).filter(Boolean);
  },
  _nrsLevel(v) {
    if (v == null || !isFinite(v)) return null;
    return v >= 70 ? _voiceL('alto', 'high') : v >= 40 ? _voiceL('medio', 'medium') : _voiceL('bajo', 'low');
  },
  // proveedores / clientes = SOLO relaciones de FLUJO (G4a), pares distintos, más pesados primero
  _flow(id) {
    const W = (typeof window !== 'undefined') ? window : {};
    const FT = W.NRS_FLOW_TYPES || { supply: 1, fab: 1, cloud: 1, license: 1, ppa: 1, owns: 1, deploy: 1 };
    const canon = (x) => { try { return W._canonId ? W._canonId(x) : x; } catch (e) { return x; } };
    const lidf = (x) => (x && typeof x === 'object') ? x.id : x;
    const sup = new Map(), cus = new Map();
    (W.LINKS || []).forEach(l => {
      if (!l || !FT[l.type || 'supply']) return;
      const s = canon(lidf(l.source)), t = canon(lidf(l.target));
      if (!s || !t || s === t) return;
      const w = +l.w || 0;
      if (t === id) sup.set(s, Math.max(sup.get(s) || 0, w));
      if (s === id) cus.set(t, Math.max(cus.get(t) || 0, w));
    });
    const out = (m) => Array.from(m.entries()).sort((a, b) => b[1] - a[1]).map(e => this._label(e[0]));
    return { suppliers: out(sup), customers: out(cus) };
  },
  // precio SOLO si MKT.quotes lo tiene (window.quotePx); con fuente, fecha y si es en vivo
  _livePx(n) {
    if (!n || !n.mkt) return null;
    const q = (typeof MKT !== 'undefined' && MKT && MKT.quotes) ? MKT.quotes[n.mkt] : null;
    const v = _voicePx(q);
    if (v == null) return null;
    let live = false;
    try { live = window.quoteIsLive ? !!window.quoteIsLive(q) : (typeof q.live === 'number' && isFinite(q.live)); } catch (e) { live = false; }
    return { value: v, currency: q.currency || null, as_of: q.as_of || null, src: q.src || null, live };
  },
  _companyFacts(n) {
    const nrs = (typeof computeNRS === 'function') ? computeNRS(n.id) : null;
    let terms = [];
    try {
      const b = window.computeNRSBreakdown ? window.computeNRSBreakdown(n.id) : null;
      if (b && Array.isArray(b.terms)) terms = b.terms.map(t => ({ key: t.key, val: t.val, max: t.max }));
    } catch (e) { terms = []; }
    const fl = this._flow(n.id);
    const f = { nrs, nrs_level: this._nrsLevel(nrs), nrs_terms: terms, suppliers: fl.suppliers.slice(0, 3), customers: fl.customers.slice(0, 3) };
    const px = this._livePx(n);
    if (px) f.price = px;
    return f;
  },
  _topRisk(k) {
    if (typeof computeNRS !== 'function') return [];
    const NB = window.NODE_BY_ID || {};
    return this._nodes().filter(n => n && (!NB[n.id] || NB[n.id].id === n.id))
      .map(n => ({ company: n.label, nrs: computeNRS(n.id) })).sort((a, b) => b.nrs - a.nrs).slice(0, k);
  },
  _actionTitle(a) {
    if (!a || !a.type) return '';
    const lab = (x) => { const n = this._resolveNode(x); return n ? n.label : ''; };
    switch (a.type) {
      case 'open_xray': return this._title('xray', a.arg, lab(a.arg));
      case 'navigate': case 'stress': return this._title('graph', a.arg, lab(a.arg));
      case 'compare': return this._title('compare', a.arg);
      case 'chart': return this._title('canvas', a.arg);
      case 'agent_sim': return this._title('agentsim', { scenario: a.arg });
      case 'broker': return this._title('broker');
      case 'open_window': return (a.arg && a.arg.kind) ? this._title(a.arg.kind, { id: a.arg.id }, lab(a.arg.id)) : '';
    }
    try { return (window.KhipuChat && window.KhipuChat.actionLabel) ? window.KhipuChat.actionLabel(a) : ''; } catch (e) { return ''; }
  },

  // ── 1) ask_khipu_brain: LA herramienta por defecto ──
  _toolBrain(params, respond) {
    let q = String((params && (params.question || params.query)) || '').trim();
    const AG = { analista: 'analista', fundamental: 'analista', analyst: 'analista', radar: 'radar', noticias: 'radar', news: 'radar',
      cadena: 'cadena', chain: 'cadena', tecnico: 'tecnico', technical: 'tecnico', comite: 'comite', committee: 'comite' };
    const TOK = { analista: '@fundamental', radar: '@noticias', cadena: '@cadena', tecnico: '@tecnico', comite: '@comite' };
    const ag = AG[String((params && params.agent) || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').trim()];
    // el servidor lo enruta a esa mascota — SOLO si la pregunta nombra una empresa: las mascotas responden sobre UNA
    // empresa; una pregunta general (noticias del mercado, un conflicto…) va al cerebro, que tiene las herramientas
    // del mundo (antes: "¿Sobre qué empresa?" o la respuesta sobre la última empresa que el usuario miró)
    if (q && ag && q.charAt(0) !== '@' && this._namesCompany(q)) q = TOK[ag] + ': ' + q;
    const K = window.KhipuChat;
    if (!q) { respond({ success: false, error: _voiceL('No entendí la pregunta: dímela de nuevo.', 'I did not catch the question: please say it again.') }); return; }
    if (!K || !K.send) { respond({ success: false, error: _voiceL('El cerebro de Khipu no está disponible ahora.', "Khipu's brain is not available right now.") }); return; }
    const ck = this._ck();
    const D = window.KhipuDesk;
    const inOS = !!(ck && ck.chatVoice && ck.isOpen && ck.isOpen() && (!D || !D.enabled || D.enabled()));
    let p;
    if (inOS) {
      // Khipus OS: el turno se ve en el chat del centro como uno escrito (y abre las ventanas igual)
      p = ck.chatVoice(q, { timeout: 55000 }).then(d => { d = d || {}; return { d, opened: Array.isArray(d.opened) ? d.opened : [] }; });
    } else {
      // vista clásica / OS cerrado: el mismo cerebro; se abre su primera acción
      p = window.KhipuChat.send(q, { timeout: 55000 }).then(d => {
        d = d || {};
        const opened = [];
        try {
          const a = (d.actions || [])[0];
          if (a && window.KhipuChat.runAction && window.KhipuChat.runAction(a)) { const t = this._actionTitle(a); if (t) opened.push(t); }
        } catch (e) {}
        return { d, opened };
      });
    }
    p.then(({ d, opened }) => {
      // quién trabajó (nombres de las mascotas que aportaron; nunca nombres de herramientas)
      const used = Array.isArray(d.agents_used) ? d.agents_used.filter(a => a && a.agent && a.ok !== false) : [];
      const nonK = used.filter(a => a.agent !== 'khipu');
      const names = [];
      (nonK.length ? nonK : used).forEach(a => {
        let nm = a.agent;
        try { if (K.agentName) nm = K.agentName(a.agent); } catch (e) {}
        if (nm && names.indexOf(nm) < 0) names.push(nm);
      });
      respond({
        success: true,
        answer: this._voiceClean(d.answer, 2500),
        agents: names,
        sources: (Array.isArray(d.sources) ? d.sources : []).slice(0, 5).map(s => ({
          label: this._voiceClean((s && (s.label || s.title || s.name || s.source)) || '', 120), as_of: (s && s.as_of) || null })),
        opened,
      });
    }).catch(e => respond({ success: false, error: _voiceL('No pude consultar a Khipu: ', 'I could not reach Khipu: ') + ((e && e.message) || e) }));
  },

  // ── 2) open_company: una empresa en la vista pedida, como ventana ──
  _toolOpenCompany(params, respond) {
    const n = this._resolveAny(params);
    if (!n) { respond(this._notFound(params.company_name || params.ticker || params.company_id)); return; }
    const W = window;
    let view = String(params.view || 'glance').toLowerCase().replace(/[\s-]+/g, '_');
    view = { supplychain: 'supply_chain', chain: 'supply_chain', graph: 'map', terminal: 'chart', price: 'chart' }[view] || view;
    if (['glance', 'xray', 'supply_chain', 'map', 'chart', 'dossier', 'research', 'committee'].indexOf(view) < 0) view = 'glance';
    const listed = !!n.mkt;
    const out = { success: true, company: n.label, ticker: n.mkt || null, listed, view, opened: '', facts: this._companyFacts(n) };
    const glance = () => {
      if (W.KhipuOSWin && W.KhipuOSWin.open && W.KhipuOSWin.open('glance', { id: n.id })) return;
      this._osStage('xray', n.id);
    };
    let go = null;
    switch (view) {
      case 'glance':
        out.opened = this._title('glance', { id: n.id }, n.label); go = glance; break;
      case 'xray':
        out.opened = this._title('xray', n.id, n.label); go = () => this._osStage('xray', n.id); break;
      case 'supply_chain':
        if (W.KhipuOSWin && W.KhipuOSWin.open) {
          out.opened = this._title('supplychain', { id: n.id }, n.label);
          go = () => { if (!W.KhipuOSWin.open('supplychain', { id: n.id })) this._osStage('graph', n.id); };
        } else { out.opened = this._title('graph', n.id, n.label); go = () => this._osStage('graph', n.id); }
        out.suppliers_count = this._flow(n.id).suppliers.length;
        out.customers_count = this._flow(n.id).customers.length;
        break;
      case 'map':
        out.opened = this._title('graph', n.id, n.label);
        go = () => { this._osStage('graph', n.id); if (W.khipuGraph3D?.active) W.khipuGraph3D.selectNode(n.id); };
        break;
      case 'chart':
        if (listed) { out.opened = this._title('terminal', { ticker: n.mkt }, n.label); go = () => this._osStage('terminal', { ticker: n.mkt }); }
        else {
          out.note = _voiceL(n.label + ' no cotiza en bolsa: no tiene gráfico de precio. Abrí su resumen.',
            n.label + ' is not publicly traded: it has no price chart. I opened its summary instead.');
          out.opened = this._title('glance', { id: n.id }, n.label); go = glance;
        }
        break;
      case 'dossier':   // funciona también para privadas (ficha + dueño + noticias)
        out.opened = 'Dossier · ' + n.label; go = () => { this._osOpen(); this._show('dossier', n.mkt || n.id); }; break;
      case 'research':
        if (!(W.KhipuResearch && W.KhipuResearch.open)) { respond({ success: false, error: _voiceL('La investigación con evidencia no está disponible ahora.', 'Evidence-based research is not available right now.') }); return; }
        out.opened = _voiceL('Investigación con evidencia · ', 'Evidence-based research · ') + n.label;
        out.note = _voiceL('Muestra las conclusiones que ya existen; lanzar un estudio nuevo es un clic del usuario.',
          "It shows the conclusions that already exist; starting a new study is the user's click.");
        go = () => { this._osOpen(); W.KhipuResearch.open(n.id); };
        break;
      case 'committee':
        if (!(W.KhipuCommittee && W.KhipuCommittee.open)) { respond({ success: false, error: _voiceL('El comité de inversión no está disponible ahora.', 'The investment committee is not available right now.') }); return; }
        out.opened = _voiceL('Comité de inversión · ', 'Investment committee · ') + n.label;
        out.note = _voiceL('El comité propone; toda orden espera la aprobación humana.', 'The committee proposes; every order waits for human approval.');
        go = () => { this._osOpen(); W.KhipuCommittee.open(n.id); };
        break;
    }
    respond(out);   // responde YA; la ventana se abre fuera del hilo del audio
    this._defer(() => { try { if (go) go(); } catch (e) {} this._updateContextSoon(); });
  },

  // ── 3) get_company_info: datos al instante, sin abrir nada ──
  async _toolCompanyInfo(params) {
    const n = this._resolveAny(params);
    if (!n) return this._notFound(params.company_name || params.ticker || params.company_id);
    const W = window;
    const listed = !!n.mkt;
    let live = null, liveNote = null;
    if (listed && W.KhipuLive && W.KhipuLive.profile) {
      let timer = null;
      const p = await Promise.race([
        Promise.resolve(W.KhipuLive.profile(n.mkt)).catch(() => null),
        new Promise(res => { timer = setTimeout(() => res(null), 9000); }),
      ]);
      clearTimeout(timer);
      if (p && p.available && (p.price != null || p.market_cap_usd_b != null)) {
        live = { price: p.price != null ? +p.price : null, market_cap_b: p.market_cap_usd_b != null ? +p.market_cap_usd_b : null,
          currency: p.currency || null, change_pct: p.change_pct != null ? +p.change_pct : null, as_of: p.as_of || null, src: p.source || null };
      }
    }
    if (listed && !live) {
      liveNote = _voiceL('El dato de mercado en vivo no está disponible ahora; no doy precios ni capitalización viejos.',
        'Live market data is unavailable right now; I will not quote stale prices or market cap.');
    }
    const meta = (W.NODE_META || {})[n.id] || {};
    const S9 = W.SECTORS9 || {}, C2S = W.CAT_TO_SECTOR || {};
    const sec = S9[C2S[n.cat]];
    const fl = this._flow(n.id);
    const nrs = (typeof computeNRS === 'function') ? computeNRS(n.id) : null;
    let terms = [];
    try { const b = W.computeNRSBreakdown ? W.computeNRSBreakdown(n.id) : null; if (b && Array.isArray(b.terms)) terms = b.terms.map(t => ({ key: t.key, val: t.val, max: t.max })); } catch (e) {}
    const out = {
      success: true, company: n.label, ticker: n.mkt || null, listed,
      listing_status: (n.listing && n.listing.status) || (listed ? 'public' : 'private'),
      live, nrs, nrs_level: this._nrsLevel(nrs), nrs_terms: terms,
      suppliers_count: fl.suppliers.length, customers_count: fl.customers.length,
      top_suppliers: fl.suppliers.slice(0, 3), top_customers: fl.customers.slice(0, 3),
      catalog_role: n.role || null, catalog_moat: n.moat || null, catalog_growth: n.growth || null,
      catalog_margin_pct: n.margin != null ? Math.round(n.margin * 100) : null,
      catalog_country: n.country || n.loc || null,
      catalog_sector: (sec && sec.label) || ((typeof catLabel === 'function') ? catLabel(n.cat) : (n.cat || null)),
      catalog_employees: meta.employees || null, catalog_founded: meta.founded || null, catalog_revenue: meta.revenue_2025 || null,
      catalog_description: meta.desc || null,
      catalog_note: _voiceL('Los campos catalog_* son del catálogo, sin fecha: pueden estar desactualizados.',
        'The catalog_* fields come from the catalog, undated: they may be outdated.'),
    };
    if (liveNote) out.live_note = liveNote;
    if (!listed) {
      const e = ((W.PRIVATE_VALUATIONS || {}).entries || {})[n.id];
      if (e && +e.valuation_usd_b > 0) out.private_valuation = { value_usd_b: +e.valuation_usd_b, label: e.label || null, as_of: e.as_of || null, source: e.source_url || null };
    }
    return out;
  },

  // ── 4) open_screen: cualquier pantalla de Herramientas, como ventana ──
  _toolOpenScreen(params) {
    const ALLOWED = ['graph', 'market', 'terminal', 'geo', 'space', 'simulation', 'crypto', 'tkg', 'portfolios', 'broker', 'committee',
      'risk', 'clients', 'scalp', 'insights', 'screener', 'canvas', 'agents', 'brief', 'guia', 'sistema', 'mcp', 'universe'];
    const ALIAS = { map: 'graph', mapa: 'graph', analysis: 'insights', opportunities: 'insights', portfolio: 'portfolios',
      account: 'broker', guide: 'guia', system: 'sistema', temporal: 'tkg', chart: 'canvas' };
    const raw = String((params && (params.screen || params.tab)) || '').toLowerCase().trim();
    const id = ALIAS[raw] || raw;
    const ck = this._ck();
    const list = (ck && ck.screens) ? (ck.screens() || []) : [];
    const hit = list.filter(x => x && x.id === id)[0];
    if (!raw || ALLOWED.indexOf(id) < 0 || (ck && ck.screens && !hit)) {
      const avail = list.filter(x => x && ALLOWED.indexOf(x.id) >= 0).map(x => _voiceL(x.es, x.en));
      return { success: false, error: _voiceL('No tengo esa pantalla' + (raw ? ' («' + raw + '»)' : '') + '.', 'There is no such screen' + (raw ? ' ("' + raw + '")' : '') + '.'),
        available: avail };
    }
    if (ck && ck.openScreen) {
      this._osOpen();
      // el Universo 3D se abre y se cierra con el MISMO botón (segundo toque = cerrar): si ya está a la vista,
      // pedirlo de nuevo no lo cierra
      if (id === 'universe') {
        try {
          const uo = (typeof document !== 'undefined') ? document.getElementById('uni-ov') : null;
          if (uo && uo.style.display !== 'none') return { success: true, opened: _voiceL(hit.es, hit.en), already_open: true };
        } catch (e) {}
      }
      let ok = false;
      try { ok = !!ck.openScreen(id); } catch (e) { ok = false; }
      if (!ok) return { success: false, error: _voiceL('No pude abrir esa pantalla.', 'I could not open that screen.') };
      this._updateContextSoon();
      return { success: true, opened: _voiceL(hit.es, hit.en) };
    }
    // sin Khipus OS (no debería pasar): la pestaña clásica equivalente
    const TAB = { graph: 'map', insights: 'analysis' };
    const ok = this._show('tab', TAB[id] || id);
    return ok ? { success: true, opened: id } : { success: false, error: _voiceL('No pude abrir esa pantalla.', 'I could not open that screen.') };
  },

  // ── 5) compare_companies ──
  _toolCompare(params, respond) {
    const a = this._resolveNode(params.company_a || params.a), b = this._resolveNode(params.company_b || params.b);
    if (!a || !b) { respond(this._notFound(!a ? (params.company_a || params.a) : (params.company_b || params.b))); return; }
    const nrsA = (typeof computeNRS === 'function') ? computeNRS(a.id) : null, nrsB = (typeof computeNRS === 'function') ? computeNRS(b.id) : null;
    const lower = (nrsA == null || nrsB == null || nrsA === nrsB) ? 'tie' : (nrsA < nrsB ? a.label : b.label);
    respond({ success: true, a: a.label, b: b.label, nrs_a: nrsA, nrs_b: nrsB, lower_risk: lower,
      opened: this._title('compare', { a: a.id, b: b.id }, a.label + ' vs ' + b.label) });
    this._defer(() => { this._osStage('compare', { a: a.id, b: b.id }); this._updateContextSoon(); });
  },

  // ── 6) run_live_simulation: shock/auge sobre la cadena, con la MISMA intensidad que la ventana ──
  _toolLiveSim(params, respond) {
    const n = this._resolveAny(params);
    if (!n) { respond(this._notFound(params.company_name || params.ticker)); return; }
    const KH = window.KhipuHot;
    if (!KH || !KH.simulate) { respond({ success: false, error: _voiceL('El motor de simulación no está disponible.', 'The simulation engine is not available.') }); return; }
    const kind = ['collapse', 'demand', 'price', 'sanction'].indexOf(params.kind) >= 0 ? params.kind : 'collapse';
    const dir = kind === 'demand' ? 'up' : 'down';
    const sev = _voiceSimSev(params.severity);
    // EL motor único del servidor (/api/hot/*): la voz dice exactamente lo que muestra la ventana (paso 13)
    KH.simulate({ targets: [n.id], kind, severity: sev }).then((r) => {
      if (!r || !r.ok) {
        respond({ success: false, company: n.label, kind, severity: sev, unsupported: !!(r && r.unsupported),
          error: (r && r.error) || _voiceL('La simulación falló.', 'The simulation failed.') });
        return;
      }
      const arr = [];
      r.impact.forEach((v, id) => { if (id !== n.id && v > 0) arr.push({ id, v }); });
      arr.sort((x, y) => y.v - x.v);
      const out = { success: true, company: n.label, kind, severity: sev, affected: r.reach_1,
        most_impacted: arr.slice(0, 5).map(x => ({ company: this._label(x.id), impact_pct: Math.round(x.v) })),
        hypothetical: true, engine_generation: r.view ? r.view.generation : null,
        note: _voiceL('Escenario hipotético simulado sobre la cadena con el motor del servidor: no son precios reales.',
          'Simulated hypothetical scenario on the chain with the server engine: not real prices.') + (r.note ? ' ' + r.note : ''),
        opened: this._title('sim', { id: n.id, kind, severity: sev }, n.label) };
      try {
        const w = dir === 'down' ? (KH.rivals([n.id], r.impact, 3) || []) : [];
        if (w.length) {
          out.barely_hit_rivals = w.map(x => ({ company: this._label(x.id), hit_pct: Math.round(x.hit) }));
          out.rivals_note = _voiceL('hit_pct = el daño que recibe cada rival (no es una ganancia): no digas que alguien gana un %.',
            'hit_pct = the damage each rival takes (not a gain): never say anyone gains a %.');
        }
      } catch (e) {}
      respond(out);
      this._defer(() => {
        const ck = this._ck();
        if (ck && ck.stage) this._osStage('sim', { id: n.id, kind, severity: sev });
        else this._show('sim', { id: n.id, kind, after: () => { if (window._liveRecolorByImpact) window._liveRecolorByImpact(r.impact, dir); } });
        this._updateContextSoon();
      });
    }, () => respond({ success: false, error: _voiceL('La simulación falló.', 'The simulation failed.') }));
  },

  // ── 7) run_agent_simulation: escenario abierto o preset; nunca cierra el OS ──
  _toolAgentSim(params, respond) {
    const PR = (window.ScenarioBuilder && window.ScenarioBuilder.PRESETS) || {};
    const pid = String(params.preset || '').trim();
    let scenario = String(params.scenario || params.query || '').trim();
    let seedNames = Array.isArray(params.companies) ? params.companies
      : (typeof params.companies === 'string' ? params.companies.split(/[,;]| y | and /) : (Array.isArray(params.seeds) ? params.seeds : []));
    if (pid) {
      const p = PR[pid];
      if (!p) {
        respond({ success: false, error: _voiceL('No conozco ese escenario.', 'I do not know that scenario.'), available: Object.keys(PR) });
        return;
      }
      scenario = (String(p.title || '') + '. ' + String(p.description || '') + ' ' + String(p.question || '')).trim();
      if (!seedNames.length && Array.isArray(p.nodeIds)) seedNames = p.nodeIds;
    }
    if (!scenario) { respond({ success: false, error: _voiceL('Dime qué escenario quieres simular.', 'Tell me which scenario to simulate.') }); return; }
    const seedIds = [];
    seedNames.forEach(c => { const nn = this._resolveNode(String(c || '').trim()); if (nn && seedIds.indexOf(nn.id) < 0) seedIds.push(nn.id); });
    if (!window._runAgentSim) { respond({ success: false, error: _voiceL('La simulación por agentes no está disponible.', 'Agent simulation is not available.') }); return; }
    const opened = this._title('agentsim', { scenario });
    window._runAgentSim(scenario, seedIds, _voiceLang())
      .then(d => {
        if (!d || d.ok === false) { respond({ success: false, error: (d && d.error) || _voiceL('La simulación falló.', 'The simulation failed.') }); return; }
        const impacts = Array.isArray(d.impacts) ? d.impacts.slice(0, 5).map(x => ({
          company: x.label || x.id, pct: x.pct, why: this._voiceClean(x.rationale, 240) })) : [];
        const agents = Array.isArray(d.agents) ? d.agents.map(a => a && a.name).filter(Boolean) : [];
        respond({ success: true, on_screen: true, hypothetical: true, narrative: this._voiceClean(d.narrative, 700),
          top_impacts: impacts, agents, opened });
      })
      .catch(e => respond({ success: false, error: _voiceL('Error en la simulación: ', 'Simulation error: ') + ((e && e.message) || e) }));
  },

  // ── 8) show_opportunities: ventana "Oportunidades" + lo que ve el hipergrafo ──
  _toolOpportunities(params, respond, extra) {
    this._defer(() => { this._osStage('insights'); this._updateContextSoon(); });
    const en = _voiceLang() === 'en';
    let resilient = [];
    if (typeof computeNRS === 'function') {
      resilient = this._nodes().map(n => {
        const nrs = computeNRS(n.id);
        const g = String(n.growth || '').toLowerCase();
        const growth = g.indexOf('🟢') >= 0 ? 2 : g.indexOf('🟡') >= 0 ? 1 : 0;
        const margin = n.margin != null ? n.margin : 0;
        return { company: n.label, nrs, growth, margin, score: growth * 22 + Math.min(30, margin * 60) + (50 - nrs) * 0.5 };
      }).filter(x => x.nrs < 55 && x.growth >= 1 && x.margin > 0.15).sort((a, b) => b.score - a.score).slice(0, 5)
        .map(x => ({ company: x.company, nrs: x.nrs }));
    }
    const base = { success: true, resilient,
      note: _voiceL('Es análisis, no asesoría financiera; la decisión es tuya.', 'This is analysis, not financial advice; the decision is yours.'),
      catalog_note: _voiceL('Las resilientes salen del NRS y del crecimiento/margen del catálogo (sin fecha; puede estar desactualizado).',
        'Resilient companies come from NRS and catalog growth/margin (undated; may be outdated).'),
      opened: this._title('insights') };
    if (extra) Object.assign(base, extra);
    let done = false, g = null;
    const finish = (ins) => {
      if (done) return; done = true; clearTimeout(g);
      respond(Object.assign({ insights: ins || [] }, base));
    };
    g = setTimeout(() => finish([]), 12000);
    let p = null;
    try {
      const ck = this._ck();
      if (ck && ck.matrixInsights) p = ck.matrixInsights(en);
      else {
        const base_ = (typeof BASE !== 'undefined') ? BASE : '';
        p = fetch(base_ + '/api/matrix/insights', { method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ lang: en ? 'en' : 'es', tier: 'fast' }) }).then(r => r.json()).catch(() => null);
      }
    } catch (e) { p = null; }
    if (!p) { finish([]); return; }
    Promise.resolve(p).then(d => {
      if (!d || d.available === false || d.error) { finish([]); return; }
      finish((d.insights || []).slice(0, 3).map(i => ({ title: this._voiceClean(i && i.title, 160), text: this._voiceClean(i && (i.detail || i.text), 400) })));
    }).catch(() => finish([]));
  },

  // ── 9) create_visualization: ventana "Gráfico" ──
  _toolVisualize(params, respond) {
    const q = String(params.query || params.description || '').trim();
    if (!q) { respond({ success: false, error: _voiceL('Dime qué gráfico quieres ver.', 'Tell me which chart you want to see.') }); return; }
    respond({ success: true, opened: this._title('canvas', q),
      note: _voiceL('El gráfico se dibuja en pantalla; descríbelo solo en general (no recibes sus datos).',
        'The chart is drawn on screen; describe it only in general terms (you do not receive its data).') });
    this._defer(() => { this._osStage('canvas', q); this._updateContextSoon(); });
  },

  // ── 10) quick_thesis: "Tesis rápida" (una respuesta de IA, sin evidencia citada) ──
  _toolQuickThesis(params, respond) {
    const n = this._resolveAny(params);
    if (!n) { respond(this._notFound(params.company_name || params.company || params.ticker)); return; }
    if (!window._openDeepResearch) { respond({ success: false, error: _voiceL('La tesis rápida no está disponible.', 'The quick thesis is not available.') }); return; }
    const opened = this._title('research', { id: n.id }, n.label);
    window._openDeepResearch(n.id, _voiceLang())
      .then(d => {
        if (!d || d.ok === false) { respond({ success: false, error: (d && d.error) || _voiceL('La tesis falló.', 'The thesis failed.') }); return; }
        respond({ success: true, on_screen: true, company: n.label,
          thesis: this._voiceClean(d.thesis, 600), sector: this._voiceClean(d.sector, 300),
          competitors: this._voiceList(d.competitors, 6, 80), geopolitics: this._voiceClean(d.geopolitics, 300),
          chokepoints: this._voiceList(d.chokepoints, 5, 160), risks: this._voiceList(d.risks, 5, 160),
          note: _voiceL('Es UNA respuesta de IA sin evidencia citada (para eso está la Investigación con evidencia).',
            'It is ONE AI answer without cited evidence (Evidence-based research is for that).'),
          opened });
      })
      .catch(e => respond({ success: false, error: _voiceL('Error en la tesis: ', 'Thesis error: ') + ((e && e.message) || e) }));
  },

  // ── 11) deep_search: "Búsqueda profunda" (30-90 s, una a la vez) ──
  _toolDeepSearch(params, respond) {
    const q = String(params.question || params.query || '').trim();
    if (!q) { respond({ success: false, error: _voiceL('Dime qué quieres que investigue a fondo.', 'Tell me what to research in depth.') }); return; }
    const opened = this._title('deep', q);
    if (!this._show('deep', q)) { respond({ success: false, error: _voiceL('La búsqueda profunda no está disponible.', 'Deep search is not available.') }); return; }
    const ok = { success: true, started: true, eta_seconds: 60, opened };
    const ck = this._ck();
    let st = null;
    try { st = (ck && ck.deepStart) ? ck.deepStart() : null; } catch (e) { st = null; }
    if (!st || typeof st.then !== 'function') { respond(ok); this._updateContextSoon(); return; }
    let done = false, g = null;
    const fin = (r) => { if (done) return; done = true; clearTimeout(g); respond(r); };
    g = setTimeout(() => fin(ok), 6000);
    st.then(res => {
      if (res && res.busy) fin({ success: false, busy: true, opened, error: _voiceL(
        'Ya hay una búsqueda profunda en curso; intenta de nuevo en un minuto.',
        'There is already a deep search running; try again in a minute.') });
      else if (res && res.error) fin({ success: false, error: String(res.error) });
      else fin(ok);
    }, () => fin(ok));
    this._updateContextSoon();
  },

  // ── 12) place_order: la MISMA seguridad de dos pasos (sin confirmed=true NADA se envía) ──
  async _toolPlaceOrder(params) {
    const r = await this._toolPlacePaperTrade(params);
    if (r && typeof r === 'object' && 'paper' in r) r.mode = r.paper === true ? 'paper' : r.paper === false ? 'live' : 'unknown';
    return r;
  },

  // ── 13) open_order_ticket: el ticket manual (nunca envía nada) ──
  _toolOrderTicket(params, respond) {
    const n = this._resolveAny(params);
    if (!n) { respond(this._notFound(params.company_name || params.ticker)); return; }
    if (!n.mkt) { respond({ success: false, error: _voiceL(n.label + ' no cotiza en bolsa: no tiene ticket de orden.', n.label + ' is not publicly traded: it has no order ticket.') }); return; }
    const note = _voiceL('No se envía nada: el usuario revisa y confirma en pantalla (la cuenta puede ser simulada o de dinero real; la pantalla lo dice).',
      'Nothing is sent: the user reviews and confirms on screen (the account may be simulated or real money; the screen says which).');
    if (typeof openTradeModal === 'function' || typeof window.openTradeModal === 'function') {
      respond({ success: true, company: n.label, ticker: n.mkt, opened: _voiceL('Ticket de orden · ', 'Order ticket · ') + n.label, note });
      this._defer(() => this._show('trade', { id: n.id, ticker: n.mkt, label: n.label }));
      return;
    }
    if (window._openBrokerStage) {
      respond({ success: true, company: n.label, ticker: n.mkt, opened: this._title('broker'), note });
      this._defer(() => window._openBrokerStage({}));
      return;
    }
    respond({ success: false, error: _voiceL('El módulo de órdenes no está cargado.', 'The order module is not loaded.') });
  },

  // ── 14) get_account_status: la cuenta del bróker ("Mi cuenta") con su modo REAL ──
  async _toolAccountStatus(params) {
    const r = await this._toolPortfolioStatus(params);
    if (r && typeof r === 'object' && 'paper' in r) r.mode = r.paper === true ? 'paper' : r.paper === false ? 'live' : 'unknown';
    return r;
  },

  // ── 17) control_interface: Khipus OS por voz (nunca sale del OS: eso colgaría la voz) ──
  _toolControl(params) {
    const a = String((params && params.action) || '').toLowerCase().trim();
    const ck = this._ck(), W = window;
    const ok = (es, en) => ({ success: true, done: _voiceL(es, en) });
    const no = (es, en) => ({ success: false, error: _voiceL(es, en) });
    const isDark = () => { try { return !!(document.body && document.body.classList && document.body.classList.contains('dark')); } catch (e) { return false; } };
    const desk = () => { const D = W.KhipuDesk; return (D && D.active && D.active()) ? D : null; };
    const KNOWN = ['new_conversation', 'arrange_windows', 'close_all_windows', 'minimize_all_windows', 'simple_mode', 'pro_mode',
      'light_theme', 'dark_theme', 'spanish', 'english'];
    if (KNOWN.indexOf(a) < 0) return no('No conozco esa acción de la interfaz.', 'I do not know that interface action.');
    this._osOpen();
    try {
      switch (a) {
        case 'new_conversation':
          if (ck && ck.newConversation) ck.newConversation();
          else if (W.KhipuChat && W.KhipuChat.clear) W.KhipuChat.clear();
          else return no('No pude empezar una conversación nueva.', 'I could not start a new conversation.');
          return ok('Empecé una conversación nueva.', 'Started a new conversation.');
        case 'arrange_windows': {
          const D = desk(); if (!D || !D.arrange) return no('No hay ventanas para ordenar.', 'There are no windows to arrange.');
          D.arrange(true); return ok('Ordené las ventanas.', 'Arranged the windows.');
        }
        case 'close_all_windows': {
          const D = desk(); if (!D || !D.closeAll) return no('No hay ventanas abiertas.', 'There are no open windows.');
          D.closeAll(); return ok('Cerré todas las ventanas; el chat sigue aquí.', 'Closed all windows; the chat is still here.');
        }
        case 'minimize_all_windows': {
          const D = desk(); if (!D || !D.list || !D.minimize) return no('No hay ventanas abiertas.', 'There are no open windows.');
          D.list().forEach(w => { if (w && !w.min) { try { D.minimize(w.id); } catch (e) {} } });
          return ok('Minimicé todas las ventanas; siguen en la barra de abajo.', 'Minimized all windows; they are in the bottom bar.');
        }
        case 'simple_mode': case 'pro_mode': {
          if (!W.KhipuAgentPrefs || !W.KhipuAgentPrefs.set) return no('No pude cambiar el modo.', 'I could not change the mode.');
          W.KhipuAgentPrefs.set({ mode: a === 'pro_mode' ? 'pro' : 'simple' });
          return a === 'pro_mode' ? ok('Modo Pro: respuestas más densas, con cifras y rangos.', 'Pro mode: denser answers, with figures and ranges.')
            : ok('Modo Simple: lenguaje llano y una conclusión clara.', 'Simple mode: plain language and a clear conclusion.');
        }
        case 'light_theme': case 'dark_theme': {
          const want = a === 'dark_theme';
          if (isDark() !== want) {
            if (ck && ck.toggleTheme) ck.toggleTheme();
            else if (document.body && document.body.classList) document.body.classList.toggle('dark', want);
          }
          return want ? ok('Tema oscuro.', 'Dark theme.') : ok('Tema claro.', 'Light theme.');
        }
        case 'spanish': case 'english': {
          const want = a === 'english' ? 'en' : 'es';
          if (_voiceLang() !== want) {
            if (ck && ck.toggleLang) ck.toggleLang();
            else { try { localStorage.setItem('eco_lang', want); } catch (e) {} }
          }
          return want === 'en' ? { success: true, done: 'The app is now in English.' } : { success: true, done: 'La app quedó en español.' };
        }
      }
    } catch (e) {
      return no('No pude hacer ese cambio.', 'I could not make that change.');
    }
    return no('No conozco esa acción de la interfaz.', 'I do not know that interface action.');
  },

  // alias get_risk_score (retirado): el NRS al instante, sin ventana
  _toolRiskScore(params) {
    const n = this._resolveAny(params);
    if (!n) return this._notFound(params.company_name || params.ticker);
    if (typeof computeNRS !== 'function') return { success: false, error: _voiceL('El NRS no está disponible ahora.', 'NRS is not available right now.') };
    const nrs = computeNRS(n.id);
    let terms = [];
    try { const b = window.computeNRSBreakdown ? window.computeNRSBreakdown(n.id) : null; if (b && Array.isArray(b.terms)) terms = b.terms.map(t => ({ key: t.key, val: t.val, max: t.max })); } catch (e) {}
    return { success: true, company: n.label, nrs, nrs_level: this._nrsLevel(nrs), nrs_terms: terms };
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

    // lado EXPLÍCITO: comprar o vender; cualquier otra cosa ('short', 'cerrar', 'salir', un error…) NO se adivina
    // (antes todo lo que no era "vender" pasaba a COMPRA: la orden contraria a lo que el usuario pidió)
    const sideRaw = String(params.side || '').trim().toLowerCase();
    const side = /^(buy|compr)/.test(sideRaw) ? 'buy' : /^(sell|vend|venta)/.test(sideRaw) ? 'sell' : '';
    if (!side) {
      return { success: false, needs_side: true, error: en
        ? `Buy or sell? Tell me which one for ${res.label}.`
        : `¿Comprar o vender? Dime cuál para ${res.label}.` };
    }
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
    // el sí verbal vale SOLO para la orden cuyo resumen se acaba de leer: mismo activo, lado y monto, hace menos de
    // VOICE_ORDER_PREVIEW_MS, y no pasó de papel/desconocido a DINERO REAL entretanto. Un confirmed=true sin ese
    // resumen (error del modelo, "compra 100, confirmado" en una sola frase, texto inyectado en una respuesta)
    // vuelve a ser un resumen: NADA se envía.
    const orderKey = [res.symbol, side, notional != null ? 'usd:' + notional : 'qty:' + qty].join('|');
    const pv = this._orderPreview;
    const previewOk = !!(pv && pv.key === orderKey && (Date.now() - pv.at) <= VOICE_ORDER_PREVIEW_MS
      && !(paper === false && pv.paper !== false));
    if (!confirmed || !previewOk) {
      this._orderPreview = { key: orderKey, at: Date.now(), paper };
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
      const out = { success: false, needs_confirmation: true, summary, symbol: res.symbol, side, amount_usd: notional, qty, paper };
      if (confirmed) out.note = 'Nothing was sent: this order had no summary read to the user yet. Read this summary and ask for an explicit yes before calling again with confirmed=true.';
      return out;
    }

    // confirmed=true tras SU resumen → enviar de verdad (con guard anti-doble-envío compartido); el sí se usa una vez
    this._orderPreview = null;
    const r = await window._executeTradeOrder(Object.assign({ channel: 'voice' }, orderObj));
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
      const r = await window._tradeFetch('/api/trade/positions/detail', { channel: 'voice' }, false);
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
    const nextL0 = Array.isArray(lch) ? lch[0] : ((lch && Array.isArray(lch.launches)) ? lch.launches[0] : null);
    // SOLO conteos EN VIVO de CelesTrak: si el servidor cayó al respaldo sintético ('fallback') se dice que
    // no hay dato — nunca se leen cifras inventadas como si fueran reales
    if (!tle || tle.source !== 'celestrak') {
      return { success: false, unavailable: true, source: (tle && tle.source) || null,
        next_launch: (nextL0 && nextL0.name) || null,
        error: en ? 'Live satellite counts (CelesTrak) are unavailable right now; I will not give fallback figures.'
          : 'Los conteos de satélites en vivo (CelesTrak) no están disponibles ahora; no doy cifras de respaldo.' };
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
      next_launch: nextL ? nextL.name : null, source: tle.source,
      as_of: tle.as_of || tle.fetched_at || null, fetched_at: new Date().toISOString(), summary,
    };
  },

  // ═══ EL RECORRIDO DE UN MINUTO narrado con la voz de Khipu (2026-10-11) ═══
  // engine/cockpit.js pinta cada paso (BixbyCockpit.tour) desde el guion único window.KHIPU_TOUR. El agente empieza
  // (run_guided_demo start → dice la frase `say`) y desde ahí LA APP MARCA EL RITMO (_driveTick): cuando la frase
  // terminó de sonar, pasa la pantalla y le manda `[TOUR n/N] <frase>`. `next` sigue sirviendo (reanudar tras una
  // pausa, o LLMs que encadenan): responde recién cuando terminó de SONAR la frase anterior (el audio del agente va
  // por delante del reloj: _playCursor) y siempre antes del tope de 30 s.
  _tour() {
    const ck = (typeof window !== 'undefined') ? window.BixbyCockpit : null;
    return (ck && ck.tour && typeof ck.tour.start === 'function') ? ck.tour : null;
  },
  _tourOn() {
    const T = this._tour();
    try { const s = T ? T.state() : null; return !!(s && s.on); } catch (e) { return false; }
  },
  _tourVoiceLed() {
    const T = this._tour();
    try { const s = T ? T.state() : null; return !!(s && s.on && s.voice); } catch (e) { return false; }
  },
  _nowMs() { return (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now(); },
  // ¿ya terminó de sonar la frase que Khipu estaba diciendo? Lo agendado ya sonó (margen 0,15 s) Y además:
  // · algo de ESTA frase llegó a sonar (audio después de la última frase entregada); si no llegó nada, se espera
  //   TOUR_NO_AUDIO_MS desde el pedido (el `next` puede llegar antes que el audio de la frase);
  // · no llega audio hace TOUR_AUDIO_GAP_MS (un hueco entre trozos no es el final: _playCursor vuelve a 0).
  _speechDrained(calledAt, needAudio) {
    const ctx = this.audioCtx;
    if (!ctx) return true;
    if (((this._playCursor || 0) - ctx.currentTime) > 0.15) return false;
    if (calledAt == null) return true;
    const now = this._nowMs(), last = this._lastAudioAt == null ? -Infinity : this._lastAudioAt;
    // needAudio: la frase la mandó la app ([TOUR n/N]) y aún no sonó → se espera a que suene (hasta el tope)
    if (this._tourSaidAt != null && last < this._tourSaidAt) return needAudio ? false : now - calledAt >= TOUR_NO_AUDIO_MS;
    return now - last >= TOUR_AUDIO_GAP_MS;
  },
  _waitSpeechDrained(maxMs, calledAt, needAudio, noAudioMs) {
    return new Promise(resolve => {
      const t0 = Date.now();
      let waited = 0;
      const tick = () => {
        if (this._speechDrained(calledAt, needAudio) || waited >= maxMs || Date.now() - t0 >= maxMs) { resolve('drained'); return; }
        // la frase pedida no empezó a sonar en noAudioMs → 'noaudio' (el que llama decide; no se sigue esperando)
        if (noAudioMs && waited >= noAudioMs && this._tourSaidAt != null &&
            (this._lastAudioAt == null || this._lastAudioAt < this._tourSaidAt)) { resolve('noaudio'); return; }
        waited += 150;
        setTimeout(tick, 150);
      };
      tick();
    });
  },
  // ── LA APP MARCA EL RITMO (contrato 2026-10-12 b) ──
  // _drive = la ÚLTIMA frase entregada: { sess, i (paso, base 0), by: 'tool' (respuesta de run_guided_demo) | 'msg'
  // ([TOUR n/N]), at (cuándo), text, sends (mensajes de este paso, máx 2), readyAt (desde cuándo ya sonó) }.
  // Una entrega por paso: la marca quien la hace (start/next del agente o el bucle) y nunca dos.
  _tourPendingN() {
    const p = this._tourPend;
    return (p && p.sess === this._sess) ? p.n : 0;
  },
  _tourPendAdd(d) {
    const p = this._tourPend;
    if (!p || p.sess !== this._sess) this._tourPend = { sess: this._sess, n: 0 };
    this._tourPend.n = Math.max(0, this._tourPend.n + d);
  },
  _driveMark(i, by, text, say) {
    const now = this._nowMs();
    const line = String(say || '');
    this._drive = { sess: this._sess, i: i, by: by, at: now, text: text || '', sends: by === 'msg' ? 1 : 0, readyAt: null,
      sec0: this._audioSec || 0,
      minSec: Math.min(TOUR_LINE_MIN_CAP_S, TOUR_LINE_MIN_FRAC * line.length / TOUR_SPEECH_CPS) };
    this._driveUnsaid = null;                     // una entrega nueva: la frase "no dicha" de antes ya no cuenta
    this._tourSaidAt = now;
    this._narrKick();                             // cada entrega cuenta como "el recorrido sigue vivo"
    this._driveArm();
  },
  _driveArm() {
    if (this._driveT) return;
    this._driveT = setTimeout(() => { this._driveT = 0; this._driveTick(); }, TOUR_DRIVE_TICK_MS);
  },
  _driveStop() {
    clearTimeout(this._driveT); this._driveT = 0;
    this._drive = null;
    this._driveUnsaid = null;                     // (_driveGiveUp la vuelve a poner DESPUÉS de detener)
  },
  _driveSend(text) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return false;
    try {
      this.ws.send(JSON.stringify({ type: 'user_message', text: text }));
      this._driveSentAt = this._nowMs();
      return true;
    } catch (e) { return false; }
  },
  _driveTick() {
    const d = this._drive;
    if (!d || d.sess !== this._sess || !this.isConnected || !this.ws || this.ws.readyState !== WebSocket.OPEN) { this._driveStop(); return; }
    const T = this._tour();
    let st = null;
    try { st = T ? T.state() : null; } catch (e) { st = null; }
    if (!st || !st.on || !st.voice) { this._driveStop(); return; }   // terminó, se cerró o sigue con sus tiempos
    // en pausa (el usuario habló) o con un run_guided_demo en curso: el agente manda; el bucle espera
    if (st.paused || this._tourPendingN() > 0) { d.readyAt = null; this._driveArm(); return; }
    const now = this._nowMs();
    if (st.i !== d.i) {                           // la pantalla cambió por otro camino: esa frase cuenta como entregada
      this._driveMark(st.i, 'tool');
      return;
    }
    const last = this._lastAudioAt == null ? -Infinity : this._lastAudioAt;
    if (last < d.at) {                            // la frase aún no empezó a sonar
      d.readyAt = null;
      if (d.by === 'msg' && now - d.at >= TOUR_LINE_WAIT_MS) {
        if (d.sends < 2 && this._driveSend(d.text)) {   // el MISMO mensaje, una sola vez más
          d.sends += 1; d.at = now; this._tourSaidAt = now; this._narrKick();
        } else { this._driveGiveUp(T); return; }
      }
      this._driveArm();
      return;
    }
    const ctx = this.audioCtx;
    const left = ctx ? (this._playCursor || 0) - ctx.currentTime : 0;
    if (left > 0.15 || now - last < TOUR_DRIVE_QUIET_MS) { d.readyAt = null; this._driveArm(); return; }
    // sonó muy poco para esta frase (p. ej. solo el "¡Claro!" de antes): se espera un poco más a que llegue
    if (((this._audioSec || 0) - (d.sec0 || 0)) < (d.minSec || 0) && now - last < TOUR_SHORT_GRACE_MS) {
      d.readyAt = null; this._driveArm(); return;
    }
    if (d.readyAt == null) d.readyAt = now;
    if (now - d.readyAt < TOUR_DRIVE_GAP_MS) { this._driveArm(); return; }
    // la frase del paso k ya sonó entera: la app avanza
    if (st.i + 1 >= st.of) { this._driveFinish(T); return; }
    let r = null;
    try { r = T.next(); } catch (e) { r = null; }
    if (!r || r.done || !r.say) { if (r && r.done) this._driveFinished(); else this._driveStop(); return; }
    const text = '[TOUR ' + r.step + '/' + r.of + '] ' + r.say;
    this._driveSend(text);
    this._driveMark(r.step - 1, 'msg', text, r.say);
    this._updateContextSoon();
  },
  // la última frase ya sonó: fin del recorrido (solo escuchar → cuelga tras la frase; con micrófono → sigue la charla)
  _driveFinish(T) {
    try { T.next(); } catch (e) {}
    this._driveFinished();
  },
  _driveFinished() {
    this._driveStop();
    this._updateContextSoon();
    if (!this._listenOnly && this.ws && this.ws.readyState === WebSocket.OPEN) {
      try { this.ws.send(JSON.stringify({ type: 'contextual_update', text: '[CONTEXT_UPDATE] {"tour":"finished"}' })); } catch (e) {}
    }
    this._narrateEnded();
  },
  // el agente no dijo la frase ni con el reenvío: solo escuchar → cuelga y el recorrido sigue LOCAL desde este paso
  // (voiceAttached(false): clips → texto, con el aviso de siempre); con micrófono → pausa (el "sí" del usuario → next)
  _driveGiveUp(T) {
    const d = this._drive;
    this._driveStop();
    if (this._listenOnly) { this._listenOnlyFail('stalled'); return; }
    // esa frase NUNCA sonó: al reanudar (`next` tras el "sí") se repite este paso en vez de saltarlo
    this._driveUnsaid = d ? { sess: this._sess, i: d.i } : null;
    this._tourSeq = (this._tourSeq || 0) + 1;
    try { T.pause(); } catch (e) {}
    this._updateContextSoon();
    this._notice(_voiceL('Khipu no siguió con el recorrido: quedó en pausa. Dile «sigue» para continuar.',
      'Khipu did not go on with the tour: it is paused. Tell him "go on" to continue.'), 'info', 'kh-tour-hand',
      _voiceL('Recorrido de un minuto', 'One-minute tour'));
  },
  _toolTour(params, respond0) {
    // cada respuesta del recorrido cuenta como "el agente sigue vivo" (vigía de la sesión de solo escuchar)
    const respond = (r) => { this._narrKick(); return respond0(r); };
    this._narrKick();
    const ck = window.BixbyCockpit;
    const T = this._tour();
    let action = String((params && params.action) || 'start').toLowerCase().trim();
    if (action !== 'start' && action !== 'next' && action !== 'stop') action = 'start';
    const closed = { success: false, stopped: true, note: 'The tour was closed; do not continue it.' };
    if (!T) {
      // Cabina vieja en caché (sin BixbyCockpit.tour): la demostración de antes, que se narra sola
      if (action === 'stop') {
        try { if (ck && ck.demoStop) ck.demoStop('voice'); } catch (e) {}
        return respond({ success: true, stopped: true });
      }
      if (action === 'next') return respond(closed);
      if (!ck || typeof ck.demo !== 'function') {
        return respond({ success: false, error: _voiceL('El recorrido no está disponible ahora.', 'The tour is not available right now.') });
      }
      respond({ success: true, note: _voiceL(
        'Recorrido en marcha; se narra solo en pantalla. Di UNA frase corta y quédate en silencio.',
        'Tour running; it narrates itself on screen. Say ONE short sentence and stay quiet.') });
      this._defer(() => { try { ck.demo(); } catch (e) {} });
      return;
    }
    if (action === 'stop') {
      this._driveStop();
      try { T.stop('voice'); } catch (e) {}
      respond({ success: true, stopped: true });
      this._narrateEnded();
      return;
    }
    if (action === 'start') {
      let st = null;
      try { st = T.state(); } catch (e) { st = null; }
      let r = null;
      if (st && st.on && st.voice && st.say) {
        r = { step: st.i + 1, of: st.of, say: st.say };   // idempotente
        // en pausa (el usuario habló) y el agente retoma con start: se reanuda en el paso actual (si no, el bucle
        // quedaba quieto para siempre)
        if (st.paused && typeof T.resume === 'function') {
          try { const rr = T.resume(); if (rr && rr.say) r = rr; } catch (e) {}
        }
      }
      else if (st && st.on && st.say && this._narrFbSess === this._sess) {
        // el respaldo del botón ya va en pantalla (esta conversación, con micrófono): la voz lo toma en el paso
        // actual, sin volver al paso 1
        try { T.voiceAttached(true); } catch (e) {}
        r = { step: st.i + 1, of: st.of, say: st.say };
      }
      else { try { r = T.start({ voice: true }); } catch (e) { r = null; } }
      if (!r || !r.say) {
        return respond({ success: false, error: _voiceL('El recorrido no está disponible ahora.', 'The tour is not available right now.') });
      }
      this._updateContextSoon();
      this._driveMark(r.step - 1, 'tool', '', r.say);   // la frase de este paso la entrega la herramienta (no un [TOUR])
      this._narrateStarted();
      return respond({ success: true, step: r.step, of: r.of, say: r.say,
        note: 'Say exactly the "say" line and nothing else. The app then sends you each next line as a message that starts with [TOUR n/N]: say exactly the text after the tag, nothing else, and do not call any tool for it.' });
    }
    // next (algunos LLM sí encadenan; y es el "sí, sigue" tras una pausa)
    if (!this._tourOn()) { respond(closed); this._narrateEnded(); return; }
    // el recorrido corre en pantalla con sus propios tiempos (p. ej. lo empezó la interfaz): la voz lo toma, para que
    // no avancen a la vez el agente y los temporizadores
    if (!this._tourVoiceLed()) { try { T.voiceAttached(true); } catch (e) {} }
    const seq = this._tourSeq || 0;
    const limitMs = Math.max(2000, (VOICE_TOOL_TIMEOUT_S.run_guided_demo || 30) * 1000 - 5000);   // ~25 s
    // la frase del paso actual la mandó la app ([TOUR n/N]) y aún no sonó: NO se avanza por encima de ella; se
    // espera a que suene y termine y se devuelve la SIGUIENTE (nunca dos entregas de un paso ni un paso saltado)
    let needAudio = false;
    try {
      const d = this._drive, st0 = T.state();
      needAudio = !!(d && d.sess === this._sess && d.by === 'msg' && st0 && d.i === st0.i &&
        (this._lastAudioAt == null || this._lastAudioAt < d.at));
    } catch (e) { needAudio = false; }
    this._tourPendAdd(1);                         // mientras tanto el bucle de la app no manda nada
    const sess = this._sess;
    const respondNext = (r) => { if (sess === this._sess) this._tourPendAdd(-1); return respond(r); };
    // needAudio y el agente no dice nada en TOUR_NO_AUDIO_MS: respondió al [TOUR] con `next` EN VEZ de decir la frase
    // (espera el resultado para hablar) → se le devuelve la frase ACTUAL, sin avanzar (antes: 25 s mudo y paso saltado)
    this._waitSpeechDrained(limitMs, this._nowMs(), needAudio, needAudio ? TOUR_NO_AUDIO_MS : 0).then((why) => {
      // la llamada era de una sesión que ya se cerró: no toca el recorrido de ahora (respond va por SU socket)
      if (sess !== this._sess) { respond(closed); return; }
      if (!this._tourOn()) { respondNext(closed); this._narrateEnded(); return; }
      if ((this._tourSeq || 0) !== seq) {
        // mientras esperaba, el usuario habló/interrumpió (en pausa) o se cortó la voz: NO se avanza
        if (!this._tourVoiceLed()) return respondNext(closed);
        let st0 = null;
        try { st0 = T.state(); } catch (e) { st0 = null; }
        this._updateContextSoon();
        return respondNext({ success: true, paused: true, step: st0 ? st0.i + 1 : null, of: st0 ? st0.of : null,
          note: 'The user interrupted: answer briefly and ask whether to continue (yes → action next, no → action stop).' });
      }
      let r = null;
      const un = this._driveUnsaid;
      this._driveUnsaid = null;
      let cur = null;
      try { cur = T.state(); } catch (e) { cur = null; }
      const d1 = this._drive;
      if (why === 'noaudio' && cur && cur.on && cur.say && d1 && d1.sess === this._sess && d1.by === 'msg' && d1.i === cur.i) {
        this._updateContextSoon();
        this._driveMark(cur.i, 'tool', '', cur.say);   // la entrega la herramienta: el bucle no reenvía el [TOUR]
        return respondNext({ success: true, step: cur.i + 1, of: cur.of, say: cur.say });
      }
      if (un && un.sess === this._sess && cur && cur.i === un.i && typeof T.resume === 'function') {
        try { r = T.resume(); } catch (e) { r = null; }   // reanuda la frase que no llegó a sonar (sin saltarla)
      }
      if (!r) { try { r = T.next(); } catch (e) { r = null; } }
      if (!r || r.done) {
        this._driveStop();
        this._updateContextSoon();
        respondNext({ success: true, done: true, note: 'Tour finished: stay quiet and wait.' });
        this._narrateEnded();                    // solo escuchaba: termina la última frase y cuelga
        return;
      }
      this._updateContextSoon();
      this._driveMark(r.step - 1, 'tool', '', r.say);   // este paso lo entregó la herramienta: el bucle no manda [TOUR]
      respondNext({ success: true, step: r.step, of: r.of, say: r.say });
    });
  },
  // pedido desde la interfaz con la voz conectada: que el agente lo narre (manda run_guided_demo start)
  requestTour() {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return false;
    try {
      this.ws.send(JSON.stringify({ type: 'user_message',
        text: _voiceL('Hazme el recorrido guiado de un minuto.', 'Give me the one-minute guided tour.') }));
      return true;
    } catch (e) { return false; }
  },
  // ═══ EL BOTÓN DEL RECORRIDO CON LA VOZ REAL DE KHIPU (2026-10-12) ═══
  // «▶ Ver el recorrido de un minuto» sin conversación abierta: se abre una sesión de SOLO ESCUCHAR (el mismo
  // /api/voice/session + URL firmada + _openSocket que connect(), SIN getUserMedia ni user_audio_chunk: no pide
  // permiso de micrófono ni hay eco) y, con la metadata, se le pide el recorrido al agente → lo narra con
  // run_guided_demo y suena EXACTAMENTE como Khipu en una conversación (los clips del servidor sonaban a "la voz
  // vieja"). Llamar DENTRO del clic (el AudioContext se crea/reanuda en el gesto). Devuelve Promise<'voice' (el
  // agente lo empezó) | 'local' (va el recorrido local) | 'requested' (conversación con micrófono ya abierta) |
  // 'unavailable' | 'busy' | 'cancelled'>. El micrófono (toggle) durante esta sesión = HABLARLE (upgradeToMic).
  narrateTour() {
    if (this._narr && !this._narr.done) return this._narr.promise;              // doble clic: el mismo pedido
    if (this.isConnected && !this._listenOnly) return Promise.resolve(this.requestTour() ? 'requested' : 'unavailable');
    // la sesión de solo escuchar de un recorrido que YA terminó (o se cerró) solo está dejando sonar su última
    // frase: se cuelga ya y se pide uno nuevo (antes el clic no hacía nada)
    if (this._listenOnly && (this.isConnected || this.isConnecting()) && !this._tourOn()) this.disconnect();
    if (this.isConnecting() || this.isConnected) return Promise.resolve('busy');
    let resolve = null;
    const promise = new Promise(r => { resolve = r; });
    const n = this._narr = { started: false, done: false, asked: false, resolve, promise };
    clearTimeout(this._narrCap);
    this._audioSessionPlayback();   // iPhone: que suene aunque el interruptor de silencio esté puesto (en el gesto)
    // el socket ni abre (red, servidor colgado): igual nunca deja al usuario sin recorrido
    this._narrCap = setTimeout(() => { if (this._narr === n && !n.started) this._narrateFallback('timeout'); }, NARRATE_TOTAL_MS);
    try {
      const p = this.connect({ listenOnly: true });   // su parte síncrona (AudioContext) corre aquí, en el gesto
      if (p && typeof p.catch === 'function') p.catch(() => {});
    } catch (e) { this._narrateFallback('error'); }
    return promise;
  },
  _narrateText() {
    return _voiceL('Khipu narra el recorrido — toca 🎙 para hablarle', 'Khipu is narrating the tour — tap 🎙 to talk to him');
  },
  // el agente empezó el recorrido (run_guided_demo start): ya no hace falta el recorrido local
  _narrateStarted() {
    const n = this._narr;
    if (!n || n.done) return;
    n.started = true; n.done = true; this._narr = null;
    clearTimeout(this._narrTimer); this._narrTimer = 0;
    clearTimeout(this._narrCap); this._narrCap = 0;
    try { const T = window.KhipuToast; if (T && T.dismiss) T.dismiss('kh-tour-hand'); } catch (e) {}
    if (this._listenOnly) { this._narrStartedSess = this._sess; this._narrKick(); }   // vigía: si el agente se calla
    try { n.resolve('voice'); } catch (e) {}
  },
  // terminó (done), lo cortó el agente (stop) o lo cerró el usuario (✕/Esc): si solo escuchaba, se deja terminar
  // la última frase (máx 8 s) y se cuelga. Si el usuario le sumó el micrófono, la conversación sigue.
  // Un `next`/`stop` ANTES de `start` (el agente se confundió) no deja al usuario sin nada: va el recorrido local.
  _narrateEnded(byUser) {
    if (this.narrationPending()) {
      if (byUser) { if (this._listenOnly) this.disconnect(); else this._narrClear(); }
      else this._narrateFallback('closed');
      return;
    }
    this._narrWatchStop();
    if (this._listenOnly) this._endAfterSpeech(true);
  },
  // VIGÍA de la sesión de solo escuchar ya empezada: si el agente deja de narrar (ni herramienta ni audio en
  // NARRATE_STALL_MS después de que terminó de sonar lo último) se cuelga y el recorrido sigue en pantalla con
  // sus tiempos. Sin esto, una sesión trabada quedaba abierta (y cobrando) hasta el tope de ElevenLabs.
  _narrKick() {
    if (!this._listenOnly || !this.isConnected || this._narrStartedSess !== this._sess) return;
    clearTimeout(this._narrWatch);
    const sess = this._sess;
    const check = () => {
      this._narrWatch = 0;
      if (sess !== this._sess || !this._listenOnly || !this.isConnected) return;
      const ctx = this.audioCtx;
      const left = (ctx && this._playCursor) ? Math.max(0, this._playCursor - ctx.currentTime) : 0;
      if (left > 0.05) { this._narrWatch = setTimeout(check, Math.min(NARRATE_STALL_MS, left * 1000 + 200)); return; }
      this._listenOnlyFail('stalled');
    };
    this._narrWatch = setTimeout(check, NARRATE_STALL_MS);
  },
  _narrWatchStop() { clearTimeout(this._narrWatch); this._narrWatch = 0; },
  // iOS Safari (16.4+): sin micrófono la página queda en la categoría 'ambient', que el interruptor de silencio
  // CALLA (los clips viejos iban por <audio>, que sí suena). 'playback' = suena como un reproductor. Se restaura
  // al colgar y ANTES de pedir el micrófono (la conversación necesita grabar).
  _audioSessionPlayback() {
    try {
      const as = (typeof navigator !== 'undefined') ? navigator.audioSession : null;
      if (!as || this._asPrev != null) return;
      this._asPrev = as.type || 'auto';
      as.type = 'playback';
    } catch (e) { this._asPrev = null; }
  },
  _audioSessionRestore() {
    if (this._asPrev == null) return;
    const prev = this._asPrev; this._asPrev = null;
    try { navigator.audioSession.type = prev; } catch (e) {}
  },
  // el navegador no dejó sonar el AudioContext (autoplay, interrupción de iOS): no se narra un recorrido mudo
  _narrCheckAudio() {
    const ctx = this.audioCtx;
    if (!ctx || ctx.state === 'running') return;
    try { const p = ctx.resume(); if (p && typeof p.catch === 'function') p.catch(() => {}); } catch (e) {}
    const sess = this._sess;
    clearTimeout(this._narrAudioT);
    this._narrAudioT = setTimeout(() => {
      this._narrAudioT = 0;
      if (sess !== this._sess || !this._listenOnly || !ctx || ctx.state === 'running') return;
      if (this.narrationPending()) this._narrateFallback('muted');
      else this._listenOnlyFail('muted');
    }, NARRATE_AUDIO_CHECK_MS);
  },
  // no se pudo (sesión 4xx/5xx, sin ElevenLabs, cuota, el socket se cerró antes de la metadata, override_error tras
  // su reintento, o el agente no lo empezó a tiempo) → se cierra la sesión de solo escuchar y va el recorrido LOCAL
  // (clips → texto), UNA vez y solo si no hay ya un recorrido en marcha.
  _narrateFallback(why) {
    const n = this._narr;
    if (!n || n.done || n.started) return false;
    const listenOnly = !!this._listenOnly;        // si ya le sumó el micrófono, la conversación sigue abierta
    n.done = true; this._narr = null;
    clearTimeout(this._narrTimer); this._narrTimer = 0;
    clearTimeout(this._narrCap); this._narrCap = 0;
    if (listenOnly) this.disconnect();            // ANTES del recorrido local: con la voz "conectada" no suena ningún clip
    const live = !!this.isConnected;              // conversación con micrófono abierta: solo texto (sin eco)
    if (live) {
      // la voz SÍ está conectada (el usuario le sumó el micrófono): no es un fallo; si el agente lo empieza tarde,
      // toma este mismo recorrido en su paso actual (_toolTour start)
      this._narrFbSess = this._sess;
      this._notice(_voiceL('El recorrido va en pantalla; puedes seguir hablándole a Khipu.',
        'The tour runs on screen; you can keep talking to Khipu.'), 'info', 'kh-tour-hand',
        _voiceL('Recorrido de un minuto', 'One-minute tour'));
    } else if (why === 'muted') {
      this._notice(_voiceL('El navegador no dejó sonar la voz de Khipu: el recorrido sigue en texto.',
        "The browser didn't let Khipu's voice play: the tour goes on as text."), 'info', 'kh-tour-hand',
        _voiceL('Recorrido de un minuto', 'One-minute tour'));
    } else {
      this._notice(_voiceL('No se pudo conectar la voz en vivo de Khipu: el recorrido sigue sin ella.',
        "Couldn't connect Khipu's live voice: the tour goes on without it."), 'info', 'kh-tour-hand',
        _voiceL('Recorrido de un minuto', 'One-minute tour'));
    }
    const T = this._tour();
    let on = false;
    try { const st = T ? T.state() : null; on = !!(st && st.on); } catch (e) { on = false; }
    if (T && !on) { try { T.start((live || why === 'muted') ? { fallback: true, textOnly: true } : { fallback: true }); } catch (e) {} }
    try { n.resolve('local'); } catch (e) {}
    return true;
  },
  // fin de la sesión del recorrido (colgar, fallo, reemplazo): timers fuera
  _narrClear() {
    clearTimeout(this._narrTimer); this._narrTimer = 0;
    clearTimeout(this._narrCap); this._narrCap = 0;
    clearTimeout(this._narrAudioT); this._narrAudioT = 0;
    this._narrWatchStop(); this._narrStartedSess = 0;
    this._audioSessionRestore();
    this._listenOnly = false;
    const n = this._narr; this._narr = null;
    if (n && !n.done) { n.done = true; try { n.resolve(n.started ? 'voice' : 'cancelled'); } catch (e) {} }
  },
  // la sesión de solo escuchar falló: sin la pantalla de error de la conversación (no hay micrófono que reintentar)
  _listenOnlyFail(text) {
    if (this.narrationPending()) { this._narrateFallback(text === 'muted' ? 'muted' : 'error'); return; }
    const touring = this._tourOn();
    this.disconnect();                            // el recorrido narrado sigue en pantalla con sus tiempos (_tourDetach)
    if (touring) {
      this._notice(text === 'muted'
        ? _voiceL('El navegador no dejó sonar la voz de Khipu: el recorrido sigue en texto.',
          "The browser didn't let Khipu's voice play: the tour goes on as text.")
        : _voiceL('Se cortó la voz de Khipu: el recorrido sigue en pantalla.',
          "Khipu's voice dropped: the tour goes on on screen."), 'info', 'kh-tour-hand',
        _voiceL('Recorrido de un minuto', 'One-minute tour'));
    }
    try { console.warn('[Khipu voz] recorrido:', text); } catch (e) {}
  },
  // 🎙 durante la sesión del recorrido = HABLARLE: el micrófono se pide DENTRO de este clic y se suma al MISMO socket
  async upgradeToMic() {
    const sess = this._sess;
    this._audioSessionRestore();                  // iPhone: la conversación graba (play-and-record), no 'playback'
    const md = (typeof navigator !== 'undefined' && navigator.mediaDevices) ? navigator.mediaDevices : null;
    if (!md || typeof md.getUserMedia !== 'function') {
      this._notice(_voiceL('Este navegador no da acceso al micrófono aquí (¿la página no es HTTPS?).',
        'This browser gives no microphone access here (is the page not HTTPS?).'), 'error', 'kh-voice-mic', _voiceL('Micrófono', 'Microphone'));
      return false;
    }
    let stream = null;
    try {
      stream = await md.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 },
        video: false,
      });
    } catch (e) {
      // sigue solo escuchando; el motivo, el mismo texto bilingüe de siempre
      if (sess === this._sess && this._listenOnly) this._notice(this._micErrorText(e), 'error', 'kh-voice-mic', _voiceL('Micrófono', 'Microphone'));
      return false;
    }
    if (sess !== this._sess || !this._listenOnly) { this._stopTracks(stream); return false; }   // ya colgó
    this._listenOnly = false;
    this._narrWatchStop();                        // ya puede hablarle: los tiempos de ElevenLabs vuelven a mandar
    try { if (this.audioCtx && this.audioCtx.state !== 'running' && this.audioCtx.state !== 'closed') this.audioCtx.resume(); } catch (e) {}
    if (this._metaReceived && this.ws && this.ws.readyState === WebSocket.OPEN) {
      this._startMicWithStream(stream);           // → "Khipu te escucha — habla"
    } else {
      this._releasePre(); this._preStream = stream;   // arranca con la metadata
      this._emitVoice(this.state, this.stateText);
    }
    this._updateContextSoon();                    // listen_only ya no va
    return true;
  },
  // aviso corto y bilingüe (KhipuToast; sin él, el toast() de app.html) — nunca texto crudo
  _notice(text, kind, id, title) {
    try {
      const T = (typeof window !== 'undefined') ? window.KhipuToast : null;
      if (T && typeof T.show === 'function') { T.show({ id: id, kind: kind || 'info', title: title || 'Khipu', body: text, timeout: 7000 }); return; }
    } catch (e) {}
    try { if (typeof toast === 'function') toast(text); } catch (e) {}
  },

  // el usuario cerró el recorrido (✕ / Esc): el agente deja de narrar; los `next` siguientes → stopped:true
  tourClosed() {
    this._tourSeq = (this._tourSeq || 0) + 1;     // un `next` que estaba esperando no avanza un recorrido nuevo
    this._driveStop();
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return false;
    let ok = false;
    try {
      this.ws.send(JSON.stringify({ type: 'contextual_update', text: '[CONTEXT_UPDATE] {"tour":"closed by the user"}' }));
      ok = true;
    } catch (e) { ok = false; }
    this._narrateEnded(true);                    // solo escuchaba el recorrido: termina la frase y cuelga
    return ok;
  },
  // el usuario habló o interrumpió → el recorrido narrado por la voz queda en pausa
  _tourPauseIfVoice() {
    // solo escuchando no hay micrófono con el que contestar "¿sigo?": el recorrido no se pausa
    if (this._listenOnly) return;
    if (!this._tourVoiceLed()) return;
    this._tourSeq = (this._tourSeq || 0) + 1;   // un `next` que estaba esperando ya no avanza
    try { this._tour().pause(); } catch (e) {}
  },
  // la conversación se cortó → el recorrido sigue en pantalla con sus propios tiempos
  _tourDetach() {
    if (!this._tourVoiceLed()) return;
    this._tourSeq = (this._tourSeq || 0) + 1;
    try { this._tour().voiceAttached(false); } catch (e) {}
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
  // sesión del recorrido (solo escuchar): no dice "Escuchando" — el usuario no está hablando con él
  _NARRATE_LABEL: ['NARRANDO', 'NARRATING', 'Narrando', 'Narrating'],
  _setState(state, text) {
    const lab = (state === 'listen' && this._listenOnly) ? this._NARRATE_LABEL : this._STATE_LABELS[state];
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
    if (this._listenOnly) { this._listenOnlyFail(text); return; }   // sesión del recorrido: recorrido local, sin error de voz
    const narrPending = !!(this._narr && !this._narr.done && !this._narr.started);
    clearTimeout(this._initTimer);
    this._tourDetach();
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
    // la sesión del botón del recorrido (ya con micrófono) falló antes de empezarlo: igual hay recorrido
    if (narrPending) this._narrateFallback('error');
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
      var r = await window._tradeFetch('/api/trade/crypto/assets', { channel: 'voice' }, false);
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
          // paso 5 (INFRA_OPERATIVA §2.5): X-Khipu-Channel = canal de quien llama (voz → 'voice'; Cabina → 'ui').
          // Es metadato: nunca autoriza nada.
          channel: o.channel === 'voice' ? 'voice' : 'ui',
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
