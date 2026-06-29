// nodes/preipo_intel.js — Inteligencia de empresas privadas / pre-IPO (Khipu Finance)
// Datos de financiación, inversores, timeline a IPO e hitos para el panel de
// empresa privada (Fase 4). Indexado por id de nodo. Los nodos sin entrada aquí
// muestran el panel con la info disponible en el propio nodo (graceful).
// `investors` que coincidan con un id de nodo se enlazan al grafo.

window.PREIPO_INTEL = {
  SpaceX: {
    total_raised:"~$10B+", valuation:"$400B (2025)", ipo_timeline:"Starlink/combinada ~2026",
    investors:["Alphabet","Fidelity","a16z","Founders Fund"],
    rounds:[{round:"Tender",amount:"$1.25B",date:"2025",lead:"Insiders"},
            {round:"Serie N",amount:"$750M",date:"2023",lead:"a16z"}],
    milestones:[{date:"2025",event:"Starlink supera $11.4B de ingresos"},
                {date:"2025",event:"Starship hacia vuelos orbitales de rutina"}],
  },
  xAI: {
    total_raised:"~$22B+", valuation:"~$2T combinada con SpaceX (objetivo)", ipo_timeline:"finales 2026 (combinada)",
    investors:["Nvidia","Fidelity","a16z","Valor Equity"],
    rounds:[{round:"Serie C",amount:"$6B",date:"2024",lead:"Varios"},
            {round:"Debt+Equity",amount:"$10B",date:"2025",lead:"Morgan Stanley"}],
    milestones:[{date:"2025",event:"Colossus 2 en expansión (Memphis)"},
                {date:"2025",event:"Grok integrado en X"}],
  },
  OpenAI: {
    total_raised:"~$60B+", valuation:"$500B (2025)", ipo_timeline:"sin fecha; reestructuración PBC",
    investors:["Microsoft","SoftBank","Thrive","Nvidia"],
    rounds:[{round:"Tender",amount:"$40B",date:"2025",lead:"SoftBank"},
            {round:"Primary",amount:"$6.6B",date:"2024",lead:"Thrive"}],
    milestones:[{date:"2025",event:"Stargate: data centers con Oracle y SoftBank"},
                {date:"2025",event:"ChatGPT supera 800M de usuarios semanales"}],
  },
  Anthropic: {
    total_raised:"~$33B+", valuation:"$350B (2025)", ipo_timeline:"sin fecha",
    investors:["Amazon","Alphabet","Lightspeed","ICONIQ"],
    rounds:[{round:"Serie F",amount:"$13B",date:"2025",lead:"ICONIQ"},
            {round:"Serie E",amount:"$3.5B",date:"2025",lead:"Lightspeed"}],
    milestones:[{date:"2025",event:"Claude líder en código y agentes empresariales"},
                {date:"2025",event:"Amazon amplía a $8B y Trainium"}],
  },
  Figure: {
    total_raised:"~$1.7B", valuation:"$39B (2025)", ipo_timeline:"pre-IPO, sin S-1",
    investors:["Microsoft","Nvidia","OpenAI","Bezos"],
    rounds:[{round:"Serie C",amount:"$1B+",date:"2025",lead:"Parkway"}],
    milestones:[{date:"2026",event:"BotQ: un Figure 03 cada 90 minutos"},
                {date:"2025",event:"Pilotos con BMW y UPS"}],
  },
  OneX: {
    total_raised:"~$1B", valuation:"$10B (objetivo)", ipo_timeline:"pre-IPO temprano",
    investors:["OpenAI","EQT","Tiger Global"],
    rounds:[{round:"Serie B",amount:"$100M",date:"2024",lead:"EQT"}],
    milestones:[{date:"2025",event:"Preórdenes de NEO abiertas (~$20k)"},
                {date:"2026",event:"Primeras entregas en hogares de EE.UU."}],
  },
  Apptronik: {
    total_raised:"~$870M", valuation:"$5.5B", ipo_timeline:"pre-IPO",
    investors:["Alphabet","Mercedes-Benz","B Capital"],
    rounds:[{round:"Serie A ext.",amount:"$520M",date:"2026",lead:"Google + QIA"}],
    milestones:[{date:"2026",event:"Pilotos Apollo con Google, Mercedes, GXO"}],
  },
  PsiQuantum: {
    total_raised:"~$1.6B", valuation:"~$7B", ipo_timeline:"pre-IPO",
    investors:["Nvidia","BlackRock","Temasek"],
    rounds:[{round:"Serie E",amount:"$1B+",date:"2025",lead:"BlackRock"}],
    milestones:[{date:"2025",event:"Megaproyectos estatales en Brisbane y Chicago"}],
  },
  CommonwealthFusion: {
    total_raised:"~$6.85B", valuation:"~$8B", ipo_timeline:"pre-IPO",
    investors:["Alphabet","Nvidia","Bill Gates","Temasek"],
    rounds:[{round:"Serie B2",amount:"$863M",date:"2025",lead:"Varios"}],
    milestones:[{date:"2026",event:"SPARC ~75% completo; magnetos HTS validados"}],
  },
  Helion: {
    total_raised:"~$1.5B", valuation:"$15.5B", ipo_timeline:"pre-IPO",
    investors:["Microsoft","Sam Altman","SoftBank"],
    rounds:[{round:"Serie G",amount:"$465M",date:"2026",lead:"Varios"}],
    milestones:[{date:"2026",event:"Polaris alcanza plasma a 150M°C"},
                {date:"2025",event:"Licencias regulatorias comerciales (WA)"}],
  },
  TerraPower: {
    total_raised:"~$3.4B", valuation:"privada", ipo_timeline:"pre-IPO",
    investors:["Bill Gates","Nvidia","HD Hyundai"],
    rounds:[{round:"Serie E",amount:"$650M",date:"2025",lead:"Gates + Nvidia"}],
    milestones:[{date:"2026",event:"Natrium en obra en Kemmerer (Wyoming)"},
                {date:"2025",event:"8 plantas comprometidas con Meta"}],
  },
  SierraSpace: {
    total_raised:"~$1.7B", valuation:"~$5B", ipo_timeline:"pre-IPO",
    investors:["General Atlantic","Coatue","BlackRock"],
    rounds:[{round:"Serie B",amount:"$290M",date:"2024",lead:"Varios"}],
    milestones:[{date:"2026",event:"Dream Chaser hacia su primer vuelo a la ISS"}],
  },
  AxiomSpace: {
    total_raised:"~$500M", valuation:"privada", ipo_timeline:"pre-IPO",
    investors:["Aljazira","Boryung","C5 Capital"],
    rounds:[{round:"Serie C",amount:"$350M",date:"2023",lead:"Aljazira + Boryung"}],
    milestones:[{date:"2027",event:"Primer módulo Axiom acoplado a la ISS (objetivo)"}],
  },
  Quantinuum: {
    total_raised:"~$925M", valuation:"~$10B (2025)", ipo_timeline:"pre-IPO",
    investors:["Honeywell","Nvidia","JPMorgan","QIA"],
    rounds:[{round:"Equity",amount:"$600M",date:"2025",lead:"QIA"}],
    milestones:[{date:"2025",event:"Helios: récord de fidelidad de qubit"}],
  },
};
