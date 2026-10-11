---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_company_data.py"
lenguaje: "python"
lineas: 667
aliases: ["tests/test_company_data.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_company_data.py

> Prueba · capa [[Capa Pruebas]] · 667 líneas · `tests/test_company_data.py`

## Qué prueba

Dossier para TODAS las empresas + info en vivo (core/company_data.py y las rutas /api/findossier, /api/dossier, /api/company/live). SIN red: todo HTTP se reemplaza con monkeypatch (el sandbox no alcanza Yahoo). Lo que se blinda: · Yahoo fundamentals-timeseries → estructura normalizada en USD (JPY→USD, FCF = OCF + CapEx cuando falta el reportado). · Yahoo quoteSummary → perfil en vivo (márgenes en %, GBp = peniques). · Orden de la cascada (FMP vacío → Yahoo; AV solo EE.UU. y último). · Las rutas conservan EXACTAMENTE las claves/unidades que consume el cliente. · /api/dossier NUNCA sintético; sin datos → 200 {available:false}.

**28** funciones `test_…`.

## Cubre

- [[core.company_data.py]]
- [[core.quotes.py]]
- [[server.py]]

## Rutas HTTP que llama

3 rutas, de los grupos: [[API company]], [[API dossier]], [[API findossier]]

## Variables de entorno que fija o nombra

[[ENV ANTHROPIC_KEY]], [[ENV AV_KEY]], [[ENV FINNHUB_KEY]], [[ENV FMP_KEY]], [[ENV MARKETSTACK_KEY]], [[ENV SECRET_KEY]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-28 (c) — DOSSIER PARA TODAS LAS EMPRESAS + DATOS EN VIVO (sw v151)]]
