"""core/canvas_spec.py — Canvas IA: criterio de tipo de gráfico + validación.

Feedback de Fabrizio (2026-10): "que haya un criterio de qué tipo de gráfico
mostrar y que se integre a la IA cuando la consulta no pueda ser respondida de
forma precisa". El cliente (engine/localcharts.js) parsea la consulta en
{intent, entities, metrics, timeframe…} y, cuando no puede responder con
precisión sin IA, manda esos `hints` a /api/canvas/generate. Aquí:

  - CHART_CRITERION: la tabla intención → gráfico (la MISMA que el cliente).
  - sanitize_hints(raw): limpia los hints que vienen del navegador.
  - hints_prompt(h): bloque de texto para el prompt de la IA.
  - validate_spec(spec, hints, query) → (spec, fixes): normaliza el tipo
    (alias, pie de 40 porciones → barras, línea sin tiempo → barras…), limpia
    los datos (sin NaN, números como número) y aplica límites. Nunca INVENTA
    valores: solo reordena, recorta, convierte o descarta.

    intención        gráfico
    ---------------  ------------------------------------------------------
    compare          bar (1 métrica) · grouped (varias) · radar si se pide ·
                     table si >6 ítems
    trend            line · bar para montos anuales que pueden ser negativos
    rank             bar horizontal ordenada (desc)
    composition      donut si ≤6 porciones · treemap si más
    distribution     histogram
    relationship     scatter (bubble si hay 3ª métrica)
    single_metric    kpi
    profile          kpi (varias tarjetas) o table
    cross            heatmap
    detalle          table
"""
import math
import re

VALID_TYPES = ('bar', 'line', 'bubble', 'treemap', 'heatmap', 'radar', 'scatter', 'table',
               'grouped', 'kpi', 'donut', 'histogram')

INTENTS = ('compare', 'trend', 'rank', 'composition', 'distribution', 'relationship',
           'single_metric', 'profile', 'cross', 'explain', 'other')

CHART_CRITERION = {
    'compare': 'bar (one metric, sorted) or grouped (several metrics); radar only if asked; table if >6 items',
    'trend': 'line (bar only for annual amounts that can be negative: capex, free cash flow, growth %)',
    'rank': 'bar, horizontal, sorted descending',
    'composition': 'donut if <=6 slices, otherwise treemap',
    'distribution': 'histogram (pre-binned counts)',
    'relationship': 'scatter (bubble if a third metric sizes the dots)',
    'single_metric': 'kpi',
    'profile': 'kpi (several tiles) or table',
    'cross': 'heatmap',
    'explain': 'the chart that best supports the explanation with the given data (often bar or line); put the key insight in subtitle',
    'other': 'bar',
}

_TYPE_ALIAS = {
    'pie': 'donut', 'doughnut': 'donut', 'donut': 'donut', 'dona': 'donut', 'torta': 'donut',
    'column': 'bar', 'columns': 'bar', 'barh': 'bar', 'hbar': 'bar', 'horizontal_bar': 'bar',
    'bar_chart': 'bar', 'bars': 'bar', 'ranking': 'bar',
    'area': 'line', 'timeseries': 'line', 'time_series': 'line', 'lines': 'line', 'line_chart': 'line',
    'number': 'kpi', 'metric': 'kpi', 'stat': 'kpi', 'card': 'kpi', 'kpis': 'kpi', 'big_number': 'kpi',
    'hist': 'histogram', 'matrix': 'heatmap', 'heat_map': 'heatmap',
    'grouped_bar': 'grouped', 'grouped_bars': 'grouped', 'clustered': 'grouped', 'clustered_bar': 'grouped',
    'multi_bar': 'grouped', 'spider': 'radar', 'points': 'scatter', 'dispersion': 'scatter',
}

_TIME_RE = re.compile(r'^(?:(?:19|20)\d{2}(?:[-/ ]?(?:Q[1-4]|\d{1,2}))?|(?:Q[1-4]|T[1-4]) ?(?:19|20)\d{2}'
                      r'|\d{4}-\d{2}-\d{2}|\d{1,2} \w{3,5}\.? \d{2,4}|(?:ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic|'
                      r'jan|apr|aug|dec)\w*\.? ?\d{2,4})$', re.I)


def _num(v):
    """Número o None. Acepta '62', '62.5', '1,234', '62%' (sin cambiar escala).
    NO interpreta sufijos de magnitud ('$1.2B') para no inventar la escala."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v) if math.isfinite(v) else None
    if isinstance(v, str):
        s = v.strip().replace(',', '').rstrip('%').strip()
        if re.fullmatch(r'[-+]?\d+(?:\.\d+)?', s):
            f = float(s)
            return f if math.isfinite(f) else None
    return None


def _clean_num(v):
    f = _num(v)
    if f is None:
        return None
    return int(f) if f.is_integer() and abs(f) < 1e15 else round(f, 4)


def time_like(labels):
    labs = [str(l).strip() for l in labels if l is not None]
    return len(labs) >= 2 and all(_TIME_RE.match(l) for l in labs)


def sanitize_hints(raw):
    """Hints del navegador → dict acotado y seguro (o {})."""
    if not isinstance(raw, dict):
        return {}
    out = {}
    it = str(raw.get('intent') or '').strip().lower()
    if it in INTENTS:
        out['intent'] = it
    ch = str(raw.get('chart') or '').strip().lower()
    ch = _TYPE_ALIAS.get(ch, ch)
    if ch in VALID_TYPES:
        out['chart'] = ch
    ents = []
    for e in (raw.get('entities') or [])[:12]:
        if isinstance(e, dict) and e.get('id'):
            ents.append({'id': str(e['id'])[:60], 'label': str(e.get('label') or e['id'])[:80],
                         'mkt': (str(e['mkt'])[:16] if e.get('mkt') else None)})
    if ents:
        out['entities'] = ents
    mets = [re.sub(r'[^a-z_]', '', str(m).lower())[:24] for m in (raw.get('metrics') or [])[:6]]
    mets = [m for m in mets if m]
    if mets:
        out['metrics'] = mets
    tf = _num(raw.get('timeframe_days'))
    if tf and 0 < tf <= 36500:
        out['timeframe_days'] = int(tf)
    gb = [g for g in (raw.get('group_by') or []) if g in ('sector', 'country')][:2]
    if gb:
        out['group_by'] = gb
    if raw.get('country'):
        out['country'] = str(raw['country'])[:40]
    tn = _num(raw.get('top_n'))
    if tn and 1 <= tn <= 50:
        out['top_n'] = int(tn)
    if raw.get('reason'):
        out['reason'] = re.sub(r'[^a-z_]', '', str(raw['reason']).lower())[:30]
    unk = [str(w)[:30] for w in (raw.get('unknown') or [])[:8] if isinstance(w, str)]
    if unk:
        out['unknown'] = unk
    return out


def hints_prompt(h):
    """Bloque del prompt con la consulta YA PARSEADA por el router del cliente."""
    if not h:
        return ''
    lines = ['PARSED REQUEST (from the app router — trust it unless the query clearly says otherwise):']
    if h.get('intent'):
        lines.append(f"- intent: {h['intent']} → recommended chart: {CHART_CRITERION.get(h['intent'], 'bar')}")
    if h.get('chart'):
        lines.append(f"- suggested type: {h['chart']}")
    if h.get('entities'):
        lines.append('- companies (node ids): ' + ', '.join(f"{e['label']} [{e['id']}]" for e in h['entities']))
    if h.get('metrics'):
        lines.append('- metrics: ' + ', '.join(h['metrics']))
    if h.get('timeframe_days'):
        lines.append(f"- timeframe: last {h['timeframe_days']} days")
    if h.get('group_by'):
        lines.append('- group by: ' + ', '.join(h['group_by']))
    if h.get('country'):
        lines.append(f"- filter country/region: {h['country']}")
    if h.get('top_n'):
        lines.append(f"- top N: {h['top_n']}")
    if h.get('unknown'):
        lines.append('- words the app could not map (interpret them): ' + ', '.join(h['unknown']))
    if h.get('reason'):
        lines.append(f"- why the app sent it to you: {h['reason']}")
    return '\n'.join(lines)


def _infer_type(data):
    if not data:
        return 'bar'
    d0 = data[0] if isinstance(data[0], dict) else {}
    if 'x' in d0 and 'y' in d0:
        return 'bubble' if 'r' in d0 else 'scatter'
    if 'row' in d0 and 'col' in d0:
        return 'heatmap'
    if isinstance(d0.get('values'), list):
        return 'line'
    if 'value' in d0:
        return 'bar'
    return 'table'


def validate_spec(spec, hints=None, query=''):
    """Normaliza la spec de la IA. Devuelve (spec, fixes). Lanza ValueError si
    no queda nada dibujable (el endpoint responde 502 y el cliente cae a la
    tarjeta honesta)."""
    if not isinstance(spec, dict):
        raise ValueError('spec is not an object')
    hints = hints or {}
    intent = hints.get('intent')
    fixes = []
    t = str(spec.get('type') or '').strip().lower()
    if t in _TYPE_ALIAS:
        if _TYPE_ALIAS[t] != t:
            fixes.append(f'type {t}→{_TYPE_ALIAS[t]}')
        t = _TYPE_ALIAS[t]
    data = spec.get('data')
    if not isinstance(data, list):
        data = []
    data = [d for d in data if isinstance(d, dict)]
    if t not in VALID_TYPES:
        nt = _infer_type(data)
        fixes.append(f'unknown type {t or "∅"}→{nt}')
        t = nt
    cfg = spec.get('config') if isinstance(spec.get('config'), dict) else {}

    # ── limpieza por forma de datos ────────────────────────────────────────
    if t in ('bar', 'donut', 'treemap', 'histogram', 'kpi'):
        clean = []
        for d in data:
            v = _clean_num(d.get('value'))
            if v is None or d.get('label') in (None, ''):
                continue
            item = {'label': str(d['label'])[:80], 'value': v}
            for k in ('color', 'unit', 'sub', 'max'):
                if d.get(k) is not None:
                    item[k] = d[k] if k != 'max' else _clean_num(d[k])
            clean.append(item)
        if len(clean) < len(data):
            fixes.append(f'dropped {len(data) - len(clean)} non-numeric items')
        data = clean
    elif t in ('line', 'grouped', 'radar'):
        if t == 'line' and data and 'value' in data[0] and not isinstance(data[0].get('values'), list):
            # forma de puntos [{label,value}] → ¿hay tiempo? si no, son barras
            labels = [d.get('label') for d in data]
            if not time_like(labels) and intent != 'trend':
                sp, fx = validate_spec(dict(spec, type='bar'), hints, query)
                fx = ['line without a time axis→bar'] + fx
                sp['fixes'] = fx[:12]
                return sp, fx
            vals = [_clean_num(d.get('value')) for d in data]
            sl = cfg.get('series_labels') if isinstance(cfg.get('series_labels'), list) and cfg.get('series_labels') else [spec.get('title') or '']
            data = [{'label': str(sl[0]), 'values': vals}]
            cfg = dict(cfg, labels=[str(l) for l in labels])
            fixes.append('line points→series')
        clean = []
        for d in data:
            vals = d.get('values')
            if not isinstance(vals, list):
                continue
            item = {'label': str(d.get('label') or '')[:80], 'values': [_clean_num(v) for v in vals][:400]}
            for k in ('color', 'unit'):
                if d.get(k) is not None:
                    item[k] = d[k]
            if any(v is not None for v in item['values']):
                clean.append(item)
        data = clean
    elif t in ('scatter', 'bubble'):
        clean = []
        for d in data:
            x, y = _clean_num(d.get('x')), _clean_num(d.get('y'))
            if x is None or y is None:
                continue
            item = {'label': str(d.get('label') or d.get('id') or '')[:60], 'x': x, 'y': y}
            if t == 'bubble':
                r = _clean_num(d.get('r'))
                item['r'] = r if r is not None and r > 0 else 1
            if d.get('color'):
                item['color'] = d['color']
            clean.append(item)
        data = clean
        if len(data) < 3:
            raise ValueError('scatter needs at least 3 points with numeric x/y')
    elif t == 'heatmap':
        data = [{'row': str(d.get('row'))[:40], 'col': str(d.get('col'))[:40], 'value': _clean_num(d.get('value'))}
                for d in data if d.get('row') is not None and d.get('col') is not None and _clean_num(d.get('value')) is not None]
    elif t == 'table':
        data = data[:15]

    if not data:
        raise ValueError('no drawable data')

    # ── reglas del CRITERIO (tipo vs intención y forma) ─────────────────────
    if t == 'donut':
        if any(d['value'] < 0 for d in data):
            fixes.append('donut with negatives→bar'); t = 'bar'
        elif len(data) > 6:
            nt = 'treemap' if intent in (None, 'composition') else 'bar'
            fixes.append(f'donut with {len(data)} slices→{nt}'); t = nt
    if t == 'treemap' and any(d['value'] <= 0 for d in data):
        pos = [d for d in data if d['value'] > 0]
        if len(pos) < len(data) and any(d['value'] < 0 for d in data):
            fixes.append('treemap with negatives→bar'); t = 'bar'
        else:
            data = pos
    if t == 'bar' and intent == 'composition' and 2 <= len(data) and all(d['value'] > 0 for d in data) \
            and not time_like([d['label'] for d in data]):
        nt = 'donut' if len(data) <= 6 else 'treemap'
        fixes.append(f'composition bar→{nt}'); t = nt
    if t == 'kpi' and len(data) > 6:
        fixes.append('kpi with many items→bar'); t = 'bar'
    if t == 'bar' and intent in ('single_metric',) and len(data) == 1:
        fixes.append('single value bar→kpi'); t = 'kpi'
    if t == 'line' and intent in ('rank', 'composition', 'compare') and len(data) == 1:
        labels = cfg.get('labels') or []
        if labels and not time_like(labels) and len(labels) == len(data[0]['values']):
            fixes.append(f'line for {intent}→bar')
            t = 'bar'
            data = [{'label': str(l), 'value': v} for l, v in zip(labels, data[0]['values']) if v is not None]
    if t == 'radar':
        axes = cfg.get('axes') if isinstance(cfg.get('axes'), list) else []
        if len(axes) < 3:
            if not axes:
                raise ValueError('radar without axes')
            fixes.append('radar with <3 axes→grouped'); t = 'grouped'
            cfg = dict(cfg, series_labels=[d['label'] for d in data])
            data = [{'label': str(a), 'values': [d['values'][i] if i < len(d['values']) else None for d in data]}
                    for i, a in enumerate(axes)]
        else:
            for d in data:
                d['values'] = [None if v is None else max(0, min(100, v)) for v in d['values']][:len(axes)]
            if len(data) > 6:
                fixes.append('radar with >6 series→first 6'); data = data[:6]
    if t == 'grouped':
        sl = cfg.get('series_labels') if isinstance(cfg.get('series_labels'), list) else []
        n = max((len(d['values']) for d in data), default=0)
        if len(sl) != n:
            sl = (list(sl) + [f'S{i + 1}' for i in range(n)])[:n]
            cfg = dict(cfg, series_labels=sl)
            fixes.append('grouped series_labels fixed')
    if t in ('scatter', 'bubble') and len(data) > 80:
        data = data[:80]; fixes.append('scatter capped at 80')
    if t == 'heatmap':
        rows = cfg.get('rows') if isinstance(cfg.get('rows'), list) else list(dict.fromkeys(d['row'] for d in data))
        cols = cfg.get('cols') if isinstance(cfg.get('cols'), list) else list(dict.fromkeys(d['col'] for d in data))
        rows, cols = [str(r) for r in rows][:10], [str(c) for c in cols][:10]
        data = [d for d in data if d['row'] in rows and d['col'] in cols]
        cfg = dict(cfg, rows=rows, cols=cols)
        if not data:
            raise ValueError('no drawable data')

    # ── orden y topes ───────────────────────────────────────────────────────
    if t == 'bar':
        labels = [d['label'] for d in data]
        if not time_like(labels) and intent != 'trend' and cfg.get('sort') != 'none':
            asc = cfg.get('sort') == 'asc'
            order = sorted(data, key=lambda d: d['value'], reverse=not asc)
            if order != data:
                fixes.append('bars sorted')
            data = order
        else:
            cfg = dict(cfg, sort='none')
        if len(data) > 20:
            data = data[:20]; fixes.append('bar capped at 20')
    if t in ('donut', 'treemap'):
        data = sorted(data, key=lambda d: d['value'], reverse=True)[:30]
    if t == 'table':
        cols = cfg.get('columns')
        if not isinstance(cols, list) or not cols:
            cfg = dict(cfg, columns=list(data[0].keys())[:8])

    out = {
        'type': t,
        'title': str(spec.get('title') or query or '')[:140],
        'subtitle': str(spec.get('subtitle') or '')[:280],
        'data': data,
        'config': cfg,
        'engine': 'ai',
    }
    src = spec.get('source') or cfg.get('source')
    if src:
        out['source'] = str(src)[:200]
    if spec.get('note'):
        out['note'] = str(spec['note'])[:240]
    if fixes:
        out['fixes'] = fixes[:12]
    return out, fixes
