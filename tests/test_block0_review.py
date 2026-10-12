"""Bloque 0 (docs/BRECHAS_V2.md) — correcciones de la REVISIÓN del guardián de cifras y
del comité (2026-10-12). Cada caso es el reproductor literal del revisor: antes fallaba.
Sin red: la IA se simula."""
import os
import sys
import time
from types import SimpleNamespace as NS

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import ai  # noqa: E402
from core.numbers import (check_numbers, facts_from_text, mark_unsupported, unsupported_in,  # noqa: E402
                          unsupported_money)


class _C:
    def __init__(self, s):
        self.statement_es, self.statement_en, self.reasoning_summary, self.object = s, '', '', ''


class _R:
    def __init__(self, *claims):
        self.claims = [_C(c) for c in claims]
        self.summary_es = self.summary_en = ''


EV = [{'title': 'Perfil', 'excerpt': 'precio 182,40 USD; capitalización 4.450 mil millones USD; margen bruto 75,2 %'}]
SRC = 'NVIDIA: precio 182,40 USD; capitalización 4.450 mil millones USD; margen bruto 75,2 %'


# ── 1) la exención de hipótesis solo cuando el condicional GOBIERNA la cifra ─────────────
@pytest.mark.parametrize('txt', ['Cuando se publicaron los resultados, NVIDIA valía 9 billones de dólares.',
                                 'Si miramos el perfil, la capitalización es de $9T.',
                                 'When results came out, revenue was $999B.'])
def test_check_numbers_no_exime_cifras_tras_palabras_comunes(txt):
    assert check_numbers(_R(txt), EV), txt


@pytest.mark.parametrize('txt', ['When the market closed, NVDA was at $250.',
                                 'Los inversores pueden ver que NVDA cotiza a 250 USD con margen de 90 %.',
                                 'Los inversores podrían ver que NVDA cotiza a 250 USD.',
                                 'Si miramos los datos, NVDA vale 9 billones de dólares.',
                                 'Hoy, cuando escribo esto, NVDA cotiza a 250 USD.',
                                 'Por ejemplo, NVDA cotiza a 250 USD.'])
def test_guardian_general_no_exime_cifras_tras_palabras_comunes(txt):
    assert unsupported_in(txt, SRC), txt


@pytest.mark.parametrize('txt', ['Si cae a 250 USD, compra.', 'Si cae por debajo de 150 USD o el RSI baja de 30, revisa.',
                                 'Podría subir 15 %.', 'NVDA could fall to $150.', 'Cuando supere 200 USD, vende.',
                                 'When it falls below $150, buy.', 'Si cae 10 %, perderías 500 USD.',
                                 'Un stop-loss en 150 USD protege.', 'p. ej. 1.000 USD invertidos', 'NVDA < 150 USD'])
def test_hipotesis_y_umbrales_gobernados_siguen_exentos(txt):
    assert unsupported_in(txt, SRC) == [], txt


# ── 2) el encabezado con escala ya no es cuadrático ──────────────────────────────────────
@pytest.mark.parametrize('n,limit', [(50_000, 0.6), (250_000, 2.0)])
def test_fuente_densa_en_parentesis_es_lineal(n, limit):
    src = ('(' + '1 ') * (n // 3)
    t0 = time.perf_counter()
    unsupported_in('NVDA $5', src)
    assert time.perf_counter() - t0 < limit          # antes: 16 s (50 KB) y 82 s (250 KB)


def test_encabezado_con_escala_sigue_funcionando():
    src = 'Ingresos (USD millones) | 2024: 51.600 | 2025: 63.900\nDeuda en miles de millones: 64,2'
    assert unsupported_in('Ingresos de $63.9B y deuda de $64.2B', src) == []
    assert unsupported_in('Ingresos de $70B', src) == ['$70B']


# ── 3) nada de respaldo cruzado entre tipos ─────────────────────────────────────────────
JSON = ('{"price_usd":182.4,"market_cap_usd_b":4450.1,"employees":36000,"change_pct":-1.85,'
        '"shares_outstanding":24400000000,"rsi":55.3,"as_of_ts":1760313600}')


@pytest.mark.parametrize('txt', ['NVIDIA vale 24,4 mil millones de dólares',              # acciones en circulación
                                 'NVIDIA tuvo flujo de caja de 1,76 mil millones de dólares',  # timestamp
                                 'NVIDIA cotiza a 36.000 dólares',                         # empleados
                                 'NVIDIA cotiza a 55,3 dólares',                           # RSI
                                 'NVIDIA cotiza a $1.85',                                  # change_pct
                                 'Los ingresos crecieron 55,3 %',                          # RSI
                                 'NVDA beta 1.85'])                                        # change_pct
def test_un_dato_de_otro_tipo_no_respalda(txt):
    assert unsupported_in(txt, JSON), txt


def test_los_datos_de_su_tipo_si_respaldan():
    ok = 'NVIDIA cotiza a 182,4 USD, vale 4,45 billones de dólares, cayó 1,85 % y su RSI es 55,3'
    assert unsupported_in(ok, JSON) == []


# ── 4) rangos, símbolos detrás y escalas sin moneda ─────────────────────────────────────
@pytest.mark.parametrize('txt,bad', [('NVDA ronda entre 150 y 160 dólares', '150 (160 dólares)'),
                                     ('NVDA 150-160 USD', '150 (160 USD)'),
                                     ('NVDA: 250 €', '250 €'), ('NVDA cotiza a 200 $', '200 $'),
                                     ('Capitalización de 9,9 billones', '9,9 billones'),
                                     ('Ingresos de 999 mil millones', '999 mil millones'),
                                     ('market cap 4.9 trillion', '4.9 trillion')])
def test_cifras_que_antes_no_se_revisaban(txt, bad):
    assert bad in unsupported_in(txt, SRC), txt


def test_rango_de_porcentajes_revisa_el_primero():
    assert unsupported_in('Crecen 50-94 %', 'crecimiento 94 %') == ['50 (94 %)']
    assert unsupported_in('Crecen 90-94 %', 'crecimiento 90 % a 94 %') == []


def test_formatos_correctos_pasan():
    ok = ('NVDA cotiza entre 178,9 y 182,4 USD; vale 4,45 billones; SAP cierra en 238,40 € y la nube factura '
          '21.300 millones de euros; 2.000 millones de usuarios')
    src = SRC + '; prev_close=178.9 · SAP 238,40 € · nube 21.300 millones de euros'
    assert unsupported_in(ok, src) == []


# ── 5) "~", "unos", "alrededor de" ensanchan la tolerancia ──────────────────────────────
@pytest.mark.parametrize('txt', ['NVDA cotiza alrededor de 180 USD', 'NVDA trades around $180', 'NVDA ~$180',
                                 'AMD vale unos 240 mil millones de dólares', 'AMD is worth roughly $240 billion',
                                 'AMD ~$240B'])
def test_redondeo_aproximado_legitimo_pasa(txt):
    assert unsupported_in(txt, 'NVIDIA: precio 182,40 USD; AMD market_cap_usd_b=243.1') == [], txt


def test_sin_marca_de_aproximacion_sigue_estricto():
    src = 'NVIDIA: precio 182,40 USD; AMD market_cap_usd_b=243.1'
    assert unsupported_in('NVDA cotiza a 180 USD', src) == ['180 USD']
    assert unsupported_in('NVDA cotiza alrededor de 170 USD', src) == ['170 USD']


# ── 6) la marca respeta las exenciones ──────────────────────────────────────────────────
def test_marca_no_toca_la_cifra_exenta_con_el_mismo_texto():
    txt = 'NVDA cotiza a 250 USD y sube 12 %. Si cae a 250 USD, compra.'
    src = 'precio 182,40 USD; change_pct=1.2'
    bad = unsupported_in(txt, src)
    want = ('NVDA cotiza a 250 USD (⚠ cifra no verificada) y sube 12 % (⚠ cifra no verificada). '
            'Si cae a 250 USD, compra.')
    assert mark_unsupported(txt, bad) == want
    assert mark_unsupported(txt, bad, facts=facts_from_text(src)) == want


def test_ai_complete_marca_por_mencion(monkeypatch):
    import core.live_facts as lf
    monkeypatch.setattr(lf, 'live_facts_block', lambda text: '')
    out = 'NVDA cotiza a 250 USD y sube 12 %. Si cae a 250 USD, compra.'
    monkeypatch.setattr(ai, '_ai_complete_raw', lambda *a, **k: (out, 'fake'))
    text, _ = ai._ai_complete('sys', 'precio 182,40 USD; change_pct=1.2', 200, live_facts=False)
    assert text.endswith('Si cae a 250 USD, compra.') and text.count('⚠') == 2


# ── 7) porcentaje: redondeo o truncado, no ±1 unidad ────────────────────────────────────
def test_porcentaje_solo_redondeo_o_truncado():
    src = 'crecimiento ingresos 94 %; vol_anual_pct 48.3; margen 55.8 %'
    for bad in ('crecimiento de 95%', 'crecimiento de 93%', 'volatilidad del 49 %'):
        assert unsupported_in(bad, src), bad
    for ok in ('crecimiento de 94%', 'volatilidad del 48 %', 'volatilidad del 48,3 %', 'margen de 55 %',
               'margen de 56 %', 'margen de 55,8 %'):
        assert unsupported_in(ok, src) == [], ok


def test_contrato_de_solo_dinero_intacto():
    assert unsupported_money('El margen es 95 %', facts_from_text(SRC)) == []


# ── comité: prompt del presidente y objetivo con el que se decide ───────────────────────
def test_prompt_del_presidente_pide_copiar_porcentajes_y_no_derivar():
    from research.committee import CHAIR_SYSTEM
    p = CHAIR_SYSTEM.format(decision='BUY', min_date='2026-10-13', max_date='2027-01-13', schema='{}')
    assert 'porcentaje' in p and 'múltiplo' in p and 'NO calcules cifras nuevas' in p and '72 %' in p


def test_confianzas_del_paquete_respaldan_su_porcentaje():
    from core.numbers import evidence_numbers, unsupported_figures
    from research.committee import build_package, compute_sizing, conviction_by_horizon, mandate_from
    claims = [{'id': 'a', 'agent_type': 'fundamental', 'stance': 'positive', 'horizon': 'LONG_TERM',
               'confidence': 0.72}]
    conv, overall = conviction_by_horizon(claims)
    cb = {'a': NS(agent_type='fundamental', horizon='LONG_TERM', stance='positive',
                  statement_es='El margen bruto de 75 % sostiene la tesis.', statement_en='',
                  reasoning_summary='', falsifiers=[])}
    sizing = compute_sizing('BUY', 37.7, mandate_from({}), equity=None, validated=False)
    _t, items, _r, _c = build_package('NVIDIA', 'NVDA', cb, conv, overall, [], {'ok': False}, {'ok': False},
                                      sizing, 'BUY', 'x', None)
    vals = evidence_numbers(items)
    assert unsupported_figures('La confianza calibrada del analista fundamental es de 72 %.', vals) == []
    assert unsupported_figures('Está a 14 % de su máximo de 52 semanas.', vals) == ['14 %']


def test_decide_usa_el_objetivo_reducido_si_no_esta_validado():
    from research.committee import (_downgrade_reason, compute_sizing, decide, effective_target_weight,
                                    mandate_from)
    m = mandate_from(None)
    assert effective_target_weight(10, m, True) == pytest.approx(0.10)
    tw = effective_target_weight(10, m, False)
    assert tw == pytest.approx(0.05)
    # 6 % con objetivo 5 %: ya NO es ADD (antes: ADD → orden 0 → HOLD "ya en el tope del mandato")
    assert decide(overall=50, has_position=True, current_w=0.06, target_w=tw)[0] == 'HOLD'
    assert decide(overall=50, has_position=True, current_w=0.03, target_w=tw)[0] == 'ADD'
    assert decide(overall=50, has_position=True, current_w=0.065, target_w=tw)[0] == 'TRIM'
    s = compute_sizing('ADD', 10, m, equity=100000.0, current_value=6000, validated=False)
    assert s['notional'] == 0 and 'mitad' in _downgrade_reason(s, 10)[0]


def test_regla_8_de_los_analistas_cubre_todas_las_cifras_y_el_perfil_cita_su_proveedor_real():
    """Pendientes del bloque 0: (1) la regla 8 del prompt de los analistas pedía copiar solo dinero, pero el guardián
    rechaza también %, múltiplos e indicadores → el primer intento ya lo sabe; (2) un perfil de Finnhub citado con una
    URL de Yahoo se contaba como la misma fuente que los estados de Yahoo (L2-08)."""
    import inspect
    from research.agents import base
    from research import context
    rule = base.SYSTEM_TEMPLATE[base.SYSTEM_TEMPLATE.index('8. CIFRAS'):base.SYSTEM_TEMPLATE.index('9. ')]
    assert 'porcentajes' in rule and 'múltiplos' in rule and 'derivadas' in rule
    src = inspect.getsource(context)
    assert "'https://finnhub.io/quote/" in src and "'finnhub' in _src" in src
