#!/usr/bin/env python3
"""scripts/build_private_valuations.py — genera nodes/private_valuations.js.

Entrada: JSON de verificación en data/private_valuations/*.json (lista de
{id, valuation_usd_b, as_of, round, raised, lead, talks_usd_b, talks_note_es,
talks_note_en, status_note, note_es, note_en, source_url, talks_source_url,
confidence, verified}). Entra solo lo verificado, con fuente y confianza
alta/media. Uso:

    python3 scripts/build_private_valuations.py data/private_valuations/*.json --as-of 2026-09-28

El .js resultante:
  · define window.PRIVATE_VALUATIONS {as_of, entries} (lo lee el Dossier);
  · actualiza window.PREIPO_INTEL[id].valuation para que el panel pre-IPO, la
    Cabina y las carteras (precio estimado) usen la cifra verificada;
  · merge_graph.js reescribe el texto "Pre-IPO ~$XB" del ticker con ella.
"""
import json
import sys
from datetime import date

KEEP = ('valuation_usd_b', 'as_of', 'round', 'raised', 'lead', 'talks_usd_b',
        'talks_note_es', 'talks_note_en', 'status_note', 'note_es', 'note_en',
        'source_url', 'talks_source_url', 'confidence')


def fmt_b(v):
    if v is None:
        return None
    return f'${v / 1000:.2f}T'.replace('.00T', 'T') if v >= 1000 else f'${v:g}B'


def main(argv):
    as_of, files, it = date.today().isoformat(), [], iter(argv)
    for a in it:
        if a == '--as-of':
            as_of = next(it)
        else:
            files.append(a)
    entries, skipped = {}, []
    for f in files:
        for r in json.load(open(f, encoding='utf-8')):
            if not r.get('verified') or r.get('valuation_usd_b') is None:
                skipped.append((r.get('id'), 'no verificado'))
                continue
            if r.get('confidence') not in ('high', 'medium') or not r.get('source_url'):
                skipped.append((r.get('id'), 'sin fuente o confianza baja'))
                continue
            e = {k: r.get(k) for k in KEEP if r.get(k) not in (None, '')}
            e['label'] = fmt_b(r['valuation_usd_b']) + (f" ({r['as_of']})" if r.get('as_of') else '')
            entries[r['id']] = e
    js = ('// nodes/private_valuations.js — GENERADO por scripts/build_private_valuations.py.\n'
          '// Última valuación CERRADA verificada con fuente de empresas privadas (y la\n'
          '// negociación, aparte). Lo "en vivo" lo agrega el Dossier desde los titulares\n'
          '// (/api/company/valuation). No editar a mano: regenerar con una verificación nueva.\n'
          'window.PRIVATE_VALUATIONS = ' +
          json.dumps({'as_of': as_of, 'entries': dict(sorted(entries.items()))}, ensure_ascii=False, indent=1) + ';\n'
          '(function () {\n'
          '  var PI = window.PREIPO_INTEL || {}, E = window.PRIVATE_VALUATIONS.entries;\n'
          '  Object.keys(E).forEach(function (id) {\n'
          '    if (PI[id]) PI[id].valuation = E[id].label;   // la cifra vieja del catálogo deja de circular\n'
          '  });\n'
          '})();\n')
    open('nodes/private_valuations.js', 'w', encoding='utf-8').write(js)
    print(f'{len(entries)} valuaciones escritas; {len(skipped)} descartadas')
    for s in skipped:
        print('  descartada:', *s)


if __name__ == '__main__':
    main(sys.argv[1:])
