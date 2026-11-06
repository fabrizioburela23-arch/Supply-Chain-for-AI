# Examen de oro del chat — 15/20 aprobadas

_2026-11-06 15:13 UTC · https://supply-chain-for-ai-production.up.railway.app_

| | Pregunta | Herramientas | Seg. | Qué falló |
|---|---|---|---|---|
| ✅ | precio | get_company | 4.3 |  |
| ✅ | fondo | get_company, simulate_price | 12.8 |  |
| ❌ | fondo_amd | get_company, simulate_price | 11.6 | muy larga (222 palabras) |
| ✅ | valuacion | get_company | 4.2 |  |
| ✅ | escenario_taiwan | scenario_exposure | 7.0 |  |
| ❌ | escenario_up | get_company, scenario_exposure, get_news | 8.9 | muy larga (175 palabras) |
| ❌ | demanda | get_company, run_scenario, get_news | 16.0 | muy larga (197 palabras) |
| ✅ | proveedores | get_company | 4.1 |  |
| ✅ | clientes | get_company | 3.5 |  |
| ✅ | screen | screen_stocks | 5.7 |  |
| ✅ | movers | market_movers | 5.8 |  |
| ✅ | noticias | get_company, get_news | 6.5 |  |
| ✅ | mundo | get_world_events, scenario_exposure | 6.8 |  |
| ✅ | privada | get_company | 3.0 |  |
| ❌ | comparar | get_company, get_company | 6.7 | muy larga (213 palabras) |
| ✅ | historia | get_company, get_history | 8.8 |  |
| ✅ | research | get_company, get_research, get_committee_memo | 6.3 |  |
| ✅ | riesgo_cartera | get_company, get_company, get_risk_report, get_risk_report | 17.5 |  |
| ✅ | web | read_url, web_search | 31.3 |  |
| ❌ | resultados | get_company, web_search, web_search, get_news | 20.9 | se rindió ("reintenta") |
