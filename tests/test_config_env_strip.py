"""Variables de modelo pegadas en Railway con saltos de línea o espacios (2026-10-13: AI_MODEL_DEEP llegó como
'claude-sonnet-5-5\\n\\n\\n\\n') no deben convertirse en un id de modelo inválido; y el respaldo Pro de Gemini usa su id
real (gemini-3.1-pro-preview)."""
import os


def _reload_config(monkeypatch, **env):
    """Carga una COPIA aislada de core/config.py con el entorno dado (no toca sys.modules['core.config'], que
    otros módulos ya importaron)."""
    import importlib.util
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'core', 'config.py')
    spec = importlib.util.spec_from_file_location('_khipu_config_copy', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_modelos_sin_espacios_ni_saltos(monkeypatch):
    cfg = _reload_config(monkeypatch, AI_MODEL_FAST=' claude-sonnet-5-5 \n', AI_MODEL_DEEP='claude-sonnet-5-5\n\n\n\n',
                         GEMINI_MODEL='gemini-3.8-flash\n', NVIDIA_MODEL='  nvidia/x  ')
    assert cfg.AI_MODEL_FAST == 'claude-sonnet-5-5'
    assert cfg.AI_MODEL_DEEP == 'claude-sonnet-5-5'
    assert cfg.GEMINI_MODEL == 'gemini-3.8-flash'
    assert cfg.NVIDIA_MODEL == 'nvidia/x'


def test_vacio_o_solo_espacios_usa_el_defecto(monkeypatch):
    cfg = _reload_config(monkeypatch, AI_MODEL_FAST='\n  \n', AI_MODEL_DEEP='', GEMINI_FALLBACK_MODEL='   ')
    assert cfg.AI_MODEL_FAST == 'claude-haiku-4-5'
    assert cfg.AI_MODEL_DEEP == 'claude-sonnet-5-5'
    assert 'gemini-3.1-pro-preview' in cfg.GEMINI_FALLBACK_MODEL


def test_respaldo_por_defecto_usa_el_id_real_del_pro(monkeypatch):
    monkeypatch.delenv('GEMINI_FALLBACK_MODEL', raising=False)
    cfg = _reload_config(monkeypatch)
    ids = [m.strip() for m in cfg.GEMINI_FALLBACK_MODEL.split(',')]
    assert 'gemini-3.1-pro-preview' in ids and 'gemini-3.1-pro' not in ids
