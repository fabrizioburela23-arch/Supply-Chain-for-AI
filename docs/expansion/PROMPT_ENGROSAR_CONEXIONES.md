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

% DE INGRESOS (prioridad ALTA, 2026-11-04): los pesos del grafo son importancia 1-6, no cuotas de venta, así que el motor
subestima a los clientes concentrados (Nvidia: 3-4 clientes dan ~40-50 % de sus ingresos y el grafo les da ~3 % cada uno).
Para cada vínculo de FLUJO (supply/fab/cloud/license/ppa/deploy) busca en fuente PRIMARIA (10-K / 20-F / informe anual /
comunicado: «un cliente representó el X % de los ingresos», clientes >10 %) y añade al JSON del vínculo:
  "share_of_supplier_revenue_pct": X      (% de las ventas del PROVEEDOR que van a ese cliente)
  "share_of_customer_purchases_pct": Y    (% de las compras del CLIENTE que vienen de ese proveedor, si se publica)
La CITA TEXTUAL de esa página debe contener ese número (scripts/links_to_ficha.py descarta el % si la cita no lo trae; el
vínculo entra igual, sin el %). Si el 10-K solo dice «cliente A, cliente B» sin nombres, NO adivines quién es: omite el %.
Empieza por las empresas con pocos clientes y mucha concentración (proveedores de hiperescaladores, de Apple, de Tesla…).

REGLAS: nunca inventes un vínculo; sin cita textual abierta de la página no entra; vínculos con contraparte
desconocida se dejan como están (el importador los marca pendientes). Responde en español simple y corto.
