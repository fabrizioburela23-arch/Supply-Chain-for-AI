"""core/genui/a2ui.py — las respuestas visuales de Khipus en el idioma ABIERTO de Google: A2UI v1.0 (2026-11-25).

Pedido de Fabrizio: «interfaz interactiva lo más avanzada posible, con futuro, rápida, útil y adaptable» + entrar como
herramienta dentro de otras apps (Meru, Takenos, Confío). A2UI (github.com/a2ui-project/a2ui, Apache-2.0) es el
estándar para que un agente describa una interfaz en JSON y cada app la dibuje con SUS componentes nativos (web, Android,
iOS). Nuestro contrato kblocks/1 ya era esa idea; este módulo lo TRADUCE sin cambiar cómo se arma ni cómo se verifican
las cifras (core/genui sigue siendo la única fuente: procedencia de cada número, presupuesto, alt).

    to_a2ui(env, lang, catalog='khipus'|'basic', surface_id=None) → [mensajes A2UI v1.0]

Dos catálogos:
  · 'khipus' (KHIPUS_CATALOG_ID): básico + `KhipusBlock` — cada bloque visual va al MODELO DE DATOS (/blocks/<id>) y
    el componente lo enlaza con {"@path"}. Ventaja: un precio que se mueve = un `updateDataModel` en esa ruta, sin
    repintar la respuesta. Lo pinta engine/a2ui.js (Khipus OS) con los mismos gráficos de siempre.
  · 'basic' (el catálogo estándar de Google): SOLO Text/Row/Column/Card/Button/Divider — para el renderizador de
    serie de cualquier app socia. Cifras clave y tablas en componentes; gráficos como su texto alternativo (alt), que
    ya lleva las cifras verificadas. Nada se pierde ni se inventa.

Acciones: los botones mandan un evento A2UI `{"event": {"name": "khipus.<tipo>", "context": {...}}}` (abrir
dossier, preguntar…); las fuentes con enlace usan la función estándar `openUrl` (solo http/https, con clic).
NUNCA hay botones de órdenes: el chat es de solo lectura (regla de oro del dinero).
"""
import re

from core.genui.util import fmt_unit

VERSION = '1.0'
BASIC_CATALOG_ID = 'https://a2ui.org/specification/v1_0/catalogs/basic/catalog.json'
KHIPUS_CATALOG_ID = 'urn:khipus:a2ui:catalog:1.0'
NON_VISUAL = ('text', 'actions', 'sources', 'callout')
MAX_TABLE_ROWS = 12
_ID_RX = re.compile(r'[^A-Za-z0-9_]')

# el catálogo propio (JSON Schema, protocolVersion 1.0): básico + KhipusBlock. Se publica en /api/a2ui/catalog.json
KHIPUS_CATALOG = {
    '$schema': 'https://json-schema.org/draft/2020-12/schema',
    '$id': KHIPUS_CATALOG_ID,
    'catalogId': KHIPUS_CATALOG_ID,
    'protocolVersion': VERSION,
    'title': 'Khipus Finance Intelligence — bloques verificados',
    'description': ('Basic A2UI catalog + KhipusBlock: a verified financial block (kblocks/1) bound from the data '
                    'model. Every figure carries its source and time; renderers without KhipusBlock should show `alt`.'),
    'extends': [BASIC_CATALOG_ID],
    'components': {
        'KhipusBlock': {
            'type': 'object',
            'required': ['component', 'block'],
            'properties': {
                'component': {'const': 'KhipusBlock'},
                'block': {'description': 'Binding {"@path": "/blocks/<id>"} to a kblocks/1 block (type, data, title, '
                                         'sources, alt).'},
                'alt': {'type': 'string', 'description': 'Text alternative with the same verified figures.'},
                'compact': {'type': 'boolean'},
            },
        },
    },
}


def _cid(s):
    return _ID_RX.sub('_', str(s or 'x'))[:60] or 'x'


def _lab(x, lang):
    if isinstance(x, dict):
        return str(x.get(lang) or x.get('es') or x.get('en') or '')
    return str(x or '')


class _Builder:
    def __init__(self, lang):
        self.lang, self.comps, self.n = lang, [], 0

    def add(self, comp, prefix='c'):
        self.n += 1
        comp = dict(comp)
        comp.setdefault('id', f'{prefix}{self.n}')
        self.comps.append(comp)
        return comp['id']

    def text(self, s, variant=None):
        c = {'component': 'Text', 'text': str(s)}
        if variant:
            c['variant'] = variant
        return self.add(c, 't')

    def col(self, children, **kw):
        return self.add({'component': 'Column', 'children': [c for c in children if c], **kw}, 'col')

    def row(self, children, **kw):
        return self.add({'component': 'Row', 'children': [c for c in children if c], **kw}, 'row')

    def card(self, child):
        return self.add({'component': 'Card', 'child': child}, 'card')


def _fmt_value(v, unit, lang):
    if isinstance(v, dict):
        if 'label' in v and 'v' not in v:
            return _lab(v.get('label'), lang)
        if v.get('v') is None:
            return '—'
        return fmt_unit(v['v'], v.get('unit') or unit, lang, v.get('currency'))
    if isinstance(v, bool) or v is None:
        return '—' if v is None else str(v)
    if isinstance(v, (int, float)):
        return fmt_unit(v, unit, lang, None)
    return str(v)


def _basic_visual(b, blk, lang):
    """Un bloque visual con SOLO componentes básicos: título + contenido + aviso de fuente."""
    d = blk.get('data') or {}
    t = blk.get('type')
    kids = []
    title = _lab(blk.get('title'), lang)
    if title:
        kids.append(b.text(title))
    sub = _lab(blk.get('subtitle'), lang)
    if sub:
        kids.append(b.text(sub, 'caption'))
    if t == 'metric.tiles':
        tiles = []
        for it in (d.get('items') or [])[:6]:
            tiles.append(b.col([b.text(_fmt_value(it.get('value'), None, lang)),
                                b.text(_lab(it.get('label'), lang), 'caption')], weight=1))
        kids.append(b.row(tiles, justify='spaceBetween'))
    elif t == 'table':
        cols = (d.get('columns') or [])[:6]
        kids.append(b.row([b.text(_lab(c.get('label'), lang), 'caption') for c in cols], justify='spaceBetween'))
        for r in (d.get('rows') or [])[:MAX_TABLE_ROWS]:
            if isinstance(r, dict):
                cells = [b.text(_fmt_value(r.get(c.get('key')), (c.get('values') or {}).get('unit'), lang)) for c in cols]
                kids.append(b.row(cells, justify='spaceBetween'))
    else:
        alt = _lab(blk.get('alt'), lang)
        if alt:
            kids.append(b.text(alt))
    return b.card(b.col(kids))


def _action_button(b, it, lang):
    kind = str(it.get('kind') or 'ask')
    ctx = {'kind': kind}
    ent = it.get('entity') or {}
    if ent.get('id'):
        ctx['entity'] = str(ent['id'])
    for k in ('window', 'lat', 'lon'):
        if it.get(k) is not None:
            ctx[k] = it[k]
    label = b.text(_lab(it.get('label'), lang))
    return b.add({'component': 'Button', 'child': label, 'variant': 'borderless',
                  'action': {'event': {'name': f'khipus.{_cid(kind)}', 'context': ctx}}}, 'btn')


def _sources(b, blk, lang):
    kids = [b.text('Fuentes' if lang == 'es' else 'Sources', 'caption')]
    for it in ((blk.get('data') or {}).get('items') or [])[:12]:
        line = ' · '.join(x for x in (it.get('id'), it.get('label'), str(it.get('as_of') or '')[:16]) if x)
        url = it.get('url')
        if isinstance(url, str) and url.startswith(('http://', 'https://')):
            kids.append(b.add({'component': 'Button', 'variant': 'borderless', 'child': b.text(line, 'caption'),
                               'action': {'functionCall': {'@call': 'openUrl', 'args': {'url': url}}}}, 'src'))
        else:
            kids.append(b.text(line, 'caption'))
    return b.col(kids)


def _callout(b, blk, lang):
    d = blk.get('data') or {}
    kids = []
    for key, es, en in (('pros', 'A favor', 'For'), ('cons', 'En contra', 'Against')):
        items = d.get(key) or []
        if items:
            kids.append(b.text(es if lang == 'es' else en, 'caption'))
            kids += [b.text('• ' + str(x.get('text') or '')) for x in items[:5] if isinstance(x, dict)]
    if d.get('text'):
        kids.append(b.text(_lab(d.get('text'), lang)))
    return b.card(b.col(kids)) if kids else None


def to_a2ui(env, lang='es', catalog='khipus', surface_id=None):
    """Sobre kblocks/1 → lista de mensajes A2UI v1.0 (createSurface con todo; un solo mensaje basta). None si no hay
    sobre válido. Determinista: el mismo sobre da los mismos mensajes."""
    if not isinstance(env, dict) or not isinstance(env.get('blocks'), list):
        return None
    lang = 'en' if lang == 'en' else 'es'
    basic = catalog == 'basic'
    b = _Builder(lang)
    model = {'meta': {'as_of': env.get('as_of'), 'lang': lang, 'layout': env.get('layout'), 'kblocks': env.get('v')},
             'blocks': {}}
    order = []
    for blk in env['blocks']:
        if not isinstance(blk, dict):
            continue
        t = blk.get('type')
        if t == 'text':
            md = (blk.get('data') or {}).get('md') or ''
            if md:
                order.append(b.text(md))
        elif t == 'actions':
            btns = [_action_button(b, it, lang) for it in ((blk.get('data') or {}).get('items') or [])[:4]
                    if isinstance(it, dict)]
            if btns:
                order.append(b.row(btns, justify='start'))
        elif t == 'sources':
            order.append(_sources(b, blk, lang))
        elif t == 'callout' and basic:
            c = _callout(b, blk, lang)
            if c:
                order.append(c)
        elif basic:
            order.append(_basic_visual(b, blk, lang))
        else:
            key = _cid(blk.get('id') or f'k{len(model["blocks"]) + 1}')
            model['blocks'][key] = blk
            order.append(b.add({'component': 'KhipusBlock', 'block': {'@path': f'/blocks/{key}'},
                                'alt': _lab(blk.get('alt'), lang)}, 'kb'))
    b.comps.insert(0, {'id': 'root', 'component': 'Column', 'children': order})
    create = {'surfaceId': _cid(surface_id or 'khipus_answer'),
              'catalogId': BASIC_CATALOG_ID if basic else KHIPUS_CATALOG_ID,
              'components': b.comps}
    if not basic:
        create['dataModel'] = model
    return [{'version': VERSION, 'createSurface': create}]


def data_update(surface_id, path, value):
    """Un cambio en vivo (p. ej. el precio de una cifra clave) sin repintar: updateDataModel."""
    return {'version': VERSION, 'updateDataModel': {'surfaceId': _cid(surface_id), 'path': path, 'value': value}}


def wants(ctx_raw):
    """¿El cliente pidió A2UI? context.ui_format ∈ {'a2ui', 'a2ui:basic'} (o a2uiRendererCapabilities)."""
    if not isinstance(ctx_raw, dict):
        return None
    fmt = str(ctx_raw.get('ui_format') or '').strip().lower()
    caps = ctx_raw.get('a2uiRendererCapabilities')
    ids = caps.get('supportedCatalogIds') if isinstance(caps, dict) else None
    if isinstance(ids, list):
        if KHIPUS_CATALOG_ID in ids:
            return 'khipus'
        if BASIC_CATALOG_ID in ids:
            return 'basic'
    if fmt == 'a2ui:basic':
        return 'basic'
    if fmt == 'a2ui':
        return 'khipus'
    return None
