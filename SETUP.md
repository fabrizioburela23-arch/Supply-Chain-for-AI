# Khipus AI Finance Inteligence — Guía de configuración (Railway)

El **código está completo y desplegado en `main`**. Lo que queda es configuración
que solo tú puedes hacer (acceso a Railway / ElevenLabs). Aquí está todo.

---

## 1. Variables de entorno (servicio principal en Railway)

### Ya configuradas ✅
`ANTHROPIC_KEY`, `ELEVENLABS_KEY`, `ELEVENLABS_AGENT_ID`, `ELEVENLABS_ALLOW_OVERRIDE`,
`FINNHUB_KEY`, `FMP_KEY`, `MARKETSTACK_KEY`, `AV_KEY`, `ALPACA_KEY`, `ALPACA_SECRET`,
`ALPACA_BASE`, `AI_MODEL`, `MIROFISH_URL`, `GEMINI_KEY`.

### Recomendadas
| Variable | Valor | Por qué |
|---|---|---|
| `SECRET_KEY` | (aleatorio fuerte) | El server avisa que está en default — necesario para JWT/seguridad. |
| `AI_ORDER` | `claude,gemini,nvidia` | Orden de fallback de IA. Claude primero (mejor calidad). |
| `RAG_URL` | (URL del servicio RAG, ver §2) | Enciende el Second Brain (búsqueda semántica). |

### Opcionales
| Variable | Valor | Por qué |
|---|---|---|
| `NVIDIA_KEY` | nvapi-… (build.nvidia.com) | 2º canal de IA de respaldo (gratis). |
| `MIROFISH_TOKEN` | (token) | Solo si MiroFish sale 🔴 por auth en el 🩺. |
| `SEC_USER_AGENT` | `Tu Nombre tu@email.com` | Para el Research SEC 10-K. |

---

## 2. Desplegar el RAG / Second Brain (2º servicio en Railway)

Es el único servicio en 🔴 en el 🩺. Búsqueda semántica de Bixby. **Opcional.**
La carpeta `rag/` ya está lista para desplegar (Dockerfile + railway.toml).

1. Railway → tu proyecto → **+ New → GitHub Repo** → mismo repo.
2. Servicio nuevo → **Settings → Root Directory** = `rag`
3. **Settings → Volumes → New Volume** → mount path = `/data`
4. **Variables** del servicio RAG: `ANTHROPIC_KEY` = (la misma clave de Claude).
5. **Settings → Networking → Generate Domain** → copia la URL.
6. Servicio **principal → Variables** → `RAG_URL` = esa URL.
7. Tras redesplegar: en la app → **⚙ Ajustes → "Indexar todos los nodos"** (1 vez).
8. Verifica en 🩺 que **Second Brain** quede 🟢.

> Nota: ChromaDB descarga un modelo de embeddings (~80 MB) al indexar. Si el
> servicio RAG se reinicia por memoria, súbele la RAM en Railway.

---

## 3. ElevenLabs — que Bixby no se corte por silencio

Si la voz de Bixby se desconecta cuando esperas un resultado callado:
1. elevenlabs.io → **Conversational AI → tu agente (Bixby)**.
2. **Advanced / Voice settings** → sube el **"Turn timeout"** (a ~45–60s) y, si existe,
   el timeout de silencio que termina la llamada.
3. **Security / Overrides** → activa el override del **System prompt** (para que la
   instrucción de "ser paciente" que manda la app se aplique).

(Hay un prompt listo para que Claude Cowork lo haga vía la API de ElevenLabs.)

---

## 4. Verificación final (🩺 Estado del Sistema)

Abre la app **en incógnito** → botón **🩺** en el header. Deberías ver:
- ✦ Claude 🟢 · ◆ Gemini 🟢 · 🎙 ElevenLabs 🟢 · 🧬 MiroFish 🟢 · 📈 Finnhub 🟢
- 🧠 Second Brain 🟢 (tras el paso §2)

### Tour de features
- **Espacio** → planeta 3D con satélites reales.
- **Geopolítica** → globo 3D con empresas por región.
- **Bixby** (⌘K) → "compara márgenes de NVIDIA, TSMC y ASML" → tabla inline.
- Clic en **NVDA** → 🧠 Second Brain · 📊 Dossier · 📄 SEC.
- Clic en **SpaceX/Helion** → panel 🔒 Empresa privada.
- **Simulación** → motor 🤖 IA Simple o 🧬 MiroFish.
- **🕸 3D** → scatter de inversión (tiempo × tamaño × riesgo) + filtros 💎.
- Detalle de empresa → **+ C1 / + C2** para editar carteras.
