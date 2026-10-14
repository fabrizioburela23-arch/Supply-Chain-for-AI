"""tests/test_scale_tensor_derived.py — E1.3 (docs/expansion/EXPANSION_5K.md): core/hotviews/derived guarda como MÁXIMO
2 generaciones CONTANDO la que se está construyendo (antes, mientras se armaba la 3.ª, seguían vivas las 2 anteriores:
a 5.000 empresas eran 3 tensores densos de ~600 MB). Y la primera ficha de una generación no espera el NRS de todas."""
import os
import sys
import threading

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class _G:
    def __init__(self, gid, ts=None):
        self.id = gid
        if ts is not None:
            self.built_ts = ts


@pytest.fixture()
def D():
    from core.hotviews import derived
    derived.reset()
    yield derived
    derived.reset()


def test_suelta_la_mas_vieja_antes_de_construir(D):
    seen = {}

    def fn(g):
        seen[g.id] = sorted({k[0] for k in D._STORE})          # lo guardado MIENTRAS se arma esta generación
        return {'gen': g.id}
    ev0 = D.stats()['evictions']
    for i, gid in enumerate(('gA', 'gB', 'gC', 'gD')):
        D.get(_G(gid, 100.0 + i), 'probe', fn)
    assert seen['gC'] == ['gB'] and seen['gD'] == ['gC']       # nunca 3: la vieja se soltó ANTES
    assert D._ORDER == ['gC', 'gD'] and D.peek(_G('gB'), 'probe') is None
    assert D.stats()['evictions'] - ev0 == 2


def test_una_generacion_vieja_no_desplaza_a_las_nuevas(D):
    un0 = D.stats()['uncached']
    D.get(_G('g2', 200.0), 'card', lambda g: {'gen': g.id})
    D.get(_G('g3', 300.0), 'card', lambda g: {'gen': g.id})
    v = D.get(_G('g1', 100.0), 'card', lambda g: {'gen': g.id})  # un lector que tomó la referencia vieja
    assert v == {'gen': 'g1'}                                  # se le responde…
    assert D._ORDER == ['g2', 'g3'] and D.peek(_G('g1'), 'card') is None   # …sin guardarla
    assert D.stats()['uncached'] - un0 == 1


def test_quien_espera_recibe_el_valor_aunque_no_se_guarde(D):
    D.get(_G('g2', 200.0), 'card', lambda g: 1)
    D.get(_G('g3', 300.0), 'card', lambda g: 2)
    gate, out = threading.Event(), []

    def slow(g):
        gate.wait(5)
        return 'viejo'
    t1 = threading.Thread(target=lambda: out.append(D.get(_G('g1', 100.0), 'card', slow)))
    t1.start()
    for _ in range(200):
        if ('g1', 'card') in D._BUILDING:
            break
        threading.Event().wait(0.005)
    t2 = threading.Thread(target=lambda: out.append(D.get(_G('g1', 100.0), 'card', lambda g: 'otra')))
    t2.start()
    threading.Event().wait(0.05)
    gate.set()
    t1.join(5)
    t2.join(5)
    assert out == ['viejo', 'viejo']                           # UNA construcción, los dos con el mismo valor


def test_construccion_que_quedo_vieja_mientras_se_armaba_no_queda_guardada(D):
    gate = threading.Event()
    res = []

    def slow(g):
        gate.wait(5)
        return 'A'
    t = threading.Thread(target=lambda: res.append(D.get(_G('gA', 1.0), 'card', slow)))
    t.start()
    for _ in range(200):
        if 'gA' in D._ORDER:
            break
        threading.Event().wait(0.005)
    D.get(_G('gB', 2.0), 'card', lambda g: 'B')
    D.get(_G('gC', 3.0), 'card', lambda g: 'C')               # suelta gA mientras todavía se arma
    gate.set()
    t.join(5)
    assert res == ['A'] and ('gA', 'card') not in D._STORE and D._ORDER == ['gB', 'gC']


def test_primera_ficha_no_espera_el_nrs_de_todas(monkeypatch):
    """La ficha de una empresa calcula SOLO su NRS si el vector de todas no está al día (mismo número)."""
    import core.live_fundamentals as lf
    import ontology.db as odb
    from core.hotviews import builder, derived, registry
    from core.hotviews.views import card
    monkeypatch.setattr(odb, 'ontology_available', lambda: False)
    monkeypatch.setattr(lf, 'live_margin', lambda *_a, **_k: None)
    monkeypatch.setattr(lf, 'version', lambda: 7)
    registry.reset()
    derived.reset()
    try:
        g = builder.build_once()
        cv = card.view(g)
        c = cv.card('TSMC', structure=False)
        assert cv._nrs is None                                  # no armó las 937
        allv = cv.nrs_all()
        assert c['nrs']['value'] == allv['TSMC']['total'] and c['nrs']['fund_version'] == 7
        assert c['nrs']['terms'] == {k: allv['TSMC'][k] for k in ('geo', 'chain', 'market', 'fundamental',
                                                                  'concentration')}
        assert cv.card('TSMC', structure=False)['nrs'] == c['nrs']
        sha = cv.content_sha                                    # la huella, a pedido y estable
        assert len(sha) == 64 and cv.content_sha == sha and card.status(cv)['content_sha'] == sha
    finally:
        registry.reset()
        derived.reset()
