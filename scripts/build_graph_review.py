#!/usr/bin/env python3
"""scripts/build_graph_review.py — LISTAS DE REVISIÓN DEL GRAFO para Fabrizio (BRECHAS_V2 bloque 5; decisiones #6 #7 #8 #10).

    python scripts/build_graph_review.py           # reescribe docs/REVISION_GRAFO.md y docs/revision_grafo.json
    python scripts/build_graph_review.py --check   # ¿están al día? (código 1 si no)
    python scripts/build_graph_review.py --db      # + resumen EN VIVO del plan de reconciliación (SOLO lectura;
                                                   #   necesita DATABASE_URL; se imprime, no se guarda en el documento)

NADA del grafo cambia aquí: el script lee el catálogo (data/grafo_v0.json + el origen de cada fila vía
scripts/link_origins.js), PROPONE y escribe dos archivos. Determinista: sin red, sin IA, sin base (salvo --db, que abre
una transacción READ ONLY). El JSON (`graph-review/1`) es el insumo de un paso futuro que aplicará como ACCIONES de
ontología (RetractarVinculo / ProponerVinculo / CorregirDato, canal `review_grafo:<id>`) SOLO lo que Fabrizio marque ✔.

Secciones (L3-02, L3-12, L3-11/PROP-14, L3-03, L3-04, L3-09):
  (a) los 27 vínculos FECHADOS que la migración guarda como 'supply' sin peso → tipo y dirección propuestos
  (b) direcciones contrarias al texto (scripts/audit_graph.py `text_direction`, la misma regla con trinquete)
  (c) escala de pesos única [0,1]: regla por fila (1-6 → w/6; 0-1 se queda; "peso = criticidad del tipo" = peso
      desconocido → el típico de su tipo) con los 462 vínculos de peso 1 uno por uno
  (d) verbos en español fuera del vocabulario (los 58 hechos que la puerta SHACL `link.rel_in_vocab` marca) y los 12
      márgenes fuera de [-1, 1] (`object.margin_range`)
  (e) los 200 vínculos de flujo más pesados SIN fecha real (para fechar CON FUENTE; ninguna fecha inventada)
  (f) reconciliación catálogo ↔ Postgres (decisión #7): qué compara, qué aplica por defecto y dónde verla en vivo
"""
import argparse
import collections
import json
import os
import re
import statistics
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts import audit_graph as AG  # noqa: E402

SNAPSHOT = os.path.join(ROOT, 'data', 'grafo_v0.json')
OUT_MD = os.path.join(ROOT, 'docs', 'REVISION_GRAFO.md')
OUT_JSON = os.path.join(ROOT, 'docs', 'revision_grafo.json')
FORMAT = 'graph-review/1'
GENESIS = '2000-01-01'
N_HEAVIEST = 200
FACT_FILES = ('nodes/temporal_seed_facts.js', 'nodes/temporal_seed_facts2.js', 'nodes/ontology_facts.js')
ARRAY_FILES = {
    'RAW_LINKS': 'nodes/nodes_seed.js', 'LINKS_EXPAND': 'nodes/links_expand.js', 'LINKS_SPACEX': 'nodes/links_all.js',
    'LINKS_CONNECT': 'nodes/links_connect.js', 'LINKS_NUCLEAR': 'nodes/nodes_nuclear.js',
    'LINKS_EXPAND4': 'nodes/nodes_expand4.js', 'LINKS_EXPAND5': 'nodes/nodes_expand5.js',
    'LINKS_CHINA': 'nodes/nodes_china.js', 'LINKS_MULTICAPA': 'nodes/nodes_multicapa.js',
}
# el único arreglo escrito en escala 0-1 (los demás: 1-6). Un peso >1 dentro de él es 1-6 (24 filas).
ZERO_ONE_ARRAYS = frozenset({'LINKS_EXPAND5'})

TYPE_ES = {'supply': 'provee a', 'fab': 'fabrica para', 'cloud': 'da nube a', 'license': 'licencia a',
           'partner': 'socio de', 'invest': 'invierte en', 'deploy': 'despliega', 'owns': 'es dueño de',
           'ppa': 'da energía a', 'affects': 'afecta a', 'about': 'trata sobre (no mueve números)'}

# ── (a) reglas por TEXTO del predicado de los hechos fechados (orden = prioridad) ──────────────────────────────────
# orient: 'as_written' (sujeto → objeto) · 'inverted' (objeto → sujeto) · 'energy' (el extremo de energía provee)
#         · 'event' (no es un vínculo: es un suceso; se propone retirar la copia)
DATED_RULES = (
    ('event_loss', re.compile(r'perdi[óo] ingresos', re.I), None, 'event',
     'Es un SUCESO (la pérdida de ventas por el veto), no una relación vigente: ya lo cuenta la noticia del hecho.'),
    ('invest', re.compile(r'invi(?:erte|rti[óo])|respalda|lidera la financiaci[óo]n', re.I), 'invest', 'as_written',
     'Es una inversión (dinero), no suministro. Por defecto (BRECHAS #4) la inversión NO transmite daño.'),
    ('ppa', re.compile(r'\bPPA\b|reabre .*\bpara\b', re.I), 'ppa', 'energy',
     'Contrato de energía: la flecha va de quien GENERA la energía a quien la consume.'),
    ('gpus_de', re.compile(r'GPUs? de\s*$', re.I), 'supply', 'inverted',
     '"X: GPUs de Y" quiere decir que Y le VENDE las GPUs a X: la flecha va al revés.'),
    ('stargate_cloud', re.compile(r'stargate.*\bcon\s*$', re.I), 'cloud', 'inverted',
     'En Stargate, Oracle construye y opera la infraestructura de cómputo para OpenAI: Oracle → OpenAI (nube).'),
    ('fab', re.compile(r'^fabrica\b', re.I), 'fab', 'as_written', 'Fabricación por encargo.'),
    ('co_design', re.compile(r'co-?diseña', re.I), 'supply', 'as_written',
     'Diseña el chip a medida para el cliente (servicio de diseño + venta del chip).'),
    ('supply', re.compile(r'\bpara\b|\bcon\s*$|componentes', re.I), 'supply', 'as_written',
     'Venta de un producto o servicio al cliente.'),
)

# ── (d) verbos en español fuera del vocabulario → propuesta (dato curado, no IA) ──────────────────────────────────
VERB_MAP = {
    'fabrica': {'type': 'about', 'orient': 'as_written', 'company_type': 'fab',
                'es': 'Empresa que produce una tecnología/material (EUV, HBM3e…). Entre empresas sería "fab"; '
                      'hacia un CONCEPTO queda como dato descriptivo que no mueve números.'},
    'usa': {'type': 'about', 'orient': 'as_written', 'company_type': 'supply', 'company_orient': 'inverted',
            'es': 'Empresa que usa una tecnología. Entre dos empresas sería "supply" AL REVÉS (quien usa es el cliente).'},
    'depende': {'type': 'about', 'orient': 'as_written', 'company_type': 'supply', 'company_orient': 'inverted',
                'es': 'Dependencia de una tecnología/material: igual que "usa".'},
    'controla': {'type': 'about', 'orient': 'as_written', 'question': True,
                 'es': '¿Qué significa "controla"? (a) es DUEÑA (Nvidia → CUDA): sería "owns"; (b) REGULA (BIS → '
                       'Entity List) o (c) tiene la mayor parte del mercado (China → tierras raras): descriptivo. '
                       'Propuesta: descriptivo (no mueve números) hasta que elijas.'},
    'restringe': {'type': 'affects', 'orient': 'as_written',
                  'es': 'Una política que restringe a alguien: "afecta a" (como los Factores; no es suministro).'},
    'sanciona': {'type': 'affects', 'orient': 'as_written', 'es': 'Sanción: "afecta a" (como los Factores).'},
    'alberga': {'type': 'about', 'orient': 'as_written', 'question': True,
                'es': '¿"Alberga" = el país donde está la empresa? Propuesta: es UBICACIÓN (dato del país de la '
                      'empresa), no un vínculo que transmita daño. El riesgo país ya lo llevan los Factores.'},
    'domina': {'type': 'about', 'orient': 'as_written', 'question': True,
               'es': '¿"Domina" = tiene la mayor cuota del mercado de esa tecnología (TSMC → 2 nm)? Propuesta: '
                     'descriptivo (no mueve números).'},
    'energiza': {'type': 'ppa', 'orient': 'as_written', 'es': 'Da energía a: es exactamente "ppa".'},
    'invierte': {'type': 'invest', 'orient': 'as_written',
                 'es': 'Invierte en: "invest" (por defecto no transmite daño, BRECHAS #4).'},
    'compite': {'type': 'about', 'orient': 'as_written',
                'es': 'Competir no es suministrar: queda descriptivo (los rivales ya se calculan aparte).'},
}

UNIFORM_MIN = 10          # (c) un mismo valor 0-1 en ≥ 10 vínculos…
UNIFORM_SHARE = 0.9       # …y en ≥ 90 % de los vínculos 0-1 de su tipo = constante copiada, no un peso medido
MARGIN_PCT_MAX = 100.0     # un margen > 1 hasta 100 casi seguro se escribió en % (20,25 → 0,2025)


# ── utilidades ───────────────────────────────────────────────────────────────────────────────────────────────────
def _n(x, d=2):
    """Número en formato español (coma decimal) sin ceros de más."""
    if x is None:
        return '—'
    if isinstance(x, float) and x.is_integer():
        x = int(x)
    if isinstance(x, int):
        return f'{x:,}'.replace(',', '.')
    s = f'{x:.{d}f}'.rstrip('0').rstrip('.')
    return s.replace('.', ',')


def _cell(s):
    return str(s or '').replace('|', '/').replace('\n', ' ').strip()


def _arrow(s, t):
    return f'{s} → {t}'


def load_snapshot(path=SNAPSHOT):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def load_origins():
    """[s, t, type, w, arreglo] por fila CRUDA del catálogo (scripts/link_origins.js, mismo cargador que el export)."""
    try:
        out = subprocess.run(['node', os.path.join(ROOT, 'scripts', 'link_origins.js')], cwd=ROOT,
                             capture_output=True, text=True, timeout=120, check=True)
    except FileNotFoundError as e:
        raise RuntimeError('hace falta Node.js (node) para leer el origen de cada vínculo') from e
    return json.loads(out.stdout)


def _fact_files(root=ROOT):
    texts = {}
    for f in FACT_FILES:
        try:
            with open(os.path.join(root, f), encoding='utf-8') as fh:
                texts[f] = fh.read()
        except OSError:
            texts[f] = ''
    return texts


def _fact_file_of(fid, texts):
    for f, txt in texts.items():
        if f"'{fid}'" in txt or f'"{fid}"' in txt:
            return f
    return None


def _is_energy(node):
    node = node or {}
    return node.get('sector') == 'energia' or bool(re.search(r'power|utilit|nuclear|energ|fusion|smr',
                                                             node.get('cat') or '', re.I))


# ── (c) escala de pesos ──────────────────────────────────────────────────────────────────────────────────────────
def weight_proposals(links, origins, vocab):
    """Una propuesta en [0,1] por vínculo del snapshot. Reglas (L3-11 + PROP-14):
      scale_1_6     → w/6 (todo arreglo salvo LINKS_EXPAND5, y los w>1 de LINKS_EXPAND5)
      placeholder   → LINKS_EXPAND5 con w == criticidad de su tipo (no es un peso: es la criticidad copiada, que el
                      motor vuelve a multiplicar) → peso desconocido → el TÍPICO de su tipo (mediana 1-6) / 6
      scale_0_1     → LINKS_EXPAND5 con w ≤ 1 distinto de la criticidad → se queda igual
      ambiguous     → la misma tripla con el mismo peso en un arreglo 0-1 y en uno 1-6 → se muestran las dos opciones.
    Revisión (PROP-14): un MISMO número en (casi) todos los vínculos 0-1 de un tipo (license 0,8 ×17) tampoco es un
    peso medido → 'placeholder' con placeholder_kind='uniform_constant' (y una pregunta propia en el documento)."""
    crit = vocab.get('criticality') or {}
    by_key = collections.defaultdict(list)
    for s, t, ty, w, arr in origins['rows']:
        by_key[(s, t, ty)].append((float(w), arr))
    typical = {}
    groups = collections.defaultdict(list)
    for l in links:
        if float(l['w']) > 1:
            groups[l.get('type') or 'supply'].append(float(l['w']))
    for ty, ws in groups.items():
        typical[ty] = float(statistics.median(ws))
    zo_vals = collections.defaultdict(collections.Counter)      # valores 0-1 por tipo (solo arreglos 0-1)
    for (_s, _t, ty), lst in by_key.items():
        for ww, a in lst:
            if a in ZERO_ONE_ARRAYS and ww <= 1:
                zo_vals[ty][ww] += 1
    uniform = {}
    for ty, cnt in zo_vals.items():
        v, n = cnt.most_common(1)[0]
        if n >= UNIFORM_MIN and n >= UNIFORM_SHARE * sum(cnt.values()) and abs(v - float(crit.get(ty, -1))) > 1e-9:
            uniform[ty] = v
    out = []
    for l in links:
        ty = l.get('type') or 'supply'
        w = float(l['w'])
        arrs = sorted({a for ww, a in by_key.get((l['source'], l['target'], ty), []) if ww == w})
        zero_one = [a for a in arrs if a in ZERO_ONE_ARRAYS]
        one_six = [a for a in arrs if a not in ZERO_ONE_ARRAYS]
        typ = typical.get(ty, 2.0)
        if w > 1 or not zero_one:
            rule, w01 = 'scale_1_6', round(w / 6.0, 4)
        elif one_six:
            rule, w01 = 'ambiguous', round(w / 6.0, 4)
        elif abs(w - float(crit.get(ty, -1))) < 1e-9:
            rule, w01 = 'placeholder', round(typ / 6.0, 4)
        elif ty in uniform and abs(w - uniform[ty]) < 1e-9:
            rule, w01 = 'placeholder', round(typ / 6.0, 4)
        else:
            rule, w01 = 'scale_0_1', round(w, 4)
        pkind = None
        if rule == 'placeholder':
            pkind = 'criticality' if abs(w - float(crit.get(ty, -1))) < 1e-9 else 'uniform_constant'
        out.append({'source': l['source'], 'target': l['target'], 'type': ty, 'w': l['w'], 'conf': l.get('conf', 1),
                    'rel': l.get('rel') or '', 'since': l.get('since'), 'arrays': arrs,
                    'files': sorted({ARRAY_FILES.get(a, a) for a in arrs}), 'rule': rule, 'placeholder_kind': pkind,
                    'w01': w01,
                    'alt_w01': (round(w, 4) if rule == 'ambiguous' else None), 'typical_1_6': typ})
    return out


# ── construcción de la revisión ──────────────────────────────────────────────────────────────────────────────────
def build(snap, origins, vocab=None, fact_texts=None):
    vocab = vocab or AG.load_vocab()
    fact_texts = fact_texts if fact_texts is not None else _fact_files()
    nodes = snap.get('nodes') or []
    links = snap.get('links') or []
    by_id = {n['id']: n for n in nodes}
    onto_objs = {o['id']: o for o in ((snap.get('ontology') or {}).get('objects') or [])}
    known = set(by_id) | set(onto_objs)
    flow = set(vocab.get('flow') or ())
    rel_types = set(vocab.get('rel_types') or ())
    crit = vocab.get('criticality') or {}
    triples = {(l['source'], l['target'], l.get('type') or 'supply'): l for l in links}
    pair_links = collections.defaultdict(list)
    for l in links:
        pair_links[frozenset((l['source'], l['target']))].append(l)

    def ctx_links(a, b):
        return [{'source': l['source'], 'target': l['target'], 'type': l.get('type') or 'supply', 'w': l['w']}
                for l in sorted(pair_links.get(frozenset((a, b)), []), key=lambda x: (x['source'], x['type']))]

    weights = weight_proposals(links, origins, vocab)
    w_by_key = {(x['source'], x['target'], x['type']): x for x in weights}
    typical = {x['type']: x['typical_1_6'] for x in weights}

    # (a) hechos fechados que la migración guarda como 'supply' sin peso (scripts/migrate_v0_to_ontology.py) ─────────
    facts = snap.get('temporal_facts') or []
    dated = []
    for f in facts:
        if f.get('object_type') != 'node' or f.get('rel'):
            continue
        subj, obj = f.get('subject'), f.get('object')
        if subj not in known or obj not in known or subj == obj:
            continue                                   # la migración lo salta: no entra al motor
        pred = f.get('predicate') or ''
        rule = next((r for r in DATED_RULES if r[1].search(pred)), None)
        rid, ty, orient, why = (rule[0], rule[2], rule[3], rule[4]) if rule else ('unmatched', None, 'review',
                                                                                 'Sin regla: revisar a mano.')
        if orient == 'energy':
            if _is_energy(by_id.get(subj)):
                orient = 'as_written'
            elif _is_energy(by_id.get(obj)):
                orient = 'inverted'
            else:
                orient = 'as_written'
        if orient == 'event':
            ps, pt = None, None
        elif orient == 'inverted':
            ps, pt = obj, subj
        else:
            ps, pt = subj, obj
        item = {'id': f"a-{f['id']}", 'fact_id': f['id'], 'fact_file': _fact_file_of(f['id'], fact_texts),
                'subject': subj, 'object': obj, 'predicate': pred, 'valid_from': f.get('valid_from'),
                'valid_until': f.get('valid_until'), 'headline': (f.get('meta') or {}).get('headline') or '',
                'today': {'rel_type': 'supply', 'weight': None,
                          'note': "la migración usa 'supply' sin peso → el motor le pone peso 2"},
                'rule': rid, 'why': why, 'mark': None}
        retract = {'action': 'RetractarVinculo',
                   'match': {'source': subj, 'target': obj, 'rel_type': 'supply', 'valid_from': f.get('valid_from'),
                             'channel': 'migration_v0_temporal'},
                   'razon': f"review_grafo {item['id']}: hecho fechado migrado como 'supply' por defecto (L3-02)"}
        if ps is None:
            item['proposal'] = {'kind': 'retract', 'type': None}
            item['actions'] = [retract]
            item['catalog_edits'] = [{'file': item['fact_file'], 'fact_id': f['id'], 'set': {'rel': 'about'}}]
        else:
            existing = triples.get((ps, pt, ty))
            item['proposal'] = {'kind': 'date_existing' if existing else 'create', 'type': ty, 'source': ps,
                                'target': pt, 'inverted': ps != subj,
                                'weight_1_6': (existing['w'] if existing else typical.get(ty, 2.0))}
            meta = {'valid_from': f.get('valid_from'), 'valid_to': f.get('valid_until'), 'temporal_fact_id': f['id'],
                    'weight': item['proposal']['weight_1_6']}
            item['actions'] = [retract, {'action': 'ProponerVinculo',
                                         'input': {'from_id': ps, 'to_id': pt, 'tipo': ty, 'metadata': meta,
                                                   'fuente': f"temporal_seed_facts:{f['id']}"},
                                         'note': ('misma tripla que el catálogo: el vínculo pasa a tener esta FECHA '
                                                  'real (since) en vez de "desde que se rastrea"'
                                                  if existing else 'vínculo nuevo con la fecha del hecho')}]
            item['catalog_edits'] = [{'file': item['fact_file'], 'fact_id': f['id'],
                                      'set': {'rel': ty, 'subject': ps, 'object': pt}}]
            if existing:
                item['catalog_edits'].append({'files': (w_by_key.get((ps, pt, ty)) or {}).get('files') or [],
                                              'link': [ps, pt, ty], 'set': {'since': f.get('valid_from')}})
        item['catalog_context'] = ctx_links(subj, obj)
        dated.append(item)

    # (b) direcciones contrarias al texto (la MISMA regla del trinquete de scripts/audit_graph.py) ────────────────
    audit = AG.audit_snapshot(snap, vocab)
    old32 = set()
    for x in audit['findings']['suspicious_directions']:
        old32.add((x['source'], x['target'], x['type']))
        if x.get('reason') == 'bidirectional_same_type':
            old32.add((x['target'], x['source'], x['type']))
    directions = []
    for i, x in enumerate(audit['findings']['text_direction'], 1):
        s, t, ty = x['source'], x['target'], x['type']
        new_ty = x.get('proposed_type') or ty
        # el vínculo al revés puede existir con el tipo NUEVO (b-02: Amazon → Palantir 'cloud' ya está): invertir
        # crearía un duplicado con otro peso → se propone solo retirar el equivocado
        reverse_type = ty if (t, s, ty) in triples else (new_ty if (t, s, new_ty) in triples else None)
        reverse_exists = reverse_type is not None
        if x['proposal'] == 'invert':
            kind = 'retract_reverse_exists' if reverse_exists else 'invert'
        else:
            kind = 'retract'
        wl = w_by_key.get((s, t, ty)) or {}
        actions = [{'action': 'RetractarVinculo', 'match': {'source': s, 'target': t, 'rel_type': ty,
                                                            'valid_from': GENESIS},
                    'razon': f'review_grafo b-{i:02d}: el texto dice lo contrario de la flecha (L3-12)'}]
        if kind == 'invert':
            actions.append({'action': 'ProponerVinculo', 'input': {'from_id': t, 'to_id': s, 'tipo': new_ty,
                                                                   'metadata': {'weight': x['w'], 'rel_label': x['rel']},
                                                                   'fuente': 'review_grafo:texto'}})
        directions.append({'id': f'b-{i:02d}', 'source': s, 'target': t, 'type': ty, 'new_type': new_ty,
                           'w': x['w'], 'rel': x['rel'],
                           'reason': x['reason'], 'verb': x['verb'], 'proposal': kind,
                           'in_audit_32': (s, t, ty) in old32, 'reverse_exists': reverse_exists,
                           'reverse_type': reverse_type,
                           'files': wl.get('files') or [], 'actions': actions, 'mark': None})

    # (c) pesos ───────────────────────────────────────────────────────────────────────────────────────────────────
    per_type = collections.OrderedDict()
    for ty in sorted({x['type'] for x in weights}):
        xs = [x for x in weights if x['type'] == ty]
        per_type[ty] = {'n': len(xs), 'lt1': sum(1 for x in xs if float(x['w']) < 1),
                        'eq1': sum(1 for x in xs if float(x['w']) == 1),
                        'gt1': sum(1 for x in xs if float(x['w']) > 1),
                        'placeholder': sum(1 for x in xs if x['rule'] == 'placeholder'),
                        'criticality': crit.get(ty), 'typical_1_6': typical.get(ty)}
    incoming = collections.Counter((l['target'], l.get('type') or 'supply') for l in links)
    eq1 = [x for x in weights if float(x['w']) == 1]
    lt1 = [x for x in weights if float(x['w']) < 1]
    sole = [x for x in lt1 if x['type'] in flow and incoming[(x['target'], x['type'])] == 1]
    weight_items = []
    for x in sorted(eq1 + lt1, key=lambda x: (x['rule'], x['type'], x['source'], x['target'])):
        weight_items.append({'source': x['source'], 'target': x['target'], 'type': x['type'], 'w': x['w'],
                             'rule': x['rule'], 'placeholder_kind': x['placeholder_kind'], 'w01': x['w01'],
                             'alt_w01': x['alt_w01'], 'files': x['files'],
                             'sole_supplier': x in sole})

    # (d) verbos fuera del vocabulario + márgenes ──────────────────────────────────────────────────────────────
    verbs = []
    for f in facts:
        rel = f.get('rel')
        if f.get('object_type') != 'node' or not rel or rel in rel_types:
            continue
        subj, obj = f.get('subject'), f.get('object')
        m = VERB_MAP.get(rel) or {'type': None, 'orient': 'review', 'es': 'Sin propuesta: revisar.'}
        both_companies = subj in by_id and obj in by_id
        ty = m.get('company_type') if (both_companies and m.get('company_type')) else m['type']
        orient = m.get('company_orient', 'as_written') if (both_companies and m.get('company_type')) else m['orient']
        ps, pt = (obj, subj) if orient == 'inverted' else (subj, obj)
        # revisión: la migración YA guardó este hecho en Postgres con el verbo como rel_type ('fabrica', 'usa'…;
        # scripts/migrate_v0_to_ontology.py, canal migration_v0_temporal) → con la marca, se retira ESE vínculo y,
        # si la propuesta es un tipo que relaciona (no 'about' descriptivo), se propone el bueno con su fecha.
        # Igual que (a). Sin esto, ✔ cambiaba el catálogo y la base seguía con el verbo fuera del vocabulario.
        actions = []
        if subj in known and obj in known and subj != obj:
            actions.append({'action': 'RetractarVinculo',
                            'match': {'source': subj, 'target': obj, 'rel_type': rel, 'valid_from': f.get('valid_from'),
                                      'channel': 'migration_v0_temporal'},
                            'razon': f"review_grafo d-{f['id']}: verbo '{rel}' fuera del vocabulario (L3-03)"})
            if ty and ty != 'about':
                actions.append({'action': 'ProponerVinculo',
                                'input': {'from_id': ps, 'to_id': pt, 'tipo': ty,
                                          'metadata': {'valid_from': f.get('valid_from'),
                                                       'valid_to': f.get('valid_until'), 'temporal_fact_id': f['id'],
                                                       'verb': rel},
                                          'fuente': f"temporal_seed_facts:{f['id']}"},
                                'note': f"'{rel}' → '{ty}' con la fecha del hecho"})
        verbs.append({'id': f"d-{f['id']}", 'fact_id': f['id'], 'fact_file': _fact_file_of(f['id'], fact_texts),
                      'verb': rel, 'subject': subj, 'object': obj, 'valid_from': f.get('valid_from'),
                      'subject_kind': 'empresa' if subj in by_id else (onto_objs.get(subj) or {}).get('type'),
                      'object_kind': 'empresa' if obj in by_id else (onto_objs.get(obj) or {}).get('type'),
                      'proposal': {'type': ty, 'source': ps, 'target': pt, 'flow': ty in flow,
                                   'question': bool(m.get('question'))},
                      'catalog_edits': [{'file': _fact_file_of(f['id'], fact_texts), 'fact_id': f['id'],
                                         'set': {'rel': ty, 'subject': ps, 'object': pt, 'verb': rel}}],
                      'actions': actions, 'mark': None})
    verb_table = collections.OrderedDict()
    for v in sorted(VERB_MAP, key=lambda k: (-sum(1 for x in verbs if x['verb'] == k), k)):
        xs = [x for x in verbs if x['verb'] == v]
        if xs:
            verb_table[v] = {'n': len(xs), 'type': VERB_MAP[v]['type'], 'company_type': VERB_MAP[v].get('company_type'),
                             'question': bool(VERB_MAP[v].get('question')), 'es': VERB_MAP[v]['es'], 'mark': None}
    margins = []
    for n in nodes:
        m = n.get('margin')
        if isinstance(m, bool) or not isinstance(m, (int, float)) or -1 <= m <= 1:
            continue
        if 1 < m <= MARGIN_PCT_MAX:
            prop = {'kind': 'percent_to_fraction', 'value': round(m / 100.0, 6),
                    'es': f'Parece escrito en %: {_n(m)} → {_n(m / 100.0, 4)}.'}
        else:
            prop = {'kind': 'keep_and_widen_rule', 'value': m,
                    'es': (f'Margen de {_n(m * 100, 0)} %: posible en una empresa que pierde más de lo que vende. '
                           'Propuesta: NO tocar el dato y ampliar la regla a [-10, 1] en la próxima versión de las '
                           'formas (ontology.shapes).')}
        margins.append({'id': f"d-margin-{n['id']}", 'node': n['id'], 'label': n.get('label'), 'margin': m,
                        'proposal': prop,
                        'actions': ([{'action': 'CorregirDato', 'input': {'object_id': n['id'], 'campo': 'margin',
                                                                          'valor_nuevo': prop['value'],
                                                                          'fuente': 'review_grafo:margen_en_porcentaje'}}]
                                    if prop['kind'] == 'percent_to_fraction' else []),
                        'mark': None})

    # (e) los vínculos de flujo más pesados SIN fecha real ─────────────────────────────────────────────────────
    # pista = un hecho fechado del catálogo cuya propuesta de (a) es EXACTAMENTE este vínculo (misma tripla)
    dated_hint = collections.defaultdict(list)
    for d in dated:
        p = d['proposal']
        if p.get('type') and d.get('valid_from') and d['valid_from'] != GENESIS:
            dated_hint[(p['source'], p['target'], p['type'])].append(
                {'id': d['fact_id'], 'valid_from': d['valid_from'], 'predicate': d['predicate']})
    cands = [x for x in weights if x['type'] in flow and not x['since']]
    fdeg = collections.Counter()                   # grado de FLUJO (pares distintos), desempate: lo más conectado primero
    for a, b in {(x['source'], x['target']) for x in cands}:
        fdeg[a] += 1
        fdeg[b] += 1
    cands.sort(key=lambda x: (-(x['w01'] * float(crit.get(x['type'], 0) or 0) * float(x['conf'] or 0)),
                              -(fdeg[x['source']] + fdeg[x['target']]), x['source'], x['target'], x['type']))
    heaviest = []
    for i, x in enumerate(cands[:N_HEAVIEST], 1):
        hints = sorted(dated_hint.get((x['source'], x['target'], x['type']), []), key=lambda f: (f['valid_from'], f['id']))
        heaviest.append({'id': f'e-{i:03d}', 'source': x['source'], 'target': x['target'], 'type': x['type'],
                         'w': x['w'], 'w01': x['w01'], 'conf': x['conf'],
                         'strength': round(x['w01'] * float(crit.get(x['type'], 0) or 0) * float(x['conf'] or 0), 4),
                         'catalog_hint': [{'fact_id': f['id'], 'valid_from': f['valid_from'],
                                           'predicate': f.get('predicate')} for f in hints],
                         'proposed_since': None, 'source_url': None, 'mark': None})

    # (f) reconciliación ─────────────────────────────────────────────────────────────────────────────────────────
    reconcile = {
        'decision': 7, 'recommended': 'postgres_is_truth',
        'categories': {
            'alias': 'empresa duplicada que el catálogo ya fusionó → FusionarEntidad (se aplica por defecto)',
            'duplicates': 'misma relación repetida con el mismo peso → se retira la copia (se aplica por defecto)',
            'direction': 'X→Y en la base pero Y→X en el catálogo → SOLO con tu marca',
            'variants': 'misma relación con otro peso → SOLO con tu marca',
            'missing': 'está en el catálogo y falta en la base → SOLO con tu marca',
            'extra': 'está en la base y no en el catálogo → SOLO con tu marca',
        },
        'default_apply': ['alias', 'duplicates'],
        'catalog': {'nodes': len(nodes), 'links': len(links), 'aliases': len(snap.get('node_id_alias') or {}),
                    'temporal_facts': len(facts), 'exported_at': snap.get('exported_at')},
        'where': {'ui': '🩺 → Diagnóstico → tarjeta «Grafo: base vs catálogo» → «📄 Ver lista completa»',
                  'api': 'GET /api/ontology/reconcile/plan',
                  'terminal': 'python scripts/reconcile_v0_to_ontology.py',
                  'this_script': 'python scripts/build_graph_review.py --db'},
    }

    review = {
        'format': FORMAT,
        'snapshot': {'exported_at': snap.get('exported_at'), 'nodes': len(nodes), 'links': len(links)},
        'apply': {'status': 'pending_marks', 'channel': 'review_grafo:<id>',
                  'note': 'Nada se aplicó. Un paso futuro aplicará SOLO los ítems con mark=true como acciones de '
                          'ontología (con PIN de operador) y como ediciones del catálogo + export.'},
        'counts': {'dated_links': len(dated), 'text_directions': len(directions),
                   'text_directions_new': sum(1 for d in directions if not d['in_audit_32']),
                   'weights_eq1': len(eq1), 'weights_lt1': len(lt1), 'weights_placeholder':
                       sum(1 for x in weights if x['rule'] == 'placeholder'),
                   'weights_sole_lt1_flow': len(sole), 'off_vocab_facts': len(verbs), 'margins_out_of_range': len(margins),
                   'heaviest_undated': len(heaviest),
                   'heaviest_with_catalog_hint': sum(1 for h in heaviest if h['catalog_hint'])},
        'a_dated_links': dated,
        'b_text_directions': directions,
        'c_weights': {'rules': {
            'scale_1_6': 'w/6 (escala 1-6)',
            'placeholder': 'peso = criticidad del tipo copiada (no es un peso) → típico del tipo (mediana 1-6) / 6',
            'scale_0_1': 'ya está en [0,1]: se queda',
            'ambiguous': 'aparece en un archivo 0-1 y en uno 1-6 con el mismo número: decidir',
        }, 'scale_arrays': {'0_1': sorted(ZERO_ONE_ARRAYS), 'files': ARRAY_FILES},
            'arrays': origins.get('arrays'), 'per_type': per_type, 'by_rule': dict(sorted(collections.Counter(
                x['rule'] for x in weights).items())), 'items_w_le_1': weight_items},
        'd_verbs': {'table': verb_table, 'facts': verbs, 'margins': margins},
        'e_heaviest_undated': heaviest,
        'f_reconcile': reconcile,
    }
    return review


# ── Markdown ─────────────────────────────────────────────────────────────────────────────────────────────────────
def _ck():
    return '✔ / ✘'


def render_md(rv):
    c = rv['counts']
    out = [
        '# Revisión del grafo — listas para marcar ✔ / ✘',
        '',
        '> GENERADO por `python scripts/build_graph_review.py` desde el catálogo (`data/grafo_v0.json`). No lo edites a '
        'mano salvo las columnas ✔/✘ y "Nota tuya" (si el catálogo cambia, se regenera y hay que copiar tus marcas). '
        'La versión para máquinas es `docs/revision_grafo.json`.',
        '',
        '## Qué es esto (en simple)',
        '',
        'Khipus calcula el contagio de riesgos sobre el mapa de relaciones entre empresas. Encontramos datos del mapa '
        'que están mal escritos: relaciones al revés, relaciones con fecha guardadas con el tipo equivocado, pesos '
        'anotados en dos escalas distintas y palabras en español que el motor no entiende. '
        '**Nada de esto se cambia hasta que tú lo marques.** Hoy la app sigue funcionando igual.',
        '',
        f'- **(a)** {c["dated_links"]} relaciones CON FECHA que hoy entran al motor como "provee a" aunque son '
        'inversiones, contratos de energía o van al revés.',
        f'- **(b)** {c["text_directions"]} relaciones cuyo texto dice lo contrario de la flecha '
        f'({c["text_directions_new"]} no estaban en ninguna lista anterior).',
        f'- **(c)** La escala de pesos: {c["weights_eq1"]} vínculos con peso 1 (no se sabe en qué escala se escribieron) '
        f'y {c["weights_lt1"]} con peso menor a 1.',
        f'- **(d)** {c["off_vocab_facts"]} hechos con verbos en español que el motor ignora (controla, alberga, domina…) '
        f'y {c["margins_out_of_range"]} márgenes fuera de rango.',
        f'- **(e)** Los {c["heaviest_undated"]} vínculos más importantes que no tienen fecha real (para fecharlos con fuente).',
        '- **(f)** La reconciliación catálogo ↔ base de datos (decisión #7).',
        '',
        '## Cómo responder',
        '',
        'Pon **✔** (de acuerdo con la propuesta) o **✘** (no) en cada fila, o en la fila "todo el grupo" cuando la haya. '
        'Si no sabes, déjala como está: **una fila sin marca no se aplica**. También puedes decirme "acepto todas las '
        'propuestas de la sección (a)". Luego mándame el archivo.',
        '',
        '**Qué significa la flecha:** `A → B` = A le PROVEE algo a B (si A cae, B sufre). En los tipos:',
        '',
        '| Tipo | Quiere decir | ¿Mueve el contagio? |',
        '|---|---|---|',
    ]
    for ty in ('supply', 'fab', 'cloud', 'license', 'ppa', 'owns', 'deploy', 'invest', 'partner', 'affects', 'about'):
        moves = 'sí' if ty in ('supply', 'fab', 'cloud', 'license', 'ppa', 'owns', 'deploy') else 'no'
        out.append(f'| `{ty}` | {TYPE_ES.get(ty, ty)} | {moves} |')

    # (a)
    out += ['', f'## (a) Las {c["dated_links"]} relaciones con fecha (tipo y dirección)', '',
            'Hoy la migración guarda estas relaciones como "provee a" (`supply`) sin peso, y el motor les pone peso 2. '
            'Ejemplo real: el motor cree que si OpenAI cae arrastra un 18 % a Oracle, cuando la relación es la inversa. '
            '"Propuesta" dice el tipo correcto y si hay que darle vuelta a la flecha.', '',
            '| # | Hecho (fecha) | Hoy | Propuesta | Por qué | Ya en el catálogo | ¿De acuerdo? | Nota tuya |',
            '|---|---|---|---|---|---|---|---|']
    for i, d in enumerate(rv['a_dated_links'], 1):
        when = d['valid_from'] + (f' → {d["valid_until"]}' if d.get('valid_until') else '')
        p = d['proposal']
        if p['kind'] == 'retract':
            prop = '**retirar** (es un suceso, no una relación)'
        else:
            prop = f"**{_arrow(p['source'], p['target'])}** `{p['type']}`" + (' ⟲ al revés' if p['inverted'] else '')
            if p['kind'] == 'date_existing':
                prop += ' (ya existe: solo se le pone la fecha)'
        ctx = '; '.join(f"{_arrow(x['source'], x['target'])} `{x['type']}` w{_n(x['w'])}" for x in d['catalog_context']) or '—'
        out.append(f"| {i} | {d['subject']} «{_cell(d['predicate'])}» {d['object']} ({when}) | "
                   f"{_arrow(d['subject'], d['object'])} `supply` | {prop} | {_cell(d['why'])} | {_cell(ctx)} | {_ck()} | |")

    # (b)
    out += ['', f'## (b) Relaciones cuyo texto dice lo contrario de la flecha ({c["text_directions"]})', '',
            'El texto de la relación nombra como CLIENTE (el que usa, compra o adquirió) a quien la flecha pone como '
            'PROVEEDOR. "La correcta ya existe" = la relación en el sentido bueno ya está en el mapa: solo se borra la '
            'equivocada. Las marcadas "lista anterior" ya aparecían en la auditoría como par en los dos sentidos; '
            'ahora el texto dice cuál de los dos está mal.', '',
            'Ojo con las de tipo `owns` ("es dueño de"): ahí la flecha va del DUEÑO a lo que posee. En esas filas el '
            'texto dice que alguien COMPRÓ (adquirió) a otro, y el comprador quedó como destino de la flecha en vez de '
            'como origen: la propuesta lo pone como origen (dueño → empresa comprada).', '',
            '| # | Hoy | Texto | Propuesta | Lista anterior | ¿De acuerdo? | Nota tuya |', '|---|---|---|---|---|---|---|']
    for i, d in enumerate(rv['b_text_directions'], 1):
        if d['proposal'] == 'invert':
            prop = f"dar vuelta: **{_arrow(d['target'], d['source'])}** `{d['new_type']}`" + (
                f" (antes `{d['type']}`)" if d['new_type'] != d['type'] else '')
        elif d['proposal'] == 'retract_reverse_exists':
            rt = d.get('reverse_type') or d['type']
            prop = f"borrar (la correcta {_arrow(d['target'], d['source'])} `{rt}` ya existe)"
        else:
            prop = 'borrar (competir o haber fundado no es suministrar)'
        out.append(f"| {i} | {_arrow(d['source'], d['target'])} `{d['type']}` w{_n(d['w'])} | «{_cell(d['rel'])[:140]}» | "
                   f"{prop} | {'sí' if d['in_audit_32'] else 'no'} | {_ck()} | |")

    # (c)
    cw = rv['c_weights']
    out += ['', '## (c) Una sola escala de pesos: de 0 a 1', '',
            '**En simple:** el "peso" dice cuánto depende el cliente de ese proveedor. Casi todo el catálogo lo anotó '
            'de 1 a 6, pero un archivo (`nodes/nodes_expand5.js`) lo anotó de 0 a 1 — y además muchos de esos números '
            'no son un peso sino la "importancia del tipo" copiada (por ejemplo 0,9 en todas las nubes), que el motor '
            f'vuelve a multiplicar: se aplica DOS veces. Resultado: {c["weights_lt1"]} vínculos (los de peso menor a 1) '
            f'cuentan mucho menos de lo que deberían ({c["weights_sole_lt1_flow"]} de ellos son el ÚNICO proveedor de '
            'ese tipo y hoy transmiten como máximo un 15 %).', '',
            '**La propuesta** es pasar todo a una escala de 0 a 1 (1 = el cliente depende por completo):', '',
            '- Peso de 1 a 6 → peso ÷ 6 (un 6 pasa a 1; un 3 pasa a 0,5; un 1 pasa a 0,17).',
            '- Peso de 0 a 1 de verdad → se queda.',
            '- "Importancia del tipo" copiada → no sabemos el peso real: se usa el TÍPICO de su tipo (la mediana de los '
            'vínculos de 1 a 6 de ese tipo, ÷ 6). Puedes corregir cualquiera.',
            '- Cuando esto se aplique, el motor cambia a la vez el "piso del proveedor único" de 6 a 1 (mismo resultado '
            'para los vínculos 1-6) y se verifica con la prueba de paridad.', '',
            '| Tipo | Vínculos | Peso < 1 | Peso = 1 | Peso > 1 | "Importancia copiada" | Típico (1-6) |',
            '|---|---:|---:|---:|---:|---:|---:|']
    for ty, r in cw['per_type'].items():
        out.append(f"| `{ty}` | {r['n']} | {r['lt1']} | {r['eq1']} | {r['gt1']} | {r['placeholder']} | {_n(r['typical_1_6'])} |")
    eq1 = [x for x in cw['items_w_le_1'] if float(x['w']) == 1]
    groups = (('scale_1_6', 'Escritos de 1 a 6 (peso 1 = dependencia débil) → 0,17'),
              ('placeholder', 'Escritos de 0 a 1 con la "importancia del tipo" copiada → peso típico de su tipo'),
              ('scale_0_1', 'Escritos de 0 a 1 de verdad → 1 (dependencia total)'),
              ('ambiguous', 'Ambiguos (el mismo número en un archivo 0-1 y en uno 1-6)'))
    out += ['', f'### Los {len(eq1)} vínculos con peso 1, uno por uno', '',
            'Primero marca el grupo entero (si estás de acuerdo con la regla del grupo); después, si quieres, cambia '
            'filas sueltas.', '']
    for rule, title in groups:
        xs = [x for x in eq1 if x['rule'] == rule]
        if not xs:
            continue
        out += [f'#### {title} — {len(xs)}', '', f'**Todo el grupo:** {_ck()}', '',
                '| # | Vínculo | Tipo | Archivo | Propuesta (0-1) | ¿De acuerdo? |', '|---|---|---|---|---:|---|']
        for i, x in enumerate(xs, 1):
            out.append(f"| {i} | {_arrow(x['source'], x['target'])} | `{x['type']}` | {', '.join(x['files'])} | "
                       f"{_n(x['w01'])} | {_ck()} |")
        out.append('')
    uni = [x for x in cw['items_w_le_1'] if x.get('placeholder_kind') == 'uniform_constant']
    if uni:
        ut = sorted({(x['type'], x['w']) for x in uni})
        out += [f'### Los {len(uni)} vínculos con el MISMO número en todo su tipo — ¿peso real o importancia copiada?', '',
                'En el archivo 0-1, ' + ', '.join(f'todos los `{t}` llevan {_n(w)}' for t, w in ut) + '. Un mismo '
                'número en todas las filas casi nunca es un peso medido: la propuesta los trata como "importancia '
                'copiada" (peso típico de su tipo). Si son pesos reales, marca ✘ y se quedan como están.', '',
                f'**Todo el grupo:** {_ck()}', '',
                '| # | Vínculo | Tipo | Peso hoy | Propuesta (0-1) | ¿De acuerdo? |', '|---|---|---|---:|---:|---|']
        for i, x in enumerate(uni, 1):
            out.append(f"| {i} | {_arrow(x['source'], x['target'])} | `{x['type']}` | {_n(x['w'])} | {_n(x['w01'])} | "
                       f"{_ck()} |")
        out.append('')
    sole = [x for x in cw['items_w_le_1'] if x['sole_supplier']]
    out += [f'### Los {len(sole)} proveedores ÚNICOS con peso menor a 1 (los que más cambian)', '',
            'Son el único proveedor de su tipo para ese cliente; hoy transmiten como máximo un 15 % del golpe.', '',
            '| # | Vínculo | Tipo | Peso hoy | Propuesta (0-1) | ¿De acuerdo? |', '|---|---|---|---:|---:|---|']
    for i, x in enumerate(sole, 1):
        out.append(f"| {i} | {_arrow(x['source'], x['target'])} | `{x['type']}` | {_n(x['w'])} | {_n(x['w01'])} | {_ck()} |")
    out += ['', f"Los demás vínculos con peso menor a 1 ({c['weights_lt1'] - len(sole)}) siguen la misma regla; están "
            'todos en `docs/revision_grafo.json` (`c_weights.items_w_le_1`). Si aceptas las reglas, se aplican igual.']

    # (d)
    dv = rv['d_verbs']
    out += ['', '## (d) Verbos en español que el motor no entiende', '',
            f'{c["off_vocab_facts"]} hechos con fecha usan verbos que no están en el vocabulario del motor, así que hoy '
            'no cuentan para nada. Casi todos unen una empresa con un CONCEPTO (una tecnología como EUV, un material, '
            f'un país o una ley). Propuesta por verbo — **las {sum(1 for r in dv["table"].values() if r["question"])} '
            'con "?" necesitan tu respuesta**:', '',
            '| Verbo | Hechos | Propuesta | Qué significa | ¿De acuerdo? | Tu respuesta |', '|---|---:|---|---|---|---|']
    for v, r in dv['table'].items():
        prop = f"`{r['type']}`" + (f" (entre dos empresas: `{r['company_type']}`)" if r.get('company_type') else '')
        out.append(f"| {'**' + v + '** ?' if r['question'] else v} | {r['n']} | {prop} | {_cell(r['es'])} | {_ck()} | |")
    out += ['', '<details><summary>Los hechos uno por uno</summary>', '',
            '| # | Hecho | Desde | Propuesta |', '|---|---|---|---|']
    for i, x in enumerate(dv['facts'], 1):
        p = x['proposal']
        out.append(f"| {i} | {x['subject']} «{x['verb']}» {x['object']} | {x['valid_from']} | "
                   f"{_arrow(p['source'], p['target'])} `{p['type']}` |")
    out += ['', '</details>', '', f'### Márgenes fuera de rango ({c["margins_out_of_range"]})', '',
            'La regla de calidad pide un margen entre -1 y 1 (o sea, entre -100 % y +100 %).', '',
            '| # | Empresa | Margen hoy | Propuesta | ¿De acuerdo? |', '|---|---|---:|---|---|']
    for i, m in enumerate(dv['margins'], 1):
        out.append(f"| {i} | **{m['label']}** (`{m['node']}`) | {_n(m['margin'])} | {_cell(m['proposal']['es'])} | {_ck()} |")

    # (e)
    out += ['', f'## (e) Los {c["heaviest_undated"]} vínculos más importantes sin fecha real', '',
            'Si preguntas "¿cómo era la cadena en 2018?", Khipus hoy muestra la de hoy, porque casi ningún vínculo tiene '
            'fecha. Estos son los más importantes (peso en la escala 0-1 propuesta × importancia del tipo × confianza). '
            '**No inventamos fechas:** la columna "Fecha (con fuente)" se llena con un documento (tú, o el agente de '
            'investigación la propone con su fuente para tu visto bueno). Cuando el catálogo ya tiene un hecho con '
            f'fecha para ESE vínculo, se muestra como pista ({c["heaviest_with_catalog_hint"]} casos): ✔ = usar esa '
            'fecha (o la que escribas, con su fuente).', '',
            '| # | Vínculo | Tipo | Peso | Pista del catálogo | Fecha (con fuente) | ¿Usar esta fecha? |',
            '|---|---|---|---:|---|---|---|']
    for i, h in enumerate(rv['e_heaviest_undated'], 1):
        hint = '; '.join(f"{x['valid_from']} «{_cell(x['predicate'])}» ({x['fact_id']})" for x in h['catalog_hint']) or '—'
        out.append(f"| {i} | {_arrow(h['source'], h['target'])} | `{h['type']}` | {_n(h['w'])} | {hint} | | {_ck()} |")

    # (f)
    rc = rv['f_reconcile']
    out += ['', '## (f) Catálogo ↔ base de datos (decisión #7)', '',
            'Hoy hay tres copias del mapa (el catálogo de archivos, su foto `data/grafo_v0.json` y la base de datos de '
            'producción). La recomendación es que **la base de datos de producción mande** y que el catálogo se '
            'reconcilie con ella una vez, con tu revisión. La reconciliación nunca borra: todo cambio es un evento '
            'nuevo que se puede deshacer por corrida.', '',
            f"**¿La base de datos de producción manda sobre el catálogo?** (recomendado) {_ck()}", '',
            '| Qué compara | Qué hace | ', '|---|---|']
    for k, v in rc['categories'].items():
        out.append(f'| `{k}` | {v} |')
    cat = rc['catalog']
    out += ['', f"Lado catálogo: {_n(cat['nodes'])} empresas, {_n(cat['links'])} vínculos, {cat['aliases']} alias, "
            f"{cat['temporal_facts']} hechos con fecha.", '',
            '**Dónde ver el plan EN VIVO** (las cifras de producción cambian, por eso no están aquí): '
            f"{rc['where']['ui']}, o `{rc['where']['api']}`, o en la terminal "
            f"`{rc['where']['this_script']}` (solo lectura). Aplicar sigue pidiendo PIN y el nombre exacto de la base.",
            '',
            '## Qué pasa después', '',
            '- Con tus marcas, un paso siguiente aplica SOLO lo marcado ✔: en la base de producción como acciones de la '
            'ontología (RetractarVinculo + ProponerVinculo/CorregirDato, canal `review_grafo:<id>`, con PIN, cada una '
            'queda en el libro de decisiones) y en el catálogo de archivos (+ exportar la foto).',
            '- Antes de aplicar se muestra cuánto cambia el contagio (por ejemplo TSMC u OpenAI) para que lo veas.',
            '- Mientras no respondas: nada cambia. Esta lista se regenera sola si el catálogo cambia '
            '(`python scripts/build_graph_review.py`).', '']
    return '\n'.join(out)


def render_json(rv):
    return json.dumps(rv, ensure_ascii=False, indent=1, sort_keys=False) + '\n'


# ── reconciliación en vivo (solo lectura) ────────────────────────────────────────────────────────────────────────
def reconcile_summary(plan):
    """Plan de ontology/reconcile.build_plan → líneas en español simple (no se guarda en el documento)."""
    s = plan.get('summary') or {}
    lines = [f"Plan de reconciliación (as_of {plan.get('as_of')}, foto del catálogo {(plan.get('snapshot') or {}).get('exported_at')}):",
             f"  base: {s.get('db_objects', 0)} objetos, {s.get('db_links_vigentes', 0)} vínculos vigentes · "
             f"catálogo: {s.get('catalog_nodes', 0)} empresas, {s.get('catalog_links', 0)} vínculos"]
    labels = {'alias': 'duplicadas por alias (se aplica por defecto)', 'duplicates': 'repetidos exactos (por defecto)',
              'direction': 'al revés (tu marca)', 'variants': 'otro peso (tu marca)', 'missing': 'faltan en la base (tu marca)',
              'extra': 'sobran en la base (tu marca)', 'objects_missing': 'con una empresa que no está en la base',
              'missing_rejected': 'faltantes que alguien ya cerró (no se re-crean)'}
    for k, lab in labels.items():
        lines.append(f'  {k:16s} {s.get(k, 0):6d}  {lab}')
    oos = plan.get('out_of_scope') or {}
    if oos:
        lines.append('  fuera de alcance (no se tocan): ' + ', '.join(f'{k} {v}' for k, v in sorted(oos.items())))
    return lines


def live_reconcile():
    if not os.getenv('DATABASE_URL'):
        return ['--db: DATABASE_URL no está configurada (nada que comparar).']
    from sqlalchemy import text
    from ontology import reconcile as RC
    from ontology.db import session_scope
    with session_scope() as s:
        s.execute(text('SET TRANSACTION READ ONLY'))
        plan = RC.build_plan(s, RC.load_snapshot())
    return reconcile_summary(plan)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Listas de revisión del grafo para Fabrizio (sin cambiar nada).')
    ap.add_argument('--check', action='store_true', help='código 1 si docs/REVISION_GRAFO.md o el JSON no están al día')
    ap.add_argument('--db', action='store_true', help='imprime el plan de reconciliación EN VIVO (solo lectura)')
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:  # noqa: BLE001
        pass
    rv = build(load_snapshot(), load_origins())
    md, js = render_md(rv), render_json(rv)
    if args.check:
        stale = []
        for path, want in ((OUT_MD, md), (OUT_JSON, js)):
            try:
                with open(path, encoding='utf-8') as fh:
                    if fh.read() != want:
                        stale.append(os.path.relpath(path, ROOT))
            except FileNotFoundError:
                stale.append(os.path.relpath(path, ROOT))
        if stale:
            print('✗ no están al día: ' + ', '.join(stale) + ' → corre python scripts/build_graph_review.py')
            return 1
        print('✓ docs/REVISION_GRAFO.md y docs/revision_grafo.json al día')
    else:
        for path, body in ((OUT_MD, md), (OUT_JSON, js)):
            with open(path, 'w', encoding='utf-8', newline='\n') as fh:
                fh.write(body)
        print('escrito docs/REVISION_GRAFO.md y docs/revision_grafo.json · ' + json.dumps(rv['counts'], ensure_ascii=False))
    if args.db:
        print('\n'.join(live_reconcile()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
