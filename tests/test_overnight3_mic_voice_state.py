"""tests/test_overnight3_mic_voice_state.py — el micrófono de la Cabina refleja el estado REAL de la voz.

Antes: toggleMic() llamaba BixbyVoice.toggle() y ponía "Escuchando" (clase .on) por su cuenta. Si el usuario
tocaba otra vez MIENTRAS conectaba, toggle() cancelaba la conexión pero el botón seguía encendido; y si la
conexión fallaba (micrófono denegado, sesión rechazada…) también quedaba "on".

Ahora engine/voice.js publica su estado (BixbyVoice.getState() + evento 'khipu:voice' en window:
off | connecting | listening | speaking | thinking | error) y engine/cockpit.js pinta el botón y la píldora
de la barra superior SOLO con eso (ES/EN), nunca "on" tras cancelar o fallar.

1. voice.js en Node (vm) con dobles deterministas: eventos, cancelación mientras conecta (micrófono o sesión
   pendientes), reintento tras cancelar, error con mensaje, reintento agendado cancelable, "Hablando" al sonar
   el audio y la insignia en inglés que ya no queda en "PENSANDO".
2. La Cabina en Chromium (Playwright) con voice.js + cockpit.js reales y getUserMedia / fetch / WebSocket falsos:
   conectar → cancelar mientras conecta → botón apagado; conectar → error → botón apagado con el mensaje.
Se salta lo que necesite `node` o Chromium si no están.
"""
import json
import os
import re
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = shutil.which('node')
VOICE_PATH = os.path.join(ROOT, 'engine', 'voice.js')
COCKPIT_PATH = os.path.join(ROOT, 'engine', 'cockpit.js')
DESKTOP_PATH = os.path.join(ROOT, 'engine', 'desktop.js')
MASCOT_PATH = os.path.join(ROOT, 'engine', 'mascot.js')
TOAST_PATH = os.path.join(ROOT, 'engine', 'toast.js')


def _r(p):
    with open(p, encoding='utf-8') as f:
        return f.read()


# ═══════════════════════════════════ 1. voice.js en Node ═══════════════════════════════════
HARNESS = r"""
const vm = require('vm'), fs = require('fs');
const VOICE = fs.readFileSync(process.argv[1], 'utf8');

function deferred() { let res, rej; const p = new Promise((a, b) => { res = a; rej = b; }); return { p, res, rej }; }

function makeEnv(opts) {
  opts = opts || {};
  let now = 0, seq = 0; const timers = new Map();
  const setTimeout_ = (fn, ms) => { const id = ++seq; timers.set(id, { fn, at: now + Math.max(0, +ms || 0) }); return id; };
  const clearTimeout_ = (id) => { timers.delete(id); };
  const flush = async () => { for (let i = 0; i < 30; i++) await Promise.resolve(); };
  async function advance(ms) {
    const end = now + ms;
    for (;;) {
      await flush();
      let next = null;
      for (const [id, t] of timers) if (t.at <= end && (!next || t.at < next[1].at)) next = [id, t];
      if (!next) break;
      timers.delete(next[0]); now = next[1].at;
      try { next[1].fn(); } catch (e) { errors.push(String(e && e.stack || e)); }
    }
    now = end; await flush();
  }
  const errors = [];
  const sockets = [];
  class FakeWS {
    constructor(url) { this.url = url; this.readyState = 0; this.sent = []; sockets.push(this); }
    send(d) { this.sent.push(JSON.parse(d)); }
    close(code, reason) { this.readyState = 3; this.closed = { code, reason }; }
    _open() { this.readyState = 1; this.onopen && this.onopen(); }
    _msg(o) { this.onmessage && this.onmessage({ data: JSON.stringify(o) }); }
    _close(code, reason) { this.readyState = 3; this.onclose && this.onclose({ code, reason: reason || '' }); }
  }
  FakeWS.OPEN = 1;
  class FakeCtx {
    constructor() { this.sampleRate = 48000; this.currentTime = 0; this.state = 'running'; this.destination = {}; this.sources = []; }
    resume() { this.state = 'running'; return Promise.resolve(); }
    createMediaStreamSource() { return { connect() {}, disconnect() {} }; }
    createScriptProcessor() { const p = { connect() {}, disconnect() {}, onaudioprocess: null }; this.proc = p; return p; }
    createGain() { return { gain: { value: 1 }, connect() {}, disconnect() {} }; }
    createBuffer(ch, len, rate) { const data = new Float32Array(len); return { length: len, sampleRate: rate, duration: len / rate, getChannelData: () => data }; }
    createBufferSource() { const s = { connect() {}, start(t) { s.startAt = t; }, stop() { s.stopped = true; }, onended: null }; this.sources.push(s); return s; }
  }
  // micrófono: cada pedido queda PENDIENTE hasta que la prueba lo resuelva (o falla al instante con opts.micError)
  const tracks = [], micReqs = [];
  const mic = { getUserMedia: () => {
    if (opts.micError) { const e = new Error('denied'); e.name = opts.micError; return Promise.reject(e); }
    const d = deferred(); micReqs.push(d);
    if (!opts.micPending) { const t = { stopped: false, stop() { this.stopped = true; } }; tracks.push(t); d.res({ getTracks: () => [t] }); }
    return d.p;
  } };
  const grantMic = (i) => { const t = { stopped: false, stop() { this.stopped = true; } }; tracks.push(t); micReqs[i].res({ getTracks: () => [t] }); return t; };
  const denyMic = (i, name) => { const e = new Error('denied'); e.name = name; micReqs[i].rej(e); };
  // sesión: inmediata o PENDIENTE (opts.sessionPending)
  const fetches = [], sessReqs = [];
  const fetch_ = (url, init) => {
    fetches.push({ url, body: init && init.body });
    if (url.endsWith('/api/voice/bixby-prompt')) return Promise.resolve({ ok: true, status: 200, json: async () => ({ system_prompt: 'P', allow_override: false }) });
    if (url.endsWith('/api/voice/session')) {
      const s = opts.session || { data: { signed_url: 'wss://x/1' } };
      const mk = () => ({ ok: (s.status || 200) < 400, status: s.status || 200, json: async () => s.data });
      if (opts.sessionPending) { const d = deferred(); sessReqs.push(d); return d.p.then(mk); }
      return Promise.resolve(mk());
    }
    return Promise.resolve({ ok: false, status: 404, json: async () => ({}) });
  };
  const els = {};
  const el = (id) => els[id] || (els[id] = { id, style: {}, textContent: '', classList: { add() {}, remove() {} } });
  const store = () => { const m = {}; return { getItem: k => (k in m ? m[k] : null), setItem: (k, v) => { m[k] = String(v); }, removeItem: k => { delete m[k]; } }; };
  const events = [], toasts = [];
  class CustomEvent_ { constructor(type, init) { this.type = type; this.detail = init && init.detail; } }
  const ctx = {
    console, Math, JSON, Date, Promise, Float32Array, Int16Array, Uint8Array, Map, Set, Error, String, Number, Array, Object,
    isFinite, parseFloat, parseInt, atob, btoa,
    performance: { now: () => now },
    setTimeout: setTimeout_, clearTimeout: clearTimeout_,
    requestAnimationFrame: (fn) => setTimeout_(fn, 16), cancelAnimationFrame: clearTimeout_,
    WebSocket: FakeWS, AudioContext: FakeCtx, CustomEvent: CustomEvent_,
    navigator: { mediaDevices: mic },
    fetch: fetch_,
    localStorage: store(), sessionStorage: store(),
    document: { hidden: false, getElementById: el, querySelectorAll: () => [], addEventListener() {} },
    toast: (t) => toasts.push(t),
    NODES: [], LINKS: [], MKT: { quotes: {}, pos: {} },
  };
  ctx.window = ctx;
  ctx.dispatchEvent = (e) => { if (e && e.type === 'khipu:voice') events.push(e.detail); return true; };
  // como app.html: setBixbyThinking(true) escribe "PENSANDO" fijo en la insignia
  ctx.setBixbyThinking = (on) => { if (on) el('bixby-state-badge').textContent = 'PENSANDO'; };
  if (opts.lang) ctx.LANG = opts.lang;
  vm.createContext(ctx);
  vm.runInContext(VOICE, ctx, { filename: 'voice.js' });
  const V = ctx.BixbyVoice;
  return { ctx, V, sockets, tracks, micReqs, sessReqs, fetches, events, toasts, errors, advance, grantMic, denyMic, flush,
           states: () => events.map(e => e.state), badge: () => el('bixby-state-badge').textContent };
}
const META = { type: 'conversation_initiation_metadata', conversation_initiation_metadata_event:
  { conversation_id: 'c1', agent_output_audio_format: 'pcm_16000', user_input_audio_format: 'pcm_16000' } };

async function main() {
  const R = {};
  // ═══ A) cancelar MIENTRAS se pide el micrófono; luego volver a tocar (el intento viejo no bloquea) ═══
  {
    const E = makeEnv({ micPending: true });
    const p1 = E.V.toggle();                         // tocar → conectando (sincrónico, antes de cualquier await)
    R.a_firstSync = E.states().slice();
    R.a_connecting = E.V.getState();
    await E.V.toggle();                              // tocar otra vez mientras conecta → cancelar
    R.a_afterCancel = { st: E.V.getState(), last: E.events[E.events.length - 1] };
    const p2 = E.V.toggle();                         // tocar de nuevo (el 1.er pedido de micrófono sigue colgado)
    R.a_retry = { st: E.V.getState().state, micReqs: E.micReqs.length };
    const t1 = E.grantMic(0); await E.flush();       // llega tarde el micrófono del intento cancelado
    R.a_staleStopped = t1.stopped; R.a_stillConnecting = E.V.getState().state;
    const t2 = E.grantMic(1); await E.flush(); await p1; await p2;
    R.a_sockets = E.sockets.length; R.a_t2Live = !t2.stopped;
    E.sockets[0]._open(); E.sockets[0]._msg(META);
    R.a_live = E.V.getState();
    R.a_states = E.states();
    R.a_errors = E.errors;
  }
  // ═══ B) cancelar mientras se espera la sesión del server → nada se abre, micrófono suelto ═══
  {
    const E = makeEnv({ sessionPending: true });
    const p = E.V.connect();
    await E.flush();
    R.b_waiting = { st: E.V.getState().state, sess: E.sessReqs.length };
    E.V.toggle();
    R.b_cancel = E.V.getState();
    E.sessReqs[0].res(); await p; await E.advance(20000);
    R.b_end = { st: E.V.getState().state, sockets: E.sockets.length, micStopped: E.tracks.every(t => t.stopped),
                errorEvents: E.events.filter(e => e.state === 'error').length };
  }
  // ═══ C) micrófono denegado → error CON mensaje; el siguiente toque reintenta (no "cuelga") ═══
  {
    const E = makeEnv({ micError: 'NotAllowedError', lang: 'en' });
    await E.V.toggle();
    R.c_err = { st: E.V.getState(), last: E.events[E.events.length - 1], connecting: E.V.isConnecting() };
    const n = E.events.length;
    E.V.toggle();
    R.c_retry = E.events.slice(n).map(e => e.state);
    await E.advance(13000);
    R.c_afterHide = E.V.getState().state;
  }
  // ═══ D) el server niega la sesión → error con el texto del server ═══
  {
    const E = makeEnv({ session: { status: 402, data: { error: 'Se acabaron los créditos', error_en: 'Credits are used up' } } });
    await E.V.connect();
    R.d_err = E.V.getState();
    await E.advance(12100);
    R.d_hidden = { st: E.V.getState().state, last: E.events[E.events.length - 1].state };
  }
  // ═══ E) el permiso se niega DESPUÉS de cancelar → sin error encima de "apagado" ═══
  {
    const E = makeEnv({ micPending: true });
    const p = E.V.toggle();
    E.V.toggle();
    E.denyMic(0, 'NotAllowedError'); await p; await E.flush();
    R.e_end = { st: E.V.getState().state, errorEvents: E.events.filter(e => e.state === 'error').length, toasts: E.toasts.length };
  }
  // ═══ F) reintento agendado (override rechazado) = "conectando"; tocar lo cancela de verdad ═══
  {
    const E = makeEnv({ session: { data: { signed_url: 'wss://x/o', overrides: { language: true }, language: 'es' } }, lang: 'en' });
    await E.V.connect();
    const ws = E.sockets[0]; ws._open();
    ws._msg({ type: 'error', error_event: { error_type: 'override_error', message: 'Override not allowed' } });
    ws._close(1008, 'Override not allowed');
    R.f_retrying = { st: E.V.getState().state, connecting: E.V.isConnecting() };
    await E.V.toggle();
    await E.advance(2000);
    R.f_end = { st: E.V.getState().state, sockets: E.sockets.length };
  }
  // ═══ G) sesión viva: escuchando → hablando (audio) → escuchando → pensando; insignia bilingüe ═══
  {
    const E = makeEnv({ lang: 'en' });
    await E.V.connect(); const ws = E.sockets[0]; ws._open(); ws._msg(META);
    const n0 = E.events.length;
    const b = Buffer.alloc(320); for (let i = 0; i < 160; i++) b.writeInt16LE(800, i * 2);
    ws._msg({ type: 'audio', audio_event: { audio_base_64: b.toString('base64'), event_id: 1 } });
    ws._msg({ type: 'audio', audio_event: { audio_base_64: b.toString('base64'), event_id: 2 } });
    R.g_speak = { st: E.V.getState().state, emitted: E.events.slice(n0).map(e => e.state), badge: E.badge() };
    ws._msg({ type: 'interruption', interruption_event: { event_id: 3 } });
    R.g_listen = E.V.getState().state;
    ws._msg({ type: 'user_transcript', user_transcription_event: { user_transcript: 'what about nvidia' } });
    R.g_think = { st: E.V.getState().state, badge: E.badge(), text: E.V.getState().text };
    E.V.toggle();
    R.g_off = { st: E.V.getState(), last: E.events[E.events.length - 1] };
  }
  console.log(JSON.stringify(R));
}
main().catch(e => { console.error(e && e.stack || e); process.exit(1); });
"""


@pytest.fixture(scope='module')
def voice():
    if not NODE:
        pytest.skip('node no instalado')
    p = subprocess.run([NODE, '-e', HARNESS, VOICE_PATH], capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_voice_cancel_while_requesting_mic_goes_off_and_retaps_reconnect(voice):
    # el primer toque avisa "conectando" en el MISMO instante (la Cabina no tiene que adivinar)
    assert voice['a_firstSync'] == ['connecting']
    assert voice['a_connecting']['state'] == 'connecting' and voice['a_connecting']['connecting'] is True
    # 2.º toque mientras conecta → apagado de verdad (estado + evento)
    st = voice['a_afterCancel']['st']
    assert st['state'] == 'off' and st['connecting'] is False and st['connected'] is False
    assert voice['a_afterCancel']['last']['state'] == 'off' and voice['a_afterCancel']['last']['prev'] == 'connecting'
    # 3.er toque: el intento cancelado (micrófono aún pendiente) NO bloquea uno nuevo
    assert voice['a_retry'] == {'st': 'connecting', 'micReqs': 2}
    # el micrófono que llega tarde del intento cancelado se suelta y no pisa el intento nuevo
    assert voice['a_staleStopped'] is True and voice['a_stillConnecting'] == 'connecting'
    assert voice['a_sockets'] == 1 and voice['a_t2Live'] is True
    assert voice['a_live']['state'] == 'listening' and voice['a_live']['connected'] is True
    # pide micrófono → cancelado → pide micrófono → pide sesión → abre sesión → META → micrófono andando
    assert voice['a_states'] == ['connecting', 'off', 'connecting', 'connecting', 'connecting', 'listening', 'listening']
    assert voice['a_errors'] == []


def test_voice_cancel_while_waiting_session_opens_nothing(voice):
    assert voice['b_waiting'] == {'st': 'connecting', 'sess': 1}
    assert voice['b_cancel']['state'] == 'off' and voice['b_cancel']['connecting'] is False
    assert voice['b_end'] == {'st': 'off', 'sockets': 0, 'micStopped': True, 'errorEvents': 0}


def test_voice_error_carries_message_and_next_tap_reconnects(voice):
    err = voice['c_err']
    assert err['st']['state'] == 'error' and err['connecting'] is False
    assert 'Microphone permission denied' in err['st']['error']               # inglés (LANG=en)
    assert err['last']['state'] == 'error' and err['last']['error'] == err['st']['error']
    assert voice['c_retry'] == ['connecting']                                  # tocar tras un error = reintentar (no colgar)
    # el aviso de error se apaga solo (12 s, como el globo de voice.js)
    assert voice['c_afterHide'] == 'off'
    assert voice['d_err']['state'] == 'error' and 'Se acabaron los créditos' in voice['d_err']['error']
    assert voice['d_hidden'] == {'st': 'off', 'last': 'off'}


def test_voice_denied_after_cancel_shows_no_error(voice):
    assert voice['e_end'] == {'st': 'off', 'errorEvents': 0, 'toasts': 0}


def test_voice_scheduled_retry_counts_as_connecting_and_cancels(voice):
    assert voice['f_retrying'] == {'st': 'connecting', 'connecting': True}
    assert voice['f_end'] == {'st': 'off', 'sockets': 1}                      # el reintento NO revivió la voz


def test_voice_speaking_and_bilingual_badge(voice):
    g = voice['g_speak']
    assert g['st'] == 'speaking' and g['emitted'] == ['speaking'] and g['badge'] == 'SPEAKING'   # una vez por respuesta
    assert voice['g_listen'] == 'listening'
    # setBixbyThinking (app.html) escribía "PENSANDO" encima: en inglés queda "THINKING"
    assert voice['g_think']['st'] == 'thinking' and voice['g_think']['badge'] == 'THINKING'
    assert voice['g_think']['text'] == 'You: what about nvidia'
    assert voice['g_off']['st']['state'] == 'off' and voice['g_off']['last']['prev'] == 'thinking'


# ═══════════════════════════════════ 2. código de la Cabina ═══════════════════════════════════
COCKPIT = _r(COCKPIT_PATH)


def _toggle_mic_src():
    a = COCKPIT.index('  function toggleMic() {')
    return COCKPIT[a:COCKPIT.index('\n  }\n', a)]


def test_cockpit_never_sets_mic_on_by_itself():
    src = _toggle_mic_src()
    # antes: btn.classList.add('on') + setState('live', 'Escuchando') pase lo que pase
    assert "classList.add('on')" not in src and "setState('live'" not in src
    assert "window.addEventListener('khipu:voice', _onVoiceEvent)" in COCKPIT
    # el botón solo se enciende con un estado vivo de la voz
    assert "btn.classList.toggle('on', live)" in COCKPIT
    assert "function _voiceLive(st) { return st === 'listening' || st === 'speaking' || st === 'thinking'; }" in COCKPIT


def test_cockpit_voice_labels_are_bilingual():
    m = re.search(r'var VOICE_LBL = \{(.*?)\n  \};', COCKPIT, re.S)
    assert m
    labels = {k: (es, en) for k, es, en in re.findall(r"(\w+): \['([^']*)', '([^']*)'\]", m.group(1))}
    assert labels['off'] == ('Hablar con Khipu', 'Talk to Khipu')
    assert labels['connecting'] == ('Conectando…', 'Connecting…')
    assert labels['listening'] == ('Escuchando', 'Listening')
    assert labels['speaking'] == ('Hablando', 'Speaking')
    assert labels['thinking'] == ('Pensando', 'Thinking')
    assert labels['error'] == ('Error de voz', 'Voice error')
    assert labels['unavailable'] == ('Voz no disponible', 'Voice unavailable')
    for k, (es, en) in labels.items():
        assert es and en and es != en, k
    assert re.search(r"connecting: \['toca para cancelar', 'tap to cancel'\]", COCKPIT)
    assert re.search(r"error: \['toca para reintentar', 'tap to retry'\]", COCKPIT)


def test_voice_state_labels_table_is_bilingual():
    v = _r(VOICE_PATH)
    m = re.search(r'_STATE_LABELS: \{(.*?)\n  \},', v, re.S)
    rows = re.findall(r"(\w+): \['([^']*)', '([^']*)', '([^']*)', '([^']*)'\]", m.group(1))
    assert {r[0] for r in rows} == {'connect', 'listen', 'speak', 'think', 'error'}
    for k, es_b, en_b, es, en in rows:
        assert es_b and en_b and es and en, k
        if k != 'error':
            assert es_b != en_b and es != en, k
    # el orden importa: setBixbyThinking (que escribe "PENSANDO") ANTES de la insignia bilingüe
    a = v.index('  _setState(state, text) {')
    body = v[a:v.index('\n  },', a)]
    assert body.index('setBixbyThinking') < body.index('this._setBadge(')


# ═══════════════════════════════════ 3. la Cabina en Chromium ═══════════════════════════════════
PAGE = r"""<!doctype html><html lang="es"><head><meta charset="utf-8"><style>html,body{margin:0;height:100%;font-family:system-ui}</style>
</head><body><main id="mainmap" style="display:flex"><div>mapa</div></main>
<script>
window.LANG = 'es';
window.NODES = [{ id: 'Nvidia', label: 'Nvidia', mkt: 'NVDA', cat: 'gpu' }];
window.NODE_BY_ID = { Nvidia: window.NODES[0] }; window.LINKS = []; window.SECTORS9 = {}; window.CAT_TO_SECTOR = {};
window.computeNRS = function () { return 40; };
window.KhipuChat = { appendUser: function () {}, appendPending: function () { return document.createElement('div'); },
  send: function () { return new Promise(function () {}); }, fillReply: function () {}, fillError: function () {},
  classify: function () { return { kind: 'brain' }; }, ensureStyles: function () {}, clear: function () {},
  noteEntity: function () {}, remember: function () {} };
// ── dobles de la voz: micrófono controlable, WebSocket falso, AudioContext mínimo ──
window.__mic = { mode: 'pending', reqs: [] };
// http://khipu.test no es un origen seguro: navigator.mediaDevices no existe → se define el doble entero
Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: { getUserMedia: function () {
  if (window.__mic.mode === 'deny') { var e = new Error('denied'); e.name = 'NotAllowedError'; return Promise.reject(e); }
  return new Promise(function (res, rej) {
    var t = { stopped: false, stop: function () { this.stopped = true; } };
    window.__mic.reqs.push({ t: t, res: function () { res({ getTracks: function () { return [t]; } }); }, rej: rej });
    if (window.__mic.mode === 'grant') res({ getTracks: function () { return [t]; } });
  });
} } });
window.__ws = [];
window.WebSocket = function (url) { this.url = url; this.readyState = 0; this.sent = []; window.__ws.push(this); };
window.WebSocket.OPEN = 1;
window.WebSocket.prototype.send = function (d) { this.sent.push(d); };
window.WebSocket.prototype.close = function () { this.readyState = 3; };
window.AudioContext = function () { this.state = 'running'; this.currentTime = 0; this.sampleRate = 48000; this.destination = {}; };
window.AudioContext.prototype.resume = function () { return Promise.resolve(); };
window.AudioContext.prototype.createMediaStreamSource = function () { return { connect: function () {}, disconnect: function () {} }; };
window.AudioContext.prototype.createScriptProcessor = function () { return { connect: function () {}, disconnect: function () {} }; };
window.AudioContext.prototype.createGain = function () { return { gain: { value: 1 }, connect: function () {}, disconnect: function () {} }; };
</script></body></html>"""
API = {
    '/api/voice/bixby-prompt': {'system_prompt': 'P', 'allow_override': False},
    '/api/voice/session': {'signed_url': 'wss://voice.test/s'},
}
_SNAP = """() => { const b = document.getElementById('bcp-mic'), p = document.getElementById('bcp-state');
  return { cls: b.className, voice: b.getAttribute('data-voice'), pressed: b.getAttribute('aria-pressed'),
           title: b.getAttribute('title'), aria: b.getAttribute('aria-label'),
           pill: p.className, pillTxt: p.querySelector('.txt').textContent, pillTitle: p.getAttribute('title'),
           pillShown: getComputedStyle(p).display !== 'none', vstate: BixbyVoice.getState().state,
           toasts: [...document.querySelectorAll('#kht-stack .kht')].map(t => t.textContent) }; }"""


def _chromium(p):
    for kw in ({}, {'executable_path': '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', 'args': ['--no-sandbox']}):
        try:
            return p.chromium.launch(**kw)
        except Exception:  # noqa: BLE001
            continue
    return None


@pytest.fixture(scope='module')
def browser():
    pw = pytest.importorskip('playwright.sync_api')
    with pw.sync_playwright() as p:
        b = _chromium(p)
        if not b:
            pytest.skip('Chromium no disponible')
        yield b
        b.close()


def _page(browser, lang='es', session=None, dark=False, toast=True):
    c = browser.new_context(viewport={'width': 1440, 'height': 900}, service_workers='block')
    api = dict(API)
    if session is not None:
        api['/api/voice/session'] = session

    def handler(route):
        path = route.request.url[len('http://khipu.test'):].split('?')[0]
        if path in ('', '/'):
            return route.fulfill(status=200, content_type='text/html', body=PAGE.replace("window.LANG = 'es'", "window.LANG = '%s'" % lang))
        if path in api:
            body = api[path]
            st = body.pop('__status', 200) if isinstance(body, dict) else 200
            return route.fulfill(status=st, content_type='application/json', body=json.dumps(body))
        return route.fulfill(status=503, content_type='application/json', body='{"error":"sin servidor"}')
    c.route('http://khipu.test/**', handler)
    pg = c.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://khipu.test/')
    if dark:
        pg.evaluate("document.body.classList.add('dark')")
    for p in ([TOAST_PATH] if toast else []) + [VOICE_PATH, MASCOT_PATH, DESKTOP_PATH, COCKPIT_PATH]:
        pg.add_script_tag(content=_r(p))
    pg.evaluate('BixbyCockpit.open()')
    pg.wait_for_timeout(200)
    return c, pg, errs


def test_navegador_conectar_cancelar_mientras_conecta_boton_apagado(browser):
    c, pg, errs = _page(browser)
    s0 = pg.evaluate(_SNAP)
    assert s0['voice'] == 'off' and 'on' not in s0['cls'].split() and s0['title'] == 'Hablar con Khipu'
    pg.click('#bcp-mic')                                   # 1.er toque: el micrófono queda pidiendo permiso
    s1 = pg.evaluate(_SNAP)
    assert s1['vstate'] == 'connecting' and s1['voice'] == 'connecting'
    assert 'conn' in s1['cls'].split() and 'on' not in s1['cls'].split()
    assert s1['pressed'] == 'true' and s1['title'] == 'Conectando… — toca para cancelar' == s1['aria']
    assert s1['pill'] == 'conn' and s1['pillTxt'] == 'Conectando…' and s1['pillShown']
    pg.click('#bcp-mic')                                   # 2.º toque MIENTRAS conecta → cancelar
    s2 = pg.evaluate(_SNAP)
    assert s2['vstate'] == 'off' and s2['voice'] == 'off'
    for k in ('on', 'conn', 'err'):
        assert k not in s2['cls'].split(), s2
    assert s2['pressed'] == 'false' and s2['title'] == 'Hablar con Khipu'
    assert s2['pill'] == '' and not s2['pillShown']
    # el permiso llega tarde: el intento cancelado no enciende nada ni abre la conexión
    pg.evaluate('() => window.__mic.reqs[0].res()')
    pg.wait_for_timeout(300)
    s3 = pg.evaluate(_SNAP)
    assert s3['voice'] == 'off' and 'on' not in s3['cls'].split() and pg.evaluate('window.__ws.length') == 0
    assert pg.evaluate('window.__mic.reqs[0].t.stopped') is True
    assert not errs, errs
    c.close()


def test_navegador_conectar_error_boton_apagado_con_mensaje(browser):
    c, pg, errs = _page(browser)
    pg.evaluate("() => { window.__mic.mode = 'deny'; }")
    pg.click('#bcp-mic')
    pg.wait_for_timeout(200)
    s = pg.evaluate(_SNAP)
    assert s['vstate'] == 'error' and s['voice'] == 'error'
    assert 'on' not in s['cls'].split() and 'conn' not in s['cls'].split() and 'err' in s['cls'].split()
    assert s['pressed'] == 'false'
    assert s['title'].startswith('Error de voz: Permiso de micrófono denegado') and s['title'].endswith('— toca para reintentar')
    assert s['pill'] == 'err' and s['pillTxt'] == 'Error de voz' and s['pillShown']
    assert s['pillTitle'].startswith('Permiso de micrófono denegado')
    # el globo de voice.js (toast de app.html) queda DEBAJO de Khipus OS: el motivo se ve en KhipuToast
    assert any('Permiso de micrófono denegado' in t for t in s['toasts']), s['toasts']
    # tocar de nuevo = reintentar (y el aviso viejo se va)
    pg.evaluate("() => { window.__mic.mode = 'pending'; }")
    pg.click('#bcp-mic')
    s2 = pg.evaluate(_SNAP)
    assert s2['voice'] == 'connecting' and 'err' not in s2['cls'].split() and s2['pill'] == 'conn'
    assert not errs, errs
    c.close()


def test_navegador_sesion_rechazada_en_ingles(browser):
    c, pg, errs = _page(browser, lang='en', session={'__status': 402, 'error': 'Se acabaron los créditos',
                                                     'error_en': 'Credits are used up', 'fix_en': 'Upgrade your plan'})
    pg.evaluate("() => { window.__mic.mode = 'grant'; }")
    pg.click('#bcp-mic')
    pg.wait_for_timeout(400)
    s = pg.evaluate(_SNAP)
    assert s['vstate'] == 'error' and 'on' not in s['cls'].split() and s['pressed'] == 'false'
    assert s['title'] == 'Voice error: Khipu: Credits are used up — Upgrade your plan — tap to retry'
    assert s['pill'] == 'err' and s['pillTxt'] == 'Voice error'
    assert pg.evaluate('window.__mic.reqs[0].t.stopped') is True          # el micrófono se soltó
    assert not errs, errs
    c.close()


def test_navegador_sesion_viva_hablando_y_colgar(browser):
    c, pg, errs = _page(browser)
    pg.evaluate("() => { window.__mic.mode = 'grant'; }")
    pg.click('#bcp-mic')
    pg.wait_for_function('window.__ws.length === 1')
    pg.evaluate("""() => { const ws = window.__ws[0]; ws.readyState = 1; ws.onopen();
      ws.onmessage({ data: JSON.stringify({ type: 'conversation_initiation_metadata', conversation_initiation_metadata_event:
        { conversation_id: 'c', agent_output_audio_format: 'pcm_16000', user_input_audio_format: 'pcm_16000' } }) }); }""")
    s = pg.evaluate(_SNAP)
    assert s['voice'] == 'listening' and 'on' in s['cls'].split() and s['pressed'] == 'true'
    assert s['title'] == 'Escuchando — toca para colgar' and s['pill'] == 'live' and s['pillTxt'] == 'Escuchando'
    # el chat piensa y termina MIENTRAS la voz escucha: la píldora vuelve a "Escuchando" (antes se escondía)
    pg.evaluate("() => { BixbyCockpit.setState('think', 'Pensando'); }")
    assert pg.evaluate(_SNAP)['pill'] == 'think'
    pg.evaluate("() => { BixbyCockpit.setState('', 'Listo'); }")
    s = pg.evaluate(_SNAP)
    assert s['pill'] == 'live' and s['pillTxt'] == 'Escuchando' and s['pillShown'] and 'on' in s['cls'].split()
    pg.evaluate("""() => window.__ws[0].onmessage({ data: JSON.stringify({ type: 'agent_response',
      agent_response_event: { agent_response: 'Hola, soy Khipu.' } }) })""")
    s = pg.evaluate(_SNAP)
    assert s['voice'] == 'speaking' and s['title'] == 'Hablando — toca para colgar' and s['pillTxt'] == 'Hablando'
    # cambio de idioma con la voz encendida: el botón y la píldora se re-traducen
    pg.evaluate("() => { window.LANG = 'en'; }")
    pg.click('#kos-lang')
    s = pg.evaluate(_SNAP)
    assert s['title'] == 'Speaking — tap to hang up' and s['pillTxt'] == 'Speaking'
    pg.click('#bcp-mic')                                   # colgar
    s = pg.evaluate(_SNAP)
    assert s['voice'] == 'off' and 'on' not in s['cls'].split() and s['title'] == 'Talk to Khipu' and not s['pillShown']
    assert not errs, errs
    c.close()


def test_navegador_cerrar_cabina_cuelga_la_conexion_en_curso(browser):
    c, pg, errs = _page(browser)
    pg.click('#bcp-mic')                                   # conectando (permiso pendiente)
    assert pg.evaluate('BixbyVoice.getState().state') == 'connecting'
    pg.evaluate('BixbyCockpit.close()')
    assert pg.evaluate('BixbyVoice.getState().state') == 'off'
    assert pg.evaluate("document.getElementById('bcp-mic').getAttribute('data-voice')") == 'off'
    assert not errs, errs
    c.close()


def test_navegador_sin_voice_js_dice_voz_no_disponible(browser):
    c = browser.new_context(viewport={'width': 1440, 'height': 900}, service_workers='block')
    c.route('http://khipu.test/**', lambda route: route.fulfill(status=200, content_type='text/html', body=PAGE))
    pg = c.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://khipu.test/')
    for p in (MASCOT_PATH, DESKTOP_PATH, COCKPIT_PATH):
        pg.add_script_tag(content=_r(p))
    pg.evaluate('BixbyCockpit.open()')
    pg.click('#bcp-mic')
    s = pg.evaluate("""() => { const b = document.getElementById('bcp-mic'), p = document.getElementById('bcp-state');
      return { cls: b.className, title: b.title, pill: p.className, txt: p.querySelector('.txt').textContent }; }""")
    assert 'on' not in s['cls'].split() and 'err' in s['cls'].split()
    assert s['title'] == 'Voz no disponible' and s['pill'] == 'err' and s['txt'] == 'Voz no disponible'
    assert not errs, errs
    c.close()
