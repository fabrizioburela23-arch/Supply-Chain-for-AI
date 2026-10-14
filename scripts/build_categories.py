#!/usr/bin/env python3
"""scripts/build_categories.py — genera nodes/categories_extra.js desde data/categories.json (FUENTE ÚNICA).

    python scripts/build_categories.py          # reescribe nodes/categories_extra.js
    python scripts/build_categories.py --check  # ¿está al día y el JSON es válido? (código 1 si no)
    python scripts/build_categories.py --css    # imprime las variables CSS (claro y oscuro) que van en app.html
    python scripts/build_categories.py --counts # empresas por categoría según data/grafo_v0.json
    python scripts/build_categories.py --delta-e  # ΔE mínimo (CIE76) de cada categoría nueva frente a todas las de app.html
    python scripts/build_categories.py --recolor  # reasigna colores de las nuevas con ΔE ≥ 12 y reescribe el JSON

Qué hace el JS generado (se carga JUSTO DESPUÉS de nodes/nodes_seed.js, antes de los demás nodes_*.js):
  · `window.CATS_EXTRA`         las categorías NUEVAS (lote 2026-10-14) → entran en CATS_NEW (engine/app_main.js
                                 las funde en CATS con Object.assign) y en CAT_TO_SECTOR, sin pisar nada que exista;
  · `window.CATS_LABELS_FIX`    etiquetas ES/EN de las categorías multicapa que mostraban su id crudo (x = 0,5 como
                                 hoy: el mapa no se mueve); nodes_multicapa.js solo rellena lo que falta, así que
                                 respeta estas;
  · `window.CAT_ALIASES`        alias → id consolidado (lo usa el importador para mapear categorías de un lote).

Determinista, stdlib, sin red. Las variables CSS NO se escriben solas: `--css` las imprime y se pegan en app.html
(claro en `:root`, oscuro en `.dark`); tests/test_catalog_fix_categories.py exige que coincidan con el JSON.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'data', 'categories.json')
OUT = os.path.join(ROOT, 'nodes', 'categories_extra.js')
SNAPSHOT = os.path.join(ROOT, 'data', 'grafo_v0.json')

ID_RX = re.compile(r'^[a-z][a-z0-9_]{1,60}$')
HEX_RX = re.compile(r'^#[0-9A-F]{6}$')
COLOR_SOURCES = ('css', 'sector', 'none')
STATUSES = ('active', 'approved', 'rejected')


def load(path=SRC):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def validate(doc):
    """Lista de problemas (vacía = JSON válido). Reglas: ids únicos y con forma; es/en/sector/cssVar en todas;
    sector conocido; cssVar = --c-<id>; alias únicos, que no sean ids; colores hex de las NUEVAS sin repetir;
    x en [0, 1]."""
    errs = []
    cats = doc.get('categories') or {}
    sectors = doc.get('sectors') or {}
    if not cats or not sectors:
        return ['categories/sectors vacíos']
    seen_alias, colors = {}, {}
    for cid, c in cats.items():
        if not ID_RX.match(cid):
            errs.append(f'id con forma inválida: {cid!r}')
        for k in ('es', 'en', 'sector', 'cssVar'):
            if not isinstance(c.get(k), str) or not c[k].strip():
                errs.append(f'{cid}: falta {k}')
        if c.get('sector') not in sectors:
            errs.append(f'{cid}: sector desconocido {c.get("sector")!r}')
        if c.get('cssVar') != '--c-' + cid:
            errs.append(f'{cid}: cssVar debe ser --c-{cid}')
        if c.get('color_source') not in COLOR_SOURCES:
            errs.append(f'{cid}: color_source ∉ {COLOR_SOURCES}')
        if c.get('status') not in STATUSES:
            errs.append(f'{cid}: status ∉ {STATUSES}')
        x = c.get('x')
        if not isinstance(x, (int, float)) or not 0 <= x <= 1:
            errs.append(f'{cid}: x fuera de [0, 1]')
        col = c.get('color')
        if c.get('color_source') == 'css':
            if not isinstance(col, dict) or not all(HEX_RX.match(str(col.get(t, ''))) for t in ('light', 'dark')):
                errs.append(f'{cid}: color light/dark en hex mayúsculas')
            else:
                for t in ('light', 'dark'):
                    prev = colors.setdefault((t, col[t]), cid)
                    # el catálogo viejo ya repetía colores entre sí (fabless/cloud…); lo NUEVO no puede repetir
                    if prev != cid and 'catalog' not in (c.get('origin'), cats[prev].get('origin')):
                        errs.append(f'{cid}: color {t} {col[t]} repetido con {prev}')
        elif col is not None:
            errs.append(f'{cid}: color debe ser null si color_source ≠ css')
        for a in c.get('aliases') or []:
            if a in cats:
                errs.append(f'{cid}: alias {a!r} es a la vez una categoría')
            if a in seen_alias and seen_alias[a] != cid:
                errs.append(f'alias {a!r} apunta a dos categorías: {seen_alias[a]} y {cid}')
            seen_alias[a] = cid
    for k, v in (doc.get('merged') or {}).items():
        if v not in cats or k not in (cats[v].get('aliases') or []):
            errs.append(f'merged {k} → {v}: {v} debe existir y tener a {k} entre sus alias')
    return errs


def aliases(doc):
    """alias → id consolidado (incluye el id mismo → id)."""
    out = {}
    for cid, c in (doc.get('categories') or {}).items():
        out[cid] = cid
        for a in c.get('aliases') or []:
            out[a] = cid
    return out


def resolve(cat, doc=None):
    """Categoría consolidada de un id o alias (None si no existe)."""
    return aliases(doc or load()).get(str(cat or '').strip().lower())


def _js_obj(d):
    return json.dumps(d, ensure_ascii=False, sort_keys=True, separators=(', ', ': '))


def render(doc):
    cats = doc['categories']
    extra = {k: {'label': v['es'], 'en': v['en'], 'cssVar': v['cssVar'], 'x': v['x']}
             for k, v in cats.items() if v.get('origin') != 'catalog' and v.get('status') != 'rejected'}
    fix = {k: {'label': v['es'], 'en': v['en'], 'cssVar': v['cssVar'], 'x': v['x']}
           for k, v in cats.items() if v.get('origin') == 'catalog' and v.get('label_fixed')}
    c2s = {k: cats[k]['sector'] for k in extra}
    al = {a: cid for a, cid in aliases(doc).items() if a != cid}
    lines = [
        '// nodes/categories_extra.js — GENERADO por scripts/build_categories.py desde data/categories.json.',
        '// NO EDITAR A MANO: cambia el JSON y regenera. Se carga justo después de nodes/nodes_seed.js.',
        f'// {len(extra)} categorías nuevas (lote {doc.get("as_of")}) + {len(fix)} etiquetas ES/EN de categorías que '
        'mostraban su id crudo.',
        '// Entra en CATS_NEW (engine/app_main.js la funde en CATS) y en CAT_TO_SECTOR SIN pisar lo que ya exista;',
        '// nodes_multicapa.js solo rellena lo que falta, así que respeta estas etiquetas.',
        'window.CATS_EXTRA = ' + _js_obj(extra) + ';',
        'window.CATS_LABELS_FIX = ' + _js_obj(fix) + ';',
        'window.CAT_TO_SECTOR_EXTRA = ' + _js_obj(c2s) + ';',
        'window.CAT_ALIASES = ' + _js_obj(al) + ';',
        '(function () {',
        "  var N = (typeof CATS_NEW !== 'undefined') ? CATS_NEW : null;",
        "  var C = (typeof CATS !== 'undefined') ? CATS : null;",
        "  var M = (typeof CAT_TO_SECTOR !== 'undefined') ? CAT_TO_SECTOR : null;",
        '  function put(src) { if (!N) return; Object.keys(src).forEach(function (k) { if (!N[k] && !(C && C[k])) N[k] = src[k]; }); }',
        '  put(window.CATS_EXTRA); put(window.CATS_LABELS_FIX);',
        '  if (M) Object.keys(window.CAT_TO_SECTOR_EXTRA).forEach(function (k) { if (!M[k]) M[k] = window.CAT_TO_SECTOR_EXTRA[k]; });',
        '})();',
        '',
    ]
    return '\n'.join(lines)


def css_lines(doc, theme):
    """Variables CSS de las categorías NUEVAS con color propio, agrupadas por sector (para pegar en app.html)."""
    cats = doc['categories']
    by = {}
    for k, v in cats.items():
        if v.get('origin') != 'catalog' and v.get('color_source') == 'css' and v.get('status') != 'rejected':
            by.setdefault(v['sector'], []).append(k)
    out = [f'  /* categorías del lote {doc.get("as_of")} (data/categories.json · scripts/build_categories.py --css) */']
    for sec in sorted(by):
        ids = sorted(by[sec])
        row, cur = [], ''
        for k in ids:
            piece = f'--c-{k}:{cats[k]["color"][theme]};'
            if len(cur) + len(piece) + 1 > 112:
                row.append(cur.rstrip())
                cur = ''
            cur += piece + ' '
        row.append(cur.rstrip())
        out.append(f'  /* · {sec} */')
        out += ['  ' + r for r in row]
    return out


# ── colores distinguibles (revisión lote K: varios nuevos quedaban a ΔE < 5 de uno existente) ────────────────────
APP_HTML = os.path.join(ROOT, 'app.html')
CSS_VAR_RX = re.compile(r'--c-([a-z_0-9]+)\s*:\s*(#[0-9A-Fa-f]{6})')
MIN_DELTA_E = 12.0          # al asignar; el test exige ≥ 10 entre cada nueva y TODAS las demás del mismo tema
L_RANGE = {'light': (0.26, 0.48), 'dark': (0.54, 0.76)}


def _hex_rgb(hx):
    hx = hx.lstrip('#')
    return tuple(int(hx[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def _rgb_hex(rgb):
    return '#' + ''.join(f'{max(0, min(255, round(c * 255))):02X}' for c in rgb)


def _lab(hx):
    """sRGB → CIE L*a*b* (D65)."""
    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in _hex_rgb(hx))
    x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047
    y = (0.2126729 * r + 0.7151522 * g + 0.0721750 * b) / 1.0
    z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / 1.08883

    def f(t):
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e(h1, h2):
    """ΔE CIE76 entre dos hex (≈ 2,3 = apenas perceptible; < 5 = iguales en una leyenda; ≥ 10 = distintos)."""
    a, b = _lab(h1), _lab(h2)
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def _hsl(hx):
    import colorsys
    r, g, b = _hex_rgb(hx)
    h, l, s_ = colorsys.rgb_to_hls(r, g, b)
    return h, s_, l


def _hex_hsl(h, s_, l):
    import colorsys
    return _rgb_hex(colorsys.hls_to_rgb(h % 1.0, max(0.0, min(1.0, l)), max(0.0, min(1.0, s_))))


def app_css_colors(theme, app_path=APP_HTML):
    """{id: hex} de TODAS las variables --c-* del tema en app.html (:root = claro, .dark = oscuro)."""
    with open(app_path, encoding='utf-8') as fh:
        app = fh.read()
    key = ':root{' if theme == 'light' else '.dark{'
    i = app.index(key)
    return {k: v.upper() for k, v in CSS_VAR_RX.findall(app[i:app.index('}', i)])}


def recolor(doc, min_de=MIN_DELTA_E, app_path=APP_HTML):
    """Reasigna el color de cada categoría NUEVA (color_source css, origin ≠ catalog) para que quede a ≥ `min_de`
    (ΔE CIE76) de todos los colores del catálogo del mismo tema y de las demás nuevas ya asignadas. Busca cerca del
    tono actual (banda del sector: ±30°, luego ±60°, luego cualquiera) variando tono, saturación y luminosidad dentro
    del rango del tema; elige el candidato más cercano al color de hoy que cumpla; si ninguno cumple, el más lejano
    de todos. Determinista. Devuelve [(id, tema, antes, después, ΔE mínimo)]."""
    cats = doc['categories']
    new_ids = sorted(k for k, v in cats.items()
                     if v.get('origin') != 'catalog' and v.get('color_source') == 'css' and v.get('status') != 'rejected')
    changes = []
    for theme in ('light', 'dark'):
        taken = {k: v for k, v in app_css_colors(theme, app_path).items() if k not in new_ids}
        lo, hi = L_RANGE[theme]
        for cid in new_ids:
            cur = cats[cid]['color'][theme].upper()
            h0, s0, l0 = _hsl(cur)
            labs = [(k, _lab(v)) for k, v in taken.items()]

            def min_de_of(hx):
                a = _lab(hx)
                return min((sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5 for _, b in labs), default=999.0)
            best, best_d, best_far, best_far_d = None, -1.0, None, -1.0
            for band in (30, 60, 180):
                for dh in range(-band, band + 1, 3):
                    for ds in (0, -0.1, 0.1, -0.2, 0.2):
                        for dl in (0, -0.04, 0.04, -0.08, 0.08, -0.12, 0.12, -0.16, 0.16):
                            l1 = l0 + dl
                            if not lo <= l1 <= hi:
                                continue
                            s1 = s0 + ds
                            if not 0.45 <= s1 <= 1.0:
                                continue
                            hx = _hex_hsl(h0 + dh / 360.0, s1, l1)
                            d = min_de_of(hx)
                            if d > best_far_d:
                                best_far, best_far_d = hx, d
                            if d >= min_de:
                                cost = abs(dh) + 60 * abs(ds) + 90 * abs(dl)
                                if best is None or cost < best_d:
                                    best, best_d = hx, cost
                if best is not None:
                    break
            chosen = best or best_far
            taken[cid] = chosen
            if chosen != cur:
                cats[cid]['color'][theme] = chosen
            changes.append((cid, theme, cur, chosen, round(min_de_of(chosen), 1)))
    return changes


def min_delta_e(doc, theme, app_path=APP_HTML):
    """ΔE mínimo entre cada categoría nueva y TODAS las demás variables --c-* del tema (lo que vigila el test)."""
    cols = app_css_colors(theme, app_path)
    cats = doc['categories']
    worst = (999.0, None, None)
    for cid, c in cats.items():
        if c.get('origin') == 'catalog' or c.get('color_source') != 'css' or c.get('status') == 'rejected':
            continue
        mine = c['color'][theme]
        for k, v in cols.items():
            if k == cid:
                continue
            d = delta_e(mine, v)
            if d < worst[0]:
                worst = (d, cid, k)
    return worst


def counts(doc, snapshot=SNAPSHOT):
    """Empresas por categoría en el snapshot (las nuevas tienen 0 hoy)."""
    try:
        with open(snapshot, encoding='utf-8') as fh:
            nodes = json.load(fh).get('nodes') or []
    except (OSError, ValueError):
        nodes = []
    al = aliases(doc)
    out = {k: 0 for k in doc['categories']}
    for n in nodes:
        cid = al.get(str(n.get('cat') or ''))
        if cid in out:
            out[cid] += 1
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    doc = load()
    errs = validate(doc)
    if errs:
        print('✗ data/categories.json inválido:\n  ' + '\n  '.join(errs))
        return 1
    if '--css' in argv:
        print(':root (claro):')
        print('\n'.join(css_lines(doc, 'light')))
        print('\n.dark (oscuro):')
        print('\n'.join(css_lines(doc, 'dark')))
        return 0
    if '--recolor' in argv:
        # reasigna los colores de las NUEVAS con ΔE ≥ 12 (ver recolor) y reescribe data/categories.json; luego hay que
        # regenerar el JS (sin bandera) y pegar `--css` en app.html
        ch = recolor(doc)
        with open(SRC, 'w', encoding='utf-8') as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=1)
            fh.write('\n')
        n = sum(1 for c in ch if c[2] != c[3])
        print(f'{n} colores cambiados de {len(ch)}; ΔE mínimo: claro {min(c[4] for c in ch if c[1] == "light")}, '
              f'oscuro {min(c[4] for c in ch if c[1] == "dark")}')
        for c in ch:
            if c[2] != c[3]:
                print(f'  {c[0]:28s} {c[1]:5s} {c[2]} → {c[3]}  (ΔE mín {c[4]})')
        return 0
    if '--delta-e' in argv:
        for t in ('light', 'dark'):
            d, a, b = min_delta_e(doc, t)
            print(f'{t}: ΔE mínimo nueva↔cualquiera = {d:.1f} ({a} vs {b})')
        return 0
    if '--counts' in argv:
        for k, v in sorted(counts(doc).items(), key=lambda kv: (-kv[1], kv[0])):
            print(f'{v:4d}  {k}')
        return 0
    text = render(doc)
    if '--check' in argv:
        try:
            with open(OUT, encoding='utf-8') as fh:
                cur = fh.read()
        except FileNotFoundError:
            cur = ''
        if cur != text:
            print('✗ nodes/categories_extra.js no está al día: corre python scripts/build_categories.py')
            return 1
        print('✓ nodes/categories_extra.js al día')
        return 0
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(text)
    print('escrito', os.path.relpath(OUT, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
