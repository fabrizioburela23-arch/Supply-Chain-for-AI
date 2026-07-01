// nodes/ontology_facts.js — Hechos tipados de la ontología (Khipus AI Finance)
// Relaciones reales empresa↔objeto y objeto↔objeto, con tipo de relación (rel)
// y ventana temporal. Se anexan a TEMPORAL_SEED_FACTS. Los ids de empresa están
// verificados contra el catálogo; los ONT_* vienen de ontology.js.

(function () {
  var F = [
    // ── Litografía ────────────────────────────────────────────────────────────
    { id:'ont_asml_euv',    subject:'ASML', predicate:'fabrica', object:'ONT_EUV', rel:'fabrica', valid_from:'2010-01-01', impact:9, hl:'ASML: único fabricante de litografía EUV del mundo' },
    { id:'ont_asml_highna', subject:'ASML', predicate:'fabrica', object:'ONT_HighNA', rel:'fabrica', valid_from:'2024-01-01', impact:8, hl:'ASML lanza EUV High-NA (EXE:5200)' },
    { id:'ont_asml_duv',    subject:'ASML', predicate:'fabrica', object:'ONT_DUV', rel:'fabrica', valid_from:'2001-01-01', impact:6, hl:'ASML también domina la litografía DUV' },
    { id:'ont_tsmc_euv',    subject:'TSMC', predicate:'usa', object:'ONT_EUV', rel:'usa', valid_from:'2019-01-01', impact:8, hl:'TSMC fabrica sus nodos avanzados con EUV' },
    { id:'ont_tsmc_highna', subject:'TSMC', predicate:'usa', object:'ONT_HighNA', rel:'usa', valid_from:'2024-01-01', impact:7, hl:'TSMC adopta High-NA para <2nm' },
    { id:'ont_samsung_euv', subject:'Samsung', predicate:'usa', object:'ONT_EUV', rel:'usa', valid_from:'2020-01-01', impact:6, hl:'Samsung Foundry usa EUV' },
    { id:'ont_intel_highna', subject:'Intel', predicate:'usa', object:'ONT_HighNA', rel:'usa', valid_from:'2024-01-01', impact:6, hl:'Intel, primer cliente de High-NA (18A/14A)' },

    // ── Empaquetado / memoria / cómputo ───────────────────────────────────────
    { id:'ont_tsmc_cowos',  subject:'TSMC', predicate:'fabrica', object:'ONT_CoWoS', rel:'fabrica', valid_from:'2016-01-01', impact:8, hl:'CoWoS: el empaquetado que limita la oferta de GPUs' },
    { id:'ont_nv_cowos',    subject:'Nvidia', predicate:'depende de', object:'ONT_CoWoS', rel:'depende', valid_from:'2020-01-01', impact:8, hl:'Nvidia depende del CoWoS de TSMC' },
    { id:'ont_nv_hbm3e',    subject:'Nvidia', predicate:'usa', object:'ONT_HBM3e', rel:'usa', valid_from:'2023-01-01', impact:8, hl:'Blackwell integra HBM3e' },
    { id:'ont_nv_cuda',     subject:'Nvidia', predicate:'controla', object:'ONT_CUDA', rel:'controla', valid_from:'2007-01-01', impact:9, hl:'CUDA: el foso de software de Nvidia' },
    { id:'ont_skhynix_hbm', subject:'SKHynix', predicate:'fabrica', object:'ONT_HBM3e', rel:'fabrica', valid_from:'2023-01-01', impact:8, hl:'SK Hynix, líder en HBM3e' },
    { id:'ont_micron_hbm',  subject:'Micron', predicate:'fabrica', object:'ONT_HBM3e', rel:'fabrica', valid_from:'2024-02-26', impact:7, hl:'Micron entra al HBM3e' },
    { id:'ont_samsung_hbm', subject:'Samsung', predicate:'fabrica', object:'ONT_HBM3e', rel:'fabrica', valid_from:'2024-07-01', impact:6, hl:'Samsung pelea por calificar su HBM3e' },
    { id:'ont_nv_blackwell', subject:'Nvidia', predicate:'fabrica', object:'ONT_Blackwell', rel:'fabrica', valid_from:'2024-03-01', impact:9, hl:'Nvidia lanza la arquitectura Blackwell' },
    { id:'ont_tsmc_blackwell', subject:'TSMC', predicate:'fabrica', object:'ONT_Blackwell', rel:'fabrica', valid_from:'2024-06-01', impact:8, hl:'TSMC produce los chips Blackwell' },
    { id:'ont_bcom_tpu',    subject:'Broadcom', predicate:'fabrica', object:'ONT_TPU', rel:'fabrica', valid_from:'2016-01-01', impact:7, hl:'Broadcom co-diseña las TPU de Google' },
    { id:'ont_goog_tpu',    subject:'Alphabet', predicate:'usa', object:'ONT_TPU', rel:'usa', valid_from:'2016-01-01', impact:7, hl:'Google entrena con sus propias TPU' },

    // ── Nodos 2nm ─────────────────────────────────────────────────────────────
    { id:'ont_tsmc_2nm',    subject:'TSMC', predicate:'domina', object:'ONT_2nm', rel:'domina', valid_from:'2025-10-01', impact:8, hl:'TSMC lidera el nodo 2nm (GAA)' },
    { id:'ont_samsung_2nm', subject:'Samsung', predicate:'usa', object:'ONT_2nm', rel:'usa', valid_from:'2022-06-01', impact:6, hl:'Samsung fue primero en GAA, pero con yields bajos' },

    // ── Materiales / obleas / fotoresinas ─────────────────────────────────────
    { id:'ont_shinetsu_wafer', subject:'ShinEtsu', predicate:'fabrica', object:'ONT_Wafer', rel:'fabrica', valid_from:'2000-01-01', impact:7, hl:'Shin-Etsu, mayor proveedor de obleas de silicio' },
    { id:'ont_jsr_resist',  subject:'JSR', predicate:'fabrica', object:'ONT_Photoresist', rel:'fabrica', valid_from:'2000-01-01', impact:6, hl:'JSR, clave en fotoresinas EUV' },
    { id:'ont_toho_resist', subject:'TokyoOhka', predicate:'fabrica', object:'ONT_Photoresist', rel:'fabrica', valid_from:'2000-01-01', impact:5, hl:'Tokyo Ohka Kogyo (TOK), fotoresinas' },
    { id:'ont_tsmc_wafer',  subject:'TSMC', predicate:'depende de', object:'ONT_Wafer', rel:'depende', valid_from:'2000-01-01', impact:6, hl:'TSMC depende de obleas japonesas' },
    { id:'ont_euv_resist',  subject:'ONT_EUV', predicate:'depende de', object:'ONT_Photoresist', rel:'depende', valid_from:'2019-01-01', impact:5, hl:'EUV necesita fotoresinas especializadas' },

    // ── SiC / GaN ─────────────────────────────────────────────────────────────
    { id:'ont_wolf_sic',    subject:'Wolfspeed', predicate:'fabrica', object:'ONT_SiC', rel:'fabrica', valid_from:'2010-01-01', impact:6, hl:'Wolfspeed, pionero en carburo de silicio' },
    { id:'ont_navitas_gan', subject:'Navitas', predicate:'fabrica', object:'ONT_GaN', rel:'fabrica', valid_from:'2018-01-01', impact:5, hl:'Navitas, líder en nitruro de galio' },

    // ── Geopolítica / políticas ───────────────────────────────────────────────
    { id:'ont_bis_entity',  subject:'ONT_BIS', predicate:'opera', object:'ONT_EntityList', rel:'controla', valid_from:'2019-01-01', impact:7, hl:'El BIS administra la Entity List' },
    { id:'ont_bis_aictrl',  subject:'ONT_BIS', predicate:'impone', object:'ONT_AIControls', rel:'controla', valid_from:'2022-10-07', impact:8, hl:'El BIS impone los controles a chips de IA' },
    { id:'ont_entity_huawei', subject:'ONT_EntityList', predicate:'sanciona', object:'Huawei', rel:'sanciona', valid_from:'2019-05-16', impact:9, hl:'La Entity List veta a Huawei' },
    { id:'ont_aictrl_nvidia', subject:'ONT_AIControls', predicate:'restringe', object:'Nvidia', rel:'restringe', valid_from:'2022-10-07', impact:8, hl:'Los controles de IA restringen las ventas de Nvidia a China' },
    { id:'ont_aictrl_china', subject:'ONT_AIControls', predicate:'restringe', object:'ONT_China', rel:'restringe', valid_from:'2022-10-07', impact:8, hl:'Objetivo: frenar la IA avanzada en China' },
    { id:'ont_duvban_china', subject:'ONT_DUVBan', predicate:'restringe', object:'ONT_China', rel:'restringe', valid_from:'2024-01-01', impact:6, hl:'Restricción de DUV avanzado a China' },
    { id:'ont_duvban_asml', subject:'ONT_DUVBan', predicate:'restringe', object:'ASML', rel:'restringe', valid_from:'2024-01-01', impact:6, hl:'ASML no puede enviar cierto DUV a China' },
    { id:'ont_nl_asml',     subject:'ONT_NL', predicate:'alberga', object:'ASML', rel:'alberga', valid_from:'1984-01-01', impact:7, hl:'ASML es neerlandesa (nodo geopolítico clave)' },

    // ── Materiales críticos y China ───────────────────────────────────────────
    { id:'ont_china_rare',  subject:'ONT_China', predicate:'controla', object:'ONT_RareEarths', rel:'controla', valid_from:'2010-01-01', impact:8, hl:'China domina ~70% de las tierras raras' },
    { id:'ont_china_ga',    subject:'ONT_China', predicate:'controla', object:'ONT_Gallium', rel:'controla', valid_from:'2010-01-01', impact:7, hl:'China controla la mayoría del galio mundial' },
    { id:'ont_china_ge',    subject:'ONT_China', predicate:'controla', object:'ONT_Germanium', rel:'controla', valid_from:'2010-01-01', impact:6, hl:'China domina el germanio' },
    { id:'ont_gageban_ga',  subject:'ONT_GaGeBan', predicate:'restringe', object:'ONT_Gallium', rel:'restringe', valid_from:'2023-08-01', impact:7, hl:'China veta exportar galio (respuesta a EE.UU.)' },
    { id:'ont_gageban_ge',  subject:'ONT_GaGeBan', predicate:'restringe', object:'ONT_Germanium', rel:'restringe', valid_from:'2023-08-01', impact:6, hl:'China veta exportar germanio' },

    // ── CHIPS Act ─────────────────────────────────────────────────────────────
    { id:'ont_chips_intel', subject:'ONT_CHIPSAct', predicate:'invierte en', object:'Intel', rel:'invierte', valid_from:'2022-08-09', impact:7, hl:'CHIPS Act: ~$8.5B para Intel' },
    { id:'ont_chips_tsmc',  subject:'ONT_CHIPSAct', predicate:'invierte en', object:'TSMC', rel:'invierte', valid_from:'2022-08-09', impact:6, hl:'CHIPS Act subsidia la fab de TSMC en Arizona' },
    { id:'ont_chips_micron', subject:'ONT_CHIPSAct', predicate:'invierte en', object:'Micron', rel:'invierte', valid_from:'2022-08-09', impact:6, hl:'CHIPS Act apoya a Micron (memoria en EE.UU.)' },

    // ── Países que albergan piezas críticas ───────────────────────────────────
    { id:'ont_tw_tsmc',     subject:'ONT_Taiwan', predicate:'alberga', object:'TSMC', rel:'alberga', valid_from:'1987-01-01', impact:10, hl:'Taiwán concentra >90% de los chips avanzados (TSMC)' },
    { id:'ont_kr_skhynix',  subject:'ONT_Korea', predicate:'alberga', object:'SKHynix', rel:'alberga', valid_from:'1983-01-01', impact:7, hl:'Corea alberga a SK Hynix' },
    { id:'ont_kr_samsung',  subject:'ONT_Korea', predicate:'alberga', object:'Samsung', rel:'alberga', valid_from:'1969-01-01', impact:7, hl:'Corea alberga a Samsung' },
    { id:'ont_jp_shinetsu', subject:'ONT_Japan', predicate:'alberga', object:'ShinEtsu', rel:'alberga', valid_from:'1926-01-01', impact:6, hl:'Japón: obleas y materiales (Shin-Etsu)' },

    // ── Energía para la IA (nuclear) ──────────────────────────────────────────
    { id:'ont_oklo_smr',    subject:'Oklo', predicate:'fabrica', object:'ONT_SMR', rel:'fabrica', valid_from:'2024-01-01', impact:6, hl:'Oklo desarrolla micro-reactores SMR' },
    { id:'ont_kairos_smr',  subject:'KairosPower', predicate:'fabrica', object:'ONT_SMR', rel:'fabrica', valid_from:'2024-01-01', impact:6, hl:'Kairos Power, SMR de sales fundidas' },
    { id:'ont_nuscale_smr', subject:'NuScale', predicate:'fabrica', object:'ONT_SMR', rel:'fabrica', valid_from:'2023-01-01', impact:5, hl:'NuScale, SMR aprobado por la NRC' },
    { id:'ont_helion_fus',  subject:'Helion', predicate:'fabrica', object:'ONT_Fusion', rel:'fabrica', valid_from:'2023-01-01', impact:6, hl:'Helion, fusión para Microsoft (2028)' },
    { id:'ont_cfs_fus',     subject:'CommonwealthFusion', predicate:'fabrica', object:'ONT_Fusion', rel:'fabrica', valid_from:'2021-01-01', impact:6, hl:'Commonwealth Fusion (SPARC/MIT)' },
    { id:'ont_smr_grid',    subject:'ONT_SMR', predicate:'da energía a', object:'ONT_Grid', rel:'energiza', valid_from:'2024-01-01', impact:6, hl:'Los SMR alimentarán datacenters de IA' },
    { id:'ont_grid_msft',   subject:'ONT_Grid', predicate:'da energía a', object:'Microsoft', rel:'energiza', valid_from:'2024-01-01', impact:6, hl:'La energía es el nuevo cuello de botella de la IA' },
    { id:'ont_grid_amzn',   subject:'ONT_Grid', predicate:'da energía a', object:'Amazon', rel:'energiza', valid_from:'2024-01-01', impact:6, hl:'Amazon asegura energía nuclear para AWS' },

    // ── Competencia ───────────────────────────────────────────────────────────
    { id:'ont_nv_amd',      subject:'Nvidia', predicate:'compite con', object:'AMD', rel:'compite', valid_from:'2023-01-01', impact:6, hl:'Nvidia vs AMD en aceleradores de IA' },
    { id:'ont_tsmc_intel',  subject:'TSMC', predicate:'compite con', object:'Intel', rel:'compite', valid_from:'2021-01-01', impact:6, hl:'TSMC vs Intel Foundry' },
    { id:'ont_openai_anthropic', subject:'OpenAI', predicate:'compite con', object:'Anthropic', rel:'compite', valid_from:'2023-01-01', impact:6, hl:'OpenAI vs Anthropic en modelos frontera' },
  ];

  var out = F.map(function (f) {
    return {
      id: f.id, subject: f.subject, predicate: f.predicate, object: f.object,
      object_type: 'node', rel: f.rel,
      valid_from: f.valid_from, valid_until: f.valid_until || null,
      source: 'ontology', confidence: f.confidence || 0.85, group: 'g_ontology',
      meta: { headline: f.hl || '', impact: f.impact || 5 },
    };
  });
  window.TEMPORAL_SEED_FACTS = (window.TEMPORAL_SEED_FACTS || []).concat(out);
})();
