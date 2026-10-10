"""Overnight 3 (2026-10-10) — 🩺 Sistema bilingüe en el SERVIDOR.

La tarjeta (app.html _diagCard) ya sabía mostrar detail_en / fix_en en inglés, pero solo la voz los mandaba: todo
lo demás llegaba solo en español. Ahora CADA _diag_* (y las tarjetas que arma la ruta /api/diagnostics) devuelve
`detail` (ES, mismo texto de siempre) + `detail_en`, y `fix_es`/`fix_en` cuando hay un arreglo que sugerir (que
además va al final del detalle como « — QUÉ HACER: … », el formato de la voz, para que la tarjeta no lo repita).
La tarjeta de Claude dice el ORDEN de las IAs por nivel (core.ai.ai_route_state) en palabras simples.
Nada de esto puede filtrar una clave: todo pasa por _diag_redact.
Red simulada en todos los tests (ninguna llamada real).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('SECRET_KEY', 'test-secret-key')

import requests  # noqa: E402

import server  # noqa: E402
from core import ai  # noqa: E402
from core import quotes  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = shutil.which('node')

# Valores "secretos" reconocibles: si alguno aparece en una tarjeta, es una filtración.
SECRETS = {
    'CLAUDE': 'sk-ant-SECRETclaude-0123456789abcdef',
    'GEMINI_KEY': 'AIzaSECRETgemini0123456789abcdef',
    'NVIDIA_KEY': 'nvapi-SECRETnvidia-0123456789abcdef',
    'FINNHUB': 'SECRETfinnhub0123456789abcdef',
    'FMP': 'SECRETfmp0123456789abcdefghij',
    'ALPACA_KEY': 'PKSECRETalpacaKEY01234567',
    'ALPACA_SECRET': 'SECRETalpacaSECRET0123456789abcdef',
    'NEO4J_PASSWORD': 'SECRETneo4jPass0123456789',
    'ELEVENLABS_KEY': 'sk_SECRETeleven0123456789abcdef',
}
DB_PASS = 'SECRETdbPass0123456789'

# Palabras que delatan un detalle en español colado en el campo inglés.
_ES_WORDS = re.compile(r'\b(está|no conecta|rechazó|válida|responde|configurad[ao]|QUÉ HACER|Opcional|'
                       r'Revisa|Espera|añade|pausa|sin clave)\b', re.I)


class _Resp:
    def __init__(self, status=200, body=None):
        self.status_code = status
        self.ok = 200 <= status < 300
        self._b = body

    def json(self):
        return self._b


def _fake_anthropic(behavior):
    """behavior(model) → nombre del modelo o lanza."""
    class Messages:
        def create(self, **kw):
            return types.SimpleNamespace(model=behavior(kw['model']), content=[], stop_reason='max_tokens', usage=None)

    class Client:
        def __init__(self, **kw):
            self.messages = Messages()
    return types.SimpleNamespace(Anthropic=Client)


@pytest.fixture(autouse=True)
def _aislado(monkeypatch):
    for k in ('AI_ORDER_FAST', 'AI_ORDER_DEEP'):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(ai, 'AI_ORDER_EXPLICIT', False)
    monkeypatch.setattr(ai, 'AI_ORDER', ai._AI_ORDER_FROM_CONFIG)
    monkeypatch.setattr(ai, '_CIRCUIT', {})
    # circuito de Finnhub PROPIO del test (otros tests cuentan sus `hits` desde 0)
    monkeypatch.setattr(quotes, '_FH_CIRCUIT', {'until': 0.0, 'hits': 0, 'last_429': None})
    server._DIAG_CACHE.update(ts=0.0, data=None)
    yield
    server._DIAG_CACHE.update(ts=0.0, data=None)


def _no_keys(monkeypatch):
    for k in ('CLAUDE', 'GEMINI_KEY', 'NVIDIA_KEY', 'FINNHUB', 'FMP', 'ALPACA_KEY', 'ALPACA_SECRET', 'MSTACK', 'AV_KEY'):
        monkeypatch.setattr(server, k, '', raising=False)
    monkeypatch.setattr(server, '_temporal_mode', lambda: 'native')


def _with_keys(monkeypatch):
    for k, v in SECRETS.items():
        monkeypatch.setattr(server, k, v, raising=False)
    monkeypatch.setattr(server, '_NEO4J_PASSWORD_RAW', SECRETS['NEO4J_PASSWORD'])
    monkeypatch.setattr(server, 'NEO4J_URI', 'neo4j+s://abc123.databases.neo4j.io')
    monkeypatch.setattr(server, '_temporal_mode', lambda: 'neo4j')


def _check_card(name, d):
    assert isinstance(d, dict), name
    es, en = d.get('detail'), d.get('detail_en')
    assert isinstance(es, str) and es.strip(), f'{name}: sin detail'
    assert isinstance(en, str) and en.strip(), f'{name}: sin detail_en'
    assert 'configured' in d and 'ok' in d, f'{name}: perdió claves de siempre'
    if d.get('fix_es') or d.get('fix_en'):
        assert d.get('fix_es') and d.get('fix_en'), f'{name}: arreglo en un solo idioma'
        # el arreglo va al FINAL del detalle con el formato de la voz (la tarjeta lo quita al pintarlo aparte)
        assert es.endswith(' — QUÉ HACER: ' + d['fix_es']), name
        assert en.endswith(' — WHAT TO DO: ' + d['fix_en']), name
        assert not _ES_WORDS.search(d['fix_en']), f'{name}: fix_en en español: {d["fix_en"]}'
    # el texto inglés no es el español copiado (salvo cifras/errores crudos del proveedor)
    head_en = en.split(' — WHAT TO DO: ')[0]
    assert not _ES_WORDS.search(head_en.split('(Orden')[0]), f'{name}: detail_en en español: {en}'


def _all_diags():
    return {
        'claude': server._diag_claude(), 'gemini': server._diag_gemini(), 'nvidia': server._diag_nvidia(),
        'finnhub': server._diag_finnhub(), 'yahoo': server._diag_yahoo(), 'fmp': server._diag_fmp(),
        'grafo': server._diag_grafo(), 'ontologia': server._diag_ontologia(), 'alpaca': server._diag_alpaca(),
    }


# ── 1. sin claves: cada tarjeta en los dos idiomas + qué hacer ───────────────────────────────────────────
def test_sin_claves_todas_bilingues(monkeypatch):
    _no_keys(monkeypatch)
    import ontology.db as odb
    monkeypatch.setattr(odb, 'ontology_available', lambda: False)
    monkeypatch.setattr(server.requests, 'get', lambda *a, **k: _Resp(200, {
        'chart': {'result': [{'meta': {'regularMarketPrice': 180.5}}]}}))
    cards = _all_diags()
    for name, d in cards.items():
        _check_card(name, d)
    # el español de siempre sigue ahí, palabra por palabra
    assert cards['gemini']['detail'].startswith('GEMINI_KEY no está. (Opcional) Canal de respaldo de IA — Google Gemini.')
    assert cards['finnhub']['detail'].startswith('FINNHUB_KEY no está. Los precios en vivo del terminal no cargarán.')
    assert cards['ontologia']['detail'].startswith('Ontología no configurada (opcional).')
    assert cards['grafo']['detail'].startswith('Grafo de Conocimiento Temporal en modo NATIVO')
    assert cards['alpaca']['mode'] in ('paper', 'live')
    # no configurado → «Qué hacer» con el paso exacto en Railway (ES y EN)
    for name in ('claude', 'gemini', 'nvidia', 'finnhub', 'fmp', 'alpaca'):
        assert cards[name]['configured'] is False and cards[name]['fix_es'] and cards[name]['fix_en'], name
        assert 'Railway' in cards[name]['fix_es'] and 'Railway' in cards[name]['fix_en'], name
    assert 'ANTHROPIC_KEY' in cards['claude']['fix_en']
    # tarjetas verdes (Yahoo, grafo nativo, ontología opcional) NO llevan «Qué hacer»
    for name in ('yahoo', 'grafo', 'ontologia'):
        assert cards[name]['ok'] is True and 'fix_es' not in cards[name], name
    assert cards['yahoo']['detail_en'].startswith('Yahoo answers — NVDA quote $180.5 OK')


# ── 2. claves presentes, todo responde bien ──────────────────────────────────────────────────────────────
def test_todo_ok_bilingue(monkeypatch):
    _with_keys(monkeypatch)
    monkeypatch.setitem(sys.modules, 'anthropic', _fake_anthropic(lambda m: m))
    monkeypatch.setattr(server, '_complete_gemini', lambda *a, **k: ('pong', 'gemini:gemini-3.8-flash'))
    monkeypatch.setattr(server, '_complete_nvidia', lambda *a, **k: ('pong', 'nvidia:meta/llama'))
    monkeypatch.setattr(server, 'ALPACA_BASE', 'https://paper-api.alpaca.markets')

    def get(url, *a, **k):
        if 'finnhub' in url:
            return _Resp(200, {'c': 190.1})
        if 'financialmodelingprep' in url:
            return _Resp(200, [{'symbol': 'AAPL', 'companyName': 'Apple Inc.'}])
        if 'yahoo' in url:
            return _Resp(200, {'chart': {'result': [{'meta': {'regularMarketPrice': 180.5}}]}})
        if 'alpaca' in url:
            return _Resp(200, {'status': 'ACTIVE'})
        raise AssertionError(url)
    monkeypatch.setattr(server.requests, 'get', get)
    monkeypatch.setattr(server, '_get_neo4j_driver', lambda: types.SimpleNamespace(verify_connectivity=lambda: None))
    import ontology.db as odb
    monkeypatch.setattr(odb, 'ontology_available', lambda: False)
    cards = _all_diags()
    for name, d in cards.items():
        _check_card(name, d)
        assert d['ok'] is True, (name, d)
        assert 'fix_es' not in d, name
    assert cards['finnhub']['detail'] == 'Key válida — cotización AAPL $190.1 OK.'
    assert cards['finnhub']['detail_en'] == 'Valid key — AAPL quote $190.1 OK.'
    assert cards['fmp']['detail_en'] == 'Valid key — AAPL profile (Apple Inc.) OK.'
    assert cards['gemini']['detail_en'] == 'Valid key — gemini:gemini-3.8-flash answered.'
    assert cards['alpaca']['detail'] == 'Cuenta PAPEL (simulada) conectada — sin dinero real.'
    assert cards['alpaca']['detail_en'] == 'PAPER (simulated) account connected — no real money.'
    assert cards['alpaca']['mode'] == 'paper'
    g = cards['grafo']
    assert g['detail'].startswith('Neo4j conectado — memoria temporal persistente activa. [usuario=')
    assert g['detail_en'].startswith('Neo4j connected — persistent temporal memory active. [user=')
    assert 'chars]' in g['detail_en'] and 'abc123.databases.neo4j.io' in g['detail_en']
    # cuenta REAL: el aviso también en inglés
    monkeypatch.setattr(server, 'ALPACA_BASE', 'https://api.alpaca.markets')
    live = server._diag_alpaca()
    assert live['mode'] == 'live' and live['detail_en'] == '⚠ REAL account connected — orders move real money.'


# ── 3. fallas reconocibles: pista en los dos idiomas, sin repetir y sin claves ─────────────────────────────
def test_fallas_con_arreglo_en_dos_idiomas(monkeypatch):
    _with_keys(monkeypatch)
    import core.config as cfg
    monkeypatch.setattr(cfg, 'AI_MODEL_FAST', 'claude-haiku-4-5')
    monkeypatch.setattr(cfg, 'AI_MODEL_DEEP', 'claude-sonnet-5-5')

    def claude_falla(m):
        raise RuntimeError('Error code: 400 — your credit balance is too low (x-api-key ' + SECRETS['CLAUDE'] + ')')
    monkeypatch.setitem(sys.modules, 'anthropic', _fake_anthropic(claude_falla))

    def gem(*a, **k):
        raise RuntimeError('Gemini HTTP 404 NOT_FOUND models/gemini-x ?key=' + SECRETS['GEMINI_KEY'])

    def nv(*a, **k):
        raise RuntimeError('NVIDIA HTTP 401 Unauthorized Bearer ' + SECRETS['NVIDIA_KEY'])
    monkeypatch.setattr(server, '_complete_gemini', gem)
    monkeypatch.setattr(server, '_complete_nvidia', nv)

    def get(url, *a, **k):
        if 'finnhub' in url:
            return _Resp(401, {})
        if 'financialmodelingprep' in url:
            return _Resp(402, {})
        if 'yahoo' in url:
            return _Resp(429, {})
        if 'alpaca' in url:
            return _Resp(403, {})
        raise AssertionError(url)
    monkeypatch.setattr(server.requests, 'get', get)

    def drv():
        raise RuntimeError('connection timed out (neo4j:' + SECRETS['NEO4J_PASSWORD'] + '@abc123.databases.neo4j.io)')
    monkeypatch.setattr(server, '_get_neo4j_driver', drv)
    import ontology.db as odb

    def onto():
        raise RuntimeError('could not translate host name "postgres.railway.internal" to address: Name or service '
                           f'not known (postgresql://postgres:{DB_PASS}@postgres.railway.internal:5432/railway)')
    monkeypatch.setattr(odb, 'ontology_available', onto)
    cards = _all_diags()
    blob = json.dumps(cards, ensure_ascii=False)
    for name, d in cards.items():
        _check_card(name, d)
        assert d['ok'] is False, name
    for v in list(SECRETS.values()) + [DB_PASS]:
        assert v not in blob, f'filtró {v}'
    c = cards['claude']
    assert c['fix_es'] == 'Saldo agotado: recarga en la consola del proveedor.'
    assert c['fix_en'] == 'Out of credit: top up in the provider console.'
    assert c['detail'].startswith('FAST: claude-haiku-4-5 ✗')
    g = cards['gemini']
    assert 'GEMINI_MODEL' in g['fix_es'] and 'retirado' in g['fix_es']
    assert 'GEMINI_MODEL' in g['fix_en'] and 'retired' in g['fix_en']
    assert g['detail'].startswith('Gemini rechazó la llamada: ') and g['detail_en'].startswith('Gemini rejected the call: ')
    assert cards['nvidia']['fix_en'] == 'The key looks invalid or has no permission for that model.'
    assert cards['finnhub']['fix_en'].startswith('Check FINNHUB_KEY in Railway')
    assert cards['finnhub']['detail_en'].startswith('Finnhub HTTP 401 — invalid key or rate-limited.')
    assert cards['fmp']['detail'].startswith('FMP HTTP 402 — plan sin acceso a este endpoint (402).')
    assert cards['fmp']['detail_en'].startswith('FMP HTTP 402 — the plan has no access to this endpoint (402).')
    assert 'Yahoo/AlphaVantage' in cards['fmp']['fix_en']
    assert cards['yahoo']['fix_en'].startswith('Wait a few minutes')
    assert cards['alpaca']['fix_en'].startswith('Check ALPACA_KEY and ALPACA_SECRET')
    o = cards['ontologia']
    assert o['detail'].startswith('Ontología configurada pero no conecta: ')
    assert 'REFERENCIA' in o['fix_es'] and 'REFERENCE' in o['fix_en'] and '${{Postgres.DATABASE_URL}}' in o['fix_en']
    n = cards['grafo']
    assert n['fix_es'].startswith('Tiempo de espera agotado') and n['fix_en'].startswith('Timed out')
    assert ' [user=neo4j · host=abc123.databases.neo4j.io · pw=' in n['detail_en']


# ── 4. fallas de red crudas (excepciones con la clave dentro): nunca salen ────────────────────────────────
def test_excepciones_crudas_no_filtran_claves(monkeypatch):
    _with_keys(monkeypatch)
    monkeypatch.setitem(sys.modules, 'anthropic', types.SimpleNamespace(
        Anthropic=lambda **kw: (_ for _ in ()).throw(RuntimeError('boom api_key=' + SECRETS['CLAUDE']))))

    def get(url, *a, **k):
        hdrs = k.get('headers') or {}
        raise requests.exceptions.ConnectionError(f'Max retries exceeded with url: {url} headers={hdrs} '
                                                  f'secret {SECRETS["ALPACA_SECRET"]}')
    monkeypatch.setattr(server.requests, 'get', get)
    monkeypatch.setattr(server, '_complete_gemini', lambda *a, **k: (_ for _ in ()).throw(
        RuntimeError('weird ' + SECRETS['GEMINI_KEY'])))
    monkeypatch.setattr(server, '_complete_nvidia', lambda *a, **k: (_ for _ in ()).throw(
        RuntimeError('weird ' + SECRETS['NVIDIA_KEY'])))
    monkeypatch.setattr(server, '_get_neo4j_driver', lambda: (_ for _ in ()).throw(
        RuntimeError('weird ' + SECRETS['NEO4J_PASSWORD'])))
    cards = _all_diags()
    blob = json.dumps(cards, ensure_ascii=False)
    for v in SECRETS.values():
        assert v not in blob, f'filtró {v}'
    for name, d in cards.items():
        if name in ('ontologia',):
            continue
        _check_card(name, d)
        assert d['ok'] is False, name
    # Alpaca: antes str(e)[:100] crudo → la clave podía salir; ahora redactado
    assert cards['alpaca']['detail'].startswith('Alpaca inalcanzable: ')
    assert cards['alpaca']['detail_en'].startswith('Alpaca unreachable: ')
    assert cards['finnhub']['detail_en'].startswith('Could not reach Finnhub: ')
    assert cards['claude']['detail_en'].startswith('Key present but the API rejected the call: ')


# ── 5. el orden de las IAs en palabras simples ───────────────────────────────────────────────────────────
def test_tarjeta_claude_dice_el_orden_de_las_ias(monkeypatch):
    monkeypatch.setattr(ai, 'CLAUDE', 'x' * 20)
    monkeypatch.setattr(ai, 'GEMINI_KEY', 'y' * 20)
    monkeypatch.setattr(ai, 'NVIDIA_KEY', '')
    monkeypatch.setattr(ai, 'AI_MODEL_FAST', 'claude-haiku-4-5')
    monkeypatch.setattr(ai, 'AI_MODEL_DEEP', 'claude-sonnet-5-5')
    es, en = server._diag_ai_route()
    assert 'Profundo: Claude Sonnet 5.5 → Gemini → NVIDIA (sin clave)' in es
    assert 'Rápido: Gemini → Claude Haiku 4.5 → NVIDIA (sin clave)' in es
    assert 'Deep: Claude Sonnet 5.5 → Gemini → NVIDIA (no key)' in en
    assert 'Fast: Gemini → Claude Haiku 4.5 → NVIDIA (no key)' in en
    # va entre paréntesis: la tarjeta no confunde sus flechas con la pista « → …»
    assert es.startswith('(') and es.endswith(')') and en.startswith('(') and en.endswith(')')
    # en pausa + orden fijado por la variable vieja AI_ORDER (lo que hay hoy en Railway)
    ai._open_circuit('gemini', 'credit', 'credit balance too low')
    monkeypatch.setattr(ai, 'AI_ORDER_EXPLICIT', True)
    monkeypatch.setattr(ai, 'AI_ORDER', ['gemini', 'nvidia', 'claude'])
    es, en = server._diag_ai_route()
    assert 'Rápido (lo fija AI_ORDER): Gemini (en pausa) → NVIDIA (sin clave) → Claude Haiku 4.5' in es
    assert 'Fast (set by AI_ORDER): Gemini (paused) → NVIDIA (no key) → Claude Haiku 4.5' in en
    assert 'Profundo: Claude Sonnet 5.5 → Gemini (en pausa)' in es
    # y la tarjeta de Claude lo lleva en los dos idiomas (con clave o sin ella)
    monkeypatch.setattr(server, 'CLAUDE', '')
    card = server._diag_claude()
    assert '(Orden de las IAs — Profundo: Claude Sonnet 5.5' in card['detail']
    assert '(AI order — Deep: Claude Sonnet 5.5' in card['detail_en']
    monkeypatch.setattr(server, 'CLAUDE', 'sk-ant-test-0123456789')
    monkeypatch.setitem(sys.modules, 'anthropic', _fake_anthropic(lambda m: m))
    import core.config as cfg
    monkeypatch.setattr(cfg, 'AI_MODEL_FAST', 'claude-haiku-4-5')
    monkeypatch.setattr(cfg, 'AI_MODEL_DEEP', 'claude-sonnet-5-5')
    card = server._diag_claude()
    assert card['ok'] and '✗' not in card['detail']
    assert card['detail'].startswith('FAST: claude-haiku-4-5 ✓') and ' · (Orden de las IAs — ' in card['detail']
    assert card['detail_en'].startswith('FAST: claude-haiku-4-5 ✓') and ' · (AI order — Deep: ' in card['detail_en']


def test_nombre_legible_del_modelo():
    f = server._diag_model_name
    assert f('claude-sonnet-5-5') == 'Claude Sonnet 5.5'
    assert f('claude-haiku-4-5-20251001') == 'Claude Haiku 4.5'
    assert f('claude-opus-5-5') == 'Claude Opus 5.5'
    assert f('claude-sonnet-5') == 'Claude Sonnet 5'
    assert f('claude-3-5-sonnet-20241022') == 'Claude Sonnet 3.5'
    assert f('claude-sonnet-5-5[1m]') == 'Claude Sonnet 5.5'
    assert f('algo-raro') == 'algo-raro' and f('') == 'Claude'


# ── 6. las pistas viejas en español no cambian (otros las usan tal cual) ──────────────────────────────────
def test_pistas_viejas_identicas():
    assert server._ai_error_hint('HTTP 404', 'gemini-x', 'GEMINI_MODEL') == (
        ' → El modelo «gemini-x» ya no existe en el proveedor (retirado). Arreglo: pon GEMINI_MODEL en Railway con '
        'un modelo vigente de su catálogo. No hace falta desplegar.')
    assert server._ai_error_hint('401 unauthorized', 'm', 'X') == ' → La key parece inválida o sin permisos para ese modelo.'
    assert server._ai_error_hint('nada', 'm', 'X') == '' and server._ai_error_fix('nada', 'm', 'X') is None
    assert server._db_error_hint('connection refused') == (
        ' → El host resuelve pero nadie escucha en ese puerto: ¿el servicio está apagado?')
    assert server._db_error_hint('???') == '' and server._db_error_fix('???') is None
    es, en = server._db_error_fix('could not translate host name "postgres.railway.internal": Name or service not known')
    assert 'REFERENCIA' in es and 'REFERENCE' in en


# ── 7. la ruta: todas las tarjetas (también las que arma ella) en los dos idiomas, sin claves ──────────────
def _route_mocks(monkeypatch):
    _with_keys(monkeypatch)
    monkeypatch.setattr(server, 'MSTACK', '', raising=False)
    monkeypatch.setattr(server, 'AV_KEY', '', raising=False)
    monkeypatch.setitem(sys.modules, 'anthropic', _fake_anthropic(lambda m: m))
    monkeypatch.setattr(server, '_complete_gemini', lambda *a, **k: (_ for _ in ()).throw(
        RuntimeError('Gemini HTTP 429 quota ' + SECRETS['GEMINI_KEY'])))
    monkeypatch.setattr(server, '_complete_nvidia', lambda *a, **k: ('pong', 'nvidia:m'))

    def get(url, *a, **k):
        if 'finnhub' in url:
            return _Resp(200, {'c': 190.1})
        if 'yahoo' in url:
            return _Resp(200, {'chart': {'result': [{'meta': {'regularMarketPrice': 180.5}}]}})
        return _Resp(500, {})
    monkeypatch.setattr(server.requests, 'get', get)
    monkeypatch.setattr(server, '_get_neo4j_driver', lambda: types.SimpleNamespace(verify_connectivity=lambda: None))
    import ontology.db as odb
    monkeypatch.setattr(odb, 'ontology_available', lambda: False)
    from core import voice_agent as va
    monkeypatch.setattr(va, 'diagnose', lambda *a, **k: {'configured': True, 'ok': True, 'detail': 'Voz lista.',
                                                         'detail_en': 'Voice ready.'})
    import research.health as rh
    monkeypatch.setattr(rh, 'research_health', lambda *a, **k: {
        'ok': False, 'hint_es': 'Todos los proveedores de IA están en pausa: gemini (sin saldo). Revisa 🩺 Sistema → IA.',
        'hint_en': 'All AI providers are paused: gemini (out of credit). Check 🩺 System → AI.',
        'providers': {'gemini': {'configured': True, 'available': False, 'circuit': {'open': True}}},
        'queue': {}, 'budget': {'research': {}}, 'scheduler': {'running': False}, 'outcomes': {}, 'last_errors': []})


def test_ruta_diagnostics_bilingue_y_sin_claves(monkeypatch):
    _route_mocks(monkeypatch)
    quotes.finnhub_pause(90)
    client = server.app.test_client()
    r = client.get('/api/diagnostics?fresh=1')
    assert r.status_code == 200
    d = r.get_json()
    raw = r.get_data(as_text=True)
    for v in SECRETS.values():
        assert v not in raw, f'filtró {v}'
    svc = d['services']
    for k in ('claude', 'gemini', 'nvidia', 'elevenlabs', 'finnhub', 'yahoo', 'fmp', 'grafo', 'ontologia', 'alpaca',
              'market_extra', 'investigacion'):
        assert svc[k].get('detail') and svc[k].get('detail_en'), k
    # Gemini en pausa (cuota) → el prefijo de la pausa también en inglés, y la pista intacta al final
    g = svc['gemini']
    assert g['detail_en'].startswith('PAUSED until ') or 'Usage limit reached' in g['detail_en']
    assert g['fix_en'] == 'Usage limit reached (quota or rate limit). Wait or upgrade the plan.'
    # Finnhub con cuota agotada → prefijo bilingüe
    f = svc['finnhub']
    assert f['quota'] is True
    assert f['detail'].startswith('Cuota agotada (HTTP 429): Finnhub en pausa')
    assert f['detail_en'].startswith('Quota used up (HTTP 429): Finnhub paused for')
    assert f['detail_en'].endswith('Valid key — AAPL quote $190.1 OK.')
    # respaldo EOD sin claves → opcional, con «Qué hacer»
    m = svc['market_extra']
    assert m['detail_en'].startswith('No EOD backup') and 'MARKETSTACK_KEY' in m['fix_en']
    # investigación caída → arreglo según la causa (aquí: todas en pausa) y reloj en inglés
    inv = svc['investigacion']
    assert inv['ok'] is False and 'server clock: OFF' in inv['detail_en']
    assert inv['fix_en'].startswith('Look at the AI cards above')
    assert 'health' in inv
    # la voz conserva lo suyo
    assert svc['elevenlabs']['detail_en'] == 'Voice ready.'
    # la tarjeta de Claude lleva el orden de las IAs en los dos idiomas
    assert '(Orden de las IAs — Profundo: ' in svc['claude']['detail']
    assert '(AI order — Deep: ' in svc['claude']['detail_en']
    assert d['summary']['total'] == len(svc)


def test_ruta_pausa_de_ia_bilingue(monkeypatch):
    _route_mocks(monkeypatch)
    # Claude responde pero NVIDIA queda en pausa por saldo (el ping de NVIDIA no lo toca en este mock)
    monkeypatch.setattr(server, '_complete_nvidia', lambda *a, **k: (_ for _ in ()).throw(
        RuntimeError('NVIDIA HTTP 402 credit balance ' + SECRETS['NVIDIA_KEY'])))
    ai._open_circuit('nvidia', 'credit', 'credit balance too low')
    d = server.app.test_client().get('/api/diagnostics?fresh=1').get_json()
    nv = d['services']['nvidia']
    assert nv['circuit']['open'] is True
    assert nv['detail'].startswith('EN PAUSA hasta ')
    assert nv['detail_en'].startswith('PAUSED until ') and 'the cascade skips it' in nv['detail_en']
    assert nv['detail_en'].endswith(' — WHAT TO DO: ' + nv['fix_en'])
    assert SECRETS['NVIDIA_KEY'] not in json.dumps(d)


# ── 8. la tarjeta REAL (app.html _diagTexts) pinta bien lo que manda el servidor, en ES y en EN ──────────
_HTML = open(os.path.join(ROOT, 'app.html'), encoding='utf-8').read()
_DIAG_JS = _HTML[_HTML.index('/* ── Estado del Sistema — diagnóstico en vivo'):_HTML.index('window.openDiagnostics = async function')]
_HARNESS = r"""
const vm = require('vm');
const out = {};
for (const lang of ['es', 'en']) {
  const ctx = { window: { LANG: lang }, out: null };
  ctx.esc = s => String(s == null ? '' : s);
  vm.createContext(ctx);
  vm.runInContext(%s + '\n;out = (s) => _diagTexts(s, _diagLevel(s));', ctx);
  const cases = %s;
  out[lang] = {};
  for (const [k, s] of Object.entries(cases)) out[lang][k] = ctx.out(s);
}
console.log(JSON.stringify(out));
"""


def test_la_tarjeta_pinta_el_arreglo_una_sola_vez(monkeypatch):
    if not NODE:
        pytest.skip('node no disponible')
    _no_keys(monkeypatch)
    monkeypatch.setattr(ai, 'CLAUDE', '')
    monkeypatch.setattr(ai, 'GEMINI_KEY', 'y' * 20)
    monkeypatch.setattr(ai, 'NVIDIA_KEY', 'z' * 20)
    cases = {'claude_off': server._diag_claude()}
    monkeypatch.setattr(server, 'GEMINI_KEY', SECRETS['GEMINI_KEY'])
    monkeypatch.setattr(server, '_complete_gemini', lambda *a, **k: (_ for _ in ()).throw(RuntimeError('Gemini HTTP 404')))
    cases['gemini_404'] = server._diag_gemini()
    monkeypatch.setattr(server, '_complete_gemini', lambda *a, **k: (_ for _ in ()).throw(RuntimeError('raro')))
    cases['gemini_raro'] = server._diag_gemini()
    import ontology.db as odb
    monkeypatch.setattr(odb, 'ontology_available', lambda: True)
    monkeypatch.setattr(odb, 'schema_outdated', lambda: ['events.source_id'])
    monkeypatch.setattr(odb, 'init_schema', lambda: False)
    cases['schema'] = server._diag_ontologia()
    js = _HARNESS % (json.dumps(_DIAG_JS), json.dumps(cases))
    r = subprocess.run([NODE, '-e', js], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    got = json.loads(r.stdout)
    for lang, fixk in (('es', 'fix_es'), ('en', 'fix_en')):
        for k, s in cases.items():
            t = got[lang][k]
            assert 'QUÉ HACER' not in t['detail'] and 'WHAT TO DO' not in t['detail'], (lang, k, t)
            if s.get(fixk):
                assert t['fixes'] == [s[fixk]], (lang, k, t)     # el arreglo UNA vez, en su idioma
    # sin arreglo y con el orden de las IAs: las flechas del orden NO se confunden con una pista
    assert got['es']['gemini_raro']['fixes'] == [] and got['en']['gemini_raro']['fixes'] == []
    c_en = got['en']['claude_off']
    assert c_en['detail'].startswith('ANTHROPIC_KEY is not in the server variables (Railway).')
    assert '(AI order — Deep: Claude' in c_en['detail'] and c_en['fixes'][0].startswith('In Railway → your service')
    c_es = got['es']['claude_off']
    assert '(Orden de las IAs — Profundo: Claude' in c_es['detail'] and c_es['fixes'][0].startswith('En Railway → tu servicio')
    assert got['en']['schema']['detail'] == 'Outdated schema: missing events.source_id. An automatic repair was attempted and failed.'
    assert got['en']['schema']['fixes'] == ['Restart the service in Railway (Deployments → Restart), then press ↻ Re-test.']
    assert got['es']['gemini_404']['fixes'][0].startswith('El modelo «')
    assert got['en']['gemini_404']['fixes'][0].startswith('The model “')
