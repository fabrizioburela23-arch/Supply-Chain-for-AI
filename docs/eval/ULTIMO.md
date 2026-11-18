# Examen de oro del chat — 19/21 aprobadas

_2026-11-18 23:51 UTC · https://supply-chain-for-ai-production.up.railway.app_

| | Pregunta | Herramientas | Seg. | Qué falló |
|---|---|---|---|---|
| ✅ | precio | get_company | 1.8 |  |
| ✅ | fondo | get_company, simulate_price | 18.9 |  |
| ✅ | fondo_amd | get_company, simulate_price, get_news | 12.2 |  |
| ✅ | valuacion | get_company | 3.0 |  |
| ✅ | escenario_taiwan | scenario_exposure | 9.3 |  |
| ✅ | escenario_up | get_company, scenario_exposure, get_supply_chain | 12.7 |  |
| ✅ | demanda | get_company, run_scenario, scenario_exposure | 15.4 |  |
| ✅ | proveedores | get_company | 2.2 |  |
| ✅ | clientes | get_company | 2.1 |  |
| ✅ | screen | screen_stocks | 4.5 |  |
| ✅ | movers | market_movers | 3.0 |  |
| ✅ | noticias | get_company, get_news, web_search | 17.5 |  |
| ❌ | mundo | get_world_events, web_search | 18.5 | muy larga (206 palabras) |
| ✅ | privada | get_company | 2.8 |  |
| ✅ | comparar | get_company, get_company | 14.4 |  |
| ✅ | historia | get_company, get_history | 3.1 |  |
| ✅ | research | get_company, get_conclusions_board, get_research, get_committee_memo | 5.7 |  |
| ✅ | riesgo_cartera | get_company, get_company, get_risk_report, get_risk_report, get_company | 20.0 |  |
| ✅ | web | read_url, web_search | 27.2 |  |
| ❌ | resultados | get_company, simulate_price | 6.3 | 1 cifra(s) no verificada(s) |
| ✅ | ipo_anthropic | get_company, get_committee_memo, get_research, scenario_exposure | 11.4 |  |
