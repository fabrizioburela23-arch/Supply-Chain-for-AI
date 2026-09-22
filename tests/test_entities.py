"""tests/test_entities.py — Phase 1 · M2: identidad de entidad.

Lo que se protege aquí es un fallo SILENCIOSO: hasta M2, un nombre generado por
un LLM ("NVIDIA Corporation", "NVDA", "AWS") no lograba pegarse a su entidad y
el hecho se perdía sin ruido. La causa de fondo era que `NODE_ID_ALIAS` —la
tabla canónica del merge— vivía solo en JS y no cruzaba al servidor.

No requiere Postgres: el resolvedor trabaja sobre el snapshot del repo.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── La tabla de alias cruza la frontera cliente→servidor ────────────────────

def test_el_snapshot_incluye_la_tabla_de_alias():
    """Regresión del defecto raíz: el exportador usaba NODE_ID_ALIAS como
    ENTRADA del merge pero no lo incluía en la salida, así que la migración y
    el servidor nunca lo veían."""
    import json
    ruta = os.path.join(os.path.dirname(__file__), '..', 'data', 'grafo_v0.json')
    with open(ruta, encoding='utf-8') as fh:
        snap = json.load(fh)
    alias = snap.get('node_id_alias')
    assert isinstance(alias, dict) and len(alias) >= 50, 'la tabla de alias no llegó al snapshot'
    # alias conocidos del merge real
    assert alias.get('AWS') == 'Amazon'
    assert alias.get('Azure') == 'Microsoft'


# ── Identificadores externos ────────────────────────────────────────────────

def test_parse_ticker_separa_simbolo_y_bolsa():
    """El campo `ticker` del catálogo mezcla las dos cosas: 'RGTI · Nasdaq'."""
    from core.entities import parse_ticker
    assert parse_ticker('RGTI · Nasdaq') == ('RGTI', 'Nasdaq')
    assert parse_ticker('IBM · NYSE (división)') == ('IBM', 'NYSE')
    assert parse_ticker('TSM · NYSE') == ('TSM', 'NYSE')
    assert parse_ticker('') == (None, None)
    assert parse_ticker(None) == (None, None)
    # basura no se cuela como símbolo
    simbolo, _ = parse_ticker('una frase larga que no es un ticker')
    assert simbolo is None


def test_external_ids_prefiere_el_simbolo_limpio():
    from core.entities import external_ids
    ids = external_ids({'mkt': 'TSM', 'ticker': 'TSM · NYSE'})
    assert ids['ticker'] == 'TSM'
    assert ids['exchange'] == 'NYSE'
    # sin `mkt` cae al símbolo parseado del campo sucio
    assert external_ids({'ticker': 'RGTI · Nasdaq'})['ticker'] == 'RGTI'
    assert external_ids({}) == {}


# ── Resolución ──────────────────────────────────────────────────────────────

def test_resuelve_los_casos_que_antes_fallaban():
    """El caso de negocio: lo que escribe un LLM."""
    from core.entities import resolve

    assert resolve('Nvidia')['id'] == 'Nvidia'
    assert resolve('NVDA')['id'] == 'Nvidia'                 # por ticker
    assert resolve('NVIDIA Corporation')['id'] == 'Nvidia'   # sufijo societario
    assert resolve('nvidia corp')['id'] == 'Nvidia'
    assert resolve('AWS')['id'] == 'Amazon'                  # alias del merge
    assert resolve('Azure')['id'] == 'Microsoft'


def test_devuelve_como_resolvio_no_solo_que_resolvio():
    """Sin el método no se puede auditar por qué un texto acabó en una entidad,
    ni exigir más rigor a quien escribe que a quien solo busca."""
    from core.entities import resolve

    exacto = resolve('Nvidia')
    assert exacto['method'] == 'id' and exacto['score'] == 100

    tic = resolve('NVDA')
    assert tic['method'] == 'ticker' and tic['score'] == 98

    ali = resolve('AWS')
    assert ali['method'] == 'alias'

    assert 'label' in exacto and 'matched' in exacto


def test_no_inventa_cuando_no_sabe():
    """Devolver None es la respuesta correcta; adivinar corrompe el grafo."""
    from core.entities import resolve
    assert resolve('no-existe-esta-empresa-xyz-123') is None
    assert resolve('') is None
    assert resolve(None) is None
    assert resolve('   ') is None


def test_el_umbral_de_escritura_es_mas_estricto_que_el_de_busqueda():
    """Un match flojo al ESCRIBIR en la ontología corrompe el grafo en
    silencio; al buscar solo molesta al usuario. Por eso los umbrales difieren."""
    from core.entities import resolve, UMBRAL_ESCRITURA, UMBRAL_BUSQUEDA

    assert UMBRAL_ESCRITURA > UMBRAL_BUSQUEDA

    # exacto/ticker/alias superan el umbral de escritura
    for texto in ('Nvidia', 'NVDA', 'AWS'):
        assert resolve(texto, umbral=UMBRAL_ESCRITURA) is not None

    # …pero un match por subcadena (score 60) NO debe pasar a escritura
    idx_casos = [t for t in ('quantum', 'micro') if resolve(t, umbral=UMBRAL_BUSQUEDA)]
    for t in idx_casos:
        r_busq = resolve(t, umbral=UMBRAL_BUSQUEDA)
        if r_busq['score'] < UMBRAL_ESCRITURA:
            assert resolve(t, umbral=UMBRAL_ESCRITURA) is None


def test_ambiguo_no_resuelve():
    """Dos candidatos por prefijo/subcadena = ninguno. Resolver 'a lo que
    salga' es exactamente cómo se cuelan hechos en la entidad equivocada."""
    from core.entities import resolve, get_index

    idx = get_index()
    # buscar un prefijo corto que matchee varios labels
    from core.entities import norm
    candidatos = {}
    for k, nid in idx['por_label'].items():
        if len(k) >= 4:
            candidatos.setdefault(k[:4], set()).add(nid)
    ambiguos = [p for p, ids in candidatos.items() if len(ids) > 1]
    if not ambiguos:
        pytest.skip('el catálogo no tiene prefijos ambiguos de 4 letras')
    # con varios candidatos el resolvedor no debe elegir por prefijo
    for p in ambiguos[:5]:
        r = resolve(p)
        if r is not None:
            # si resolvió, debe ser por una vía EXACTA, no por prefijo/subcadena
            assert r['method'] not in ('prefijo', 'subcadena'), (p, r)


def test_resolve_many_separa_resueltos_de_fallos():
    from core.entities import resolve_many
    ok, fallos = resolve_many(['Nvidia', 'NVDA', 'no-existe-xyz-123'])
    assert set(ok) == {'Nvidia', 'NVDA'}
    assert fallos == ['no-existe-xyz-123']
