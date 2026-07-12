"""core/providers — capa de proveedores de datos financieros (patrón adapter).

Objetivo (Fase 1 del "módulo de datos Bloomberg-depth", 2026-07-12):
la app consume SIEMPRE los esquemas unificados de base.py (CompanyProfile,
CryptoAsset) y nunca el JSON crudo de un proveedor. Cambiar de proveedor
(FMP → Bloomberg SAPI, CoinGecko → otro) = escribir un adapter nuevo, sin
tocar la UI ni los endpoints.

Adapters:
  - coingecko.py  → cripto (sin API key, tier gratuito; COINGECKO_KEY opcional)
  - (futuro) fmp.py, alpaca.py, bloomberg_sapi.py — equities/trading

REGLA DE SEGURIDAD (verbatim del usuario): las API keys van SIEMPRE en
variables de entorno, NUNCA en el código.
"""
