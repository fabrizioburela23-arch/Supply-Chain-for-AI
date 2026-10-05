"""Simulación (2026-10-05): el contexto que leen los agentes de IA era FIJO ("Geopolitical Context (2026)",
narrativas de redes inventadas) y los presets usaban cifras viejas (OpenAI IPO a $250B, SpaceX a $500B)."""
import json
import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = shutil.which('node')

JS = r"""
global.window = {};
global.BASE = '';
global.NODE_BY_ID = { Nvidia: { id: 'Nvidia', label: 'Nvidia' } };
window.PRIVATE_VALUATIONS = { entries: { OpenAI: { label: '$852B (2026-03-31)', as_of: '2026-03-31' } } };
window.NODE_META = { SpaceX: { mktcap_b: 1650.4, mktcap_live: { as_of: 'x' } } };
global.fetch = async (url) => ({ ok: true, json: async () => (
  url.includes('/api/world/brief') ? { items: [{ layer: 'shipping', title_en: 'Strait of Hormuz: ▼ 64% transits', severity: 100, time: '2026-09-27T00:00:00Z', source_en: 'IMF PortWatch' }] } :
  url.includes('/api/world/gpr') ? { ok: true, daily: { value: 141.5, date: '2026-10-05', avg30: 167.3, percentile_1y: 39 } } :
  url.includes('/api/world/policy') ? { items: [{ time: '2026-09-30', agency: 'BIS', title: 'Additions to the Entity List' }] } :
  url.includes('/api/news/gdelt') ? [] : {}) });
const src = require('fs').readFileSync(process.argv[1] + '/sim/scenario_builder.js', 'utf8');
eval(src + '\n;global.__g = buildGeopoliticalContext; global.__s = buildSocialContext; global.__SB = ScenarioBuilder;');
(async () => {
  const g = await __g(), soc = await __s(['Nvidia']);
  process.stdout.write(JSON.stringify({ g, soc, oa: __SB.PRESETS.openai_ipo_impact.description, oaT: __SB.PRESETS.openai_ipo_impact.title,
                                        ss: __SB.PRESETS.starshield_reveal.description }));
})();
"""


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_contexto_en_vivo_y_presets_con_cifras_verificadas():
    r = subprocess.run([NODE, '-e', JS, ROOT], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    o = json.loads(r.stdout)
    assert 'Geopolitical Context (LIVE' in o['g'] and '141.5' in o['g'] and 'Hormuz' in o['g'] and 'Entity List' in o['g']
    assert 'Structural background' in o['g'] and 'Geopolitical Context (2026)' not in o['g']
    assert 'AI bubble' not in o['soc'] and 'do not invent' in o['soc']          # sin narrativas inventadas
    assert '$250B' not in o['oaT'] + o['oa'] and '$852B' in o['oa']
    assert '$500B' not in o['ss'] and 'SPCX' in o['ss'] and '$1650B live market cap' in o['ss']
