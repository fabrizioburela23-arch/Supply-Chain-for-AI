"""tests/test_graph_audit.py — G1 (misión de reparación 2026-10-04): auditoría
automática del grafo + alias faltantes (G1b).

Dos verdades del grafo (catálogo del repo vs Postgres) y ningún chequeo de
consistencia: el diagnóstico (docs/REPARACION_DIAGNOSTICO.md, C1-C10) encontró
entidades duplicadas, enlaces al revés, enlaces "no verificados" con peso y
303 enlaces sin texto. `scripts/audit_graph.py` los cuenta sobre el snapshot
`data/grafo_v0.json` (sin red, sin base) y `data/graph_audit_baseline.json`
es el trinquete: ninguna categoría puede EMPEORAR sin que alguien lo decida.

Sin Postgres; todo el archivo corre en < 3 s.
"""
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

SNAPSHOT = os.path.join(ROOT, 'data', 'grafo_v0.json')
BASELINE = os.path.join(ROOT, 'data', 'graph_audit_baseline.json')
SEED_JS = os.path.join(ROOT, 'nodes', 'nodes_seed.js')


def _toy_snapshot():
    """Mini-grafo de juguete con UN caso por categoría (y dos contraejemplos
    que fijan la regla de perspectiva: el verbo de consumo solo cuenta si el
    texto nombra al TARGET como proveedor y no al source)."""
    return {
        'exported_at': '2026-01-01T00:00:00Z',
        'nodes': [
            {'id': 'Acme', 'label': 'Acme Inc', 'cat': 'fabless', 'sector': 'diseno', 'mkt': 'ACME', 'margin': 0.2},
            {'id': 'Acme_Corp', 'label': 'ACME Corp', 'cat': 'fabless', 'sector': 'diseno', 'mkt': 'ACM'},  # duplicado sin alias
            {'id': 'TSMC', 'label': 'TSMC', 'cat': 'foundry', 'sector': 'fabricacion', 'mkt': 'TSM'},
            {'id': 'Nvidia', 'label': 'Nvidia', 'cat': 'fabless', 'sector': 'diseno', 'mkt': 'NVDA'},
            {'id': 'Fitch', 'label': 'Fitch Ratings', 'cat': 'rating_agency', 'sector': 'macro_credito', 'mkt': None},
            {'id': 'Solo', 'label': 'Solo Ltd', 'cat': 'fabless', 'sector': 'diseno', 'mkt': 'SOLO'},  # huérfano
        ],
        'links': [
            {'source': 'TSMC', 'target': 'Nvidia', 'w': 5, 'rel': 'Fabrica Blackwell en N4P — Nvidia es su 1º cliente', 'type': 'fab'},
            {'source': 'TSMC', 'target': 'Nvidia', 'w': 3, 'rel': 'duplicado', 'type': 'fab'},            # (a) tripla repetida
            {'source': 'Acme', 'target': 'TSMC', 'w': 2, 'rel': 'Usa obleas de TSMC', 'type': 'supply'},  # (c1) verbo de consumo → target
            {'source': 'Nvidia', 'target': 'Acme', 'w': 3, 'rel': 'Contrato no verificado públicamente', 'type': 'supply'},  # (e) w 3
            {'source': 'Nvidia', 'target': 'Acme_Corp', 'w': 2, 'rel': 'Usa GPUs Nvidia para entrenar', 'type': 'supply'},  # NO: nombra al source
            {'source': 'Fitch', 'target': 'Acme', 'w': 1, 'rel': 'Cobertura de rating', 'type': 'supply'},  # (c2) fuente de servicio
            {'source': 'Acme', 'target': 'Nvidia', 'w': 1, 'rel': 'Vende IP a Nvidia', 'type': 'supply'},  # (c3) A→B y B→A supply
            {'source': 'Nvidia', 'target': 'TSMC', 'w': 1, 'rel': '', 'type': 'partner'},                 # (d) sin texto
            {'source': 'Acme', 'target': 'Nvidia', 'w': 1, 'rel': 'cliente', 'type': 'customer'},         # (g) tipo fuera de vocabulario
        ],
        'node_id_alias': {},
        'categories': {'fabless': {}, 'foundry': {}, 'rating_agency': {}},
        'sectors9': {'diseno': {}, 'fabricacion': {}, 'macro_credito': {}},
    }


# ── (i) casos sintéticos ────────────────────────────────────────────────────

def test_auditoria_detecta_casos_sinteticos():
    from scripts.audit_graph import audit_snapshot, to_markdown

    res = audit_snapshot(_toy_snapshot())
    m, f = res['metrics'], res['findings']

    assert m['duplicate_links'] == 1
    assert f['duplicate_links'][0] == {'source': 'TSMC', 'target': 'Nvidia', 'type': 'fab', 'n': 2}

    assert m['duplicate_entities'] == 1
    assert f['duplicate_entities'][0]['ids'] == ['Acme', 'Acme_Corp']
    assert 'label' in f['duplicate_entities'][0]['reasons']

    razones = {(x['source'], x['target'], x['reason']) for x in f['suspicious_directions']}
    assert ('Acme', 'TSMC', 'consume_verb_target') in razones
    assert ('Fitch', 'Acme', 'service_source') in razones
    assert ('Acme', 'Nvidia', 'bidirectional_same_type') in razones
    # contraejemplos: el texto escrito desde el cliente NO es una dirección al revés
    assert not any(x['source'] == 'Nvidia' and x['target'] == 'Acme_Corp' for x in f['suspicious_directions'])
    assert not any(x['source'] == 'TSMC' and x['reason'] == 'consume_verb_target' for x in f['suspicious_directions'])
    assert m['suspicious_directions'] == 3

    assert m['no_source_text'] == 1 and f['no_source_text'][0]['type'] == 'partner'
    assert m['unverified_weighted'] == 1 and f['unverified_weighted'][0]['w'] == 3
    assert f['orphans'] == ['Solo']
    assert m['bad_vocab'] == 1 and f['bad_vocab'][0] == {'kind': 'rel_type', 'value': 'customer', 'source': 'Acme', 'target': 'Nvidia'}

    # informativas: cifras sin fecha (Acme tiene margin), cobertura (toy sin ADI…), multi-tipo (Acme→Nvidia)
    assert res['info']['undated_figures'] == 1
    assert res['info']['missing_coverage'] == 6
    assert res['info']['pairs_multi_type'] == 1

    # resumen bilingüe y Markdown
    assert 'entidades duplicadas 1' in res['summary']['es']
    assert 'duplicate entities 1' in res['summary']['en']
    md = to_markdown(res)
    assert '# Auditoría del grafo · Graph audit' in md and 'Acme ≈ Acme_Corp' in md


def test_alias_cubre_el_par_duplicado():
    """Un par cubierto por node_id_alias deja de ser hallazgo (es lo que hace
    el merge del navegador con esos ids)."""
    from scripts.audit_graph import audit_snapshot

    snap = _toy_snapshot()
    snap['node_id_alias'] = {'Acme_Corp': 'Acme'}
    assert audit_snapshot(snap)['metrics']['duplicate_entities'] == 0


def test_main_exit_codes(tmp_path):
    from scripts.audit_graph import main

    toy = tmp_path / 'toy.json'
    toy.write_text(json.dumps(_toy_snapshot()), encoding='utf-8')
    assert main(['--format', 'json', '--snapshot', str(toy), '--no-baseline']) == 0
    assert main(['--format', 'md', '--snapshot', str(toy), '--no-baseline', '--strict']) == 1
    # trinquete: la línea base escrita con el toy se respeta a sí misma…
    base = tmp_path / 'base.json'
    assert main(['--snapshot', str(toy), '--baseline', str(base), '--write-baseline']) == 0
    assert main(['--format', 'json', '--snapshot', str(toy), '--baseline', str(base)]) == 0
    # …y un grafo que empeora (un huérfano más) falla
    peor = _toy_snapshot()
    peor['nodes'].append({'id': 'Otro', 'label': 'Otro', 'cat': 'fabless', 'sector': 'diseno'})
    toy2 = tmp_path / 'toy2.json'
    toy2.write_text(json.dumps(peor), encoding='utf-8')
    assert main(['--format', 'json', '--snapshot', str(toy2), '--baseline', str(base)]) == 1


# ── (ii) trinquete sobre el snapshot real ───────────────────────────────────

def test_auditoria_no_empeora_respecto_al_baseline():
    """Ninguna categoría RATCHET puede empeorar frente a data/graph_audit_baseline.json.
    Mejorar pasa; si una mejora consciente cambia los números, regenerar con
    `python scripts/audit_graph.py --write-baseline`."""
    from scripts.audit_graph import RATCHET, INFO, audit_snapshot, compare_baseline, load_baseline, load_snapshot

    baseline = load_baseline(BASELINE)
    assert baseline and baseline.get('metrics'), 'falta data/graph_audit_baseline.json'
    assert set(RATCHET) <= set(baseline['metrics'])
    res = audit_snapshot(load_snapshot(SNAPSHOT))
    assert set(INFO) <= set(res['info'])
    cmp = compare_baseline(res, baseline)
    assert cmp['ok'], f"la auditoría EMPEORA frente a la línea base: {cmp['worse']}"
    # el snapshot real no tiene triplas repetidas (el merge dedupa por (s,t,type)) ni tipos fuera de vocabulario
    assert res['metrics']['duplicate_links'] == 0
    assert res['metrics']['bad_vocab'] == 0
