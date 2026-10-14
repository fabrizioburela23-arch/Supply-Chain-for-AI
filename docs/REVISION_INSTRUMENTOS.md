# Revisión de instrumentos — ¿qué precio usamos para cada empresa?

> GENERADO por `python scripts/build_instrument_review.py` desde el catálogo (`data/grafo_v0.json`). No lo edites a mano salvo las columnas ✔/✘ y "Nota tuya" (si el catálogo cambia, se regenera y hay que copiar tus marcas).

## Qué es esto (en simple)

Una **empresa** no es lo mismo que su **acción**. Algunas empresas se compran en varias bolsas del mundo (por ejemplo Baidu en Nueva York y en Hong Kong), y otras hoy las medimos con un **certificado OTC** que se negocia poco en Estados Unidos (por ejemplo Samsung con `SSNLF`, cuando su acción de verdad es `005930` en Corea).

Khipus necesita UN precio de referencia por empresa para calcular riesgo, volatilidad y la historia de precios. **Hasta que tú elijas, sigue usando el de hoy** (nada cambia solo).

- **21 empresas con varios listados** (sección 1).
- **25 empresas que hoy se miden con un certificado OTC o ADR** (sección 2).

## Cómo responder

En cada fila deja **✔** en UNA de las dos columnas ("¿Mantener el de hoy?" o "¿Cambiar a la otra?") y borra la otra marca (o pon ✘). Si no sabes, déjala como está: se mantiene el de hoy. Luego mándame el archivo o dime "acepto las recomendaciones".

**Cómo pensarlo:**

- **Acción local** (la de su país): es el precio "de verdad", con más volumen; viene en moneda local (yenes, euros…) y Khipus la pasa a dólares con el tipo de cambio de cada día.
- **ADR / OTC en dólares**: cómodo porque ya está en dólares, pero un certificado OTC (los que terminan en **F**) se negocia muy poco: su precio puede quedarse quieto días enteros y eso hace que el riesgo parezca MENOR de lo que es.
- **Recomendación de Khipus**: cambiar a la acción local cuando hoy usamos un certificado OTC; mantener el de hoy cuando ya es un listado grande en Nueva York.

## 1. Empresas con varios listados (21)

| # | Empresa | Precio que usa HOY | Otra opción (acción local / otro listado) | Recomendación de Khipus | ¿Mantener el de hoy? | ¿Cambiar a la otra? | Nota tuya |
|---|---|---|---|---|---|---|---|
| 1 | **Ajinomoto** (`Ajinomoto`) | `2802.T` · acción · JPY | `AJINY` · OTC (EE.UU.) · USD | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |
| 2 | **Astroscale** (`astroscale`) | `5034.T` · acción · JPY | `186A.T` · Tokyo (TSE) · JPY | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |
| 3 | **Baidu** (`Baidu`) | `BIDU` · acción · USD | `9888.HK` · Hong Kong (HKEX) · HKD | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |
| 4 | **Canadian National** (`CanadianNational`) | `CNI` · acción · USD | `CNR.TO` · Toronto (TSX) · CAD | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |
| 5 | **Cemex** (`Cemex`) | `CX` · ADR (certificado en dólares) · USD | `CEMEXCPO.MX` · México (BMV) · MXN | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |
| 6 | **CGN Power** (`CGNPower`) | `1816.HK` · acción · HKD | `003816.SZ` · Shenzhen (SZSE) · CNY | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |
| 7 | **CNOOC** (`CNOOC`) | `0883.HK` · acción · HKD | `600938.SS` · Shanghái (SSE) · CNY | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |
| 8 | **CPKC** (`CPKC`) | `CP` · acción · USD | `CP.TO` · Toronto (TSX) · CAD | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |
| 9 | **CRH** (`CRH`) | `CRH` · acción · USD | `CRH.L` · Londres (LSE) · GBP | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |
| 10 | **Denison Mines** (`DenisonMines`) | `DNN` · acción · USD | `DNN.TO` · Toronto (TSX) · CAD | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |
| 11 | **Hua Hong Semiconductor** (`HuaHong`) | `1347.HK` · acción · HKD | `688347.SS` · Shanghái (SSE) · CNY | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |
| 12 | **KEPCO** (`KEPCO`) | `KEP` · ADR (certificado en dólares) · USD | `015760.KS` · Corea (KRX) · KRW | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |
| 13 | **NexGen Energy** (`NexGenEnergy`) | `NXE` · acción · USD | `NXE.TO` · Toronto (TSX) · CAD | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |
| 14 | **POSCO** (`POSCO`) | `PKX` · ADR (certificado en dólares) · USD | `005490.KS` · Corea (KRX) · KRW | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |
| 15 | **Siemens Energy** (`SiemensEnergy`) | `ENR.DE` · acción · EUR | `SMNEY` · OTC (EE.UU.) · USD | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |
| 16 | **Tencent** (`Tencent`) | `TCEHY` · certificado OTC (poco negociado) · USD | `0700.HK` · Hong Kong (HKEX) · HKD | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 17 | **Tokyo Electron** (`TEL`) | `8035.T` · acción · JPY | `TOELY` · OTC (EE.UU.) · USD | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |
| 18 | **TSMC** (`TSMC`) | `TSM` · ADR (certificado en dólares) · USD | `2330.TW` · Taiwán (TWSE) · TWD | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |
| 19 | **Ur-Energy** (`UrEnergy`) | `URG` · acción · USD | `URG.TO` · Toronto (TSX) · CAD | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |
| 20 | **Xanadu** (`xanadu-quantum`) | `XNDU` · acción · USD | `XNDU.TO` · Toronto (TSX) · CAD | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |
| 21 | **Zijin Mining** (`ZijinMining`) | `2899.HK` · acción · HKD | `601899.SS` · Shanghái (SSE) · CNY | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |

## 2. Empresas medidas hoy con un certificado OTC o ADR (25)

| # | Empresa | Precio que usa HOY | Otra opción (acción local / otro listado) | Recomendación de Khipus | ¿Mantener el de hoy? | ¿Cambiar a la otra? | Nota tuya |
|---|---|---|---|---|---|---|---|
| 1 | **Advantest** (`Advantest`) | `ATEYY` · ADR (certificado en dólares) · USD | `6857.T` · Tokyo (TSE) · JPY | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 2 | **Air Liquide** (`AirLiquide`) | `AIQUY` · ADR (certificado en dólares) · USD | `AI.PA` · Euronext París · EUR | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 3 | **Airbus** (`Airbus`) | `EADSY` · ADR (certificado en dólares) · USD | `AIR.PA` · Euronext París · EUR | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 4 | **ASM International** (`ASMInt`) | `ASMIY` · ADR (certificado en dólares) · USD | `ASM.AS` · Euronext Ámsterdam · EUR | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 5 | **BE Semiconductor** (`Besi`) | `BESIY` · ADR (certificado en dólares) · USD | `BESI.AS` · Euronext Ámsterdam · EUR | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 6 | **Canon** (`Canon`) | `CAJPY` · ADR (certificado en dólares) · USD | `7751.T` · Tokyo (TSE) · JPY | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 7 | **Disco** (`Disco`) | `DSCSY` · ADR (certificado en dólares) · USD | `6146.T` · Tokyo (TSE) · JPY | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 8 | **Hon Hai (Foxconn)** (`Foxconn`) | `HNHPF` · certificado OTC (poco negociado) · USD | `2317.TW` · Taiwán (TWSE) · TWD | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 9 | **Hoya** (`Hoya`) | `HOCPY` · ADR (certificado en dólares) · USD | `7741.T` · Tokyo (TSE) · JPY | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 10 | **Ibiden** (`Ibiden`) | `IBIDF` · certificado OTC (poco negociado) · USD | `4062.T` · Tokyo (TSE) · JPY | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 11 | **Infineon** (`Infineon`) | `IFNNY` · ADR (certificado en dólares) · USD | `IFX.DE` · Fráncfort (Xetra) · EUR | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 12 | **Lenovo** (`Lenovo`) | `LNVGY` · ADR (certificado en dólares) · USD | `0992.HK` · Hong Kong (HKEX) · HKD | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 13 | **Merck KGaA** (`MerckKGaA`) | `MKKGY` · ADR (certificado en dólares) · USD | `MRK.DE` · Fráncfort (Xetra) · EUR | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 14 | **Mitsui Chemicals** (`MitsuiChemicals`) | `MITUY` · ADR (certificado en dólares) · USD | `4183.T` · Tokyo (TSE) · JPY | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 15 | **NEC** (`NEC`) | `NIPNF` · certificado OTC (poco negociado) · USD | `6701.T` · Tokyo (TSE) · JPY | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 16 | **Nikon** (`Nikon`) | `NINOY` · ADR (certificado en dólares) · USD | `7731.T` · Tokyo (TSE) · JPY | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 17 | **Oxford Instruments** (`OxfordInstruments`) | `OXINF` · certificado OTC (poco negociado) · USD | `OXIG.L` · Londres (LSE) · GBP | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 18 | **Samsung Electronics** (`Samsung`) | `SSNLF` · certificado OTC (poco negociado) · USD | `005930.KS` · Corea (KRX) · KRW | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 19 | **Schneider Electric** (`Schneider`) | `SBGSY` · ADR (certificado en dólares) · USD | `SU.PA` · Euronext París · EUR | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 20 | **Screen Holdings** (`Screen`) | `DINRF` · certificado OTC (poco negociado) · USD | `7735.T` · Tokyo (TSE) · JPY | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 21 | **Shin-Etsu Chemical** (`ShinEtsu`) | `SHECY` · ADR (certificado en dólares) · USD | `4063.T` · Tokyo (TSE) · JPY | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 22 | **Siltronic** (`Siltronic`) | `SSLLF` · certificado OTC (poco negociado) · USD | `WAF.DE` · Fráncfort (Xetra) · EUR | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 23 | **SUMCO** (`SUMCO`) | `SUOPY` · ADR (certificado en dólares) · USD | `3436.T` · Tokyo (TSE) · JPY | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 24 | **Toto** (`Toto`) | `TOTDY` · ADR (certificado en dólares) · USD | `5332.T` · Tokyo (TSE) · JPY | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 25 | **Vicarious Surgical** (`vicarious-surgical`) | `RBOT` · certificado OTC (poco negociado) · USD | — (no hay otro listado claro en el catálogo) | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |

## 3. Lote 2026-10-14: los 19 símbolos que no cuadraban con el agregador

La investigación externa (`data/import/lotes/2026-10-14/existentes_simbolos_revisar.csv`) comparó el catálogo con una base de cotizaciones. Regla aplicada: **la cotización principal es la de la bolsa de origen; los ADR/OTC son secundarios** (quedan registrados en `listings` de la ficha y en la tabla `instruments` como secundarios, nunca se borran).

- **8 corregidos** en `nodes/*.js` (con su fuente en `listings[].source_url`).
- **4 confirmados** (el catálogo ya estaba bien; el agregador no conocía el símbolo).
- **7 para que decidas tú** (la investigación contradice `nodes/listing_status.js`, que es GENERADO y no se toca a mano, o no se pudo verificar sin red).

| # | Empresa | Antes | Ahora | Qué pasó | Fuente | Nota |
|---|---|---|---|---|---|---|
| 1 | **SiTime** (`SiTime`) | `SITT / SITS` | SITM | corregido en el catálogo | https://investor.sitime.com/ | SITT no existía (y nodes_spacex.js decía SITS); el ticker de SiTime en Nasdaq es SITM. |
| 2 | **SK Hynix** (`SKHynix`) | `HXSCL` | 000660.KS | corregido en el catálogo | https://www.skhynix.com/ir/ | HXSCL era incorrecto; la cotización principal es 000660 en la Bolsa de Corea (KRX). |
| 3 | **QinetiQ** (`qinetiq`) | `QQ.` | QQ.L | corregido en el catálogo | https://www.qinetiq.com/en/investors | Símbolo mal escrito; en Yahoo la acción de Londres es QQ.L. |
| 4 | **Tokyo Electron** (`TEL`) | `TOELY` | 8035.T (+ TOELY secundario) | corregido en el catálogo | https://www.tel.com/ir/stock/ | La acción de Tokio pasa a primaria; el ADR TOELY queda como listado secundario (el agregador lo da de baja). |
| 5 | **Ajinomoto** (`Ajinomoto`) | `AJINY` | 2802.T (+ AJINY secundario) | corregido en el catálogo | https://www.ajinomoto.co.jp/company/en/ir/stock/ | La acción de Tokio pasa a primaria; el ADR AJINY queda como secundario (el agregador lo da de baja). |
| 6 | **Siemens Energy** (`SiemensEnergy`) | `SMNEY` | ENR.DE (+ SMNEY secundario) | corregido en el catálogo | https://www.siemens-energy.com/global/en/home/investor-relations/share.html | La acción de Xetra pasa a primaria; el ADR SMNEY queda como secundario (el agregador lo da de baja). |
| 7 | **Vulcan Energy** (`VulcanEnergy`) | `VUL.DE` | VUL.AX (+ Fráncfort sin símbolo) | corregido en el catálogo | https://v-er.eu/investors/ | VUL.DE no existe en el agregador; la principal es la ASX (VUL.AX). El listado de Fráncfort queda anotado sin símbolo de Yahoo verificado. |
| 8 | **TSMC** (`TSMC`) | `TSM` | TSM (ADR, sigue cotizando en la UI) + 2330.TW secundario | corregido en el catálogo | https://investor.tsmc.com/english/stock-information | Se registra la bolsa de origen 2330.TW como listado secundario (home); el ADR TSM (1 ADR = 5 acciones) sigue siendo el primario porque hoy es el que cotiza la app (nada cambia solo). |
| 9 | **Astroscale** (`astroscale`) | `5034.T` | 186A.T (en la fila cruda; listing_status.js sigue diciendo 5034.T) | decide Fabrizio | https://astroscale.com/ir/ | 5034.T es unerry, Inc. Astroscale Holdings cotiza en TSE Growth como 186A desde jun-2024. La fila del catálogo ya dice 186A.T, pero nodes/listing_status.js (GENERADO el 2026-09-29) la pisa con 5034.T: hay que corregir data/listing_verification/ (astroscale → 186A.T, fuente astroscale.com/ir) y regenerar con scripts/build_listing_status.py. |
| 10 | **Kazatomprom** (`Kazatomprom`) | `KAP.L` | KAP.L (sin cambio) | decide Fabrizio | https://www.kazatomprom.kz/en/investors | El GDR cotiza en Londres (IOB); el agregador no conoce KAP.L y en Yahoo el GDR suele ir como KAP.IL (USD). La acción local es KAP en AIX/KASE (KZT). listing_status.js impone KAP.L: decidir KAP.IL o KAP (AIX) y regenerar. |
| 11 | **Enflame Technology** (`enflame`) | `688801.SS` | 688801.SS (sin cambio) | confirmado (sin cambio) | https://www.cnbc.com/2026/09/11/chinese-nvidia-rival-enflame-stock-market-debut-ai.html | Salida a bolsa reciente (STAR, 11-sep-2026): el agregador aún no la tiene; la fuente primaria confirma el código. |
| 12 | **Moore Threads** (`moorethreads`) | `688795.SS` | 688795.SS (sin cambio) | confirmado (sin cambio) | https://english.sse.com.cn/ | Salida a bolsa reciente (STAR, 2026): el agregador aún no la tiene. |
| 13 | **Meeza** (`Meeza`) | `MEZA.QA` | MEZA.QA (sin cambio) | confirmado (sin cambio) | https://www.meeza.net/meeza-successfully-listed-on-qatar-stock-exchange-main-market/ | Cotiza en la Bolsa de Catar desde ago-2023 (fuente primaria); sufijo .QA correcto. |
| 14 | **Mindspace Business Parks REIT** (`Mindspace Business Parks REIT`) | `MINDSPACE.NS` | MINDSPACE.NS (sin cambio) | confirmado (sin cambio) | https://www.mindspacereit.com/investors | REIT listado en NSE/BSE; símbolo de Yahoo correcto. |
| 15 | **Uniper** (`Uniper`) | `UN01.DE` | UN01.DE (sin cambio) | decide Fabrizio | https://www.bloomberg.com/news/articles/2026-05-19/german-government-launches-privatization-of-energy-firm-uniper-mpc7nu4l | El agregador lo marca dado de baja; listing_status.js (fuente Bloomberg, may-2026) dice que cotiza en Xetra con ~99 % del Estado (flotante mínimo). Confirmar si sigue listado. |
| 16 | **Northern Data Group** (`northern-data`) | `NB2.DE` | NB2.DE (sin cambio) | decide Fabrizio | https://www.boerse-frankfurt.de/en | El agregador lo marca dado de baja (posible cierre de la compra por Rumble); listing_status.js lo da por cotizado con fuente genérica. Confirmar antes de cambiar. |
| 17 | **Qorvo** (`Qorvo`) | `QRVO` | QRVO (sin cambio) | decide Fabrizio | https://finance.yahoo.com/technology/articles/skyworks-solutions-sees-qorvo-deal-140319451.html | El agregador lo marca dado de baja (fusión con Skyworks); listing_status.js (sep-2026) decía pendiente de China y Corea. Si la fusión cerró, Qorvo pasa a "acquired" por Skyworks (SWKS). |
| 18 | **Asetek** (`Asetek`) | `ASTK.CO` | ASTK.CO (sin cambio) | decide Fabrizio | https://www.nasdaqomxnordic.com/ | El agregador lo marca dado de baja; listing_status.js lo da por cotizado en Nasdaq Copenhague con fuente genérica. Confirmar. |
| 19 | **Australian Strategic Materials** (`AustralianStrategicMaterials`) | `ASM.AX` | ASM.AX (sin cambio) | decide Fabrizio | https://asm-au.com/investors/ | El agregador lo marca dado de baja (compra por Energy Fuels anunciada en ene-2026, cierre pospuesto). Si cerró, pasa a "acquired" por Energy Fuels (UUUU). |

Ojo con la base: la siembra de `instruments` nunca pisa filas, así que los símbolos viejos (TOELY, AJINY, SMNEY, HXSCL, SITT, QQ., VUL.DE) siguen marcados como primarios hasta que se decida; `core.instruments.primary_conflicts()` los lista.

## Qué pasa después

- Con tu elección, Khipus marca el instrumento elegido como **primario** (la tabla `instruments`; el otro queda guardado como secundario) y la historia de precios, el riesgo y los técnicos pasan a usarlo.
- Mientras no respondas: se usa el de hoy y esta lista sigue en GET `/api/instruments/review`.
