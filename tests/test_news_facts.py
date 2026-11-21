"""tests/test_news_facts.py — la ontología se actualiza sola: noticias → hechos (Lector) → curador → ciclo automático.

Lo que se blinda: el curador NO deja pasar lo que la noticia no dice (contraparte o cifra inventadas, índice falso),
no duplica, calcula la confianza (no la dice la IA), exige prensa seria para personas clave, y el ciclo aplica solo
lo que pasa el umbral de policy.auto_apply — un vínculo entra como 'proposed' (lo confirma una persona).
"""
import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ontology import news_facts as nf  # noqa: E402

DATABASE_URL = os.getenv('DATABASE_URL', '')


class _Res:
    def __init__(self, rows=()):
        self._rows = list(rows)

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, proposals=(), link=False):
        self._p, self._link = list(proposals), link

    def execute(self, q):
        return _Res([(1,)] if self._link else [])

    def scalars(self, q):
        return _Res(self._p)


CO = SimpleNamespace(id='nvidia', label='NVIDIA', properties={'mkt': 'NVDA'})
NEWS = [
    {'title': 'TSMC to expand CoWoS capacity for Nvidia as AI demand surges', 'summary': '',
     'url': 'https://www.reuters.com/tech/tsmc-cowos', 'outlet': 'Reuters', 'date': '2026-11-20'},
    {'title': 'Nvidia signs $5 billion deal with Acme Robotics', 'summary': '',
     'url': 'https://randomblog.example/acme', 'outlet': 'randomblog.example', 'date': '2026-11-19'},
    {'title': 'Nvidia CEO health rumor spreads online', 'summary': '',
     'url': 'https://gossip.example/ceo', 'outlet': 'gossip.example', 'date': '2026-11-19'},
]
RESOLVE = {'tsmc': 'tsmc', 'acme robotics': None}.get


def _resolver(name):
    return RESOLVE(str(name).lower())


def test_link_fact_from_press_becomes_link_proposal_with_computed_confidence():
    facts = [{'kind': 'supplier', 'news': 0, 'counterpart': 'TSMC', 'text': 'TSMC amplía CoWoS para Nvidia',
              'confidence': 0.99}]
    props, dropped = nf.curate(_FakeSession(), CO, NEWS, facts, resolver=_resolver)
    assert not dropped and len(props) == 1
    p = props[0]
    assert p['action_type'] == 'ProponerVinculo'
    # supplier: la contraparte PROVEE a la empresa (dirección única source → target)
    assert (p['payload']['from_id'], p['payload']['to_id'], p['payload']['tipo']) == ('tsmc', 'nvidia', 'supply')
    assert p['payload']['fuente'].startswith('https://www.reuters.com')
    assert p['confidence'] == nf.confidence('supplier', 2, 1) == 0.55      # Reuters = prensa (trust 2)
    assert p['payload']['metadata']['evidence'][0]['date'] == '2026-11-20'


def test_invented_counterpart_amount_or_index_are_dropped():
    facts = [{'kind': 'customer', 'news': 0, 'counterpart': 'Samsung', 'text': 'x'},       # no está en el titular
             {'kind': 'deal', 'news': 1, 'amount': '$9 billion', 'text': 'x'},              # la cifra es 5, no 9
             {'kind': 'deal', 'news': 7, 'text': 'x'},                                     # noticia inexistente
             {'kind': 'opinion', 'news': 0, 'text': 'x'}]                                  # tipo fuera del vocabulario
    props, dropped = nf.curate(_FakeSession(), CO, NEWS, facts, resolver=_resolver)
    assert props == [] and len(dropped) == 4


def test_unresolved_counterpart_goes_to_human_as_note():
    facts = [{'kind': 'customer', 'news': 1, 'counterpart': 'Acme Robotics', 'amount': '$5 billion', 'text': 'acuerdo'}]
    props, _ = nf.curate(_FakeSession(), CO, NEWS, facts, resolver=_resolver)
    assert len(props) == 1 and props[0]['action_type'] == 'AnotarObjeto'
    assert props[0]['confidence'] < 0.55            # bajo el umbral: lo revisa una persona
    assert 'Acme Robotics' in props[0]['payload']['texto'] and 'randomblog.example/acme' in props[0]['payload']['texto']


def test_key_person_needs_serious_press():
    facts = [{'kind': 'key_person', 'news': 2, 'text': 'rumor sobre la salud del CEO'}]
    props, dropped = nf.curate(_FakeSession(), CO, NEWS, facts, resolver=_resolver)
    assert props == [] and dropped and 'persona clave' in dropped[0][1]


def test_existing_link_or_recent_proposal_is_not_duplicated():
    facts = [{'kind': 'supplier', 'news': 0, 'counterpart': 'TSMC', 'text': 't'}]
    assert nf.curate(_FakeSession(link=True), CO, NEWS, facts, resolver=_resolver)[0] == []
    prev = SimpleNamespace(payload={'from_id': 'tsmc', 'to_id': 'nvidia', 'tipo': 'supply'})
    assert nf.curate(_FakeSession(proposals=[prev]), CO, NEWS, facts, resolver=_resolver)[0] == []


def test_confidence_is_bounded_and_rewards_corroboration():
    assert nf.confidence('supplier', 1, 1) < 0.55 <= nf.confidence('supplier', 2, 1)
    assert nf.confidence('supplier', 2, 3) > nf.confidence('supplier', 2, 1)
    assert nf.confidence('ipo', 3, 9) <= 0.9


def test_observe_does_nothing_without_ai_or_when_off(monkeypatch):
    monkeypatch.setattr(nf, '_has_ai', lambda: False)
    assert nf.LectorHechos().observe(_FakeSession()) == []
    monkeypatch.setenv('ONTOLOGY_NEWS_FACTS', 'off')
    assert nf.LectorHechos(ai_json=lambda s, p: {'facts': []}).observe(_FakeSession()) == []


def test_daily_cap(monkeypatch):
    monkeypatch.setenv('ONTOLOGY_NEWS_DAILY', '2')
    monkeypatch.setitem(nf._DAY, 'day', None)
    assert nf._take_budget() and nf._take_budget() and not nf._take_budget()


def test_agent_registered_and_never_money():
    from ontology.agents import AGENTS, SAFE_AUTO
    assert nf.NAME in [a.name for a in AGENTS]
    assert 'AjustarPosicion' not in SAFE_AUTO
    src = open(nf.__file__, encoding='utf-8').read()
    assert 'AjustarPosicion' not in src and 'brokerage' not in src


def test_server_heartbeat_is_off_in_tests_and_reuses_the_cycle(monkeypatch):
    from ontology import curation_loop as cl
    monkeypatch.setenv('KHIPU_SCHEDULER', 'off')
    assert cl.enabled() is False and cl.start() is False
    monkeypatch.setenv('KHIPU_SCHEDULER', 'on')
    monkeypatch.setenv('ONTOLOGY_AUTO', 'off')
    assert cl.enabled() is False
    src = open(cl.__file__, encoding='utf-8').read()
    assert '_try_start_cycle' in src and 'core.scheduler' not in src.replace('core/scheduler.py', '')


# ── integración con la base: lector → curador → auto_cycle ───────────────────
@pytest.fixture()
def db():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    from ontology.db import _get_engine, init_schema, session_scope
    from ontology.models import Base
    from ontology.service import apply_event
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    assert init_schema(retries=1)
    with session_scope() as s:
        for oid, label in (('nvidia', 'NVIDIA'), ('tsmc', 'TSMC'), ('amd', 'AMD')):
            apply_event(s, 'ObjectCreated', {'label': label, 'type': 'Company'}, valid_from='2000-01-01',
                        source='test', actor='pytest', object_id=oid)
        apply_event(s, 'LinkCreated', {'rel_type': 'supply', 'properties': {}}, valid_from='2000-01-01',
                    source='test', actor='pytest', object_id='nvidia', target_id='amd')
    yield engine
    Base.metadata.drop_all(engine)


def test_cycle_incorporates_press_fact_and_leaves_weak_one(db, monkeypatch):
    from sqlalchemy import select

    import ontology.agents as A
    from ontology.db import session_scope
    from ontology.models import LinkRecord, ProposedAction
    news = NEWS[:2]
    facts = {'facts': [{'kind': 'supplier', 'news': 0, 'counterpart': 'TSMC', 'text': 'TSMC amplía CoWoS para Nvidia'},
                       {'kind': 'customer', 'news': 1, 'counterpart': 'Acme Robotics', 'amount': '$5 billion',
                        'text': 'acuerdo con Acme'}]}
    lector = nf.LectorHechos(fetch=lambda c: news if c.id == 'nvidia' else [], ai_json=lambda s, p: facts,
                             resolver=_resolver)
    monkeypatch.setattr(A, 'AGENTS', [lector])
    monkeypatch.setattr(nf, '_SEEN', {})
    monkeypatch.setitem(nf._DAY, 'day', None)
    with session_scope() as s:
        out = A.auto_cycle(s)
    assert out['agents'][nf.NAME]['ok'] and out['agents'][nf.NAME]['proposals'] == 2, out
    assert [a['action'] for a in out['auto_applied']] == ['ProponerVinculo'], out
    assert out['left_for_human'] == 1
    with session_scope() as s:
        link = s.scalars(select(LinkRecord).where(LinkRecord.source_id == 'tsmc',
                                                  LinkRecord.target_id == 'nvidia')).first()
        assert link is not None and (link.properties or {}).get('status') == 'proposed'
        assert (link.properties or {}).get('via') == nf.NAME
        pend = s.scalars(select(ProposedAction).where(ProposedAction.status == 'pending')).all()
        assert [p.action_type for p in pend] == ['AnotarObjeto']
    # segunda vuelta: lo mismo no se vuelve a proponer
    monkeypatch.setattr(nf, '_SEEN', {})
    with session_scope() as s:
        out2 = A.auto_cycle(s)
    assert out2['agents'][nf.NAME]['proposals'] == 0, out2
