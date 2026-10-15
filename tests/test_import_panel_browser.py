"""tests/test_import_panel_browser.py — EXPANSION_5K E2.7: el panel 📥 Importar (engine/importer.js) en Chromium REAL.

Página mínima con el PRIMER bloque inline de app.html (window._tradeFetch y el PIN oculto), engine/toast.js,
engine/explain.js, los tokens --os-* de engine/cockpit.js y engine/importer.js servidos como archivos (mismo origen).
Las rutas /api/* responden con un plan REAL del paquete del lote 2 armado sobre el snapshot (hot.fallback(): sin base).
  · lista → «Ver plan» → cifras del plan (372 / 14 / 656…), ¿qué cambia?, sin desplazamiento horizontal a 390 px,
    0 errores de página, en claro y en oscuro; el «?» abre la explicación;
  · «Aplicar…»: confirmación (el botón espera la casilla de la copia de seguridad) → nombre de la base → PIN OCULTO
    (password) → POST con package + expect.plan_sha + confirm_db + X-Trade-Pin; si el servidor dice que la base se
    llama de otro modo (400 confirm_db) el panel lo ofrece y reintenta UNA vez; resultado con corrida y decisión;
  · 409 plan_changed → mensaje en palabras simples y el plan se vuelve a pedir; red caída → «puede que SÍ se haya
    hecho: mira Corridas»; «Deshacer» con PIN; nombres con HTML se pintan como TEXTO; ES/EN.
Capturas opcionales en $KH_SHOTS (escritorio oscuro y teléfono claro). Se salta sin Playwright/Chromium.
"""
import json
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('KHIPU_SCHEDULER', 'off')
PKG = '2026-10-15/bundle_lote2_completas.json.gz'
SCRIPTS = ['engine/toast.js', 'engine/explain.js', 'engine/agents_registry.js', 'engine/mascot.js', 'engine/desktop.js',
           'engine/cockpit.js', 'engine/importer.js']


def _r(*p):
    with open(os.path.join(ROOT, *p), encoding='utf-8') as f:
        return f.read()


def _first_inline_block():
    html = _r('app.html')
    return re.search(r'<script>(.*?)</script>', html, re.S).group(1)


PAGE = ('<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,'
        'initial-scale=1"><style>html,body{margin:0;font-family:system-ui}body{background:#EDEDF5}'
        'body.dark{background:#0E0F14}#sistema-panel{max-width:560px;margin:0 auto;padding:12px 16px;box-sizing:border-box}'
        '</style><script>' + _first_inline_block().replace('</script', '<\\/script') + '</script></head><body>'
        '<aside id="sistema-panel" class="kos-themed"><div id="sistema-diag"><div id="prices-box"></div></div></aside>'
        + ''.join('<script src="/%s"></script>' % s for s in SCRIPTS) + '</body></html>')


def _chromium(p):
    for kw in ({}, {'executable_path': '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', 'args': ['--no-sandbox']}):
        try:
            return p.chromium.launch(**kw)
        except Exception:  # noqa: BLE001
            continue
    return None


@pytest.fixture(scope='module')
def fx():
    """Lista + plan del panel con los MISMOS armadores del servidor (ontology/api.py) sobre el snapshot."""
    from core.hotviews import hot
    from ontology import api as A
    from ontology import company_import as CI
    b, sha, meta = A._import_package(PKG)
    p = CI.plan(b['records'], b['updates'], view=hot.fallback(), batch=b['batch'])
    plan = A._import_panel_summary(p)
    run = {'id': '11111111-2222-3333-4444-555555555555', 'run_id': '20261015T120000Z-abc123', 'kind': 'apply',
           'batch': b['batch'], 'status': 'applied', 'file_sha': sha, 'decision_id': 'dec-apply-1', 'created_at':
           '2026-10-15T12:00:00+00:00', 'rolled_back_run': None, 'summary': {'counts': p['counts']}}
    return {'packages': {'packages': [{**meta, 'runs': [], 'applied': False}], 'errors': []},
            'plan': {'status': 'ok', 'package': meta, 'file_sha': sha, 'plan': json.loads(json.dumps(plan, default=str))},
            'policy': CI.policy(), 'run': run, 'counts': p['counts']}


@pytest.fixture(scope='module')
def browser():
    sync = pytest.importorskip('playwright.sync_api')
    with sync.sync_playwright() as p:
        b = _chromium(p)
        if not b:
            pytest.skip('Chromium no disponible')
        yield b
        b.close()


class Server:
    """Las respuestas de /api/* (programables por prueba) + el registro de lo que pidió el navegador."""
    def __init__(self, fx):
        self.fx, self.log, self.apply, self.rollback = fx, [], [], []
        self.runs = []
        self.chunks = {}
        self.pkgs = json.loads(json.dumps(fx['packages']))

    def handler(self, route):
        req = route.request
        path = req.url.split('khipu.test', 1)[1].split('?')[0]
        j = lambda body, status=200: route.fulfill(status=status, content_type='application/json', body=json.dumps(body))  # noqa: E731
        if path in ('', '/'):
            return route.fulfill(status=200, content_type='text/html', body=PAGE)
        if path.startswith('/engine/'):
            return route.fulfill(status=200, content_type='application/javascript', body=_r(*path.lstrip('/').split('/')))
        if not path.startswith('/api/'):
            return route.fulfill(status=404, body='')
        self.log.append({'method': req.method, 'path': path, 'url': req.url, 'body': req.post_data,
                         'pin': req.headers.get('x-trade-pin')})
        if path == '/api/ontology/import/packages':
            return j(self.pkgs)
        if path == '/api/ontology/import/packages/plan':
            return j(self.fx['plan'])
        if path == '/api/ontology/import/runs':
            return j({'runs': self.runs, 'pending_links': 2050, 'policy': self.fx['policy']})
        if path == '/api/trade/status':
            return j({'pin_set': True, 'paper': True})
        if path == '/api/ontology/import/files':
            d = json.loads(req.post_data)
            self.chunks.setdefault(d['sha256'], {})[d['chunk']] = d
            done = len(self.chunks[d['sha256']]) == d['chunks']
            return j({'status': 'stored' if done else 'partial', 'sha256': d['sha256'], 'name': d['name'],
                      'n_records': 2 if done else None, 'n_updates': 0, 'batch': None})
        if path == '/api/ontology/import/plan':
            return j({'status': 'ok', 'file_sha': json.loads(req.post_data).get('file_sha'), 'plan': self.fx['plan']['plan']})
        if path == '/api/ontology/import/apply' and self.apply:
            nxt = self.apply.pop(0)
            if nxt == 'abort':
                return route.abort()
            status, body = nxt
            if status == 200:
                self.runs = [self.fx['run']]
            return j(body, status)
        if path == '/api/ontology/import/rollback' and self.rollback:
            status, body = self.rollback.pop(0)
            if status == 200:
                self.runs = [self.fx['run'], {**self.fx['run'], 'id': 'rb-1', 'kind': 'rollback',
                                              'rolled_back_run': self.fx['run']['id']}]
            return j(body, status)
        return j({'error': 'sin servidor'}, 503)

    def posts(self, path):
        return [x for x in self.log if x['method'] == 'POST' and x['path'] == path]


def _page(browser, fx, *, dark=False, width=1440, height=900, lang='es'):
    c = browser.new_context(viewport={'width': width, 'height': height}, service_workers='block')
    c.add_init_script("try { localStorage.setItem('eco_lang', %r); localStorage.setItem('khipu_actor', 'Fabrizio'); } catch (e) {}"
                      % lang)
    srv = Server(fx)
    c.route('http://khipu.test/**', srv.handler)
    pg = c.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://khipu.test/')
    pg.evaluate("(d) => { document.body.classList.toggle('dark', d); window.LANG = %r; }" % lang, dark)
    pg.wait_for_function("() => !!window.KhipuImporter")
    pg.evaluate("() => window.KhipuImporter.mount('sistema-diag')")
    pg.wait_for_selector('#import-box .kim-pkg')
    return c, pg, srv, errs


def _open_plan(pg):
    pg.click('#import-box .kim-pkg .kim-pkg-hd .kim-btn')
    pg.wait_for_selector('#import-box .kim-tiles')


def _shot(pg, name):
    d = os.environ.get('KH_SHOTS')
    if d:
        os.makedirs(d, exist_ok=True)
        pg.screenshot(path=os.path.join(d, name + '.png'), full_page=True)


@pytest.mark.parametrize('dark,width', [(True, 1440), (False, 390)])
def test_lista_y_plan_se_ven_bien(browser, fx, dark, width):
    c, pg, srv, errs = _page(browser, fx, dark=dark, width=width, height=900 if width > 500 else 844)
    try:
        txt = pg.inner_text('#import-box')
        assert 'Lote 2 — 386 empresas completas' in txt and 'sin aplicar' in txt
        _open_plan(pg)
        cn = fx['counts']
        tiles = pg.eval_on_selector_all('#import-box .kim-tile .n', 'els => els.map(e => e.textContent)')
        fmt = lambda n: f'{n:,}'.replace(',', '.')  # noqa: E731
        assert tiles == [fmt(cn['create']), fmt(cn['merge']), fmt(cn['links']['live']), fmt(cn['links']['proposed']),
                         fmt(cn['links']['pending']), fmt(cn['categories_to_approve'])]
        txt = pg.inner_text('#import-box')
        assert 'Si TSMC falla, golpea a: 318 →' in txt and 'Fuerza de contagio (ρ): 1,2107 →' in txt
        assert 'Huella del plan:' in txt and fx['plan']['plan']['plan_sha'][:12] in txt
        assert '9 fichas de la entrega NO entran' in txt
        lay = pg.evaluate("""() => { const b = document.getElementById('import-box');
          return {sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth,
                  over: [...b.querySelectorAll('*')].filter(e => e.getBoundingClientRect().right > b.getBoundingClientRect().right + 1).length,
                  themed: b.classList.contains('kos-themed')}; }""")
        assert lay['sw'] <= lay['cw'] and lay['over'] == 0 and lay['themed'], lay
        # «?» → la explicación en palabras simples (engine/explain.js)
        pg.click('#import-box .kim-hd .kim-q')
        assert 'Importar empresas' in pg.inner_text('#xpl-t')
        assert not errs, errs
        assert srv.log[0]['pin'] is None and all(x['method'] == 'GET' for x in srv.log)   # ver el plan NO pide PIN
        _shot(pg, 'importar_%s_%d' % ('oscuro' if dark else 'claro', width))
    finally:
        c.close()


def _confirm_backup(pg):
    pg.wait_for_selector('#khm-ov .khm-ok')
    assert pg.is_disabled('#khm-ov .khm-ok')                     # la casilla de la copia de seguridad manda
    pg.check('#khm-ck')
    pg.click('#khm-ov .khm-ok')


def _answer_prompt(pg, value, password=False):
    sel = '#khm-in[type=%s]' % ('password' if password else 'text')
    pg.wait_for_selector(sel)
    pg.fill(sel, value)
    pg.click('#khm-ov .khm-ok')


def test_aplicar_con_pin_y_nombre_de_la_base(browser, fx):
    c, pg, srv, errs = _page(browser, fx)
    try:
        _open_plan(pg)
        msg = "--confirm-db debe ser exactamente el nombre de la base ('railway'); nada se ha cambiado"
        res = {'status': 'ok', 'run_id': fx['run']['run_id'], 'decision_id': 'dec-apply-1', 'objects_created': 3216,
               'objects_updated': 14, 'links_created': 656, 'events': 4380, 'elapsed_ms': 12034.5, 'plan_counts': fx['counts']}
        srv.apply = [(400, {'error': msg, 'error_en': msg, 'code': 'confirm_db'}), (200, res)]
        pg.click('#import-box [data-kim-f^="apply:"]')
        _confirm_backup(pg)
        _answer_prompt(pg, 'mi_base')                            # nombre equivocado
        _answer_prompt(pg, '4321', password=True)                # PIN oculto (window._tradeFetch → askPin)
        pg.wait_for_selector('#khm-in[type=text]')
        assert pg.input_value('#khm-in') == 'railway'            # tras el PIN, el servidor dijo el nombre: se ofrece
        pg.click('#khm-ov .khm-ok')
        pg.wait_for_selector('#import-box .kim-msg.ok')
        posts = srv.posts('/api/ontology/import/apply')
        assert len(posts) == 2 and all(p['pin'] == '4321' for p in posts)
        b1, b2 = (json.loads(p['body']) for p in posts)
        assert b1['package'] == PKG and b1['expect'] == {'plan_sha': fx['plan']['plan']['plan_sha']}
        assert b1['confirm_db'] == 'mi_base' and b2['confirm_db'] == 'railway' and b2['actor'] == 'Fabrizio'
        assert 'file_sha' not in b1 and 'sanitize' not in b1
        txt = pg.inner_text('#import-box')
        assert 'Importado.' in txt and fx['run']['run_id'] in txt and 'dec-apply-1' in txt
        assert '%d empresas nuevas' % fx['counts']['create'] in txt and '3216' not in txt.replace('.', '')
        pg.wait_for_selector('#import-box [data-kim-f="undo"]')  # la corrida nueva se puede deshacer
        assert pg.evaluate("() => localStorage.getItem('kh_import_db')") == 'railway'
        # deshacer con PIN (ya guardado 12 h) y el nombre recordado
        srv.rollback = [(200, {'status': 'ok', 'run_id': fx['run']['run_id'], 'decision_id': 'dec-rb-1', 'links_retracted': 656,
                               'objects_retired': 372, 'objects_restored': 14})]
        pg.click('#import-box [data-kim-f="undo"]')
        pg.wait_for_selector('#khm-ov .khm-ok')
        pg.click('#khm-ov .khm-ok')
        pg.wait_for_selector('#khm-in[type=text]')
        assert pg.input_value('#khm-in') == 'railway'
        pg.click('#khm-ov .khm-ok')
        pg.wait_for_selector('#import-box .kim-msg.ok >> text=Deshecho.')
        rb = srv.posts('/api/ontology/import/rollback')
        assert len(rb) == 1 and rb[0]['pin'] == '4321' and json.loads(rb[0]['body'])['run_id'] == fx['run']['run_id']
        assert 'dec-rb-1' in pg.inner_text('#import-box')
        assert not errs, errs
    finally:
        c.close()


def test_plan_cambiado_y_red_caida(browser, fx):
    c, pg, srv, errs = _page(browser, fx)
    try:
        pg.evaluate("() => { localStorage.setItem('kh_import_db', 'railway'); window._tradePinSave('4321'); }")
        _open_plan(pg)
        n_plan = len([x for x in srv.log if x['path'].endswith('/packages/plan')])
        srv.apply = [(409, {'error': 'el plan cambió', 'error_en': 'the plan changed', 'code': 'plan_changed'}), 'abort']
        pg.click('#import-box [data-kim-f^="apply:"]')
        _confirm_backup(pg)
        _answer_prompt(pg, 'railway')
        pg.wait_for_selector('#import-box .kim-msg.err')
        assert 'El plan cambió desde que lo miraste' in pg.inner_text('#import-box')
        pg.wait_for_selector('#import-box .kim-tiles')
        assert len([x for x in srv.log if x['path'].endswith('/packages/plan')]) == n_plan + 1   # se volvió a pedir
        n_runs = len([x for x in srv.log if x['path'].endswith('/import/runs')])
        pg.click('#import-box [data-kim-f^="apply:"]')
        _confirm_backup(pg)
        _answer_prompt(pg, 'railway')
        pg.wait_for_selector('#import-box .kim-msg.warn')
        assert 'Puede que SÍ se haya hecho' in pg.inner_text('#import-box')
        assert len([x for x in srv.log if x['path'].endswith('/import/runs')]) > n_runs    # se miran las corridas
        assert not errs, errs
    finally:
        c.close()


def test_texto_con_html_se_pinta_como_texto_y_en_ingles(browser, fx):
    evil = json.loads(json.dumps(fx))
    p0 = evil['packages']['packages'][0]
    p0['title_es'] = p0['title_en'] = '<img src=x onerror="window.__pwn=1">Lote'
    evil['plan']['plan']['merges'] = [{'record_id': 'r', 'name': '<b id="inj">X</b>', 'id': 'Y', 'method': 'lei', 'score': 99}]
    c, pg, srv, errs = _page(browser, evil, lang='en')
    try:
        _open_plan(pg)
        pg.click('#import-box details summary')                 # abre «Merged into one that already exists»
        assert pg.evaluate("() => !document.querySelector('#import-box img') && !document.getElementById('inj') && !window.__pwn")
        txt = pg.inner_text('#import-box')
        assert '<img src=x' in txt and 'Import companies' in txt and 'What enters' in txt and 'Live links' in txt
        assert 'If TSMC fails, it hits: 318 →' in txt and 'same LEI' in txt
        # cambiar el idioma (applyLang pone <html lang>) repinta el panel abierto
        pg.evaluate("() => { window.LANG = 'es'; document.documentElement.lang = 'es'; }")
        pg.wait_for_selector('#import-box .kim-hd >> text=Importar empresas')
        assert 'Si TSMC falla, golpea a: 318 →' in pg.inner_text('#import-box')
        assert not errs, errs
    finally:
        c.close()


@pytest.mark.parametrize('gz', [False, True])
def test_subir_un_archivo_propio(browser, fx, tmp_path, gz):
    import base64
    import gzip
    import hashlib
    import zlib
    raw = (json.dumps({'schema': 'khipus.company/1', 'record_id': 'x-1'}) + '\n' +
           json.dumps({'schema': 'khipus.company/1', 'record_id': 'x-2'}) + '\n').encode('utf-8')
    f = tmp_path / ('mis_fichas.jsonl' + ('.gz' if gz else ''))
    f.write_bytes(gzip.compress(raw) if gz else raw)
    c, pg, srv, errs = _page(browser, fx)
    try:
        pg.evaluate("() => { window._tradePinSave('4321'); }")
        pg.click('#import-box details:has(.kim-file) summary')
        pg.set_input_files('#import-box .kim-file', str(f))
        pg.wait_for_selector('#import-box [data-file] .kim-tiles')
        ups = srv.posts('/api/ontology/import/files')
        assert ups and all(u['pin'] == '4321' for u in ups)
        body = json.loads(ups[0]['body'])
        assert body['name'] == 'mis_fichas.jsonl' and body['sha256'] == hashlib.sha256(raw).hexdigest()
        data = base64.b64decode(body['data'])
        assert (zlib.decompress(data) if body['encoding'] == 'zlib' else data) == raw     # el contenido SIN comprimir
        pl = srv.posts('/api/ontology/import/plan')
        assert len(pl) == 1 and pl[0]['pin'] == '4321'
        assert json.loads(pl[0]['body']) == {'file_sha': body['sha256'], 'view': 'panel', 'sanitize': 1}
        assert 'Archivo mis_fichas.jsonl' in pg.inner_text('#import-box')
        # aplicar el archivo: file_sha + sanitize (la MISMA huella que el plan que se vio)
        srv.apply = [(200, {'status': 'ok', 'run_id': 'r-file', 'decision_id': 'd-file', 'links_created': 0, 'events': 3,
                            'elapsed_ms': 800, 'plan_counts': fx['counts']})]
        pg.evaluate("() => localStorage.setItem('kh_import_db', 'railway')")
        pg.click('#import-box [data-file] [data-kim-f^="apply:"]')
        _confirm_backup(pg)
        _answer_prompt(pg, 'railway')
        pg.wait_for_selector('#import-box .kim-msg.ok')
        ap = json.loads(srv.posts('/api/ontology/import/apply')[0]['body'])
        assert ap['file_sha'] == body['sha256'] and ap['sanitize'] == 1 and 'package' not in ap
        assert not errs, errs
    finally:
        c.close()
