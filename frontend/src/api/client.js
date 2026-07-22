/* api/client.js — ÚNICO punto de acceso HTTP del frontend.
   Reglas (mismas que el app clásico):
   - Las keys NUNCA viven en el browser: todo pasa por /api/* del server Flask.
   - Errores normalizados: siempre lanza ApiError con {status, body} — los
     componentes deciden qué mostrar, aquí no se pinta nada.
   - Timeout explícito: sin él, un endpoint colgado congela paneles enteros. */

const DEFAULT_TIMEOUT_MS = 30000

export class ApiError extends Error {
  constructor(message, { status = 0, body = null } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}

async function request(path, { method = 'GET', body, timeoutMs = DEFAULT_TIMEOUT_MS } = {}) {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), timeoutMs)
  try {
    const res = await fetch(path, {
      method,
      headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: ctrl.signal,
    })
    const text = await res.text()
    let data = null
    try { data = text ? JSON.parse(text) : null } catch { data = text }
    if (!res.ok) {
      throw new ApiError(`HTTP ${res.status} en ${path}`, { status: res.status, body: data })
    }
    return data
  } catch (e) {
    if (e instanceof ApiError) throw e
    if (e.name === 'AbortError') throw new ApiError(`Timeout (${timeoutMs}ms) en ${path}`, { status: 0 })
    throw new ApiError(`Red caída en ${path}: ${e.message}`, { status: 0 })
  } finally {
    clearTimeout(timer)
  }
}

export const get = (path, opts) => request(path, opts)
export const post = (path, body, opts) => request(path, { ...opts, method: 'POST', body })
