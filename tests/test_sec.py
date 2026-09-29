"""SEC EDGAR como evidencia primaria (core/sec + research/context)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class R:
    def __init__(self, js=None, text='', ok=True):
        self._js, self.text, self.ok, self.status_code = js, text, ok, 200 if ok else 404

    def json(self):
        return self._js


def _getter(url, headers=None, timeout=None):
    assert 'User-Agent' in headers
    if 'company_tickers' in url:
        return R({'0': {'ticker': 'AVGO', 'cik_str': 1730168}})
    if 'submissions' in url:
        return R({'filings': {'recent': {
            'form': ['4', '8-K', '10-Q', '10-K'], 'filingDate': ['2026-09-20', '2026-09-12', '2026-09-10', '2025-12-18'],
            'accessionNumber': ['0001-1', '0001-2', '0001-3', '0001-4'],
            'primaryDocument': ['f4.xml', 'ek.htm', 'q.htm', 'k.htm'],
            'primaryDocDescription': ['', '8-K', '10-Q', '10-K'], 'items': ['', '2.02,9.01', '', '']}}})
    return R(text='<html>Table of contents Item 1A. Risk Factors 12 ... '
                  '<p>Item 1A. Risk Factors</p><p>' + 'Our customers are concentrated. ' * 40 + '</p>'
                  "<p>Item 2. Management's Discussion and Analysis</p><p>" + 'Revenue grew 22%. ' * 40 + '</p></html>')


def test_latest_filings_filtra_formularios_y_arma_urls():
    from core import sec
    sec._TICKERS.update(map=None, ts=0)
    sec._CACHE.clear()
    fl = sec.latest_filings('AVGO', getter=_getter)
    assert [f['form'] for f in fl] == ['8-K', '10-Q', '10-K']           # el Form 4 no entra
    assert fl[0]['url'] == 'https://www.sec.gov/Archives/edgar/data/1730168/00012/ek.htm'
    assert fl[0]['items'] == '2.02,9.01'


def test_filing_sections_salta_el_indice_y_extrae_contenido():
    from core import sec
    sec._CACHE.clear()
    out = sec.filing_sections('https://www.sec.gov/x.htm', getter=_getter)
    assert 'customers are concentrated' in out['risk_factors']
    assert 'Revenue grew 22%' in out['mdna']


def test_contexto_incluye_reportes_sec_para_el_agente_fundamental():
    from research.context import ContextBuilder
    fetch = {'financials': lambda s: {}, 'profile': lambda s: {}, 'news': lambda q, n: [],
             'web': lambda q, n: [], 'candles': lambda s: [], 'mcap': lambda s: None,
             'sec_filings': lambda s: [{'form': '10-Q', 'date': '2026-09-10', 'items': '',
                                        'url': 'https://www.sec.gov/a/q.htm', 'description': '10-Q'}],
             'sec_sections': lambda u: {'risk_factors': 'Customer concentration risk. ' * 10}}
    ctx = ContextBuilder(fetchers=fetch).build('Broadcom', 'fundamental', depth='STANDARD')
    filings = [e for e in ctx['evidence'] if e['source_type'] == 'filing']
    assert len(filings) == 2 and filings[0]['reliability'] == 0.95
    assert filings[1]['reference'] == 'https://www.sec.gov/a/q.htm' and 'Customer concentration' in filings[1]['excerpt']
    # QUICK: solo la lista, sin descargar el documento
    ctx_q = ContextBuilder(fetchers=fetch).build('Broadcom', 'fundamental', depth='QUICK')
    assert len([e for e in ctx_q['evidence'] if e['source_type'] == 'filing']) == 1


def test_ticker_extranjero_no_se_confunde_con_uno_de_eeuu():
    from core import sec
    sec._TICKERS.update(map={'BA': '0000012927', 'BRK-B': '0001067983'}, ts=9e18)
    assert sec.resolve_cik('BA.L') is None           # BAE Systems ≠ Boeing
    assert sec.resolve_cik('6488.TWO') is None
    assert sec.resolve_cik('BRK.B') == '0001067983'  # clase de acción de EE.UU.
    assert sec.resolve_cik('BA') == '0000012927'


def test_seccion_prioriza_encabezado_especifico_y_apostrofe_curvo():
    from core import sec
    html = ('<p>Item 1A. Risk Factors</p><p>' + 'Real risk text. ' * 60 + '</p>'
            '<p>Item 7. Management’s Discussion and Analysis</p><p>' + 'Revenue grew. ' * 60 + '</p>'
            '<p>as discussed in Risk Factors above, ' + 'cross reference filler. ' * 60 + '</p>')
    txt = sec._strip_html(html)
    assert sec._section(txt, ['Item 1A. Risk Factors', 'Risk Factors'], 800).startswith('Item 1A. Risk Factors')
    assert 'Revenue grew' in sec._section(txt, ["Item 7. Management's Discussion"], 800)
