#!/usr/bin/env python3
"""scripts/reconcile_v0_to_ontology.py — G3: reconciliar el catálogo
(data/grafo_v0.json) con la ontología en Postgres SIN borrar nada.

Uso (la lógica vive en ontology/reconcile.py; esto es la terminal):

    # 1) Solo mirar (por defecto): escribe reconcile_out/revision_<fecha>.md y .json
    python scripts/reconcile_v0_to_ontology.py

    # 2) Aplicar lo seguro (alias + repetidos exactos). Pide el nombre de la base.
    python scripts/reconcile_v0_to_ontology.py --apply --confirm-db railway

    # 3) Aplicar también otras categorías (SOLO con el OK de Fabrizio — decisión D5)
    python scripts/reconcile_v0_to_ontology.py --apply --confirm-db railway --include alias,duplicates,direction

    # 4) Deshacer una corrida (con nuevos eventos; la historia queda)
    python scripts/reconcile_v0_to_ontology.py --rollback-run <run_id> --confirm-db railway

    # 5) Ver corridas anteriores
    python scripts/reconcile_v0_to_ontology.py --list-runs

ANTES de --apply contra producción: copia de seguridad (Railway → Postgres →
Backups → Create backup, o `pg_dump "$DATABASE_URL" > respaldo.sql`).
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--graph', default=None, help='snapshot (default data/grafo_v0.json)')
    ap.add_argument('--out', default='reconcile_out', help='carpeta de salida del dry-run (default reconcile_out/)')
    ap.add_argument('--apply', action='store_true', help='emitir los eventos (requiere --confirm-db)')
    ap.add_argument('--include', default='alias,duplicates',
                    help='categorías a aplicar, separadas por coma (default: alias,duplicates — lo seguro)')
    ap.add_argument('--confirm-db', default=None, help='nombre EXACTO de la base (SELECT current_database())')
    ap.add_argument('--rollback-run', default=None, help='run_id a deshacer (requiere --confirm-db)')
    ap.add_argument('--list-runs', action='store_true')
    ap.add_argument('--json', action='store_true', help='imprimir el resultado como JSON')
    ap.add_argument('--lang', default='es', choices=('es', 'en'), help='idioma del informe Markdown')
    args = ap.parse_args(argv)

    if not os.getenv('DATABASE_URL'):
        print('❌ Falta DATABASE_URL (la de Railway, o una base local).', file=sys.stderr)
        return 2
    from ontology import reconcile as R
    from ontology.db import session_scope

    if args.list_runs:
        with session_scope() as s:
            runs = R.list_runs(s)
        print(json.dumps(runs, indent=1, ensure_ascii=False))
        return 0

    if args.rollback_run:
        try:
            with session_scope() as s:
                res = R.rollback_run(s, args.rollback_run, confirm_db=args.confirm_db)
        except R.ReconcileError as e:
            print(f'❌ {e}', file=sys.stderr)
            return 1
        print(json.dumps(res, indent=1, ensure_ascii=False))
        return 0

    snap = R.load_snapshot(args.graph)
    if args.apply:
        include = [x.strip() for x in args.include.split(',') if x.strip()]
        try:
            res = R.apply_plan(session_scope, snap, include=include, confirm_db=args.confirm_db, log=print)
        except R.ReconcileError as e:
            print(f'❌ {e}', file=sys.stderr)
            return 1
        print(json.dumps(res, indent=1, ensure_ascii=False))
        print(f"\n✅ Corrida {res['run_id']} aplicada. Para deshacer: --rollback-run {res['run_id']} --confirm-db {res['db']}")
        return 0

    with session_scope() as s:
        plan = R.build_plan(s, snap)
        dbname = R._db_name(s)
    md = R.render_markdown(plan, dbname=dbname, lang=args.lang, limit_rows=500)
    os.makedirs(args.out, exist_ok=True)
    stamp = plan['as_of'].replace('+00:00', 'Z').replace(':', '')
    pj, pm = os.path.join(args.out, f'revision_{stamp}.json'), os.path.join(args.out, f'revision_{stamp}.md')
    with open(pj, 'w', encoding='utf-8') as f:
        json.dump(plan, f, indent=1, ensure_ascii=False)
    with open(pm, 'w', encoding='utf-8') as f:
        f.write(md)
    if args.json:
        print(json.dumps(plan['summary'], indent=1, ensure_ascii=False))
    else:
        print(md)
    print(f'\n📄 Guardado: {pm} y {pj}  (solo lectura: nada se cambió)', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
