"""tests/test_genui_f3_browser.py — RESPUESTAS VISUALES PROGRESIVAS (kblocks/1, fase F3, pasos 23-24) en Chromium REAL
(docs/CHAT_UI_GENERATIVA.md §6, §7.4, §8, §10.1).

El guion es REAL de punta a punta: el servidor (run_chat con una IA de guion, herramientas offline) produce los estados
del progreso (bloques provisionales con su seq) y la respuesta final; el navegador los recibe por el camino de siempre
(KhipuChat.send → sondeo GET …/progress?since= → fillReply), con un fetch de guion que los entrega a sus tiempos.
  · el primer bloque se ve ANTES que el texto (y el esqueleto del principal también);
  · CLS == 0 medido con PerformanceObserver('layout-shift') desde la pregunta hasta que todo se asienta (1440 oscuro
    ES y 390 claro EN);
  · el sobre final manda: mismos ids en el orden final, el MISMO elemento del bloque que ya estaba (sin repintar),
    lo listo que no usa pasa a «Más datos de esta respuesta», la fila de pasos se pliega, el texto se revela entero;
  · desplazamiento inteligente: si el usuario subió a leer, nada lo arrastra; si seguía el final, lo sigue;
  · reducir movimiento: nada se anima y todo se ve de golpe; el esqueleto reserva la altura de height().
Se salta sin Playwright/Chromium. Capturas opcionales en $KH_SHOTS.
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tests.test_genui_browser import _chromium, _open  # noqa: E402

TIMES = (300, 1000, 1700, 2400, 2600)      # cuándo cada estado del servidor queda a la vista del sondeo (ms)
FINAL_AT = 3300                            # cuándo llega la respuesta final (ms)

TEXT = {
    'es': ('**TSMC** fabrica los chips más avanzados del mundo [F1].\n\nSi cayera, el golpe recorre la cadena: primero sus '
           'clientes directos y luego los clientes de ellos [F2]. Abajo ves cuántas empresas toca cada salto.'),
    'en': ('**TSMC** makes the most advanced chips in the world [F1].\n\nIf it failed, the hit travels down the chain: '
           'first its direct customers, then their customers [F2]. Below you can see how many companies each hop reaches.'),
}


def _scenario(monkeypatch, lang='es', mode='pro', question=None, script=None):
    """Guion REAL del servidor: estados del progreso tras cada publicación + la respuesta final."""
    from core import ai as core_ai
    from core import khipu_chat as kc
    from mcp_server import tools as mt
    monkeypatch.setenv('GENUI', 'on')
    monkeypatch.setattr(mt, '_live_profile', lambda sym: {'available': False, 'reason': 'test (offline)'})
    monkeypatch.setattr(mt._auth, 'db_available', lambda: False)
    monkeypatch.setattr(core_ai, '_ai_configured', lambda: True)
    script = list(script or [{'tool': 'run_scenario', 'args': {'shocks': [{'id': 'TSMC'}]}},
                             {'final': {'answer': TEXT[lang], 'actions': [{'type': 'open_xray', 'arg': 'TSMC'}]}}])
    monkeypatch.setattr(core_ai, '_ai_complete',
                        lambda *a, **k: (json.dumps(script.pop(0) if script else {'final': {'answer': 'ok'}}), 'fake:model'))
    states = []
    real = kc.progress_ui

    def spy(req_id, blocks, as_of=None):
        n = real(req_id, blocks, as_of)
        states.append(kc.progress_get(req_id))
        return n
    monkeypatch.setattr(kc, 'progress_ui', spy)
    rid = 'f3b-%s-%s-%d' % (lang, mode, len(question or ''))
    q = question or ('¿Qué pasa si cae TSMC?' if lang == 'es' else 'What happens if TSMC fails?')
    out = kc.run_chat(q, [], lang, {'genui': 1, 'mode': mode}, req_id=rid)
    states.append(kc.progress_get(rid))
    assert out['ui'] and any(s.get('ui') for s in states)
    return {'question': q, 'final': json.loads(json.dumps(out, default=str)), 'finalAt': FINAL_AT,
            'states': [{'t': TIMES[min(i, len(TIMES) - 1)], 'p': s} for i, s in enumerate(states)]}


# fetch de guion: el sondeo filtra por ?since= como el servidor; la respuesta final llega a los FINAL_AT ms
MOCK = r"""
(function () {
  var S = window.__SCN, real = window.fetch, t0 = null;
  var R = function (o) { return new Response(JSON.stringify(o), { status: 200, headers: { 'content-type': 'application/json' } }); };
  window.__t = function () { return t0 == null ? -1 : Date.now() - t0; };
  window.__since = [];
  window.fetch = function (url, opts) {
    url = String(url);
    if (url.indexOf('/api/khipu/chat/progress/') >= 0) {
      var now = window.__t(), m = /since=(\d+)/.exec(url), since = m ? +m[1] : 0, st = null;
      window.__since.push(m ? since : null);
      S.states.forEach(function (s) { if (s.t <= now) st = s.p; });
      st = JSON.parse(JSON.stringify(st || { req_id: 'x', done: false, elapsed_ms: 0, phase: 'start', agents: [], seq: 0 }));
      st.done = false;
      if (st.ui) { st.ui.blocks = st.ui.blocks.filter(function (b) { return b.seq > since; }); if (!st.ui.blocks.length) delete st.ui; }
      return Promise.resolve(R(st));
    }
    if (url.indexOf('/api/khipu/chat') >= 0) {
      t0 = Date.now();
      return new Promise(function (res) { setTimeout(function () { res(R(S.final)); }, S.finalAt); });
    }
    return real.apply(this, arguments);
  };
})();
"""

ASK = r"""(q) => {
  window.__cls = 0; window.__shifts = [];
  new PerformanceObserver(l => { for (const e of l.getEntries()) if (!e.hadRecentInput) { window.__cls += e.value;
    window.__shifts.push({ v: e.value, t: window.__t(), src: (e.sources || []).map(s => s.node && (s.node.className || s.node.nodeName)) }); } })
    .observe({ type: 'layout-shift' });
  const C = window.BixbyCockpit; if (!C.isOpen || !C.isOpen()) C.open();
  const th = document.getElementById('bcp-thread'), K = window.KhipuChat;
  K.appendUser(th, q);
  const pend = K.appendPending(th, { text: q });
  window.__pend = pend; window.__marks = {}; window.__sk = null;
  const tick = () => {
    const t = window.__t(), M = window.__marks;
    if (M.block == null && pend.querySelector('.kc-prov [data-kg-id]:not([aria-busy])')) M.block = t;
    const sk = pend.querySelector('.kc-prov [aria-busy=true]');
    if (sk && !window.__sk) { window.__sk = sk; M.skel = t; M.skMin = sk.style.minHeight;
      M.skTop = sk.closest('.kc-pb').offsetTop - pend.querySelector('.kc-prov').offsetTop;   // posición de diseño (sin transform)
      M.skWidth = pend.querySelector('.kc-prov').clientWidth; }
    if (!window.__card) window.__card = pend.querySelector('.kc-prov [data-kg-type="company.card"]');
    if (M.text == null && pend.querySelector('.kg-root > [data-kg-type=text]')) M.text = t;
    if (M.text != null && M.revealed == null) M.revealed = pend.querySelectorAll('.kc-w').length;
    if (t < 5200) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
  K.send(q, { pending: pend }).then(d => K.fillReply(pend, d, { autoRun: false }));
  return true;
}"""

STATE = r"""() => {
  const pend = window.__pend, root = pend.querySelector('.kc-body > .kg-root');
  return { cls: window.__cls, shifts: window.__shifts, marks: window.__marks, since: window.__since, csp: window.__csp.slice(),
    ids: root ? [...root.children].map(e => e.getAttribute('data-kg-id')) : null,
    cardKept: !!(window.__card && root && root.querySelector('[data-kg-type="company.card"]') === window.__card),
    cardChip: ((root && root.querySelector('[data-kg-type="company.card"] .kg-src[data-kg-fact]')) || {}).textContent || '',
    more: (pend.querySelector('.kc-more > summary') || {}).textContent || '', moreBlocks: pend.querySelectorAll('.kc-more [data-kg-id]').length,
    steps: (pend.querySelector('.kc-think .kc-tt') || {}).textContent || '', pending: pend.classList.contains('kc-pending'),
    busy: pend.getAttribute('aria-busy'), xf: pend.querySelectorAll('.kc-xf').length, hidden: pend.querySelectorAll('.kc-w').length,
    prov: pend.querySelectorAll('.kc-prov').length, status: (document.getElementById('kg-status') || {}).textContent || '',
    // lo PROPIO de F3 (FLIP y fundidos por script, entrada kcBk) ya terminó; y nada en bucle dentro de los bloques
    // (el parpadeo de las mascotas es de mascot.js, fuera de los bloques)
    anims: document.getAnimations().filter(a => a.playState === 'running' && a.effect && a.effect.target && a.effect.target.closest &&
      a.effect.target.closest('.kc-bot') && (a.constructor.name === 'Animation' || a.animationName === 'kcBk')).length,
    loops: document.getAnimations().filter(a => a.effect && a.effect.target && a.effect.target.closest &&
      a.effect.target.closest('.kc-body, .kc-more') && a.effect.getComputedTiming().iterations === Infinity).length };
}"""


@pytest.fixture(scope='module')
def pw():
    sync = pytest.importorskip('playwright.sync_api')
    with sync.sync_playwright() as p:
        b = _chromium(p)
        if not b:
            pytest.skip('Chromium no disponible')
        yield b
        b.close()


def _page(pw, scn, lang, theme, width, height, reduced=False, pre=''):
    extra = 'window.__SCN=%s;%s%s' % (json.dumps(scn, ensure_ascii=False), MOCK, pre)
    return _open(pw, lang, theme, width, height=height, reduced=reduced, extra=extra)


@pytest.mark.parametrize('lang,theme,width,height', [('es', 'dark', 1440, 900), ('en', 'light', 390, 844)])
def test_primer_bloque_antes_que_el_texto_cls_cero_y_el_final_manda(pw, monkeypatch, lang, theme, width, height):
    scn = _scenario(monkeypatch, lang)
    final_ids = [b['id'] for b in scn['final']['ui']['blocks']]
    ctx, pg, errs = _page(pw, scn, lang, theme, width, height)
    shots = os.environ.get('KH_SHOTS')
    try:
        pg.evaluate(ASK, scn['question'])
        if shots:
            pg.wait_for_timeout(2000)
            pg.screenshot(path=os.path.join(shots, 'genui_f3_%s_%s_%d_mid.png' % (lang, theme, width)))
        pg.wait_for_function('() => window.__marks && window.__marks.text != null', timeout=9000)
        pg.wait_for_timeout(1600)                                        # FLIP, revelado y entradas terminan
        s = pg.evaluate(STATE)
        if shots:
            pg.screenshot(path=os.path.join(shots, 'genui_f3_%s_%s_%d_end.png' % (lang, theme, width)))
        m = s['marks']
        # 1) el esqueleto del principal y luego su bloque se ven ANTES que el texto; la ficha pre-consultada no se
        #    adelanta a la cascada (revisión F3: el sobre final la plegaba y la cascada saltaba arriba)
        assert m['block'] is not None and m['skel'] is not None and m['skel'] < m['block'] < m['text'], m
        assert m['text'] >= FINAL_AT and m['block'] < 1900, m
        # 2) cero saltos de diseño
        assert s['cls'] == 0, s['shifts']
        # 3) el sobre final manda: sus ids en su orden, el MISMO elemento de la ficha, lo no usado plegado
        assert s['ids'] == final_ids, (s['ids'], final_ids)
        assert s['cardKept'], 'la ficha provisional se repintó'
        # …y aun así su chip [F#] dice lo mismo que diría recién pintada (nombre de la fuente del sobre final)
        srcs = {it['id']: it for b in scn['final']['ui']['blocks'] if b['type'] == 'sources' for it in b['data']['items'] if it.get('id')}
        card = next(b for b in scn['final']['ui']['blocks'] if b['type'] == 'company.card')
        assert s['cardChip'].startswith(card['sources'][0] + srcs[card['sources'][0]]['label']), s['cardChip']
        assert s['more'] == '' and s['moreBlocks'] == 0           # todo lo que se vio antes está en el sobre final
        assert s['steps'].startswith('✓ 2 pasos · ' if lang == 'es' else '✓ 2 steps · '), s['steps']
        assert not s['pending'] and s['busy'] is None and s['prov'] == 0
        assert s['xf'] == 0 and s['hidden'] == 0 and s['anims'] == 0 and s['loops'] == 0, s   # nada a medias ni en bucle
        assert m['revealed'] > 0                                               # el texto SE REVELÓ (palabras ocultas al llegar)
        assert s['status'].startswith('Respuesta lista' if lang == 'es' else 'Answer ready')
        # el sondeo pidió solo lo nuevo
        assert s['since'][0] == 0 and max(s['since']) > 0 and s['since'] == sorted(s['since'])
        assert not s['csp'], s['csp']
        assert not errs, errs
    finally:
        ctx.close()


SCROLL = r"""() => { const p = window.__pend; let s = p; while (s && s.parentElement) { s = s.parentElement;
  const cs = getComputedStyle(s); if (s.scrollHeight > s.clientHeight + 4 && /(auto|scroll)/.test(cs.overflowY)) return s; } return null; }"""


def test_desplazamiento_inteligente_no_arrastra_al_que_subio(pw, monkeypatch):
    scn = _scenario(monkeypatch, 'es')
    fill = ("window.__fill=function(){const th=document.getElementById('bcp-thread'),K=window.KhipuChat;"
            "for(let i=0;i<10;i++){K.appendUser(th,'pregunta '+i);const p=K.appendPending(th,{text:'x'});"
            "K.fillReply(p,{answer:'Respuesta larga '+i+'.\\n\\n'+'Texto de relleno para que el hilo se desplace. '.repeat(8)},{autoRun:false});}};")
    ctx, pg, errs = _page(pw, scn, 'es', 'dark', 1440, 900, pre=fill)
    try:
        pg.evaluate("() => { const C = window.BixbyCockpit; if (!C.isOpen()) C.open(); window.__fill(); }")
        pg.evaluate(ASK, scn['question'])
        pg.wait_for_timeout(150)
        # el usuario sube a leer algo viejo
        pg.evaluate("(sel) => { const s = (" + SCROLL + ")(); window.__sc = s; s.scrollTop = 120; }", None)
        seen = []
        for _ in range(9):
            pg.wait_for_timeout(500)
            seen.append(pg.evaluate('() => window.__sc.scrollTop'))
        assert pg.evaluate("() => window.__marks.text != null")
        assert set(seen) == {120}, seen                                       # ni los bloques ni la respuesta lo arrastran
        assert not errs, errs
    finally:
        ctx.close()
    # control: quien sigue el final del hilo SÍ es llevado (hasta el borde superior de la respuesta si es alta)
    ctx, pg, errs = _page(pw, scn, 'es', 'dark', 1440, 900, pre=fill)
    try:
        pg.evaluate("() => { const C = window.BixbyCockpit; if (!C.isOpen()) C.open(); window.__fill(); }")
        pg.evaluate(ASK, scn['question'])
        pg.wait_for_timeout(150)
        top0 = pg.evaluate("() => { window.__sc = (" + SCROLL + ")(); return window.__sc.scrollTop; }")
        pg.wait_for_function('() => window.__marks && window.__marks.text != null', timeout=9000)
        pg.wait_for_timeout(1200)
        out = pg.evaluate("""() => { const s = window.__sc, r = window.__pend.getBoundingClientRect(), sr = s.getBoundingClientRect();
            return { top: s.scrollTop, replyTop: r.top - sr.top, h: s.clientHeight }; }""")
        assert out['top'] > top0, (out, top0)
        assert -12 <= out['replyTop'] <= 0.3 * out['h'], out                # se paró en el borde superior de la respuesta
        assert not errs, errs
    finally:
        ctx.close()


def test_reducir_movimiento_todo_de_golpe_y_altura_reservada(pw, monkeypatch):
    scn = _scenario(monkeypatch, 'es')
    ctx, pg, errs = _page(pw, scn, 'es', 'dark', 1440, 900, reduced=True)
    try:
        pg.evaluate(ASK, scn['question'])
        checks = []
        for _ in range(10):
            pg.wait_for_timeout(450)
            # nada se anima en los bloques ni por script en la burbuja (el parpadeo de la mascota es de mascot.js)
            checks.append(pg.evaluate("""() => ({ anims: document.getAnimations().filter(a => a.effect && a.effect.target && a.effect.target.closest &&
                (a.effect.target.closest('.kc-body, .kc-prov, .kc-more') || (a.effect.target.closest('.kc-bot') && a.constructor.name === 'Animation'))).length,
                hidden: [...document.querySelectorAll('.kc-bot .kc-pb, .kc-bot .kg-b, .kc-bot .kg-bare')].filter(e => getComputedStyle(e).opacity !== '1').length,
                words: document.querySelectorAll('.kc-w').length })"""))
        assert all(c['anims'] == 0 and c['hidden'] == 0 and c['words'] == 0 for c in checks), checks
        s = pg.evaluate(STATE)
        m = s['marks']
        assert m['skel'] < m['block'] < m['text'] and s['ids'] == [b['id'] for b in scn['final']['ui']['blocks']]
        # el esqueleto reservó la altura del renderizador (height()) con un contenido típico
        want = pg.evaluate("""(w) => window.KhipuGenUI._u.height({ type: 'impact.cascade', state: 'ready',
            data: window.KhipuChat._f3.typical['impact.cascade'] }, w) + 'px'""", m['skWidth'])
        assert m['skMin'] == want, (m['skMin'], want)
        # sin movimiento no hay FLIP (por diseño, todo es instantáneo): los bloques no se mueven NADA; lo único que puede
        # saltar es una mascota de la fila de pasos dentro de su caja fija (≈ 1e-5, invisible para la métrica real)
        assert s['cls'] < 1e-4 and all(set(x['src']) <= {'kc-tmi', 'kc-tmi kc-done', 'kc-tmi kc-fail'} for x in s['shifts']), s['shifts']
        assert not errs, errs
    finally:
        ctx.close()


def test_esqueleto_se_funde_en_su_sitio(pw, monkeypatch):
    scn = _scenario(monkeypatch, 'es')
    ctx, pg, errs = _page(pw, scn, 'es', 'dark', 1440, 1400)
    try:
        pg.evaluate(ASK, scn['question'])
        pg.wait_for_function('() => window.__marks && window.__marks.skel != null', timeout=6000)
        # el bloque listo ocupa el MISMO lugar que su esqueleto; el esqueleto se apaga encima y desaparece
        pg.wait_for_function("() => window.__pend.querySelector('.kc-prov [data-kg-type=\"impact.cascade\"]:not([aria-busy])')", timeout=6000)
        mid = pg.evaluate("""() => { const box = window.__pend.querySelector('.kc-prov'), c = box.querySelector('[data-kg-type="impact.cascade"]:not([aria-busy])');
            return { top: c.closest('.kc-pb').offsetTop - box.offsetTop, xf: window.__pend.querySelectorAll('.kc-xf').length }; }""")
        skTop = pg.evaluate('() => window.__marks.skTop')
        assert abs(mid['top'] - skTop) <= 1, (mid, skTop)
        # el esqueleto reservó (casi) la altura del bloque listo: |listo − reservado| ≤ 10 % (antes ~55 %)
        hh = pg.evaluate("""() => { const c = window.__pend.querySelector('.kc-prov [data-kg-type="impact.cascade"]:not([aria-busy])');
            return { ready: c.getBoundingClientRect().height, reserved: parseFloat(window.__marks.skMin) }; }""")
        assert abs(hh['ready'] - hh['reserved']) <= 0.10 * hh['reserved'], hh
        pg.wait_for_timeout(700)
        assert pg.evaluate("() => window.__pend.querySelectorAll('.kc-xf').length") == 0
        assert not errs, errs
    finally:
        ctx.close()


def test_varias_fichas_se_agrupan_sin_duplicarse_en_mas_datos(pw, monkeypatch):
    """«Compara Nvidia y AMD»: las dos fichas provisionales pasan a UNA fila en el sobre final; nada se repite plegado
    y la comparación (el mismo elemento) se desliza a su lugar."""
    scn = _scenario(monkeypatch, 'es', question='Compara Nvidia y AMD',
                    script=[{'final': {'answer': 'Nvidia y AMD compiten en GPUs [F1] [F2].', 'actions': []}}])
    ctx, pg, errs = _page(pw, scn, 'es', 'light', 1440, 900)
    try:
        pg.evaluate(ASK, scn['question'])
        pg.evaluate("() => { const t = () => { const c = window.__pend.querySelector('.kc-prov [data-kg-type=comparison]'); if (c) window.__cmp = c; else requestAnimationFrame(t); }; requestAnimationFrame(t); }")
        # opacidad mínima de las fichas a la vista, fotograma a fotograma (antes la fila nueva parpadeaba 1 → 0 → 1)
        pg.evaluate("""() => { window.__minOp = 1; const t = () => { document.querySelectorAll('.kc-bot [data-kg-type="company.card"]').forEach(e => {
            let o = 1; for (let x = e; x && x !== document.body; x = x.parentElement) o *= parseFloat(getComputedStyle(x).opacity);
            if (window.__marks && window.__marks.text != null) window.__minOp = Math.min(window.__minOp, o); });
            if (window.__t() < 5200) requestAnimationFrame(t); }; requestAnimationFrame(t); }""")
        pg.wait_for_function('() => window.__marks && window.__marks.text != null', timeout=9000)
        pg.wait_for_timeout(1200)
        assert pg.evaluate('() => window.__minOp') >= 0.99, 'una ficha que ya se veía se apagó al aterrizar'
        s = pg.evaluate(STATE)
        out = pg.evaluate("""() => { const root = window.__pend.querySelector('.kc-body > .kg-root');
            return { kept: root.querySelector('[data-kg-type=comparison]') === window.__cmp, rows: root.querySelectorAll('.kg-t-cards').length,
                     cards: root.querySelectorAll('.kg-t-cards .kg-cc').length, more: window.__pend.querySelectorAll('.kc-more').length }; }""")
        assert out == {'kept': True, 'rows': 1, 'cards': 2, 'more': 0}, out
        assert s['cls'] == 0, s['shifts']
        assert s['marks']['block'] < s['marks']['text']
        assert not errs, errs
    finally:
        ctx.close()


def test_lo_que_el_final_no_usa_va_a_mas_datos(pw, monkeypatch):
    """La IA pide la ficha en la 1.ª ronda y el choque en la 2.ª: lo de la ficha se mostró al cerrar la ronda y el sobre
    final (modo simple: solo la cascada) no lo usa → «Más datos de esta respuesta», nunca desaparece."""
    scn = _scenario(monkeypatch, 'es', mode='simple', script=[
        {'tool': 'get_company', 'args': {'id_or_ticker': 'TSMC'}},
        {'tool': 'run_scenario', 'args': {'shocks': [{'id': 'TSMC'}]}},
        {'final': {'answer': TEXT['es'], 'actions': []}}])
    ctx, pg, errs = _page(pw, scn, 'es', 'dark', 1440, 900)
    try:
        pg.evaluate(ASK, scn['question'])
        pg.wait_for_function('() => window.__marks && window.__marks.text != null', timeout=9000)
        pg.wait_for_timeout(1200)
        s = pg.evaluate(STATE)
        assert s['more'].startswith('Más datos de esta respuesta (') and s['moreBlocks'] >= 1, s
        assert s['ids'] == [b['id'] for b in scn['final']['ui']['blocks']]
        assert not errs, errs
    finally:
        ctx.close()


def test_acciones_de_bloques_reusados_van_al_onaction_de_la_cabina(pw, monkeypatch):
    """Los bloques provisionales que el sobre final reusa (y los de «Más datos») mandan sus acciones al onAction de quien
    pintó la respuesta (la Cabina pone la ventana AL LADO del chat), no al camino por defecto."""
    scn = _scenario(monkeypatch, 'es')
    ask = ASK.replace("K.send(q, { pending: pend }).then(d => K.fillReply(pend, d, { autoRun: false }));",
                      "window.__acts = []; K.send(q, { pending: pend }).then(d => K.fillReply(pend, d, { autoRun: false, "
                      "onAction: a => { window.__acts.push(a.type + ':' + a.arg); return true; } }));")
    assert ask != ASK
    ctx, pg, errs = _page(pw, scn, 'es', 'dark', 1440, 900)
    try:
        pg.evaluate(ask, scn['question'])
        pg.wait_for_function('() => window.__marks && window.__marks.text != null', timeout=9000)
        pg.wait_for_timeout(900)
        out = pg.evaluate("""() => { const root = window.__pend.querySelector('.kc-body > .kg-root');
            const card = root.querySelector('[data-kg-type="company.card"]');
            const btns = [...card.querySelectorAll('button')].filter(b => !b.closest('.kg-src') && b.offsetParent && /Dossier|X-Ray|Radiograf/i.test(b.textContent));
            btns.forEach(b => b.click());
            return { kept: card === window.__card, n: btns.length, acts: window.__acts.slice() }; }""")
        assert out['kept'] and out['n'] >= 1, out
        assert len(out['acts']) == out['n'] and all(a.endswith(':TSMC') for a in out['acts']), out
        assert not errs, errs
    finally:
        ctx.close()


def test_un_error_despues_de_los_bloques_no_los_borra(pw, monkeypatch):
    """Plazo del cliente / 5xx / red DESPUÉS de mostrar bloques listos: el aviso reemplaza la fila de pasos y los bloques
    siguen a la vista (antes fillError vaciaba la burbuja entera)."""
    scn = _scenario(monkeypatch, 'es')
    ctx, pg, errs = _page(pw, scn, 'es', 'dark', 1440, 900)
    try:
        pg.evaluate(ASK.replace("K.send(q, { pending: pend }).then(d => K.fillReply(pend, d, { autoRun: false }));",
                                "K.send(q, { pending: pend }).then(() => {});"), scn['question'])
        pg.wait_for_function("() => window.__pend.querySelector('.kc-prov [data-kg-type=\"impact.cascade\"]:not([aria-busy])')", timeout=6000)
        out = pg.evaluate("""() => { const p = window.__pend; window.KhipuChat.fillError(p, 'Khipu tardó demasiado');
            return { err: (p.querySelector('.kc-err') || {}).textContent || '', blocks: p.querySelectorAll('.kc-body [data-kg-id]:not([aria-busy])').length,
                     think: p.querySelectorAll('.kc-think').length, skel: p.querySelectorAll('[aria-busy=true]').length,
                     pending: p.classList.contains('kc-pending') }; }""")
        assert 'Khipu tardó demasiado' in out['err'] and out['blocks'] >= 1, out
        assert out['think'] == 0 and out['skel'] == 0 and not out['pending'], out
        assert not errs, errs
    finally:
        ctx.close()
