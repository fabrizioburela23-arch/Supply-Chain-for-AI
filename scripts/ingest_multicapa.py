#!/usr/bin/env python3
"""scripts/ingest_multicapa.py — Ingesta de la EXPANSIÓN MULTICAPA de Fabrizio.

Fuente: C:/Users/Dell/Downloads/khipus_ai_finance_grafo_completo.md (1,1 MB):
393 nodos + 69 FACTOR + 28 ASIENTO en 6 capas (Energía, Materiales, Macro/
Crédito, Actores, Inmobiliario, Logística). Este parser:

1. Extrae los bloques `### Nodo` / `### FACTOR:` / `### ASIENTO:` (esquema
   declarado en las líneas 96-180 del propio doc).
2. Cruza contra el grafo REAL actual (data/grafo_v0.json) — las alertas del doc
   usan baselines viejos (463/832 ids); nuestra verdad es el snapshot vivo.
3. Aplica las 5 alertas de reconciliación: Calpine y DB_Schenker NO se cargan;
   colisiones → lista de "update/skip"; dupes internos → primero gana.
4. Emite nodes/nodes_multicapa.js (nodos+links+META, patrón nodes_china.js)
   + un reporte JSON con todo lo excluido y por qué (nada se descarta en
   silencio — regla del proyecto).

Uso:  python scripts/ingest_multicapa.py [--write]   (sin --write: solo reporte)
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = r'C:\Users\Dell\Downloads\khipus_ai_finance_grafo_completo.md'

# Alerta 1 y 5 del doc: entidades absorbidas — NUNCA cargar como nodo nuevo
ABSORBED = {'Calpine', 'DB_Schenker', 'DBSchenker'}

# País del doc → convención del catálogo (GeoCoords/COUNTRY)
COUNTRY_MAP = {
    'United States': 'EEUU', 'USA': 'EEUU', 'EEUU': 'EEUU', 'US': 'EEUU',
    'South Korea': 'Corea', 'Korea': 'Corea', 'Japan': 'Japon', 'Japón': 'Japon',
    'China': 'China', 'Taiwan': 'Taiwan', 'Taiwán': 'Taiwan',
    'Germany': 'Alemania', 'Alemania': 'Alemania', 'France': 'Francia',
    'Netherlands': 'PaisesBajos', 'United Kingdom': 'ReinoUnido', 'UK': 'ReinoUnido',
    'Israel': 'Israel', 'India': 'India', 'Australia': 'Australia',
    'Canada': 'Canadá', 'Canadá': 'Canadá', 'Switzerland': 'Europa',
    'Spain': 'Europa', 'Italy': 'Europa', 'Sweden': 'Europa', 'Norway': 'Europa',
    'Denmark': 'Europa', 'Finland': 'Europa', 'Belgium': 'Europa',
    'Luxembourg': 'Europa', 'Ireland': 'Europa', 'Austria': 'Europa',
    'Singapore': 'RestoMundo', 'Hong Kong': 'China', 'Brazil': 'RestoMundo',
    'Mexico': 'RestoMundo', 'México': 'RestoMundo', 'Chile': 'Chile',
    'Saudi Arabia': 'RestoMundo', 'UAE': 'RestoMundo', 'Qatar': 'RestoMundo',
    'Kazakhstan': 'RestoMundo', 'Global': 'RestoMundo', 'Multinacional': 'RestoMundo',
}

# Sufijo de bolsa por si el ticker trae bolsa no-US (para mkt multi-mercado)
US_EXCH = ('NYSE', 'NASDAQ', 'OTC', 'AMEX', 'CBOE')


def parse_blocks(text):
    """Divide el doc en bloques ### y clasifica nodo/FACTOR/ASIENTO."""
    nodes, factors, seats = [], [], []
    # bloque = desde '### X' hasta el próximo '### ' o '## ' o '# '
    for m in re.finditer(r'^### (.+?)$\n(.*?)(?=^#{1,3} |\Z)', text, re.M | re.S):
        head, body = m.group(1).strip(), m.group(2)
        if head.startswith('FACTOR:'):
            f = parse_factor(head, body)
            if f:
                factors.append(f)
        elif head.startswith('ASIENTO:'):
            s = parse_seat(head, body)
            if s:
                seats.append(s)
        else:
            n = parse_node(head, body)
            if n:
                nodes.append(n)
    return nodes, factors, seats


def _fields(body):
    """- key: value (una línea por campo; los links se tratan aparte)."""
    out = {}
    for fm in re.finditer(r'^- ([a-zA-Z_0-9áéíóúñ]+): (.+?)$', body, re.M):
        out[fm.group(1).strip()] = fm.group(2).strip()
    return out


def parse_node(head, body):
    f = _fields(body)
    if 'id' not in f:
        return None            # bloques de prosa/esquema sin id — no son nodos
    nid = f['id'].strip()
    links = []
    for lm in re.finditer(
            r'\{target:\s*([^,}]+),\s*type:\s*([a-z_]+),\s*weight:\s*([\d.]+),\s*rel:\s*"(.*?)"\s*\}',
            body, re.S):
        links.append({'target': lm.group(1).strip(), 'type': lm.group(2).strip(),
                      'weight': float(lm.group(3)), 'rel': lm.group(4).strip()[:220]})
    nd = lambda v: (None if v in ('N/D', 'N/A', '', None) or (v or '').startswith('N/D') else v)

    def margin_of(v):
        v = nd(v)
        if not v:
            return None
        mm = re.search(r'(-?[\d.]+)', v)
        try:
            x = float(mm.group(1)) if mm else None
            if x is None:
                return None
            return round(x / 100, 3) if abs(x) > 1.5 else x   # '12%' o '0.12'
        except Exception:
            return None

    def founded_of(v):
        v = nd(v)
        mm = re.search(r'(18|19|20)\d{2}', v or '')
        return int(mm.group(0)) if mm else None

    def employees_of(v):
        v = nd(v)
        mm = re.search(r'([\d][\d,\.]*)', (v or '').replace(' ', ''))
        try:
            return int(mm.group(1).replace(',', '').split('.')[0]) if mm else None
        except Exception:
            return None

    def mkt_of(ticker):
        t = nd(ticker) or ''
        mm = re.match(r'^([A-Z][A-Z0-9.\-]{0,9})\s*·\s*(.+)$', t)
        if not mm:
            return ''
        sym, exch = mm.group(1), mm.group(2).upper()
        if any(e in exch for e in US_EXCH):
            return sym
        return ''   # bolsas no-US: mapear a sufijo Yahoo en una pasada posterior

    return {
        'id': nid, 'label': head.strip(), 'sector': f.get('sector', ''),
        'cat': f.get('cat', ''), 'ticker': nd(f.get('ticker')) or '',
        'country': COUNTRY_MAP.get(f.get('country', ''), f.get('country', '') or 'RestoMundo'),
        'role': f.get('role', ''), 'supplies': f.get('supplies', ''),
        'moat': f.get('moat', ''), 'growth': f.get('growth', ''),
        'margin': margin_of(f.get('margin')), 'mkt': mkt_of(f.get('ticker')),
        'meta': {k: v for k, v in {
            'founded': founded_of(f.get('founded')),
            'employees': employees_of(f.get('employees')),
            'revenue_2025': nd(f.get('revenue_2025')),
            'market_cap': nd(f.get('market_cap')),
            'capacity': nd(f.get('capacity')),
            'capex_2026': nd(f.get('capex_2026')),
            'geo_risk': nd(f.get('geo_risk')),
            'desc': nd(f.get('desc')),
        }.items() if v is not None},
        'links': links,
    }


def parse_factor(head, body):
    f = _fields(body)
    if 'id' not in f:
        return None
    members = {}
    mm = re.search(r'members:\s*\{(.*?)\}', body, re.S)
    if mm:
        for pm in re.finditer(r'([A-Za-z_0-9]+):\s*([\d.]+)', mm.group(1)):
            members[pm.group(1)] = float(pm.group(2))
    return {'id': f['id'].strip(), 'label': head.replace('FACTOR:', '').strip(),
            'severity': float(re.search(r'[\d.]+', f.get('severity', '5')).group(0)),
            'members': members, 'rationale': f.get('rationale', '')[:1000]}


def parse_seat(head, body):
    f = _fields(body)
    if 'id' not in f:
        return None
    return {'id': f['id'].strip(), 'label': head.replace('ASIENTO:', '').strip(),
            'props': {k: v[:600] for k, v in f.items() if k != 'id'}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    args = ap.parse_args()

    text = open(SRC, encoding='utf-8').read()
    with open(os.path.join(ROOT, 'data', 'grafo_v0.json'), encoding='utf-8') as fh:
        snap = json.load(fh)
    existing = {n['id'] for n in snap['nodes']}
    # AUTO-EXCLUSIÓN: si nodes_multicapa.js ya existe de una corrida previa, sus
    # ids NO cuentan como 'existentes' (si no, la re-corrida colisiona consigo
    # misma y vacía el catálogo — pasó en la primera ejecución).
    prev = os.path.join(ROOT, 'nodes', 'nodes_multicapa.js')
    if os.path.exists(prev):
        prev_ids = set(re.findall(r'"id":\s*"([^"]+)"', open(prev, encoding='utf-8').read()))
        existing -= prev_ids
    existing_lower = {i.lower(): i for i in existing}

    nodes, factors, seats = parse_blocks(text)
    # dedupe por id (los EJEMPLOS del esquema del doc duplican bloques reales)
    def _dedupe(items):
        out, seen_ids = [], set()
        for it in items:
            if it['id'] in seen_ids:
                continue
            seen_ids.add(it['id'])
            out.append(it)
        return out
    factors, seats = _dedupe(factors), _dedupe(seats)

    seen, fresh, collisions, absorbed, dupes = set(), [], [], [], []
    for n in nodes:
        nid = n['id']
        if nid in ABSORBED:
            absorbed.append(nid)
            continue
        if nid in seen:
            dupes.append(nid)
            continue
        seen.add(nid)
        if nid in existing or nid.lower() in existing_lower:
            collisions.append(nid)
            continue
        fresh.append(n)

    # links: separar los que apuntan a ids que existirán (snapshot ∪ nuevos)
    will_exist = existing | {n['id'] for n in fresh}
    link_rows, dropped_links = [], []
    for n in fresh:
        for l in n['links']:
            tgt = l['target']
            if tgt in ABSORBED:
                tgt = 'Constellation' if l['target'] == 'Calpine' else None
            if tgt and (tgt in will_exist):
                link_rows.append([n['id'], tgt, max(1, min(5, round(l['weight']))), l['rel'], l['type']])
            else:
                dropped_links.append(f"{n['id']}→{l['target']} ({l['type']})")

    sectors = {}
    for n in fresh:
        sectors[n['sector']] = sectors.get(n['sector'], 0) + 1

    report = {
        'parsed': {'nodes': len(nodes), 'factors': len(factors), 'seats': len(seats)},
        'fresh_nodes': len(fresh), 'collisions_vs_grafo_actual': len(collisions),
        'collision_ids': sorted(collisions)[:40], 'absorbed_skipped': absorbed,
        'internal_dupes': dupes, 'links_ok': len(link_rows),
        'links_dropped_target_desconocido': len(dropped_links),
        'dropped_sample': dropped_links[:20],
        'sectores': sectors,
        'quotables': sum(1 for n in fresh if n['mkt']),
    }
    print(json.dumps(report, ensure_ascii=False, indent=1))

    if not args.write:
        return

    # Emitir nodes/nodes_multicapa.js (patrón nodes_china.js)
    def js(o):
        return json.dumps(o, ensure_ascii=False)
    lines = [
        '// nodes/nodes_multicapa.js — EXPANSIÓN MULTICAPA (doc de Fabrizio, ago-2026):',
        f'// {len(fresh)} nodos en 6 capas (energía, materiales, macro/crédito, inmobiliario,',
        '// logística, actores) + sus links. Generado por scripts/ingest_multicapa.py — NO',
        '// editar a mano: regenerar con el script. Reconciliación aplicada (Calpine→',
        '// Constellation, DB_Schenker fuera, colisiones contra el grafo real omitidas).',
        '', 'var NODES_MULTICAPA = [',
    ]
    for n in fresh:
        row = {'id': n['id'], 'label': n['label'], 'ticker': n['ticker'], 'cat': n['cat'] or 'aisoft',
               'port': '', 'role': n['role'], 'supplies': n['supplies'], 'moat': n['moat'],
               'country': n['country'], 'growth': n['growth'], 'margin': n['margin'],
               'mkt': n['mkt'], 'sector_hint': n['sector']}
        lines.append('  ' + js(row) + ',')
    lines.append('];')
    lines.append('')
    lines.append('var LINKS_MULTICAPA = [')
    for r in link_rows:
        lines.append('  ' + js(r) + ',')
    lines.append('];')
    lines.append('')
    lines.append('var META_MULTICAPA = {')
    for n in fresh:
        if n['meta']:
            lines.append(f'  {js(n["id"])}: {js(n["meta"])},')
    lines.append('};')
    # Registro de MACRO-SECTORES nuevos + mapeo cat→sector desde los propios
    # datos (dato, no código: nada de editar nodes_seed a mano)
    NEW_SECTORS = {
        'materiales':    {'label': 'Materiales', 'en': 'Materials', 'color': '#C9A227'},
        'macro_credito': {'label': 'Macro & Crédito', 'en': 'Macro & Credit', 'color': '#7FB3D5'},
        'inmobiliario':  {'label': 'Inmobiliario', 'en': 'Real Estate', 'color': '#B08968'},
        'logistica':     {'label': 'Logística', 'en': 'Logistics', 'color': '#5FB49C'},
    }
    cat2sec = {}
    for n in fresh:
        if n['cat'] and n['sector']:
            cat2sec.setdefault(n['cat'], n['sector'])
    lines.append('')
    lines.append('// Macro-sectores nuevos + mapeo de categorías (generado de los datos)')
    # global pelado con fallback a window: funciona en navegador Y en el vm del
    # exportador (que no tiene window poblado) — sin esto, los 381 nodos caian
    # al fallback silencioso 'cloud_ia' en el snapshot
    lines.append('var _MC_S9 = (typeof SECTORS9 !== "undefined") ? SECTORS9 : ((typeof window !== "undefined") ? window.SECTORS9 : null);')
    lines.append('if (_MC_S9) Object.assign(_MC_S9, ' + js(NEW_SECTORS) + ');')
    lines.append('var _MC_C2S = (typeof CAT_TO_SECTOR !== "undefined") ? CAT_TO_SECTOR : ((typeof window !== "undefined") ? window.CAT_TO_SECTOR : null);')
    lines.append('if (_MC_C2S) Object.assign(_MC_C2S, ' + js(cat2sec) + ');')
    lines.append('if (typeof CATS_NEW !== "undefined") { var _mc_cats = ' + js(sorted(set(n['cat'] for n in fresh if n['cat']))) + ';')
    lines.append('  _mc_cats.forEach(function(c){ if (!CATS_NEW[c] && (typeof CATS === "undefined" || !CATS[c])) CATS_NEW[c] = {label: c, en: c, cssVar: "--c-" + c, x: 0.5}; }); }')
    lines.append('if (typeof document !== "undefined") { var _mc_seccol = ' + js({}) + ';')
    lines.append('  var _mc_c2s = ' + js(cat2sec) + '; var _mc_scol = ' + js({k: v['color'] for k, v in NEW_SECTORS.items()}) + ';')
    lines.append('  Object.keys(_mc_c2s).forEach(function(c){ var col = _mc_scol[_mc_c2s[c]];')
    lines.append('    if (col) document.documentElement.style.setProperty("--c-" + c, col); }); }')
    lines.append('''
if (typeof NODE_META !== 'undefined') { for (var _km in META_MULTICAPA) {
  NODE_META[_km] = Object.assign({}, NODE_META[_km] || {}, META_MULTICAPA[_km]); } }
if (typeof window !== 'undefined') {
  window.NODES_MULTICAPA = NODES_MULTICAPA;
  window.LINKS_MULTICAPA = LINKS_MULTICAPA;
}''')
    out = os.path.join(ROOT, 'nodes', 'nodes_multicapa.js')
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines))
    # factors + seats a JSON aparte (se cargan en una pasada separada, revisada)
    with open(os.path.join(ROOT, 'data', 'multicapa_factors_seats.json'), 'w', encoding='utf-8') as fh:
        json.dump({'factors': factors, 'seats': seats}, fh, ensure_ascii=False, indent=1)
    print(f'ESCRITO {out} + data/multicapa_factors_seats.json')


if __name__ == '__main__':
    main()
