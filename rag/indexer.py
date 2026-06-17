"""
rag/indexer.py — Indexa todos los nodos de Khipu Finance en ChromaDB al inicio.

Uso:
    python indexer.py [nodes_all.json]

El JSON debe ser una lista de objetos-nodo (id, label, ticker, cat, role, ...).
Puedes generarlo exportando NODES desde el frontend o concatenando
nodes/nodes_core.js + nodes/nodes_spacex.js.
"""
import json
import sys
import os

import requests

RAG_URL = os.getenv('RAG_URL', 'http://localhost:5051')


def index_all_nodes(nodes_json_path='nodes_all.json'):
    with open(nodes_json_path) as f:
        nodes = json.load(f)

    print(f'Indexing {len(nodes)} companies into {RAG_URL} ...')
    indexed = 0
    for node in nodes:
        try:
            r = requests.post(f'{RAG_URL}/index/company', json=node, timeout=30)
            if r.ok:
                indexed += 1
            else:
                print(f'  error indexing {node.get("id")}: {r.text[:100]}')
        except Exception as e:
            print(f'  exception indexing {node.get("id")}: {e}')

    print(f'Done. Indexed {indexed}/{len(nodes)} companies.')
    return indexed


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else 'nodes_all.json'
    index_all_nodes(path)
