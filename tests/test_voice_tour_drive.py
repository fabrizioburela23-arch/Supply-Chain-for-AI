"""tests/test_voice_tour_drive.py — el recorrido narrado por la voz: LA APP MARCA EL RITMO (2026-10-12 b).

Fabrizio: «Solo dice el primer paso y se queda ahí». Transcripción real de ElevenLabs (gemini-2.5-flash): el agente
llama run_guided_demo start, dice la frase 1 EXACTA y termina su turno SIN llamar `next` → el recorrido quedaba en el
paso 1. Contrato nuevo (engine/voice.js `_driveTick`):
  · start: la herramienta entrega la frase 1 (nota nueva: "the app then sends you each next line … [TOUR n/N]").
  · cuando la frase del paso k terminó de SONAR (llegó audio después de entregarla, lo agendado ya sonó y no llega
    audio hace 600 ms) y no hay run_guided_demo en curso → 600 ms → la pantalla pasa al paso k+1 y se manda
    {type:'user_message', text:'[TOUR k+1/N] <frase>'}; tras la última → fin (solo escuchar: cuelga; con micrófono:
    contextual_update {"tour":"finished"} y la charla sigue).
  · sin audio a los 8 s → el MISMO mensaje una vez más; otra vez nada → solo escuchar: cuelga y sigue el recorrido
    local desde ese paso; con micrófono: pausa + aviso bilingüe (al reanudar se repite ESE paso, no se salta).
  · si el agente SÍ encadena `next`, no se manda ningún [TOUR] para ese paso; si llama `next` cuando el paso ya se
    entregó por mensaje y aún no sonó, espera a que suene y devuelve el SIGUIENTE: una entrega por paso, ninguno saltado.
  · pausa (el usuario habló) → el bucle no manda nada; `next` del agente reanuda.
Node (reloj falso, arnés de tests/test_overnight_voice_client.py) + Chromium con la Cabina REAL y un WebSocket falso
que NUNCA encadena, el recorrido entero (9 pasos) en ES y EN. Se salta lo que necesite `node` o Chromium.
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

START_NOTE = ('Say exactly the "say" line and nothing else. The app then sends you each next line as a message that '
              'starts with [TOUR n/N]: say exactly the text after the tag, nothing else, and do not call any tool for it.')
ES_DROP = 'Se cortó la voz de Khipu: el recorrido sigue en pantalla.'
ES_PAUSED = 'Khipu no siguió con el recorrido: quedó en pausa. Dile «sigue» para continuar.'
EN_PAUSED = 'Khipu did not go on with the tour: it is paused. Tell him "go on" to continue.'
FINISHED = {'type': 'contextual_update', 'text': '[CONTEXT_UPDATE] {"tour":"finished"}'}


def _r(*p):
    with open(os.path.join(ROOT, *p), encoding='utf-8') as f:
        return f.read()


# ═══════════════════════════════ estáticas ═══════════════════════════════
def test_static_contract():
    js = _r('engine', 'voice.js')
    ck = _r('engine', 'cockpit.js')
    assert 'const TOUR_DRIVE_GAP_MS = 600, TOUR_DRIVE_QUIET_MS = 600, TOUR_LINE_WAIT_MS = 8000' in js
    assert "'[TOUR ' + r.step + '/' + r.of + '] ' + r.say" in js
    assert START_NOTE in js and 'then call run_guided_demo with action next' not in js
    assert '[CONTEXT_UPDATE] {"tour":"finished"}' in js
    assert ES_PAUSED in js and EN_PAUSED in js                          # bilingüe
    assert 'resume: tourResume' in ck
    for s in (js, ck):
        assert 'window.confirm' not in s and 'window.alert' not in s and 'window.prompt(' not in s


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
function spoke(E, ws, seconds, eid) {
  speak(ws, seconds || 0.3, eid);
  const c = E.V.audioCtx; c.currentTime = E.V._playCursor + 0.01; E.V._playCursor = 0;
}
// la Cabina falsa: como la real, `next` con la voz también reanuda; `resume` repite el paso actual
function fakeTour(E, steps) {
  const rec = { start: [], next: 0, stop: [], pause: 0, resume: 0, attached: [] };
  const st = { on: false, i: -1, voice: false, paused: false };
  const T = {
    start: (o) => { rec.start.push(o); st.on = true; st.i = 0; st.voice = !!(o && o.voice); st.paused = false; return { step: 1, of: steps.length, say: steps[0] }; },
    next: () => { rec.next++; if (st.i + 1 >= steps.length) { st.on = false; return { done: true }; } st.i++; st.paused = false; return { step: st.i + 1, of: steps.length, say: steps[st.i] }; },
    stop: (r) => { rec.stop.push(r); st.on = false; },
    pause: () => { rec.pause++; st.paused = true; },
    resume: () => { rec.resume++; st.paused = false; return { step: st.i + 1, of: steps.length, say: steps[st.i] }; },
    state: () => ({ on: st.on, i: st.i, of: steps.length, voice: st.voice, paused: st.paused, premium: false, say: st.on ? steps[st.i] : null }),
    voiceAttached: (v) => { rec.attached.push(v); st.voice = !!v; },
  };
  E.ctx.BixbyCockpit = { tour: T };
  return { rec, st };
}
function env(opts) {
  const E = makeEnv(opts);
  E.ctx.V8 = { Keys: { has: (k) => k === 'elevenlabs' } };
  return E;
}
const S = { data: { signed_url: 'wss://api.elevenlabs.io/v1/convai/conversation?agent_id=a&conversation_signature=s', overrides: {}, language: 'es' } };
const NINE = ['L1.', 'L2.', 'L3.', 'L4.', 'L5.', 'L6.', 'L7.', 'L8.', 'L9.'];
const tags = (ws) => ws.sent.filter(m => m.type === 'user_message' && /^\[TOUR /.test(m.text)).map(m => m.text);
const toolSteps = (ws) => ws.sent.filter(m => m.type === 'client_tool_result').map(m => JSON.parse(m.result)).filter(r => r.step && r.say).map(r => r.step);
async function listenOnly(E) {
  E.V.narrateTour(); await E.advance(20);
  const ws = E.sockets[0]; ws._open(); ws._msg(META('pcm_16000', 'pcm_16000')); await E.advance(20);
  return ws;
}
async function mic(E) {
  await E.V.connect();
  const ws = E.sockets[0]; ws._open(); ws._msg(META('pcm_16000', 'pcm_16000')); await E.advance(20);
  return ws;
}
// avanza el reloj de a 50 ms hasta que aparece un [TOUR] nuevo (o vence maxMs); devuelve cuánto tardó
async function waitTag(E, ws, n0, maxMs) {
  for (let t = 0; t <= maxMs; t += 50) { if (tags(ws).length > n0) return t; await E.advance(50); }
  return null;
}
// el agente que NO encadena (como en la transcripción real): dice cada frase que recibe y nada más
async function nonChaining(E, ws, st, steps) {
  const out = { tags: [], waits: [], sync: [] };
  await call(E, ws, 'run_guided_demo', { action: 'start' });
  spoke(E, ws);
  for (let k = 2; k <= steps.length; k++) {
    const n0 = tags(ws).length;
    const w = await waitTag(E, ws, n0, 6000);
    out.waits.push(w);
    if (w == null) break;
    const t = tags(ws);
    out.tags.push(t[t.length - 1]);
    out.sync.push(st.i);                                     // la pantalla ya está en el paso del mensaje
    spoke(E, ws);
  }
  return out;
}

async function main() {
  const R = {};
  {   // ── A: solo escuchar, el agente NO encadena → la app manda [TOUR 2/9] … [TOUR 9/9] y cuelga al final ──
    const E = env({ session: S }); const { rec, st } = fakeTour(E, NINE);
    const ws = await listenOnly(E);
    const start = await call(E, ws, 'run_guided_demo', { action: 'start' });
    R.A = { start };
    // mientras la frase 1 suena (2 s por delante del reloj del audio) no se manda nada, aunque pase el tiempo
    speak(ws, 2.0);
    await E.advance(6000);
    R.A.whileSpeaking = tags(ws).length;
    E.V.audioCtx.currentTime = E.V._playCursor + 0.01; E.V._playCursor = 0;   // terminó de sonar
    const t2 = await waitTag(E, ws, 0, 3000);
    R.A.firstWait = t2;
    R.A.firstSync = st.i;
    spoke(E, ws);
    const out = { tags: tags(ws).slice(), waits: [t2], sync: [1] };
    for (let k = 3; k <= NINE.length; k++) {
      const w = await waitTag(E, ws, tags(ws).length, 6000);
      out.waits.push(w);
      if (w == null) break;
      const t = tags(ws); out.tags.push(t[t.length - 1]); out.sync.push(st.i);
      spoke(E, ws);
    }
    R.A.out = out;
    R.A.closedBeforeEnd = !!ws.closed;
    await E.advance(3000);
    R.A.end = { on: st.on, next: rec.next, closed: ws.closed || null, connected: E.V.isConnected, local: rec.start.filter(o => o && o.fallback).length,
                attached: rec.attached.slice(), toasts: E.toasts.slice(), tags: tags(ws).length,
                tools: ws.sent.filter(m => m.type === 'client_tool_result').length,
                finished: ws.sent.filter(m => m.type === 'contextual_update' && /finished/.test(m.text)).length };
    R.A.ctx = ws.sent.filter(m => m.type === 'contextual_update').map(m => JSON.parse(m.text.slice(17))).filter(c => c.tour).map(c => c.tour.step);
    R.errA = E.errors;
  }
  {   // ── B: conversación con micrófono, sin encadenar → la app marca el ritmo; al final "finished" y sigue abierta ──
    const E = env({ session: S }); const { rec, st } = fakeTour(E, NINE);
    const ws = await mic(E);
    const o = await nonChaining(E, ws, st, NINE);
    await E.advance(3000);
    R.B = { out: o, on: st.on, next: rec.next, closed: !!ws.closed, connected: E.V.isConnected,
            finished: ws.sent.filter(m => m.type === 'contextual_update' && m.text === '[CONTEXT_UPDATE] {"tour":"finished"}'),
            pause: rec.pause, toasts: E.toasts.slice() };
    await E.advance(20000);
    R.B.later = { tags: tags(ws).length, connected: E.V.isConnected };
    R.errB = E.errors;
  }
  // ── C: el agente SÍ encadena `next` tras cada frase → ningún [TOUR], sin doble avance ni pasos saltados ──
  R.C = {};
  for (const mode of ['listen', 'mic']) {
    const E = env({ session: S }); const { rec, st } = fakeTour(E, NINE);
    const ws = mode === 'listen' ? await listenOnly(E) : await mic(E);
    const got = [];
    let r = await call(E, ws, 'run_guided_demo', { action: 'start' });
    for (let guard = 0; r && r[0] && !r[0].done && guard < 20; guard++) {
      got.push(r[0].step);
      spoke(E, ws);
      r = await call(E, ws, 'run_guided_demo', { action: 'next' }, 900);
    }
    await E.advance(3000);
    R.C[mode] = { got, done: r && r[0] ? r[0].done : null, tags: tags(ws).length, next: rec.next, on: st.on,
                  closed: !!ws.closed, connected: E.V.isConnected };
    R['errC' + mode] = E.errors;
  }
  {   // ── D: mezcla — encadena unos pasos y otros no, y un `next` tardío cuando el paso ya salió por mensaje ──
    const E = env({ session: S }); const { rec, st } = fakeTour(E, NINE);
    const ws = await listenOnly(E);
    const log = [];
    const tagNow = async () => { const n0 = tags(ws).length; const w = await waitTag(E, ws, n0, 6000); const t = tags(ws); return w == null ? null : t[t.length - 1]; };
    let r = await call(E, ws, 'run_guided_demo', { action: 'start' }); log.push(['tool', r[0].step]);
    spoke(E, ws); r = await call(E, ws, 'run_guided_demo', { action: 'next' }, 900); log.push(['tool', r[0].step]);   // 2 por herramienta
    spoke(E, ws); log.push(['msg', await tagNow()]);                                                                   // 3 por mensaje
    spoke(E, ws); r = await call(E, ws, 'run_guided_demo', { action: 'next' }, 900); log.push(['tool', r[0].step]);   // 4
    spoke(E, ws); log.push(['msg', await tagNow()]);                                                                   // 5 por mensaje…
    // …y el agente dice la frase 5 Y encadena `next` en la misma respuesta (el `next` llega antes que el audio):
    // no avanza por encima de ella
    const late = send(ws, 'run_guided_demo', { action: 'next' });
    await E.advance(1500);
    R.D = { lateBeforeAudio: results(ws, late).length, iBeforeAudio: st.i };
    await E.advance(1500);
    R.D.lateStill = results(ws, late).length;                 // (aún dentro de los 4 s: espera el audio)
    spoke(E, ws);                                             // suena la frase 5
    await E.advance(900);
    const lr = results(ws, late);
    log.push(['tool', lr[0] ? lr[0].step : null]);           // → 6, no 5 otra vez
    spoke(E, ws); log.push(['msg', await tagNow()]);         // 7
    spoke(E, ws); log.push(['msg', await tagNow()]);         // 8
    spoke(E, ws); r = await call(E, ws, 'run_guided_demo', { action: 'next' }, 900); log.push(['tool', r[0].step]);   // 9
    spoke(E, ws); r = await call(E, ws, 'run_guided_demo', { action: 'next' }, 900);
    R.D.done = r[0] ? r[0].done : null;
    await E.advance(3000);
    R.D.log = log; R.D.next = rec.next; R.D.tags = tags(ws); R.D.toolSteps = toolSteps(ws);
    R.D.closed = !!ws.closed; R.D.on = st.on;
    R.errD = E.errors;
  }
  {   // ── E1: solo escuchar, la frase nunca suena → un reenvío; después cuelga y sigue el recorrido local ──
    const E = env({ session: S }); const { rec, st } = fakeTour(E, ['Uno.', 'Dos.', 'Tres.']);
    const ws = await listenOnly(E);
    await call(E, ws, 'run_guided_demo', { action: 'start' });
    spoke(E, ws);
    await waitTag(E, ws, 0, 3000);
    await E.advance(7700);
    R.E1 = { at77: tags(ws).length };
    await E.advance(500);
    R.E1.at82 = tags(ws).slice();
    await E.advance(7600);
    R.E1.at158 = { closed: !!ws.closed, tags: tags(ws).length };
    await E.advance(600);
    R.E1.end = { closed: ws.closed || null, connected: E.V.isConnected, attached: rec.attached.slice(), toasts: E.toasts.slice(),
                 i: st.i, on: st.on, local: rec.start.filter(o => o && o.fallback).length };
    await E.advance(30000);
    R.E1.later = tags(ws).length;
    R.errE1 = E.errors;
  }
  {   // ── E2: con micrófono, la frase nunca suena → un reenvío; después PAUSA (sin colgar); el "sí" repite el paso ──
    const E = env({ session: S, lang: 'es' }); const { rec, st } = fakeTour(E, ['Uno.', 'Dos.', 'Tres.']);
    const ws = await mic(E);
    await call(E, ws, 'run_guided_demo', { action: 'start' });
    spoke(E, ws);
    await waitTag(E, ws, 0, 3000);
    await E.advance(17000);
    R.E2 = { tags: tags(ws).slice(), pause: rec.pause, paused: st.paused, i: st.i, closed: !!ws.closed, connected: E.V.isConnected,
             toasts: E.toasts.slice() };
    await E.advance(30000);
    R.E2.later = tags(ws).length;
    // el usuario dice "sí, sigue" → el agente llama next → se repite "Dos." (nunca sonó), sin saltarlo
    speak(ws, 0.4); E.V.audioCtx.currentTime = E.V._playCursor + 0.01; E.V._playCursor = 0;   // "¡Claro!"
    R.E2.resume = await call(E, ws, 'run_guided_demo', { action: 'next' }, 900);
    R.E2.after = { i: st.i, paused: st.paused, resume: rec.resume, next: rec.next };
    spoke(E, ws);
    const w = await waitTag(E, ws, tags(ws).length, 4000);
    R.E2.nextTag = w == null ? null : tags(ws).pop();
    R.errE2 = E.errors;
  }
  {   // ── F: pausa por la voz del usuario en una conversación con micrófono → nada mientras está en pausa; `next` reanuda ──
    const E = env({ session: S }); const { rec, st } = fakeTour(E, ['Uno.', 'Dos.', 'Tres.', 'Cuatro.']);
    const ws = await mic(E);
    await call(E, ws, 'run_guided_demo', { action: 'start' });
    spoke(E, ws);
    await waitTag(E, ws, 0, 3000);                           // [TOUR 2/4]
    // un eco de nuestro propio mensaje y una interrupción justo después de mandarlo NO pausan
    ws._msg({ type: 'user_transcript', user_transcription_event: { user_transcript: tags(ws)[0] } });
    ws._msg({ type: 'interruption', interruption_event: { event_id: 3 } });
    R.F = { echoPause: rec.pause };
    speak(ws, 2.0, 4);                                        // Khipu dice la frase 2…
    await E.advance(500);
    ws._msg({ type: 'user_transcript', user_transcription_event: { user_transcript: 'espera, una pregunta' } });   // …y el usuario habla
    R.F.pause = rec.pause; R.F.paused = st.paused;
    E.V.audioCtx.currentTime = E.V._playCursor + 0.01; E.V._playCursor = 0;
    const n0 = tags(ws).length;
    await E.advance(25000);
    R.F.whilePaused = tags(ws).length - n0;
    speak(ws, 0.5, 9); E.V.audioCtx.currentTime = E.V._playCursor + 0.01; E.V._playCursor = 0;   // responde la pregunta
    R.F.resume = await call(E, ws, 'run_guided_demo', { action: 'next' }, 900);                 // "sí" → next
    R.F.afterResume = { i: st.i, paused: st.paused };
    spoke(E, ws, 0.3, 11);                                    // dice la frase 3 (respuesta posterior a la interrupción)
    const w = await waitTag(E, ws, tags(ws).length, 4000);
    R.F.tag4 = w == null ? null : tags(ws).pop();
    spoke(E, ws, 0.3, 12);
    await E.advance(3000);
    R.F.end = { on: st.on, connected: E.V.isConnected, finished: ws.sent.filter(m => m.type === 'contextual_update' && /"finished"/.test(m.text)).length,
                tags: tags(ws).length };
    R.errF = E.errors;
  }
  {   // ── G: inglés + ✕ del usuario a mitad → el bucle se detiene (nada más se manda) ──
    const E = env({ session: S, lang: 'en' }); const { st } = fakeTour(E, ['One.', 'Two.', 'Three.']);
    const ws = await listenOnly(E);
    await call(E, ws, 'run_guided_demo', { action: 'start' });
    spoke(E, ws);
    await waitTag(E, ws, 0, 3000);
    R.G = { tag: tags(ws)[0] };
    st.on = false; E.V.tourClosed();
    spoke(E, ws);
    await E.advance(10000);
    R.G.after = { tags: tags(ws).length, closed: !!ws.closed };
    R.errG = E.errors;
  }
  // ═══ revisión (2026-10-12 c) ═══
  // el agente responde a [TOUR n/N] SOLO con `next` (sin decir la frase): la herramienta devuelve la frase ACTUAL
  // (no avanza por encima de ella ni deja 25 s de silencio)
  R.H = {};
  for (const mode of ['listen', 'mic']) {
    const E = env({ session: S }); const { rec, st } = fakeTour(E, NINE);
    const ws = mode === 'listen' ? await listenOnly(E) : await mic(E);
    await call(E, ws, 'run_guided_demo', { action: 'start' });
    spoke(E, ws);
    await waitTag(E, ws, 0, 3000);                              // [TOUR 2/9] L2.
    const id = send(ws, 'run_guided_demo', { action: 'next' }); // …y el agente llama next en vez de decirla
    let t = 0;
    for (; t <= 30000 && !results(ws, id).length; t += 100) await E.advance(100);
    const h = { ms: t, res: results(ws, id), i: st.i, next: rec.next };
    spoke(E, ws);                                               // ahora sí dice L2
    const w = await waitTag(E, ws, tags(ws).length, 6000);
    h.nextTag = w == null ? null : tags(ws).pop();
    h.tags = tags(ws).length;
    R.H[mode] = h;
    R['errH' + mode] = E.errors;
  }
  {   // un `next` que esperaba en una sesión que se cerró NO toca el recorrido nuevo ni responde por el socket nuevo
    const E = env({ session: S }); const { st } = fakeTour(E, NINE);
    const ws = await listenOnly(E);
    await call(E, ws, 'run_guided_demo', { action: 'start' });
    spoke(E, ws);
    await waitTag(E, ws, 0, 3000);
    const id = send(ws, 'run_guided_demo', { action: 'next' });
    await E.advance(1000);
    st.on = false; E.V.tourClosed(); E.V.disconnect();          // ✕
    await E.advance(50);
    E.V.narrateTour(); await E.advance(20);                     // y lo vuelve a pedir enseguida
    const ws2 = E.sockets[E.sockets.length - 1];
    ws2._open(); ws2._msg(META('pcm_16000', 'pcm_16000')); await E.advance(20);
    const s2 = await call(E, ws2, 'run_guided_demo', { action: 'start' });
    await E.advance(26000);
    R.I = { two: E.sockets.length, s2, i: st.i, staleOnNew: ws2.sent.filter(m => m.type === 'client_tool_result' && m.tool_call_id === id).length,
            staleOnOld: results(ws, id).filter(r => r.step).length, tags2: tags(ws2).length };
    R.errI = E.errors;
  }
  {   // en pausa (el usuario habló) el agente retoma con `start` en vez de `next`: el recorrido se reanuda
    const E = env({ session: S }); const { rec, st } = fakeTour(E, NINE);
    const ws = await mic(E);
    await call(E, ws, 'run_guided_demo', { action: 'start' });
    spoke(E, ws);
    await waitTag(E, ws, 0, 3000);                              // [TOUR 2/9]
    speak(ws, 2.0, 4);
    await E.advance(1600);
    ws._msg({ type: 'user_transcript', user_transcription_event: { user_transcript: 'espera' } });
    E.V.audioCtx.currentTime = E.V._playCursor + 0.01; E.V._playCursor = 0;
    speak(ws, 0.5, 6); E.V.audioCtx.currentTime = E.V._playCursor + 0.01; E.V._playCursor = 0;   // contesta
    await E.advance(1000);
    R.J = { paused: st.paused, start: await call(E, ws, 'run_guided_demo', { action: 'start' }) };
    R.J.after = { paused: st.paused, i: st.i };
    spoke(E, ws, 0.3, 8);                                       // dice L2
    const w = await waitTag(E, ws, tags(ws).length, 6000);
    R.J.nextTag = w == null ? null : tags(ws).pop();
    R.errJ = E.errors;
  }
  {   // la pausa por "no la dijo" no sobrevive a un stop: en el recorrido nuevo `next` avanza (no repite)
    const E = env({ session: S }); const { rec, st } = fakeTour(E, ['Uno.', 'Dos.', 'Tres.', 'Cuatro.']);
    const ws = await mic(E);
    await call(E, ws, 'run_guided_demo', { action: 'start' });
    spoke(E, ws);
    await waitTag(E, ws, 0, 3000);
    await E.advance(17000);                                     // nunca dice "Dos." → pausa
    const gaveUp = { paused: st.paused, tags: tags(ws).length };
    await call(E, ws, 'run_guided_demo', { action: 'stop' });
    await call(E, ws, 'run_guided_demo', { action: 'start' });  // recorrido nuevo
    spoke(E, ws, 0.3, 5);
    const n0 = tags(ws).length;
    await waitTag(E, ws, n0, 3000);                             // [TOUR 2/4] Dos.
    speak(ws, 2.0, 7);
    await E.advance(500);
    ws._msg({ type: 'user_transcript', user_transcription_event: { user_transcript: 'perdón' } });
    E.V.audioCtx.currentTime = E.V._playCursor + 0.01; E.V._playCursor = 0;
    R.K = { gaveUp, res: await call(E, ws, 'run_guided_demo', { action: 'next' }, 1500), resume: rec.resume, i: st.i };
    R.errK = E.errors;
  }
  {   // un "¡Claro!" antes de start cuyo audio llega DESPUÉS del resultado no cuenta como la frase 1
    const LONG = NINE.map((s, k) => 'Paso ' + (k + 1) + ': ' + 'esta es una frase larga del recorrido de un minuto. '.repeat(2));
    const E = env({ session: S }); const { st } = fakeTour(E, LONG);
    const ws = await listenOnly(E);
    await call(E, ws, 'run_guided_demo', { action: 'start' });
    await E.advance(250);
    speak(ws, 0.5, 2);                                          // "¡Claro!" (la misma generación que el start)
    await E.advance(500);
    E.V.audioCtx.currentTime = E.V._playCursor + 0.01; E.V._playCursor = 0;   // sonó
    await E.advance(1900);                                      // la frase 1 tarda (LLM + TTS)
    R.L = { early: tags(ws).length, iEarly: st.i };
    speak(ws, 4.0, 3);                                          // la frase 1
    await E.advance(400);
    E.V.audioCtx.currentTime = E.V._playCursor + 0.01; E.V._playCursor = 0;
    const w = await waitTag(E, ws, 0, 6000);
    R.L.after = { w, tag: tags(ws)[0] ? tags(ws)[0].slice(0, 9) : null, i: st.i };
    // si de verdad solo dijo algo corto, igual sigue (nunca se traba): tope de gracia
    spoke(E, ws, 0.3, 4);
    R.L.shortWait = await waitTag(E, ws, 1, 6000);
    R.errL = E.errors;
  }
  process.stdout.write(JSON.stringify(R));
  process.exit(0);
}
main().catch(e => { process.stdout.write(JSON.stringify({ fatal: String(e && e.stack || e) })); process.exit(0); });
"""


@pytest.fixture(scope='module')
def D():
    if not NODE:
        pytest.skip('node no instalado')
    from tests import test_overnight_voice_client as vc
    harness = vc.HARNESS.split('async function main()')[0] + MAIN
    p = subprocess.run([NODE, '-e', harness, VOICE_PATH], capture_output=True, text=True, timeout=240)
    assert p.returncode == 0, p.stderr[-3000:]
    out = json.loads(p.stdout)
    assert 'fatal' not in out, out.get('fatal')
    for k in [k for k in out if k.startswith('err')]:
        assert out[k] == [], (k, out[k])
    return out


def test_start_note_tells_the_agent_the_app_sends_the_lines(D):
    assert D['A']['start'] == [{'success': True, 'step': 1, 'of': 9, 'say': 'L1.', 'note': START_NOTE}]


def test_listen_only_non_chaining_agent_gets_every_line_in_order(D):
    a = D['A']
    assert a['whileSpeaking'] == 0                                       # nada mientras la frase 1 suena
    assert a["firstWait"] is not None and 500 <= a["firstWait"] <= 900   # ya callado hace rato: solo la pausa de 600 ms
    o = a['out']
    assert o['tags'] == ['[TOUR %d/9] L%d.' % (k, k) for k in range(2, 10)]
    assert o['sync'] == list(range(1, 9))                                 # pantalla y frase, el mismo paso
    assert all(w is not None and 1000 <= w <= 1600 for w in o['waits'][1:]), o['waits']   # 600 ms sin audio + 600 ms
    e = a['end']
    assert e['on'] is False and e['next'] == 9                            # 8 avances + el fin
    assert e['closed'] and e['closed']['code'] == 1000 and e['connected'] is False   # solo escuchaba: cuelga
    assert e['tags'] == 8 and e['tools'] == 1                             # una sola herramienta (start); 8 mensajes
    assert e['local'] == 0 and e['attached'] == [] and e['toasts'] == [] and e['finished'] == 0
    assert a['ctx'][-1] >= 8                                              # CONTEXT_UPDATE sigue con tour.step


def test_mic_session_non_chaining_finishes_and_stays_open(D):
    b = D['B']
    assert b['out']['tags'] == ['[TOUR %d/9] L%d.' % (k, k) for k in range(2, 10)]
    assert b['out']['sync'] == list(range(1, 9))
    assert b['on'] is False and b['next'] == 9 and b['pause'] == 0
    assert b['finished'] == [FINISHED]                                    # "finished" una vez…
    assert b['closed'] is False and b['connected'] is True                # …y la conversación sigue
    assert b['later'] == {'tags': 8, 'connected': True} and b['toasts'] == []


@pytest.mark.parametrize('mode', ['listen', 'mic'])
def test_chaining_agent_gets_no_tour_messages(D, mode):
    c = D['C'][mode]
    assert c['got'] == list(range(1, 10)) and c['done'] is True
    assert c['tags'] == 0 and c['next'] == 9 and c['on'] is False
    assert c['closed'] is (mode == 'listen') and c['connected'] is (mode == 'mic')


def test_mixed_exactly_one_delivery_per_step(D):
    d = D['D']
    assert d['log'] == [['tool', 1], ['tool', 2], ['msg', '[TOUR 3/9] L3.'], ['tool', 4], ['msg', '[TOUR 5/9] L5.'],
                        ['tool', 6], ['msg', '[TOUR 7/9] L7.'], ['msg', '[TOUR 8/9] L8.'], ['tool', 9]]
    assert d['lateBeforeAudio'] == 0 and d['iBeforeAudio'] == 4 and d['lateStill'] == 0   # no avanza sobre la frase 5
    assert d['done'] is True and d['next'] == 9 and d['on'] is False and d['closed'] is True
    delivered = sorted(d['toolSteps'] + [int(re.match(r'\[TOUR (\d+)/', t).group(1)) for t in d['tags']])
    assert delivered == list(range(1, 10))                                # cada paso una vez, ninguno saltado


def test_line_never_spoken_listen_only_resends_once_then_local_tour(D):
    e = D['E1']
    assert e['at77'] == 1                                                 # a los 8 s, todavía uno
    assert e['at82'] == ['[TOUR 2/3] Dos.', '[TOUR 2/3] Dos.']           # el MISMO mensaje, una vez más
    assert e['at158'] == {'closed': False, 'tags': 2}
    end = e['end']
    assert end['closed'] and end['closed']['code'] == 1000 and end['connected'] is False
    assert end['attached'] == [False] and end['on'] is True and end['i'] == 1 and end['local'] == 0   # sigue local, desde el paso 2
    assert end['toasts'] == [ES_DROP]
    assert e['later'] == 2                                                # nunca más de 2 por paso


def test_line_never_spoken_mic_pauses_and_resume_repeats_the_step(D):
    e = D['E2']
    assert e['tags'] == ['[TOUR 2/3] Dos.', '[TOUR 2/3] Dos.']
    assert e['pause'] == 1 and e['paused'] is True and e['i'] == 1
    assert e['closed'] is False and e['connected'] is True                # no cuelga la conversación
    assert e['toasts'] == [ES_PAUSED]
    assert e['later'] == 2                                                # en pausa: nada más
    assert e['resume'] == [{'success': True, 'step': 2, 'of': 3, 'say': 'Dos.'}]   # repite el paso que no sonó
    assert e['after'] == {'i': 1, 'paused': False, 'resume': 1, 'next': 1}
    assert e['nextTag'] == '[TOUR 3/3] Tres.'                             # y el ritmo sigue


def test_user_pause_stops_the_loop_and_agent_next_resumes(D):
    f = D['F']
    assert f['echoPause'] == 0                                            # eco / interrupción propia: no pausa
    assert f['pause'] == 1 and f['paused'] is True
    assert f['whilePaused'] == 0
    assert f['resume'] == [{'success': True, 'step': 3, 'of': 4, 'say': 'Tres.'}]
    assert f['afterResume'] == {'i': 2, 'paused': False}
    assert f['tag4'] == '[TOUR 4/4] Cuatro.'
    assert f['end'] == {'on': False, 'connected': True, 'finished': 1, 'tags': 2}


def test_english_and_close_stops_the_loop(D):
    assert D['G']['tag'] == '[TOUR 2/3] Two.'
    assert D['G']['after']['tags'] == 1


# ═══════════════════════ la Cabina REAL en Chromium (agente que NUNCA encadena) ═══════════════════════
NEVER_CHAINS = r"""async ({ lang }) => {
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));
  const waitFor = async (fn, ms) => { const t0 = Date.now(); while (!fn()) { if (Date.now() - t0 > ms) return false; await sleep(25); } return true; };
  const out = { tags: [], shown: [], idx: [] };
  out.socket = await waitFor(() => window.__ws.length === 1, 3000);
  const ws = window.__ws[0];
  ws._open();
  ws._msg({ type: 'conversation_initiation_metadata', conversation_initiation_metadata_event:
    { conversation_id: 'c', agent_output_audio_format: 'pcm_16000', user_input_audio_format: 'pcm_16000' } });
  await sleep(50);
  const pcm = (() => { const b = new Uint8Array(3200); for (let i = 0; i < b.length; i += 2) { b[i] = 0x20; b[i + 1] = 0x03; } let s = ''; b.forEach(x => { s += String.fromCharCode(x); }); return btoa(s); })();
  const tagsOf = () => ws.sent.filter(m => m.type === 'user_message' && /^\[TOUR /.test(m.text)).map(m => m.text);
  // start: el agente dice la frase 1 (0,1 s de "voz") y termina su turno — NUNCA llama `next`
  ws._msg({ type: 'client_tool_call', client_tool_call: { tool_name: 'run_guided_demo', tool_call_id: 't1', parameters: { action: 'start' } } });
  await waitFor(() => ws.sent.some(m => m.type === 'client_tool_result'), 3000);
  out.start = JSON.parse(ws.sent.find(m => m.type === 'client_tool_result').result);
  ws._msg({ type: 'audio', audio_event: { audio_base_64: pcm, event_id: 1 } });
  for (let k = 2; k <= out.start.of; k++) {
    const n0 = tagsOf().length;
    if (!await waitFor(() => tagsOf().length > n0, 6000)) { out.stuck = k; break; }
    const t = tagsOf(); out.tags.push(t[t.length - 1]);
    out.idx.push(BixbyCockpit.tour.state().i);
    out.shown.push((document.querySelector('#bcp-demotxt .bcp-demosr') || {}).textContent);
    ws._msg({ type: 'audio', audio_event: { audio_base_64: pcm, event_id: 1 } });   // dice la frase recibida
  }
  out.hungUp = await waitFor(() => !!ws.closed, 6000);
  await sleep(100);
  out.closed = ws.closed || null;
  out.after = { tour: BixbyCockpit.tour.state().on, voice: BixbyVoice.getState().state, sockets: window.__ws.length };
  out.tools = ws.sent.filter(m => m.type === 'client_tool_result').length;
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


@pytest.mark.parametrize('lang', ['es', 'en'])
def test_navegador_recorrido_entero_sin_que_el_agente_encadene(browser, lang):
    from tests.test_voice_tour_client import TOUR, N
    from tests.test_voice_tour_narrator import _page
    c, pg, errs, reqs = _page(browser, lang=lang, steps=0)              # el guion completo
    pg.locator('#kos-empty [data-q="demo"]').click()
    out = pg.evaluate(NEVER_CHAINS, {'lang': lang})
    assert out['socket'] is True and 'stuck' not in out, out
    assert out['start']['step'] == 1 and out['start']['of'] == N and out['start']['note'] == START_NOTE
    assert out['start']['say'] == TOUR['steps'][0][lang]
    want = ['[TOUR %d/%d] %s' % (k + 1, N, TOUR['steps'][k][lang]) for k in range(1, N)]
    assert out['tags'] == want
    assert out['idx'] == list(range(1, N))                               # la pantalla, en el paso del mensaje
    assert out['shown'] == [TOUR['steps'][k][lang] for k in range(1, N)]   # y el subtítulo, la misma frase
    assert out['hungUp'] is True and out['closed']['code'] == 1000
    assert out['after'] == {'tour': False, 'voice': 'off', 'sockets': 1}
    assert out['tools'] == 1 and out['chunks'] == 0
    assert pg.evaluate('window.__gum') == 0
    assert not [r for r in reqs if r.startswith('/api/voice/tour/')]
    assert not errs, errs
    c.close()


# ═══════════════════════ revisión 2026-10-12 c ═══════════════════════
@pytest.mark.parametrize('mode', ['listen', 'mic'])
def test_next_instead_of_saying_the_tour_line_returns_the_current_line(D, mode):
    h = D['H'][mode]
    assert h['res'] == [{'success': True, 'step': 2, 'of': 9, 'say': 'L2.'}]   # la frase ACTUAL, no la 3
    assert 3500 <= h['ms'] <= 5000, h['ms']                                     # sin 25 s de silencio
    assert h['i'] == 1 and h['next'] == 1
    assert h['nextTag'] == '[TOUR 3/9] L3.' and h['tags'] == 2                  # y el ritmo sigue, sin saltos


def test_stale_next_from_a_closed_session_does_not_touch_the_new_tour(D):
    i = D['I']
    assert i['two'] == 2 and i['s2'][0]['step'] == 1
    assert i['staleOnNew'] == 0 and i['staleOnOld'] == 0                         # ni por el socket nuevo ni avanza
    assert i['i'] == 0


def test_start_while_paused_resumes_the_tour(D):
    j = D['J']
    assert j['paused'] is True
    assert j['start'][0]['step'] == 2 and j['start'][0]['say'] == 'L2.'
    assert j['after'] == {'paused': False, 'i': 1}
    assert j['nextTag'] == '[TOUR 3/9] L3.'


def test_unsaid_step_does_not_survive_stop(D):
    k = D['K']
    assert k['gaveUp'] == {'paused': True, 'tags': 2}
    assert k['res'] == [{'success': True, 'step': 3, 'of': 4, 'say': 'Tres.'}]
    assert k['resume'] == 0 and k['i'] == 2


def test_lead_in_audio_after_start_is_not_line_one(D):
    l = D['L']
    assert l['early'] == 0 and l['iEarly'] == 0                                 # no avanzó con el "¡Claro!"
    assert l['after']['w'] is not None and l['after']['tag'] == '[TOUR 2/9' and l['after']['i'] == 1
    assert l['shortWait'] is not None and l['shortWait'] <= 4500                # nunca se traba
