/**
 * MarketPanel — cotizaciones vivas (migración de `renderMarket` del clásico).
 *
 * Fuente: `POST /api/quotes/live` (server.py ~línea 3405). Request:
 * `{ tickers: ["NVDA", ...] }`. Response: `{ TICKER: {close, prev, live, pct, vol} }`
 * — convención del clásico `MKT.quotes[t] = {close, prev, live}`; NUNCA `q.c`/`q.pc`.
 *
 * Refresca cada 30 s y limpia el intervalo al desmontar.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { post } from '../api/client.js';
import { fmtUsd, fmtPct } from '../lib/format.js';

/** Tickers demo (lista corta; luego vendrá del universo/portafolio). */
export const DEMO_TICKERS = ['NVDA', 'TSM', 'ASML', 'AMD', 'MSFT', 'AMZN'];

/** Intervalo de refresco en ms. */
const REFRESH_MS = 30000;

/**
 * Cambio porcentual de una cotización. Usa `pct` del server si viene;
 * si no, lo deriva de live/prev (misma fórmula que el server).
 *
 * @param {{close?: number, prev?: number, live?: number, pct?: number}} q
 * @returns {number|null} Porcentaje (ej. -1.23) o null si no hay datos.
 */
export function quotePct(q) {
  if (!q) return null;
  if (typeof q.pct === 'number' && isFinite(q.pct)) return q.pct;
  const live = Number(q.live ?? q.close);
  const prev = Number(q.prev);
  if (!isFinite(live) || !isFinite(prev) || !prev) return null;
  return ((live - prev) / prev) * 100;
}

/**
 * Panel de mercado con tabla de cotizaciones vivas.
 *
 * @param {{tickers?: string[]}} props - Lista de tickers (default: DEMO_TICKERS).
 * @returns {JSX.Element}
 */
export default function MarketPanel({ tickers = DEMO_TICKERS } = {}) {
  const [quotes, setQuotes] = useState(/** @type {Object<string, any>|null} */ (null));
  const [error, setError] = useState(/** @type {string|null} */ (null));
  const mounted = useRef(true);

  const load = useCallback(async () => {
    try {
      const data = await post('/api/quotes/live', { tickers });
      if (!mounted.current) return;
      setQuotes(data && typeof data === 'object' ? data : {});
      setError(null);
    } catch (e) {
      if (!mounted.current) return;
      setError(e && e.message ? e.message : 'Error de red');
    }
  }, [tickers]);

  useEffect(() => {
    mounted.current = true;
    load();
    const timer = setInterval(load, REFRESH_MS);
    return () => {
      mounted.current = false;
      clearInterval(timer);
    };
  }, [load]);

  if (error && !quotes) {
    return (
      <div className="panel-card">
        <h3>Mercado</h3>
        <div className="error-box" role="alert">
          No se pudieron cargar las cotizaciones: {error}
        </div>
      </div>
    );
  }

  if (!quotes) {
    return (
      <div className="panel-card">
        <h3>Mercado</h3>
        <div className="loading">Cargando cotizaciones…</div>
      </div>
    );
  }

  return (
    <div className="panel-card">
      <h3>Mercado</h3>
      {error && (
        <div className="error-box" role="alert">
          Último refresco falló: {error} (mostrando datos previos)
        </div>
      )}
      <table className="market-table">
        <thead>
          <tr>
            <th style={{ textAlign: 'left' }}>Ticker</th>
            <th style={{ textAlign: 'right' }}>Precio</th>
            <th style={{ textAlign: 'right' }}>Cambio</th>
          </tr>
        </thead>
        <tbody>
          {tickers.map((t) => {
            const q = quotes[t];
            const pct = quotePct(q);
            const dir = pct == null ? '' : pct < 0 ? 'down' : 'up';
            const color = dir ? `var(--${dir})` : undefined;
            const price = q ? Number(q.live ?? q.close) : null;
            return (
              <tr key={t}>
                <td>{t}</td>
                <td style={{ textAlign: 'right' }}>
                  {price != null && isFinite(price) ? fmtUsd(price) : '—'}
                </td>
                <td
                  style={{ textAlign: 'right', color }}
                  className={dir ? `pct-${dir}` : undefined}
                >
                  {fmtPct(pct)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
