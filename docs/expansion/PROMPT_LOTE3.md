# Prompt del lote 3 — 100 empresas nuevas a nivel B (ficha completa con vínculos)

Adjuntar: `data/import/lotes/lote3/lote3_100_empresas.csv` (las 100), `data/import/empresas_existentes.csv`,
`data/import/company.schema.json`, `data/import/plantilla_empresa.json`.

```text
Eres el mismo analista que armó los lotes 1 y 2. Khipus ya importó 386 fichas completas. Ahora necesito la FICHA COMPLETA
(nivel B, esquema khipus.company/1 adjunto, sigue plantilla_empresa.json) de las 100 empresas de lote3_100_empresas.csv.
UN DATO INVENTADO ES PEOR QUE UN DATO FALTANTE: si no lo encuentras, borra el campo y anota su ruta en
research_meta.not_found.

FORMATO: SOLO líneas JSONL (una línea = una empresa), sin texto fuera, sin ```. record_id "fb-2026-<khipus_id_hint en
minúsculas>"; khipus_id_hint = el de la columna khipus_id_hint (no lo cambies); research_meta: batch "lote3-<n>",
tier "B", priority = la de la fila, method "ai_assisted", revision 1, researched_at = ahora (ISO con Z). Entrega de 5 a 10
empresas por respuesta, en el orden de la lista; al final de cada respuesta NO escribas nada más.

FORMATOS QUE KHIPUS EXIGE (en el lote 2 fallaron 357 de 386 por esto):
- Números como números (fiscal_year 2025, no "2025"); punto decimal; sin separador de miles; dinero en UNIDADES de la moneda
  original con currency (ISO 4217) y period (FY2025, 2025-Q2, 2025-H1, TTM-2026-06 o point).
- URLs exactas y SIN espacios ni corchetes (codifica los espacios como %20); nada de URLs de búsqueda ni de la API de GLEIF:
  para el LEI cita https://search.gleif.org/#/record/<LEI>.
- Fechas AAAA-MM-DD, o AAAA-MM / AAAA si no sabes el día. Países ISO-2 (HK y TW nunca CN). Bolsas en MIC. Tickers sin
  espacios (ERIC-B).
- Toda cifra y todo vínculo con source_url, as_of, retrieved_at, confidence (0-1) y source_kind (primary, press, trade,
  corporate, rumor, aggregator, state); ≥ 0,9 solo con fuente primary; rumor ≤ 0,3; cita textual (quote ≤ 500).
- Textos en español (value) e inglés (value_en).

PRIORIDAD 1 — VÍNCULOS (relations): de 3 a 10 verificables, de TODOS los tipos que existan, uno por vínculo:
- FLUJO: supply, fab, cloud, license, ppa, deploy, owns. NO FLUJO: invest, partner.
- this_role = papel de ESTA empresa (supplier, customer, investor, investee, owner, owned, partner).
- counterparty: khipus_id exacto si está en empresas_existentes.csv o en lote3_100_empresas.csv; si no, nombre +
  identificadores (LEI/ISIN/dominio).
- product: qué fluye exactamente; label_es/label_en en forma PROVEEDOR→cliente.
- dependency OBLIGATORIA en vínculos de flujo: criticality 1-6 (6 único sin sustituto <12 meses · 5 >50 % del insumo ·
  4 principal con 1-2 alternativas · 3 uno de pocos · 2 uno de varios · 1 marginal), sole_source, y si la fuente lo dice:
  share_of_customer_purchases, share_of_supplier_revenue, contract_value, volume con unidad, substitutability_months,
  supplier_facility / customer_facility (planta con share_of_flow_pct), component, product_affected, bom_share_pct, tier,
  alternatives. En owns e invest pon el % de participación.
- status (active, ended, announced, planned, rumored, disputed) + start/end; evidence con quote.
- Prioriza criticidad ≥ 4, proveedor único y vínculos entre países.

PRIORIDAD 2 — EL RESTO DE LA FICHA:
- identity: nombre legal, LEI, ISIN, CIK (si reporta en EE.UU.), FIGI, Wikidata QID; TODAS las cotizaciones en listings
  con UNA sola is_primary = true (la bolsa del país de la sede; ADR, GDR, CEDEAR, OTC y bolsas regionales alemanas nunca
  principales); other_names (nombre local, siglas, nombres anteriores).
- market_position: puesto y/o cuota por mercado, con quién lo mide, región y período.
- facilities con facility_id (fac-001…), capacidad con unidad, país y estado.
- corporate: matriz, filiales y accionistas principales con %.
- textos: qué hace, qué vende, ventaja, riesgo principal, crecimiento (es/en).
- riesgos, regulación/sanciones y timeline con hechos fechados.
- privadas: última valuación VERIFICADA (ronda cerrada con fecha y fuente). Nunca "en conversaciones".

PROHIBIDO (llega en vivo o lo calcula Khipus; la ficha se rechaza): precio, capitalización, volumen, tipo de cambio,
múltiplos (P/E, EV/EBITDA…), acciones en circulación de las que cotizan, puntajes propios.
```
