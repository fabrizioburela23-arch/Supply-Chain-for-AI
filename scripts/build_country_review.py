#!/usr/bin/env python3
"""scripts/build_country_review.py — LISTA DE REVISIÓN DE PAÍSES para Fabrizio (lote 2026-10-14) + gemela JS.

    python scripts/build_country_review.py           # reescribe docs/REVISION_PAISES.md
    python scripts/build_country_review.py --js      # regenera la tabla KhipuCountries de engine/geo_coords.js
    python scripts/build_country_review.py --check   # ¿doc y tabla JS al día? (código 1 si no)

NADA cambia en el grafo: lee el catálogo (data/grafo_v0.json), lo que resuelve core/countries (ISO-2 derivado de las
136 grafías del campo `country`) y lo que propone la investigación (data/import/lotes/2026-10-14/existentes_paises.csv,
DATO no confiable: se cita, no se aplica) y escribe UN documento con lo que solo Fabrizio puede decidir:
  (1) las 70 empresas cuyo `country` es una región (Europa / RestoMundo / RestoEuropa) y no un país,
  (2) los textos con varios países ("Reino Unido / Noruega"): qué país toma Khipus (el primero) y qué dice la investigación,
  (3) las empresas que el mapa ubica en OTRO país que su clave (la ciudad del texto manda sobre el país),
  (4) todo desacuerdo entre nuestro ISO-2 derivado y el `hq_country` investigado (con método y fuente),
  (5) país de registro ≠ sede (información nueva),
  (6) el NRS: qué cambiaría si usara la clave canónica (NO se toca: nrs.formula es gobernado; decisión con PIN).
Determinista: sin red, sin IA, sin base.
"""
import argparse
import collections
import csv
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core import countries as C  # noqa: E402
from core import world as W  # noqa: E402

SNAPSHOT = os.path.join(ROOT, 'data', 'grafo_v0.json')
CSV_PATH = os.path.join(ROOT, 'data', 'import', 'lotes', '2026-10-14', 'existentes_paises.csv')
OUT_MD = os.path.join(ROOT, 'docs', 'REVISION_PAISES.md')
JS_PATH = os.path.join(ROOT, 'engine', 'geo_coords.js')
JS_BEGIN = '  // BEGIN KhipuCountries TABLE (generado)\n'
JS_END = '  // END KhipuCountries TABLE\n'
# ISO-2 → clave de la tabla NRS gobernada (nrs.formula `geo`); Europa = continente. Solo para MEDIR la diferencia.
_NRS_KEY_OF_ISO = {'US': 'EEUU', 'CN': 'China', 'TW': 'Taiwan', 'KR': 'Korea', 'JP': 'Japan', 'IL': 'Israel'}
_MULTI_RX = re.compile(r'/|doble sede|multi-pa[ií]s', re.I)     # varios países de verdad (no "sede X — operaciones en…")


def _load_nodes():
    with open(SNAPSHOT, encoding='utf-8') as fh:
        return json.load(fh)['nodes']


def _load_csv():
    if not os.path.exists(CSV_PATH):
        return {}
    with open(CSV_PATH, encoding='utf-8', newline='') as fh:
        return {r['khipus_id']: r for r in csv.DictReader(fh)}


def _esc(s):
    return str(s if s is not None else '').replace('|', '\\|').replace('\n', ' ').strip()


def _lbl(iso):
    return f'{C.label(iso, "es")} (`{iso}`)' if iso else '—'


def _src(row):
    """Método + fuente + cita de la investigación, en una celda."""
    if not row:
        return 'sin fila en el CSV'
    parts = [row.get('metodo') or '?']
    if row.get('fuente_url'):
        parts.append(f'<{row["fuente_url"]}>')
    if row.get('nota'):
        parts.append(_esc(row['nota']))
    return ' · '.join(parts)


def _nrs_key_now(country):
    return W.nrs_country(country)


def _nrs_key_canonical(country, continent=False):
    """Clave NRS que saldría del ISO-2 derivado del texto; `continent` = además 'Europa' para todo país europeo."""
    iso = C.iso2_of(country)
    if iso:
        return _NRS_KEY_OF_ISO.get(iso) or ('Europa' if continent and iso in C.EUROPE else None)
    return C.region_of(country) if C.region_of(country) == 'Europa' else None


def _nrs_key_of_map(node):
    """Clave NRS que saldría del país del MAPA (geo_coord: la ciudad/loc mandan) — la variante del plan."""
    ck = W.geo_coord(node).get('country')
    iso = C.KEY_TO_ISO.get(ck)
    return _NRS_KEY_OF_ISO.get(iso) or (ck if ck == 'Europa' else None)


def _nrs_changes(now, canon):
    return (W._NRS_GEO.get(now, W._NRS_GEO_DEFAULT) != W._NRS_GEO.get(canon, W._NRS_GEO_DEFAULT)
            or (now in W._NRS_CONCENTRATED) != (canon in W._NRS_CONCENTRATED))


def analyze(nodes=None, rows=None):
    """Todo lo que el documento cuenta, como datos (lo usa tests/test_countries.py)."""
    nodes = _load_nodes() if nodes is None else nodes
    rows = _load_csv() if rows is None else rows
    spellings = collections.Counter(str(n.get('country') or '') for n in nodes)
    regions, multi, geo_neq, disagree, incorp, nrs_diff, nrs_map, nrs_cont, unresolved = [], [], [], [], [], [], [], [], []
    for n in nodes:
        c = n.get('country') or ''
        iso = C.iso2_of(c)
        reg = C.region_of(c)
        row = rows.get(n['id'])
        hq = (row or {}).get('hq_country') or ''
        geo = W.geo_coord(n)
        key = W.country_key(c)
        rec = {'id': n['id'], 'label': n.get('label') or n['id'], 'country': c, 'loc': n.get('loc') or '',
               'iso2': iso, 'key': key, 'region': reg, 'geo_country': geo.get('country'), 'geo_precision': geo['precision'],
               'hq': hq, 'hq_key': C.catalog_key_of(hq) if hq else '', 'incorp': (row or {}).get('incorporation_country') or '',
               'src': _src(row)}
        if not iso and not reg and c:
            unresolved.append(rec)
        if reg:
            regions.append(rec)
        elif _MULTI_RX.search(c):
            multi.append(rec)
        if geo.get('country') != key and key is not None:
            geo_neq.append(rec)
        if hq and iso and hq != iso:
            disagree.append(rec)
        if hq and rec['incorp'] and rec['incorp'] != hq:
            incorp.append(rec)
        now = _nrs_key_now(c)
        for bucket, canon in ((nrs_diff, _nrs_key_canonical(c)), (nrs_map, _nrs_key_of_map(n)),
                              (nrs_cont, _nrs_key_canonical(c, continent=True))):
            if _nrs_changes(now, canon):
                bucket.append(dict(rec, nrs_now=now, nrs_canon=canon, geo_now=W._NRS_GEO.get(now, W._NRS_GEO_DEFAULT),
                                   geo_canon=W._NRS_GEO.get(canon, W._NRS_GEO_DEFAULT)))
    return {'n_nodes': len(nodes), 'n_spellings': len(spellings), 'spellings': spellings, 'regions': regions,
            'multi': multi, 'geo_neq': geo_neq, 'disagree': disagree, 'incorp': incorp, 'nrs_diff': nrs_diff,
            'nrs_map': nrs_map, 'nrs_cont': nrs_cont, 'unresolved': unresolved, 'n_csv': len(rows),
            'no_hq': [r for i, r in rows.items() if not r.get('hq_country')]}


def render(a):
    reg_counts = collections.Counter(r['region'] for r in a['regions'])
    out = io.StringIO()
    w = out.write
    w('# Revisión de países — ¿de dónde es cada empresa?\n\n')
    w('> GENERADO por `python scripts/build_country_review.py` desde el catálogo (`data/grafo_v0.json`) y la investigación del lote '
      '2026-10-14 (`data/import/lotes/2026-10-14/existentes_paises.csv`, dato NO verificado por Khipus: se cita con su fuente). '
      'NADA se aplicó: el texto `country` de cada empresa sigue igual (las ciudades que trae dan la posición fina en el mapa). '
      'No lo edites a mano salvo las columnas ✔/✘ y "Nota tuya".\n\n')
    w('## Qué es esto (en simple)\n\n')
    w(f'El catálogo escribe el país de **{a["n_spellings"]} formas distintas** ("EEUU", "Estados Unidos (HQ Denver, CO)", "Japón", '
      '"Taiwán", "Hong Kong (China)"…). Desde hoy Khipus las lee todas y deriva un **código de país ISO-2** (`US`, `JP`, `TW`…) '
      'sin cambiar el texto: la vista geopolítica del mapa, los filtros, la cartera y el contexto del chat agrupan por ese código '
      '(medido en la cartera: 126 empresas cambian de grupo, de 130 grupos a 47 —«Russia»→Rusia, EAU, HongKong, «Estados Unidos (…)»→EEUU—; '
      'las exclusiones por país aceptan cualquier grafía: «Israel», «India», «Singapur» ya no se buscan como empresa). '
      f'De las {a["n_nodes"]} empresas, **{a["n_nodes"] - len(a["regions"]) - len(a["unresolved"])} resuelven a un país**, '
      f'**{len(a["regions"])} dicen solo una región** (Europa {reg_counts.get("Europa", 0)}, Resto del mundo '
      f'{reg_counts.get("RestoMundo", 0)}, Resto de Europa {reg_counts.get("RestoEuropa", 0)}) y '
      f'{len(a["unresolved"])} no se reconocen.\n\n')
    w('**Lo que NO cambia solo:** el NRS sigue usando su tabla de siempre (sección 6: es un parámetro gobernado, '
      'cambiarlo pide tu PIN) y el país guardado de cada empresa (secciones 1-4: tú decides).\n\n')
    w('## Cómo responder\n\n')
    w('En cada fila deja **✔** en "¿Aceptar?" si el país propuesto por la investigación es correcto (o escribe el correcto en '
      '"Nota tuya") y **✘** si no. Lo que no marques se queda como hoy. Luego mándame el archivo o dime "acepto todo lo que '
      'tenga fuente".\n\n')

    w(f'## 1. Empresas sin país real — solo región ({len(a["regions"])})\n\n')
    w('"Europa" o "Resto del mundo" no es un país: sin país real no hay riesgo-país fino ni exposición a eventos locales. '
      'La investigación propone una sede concreta; el mapa de hoy la ubica como dice la columna "Mapa hoy" (por `loc` o por la '
      'ciudad del texto).\n\n')
    w('| # | Empresa | Hoy (`country`) | `loc` | Mapa hoy | Investigación: sede | Método · fuente · cita | País propuesto (clave) | ¿Aceptar? | Nota tuya |\n')
    w('|---|---|---|---|---|---|---|---|---|---|\n')
    for i, r in enumerate(sorted(a['regions'], key=lambda x: (x['region'], x['id'].lower())), 1):
        w(f'| {i} | **{_esc(r["label"])}** (`{r["id"]}`) | {_esc(r["country"])} | {_esc(r["loc"])} | {r["geo_country"]} · {r["geo_precision"]} | '
          f'{_lbl(r["hq"])} | {_esc(r["src"])} | `{r["hq_key"] or "—"}` | ✔ / ✘ | |\n')
    w('\n')

    w(f'## 2. Textos con varios países ({len(a["multi"])})\n\n')
    w('Khipus toma el PRIMER país del texto (antes de "/", "(" o ","). Si la sede real es otra, márcalo.\n\n')
    w('| # | Empresa | Texto de hoy | Khipus toma | Investigación: sede | Método · fuente · cita | ¿De acuerdo? | ¿Aceptar la investigación? | Nota tuya |\n')
    w('|---|---|---|---|---|---|---|---|---|\n')
    for i, r in enumerate(sorted(a['multi'], key=lambda x: x['id'].lower()), 1):
        ok = 'sí' if r['hq'] and r['hq'] == r['iso2'] else ('—' if not r['hq'] else 'NO')
        w(f'| {i} | **{_esc(r["label"])}** (`{r["id"]}`) | {_esc(r["country"])} | {_lbl(r["iso2"])} | {_lbl(r["hq"])} | '
          f'{_esc(r["src"])} | {ok} | ✔ / ✘ | |\n')
    w('\n')

    w(f'## 3. El mapa las pone en otro país que su clave ({len(a["geo_neq"])})\n\n')
    w('La ciudad del texto o el `loc` mandan sobre el país (regla de `geo_coord`): no es un error, pero conviene saberlo. '
      'Sin cambios salvo que marques la sede.\n\n')
    w('| # | Empresa | `country` | `loc` | Clave (país) | Mapa hoy | Investigación: sede | ¿Aceptar? | Nota tuya |\n')
    w('|---|---|---|---|---|---|---|---|---|\n')
    for i, r in enumerate(sorted(a['geo_neq'], key=lambda x: x['id'].lower()), 1):
        w(f'| {i} | **{_esc(r["label"])}** (`{r["id"]}`) | {_esc(r["country"])} | {_esc(r["loc"])} | `{r["key"]}` | '
          f'{r["geo_country"]} · {r["geo_precision"]} | {_lbl(r["hq"])} | ✔ / ✘ | |\n')
    w('\n')

    w(f'## 4. Desacuerdos entre Khipus y la investigación ({len(a["disagree"])})\n\n')
    w('Empresas con país real en el catálogo donde la investigación dice OTRA sede. Manda la fuente primaria; si la fila no '
      'trae fuente, desconfía.\n\n')
    w('| # | Empresa | Texto de hoy | Khipus deriva | Investigación: sede | Método · fuente · cita | ¿Aceptar la investigación? | Nota tuya |\n')
    w('|---|---|---|---|---|---|---|---|\n')
    for i, r in enumerate(sorted(a['disagree'], key=lambda x: x['id'].lower()), 1):
        w(f'| {i} | **{_esc(r["label"])}** (`{r["id"]}`) | {_esc(r["country"])} | {_lbl(r["iso2"])} | {_lbl(r["hq"])} | '
          f'{_esc(r["src"])} | ✔ / ✘ | |\n')
    w('\n')
    if a['no_hq']:
        w('Sin sede en la investigación: ' + ', '.join(f'`{r["khipus_id"]}` ({_esc(r["pais_original"])})' for r in a['no_hq']) + '.\n\n')

    w(f'## 5. País de registro distinto de la sede ({len(a["incorp"])}) — información\n\n')
    w('Entra como hecho con fuente (`incorporation_country`) cuando corra el importador; no mueve el mapa ni el NRS.\n\n')
    w('| # | Empresa | Sede | Registro | Método · fuente · cita |\n|---|---|---|---|---|\n')
    for i, r in enumerate(sorted(a['incorp'], key=lambda x: x['id'].lower()), 1):
        w(f'| {i} | **{_esc(r["label"])}** (`{r["id"]}`) | {_lbl(r["hq"])} | {_lbl(r["incorp"])} | {_esc(r["src"])} |\n')
    w('\n')

    w(f'## 6. El NRS no cambió — qué cambiaría si leyera el país canónico\n\n')
    w('El término "país" del NRS usa su propia tabla gobernada (`nrs.formula` 1.0.0: China 28, Taiwán 25, Corea 15, Japón 12, '
      'EE.UU. 8, Europa 10, Israel 18, resto 15) leída con alias de ORTOGRAFÍA (`core/world._NRS_GEO_ALIAS`), no con el '
      'ISO-2 nuevo. Hoy NO se toca: es una decisión tuya (`nrs.formula` 1.1.0 con PIN: 🩺 → Gobernanza → ¿Qué cambia? → '
      'Activar). Medido sobre el catálogo, tres variantes:\n\n')
    w(f'- **(a) ISO-2 del texto `country`** → cambian **{len(a["nrs_diff"])}** empresas (tabla de abajo).\n')
    w(f'- **(b) el país del MAPA** (la ciudad o el `loc` mandan: ECB → Alemania, chindata → Singapur…) → cambian '
      f'**{len(a["nrs_map"])}**: ' + ', '.join(f'`{r["id"]}` {r["geo_now"]}→{r["geo_canon"]}' for r in sorted(a['nrs_map'], key=lambda x: x['id'].lower())) + '.\n')
    w(f'- **(c) (a) + "Europa = todo país europeo"** (hoy "Alemania", "Francia", "Finlandia"… caen al 15 por defecto, no al 10 de '
      f'Europa) → cambian **{len(a["nrs_cont"])}** empresas (las {len(a["nrs_cont"]) - len(a["nrs_diff"])} europeas con país escrito '
      'bajarían 5 puntos).\n\n')
    w('| # | Empresa | Texto de hoy | NRS hoy lee | Puntos hoy | (a) leería | Puntos (a) |\n|---|---|---|---|---|---|---|\n')
    for i, r in enumerate(sorted(a['nrs_diff'], key=lambda x: x['id'].lower()), 1):
        w(f'| {i} | **{_esc(r["label"])}** (`{r["id"]}`) | {_esc(r["country"])} | {r["nrs_now"] or "(defecto)"} | {r["geo_now"]} | '
          f'{r["nrs_canon"] or "(defecto)"} | {r["geo_canon"]} |\n')
    w('\n')

    w('## 7. Las grafías del catálogo (para el trinquete)\n\n')
    w('Toda grafía nueva debe resolver a un ISO-2 o ser una región (tests/test_countries.py). Hoy:\n\n')
    w('| Grafía | Empresas | ISO-2 / región |\n|---|---|---|\n')
    for sp, cnt in sorted(a['spellings'].items(), key=lambda kv: (-kv[1], kv[0].lower())):
        iso, reg = C.iso2_of(sp), C.region_of(sp)
        w(f'| {_esc(sp) or "(vacío)"} | {cnt} | {iso or reg or "**NO RESUELVE**"} |\n')
    w('\n## Qué hacer ahora\n\n')
    w('1. Mira la sección 1 (70 filas): es la que más vale — hoy esas empresas no tienen país.\n')
    w('2. Marca ✔/✘ y mándame el archivo. Lo que marques entrará como hecho con fuente por el importador (E2), nunca a mano.\n')
    w('3. Si quieres que el NRS use el país canónico, dímelo: preparo `nrs.formula` 1.1.0 y lo activas con tu PIN.\n')
    return out.getvalue()


def render_js_line():
    """El bloque JS (varias líneas de ≤ ~120 caracteres para que el diff se lea; el contenido es el JSON de js_table)."""
    data = json.loads(C.js_table())
    parts = [json.dumps({'regions': data['regions']}, ensure_ascii=False, separators=(',', ':'))[1:-1],
             json.dumps({'extra': data['extra']}, ensure_ascii=False, separators=(',', ':'))[1:-1],
             '"rows":[' + ','.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) for r in data['rows']) + ']']
    body = ','.join(parts)
    lines, cur = [], ''
    for tok in re.split(r'(?<=\],)|(?<=",)', body):      # cortes solo tras una fila o un par del diccionario
        if cur and len(cur) + len(tok) > 118:
            lines.append(cur)
            cur = ''
        cur += tok
    lines.append(cur)
    return '  const KC_DATA = {' + '\n    '.join(lines) + '};\n'


def update_js(write=True):
    with open(JS_PATH, encoding='utf-8') as fh:
        src = fh.read()
    i, j = src.index(JS_BEGIN) + len(JS_BEGIN), src.index(JS_END)
    new = src[:i] + render_js_line() + src[j:]
    assert json.loads(render_js_line().split('= ', 1)[1].rstrip().rstrip(';').replace('\n    ', '')) == json.loads(C.js_table())
    changed = new != src
    if write and changed:
        with open(JS_PATH, 'w', encoding='utf-8') as fh:
            fh.write(new)
    return changed


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--js', action='store_true', help='regenera la tabla KhipuCountries de engine/geo_coords.js')
    args = ap.parse_args(argv)
    if args.js and not args.check:
        print('engine/geo_coords.js:', 'actualizado' if update_js() else 'ya estaba al día')
        return 0
    md = render(analyze())
    if args.check:
        bad = []
        if update_js(write=False):
            bad.append('engine/geo_coords.js (tabla KhipuCountries): corre `python scripts/build_country_review.py --js`')
        cur = open(OUT_MD, encoding='utf-8').read() if os.path.exists(OUT_MD) else ''
        if cur != md:
            bad.append('docs/REVISION_PAISES.md: corre `python scripts/build_country_review.py`')
        for b in bad:
            print('DESACTUALIZADO:', b)
        print('al día' if not bad else '')
        return 1 if bad else 0
    with open(OUT_MD, 'w', encoding='utf-8') as fh:
        fh.write(md)
    a = analyze()
    print(f'{OUT_MD}: {len(a["regions"])} regiones · {len(a["multi"])} multi-país · {len(a["geo_neq"])} mapa≠clave · '
          f'{len(a["disagree"])} desacuerdos · {len(a["incorp"])} registro≠sede · NRS (a) {len(a["nrs_diff"])} / (b) '
          f'{len(a["nrs_map"])} / (c) {len(a["nrs_cont"])} · {len(a["unresolved"])} sin resolver')
    return 0


if __name__ == '__main__':
    sys.exit(main())
