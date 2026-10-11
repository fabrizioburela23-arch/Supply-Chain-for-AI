/* ============================================================================
   engine/tour_script.js — EL guion del recorrido de un minuto (voz para Khipus OS, 2026-10-11)

   ÚNICA fuente de lo que Khipu dice y muestra en el recorrido guiado:
   - el navegador lo lee como window.KHIPU_TOUR (engine/cockpit.js pinta cada paso y engine/voice.js
     se lo pasa a la voz cuando la conversación está activa: el agente lo narra con SU voz);
   - el servidor lo lee con core/tour.py para generar el audio de cada frase con la MISMA voz del
     agente de ElevenLabs (GET /api/voice/tour/<lang>/<paso>) cuando no hay conversación abierta.
   Como el servidor SOLO sintetiza estas frases (nunca texto libre), nadie puede gastar la cuota de
   ElevenLabs pidiendo audio arbitrario. Lo que va entre `KHIPU_TOUR = ` y el `;` final debe ser JSON
   ESTRICTO (comillas dobles, sin comentarios ni comas colgantes) — tests/test_voice_tour.py lo verifica.

   act.kind ∈ empty (solo el chat) · graph (mapa) · glance (<empresa> en una mirada) · xray · sim
   (caída/auge simulado de act.company, act.sim) · agents (Tus agentes) · insights (Oportunidades) ·
   broker (Mi cuenta). El paso de las mascotas nombra a TODAS las del registro único (un test lo exige).
   ============================================================================ */
(typeof window !== 'undefined' ? window : globalThis).KHIPU_TOUR = {
  "version": "2026-10-11",
  "steps": [
    {"id": "hello", "act": {"kind": "empty"},
     "es": "Soy Khipu. Esto es Khipus OS: me hablas aquí, en el centro, y todo lo que te muestro se abre como una ventana a tu lado.",
     "en": "I'm Khipu. This is Khipus OS: you talk to me here in the center, and everything I show you opens as a window beside you."},
    {"id": "map", "act": {"kind": "graph"},
     "es": "Este es el mapa de la cadena de la inteligencia artificial: cada punto es una empresa y cada línea, una dependencia real.",
     "en": "This is the map of the AI supply chain: every dot is a company and every line, a real dependency."},
    {"id": "glance", "act": {"kind": "glance", "company": "Nvidia"},
     "es": "Pídeme cualquier empresa y te la resumo en una mirada: su riesgo, de quién depende y su precio en vivo, con su fuente.",
     "en": "Ask me about any company and I sum it up at a glance: its risk, who it depends on and its live price, with the source."},
    {"id": "xray", "act": {"kind": "xray", "company": "Nvidia"},
     "es": "Si quieres más, la desarmo: el X-Ray muestra de qué depende y quién sufre o gana si cae.",
     "en": "Want more? I take it apart: the X-Ray shows what it depends on, and who suffers or wins if it falls."},
    {"id": "sim", "act": {"kind": "sim", "company": "TSMC", "sim": "collapse"},
     "es": "¿Y si cae TSMC? Simulo el golpe y lo propago por toda la cadena, salto por salto. Es un escenario hipotético, no un pronóstico.",
     "en": "And if TSMC falls? I simulate the shock and spread it through the whole chain, hop by hop. It is a hypothetical scenario, not a forecast."},
    {"id": "agents", "act": {"kind": "agents"},
     "es": "No trabajo solo: Analista, Radar, Cadena, Técnico y Comité investigan con evidencia citada. Llámalos por su nombre.",
     "en": "I don't work alone: Analyst, Radar, Chain, Technical and Committee research with cited evidence. Call them by name."},
    {"id": "insights", "act": {"kind": "insights"},
     "es": "Aquí ves lo que el sistema detecta ahora mismo: riesgos y oportunidades en vivo. Es análisis, no una recomendación.",
     "en": "Here you see what the system detects right now: live risks and opportunities. It is analysis, not a recommendation."},
    {"id": "money", "act": {"kind": "broker"},
     "es": "Y puedes invertir desde aquí: siempre ves el resumen antes, nada se envía sin tu confirmación, y la insignia de arriba te dice si es práctica o dinero real.",
     "en": "And you can invest from here: you always see the summary first, nothing is sent without your confirmation, and the badge on top tells you whether it is practice or real money."},
    {"id": "bye", "act": {"kind": "empty"},
     "es": "Eso es Khipus. Escríbeme o háblame: «desármame Nvidia», «¿qué pasa si cae TSMC?» o «muéstrame oportunidades».",
     "en": "That's Khipus. Type or talk to me: “break down Nvidia”, “what if TSMC falls?” or “show me opportunities”."}
  ]
};
