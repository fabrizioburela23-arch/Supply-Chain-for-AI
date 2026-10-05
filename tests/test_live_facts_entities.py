"""core/live_facts.detect_entities (2026-10-05): en la simulación del IPO de OpenAI la IA recibió los datos de C3.ai
(ticker "AI") y no los de Microsoft/Nvidia — "AI" es una palabra, no una empresa, y "Microsoft (Azure)" no casaba."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_ai_no_es_c3ai_y_microsoft_se_reconoce():
    from core.live_facts import detect_entities
    txt = ('Geopolitical context: AI chips export controls. OpenAI goes public. Key players: OpenAI, Microsoft, '
           'Anthropic, Nvidia, Oracle, Meta, Alphabet. AI profitability timeline.')
    ids = detect_entities(txt)
    assert 'C3ai' not in ids and not any('c3' in i.lower() for i in ids)
    assert ids[:6] == ['OpenAI', 'Microsoft', 'Anthropic', 'Nvidia', 'Oracle', 'Meta']
    assert detect_entities('Compare NVDA vs AMD')[:2] == ['Nvidia', 'AMD']          # los tickers reales siguen valiendo
