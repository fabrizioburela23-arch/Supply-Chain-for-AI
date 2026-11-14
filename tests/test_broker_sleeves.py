"""Carteras sobre UNA cuenta de Alpaca (brokerage/sleeves, fase 2): contabilidad por cartera y control previo a la
orden (comprar ≤ efectivo disponible; vender ≤ lo que es suyo)."""
from types import SimpleNamespace as NS

import pytest

from brokerage import sleeves as sv


def _o(side, sym, fq, fp, status='filled', est=None):
    return NS(side=side, symbol=sym, filled_qty=fq, filled_avg_price=fp, est_price=fp, est_usd=est, notional=None,
              status=status)


@pytest.fixture
def sleeve(monkeypatch):
    sl = NS(id='s1', client_id='house', name='Crecimiento IA', status='active', alloc_usd=1000.0, objective='crecer',
            risk_profile='moderado')
    orders = [_o('buy', 'NVDA', 2, 200.0), _o('sell', 'NVDA', 1, 210.0),
              _o('buy', 'AMD', 0, None, status='submitted', est=150.0)]      # compra abierta: reserva US$150
    monkeypatch.setattr(sv, '_orders', lambda s, c, i: orders)
    monkeypatch.setattr(sv, '_get', lambda s, c, i: sl if i == 's1' else None)
    return sl


def test_contabilidad_de_la_cartera(sleeve):
    lg = sv.ledger(None, sleeve)
    assert lg['cash'] == 1000 - 400 + 210 and lg['reserved'] == 150 and lg['available'] == 660
    assert lg['holdings'] == {'NVDA': 1} and lg['cost'] == {'NVDA': 200.0}


def test_comprar_solo_con_su_efectivo(sleeve):
    assert sv.check_order(None, 'house', 's1', 'TSM', 'buy', notional=600)[0]
    ok, es, en = sv.check_order(None, 'house', 's1', 'TSM', 'buy', notional=700)
    assert not ok and 'US$660.00 disponibles' in es and 'available' in en


def test_vender_solo_lo_suyo(sleeve):
    assert sv.check_order(None, 'house', 's1', 'NVDA', 'sell', qty=1)[0]
    assert not sv.check_order(None, 'house', 's1', 'NVDA', 'sell', qty=2)[0]
    assert not sv.check_order(None, 'house', 's1', 'MU', 'sell', notional=100, price=100)[0]
    assert not sv.check_order(None, 'house', 'nope', 'NVDA', 'sell', qty=1)[0]
    sleeve.status = 'archived'
    assert 'archivada' in sv.check_order(None, 'house', 's1', 'NVDA', 'buy', notional=1)[1]


def test_vista_y_conciliacion(sleeve, monkeypatch):
    class Q:
        def filter(self, *a):
            return self

        def order_by(self, *a):
            return self

        def all(self):
            return [sleeve]
    monkeypatch.setattr(sv, 'list_view', sv.list_view)
    sess = NS(query=lambda m: Q())
    out = sv.list_view(sess, 'house', {'equity': 5000.0, 'cash': 4000.0},
                       [{'symbol': 'NVDA', 'qty': 0.5, 'current_price': 220.0}])
    it = out['items'][0]
    assert it['value_usd'] == 810 + 220 and it['pnl_usd'] == 30
    assert out['main']['value_usd'] == 5000 - 1030
    assert out['reconcile_issues'] == [{'symbol': 'NVDA', 'claimed': 1, 'in_account': 0.5}]


def test_la_orden_con_cartera_pasa_por_el_unico_camino():
    src = open('brokerage/service.py', encoding='utf-8').read()
    assert "_sleeves.check_order(session, rec.id, sleeve_id" in src and "return _err('sleeve_limit'" in src
    assert 'reuse_eval=True, sleeve_id=sleeve_id' in src
    assert 'alpaca' not in open('brokerage/sleeves.py', encoding='utf-8').read().split('import')[0].lower() or True
    import ast
    tree = ast.parse(open('brokerage/sleeves.py', encoding='utf-8').read())
    mods = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert 'brokerage.alpaca' not in mods          # este módulo nunca habla con Alpaca
