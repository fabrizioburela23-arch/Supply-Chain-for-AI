# 🤖 Prompts listos para pegar en otra IA de investigación

Dos prompts:

- **Prompt A**: investiga una empresa o una lista y devuelve la ficha en JSON.
- **Prompt B**: propone la lista de ~4.000 empresas nuevas en CSV.

## 📎 Cómo usarlos

1. Abre una IA que busque en internet y cite fuentes (por ejemplo, un modo de "investigación profunda").
2. **Adjunta** `empresas_existentes.csv` (las 937 que ya están) a los dos prompts. Para el Prompt A, adjunta también
   `company.schema.json` y `plantilla_empresa.json`.
3. Copia el bloque de texto, cambia lo que está entre `[[ ]]` y envíalo.
4. Guarda la respuesta como archivo `.jsonl` (Prompt A) o `.csv` (Prompt B).
5. Pide **pocas empresas por vez**, porque las respuestas largas se cortan:
   - nivel C: 1 empresa por vez;
   - nivel B: de 1 a 3;
   - nivel A: de 5 a 10;
   - Prompt B: unas 200 filas por vez, un bloque cada vez.

---

## 🅰️ Prompt A: ficha de una o varias empresas

```text
Eres un analista de investigación financiera. Tu trabajo es armar la ficha de cada empresa de la lista para
importarla a un grafo de la cadena de suministro de la IA (Khipus). La precisión importa más que la cantidad.
UN DATO INVENTADO ES PEOR QUE UN DATO FALTANTE.

EMPRESAS: [[ CATL ; BYD ; LG Energy Solution ]]
NIVEL: [[ B ]]   (A = mínimo para entrar: identidad, cotizaciones, categoría, resumen, qué vende, palabras clave y
                 al menos 1 vínculo · B = ficha completa · C = profunda, con plantas, capacidades y % de dependencia)
LOTE: [[ baterias-01 ]]
PRIORIDAD: [[ P1 ]]
INVESTIGADOR: [[ Fabrizio + nombre de esta herramienta ]]

FORMATO DE SALIDA (obligatorio):
- Devuelve SOLO líneas JSON (formato JSONL): UNA línea = UN objeto JSON = UNA empresa. Sin texto antes ni después y
  sin ```.
- Cada objeto debe cumplir EXACTAMENTE el esquema adjunto company.schema.json ("schema": "khipus.company/1").
  Toma como guía la forma de plantilla_empresa.json.
- No inventes campos: cualquier campo que no esté en el esquema se rechaza.
- Nunca dejes un texto "<...>" de la plantilla. Si encuentras el dato, ponlo. Si no lo encuentras, BORRA el campo y
  anota su ruta en research_meta.not_found (ejemplo: "identity.ids.lei").
- JSON estricto: números con PUNTO decimal y sin separador de miles (0.9, 1250000000), nunca entre comillas;
  true/false sin comillas; sin comentarios; sin marcas de cita tipo [1] o 【】; sin comas al final.
- record_id: estable y único, en minúsculas. Ejemplo: "fb-2026-catl".
- khipus_id_hint: si la empresa YA está en empresas_existentes.csv, su khipus_id exacto. Si es nueva, el nombre corto
  en CamelCase sin espacios. Ejemplo: "CATL", "LGEnergySolution".
- research_meta: researcher = INVESTIGADOR; researched_at = fecha y hora de hoy (2026-10-13T15:00:00Z);
  method = "ai_assisted"; tier = NIVEL; priority = PRIORIDAD; batch = LOTE; revision = 1 (súbelo si re-entregas la
  misma empresa con el mismo record_id).

REGLAS DE PROCEDENCIA (cada dato):
1. Cada "fact" lleva:
   - source_url: el enlace EXACTO al documento, no a un buscador;
   - as_of: la fecha en que el dato es verdad, en formato AAAA-MM-DD, o AAAA-MM / AAAA si no sabes el día
     (NUNCA inventes el día);
   - retrieved_at: la fecha de hoy;
   - confidence: de 0 a 1;
   - source_kind: un tipo de la lista de abajo.
2. Tipos de fuente (source_kind):
   - primary: informe anual, 10-K, 20-F, regulador, bolsa;
   - press: prensa seria;
   - trade: prensa o consultora especializada del sector;
   - corporate: comunicado o web de la propia empresa;
   - rumor: rumor;
   - aggregator: sitios que juntan datos de otros;
   - state: medio estatal.
3. Confianza:
   - 0,9 o más: solo con fuente primary;
   - 0,5 o más: exige una fuente press, trade o primary;
   - rumor: 0,3 como máximo.
4. Toda cifra y todo vínculo llevan "quote": una frase TEXTUAL de la fuente (máximo 500 caracteres).
5. Los textos van en español (value) y en inglés (value_en). En listas, usa text_es y text_en.
6. Dinero: el número en UNIDADES de la moneda ORIGINAL (no en millones), con "currency" (ISO 4217) y "period"
   (FY2025, 2025-Q2, TTM-2026-06 o point). No conviertas a dólares.
7. Porcentajes de 0 a 100 (participaciones, cuotas, % de ingresos). Los márgenes pueden ser negativos (-35).
   Empleados en personas (no en miles). Toda capacidad o volumen lleva "unit" (GWh/año, obleas/mes, MW, t/año).
8. Países en ISO 3166-1 de 2 letras (CN, US, TW, KR, JP, DE). Bolsas en código MIC ISO 10383 (XSHE, XHKG, XNAS, XNYS,
   XTAI, XKRX, XTKS). Monedas en ISO 4217.

PROHIBIDO (llega en vivo o lo calcula Khipus; si aparece, la ficha se rechaza):
- precio;
- capitalización de mercado;
- volumen;
- tipo de cambio;
- P/E, EV, EV/EBITDA y otros múltiplos;
- acciones en circulación de empresas que cotizan;
- valuación "en negociación" o "en conversaciones" de una privada;
- cualquier puntaje (NRS, ranking propio).
En su lugar, entrega los IDENTIFICADORES: LEI, ISIN, CIK, Wikidata, FIGI, símbolo de Yahoo con sufijo (300750.SZ,
3750.HK, 2330.TW), MIC, dominio web. Con ellos el sistema trae esos números en vivo.

IDENTIDAD (lo más importante, para no duplicar empresas):
- Busca el LEI en search.gleif.org. Ahí también salen la matriz directa y la última.
- Busca el CIK en sec.gov/edgar, solo si la empresa reporta en EE.UU.
- Busca el QID en wikidata.org y el FIGI en openfigi.com.
- Lista TODAS las cotizaciones en "listings":
  - una sola con is_primary = true;
  - en un ADR, pon ordinary_per_depositary (cuántas acciones vale 1 ADR).
- En other_names pon: el nombre en escritura local (chino, japonés, coreano), siglas, marcas y nombres anteriores con
  su fecha.

CATEGORÍA (classification.cat): usa UNA de estas ids existentes. Si ninguna sirve, pon la más cercana y propone otra
en cat_proposed (id en minúsculas_con_guiones, label_es, label_en, y sector, que es uno de los 13 de abajo):
- diseno: asic_custom, eda, edge_ai, fabless, neuromorphic, photonics_si, quantum_hw
- equipos: chemicals, equip, materials, optics, quantum_infra
- fabricacion: foundry, memory, osat, substrates
- infra: cdn_edge, connectivity_infra, dc_reit, hpc_super, networking, power, servers
- cloud_ia: ai_agents, ai_auto, ai_finance, ai_health, ailab, aisoft, cloud
- robotica: robotics_physical
- espacio: earth_obs, satellite, space_infra, space_launch
- energia: battery_mat, energy_trading, grid_transmission, hydrogen, lng, midstream_pipeline, nuclear_equipment,
  nuclear_fusion, nuclear_operator, nuclear_smr, oil_gas_major, power_ipp, rare_earth, renewables_utility,
  storage_grid, uranium, uranium_enrichment, uranium_mining
- defensa: ai_defense, defense_prime
- logistica: air_cargo, canal_authority, freight_forwarder, heavy_lift_logistics, port_operator, rail_freight,
  shipping_line
- macro_credito: alternative_asset_manager, asset_manager, bis, cds_index_provider, central_bank,
  derivatives_standards, exchange_derivatives, exchange_index_provider, growth_equity, index_provider,
  infrastructure_investor, investment_bank, pension_fund, private_credit, private_equity, rating_agency,
  sovereign_fund, treasury, universal_bank, venture_capital
- materiales: aluminum, cement, fiber_optic_cable, glass_fiber, graphite, high_purity_quartz, industrial_gas,
  mining_cobalt, mining_copper, mining_diversified, mining_lithium, mining_nickel, mining_pgm, mining_zinc,
  polysilicon, rare_earths, silicon_metal, specialty_chemical, steel
- inmobiliario: colocation, cooling_thermal, datacenter_operator, datacenter_reit, dc_construction, industrial_reit,
  real_estate_services

POSICIÓN DE MERCADO (market_position): es OBLIGATORIA en los niveles B y C. Para cada mercado principal indica:
- el puesto (rank) y la cuota (share_pct);
- con qué se mide (revenue, units, capacity, installed_gwh, shipments);
- la región (GLOBAL o ISO-2) y el período;
- la firma que lo mide (SNE Research, TrendForce, Gartner, IDC, IEA, BNEF, USGS…) o el informe anual.
Cada entrada lleva rank, share_pct o los dos (sin ninguno se rechaza).
Con esto el sistema puede contestar "¿cuál es la más grande en X?".

VÍNCULOS (relations): de 3 a 10 en el nivel B, todos los verificables en el nivel C. Para cada uno:
- rel_type, uno de:
  - supply = provee;
  - fab = fabrica para;
  - cloud = da nube;
  - license = licencia;
  - ppa = vende energía;
  - deploy = despliega en;
  - owns = posee;
  - invest = invierte en;
  - partner = socio (no es flujo).
- this_role = el PAPEL DE ESTA EMPRESA. NO decidas la dirección de la flecha; el sistema la calcula.
  - supply, fab, cloud, license, ppa, deploy → supplier o customer;
  - invest → investor o investee;
  - owns → owner u owned;
  - partner → partner.
- label_es y label_en en forma "lo que el proveedor da al cliente". Ejemplo: "Celdas LFP para vehículos". No uses
  "usa".
- status: active, ended, announced, planned, rumored o disputed. Un vínculo ended necesita "end".
- start y end con su fecha real si existen. Si no sabes cuándo empezó, NO pongas start (nunca la fecha de hoy).
- dependency.criticality del 1 al 6:
  - 6 = proveedor único, sin reemplazo en menos de 12 meses;
  - 5 = más del 50 % del insumo, o más de 1 año para calificar a otro proveedor;
  - 4 = proveedor principal con 1 o 2 alternativas;
  - 3 = uno de pocos;
  - 2 = uno de varios;
  - 1 = menor.
- Si están publicados: sole_source, share_of_supplier_revenue, share_of_customer_purchases, contract_value.
- evidence: al menos 1, con source_url, source_kind, as_of y una "quote" textual.
- counterparty: el nombre y TODOS los identificadores que encuentres (LEI, símbolo de Yahoo, ticker@MIC). Si la
  contraparte está en empresas_existentes.csv, pon su khipus_id exacto.
- Un vínculo dudoso NO se omite: va con status "rumored" y confidence baja. El sistema lo deja como propuesta para
  revisión humana.

DÓNDE BUSCAR (fuentes primarias primero):
- documentos oficiales:
  - EE.UU.: sec.gov/edgar (10-K, 20-F, 10-Q, 13D/13G, Exhibit 21);
  - China: cninfo.com.cn;
  - Hong Kong: hkexnews.hk;
  - Japón: EDINET / TDnet;
  - Corea: dart.fss.or.kr;
  - Taiwán: mops.twse.com.tw;
  - Europa: la página de inversores de la empresa;
- sanciones: trade.gov (Consolidated Screening List) y federalregister.gov;
- mercados: SNE Research, TrendForce, Gartner, IDC, IEA, BNEF, USGS;
- prensa seria: Reuters, Bloomberg, Nikkei, FT y prensa especializada.

PRIVADAS: en "funding" van SOLO las rondas CERRADAS, con fecha, monto, valuación post-money, líderes y fuente.
Pon live_hooks.valuation_watch = true.

PARA SEGUIRLA EN VIVO (live_hooks):
- news_keywords: el nombre corto, el nombre local y las marcas;
- ir_url;
- filings_feed: dónde publica (EDGAR, HKEXnews, CNINFO, DART, EDINET/TDnet, MOPS).

ANTES DE RESPONDER, REVISA:
- que cada número tenga source_url + as_of + quote;
- que no quede ningún "<...>";
- que no haya ningún campo prohibido;
- que cada vínculo tenga this_role y evidence;
- que todo lo que buscaste y no encontraste esté en research_meta.not_found.
```

---

## 🅱️ Prompt B: lista de ~4.000 empresas nuevas (CSV)

Pídelo **un bloque por vez**: cambia `[[ BLOQUE ]]` y `[[ CUÁNTAS ]]` según la tabla de abajo. Si un bloque pide más de
200, divídelo en tandas ("primeras 200", "siguientes 200"…).

```text
Eres un analista de cadenas de suministro. Estoy ampliando un grafo de la cadena de suministro de la IA y de sus capas
macro (energía, materiales, logística, crédito, inmobiliario) de 937 a unas 5.000 empresas. Adjunto
empresas_existentes.csv: NO repitas ninguna de esas, ni sus filiales que ya figuran con otro nombre.

BLOQUE: [[ Baterías: celdas, cátodo, ánodo, electrolito, separadores, reciclaje, almacenamiento en red ]]
CUÁNTAS: [[ 250 ]]  (en tandas de 200 como máximo)

Criterio para elegir (en este orden):
1. Peso real en la cadena: líderes mundiales por cuota o capacidad, proveedores únicos o casi únicos, cuellos de
   botella, aunque sean pequeñas o privadas.
2. Que se pueda investigar: que tenga informe anual, cotización o cobertura seria de prensa.
3. Diversidad geográfica: incluye China, Japón, Corea, Taiwán, Europa, India, Sudeste Asiático y América Latina, no
   solo EE.UU.
4. Incluye privadas y estatales importantes (por ejemplo, empresas estatales chinas o cooperativas).

Prioridad:
- P1 = imprescindible (top 3 de su mercado o proveedor crítico);
- P2 = importante;
- P3 = completa el mapa.

SALIDA: SOLO un CSV (separador coma, UTF-8, comillas dobles si el texto lleva comas). Sin texto antes ni después.
Columnas exactas:
nombre,nombre_legal,pais_iso2,estado,ticker,bolsa_mic,simbolo_yahoo,identificador,tipo_identificador,sector,categoria,capa,prioridad,por_que,fuente_url

- estado: public | private | subsidiary | state_owned
- simbolo_yahoo: con sufijo de bolsa (300750.SZ, 6752.T, 005930.KS). Vacío si no cotiza.
- identificador: el más fuerte que encuentres (LEI > ISIN > CIK > Wikidata QID). tipo_identificador = LEI | ISIN | CIK
  | QID. Si no hay ninguno, deja ambos vacíos (NO lo inventes).
- sector: uno de diseno, equipos, fabricacion, infra, cloud_ia, robotica, espacio, energia, defensa, logistica,
  macro_credito, materiales, inmobiliario.
- categoria: una id existente de Khipus (te paso la lista abajo) o "NUEVA:<id_propuesto>".
- capa: raw_materials | refining | components | equipment | fabrication | packaging | systems | networking | power |
  datacenter | cloud | models | software | applications | distribution | logistics | finance | real_estate | government
  | space | defense | robotics
- por_que: UNA frase en español (máximo 160 caracteres) sobre su papel en la cadena. Sin precio ni capitalización.
- fuente_url: un enlace que confirme que existe y qué hace (de preferencia la web oficial o el informe anual).

Categorías existentes (sector: categorías):
- diseno: asic_custom, eda, edge_ai, fabless, neuromorphic, photonics_si, quantum_hw
- equipos: chemicals, equip, materials, optics, quantum_infra
- fabricacion: foundry, memory, osat, substrates
- infra: cdn_edge, connectivity_infra, dc_reit, hpc_super, networking, power, servers
- cloud_ia: ai_agents, ai_auto, ai_finance, ai_health, ailab, aisoft, cloud
- robotica: robotics_physical
- espacio: earth_obs, satellite, space_infra, space_launch
- energia: battery_mat, energy_trading, grid_transmission, hydrogen, lng, midstream_pipeline, nuclear_equipment,
  nuclear_fusion, nuclear_operator, nuclear_smr, oil_gas_major, power_ipp, rare_earth, renewables_utility,
  storage_grid, uranium, uranium_enrichment, uranium_mining
- defensa: ai_defense, defense_prime
- logistica: air_cargo, canal_authority, freight_forwarder, heavy_lift_logistics, port_operator, rail_freight,
  shipping_line
- macro_credito: alternative_asset_manager, asset_manager, bis, cds_index_provider, central_bank,
  derivatives_standards, exchange_derivatives, exchange_index_provider, growth_equity, index_provider,
  infrastructure_investor, investment_bank, pension_fund, private_credit, private_equity, rating_agency,
  sovereign_fund, treasury, universal_bank, venture_capital
- materiales: aluminum, cement, fiber_optic_cable, glass_fiber, graphite, high_purity_quartz, industrial_gas,
  mining_cobalt, mining_copper, mining_diversified, mining_lithium, mining_nickel, mining_pgm, mining_zinc,
  polysilicon, rare_earths, silicon_metal, specialty_chemical, steel
- inmobiliario: colocation, cooling_thermal, datacenter_operator, datacenter_reit, dc_construction, industrial_reit,
  real_estate_services

Reglas:
- Nunca inventes tickers ni identificadores: si dudas, déjalos vacíos.
- Nada de precios, capitalizaciones ni valuaciones.
- Al final, revisa que no haya duplicados dentro del CSV ni contra empresas_existentes.csv.
```

### 📊 Bloques sugeridos (suman ~4.000)

| # | Bloque | Cuántas | Prioridad |
|---|---|---|---|
| 1 | 🔋 Baterías: celdas, cátodo, ánodo, electrolito, separadores, reciclaje, almacenamiento | 250 | 🔴 primero (la pregunta que falló) |
| 2 | ⚡ Energía: generación, utilities, nuclear, gas, renovables, transformadores, red eléctrica | 500 | 🔴 |
| 3 | ⛏ Materiales y minería: litio, cobre, níquel, tierras raras, galio/germanio, grafito, químicos especiales, gases | 450 | 🔴 |
| 4 | 🔬 Equipos de semiconductores y subcomponentes: litografía, depósito, grabado, metrología, vacío, ópticas, piezas | 300 | 🔴 |
| 5 | 🏭 Fabricación de chips: fundiciones, memoria, encapsulado (OSAT), sustratos, obleas | 200 | 🟡 |
| 6 | 🧠 Diseño de chips: fabless, IP, EDA, chips a medida | 200 | 🟡 |
| 7 | 🔌 Componentes electrónicos: pasivos, PCB, conectores, fuentes de poder, cables, transceptores ópticos | 300 | 🟡 |
| 8 | 🏢 Infraestructura de centros de datos: servidores, redes, refrigeración, energía, construcción, operadores | 350 | 🟡 |
| 9 | ☁️ Nube, modelos y software de IA | 300 | 🟡 |
| 10 | 🚢 Logística: navieras, puertos, aéreo de carga, ferrocarril, transitarios, almacenes | 250 | 🟡 |
| 11 | 🤖 Robótica, automatización industrial y autos | 200 | 🟢 |
| 12 | 📡 Telecom, cables submarinos, satélites y espacio | 200 | 🟢 |
| 13 | 🏦 Macro y crédito: bancos, aseguradoras, gestoras, fondos soberanos, bolsas | 250 | 🟢 |
| 14 | 🏗 Inmobiliario industrial y de centros de datos | 100 | 🟢 |
| 15 | 🛡 Defensa | 100 | 🟢 |
| | **Total** | **3.950** | |

👉 Después de cada CSV, las P1 pasan al **Prompt A con nivel B**, y las P2 y P3 con **nivel A**.
