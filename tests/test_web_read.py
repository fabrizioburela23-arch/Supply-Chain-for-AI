"""tests/test_web_read.py — el chat busca y LEE la web sin Tavily (2026-11-04): las herramientas de servidor de Anthropic
(web_search / web_fetch) con la MISMA ANTHROPIC_KEY, por core/ai.py (control de gasto, cupo y corta-circuito de siempre)."""
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('SECRET_KEY', 'test')


class _Cite:
    def __init__(self, url, title, text):
        self.url, self.title, self.cited_text = url, title, text


class _Block:
    def __init__(self, text, cites=()):
        self.type, self.text, self.citations = 'text', text, list(cites)


class _Msg:
    def __init__(self, blocks, stop='end_turn'):
        self.content, self.stop_reason, self.model = blocks, stop, 'claude-sonnet-5-5'
        self.usage = types.SimpleNamespace(input_tokens=100, output_tokens=50)


@pytest.fixture
def fake_claude(monkeypatch):
    calls = []

    class _Client:
        def __init__(self, **kw):
            self.messages = self

        def create(self, **kw):
            calls.append(kw)
            if len(calls) == 1 and kw['tools'][0]['name'] == 'web_search':
                return _Msg([], stop='pause_turn')                      # búsqueda larga: se retoma
            return _Msg([_Block('Nvidia reported revenue of $57.0 billion.',
                                [_Cite('https://nvidianews.nvidia.com/q3', 'Q3 FY26', 'revenue of $57.0 billion')])])

    import anthropic
    from core import ai
    monkeypatch.setattr(anthropic, 'Anthropic', _Client)
    monkeypatch.setattr(ai, 'CLAUDE', 'sk-test')
    monkeypatch.setattr(ai, 'provider_available', lambda p: True)
    return calls


def test_busqueda_sin_tavily_usa_claude_y_devuelve_tramos_citados(fake_claude, monkeypatch):
    from core import websearch
    monkeypatch.setattr(websearch, 'TAVILY_KEY', '')
    assert websearch._web_search_available()
    res = websearch.web_search('Nvidia Q3 revenue')
    assert res and res[0]['url'] == 'https://nvidianews.nvidia.com/q3' and '57.0' in res[0]['content']
    assert fake_claude[0]['tools'][0]['type'] == 'web_search_20260209' and len(fake_claude) == 2   # retomó la pausa


def test_read_url_lee_la_pagina(fake_claude):
    from core import khipu_chat as K
    out = K.x_read_url('https://nvidianews.nvidia.com/q3')
    assert '57.0' in out['content'] and out['url'].startswith('https://')
    assert fake_claude[0]['tools'][0]['type'] == 'web_fetch_20260209'


@pytest.mark.parametrize('bad', ['ftp://x.com/a', 'nvidia.com', 'http://localhost:8080/admin', 'http://10.0.0.5/x',
                                 'http://192.168.1.1/', 'http://metadata.internal/latest', 'http://[::1]/'])
def test_read_url_rechaza_direcciones_no_publicas(bad, fake_claude):
    from core import khipu_chat as K
    with pytest.raises(K.ToolFailure):
        K.x_read_url(bad)
    assert not fake_claude                                  # ni siquiera se llamó a la IA


def test_herramientas_en_el_catalogo_y_receta():
    from core import khipu_chat as K
    assert 'read_url' in K._EXTRA and 'web_search' in K._EXTRA
    src = open(K.__file__, encoding='utf-8').read()
    assert 'UN ENLACE pegado' in src and 'Nunca digas «no tengo acceso a internet»' in src
