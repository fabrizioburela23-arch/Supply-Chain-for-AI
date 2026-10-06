"""Khipus OS v1 — arreglos de velocidad/arranque tras la revisión (engine/brief.js + app.html).

Cada prueba falla con el código anterior al arreglo y pasa con el nuevo:
  #15 las tarjetas del brief abierto desde la paleta (⌘K) del OS movían el mapa clásico OCULTO detrás
      del OS (switchTab + jumpTo a ciegas): el clic no hacía nada visible. Ahora van por _surface('graph').
  #16 si cockpit.js nunca cargaba, el mapa de respaldo quedaba en blanco desde que se iba el splash
      (~3 s) hasta los 12 s: _mapBootWaiting solo aceptaba "splash fuera" si la Cabina ya existía.
Reutiliza los arneses de tests/test_khipus_os_perf.py (el código REAL de app.html / brief.js corre en node).
"""
import json
import re
import shutil
import subprocess

import pytest

from tests.test_khipus_os_perf import BRIEF, HTML, _brief_js, _map_js

NODE = shutil.which('node')


# ════════════════════════════════════════════════════════════════════════════
# #15 · Brief: ir a la empresa de una tarjeta SIEMPRE por _surface
# ════════════════════════════════════════════════════════════════════════════

_JUMP_SETUP = r'''
  const calls = { surface: [], tab: [], jump: [] };
  window.BixbyCockpit = { isOpen: () => true, open() {} };     // Khipus OS abierto
  window.switchTab = t => calls.tab.push(t);
  window.jumpTo = id => calls.jump.push(id);
'''


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_15_tarjeta_del_brief_con_khipus_os_abre_la_ventana_grafo():
    o = _brief_js(_JUMP_SETUP + r'''
      window._surface = (k, a) => { calls.surface.push([k, a]); return true; };   // la ventana Grafo se abre
      /*LOAD*/
      window._briefOpen(); await wait(40);
      out.openBefore = els['brief-ov'].classList.contains('show');
      window._briefJump('b'); await wait(160);
      out.calls = calls; out.openAfter = els['brief-ov'].classList.contains('show');
    ''')
    assert o['openBefore'] is True and o['openAfter'] is False     # el brief se cierra
    assert o['calls']['surface'] == [['graph', 'b']]               # un solo camino: _surface('graph', id)
    # nada de mover el mapa clásico escondido detrás del OS
    assert o['calls']['tab'] == [] and o['calls']['jump'] == []


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_15_sin_surface_o_si_no_pudo_queda_el_salto_clasico():
    # _surface no cargó (resolve.js falló) → la receta de siempre: pestaña Mapa + jumpTo
    o = _brief_js(_JUMP_SETUP + r'''
      /*LOAD*/
      window._briefJump('c'); await wait(160);
      out.calls = calls;
    ''')
    assert o['calls']['tab'] == ['map'] and o['calls']['jump'] == ['c']
    # _surface existe pero dice que no pudo (false) o revienta → también la receta de siempre
    for impl in ('() => false', '() => { throw new Error("x"); }'):
        o = _brief_js(_JUMP_SETUP + 'window._surface = ' + impl + ';\n' + r'''
          /*LOAD*/
          window._briefJump('a'); await wait(160);
          out.calls = calls;
        ''')
        assert o['calls']['tab'] == ['map'] and o['calls']['jump'] == ['a'], impl


def test_15_estatico_brief_jump_pasa_por_surface_antes_que_switchtab():
    m = re.search(r"window\._briefJump = function \(id\) \{.*?\n  \};", BRIEF, re.S)
    assert m
    fn = m.group(0)
    assert "_surface('graph', id)" in fn
    assert fn.index("_surface('graph', id)") < fn.index("switchTab('map')")


# ════════════════════════════════════════════════════════════════════════════
# #16 · Mapa: deja de esperar al OS cuando el splash ya se fue aunque cockpit.js no cargue
# ════════════════════════════════════════════════════════════════════════════

@pytest.mark.skipif(not NODE, reason='requiere node')
def test_16_splash_fuera_y_cabina_que_nunca_cargo_el_mapa_se_ordena():
    o = _map_js(r'''
      // window.BixbyCockpit NO existe (cockpit.js dio 404 / error de sintaxis) y el respaldo fijo de 3 s
      // ya quitó el splash: el mapa es lo que se ve
      bootEl = { classList: { contains: c => c === 'gone' } };
      resize(); out.first = ticks; out.waitingFirst = window._mapState().bootWaiting;   // respiro de 600 ms
      await wait(650); resize(); await settled();
      out.ticks = ticks; out.state = window._mapState();
    ''')
    assert o['first'] == 0 and o['waitingFirst'] is True
    assert o['ticks'] > 0 and o['state']['laid'] is True
    assert o['state']['osExpected'] is False and o['state']['bootWaiting'] is False
    # #boot ya removido del DOM → lo mismo
    o = _map_js(r'''
      resize(); await wait(650); resize(); await settled();
      out.laid = _mapLaidOnce;
    ''')
    assert o['laid'] is True


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_16_arranque_que_se_rindio_libera_el_mapa_al_instante():
    o = _map_js(r'''
      bootEl = { classList: { contains: () => false } };    // el splash todavía está (se está desvaneciendo)
      window.__khOsGaveUp = true;                           // tryLand agotó sus 90 intentos
      resize(); await settled();
      out.ticks = ticks; out.state = window._mapState();
    ''')
    assert o['ticks'] > 0 and o['state']['laid'] is True and o['state']['osExpected'] is False


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_16_con_el_splash_encima_sigue_esperando_y_si_el_os_llega_tarde_se_pausa():
    # comportamiento conservado: splash todavía encima, sin rendición → el mapa sigue esperando al OS
    o = _map_js(r'''
      bootEl = { classList: { contains: () => false } };
      resize(); await wait(650); resize(); await wait(20);
      out.ticks = ticks; out.waiting = window._mapState().bootWaiting;
    ''')
    assert o['ticks'] == 0 and o['waiting'] is True
    # la Cabina llega tarde (después del respiro) y se abre → el asentado por porciones se pausa solo
    o = _map_js(r'''
      bootEl = { classList: { contains: c => c === 'gone' } };
      tickMs = 6;
      resize(); await wait(650); resize();                  // empieza el primer asentado por porciones
      out.started = window._mapState().settling;
      await wait(0);
      window.BixbyCockpit = { isOpen: () => true, open() {} };   // el OS se abrió por fin, sin el mapa adentro
      await wait(60);
      out.paused = window._mapState().paused; out.laid = _mapLaidOnce;
    ''')
    assert o['started'] is True and o['paused'] is True and o['laid'] is False


def _try_block():
    m = re.search(r"\n  try \{\n    let classic = false;.*?\n  \} catch \(e\) \{[^\n]*\}\n", HTML, re.S)
    assert m, 'bloque de arranque hacia Khipus OS no encontrado'
    return m.group(0)


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_16_tryland_avisa_al_mapa_cuando_se_rinde():
    """El código REAL del arranque (tryLand) corre en node con relojes falsos y sin cockpit.js."""
    js = r'''
      const timers = []; let fades = 0, now = 0;
      global.setTimeout = (f, ms) => { timers.push([now + (ms || 0), f]); };
      global.window = {};
      global.sessionStorage = { getItem: () => null, setItem() {} };
      const NODES = [{ id: 'a' }];
      const fadeBoot = () => { fades++; };
      (function () {
    ''' + _try_block() + r'''
      })();
      let steps = 0;
      while (timers.length && steps++ < 1000) {
        timers.sort((a, b) => a[0] - b[0]); const [t, f] = timers.shift(); now = t; f();
      }
      process.stdout.write(JSON.stringify({ gaveUp: window.__khOsGaveUp === true, fades, at: now, steps }));
    '''
    r = subprocess.run([NODE, '-e', js], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    o = json.loads(r.stdout)
    assert o['gaveUp'] is True and o['fades'] == 1
    assert 8900 <= o['at'] <= 9200                          # ~9 s: 60 ms + 89 × 100 ms


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_16_tryland_con_cabina_no_se_rinde():
    js = r'''
      const timers = []; let fades = 0, opened = 0, now = 0;
      global.setTimeout = (f, ms) => { timers.push([now + (ms || 0), f]); };
      global.window = { BixbyCockpit: { open() { opened++; } } };
      global.sessionStorage = { getItem: () => null, setItem() {} };
      const NODES = [{ id: 'a' }];
      const fadeBoot = () => { fades++; };
      (function () {
    ''' + _try_block() + r'''
      })();
      let steps = 0;
      while (timers.length && steps++ < 1000) {
        timers.sort((a, b) => a[0] - b[0]); const [t, f] = timers.shift(); now = t; f();
      }
      process.stdout.write(JSON.stringify({ gaveUp: window.__khOsGaveUp === true, fades, opened }));
    '''
    r = subprocess.run([NODE, '-e', js], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    o = json.loads(r.stdout)
    assert o == {'gaveUp': False, 'fades': 1, 'opened': 1}
