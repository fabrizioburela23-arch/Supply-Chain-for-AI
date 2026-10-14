"""tests/test_genui_k_browser.py — RESPUESTAS VISUALES, lote K (2026-10-14), en Chromium REAL: los 3 problemas de pantalla
que Fabrizio vio con GENUI=on (misma página y mismos scripts que tests/test_genui_browser.py).

  2. tiles en una columna de 520 px: ningún texto desborda (scrollWidth ≤ clientWidth), 4 cifras van en 2×2, la
     capitalización grande se escribe corta («$5,52 T») y la etiqueta larga cabe en dos líneas;
  3. UNA cotización por empresa en pantalla: las cifras del chat (precio y cambio) y la ventana «en una mirada» leen
     el MISMO /api/hot/quote (un solo stub) y muestran el mismo número; el cambio positivo lleva «+»;
  4. acciones sin duplicar: Dossier y X-Ray aparecen UNA vez por empresa aunque la ficha, su pie y la fila final los
     traigan, con UN rótulo por idioma (nunca «Radiografía» y «X-Ray» a la vez); los chips del chat no los repiten.
Se salta sin Playwright/Chromium.
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tests.test_genui_browser import ASK, _chromium, _open  # noqa: E402

NOW = '2026-10-14T15:00:00Z'
OLD = '2026-10-14T08:00:00Z'


def _fig(v, unit, src='yahoo', as_of=OLD, **kw):
    f = {'v': v, 'unit': unit, 'src': src, 'as_of': as_of, 'fact': 'F1'}
    f.update(kw)
    return f


def _tiles(as_of=OLD):
    return {'id': 'b1', 'type': 'metric.tiles', 'state': 'ready', 'title': {'es': 'Nvidia: cifras clave', 'en': 'Nvidia: key figures'},
            'alt': {'es': 'cifras', 'en': 'figures'}, 'prov': {'kind': 'tool', 'name': 'get_company', 'call': 0, 'fact': 'F1'},
            'entity': {'id': 'Nvidia', 'label': 'Nvidia', 'symbol': 'NVDA'}, 'sources': ['F1'], 'menu': ['where_from', 'ask'],
            'data': {'items': [
                {'label': {'es': 'Precio', 'en': 'Price'}, 'value': _fig(228.52, 'USD', as_of=as_of, live=True)},
                {'label': {'es': 'Cambio', 'en': 'Change'}, 'value': _fig(1.0, 'pct', as_of=as_of, live=True)},
                {'label': {'es': 'Capitalización', 'en': 'Market cap'}, 'value': _fig(5518.6, 'USD_B', as_of=as_of)},
                {'label': {'es': 'Riesgo de red (NRS)', 'en': 'Network risk (NRS)'}, 'value': _fig(41, 'nrs', 'khipus_nrs', NOW, explain='nrs')}]}}


def _card():
    return {'id': 'b2', 'type': 'company.card', 'state': 'ready', 'title': {'es': 'Ficha de Nvidia', 'en': 'Nvidia card'},
            'alt': {'es': 'ficha', 'en': 'card'}, 'prov': {'kind': 'tool', 'name': 'get_company', 'call': 0, 'fact': 'F1'},
            'entity': {'id': 'Nvidia', 'label': 'Nvidia', 'symbol': 'NVDA'}, 'sources': ['F1'],
            'actions': [{'kind': 'open_dossier', 'label': {'es': 'Dossier', 'en': 'Dossier'}, 'entity': {'id': 'Nvidia', 'label': 'Nvidia', 'symbol': 'NVDA'}},
                        {'kind': 'open_xray', 'label': {'es': 'Radiografía', 'en': 'X-Ray'}, 'entity': {'id': 'Nvidia', 'label': 'Nvidia', 'symbol': 'NVDA'}}],
            'data': {'company': {'id': 'Nvidia', 'label': 'Nvidia', 'symbol': 'NVDA'}, 'listed': True,
                     'price': _fig(228.52, 'USD', live=True), 'change': _fig(1.0, 'pct', live=True),
                     'market_cap': _fig(5518.6, 'USD_B'), 'nrs': _fig(41, 'nrs', 'khipus_nrs', NOW)}}


def _env(blocks, lang='es', actions=None):
    bl = [{'id': 't1', 'type': 'text', 'state': 'ready', 'data': {'md': 'Texto de prueba.', 'lang': lang}}] + list(blocks)
    if actions:
        bl.append({'id': 'act', 'type': 'actions', 'state': 'ready', 'data': {'items': actions}})
    bl.append({'id': 'src', 'type': 'sources', 'state': 'ready', 'data': {'items': [{'id': 'F1', 'label': 'Khipus graph (curated catalog)', 'as_of': OLD}]}})
    return {'v': 'kblocks/1', 'lang': lang, 'state': 'final', 'layout': 'auto', 'as_of': NOW, 'impl': 'genui.build@1', 'blocks': bl}


QUOTE = {'data': {'quotes': {'NVDA': {'px': 229.39, 'prev': 226.31, 'pct': 1.36, 'currency': 'USD', 'converted': False,
                                      'stamp': {'src': 'finnhub', 'via': None, 'as_of': NOW, 'age_s': 5, 'live': True, 'stale': False, 'ttl_s': 15}}},
                  'n': 1, 'missing': [], 'stale_after_s': 900}, 'view': {'name': 'quote', 'live': True}}

RENDER = r"""(a) => {
  var host = document.getElementById('kg-host'); if (!host) { host = document.createElement('div'); host.id = 'kg-host'; document.body.appendChild(host); }
  host.style.width = a.width + 'px'; host.style.margin = '0 auto'; host.textContent = '';
  var r = window.KhipuGenUI.renderAnswer(host, a.env, { answer: '', reqId: 'k' });
  return !!r;
}"""

TILES = r"""() => {
  var out = [], tiles = document.querySelectorAll('#kg-host .kg-tile');
  tiles.forEach(function (tl, i) {
    tl.querySelectorAll('*').forEach(function (el) {
      if (!el.textContent.trim() || el.tagName === 'svg' || el.tagName === 'path') return;
      if (el.scrollWidth > el.clientWidth + 1) out.push({ tile: i, cls: el.className, text: el.textContent.slice(0, 40), sw: el.scrollWidth, cw: el.clientWidth });
    });
    if (tl.scrollWidth > tl.clientWidth + 1) out.push({ tile: i, cls: 'TILE', sw: tl.scrollWidth, cw: tl.clientWidth });
  });
  var g = document.querySelector('#kg-host .kg-tiles');
  return { overflow: out, n: tiles.length, cols: g ? getComputedStyle(g).getPropertyValue('--kg-cols').trim() : '',
    bigs: [].map.call(document.querySelectorAll('#kg-host .kg-big'), function (e) { return e.textContent; }),
    labels: [].map.call(document.querySelectorAll('#kg-host .kg-tile .l > span:first-child'), function (e) { return e.textContent; }),
    chips: [].map.call(document.querySelectorAll('#kg-host .kg-tile .kg-src'), function (e) { return e.textContent; }),
    rows: g ? [].map.call(tiles, function (t) { return Math.round(t.getBoundingClientRect().top); }) : [],
    rootOverflow: (function () { var r = document.querySelector('#kg-host .kg-root'); return r ? r.scrollWidth > r.clientWidth + 1 : null; })() };
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


def _page(pw, quote=None, **kw):
    ctx, pg, errs = _open(pw, **kw)
    if quote is not None:
        ctx.route('http://khipu.test/api/hot/quote**', lambda route: route.fulfill(status=200, content_type='application/json', body=json.dumps(quote)))
    return ctx, pg, errs


# ── 2. tiles a 520 px ───────────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize('theme,lang', [('dark', 'es'), ('light', 'en')])
def test_tiles_a_520px_no_desbordan_y_van_en_2x2(pw, theme, lang):
    ctx, pg, errs = _page(pw, theme=theme, lang=lang)
    try:
        assert pg.evaluate(RENDER, {'width': 520, 'env': _env([_tiles()], lang)})
        pg.wait_for_timeout(150)
        r = pg.evaluate(TILES)
        assert r['n'] == 4 and r['cols'] == '2', r
        assert r['overflow'] == [], r['overflow']                       # ningún texto desborda su tile
        assert r['rootOverflow'] is False
        assert len(set(r['rows'])) == 2                                 # dos filas: 2×2
        big = r['bigs']
        assert any('5,52' in b or '5.52' in b for b in big) and any('T' in b for b in big), big       # $5,52 T, no «$5518…»
        assert any(b.startswith('+') for b in big), big                 # el cambio positivo lleva «+»
        assert any('NRS' in l for l in r['labels'])                     # etiqueta completa (dos líneas), no «Riesgo de r…»
        assert all('…' not in c for c in r['chips']), r['chips']
        assert not errs, errs
        # ancho normal (1100 px): 4 columnas, tampoco desborda
        assert pg.evaluate(RENDER, {'width': 1100, 'env': _env([_tiles()], lang)})
        r2 = pg.evaluate(TILES)
        assert r2['cols'] == '4' and r2['overflow'] == [] and len(set(r2['rows'])) == 1, r2
    finally:
        ctx.close()


# ── 3. una cotización por empresa en pantalla ──────────────────────────────────────────────────────────────────────
def test_tiles_y_en_una_mirada_leen_la_misma_cotizacion(pw):
    ctx, pg, errs = _page(pw, quote=QUOTE)
    try:
        # cifras del servidor: 228,52 de hace horas → el tile se refresca con /api/hot/quote (229,39, +1,36 %)
        assert pg.evaluate(RENDER, {'width': 700, 'env': _env([_tiles(), _card()])})
        pg.wait_for_function("() => [].some.call(document.querySelectorAll('#kg-host .kg-big'), e => e.textContent.indexOf('229,39') >= 0)", timeout=5000)
        r = pg.evaluate(TILES)
        assert any('229,39' in b for b in r['bigs']) and any(b.startswith('+1,36') for b in r['bigs']), r['bigs']
        assert not any('228,52' in b for b in r['bigs'])
        assert any('finnhub' in c for c in r['chips']), r['chips']          # el sello de la cotización, no el de la ficha
        card = pg.evaluate("() => document.querySelector('#kg-host .kg-cc-f').textContent")
        assert '229,39' in card and '+1,36' in card, card
        # «en una mirada» (engine/oswindows.js) lee el MISMO almacén
        assert pg.evaluate("() => { const C = window.BixbyCockpit; if (!C.isOpen || !C.isOpen()) C.open(); return window.KhipuOSWin.open('glance', { id: 'Nvidia' }); }")
        pg.wait_for_function("() => { const w = [...document.querySelectorAll('.kd-win')].find(w => w.textContent.indexOf('229,39') >= 0 || w.textContent.indexOf('229.39') >= 0); return !!w; }", timeout=5000)
        glance = pg.evaluate("() => [...document.querySelectorAll('.kd-win')].map(w => w.innerText).join('\\n')")
        assert ('229,39' in glance or '229.39' in glance) and '228,52' not in glance, glance[:400]
        assert '1,36' in glance or '1.36' in glance
        q = pg.evaluate("() => window.KhipuOSWin.quote.get('NVDA')")
        assert q and q['close'] == 229.39 and q['src'] == 'finnhub' and q['live'] == 229.39 and q['as_of'] == NOW
        mk = pg.evaluate("() => window.MKT.quotes.NVDA")
        assert mk and mk['close'] == 229.39 and mk['via'] == 'hot.quote'    # la app entera ve la misma cotización
        assert not errs, errs
    finally:
        ctx.close()


def test_sin_cotizacion_nueva_la_cifra_del_servidor_se_queda(pw):
    ctx, pg, errs = _page(pw)                                                # /api/hot/quote → 503 (offline)
    try:
        assert pg.evaluate(RENDER, {'width': 700, 'env': _env([_tiles()])})
        pg.wait_for_timeout(400)
        r = pg.evaluate(TILES)
        assert any('228,52' in b for b in r['bigs']) and any(b.startswith('+1') for b in r['bigs']), r['bigs']
        assert not errs, errs
    finally:
        ctx.close()


# ── 4. acciones sin duplicados ─────────────────────────────────────────────────────────────────────────────────────
def test_dossier_y_xray_una_sola_vez_con_un_rotulo(pw):
    ctx, pg, errs = _page(pw)
    try:
        acts = [{'kind': 'open_xray', 'label': {'es': 'Radiografía: Nvidia', 'en': 'X-Ray: Nvidia'}, 'entity': {'id': 'Nvidia', 'label': 'Nvidia'}},
                {'kind': 'open_dossier', 'label': {'es': 'Dossier: Nvidia', 'en': 'Dossier: Nvidia'}, 'entity': {'id': 'Nvidia', 'label': 'Nvidia'}},
                {'kind': 'open_window', 'window': 'supplychain', 'label': {'es': 'Cadena de suministro: Nvidia', 'en': 'Supply chain: Nvidia'}, 'entity': {'id': 'Nvidia', 'label': 'Nvidia'}}]
        env = _env([_tiles(), _card()], actions=acts)
        # el camino real: fillReply con el sobre Y las acciones del chat (open_xray + dossier de la misma empresa)
        q = {'text': 'ficha de Nvidia', 'env': env, 'tools': ['get_company'], 'agents': ['analista'], 'clear': True}
        n = pg.evaluate(ASK.replace("ai: true,", "ai: true, actions: [{type: 'open_xray', arg: 'Nvidia', label: 'Nvidia'}, {type: 'dossier', arg: 'Nvidia', label: 'Nvidia'}],"), q)
        assert n >= 3
        r = pg.evaluate(r"""() => {
          const th = document.getElementById('bcp-thread');
          const btns = [...th.querySelectorAll('button')].map(b => b.textContent.trim()).filter(t => /Dossier|X-Ray|Radiograf|Cadena de suministro/i.test(t));
          const chips = [...th.querySelectorAll('.kc-act')].map(b => b.textContent.trim());
          const hidden = [...th.querySelectorAll('[data-kg-type="actions"]')].map(e => e.hidden);
          return { btns, chips, hidden };
        }""")
        dos = [b for b in r['btns'] if 'Dossier' in b]
        xr = [b for b in r['btns'] if 'X-Ray' in b or 'Radiograf' in b]
        assert len(dos) == 1 and len(xr) == 1, r
        assert not any('Radiograf' in b for b in r['btns']), r['btns']    # un solo rótulo (el de la Cabina: X-Ray)
        assert any('Cadena de suministro' in b for b in r['btns']), r      # la ventana sí (nadie la ofrecía antes)
        assert not any('X-Ray' in c or 'Dossier' in c for c in r['chips']), r['chips']   # los chips del chat no repiten
        assert not errs, errs
        # EN: mismo rótulo único
        pg.evaluate("() => { try { localStorage.setItem('eco_lang', 'en'); } catch (e) {} window.LANG = 'en'; document.documentElement.setAttribute('lang', 'en'); }")
        pg.wait_for_timeout(300)
        en = pg.evaluate("() => [...document.querySelectorAll('#bcp-thread button')].map(b => b.textContent.trim()).filter(t => /Dossier|X-Ray/i.test(t))")
        assert len([b for b in en if 'X-Ray' in b]) == 1 and len([b for b in en if 'Dossier' in b]) == 1, en
    finally:
        ctx.close()
