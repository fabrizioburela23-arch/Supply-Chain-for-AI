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
  "version": "2026-10-12",
  "steps": [
    {"id": "hello", "act": {"kind": "empty"},
     "es": "Soy Khipu. Me hablas aquí, en el centro, y lo que te muestro se abre a tu lado.",
     "en": "I'm Khipu. You talk to me here in the center, and what I show you opens beside you."},
    {"id": "map", "act": {"kind": "graph"},
     "es": "Este es el mapa de la cadena de la IA: cada punto, una empresa; cada línea, una dependencia.",
     "en": "This is the AI supply-chain map: each dot a company, each line a dependency."},
    {"id": "glance", "act": {"kind": "glance", "company": "Nvidia"},
     "es": "Pide una empresa y la ves en una mirada: precio en vivo con su fuente y lo más fuerte a favor y en contra.",
     "en": "Ask for a company and see it at a glance: live price with its source, and the strongest points for and against."},
    {"id": "xray", "act": {"kind": "xray", "company": "Nvidia"},
     "es": "¿Quieres más? El X-Ray muestra de qué depende y quién sufre o gana si cae.",
     "en": "Want more? The X-Ray shows what it depends on and who suffers or wins if it falls."},
    {"id": "sim", "act": {"kind": "sim", "company": "TSMC", "sim": "collapse"},
     "es": "¿Y si cae TSMC? Propago el golpe por la cadena: es hipotético, no un pronóstico.",
     "en": "And if TSMC falls? I spread the shock through the chain: it is hypothetical, not a forecast."},
    {"id": "agents", "act": {"kind": "agents"},
     "es": "No trabajo solo: Analista, Radar, Cadena, Técnico y Comité investigan con evidencia. Llámalos por su nombre.",
     "en": "I don't work alone: Analyst, Radar, Chain, Technical and Committee research with evidence. Call them by name."},
    {"id": "insights", "act": {"kind": "insights"},
     "es": "Aquí ves riesgos y oportunidades detectados en vivo. Es análisis, no una recomendación.",
     "en": "Here are risks and opportunities detected live. It is analysis, not a recommendation."},
    {"id": "money", "act": {"kind": "broker"},
     "es": "Y puedes invertir: el resumen siempre dice si es práctica o dinero real, y nada se envía sin tu confirmación.",
     "en": "And you can invest: the summary always says practice or real money, and nothing is sent without your confirmation."},
    {"id": "bye", "act": {"kind": "empty"},
     "es": "Eso es Khipus. Escríbeme o háblame: «desármame Nvidia» o «¿qué pasa si cae TSMC?».",
     "en": "That's Khipus. Type or talk to me: “break down Nvidia” or “what if TSMC falls?”."}
  ]
};
