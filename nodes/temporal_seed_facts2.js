// nodes/temporal_seed_facts2.js — Hechos temporales adicionales (Khipus AI Finance)
// Segunda tanda de hechos reales y verificados (2016–2026) de la cadena IA / semis
// / nuclear / espacio. Se anexan a window.TEMPORAL_SEED_FACTS. Todos los ids de
// 'object_type:node' están verificados contra el catálogo de nodos existente.
// Esquema idéntico al de temporal_seed_facts.js.

(function () {
  var MORE = [
    // ── Megaproyectos de infraestructura de IA ───────────────────────────────
    { id:'tf_stargate', subject:'OpenAI', predicate:'proyecto Stargate $500B (infra IA) con', object:'Oracle', object_type:'node',
      valid_from:'2025-01-21', valid_until:null, source:'deal', confidence:0.9, group:'g_stargate',
      meta:{ headline:'Stargate: hasta $500B en datacenters de IA (OpenAI/Oracle/SoftBank)', impact:9 } },
    { id:'tf_stargate_sb', subject:'SoftBank', predicate:'lidera la financiación de Stargate con', object:'OpenAI', object_type:'node',
      valid_from:'2025-01-21', valid_until:null, source:'deal', confidence:0.85, group:'g_stargate',
      meta:{ headline:'SoftBank, socio financiero principal de Stargate', impact:7 } },
    { id:'tf_xai_colossus', subject:'xAI', predicate:'Colossus: 100k+ GPUs de', object:'Nvidia', object_type:'node',
      valid_from:'2024-09-01', valid_until:null, source:'hypergraph', confidence:0.9, group:'g_xai',
      meta:{ headline:'xAI enciende Colossus (Memphis): mayor supercluster de GPUs', impact:7 } },

    // ── Neoclouds de GPU ──────────────────────────────────────────────────────
    { id:'tf_nvidia_coreweave', subject:'Nvidia', predicate:'respalda y coloca GPUs en', object:'CoreWeave', object_type:'node',
      valid_from:'2023-04-01', valid_until:null, source:'link', confidence:0.9, group:'g_coreweave',
      meta:{ headline:'Nvidia ancla a CoreWeave (neocloud de GPUs)', impact:6 } },
    { id:'tf_coreweave_ipo', subject:'CoreWeave', predicate:'IPO en Nasdaq (~$23B valoración)', object:'IPO 2025', object_type:'literal',
      valid_from:'2025-03-28', valid_until:null, source:'preipo', confidence:0.95, group:'g_coreweave',
      meta:{ headline:'CoreWeave sale a bolsa: primera gran IPO de la era GPU', impact:6 } },

    // ── Capital de los grandes en los laboratorios de IA ──────────────────────
    { id:'tf_msft_openai', subject:'Microsoft', predicate:'invirtió ~$13B en', object:'OpenAI', object_type:'node',
      valid_from:'2023-01-23', valid_until:null, source:'deal', confidence:0.95, group:'g_ai_deals',
      meta:{ headline:'Microsoft: socio de nube y capital de OpenAI (~$13B)', impact:9 } },
    { id:'tf_amazon_anthropic', subject:'Amazon', predicate:'invierte $8B en', object:'Anthropic', object_type:'node',
      valid_from:'2024-11-22', valid_until:null, source:'deal', confidence:0.95, group:'g_ai_deals',
      meta:{ headline:'Amazon: $8B en Anthropic; AWS Trainium como cómputo', impact:8 } },
    { id:'tf_google_anthropic', subject:'Alphabet', predicate:'respalda con >$3B a', object:'Anthropic', object_type:'node',
      valid_from:'2025-01-01', valid_until:null, source:'deal', confidence:0.85, group:'g_ai_deals',
      meta:{ headline:'Google, coinversor de Anthropic (>$3B)', impact:6 } },
    { id:'tf_meta_scale', subject:'Meta', predicate:'invierte $14.3B (49%) en', object:'ScaleAI', object_type:'node',
      valid_from:'2025-06-12', valid_until:null, source:'deal', confidence:0.9, group:'g_ai_deals',
      meta:{ headline:'Meta toma 49% de Scale AI y ficha a su CEO', impact:7 } },

    // ── Guerra de la HBM ──────────────────────────────────────────────────────
    { id:'tf_micron_nvidia', subject:'Micron', predicate:'HBM3e calificada para', object:'Nvidia', object_type:'node',
      valid_from:'2024-02-26', valid_until:null, source:'link', confidence:0.9, group:'g_hbm',
      meta:{ headline:'Micron entra al HBM3e de Nvidia y rompe el duopolio', impact:7 } },
    { id:'tf_samsung_nvidia', subject:'Samsung', predicate:'HBM3e en calificación para', object:'Nvidia', object_type:'node',
      valid_from:'2024-07-01', valid_until:null, source:'link', confidence:0.8, group:'g_hbm',
      meta:{ headline:'Samsung batalla por calificar su HBM3e en Nvidia', impact:6 } },

    // ── Silicio a medida (custom ASICs) ───────────────────────────────────────
    { id:'tf_broadcom_google', subject:'Broadcom', predicate:'co-diseña las TPU de', object:'Alphabet', object_type:'node',
      valid_from:'2016-01-01', valid_until:null, source:'link', confidence:0.9, group:'g_custom_si',
      meta:{ headline:'Broadcom, socio de silicio de las TPU de Google', impact:6 } },
    { id:'tf_broadcom_meta', subject:'Broadcom', predicate:'ASIC de IA (MTIA) para', object:'Meta', object_type:'node',
      valid_from:'2024-01-01', valid_until:null, source:'link', confidence:0.85, group:'g_custom_si',
      meta:{ headline:'Broadcom fabrica el acelerador MTIA de Meta', impact:6 } },
    { id:'tf_marvell_amazon', subject:'Marvell', predicate:'co-diseña Trainium/Inferentia con', object:'Amazon', object_type:'node',
      valid_from:'2023-01-01', valid_until:null, source:'link', confidence:0.85, group:'g_custom_si',
      meta:{ headline:'Marvell, socio de silicio de AWS (Trainium)', impact:6 } },

    // ── Nuclear para datacenters ──────────────────────────────────────────────
    { id:'tf_constellation_msft', subject:'Constellation', predicate:'reabre Three Mile Island (835MW) para', object:'Microsoft', object_type:'node',
      valid_from:'2024-09-20', valid_until:null, source:'link', confidence:0.9, group:'g_nuclear_ppa',
      meta:{ headline:'Constellation reactiva TMI para los datacenters de Microsoft', impact:7 } },
    { id:'tf_google_kairos', subject:'Alphabet', predicate:'PPA de reactores SMR con', object:'KairosPower', object_type:'node',
      valid_from:'2024-10-14', valid_until:null, source:'link', confidence:0.85, group:'g_nuclear_ppa',
      meta:{ headline:'Google compra energía a los SMR de Kairos Power', impact:6 } },

    // ── Infraestructura física (cooling / energía) ────────────────────────────
    { id:'tf_vertiv_nvidia', subject:'Vertiv', predicate:'refrigeración líquida para racks de', object:'Nvidia', object_type:'node',
      valid_from:'2024-01-01', valid_until:null, source:'link', confidence:0.85, group:'g_infra',
      meta:{ headline:'Vertiv, ganador de la ola de cooling para GB200', impact:6 } },

    // ── Shocks y riesgos ──────────────────────────────────────────────────────
    { id:'tf_deepseek_r1', subject:'DeepSeek', predicate:'R1 hunde a Nvidia −$589B en un día', object:'shock R1', object_type:'literal',
      valid_from:'2025-01-27', valid_until:null, source:'hypergraph', confidence:0.95, group:'g_shock',
      meta:{ headline:'DeepSeek R1: la mayor caída diaria en la historia de Nvidia', impact:8 } },
    { id:'tf_intel_foundry', subject:'Intel', predicate:'pérdidas en Foundry · 18A crítico', object:'reestructuración', object_type:'literal',
      valid_from:'2024-09-01', valid_until:null, source:'node_meta', confidence:0.85, group:'g_risk',
      meta:{ headline:'Intel Foundry sangra; el nodo 18A es su última bala', impact:7 } },
    { id:'tf_wolfspeed_ch11', subject:'Wolfspeed', predicate:'Chapter 11 · sobreoferta de SiC', object:'reestructuración', object_type:'literal',
      valid_from:'2025-06-30', valid_until:null, source:'node_meta', confidence:0.85, group:'g_risk',
      meta:{ headline:'Wolfspeed colapsa por exceso de capacidad en carburo de silicio', impact:6 } },

    // ── Fabs y nodos ──────────────────────────────────────────────────────────
    { id:'tf_arm_ipo', subject:'ARM', predicate:'IPO en Nasdaq (SoftBank ~90%)', object:'$54B val.', object_type:'literal',
      valid_from:'2023-09-14', valid_until:null, source:'preipo', confidence:0.95, group:'g_corp',
      meta:{ headline:'Arm regresa a bolsa; SoftBank retiene el control', impact:6 } },
    { id:'tf_tsmc_az', subject:'TSMC', predicate:'produce 4nm en Arizona (Fab 21)', object:'Fab 21 AZ', object_type:'literal',
      valid_from:'2024-12-01', valid_until:null, source:'node_meta', confidence:0.9, group:'g_fabs',
      meta:{ headline:'TSMC arranca producción avanzada en EE.UU. (Arizona)', impact:6 } },
    { id:'tf_tsmc_n2', subject:'TSMC', predicate:'N2 (2nm, nanosheets) en producción', object:'N2', object_type:'literal',
      valid_from:'2025-10-01', valid_until:null, source:'node_meta', confidence:0.85, group:'g_fabs',
      meta:{ headline:'TSMC inicia el nodo 2nm (transistores GAA)', impact:7 } },
  ];

  window.TEMPORAL_SEED_FACTS = (window.TEMPORAL_SEED_FACTS || []).concat(MORE);
})();
