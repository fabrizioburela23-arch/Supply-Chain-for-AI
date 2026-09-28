#!/usr/bin/env python3
"""scripts/build_listing_status.py — genera nodes/listing_status.js.

Entrada: uno o más JSON de verificación (lista de objetos con id, status,
ticker, exchange, listed_since, parent, parent_ticker, event_date, note_es,
note_en, source_url, confidence), producidos investigando CADA empresa del
catálogo marcada como privada / sin ticker contra fuentes (SEC, bolsas,
prensa). Solo entra lo que cambia algo (no 'private'/'unknown'), con fuente y
confianza alta o media. Uso:

    python3 scripts/build_listing_status.py data/listing_verification/*.json --as-of 2026-09-28

Las entradas de verificación se GUARDAN en data/listing_verification/ (una
por auditoría) para poder regenerar y auditar: el .js es solo el resultado.

Después: node scripts/export_graph_v0.js (el snapshot del servidor).
"""
import json
import sys
from datetime import date

CAMPOS = ('status', 'ticker', 'exchange', 'listed_since', 'parent', 'parent_ticker',
          'event_date', 'note_es', 'note_en', 'source_url', 'confidence')


def main(argv):
    as_of = date.today().isoformat()
    files = []
    it = iter(argv)
    for a in it:
        if a == '--as-of':
            as_of = next(it)
        else:
            files.append(a)
    entries, descartes = {}, []
    for f in files:
        for r in json.load(open(f, encoding='utf-8')):
            st = r.get('status')
            if st in (None, 'private', 'unknown', 'state_owned'):
                continue
            if r.get('confidence') not in ('high', 'medium') or not r.get('source_url'):
                descartes.append((r.get('id'), st, 'sin fuente o confianza baja'))
                continue
            if st == 'public' and not r.get('ticker'):
                descartes.append((r.get('id'), st, 'public sin ticker'))
                continue
            entries[r['id']] = {k: r.get(k) for k in CAMPOS if r.get(k) not in (None, '')}
    out = ('// nodes/listing_status.js — GENERADO por scripts/build_listing_status.py.\n'
           '// Estado en bolsa VERIFICADO con fuente (salió a bolsa / comprada /\n'
           '// fusionada / filial / cerró) de empresas que el catálogo daba por\n'
           '// privadas. Lo aplica nodes/merge_graph.js (navegador y snapshot).\n'
           '// No editar a mano: regenerar con una nueva verificación.\n'
           'window.LISTING_STATUS = ' +
           json.dumps({'as_of': as_of, 'entries': dict(sorted(entries.items()))},
                      ensure_ascii=False, indent=1) + ';\n')
    open('nodes/listing_status.js', 'w', encoding='utf-8').write(out)
    print(f'{len(entries)} entradas escritas; {len(descartes)} descartadas')
    for d in descartes:
        print('  descartada:', *d)


if __name__ == '__main__':
    main(sys.argv[1:])
