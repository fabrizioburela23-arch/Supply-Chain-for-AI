"""
tests/test_company_data.py — Dossier para TODAS las empresas + info en vivo
(core/company_data.py y las rutas /api/findossier, /api/dossier,
/api/company/live). SIN red: todo HTTP se reemplaza con monkeypatch (el
sandbox no alcanza Yahoo). Lo que se blinda:
  · Yahoo fundamentals-timeseries → estructura normalizada en USD (JPY→USD,
    FCF = OCF + CapEx cuando falta el reportado).
  · Yahoo quoteSummary → perfil en vivo (márgenes en %, GBp = peniques).
  · Orden de la cascada (FMP vacío → Yahoo; AV solo EE.UU. y último).
  · Las rutas conservan EXACTAMENTE las claves/unidades que consume el cliente.
  · /api/dossier NUNCA sintético; sin datos → 200 {available:false}.
"""
import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('FINNHUB_KEY', '')
os.environ.setdefault('FMP_KEY', '')
os.environ.setdefault('ANTHROPIC_KEY', '')
os.environ.setdefault('AV_KEY', '')
os.environ.setdefault('MARKETSTACK_KEY', '')

import core.quotes as q  # noqa: E402
import core.company_data as cd  # noqa: E402

_real_yahoo_get = cd._yahoo_get     # la REAL, capturada antes de que el fixture la reemplace

JPY = 0.0067
GBP = 1.27
RATES = {'USD': 1.0, 'JPY': JPY, 'GBP': GBP, 'TWD': 0.031}


def fake_fx(cur):
    return RATES.get(cur)


# ── Payloads realistas ───────────────────────────────────────────────────────

def _e(date, raw, cur='JPY'):
    return {'dataId': 20100, 'asOfDate': date, 'periodType': '12M', 'currencyCode': cur,
            'reportedValue': {'raw': raw, 'fmt': f'{raw:,.0f}'}}


def _item(typ, entries, sym='7203.T'):
    return {'meta': {'symbol': [sym], 'type': [typ]},
            'timestamp': [1648684800, 1680220800, 1711843200, 1743379200][:len(entries)],
            typ: entries}


def toyota_timeseries():
    """Forma real de ws/fundamentals-timeseries (Toyota, cierre fiscal 31-mar,
    en yenes). 2024 y 2025 SIN annualFreeCashFlow → se calcula OCF + CapEx."""
    d = ['2022-03-31', '2023-03-31', '2024-03-31', '2025-03-31']
    return {'timeseries': {'error': None, 'result': [
        _item('annualTotalRevenue', [_e(d[0], 31.38e12), _e(d[1], 37.15e12),
                                     _e(d[2], 45.10e12), _e(d[3], 48.04e12)]),
        _item('annualGrossProfit', [_e(d[0], 5.8e12), _e(d[1], 6.2e12),
                                    _e(d[2], 9.0e12), _e(d[3], 9.6e12)]),
        _item('annualNetIncome', [_e(d[0], 2.85e12), _e(d[1], 2.45e12),
                                  _e(d[2], 4.94e12), _e(d[3], 4.77e12)]),
        # Yahoo rellena con null los años sin dato
        _item('annualFreeCashFlow', [_e(d[0], 0.5e12), _e(d[1], 0.4e12), None, None]),
        _item('annualOperatingCashFlow', [_e(d[0], 3.72e12), _e(d[1], 2.96e12),
                                          _e(d[2], 4.21e12), _e(d[3], 3.69e12)]),
        _item('annualCapitalExpenditure', [_e(d[0], -3.2e12), _e(d[1], -2.5e12),
                                           _e(d[2], -2.0e12), _e(d[3], -2.2e12)]),
        _item('annualTotalDebt', [_e(d[0], 27.0e12), _e(d[1], 28.0e12),
                                  _e(d[2], 34.0e12), _e(d[3], 38.0e12)]),
        _item('annualCashAndCashEquivalents', [_e(d[0], 6.1e12), _e(d[1], 7.5e12),
                                               _e(d[2], 9.4e12), _e(d[3], 8.9e12)]),
        _item('annualStockholdersEquity', [_e(d[0], 28.3e12), _e(d[1], 30.0e12),
                                           _e(d[2], 35.2e12), _e(d[3], 36.9e12)]),
        _item('annualDilutedAverageShares', [
            {'asOfDate': d[0], 'periodType': '12M', 'reportedValue': {'raw': 13.95e9}},
            {'asOfDate': d[1], 'periodType': '12M', 'reportedValue': {'raw': 13.73e9}},
            {'asOfDate': d[2], 'periodType': '12M', 'reportedValue': {'raw': 13.48e9}},
            {'asOfDate': d[3], 'periodType': '12M', 'reportedValue': {'raw': 13.22e9}}]),
        _item('annualEBITDA', [_e(d[0], 6.0e12), _e(d[1], 5.8e12),
                               _e(d[2], 8.5e12), _e(d[3], 8.9e12)]),
        _item('annualDilutedEPS', [_e(d[0], 204.5), _e(d[1], 179.5),
                                   _e(d[2], 365.9), _e(d[3], 359.6)]),
        _item('annualOperatingIncome', [_e(d[0], 3.0e12), _e(d[1], 2.7e12),
                                        _e(d[2], 5.35e12), _e(d[3], 4.8e12)]),
        _item('annualInvestedCapital', [_e(d[0], 50e12), _e(d[1], 55e12),
                                        _e(d[2], 60e12), _e(d[3], 66e12)]),
        _item('annualTaxRateForCalcs', [
            {'asOfDate': d[0], 'reportedValue': {'raw': 0.27}},
            {'asOfDate': d[1], 'reportedValue': {'raw': 0.28}},
            {'asOfDate': d[2], 'reportedValue': {'raw': 0.26}},
            {'asOfDate': d[3], 'reportedValue': {'raw': 0.25}}]),
        # tipo pedido pero sin datos (Yahoo lo devuelve solo con meta)
        {'meta': {'symbol': ['7203.T'], 'type': ['annualOrdinarySharesNumber']}},
    ]}}


def mizuho_quote_summary():
    return {'quoteSummary': {'error': None, 'result': [{
        'price': {'maxAge': 1, 'symbol': '8411.T', 'currency': 'JPY',
                  'longName': 'Mizuho Financial Group, Inc.', 'exchangeName': 'Tokyo',
                  'marketState': 'CLOSED', 'regularMarketTime': 1759036800,
                  'regularMarketPrice': {'raw': 4012.0, 'fmt': '4,012.00'},
                  'regularMarketPreviousClose': {'raw': 3963.0, 'fmt': '3,963.00'},
                  'regularMarketChangePercent': {'raw': 0.012364, 'fmt': '1.24%'},
                  'marketCap': {'raw': 10_100_000_000_000, 'fmt': '10.1T'}},
        'summaryProfile': {'country': 'Japan', 'website': 'https://www.mizuhogroup.com',
                           'industry': 'Banks - Regional', 'sector': 'Financial Services',
                           'fullTimeEmployees': 52307,
                           'longBusinessSummary': 'Mizuho Financial Group, Inc. provides banking services.'},
        'financialData': {'financialCurrency': 'JPY',
                          'totalRevenue': {'raw': 3_300_000_000_000, 'fmt': '3.3T'},
                          'grossMargins': {'raw': 0.0, 'fmt': '0.00%'}, 'grossProfits': {},
                          'operatingMargins': {'raw': 0.3412, 'fmt': '34.12%'},
                          'profitMargins': {'raw': 0.2605, 'fmt': '26.05%'},
                          'revenueGrowth': {'raw': 0.081, 'fmt': '8.10%'},
                          'targetMeanPrice': {'raw': 4300.5, 'fmt': '4,300.50'},
                          'recommendationKey': 'buy'},
        'defaultKeyStatistics': {'forwardPE': {'raw': 11.2, 'fmt': '11.20'}},
        'summaryDetail': {'currency': 'JPY', 'trailingPE': {'raw': 12.9, 'fmt': '12.90'},
                          'dividendYield': {'raw': 0.0302, 'fmt': '3.02%'},
                          'fiftyTwoWeekLow': {'raw': 2800.0}, 'fiftyTwoWeekHigh': {'raw': 4200.0}},
    }]}}


def fmp_payloads():
    """FMP /stable/ (USD) — 3 años completos."""
    years = ['2022', '2023', '2024']
    inc = [{'date': f'{y}-12-31', 'fiscalYear': y, 'reportedCurrency': 'USD',
            'revenue': 100e9 * (i + 1), 'grossProfit': 60e9 * (i + 1), 'netIncome': 20e9 * (i + 1),
            'ebitda': 30e9 * (i + 1), 'epsDiluted': 2.0 + i, 'weightedAverageShsOutDil': 10e9 + i * 1e8,
            'operatingIncome': 25e9} for i, y in enumerate(years)][::-1]   # FMP: más nuevo primero
    cfs = [{'date': f'{y}-12-31', 'fiscalYear': y, 'freeCashFlow': 15e9 * (i + 1),
            'operatingCashFlow': 25e9, 'capitalExpenditure': -10e9} for i, y in enumerate(years)]
    bal = [{'date': f'{y}-12-31', 'fiscalYear': y, 'totalDebt': 50e9, 'cashAndCashEquivalents': 30e9,
            'totalStockholdersEquity': 200e9} for y in years]
    km = [{'date': f'{y}-12-31', 'fiscalYear': y, 'evToSales': 8.123, 'returnOnEquity': 0.15,
           'returnOnInvestedCapital': 0.12} for y in years]
    return {'income-statement': inc, 'cash-flow-statement': cfs,
            'balance-sheet-statement': bal, 'key-metrics': km}


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """Por defecto TODA llamada de red falla; cada test habilita lo suyo."""
    monkeypatch.setattr(q, '_fx_to_usd', fake_fx)
    monkeypatch.setattr(cd, '_get_json', lambda *a, **k: (None, 'upstream 404'))
    monkeypatch.setattr(cd, '_yahoo_get', lambda *a, **k: (None, 'upstream 404'))
    monkeypatch.setattr(cd, '_sleep', lambda s: None)
    cd._clear_caches()
    yield
    cd._clear_caches()


# ════════════════════════════════════════════════════════════════════════════
# Transformaciones puras
# ════════════════════════════════════════════════════════════════════════════

def test_yahoo_timeseries_jpy_a_usd_y_fcf_calculado():
    r = cd.yahoo_timeseries_to_annual(toyota_timeseries(), fx=fake_fx)
    assert r['available'] is True and r['source'] == 'yahoo'
    assert r['currency'] == 'JPY'                       # moneda ORIGINAL del reporte
    assert r['years'] == ['2022', '2023', '2024', '2025']   # ascendente
    assert r['revenue'][-1] == pytest.approx(48.04e12 * JPY)   # USD crudos
    assert r['net_income'][0] == pytest.approx(2.85e12 * JPY)
    # FCF reportado donde existe; OCF + CapEx (CapEx negativo) donde falta
    assert r['fcf'][0] == pytest.approx(0.5e12 * JPY)
    assert r['fcf'][2] == pytest.approx((4.21e12 - 2.0e12) * JPY)
    assert r['fcf'][3] == pytest.approx((3.69e12 - 2.2e12) * JPY)
    # acciones: crudas, sin convertir; EPS sí es dinero → USD
    assert r['shares'][-1] == 13.22e9
    assert r['eps'][-1] == pytest.approx(359.6 * JPY)
    # ROE = utilidad / patrimonio (fracción); ROIC = EBIT·(1−t)/capital invertido
    assert r['roe'][-1] == pytest.approx(4.77 / 36.9)
    assert r['roic'][-1] == pytest.approx(4.8e12 * 0.75 / 66e12)
    # Yahoo no da EV/Ventas anual → None (no se inventa)
    assert r['ev_to_sales'] == [None, None, None, None]
    assert len(r['total_debt']) == len(r['years']) == len(r['cash']) == len(r['ebitda'])


def test_yahoo_timeseries_sin_tipo_de_cambio_no_inventa():
    r = cd.yahoo_timeseries_to_annual(toyota_timeseries(), fx=lambda c: None if c == 'JPY' else 1.0)
    assert r['available'] is False
    assert 'JPY' in r['reason'] and r['revenue'] == []


def test_yahoo_timeseries_vacio_y_anio_duplicado():
    assert cd.yahoo_timeseries_to_annual({'timeseries': {'result': []}}, fx=fake_fx)['available'] is False
    assert cd.yahoo_timeseries_to_annual(None, fx=fake_fx)['available'] is False
    # cambio de cierre fiscal: dos entradas en 2023 → gana la más reciente
    p = {'timeseries': {'result': [_item('annualTotalRevenue', [
        _e('2023-03-31', 10e9, 'USD'), _e('2023-12-31', 12e9, 'USD'), _e('2024-12-31', 15e9, 'USD')], 'X')]}}
    r = cd.yahoo_timeseries_to_annual(p, fx=fake_fx)
    assert r['years'] == ['2023', '2024'] and r['revenue'] == [12e9, 15e9]


def test_quote_summary_a_perfil_en_vivo():
    p = cd.yahoo_quote_summary_to_profile(mizuho_quote_summary(), fx=fake_fx, symbol='8411.T')
    assert p['available'] is True and p['source'] == 'yahoo'
    assert p['symbol'] == '8411.T' and p['currency'] == 'JPY'
    assert p['price'] == 4012.0 and p['prev_close'] == 3963.0           # moneda LOCAL
    assert p['change_pct'] == pytest.approx(1.24, abs=0.01)             # en %
    assert p['price_usd'] == pytest.approx(4012.0 * JPY, abs=1e-3)
    assert p['market_cap_usd_b'] == pytest.approx(10.1e12 * JPY / 1e9, abs=1e-2)
    assert p['revenue_ttm_usd_b'] == pytest.approx(3.3e12 * JPY / 1e9, abs=1e-2)
    assert p['employees'] == 52307 and isinstance(p['employees'], int)
    assert p['sector'] == 'Financial Services' and p['country'] == 'Japan'
    assert p['summary'].startswith('Mizuho')
    assert p['gross_margin'] is None          # banco: Yahoo pone 0, no es margen real
    assert p['operating_margin'] == 34.12 and p['profit_margin'] == 26.05
    # Yahoo revenueGrowth = ÚLTIMO TRIMESTRE interanual, NO el TTM: va en su
    # propia clave; revenue_growth (TTM real) queda vacío en vez de mal rotulado
    assert p['revenue_growth_q'] == 8.1 and p['revenue_growth'] is None
    assert p['dividend_yield'] == 3.02
    assert p['pe_trailing'] == 12.9 and p['pe_forward'] == 11.2
    assert p['week52_low'] == 2800.0 and p['week52_high'] == 4200.0
    assert p['target_mean'] == 4300.5 and p['recommendation'] == 'buy'
    # TODAS las claves del contrato presentes
    for k in ('available', 'source', 'as_of', 'symbol', 'currency', 'price', 'prev_close',
              'change_pct', 'price_usd', 'market_cap_usd_b', 'employees', 'sector', 'industry',
              'country', 'website', 'summary', 'revenue_ttm_usd_b', 'gross_margin',
              'operating_margin', 'profit_margin', 'revenue_growth', 'pe_trailing', 'pe_forward',
              'dividend_yield', 'week52_low', 'week52_high', 'target_mean', 'recommendation', 'reason'):
        assert k in p, k


def test_quote_summary_peniques_de_londres():
    """LSE cotiza en GBp (peniques): el precio en USD va /100, la
    capitalización ya viene en libras."""
    payload = {'quoteSummary': {'result': [{'price': {
        'symbol': 'VOD.L', 'currency': 'GBp', 'regularMarketPrice': {'raw': 72.5},
        'regularMarketPreviousClose': {'raw': 72.0}, 'marketCap': {'raw': 19e9}}}]}}
    p = cd.yahoo_quote_summary_to_profile(payload, fx=fake_fx)
    assert p['price_usd'] == pytest.approx(72.5 * 0.01 * GBP, abs=1e-4)
    assert p['market_cap_usd_b'] == pytest.approx(19 * GBP, abs=1e-2)


def test_quote_summary_sin_resultado():
    bad = {'quoteSummary': {'result': None, 'error': {'code': 'Not Found'}}}
    assert cd.yahoo_quote_summary_to_profile(bad, fx=fake_fx) is None


def test_fmp_stable_a_normalizado():
    f = fmp_payloads()
    r = cd.fmp_statements_to_annual(f['income-statement'], f['cash-flow-statement'],
                                    f['balance-sheet-statement'], f['key-metrics'], fx=fake_fx)
    assert r['source'] == 'fmp' and r['years'] == ['2022', '2023', '2024']
    assert r['revenue'] == [100e9, 200e9, 300e9]
    assert r['ev_to_sales'] == [8.123] * 3 and r['roe'] == [0.15] * 3
    assert r['shares'][0] == 10e9


# ════════════════════════════════════════════════════════════════════════════
# Cascada
# ════════════════════════════════════════════════════════════════════════════

def test_cascada_fmp_vacio_cae_a_yahoo(monkeypatch):
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(('fmp' if 'financialmodelingprep' in url else url, params and params.get('symbol')))
        return None, 'upstream 402'          # plan de producción: 402 en statements

    def fake_yahoo(url, params=None, timeout=None):
        calls.append(('yahoo', params and params.get('symbol')))
        assert 'fundamentals-timeseries' in url
        assert 'annualFreeCashFlow' in params['type'] and 'annualTotalRevenue' in params['type']
        assert params['period1'] == 1483228800
        return toyota_timeseries(), None

    monkeypatch.setattr(cd, '_get_json', fake_get)
    monkeypatch.setattr(cd, '_yahoo_get', fake_yahoo)
    r = cd.get_annual_financials('7203.T', fmp_key='k', av_key='avk', use_cache=False)
    assert r['available'] is True and r['source'] == 'yahoo'
    assert [c[0] for c in calls] == ['fmp', 'yahoo']   # FMP primero; sin income no pide más
    assert r['tried'] == ['fmp', 'yahoo']              # AV no se gasta: Yahoo ya dio datos


def test_cascada_fmp_completo_no_llama_a_yahoo(monkeypatch):
    f = fmp_payloads()

    def fake_get(url, params=None, timeout=None):
        return f[url.rsplit('/', 1)[-1]], None

    def boom(*a, **k):
        raise AssertionError('Yahoo no debía consultarse')

    monkeypatch.setattr(cd, '_get_json', fake_get)
    monkeypatch.setattr(cd, '_yahoo_get', boom)
    r = cd.get_annual_financials('AAA', fmp_key='k', av_key='', use_cache=False)
    assert r['source'] == 'fmp' and r['tried'] == ['fmp']


def _fin(source, **fields):
    """Resultado normalizado mínimo de una fuente (2 años) para probar la cascada."""
    base = {'available': True, 'source': source, 'currency': 'USD', 'reason': None,
            'reason_en': None, 'years': ['2023', '2024']}
    for f in cd._FIELDS:
        base[f] = fields.get(f, [None, None])
    return base


def test_cascada_prefiere_fuente_completa_aunque_tenga_menos_campos(monkeypatch):
    """FMP parcial (cash-flow en 402 → sin FCF, 9 campos) vs Yahoo COMPLETO
    con menos campos (banco: sin gross_profit ni EBITDA). Gana Yahoo: la
    completitud va primero; si no, el FCF desaparece del Dossier."""
    v = [1e9, 2e9]
    fmp_partial = _fin('fmp', revenue=v, gross_profit=v, net_income=v, total_debt=v, cash=v,
                       equity=v, shares=v, ebitda=v, eps=[1.0, 2.0])            # score 9, sin FCF
    yahoo_full = _fin('yahoo', revenue=v, net_income=v, fcf=v, total_debt=v, cash=v,
                      equity=v, shares=v, eps=[1.0, 2.0])                       # score 8, completo
    assert cd._score(fmp_partial) > cd._score(yahoo_full)
    monkeypatch.setattr(cd, '_fetch_fmp', lambda t, k: (copy.deepcopy(fmp_partial), None))
    monkeypatch.setattr(cd, '_fetch_yahoo_fin', lambda t: (copy.deepcopy(yahoo_full), None))
    r = cd.get_annual_financials('AAA', fmp_key='k', av_key='', use_cache=True)
    assert r['source'] == 'yahoo' and r['fcf'] == v and r['tried'] == ['fmp', 'yahoo']
    assert cd._FIN_CACHE['AAA'][2] == cd.FIN_TTL_OK                    # completo → 12 h
    # empate de puntaje: también gana la completa
    yahoo_tie = _fin('yahoo', revenue=v, net_income=v, fcf=v, total_debt=v, cash=v,
                     equity=v, shares=v, eps=[1.0, 2.0], ebitda=v)             # score 9, completo
    monkeypatch.setattr(cd, '_fetch_yahoo_fin', lambda t: (copy.deepcopy(yahoo_tie), None))
    r2 = cd.get_annual_financials('BBB', fmp_key='k', av_key='', use_cache=False)
    assert r2['source'] == 'yahoo' and r2['fcf'] == v
    # ambas parciales: se queda con la que más datos trajo
    yahoo_partial = _fin('yahoo', revenue=v, equity=v)
    monkeypatch.setattr(cd, '_fetch_yahoo_fin', lambda t: (copy.deepcopy(yahoo_partial), None))
    r3 = cd.get_annual_financials('CCC', fmp_key='k', av_key='', use_cache=False)
    assert r3['source'] == 'fmp'


def test_alpha_vantage_ultimo_recurso_solo_eeuu(monkeypatch):
    av = {
        'INCOME_STATEMENT': {'annualReports': [
            {'fiscalDateEnding': '2024-12-31', 'reportedCurrency': 'USD', 'totalRevenue': '5000000000',
             'grossProfit': '2000000000', 'netIncome': '500000000', 'ebitda': 'None'},
            {'fiscalDateEnding': '2023-12-31', 'reportedCurrency': 'USD', 'totalRevenue': '4000000000',
             'grossProfit': '1500000000', 'netIncome': '400000000', 'ebitda': 'None'}]},
        'BALANCE_SHEET': {'annualReports': [
            {'fiscalDateEnding': '2024-12-31', 'totalShareholderEquity': '2500000000',
             'shortLongTermDebtTotal': '1000000000', 'commonStockSharesOutstanding': '100000000'},
            {'fiscalDateEnding': '2023-12-31', 'totalShareholderEquity': '2000000000',
             'shortLongTermDebtTotal': '900000000', 'commonStockSharesOutstanding': '98000000'}]},
        'CASH_FLOW': {'annualReports': [
            {'fiscalDateEnding': '2024-12-31', 'operatingCashflow': '800000000', 'capitalExpenditures': '300000000'},
            {'fiscalDateEnding': '2023-12-31', 'operatingCashflow': '700000000', 'capitalExpenditures': '250000000'}]},
    }
    seen = []

    def fake_get(url, params=None, timeout=None):
        if 'alphavantage' in url:
            seen.append(params['function'])
            return av[params['function']], None
        return None, 'upstream 404'

    monkeypatch.setattr(cd, '_get_json', fake_get)
    r = cd.get_annual_financials('AAA', fmp_key='', av_key='avk', use_cache=False)
    assert r['source'] == 'alphavantage' and r['years'] == ['2023', '2024']
    assert r['fcf'] == [450e6, 500e6]                  # OCF − capex (AV lo da positivo)
    assert r['ebitda'] == [None, None]                 # 'None' de AV → None
    assert seen == ['INCOME_STATEMENT', 'BALANCE_SHEET', 'CASH_FLOW']
    # bolsa no-EE.UU.: AV ni se consulta (no la cubre y el cupo es de 25/día)
    seen.clear()
    r2 = cd.get_annual_financials('7203.T', fmp_key='', av_key='avk', use_cache=False)
    assert r2['available'] is False and seen == []
    assert 'solo cubre EE.UU.' in r2['reason'] and 'US only' in r2['reason_en']


def test_cache_exito_12h_fallo_max_10min(monkeypatch):
    n = {'y': 0}

    def fake_yahoo(url, params=None, timeout=None):
        n['y'] += 1
        return toyota_timeseries(), None

    monkeypatch.setattr(cd, '_yahoo_get', fake_yahoo)
    cd.get_annual_financials('7203.T', fmp_key='', av_key='')
    cd.get_annual_financials('7203.T', fmp_key='', av_key='')
    assert n['y'] == 1                                  # segunda vez desde caché
    assert cd._FIN_CACHE['7203.T'][2] == 12 * 3600
    # fallo → caché corta (≤ 10 min)
    monkeypatch.setattr(cd, '_yahoo_get', lambda *a, **k: (None, 'timeout'))
    r = cd.get_annual_financials('ZZZZ.T', fmp_key='', av_key='')
    assert r['available'] is False
    assert cd._FIN_CACHE['ZZZZ.T'][2] <= 600


def test_yahoo_get_renueva_crumb_una_vez(monkeypatch):
    """Crumb caducada (401) → se fuerza sesión nueva y se reintenta UNA vez."""
    class Resp:
        def __init__(self, code, body=None):
            self.status_code, self._b = code, body

        def json(self):
            return self._b

    class Sess:
        def __init__(self):
            self.calls = []

        def get(self, url, params=None, timeout=None):
            self.calls.append(params.get('crumb'))
            return Resp(401) if len(self.calls) == 1 else Resp(200, {'ok': True})

    s = Sess()
    monkeypatch.setattr(q, '_yahoo_session', lambda: (s, 'CRUMB'))
    monkeypatch.setitem(q._Y_SESS, 'ts', 12345)
    # la función REAL (el fixture autouse la reemplazó en el módulo)
    data, err = _real_yahoo_get('https://query2.finance.yahoo.com/x', {'a': 1})
    assert data == {'ok': True} and err is None
    assert s.calls == ['CRUMB', 'CRUMB'] and q._Y_SESS['ts'] == 0



# ════════════════════════════════════════════════════════════════════════════
# Perfil en vivo — cascada
# ════════════════════════════════════════════════════════════════════════════

def test_perfil_en_vivo_finnhub_si_yahoo_falla_en_eeuu(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        if url.endswith('stock/profile2'):
            return {'ticker': 'AAA', 'name': 'AAA Corp', 'currency': 'USD', 'country': 'US',
                    'marketCapitalization': 2500000, 'finnhubIndustry': 'Semiconductors',
                    'weburl': 'https://aaa.example'}, None
        if url.endswith('/quote'):
            return {'c': 110.0, 'pc': 100.0, 'dp': 10.0, 't': 1759036800}, None
        if url.endswith('stock/metric'):
            return {'metric': {'grossMarginTTM': 75.1, 'netProfitMarginTTM': 55.2,
                               '52WeekHigh': 120, '52WeekLow': 80, 'peTTM': 40.5}}, None
        return None, 'upstream 404'

    monkeypatch.setattr(cd, '_get_json', fake_get)
    p = cd.get_live_profile('AAA', finnhub_key='k', use_cache=False)
    assert p['available'] is True and p['source'] == 'finnhub'
    assert p['price'] == 110.0 and p['change_pct'] == 10.0
    assert p['market_cap_usd_b'] == 2500.0                 # millones → miles de millones
    assert p['gross_margin'] == 75.1 and p['profit_margin'] == 55.2
    assert p['week52_high'] == 120 and p['employees'] is None   # Finnhub free no lo da


def test_perfil_finnhub_adr_cotiza_en_usd_no_en_moneda_de_reporte(monkeypatch):
    """ADR (TSM): profile2.currency es la moneda de los REPORTES ('TWD'), pero
    /quote da el precio del listado de EE.UU. en USD. El precio NO se rotula
    en TWD, price_usd NO se escala por el TWD, y la capitalización (unidad
    no confirmada para reportes en otra moneda) no se adivina."""
    def fake_get(url, params=None, timeout=None):
        if url.endswith('stock/profile2'):
            return {'ticker': 'TSM', 'name': 'Taiwan Semiconductor', 'currency': 'TWD',
                    'country': 'TW', 'marketCapitalization': 48_000_000}, None
        if url.endswith('/quote'):
            return {'c': 180.5, 'pc': 178.0, 'dp': 1.4, 't': 1759036800}, None
        if url.endswith('stock/metric'):
            return {'metric': {'52WeekHigh': 210, '52WeekLow': 130,
                               'revenueGrowthTTMYoy': 33.9}}, None
        return None, 'upstream 404'

    monkeypatch.setattr(cd, '_get_json', fake_get)
    p = cd.get_live_profile('TSM', finnhub_key='k', use_cache=False)
    assert p['available'] is True and p['source'] == 'finnhub'
    assert p['currency'] == 'USD' and p['price'] == 180.5
    assert p['price_usd'] == 180.5                          # NO 180.5 × 0.031
    assert p['market_cap_usd_b'] is None                    # nada adivinado
    assert p['week52_high'] == 210
    assert p['revenue_growth'] == 33.9                      # Finnhub SÍ da el TTM interanual
    # la función pura, directo: mismo resultado aunque el fx conozca el TWD
    p2 = cd.finnhub_to_profile({'currency': 'TWD', 'marketCapitalization': 48_000_000},
                               {'c': 180.5, 'pc': 178.0}, fx=fake_fx, symbol='TSM')
    assert p2['currency'] == 'USD' and p2['price_usd'] == 180.5 and p2['market_cap_usd_b'] is None


def test_razones_en_lenguaje_llano_y_bilingues():
    """Los códigos crudos ('upstream 404', 'timeout', 'ConnectionError'…) NO
    llegan al usuario: cada uno se traduce a una frase llana en es y en."""
    raw = ('upstream 404', 'upstream 429', 'upstream 402', 'upstream 403', 'upstream 500',
           'upstream 503', 'upstream 418', 'timeout', 'invalid json', 'crumb', 'ConnectionError',
           'SSLError', 'RuntimeError',
           'Thank you for using Alpha Vantage! Our standard API rate limit is 25 requests per day.',
           'Invalid API KEY. Feel free to create a Free API Key.',
           'Premium Query Parameter: this endpoint is not available under your current subscription',
           '')
    for err in raw:
        es, en = cd._explain('yahoo', err)
        assert es.startswith('Yahoo Finance: ') and en.startswith('Yahoo Finance: ')
        assert es != en, err                                  # de verdad bilingüe
        for bad in ('upstream', 'timeout', 'json', 'crumb', 'Error', 'Alpha Vantage!', 'Premium'):
            assert bad not in es and bad not in en, (err, es, en)
    assert cd._explain('yahoo', 'upstream 404') == ('Yahoo Finance: no reconoce este símbolo',
                                                    'Yahoo Finance: does not recognize this symbol')
    assert cd._explain('fmp', 'timeout')[1] == 'FMP: took too long to answer'
    assert 'límite' in cd._explain('fmp', 'upstream 429')[0]
    assert 'plan' in cd._explain('fmp', 'upstream 402')[1]
    # razón ya bilingüe de una transformación pura (tupla es/en): pasa tal cual
    assert cd._explain('yahoo', ('sin tipo de cambio XXX→USD', 'no XXX→USD exchange rate')) == \
        ('Yahoo Finance: sin tipo de cambio XXX→USD', 'Yahoo Finance: no XXX→USD exchange rate')


def test_razon_del_perfil_sin_codigos_crudos(monkeypatch):
    monkeypatch.setattr(cd, '_get_json', lambda *a, **k: (None, 'timeout'))
    p = cd.get_live_profile('ZZZZ.T', finnhub_key='', use_cache=False)
    assert p['available'] is False
    assert 'upstream' not in p['reason'] and 'timeout' not in p['reason']
    assert 'no reconoce este símbolo' in p['reason'] and 'does not recognize this symbol' in p['reason_en']
    assert 'tardó demasiado en responder' in p['reason'] and 'took too long to answer' in p['reason_en']


def test_razon_de_tipo_de_cambio_llega_bilingue_por_la_cascada(monkeypatch):
    ts = toyota_timeseries()
    monkeypatch.setattr(cd, '_yahoo_get', lambda *a, **k: (ts, None))
    monkeypatch.setattr(q, '_fx_to_usd', lambda cur: None)       # sin tipo de cambio para JPY
    r = cd.get_annual_financials('7203.T', fmp_key='', av_key='', use_cache=False)
    assert r['available'] is False
    assert 'sin tipo de cambio JPY' in r['reason'] and 'JPY→USD exchange rate' in r['reason_en']


def test_perfil_en_vivo_chart_si_quote_summary_falla_fuera_de_eeuu(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        assert 'finnhub' not in url                         # bolsa de Tokio: Finnhub free no la cubre
        if '/v8/finance/chart/' in url:
            return {'chart': {'result': [{
                'meta': {'symbol': '8411.T', 'currency': 'JPY', 'regularMarketPrice': 4012.0,
                         'regularMarketTime': 1759036800 + 3600},
                'timestamp': [1758844800, 1758931200, 1759017600 + 3600],
                'indicators': {'quote': [{'close': [3900.0, 3963.0, 4012.0]}]}}]}}, None
        return None, 'upstream 404'

    monkeypatch.setattr(cd, '_get_json', fake_get)
    p = cd.get_live_profile('8411.T', finnhub_key='k', use_cache=False)
    assert p['available'] is True and p['source'] == 'yahoo'
    assert p['price'] == 4012.0 and p['prev_close'] == 3963.0
    assert p['price_usd'] == pytest.approx(4012.0 * JPY, abs=1e-3)


def test_perfil_en_vivo_sin_nada_no_inventa():
    p = cd.get_live_profile('ZZZZ.T', finnhub_key='', use_cache=False)
    assert p['available'] is False and p['price'] is None and p['market_cap_usd_b'] is None
    assert p['reason'] and p['reason_en']


# ════════════════════════════════════════════════════════════════════════════
# Rutas HTTP
# ════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def client(monkeypatch):
    import server
    server.app.config['TESTING'] = True
    monkeypatch.setattr(server, 'FMP', '')
    monkeypatch.setattr(server, 'AV_KEY', '')
    monkeypatch.setattr(server, 'FINNHUB', '')
    with server.app.test_client() as c:
        yield c


FINDOSSIER_KEYS = ('available', 'ticker', 'years', 'revenue', 'revenue_growth', 'gross_margin',
                   'capex', 'fcf', 'fcf_margin', 'fcf_growth', 'dilution', 'de_ratio', 'roe',
                   'ev_to_sales', 'shares', 'reason', 'source', 'currency')
DOSSIER_KEYS = ('ticker', 'years', 'synthetic', 'revenue', 'revenue_growth', 'shares', 'fcf',
                'fcf_margin', 'ev_revenue', 'pe_ratio', 'total_debt', 'cash', 'net_debt',
                'gross_margin', 'net_margin', 'roe', 'roic', 'net_income', 'eps', 'ebitda',
                'available', 'source', 'currency')


def test_ruta_findossier_conserva_claves_y_unidades(client, monkeypatch):
    monkeypatch.setattr(cd, '_yahoo_get', lambda *a, **k: (toyota_timeseries(), None))
    d = client.get('/api/findossier/7203.T').get_json()
    for k in FINDOSSIER_KEYS:
        assert k in d, k
    assert d['available'] is True and d['source'] == 'yahoo' and d['currency'] == 'JPY'
    assert d['years'] == ['2022', '2023', '2024', '2025']
    assert d['revenue'][-1] == pytest.approx(48.04e12 * JPY)          # USD CRUDO (fincard divide /1e9)
    assert d['revenue_growth'][0] is None
    assert d['revenue_growth'][-1] == round((48.04 / 45.10 - 1) * 100, 1)   # %
    assert d['gross_margin'][-1] == round(9.6 / 48.04 * 100, 1)             # %
    assert d['shares'][-1] == 13.22                                        # miles de millones
    assert d['dilution'][-1] == round((13.22 / 13.48 - 1) * 100, 2)         # %
    assert d['fcf'][-1] == pytest.approx((3.69e12 - 2.2e12) * JPY)          # crudo
    assert d['fcf_margin'][-1] == round((3.69 - 2.2) / 48.04 * 100, 1)
    assert d['capex'][-1] == pytest.approx(2.2e12 * JPY)                    # valor absoluto
    assert d['de_ratio'][-1] == round(38.0 / 36.9, 3)
    assert d['roe'][-1] == round(4.77 / 36.9 * 100, 1)
    assert d['ev_to_sales'] == [None, None, None, None]
    assert all(len(d[k]) == 4 for k in ('revenue', 'fcf', 'roe', 'dilution', 'capex'))


def test_ruta_findossier_sin_datos(client):
    d = client.get('/api/findossier/ZZZZ.T').get_json()
    assert d['available'] is False and d['reason'] and d['source'] is None


def test_ruta_dossier_en_miles_de_millones_y_nunca_sintetico(client, monkeypatch):
    monkeypatch.setattr(cd, '_yahoo_get', lambda *a, **k: (toyota_timeseries(), None))
    r = client.get('/api/dossier/7203.T')
    assert r.status_code == 200
    d = r.get_json()
    for k in DOSSIER_KEYS:
        assert k in d, k
    assert d['synthetic'] is False and d['available'] is True
    assert d['revenue'][-1] == round(48.04e12 * JPY / 1e9, 2)        # miles de millones USD
    assert d['shares'][-1] == 13.22
    assert d['net_debt'][-1] == round((38.0e12 - 8.9e12) * JPY / 1e9, 2)
    assert d['net_margin'][-1] == round(4.77 / 48.04 * 100, 1)
    assert d['roic'][-1] == round(4.8 * 0.75 / 66 * 100, 1)
    assert d['eps'][-1] == round(359.6 * JPY, 2)
    assert d['ev_revenue'] == [None] * 4 and d['pe_ratio'] == [None] * 4   # Yahoo no los da: nada inventado


def test_ruta_dossier_sin_datos_200_available_false(client):
    r = client.get('/api/dossier/ZZZZ')
    assert r.status_code == 200                           # antes 503 → el cliente inventaba
    d = r.get_json()
    assert d['available'] is False and d['synthetic'] is False
    assert d['ticker'] == 'ZZZZ' and d['reason']
    assert 'error' not in d
    assert 'revenue' not in d and 'fcf' not in d          # CERO números inventados


def test_ruta_live(client, monkeypatch):
    monkeypatch.setattr(cd, '_yahoo_get', lambda *a, **k: (mizuho_quote_summary(), None))
    r = client.get('/api/company/live/8411.T')
    assert r.status_code == 200
    d = r.get_json()
    assert d['available'] is True and d['source'] == 'yahoo'
    assert d['employees'] == 52307 and d['market_cap_usd_b'] > 0
    assert d['as_of'].endswith('Z')
    # sin ninguna fuente: 200 con available false (nunca 5xx)
    monkeypatch.setattr(cd, '_yahoo_get', lambda *a, **k: (None, 'upstream 404'))
    r2 = client.get('/api/company/live/QQQQ.T')
    assert r2.status_code == 200 and r2.get_json()['available'] is False


def test_rutas_ticker_invalido(client):
    for path in ('/api/company/live/', '/api/dossier/', '/api/findossier/'):
        assert client.get(path + 'A%26token%3Dx').status_code == 400
