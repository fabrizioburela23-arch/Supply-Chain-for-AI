"""tests/test_ai_usage_cache.py — BRECHAS L4-06: la caché de prompts se cuenta y se cobra APARTE en 💰 Gasto IA.

  · PRICES trae, por modelo, el precio de escribir y de leer la caché (Claude: 1,25× y ~0,1× la entrada; Opus 5.5
    0,05×); sin esos valores, los multiplicadores por proveedor (CACHE_MULT; Gemini: caché implícita, leer ≈ 0,1×);
  · price_for sigue devolviendo (entrada, salida) — nada de lo que ya lo usa cambia;
  · cost_of: los tokens de caché son PARTE de los de entrada y se cobran a su propio precio;
  · record guarda cache_read/cache_write en la fila; el medidor (presupuesto de research) cuenta la entrada a
    "precio lleno equivalente" (no sube por leer de la caché) y además trae el costo y los tokens crudos;
  · AI_PRICES_JSON acepta 2 o 4 valores; el reporte trae los totales de caché por proveedor.
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


@pytest.fixture
def usage(monkeypatch):
    from core import ai_usage
    monkeypatch.delenv('AI_PRICES_JSON', raising=False)
    monkeypatch.setattr(ai_usage, '_ensure_writer', lambda: None)
    ai_usage._reset_for_tests()
    yield ai_usage
    ai_usage._reset_for_tests()


def test_price_for_sigue_siendo_entrada_y_salida(usage):
    assert usage.price_for('claude', 'claude-sonnet-5-5') == (2.0, 10.0)
    assert usage.price_for('claude', 'claude-opus-5-5') == (4.0, 20.0)
    assert usage.price_for('gemini', 'gemini-3.8-flash', at='2026-10-13') == (0.75, 3.75)


def test_precios_de_cache_por_modelo_y_por_proveedor(usage):
    assert usage.cache_price_for('claude', 'claude-sonnet-5-5') == (2.5, 0.2)
    assert usage.cache_price_for('claude', 'claude-opus-5-5') == (5.0, 0.2)          # lectura 0,05×
    assert usage.cache_price_for('claude', 'claude-haiku-4-5') == (1.25, 0.1)
    w, r = usage.cache_price_for('gemini', 'gemini-3.8-flash', at='2026-10-13')      # sin fila propia
    assert w == 0.0 and r == pytest.approx(0.075)
    assert usage.cache_price_for('nvidia', 'meta/llama') == (0.0, 0.0)


def test_cost_of_cobra_la_cache_a_su_precio(usage):
    full = usage.cost_of('claude', 'claude-sonnet-5-5', 1_000_000, 0)
    assert full == pytest.approx(2.0)
    hit = usage.cost_of('claude', 'claude-sonnet-5-5', 1_000_000, 0, cache_read=900_000)
    assert hit == pytest.approx(0.1 * 2.0 + 0.9 * 0.2)
    write = usage.cost_of('claude', 'claude-sonnet-5-5', 1_000_000, 0, cache_write=1_000_000)
    assert write == pytest.approx(2.5)
    assert usage.cost_of('claude', 'claude-sonnet-5-5', 100, 10) == usage.cost_of('claude', 'claude-sonnet-5-5', 100, 10, 0, 0)


def test_record_guarda_la_cache_y_el_medidor_no_infla_el_presupuesto(usage):
    with usage.meter() as acc:
        usage.record('claude', 'claude-sonnet-5-5', 10_000, 500, cache_read=9_000, cache_write=0)
    row = usage._QUEUE[-1]
    assert row['cache_read'] == 9_000 and row['cache_write'] == 0 and row['tokens_in'] == 10_000
    cost = usage.cost_of('claude', 'claude-sonnet-5-5', 10_000, 500, cache_read=9_000)
    assert row['cost_usd'] == pytest.approx(cost)
    assert acc['raw_in'] == 10_000 and acc['cache_read'] == 9_000 and acc['cost_usd'] == pytest.approx(cost)
    # presupuesto de research/llm: estimate_cost(tokens_in, tokens_out) == el costo REAL (con caché)
    from research.llm import estimate_cost
    assert estimate_cost('claude-sonnet-5-5', acc['tokens_in'], acc['tokens_out']) == pytest.approx(cost, rel=1e-3)
    assert acc['tokens_in'] < 10_000


def test_ai_prices_json_acepta_dos_o_cuatro_valores(usage, monkeypatch):
    monkeypatch.setenv('AI_PRICES_JSON', '{"claude-sonnet-5-5": [3, 12, 4, 0.5], "gemini:gemini-3.8-flash": [1, 4]}')
    assert usage.price_for('claude', 'claude-sonnet-5-5') == (3.0, 12.0)
    assert usage.cache_price_for('claude', 'claude-sonnet-5-5') == (4.0, 0.5)
    assert usage.cache_price_for('gemini', 'gemini-3.8-flash') == (0.0, pytest.approx(0.1))


def test_el_reporte_trae_los_totales_de_cache(usage, monkeypatch):
    import ontology.db as odb
    monkeypatch.setattr(odb, 'DATABASE_URL', '')
    usage.record('claude', 'claude-haiku-4-5', 4000, 100, cache_read=3000)
    usage.record('gemini', 'gemini-3.8-flash', 1000, 50, cache_read=0)
    rep = usage.report(days=1)
    assert rep['cache']['claude'] == {'cache_read': 3000, 'cache_write': 0, 'tokens_in': 4000, 'read_pct': 75.0}
    assert rep['prices']['claude-sonnet-5-5'] == [2.0, 10.0]
    assert rep['cache_prices']['claude-sonnet-5-5'] == [2.5, 0.2]
