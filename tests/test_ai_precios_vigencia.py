"""tests/test_ai_precios_vigencia.py — L3-16 / G5-17 (lote I1): precios de IA con FECHA DE VIGENCIA.

El 1-ene-2027 Gemini 3.8 Flash pasa de 0,75/3,75 a 1,50/7,50 USD por 1M tokens. Antes era un comentario
("actualizar aquí"); ahora core/ai_usage.PRICE_WINDOWS lo aplica solo según la fecha de la LLAMADA:
  · cost_of/price_for/cache_price_for aceptan `at` (fecha de la llamada) y por defecto usan el reloj;
  · record() valora cada llamada al precio de SU día (reloj congelado en 2026-12-31 23:59 y 2027-01-02);
  · AI_PRICES_JSON (env, emergencia) sigue mandando sobre las ventanas;
  · el reporte del panel (💰 Gasto IA) anuncia el cambio programado mientras no haya pasado.
Sin red ni base.
"""
import os
import sys
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def usage(monkeypatch):
    from core import ai_usage
    monkeypatch.delenv('AI_PRICES_JSON', raising=False)
    monkeypatch.delenv('DATABASE_URL', raising=False)
    ai_usage._reset_for_tests()
    yield ai_usage
    ai_usage._reset_for_tests()


def _freeze(monkeypatch, usage, dt):
    monkeypatch.setattr(usage, '_now', lambda: dt)


def test_precio_por_fecha_de_la_llamada(usage):
    assert usage.price_for('gemini', 'gemini-3.8-flash', at='2026-12-31') == (0.75, 3.75)
    assert usage.price_for('gemini', 'gemini-3.8-flash', at='2027-01-01') == (1.5, 7.5)
    assert usage.price_for('gemini', 'gemini-3.8-flash', at=datetime(2027, 1, 2, 9, tzinfo=timezone.utc)) == (1.5, 7.5)
    # 23:30 en Lima del 31-dic = 04:30 UTC del 1-ene → ya es 2027 (UTC manda)
    from datetime import timedelta
    lima = timezone(timedelta(hours=-5))
    assert usage.price_for('gemini', 'gemini-3.8-flash', at=datetime(2026, 12, 31, 23, 30, tzinfo=lima)) == (1.5, 7.5)
    # otros modelos no cambian
    assert usage.price_for('claude', 'claude-sonnet-5-5', at='2027-06-01') == (2.0, 10.0)
    assert usage.price_for('gemini', 'gemini-3.5-flash', at='2027-06-01') == (1.5, 9.0)


def test_cost_of_usa_la_fecha_y_por_defecto_el_reloj(usage, monkeypatch):
    m = 'gemini-3.8-flash'
    assert usage.cost_of('gemini', m, 1_000_000, 1_000_000, at='2026-06-01') == pytest.approx(4.5)
    assert usage.cost_of('gemini', m, 1_000_000, 1_000_000, at='2027-01-02') == pytest.approx(9.0)
    _freeze(monkeypatch, usage, datetime(2027, 1, 2, 12, tzinfo=timezone.utc))
    assert usage.cost_of('gemini', m, 1_000_000, 1_000_000) == pytest.approx(9.0)
    # la caché implícita de Gemini se cobra sobre el precio de entrada del día
    assert usage.cache_price_for('gemini', m) == (0.0, pytest.approx(0.15))
    _freeze(monkeypatch, usage, datetime(2026, 12, 31, 23, 59, tzinfo=timezone.utc))
    assert usage.cost_of('gemini', m, 1_000_000, 1_000_000) == pytest.approx(4.5)


def test_record_valora_cada_llamada_a_su_dia(usage, monkeypatch):
    _freeze(monkeypatch, usage, datetime(2026, 12, 31, 23, 59, tzinfo=timezone.utc))
    usage.record('gemini', 'gemini-3.8-flash', 1_000_000, 0)
    _freeze(monkeypatch, usage, datetime(2027, 1, 2, 10, tzinfo=timezone.utc))
    usage.record('gemini', 'gemini-3.8-flash', 1_000_000, 0)
    costs = sorted(r['cost_usd'] for r in list(usage._RECENT))
    assert costs == [pytest.approx(0.75), pytest.approx(1.5)]


def test_env_sigue_mandando_y_el_panel_anuncia_el_cambio(usage, monkeypatch):
    monkeypatch.setenv('AI_PRICES_JSON', '{"gemini:gemini-3.8-flash": [1, 4]}')
    assert usage.price_for('gemini', 'gemini-3.8-flash', at='2027-03-01') == (1.0, 4.0)
    monkeypatch.delenv('AI_PRICES_JSON')
    _freeze(monkeypatch, usage, datetime(2026, 10, 13, tzinfo=timezone.utc))
    rep = usage.report(days=1)
    ch = [c for c in rep['price_changes'] if c['model'] == 'gemini:gemini-3.8-flash']
    assert ch and ch[0]['from'] == '2027-01-01' and ch[0]['prices'] == [1.5, 7.5]
    assert rep['prices']['gemini:gemini-3.8-flash'] == [0.75, 3.75]
    _freeze(monkeypatch, usage, datetime(2027, 2, 1, tzinfo=timezone.utc))
    rep = usage.report(days=1)
    assert rep['prices']['gemini:gemini-3.8-flash'] == [1.5, 7.5]


def test_ventanas_bien_formadas(usage):
    for k, wins in usage.PRICE_WINDOWS.items():
        assert k in usage.PRICES, f'{k}: una ventana sin fila base en PRICES'
        prev_to = None
        for frm, to, row in wins:
            assert len(frm) == 10 and (to is None or (len(to) == 10 and to >= frm))
            assert len(row) in (2, 4) and all(isinstance(x, (int, float)) and x >= 0 for x in row)
            assert prev_to is None or frm > prev_to
            prev_to = to or '9999-12-31'
