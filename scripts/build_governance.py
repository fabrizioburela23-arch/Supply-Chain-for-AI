#!/usr/bin/env python3
"""scripts/build_governance.py — mantiene governance/manifest.json (docs/INFRA_OPERATIVA.md §5.1-§5.3; paso 9).

    python scripts/build_governance.py            # = --check: ¿manifest al día? ¿espejos iguales? ¿semver honesto?
    python scripts/build_governance.py --write    # reescribe manifest.json desde los archivos (y los generados)
    python scripts/build_governance.py --write --release-semver 1.1.0

Qué revisa (falla con código 1 y la lista de problemas):
  · cada governance/artifacts/<id>@<semver>.json: forma, nombre, hash (sha256 del JSON canónico de
    {id, semver, kind, params[, deprecated]}) igual al del manifiesto; NINGÚN archivo ya listado cambió de
    contenido con la misma versión (un cambio = archivo NUEVO con otra versión: el registro solo crece);
  · el release del manifiesto = la versión más alta de cada artefacto, salvo las `"activation": "pin"` (un MAJOR que
    solo entra en vigor cuando Fabrizio lo activa con PIN: queda disponible); release_hash = sha256({id: hash});
  · lint de semver (`gov.semver_matches_diff`): un 'patch' no cambia ningún parámetro; un 'minor' solo AGREGA
    claves; quitar o cambiar un número o un conjunto exige 'major'; el salto de versión debe ser del tamaño que
    declara change_kind; 'initial' (o sin change_kind) solo para la primera versión de cada artefacto;
  · espejos (mientras el cliente no lea /api/governance/active): kernel.params.rel_weights = pesos de
    ontology/vocabulary.json; ledger.kinds = core/decisions.KINDS; ontology.schema.vocabulary_sha256 = sha del
    vocabulario; ontology.shapes = governance/shapes/compiled.ir.json (ir_hash y contenido).

Solo biblioteca estándar (+ el propio repo). Sin red, sin base, sin IA.
"""
import argparse
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core import governance as G  # noqa: E402
from core import governance_lint as GL  # noqa: E402

IR_PATH = os.path.join(ROOT, 'governance', 'shapes', 'compiled.ir.json')
# artefactos GENERADOS desde otra fuente del repo: --write los regenera (si la fuente cambió hay que subir versión)
GENERATED = ('ledger.kinds', 'ontology.schema', 'ontology.shapes')


def _vocab_sha():
    with open(os.path.join(ROOT, 'ontology', 'vocabulary.json'), 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _ir():
    try:
        with open(IR_PATH, encoding='utf-8') as fh:
            return json.load(fh)
    except FileNotFoundError:
        return None


def expected_generated(aid):
    """Parámetros que DEBE tener un artefacto generado según su fuente de hoy (o None si no aplica)."""
    if aid == 'ledger.kinds':
        from core import decisions
        return {'kinds': sorted(decisions.KINDS), 'sync_prefixes': list(decisions.SYNC_PREFIXES)}
    if aid == 'ontology.schema':
        from ontology import vocabulary as vocab
        return {'vocabulary_file': 'ontology/vocabulary.json', 'vocabulary_sha256': _vocab_sha(),
                'vocabulary_version': vocab.load().get('version', 1)}
    if aid == 'ontology.shapes':
        ir = _ir()
        if ir is None:
            return None
        return {'ir_hash': ir['ir_hash'], 'source_sha': ir['source_sha'], 'ir': ir}
    return None


def mirror_problems(latest):
    probs = []
    kp = latest.get('kernel.params')
    if kp is not None:
        from ontology import vocabulary as vocab
        vw = vocab.relation_weights()
        if dict(kp['params'].get('rel_weights') or {}) != dict(vw):
            probs.append('kernel.params.rel_weights ≠ pesos de ontology/vocabulary.json (espejo): '
                         f'{kp["params"].get("rel_weights")} vs {vw}')
    for aid in GENERATED:
        doc = latest.get(aid)
        exp = expected_generated(aid)
        if doc is None or exp is None:
            continue
        if doc['params'] != exp:
            probs.append(f'{aid}@{doc["semver"]} no refleja su fuente de hoy: crea {aid}@<versión nueva>.json '
                         '(scripts/build_governance.py --bump ' + aid + '=<semver>:<patch|minor|major>)')
    return probs


# el lint vive en core/governance_lint.py (bilingüe; lo usa también la propuesta hecha en la app con PIN, paso 25)
_diff_kind = GL.diff_kind
_bump_matches = GL.bump_matches


def semver_problems(docs):
    """Textos (es) de los problemas semver — core.governance_lint.semver_problems los da bilingües."""
    return [p['es'] for p in GL.semver_problems(docs)]


def releasable(docs):
    """Las versiones que pueden entrar en el release PROPUESTO del repositorio: todas menos las marcadas
    `"activation": "pin"` (un MAJOR que solo entra en vigor cuando Fabrizio lo activa con su PIN en el 🩺 —
    core.governance.activate; hasta entonces queda 'disponible' y el release propuesto conserva la versión anterior)."""
    return {k: d for k, d in docs.items() if d.get('activation') != 'pin'}


def build_manifest(docs, release_semver):
    latest = G.latest_per_id(releasable(docs))
    arts = {aid: {'semver': d['semver'], 'hash': G.artifact_hash(d), 'file': f'artifacts/{aid}@{d["semver"]}.json'}
            for aid, d in sorted(latest.items())}
    return {
        'schema': G.SCHEMA,
        '_doc': ('GENERADO por scripts/build_governance.py --write: no editar a mano. El release del repositorio es '
                 'una PROPUESTA; manda el aprobado en la base (core/governance.py).'),
        'release': {'semver': release_semver, 'release_hash': G.release_hash_of({a: v['hash'] for a, v in arts.items()}),
                    'artifacts': arts},
        'available': [dict({'id': aid, 'semver': sv, 'hash': G.artifact_hash(d), 'change_kind': d.get('change_kind'),
                            'file': f'artifacts/{aid}@{sv}.json'}, **({'activation': d['activation']}
                                                                     if d.get('activation') else {}))
                      for (aid, sv), d in sorted(docs.items())],
    }


def _dump(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=False) + '\n'


def check(verbose=True):
    probs = []
    try:
        docs = G.scan_repo()
    except G.GovernanceError as e:
        return [str(e)]
    try:
        man = G.load_manifest()
    except FileNotFoundError:
        return ['falta governance/manifest.json: corre scripts/build_governance.py --write']
    listed = {(a['id'], a['semver']): a['hash'] for a in man.get('available') or []}
    for key, doc in docs.items():
        h = G.artifact_hash(doc)
        if key in listed and listed[key] != h:
            probs.append(f'{key[0]}@{key[1]} CAMBIÓ de contenido con la misma versión: el registro solo crece — '
                         'restaura el archivo y crea uno con versión nueva')
        elif key not in listed:
            probs.append(f'{key[0]}@{key[1]} no está en manifest.json: corre scripts/build_governance.py --write')
    for key in listed:
        if key not in docs:
            probs.append(f'manifest.json lista {key[0]}@{key[1]} y el archivo no existe (el registro solo crece)')
    exp = build_manifest(docs, (man.get('release') or {}).get('semver', '1.0.0'))
    if exp['release'] != man.get('release'):
        probs.append('el release de manifest.json no es el de los archivos: corre scripts/build_governance.py --write')
    probs += semver_problems(docs)
    probs += mirror_problems(G.latest_per_id(docs))
    probs += GL.tunables_problems(G.latest_per_id(docs))
    if verbose:
        for p in probs:
            print('✗', p)
        if not probs:
            print(f"✓ gobernanza al día: release {exp['release']['semver']} {exp['release']['release_hash'][:12]} "
                  f"({len(exp['release']['artifacts'])} artefactos)")
    return probs


def bump(spec, changelog_es, changelog_en):
    """--bump id=semver:kind → archivo nuevo de un artefacto GENERADO con los parámetros de su fuente de hoy."""
    aid, rest = spec.split('=', 1)
    sv, ck = rest.split(':', 1)
    if aid not in GENERATED:
        raise SystemExit(f'--bump solo para artefactos generados ({", ".join(GENERATED)}); los demás se editan a mano')
    docs = G.scan_repo()
    prev = G.latest_per_id(docs).get(aid)
    params = expected_generated(aid)
    if params is None:
        raise SystemExit(f'{aid}: su fuente no existe todavía')
    kind = {'ledger.kinds': 'vocabulary', 'ontology.schema': 'schema', 'ontology.shapes': 'shapes'}[aid]
    doc = {'id': aid, 'semver': sv, 'kind': kind, 'change_kind': ck if prev else 'initial',
           'parent': f"{aid}@{prev['semver']}" if prev else None, 'params': params,
           'changelog_es': changelog_es or f'{aid} regenerado desde su fuente.',
           'changelog_en': changelog_en or f'{aid} regenerated from its source.'}
    path = G.artifact_path(aid, sv)
    if os.path.exists(path):
        raise SystemExit(f'{path} ya existe (el registro solo crece)')
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(_dump(doc))
    print('escrito', os.path.relpath(path, ROOT))


def write(release_semver=None):
    docs = G.scan_repo()
    try:
        man = G.load_manifest()
    except FileNotFoundError:
        man = {}
    listed = {(a['id'], a['semver']): a['hash'] for a in man.get('available') or []}
    changed = [f'{k[0]}@{k[1]}' for k, d in docs.items() if k in listed and listed[k] != G.artifact_hash(d)]
    if changed:
        raise SystemExit('✗ estos artefactos cambiaron con la MISMA versión (el registro solo crece): '
                         + ', '.join(changed))
    rs = release_semver or (man.get('release') or {}).get('semver') or '1.0.0'
    new = build_manifest(docs, rs)
    with open(G.MANIFEST_PATH, 'w', encoding='utf-8') as fh:
        fh.write(_dump(new))
    G._STATE['repo'] = None
    print(f"manifest.json: release {rs} {new['release']['release_hash'][:12]} ({len(new['release']['artifacts'])} "
          'artefactos)')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--release-semver')
    ap.add_argument('--bump', help='id=semver:patch|minor|major (solo artefactos generados)')
    ap.add_argument('--changelog-es', default='')
    ap.add_argument('--changelog-en', default='')
    a = ap.parse_args(argv)
    if a.bump:
        bump(a.bump, a.changelog_es, a.changelog_en)
    if a.write:
        write(a.release_semver)
    return 1 if check() else 0


if __name__ == '__main__':
    sys.exit(main())
