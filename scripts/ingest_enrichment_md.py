#!/usr/bin/env python3
"""scripts/ingest_enrichment_md.py — Ingesta de informes de enriquecimiento.

Parsea un informe markdown con el formato del "prompt de implementación"
(Sección A = empresas nuevas con esquema de nodo Khipus; Sección B =
enriquecimiento de nodos existentes con links_nuevos) y genera
nodes/nodes_expand5.js + un reporte JSON auditable.

Reglas clave:
- Resolución de entidades contra el grafo real (ids, labels, alias, tickers)
  usando la tabla exportada por Node (graph_table.json).
- Un nodo "nuevo" que YA existe en el grafo se convierte en enriquecimiento
  (meta + links) en vez de duplicarse.
- DIRECCIÓN CANÓNICA de links: source PROVEE a target. En la Sección B los
  links están escritos desde el nodo ("usa GPUs de Nvidia") → se invierten
  según tipo + heurística de texto. Toda decisión queda en el reporte para
  la verificación adversarial posterior (Workflow).
- Categorías de cola larga → mapeo editorial a las 40 canónicas; solo
  power_ipp / osat / defense_prime nacen como categorías nuevas.

Uso:
    python scripts/ingest_enrichment_md.py <informe.md> <graph_table.json> \
        <salida_nodes.js> <salida_reporte.json>
"""
import json
import re
import sys

# ── mapeo editorial de categorías de cola larga → canónicas ──────────────────
NEW_CATS = {
    # cat: (label_es, label_en, sector, x_layout, color_hex)
    'power_ipp':     ('Energía IPP / PPA', 'Power IPP / PPA', 'energia', .06, '#B8E356'),
    'osat':          ('Empaquetado / OSAT', 'Packaging / OSAT', 'fabricacion', .12, '#FFA94D'),
    'defense_prime': ('Defensa Prime', 'Defense Primes', 'defensa', .58, '#FF6B8A'),
}
CAT_MAP = {
    'power_ipp': 'power_ipp',
    'OSAT': 'osat',
    'defense_prime': 'defense_prime',
    'defense_electronics': 'defense_prime',
    'defense_services': 'defense_prime',
    'nuclear': 'nuclear_smr',
    'nuclear_fuel': 'uranium',
    'lunar': 'space_infra',
    'space_logistics': 'space_infra',
    'space_defense': 'space_infra',
    'space_stations': 'space_infra',
    'space_servicing': 'space_infra',
    'space_manufacturing': 'space_infra',
    'robotics_logistics': 'robotics_physical',
    'robotics_humanoid': 'robotics_physical',
    'robotics_manufacturing': 'robotics_physical',
    'robotics_healthcare': 'robotics_physical',
    'robotics_delivery': 'robotics_physical',
    'robotics_food': 'robotics_physical',
    'robotics_drones': 'robotics_physical',
    'robotics_autonomous_trucking': 'robotics_physical',
    'discretos_pasivos': 'materials',
    'ODM_semiconductor': 'servers',
    'EMS_optico': 'optics',
}

# nubes/hyperscalers para la regla de dirección del tipo `cloud`
CLOUD_PROVIDERS = {'Amazon', 'Microsoft', 'Alphabet', 'Oracle', 'IBM', 'CoreWeave',
                   'Nebius', 'GDSHoldings', 'Equinix', 'DigitalRealty'}

CONSUME_RE = re.compile(
    r'\busa[n]?\b|\butiliza|corre[n]? sobre|\bdepende|basad[oa]s? en|alojad|'
    r'se abastece|integra (?:modelos|chips|GPUs|los modelos)|adquirid[oa] por|'
    r'compr[óa] (?:a|de)|licencia (?:de|con) |sobre (?:AWS|Azure|GCP|infraestructura)|'
    r'inversor|invirti[óo]|particip[óo] como|lider(?:ó|ada) (?:la )?ronda|respaldad|financiad', re.I)
PROVIDE_RE = re.compile(
    r'\bsuministr|\bprovee|\bvende|\bentrega|fabrica para|sirve a|abastece a|'
    r'PPA .{0,40}(?:a|con|para)|suministro (?:el[ée]ctrico|de energ[ií]a) a', re.I)


SUFFIX_RE = re.compile(
    r'\s+(inc\.?|corp\.?|corporation|ltd\.?|co\.?|company|group|holdings?|'
    r'technolog(?:y|ies)|systems?|s\.a\.|plc|ag|nv|se)\s*$', re.I)


def norm_target(t):
    t = t.strip()
    # prefijo numerado de la Sección B.4 ("01. Hughes Network Systems (ya existe)")
    t = re.sub(r'^\d+\.\s*', '', t)
    t = re.sub(r'\s*\(ya existe\)\s*$', '', t, flags=re.I)
    cands = [t, re.sub(r'\s*\([^)]*\)\s*$', '', t).strip()]  # sin paréntesis
    # sin sufijos corporativos ("Oklo Inc" → "Oklo", "Seagate Technology" → "Seagate")
    for c in list(cands):
        s = SUFFIX_RE.sub('', c).strip()
        if s and s not in cands:
            cands.append(s)
    return cands


class Resolver:
    def __init__(self, table, new_ids):
        self.ids = set(table['ids'])
        self.labels = dict(table['labels'])
        self.tickers = dict(table.get('tickers') or {})
        self.aliases = dict(table.get('aliases') or {})
        self.labels_lc = {k.lower(): v for k, v in self.labels.items()}
        self.new_ids = new_ids            # ids de nodos nuevos de ESTE informe
        self.new_labels_lc = {}

    def add_new(self, nid, label):
        self.new_ids.add(nid)
        self.new_labels_lc[label.lower()] = nid

    def resolve(self, raw):
        for cand in norm_target(raw):
            if cand in self.ids or cand in self.new_ids:
                return cand
            if cand in self.aliases:
                a = self.aliases[cand]
                hops = 0
                while a in self.aliases and hops < 5:
                    a = self.aliases[a]; hops += 1
                return a
            if cand in self.labels:
                return self.labels[cand]
            if cand in self.tickers:
                return self.tickers[cand]
            lc = cand.lower()
            if lc in self.labels_lc:
                return self.labels_lc[lc]
            if lc in self.new_labels_lc:
                return self.new_labels_lc[lc]
        # último recurso: startswith ÚNICO contra labels (evita falsos positivos)
        for cand in norm_target(raw):
            lc = cand.lower()
            if len(lc) < 5:
                continue
            hits = {v for k, v in self.labels_lc.items() if k.startswith(lc)}
            hits |= {v for k, v in self.new_labels_lc.items() if k.startswith(lc)}
            if len(hits) == 1:
                return hits.pop()
        return None


def parse_blocks(md):
    """Devuelve lista de (section, header, lines) para cada bloque ###."""
    blocks, cur, section = [], None, None
    for line in md.split('\n'):
        if line.startswith('# Sección A'):
            section = 'A'
        elif line.startswith('# Sección B'):
            section = 'B'
        elif line.startswith('# Resumen final'):
            if cur: blocks.append(cur)
            cur = None
            section = None
        if section is None:
            continue
        if line.startswith('### '):
            if cur: blocks.append(cur)
            cur = (section, line[4:].strip(), [])
        elif line.startswith('## ') or line.startswith('# '):
            if cur: blocks.append(cur)
            cur = None
        elif cur is not None:
            cur[2].append(line)
    if cur: blocks.append(cur)
    return blocks


FIELD_RE = re.compile(r'^- (\w+):\s*(.*)$')
LINK_RE = re.compile(r'\{target:\s*(.+?),\s*type:\s*(\w+),\s*weight:\s*([\d.]+),\s*rel:\s*"(.*)"\s*\}')


def parse_fields(lines):
    fields, links, mode = {}, [], None
    for ln in lines:
        m = FIELD_RE.match(ln.strip()) if not ln.startswith('  ') else None
        if ln.strip().startswith('- links') or ln.strip() in ('- links:', '- links_nuevos:'):
            mode = 'links'
            continue
        lm = LINK_RE.search(ln)
        if lm and (mode == 'links' or ln.lstrip().startswith('- {target')):
            links.append({'target': lm.group(1).strip(), 'type': lm.group(2),
                          'weight': float(lm.group(3)), 'rel': lm.group(4)})
            continue
        m2 = FIELD_RE.match(ln.strip())
        if m2 and mode != 'links':
            k, v = m2.group(1), m2.group(2).strip()
            if k in ('links', 'links_nuevos'):
                mode = 'links'
            else:
                fields[k] = v
    return fields, links


def to_int(v):
    if v is None: return None
    m = re.search(r'[\d,]+', str(v).replace('.', ','))
    if not m: return None
    try: return int(m.group(0).replace(',', ''))
    except ValueError: return None


def to_margin(v):
    if v is None: return None
    m = re.match(r'^-?\d+(\.\d+)?$', str(v).strip())
    return float(v) if m else None


def mk_mkt(ticker):
    if not ticker: return ''
    first = ticker.split('·')[0].strip()
    if re.match(r'^[A-Z0-9.\-]{1,7}$', first) and first.upper() not in ('PRIVADA', 'PRE-IPO'):
        return first
    return ''


def infer_direction(section, node_id, target_id, ltype, rel, node_sector):
    """Devuelve (source, target, motivo). Canónico: source PROVEE a target."""
    consume = bool(CONSUME_RE.search(rel))
    provide = bool(PROVIDE_RE.search(rel))
    if ltype in ('partner', 'deploy'):
        return node_id, target_id, 'simétrico/deploy: nodo→target'
    if ltype == 'ppa':
        if node_sector == 'energia' or provide:
            return node_id, target_id, 'ppa: el nodo genera la energía'
        return target_id, node_id, 'ppa: el target genera la energía'
    if ltype == 'cloud':
        if target_id in CLOUD_PROVIDERS and node_id not in CLOUD_PROVIDERS:
            return target_id, node_id, 'cloud: target es el hyperscaler'
        if node_id in CLOUD_PROVIDERS and target_id not in CLOUD_PROVIDERS:
            return node_id, target_id, 'cloud: nodo es el hyperscaler'
    if ltype in ('supply', 'fab', 'license', 'cloud', 'invest', 'owns'):
        if provide and not consume:
            return node_id, target_id, 'texto: el nodo provee'
        if consume and not provide:
            return target_id, node_id, 'texto: el nodo consume/recibe'
        # sin señal clara → default por sección
        if section == 'B':
            return target_id, node_id, 'default B: target provee al nodo'
        return node_id, target_id, 'default A: nodo provee al target'
    return node_id, target_id, 'default'


def main():
    md_path, table_path, out_js, out_report = sys.argv[1:5]
    md = open(md_path, 'r', encoding='utf-8').read()
    table = json.load(open(table_path, 'r', encoding='utf-8'))
    known_cats = set(table['cats']) | set(NEW_CATS)

    res = Resolver(table, set())
    blocks = parse_blocks(md)

    new_nodes, meta, links, enrich_meta = [], {}, [], {}
    report = {'converted_to_enrichment': [], 'unmatched_targets': [],
              'unmatched_b_headers': [], 'cat_remaps': [], 'direction_log': [],
              'skipped': [], 'counts': {}}

    # ── pase 1: registrar ids nuevos (para que A pueda enlazar entre sí) ──
    for section, header, lines in blocks:
        if section != 'A' or 'DUPLICADO' in header:
            continue
        fields, _ = parse_fields(lines)
        nid = fields.get('id')
        if not nid:
            continue
        if res.resolve(nid) or res.resolve(header):
            continue  # ya existe → será enriquecimiento
        label = re.sub(r'\s*\((?:adicional|ex-)[^)]*\)\s*$', '', header).strip()
        res.add_new(nid, label)

    # ── pase 2: construir nodos, meta y links ──
    for section, header, lines in blocks:
        if 'DUPLICADO' in header:
            report['skipped'].append(header)
            continue
        fields, blk_links = parse_fields(lines)

        if section == 'A':
            if not fields.get('id'):
                # encabezado de nota/sub-sección ("Together AI — omitida", etc.), no es empresa
                report['skipped'].append(header)
                continue
            nid = fields.get('id')
            existing = res.resolve(nid) or res.resolve(header)
            if existing and existing not in res.new_ids:
                # ya está en el grafo → convertir a enriquecimiento
                report['converted_to_enrichment'].append({'header': header, 'id': existing})
                node_id, node_sector = existing, fields.get('sector', '')
                em = {k: fields[k] for k in ('founded', 'employees', 'revenue_2025', 'geo_risk', 'desc') if fields.get(k)}
                if em:
                    em['founded'] = to_int(em.get('founded'))
                    em['employees'] = to_int(em.get('employees'))
                    enrich_meta[existing] = {k: v for k, v in em.items() if v}
            else:
                cat_raw = fields.get('cat', 'aisoft')
                cat = CAT_MAP.get(cat_raw, cat_raw)
                if cat != cat_raw:
                    report['cat_remaps'].append({'id': nid, 'de': cat_raw, 'a': cat})
                if cat not in known_cats:
                    report['cat_remaps'].append({'id': nid, 'de': cat_raw, 'a': 'aisoft', 'motivo': 'cat desconocida'})
                    cat = 'aisoft'
                label = re.sub(r'\s*\((?:adicional|ex-)[^)]*\)\s*$', '', header).strip()
                ticker = fields.get('ticker', '')
                mkt = mk_mkt(ticker)
                node = {
                    'id': nid, 'label': label, 'ticker': ticker, 'cat': cat, 'port': '',
                    'role': fields.get('role', ''), 'supplies': fields.get('supplies', ''),
                    'moat': fields.get('moat', ''), 'country': fields.get('country', ''),
                    'growth': fields.get('growth', ''), 'margin': to_margin(fields.get('margin')),
                    'mkt': mkt,
                }
                if not mkt and re.search(r'privada|pre-ipo', ticker, re.I):
                    node['preipo'] = True
                new_nodes.append(node)
                meta[nid] = {k: v for k, v in {
                    'founded': to_int(fields.get('founded')),
                    'employees': to_int(fields.get('employees')),
                    'revenue_2025': fields.get('revenue_2025'),
                    'geo_risk': fields.get('geo_risk'),
                    'desc': fields.get('desc'),
                }.items() if v}
                node_id, node_sector = nid, fields.get('sector', '')
        else:  # Sección B
            existing = res.resolve(header)
            if not existing:
                report['unmatched_b_headers'].append(header)
                continue
            node_id, node_sector = existing, ''
            em = {k: fields[k] for k in ('founded', 'employees', 'revenue_2025', 'geo_risk', 'desc') if fields.get(k)}
            if em:
                em['founded'] = to_int(em.get('founded'))
                em['employees'] = to_int(em.get('employees'))
                enrich_meta[existing] = {k: v for k, v in em.items() if v}

        # links del bloque
        for lk in blk_links:
            tgt = res.resolve(lk['target'])
            if not tgt:
                report['unmatched_targets'].append({'de': node_id, 'target': lk['target'], 'rel': lk['rel'][:80]})
                continue
            if tgt == node_id:
                continue
            s, t, motivo = infer_direction(section, node_id, tgt, lk['type'], lk['rel'], node_sector)
            links.append([s, t, lk['weight'], lk['rel'], lk['type']])
            report['direction_log'].append({'seccion': section, 's': s, 't': t,
                                            'type': lk['type'], 'motivo': motivo, 'rel': lk['rel'][:100]})

    report['counts'] = {
        'nodos_nuevos': len(new_nodes), 'links_nuevos': len(links),
        'meta_nuevos': len(meta), 'meta_enriquecidos': len(enrich_meta),
        'sin_target': len(report['unmatched_targets']),
        'b_sin_match': len(report['unmatched_b_headers']),
        'convertidos': len(report['converted_to_enrichment']),
    }

    # ── generar nodes_expand5.js ──
    def js(o):
        return json.dumps(o, ensure_ascii=False)

    lines_js = [
        '// nodes/nodes_expand5.js — Informe de enriquecimiento 2026-07',
        '// Generado por scripts/ingest_enrichment_md.py desde el informe de Fabrizio',
        '// (148 nuevas + 82 enriquecidas). NO editar a mano: regenerar con el script.',
        '',
        'var NODES_EXPAND5 = [',
    ]
    for n in new_nodes:
        lines_js.append('  ' + js(n) + ',')
    lines_js += [
        '];',
        'window.NODES_EXPAND5 = NODES_EXPAND5;',
        '',
        '// [source, target, weight, rel, type] — canónico: source PROVEE a target',
        'var LINKS_EXPAND5 = [',
    ]
    for l in links:
        lines_js.append('  ' + js(l) + ',')
    lines_js += [
        '];',
        'window.LINKS_EXPAND5 = LINKS_EXPAND5;',
        '',
        '// meta (founded/employees/revenue/geo_risk/desc) de nodos nuevos y enriquecidos',
        'var META_EXPAND5 = ' + json.dumps({**meta, **enrich_meta}, ensure_ascii=False, indent=1) + ';',
        "if (typeof NODE_META !== 'undefined') { for (var _k5 in META_EXPAND5) {",
        '  NODE_META[_k5] = Object.assign({}, NODE_META[_k5] || {}, META_EXPAND5[_k5]); } }',
        'window.META_EXPAND5 = META_EXPAND5;',
        '',
        '// categorías nuevas de primera clase (el resto de la cola larga mapea a canónicas)',
    ]
    cats_new_js = {k: {'label': v[0], 'en': v[1], 'cssVar': '--c-' + k, 'x': v[3]} for k, v in NEW_CATS.items()}
    cat_sector_js = {k: v[2] for k, v in NEW_CATS.items()}
    cat_colors_js = {('--c-' + k): v[4] for k, v in NEW_CATS.items()}
    lines_js += [
        "if (typeof CATS_NEW !== 'undefined') Object.assign(CATS_NEW, " + js(cats_new_js) + ');',
        "if (typeof CAT_TO_SECTOR !== 'undefined') Object.assign(CAT_TO_SECTOR, " + js(cat_sector_js) + ');',
        "if (typeof document !== 'undefined') { var _cc5 = " + js(cat_colors_js) + ';',
        "  for (var _v5 in _cc5) document.documentElement.style.setProperty(_v5, _cc5[_v5]); }",
        '',
    ]
    open(out_js, 'w', encoding='utf-8').write('\n'.join(lines_js))
    open(out_report, 'w', encoding='utf-8').write(json.dumps(report, ensure_ascii=False, indent=1))
    print('OK:', json.dumps(report['counts'], ensure_ascii=False))


if __name__ == '__main__':
    main()
