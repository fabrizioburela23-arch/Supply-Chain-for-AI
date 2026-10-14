"""tests/test_genui_guardian.py — los TEXTOS que escribe el servidor en los bloques (docs/CHAT_UI_GENERATIVA.md §2.5,
§5.5 y §10.1; F1 paso 10, core/genui/alt.py):

  · cada `alt` (lector de pantalla, voz, «ver como tabla») solo usa cifras que están en los DATOS del propio bloque:
    el guardián de cifras (core/numbers.unsupported_in) no encuentra ninguna ajena, en español ni en inglés;
  · `spoken` (lo que la voz puede añadir) NO lleva cifras, ni siquiera conteos;
  · las marcas del texto: [F#] → fuente, nombre de empresa → Dossier, el tramo «(⚠ cifra no verificada)» que dejó el
    guardián → marca `unverified`; posiciones en unidades UTF-16 (las del navegador) aunque haya emojis.
(La prosa del Plan de la IA y los pros/contras con origin:model llegan en F5.)
"""
import glob
import json
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import genui  # noqa: E402
from core.genui import builders as B  # noqa: E402
from core.genui import layout as L  # noqa: E402
from core.numbers import unsupported_in  # noqa: E402

FIX = sorted(glob.glob(os.path.join(ROOT, 'tests', 'fixtures', 'genui', 'tools', '*.json')))


def _blocks(path, lang):
    with open(path, encoding='utf-8') as fh:
        doc = json.load(fh)
    b = B.Ctx(lang, 0, 'F1', '', meta={'labels': {'Nvidia': 'Nvidia', 'AMD': 'AMD'}})
    out = []
    for blk in B.BUILDERS[doc['tool']](doc['result'], b):
        ok, _why, _n = genui._check(blk, [(doc['tool'], None, True, doc['result'])])
        assert ok
        out.append(genui._strip(blk))
    return out


def _source_text(data):
    """Los datos del bloque como los leería el guardián: el JSON + cada cifra en miles de millones también en
    dólares (el JSON dice 852 con unit USD_B; el alt dice «852 mil millones USD» = 852e9 USD)."""
    extra = []

    def walk(x, unit=None):
        if isinstance(x, dict):
            u = x.get('unit', unit)
            if isinstance(x.get('v'), (int, float)) and u in ('USD_B', 'USD_T'):
                extra.append(f"{x['v'] * (1e9 if u == 'USD_B' else 1e12):.0f} USD")
            for k, v in x.items():
                walk(v, u if k != 'values' else None)
        elif isinstance(x, list):
            for v in x:
                walk(v, unit)
    walk(data)
    return json.dumps(data, ensure_ascii=False) + ' ' + ' '.join(extra)


@pytest.mark.parametrize('path', FIX, ids=[os.path.basename(p)[:-5] for p in FIX])
def test_alt_sin_cifras_ajenas_a_los_datos(path):
    for lang in ('es', 'en'):
        for blk in _blocks(path, lang):
            data = _source_text(blk.get('data'))
            for k in ('es', 'en'):
                bad = unsupported_in(blk['alt'][k], data)
                assert not bad, (blk['type'], k, blk['alt'][k], bad)


def test_spoken_sin_cifras():
    calls = []
    for p in FIX:
        with open(p, encoding='utf-8') as fh:
            d = json.load(fh)
        calls.append((d['tool'], None, True, d['result']))
    for mode in ('simple', 'pro'):
        for q in ('¿Qué pasa si cae TSMC?', 'proveedores de Nvidia', 'noticias', 'Nvidia', 'compara Nvidia y AMD'):
            env, _ = genui.build_ui(q, calls, [{'id': 'Nvidia', 'label': 'Nvidia'}], None, 'es',
                                    {'answer': 'Texto.', 'mode': mode})
            sp = env.get('spoken')
            assert sp and not re.search(r'\d', sp['es'] + sp['en']), sp


def test_marcas_del_texto():
    md = 'Nvidia 🔴 depende de TSMC [F2]; cotiza a 233,95 USD (⚠ cifra no verificada). Nvidia otra vez [F10].'
    marks = L.marks_of(md, [{'id': 'Nvidia', 'label': 'Nvidia'}, {'id': 'TSMC', 'label': 'TSMC'}])
    kinds = [(m['kind'], m.get('ref')) for m in marks]
    assert kinds == [('entity', 'Nvidia'), ('entity', 'TSMC'), ('fact', 'F2'), ('unverified', None),
                     ('entity', 'Nvidia'), ('fact', 'F10')]
    u16 = md.encode('utf-16-le')

    def piece(m):
        return u16[2 * m['s']:2 * m['e']].decode('utf-16-le')
    assert [piece(m) for m in marks] == ['Nvidia', 'TSMC', '[F2]', '(⚠ cifra no verificada)', 'Nvidia', '[F10]']


def test_texto_largo_se_parte_sin_perder_nada():
    ans = '\n\n'.join(('Párrafo %d. ' % i) + 'x' * 900 for i in range(9))
    blocks = L.text_blocks(ans, 'es', [])
    assert all(len(b['data']['md']) <= 4000 for b in blocks)
    assert '\n\n'.join(b['data']['md'] for b in blocks) == ans
