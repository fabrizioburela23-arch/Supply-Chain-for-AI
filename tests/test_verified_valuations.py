"""Una sola valuación por empresa privada (2026-10-05): la auditoría encontró Anthropic con TRES valuaciones en la
misma ficha ($965B verificada, "$350B (2025)" y "$60B" del catálogo) y la de $60B entraba en el valor de las carteras.
app.html:applyVerifiedValuations hace que NODE_META, PREIPO_INTEL e INVEST_PATH usen nodes/private_valuations.js."""
import json
import os
import re
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = shutil.which('node')


def _fn():
    h = open(os.path.join(ROOT, 'app.html'), encoding='utf-8').read()
    m = re.search(r'function applyVerifiedValuations\(\)\{[\s\S]*?\n\}\n', h)
    assert m, 'applyVerifiedValuations no está en app.html'
    return m.group(0)


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_valuacion_verificada_unica_en_ficha_panel_cartera_y_notas():
    js = """
    global.window = {};
    global.document = { addEventListener: () => {} };
    window.PRIVATE_VALUATIONS = { entries: {
      Anthropic: { valuation_usd_b: 965, as_of: '2026-05-28', label: '$965B (2026-05-28)', source_url: 'https://x' },
      Databricks: { valuation_usd_b: 190, as_of: '2026-08-13', label: '$190B (2026-08-13)' },
      Cerebras: { valuation_usd_b: 8, as_of: '2025-01', label: '$8B (2025-01)' } } };
    window.PREIPO_INTEL = { Anthropic: { valuation: '$350B (2025)' }, xAI: { valuation: '~$2T combinada' } };
    global.NODE_META = { Anthropic: { mktcap_b: 60 }, Cerebras: { mktcap_b: 30 }, xAI: { mktcap_b: 50 } };
    global.INVEST_PATH = { Databricks: { note: 'Pre-IPO. Valoración ~$62B (2024). IPO anticipada.' },
                           Cerebras: { note: 'IPO realizada en Nasdaq 2024' } };
    global.NODE_BY_ID = { Anthropic: { id: 'Anthropic', preipo: true }, Databricks: { id: 'Databricks', preipo: true },
      Cerebras: { id: 'Cerebras', listing: { status: 'public', note_es: 'Salió a bolsa en Nasdaq (CBRS) el 14-may-2026.' } },
      xAI: { id: 'xAI', listing: { status: 'merged', parent: 'SpaceX', note_es: 'Se fusionó con SpaceX; cotiza como SPCX.' } } };
    window.NODE_BY_ID = NODE_BY_ID;
    """ + _fn() + """
    applyVerifiedValuations(); applyVerifiedValuations();   // idempotente (se aplica 2 veces al cargar)
    process.stdout.write(JSON.stringify({ meta: NODE_META, pi: window.PREIPO_INTEL, ip: INVEST_PATH }));
    """
    r = subprocess.run([NODE, '-e', js], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    o = json.loads(r.stdout)
    a = o['meta']['Anthropic']
    assert a['mktcap_b'] == 965 and a['mktcap_catalog'] == 60 and a['mktcap_verified']['as_of'] == '2026-05-28'
    assert o['pi']['Anthropic']['valuation'] == '$965B (2026-05-28)' and o['pi']['Anthropic']['valuation_catalog'] == '$350B (2025)'
    assert o['meta']['Databricks']['mktcap_b'] == 190
    assert o['ip']['Databricks']['note'] == 'Pre-IPO. Valuación verificada $190B (2026-08-13). IPO anticipada.'
    assert o['meta']['Cerebras']['mktcap_b'] == 30                      # cotizada: manda el precio en vivo, no la ronda vieja
    assert o['ip']['Cerebras']['note'].startswith('Salió a bolsa en Nasdaq (CBRS)')
    assert o['meta']['xAI']['mktcap_b'] is None and 'SpaceX' in o['pi']['xAI']['valuation']   # fusionada: sin valuación propia vieja
