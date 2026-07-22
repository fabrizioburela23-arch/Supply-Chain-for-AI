/**
 * NewsPanel — EL ÚNICO renderer de noticias del frontend React.
 *
 * El app clásico tenía 5 renderers de noticias duplicados que divergieron
 * (formatos de fecha distintos, unos sin fuente, otros sin enlace). Aquí hay
 * UNA sola normalización y UNA sola tarjeta, alimentadas por dos endpoints
 * del server (ver server.py):
 *
 * - `GET /api/news/<ticker>` (~1486): Finnhub CRUDO —
 *   `{headline, source, url, datetime}` con `datetime` en EPOCH SEGUNDOS,
 *   más `summary`.
 * - `GET /api/news/gdelt/<company>` (~2311): GDELT normalizado —
 *   `{headline, url, source}` donde `source` es un DOMINIO, `datetime` es el
 *   string `seendate` de GDELT (`YYYYMMDDTHHMMSSZ`), más `language`,
 *   `sentiment` (float tone) y `source_api: 'GDELT'`.
 *
 * Reglas del panel (semilla del filtro de objetividad):
 * - Ambos endpoints se piden en paralelo con Promise.allSettled: si uno cae,
 *   el otro sigue vivo (solo error total si caen los dos).
 * - Dedupe por URL canónica; orden por fecha descendente.
 * - La FUENTE es SIEMPRE visible y enlaza al original (target=_blank,
 *   rel=noopener noreferrer).
 * - Badge «fuente única» cuando, tras el dedupe, un solo dominio cubre ese
 *   titular. Badge de idioma cuando la noticia no está en inglés.
 */
import { useEffect, useState } from 'react'
import { get } from '../api/client.js'
import { classify } from '../lib/sentiment.js'

/**
 * @typedef {Object} NewsItem Noticia ya normalizada (única forma que pinta la UI).
 * @property {string} headline - Titular.
 * @property {string} url - Enlace al artículo original.
 * @property {string} source - Nombre de la fuente (Finnhub) o dominio (GDELT).
 * @property {string} domain - Dominio real (derivado de la URL; clave del
 *   filtro de objetividad).
 * @property {number} ts - Fecha en ms epoch (0 si no se pudo parsear).
 * @property {string} api - 'Finnhub' | 'GDELT'.
 * @property {string} [summary] - Resumen (solo Finnhub).
 * @property {string} [language] - Idioma reportado (solo GDELT).
 * @property {number} [sentiment] - Tono GDELT (float).
 * @property {boolean} uniqueSource - true si solo 1 dominio cubre el titular.
 * @property {boolean} foreignLang - true si el idioma reportado no es inglés.
 */

/** Idiomas que consideramos "inglés" (GDELT reporta 'English'; otros 'en'/'eng'). */
const EN_LANGS = new Set(['en', 'eng', 'english'])

/**
 * Dominio de una URL sin `www.` (para el filtro de objetividad).
 * @param {string} url - URL del artículo.
 * @param {string} [fallback] - Valor si la URL no parsea (ej. source de GDELT).
 * @returns {string} Dominio en minúsculas, o el fallback.
 */
export function domainOf(url, fallback = '') {
  try {
    return new URL(url).hostname.replace(/^www\./, '').toLowerCase()
  } catch {
    return String(fallback).toLowerCase()
  }
}

/**
 * URL canónica para dedupe: sin protocolo, sin barra final, en minúsculas.
 * @param {string} url
 * @returns {string}
 */
export function canonicalUrl(url) {
  return String(url || '')
    .trim()
    .replace(/^https?:\/\//i, '')
    .replace(/\/+$/, '')
    .toLowerCase()
}

/**
 * Parsea el `seendate` de GDELT (`YYYYMMDDTHHMMSSZ`) o cualquier fecha
 * ISO-parseable a ms epoch.
 * @param {string|null|undefined} s - Fecha en string.
 * @returns {number} ms epoch, o 0 si no parsea.
 */
export function parseGdeltDate(s) {
  if (!s) return 0
  const m = /^(\d{4})(\d{2})(\d{2})T?(\d{2})?(\d{2})?(\d{2})?/.exec(String(s).trim())
  if (m) {
    const iso = `${m[1]}-${m[2]}-${m[3]}T${m[4] || '00'}:${m[5] || '00'}:${m[6] || '00'}Z`
    const t = Date.parse(iso)
    if (Number.isFinite(t)) return t
  }
  const t = Date.parse(String(s))
  return Number.isFinite(t) ? t : 0
}

/**
 * Normaliza las DOS formas de noticia del server a una sola, deduplica por
 * URL canónica, marca «fuente única» por titular y ordena por fecha desc.
 *
 * @param {Array<Object>} finnhubItems - Respuesta cruda de /api/news/<ticker>
 *   (Finnhub: headline, source, url, datetime en epoch segundos, summary).
 * @param {Array<Object>} gdeltItems - Respuesta de /api/news/gdelt/<company>
 *   (headline, url, source=dominio, datetime=seendate string, language,
 *   sentiment, source_api).
 * @returns {NewsItem[]} Lista única, deduplicada y ordenada (fecha desc).
 */
export function normalizeNews(finnhubItems, gdeltItems) {
  /** @type {Array<Omit<NewsItem,'uniqueSource'|'foreignLang'>>} */
  const raw = []

  for (const a of Array.isArray(finnhubItems) ? finnhubItems : []) {
    if (!a || !a.headline || !a.url) continue
    raw.push({
      headline: String(a.headline),
      url: String(a.url),
      source: String(a.source || ''),
      domain: domainOf(a.url, a.source),
      ts: Number.isFinite(Number(a.datetime)) ? Number(a.datetime) * 1000 : 0,
      api: 'Finnhub',
      summary: a.summary ? String(a.summary) : undefined,
    })
  }

  for (const a of Array.isArray(gdeltItems) ? gdeltItems : []) {
    if (!a || !a.headline || !a.url) continue
    raw.push({
      headline: String(a.headline),
      url: String(a.url),
      source: String(a.source || ''),
      domain: domainOf(a.url, a.source),
      ts: parseGdeltDate(a.datetime),
      api: 'GDELT',
      language: a.language ? String(a.language) : undefined,
      sentiment: Number.isFinite(Number(a.sentiment)) ? Number(a.sentiment) : undefined,
    })
  }

  // Dedupe por URL canónica (gana la primera aparición: Finnhub trae summary).
  const seen = new Set()
  const deduped = []
  for (const it of raw) {
    const key = canonicalUrl(it.url)
    if (seen.has(key)) continue
    seen.add(key)
    deduped.push(it)
  }

  // ¿Cuántos dominios cubren cada titular tras el dedupe?
  const domainsByHeadline = new Map()
  for (const it of deduped) {
    const hk = it.headline.trim().toLowerCase()
    if (!domainsByHeadline.has(hk)) domainsByHeadline.set(hk, new Set())
    domainsByHeadline.get(hk).add(it.domain)
  }

  return deduped
    .map((it) => ({
      ...it,
      uniqueSource: (domainsByHeadline.get(it.headline.trim().toLowerCase())?.size ?? 1) === 1,
      foreignLang: Boolean(it.language) && !EN_LANGS.has(String(it.language).toLowerCase()),
    }))
    .sort((a, b) => b.ts - a.ts)
}

/**
 * Fecha corta en español para la tarjeta.
 * @param {number} ts - ms epoch.
 * @returns {string}
 */
function fmtDate(ts) {
  if (!ts) return ''
  try {
    return new Date(ts).toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' })
  } catch {
    return new Date(ts).toISOString().slice(0, 10)
  }
}

const SENT_COLOR = { pos: 'var(--up)', neg: 'var(--down)', neutral: 'var(--border)' }

const S = {
  form: { display: 'flex', gap: 8, marginBottom: 14 },
  input: {
    flex: '0 1 220px', padding: '8px 12px', borderRadius: 10, font: 'inherit',
    background: 'var(--panel)', border: '1px solid var(--border)', color: 'var(--text)',
  },
  btn: {
    padding: '8px 16px', borderRadius: 10, font: 'inherit', cursor: 'pointer',
    background: 'rgba(0,224,255,0.08)', border: '1px solid var(--border-hi)', color: 'var(--neon)',
  },
  list: { display: 'flex', flexDirection: 'column', gap: 10 },
  card: { borderLeft: '3px solid var(--border)' },
  meta: {
    display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 8,
    fontSize: 11.5, color: 'var(--text-dim)', marginBottom: 6,
  },
  source: { color: 'var(--neon)', textDecoration: 'none', fontWeight: 600 },
  api: { color: 'var(--text-faint)', fontSize: 10.5, letterSpacing: 0.4 },
  badge: {
    fontSize: 10.5, padding: '2px 8px', borderRadius: 999,
    border: '1px solid rgba(255,179,0,0.45)', color: 'var(--warn)',
    background: 'rgba(255,179,0,0.08)',
  },
  badgeLang: {
    fontSize: 10.5, padding: '2px 8px', borderRadius: 999,
    border: '1px solid rgba(142,90,255,0.45)', color: 'var(--violet)',
    background: 'rgba(142,90,255,0.08)',
  },
  headline: { color: 'var(--text)', textDecoration: 'none', fontSize: 13.5, fontWeight: 600, lineHeight: 1.35 },
  summary: { margin: '6px 0 0', fontSize: 12, color: 'var(--text-dim)', lineHeight: 1.45 },
  warn: { fontSize: 12, color: 'var(--warn)', marginBottom: 10 },
  empty: { color: 'var(--text-faint)', fontSize: 13, textAlign: 'center', padding: 30 },
}

/**
 * Panel de noticias: input de ticker/empresa (default NVDA), Finnhub + GDELT
 * en paralelo, tarjetas con fuente siempre visible.
 * @returns {import('react').JSX.Element}
 */
export default function NewsPanel() {
  const [input, setInput] = useState('NVDA')
  const [query, setQuery] = useState('NVDA')
  const [state, setState] = useState(
    /** @type {{status:'loading'|'ok'|'error', items:NewsItem[], failed:string[]}} */
    ({ status: 'loading', items: [], failed: [] }),
  )

  useEffect(() => {
    let alive = true
    setState({ status: 'loading', items: [], failed: [] })
    const q = encodeURIComponent(query)
    Promise.allSettled([get(`/api/news/${q}`), get(`/api/news/gdelt/${q}`)]).then(([fh, gd]) => {
      if (!alive) return
      const failed = []
      if (fh.status === 'rejected') failed.push('Finnhub')
      if (gd.status === 'rejected') failed.push('GDELT')
      if (failed.length === 2) {
        setState({ status: 'error', items: [], failed })
        return
      }
      const items = normalizeNews(
        fh.status === 'fulfilled' ? fh.value : [],
        gd.status === 'fulfilled' ? gd.value : [],
      )
      setState({ status: 'ok', items, failed })
    })
    return () => { alive = false }
  }, [query])

  /** @param {import('react').FormEvent} e */
  const onSubmit = (e) => {
    e.preventDefault()
    const t = input.trim()
    if (t) setQuery(t)
  }

  return (
    <section aria-label="Noticias">
      <form style={S.form} onSubmit={onSubmit}>
        <input
          style={S.input}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ticker o empresa (ej. NVDA)"
          aria-label="Ticker o empresa"
        />
        <button type="submit" style={S.btn}>Buscar noticias</button>
      </form>

      {state.status === 'loading' && <div className="loading">Buscando noticias de {query}…</div>}

      {state.status === 'error' && (
        <div className="error-box">
          No se pudieron cargar las noticias de {query} (Finnhub y GDELT fallaron).
          Revisa la conexión e inténtalo de nuevo.
        </div>
      )}

      {state.status === 'ok' && (
        <>
          {state.failed.length === 1 && (
            <div style={S.warn}>
              ⚠ La fuente {state.failed[0]} no respondió — mostrando solo el resto.
            </div>
          )}
          {state.items.length === 0 ? (
            <div style={S.empty}>Sin noticias recientes para «{query}».</div>
          ) : (
            <div style={S.list}>
              {state.items.map((it) => (
                <article
                  key={canonicalUrl(it.url)}
                  className="panel-card"
                  style={{ ...S.card, borderLeftColor: SENT_COLOR[classify(it.headline)] }}
                >
                  <div style={S.meta}>
                    <a href={it.url} target="_blank" rel="noopener noreferrer" style={S.source}>
                      {it.domain || it.source || 'fuente desconocida'}
                    </a>
                    {it.ts > 0 && <span>{fmtDate(it.ts)}</span>}
                    <span style={S.api}>{it.api}</span>
                    {it.uniqueSource && (
                      <span style={S.badge} title="Solo un dominio cubre este titular — contrástalo antes de confiar">
                        fuente única
                      </span>
                    )}
                    {it.foreignLang && (
                      <span style={S.badgeLang} title="Noticia en otro idioma">{it.language}</span>
                    )}
                  </div>
                  <a href={it.url} target="_blank" rel="noopener noreferrer" style={S.headline}>
                    {it.headline}
                  </a>
                  {it.summary && <p style={S.summary}>{it.summary}</p>}
                </article>
              ))}
            </div>
          )}
        </>
      )}
    </section>
  )
}
