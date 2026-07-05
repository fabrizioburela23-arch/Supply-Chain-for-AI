# Activar la Ontología (Postgres en Railway) — Fase 1

## Qué es esto

Es el "cerebro" nuevo del sistema: un registro de **eventos** (cada hecho con
fecha de validez real) que reconstruye el estado del mundo en cualquier
momento — el mismo concepto del Grafo Temporal, pero como fuente de verdad
persistente y consultable, no solo una vista.

Ya está **todo el código construido y probado**. Solo falta que exista la
base de datos en Railway (2 clics) y pegar 1 variable.

## 1. Crear Postgres en Railway (2 min, gratis en tu plan actual de Railway)

1. Entra a tu proyecto en Railway (el mismo donde está `Supply-Chain-for-AI`).
2. Clic en **"+ New"** (o "Create") → **"Database"** → **"Add PostgreSQL"**.
3. Railway lo crea solo y **automáticamente** te da (y setea) una variable
   `DATABASE_URL` — no necesitas copiarla a mano si el servicio Postgres
   queda en el MISMO proyecto que tu app principal (Railway conecta los
   servicios del mismo proyecto por red privada).
4. Verifica: en tu servicio **principal** (Supply-Chain-for-AI) → Variables
   → debería aparecer `DATABASE_URL` automáticamente (si Railway soporta la
   referencia automática) o cópiala manualmente desde el servicio Postgres →
   pestaña **Variables** → `DATABASE_URL` → pégala en el servicio principal.

## 2. Redeploy

Railway → tu servicio principal → **Deployments** → `⋮` del último →
**Redeploy** (para que instale `sqlalchemy`/`psycopg2-binary` del
`requirements.txt` actualizado).

## 3. Correr la migración (una sola vez)

Esto carga las 463 empresas + 32 objetos de ontología + 1163 relaciones +
105 hechos temporales reales a la base nueva. Necesitas correrlo **una vez**,
desde tu computadora (o pídeselo a Cowork):

```bash
export DATABASE_URL="<la misma URL que pusiste en Railway>"
pip install sqlalchemy psycopg2-binary
python scripts/migrate_v0_to_ontology.py --reset
```

Deberías ver:
```
✅ 495 objetos creados
✅ 1163 links base creados (0 saltados)
✅ 86 hechos temporales con fecha real creados (0 saltados)
🎉 Migración completa
```

## 4. Verificar

- Abre **🩺 diagnóstico** → busca "ontología" → debe decir **"Ontología
  activa — 495 objetos, ~1249 vínculos, ~1744 eventos"**.
- Abre **◈ Grafo Temporal** → verás un badge morado nuevo: **"◈ ontología: N
  objetos · N vínculos · N eventos"**.
- Prueba la API directo en el navegador:
  `https://tu-app.railway.app/api/ontology/objects/TSMC`
  `https://tu-app.railway.app/api/ontology/graph?as_of=2020-01-01`
  `https://tu-app.railway.app/api/ontology/graph/diff?from=2018-01-01&to=2020-01-01`

## Qué NO cambia (importante)

El resto de la app (mapa, mercado, análisis, Bixby, Canvas…) sigue
funcionando exactamente igual — la ontología es **aditiva**, no reemplaza
nada todavía. El siguiente paso (que el mapa principal también lea de la
ontología) es un cambio más grande que se hace en su propia sesión, con
tiempo para probar cada pestaña — no se apuró para no arriesgar la demo.

## Si algo falla

- **"ontología no configurada"** en 🩺 → `DATABASE_URL` no llegó a Railway o
  no se redesplegó. Repite el paso 1-2.
- **La migración da error de conexión** → revisa que copiaste la
  `DATABASE_URL` completa (incluye usuario, contraseña, host, puerto,
  nombre de la base) y que tu computadora puede llegar a esa base (Railway
  Postgres suele ser accesible por internet mediante un dominio público en
  el plan gratis — revisa la pestaña "Connect" del servicio Postgres).
