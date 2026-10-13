"""core/governance_flow.py — FLUJO DE GOBERNANZA COMPLETO (docs/INFRA_OPERATIVA.md §5.3; paso 25 del plan).

    proponer ──► regresión contrafactual ──► activar YA o PROGRAMAR (effective_from) ──► (cancelar) ──► deshacer
                                                                            └─► atribución: qué versiones decidieron X

  · `propose(session, principal, artifact, changes)` — una versión NUEVA de un artefacto de PARÁMETROS (kernel.params,
    policy.*) hecha en la app con PIN. Se valida con EL MISMO lint que scripts/build_governance.py
    (core/governance_lint: honestidad semver, esquema de afinables governance/tunables.json, espejos) y se guarda en
    gov_artifacts (origin 'app', activation 'pin') con la decisión governance.propose de op:… (status 'proposed').
    Nunca entra en vigor sola. Un problema → ProposalRefused con los mensajes ES/EN.
  · `regress(selection)` — regresión contrafactual ANTES de activar, sin tocar el motor vivo
    (core.governance.counterfactual, solo este hilo): (1) el LIBRO MAYOR real — las últimas decisiones whatif.shock /
    whatif.factor_fire recalculadas con la propuesta (kernel.params), los memos del comité reclasificados con los
    umbrales nuevos (policy.committee) y los controles de monto de las órdenes recientes (policy.broker_risk) —
    cuántas salidas cambian; (2) los ~969 choques de un nodo; (3) el NRS de TODAS las empresas (nrs.formula);
    (4) formas SHACL propuestas en SOMBRA junto a las vigentes (core/governance_shadow: diferencia de violaciones);
    (5) «¿qué cambia para mí?» para las posiciones del usuario (o las 10 empresas más críticas). Se guarda como
    decisión governance.validate (blob 'validation', retención legal). En segundo plano: `validate_async`.
  · `cancel_scheduled` / `apply_due` — una activación programada se cancela con OTRA decisión (nunca UPDATE) antes de
    empezar; al llegar su hora el reloj la pone en vigor (core.governance.refresh) y `apply_due` deja la decisión
    governance.activate de system:governance_scheduler que lo registra.
  · `attribution(session, decision_id)` — qué release y qué versión de cada artefacto regían una decisión.
  · `history(session)` — releases, decisiones governance.*, programadas, propuestas de la app y su validación.

four_eyes: D1 (un solo aprobador) → los MAJOR se marcan 'unavailable' y el flujo lo REGISTRA. Nunca IA. Nunca
UPDATE/DELETE (gov_* y decisions son append-only). Sin base: proponer/activar responden 503 (rige el repositorio).
"""
import copy
import logging
import threading
import time
from datetime import datetime, timedelta, timezone

log = logging.getLogger('khipu')

DELTA_PP = 0.5                  # una salida "cambia" si un impacto se mueve ≥ 0,5 puntos (= governance_preview)
LEDGER_DAYS = 30
LEDGER_PER_KIND = 200
FOCUS_MAX = 25
_JOBS = {}                      # (artifact, semver) → estado de la validación en segundo plano
_JOBS_LOCK = threading.Lock()
_RUN_LOCK = threading.Lock()    # una regresión a la vez (pesada: dos grafos + cientos de choques)


class ProposalRefused(ValueError):
    """La propuesta no pasa el lint: `problems` = [{code, es, en}]."""

    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__('; '.join(p['es'] for p in self.problems))


def _gov():
    from core import governance
    return governance


def _lint():
    from core import governance_lint
    return governance_lint


def param_artifacts():
    """Artefactos que se pueden proponer desde la app (los que tienen afinables en governance/tunables.json)."""
    return sorted(a for a in _lint().tunables() if not a.startswith('_') and a not in _lint().APP_FORBIDDEN)


def _num(v):
    if isinstance(v, bool):
        raise ValueError
    if isinstance(v, (int, float)):
        return v
    s = str(v).strip().replace(' ', '')
    if s.count(',') == 1 and '.' not in s:
        s = s.replace(',', '.')               # 0,55 (es) = 0.55
    f = float(s)
    return int(f) if f == int(f) and '.' not in s and 'e' not in s.lower() else f


def _versions_of(aid):
    """Todas las versiones conocidas de un artefacto: repositorio + base."""
    G = _gov()
    vs = {sv for (a, sv) in G.scan_repo() if a == aid}
    vs |= {sv for (a, sv) in G.registered() if a == aid}
    return vs


def _auto_changelog(aid, diffs):
    es = '; '.join(f"{d['path']}: {d['from']} → {d['to']}" for d in diffs)
    return (f'Propuesta hecha en la app (🩺 ⚖ Gobernanza): {aid} — {es}.',
            f'Proposal made in the app (🩺 ⚖ Governance): {aid} — {es}.')


def build_proposal(aid, changes, *, change_kind=None, semver=None, base_semver=None, changelog_es='',
                   changelog_en=''):
    """(doc, diffs, problems) — SIN base: arma la versión nueva y corre el lint. `changes` = {ruta: número}."""
    G, GL = _gov(), _lint()
    P = GL.P
    problems = []
    aid = str(aid or '').strip()[:48]
    if aid in GL.APP_FORBIDDEN:
        es, en = GL.APP_FORBIDDEN[aid]
        return None, [], [P('mirror', f'{aid}: {es}', f'{aid}: {en}')]
    if aid not in GL.tunables() or aid.startswith('_'):
        return None, [], [P('not_proposable', f'{aid}: no es un artefacto de parámetros que se pueda proponer desde '
                            'la app', f'{aid}: it is not a parameter artifact that can be proposed from the app')]
    try:
        base_sv = base_semver or G.artifact_semver(aid)
        base = G.available_artifact(aid, base_sv)
    except Exception:  # noqa: BLE001
        return None, [], [P('base_missing', f'{aid}@{base_semver}: la versión base no existe',
                            f'{aid}@{base_semver}: the base version does not exist')]
    if not isinstance(changes, dict) or not changes:
        return None, [], [P('no_change', 'No cambiaste ningún número.', 'You did not change any number.')]
    params = copy.deepcopy(base['params'])
    diffs = []
    for path, raw in sorted(changes.items()):
        path = str(path)[:96]
        old = GL.get_path(params, path)
        if old is None or isinstance(old, (dict, list)):
            problems.append(P('unknown_key', f'{aid}: «{path}» no existe en {aid}@{base_sv}',
                              f'{aid}: "{path}" does not exist in {aid}@{base_sv}'))
            continue
        try:
            v = _num(raw)
        except (TypeError, ValueError):
            problems.append(P('not_number', f'{aid}: «{path}» debe ser un número', f'{aid}: "{path}" must be a number'))
            continue
        if isinstance(old, float) and isinstance(v, int):
            v = float(v)
        if v != old:
            GL.set_path(params, path, v)
            diffs.append({'path': path, 'from': old, 'to': v})
    if problems:
        return None, diffs, problems
    need = GL.needed_kind(base['params'], params)
    if need is None:
        return None, diffs, [P('no_change', 'No cambiaste ningún número.', 'You did not change any number.')]
    ck = (change_kind or need).strip().lower() if isinstance(change_kind or need, str) else need
    if ck not in ('patch', 'minor', 'major'):
        return None, diffs, [P('bad_kind', f'change_kind inválido {ck!r} (patch|minor|major)',
                               f'invalid change_kind {ck!r} (patch|minor|major)')]
    versions = _versions_of(aid)
    try:
        sv = str(semver).strip() if semver else GL.next_semver(versions, base_sv, ck)
        G.semver_key(sv)
    except Exception:  # noqa: BLE001
        return None, diffs, [P('bad_semver', f'versión inválida {semver!r} (X.Y.Z)', f'invalid version {semver!r} (X.Y.Z)')]
    if any(G.semver_key(sv) == G.semver_key(x) for x in versions if G._SEMVER.match(str(x))):
        problems.append(P('semver_taken', f'{aid}@{sv} ya existe: el registro solo crece (usa otra versión)',
                          f'{aid}@{sv} already exists: the registry only grows (use another version)'))
    if not changelog_es or not changelog_en:
        a_es, a_en = _auto_changelog(aid, diffs)
        changelog_es, changelog_en = changelog_es or a_es, changelog_en or a_en
    doc = {'id': aid, 'semver': sv, 'kind': base['kind'], 'change_kind': ck, 'parent': f'{aid}@{base_sv}',
           'activation': 'pin', 'origin': 'app', 'params': params,
           'changelog_es': str(changelog_es)[:2000], 'changelog_en': str(changelog_en)[:2000]}
    lint_docs = {(aid, base_sv): {'id': aid, 'semver': base_sv, 'params': base['params'], 'change_kind': 'initial',
                                  'parent': None},
                 (aid, sv): doc}
    problems += [p for p in GL.semver_problems(lint_docs) if p['es'].startswith(f'{aid}@{sv}')]
    problems += GL.schema_problems(aid, base['params'], params)
    problems += GL.mirror_problems(aid, params)
    return doc, diffs, problems


def propose(session, principal, aid, changes, *, change_kind=None, semver=None, base_semver=None,
            changelog_es='', changelog_en='', note=None):
    """Registra la propuesta (gov_artifacts + decisión governance.propose 'proposed' de op:…, MISMA transacción).
    PermissionError sin persona con PIN; ProposalRefused si el lint falla. Quien llama hace `governance.refresh()`
    después del commit y lanza `validate_async`."""
    import json

    from sqlalchemy import text

    from core import decisions
    G = _gov()
    if not getattr(principal, 'is_human_pin', False):
        raise PermissionError('proponer exige una persona autenticada con PIN (op:…)')
    doc, diffs, problems = build_proposal(aid, changes, change_kind=change_kind, semver=semver,
                                          base_semver=base_semver, changelog_es=changelog_es,
                                          changelog_en=changelog_en)
    if problems:
        raise ProposalRefused(problems)
    session.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))'), {'k': 'khipus:governance'})
    if session.execute(text('SELECT 1 FROM gov_artifacts WHERE artifact_id = :a AND semver = :v'),
                       {'a': doc['id'], 'v': doc['semver']}).first():
        raise ProposalRefused([_lint().P('semver_taken', f"{doc['id']}@{doc['semver']} ya existe: el registro solo crece",
                                         f"{doc['id']}@{doc['semver']} already exists: the registry only grows")])
    h = G.artifact_hash(doc)
    parent_hash = None
    try:
        paid, psv = doc['parent'].split('@', 1)
        parent_hash = G.available_artifact(paid, psv)['hash']
    except Exception:  # noqa: BLE001
        pass
    body = dict(G.hashed_body(doc), parent=doc['parent'], origin='app', activation='pin')
    four = 'unavailable' if doc['change_kind'] == 'major' else None
    with decisions.decision_scope('governance.propose', principal, session=session,
                                  subject={'artifacts': [f"{doc['id']}@{doc['semver']}"], 'artifact': doc['id'],
                                           'semver': doc['semver'], 'hash': h, 'parent': doc['parent'],
                                           'change_kind': doc['change_kind'], 'origin': 'app',
                                           'changes': diffs[:40], 'four_eyes': four}) as ctx:
        session.execute(text(
            'INSERT INTO gov_artifacts (hash, artifact_id, semver, change_kind, parent_hash, body, changelog_es, '
            'changelog_en, proposed_by, proposal_decision_id) VALUES (:h, :a, :v, :ck, :p, CAST(:b AS jsonb), :es, '
            ':en, :by, CAST(:did AS uuid))'),
            {'h': h, 'a': doc['id'], 'v': doc['semver'], 'ck': doc['change_kind'], 'p': parent_hash,
             'b': json.dumps(body, ensure_ascii=False), 'es': doc['changelog_es'], 'en': doc['changelog_en'],
             'by': principal.id, 'did': str(ctx.id)})
        ctx.effect('gov_artifact', h, artifact=f"{doc['id']}@{doc['semver']}")
        if parent_hash:
            ctx.cause('gov_artifact', parent_hash)
        if note:
            ctx.extra['note_blob'] = ctx.blob('payload', {'note': str(note)[:2000]})
        ctx.output = {'registered': [f"{doc['id']}@{doc['semver']}"], 'hash': h, 'activation': 'pin'}
        ctx.status = 'proposed'
    return {'decision_id': str(ctx.id), 'artifact': doc['id'], 'semver': doc['semver'], 'hash': h,
            'change_kind': doc['change_kind'], 'parent': doc['parent'], 'changes': diffs, 'four_eyes': four,
            'changelog_es': doc['changelog_es'], 'changelog_en': doc['changelog_en']}


# ── regresión contrafactual ──────────────────────────────────────────────────
def _impacts_changed(a, b):
    for k in set(a) | set(b):
        if abs(float(a.get(k, 0.0)) - float(b.get(k, 0.0))) >= DELTA_PP:
            return True
    return False


def _x0_whatif(core, rp, kind):
    """Vector inicial de un qué-pasaría-si guardado (request_params del manifiesto)."""
    import numpy as np
    x0 = np.zeros(len(core.ids))
    seeds = []
    if kind == 'whatif.shock':
        items = rp.get('shocks') if isinstance(rp.get('shocks'), list) else None
        if items is None:
            mag = rp.get('magnitude')
            items = [{'id': i, 'magnitude': 1.0 if mag is None else mag} for i in (rp.get('shock') or [])]
        for it in items[:50]:
            sid = it.get('id') if isinstance(it, dict) else it
            oid = core.resolve(str(sid or '')[:120]) if hasattr(core, 'resolve') else (sid if sid in core.idx else None)
            if oid is None:
                continue
            try:
                m = float((it.get('magnitude') if isinstance(it, dict) else 1.0) or 0.0)
            except (TypeError, ValueError):
                m = 1.0
            x0[core.idx[oid]] = max(x0[core.idx[oid]], min(1.0, m))
            seeds.append(oid)
    return x0, seeds


def _fire_x0(core, fid, magnitude):
    """Siembra de un factor disparado con LA regla del kernel vigente en este hilo (member_coef | legacy), la misma
    de /api/matrix/factor/fire (matrix/api.py). Devuelve (x0, factors_crisis) o (None, None)."""
    import numpy as np

    from matrix import engine as E
    target = next((f for f in core.factors if f['id'] == fid), None)
    if target is None:
        return None, None
    member_coef = E._P('fire_mode', 'legacy') == 'member_coef'
    if member_coef:
        crisis = target.get('severity_crisis') or min(float(E._P('fire_crisis_default_max', 10.0)),
                                                      target['severity'] * 2)
        base = min(1.0, magnitude if magnitude is not None else max(0.0, float(crisis) / float(E._P('severity_divisor'))))
    else:
        crisis = target.get('severity_crisis') or min(5.0, target['severity'] * 2)
        base = magnitude if magnitude is not None else max(0.0, min(1.0, float(crisis) / 5.0))
    x0 = np.zeros(len(core.ids))
    for m, coef in target['members'].items():
        if m in core.idx:
            x0[core.idx[m]] = min(1.0, base * min(1.0, max(0.0, float(coef))))
    fc = [dict(f, severity=crisis) if f['id'] == fid else f for f in core.factors]
    return x0, fc


def _replay_whatif(core, row):
    """Impactos {id: pct} de una decisión whatif.* recalculada con el kernel de ESTE hilo, o None si no se puede."""
    from core.hotviews.views import impact
    from matrix import engine as E
    rp = (row['manifest'] or {}).get('request_params') or {}
    kind = row['kind']
    damping = rp.get('damping')
    hops = rp.get('max_hops')
    # lo que el pedido NO fijó (igual al valor por defecto del kernel de entonces) sigue al kernel del contrafactual
    if damping is not None and abs(float(damping) - float(row['_def_damping'])) < 1e-9:
        damping = None
    if hops is not None and int(hops) == int(row['_def_hops']):
        hops = None
    if kind == 'whatif.factor_fire':
        x0, fc = _fire_x0(core, rp.get('factor_id') or (row['subject'] or {}).get('factor_id'), rp.get('magnitude'))
        if x0 is None or not x0.any():
            return None
        frag = E.fragility(core.idx, fc)
        total, _first = E.propagate_block(core.dt, frag, x0, damping=damping, max_hops=hops)
        col = total[:, 0]
        return {core.ids[j]: round(float(min(1.0, col[j])) * 100, 2) for j in col.nonzero()[0].tolist()}
    x0, seeds = _x0_whatif(core, rp, kind)
    if not seeds:
        return None
    direction = rp.get('direction') or 'down'
    factors = rp.get('factors') if rp.get('factors') in ('none',) or isinstance(rp.get('factors'), list) else 'active'
    try:
        sc = impact.scenario(core, x0, factors=factors, damping=damping, max_hops=hops, direction=direction)
    except ValueError:
        return {'__unavailable__': 1.0}          # p. ej. 'up' sin kernel 2.0.0: el resultado no existiría
    return sc['impacts']


def _ledger_rows(kinds, days=LEDGER_DAYS, limit=LEDGER_PER_KIND):
    """Decisiones recientes del libro (últimos `days` días, `limit` por tipo). [] sin base."""
    from core import governance
    if not governance._db_on():
        return []
    from sqlalchemy import text
    from ontology.db import session_scope
    out = []
    with session_scope() as s:
        for k in kinds:
            for r in s.execute(text(
                    'SELECT id, kind, status, subject, manifest, output, recorded_at FROM decisions WHERE kind = :k '
                    "AND recorded_at >= clock_timestamp() - make_interval(days => :d) ORDER BY recorded_at DESC "
                    'LIMIT :n'), {'k': k, 'd': int(days), 'n': int(limit)}):
                out.append({'id': str(r.id), 'kind': r.kind, 'status': r.status, 'subject': r.subject or {},
                            'manifest': r.manifest or {}, 'output': r.output or {},
                            'recorded_at': r.recorded_at.isoformat() if r.recorded_at else None})
    return out


def _ledger_whatif(before, after, sel):
    """whatif.shock / whatif.factor_fire del libro recalculados con el kernel vigente y con la propuesta."""
    from core import governance
    from matrix import engine as E
    rows = _ledger_rows(('whatif.shock', 'whatif.factor_fire'))
    d0, h0 = float(E._P('damping')), int(E._P('max_hops'))
    res = {'decisions': len(rows), 'replayed': 0, 'changed': 0, 'not_replayable': 0, 'by_kind': {}, 'examples': []}
    core0, core1 = before[1], after[1]
    after_out = {}
    with governance.counterfactual(sel):
        for r in rows:
            r['_def_damping'], r['_def_hops'] = d0, h0
            try:
                after_out[r['id']] = _replay_whatif(core1, r)
            except Exception:  # noqa: BLE001
                after_out[r['id']] = None
    for r in rows:
        bk = res['by_kind'].setdefault(r['kind'], {'decisions': 0, 'replayed': 0, 'changed': 0})
        bk['decisions'] += 1
        try:
            a = _replay_whatif(core0, r)
        except Exception:  # noqa: BLE001
            a = None
        b = after_out.get(r['id'])
        if a is None or b is None:
            res['not_replayable'] += 1
            continue
        res['replayed'] += 1
        bk['replayed'] += 1
        if _impacts_changed(a, b):
            res['changed'] += 1
            bk['changed'] += 1
            if len(res['examples']) < 5:
                ids = (r['subject'] or {}).get('entity_ids') or []
                res['examples'].append({'decision_id': r['id'], 'kind': r['kind'], 'entity_ids': ids[:5],
                                        'recorded_at': r['recorded_at'],
                                        'affected_before': sum(1 for v in a.values() if v >= 1.0),
                                        'affected_after': sum(1 for v in b.values() if v >= 1.0)})
    return res


def _committee_band(conv, p):
    if conv is None:
        return None
    conv = float(conv)
    if conv >= float(p['buy_threshold']):
        return 'buy'
    if conv <= float(p['sell_threshold']):
        return 'sell'
    if conv <= float(p['trim_threshold']):
        return 'trim'
    return 'hold'


def _ledger_committee(cur, new):
    rows = _ledger_rows(('committee.run',))
    res = {'decisions': len(rows), 'replayed': 0, 'changed': 0, 'evidence_changed': 0, 'examples': []}
    for r in rows:
        o = r['output'] or {}
        conv = o.get('overall_conviction')
        b0, b1 = _committee_band(conv, cur), _committee_band(conv, new)
        if b0 is None:
            continue
        res['replayed'] += 1
        n = o.get('n_claims')
        ev = (n is not None and (int(n) < int(cur.get('min_claims', 0))) != (int(n) < int(new.get('min_claims', 0))))
        res['evidence_changed'] += bool(ev)
        if b0 != b1 or ev:
            res['changed'] += 1
            if len(res['examples']) < 5:
                res['examples'].append({'decision_id': r['id'], 'memo_id': o.get('memo_id'),
                                        'entity_ids': (r['subject'] or {}).get('entity_ids'), 'conviction': conv,
                                        'zone_before': b0, 'zone_after': b1})
    return res


def _order_amount_verdict(est, client, p):
    """Controles de MONTO de una orden con los parámetros `p` de policy.broker_risk: tope absoluto, mínimo y tope por
    orden del perfil (+ overrides del cliente, como brokerage/risk.effective_limits). Devuelve el conjunto de los
    que bloquearían."""
    if est is None:
        return None
    est = float(est)
    prof = (p.get('profiles') or {}).get(client.get('risk_profile') or 'moderado') or \
        (p.get('profiles') or {}).get('moderado') or {}
    lim = float(prof.get('max_order_usd') or 0) or None
    ov = client.get('risk_limits') or {}
    try:
        if ov.get('max_order_usd') not in (None, '') and float(ov['max_order_usd']) > 0:
            lim = float(ov['max_order_usd'])
    except (TypeError, ValueError):
        pass
    hard = float(p.get('hard_max_order_usd') or 0)
    if lim is not None:
        lim = min(lim, hard)
    out = set()
    if est > hard:
        out.add('hard_max')
    if est < float(p.get('min_order_usd') or 0):
        out.add('min_order')
    if lim is not None and est > lim:
        out.add('max_order')
    return out


def _ledger_orders(cur, new):
    from core import governance
    res = {'orders': 0, 'replayed': 0, 'changed': 0, 'would_block_now': 0, 'would_unblock_now': 0, 'examples': [],
           'checks': ['hard_max', 'min_order', 'max_order']}
    if not governance._db_on():
        return res
    from sqlalchemy import text
    from ontology.db import session_scope
    with session_scope() as s:
        try:
            rows = s.execute(text(
                'SELECT o.id, o.symbol, o.side, o.est_usd, o.created_at, c.risk_profile, c.risk_limits '
                'FROM broker_orders o JOIN broker_clients c ON c.id = o.client_id '
                "WHERE o.created_at >= now() - make_interval(days => :d) ORDER BY o.created_at DESC LIMIT :n"),
                {'d': LEDGER_DAYS, 'n': LEDGER_PER_KIND}).all()
        except Exception:  # noqa: BLE001 — sin tablas del corretaje
            return res
    res['orders'] = len(rows)
    for r in rows:
        client = {'risk_profile': r.risk_profile, 'risk_limits': r.risk_limits or {}}
        a, b = _order_amount_verdict(r.est_usd, client, cur), _order_amount_verdict(r.est_usd, client, new)
        if a is None:
            continue
        res['replayed'] += 1
        if a != b:
            res['changed'] += 1
            res['would_block_now'] += bool(b and not a)
            res['would_unblock_now'] += bool(a and not b)
            if len(res['examples']) < 5:
                res['examples'].append({'order_id': r.id, 'symbol': r.symbol, 'side': r.side, 'est_usd': r.est_usd,
                                        'blocked_before': sorted(a), 'blocked_after': sorted(b)})
    return res


def _nrs_compare(cur, new, focus):
    """NRS de TODAS las empresas con la fórmula vigente y con la propuesta (core.world.nrs_terms con params)."""
    from core import world
    from core.hotviews import hot
    g = hot.graph()
    deg = g.flow_degree
    changed, rows = 0, []
    for n in g.nodes:
        d = deg.get(n['id'], 0)
        try:
            a = world.nrs_terms(n, d, params=cur)['total']
            b = world.nrs_terms(n, d, params=new)['total']
        except Exception:  # noqa: BLE001
            continue
        if a != b:
            changed += 1
        rows.append((n['id'], n.get('label') or n['id'], a, b))
    fset = set(focus or ())
    top = sorted(rows, key=lambda t: (-abs(t[3] - t[2]), t[0]))[:10]
    return {'companies': len(rows), 'changed': changed,
            'top_changes': [{'id': i, 'label': lb, 'before': a, 'after': b} for i, lb, a, b in top if a != b],
            'focus': [{'id': i, 'label': lb, 'before': a, 'after': b} for i, lb, a, b in rows if i in fset]}


def _focus_ids(core0, imp0, focus):
    """Ids canónicos de las posiciones del usuario; si no hay, las 10 empresas más críticas (cuellos de botella)."""
    out = []
    for f in focus or ():
        oid = core0.resolve(str(f)[:120]) if hasattr(core0, 'resolve') else (f if f in core0.idx else None)
        if oid and oid not in out:
            out.append(oid)
        if len(out) >= FOCUS_MAX:
            break
    if out:
        return out, 'positions'
    rank = sorted(imp0.metrics.items(), key=lambda kv: kv[1]['chokepoint_rank'])[:10]
    return [k for k, _m in rank], 'top10'


def _exposure(imp, focus):
    """{id: (máximo golpe recibido en cualquier choque de un nodo, fuente)} para los ids de `focus`."""
    fs = set(focus)
    best = {f: (0.0, None) for f in focus}
    for src, hit in imp.victims.items():
        for k, p in zip(hit[0], hit[1]):
            if k in fs and k != src and p > best[k][0]:
                best[k] = (float(p), src)
    return best


def for_me(sel, before=None, after=None, focus=None):
    """«¿Qué cambia para mí?»: por cada empresa de las posiciones del usuario (o de las 10 más críticas) el golpe
    máximo que puede recibir y a cuántas arrastra si cae, antes y después; para políticas, los números que cambian
    con su nombre en lenguaje simple. {basis: positions|top10|params, items: [...], lines_es: [...], lines_en: [...]}"""
    from core import governance
    GL = _lint()
    lines_es, lines_en, items = [], [], []
    basis = 'params'
    if before is not None and after is not None:
        (_d0, c0, i0), (_d1, c1, i1) = before, after
        ids, basis = _focus_ids(c0, i0, focus)
        e0, e1 = _exposure(i0, ids), _exposure(i1, ids)
        for oid in ids:
            s0, s1 = i0.stats.get(oid) or {}, i1.stats.get(oid) or {}
            (p0, src0), (p1, src1) = e0.get(oid, (0.0, None)), e1.get(oid, (0.0, None))
            it = {'id': oid, 'label': c0.label(oid), 'max_hit_before': round(p0, 2), 'max_hit_after': round(p1, 2),
                  'max_hit_from_before': src0, 'max_hit_from_after': src1,
                  'drags_before': s0.get('reach_1', 0), 'drags_after': s1.get('reach_1', 0)}
            it['changed'] = abs(p1 - p0) >= DELTA_PP or it['drags_before'] != it['drags_after']
            items.append(it)
        items.sort(key=lambda x: (-abs(x['max_hit_after'] - x['max_hit_before']),
                                  -abs(x['drags_after'] - x['drags_before']), x['id']))
        for it in items[:8]:
            if not it['changed']:
                continue
            lines_es.append(f"{it['label']}: el peor golpe que puede recibir pasa de {it['max_hit_before']} % a "
                            f"{it['max_hit_after']} %; si cae, arrastra a {it['drags_before']} → {it['drags_after']} "
                            'empresas.')
            lines_en.append(f"{it['label']}: the worst hit it can take goes from {it['max_hit_before']}% to "
                            f"{it['max_hit_after']}%; if it fails, it drags {it['drags_before']} → {it['drags_after']} "
                            'companies.')
        if not lines_es:
            lines_es.append('Para estas empresas no cambia nada visible (menos de 0,5 puntos).')
            lines_en.append('Nothing visible changes for these companies (under 0.5 points).')
    tab = GL.tunables()
    for aid, sv in sorted(sel.items()):
        if aid == 'kernel.params' and before is not None:
            continue
        try:
            cur = governance.section(aid)
            new = governance.available_artifact(aid, sv)['params']
        except Exception:  # noqa: BLE001
            continue
        specs = tab.get(aid) or {}
        for path in sorted(set(GL._flat(cur)) | set(GL._flat(new))):
            a, b = GL.get_path(cur, path), GL.get_path(new, path)
            if a == b:
                continue
            spec = specs.get(path) or {}
            lines_es.append(f"{spec.get('label_es') or path}: {a} → {b}." + (f" {spec['help_es']}" if spec.get('help_es') else ''))
            lines_en.append(f"{spec.get('label_en') or path}: {a} → {b}." + (f" {spec['help_en']}" if spec.get('help_en') else ''))
            if len(lines_es) >= 12:
                break
    return {'basis': basis, 'items': items, 'lines_es': lines_es, 'lines_en': lines_en}


def _shapes_section(sel):
    out = {}
    if 'ontology.shapes' not in sel:
        return None
    try:
        from core import governance_shadow
        out = governance_shadow.stats(sel['ontology.shapes'])
    except Exception as e:  # noqa: BLE001
        out = {'error': type(e).__name__}
    return out


def _summary(rep):
    es, en = [], []
    k = rep.get('shocks')
    if k:
        es.append(f"Simulaciones de caída de una empresa: cambian {k['shocks_changed']} de {k['shocks']}.")
        en.append(f"Single-company collapse simulations: {k['shocks_changed']} of {k['shocks']} change.")
    w = (rep.get('ledger') or {}).get('whatif')
    if w:
        es.append(f"Qué-pasaría-si reales de los últimos {LEDGER_DAYS} días: {w['changed']} de {w['replayed']} darían "
                  'otro resultado.')
        en.append(f"Real what-ifs from the last {LEDGER_DAYS} days: {w['changed']} of {w['replayed']} would give a "
                  'different result.')
    c = (rep.get('ledger') or {}).get('committee')
    if c:
        es.append(f"Memos del comité: {c['changed']} de {c['replayed']} cambiarían de zona (comprar/mantener/recortar/vender).")
        en.append(f"Committee memos: {c['changed']} of {c['replayed']} would change zone (buy/hold/trim/sell).")
    o = (rep.get('ledger') or {}).get('orders')
    if o:
        es.append(f"Órdenes recientes: {o['changed']} de {o['replayed']} cambiarían de veredicto en los controles de monto "
                  f"({o['would_block_now']} se frenarían, {o['would_unblock_now']} pasarían).")
        en.append(f"Recent orders: {o['changed']} of {o['replayed']} would change verdict on the amount checks "
                  f"({o['would_block_now']} would be stopped, {o['would_unblock_now']} would pass).")
    n = rep.get('nrs')
    if n:
        es.append(f"NRS: cambia en {n['changed']} de {n['companies']} empresas.")
        en.append(f"NRS: changes for {n['changed']} of {n['companies']} companies.")
    elif rep.get('shocks') is not None or rep.get('ledger'):
        es.append('El NRS no cambia.')
        en.append('The NRS does not change.')
    sh = rep.get('shapes')
    if sh is not None:
        es.append(f"Reglas nuevas en sombra: {sh.get('evaluations', 0)} revisiones en vivo, {sh.get('with_diff', 0)} con "
                  'diferencias.')
        en.append(f"New rules in shadow: {sh.get('evaluations', 0)} live checks, {sh.get('with_diff', 0)} with "
                  'differences.')
    if rep.get('semver_warning'):
        es.append(rep['semver_warning']['es'])
        en.append(rep['semver_warning']['en'])
    return ' '.join(es), ' '.join(en)


def regress(selection, focus=None):
    """El reporte de regresión contrafactual (gov-regression/1). Nunca escribe; nunca toca el release vigente."""
    from core import governance, governance_preview
    if not isinstance(selection, dict) or not selection:
        raise ValueError('selection vacía')
    sel = {str(a)[:48]: str(v)[:16] for a, v in selection.items()}
    docs = {a: governance.available_artifact(a, v) for a, v in sel.items()}          # LookupError si no existe
    t0 = time.perf_counter()
    rep = {'schema': 'gov-regression/1', 'selection': sel, 'release_hash': governance.active().release_hash,
           'active': {a: governance.artifact_semver(a) for a in sel}, 'computed_at': datetime.now(timezone.utc).isoformat(),
           'params_diff': {a: governance_preview._params_diff(a, v) for a, v in sel.items()},
           'change_kind': {a: d['change_kind'] for a, d in docs.items()}, 'ledger': {}}
    with _RUN_LOCK:
        before = after = None
        if 'kernel.params' in sel:
            before = governance_preview._build()
            with governance.counterfactual(sel):
                after = governance_preview._build()
            rep['shocks'] = governance_preview._kernel_compare(before, after)
            rep['shocks'].pop('reference', None)
            rep['graph_version'] = before[0].graph_version
            rep['ledger']['whatif'] = _ledger_whatif(before, after, sel)
        if 'policy.committee' in sel:
            rep['ledger']['committee'] = _ledger_committee(governance.section('policy.committee'),
                                                           docs['policy.committee']['params'])
        if 'policy.broker_risk' in sel:
            rep['ledger']['orders'] = _ledger_orders(governance.section('policy.broker_risk'),
                                                     docs['policy.broker_risk']['params'])
        if 'nrs.formula' in sel:
            rep['nrs'] = _nrs_compare(governance.section('nrs.formula'), docs['nrs.formula']['params'], focus)
        sh = _shapes_section(sel)
        if sh is not None:
            rep['shapes'] = sh
        rep['for_me'] = for_me(sel, before, after, focus)
    changed = sum(int((rep['ledger'].get(k) or {}).get('changed') or 0) for k in ('whatif', 'committee', 'orders'))
    changed += int((rep.get('shocks') or {}).get('shocks_changed') or 0) + int((rep.get('nrs') or {}).get('changed') or 0)
    rep['outputs_changed'] = changed
    small = [a for a, ck in rep['change_kind'].items() if ck in ('patch', 'minor')]
    if small and changed:
        rep['semver_warning'] = {
            'es': f"Atención: {', '.join(small)} dice ser un cambio menor, pero cambian {changed} resultados "
                  '(§5.2: un PATCH/MINOR exige 0 diferencias).',
            'en': f"Warning: {', '.join(small)} claims to be a minor change, but {changed} results change "
                  '(§5.2: a PATCH/MINOR requires 0 differences).'}
    rep['summary_es'], rep['summary_en'] = _summary(rep)
    rep['compute_ms'] = round((time.perf_counter() - t0) * 1000, 1)
    return rep


def _validation_output(rep, blob_sha):
    sh = rep.get('shocks') or {}
    led = rep.get('ledger') or {}
    return {'outputs_changed': rep.get('outputs_changed'), 'validation_blob': blob_sha,
            'shocks': {k: sh.get(k) for k in ('shocks', 'shocks_changed')} if sh else None,
            'whatif': {k: (led.get('whatif') or {}).get(k) for k in ('replayed', 'changed')} if led.get('whatif') else None,
            'committee': {k: led['committee'].get(k) for k in ('replayed', 'changed')} if led.get('committee') else None,
            'orders': {k: led['orders'].get(k) for k in ('replayed', 'changed')} if led.get('orders') else None,
            'nrs': {k: rep['nrs'].get(k) for k in ('companies', 'changed')} if rep.get('nrs') else None,
            'semver_warning': bool(rep.get('semver_warning')),
            'summary_es': rep.get('summary_es'), 'summary_en': rep.get('summary_en'),
            'compute_ms': rep.get('compute_ms')}


def validate(principal, aid, semver, focus=None):
    """Corre la regresión y la REGISTRA (decisión governance.validate; blob 'validation'). Devuelve
    {decision_id, report}. Sin base: solo el reporte (decision_id None)."""
    from core import decisions, governance
    rep = regress({aid: semver}, focus=focus)
    if not governance._db_on():
        return {'decision_id': None, 'report': rep}
    from ontology.db import session_scope
    h = governance.available_artifact(aid, semver)['hash']
    with session_scope() as s:
        with decisions.decision_scope('governance.validate', principal, session=s,
                                      subject={'artifact': aid, 'semver': semver, 'hash': h,
                                               'release_hash': rep['release_hash']}) as ctx:
            ctx.cause('gov_artifact', h)
            sha = ctx.blob('validation', rep)
            ctx.inputs_sha = sha
            ctx.extra['impl'] = {'regression': 'gov-regression@1'}
            ctx.output = _validation_output(rep, sha)
            ctx.status = 'recorded'
    return {'decision_id': str(ctx.id), 'report': rep}


def validate_async(principal, aid, semver, focus=None):
    """Lanza la validación en un hilo (una a la vez por versión). Devuelve el estado del trabajo."""
    key = (aid, semver)
    with _JOBS_LOCK:
        cur = _JOBS.get(key)
        if cur and cur['state'] == 'running':
            return dict(cur)
        job = {'artifact': aid, 'semver': semver, 'state': 'running', 'started_at': time.time()}
        _JOBS[key] = job

    def run():
        try:
            out = validate(principal, aid, semver, focus=focus)
            rep = out['report']
            job.update(state='done', decision_id=out['decision_id'], finished_at=time.time(),
                       summary_es=rep.get('summary_es'), summary_en=rep.get('summary_en'),
                       outputs_changed=rep.get('outputs_changed'), report=rep)
        except Exception as e:  # noqa: BLE001
            log.warning('governance validate %s@%s: %s', aid, semver, type(e).__name__)
            job.update(state='error', error=f'{type(e).__name__}: {str(e)[:200]}', finished_at=time.time())
    try:
        from core import ai_usage
        target = ai_usage.bind(run) if hasattr(ai_usage, 'bind') else run
    except Exception:  # noqa: BLE001
        target = run
    threading.Thread(target=target, name=f'gov-validate-{aid}@{semver}', daemon=True).start()
    return dict(job)


def validation(aid, semver):
    """Último resultado: el trabajo en memoria si existe; si no, la última decisión governance.validate."""
    with _JOBS_LOCK:
        job = _JOBS.get((aid, semver))
        if job is not None:
            return dict(job)
    from core import governance
    if not governance._db_on():
        return None
    from sqlalchemy import text
    from ontology.db import session_scope
    with session_scope() as s:
        r = s.execute(text("SELECT id, output, recorded_at FROM decisions WHERE kind = 'governance.validate' AND "
                           "subject->>'artifact' = :a AND subject->>'semver' = :v ORDER BY recorded_at DESC LIMIT 1"),
                      {'a': aid, 'v': semver}).first()
        if r is None:
            return None
        o = r.output or {}
        rep = None
        if o.get('validation_blob'):
            from core import decisions
            try:
                d = decisions.get(s, r.id, redact=False, with_blobs=True)
                rep = ((d.get('blobs') or {}).get(o['validation_blob']) or {}).get('body')
            except Exception:  # noqa: BLE001
                rep = None
    return {'artifact': aid, 'semver': semver, 'state': 'done', 'decision_id': str(r.id),
            'finished_at': r.recorded_at.isoformat() if r.recorded_at else None, 'summary_es': o.get('summary_es'),
            'summary_en': o.get('summary_en'), 'outputs_changed': o.get('outputs_changed'), 'report': rep}


def latest_validation_id(session, selection):
    """La decisión governance.validate más reciente de la versión (selección de UN artefacto) o None."""
    from sqlalchemy import text
    if not isinstance(selection, dict) or len(selection) != 1:
        return None
    (aid, sv), = selection.items()
    r = session.execute(text("SELECT id FROM decisions WHERE kind = 'governance.validate' AND subject->>'artifact' = :a "
                             "AND subject->>'semver' = :v ORDER BY recorded_at DESC LIMIT 1"),
                        {'a': aid, 'v': sv}).first()
    return str(r.id) if r is not None else None


# ── programar, cancelar, aplicar ─────────────────────────────────────────────
def next_ny_close(now=None):
    """D5: los cambios de policy.broker_risk entran por defecto DESPUÉS del cierre de Nueva York (16:05 ET del
    próximo día hábil; sin feriados)."""
    from zoneinfo import ZoneInfo
    ny = ZoneInfo('America/New_York')
    now = (now or datetime.now(timezone.utc)).astimezone(ny)
    t = now.replace(hour=16, minute=5, second=0, microsecond=0)
    if now >= t or now.weekday() >= 5:
        t = t + timedelta(days=1)
    while t.weekday() >= 5:
        t = t + timedelta(days=1)
    return t.astimezone(timezone.utc)


def parse_effective_from(raw, selection):
    """'now' | None → None (inmediato; salvo policy.broker_risk → cierre de NY, D5) | 'ny_close' | ISO 8601.
    ValueError si el texto no es una fecha, no lleva zona o está a más de 90 días."""
    if raw is None or raw == '':
        return next_ny_close() if 'policy.broker_risk' in (selection or {}) else None
    s = str(raw).strip()
    if s.lower() == 'now':
        return None
    if s.lower() == 'ny_close':
        return next_ny_close()
    dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('effective_from debe llevar zona horaria (p. ej. 2026-10-14T21:00:00Z)')
    if dt > datetime.now(timezone.utc) + timedelta(days=90):
        raise ValueError('effective_from: como máximo 90 días adelante')
    return dt


def cancel_scheduled(session, principal, decision_id):
    """Cancela una activación PROGRAMADA que aún no empezó: decisión governance.activate 'rejected' con
    subject.cancels (la fila de gov_releases queda; refresh nunca la pondrá en vigor)."""
    from sqlalchemy import text

    from core import decisions, governance
    if not getattr(principal, 'is_human_pin', False):
        raise PermissionError('cancelar exige una persona autenticada con PIN (op:…)')
    session.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))'), {'k': 'khipus:governance'})
    pend = {p['decision_id']: p for p in governance.scheduled_pending(session)}
    p = pend.get(str(decision_id))
    if p is None:
        raise governance.GovernanceConflict(
            'not_cancellable', 'Esa activación no está programada o ya empezó: para volver atrás usa «Deshacer».',
            'That activation is not scheduled or has already started: to go back use "Undo".')
    with decisions.decision_scope('governance.activate', principal, session=session,
                                  subject={'cancels': p['decision_id'], 'release_hash': p['release_hash'],
                                           'effective_from': p['effective_from'], 'cancellation': True}) as ctx:
        ctx.cause('decision', p['decision_id'])
        ctx.output = {'cancelled': p['decision_id'], 'release_hash': p['release_hash']}
        ctx.status = 'rejected'
    return {'decision_id': str(ctx.id), 'cancelled': p['decision_id'], 'release_hash': p['release_hash'],
            'effective_from': p['effective_from']}


def apply_due():
    """Reloj (tras refresh): por cada activación programada cuya hora llegó (no cancelada) deja UNA decisión
    governance.activate 'executed' de system:governance_scheduler (subject.applies). Idempotente. Nunca lanza."""
    from core import governance
    if not governance._db_on():
        return 0
    try:
        from sqlalchemy import text

        from ontology.db import session_scope
        with session_scope() as s:
            s.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))'), {'k': 'khipus:governance'})
            due = governance.due_unapplied(s)
            if not due:
                return 0
            # revisión batch G: 'executed' solo si el release programado ESTÁ en vigor (si refresh falló o un
            # GOV_RELEASE fija otro, se reintenta en el próximo tic: nunca un "aplicado" que no rige)
            if governance.active().release_hash != (due[-1].subject or {}).get('release_hash'):
                log.warning('governance.apply_due: el release programado aún no está en vigor; se reintenta')
                return 0
            return record_applied(s, due)
    except Exception as e:  # noqa: BLE001
        log.warning('governance.apply_due: %s', type(e).__name__)
        return 0


def record_applied(s, due):
    """Una decisión governance.activate 'executed' de system:governance_scheduler (subject.applies) por cada
    programada de `due` (filas de governance.due_unapplied), en la sesión `s` (que ya tiene el candado). Las
    anteriores a la última quedaron superadas por ella: in_force dice la verdad de cada una."""
    from core import decisions, governance, identity
    who = identity.system('governance_scheduler')
    n = 0
    for r in due:
        sub = r.subject or {}
        with decisions.decision_scope('governance.activate', who, session=s,
                                      subject={'applies': str(r.id), 'release_hash': sub.get('release_hash'),
                                               'effective_from': sub.get('effective_from'),
                                               'scheduled_apply': True}) as ctx:
            ctx.cause('decision', str(r.id))
            ctx.effect('gov_release', sub.get('release_hash'))
            ctx.output = {'applied': str(r.id), 'release_hash': sub.get('release_hash'),
                          'in_force': governance.active().release_hash == sub.get('release_hash')}
            ctx.status = 'executed'
        n += 1
    return n


# ── atribución e historia ────────────────────────────────────────────────────
def attribution(session, decision_id):
    """Qué release y qué versión de cada artefacto regían la decisión `decision_id` (modo atribución §5.3).
    LookupError si no existe."""
    import uuid as _uuid

    from sqlalchemy import text
    try:
        did = _uuid.UUID(str(decision_id))
    except (TypeError, ValueError):
        raise LookupError('decision_id inválido') from None
    r = session.execute(text('SELECT id, kind, status, principal_id, recorded_at, valid_at, release_hash, graph_version, '
                             "manifest->'release' AS rel FROM decisions WHERE id = :i"), {'i': did}).first()
    if r is None:
        raise LookupError('decisión no encontrada')
    rel = r.rel or {}
    rr = session.execute(text('SELECT release_hash, semver, artifacts, effective_from, ratified, approval_decision_id '
                              'FROM gov_releases WHERE release_hash = :h'), {'h': r.release_hash}).first()
    arts, source = {}, 'manifest'
    if rr is not None:
        source = 'gov_releases'
        arts = {a: {'semver': v.get('semver'), 'hash': v.get('hash')} for a, v in sorted((rr.artifacts or {}).items())}
    else:
        arts = {a: {'semver': v, 'hash': None} for a, v in sorted((rel.get('semver') or {}).items())}
    pols = session.execute(text("SELECT ref_id, ref_hash FROM decision_refs WHERE decision_id = :i AND role = 'policy' "
                                'ORDER BY ref_id'), {'i': did}).all()
    cited = []
    for p in pols:
        aid, _, sv = str(p.ref_id).partition('@')
        inrel = arts.get(aid) or {}
        cited.append({'artifact': aid, 'semver': sv or None, 'hash': p.ref_hash,
                      'matches_release': (inrel.get('hash') == p.ref_hash) if p.ref_hash and inrel.get('hash')
                      else (inrel.get('semver') == sv if sv else None)})
    fb = rel.get('fallback') or {}
    label = rel.get('label') or ('db' if rr is not None else 'unknown')
    out = {'decision_id': str(r.id), 'kind': r.kind, 'status': r.status, 'principal_id': r.principal_id,
           'recorded_at': r.recorded_at.isoformat() if r.recorded_at else None,
           'graph_version': r.graph_version,
           'release': {'hash': r.release_hash, 'label': label, 'semver': rr.semver if rr is not None else None,
                       'effective_from': rr.effective_from.isoformat() if rr is not None and rr.effective_from else None,
                       'ratified': bool(rr.ratified) if rr is not None else None, 'source': source},
           'artifacts': arts, 'cited_policies': cited, 'fallback': fb}
    k = ', '.join(f"{a} {v['semver']}" for a, v in arts.items() if a in {c['artifact'] for c in cited}) or \
        ', '.join(f"{a} {v['semver']}" for a, v in list(arts.items())[:4])
    out['explain_es'] = (f"Esta decisión ({r.kind}) se tomó con el release {str(r.release_hash)[:8]}"
                         + (f" ({rr.semver})" if rr is not None else ' (del repositorio, sin aprobar)')
                         + (f'; versiones que la decidieron: {k}.' if k else '.')
                         + (f" Además leyó del repositorio, sin aprobar: {', '.join(sorted(fb))}." if fb else ''))
    out['explain_en'] = (f"This decision ({r.kind}) was made with release {str(r.release_hash)[:8]}"
                         + (f" ({rr.semver})" if rr is not None else ' (from the repository, unapproved)')
                         + (f'; versions that decided it: {k}.' if k else '.')
                         + (f" It also read from the repository, unapproved: {', '.join(sorted(fb))}." if fb else ''))
    return out


def history(session, limit=30):
    """Releases, decisiones governance.*, activaciones programadas, propuestas de la app (con su validación) y el
    «Deshacer» disponible (volver al release anterior a la última activación con PIN)."""
    from sqlalchemy import text

    from core import governance
    lim = max(1, min(100, int(limit)))
    rels = [{'release_hash': r.release_hash, 'semver': r.semver,
             'artifacts': {a: v.get('semver') for a, v in sorted((r.artifacts or {}).items())},
             'effective_from': r.effective_from.isoformat() if r.effective_from else None, 'ratified': r.ratified,
             'note_es': r.note_es, 'note_en': r.note_en, 'approval_decision_id': str(r.approval_decision_id),
             'validation_blob': r.validation_blob, 'recorded_at': r.recorded_at.isoformat() if r.recorded_at else None}
            for r in session.execute(text('SELECT * FROM gov_releases ORDER BY recorded_at DESC LIMIT :n'), {'n': lim})]
    decs = []
    for r in session.execute(text("SELECT id, kind, status, principal_id, auth, recorded_at, subject, output FROM decisions "
                                  "WHERE kind LIKE 'governance.%' ORDER BY recorded_at DESC LIMIT :n"), {'n': lim * 2}):
        sub = r.subject or {}
        decs.append({'decision_id': str(r.id), 'kind': r.kind, 'status': r.status, 'principal_id': r.principal_id,
                     'auth': r.auth, 'recorded_at': r.recorded_at.isoformat() if r.recorded_at else None,
                     'subject': {k: sub.get(k) for k in ('artifact', 'semver', 'artifacts', 'release_hash', 'changes',
                                                         'effective_from', 'scheduled', 'reactivation', 'cancels',
                                                         'applies', 'four_eyes', 'regression', 'bootstrap')
                                 if sub.get(k) is not None},
                     'summary_es': (r.output or {}).get('summary_es'), 'summary_en': (r.output or {}).get('summary_en')})
    last = session.execute(text(
        "SELECT d.id, d.subject, d.recorded_at FROM decisions d WHERE d.kind = 'governance.activate' AND d.auth = 'pin' "
        "AND d.status IN ('executed', 'approved') AND d.subject ? 'from_release' "
        "AND (d.subject->>'effective_from')::timestamptz <= clock_timestamp() "
        "AND NOT EXISTS (" + governance._CANCELLED_SQL.format(ref='d.id') + ") "
        "ORDER BY (d.subject->>'effective_from')::timestamptz DESC, d.recorded_at DESC LIMIT 1")).first()
    undo = None
    if last is not None:
        sub = last.subject or {}
        cur = governance.active().release_hash
        if sub.get('release_hash') == cur and sub.get('from_release') and sub.get('from_release') != cur:
            fr = session.execute(text('SELECT semver FROM gov_releases WHERE release_hash = :h'),
                                 {'h': sub['from_release']}).first()
            undo = {'decision_id': str(last.id), 'to_release': sub['from_release'],
                    'to_semver': fr.semver if fr is not None else None, 'changes': sub.get('changes')}
    app_props = [{'artifact': a, 'semver': sv, **{k: v for k, v in ent.items() if k != 'hash'}, 'hash': ent['hash']}
                 for (a, sv), ent in sorted(governance.registered().items()) if ent.get('origin') == 'app']
    return {'releases': rels, 'decisions': decs[:lim * 2], 'scheduled': governance.scheduled_pending(session),
            'app_proposals': app_props, 'undo': undo, 'in_force': governance.active().release_hash,
            'proposable': {a: _proposable_fields(a) for a in param_artifacts()}}


def _proposable_fields(aid):
    """Campos del formulario «Proponer cambio»: los afinables del artefacto con su valor VIGENTE."""
    from core import governance
    GL = _lint()
    try:
        cur = governance.section(aid)
        sv = governance.artifact_semver(aid)
    except Exception:  # noqa: BLE001
        return None
    fields = []
    for path, spec in sorted((GL.tunables().get(aid) or {}).items()):
        v = GL.get_path(cur, path)
        if v is None or isinstance(v, (dict, list, bool)):
            continue
        fields.append({'path': path, 'value': v, **{k: spec.get(k) for k in ('type', 'min', 'max', 'step', 'label_es',
                                                                               'label_en', 'help_es', 'help_en')}})
    return {'semver': sv, 'fields': fields}


def reset_for_tests():
    with _JOBS_LOCK:
        _JOBS.clear()
