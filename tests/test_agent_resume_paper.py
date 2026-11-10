"""Tras una actualización, el agente de PAPEL que estaba encendido se reanuda solo; con dinero real queda APAGADO
(2026-11-07: la prueba en papel nunca corrió porque cada despliegue lo apagaba)."""
import contextlib
import datetime as dt
import types

import pytest

from core import trading_agent as ta


class _Res:
    def __init__(self, row):
        self.row = row

    def first(self):
        return self.row


class _Sess:
    def __init__(self, row):
        self.row = row

    def execute(self, *a, **k):
        return _Res(self.row)


@pytest.fixture
def boot(monkeypatch):
    persisted, launched = [], []
    row = ({'config': {'mode': 'auto', 'universe': ['NVDA', 'AMD'], 'interval_min': 60}, 'running': True},
           dt.datetime(2026, 11, 7, tzinfo=dt.timezone.utc))
    import ontology.db as odb
    monkeypatch.setattr(odb, 'ontology_available', lambda: True)
    monkeypatch.setattr(odb, 'session_scope', lambda: contextlib.nullcontext(_Sess(row)))
    monkeypatch.setattr(ta, '_agent_persist', lambda running, reason, principal=None: persisted.append((running, reason)))
    monkeypatch.setattr(ta, '_launch_locked', lambda: (launched.append(1), ta._AGENT.__setitem__('running', True)))
    monkeypatch.setitem(ta._AGENT_RESTORE, 'done', False)
    monkeypatch.setitem(ta._AGENT, 'running', False)
    monkeypatch.setitem(ta._AGENT, 'log', [])
    ta._AGENT.pop('notice', None)

    def host(paper):
        monkeypatch.setattr(ta, '_S', types.SimpleNamespace(ALPACA_KEY='k', _paper=lambda: paper,
                                                            _safe_ticker=lambda t: str(t).upper()), raising=False)
    return host, persisted, launched


def test_papel_se_reanuda_solo(boot, monkeypatch):
    host, persisted, launched = boot
    monkeypatch.delenv('AGENT_RESUME_PAPER', raising=False)
    host(True)
    ta._agent_restore()
    assert launched and ta._AGENT['running'] and persisted[-1] == (True, 'resumed_after_restart')
    assert 'notice' not in ta._AGENT and ta._AGENT['universe'] == ['NVDA', 'AMD']


def test_dinero_real_queda_apagado(boot, monkeypatch):
    host, persisted, launched = boot
    monkeypatch.delenv('AGENT_RESUME_PAPER', raising=False)
    host(False)
    ta._agent_restore()
    assert not launched and not ta._AGENT['running'] and persisted[-1] == (False, 'stopped_by_restart')
    assert ta._AGENT['notice']['es'].startswith('⏸') and ta._AGENT['mode'] == 'manual'   # AUTO nunca con dinero real


def test_interruptor_apaga_la_reanudacion(boot, monkeypatch):
    host, persisted, launched = boot
    monkeypatch.setenv('AGENT_RESUME_PAPER', 'off')
    host(True)
    ta._agent_restore()
    assert not launched and persisted[-1] == (False, 'stopped_by_restart')
