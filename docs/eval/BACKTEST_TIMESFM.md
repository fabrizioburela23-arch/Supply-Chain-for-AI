# Backtest: simulación de Khipus vs TimesFM 2.5 (2026-11-10)

Pronóstico del cierre a **1 mes** (21 días hábiles), 100 fechas de corte por acción (cada 5 días, ~2 años), cada
modelo solo ve el pasado. Precios: /api/prices/eod (5 años, ajustados). Script: `scripts/backtest_forecast.py`.

| Modelo | Error de la mediana | Pérdida de cuantiles (↓ mejor) | Banda 50 % (ideal 50) | Banda 80 % (ideal 80) |
|---|---|---|---|---|
| **Khipus (core/price_sim)** | 10,25 % | **4,47 %** | **51,0 %** | **84,7 %** |
| TimesFM 2.5 (200M, Google) | 10,26 % | 4,49 % | 42,5 % | 73,5 % |
| Ingenuo (precio de hoy) | 10,12 % | 5,06 % | — | — |

Total de 600 pronósticos (NVDA, AMD, AVGO, TSM, MU, SPY; detalle por acción en el historial de la sesión).

**Lectura:** empate en exactitud; ninguno adivina la dirección mejor que «el precio de hoy» (esperado: el precio se
comporta casi como paseo aleatorio). Khipus tiene RANGOS mejor calibrados; TimesFM es demasiado confiado (sus bandas
contienen el precio real menos veces de lo que dicen). → No se integra TimesFM; se queda la simulación propia.
Límites: cortes solapados (no independientes), 6 acciones, 1 horizonte, q10/q90 de Khipus interpolados, sin salto de
resultados en Khipus (para comparar parejo). Repetir con más acciones y horizontes antes de conclusiones fuertes.
