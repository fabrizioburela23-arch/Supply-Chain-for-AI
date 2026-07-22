/**
 * Formateadores numéricos portados del clásico:
 * - fmtUsd: `engine/cockpit.js` (~línea 955) — monto USD con separador de miles.
 * - fmtPct: patrón "growth" de `_fundVal` en cockpit.js (~línea 680) — signo
 *   explícito + 1 decimal.
 * - fmtBig: números grandes estilo $1.2B / $3.4T (patrón de crypto.js /
 *   livesim.js / cvFmt de app.html, unificado sobre valores en USD crudos).
 */

/**
 * Formatea un monto en dólares con separador de miles (en-US) y hasta
 * 2 decimales. Igual que el clásico: valores no numéricos → '$0'.
 *
 * @param {number|null|undefined} v - Monto en USD.
 * @returns {string} Ej.: `$1,234.56`, `-$500`, `$0`.
 */
export function fmtUsd(v) {
  const n = Number(v) || 0;
  const abs = Math.abs(n).toLocaleString('en-US', { maximumFractionDigits: 2 });
  return (n < 0 ? '-$' : '$') + abs;
}

/**
 * Formatea un porcentaje con signo explícito y 1 decimal
 * (estilo "growth" del clásico: `(v>=0?'+':'') + v.toFixed(1) + '%'`).
 *
 * @param {number|null|undefined} v - Valor porcentual (ej. 3.25 → '+3.3%').
 * @returns {string} Ej.: `+3.3%`, `-1.2%`, `+0.0%`; '—' si es null/no numérico.
 */
export function fmtPct(v) {
  if (v == null || !isFinite(Number(v)) || (typeof v !== 'number' && String(v).trim() === '')) return '—';
  const n = Number(v);
  return (n >= 0 ? '+' : '') + n.toFixed(1) + '%';
}

/**
 * Formatea un número grande en USD con sufijo T/B/M/K, estilo del clásico
 * ($1.2B, $3.4T). Entrada en dólares crudos.
 *
 * @param {number|null|undefined} v - Monto en USD.
 * @returns {string} Ej.: `$3.4T`, `$1.2B`, `$5.0M`, `$1.5K`, `$980`, `-$2.1B`;
 *   '—' si es null/no numérico.
 */
export function fmtBig(v) {
  if (v == null || !isFinite(Number(v)) || (typeof v !== 'number' && String(v).trim() === '')) return '—';
  const n = Number(v);
  const sign = n < 0 ? '-' : '';
  const a = Math.abs(n);
  if (a >= 1e12) return sign + '$' + (a / 1e12).toFixed(1) + 'T';
  if (a >= 1e9) return sign + '$' + (a / 1e9).toFixed(1) + 'B';
  if (a >= 1e6) return sign + '$' + (a / 1e6).toFixed(1) + 'M';
  if (a >= 1e3) return sign + '$' + (a / 1e3).toFixed(1) + 'K';
  return sign + '$' + Math.round(a);
}
