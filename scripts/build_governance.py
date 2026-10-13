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


def _diff_kind(old, new):
    """'none' | 'add' (solo claves nuevas) | 'change' (algo quitado o distinto)."""
    if old == new:
        return 'none'
    if isinstance(old, dict) and isinstance(new, dict):
        if any(k not in new for k in old):
            return 'change'
        kinds = [_diff_kind(old[k], new[k]) for k in old]
        if 'change' in kinds:
            return 'change'
        return 'add'
    return 'change'


def _bump_matches(ck, psv, sv):
    """¿El salto de versión parent→sv es del tamaño que declara change_kind? major sube X; minor sube Y con el
    mismo X; patch sube Z con el mismo X.Y."""
    p, n = G.semver_key(psv), G.semver_key(sv)
    if ck == 'major':
        return n[0] > p[0]
    if ck == 'minor':
        return n[0] == p[0] and n[1] > p[1]
    if ck == 'patch':
        return n[:2] == p[:2] and n[2] > p[2]
    return True


def semver_problems(docs):
    probs = []
    first = {}                                      # id → semver más baja (la única que puede ser 'initial')
    for (aid, sv) in docs:
        if aid not in first or G.semver_key(sv) < G.semver_key(first[aid]):
            first[aid] = sv
    for (aid, sv), doc in sorted(docs.items()):
        ck = doc.get('change_kind') or 'initial'
        par = doc.get('parent')
        if ck == 'initial':
            # 'initial' (también el valor por omisión) solo vale para la PRIMERA versión de un artefacto: antes
            # cualquier archivo nuevo sin change_kind se saltaba todo el lint (un 1.0.1 que cambiaba el kernel
            # pasaba --check)
            if sv != first[aid] or par:
                probs.append(f'{aid}@{sv}: solo la primera versión puede ser "initial"; declara change_kind '
                             '(patch|minor|major) y "parent"')
            continue
        if not par:
            probs.append(f'{aid}@{sv}: change_kind={ck} exige "parent" (<id>@<semver>)')
            continue
        try:
            paid, psv = par.split('@', 1)
        except ValueError:
            probs.append(f'{aid}@{sv}: parent inválido {par!r}')
            continue
        pdoc = docs.get((paid, psv))
        if pdoc is None or paid != aid:
            probs.append(f'{aid}@{sv}: el parent {par} no existe')
            continue
        if G.semver_key(sv) <= G.semver_key(psv):
            probs.append(f'{aid}@{sv}: la versión debe ser mayor que la del parent {psv}')
        elif ck in ('patch', 'minor', 'major') and not _bump_matches(ck, psv, sv):
            probs.append(f'{aid}@{sv}: change_kind={ck} no coincide con el salto {psv} → {sv} (major sube X, '
                         'minor sube Y con el mismo X, patch sube Z con el mismo X.Y)')
        d = _diff_kind(pdoc['params'], doc['params'])
        if ck == 'patch' and d != 'none':
            probs.append(f'{aid}@{sv}: un PATCH no puede cambiar parámetros (gov.semver_matches_diff); usa major')
        if ck == 'minor' and d == 'change':
            probs.append(f'{aid}@{sv}: un MINOR solo agrega claves; cambiar o quitar un número/conjunto es MAJOR')
        if ck not in ('patch', 'minor', 'major'):
            probs.append(f'{aid}@{sv}: change_kind inválido {ck!r}')
    return probs


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
