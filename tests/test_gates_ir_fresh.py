"""tests/test_gates_ir_fresh.py — INFRA_OPERATIVA paso 10: el IR compilado está AL DÍA con los TTL.

  · governance/shapes/vocab.generated.ttl == lo que genera scripts/build_shapes.py desde ontology/vocabulary.json y
    core/decisions.KINDS (sin rdflib); las listas sh:in del IR == el vocabulario de hoy;
  · compiled.ir.json: source_sha == sha de los TTL (sin rdflib); con rdflib, IR recompilado == archivo;
  · ir_hash semántico correcto; el artefacto `ontology.shapes` del registro de gobernanza lleva ESE IR;
  · toda impl del IR está registrada en core/gates/rules.py y el arranque compila sin error;
  · ninguna consulta usa VALUES/MINUS/SERVICE; todo mensaje existe en ES y EN.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _ir():
    from core.gates import engine
    return engine.read_ir_file()


def test_build_shapes_check():
    from scripts import build_shapes as BS
    assert BS.check(verbose=False) == []


def test_vocabulario_generado_al_dia():
    from scripts import build_shapes as BS
    with open(BS.VOCAB_TTL, encoding='utf-8') as fh:
        assert fh.read() == BS.vocab_ttl()


def test_sh_in_igual_al_vocabulario():
    from core import decisions
    from ontology import vocabulary as vocab
    ins = {}
    for sh in _ir()['shapes']:
        for p in sh['props']:
            for c in p['constraints']:
                if c['kind'] == 'in':
                    ins[p['rule']] = sorted(c['value'])
    assert ins['khr:link.rel_in_vocab'] == sorted(vocab.relation_types_all())
    assert ins['khr:object.type_in_vocab'] == sorted(vocab.object_types())
    assert ins['khr:decision.kind_in_vocab'] == sorted(decisions.KINDS)


def test_hash_semantico_y_artefacto_de_gobernanza():
    from core import governance
    from core.gates import engine
    ir = _ir()
    assert engine.ir_canonical_hash(ir) == ir['ir_hash']
    from scripts import build_shapes as BS
    assert ir['source_sha'] == BS.source_sha()
    art = governance.repo_bundle().artifacts['ontology.shapes']['params']
    assert art['ir'] == ir and art['ir_hash'] == ir['ir_hash'] and art['source_sha'] == ir['source_sha']


def test_impls_registradas_y_carga():
    from core.gates import engine, rules
    ir = _ir()
    impls = {s['impl'] for sh in ir['shapes'] for s in sh['sparql']}
    assert impls and impls <= set(rules.RULES)
    comp = engine.compile_ir(ir)
    assert comp.n_rules == len(ir['rules']) == 31


def test_sin_sparql_prohibido_y_mensajes_bilingues():
    import re
    ir = _ir()
    for sh in ir['shapes']:
        for s in sh['sparql']:
            assert not re.search(r'\b(VALUES|MINUS|SERVICE)\b', s['select'], re.I), s['iri']
            assert s['msg_es'] and s['msg_en'] and s['rule'].startswith('khr:')
        for p in sh['props']:
            assert p['msg_es'] and p['msg_en'] and p['rule'].startswith('khr:')


def test_ir_es_json_canonico_estable():
    with open(os.path.join(ROOT, 'governance', 'shapes', 'compiled.ir.json'), encoding='utf-8') as fh:
        raw = fh.read()
    assert raw == json.dumps(json.loads(raw), ensure_ascii=False, indent=1, sort_keys=True) + '\n'
