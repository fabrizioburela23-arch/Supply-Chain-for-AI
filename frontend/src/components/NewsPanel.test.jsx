/**
 * Tests de NewsPanel — el ÚNICO renderer de noticias.
 * fetch SIEMPRE mockeado (vi.stubGlobal) — nunca red real.
 */
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, afterEach } from 'vitest'
import NewsPanel, { normalizeNews, parseGdeltDate, canonicalUrl, domainOf } from './NewsPanel.jsx'

// ── Fixtures: las DOS formas reales del server ───────────────────────────────

/** Forma Finnhub cruda (/api/news/<ticker>): datetime en EPOCH SEGUNDOS. */
const FINNHUB = [
  {
    headline: 'NVDA beats earnings expectations',
    source: 'Reuters',
    url: 'https://www.reuters.com/tech/nvda-beats',
    datetime: 1752834000, // 2025-07-18 ~ (epoch segundos)
    summary: 'Nvidia superó las expectativas del trimestre.',
  },
  {
    headline: 'HBM shortage looms over AI chips',
    source: 'CNBC',
    url: 'https://cnbc.com/hbm-shortage',
    datetime: 1752600000,
  },
]

/** Forma GDELT (/api/news/gdelt/<company>): datetime = seendate string. */
const GDELT = [
  {
    headline: 'Nvidia sube en bolsa tras resultados',
    url: 'https://elpais.com/economia/nvidia-sube',
    source: 'elpais.com',
    datetime: '20260720T083000Z',
    language: 'Spanish',
    sentiment: 2.1,
    source_api: 'GDELT',
  },
  {
    // DUPLICADO por URL del primer artículo Finnhub (debe deduplicarse)
    headline: 'NVDA beats earnings expectations',
    url: 'https://www.reuters.com/tech/nvda-beats',
    source: 'reuters.com',
    datetime: '20260718T120000Z',
    language: 'English',
    sentiment: 3.0,
    source_api: 'GDELT',
  },
  {
    // MISMO titular que el de CNBC pero en OTRO dominio → NO «fuente única»
    headline: 'HBM shortage looms over AI chips',
    url: 'https://ft.com/hbm-shortage',
    source: 'ft.com',
    datetime: '20260719T090000Z',
    language: 'English',
    sentiment: -1.4,
    source_api: 'GDELT',
  },
]

// ── Helpers de mock de fetch (contrato de src/api/client.js: ok/status/text) ─

const okRes = (data) =>
  Promise.resolve({ ok: true, status: 200, text: () => Promise.resolve(JSON.stringify(data)) })
const errRes = (status = 500) =>
  Promise.resolve({ ok: false, status, text: () => Promise.resolve('{"error":"boom"}') })

/** Mockea fetch: gdelt → gdeltData, resto (/api/news/*) → finnhubData. */
function stubFetch({ finnhub = FINNHUB, gdelt = GDELT, finnhubFails = false, gdeltFails = false } = {}) {
  const fn = vi.fn((url) => {
    const u = String(url)
    if (u.startsWith('/api/news/gdelt/')) return gdeltFails ? errRes() : okRes(gdelt)
    if (u.startsWith('/api/news/')) return finnhubFails ? errRes() : okRes(finnhub)
    return errRes(404)
  })
  vi.stubGlobal('fetch', fn)
  return fn
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

// ── normalizeNews (lógica pura, tests de tabla) ──────────────────────────────

describe('normalizeNews', () => {
  it('normaliza ambas formas: epoch segundos (Finnhub) y seendate string (GDELT)', () => {
    const items = normalizeNews(FINNHUB, GDELT)
    const fh = items.find((i) => i.api === 'Finnhub' && i.headline.startsWith('NVDA beats'))
    const gd = items.find((i) => i.api === 'GDELT' && i.headline.startsWith('Nvidia sube'))
    expect(fh).toBeTruthy()
    expect(gd).toBeTruthy()
    // Finnhub: epoch segundos → ms
    expect(fh.ts).toBe(1752834000 * 1000)
    // GDELT: '20260720T083000Z' → ms epoch UTC
    expect(gd.ts).toBe(Date.parse('2026-07-20T08:30:00Z'))
    // Campos propios de cada forma sobreviven
    expect(fh.summary).toMatch(/expectativas/)
    expect(gd.language).toBe('Spanish')
    expect(gd.sentiment).toBeCloseTo(2.1)
  })

  it('deduplica por URL canónica (gana la primera aparición, Finnhub)', () => {
    const items = normalizeNews(FINNHUB, GDELT)
    const beats = items.filter((i) => i.headline === 'NVDA beats earnings expectations')
    expect(beats).toHaveLength(1)
    expect(beats[0].api).toBe('Finnhub') // la de Finnhub gana (trae summary)
  })

  it('ordena por fecha descendente', () => {
    const items = normalizeNews(FINNHUB, GDELT)
    const ts = items.map((i) => i.ts)
    expect(ts).toEqual([...ts].sort((a, b) => b - a))
  })

  it('marca «fuente única» solo cuando 1 dominio cubre el titular', () => {
    const items = normalizeNews(FINNHUB, GDELT)
    const solo = items.find((i) => i.headline.startsWith('Nvidia sube'))
    expect(solo.uniqueSource).toBe(true)
    // El titular de HBM lo cubren cnbc.com Y ft.com → NO es fuente única
    for (const i of items.filter((x) => x.headline.startsWith('HBM shortage'))) {
      expect(i.uniqueSource).toBe(false)
    }
  })

  it('marca idioma extranjero solo si no es inglés', () => {
    const items = normalizeNews([], GDELT)
    expect(items.find((i) => i.language === 'Spanish').foreignLang).toBe(true)
    expect(items.find((i) => i.language === 'English').foreignLang).toBe(false)
  })

  it('descarta entradas sin headline o sin url y tolera arrays no válidos', () => {
    expect(normalizeNews(null, undefined)).toEqual([])
    const items = normalizeNews([{ headline: '', url: 'https://x.com/a' }, { headline: 'ok' }], [])
    expect(items).toEqual([])
  })
})

describe('helpers puros', () => {
  it('parseGdeltDate: seendate compacto, ISO y basura', () => {
    expect(parseGdeltDate('20260720T083000Z')).toBe(Date.parse('2026-07-20T08:30:00Z'))
    expect(parseGdeltDate('2026-07-20T08:30:00Z')).toBe(Date.parse('2026-07-20T08:30:00Z'))
    expect(parseGdeltDate('')).toBe(0)
    expect(parseGdeltDate('no-es-fecha')).toBe(0)
  })

  it('canonicalUrl iguala http/https, barra final y mayúsculas', () => {
    expect(canonicalUrl('https://Reuters.com/a/')).toBe(canonicalUrl('http://reuters.com/a'))
  })

  it('domainOf extrae dominio sin www y usa fallback si no parsea', () => {
    expect(domainOf('https://www.reuters.com/tech/x')).toBe('reuters.com')
    expect(domainOf('no-url', 'elpais.com')).toBe('elpais.com')
  })
})

// ── Componente (RTL + jsdom, fetch mockeado) ─────────────────────────────────

describe('<NewsPanel />', () => {
  it('pide ambos endpoints en paralelo para NVDA (default) y pinta tarjetas', async () => {
    const fetchMock = stubFetch()
    render(<NewsPanel />)
    expect(document.querySelector('.loading')).toBeInTheDocument()

    await waitFor(() =>
      expect(screen.getByText('NVDA beats earnings expectations')).toBeInTheDocument(),
    )
    const urls = fetchMock.mock.calls.map((c) => String(c[0]))
    expect(urls).toContain('/api/news/NVDA')
    expect(urls).toContain('/api/news/gdelt/NVDA')
    expect(screen.getByText('Nvidia sube en bolsa tras resultados')).toBeInTheDocument()
  })

  it('la fuente es siempre visible y enlaza al original con rel=noopener', async () => {
    stubFetch()
    render(<NewsPanel />)
    await waitFor(() => expect(screen.getByText('elpais.com')).toBeInTheDocument())

    const sourceLink = screen.getByRole('link', { name: 'elpais.com' })
    expect(sourceLink).toHaveAttribute('href', 'https://elpais.com/economia/nvidia-sube')
    expect(sourceLink).toHaveAttribute('target', '_blank')
    expect(sourceLink.getAttribute('rel')).toContain('noopener')

    const headlineLink = screen.getByRole('link', { name: 'Nvidia sube en bolsa tras resultados' })
    expect(headlineLink).toHaveAttribute('href', 'https://elpais.com/economia/nvidia-sube')
    expect(headlineLink.getAttribute('rel')).toContain('noopener')
  })

  it('deduplica por URL: el artículo repetido en ambos feeds sale UNA vez', async () => {
    stubFetch()
    render(<NewsPanel />)
    await waitFor(() =>
      expect(screen.getAllByText('NVDA beats earnings expectations')).toHaveLength(1),
    )
  })

  it('muestra badges: «fuente única» y de idioma no inglés', async () => {
    stubFetch()
    render(<NewsPanel />)
    await waitFor(() => expect(screen.getByText('Nvidia sube en bolsa tras resultados')).toBeInTheDocument())
    // 4 tarjetas tras dedupe; HBM está cubierto por 2 dominios → 2 badges
    expect(screen.getAllByText('fuente única')).toHaveLength(2)
    expect(screen.getByText('Spanish')).toBeInTheDocument()
    expect(screen.queryByText('English')).not.toBeInTheDocument()
  })

  it('si Finnhub cae, el panel sigue vivo con GDELT (sin .error-box)', async () => {
    stubFetch({ finnhubFails: true })
    render(<NewsPanel />)
    await waitFor(() =>
      expect(screen.getByText('Nvidia sube en bolsa tras resultados')).toBeInTheDocument(),
    )
    expect(document.querySelector('.error-box')).toBeNull()
    expect(screen.getByText(/Finnhub no respondió/)).toBeInTheDocument()
  })

  it('si GDELT cae, el panel sigue vivo con Finnhub', async () => {
    stubFetch({ gdeltFails: true })
    render(<NewsPanel />)
    await waitFor(() =>
      expect(screen.getByText('NVDA beats earnings expectations')).toBeInTheDocument(),
    )
    expect(document.querySelector('.error-box')).toBeNull()
  })

  it('solo si caen AMBOS endpoints muestra .error-box', async () => {
    stubFetch({ finnhubFails: true, gdeltFails: true })
    render(<NewsPanel />)
    await waitFor(() => expect(document.querySelector('.error-box')).toBeInTheDocument())
    expect(screen.getByText(/Finnhub y GDELT fallaron/)).toBeInTheDocument()
  })

  it('buscar otro ticker dispara nuevas peticiones codificadas', async () => {
    const fetchMock = stubFetch()
    render(<NewsPanel />)
    await waitFor(() => expect(screen.getByText('NVDA beats earnings expectations')).toBeInTheDocument())

    fireEvent.change(screen.getByLabelText('Ticker o empresa'), { target: { value: 'Taiwan Semiconductor' } })
    fireEvent.click(screen.getByRole('button', { name: 'Buscar noticias' }))

    await waitFor(() => {
      const urls = fetchMock.mock.calls.map((c) => String(c[0]))
      expect(urls).toContain('/api/news/Taiwan%20Semiconductor')
      expect(urls).toContain('/api/news/gdelt/Taiwan%20Semiconductor')
    })
  })

  it('ambos endpoints OK pero vacíos → mensaje de "sin noticias", no error', async () => {
    stubFetch({ finnhub: [], gdelt: [] })
    render(<NewsPanel />)
    await waitFor(() => expect(screen.getByText(/Sin noticias recientes/)).toBeInTheDocument())
    expect(document.querySelector('.error-box')).toBeNull()
  })
})
