"""tests/test_repair_logs.py — O2 (misión de reparación 2026-10-04): logs
estructurados con LOG_JSON=on, sin cambiar nada en modo texto."""
import io
import json
import logging
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _logger_to(buf, json_on):
    from core.logjson import JsonFormatter
    lg = logging.getLogger('khipu.test.o2')
    lg.handlers[:] = []
    h = logging.StreamHandler(buf)
    h.setFormatter(JsonFormatter() if json_on else logging.Formatter('%(message)s'))
    lg.addHandler(h)
    lg.setLevel(logging.INFO)
    lg.propagate = False
    return lg


def test_o2_modo_texto_no_cambia_y_no_emite_eventos(monkeypatch):
    from core import logjson
    monkeypatch.delenv('LOG_JSON', raising=False)
    assert logjson.enabled() is False and logjson.configure(logging.getLogger('khipu.test.none')) is False
    buf = io.StringIO()
    ev = logging.getLogger(logjson.EVENT_LOGGER)
    h = logging.StreamHandler(buf); ev.addHandler(h)
    try:
        logjson.event('ai_call', provider='gemini', ms=10)
    finally:
        ev.removeHandler(h)
    assert buf.getvalue() == ''


def test_o2_json_con_contexto_y_campos(monkeypatch):
    from core import logjson
    monkeypatch.setenv('LOG_JSON', 'on')
    buf = io.StringIO()
    lg = _logger_to(buf, True)
    with logjson.log_context(job_id='j1', entity='TSMC'):
        lg.warning('research run %s/%s: %s', 'TSMC', 'news', 'boom')   # mensaje de texto IGUAL que antes
    d = json.loads(buf.getvalue().strip())
    assert d['msg'] == 'research run TSMC/news: boom'
    assert d['job_id'] == 'j1' and d['entity'] == 'TSMC' and d['level'] == 'WARNING' and d['ts']


def test_o2_contexto_viaja_a_los_hilos_del_pool(monkeypatch):
    from core import logjson
    from core.ai_usage import bind
    monkeypatch.setenv('LOG_JSON', 'on')
    seen = {}
    with logjson.log_context(job_id='j2', entity='NVDA'):
        fn = bind(lambda: seen.update(logjson.current_fields(), thread=threading.current_thread().name))
    with ThreadPoolExecutor(1) as ex:
        ex.submit(fn).result()
    assert seen['job_id'] == 'j2' and seen['entity'] == 'NVDA'


def test_o2_cada_llamada_de_ia_deja_un_evento(monkeypatch):
    from core import ai_usage, logjson
    monkeypatch.setenv('LOG_JSON', 'on')
    monkeypatch.setattr(ai_usage, '_ensure_writer', lambda: None)
    buf = io.StringIO()
    ev = logging.getLogger(logjson.EVENT_LOGGER)
    h = logging.StreamHandler(buf); h.setFormatter(logjson.JsonFormatter())
    ev.addHandler(h); ev.setLevel(logging.INFO)
    try:
        with logjson.log_context(job_id='j3', agent='fundamental'):
            ai_usage.record('gemini', 'gemini-2.5-flash', 1000, 200, ok=True, ms=850)
    finally:
        ev.removeHandler(h)
    d = json.loads(buf.getvalue().strip().splitlines()[-1])
    assert d['event'] == 'ai_call' and d['provider'] == 'gemini' and d['tokens_in'] == 1000 and d['ms'] == 850
    assert d['job_id'] == 'j3' and d['agent'] == 'fundamental' and 'cost_usd' in d and d['ok'] is True
