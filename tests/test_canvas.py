"""Canvas IA — criterio de tipo de gráfico y validación de la spec de la IA
(core/canvas_spec.py) + el endpoint /api/canvas/generate con la IA simulada."""
import json

import pytest

from core.canvas_spec import (CHART_CRITERION, VALID_TYPES, hints_prompt, sanitize_hints,
                              time_like, validate_spec)


def _bar(n, neg=False):
    return [{'label': f'C{i}', 'value': (i - 3 if neg else i + 1)} for i in range(n)]


# ── tipos y alias ────────────────────────────────────────────────────────────
def test_pie_alias_becomes_donut_when_few_slices():
    spec, fixes = validate_spec({'type': 'pie', 'title': 't', 'data': _bar(4)}, {'intent': 'composition'})
    assert spec['type'] == 'donut'
    assert any('pie' in f for f in fixes)


def test_pie_with_40_slices_becomes_treemap_for_composition_and_bar_otherwise():
    spec, _ = validate_spec({'type': 'pie', 'data': _bar(40)}, {'intent': 'composition'})
    assert spec['type'] == 'treemap'
    assert len(spec['data']) <= 30
    spec2, _ = validate_spec({'type': 'pie', 'data': _bar(40)}, {'intent': 'rank'})
    assert spec2['type'] == 'bar'
    assert len(spec2['data']) == 20                      # tope de barras


def test_donut_with_negatives_becomes_bar():
    spec, _ = validate_spec({'type': 'donut', 'data': _bar(4, neg=True)}, {})
    assert spec['type'] == 'bar'


def test_unknown_type_is_inferred_from_data_shape():
    spec, _ = validate_spec({'type': 'sparkle', 'data': [{'label': 'a', 'x': 1, 'y': 2},
                                                         {'label': 'b', 'x': 2, 'y': 3},
                                                         {'label': 'c', 'x': 3, 'y': 1}]}, {})
    assert spec['type'] == 'scatter'
    spec2, _ = validate_spec({'data': [{'label': 'a', 'value': 1}, {'label': 'b', 'value': 3}]}, {})
    assert spec2['type'] == 'bar'


def test_all_types_known_to_criterion():
    for t in ('bar', 'line', 'kpi', 'donut', 'treemap', 'histogram', 'scatter', 'heatmap', 'table', 'grouped', 'radar'):
        assert t in VALID_TYPES
    for intent in ('compare', 'trend', 'rank', 'composition', 'distribution', 'relationship', 'single_metric'):
        assert intent in CHART_CRITERION


# ── barras ───────────────────────────────────────────────────────────────────
def test_bars_sorted_descending_for_ranking():
    data = [{'label': 'A', 'value': 1}, {'label': 'B', 'value': 9}, {'label': 'C', 'value': 5}]
    spec, fixes = validate_spec({'type': 'bar', 'data': data}, {'intent': 'rank'})
    assert [d['label'] for d in spec['data']] == ['B', 'C', 'A']
    assert 'bars sorted' in fixes


def test_bars_over_years_keep_chronological_order():
    data = [{'label': '2021', 'value': 5}, {'label': '2022', 'value': -2}, {'label': '2023', 'value': 9}]
    spec, _ = validate_spec({'type': 'bar', 'data': data}, {'intent': 'trend'})
    assert [d['label'] for d in spec['data']] == ['2021', '2022', '2023']


def test_composition_bar_becomes_donut_or_treemap():
    spec, _ = validate_spec({'type': 'bar', 'data': _bar(5)}, {'intent': 'composition'})
    assert spec['type'] == 'donut'
    spec2, _ = validate_spec({'type': 'bar', 'data': _bar(12)}, {'intent': 'composition'})
    assert spec2['type'] == 'treemap'


def test_single_value_bar_becomes_kpi():
    spec, _ = validate_spec({'type': 'bar', 'data': [{'label': 'Margen', 'value': 62}]}, {'intent': 'single_metric'})
    assert spec['type'] == 'kpi'


def test_numeric_strings_are_coerced_but_magnitudes_never_guessed():
    data = [{'label': 'A', 'value': '62%'}, {'label': 'B', 'value': '1,250'}, {'label': 'C', 'value': '$1.2B'},
            {'label': 'D', 'value': None}, {'label': 'E', 'value': float('nan')}]
    spec, fixes = validate_spec({'type': 'bar', 'data': data}, {})
    vals = {d['label']: d['value'] for d in spec['data']}
    assert vals == {'B': 1250, 'A': 62}                 # "$1.2B", None y NaN se descartan
    assert any('dropped' in f for f in fixes)


def test_empty_after_cleaning_raises():
    with pytest.raises(ValueError):
        validate_spec({'type': 'bar', 'data': [{'label': 'x', 'value': 'n/a'}]}, {})
    with pytest.raises(ValueError):
        validate_spec('not a dict', {})


# ── líneas ───────────────────────────────────────────────────────────────────
def test_line_points_without_time_axis_become_bars():
    data = [{'label': 'Nvidia', 'value': 62}, {'label': 'AMD', 'value': 8}]
    spec, fixes = validate_spec({'type': 'line', 'data': data}, {'intent': 'compare'})
    assert spec['type'] == 'bar'
    assert any('time axis' in f for f in fixes)


def test_line_points_with_years_become_a_series():
    data = [{'label': '2023', 'value': 27}, {'label': '2024', 'value': 61}, {'label': '2025', 'value': 130}]
    spec, _ = validate_spec({'type': 'line', 'data': data, 'config': {'unit': '$B'}}, {'intent': 'trend'})
    assert spec['type'] == 'line'
    assert spec['data'][0]['values'] == [27, 61, 130]
    assert spec['config']['labels'] == ['2023', '2024', '2025']


def test_time_like():
    assert time_like(['2021', '2022', '2023'])
    assert time_like(['Q1 2024', 'Q2 2024'])
    assert not time_like(['Nvidia', 'AMD'])


# ── otros tipos ──────────────────────────────────────────────────────────────
def test_scatter_needs_numeric_points():
    with pytest.raises(ValueError):
        validate_spec({'type': 'scatter', 'data': [{'label': 'a', 'x': 'foo', 'y': 1}]}, {})


def test_radar_values_clipped_and_few_axes_to_grouped():
    spec, _ = validate_spec({'type': 'radar', 'data': [{'label': 'A', 'values': [120, -5, 50]}],
                             'config': {'axes': ['x', 'y', 'z']}}, {})
    assert spec['data'][0]['values'] == [100, 0, 50]
    spec2, _ = validate_spec({'type': 'radar', 'data': [{'label': 'A', 'values': [1, 2]}, {'label': 'B', 'values': [3, 4]}],
                              'config': {'axes': ['m1', 'm2']}}, {})
    assert spec2['type'] == 'grouped'
    assert spec2['config']['series_labels'] == ['A', 'B']
    assert spec2['data'][0] == {'label': 'm1', 'values': [1, 3]}


def test_heatmap_trimmed_to_10x10():
    data = [{'row': f'r{i}', 'col': f'c{j}', 'value': i + j} for i in range(14) for j in range(12)]
    spec, _ = validate_spec({'type': 'heatmap', 'data': data}, {})
    assert len(spec['config']['rows']) == 10 and len(spec['config']['cols']) == 10
    assert len(spec['data']) == 100


def test_output_marks_engine_and_keeps_source():
    spec, _ = validate_spec({'type': 'bar', 'title': 'T', 'data': _bar(3), 'source': 'catálogo: nrs'}, {})
    assert spec['engine'] == 'ai'
    assert spec['source'] == 'catálogo: nrs'


# ── hints ────────────────────────────────────────────────────────────────────
def test_sanitize_hints_filters_garbage():
    h = sanitize_hints({'intent': 'compare', 'chart': 'pie', 'entities': [{'id': 'Nvidia', 'label': 'Nvidia', 'mkt': 'NVDA'}, 'x'],
                        'metrics': ['margin', '<script>'], 'timeframe_days': 99999, 'group_by': ['sector', 'evil'],
                        'top_n': 500, 'reason': 'metric_unavailable!'})
    assert h['intent'] == 'compare'
    assert h['chart'] == 'donut'
    assert h['entities'] == [{'id': 'Nvidia', 'label': 'Nvidia', 'mkt': 'NVDA'}]
    assert h['metrics'] == ['margin', 'script']
    assert 'timeframe_days' not in h and 'top_n' not in h
    assert h['group_by'] == ['sector']
    assert h['reason'] == 'metric_unavailable'
    assert sanitize_hints('nope') == {}
    assert sanitize_hints({'intent': 'hack'}) == {}


def test_hints_prompt_mentions_intent_and_criterion():
    txt = hints_prompt({'intent': 'composition', 'entities': [{'id': 'TSMC', 'label': 'TSMC', 'mkt': 'TSM'}], 'metrics': ['mktcap']})
    assert 'composition' in txt and 'donut' in txt and 'TSMC' in txt and 'mktcap' in txt
    assert hints_prompt({}) == ''


# ── endpoint con la IA simulada ──────────────────────────────────────────────
@pytest.fixture
def client(monkeypatch):
    import server
    server.app.config['TESTING'] = True
    try:
        server.cache.clear()
    except Exception:  # noqa: BLE001
        pass
    monkeypatch.setattr(server, '_ai_configured', lambda: True)
    return server


def test_endpoint_fixes_pie_with_many_slices(client, monkeypatch):
    seen = {}

    def fake(system, prompt, max_tokens, tier='fast'):
        seen['system'], seen['prompt'] = system, prompt
        data = [{'label': f'Sector {i}', 'value': 10 + i} for i in range(9)]
        return json.dumps({'type': 'pie', 'title': 'Cap por sector', 'data': data, 'config': {'unit': '$B'}}), 'fake-model'

    monkeypatch.setattr(client, '_claude_complete', fake)
    body = {'query': 'capitalización por sector (test pie)', 'hints': {'intent': 'composition', 'metrics': ['mktcap'], 'group_by': ['sector']},
            'context': {'nodes': [{'id': 'Nvidia', 'label': 'Nvidia', 'mktcap_b': 3200, 'nrs': 37}]}}
    r = client.app.test_client().post('/api/canvas/generate', json=body)
    assert r.status_code == 200, r.get_json()
    spec = r.get_json()['spec']
    assert spec['type'] == 'treemap'
    assert spec['engine'] == 'ai'
    # la IA recibió el criterio y la consulta parseada
    assert 'CHART-TYPE CRITERION' in seen['system']
    assert 'PARSED REQUEST' in seen['prompt'] and 'composition' in seen['prompt']
    assert '"mktcap_b": 3200' in seen['prompt']


def test_endpoint_rejects_undrawable_spec(client, monkeypatch):
    monkeypatch.setattr(client, '_claude_complete',
                        lambda *a, **k: (json.dumps({'type': 'bar', 'data': [{'label': 'x', 'value': 'n/a'}]}), 'fake'))
    r = client.app.test_client().post('/api/canvas/generate', json={'query': 'algo indibujable (test)', 'context': {}})
    assert r.status_code == 502
    assert 'invalid chart spec' in r.get_json()['error']


def test_endpoint_includes_hinted_entities_in_context(client, monkeypatch):
    seen = {}

    def fake(system, prompt, max_tokens, tier='fast'):
        seen['prompt'] = prompt
        return json.dumps({'type': 'kpi', 'data': [{'label': 'Margen', 'value': 62, 'unit': '%'}]}), 'fake'

    monkeypatch.setattr(client, '_claude_complete', fake)
    nodes = [{'id': f'N{i}', 'label': f'Empresa {i}', 'nrs': i} for i in range(200)]
    nodes.append({'id': 'ZZTarget', 'label': 'Zeta Objetivo', 'margin': 0.62})
    body = {'query': 'margen de la zeta (test)', 'hints': {'intent': 'single_metric', 'metrics': ['margin'],
                                                         'entities': [{'id': 'ZZTarget', 'label': 'Zeta Objetivo'}]},
            'context': {'nodes': nodes}}
    r = client.app.test_client().post('/api/canvas/generate', json=body)
    assert r.status_code == 200
    assert 'ZZTarget' in seen['prompt']
    assert r.get_json()['spec']['type'] == 'kpi'
