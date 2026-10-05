"""Payloads con la FORMA real de las fuentes nuevas del World Monitor (core/world_feeds.py)."""
from datetime import datetime, timedelta, timezone

_LAST = datetime(2026, 9, 28, tzinfo=timezone.utc)


def _pw_rows():
    rows = []
    for i in range(100):
        d = _LAST - timedelta(days=i)
        ms = int(d.timestamp() * 1000)
        suez = 30 if i < 7 else 60                       # −50 % en la última semana
        rows.append({'attributes': {'date': ms, 'year': d.year, 'month': d.month, 'day': d.day, 'portid': 'chokepoint1',
                                    'portname': 'Suez Canal', 'n_total': suez, 'n_tanker': 10, 'n_container': 8,
                                    'n_dry_bulk': 7}})
        rows.append({'attributes': {'date': d.strftime('%Y-%m-%d'), 'portid': 'chokepoint6', 'portname': 'Malacca Strait',
                                    'n_total': 220 + (i % 3), 'n_tanker': 60, 'n_container': 70}})
    return rows


PORTWATCH_PAYLOAD = {'features': _pw_rows(), 'exceededTransferLimit': False}

FEDREG_PAYLOAD = {'count': 3, 'results': [
    {'title': 'Additions to the Entity List', 'type': 'Rule', 'document_number': '2026-19001',
     'abstract': 'BIS adds entities in China, including SMIC affiliates, for acquiring advanced computing integrated circuits for AI.',
     'html_url': 'https://www.federalregister.gov/documents/2026/09/30/2026-19001/additions-to-the-entity-list',
     'publication_date': '2026-09-30', 'agencies': [{'slug': 'industry-and-security-bureau', 'name': 'Industry and Security Bureau'}]},
    {'title': 'Notice of OFAC Sanctions Actions', 'type': 'Notice', 'document_number': '2026-19002',
     'abstract': 'OFAC is publishing the names of persons whose property is blocked under the Russian harmful foreign activities sanctions.',
     'html_url': 'https://www.federalregister.gov/documents/2026/09/29/2026-19002/notice-of-ofac-sanctions-actions',
     'publication_date': '2026-09-29', 'agencies': [{'slug': 'foreign-assets-control-office', 'name': 'Foreign Assets Control Office'}]},
    {'title': 'Information Collection: Export Licensing', 'type': 'Notice', 'document_number': '2026-19003',
     'abstract': 'Proposed collection; comment request.', 'html_url': 'https://www.federalregister.gov/documents/2026/09/28/x',
     'publication_date': '2026-09-28', 'agencies': [{'slug': 'industry-and-security-bureau'}]},
]}

GDACS_PAYLOAD = {'type': 'FeatureCollection', 'features': [
    {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [121.0, 23.5]},
     'properties': {'eventtype': 'TC', 'eventid': 1001234, 'name': 'CHOI-WAN-26', 'alertlevel': 'Red', 'iscurrent': 'true',
                    'country': 'Taiwan', 'fromdate': '2026-09-29T00:00:00', 'todate': '2026-10-05T06:00:00',
                    'datemodified': '2026-10-05T06:00:00', 'severitydata': {'severity': 250, 'severitytext': 'Super Typhoon (h-5) (wind 250 km/h)'},
                    'url': {'report': 'https://www.gdacs.org/report.aspx?eventid=1001234&eventtype=TC'}}},
    {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [10.0, 10.0]},
     'properties': {'eventtype': 'FL', 'eventid': 5, 'alertlevel': 'Green', 'country': 'Nigeria', 'todate': '2026-10-04T00:00:00'}},
]}


def route(url):
    if 'arcgis' in url:
        return PORTWATCH_PAYLOAD
    if 'federalregister' in url:
        return FEDREG_PAYLOAD
    if 'gdacs' in url:
        return GDACS_PAYLOAD
    return None
