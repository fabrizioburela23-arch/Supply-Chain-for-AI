"""core/sim_report.py — INFORME de la simulación de escenarios (2026-10-21, «que parezca un producto»).

La simulación (core/sim_agents.run) devuelve narrativa + impactos por empresa. Esto le suma, SIN IA y sin inventar:
  · por empresa: ticker, sector, país, capitalización y precio EN VIVO (core/live_caps, con su hora) y el «valor en
    juego» = capitalización × % estimado (estimación del escenario, no precio);
  · cifras clave: cuántas golpeadas / ganadoras, sectores, países, capitalización expuesta, el golpe más fuerte;
  · por sector y por país (cuántas, % medio, valor en juego);
  · TU CARTERA: tus posiciones que el escenario toca, con su monto y lo que implicaría el % estimado (aritmética
    simple y rotulada; las que no toca, contadas);
  · titular de una línea y METODOLOGÍA (quién puso los %, modelo de IA, versión del motor, hora de los precios).
Puro salvo `get_caps` y el grafo vigente (lecturas en memoria). Nunca lanza: lo que falta se dice.
"""
import math
from datetime import datetime, timezone


def _f(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def _es(lang):
    return not str(lang or 'es').lower().startswith('en')


def _caps():
    try:
        from core.live_caps import get_caps
        st = get_caps(start=False)
        return st.get('caps') or {}, st.get('as_of')
    except Exception:  # noqa: BLE001
        return {}, None


def _snap():
    try:
        from core import semantic
        return semantic._load_snapshot()
    except Exception:  # noqa: BLE001
        return {'by_id': {}}


def _sector_label(sec, lang):
    try:
        from core.portfolio_ai import sector_label
        return sector_label(sec, lang)
    except Exception:  # noqa: BLE001
        return sec or '—'


def _country_label(c, lang):
    try:
        from core import countries
        iso = countries.iso2_of(c)
        return countries.label(iso, 'es' if _es(lang) else 'en') if iso else (c or '—')
    except Exception:  # noqa: BLE001
        return c or '—'


def _kernel_semver():
    try:
        from core import governance
        return governance.artifact_semver('kernel.params')
    except Exception:  # noqa: BLE001
        return None


def clean_positions(raw):
    """[{id, symbol?, usd}] del navegador → lista validada (máx 60, usd > 0)."""
    out = []
    for p in (raw or [])[:60]:
        if not isinstance(p, dict):
            continue
        usd = _f(p.get('usd'))
        pid = str(p.get('id') or '').strip()[:80]
        if pid and usd and 0 < usd <= 1e12:
            out.append({'id': pid, 'symbol': str(p.get('symbol') or '')[:15], 'usd': round(usd, 2)})
    return out


def build(sim, lang='es', positions=None, caps=None, caps_as_of=None, snap=None, now=None):
    """sim = salida de sim_agents.run → {'rows', 'kpis', 'by_sector', 'by_country', 'portfolio', 'headline',
    'method'}. `caps`/`snap` inyectables (pruebas)."""
    es = _es(lang)
    if caps is None:
        caps, caps_as_of = _caps()
    snap = snap if snap is not None else _snap()
    by_id = snap.get('by_id') or {}
    rows = []
    for i in sim.get('impacts') or []:
        if not isinstance(i, dict) or not i.get('id'):
            continue
        n = by_id.get(i['id']) or {}
        c = caps.get(i['id']) or {}
        pct = _f(i.get('pct')) or 0.0
        mcap = _f(c.get('mcap_b'))
        rows.append({
            'id': i['id'], 'label': i.get('label') or n.get('label') or i['id'], 'pct': round(pct, 2),
            'channel': i.get('channel'), 'path': i.get('path') or '', 'rationale': i.get('rationale') or '',
            'ticker': n.get('mkt') or c.get('symbol'), 'sector': n.get('sector'),
            'sector_label': _sector_label(n.get('sector'), lang) if n.get('sector') else None,
            'country': n.get('country'), 'country_label': _country_label(n.get('country'), lang) if n.get('country') else None,
            'mcap_b': round(mcap, 2) if mcap else None,
            'price_usd': _f(c.get('price_usd')), 'change_pct': _f(c.get('change_pct')),
            'value_at_stake_b': round(mcap * pct / 100, 3) if mcap else None,
        })
    hit = [r for r in rows if r['pct'] < 0]
    win = [r for r in rows if r['pct'] > 0]
    sec_set = {r['sector'] for r in rows if r['sector']}
    ctry_set = {r['country'] for r in rows if r['country']}
    worst = min(hit, key=lambda r: r['pct']) if hit else None
    best = max(win, key=lambda r: r['pct']) if win else None
    loss_b = sum(r['value_at_stake_b'] for r in hit if r['value_at_stake_b'] is not None)
    gain_b = sum(r['value_at_stake_b'] for r in win if r['value_at_stake_b'] is not None)
    kpis = {
        'n_companies': len(rows), 'n_hit': len(hit), 'n_benefit': len(win),
        'n_sectors': len(sec_set), 'n_countries': len(ctry_set),
        'avg_hit_pct': round(sum(r['pct'] for r in hit) / len(hit), 2) if hit else None,
        'worst': {'label': worst['label'], 'pct': worst['pct'], 'id': worst['id']} if worst else None,
        'best': {'label': best['label'], 'pct': best['pct'], 'id': best['id']} if best else None,
        'mcap_hit_b': round(sum(r['mcap_b'] for r in hit if r['mcap_b']), 1) if hit else 0.0,
        'value_loss_b': round(loss_b, 1), 'value_gain_b': round(gain_b, 1),
        'n_with_mcap': sum(1 for r in rows if r['mcap_b']),
    }

    def group(key, label_key):
        g = {}
        for r in rows:
            k = r[key] or '—'
            e = g.setdefault(k, {'key': k, 'label': r[label_key] or '—', 'n': 0, 'sum_pct': 0.0, 'value_b': 0.0,
                                 'n_hit': 0, 'n_benefit': 0})
            e['n'] += 1
            e['sum_pct'] += r['pct']
            e['n_hit'] += r['pct'] < 0
            e['n_benefit'] += r['pct'] > 0
            if r['value_at_stake_b'] is not None:
                e['value_b'] += r['value_at_stake_b']
        out = []
        for e in g.values():
            e['avg_pct'] = round(e.pop('sum_pct') / e['n'], 2)
            e['value_b'] = round(e['value_b'], 2)
            out.append(e)
        return sorted(out, key=lambda e: (e['value_b'], e['avg_pct']))

    portfolio = {'status': 'no_positions'}
    pos = clean_positions(positions)
    if pos:
        by_row = {r['id']: r for r in rows}
        touched, untouched, tot, est = [], 0, 0.0, 0.0
        for p in pos:
            tot += p['usd']
            r = by_row.get(p['id'])
            if r is None:
                untouched += 1
                continue
            e = round(p['usd'] * r['pct'] / 100, 2)
            est += e
            touched.append({'id': p['id'], 'label': r['label'], 'symbol': p['symbol'] or r['ticker'], 'usd': p['usd'],
                            'pct': r['pct'], 'est_usd': e, 'channel': r['channel'], 'path': r['path']})
        touched.sort(key=lambda x: x['est_usd'])
        portfolio = {'status': 'ok' if touched else 'untouched', 'positions': touched, 'n_untouched': untouched,
                     'total_usd': round(tot, 2), 'est_usd': round(est, 2),
                     'est_pct': round(est / tot * 100, 2) if tot else None,
                     'note': ('Aritmética simple: monto × % estimado del escenario. Es una estimación estructural, no un '
                              'precio ni un pronóstico.' if es else
                              'Simple arithmetic: amount × the scenario\'s estimated %. A structural estimate, not a price '
                              'or a forecast.')}

    if worst:
        hl = (f"{len(hit)} empresas golpeadas en {len(sec_set)} sectores; la más afectada, {worst['label']} "
              f"({worst['pct']:+.1f} %)" if es else
              f"{len(hit)} companies hit across {len(sec_set)} sectors; the hardest hit, {worst['label']} "
              f"({worst['pct']:+.1f}%)")
        if best:
            hl += (f"; podría ganar {best['label']} ({best['pct']:+.1f} %)." if es else
                   f"; {best['label']} could gain ({best['pct']:+.1f}%).")
        else:
            hl += '.'
    else:
        hl = 'Sin empresas golpeadas de forma clara.' if es else 'No company clearly hit.'

    src = sim.get('pct_source')
    method = {
        'pct_source': src or ('structural' if sim.get('structural') else 'ai'),
        'pct_source_text': (sim.get('pct_note') or (
            ('Los % los estima la IA dentro de topes por tamaño de empresa, sobre la cadena de Khipus.' if es else
             'The % are estimated by the AI within size-based caps, on the Khipus supply chain.')
            if not sim.get('fallback') else
            ('Sin IA: estimación estructural por la fuerza de cada vínculo de la cadena.' if es else
             'No AI: structural estimate from the strength of each supply-chain link.'))),
        'model': sim.get('model') or None, 'kernel_semver': _kernel_semver(), 'kappa_pct': sim.get('kappa_pct'),
        'rounds': len(sim.get('rounds') or []), 'agents': len(sim.get('agents') or []),
        'caps_as_of': caps_as_of, 'caps_source': 'Yahoo Finance (Khipus live_caps)' if caps else None,
        'graph': 'Khipus (grafo vigente)' if es else 'Khipus (current graph)',
        'generated_at': (now or datetime.now(timezone.utc)).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'limits': ('Estimación de un escenario HIPOTÉTICO: no es un pronóstico de precios ni una recomendación. '
                   'Las empresas fuera del grafo de Khipus no aparecen.' if es else
                   'Estimate of a HYPOTHETICAL scenario: not a price forecast nor a recommendation. Companies outside '
                   'the Khipus graph do not appear.'),
    }
    return {'rows': rows, 'kpis': kpis, 'by_sector': group('sector', 'sector_label'),
            'by_country': group('country', 'country_label')[:8], 'portfolio': portfolio, 'headline': hl,
            'method': method}
