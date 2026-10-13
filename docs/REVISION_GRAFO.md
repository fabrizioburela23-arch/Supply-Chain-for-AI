# Revisión del grafo — listas para marcar ✔ / ✘

> GENERADO por `python scripts/build_graph_review.py` desde el catálogo (`data/grafo_v0.json`). No lo edites a mano salvo las columnas ✔/✘ y "Nota tuya" (si el catálogo cambia, se regenera y hay que copiar tus marcas). La versión para máquinas es `docs/revision_grafo.json`.

## Qué es esto (en simple)

Khipus calcula el contagio de riesgos sobre el mapa de relaciones entre empresas. Encontramos datos del mapa que están mal escritos: relaciones al revés, relaciones con fecha guardadas con el tipo equivocado, pesos anotados en dos escalas distintas y palabras en español que el motor no entiende. **Nada de esto se cambia hasta que tú lo marques.** Hoy la app sigue funcionando igual.

- **(a)** 27 relaciones CON FECHA que hoy entran al motor como "provee a" aunque son inversiones, contratos de energía o van al revés.
- **(b)** 17 relaciones cuyo texto dice lo contrario de la flecha (14 no estaban en ninguna lista anterior).
- **(c)** La escala de pesos: 462 vínculos con peso 1 (no se sabe en qué escala se escribieron) y 400 con peso menor a 1.
- **(d)** 58 hechos con verbos en español que el motor ignora (controla, alberga, domina…) y 12 márgenes fuera de rango.
- **(e)** Los 200 vínculos más importantes que no tienen fecha real (para fecharlos con fuente).
- **(f)** La reconciliación catálogo ↔ base de datos (decisión #7).

## Cómo responder

Pon **✔** (de acuerdo con la propuesta) o **✘** (no) en cada fila, o en la fila "todo el grupo" cuando la haya. Si no sabes, déjala como está: **una fila sin marca no se aplica**. También puedes decirme "acepto todas las propuestas de la sección (a)". Luego mándame el archivo.

**Qué significa la flecha:** `A → B` = A le PROVEE algo a B (si A cae, B sufre). En los tipos:

| Tipo | Quiere decir | ¿Mueve el contagio? |
|---|---|---|
| `supply` | provee a | sí |
| `fab` | fabrica para | sí |
| `cloud` | da nube a | sí |
| `license` | licencia a | sí |
| `ppa` | da energía a | sí |
| `owns` | es dueño de | sí |
| `deploy` | despliega | sí |
| `invest` | invierte en | no |
| `partner` | socio de | no |
| `affects` | afecta a | no |
| `about` | trata sobre (no mueve números) | no |

## (a) Las 27 relaciones con fecha (tipo y dirección)

Hoy la migración guarda estas relaciones como "provee a" (`supply`) sin peso, y el motor les pone peso 2. Ejemplo real: el motor cree que si OpenAI cae arrastra un 18 % a Oracle, cuando la relación es la inversa. "Propuesta" dice el tipo correcto y si hay que darle vuelta a la flecha.

| # | Hecho (fecha) | Hoy | Propuesta | Por qué | Ya en el catálogo | ¿De acuerdo? | Nota tuya |
|---|---|---|---|---|---|---|---|
| 1 | Qualcomm «perdió ingresos de» Huawei (2019-05-16 → 2021-06-30) | Qualcomm → Huawei `supply` | **retirar** (es un suceso, no una relación) | Es un SUCESO (la pérdida de ventas por el veto), no una relación vigente: ya lo cuenta la noticia del hecho. | — | ✔ / ✘ | |
| 2 | TSMC «fabrica GPUs para» Nvidia (2020-01-01) | TSMC → Nvidia `supply` | **TSMC → Nvidia** `fab` (ya existe: solo se le pone la fecha) | Fabricación por encargo. | TSMC → Nvidia `fab` w6; TSMC → Nvidia `supply` w2 | ✔ / ✘ | |
| 3 | SKHynix «HBM3e para» Nvidia (2023-01-01) | SKHynix → Nvidia `supply` | **SKHynix → Nvidia** `supply` (ya existe: solo se le pone la fecha) | Venta de un producto o servicio al cliente. | SKHynix → Nvidia `supply` w6 | ✔ / ✘ | |
| 4 | ASML «EUV High-NA para» TSMC (2024-01-01) | ASML → TSMC `supply` | **ASML → TSMC** `supply` (ya existe: solo se le pone la fecha) | Venta de un producto o servicio al cliente. | ASML → TSMC `supply` w6 | ✔ / ✘ | |
| 5 | Foxconn «ensambla racks GB200 para» Nvidia (2024-06-01) | Foxconn → Nvidia `supply` | **Foxconn → Nvidia** `supply` (ya existe: solo se le pone la fecha) | Venta de un producto o servicio al cliente. | Foxconn → Nvidia `supply` w3; Nvidia → Foxconn `license` w3 | ✔ / ✘ | |
| 6 | Nvidia «invierte $5B en» Intel (2025-09-01) | Nvidia → Intel `supply` | **Nvidia → Intel** `invest` | Es una inversión (dinero), no suministro. Por defecto (BRECHAS #4) la inversión NO transmite daño. | — | ✔ / ✘ | |
| 7 | AMD «acuerdo 6GW Instinct con» OpenAI (2025-01-01) | AMD → OpenAI `supply` | **AMD → OpenAI** `supply` (ya existe: solo se le pone la fecha) | Venta de un producto o servicio al cliente. | AMD → OpenAI `supply` w4 | ✔ / ✘ | |
| 8 | Oklo «PPA 1.2 GW con» Meta (2025-06-01) | Oklo → Meta `supply` | **Oklo → Meta** `ppa` (ya existe: solo se le pone la fecha) | Contrato de energía: la flecha va de quien GENERA la energía a quien la consume. | Oklo → Meta `ppa` w3 | ✔ / ✘ | |
| 9 | Helion «PPA fusión 50 MW con» Microsoft (2023-05-01) | Helion → Microsoft `supply` | **Helion → Microsoft** `ppa` (ya existe: solo se le pone la fecha) | Contrato de energía: la flecha va de quien GENERA la energía a quien la consume. | Helion → Microsoft `ppa` w3 | ✔ / ✘ | |
| 10 | Xenergy «PPA 5+ GW con» Amazon (2024-10-01) | Xenergy → Amazon `supply` | **Xenergy → Amazon** `ppa` (ya existe: solo se le pone la fecha) | Contrato de energía: la flecha va de quien GENERA la energía a quien la consume. | Xenergy → Amazon `ppa` w3 | ✔ / ✘ | |
| 11 | RocketLab «componentes para» PlanetLabs (2022-01-01) | RocketLab → PlanetLabs `supply` | **RocketLab → PlanetLabs** `supply` (ya existe: solo se le pone la fecha) | Venta de un producto o servicio al cliente. | RocketLab → PlanetLabs `supply` w3 | ✔ / ✘ | |
| 12 | OpenAI «proyecto Stargate $500B (infra IA) con» Oracle (2025-01-21) | OpenAI → Oracle `supply` | **Oracle → OpenAI** `cloud` ⟲ al revés (ya existe: solo se le pone la fecha) | En Stargate, Oracle construye y opera la infraestructura de cómputo para OpenAI: Oracle → OpenAI (nube). | Oracle → OpenAI `cloud` w6 | ✔ / ✘ | |
| 13 | SoftBank «lidera la financiación de Stargate con» OpenAI (2025-01-21) | SoftBank → OpenAI `supply` | **SoftBank → OpenAI** `invest` (ya existe: solo se le pone la fecha) | Es una inversión (dinero), no suministro. Por defecto (BRECHAS #4) la inversión NO transmite daño. | SoftBank → OpenAI `invest` w5 | ✔ / ✘ | |
| 14 | xAI «Colossus: 100k+ GPUs de» Nvidia (2024-09-01) | xAI → Nvidia `supply` | **Nvidia → xAI** `supply` ⟲ al revés (ya existe: solo se le pone la fecha) | "X: GPUs de Y" quiere decir que Y le VENDE las GPUs a X: la flecha va al revés. | Nvidia → xAI `supply` w5 | ✔ / ✘ | |
| 15 | Nvidia «respalda y coloca GPUs en» CoreWeave (2023-04-01) | Nvidia → CoreWeave `supply` | **Nvidia → CoreWeave** `invest` (ya existe: solo se le pone la fecha) | Es una inversión (dinero), no suministro. Por defecto (BRECHAS #4) la inversión NO transmite daño. | Nvidia → CoreWeave `cloud` w6; Nvidia → CoreWeave `invest` w4; Nvidia → CoreWeave `supply` w2 | ✔ / ✘ | |
| 16 | Microsoft «invirtió ~$13B en» OpenAI (2023-01-23) | Microsoft → OpenAI `supply` | **Microsoft → OpenAI** `invest` (ya existe: solo se le pone la fecha) | Es una inversión (dinero), no suministro. Por defecto (BRECHAS #4) la inversión NO transmite daño. | Microsoft → OpenAI `cloud` w6; Microsoft → OpenAI `invest` w5; OpenAI → Microsoft `deploy` w3 | ✔ / ✘ | |
| 17 | Amazon «invierte $8B en» Anthropic (2024-11-22) | Amazon → Anthropic `supply` | **Amazon → Anthropic** `invest` (ya existe: solo se le pone la fecha) | Es una inversión (dinero), no suministro. Por defecto (BRECHAS #4) la inversión NO transmite daño. | Amazon → Anthropic `cloud` w6; Amazon → Anthropic `invest` w4 | ✔ / ✘ | |
| 18 | Alphabet «respalda con >$3B a» Anthropic (2025-01-01) | Alphabet → Anthropic `supply` | **Alphabet → Anthropic** `invest` (ya existe: solo se le pone la fecha) | Es una inversión (dinero), no suministro. Por defecto (BRECHAS #4) la inversión NO transmite daño. | Alphabet → Anthropic `cloud` w4; Alphabet → Anthropic `invest` w3 | ✔ / ✘ | |
| 19 | Meta «invierte $14.3B (49%) en» ScaleAI (2025-06-12) | Meta → ScaleAI `supply` | **Meta → ScaleAI** `invest` (ya existe: solo se le pone la fecha) | Es una inversión (dinero), no suministro. Por defecto (BRECHAS #4) la inversión NO transmite daño. | Meta → ScaleAI `invest` w3 | ✔ / ✘ | |
| 20 | Micron «HBM3e calificada para» Nvidia (2024-02-26) | Micron → Nvidia `supply` | **Micron → Nvidia** `supply` (ya existe: solo se le pone la fecha) | Venta de un producto o servicio al cliente. | Micron → Nvidia `supply` w3 | ✔ / ✘ | |
| 21 | Samsung «HBM3e en calificación para» Nvidia (2024-07-01) | Samsung → Nvidia `supply` | **Samsung → Nvidia** `supply` (ya existe: solo se le pone la fecha) | Venta de un producto o servicio al cliente. | Samsung → Nvidia `supply` w2 | ✔ / ✘ | |
| 22 | Broadcom «co-diseña las TPU de» Alphabet (2016-01-01) | Broadcom → Alphabet `supply` | **Broadcom → Alphabet** `supply` (ya existe: solo se le pone la fecha) | Diseña el chip a medida para el cliente (servicio de diseño + venta del chip). | Broadcom → Alphabet `cloud` w4; Broadcom → Alphabet `supply` w5 | ✔ / ✘ | |
| 23 | Broadcom «ASIC de IA (MTIA) para» Meta (2024-01-01) | Broadcom → Meta `supply` | **Broadcom → Meta** `supply` (ya existe: solo se le pone la fecha) | Venta de un producto o servicio al cliente. | Broadcom → Meta `supply` w4 | ✔ / ✘ | |
| 24 | Marvell «co-diseña Trainium/Inferentia con» Amazon (2023-01-01) | Marvell → Amazon `supply` | **Marvell → Amazon** `supply` | Diseña el chip a medida para el cliente (servicio de diseño + venta del chip). | Marvell → Amazon `cloud` w3 | ✔ / ✘ | |
| 25 | Constellation «reabre Three Mile Island (835MW) para» Microsoft (2024-09-20) | Constellation → Microsoft `supply` | **Constellation → Microsoft** `ppa` | Contrato de energía: la flecha va de quien GENERA la energía a quien la consume. | Constellation → Microsoft `cloud` w4 | ✔ / ✘ | |
| 26 | Alphabet «PPA de reactores SMR con» KairosPower (2024-10-14) | Alphabet → KairosPower `supply` | **KairosPower → Alphabet** `ppa` ⟲ al revés (ya existe: solo se le pone la fecha) | Contrato de energía: la flecha va de quien GENERA la energía a quien la consume. | KairosPower → Alphabet `ppa` w2 | ✔ / ✘ | |
| 27 | Vertiv «refrigeración líquida para racks de» Nvidia (2024-01-01) | Vertiv → Nvidia `supply` | **Vertiv → Nvidia** `supply` (ya existe: solo se le pone la fecha) | Venta de un producto o servicio al cliente. | Vertiv → Nvidia `supply` w3 | ✔ / ✘ | |

## (b) Relaciones cuyo texto dice lo contrario de la flecha (17)

El texto de la relación nombra como CLIENTE (el que usa, compra o adquirió) a quien la flecha pone como PROVEEDOR. "La correcta ya existe" = la relación en el sentido bueno ya está en el mapa: solo se borra la equivocada. Las marcadas "lista anterior" ya aparecían en la auditoría como par en los dos sentidos; ahora el texto dice cuál de los dos está mal.

Ojo con las de tipo `owns` ("es dueño de"): ahí la flecha va del DUEÑO a lo que posee. En esas filas el texto dice que alguien COMPRÓ (adquirió) a otro, y el comprador quedó como destino de la flecha en vez de como origen: la propuesta lo pone como origen (dueño → empresa comprada).

| # | Hoy | Texto | Propuesta | Lista anterior | ¿De acuerdo? | Nota tuya |
|---|---|---|---|---|---|---|
| 1 | BostonDynamics → Nvidia `supply` w3 | «Spot y Atlas usan módulos Jetson para percepción IA en campo» | borrar (la correcta Nvidia → BostonDynamics `supply` ya existe) | sí | ✔ / ✘ | |
| 2 | Palantir → Amazon `license` w5 | «AIP corre sobre AWS — mayor proveedor de infra de Palantir» | borrar (la correcta Amazon → Palantir `cloud` ya existe) | no | ✔ / ✘ | |
| 3 | Snowflake → Nvidia `supply` w2 | «Snowflake Cortex AI usa GPUs Nvidia para modelos in-database» | dar vuelta: **Nvidia → Snowflake** `supply` | no | ✔ / ✘ | |
| 4 | OpenAI → Nvidia `supply` w4 | «ChatGPT usa clusters de H100/H200 para inferencia a 100M+ usuarios» | dar vuelta: **Nvidia → OpenAI** `supply` | no | ✔ / ✘ | |
| 5 | Qwen → Nvidia `supply` w3 | «Alibaba usa clusters H800/H20 para entrenamiento Qwen 2.5/3» | dar vuelta: **Nvidia → Qwen** `supply` | no | ✔ / ✘ | |
| 6 | Samsung → SKHynix `fab` w2 | «Compite en DRAM/NAND — referencia de proceso para HBM4» | borrar (competir o haber fundado no es suministrar) | no | ✔ / ✘ | |
| 7 | Tesla → OpenAI `supply` w1 | «Elon Musk co-fundó OpenAI; ahora competidores directos» | borrar (competir o haber fundado no es suministrar) | no | ✔ / ✘ | |
| 8 | BostonDynamics → OpenAI `supply` w1 | «Boston Dynamics usa GPT-4V para comprensión semántica de entornos» | dar vuelta: **OpenAI → BostonDynamics** `supply` | no | ✔ / ✘ | |
| 9 | SouthernCo → Westinghouse `supply` w3 | «Vogtle 3 y 4 usan reactores AP1000 de Westinghouse, primeros en operación comercial en EEUU» | borrar (la correcta Westinghouse → SouthernCo `supply` ya existe) | sí | ✔ / ✘ | |
| 10 | Data4 → Brookfield `owns` w5 | «Brookfield Infrastructure adquirió Data4 de AXA IM Alts en 2023 (~€3.5bn); Brookfield financia el plan de expansión de €20bn a 2030» | dar vuelta: **Brookfield → Data4** `owns` | no | ✔ / ✘ | |
| 11 | AirTrunk → Blackstone `owns` w5 | «Blackstone lidera el consorcio que adquirió AirTrunk de Macquarie/PSP por A$24bn (US$16.1bn), cerrado dic-2024» | dar vuelta: **Blackstone → AirTrunk** `owns` | no | ✔ / ✘ | |
| 12 | Teraco → DigitalRealty `owns` w5 | «Digital Realty adquirió ~55% de Teraco en una transacción de $3.5bn anunciada ene-2022 y cerrada en 1H2022» | dar vuelta: **DigitalRealty → Teraco** `owns` | no | ✔ / ✘ | |
| 13 | ODATA → AlignedDataCenters `owns` w5 | «Aligned Data Centers adquirió ODATA en 2023 para expandir su presencia panamericana hacia Brasil, Chile, Colombia y México» | borrar (la correcta AlignedDataCenters → ODATA `owns` ya existe) | sí | ✔ / ✘ | |
| 14 | CoreSite → americantower `owns` w5 | «American Tower adquirió CoreSite por ~$10.1bn en nov-2021; Stonepeak posee 36% de la JV del negocio de datacenters de American Tower desde o» | dar vuelta: **americantower → CoreSite** `owns` | no | ✔ / ✘ | |
| 15 | CompassDatacenters → Brookfield `owns` w5 | «Brookfield Infrastructure adquirió control conjunto de Compass Datacenters junto a Ontario Teachers' Pension Plan por $5.5bn (jun-2023)» | dar vuelta: **Brookfield → CompassDatacenters** `owns` | no | ✔ / ✘ | |
| 16 | DSV → MSC `supply` w4 | «DSV compra capacidad de bodega a MSC» | dar vuelta: **MSC → DSV** `supply` | no | ✔ / ✘ | |
| 17 | DSV → APMTerminals `supply` w2 | «DSV utiliza terminales operadas por APM Terminals sin activos portuarios propios» | dar vuelta: **APMTerminals → DSV** `supply` | no | ✔ / ✘ | |

## (c) Una sola escala de pesos: de 0 a 1

**En simple:** el "peso" dice cuánto depende el cliente de ese proveedor. Casi todo el catálogo lo anotó de 1 a 6, pero un archivo (`nodes/nodes_expand5.js`) lo anotó de 0 a 1 — y además muchos de esos números no son un peso sino la "importancia del tipo" copiada (por ejemplo 0,9 en todas las nubes), que el motor vuelve a multiplicar: se aplica DOS veces. Resultado: 400 vínculos (los de peso menor a 1) cuentan mucho menos de lo que deberían (41 de ellos son el ÚNICO proveedor de ese tipo y hoy transmiten como máximo un 15 %).

**La propuesta** es pasar todo a una escala de 0 a 1 (1 = el cliente depende por completo):

- Peso de 1 a 6 → peso ÷ 6 (un 6 pasa a 1; un 3 pasa a 0,5; un 1 pasa a 0,17).
- Peso de 0 a 1 de verdad → se queda.
- "Importancia del tipo" copiada → no sabemos el peso real: se usa el TÍPICO de su tipo (la mediana de los vínculos de 1 a 6 de ese tipo, ÷ 6). Puedes corregir cualquiera.
- Cuando esto se aplique, el motor cambia a la vez el "piso del proveedor único" de 6 a 1 (mismo resultado para los vínculos 1-6) y se verifica con la prueba de paridad.

| Tipo | Vínculos | Peso < 1 | Peso = 1 | Peso > 1 | "Importancia copiada" | Típico (1-6) |
|---|---:|---:|---:|---:|---:|---:|
| `about` | 4 | 0 | 0 | 4 | 0 | 2 |
| `cloud` | 307 | 44 | 27 | 236 | 44 | 2 |
| `deploy` | 19 | 2 | 3 | 14 | 2 | 3 |
| `fab` | 83 | 0 | 18 | 65 | 14 | 2 |
| `invest` | 192 | 34 | 6 | 152 | 34 | 4 |
| `license` | 63 | 17 | 8 | 38 | 17 | 2 |
| `owns` | 51 | 6 | 0 | 45 | 6 | 5 |
| `partner` | 756 | 263 | 136 | 357 | 263 | 3 |
| `ppa` | 34 | 2 | 4 | 28 | 2 | 3 |
| `supply` | 1001 | 32 | 260 | 709 | 144 | 2 |

### Los 462 vínculos con peso 1, uno por uno

Primero marca el grupo entero (si estás de acuerdo con la regla del grupo); después, si quieres, cambia filas sueltas.

#### Escritos de 1 a 6 (peso 1 = dependencia débil) → 0,17 — 294

**Todo el grupo:** ✔ / ✘

| # | Vínculo | Tipo | Archivo | Propuesta (0-1) | ¿De acuerdo? |
|---|---|---|---|---:|---|
| 1 | ASN → Alphabet | `cloud` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 2 | ASN → Microsoft | `cloud` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 3 | Apptronik → Alphabet | `cloud` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 4 | Apptronik → Amazon | `cloud` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 5 | BostonDynamics → Amazon | `cloud` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 6 | Cisco → Amazon | `cloud` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 7 | DWave → Amazon | `cloud` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 8 | DigitalRealty → Nebius | `cloud` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 9 | Equinix → Microsoft | `cloud` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 10 | Foxconn → CoreWeave | `cloud` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 11 | Groq → Microsoft | `cloud` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 12 | HPE → Microsoft | `cloud` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 13 | IBMQuantum → Alphabet | `cloud` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 14 | IBMQuantum → Amazon | `cloud` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 15 | Jabil → Amazon | `cloud` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 16 | Jabil → CoreWeave | `cloud` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 17 | Lenovo → Microsoft | `cloud` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 18 | Lenovo → Nebius | `cloud` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 19 | Lumen → Oracle | `cloud` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 20 | NEC → Microsoft | `cloud` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 21 | OneX → Amazon | `cloud` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 22 | Pasqal → Microsoft | `cloud` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 23 | Rigetti → Amazon | `cloud` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 24 | Rigetti → Microsoft | `cloud` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 25 | SambaNova → Amazon | `cloud` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 26 | Schneider → Nebius | `cloud` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 27 | SuperMicro → Oracle | `cloud` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 28 | Apptronik → Amazon | `deploy` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 29 | BostonDynamics → Alphabet | `deploy` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 30 | Figure → Microsoft | `deploy` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 31 | Entegris → SKHynix | `fab` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 32 | Linde → Micron | `fab` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 33 | MerckKGaA → Intel | `fab` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 34 | TSMC → WesternDigital | `fab` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 35 | BMW → Figure | `invest` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 36 | LiontownResources → Albemarle | `invest` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 37 | Mubadala → AMD | `invest` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 38 | Nakilat → BlackRock | `invest` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 39 | Nakilat → Vanguard | `invest` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 40 | NxtraData → CDPQ | `invest` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 41 | ARM → GF | `license` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 42 | ARM → Microsoft | `license` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 43 | Cadence → Marvell | `license` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 44 | Microsoft → Mistral | `license` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 45 | Qualcomm → Apple | `license` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 46 | SiemensEDA → Broadcom | `license` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 47 | SiemensEDA → Intel | `license` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 48 | SumitomoElectric → Corning | `license` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 49 | ADNOC → QatarEnergy | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 50 | AirProducts → Linde | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 51 | Albemarle → SQM | `partner` | nodes/links_all.js | 0,17 | ✔ / ✘ |
| 52 | Alphabet → SambaNova | `partner` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 53 | Anduril → ShieldAI | `partner` | nodes/links_all.js | 0,17 | ✔ / ✘ |
| 54 | Antofagasta → Codelco | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 55 | Antofagasta → RioTinto | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 56 | Asetek → CoolIT Systems | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 57 | AustralianStrategicMaterials → UcoreRareMetals | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 58 | BallardPower → PlugPower | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 59 | BloomEnergy → Vertiv | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 60 | Boliden → KGHM | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 61 | CBRE Group → Turner Construction | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 62 | CMOC → EurasianResourcesGroup | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 63 | CNOOC → PetroChina | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 64 | CanadianNational → COSCOShipping | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 65 | Cargolux → Qatar_Airways_Cargo | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 66 | ChinaNorthernRareEarth → Lynas | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 67 | ChinaNorthernRareEarth → MP_Materials | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 68 | ChinaRareEarthGroup → MP_Materials | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 69 | Colliers → Alphabet | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 70 | Colliers → Blackstone | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 71 | Comfort Systems USA → EMCOR Group | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 72 | ConocoPhillips → QatarEnergy | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 73 | CoolIT Systems → Vertiv | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 74 | Cushman & Wakefield → Amazon | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 75 | DHL_Group → Boeing | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 76 | EDF → RollsRoyceSMR | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 77 | EDF → Westinghouse | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 78 | EMCOR Group → Comfort Systems USA | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 79 | EON → RWE | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 80 | ElevenLabs → Cohere | `partner` | nodes/links_all.js | 0,17 | ✔ / ✘ |
| 81 | Enel → Iberdrola | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 82 | EnergyTransfer → WilliamsCompanies | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 83 | Engie → EDF | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 84 | Engie → RWE | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 85 | Eni → TotalEnergies | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 86 | Equinor → WilliamsCompanies | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 87 | Eramet → ZijinMining | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 88 | EurasianResourcesGroup → Glencore | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 89 | FedEx → Boeing | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 90 | FirstQuantumMinerals → Codelco | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 91 | FirstQuantumMinerals → IvanhoeMines | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 92 | FreeportMcMoRan → Codelco | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 93 | FreeportMcMoRan → SouthernCopper | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 94 | Gazprom → Rosneft | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 95 | Glencore → Shell | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 96 | Globalstar → AST_SpaceMobile | `partner` | nodes/links_all.js | 0,17 | ✔ / ✘ |
| 97 | GraphiteOne → NextSourceMaterials | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 98 | Groq → OpenAI | `partner` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 99 | Gunvor → Lukoil | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 100 | HDR Inc → Jacobs Engineering | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 101 | HindustanZinc → Boliden | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 102 | HindustanZinc → Vedanta_Semi | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 103 | ICE → GE_Aerospace | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 104 | ICE → Salesforce | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 105 | ITCHoldings → AEP | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 106 | Iberdrola → NationalGrid | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 107 | Iberdrola → RWE | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 108 | IlukaResources → MP_Materials | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 109 | IvanhoeMines → FirstQuantumMinerals | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 110 | JLL → DigitalRealty | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 111 | JLL → Microsoft | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 112 | Jacobs Engineering → HDR Inc | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 113 | JinchuanGroup → CMOC | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 114 | KGHM → Boliden | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 115 | KIONetworks → ODATA | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 116 | KansaiElectric → TEPCO | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 117 | Kratos_Defense → Anduril | `partner` | nodes/links_all.js | 0,17 | ✔ / ✘ |
| 118 | LithiumAmericas → PiedmontLithium | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 119 | Lukoil → Gunvor | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 120 | MP_Materials → Lynas | `partner` | nodes/links_all.js | 0,17 | ✔ / ✘ |
| 121 | Meeza → MoroHub | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 122 | Meta → OpenAI | `partner` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 123 | Mistral → OpenAI | `partner` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 124 | Mobileye → AuroraInnovation | `partner` | nodes/links_all.js | 0,17 | ✔ / ✘ |
| 125 | NationalGrid → SSE | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 126 | Naver → Alphabet | `partner` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 127 | NelASA → AirProducts | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 128 | Newmark Group → DigitalRealty | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 129 | Nexans → SiemensEnergy | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 130 | NextSourceMaterials → GraphiteOne | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 131 | NickelIndustries → PTValeIndonesia | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 132 | Occidental → AirProducts | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 133 | OpenAI → Anthropic | `partner` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 134 | Orsted → DominionEnergy | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 135 | Orsted → NationalGrid | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 136 | PTValeIndonesia → NickelIndustries | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 137 | PilbaraMinerals → SQM | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 138 | PlugPower → AirProducts | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 139 | Prysmian → SubCom | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 140 | Qatar_Airways_Cargo → Cargolux | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 141 | RWE → EON | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 142 | RaxioGroup → AfricaDataCentres | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 143 | RioTinto → TalonMetals | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 144 | Rosatom → CentrusEnergy | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 145 | Rosatom → Gazprom | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 146 | Rosneft → Gazprom | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 147 | SSE → RollsRoyceSMR | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 148 | SaudiAramco → ExxonMobil | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 149 | ScalaDataCenters → IonQ | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 150 | Sempra → PGECorp | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 151 | Shell → Glencore | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 152 | Sify → DigitalRealty | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 153 | Silk_Way_West → Airbus | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 154 | Sinopec → PetroChina | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 155 | Sonatrach → TotalEnergies | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 156 | SouthernCo → BerkshireHathawayEnergy | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 157 | SouthernCo → PJM | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 158 | SpaceX → RocketLab | `partner` | nodes/links_all.js | 0,17 | ✔ / ✘ |
| 159 | StandardLithium → LithiumAmericas | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 160 | StateGridChina → CGNPower | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 161 | Sterling Infrastructure → Eaton | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 162 | Sterling Infrastructure → Quanta | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 163 | TAETechnologies → Alphabet | `partner` | nodes/nodes_nuclear.js | 0,17 | ✔ / ✘ |
| 164 | TEPCO → KansaiElectric | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 165 | TotalEnergies → SiemensEnergy | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 166 | UcoreRareMetals → AustralianStrategicMaterials | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 167 | UcoreRareMetals → EnergyFuels | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 168 | Vale → SouthernCopper | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 169 | Vattenfall → RWE | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 170 | Vattenfall → RollsRoyceSMR | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 171 | Volga_Dnepr → DHL_Group | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 172 | Westinghouse → BerkshireHathawayEnergy | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 173 | WilliamsCompanies → Vertiv | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 174 | Woodside → CheniereEnergy | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 175 | XcelEnergy → PJM | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 176 | Xiaomi → Unitree | `partner` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 177 | ZijinMining → GanfengLithium | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 178 | ZijinMining → SQM | `partner` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 179 | ADNOC → Glencore | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 180 | AECOM → Huawei | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 181 | AGC → ASML | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 182 | AirLiquide → SMIC | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 183 | AirLiquide → Samsung | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 184 | Air_Charter_Service → GE_Aerospace | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 185 | Alcoa → TSMC | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 186 | Amkor → Nvidia | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 187 | Amphenol → Foxconn | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 188 | AnhuiConch → AlibabaCloud | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 189 | AnhuiConch → SMIC | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 190 | Antonov_Airlines → SiemensEnergy | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 191 | ArcelorMittal → TSMC | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 192 | ArcelorMittal → Vertiv | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 193 | Astera → SuperMicro | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 194 | BNSFRailway → GEVernova | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 195 | BP → WilliamsCompanies | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 196 | BerkshireHathawayEnergy → Alphabet | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 197 | Besi → Intel | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 198 | Boliden → Vertiv | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 199 | BostonDynamics → OpenAI | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 200 | Broadcom → Cisco | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 201 | CLPGroup → TataSemiconductor | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 202 | CPKC → KIA | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 203 | CRH → CoreWeave | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 204 | CSXCorp → Boeing | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 205 | Cambricon → DeepSeek | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 206 | Cemex → TSMC | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 207 | Chalco → AlibabaCloud | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 208 | Chalco → YOFC | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 209 | Chapman_Freeborn → GE_Aerospace | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 210 | CheniereEnergy → Vitol | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 211 | ChinaBaowu → AlibabaCloud | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 212 | ChinaBaowu → SMIC | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 213 | Ciena → Meta | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 214 | Comfort Systems USA → DPR Construction | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 215 | ConocoPhillips → Vitol | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 216 | Corning → ASN | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 217 | DHL_Group → Vertiv | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 218 | DeltaElectronics → Dell | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 219 | EMCOR Group → Bechtel | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 220 | Elkem → MerckKGaA | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 221 | EnergyTransfer → BloomEnergy | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 222 | EnterpriseProductsPartners → ConocoPhillips | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 223 | Envicool → Huawei | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 224 | Equinor → Gunvor | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 225 | Fagioli → Vertiv | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 226 | FedEx → TSMC | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 227 | FormFactor → IBMQuantum | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 228 | FormFactor → Rigetti | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 229 | GlobalWafers → Intel | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 230 | GrupoMexico → Vertiv | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 231 | Gunvor → Rosneft | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 232 | HemlockSemiconductor → Intel | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 233 | Jacobs Engineering → Microsoft | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 234 | Kalitta_Air → GE_Aerospace | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 235 | KinderMorgan → Chevron | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 236 | Kioxia → HPE | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 237 | KuehneNagel → SiemensEnergy | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 238 | MPWR → SuperMicro | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 239 | MSCI → AlphaSense | `supply` | nodes/links_all.js | 0,17 | ✔ / ✘ |
| 240 | Marvell → Dell | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 241 | Maximus_Air → ADNOC | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 242 | Mercuria → TotalEnergies | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 243 | Micron → HPE | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 244 | MitsuiChemicals → TSMC | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 245 | NipponSteel → TSMC | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 246 | NorfolkSouthern → Nucor | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 247 | Nornickel → Tesla | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 248 | Nucor → Equinix | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 249 | Nvidia → CrowdStrike | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 250 | Occidental → Vitol | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 251 | OpenAI → CrowdStrike | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 252 | OpenAI → Palantir | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 253 | OpenAI → Snowflake | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 254 | OxfordInstruments → DWave | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 255 | OxfordInstruments → Quantinuum | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 256 | PGECorp → Apple | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 257 | POSCO → Samsung | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 258 | Petrobras → Glencore | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 259 | Petronas → Vitol | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 260 | Quanta Services → Bechtel | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 261 | QuantumMachines → PsiQuantum | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 262 | Qwen → Unitree | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 263 | Repsol → Trafigura | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 264 | Rusal → TSMC | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 265 | SKHynix → SuperMicro | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 266 | SMIC → Lenovo | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 267 | SSAB → GEVernova | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 268 | SanDisk → Lenovo | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 269 | ScaleAI → ElevenLabs | `supply` | nodes/links_all.js | 0,17 | ✔ / ✘ |
| 270 | SchottAG → Intel | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 271 | Screen → SMIC | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 272 | Sibelco → First_Solar | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 273 | Siltronic → Intel | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 274 | Siltronic → Samsung | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 275 | SouthernCopper → Vertiv | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 276 | Sterling Infrastructure → Hensel Phelps | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 277 | SumitomoElectric → CoreWeave | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 278 | TataSteel → Vedanta_Semi | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 279 | TeckResources → Vertiv | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 280 | Tesla → OpenAI | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 281 | TexasInstruments → Dell | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 282 | TexasInstruments → Foxconn | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 283 | TexasInstruments → Tesla | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 284 | Tokuyama → Equinix | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 285 | TotalEnergies → Gunvor | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 286 | Toto → AMAT | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 287 | Trafigura → Repsol | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 288 | TransGlobalProjects → SiemensEnergy | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 289 | VentureGlobalLNG → Shell | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 290 | Volga_Dnepr → Rosatom | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 291 | WilliamsCompanies → Constellation | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 292 | Woodside → Gunvor | `supply` | nodes/nodes_multicapa.js | 0,17 | ✔ / ✘ |
| 293 | YMTC → Lenovo | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |
| 294 | onsemi → Vertiv | `supply` | nodes/nodes_seed.js | 0,17 | ✔ / ✘ |

#### Escritos de 0 a 1 con la "importancia del tipo" copiada → peso típico de su tipo — 158

**Todo el grupo:** ✔ / ✘

| # | Vínculo | Tipo | Archivo | Propuesta (0-1) | ¿De acuerdo? |
|---|---|---|---|---:|---|
| 1 | GF → Innatera | `fab` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 2 | GF → Lightelligence | `fab` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 3 | GF → Mythic | `fab` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 4 | GF → RockleyPhotonics | `fab` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 5 | GF → Untether_AI | `fab` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 6 | TSMC → Cerebras | `fab` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 7 | TSMC → Cirrus_Logic | `fab` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 8 | TSMC → Diodes | `fab` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 9 | TSMC → GreenWaves | `fab` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 10 | TSMC → Kneron | `fab` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 11 | TSMC → PowerIntegrations | `fab` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 12 | TSMC → Semtech | `fab` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 13 | TSMC → SiMa | `fab` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 14 | TSMC → Untether_AI | `fab` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 15 | AMD → tensorwave | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 16 | AirProducts → Samsung | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 17 | ArcadiumLithium → BMW | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 18 | Array_Technologies → Lightsource_BP | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 19 | Bluefors → infleqtion | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 20 | Bluefors → iqm-quantum | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 21 | Bluefors → seeqc-quantum | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 22 | BossEnergy → Constellation | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 23 | Cerebras → OpenAI | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 24 | ChinaNorthernRareEarth → BMW | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 25 | ChinaNorthernRareEarth → GEVernova | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 26 | ChinaNorthernRareEarth → Tesla | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 27 | Cirrus_Logic → Samsung | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 28 | Cohu → STMicroelectronics | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 29 | Cohu → TexasInstruments | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 30 | Cohu → onsemi | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 31 | Danaher → Intel | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 32 | Danaher → Samsung | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 33 | DenisonMines → Constellation | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 34 | Diodes → BMW | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 35 | Diodes → Dell | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 36 | First_Solar → Lightsource_BP | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 37 | GE_Aerospace → Boeing | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 38 | GE_Aerospace → general-dynamics | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 39 | GlobalAtomic → Constellation | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 40 | Huawei → agibot-zhiyuan | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 41 | L3Harris → textron-systems | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 42 | Livent → BMW | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 43 | Lynas → ubtech-robotics | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 44 | MACOM → L3Harris | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 45 | MACOM → Nvidia | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 46 | MACOM → Raytheon | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 47 | Maxar → HughesNetwork | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 48 | Micron → Penguin_Solutions | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 49 | NexGenEnergy → Constellation | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 50 | NexTracker → Lightsource_BP | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 51 | NioCorp → GE_Aerospace | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 52 | NioCorp → Raytheon | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 53 | Northrop → lockheed-martin | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 54 | Nvidia → Cognition | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 55 | Nvidia → Crane_NXT | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 56 | Nvidia → Pegatron | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 57 | Nvidia → Suno | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 58 | Nvidia → ambi-robotics | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 59 | Nvidia → chef-robotics | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 60 | Nvidia → crusoe-energy | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 61 | Nvidia → dexterity | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 62 | Nvidia → diligent-robotics | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 63 | Nvidia → fluidstack | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 64 | Nvidia → fourier-intelligence | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 65 | Nvidia → lightning-ai | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 66 | Nvidia → lockheed-martin | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 67 | Nvidia → locus-robotics | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 68 | Nvidia → northern-data | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 69 | Nvidia → nscale | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 70 | Nvidia → poolside-ai | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 71 | Nvidia → righthand-robotics | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 72 | Nvidia → skydio | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 73 | Nvidia → vicarious-surgical | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 74 | Nvidia → voltage-park | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 75 | Nvidia → waabi | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 76 | Nvidia → world-labs | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 77 | Nvidia → yotta-data-services | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 78 | Orano → Constellation | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 79 | OxfordInstruments → iqm-quantum | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 80 | PaladinEnergy → Constellation | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 81 | Pegatron → Microsoft | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 82 | Penguin_Solutions → CoreWeave | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 83 | PowerIntegrations → Vertiv | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 84 | Qualcomm → skydio | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 85 | Qualcomm → wing-alphabet | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 86 | Qualcomm → zipline | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 87 | Raytheon → Airbus | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 88 | Raytheon → Boeing | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 89 | Raytheon → Saab_AB | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 90 | RocketLab → varda-space-industries | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 91 | RockleyPhotonics → Apple | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 92 | SQM → BMW | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 93 | SQM → Tesla | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 94 | STMicroelectronics → Thales | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 95 | Seagate → Alphabet | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 96 | Seagate → Amazon | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 97 | Seagate → Microsoft | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 98 | Semtech → Nvidia | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 99 | Silicom → PaloAltoNetworks | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 100 | Teledyne_Flir → Anduril | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 101 | Teledyne_Flir → Raytheon | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 102 | Thales → AxiomSpace | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 103 | Thales → dassault-aviation | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 104 | Trimble_Inc → Boeing | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 105 | Trumpf → Airbus | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 106 | Trumpf → BMW | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 107 | UrEnergy → Constellation | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 108 | UraniumEnergy → Constellation | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 109 | Zeiss → Samsung | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 110 | Zeiss → TSMC | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 111 | americantower → T_Mobile | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 112 | babcock-international → Airbus | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 113 | biren → AlibabaCloud | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 114 | chang-chun-group → TSMC | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 115 | chindata → AlibabaCloud | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 116 | chipbond → Himax_Tech | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 117 | chipbond → Navitas | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 118 | colt → CBOE | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 119 | colt → VirtuFinancial | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 120 | crowncastle → T_Mobile | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 121 | elbit-systems → Kratos_Defense | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 122 | f5 → T_Mobile | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 123 | fabrinet → Ciena | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 124 | fabrinet → Cisco | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 125 | fabrinet → Lumentum | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 126 | fabrinet → Nvidia | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 127 | gds → AlibabaCloud | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 128 | jcet → Cambricon | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 129 | jcet → HiSilicon | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 130 | kanto-denka-kogyo → Micron | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 131 | kanto-denka-kogyo → Rapidus | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 132 | kanto-denka-kogyo → SKHynix | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 133 | kanto-denka-kogyo → Samsung | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 134 | kanto-denka-kogyo → TSMC | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 135 | karman-space-defense → Northrop | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 136 | karman-space-defense → Raytheon | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 137 | loongson → Lenovo | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 138 | moorethreads → AlibabaCloud | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 139 | nexperia → BMW | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 140 | nexperia → Stellantis | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 141 | pti → Micron | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 142 | pti → Nanya | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 143 | pti → SKHynix | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 144 | rafael-advanced-defense → Leonardo_DRS | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 145 | resonac-holdings → TSMC | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 146 | sba → T_Mobile | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 147 | sidus-space → BlueOrigin | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 148 | sidus-space → SpaceX | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 149 | stack-infra → Amazon | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 150 | stella-chemifa → SKHynix | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 151 | sumitomo-chemical → TSMC | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 152 | unisoc → Xiaomi | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 153 | vantage-dc → Meta | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 154 | vantage-dc → Microsoft | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 155 | vishay → BMW | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 156 | vishay → Rockwell_Automation | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 157 | vishay → Vertiv | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |
| 158 | wingtech → Xiaomi | `supply` | nodes/nodes_expand5.js | 0,33 | ✔ / ✘ |

#### Escritos de 0 a 1 de verdad → 1 (dependencia total) — 10

**Todo el grupo:** ✔ / ✘

| # | Vínculo | Tipo | Archivo | Propuesta (0-1) | ¿De acuerdo? |
|---|---|---|---|---:|---|
| 1 | AEP → Meta | `partner` | nodes/nodes_expand5.js | 1 | ✔ / ✘ |
| 2 | GeneralFusion → Helion | `partner` | nodes/nodes_expand5.js | 1 | ✔ / ✘ |
| 3 | PSEG → Constellation | `partner` | nodes/nodes_expand5.js | 1 | ✔ / ✘ |
| 4 | RollsRoyceSMR → SiemensEnergy | `partner` | nodes/nodes_expand5.js | 1 | ✔ / ✘ |
| 5 | TalenEnergy → Constellation | `partner` | nodes/nodes_expand5.js | 1 | ✔ / ✘ |
| 6 | ZapEnergy → Helion | `partner` | nodes/nodes_expand5.js | 1 | ✔ / ✘ |
| 7 | DukeEnergy → Microsoft | `ppa` | nodes/nodes_expand5.js | 1 | ✔ / ✘ |
| 8 | NRGEnergy → CoreWeave | `ppa` | nodes/nodes_expand5.js | 1 | ✔ / ✘ |
| 9 | PPLCorp → Microsoft | `ppa` | nodes/nodes_expand5.js | 1 | ✔ / ✘ |
| 10 | PSEG → Alphabet | `ppa` | nodes/nodes_expand5.js | 1 | ✔ / ✘ |

### Los 17 vínculos con el MISMO número en todo su tipo — ¿peso real o importancia copiada?

En el archivo 0-1, todos los `license` llevan 0,8. Un mismo número en todas las filas casi nunca es un peso medido: la propuesta los trata como "importancia copiada" (peso típico de su tipo). Si son pesos reales, marca ✘ y se quedan como están.

**Todo el grupo:** ✔ / ✘

| # | Vínculo | Tipo | Peso hoy | Propuesta (0-1) | ¿De acuerdo? |
|---|---|---|---:|---:|---|
| 1 | ARM → Innatera | `license` | 0,8 | 0,33 | ✔ / ✘ |
| 2 | ARM → SiMa | `license` | 0,8 | 0,33 | ✔ / ✘ |
| 3 | Anthropic → Cognition | `license` | 0,8 | 0,33 | ✔ / ✘ |
| 4 | Anthropic → Voiceflow | `license` | 0,8 | 0,33 | ✔ / ✘ |
| 5 | CommonwealthFusion → type-one-energy | `license` | 0,8 | 0,33 | ✔ / ✘ |
| 6 | GE_Aerospace → hanwha-aerospace | `license` | 0,8 | 0,33 | ✔ / ✘ |
| 7 | Mistral → helsing | `license` | 0,8 | 0,33 | ✔ / ✘ |
| 8 | OpenAI → AlphaSense | `license` | 0,8 | 0,33 | ✔ / ✘ |
| 9 | OpenAI → FactSet | `license` | 0,8 | 0,33 | ✔ / ✘ |
| 10 | OpenAI → Verint | `license` | 0,8 | 0,33 | ✔ / ✘ |
| 11 | OpenAI → Voiceflow | `license` | 0,8 | 0,33 | ✔ / ✘ |
| 12 | PowerchipSemi → TataSemiconductor | `license` | 0,8 | 0,33 | ✔ / ✘ |
| 13 | WiTricity → BMW | `license` | 0,8 | 0,33 | ✔ / ✘ |
| 14 | WiTricity → Hyundai | `license` | 0,8 | 0,33 | ✔ / ✘ |
| 15 | brewer-science → nissan-chemical | `license` | 0,8 | 0,33 | ✔ / ✘ |
| 16 | covariant → Amazon | `license` | 0,8 | 0,33 | ✔ / ✘ |
| 17 | rafael-advanced-defense → Raytheon | `license` | 0,8 | 0,33 | ✔ / ✘ |

### Los 41 proveedores ÚNICOS con peso menor a 1 (los que más cambian)

Son el único proveedor de su tipo para ese cliente; hoy transmiten como máximo un 15 % del golpe.

| # | Vínculo | Tipo | Peso hoy | Propuesta (0-1) | ¿De acuerdo? |
|---|---|---|---:|---:|---|
| 1 | AlibabaCloud → agibot-zhiyuan | `cloud` | 0,9 | 0,33 | ✔ / ✘ |
| 2 | Alphabet → CBOE | `cloud` | 0,9 | 0,33 | ✔ / ✘ |
| 3 | Alphabet → Thales | `cloud` | 0,9 | 0,33 | ✔ / ✘ |
| 4 | Amazon → NASDAQ | `cloud` | 0,9 | 0,33 | ✔ / ✘ |
| 5 | Amazon → QuEra | `cloud` | 0,9 | 0,33 | ✔ / ✘ |
| 6 | Amazon → locus-robotics | `cloud` | 0,9 | 0,33 | ✔ / ✘ |
| 7 | Amazon → zipline | `cloud` | 0,9 | 0,33 | ✔ / ✘ |
| 8 | Microsoft → Crane_NXT | `cloud` | 0,9 | 0,33 | ✔ / ✘ |
| 9 | Microsoft → MSCI | `cloud` | 0,9 | 0,33 | ✔ / ✘ |
| 10 | Microsoft → Raytheon | `cloud` | 0,9 | 0,33 | ✔ / ✘ |
| 11 | Microsoft → Saab_AB | `cloud` | 0,9 | 0,33 | ✔ / ✘ |
| 12 | Microsoft → general-dynamics | `cloud` | 0,9 | 0,33 | ✔ / ✘ |
| 13 | Microsoft → helsing | `cloud` | 0,9 | 0,33 | ✔ / ✘ |
| 14 | Microsoft → iqm-quantum | `cloud` | 0,9 | 0,33 | ✔ / ✘ |
| 15 | Microsoft → lockheed-martin | `cloud` | 0,9 | 0,33 | ✔ / ✘ |
| 16 | SpaceX → Satellogic | `deploy` | 0,4 | 0,5 | ✔ / ✘ |
| 17 | ARM → Innatera | `license` | 0,8 | 0,33 | ✔ / ✘ |
| 18 | ARM → SiMa | `license` | 0,8 | 0,33 | ✔ / ✘ |
| 19 | Anthropic → Cognition | `license` | 0,8 | 0,33 | ✔ / ✘ |
| 20 | CommonwealthFusion → type-one-energy | `license` | 0,8 | 0,33 | ✔ / ✘ |
| 21 | GE_Aerospace → hanwha-aerospace | `license` | 0,8 | 0,33 | ✔ / ✘ |
| 22 | Mistral → helsing | `license` | 0,8 | 0,33 | ✔ / ✘ |
| 23 | OpenAI → AlphaSense | `license` | 0,8 | 0,33 | ✔ / ✘ |
| 24 | OpenAI → FactSet | `license` | 0,8 | 0,33 | ✔ / ✘ |
| 25 | OpenAI → Verint | `license` | 0,8 | 0,33 | ✔ / ✘ |
| 26 | PowerchipSemi → TataSemiconductor | `license` | 0,8 | 0,33 | ✔ / ✘ |
| 27 | WiTricity → BMW | `license` | 0,8 | 0,33 | ✔ / ✘ |
| 28 | WiTricity → Hyundai | `license` | 0,8 | 0,33 | ✔ / ✘ |
| 29 | brewer-science → nissan-chemical | `license` | 0,8 | 0,33 | ✔ / ✘ |
| 30 | rafael-advanced-defense → Raytheon | `license` | 0,8 | 0,33 | ✔ / ✘ |
| 31 | Alphabet → wing-alphabet | `owns` | 0,6 | 0,83 | ✔ / ✘ |
| 32 | SoftBank → berkshire-grey | `owns` | 0,6 | 0,83 | ✔ / ✘ |
| 33 | Synopsys → AnsysEDA | `owns` | 0,6 | 0,83 | ✔ / ✘ |
| 34 | Thales → Imperva | `owns` | 0,6 | 0,83 | ✔ / ✘ |
| 35 | sierra-nevada-corporation → SierraSpace | `owns` | 0,6 | 0,83 | ✔ / ✘ |
| 36 | wingtech → nexperia | `owns` | 0,6 | 0,83 | ✔ / ✘ |
| 37 | Helion → Constellation | `ppa` | 0,7 | 0,5 | ✔ / ✘ |
| 38 | Nvidia → ntt-gdc | `supply` | 0,5 | 0,5 | ✔ / ✘ |
| 39 | Vertiv → edgeconnex | `supply` | 0,3 | 0,3 | ✔ / ✘ |
| 40 | Vertiv → stack-infra | `supply` | 0,3 | 0,3 | ✔ / ✘ |
| 41 | chang-chun-group → ASE | `supply` | 0,6 | 0,6 | ✔ / ✘ |

Los demás vínculos con peso menor a 1 (359) siguen la misma regla; están todos en `docs/revision_grafo.json` (`c_weights.items_w_le_1`). Si aceptas las reglas, se aplican igual.

## (d) Verbos en español que el motor no entiende

58 hechos con fecha usan verbos que no están en el vocabulario del motor, así que hoy no cuentan para nada. Casi todos unen una empresa con un CONCEPTO (una tecnología como EUV, un material, un país o una ley). Propuesta por verbo — **las 3 con "?" necesitan tu respuesta**:

| Verbo | Hechos | Propuesta | Qué significa | ¿De acuerdo? | Tu respuesta |
|---|---:|---|---|---|---|
| fabrica | 20 | `about` (entre dos empresas: `fab`) | Empresa que produce una tecnología/material (EUV, HBM3e…). Entre empresas sería "fab"; hacia un CONCEPTO queda como dato descriptivo que no mueve números. | ✔ / ✘ | |
| usa | 7 | `about` (entre dos empresas: `supply`) | Empresa que usa una tecnología. Entre dos empresas sería "supply" AL REVÉS (quien usa es el cliente). | ✔ / ✘ | |
| **controla** ? | 6 | `about` | ¿Qué significa "controla"? (a) es DUEÑA (Nvidia → CUDA): sería "owns"; (b) REGULA (BIS → Entity List) o (c) tiene la mayor parte del mercado (China → tierras raras): descriptivo. Propuesta: descriptivo (no mueve números) hasta que elijas. | ✔ / ✘ | |
| restringe | 6 | `affects` | Una política que restringe a alguien: "afecta a" (como los Factores; no es suministro). | ✔ / ✘ | |
| **alberga** ? | 5 | `about` | ¿"Alberga" = el país donde está la empresa? Propuesta: es UBICACIÓN (dato del país de la empresa), no un vínculo que transmita daño. El riesgo país ya lo llevan los Factores. | ✔ / ✘ | |
| compite | 3 | `about` | Competir no es suministrar: queda descriptivo (los rivales ya se calculan aparte). | ✔ / ✘ | |
| depende | 3 | `about` (entre dos empresas: `supply`) | Dependencia de una tecnología/material: igual que "usa". | ✔ / ✘ | |
| energiza | 3 | `ppa` | Da energía a: es exactamente "ppa". | ✔ / ✘ | |
| invierte | 3 | `invest` | Invierte en: "invest" (por defecto no transmite daño, BRECHAS #4). | ✔ / ✘ | |
| **domina** ? | 1 | `about` | ¿"Domina" = tiene la mayor cuota del mercado de esa tecnología (TSMC → 2 nm)? Propuesta: descriptivo (no mueve números). | ✔ / ✘ | |
| sanciona | 1 | `affects` | Sanción: "afecta a" (como los Factores). | ✔ / ✘ | |

<details><summary>Los hechos uno por uno</summary>

| # | Hecho | Desde | Propuesta |
|---|---|---|---|
| 1 | ASML «fabrica» ONT_EUV | 2010-01-01 | ASML → ONT_EUV `about` |
| 2 | ASML «fabrica» ONT_HighNA | 2024-01-01 | ASML → ONT_HighNA `about` |
| 3 | ASML «fabrica» ONT_DUV | 2001-01-01 | ASML → ONT_DUV `about` |
| 4 | TSMC «usa» ONT_EUV | 2019-01-01 | TSMC → ONT_EUV `about` |
| 5 | TSMC «usa» ONT_HighNA | 2024-01-01 | TSMC → ONT_HighNA `about` |
| 6 | Samsung «usa» ONT_EUV | 2020-01-01 | Samsung → ONT_EUV `about` |
| 7 | Intel «usa» ONT_HighNA | 2024-01-01 | Intel → ONT_HighNA `about` |
| 8 | TSMC «fabrica» ONT_CoWoS | 2016-01-01 | TSMC → ONT_CoWoS `about` |
| 9 | Nvidia «depende» ONT_CoWoS | 2020-01-01 | Nvidia → ONT_CoWoS `about` |
| 10 | Nvidia «usa» ONT_HBM3e | 2023-01-01 | Nvidia → ONT_HBM3e `about` |
| 11 | Nvidia «controla» ONT_CUDA | 2007-01-01 | Nvidia → ONT_CUDA `about` |
| 12 | SKHynix «fabrica» ONT_HBM3e | 2023-01-01 | SKHynix → ONT_HBM3e `about` |
| 13 | Micron «fabrica» ONT_HBM3e | 2024-02-26 | Micron → ONT_HBM3e `about` |
| 14 | Samsung «fabrica» ONT_HBM3e | 2024-07-01 | Samsung → ONT_HBM3e `about` |
| 15 | Nvidia «fabrica» ONT_Blackwell | 2024-03-01 | Nvidia → ONT_Blackwell `about` |
| 16 | TSMC «fabrica» ONT_Blackwell | 2024-06-01 | TSMC → ONT_Blackwell `about` |
| 17 | Broadcom «fabrica» ONT_TPU | 2016-01-01 | Broadcom → ONT_TPU `about` |
| 18 | Alphabet «usa» ONT_TPU | 2016-01-01 | Alphabet → ONT_TPU `about` |
| 19 | TSMC «domina» ONT_2nm | 2025-10-01 | TSMC → ONT_2nm `about` |
| 20 | Samsung «usa» ONT_2nm | 2022-06-01 | Samsung → ONT_2nm `about` |
| 21 | ShinEtsu «fabrica» ONT_Wafer | 2000-01-01 | ShinEtsu → ONT_Wafer `about` |
| 22 | JSR «fabrica» ONT_Photoresist | 2000-01-01 | JSR → ONT_Photoresist `about` |
| 23 | TokyoOhka «fabrica» ONT_Photoresist | 2000-01-01 | TokyoOhka → ONT_Photoresist `about` |
| 24 | TSMC «depende» ONT_Wafer | 2000-01-01 | TSMC → ONT_Wafer `about` |
| 25 | ONT_EUV «depende» ONT_Photoresist | 2019-01-01 | ONT_EUV → ONT_Photoresist `about` |
| 26 | Wolfspeed «fabrica» ONT_SiC | 2010-01-01 | Wolfspeed → ONT_SiC `about` |
| 27 | Navitas «fabrica» ONT_GaN | 2018-01-01 | Navitas → ONT_GaN `about` |
| 28 | ONT_BIS «controla» ONT_EntityList | 2019-01-01 | ONT_BIS → ONT_EntityList `about` |
| 29 | ONT_BIS «controla» ONT_AIControls | 2022-10-07 | ONT_BIS → ONT_AIControls `about` |
| 30 | ONT_EntityList «sanciona» Huawei | 2019-05-16 | ONT_EntityList → Huawei `affects` |
| 31 | ONT_AIControls «restringe» Nvidia | 2022-10-07 | ONT_AIControls → Nvidia `affects` |
| 32 | ONT_AIControls «restringe» ONT_China | 2022-10-07 | ONT_AIControls → ONT_China `affects` |
| 33 | ONT_DUVBan «restringe» ONT_China | 2024-01-01 | ONT_DUVBan → ONT_China `affects` |
| 34 | ONT_DUVBan «restringe» ASML | 2024-01-01 | ONT_DUVBan → ASML `affects` |
| 35 | ONT_NL «alberga» ASML | 1984-01-01 | ONT_NL → ASML `about` |
| 36 | ONT_China «controla» ONT_RareEarths | 2010-01-01 | ONT_China → ONT_RareEarths `about` |
| 37 | ONT_China «controla» ONT_Gallium | 2010-01-01 | ONT_China → ONT_Gallium `about` |
| 38 | ONT_China «controla» ONT_Germanium | 2010-01-01 | ONT_China → ONT_Germanium `about` |
| 39 | ONT_GaGeBan «restringe» ONT_Gallium | 2023-08-01 | ONT_GaGeBan → ONT_Gallium `affects` |
| 40 | ONT_GaGeBan «restringe» ONT_Germanium | 2023-08-01 | ONT_GaGeBan → ONT_Germanium `affects` |
| 41 | ONT_CHIPSAct «invierte» Intel | 2022-08-09 | ONT_CHIPSAct → Intel `invest` |
| 42 | ONT_CHIPSAct «invierte» TSMC | 2022-08-09 | ONT_CHIPSAct → TSMC `invest` |
| 43 | ONT_CHIPSAct «invierte» Micron | 2022-08-09 | ONT_CHIPSAct → Micron `invest` |
| 44 | ONT_Taiwan «alberga» TSMC | 1987-01-01 | ONT_Taiwan → TSMC `about` |
| 45 | ONT_Korea «alberga» SKHynix | 1983-01-01 | ONT_Korea → SKHynix `about` |
| 46 | ONT_Korea «alberga» Samsung | 1969-01-01 | ONT_Korea → Samsung `about` |
| 47 | ONT_Japan «alberga» ShinEtsu | 1926-01-01 | ONT_Japan → ShinEtsu `about` |
| 48 | Oklo «fabrica» ONT_SMR | 2024-01-01 | Oklo → ONT_SMR `about` |
| 49 | KairosPower «fabrica» ONT_SMR | 2024-01-01 | KairosPower → ONT_SMR `about` |
| 50 | NuScale «fabrica» ONT_SMR | 2023-01-01 | NuScale → ONT_SMR `about` |
| 51 | Helion «fabrica» ONT_Fusion | 2023-01-01 | Helion → ONT_Fusion `about` |
| 52 | CommonwealthFusion «fabrica» ONT_Fusion | 2021-01-01 | CommonwealthFusion → ONT_Fusion `about` |
| 53 | ONT_SMR «energiza» ONT_Grid | 2024-01-01 | ONT_SMR → ONT_Grid `ppa` |
| 54 | ONT_Grid «energiza» Microsoft | 2024-01-01 | ONT_Grid → Microsoft `ppa` |
| 55 | ONT_Grid «energiza» Amazon | 2024-01-01 | ONT_Grid → Amazon `ppa` |
| 56 | Nvidia «compite» AMD | 2023-01-01 | Nvidia → AMD `about` |
| 57 | TSMC «compite» Intel | 2021-01-01 | TSMC → Intel `about` |
| 58 | OpenAI «compite» Anthropic | 2023-01-01 | OpenAI → Anthropic `about` |

</details>

### Márgenes fuera de rango (12)

La regla de calidad pide un margen entre -1 y 1 (o sea, entre -100 % y +100 %).

| # | Empresa | Margen hoy | Propuesta | ¿De acuerdo? |
|---|---|---:|---|---|
| 1 | **Rigetti Computing** (`Rigetti`) | -2,5 | Margen de -250 %: posible en una empresa que pierde más de lo que vende. Propuesta: NO tocar el dato y ampliar la regla a [-10, 1] en la próxima versión de las formas (ontology.shapes). | ✔ / ✘ |
| 2 | **IonQ** (`IonQ`) | -1,5 | Margen de -150 %: posible en una empresa que pierde más de lo que vende. Propuesta: NO tocar el dato y ampliar la regla a [-10, 1] en la próxima versión de las formas (ontology.shapes). | ✔ / ✘ |
| 3 | **D-Wave Quantum** (`DWave`) | -1,5 | Margen de -150 %: posible en una empresa que pierde más de lo que vende. Propuesta: NO tocar el dato y ampliar la regla a [-10, 1] en la próxima versión de las formas (ontology.shapes). | ✔ / ✘ |
| 4 | **Quantinuum** (`Quantinuum`) | -2 | Margen de -200 %: posible en una empresa que pierde más de lo que vende. Propuesta: NO tocar el dato y ampliar la regla a [-10, 1] en la próxima versión de las formas (ontology.shapes). | ✔ / ✘ |
| 5 | **Pasqal** (`Pasqal`) | -2,5 | Margen de -250 %: posible en una empresa que pierde más de lo que vende. Propuesta: NO tocar el dato y ampliar la regla a [-10, 1] en la próxima versión de las formas (ontology.shapes). | ✔ / ✘ |
| 6 | **OpenAI** (`OpenAI`) | -1,2 | Margen de -120 %: posible en una empresa que pierde más de lo que vende. Propuesta: NO tocar el dato y ampliar la regla a [-10, 1] en la próxima versión de las formas (ontology.shapes). | ✔ / ✘ |
| 7 | **xAI (+SpaceX)** (`xAI`) | -1,5 | Margen de -150 %: posible en una empresa que pierde más de lo que vende. Propuesta: NO tocar el dato y ampliar la regla a [-10, 1] en la próxima versión de las formas (ontology.shapes). | ✔ / ✘ |
| 8 | **BenevolentAI** (`BenevolentAI`) | -1,2 | Margen de -120 %: posible en una empresa que pierde más de lo que vende. Propuesta: NO tocar el dato y ampliar la regla a [-10, 1] en la próxima versión de las formas (ontology.shapes). | ✔ / ✘ |
| 9 | **Rockley Photonics** (`RockleyPhotonics`) | -1,2 | Margen de -120 %: posible en una empresa que pierde más de lo que vende. Propuesta: NO tocar el dato y ampliar la regla a [-10, 1] en la próxima versión de las formas (ontology.shapes). | ✔ / ✘ |
| 10 | **POET Technologies** (`Coherus_Bio`) | -2 | Margen de -200 %: posible en una empresa que pierde más de lo que vende. Propuesta: NO tocar el dato y ampliar la regla a [-10, 1] en la próxima versión de las formas (ontology.shapes). | ✔ / ✘ |
| 11 | **Aurora Innovation** (`AuroraInnovation`) | -2 | Margen de -200 %: posible en una empresa que pierde más de lo que vende. Propuesta: NO tocar el dato y ampliar la regla a [-10, 1] en la próxima versión de las formas (ontology.shapes). | ✔ / ✘ |
| 12 | **Envicool** (`Envicool`) | 20,25 | Parece escrito en %: 20,25 → 0,2025. | ✔ / ✘ |

## (e) Los 200 vínculos más importantes sin fecha real

Si preguntas "¿cómo era la cadena en 2018?", Khipus hoy muestra la de hoy, porque casi ningún vínculo tiene fecha. Estos son los más importantes (peso en la escala 0-1 propuesta × importancia del tipo × confianza). **No inventamos fechas:** la columna "Fecha (con fuente)" se llena con un documento (tú, o el agente de investigación la propone con su fuente para tu visto bueno). Cuando el catálogo ya tiene un hecho con fecha para ESE vínculo, se muestra como pista (11 casos): ✔ = usar esa fecha (o la que escribas, con su fuente).

| # | Vínculo | Tipo | Peso | Pista del catálogo | Fecha (con fuente) | ¿Usar esta fecha? |
|---|---|---|---:|---|---|---|
| 1 | TSMC → Nvidia | `fab` | 6 | 2020-01-01 «fabrica GPUs para» (tf_tsmc_supplies_nvidia) | | ✔ / ✘ |
| 2 | TSMC → Apple | `fab` | 6 | — | | ✔ / ✘ |
| 3 | SKHynix → Nvidia | `supply` | 6 | 2023-01-01 «HBM3e para» (tf_skhynix_supplies_nvidia) | | ✔ / ✘ |
| 4 | ASML → TSMC | `supply` | 6 | 2024-01-01 «EUV High-NA para» (tf_asml_supplies_tsmc) | | ✔ / ✘ |
| 5 | Nvidia → Dell | `supply` | 6 | — | | ✔ / ✘ |
| 6 | SpaceX → Iridium | `supply` | 6 | — | | ✔ / ✘ |
| 7 | Zeiss → ASML | `supply` | 6 | — | | ✔ / ✘ |
| 8 | Ajinomoto → Ibiden | `supply` | 6 | — | | ✔ / ✘ |
| 9 | Nvidia → CoreWeave | `cloud` | 6 | — | | ✔ / ✘ |
| 10 | Amazon → Anthropic | `cloud` | 6 | — | | ✔ / ✘ |
| 11 | Microsoft → OpenAI | `cloud` | 6 | — | | ✔ / ✘ |
| 12 | Oracle → OpenAI | `cloud` | 6 | 2025-01-21 «proyecto Stargate $500B (infra IA) con» (tf_stargate) | | ✔ / ✘ |
| 13 | Nvidia → Meta | `supply` | 5 | — | | ✔ / ✘ |
| 14 | TSMC → AMD | `fab` | 5 | — | | ✔ / ✘ |
| 15 | TSMC → Broadcom | `fab` | 5 | — | | ✔ / ✘ |
| 16 | TSMC → MediaTek | `fab` | 5 | — | | ✔ / ✘ |
| 17 | WanHai → TSMC | `supply` | 5 | — | | ✔ / ✘ |
| 18 | YangMing → TSMC | `supply` | 5 | — | | ✔ / ✘ |
| 19 | EvergreenMarine → TSMC | `supply` | 5 | — | | ✔ / ✘ |
| 20 | Nvidia → xAI | `supply` | 5 | 2024-09-01 «Colossus: 100k+ GPUs de» (tf_xai_colossus) | | ✔ / ✘ |
| 21 | Prologis → Amazon | `supply` | 5 | — | | ✔ / ✘ |
| 22 | Segro → Amazon | `supply` | 5 | — | | ✔ / ✘ |
| 23 | Astera → Nvidia | `supply` | 5 | — | | ✔ / ✘ |
| 24 | Ibiden → Nvidia | `supply` | 5 | — | | ✔ / ✘ |
| 25 | Khazna → Nvidia | `supply` | 5 | — | | ✔ / ✘ |
| 26 | Boyd Thermal → Nvidia | `supply` | 5 | — | | ✔ / ✘ |
| 27 | Broadcom → Alphabet | `supply` | 5 | 2016-01-01 «co-diseña las TPU de» (tf_broadcom_google) | | ✔ / ✘ |
| 28 | HMM → Samsung | `supply` | 5 | — | | ✔ / ✘ |
| 29 | Nikon → Intel | `supply` | 5 | — | | ✔ / ✘ |
| 30 | DPR Construction → Meta | `supply` | 5 | — | | ✔ / ✘ |
| 31 | Turner Construction → Meta | `supply` | 5 | — | | ✔ / ✘ |
| 32 | Fortis Construction → Meta | `supply` | 5 | — | | ✔ / ✘ |
| 33 | Hensel Phelps → Meta | `supply` | 5 | — | | ✔ / ✘ |
| 34 | Mortenson → Meta | `supply` | 5 | — | | ✔ / ✘ |
| 35 | onsemi → Tesla | `supply` | 5 | — | | ✔ / ✘ |
| 36 | HMM → SKHynix | `supply` | 5 | — | | ✔ / ✘ |
| 37 | Turner Construction → CoreWeave | `supply` | 5 | — | | ✔ / ✘ |
| 38 | HiSilicon → Huawei | `supply` | 5 | — | | ✔ / ✘ |
| 39 | Envicool → AlibabaCloud | `supply` | 5 | — | | ✔ / ✘ |
| 40 | Ultra_Clean → AMAT | `supply` | 5 | — | | ✔ / ✘ |
| 41 | ChinaStateRailway → Foxconn | `supply` | 5 | — | | ✔ / ✘ |
| 42 | Maersk → PanamaCanalAuthority | `supply` | 5 | — | | ✔ / ✘ |
| 43 | Maersk → SuezCanalAuthority | `supply` | 5 | — | | ✔ / ✘ |
| 44 | CMA_CGM → PanamaCanalAuthority | `supply` | 5 | — | | ✔ / ✘ |
| 45 | CMA_CGM → SuezCanalAuthority | `supply` | 5 | — | | ✔ / ✘ |
| 46 | COSCOShipping → PanamaCanalAuthority | `supply` | 5 | — | | ✔ / ✘ |
| 47 | COSCOShipping → SuezCanalAuthority | `supply` | 5 | — | | ✔ / ✘ |
| 48 | DPR Construction → vantage-dc | `supply` | 5 | — | | ✔ / ✘ |
| 49 | HapagLloyd → PanamaCanalAuthority | `supply` | 5 | — | | ✔ / ✘ |
| 50 | HapagLloyd → SuezCanalAuthority | `supply` | 5 | — | | ✔ / ✘ |
| 51 | MSC → PanamaCanalAuthority | `supply` | 5 | — | | ✔ / ✘ |
| 52 | ZIM → SuezCanalAuthority | `supply` | 5 | — | | ✔ / ✘ |
| 53 | Ajinomoto → Unimicron | `supply` | 5 | — | | ✔ / ✘ |
| 54 | DPR Construction → crusoe-energy | `supply` | 5 | — | | ✔ / ✘ |
| 55 | Turner Construction → vantage-dc | `supply` | 5 | — | | ✔ / ✘ |
| 56 | Envicool → ByteDance | `supply` | 5 | — | | ✔ / ✘ |
| 57 | Envicool → Tencent | `supply` | 5 | — | | ✔ / ✘ |
| 58 | RussianRailways → Rosneft | `supply` | 5 | — | | ✔ / ✘ |
| 59 | Exelon → PJM | `supply` | 5 | — | | ✔ / ✘ |
| 60 | Fortis Construction → QTS | `supply` | 5 | — | | ✔ / ✘ |
| 61 | SouthernCopper → GrupoMexico | `supply` | 5 | — | | ✔ / ✘ |
| 62 | Nakilat → QatarEnergy | `supply` | 5 | — | | ✔ / ✘ |
| 63 | DBCargo → BASF | `supply` | 5 | — | | ✔ / ✘ |
| 64 | RussianRailways → Gazprom | `supply` | 5 | — | | ✔ / ✘ |
| 65 | Nvidia → Microsoft | `cloud` | 5 | — | | ✔ / ✘ |
| 66 | Nvidia → Oracle | `cloud` | 5 | — | | ✔ / ✘ |
| 67 | Amazon → Snowflake | `cloud` | 5 | — | | ✔ / ✘ |
| 68 | CoreSite → Amazon | `cloud` | 5 | — | | ✔ / ✘ |
| 69 | GlobalSwitch → Amazon | `cloud` | 5 | — | | ✔ / ✘ |
| 70 | NEXTDC → Amazon | `cloud` | 5 | — | | ✔ / ✘ |
| 71 | Telehouse → Amazon | `cloud` | 5 | — | | ✔ / ✘ |
| 72 | Arista → Microsoft | `cloud` | 5 | — | | ✔ / ✘ |
| 73 | Microsoft → Snowflake | `cloud` | 5 | — | | ✔ / ✘ |
| 74 | CoreSite → Microsoft | `cloud` | 5 | — | | ✔ / ✘ |
| 75 | GlobalSwitch → Microsoft | `cloud` | 5 | — | | ✔ / ✘ |
| 76 | AdaniConneX → Microsoft | `cloud` | 5 | — | | ✔ / ✘ |
| 77 | NEXTDC → Microsoft | `cloud` | 5 | — | | ✔ / ✘ |
| 78 | Khazna → Microsoft | `cloud` | 5 | — | | ✔ / ✘ |
| 79 | CDC_DataCentres → Microsoft | `cloud` | 5 | — | | ✔ / ✘ |
| 80 | PureDataCentres → Microsoft | `cloud` | 5 | — | | ✔ / ✘ |
| 81 | SubCom → Alphabet | `cloud` | 5 | — | | ✔ / ✘ |
| 82 | CoreSite → Alphabet | `cloud` | 5 | — | | ✔ / ✘ |
| 83 | GlobalSwitch → Alphabet | `cloud` | 5 | — | | ✔ / ✘ |
| 84 | AdaniConneX → Alphabet | `cloud` | 5 | — | | ✔ / ✘ |
| 85 | NEXTDC → Alphabet | `cloud` | 5 | — | | ✔ / ✘ |
| 86 | NxtraData → Alphabet | `cloud` | 5 | — | | ✔ / ✘ |
| 87 | CoreWeave → OpenAI | `cloud` | 5 | — | | ✔ / ✘ |
| 88 | JioDataCenters → Meta | `cloud` | 5 | — | | ✔ / ✘ |
| 89 | SuperMicro → CoreWeave | `cloud` | 5 | — | | ✔ / ✘ |
| 90 | MoroHub → Huawei | `cloud` | 5 | — | | ✔ / ✘ |
| 91 | DukeEnergy → Microsoft | `ppa` | 1 | — | | ✔ / ✘ |
| 92 | PPLCorp → Microsoft | `ppa` | 1 | — | | ✔ / ✘ |
| 93 | adeka-corporation → Samsung | `supply` | 0,7 | — | | ✔ / ✘ |
| 94 | PSEG → Alphabet | `ppa` | 1 | — | | ✔ / ✘ |
| 95 | SigmaLithium → Tesla | `supply` | 0,7 | — | | ✔ / ✘ |
| 96 | NRGEnergy → CoreWeave | `ppa` | 1 | — | | ✔ / ✘ |
| 97 | NioCorp → Northrop | `supply` | 0,7 | — | | ✔ / ✘ |
| 98 | UraniumEnergy → Oklo | `supply` | 0,7 | — | | ✔ / ✘ |
| 99 | TSMC → Meta | `fab` | 4 | — | | ✔ / ✘ |
| 100 | TSMC → Tesla | `fab` | 4 | — | | ✔ / ✘ |
| 101 | TSMC → Qualcomm | `fab` | 4 | — | | ✔ / ✘ |
| 102 | OpenAI → Nvidia | `supply` | 4 | — | | ✔ / ✘ |
| 103 | TSMC → Groq | `fab` | 4 | — | | ✔ / ✘ |
| 104 | TSMC → NXP | `fab` | 4 | — | | ✔ / ✘ |
| 105 | Expeditors → TSMC | `supply` | 4 | — | | ✔ / ✘ |
| 106 | Nvidia → HPE | `supply` | 4 | — | | ✔ / ✘ |
| 107 | Quanta → Nvidia | `supply` | 4 | — | | ✔ / ✘ |
| 108 | Expeditors → Nvidia | `supply` | 4 | — | | ✔ / ✘ |
| 109 | ASML → Samsung | `fab` | 4 | — | | ✔ / ✘ |
| 110 | YangMing → Samsung | `supply` | 4 | — | | ✔ / ✘ |
| 111 | XcelEnergy → Alphabet | `supply` | 4 | — | | ✔ / ✘ |
| 112 | Broadcom → Meta | `supply` | 4 | 2024-01-01 «ASIC de IA (MTIA) para» (tf_broadcom_meta) | | ✔ / ✘ |
| 113 | AMD → OpenAI | `supply` | 4 | 2025-01-01 «acuerdo 6GW Instinct con» (tf_amd_openai_6gw) | | ✔ / ✘ |
| 114 | Broadcom → OpenAI | `supply` | 4 | — | | ✔ / ✘ |
| 115 | SMIC → Huawei | `fab` | 4 | — | | ✔ / ✘ |
| 116 | Hexcel → SpaceX | `supply` | 4 | — | | ✔ / ✘ |
| 117 | LiontownResources → Tesla | `supply` | 4 | — | | ✔ / ✘ |
| 118 | MaxLinear → SpaceX | `supply` | 4 | — | | ✔ / ✘ |
| 119 | TalonMetals → Tesla | `supply` | 4 | — | | ✔ / ✘ |
| 120 | TorayIndustries → SpaceX | `supply` | 4 | — | | ✔ / ✘ |
| 121 | SKMaterials → SKHynix | `supply` | 4 | — | | ✔ / ✘ |
| 122 | SMIC → HiSilicon | `fab` | 4 | — | | ✔ / ✘ |
| 123 | Qorvo → Apple | `supply` | 4 | — | | ✔ / ✘ |
| 124 | CMA_CGM → Boeing | `supply` | 4 | — | | ✔ / ✘ |
| 125 | Skyworks → Apple | `supply` | 4 | — | | ✔ / ✘ |
| 126 | GF → PsiQuantum | `fab` | 4 | — | | ✔ / ✘ |
| 127 | Trumpf → ASML | `supply` | 4 | — | | ✔ / ✘ |
| 128 | WanHai → Foxconn | `supply` | 4 | — | | ✔ / ✘ |
| 129 | ChinaStateRailway → Huawei | `supply` | 4 | — | | ✔ / ✘ |
| 130 | DPR Construction → DigitalRealty | `supply` | 4 | — | | ✔ / ✘ |
| 131 | DSV → Maersk | `supply` | 4 | — | | ✔ / ✘ |
| 132 | Westinghouse → SouthernCo | `supply` | 4 | — | | ✔ / ✘ |
| 133 | DSV → MSC | `supply` | 4 | — | | ✔ / ✘ |
| 134 | Sibelco → GlobalWafers | `supply` | 4 | — | | ✔ / ✘ |
| 135 | CentrusEnergy → Xenergy | `supply` | 4 | — | | ✔ / ✘ |
| 136 | FirstEnergy → PJM | `supply` | 4 | — | | ✔ / ✘ |
| 137 | VulcanEnergy → Stellantis | `supply` | 4 | — | | ✔ / ✘ |
| 138 | CentrusEnergy → TerraPower | `supply` | 4 | — | | ✔ / ✘ |
| 139 | DBCargo → ArcelorMittal | `supply` | 4 | — | | ✔ / ✘ |
| 140 | Gazprom → PetroChina | `supply` | 4 | — | | ✔ / ✘ |
| 141 | PTValeIndonesia → Vale | `supply` | 4 | — | | ✔ / ✘ |
| 142 | Sempra → ERCOT | `supply` | 4 | — | | ✔ / ✘ |
| 143 | Nvidia → Amazon | `cloud` | 4 | — | | ✔ / ✘ |
| 144 | Nvidia → Nebius | `cloud` | 4 | — | | ✔ / ✘ |
| 145 | Constellation → Microsoft | `cloud` | 4 | — | | ✔ / ✘ |
| 146 | Broadcom → Alphabet | `cloud` | 4 | — | | ✔ / ✘ |
| 147 | Alphabet → Anthropic | `cloud` | 4 | — | | ✔ / ✘ |
| 148 | Dell → CoreWeave | `cloud` | 4 | — | | ✔ / ✘ |
| 149 | SpaceX → T_Mobile | `cloud` | 4 | — | | ✔ / ✘ |
| 150 | AirProducts → TSMC | `supply` | 0,6 | — | | ✔ / ✘ |
| 151 | fujimi-incorporated → TSMC | `supply` | 0,6 | — | | ✔ / ✘ |
| 152 | tosoh-corporation → TSMC | `supply` | 0,6 | — | | ✔ / ✘ |
| 153 | ntt-gdc → Microsoft | `supply` | 0,6 | — | | ✔ / ✘ |
| 154 | nissan-chemical → Samsung | `supply` | 0,6 | — | | ✔ / ✘ |
| 155 | fujimi-incorporated → Samsung | `supply` | 0,6 | — | | ✔ / ✘ |
| 156 | nitto-denko → Samsung | `supply` | 0,6 | — | | ✔ / ✘ |
| 157 | sumitomo-chemical → Samsung | `supply` | 0,6 | — | | ✔ / ✘ |
| 158 | tosoh-corporation → Samsung | `supply` | 0,6 | — | | ✔ / ✘ |
| 159 | adeka-corporation → SKHynix | `supply` | 0,6 | — | | ✔ / ✘ |
| 160 | princeton-digital-group → AlibabaCloud | `supply` | 0,6 | — | | ✔ / ✘ |
| 161 | chang-chun-group → ASE | `supply` | 0,6 | — | | ✔ / ✘ |
| 162 | Vistra → Amazon | `ppa` | 5 | — | | ✔ / ✘ |
| 163 | TalenEnergy → Amazon | `ppa` | 5 | — | | ✔ / ✘ |
| 164 | Brookfield → Microsoft | `ppa` | 5 | — | | ✔ / ✘ |
| 165 | AESCorp → Alphabet | `ppa` | 5 | — | | ✔ / ✘ |
| 166 | Vistra → Meta | `ppa` | 5 | — | | ✔ / ✘ |
| 167 | Entergy → Meta | `ppa` | 5 | — | | ✔ / ✘ |
| 168 | Vertiv → Nvidia | `supply` | 3 | 2024-01-01 «refrigeración líquida para racks de» (tf_vertiv_nvidia) | | ✔ / ✘ |
| 169 | Nvidia → Tesla | `supply` | 3 | — | | ✔ / ✘ |
| 170 | AMAT → TSMC | `supply` | 3 | — | | ✔ / ✘ |
| 171 | Dell → Nvidia | `supply` | 3 | — | | ✔ / ✘ |
| 172 | Lam → TSMC | `supply` | 3 | — | | ✔ / ✘ |
| 173 | Micron → Nvidia | `supply` | 3 | 2024-02-26 «HBM3e calificada para» (tf_micron_nvidia) | | ✔ / ✘ |
| 174 | TEL → TSMC | `supply` | 3 | — | | ✔ / ✘ |
| 175 | TSMC → Marvell | `fab` | 3 | — | | ✔ / ✘ |
| 176 | ShinEtsu → TSMC | `supply` | 3 | — | | ✔ / ✘ |
| 177 | TSMC → MPWR | `fab` | 3 | — | | ✔ / ✘ |
| 178 | TSMC → Renesas | `fab` | 3 | — | | ✔ / ✘ |
| 179 | TSMC → SambaNova | `fab` | 3 | — | | ✔ / ✘ |
| 180 | Besi → TSMC | `supply` | 3 | — | | ✔ / ✘ |
| 181 | CMC_Materials → TSMC | `supply` | 3 | — | | ✔ / ✘ |
| 182 | JSR → TSMC | `supply` | 3 | — | | ✔ / ✘ |
| 183 | KLA → TSMC | `supply` | 3 | — | | ✔ / ✘ |
| 184 | TSMC → Achronix | `fab` | 3 | — | | ✔ / ✘ |
| 185 | TSMC → Himax_Tech | `fab` | 3 | — | | ✔ / ✘ |
| 186 | TSMC → Qorvo | `fab` | 3 | — | | ✔ / ✘ |
| 187 | KuehneNagel → TSMC | `supply` | 3 | — | | ✔ / ✘ |
| 188 | NipponSanso → TSMC | `supply` | 3 | — | | ✔ / ✘ |
| 189 | Photronics → TSMC | `supply` | 3 | — | | ✔ / ✘ |
| 190 | TSMC → Etched | `fab` | 3 | — | | ✔ / ✘ |
| 191 | TSMC → Graphcore | `fab` | 3 | — | | ✔ / ✘ |
| 192 | TSMC → Microchip_Tech | `fab` | 3 | — | | ✔ / ✘ |
| 193 | TSMC → Skyworks | `fab` | 3 | — | | ✔ / ✘ |
| 194 | VulcanMaterials → TSMC | `supply` | 3 | — | | ✔ / ✘ |
| 195 | Foxconn → Nvidia | `supply` | 3 | 2024-06-01 «ensambla racks GB200 para» (tf_foxconn_assembles_nvidia) | | ✔ / ✘ |
| 196 | TSMC → HorizonRobotics | `fab` | 3 | — | | ✔ / ✘ |
| 197 | Quanta → Amazon | `supply` | 3 | — | | ✔ / ✘ |
| 198 | Nvidia → SuperMicro | `supply` | 3 | — | | ✔ / ✘ |
| 199 | SuperMicro → Nvidia | `supply` | 3 | — | | ✔ / ✘ |
| 200 | WesternDigital → Amazon | `supply` | 3 | — | | ✔ / ✘ |

## (f) Catálogo ↔ base de datos (decisión #7)

Hoy hay tres copias del mapa (el catálogo de archivos, su foto `data/grafo_v0.json` y la base de datos de producción). La recomendación es que **la base de datos de producción mande** y que el catálogo se reconcilie con ella una vez, con tu revisión. La reconciliación nunca borra: todo cambio es un evento nuevo que se puede deshacer por corrida.

**¿La base de datos de producción manda sobre el catálogo?** (recomendado) ✔ / ✘

| Qué compara | Qué hace | 
|---|---|
| `alias` | empresa duplicada que el catálogo ya fusionó → FusionarEntidad (se aplica por defecto) |
| `duplicates` | misma relación repetida con el mismo peso → se retira la copia (se aplica por defecto) |
| `direction` | X→Y en la base pero Y→X en el catálogo → SOLO con tu marca |
| `variants` | misma relación con otro peso → SOLO con tu marca |
| `missing` | está en el catálogo y falta en la base → SOLO con tu marca |
| `extra` | está en la base y no en el catálogo → SOLO con tu marca |

Lado catálogo: 937 empresas, 2.510 vínculos, 93 alias, 105 hechos con fecha.

**Dónde ver el plan EN VIVO** (las cifras de producción cambian, por eso no están aquí): 🩺 → Diagnóstico → tarjeta «Grafo: base vs catálogo» → «📄 Ver lista completa», o `GET /api/ontology/reconcile/plan`, o en la terminal `python scripts/build_graph_review.py --db` (solo lectura). Aplicar sigue pidiendo PIN y el nombre exacto de la base.

## Qué pasa después

- Con tus marcas, un paso siguiente aplica SOLO lo marcado ✔: en la base de producción como acciones de la ontología (RetractarVinculo + ProponerVinculo/CorregirDato, canal `review_grafo:<id>`, con PIN, cada una queda en el libro de decisiones) y en el catálogo de archivos (+ exportar la foto).
- Antes de aplicar se muestra cuánto cambia el contagio (por ejemplo TSMC u OpenAI) para que lo veas.
- Mientras no respondas: nada cambia. Esta lista se regenera sola si el catálogo cambia (`python scripts/build_graph_review.py`).
