"""tests/test_ticket_mode.py — MODO TICKET del panel de trading (engine/ticket.js, 2026-10-30).

Regla de oro: el modo ticket NO envía nada a ningún bróker. Estas pruebas fijan eso (estático) y comprueban en un
Chromium real que el modo 'broker' sigue llamando a la función original, que el modo 'ticket' no la llama y que
«Ya lo ejecuté» anota la posición en la cartera con costo promedio ponderado."""
import os
import re
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS = os.path.join(ROOT, 'engine', 'ticket.js')


def _read(p):
    with open(os.path.join(ROOT, p), encoding='utf-8') as fh:
        return fh.read()


def test_ticket_never_talks_to_a_broker():
    src = _read('engine/ticket.js')
    code = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
    for bad in ('_tradeFetch', '/api/trade', '/api/brokerage', 'alpaca', 'fetch(', 'XMLHttpRequest', 'sendBeacon'):
        assert bad not in code, bad


def test_loaded_after_trade_panel_and_cached_offline():
    html, sw = _read('app.html'), _read('sw.js')
    a, b = html.index('<script src="engine/app_trade_panel.js"></script>'), html.index('<script src="engine/ticket.js"></script>')
    assert a < b
    assert "'/engine/ticket.js'" in sw[sw.index('const SHELL'):sw.index('];', sw.index('const SHELL'))]


def test_bilingual_strings_match():
    src = _read('engine/ticket.js')
    es = src[src.index("es: {"):src.index("en: {")]
    en = src[src.index("en: {"):src.index("function lang()")]
    keys = lambda s: set(re.findall(r"\b([A-Za-z_]+):\s*'", s))
    assert keys(es) == keys(en)


@pytest.mark.skipif(not shutil.which('node'), reason='sin node')
def test_browser_flow(tmp_path):
    script = os.path.join(ROOT, 'tests', '_ticket_browser.js')
    r = subprocess.run(['node', script], cwd=ROOT, capture_output=True, text=True, timeout=120)
    if r.returncode == 77:
        pytest.skip('sin Chromium/playwright')
    assert r.returncode == 0, r.stdout + r.stderr
