# Revisión de instrumentos — ¿qué precio usamos para cada empresa?

> GENERADO por `python scripts/build_instrument_review.py` desde el catálogo (`data/grafo_v0.json`). No lo edites a mano salvo las columnas ✔/✘ y "Nota tuya" (si el catálogo cambia, se regenera y hay que copiar tus marcas).

## Qué es esto (en simple)

Una **empresa** no es lo mismo que su **acción**. Algunas empresas se compran en varias bolsas del mundo (por ejemplo Baidu en Nueva York y en Hong Kong), y otras hoy las medimos con un **certificado OTC** que se negocia poco en Estados Unidos (por ejemplo Samsung con `SSNLF`, cuando su acción de verdad es `005930` en Corea).

Khipus necesita UN precio de referencia por empresa para calcular riesgo, volatilidad y la historia de precios. **Hasta que tú elijas, sigue usando el de hoy** (nada cambia solo).

- **16 empresas con varios listados** (sección 1).
- **28 empresas que hoy se miden con un certificado OTC o ADR** (sección 2).

## Cómo responder

En cada fila deja **✔** en UNA de las dos columnas ("¿Mantener el de hoy?" o "¿Cambiar a la otra?") y borra la otra marca (o pon ✘). Si no sabes, déjala como está: se mantiene el de hoy. Luego mándame el archivo o dime "acepto las recomendaciones".

**Cómo pensarlo:**

- **Acción local** (la de su país): es el precio "de verdad", con más volumen; viene en moneda local (yenes, euros…) y Khipus la pasa a dólares con el tipo de cambio de cada día.
- **ADR / OTC en dólares**: cómodo porque ya está en dólares, pero un certificado OTC (los que terminan en **F**) se negocia muy poco: su precio puede quedarse quieto días enteros y eso hace que el riesgo parezca MENOR de lo que es.
- **Recomendación de Khipus**: cambiar a la acción local cuando hoy usamos un certificado OTC; mantener el de hoy cuando ya es un listado grande en Nueva York.

## 1. Empresas con varios listados (16)

| # | Empresa | Precio que usa HOY | Otra opción (acción local / otro listado) | Recomendación de Khipus | ¿Mantener el de hoy? | ¿Cambiar a la otra? | Nota tuya |
|---|---|---|---|---|---|---|---|
| 1 | **Baidu** (`Baidu`) | `BIDU` · acción · USD | `9888.HK` · Hong Kong (HKEX) · HKD | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |
| 2 | **Canadian National** (`CanadianNational`) | `CNI` · acción · USD | `CNR.TO` · Toronto (TSX) · CAD | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |
| 3 | **Cemex** (`Cemex`) | `CX` · ADR (certificado en dólares) · USD | `CEMEXCPO.MX` · México (BMV) · MXN | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |
| 4 | **CGN Power** (`CGNPower`) | `1816.HK` · acción · HKD | `003816.SZ` · Shenzhen (SZSE) · CNY | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |
| 5 | **CNOOC** (`CNOOC`) | `0883.HK` · acción · HKD | `600938.SS` · Shanghái (SSE) · CNY | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |
| 6 | **CPKC** (`CPKC`) | `CP` · acción · USD | `CP.TO` · Toronto (TSX) · CAD | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |
| 7 | **CRH** (`CRH`) | `CRH` · acción · USD | `CRH.L` · Londres (LSE) · GBP | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |
| 8 | **Denison Mines** (`DenisonMines`) | `DNN` · acción · USD | `DNN.TO` · Toronto (TSX) · CAD | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |
| 9 | **Hua Hong Semiconductor** (`HuaHong`) | `1347.HK` · acción · HKD | `688347.SS` · Shanghái (SSE) · CNY | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |
| 10 | **KEPCO** (`KEPCO`) | `KEP` · ADR (certificado en dólares) · USD | `015760.KS` · Corea (KRX) · KRW | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |
| 11 | **NexGen Energy** (`NexGenEnergy`) | `NXE` · acción · USD | `NXE.TO` · Toronto (TSX) · CAD | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |
| 12 | **POSCO** (`POSCO`) | `PKX` · ADR (certificado en dólares) · USD | `005490.KS` · Corea (KRX) · KRW | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |
| 13 | **Tencent** (`Tencent`) | `TCEHY` · certificado OTC (poco negociado) · USD | `0700.HK` · Hong Kong (HKEX) · HKD | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 14 | **Ur-Energy** (`UrEnergy`) | `URG` · acción · USD | `URG.TO` · Toronto (TSX) · CAD | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |
| 15 | **Xanadu** (`xanadu-quantum`) | `XNDU` · acción · USD | `XNDU.TO` · Toronto (TSX) · CAD | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |
| 16 | **Zijin Mining** (`ZijinMining`) | `2899.HK` · acción · HKD | `601899.SS` · Shanghái (SSE) · CNY | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |

## 2. Empresas medidas hoy con un certificado OTC o ADR (28)

| # | Empresa | Precio que usa HOY | Otra opción (acción local / otro listado) | Recomendación de Khipus | ¿Mantener el de hoy? | ¿Cambiar a la otra? | Nota tuya |
|---|---|---|---|---|---|---|---|
| 1 | **Advantest** (`Advantest`) | `ATEYY` · ADR (certificado en dólares) · USD | `6857.T` · Tokyo (TSE) · JPY | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 2 | **Air Liquide** (`AirLiquide`) | `AIQUY` · ADR (certificado en dólares) · USD | `AI.PA` · Euronext París · EUR | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 3 | **Airbus** (`Airbus`) | `EADSY` · ADR (certificado en dólares) · USD | `AIR.PA` · Euronext París · EUR | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 4 | **Ajinomoto** (`Ajinomoto`) | `AJINY` · ADR (certificado en dólares) · USD | `2802.T` · Tokyo (TSE) · JPY | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 5 | **ASM International** (`ASMInt`) | `ASMIY` · ADR (certificado en dólares) · USD | `ASM.AS` · Euronext Ámsterdam · EUR | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 6 | **BE Semiconductor** (`Besi`) | `BESIY` · ADR (certificado en dólares) · USD | `BESI.AS` · Euronext Ámsterdam · EUR | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 7 | **Canon** (`Canon`) | `CAJPY` · ADR (certificado en dólares) · USD | `7751.T` · Tokyo (TSE) · JPY | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 8 | **Disco** (`Disco`) | `DSCSY` · ADR (certificado en dólares) · USD | `6146.T` · Tokyo (TSE) · JPY | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 9 | **Hon Hai (Foxconn)** (`Foxconn`) | `HNHPF` · certificado OTC (poco negociado) · USD | `2317.TW` · Taiwán (TWSE) · TWD | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 10 | **Hoya** (`Hoya`) | `HOCPY` · ADR (certificado en dólares) · USD | `7741.T` · Tokyo (TSE) · JPY | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 11 | **Ibiden** (`Ibiden`) | `IBIDF` · certificado OTC (poco negociado) · USD | `4062.T` · Tokyo (TSE) · JPY | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 12 | **Infineon** (`Infineon`) | `IFNNY` · ADR (certificado en dólares) · USD | `IFX.DE` · Fráncfort (Xetra) · EUR | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 13 | **Lenovo** (`Lenovo`) | `LNVGY` · ADR (certificado en dólares) · USD | `0992.HK` · Hong Kong (HKEX) · HKD | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 14 | **Merck KGaA** (`MerckKGaA`) | `MKKGY` · ADR (certificado en dólares) · USD | `MRK.DE` · Fráncfort (Xetra) · EUR | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 15 | **Mitsui Chemicals** (`MitsuiChemicals`) | `MITUY` · ADR (certificado en dólares) · USD | `4183.T` · Tokyo (TSE) · JPY | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 16 | **NEC** (`NEC`) | `NIPNF` · certificado OTC (poco negociado) · USD | `6701.T` · Tokyo (TSE) · JPY | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 17 | **Nikon** (`Nikon`) | `NINOY` · ADR (certificado en dólares) · USD | `7731.T` · Tokyo (TSE) · JPY | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 18 | **Oxford Instruments** (`OxfordInstruments`) | `OXINF` · certificado OTC (poco negociado) · USD | `OXIG.L` · Londres (LSE) · GBP | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 19 | **Samsung Electronics** (`Samsung`) | `SSNLF` · certificado OTC (poco negociado) · USD | `005930.KS` · Corea (KRX) · KRW | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 20 | **Schneider Electric** (`Schneider`) | `SBGSY` · ADR (certificado en dólares) · USD | `SU.PA` · Euronext París · EUR | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 21 | **Screen Holdings** (`Screen`) | `DINRF` · certificado OTC (poco negociado) · USD | `7735.T` · Tokyo (TSE) · JPY | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 22 | **Shin-Etsu Chemical** (`ShinEtsu`) | `SHECY` · ADR (certificado en dólares) · USD | `4063.T` · Tokyo (TSE) · JPY | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 23 | **Siemens Energy** (`SiemensEnergy`) | `SMNEY` · ADR (certificado en dólares) · USD | `ENR.DE` · Fráncfort (Xetra) · EUR | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 24 | **Siltronic** (`Siltronic`) | `SSLLF` · certificado OTC (poco negociado) · USD | `WAF.DE` · Fráncfort (Xetra) · EUR | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 25 | **SUMCO** (`SUMCO`) | `SUOPY` · ADR (certificado en dólares) · USD | `3436.T` · Tokyo (TSE) · JPY | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 26 | **Tokyo Electron** (`TEL`) | `TOELY` · ADR (certificado en dólares) · USD | `8035.T` · Tokyo (TSE) · JPY | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 27 | **Toto** (`Toto`) | `TOTDY` · ADR (certificado en dólares) · USD | `5332.T` · Tokyo (TSE) · JPY | cambiar a la acción local | ✔ / ✘ | ✔ / ✘ | |
| 28 | **Vicarious Surgical** (`vicarious-surgical`) | `RBOT` · certificado OTC (poco negociado) · USD | — (no hay otro listado claro en el catálogo) | mantener el de hoy | ✔ / ✘ | ✔ / ✘ | |

## Qué pasa después

- Con tu elección, Khipus marca el instrumento elegido como **primario** (la tabla `instruments`; el otro queda guardado como secundario) y la historia de precios, el riesgo y los técnicos pasan a usarlo.
- Mientras no respondas: se usa el de hoy y esta lista sigue en GET `/api/instruments/review`.
