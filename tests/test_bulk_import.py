"""tests/test_bulk_import.py — validación e idempotencia de la ingesta masiva.

DB-free: prueba el núcleo PURO `validate_bulk_links` y la clave de idempotencia.
El camino con DB (import_links_bulk) se cubre en CI con Postgres; su lógica de
deduplicación se apoya en la misma clave probada aquí.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ontology.bulk_import import (BULK_DEFAULT_WEIGHT, _idempotency_key,  # noqa: E402
                                  validate_bulk_links)

EXISTING = {'TSMC', 'Nvidia', 'ASML', 'Apple'}


def test_accepts_valid_records():
    recs = [{'source': 'ASML', 'target': 'TSMC', 'rel_type': 'supply', 'weight': 3.0},
            {'source': 'TSMC', 'target': 'Nvidia', 'rel_type': 'fab'}]
    accepted, quarantined = validate_bulk_links(recs, EXISTING)
    assert len(accepted) == 2 and not quarantined
    assert accepted[0]['weight'] == 3.0
    assert accepted[1]['weight'] == BULK_DEFAULT_WEIGHT   # sin weight → default nominal


def test_quarantines_missing_endpoints_not_silent_drop():
    recs = [{'source': 'ASML', 'target': 'NoExiste', 'rel_type': 'supply'},
            {'source': 'Fantasma', 'target': 'TSMC', 'rel_type': 'supply'}]
    accepted, quarantined = validate_bulk_links(recs, EXISTING)
    assert not accepted
    assert len(quarantined) == 2               # cuarentena, NO descarte silencioso
    reasons = ' '.join(q['reason'] for q in quarantined)
    assert 'inexistente' in reasons


def test_quarantines_noncanonical_rel_type():
    recs = [{'source': 'ASML', 'target': 'TSMC', 'rel_type': 'inventado'}]
    accepted, quarantined = validate_bulk_links(recs, EXISTING)
    assert not accepted and len(quarantined) == 1
    assert 'no canónico' in quarantined[0]['reason']


def test_quarantines_self_link_and_bad_weight():
    recs = [{'source': 'TSMC', 'target': 'TSMC', 'rel_type': 'supply'},
            {'source': 'ASML', 'target': 'TSMC', 'rel_type': 'supply', 'weight': 'x'}]
    accepted, quarantined = validate_bulk_links(recs, EXISTING)
    assert not accepted and len(quarantined) == 2


def test_idempotency_key_prefers_external_id():
    a = {'source': 'ASML', 'target': 'TSMC', 'rel_type': 'supply', 'external_id': 'Q123'}
    b = {'source': 'ASML', 'target': 'TSMC', 'rel_type': 'supply', 'external_id': 'Q123'}
    c = {'source': 'ASML', 'target': 'TSMC', 'rel_type': 'supply'}
    assert _idempotency_key(a, 'wikidata') == _idempotency_key(b, 'wikidata')
    assert _idempotency_key(a, 'wikidata') != _idempotency_key(c, 'wikidata')
    # sin external_id, cae al triple (source,target,rel_type)
    assert _idempotency_key(c, 'wikidata')[0] == 'triple'


def test_source_target_id_aliases_accepted():
    recs = [{'source_id': 'ASML', 'target_id': 'TSMC', 'rel': 'supply'}]
    accepted, quarantined = validate_bulk_links(recs, EXISTING)
    assert len(accepted) == 1 and not quarantined
