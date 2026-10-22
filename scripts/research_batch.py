"""scripts/research_batch.py — investiga empresas con la API de Claude (búsqueda web) y escribe fichas khipus.company/1.

Para gastar los créditos de API (sirven para la API, no para Claude Code) en lo mismo que hacía el agente investigador
de los lotes 2-6: una ficha nivel B por empresa, con vínculos citados, en un JSONL que después se empaqueta para el
panel 📥 Importar. Cada ficha pasa por el MISMO saneador y validador del importador antes de guardarse; si no valida,
se le devuelven los errores a la IA una vez para que la corrija. Se puede cortar y retomar: salta lo ya hecho.

    # 0) la lista de pendientes: empresas del lote 1 que todavía no tienen ficha nivel B (lotes 2-6)
    python scripts/research_batch.py --make-list
    # 1) prueba con 3 empresas y mira el costo real por ficha
    set ANTHROPIC_API_KEY=sk-ant-...         (PowerShell: $env:ANTHROPIC_API_KEY="sk-ant-...")
    python scripts/research_batch.py --limit 3
    # 1') o ENGROSAR las que ya están en Khipus pero casi sin vínculos (las que cotizan primero)
    python scripts/research_batch.py --make-enrich-list
    python scripts/research_batch.py --enrich --budget-usd 150 --workers 4
    # 2) el resto, con tope de gasto
    python scripts/research_batch.py --budget-usd 150 --workers 4      (modelo: Sonnet 5.5; --model claude-opus-5-5 = más fino y el doble de caro)

La clave tiene que ser de la organización que tiene los créditos (platform.claude.com → API keys). Salida:
data/import/lotes/api/fichas_api.jsonl (+ rechazadas_api.jsonl y costo_api.json).
"""
import argparse
import csv
import datetime as dt
import gzip
import json
import os
import re
import sys
import threading
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
IMPORT = os.path.join(ROOT, 'data', 'import')
OUT_DIR = os.path.join(IMPORT, 'lotes', 'api')
LIST_CSV = os.path.join(OUT_DIR, 'pendientes.csv')
OUT = os.path.join(OUT_DIR, 'fichas_api.jsonl')
BAD = os.path.join(OUT_DIR, 'rechazadas_api.jsonl')
COST = os.path.join(OUT_DIR, 'costo_api.json')
ENR_CSV = os.path.join(OUT_DIR, 'engrosar.csv')
ENR_OUT = os.path.join(OUT_DIR, 'fichas_engrosar.jsonl')
ENR_BAD = os.path.join(OUT_DIR, 'rechazadas_engrosar.jsonl')

# USD por millón de tokens (entrada, salida, escritura de caché, lectura de caché) y por búsqueda web. ESTIMADOS con
# los precios de lista; el gasto real lo dice platform.claude.com → Usage.
PRICES = {'claude-opus-5-5': (4.0, 20.0, 5.0, 0.20), 'claude-sonnet-5-5': (2.0, 10.0, 2.5, 0.20)}
WEB_SEARCH_USD = 0.01

LOTES = ['2026-10-15/bundle_lote2_completas.json.gz', '2026-10-21-r/bundle_lote5_r.json.gz',
         '2026-10-22/bundle_lote6_s.json.gz']
LOTES_JSONL = ['2026-10-21/fichas_P2_nivelB.jsonl.gz']


def norm(s):
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'[^a-z0-9]', '', s.lower())


def hint_of(name):
    """'AECC Aviation Power' → 'AECCAviationPower' (el estilo de id del catálogo)."""
    s = unicodedata.normalize('NFKD', str(name)).encode('ascii', 'ignore').decode('ascii')
    s = re.sub(r'\s*\(.*?\)', '', s)                    # «ASML Berlin (ex Berliner Glas)» → ASMLBerlin
    s = re.sub(r'\b(inc|corp|corporation|co|ltd|limited|llc|plc|sa|ag|gmbh|group|holdings?)\b\.?', '', s, flags=re.I)
    parts = re.findall(r'[A-Za-z0-9]+', s)
    return ''.join(p if p.isupper() else p[:1].upper() + p[1:] for p in parts)[:60] or 'Empresa'


def _records():
    for rel in LOTES:
        p = os.path.join(IMPORT, 'lotes', rel)
        if os.path.exists(p):
            with gzip.open(p, 'rt', encoding='utf-8') as fh:
                yield from json.load(fh).get('records') or []
    for rel in LOTES_JSONL:
        p = os.path.join(IMPORT, 'lotes', rel)
        if os.path.exists(p):
            with gzip.open(p, 'rt', encoding='utf-8') as fh:
                for line in fh:
                    if line.strip():
                        yield json.loads(line)


def known_entities():
    """{norm(nombre o id): (id, nombre)} del catálogo + todas las fichas de los lotes 2-6 (para no repetir y para que
    la IA use el id exacto de la contraparte)."""
    out = {}
    with open(os.path.join(ROOT, 'data', 'grafo_v0.json'), encoding='utf-8') as fh:
        for n in json.load(fh).get('nodes') or []:
            for k in (n.get('id'), n.get('label')):
                if k:
                    out.setdefault(norm(k), (n['id'], n.get('label') or n['id']))
    for r in _records():
        hid = r.get('khipus_id_hint')
        idn = r.get('identity') or {}
        names = [hid] + [(idn.get(k) or {}).get('value') if isinstance(idn.get(k), dict) else idn.get(k)
                         for k in ('name', 'legal_name')]
        label = next((x for x in names[1:] if isinstance(x, str)), hid)
        for k in names:
            if isinstance(k, str) and hid:
                out.setdefault(norm(k), (hid, label))
    return out


def make_list():
    known = known_entities()
    src = os.path.join(IMPORT, 'lotes', '2026-10-14', 'empresas_nuevas.csv')
    rows, seen = [], set()
    with open(src, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            keys = [norm(r.get('nombre')), norm(r.get('nombre_legal'))]
            if any(k and k in known for k in keys):
                continue
            hid = hint_of(r.get('nombre') or r.get('nombre_legal'))
            if hid in seen:
                continue
            seen.add(hid)
            rows.append({'khipus_id_hint': hid, 'nombre': r.get('nombre'), 'nombre_legal': r.get('nombre_legal'),
                         'pais_iso2': r.get('pais_iso2'), 'estado': r.get('estado'), 'ticker': r.get('ticker'),
                         'bolsa_mic': r.get('bolsa_mic'), 'simbolo_yahoo': r.get('simbolo_yahoo'),
                         'identificador': r.get('identificador'), 'sector': r.get('sector'),
                         'categoria': r.get('categoria'), 'prioridad': r.get('prioridad') or 'P3',
                         'por_que': r.get('por_que'), 'fuente_url': r.get('fuente_url')})
    order = {'P1': 0, 'P2': 1, 'P3': 2}
    rows.sort(key=lambda x: (order.get(x['prioridad'], 3), x['nombre'] or ''))
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(LIST_CSV, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f'{len(rows)} empresas pendientes → {os.path.relpath(LIST_CSV, ROOT)} (P1/P2 primero)')


def _solid(rel, flow):
    ev = rel.get('evidence') if isinstance(rel.get('evidence'), list) else []
    conf = rel.get('confidence') if rel.get('confidence') is not None else (ev[0].get('confidence') if ev else None)
    return (rel.get('rel_type') in flow and (rel.get('status') or 'active') == 'active' and (conf or 0) >= 0.5
            and bool((rel.get('counterparty') or {}).get('khipus_id')))


def make_enrich_list():
    """Empresas que YA están en Khipus pero casi sin conexiones: del catálogo, las de ≤ 2 vínculos de flujo; de los
    lotes 2-6, las de < 3 vínculos de flujo sólidos (activos, confianza ≥ 0,5, contraparte con id de Khipus). Primero
    las que cotizan (mueven carteras) y las de menos vínculos."""
    from ontology import vocabulary as V
    flow = set(V.flow_relation_types())
    g = json.load(open(os.path.join(ROOT, 'data', 'grafo_v0.json'), encoding='utf-8'))
    deg = {}
    for l in g.get('links') or []:
        if (l.get('type') or 'supply') in flow:
            for k in (l.get('source'), l.get('target')):
                deg[k] = deg.get(k, 0) + 1
    rows = {}
    for n in g.get('nodes') or []:
        d = deg.get(n['id'], 0)
        if d <= 2:
            rows[n['id']] = {'khipus_id': n['id'], 'nombre': n.get('label') or n['id'], 'pais': n.get('country') or '',
                             'cotiza': n.get('mkt') or '', 'vinculos': d, 'origen': 'catalogo'}
    for r in _records():
        hid = r.get('khipus_id_hint')
        if not hid or hid in rows:
            continue
        d = sum(1 for rel in r.get('relations') or [] if _solid(rel, flow))
        if d >= 3:
            continue
        idn = r.get('identity') or {}
        nm = idn.get('short_name') or idn.get('legal_name') or {}
        lst = [x for x in r.get('listings') or [] if isinstance(x, dict)]
        rows[hid] = {'khipus_id': hid, 'nombre': (nm.get('value') if isinstance(nm, dict) else nm) or hid,
                     'pais': ((idn.get('hq_country') or {}).get('value') if isinstance(idn.get('hq_country'), dict) else '') or '',
                     'cotiza': (lst[0].get('yahoo_symbol') or lst[0].get('ticker') or '') if lst else '',
                     'vinculos': d, 'origen': 'lote'}
    out = sorted(rows.values(), key=lambda x: (not x['cotiza'], x['vinculos'], x['nombre']))
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(ENR_CSV, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print(f"{len(out)} empresas para engrosar ({sum(1 for x in out if x['cotiza'])} cotizan; "
          f"{sum(1 for x in out if x['vinculos'] == 0)} sin ningún vínculo sólido) → {os.path.relpath(ENR_CSV, ROOT)}")


def _rules():
    """Las reglas del prompt de los lotes (docs/expansion/PROMPT_LOTE3.md), adaptadas a UNA empresa por pedido."""
    txt = open(os.path.join(ROOT, 'docs', 'expansion', 'PROMPT_LOTE3.md'), encoding='utf-8').read()
    m = re.search(r'```text\n(.*?)```', txt, re.S)
    body = m.group(1) if m else txt
    body = re.sub(r'FORMATO:.*?ESCRIBAS nada más\.\n', '', body, flags=re.S)
    return body.replace('lote3_100_empresas.csv', 'la ficha pedida').replace('empresas_existentes.csv',
                                                                                'la lista ENTIDADES KHIPUS')


def system_prompt():
    cats = json.load(open(os.path.join(ROOT, 'data', 'categories.json'), encoding='utf-8'))
    cat_lines = '\n'.join(f"{k}: {v.get('es')} ({v.get('sector')})" for k, v in sorted((cats.get('categories') or {}).items()))
    ents = sorted(set(known_entities().values()))
    ent_lines = '\n'.join(f'{i},{n}' for i, n in ents)
    schema = open(os.path.join(IMPORT, 'company.schema.json'), encoding='utf-8').read()
    plantilla = open(os.path.join(IMPORT, 'plantilla_empresa.json'), encoding='utf-8').read()
    return (
        'Eres el analista de investigación de Khipus Finance Intelligence (cadena de suministro de la IA). Investigas '
        'UNA empresa por pedido con la búsqueda web y devuelves su ficha khipus.company/1.\n\n'
        'SALIDA: al terminar, tu ÚLTIMO mensaje es SOLO el objeto JSON de la ficha (sin texto antes ni después, sin ```).\n'
        'Usa la búsqueda web y abre las páginas que cites: toda cifra, vínculo y dato lleva la URL donde lo leíste. '
        'Prefiere fuentes primarias (reportes anuales, sitio de la empresa, reguladores, bolsas) y prensa seria.\n\n'
        + _rules() +
        '\n\nCATEGORÍAS VÁLIDAS (classification.cat):\n' + cat_lines +
        '\n\nENTIDADES KHIPUS (id,nombre) — usa el id EXACTO como counterparty.khipus_id cuando la contraparte esté aquí:\n'
        + ent_lines +
        '\n\nESQUEMA company.schema.json:\n' + schema +
        '\n\nPLANTILLA plantilla_empresa.json:\n' + plantilla)


def user_prompt(row, n):
    now = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    return (f"Ficha nivel B de: {row['nombre']}" + (f" ({row['nombre_legal']})" if row.get('nombre_legal') else '') + '\n'
            + ''.join(f'- {k}: {row[k]}\n' for k in ('pais_iso2', 'estado', 'ticker', 'bolsa_mic', 'simbolo_yahoo',
                                                     'identificador', 'sector', 'categoria', 'por_que', 'fuente_url')
                      if row.get(k)) +
            f"record_id \"fb-2026-{row['khipus_id_hint'].lower()}\"; khipus_id_hint \"{row['khipus_id_hint']}\"; "
            f"research_meta: batch \"api-{now[:10]}-{n // 25 + 1}\", tier \"B\", priority \"{row.get('prioridad') or 'P3'}\", "
            f"method \"ai_assisted\", revision 1, researched_at \"{now}\", researcher \"Claude API (Khipus research_batch)\".")


def enrich_prompt(row, n):
    """La empresa YA existe en Khipus: el objetivo son los VÍNCULOS (y lo que le falte a la ficha), no repetirla."""
    now = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    kid = row['khipus_id']
    return (f"ENGROSAR una empresa que YA EXISTE en Khipus: {row['nombre']} (id Khipus \"{kid}\""
            + (f", país {row['pais']}" if row.get('pais') else '') + (f", cotiza {row['cotiza']}" if row.get('cotiza') else '')
            + f"). Hoy tiene solo {row.get('vinculos') or 0} vínculo(s) de flujo en el grafo.\n"
            "OBJETIVO: de 6 a 15 vínculos VERIFICABLES nuevos (proveedores, clientes, fábricas, nube, licencias, PPAs, "
            "dueños/filiales), priorizando contrapartes que estén en ENTIDADES KHIPUS con su khipus_id EXACTO; cada uno con "
            "evidencia (source_url + quote), dependency en los de flujo y confidence honesta. Después completa lo que más "
            "falte de la ficha (market_position, facilities, products, financials, risks, timeline). Mejor 6 vínculos "
            "ciertos que 15 dudosos.\n"
            f"Devuelve la ficha khipus.company/1 COMPLETA con khipus_id_hint \"{kid}\" (así se fusiona con la existente); "
            f"record_id \"fb-2026-enr-{kid.lower()}\"; research_meta: batch \"enr-{now[:10]}-{n // 25 + 1}\", tier \"B\", "
            f"priority \"P2\", method \"ai_assisted\", revision 1, researched_at \"{now}\", "
            "researcher \"Claude API (Khipus research_batch --enrich)\".")


class Spend:
    def __init__(self, model, path):
        self.model, self.path, self.lock = model, path, threading.Lock()
        self.d = {'usd': 0.0, 'calls': 0, 'web_searches': 0, 'fichas_ok': 0, 'rechazadas': 0}
        if os.path.exists(path):
            try:
                self.d.update(json.load(open(path, encoding='utf-8')))
            except ValueError:
                pass

    def add(self, usage):
        pin, pout, pcw, pcr = PRICES.get(self.model, PRICES['claude-opus-5-5'])
        u = usage
        stu = getattr(u, 'server_tool_use', None)
        ws = int(getattr(stu, 'web_search_requests', 0) or 0) if stu is not None else 0
        usd = ((u.input_tokens or 0) * pin + (u.output_tokens or 0) * pout +
               (getattr(u, 'cache_creation_input_tokens', 0) or 0) * pcw +
               (getattr(u, 'cache_read_input_tokens', 0) or 0) * pcr) / 1e6 + ws * WEB_SEARCH_USD
        with self.lock:
            self.d['usd'] = round(self.d['usd'] + usd, 4)
            self.d['calls'] += 1
            self.d['web_searches'] += ws
        return usd

    def bump(self, k):
        with self.lock:
            self.d[k] += 1
            json.dump(self.d, open(self.path, 'w', encoding='utf-8'), indent=1)


def _text(msg):
    return ''.join(b.text for b in msg.content if getattr(b, 'type', None) == 'text')


def _json(text):
    from core.ai import _extract_json
    try:
        obj = _extract_json(text or '')
    except ValueError:                      # sin JSON en la respuesta
        return None
    return obj if isinstance(obj, dict) else None


def research_one(client, args, system, row, n, spend):
    import anthropic
    tools = [{'type': 'web_search_20260209', 'name': 'web_search', 'max_uses': args.max_searches},
             {'type': 'web_fetch_20260209', 'name': 'web_fetch', 'max_uses': args.max_fetches}]
    messages = [{'role': 'user', 'content': enrich_prompt(row, n) if row.get('khipus_id') else user_prompt(row, n)}]
    usd = 0.0

    def call():
        nonlocal usd
        for attempt in range(4):
            try:
                # el bloque fijo (reglas + esquema + entidades, ~70k tokens) va con caché: desde la 2.ª empresa se cobra
                # a una décima parte. fallbacks "default": si un filtro de seguridad rechaza, reintenta en otro modelo.
                with client.beta.messages.stream(
                        model=args.model, max_tokens=32000, tools=tools, messages=messages,
                        system=[{'type': 'text', 'text': system, 'cache_control': {'type': 'ephemeral', 'ttl': '1h'}}],
                        betas=['server-side-fallback-2026-07-01'],
                        extra_body={'fallbacks': 'default', 'output_config': {'effort': args.effort}}) as st:
                    msg = st.get_final_message()
                usd += spend.add(msg.usage)
                return msg
            except (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.InternalServerError):
                time.sleep(15 * (attempt + 1))
        raise RuntimeError('la API no respondió tras 4 intentos')

    msg = call()
    for _ in range(5):                      # búsqueda larga: el servidor pausa y se retoma reenviando el turno
        if msg.stop_reason != 'pause_turn':
            break
        messages.append({'role': 'assistant', 'content': msg.content})
        msg = call()
    if msg.stop_reason == 'refusal':
        return None, ['la IA rechazó el pedido'], usd
    from ontology import company_import as CI
    rec, errs = _json(_text(msg)), ['no devolvió un JSON']
    for fix in range(2):
        if rec is not None:
            san, _logs, _s = CI.sanitize_batch([rec])
            _valid, invalid = CI.validate_batch(san)
            if not invalid:
                return san[0], [], usd
            errs = [f"{e.get('path')}: {e.get('msg') or e.get('type')}" for e in invalid[0]['errors']][:25]
        if fix == 1:
            break
        messages.append({'role': 'assistant', 'content': msg.content})
        messages.append({'role': 'user', 'content': 'La ficha NO valida contra el esquema. Errores:\n' + '\n'.join(errs) +
                         '\nCorrígelos (si un dato no se puede arreglar, bórralo y anota su ruta en '
                         'research_meta.not_found) y devuelve SOLO el JSON completo de la ficha.'})
        msg = call()
        rec = _json(_text(msg))
    return rec, errs, usd


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--make-list', action='store_true', help='armar la lista de pendientes y salir')
    ap.add_argument('--enrich', action='store_true',
                    help='ENGROSAR empresas que ya están en Khipus pero casi sin vínculos (engrosar.csv)')
    ap.add_argument('--make-enrich-list', action='store_true', help='armar engrosar.csv y salir')
    ap.add_argument('--list', default=None, help='CSV de empresas (por defecto pendientes.csv o engrosar.csv)')
    ap.add_argument('--limit', type=int, default=0, help='máximo de empresas en esta corrida (0 = todas)')
    ap.add_argument('--budget-usd', type=float, default=20.0, help='tope de gasto ACUMULADO (costo_api.json)')
    ap.add_argument('--workers', type=int, default=3)
    ap.add_argument('--model', default='claude-sonnet-5-5', choices=sorted(PRICES))
    ap.add_argument('--effort', default='medium', choices=('low', 'medium', 'high', 'xhigh', 'max'))
    ap.add_argument('--max-searches', type=int, default=8)
    ap.add_argument('--max-fetches', type=int, default=6)
    args = ap.parse_args(argv)
    if args.make_list:
        return make_list()
    if args.make_enrich_list:
        return make_enrich_list()
    out_path, bad_path = (ENR_OUT, ENR_BAD) if args.enrich else (OUT, BAD)
    args.list = args.list or (ENR_CSV if args.enrich else LIST_CSV)
    if not os.path.exists(args.list):
        sys.exit(f'falta {args.list}: corre primero  python scripts/research_batch.py '
                 + ('--make-enrich-list' if args.enrich else '--make-list'))
    import anthropic
    client = anthropic.Anthropic(max_retries=3, timeout=900)
    os.makedirs(OUT_DIR, exist_ok=True)
    done = set()
    key = 'khipus_id' if args.enrich else 'khipus_id_hint'
    for p in (out_path, bad_path):
        if os.path.exists(p):
            for line in open(p, encoding='utf-8'):
                try:
                    done.add(json.loads(line).get('khipus_id_hint'))       # engrosar: hint = id existente
                except ValueError:
                    pass
    rows = [r for r in csv.DictReader(open(args.list, encoding='utf-8')) if r.get(key) not in done]
    if args.limit:
        rows = rows[:args.limit]
    spend = Spend(args.model, COST)
    print(f'{len(rows)} por investigar · ya hechas {len(done)} · gastado hasta ahora ≈ {spend.d["usd"]:.2f} USD '
          f'(tope {args.budget_usd}) · modelo {args.model}, esfuerzo {args.effort}')
    system = system_prompt()
    wlock = threading.Lock()

    def job(i, row):
        if spend.d['usd'] >= args.budget_usd:
            return row, 'skip', 0.0
        rec, errs, usd = research_one(client, args, system, row, i, spend)
        with wlock:
            if rec is not None and not errs:
                with open(out_path, 'a', encoding='utf-8') as fh:
                    fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
                spend.bump('fichas_ok')
                return row, 'ok', usd
            with open(bad_path, 'a', encoding='utf-8') as fh:
                fh.write(json.dumps({'khipus_id_hint': row.get(key), 'nombre': row['nombre'],
                                     'errores': errs, 'ficha': rec}, ensure_ascii=False) + '\n')
            spend.bump('rechazadas')
            return row, 'bad', usd

    ex = ThreadPoolExecutor(max_workers=max(1, args.workers))
    futs = [ex.submit(job, i, r) for i, r in enumerate(rows)]
    try:
        for f in as_completed(futs):
            try:
                row, st, usd = f.result()
            except Exception as e:  # noqa: BLE001 — una empresa que falla no corta la tanda
                print('  ✗ error:', str(e)[:200])
                continue
            if st != 'skip':
                mark = '✓' if st == 'ok' else '✗'
                print(f"  {mark} {row['nombre']} · {usd:.3f} USD · total ≈ {spend.d['usd']:.2f} USD")
    except KeyboardInterrupt:
        # Ctrl+C: se cancela la cola; las que ya estaban en curso terminan y se guardan (≤ 1-3 min)
        print(f'\n⏹ deteniendo: se cancela la cola; terminan las {max(1, args.workers)} en curso y se guardan…')
        ex.shutdown(wait=True, cancel_futures=True)
    else:
        ex.shutdown(wait=True)
    print(f"listo: {spend.d['fichas_ok']} fichas válidas, {spend.d['rechazadas']} rechazadas, ≈ {spend.d['usd']:.2f} USD "
          f"→ {os.path.relpath(out_path, ROOT)} (mándaselo a Claude para empaquetarlo en el panel 📥)")


if __name__ == '__main__':
    main()
