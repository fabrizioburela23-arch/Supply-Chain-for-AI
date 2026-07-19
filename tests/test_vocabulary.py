"""tests/test_vocabulary.py — el registro único de vocabulario.

El riesgo de mover el vocabulario a un JSON es cambiar el comportamiento del
motor sin darse cuenta. Estos tests CLAVAN los valores históricos: si alguien
edita vocabulary.json y rompe la equivalencia con el motor histórico, falla aquí
antes de llegar a producción (y antes de que /api/matrix/parity lo detecte).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ontology import vocabulary as V  # noqa: E402

# Valores EXACTOS del motor antes del registro (matrix/engine.py:21-31).
HIST_REL_TYPES = ['supply', 'cloud', 'fab', 'license', 'partner', 'invest',
                  'deploy', 'owns', 'ppa']
HIST_WEIGHTS = {'supply': 1.0, 'fab': 1.0, 'cloud': 0.9, 'license': 0.8,
                'ppa': 0.7, 'deploy': 0.4, 'partner': 0.3, 'owns': 0.6,
                'invest': 0.25}
HIST_SYMMETRIC = {'partner'}
# Tipos que HOY forman el grafo (lista negra histórica = todo menos estos dos)
HIST_ECONOMIC = {'Company', 'Tech', 'Country', 'Policy', 'Material', 'Energy',
                 'Product', 'Org'}


def test_relation_types_exact_order():
    """El ORDEN importa: la suma de matrices en float no es asociativa."""
    assert V.relation_types() == HIST_REL_TYPES


def test_relation_weights_exact():
    assert V.relation_weights() == HIST_WEIGHTS


def test_symmetric_exact():
    assert V.symmetric_relations() == HIST_SYMMETRIC


def test_economic_types_whitelist_matches_today():
    """La lista blanca debe dar el MISMO conjunto de nodos que la lista negra
    histórica sobre los tipos que existen hoy en la ontología."""
    assert set(V.economic_types()) == HIST_ECONOMIC


def test_user_artifacts_are_not_graph_nodes():
    """El bug que motivó el cambio: notas/tesis/decisiones/noticias NO deben
    entrar al grafo económico (con la lista negra sí entraban)."""
    for t in ('Thesis', 'Annotation', 'Decision', 'PositionAdjustment',
              'NewsItem', 'Source', 'Simulation', 'Factor', 'Supercycle'):
        assert V.is_economic(t) is False, t


def test_unknown_type_is_reported_not_silently_defaulted():
    V.reset_unknown()
    assert V.is_economic('TipoQueNoExiste') is False
    rep = V.unknown_report()
    assert 'TipoQueNoExiste' in rep.get('object_type', {})
    V.reset_unknown()


def test_unknown_relation_is_reported():
    V.reset_unknown()
    assert V.is_known_relation('relacion_inventada') is False
    assert 'relacion_inventada' in V.unknown_report().get('relation_type', {})
    assert V.is_known_relation('supply') is True
    V.reset_unknown()


def test_non_structural_relations_stay_out_of_matrices():
    """'affects' (hiperaristas) y las de conocimiento no deben propagar daño:
    se guardan y consultan, pero no entran en las matrices."""
    for rel in ('affects', 'about', 'reports_on', 'published_by'):
        assert rel in V.relation_types_all()
        assert rel not in V.relation_types()
        assert rel not in V.relation_weights()


def test_engine_reads_registry():
    """El motor debe exponer exactamente lo del registro (una sola fuente)."""
    from matrix import engine as E
    assert E.REL_TYPES == HIST_REL_TYPES
    assert E.DEFAULT_REL_WEIGHTS == HIST_WEIGHTS
    assert E.SYMMETRIC == HIST_SYMMETRIC


def test_snapshot_serializable():
    import json
    snap = V.snapshot()
    json.dumps(snap)   # debe poder servirse tal cual al cliente
    assert snap['structural_relations'] == HIST_REL_TYPES
    assert set(snap['economic_types']) == HIST_ECONOMIC
    assert snap['source_kinds'], 'los tipos de fuente alimentan el filtro de objetividad'
