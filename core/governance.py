"""core/governance.py — EL registro de gobernanza (docs/INFRA_OPERATIVA.md §5.1-§5.4; paso 9 del plan).

Las reglas y los números del sistema (parámetros del kernel, fórmula NRS, controles del corretaje, umbrales del
comité, tolerancias del guardián de cifras, auto-aplicación de agentes, Jev, vocabulario de decisiones, formas
SHACL) son ARTEFACTOS versionados con hash. Manda el RELEASE aprobado que está en la base; el repositorio solo
propone. Ninguna constante de esas vuelve a declararse en otro archivo: el código las lee de aquí.

  · `governance/artifacts/<id>@<semver>.json`: {id, semver, kind, change_kind, parent, params, changelog_es/en}.
    Identidad del artefacto = sha256 del JSON canónico de {id, semver, kind, params[, deprecated]} (el
    changelog no entra: corregir un texto no cambia la regla). `governance/manifest.json` lista los archivos y el
    release propuesto (scripts/build_governance.py lo mantiene; `--check` corre en las pruebas).
  · release_hash = sha256(canónico({artifact_id: hash})) — SIN el código (el code_sha va aparte en cada
    decisión). Es κ de configuración: lo estampan las decisiones, los eventos y las generaciones de vistas.
  · Con base (DATABASE_URL): `bootstrap_db()` (lo llama init_schema) registra los artefactos del repo en
    gov_artifacts (decisión governance.propose) y, si no hay ningún release, crea el 1.0.0 con los valores de hoy,
    `ratified=false` (decisión governance.activate de system:bootstrap). El vigente es el de mayor
    effective_from ≤ now(); sus cuerpos se verifican por hash. Fabrizio lo RATIFICA una vez con PIN
    (`ratify()` → decisión governance.ratify; no bloquea nada). Sin base: el del repositorio, `repo-unapproved`.
  · Variables de entorno (decisión D2): NUNCA fijan números. Las viejas (FRAGILITY_CAP,
    IMPORT_BULK_WEIGHT_FACTOR, DECIDE_MIN_CONF, DECIDE_WAIT_S, COMMITTEE_MEMO_TTL_HOURS) se IGNORAN y, si
    contradicen al artefacto, avisan en el 🩺. Solo SELECCIONAN una versión aprobada: `GOV_RELEASE=<hash>` (un
    release ratificado) o `<ARTEFACTO>=<semver>` (p. ej. KERNEL_PARAMS=1.0.0) si esa versión está en un release.
    Excepción: los modelos de IA (se anotan, no se gobiernan aquí).

Lectura en caliente = un diccionario en memoria (sin SQL). `bind()` asigna constantes de módulo desde el
artefacto y las vuelve a asignar si cambia el release vigente (cambio atómico bajo candado; las vistas se
reconstruyen). Nunca IA. Nunca UPDATE/DELETE (las tablas gov_* son append-only).
"""
import copy
import hashlib
import json
import logging
import os
import re
import sys
import threading
import time

log = logging.getLogger('khipu')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOV_DIR = os.path.join(ROOT, 'governance')
ART_DIR = os.path.join(GOV_DIR, 'artifacts')
MANIFEST_PATH = os.path.join(GOV_DIR, 'manifest.json')
SCHEMA = 'gov-manifest/1'
HASHED_KEYS = ('id', 'semver', 'kind', 'params', 'deprecated')
_SEMVER = re.compile(r'^(\d+)\.(\d+)\.(\d+)$')
_MISSING = object()

# D2: variables de entorno numéricas que ANTES fijaban un número → (artefacto, clave). Hoy se ignoran y avisan.
LEGACY_NUMERIC_ENV = {
    'FRAGILITY_CAP': ('kernel.params', 'fragility_cap'),
    'IMPORT_BULK_WEIGHT_FACTOR': ('kernel.params', 'bulk_weight_factor'),
    'DECIDE_MIN_CONF': ('policy.decide', 'min_conf'),
    'DECIDE_WAIT_S': ('policy.decide', 'control_wait_s'),
    'COMMITTEE_MEMO_TTL_HOURS': ('policy.committee', 'memo_ttl_hours'),
}

_LOCK = threading.RLock()
_STATE = {'repo': None, 'db': None, 'db_error': None, 'refreshed_at': None, 'bindings': [], 'last_applied': None,
          'listeners': []}


class GovernanceError(RuntimeError):
    pass


# ── forma canónica y hashes ──────────────────────────────────────────────────
def canonical(obj):
    from core.decisions import canonical as _c
    return _c(obj)


def hashed_body(doc):
    return {k: doc[k] for k in HASHED_KEYS if k in doc and doc[k] is not None}


def artifact_hash(doc):
    return hashlib.sha256(canonical(hashed_body(doc))).hexdigest()


def release_hash_of(artifact_hashes):
    """sha256 del mapa {artifact_id: hash} canónico (sin el código)."""
    return hashlib.sha256(canonical(dict(artifact_hashes))).hexdigest()


def semver_key(v):
    m = _SEMVER.match(str(v or ''))
    if not m:
        raise GovernanceError(f'semver inválido: {v!r}')
    return tuple(int(x) for x in m.groups())


# ── repositorio ──────────────────────────────────────────────────────────────
def artifact_path(aid, semver):
    return os.path.join(ART_DIR, f'{aid}@{semver}.json')


def read_artifact_file(path):
    with open(path, encoding='utf-8') as fh:
        doc = json.load(fh)
    for k in ('id', 'semver', 'kind', 'params'):
        if k not in doc:
            raise GovernanceError(f'{os.path.basename(path)}: falta "{k}"')
    exp = f"{doc['id']}@{doc['semver']}.json"
    if os.path.basename(path) != exp:
        raise GovernanceError(f'{os.path.basename(path)}: el nombre debe ser {exp}')
    semver_key(doc['semver'])
    return doc


def scan_repo():
    """{(id, semver): doc} de todos los archivos de governance/artifacts."""
    out = {}
    if not os.path.isdir(ART_DIR):
        return out
    for name in sorted(os.listdir(ART_DIR)):
        if name.endswith('.json'):
            doc = read_artifact_file(os.path.join(ART_DIR, name))
            out[(doc['id'], doc['semver'])] = doc
    return out


def latest_per_id(docs):
    best = {}
    for (aid, sv), doc in docs.items():
        if aid not in best or semver_key(sv) > semver_key(best[aid]['semver']):
            best[aid] = doc
    return best


class Bundle:
    """Release resuelto en memoria: {artifact_id: {semver, hash, params}} + sello."""
    __slots__ = ('release_hash', 'semver', 'label', 'source', 'ratified', 'effective_from', 'artifacts',
                 'selected', 'loaded_at')

    def as_stamp(self):
        return self.release_hash, self.label

    def summary(self):
        return {'release_hash': self.release_hash, 'semver': self.semver, 'label': self.label,
                'source': self.source, 'ratified': self.ratified, 'effective_from': self.effective_from,
                'artifacts': {a: {'semver': v['semver'], 'hash': v['hash']} for a, v in sorted(self.artifacts.items())},
                'selected_by_env': dict(self.selected or {})}


def _bundle(artifacts, semver, label, source, ratified, effective_from=None, selected=None):
    b = Bundle()
    b.artifacts = artifacts
    b.release_hash = release_hash_of({a: v['hash'] for a, v in artifacts.items()})
    b.semver, b.label, b.source, b.ratified = semver, label, source, ratified
    b.effective_from, b.selected, b.loaded_at = effective_from, selected or {}, time.time()
    return b


def load_manifest():
    with open(MANIFEST_PATH, encoding='utf-8') as fh:
        return json.load(fh)


def repo_bundle():
    """El release PROPUESTO por el repositorio (manifest.json), verificado contra los archivos. Cacheado."""
    with _LOCK:
        if _STATE['repo'] is not None:
            return _STATE['repo']
    man = load_manifest()
    docs = scan_repo()
    arts = {}
    for aid, ent in sorted((man.get('release') or {}).get('artifacts', {}).items()):
        doc = docs.get((aid, ent['semver']))
        if doc is None:
            raise GovernanceError(f'manifest.json cita {aid}@{ent["semver"]} y el archivo no existe')
        h = artifact_hash(doc)
        if h != ent['hash']:
            raise GovernanceError(f'{aid}@{ent["semver"]}: el contenido no coincide con manifest.json '
                                  f'(¿cambió sin subir la versión? corre scripts/build_governance.py)')
        arts[aid] = {'semver': doc['semver'], 'hash': h, 'params': doc['params'], 'kind': doc['kind']}
    sel = {}
    for aid in list(arts):                     # D2: <ARTEFACTO>=<semver> selecciona otra versión DEL REPO
        want = (os.getenv(env_name(aid)) or '').strip()
        if want and want != arts[aid]['semver']:
            doc = docs.get((aid, want))
            if doc is not None:
                arts[aid] = {'semver': want, 'hash': artifact_hash(doc), 'params': doc['params'], 'kind': doc['kind']}
                sel[aid] = want
    b = _bundle(arts, (man.get('release') or {}).get('semver', '0.0.0'), 'repo-unapproved', 'repo', False,
                selected=sel)
    with _LOCK:
        _STATE['repo'] = b
    return b


def env_name(aid):
    return re.sub(r'[^A-Z0-9]+', '_', aid.upper())


# ── release vigente ──────────────────────────────────────────────────────────
def _db_on():
    try:
        import ontology.db as odb
        return odb.ontology_available()
    except Exception:  # noqa: BLE001
        return False


def active():
    """El Bundle vigente: el de la base si hay base y se pudo cargar; si no, el del repositorio."""
    db = _STATE['db']
    if db is not None and _db_on():
        return db
    return repo_bundle()


def release():
    """(release_hash, etiqueta) — κ de configuración para decisiones, eventos y vistas."""
    try:
        return active().as_stamp()
    except Exception as e:  # noqa: BLE001
        log.error('governance: release no disponible (%s)', e)
        return '0' * 64, 'unavailable'


_TL = threading.local()          # contrafactual por HILO (counterfactual): nunca toca el release vigente


def _art(aid):
    ov = getattr(_TL, 'override', None)
    if ov is not None and aid in ov:
        return ov[aid]
    b = active()
    a = b.artifacts.get(aid)
    if a is None:                      # el release de la base no tiene este artefacto (código más nuevo)
        a = repo_bundle().artifacts.get(aid)
        if a is None:
            raise GovernanceError(f'artefacto desconocido: {aid}')
    return a


def fallbacks():
    """{artifact_id: {semver, hash}} que el release VIGENTE de la base NO trae y que el código lee del archivo del
    repositorio (sin aprobar; p. ej. un artefacto nuevo desplegado después del bootstrap). El release_hash no los
    cubre: por eso van aparte en el sello de cada decisión (`manifest.release.fallback`) y en el 🩺. Vacío sin base
    (todo es del repositorio y el sello ya lo dice: repo-unapproved)."""
    try:
        b = active()
        if b.source != 'db':
            return {}
        repo = repo_bundle()
    except Exception:  # noqa: BLE001
        return {}
    return {a: {'semver': v['semver'], 'hash': v['hash']} for a, v in sorted(repo.artifacts.items())
            if a not in b.artifacts}


def param(aid, key, default=_MISSING):
    p = _art(aid)['params']
    if key in p:
        return p[key]
    if default is _MISSING:
        raise GovernanceError(f'{aid} no tiene la clave {key!r}')
    return default


def section(aid):
    """Copia de los parámetros del artefacto vigente (para inicializar estructuras del módulo)."""
    return copy.deepcopy(_art(aid)['params'])


def artifact_hash_of(aid):
    return _art(aid)['hash']


def artifact_semver(aid):
    return _art(aid)['semver']


def policy_ref(aid):
    """'policy.broker_risk@1.0.0' + hash — para citar la política en una decisión."""
    a = _art(aid)
    return f'{aid}@{a["semver"]}', a['hash']


# ── constantes de módulo ─────────────────────────────────────────────────────
def bind(target, aid, mapping):
    """Asigna constantes de un módulo desde el artefacto `aid` y las re-asigna si cambia el release.
    `target`: dict de globals() o nombre de módulo. `mapping`: {CONSTANTE: clave | (clave, conversor)}.
    Devuelve los valores en el orden de `mapping` (el módulo los asigna explícitamente: se leen como constantes
    normales y los analizadores estáticos las ven definidas)."""
    spec = {}
    for const, how in mapping.items():
        key, conv = (how if isinstance(how, tuple) else (how, None))
        spec[const] = (key, conv)
    mod_name = target if isinstance(target, str) else target.get('__name__')
    _apply_one(mod_name, target if isinstance(target, dict) else None, aid, spec)
    with _LOCK:
        _STATE['bindings'] = [b for b in _STATE['bindings'] if not (b[0] == mod_name and b[1] == aid)]
        _STATE['bindings'].append((mod_name, aid, spec))
    gl = target if isinstance(target, dict) else sys.modules[mod_name].__dict__
    return tuple(gl[c] for c in spec)       # para asignarlas a la vista: `A, B = _gov.bind(globals(), …)`


def _apply_one(mod_name, gl, aid, spec):
    if gl is None:
        mod = sys.modules.get(mod_name)
        if mod is None:
            return
        gl = mod.__dict__
    params = _art(aid)['params']
    for const, (key, conv) in spec.items():
        v = copy.deepcopy(params[key])
        gl[const] = conv(v) if conv else v


def on_release_change(fn):
    """Oyente: fn(old_hash, new_hash) tras un cambio de release (vistas, cachés)."""
    with _LOCK:
        _STATE['listeners'].append(fn)
    return fn


def _apply_bindings():
    with _LOCK:
        bindings = list(_STATE['bindings'])
    for mod_name, aid, spec in bindings:
        try:
            _apply_one(mod_name, None, aid, spec)
        except Exception as e:  # noqa: BLE001
            log.error('governance: no se re-asignó %s ← %s (%s)', mod_name, aid, e)


def _swap(new_db_bundle):
    """Cambio atómico del release vigente (asignación de referencia, 1 worker) + re-asignación + señal."""
    old = active().release_hash
    with _LOCK:
        _STATE['db'] = new_db_bundle
    new = active().release_hash
    if new != old:
        _apply_bindings()
        log.warning('governance: release vigente %s → %s', old[:12], new[:12])
        for fn in list(_STATE['listeners']):
            try:
                fn(old, new)
            except Exception:  # noqa: BLE001
                pass
    with _LOCK:
        _STATE['last_applied'] = new


# ── base de datos ────────────────────────────────────────────────────────────
def _engine(engine=None):
    if engine is not None:
        return engine
    from ontology.db import _get_engine
    return _get_engine()


def _tables_ready(conn):
    from sqlalchemy import text
    return bool(conn.execute(text("SELECT to_regclass('gov_artifacts') IS NOT NULL AND "
                                  "to_regclass('gov_releases') IS NOT NULL")).scalar())


def bootstrap_db(engine=None):
    """init_schema: registra en gov_artifacts los artefactos del repo cuyo hash es nuevo (decisión
    governance.propose) y, si la base no tiene NINGÚN release, crea el bootstrap 1.0.0 (ratified=false, decisión
    governance.activate de system:bootstrap). Después carga el vigente. Nunca lanza."""
    from sqlalchemy import text
    try:
        eng = _engine(engine)
        repo = repo_bundle()
        docs = scan_repo()
        with eng.begin() as c:
            if not _tables_ready(c):
                return {'skipped': 'no_tables'}
            c.execute(text("SET LOCAL lock_timeout = '5s'"))
            c.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))'), {'k': 'khipus:governance'})
            have = {h for (h,) in c.execute(text('SELECT hash FROM gov_artifacts')).all()}
            taken = {(a, s): h for a, s, h in c.execute(text('SELECT artifact_id, semver, hash FROM gov_artifacts'))}
            new_docs = [d for d in docs.values() if artifact_hash(d) not in have]
            n_rel = c.execute(text('SELECT count(*) FROM gov_releases')).scalar()
        conflicts = [f"{d['id']}@{d['semver']}" for d in new_docs if (d['id'], d['semver']) in taken]
        new_docs = [d for d in new_docs if (d['id'], d['semver']) not in taken]
        out = {'registered': [], 'conflicts': conflicts, 'release_created': False}
        if conflicts:
            log.error('governance: artefactos que cambiaron SIN subir la versión (no se registran): %s', conflicts)
        if new_docs or not n_rel:
            out.update(_bootstrap_write(eng, new_docs, repo, create_release=not n_rel))
        refresh(eng)
        return out
    except Exception as e:  # noqa: BLE001
        with _LOCK:
            _STATE['db_error'] = f'{type(e).__name__}: {str(e)[:200]}'
        log.warning('governance.bootstrap_db: %s (la app sigue con el release del repositorio)', _STATE['db_error'])
        return {'error': _STATE['db_error']}


def _bootstrap_write(eng, new_docs, repo, create_release):
    from sqlalchemy import text

    from core import decisions, identity
    from ontology.db import session_scope
    principal = identity.system('bootstrap')
    out = {'registered': [], 'release_created': False}
    with session_scope() as s:
        s.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))'), {'k': 'khipus:governance'})
        have = {h for (h,) in s.execute(text('SELECT hash FROM gov_artifacts')).all()}
        new_docs = [d for d in new_docs if artifact_hash(d) not in have]
        if new_docs:
            with decisions.decision_scope('governance.propose', principal, session=s,
                                          subject={'artifacts': [f"{d['id']}@{d['semver']}" for d in new_docs]}
                                          ) as ctx:
                for d in new_docs:
                    h = artifact_hash(d)
                    s.execute(text(
                        'INSERT INTO gov_artifacts (hash, artifact_id, semver, change_kind, parent_hash, body, '
                        'changelog_es, changelog_en, proposed_by, proposal_decision_id) VALUES (:h, :a, :v, :ck, '
                        ':p, CAST(:b AS jsonb), :es, :en, :by, CAST(:did AS uuid)) ON CONFLICT DO NOTHING'),
                        {'h': h, 'a': d['id'], 'v': d['semver'], 'ck': d.get('change_kind') or 'initial',
                         'p': _parent_hash(d), 'b': json.dumps(hashed_body(d), ensure_ascii=False),
                         'es': d.get('changelog_es') or '', 'en': d.get('changelog_en') or '',
                         'by': principal.id, 'did': str(ctx.id)})
                    ctx.effect('gov_artifact', h, artifact=f"{d['id']}@{d['semver']}")
                    out['registered'].append(f"{d['id']}@{d['semver']}")
                ctx.output = {'registered': out['registered']}
                ctx.status = 'recorded'
        if create_release and not s.execute(text('SELECT 1 FROM gov_releases LIMIT 1')).first():
            arts = {a: {'hash': v['hash'], 'semver': v['semver']} for a, v in repo.artifacts.items()}
            rh = release_hash_of({a: v['hash'] for a, v in arts.items()})
            with decisions.decision_scope('governance.activate', principal, session=s,
                                          subject={'release_hash': rh, 'semver': repo.semver, 'bootstrap': True}
                                          ) as ctx:
                for a, v in arts.items():
                    ctx.policy(f"{a}@{v['semver']}", v['hash'])
                s.execute(text(
                    'INSERT INTO gov_releases (release_hash, semver, artifacts, effective_from, approval_decision_id, '
                    'ratified, note_es, note_en) VALUES (:r, :v, CAST(:a AS jsonb), clock_timestamp(), '
                    'CAST(:d AS uuid), false, :es, :en) ON CONFLICT DO NOTHING'),
                    {'r': rh, 'v': repo.semver, 'a': json.dumps(arts), 'd': str(ctx.id),
                     'es': 'Bootstrap con los valores de hoy (paso 9). Falta que Fabrizio lo ratifique con su PIN; '
                           'no bloquea nada.',
                     'en': "Bootstrap with today's values (step 9). Awaiting Fabrizio's ratification with his PIN; "
                           'it blocks nothing.'})
                ctx.effect('gov_release', rh)
                ctx.output = {'release_hash': rh, 'semver': repo.semver, 'ratified': False}
                ctx.status = 'executed'
            out['release_created'] = True
            out['release_hash'] = rh
    return out


def _parent_hash(doc):
    par = doc.get('parent')
    if not par:
        return None
    try:
        aid, sv = str(par).split('@', 1)
        return artifact_hash(read_artifact_file(artifact_path(aid, sv)))
    except Exception:  # noqa: BLE001
        return None


def _ratified_releases(conn):
    """Releases aprobados por una persona con PIN: ratificados (governance.ratify) o ACTIVADOS (governance.activate
    — `activate` exige PIN; también al volver a una versión anterior, que reactiva el release sin fila nueva: antes
    el 1.0.0 del arranque volvía a pedir «Ratificar» justo después de que Fabrizio lo aprobara, revisión batch E)."""
    from sqlalchemy import text
    rows = conn.execute(text("SELECT subject->>'release_hash' FROM decisions WHERE "
                             "(kind = 'governance.ratify' AND status = 'approved') OR "
                             "(kind = 'governance.activate' AND status = 'executed' AND auth = 'pin' "
                             "AND coalesce(subject->>'bootstrap', 'false') <> 'true')")).all()
    return {r[0] for r in rows if r[0]}


def refresh(engine=None):
    """Lee el release vigente de la base (y la selección por entorno), verifica los cuerpos por hash y lo pone en
    vigor. Barato (2 consultas indexadas); lo corre el reloj cada 60 s y tras ratificar. Nunca lanza."""
    from sqlalchemy import text
    if not _db_on():
        return None
    try:
        eng = _engine(engine)
        with eng.connect() as c:
            if not _tables_ready(c):
                return None
            want = (os.getenv('GOV_RELEASE') or '').strip().lower()
            ratified = _ratified_releases(c)
            row = None
            selected = {}
            if want:
                row = c.execute(text("SELECT * FROM gov_releases WHERE release_hash LIKE :p "
                                     "ORDER BY recorded_at DESC LIMIT 1"), {'p': want[:64] + '%'}).first()
                if row is None or not (row.ratified or row.release_hash in ratified) or len(want) < 8:
                    log.warning('governance: GOV_RELEASE=%s no es un release ratificado → se ignora', want[:12])
                    row = None
                else:
                    selected['release'] = row.release_hash
            if row is None:
                row = c.execute(text('SELECT * FROM gov_releases WHERE effective_from <= clock_timestamp() '
                                     'ORDER BY effective_from DESC, recorded_at DESC LIMIT 1')).first()
                # paso 12: deshacer = REACTIVAR un release que ya existía (su release_hash es la clave: no se
                # inserta otra fila; manda la decisión governance.activate más reciente con reactivation=true)
                if row is not None:
                    re_ = c.execute(text(
                        "SELECT subject->>'release_hash' AS rh, (subject->>'effective_from')::timestamptz AS eff "
                        "FROM decisions WHERE kind = 'governance.activate' AND status = 'executed' "
                        "AND subject->>'reactivation' = 'true' "
                        "AND (subject->>'effective_from')::timestamptz <= clock_timestamp() "
                        "ORDER BY (subject->>'effective_from')::timestamptz DESC, recorded_at DESC LIMIT 1")).first()
                    if re_ is not None and re_.eff is not None and row.effective_from is not None \
                            and re_.eff > row.effective_from:
                        alt = c.execute(text('SELECT * FROM gov_releases WHERE release_hash = :r'),
                                        {'r': re_.rh}).first()
                        if alt is not None:
                            row = alt
                            selected['reactivated_at'] = re_.eff.isoformat()
            if row is None:
                return None
            arts_ref = dict(row.artifacts or {})
            hashes = sorted({v['hash'] for v in arts_ref.values()})
            bodies = {r.hash: r for r in c.execute(text(
                'SELECT hash, artifact_id, semver, body FROM gov_artifacts WHERE hash = ANY(:h)'), {'h': hashes})}
            # D2: <ARTEFACTO>=<semver> elige otra versión si está en ALGÚN release ratificado
            for aid in list(arts_ref):
                v = (os.getenv(env_name(aid)) or '').strip()
                if v and v != arts_ref[aid].get('semver'):
                    alt = c.execute(text(
                        "SELECT a.hash, a.artifact_id, a.semver, a.body FROM gov_artifacts a WHERE a.artifact_id = :a "
                        "AND a.semver = :v AND EXISTS (SELECT 1 FROM gov_releases r WHERE "
                        "r.artifacts -> :a ->> 'hash' = a.hash AND (r.ratified OR r.release_hash = ANY(:rr)))"),
                        {'a': aid, 'v': v, 'rr': sorted(ratified)}).first()
                    if alt is None:
                        log.warning('governance: %s=%s no es una versión aprobada → se ignora', env_name(aid), v)
                        continue
                    bodies[alt.hash] = alt
                    arts_ref[aid] = {'hash': alt.hash, 'semver': v}
                    selected[aid] = v
        arts = {}
        for aid, ref in arts_ref.items():
            r = bodies.get(ref['hash'])
            if r is None:
                raise GovernanceError(f'{aid}: el cuerpo {ref["hash"][:12]} no está en gov_artifacts')
            body = r.body if isinstance(r.body, dict) else json.loads(r.body)
            if artifact_hash(body) != ref['hash'] or body.get('id') != aid:
                raise GovernanceError(f'{aid}: el cuerpo no coincide con su hash (¿manipulado?)')
            arts[aid] = {'semver': body['semver'], 'hash': ref['hash'], 'params': body['params'],
                         'kind': body['kind']}
        rh = release_hash_of({a: v['hash'] for a, v in arts.items()})
        is_ratified = bool(row.ratified or row.release_hash in ratified)
        reactivated = selected.pop('reactivated_at', None)
        label = ('db' if is_ratified else 'db-unratified') if not selected else 'db-selected'
        b = _bundle(arts, row.semver, label, 'db', is_ratified,
                    effective_from=reactivated or (row.effective_from.isoformat() if row.effective_from else None),
                    selected=selected)
        if rh != row.release_hash and not selected:
            raise GovernanceError('el release_hash guardado no coincide con sus artefactos')
        _swap(b)
        with _LOCK:
            _STATE['db_error'] = None
            _STATE['refreshed_at'] = time.time()
        return b
    except Exception as e:  # noqa: BLE001
        with _LOCK:
            _STATE['db_error'] = f'{type(e).__name__}: {str(e)[:200]}'
        log.error('governance.refresh: %s (sigue el release anterior)', _STATE['db_error'])
        return None


def refresh_job():
    """Tarea del reloj (system:governance_refresh)."""
    b = refresh()
    return {'release': b.release_hash[:12] if b else None, 'error': _STATE['db_error']}


def ratify(session, principal, release_hash=None, note=None):
    """Ratifica (con PIN, una persona) el release vigente o `release_hash` → decisión governance.ratify. No es un
    UPDATE: el estado ratificado se deriva de esta decisión. ValueError si ya estaba ratificado."""
    from sqlalchemy import text

    from core import decisions
    if not getattr(principal, 'is_human_pin', False):
        raise PermissionError('ratificar exige una persona autenticada con PIN (op:…)')
    target = (release_hash or active().release_hash).lower()
    session.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))'), {'k': f'gov_ratify:{target}'})
    row = session.execute(text('SELECT release_hash, semver, ratified FROM gov_releases WHERE release_hash = :r'),
                          {'r': target}).first()
    if row is None:
        raise LookupError(f'release no encontrado: {target[:12]}')
    if row.ratified or session.execute(text(
            "SELECT 1 FROM decisions WHERE kind = 'governance.ratify' AND status = 'approved' "
            "AND subject->>'release_hash' = :r"), {'r': target}).first():
        raise ValueError(f'el release {target[:12]} ya está ratificado')
    with decisions.decision_scope('governance.ratify', principal, session=session,
                                  subject={'release_hash': target, 'semver': row.semver}) as ctx:
        ctx.cause('gov_release', target)
        if note:
            ctx.extra['note_blob'] = ctx.blob('payload', {'note': str(note)[:2000]})
        ctx.output = {'ratified': target, 'semver': row.semver}
        ctx.status = 'approved'
    return {'decision_id': str(ctx.id), 'release_hash': target, 'semver': row.semver}


# ── contrafactual, propuestas y activación (paso 12: pieza mínima del paso 25) ─────────────────────────────────
def available_artifact(aid, semver):
    """{semver, hash, params, kind, change_kind, changelog_es/en, activation} de una versión DISPONIBLE (archivo del
    repositorio; con base, además debe coincidir con lo registrado en gov_artifacts si ya está registrada).
    LookupError si no existe."""
    try:
        doc = read_artifact_file(artifact_path(aid, semver))
    except FileNotFoundError:
        raise LookupError(f'{aid}@{semver} no existe') from None
    h = artifact_hash(doc)
    return {'semver': doc['semver'], 'hash': h, 'params': doc['params'], 'kind': doc['kind'],
            'change_kind': doc.get('change_kind') or 'initial', 'parent': doc.get('parent'),
            'changelog_es': doc.get('changelog_es') or '', 'changelog_en': doc.get('changelog_en') or '',
            'activation': doc.get('activation'), 'summary_es': doc.get('summary_es'), 'summary_en': doc.get('summary_en')}


class counterfactual:
    """`with counterfactual({'kernel.params': '2.0.0'}):` — ESTE hilo lee esas versiones (archivo del repositorio,
    verificado por hash) en vez de las del release vigente. Nada global cambia: los demás hilos, las vistas
    publicadas y las decisiones siguen con el release vigente. Lo usan /api/governance/preview y las pruebas."""

    def __init__(self, selection):
        self.arts = {aid: available_artifact(aid, sv) for aid, sv in (selection or {}).items()}

    def __enter__(self):
        self.prev = getattr(_TL, 'override', None)
        _TL.override = dict(self.prev or {}, **self.arts)
        return self

    def __exit__(self, *exc):
        _TL.override = self.prev
        return False


def proposals():
    """Versiones DISPONIBLES (repositorio) distintas de la vigente, por artefacto: lo que el 🩺 ofrece activar con PIN.
    [{id, semver, active_semver, change_kind, activation, changelog_es/en, newer}]"""
    try:
        b = active()
        docs = scan_repo()
    except Exception:  # noqa: BLE001
        return []
    out = []
    for (aid, sv), doc in sorted(docs.items()):
        cur = (b.artifacts.get(aid) or {}).get('semver')
        if cur == sv:
            continue
        try:
            newer = cur is None or semver_key(sv) > semver_key(cur)
        except GovernanceError:
            newer = False
        out.append({'id': aid, 'semver': sv, 'active_semver': cur, 'change_kind': doc.get('change_kind') or 'initial',
                    'activation': doc.get('activation'), 'newer': newer,
                    'changelog_es': doc.get('changelog_es') or '', 'changelog_en': doc.get('changelog_en') or '',
                    'summary_es': doc.get('summary_es'), 'summary_en': doc.get('summary_en'),
                    'four_eyes': 'unavailable' if doc.get('change_kind') == 'major' else None})
    return out


def _bump_release_semver(cur_semver, changes):
    """Semver del release nuevo: MAJOR si algún artefacto cambia de versión mayor, MINOR si de menor, si no PATCH."""
    try:
        x, y, z = semver_key(cur_semver or '1.0.0')
    except GovernanceError:
        x, y, z = 1, 0, 0
    lvl = 'patch'
    for _aid, (old, new) in changes.items():
        try:
            o, n = semver_key(old or '0.0.0'), semver_key(new)
        except GovernanceError:
            lvl = 'major'
            continue
        if o[0] != n[0]:
            lvl = 'major'
        elif o[1] != n[1] and lvl != 'major':
            lvl = 'minor'
    if lvl == 'major':
        return f'{x + 1}.0.0'
    if lvl == 'minor':
        return f'{x}.{y + 1}.0'
    return f'{x}.{y}.{z + 1}'


def activate(session, principal, selection, note=None):
    """Activa YA (D5: inmediato) el release vigente con las versiones de `selection` ({artifact_id: semver})
    sustituidas → fila nueva en gov_releases (ratified=true: lo aprueba una persona con PIN) + decisión
    `governance.activate` de op:… en la MISMA transacción. Deshacer = activar la versión anterior (otra decisión;
    si ese release ya existía, la decisión lo REACTIVA: `refresh` toma la activación más reciente).
    Nunca UPDATE/DELETE. PermissionError sin persona con PIN; LookupError si una versión no existe; ValueError si
    no cambia nada. Quien llama hace `refresh()` después del commit (las vistas se reconstruyen solas)."""
    from sqlalchemy import text

    from core import decisions
    if not getattr(principal, 'is_human_pin', False):
        raise PermissionError('activar exige una persona autenticada con PIN (op:…)')
    if not isinstance(selection, dict) or not selection:
        raise ValueError('selection vacía: {artifact_id: semver}')
    session.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))'), {'k': 'khipus:governance'})
    cur = active()
    if cur.source != 'db':
        raise LookupError('sin release de la base no hay nada que activar (rige el del repositorio)')
    arts = {a: {'hash': v['hash'], 'semver': v['semver']} for a, v in cur.artifacts.items()}
    changes, register = {}, []
    for aid, sv in sorted(selection.items()):
        aid, sv = str(aid)[:48], str(sv)[:16]
        semver_key(sv)
        row = session.execute(text('SELECT hash, body, change_kind FROM gov_artifacts WHERE artifact_id = :a AND '
                                   'semver = :v'), {'a': aid, 'v': sv}).first()
        if row is not None:
            body = row.body if isinstance(row.body, dict) else json.loads(row.body)
            if artifact_hash(body) != row.hash:
                raise GovernanceError(f'{aid}@{sv}: el cuerpo registrado no coincide con su hash')
            h = row.hash
        else:
            doc = available_artifact(aid, sv)          # LookupError si tampoco está en el repositorio
            h = doc['hash']
            register.append((aid, sv))
        old = (arts.get(aid) or {}).get('semver')
        if (arts.get(aid) or {}).get('hash') != h:
            changes[aid] = (old, sv)
        arts[aid] = {'hash': h, 'semver': sv}
    if not changes:
        raise ValueError('esas versiones ya están vigentes')
    rh = release_hash_of({a: v['hash'] for a, v in arts.items()})
    existing = session.execute(text('SELECT release_hash, semver FROM gov_releases WHERE release_hash = :r'),
                               {'r': rh}).first()
    rel_semver = existing.semver if existing is not None else _bump_release_semver(cur.semver, changes)
    eff = session.execute(text('SELECT clock_timestamp()')).scalar()
    major = any(_semver_major_changed(o, n) for o, n in changes.values())
    subject = {'release_hash': rh, 'semver': rel_semver, 'from_release': cur.release_hash,
               'changes': {a: {'from': o, 'to': n} for a, (o, n) in changes.items()},
               'effective_from': eff.isoformat(), 'reactivation': existing is not None,
               'four_eyes': 'unavailable' if major else None}
    if register:
        docs = [read_artifact_file(artifact_path(a, v)) for a, v in register]
        with decisions.decision_scope('governance.propose', principal, session=session,
                                      subject={'artifacts': [f'{a}@{v}' for a, v in register]}) as pctx:
            for d in docs:
                hh = artifact_hash(d)
                session.execute(text(
                    'INSERT INTO gov_artifacts (hash, artifact_id, semver, change_kind, parent_hash, body, '
                    'changelog_es, changelog_en, proposed_by, proposal_decision_id) VALUES (:h, :a, :v, :ck, :p, '
                    'CAST(:b AS jsonb), :es, :en, :by, CAST(:did AS uuid)) ON CONFLICT DO NOTHING'),
                    {'h': hh, 'a': d['id'], 'v': d['semver'], 'ck': d.get('change_kind') or 'initial',
                     'p': _parent_hash(d), 'b': json.dumps(hashed_body(d), ensure_ascii=False),
                     'es': d.get('changelog_es') or '', 'en': d.get('changelog_en') or '', 'by': principal.id,
                     'did': str(pctx.id)})
                pctx.effect('gov_artifact', hh, artifact=f"{d['id']}@{d['semver']}")
            pctx.output = {'registered': [f'{a}@{v}' for a, v in register]}
            pctx.status = 'recorded'
    with decisions.decision_scope('governance.activate', principal, session=session, subject=subject) as ctx:
        for a, v in sorted(arts.items()):
            ctx.policy(f"{a}@{v['semver']}", v['hash'])
        ctx.cause('gov_release', cur.release_hash)
        if note:
            ctx.extra['note_blob'] = ctx.blob('payload', {'note': str(note)[:2000]})
        if existing is None:
            ch_es = '; '.join(f'{a}: {o} → {n}' for a, (o, n) in sorted(changes.items()))
            session.execute(text(
                'INSERT INTO gov_releases (release_hash, semver, artifacts, effective_from, approval_decision_id, '
                'ratified, note_es, note_en) VALUES (:r, :v, CAST(:a AS jsonb), :eff, CAST(:d AS uuid), true, '
                ':es, :en)'),
                {'r': rh, 'v': rel_semver, 'a': json.dumps(arts), 'eff': eff, 'd': str(ctx.id),
                 'es': f'Activado con PIN por {principal.id}: {ch_es}.',
                 'en': f'Activated with PIN by {principal.id}: {ch_es}.'})
        ctx.effect('gov_release', rh)
        ctx.output = {'release_hash': rh, 'semver': rel_semver, 'changes': subject['changes'],
                      'reactivation': existing is not None}
        ctx.status = 'executed'
    return {'decision_id': str(ctx.id), 'release_hash': rh, 'semver': rel_semver, 'changes': subject['changes'],
            'reactivation': existing is not None, 'from_release': cur.release_hash,
            'four_eyes': subject['four_eyes']}


def _semver_major_changed(old, new):
    try:
        return semver_key(old or '0.0.0')[0] != semver_key(new)[0]
    except GovernanceError:
        return True


# ── avisos (🩺) ──────────────────────────────────────────────────────────────
def env_warnings():
    """D2: variables de entorno numéricas que ya no mandan y CONTRADICEN al artefacto vigente."""
    out = []
    for env, (aid, key) in LEGACY_NUMERIC_ENV.items():
        raw = os.getenv(env)
        if raw is None or raw.strip() == '':
            continue
        try:
            cur = param(aid, key)
            differs = float(raw) != float(cur)
        except (TypeError, ValueError):
            cur, differs = None, True
        except GovernanceError:
            continue
        if differs:
            out.append({'env': env, 'value': raw[:20], 'artifact': f'{aid}#{key}', 'in_force': cur,
                        'es': f'La variable {env}={raw[:20]} ya NO cambia el número (manda {aid}: {cur}). '
                              'Para cambiarlo hay que aprobar una versión nueva del artefacto; bórrala de Railway.',
                        'en': f'The variable {env}={raw[:20]} NO longer changes the number ({aid} rules: {cur}). '
                              'To change it a new artifact version must be approved; delete it from Railway.'})
    return out


def status():
    b = active()
    repo = repo_bundle()
    out = b.summary()
    out.update({'repo_release_hash': repo.release_hash, 'repo_semver': repo.semver,
                'repo_differs': repo.release_hash != b.release_hash, 'db_error': _STATE['db_error'],
                'refreshed_at': _STATE['refreshed_at'], 'env_warnings': env_warnings(),
                'needs_ratification': b.source == 'db' and not b.ratified,
                'repo_fallback': fallbacks(), 'proposals': proposals()})
    return out


def explain(lang='es'):
    s = status()
    en = lang == 'en'
    if s['source'] == 'repo':
        return ('Rules and numbers come from the repository (no database): proposal, not approved.' if en else
                'Las reglas y números salen del repositorio (sin base): propuesta, sin aprobar.')
    fb = sorted(s.get('repo_fallback') or {})
    if fb:
        names = ', '.join(fb)
        return (f"Release {s['semver']} ({s['release_hash'][:8]}) is in force, but {names} is NOT in it: those "
                'numbers come from the repository file (not approved). Propose a release that includes it.' if en
                else f"El release {s['semver']} ({s['release_hash'][:8]}) está vigente, pero {names} NO está en él: "
                'esos números salen del archivo del repositorio (sin aprobar). Propón un release que lo incluya.')
    if s['needs_ratification']:
        return (f"Release {s['semver']} ({s['release_hash'][:8]}) is in force with today's values; ratify it once "
                'with your PIN.' if en else
                f"El release {s['semver']} ({s['release_hash'][:8]}) está vigente con los valores de hoy; ratifícalo "
                'una vez con tu PIN.')
    return (f"Release {s['semver']} ({s['release_hash'][:8]}) ratified and in force." if en else
            f"Release {s['semver']} ({s['release_hash'][:8]}) ratificado y vigente.")


def _reset_for_tests():
    with _LOCK:
        _STATE['db'] = None
        _STATE['repo'] = None
        _STATE['db_error'] = None
    _apply_bindings()
