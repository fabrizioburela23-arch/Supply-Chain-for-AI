"""core/genui/alt.py — textos `alt` (equivalente en texto de cada bloque: lector de pantalla, voz, «ver como tabla»)
y `spoken` (lo que la voz puede añadir: QUÉ quedó en pantalla, SIN cifras). Plantillas ES/EN del servidor: solo
usan valores que YA están en el bloque (nunca texto de la IA, nunca una cifra nueva). docs/CHAT_UI_GENERATIVA.md §2.5.
"""
from core.genui.util import clip, fmt, fmt_unit, i18n


def _lab(x, lang):
    if isinstance(x, dict):
        return x.get(lang) or x.get('es') or ''
    return str(x or '')


def _fig(f, lang, missing):
    if not isinstance(f, dict):
        return None
    if f.get('v') is None:
        return missing
    return fmt_unit(f['v'], f.get('unit'), lang, f.get('currency'))


def _names(items, n=3):
    return ', '.join(x for x in items[:n] if x)


def alt_of(block):
    """{es, en} para un bloque (o None si el tipo no lleva cifras ni alt obligatorio)."""
    t = block.get('type')
    d = block.get('data') or {}
    out = {}
    for lang in ('es', 'en'):
        es = lang == 'es'
        miss = 'sin dato' if es else 'no data'
        if t == 'metric.tiles':
            parts = []
            for it in d.get('items') or []:
                parts.append(f"{_lab(it.get('label'), lang)}: {_fig(it.get('value'), lang, miss)}")
            s = '; '.join(parts)
        elif t == 'company.card':
            c = (d.get('company') or {}).get('label') or ''
            bits = []
            for k, es_l, en_l in (('price', 'precio', 'price'), ('change', 'cambio', 'change'),
                                  ('market_cap', 'capitalización', 'market cap'), ('nrs', 'NRS', 'NRS')):
                if isinstance(d.get(k), dict):
                    bits.append(f"{es_l if es else en_l} {_fig(d[k], lang, miss)}")
            pv = d.get('private_valuation')
            if isinstance(pv, dict):
                bits.append(('última valuación ' if es else 'last valuation ') + _fig(pv.get('value'), lang, miss))
            sup = _names([(x.get('entity') or {}).get('label') for x in d.get('top_suppliers') or []])
            cus = _names([(x.get('entity') or {}).get('label') for x in d.get('top_customers') or []])
            s = f"{c}: " + ', '.join(bits)
            if sup:
                s += ('. Proveedores: ' if es else '. Suppliers: ') + sup
            if cus:
                s += ('. Clientes: ' if es else '. Customers: ') + cus
        elif t == 'chart.line':
            parts = []
            for se in d.get('series') or []:
                pts = [p for p in se.get('points') or [] if p and p[1] is not None]
                if not pts:
                    continue
                unit = 'index' if d.get('rebased') else (se.get('values') or {}).get('unit')
                cur = (se.get('values') or {}).get('currency')
                a, b = pts[0], pts[-1]
                parts.append((f"{_lab(se.get('name'), lang)}: de {fmt_unit(a[1], unit, lang, cur)} ({a[0][:10]}) "
                              f"a {fmt_unit(b[1], unit, lang, cur)} ({b[0][:10]})") if es else
                             (f"{_lab(se.get('name'), lang)}: from {fmt_unit(a[1], unit, lang, cur)} ({a[0][:10]}) "
                              f"to {fmt_unit(b[1], unit, lang, cur)} ({b[0][:10]})"))
            s = '; '.join(parts)
        elif t in ('chart.bar', 'ranking'):
            vs = d.get('values') or d.get('metric') or {}
            unit, cur = vs.get('unit'), vs.get('currency')
            parts = []
            for it in (d.get('items') or [])[:5]:
                name = _lab(it.get('label'), lang) or (it.get('entity') or {}).get('label') or ''
                parts.append(f"{name} {fmt_unit(it.get('v'), unit, lang, cur)}")
            n = len(d.get('items') or [])
            s = '; '.join(parts) + (f" (+{n - 5} {'más' if es else 'more'})" if n > 5 else '')
        elif t == 'graph.mini':
            c = (d.get('center') or {}).get('label') or ''
            sup = _names([(x.get('entity') or {}).get('label') for x in d.get('nodes') or []
                          if x.get('role') == 'supplier'], 5)
            cus = _names([(x.get('entity') or {}).get('label') for x in d.get('nodes') or []
                          if x.get('role') == 'customer'], 5)
            s = c + ('. Proveedores: ' if es else '. Suppliers: ') + (sup or '—') + \
                ('. Clientes: ' if es else '. Customers: ') + (cus or '—')
        elif t == 'impact.cascade':
            o = (d.get('origin') or {}).get('label') or ''
            hops = [h for h in d.get('hops') or [] if h.get('count') is not None]
            hs = ', '.join(f"{('salto' if es else 'hop')} {h['hop']}: {fmt(h['count'], lang)}" for h in hops)
            s = ((f"Choque en {o}: {fmt(d.get('total'), lang)} empresas golpeadas ≥ "
                  f"{fmt_unit(d.get('threshold_pct'), 'pct', lang) if d.get('threshold_pct') is not None else 'el umbral'}"
                  f" ({hs})") if es else
                 (f"Shock at {o}: {fmt(d.get('total'), lang)} companies hit ≥ "
                  f"{fmt_unit(d.get('threshold_pct'), 'pct', lang) if d.get('threshold_pct') is not None else 'the threshold'}"
                  f" ({hs})"))
            riv = [f"{(r.get('entity') or {}).get('label')} {fmt_unit(r.get('damage_pct'), 'pct', lang)}"
                   for r in d.get('least_hit_rivals') or []]
            if riv:
                s += ('. Rivales poco golpeados (daño): ' if es else '. Least-hit rivals (damage): ') + ', '.join(riv)
        elif t == 'timeline':
            items = d.get('items') or []
            s = (f"{len(items)} {'hechos' if es else 'items'}: " +
                 '; '.join(f"{str(it.get('date'))[:10]} {_lab(it.get('title'), lang)}" for it in items[:3]))
        elif t == 'geo.mini':
            pts = d.get('points') or []
            s = (f"{'Mapa con' if es else 'Map with'} {len(pts)} {'puntos' if es else 'points'}: " +
                 _names([_lab(p.get('label'), lang) for p in pts], 4))
        elif t == 'callout':
            v = d.get('variant')
            if v == 'pros_cons':
                s = (('A favor: ' if es else 'For: ') + '; '.join(x.get('text', '') for x in d.get('pros') or [])
                     + ('. En contra: ' if es else '. Against: ') + '; '.join(x.get('text', '') for x in d.get('cons') or []))
            else:
                s = _lab(d.get('text'), lang) or '; '.join(x.get('text', '') for x in d.get('items') or [])
        elif t == 'comparison':
            ents = [e.get('label') for e in d.get('entities') or []]
            s = ' vs '.join(ents)
            for m in (d.get('metrics') or [])[:4]:
                vs = m.get('values') or {}
                cells = ', '.join(f"{ents[i] if i < len(ents) else ''} {fmt_unit(c, vs.get('unit'), lang, vs.get('currency'))}"
                                  for i, c in enumerate(m.get('cells') or []))
                s += f". {_lab(vs.get('label'), lang) or m.get('key')}: {cells}"
        else:
            return None
        out[lang] = clip(s, 400)
    return i18n(out['es'], out['en'])


_KIND_NAME = {
    'metric.tiles': ('las cifras clave', 'the key figures'),
    'company.card': ('la ficha', 'the company card'),
    'chart.line': ('el gráfico de precio', 'the price chart'),
    'chart.bar': ('un gráfico de barras', 'a bar chart'),
    'ranking': ('un ranking', 'a ranking'),
    'graph.mini': ('la cadena de suministro', 'the supply chain'),
    'impact.cascade': ('la cascada del choque', 'the shock cascade'),
    'timeline': ('una línea de tiempo', 'a timeline'),
    'geo.mini': ('un mapa', 'a map'),
    'callout': ('los puntos a favor y en contra', 'the pros and cons'),
    'comparison': ('una comparación', 'a comparison'),
    'table': ('una tabla', 'a table'),
    'image': ('un diagrama', 'a diagram'),
    'chart.candles': ('un gráfico de velas', 'a candlestick chart'),
}


def spoken_of(blocks):
    """Lo que la voz puede añadir: QUÉ quedó en pantalla. SIN cifras (ni siquiera conteos)."""
    seen = []
    for b in blocks:
        t = b.get('type')
        if t == 'callout' and (b.get('data') or {}).get('variant') != 'pros_cons':
            continue
        if t in _KIND_NAME and t not in seen:
            seen.append(t)
    if not seen:
        return None
    es = [_KIND_NAME[t][0] for t in seen[:4]]
    en = [_KIND_NAME[t][1] for t in seen[:4]]

    def join(xs, y):
        return xs[0] if len(xs) == 1 else ', '.join(xs[:-1]) + f' {y} ' + xs[-1]
    return i18n('Te dejé en pantalla ' + join(es, 'y') + '.', 'I left ' + join(en, 'and') + ' on screen.')
