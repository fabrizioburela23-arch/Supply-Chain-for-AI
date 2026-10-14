# Prompt para el lote 2 (corregir el lote 1 y completar lo que falta)

Pegar tal cual en la IA de investigación, adjuntando `data/import/lotes/2026-10-14/empresas_nuevas.csv`,
`empresas_nuevas_verificacion.csv`, `data/import/empresas_existentes.csv`, `data/import/company.schema.json` y
`data/import/plantilla_empresa.json`.

```text
Eres el mismo analista que armó el lote 1 (4.174 empresas nuevas + 937 países). Khipus ya lo revisó: el formato está
bien y se va a importar. Ahora toca CORREGIR 3 cosas y COMPLETAR lo que al grafo todavía le falta. Regla de siempre:
UN DATO INVENTADO ES PEOR QUE UN DATO FALTANTE. No cambies el formato de los archivos que ya entregaste.

PARTE 1 — CORRECCIONES AL LOTE 1 (devuelve solo las filas corregidas, mismo CSV y mismas columnas)
1. Cotización principal equivocada. La cotización principal es la de la bolsa del país de la sede (o la de mayor
   volumen si cotiza en varias). Todo lo demás es secundario y va en la columna "secundarias" del archivo de
   verificación (ADR, GDR, CEDEAR, OTC, bolsas regionales alemanas XSTU/XBER/XHAM/XDUS, Viena XWBO).
   Revisa y corrige al menos: Boeing (NYSE: BA, no BAC.BA), GE Aerospace (NYSE: GE), Globant (NYSE: GLOB), Siemens
   (XETR: SIE, el nombre legal es "Siemens AG", no "Shares (Sp. ADRs)"), RWE (XETR: RWE), Samsung Electronics
   (XKRX: 005930.KS, no el GDR), las 22 filas con bolsa OTCM y las 21 con XSTU/XBER. Después revisa las 205 filas cuya
   bolsa está en otro país que la sede (CN→XHKG está bien; el resto, una por una).
2. Las 1.170 empresas con verificado = "no" (método "conocimiento"). Para cada una busca UNA fuente real (web
   corporativa, registro mercantil, prensa seria) que confirme que existe, su país y a qué se dedica, y actualiza el
   archivo de verificación (verificado = "si", método = "webfetch"/"websearch", y pon la URL en fuente_url del CSV
   principal). Empieza por las 146 de prioridad P1 y las 57 públicas (tienen bolsa: es fácil). La que no puedas
   confirmar queda con verificado = "no": no la inventes ni la borres.
3. Categorías: battery_components quedó "sin consolidar" (2 empresas): asígnalas a battery_cells o a la que
   corresponda. Confirma que cada categoría nueva (NUEVA:…) tiene sector, label_es y label_en en
   categorias_propuestas.csv.

PARTE 2 — LO QUE LE FALTA AL GRAFO (la parte importante)
El grafo vive de los VÍNCULOS: sin "quién le vende a quién", una empresa nueva es un punto suelto. Para las empresas de
prioridad P1 (396) y después P2, entrega la FICHA COMPLETA en JSONL con el esquema adjunto (khipus.company/1, nivel B;
sigue la plantilla_empresa.json). Por cada empresa, en este orden de importancia:
a) relations: de 3 a 10 vínculos verificables, TODOS los tipos que existan, no solo "proveedor". Son 9 tipos y no se
   mezclan (uno por vínculo; si hay dos cosas, son dos vínculos):
   - FLUJO (mueven algo del source al target y propagan daño): supply (provee un insumo o componente), fab (fabrica
     para: foundry, OSAT, EMS), cloud (da capacidad de nube/cómputo), license (licencia IP o software: ARM, EDA),
     ppa (da energía por contrato), deploy (despliega sus sistemas en el cliente: robots, equipos, satélites),
     owns (posee: filial, planta, participación de control).
   - NO FLUJO (se guardan y se consultan, no propagan daño): invest (accionista o inversor con % o ronda),
     partner (JV, alianza, codesarrollo, acuerdo comercial sin suministro medible).
   Dirección ÚNICA: source PROVEE/invierte/posee → target. this_role dice el papel de ESTA empresa (supplier, customer,
   investor, investee, owner, owned, partner). Casos típicos: cliente de un chip = supply con this_role=customer; una
   matriz y su filial = owns; un accionista con 8 % = invest con share; un JV = partner + (si aporta capital) invest.
   Cada vínculo lleva:
   - counterparty: nombre + identificadores (khipus_id exacto de empresas_existentes.csv si ya existe; si no, LEI/ISIN/
     QID/dominio y el nombre en CamelCase; sin identificador fuerte el vínculo entra como PROPUESTA).
   - product: qué fluye exactamente ("celdas LFP prismáticas", "HBM3E", "obleas 3 nm", "GPU H100 en nube",
     "licencia Armv9"). label_es/label_en en forma PROVEEDOR→cliente.
   - dependency (la parte que más vale): criticality 1-6 (6 = proveedor único sin sustituto en <12 meses; 5 = >50 %
     del insumo o calificación >1 año; 4 = principal con 1-2 alternativas; 3 = uno de pocos; 2 = uno de varios;
     1 = marginal); sole_source true/false; share_of_customer_purchases (% de lo que el cliente compra de ese insumo
     que viene de este proveedor); share_of_supplier_revenue (% de las ventas del proveedor que son a ese cliente);
     contract_value (moneda y período); volume con unidad (GWh/año, obleas/mes, MW); substitutability_months (cuántos
     meses tardaría en reemplazarlo). Pon solo lo que la fuente diga; la criticality es tu juicio razonado y va con
     su quote.
   - dependencia POR PLANTA y POR PIEZA (nuevo, dentro de dependency): supplier_facility = la planta concreta del
     proveedor de donde sale ESTE flujo (name + country + city, o su facility_id si la planta está en la ficha) con
     share_of_flow_pct (100 = toda la relación depende de esa planta; «el 3 nm sale solo de Hsinchu»);
     customer_facility = la planta del cliente que lo recibe; component = la pieza o material exacto dentro del
     producto («HBM3E», «sustrato ABF», «electrolito LiPF6»); product_affected = qué producto del cliente lo necesita
     («H100», «Model 3»); bom_share_pct = % del costo de ese producto que es este insumo (solo si una fuente lo dice);
     tier = 1 si le vende directo al cliente final, 2 si es proveedor del proveedor, 3 más atrás; alternatives =
     proveedores alternativos calificados hoy, si la fuente los nombra (lista vacía = no se conocen). Cada planta de
     la ficha lleva facility_id (fac-001…) y cada producto product_id (prod-001…) para poder apuntarlos.
   - status (active, ended, announced, planned, rumored, disputed) + start/end (fecha parcial permitida: AAAA o AAAA-MM).
     Un contrato terminado NO se borra: status=ended con end. Uno anunciado = announced con start futuro.
   - evidence: source_url exacto, as_of, quote textual (máx. 500 caracteres), source_kind; confidence 0-1 (<0,5,
     rumored o contraparte sin identificador → va a aprobación humana, no al grafo directo).
   Prioriza los vínculos que importan para el riesgo: los de criticality ≥ 4, los de proveedor único y los que
   cruzan países (TW→US, CN→DE…). Un "partner" vago sin producto ni cifra vale menos que un "supply" con %.
b) market_position: puesto (rank) y cuota (share_pct) en cada mercado principal, con la firma que lo mide (SNE
   Research, TrendForce, Gartner, IDC, IEA, BNEF, USGS…), la región (GLOBAL o ISO-2) y el período.
c) identity.ids: LEI (search.gleif.org), CIK (solo si reporta en EE.UU.), Wikidata QID, FIGI; TODAS las cotizaciones
   en listings con una sola is_primary = true y, en los ADR, ordinary_per_depositary; other_names con el nombre en
   escritura local y nombres anteriores con fecha.
d) textos bilingües (es/en): qué hace, qué vende, su ventaja (moat), su riesgo principal, su crecimiento.
e) capacidades y plantas con unidad (GWh/año, obleas/mes, MW, t/año), país y fecha.
f) empresas PRIVADAS: última valuación VERIFICADA (ronda cerrada, con fecha, moneda y fuente primary/press). Nunca una
   valuación "en conversaciones".

PROHIBIDO (llega en vivo o lo calcula Khipus; si aparece, la ficha se rechaza): precio, capitalización de mercado,
volumen, tipo de cambio, múltiplos (P/E, EV/EBITDA…), acciones en circulación de las que cotizan, puntajes propios.
En su lugar van los identificadores (con ellos el sistema trae esos números al segundo).

REGLAS DE PROCEDENCIA: cada dato con source_url exacto (no un buscador), as_of (AAAA-MM-DD, o AAAA-MM/AAAA si no
sabes el día), retrieved_at = hoy, confidence 0-1 (≥ 0,9 solo con fuente primary; ≥ 0,5 exige press/trade/primary;
rumor máx. 0,3) y source_kind (primary, press, trade, corporate, rumor, aggregator, state). Dinero en UNIDADES de la
moneda original con currency y period. Países ISO-2 (Hong Kong = HK, Taiwán = TW, nunca CN); si tiene doble sede,
hq_country = sede principal e incorporation_country = país de registro. Bolsas en MIC. JSON estricto: punto decimal,
sin separador de miles, sin comentarios, sin ``` y sin texto fuera del JSONL.

ENTREGA: lotes de 5 a 10 empresas por respuesta (las respuestas largas se cortan), empezando por P1 ordenadas por
sector: energia → materiales → equipos → fabricacion → infra → cloud_ia → el resto. record_id estable ("fb-2026-<id>"),
research_meta.batch = "lote2-<sector>-<n>", revision = 1. Si una empresa ya está en empresas_existentes.csv (son 30 del
lote 1: Boeing, BMW, Cemex, Brookfield, Umicore, National Grid, Terna, Prysmian, DHL, Tencent, GE Aerospace, Vulcan
Energy, RWE, Ericsson, Shell…), usa su khipus_id en khipus_id_hint: se fusiona, no se duplica.
```
