"""Chat: de qué lista sale la cartera y qué hacer con una noticia que cuenta el usuario (Fabrizio, 2026-10-15).

1) «quiero que mencione la cartera de donde está sacando la info»: el contexto lleva la cartera ACTIVA con su nombre
   (desde «que solo haya uno donde guardar», 2026-10-15, ya no hay «Mis posiciones (Mercado)» aparte: Mercado muestra
   la cartera activa) + los nombres de las otras, y la regla obliga a nombrar la fuente.
2) Reunión con Diego: «le pasamos una noticia como si la hubiéramos escuchado y dijo que no la puede confirmar»: la
   noticia se busca, se dice si se confirmó y, si no, se analiza como HIPÓTESIS (nunca como hecho).
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('KHIPU_SCHEDULER', 'off')

from core import khipu_chat as K  # noqa: E402


def _req(msg, **ctx):
    return K.validate_request({'message': msg, 'lang': 'es', 'context': ctx})


def _ctx(r):
    return r[3] if isinstance(r, tuple) and len(r) > 3 and isinstance(r[3], dict) else \
        (r.get('context') if isinstance(r, dict) else next(x for x in r if isinstance(x, dict) and 'mode' in x))


def test_cartera_activa_con_nombre_y_las_otras_solo_nombres():
    """Un solo lugar donde guardar (2026-10-15): la cartera del contexto es la ACTIVA, con su nombre; de las otras
    solo van los nombres (nunca dos listas con las mismas posiciones); ya no existe «Mis posiciones (Mercado)»."""
    c = _ctx(_req('¿cómo va mi cartera?',
                  portfolio={'name': 'Tecnología <script>', 'positions': [{'symbol': 'TSLA', 'shares': 10000},
                                                                         {'symbol': 'X', 'shares': -1}]},
                  other_portfolios=['Energía', 'Tecnología <script>', 'Energía', 42]))
    assert c['portfolio'] == [{'symbol': 'TSLA', 'shares': 10000.0}]
    assert c['portfolio_name'] == 'Tecnología script'                          # sin caracteres peligrosos
    assert c['other_portfolios'] == ['Energía']                                  # sin la activa, sin repetidas
    assert 'practice_portfolios' not in c
    p = K.build_prompt('¿cómo va mi cartera?', [], 'es', c, [], 2, False)
    assert 'TU CARTERA del usuario «Tecnología script»' in p and 'TSLA 10000' in p
    assert 'MISMA que muestran Mercado' in p and 'OTRAS CARTERAS' in p and '«Energía»' in p
    assert 'REGLA DE CARTERAS' in p and '«tu cartera “<nombre>”»' in p
    assert 'Mis posiciones' not in p and 'MIS POSICIONES' not in p and 'CARTERAS DE PRÁCTICA' not in p


def test_cartera_activa_vacia_se_dice_con_su_nombre():
    c = _ctx(_req('¿qué tengo?', portfolio_empty='Mi cartera'))
    assert c['portfolio_empty'] == 'Mi cartera' and 'portfolio' not in c
    p = K.build_prompt('¿qué tengo?', [], 'es', c, [], 2, False)
    assert '«Mi cartera»' in p and 'VACÍA' in p and 'REGLA DE CARTERAS' in p


def test_sin_carteras_no_hay_regla():
    c = _ctx(_req('hola'))
    p = K.build_prompt('hola', [], 'es', c, [], 2, False)
    assert 'REGLA DE CARTERAS' not in p and 'NOTICIA QUE NADIE VERIFICÓ' not in p


def test_noticia_contada_por_el_usuario_se_busca_y_si_no_se_confirma_es_hipotesis():
    for msg in ('Escuché que TSMC va a parar una fábrica en Arizona', 'me dijeron que Nvidia compra a Arm',
                'dicen que Samsung pierde a Apple como cliente', 'I heard that Intel is selling its fabs',
                'salió una noticia de que BYD abre planta en México'):
        c = _ctx(_req(msg))
        assert c.get('user_claim') is True, msg
        p = K.build_prompt(msg, [], 'es', c, [], 2, False)
        assert 'NOTICIA QUE NADIE VERIFICÓ' in p and 'HIPÓTESIS' in p and 'get_news' in p
    assert not _ctx(_req('¿cómo va Nvidia hoy?')).get('user_claim')


def test_cliente_manda_la_cartera_activa_con_nombre():
    js = open(os.path.join(ROOT, 'engine', 'khipu_chat.js'), encoding='utf-8').read()
    assert 'ctx.portfolio.name = pfName' in js and 'ctx.other_portfolios = oth' in js and 'PS.name()' in js
    assert 'practice_portfolios' not in js and "getItem('kh_portfolios')" not in js
