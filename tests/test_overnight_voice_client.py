"""tests/test_overnight_voice_client.py — engine/voice.js contra el protocolo de
ElevenLabs Agents (oct-2026), ejecutado en Node (vm) con dobles:
WebSocket falso, AudioContext falso, micrófono falso, fetch falso y RELOJ
falso (determinista: los topes de herramientas de 60-90 s se prueban al instante).

Cubre: overrides SOLO permitidos y reintento sin overrides ante override_error,
formatos de audio de conversation_initiation_metadata (pcm_24000 / ulaw_8000),
re-muestreo con estado del micrófono (sin deriva), ping→pong,
client_tool_call→client_tool_result (string, is_error false, tope que responde
antes del timeout del agente), interrupción que descarta audio viejo por
event_id, end_call, fallo antes de abrir (suelta el micrófono y explica),
errores de sesión del server en ES/EN, reconexión única tras caída de red.
Se salta si no hay `node`.
"""
import json
import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = shutil.which('node')
pytestmark = pytest.mark.skipif(not NODE, reason='node no instalado')

HARNESS = r"""
const vm = require('vm'), fs = require('fs');
const VOICE = fs.readFileSync(process.argv[1], 'utf8');

function makeEnv(opts) {
  opts = opts || {};
  // ── reloj falso ──
  let now = 0, seq = 0; const timers = new Map();
  const setTimeout_ = (fn, ms) => { const id = ++seq; timers.set(id, { fn, at: now + Math.max(0, +ms || 0) }); return id; };
  const clearTimeout_ = (id) => { timers.delete(id); };
  const flush = async () => { for (let i = 0; i < 20; i++) await Promise.resolve(); };
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
  // ── WebSocket falso ──
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
  // ── audio falso ──
  const ctxs = [];
  class FakeCtx {
    constructor() { this.sampleRate = opts.ctxRate || 48000; this.currentTime = 0; this.state = 'running';
      this.destination = {}; this.buffers = []; this.sources = []; ctxs.push(this); }
    resume() { this.state = 'running'; return Promise.resolve(); }
    createMediaStreamSource() { return { connect() {}, disconnect() {} }; }
    createScriptProcessor() { const p = { connect() {}, disconnect() {}, onaudioprocess: null }; this.proc = p; return p; }
    createGain() { return { gain: { value: 1 }, connect() {}, disconnect() {} }; }
    createBuffer(ch, len, rate) {
      if (opts.minRate && rate < opts.minRate) throw new Error('NotSupportedError: rate');
      const data = new Float32Array(len);
      const b = { length: len, sampleRate: rate, duration: len / rate, getChannelData: () => data };
      this.buffers.push(b); return b;
    }
    createBufferSource() { const s = { connect() {}, start(t) { s.startAt = t; }, stop() { s.stopped = true; }, onended: null }; this.sources.push(s); return s; }
  }
  // ── micrófono falso ──
  const tracks = [];
  const mic = { getUserMedia: async () => {
    if (opts.micError) { const e = new Error('denied'); e.name = opts.micError; throw e; }
    const t = { stopped: false, stop() { this.stopped = true; } }; tracks.push(t);
    return { getTracks: () => [t] };
  } };
  // ── fetch falso ──
  const fetches = [];
  const fetch_ = async (url, init) => {
    fetches.push({ url, body: init && init.body });
    if (url.endsWith('/api/voice/bixby-prompt')) return { ok: true, status: 200, json: async () => (opts.prompt || { system_prompt: 'PROMPT', allow_override: false }) };
    if (url.endsWith('/api/voice/session')) {
      const s = typeof opts.session === 'function' ? opts.session(fetches.length) : opts.session;
      return { ok: (s.status || 200) < 400, status: s.status || 200, json: async () => s.data };
    }
    return { ok: false, status: 404, json: async () => ({}) };
  };
  // ── DOM mínimo ──
  const els = {};
  const el = (id) => els[id] || (els[id] = { id, style: {}, textContent: '', classList: { add() {}, remove() {} } });
  const store = () => { const m = {}; return { getItem: k => (k in m ? m[k] : null), setItem: (k, v) => { m[k] = String(v); }, removeItem: k => { delete m[k]; }, _m: m }; };
  const toasts = [], surfaces = [];
  const ctx = {
    console, Math, JSON, Date, Promise, Float32Array, Int16Array, Uint8Array, Map, Set, Error, String, Number, Array, Object,
    isFinite, parseFloat, parseInt, atob, btoa,
    performance: { now: () => now },
    setTimeout: setTimeout_, clearTimeout: clearTimeout_,
    requestAnimationFrame: (fn) => setTimeout_(fn, 16), cancelAnimationFrame: clearTimeout_,
    WebSocket: FakeWS, AudioContext: FakeCtx,
    navigator: { mediaDevices: mic },
    fetch: fetch_,
    localStorage: store(), sessionStorage: store(),
    document: { hidden: false, getElementById: el, querySelectorAll: () => [], addEventListener() {} },
    toast: (t) => toasts.push(t),
    NODES: [{ id: 'nvidia', label: 'NVIDIA', mkt: 'NVDA', cat: 'fabless' }],
    LINKS: [], MKT: { quotes: {}, pos: {} },
    computeNRS: () => 42, lid: (x) => (x && x.id) || x,
  };
  ctx.window = ctx;
  ctx.NODE_BY_ID = { nvidia: ctx.NODES[0] };
  ctx._surface = (k, a) => { surfaces.push([k, a]); return true; };
  if (opts.lang) ctx.LANG = opts.lang;
  vm.createContext(ctx);
  vm.runInContext(VOICE, ctx, { filename: 'voice.js' });
  const V = ctx.BixbyVoice;
  return { ctx, V, sockets, ctxs, tracks, fetches, toasts, surfaces, errors, advance, els,
           text: () => el('bixby-text').textContent };
}

function b64pcm(samples) {          // Int16 LE → base64
  const b = Buffer.alloc(samples.length * 2);
  samples.forEach((v, i) => b.writeInt16LE(v, i * 2));
  return b.toString('base64');
}
const META = (out, inp) => ({ type: 'conversation_initiation_metadata', conversation_initiation_metadata_event:
  { conversation_id: 'conv_1', agent_output_audio_format: out, user_input_audio_format: inp } });

async function main() {
  const R = {};
  // ═══ 1) sesión normal en inglés: overrides solo permitidos ═══
  {
    const E = makeEnv({ lang: 'en', session: { data: { signed_url: 'wss://api.elevenlabs.io/v1/convai/conversation?agent_id=a&conversation_signature=s',
      overrides: { prompt: false, language: true, first_message: true }, language: 'es', has_first_message: true, override_env: false } } });
    await E.V.connect();
    const ws = E.sockets[0];
    R.url = ws && ws.url;
    R.sessionBody = E.fetches.find(f => f.url.endsWith('/api/voice/session')).body;
    ws._open();
    R.init = ws.sent[0];
    ws._msg(META('pcm_24000', 'pcm_16000'));
    R.outFmt = E.V._outFmt; R.inFmt = E.V._inFmt;
    R.listening = E.text();
    // micrófono: 3 bloques de 2048 a 48 kHz → exactamente 2048 muestras a 16 kHz en total
    const proc = E.ctxs[0].proc;
    let total = 0;
    for (let k = 0; k < 3; k++) {
      const f = new Float32Array(2048); for (let i = 0; i < f.length; i++) f[i] = 0.5 * Math.sin((k * 2048 + i) / 10);
      const before = ws.sent.length;
      proc.onaudioprocess({ inputBuffer: { getChannelData: () => f } });
      for (const m of ws.sent.slice(before)) if (m.user_audio_chunk) total += Buffer.from(m.user_audio_chunk, 'base64').length / 2;
    }
    R.micSamples16k = total;
    // audio del agente a 24 kHz
    ws._msg({ type: 'audio', audio_event: { audio_base_64: b64pcm(new Array(480).fill(1000)), event_id: 5 } });
    const buf = E.ctxs[0].buffers.slice(-1)[0];
    R.playRate = buf.sampleRate; R.playLen = buf.length; R.playVal = Math.round(buf.getChannelData()[0] * 32768);
    // ping → pong
    ws._msg({ type: 'ping', ping_event: { event_id: 7, ping_ms: 30 } });
    R.pong = ws.sent.slice(-1)[0];
    // herramienta
    ws._msg({ type: 'client_tool_call', client_tool_call: { tool_name: 'get_risk_score', tool_call_id: 'tc_1', parameters: { company_name: 'nvidia' }, event_id: 8 } });
    R.toolResult = ws.sent.slice(-1)[0];
    ws._msg({ type: 'client_tool_call', client_tool_call: { tool_name: 'nope_tool', tool_call_id: 'tc_2', parameters: {} } });
    R.unknownTool = ws.sent.slice(-1)[0];
    // interrupción: corta lo agendado y DESCARTA audio viejo
    const srcBefore = E.ctxs[0].sources.slice();
    ws._msg({ type: 'interruption', interruption_event: { event_id: 10 } });
    R.stoppedOnInterrupt = srcBefore.every(s => s.stopped);
    const nb = E.ctxs[0].buffers.length;
    ws._msg({ type: 'audio', audio_event: { audio_base_64: b64pcm([1, 2, 3, 4]), event_id: 9 } });
    R.staleDropped = E.ctxs[0].buffers.length === nb;
    ws._msg({ type: 'audio', audio_event: { audio_base_64: b64pcm([1, 2, 3, 4]), event_id: 11 } });
    R.freshPlayed = E.ctxs[0].buffers.length === nb + 1;
    // herramienta lenta: el tope responde antes del timeout del agente (60 s)
    E.ctx.KhipuChat = { send: () => new Promise(() => {}) };
    ws._msg({ type: 'client_tool_call', client_tool_call: { tool_name: 'ask_khipu_brain', tool_call_id: 'tc_3', parameters: { question: 'q' } } });
    const n0 = ws.sent.length;
    await E.advance(57000);
    R.slowBefore = ws.sent.length - n0;
    await E.advance(2000);
    const slow = ws.sent.slice(n0);
    R.slowAfter = slow.length; R.slowMsg = slow[0];
    await E.advance(60000);
    R.slowOnce = ws.sent.slice(n0).filter(m => m.type === 'client_tool_result').length;
    // end_call: cuelga tras la frase
    ws._msg({ type: 'agent_tool_response', agent_tool_response: { tool_name: 'end_call' } });
    await E.advance(9000);
    R.endCallClosed = ws.closed; R.connectedAfterEnd = E.V.isConnected;
    R.micReleased = E.tracks.every(t => t.stopped);
    R.errors = E.errors;
  }
  // ═══ 2) override rechazado → reintento SIN overrides ═══
  {
    const E = makeEnv({ lang: 'en', session: { data: { signed_url: 'wss://x/1', overrides: { prompt: false, language: true, first_message: false }, language: 'es' } } });
    await E.V.connect();
    const ws1 = E.sockets[0]; ws1._open();
    R.ov1 = ws1.sent[0];
    ws1._msg({ type: 'error', error_event: { code: 1008, error_type: 'override_error', message: "Override for field 'language' is not allowed by config." } });
    ws1._close(1008, "Override for field 'language' is not allowed by config.");
    await E.advance(1000);
    const ws2 = E.sockets[1];
    R.retried = !!ws2;
    if (ws2) { ws2._open(); R.ov2 = ws2.sent[0]; }
    R.noOverrideFlag = E.ctx.sessionStorage.getItem('kh_voice_no_override');
    R.firstMicReleased = E.tracks[0] && E.tracks[0].stopped;
  }
  // ═══ 3) falla ANTES de abrir el socket → suelta micrófono y explica ═══
  {
    const E = makeEnv({ session: { data: { signed_url: 'wss://x/2' } } });
    await E.V.connect();
    E.sockets[0]._close(1006, '');
    await E.advance(10);
    R.preOpen = { micStopped: E.tracks.every(t => t.stopped), connected: E.V.isConnected, text: E.text(), toasts: E.toasts.length,
                  sockets: E.sockets.length };
  }
  // ═══ 4) el server niega la sesión (cuota) → sin socket, mensaje bilingüe ═══
  {
    const E = makeEnv({ lang: 'en', session: { status: 402, data: { error: 'Se acabaron los créditos', error_en: 'Credits are used up',
      fix_en: 'Upgrade at elevenlabs.io', code: 'quota_exceeded' } } });
    await E.V.connect();
    R.sessionErr = { sockets: E.sockets.length, text: E.text(), mic: E.tracks.every(t => t.stopped) };
  }
  // ═══ 5) micrófono denegado ═══
  {
    const E = makeEnv({ micError: 'NotAllowedError', session: { data: { signed_url: 'wss://x' } } });
    await E.V.connect();
    R.micDenied = { text: E.text(), sockets: E.sockets.length, fetches: E.fetches.length };
  }
  // ═══ 6) salida µ-law 8 kHz con Safari que no crea buffers < 22050 ═══
  {
    const E = makeEnv({ minRate: 22050, session: { data: { signed_url: 'wss://x' } } });
    await E.V.connect(); const ws = E.sockets[0]; ws._open();
    ws._msg(META('ulaw_8000', 'ulaw_8000'));
    const A = E.ctx.KhipuVoiceAudio;
    const u = Buffer.from([A.ulawEncode(1000), A.ulawEncode(-1000), A.ulawEncode(0), A.ulawEncode(8000)]);
    ws._msg({ type: 'audio', audio_event: { audio_base_64: u.toString('base64'), event_id: 1 } });
    const b = E.ctxs[0].buffers.slice(-1)[0];
    R.ulaw = { rate: b && b.sampleRate, len: b && b.length,
               roundtrip: [1000, -1000, 0, 8000, -32000].map(v => A.ulawDecode(A.ulawEncode(v))) };
    const proc = E.ctxs[0].proc; const f = new Float32Array(600).fill(0.25);
    const n0 = ws.sent.length; proc.onaudioprocess({ inputBuffer: { getChannelData: () => f } });
    R.ulawMicBytes = Buffer.from(ws.sent[n0].user_audio_chunk, 'base64').length;   // 600 @48k → 100 @8k, 1 byte c/u
  }
  // ═══ 7) caída de red a mitad de conversación → UNA reconexión ═══
  {
    const E = makeEnv({ session: { data: { signed_url: 'wss://x/r' } } });
    await E.V.connect(); const ws1 = E.sockets[0]; ws1._open(); ws1._msg(META('pcm_16000', 'pcm_16000'));
    ws1._close(1006, '');
    await E.advance(2000);
    const ws2 = E.sockets[1]; R.reconnected = !!ws2;
    if (ws2) { ws2._open(); ws2._msg(META('pcm_16000', 'pcm_16000')); ws2._close(1006, ''); }
    await E.advance(2000);
    R.reconnectOnce = E.sockets.length; R.afterSecondDrop = E.text();
  }
  // ═══ 8) init sin respuesta → corta a los 15 s y explica ═══
  {
    const E = makeEnv({ session: { data: { signed_url: 'wss://x/t' } } });
    await E.V.connect(); const ws = E.sockets[0]; ws._open();
    await E.advance(15100);
    R.initTimeout = { closed: ws.closed, };
    ws._close(4000, 'init timeout');
    await E.advance(10);
    R.initTimeout.text = E.text();
  }
  process.stdout.write(JSON.stringify(R));
  process.exit(0);
}
main().catch(e => { process.stdout.write(JSON.stringify({ fatal: String(e && e.stack || e) })); process.exit(0); });
"""


@pytest.fixture(scope='module')
def R():
    p = subprocess.run([NODE, '-e', HARNESS, os.path.join(ROOT, 'engine', 'voice.js')],
                       capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stderr[-2000:]
    out = json.loads(p.stdout)
    assert 'fatal' not in out, out.get('fatal')
    return out


def test_session_request_and_overrides_only_allowed(R):
    assert R['url'].startswith('wss://api.elevenlabs.io/v1/convai/conversation')
    assert R['sessionBody'] in ('{}', None)          # sin preferencia local, no manda agent_id
    init = R['init']
    assert init['type'] == 'conversation_initiation_client_data'
    agent = init['conversation_config_override']['agent']
    assert agent['language'] == 'en' and 'prompt' not in agent        # prompt override NO permitido
    assert agent['first_message'].startswith("Hi, I'm Khipu")
    assert 'dynamic_variables' not in init


def test_metadata_formats_and_mic_resampling(R):
    assert R['outFmt'] == {'format': 'pcm', 'sampleRate': 24000}
    assert R['inFmt'] == {'format': 'pcm', 'sampleRate': 16000}
    assert 'listening' in R['listening'].lower()
    assert R['micSamples16k'] == 2048                 # 3×2048 @48k → 2048 @16k, sin deriva
    assert R['playRate'] == 24000 and R['playLen'] == 480 and R['playVal'] == 1000


def test_ping_pong_and_tool_results(R):
    assert R['pong'] == {'type': 'pong', 'event_id': 7}
    tr = R['toolResult']
    assert tr['type'] == 'client_tool_result' and tr['tool_call_id'] == 'tc_1' and tr['is_error'] is False
    assert isinstance(tr['result'], str)
    body = json.loads(tr['result'])
    assert body['success'] is True and body['company'] == 'NVIDIA' and body['nrs'] == 42
    ut = json.loads(R['unknownTool']['result'])
    assert ut['success'] is False and 'nope_tool' in ut['error'] and R['unknownTool']['is_error'] is False


def test_interruption_drops_stale_audio(R):
    assert R['stoppedOnInterrupt'] and R['staleDropped'] and R['freshPlayed']


def test_slow_tool_answers_before_agent_timeout_once(R):
    assert R['slowBefore'] == 0 and R['slowAfter'] == 1 and R['slowOnce'] == 1
    m = R['slowMsg']
    assert m['tool_call_id'] == 'tc_3'
    body = json.loads(m['result'])
    assert body['pending'] is True and body['success'] is True


def test_end_call_closes_cleanly(R):
    assert R['endCallClosed']['code'] == 1000 and R['connectedAfterEnd'] is False and R['micReleased']
    assert R['errors'] == []


def test_override_error_retries_without_overrides(R):
    assert R['ov1']['conversation_config_override']['agent']['language'] == 'en'
    assert R['retried'] and 'conversation_config_override' not in R['ov2']
    assert R['noOverrideFlag'] == '1' and R['firstMicReleased']


def test_failure_before_open_releases_mic_and_explains(R):
    p = R['preOpen']
    assert p['micStopped'] and p['connected'] is False and p['sockets'] == 1 and p['toasts'] >= 1
    assert 'No se pudo abrir la conexión de voz' in p['text']


def test_server_session_error_is_bilingual(R):
    s = R['sessionErr']
    assert s['sockets'] == 0 and s['mic'] and 'Credits are used up' in s['text'] and 'Upgrade' in s['text']


def test_mic_denied_message(R):
    m = R['micDenied']
    assert 'Permiso de micrófono denegado' in m['text'] and m['sockets'] == 0 and m['fetches'] == 0


def test_ulaw_output_and_input(R):
    u = R['ulaw']
    assert u['rate'] == 48000 and u['len'] == 24       # 4 muestras @8k subidas a 48k (Safari viejo)
    rt = u['roundtrip']
    assert abs(rt[0] - 1000) < 40 and abs(rt[1] + 1000) < 40 and abs(rt[2]) < 10 and abs(rt[3] - 8000) < 300
    assert rt[4] < -30000
    assert R['ulawMicBytes'] == 100


def test_network_drop_reconnects_once(R):
    assert R['reconnected'] and R['reconnectOnce'] == 2
    assert 'desconect' in R['afterSecondDrop'].lower() or 'conexión' in R['afterSecondDrop'].lower()


def test_init_timeout(R):
    assert R['initTimeout']['closed']['code'] == 4000
    assert 'no respondió' in R['initTimeout']['text']
