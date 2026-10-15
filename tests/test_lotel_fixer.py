"""tests/test_lotel_fixer.py — revisión del lote L (2026-10-15, 386 empresas completas): lo que el arreglador cambió.

  · un PENDIENTE que se resuelve cuando llega su contraparte sigue las MISMAS reglas que un vínculo nuevo (antes todo
    pendiente resuelto por id entraba VIVO: participaciones sin %, owns sin % de control, confianza < 0,5, fuente débil);
  · las participaciones pendientes guardan su papel (this_role) y no hay lazos a sí misma (Brookfield → Brookfield);
  · el plan cuenta los vínculos vivos con peso POR DEFECTO de la política (owns 2, socio/inversor 37);
  · «¿qué cambia?»: vínculos antes y después con la MISMA medida (entradas de las matrices del kernel);
  · `margin` de una empresa importada = margen OPERATIVO (nunca el bruto); año fiscal rotulado con el año en que
    EMPIEZA = aviso (no se cambia el número);
  · Boeing no hereda el CEDEAR «BAC.BA» (de Bank of America);
  · live_caps publica el catálogo primero tras un despliegue (sin esperar el minuto del tope de Yahoo);
  · el panel 📥 no retiene el paquete parseado en memoria;
  · cliente: la banda de categorías se rehace tras el catálogo de la base, las importadas no entran en la ronda de
    precios sin tope, la ficha dice «sin dato» / «ficha importada» y el panel pide recargar tras aplicar/deshacer."""
import collections
import json
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('KHIPU_SCHEDULER', 'off')

from ontology import company_import as CI  # noqa: E402

LOTE = os.path.join(ROOT, 'data', 'import', 'lotes', '2026-10-15')


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as fh:
        return fh.read()


@pytest.fixture(scope='module')
def view():
    """El grafo de los lectores desde el SNAPSHOT (sin base)."""
    import ontology.db as odb
    from core.hotviews import hot, registry
    real = odb.ontology_available
    odb.ontology_available = lambda: False
    try:
        registry.reset()
        hot.reset()
        v = hot.graph()
    finally:
        odb.ontology_available = real
    assert v is not None and len(v.nodes) >= 900
    return v


@pytest.fixture(scope='module')
def bundle():
    return CI.load_bundle(os.path.join(LOTE, CI.LOTE2_BUNDLE))


@pytest.fixture(scope='module')
def lote_plan(bundle, view):
    return CI.plan(bundle['records'], bundle['updates'], view=view, batch=bundle['batch'], what_changes=True)


# ── pendientes que se resuelven: las mismas reglas ────────────────────────────────────────────────────────────────
_F = {'source_url': 'https://www.gleif.org/lei/x', 'source_kind': 'primary', 'as_of': '2026-10', 'confidence': 0.9}


def _arrival(n, hint, lei=None):
    """Ficha sintética mínima de una contraparte que «llega» (nombre neutro: se encuentra por id o LEI, nunca por nombre)."""
    name = f'Zeta Arrival Holdings {n:03d}'
    return {'schema': 'khipus.company/1', 'record_id': f'fx-arrival-{n:03d}', 'khipus_id_hint': hint,
            'research_meta': {'researcher': 'test', 'researched_at': '2026-10-15T00:00:00Z', 'method': 'manual',
                              'tier': 'B', 'batch': 'fx-arrival'},
            'identity': {'legal_name': {'value': name, **_F}, 'short_name': name, 'status': {'value': 'private', **_F},
                         'hq_country': {'value': 'US', **_F}, 'ids': {'lei': lei} if lei else {}},
            'classification': {'cat': 'foundry'},
            'profile': {'summary': {'value': 'Ficha sintética de prueba', 'value_en': 'Synthetic test record', **_F}}}


def _expected_route(props, method):
    """Las reglas del plan (policy.import 1.1.0) escritas a mano, independientes del código."""
    if props.get('status') in ('rumored', 'disputed'):
        return 'proposed'
    if str(method).startswith('name'):
        return 'proposed'
    if props.get('share_pct_known') is False:
        return 'proposed'
    if float(props.get('confidence') or 0) < 0.5 or props.get('verified') is not True:
        return 'proposed'
    if props.get('criticality_source') == 'default_owns' and (props.get('criticality_pct') is None
                                                               or float(props['criticality_pct']) < 50):
        return 'proposed'
    return 'live'


@pytest.fixture(scope='module')
def arrival_case(lote_plan, view):
    from core.import_normalize import is_khipus_id
    _evs, pend, _quar = CI.events_of(lote_plan, 'run-fx')
    rows = [dict(q, id=f'pend-{i:04d}', run_id='run-fx') for i, q in enumerate(pend)]
    kids, leis = [], []
    for q in rows:
        cp = q['counterparty'] or {}
        k = cp.get('khipus_id')
        if k and is_khipus_id(k) and k not in view.by_id and k not in kids:
            kids.append(k)
        lei = (cp.get('ids') or {}).get('lei')
        if not k and lei and lei not in leis:
            leis.append(lei)
    arr = [_arrival(i, k) for i, k in enumerate(kids)] + [_arrival(500 + i, f'ZetaArrival{i:03d}', lei)
                                                           for i, lei in enumerate(leis)]
    p2 = CI.plan(arr, [], view=view, batch='fx-arrival', pending=rows, what_changes=False)
    return {r['id']: r for r in rows}, p2


def test_pendiente_resuelto_sigue_las_reglas_del_plan(arrival_case):
    rows, p2 = arrival_case
    res = p2['pending_resolved']
    assert len(res) >= 300
    by = collections.Counter((r['route'], r.get('route_reason')) for r in res)
    for want in ('holding_without_pct', 'owns_without_control_pct', 'source_trust_low', 'low_confidence'):
        assert by[('proposed', want)] >= 1, by
    assert by[('live', 'ok')] >= 100, by
    for r in res:
        src_row = rows[r['from_pending']]
        old = src_row['payload']['properties']
        method = (src_row['counterparty'] or {}).get('how') or ''
        assert r['route'] == _expected_route(old, 'ids' if not method.startswith('name') else method), (r['from_pending'], r['route'], old)
        props = r['properties']
        if r['route'] == 'proposed':
            assert props['status'] == 'proposed' and props['proposed'] is True and props['confidence'] == 0.0
            assert props['proposed_reason'] == r['route_reason']
        else:
            assert props.get('status') != 'proposed' and props.get('verified') is True and props['confidence'] >= 0.5


def test_participacion_pendiente_se_resuelve_con_el_dueno_como_origen(arrival_case):
    rows, p2 = arrival_case
    seen = 0
    for r in p2['pending_resolved']:
        row = rows[r['from_pending']]
        role = row['payload']['properties'].get('this_role')
        if not str(row['relation_id']).startswith('holding-'):
            continue
        assert role in ('owned', 'owner'), row['relation_id']
        if role == 'owned':
            assert r['target'] == row['company_id'] and r['source'] != row['company_id']
        else:
            assert r['source'] == row['company_id']
        seen += 1
    assert seen >= 10


def test_ninguna_participacion_queda_sin_papel_ni_apunta_a_si_misma(lote_plan):
    for it in lote_plan['items']:
        for l in it['links']:
            assert not (l.get('source') and l.get('source') == l.get('target')), (it['record_id'], l['relation_id'])
            if str(l['relation_id']).startswith('holding-') and l['route'] in ('pending', 'proposed', 'live'):
                assert (l.get('properties') or {}).get('this_role') in ('owned', 'owner'), (it['record_id'], l['relation_id'])
    bam = next(it for it in lote_plan['items'] if it['record_id'] == 'fb-2026-brookfield-asset-management')
    h1 = next(l for l in bam['links'] if l['relation_id'] == 'holding-001')
    assert h1.get('source') != 'Brookfield' or h1.get('target') != 'Brookfield'
    assert h1['route'] in ('pending', 'quarantine')              # «Brookfield Corporation» ≠ BAM (3_fusionar_con_existentes)


# ── conteos y «¿qué cambia?» ─────────────────────────────────────────────────────────────────────────────────────
def test_plan_cuenta_los_vivos_con_peso_por_defecto(lote_plan):
    dw = lote_plan['counts']['links_default_weight']
    assert dw['live'] == {'default_nonflow': 37, 'default_owns': 2}
    real = collections.Counter((l['properties'] or {}).get('criticality_source') for it in lote_plan['items']
                               for l in it['links'] if l['route'] == 'live')
    assert real['default_nonflow'] == 37 and real['default_owns'] == 2
    es = CI.render_summary(lote_plan, 'es')
    assert 'peso POR DEFECTO' in es and 'socio/inversor 37' in es
    assert 'POLICY default weight' in CI.render_summary(lote_plan, 'en')


def test_vinculos_antes_y_despues_con_la_misma_medida(lote_plan, view):
    wc = lote_plan['what_changes']
    assert wc['before']['links'] == sum(int(m.nnz) if hasattr(m, 'nnz') else int((m != 0).sum())
                                        for m in view.core.mats.values())
    assert wc['before']['links'] <= wc['after']['links'] <= wc['before']['links'] + wc['added_links']
    ended = sum(1 for it in lote_plan['items'] for l in it['links'] if l['route'] == 'live' and l.get('valid_to'))
    assert ended >= 1 and wc['added_links'] == lote_plan['counts']['links']['live'] - ended
    assert (wc['before']['tsmc_hit'], wc['after']['tsmc_hit']) == (318, 348)


# ── ficha: margen, año fiscal, Boeing ────────────────────────────────────────────────────────────────────────────
def test_margen_del_catalogo_es_el_operativo_nunca_el_bruto(bundle, lote_plan):
    from core.import_normalize import pct
    recs = {r['record_id']: r for r in bundle['records']}
    n_gross_only = n_op = 0
    for it in lote_plan['items']:
        if it['action'] != 'create':
            continue
        ann = ((recs[it['record_id']].get('financials') or {}).get('annual') or [])
        last = max(ann, key=lambda a: a['fiscal_year']) if ann else None
        op = (last or {}).get('operating_margin_pct')
        gross = (last or {}).get('gross_margin_pct')
        if op is not None:
            assert it['props']['margin'] == pct(op['value']), it['record_id']
            n_op += 1
        else:
            assert 'margin' not in it['props'], it['record_id']
            n_gross_only += 1 if gross is not None else 0
    assert n_op >= 1 and n_gross_only >= 1


def test_anio_fiscal_rotulado_con_el_inicio_es_aviso_sin_tocar_el_numero(bundle, lote_plan):
    flagged = sorted(it['record_id'] for it in lote_plan['items']
                     if any(w.get('code') == 'fiscal_year_label_start' for w in it.get('warnings') or []))
    assert len(flagged) == 14 and 'fb-2026-mitsubishi-heavy' in flagged and 'fb-2026-toyota' not in flagged
    mhi = next(r for r in bundle['records'] if r['record_id'] == 'fb-2026-mitsubishi-heavy')
    it = next(x for x in lote_plan['items'] if x['record_id'] == 'fb-2026-mitsubishi-heavy')
    assert [a['fiscal_year'] for a in it['props']['financials']['annual']] == \
        [a['fiscal_year'] for a in mhi['financials']['annual']]


def test_boeing_no_hereda_el_cedear_de_bank_of_america(bundle, lote_plan):
    boe = next(r for r in bundle['records'] if r['record_id'] == 'fb-2026-boeing')
    assert all(l.get('yahoo_symbol') != 'BAC.BA' and l.get('ticker') != 'BAC' for l in boe.get('listings') or [])
    it = next(x for x in lote_plan['items'] if x['record_id'] == 'fb-2026-boeing')
    lst = (it.get('props') or {}).get('listings') or []
    assert lst and all(l.get('yahoo') != 'BAC.BA' and l.get('yahoo_symbol') != 'BAC.BA' and l.get('symbol') != 'BAC'
                       for l in lst), lst
    with open(os.path.join(LOTE, CI.LOTE2_LOG), encoding='utf-8') as fh:
        log = json.load(fh)
    conf = [e for e in log['records']['fb-2026-boeing'] if e['rule'] == 'listing_ticker_conflict']
    assert len(conf) == 1 and conf[0]['before']['yahoo_symbol'] == 'BAC.BA'


# ── live_caps: el catálogo primero tras un despliegue ───────────────────────────────────────────────────────────
def test_live_caps_publica_el_catalogo_antes_que_lo_importado(monkeypatch):
    from core import instruments
    from core import live_caps as LC
    monkeypatch.setattr(LC, '_symbols_by_id', lambda: {'Nvidia': 'NVDA', 'AMD': 'AMD', 'Moutai': '600519.SS'})
    monkeypatch.setattr(LC, '_daily_outcomes', lambda: None)
    monkeypatch.setattr(instruments, 'baseline_symbols', lambda: frozenset({'NVDA', 'AMD'}))
    LC._PHASE['admitted'].clear()
    LC._STATE.update(caps={}, as_of=None, ts=0.0, running=False, error=None, cycle=None)
    calls = []

    def fetch(syms):
        calls.append((list(syms), dict(LC._STATE['caps'])))
        return {s: {'mcap_b': 1.0, 'price': 10.0, 'currency': 'USD'} for s in syms}
    try:
        LC.refresh(fetch=fetch)
        assert [c[0] for c in calls] == [['AMD', 'NVDA'], ['600519.SS']]
        assert set(calls[1][1]) == {'Nvidia', 'AMD'}           # el catálogo ya estaba publicado al pedir lo importado
        st = LC.get_caps(start=False)
        assert set(st['caps']) == {'Nvidia', 'AMD', 'Moutai'} and st['cycle']['requests'] == 2
        calls.clear()
        LC.refresh(fetch=fetch)                                # con estado: UN pedido, catálogo primero en el orden
        assert [c[0] for c in calls] == [['AMD', 'NVDA', '600519.SS']]
    finally:
        LC._PHASE['admitted'].clear()
        LC._STATE.update(caps={}, as_of=None, ts=0.0, running=False, error=None, cycle=None)


# ── panel 📥: la lista no retiene las fichas ─────────────────────────────────────────────────────────────────────
def test_lista_de_paquetes_no_retiene_las_fichas():
    from ontology import api as A
    A._PKG_CACHE.clear()
    A._pkg_release()
    name = '2026-10-15/' + CI.LOTE2_BUNDLE
    b, sha, meta = A._import_package(name, with_bundle=False)
    assert b is None and meta['n_records'] == 386 and meta['sanitize']['fields_dropped'] == 6
    assert set(A._PKG_CACHE[name]) == {'stat', 'sha', 'meta'} and not A._PKG_BUNDLE
    b2, sha2, _m = A._import_package(name)
    assert sha2 == sha and len(b2['records']) == 386 and A._PKG_BUNDLE['name'] == name
    A._pkg_release()
    assert not A._PKG_BUNDLE


# ── cliente (estático) ───────────────────────────────────────────────────────────────────────────────────────────
def test_catalogo_de_la_base_rehace_banda_y_contadores():
    src = _read('engine/catalog_sync.js')
    body = src[src.index('function refreshCounters()'):src.index('// ── 4. textos al abrir la ficha')]
    assert 'renderBand()' in body and 'invalidateFilterCache()' in body and '_deg = null' in body
    assert 'setTimeout(function () { try { refreshCounters(); } catch (e) {} }, 1300)' in src
    assert 'tamaño mínimo fijo' not in src and 'tamaño por defecto (sin dato)' in src and 'default size (no data)' in src


def test_importadas_no_entran_en_la_ronda_de_precios_sin_tope():
    src = _read('engine/app_main.js')
    i = src.index('window.loadLiveQuotes = function(opts){')
    assert "NODES.filter(n=>n.mkt && !n.from_db)" in src[i:i + 900]
    j = src.index('async function validateTickers(){')
    assert '!n.from_db' in src[j:j + 1200]


def test_ficha_de_una_importada_no_dice_catalogo_ni_preingresos():
    src = _read('engine/app_main.js')
    assert "const _imp = !!d.from_db" in src
    assert "'ficha importada (con fuente)'" in src and "'imported record (sourced)'" in src
    assert "'Crecimiento (ficha investigada)'" in src and "'Growth (researched record)'" in src
    assert re.search(r"d\.margin==null \? \(_en\?'no data':'sin dato'\)", src)


def test_panel_pide_recargar_y_explica_en_palabras_simples():
    src = _read('engine/importer.js')
    for k in ('reload_hint', 'reload_btn', 'dw_line', 'x_cal_t', 'x_cal_b', 'x_dw_t', 'x_dw_b', 'w_fiscal_year_label_start'):
        assert src.count(k + ':') == 2, k                       # ES y EN
    assert "['import_calibration', 'x_cal']" in src and "['import_default_weight', 'x_dw']" in src
    assert '{ reload: true }' in src and 'W.location.reload()' in src
    assert 'kernel.calibration) queda vieja' not in src         # sin jerga en la línea visible
