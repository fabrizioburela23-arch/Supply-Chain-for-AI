"""scripts/build_impl_goldens.py — salidas DORADAS de las implementaciones retenidas (core/impls.py; INFRA §5.2, paso 24).

    python scripts/build_impl_goldens.py           # (re)escribe tests/golden/impl_<clave>@<versión>.json
    python scripts/build_impl_goldens.py --check   # falla si alguna salida de hoy no coincide con su dorada

Cada archivo fija, para una implementación y versión, las salidas sobre entradas FIJAS con versiones EXPLÍCITAS de los
artefactos de gobernanza (no "las de hoy"). Si un cambio de código altera una salida dorada NO se regenera el archivo:
nace `@2` en core/impls.py y `@1` se conserva en core/impls_legacy/ (las decisiones viejas se repiten con `@1`).
Sin base, sin red, determinista.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
GOLDEN_DIR = os.path.join(ROOT, 'tests', 'golden')

# artefactos (versión explícita) con que se corre cada caso dorado
CASES = {
    'kernel.propagate': [{'kernel.params': '1.0.0'}, {'kernel.params': '2.0.0'}],
    'nrs.formula': [{'nrs.formula': '1.0.0'}],
    'committee.conviction': [{'policy.committee': '1.0.0'}],
    'committee.quorum': [{'policy.committee': '1.0.0'}],
    'committee.decide': [{'policy.committee': '1.0.0'}],
    'committee.sizing': [{'policy.committee': '1.0.0'}],
    'broker.run_checks': [{'policy.broker_risk': '1.0.0'}],
    'numbers.guard': [{'policy.numbers_guard': '1.0.0'}],
    'gates.eval': [{'ontology.shapes': '5.0.0'}],
}


def path_of(key, version):
    return os.path.join(GOLDEN_DIR, f'impl_{key}@{version}.json')


def compute(key, version):
    from core import impls
    out = []
    for sel in CASES[key]:
        arts = impls.repo_arts(sel)
        res = impls.golden_run(key, version, arts)
        out.append({'artifacts': sel, 'sha': impls.sha(res), 'output': res})
    return {'key': key, 'version': version, 'cases': out}


def main(check=False):
    from core import impls
    bad = []
    for key in impls.GOLDEN_CASES:
        for version in sorted(impls.IMPLS[key]):
            doc = compute(key, version)
            p = path_of(key, version)
            if check:
                try:
                    with open(p, encoding='utf-8') as fh:
                        cur = json.load(fh)
                except FileNotFoundError:
                    bad.append(f'{key}@{version}: falta {os.path.relpath(p, ROOT)}')
                    continue
                if [c['sha'] for c in cur['cases']] != [c['sha'] for c in doc['cases']]:
                    bad.append(f'{key}@{version}: la salida cambió (¿nuevo código? → @{version + 1})')
            else:
                os.makedirs(GOLDEN_DIR, exist_ok=True)
                with open(p, 'w', encoding='utf-8') as fh:
                    json.dump(doc, fh, ensure_ascii=False, indent=1, sort_keys=True)
                    fh.write('\n')
    for b in bad:
        print('✗', b)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(check='--check' in sys.argv))
