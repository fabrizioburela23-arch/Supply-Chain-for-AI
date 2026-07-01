// nodes/temporal_seed_facts.js — Hechos temporales curados (Khipus AI Finance)
// Grafo de Conocimiento Temporal: cada hecho tiene ventana de validez
// (valid_from → valid_until; null = vigente hoy). Datos reales de la cadena de
// suministro de semis / IA / espacio / nuclear, con fechas reales.
// object_type: 'node' (arista entre entidades) | 'literal' (atributo del sujeto).

window.TEMPORAL_SEED_FACTS = [
  // ── Controles de exportación / geopolítica ────────────────────────────────
  { id:'tf_huawei_entitylist', subject:'Huawei', predicate:'sancionada · US Entity List', object:'Entity List', object_type:'literal',
    valid_from:'2019-05-16', valid_until:null, source:'hypergraph', confidence:1.0, group:'g_huawei_2019',
    meta:{ headline:'Huawei añadida a la Entity List de EE.UU.', impact:9 } },
  { id:'tf_qualcomm_huawei_loss', subject:'Qualcomm', predicate:'perdió ingresos de', object:'Huawei', object_type:'node',
    valid_from:'2019-05-16', valid_until:'2021-06-30', source:'hypergraph', confidence:0.9, group:'g_huawei_2019',
    meta:{ headline:'Qualcomm pierde ~$8B en 2 años por el veto a Huawei', impact:7 } },
  { id:'tf_asml_euv_ban', subject:'ASML', predicate:'no puede exportar EUV a', object:'China', object_type:'literal',
    valid_from:'2019-01-01', valid_until:null, source:'node_meta', confidence:1.0, group:'g_export_controls',
    meta:{ headline:'ASML no puede enviar litografía EUV a China', impact:8 } },
  { id:'tf_asml_duv_restrict', subject:'ASML', predicate:'DUV restringido a', object:'China', object_type:'literal',
    valid_from:'2024-01-01', valid_until:null, source:'node_meta', confidence:0.95, group:'g_export_controls',
    meta:{ headline:'ASML: DUV avanzado también restringido a China', impact:6 } },
  { id:'tf_nvidia_a800_ban', subject:'Nvidia', predicate:'A800/H800 prohibidos a', object:'China', object_type:'literal',
    valid_from:'2023-10-17', valid_until:null, source:'hypergraph', confidence:1.0, group:'g_nvidia_china',
    meta:{ headline:'BIS prohíbe A800/H800 a China', impact:7 } },
  { id:'tf_nvidia_h20_restrict', subject:'Nvidia', predicate:'H20 restringido a', object:'China', object_type:'literal',
    valid_from:'2024-04-01', valid_until:null, source:'hypergraph', confidence:0.95, group:'g_nvidia_china',
    meta:{ headline:'H20 (recorte) también restringido', impact:6 } },
  { id:'tf_smic_7nm', subject:'SMIC', predicate:'yield 7nm por debajo de 40% vs TSMC 90%', object:'rezago técnico', object_type:'literal',
    valid_from:'2024-01-01', valid_until:null, source:'node_meta', confidence:0.8, group:'g_export_controls',
    meta:{ headline:'SMIC 1-2 generaciones atrás sin EUV', impact:5 } },

  // ── Cadena de suministro (relaciones vigentes) ────────────────────────────
  { id:'tf_tsmc_supplies_nvidia', subject:'TSMC', predicate:'fabrica GPUs para', object:'Nvidia', object_type:'node',
    valid_from:'2020-01-01', valid_until:null, source:'link', confidence:0.98, group:'g_supply_core',
    meta:{ headline:'TSMC fabrica los Blackwell/Rubin de Nvidia', impact:9 } },
  { id:'tf_skhynix_supplies_nvidia', subject:'SKHynix', predicate:'HBM3e para', object:'Nvidia', object_type:'node',
    valid_from:'2023-01-01', valid_until:null, source:'link', confidence:0.95, group:'g_supply_core',
    meta:{ headline:'SK Hynix, único proveedor calificado de HBM3e', impact:8 } },
  { id:'tf_asml_supplies_tsmc', subject:'ASML', predicate:'EUV High-NA para', object:'TSMC', object_type:'node',
    valid_from:'2024-01-01', valid_until:null, source:'link', confidence:0.98, group:'g_supply_core',
    meta:{ headline:'High-NA EXE:5200 ya en TSMC', impact:8 } },
  { id:'tf_foxconn_assembles_nvidia', subject:'Foxconn', predicate:'ensambla racks GB200 para', object:'Nvidia', object_type:'node',
    valid_from:'2024-06-01', valid_until:null, source:'link', confidence:0.9, group:'g_supply_core',
    meta:{ headline:'Foxconn arma los NVL72 (planta Houston)', impact:6 } },

  // ── HBM / memoria ─────────────────────────────────────────────────────────
  { id:'tf_hbm_shortage', subject:'SKHynix', predicate:'HBM agotada (lista de espera 12m)', object:'escasez HBM', object_type:'literal',
    valid_from:'2023-06-01', valid_until:null, source:'hypergraph', confidence:0.9, group:'g_hbm',
    meta:{ headline:'Superciclo HBM: capacidad vendida por adelantado', impact:7 } },
  { id:'tf_covid_shortage', subject:'TSMC', predicate:'escasez global de chips', object:'COVID', object_type:'literal',
    valid_from:'2020-03-01', valid_until:'2022-12-31', source:'hypergraph', confidence:1.0, group:'g_covid',
    meta:{ headline:'Escasez COVID: 2-3 años de lead time (EXPIRADO)', impact:8 } },

  // ── Inversiones / acuerdos ────────────────────────────────────────────────
  { id:'tf_nvidia_invests_intel', subject:'Nvidia', predicate:'invierte $5B en', object:'Intel', object_type:'node',
    valid_from:'2025-09-01', valid_until:null, source:'preipo', confidence:0.9, group:'g_deals_2025',
    meta:{ headline:'Nvidia toma participación de $5B en Intel', impact:6 } },
  { id:'tf_amd_openai_6gw', subject:'AMD', predicate:'acuerdo 6GW Instinct con', object:'OpenAI', object_type:'node',
    valid_from:'2025-01-01', valid_until:null, source:'preipo', confidence:0.9, group:'g_deals_2025',
    meta:{ headline:'AMD: 6 GW de GPUs Instinct para OpenAI (+warrants)', impact:7 } },
  { id:'tf_openai_raised_40b', subject:'OpenAI', predicate:'levantó $40B (SoftBank)', object:'$40B', object_type:'literal',
    valid_from:'2025-03-01', valid_until:null, source:'preipo', confidence:0.95, group:'g_ai_funding',
    meta:{ headline:'OpenAI cierra $40B a $500B de valoración', impact:8 } },
  { id:'tf_anthropic_raised', subject:'Anthropic', predicate:'levantó $13B (Serie F)', object:'$13B', object_type:'literal',
    valid_from:'2025-01-01', valid_until:null, source:'preipo', confidence:0.9, group:'g_ai_funding',
    meta:{ headline:'Anthropic a $350B; Amazon amplía', impact:7 } },

  // ── Nuclear / energía IA ──────────────────────────────────────────────────
  { id:'tf_oklo_meta_ppa', subject:'Oklo', predicate:'PPA 1.2 GW con', object:'Meta', object_type:'node',
    valid_from:'2025-06-01', valid_until:null, source:'link', confidence:0.85, group:'g_nuclear_ppa',
    meta:{ headline:'Oklo abastecerá 1.2 GW a Meta (Ohio)', impact:6 } },
  { id:'tf_helion_microsoft_ppa', subject:'Helion', predicate:'PPA fusión 50 MW con', object:'Microsoft', object_type:'node',
    valid_from:'2023-05-01', valid_until:null, source:'link', confidence:0.8, group:'g_nuclear_ppa',
    meta:{ headline:'Helion: primer PPA comercial de fusión (Microsoft 2028)', impact:6 } },
  { id:'tf_xenergy_amazon', subject:'Xenergy', predicate:'PPA 5+ GW con', object:'Amazon', object_type:'node',
    valid_from:'2024-10-01', valid_until:null, source:'link', confidence:0.85, group:'g_nuclear_ppa',
    meta:{ headline:'X-energy: 5+ GW para Amazon (SMR Xe-100)', impact:6 } },

  // ── Espacio ───────────────────────────────────────────────────────────────
  { id:'tf_starlink_revenue', subject:'SpaceX', predicate:'Starlink supera $11.4B ingresos', object:'$11.4B', object_type:'literal',
    valid_from:'2025-01-01', valid_until:null, source:'hypergraph', confidence:0.9, group:'g_space',
    meta:{ headline:'Starlink es el motor financiero de SpaceX', impact:7 } },
  { id:'tf_rocketlab_supplies_planet', subject:'RocketLab', predicate:'componentes para', object:'PlanetLabs', object_type:'node',
    valid_from:'2022-01-01', valid_until:null, source:'link', confidence:0.8, group:'g_space',
    meta:{ headline:'Rocket Lab fabrica componentes para Planet Labs', impact:4 } },

  // ── Riesgo corporativo ────────────────────────────────────────────────────
  { id:'tf_smci_doj', subject:'SuperMicro', predicate:'indictment del DOJ · ⚠ excluida', object:'riesgo legal', object_type:'literal',
    valid_from:'2026-03-01', valid_until:null, source:'node_meta', confidence:0.9, group:'g_risk',
    meta:{ headline:'SMCI: indictment DOJ → fuga de clientes a Dell/HPE', impact:6 } },
  { id:'tf_sandisk_spinoff', subject:'SanDisk', predicate:'IPO / separada de', object:'Western_Digital', object_type:'node',
    valid_from:'2025-05-01', valid_until:null, source:'preipo', confidence:0.9, group:'g_corp',
    meta:{ headline:'SanDisk se independiza (NAND pure-play)', impact:5 } },
];
