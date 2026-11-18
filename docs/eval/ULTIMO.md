# Examen de oro del chat — 13/21 aprobadas

_2026-11-18 23:30 UTC · https://supply-chain-for-ai-production.up.railway.app_

| | Pregunta | Herramientas | Seg. | Qué falló |
|---|---|---|---|---|
| ✅ | precio | get_company | 2.1 |  |
| ❌ | fondo | get_company, simulate_price | 12.5 | sin «Mi recomendación» |
| ❌ | fondo_amd | get_company, simulate_price, get_news | 12.9 | sin «Mi recomendación» |
| ❌ | valuacion | get_company | 2.4 | sin «Mi recomendación» |
| ✅ | escenario_taiwan | scenario_exposure | 13.6 |  |
| ✅ | escenario_up | get_company, scenario_exposure | 7.9 |  |
| ✅ | demanda | get_company, run_scenario, get_news | 14.9 |  |
| ✅ | proveedores | get_company | 2.7 |  |
| ✅ | clientes | get_company | 2.2 |  |
| ✅ | screen | screen_stocks | 4.0 |  |
| ✅ | movers | market_movers | 3.6 |  |
| ✅ | noticias | get_company, get_news | 4.8 |  |
| ✅ | mundo | get_world_events, web_search | 18.3 |  |
| ✅ | privada | get_company | 1.8 |  |
| ❌ | comparar | get_company, get_company | 10.7 | sin «Mi recomendación» |
| ✅ | historia | get_company, get_history | 5.4 |  |
| ❌ | research | get_company, get_research, get_committee_memo | 3.6 | sin «Mi recomendación» |
| ❌ | riesgo_cartera | get_company, get_company, get_risk_report, get_company | 12.2 | sin «Mi recomendación» |
| ✅ | web | read_url, web_search | 29.2 |  |
| ❌ | resultados | get_company, simulate_price | 5.4 | 1 cifra(s) no verificada(s) |
| ❌ | ipo_anthropic | get_company, scenario_exposure, get_news, get_research | 22.8 | sin «Mi recomendación» |
