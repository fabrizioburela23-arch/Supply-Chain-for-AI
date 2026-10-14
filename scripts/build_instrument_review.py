#!/usr/bin/env python3
"""scripts/build_instrument_review.py — genera docs/REVISION_INSTRUMENTOS.md (BRECHAS_V2 L3-13, decisión #9).

    python scripts/build_instrument_review.py          # reescribe el documento desde data/grafo_v0.json
    python scripts/build_instrument_review.py --check  # ¿está al día? (código 1 si no)

La lista sale de core/instruments.review_list() sobre el snapshot del catálogo: las empresas con VARIOS listados
declarados y las que hoy se miden con un certificado OTC/ADR. Nada cambia en la app hasta que Fabrizio marque su
elección; el precio de hoy sigue siendo el primario. Determinista, sin red, sin base.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core import instruments as I  # noqa: E402

OUT = os.path.join(ROOT, 'docs', 'REVISION_INSTRUMENTOS.md')

_KIND = {'equity': 'acción', 'adr': 'ADR (certificado en dólares)', 'otc': 'certificado OTC (poco negociado)'}


def _row(r, n):
    alt = (f"`{r['alternative']}` · {r['alternative_exchange'] or '¿?'} · {r['alternative_currency'] or '¿?'}"
           if r['alternative'] else '— (no hay otro listado claro en el catálogo)')
    rec = ('mantener el de hoy' if r['recommend'] == 'keep' else 'cambiar a la acción local')
    return (f"| {n} | **{r['label']}** (`{r['id']}`) | `{r['current']}` · {_KIND.get(r['current_kind'], r['current_kind'])}"
            f" · {r['current_currency'] or '¿?'} | {alt} | {rec} | ✔ / ✘ | ✔ / ✘ | |")


def render(nodes):
    rows = I.review_list(nodes)
    multi = [r for r in rows if r['review'] == 'multi_listed']
    otc = [r for r in rows if r['review'] == 'otc_adr']
    head = ('| # | Empresa | Precio que usa HOY | Otra opción (acción local / otro listado) | Recomendación de Khipus '
            '| ¿Mantener el de hoy? | ¿Cambiar a la otra? | Nota tuya |\n'
            '|---|---|---|---|---|---|---|---|')
    out = [
        '# Revisión de instrumentos — ¿qué precio usamos para cada empresa?',
        '',
        '> GENERADO por `python scripts/build_instrument_review.py` desde el catálogo (`data/grafo_v0.json`). '
        'No lo edites a mano salvo las columnas ✔/✘ y "Nota tuya" (si el catálogo cambia, se regenera y '
        'hay que copiar tus marcas).',
        '',
        '## Qué es esto (en simple)',
        '',
        'Una **empresa** no es lo mismo que su **acción**. Algunas empresas se compran en varias bolsas del mundo '
        '(por ejemplo Baidu en Nueva York y en Hong Kong), y otras hoy las medimos con un **certificado OTC** que '
        'se negocia poco en Estados Unidos (por ejemplo Samsung con `SSNLF`, cuando su acción de verdad es '
        '`005930` en Corea).',
        '',
        'Khipus necesita UN precio de referencia por empresa para calcular riesgo, volatilidad y la historia de '
        'precios. **Hasta que tú elijas, sigue usando el de hoy** (nada cambia solo).',
        '',
        f'- **{len(multi)} empresas con varios listados** (sección 1).',
        f'- **{len(otc)} empresas que hoy se miden con un certificado OTC o ADR** (sección 2).',
        '',
        '## Cómo responder',
        '',
        'En cada fila deja **✔** en UNA de las dos columnas ("¿Mantener el de hoy?" o "¿Cambiar a la otra?") y '
        'borra la otra marca (o pon ✘). Si no sabes, déjala como está: se mantiene el de hoy. '
        'Luego mándame el archivo o dime "acepto las recomendaciones".',
        '',
        '**Cómo pensarlo:**',
        '',
        '- **Acción local** (la de su país): es el precio "de verdad", con más volumen; viene en moneda local '
        '(yenes, euros…) y Khipus la pasa a dólares con el tipo de cambio de cada día.',
        '- **ADR / OTC en dólares**: cómodo porque ya está en dólares, pero un certificado OTC (los que terminan '
        'en **F**) se negocia muy poco: su precio puede quedarse quieto días enteros y eso hace que el riesgo '
        'parezca MENOR de lo que es.',
        '- **Recomendación de Khipus**: cambiar a la acción local cuando hoy usamos un certificado OTC; mantener '
        'el de hoy cuando ya es un listado grande en Nueva York.',
        '',
        f'## 1. Empresas con varios listados ({len(multi)})',
        '',
        head,
    ]
    out += [_row(r, i + 1) for i, r in enumerate(multi)]
    out += ['', f'## 2. Empresas medidas hoy con un certificado OTC o ADR ({len(otc)})', '', head]
    out += [_row(r, i + 1) for i, r in enumerate(otc)]
    out += I.lot_review_markdown()   # lote 2026-10-14: §3 símbolos corregidos / por decidir (core/instruments.LOT_2026_10_14)
    out += ['', '## Qué pasa después', '',
            '- Con tu elección, Khipus marca el instrumento elegido como **primario** (la tabla `instruments`; el '
            'otro queda guardado como secundario) y la historia de precios, el riesgo y los técnicos pasan a usarlo.',
            '- Mientras no respondas: se usa el de hoy y esta lista sigue en GET `/api/instruments/review`.',
            '']
    return '\n'.join(out)


def _nodes():
    with open(os.path.join(ROOT, 'data', 'grafo_v0.json'), encoding='utf-8') as fh:
        return json.load(fh).get('nodes') or []


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    text = render(_nodes())
    if '--check' in argv:
        try:
            with open(OUT, encoding='utf-8') as fh:
                cur = fh.read()
        except FileNotFoundError:
            cur = ''
        if cur != text:
            print('✗ docs/REVISION_INSTRUMENTOS.md no está al día: corre python scripts/build_instrument_review.py')
            return 1
        print('✓ docs/REVISION_INSTRUMENTOS.md al día')
        return 0
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(text)
    print('escrito', os.path.relpath(OUT, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
