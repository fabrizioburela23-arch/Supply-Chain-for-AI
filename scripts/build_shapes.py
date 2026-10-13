#!/usr/bin/env python3
"""scripts/build_shapes.py — compila las formas SHACL a IR (docs/INFRA_OPERATIVA.md §3.3; paso 10).

    python scripts/build_shapes.py            # = --check: ¿vocab.generated.ttl y compiled.ir.json al día?
    python scripts/build_shapes.py --write    # regenera vocab.generated.ttl y compiled.ir.json

  1. Regenera governance/shapes/vocab.generated.ttl (listas sh:in de tipos de objeto, relaciones y kinds de
     decisión) desde ontology/vocabulary.json y core/decisions.KINDS. NUNCA se edita a mano.
  2. Lee los TTL con rdflib (solo aquí y en las pruebas: requirements-dev.txt) y compila cada forma a un IR
     genérico: {shapes:[{iri, target, props:[{iri, rule, severity, path, constraints:[{kind, value}], msg_es,
     msg_en}], sparql:[{iri, rule, severity, impl, select, msg_es, msg_en}]}]}.
  3. Meta-formas (en Python): toda forma de propiedad y toda forma SPARQL tiene sh:name, khs:rule, sh:severity y
     sh:message en es y en; ninguna consulta usa VALUES/MINUS/SERVICE (pySHACL los rechaza); toda impl existe en
     core/gates/rules.py.
  4. ir_hash = sha256 del IR canónico SIN source_sha (hash SEMÁNTICO: un cambio de formato no lo mueve);
     source_sha = sha256 de los TTL (nombre + bytes). `--check` sin rdflib verifica al menos source_sha y el
     vocabulario generado (el compilador completo corre en CI, donde rdflib está instalado).

El IR compilado entra al registro de gobernanza como el artefacto `ontology.shapes` (scripts/build_governance.py
--bump ontology.shapes=<semver>:<tipo> si cambió).
"""
import argparse
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

SHAPES_DIR = os.path.join(ROOT, 'governance', 'shapes')
IR_PATH = os.path.join(SHAPES_DIR, 'compiled.ir.json')
VOCAB_TTL = os.path.join(SHAPES_DIR, 'vocab.generated.ttl')
SOURCES = ('prefixes.ttl', 'vocab.generated.ttl', 'link.ttl', 'object.ttl', 'factor.ttl', 'action.ttl',
           'decision.ttl', 'order.ttl', 'committee.ttl')
FORBIDDEN_SPARQL = re.compile(r'\b(VALUES|MINUS|SERVICE)\b', re.I)
CONSTRAINT_ORDER = ('datatype', 'in', 'minInclusive', 'maxInclusive', 'minExclusive', 'maxExclusive', 'minCount',
                    'maxCount', 'pattern', 'lessThan', 'lessThanOrEquals', 'disjoint', 'class')


# ── 1. vocabulario generado (sin rdflib) ─────────────────────────────────────
def _ttl_list(values):
    return '( ' + ' '.join(json.dumps(v, ensure_ascii=False) for v in values) + ' )'


def vocab_ttl():
    from core import decisions
    from ontology import vocabulary as vocab
    rels = sorted(vocab.relation_types_all())
    objs = sorted(vocab.object_types())
    kinds = sorted(decisions.KINDS)
    return f'''# governance/shapes/vocab.generated.ttl — GENERADO por scripts/build_shapes.py --write. NO EDITAR A MANO.
# Fuente: ontology/vocabulary.json (tipos de objeto y de relación) y core/decisions.KINDS (artefacto ledger.kinds).
@prefix sh:   <http://www.w3.org/ns/shacl#> .
@prefix kh:   <https://khipus.ai/ont#> .
@prefix khs:  <https://khipus.ai/shapes#> .
@prefix khr:  <https://khipus.ai/rule#> .

khs:LinkRelInVocab a sh:PropertyShape ;
  sh:path kh:relType ; sh:minCount 1 ; sh:maxCount 1 ;
  sh:in {_ttl_list(rels)} ;
  sh:name "relación del vocabulario" ; khs:rule khr:link.rel_in_vocab ; sh:severity sh:Violation ;
  sh:message "La relación «{{value}}» no está en ontology/vocabulary.json."@es ,
             "The relation \\"{{value}}\\" is not in ontology/vocabulary.json."@en .

khs:ObjectTypeInVocab a sh:PropertyShape ;
  sh:path kh:type ; sh:minCount 1 ; sh:maxCount 1 ;
  sh:in {_ttl_list(objs)} ;
  sh:name "tipo de objeto del vocabulario" ; khs:rule khr:object.type_in_vocab ; sh:severity sh:Warning ;
  sh:message "El tipo «{{value}}» no está en ontology/vocabulary.json (se excluye del grafo en silencio)."@es ,
             "The type \\"{{value}}\\" is not in ontology/vocabulary.json (it is silently left out of the graph)."@en .

khs:DecisionKindInVocab a sh:PropertyShape ;
  sh:path kh:kind ; sh:minCount 1 ; sh:maxCount 1 ;
  sh:in {_ttl_list(kinds)} ;
  sh:name "tipo de decisión del vocabulario" ; khs:rule khr:decision.kind_in_vocab ; sh:severity sh:Violation ;
  sh:message "El tipo de decisión «{{value}}» no está en el vocabulario cerrado (ledger.kinds)."@es ,
             "The decision kind \\"{{value}}\\" is not in the closed vocabulary (ledger.kinds)."@en .
'''


def source_sha():
    h = hashlib.sha256()
    for name in SOURCES:
        with open(os.path.join(SHAPES_DIR, name), 'rb') as fh:
            h.update(name.encode() + b'\0' + fh.read() + b'\0')
    return h.hexdigest()


# ── 2-3. compilación (rdflib) ────────────────────────────────────────────────
def shapes_graph():
    from rdflib import Graph
    g = Graph()
    for name in SOURCES:
        g.parse(os.path.join(SHAPES_DIR, name), format='turtle')
    return g


def compile_ir(g=None):
    from rdflib import RDF, Literal, URIRef
    from rdflib.collection import Collection
    from rdflib.namespace import SH

    from core.gates.focus import KHS, compact
    from core.gates.rules import RULES
    g = g if g is not None else shapes_graph()
    KHS_RULE, KHS_IMPL = URIRef(KHS + 'rule'), URIRef(KHS + 'impl')
    probs = []

    def one(s, p, what):
        vs = list(g.objects(s, p))
        if len(vs) != 1:
            probs.append(f'{compact(s)}: {what} debe tener exactamente un valor (tiene {len(vs)})')
            return None
        return vs[0]

    def msgs(s):
        out = {}
        for m in g.objects(s, SH.message):
            if isinstance(m, Literal) and m.language in ('es', 'en'):
                out[m.language] = str(m)
        for lang in ('es', 'en'):
            if lang not in out:
                probs.append(f'{compact(s)}: falta sh:message@{lang}')
        return out

    def lit(v):
        if isinstance(v, Literal):
            p = v.toPython()
            if isinstance(p, bool):
                return p
            if isinstance(p, (int, float)) or type(p).__name__ == 'Decimal':
                return float(p) if not float(p).is_integer() else int(p)
            return str(v)
        return compact(v)

    shapes = []
    for shp in sorted(set(g.subjects(RDF.type, SH.NodeShape)), key=str):
        target = one(shp, SH.targetClass, 'sh:targetClass')
        if target is None:
            continue
        entry = {'iri': compact(shp), 'target': compact(target), 'props': [], 'sparql': []}
        for ps in sorted(g.objects(shp, SH.property), key=str):
            if not isinstance(ps, URIRef):
                probs.append(f'{compact(shp)}: las formas de propiedad deben tener IRI (para la regla en el reporte)')
                continue
            for need, pred in (('sh:name', SH.name), ('khs:rule', KHS_RULE), ('sh:severity', SH.severity)):
                one(ps, pred, need)
            path = one(ps, SH.path, 'sh:path')
            if path is not None and not isinstance(path, URIRef):
                probs.append(f'{compact(ps)}: solo rutas simples (un predicado)')
            cons = []
            for kind in CONSTRAINT_ORDER:
                for v in g.objects(ps, getattr(SH, kind)):
                    if kind == 'in':
                        cons.append({'kind': 'in', 'value': [lit(x) for x in Collection(g, v)]})
                    elif kind == 'pattern':
                        fl = g.value(ps, SH.flags)
                        cons.append({'kind': 'pattern', 'value': str(v), 'flags': str(fl) if fl else ''})
                    else:
                        cons.append({'kind': kind, 'value': lit(v)})
            known = {SH.path, SH.name, SH.message, SH.severity, SH.flags, SH.description, RDF.type, KHS_RULE} | \
                {getattr(SH, k) for k in CONSTRAINT_ORDER}
            for p in set(g.predicates(ps)):
                if p not in known:
                    probs.append(f'{compact(ps)}: componente no soportado por el compilador: {compact(p)}')
            m = msgs(ps)
            entry['props'].append({'iri': compact(ps), 'rule': compact(g.value(ps, KHS_RULE) or ''),
                                   'severity': compact(g.value(ps, SH.severity) or SH.Violation),
                                   'path': compact(path) if path is not None else None, 'constraints': cons,
                                   'name': str(g.value(ps, SH.name) or ''), 'msg_es': m.get('es'),
                                   'msg_en': m.get('en')})
        sparqls = list(g.objects(shp, SH.sparql))
        if sparqls:
            for need, pred in (('sh:name', SH.name), ('khs:rule', KHS_RULE), ('sh:severity', SH.severity)):
                one(shp, pred, need)
        for sp in sparqls:
            sel = str(one(sp, SH.select, 'sh:select') or '')
            if FORBIDDEN_SPARQL.search(sel):
                probs.append(f'{compact(shp)}: VALUES/MINUS/SERVICE prohibidos en SHACL-SPARQL (pySHACL los rechaza)')
            impl = str(one(sp, KHS_IMPL, 'khs:impl') or '')
            if impl not in RULES:
                probs.append(f'{compact(shp)}: impl {impl!r} sin registrar en core/gates/rules.py')
            m = msgs(sp)
            entry['sparql'].append({'iri': compact(shp), 'rule': compact(g.value(shp, KHS_RULE) or ''),
                                    'severity': compact(g.value(shp, SH.severity) or SH.Violation), 'impl': impl,
                                    'select': ' '.join(sel.split()), 'name': str(g.value(shp, SH.name) or ''),
                                    'msg_es': m.get('es'), 'msg_en': m.get('en')})
        if entry['props'] or entry['sparql']:
            shapes.append(entry)
    from core.gates.engine import ir_canonical_hash
    ir = {'schema': 'shapes-ir/1', 'shapes': shapes}
    rules = sorted({p['rule'] for s in shapes for p in s['props']} | {q['rule'] for s in shapes for q in s['sparql']})
    ir['rules'] = rules
    ir['ir_hash'] = ir_canonical_hash(ir)
    ir['source_sha'] = source_sha()
    return ir, probs


def _read(path):
    try:
        with open(path, encoding='utf-8') as fh:
            return fh.read()
    except FileNotFoundError:
        return None


def check(verbose=True):
    probs = []
    if _read(VOCAB_TTL) != vocab_ttl():
        probs.append('vocab.generated.ttl no refleja el vocabulario de hoy: corre scripts/build_shapes.py --write')
    cur = _read(IR_PATH)
    if cur is None:
        probs.append('falta compiled.ir.json: corre scripts/build_shapes.py --write')
    else:
        cur = json.loads(cur)
        if cur.get('source_sha') != source_sha():
            probs.append('los TTL cambiaron y compiled.ir.json no: corre scripts/build_shapes.py --write')
        try:
            import rdflib  # noqa: F401
            have_rdflib = True
        except ImportError:
            have_rdflib = False
        if have_rdflib:
            ir, p2 = compile_ir()
            probs += p2
            if ir != cur:
                probs.append('compiled.ir.json no es lo que compilan los TTL: corre scripts/build_shapes.py --write')
        elif verbose:
            print('· sin rdflib: solo se comprobó source_sha (el compilador completo corre en CI)')
    if verbose:
        for p in probs:
            print('✗', p)
        if not probs:
            print(f"✓ formas al día: ir_hash {cur['ir_hash'][:12]} ({len(cur['rules'])} reglas)")
    return probs


def write():
    with open(VOCAB_TTL, 'w', encoding='utf-8') as fh:
        fh.write(vocab_ttl())
    ir, probs = compile_ir()
    if probs:
        for p in probs:
            print('✗', p)
        raise SystemExit(1)
    with open(IR_PATH, 'w', encoding='utf-8') as fh:
        fh.write(json.dumps(ir, ensure_ascii=False, indent=1, sort_keys=True) + '\n')
    print(f"compiled.ir.json: ir_hash {ir['ir_hash'][:12]} · {len(ir['rules'])} reglas · {len(ir['shapes'])} formas")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args(argv)
    if a.write:
        write()
    return 1 if check() else 0


if __name__ == '__main__':
    sys.exit(main())
