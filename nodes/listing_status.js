// nodes/listing_status.js — GENERADO por scripts/build_listing_status.py.
// Estado en bolsa VERIFICADO con fuente (salió a bolsa / comprada /
// fusionada / filial / cerró) de empresas que el catálogo daba por
// privadas. Lo aplica nodes/merge_graph.js (navegador y snapshot).
// No editar a mano: regenerar con una nueva verificación.
window.LISTING_STATUS = {
 "as_of": "2026-09-28",
 "entries": {
  "APMTerminals": {
   "status": "subsidiary",
   "parent": "A.P. Møller-Maersk",
   "parent_ticker": "MAERSK-B.CO",
   "note_es": "Filial de A.P. Møller-Maersk; no cotiza por separado.",
   "note_en": "Subsidiary of A.P. Møller-Maersk; not separately listed.",
   "source_url": "https://en.wikipedia.org/wiki/APM_Terminals",
   "confidence": "high"
  },
  "AdaniConneX": {
   "status": "subsidiary",
   "parent": "Adani Enterprises (50%) / EdgeConneX (50%)",
   "parent_ticker": "ADANIENT.NS",
   "note_es": "JV 50/50 de Adani Enterprises y EdgeConneX; no cotiza por separado.",
   "note_en": "50/50 JV of Adani Enterprises and EdgeConneX; not separately listed.",
   "source_url": "https://www.adanienterprises.com/newsroom/media-releases/adaniconnex-a-new-data-center-joint-venture-formed-between-adani-enterprises-and-edgeconnex",
   "confidence": "medium"
  },
  "Aerojet": {
   "status": "acquired",
   "parent": "L3Harris Technologies",
   "parent_ticker": "LHX",
   "event_date": "2023-07-28",
   "note_es": "Comprada por L3Harris (LHX) en jul-2023; ya no cotiza.",
   "note_en": "Acquired by L3Harris (LHX) in Jul 2023; no longer listed.",
   "source_url": "https://en.wikipedia.org/wiki/Aerojet_Rocketdyne",
   "confidence": "high"
  },
  "AlignedDataCenters": {
   "status": "acquired",
   "parent": "AIP / MGX / BlackRock's GIP consortium",
   "parent_ticker": "BLK",
   "event_date": "2026-07-21",
   "note_es": "AIP, MGX y GIP (BlackRock) cerraron su compra por ~US$40.000M el 21-jul-2026.",
   "note_en": "AIP, MGX and BlackRock's GIP closed its ~US$40bn acquisition on 21-Jul-2026.",
   "source_url": "https://www.businesswire.com/news/home/20260720395324/en/AIP-MGX-and-BlackRocks-GIP-Close-Acquisition-of-Aligned-Data-Centers",
   "confidence": "high"
  },
  "Altium": {
   "status": "acquired",
   "parent": "Renesas Electronics",
   "parent_ticker": "6723.T",
   "event_date": "2024-08-01",
   "note_es": "Comprada por Renesas (6723.T) en ago-2024; ya no cotiza en la ASX.",
   "note_en": "Acquired by Renesas (6723.T) in Aug 2024; delisted from the ASX.",
   "source_url": "https://en.wikipedia.org/wiki/Altium",
   "confidence": "high"
  },
  "AmpereComputing": {
   "status": "acquired",
   "parent": "SoftBank Group",
   "parent_ticker": "9984.T",
   "event_date": "2025-11-25",
   "note_es": "SoftBank completó su compra por $6.500M el 25-nov-2025; ahora es filial 100% de SoftBank.",
   "note_en": "SoftBank completed its $6.5B acquisition on 25-Nov-2025; now a wholly owned SoftBank subsidiary.",
   "source_url": "https://group.softbank/en/news/press/20251126",
   "confidence": "high"
  },
  "AnhuiConch": {
   "status": "public",
   "ticker": "0914.HK",
   "exchange": "HKEX",
   "note_es": "Símbolo mal formado: 600585 es el código A-share de Shanghái, no de Hong Kong; la acción H de Anhui Conch es 0914.HK (A-share: 600585.SS).",
   "note_en": "Malformed symbol: 600585 is the Shanghai A-share code, not a Hong Kong code; Anhui Conch's H-share is 0914.HK (A-share: 600585.SS).",
   "source_url": "https://www.hkex.com.hk/Market-Data/Securities-Prices/Equities/Equities-Quote?sym=914&sc_lang=en",
   "confidence": "high"
  },
  "AnsysEDA": {
   "status": "acquired",
   "parent": "Synopsys",
   "parent_ticker": "SNPS",
   "event_date": "2025-07-17",
   "note_es": "Comprada por Synopsys (SNPS) en jul-2025; ya no cotiza.",
   "note_en": "Acquired by Synopsys (SNPS) in Jul 2025; no longer listed.",
   "source_url": "https://en.wikipedia.org/wiki/Ansys",
   "confidence": "high"
  },
  "ArcadiumLithium": {
   "status": "acquired",
   "parent": "Rio Tinto",
   "parent_ticker": "RIO",
   "event_date": "2025-03-06",
   "note_es": "Comprada por Rio Tinto (RIO) en mar-2025 por ~US$6.700M; ya no cotiza.",
   "note_en": "Acquired by Rio Tinto (RIO) in Mar 2025 for ~US$6.7B; no longer listed.",
   "source_url": "https://en.wikipedia.org/wiki/Arcadium_Lithium",
   "confidence": "high"
  },
  "Ascenty": {
   "status": "subsidiary",
   "parent": "Digital Realty / Brookfield Infrastructure",
   "parent_ticker": "DLR",
   "note_es": "JV controlada por Digital Realty (51%) con Brookfield (49%).",
   "note_en": "JV controlled by Digital Realty (51%) with Brookfield (49%).",
   "source_url": "https://ascenty.com/en/about/investors/",
   "confidence": "medium"
  },
  "BMW": {
   "status": "public",
   "ticker": "BMW.DE",
   "exchange": "XETRA",
   "note_es": "Cotiza en Fráncfort/XETRA (BMW); siempre fue pública.",
   "note_en": "Listed on Frankfurt/XETRA (BMW); it has always been public.",
   "source_url": "https://finance.yahoo.com/quote/BMW.DE/",
   "confidence": "high"
  },
  "BNSFRailway": {
   "status": "subsidiary",
   "parent": "Berkshire Hathaway",
   "parent_ticker": "BRK-B",
   "event_date": "2010-02",
   "note_es": "Filial 100% de Berkshire Hathaway.",
   "note_en": "Wholly owned subsidiary of Berkshire Hathaway.",
   "source_url": "https://en.wikipedia.org/wiki/BNSF_Railway",
   "confidence": "high"
  },
  "BenevolentAI": {
   "status": "defunct",
   "parent": "Osaka Holdings (founder-led take-private)",
   "event_date": "2025-03",
   "note_es": "Excluida de Euronext Amsterdam en 2025 tras una oferta para sacarla de bolsa; hoy es privada.",
   "note_en": "Delisted from Euronext Amsterdam in 2025 after a take-private offer; now private.",
   "source_url": "https://en.wikipedia.org/wiki/BenevolentAI",
   "confidence": "medium"
  },
  "BerkshireHathawayEnergy": {
   "status": "subsidiary",
   "parent": "Berkshire Hathaway Inc.",
   "parent_ticker": "BRK-B",
   "note_es": "Subsidiaria de Berkshire Hathaway (~92%); no cotiza.",
   "note_en": "Subsidiary of Berkshire Hathaway (~92%); not listed.",
   "source_url": "https://www.brkenergy.com/",
   "confidence": "high"
  },
  "BostonDynamics": {
   "status": "subsidiary",
   "parent": "Hyundai Motor Group",
   "parent_ticker": "005380.KS",
   "event_date": "2026-07",
   "note_es": "Filial de Hyundai, que en jul-2026 compró el ~10% restante de SoftBank; IPO poco probable antes de 2028.",
   "note_en": "Hyundai subsidiary; Hyundai bought SoftBank's remaining ~10% in Jul 2026; IPO unlikely before 2028.",
   "source_url": "https://yournews.com/2026/09/14/7194096/boston-dynamics-ipo-unlikely-in-2027-as-hyundai-prioritizes-robot/",
   "confidence": "medium"
  },
  "Boyd Thermal": {
   "status": "acquired",
   "parent": "Eaton",
   "parent_ticker": "ETN",
   "event_date": "2026-03-12",
   "note_es": "Eaton completó su compra por US$9.500M el 12-mar-2026.",
   "note_en": "Eaton completed its US$9.5bn acquisition on 12-Mar-2026.",
   "source_url": "https://www.businesswire.com/news/home/20260312582488/en/Eaton-completes-acquisition-of-leading-liquid-cooling-solutions-provider-Boyd-Thermal-creating-an-industry-leading-grid-to-chip-solution-for-data-centers",
   "confidence": "high"
  },
  "CMC_Materials": {
   "status": "acquired",
   "parent": "Entegris",
   "parent_ticker": "ENTG",
   "event_date": "2022-07-06",
   "note_es": "Comprada por Entegris (ENTG) en jul-2022; ya no cotiza ('CMIT' no es su ticker).",
   "note_en": "Acquired by Entegris (ENTG) in Jul 2022; no longer listed ('CMIT' is not its ticker).",
   "source_url": "https://en.wikipedia.org/wiki/CMC_Materials",
   "confidence": "high"
  },
  "CMOC": {
   "status": "public",
   "ticker": "3993.HK",
   "exchange": "HKEX",
   "note_es": "Símbolo mal formado: 603993 es el código A-share de Shanghái, no de Hong Kong; la acción H de CMOC es 3993.HK (A-share: 603993.SS).",
   "note_en": "Malformed symbol: 603993 is the Shanghai A-share code, not a Hong Kong code; CMOC's H-share is 3993.HK (A-share: 603993.SS).",
   "source_url": "https://www.hkex.com.hk/Market-Data/Securities-Prices/Equities/Equities-Quote?sym=3993&sc_lang=en",
   "confidence": "high"
  },
  "COSCOShipping": {
   "status": "public",
   "ticker": "1919.HK",
   "exchange": "HKEX",
   "note_es": "Símbolo mal formado: 601919 es el código A-share de Shanghái, no de Hong Kong; la acción H de COSCO Shipping Holdings es 1919.HK (A-share: 601919.SS).",
   "note_en": "Malformed symbol: 601919 is the Shanghai A-share code, not a Hong Kong code; COSCO Shipping Holdings's H-share is 1919.HK (A-share: 601919.SS).",
   "source_url": "https://www.hkex.com.hk/Market-Data/Securities-Prices/Equities/Equities-Quote?sym=1919&sc_lang=en",
   "confidence": "high"
  },
  "Calpine": {
   "status": "acquired",
   "parent": "Constellation Energy",
   "parent_ticker": "CEG",
   "event_date": "2026-01-07",
   "note_es": "Adquirida por Constellation Energy (CEG) el 7-ene-2026.",
   "note_en": "Acquired by Constellation Energy (CEG) on 7-Jan-2026.",
   "source_url": "https://www.constellationenergy.com/news/2026/01/constellation-completes-calpine-transaction-powering-americas-clean-energy-future.html",
   "confidence": "high"
  },
  "CapellaSpace": {
   "status": "acquired",
   "parent": "IonQ",
   "parent_ticker": "IONQ",
   "event_date": "2025-07-15",
   "note_es": "IonQ completó su adquisición el 15-jul-2025.",
   "note_en": "IonQ completed its acquisition on 15-Jul-2025.",
   "source_url": "https://investors.ionq.com/news/news-details/2025/IonQ-Completes-Acquisition-of-Capella-Space-Advancing-Vision-for-Space-Based-Quantum-Communications/default.aspx",
   "confidence": "high"
  },
  "Cathay_Cargo": {
   "status": "subsidiary",
   "parent": "Cathay Pacific Airways",
   "parent_ticker": "0293.HK",
   "note_es": "Cathay Cargo es la división de carga de Cathay Pacific (0293.HK); no cotiza por separado.",
   "note_en": "Cathay Cargo is Cathay Pacific's cargo division (0293.HK); it is not separately listed.",
   "source_url": "https://www.cathaypacific.com/cx/en_HK/about-us/investor-relations.html",
   "confidence": "high"
  },
  "Cepton": {
   "status": "acquired",
   "parent": "Koito Manufacturing",
   "parent_ticker": "7276.T",
   "event_date": "2025-01-07",
   "note_es": "Koito completó su compra el 7-ene-2025 y la retiró de Nasdaq.",
   "note_en": "Koito completed its acquisition on 7-Jan-2025 and delisted it from Nasdaq.",
   "source_url": "https://www.koito.co.jp/english/news/2025/01/08/004421.html",
   "confidence": "high"
  },
  "Chalco": {
   "status": "public",
   "ticker": "2600.HK",
   "exchange": "HKEX",
   "note_es": "Símbolo mal formado: 601600 es el código A-share de Shanghái, no de Hong Kong; la acción H de Chalco es 2600.HK (A-share: 601600.SS).",
   "note_en": "Malformed symbol: 601600 is the Shanghai A-share code, not a Hong Kong code; Chalco's H-share is 2600.HK (A-share: 601600.SS).",
   "source_url": "https://www.hkex.com.hk/Market-Data/Securities-Prices/Equities/Equities-Quote?sym=2600&sc_lang=en",
   "confidence": "high"
  },
  "ChinaNorthernRareEarth": {
   "status": "public",
   "ticker": "600111.SS",
   "exchange": "SSE",
   "note_es": "Cotiza en Shanghái (600111), bajo control estatal (Baotou Steel).",
   "note_en": "Listed in Shanghai (600111), state-controlled (Baotou Steel).",
   "source_url": "http://www.sse.com.cn/assortment/stock/list/info/company/index.shtml?COMPANY_CODE=600111",
   "confidence": "high"
  },
  "CoolIT Systems": {
   "status": "acquired",
   "parent": "Ecolab",
   "parent_ticker": "ECL",
   "event_date": "2026-07-02",
   "note_es": "Ecolab completó su compra por US$4.750M en 2026.",
   "note_en": "Ecolab completed its US$4.75bn acquisition in 2026.",
   "source_url": "https://www.coolitsystems.com/resources/news/ecolab-has-closed-its-acquisition-of-coolit-systems/",
   "confidence": "high"
  },
  "CoreSite": {
   "status": "subsidiary",
   "parent": "American Tower",
   "parent_ticker": "AMT",
   "event_date": "2021-12-28",
   "note_es": "Filial de American Tower (Stonepeak con participación minoritaria); no cotiza.",
   "note_en": "Subsidiary of American Tower (Stonepeak holds a minority stake); not listed.",
   "source_url": "https://www.datacenterdynamics.com/en/news/stonepeak-to-acquire-25bn-stake-in-american-towers-coresite-business/",
   "confidence": "high"
  },
  "DeltaElectronics": {
   "status": "public",
   "ticker": "2308.TW",
   "exchange": "TWSE",
   "note_es": "Cotiza en la Bolsa de Taiwán (2308); siempre fue pública.",
   "note_en": "Listed on the Taiwan Stock Exchange (2308); it has always been public.",
   "source_url": "https://finance.yahoo.com/quote/2308.TW/",
   "confidence": "high"
  },
  "DuPont_Electronics": {
   "status": "public",
   "ticker": "Q",
   "exchange": "NYSE",
   "listed_since": "2025-11-03",
   "event_date": "2025-11-01",
   "note_es": "El negocio de electrónica de DuPont se escindió como Qnity Electronics (NYSE: Q) el 1-nov-2025.",
   "note_en": "DuPont's electronics business was spun off as Qnity Electronics (NYSE: Q) on Nov 1, 2025.",
   "source_url": "https://www.qnityelectronics.com",
   "confidence": "high"
  },
  "EON": {
   "status": "public",
   "ticker": "EOAN.DE",
   "exchange": "XETRA",
   "note_es": "Cotiza en Fráncfort (EOAN).",
   "note_en": "Listed in Frankfurt (EOAN).",
   "source_url": "https://www.eon.com/en/investor-relations.html",
   "confidence": "high"
  },
  "ESR Group": {
   "status": "acquired",
   "parent": "Starwood Capital-led consortium",
   "event_date": "2025-07-04",
   "note_es": "Deslistada de HKEX el 4-jul-2025 tras la compra de ~US$7.100M del consorcio liderado por Starwood.",
   "note_en": "Delisted from HKEX on 4-Jul-2025 after a ~US$7.1bn Starwood-led take-private.",
   "source_url": "https://www.esr.com/news/esr-completes-privatisation-strengthens-leadership-team/",
   "confidence": "high"
  },
  "ESR_Group": {
   "status": "acquired",
   "parent": "Starwood Capital-led consortium",
   "event_date": "2025-07-04",
   "note_es": "Deslistada de HKEX el 4-jul-2025 tras la compra de ~US$7.100M del consorcio liderado por Starwood.",
   "note_en": "Delisted from HKEX on 4-Jul-2025 after a ~US$7.1bn Starwood-led take-private.",
   "source_url": "https://www.esr.com/news/esr-completes-privatisation-strengthens-leadership-team/",
   "confidence": "high"
  },
  "EdgeImpulse": {
   "status": "acquired",
   "parent": "Qualcomm",
   "parent_ticker": "QCOM",
   "event_date": "2025-03",
   "note_es": "Adquirida por Qualcomm en marzo de 2025.",
   "note_en": "Acquired by Qualcomm in March 2025.",
   "source_url": "https://www.qualcomm.com/news/releases/2025/03/qualcomm-to-bolster-ai-and-iot-capabilities-with-edge-impulse-ac",
   "confidence": "high"
  },
  "Edgio": {
   "status": "defunct",
   "event_date": "2024-09-09",
   "note_es": "Se declaró en quiebra (Chapter 11) en sep-2024, vendió sus activos (parte a Akamai) y fue retirada de Nasdaq.",
   "note_en": "Filed Chapter 11 in Sep 2024, sold its assets (partly to Akamai) and was delisted from Nasdaq.",
   "source_url": "https://en.wikipedia.org/wiki/Edgio",
   "confidence": "high"
  },
  "Eni": {
   "status": "public",
   "ticker": "ENI.MI",
   "exchange": "Borsa Italiana (Euronext Milan); ADR NYSE: E",
   "note_es": "El símbolo 'ENI' no es Eni en Yahoo: cotiza como ENI.MI en Milán y su ADR en NYSE es 'E'.",
   "note_en": "'ENI' is not Eni's Yahoo symbol: it trades as ENI.MI in Milan and its NYSE ADR is 'E'.",
   "source_url": "https://www.eni.com/en-IT/investors.html",
   "confidence": "high"
  },
  "Envicool": {
   "status": "public",
   "ticker": "002837.SZ",
   "exchange": "Shenzhen Stock Exchange",
   "listed_since": "2016-12",
   "note_es": "Cotiza en la Bolsa de Shenzhen (002837).",
   "note_en": "Listed on the Shenzhen Stock Exchange (002837).",
   "source_url": "https://finance.yahoo.com/quote/002837.SZ/",
   "confidence": "high"
  },
  "Esperanto": {
   "status": "defunct",
   "parent": "Ainekko (compró su PI)",
   "event_date": "2025-11",
   "note_es": "Cerró su negocio de chips en 2025; Ainekko compró su propiedad intelectual y activos en nov-2025.",
   "note_en": "Wound down its chip business in 2025; Ainekko bought its IP and assets in Nov 2025.",
   "source_url": "https://www.eetimes.com/ainekko-buys-esperanto-hardware-ip-open-sources-it/",
   "confidence": "high"
  },
  "EvergreenMarine": {
   "status": "public",
   "ticker": "2603.TW",
   "exchange": "Taiwan Stock Exchange",
   "note_es": "Cotiza en la Bolsa de Taiwán (2603).",
   "note_en": "Listed on the Taiwan Stock Exchange (2603).",
   "source_url": "https://en.wikipedia.org/wiki/Evergreen_Marine",
   "confidence": "high"
  },
  "Exscientia": {
   "status": "merged",
   "parent": "Recursion Pharmaceuticals",
   "parent_ticker": "RXRX",
   "event_date": "2024-11-20",
   "note_es": "Se fusionó con Recursion (RXRX) en nov-2024; ya no cotiza.",
   "note_en": "Merged into Recursion (RXRX) in Nov 2024; no longer listed.",
   "source_url": "https://en.wikipedia.org/wiki/Exscientia",
   "confidence": "high"
  },
  "Fagioli": {
   "status": "acquired",
   "parent": "CEVA Logistics (CMA CGM)",
   "event_date": "2026-03-31",
   "note_es": "CEVA Logistics (grupo CMA CGM) completó su compra el 31-mar-2026.",
   "note_en": "CEVA Logistics (CMA CGM group) completed its acquisition on 31-Mar-2026.",
   "source_url": "https://www.heavyliftpfi.com/logistics/2026/03/31/ceva-completes-fagioli-acquisition/",
   "confidence": "high"
  },
  "Firefly": {
   "status": "public",
   "ticker": "FLY",
   "exchange": "Nasdaq",
   "listed_since": "2025-08-07",
   "note_es": "Salió a bolsa en Nasdaq (FLY) el 7-ago-2025 a $45 por acción.",
   "note_en": "IPO'd on Nasdaq (FLY) on 7-Aug-2025 at $45 per share.",
   "source_url": "https://fireflyspace.com/news/firefly-aerospace-announces-pricing-of-upsized-initial-public-offering/",
   "confidence": "high"
  },
  "FlexLogix": {
   "status": "acquired",
   "parent": "Analog Devices",
   "parent_ticker": "ADI",
   "event_date": "2024-11-11",
   "note_es": "Adquirida por Analog Devices (ADI) el 11-nov-2024.",
   "note_en": "Acquired by Analog Devices (ADI) on 11-Nov-2024.",
   "source_url": "https://www.eetimes.com/flex-logix-acquired-by-analog-devices/",
   "confidence": "high"
  },
  "FujitsuHPC": {
   "status": "public",
   "ticker": "6702.T",
   "exchange": "Tokyo Stock Exchange",
   "note_es": "Fujitsu cotiza en la Bolsa de Tokio (6702.T); el catálogo la marca mal como no cotizada.",
   "note_en": "Fujitsu is listed on the Tokyo Stock Exchange (6702.T); the catalog wrongly marks it unlisted.",
   "source_url": "https://www.fujitsu.com/global/about/ir/",
   "confidence": "high"
  },
  "GEHitachiNuclear": {
   "status": "subsidiary",
   "parent": "GE Vernova",
   "parent_ticker": "GEV",
   "note_es": "JV controlada por GE Vernova (GEV) con Hitachi (6501.T) como socio minoritario; no cotiza.",
   "note_en": "JV controlled by GE Vernova (GEV) with Hitachi (6501.T) as minority partner; not listed.",
   "source_url": "https://www.gevernova.com/nuclear",
   "confidence": "medium"
  },
  "GanfengLithium": {
   "status": "public",
   "ticker": "1772.HK",
   "exchange": "HKEX",
   "note_es": "Símbolo mal formado: 002460 es el código A-share de Shenzhen, no de Hong Kong; la acción H de Ganfeng Lithium es 1772.HK (A-share: 002460.SZ).",
   "note_en": "Malformed symbol: 002460 is the Shenzhen A-share code, not a Hong Kong code; Ganfeng Lithium's H-share is 1772.HK (A-share: 002460.SZ).",
   "source_url": "https://www.hkex.com.hk/Market-Data/Securities-Prices/Equities/Equities-Quote?sym=1772&sc_lang=en",
   "confidence": "high"
  },
  "Gazprom": {
   "status": "public",
   "ticker": "GAZP.ME",
   "exchange": "MOEX",
   "note_es": "Cotiza en la Bolsa de Moscú (GAZP), control estatal.",
   "note_en": "Listed on Moscow Exchange (GAZP), state-controlled.",
   "source_url": "https://www.gazprom.com/investors/",
   "confidence": "high"
  },
  "GeneralFusion": {
   "status": "public",
   "ticker": "GFUZ",
   "exchange": "Nasdaq",
   "listed_since": "2026-07-13",
   "event_date": "2026-07-10",
   "note_es": "Cotiza en Nasdaq (GFUZ) desde el 13-jul-2026 tras fusionarse con el SPAC Spring Valley III.",
   "note_en": "Trades on Nasdaq (GFUZ) since 13-Jul-2026 after merging with SPAC Spring Valley III.",
   "source_url": "https://generalfusion.com/post/general-fusion-completes-business-combination-with-spring-valley-acquisition-corp-iii/",
   "confidence": "high"
  },
  "GlobalWafers": {
   "status": "public",
   "ticker": "6488.TWO",
   "exchange": "TPEx (Taipei Exchange)",
   "note_es": "Cotiza en la bolsa de Taipéi TPEx con el código 6488; el catálogo la marcaba como no cotizada por error.",
   "note_en": "Listed on Taipei Exchange (TPEx) under code 6488; the catalog wrongly marked it as unlisted.",
   "source_url": "https://finance.yahoo.com/quote/6488.TWO/",
   "confidence": "high"
  },
  "GrAI_Matter": {
   "status": "acquired",
   "parent": "Snap Inc.",
   "parent_ticker": "SNAP",
   "event_date": "2023-10-31",
   "note_es": "Adquirida por Snap Inc. (SNAP) el 31-oct-2023.",
   "note_en": "Acquired by Snap Inc. (SNAP) on 31-Oct-2023.",
   "source_url": "https://www.eetimes.com/has-grai-matter-labs-been-snapped-up-by-snap-inc/",
   "confidence": "high"
  },
  "Graphcore": {
   "status": "acquired",
   "parent": "SoftBank Group",
   "parent_ticker": "9984.T",
   "event_date": "2024-07",
   "note_es": "Adquirida por SoftBank Group (9984.T) en 2024; ya no es independiente.",
   "note_en": "Acquired by SoftBank Group (9984.T) in 2024; no longer independent.",
   "source_url": "https://www.softbank.jp/en/corp/news/press/sbkk/",
   "confidence": "medium"
  },
  "GrupoMexico": {
   "status": "public",
   "ticker": "GMEXICOB.MX",
   "exchange": "BMV",
   "note_es": "Cotiza en la Bolsa Mexicana (GMEXICO B).",
   "note_en": "Listed on the Mexican Stock Exchange (GMEXICO B).",
   "source_url": "https://www.gmexico.com/en/Pages/investors.aspx",
   "confidence": "high"
  },
  "Hailo": {
   "status": "acquired",
   "parent": "Microchip Technology",
   "parent_ticker": "MCHP",
   "event_date": "2026-09-21",
   "note_es": "Microchip Technology completó su adquisición el 21-sept-2026 tras el fracaso de su fusión con un SPAC.",
   "note_en": "Microchip Technology completed its acquisition on 21-Sep-2026 after its SPAC merger collapsed.",
   "source_url": "https://ir.microchip.com/news-events/press-releases/detail/1415/microchip-technology-completes-acquisition-of-hailo",
   "confidence": "high"
  },
  "HashiCorp": {
   "status": "acquired",
   "parent": "IBM",
   "parent_ticker": "IBM",
   "event_date": "2025-02-27",
   "note_es": "Comprada por IBM en feb-2025; ya no cotiza.",
   "note_en": "Acquired by IBM in Feb 2025; no longer listed.",
   "source_url": "https://en.wikipedia.org/wiki/HashiCorp",
   "confidence": "high"
  },
  "HawkEye360": {
   "status": "public",
   "ticker": "HAWK",
   "exchange": "NYSE",
   "listed_since": "2026-05-07",
   "note_es": "Salió a bolsa en la NYSE (HAWK) el 7-may-2026 a $26 por acción, recaudando $416M.",
   "note_en": "IPO'd on the NYSE (HAWK) on 7-May-2026 at $26/share, raising $416M.",
   "source_url": "https://qz.com/hawkeye-360-ipo-nyse-hawk-416-million-050726",
   "confidence": "high"
  },
  "HemlockSemiconductor": {
   "status": "subsidiary",
   "parent": "Corning Inc.",
   "parent_ticker": "GLW",
   "note_es": "Participada mayoritariamente por Corning (~80,5%); no cotiza.",
   "note_en": "Majority-owned by Corning (~80.5%); not listed.",
   "source_url": "https://www.corning.com/worldwide/en/about-us/company-profile.html",
   "confidence": "medium"
  },
  "HughesNetwork": {
   "status": "subsidiary",
   "parent": "EchoStar",
   "parent_ticker": "SATS",
   "note_es": "Filial de EchoStar (Nasdaq: SATS); no cotiza por separado.",
   "note_en": "Subsidiary of EchoStar (Nasdaq: SATS); not separately listed.",
   "source_url": "https://www.hughes.com/who-we-are",
   "confidence": "medium"
  },
  "HutchisonPorts": {
   "status": "subsidiary",
   "parent": "CK Hutchison Holdings",
   "parent_ticker": "0001.HK",
   "note_es": "Filial de CK Hutchison; la venta del 80% a BlackRock/MSC sigue sin cerrarse.",
   "note_en": "Subsidiary of CK Hutchison; the 80% sale to BlackRock/MSC remains unclosed.",
   "source_url": "https://theloadstar.com/hutchwatch-the-23bn-port-deal-that-nobody-can-close/",
   "confidence": "high"
  },
  "Hyundai": {
   "status": "public",
   "ticker": "005380.KS",
   "exchange": "KRX (KOSPI)",
   "note_es": "Cotiza en la Bolsa de Corea (005380); siempre fue pública.",
   "note_en": "Listed on the Korea Exchange (005380); it has always been public.",
   "source_url": "https://finance.yahoo.com/quote/005380.KS/",
   "confidence": "high"
  },
  "ITCHoldings": {
   "status": "subsidiary",
   "parent": "Fortis Inc.",
   "parent_ticker": "FTS.TO",
   "note_es": "Subsidiaria de Fortis (80,1%; GIC 19,9%); no cotiza.",
   "note_en": "Fortis subsidiary (80.1%; GIC 19.9%); not listed.",
   "source_url": "https://www.fortisinc.com/our-utilities/itc",
   "confidence": "high"
  },
  "Imperva": {
   "status": "subsidiary",
   "parent": "Thales",
   "parent_ticker": "HO.PA",
   "event_date": "2023-12",
   "note_es": "Filial de Thales desde que completó su compra por $3.600M en dic-2023.",
   "note_en": "Thales subsidiary since Thales completed its $3.6B purchase in Dec 2023.",
   "source_url": "https://www.thalesgroup.com/en/worldwide/group/press_release/thales-completes-acquisition-imperva",
   "confidence": "medium"
  },
  "InfiniteraNet": {
   "status": "acquired",
   "parent": "Nokia",
   "parent_ticker": "NOK",
   "event_date": "2025-02-28",
   "note_es": "Comprada por Nokia (NOK) en feb-2025; ya no cotiza.",
   "note_en": "Acquired by Nokia (NOK) in Feb 2025; no longer listed.",
   "source_url": "https://en.wikipedia.org/wiki/Infinera",
   "confidence": "high"
  },
  "Innolight": {
   "status": "public",
   "ticker": "300308.SZ",
   "exchange": "SZSE ChiNext + HKEX (3308.HK)",
   "listed_since": "2026-07-30",
   "note_es": "Cotiza en Shenzhen (300308) y desde el 30-jul-2026 también en Hong Kong (3308) tras recaudar ~$6.800M.",
   "note_en": "Listed in Shenzhen (300308) and, since 30-Jul-2026, also in Hong Kong (3308) after raising ~$6.8B.",
   "source_url": "https://www.trendforce.com/news/2026/08/03/news-zj-innolight-debuts-on-hkex-in-record-ipo-as-inp-substrate-bottleneck-intensifies/",
   "confidence": "high"
  },
  "Insilico": {
   "status": "public",
   "ticker": "3696.HK",
   "exchange": "HKEX",
   "listed_since": "2025-12-30",
   "note_es": "Cotiza en la Bolsa de Hong Kong (3696) desde el 30-dic-2025.",
   "note_en": "Listed on the Hong Kong Stock Exchange (3696) since 30-Dec-2025.",
   "source_url": "https://insilico.com/news/p010170up1-insilico-medicine-lists-on-hong-kong-sto",
   "confidence": "high"
  },
  "JSR": {
   "status": "acquired",
   "parent": "Japan Investment Corporation (JIC, estatal)",
   "event_date": "2024-06",
   "note_es": "Fue comprada por el fondo estatal JIC y excluida de la Bolsa de Tokio en 2024.",
   "note_en": "Taken private by state-backed fund JIC and delisted from the Tokyo Stock Exchange in 2024.",
   "source_url": "https://www.jsr.co.jp/jsr/en/",
   "confidence": "medium"
  },
  "JioDataCenters": {
   "status": "subsidiary",
   "parent": "Reliance Industries",
   "parent_ticker": "RELIANCE.NS",
   "note_es": "Unidad de Reliance Industries/Jio Platforms; no cotiza por separado.",
   "note_en": "Unit of Reliance Industries/Jio Platforms; not separately listed.",
   "source_url": "https://en.wikipedia.org/wiki/Jio_Platforms",
   "confidence": "medium"
  },
  "KGHM": {
   "status": "public",
   "ticker": "KGH.WA",
   "exchange": "GPW Warsaw",
   "note_es": "Cotiza en la Bolsa de Varsovia (KGH); el Estado polaco tiene ~31,8%.",
   "note_en": "Listed on the Warsaw Stock Exchange (KGH); Polish State holds ~31.8%.",
   "source_url": "https://kghm.com/en/investors",
   "confidence": "high"
  },
  "Kensho": {
   "status": "subsidiary",
   "parent": "S&P Global",
   "parent_ticker": "SPGI",
   "event_date": "2018-04",
   "note_es": "Filial de S&P Global desde 2018; no cotiza por separado.",
   "note_en": "S&P Global subsidiary since 2018; not separately listed.",
   "source_url": "https://kensho.com/",
   "confidence": "high"
  },
  "Lightelligence": {
   "status": "public",
   "ticker": "1879.HK",
   "exchange": "HKEX",
   "listed_since": "2026-04-28",
   "note_es": "Salió a bolsa en Hong Kong (1879) el 28-abr-2026 a HK$183,2 y subió 383% en su debut.",
   "note_en": "Listed in Hong Kong (1879) on 28-Apr-2026 at HK$183.2 and rose 383% on debut.",
   "source_url": "https://www.caixinglobal.com/2026-04-28/lightelligence-sets-record-ipo-gain-with-383-surge-on-hong-kong-debut-102438977.html",
   "confidence": "high"
  },
  "Lightsource_BP": {
   "status": "subsidiary",
   "parent": "BP",
   "parent_ticker": "BP.L",
   "event_date": "2024-10",
   "note_es": "Filial 100% de BP (BP.L) desde 2024; BP negocia venderla a un consorcio respaldado por Kuwait (jul-2026).",
   "note_en": "Wholly owned by BP (BP.L) since 2024; BP is negotiating a sale to a Kuwait-backed consortium (Jul-2026).",
   "source_url": "https://solarquarter.com/2026/07/29/british-petroleum-moves-to-sell-lightsource-solar-business-to-kuwait-backed-consortium/",
   "confidence": "high"
  },
  "LiquidStack": {
   "status": "acquired",
   "parent": "Trane Technologies",
   "parent_ticker": "TT",
   "event_date": "2026-03-03",
   "note_es": "Trane Technologies completó su compra el 3-mar-2026.",
   "note_en": "Trane Technologies completed its acquisition on 3-Mar-2026.",
   "source_url": "https://www.businesswire.com/news/home/20260303582406/en/Trane-Technologies-Completes-Acquisition-of-LiquidStack",
   "confidence": "high"
  },
  "Livent": {
   "status": "acquired",
   "parent": "Rio Tinto",
   "parent_ticker": "RIO",
   "event_date": "2025-03-06",
   "note_es": "Se fusionó con Allkem como Arcadium Lithium (ene-2024), que Rio Tinto compró en mar-2025; ya no cotiza.",
   "note_en": "Merged with Allkem into Arcadium Lithium (Jan 2024), which Rio Tinto acquired in Mar 2025; no longer listed.",
   "source_url": "https://en.wikipedia.org/wiki/Arcadium_Lithium",
   "confidence": "high"
  },
  "Lukoil": {
   "status": "public",
   "ticker": "LKOH.ME",
   "exchange": "MOEX",
   "note_es": "Cotiza en la Bolsa de Moscú (LKOH); sancionada por EE.UU. desde oct-2025.",
   "note_en": "Listed on Moscow Exchange (LKOH); under US sanctions since Oct 2025.",
   "source_url": "https://lukoil.com/InvestorAndShareholderCenter",
   "confidence": "high"
  },
  "Maersk": {
   "status": "public",
   "ticker": "MAERSK-B.CO",
   "exchange": "Nasdaq Copenhagen",
   "note_es": "Cotiza en Nasdaq Copenhague (MAERSK-B).",
   "note_en": "Listed on Nasdaq Copenhagen (MAERSK-B).",
   "source_url": "https://en.wikipedia.org/wiki/Maersk",
   "confidence": "high"
  },
  "Maxar": {
   "status": "acquired",
   "parent": "Advent International",
   "event_date": "2023-05",
   "note_es": "Adquirida por Advent International (2023) y dividida: hoy Vantor (privada) y Lanteris, vendida a Intuitive Machines (LUNR) en ene-2026.",
   "note_en": "Acquired by Advent International (2023) and split: now Vantor (private) and Lanteris, sold to Intuitive Machines (LUNR) in Jan-2026.",
   "source_url": "https://breakingdefense.com/2025/10/whats-in-a-name-goodbye-maxar-hello-vantor-and-lanteris/",
   "confidence": "high"
  },
  "Maximus_Air": {
   "status": "subsidiary",
   "parent": "Abu Dhabi Aviation",
   "event_date": "2008-11",
   "note_es": "Filial (95%) de Abu Dhabi Aviation (cotizada en ADX) desde 2008.",
   "note_en": "95%-owned subsidiary of Abu Dhabi Aviation (listed on ADX) since 2008.",
   "source_url": "https://en.wikipedia.org/wiki/Maximus_Air",
   "confidence": "medium"
  },
  "MediaTek": {
   "status": "public",
   "ticker": "2454.TW",
   "exchange": "TWSE",
   "note_es": "Cotiza en la Bolsa de Taiwán (2454); siempre fue pública.",
   "note_en": "Listed on the Taiwan Stock Exchange (2454); it has always been public.",
   "source_url": "https://finance.yahoo.com/quote/2454.TW/",
   "confidence": "high"
  },
  "Meeza": {
   "status": "public",
   "ticker": "MEZA.QA",
   "exchange": "Qatar Stock Exchange",
   "listed_since": "2023-08-23",
   "note_es": "Cotiza en la Bolsa de Qatar (MEZA) desde el 23-ago-2023.",
   "note_en": "Listed on the Qatar Stock Exchange (MEZA) since 23-Aug-2023.",
   "source_url": "https://www.meeza.net/meeza-successfully-listed-on-qatar-stock-exchange-main-market/",
   "confidence": "high"
  },
  "MoodysRatings": {
   "status": "subsidiary",
   "parent": "Moody's Corporation",
   "parent_ticker": "MCO",
   "note_es": "Moody's Ratings es una división de Moody's Corporation (MCO); no cotiza por separado.",
   "note_en": "Moody's Ratings is a division of Moody's Corporation (MCO); it is not separately listed.",
   "source_url": "https://ir.moodys.com/",
   "confidence": "high"
  },
  "MoroHub": {
   "status": "subsidiary",
   "parent": "Dubai Electricity and Water Authority (DEWA)",
   "note_es": "Filial de Digital DEWA, brazo de DEWA (cotizada en el DFM de Dubái).",
   "note_en": "Subsidiary of Digital DEWA, the digital arm of DEWA (listed on Dubai Financial Market).",
   "source_url": "https://www.morohub.com/",
   "confidence": "medium"
  },
  "Nakilat": {
   "status": "public",
   "ticker": "QGTS.QA",
   "exchange": "Qatar Stock Exchange",
   "note_es": "Cotiza en la Bolsa de Qatar (QGTS).",
   "note_en": "Listed on the Qatar Stock Exchange (QGTS).",
   "source_url": "https://en.wikipedia.org/wiki/Nakilat",
   "confidence": "high"
  },
  "Nanya": {
   "status": "public",
   "ticker": "2408.TW",
   "exchange": "TWSE",
   "note_es": "Nanya Technology cotiza como 2408 en TWSE; 2303 es UMC, otra empresa.",
   "note_en": "Nanya Technology trades as 2408 on TWSE; 2303 is UMC, a different company.",
   "source_url": "https://en.wikipedia.org/wiki/Nanya_Technology",
   "confidence": "high"
  },
  "Naver": {
   "status": "public",
   "ticker": "035420.KS",
   "exchange": "KOSPI",
   "note_es": "Cotiza en el KOSPI de Corea (035420); siempre fue pública.",
   "note_en": "Listed on Korea's KOSPI (035420); it has always been public.",
   "source_url": "https://finance.yahoo.com/quote/035420.KS/",
   "confidence": "high"
  },
  "Nornickel": {
   "status": "public",
   "ticker": "GMKN.ME",
   "exchange": "MOEX",
   "note_es": "Cotiza en la Bolsa de Moscú (GMKN).",
   "note_en": "Listed on Moscow Exchange (GMKN).",
   "source_url": "https://nornickel.com/investors/",
   "confidence": "high"
  },
  "NxtraData": {
   "status": "subsidiary",
   "parent": "Bharti Airtel",
   "parent_ticker": "BHARTIARTL.NS",
   "note_es": "Filial de Bharti Airtel, que mantiene el control tras la ronda de US$1.000M de 2026.",
   "note_en": "Subsidiary of Bharti Airtel, which keeps control after the 2026 US$1bn round.",
   "source_url": "https://www.cnbc.com/2026/03/31/pe-alpha-wave-carlyle-1-billion-airtel-data-center.html",
   "confidence": "high"
  },
  "Orano": {
   "status": "subsidiary",
   "parent": "Estado francés (APE/CEA ~90%; JNFL y MHI ~5% c/u)",
   "event_date": "2018-01",
   "note_es": "Orano no cotiza en bolsa: ~90% pertenece al Estado francés y el resto a JNFL y Mitsubishi Heavy; 'ORAN' no es su ticker.",
   "note_en": "Orano is not listed: ~90% owned by the French State, the rest by JNFL and Mitsubishi Heavy; 'ORAN' is not its ticker.",
   "source_url": "https://www.orano.group/en/group/who-we-are",
   "confidence": "high"
  },
  "Orbcomm": {
   "status": "acquired",
   "parent": "GI Partners",
   "event_date": "2021-09-01",
   "note_es": "Adquirida por GI Partners en 2021 y retirada de Nasdaq; sigue privada.",
   "note_en": "Acquired by GI Partners in 2021 and delisted from Nasdaq; remains private.",
   "source_url": "https://www.orbcomm.com/en/company/news/2021/orbcomm-completes-acquisition-by-gi-partners",
   "confidence": "medium"
  },
  "Orsted": {
   "status": "public",
   "ticker": "ORSTED.CO",
   "exchange": "Nasdaq Copenhagen",
   "note_es": "Cotiza en Copenhague (ORSTED); el Estado danés es accionista mayoritario.",
   "note_en": "Listed in Copenhagen (ORSTED); Danish State is majority shareholder.",
   "source_url": "https://orsted.com/en/investors",
   "confidence": "high"
  },
  "PIMCO": {
   "status": "subsidiary",
   "parent": "Allianz SE",
   "parent_ticker": "ALV.DE",
   "note_es": "Filial de Allianz SE; no cotiza por separado.",
   "note_en": "Subsidiary of Allianz SE; not separately listed.",
   "source_url": "https://en.wikipedia.org/wiki/PIMCO",
   "confidence": "high"
  },
  "Pasqal": {
   "status": "public",
   "ticker": "PSQL",
   "exchange": "Nasdaq",
   "listed_since": "2026-08-28",
   "event_date": "2026-08-27",
   "note_es": "Cotiza en Nasdaq (PSQL) desde el 28-ago-2026 tras fusionarse con el SPAC Bleichroeder Acquisition Corp. II.",
   "note_en": "Trades on Nasdaq (PSQL) since 28-Aug-2026 after merging with SPAC Bleichroeder Acquisition Corp. II.",
   "source_url": "https://investors.pasqal.com/news-releases/news-release-details/pasqal-and-bleichroeder-acquisition-corp-ii-complete-business",
   "confidence": "high"
  },
  "PetroChina": {
   "status": "public",
   "ticker": "0857.HK",
   "exchange": "HKEX",
   "note_es": "Símbolo mal formado: 601857 es el código A-share de Shanghái, no de Hong Kong; la acción H de PetroChina es 0857.HK (A-share: 601857.SS).",
   "note_en": "Malformed symbol: 601857 is the Shanghai A-share code, not a Hong Kong code; PetroChina's H-share is 0857.HK (A-share: 601857.SS).",
   "source_url": "https://www.hkex.com.hk/Market-Data/Securities-Prices/Equities/Equities-Quote?sym=857&sc_lang=en",
   "confidence": "high"
  },
  "PiedmontLithium": {
   "status": "merged",
   "parent": "Elevra Lithium",
   "parent_ticker": "ELV.AX",
   "event_date": "2025-08-29",
   "note_es": "Se fusionó con Sayona Mining para formar Elevra Lithium (ASX: ELV) en ago-2025; PLL ya no cotiza.",
   "note_en": "Merged with Sayona Mining to form Elevra Lithium (ASX: ELV) in Aug 2025; PLL no longer trades.",
   "source_url": "https://en.wikipedia.org/wiki/Piedmont_Lithium",
   "confidence": "high"
  },
  "PowerchipSemi": {
   "status": "public",
   "ticker": "6770.TW",
   "exchange": "TWSE",
   "note_es": "Powerchip Semiconductor Manufacturing (PSMC) cotiza como 6770 en TWSE; 6239 es Powertech Technology, otra empresa.",
   "note_en": "Powerchip Semiconductor Manufacturing (PSMC) trades as 6770 on TWSE; 6239 is Powertech Technology, a different company.",
   "source_url": "https://en.wikipedia.org/wiki/Powerchip",
   "confidence": "high"
  },
  "QTS": {
   "status": "acquired",
   "parent": "Blackstone Infrastructure / BREIT",
   "parent_ticker": "BX",
   "event_date": "2021-08-31",
   "note_es": "Comprada por Blackstone en ago-2021; ya no cotiza (BX es el ticker del comprador).",
   "note_en": "Acquired by Blackstone in Aug 2021; no longer listed (BX is the acquirer's ticker).",
   "source_url": "https://en.wikipedia.org/wiki/QTS_Realty_Trust",
   "confidence": "high"
  },
  "Quantinuum": {
   "status": "public",
   "ticker": "QNT",
   "exchange": "Nasdaq",
   "listed_since": "2026-06-04",
   "note_es": "Salió a bolsa en Nasdaq (QNT) el 4-jun-2026 a $60 por acción, recaudando $1.680M; Honeywell sigue como accionista mayoritario.",
   "note_en": "IPO'd on Nasdaq (QNT) on 4-Jun-2026 at $60/share, raising $1.68B; Honeywell remains majority holder.",
   "source_url": "https://www.cnbc.com/2026/06/04/quantinuum-qnt-stock-first-trade-ipo.html",
   "confidence": "high"
  },
  "RWE": {
   "status": "public",
   "ticker": "RWE.DE",
   "exchange": "XETRA",
   "note_es": "Cotiza en Fráncfort (RWE).",
   "note_en": "Listed in Frankfurt (RWE).",
   "source_url": "https://www.rwe.com/en/investor-relations/",
   "confidence": "high"
  },
  "Richtek": {
   "status": "subsidiary",
   "parent": "MediaTek",
   "parent_ticker": "2454.TW",
   "event_date": "2019",
   "note_es": "Filial 100% de MediaTek (2454.TW) y retirada de la bolsa de Taiwán; 6286 ya no cotiza.",
   "note_en": "Wholly owned MediaTek (2454.TW) subsidiary, delisted from the Taiwan exchange; 6286 no longer trades.",
   "source_url": "https://en.wikipedia.org/wiki/Richtek_Technology",
   "confidence": "medium"
  },
  "RioTintoAluminium": {
   "status": "subsidiary",
   "parent": "Rio Tinto",
   "parent_ticker": "RIO",
   "note_es": "Rio Tinto Aluminium es una división de Rio Tinto (RIO / RIO.L / RIO.AX); no cotiza por separado.",
   "note_en": "Rio Tinto Aluminium is a division of Rio Tinto (RIO / RIO.L / RIO.AX); it is not separately listed.",
   "source_url": "https://www.riotinto.com/en/invest",
   "confidence": "high"
  },
  "RockleyPhotonics": {
   "status": "defunct",
   "event_date": "2023-01",
   "note_es": "Entró en liquidación provisional/reestructuración en ene-2023 y fue retirada de la NYSE; hoy es privada.",
   "note_en": "Entered provisional liquidation/restructuring in Jan 2023 and was delisted from the NYSE; now private.",
   "source_url": "https://en.wikipedia.org/wiki/Rockley_Photonics",
   "confidence": "medium"
  },
  "RollsRoyceSMR": {
   "status": "subsidiary",
   "parent": "Rolls-Royce Holdings",
   "parent_ticker": "RR.L",
   "note_es": "Filial mayoritaria de Rolls-Royce Holdings (RR.L); no cotiza por separado.",
   "note_en": "Majority-owned subsidiary of Rolls-Royce Holdings (RR.L); not separately listed.",
   "source_url": "https://www.rolls-royce-smr.com/",
   "confidence": "medium"
  },
  "Rosneft": {
   "status": "public",
   "ticker": "ROSN.ME",
   "exchange": "MOEX",
   "note_es": "Cotiza en la Bolsa de Moscú (ROSN), control estatal; sancionada.",
   "note_en": "Listed on Moscow Exchange (ROSN), state-controlled; under sanctions.",
   "source_url": "https://www.rosneft.com/Investors/",
   "confidence": "high"
  },
  "Rumo": {
   "status": "public",
   "ticker": "RAIL3.SA",
   "exchange": "B3",
   "note_es": "Cotiza en B3 (RAIL3).",
   "note_en": "Listed on B3 (RAIL3).",
   "source_url": "https://en.wikipedia.org/wiki/Rumo_Logística",
   "confidence": "high"
  },
  "SAIC": {
   "status": "public",
   "ticker": "600104.SS",
   "exchange": "SSE",
   "note_es": "SAIC Motor cotiza en Shanghái (600104); el ticker 'SAIC' es de Science Applications International Corp (Nasdaq), otra empresa.",
   "note_en": "SAIC Motor trades in Shanghai (600104); 'SAIC' is the Nasdaq ticker of Science Applications International Corp, an unrelated company.",
   "source_url": "https://en.wikipedia.org/wiki/SAIC_Motor",
   "confidence": "high"
  },
  "SKMaterials": {
   "status": "merged",
   "parent": "SK Inc.",
   "parent_ticker": "034730.KS",
   "event_date": "2021-12-01",
   "note_es": "Fusionada en SK Inc. en dic-2021; dejó de cotizar.",
   "note_en": "Merged into SK Inc. in Dec 2021; delisted.",
   "source_url": "https://eng.sk.com/",
   "confidence": "medium"
  },
  "SPGlobalRatings": {
   "status": "subsidiary",
   "parent": "S&P Global Inc.",
   "parent_ticker": "SPGI",
   "note_es": "S&P Global Ratings es una división de S&P Global (SPGI); no cotiza por separado.",
   "note_en": "S&P Global Ratings is a division of S&P Global (SPGI); it is not separately listed.",
   "source_url": "https://investor.spglobal.com/",
   "confidence": "high"
  },
  "SSAB": {
   "status": "public",
   "ticker": "SSAB-B.ST",
   "exchange": "Nasdaq Stockholm",
   "note_es": "Cotiza en Nasdaq Estocolmo (SSAB A/B) y Helsinki.",
   "note_en": "Listed on Nasdaq Stockholm (SSAB A/B) and Helsinki.",
   "source_url": "https://www.ssab.com/en/company/investors",
   "confidence": "high"
  },
  "STT_GDC": {
   "status": "acquired",
   "parent": "KKR / Singtel",
   "parent_ticker": "KKR",
   "event_date": "2026-09",
   "note_es": "KKR (75%) y Singtel (25%) completaron la compra total en sep-2026.",
   "note_en": "KKR (75%) and Singtel (25%) completed the full takeover in Sep-2026.",
   "source_url": "https://technode.global/2026/09/03/kkr-singtel-consortium-completes-takeover-of-singapores-stt-gdc-at-10-9b/",
   "confidence": "high"
  },
  "SaudiAramco": {
   "status": "public",
   "ticker": "2222.SR",
   "exchange": "Tadawul",
   "listed_since": "2019-12-11",
   "note_es": "Cotiza en Tadawul (2222) desde dic-2019; el Estado saudí es mayoritario.",
   "note_en": "Listed on Tadawul (2222) since Dec 2019; Saudi State is majority owner.",
   "source_url": "https://www.aramco.com/en/investors",
   "confidence": "high"
  },
  "Shinko_Electric": {
   "status": "acquired",
   "parent": "JIC Capital consortium (with DNP and Mitsui Chemicals)",
   "event_date": "2025",
   "note_es": "Sacada de bolsa por un consorcio liderado por JIC Capital (compra a Fujitsu) en 2025; ya no cotiza en Tokio.",
   "note_en": "Taken private by a JIC Capital-led consortium (buying out Fujitsu) in 2025; no longer listed in Tokyo.",
   "source_url": "https://en.wikipedia.org/wiki/Shinko_Electric_Industries",
   "confidence": "medium"
  },
  "Sinopec": {
   "status": "public",
   "ticker": "0386.HK",
   "exchange": "HKEX",
   "note_es": "Símbolo mal formado: 600028 es el código A-share de Shanghái, no de Hong Kong; la acción H de Sinopec es 0386.HK (A-share: 600028.SS).",
   "note_en": "Malformed symbol: 600028 is the Shanghai A-share code, not a Hong Kong code; Sinopec's H-share is 0386.HK (A-share: 600028.SS).",
   "source_url": "https://www.hkex.com.hk/Market-Data/Securities-Prices/Equities/Equities-Quote?sym=386&sc_lang=en",
   "confidence": "high"
  },
  "SoftBank": {
   "status": "public",
   "ticker": "9984.T",
   "exchange": "Tokyo Stock Exchange",
   "note_es": "Cotiza en la Bolsa de Tokio (9984); siempre fue pública.",
   "note_en": "Listed on the Tokyo Stock Exchange (9984); it has always been public.",
   "source_url": "https://finance.yahoo.com/quote/9984.T/",
   "confidence": "high"
  },
  "SpaceX": {
   "status": "public",
   "ticker": "SPCX",
   "exchange": "Nasdaq",
   "listed_since": "2026-06-12",
   "note_es": "Salió a bolsa en Nasdaq (SPCX) el 12-jun-2026 a $135 por acción.",
   "note_en": "IPO'd on Nasdaq (SPCX) on 12-Jun-2026 at $135 per share.",
   "source_url": "https://www.nasdaq.com/newsroom/spacex-ipo-rocket-company-launches-historic-ipo",
   "confidence": "high"
  },
  "Switch": {
   "status": "acquired",
   "parent": "DigitalBridge-led consortium (with IFM Investors)",
   "event_date": "2022-12-06",
   "note_es": "Comprada por un consorcio liderado por DigitalBridge e IFM en dic-2022; es privada (DBRG no es su cotización).",
   "note_en": "Taken private by a DigitalBridge/IFM-led consortium in Dec 2022; DBRG is not its quote.",
   "source_url": "https://en.wikipedia.org/wiki/Switch,_Inc.",
   "confidence": "high"
  },
  "Sycamore": {
   "status": "defunct",
   "event_date": "2013-03",
   "note_es": "Vendió su negocio a Marlin Equity en 2013, salió de Nasdaq y se disolvió; ya no existe como cotizada.",
   "note_en": "Sold its business to Marlin Equity in 2013, delisted from Nasdaq and dissolved; no longer a listed company.",
   "source_url": "https://en.wikipedia.org/wiki/Sycamore_Networks",
   "confidence": "medium"
  },
  "Telehouse": {
   "status": "subsidiary",
   "parent": "KDDI Corporation",
   "parent_ticker": "9433.T",
   "note_es": "Filial 100% de KDDI; no cotiza por separado.",
   "note_en": "Wholly owned subsidiary of KDDI; not separately listed.",
   "source_url": "https://en.wikipedia.org/wiki/Telehouse",
   "confidence": "high"
  },
  "Teraco": {
   "status": "subsidiary",
   "parent": "Digital Realty",
   "parent_ticker": "DLR",
   "note_es": "Controlada por Digital Realty (~61%, sube a 77% tras acuerdo de jun-2026).",
   "note_en": "Controlled by Digital Realty (~61%, rising to 77% under a Jun-2026 deal).",
   "source_url": "https://investor.digitalrealty.com/news-releases/news-release-details/digital-realty-announces-transactions-drive-continued-platform",
   "confidence": "high"
  },
  "TianqiLithium": {
   "status": "public",
   "ticker": "9696.HK",
   "exchange": "HKEX",
   "note_es": "Símbolo mal formado: 002466 es el código A-share de Shenzhen, no de Hong Kong; la acción H de Tianqi Lithium es 9696.HK (A-share: 002466.SZ).",
   "note_en": "Malformed symbol: 002466 is the Shenzhen A-share code, not a Hong Kong code; Tianqi Lithium's H-share is 9696.HK (A-share: 002466.SZ).",
   "source_url": "https://www.hkex.com.hk/Market-Data/Securities-Prices/Equities/Equities-Quote?sym=9696&sc_lang=en",
   "confidence": "high"
  },
  "TokyoOhka": {
   "status": "public",
   "ticker": "4186.T",
   "exchange": "Tokyo Stock Exchange",
   "note_es": "Cotiza en la Bolsa de Tokio (4186); siempre fue pública.",
   "note_en": "Listed on the Tokyo Stock Exchange (4186); it has always been public.",
   "source_url": "https://finance.yahoo.com/quote/4186.T/",
   "confidence": "high"
  },
  "Turner Construction": {
   "status": "subsidiary",
   "parent": "HOCHTIEF AG",
   "parent_ticker": "HOT.DE",
   "note_es": "Filial 100% de HOCHTIEF (controlada por ACS); no cotiza por separado.",
   "note_en": "Wholly owned subsidiary of HOCHTIEF (controlled by ACS); not separately listed.",
   "source_url": "https://en.wikipedia.org/wiki/Turner_Construction",
   "confidence": "high"
  },
  "ULA": {
   "status": "subsidiary",
   "parent": "Boeing / Lockheed Martin (50/50 joint venture)",
   "note_es": "Empresa conjunta privada 50/50 de Boeing y Lockheed Martin; no cotiza ('ULA' no es un ticker válido).",
   "note_en": "Private 50/50 joint venture of Boeing and Lockheed Martin; not listed ('ULA' is not a valid ticker).",
   "source_url": "https://en.wikipedia.org/wiki/United_Launch_Alliance",
   "confidence": "high"
  },
  "Unimicron": {
   "status": "public",
   "ticker": "3037.TW",
   "exchange": "TWSE",
   "note_es": "Cotiza en la Bolsa de Taiwán (3037); siempre fue pública.",
   "note_en": "Listed on the Taiwan Stock Exchange (3037); it has always been public.",
   "source_url": "https://finance.yahoo.com/quote/3037.TW/",
   "confidence": "high"
  },
  "Uniper": {
   "status": "public",
   "ticker": "UN01.DE",
   "exchange": "XETRA",
   "note_es": "Cotiza en Fráncfort (UN01), ~99% del Estado alemán, que inició su venta en may-2026.",
   "note_en": "Listed in Frankfurt (UN01), ~99% German State, which launched its sale in May 2026.",
   "source_url": "https://www.bloomberg.com/news/articles/2026-05-19/german-government-launches-privatization-of-energy-firm-uniper-mpc7nu4l",
   "confidence": "high"
  },
  "Untether_AI": {
   "status": "defunct",
   "parent": "AMD (solo equipo / team only)",
   "parent_ticker": "AMD",
   "event_date": "2025-06",
   "note_es": "Cerró en jun-2025: dejó de vender productos y su equipo de ingeniería pasó a AMD.",
   "note_en": "Shut down in Jun-2025: discontinued its products and its engineering team joined AMD.",
   "source_url": "https://www.eetimes.com/untether-ai-shuts-down-engineering-team-joins-amd/",
   "confidence": "high"
  },
  "Vedanta_Semi": {
   "status": "subsidiary",
   "parent": "Vedanta Limited",
   "parent_ticker": "VEDL.NS",
   "event_date": "2023-07-10",
   "note_es": "La JV se deshizo en jul-2023 al salir Foxconn; la entidad quedó 100% en manos de Vedanta (VEDL.NS).",
   "note_en": "The JV unraveled in Jul-2023 when Foxconn exited; the entity is now wholly owned by Vedanta (VEDL.NS).",
   "source_url": "https://thediplomat.com/2023/07/chip-maker-foxconn-exits-semiconductor-joint-venture-with-indian-mining-company-vedanta/",
   "confidence": "medium"
  },
  "WPT Industrial": {
   "status": "acquired",
   "parent": "Blackstone Real Estate Income Trust (BREIT)",
   "event_date": "2021-10",
   "note_es": "Adquirida por BREIT (Blackstone) en 2021 y deslistada.",
   "note_en": "Acquired by BREIT (Blackstone) in 2021 and delisted.",
   "source_url": "https://en.wikipedia.org/wiki/WPT_Industrial_REIT",
   "confidence": "medium"
  },
  "WanHai": {
   "status": "public",
   "ticker": "2615.TW",
   "exchange": "Taiwan Stock Exchange",
   "note_es": "Cotiza en la Bolsa de Taiwán (2615).",
   "note_en": "Listed on the Taiwan Stock Exchange (2615).",
   "source_url": "https://en.wikipedia.org/wiki/Wan_Hai_Lines",
   "confidence": "high"
  },
  "Waymo": {
   "status": "subsidiary",
   "parent": "Alphabet",
   "parent_ticker": "GOOGL",
   "note_es": "Filial de Alphabet; no cotiza por separado.",
   "note_en": "Alphabet subsidiary; not separately listed.",
   "source_url": "https://abc.xyz/investor/",
   "confidence": "high"
  },
  "Xiaomi": {
   "status": "public",
   "ticker": "1810.HK",
   "exchange": "HKEX",
   "note_es": "Cotiza en la Bolsa de Hong Kong (1810) desde 2018.",
   "note_en": "Listed on the Hong Kong Stock Exchange (1810) since 2018.",
   "source_url": "https://finance.yahoo.com/quote/1810.HK/",
   "confidence": "high"
  },
  "YOFC": {
   "status": "public",
   "ticker": "6869.HK",
   "exchange": "HKEX",
   "note_es": "Símbolo mal formado: 601869 es el código A-share de Shanghái, no de Hong Kong; la acción H de YOFC es 6869.HK (A-share: 601869.SS).",
   "note_en": "Malformed symbol: 601869 is the Shanghai A-share code, not a Hong Kong code; YOFC's H-share is 6869.HK (A-share: 601869.SS).",
   "source_url": "https://www.hkex.com.hk/Market-Data/Securities-Prices/Equities/Equities-Quote?sym=6869&sc_lang=en",
   "confidence": "high"
  },
  "YangMing": {
   "status": "public",
   "ticker": "2609.TW",
   "exchange": "Taiwan Stock Exchange",
   "note_es": "Cotiza en la Bolsa de Taiwán (2609).",
   "note_en": "Listed on the Taiwan Stock Exchange (2609).",
   "source_url": "https://en.wikipedia.org/wiki/Yang_Ming_Marine_Transport_Corporation",
   "confidence": "high"
  },
  "YondrGroup": {
   "status": "acquired",
   "parent": "DigitalBridge / La Caisse",
   "parent_ticker": "DBRG",
   "event_date": "2025-07-01",
   "note_es": "DigitalBridge y La Caisse completaron su compra el 1-jul-2025.",
   "note_en": "DigitalBridge and La Caisse completed its acquisition on 1-Jul-2025.",
   "source_url": "https://www.businesswire.com/news/home/20250701076482/en/DigitalBridge-and-La-Caisse-Complete-Acquisition-of-Yondr-Group",
   "confidence": "high"
  },
  "ZhipuAI": {
   "status": "public",
   "ticker": "2513.HK",
   "exchange": "HKEX",
   "listed_since": "2026-01-08",
   "note_es": "Salió a bolsa en Hong Kong (2513) el 8-ene-2026 a HK$116,20 por acción.",
   "note_en": "Listed in Hong Kong (2513) on 8-Jan-2026 at HK$116.20 per share.",
   "source_url": "https://www.cnbc.com/2026/01/08/china-ai-tiger-goes-ipo-zhipu-hong-kong-debut-openai-knowledge-atlas-hsi-hang-seng-listing.html",
   "confidence": "high"
  },
  "Zoox": {
   "status": "subsidiary",
   "parent": "Amazon",
   "parent_ticker": "AMZN",
   "event_date": "2020-06",
   "note_es": "Filial de Amazon desde 2020; no cotiza por separado.",
   "note_en": "Amazon subsidiary since 2020; not separately listed.",
   "source_url": "https://zoox.com/about",
   "confidence": "high"
  },
  "berkshire-grey": {
   "status": "acquired",
   "parent": "SoftBank Group",
   "parent_ticker": "9984.T",
   "event_date": "2023-07",
   "note_es": "Adquirida por SoftBank Group (9984.T) en 2023 y retirada de Nasdaq.",
   "note_en": "Acquired by SoftBank Group (9984.T) in 2023 and delisted from Nasdaq.",
   "source_url": "https://www.berkshiregrey.com/",
   "confidence": "medium"
  },
  "chindata": {
   "status": "acquired",
   "parent": "Bain Capital",
   "event_date": "2023-09",
   "note_es": "Adquirida y retirada de Nasdaq por Bain Capital en 2023; sigue privada.",
   "note_en": "Taken private and delisted from Nasdaq by Bain Capital in 2023; remains private.",
   "source_url": "https://www.chindatagroup.com/",
   "confidence": "medium"
  },
  "diligent-robotics": {
   "status": "acquired",
   "parent": "Serve Robotics",
   "parent_ticker": "SERV",
   "event_date": "2026-01-27",
   "note_es": "Adquirida por Serve Robotics (SERV) el 27-ene-2026 por ~$25,7M.",
   "note_en": "Acquired by Serve Robotics (SERV) on 27-Jan-2026 for ~$25.7M.",
   "source_url": "https://www.stocktitan.net/sec-filings/SERV/8-k-serve-robotics-inc-de-reports-material-event-1d63fae26ecc.html",
   "confidence": "high"
  },
  "enflame": {
   "status": "public",
   "ticker": "688801.SS",
   "exchange": "Shanghai Stock Exchange (STAR Market)",
   "listed_since": "2026-09-11",
   "note_es": "Salió a bolsa en el STAR Market de Shanghái (688801) el 11-sep-2026 a RMB 142,18; subió 206% el primer día.",
   "note_en": "Listed on Shanghai's STAR Market (688801) on 11-Sep-2026 at RMB 142.18; rose 206% on day one.",
   "source_url": "https://www.cnbc.com/2026/09/11/chinese-nvidia-rival-enflame-stock-market-debut-ai.html",
   "confidence": "high"
  },
  "infleqtion": {
   "status": "public",
   "ticker": "INFQ",
   "exchange": "NYSE",
   "listed_since": "2026-02-17",
   "note_es": "Salió a bolsa vía SPAC (Churchill Capital X); cotiza en NYSE como INFQ desde el 17-feb-2026.",
   "note_en": "Went public via SPAC (Churchill Capital X); trades on NYSE as INFQ since 17-Feb-2026.",
   "source_url": "https://ir.infleqtion.com/news-events/press-releases/detail/166/infleqtion-and-churchill-capital-corp-x-complete-business-combination",
   "confidence": "high"
  },
  "iqm-quantum": {
   "status": "public",
   "ticker": "IQMX",
   "exchange": "Nasdaq",
   "listed_since": "2026-07-02",
   "note_es": "Salió a bolsa vía SPAC (Real Asset Acquisition); ADS cotizan en Nasdaq como IQMX desde el 2-jul-2026.",
   "note_en": "Went public via SPAC (Real Asset Acquisition); ADSs trade on Nasdaq as IQMX since 2-Jul-2026.",
   "source_url": "https://www.nasdaq.com/press-release/iqm-quantum-computers-and-real-asset-acquisition-corp-complete-combination-trading",
   "confidence": "high"
  },
  "juniper": {
   "status": "acquired",
   "parent": "Hewlett Packard Enterprise",
   "parent_ticker": "HPE",
   "event_date": "2025-07-02",
   "note_es": "Adquirida por Hewlett Packard Enterprise (HPE) el 2-jul-2025.",
   "note_en": "Acquired by Hewlett Packard Enterprise (HPE) on 2-Jul-2025.",
   "source_url": "https://www.hpe.com/us/en/newsroom/press-release/2025/07/hpe-completes-acquisition-of-juniper-networks.html",
   "confidence": "high"
  },
  "nanoavionics": {
   "status": "subsidiary",
   "parent": "Kongsberg Gruppen",
   "parent_ticker": "KOG.OL",
   "event_date": "2022",
   "note_es": "Subsidiaria de Kongsberg (mayoría desde 2022), opera como Kongsberg NanoAvionics.",
   "note_en": "Kongsberg subsidiary (majority since 2022), operating as Kongsberg NanoAvionics.",
   "source_url": "https://payloadspace.com/kongsberg-acquires-majority-stake-in-nanoavionics/",
   "confidence": "medium"
  },
  "nexperia": {
   "status": "subsidiary",
   "parent": "Wingtech Technology",
   "parent_ticker": "600745.SS",
   "note_es": "Filial de Wingtech Technology (600745.SS), bajo disputa de control con el gobierno neerlandés desde oct-2025.",
   "note_en": "Subsidiary of Wingtech Technology (600745.SS), under a control dispute with the Dutch government since Oct-2025.",
   "source_url": "https://www.nexperia.com/about",
   "confidence": "medium"
  },
  "ntt-gdc": {
   "status": "subsidiary",
   "parent": "NTT, Inc. (vía NTT DATA Group)",
   "parent_ticker": "9432.T",
   "note_es": "NTT Global Data Centers es una unidad del grupo NTT (9432.T); no cotiza por separado.",
   "note_en": "NTT Global Data Centers is a unit of the NTT group (9432.T); it is not separately listed.",
   "source_url": "https://group.ntt/en/ir/",
   "confidence": "high"
  },
  "terran-orbital": {
   "status": "acquired",
   "parent": "Lockheed Martin",
   "parent_ticker": "LMT",
   "event_date": "2024-10-30",
   "note_es": "Adquirida por Lockheed Martin el 30-oct-2024; ya no cotiza.",
   "note_en": "Acquired by Lockheed Martin on 30-Oct-2024; no longer listed.",
   "source_url": "https://www.sec.gov/Archives/edgar/data/1835512/000095017024118608/llap-ex99_1.htm",
   "confidence": "high"
  },
  "textron-systems": {
   "status": "subsidiary",
   "parent": "Textron Inc.",
   "parent_ticker": "TXT",
   "note_es": "División de Textron Inc.; no cotiza por separado.",
   "note_en": "Business unit of Textron Inc.; not separately listed.",
   "source_url": "https://investor.textron.com/",
   "confidence": "high"
  },
  "voltage-park": {
   "status": "merged",
   "parent": "Lightning AI",
   "event_date": "2026-01-21",
   "note_es": "Se fusionó con Lightning AI el 21-ene-2026; la empresa combinada (privada) opera como Lightning AI.",
   "note_en": "Merged with Lightning AI on 21-Jan-2026; the combined (private) company operates as Lightning AI.",
   "source_url": "https://www.businesswire.com/news/home/20260121371691/en/Lightning-AI-and-Voltage-Park-Complete-Merger-to-Create-the-First-Cloud-Built-for-AI",
   "confidence": "high"
  },
  "wing-alphabet": {
   "status": "subsidiary",
   "parent": "Alphabet Inc.",
   "parent_ticker": "GOOGL",
   "note_es": "Subsidiaria de Alphabet; no cotiza por separado.",
   "note_en": "Alphabet subsidiary; not separately listed.",
   "source_url": "https://abc.xyz/investor/",
   "confidence": "high"
  },
  "xAI": {
   "status": "merged",
   "parent": "SpaceX",
   "parent_ticker": "SPCX",
   "event_date": "2026-02-02",
   "note_es": "Se fusionó con SpaceX el 2-feb-2026; la entidad combinada cotiza en Nasdaq (SPCX) desde el 12-jun-2026.",
   "note_en": "Merged into SpaceX on 2-Feb-2026; the combined company trades on Nasdaq (SPCX) since 12-Jun-2026.",
   "source_url": "https://www.npr.org/2026/06/11/nx-s1-5853199/spacex-ipo-price-elon-musk",
   "confidence": "high"
  },
  "xanadu-quantum": {
   "status": "public",
   "ticker": "XNDU",
   "exchange": "Nasdaq / TSX",
   "listed_since": "2026-03-27",
   "note_es": "Salió a bolsa vía SPAC con Crane Harbor; cotiza como XNDU en Nasdaq y TSX desde mar-2026.",
   "note_en": "Went public via SPAC with Crane Harbor; trades as XNDU on Nasdaq and TSX since Mar 2026.",
   "source_url": "https://www.sec.gov/Archives/edgar/data/2054174/000121390026032904/ea028273201ex99-1.htm",
   "confidence": "medium"
  }
 }
};
