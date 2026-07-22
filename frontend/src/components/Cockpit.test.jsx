/**
 * Tests de Cockpit — la Cabina de Bixby (pantalla inicial).
 * fetch SIEMPRE mockeado (vi.stubGlobal) — nunca red real.
 * El parser KHIPU se mockea (vi.mock) para no depender de src/lib/khipu.js.
 */
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, afterEach } from 'vitest'
import Cockpit from './Cockpit.jsx'
import { tryParse } from '../lib/khipu.js'

vi.mock('../lib/khipu.js', () => ({
  tryParse: vi.fn(() => null),
}))

// ── Fixture: respuesta de POST /api/matrix/insights ──────────────────────────

const INSIGHTS = {
  available: true,
  insights: [
    { kind: 'riesgo', title: 'Concentración extrema en TSMC', detail: 'El 82% del cómputo IA pasa por un solo fab.' },
    { kind: 'oportunidad', title: 'Samsung gana terreno en HBM', detail: 'Capacidad libre ante el cuello de SK Hynix.' },
    { kind: 'estructura', title: 'ASML es puente único', detail: 'Sin sustituto en litografía EUV.' },
  ],
  factors: [
    { label: 'Escasez HBM', severity: 7, members: ['nvidia', 'skhynix'] },
    { label: 'Tensión Taiwán', severity: 8, members: ['tsmc'] },
  ],
  cascade: [
    { id: 'tsmc', name: 'TSMC', impact: 92 },
    { id: 'nvidia', name: 'Nvidia', impact: 61 },
  ],
  trigger: 'Caída de TSMC',
  affected: 214,
  model: 'plantilla',
}

// ── Helpers de mock de fetch (contrato de src/api/client.js: ok/status/text) ─

const okRes = (data) =>
  Promise.resolve({ ok: true, status: 200, text: () => Promise.resolve(JSON.stringify(data)) })
const errRes = (status = 503) =>
  Promise.resolve({ ok: false, status, text: () => Promise.resolve('{"error":"down"}') })

/** Mockea fetch: /api/matrix/insights → data (o error si fails). */
function stubFetch({ data = INSIGHTS, fails = false } = {}) {
  const fn = vi.fn((url) => {
    if (String(url) === '/api/matrix/insights') return fails ? errRes() : okRes(data)
    return errRes(404)
  })
  vi.stubGlobal('fetch', fn)
  return fn
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.clearAllMocks()
})

// ── Hero ─────────────────────────────────────────────────────────────────────

describe('<Cockpit /> — hero', () => {
  it('pinta el saludo de Bixby y los 4 chips de ejemplo', async () => {
    stubFetch()
    render(<Cockpit />)
    expect(screen.getByText('Soy Bixby. Pregúntame lo que sea.')).toBeInTheDocument()
    for (const q of ['desármame Nvidia', '¿qué pasa si cae TSMC?', 'muéstrame oportunidades', 'compara Nvidia y AMD']) {
      expect(screen.getByRole('button', { name: new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')) })).toBeInTheDocument()
    }
    // El disclaimer fijo SIEMPRE está.
    expect(screen.getByText('Análisis, no asesoría financiera.')).toBeInTheDocument()
    await waitFor(() => expect(document.querySelector('.loading')).toBeNull())
  })

  it('clic en un chip RELLENA el input (no envía nada solo)', async () => {
    stubFetch()
    render(<Cockpit />)
    fireEvent.click(screen.getByRole('button', { name: /desármame Nvidia/ }))
    expect(screen.getByLabelText('Pregunta a Bixby')).toHaveValue('desármame Nvidia')
    // Rellenar NO dispara el parser ni ninguna respuesta.
    expect(tryParse).not.toHaveBeenCalled()
    await waitFor(() => expect(document.querySelector('.loading')).toBeNull())
  })
})

// ── Banner del hipergrafo ────────────────────────────────────────────────────

describe('<Cockpit /> — banner del hipergrafo', () => {
  it('POST a /api/matrix/insights con {lang:es, tier:fast} y pinta las tarjetas del mock', async () => {
    const fetchMock = stubFetch()
    render(<Cockpit />)
    expect(document.querySelector('.loading')).toBeInTheDocument()

    await waitFor(() => expect(screen.getByText('Samsung gana terreno en HBM')).toBeInTheDocument())
    expect(screen.getByText('ASML es puente único')).toBeInTheDocument()
    // Top insight destacado (el primero aparece en el titular Y en su tarjeta).
    expect(screen.getAllByText('Concentración extrema en TSMC').length).toBeGreaterThanOrEqual(1)

    // Factores activos como chips.
    expect(screen.getByText(/Escasez HBM/)).toBeInTheDocument()
    expect(screen.getByText(/Tensión Taiwán/)).toBeInTheDocument()

    // Cascada con nombres e impactos.
    expect(screen.getByText('TSMC')).toBeInTheDocument()
    expect(screen.getByText('92%')).toBeInTheDocument()

    // El request fue el correcto.
    const call = fetchMock.mock.calls.find((c) => String(c[0]) === '/api/matrix/insights')
    expect(call).toBeTruthy()
    expect(call[1].method).toBe('POST')
    expect(JSON.parse(call[1].body)).toEqual({ lang: 'es', tier: 'fast' })
  })

  it('colorea el borde por kind: riesgo=--down, oportunidad=--up, estructura=--neon', async () => {
    stubFetch()
    render(<Cockpit />)
    await waitFor(() => expect(screen.getByText('Samsung gana terreno en HBM')).toBeInTheDocument())
    const cardOf = (title) => screen.getByText(title).closest('article')
    expect(cardOf('Concentración extrema en TSMC')).toHaveStyle({ borderLeftColor: 'var(--down)' })
    expect(cardOf('Samsung gana terreno en HBM')).toHaveStyle({ borderLeftColor: 'var(--up)' })
    expect(cardOf('ASML es puente único')).toHaveStyle({ borderLeftColor: 'var(--neon)' })
  })

  it('available:false → NO pinta el banner y NO muestra error (silencioso)', async () => {
    stubFetch({ data: { available: false } })
    render(<Cockpit />)
    await waitFor(() => expect(document.querySelector('.loading')).toBeNull())
    expect(screen.queryByText(/hipergrafo/)).not.toBeInTheDocument()
    expect(document.querySelector('.error-box')).toBeNull()
  })

  it('endpoint caído (HTTP 503) → silencioso: ni banner ni error', async () => {
    stubFetch({ fails: true })
    render(<Cockpit />)
    await waitFor(() => expect(document.querySelector('.loading')).toBeNull())
    expect(screen.queryByText(/hipergrafo/)).not.toBeInTheDocument()
    expect(document.querySelector('.error-box')).toBeNull()
    // El hero sigue intacto.
    expect(screen.getByText('Soy Bixby. Pregúntame lo que sea.')).toBeInTheDocument()
  })
})

// ── Barra de entrada: KHIPU primero, IA después ──────────────────────────────

describe('<Cockpit /> — envío', () => {
  it('comando KHIPU válido → panel «Comando KHIPU» con el parseo formateado', async () => {
    stubFetch()
    tryParse.mockReturnValueOnce({
      cmd: 'DES',
      id: 'nvidia',
      label: 'NVIDIA',
      answer: 'Abriendo ficha de NVIDIA.',
      actions: [{ type: 'second_brain', arg: 'nvidia' }],
    })
    render(<Cockpit />)

    fireEvent.change(screen.getByLabelText('Pregunta a Bixby'), { target: { value: 'NVDA DES' } })
    fireEvent.click(screen.getByRole('button', { name: 'Enviar' }))

    expect(tryParse).toHaveBeenCalledWith('NVDA DES')
    expect(screen.getByText(/Comando KHIPU/)).toBeInTheDocument()
    expect(screen.getByText('Abriendo ficha de NVIDIA.')).toBeInTheDocument()
    // El objeto parseado se muestra formateado.
    expect(screen.getByText(/"cmd": "DES"/)).toBeInTheDocument()
    expect(screen.getByText(/"second_brain"/)).toBeInTheDocument()
    await waitFor(() => expect(document.querySelector('.loading')).toBeNull())
  })

  it('texto que NO es comando → aviso de IA conversacional pendiente (sin llamadas de IA)', async () => {
    const fetchMock = stubFetch()
    tryParse.mockReturnValueOnce(null)
    render(<Cockpit />)

    fireEvent.change(screen.getByLabelText('Pregunta a Bixby'), { target: { value: 'hola bixby' } })
    fireEvent.click(screen.getByRole('button', { name: 'Enviar' }))

    expect(tryParse).toHaveBeenCalledWith('hola bixby')
    expect(
      screen.getByText('IA conversacional: llega en la siguiente oleada de la migración.'),
    ).toBeInTheDocument()
    // NINGÚN endpoint de IA fue llamado: solo el de insights.
    await waitFor(() => expect(document.querySelector('.loading')).toBeNull())
    const urls = fetchMock.mock.calls.map((c) => String(c[0]))
    expect(urls.every((u) => u === '/api/matrix/insights')).toBe(true)
  })

  it('envío vacío no hace nada', async () => {
    stubFetch()
    render(<Cockpit />)
    fireEvent.click(screen.getByRole('button', { name: 'Enviar' }))
    expect(tryParse).not.toHaveBeenCalled()
    expect(screen.queryByText(/Comando KHIPU/)).not.toBeInTheDocument()
    await waitFor(() => expect(document.querySelector('.loading')).toBeNull())
  })
})
