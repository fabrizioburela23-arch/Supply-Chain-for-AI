"""La ventana de Mercado mostraba «Error al obtener precios: Keys is not defined» (2026-10-13, hallado al partir app.html):
fetchQuotes usaba `Keys`, que solo existe dentro del IIFE de V8. Debe leerse por window.V8.Keys."""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_fetchquotes_no_usa_keys_fuera_del_iife():
    src = open(os.path.join(ROOT, 'engine', 'app_main.js'), encoding='utf-8').read()
    i = src.find('async function fetchQuotes')
    if i < 0:
        i = src.find('function fetchQuotes')
    assert i >= 0, 'fetchQuotes no encontrada'
    end = src.find('\nconst Keys = {')
    body = src[i:end if end > i else i + 6000]
    assert not re.search(r'(?<![\w.])Keys\.has\(', body), 'fetchQuotes usa Keys fuera de su alcance'
    assert 'window.V8.Keys' in body
