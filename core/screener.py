"""core/screener.py — Screener de crecimiento explosivo: /api/screener/*.

LA tesis de la app (Fabrizio): "spotear empresas con potencial de crecimiento
exponencial" — en TODAS las bolsas, no solo EE.UU. Este módulo la convierte en
un ranking diario computable:

- Universo: los ~410 tickers cotizables del grafo (data/grafo_v0.json — incluye
  la ola china: 688825.SS, 1347.HK…). Multi-bolsa vía Yahoo.
- MOMENTUM real multi-semana por símbolo (5/20/60 días + media móvil), calculado
  de la serie de 3 meses. Los retornos son ratios → invariantes a la moneda
  (no necesitan conversión FX).
- Señal ESTRUCTURAL del grafo: bonus si la empresa está entre las más centrales
  (PageRank del motor de matrices) — de quién se está volviendo dependiente el
  sistema. Esta señal no la tiene ningún screener de precios.
- Calentador en HILO de fondo (patrón geosit): 1 símbolo/seg → universo entero
  en ~7 min tras el arranque, refresco cada 6 h. El endpoint responde al
  instante con lo caliente y declara la cobertura (nada de fingir que se vio
  todo cuando no).

HONESTIDAD: es un ranking de SEÑALES (precio + estructura), no una predicción
ni asesoría. El método viaja en la respuesta.
"""
import json
import logging
import os
import threading
import time

import requests as _requests

log = logging.getLogger('screener')

_YH = {'User-Agent': 'Mozilla/5.0 (compatible; Khipu/1.0)'}
_MOM_TTL = 6 * 3600
_MOM_CACHE = {}                 # symbol → {'ts', 'r5','r20','r60','above_ma20','closes_n'}
_WARM_EVERY = 1.0               # Yahoo tolera 1 req/s sin drama
_WARMER = {'started': False}
_UNIVERSE = {'ts': 0.0, 'items': None}


def _load_universe():
    """[{id,label,mkt,cat,sector}] desde el snapshot canónico (con dedupe por
    símbolo — varias entidades comparten ticker, p.ej. BABA)."""
    if _UNIVERSE['items'] is not None and time.time() - _UNIVERSE['ts'] < 3600:
        return _UNIVERSE['items']
    items, seen = [], set()
    try:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(base, 'data', 'grafo_v0.json'), encoding='utf-8') as f:
            d = json.load(f)
        for n in d.get('nodes', []):
            mkt = (n.get('mkt') or '').strip()
            if not mkt or mkt in seen:
                continue
            seen.add(mkt)
            items.append({'id': n['id'], 'label': n.get('label') or n['id'],
                          'mkt': mkt, 'cat': n.get('cat', ''), 'sector': n.get('sector', '')})
    except Exception as e:  # noqa: BLE001
        log.warning('screener: universo no cargado: %s', e)
    _UNIVERSE.update(ts=time.time(), items=items)
    return items


def _momentum(symbol):
    """Serie 3 meses → retornos 5/20/60d (%) y si está sobre su MA20.
    En moneda LOCAL (los ratios no necesitan FX). None si no hay datos."""
    try:
        r = _requests.get(
            f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}',
            params={'interval': '1d', 'range': '3mo'}, headers=_YH, timeout=8)
        res = ((r.json().get('chart') or {}).get('result') or [None])[0]
        if not res:
            return None
        closes = [c for c in (res.get('indicators', {}).get('quote', [{}])[0]
                              .get('close') or []) if c is not None]
        if len(closes) < 21:
            return None
        last = closes[-1]

        def ret(days):
            if len(closes) <= days:
                return None
            prev = closes[-1 - days]
            return round((last - prev) / prev * 100, 2) if prev else None

        ma20 = sum(closes[-20:]) / 20.0
        return {'r5': ret(5), 'r20': ret(20), 'r60': ret(60),
                'above_ma20': bool(last > ma20), 'closes_n': len(closes)}
    except Exception:  # noqa: BLE001
        return None


def _next_stale():
    now = time.time()
    for it in _load_universe():
        e = _MOM_CACHE.get(it['mkt'])
        if e is None or now - e['ts'] > _MOM_TTL:
            return it['mkt']
    return None


def _warmer_loop():
    while True:
        try:
            sym = _next_stale()
            if sym is None:
                time.sleep(60)
                continue
            m = _momentum(sym)
            now = time.time()
            if m is not None:
                _MOM_CACHE[sym] = {'ts': now, **m}
            else:
                # sin datos: reintenta en ~1 h, no bloquea el ciclo
                _MOM_CACHE[sym] = {'ts': now - _MOM_TTL + 3600, 'r5': None,
                                   'r20': None, 'r60': None, 'above_ma20': None,
                                   'closes_n': 0}
            time.sleep(_WARM_EVERY)
        except Exception:  # noqa: BLE001
            time.sleep(10)


def ensure_warmer():
    if _WARMER['started']:
        return
    _WARMER['started'] = True
    try:
        threading.Thread(target=_warmer_loop, name='screener-warmer', daemon=True).start()
    except Exception:  # noqa: BLE001
        _WARMER['started'] = False


def _pagerank_ranks():
    """{node_id: pagerank_rank} desde la caché del endpoint /api/matrix/metrics
    si está caliente (no dispara el cómputo pesado — señal opcional)."""
    try:
        from matrix.api import _TTL_CACHE
        best = None
        for k, (ts, payload) in list(_TTL_CACHE.items()):
            if isinstance(k, str) and k.startswith('metrics:'):
                if best is None or ts > best[0]:
                    best = (ts, payload)
        if best and isinstance(best[1], dict):
            return {oid: m.get('pagerank_rank') for oid, m in
                    (best[1].get('metrics') or {}).items() if m.get('pagerank_rank')}
    except Exception:  # noqa: BLE001
        pass
    return {}


def screen_growth(top=30):
    """Ranking de señales de crecimiento explosivo. Score:
    0.5·r20 + 0.2·r60 + 0.3·r5 (aceleración reciente pesa) + bonus estructural
    (+6 si PageRank top-25, +3 si top-60) + bonus +2 si sobre su MA20."""
    ensure_warmer()
    pr = _pagerank_ranks()
    rows, warm = [], 0
    for it in _load_universe():
        e = _MOM_CACHE.get(it['mkt'])
        if not e or e.get('r20') is None:
            continue
        warm += 1
        r5 = e.get('r5') or 0.0
        r20 = e['r20']
        r60 = e.get('r60')
        score = 0.5 * r20 + 0.2 * (r60 if r60 is not None else r20) + 0.3 * r5
        prk = pr.get(it['id'])
        if prk:
            score += 6 if prk <= 25 else (3 if prk <= 60 else 0)
        if e.get('above_ma20'):
            score += 2
        rows.append({**it, 'score': round(score, 2), 'r5': r5, 'r20': r20,
                     'r60': r60, 'above_ma20': e.get('above_ma20'),
                     'pagerank_rank': prk})
    rows.sort(key=lambda x: -x['score'])
    total = len(_load_universe())
    return {
        'ranked': rows[:max(5, min(int(top), 100))],
        'coverage': {'warm': warm, 'total': total,
                     'complete': warm >= total * 0.9},
        'method_es': 'Señales, no predicción: momentum 5/20/60 días (multi-bolsa, '
                     'invariante a la moneda) + centralidad PageRank del grafo '
                     '(de quién depende el sistema) + tendencia sobre MA20. '
                     'Análisis, no asesoría financiera.',
    }
