"""core/tour.py — el guion del recorrido de un minuto, lado Python (voz para Khipus OS, 2026-10-11).

La fuente es engine/tour_script.js (la MISMA que carga el navegador como window.KHIPU_TOUR): aquí se
extrae su objeto JSON una vez. El servidor solo genera audio para ESTAS frases (GET /api/voice/tour/…),
así nadie puede pedirle a ElevenLabs texto arbitrario con la cuota de Khipus."""
import hashlib
import json
import os
import re

_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'engine', 'tour_script.js')
_RX = re.compile(r'\.KHIPU_TOUR\s*=\s*(\{.*\})\s*;\s*$', re.S)

LANGS = ('es', 'en')


def _load(path=_PATH):
    with open(path, encoding='utf-8') as fh:
        m = _RX.search(fh.read())
    if not m:
        raise ValueError('engine/tour_script.js: no encuentro "….KHIPU_TOUR = {…};"')
    return json.loads(m.group(1))


TOUR = _load()
STEPS = tuple(TOUR['steps'])
VERSION = str(TOUR.get('version') or '')


def line(step, lang):
    """Frase del paso `step` (0…N-1) en `lang` ('es'|'en'); None si no existe."""
    if lang not in LANGS or not isinstance(step, int) or not 0 <= step < len(STEPS):
        return None
    return STEPS[step].get(lang) or None


def text_hash(text):
    """Huella corta de una frase: entra en la clave de la caché de audio (si el guion cambia, el audio también)."""
    return hashlib.sha1(str(text or '').encode('utf-8')).hexdigest()[:16]
