# Revisión de países — ¿de dónde es cada empresa?

> GENERADO por `python scripts/build_country_review.py` desde el catálogo (`data/grafo_v0.json`) y la investigación del lote 2026-10-14 (`data/import/lotes/2026-10-14/existentes_paises.csv`, dato NO verificado por Khipus: se cita con su fuente). NADA se aplicó: el texto `country` de cada empresa sigue igual (las ciudades que trae dan la posición fina en el mapa). No lo edites a mano salvo las columnas ✔/✘ y "Nota tuya".

## Qué es esto (en simple)

El catálogo escribe el país de **136 formas distintas** ("EEUU", "Estados Unidos (HQ Denver, CO)", "Japón", "Taiwán", "Hong Kong (China)"…). Desde hoy Khipus las lee todas y deriva un **código de país ISO-2** (`US`, `JP`, `TW`…) sin cambiar el texto: la vista geopolítica del mapa, los filtros, la cartera y el contexto del chat agrupan por ese código (medido en la cartera: 126 empresas cambian de grupo, de 130 grupos a 47 —«Russia»→Rusia, EAU, HongKong, «Estados Unidos (…)»→EEUU—; las exclusiones por país aceptan cualquier grafía: «Israel», «India», «Singapur» ya no se buscan como empresa). De las 937 empresas, **866 resuelven a un país**, **71 dicen solo una región** (Europa 52, Resto del mundo 16, Resto de Europa 3) y 0 no se reconocen.

**Lo que NO cambia solo:** el NRS sigue usando su tabla de siempre (sección 6: es un parámetro gobernado, cambiarlo pide tu PIN) y el país guardado de cada empresa (secciones 1-4: tú decides).

## Cómo responder

En cada fila deja **✔** en "¿Aceptar?" si el país propuesto por la investigación es correcto (o escribe el correcto en "Nota tuya") y **✘** si no. Lo que no marques se queda como hoy. Luego mándame el archivo o dime "acepto todo lo que tenga fuente".

## 1. Empresas sin país real — solo región (71)

"Europa" o "Resto del mundo" no es un país: sin país real no hay riesgo-país fino ni exposición a eventos locales. La investigación propone una sede concreta; el mapa de hoy la ubica como dice la columna "Mapa hoy" (por `loc` o por la ciudad del texto).

| # | Empresa | Hoy (`country`) | `loc` | Mapa hoy | Investigación: sede | Método · fuente · cita | País propuesto (clave) | ¿Aceptar? | Nota tuya |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **ABB Robotics** (`ABB_Robotics`) | Europa | Europa | Europa · country | — | investigado_web · no es un país | `—` | ✔ / ✘ | |
| 2 | **Aleph Alpha** (`AlephAlpha`) | Europa | Europa | Europa · country | Alemania (`DE`) | investigado_web · <https://en.wikipedia.org/wiki/Aleph_Alpha> · no es un país | `Alemania` | ✔ / ✘ | |
| 3 | **ArcelorMittal** (`ArcelorMittal`) | Europa |  | Europa · country | Luxemburgo (`LU`) | agregador · <https://finance.yahoo.com/quote/MT/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Luxemburgo` | ✔ / ✘ | |
| 4 | **BAE Systems** (`BAESystems`) | Europa | Europa | Europa · country | Reino Unido (`GB`) | agregador · <https://finance.yahoo.com/quote/BA.L/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `ReinoUnido` | ✔ / ✘ | |
| 5 | **BenevolentAI** (`BenevolentAI`) | Europa | Europa | Europa · country | Reino Unido (`GB`) | investigado_web · <https://www.businesswire.com/news/home/20250205177929/en/Proposed-Delisting-via-Merger-of-BenevolentAI-into-Osaka-Holdings-S.-r.l.-and-Publication-of-Notice-of-Extraordinary-General-Meeting> · no es un país | `ReinoUnido` | ✔ / ✘ | |
| 6 | **Boliden** (`Boliden`) | Europa |  | Europa · country | Suecia (`SE`) | agregador · <https://finance.yahoo.com/quote/BOL.ST/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Suecia` | ✔ / ✘ | |
| 7 | **CRH** (`CRH`) | Europa |  | Europa · country | Irlanda (`IE`) | agregador · <https://finance.yahoo.com/quote/CRH/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Irlanda` | ✔ / ✘ | |
| 8 | **ECB** (`ECB`) | Eurozone (HQ Frankfurt, Germany) |  | Alemania · city | Alemania (`DE`) | investigado_web · <https://www.ecb.europa.eu/ecb/contacts/address/html/index.en.html> · texto no reconocido | `Alemania` | ✔ / ✘ | |
| 9 | **Elkem** (`Elkem`) | Europa |  | Europa · country | Noruega (`NO`) | agregador · <https://finance.yahoo.com/quote/ELK.OL/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Noruega` | ✔ / ✘ | |
| 10 | **Enel** (`Enel`) | Europa |  | Europa · country | Italia (`IT`) | agregador · <https://finance.yahoo.com/quote/ENEL.MI/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Italia` | ✔ / ✘ | |
| 11 | **Eni** (`Eni`) | Europa |  | Europa · country | Italia (`IT`) | agregador · <https://finance.yahoo.com/quote/ENI.MI/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Italia` | ✔ / ✘ | |
| 12 | **Equinor** (`Equinor`) | Europa |  | Europa · country | Noruega (`NO`) | agregador · <https://finance.yahoo.com/quote/EQNR/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Noruega` | ✔ / ✘ | |
| 13 | **Ericsson** (`Ericsson`) | Europa | Europa | Europa · hq | Suecia (`SE`) | agregador · <https://finance.yahoo.com/quote/ERIC/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Suecia` | ✔ / ✘ | |
| 14 | **Eurasian Resources Group** (`EurasianResourcesGroup`) | Europa |  | Europa · country | Luxemburgo (`LU`) | investigado_web · <https://en.wikipedia.org/wiki/Eurasian_Resources_Group> · no es un país | `Luxemburgo` | ✔ / ✘ | |
| 15 | **Eutelsat / OneWeb** (`Eutelsat`) | Europa | Europa | Europa · country | Francia (`FR`) | agregador · <https://finance.yahoo.com/quote/ETL.PA/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Francia` | ✔ / ✘ | |
| 16 | **Exscientia** (`Exscientia`) | Europa | Europa | Europa · country | Reino Unido (`GB`) | investigado_web · <https://www.sec.gov/Archives/edgar/data/1865408/000110465924107445/tm2424015d6_ex99-1.htm> · no es un país | `ReinoUnido` | ✔ / ✘ | |
| 17 | **Glencore** (`Glencore`) | Europa |  | Europa · country | Suiza (`CH`) | agregador · <https://finance.yahoo.com/quote/GLEN.L/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Suiza` | ✔ / ✘ | |
| 18 | **GrAI Matter Labs** (`GrAI_Matter`) | Europa | Europa | Europa · country | — | investigado_web · no es un país | `—` | ✔ / ✘ | |
| 19 | **Graphcore** (`Graphcore`) | Europa | Europa | Europa · country | Reino Unido (`GB`) | investigado_web · <https://www.graphcore.ai/contact> · no es un país | `ReinoUnido` | ✔ / ✘ | |
| 20 | **GreenWaves Technologies** (`GreenWaves`) | Europa | Europa | Europa · country | Francia (`FR`) | investigado_web · <https://minalogic.com/en/member-directory/greenwaves-technologies> · no es un país | `Francia` | ✔ / ✘ | |
| 21 | **Gunvor** (`Gunvor`) | Europa |  | Europa · country | Suiza (`CH`) | investigado_web · <https://en.wikipedia.org/wiki/Gunvor> · no es un país | `Suiza` | ✔ / ✘ | |
| 22 | **Holcim** (`Holcim`) | Europa |  | Europa · country | Suiza (`CH`) | agregador · <https://finance.yahoo.com/quote/HOLN.SW/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Suiza` | ✔ / ✘ | |
| 23 | **Iberdrola** (`Iberdrola`) | Europa |  | Europa · country | España (`ES`) | agregador · <https://finance.yahoo.com/quote/IBE.MC/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Espana` | ✔ / ✘ | |
| 24 | **Innatera Nanosystems** (`Innatera`) | Europa | Europa | Europa · country | Países Bajos (`NL`) | investigado_web · <https://innatera.com/contact> · no es un país | `PaisesBajos` | ✔ / ✘ | |
| 25 | **Lightsource bp** (`Lightsource_BP`) | Europa | Europa | Europa · country | Reino Unido (`GB`) | investigado_web · <https://en.wikipedia.org/wiki/Lightsource_BP> · no es un país | `ReinoUnido` | ✔ / ✘ | |
| 26 | **Mercuria** (`Mercuria`) | Europa |  | Europa · country | Suiza (`CH`) | investigado_web · <https://en.wikipedia.org/wiki/Mercuria_Energy_Group> · no es un país | `Suiza` | ✔ / ✘ | |
| 27 | **NBIM** (`NBIM`) | Europa |  | Europa · country | Noruega (`NO`) | investigado_web · <https://en.wikipedia.org/wiki/Norges_Bank_Investment_Management> · no es un país | `Noruega` | ✔ / ✘ | |
| 28 | **Nel ASA** (`NelASA`) | Europa |  | Europa · country | Noruega (`NO`) | agregador · <https://finance.yahoo.com/quote/NEL.OL/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Noruega` | ✔ / ✘ | |
| 29 | **Nokia** (`Nokia`) | Europa | Europa | Europa · hq | Finlandia (`FI`) | agregador · <https://finance.yahoo.com/quote/NOK/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Finlandia` | ✔ / ✘ | |
| 30 | **Norsk Hydro** (`NorskHydro`) | Europa |  | Europa · country | Noruega (`NO`) | agregador · <https://finance.yahoo.com/quote/NHY.OL/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Noruega` | ✔ / ✘ | |
| 31 | **NXP Semiconductors** (`NXP`) | Europa | Europa | Europa · country | Países Bajos (`NL`) | agregador · <https://finance.yahoo.com/quote/NXPI/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `PaisesBajos` | ✔ / ✘ | |
| 32 | **Orsted** (`Orsted`) | Europa |  | Europa · country | Dinamarca (`DK`) | agregador · <https://finance.yahoo.com/quote/ORSTED.CO/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Dinamarca` | ✔ / ✘ | |
| 33 | **Prophesee** (`Prophesee`) | Europa | Europa | Europa · country | Francia (`FR`) | investigado_web · <https://www.prophesee.ai/contact/> · no es un país | `Francia` | ✔ / ✘ | |
| 34 | **Prysmian** (`Prysmian`) | Europa |  | Europa · country | Italia (`IT`) | agregador · <https://finance.yahoo.com/quote/PRY.MI/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Italia` | ✔ / ✘ | |
| 35 | **Repsol** (`Repsol`) | Europa |  | Europa · country | España (`ES`) | agregador · <https://finance.yahoo.com/quote/REP.MC/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Espana` | ✔ / ✘ | |
| 36 | **Rheinmetall** (`Rheinmetall`) | Europa | Europa | Europa · country | Alemania (`DE`) | agregador · <https://finance.yahoo.com/quote/RHM.DE/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Alemania` | ✔ / ✘ | |
| 37 | **Saab AB** (`Saab_AB`) | Europa | Europa | Europa · country | Suecia (`SE`) | agregador · <https://finance.yahoo.com/quote/SAAB-B.ST/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Suecia` | ✔ / ✘ | |
| 38 | **SES S.A.** (`SES`) | Europa | Europa | Europa · country | Luxemburgo (`LU`) | agregador · <https://finance.yahoo.com/quote/SESG.PA/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Luxemburgo` | ✔ / ✘ | |
| 39 | **Sibelco** (`Sibelco`) | Europa |  | Europa · country | Bélgica (`BE`) | investigado_web · <https://www.sibelco.com/en/sites/sibelco-corporate-headquarters> · no es un país | `Belgica` | ✔ / ✘ | |
| 40 | **SMA Solar Technology** (`SMA_Solar`) | Europa |  | Europa · country | Alemania (`DE`) | agregador · <https://finance.yahoo.com/quote/S92.DE/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Alemania` | ✔ / ✘ | |
| 41 | **SNB** (`SNB`) | Europa |  | Europa · country | Suiza (`CH`) | investigado_web · <https://en.wikipedia.org/wiki/Swiss_National_Bank> · no es un país | `Suiza` | ✔ / ✘ | |
| 42 | **SpiNNcloud Systems** (`SpiNNcloud`) | Europa | Europa | Europa · country | Alemania (`DE`) | investigado_web · <https://spinncloud.com/imprint/> · no es un país | `Alemania` | ✔ / ✘ | |
| 43 | **SSAB** (`SSAB`) | Europa |  | Europa · country | Suecia (`SE`) | agregador · <https://finance.yahoo.com/quote/SSAB-B.ST/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Suecia` | ✔ / ✘ | |
| 44 | **STMicroelectronics** (`STMicroelectronics`) | Europa |  | Europa · country | Suiza (`CH`) | agregador · <https://finance.yahoo.com/quote/STM/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Suiza` | ✔ / ✘ | |
| 45 | **Terna** (`Terna`) | Europa |  | Europa · country | Italia (`IT`) | agregador · <https://finance.yahoo.com/quote/TRN.MI/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Italia` | ✔ / ✘ | |
| 46 | **Thales** (`Thales`) | Europa | Europa | Europa · country | Francia (`FR`) | agregador · <https://finance.yahoo.com/quote/HO.PA/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Francia` | ✔ / ✘ | |
| 47 | **The Quartz Corp** (`TheQuartzCorp`) | Europa |  | Europa · country | Noruega (`NO`) | investigado_web · <https://www.thequartzcorp.com/contact> · no es un país | `Noruega` | ✔ / ✘ | |
| 48 | **Umicore** (`Umicore`) | Europa | Europa | Europa · country | Bélgica (`BE`) | agregador · <https://finance.yahoo.com/quote/UMI.BR/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Belgica` | ✔ / ✘ | |
| 49 | **Vattenfall** (`Vattenfall`) | Europa |  | Europa · country | Suecia (`SE`) | investigado_web · <https://en.wikipedia.org/wiki/Vattenfall> · no es un país | `Suecia` | ✔ / ✘ | |
| 50 | **Vitol** (`Vitol`) | Europa |  | Europa · country | Suiza (`CH`) | investigado_web · <https://en.wikipedia.org/wiki/Vitol> · no es un país | `Suiza` | ✔ / ✘ | |
| 51 | **Wayve** (`Wayve`) | Europa | Europa | Europa · country | Reino Unido (`GB`) | investigado_web · <https://wayve.ai/contact/> · no es un país | `ReinoUnido` | ✔ / ✘ | |
| 52 | **X-FAB Silicon Foundries** (`X_Fab`) | Europa | Europa | Europa · country | Bélgica (`BE`) | agregador · <https://finance.yahoo.com/quote/XFAB.PA/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Belgica` | ✔ / ✘ | |
| 53 | **Bluefors** (`Bluefors`) | RestoEuropa | Finlandia | Finlandia · country | Finlandia (`FI`) | investigado_web · <https://bluefors.com/contact/> · no es un país | `Finlandia` | ✔ / ✘ | |
| 54 | **ICEYE** (`ICEYE`) | RestoEuropa | Finlandia | Finlandia · country | Finlandia (`FI`) | investigado_web · <https://www.iceye.com/contact> · no es un país | `Finlandia` | ✔ / ✘ | |
| 55 | **1X Technologies** (`OneX`) | RestoEuropa | Noruega | Noruega · country | Estados Unidos (`US`) | investigado_web · <https://www.1x.tech/about> · no es un país | `EEUU` | ✔ / ✘ | |
| 56 | **Celestica** (`Celestica`) | RestoMundo | Canadá | Canada · country | Canadá (`CA`) | agregador · <https://finance.yahoo.com/quote/CLS/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Canada` | ✔ / ✘ | |
| 57 | **Cemex** (`Cemex`) | RestoMundo |  | RestoMundo · hq | México (`MX`) | agregador · <https://finance.yahoo.com/quote/CX/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Mexico` | ✔ / ✘ | |
| 58 | **D-Wave Quantum** (`DWave`) | RestoMundo | Canadá | Canada · country | Estados Unidos (`US`) | agregador · <https://finance.yahoo.com/quote/QBTS/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `EEUU` | ✔ / ✘ | |
| 59 | **GIC_Singapore** (`GIC_Singapore`) | RestoMundo |  | RestoMundo · hq | Singapur (`SG`) | investigado_web · <https://www.gic.com.sg/contact-us/> · no es un país | `Singapur` | ✔ / ✘ | |
| 60 | **Grupo México** (`GrupoMexico`) | RestoMundo |  | RestoMundo · hq | México (`MX`) | agregador · <https://finance.yahoo.com/quote/GMEXICOB.MX/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Mexico` | ✔ / ✘ | |
| 61 | **Petrobras** (`Petrobras`) | RestoMundo |  | RestoMundo · hq | Brasil (`BR`) | agregador · <https://finance.yahoo.com/quote/PBR/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Brasil` | ✔ / ✘ | |
| 62 | **PIF (Saudi Arabia)** (`PIF_SaudiArabia`) | RestoMundo |  | RestoMundo · hq | Arabia Saudita (`SA`) | investigado_web · <https://en.wikipedia.org/wiki/Public_Investment_Fund> · no es un país | `ArabiaSaudita` | ✔ / ✘ | |
| 63 | **Qatar_Airways_Cargo** (`Qatar_Airways_Cargo`) | RestoMundo |  | RestoMundo · hq | Catar (`QA`) | investigado_web · <https://en.wikipedia.org/wiki/Qatar_Airways_Cargo> · no es un país | `Catar` | ✔ / ✘ | |
| 64 | **QatarEnergy** (`QatarEnergy`) | RestoMundo |  | RestoMundo · hq | Catar (`QA`) | investigado_web · <https://en.wikipedia.org/wiki/QatarEnergy> · no es un país | `Catar` | ✔ / ✘ | |
| 65 | **QIA** (`QIA`) | RestoMundo |  | RestoMundo · hq | Catar (`QA`) | investigado_web · <https://en.wikipedia.org/wiki/Qatar_Investment_Authority> · no es un país | `Catar` | ✔ / ✘ | |
| 66 | **Quantum Machines** (`QuantumMachines`) | RestoMundo | Israel | Israel · hq | Israel (`IL`) | investigado_web · <https://www.datacenterdynamics.com/en/news/quantum-machines-raises-170m-in-oversubscribed-funding-round> · no es un país | `Israel` | ✔ / ✘ | |
| 67 | **Saudi Aramco** (`SaudiAramco`) | RestoMundo |  | RestoMundo · hq | Arabia Saudita (`SA`) | agregador · <https://finance.yahoo.com/quote/2222.SR/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `ArabiaSaudita` | ✔ / ✘ | |
| 68 | **SQM** (`SQM`) | RestoMundo | Chile | Chile · country | Chile (`CL`) | agregador · <https://finance.yahoo.com/quote/SQM/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Chile` | ✔ / ✘ | |
| 69 | **Temasek** (`Temasek`) | RestoMundo |  | RestoMundo · hq | Singapur (`SG`) | investigado_web · <https://www.temasek.com.sg/en/contact-us> · no es un país | `Singapur` | ✔ / ✘ | |
| 70 | **Trafigura** (`Trafigura`) | RestoMundo |  | RestoMundo · hq | Singapur (`SG`) | investigado_web · <https://en.wikipedia.org/wiki/Trafigura> · no es un país | `Singapur` | ✔ / ✘ | |
| 71 | **Vale** (`Vale`) | RestoMundo |  | RestoMundo · hq | Brasil (`BR`) | agregador · <https://finance.yahoo.com/quote/VALE/profile> · no es un país; sede tomada de FinanceDatabase (agregador) | `Brasil` | ✔ / ✘ | |

## 2. Textos con varios países (26)

Khipus toma el PRIMER país del texto (antes de "/", "(" o ","). Si la sede real es otra, márcalo.

| # | Empresa | Texto de hoy | Khipus toma | Investigación: sede | Método · fuente · cita | ¿De acuerdo? | ¿Aceptar la investigación? | Nota tuya |
|---|---|---|---|---|---|---|---|---|
| 1 | **Antonov_Airlines** (`Antonov_Airlines`) | Ucrania (operativamente reubicada a Leipzig/Halle, Alemania, desde 2022) | Ucrania (`UA`) | Ucrania (`UA`) | mapeo | sí | ✔ / ✘ | |
| 2 | **Asetek** (`Asetek`) | Dinamarca (HQ, como Asetek A/S) | Dinamarca (`DK`) | Dinamarca (`DK`) | mapeo | sí | ✔ / ✘ | |
| 3 | **Boyd Thermal** (`Boyd Thermal`) | Estados Unidos (manufactura global: México/Norteamérica, Asia, Europa) | Estados Unidos (`US`) | Estados Unidos (`US`) | mapeo | sí | ✔ / ✘ | |
| 4 | **China Merchants Port** (`ChinaMerchantsPort`) | China (Hong Kong/Shenzhen) | China (`CN`) | Hong Kong (`HK`) | investigado_web · <https://en.wikipedia.org/wiki/China_Merchants_Port> · texto menciona otra sede o constitución; la base (FinanceDatabase) dice HK | NO | ✔ / ✘ | |
| 5 | **Chindata Group** (`chindata`) | China / Singapur (holding, operaciones pan-asiáticas) | China (`CN`) | China (`CN`) | investigado_web · <https://w.media/bain-capital-takes-chindata-private-with-full-ownership/> · sede múltiple o ambigua | sí | ✔ / ✘ | |
| 6 | **Cirion** (`Cirion`) | Panamá/multi-país LatAm — operaciones en Argentina, Brasil, Chile, Colombia, México y Perú | Panamá (`PA`) | Argentina (`AR`) | investigado_web · <https://builtin.com/company/cirion> · sede múltiple o ambigua | NO | ✔ / ✘ | |
| 7 | **ESR Group** (`ESR_Group`) | Hong Kong / Singapur (sede dual) | Hong Kong (`HK`) | Singapur (`SG`) | investigado_web · <https://www.esr.com/connect-with-us/> · sede múltiple o ambigua | NO | ✔ / ✘ | |
| 8 | **Fitch Ratings** (`FitchRatings`) | United States / United Kingdom (doble sede Nueva York–Londres) | Estados Unidos (`US`) | — | investigado_web · sede múltiple o ambigua | — | ✔ / ✘ | |
| 9 | **FluidStack** (`fluidstack`) | Reino Unido / Estados Unidos | Reino Unido (`GB`) | Estados Unidos (`US`) | investigado_web · <https://fluidstack.io/blog/fluidstack-selected-by-anthropic-to-deliver-custom-data-centers-in-the-us> · sede múltiple o ambigua | NO | ✔ / ✘ | |
| 10 | **GLP** (`GLP`) | Singapur (origen) / EE.UU. (Ares) / China (GLP China) | Singapur (`SG`) | Singapur (`SG`) | mapeo | sí | ✔ / ✘ | |
| 11 | **IHSMarkit** (`IHSMarkit`) | United States / United Kingdom | Estados Unidos (`US`) | Reino Unido (`GB`) | investigado_web · <https://en.wikipedia.org/wiki/IHS_Markit> · sede múltiple o ambigua | NO | ✔ / ✘ | |
| 12 | **Johnson Controls** (`Johnson Controls`) | Irlanda (Cork) / operaciones principales en EE.UU. (Milwaukee, WI) | Irlanda (`IE`) | Irlanda (`IE`) | mapeo | sí | ✔ / ✘ | |
| 13 | **Morningstar DBRS** (`MorningstarDBRS`) | Canada / United States (fundada en Toronto, hoy con oficinas en Nueva York, Chicago, Londres, Fráncfort, Madrid) | Canadá (`CA`) | Canadá (`CA`) | investigado_web · <https://www.insurancebusinessmag.com/us/companies/morningstar-dbrs/587365/> · sede múltiple o ambigua | sí | ✔ / ✘ | |
| 14 | **Munters Group** (`Munters Group`) | Suecia (Kista/Estocolmo) | Suecia (`SE`) | Suecia (`SE`) | mapeo | sí | ✔ / ✘ | |
| 15 | **Nscale** (`nscale`) | Reino Unido / Noruega | Reino Unido (`GB`) | Reino Unido (`GB`) | investigado_web · <https://en.wikipedia.org/wiki/Nscale> · sede múltiple o ambigua | sí | ✔ / ✘ | |
| 16 | **nVent Electric** (`nVent Electric`) | Reino Unido (sede corporativa en Londres) / operaciones principales en EE.UU. (Minneapolis, Minnesota) | Reino Unido (`GB`) | Reino Unido (`GB`) | mapeo | sí | ✔ / ✘ | |
| 17 | **ONE_Line** (`ONE_Line`) | Singapur (sede operativa) / Japón (sede legal) | Singapur (`SG`) | Singapur (`SG`) | investigado_web · <https://en.wikipedia.org/wiki/Ocean_Network_Express> · texto menciona otra sede o constitución | sí | ✔ / ✘ | |
| 18 | **Poolside AI** (`poolside-ai`) | Estados Unidos / Francia | Estados Unidos (`US`) | Estados Unidos (`US`) | investigado_web · <https://en.wikipedia.org/wiki/Poolside_AI> · sede múltiple o ambigua | sí | ✔ / ✘ | |
| 19 | **Rio Tinto** (`RioTinto`) | United Kingdom / Australia | Reino Unido (`GB`) | Reino Unido (`GB`) | agregador · <https://finance.yahoo.com/quote/RIO/profile> · sede múltiple o ambigua; sede tomada de FinanceDatabase (agregador) | sí | ✔ / ✘ | |
| 20 | **Rio Tinto Aluminium** (`RioTintoAluminium`) | United Kingdom/Australia | Reino Unido (`GB`) | Canadá (`CA`) | investigado_web · <https://en.wikipedia.org/wiki/Rio_Tinto_Alcan> · sede múltiple o ambigua | NO | ✔ / ✘ | |
| 21 | **STACK Infrastructure** (`stack-infra`) | Estados Unidos (HQ Denver/Kansas City) — propiedad de Blue Owl Capital | Estados Unidos (`US`) | Estados Unidos (`US`) | mapeo | sí | ✔ / ✘ | |
| 22 | **STOXX** (`STOXX`) | Germany / Switzerland | Alemania (`DE`) | Suiza (`CH`) | investigado_web · <https://en.wikipedia.org/wiki/STOXX> · sede múltiple o ambigua | NO | ✔ / ✘ | |
| 23 | **Trane Technologies** (`Trane Technologies`) | Irlanda (Swords) / operaciones principales en EE.UU. (Davidson, NC) | Irlanda (`IE`) | Irlanda (`IE`) | mapeo | sí | ✔ / ✘ | |
| 24 | **Volga_Dnepr** (`Volga_Dnepr`) | Rusia (Ulyanovsk / Moscú) | Rusia (`RU`) | Rusia (`RU`) | mapeo | sí | ✔ / ✘ | |
| 25 | **Vulcan Energy** (`VulcanEnergy`) | Australia / Germany | Australia (`AU`) | Alemania (`DE`) | investigado_web · <https://battery-tech.net/company/vulcan-energy-resources-deutschland/> · sede múltiple o ambigua | NO | ✔ / ✘ | |
| 26 | **WPT Industrial** (`WPT Industrial`) | Canadá (sede original Toronto) / activos en EE.UU. | Canadá (`CA`) | Canadá (`CA`) | mapeo | sí | ✔ / ✘ | |

## 3. El mapa las pone en otro país que su clave (12)

La ciudad del texto o el `loc` mandan sobre el país (regla de `geo_coord`): no es un error, pero conviene saberlo. Sin cambios salvo que marques la sede.

| # | Empresa | `country` | `loc` | Clave (país) | Mapa hoy | Investigación: sede | ¿Aceptar? | Nota tuya |
|---|---|---|---|---|---|---|---|---|
| 1 | **Antonov_Airlines** (`Antonov_Airlines`) | Ucrania (operativamente reubicada a Leipzig/Halle, Alemania, desde 2022) |  | `Ucrania` | Alemania · city | Ucrania (`UA`) | ✔ / ✘ | |
| 2 | **Bluefors** (`Bluefors`) | RestoEuropa | Finlandia | `RestoEuropa` | Finlandia · country | Finlandia (`FI`) | ✔ / ✘ | |
| 3 | **Brookfield** (`Brookfield`) | Canada (sede corporativa trasladada a Nueva York en dic-2024) |  | `Canada` | EEUU · city | Estados Unidos (`US`) | ✔ / ✘ | |
| 4 | **Celestica** (`Celestica`) | RestoMundo | Canadá | `RestoMundo` | Canada · country | Canadá (`CA`) | ✔ / ✘ | |
| 5 | **China Merchants Port** (`ChinaMerchantsPort`) | China (Hong Kong/Shenzhen) |  | `China` | HongKong · city | Hong Kong (`HK`) | ✔ / ✘ | |
| 6 | **Chindata Group** (`chindata`) | China / Singapur (holding, operaciones pan-asiáticas) |  | `China` | Singapur · city | China (`CN`) | ✔ / ✘ | |
| 7 | **D-Wave Quantum** (`DWave`) | RestoMundo | Canadá | `RestoMundo` | Canada · country | Estados Unidos (`US`) | ✔ / ✘ | |
| 8 | **ECB** (`ECB`) | Eurozone (HQ Frankfurt, Germany) |  | `Europa` | Alemania · city | Alemania (`DE`) | ✔ / ✘ | |
| 9 | **ICEYE** (`ICEYE`) | RestoEuropa | Finlandia | `RestoEuropa` | Finlandia · country | Finlandia (`FI`) | ✔ / ✘ | |
| 10 | **1X Technologies** (`OneX`) | RestoEuropa | Noruega | `RestoEuropa` | Noruega · country | Estados Unidos (`US`) | ✔ / ✘ | |
| 11 | **Quantum Machines** (`QuantumMachines`) | RestoMundo | Israel | `RestoMundo` | Israel · hq | Israel (`IL`) | ✔ / ✘ | |
| 12 | **SQM** (`SQM`) | RestoMundo | Chile | `RestoMundo` | Chile · country | Chile (`CL`) | ✔ / ✘ | |

## 4. Desacuerdos entre Khipus y la investigación (20)

Empresas con país real en el catálogo donde la investigación dice OTRA sede. Manda la fuente primaria; si la fila no trae fuente, desconfía.

| # | Empresa | Texto de hoy | Khipus deriva | Investigación: sede | Método · fuente · cita | ¿Aceptar la investigación? | Nota tuya |
|---|---|---|---|---|---|---|---|
| 1 | **Brookfield** (`Brookfield`) | Canada (sede corporativa trasladada a Nueva York en dic-2024) | Canadá (`CA`) | Estados Unidos (`US`) | investigado_web · <https://en.wikipedia.org/wiki/Brookfield_Asset_Management> · texto menciona otra sede o constitución; la base (FinanceDatabase) dice US | ✔ / ✘ | |
| 2 | **CEVA** (`Ceva`) | Israel | Israel (`IL`) | Estados Unidos (`US`) | investigado_web · <https://en.wikipedia.org/wiki/CEVA,_Inc.> · la base (FinanceDatabase) dice US | ✔ / ✘ | |
| 3 | **China Merchants Port** (`ChinaMerchantsPort`) | China (Hong Kong/Shenzhen) | China (`CN`) | Hong Kong (`HK`) | investigado_web · <https://en.wikipedia.org/wiki/China_Merchants_Port> · texto menciona otra sede o constitución; la base (FinanceDatabase) dice HK | ✔ / ✘ | |
| 4 | **Cirion** (`Cirion`) | Panamá/multi-país LatAm — operaciones en Argentina, Brasil, Chile, Colombia, México y Perú | Panamá (`PA`) | Argentina (`AR`) | investigado_web · <https://builtin.com/company/cirion> · sede múltiple o ambigua | ✔ / ✘ | |
| 5 | **CLP Group** (`CLPGroup`) | China | China (`CN`) | Hong Kong (`HK`) | investigado_web · <https://en.wikipedia.org/wiki/CLP_Group> · la base (FinanceDatabase) dice HK | ✔ / ✘ | |
| 6 | **POET Technologies** (`Coherus_Bio`) | EEUU | Estados Unidos (`US`) | Canadá (`CA`) | investigado_web · <https://poet-technologies.com/contact-us> · la base (FinanceDatabase) dice CA | ✔ / ✘ | |
| 7 | **COSCO Shipping Ports** (`COSCOShippingPorts`) | China (matriz COSCO Shipping Group en Shanghái) | China (`CN`) | Hong Kong (`HK`) | investigado_web · <https://en.wikipedia.org/wiki/COSCO_Shipping_Ports> · la base (FinanceDatabase) dice HK | ✔ / ✘ | |
| 8 | **DayOne** (`DayOne`) | Hong Kong (sede) — operaciones en Hong Kong, Singapur, Malasia (Johor), Indonesia (Batam) y Japón (Tokio) | Hong Kong (`HK`) | Singapur (`SG`) | investigado_web · <https://www.caproasia.com/?p=69391> · texto no reconocido | ✔ / ✘ | |
| 9 | **ESR Group** (`ESR_Group`) | Hong Kong / Singapur (sede dual) | Hong Kong (`HK`) | Singapur (`SG`) | investigado_web · <https://www.esr.com/connect-with-us/> · sede múltiple o ambigua | ✔ / ✘ | |
| 10 | **Fabrinet** (`fabrinet`) | Tailandia (incorporada en Islas Caimán) | Tailandia (`TH`) | Islas Caimán (`KY`) | agregador · <https://finance.yahoo.com/quote/FN/profile> · texto no reconocido; sede tomada de FinanceDatabase (agregador) | ✔ / ✘ | |
| 11 | **FluidStack** (`fluidstack`) | Reino Unido / Estados Unidos | Reino Unido (`GB`) | Estados Unidos (`US`) | investigado_web · <https://fluidstack.io/blog/fluidstack-selected-by-anthropic-to-deliver-custom-data-centers-in-the-us> · sede múltiple o ambigua | ✔ / ✘ | |
| 12 | **IHSMarkit** (`IHSMarkit`) | United States / United Kingdom | Estados Unidos (`US`) | Reino Unido (`GB`) | investigado_web · <https://en.wikipedia.org/wiki/IHS_Markit> · sede múltiple o ambigua | ✔ / ✘ | |
| 13 | **Insilico Medicine** (`Insilico`) | China | China (`CN`) | Estados Unidos (`US`) | investigado_web · <https://en.wikipedia.org/wiki/Insilico_Medicine> · la base (FinanceDatabase) dice HK | ✔ / ✘ | |
| 14 | **Lightelligence** (`Lightelligence`) | EEUU | Estados Unidos (`US`) | China (`CN`) | investigado_web · <https://english.shanghai.gov.cn/en-Latest-WhatsNew/20260710/d4e7f937a9df450abbb17638d873c88d.html> · la base (FinanceDatabase) dice CN | ✔ / ✘ | |
| 15 | **Linde** (`Linde`) | EEUU | Estados Unidos (`US`) | Reino Unido (`GB`) | investigado_web · <https://en.wikipedia.org/wiki/Linde_plc> · la base (FinanceDatabase) dice GB | ✔ / ✘ | |
| 16 | **Rio Tinto Aluminium** (`RioTintoAluminium`) | United Kingdom/Australia | Reino Unido (`GB`) | Canadá (`CA`) | investigado_web · <https://en.wikipedia.org/wiki/Rio_Tinto_Alcan> · sede múltiple o ambigua | ✔ / ✘ | |
| 17 | **Sigma Lithium** (`SigmaLithium`) | EEUU | Estados Unidos (`US`) | Brasil (`BR`) | investigado_web · <https://www.sec.gov/Archives/edgar/data/1848309/000117184325001837/ex_796004.htm> · la base (FinanceDatabase) dice CA | ✔ / ✘ | |
| 18 | **STOXX** (`STOXX`) | Germany / Switzerland | Alemania (`DE`) | Suiza (`CH`) | investigado_web · <https://en.wikipedia.org/wiki/STOXX> · sede múltiple o ambigua | ✔ / ✘ | |
| 19 | **Talon Metals** (`TalonMetals`) | Canadá | Canadá (`CA`) | Estados Unidos (`US`) | investigado_web · <https://talonmetals.com/contact/> · la base (FinanceDatabase) dice VG | ✔ / ✘ | |
| 20 | **Vulcan Energy** (`VulcanEnergy`) | Australia / Germany | Australia (`AU`) | Alemania (`DE`) | investigado_web · <https://battery-tech.net/company/vulcan-energy-resources-deutschland/> · sede múltiple o ambigua | ✔ / ✘ | |

Sin sede en la investigación: `GrAI_Matter` (Europa), `FitchRatings` (United States / United Kingdom (doble sede Nueva York–Londres)), `ABB_Robotics` (Europa).

## 5. País de registro distinto de la sede (12) — información

Entra como hecho con fuente (`incorporation_country`) cuando corra el importador; no mueve el mapa ni el NRS.

| # | Empresa | Sede | Registro | Método · fuente · cita |
|---|---|---|---|---|
| 1 | **Airbus** (`Airbus`) | Francia (`FR`) | Países Bajos (`NL`) | investigado_web · <https://en.wikipedia.org/wiki/Airbus> · la base (FinanceDatabase) dice NL |
| 2 | **CNOOC** (`CNOOC`) | China (`CN`) | Hong Kong (`HK`) | investigado_web · <https://en.wikipedia.org/wiki/CNOOC_Limited> · la base (FinanceDatabase) dice HK |
| 3 | **COSCO Shipping Ports** (`COSCOShippingPorts`) | Hong Kong (`HK`) | Bermudas (`BM`) | investigado_web · <https://en.wikipedia.org/wiki/COSCO_Shipping_Ports> · la base (FinanceDatabase) dice HK |
| 4 | **Eaton** (`Eaton`) | Estados Unidos (`US`) | Irlanda (`IE`) | investigado_web · <https://en.wikipedia.org/wiki/Eaton_Corporation> · la base (FinanceDatabase) dice IE |
| 5 | **Gunvor** (`Gunvor`) | Suiza (`CH`) | Chipre (`CY`) | investigado_web · <https://en.wikipedia.org/wiki/Gunvor> · no es un país |
| 6 | **Lenovo** (`Lenovo`) | China (`CN`) | Hong Kong (`HK`) | investigado_web · <https://en.wikipedia.org/wiki/Lenovo> · la base (FinanceDatabase) dice HK |
| 7 | **Linde** (`Linde`) | Reino Unido (`GB`) | Irlanda (`IE`) | investigado_web · <https://en.wikipedia.org/wiki/Linde_plc> · la base (FinanceDatabase) dice GB |
| 8 | **Mercuria** (`Mercuria`) | Suiza (`CH`) | Islas Caimán (`KY`) | investigado_web · <https://en.wikipedia.org/wiki/Mercuria_Energy_Group> · no es un país |
| 9 | **Seagate Technology** (`Seagate`) | Estados Unidos (`US`) | Irlanda (`IE`) | investigado_web · <https://en.wikipedia.org/wiki/Seagate_Technology> · la base (FinanceDatabase) dice IE |
| 10 | **Sigma Lithium** (`SigmaLithium`) | Brasil (`BR`) | Canadá (`CA`) | investigado_web · <https://www.sec.gov/Archives/edgar/data/1848309/000117184325001837/ex_796004.htm> · la base (FinanceDatabase) dice CA |
| 11 | **Silicon Motion** (`SiliconMotion`) | Taiwán (`TW`) | Islas Caimán (`KY`) | investigado_web · <https://en.wikipedia.org/wiki/Silicon_Motion> · la base (FinanceDatabase) dice HK |
| 12 | **Talon Metals** (`TalonMetals`) | Estados Unidos (`US`) | Islas Vírgenes Británicas (`VG`) | investigado_web · <https://talonmetals.com/contact/> · la base (FinanceDatabase) dice VG |

## 6. El NRS no cambió — qué cambiaría si leyera el país canónico

El término "país" del NRS usa su propia tabla gobernada (`nrs.formula` 1.0.0: China 28, Taiwán 25, Corea 15, Japón 12, EE.UU. 8, Europa 10, Israel 18, resto 15) leída con alias de ORTOGRAFÍA (`core/world._NRS_GEO_ALIAS`), no con el ISO-2 nuevo. Hoy NO se toca: es una decisión tuya (`nrs.formula` 1.1.0 con PIN: 🩺 → Gobernanza → ¿Qué cambia? → Activar). Medido sobre el catálogo, tres variantes:

- **(a) ISO-2 del texto `country`** → cambian **2** empresas (tabla de abajo).
- **(b) el país del MAPA** (la ciudad o el `loc` mandan: ECB → Alemania, chindata → Singapur…) → cambian **5**: `AlignedDataCenters` 15→8, `Brookfield` 15→8, `ChinaMerchantsPort` 28→15, `chindata` 28→15, `QuantumMachines` 15→18.
- **(c) (a) + "Europa = todo país europeo"** (hoy "Alemania", "Francia", "Finlandia"… caen al 15 por defecto, no al 10 de Europa) → cambian **105** empresas (las 103 europeas con país escrito bajarían 5 puntos).

| # | Empresa | Texto de hoy | NRS hoy lee | Puntos hoy | (a) leería | Puntos (a) |
|---|---|---|---|---|---|---|
| 1 | **Aligned Data Centers** (`AlignedDataCenters`) | Estados Unidos — huella pan-americana (incl. Brasil, Chile, Colombia, México vía ODATA) | (defecto) | 15 | EEUU | 8 |
| 2 | **ECB** (`ECB`) | Eurozone (HQ Frankfurt, Germany) | (defecto) | 15 | Europa | 10 |

## 7. Las grafías del catálogo (para el trinquete)

Toda grafía nueva debe resolver a un ISO-2 o ser una región (tests/test_countries.py). Hoy:

| Grafía | Empresas | ISO-2 / región |
|---|---|---|
| EEUU | 361 | US |
| China | 67 | CN |
| Estados Unidos | 62 | US |
| Europa | 51 | Europa |
| Japon | 44 | JP |
| Alemania | 25 | DE |
| Australia | 24 | AU |
| Taiwan | 21 | TW |
| Canadá | 20 | CA |
| Francia | 17 | FR |
| RestoMundo | 16 | RestoMundo |
| Japón | 15 | JP |
| India | 14 | IN |
| ReinoUnido | 13 | GB |
| Israel | 10 | IL |
| Corea | 9 | KR |
| Reino Unido | 9 | GB |
| Russia | 7 | RU |
| PaisesBajos | 5 | NL |
| United Arab Emirates | 5 | AE |
| Emiratos Árabes Unidos | 4 | AE |
| Singapur | 4 | SG |
| Taiwán | 4 | TW |
| Estados Unidos (Dallas, Texas) | 3 | US |
| Estados Unidos (HQ Denver, CO) | 3 | US |
| RestoEuropa | 3 | RestoEuropa |
| Brasil | 2 | BR |
| Catar | 2 | QA |
| Corea del Sur | 2 | KR |
| Dinamarca | 2 | DK |
| Estados Unidos (Atlanta, Georgia) | 2 | US |
| Estados Unidos (HQ San Francisco, CA) | 2 | US |
| Estados Unidos (Nueva York, NY) | 2 | US |
| Estados Unidos (Omaha, Nebraska) | 2 | US |
| Hong Kong (China) | 2 | HK |
| Países Bajos | 2 | NL |
| Suiza | 2 | CH |
| Alemania (Frankfurt am Main) | 1 | DE |
| Alemania (Hamburgo) | 1 | DE |
| Algeria | 1 | DZ |
| Australia (sede Canberra) — operaciones en Canberra, Sídney, Melbourne (Australia) y Auckland (Nueva Zelanda) | 1 | AU |
| Australia (sede Sídney) — operaciones en Australia, Japón, Hong Kong, Singapur y Malasia (Johor) | 1 | AU |
| Australia / Germany | 1 | AU |
| Azerbaiyán (Bakú) | 1 | AZ |
| Brasil — operaciones en Brasil, Chile, Colombia y México | 1 | BR |
| Brasil — operaciones en Brasil, México y Chile | 1 | BR |
| Bélgica | 1 | BE |
| Canada | 1 | CA |
| Canada (sede corporativa trasladada a Nueva York en dic-2024) | 1 | CA |
| Canada / United States (fundada en Toronto, hoy con oficinas en Nueva York, Chicago, Londres, Fráncfort, Madrid) | 1 | CA |
| Canadá (Calgary, Alberta) | 1 | CA |
| Canadá (Calgary, Alberta); manufactura también en China y Vietnam | 1 | CA |
| Canadá (Montreal, Quebec) | 1 | CA |
| Canadá (sede original Toronto) / activos en EE.UU. | 1 | CA |
| Canadá (Toronto, Ontario) | 1 | CA |
| Chile | 1 | CL |
| China (Hong Kong/Shenzhen) | 1 | CN |
| China (matriz COSCO Shipping Group en Shanghái) | 1 | CN |
| China (Shenzhen) | 1 | CN |
| China / Singapur (holding, operaciones pan-asiáticas) | 1 | CN |
| Dinamarca (HQ, como Asetek A/S) | 1 | DK |
| Egipto | 1 | EG |
| Emiratos Árabes Unidos (Abu Dhabi) | 1 | AE |
| Emiratos Árabes Unidos (sede Dubái) — expansión a 13 países incl. EE.UU., España, Italia, Grecia, Turquía, Arabia Saudita | 1 | AE |
| España | 1 | ES |
| Estados Unidos (Chicago, IL; herencia UK vía DTZ) | 1 | US |
| Estados Unidos (Chicago, IL; origen histórico Jones Lang Wootton, Londres, S.XVIII) | 1 | US |
| Estados Unidos (Dallas, TX; sede financiera global en Nueva York desde ene-2025) | 1 | US |
| Estados Unidos (Fort Worth, Texas) | 1 | US |
| Estados Unidos (Greeley, Colorado) | 1 | US |
| Estados Unidos (HQ Boulder, CO) | 1 | US |
| Estados Unidos (HQ Denver/Kansas City) — propiedad de Blue Owl Capital | 1 | US |
| Estados Unidos (HQ Herndon, VA) | 1 | US |
| Estados Unidos (HQ Las Vegas, NV) | 1 | US |
| Estados Unidos (HQ y manufactura en Carrollton, Texas, desde 2024) — origen corporativo en Hong Kong (Allied Control Limited, 2012) | 1 | US |
| Estados Unidos (Jacksonville, Florida) | 1 | US |
| Estados Unidos (manufactura global: México/Norteamérica, Asia, Europa) | 1 | US |
| Estados Unidos (Minneapolis, Minnesota) | 1 | US |
| Estados Unidos (Palm Beach Gardens, Florida) | 1 | US |
| Estados Unidos (Portland, Oregon) | 1 | US |
| Estados Unidos (Redwood City, California) | 1 | US |
| Estados Unidos (Reston, Virginia) | 1 | US |
| Estados Unidos (San Francisco, CA) | 1 | US |
| Estados Unidos (sede Dallas, TX) — operaciones también en Canadá e Israel | 1 | US |
| Estados Unidos (Ypsilanti, Michigan; base en Willow Run Airport) | 1 | US |
| Estados Unidos / Francia | 1 | US |
| Estados Unidos — huella pan-americana (incl. Brasil, Chile, Colombia, México vía ODATA) | 1 | US |
| Eurozone (HQ Frankfurt, Germany) | 1 | Europa |
| Finlandia | 1 | FI |
| Germany / Switzerland | 1 | DE |
| Hong Kong (sede) — operaciones en Hong Kong, Singapur, Malasia (Johor), Indonesia (Batam) y Japón (Tokio) | 1 | HK |
| Hong Kong / Singapur (sede dual) | 1 | HK |
| Indonesia | 1 | ID |
| Irlanda (Cork) / operaciones principales en EE.UU. (Milwaukee, WI) | 1 | IE |
| Irlanda (Swords) / operaciones principales en EE.UU. (Davidson, NC) | 1 | IE |
| Italia | 1 | IT |
| Italia (Reggio Emilia) | 1 | IT |
| Japón (sede operativa global, matriz KDDI) | 1 | JP |
| Kazajistán | 1 | KZ |
| Kuwait | 1 | KW |
| Lituania | 1 | LT |
| Luxemburgo | 1 | LU |
| Malaysia | 1 | MY |
| México — operaciones en México, Centroamérica, Caribe, Colombia y España | 1 | MX |
| Panamá | 1 | PA |
| Panamá/multi-país LatAm — operaciones en Argentina, Brasil, Chile, Colombia, México y Perú | 1 | PA |
| Países Bajos (sede en La Haya) | 1 | NL |
| Poland | 1 | PL |
| Reino Unido (Kent) | 1 | GB |
| Reino Unido (Kingston upon Thames) | 1 | GB |
| Reino Unido (sede corporativa en Londres) / operaciones principales en EE.UU. (Minneapolis, Minnesota) | 1 | GB |
| Reino Unido (sede Londres) — operaciones en EE.UU., Canadá y Europa (Londres, Fráncfort, Ámsterdam) | 1 | GB |
| Reino Unido (sede Londres) — operaciones en Europa y Asia-Pacífico | 1 | GB |
| Reino Unido (sede Londres) — operaciones en Europa, Medio Oriente y Asia | 1 | GB |
| Reino Unido / Estados Unidos | 1 | GB |
| Reino Unido / Noruega | 1 | GB |
| Rusia | 1 | RU |
| Rusia (Ulyanovsk / Moscú) | 1 | RU |
| Singapur (operaciones pan-asiáticas) | 1 | SG |
| Singapur (origen) / EE.UU. (Ares) / China (GLP China) | 1 | SG |
| Singapur (sede operativa) / Japón (sede legal) | 1 | SG |
| Singapur (sede) — operaciones en Japón, Corea, India, Malasia, Indonesia, Filipinas | 1 | SG |
| South Africa | 1 | ZA |
| Sudáfrica | 1 | ZA |
| Sudáfrica (sede operativa) — operaciones en Sudáfrica, Nigeria y Kenia | 1 | ZA |
| Suecia (Kista/Estocolmo) | 1 | SE |
| Switzerland (Basel) | 1 | CH |
| Tailandia (incorporada en Islas Caimán) | 1 | TH |
| Ucrania (operativamente reubicada a Leipzig/Halle, Alemania, desde 2022) | 1 | UA |
| Uganda (sede) — operaciones en Angola, Costa de Marfil, RD Congo, Etiopía, Mozambique, Tanzania y Uganda (7 países) | 1 | UG |
| United Kingdom / Australia | 1 | GB |
| United Kingdom/Australia | 1 | GB |
| United States (mayoritariamente propiedad de Mubadala Capital, Emiratos Árabes Unidos, desde may-2024) | 1 | US |
| United States (membresía global, 75 países) | 1 | US |
| United States / United Kingdom | 1 | US |
| United States / United Kingdom (doble sede Nueva York–Londres) | 1 | US |

## Qué hacer ahora

1. Mira la sección 1 (70 filas): es la que más vale — hoy esas empresas no tienen país.
2. Marca ✔/✘ y mándame el archivo. Lo que marques entrará como hecho con fuente por el importador (E2), nunca a mano.
3. Si quieres que el NRS use el país canónico, dímelo: preparo `nrs.formula` 1.1.0 y lo activas con tu PIN.
