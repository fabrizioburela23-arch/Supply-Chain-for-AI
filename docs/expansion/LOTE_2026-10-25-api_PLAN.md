# Lote 7 (API) — 260 empresas investigadas con la API de Claude (plan; nada aplicado)

> Fabrizio corrió `scripts/research_batch.py` (Claude Sonnet 5.5 + búsqueda web) con sus créditos de API: 260 fichas,
> ≈ 84 USD estimados (999 búsquedas), 1 rechazada (devolvió research_meta suelto). Ninguna repetida con los lotes 2-6.

- Formato: 260/260 válidas sin arreglos (el script ya sanea y valida antes de guardar).
- Plan sobre el catálogo de esta PC (sin los lotes 2-6): 256 crear · 4 completar (Brookfield, Raytheon, Samsung, SMBC) ·
  vínculos 125 vivos / 77 propuestos / 584 pendientes / 2 cuarentena · ρ 1,2107 → 1,2099 · TSMC 318 → 329 · empresas
  969 → 1.225.
- ⚠ Pocos vínculos: 109 fichas sin ninguno y 88 con 1-2 (Sonnet con esfuerzo medio priorizó la ficha). Desde
  2026-10-25 el script devuelve a la IA toda ficha con < 3 vínculos (una vez) y este lote entra en la lista de
  `--make-enrich-list` para engrosarlo.
- Sin listas de sanciones consultadas. Aplicar DESPUÉS de los lotes 5 y 6: 🩺 → 📥 Importar → «Lote 7 — 260 empresas».
