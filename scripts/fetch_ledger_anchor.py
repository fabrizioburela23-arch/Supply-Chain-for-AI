#!/usr/bin/env python3
"""scripts/fetch_ledger_anchor.py — baja el ANCLA DIARIA pública del libro de decisiones y la guarda fuera de la base
(docs/INFRA_OPERATIVA.md §2.8, paso 7, decisión D7). La corre el GitHub Action smoke-mcp.yml.

GET <KHIPU_URL>/api/ledger/anchor → {day, head_seal, head_hash} (nada más: ningún contenido del libro).
Escribe `--out` (JSON con la hora de descarga y la URL), añade una tabla al resumen del trabajo (`--summary`) y
deja `day=` en $GITHUB_OUTPUT para nombrar el artefacto. Solo biblioteca estándar; sin secretos.

Salida 0 si se guardó o si el servidor no tiene ancla todavía / no responde (aviso ::warning::, el humo no se
pone rojo por eso); salida 1 si la respuesta tiene una forma inválida (eso sí merece mirarse).
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

DEFAULT_URL = 'https://supply-chain-for-ai-production.up.railway.app'
_HEX64 = re.compile(r'^[0-9a-f]{64}$')
_DAY = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def fetch(url, retries=4, wait_s=20, timeout=20):
    last = None
    for i in range(max(1, retries)):
        try:
            req = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'khipus-anchor/1'})
            with urllib.request.urlopen(req, timeout=timeout) as r:      # noqa: S310 — URL fija https
                return r.status, json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            last = (e.code, None)
            if e.code < 500 and e.code != 429:
                return last
        except Exception as e:  # noqa: BLE001
            last = (None, {'error': type(e).__name__})
        if i + 1 < retries:
            time.sleep(wait_s)
    return last


def validate(d):
    """Lista de problemas de forma (vacía = válida)."""
    probs = []
    if not isinstance(d, dict):
        return ['la respuesta no es un objeto JSON']
    if not _DAY.match(str(d.get('day') or '')):
        probs.append('day inválido')
    if not isinstance(d.get('head_seal'), int) or d['head_seal'] < 0:
        probs.append('head_seal inválido')
    if not _HEX64.match(str(d.get('head_hash') or '')):
        probs.append('head_hash inválido (64 hex)')
    extra = set(d) - {'available', 'day', 'head_seal', 'head_hash'}
    if extra:
        probs.append(f'campos inesperados en una respuesta pública: {sorted(extra)}')
    return probs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--url', default=os.getenv('KHIPU_URL') or DEFAULT_URL)
    ap.add_argument('--out', default='ledger-anchor.json')
    ap.add_argument('--summary', default=os.getenv('GITHUB_STEP_SUMMARY') or '')
    ap.add_argument('--retries', type=int, default=4)
    args = ap.parse_args(argv)
    url = args.url.rstrip('/') + '/api/ledger/anchor'
    status, data = fetch(url, retries=args.retries)
    if status != 200 or not isinstance(data, dict) or data.get('pending') or data.get('day') is None:
        print(f'::warning::Ancla no disponible todavía ({status}): {url}')
        return 0
    probs = validate(data)
    if probs:
        print('::error::Ancla con forma inválida: ' + '; '.join(probs))
        return 1
    rec = {'schema': 'ledger-anchor/1', 'day': data['day'], 'head_seal': data['head_seal'],
           'head_hash': data['head_hash'], 'source': url,
           'fetched_at': datetime.now(timezone.utc).isoformat(timespec='seconds')}
    with open(args.out, 'w', encoding='utf-8') as fh:
        json.dump(rec, fh, ensure_ascii=False, indent=2, sort_keys=True)
    print(json.dumps(rec, ensure_ascii=False))
    gh_out = os.getenv('GITHUB_OUTPUT')
    if gh_out:
        with open(gh_out, 'a', encoding='utf-8') as fh:
            fh.write(f"day={rec['day']}\n")
    if args.summary:
        with open(args.summary, 'a', encoding='utf-8') as fh:
            fh.write('### Ancla diaria del libro de decisiones / Daily ledger anchor\n\n'
                     '| día / day | sello / seal | hash |\n|---|---|---|\n'
                     f"| {rec['day']} | {rec['head_seal']} | `{rec['head_hash']}` |\n\n"
                     f"Descargada / fetched {rec['fetched_at']} de / from {url}\n")
    return 0


if __name__ == '__main__':
    sys.exit(main())
