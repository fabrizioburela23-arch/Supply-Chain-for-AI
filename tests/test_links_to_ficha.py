"""scripts/links_to_ficha.py (2026-10-26, piloto de engrosar vínculos con agentes): vínculos investigados → ficha mínima por
empresa existente que entra por el importador (fusiona sin pisar lo curado)."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
os.environ.setdefault('SECRET_KEY', 'test')

import links_to_ficha as L  # noqa: E402

GOOD = {'company_id': 'symbotic', 'counterparty_name': 'Walmart', 'counterparty_khipus_id': 'Walmart',
        'rel_type': 'supply', 'this_role': 'supplier', 'product': 'Automatización de almacenes',
        'label_es': 'Symbotic → Walmart', 'label_en': 'Symbotic → Walmart', 'status': 'active', 'criticality': 4,
        'confidence': 0.95, 'source_url': 'https://www.sec.gov/x/10k.htm', 'source_kind': 'primary', 'as_of': '2025-11',
        'quote': 'Walmart accounted for 85% of our revenue'}


def _run(tmp_path, links, min_conf=0.2):
    f = tmp_path / 'o.json'
    f.write_text(json.dumps({'links': links}))
    return L.build([str(f)], min_conf=min_conf)


def test_reglas_de_limpieza(tmp_path):
    bad_role = dict(GOOD, this_role='investor')
    no_quote = dict(GOOD, quote='')
    rumor = dict(GOOD, counterparty_name='Otra Corp', counterparty_khipus_id=None, source_kind='rumor', confidence=0.8)
    press = dict(GOOD, counterparty_name='Tercera Corp', counterparty_khipus_id=None, source_kind='press', confidence=0.99)
    fichas, res = _run(tmp_path, [GOOD, GOOD, bad_role, no_quote, rumor, press])
    assert res['companies'] == 1 and res['links'] == 3 and res['dropped'] == {'rel_type/this_role': 1, 'sin fuente o cita': 1}
    rels = {r['counterparty']['name']: r for r in fichas[0]['relations']}
    assert rels['Walmart']['confidence'] == 0.95 and rels['Walmart']['dependency']['criticality'] == 4
    assert rels['Otra Corp']['confidence'] == 0.3 and rels['Otra Corp']['status'] == 'rumored'
    assert rels['Tercera Corp']['confidence'] == 0.89        # ≥ 0,9 solo con fuente primaria
    _f, res2 = _run(tmp_path, [rumor], min_conf=0.4)         # el rumor (0,3) no pasa el piso por defecto
    assert res2['links'] == 0 and res2['dropped'] == {'confianza baja': 1}


def test_la_ficha_valida_y_fusiona_con_la_empresa_existente(tmp_path):
    from ontology import company_import as CI
    fichas, _ = _run(tmp_path, [GOOD])
    san, _l, _s = CI.sanitize_batch(fichas)
    valid, invalid = CI.validate_batch(san)
    assert len(valid) == 1 and not invalid
    plan = CI.plan(san, [], batch='t', what_changes=False)
    it = plan['items'][0]
    assert it['action'] == 'merge' and it['id'] == 'symbotic' and not it['conflicts']
