"""tests/test_voice_tour_narrator.py — el botón «▶ Ver el recorrido de un minuto» con la voz REAL de Khipu (2026-10-12).

Fabrizio: «Cuando aprieto "Ver el recorrido en un minuto", usa la voz antigua. Solo cuando se lo pido por voz, usa la
voz nueva.» Los clips del servidor sonaban a otra voz; ahora el botón abre una sesión de voz de SOLO ESCUCHAR y el
AGENTE narra el recorrido (run_guided_demo), igual que cuando se lo piden hablando.

Contrato del cliente (engine/voice.js + engine/cockpit.js):
  · BixbyVoice.narrateTour(): mismo /api/voice/session + URL firmada + _openSocket que connect(), SIN getUserMedia ni
    user_audio_chunk; con la metadata manda el pedido del recorrido (user_message); SIN user_activity (ElevenLabs
    no deja hablar al agente ~2 s tras cada uno; un vigía de 35 s cuelga la sesión trabada); CONTEXT_UPDATE con
    listen_only:true; nunca "te escucha — habla".
  · 🎙 (toggle) durante esa sesión = hablarle: getUserMedia dentro del clic y el micrófono se suma al MISMO socket.
  · fin del recorrido (done / ✕ / stop) con la sesión aún de solo escuchar → termina la frase y cuelga; con micrófono
    sigue abierta.
  · respaldo: sesión 400/402/502, socket cerrado antes de la metadata, override_error tras su reintento, o sin
    run_guided_demo start a los 9 s → se cuelga y va el recorrido LOCAL (clips → texto) UNA vez, sin duplicar.
  · cockpit demoStart: sin conversación y con la voz contratada → narrateTour() DENTRO del clic y nada local; sin voz
    contratada → local; con conversación (micrófono) → requestTour (como antes).
Node (reloj falso, arnés de tests/test_overnight_voice_client.py) + Chromium con la Cabina REAL y un WebSocket falso.
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

ES_ASK = 'Hazme el recorrido guiado de un minuto.'
EN_ASK = 'Give me the one-minute guided tour.'
ES_NARR = 'Khipu narra el recorrido — toca 🎙 para hablarle'
EN_NARR = 'Khipu is narrating the tour — tap 🎙 to talk to him'
ES_FALLBACK = 'No se pudo conectar la voz en vivo de Khipu: el recorrido sigue sin ella.'
EN_FALLBACK = "Couldn't connect Khipu's live voice: the tour goes on without it."


def _r(*p):
    with open(os.path.join(ROOT, *p), encoding='utf-8') as f:
        return f.read()


# ═══════════════════════════════ estáticas ═══════════════════════════════
def test_static_contract():
    js = _r('engine', 'voice.js')
    ck = _r('engine', 'cockpit.js')
    assert 'narrateTour()' in js and 'upgradeToMic()' in js and 'isListenOnly()' in js and 'isConfigured()' in js
    # SIN user_activity: ElevenLabs no deja hablar al agente ~2 s tras cada uno (pausas en la narración)
    assert "type: 'user_activity'" not in js and 'NARRATE_KEEPALIVE_MS' not in js and 'ctx.listen_only = true' in js
    assert 'const NARRATE_START_MS = 9000' in js
    # la Cabina llama narrateTour en el clic y solo con la voz contratada; el micrófono la "sube", no la cuelga
    assert 'V.narrateTour()' in ck and '_voiceConfigured(V)' in ck and 'V.upgradeToMic' in ck
    assert 'if (opts.fallback && _demo.on) return _tourResult();' in ck
    for s in (js, ck):
        assert 'window.confirm' not in s and 'window.alert' not in s and 'window.prompt(' not in s
    # bilingüe
    assert ES_NARR in js and EN_NARR in js
    assert "'Conectando con la voz de Khipu…', \"Connecting to Khipu's voice…\"" in ck


# ═══════════════════════ voice.js en Node (reloj falso) ═══════════════════════
MAIN = r"""
let CALLN = 0;
function send(ws, name, params) {
  const id = 'tc_' + (++CALLN);
  ws._msg({ type: 'client_tool_call', client_tool_call: { tool_name: name, tool_call_id: id, parameters: params || {} } });
  return id;
}
function results(ws, id) { return ws.sent.filter(x => x.type === 'client_tool_result' && x.tool_call_id === id).map(x => JSON.parse(x.result)); }
async function call(E, ws, name, params, ms) { const id = send(ws, name, params); await E.advance(ms == null ? 60 : ms); return results(ws, id); }
function speak(ws, seconds, eid) {
  ws._msg({ type: 'audio', audio_event: { audio_base_64: b64pcm(new Array(Math.round(16000 * seconds)).fill(800)), event_id: eid || 1 } });
}
// Khipu dijo la frase y ya terminó de sonar (el reloj del AudioContext falso no avanza solo)
function spoke(E, ws, seconds) {
  speak(ws, seconds);
  const c = E.V.audioCtx; c.currentTime = E.V._playCursor + 0.01; E.V._playCursor = 0;
}
function fakeTour(E, steps, opts) {
  opts = opts || {};
  const rec = { start: [], next: 0, stop: [], pause: 0, attached: [] };
  const st = { on: false, i: -1, voice: false, paused: false };
  const T = {
    start: (o) => { rec.start.push(o); st.on = true; st.i = 0; st.voice = !!(o && o.voice); return { step: 1, of: steps.length, say: steps[0] }; },
    next: () => { rec.next++; if (st.i + 1 >= steps.length) { st.on = false; return { done: true }; } st.i++; return { step: st.i + 1, of: steps.length, say: steps[st.i] }; },
    stop: (r) => { rec.stop.push(r); st.on = false; },
    pause: () => { rec.pause++; st.paused = true; },
    state: () => ({ on: st.on, i: st.i, of: steps.length, voice: st.voice, paused: st.paused, premium: false, say: st.on ? steps[st.i] : null }),
    voiceAttached: (v) => { rec.attached.push(v); st.voice = !!v; },
  };
  E.ctx.BixbyCockpit = { tour: T };
  return { rec, st };
}
// el arnés + contador de getUserMedia + "voz contratada" — con la FORMA de app.html: `Keys` vive dentro del IIFE
// de v8 y solo existe como window.V8.Keys (un `Keys` global escondía que en la app real el botón no narraba)
function env(opts) {
  const E = makeEnv(opts);
  E.gum = 0;
  const md = E.ctx.navigator.mediaDevices, g0 = md.getUserMedia;
  md.getUserMedia = function () { E.gum++; return g0.apply(this, arguments); };
  E.ctx.V8 = { Keys: { has: (k) => k === 'elevenlabs' } };
  return E;
}
const kinds = (ws) => ws.sent.map(m => m.type || (m.user_audio_chunk ? 'user_audio_chunk' : '?'));
const ctxOf = (m) => JSON.parse(m.text.slice('[CONTEXT_UPDATE] '.length));
const S = { data: { signed_url: 'wss://api.elevenlabs.io/v1/convai/conversation?agent_id=a&conversation_signature=s', overrides: {}, language: 'es' } };
const STEPS = ['Uno.', 'Dos.', 'Tres.'];

async function narrate(E) {
  let res = null;
  const p = E.V.narrateTour(); p.then(r => { res = r; });
  const sync = { ctxs: E.ctxs.length, listenOnly: E.V.isListenOnly(), gum: E.gum };
  await E.advance(20);
  return { p, sync, res: () => res };
}

async function main() {
  const R = {};
  {   // ── el camino feliz: solo escuchar → el agente lo narra → done → cuelga cuando terminó de sonar ──
    const E = env({ session: S }); const { rec } = fakeTour(E, STEPS);
    R.configured = E.V.isConfigured();
    const N = await narrate(E);
    R.sync = N.sync;
    R.sockets = E.sockets.length;
    const ws = E.sockets[0]; ws._open();
    R.initKinds = kinds(ws);
    ws._msg(META('pcm_16000', 'pcm_16000'));
    R.afterMeta = ws.sent.slice(1);
    R.overlay = E.text();
    R.stateMeta = E.V.getState();
    R.status = E.els['bixby-state-badge'] ? E.els['bixby-state-badge'].textContent : null;
    await E.advance(1000);
    R.start = await call(E, ws, 'run_guided_demo', { action: 'start' });
    R.startCalls = rec.start.slice();
    await E.advance(500);
    R.ctxStart = ws.sent.filter(m => m.type === 'contextual_update').map(ctxOf).pop();
    R.res = N.res();
    // nada de user_activity (pausaría al agente ~2 s cada vez) ni de audio del usuario
    const ua0 = ws.sent.filter(m => m.type === 'user_activity').length;
    await E.advance(15000);
    R.uaIn15 = ws.sent.filter(m => m.type === 'user_activity').length - ua0;
    R.uaTotal = ws.sent.filter(m => m.type === 'user_activity').length;
    R.after9s = rec.start.length;                                  // empezó a tiempo: el respaldo NO corre
    spoke(E, ws, 0.3);
    R.n2 = await call(E, ws, 'run_guided_demo', { action: 'next' }, 900);
    spoke(E, ws, 0.3);
    R.n3 = await call(E, ws, 'run_guided_demo', { action: 'next' }, 900);
    spoke(E, ws, 0.3);
    const idDone = send(ws, 'run_guided_demo', { action: 'next' });
    await E.advance(800);
    R.done = results(ws, idDone);
    R.closedRightAfterDone = !!ws.closed;
    await E.advance(600);
    R.closedAfter = ws.closed || null;
    R.connectedAfter = E.V.isConnected;
    R.stateAfter = E.V.getState();
    const uaEnd = ws.sent.filter(m => m.type === 'user_activity').length;
    await E.advance(12000);
    R.uaAfterEnd = ws.sent.filter(m => m.type === 'user_activity').length - uaEnd;
    R.gum = E.gum; R.tracks = E.tracks.length;
    R.audioChunks = ws.sent.filter(m => m.user_audio_chunk).length;
    R.localStarts = rec.start.filter(o => o && o.fallback).length;
    R.errors = E.errors; R.toasts = E.toasts.slice();
  }
  {   // ── ✕ durante el recorrido: la frase en curso termina y cuelga ──
    const E = env({ session: S }); const { st } = fakeTour(E, STEPS);
    await narrate(E);
    const ws = E.sockets[0]; ws._open(); ws._msg(META('pcm_16000', 'pcm_16000'));
    await call(E, ws, 'run_guided_demo', { action: 'start' });
    speak(ws, 2.0);                                                // Khipu está diciendo 2 s de frase
    st.on = false;                                                 // la Cabina cerró el recorrido (demoStop 'user')…
    R.closeSent = E.V.tourClosed();                                // …y avisa
    R.closeMsg = ws.sent.filter(m => m.type === 'contextual_update').pop();
    await E.advance(1000);
    R.xMid = { closed: !!ws.closed, connected: E.V.isConnected };
    await E.advance(1600);
    R.xEnd = { closed: ws.closed || null, connected: E.V.isConnected };
    R.errorsX = E.errors;
  }
  {   // ── stop del agente en solo escuchar → cuelga ──
    const E = env({ session: S }); fakeTour(E, STEPS);
    await narrate(E);
    const ws = E.sockets[0]; ws._open(); ws._msg(META('pcm_16000', 'pcm_16000'));
    await call(E, ws, 'run_guided_demo', { action: 'start' });
    R.stop = await call(E, ws, 'run_guided_demo', { action: 'stop' }, 1000);
    R.stopClosed = ws.closed || null;
    R.errorsStop = E.errors;
  }
  {   // ── 🎙 durante el recorrido = hablarle: getUserMedia una vez, mismo socket, sigue abierta tras done ──
    const E = env({ session: S }); const { rec } = fakeTour(E, STEPS);
    await narrate(E);
    const ws = E.sockets[0]; ws._open(); ws._msg(META('pcm_16000', 'pcm_16000'));
    await call(E, ws, 'run_guided_demo', { action: 'start' });
    await E.advance(5100);
    const ua0 = ws.sent.filter(m => m.type === 'user_activity').length;
    const up = E.V.toggle();
    R.upGumSync = E.gum;                                           // pedido DENTRO del clic (antes de cualquier await)
    R.upRes = await up;
    await E.advance(20);
    R.upListenOnly = E.V.isListenOnly();
    R.upSockets = E.sockets.length;
    R.upOverlay = E.text();
    R.upState = E.V.getState();
    // el micrófono manda audio por el MISMO socket
    const proc = E.ctxs[0].proc;
    R.hasProc = !!(proc && proc.onaudioprocess);
    if (proc && proc.onaudioprocess) proc.onaudioprocess({ inputBuffer: { getChannelData: () => new Float32Array(4800).fill(0.1) } });
    R.upChunks = ws.sent.filter(m => m.user_audio_chunk).length;
    await E.advance(12000);
    R.upUaAfter = ws.sent.filter(m => m.type === 'user_activity').length - ua0;
    R.upCtx = ws.sent.filter(m => m.type === 'contextual_update').map(ctxOf).pop();
    spoke(E, ws, 0.3); await call(E, ws, 'run_guided_demo', { action: 'next' }, 900);
    spoke(E, ws, 0.3); await call(E, ws, 'run_guided_demo', { action: 'next' }, 900);
    R.upDone = await call(E, ws, 'run_guided_demo', { action: 'next' }, 4500);
    await E.advance(10000);
    R.upAfterDone = { closed: !!ws.closed, connected: E.V.isConnected };
    R.upGum = E.gum;
    R.upLocal = rec.start.filter(o => o && o.fallback).length;
    R.errorsUp = E.errors;
  }
  {   // ── 🎙 ANTES de la metadata: el micrófono arranca con ella y el pedido del recorrido igual sale ──
    const E = env({ session: S }); const { rec } = fakeTour(E, STEPS);
    await narrate(E);
    const ws = E.sockets[0]; ws._open();
    R.earlyUp = await E.V.toggle();
    ws._msg(META('pcm_16000', 'pcm_16000'));
    await E.advance(20);
    R.early = { gum: E.gum, listenOnly: E.V.isListenOnly(), asked: ws.sent.filter(m => m.type === 'user_message'),
                proc: !!(E.ctxs[0].proc && E.ctxs[0].proc.onaudioprocess), overlay: E.text() };
    await call(E, ws, 'run_guided_demo', { action: 'start' });
    await E.advance(12000);
    R.early.local = rec.start.filter(o => o && o.fallback).length;
    R.early.connected = E.V.isConnected;
    R.errorsEarly = E.errors;
  }
  {   // ── 🎙 con el permiso denegado: sigue solo escuchando y muestra el error bilingüe de siempre ──
    const E = env({ session: S, micError: 'NotAllowedError' }); fakeTour(E, STEPS);
    await narrate(E);
    const ws = E.sockets[0]; ws._open(); ws._msg(META('pcm_16000', 'pcm_16000'));
    await call(E, ws, 'run_guided_demo', { action: 'start' });
    R.denyRes = await E.V.toggle();
    await E.advance(20);
    R.deny = { gum: E.gum, listenOnly: E.V.isListenOnly(), connected: E.V.isConnected, closed: !!ws.closed, toasts: E.toasts.slice(),
               state: E.V.getState().state };
    R.errorsDeny = E.errors;
  }
  {   // ── la sesión de solo escuchar se corta a mitad del recorrido: NO reconecta; el recorrido sigue en pantalla ──
    const E = env({ session: S }); const { rec } = fakeTour(E, STEPS);
    await narrate(E);
    const ws = E.sockets[0]; ws._open(); ws._msg(META('pcm_16000', 'pcm_16000'));
    await call(E, ws, 'run_guided_demo', { action: 'start' });
    ws._close(1006, '');
    await E.advance(3000);
    R.drop = { sockets: E.sockets.length, attached: rec.attached.slice(), state: E.V.getState().state, toasts: E.toasts.slice(),
               local: rec.start.filter(o => o && o.fallback).length };
    R.errorsDrop = E.errors;
  }
  // ── respaldos: el recorrido LOCAL, una sola vez ──
  R.fb = {};
  for (const status of [400, 402, 502]) {
    const E = env({ session: { status, data: { error: 'ElevenLabs dijo algo crudo ' + status, error_en: 'raw upstream ' + status } } });
    const { rec } = fakeTour(E, STEPS);
    const N = await narrate(E);
    await E.advance(30000);
    R.fb[status] = { starts: rec.start, sockets: E.sockets.length, res: N.res(), state: E.V.getState().state,
                     listenOnly: E.V.isListenOnly(), toasts: E.toasts.slice(), gum: E.gum, errors: E.errors };
  }
  {   // el socket se cierra antes de la metadata
    const E = env({ session: S }); const { rec } = fakeTour(E, STEPS);
    const N = await narrate(E);
    const ws = E.sockets[0]; ws._open(); ws._close(1006, '');
    await E.advance(30000);
    R.fb.preMeta = { starts: rec.start, sockets: E.sockets.length, res: N.res(), state: E.V.getState().state, errors: E.errors };
  }
  {   // cuota de ElevenLabs (cierra con el motivo) antes de empezar
    const E = env({ session: S }); const { rec } = fakeTour(E, STEPS);
    await narrate(E);
    const ws = E.sockets[0]; ws._open(); ws._msg(META('pcm_16000', 'pcm_16000'));
    ws._close(1002, 'Quota exceeded');
    await E.advance(30000);
    R.fb.quota = { starts: rec.start, sockets: E.sockets.length, toasts: E.toasts.slice(), errors: E.errors };
  }
  {   // override_error → UN reintento sin overrides → otra vez cerrado → recorrido local
    const E = env({ session: { data: Object.assign({}, S.data, { overrides: { language: true }, language: 'es' }) }, lang: 'en' });
    const { rec } = fakeTour(E, STEPS);
    await narrate(E);
    const ws1 = E.sockets[0]; ws1._open();
    R.ovFirstInit = ws1.sent[0];
    ws1._lastErr = 1;
    ws1._msg({ type: 'error', error_event: { error_type: 'override_error', message: 'override not allowed' } });
    ws1._close(1008, 'override not allowed');
    await E.advance(200);
    const ws2 = E.sockets[1];
    R.ovSecond = ws2 ? { url: ws2.url } : null;
    if (ws2) { ws2._open(); ws2._close(1008, 'Policy violation'); }
    await E.advance(30000);
    R.fb.override = { starts: rec.start, sockets: E.sockets.length, toasts: E.toasts.slice(), errors: E.errors,
                      secondInit: ws2 ? ws2.sent[0] : null };
  }
  {   // el agente no llama run_guided_demo start en 9 s → recorrido local, una vez (aunque después lo llame)
    const E = env({ session: S }); const { rec } = fakeTour(E, STEPS);
    const N = await narrate(E);
    const ws = E.sockets[0]; ws._open(); ws._msg(META('pcm_16000', 'pcm_16000'));
    await E.advance(8800);
    R.fb.t88 = { starts: rec.start.length, closed: !!ws.closed };
    await E.advance(400);
    R.fb.noStart = { starts: rec.start.slice(), closed: ws.closed || null, connected: E.V.isConnected, res: N.res(),
                     state: E.V.getState().state };
    // un start tardío del socket viejo se ignora; nada se repite
    send(ws, 'run_guided_demo', { action: 'start' });
    await E.advance(30000);
    R.fb.noStartLater = rec.start.length;
    R.fb.noStartErrors = E.errors;
  }
  {   // el socket ni abre → a los 20 s del clic
    const E = env({ session: S }); const { rec } = fakeTour(E, STEPS);
    await narrate(E);
    await E.advance(19000);
    R.fb.hang19 = rec.start.length;
    await E.advance(1500);
    R.fb.hang = { starts: rec.start.slice(), wsClosed: E.sockets[0] ? (E.sockets[0].closed || null) : 'none', errors: E.errors };
  }
  {   // sin doble recorrido: si ya hay uno en marcha cuando vence el plazo, no se arma otro
    const E = env({ session: S }); const { rec, st } = fakeTour(E, STEPS);
    await narrate(E);
    const ws = E.sockets[0]; ws._open(); ws._msg(META('pcm_16000', 'pcm_16000'));
    st.on = true; st.i = 0;
    await E.advance(10000);
    R.fb.already = { starts: rec.start.length, closed: !!ws.closed };
    // doble clic: el MISMO pedido (un solo socket)
    R.errorsAlready = E.errors;
  }
  {   // doble clic = el mismo pedido; con una conversación con micrófono abierta → requestTour, sin socket nuevo
    const E = env({ session: S }); fakeTour(E, STEPS);
    const p1 = E.V.narrateTour(), p2 = E.V.narrateTour();
    R.dbl = { same: p1 === p2 };
    await E.advance(20);
    R.dbl.sockets = E.sockets.length;
    E.V.disconnect();
    await E.V.connect();
    const ws = E.sockets[E.sockets.length - 1]; ws._open(); ws._msg(META('pcm_16000', 'pcm_16000'));
    const n0 = ws.sent.length, nSock = E.sockets.length;
    let r = null; E.V.narrateTour().then(x => { r = x; });
    await E.advance(20);
    R.dbl.mic = { res: r, sent: ws.sent.slice(n0).filter(m => !m.user_audio_chunk), sockets: E.sockets.length - nSock, listenOnly: E.V.isListenOnly() };
    R.errorsDbl = E.errors;
  }
  {   // inglés
    const E = env({ session: S, lang: 'en' }); fakeTour(E, STEPS);
    await narrate(E);
    const ws = E.sockets[0]; ws._open(); ws._msg(META('pcm_16000', 'pcm_16000'));
    R.en = { ask: ws.sent.filter(m => m.type === 'user_message'), overlay: E.text() };
    const E2 = env({ session: { status: 402, data: { error: 'x' } }, lang: 'en' }); fakeTour(E2, STEPS);
    await narrate(E2); await E2.advance(100);
    R.en.toasts = E2.toasts.slice();
    // sin la voz contratada: isConfigured() = false
    delete E2.ctx.V8;
    R.en.unconfigured = E2.V.isConfigured();
    E2.ctx.V8 = { Keys: { has: () => false } };
    R.en.notConfigured = E2.V.isConfigured();
    R.errorsEn = E.errors.concat(E2.errors);
  }
  process.stdout.write(JSON.stringify(R));
  process.exit(0);
}
main().catch(e => { process.stdout.write(JSON.stringify({ fatal: String(e && e.stack || e) })); process.exit(0); });
"""


@pytest.fixture(scope='module')
def V():
    if not NODE:
        pytest.skip('node no instalado')
    from tests import test_overnight_voice_client as vc
    harness = vc.HARNESS.split('async function main()')[0] + MAIN
    p = subprocess.run([NODE, '-e', harness, VOICE_PATH], capture_output=True, text=True, timeout=180)
    assert p.returncode == 0, p.stderr[-3000:]
    out = json.loads(p.stdout)
    assert 'fatal' not in out, out.get('fatal')
    for k in ('errors', 'errorsX', 'errorsStop', 'errorsUp', 'errorsDeny', 'errorsEarly', 'errorsDrop', 'errorsAlready', 'errorsDbl', 'errorsEn'):
        assert out[k] == [], (k, out[k])
    return out


def test_narrate_opens_the_socket_without_microphone(V):
    assert V['configured'] is True
    # síncrono, dentro del clic: el AudioContext (reproducción) ya existe y la sesión ya es de solo escuchar
    assert V['sync'] == {'ctxs': 1, 'listenOnly': True, 'gum': 0}
    assert V['sockets'] == 1
    assert V['initKinds'] == ['conversation_initiation_client_data']
    assert V['gum'] == 0 and V['tracks'] == 0 and V['audioChunks'] == 0      # nunca micrófono ni audio del usuario


def test_narrate_asks_the_agent_after_metadata_with_listen_only_context(V):
    after = V['afterMeta']
    assert [m['type'] for m in after] == ['contextual_update', 'user_message']
    ctx = json.loads(after[0]['text'][len('[CONTEXT_UPDATE] '):])
    assert ctx['listen_only'] is True
    assert after[1] == {'type': 'user_message', 'text': ES_ASK}
    assert V['ctxStart']['listen_only'] is True and V['ctxStart']['tour']['on'] is True
    # estado visible: "Khipu narra el recorrido — toca 🎙 para hablarle", nunca "te escucha — habla"
    assert V['overlay'] == ES_NARR and 'habla' not in V['overlay'].replace('hablarle', '')
    assert V['stateMeta']['state'] == 'listening' and V['stateMeta']['listenOnly'] is True
    assert V['status'] == 'NARRANDO'


def test_narrate_keeps_the_turn_alive_every_5s(V):
    assert V['uaIn15'] == 0 and V['uaTotal'] == 0                            # sin user_activity: no pausa al agente
    assert V['uaAfterEnd'] == 0                                             # colgó: se acabó el user_activity


def test_voice_led_tour_then_hang_up_after_the_audio(V):
    assert V['start'][0]['success'] is True and V['start'][0]['step'] == 1
    assert V['startCalls'] == [{'voice': True}] and V['res'] == 'voice'
    assert V['after9s'] == 1 and V['localStarts'] == 0                     # empezó a tiempo: nada local
    assert V['n2'][0]['step'] == 2 and V['n3'][0]['step'] == 3
    assert V['done'] == [{'success': True, 'done': True, 'note': 'Tour finished: stay quiet and wait.'}]
    assert V['closedRightAfterDone'] is False                              # no corta en seco: deja sonar lo último
    assert V['closedAfter'] and V['closedAfter']['code'] == 1000
    assert V['connectedAfter'] is False and V['stateAfter']['state'] == 'off' and V['stateAfter']['listenOnly'] is False
    assert V['toasts'] == []


def test_close_with_x_lets_the_line_finish_then_hangs_up(V):
    assert V['closeSent'] is True
    assert V['closeMsg'] == {'type': 'contextual_update', 'text': '[CONTEXT_UPDATE] {"tour":"closed by the user"}'}
    assert V['xMid'] == {'closed': False, 'connected': True}                # la frase (2 s) sigue sonando
    assert V['xEnd']['closed'] and V['xEnd']['connected'] is False


def test_agent_stop_hangs_up_a_listen_only_session(V):
    assert V['stop'] == [{'success': True, 'stopped': True}]
    assert V['stopClosed'] and V['stopClosed']['code'] == 1000


def test_mic_button_upgrades_instead_of_hanging_up(V):
    assert V['upGumSync'] == 1 and V['upRes'] is True and V['upGum'] == 1    # getUserMedia una vez, dentro del clic
    assert V['upListenOnly'] is False and V['upSockets'] == 1                # el MISMO socket
    assert V['upOverlay'] == '🎙️ Khipu te escucha — habla'
    assert V['upState']['listenOnly'] is False and V['upState']['connected'] is True
    assert V['hasProc'] is True and V['upChunks'] >= 1                       # ahora sí sale audio del usuario
    assert V['upUaAfter'] == 0                                               # ya no hace falta user_activity
    assert 'listen_only' not in V['upCtx']
    assert V['upDone'][0]['done'] is True
    assert V['upAfterDone'] == {'closed': False, 'connected': True}         # conversación normal: sigue abierta
    assert V['upLocal'] == 0


def test_mic_before_metadata_still_asks_for_the_tour(V):
    e = V['early']
    assert V['earlyUp'] is True and e['gum'] == 1 and e['listenOnly'] is False and e['proc'] is True
    assert e['asked'] == [{'type': 'user_message', 'text': ES_ASK}]
    assert e['overlay'] == '🎙️ Khipu te escucha — habla'
    assert e['local'] == 0 and e['connected'] is True


def test_mic_denied_stays_listen_only_with_the_bilingual_error(V):
    d = V['deny']
    assert V['denyRes'] is False
    assert d['gum'] == 1 and d['listenOnly'] is True and d['connected'] is True and d['closed'] is False
    assert d['state'] != 'error'
    assert any('Permiso de micrófono denegado' in t for t in d['toasts']), d['toasts']


def test_drop_mid_tour_does_not_reconnect_and_tour_continues(V):
    d = V['drop']
    assert d['sockets'] == 1 and d['attached'] == [False] and d['state'] == 'off' and d['local'] == 0
    assert d['toasts'] == ['Se cortó la voz de Khipu: el recorrido sigue en pantalla.']


@pytest.mark.parametrize('status', ['400', '402', '502'])
def test_session_error_falls_back_to_the_local_tour_once(V, status):
    f = V['fb'][status]
    assert f['starts'] == [{'fallback': True}], f                          # clips → texto (lo decide la Cabina), una vez
    assert f['sockets'] == 0 and f['res'] == 'local' and f['gum'] == 0
    assert f['state'] == 'off' and f['listenOnly'] is False                 # sin pantalla de "error de voz"
    assert f['toasts'] == [ES_FALLBACK]                                     # corto y bilingüe, nunca el texto crudo
    assert f['errors'] == []


def test_socket_closed_before_metadata_falls_back(V):
    f = V['fb']['preMeta']
    assert f['starts'] == [{'fallback': True}] and f['sockets'] == 1 and f['res'] == 'local' and f['state'] == 'off'
    assert f['errors'] == []
    q = V['fb']['quota']
    assert q['starts'] == [{'fallback': True}] and q['sockets'] == 1 and q['toasts'] == [ES_FALLBACK] and q['errors'] == []


def test_override_error_retries_once_then_falls_back(V):
    assert 'conversation_config_override' in V['ovFirstInit']
    assert V['ovSecond'] is not None
    f = V['fb']['override']
    assert f['sockets'] == 2 and f['starts'] == [{'fallback': True}] and f['errors'] == []
    assert 'conversation_config_override' not in f['secondInit']           # el reintento, sin overrides
    assert f['toasts'] == [EN_FALLBACK]


def test_no_tool_call_in_9s_falls_back_exactly_once(V):
    f = V['fb']
    assert f['t88'] == {'starts': 0, 'closed': False}
    ns = f['noStart']
    assert ns['starts'] == [{'fallback': True}] and ns['closed'] and ns['connected'] is False
    assert ns['res'] == 'local' and ns['state'] == 'off'
    assert f['noStartLater'] == 1 and f['noStartErrors'] == []
    assert f['hang19'] == 0 and f['hang']['starts'] == [{'fallback': True}] and f['hang']['errors'] == []
    assert f['already'] == {'starts': 0, 'closed': True}                   # había un recorrido en marcha: no se duplica


def test_double_click_and_open_mic_conversation(V):
    assert V['dbl']['same'] is True and V['dbl']['sockets'] == 1
    m = V['dbl']['mic']
    assert m['res'] == 'requested' and m['sockets'] == 0 and m['listenOnly'] is False
    assert m['sent'] == [{'type': 'user_message', 'text': ES_ASK}]


def test_english(V):
    assert V['en']['ask'] == [{'type': 'user_message', 'text': EN_ASK}]
    assert V['en']['overlay'] == EN_NARR
    assert V['en']['toasts'] == [EN_FALLBACK]
    assert V['en']['unconfigured'] is False and V['en']['notConfigured'] is False


# ═══════════════════════ la Cabina REAL en Chromium (WebSocket falso) ═══════════════════════
FAKE_WS = r"""
(function () {
  window.__ws = [];
  window.__gum = 0;
  function FakeWS(url) {
    this.url = url; this.readyState = 0; this.sent = []; window.__ws.push(this);
  }
  FakeWS.CONNECTING = 0; FakeWS.OPEN = 1; FakeWS.CLOSING = 2; FakeWS.CLOSED = 3;
  FakeWS.prototype.send = function (d) { this.sent.push(JSON.parse(d)); };
  FakeWS.prototype.close = function (code, reason) {
    if (this.readyState === 3) return;
    this.readyState = 3; this.closed = { code: code, reason: reason };
    var self = this; setTimeout(function () { self.onclose && self.onclose({ code: code || 1000, reason: reason || '' }); }, 0);
  };
  FakeWS.prototype._open = function () { this.readyState = 1; this.onopen && this.onopen(); };
  FakeWS.prototype._msg = function (o) { this.onmessage && this.onmessage({ data: JSON.stringify(o) }); };
  window.WebSocket = FakeWS;
  if (!navigator.mediaDevices) { try { Object.defineProperty(navigator, 'mediaDevices', { value: {}, configurable: true }); } catch (e) {} }
  navigator.mediaDevices.getUserMedia = function () { window.__gum++; return Promise.reject(Object.assign(new Error('no'), { name: 'NotAllowedError' })); };
})();
"""

DRIVE = r"""async ({ lang }) => {
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));
  const waitFor = async (fn, ms) => { const t0 = Date.now(); while (!fn()) { if (Date.now() - t0 > ms) return false; await sleep(30); } return true; };
  const out = { steps: [], says: [] };
  out.socket = await waitFor(() => window.__ws.length === 1, 3000);
  const ws = window.__ws[0];
  ws._open();
  ws._msg({ type: 'conversation_initiation_metadata', conversation_initiation_metadata_event:
    { conversation_id: 'c', agent_output_audio_format: 'pcm_16000', user_input_audio_format: 'pcm_16000' } });
  await sleep(50);
  out.asked = ws.sent.filter(m => m.type === 'user_message');
  out.ctx = ws.sent.filter(m => m.type === 'contextual_update').map(m => JSON.parse(m.text.slice(17)));
  out.pill = (document.querySelector('#bcp-state .txt') || {}).textContent || '';
  out.mic = (document.getElementById('bcp-mic') || { getAttribute: () => '' }).getAttribute('title');
  let n = 0;
  const tool = async (params) => {
    const id = 'tc' + (++n);
    ws._msg({ type: 'client_tool_call', client_tool_call: { tool_name: 'run_guided_demo', tool_call_id: id, parameters: params } });
    await waitFor(() => ws.sent.some(m => m.type === 'client_tool_result' && m.tool_call_id === id), 8000);
    const r = ws.sent.find(m => m.type === 'client_tool_result' && m.tool_call_id === id);
    return r ? JSON.parse(r.result) : null;
  };
  // 0,1 s de "voz" del agente por frase (PCM16 a 16 kHz): `next` responde cuando terminó de sonar
  const pcm = (() => { const b = new Uint8Array(3200); for (let i = 0; i < b.length; i += 2) { b[i] = 0x20; b[i + 1] = 0x03; } let s = ''; b.forEach(x => { s += String.fromCharCode(x); }); return btoa(s); })();
  let r = await tool({ action: 'start' });
  for (let guard = 0; r && !r.done && guard < 30; guard++) {
    out.steps.push(r.step); out.says.push(r.say);
    out.shown = (document.querySelector('#bcp-demotxt .bcp-demosr') || {}).textContent;
    if (out.shown !== r.say) out.mismatch = (out.mismatch || 0) + 1;
    ws._msg({ type: 'audio', audio_event: { audio_base_64: pcm, event_id: 1 } });
    r = await tool({ action: 'next' });
  }
  out.done = r;
  out.hungUp = await waitFor(() => !!ws.closed, 3000);
  await sleep(100);
  out.closed = ws.closed || null;
  out.after = { tour: BixbyCockpit.tour.state().on, voice: BixbyVoice.getState().state, sockets: window.__ws.length };
  out.ua = ws.sent.filter(m => m.type === 'user_activity').length;
  out.chunks = ws.sent.filter(m => m.user_audio_chunk).length;
  return out;
}"""


@pytest.fixture(scope='module')
def browser():
    pw = pytest.importorskip('playwright.sync_api')
    from tests.test_voice_tour_client import _chromium
    with pw.sync_playwright() as p:
        b = _chromium(p)
        if not b:
            pytest.skip('Chromium no disponible')
        yield b
        b.close()


def _page(browser, lang='es', session=None, configured=True, steps=3):
    from tests import test_voice_tour_client as tc
    c = browser.new_context(viewport={'width': 1366, 'height': 900}, service_workers='block')
    reqs = []

    def handler(route):
        url = route.request.url
        path = url[len('http://khipu.test'):].split('?')[0]
        reqs.append(path)
        if path in ('', '/'):
            page = tc.PAGE.replace("window.LANG = 'es'", "window.LANG = '%s'" % lang)
            if configured:
                # la forma REAL de app.html: window.V8.Keys (no hay `Keys` global)
                page = page.replace('<script>', '<script>window.V8 = { Keys: { has: function (k) { return k === "elevenlabs"; } } };', 1)
            return route.fulfill(status=200, content_type='text/html', headers={'Content-Security-Policy': tc._csp()}, body=page)
        if path == '/api/voice/bixby-prompt':
            return route.fulfill(status=200, content_type='application/json', body=json.dumps({'system_prompt': 'P', 'allow_override': False}))
        if path == '/api/voice/session':
            st, data = session or (200, {'signed_url': 'wss://api.elevenlabs.io/v1/convai/conversation?agent_id=a&conversation_signature=s',
                                         'overrides': {}, 'language': 'es'})
            return route.fulfill(status=st, content_type='application/json', body=json.dumps(data))
        if path.startswith('/api/voice/tour/'):
            return route.fulfill(status=404, content_type='application/json', body=json.dumps({'error': 'x', 'error_en': 'x'}))
        return route.fulfill(status=503, content_type='application/json', body='{"error":"sin servidor"}')
    c.route('http://khipu.test/**', handler)
    pg = c.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append('pageerror: ' + str(e)))
    pg.on('console', lambda m: errs.append('console: ' + m.text) if m.type == 'error' and 'Failed to load resource' not in m.text else None)
    pg.goto('http://khipu.test/')
    pg.add_script_tag(content=FAKE_WS)
    for s in tc.SCRIPTS:
        pg.add_script_tag(content=_r('engine', s))
    if steps:
        pg.evaluate('(n) => { window.KHIPU_TOUR.steps = window.KHIPU_TOUR.steps.slice(0, n); }', steps)
    # ¿narrateTour se llama DENTRO del clic? window.event es el clic mientras se despacha
    pg.evaluate("""() => { window.__narr = []; const V = window.BixbyVoice, n0 = V.narrateTour.bind(V);
      V.narrateTour = function () { window.__narr.push(window.event ? window.event.type : null); return n0(); }; }""")
    pg.evaluate('BixbyCockpit.open()')
    pg.wait_for_timeout(300)
    return c, pg, errs, reqs


@pytest.mark.parametrize('lang', ['es', 'en'])
def test_navegador_enlace_del_recorrido_lo_narra_el_agente(browser, lang):
    from tests.test_voice_tour_client import TOUR
    c, pg, errs, reqs = _page(browser, lang=lang)
    link = pg.locator('#kos-empty [data-q="demo"]')
    assert link.count() == 1
    link.click()
    pg.wait_for_timeout(100)
    assert pg.evaluate('window.__narr') == ['click']                          # síncrono, dentro del clic
    assert pg.evaluate('BixbyCockpit.tour.state().on') is False                # nada local: lo empieza el agente
    toast = pg.evaluate("() => [...document.querySelectorAll('.kht')].map(e => e.textContent).join(' | ')")
    assert ('Conectando con la voz de Khipu…' if lang == 'es' else "Connecting to Khipu's voice…") in toast, toast
    out = pg.evaluate(DRIVE, {'lang': lang})
    assert out['socket'] is True
    assert out['asked'] == [{'type': 'user_message', 'text': ES_ASK if lang == 'es' else EN_ASK}]
    assert out['ctx'] and out['ctx'][0]['listen_only'] is True
    assert out['pill'] == ('Khipu narra el recorrido' if lang == 'es' else 'Khipu is narrating the tour'), out['pill']
    assert ('toca 🎙 para hablarle' if lang == 'es' else 'tap 🎙 to talk to him') in out['mic'], out['mic']
    assert out['steps'] == [1, 2, 3] and 'mismatch' not in out
    assert out['says'] == [s[lang] for s in TOUR['steps'][:3]]
    assert out['done']['done'] is True
    assert out['hungUp'] is True and out['closed']['code'] == 1000           # colgó al terminar
    assert out['after'] == {'tour': False, 'voice': 'off', 'sockets': 1}
    assert out['chunks'] == 0
    assert pg.evaluate('window.__gum') == 0                                   # sin permiso de micrófono
    assert not [r for r in reqs if r.startswith('/api/voice/tour/')]          # ningún clip del servidor
    assert not errs, errs
    c.close()


def test_navegador_sesion_fallida_va_al_recorrido_local(browser):
    c, pg, errs, reqs = _page(browser, session=(402, {'error': 'Sin créditos (crudo)', 'error_en': 'raw'}))
    pg.locator('#kos-empty [data-q="demo"]').click()
    pg.wait_for_function('() => BixbyCockpit.tour.state().on', timeout=4000)
    s = pg.evaluate('BixbyCockpit.tour.state()')
    assert s['on'] and s['voice'] is False and s['i'] == 0
    assert pg.evaluate('window.__ws.length') == 0 and pg.evaluate('window.__gum') == 0
    pg.wait_for_timeout(600)
    assert any(r.startswith('/api/voice/tour/') for r in reqs)                # clips (aquí 404 → texto)
    toast = pg.evaluate("() => [...document.querySelectorAll('.kht')].map(e => e.textContent).join(' | ')")
    assert ES_FALLBACK in toast and 'crudo' not in toast, toast
    assert pg.evaluate("document.getElementById('bcp-mic').getAttribute('data-voice')") == 'off'
    pg.wait_for_timeout(300)
    assert pg.evaluate('BixbyCockpit.tour.state().i') == 0                    # un solo recorrido (no reinició)
    assert not errs, errs
    c.close()


def test_navegador_sin_voz_contratada_recorrido_local(browser):
    c, pg, errs, reqs = _page(browser, configured=False)
    pg.locator('#kos-empty [data-q="demo"]').click()
    pg.wait_for_timeout(200)
    assert pg.evaluate('window.__narr') == []
    assert pg.evaluate('BixbyCockpit.tour.state().on') is True
    assert '/api/voice/session' not in reqs
    assert not errs, errs
    c.close()


def test_navegador_con_la_conversacion_abierta_pide_requestTour(browser):
    c, pg, errs, reqs = _page(browser)
    pg.evaluate("""() => { window.__req = 0; BixbyVoice.isConnected = true;
      BixbyVoice.getState = () => ({ state: 'listening', connected: true, connecting: false, error: '', listenOnly: false });
      BixbyVoice.requestTour = () => { window.__req++; return true; }; }""")
    pg.locator('#kos-empty [data-q="demo"]').click()
    pg.wait_for_timeout(200)
    assert pg.evaluate('window.__req') == 1 and pg.evaluate('window.__narr') == []
    assert pg.evaluate('BixbyCockpit.tour.state().on') is False
    assert not errs, errs
    c.close()


def test_navegador_microfono_durante_el_recorrido_no_cuelga(browser):
    c, pg, errs, _ = _page(browser)
    pg.locator('#kos-empty [data-q="demo"]').click()
    pg.wait_for_function('() => window.__ws.length === 1', timeout=3000)
    pg.evaluate("""() => { const ws = window.__ws[0]; ws._open(); ws._msg({ type: 'conversation_initiation_metadata',
      conversation_initiation_metadata_event: { conversation_id: 'c', agent_output_audio_format: 'pcm_16000', user_input_audio_format: 'pcm_16000' } }); }""")
    pg.wait_for_timeout(100)
    pg.click('#bcp-mic')                                                      # permiso denegado (stub): sigue narrando
    pg.wait_for_timeout(300)
    st = pg.evaluate("() => ({ gum: window.__gum, lo: BixbyVoice.isListenOnly(), conn: BixbyVoice.isConnected, closed: !!window.__ws[0].closed })")
    assert st == {'gum': 1, 'lo': True, 'conn': True, 'closed': False}
    toast = pg.evaluate("() => [...document.querySelectorAll('.kht')].map(e => e.textContent).join(' | ')")
    assert 'Permiso de micrófono denegado' in toast, toast
    pg.evaluate('BixbyVoice.disconnect()')
    assert not errs, errs
    c.close()


# ═══════════════════ revisión (3 lentes): casos que dejaban al usuario sin recorrido ═══════════════════
ES_DROP = 'Se cortó la voz de Khipu: el recorrido sigue en pantalla.'
ES_MUTED = 'El navegador no dejó sonar la voz de Khipu: el recorrido sigue en texto.'
ES_ONSCREEN = 'El recorrido va en pantalla; puedes seguir hablándole a Khipu.'


def test_isconfigured_reads_the_health_flag_the_way_app_html_exposes_it():
    """app.html declara `const Keys` DENTRO del IIFE de v8 y solo lo publica como V8.Keys: un `Keys` global no
    existe en la app real (por eso el botón seguía tocando los clips viejos)."""
    app = _r('app.html')
    iife = app.index("var V8 = {};")
    assert app.index('(function(){', iife) < app.index('const Keys = {', iife)       # Keys queda dentro del IIFE
    assert 'V8.Keys=Keys;' in app
    js = _r('engine', 'voice.js')
    body = js[js.index('  isConfigured() {'):js.index('  narrationPending()')]
    assert 'W.V8 && W.V8.Keys' in body


REVIEW = r"""
async function main() {
  const R = {};
  const uaN = (ws) => ws.sent.filter(m => m.type === 'user_activity').length;
  async function opened(E) { const N = await narrate(E); const ws = E.sockets[E.sockets.length - 1]; ws._open(); ws._msg(META('pcm_16000', 'pcm_16000')); return { N, ws }; }
  {   // vigía: el agente empieza y se calla (ni siquiera dice la frase 1) → a los ~35 s cuelga; el recorrido sigue en
      // pantalla (no 30 min de user_activity). Si SÍ dice la frase 1 y después se calla, la app le manda [TOUR 2/N]
      // (tests/test_voice_tour_drive.py cubre el reenvío y el recorrido local).
    const E = env({ session: S }); const { rec } = fakeTour(E, STEPS);
    const { ws } = await opened(E);
    await call(E, ws, 'run_guided_demo', { action: 'start' });
    await E.advance(30000);
    R.stall30 = { connected: E.V.isConnected, closed: !!ws.closed };
    await E.advance(300000);
    R.stall = { connected: E.V.isConnected, closed: ws.closed || null, ua: uaN(ws), attached: rec.attached.slice(),
                tags: ws.sent.filter(m => m.type === 'user_message' && /^\[TOUR /.test(m.text)).length,
                listenOnly: E.V.isListenOnly(), toasts: E.toasts.slice(), local: rec.start.filter(o => o && o.fallback).length };
    R.errStall = E.errors;
  }
  {   // un `next` que espera una frase larga NO dispara el vigía
    const E = env({ session: S }); fakeTour(E, STEPS);
    const { ws } = await opened(E);
    await call(E, ws, 'run_guided_demo', { action: 'start' });
    speak(ws, 20);
    const r = await call(E, ws, 'run_guided_demo', { action: 'next' }, 26000);
    R.longNext = { r, connected: E.V.isConnected, closed: !!ws.closed };
    R.errLong = E.errors;
  }
  {   // interrupción en solo escuchar: NO pausa (nadie puede contestar "¿sigo?")
    const E = env({ session: S }); const { rec } = fakeTour(E, STEPS);
    const { ws } = await opened(E);
    await call(E, ws, 'run_guided_demo', { action: 'start' });
    spoke(E, ws, 0.3);
    const id = send(ws, 'run_guided_demo', { action: 'next' });
    ws._msg({ type: 'interruption', interruption_event: { event_id: 5 } });
    await E.advance(1500);
    R.intr = { r: results(ws, id), pause: rec.pause };
    R.errIntr = E.errors;
  }
  {   // max_duration en solo escuchar: UN aviso (no "toca el micrófono")
    const E = env({ session: S }); fakeTour(E, STEPS);
    const { ws } = await opened(E);
    await call(E, ws, 'run_guided_demo', { action: 'start' });
    ws._msg({ type: 'error', error_event: { error_type: 'max_duration_exceeded', message: 'max' } });
    ws._close(1000, '');
    await E.advance(2000);
    R.maxdur = { toasts: E.toasts.slice(), connected: E.V.isConnected };
    R.errMax = E.errors;
  }
  // el agente cuelga / se confunde ANTES de empezar → recorrido local (no "cancelled" sin nada)
  R.early = {};
  for (const kind of ['end_call', 'next', 'stop']) {
    const E = env({ session: S }); const { rec } = fakeTour(E, STEPS);
    const { N, ws } = await opened(E);
    await E.advance(1500);
    if (kind === 'end_call') ws._msg({ type: 'agent_tool_response', agent_tool_response: { tool_name: 'end_call' } });
    else send(ws, 'run_guided_demo', { action: kind });
    await E.advance(31000);
    R.early[kind] = { starts: rec.start.slice(), res: N.res(), closed: !!ws.closed, connected: E.V.isConnected,
                      toasts: E.toasts.slice(), errors: E.errors };
  }
  {   // override_error → reintento; 🎙 en los 50 ms del reintento → el reintento va CON micrófono (el del clic)
    const E = env({ session: { data: Object.assign({}, S.data, { overrides: { language: true }, language: 'es' }) }, lang: 'en' });
    fakeTour(E, STEPS);
    await narrate(E);
    const ws1 = E.sockets[0]; ws1._open();
    ws1._msg({ type: 'error', error_event: { error_type: 'override_error', message: 'override not allowed' } });
    ws1._close(1008, 'override');
    const up = await E.V.toggle();
    await E.advance(1000);
    const ws2 = E.sockets[1]; ws2._open(); ws2._msg(META('pcm_16000', 'pcm_16000'));
    await E.advance(20);
    const proc = E.ctxs[0].proc;
    if (proc && proc.onaudioprocess) proc.onaudioprocess({ inputBuffer: { getChannelData: () => new Float32Array(4800).fill(0.1) } });
    R.ovUp = { up, gum: E.gum, listenOnly: E.V.isListenOnly(), sockets: E.sockets.length,
               live: E.tracks.filter(t => !t.stopped).length, chunks: ws2.sent.filter(m => m.user_audio_chunk).length,
               asked: ws2.sent.filter(m => m.type === 'user_message').length };
    E.V.disconnect();
    R.errOv = E.errors;
  }
  {   // AudioContext que no suena (autoplay/iOS) antes de empezar → recorrido local SOLO TEXTO, sin narración muda
    const E = env({ session: S }); const { rec } = fakeTour(E, STEPS);
    const N = await narrate(E);
    const c = E.ctxs[0]; c.state = 'suspended'; c.resume = () => Promise.reject(new Error('autoplay'));
    const ws = E.sockets[0]; ws._open(); ws._msg(META('pcm_16000', 'pcm_16000'));
    await E.advance(1400);
    R.mute14 = rec.start.length;
    await E.advance(300);
    R.mute = { starts: rec.start.slice(), res: N.res(), closed: !!ws.closed, toasts: E.toasts.slice() };
    R.errMute = E.errors;
  }
  {   // 🎙 (sube a micrófono) y el agente tarda: el respaldo NO dice "no se pudo conectar"; su start tardío toma
      // el MISMO recorrido en su paso (no vuelve al 1)
    const E = env({ session: S }); const { rec } = fakeTour(E, STEPS);
    const { ws } = await opened(E);
    await E.V.toggle();
    await E.advance(9500);
    R.late = { starts: rec.start.slice(), toasts: E.toasts.slice(), connected: E.V.isConnected };
    const r = await call(E, ws, 'run_guided_demo', { action: 'start' });
    R.late.r = r; R.late.startsAfter = rec.start.length; R.late.attached = rec.attached.slice();
    E.V.disconnect();
    R.errLate = E.errors;
  }
  {   // clic de nuevo mientras la sesión vieja deja sonar su última frase tras ✕ → cuelga ya y arma uno nuevo
    const E = env({ session: S }); const { st } = fakeTour(E, STEPS);
    const { ws } = await opened(E);
    await call(E, ws, 'run_guided_demo', { action: 'start' });
    speak(ws, 6);
    st.on = false; E.V.tourClosed();
    await E.advance(300);
    R.pendBefore = E.V.narrationPending();
    let res = null; E.V.narrateTour().then(r => { res = r; });
    await E.advance(20);
    R.again = { res, sockets: E.sockets.length, oldClosed: ws.closed || null, listenOnly: E.V.isListenOnly(),
                pending: E.V.narrationPending() };
    const ws2 = E.sockets[E.sockets.length - 1];
    if (ws2 !== ws) { ws2._open(); ws2._msg(META('pcm_16000', 'pcm_16000')); }
    await E.advance(8500);           // el temporizador viejo (≤8 s) NO cuelga la sesión nueva (el de 9 s aún no vence)
    R.again.newAlive = ws2 !== ws && !ws2.closed;
    E.V.disconnect();
    R.errAgain = E.errors;
  }
  {   // iPhone: categoría de audio 'playback' durante la narración; se restaura al colgar y antes del micrófono
    const E = env({ session: S }); fakeTour(E, STEPS);
    const as = { type: 'auto' }; E.ctx.navigator.audioSession = as;
    const md = E.ctx.navigator.mediaDevices, g1 = md.getUserMedia; let atGum = null;
    md.getUserMedia = function () { atGum = as.type; return g1.apply(this, arguments); };
    E.V.narrateTour();
    R.ios = { sync: as.type };
    await E.advance(20);
    const ws = E.sockets[0]; ws._open(); ws._msg(META('pcm_16000', 'pcm_16000'));
    await E.V.toggle();
    R.ios.atGum = atGum; R.ios.afterUp = as.type;
    E.V.disconnect();
    const E2 = env({ session: S }); fakeTour(E2, STEPS);
    const as2 = { type: 'auto' }; E2.ctx.navigator.audioSession = as2;
    await opened(E2); R.ios.during = as2.type;
    E2.V.disconnect(); R.ios.afterHang = as2.type;
    R.errIos = E.errors.concat(E2.errors);
  }
  process.stdout.write(JSON.stringify(R));
  process.exit(0);
}
main().catch(e => { process.stdout.write(JSON.stringify({ fatal: String(e && e.stack || e) })); process.exit(0); });
"""


def _run_review(voice_path=VOICE_PATH):
    from tests import test_overnight_voice_client as vc
    helpers = MAIN.split('async function main()')[0]
    harness = vc.HARNESS.split('async function main()')[0] + helpers + REVIEW
    p = subprocess.run([NODE, '-e', harness, voice_path], capture_output=True, text=True, timeout=180)
    assert p.returncode == 0, p.stderr[-3000:]
    out = json.loads(p.stdout)
    assert 'fatal' not in out, out.get('fatal')
    return out


@pytest.fixture(scope='module')
def RV():
    if not NODE:
        pytest.skip('node no instalado')
    out = _run_review()
    for k in [k for k in out if k.startswith('err')]:
        assert out[k] == [], (k, out[k])
    return out


def test_stalled_agent_does_not_keep_a_paid_session_open(RV):
    assert RV['stall30'] == {'connected': True, 'closed': False}
    s = RV['stall']
    assert s['connected'] is False and s['closed'] and s['closed']['code'] == 1000
    assert s['ua'] == 0                                                  # ni un user_activity: el vigía cuelga
    assert s['tags'] == 0                                                # la frase 1 nunca sonó: la app no avanza
    assert s['attached'] == [False] and s['local'] == 0                  # el recorrido sigue en pantalla, solo
    assert s['toasts'] == [ES_DROP]
    ln = RV['longNext']
    assert ln['r'][0]['step'] == 2 and ln['connected'] is True and ln['closed'] is False


def test_listen_only_interruption_does_not_pause_the_tour(RV):
    assert RV['intr']['pause'] == 0
    assert RV['intr']['r'] and RV['intr']['r'][0].get('step') == 2 and 'paused' not in RV['intr']['r'][0]


def test_listen_only_max_duration_shows_one_notice(RV):
    assert RV['maxdur']['toasts'] == [ES_DROP] and RV['maxdur']['connected'] is False


@pytest.mark.parametrize('kind', ['end_call', 'next', 'stop'])
def test_agent_hangs_up_or_misfires_before_start_falls_back(RV, kind):
    e = RV['early'][kind]
    assert e['starts'] == [{'fallback': True}], e
    assert e['res'] == 'local' and e['closed'] is True and e['connected'] is False
    assert e['toasts'] == [ES_FALLBACK] and e['errors'] == []


def test_mic_tapped_during_override_retry_is_not_reverted(RV):
    o = RV['ovUp']
    assert o['up'] is True and o['gum'] == 1                             # el micrófono del clic, y no otro
    assert o['listenOnly'] is False and o['sockets'] == 2
    assert o['live'] == 1 and o['chunks'] >= 1                            # ahora SÍ se oye al usuario
    assert o['asked'] == 1


def test_muted_audio_context_falls_back_to_text(RV):
    assert RV['mute14'] == 0
    m = RV['mute']
    assert m['starts'] == [{'fallback': True, 'textOnly': True}] and m['res'] == 'local' and m['closed'] is True
    assert m['toasts'] == [ES_MUTED]


def test_upgraded_session_fallback_message_and_late_start_keeps_the_step(RV):
    lt = RV['late']
    assert lt['starts'] == [{'fallback': True, 'textOnly': True}] and lt['connected'] is True
    assert lt['toasts'] == [ES_ONSCREEN] and ES_FALLBACK not in lt['toasts']
    assert lt['r'][0]['success'] is True and lt['r'][0]['step'] == 1
    assert lt['startsAfter'] == 1 and lt['attached'] == [True]          # la voz lo toma; no reinicia


def test_click_again_while_old_session_drains_starts_a_new_narration(RV):
    assert RV['pendBefore'] is False
    a = RV['again']
    assert a['res'] is None and a['sockets'] == 2 and a['oldClosed']['code'] == 1000
    assert a['listenOnly'] is True and a['pending'] is True and a['newAlive'] is True


def test_ios_audio_session_playback_while_narrating(RV):
    i = RV['ios']
    assert i['sync'] == 'playback' and i['during'] == 'playback'
    assert i['atGum'] == 'auto' and i['afterUp'] == 'auto' and i['afterHang'] == 'auto'


def test_cockpit_review_static():
    ck = _r('engine', 'cockpit.js')
    # el doble clic solo se ignora mientras el pedido sigue pendiente; Esc cancela "Conectando…"; el aviso se va
    assert '_voiceListenOnly() && _voiceNarrPending(V)' in ck
    assert "if (_voiceListenOnly()) { e.stopPropagation(); try { window.BixbyVoice.stop(); }" in ck
    assert "if (r === 'cancelled')" in ck and "dismiss('kh-tour-hand')" in ck


def test_navegador_esc_cancela_conectando(browser):
    c, pg, errs, reqs = _page(browser)
    pg.locator('#kos-empty [data-q="demo"]').click()
    pg.wait_for_timeout(150)
    assert pg.evaluate('BixbyVoice.isListenOnly()') is True
    pg.keyboard.press('Escape')
    pg.wait_for_timeout(300)
    st = pg.evaluate("""() => ({ lo: BixbyVoice.isListenOnly(), tour: BixbyCockpit.tour.state().on,
      ws: window.__ws.length, closed: window.__ws.length ? !!window.__ws[0].closed : null,
      toast: [...document.querySelectorAll('.kht')].map(e => e.textContent).join(' | ') })""")
    assert st['lo'] is False and st['tour'] is False
    assert st['ws'] == 0 or st['closed'] is True
    assert 'Conectando con la voz de Khipu' not in st['toast'], st
    pg.wait_for_timeout(500)
    assert pg.evaluate('BixbyCockpit.tour.state().on') is False                # nada local tras cancelar
    assert not errs, errs
    c.close()


def test_navegador_relanzar_tras_cerrar_con_x(browser):
    c, pg, errs, _ = _page(browser)
    pg.locator('#kos-empty [data-q="demo"]').click()
    pg.wait_for_function('() => window.__ws.length === 1', timeout=3000)
    pg.evaluate("""async () => { const ws = window.__ws[0]; ws._open(); ws._msg({ type: 'conversation_initiation_metadata',
      conversation_initiation_metadata_event: { conversation_id: 'c', agent_output_audio_format: 'pcm_16000', user_input_audio_format: 'pcm_16000' } });
      ws._msg({ type: 'client_tool_call', client_tool_call: { tool_name: 'run_guided_demo', tool_call_id: 't1', parameters: { action: 'start' } } });
      // 4 s de "voz" (la frase sigue sonando cuando se cierra con ✕)
      const b = new Uint8Array(128000); let s = ''; for (let i = 0; i < b.length; i++) s += String.fromCharCode(i % 2 ? 3 : 32);
      ws._msg({ type: 'audio', audio_event: { audio_base_64: btoa(s), event_id: 1 } }); }""")
    pg.wait_for_function('() => BixbyCockpit.tour.state().on', timeout=3000)
    pg.click('#bcp-demoexit')
    pg.wait_for_timeout(300)
    assert pg.evaluate('!!window.__ws[0].closed') is False                   # deja terminar la frase…
    r = pg.evaluate('BixbyCockpit.demo()')
    assert r is None
    pg.wait_for_timeout(200)
    st = pg.evaluate("() => ({ n: window.__ws.length, old: window.__ws[0].closed || null, lo: BixbyVoice.isListenOnly() })")
    assert st['n'] == 2 and st['old'] and st['old']['code'] == 1000 and st['lo'] is True   # …pero un clic nuevo sí arma otro
    pg.evaluate('BixbyVoice.disconnect()')
    assert not errs, errs
    c.close()
