"""core/scenario_pnl.py — ESCENARIO → DINERO (BRECHAS L2-13 / PROP-16; batch I3, 2026-10-13).

El kernel dice "si TSMC cae, a Nvidia le llega un 61 % del golpe" (fracción del suministro). Esto lo traduce a dólares
de UNA cartera con un κ CALIBRADO sobre episodios reales:

    r_i ≈ a_e − κ · impacto_i          (r_i = caída relativa al mercado del episodio e; a_e = ruido del episodio)
    ΔP&L = − κ · Σ_i V_i · impacto_i  ±  z · √((se_κ · Σ V_i·impacto_i)² + σ_res² · Σ_{i golpeadas} V_i²)

  · κ, su error, σ_res, n, R² y los episodios viven en el artefacto de gobernanza `kernel.calibration@<semver>` (los
    escribe scripts/calibrate_kernel.py con la huella de sus entradas). NUNCA se ajusta a pedido: aquí solo se LEE.
  · Si el ajuste es débil (pocos puntos, κ no positivo, t o R² bajos), si no hay calibración o si el motor vigente no es
    el que se calibró, la respuesta lo DICE y no da cifra (`status` ≠ 'ok'). Honestidad antes que precisión.
  · Traducir es aritmética de microsegundos sobre impactos que ya calculó el kernel único (vistas rápidas).

Sin red, sin base, sin IA. Funciones puras salvo `calibration()` (lee el release vigente).
"""
import math

ARTIFACT = 'kernel.calibration'
MEASURE = 'relative_drawdown'


# ════════════════════════════════════════════════════════════════════════════
# lectura del artefacto vigente
# ════════════════════════════════════════════════════════════════════════════
def calibration():
    """(params, (ref, hash)) del kernel.calibration vigente, o (None, None) si este código/release no lo trae."""
    try:
        from core import governance
        return governance.section(ARTIFACT), governance.policy_ref(ARTIFACT)
    except Exception:  # noqa: BLE001 — artefacto ausente: no hay traducción a dinero (se dice)
        return None, None


def _kernel_semver():
    try:
        from core import governance
        return governance.artifact_semver('kernel.params')
    except Exception:  # noqa: BLE001
        return None


# ════════════════════════════════════════════════════════════════════════════
# medición de un episodio (la usa el script de calibración)
# ════════════════════════════════════════════════════════════════════════════
def close_on_or_before(closes, day):
    """(fecha, cierre) del último cierre en o antes de `day` ('YYYY-MM-DD'), o (None, None)."""
    best = None
    for d in closes:
        if d <= day and (best is None or d > best):
            best = d
    return (best, float(closes[best])) if best is not None else (None, None)


def relative_drawdown(closes_i, closes_m, t0, t1):
    """Peor caída de la empresa RELATIVA al mercado entre t0 (exclusivo, base = último cierre ≤ t0) y t1 (inclusive):
    min_d (P_i(d)/P_i(b)) / (P_m(d)/P_m(b)) − 1, acotada a ≤ 0. None si falta la base o no hay cierres comunes."""
    b_i, p_i0 = close_on_or_before(closes_i, t0)
    b_m, p_m0 = close_on_or_before(closes_m, t0)
    if b_i is None or b_m is None or p_i0 <= 0 or p_m0 <= 0:
        return None
    worst = None
    for d in sorted(closes_i):
        if not (t0 < d <= t1) or d not in closes_m:
            continue
        pi, pm = float(closes_i[d]), float(closes_m[d])
        if pi <= 0 or pm <= 0:
            continue
        rel = (pi / p_i0) / (pm / p_m0) - 1.0
        worst = rel if worst is None else min(worst, rel)
    if worst is None:
        return None
    return min(0.0, worst)


# ════════════════════════════════════════════════════════════════════════════
# ajuste (puro; determinista)
# ════════════════════════════════════════════════════════════════════════════
DEFAULT_RULES = {'min_points': 20, 'min_points_per_episode': 4, 'min_episodes': 2, 'min_t': 2.0,
                 'min_partial_r2': 0.10, 'band_z': 1.645}


def _ols(X, y):
    import numpy as np
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    return beta, resid


def fit(points, rules=None):
    """points [{episode, id, impact (0..1), y (≤0)}] → ajuste con efecto fijo por episodio:
    y = a_e − κ·impacto. Devuelve {status: ok|weak|insufficient, kappa, kappa_se, t, r2, partial_r2, resid_sd, n,
    n_episodes, impact_max, intercepts, per_episode, reasons}. Las razones explican por qué NO hay cifra."""
    import numpy as np
    r = dict(DEFAULT_RULES, **(rules or {}))
    by_ep = {}
    for p in points:
        if p.get('y') is None or p.get('impact') is None:
            continue
        by_ep.setdefault(p['episode'], []).append(p)
    eps = sorted(e for e, pts in by_ep.items() if len(pts) >= int(r['min_points_per_episode']))
    pts = [p for e in eps for p in by_ep[e]]
    n = len(pts)
    out = {'status': 'insufficient', 'n': n, 'n_episodes': len(eps), 'episodes_used': eps, 'kappa': None,
           'kappa_se': None, 't': None, 'r2': None, 'partial_r2': None, 'resid_sd': None, 'impact_max': None,
           'intercepts': {}, 'per_episode': {}, 'reasons': []}
    if len(eps) < int(r['min_episodes']):
        out['reasons'].append(f"episodes_with_data {len(eps)} < {int(r['min_episodes'])}")
    if n < int(r['min_points']):
        out['reasons'].append(f"points {n} < {int(r['min_points'])}")
    if not eps or n <= len(eps) + 1:
        return out
    imp = np.array([float(p['impact']) for p in pts])
    y = np.array([float(p['y']) for p in pts])
    D = np.array([[1.0 if p['episode'] == e else 0.0 for e in eps] for p in pts])
    X = np.column_stack([D, imp])
    beta, resid = _ols(X, y)
    _b0, resid0 = _ols(D, y)
    dof = n - X.shape[1]
    rss, rss0 = float(resid @ resid), float(resid0 @ resid0)
    tss = float(((y - y.mean()) ** 2).sum())
    if dof <= 0 or float(np.var(imp)) == 0.0:
        out['reasons'].append('no impact variation')
        return out
    s2 = rss / dof
    try:
        cov = s2 * np.linalg.inv(X.T @ X)
        se = math.sqrt(max(0.0, float(cov[-1, -1])))
    except np.linalg.LinAlgError:
        out['reasons'].append('singular design')
        return out
    kappa = -float(beta[-1])
    out.update(kappa=round(kappa, 6), kappa_se=round(se, 6), t=round(kappa / se, 4) if se > 0 else None,
               r2=round(1.0 - rss / tss, 6) if tss > 0 else None,
               partial_r2=round(1.0 - rss / rss0, 6) if rss0 > 0 else None,
               resid_sd=round(math.sqrt(s2), 6), impact_max=round(float(imp.max()), 6),
               intercepts={e: round(float(beta[i]), 6) for i, e in enumerate(eps)})
    for e in eps:
        ei = np.array([p['impact'] for p in by_ep[e]], dtype=float)
        ey = np.array([p['y'] for p in by_ep[e]], dtype=float)
        if len(ei) >= 3 and float(np.var(ei)) > 0:
            b, _res = _ols(np.column_stack([np.ones(len(ei)), ei]), ey)
            out['per_episode'][e] = {'n': len(ei), 'kappa': round(-float(b[1]), 6)}
        else:
            out['per_episode'][e] = {'n': len(ei), 'kappa': None}
    if kappa <= 0:
        out['reasons'].append('kappa <= 0 (more impact did not mean a bigger fall)')
    if out['t'] is None or out['t'] < float(r['min_t']):
        out['reasons'].append(f"t {out['t']} < {r['min_t']}")
    if out['partial_r2'] is None or out['partial_r2'] < float(r['min_partial_r2']):
        out['reasons'].append(f"partial_r2 {out['partial_r2']} < {r['min_partial_r2']}")
    out['status'] = 'ok' if not out['reasons'] else 'weak'
    return out


MAX_STEP_RATIO = 3.0     # un salto de ×3 entre dos cierres seguidos de la ventana = serie corrupta (no un precio real)


def series_problem(entry, t0, t1):
    """Por qué una serie NO sirve para medir el episodio (o None): sin datos, sin ajustar (splits/dividendos), precio
    congelado (OTC sin operaciones) o saltos imposibles. Se descarta y se cuenta; nunca se corrige a mano."""
    closes = (entry or {}).get('closes') or {}
    base = close_on_or_before(closes, t0)[0]
    if base is None or not any(t0 < d <= t1 for d in closes):
        return 'no_data'
    if (entry or {}).get('adjusted') is False:
        return 'unadjusted'
    seg = [float(closes[d]) for d in sorted(closes) if base <= d <= t1]
    if len(set(seg)) < 2:
        return 'frozen'
    if any(b <= 0 or a <= 0 or max(a / b, b / a) > MAX_STEP_RATIO for a, b in zip(seg, seg[1:])):
        return 'corrupt'
    return None


def points_from_inputs(inputs):
    """El archivo de entradas (scripts/calibrate_kernel.py) → puntos {episode, id, symbol, impact, y, excluded}. Puro.
    `y` = None y `excluded` = la razón cuando la serie no sirve (series_problem)."""
    bench = (inputs.get('benchmark') or {}).get('symbol')
    prices = inputs.get('prices') or {}
    bm = prices.get(bench) or {}
    out = []
    for ep in inputs.get('episodes') or []:
        bprob = series_problem(bm, ep['t0'], ep['t1'])
        for s in ep.get('sample') or []:
            ent = prices.get(s.get('symbol')) or {}
            prob = bprob and f'benchmark_{bprob}' or series_problem(ent, ep['t0'], ep['t1'])
            y = None if prob else relative_drawdown(ent['closes'], bm['closes'], ep['t0'], ep['t1'])
            out.append({'episode': ep['id'], 'id': s['id'], 'symbol': s.get('symbol'),
                        'impact': round(float(s['impact_pct']) / 100.0, 6),
                        'y': None if y is None else round(y, 6), 'excluded': prob})
    return out


# ════════════════════════════════════════════════════════════════════════════
# traducción a dinero (a pedido: solo aritmética sobre el κ guardado)
# ════════════════════════════════════════════════════════════════════════════
_MSG = {
    'uncalibrated': ('Sin calibrar todavía: no damos una cifra en dinero.', 'Not calibrated yet: we give no money figure.'),
    'weak': ('La calibración con episodios reales es débil: no damos una cifra en dinero.',
             'The calibration on real episodes is weak: we give no money figure.'),
    'kernel_mismatch': ('La calibración se hizo con otra versión del motor: no damos una cifra en dinero.',
                        'The calibration was made with another engine version: we give no money figure.'),
    'no_positions': ('Sin posiciones guardadas.', 'No saved positions.'),
    'ok': ('Estimación con episodios reales; no es un pronóstico.', 'Estimate from real episodes; not a forecast.'),
}


def _status(st, **kw):
    es, en = _MSG[st]
    return dict({'status': st, 'pnl_usd': None, 'band_usd': None, 'note_es': es, 'note_en': en}, **kw)


def cal_summary(cal, ref=None):
    fit_ = (cal or {}).get('fit') or {}
    return {'artifact': ref[0] if ref else None, 'hash': ref[1] if ref else None,
            'status': fit_.get('status'), 'kappa': fit_.get('kappa'), 'kappa_se': fit_.get('kappa_se'),
            'n': fit_.get('n'), 'n_episodes': fit_.get('n_episodes'), 'r2': fit_.get('r2'),
            'partial_r2': fit_.get('partial_r2'), 'reasons': list(fit_.get('reasons') or []),
            'episodes': [{'id': e.get('id'), 'label_es': e.get('label_es'), 'label_en': e.get('label_en'),
                          'proposed': bool(e.get('proposed', True))} for e in (cal or {}).get('episodes') or []],
            'kernel_params': (cal or {}).get('kernel_params_semver'), 'proposed': (cal or {}).get('status') == 'proposed'}


def translate(impacts, positions, cal=None, ref=None, kernel_semver=None):
    """impacts {id: pct 0..100} (del kernel) + positions [{id, usd, symbol?}] → P&L estimado con banda o un estado
    honesto sin cifra. `cal`/`ref` por defecto: el kernel.calibration vigente. Nunca lanza por datos raros."""
    if cal is None and ref is None:
        cal, ref = calibration()
    summ = cal_summary(cal, ref)
    if not cal or not (cal.get('fit') or {}).get('status'):
        return _status('uncalibrated', calibration=summ)
    fit_ = cal['fit']
    if fit_.get('status') != 'ok' or fit_.get('kappa') is None:
        return _status('weak', calibration=summ)
    ks = kernel_semver if kernel_semver is not None else _kernel_semver()
    want = cal.get('kernel_params_semver')
    if want and ks and ks != want:
        return _status('kernel_mismatch', calibration=summ, kernel_active=ks)
    rows, total, expo, sq, unmapped = [], 0.0, 0.0, 0.0, []
    for p in positions or []:
        try:
            usd = float(p.get('usd') or 0.0)
        except (TypeError, ValueError):
            usd = 0.0
        if not (usd > 0 and math.isfinite(usd)):
            continue
        oid = p.get('id')
        total += usd
        if not oid:
            unmapped.append(p.get('symbol') or '?')
            continue
        hit = float((impacts or {}).get(oid, 0.0) or 0.0) / 100.0
        expo += usd * hit
        if hit > 0:
            sq += usd * usd
        rows.append({'id': oid, 'symbol': p.get('symbol'), 'usd': round(usd, 2), 'impact_pct': round(hit * 100, 2),
                     'pnl_usd': round(-float(fit_['kappa']) * usd * hit, 2)})
    if total <= 0:
        return _status('no_positions', calibration=summ)
    k, se, sd = float(fit_['kappa']), float(fit_.get('kappa_se') or 0.0), float(fit_.get('resid_sd') or 0.0)
    z = float((cal.get('rules') or {}).get('band_z', DEFAULT_RULES['band_z']))
    pnl = -k * expo
    band = z * math.sqrt((se * expo) ** 2 + (sd ** 2) * sq) if expo > 0 else 0.0
    hit_max = max((r['impact_pct'] for r in rows), default=0.0) / 100.0
    out = _status('ok', calibration=summ)
    out.update(pnl_usd=round(pnl, 2), band_usd=round(band, 2), lo_usd=round(pnl - band, 2), hi_usd=round(pnl + band, 2),
               total_usd=round(total, 2), pnl_pct=round(100.0 * pnl / total, 2),
               exposure_usd=round(expo, 2), hit_positions=sum(1 for r in rows if r['impact_pct'] > 0),
               positions=sorted(rows, key=lambda r: (r['pnl_usd'], r['id']))[:60], unmapped=unmapped[:60],
               extrapolated=bool(fit_.get('impact_max') is not None and hit_max > float(fit_['impact_max']) + 1e-9),
               method='pnl = -kappa * sum(usd * impact); band = z * sqrt((se*E)^2 + resid_sd^2 * sum(usd^2 hit))')
    return out
