# Del Silicio a la IA · v8

Herramienta de **inteligencia de inversión** sobre la cadena de valor global de la IA:
137 empresas reales, 540+ conexiones, grafo D3 interactivo, y ahora **datos en vivo,
fundamentales, noticias, análisis con IA, portfolio real y alertas**.

Funciona de dos maneras:

| Modo | Cómo | API keys | Para quién |
|------|------|----------|------------|
| **Standalone** | Abre `app.html` en el navegador | Las ingresas en el panel ⚙ (se guardan en tu navegador) | Uso personal rápido |
| **Servidor** | `python server.py` → `http://localhost:5050` | Viven en `.env` (nunca en el browser) | Distribución / producción |

La app detecta sola en qué modo corre (mira si el puerto es `5050`) y enruta sus
llamadas al proxy del servidor o directo a las APIs.

---

## Modo standalone (sin instalar nada)

1. Doble clic en `app.html`.
2. Abre el panel **⚙ Configuración** (arriba a la derecha).
3. Pega tus API keys (Finnhub, FMP, Claude). Cada una tiene un botón **Probar**.
4. Listo: precios en vivo, noticias, fundamentales y análisis IA quedan activos.

> Las keys se guardan **solo en tu navegador** (`localStorage`), nunca dentro del
> archivo ni se envían a ningún servidor nuestro. Finnhub y FMP permiten llamadas
> directas desde el browser (CORS); Claude se llama con el header oficial
> `anthropic-dangerous-direct-browser-access`.

---

## Modo servidor (recomendado para producción)

```bash
pip install flask requests python-dotenv flask-caching anthropic
cp .env.example .env          # y rellena tus claves
python server.py              # http://localhost:5050
```

El servidor:
- Sirve `app.html`.
- Proxea Finnhub / FMP / Marketstack / Claude (las keys quedan en el servidor).
- Cachea respuestas en memoria (`flask-caching`) para no gastar llamadas.
- Expone `/api/*` y un `/api/health` para la barra de estado de la app.

Para abrir el WebSocket de precios en vivo, el frontend pide el token a
`/api/ws-token` y conecta directo a Finnhub (Flask no proxea WebSockets sin libs extra).

---

## Cómo obtener cada API key

| API | Para qué | Free tier | Registro |
|-----|----------|-----------|----------|
| **Finnhub** | Precios real-time (WebSocket), noticias, earnings | 60 req/min · WS 50 símbolos | <https://finnhub.io/register> |
| **Financial Modeling Prep** | Fundamentales, DCF, precio objetivo, insiders | 250 req/día | <https://site.financialmodelingprep.com/developer/docs> |
| **Anthropic Claude** | Análisis IA, síntesis de noticias, riesgo de cadena | pay-as-you-go (~$0.001/análisis) | <https://console.anthropic.com> |
| **Marketstack** | Precios EOD históricos (de v7) | 100 req/mes | <https://marketstack.com> |

---

## Qué feature necesita qué API

| Feature | Finnhub | FMP | Claude | Marketstack |
|---------|:------:|:---:|:------:|:-----------:|
| Precios en vivo (WebSocket) | ✅ | | | |
| Noticias por empresa | ✅ | | | |
| Próximo earnings + corona en el grafo | ✅ | | | |
| Fundamentales (P/E, EV/EBITDA, precio obj., insiders) | | ✅ | | |
| ✨ Análisis con IA | recom. | recom. | ✅ | |
| 📰 Resumen de noticias IA | ✅ | | ✅ | |
| Análisis de impacto del stress-test con IA | | | ✅ | |
| Portfolio personal con P&L real | ✅ | | | |
| Alertas de precio | ✅ | | | |
| Precios EOD (compatibilidad v7) | | | | ✅ |

Sin ninguna key, la app **sigue funcionando**: el grafo, el stress-test, el
pathfinder, la geopolítica y el análisis de red son 100% locales. Las features de
datos en vivo muestran un estado «configura tu key en ⚙» y degradan con elegancia.

---

## Archivos

```
Del_Silicio_IA_v8/
├── app.html        ← la app completa (un solo archivo, D3 desde CDN)
├── server.py       ← backend proxy opcional (~200 líneas, Flask)
├── .env.example    ← plantilla de variables de entorno
└── README.md       ← este archivo
```

## PWA / offline

En modo servidor, la app se puede **instalar** como aplicación de escritorio/móvil
(Service Worker embebido + Web App Manifest) y muestra los últimos datos cacheados
cuando no hay conexión, con un indicador «📴 Offline» en la cabecera.

---

*Análisis informativo basado en datos públicos y estimaciones. No constituye
asesoría financiera.*
