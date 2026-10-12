"""Bloque 0 (docs/BRECHAS_V2.md) — guardián de cifras: L4-02, L4-M1, L2-04 y los
5 defectos CONFIRMADOS de la revisión del guardián (regex cuadrática, marca que
parte cifras, monedas no USD, signo perdido, "1.234,56" mal leído).
Sin red: la IA se simula."""
import os
import random
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import ai  # noqa: E402
from core.numbers import (check_numbers, evidence_numbers, mark_unsupported, money_mentions,  # noqa: E402
                          unsupported_figures, unsupported_in, unsupported_money)

SRC = 'Nvidia price 180 USD'


# ── L4-02: el formato que el propio chat exige ──────────────────────────────
@pytest.mark.parametrize('txt', ['cotiza a 233,95 USD (Yahoo, hoy)', '233,95 dólares', 'el precio es 912 USD',
                                 'USD 233,95', 'cotiza a 233.95 dollars', 'US$ 1,2 mil millones',
                                 '5,7 billones de dólares', 'ingresos de 500 USD millones'])
def test_formatos_de_dinero_que_escribe_el_chat_se_detectan(txt):
    assert unsupported_in(txt, SRC), txt


def test_el_mismo_formato_con_la_cifra_correcta_pasa():
    assert unsupported_in('cotiza a 180 USD (Yahoo, hoy)', SRC) == []
    assert unsupported_in('cotiza a 180,00 dólares', SRC) == []
    assert unsupported_in('Apple vale 5,7 billones de dólares', 'market_cap_usd_b=5712.3') == []


# ── revisión #3: monedas distintas del dólar ────────────────────────────────
def test_monedas_locales_se_revisan():
    txt = 'El precio es 912 euros; SAP vale €300.000 millones; Toyota ¥3.000; MXN 4,500 millones; S/ 12,50'
    bad = unsupported_in(txt, 'precio 180')
    assert {'912 euros', '€300.000 millones', '¥3.000', 'MXN 4,500 millones', 'S/ 12,50'} <= set(bad)
    ok = 'SAP cerró en 238,40 euros y vale €300.000 millones'
    assert unsupported_in(ok, 'La acción cierra en 238,40 euros; capitalización 300.000 millones de euros') == []


# ── L2-04: porcentajes, múltiplos, RSI/NRS ──────────────────────────────────
def test_porcentajes_multiplos_e_indicadores_inventados_se_detectan():
    src = 'margen bruto 75 %; RSI(14) 55; volatilidad 48 %; P/E 35.2; "nrs": 62'
    bad = unsupported_in('El margen bruto es 95 % y el RSI 82, P/E 300x, crece 400 %, NRS de 88', src)
    assert set(bad) == {'95 %', 'RSI 82', '300x', '400 %', 'NRS de 88'}
    assert unsupported_in('Margen bruto 75 %, RSI 55, volatilidad 48 %, P/E 35x y NRS 62/100', src) == []


def test_no_se_marcan_fechas_conteos_umbrales_ni_la_pregunta():
    src = 'PREGUNTA: ¿y si invierto 5.000 USD y cae 20 %? price=180'
    txt = ('Desde 2024-10-12 y en 2025, 3 de 4 analistas lo ven bien; si cae por debajo de 150 USD o el RSI baja '
           'de 30, revisa. Con 5.000 USD y una caída de 20 % perderías parte; el VaR al 95 % ayuda; 100 % de tu '
           'dinero no debería estar en una sola acción; podría subir 15 %.')
    assert unsupported_in(txt, src) == []


# ── revisión #4: el signo ──────────────────────────────────────────────────
def test_el_signo_de_los_datos_cuenta():
    src = 'Flujo de caja libre: -12 mil millones · change_pct=-2.35'
    assert unsupported_in('Flujo de caja libre positivo de $12B', src) == ['$12B']
    assert unsupported_in('Broadcom subió 2,35 % hoy', src) == ['2,35 %']
    assert unsupported_in('Flujo de caja libre negativo de $12B; cayó 2,35 %', src) == []


# ── revisión #5: "1.234,56" ─────────────────────────────────────────────────
def test_numeros_en_formato_espanol_con_miles_y_decimales():
    src = 'Precio: 1.234,56 USD'
    assert unsupported_in('La acción cotiza a $1.234,56.', src) == []
    assert unsupported_in('cotiza a $1,234.56', src) == []
    assert unsupported_in('cotiza a 1.234,56 USD', 'price=1234.56') == []
    assert unsupported_in('cotiza a 1.334,56 USD', src) == ['1.334,56 USD']


# ── revisión #2: la marca va en el tramo exacto ─────────────────────────────
def test_la_marca_no_parte_cifras_mas_largas():
    t = 'Ganancia total $200; comisión $20.'
    assert mark_unsupported(t, ['$20']) == 'Ganancia total $200; comisión $20 (⚠ cifra no verificada).'
    t2 = 'Pagó $1 por acción y ahora vale $1,500 millones la empresa.'
    out = mark_unsupported(t2, ['$1'])
    assert '$1,500 millones la empresa' in out and out.startswith('Pagó $1 (⚠ cifra no verificada) por')
    t3 = 'Comisión $20; cap $20.5B.'
    assert mark_unsupported(t3, ['$20']) == 'Comisión $20 (⚠ cifra no verificada); cap $20.5B.'
    assert mark_unsupported(mark_unsupported(t3, ['$20']), ['$20']).count('⚠') == 1     # idempotente


# ── revisión #1: sin backtracking cuadrático ────────────────────────────────
@pytest.mark.parametrize('blob', ['7' * 50000, '1,' * 25000, '9.' * 25000, '7' * 50000 + '%'])
def test_50k_digitos_en_menos_de_medio_segundo(blob):
    t0 = time.perf_counter()
    unsupported_in('Analiza: ' + blob + ' y $180', 'Datos: ' + blob)
    assert time.perf_counter() - t0 < 0.5


def test_ai_complete_con_prompt_de_50k_digitos_no_congela(monkeypatch):
    import core.live_facts as lf
    monkeypatch.setattr(lf, 'live_facts_block', lambda text: '')
    monkeypatch.setattr(ai, '_ai_complete_raw', lambda *a, **k: ('Precio $180.', 'fake'))
    t0 = time.perf_counter()
    ai._ai_complete('sys', 'Analiza: ' + '7' * 50000, 100, live_facts=False)
    assert time.perf_counter() - t0 < 0.5


# ── L4-M1: fuente = datos del mensaje, comparación por tipo y tolerancia ajustada ──
NVDA = ('DATOS EN VIVO: - Nvidia (NVDA, cotiza): capitalización de mercado 4412.6 mil millones USD; precio 181.27 '
        'USD [en vivo, yahoo]\n[1] get_company → {"nrs":62,"live":{"price":181.27,"prev_close":178.9,'
        '"change_pct":1.32,"market_cap_usd_b":4412.6,"pe_trailing":51.3,"week52_high":212.5,"week52_low":86.6},'
        '"degree":48,"top_suppliers":[{"id":"TSMC","w":6},{"id":"SK Hynix","w":6}]}\nPREGUNTA: ¿cómo va Nvidia? '
        'Responde en 1-2 frases, máx. 3 bullets, 80-250 palabras.')


def test_precio_inventado_a_mas_de_2_por_ciento_se_marca():
    rng = random.Random(7)
    real = 181.27
    other = (178.9, 212.5, 86.6)          # precios que SÍ están en los datos (cierre previo, máx./mín. 52 sem.)
    n = flagged = 0
    for _ in range(300):
        off = rng.uniform(0.03, 0.20) * rng.choice((-1, 1))
        p = round(real * (1 + off), 2)
        if any(abs(p - o) / o <= 0.02 for o in other):
            continue
        n += 1
        flagged += bool(unsupported_in(f'Nvidia cotiza a ${p}', NVDA))
    assert n > 250 and flagged == n, (flagged, n)
    assert unsupported_in('Nvidia cotiza a $181.27 (o 181,3 USD)', NVDA) == []


def test_capitalizacion_inventada_fuera_de_10_por_ciento_se_marca():
    rng = random.Random(11)
    caps = [rng.uniform(100, 5000) for _ in range(300)]
    caps = [c for c in caps if abs(c - 4412.6) / 4412.6 > 0.10]
    flagged = sum(bool(unsupported_in(f'Nvidia vale ${c:.0f}B', NVDA)) for c in caps)
    assert flagged == len(caps)
    assert unsupported_in('Nvidia vale $4.4T, unos 4,41 billones de dólares, más de $4T', NVDA) == []


def test_numeros_de_reglas_y_pesos_no_respaldan_precios():
    """Antes: 'máx. 3', '250 palabras', el peso 6 o el grado 48 respaldaban precios de ±15 %."""
    for p in ('$250', '$6.50', '$48', '$3', '$62'):
        assert unsupported_in(f'El precio objetivo es {p}', NVDA), p


def _fake(responses, calls):
    def f(system, prompt, max_tokens, tier='fast', model=None, **kw):
        calls.append((system, prompt))
        return responses.pop(0), 'fake'
    return f


def _patch(monkeypatch, responses, calls):
    import core.live_facts as lf
    monkeypatch.setattr(lf, 'live_facts_block', lambda text: '')
    monkeypatch.setattr(ai, 'CLAUDE', '')
    monkeypatch.setattr(ai, 'AI_ORDER', ['gemini'])
    monkeypatch.setitem(ai._AI_PROVIDERS, 'gemini', (lambda: True, _fake(responses, calls)))


def test_ai_complete_el_ejemplo_del_system_no_respalda_la_cifra(monkeypatch):
    calls = []
    system = 'Cada cifra con su fuente y fecha en la misma frase, p. ej. «233,95 USD (Yahoo, hoy)».'
    _patch(monkeypatch, ['Nvidia cotiza a 233,95 USD (Yahoo, hoy).'] * 2, calls)
    text, _ = ai._ai_complete(system, NVDA, 500)
    assert '233,95 USD (⚠ cifra no verificada)' in text and len(calls) == 2
    assert 'REGLA DE CIFRAS' in calls[0][0] and '233,95 USD' in calls[1][1]


def test_ai_complete_porcentaje_inventado_reintenta_y_corrige(monkeypatch):
    calls = []
    _patch(monkeypatch, ['Nvidia sube 4,8 % hoy.', 'Nvidia sube 1,32 % hoy.'], calls)
    text, _ = ai._ai_complete('Analista', NVDA, 500)
    assert text == 'Nvidia sube 1,32 % hoy.' and len(calls) == 2 and '4,8 %' in calls[1][1]


def test_simulacion_por_agentes_solo_revisa_dinero(monkeypatch):
    """core/sim_agents pide a la IA ESTIMAR impactos %: ahí un % no es una cifra inventada."""
    from core.ai_usage import ai_context
    calls = []
    _patch(monkeypatch, ['{"rationale": "TSMC cae 12 % por el bloqueo"}'], calls)
    with ai_context('simulacion_agentes'):
        text, _ = ai._ai_complete('Motor', 'Escenario: bloqueo de Taiwán', 500)
    assert len(calls) == 1 and '⚠' not in text
    calls2 = []
    _patch(monkeypatch, ['TSMC cae 12 %', 'TSMC cae 12 %'], calls2)
    text, _ = ai._ai_complete('Motor', 'Escenario', 500, verify_numbers='money')
    assert len(calls2) == 1 and '⚠' not in text


def test_cifra_marcada_en_el_historial_no_respalda_nada():
    src = 'Khipu: Apple vale $5.1T (⚠ cifra no verificada).\nprice=254.63, market_cap_usd_b=3781.4'
    assert unsupported_in('Apple vale $5.1T', src) == ['$5.1T']
    assert unsupported_in('Apple vale $3.78T', src) == []


# ── investigación: rechazo estricto también para % e indicadores ────────────
class _C:
    def __init__(self, s):
        self.statement_es, self.statement_en, self.reasoning_summary, self.object = s, '', '', ''


class _R:
    def __init__(self, *claims):
        self.claims = [_C(c) for c in claims]
        self.summary_es = self.summary_en = ''


EV = [{'title': 'Perfil EN VIVO AVGO', 'excerpt': 'price=342.8, change_pct=-2.35, gross_margin=77.1, '
                                                 'operating_margin=40.2, pe_trailing=88.4'},
      {'title': 'Análisis técnico', 'excerpt': 'RSI(14) 41.7 · caída máxima 1 año -31.5 %'}]


def test_check_numbers_rechaza_porcentaje_e_indicador_inventados():
    errs = check_numbers(_R('El margen operativo es 45 % y el RSI 72.'), EV)
    assert errs and '45 %' in errs[0] and 'RSI 72' in errs[0]
    assert check_numbers(_R('Margen operativo 40,2 %, RSI(14) 41,7, P/E 88,4x; cayó 2,35 %.'), EV) == []
    # el contrato viejo de solo-dinero sigue disponible (retiro/ocultamiento de claims guardadas)
    assert unsupported_money('El margen operativo es 45 %', evidence_numbers(EV)) == []
    assert unsupported_figures('El margen operativo es 45 %', evidence_numbers(EV)) == ['45 %']


def test_comite_los_falsadores_son_umbrales_no_hechos():
    from types import SimpleNamespace as NS

    from research.committee import _money_check
    obj = NS(thesis=[NS(thesis_es='Margen operativo de 52 %.', thesis_en='')], key_risks=[], dissent=[],
             falsifiers_es=['Si el margen operativo cae por debajo de 35 %', 'Margen bruto < 70 %'],
             falsifiers_en=['RSI above 80 for two weeks'], chair_note_es='', chair_note_en='', key_conclusions=[],
             summary_es='', summary_en='')
    errs = _money_check(obj, EV)
    assert len(errs) == 1 and '52 %' in errs[0]


def test_compatibilidad_money_mentions_y_evidence_numbers():
    mm = money_mentions('Vale $350B y cotiza a 233,95 USD')
    assert [m[0] for m in mm] == ['$350B', '233,95 USD'] and mm[0][1] == pytest.approx(350.0) and mm[1][1] is None
    vals = evidence_numbers([{'title': '', 'excerpt': 'market_cap_usd_b=1105.2, price=235.4'}])
    assert 235.4 in set(vals)
