"""tests/test_voice_tour_client.py — el recorrido de un minuto en Khipus OS, narrado con la voz de Khipu (2026-10-11).

Lado CLIENTE del contrato (el servidor y el guion los cubre tests/test_voice_tour.py):
  · engine/cockpit.js ya no trae narración propia: los pasos salen de window.KHIPU_TOUR y cada act.kind abre
    su ventana (empty/graph/glance/xray/sim/agents/insights/broker); una empresa que no existe → el mapa.
  · engine/voice.js: run_guided_demo start/next/stop; `next` responde recién cuando terminó de SONAR la frase
    anterior (_playCursor) y siempre antes del tope de 30 s; stopped:true después de que el usuario lo cerró;
    interrumpir pausa; colgar deja el recorrido en pantalla; CONTEXT_UPDATE lleva {tour}; requestTour().
  · Chromium (Playwright) con la Cabina REAL: sin voz contratada (audio del recorrido → 404) se ve con
    subtítulos, la ventana va AL LADO del chat a 1366 px (no maximizada), ⏭ hasta el final sin errores, ES y EN;
    en un celular (390×844) las ventanas van encima; con clips (b) avanza al terminar cada clip y libera los
    object URLs; con la voz conectada no suena NADA aquí (ni clip ni speechSynthesis) y el pedido va al agente.
Se salta lo que necesite `node` o Chromium si no están.
"""
import json
import os
import re
import shutil
import struct
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = shutil.which('node')
VOICE_PATH = os.path.join(ROOT, 'engine', 'voice.js')


def _r(*p):
    with open(os.path.join(ROOT, *p), encoding='utf-8') as f:
        return f.read()


def _tour():
    src = _r('engine', 'tour_script.js')
    return json.loads(re.search(r'\.KHIPU_TOUR\s*=\s*(\{.*\})\s*;\s*$', src, re.S).group(1))


TOUR = _tour()
N = len(TOUR['steps'])


def _func(src, name):
    """Fuente de `function name(…) {…}` con llaves balanceadas (salta cadenas y comentarios)."""
    m = re.search(r'function ' + re.escape(name) + r'\s*\(', src)
    assert m, name
    i = src.index('{', m.end())
    depth, j, n, q = 0, i, len(src), None
    while j < n:
        c = src[j]
        if q:
            if c == '\\':
                j += 2
                continue
            if c == q:
                q = None
        elif c in '\'"`':
            q = c
        elif src.startswith('//', j):
            j = src.index('\n', j)
            continue
        elif src.startswith('/*', j):
            j = src.index('*/', j) + 2
            continue
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return src[m.start():j + 1]
        j += 1
    raise AssertionError(name)


# ═══════════════════════════════ estáticas ═══════════════════════════════
def test_cockpit_has_no_hardcoded_tour_narration():
    ck = _r('engine', 'cockpit.js')
    for old in ('Te muestro en un minuto', 'cuenta simulada', 'simulated account', 'Vigilo casi mil', 'Let me show you what I do',
                'GUIDED DEMO', 'DEMOSTRACIÓN GUIADA'):
        assert old not in ck, old
    for st in TOUR['steps']:                                    # ninguna frase del guion copiada en la Cabina
        assert st['es'][:40] not in ck and st['en'][:40] not in ck, st['id']
    steps = _func(ck, 'demoSteps')
    assert '_tourScript()' in steps and 's[lang]' in steps
    assert 'window.KHIPU_TOUR' in _func(ck, '_tourScript')
    act = _func(ck, '_tourAct')
    for k in ('empty', 'graph', 'glance', 'xray', 'sim', 'agents', 'insights', 'broker'):
        assert "'" + k + "'" in act, k
    assert 'aria-live="polite"' in _func(ck, '_demoRenderBar')
    assert "'/api/voice/tour/'" in _func(ck, '_tourClipUrl') and "'?v='" in _func(ck, '_tourClipUrl')
    # una sola puerta para el audio: UN <audio> (new Audio en un solo lugar) y la voz del navegador en uno solo
    assert ck.count('new Audio(') == 1 and ck.count('speechSynthesis.speak(') == 1
    assert 'window.confirm' not in ck and 'window.alert' not in ck
    # en pantallas anchas la ventana del recorrido NO se maximiza
    assert 'if (_demo.on) { opts.solo = true; if (!isCentered()) opts.max = true; }' in ck
    assert 'tour: tourApi' in ck and 'demo: demoStart' in ck


def test_voice_timeout_mirror_and_handler():
    js = _r('engine', 'voice.js')
    m = re.search(r'const VOICE_TOOL_TIMEOUT_S = \{(.*?)\};', js, re.S)
    assert dict((k, int(v)) for k, v in re.findall(r'(\w+):\s*(\d+)', m.group(1)))['run_guided_demo'] == 30
    import server
    assert server._VOICE_TOOL_TIMEOUTS['run_guided_demo'] == 30
    assert "case 'run_guided_demo': return this._toolTour(params, respond);" in js
    assert "type: 'user_message'" in _func_obj(js, 'requestTour')
    assert '[CONTEXT_UPDATE] {"tour":"closed by the user"}' in js


def _func_obj(src, name):
    """Método de objeto literal `name(…) {…}` (voice.js)."""
    i = src.index('\n  ' + name + '(')
    return _func(src[:i] + '\nfunction ' + src[i + 3:], name)


# ═══════════════════════ cockpit.js: pasos desde el guion (Node) ═══════════════════════
ACT_HARNESS = r"""
const fs = require('fs'), vm = require('vm');
const SRC = JSON.parse(fs.readFileSync(0, 'utf8'));
const out = {};
function run(lang, opts) {
  opts = opts || {};
  const calls = [];
  const ctx = {
    window: {}, console,
    ckLang: () => lang,
    resolveNode: (q) => ({ nvidia: { id: 'Nvidia' }, tsmc: { id: 'TSMC' } })[String(q).toLowerCase()] || null,
    stage: (k, a) => { calls.push(['stage', k, a == null ? null : a]); return 'w'; },
    deskActive: () => true,
    desk: () => ({ closeAll: () => calls.push(['closeAll']) }),
    _runScreen: (id) => { calls.push(['screen', id]); return opts.noAgents ? false : true; },
  };
  ctx.window.KHIPU_TOUR = opts.tour || SRC.tour;
  ctx.window.KhipuOSWin = opts.noOsw ? undefined : { open: (k, a) => { calls.push(['osw', k, a]); return opts.oswFails ? false : true; } };
  vm.createContext(ctx);
  vm.runInContext(SRC.fns, ctx);
  const steps = ctx.demoSteps();
  const perStep = steps.map(s => { calls.length = 0; s.act(); return { id: s.id, kind: s.kind, say: s.say, calls: calls.slice() }; });
  return perStep;
}
out.es = run('es');
out.en = run('en');
out.oswFails = run('es', { oswFails: true });
out.noOsw = run('es', { noOsw: true });
out.noAgents = run('es', { noAgents: true });
const bad = { version: 'x', steps: [
  { id: 'a', act: { kind: 'glance', company: 'Nadie SA' }, es: 'uno', en: 'one' },
  { id: 'b', act: { kind: 'xray', company: 'Nadie SA' }, es: 'dos', en: 'two' },
  { id: 'c', act: { kind: 'sim', company: 'Nadie SA' }, es: 'tres', en: 'three' },
  { id: 'd', act: { kind: 'teleport' }, es: 'cuatro', en: 'four' },
  { id: 'e', act: { kind: 'sim', company: 'tsmc' }, es: 'cinco' } ] };
out.bad = run('en', { tour: bad });
out.none = (function () { const c = { window: {}, ckLang: () => 'es' }; vm.createContext(c); vm.runInContext(SRC.fns, c); return c.demoSteps().length; })();
process.stdout.write(JSON.stringify(out));
"""


@pytest.fixture(scope='module')
def acts():
    if not NODE:
        pytest.skip('node no instalado')
    ck = _r('engine', 'cockpit.js')
    fns = '\n'.join(_func(ck, n) for n in ('_demoNode', '_tourScript', '_tourAct', 'demoSteps'))
    p = subprocess.run([NODE, '-e', ACT_HARNESS], input=json.dumps({'fns': fns, 'tour': TOUR}),
                       capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr[-3000:]
    return json.loads(p.stdout)


def test_steps_come_from_the_script_in_the_ui_language(acts):
    assert [s['say'] for s in acts['es']] == [s['es'] for s in TOUR['steps']]
    assert [s['say'] for s in acts['en']] == [s['en'] for s in TOUR['steps']]
    assert [s['kind'] for s in acts['es']] == [s['act']['kind'] for s in TOUR['steps']]
    assert acts['none'] == 0                                         # sin guion → sin recorrido (no inventa texto)


def test_every_act_kind_opens_its_window(acts):
    by = {s['kind']: s['calls'] for s in acts['es']}
    assert set(by) == {'empty', 'graph', 'glance', 'xray', 'sim', 'agents', 'insights', 'broker'}
    assert by['empty'] == [['closeAll'], ['stage', 'empty', None]]
    assert by['graph'] == [['stage', 'graph', None]]
    assert by['insights'] == [['stage', 'insights', None]] and by['broker'] == [['stage', 'broker', None]]
    assert by['glance'] == [['osw', 'glance', {'id': 'Nvidia'}]]
    assert by['xray'] == [['stage', 'xray', 'Nvidia']]
    assert by['sim'] == [['stage', 'sim', {'id': 'TSMC', 'kind': 'collapse', 'severity': 100}]]
    assert by['agents'] == [['screen', 'agents']]


def test_fallbacks_never_throw(acts):
    g = [s for s in acts['oswFails'] if s['kind'] == 'glance'][0]['calls']
    assert g == [['osw', 'glance', {'id': 'Nvidia'}], ['stage', 'xray', 'Nvidia']]
    assert [s for s in acts['noOsw'] if s['kind'] == 'glance'][0]['calls'] == [['stage', 'xray', 'Nvidia']]
    assert [s for s in acts['noAgents'] if s['kind'] == 'agents'][0]['calls'] == [['screen', 'agents'], ['stage', 'empty', None]]
    b = acts['bad']
    assert [s['calls'] for s in b[:4]] == [[['stage', 'graph', None]]] * 4      # empresa inexistente / tipo raro → el mapa
    assert b[4]['say'] == 'cinco'                                               # sin la frase en inglés → la española
    assert b[4]['calls'] == [['stage', 'sim', {'id': 'TSMC', 'kind': 'collapse', 'severity': 100}]]


# ═══════════════════════ voice.js: run_guided_demo (Node, reloj falso) ═══════════════════════
MAIN = r"""
let CALLN = 0;
function send(ws, name, params) {
  const id = 'tc_' + (++CALLN);
  ws._msg({ type: 'client_tool_call', client_tool_call: { tool_name: name, tool_call_id: id, parameters: params || {} } });
  return id;
}
function results(ws, id) { return ws.sent.filter(x => x.type === 'client_tool_result' && x.tool_call_id === id).map(x => JSON.parse(x.result)); }
async function call(E, ws, name, params, ms) { const id = send(ws, name, params); await E.advance(ms == null ? 60 : ms); return results(ws, id); }

function fakeTour(E, steps) {
  const rec = { start: [], next: 0, stop: [], pause: 0, attached: [] };
  const st = { on: false, i: -1, voice: false, paused: false };
  const T = {
    start: (o) => { rec.start.push(o); st.on = true; st.i = 0; st.voice = !!(o && o.voice); return { step: 1, of: steps.length, say: steps[0] }; },
    next: () => { rec.next++; if (st.i + 1 >= steps.length) { st.on = false; return { done: true }; } st.i++; st.paused = false; return { step: st.i + 1, of: steps.length, say: steps[st.i] }; },
    stop: (r) => { rec.stop.push(r); st.on = false; },
    pause: () => { rec.pause++; st.paused = true; },
    state: () => ({ on: st.on, i: st.i, of: steps.length, voice: st.voice, paused: st.paused, premium: false, say: st.on ? steps[st.i] : null }),
    voiceAttached: (v) => { rec.attached.push(v); st.voice = !!v; },
  };
  E.ctx.BixbyCockpit = { tour: T, demo: () => { rec.demo = (rec.demo || 0) + 1; } };
  return { rec, st };
}
async function session(E) {
  await E.V.connect();
  const ws = E.sockets[0]; ws._open();
  ws._msg(META('pcm_16000', 'pcm_16000'));
  return ws;
}
function speak(ws, seconds, eid) {   // audio del agente: `seconds` de PCM a 16 kHz (eid: respuesta posterior a una interrupción)
  ws._msg({ type: 'audio', audio_event: { audio_base_64: b64pcm(new Array(Math.round(16000 * seconds)).fill(800)), event_id: eid || 1 } });
}

async function main() {
  const R = {};
  const S = { data: { signed_url: 'wss://api.elevenlabs.io/v1/convai/conversation?agent_id=a&conversation_signature=s', overrides: {}, language: 'es' } };
  const STEPS = ['Uno.', 'Dos.', 'Tres.'];
  {
    const E = makeEnv({ session: S }); const { rec, st } = fakeTour(E, STEPS); const ws = await session(E);
    const ctxNow = () => E.V.audioCtx;
    // contexto sin recorrido: sin clave tour
    let n0 = ws.sent.length; E.V.updateContext();
    R.ctxOff = JSON.parse(ws.sent.slice(n0)[0].text.slice('[CONTEXT_UPDATE] '.length));
    R.start = await call(E, ws, 'run_guided_demo', {});
    R.startAgain = await call(E, ws, 'run_guided_demo', { action: 'start' });
    R.startCalls = rec.start.slice();
    n0 = ws.sent.length; E.V.updateContext();
    R.ctxOn = JSON.parse(ws.sent.slice(n0).filter(m => m.type === 'contextual_update')[0].text.slice('[CONTEXT_UPDATE] '.length));
    // Khipu está diciendo la frase 1 (1 s de audio por delante del reloj): `next` espera
    speak(ws, 1.0);
    R.cursor = E.V._playCursor;
    const id = send(ws, 'run_guided_demo', { action: 'next' });
    await E.advance(600);
    R.nextWhileSpeaking = results(ws, id).length; R.nextCallsWhileSpeaking = rec.next;
    ctxNow().currentTime = R.cursor - 0.1;                // ya casi terminó (≤0,15 s)
    await E.advance(200);
    R.nextAfter = results(ws, id); R.nextCallsAfter = rec.next;
    // la frase 2 sonó entera (llegó su audio y terminó; sin trozos nuevos hace >0,7 s) → responde
    speak(ws, 0.2);
    ctxNow().currentTime = E.V._playCursor + 1; E.V._playCursor = 0;
    R.nextQuick = await call(E, ws, 'run_guided_demo', { action: 'next' }, 900);
    // interrupción / el usuario habla → pausa
    ws._msg({ type: 'interruption', interruption_event: { event_id: 50 } });
    ws._msg({ type: 'user_transcript', user_transcription_event: { user_transcript: 'espera' } });
    R.pauses = rec.pause;
    // fin: next después del último paso → done
    R.done = await call(E, ws, 'run_guided_demo', { action: 'next' }, 4500);   // la frase 3 nunca sonó: espera ~4 s
    R.afterDone = await call(E, ws, 'run_guided_demo', { action: 'next' });
    // audio que nunca termina: responde a ~25 s (antes del tope de 30 s, nunca "pending")
    await call(E, ws, 'run_guided_demo', { action: 'start' });
    E.V._playCursor = ctxNow().currentTime + 500;
    const id2 = send(ws, 'run_guided_demo', { action: 'next' });
    await E.advance(24000);
    R.stuckBefore = results(ws, id2).length;
    await E.advance(1500);
    R.stuckAfter = results(ws, id2);
    E.V._playCursor = 0;
    // el usuario cierra (✕): aviso silencioso al agente y los `next` siguientes → stopped
    n0 = ws.sent.length;
    R.closedSent = E.V.tourClosed();
    R.closedMsg = ws.sent.slice(n0);
    st.on = false;
    R.afterClose = await call(E, ws, 'run_guided_demo', { action: 'next' });
    // stop del agente
    await call(E, ws, 'run_guided_demo', { action: 'start' });
    R.stop = await call(E, ws, 'run_guided_demo', { action: 'stop' });
    R.stopCalls = rec.stop.slice();
    R.weird = await call(E, ws, 'run_guided_demo', { action: 'dance' });   // acción desconocida → start
    // pedido desde la interfaz
    n0 = ws.sent.length;
    R.req = E.V.requestTour(); R.reqMsg = ws.sent.slice(n0);
    // colgar a mitad del recorrido narrado → sigue en pantalla
    E.V.disconnect();
    R.attached = rec.attached.slice();
    R.reqClosed = E.V.requestTour();
    R.closedClosed = E.V.tourClosed();
    R.errors = E.errors;
  }
  {   // inglés + una Cabina vieja sin BixbyCockpit.tour
    const E = makeEnv({ session: S, lang: 'en' }); const ws = await session(E);
    const n0 = ws.sent.length; R.reqEn = E.V.requestTour(); R.reqEnMsg = ws.sent.slice(n0);
    let demo = 0, stops = [];
    E.ctx.BixbyCockpit = { demo: () => { demo++; }, demoStop: (r) => stops.push(r) };
    R.oldStart = await call(E, ws, 'run_guided_demo', {}); R.oldDemo = demo;
    R.oldNext = await call(E, ws, 'run_guided_demo', { action: 'next' });
    R.oldStop = await call(E, ws, 'run_guided_demo', { action: 'stop' }); R.oldStops = stops;
    E.ctx.BixbyCockpit = undefined;
    R.noCockpit = await call(E, ws, 'run_guided_demo', {});
    R.errorsEn = E.errors;
  }
  {   // interrumpir MIENTRAS un `next` espera: no avanza (pausa); el `next` siguiente (el "sí") reanuda
    const E = makeEnv({ session: S }); const { rec, st } = fakeTour(E, ['Uno.', 'Dos.', 'Tres.', 'Cuatro.']); const ws = await session(E);
    const ctxNow = () => E.V.audioCtx;
    await call(E, ws, 'run_guided_demo', {});
    speak(ws, 3.0);
    const id = send(ws, 'run_guided_demo', { action: 'next' });
    await E.advance(500);
    R.intBefore = results(ws, id).length;
    ws._msg({ type: 'interruption', interruption_event: { event_id: 50 } });
    await E.advance(300);
    R.intRes = results(ws, id); R.intNext = rec.next; R.intPaused = st.paused;
    R.intResume = await call(E, ws, 'run_guided_demo', { action: 'next' }, 300);
    R.intNext2 = rec.next;
    // el `next` llega ANTES que el audio de la frase: espera a que suene y termine
    const id2 = send(ws, 'run_guided_demo', { action: 'next' });
    await E.advance(1000);
    R.earlyNoAudio = results(ws, id2).length;
    speak(ws, 0.5, 60);
    await E.advance(400);
    R.earlyPlaying = results(ws, id2).length;
    ctxNow().currentTime = E.V._playCursor + 0.01; E.V._playCursor = 0;   // terminó lo agendado…
    await E.advance(150);
    R.earlyGap = results(ws, id2).length;                                    // …pero un hueco <0,7 s no es el final
    await E.advance(450);
    R.earlyAfter = results(ws, id2);
    // la frase nunca suena (sin audio): responde a los ~4 s, no al instante
    const id3 = send(ws, 'run_guided_demo', { action: 'next' });
    await E.advance(3000);
    R.silentBefore = results(ws, id3).length;
    await E.advance(1300);
    R.silentAfter = results(ws, id3);
    R.errorsInt = E.errors;
  }
  {   // colgar MIENTRAS un `next` espera: el recorrido sigue en pantalla con sus tiempos; ese `next` no avanza
    const E = makeEnv({ session: S }); const { rec } = fakeTour(E, STEPS); const ws = await session(E);
    await call(E, ws, 'run_guided_demo', {});
    speak(ws, 3.0);
    send(ws, 'run_guided_demo', { action: 'next' });
    await E.advance(500);
    E.V.disconnect();
    await E.advance(400);
    R.hangNext = rec.next; R.hangAttached = rec.attached.slice();
    R.errorsHang = E.errors;
  }
  {   // el recorrido corre con temporizadores (lo empezó la interfaz) y el agente pide `next`: la voz lo toma
    const E = makeEnv({ session: S }); const { rec, st } = fakeTour(E, STEPS); const ws = await session(E);
    rec.start.length = 0; st.on = true; st.i = 0; st.voice = false;
    R.timedNext = await call(E, ws, 'run_guided_demo', { action: 'next' }, 4500);
    R.timedAttached = rec.attached.slice(); R.timedVoice = st.voice;
    R.errorsTimed = E.errors;
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
    for k in ('errors', 'errorsEn', 'errorsInt', 'errorsHang', 'errorsTimed'):
        assert out[k] == [], (k, out[k])
    return out


def test_voice_start_is_voice_led_and_idempotent(V):
    assert V['start'] == [{'success': True, 'step': 1, 'of': 3, 'say': 'Uno.',
                           'note': 'Say exactly the "say" line and nothing else. The app then sends you each next line as a '
                                   'message that starts with [TOUR n/N]: say exactly the text after the tag, nothing else, '
                                   'and do not call any tool for it.'}]   # la APP marca el ritmo (test_voice_tour_drive.py)
    assert V['startAgain'][0]['step'] == 1 and V['startAgain'][0]['say'] == 'Uno.'
    assert V['startCalls'] == [{'voice': True}]                          # el segundo start no reinicia
    assert 'tour' not in V['ctxOff'] and V['ctxOn']['tour'] == {'on': True, 'step': 1, 'of': 3}


def test_voice_next_waits_until_khipu_finished_the_line(V):
    assert V['cursor'] > 0.9
    assert V['nextWhileSpeaking'] == 0 and V['nextCallsWhileSpeaking'] == 0
    assert V['nextAfter'] == [{'success': True, 'step': 2, 'of': 3, 'say': 'Dos.'}] and V['nextCallsAfter'] == 1
    assert V['nextQuick'] == [{'success': True, 'step': 3, 'of': 3, 'say': 'Tres.'}]
    assert V['pauses'] == 2                                               # interrupción + el usuario habló
    assert V['done'] == [{'success': True, 'done': True, 'note': 'Tour finished: stay quiet and wait.'}]
    assert V['afterDone'][0]['stopped'] is True and V['afterDone'][0]['success'] is False


def test_voice_interruption_while_next_waits_pauses_instead_of_advancing(V):
    assert V['intBefore'] == 0
    assert V['intNext'] == 0 and V['intPaused'] is True                   # la pantalla NO avanzó
    r = V['intRes']
    assert len(r) == 1 and r[0]['success'] is True and r[0]['paused'] is True and r[0]['step'] == 1 and 'say' not in r[0]
    assert 'ask whether to continue' in r[0]['note']
    assert V['intResume'] == [{'success': True, 'step': 2, 'of': 4, 'say': 'Dos.'}] and V['intNext2'] == 1   # "sí" → sigue
    assert V['hangNext'] == 0 and V['hangAttached'] == [False]            # colgar: no avanza por un `next` viejo


def test_voice_next_waits_for_the_line_to_actually_sound(V):
    assert V['earlyNoAudio'] == 0 and V['earlyPlaying'] == 0 and V['earlyGap'] == 0
    assert V['earlyAfter'] == [{'success': True, 'step': 3, 'of': 4, 'say': 'Tres.'}]
    assert V['silentBefore'] == 0
    assert V['silentAfter'] == [{'success': True, 'step': 4, 'of': 4, 'say': 'Cuatro.'}]


def test_voice_next_on_a_timed_tour_takes_it_over(V):
    assert V['timedAttached'] == [True] and V['timedVoice'] is True
    assert V['timedNext'] == [{'success': True, 'step': 2, 'of': 3, 'say': 'Dos.'}]


def test_voice_next_answers_before_the_30s_limit(V):
    assert V['stuckBefore'] == 0
    assert len(V['stuckAfter']) == 1 and V['stuckAfter'][0]['success'] is True
    assert 'pending' not in V['stuckAfter'][0] and V['stuckAfter'][0]['step'] == 2


def test_voice_close_stop_and_unknown_action(V):
    assert V['closedSent'] is True
    assert V['closedMsg'] == [{'type': 'contextual_update', 'text': '[CONTEXT_UPDATE] {"tour":"closed by the user"}'}]
    assert V['afterClose'] == [{'success': False, 'stopped': True, 'note': 'The tour was closed; do not continue it.'}]
    assert V['stop'] == [{'success': True, 'stopped': True}] and V['stopCalls'] == ['voice']
    assert V['weird'][0]['success'] is True and V['weird'][0]['step'] == 1


def test_request_tour_message_and_disconnect(V):
    assert V['req'] is True and V['reqMsg'] == [{'type': 'user_message', 'text': 'Hazme el recorrido guiado de un minuto.'}]
    assert V['reqEn'] is True and V['reqEnMsg'] == [{'type': 'user_message', 'text': 'Give me the one-minute guided tour.'}]
    assert V['attached'] == [False]                                       # colgar: el recorrido sigue en pantalla
    assert V['reqClosed'] is False and V['closedClosed'] is False


def test_voice_with_an_old_cockpit_still_answers(V):
    assert V['oldStart'][0]['success'] is True and V['oldDemo'] == 1
    assert V['oldNext'][0]['stopped'] is True
    assert V['oldStop'] == [{'success': True, 'stopped': True}] and V['oldStops'] == ['voice']
    nc = V['noCockpit'][0]
    assert nc['success'] is False and nc['error'] == 'The tour is not available right now.'


# ═══════════════════════════════ la Cabina REAL en Chromium ═══════════════════════════════
PAGE = r"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>html,body{margin:0;height:100%;font-family:system-ui}</style>
</head><body><main id="mainmap" style="display:flex"><div>mapa</div></main>
<script>
window.LANG = 'es';
window.NODES = [
  { id: 'Nvidia', label: 'Nvidia', mkt: 'NVDA', cat: 'gpu', margin: 0.55, growth: '🟢' },
  { id: 'TSMC', label: 'TSMC', mkt: 'TSM', cat: 'foundry', margin: 0.4, growth: '🟢' },
  { id: 'OpenAI', label: 'OpenAI', cat: 'lab', margin: -0.2, growth: '🟢' },
  { id: 'Microsoft', label: 'Microsoft', mkt: 'MSFT', cat: 'cloud', margin: 0.45, growth: '🟢' },
  { id: 'AMD', label: 'AMD', mkt: 'AMD', cat: 'gpu', margin: 0.2, growth: '🟡' }];
window.NODE_BY_ID = {}; window.NODES.forEach(function (n) { window.NODE_BY_ID[n.id] = n; });
window.LINKS = [
  { source: 'TSMC', target: 'Nvidia', type: 'supply', w: 9 },
  { source: 'Nvidia', target: 'OpenAI', type: 'supply', w: 8 },
  { source: 'Nvidia', target: 'Microsoft', type: 'supply', w: 7 },
  { source: 'Microsoft', target: 'OpenAI', type: 'cloud', w: 8 }];
window.SECTORS9 = {}; window.CAT_TO_SECTOR = {};
window.computeNRS = function () { return 40; };
window._liveRecolorByImpact = function () {};
window.jumpTo = function () {};
window.__media = { play: 0, speak: 0, created: 0, revoked: 0, srcs: [], errors: 0 };
window.__csp = [];
document.addEventListener('securitypolicyviolation', function (e) { window.__csp.push(e.violatedDirective + ' ' + e.blockedURI); });
(function () {
  var p0 = HTMLMediaElement.prototype.play;
  HTMLMediaElement.prototype.play = function () {
    window.__media.play++; window.__media.srcs.push(this.getAttribute('src'));
    var a = this; if (!a.__khErr) { a.__khErr = 1; a.addEventListener('error', function () { window.__media.errors++; }); }
    window.__media.last = a;
    return p0.apply(this, arguments);
  };
  if (window.speechSynthesis) window.speechSynthesis.speak = function () { window.__media.speak++; };
  var c0 = URL.createObjectURL, r0 = URL.revokeObjectURL;
  URL.createObjectURL = function (b) { window.__media.created++; return c0.call(URL, b); };
  URL.revokeObjectURL = function (u) { window.__media.revoked++; return r0.call(URL, u); };
})();
</script><button id="lang-toggle" style="display:none" onclick="window.LANG = window.LANG === 'en' ? 'es' : 'en'">lang</button></body></html>"""

SCRIPTS = ('toast.js', 'agents_registry.js', 'mascot.js', 'desktop.js', 'khipu_chat.js', 'statematrix.js', 'tour_script.js',
           'trade.js', 'voice.js', 'cockpit.js', 'oswindows.js')


def _wav(seconds=0.25, rate=8000):
    n = int(seconds * rate)
    data = b'\x00\x00' * n
    return (b'RIFF' + struct.pack('<I', 36 + len(data)) + b'WAVEfmt ' + struct.pack('<IHHIIHH', 16, 1, 1, rate, rate * 2, 2, 16)
            + b'data' + struct.pack('<I', len(data)) + data)


def _chromium(p):
    for kw in ({'args': ['--autoplay-policy=no-user-gesture-required']},
               {'executable_path': '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
                'args': ['--no-sandbox', '--autoplay-policy=no-user-gesture-required']}):
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


def _csp():
    import server
    return server.CONTENT_SECURITY_POLICY


def _page(browser, lang='es', size=(1366, 900), clips=False):
    """La Cabina REAL servida con la MISMA Content-Security-Policy que server.py (default-src 'self', sin media-src):
    sin ella, el audio de los clips se probaba con blob: que en producción la CSP bloquea. `clips`: False (404 = sin
    voz), True (WAV de 0,25 s) o una función paso → (status, content_type, body)."""
    c = browser.new_context(viewport={'width': size[0], 'height': size[1]}, service_workers='block')
    tour_reqs = []

    def handler(route):
        url = route.request.url
        path = url[len('http://khipu.test'):].split('?')[0]
        if path in ('', '/'):
            return route.fulfill(status=200, content_type='text/html', headers={'Content-Security-Policy': _csp()},
                                 body=PAGE.replace("window.LANG = 'es'", "window.LANG = '%s'" % lang))
        if path.startswith('/api/voice/tour/'):
            tour_reqs.append(url[len('http://khipu.test'):])
            if callable(clips):
                st, ct, body = clips(int(path.rsplit('/', 1)[1]))
                return route.fulfill(status=st, content_type=ct, body=body)
            if clips:
                return route.fulfill(status=200, content_type='audio/mpeg', body=_wav())
            return route.fulfill(status=404, content_type='application/json',
                                 body=json.dumps({'error': 'La voz de Khipu no está configurada.', 'error_en': 'Khipu voice is not configured.',
                                                  'code': 'not_configured', 'available': False}))
        return route.fulfill(status=503, content_type='application/json', body='{"error":"sin servidor"}')
    c.route('http://khipu.test/**', handler)
    pg = c.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append('pageerror: ' + str(e)))
    # los 404/503 de red que el navegador anota solos ("Failed to load resource") son esperados aquí
    pg.on('console', lambda m: errs.append('console: ' + m.text) if m.type == 'error' and 'Failed to load resource' not in m.text else None)
    pg.goto('http://khipu.test/')
    for s in SCRIPTS:
        pg.add_script_tag(content=_r('engine', s))
    pg.evaluate('BixbyCockpit.open()')
    pg.wait_for_timeout(300)
    return c, pg, errs, tour_reqs


_SNAP = """() => {
  const s = BixbyCockpit.tour.state();
  const txt = document.querySelector('#bcp-demotxt .bcp-demosr');
  const wins = [...document.querySelectorAll('.kd-win')].filter(w => getComputedStyle(w).display !== 'none' && !w.classList.contains('kd-min'));
  const ce = document.getElementById('kd-center');
  const cr = ce && getComputedStyle(ce).display !== 'none' ? ce.getBoundingClientRect() : null;
  const overlap = (a, b) => !!(a && b && a.left < b.right - 1 && b.left < a.right - 1 && a.top < b.bottom - 1 && b.top < a.bottom - 1);
  return { on: s.on, i: s.i, of: s.of, premium: s.premium, voice: s.voice, paused: s.paused,
    say: txt ? txt.textContent : null,
    live: (document.getElementById('bcp-demotxt') || {}).getAttribute ? document.getElementById('bcp-demotxt').getAttribute('aria-live') : null,
    bar: !!document.getElementById('bcp-demo'),
    wins: wins.map(w => ({ kind: w.getAttribute('data-kind'), max: w.classList.contains('kd-max'), overChat: overlap(w.getBoundingClientRect(), cr) })),
    centered: BixbyCockpit.isCentered(),
    hscroll: document.documentElement.scrollWidth > window.innerWidth + 1 };
}"""


def _walk(pg):
    """⏭ por todos los pasos; devuelve una foto por paso + la del final."""
    snaps = []
    pg.wait_for_function("() => { const t = document.querySelector('#bcp-demotxt .bcp-demosr'); return t && t.textContent.length > 0; }")
    for _ in range(N):
        pg.wait_for_timeout(350)
        snaps.append(pg.evaluate(_SNAP))
        pg.click('#bcp-demonext')
    pg.wait_for_timeout(400)
    end = pg.evaluate(_SNAP)
    return snaps, end


@pytest.mark.parametrize('lang', ['es', 'en'])
def test_navegador_recorrido_sin_voz_con_subtitulos_y_ventanas_al_lado(browser, lang):
    c, pg, errs, reqs = _page(browser, lang=lang)
    pg.evaluate('BixbyCockpit.demo()')
    snaps, end = _walk(pg)
    kinds = [s['act']['kind'] for s in TOUR['steps']]
    for k, (s, step) in enumerate(zip(snaps, TOUR['steps'])):
        assert s['on'] and s['i'] == k and s['of'] == N and s['bar'], (k, s)
        assert s['say'] == step[lang] and s['live'] == 'polite'
        assert s['premium'] is False and s['voice'] is False                 # sin voz contratada → solo texto
        assert len(s['wins']) <= 1, (k, s['wins'])                           # una ventana del recorrido a la vez
        assert s['hscroll'] is False
        if kinds[k] == 'empty':
            assert s['wins'] == [], (k, s['wins'])                           # solo el chat
        else:
            assert s['wins'], (k, kinds[k])
            assert s['centered'] is True
            for w in s['wins']:
                assert w['max'] is False and w['overChat'] is False, (k, w)   # AL LADO del chat, no maximizada
    by = {kinds[k]: snaps[k]['wins'] for k in range(N)}
    assert by['glance'][0]['kind'] == 'glance' and by['xray'][0]['kind'] == 'xray' and by['sim'][0]['kind'] == 'sim'
    assert by['graph'][0]['kind'] == 'graph' and by['insights'][0]['kind'] == 'insights' and by['broker'][0]['kind'] == 'broker'
    assert by['agents'][0]['kind'] == 'agents'
    assert end['on'] is False and end['bar'] is False and end['wins'] == []  # terminó: vuelve al chat solo
    # el primer clip falló (404) → no se piden más; URL del contrato
    assert reqs and reqs[0] == '/api/voice/tour/%s/0?v=%s' % (lang, TOUR['version'])
    assert len(reqs) == 1, reqs
    m = pg.evaluate('window.__media')
    assert m['play'] == 0 and m['speak'] == 0
    assert not errs, errs
    c.close()


def test_navegador_celular_ventanas_encima(browser):
    c, pg, errs, _ = _page(browser, size=(390, 844))
    pg.evaluate('BixbyCockpit.demo()')
    snaps, end = _walk(pg)
    for s in snaps:
        assert s['on'] and s['bar'] and s['hscroll'] is False
        assert s['centered'] is False
    graph = snaps[[s['act']['kind'] for s in TOUR['steps']].index('graph')]
    assert graph['wins'] and graph['wins'][0]['kind'] == 'graph'
    box = pg.evaluate("() => { const r = document.querySelector('.kd-win, #bcp-ov').getBoundingClientRect(); return [r.left, r.right]; }")
    assert box[0] >= -1 and box[1] <= 391
    assert end['on'] is False
    assert not errs, errs
    c.close()


def test_navegador_esc_sale_y_clips_premium_avanzan_solos(browser):
    c, pg, errs, reqs = _page(browser, clips=True)
    # inicio con un clic real (gesto del usuario): el enlace "Ver el recorrido de un minuto" del inicio de Khipus OS
    link = pg.locator('#kos-empty [data-q="demo"]')
    assert link.count() == 1 and link.is_visible()
    assert link.inner_text() == '▶ Ver el recorrido de un minuto'
    link.click()
    pg.wait_for_function('() => BixbyCockpit.tour.state().i >= 2', timeout=8000)   # clips de 0,25 s: avanza solo, rápido
    s = pg.evaluate(_SNAP)
    assert s['on'] and s['premium'] is True
    m = pg.evaluate('window.__media')
    assert m['play'] >= 2 and m['speak'] == 0
    # con la CSP REAL de la app: el <audio> suena desde la URL del servidor (mismo origen), nunca desde blob:
    assert m['created'] == 0 and pg.evaluate('window.__csp') == []
    assert m['errors'] == 0
    assert m['srcs'] and all(re.match(r'^/api/voice/tour/es/\d+\?v=', u) for u in m['srcs']), m['srcs']
    # prefetch: clip 0 primero, después en orden; formato del contrato
    idx = [int(re.match(r'/api/voice/tour/es/(\d+)\?v=' + re.escape(TOUR['version']) + '$', u).group(1)) for u in reqs]
    # (con page.route Chromium no usa su caché HTTP: el <audio> vuelve a pedir la MISMA URL que se precargó)
    assert list(dict.fromkeys(idx))[:3] == [0, 1, 2] and max(idx.count(i) for i in set(idx)) <= 2, idx
    pg.keyboard.press('Escape')
    pg.wait_for_timeout(200)
    s2 = pg.evaluate(_SNAP)
    assert s2['on'] is False and s2['bar'] is False
    m2 = pg.evaluate('window.__media')
    assert m2['created'] == 0 and m2['revoked'] == 0                       # sin object URLs (la CSP los bloquea)
    assert pg.evaluate('BixbyCockpit.isOpen()') is True                    # Esc sale del recorrido, no de Khipus OS
    assert not errs, errs
    c.close()


def test_navegador_con_la_voz_conectada_no_suena_nada_aqui(browser):
    c, pg, errs, reqs = _page(browser)
    pg.evaluate("""() => {
      window.__req = 0; window.__closed = 0;
      BixbyVoice.isConnected = true;
      BixbyVoice.getState = () => ({ state: 'listening', connected: true, connecting: false, error: '' });
      BixbyVoice.requestTour = () => { window.__req++; return true; };
      BixbyVoice.tourClosed = () => { window.__closed++; return true; };
    }""")
    pg.evaluate('BixbyCockpit.demo()')
    pg.wait_for_timeout(300)
    assert pg.evaluate('window.__req') == 1
    assert pg.evaluate('BixbyCockpit.tour.state().on') is False                # se lo pasó al agente
    # el agente no lo empezó en 8 s → aquí, SOLO texto
    pg.wait_for_function('() => BixbyCockpit.tour.state().on', timeout=10000)
    s = pg.evaluate(_SNAP)
    assert s['premium'] is False and s['voice'] is False and s['say'] == TOUR['steps'][0]['es']
    pg.click('#bcp-demomute')                                                  # pedir sonido: igual no suena (eco)
    pg.wait_for_timeout(200)
    pg.evaluate("BixbyCockpit.tour.stop()")
    # el agente lo narra: sin ⏸/⏭/🔊, no avanza solo, pausa y reanuda
    r = pg.evaluate('BixbyCockpit.tour.start({ voice: true })')
    assert r == {'step': 1, 'of': N, 'say': TOUR['steps'][0]['es']}
    hidden = pg.evaluate("() => ['bcp-demopause', 'bcp-demonext', 'bcp-demomute', 'bcp-demoexit'].map(id => document.getElementById(id).offsetParent === null)")
    assert hidden == [True, True, True, False]
    pg.wait_for_timeout(6000)
    assert pg.evaluate('BixbyCockpit.tour.state().i') == 0                     # el ritmo lo lleva la voz
    pg.evaluate('BixbyCockpit.tour.pause()')
    assert pg.evaluate("document.getElementById('bcp-demostate').textContent") == 'en pausa'
    nx = pg.evaluate('BixbyCockpit.tour.next()')
    assert nx['step'] == 2 and pg.evaluate('BixbyCockpit.tour.state().paused') is False
    m = pg.evaluate('window.__media')
    assert m['play'] == 0 and m['speak'] == 0
    assert reqs == []                                                          # ni un clip pedido con la voz conectada
    # la voz se corta → sigue con sus tiempos (con clips si hay voz premium); vuelve a unirse y ✕ avisa al agente
    pg.evaluate('BixbyCockpit.tour.voiceAttached(false)')
    s3 = pg.evaluate(_SNAP)
    assert s3['on'] and s3['voice'] is False and s3['i'] == 1
    assert pg.evaluate("document.getElementById('bcp-demonext').offsetParent !== null") is True
    pg.evaluate('BixbyCockpit.tour.voiceAttached(true)')
    assert pg.evaluate('BixbyCockpit.tour.state().voice') is True
    pg.click('#bcp-demoexit')
    assert pg.evaluate('window.__closed') == 1 and pg.evaluate('BixbyCockpit.tour.state().on') is False
    assert pg.evaluate('window.__media')['play'] == 0
    assert not errs, errs
    c.close()


# ═══════════════════ revisión 2026-10-12: lo que los revisores encontraron en la Cabina REAL ═══════════════════
def test_navegador_clip_roto_pasa_a_subtitulos_sin_reintentar(browser):
    # el servidor responde "audio" pero el navegador no lo puede reproducir (bloqueado / formato): no queda 🔊 mudo
    c, pg, errs, reqs = _page(browser, clips=lambda i: (200, 'audio/mpeg', b'esto no es audio'))
    pg.evaluate('BixbyCockpit.demo()')
    pg.wait_for_function('() => BixbyCockpit.tour.state().premium === false', timeout=6000)
    assert pg.evaluate("document.getElementById('bcp-demomute').textContent") == '🔇'
    n = len(reqs)
    pg.click('#bcp-demonext'); pg.wait_for_timeout(300); pg.click('#bcp-demonext'); pg.wait_for_timeout(300)
    assert len(reqs) == n                                                    # no se vuelve a intentar en cada paso
    assert pg.evaluate('window.__media')['speak'] == 0                       # y la voz del navegador solo si se pide
    assert not errs, errs
    c.close()


def test_navegador_falla_otro_clip_mientras_suena_uno(browser):
    # pasos 0 y 1 con un clip de 6 s; el 2 falla (502) en la precarga mientras el 0 todavía suena
    c, pg, errs, _ = _page(browser, clips=lambda i: (200, 'audio/mpeg', _wav(6.0)) if i < 2 else
                           (502, 'application/json', json.dumps({'error': 'x', 'error_en': 'x', 'code': 'upstream'})))
    pg.evaluate('BixbyCockpit.demo()')
    pg.wait_for_function('() => BixbyCockpit.tour.state().premium === false', timeout=6000)
    pg.wait_for_timeout(200)
    st = pg.evaluate("() => ({ btn: document.getElementById('bcp-demomute').textContent, playing: !window.__media.last.paused, i: BixbyCockpit.tour.state().i })")
    assert st == {'btn': '🔊', 'playing': True, 'i': 0}                     # suena → el botón NO dice "silenciado"
    pg.click('#bcp-demomute')                                               # silenciar: corta el clip
    st = pg.evaluate("() => ({ btn: document.getElementById('bcp-demomute').textContent, playing: !window.__media.last.paused, speak: window.__media.speak })")
    assert st == {'btn': '🔇', 'playing': False, 'speak': 0}
    pg.click('#bcp-demomute')                                               # activar sonido: la voz del navegador, SOLA
    st = pg.evaluate("() => ({ playing: !window.__media.last.paused, speak: window.__media.speak })")
    assert st == {'playing': False, 'speak': 1}
    assert not errs, errs
    c.close()


def test_navegador_demo_desde_la_interfaz_no_reemplaza_el_recorrido_de_la_voz(browser):
    c, pg, errs, reqs = _page(browser)
    pg.evaluate("""() => { window.__req = 0; BixbyVoice.isConnected = true;
      BixbyVoice.getState = () => ({ state: 'listening', connected: true, connecting: false, error: '' });
      BixbyVoice.requestTour = () => { window.__req++; return true; }; }""")
    pg.evaluate('BixbyCockpit.tour.start({ voice: true })')
    pg.evaluate('BixbyCockpit.tour.next()')
    pg.evaluate('BixbyCockpit.demo()')
    pg.wait_for_timeout(300)
    s = pg.evaluate('BixbyCockpit.tour.state()')
    assert s['on'] and s['voice'] is True and s['i'] == 1 and pg.evaluate('window.__req') == 0
    pg.wait_for_timeout(6500)
    assert pg.evaluate('BixbyCockpit.tour.state().i') == 1                  # nadie avanza con temporizadores
    assert reqs == [] and not errs, (reqs, errs)
    c.close()


def test_navegador_cambiar_idioma_a_mitad_del_recorrido(browser):
    c, pg, errs, _ = _page(browser)
    pg.evaluate('BixbyCockpit.demo()')
    pg.wait_for_timeout(200)
    pg.click('#kos-lang')                                                   # el botón ES/EN de Khipus OS
    pg.wait_for_timeout(200)
    snap = "() => ({ label: document.querySelector('.bcp-demolabel').firstChild.textContent.trim(), say: document.querySelector('#bcp-demotxt .bcp-demosr').textContent, next: document.getElementById('bcp-demonext').title })"
    assert pg.evaluate(snap) == {'label': 'ONE-MINUTE TOUR', 'say': TOUR['steps'][0]['en'], 'next': 'Next'}
    pg.evaluate('BixbyCockpit.tour.next()')
    assert pg.evaluate(snap)['say'] == TOUR['steps'][1]['en']
    # otro camino (el botón de idioma de la app): el paso siguiente ya sale en el idioma nuevo
    pg.evaluate("window.LANG = 'es'")
    pg.evaluate('BixbyCockpit.tour.next()')
    assert pg.evaluate(snap) == {'label': 'RECORRIDO DE UN MINUTO', 'say': TOUR['steps'][2]['es'], 'next': 'Siguiente'}
    assert not errs, errs
    c.close()


_COVERED = """() => {
  const bar = document.getElementById('bcp-demo');
  const body = document.querySelector('#kd-center .kos-chatbody');
  const br = body ? body.getBoundingClientRect() : null;
  const out = [];
  const sel = ['#bcp-send', '#bcp-mic', '#bcp-input', '#kd-center .kos-ag', '#kd-center .kos-chip', '#kd-center .kos-tour'];
  for (const s of sel) for (const e of document.querySelectorAll(s)) {
    const r = e.getBoundingClientRect();
    if (!r.width || !r.height) continue;
    const x = (r.left + r.right) / 2, y = (r.top + r.bottom) / 2;
    if (br && e.closest('.kos-chatbody') && (y < br.top || y > br.bottom)) continue;   // fuera de la vista del chat (se desplaza)
    const h = document.elementFromPoint(x, y);
    if (h && bar && bar.contains(h)) out.push(s);
  }
  const tw = document.querySelector('#bcp-demotxt');
  return { covered: out, txtw: tw ? Math.round(tw.getBoundingClientRect().width) : 0 };
}"""


@pytest.mark.parametrize('size,lang', [((1366, 900), 'es'), ((1366, 900), 'en'), ((390, 844), 'es')])
def test_navegador_la_barra_no_tapa_el_chat_ni_las_mascotas(browser, size, lang):
    c, pg, errs, _ = _page(browser, lang=lang, size=size)
    pg.evaluate('BixbyCockpit.demo()')
    pg.wait_for_timeout(400)
    kinds = [s['act']['kind'] for s in TOUR['steps']]
    for k in range(N):
        pg.wait_for_timeout(250)
        r = pg.evaluate(_COVERED)
        if size[0] >= 1100 or kinds[k] == 'empty':                       # celular: las hojas tapan el chat igual
            assert r['covered'] == [], (k, kinds[k], r)
        if size[0] >= 1100:
            assert r['txtw'] >= 380, (k, r)                                 # la frase usa el ancho de la columna
        if k < N - 1:
            pg.evaluate('BixbyCockpit.tour.next()')
    pg.evaluate('BixbyCockpit.tour.stop()')
    assert pg.evaluate("document.querySelector('#kd-center .kos-chatbody').style.marginBottom") == ''
    assert not errs, errs
    c.close()


def test_navegador_paleta_ofrece_el_recorrido(browser):
    c, pg, errs, _ = _page(browser)
    pg.evaluate("BixbyCockpit.palette('recorrido')")
    pg.wait_for_timeout(200)
    items = pg.evaluate("() => [...document.querySelectorAll('.kos-pi .tx')].map(e => e.textContent)")
    assert 'Ver el recorrido de un minuto' in items, items
    i = items.index('Ver el recorrido de un minuto')
    pg.click('#kos-pi-%d' % i)
    pg.wait_for_function('() => BixbyCockpit.tour.state().on', timeout=3000)
    assert not errs, errs
    c.close()


def test_hoja_del_celular_deja_espacio_bajo_la_barra_del_recorrido():
    """En pantallas chicas la ventana del recorrido es una hoja encima del chat y la barra flotaba sobre su final
    (tapaba "Pedir opinión al comité" / "Investigar"): el cuerpo de la ventana gana ese espacio abajo."""
    js = _r('engine', 'cockpit.js')
    assert '#bcp-ov.kh-tour-sheet .kd-win .kd-body{padding-bottom:var(--kh-tour-room,0px)}' in js
    fn = js[js.index('function _tourChatRoom(px)'):js.index('function _tourPlaceBar()')]
    assert "classList.toggle('kh-tour-sheet', sheet)" in fn and '!isCentered()' in fn and "removeProperty('--kh-tour-room')" in fn
