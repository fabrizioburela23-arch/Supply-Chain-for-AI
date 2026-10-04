"""ontology/reconcile.py — G3 (misión de reparación 2026-10-04): RECONCILIACIÓN
append-only entre el catálogo (data/grafo_v0.json, la verdad del MAPA/MCP) y
Postgres (la verdad del GRAFO: motor de matrices, NRS servidor, Grafo Temporal,
get_ontology_object).

Por qué existe: la limpieza de datos de Etapa 2 (fusiones por alias, dedupe,
volteo de dirección a "source PROVEE a target") se hizo reescribiendo el
catálogo y el snapshot, pero NUNCA se reprodujo como eventos en Postgres — y
la base de producción no puede re-migrarse (216 objetos irreproducibles).

Qué hace: compara y PROPONE (dry-run) correcciones por categoría; `apply`
emite SOLO eventos (RetractarVinculo dirigido, FusionarEntidad, LinkCreated)
con el canal `source='reconcile_v0:<run_id>'`; `rollback_run` las deshace con
más eventos. Nada se borra ni se actualiza a mano (regla 5).

Alcance — la reconciliación SOLO toca filas de `links`:
  · vigentes (valid_to IS NULL),
  · con valid_from = GENESIS (2000-01-01: la "foto" del catálogo migrada),
  · con un rel_type del vocabulario del catálogo,
  · sin fuente externa en properties.source (wikidata/gleif…), ni factores,
  · cuyos dos extremos (tras resolver alias) sean nodos del snapshot.
Los hechos con fecha real, las noticias, los factores y los objetos que solo
existen en Postgres NO se tocan — EXCEPTO al fusionar un alias: fusionar una
empresa duplicada mueve TODOS sus vínculos vigentes al canónico (con su fecha,
su documento de procedencia y su confianza), porque es la misma empresa.

Seguridad (revisión adversarial G5): aplicar y deshacer toman un candado de
Postgres (pg_advisory_lock): nunca corren dos a la vez. Aplicar exige que las
cifras del plan sean las que la persona revisó (`expect`); si cambiaron, se
niega. Lo que una persona cerró DESPUÉS de una corrida no se resucita al
deshacerla, y lo que una persona rechazó no se propone como 'faltante'.

Categorías (y si la orden por defecto las aplica):
  alias       empresa duplicada que el catálogo ya fusionó      → sí (FusionarEntidad)
  duplicates  misma tripla + mismo peso repetida                → sí (se conserva la más antigua)
  direction   X→Y en la base pero Y→X en el catálogo            → NO: lista para Fabrizio (decisión D5)
  variants    misma tripla, otro peso                           → NO (revisar)
  missing     está en el catálogo, falta en la base             → NO (revisar)
  extra       está en la base, no en el catálogo                → NO (revisar)
"""
import json
import os
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select

from ontology.models import Event, LinkRecord, ObjectRecord, EventType

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT_PATH = os.path.join(_ROOT, 'data', 'grafo_v0.json')
GENESIS = '2000-01-01'
ACTOR = 'script:reconcile_v0'
RUN_PREFIX = 'reconcile_v0:'
ROLLBACK_PREFIX = 'reconcile_v0_rollback:'
CATEGORIES = ('alias', 'duplicates', 'direction', 'variants', 'missing', 'extra')
DEFAULT_APPLY = ('alias', 'duplicates')
EXTERNAL_SOURCES = ('wikidata', 'gleif', 'news', 'sec', 'edgar')
MAX_ALIAS_HOPS = 5


class ReconcileError(RuntimeError):
    """Mensaje en español (args[0]) + inglés (`en`) para la UI bilingüe."""
    def __init__(self, es, en=None):
        super().__init__(es)
        self.en = en or es


LOCK_KEY = 74_281_337          # pg_advisory_lock de reconcile (aplicar / deshacer)


# ───────────────────────── snapshot ─────────────────────────

def load_snapshot(path=None):
    path = path or SNAPSHOT_PATH
    with open(path, encoding='utf-8') as f:
        g = json.load(f)
    return snapshot_from_dict(g, path=path)


def snapshot_from_dict(g, path=None):
    alias = dict(g.get('node_id_alias') or {})
    nodes = {n['id'] for n in g.get('nodes') or []}
    triples = {}
    for l in g.get('links') or []:
        s, t, rel = l.get('source'), l.get('target'), l.get('type') or 'supply'
        if not s or not t or s == t:
            continue
        key = (s, t, rel)
        if key in triples:                     # el merge ya dedupea; por si acaso: mayor peso
            if _w(l.get('w')) is not None and (_w(triples[key]['w']) or 0) < _w(l.get('w')):
                triples[key] = {'w': l.get('w'), 'rel': l.get('rel') or ''}
            continue
        triples[key] = {'w': l.get('w'), 'rel': l.get('rel') or ''}
    return {'path': path, 'exported_at': g.get('exported_at'), 'alias': alias, 'nodes': nodes, 'triples': triples,
            'rels': {k[2] for k in triples}}


def canon(alias_map, oid):
    seen = 0
    while oid in alias_map and seen < MAX_ALIAS_HOPS:
        oid = alias_map[oid]
        seen += 1
    return oid


def _w(v):
    try:
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None


def _same_w(a, b):
    a, b = _w(a), _w(b)
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) < 1e-9


def _is_genesis(dt):
    if dt is None:
        return False
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    return dt.date().isoformat() == GENESIS


def _now():
    return datetime.now(timezone.utc)


# ───────────────────────── plan (dry-run) ─────────────────────────

def _load_db(session):
    objs = {o.id: o for o in session.scalars(select(ObjectRecord)).all()}
    links = session.scalars(select(LinkRecord).where(LinkRecord.valid_to.is_(None))).all()
    return objs, links


def _row_scope(row, snap):
    """None si está en alcance; si no, el motivo (fuera_de_alcance)."""
    if not _is_genesis(row.valid_from):
        return 'fecha_real'
    if row.rel_type not in snap['rels']:
        return 'rel_fuera_del_catalogo'
    props = row.properties or {}
    src = str(props.get('source') or '').lower()
    if props.get('factor') or (src and any(src.startswith(x) for x in EXTERNAL_SOURCES)):
        return 'fuente_externa'
    cs, ct = canon(snap['alias'], row.source_id), canon(snap['alias'], row.target_id)
    if cs not in snap['nodes'] or ct not in snap['nodes']:
        return 'objeto_fuera_del_catalogo'
    return None


def _creation_order(session, rows):
    from ontology.service import _creation_event_for
    out = {}
    for r in rows:
        ev = _creation_event_for(session, r)
        out[str(r.id)] = (ev.recorded_at.isoformat() if ev is not None and ev.recorded_at else '9999', str(r.id))
    return out


def _human_rejections(session):
    """Pares que una persona/agente cerró (LinkRemoved NO dirigido y fuera de
    las corridas de reconcile): {(s, t, rel|None)}. No se proponen como faltantes."""
    out = set()
    for ev in session.scalars(select(Event).where(Event.event_type == EventType.LINK_REMOVED.value)).all():
        p = ev.payload or {}
        if (p.get('properties') or {}).get('retracts_event_id'):
            continue
        if str(ev.source or '').startswith((RUN_PREFIX, ROLLBACK_PREFIX)):
            continue
        out.add((ev.object_id, ev.target_id, p.get('rel_type') or p.get('type')))
    return out


def build_plan(session, snap):
    objs, links = _load_db(session)
    rejected = _human_rejections(session)
    alias_map, triples = snap['alias'], snap['triples']
    plan = {k: [] for k in CATEGORIES}
    plan['objects_missing'] = []
    plan['missing_rejected'] = []
    out_of_scope = defaultdict(int)

    # 1) alias: objetos que el catálogo fusionó y en la base siguen vivos
    for a, c in sorted(alias_map.items()):
        cc = canon(alias_map, a)
        oa = objs.get(a)
        if oa is None or (oa.properties or {}).get('merged_into'):
            continue
        n_links = sum(1 for l in links if a in (l.source_id, l.target_id))
        plan['alias'].append({'alias': a, 'canonical': cc, 'alias_label': oa.label,
                              'canonical_in_db': cc in objs, 'links_vigentes': n_links,
                              'action': 'FusionarEntidad' if cc in objs else 'omitir (canónico ausente en la base)'})

    scoped = []
    any_present = set()                # TODA fila vigente (en alcance o no) cuenta como "ya está"
    for l in links:
        any_present.add((canon(alias_map, l.source_id), canon(alias_map, l.target_id), l.rel_type))
        why = _row_scope(l, snap)
        if why:
            out_of_scope[why] += 1
        else:
            scoped.append(l)

    # 2) duplicados exactos (ids crudos: la fusión de alias ya cubre los cruzados)
    groups = defaultdict(list)
    for l in scoped:
        groups[(l.source_id, l.target_id, l.rel_type, round(_w(l.weight), 6) if _w(l.weight) is not None else None)].append(l)
    dup_retract = set()
    for (s, t, rel, w), rows in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2])):
        if len(rows) < 2:
            continue
        order = _creation_order(session, rows)
        cat = triples.get((canon(alias_map, s), canon(alias_map, t), rel)) or {}
        # G5: se conserva la copia cuyo texto es el del catálogo (si alguna lo es), si no la más antigua
        rows = sorted(rows, key=lambda r: (0 if cat and (r.properties or {}).get('rel_label') == cat.get('rel') else 1,
                                           order[str(r.id)]))
        keep, rest = rows[0], rows[1:]
        dup_retract.update(str(r.id) for r in rest)
        plan['duplicates'].append({'source': s, 'target': t, 'rel': rel, 'weight': w, 'keep_link_id': str(keep.id),
                                   'retract_link_ids': [str(r.id) for r in rest], 'copies': len(rows)})

    # 3-6) dirección / variantes / sobrantes (sobre ids canónicos) y faltantes
    present = defaultdict(list)       # (cs, ct, rel) → filas
    for l in scoped:
        if str(l.id) in dup_retract:
            continue
        present[(canon(alias_map, l.source_id), canon(alias_map, l.target_id), l.rel_type)].append(l)

    for (cs, ct, rel), rows in sorted(present.items()):
        via_alias = any(r.source_id != cs or r.target_id != ct for r in rows)
        if cs not in objs or ct not in objs:
            # G5: el canónico no existe en la base → re-crear fallaría (FK); se reporta aparte
            plan['objects_missing'].append({'source': cs, 'target': ct, 'rel': rel,
                                            'missing': [x for x in (cs, ct) if x not in objs],
                                            'db_link_ids': [str(r.id) for r in rows]})
            continue
        if (cs, ct, rel) in triples:
            sw = triples[(cs, ct, rel)]['w']
            exact = any(_same_w(r.weight, sw) for r in rows)
            for r in rows:
                if not _same_w(r.weight, sw):
                    plan['variants'].append({'link_id': str(r.id), 'source': r.source_id, 'target': r.target_id, 'rel': rel,
                                             'weight_db': _w(r.weight), 'weight_catalog': _w(sw), 'via_alias': via_alias,
                                             'rel_label': triples[(cs, ct, rel)]['rel'], 'catalog_row_exists': exact,
                                             'action': ('retractar (ya existe la fila con el peso del catálogo)' if exact
                                                        else 'retractar fila y re-crear con el peso del catálogo')})
            continue
        if (ct, cs, rel) in triples:
            cat = triples[(ct, cs, rel)]
            reverse_present = (ct, cs, rel) in any_present
            for r in rows:
                plan['direction'].append({'link_id': str(r.id), 'db_source': r.source_id, 'db_target': r.target_id,
                                          'catalog_source': ct, 'catalog_target': cs, 'rel': rel, 'weight_db': _w(r.weight),
                                          'weight_catalog': _w(cat['w']), 'rel_label': cat['rel'], 'via_alias': via_alias,
                                          'already_correct_in_db': reverse_present,
                                          'hub': ct if ct in _HUBS else (cs if cs in _HUBS else ct),
                                          'action': ('retractar (la dirección correcta ya existe)' if reverse_present
                                                     else 'retractar y re-crear al revés (catálogo)')})
            continue
        for r in rows:
            plan['extra'].append({'link_id': str(r.id), 'source': r.source_id, 'target': r.target_id, 'rel': rel,
                                  'weight_db': _w(r.weight), 'via_alias': via_alias,
                                  'rel_label_db': (r.properties or {}).get('rel_label') or '',
                                  'action': 'retractar (no está en el catálogo)'})

    for (s, t, rel), cat in sorted(triples.items()):
        if (s, t, rel) in any_present or (t, s, rel) in any_present:
            continue                   # presente (o al revés: eso lo cubre 'direction' o está fuera de alcance)
        if s not in objs or t not in objs:
            plan['objects_missing'].append({'source': s, 'target': t, 'rel': rel,
                                            'missing': [x for x in (s, t) if x not in objs]})
            continue
        if (s, t, rel) in rejected or (s, t, None) in rejected:
            plan['missing_rejected'].append({'source': s, 'target': t, 'rel': rel,
                                             'note': 'una persona o agente lo cerró en la base: no se re-crea'})
            continue
        plan['missing'].append({'source': s, 'target': t, 'rel': rel, 'weight_catalog': _w(cat['w']),
                                'rel_label': cat['rel'], 'action': 'LinkCreated (valid_from GENESIS)'})

    plan['out_of_scope'] = dict(out_of_scope)
    plan['summary'] = {k: len(plan[k]) for k in CATEGORIES}
    plan['summary']['objects_missing'] = len(plan['objects_missing'])
    plan['summary']['missing_rejected'] = len(plan['missing_rejected'])
    plan['summary']['db_links_vigentes'] = len(links)
    plan['summary']['db_objects'] = len(objs)
    plan['summary']['catalog_links'] = len(triples)
    plan['summary']['catalog_nodes'] = len(snap['nodes'])
    plan['snapshot'] = {'exported_at': snap.get('exported_at')}      # G5: sin rutas del servidor
    plan['as_of'] = _now().isoformat(timespec='seconds')
    plan['default_apply'] = list(DEFAULT_APPLY)
    return plan


_HUBS = {'TSMC', 'Nvidia', 'ASML', 'Samsung', 'SKHynix', 'Micron', 'Intel', 'AMD', 'Apple', 'Microsoft', 'Amazon',
         'Alphabet', 'Meta', 'OpenAI', 'Broadcom', 'Qualcomm', 'Arm', 'Tesla', 'Oracle', 'Dell', 'Supermicro'}


# ───────────────────────── informe para Fabrizio (ES/EN) ─────────────────────────

_TXT = {
    'es': {
        'title': 'Revisión del grafo: catálogo vs base de datos (Postgres)',
        'meta': 'Generado: {as_of} · base: `{db}` · catálogo exportado: `{snap}` · modo: **solo lectura** — nada se ha cambiado.',
        'why': ('Por qué importa: el mapa y las herramientas MCP leen el CATÁLOGO; el motor de matrices, el NRS del servidor y '
                'el Grafo Temporal leen la BASE. Si no coinciden, el mismo shock da resultados distintos según la pantalla.'),
        'summary': 'Resumen', 'col_cat': 'Categoría', 'col_n': 'Cuántos', 'col_fix': 'Qué hace el arreglo',
        'col_default': '¿Se aplica con "Aplicar lo seguro"?', 'yes': '**Sí**', 'no': 'No — hay que marcarla',
        'counts': 'Base: {dbo} objetos · {dbl} vínculos vigentes. Catálogo: {cn} nodos · {cl} vínculos. No se tocan (fuera de alcance): {oos}.',
        'objmiss': 'Vínculos del catálogo cuyo objeto no existe en la base (no se pueden crear aquí): {n}.',
        'none': 'Ninguno. ✅', 'more': '{n} más (ver JSON)', 'already': 'sí',
        'dir_how': ('Cómo leerlo: cada fila dice lo que hay HOY en la base y lo que dice el catálogo. Si el catálogo tiene razón, '
                    'dime OK; si la base tiene razón, corregimos el catálogo (nodes/*.js) y la fila desaparece de esta lista.'),
        'dir_req': 'REQUIEREN TU OK',
        'h_alias': ['Duplicado en la base', 'Nombre canónico', 'Vínculos vigentes', 'Acción'],
        'h_dup': ['Proveedor (source)', 'Cliente (target)', 'Relación', 'Peso', 'Copias', 'Se retractan'],
        'h_dir': ['Hoy en la base', 'Según el catálogo', 'Relación', 'Peso base → catálogo', 'Texto del catálogo', 'La correcta ya existe'],
        'h_var': ['Proveedor', 'Cliente', 'Relación', 'Peso en la base', 'Peso en el catálogo', 'Texto del catálogo'],
        'h_miss': ['Proveedor', 'Cliente', 'Relación', 'Peso', 'Texto del catálogo'],
        'h_extra': ['Proveedor', 'Cliente', 'Relación', 'Peso', 'Texto en la base'],
        'how': 'Cómo aplicar (cuando des el OK)',
        'steps': [
            '**Copia de seguridad primero.** Railway → tu proyecto → Postgres → pestaña *Backups* → *Create backup*.',
            '**Aplicar lo seguro** (duplicados de empresas + vínculos repetidos): en la app, 🩺 → Diagnóstico → '
            '*Grafo: base vs catálogo* → *Aplicar lo seguro* (pide tu PIN de operador).',
            '**Las demás categorías** (direcciones, pesos, faltantes, sobrantes) solo se aplican si las marcas a propósito.',
            '**Deshacer**: cada aplicación tiene un código (run). En el mismo panel, *Deshacer* lo revierte con eventos nuevos: '
            'nada se borra y la historia queda.',
        ],
        'cats': {
            'alias': ('Empresas duplicadas (alias)', 'La misma empresa aparece con dos nombres; el catálogo ya las unió. '
                      'Se retira el duplicado y sus vínculos pasan al nombre canónico, con su fecha.'),
            'duplicates': ('Vínculos repetidos exactos', 'La misma relación, con el mismo peso, está varias veces (cuenta doble '
                           'en el NRS). Se conserva la más antigua.'),
            'direction': ('Direcciones al revés', 'La base dice "A provee a B"; el catálogo dice "B provee a A". La regla es '
                          'ÚNICA: el primero PROVEE al segundo.'),
            'variants': ('Mismo vínculo, otro peso', 'La relación existe en ambos, con distinto peso (importancia 1-6).'),
            'missing': ('Faltan en la base', 'Están en el mapa pero no en la base: el motor de shocks y el NRS no los ven.'),
            'extra': ('Sobran en la base', 'Están en la base pero el catálogo ya no los tiene (se quitaron en la limpieza).'),
        },
    },
    'en': {
        'title': 'Graph review: catalog vs database (Postgres)',
        'meta': 'Generated: {as_of} · database: `{db}` · catalog exported: `{snap}` · mode: **read-only** — nothing has been changed.',
        'why': ('Why it matters: the map and the MCP tools read the CATALOG; the matrix engine, the server NRS and the Temporal '
                'Graph read the DATABASE. If they differ, the same shock gives different results depending on the screen.'),
        'summary': 'Summary', 'col_cat': 'Category', 'col_n': 'Count', 'col_fix': 'What the fix does',
        'col_default': 'Applied by "Apply the safe part"?', 'yes': '**Yes**', 'no': 'No — must be ticked',
        'counts': 'Database: {dbo} objects · {dbl} current links. Catalog: {cn} nodes · {cl} links. Not touched (out of scope): {oos}.',
        'objmiss': 'Catalog links whose object does not exist in the database (cannot be created here): {n}.',
        'none': 'None. ✅', 'more': '{n} more (see JSON)', 'already': 'yes',
        'dir_how': ('How to read it: each row shows what the database says TODAY and what the catalog says. If the catalog is '
                    'right, tell me OK; if the database is right, we fix the catalog (nodes/*.js) and the row disappears.'),
        'dir_req': 'NEED YOUR OK',
        'h_alias': ['Duplicate in the database', 'Canonical name', 'Current links', 'Action'],
        'h_dup': ['Supplier (source)', 'Customer (target)', 'Relation', 'Weight', 'Copies', 'Retracted'],
        'h_dir': ['Database today', 'Catalog says', 'Relation', 'Weight db → catalog', 'Catalog text', 'Correct one exists'],
        'h_var': ['Supplier', 'Customer', 'Relation', 'Weight in db', 'Weight in catalog', 'Catalog text'],
        'h_miss': ['Supplier', 'Customer', 'Relation', 'Weight', 'Catalog text'],
        'h_extra': ['Supplier', 'Customer', 'Relation', 'Weight', 'Database text'],
        'how': 'How to apply (once you approve)',
        'steps': [
            '**Backup first.** Railway → your project → Postgres → *Backups* tab → *Create backup*.',
            '**Apply the safe part** (duplicate companies + repeated links): in the app, 🩺 → Diagnostics → '
            '*Graph: database vs catalog* → *Apply the safe part* (asks for your operator PIN).',
            '**The other categories** (directions, weights, missing, extra) are applied only if you tick them on purpose.',
            '**Undo**: every run has a code. In the same panel, *Undo* reverts it with new events: nothing is deleted and '
            'the history stays.',
        ],
        'cats': {
            'alias': ('Duplicate companies (aliases)', 'The same company appears under two names; the catalog already merged '
                      'them. The duplicate is retired and its links move to the canonical name, keeping their date.'),
            'duplicates': ('Exact repeated links', 'The same relation with the same weight appears several times (double '
                           'counted in the NRS). The oldest one is kept.'),
            'direction': ('Reversed directions', 'The database says "A supplies B"; the catalog says "B supplies A". The rule '
                          'is SINGLE: the first one SUPPLIES the second.'),
            'variants': ('Same link, other weight', 'The relation exists in both, with a different weight (importance 1-6).'),
            'missing': ('Missing in the database', 'They are on the map but not in the database: the shock engine and the NRS '
                        'do not see them.'),
            'extra': ('Extra in the database', 'They are in the database but the catalog no longer has them (removed in the '
                      'clean-up).'),
        },
    },
}
_OOS = {'es': {'fecha_real': 'con fecha real', 'rel_fuera_del_catalogo': 'con relación fuera del catálogo',
               'fuente_externa': 'de fuente externa/factor', 'objeto_fuera_del_catalogo': 'con objetos que solo están en la base'},
        'en': {'fecha_real': 'with a real date', 'rel_fuera_del_catalogo': 'with a relation outside the catalog',
               'fuente_externa': 'from an external source/factor', 'objeto_fuera_del_catalogo': 'with objects only in the database'}}


def _cell(x):
    return str(x if x is not None else '').replace('|', '/').replace('\n', ' ')


def render_markdown(plan, dbname=None, limit_rows=80, lang='es'):
    T = _TXT['en' if lang == 'en' else 'es']
    oos_t = _OOS['en' if lang == 'en' else 'es']
    s = plan['summary']
    L = ['# ' + T['title'], '',
         T['meta'].format(as_of=plan['as_of'], db=dbname or '?', snap=plan['snapshot'].get('exported_at')), '',
         T['why'], '', '## ' + T['summary'], '',
         f"| {T['col_cat']} | {T['col_n']} | {T['col_fix']} | {T['col_default']} |", '|---|---:|---|---|']
    for k in CATEGORIES:
        name, what = T['cats'][k]
        L.append(f"| {name} | {s[k]} | {what} | {T['yes'] if k in DEFAULT_APPLY else T['no']} |")
    L.append('')
    oos = ', '.join(f'{v} {oos_t.get(k, k)}' for k, v in sorted(plan['out_of_scope'].items())) or '0'
    L.append(T['counts'].format(dbo=s['db_objects'], dbl=s['db_links_vigentes'], cn=s['catalog_nodes'],
                                cl=s['catalog_links'], oos=oos))
    if plan['objects_missing']:
        L.append(''); L.append(T['objmiss'].format(n=len(plan['objects_missing'])))
    L.append('')

    def table(headers, rows):
        if not rows:
            L.append(T['none']); L.append('')
            return
        L.append('| ' + ' | '.join(headers) + ' |')
        L.append('|' + '---|' * len(headers))
        for r in rows[:limit_rows]:
            L.append('| ' + ' | '.join(_cell(x) for x in r) + ' |')
        if len(rows) > limit_rows:
            cells = ['…', T['more'].format(n=len(rows) - limit_rows)] + [''] * (len(headers) - 2)
            L.append('| ' + ' | '.join(cells[:len(headers)]) + ' |')
        L.append('')

    def head(i, k, extra=''):
        L.append(f"## {i}. {T['cats'][k][0]} ({s[k]}){extra}"); L.append(T['cats'][k][1]); L.append('')

    head(1, 'alias')
    table(T['h_alias'], [(a['alias'], a['canonical'], a['links_vigentes'], a['action']) for a in plan['alias']])
    head(2, 'duplicates')
    table(T['h_dup'], [(d['source'], d['target'], d['rel'], d['weight'], d['copies'], len(d['retract_link_ids']))
                       for d in plan['duplicates']])
    head(3, 'direction', ' — ' + T['dir_req'])
    L.append(T['dir_how']); L.append('')
    by_hub = defaultdict(list)
    for d in plan['direction']:
        by_hub[d['hub']].append(d)
    if not by_hub:
        L.append(T['none']); L.append('')
    for hub, items in sorted(by_hub.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        L.append(f'### {hub} ({len(items)})'); L.append('')
        table(T['h_dir'], [(f"{d['db_source']} → {d['db_target']}", f"{d['catalog_source']} → {d['catalog_target']}", d['rel'],
                            f"{d['weight_db']} → {d['weight_catalog']}", (d['rel_label'] or '')[:90],
                            T['already'] if d['already_correct_in_db'] else '') for d in items])
    head(4, 'variants')
    table(T['h_var'], [(v['source'], v['target'], v['rel'], v['weight_db'], v['weight_catalog'], (v['rel_label'] or '')[:80])
                       for v in plan['variants']])
    head(5, 'missing')
    table(T['h_miss'], [(m['source'], m['target'], m['rel'], m['weight_catalog'], (m['rel_label'] or '')[:80])
                        for m in plan['missing']])
    head(6, 'extra')
    table(T['h_extra'], [(e['source'], e['target'], e['rel'], e['weight_db'], (e['rel_label_db'] or '')[:80])
                         for e in plan['extra']])
    L.append('## ' + T['how']); L.append('')
    for i, st in enumerate(T['steps'], 1):
        L.append(f'{i}. {st}')
    L.append('')
    return '\n'.join(L)


def markdown_to_html(md, title='Khipus'):
    """Conversor MÍNIMO y seguro (todo se escapa) para el informe: títulos,
    tablas, listas numeradas, párrafos, **negrita**, *cursiva* y `código`."""
    import html
    import re

    def inline(t):
        t = html.escape(t, quote=False)
        t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
        t = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', t)
        t = re.sub(r'(?<![*\w])\*([^*]+)\*(?!\*)', r'<i>\1</i>', t)
        return t

    out, lines, i = [], md.split('\n'), 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                rows.append(lines[i]); i += 1
            cells = [[c.strip() for c in r.strip().strip('|').split('|')] for r in rows if not re.match(r'^\|(-+:?\|)+$', r.replace(' ', ''))]
            if cells:
                out.append('<div class="tw"><table><thead><tr>' + ''.join(f'<th>{inline(c)}</th>' for c in cells[0]) + '</tr></thead><tbody>')
                for r in cells[1:]:
                    out.append('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in r) + '</tr>')
                out.append('</tbody></table></div>')
            continue
        m = re.match(r'^(#{1,3}) (.*)$', ln)
        if m:
            lv = len(m.group(1)); out.append(f'<h{lv}>{inline(m.group(2))}</h{lv}>'); i += 1; continue
        if re.match(r'^\d+\. ', ln):
            out.append('<ol>')
            while i < len(lines) and re.match(r'^\d+\. ', lines[i]):
                out.append('<li>' + inline(re.sub(r'^\d+\. ', '', lines[i])) + '</li>'); i += 1
            out.append('</ol>')
            continue
        if ln.strip():
            out.append(f'<p>{inline(ln)}</p>')
        i += 1
    css = ('body{font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;margin:0 auto;max-width:1100px;padding:16px;'
           'background:#0d1117;color:#e6edf3}h1{font-size:20px}h2{font-size:16px;margin-top:28px;border-bottom:1px solid #30363d;'
           'padding-bottom:4px}h3{font-size:14px;color:#9ecbff}.tw{overflow-x:auto}table{border-collapse:collapse;width:100%;'
           'font-size:12.5px;margin:6px 0 14px}th,td{border:1px solid #30363d;padding:4px 7px;text-align:left;vertical-align:top}'
           'th{background:#161b22}tr:nth-child(even) td{background:#11161d}code{background:#161b22;padding:1px 4px;'
           'border-radius:4px}@media (prefers-color-scheme:light){body{background:#fff;color:#1f2328}th{background:#f6f8fa}'
           'tr:nth-child(even) td{background:#fafbfc}code{background:#f6f8fa}th,td{border-color:#d0d7de}h3{color:#0550ae}}')
    return ('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{html.escape(title)}</title><style>{css}</style></head><body>' + '\n'.join(out) + '</body></html>')


# ───────────────────────── apply ─────────────────────────

def new_run_id():
    return _now().strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:6]


def _db_name(session):
    from sqlalchemy import text
    return session.execute(text('SELECT current_database()')).scalar()


def _check_confirm(session, confirm_db):
    name = _db_name(session)
    if not confirm_db or confirm_db != name:
        raise ReconcileError(f'--confirm-db debe ser exactamente el nombre de la base ({name!r}); nada se ha cambiado',
                             f'confirm_db must be exactly the database name ({name!r}); nothing was changed')
    return name


def _busy():
    return ReconcileError('otra reconciliación (aplicar o deshacer) está en curso; inténtalo en un minuto',
                          'another reconciliation (apply or undo) is running; try again in a minute')


def apply_plan(session_scope, snap, include=DEFAULT_APPLY, confirm_db=None, actor=ACTOR, run_id=None, log=None,
               expect=None):
    """Aplica por categoría, RE-CALCULANDO el plan antes de cada una (la
    fusión de alias cambia qué filas existen). Cada categoría en su propia
    transacción. Devuelve {run_id, applied: {cat: n}, events: n, plan_before}."""
    from sqlalchemy import text
    from ontology.db import _get_engine
    bad = [c for c in (include or ()) if c not in CATEGORIES]
    if bad:                         # G5: antes se filtraba primero y una errata se descartaba en silencio
        raise ReconcileError(f'categorías desconocidas: {bad}; válidas: {list(CATEGORIES)}',
                             f'unknown categories: {bad}; valid: {list(CATEGORIES)}')
    conn = _get_engine().connect()
    try:
        if not conn.execute(text('SELECT pg_try_advisory_lock(:k)'), {'k': LOCK_KEY}).scalar():
            raise _busy()
        try:
            return _apply_locked(session_scope, snap, include, confirm_db, actor, run_id, log, expect)
        finally:
            conn.execute(text('SELECT pg_advisory_unlock(:k)'), {'k': LOCK_KEY})
    finally:
        conn.close()


def _apply_locked(session_scope, snap, include, confirm_db, actor, run_id, log, expect):
    from ontology.actions import RetractarVinculoInput, FusionarEntidadInput, retractar_vinculo, fusionar_entidad
    from ontology.service import apply_event
    include = [c for c in (include or ()) if c in CATEGORIES]
    run_id = run_id or new_run_id()
    source = RUN_PREFIX + run_id
    log = log or (lambda *_: None)
    with session_scope() as s:
        dbname = _check_confirm(s, confirm_db)
        before = build_plan(s, snap)
    if expect:                      # G5: se aplica SOLO el plan que la persona revisó
        changed = {c: (expect.get(c), before['summary'][c]) for c in include
                   if c in expect and int(expect.get(c) or 0) != before['summary'][c]}
        if changed:
            raise ReconcileError(f'la lista cambió desde que la revisaste {changed}: vuelve a mirarla antes de aplicar',
                                 f'the list changed since you reviewed it {changed}: review it again before applying')
    applied, n_events, error = {}, 0, None
    order = [c for c in CATEGORIES if c in include]
    for cat in order:
      try:
        with session_scope() as s:
            plan = build_plan(s, snap)
            items = plan[cat]
            n = 0
            if cat == 'alias':
                for a in items:
                    if not a['canonical_in_db']:
                        continue
                    r = fusionar_entidad(s, FusionarEntidadInput(alias_id=a['alias'], canonical_id=a['canonical'],
                                                                   razon=f'reconciliación con el catálogo {snap.get("exported_at")} ({run_id})'),
                                         actor, source=source)
                    n += 1; n_events += 3 + 2 * r['links_moved'] + r['links_dropped']
            elif cat == 'duplicates':
                for d in items:
                    for lid in d['retract_link_ids']:
                        retractar_vinculo(s, RetractarVinculoInput(link_id=lid, razon=f'duplicado exacto ({run_id})'), actor,
                                          source=source)
                        n += 1; n_events += 2
            elif cat == 'direction':
                for d in items:
                    retractar_vinculo(s, RetractarVinculoInput(link_id=d['link_id'], razon=f'dirección invertida ({run_id})'), actor,
                                      source=source)
                    n_events += 2
                    if not d['already_correct_in_db']:
                        apply_event(s, 'LinkCreated', {'rel_type': d['rel'], 'weight': d['weight_catalog'],
                                                       'properties': {'rel_label': d['rel_label'], 'reconcile': 'direction',
                                                                      'from_link_id': d['link_id'], 'catalog_snapshot': snap.get('exported_at')}},
                                    valid_from=GENESIS, source=source, actor=actor,
                                    object_id=d['catalog_source'], target_id=d['catalog_target'])
                        n_events += 1
                    n += 1
            elif cat == 'variants':
                for v in items:
                    retractar_vinculo(s, RetractarVinculoInput(link_id=v['link_id'], razon=f'peso distinto al catálogo ({run_id})'), actor,
                                      source=source)
                    n_events += 2
                    if not v['catalog_row_exists']:
                        apply_event(s, 'LinkCreated', {'rel_type': v['rel'], 'weight': v['weight_catalog'],
                                                       'properties': {'rel_label': v['rel_label'], 'reconcile': 'variant',
                                                                      'from_link_id': v['link_id'], 'catalog_snapshot': snap.get('exported_at')}},
                                    valid_from=GENESIS, source=source, actor=actor,
                                    object_id=canon(snap['alias'], v['source']), target_id=canon(snap['alias'], v['target']))
                        n_events += 1
                    n += 1
            elif cat == 'missing':
                for m in items:
                    apply_event(s, 'LinkCreated', {'rel_type': m['rel'], 'weight': m['weight_catalog'],
                                                   'properties': {'rel_label': m['rel_label'], 'reconcile': 'missing',
                                                                  'catalog_snapshot': snap.get('exported_at')}},
                                valid_from=GENESIS, source=source, actor=actor, object_id=m['source'], target_id=m['target'])
                    n += 1; n_events += 1
            elif cat == 'extra':
                for e in items:
                    retractar_vinculo(s, RetractarVinculoInput(link_id=e['link_id'],
                                                               razon=f'superseded_by_snapshot_{snap.get("exported_at")} ({run_id})'),
                                      actor, source=source)
                    n += 1; n_events += 2
            applied[cat] = n
            log(f'{cat}: {n} aplicados')
      except Exception as e:  # noqa: BLE001 — G5: lo ya aplicado queda (y se puede deshacer); se informa el run_id
        error = {'category': cat, 'error': f'{type(e).__name__}: {str(e)[:300]}'}
        log(f'{cat}: ERROR {error["error"]}')
        break
    with session_scope() as s:
        after = build_plan(s, snap)
    out = {'run_id': run_id, 'db': dbname, 'include': order, 'applied': applied, 'events_estimated': n_events,
           'summary_before': before['summary'], 'summary_after': after['summary'], 'source_channel': source}
    if error:
        out['error'] = error
    return out


# ───────────────────────── rollback ─────────────────────────

def rollback_run(session, run_id, confirm_db=None, actor=ACTOR):
    """Deshace una corrida con NUEVOS eventos (canal reconcile_v0_rollback:<run_id>).
    No borra nada. No se puede deshacer un rollback (sería otra corrida)."""
    from sqlalchemy import text
    from ontology.service import apply_event
    _check_confirm(session, confirm_db)
    if not session.execute(text('SELECT pg_try_advisory_xact_lock(:k)'), {'k': LOCK_KEY}).scalar():
        raise _busy()               # G5: dos "deshacer" a la vez duplicaban miles de filas
    source = RUN_PREFIX + run_id
    evs = session.scalars(select(Event).where(Event.source == source).order_by(Event.recorded_at.desc())).all()
    if not evs:
        raise ReconcileError(f'no hay eventos de la corrida {run_id}', f'no events for run {run_id}')
    rb = ROLLBACK_PREFIX + run_id
    runs = list_runs(session, limit=500)
    rolled = {r['run_id'] for r in runs if r['rollback']}
    if run_id in rolled:
        raise ReconcileError(f'la corrida {run_id} ya fue deshecha', f'run {run_id} was already undone')
    mine = next((r for r in runs if r['run_id'] == run_id and not r['rollback']), None)
    later = [r['run_id'] for r in runs if not r['rollback'] and r['run_id'] not in rolled and r['run_id'] != run_id
             and mine and r['from'] and mine['to'] and r['from'] > mine['to']]
    if later:
        raise ReconcileError(f'primero deshaz las corridas posteriores (de la más nueva a la más vieja): {", ".join(later)}',
                             f'undo the later runs first (newest to oldest): {", ".join(later)}')
    done = {'links_reopened': 0, 'links_retracted': 0, 'merges_undone': 0, 'skipped': 0, 'skipped_closed_later': 0}
    run_end = max((e.recorded_at for e in evs if e.recorded_at), default=None)
    closed_later = set()            # G5: pares que alguien cerró DESPUÉS de la corrida → no se resucitan
    if run_end is not None:
        for e in session.scalars(select(Event).where(Event.event_type == EventType.LINK_REMOVED.value,
                                                     Event.recorded_at > run_end)).all():
            ep = e.payload or {}
            if str(e.source or '').startswith((RUN_PREFIX, ROLLBACK_PREFIX)):
                continue
            if (ep.get('properties') or {}).get('retracts_event_id'):
                continue
            closed_later.add((e.object_id, e.target_id, ep.get('rel_type') or ep.get('type')))
    now = _now()
    for ev in evs:
        p = ev.payload or {}
        props = p.get('properties') or {}
        if ev.event_type == EventType.LINK_REMOVED.value and props.get('retracts_event_id'):
            orig = session.get(Event, uuid.UUID(str(props['retracts_event_id'])))
            if orig is None or orig.source == source:
                done['skipped'] += 1        # G5: creado Y retractado en la misma corrida → efecto neto cero
                continue
            op = dict(orig.payload or {})
            orel = op.get('rel_type') or op.get('type') or 'supply'
            if (orig.object_id, orig.target_id, orel) in closed_later or (orig.object_id, orig.target_id, None) in closed_later:
                done['skipped_closed_later'] += 1
                continue
            oprops = {k: v for k, v in (op.get('properties') or {}).items() if k not in ('dedup_of', 'dedup_event_id')}
            oprops.update({'allow_duplicate': True, 'rollback_of': str(ev.id), 'rollback_run': run_id,
                           'restores_event_id': str(orig.id)})
            apply_event(session, 'LinkCreated', {'rel_type': op.get('rel_type') or op.get('type') or 'supply',
                                                 'weight': op.get('weight'), 'properties': oprops},
                        valid_from=orig.valid_from, source=rb, actor=actor, object_id=orig.object_id, target_id=orig.target_id)
            done['links_reopened'] += 1
        elif ev.event_type == EventType.LINK_CREATED.value:
            if props.get('dedup_of'):
                done['skipped'] += 1
                continue
            target = _current_incarnation(session, ev)
            if target is None:
                done['skipped'] += 1            # ya no está vigente (otra corrección lo cerró)
                continue
            tp = target.payload or {}
            apply_event(session, 'LinkRemoved', {'rel_type': tp.get('rel_type') or tp.get('type') or 'supply',
                                                 'properties': {'retracts_event_id': str(target.id), 'reason': f'rollback {run_id}',
                                                                'promote_dedups': True}},
                        valid_from=target.valid_from, source=rb, actor=actor, object_id=target.object_id,
                        target_id=target.target_id)
            done['links_retracted'] += 1
        elif ev.event_type == 'ActionExecuted' and p.get('action') == 'FusionarEntidad':
            alias_id, canonical_id = p.get('alias_id'), ev.object_id
            prev = p.get('prev_alias_props')          # G5: se restaura el estado EXACTO de antes de la fusión
            if not isinstance(prev, dict):
                prev = {'retired': False, 'merged_into': None, 'retired_razon': None}
            apply_event(session, 'ObjectUpdated', {'properties': {**{k: prev.get(k) for k in ('retired', 'merged_into', 'retired_razon')},
                                                                  'rollback_run': run_id}},
                        valid_from=now, source=rb, actor=actor, object_id=alias_id)
            canon_obj = session.get(ObjectRecord, canonical_id)
            if canon_obj is not None:
                aliases = p.get('prev_canon_aliases')
                if not isinstance(aliases, list):
                    aliases = [a for a in ((canon_obj.properties or {}).get('aliases') or []) if a != alias_id]
                apply_event(session, 'ObjectUpdated', {'properties': {'aliases': aliases}},
                            valid_from=now, source=rb, actor=actor, object_id=canonical_id)
            done['merges_undone'] += 1
        else:
            done['skipped'] += 1
    return {'run_id': run_id, 'rollback_channel': rb, **done, 'events_reverted': len(evs)}


def _current_incarnation(session, ev):
    """La creación VIGENTE que desciende de `ev`: si un rollback posterior la
    retractó y la re-abrió (LinkCreated con restores_event_id), seguir la
    cadena. None si ninguna está vigente."""
    chain, cur, seen = [ev], ev, {str(ev.id)}
    sib = session.scalars(select(Event).where(Event.event_type == EventType.LINK_CREATED.value,
                                              Event.object_id == ev.object_id, Event.target_id == ev.target_id)
                          .order_by(Event.recorded_at)).all()
    while True:
        nxt = [e for e in sib if ((e.payload or {}).get('properties') or {}).get('restores_event_id') == str(cur.id)
               and str(e.id) not in seen]
        if not nxt:
            break
        cur = nxt[-1]
        seen.add(str(cur.id))
        chain.append(cur)
    for c in reversed(chain):
        if session.scalars(select(LinkRecord).where(LinkRecord.event_id == c.id, LinkRecord.valid_to.is_(None))).first():
            return c
        if session.scalars(select(Event).where(Event.event_type == EventType.LINK_REMOVED.value,
                                               Event.object_id == c.object_id, Event.target_id == c.target_id)).first() is None:
            return c                       # fila heredada sin event_id y nunca retractada
    return None


def list_runs(session, limit=20):
    from sqlalchemy import func
    rows = session.execute(
        select(Event.source, func.count(), func.min(Event.recorded_at), func.max(Event.recorded_at))
        .where(Event.source.like(RUN_PREFIX + '%') | Event.source.like(ROLLBACK_PREFIX + '%'))
        .group_by(Event.source).order_by(func.max(Event.recorded_at).desc()).limit(limit)).all()
    return [{'channel': r[0], 'run_id': r[0].split(':', 1)[1], 'rollback': r[0].startswith(ROLLBACK_PREFIX),
             'events': int(r[1]), 'from': r[2].isoformat() if r[2] else None, 'to': r[3].isoformat() if r[3] else None} for r in rows]
