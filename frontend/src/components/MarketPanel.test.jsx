/**
 * Tests de MarketPanel — fetch SIEMPRE mockeado (nunca red real).
 */
import { render, screen, waitFor } from '@testing-library/react';
import MarketPanel, { DEMO_TICKERS, quotePct } from './MarketPanel.jsx';

/** Respuesta demo con la forma REAL de /api/quotes/live: {close, prev, live, pct}. */
const QUOTES = {
  NVDA: { close: 180.5, prev: 175.0, live: 180.5, pct: 3.143, vol: 0 },
  TSM: { close: 210.0, prev: 215.0, live: 210.0, pct: -2.326, vol: 0 },
  ASML: { close: 900.25, prev: 900.25, live: 900.25, pct: 0, vol: 0 },
  AMD: { close: 150.1, prev: 148.0, live: 150.1, pct: 1.419, vol: 0 },
  MSFT: { close: 500.0, prev: 495.0, live: 500.0, pct: 1.01, vol: 0 },
  AMZN: { close: 230.0, prev: 231.0, live: 230.0, pct: -0.433, vol: 0 },
};

function okFetch(payload) {
  return vi.fn(async () => ({
    ok: true,
    status: 200,
    text: async () => JSON.stringify(payload),
  }));
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('MarketPanel', () => {
  it('muestra .loading y luego pinta filas con precios', async () => {
    vi.stubGlobal('fetch', okFetch(QUOTES));
    const { container } = render(<MarketPanel />);
    expect(container.querySelector('.loading')).toBeInTheDocument();

    await waitFor(() => expect(screen.getByText('NVDA')).toBeInTheDocument());
    expect(container.querySelector('.loading')).not.toBeInTheDocument();
    // Una fila por ticker demo
    expect(container.querySelectorAll('tbody tr')).toHaveLength(DEMO_TICKERS.length);
    // Precios formateados (fmtUsd)
    expect(screen.getByText('$180.5')).toBeInTheDocument();
    expect(screen.getByText('$900.25')).toBeInTheDocument();
    // Cambio % con signo
    expect(screen.getByText('+3.1%')).toBeInTheDocument();

    // Request con la forma real: POST /api/quotes/live {tickers: [...]}
    const [url, opts] = fetch.mock.calls[0];
    expect(url).toBe('/api/quotes/live');
    expect(opts.method).toBe('POST');
    expect(JSON.parse(opts.body)).toEqual({ tickers: DEMO_TICKERS });
  });

  it('cambio negativo usa la clase/color down; positivo usa up', async () => {
    vi.stubGlobal('fetch', okFetch(QUOTES));
    const { container } = render(<MarketPanel />);
    await waitFor(() => expect(screen.getByText('TSM')).toBeInTheDocument());

    const downCell = screen.getByText('-2.3%');
    expect(downCell).toHaveClass('pct-down');
    expect(downCell.style.color).toBe('var(--down)');

    const upCell = screen.getByText('+3.1%');
    expect(upCell).toHaveClass('pct-up');
    expect(upCell.style.color).toBe('var(--up)');

    expect(container.querySelectorAll('.pct-down')).toHaveLength(2); // TSM y AMZN
  });

  it('error de red muestra .error-box, no pantalla vacía', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('Failed to fetch'); }));
    const { container } = render(<MarketPanel />);

    await waitFor(() =>
      expect(container.querySelector('.error-box')).toBeInTheDocument()
    );
    expect(container.querySelector('.error-box').textContent)
      .toMatch(/cotizaciones/i);
    // El panel sigue teniendo contenido visible
    expect(screen.getByText('Mercado')).toBeInTheDocument();
  });

  it('refresca cada 30s y limpia el intervalo al desmontar', async () => {
    vi.stubGlobal('fetch', okFetch(QUOTES));
    vi.useFakeTimers();
    try {
      const { unmount } = render(<MarketPanel />);
      await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
      await vi.advanceTimersByTimeAsync(30000);
      expect(fetch).toHaveBeenCalledTimes(2);
      unmount();
      await vi.advanceTimersByTimeAsync(90000);
      expect(fetch).toHaveBeenCalledTimes(2);
    } finally {
      vi.useRealTimers();
    }
  });
});

describe('quotePct', () => {
  it.each([
    ['usa pct del server', { pct: -1.5, live: 10, prev: 10 }, -1.5],
    ['deriva de live/prev', { live: 110, prev: 100 }, 10],
    ['sin prev → null', { live: 110 }, null],
    ['prev 0 → null', { live: 110, prev: 0 }, null],
    ['sin quote → null', null, null],
  ])('%s', (_name, q, expected) => {
    expect(quotePct(q)).toBe(expected);
  });
});
