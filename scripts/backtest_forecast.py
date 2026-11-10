"""Backtest: simulación propia de Khipus (core/price_sim) vs TimesFM 2.5 vs ingenuo (precio de hoy).
Para cada acción y cada fecha de corte (cada 5 días hábiles del último ~2 años) cada modelo solo ve el pasado y
pronostica el cierre a 21 días hábiles (1 mes). Se compara con lo que pasó de verdad.

Métricas (más bajo = mejor, salvo cobertura):
  · error de la mediana (|mediana/real − 1|, en %)
  · pérdida de cuantiles (pinball) promedio en q25/q50/q75, en % del precio — la nota principal
  · cobertura de la banda 50 % (q25–q75: lo ideal es 50 %) y de la banda 80 % (q10–q90: lo ideal es 80 %)
uso (venv aparte con torch CPU + timesfm[torch]; NUNCA en el servidor web):
  python scripts/backtest_forecast.py datos/NVDA.json …   (cada json = /api/prices/eod/<T>?range=5y)
"""
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import price_sim  # noqa: E402

H = 21
STEP = 5
N_ORIGINS = 100          # ~2 años de cortes
CTX = 1024


def load(path):
    d = json.load(open(path))
    pts = d.get('points') or d.get('series') or []
    out = []
    for p in pts:
        if isinstance(p, (list, tuple)) and len(p) >= 2 and p[1]:
            out.append((str(p[0])[:10], float(p[1])))
        elif isinstance(p, dict) and p.get('close'):
            out.append((p['date'][:10], float(p['close'])))
    out.sort()
    return d.get('symbol') or os.path.basename(path).split('.')[0], out


def ours(sym, hist):
    r = price_sim.simulate(sym, dict(hist), earnings=([], None, None), n_paths=6000, fan_days=H)
    f = r['fan'][-1]
    p5, p25, p50, p75, p95 = f['p5'], f['p25'], f['p50'], f['p75'], f['p95']
    q10 = p5 + (p25 - p5) * 0.25          # interpolación lineal en el cuantil (aprox.)
    q90 = p95 - (p95 - p75) * 0.25
    return {'q10': q10, 'q25': p25, 'q50': p50, 'q75': p75, 'q90': q90}


def pinball(y, q, tau):
    return max(tau * (y - q), (tau - 1) * (y - q))


def score(rows):
    if not rows:
        return {}
    a = np.array([[r['err'], r['pin'], r['in50'], r['in80']] for r in rows], float)
    return {'n': len(rows), 'error_mediana_pct': round(a[:, 0].mean() * 100, 2),
            'pinball_pct': round(a[:, 1].mean() * 100, 3),
            'cobertura_50': round(a[:, 2].mean() * 100, 1), 'cobertura_80': round(a[:, 3].mean() * 100, 1)}


def evaluate(q, y):
    pin = np.mean([pinball(y, q['q25'], .25), pinball(y, q['q50'], .5), pinball(y, q['q75'], .75)]) / y
    return {'err': abs(q['q50'] / y - 1), 'pin': pin, 'in50': q['q25'] <= y <= q['q75'],
            'in80': q['q10'] <= y <= q['q90']}


def main(paths):
    import timesfm
    t0 = time.time()
    model = timesfm.TimesFM_2p5_200M_torch.from_pretrained('google/timesfm-2.5-200m-pytorch')
    model.compile(timesfm.ForecastConfig(max_context=CTX, max_horizon=64, normalize_inputs=True,
                                         use_continuous_quantile_head=True, force_flip_invariance=True,
                                         infer_is_positive=True, fix_quantile_crossing=True))
    print(f'TimesFM cargado en {time.time() - t0:.0f} s', flush=True)
    allres = {'khipus': [], 'timesfm': [], 'ingenuo': []}
    per = {}
    for p in paths:
        sym, data = load(p)
        n = len(data)
        origins = [n - H - 1 - k * STEP for k in range(N_ORIGINS)]
        origins = [o for o in origins if o >= 300]
        res = {'khipus': [], 'timesfm': [], 'ingenuo': []}
        ctxs, truths, lasts = [], [], []
        for o in origins:
            hist = data[:o + 1]
            y = data[o + H][1]
            last = hist[-1][1]
            res['khipus'].append(evaluate(ours(sym, hist), y))
            res['ingenuo'].append(evaluate({'q10': last, 'q25': last, 'q50': last, 'q75': last, 'q90': last}, y))
            ctxs.append(np.array([c for _, c in hist[-CTX:]], dtype=np.float32))
            truths.append(y)
            lasts.append(last)
        _pt, qf = model.forecast(horizon=H, inputs=ctxs)      # qf: (n, H, 10) = media, q10..q90
        for i, y in enumerate(truths):
            dq = qf[i, H - 1]
            q10, q20, q30, q50, q70, q80, q90 = (float(dq[k]) for k in (1, 2, 3, 5, 7, 8, 9))
            q = {'q10': q10, 'q25': (q20 + q30) / 2, 'q50': q50, 'q75': (q70 + q80) / 2, 'q90': q90}
            res['timesfm'].append(evaluate(q, y))
        per[sym] = {k: score(v) for k, v in res.items()}
        for k in allres:
            allres[k] += res[k]
        print(sym, json.dumps(per[sym], ensure_ascii=False), flush=True)
    total = {k: score(v) for k, v in allres.items()}
    print('TOTAL', json.dumps(total, ensure_ascii=False))
    json.dump({'por_accion': per, 'total': total, 'horizonte_dias': H, 'cortes_cada': STEP},
              open('resultado_backtest.json', 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main(sys.argv[1:])
