"""matrix/ — el motor de matrices de Khipus (Etapa 3, 2026-07).

Cada tipo de relación (supply, fab, cloud, license, invest, deploy, owns,
ppa, partner) es una MATRIZ numérica N×N sobre los objetos de la ontología.
Convención canónica (Etapa 2): A[i,j] = peso del vínculo i→j donde la fila i
PROVEE a la columna j — el valor fluye i→j, y por tanto el DAÑO también:
si i cae, j sufre en proporción a su dependencia (columna normalizada).

Los factores externos (sanciones, escaseces, conflictos) se modelan como
HIPERARISTAS: objetos tipo 'Factor' en la ontología con links 'affects'
cuyo peso es el coeficiente de modulación — M' = M ∘ (1 + Σ coef·máscara),
con ventanas de validez bitemporales (mismo time-travel que todo lo demás).

Módulos:
  engine.py — build_matrices / modulate / propagate / compute_metrics.
  api.py    — blueprint Flask /api/matrix/* (registrado defensivo en server).

Igual que la ontología: 100% opcional — sin DATABASE_URL el server arranca
y estas rutas devuelven 503.
"""
