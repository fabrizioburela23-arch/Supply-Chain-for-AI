"""tests/test_gates_conformance.py — INFRA_OPERATIVA paso 10: el evaluador COMPILADO == pySHACL (oráculo).

docs/INFRA_OPERATIVA.md §3.3 punto 5. pySHACL + rdflib viven SOLO en requirements-dev.txt (CI los instala; fuera de
CI la prueba se salta sola; EN CI una guardia exige que estén). Garantiza:
  (a) un accesorio de UN SOLO defecto por regla (31 reglas + casos limpios): exactamente esa regla, en los dos;
  (b) ≥ 1.000 focos ALEATORIOS (semilla derivada del ir_hash, 5 tipos de foco, valores buenos y malos, tipos
      mezclados) → 0 diferencias en conforms y en el conjunto (foco, regla, severidad);
  (c) pySHACL ejecuta el TEXTO SPARQL real del TTL: cada impl de core/gates/rules.py queda verificada contra él;
  (d) la severidad propia khs:RequiresApproval pasa tal cual por pySHACL;
  (e) las meta-formas (governance/shapes/meta.ttl) aceptan el grafo de formas.
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

IN_CI = (os.getenv('CI') or os.getenv('GITHUB_ACTIONS') or '').lower() in ('1', 'true', 'yes')
N_RANDOM = int(os.getenv('GATES_CONFORMANCE_N') or 1000)
BATCH = 25

try:
    import pyshacl  # noqa: F401
    import rdflib  # noqa: F401
    HAVE = True
except ImportError:
    HAVE = False


def test_guardia_ci_exige_pyshacl():
    if IN_CI:
        assert HAVE, 'en CI pyshacl y rdflib deben estar instalados (pip install -r requirements-dev.txt)'


pytestmark_skip = pytest.mark.skipif(not HAVE, reason='pyshacl/rdflib no instalados (requirements-dev.txt)')


@pytest.fixture(scope='module')
def oracle():
    if not HAVE:
        pytest.skip('pyshacl/rdflib no instalados')
    from rdflib import URIRef

    from core.gates import engine
    from core.gates import focus as F
    from scripts import build_shapes as BS
    sg = BS.shapes_graph()
    comp = engine.load(force=True)
    assert comp is not None, engine.state()
    return {'sg': sg, 'comp': comp, 'rule': URIRef(F.KHS + 'rule')}


def _engine_set(o, triples):
    from core.gates import engine
    from core.gates import focus as F
    return {(str(t), s['rule'], F.expand(s['severity'])) for t, _k, s, _v, _l in engine.run(o['comp'], triples)}


def _shacl(o, triples):
    import pyshacl
    from rdflib import RDF
    from rdflib.namespace import SH

    from core.gates import focus as F
    g = F.to_rdflib(triples)
    conforms, rg, _ = pyshacl.validate(g, shacl_graph=o['sg'], inference='none', inplace=True,
                                       allow_warnings=False, abort_on_first=False)
    out = set()
    for r in rg.subjects(RDF.type, SH.ValidationResult):
        ss = rg.value(r, SH.sourceShape)
        rule = o['sg'].value(ss, o['rule'])
        out.add((str(rg.value(r, SH.focusNode)), F.compact(rule) if rule is not None else F.compact(ss),
                 str(rg.value(r, SH.resultSeverity))))
    return conforms, out


@pytestmark_skip
def test_un_defecto_por_regla(oracle):
    from tests import gates_cases as GC
    seen = set()
    for rule, kind, inp in GC.single_defect_cases():
        t, _f = GC.triples_of(kind, inp)
        eng = _engine_set(oracle, t)
        conforms, sh = _shacl(oracle, t)
        assert eng == sh, (rule, sorted(eng ^ sh))
        assert {x[1] for x in eng} == ({rule} if rule else set()), (rule, sorted(eng))
        assert conforms == (not eng)
        if rule:
            seen.add(rule)
    assert seen == set(oracle['comp'].rules), sorted(set(oracle['comp'].rules) - seen)   # TODAS las reglas


@pytestmark_skip
def test_requires_approval_pasa_tal_cual(oracle):
    from core.gates import focus as F
    from tests import gates_cases as GC
    rule, kind, inp = next(c for c in GC.single_defect_cases() if c[0] == 'khr:action.agent_needs_human')
    _c, sh = _shacl(oracle, GC.triples_of(kind, inp)[0])
    assert {x[2] for x in sh} == {F.KHS + 'RequiresApproval'}


@pytestmark_skip
def test_aleatorio_0_diferencias(oracle):
    from tests import gates_cases as GC
    seed = int(oracle['comp'].ir_hash[:8], 16)
    cases = GC.random_cases(seed, N_RANDOM)
    assert len(cases) >= 1000 or os.getenv('GATES_CONFORMANCE_N')
    diffs, n_results, rules_hit = [], 0, set()
    for i in range(0, len(cases), BATCH):
        triples = []
        for kind, inp in cases[i:i + BATCH]:
            triples += GC.triples_of(kind, inp)[0]
        eng = _engine_set(oracle, triples)
        conforms, sh = _shacl(oracle, triples)
        n_results += len(eng)
        rules_hit |= {x[1] for x in eng}
        if eng != sh or conforms != (not eng):
            diffs.append((i, sorted(eng - sh)[:5], sorted(sh - eng)[:5]))
    print(f'conformidad: {len(cases)} focos aleatorios, {n_results} resultados, {len(rules_hit)} reglas, '
          f'{len(diffs)} diferencias (semilla {seed})')
    assert diffs == []
    assert len(rules_hit) >= 25          # el generador ejercita casi todas las reglas


@pytestmark_skip
def test_meta_formas(oracle):
    import pyshacl
    from rdflib import Graph
    meta = Graph().parse(os.path.join(ROOT, 'governance', 'shapes', 'meta.ttl'), format='turtle')
    conforms, _g, text = pyshacl.validate(oracle['sg'], shacl_graph=meta, inference='none')
    assert conforms, text
