# Examen de oro del chat — 17/20 aprobadas

_2026-11-06 03:45 UTC · https://supply-chain-for-ai-production.up.railway.app_

| | Pregunta | Herramientas | Seg. | Qué falló |
|---|---|---|---|---|
| ❌ | precio | get_company | 8.9 | 1 cifra(s) no verificada(s) |
| ✅ | fondo | get_company, simulate_price, get_news, get_history | 16.1 |  |
| ✅ | fondo_amd | get_company, simulate_price, get_news | 20.6 |  |
| ✅ | valuacion | get_company | 6.9 |  |
| ✅ | escenario_taiwan | scenario_exposure | 9.2 |  |
| ❌ | escenario_up | get_company, scenario_exposure, get_supply_chain | 16.7 | no usó run_scenario |
| ✅ | demanda | get_company, run_scenario | 15.8 |  |
| ✅ | proveedores | get_company | 5.9 |  |
| ✅ | clientes | get_company | 5.3 |  |
| ✅ | screen | screen_stocks | 6.0 |  |
| ✅ | movers | market_movers | 7.4 |  |
| ✅ | noticias | get_company, get_news | 9.9 |  |
| ✅ | mundo | get_world_events, get_news | 8.6 |  |
| ✅ | privada | get_company | 3.5 |  |
| ✅ | comparar | get_company, get_company | 10.1 |  |
| ✅ | historia | get_company, get_history | 13.6 |  |
| ✅ | research | get_company, get_research, get_committee_memo | 10.2 |  |
| ✅ | riesgo_cartera | get_company, get_company, get_risk_report, get_company, get_news | 14.1 |  |
| ❌ | web | read_url | 18.9 | se rindió ("reintenta") |
| ✅ | resultados | get_company, get_history, get_news, web_search | 18.4 |  |
