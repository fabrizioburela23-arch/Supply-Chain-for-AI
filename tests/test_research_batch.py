"""scripts/research_batch.py (2026-10-22): investiga empresas con la API de Claude y guarda SOLO fichas que pasan el
mismo saneador + validador del importador; un turno pausado se retoma y una ficha inválida vuelve a la IA con sus
errores una vez. Aquí con un cliente FALSO (sin red ni gasto)."""
import gzip
import json
import os
import sys
from types import SimpleNamespace as NS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
os.environ.setdefault('SECRET_KEY', 'test')

import research_batch as R  # noqa: E402


def _good():
    with gzip.open(os.path.join(ROOT, 'data/import/lotes/2026-10-22/bundle_lote6_s.json.gz'), 'rt') as fh:
        return json.load(fh)['records'][0]


class FakeClient:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []
        self.beta = NS(messages=NS(stream=self._stream))

    def _stream(self, **kw):
        self.calls.append(kw)
        stop, text = self.replies.pop(0)
        usage = NS(input_tokens=1000, output_tokens=2000, cache_creation_input_tokens=0, cache_read_input_tokens=60000,
                   server_tool_use=NS(web_search_requests=3))
        msg = NS(stop_reason=stop, content=[NS(type='text', text=text)], usage=usage)

        class Ctx:
            def __enter__(self):
                return NS(get_final_message=lambda: msg)

            def __exit__(self, *a):
                return False
        return Ctx()


def _args():
    return NS(model='claude-opus-5-5', effort='medium', max_searches=8, max_fetches=6)


def test_pausa_y_correccion_hasta_una_ficha_valida(tmp_path):
    good = _good()
    bad = dict(good)
    bad.pop('identity')
    cli = FakeClient([('pause_turn', ''), ('end_turn', json.dumps(bad)), ('end_turn', json.dumps(good))])
    spend = R.Spend('claude-opus-5-5', str(tmp_path / 'c.json'))
    rec, errs, usd = R.research_one(cli, _args(), 'SYS', {'nombre': 'X', 'khipus_id_hint': 'X'}, 0, spend)
    assert errs == [] and rec['record_id'] == good['record_id']
    assert len(cli.calls) == 3
    fix = cli.calls[2]['messages'][-1]['content']
    assert 'NO valida' in fix and 'identity' in fix
    # costo estimado: 1000×4 + 2000×20 + 60000×0,20 por millón + 3 búsquedas × 0,01, por llamada
    assert round(usd, 4) == round(3 * ((1000 * 4 + 2000 * 20 + 60000 * 0.2) / 1e6 + 0.03), 4)
    kw = cli.calls[0]
    assert kw['tools'][0]['type'] == 'web_search_20260209' and kw['system'][0]['cache_control']['type'] == 'ephemeral'


def test_ficha_irreparable_no_se_guarda(tmp_path):
    cli = FakeClient([('end_turn', 'no encontré nada'), ('end_turn', '{"schema": "khipus.company/1"}')])
    rec, errs, _ = R.research_one(cli, _args(), 'SYS', {'nombre': 'X', 'khipus_id_hint': 'X'}, 0,
                                  R.Spend('claude-opus-5-5', str(tmp_path / 'c.json')))
    assert errs and len(cli.calls) == 2


def test_lista_de_pendientes_no_repite_lo_ya_investigado():
    known = R.known_entities()
    assert R.norm('HongShan') in known and R.norm('Hithium') in known
    assert R.hint_of('ASML Berlin (ex Berliner Glas)') == 'ASMLBerlin'
    assert R.hint_of('Aecc Aviation Power Co.,Ltd') == 'AeccAviationPower'


def test_el_prompt_lleva_reglas_categorias_entidades_y_esquema():
    s = R.system_prompt()
    for frag in ('UN DATO INVENTADO ES PEOR', 'CATEGORÍAS VÁLIDAS', 'aerospace_components', 'ENTIDADES KHIPUS',
                 'ESQUEMA company.schema.json', 'PLANTILLA'):
        assert frag in s, frag
    assert 'lote3_100_empresas.csv' not in s


def test_engrosar_pide_vinculos_y_conserva_el_id_existente(tmp_path):
    row = {'khipus_id': 'AAON', 'nombre': 'AAON', 'pais': 'US', 'cotiza': 'AAON', 'vinculos': '0'}
    p = R.enrich_prompt(row, 0)
    assert 'YA EXISTE' in p and 'khipus_id_hint "AAON"' in p and 'fb-2026-enr-aaon' in p and '6 a 15 vínculos' in p
    cli = FakeClient([('end_turn', json.dumps(_good()))])
    R.research_one(cli, _args(), 'SYS', row, 0, R.Spend('claude-sonnet-5-5', str(tmp_path / 'c.json')))
    assert 'ENGROSAR' in cli.calls[0]['messages'][0]['content']


def test_lista_de_engrosar_prioriza_las_que_cotizan(monkeypatch, tmp_path):
    monkeypatch.setattr(R, 'OUT_DIR', str(tmp_path))
    monkeypatch.setattr(R, 'ENR_CSV', str(tmp_path / 'e.csv'))
    R.make_enrich_list()
    import csv
    rows = list(csv.DictReader(open(tmp_path / 'e.csv', encoding='utf-8')))
    assert len(rows) > 500
    first_unlisted = next(i for i, r in enumerate(rows) if not r['cotiza'])
    assert all(r['cotiza'] for r in rows[:first_unlisted]) and all(int(r['vinculos']) <= 2 for r in rows)
