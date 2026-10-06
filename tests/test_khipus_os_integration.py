"""Khipus OS v1 — integración (2026-10-06): lo que se ajustó al unir las 5 piezas."""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _r(p):
    return open(os.path.join(ROOT, p), encoding='utf-8').read()


def test_scripts_nuevos_cargados_y_en_cache():
    html, sw = _r('app.html'), _r('sw.js')
    i_m, i_w, i_c = html.index('src="engine/mascot.js"'), html.index('src="engine/oswindows.js"'), html.index('src="engine/cockpit.js"')
    assert i_m < i_c and i_w < i_c                       # antes de la Cabina (registerKind usa la cola si hace falta)
    assert "'/engine/mascot.js'" in sw and "'/engine/oswindows.js'" in sw


def test_celular_y_tablet_usan_el_chat_a_pantalla_completa():
    d, c = _r('engine/desktop.js'), _r('engine/cockpit.js')
    assert "'#bcp-stage.kd-solo #kd-center{display:flex" in d and 'chatInCenter:' in d and 'isSolo:' in d
    assert 'var sOn = !on && flankOn();' in d                 # sin lugar para flancos → solo chat (si el OS está activo)
    assert 'function chatCentered()' in c
    # el hilo/inicio usan chatCentered; las ventanas automáticas siguen exigiendo flancos (isCentered)
    assert '!(chatCentered() && !isCentered())' in c


def test_ventanas_nativas_sin_titulo_doble():
    w = _r('engine/oswindows.js')
    assert '.kd-body.kos-native .osw-hd>h3' in w and "mascot: 'analista'" in w and "mascot: 'cadena'" in w and "mascot: 'comite'" in w


def test_carteras_se_abren_dentro_del_os():
    r = _r('engine/resolve.js')
    assert re.search(r"\['tkg', 'guia', 'market', 'geo', 'space', 'simulation', 'portfolios'\]", r)


def test_arranque_sin_espera_fija_y_feed_una_vez():
    html = _r('app.html')
    assert 'setTimeout(tryLand, 60);' in html and 'setTimeout(tryLand, 850);' not in html
    assert "if(force && this._lang===lang && Date.now()-this._t<5000) return;" in html
