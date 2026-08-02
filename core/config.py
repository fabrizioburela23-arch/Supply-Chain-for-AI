"""core/config.py — variables de entorno compartidas entre server y ontology.

Solo viven aquí las que necesita más de un módulo (IA, Finnhub, timeout).
Las exclusivas del server (Alpaca, ElevenLabs, Neo4j…) siguen en server.py.
load_dotenv() es idempotente: no importa si server.py también lo llama.
"""
import os

from dotenv import load_dotenv

load_dotenv()

FINNHUB  = os.getenv('FINNHUB_KEY', '')
CLAUDE   = os.getenv('ANTHROPIC_KEY') or os.getenv('CLAUDE_KEY', '')
# Modelo de Claude para los análisis. Decisión del usuario (2026-07): SONNET 5
# EN TODO — es el mejor equilibrio calidad/velocidad de la familia Sonnet y
# rinde a nivel Opus en muchas tareas. Cambiable sin tocar código con AI_MODEL.
AI_MODEL = os.getenv('AI_MODEL', 'claude-sonnet-5')

# ── IA híbrida: dos niveles de modelo ───────────────────────────────────────
# 'fast'  → comandos, ruteo, resúmenes de noticias, alertas, agente de trading.
# 'deep'  → síntesis de investigación profunda, tesis, Canvas IA, cripto IA, SIM.
# 2026-07-15 (feedback Fabrizio: "Bixby tarda mucho en hablar/ejecutar"): el tier
# 'fast' pasa a Haiku 4.5 (3-5x más rápido para clasificación+JSON trivial); el
# 'deep' se queda en Sonnet 5 para que la calidad de la sim/investigación/cripto
# NO cambie. Sobreescribibles por entorno. La MISMA ANTHROPIC_KEY sirve para ambos.
AI_MODEL_FAST = os.getenv('AI_MODEL_FAST') or 'claude-haiku-4-5'
AI_MODEL_DEEP = os.getenv('AI_MODEL_DEEP') or 'claude-sonnet-5'

# ── Multi-proveedor de IA: alterna entre Claude, Google Gemini y NVIDIA NIM ──
# Si un canal falla (o no tiene key), pasa al siguiente automáticamente.
# NVIDIA NIM (build.nvidia.com) y Gemini tienen tier gratis útil para el MVP.
GEMINI_KEY   = os.getenv('GEMINI_KEY') or os.getenv('GOOGLE_API_KEY', '')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')
NVIDIA_KEY   = os.getenv('NVIDIA_KEY') or os.getenv('NVIDIA_API_KEY', '')
NVIDIA_MODEL = os.getenv('NVIDIA_MODEL', 'meta/llama-3.1-70b-instruct')
AI_ORDER     = [p.strip() for p in os.getenv('AI_ORDER', 'claude,gemini,nvidia').split(',') if p.strip()]

HTTP_TIMEOUT = 8

# ── Búsqueda web (Investigador Autónomo) ─────────────────────────────────────
# Tavily: pensado para agentes LLM (snippets + URL ya listos para citar, sin
# parsear HTML a mano); tier gratis 1,000 búsquedas/mes alcanza para uso
# personal. Sin la key, el agente se auto-deshabilita — mismo patrón que
# NEO4J_*/DATABASE_URL (*_available()), nunca rompe el resto de la app.
TAVILY_KEY = os.getenv('TAVILY_KEY', '')

# Interruptor de investigación reactiva — decisión de Fabrizio (2026-08-02):
# arranca en 'off' (el agente SOLO investiga cuando se lo piden por el endpoint
# manual). El gancho reactivo (observe()) queda construido pero apagado —
# prenderlo más adelante es cambiar esta env var a 'on' en Railway y
# redeployar, no requiere código nuevo. Mismo espíritu que MIROFISH_URL/
# TAVILY_KEY: la capacidad existe, el gasto de IA no ocurre salvo que esté
# explícitamente prendida.
INVESTIGADOR_AUTO = os.getenv('INVESTIGADOR_AUTO', 'off')            # 'off' | 'on'
INVESTIGADOR_AUTO_CUTOFF_HORAS = int(os.getenv('INVESTIGADOR_AUTO_CUTOFF_HORAS', '6'))
