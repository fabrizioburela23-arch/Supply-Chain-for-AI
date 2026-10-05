"""core/gpr.py — índice de riesgo geopolítico (Caldara-Iacoviello), sin red: filas como las del .xls."""
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import gpr as G  # noqa: E402


def _daily_rows():
    d0 = datetime(2025, 10, 1)
    rows = [['DAY', 'N10D', 'GPRD', 'GPRD_ACT', 'GPRD_THREAT', 'date', 'GPRD_MA30', 'GPRD_MA7', 'event']]
    for i in range(370):
        d = d0 + timedelta(days=i)
        v = 100 + (i % 10) + (80 if i >= 365 else 0)          # los últimos 5 días se dispara
        rows.append([int(d.strftime('%Y%m%d')), 5000, v, v, v, '', '', '', ''])
    return rows


def _monthly_rows():
    rows = [['month', 'GPR', 'GPRT', 'GPRA', 'GPRC_CHN', 'GPRC_TWN', 'GPRC_USA']]
    for m in range(13):
        rows.append([f'2025-{m + 1:02d}' if m < 12 else '2026-01', 100 + m, 0, 0, 0.5, 0.10 if m < 12 else 0.30, 2.0])
    return rows


def test_diario_ultimo_valor_medias_y_percentil():
    d = G.parse_daily(_daily_rows())
    assert d['date'] == '2026-10-05' and d['value'] >= 180
    assert d['avg30'] < d['avg7'] and d['percentile_1y'] == 100 and len(d['history']) == 120


def test_mensual_por_pais_contra_su_ano():
    m = G.parse_monthly(_monthly_rows())
    assert m['month'] == '2026-01' and m['global'] == 112
    twn = next(c for c in m['countries'] if c['iso3'] == 'TWN')
    assert twn['country_key'] == 'Taiwan' and twn['vs_12m'] == 3.0 and m['countries'][0]['iso3'] == 'TWN'


def test_gpr_con_cache_y_fuente_caida(monkeypatch):
    G._CACHE.update(data=None, ts=0.0)
    monkeypatch.setattr(G, '_get', lambda url: url.encode())
    monkeypatch.setattr(G, '_xls_rows', lambda content: ((_daily_rows() if b'daily' in content else _monthly_rows()), 0))
    out = G.gpr()
    assert out['ok'] and out['daily']['value'] >= 180 and out['monthly']['month'] == '2026-01' and G.gpr_cached() is out
    # el país con la prensa disparando sube en la capa de inestabilidad
    from core import world as W
    it = W._blend_live_country({'country_key': 'Taiwan', 'severity': 60})
    assert it['gpr_country']['vs_12m'] == 3.0 and it['severity'] == 65
    # fuente caída: se sirve lo último bueno marcado stale
    G._CACHE['ts'] = 0.0
    monkeypatch.setattr(G, '_get', lambda url: (_ for _ in ()).throw(IOError('http:503')))
    st = G.gpr()
    assert st['ok'] and st.get('stale')
    G._CACHE.update(data=None, ts=0.0)
    assert G.gpr()['error_code'] == 'source_unavailable'
