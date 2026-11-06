#!/usr/bin/env python3
"""Examen de oro del chat Khipu (stdlib, sin dependencias).

Manda cada pregunta de data/eval/preguntas_oro.json al chat (POST /api/khipu/chat) y la califica:
  · herramientas: usó al menos una de cada grupo esperado
  · respondió: texto de verdad (> 120 caracteres) y no un "no puedo / no tengo datos"
  · cifras: sin "(⚠ cifra no verificada)" del guardián
  · tiempo: dentro de --max-s
Escribe docs/eval/ULTIMO.md (tabla simple) + docs/eval/ultimo.json. Es la forma de "entrenar" sin fine-tuning:
cada falla dice qué receta/herramienta arreglar; se vuelve a correr y la nota debe subir.

  python3 scripts/eval_chat.py                       # producción
  python3 scripts/eval_chat.py --url http://localhost:8080 --only fondo,precio
"""
import argparse
import concurrent.futures as cf
import json
import os
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES = os.path.join(ROOT, 'data', 'eval', 'preguntas_oro.json')
OUT_DIR = os.path.join(ROOT, 'docs', 'eval')
DEFAULT_URL = os.environ.get('KHIPU_URL', 'https://supply-chain-for-ai-production.up.railway.app')

REFUSALS = ('no tengo acceso', 'no puedo responder', 'no dispongo', 'no tengo datos', 'no tengo información',
            'no pude obtener', 'no está disponible en este momento', 'intenta de nuevo', 'reintenta')
UNVERIFIED = 'cifra no verificada'


def grade(case, out, elapsed_s, max_s=60.0):
    """Califica UNA respuesta → {ok, checks:{...}, fallas:[...]} (función pura: la prueban los tests)."""
    out = out or {}
    used = [t.get('name') for t in (out.get('tools_used') or []) if isinstance(t, dict)]
    ans = str(out.get('answer') or '')
    low = ans.lower()
    fallas = []
    faltan = [g for g in case.get('tools', []) if not set(g) & set(used)]
    if faltan:
        fallas.append('no usó ' + ' / '.join('|'.join(g) for g in faltan))
    if out.get('error'):
        fallas.append('error: ' + str(out.get('error'))[:80])
    elif len(ans) < 120:
        fallas.append('respuesta corta')
    hit = next((r for r in REFUSALS if r in low), None)
    if hit:
        fallas.append(f'se rindió ("{hit}")')
    n_unv = low.count(UNVERIFIED)
    if n_unv:
        fallas.append(f'{n_unv} cifra(s) no verificada(s)')
    if out.get('answer_source') not in (None, 'ai', 'agent'):
        fallas.append('respuesta de respaldo (' + str(out.get('answer_source')) + ')')
    if elapsed_s > max_s:
        fallas.append(f'lenta ({elapsed_s:.0f} s)')
    return {'id': case['id'], 'ok': not fallas, 'fallas': fallas, 'tools': used,
            'segundos': round(elapsed_s, 1), 'modelo': out.get('model'), 'respuesta': ans[:600]}


def ask(url, q, lang='es', timeout=120):
    body = json.dumps({'message': q, 'lang': lang}).encode('utf-8')
    req = urllib.request.Request(url.rstrip('/') + '/api/khipu/chat', data=body,
                                 headers={'Content-Type': 'application/json', 'User-Agent': 'khipu-eval/1'})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            out = json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:
            out = json.loads(e.read().decode('utf-8'))
        except Exception:  # noqa: BLE001
            out = {}
        out.setdefault('error', f'HTTP {e.code}')
    except Exception as e:  # noqa: BLE001
        out = {'error': type(e).__name__ + ': ' + str(e)[:80]}
    return out, time.monotonic() - t0


def report_md(results, url):
    ok = sum(r['ok'] for r in results)
    lines = [f'# Examen de oro del chat — {ok}/{len(results)} aprobadas', '',
             f'_{time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())} · {url}_', '',
             '| | Pregunta | Herramientas | Seg. | Qué falló |', '|---|---|---|---|---|']
    for r in results:
        lines.append(f"| {'✅' if r['ok'] else '❌'} | {r['id']} | {', '.join(r['tools']) or '—'} | {r['segundos']} | "
                     f"{'; '.join(r['fallas']) or ''} |")
    return '\n'.join(lines) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', default=DEFAULT_URL)
    ap.add_argument('--only', default='')
    ap.add_argument('--max-s', type=float, default=60.0)
    ap.add_argument('--workers', type=int, default=2)   # el chat limita 40 pedidos / 5 min
    a = ap.parse_args()
    cases = json.load(open(CASES, encoding='utf-8'))['casos']
    if a.only:
        keep = set(a.only.split(','))
        cases = [c for c in cases if c['id'] in keep]

    def run(c):
        out, s = ask(a.url, c['q'])
        r = grade(c, out, s, a.max_s)
        r['pregunta'] = c['q']
        print(('✅' if r['ok'] else '❌'), c['id'], f"{r['segundos']}s", '; '.join(r['fallas']), flush=True)
        return r

    with cf.ThreadPoolExecutor(a.workers) as ex:
        results = list(ex.map(run, cases))
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, 'ultimo.json'), 'w', encoding='utf-8') as f:
        json.dump({'url': a.url, 'resultados': results}, f, ensure_ascii=False, indent=1)
    md = report_md(results, a.url)
    with open(os.path.join(OUT_DIR, 'ULTIMO.md'), 'w', encoding='utf-8') as f:
        f.write(md)
    print('\n' + md)


if __name__ == '__main__':
    main()
