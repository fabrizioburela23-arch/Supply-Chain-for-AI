// nodes/nodes_expand4.js — Infraestructura espacial (Khipu Finance)
// Completa el sector espacio del documento de expansión: landers lunares,
// estructuras en microgravedad, plano espacial y estación comercial.

var NODES_EXPAND4 = [
  {
    "id":"IntuitiveMachines","label":"Intuitive Machines","ticker":"LUNR · Nasdaq","cat":"space_infra","port":"",
    "role":"Primer contratista lunar comercial puro: landers, comunicaciones lunares y navegación.",
    "supplies":"Lander Nova-C (misiones IM-1/2/3), Near Space Network y contratos NASA CLPS; servicios de datos lunares.",
    "moat":"Único operador con lander lunar certificado por la NASA; backlog ~$1B y contratos CLPS plurianuales.",
    "loc":"EE.UU.","country":"EEUU","growth":"🟢 Récord de ingresos 2026; guidance ~$1B","margin":-0.05,"mkt":"LUNR",
    "role_en":"First pure-play commercial lunar contractor: landers, lunar comms and navigation.",
    "supplies_en":"Nova-C lander (IM-1/2/3 missions), Near Space Network and NASA CLPS contracts; lunar data services.",
    "moat_en":"Only operator with a NASA-certified lunar lander; ~$1B backlog and multi-year CLPS contracts.",
    "growth_en":"🟢 Record revenue 2026; ~$1B guidance"
  },
  {
    "id":"Redwire","label":"Redwire Space","ticker":"RDW · NYSE","cat":"space_infra","port":"",
    "role":"Infraestructura espacial: estructuras desplegables, paneles solares y manufactura en microgravedad.",
    "supplies":"Arrays solares (ROSA), antenas, sensores y biofabricación en órbita; componentes para satélites y estaciones.",
    "moat":"Cartera amplia de hardware espacial probado en vuelo; manufactura en microgravedad como upside único (órganos, cristales).",
    "loc":"EE.UU.","country":"EEUU","growth":"🟢 ~$335M 2025; guidance $450-500M 2026","margin":-0.02,"mkt":"RDW",
    "role_en":"Space infrastructure: deployable structures, solar arrays and microgravity manufacturing.",
    "supplies_en":"Solar arrays (ROSA), antennas, sensors and in-orbit biofabrication; components for satellites and stations.",
    "moat_en":"Broad flight-proven space hardware portfolio; microgravity manufacturing as unique upside (organs, crystals).",
    "growth_en":"🟢 ~$335M 2025; $450-500M guidance 2026"
  },
  {
    "id":"SierraSpace","label":"Sierra Space","ticker":"Pre-IPO","cat":"space_infra","port":"",
    "role":"Plano espacial Dream Chaser y módulos inflables LIFE para estaciones comerciales.",
    "supplies":"Dream Chaser (carga a la ISS, reutilizable, aterriza en pista); módulos LIFE para Orbital Reef con Blue Origin.",
    "moat":"Único vehículo de reentrada con alas en desarrollo comercial; socio clave de la estación Orbital Reef.",
    "loc":"EE.UU.","country":"EEUU","growth":"⭐ PRE-IPO (~$5B valuation); Dream Chaser primer vuelo","margin":null,"preipo":true,"mkt":"",
    "role_en":"Dream Chaser spaceplane and LIFE inflatable modules for commercial stations.",
    "supplies_en":"Dream Chaser (reusable ISS cargo, runway landing); LIFE modules for Orbital Reef with Blue Origin.",
    "moat_en":"The only winged reentry vehicle in commercial development; key partner of the Orbital Reef station.",
    "growth_en":"⭐ PRE-IPO (~$5B valuation); Dream Chaser maiden flight"
  },
  {
    "id":"AxiomSpace","label":"Axiom Space","ticker":"Pre-IPO","cat":"space_infra","port":"",
    "role":"Primera estación espacial comercial privada; misiones de astronautas privados.",
    "supplies":"Misiones Ax-1/2/3 (astronautas privados vía Crew Dragon de SpaceX); módulos Axiom Station que sucederán a la ISS.",
    "moat":"Primer mover en estaciones comerciales con contrato NASA para acoplar a la ISS; trajes espaciales de nueva generación.",
    "loc":"EE.UU.","country":"EEUU","growth":"⭐ PRE-IPO; primer módulo a la ISS hacia 2027","margin":null,"preipo":true,"mkt":"",
    "role_en":"First commercial private space station; private astronaut missions.",
    "supplies_en":"Ax-1/2/3 missions (private astronauts via SpaceX Crew Dragon); Axiom Station modules to succeed the ISS.",
    "moat_en":"First mover in commercial stations with a NASA contract to dock to the ISS; next-gen spacesuits.",
    "growth_en":"⭐ PRE-IPO; first module to the ISS ~2027"
  }
];
window.NODES_EXPAND4 = NODES_EXPAND4;

var LINKS_EXPAND4 = [
  {s:"IntuitiveMachines", t:"SpaceX",     w:2, rel:"lanza en Falcon 9",        type:"supply"},
  {s:"AxiomSpace",        t:"SpaceX",     w:3, rel:"misiones en Crew Dragon",  type:"supply"},
  {s:"Redwire",           t:"PlanetLabs", w:2, rel:"estructuras/componentes",  type:"supply"},
  {s:"Redwire",           t:"AST_SpaceMobile", w:2, rel:"componentes",          type:"supply"},
  {s:"SierraSpace",       t:"BlueOrigin", w:2, rel:"Orbital Reef (estación)",  type:"partner"},
];
window.LINKS_EXPAND4 = LINKS_EXPAND4;
