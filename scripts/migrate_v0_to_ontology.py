#!/usr/bin/env python3
"""scripts/migrate_v0_to_ontology.py — Fase 1: migra data/grafo_v0.json (el
snapshot congelado en Fase 0) a la ontología (Postgres, tabla events + vistas
materializadas objects/links).

Reglas de fecha (documentadas — no son arbitrarias):
- Empresas y objetos de ontología (Tech/Policy/Country/…): valid_from =
  GENESIS ('2000-01-01'). No tenemos fecha de fundación real para las 463
  empresas; GENESIS representa "desde que empezamos a rastrear este universo"
  — es anterior a todos los hechos temporales curados (el más antiguo es de
  2010), así que ningún as_of relevante los excluye por accidente.
- Relaciones de cadena de suministro SIN fecha propia (los 1163 links crudos):
  valid_from = GENESIS también (fuente: 'migration_v0_links'). Representan
  "según nuestro conocimiento, esta relación siempre estuvo vigente" — es una
  aproximación honesta: no inventamos una fecha de inicio que no tenemos.
- Hechos temporales curados (105 en temporal_facts, 86 son aristas): usan su
  valid_from/valid_until REAL (fuente: 'migration_v0_temporal'). Estos son los
  que dan valor real al time-travel (ej. Qualcomm perdió a Huawei 2019-2021).

Es NORMAL que una misma pareja (source,target) tenga más de una fila en
`links`: una genérica desde GENESIS y otra con fecha real desde los hechos
temporales — son evidencias distintas, no un error. Bitemporal = puede haber
más de una "versión de la verdad" para el mismo par en el tiempo.

Uso:
    export DATABASE_URL=postgresql://...
    python scripts/migrate_v0_to_ontology.py [--dry-run] [--reset [--confirm-db NOMBRE]]

--reset / REMIGRATE_ON_BOOT (auditoría estructural 2026-09-30, #6) — SALVAGUARDAS:
  · solo se borran las tablas del GRAFO que esta migración reconstruye
    (RESET_TABLES: links, events, objects). Antes era Base.metadata.drop_all,
    que también borraba corretaje (broker_*: el libro de clientes), MCP,
    research_*, alertas, propuestas e historial de insights;
  · si alguna tabla broker_* tiene filas, se NIEGA (el libro de clientes jamás
    convive con una re-migración);
  · desde el arranque (REMIGRATE_ON_BOOT) el valor de la variable debe ser
    EXACTAMENTE el nombre de la base (SELECT current_database(), p.ej.
    'railway'); '1'/'true' ya no bastan;
  · UNA SOLA VEZ por valor (revisión 2026-09-30): la tabla `remigrate_log`
    recuerda cada re-migración del arranque. Si la variable se queda puesta,
    los reinicios siguientes (restartPolicy ALWAYS, redeploys) NO vuelven a
    borrar el grafo: se niegan con un aviso bilingüe en el log. Para re-migrar
    otra vez A PROPÓSITO: REMIGRATE_ON_BOOT=<nombre>:2 (o :3, :fecha… — lo que
    va después de ':' es una etiqueta libre; el mismo valor nunca corre dos veces);
  · desde la CLI, --reset sin --confirm-db solo vale contra una base LOCAL
    (localhost / 127.0.0.1 / ::1 / socket unix) que NO se llame 'railway' y
    fuera de Railway; con cualquier otro host (p. ej. la URL pública
    …proxy.rlwy.net de producción copiada a una terminal) hace falta
    --confirm-db NOMBRE.
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# El centinela se define UNA vez en ontology/service.py (G4b): quien serialice
# un valid_from lo compara con `is_genesis` para marcar `valid_from_known: false`.
from ontology.service import GENESIS_SENTINEL as GENESIS  # noqa: E402


# Tablas que --reset / REMIGRATE_ON_BOOT pueden borrar: SOLO las del grafo
# que esta migración vuelve a construir. Todo lo demás (broker_*, mcp_*,
# research_*, alerts, proposed_actions, insight_snapshots) se conserva.
RESET_TABLES = ('links', 'events', 'objects')
PROTECTED_PREFIXES = ('broker_',)     # con filas → la re-migración se niega

# Marca interna: la CLI local con --reset explícito no necesita el nombre de la base.
_CLI_EXPLICIT = object()

# Registro de re-migraciones del ARRANQUE (una sola vez por valor de
# REMIGRATE_ON_BOOT). Tabla propia, fuera de RESET_TABLES → sobrevive al reset.
REMIGRATE_LOG_TABLE = 'remigrate_log'
REMIGRATE_STALE_MIN = 15      # un 'started' sin terminar más viejo que esto = intento fallido
_LOCAL_HOSTS = ('localhost', '127.0.0.1', '::1')
_PROD_DB_NAMES = ('railway',)  # nombre de la base del plugin Postgres de Railway


class RemigrateRefused(RuntimeError):
    """La re-migración destructiva se negó (nada se borró)."""


def _in_production():
    try:
        from core.pin import in_production
        return in_production()
    except Exception:  # noqa: BLE001 — sin flask/core: mismas variables de Railway
        return any((os.getenv(n) or '').strip() for n in
                   ('RAILWAY_ENVIRONMENT', 'RAILWAY_ENVIRONMENT_NAME', 'RAILWAY_PROJECT_ID'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true', help='no escribe nada, solo valida y cuenta')
    ap.add_argument('--reset', action='store_true',
                    help='borra SOLO las tablas del grafo (links/events/objects) antes de migrar (destructivo)')
    ap.add_argument('--confirm-db', default=None,
                    help='nombre exacto de la base (obligatorio con --reset en producción)')
    ap.add_argument('--graph', default=os.path.join(os.path.dirname(__file__), '..', 'data', 'grafo_v0.json'))
    args = ap.parse_args()
    confirm = args.confirm_db
    if args.reset and confirm is None:
        if not _in_production() and _local_reset_ok(os.getenv('DATABASE_URL', '')):
            confirm = _CLI_EXPLICIT      # base local de desarrollo: el --reset tecleado basta
        else:
            # host remoto (p. ej. la URL pública de Railway copiada a la terminal),
            # base 'railway' o dentro de Railway: se niega ANTES de conectar.
            print('❌ re-migración NEGADA: --reset contra una base que no es local (o dentro de '
                  'Railway) exige --confirm-db <nombre exacto de la base>. Nada se borró. '
                  '/ re-migration REFUSED: --reset against a non-local database (or inside Railway) '
                  'requires --confirm-db <exact database name>. Nothing was deleted.', file=sys.stderr)
            sys.exit(2)
    try:
        ok = run_migration(reset=args.reset, dry_run=args.dry_run, graph_path=args.graph,
                           confirm_db=confirm if args.reset else None)
    except RemigrateRefused as e:
        print(f'❌ {e}', file=sys.stderr)
        sys.exit(2)
    if not ok:
        sys.exit(1)


def _local_reset_ok(url):
    """¿`url` apunta a una base LOCAL de desarrollo (y no a una llamada
    'railway')? Solo entonces la CLI acepta --reset sin --confirm-db."""
    if not url:
        return False
    try:
        from sqlalchemy.engine import make_url
        u = make_url(url.replace('postgres://', 'postgresql://', 1) if url.startswith('postgres://') else url)
    except Exception:  # noqa: BLE001 — URL ilegible → no es "local seguro"
        return False
    if (u.database or '').strip().lower() in _PROD_DB_NAMES:
        return False
    host = (u.host or '').strip().strip('[]').lower()
    qhost = u.query.get('host') if hasattr(u, 'query') else None
    if isinstance(qhost, (list, tuple)):
        qhost = qhost[0] if qhost else None
    if not host:
        # sin host: socket unix por defecto de libpq, o ?host=/ruta/al/socket
        return (not qhost) or str(qhost).startswith('/')
    return host in _LOCAL_HOSTS or host.startswith('/')


def _current_database(engine):
    from sqlalchemy import text
    with engine.connect() as c:
        return c.execute(text('SELECT current_database()')).scalar()


def _protected_tables_with_rows(engine):
    """Tablas broker_* (libro de clientes) que tienen al menos una fila."""
    from sqlalchemy import inspect, text
    names = [t for t in inspect(engine).get_table_names()
             if any(t.startswith(p) for p in PROTECTED_PREFIXES)]
    llenas = []
    with engine.connect() as c:
        for t in names:
            if c.execute(text(f'SELECT 1 FROM "{t}" LIMIT 1')).first() is not None:
                llenas.append(t)
    return sorted(llenas)


def check_reset_allowed(engine, confirm_db=None):
    """Lanza RemigrateRefused si el borrado NO está autorizado. Devuelve el
    nombre de la base. `confirm_db`: nombre confirmado por el operador; None →
    se lee REMIGRATE_ON_BOOT (camino del arranque del server)."""
    dbname = _current_database(engine)
    if confirm_db is _CLI_EXPLICIT and (dbname or '').lower() in _PROD_DB_NAMES:
        raise RemigrateRefused(
            f"re-migración NEGADA: la base se llama '{dbname}' (producción de Railway): hace falta "
            f"--confirm-db {dbname}. Nada se borró. / re-migration REFUSED: database '{dbname}' "
            f"looks like Railway production: pass --confirm-db {dbname}. Nothing was deleted.")
    if confirm_db is not _CLI_EXPLICIT:
        raw = (os.getenv('REMIGRATE_ON_BOOT', '') if confirm_db is None else str(confirm_db)).strip()
        # arranque: '<base>' o '<base>:<etiqueta>' (la etiqueta permite repetir a propósito)
        got = raw.split(':', 1)[0].strip() if confirm_db is None else raw
        if not dbname or got != dbname:
            raise RemigrateRefused(
                f"re-migración NEGADA: la confirmación debe ser EXACTAMENTE el nombre de la base "
                f"('{dbname}'); llegó '{got[:40]}'. Nada se borró. Para re-migrar pon "
                f"REMIGRATE_ON_BOOT={dbname} (o --confirm-db {dbname}) y quítala después. "
                f"/ re-migration REFUSED: the confirmation must equal the database name "
                f"('{dbname}'); got '{got[:40]}'. Nothing was deleted.")
    llenas = _protected_tables_with_rows(engine)
    if llenas:
        raise RemigrateRefused(
            f"re-migración NEGADA: hay datos de clientes de corretaje en {', '.join(llenas)} — "
            f"la re-migración nunca corre junto al libro de clientes. Nada se borró. "
            f"/ re-migration REFUSED: brokerage client data present in {', '.join(llenas)}. "
            f"Nothing was deleted.")
    return dbname


def _ensure_remigrate_log(conn):
    from sqlalchemy import text
    conn.execute(text(
        f'CREATE TABLE IF NOT EXISTS {REMIGRATE_LOG_TABLE} ('
        ' id SERIAL PRIMARY KEY, dbname TEXT NOT NULL, flag TEXT NOT NULL,'
        " status TEXT NOT NULL DEFAULT 'started',"
        ' started_at TIMESTAMPTZ NOT NULL DEFAULT now(), done_at TIMESTAMPTZ)'))


def claim_boot_remigration(engine, dbname, flag):
    """Reserva la re-migración del ARRANQUE para este valor de REMIGRATE_ON_BOOT
    (una sola vez). Devuelve el id de la fila 'started'; lanza RemigrateRefused
    si ese valor ya corrió ('done') o si otra corrida empezó hace menos de
    REMIGRATE_STALE_MIN minutos. Tabla bloqueada durante el chequeo → dos
    arranques simultáneos no pueden reclamarla a la vez."""
    from sqlalchemy import text
    with engine.begin() as c:
        _ensure_remigrate_log(c)
        c.execute(text(f'LOCK TABLE {REMIGRATE_LOG_TABLE} IN SHARE ROW EXCLUSIVE MODE'))
        prev = c.execute(text(
            f"SELECT status, COALESCE(done_at, started_at) FROM {REMIGRATE_LOG_TABLE} "
            f"WHERE dbname = :d AND flag = :f AND (status = 'done' OR "
            f"(status = 'started' AND started_at > now() - make_interval(mins => :m))) "
            f"ORDER BY started_at DESC LIMIT 1"),
            {'d': dbname, 'f': flag, 'm': REMIGRATE_STALE_MIN}).first()
        if prev is not None:
            when = prev[1].isoformat(timespec='minutes') if prev[1] else '?'
            if prev[0] == 'done':
                raise RemigrateRefused(
                    f"re-migración NEGADA: REMIGRATE_ON_BOOT='{flag}' YA se ejecutó ({when}) y corre una "
                    f"sola vez — QUITA la variable en Railway (Variables → REMIGRATE_ON_BOOT → borrar). "
                    f"Para re-migrar otra vez a propósito usa REMIGRATE_ON_BOOT={dbname}:2. Nada se borró. "
                    f"/ re-migration REFUSED: REMIGRATE_ON_BOOT='{flag}' already ran ({when}); it runs "
                    f"once — REMOVE the variable in Railway. To re-migrate again on purpose use "
                    f"REMIGRATE_ON_BOOT={dbname}:2. Nothing was deleted.")
            raise RemigrateRefused(
                f"re-migración NEGADA: otra re-migración con '{flag}' empezó a las {when} y sigue en curso. "
                f"Nada se borró. / re-migration REFUSED: another run with '{flag}' started at {when} "
                f"and is still in progress. Nothing was deleted.")
        return c.execute(text(
            f"INSERT INTO {REMIGRATE_LOG_TABLE} (dbname, flag, status) VALUES (:d, :f, 'started') RETURNING id"),
            {'d': dbname, 'f': flag}).scalar()


def _finish_boot_remigration(engine, row_id, status):
    from sqlalchemy import text
    try:
        with engine.begin() as c:
            c.execute(text(f'UPDATE {REMIGRATE_LOG_TABLE} SET status = :s, done_at = now() WHERE id = :i'),
                      {'s': status, 'i': row_id})
    except Exception:  # noqa: BLE001 — el registro nunca tumba la migración
        pass


def remigrate_flag_warning():
    """Para /api/health o /api/diagnostics: si REMIGRATE_ON_BOOT sigue puesta,
    devuelve un aviso bilingüe (y si ese valor ya se ejecutó, cuándo). None si
    la variable no está. Nunca lanza."""
    flag = (os.getenv('REMIGRATE_ON_BOOT') or '').strip()
    if not flag:
        return None
    out = {'code': 'remigrate_flag_set', 'flag': flag[:60], 'already_ran_at': None,
           'warning': 'REMIGRATE_ON_BOOT sigue configurada en Railway: quítala (la re-migración corre una sola vez).',
           'warning_en': 'REMIGRATE_ON_BOOT is still set in Railway: remove it (the re-migration runs only once).'}
    try:
        from sqlalchemy import inspect, text

        from ontology.db import _get_engine, ontology_available
        if not ontology_available():
            return out
        engine = _get_engine()
        if REMIGRATE_LOG_TABLE not in inspect(engine).get_table_names():
            return out
        with engine.connect() as c:
            v = c.execute(text(f"SELECT max(done_at) FROM {REMIGRATE_LOG_TABLE} "
                               f"WHERE flag = :f AND status = 'done'"), {'f': flag}).scalar()
        out['already_ran_at'] = v.isoformat() if v else None
    except Exception:  # noqa: BLE001
        pass
    return out


def reset_graph_tables(engine, log=print):
    """DROP SOLO de RESET_TABLES (en orden de FKs). No toca ninguna otra tabla."""
    from ontology.models import Base
    tables = [Base.metadata.tables[t] for t in RESET_TABLES if t in Base.metadata.tables]
    Base.metadata.drop_all(engine, tables=tables)
    log(f"⚠️  --reset: borradas SOLO {', '.join(t.name for t in tables)} "
        f"(corretaje, MCP, research, alertas y propuestas se conservan)")


def run_migration(reset=False, dry_run=False, graph_path=None, log=print, confirm_db=None):
    """Núcleo reutilizable de la migración v0 → ontología. Lo llama main() (CLI)
    y el hook REMIGRATE_ON_BOOT del server (para re-migrar producción sin CLI).
    `log`: función de progreso (print o logger.info). reset=True es DESTRUCTIVO
    (DROP de links/events/objects) y exige confirmación (ver check_reset_allowed):
    si se niega lanza RemigrateRefused SIN borrar nada. Devuelve True si migró
    (o dry-run), False si falló."""
    graph_path = graph_path or os.path.join(os.path.dirname(__file__), '..', 'data', 'grafo_v0.json')

    from ontology.db import ontology_available, init_schema, session_scope, _get_engine
    if not ontology_available():
        log('❌ DATABASE_URL no está configurada.')
        return False

    with open(graph_path, 'r', encoding='utf-8') as f:
        g = json.load(f)

    nodes = g['nodes']
    links = g['links']
    ontology_objects = (g.get('ontology') or {}).get('objects', [])
    temporal_facts = g.get('temporal_facts') or []

    log(f'Snapshot: {len(nodes)} empresas, {len(links)} links crudos, '
        f'{len(ontology_objects)} objetos de ontología, {len(temporal_facts)} hechos temporales')

    if dry_run:
        edges_in_facts = [f for f in temporal_facts if f.get('object_type') == 'node']
        log(f'[dry-run] Se crearían: {len(nodes) + len(ontology_objects)} objetos, '
            f'{len(links)} links base (GENESIS) + {len(edges_in_facts)} links con fecha real')
        return True

    from ontology.service import apply_event

    engine = _get_engine()
    boot_claim = None
    if reset:
        try:
            dbname = check_reset_allowed(engine, confirm_db)
            if confirm_db is None:        # arranque (REMIGRATE_ON_BOOT): una sola vez por valor
                boot_claim = claim_boot_remigration(
                    engine, dbname, (os.getenv('REMIGRATE_ON_BOOT') or '').strip()[:120])
        except RemigrateRefused as e:
            log(f'❌ {e}')
            raise
        log(f"⚠️  --reset confirmado para la base '{dbname}'")
    try:
        if reset:
            reset_graph_tables(engine, log=log)
        _migrate_graph(nodes, links, ontology_objects, temporal_facts, init_schema, session_scope,
                       apply_event, log)
    except BaseException:
        if boot_claim is not None:
            _finish_boot_remigration(engine, boot_claim, 'failed')   # el próximo arranque reintenta
        raise
    if boot_claim is not None:
        _finish_boot_remigration(engine, boot_claim, 'done')
        log('✅ re-migración registrada: este valor de REMIGRATE_ON_BOOT ya no volverá a borrar nada. '
            'QUITA la variable de Railway.')
    return True


def _migrate_graph(nodes, links, ontology_objects, temporal_facts, init_schema, session_scope,
                   apply_event, log):
    init_schema()

    t0 = time.time()
    known_ids = {n['id'] for n in nodes} | {o['id'] for o in ontology_objects}

    with session_scope() as s:
        for n in nodes:
            props = {k: v for k, v in n.items() if k not in ('id', 'label')}
            apply_event(s, 'ObjectCreated', {'label': n.get('label') or n['id'], 'type': 'Company', 'properties': props},
                        valid_from=GENESIS, source='migration_v0', actor='script:migrate_v0_to_ontology',
                        object_id=n['id'])
        for o in ontology_objects:
            apply_event(s, 'ObjectCreated', {'label': o.get('label') or o['id'], 'type': o.get('type', 'Org'), 'properties': {}},
                        valid_from=GENESIS, source='migration_v0', actor='script:migrate_v0_to_ontology',
                        object_id=o['id'])
        s.flush()
        log(f'✅ {len(nodes) + len(ontology_objects)} objetos creados ({time.time()-t0:.1f}s)')

        skipped = 0
        for l in links:
            src, tgt = l.get('source'), l.get('target')
            if src not in known_ids or tgt not in known_ids or src == tgt:
                skipped += 1
                continue
            props = {'rel_label': l.get('rel') or ''}
            # G4c: el snapshot (nodes/merge_graph.js) trae conf/verified por link;
            # el motor de matrices (matrix/engine._eff_weight) multiplica el peso
            # por properties.confidence. Solo se copian si el snapshot los trae.
            if l.get('conf') is not None:
                props['confidence'] = l.get('conf')
            if l.get('verified') is not None:
                props['verified'] = bool(l.get('verified'))
            if l.get('since'):
                props['since'] = l.get('since')
            apply_event(s, 'LinkCreated',
                        {'rel_type': l.get('type') or 'supply', 'weight': l.get('w'), 'properties': props},
                        valid_from=GENESIS, source='migration_v0_links', actor='script:migrate_v0_to_ontology',
                        object_id=src, target_id=tgt)
        s.flush()
        log(f'✅ {len(links) - skipped} links base creados ({skipped} saltados) ({time.time()-t0:.1f}s)')

        edges = [f for f in temporal_facts if f.get('object_type') == 'node']
        skipped_t = 0
        for f in edges:
            subj, obj = f.get('subject'), f.get('object')
            if subj not in known_ids or obj not in known_ids or subj == obj:
                skipped_t += 1
                continue
            apply_event(s, 'LinkCreated',
                        {'rel_type': f.get('rel') or 'supply',
                         'properties': {'headline': (f.get('meta') or {}).get('headline', ''),
                                        'confidence': f.get('confidence'), 'predicate': f.get('predicate')}},
                        valid_from=f.get('valid_from') or GENESIS, valid_to=f.get('valid_until'),
                        source='migration_v0_temporal', actor='script:migrate_v0_to_ontology',
                        object_id=subj, target_id=obj)
        s.flush()
        log(f'✅ {len(edges) - skipped_t} hechos temporales creados ({skipped_t} saltados) ({time.time()-t0:.1f}s)')

        # ── Factores sistémicos + Asientos (capa multicapa) ──────────────────
        # NO vienen en grafo_v0.json (ese snapshot son empresas y sus links):
        # viven en data/multicapa_factors_seats.json, que produjo
        # scripts/ingest_multicapa.py a partir del documento de Fabrizio.
        # Sin este paso, una re-migración deja la ontología a medias: sin
        # factores no hay FACTOR LIST/FIRE, ni hiperaristas en la fragilidad
        # del motor de matrices, y Activar/DesactivarFactor quedan sin objeto.
        n_fact, n_aff, n_seat = _restore_factors_and_seats(s, known_ids, log)
        s.flush()
        log(f'✅ {n_fact} factores (latentes) + {n_aff} vínculos affects + {n_seat} asientos ({time.time()-t0:.1f}s)')

    log(f'🎉 Migración completa en {time.time()-t0:.1f}s')


# Nivel LATENTE de los factores. Lección registrada en docs/ESTADO.md: cargar
# los ~70 factores a su severidad de CRISIS pone ρ(T) en 2.63 y satura las
# cascadas (todo al 100%) — "todas las crisis a la vez" no es un escenario
# real. Viven en 1.0 y su nivel de crisis queda en `severity_crisis`, que es
# lo que disparan /api/matrix/factor/fire (what-if) y la Acción ActivarFactor
# (persistente). OJO con la escala: el documento usa 0-10, no 0-5.
FACTOR_LATENT_SEVERITY = 1.0


def _restore_factors_and_seats(s, known_ids, log=print):
    """Carga data/multicapa_factors_seats.json en la ontología. Devuelve
    (n_factores, n_links_affects, n_asientos). Si el archivo no está, no es un
    error: se avisa y se sigue (la migración base ya es útil)."""
    from ontology.service import apply_event

    path = os.path.join(os.path.dirname(__file__), '..', 'data', 'multicapa_factors_seats.json')
    if not os.path.exists(path):
        log('⚠️  data/multicapa_factors_seats.json no está — se omiten factores y asientos.')
        return 0, 0, 0
    with open(path, 'r', encoding='utf-8') as fh:
        data = json.load(fh)

    factors = data.get('factors') or []
    seats = data.get('seats') or []

    n_fact = n_aff = 0
    for f in factors:
        fid = (f.get('id') or '').strip()
        if not fid:
            continue
        members = f.get('members') or {}
        # Solo miembros que EXISTEN: un link 'affects' colgante corrompería la
        # matriz (mismo criterio que la Acción CrearFactor).
        pairs = [(m, float(c)) for m, c in members.items() if m in known_ids]
        if not pairs:
            continue
        apply_event(s, 'ObjectCreated', {
            'label': f.get('label') or fid, 'type': 'Factor',
            'properties': {
                'severity': FACTOR_LATENT_SEVERITY,
                'severity_crisis': float(f['severity']) if f.get('severity') is not None else None,
                'razon': f.get('rationale') or '',
                'fuente': 'multicapa', 'activo': False,
            },
        }, valid_from=GENESIS, source='migration_multicapa',
           actor='script:migrate_v0_to_ontology', object_id=fid)
        n_fact += 1
        for m, coef in pairs:
            apply_event(s, 'LinkCreated',
                        {'rel_type': 'affects', 'weight': coef, 'properties': {'factor': True}},
                        valid_from=GENESIS, source='migration_multicapa',
                        actor='script:migrate_v0_to_ontology', object_id=fid, target_id=m)
            n_aff += 1

    n_seat = 0
    for st in seats:
        sid = (st.get('id') or '').strip()
        if not sid:
            continue
        apply_event(s, 'ObjectCreated', {
            'label': st.get('label') or sid, 'type': 'Seat',
            'properties': st.get('props') or {},
        }, valid_from=GENESIS, source='migration_multicapa',
           actor='script:migrate_v0_to_ontology', object_id=sid)
        n_seat += 1

    return n_fact, n_aff, n_seat


if __name__ == '__main__':
    main()
