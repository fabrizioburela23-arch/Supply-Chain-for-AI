"""Chat: de qué lista sale la cartera y qué hacer con una noticia que cuenta el usuario (Fabrizio, 2026-10-15).

1) «quiero que mencione la cartera de donde está sacando la info»: el contexto separa «Mis posiciones (Mercado)» de las
   carteras de práctica (con su nombre) y la regla obliga a nombrar la fuente.
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


def test_carteras_de_practica_con_nombre_y_fuente_en_el_prompt():
    c = _ctx(_req('¿cómo va mi cartera?',
                  portfolio={'positions': [{'symbol': 'TSLA', 'shares': 10000}]},
                  practice_portfolios=[{'name': 'Tecnología <script>', 'active': True,
                                        'positions': [{'symbol': 'NVDA', 'shares': 5}, {'symbol': 'X', 'shares': -1}]},
                                       {'name': 'Vacía', 'positions': []}]))
    assert c['practice_portfolios'][0]['name'] == 'Tecnología script'          # sin caracteres peligrosos
    assert c['practice_portfolios'][0]['positions'] == [{'symbol': 'NVDA', 'shares': 5.0}]
    p = K.build_prompt('¿cómo va mi cartera?', [], 'es', c, [], 2, False)
    assert 'MIS POSICIONES' in p and '«Mis posiciones' in p and 'TSLA 10000' in p
    assert '«Tecnología script» [activa]: NVDA 5' in p and '«Vacía»: vacía' in p
    assert 'REGLA DE CARTERAS' in p


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


def test_cliente_manda_las_carteras_de_practica_con_nombre():
    js = open(os.path.join(ROOT, 'engine', 'khipu_chat.js'), encoding='utf-8').read()
    assert "ctx.practice_portfolios = prac" in js and "kh_portfolios" in js and 'kh_pf_active' in js
