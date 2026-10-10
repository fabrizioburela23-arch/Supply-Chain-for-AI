"""tests/test_overnight3_fixer_voice_race.py — revisión de engine/voice.js (estado público de la voz).

1. Cancelar MIENTRAS el AudioContext se reanuda (iOS lo deja 'suspended' tras abrir el micrófono): el intento
   viejo volvía a emitir "conectando" al terminar resume() y el micrófono de la Cabina quedaba trabado en
   "Conectando…" (sin socket, sin nada que lo apagara). Ahora: queda "apagado", sin pedir sesión ni abrir socket,
   y un intento NUEVO iniciado mientras tanto conserva su micrófono y conecta normal.
2. Durante el saludo del WebSocket (connect() ya terminó, el socket aún no abrió) isConnecting() era false:
   BixbyVoice.toggle() abría un SEGUNDO socket y dejaba el primero huérfano. Ahora cuenta como "conectando",
   tocar cuelga (cierra ese socket) y un connect() repetido no abre otro.
3. Un socket que quedó abierto tras fallar el micrófono (estado "error", tocar = reintentar) se cierra al
   reintentar en vez de quedar huérfano; el error no cuenta como "conectando".
4. La Cabina real en Chromium: cancelar durante el resume() → el botón queda "Hablar con Khipu".
"""
import json
import subprocess

import pytest

from tests.test_overnight3_mic_voice_state import HARNESS, NODE, VOICE_PATH, _SNAP, _page, browser  # noqa: F401

_PREFIX = HARNESS[:HARNESS.index('async function main() {')]

MAIN = r"""
// AudioContext que queda 'suspended' y cuyo resume() NO se resuelve hasta que la prueba lo diga
function suspendedCtx(E) {
  const Base = E.ctx.AudioContext, pend = [];
  class Susp extends Base {
    constructor() { super(); this.state = 'suspended'; }
    resume() { const d = deferred(); pend.push(d); return d.p.then(() => { this.state = 'running'; }); }
  }
  E.ctx.AudioContext = Susp;
  return { pend, resolveAll: () => pend.splice(0).forEach(d => d.res()) };
}
const sessionFetches = (E) => E.fetches.filter(f => f.url.endsWith('/api/voice/session')).length;

async function main() {
  const R = {};
  // ═══ 1) tocar → (micrófono OK) → resume() colgado → tocar otra vez = cancelar → resume() termina ═══
  {
    const E = makeEnv();
    const C = suspendedCtx(E);
    const p = E.V.toggle();
    await E.flush();
    R.r1_atResume = { st: E.V.getState().state, resumes: C.pend.length, mic: E.tracks.length };
    await E.V.toggle();                                   // cancelar mientras se reanuda el audio
    R.r1_cancel = E.V.getState();
    C.resolveAll(); await p; await E.advance(30000);
    R.r1_end = { st: E.V.getState(), states: E.states(), sockets: E.sockets.length, sess: sessionFetches(E),
                 micStopped: E.tracks.every(t => t.stopped), errors: E.errors };
  }
  // ═══ 1b) cancelar durante resume() y volver a tocar ANTES de que termine: el nuevo intento sigue intacto ═══
  {
    const E = makeEnv();
    const C = suspendedCtx(E);
    const p1 = E.V.toggle(); await E.flush();
    await E.V.toggle();                                   // cancelar
    const p2 = E.V.toggle(); await E.flush();             // 3.er toque: nuevo intento (también espera su resume)
    C.resolveAll(); await p1; await p2; await E.flush();
    R.r1b_mid = { st: E.V.getState().state, sockets: E.sockets.length, sess: sessionFetches(E),
                  t0: E.tracks[0].stopped, t1: E.tracks[1].stopped };
    E.sockets[0]._open(); E.sockets[0]._msg(META);
    R.r1b_live = { st: E.V.getState(), t1: E.tracks[1].stopped, errors: E.errors };
  }
  // ═══ 2) saludo del WebSocket: cuenta como "conectando"; tocar cuelga; connect() repetido no abre otro ═══
  {
    const E = makeEnv();
    await E.V.connect();
    R.r2_hs = { st: E.V.getState(), sockets: E.sockets.length, ready: E.sockets[0].readyState };
    await E.V.connect();                                  // un connect() directo durante el saludo
    R.r2_dup = E.sockets.length;
    await E.V.toggle();                                   // tocar durante el saludo = colgar
    R.r2_cut = { st: E.V.getState(), sockets: E.sockets.length, closed: E.sockets[0].closed || null };
    await E.V.toggle();                                   // tocar otra vez = conectar de nuevo (1 socket nuevo)
    R.r2_again = { st: E.V.getState().state, sockets: E.sockets.length };
    E.sockets[1]._open(); E.sockets[1]._msg(META);
    R.r2_live = E.V.getState();
    R.r2_errors = E.errors;
  }
  // ═══ 3) el micrófono falla con el socket ya abierto → error (no "conectando"); reintentar cierra ese socket ═══
  {
    const E = makeEnv();
    await E.V.connect();
    const ws = E.sockets[0]; ws._open();
    E.V.audioCtx.createScriptProcessor = () => { throw new Error('boom'); };
    ws._msg(META);
    R.r3_err = { st: E.V.getState(), ready: ws.readyState };
    E.V.audioCtx.createScriptProcessor = E.ctx.AudioContext.prototype.createScriptProcessor;
    await E.V.toggle();                                   // tocar tras el error = reintentar
    R.r3_retry = { st: E.V.getState().state, sockets: E.sockets.length, oldClosed: ws.closed || null };
    E.sockets[1]._open(); E.sockets[1]._msg(META);
    R.r3_live = E.V.getState().state;
    R.r3_errors = E.errors;
  }
  console.log(JSON.stringify(R));
}
main().catch(e => { console.error(e && e.stack || e); process.exit(1); });
"""


def _run(voice_path=VOICE_PATH):
    p = subprocess.run([NODE, '-e', _PREFIX + MAIN, voice_path], capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


@pytest.fixture(scope='module')
def race():
    if not NODE:
        pytest.skip('node no instalado')
    return _run()


def test_cancelar_durante_resume_queda_apagado(race):
    # de verdad estaba esperando el resume() (micrófono ya concedido)
    assert race['r1_atResume']['st'] == 'connecting' and race['r1_atResume']['resumes'] >= 2
    assert race['r1_atResume']['mic'] == 1
    assert race['r1_cancel']['state'] == 'off' and race['r1_cancel']['connecting'] is False
    end = race['r1_end']
    # antes: ['connecting', 'off', 'connecting'] y getState().state === 'connecting' para siempre
    assert end['states'] == ['connecting', 'off'], end['states']
    assert end['st']['state'] == 'off' and end['st']['connecting'] is False and end['st']['connected'] is False
    assert end['sockets'] == 0 and end['sess'] == 0         # el intento cancelado no pide sesión ni abre socket
    assert end['micStopped'] is True and end['errors'] == []


def test_cancelar_durante_resume_no_pisa_el_intento_nuevo(race):
    mid = race['r1b_mid']
    assert mid['t0'] is True and mid['t1'] is False         # solo se suelta el micrófono del intento cancelado
    assert mid['st'] == 'connecting' and mid['sockets'] == 1 and mid['sess'] == 1
    live = race['r1b_live']
    assert live['st']['state'] == 'listening' and live['st']['connected'] is True and live['t1'] is False
    assert live['errors'] == []


def test_saludo_del_socket_cuenta_como_conectando_y_tocar_cuelga(race):
    hs = race['r2_hs']
    assert hs['sockets'] == 1 and hs['ready'] == 0
    assert hs['st']['state'] == 'connecting' and hs['st']['connecting'] is True and hs['st']['connected'] is False
    assert race['r2_dup'] == 1                               # connect() repetido no abre un 2.º socket
    cut = race['r2_cut']
    # antes: toggle() abría un 2.º socket y dejaba el 1.º huérfano (sin cerrar)
    assert cut['sockets'] == 1 and cut['closed'] and cut['closed']['code'] == 1000
    assert cut['st']['state'] == 'off' and cut['st']['connecting'] is False
    assert race['r2_again'] == {'st': 'connecting', 'sockets': 2}
    assert race['r2_live']['state'] == 'listening' and race['r2_live']['connected'] is True
    assert race['r2_errors'] == []


def test_error_con_socket_abierto_no_es_conectando_y_reintentar_lo_cierra(race):
    err = race['r3_err']
    assert err['st']['state'] == 'error' and err['st']['connecting'] is False and err['ready'] == 1
    retry = race['r3_retry']
    assert retry['st'] == 'connecting' and retry['sockets'] == 2
    assert retry['oldClosed'] and retry['oldClosed']['code'] == 1000   # ya no queda huérfano
    assert race['r3_live'] == 'listening' and race['r3_errors'] == []


# ═══════════════════════ 4. la Cabina real: cancelar durante el resume() del audio ═══════════════════════
def test_navegador_cancelar_durante_resume_boton_apagado(browser):  # noqa: F811
    c, pg, errs = _page(browser)
    pg.evaluate("""() => { window.__mic.mode = 'grant'; window.__resumes = [];
      window.AudioContext.prototype.resume = function () { var self = this;
        return new Promise(function (res) { window.__resumes.push(function () { self.state = 'running'; res(); }); }); };
      var Orig = window.AudioContext;
      window.AudioContext = function () { Orig.call(this); this.state = 'suspended'; };
      window.AudioContext.prototype = Orig.prototype; }""")
    pg.click('#bcp-mic')
    pg.wait_for_function('window.__resumes.length >= 2')     # micrófono concedido; esperando el resume()
    assert pg.evaluate(_SNAP)['voice'] == 'connecting'
    pg.click('#bcp-mic')                                     # cancelar
    s = pg.evaluate(_SNAP)
    assert s['voice'] == 'off' and s['title'] == 'Hablar con Khipu'
    pg.evaluate('() => window.__resumes.forEach(function (f) { f(); })')
    pg.wait_for_timeout(400)
    s = pg.evaluate(_SNAP)
    assert s['vstate'] == 'off' and s['voice'] == 'off', s
    for k in ('on', 'conn', 'err'):
        assert k not in s['cls'].split(), s
    assert s['title'] == 'Hablar con Khipu' and s['pressed'] == 'false' and not s['pillShown']
    assert pg.evaluate('window.__ws.length') == 0
    assert not errs, errs
    c.close()
