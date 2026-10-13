"""tests/test_csp_estricta.py — G5-09 (lote I1): la Content-Security-Policy de server.py sin 'unsafe-eval' y con
connect-src cerrado a los hosts que el navegador llama de verdad.

  1. Nada del cliente evalúa texto como código (eval, new Function, setTimeout/setInterval con texto, javascript: en
     atributos generados). Si alguien lo agrega, esta prueba falla ANTES de que la CSP lo rompa en producción.
  2. connect-src no tiene comodines (`https:` / `wss:` sueltos) y SÍ tiene: el WebSocket de Finnhub que abre
     app.html, la voz de ElevenLabs (URL firmada wss://api…elevenlabs.io), y cada CDN que sw.js vuelve a pedir con
     fetch() (CDN_HOSTS: su CSP es la de /sw.js, esta misma).
  3. Todo host wss:// o https:// absoluto que el cliente usa con fetch/WebSocket está permitido (escaneo del código).
  4. La cabecera real: /, /sw.js y una ruta /api la llevan (o Report-Only con CSP_REPORT_ONLY).

La comprobación en Chromium (la app real a 1440 px, 0 violaciones) se corrió a mano en el lote I1; aquí va lo
estático, que es lo que se rompe al editar.
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('SECRET_KEY', 'test-secret-key')

CLIENT = ([os.path.join(ROOT, 'app.html')] + glob.glob(os.path.join(ROOT, 'engine', '*.js'))
          + glob.glob(os.path.join(ROOT, 'nodes', '*.js')) + glob.glob(os.path.join(ROOT, 'sim', '*.js'))
          + [os.path.join(ROOT, 'sw.js')])


def _csp():
    import server
    return server.CONTENT_SECURITY_POLICY


def _directive(csp, name):
    for part in csp.split(';'):
        bits = part.strip().split()
        if bits and bits[0] == name:
            return bits[1:]
    return None


def _src(path):
    with open(path, encoding='utf-8', errors='ignore') as fh:
        return fh.read()


def test_sin_unsafe_eval_y_el_cliente_no_evalua_texto():
    csp = _csp()
    assert "'unsafe-eval'" not in csp
    bad = re.compile(r"(?<![\w.$])eval\s*\(|new\s+Function\s*\(|(?<![\w.$])Function\s*\(\s*['\"`]"
                     r"|set(?:Timeout|Interval)\s*\(\s*['\"`]")
    hits = []
    for f in CLIENT:
        for n, line in enumerate(_src(f).splitlines(), 1):
            s = line.strip()
            if s.startswith('//') or s.startswith('*'):
                continue
            if bad.search(line):
                hits.append(f'{os.path.relpath(f, ROOT)}:{n}: {s[:120]}')
    assert not hits, 'código que la CSP sin unsafe-eval bloquearía:\n' + '\n'.join(hits)


def test_connect_src_cerrado_a_hosts_reales():
    cs = _directive(_csp(), 'connect-src')
    assert cs, 'falta connect-src'
    assert 'https:' not in cs and 'wss:' not in cs and '*' not in cs, cs
    assert "'self'" in cs
    for host in ('wss://ws.finnhub.io', 'wss://*.elevenlabs.io'):
        assert host in cs, host
    sw = _src(os.path.join(ROOT, 'sw.js'))
    cdn = re.search(r'const CDN_HOSTS = \[([^\]]*)\]', sw).group(1)
    for h in re.findall(r"'([^']+)'", cdn):
        assert f'https://{h}' in cs, f'el service worker pide {h} con fetch(): falta en connect-src'


def _host_allowed(url, allowed):
    m = re.match(r'(wss?|https?)://([^/:?#]+)', url)
    if not m:
        return True
    scheme, host = m.group(1), m.group(2)
    for a in allowed:
        am = re.match(r'(wss?|https?)://(\*\.)?([^/]+)$', a)
        if not am or am.group(1) != scheme:
            continue
        if host == am.group(3) or (am.group(2) and host.endswith('.' + am.group(3))):
            return True
    return False


def test_todo_host_absoluto_que_el_cliente_conecta_esta_permitido():
    cs = _directive(_csp(), 'connect-src')
    rx = re.compile(r"(?:new\s+WebSocket|fetch|EventSource)\s*\(\s*['\"`]((?:wss?|https?)://[^'\"`$]+)")
    found = []
    for f in CLIENT:
        for m in rx.finditer(_src(f)):
            found.append((os.path.relpath(f, ROOT), m.group(1)))
    assert any('ws.finnhub.io' in u for _f, u in found), 'el escaneo ya no ve el WebSocket de Finnhub'
    bad = [(f, u) for f, u in found if not _host_allowed(u, cs)]
    assert not bad, f'el navegador se conecta a hosts que connect-src bloquearía: {bad}'
    # la voz: el host lo pone ElevenLabs en la URL firmada → debe ser *.elevenlabs.io
    from core import voice_agent
    assert re.match(r'https://api\.elevenlabs\.io', voice_agent.EL_API)


def test_la_cabecera_sale_en_la_app_el_sw_y_la_api(monkeypatch):
    import server
    c = server.app.test_client()
    for path in ('/', '/sw.js', '/api/vocabulary'):
        r = c.get(path)
        h = r.headers.get('Content-Security-Policy') or r.headers.get('Content-Security-Policy-Report-Only')
        assert h and "'unsafe-eval'" not in h and 'connect-src ' + server.CSP_CONNECT_SRC in h, path
