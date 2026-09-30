"""brokerage/ — corretaje MULTI-CLIENTE vía Alpaca (Phase 3, 2026-09-30).

Opera cuentas de varias personas (papel por defecto) con:
  · credenciales CIFRADAS por cliente (crypto.py, Fernet),
  · controles de riesgo PRE-orden por cliente (risk.py),
  · previsualización → confirmación explícita (service.py),
  · cola de APROBACIÓN HUMANA para lo que proponen agentes (MCP) y el comité,
  · registro de auditoría append-only (tabla broker_audit),
  · interruptor global (BROKERAGE_TRADING_ENABLED=off bloquea todo).

Todo es OPCIONAL: sin DATABASE_URL, `service.available()` es False y el
blueprint responde 503 sin romper el resto de la app. Ver docs/BROKERAGE.md.
Las rutas /api/trade/* (cuenta de la casa) siguen intactas.
"""
