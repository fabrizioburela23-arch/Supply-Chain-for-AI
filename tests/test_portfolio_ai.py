"""Asistente de carteras (core/portfolio_ai.py) — sin red, historias sintéticas."""
import hashlib
import math
import os
import random
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import portfolio_ai as pa  # noqa: E402

DATES = [f'2025-{m:02d}-{d:02d}' for m in range(1, 13) for d in range(1, 22)]   # 252 días


def synth_history(sym, days=DATES):
    """Serie determinista por símbolo: volatilidad entre 1 % y 4 % diario + factor común."""
    seed = int(hashlib.md5(sym.encode()).hexdigest()[:8], 16)
    rnd = random.Random(seed)
    mkt = random.Random(42)
    vol = 0.01 + (seed % 300) / 10000.0
    beta = 0.5 + (seed % 7) / 7
    out, p = {}, 50.0 + seed % 200
    for d in days:
        p *= 1 + beta * mkt.gauss(0.0003, 0.008) + rnd.gauss(0.0002, vol)
        out[d] = round(p, 4)
    return out, 'USD'


def fx_one(cur):
    return 1.0


def base(**kw):
    p = {'goal': 'equilibrio', 'horizon': '1-3', 'risk': 'medio', 'amount_usd': 10000,
         'themes': [], 'exclude': [], 'lang': 'es'}
    p.update(kw)
    return pa.validate_propose(p)


def run(p, history_fn=synth_history, **kw):
    return pa.build_proposals(p, history_fn=history_fn, fx_fn=fx_one, caps={}, claims={}, **kw)


# ── validación ───────────────────────────────────────────────────────────────
@pytest.mark.parametrize('body,frag', [
    ({'amount_usd': 50}, 'monto'),
    ({'amount_usd': 'x'}, 'monto'),
    ({'amount_usd': 1000, 'risk': 'extremo'}, 'riesgo'),
    ({'amount_usd': 1000, 'goal': 'magia'}, 'objetivo'),
    ({'amount_usd': 1000, 'horizon': '50'}, 'horizonte'),
    ({'amount_usd': 1000, 'themes': ['bitcoin']}, 'tema'),
    ({'amount_usd': 1000, 'exclude': [f'x{i}' for i in range(25)]}, 'máximo'),
])
def test_validacion(body, frag):
    with pytest.raises(pa.ValidationError) as e:
        pa.validate_propose(body)
    assert frag in e.value.es and e.value.en


def test_validacion_mapea_ingles():
    p = pa.validate_propose({'goal': 'growth', 'risk': 'high', 'horizon': '3+', 'amount_usd': '5000',
                             'themes': 'semis, energia', 'lang': 'en'})
    assert p['goal'] == 'crecimiento' and p['risk'] == 'alto' and p['themes'] == ['semis', 'energia']
    assert p['lang'] == 'en'


# ── matemática ───────────────────────────────────────────────────────────────
def test_inverse_vol_y_risk_parity():
    w = pa.inverse_vol({'A': 0.01, 'B': 0.02})
    assert abs(w['A'] - 2 / 3) < 1e-9 and abs(sum(w.values()) - 1) < 1e-12
    cov = {'A': {'A': 0.0004, 'B': 0.0}, 'B': {'A': 0.0, 'B': 0.0001}}
    rp = pa.risk_parity(cov, ['A', 'B'])
    # sin correlación la paridad de riesgo = inversa de la volatilidad
    assert abs(rp['A'] - 1 / 3) < 1e-6
    sw = {a: sum(cov[a][b] * rp[b] for b in rp) for a in rp}
    rc = [rp[a] * sw[a] for a in rp]
    assert abs(rc[0] - rc[1]) < 1e-10


def test_apply_caps_respeta_topes():
    meta = {s: {'sector': 'x' if i < 3 else 'y' if i < 6 else 'z', 'country': 'EEUU' if i % 2 else 'Japon'}
            for i, s in enumerate('ABCDEFGHIJ')}
    w0 = {s: (10 if s == 'A' else 1) for s in meta}
    w, relaxed = pa.apply_caps(w0, meta, 0.15, 0.40, 0.70)
    assert abs(sum(w.values()) - 1) < 1e-9 and not relaxed
    assert max(w.values()) <= 0.15 + 1e-6
    for sec in 'xyz':
        assert sum(v for s, v in w.items() if meta[s]['sector'] == sec) <= 0.40 + 1e-6


def test_apply_caps_relaja_si_imposible():
    meta = {s: {'sector': 'solo', 'country': 'EEUU'} for s in 'ABCD'}
    w, relaxed = pa.apply_caps({s: 1 for s in meta}, meta, 0.2, 0.3, 0.6)
    assert 'sector' in relaxed and 'country' in relaxed
    assert abs(sum(w.values()) - 1) < 1e-9 and max(w.values()) <= 0.25 + 1e-9   # 1/n cuando n·cap < 1


# ── construcción determinista ────────────────────────────────────────────────
def test_propuesta_basica_topes_y_pesos():
    res = run(base())
    assert res['ok'] and 2 <= len(res['portfolios']) <= 3
    prof = pa.PROFILES['medio']
    for pf in res['portfolios']:
        ws = [p['weight'] for p in pf['positions']]
        assert abs(sum(ws) - 1) < 1e-3
        assert max(ws) <= prof['max_name'] + 1e-3
        if 'sector' not in pf['caps']['relaxed']:
            assert max(pf['metrics']['sector_weights_pct'].values()) <= prof['max_sector'] * 100 + 0.1
        assert abs(sum(p['usd'] for p in pf['positions']) - 10000) < 0.5
        for p in pf['positions']:
            assert abs(p['shares'] * p['price'] - p['usd']) < 0.05
        m = pf['metrics']
        assert m['vol_ann_pct'] > 0 and m['var95_1d_usd'] > 0 and m['n_names'] == len(pf['positions'])
        assert pf['risks_es'] and pf['risks_en']
    ids = [frozenset(p['symbol'] for p in pf['positions']) for pf in res['portfolios']]
    assert len(set(ids)) == len(ids)      # sin duplicados


def test_inverse_vol_pondera_mas_a_la_menos_volatil():
    res = run(base(risk='alto'))
    pf = [x for x in res['portfolios'] if x['method'] == 'inverse_vol'][0]
    uncapped = [p for p in pf['positions'] if p['weight'] < pa.PROFILES['alto']['max_name'] - 1e-3]
    if len(uncapped) >= 2:
        a, b = min(uncapped, key=lambda p: p['vol_ann_pct']), max(uncapped, key=lambda p: p['vol_ann_pct'])
        assert a['weight'] >= b['weight']


def test_filtro_por_tema_y_exclusiones():
    res = run(base(themes=['energia'], exclude=['Estados Unidos', 'algo-que-no-existe']))
    assert res['ok']
    for pf in res['portfolios']:
        for p in pf['positions']:
            assert p['sector'] == 'energia' and p['country'] != 'EEUU'
    assert any('no reconocido' in e['reason'] for e in res['excluded'])


def test_excluir_empresa_por_nombre():
    res = run(base(themes=['semis'], exclude=['Nvidia']))
    assert all(p['node_id'] != 'Nvidia' for pf in res['portfolios'] for p in pf['positions'])


def test_riesgo_bajo_mas_nombres_y_tope_de_volatilidad():
    res = run(base(risk='bajo', horizon='lt1'))
    assert res['ok'] and len(res['portfolios']) <= 2           # sin la de "convicción"
    cap = pa.PROFILES['bajo']['max_vol'] * pa.HORIZON_VOL_MULT['lt1']
    for pf in res['portfolios']:
        assert all(p['vol_ann_pct'] <= cap + 1 for p in pf['positions'])
        n = len(pf['positions'])
        assert max(p['weight'] for p in pf['positions']) <= max(0.12, 1 / n) + 1e-3
        assert any('excluida' in e['reason'] or 'volatilidad' in e['reason'] for e in res['excluded'])


def test_sin_datos_suficientes():
    res = run(base(), history_fn=lambda s: ({}, None))
    assert not res['ok'] and 'datos' in res['error']
    assert any('historia' in e['reason'] for e in res['excluded'])


def test_tema_sin_empresas_suficientes():
    res = run(base(themes=['espacio'], exclude=['espacio']))
    assert not res['ok'] and 'suficientes' in res['error']


def test_claims_negativos_bajan_el_ranking():
    p = base(risk='alto')
    uni = [c for c in pa.universe()]
    top = sorted(uni, key=lambda c: -pa.score(dict(c, live=False, mcap_b=None), pa.SCORE_W['alto'], 'equilibrio',
                                              max(x['degree'] for x in uni), {}))[0]
    claims = {top['id']: [{'stance': 'negative', 'confidence': 0.9}] * 3}
    r = pa.research_signal(claims)
    assert r[top['id']]['net'] == -1.0 and r[top['id']]['neg'] == 3
    s0 = pa.score(dict(top, live=False, mcap_b=None), pa.SCORE_W['alto'], 'equilibrio', 50, {})
    s1 = pa.score(dict(top, live=False, mcap_b=None), pa.SCORE_W['alto'], 'equilibrio', 50, r)
    assert s1 < s0
    assert p['risk'] == 'alto'


# ── redacción y endpoints ────────────────────────────────────────────────────
@pytest.fixture
def client(monkeypatch):
    import server
    monkeypatch.setattr(pa, '_history', synth_history)
    monkeypatch.setattr(pa, '_fx', fx_one)
    monkeypatch.setattr(pa, '_live_caps', lambda: {'caps': {'Nvidia': {'price': 180.5, 'mcap_b': 4400}}})
    monkeypatch.setattr(pa, '_claims_for', lambda ids: {})
    monkeypatch.setattr(pa, '_portfolio_report', lambda pos: {
        'ok': True, 'days': 250, 'as_of': '2025-12-21', 'portfolio_value_usd': 5000, 'vol_ann_pct': 31.2,
        'var95': {'hist_1d_usd': 140.5, 'hist_1d_pct': 2.81}, 'max_drawdown_pct': -22.0, 'beta_spy': 1.3,
        'diversification_ratio': 1.2, 'positions': [{'symbol': 'NVDA', 'weight_pct': 100, 'vol_ann_pct': 45,
                                                     'risk_contrib_pct': 100}]})
    import core.http as h
    h._rate_buckets.clear()
    pa._CACHE.clear()
    server.app.config['TESTING'] = True
    return server.app.test_client()


def _no_ai(monkeypatch):
    from core import ai
    monkeypatch.setattr(ai, '_ai_configured', lambda: False)


def _fake_ai(monkeypatch, reply):
    from core import ai
    calls = []
    monkeypatch.setattr(ai, '_ai_configured', lambda: True)

    def fake(system, prompt, max_tokens=1000, tier='fast', model=None, verify_numbers=True):
        calls.append(prompt)
        return (reply(prompt) if callable(reply) else reply), 'fake-model'
    monkeypatch.setattr(ai, '_ai_complete', fake)
    return calls


def test_propose_sin_ia(client, monkeypatch):
    _no_ai(monkeypatch)
    r = client.post('/api/portfolio-ai/propose', json={'amount_usd': 10000, 'risk': 'medio', 'lang': 'es'})
    assert r.status_code == 200
    d = r.get_json()
    assert d['ok'] and d['portfolios'] and 'no es asesoría' in d['disclaimer']
    for pf in d['portfolios']:
        assert pf['rationale_source'] == 'sin IA' and pf['rationale']


def test_propose_con_ia_falsa(client, monkeypatch):
    import json as _j
    calls = _fake_ai(monkeypatch, lambda prompt: _j.dumps({'diversificada': 'Texto de la IA.',
                                                            'baja_vol': 'Otro texto.'}))
    r = client.post('/api/portfolio-ai/propose', json={'amount_usd': 20000, 'risk': 'alto', 'lang': 'en',
                                                       'themes': ['semis']})
    d = r.get_json()
    assert r.status_code == 200 and len(calls) == 1
    by = {pf['id']: pf for pf in d['portfolios']}
    assert by['diversificada']['rationale'] == 'Texto de la IA.' and by['diversificada']['rationale_source'] == 'ai'
    if 'conviccion' in by:     # la IA no la redactó → respaldo determinista
        assert by['conviccion']['rationale_source'] == 'sin IA'
    assert 'educational' in d['disclaimer'].lower()


def test_propose_validacion_400(client):
    r = client.post('/api/portfolio-ai/propose', json={'amount_usd': 5})
    assert r.status_code == 400 and r.get_json()['code'] == 'invalid'
    r = client.post('/api/portfolio-ai/propose', data='no-json', content_type='text/plain')
    assert r.status_code == 400


def test_propose_sin_datos_422(client, monkeypatch):
    _no_ai(monkeypatch)
    monkeypatch.setattr(pa, '_history', lambda s: ({}, None))
    r = client.post('/api/portfolio-ai/propose', json={'amount_usd': 1000})
    assert r.status_code == 422 and r.get_json()['code'] == 'no_data'


def test_themes(client):
    d = client.get('/api/portfolio-ai/themes?lang=en').get_json()
    keys = [t['key'] for t in d['themes']]
    assert 'semis' in keys and 'energia' in keys and all(t['count'] > 0 for t in d['themes'])


def test_ask_sin_ia_correlacion_real(client, monkeypatch):
    _no_ai(monkeypatch)
    r = client.post('/api/portfolio-ai/ask', json={'question': '¿Nvidia y AMD se mueven juntas?', 'lang': 'es'})
    d = r.get_json()
    assert r.status_code == 200 and d['answer_source'] == 'sin IA'
    assert 'correlación' in d['answer'] and 'Nvidia' in d['entities'] and 'AMD' in d['entities']
    assert any(s['type'] == 'prices' for s in d['sources'])


def test_ask_con_ia_y_cartera(client, monkeypatch):
    calls = _fake_ai(monkeypatch, 'Diversificar es repartir el riesgo.')
    r = client.post('/api/portfolio-ai/ask', json={
        'question': 'quiero algo menos riesgoso', 'lang': 'es',
        'portfolio': {'name': 'Mi IA', 'positions': [{'symbol': 'NVDA', 'node_id': 'Nvidia', 'shares': 10}]},
        'history': [{'role': 'user', 'text': 'hola'}, {'role': 'assistant', 'text': '¡hola!'}]})
    d = r.get_json()
    assert r.status_code == 200 and d['ai'] and d['answer'] == 'Diversificar es repartir el riesgo.'
    assert 'volatilidad anual 31.2%' in calls[0] and 'CONVERSACIÓN PREVIA' in calls[0]
    assert any(s['type'] == 'portfolio' for s in d['sources'])


def test_ask_ia_falla_cae_a_determinista(client, monkeypatch):
    from core import ai
    monkeypatch.setattr(ai, '_ai_configured', lambda: True)

    def boom(*a, **k):
        raise RuntimeError('Ningún proveedor de IA respondió')
    monkeypatch.setattr(ai, '_ai_complete', boom)
    d = client.post('/api/portfolio-ai/ask', json={'question': 'what is diversification?', 'lang': 'en'}).get_json()
    assert d['answer_source'] == 'sin IA' and 'Diversifying' in d['answer']


@pytest.mark.parametrize('body', [
    {'question': ''}, {'question': 'x' * 900}, {'question': 'hola', 'history': 'x'},
    {'question': 'hola', 'portfolio': {'positions': [{'symbol': 'A', 'shares': 1}] * 31}},
    {'question': 'hola', 'portfolio': {'positions': [{'symbol': 'A', 'shares': 'muchas'}]}},
])
def test_ask_validacion(client, body):
    r = client.post('/api/portfolio-ai/ask', json=body)
    assert r.status_code == 400 and r.get_json()['error_en']


def test_nrs_rango():
    for c in pa.universe()[:50]:
        assert 0 <= c['nrs'] <= 100
    assert not math.isnan(pa.universe()[0]['nrs'])


def test_varios_temas_quedan_representados():
    res = run(base(themes=['semis', 'energia']))
    assert res['ok']
    for pf in res['portfolios']:
        secs = {p['sector'] for p in pf['positions']}
        assert 'energia' in secs and secs & {'fabricacion', 'diseno', 'equipos'}
