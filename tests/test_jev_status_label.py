"""El 💰 Gasto IA decía «MODO SOMBRA» aunque Jev ya mandaba en el chat (Fabrizio, 2026-10-13: «modo sombra dice, ¿qué
significa?»). /api/decide/status expone control_features y la UI dice «ACTIVO · manda en el chat»."""
import os


def test_status_expone_control_features(monkeypatch):
    monkeypatch.setenv('TYPESAFE_API_KEY', 'k-test')
    monkeypatch.delenv('DECIDE_CONTROL', raising=False)
    import server
    j = server.app.test_client().get('/api/decide/status').get_json()
    assert j['available'] is True and 'chat_gate' in j['control_features']


def test_status_sin_clave_no_manda(monkeypatch):
    monkeypatch.delenv('TYPESAFE_API_KEY', raising=False)
    monkeypatch.delenv('TYPESAFE_KEY', raising=False)
    import server
    j = server.app.test_client().get('/api/decide/status').get_json()
    assert j['available'] is False and j['control_features'] == []


def test_ui_dice_activo_cuando_manda():
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'engine', 'aispend.js'),
               encoding='utf-8').read()
    assert "ACTIVO · manda en " in src and "ACTIVE · in control of " in src
    assert "MODO SOMBRA · solo compara" in src and "SHADOW MODE · compares only" in src
