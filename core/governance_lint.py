"""core/governance_lint.py — EL lint de los artefactos de gobernanza (docs/INFRA_OPERATIVA.md §5.2; pasos 9 y 25).

Una sola implementación para los dos caminos por los que llega una versión nueva:
  · un archivo del repositorio (scripts/build_governance.py --check, en las pruebas y en CI), y
  · una PROPUESTA hecha dentro de la app con PIN (core/governance_flow.propose, 🩺 ⚖ Gobernanza → «Proponer cambio»).

Cada problema es {code, es, en} (bilingüe: la app lo muestra tal cual); el script imprime el texto en español.

    semver_problems(docs)            honestidad semver (gov.semver_matches_diff): un 'patch' no cambia parámetros, un
                                     'minor' solo AGREGA claves, cambiar/quitar un número o un conjunto es 'major', el
                                     salto de versión es del tamaño declarado, 'initial' solo para la primera versión
    schema_problems(aid, base, new)  esquema de los parámetros afinables desde la app (governance/tunables.json:
                                     tipo, mínimo y máximo por clave; relaciones entre claves) — lo que NO está en la
                                     tabla no se puede cambiar desde la app (solo por PR)
    mirror_problems(aid, params)     espejos: kernel.params.rel_weights = pesos de ontology/vocabulary.json;
                                     nrs.formula tiene su espejo en app.html (computeNRS) → solo por PR

Solo biblioteca estándar (+ el propio repo). Sin red, sin base, sin IA.
"""
import json
import os

from core import governance as G

TUNABLES_PATH = os.path.join(G.GOV_DIR, 'tunables.json')
# artefactos con un ESPEJO fuera del registro: un cambio hecho en la app rompería la paridad → solo por PR
APP_FORBIDDEN = {
    'nrs.formula': ('la fórmula NRS tiene un espejo en app.html (computeNRS) y en las pruebas de paridad: cámbiala '
                    'con un PR que actualice los dos lados',
                    'the NRS formula has a mirror in app.html (computeNRS) and in the parity tests: change it with a '
                    'PR that updates both sides'),
    'policy.gates': ('las puertas (sombra/bloqueo) solo cambian con una versión del repositorio activada con PIN '
                     '(paso 11)',
                     'the gates (shadow/block) only change with a repository version activated with the PIN '
                     '(step 11)'),
}


def P(code, es, en):
    return {'code': code, 'es': es, 'en': en}


# ── honestidad semver ────────────────────────────────────────────────────────
def diff_kind(old, new):
    """'none' | 'add' (solo claves nuevas) | 'change' (algo quitado o distinto)."""
    if old == new:
        return 'none'
    if isinstance(old, dict) and isinstance(new, dict):
        if any(k not in new for k in old):
            return 'change'
        kinds = [diff_kind(old[k], new[k]) for k in old]
        if 'change' in kinds:
            return 'change'
        return 'add'
    return 'change'


def bump_matches(ck, psv, sv):
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


def needed_kind(old_params, new_params):
    """El change_kind MÍNIMO honesto para pasar de old a new: None (nada cambia), 'minor' (solo agrega), 'major'."""
    d = diff_kind(old_params, new_params)
    return None if d == 'none' else ('minor' if d == 'add' else 'major')


def next_semver(versions, parent_semver, change_kind):
    """La siguiente versión libre del tamaño declarado sobre `parent_semver`, por encima de TODAS las existentes con
    el mismo prefijo (repositorio + base): major → (max X)+1.0.0; minor → X.(max Y)+1.0; patch → X.Y.(max Z)+1."""
    px, py, _pz = G.semver_key(parent_semver)
    keys = [G.semver_key(v) for v in versions]
    if change_kind == 'major':
        return f'{max([k[0] for k in keys] + [px]) + 1}.0.0'
    if change_kind == 'minor':
        return f'{px}.{max([k[1] for k in keys if k[0] == px] + [py]) + 1}.0'
    return f'{px}.{py}.{max([k[2] for k in keys if k[:2] == (px, py)] + [0]) + 1}'


def semver_problems(docs):
    """[{code, es, en}] de un conjunto {(id, semver): doc} (el del repositorio, o el repositorio + la base + la
    propuesta)."""
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
                probs.append(P('initial_not_first',
                               f'{aid}@{sv}: solo la primera versión puede ser "initial"; declara change_kind '
                               '(patch|minor|major) y "parent"',
                               f'{aid}@{sv}: only the first version may be "initial"; declare change_kind '
                               '(patch|minor|major) and "parent"'))
            continue
        if not par:
            probs.append(P('no_parent', f'{aid}@{sv}: change_kind={ck} exige "parent" (<id>@<semver>)',
                           f'{aid}@{sv}: change_kind={ck} requires "parent" (<id>@<semver>)'))
            continue
        try:
            paid, psv = par.split('@', 1)
        except ValueError:
            probs.append(P('bad_parent', f'{aid}@{sv}: parent inválido {par!r}', f'{aid}@{sv}: invalid parent {par!r}'))
            continue
        pdoc = docs.get((paid, psv))
        if pdoc is None or paid != aid:
            probs.append(P('parent_missing', f'{aid}@{sv}: el parent {par} no existe',
                           f'{aid}@{sv}: parent {par} does not exist'))
            continue
        if G.semver_key(sv) <= G.semver_key(psv):
            probs.append(P('not_greater', f'{aid}@{sv}: la versión debe ser mayor que la del parent {psv}',
                           f'{aid}@{sv}: the version must be greater than the parent {psv}'))
        elif ck in ('patch', 'minor', 'major') and not bump_matches(ck, psv, sv):
            probs.append(P('bump_mismatch',
                           f'{aid}@{sv}: change_kind={ck} no coincide con el salto {psv} → {sv} (major sube X, '
                           'minor sube Y con el mismo X, patch sube Z con el mismo X.Y)',
                           f'{aid}@{sv}: change_kind={ck} does not match the jump {psv} → {sv} (major raises X, '
                           'minor raises Y with the same X, patch raises Z with the same X.Y)'))
        d = diff_kind(pdoc['params'], doc['params'])
        if ck == 'patch' and d != 'none':
            probs.append(P('patch_changes',
                           f'{aid}@{sv}: un PATCH no puede cambiar parámetros (gov.semver_matches_diff); usa major',
                           f'{aid}@{sv}: a PATCH cannot change parameters (gov.semver_matches_diff); use major'))
        if ck == 'minor' and d == 'change':
            probs.append(P('minor_changes',
                           f'{aid}@{sv}: un MINOR solo agrega claves; cambiar o quitar un número/conjunto es MAJOR',
                           f'{aid}@{sv}: a MINOR only adds keys; changing or removing a number/set is MAJOR'))
        if ck not in ('patch', 'minor', 'major'):
            probs.append(P('bad_kind', f'{aid}@{sv}: change_kind inválido {ck!r}', f'{aid}@{sv}: invalid change_kind {ck!r}'))
    return probs


# ── esquema de lo afinable desde la app ─────────────────────────────────────
_TUN = {'mtime': None, 'data': None}


def tunables():
    """governance/tunables.json → {artifact_id: {ruta: {type, min, max, step?, label_es/en, help_es/en}}, _relations}."""
    try:
        mt = os.path.getmtime(TUNABLES_PATH)
    except OSError:
        return {}
    if _TUN['mtime'] != mt:
        with open(TUNABLES_PATH, encoding='utf-8') as fh:
            _TUN['data'] = json.load(fh)
        _TUN['mtime'] = mt
    return _TUN['data'] or {}


def get_path(params, path):
    cur = params
    for part in str(path).split('.'):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def set_path(params, path, value):
    parts = str(path).split('.')
    cur = params
    for part in parts[:-1]:
        cur = cur[part]
    cur[parts[-1]] = value


def _flat(params, prefix=''):
    out = {}
    if isinstance(params, dict):
        for k, v in params.items():
            out.update(_flat(v, f'{prefix}{k}.') if isinstance(v, dict) else {f'{prefix}{k}': v})
    return out


def schema_problems(aid, base_params, new_params):
    """Lo cambiado entre base y new debe estar en la tabla de afinables, con su tipo y dentro de [min, max]."""
    tab = (tunables().get(aid) or {})
    probs = []
    fb, fn = _flat(base_params), _flat(new_params)
    for path in sorted(set(fb) | set(fn)):
        a, b = fb.get(path, G._MISSING), fn.get(path, G._MISSING)
        if a == b:
            continue
        spec = tab.get(path)
        if spec is None:
            probs.append(P('not_tunable', f'{aid}: «{path}» no se puede cambiar desde la app (solo con un PR)',
                           f'{aid}: "{path}" cannot be changed from the app (only with a PR)'))
            continue
        if b is G._MISSING:
            probs.append(P('removed', f'{aid}: no se puede quitar «{path}»', f'{aid}: "{path}" cannot be removed'))
            continue
        if isinstance(b, bool) or not isinstance(b, (int, float)):
            probs.append(P('not_number', f'{aid}: «{path}» debe ser un número', f'{aid}: "{path}" must be a number'))
            continue
        if spec.get('type') == 'int' and float(b) != int(b):
            probs.append(P('not_int', f'{aid}: «{path}» debe ser un número entero', f'{aid}: "{path}" must be a whole number'))
            continue
        lo, hi = spec.get('min'), spec.get('max')
        if (lo is not None and b < lo) or (hi is not None and b > hi):
            probs.append(P('out_of_range', f'{aid}: «{path}» = {b} está fuera del rango permitido [{lo}, {hi}]',
                           f'{aid}: "{path}" = {b} is outside the allowed range [{lo}, {hi}]'))
    for rel in (tunables().get('_relations') or {}).get(aid) or ():
        strict = 'lt' in rel
        lo_p, hi_p = rel.get('lt') or rel.get('le') or (None, None)
        x, y = get_path(new_params, lo_p), get_path(new_params, hi_p)
        if isinstance(x, (int, float)) and isinstance(y, (int, float)) and not (x < y if strict else x <= y):
            w_es, w_en = ('menor que', 'lower than') if strict else ('menor o igual que', 'lower than or equal to')
            probs.append(P('relation', f"{aid}: «{lo_p}» ({x}) debe ser {w_es} «{hi_p}» ({y})"
                           + (f" — {rel['es']}" if rel.get('es') else ''),
                           f"{aid}: \"{lo_p}\" ({x}) must be {w_en} \"{hi_p}\" ({y})"
                           + (f" — {rel['en']}" if rel.get('en') else '')))
    return probs


def tunables_problems(latest):
    """Revisión del propio esquema contra los artefactos del repositorio (la corre --check): cada ruta afinable
    existe en la versión más alta de su artefacto y su valor de hoy está dentro de [min, max]."""
    probs = []
    for aid, tab in sorted(tunables().items()):
        if aid.startswith('_'):
            continue
        doc = latest.get(aid)
        if doc is None:
            probs.append(f'tunables.json: el artefacto {aid} no existe')
            continue
        if aid in APP_FORBIDDEN:
            probs.append(f'tunables.json: {aid} no se puede afinar desde la app ({APP_FORBIDDEN[aid][0]})')
        for path, spec in sorted(tab.items()):
            v = get_path(doc['params'], path)
            if v is None:
                probs.append(f'tunables.json: {aid}#{path} no existe en {aid}@{doc["semver"]}')
            elif not isinstance(v, (int, float)) or isinstance(v, bool):
                probs.append(f'tunables.json: {aid}#{path} no es numérico')
            elif not (spec.get('min', v) <= v <= spec.get('max', v)):
                probs.append(f'tunables.json: {aid}#{path} = {v} fuera de [{spec.get("min")}, {spec.get("max")}]')
            for k in ('label_es', 'label_en'):
                if not spec.get(k):
                    probs.append(f'tunables.json: {aid}#{path} sin {k} (regla bilingüe)')
    return probs


# ── espejos ──────────────────────────────────────────────────────────────────
def mirror_problems(aid, params):
    """Espejos de UNA versión (la propuesta de la app): rel_weights = vocabulario; artefactos con espejo fuera."""
    probs = []
    if aid in APP_FORBIDDEN:
        es, en = APP_FORBIDDEN[aid]
        probs.append(P('mirror', f'{aid}: {es}', f'{aid}: {en}'))
    if aid == 'kernel.params' and 'rel_weights' in params:
        from ontology import vocabulary as vocab
        if dict(params.get('rel_weights') or {}) != dict(vocab.relation_weights()):
            probs.append(P('mirror', 'kernel.params.rel_weights debe ser igual a los pesos de ontology/vocabulary.json '
                           '(espejo): cámbialos con un PR', 'kernel.params.rel_weights must equal the weights in '
                           'ontology/vocabulary.json (mirror): change them with a PR'))
    return probs
