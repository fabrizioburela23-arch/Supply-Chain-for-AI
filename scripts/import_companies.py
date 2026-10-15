#!/usr/bin/env python3
"""scripts/import_companies.py — terminal del importador de fichas khipus.company/1 (EXPANSION_5K E2.4).

    # 0) Lote 1 (CSV de la investigación 2026-10-14) → paquete khipus.import/1 (fichas nivel A + países + categorías)
    python scripts/import_companies.py --lote1 --out lote1.json
    # 0') Lote 2 (2026-10-15): las 386 fichas COMPLETAS → data/import/lotes/2026-10-15/bundle_lote2_completas.json.gz
    #     (fichas saneadas: solo FORMATO) + sanitize_log.json (cada cambio). --check = ¿los archivos están al día?
    #     --md = además el plan sobre el grafo de esta PC (sin DATABASE_URL: el catálogo) en Markdown simple.
    python scripts/import_companies.py --lote2 [--check] [--md docs/expansion/LOTE_2026-10-15_PLAN.md]

    # 1) PLAN (no escribe nada): qué se crea/fusiona/actualiza/omite, categorías por aprobar, "¿qué cambia?" y plan_sha.
    #    Con DATABASE_URL usa el grafo de la base; sin ella, el catálogo (snapshot).
    python scripts/import_companies.py --plan lote1.json --md docs/expansion/LOTE_2026-10-14_PLAN.md
    python scripts/import_companies.py --plan lote1.json --approve-cats     # aprobando las categorías del paquete
    # 1') PLAN EN EL SERVIDOR (sube el archivo y planea sobre el grafo de producción + vínculos pendientes): la huella
    #     que imprime es LA que exige --apply --server (la del plan local es otra: otro grafo, sin pendientes)
    python scripts/import_companies.py --plan lote1.json --server https://<app>.railway.app --pin 1234 [--md plan.md]

    # 2) APLICAR contra un servidor (PIN por X-Trade-Pin; sube el archivo en trozos ≤ 900 KB; 409 si el plan cambió)
    python scripts/import_companies.py --apply lote1.json --server https://<app>.railway.app --pin 1234 \
        --plan-sha <plan_sha> --confirm-db railway

    # 2') APLICAR directo a la base (--db): UNA decisión ontology.bulk_import del principal system:import_cli
    DATABASE_URL=... python scripts/import_companies.py --apply lote1.json --db --plan-sha <plan_sha> --confirm-db <nombre>

    # 3) DESHACER una corrida (de la más nueva a la más vieja) · 4) ver corridas
    python scripts/import_companies.py --rollback <run_id> --confirm-db <nombre> [--server URL --pin PIN | --db]
    python scripts/import_companies.py --runs [--server URL --pin PIN]

ANTES de --apply contra producción: copia de seguridad (Railway → Postgres → Backups). Nada se borra: deshacer = eventos.
"""
import argparse
import base64
import hashlib
import json
import os
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CHUNK = 900 * 1024


def _die(msg, code=2):
    print(f'❌ {msg}', file=sys.stderr)
    return code


def _http(server, path, body, pin, timeout=600):
    import requests
    r = requests.post(server.rstrip('/') + path, json=body, headers={'X-Trade-Pin': pin, 'X-Khipu-Actor': 'import_cli'},
                      timeout=timeout)
    try:
        data = r.json()
    except ValueError:
        data = {'error': r.text[:300]}
    return r.status_code, data


def _http_text(server, path, body, pin, timeout=600):
    import requests
    r = requests.post(server.rstrip('/') + path, json=body, headers={'X-Trade-Pin': pin, 'X-Khipu-Actor': 'import_cli'},
                      timeout=timeout)
    return r.status_code, r.text


def _upload(server, pin, path):
    """Sube el archivo en trozos comprimidos; devuelve el sha256 del contenido. Un `.gz` se sube DESCOMPRIMIDO (con su
    nombre sin `.gz`): el servidor lee JSON/JSONL y la huella es la del contenido."""
    name = os.path.basename(path)
    if name.endswith('.gz'):
        import gzip
        with gzip.open(path, 'rb') as fh:
            content = fh.read()
        name = name[:-3]
    else:
        with open(path, 'rb') as fh:
            content = fh.read()
    sha = hashlib.sha256(content).hexdigest()
    parts = [content[i:i + CHUNK] for i in range(0, len(content), CHUNK)] or [b'']
    for i, part in enumerate(parts):
        data = base64.b64encode(zlib.compress(part, 6)).decode('ascii')
        code, res = _http(server, '/api/ontology/import/files', {'name': name, 'sha256': sha, 'chunk': i,
                                                                  'chunks': len(parts), 'data': data, 'encoding': 'zlib'}, pin)
        if code >= 300:
            raise SystemExit(_die(f'subida trozo {i + 1}/{len(parts)}: {code} {res.get("error")}'))
        print(f'  trozo {i + 1}/{len(parts)} → {res.get("status")}')
    print(f'archivo guardado: sha {sha[:12]}… ({res.get("n_records")} fichas, {res.get("n_updates")} actualizaciones)')
    return sha


def _gz_text(path):
    import gzip
    with gzip.open(path, 'rt', encoding='utf-8') as fh:
        return fh.read()


def _lote2(CI, a):
    """--lote2 [--check] [--md]: arma el paquete saneado y el registro del lote 2026-10-15 (o comprueba que estén al
    día); con --md, además el plan sobre el grafo de esta PC."""
    import gzip
    d = a.lote2 or CI.LOTE2_DIR
    built = CI.build_lote_2026_10_15(d)
    if built['missing']:
        return _die(f'faltan {len(built["missing"])} fichas de la lista en {CI.LOTE2_FICHAS}: {built["missing"][:5]}', 1)
    valid, invalid = CI.validate_batch(built['bundle']['records'])
    bundle_txt, log_txt = CI.lote2_texts(built)
    bpath, lpath = os.path.join(d, CI.LOTE2_BUNDLE), os.path.join(d, CI.LOTE2_LOG)
    summ = built['log']['summary']
    print(f'lote 2026-10-15: {built["kept"]} fichas completas · válidas tras sanear {len(valid)} · inválidas '
          f'{len(invalid)} · reparadas {summ["fields_repaired"]} · quitadas {summ["fields_dropped"]} · rechazadas '
          f'{len(summ["rejected"])}')
    if a.check:
        probs = []
        if invalid:
            probs.append(f'{len(invalid)} fichas no validan tras sanear: {[i.get("record_id") for i in invalid[:5]]}')
        try:
            if _gz_text(bpath) != bundle_txt:
                probs.append(f'{CI.LOTE2_BUNDLE} no es el que se generaría hoy: corre --lote2 (sin --check)')
        except FileNotFoundError:
            probs.append(f'falta {CI.LOTE2_BUNDLE}: corre --lote2')
        try:
            with open(lpath, encoding='utf-8') as fh:
                if fh.read() != log_txt:
                    probs.append(f'{CI.LOTE2_LOG} no es el que se generaría hoy: corre --lote2 (sin --check)')
        except FileNotFoundError:
            probs.append(f'falta {CI.LOTE2_LOG}: corre --lote2')
        for p in probs:
            print('✗', p)
        if not probs:
            print('✓ paquete y registro del lote 2026-10-15 al día')
        return 1 if probs else 0
    if invalid:
        return _die(f'{len(invalid)} fichas no validan tras sanear (no se escribe nada): '
                    f'{[i.get("record_id") for i in invalid[:5]]}', 1)
    with open(bpath, 'wb') as fh:
        fh.write(gzip.compress(bundle_txt.encode('utf-8'), compresslevel=9, mtime=0))
    with open(lpath, 'w', encoding='utf-8') as fh:
        fh.write(log_txt)
    print(f'escrito {os.path.relpath(bpath)} y {os.path.relpath(lpath)} · reglas: {summ["by_rule"]}')
    if a.md:
        p = CI.plan(built['bundle']['records'], [], batch=built['bundle']['batch'], what_changes=not a.no_what_changes)
        md = CI.render_lote2_md(p, built, d)
        with open(a.md, 'w', encoding='utf-8') as fh:
            fh.write(md)
        print(f'plan: {json.dumps(p["counts"], ensure_ascii=False)} · plan_sha {p["plan_sha"]} → {a.md}')
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--lote1', nargs='?', const='', default=None, help='adaptar el lote 2026-10-14 (CSV) → paquete JSON')
    ap.add_argument('--lote2', nargs='?', const='', default=None,
                    help='lote 2026-10-15: 386 fichas completas → paquete saneado + registro (carpeta opcional)')
    ap.add_argument('--check', action='store_true', help='con --lote2: comprobar que los archivos están al día (no escribe)')
    ap.add_argument('--plan', default=None, help='paquete (.json) o fichas (.jsonl): calcular el plan')
    ap.add_argument('--apply', default=None, help='paquete a aplicar (exige --plan-sha y --confirm-db)')
    ap.add_argument('--rollback', default=None, help='run_id a deshacer')
    ap.add_argument('--runs', action='store_true', help='listar corridas')
    ap.add_argument('--out', default=None, help='salida del paquete (--lote1) o del plan completo (--plan, JSON)')
    ap.add_argument('--md', default=None, help='escribir el resumen del plan en Markdown')
    ap.add_argument('--approve-cats', action='store_true', help='aprobar en este lote las categorías del paquete (F-8)')
    ap.add_argument('--plan-sha', default=None, help='huella del plan revisado (obligatoria para aplicar)')
    ap.add_argument('--confirm-db', default=None, help='nombre EXACTO de la base (SELECT current_database())')
    ap.add_argument('--server', default=None, help='URL del servidor (aplicar por la API con PIN)')
    ap.add_argument('--pin', default=os.getenv('TRADE_PIN') or None, help='PIN de operador (X-Trade-Pin)')
    ap.add_argument('--db', action='store_true', help='escribir directo en DATABASE_URL (sin servidor)')
    ap.add_argument('--json', action='store_true', help='imprimir el resultado como JSON')
    ap.add_argument('--lang', default='es', choices=('es', 'en'))
    ap.add_argument('--no-what-changes', action='store_true', help='no calcular el "¿qué cambia?" del kernel')
    a = ap.parse_args(argv)

    from ontology import company_import as CI

    if a.lote2 is not None:
        return _lote2(CI, a)

    if a.lote1 is not None:
        b = CI.adapt_lote_2026_10_14(a.lote1 or None)
        out = a.out or 'lote_2026-10-14.json'
        with open(out, 'w', encoding='utf-8') as fh:
            json.dump({k: v for k, v in b.items() if k != 'warnings'}, fh, ensure_ascii=False)
        from collections import Counter
        print(f'{out}: {len(b["records"])} fichas, {len(b["updates"])} actualizaciones, {len(b["approve_categories"])} '
              f'categorías propuestas; avisos: {dict(Counter(w["code"] for w in b["warnings"]))}')
        return 0

    if a.plan and a.server:
        # el plan del SERVIDOR (grafo de producción + vínculos pendientes): su plan_sha es la huella que --apply --server exige
        if not a.pin:
            return _die('--server exige --pin (o TRADE_PIN en el entorno)')
        sha = _upload(a.server, a.pin, a.plan)
        b = CI.load_bundle(a.plan)
        body = {'file_sha': sha, 'actor': 'import_cli', 'fresh': 1, 'format': 'json', 'full': 1 if a.out else 0,
                'approve_categories': b.get('approve_categories') if a.approve_cats else []}
        code, res = _http(a.server, '/api/ontology/import/plan', body, a.pin)
        if code >= 300:
            return _die(f'plan en el servidor: {code} {res.get("error")} ({res.get("code")})', 1)
        p = res.get('plan') or {}
        if a.out:
            with open(a.out, 'w', encoding='utf-8') as fh:
                json.dump(p, fh, ensure_ascii=False, default=str)
        if a.md:
            code, md = _http_text(a.server, '/api/ontology/import/plan', dict(body, format='md', lang=a.lang, full=0), a.pin)
            with open(a.md, 'w', encoding='utf-8') as fh:
                fh.write(md)
        wc = p.get('what_changes') or {}
        b4, af = wc.get('before') or {}, wc.get('after') or {}
        keys = ('nodes', 'links', 'rho', 'tsmc_hit')
        what = {'before': {k: b4.get(k) for k in keys}, 'after': {k: af.get(k) for k in keys},
                'added_links': wc.get('added_links')} if wc.get('available') else \
            {k: wc.get(k) for k in ('reason', 'error') if k in wc}
        print(json.dumps({'server': a.server, 'file_sha': sha, 'plan_sha': p.get('plan_sha'), 'generation': p.get('generation'),
                          'graph_key': p.get('graph_key'), 'counts': p.get('counts'),
                          'pending_resolved': len(p.get('pending_resolved') or []) if 'pending_resolved' in p else None,
                          'what_changes': what},
                         ensure_ascii=False, indent=1, default=str))
        print(f'\nhuella del plan del servidor: {p.get("plan_sha")}  ← esta es la que exige --apply --server --plan-sha')
        return 0

    if a.plan:
        b = CI.load_bundle(a.plan)
        approve = b.get('approve_categories') if a.approve_cats else []
        p = CI.plan(b['records'], b['updates'], batch=b.get('batch'), approve_categories=approve,
                    what_changes=not a.no_what_changes)
        print('(plan LOCAL: la huella válida para --apply --server es la de `--plan ... --server URL --pin PIN`)', file=sys.stderr)
        if a.out:
            with open(a.out, 'w', encoding='utf-8') as fh:
                json.dump(p, fh, ensure_ascii=False, default=str)
        md = CI.render_summary(p, lang=a.lang)
        if a.md:
            with open(a.md, 'w', encoding='utf-8') as fh:
                fh.write(md)
        if a.json:
            print(json.dumps({'counts': p['counts'], 'plan_sha': p['plan_sha'], 'generation': p['generation'],
                              'what_changes': p.get('what_changes')}, ensure_ascii=False, indent=1, default=str))
        else:
            print(md)
        return 0

    if a.apply:
        if not a.plan_sha or not a.confirm_db:
            return _die('--apply exige --plan-sha (la huella del plan revisado) y --confirm-db (nombre exacto de la base)')
        if a.server:
            if not a.pin:
                return _die('--server exige --pin (o TRADE_PIN en el entorno)')
            sha = _upload(a.server, a.pin, a.apply)
            b = CI.load_bundle(a.apply)
            body = {'file_sha': sha, 'confirm_db': a.confirm_db, 'expect': {'plan_sha': a.plan_sha}, 'actor': 'import_cli',
                    'approve_categories': b.get('approve_categories') if a.approve_cats else []}
            code, res = _http(a.server, '/api/ontology/import/apply', body, a.pin)
            print(json.dumps(res, ensure_ascii=False, indent=1))
            return 0 if code < 300 else 1
        if not a.db:
            return _die('elige --server URL --pin PIN (por la API) o --db (directo a DATABASE_URL)')
        if not os.getenv('DATABASE_URL'):
            return _die('falta DATABASE_URL')
        from ontology.db import init_schema, session_scope
        init_schema(retries=1)
        b = CI.load_bundle(a.apply)
        approve = b.get('approve_categories') if a.approve_cats else []
        try:
            p = CI.plan(b['records'], b['updates'], batch=b.get('batch'), approve_categories=approve, what_changes=False)
            res = CI.apply_run(session_scope, p, None, confirm_db=a.confirm_db, expect={'plan_sha': a.plan_sha},
                               log=print)
        except CI.ImportProblem as e:
            return _die(f'{e} ({e.code})', 1)
        print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
        return 0

    if a.rollback:
        if not a.confirm_db:
            return _die('--rollback exige --confirm-db')
        if a.server:
            code, res = _http(a.server, '/api/ontology/import/rollback',
                              {'run_id': a.rollback, 'confirm_db': a.confirm_db, 'actor': 'import_cli'}, a.pin or '')
            print(json.dumps(res, ensure_ascii=False, indent=1))
            return 0 if code < 300 else 1
        if not os.getenv('DATABASE_URL'):
            return _die('falta DATABASE_URL (o usa --server)')
        from ontology.db import init_schema, session_scope
        init_schema(retries=1)
        try:
            with session_scope() as s:
                res = CI.rollback_run(s, a.rollback, None, confirm_db=a.confirm_db)
        except CI.ImportProblem as e:
            return _die(f'{e} ({e.code})', 1)
        print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
        return 0

    if a.runs:
        if a.server:
            import requests
            r = requests.get(a.server.rstrip('/') + '/api/ontology/import/runs', timeout=60)
            print(json.dumps(r.json(), ensure_ascii=False, indent=1))
            return 0
        if not os.getenv('DATABASE_URL'):
            return _die('falta DATABASE_URL (o usa --server)')
        from ontology.db import init_schema, session_scope
        init_schema(retries=1)
        with session_scope() as s:
            print(json.dumps(CI.list_runs(s), ensure_ascii=False, indent=1))
        return 0

    ap.print_help()
    return 0


if __name__ == '__main__':
    sys.exit(main())
