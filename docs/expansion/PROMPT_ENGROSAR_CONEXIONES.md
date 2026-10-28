# Prompt: engrosar conexiones (para pegar en otro chat de Claude Code, en tu PC)

Repo: Khipus Finance Intelligence. Lee CLAUDE.md y la sección «▶ PRÓXIMA SESIÓN» de docs/ESTADO.md.

OBJETIVO: las empresas con 0-2 vínculos de flujo (supply/fab/cloud/license/ppa/deploy) deben tener sus
proveedores y clientes reales, con fuente verificable.

PASOS
1. Lista las empresas con grado de flujo ≤ 2 en data/grafo_v0.json. Empieza por las de mayor
   capitalización o por las que más se conectan con Nvidia, Microsoft, TSMC, Amazon y Alphabet.
2. Para cada una (lotes de 10), con WebSearch Y WebFETCH abre la fuente (10-K, comunicado, prensa grande):
   - de quién compra (6-15) y a quién le vende (6-15), con producto.
   - copia la CITA TEXTUAL de la página abierta (no parafrasees) y la URL.
   - confianza ≥ 0,9 solo con fuente primaria; rumores ≤ 0,3; sin fuente → no lo incluyas.
3. Guarda un JSON por lote con el formato que usa scripts/links_to_ficha.py (ver su docstring y
   tests/test_links_to_ficha.py).
4. Conviértelo: `python scripts/links_to_ficha.py out*.json --out data/import/lotes/<fecha>-links/fichas_links.jsonl`.
5. NO escribas en la base. Deja el JSONL listo para 📥 Importar (lo aplica Fabrizio).
6. Antes de commitear: regenerar la bóveda (`python scripts/build_vault.py`) y `pytest tests/ -q`.
   Sube CACHE de sw.js si tocas JS. Rama de trabajo, no main.

REGLAS: nunca inventes un vínculo; sin cita textual abierta de la página no entra; vínculos con contraparte
desconocida se dejan como están (el importador los marca pendientes). Responde en español simple y corto.
