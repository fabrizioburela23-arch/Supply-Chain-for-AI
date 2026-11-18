# Examen de oro del chat — 12/21 aprobadas

_2026-11-18 22:42 UTC · https://supply-chain-for-ai-production.up.railway.app_

| | Pregunta | Herramientas | Seg. | Qué falló |
|---|---|---|---|---|
| ✅ | precio | get_company | 2.6 |  |
| ❌ | fondo | get_company, simulate_price | 13.3 | sin «Mi recomendación» |
| ❌ | fondo_amd | get_company, simulate_price, get_news | 14.2 | sin «Mi recomendación» |
| ❌ | valuacion | get_company | 2.6 | sin «Mi recomendación» |
| ✅ | escenario_taiwan | scenario_exposure | 11.9 |  |
| ✅ | escenario_up | get_company, scenario_exposure | 12.6 |  |
| ✅ | demanda | get_company, run_scenario, get_news | 14.9 |  |
| ✅ | proveedores | get_company | 2.2 |  |
| ✅ | clientes | get_company | 2.3 |  |
| ❌ | screen | screen_stocks, market_movers, rank_companies, screen_stocks, rank_companies | 14.9 | muy larga (239 palabras); se rindió ("no tengo datos") |
| ✅ | movers | market_movers | 3.5 |  |
| ✅ | noticias | get_company, get_news | 3.2 |  |
| ✅ | mundo | get_world_events, web_search | 17.8 |  |
| ✅ | privada | get_company | 2.0 |  |
| ❌ | comparar | get_company, get_company | 11.3 | sin «Mi recomendación» |
| ✅ | historia | get_company, get_history | 5.2 |  |
| ❌ | research | get_company, get_research, get_committee_memo | 3.1 | sin «Mi recomendación» |
| ❌ | riesgo_cartera | get_company, get_company, get_risk_report, get_company | 12.1 | sin «Mi recomendación» |
| ✅ | web | read_url, web_search | 30.9 |  |
| ❌ | resultados | get_company, simulate_price | 5.6 | 1 cifra(s) no verificada(s) |
| ❌ | ipo_anthropic | get_company, scenario_exposure, get_research, web_search | 26.1 | sin «Mi recomendación» |
