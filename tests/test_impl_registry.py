"""tests/test_impl_registry.py — INFRA_OPERATIVA §5.2 «Implementaciones retenidas» (paso 24), sin base.

  · cada etiqueta `impl` que el código estampa en un manifiesto (run_checks@1, compute_sizing@1, propagate@1, …) existe
    en core/impls.STAMPS — una decisión nueva nunca cita código que el replay no conoce;
  · cada implementación registrada se importa y su artefacto de gobernanza existe;
  · las salidas DORADAS (tests/golden/impl_*.json, scripts/build_impl_goldens.py) no cambiaron: si cambian, nace @2;
  · la VISTA de un módulo con los números de otro release no toca el módulo vivo ni a otros hilos; el contrafactual
    por hilo (governance.pinned) tampoco.
"""
import os
import re
import sys
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as fh:
        return fh.read()


def test_toda_etiqueta_impl_del_codigo_esta_registrada():
    from core import impls
    files = ('brokerage/service.py', 'core/decision_sites.py', 'core/decisions.py', 'core/governance_flow.py',
             'matrix/api.py', 'core/gates/report.py', 'core/replay.py')
    found = set()
    for f in files:
        src = _read(f)
        for line in src.splitlines():
            if "'impl'" in line or 'impl\']' in line or "extra['impl']" in line or 'setdefault(\'impl\'' in line \
                    or "'committee':" in line or "'sizing':" in line or "'conviction':" in line or "'gates'" in line:
                found |= set(re.findall(r"'([a-z_.\-]+@\d+|committee-v\d+)'", line))
    found.discard('replay@1')                  # la propia auditoría (audit.replay) no es un cálculo que se repita
    assert found >= {'run_checks@1', 'gate_eval@1', 'compute_sizing@1', 'conviction_by_horizon@1', 'record@1',
                     'gov-regression@1', 'propagate@1', 'portfolio_advisor.analyze@1', 'committee-v1'}, found
    missing = sorted(s for s in found if s not in impls.STAMPS)
    assert not missing, missing
    assert impls.missing_for({'impl': {'risk': 'run_checks@9', 'action': 'CrearTesis@1', 'sizing': 'compute_sizing@1'}}) \
        == [{'role': 'risk', 'stamp': 'run_checks@9'}]
    assert impls.missing_for({'impl': {'replay': 'replay@1'}}) == []     # audit.replay es un registro, no «código perdido»


def test_cada_impl_se_importa_y_su_artefacto_existe():
    import importlib

    from core import governance, impls
    arts = governance.load_manifest()['release']['artifacts']
    for key, vers in impls.IMPLS.items():
        for v, i in vers.items():
            mod = importlib.import_module(i.module)
            assert callable(getattr(mod, i.attr)), f'{key}@{v}'
            assert i.artifact is None or i.artifact in arts, (key, i.artifact)
            assert i.es and i.en
    cat = impls.catalog('en')
    assert {c['key'] for c in cat} >= set(impls.GOLDEN_CASES) and all(c['about'] for c in cat)
    assert impls.resolve_stamp('run_checks@1').key == 'broker.run_checks'
    assert impls.resolve_stamp('CrearTesis@1') is None
    try:
        impls.get('kernel.propagate', 9)
        raise AssertionError('debía fallar')
    except LookupError:
        pass


def test_salidas_doradas_sin_cambios():
    sys.path.insert(0, os.path.join(ROOT, 'scripts'))
    import build_impl_goldens as B
    assert B.main(check=True) == 0
    from core import impls
    k = B.compute('kernel.propagate', 1)['cases']
    assert k[0]['sha'] != k[1]['sha']          # 2.0.0 (los socios no transmiten daño) da OTRO resultado que 1.0.0
    assert 'D' in k[0]['output']['impacts']
    assert set(B.CASES) == set(impls.GOLDEN_CASES)


def test_vista_de_modulo_con_otro_release_no_toca_el_vivo():
    from core import impls
    import research.committee as C
    arts = impls.repo_arts()
    alt = {k: dict(v) for k, v in arts.items()}
    alt['policy.committee'] = dict(alt['policy.committee'], params=dict(alt['policy.committee']['params'],
                                                                         unvalidated_factor=0.25))
    live_factor = C.UNVALIDATED_FACTOR
    v0, v1 = impls.module_view('research.committee', arts), impls.module_view('research.committee', alt)
    mandate = {'risk_budget': 0.01, 'max_position': 0.1, 'min_vol': 0.15}
    s0 = v0.compute_sizing('BUY', 30.0, mandate, validated=False)
    s1 = v1.compute_sizing('BUY', 30.0, mandate, validated=False)
    assert s0['unvalidated_factor'] == live_factor and s1['unvalidated_factor'] == 0.25
    assert s1['target_weight_pct'] < s0['target_weight_pct']
    assert C.UNVALIDATED_FACTOR == live_factor                                   # el módulo vivo no cambió
    assert C.compute_sizing('BUY', 30.0, mandate, validated=False)['unvalidated_factor'] == live_factor
    notes = []
    cut = dict(alt, **{'policy.committee': dict(alt['policy.committee'],
                                                params={k: v for k, v in alt['policy.committee']['params'].items()
                                                        if k != 'w0'})})
    impls.module_view('research.committee', cut, notes)
    assert {'module': 'research.committee', 'artifact': 'policy.committee', 'key': 'w0',
            'note': 'key_not_in_version'} in notes
    r = impls.module_view('brokerage.risk', arts)
    impls.view_with(r, trading_enabled=lambda: False)
    import brokerage.risk as R
    assert R.trading_enabled() is True or os.getenv('BROKERAGE_TRADING_ENABLED')            # el vivo intacto
    assert r.trading_enabled() is False


def test_pinned_es_por_hilo():
    from core import governance, impls
    from matrix import engine as E
    arts2 = impls.repo_arts({'kernel.params': '2.0.0'})
    assert E._P('damage_rels', None) is None                                     # 1.0.0 vigente (repo)
    seen = {}
    gate = threading.Event()
    done = threading.Event()

    def other():
        gate.wait(5)
        seen['other'] = E._P('damage_rels', None)
        done.set()
    t = threading.Thread(target=other)
    t.start()
    with impls.under(arts2):
        assert E._P('damage_rels', None) is not None
        assert governance.artifact_semver('kernel.params') == '2.0.0'
        gate.set()
        done.wait(5)
    t.join(5)
    assert seen['other'] is None                                                 # el otro hilo no se enteró
    assert governance.artifact_semver('kernel.params') == '1.0.0'


def test_diff_campo_a_campo():
    from core import impls
    d = impls.diff({'a': 1, 'b': [1, 2], 'c': {'x': 'y'}}, {'a': 1.0, 'b': [1, 3, 4], 'c': {'x': 'z'}})
    paths = {x['path'] for x in d}
    assert paths == {'b.length', 'b[1]', 'c.x'}
    assert impls.diff({'a': None}, {'a': None}) == []


def test_radio_espectral_repetible():
    """ARPACK arrancaba de un vector ALEATORIO: ρ cambiaba en el 6.º decimal entre corridas (un factor disparado no se
    repetía igual). Con v0 fijo, la misma matriz da el mismo ρ siempre."""
    from matrix import engine as E
    ids = [f'N{i}' for i in range(12)]
    idx = {k: i for i, k in enumerate(ids)}
    tri = [(ids[i], ids[i + 1], 'supply', 3.0 + (i % 3)) for i in range(11)] + [('N0', 'N5', 'fab', 2.0)]
    mats, _, _ = E.build_matrices_from_triples(tri, idx, sparse=True)
    fac = [{'id': 'F', 'severity': 4.0, 'members': {'N3': 0.8, 'N7': 0.5}}]
    vals = {E.spectral_radius(mats, fac, idx)['rho'] for _ in range(8)}
    assert len(vals) == 1, vals
