"""
rag/rag_server.py — Microservicio RAG (Second Brain) de Khipu Finance
Flask + ChromaDB. Corre en el puerto 5051 (separado del server principal).

Indexa empresas, noticias, tesis, simulaciones y documentos del usuario en
colecciones vectoriales, y responde consultas semánticas — opcionalmente
enriquecidas con Claude.

Correr:   python rag_server.py
Deps:     pip install flask chromadb anthropic python-dotenv
"""
import os
import time

import chromadb
from flask import Flask, request, jsonify

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

app_rag = Flask(__name__)

# ChromaDB local persistente
CHROMA_PATH = os.getenv('CHROMA_PATH', '.chroma')
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

COLLECTIONS = {
    'companies':   chroma_client.get_or_create_collection('khipu_companies'),
    'news':        chroma_client.get_or_create_collection('khipu_news'),
    'thesis':      chroma_client.get_or_create_collection('khipu_thesis'),
    'simulations': chroma_client.get_or_create_collection('khipu_simulations'),
    'user_docs':   chroma_client.get_or_create_collection('khipu_user_docs'),
}

CLAUDE_KEY = os.getenv('CLAUDE_KEY', '')
AI_MODEL = os.getenv('AI_MODEL', 'claude-haiku-4-5-20251001')

_claude = None
if CLAUDE_KEY:
    try:
        from anthropic import Anthropic
        _claude = Anthropic(api_key=CLAUDE_KEY)
    except Exception:
        _claude = None


@app_rag.route('/index/company', methods=['POST'])
def index_company():
    data = request.get_json() or {}
    node_id = data.get('id')
    if not node_id:
        return jsonify({'error': 'id required'}), 400

    doc = f"""
Company: {data.get('label', '')} ({data.get('ticker', '')})
Category: {data.get('cat', '')} | Country: {data.get('country', '')} | Location: {data.get('loc', '')}
Role: {data.get('role', '')}
Products/Services: {data.get('supplies', '')}
Competitive Moat: {data.get('moat', '')}
Growth: {data.get('growth', '')}
Thesis: {data.get('thesis', '')}
Revenue 2025: {data.get('revenue_2025', 'N/A')}
Geo Risk: {data.get('geo_risk', 'N/A')}
""".strip()
    try:
        COLLECTIONS['companies'].upsert(
            documents=[doc], ids=[node_id],
            metadatas=[{
                'ticker': data.get('mkt', '') or '',
                'cat': data.get('cat', '') or '',
                'country': data.get('country', '') or '',
                'preipo': str(data.get('preipo', False)),
            }],
        )
        return jsonify({'status': 'indexed', 'id': node_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app_rag.route('/index/news', methods=['POST'])
def index_news():
    items = (request.get_json() or {}).get('items', [])
    ids, docs, metas = [], [], []
    for item in items[:50]:
        uid = f"news_{item.get('datetime', 0)}_{str(item.get('source', ''))[:10]}"
        doc = (f"Headline: {item.get('headline', '')}\n"
               f"Source: {item.get('source', '')} | Date: {item.get('datetime', '')}\n"
               f"Summary: {item.get('summary', '')}\n"
               f"Company: {item.get('related', '')}\nURL: {item.get('url', '')}")
        ids.append(uid)
        docs.append(doc)
        metas.append({'ticker': item.get('related', '') or '', 'source': str(item.get('source', ''))})
    if ids:
        COLLECTIONS['news'].upsert(documents=docs, ids=ids, metadatas=metas)
    return jsonify({'indexed': len(ids)})


@app_rag.route('/index/simulation', methods=['POST'])
def index_simulation():
    data = request.get_json() or {}
    uid = f"sim_{data.get('simulation_id', '')}_{int(time.time())}"
    doc = (f"Simulation: {data.get('title', '')}\nDate: {data.get('date', '')}\n"
           f"Scenario: {data.get('description', '')}\n"
           f"Companies: {', '.join(data.get('nodes_affected', []))}\n"
           f"Prediction: {data.get('report_summary', '')}\n"
           f"Winners: {data.get('winners', '')}\nLosers: {data.get('losers', '')}")
    COLLECTIONS['simulations'].upsert(
        documents=[doc], ids=[uid],
        metadatas=[{'type': 'simulation', 'nodes': ','.join(data.get('nodes_affected', []))}])
    return jsonify({'status': 'indexed', 'id': uid})


@app_rag.route('/index/user-doc', methods=['POST'])
def index_user_doc():
    data = request.get_json() or {}
    content = data.get('content', '')
    if not content:
        return jsonify({'error': 'content required'}), 400
    uid = f"userdoc_{data.get('filename', 'doc')}_{int(time.time())}"
    COLLECTIONS['user_docs'].upsert(
        documents=[content], ids=[uid],
        metadatas=[{'filename': data.get('filename', ''), 'type': data.get('type', 'document')}])
    return jsonify({'status': 'indexed', 'id': uid, 'chars': len(content)})


def _query_internal(query, n_results=6, collections=None):
    names = collections or list(COLLECTIONS.keys())
    out = []
    for col_name in names:
        col = COLLECTIONS.get(col_name)
        if not col:
            continue
        try:
            cnt = col.count()
            if cnt == 0:
                continue
            res = col.query(query_texts=[query], n_results=min(n_results, cnt))
            for i, doc in enumerate(res.get('documents', [[]])[0]):
                out.append({
                    'collection': col_name,
                    'document': doc,
                    'distance': (res.get('distances', [[]])[0] or [99])[i],
                    'metadata': (res.get('metadatas', [[]])[0] or [{}])[i],
                })
        except Exception:
            pass
    out.sort(key=lambda x: x['distance'])
    return out[:n_results]


@app_rag.route('/query', methods=['POST'])
def query_rag():
    data = request.get_json() or {}
    query = data.get('query', '')
    n_results = min(int(data.get('n_results', 5)), 10)
    collections = data.get('collections')
    results = _query_internal(query, n_results, collections)
    return jsonify({'results': results, 'query': query, 'total_searched': len(results)})


@app_rag.route('/query/ai', methods=['POST'])
def query_with_ai():
    data = request.get_json() or {}
    query = data.get('query', '')
    system = data.get('system',
                      'You are Bixby, the financial intelligence assistant of Khipu Finance, '
                      'covering the semiconductor / AI / space value chain.')
    results = _query_internal(query, n_results=6)
    context_block = '\n\n---\n\n'.join(
        f"[{r['collection'].upper()}] {r['document'][:500]}" for r in results)

    if not _claude:
        # Sin Claude: devolver solo el contexto recuperado
        return jsonify({'answer': context_block[:800] or 'No context available and CLAUDE_KEY not set.',
                        'context_used': len(results), 'sources': results, 'note': 'no_llm'})
    try:
        msg = _claude.messages.create(
            model=AI_MODEL, max_tokens=800, system=system,
            messages=[{'role': 'user', 'content':
                       f"Relevant context from the Khipu Finance knowledge base:\n\n{context_block}\n\n"
                       f"---\n\nUser question: {query}\n\n"
                       "Answer using the context above. Be specific and cite relevant data points."}])
        answer = msg.content[0].text if msg.content else ''
        return jsonify({'answer': answer, 'context_used': len(results), 'sources': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app_rag.route('/stats', methods=['GET'])
def rag_stats():
    return jsonify({col: {'count': COLLECTIONS[col].count()} for col in COLLECTIONS})


if __name__ == '__main__':
    port = int(os.getenv('RAG_PORT', 5051))
    print(f'Khipu Finance RAG Server (Second Brain) on port {port}')
    app_rag.run(host='0.0.0.0', port=port, debug=False)
