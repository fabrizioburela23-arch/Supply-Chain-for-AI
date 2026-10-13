---
tipo: "modulo"
capa: "Cuantitativo (matrices, tensores, riesgo)"
ruta: "core/risk_models.py"
lenguaje: "python"
lineas: 292
aliases: ["core/risk_models.py"]
tags: ["capa/cuantitativo", "tipo/modulo"]
---

# core/risk_models.py

> Módulo · capa [[Capa Cuantitativo (matrices, tensores, riesgo)]] · 292 líneas · `core/risk_models.py`

## Para qué sirve

estimadores ROBUSTOS de riesgo (BRECHAS L2-14/L2-15/L2-16/L2-18; ARQUITECTURA_V2 §9.2-§9.3).

## API pública

- `ewma_var(returns, lam=…, seed_n=…)` — Varianza EWMA PRONOSTICADA para el día siguiente al último retorno (media cero, RiskMetrics). Semilla: media de r² de las primeras `seed_n` … _(línea 38)_
- `ewma_cov(R, lam=…, seed_n=…)` — Matriz EWMA (T×p → p×p): Σ_{t+1} = λΣ_t + (1−λ) r_t r_tᵀ, semilla = media de r rᵀ de las primeras `seed_n`. _(línea 50)_
- `ledoit_wolf(X)` — (Σ̂, δ, μ) para X (T×p, retornos). Igual que sklearn.covariance.ledoit_wolf (assume_centered=False): X se centra, S = XᵀX/T, objetivo μ·I … _(línea 63)_
- `shrink(S, delta)` — (1−δ)·S + δ·μ·I con μ = tr(S)/p. _(línea 87)_
- `nearest_psd(S, rel_floor=…)` — (matriz semidefinida positiva más cercana por recorte de autovalores, ¿se reparó?). _(línea 95)_
- `pairwise_cov(rets, syms, min_obs=…)` — rets {sym: {fecha: retorno}} → (S p×p con n−1, N p×p de observaciones comunes). Un par con menos de `min_obs` observaciones comunes queda … _(línea 108)_
- `pairwise_corr(rets, syms, min_obs=…)` — Correlación de CADA par con los momentos de SU ventana común: cov_ij / √(var_i|ij · var_j|ij), recortada a [−1, 1]. Revisión lote I: … _(línea 116)_
- `moments(x)` — (media, σ muestral n−1, asimetría g1, curtosis en EXCESO g2) — momentos poblacionales para g1/g2. _(línea 155)_
- `cornish_fisher_z(z, skew, exkurt)` _(línea 171)_
- `cf_valid(skew, exkurt)` — ¿La expansión de Cornish-Fisher es usable en la cola izquierda? (revisión lote I) Fuera de su dominio (gran asimetría POSITIVA con curtosis … _(línea 176)_
- `cf_var(mu, sigma, skew, exkurt, conf=…, h=…)` — VaR Cornish-Fisher a h días (fracción positiva = pérdida). Escala iid: μh, σ√h, asimetría/√h, curtosis/h. None si la expansión está fuera … _(línea 191)_
- `param_var(mu, sigma, conf=…, h=…)` — VaR normal a h días: −(μh + z·σ√h). _(línea 202)_
- `overlapping_returns(r, h)` — Retornos compuestos de h días en ventanas superpuestas (n − h + 1 ventanas). _(línea 208)_
- `hist_var_cvar(x, conf=…)` — (VaR, CVaR) históricos (pérdida positiva) con el mismo cuantil lineal que core/risk_report. _(línea 224)_
- `sharpe_arith(r, rf_annual=…, periods=…)` — (media diaria − rf/252)·252 / (σ diaria·√252). None si σ = 0 o pocos datos. _(línea 235)_
- `tbill_yield(discount, days=…, basis=…)` — Tasa de descuento bancaria (decimal, p. ej. 0,04) → rendimiento equivalente (decimal). basis 'bond_equivalent' (365) o 'money_market' … _(línea 247)_
- `adv_from_rows(rows, days=…)` — rows [(fecha, cierre, volumen)] (cierre en moneda local) → {adv_shares, adv_value, n, as_of} con las últimas `days` sesiones que SÍ traen … _(línea 260)_
- `liquidity(value_usd, adv_value_usd, participation=…, flag_days=…)` — {days_to_liquidate, flag} — días vendiendo el `participation` del volumen medio diario. _(línea 271)_
- `rc_dispersion(w, cov)` — Contribuciones al riesgo RC_i = w_i(Σw)_i/σ² (fracciones) + dispersión: {rc, min, max, max_over_min, cv, hhi, n_eff} (HHI y n_eff = 1/HHI … _(línea 280)_

**Internas** (empiezan con `_`): `_seed_var`, `_pairwise_moments`, `_quantile_linear`

## Depende de

_Nada interno._

## Lo usan

- [[core.portfolio_ai.py]] — lo importa
- [[core.prices_store.py]] — lo importa
- [[core.risk_report.py]] — lo importa
- [[mcp_server.ops.py]] — lo importa
- herramienta MCP `project_portfolio` → [[API herramientas MCP]]

_Además lo importan 1 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_risk_robust.py]]
