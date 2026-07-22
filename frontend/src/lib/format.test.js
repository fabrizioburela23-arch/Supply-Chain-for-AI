import { describe, it, expect } from 'vitest';
import { fmtUsd, fmtPct, fmtBig } from './format.js';

describe('fmtUsd', () => {
  it('cero', () => {
    expect(fmtUsd(0)).toBe('$0');
  });

  it('negativos', () => {
    expect(fmtUsd(-500)).toBe('-$500');
    expect(fmtUsd(-1234.56)).toBe('-$1,234.56');
  });

  it('miles con separador', () => {
    expect(fmtUsd(1234)).toBe('$1,234');
    expect(fmtUsd(987654.321)).toBe('$987,654.32');
  });

  it('millones y billones con separador (sin sufijo)', () => {
    expect(fmtUsd(2500000)).toBe('$2,500,000');
    expect(fmtUsd(3400000000)).toBe('$3,400,000,000');
  });

  it('null/undefined/no numérico → $0 (igual que el clásico)', () => {
    expect(fmtUsd(null)).toBe('$0');
    expect(fmtUsd(undefined)).toBe('$0');
    expect(fmtUsd('abc')).toBe('$0');
  });
});

describe('fmtPct', () => {
  it('cero lleva signo + (estilo growth del clásico)', () => {
    expect(fmtPct(0)).toBe('+0.0%');
  });

  it('positivos y negativos con 1 decimal', () => {
    expect(fmtPct(3.25)).toBe('+3.3%');
    expect(fmtPct(12)).toBe('+12.0%');
    expect(fmtPct(-1.15)).toBe('-1.1%');
    expect(fmtPct(-40)).toBe('-40.0%');
  });

  it('null/undefined/NaN → —', () => {
    expect(fmtPct(null)).toBe('—');
    expect(fmtPct(undefined)).toBe('—');
    expect(fmtPct(NaN)).toBe('—');
  });
});

describe('fmtBig', () => {
  it('cero', () => {
    expect(fmtBig(0)).toBe('$0');
  });

  it('valores pequeños (< 1K) redondeados', () => {
    expect(fmtBig(980)).toBe('$980');
    expect(fmtBig(999.6)).toBe('$1000');
  });

  it('miles → K', () => {
    expect(fmtBig(1500)).toBe('$1.5K');
    expect(fmtBig(999999)).toBe('$1000.0K');
  });

  it('millones → M', () => {
    expect(fmtBig(5000000)).toBe('$5.0M');
    expect(fmtBig(750250000)).toBe('$750.3M');
  });

  it('billones (miles de millones) → B, estilo $1.2B', () => {
    expect(fmtBig(1200000000)).toBe('$1.2B');
    expect(fmtBig(87e9)).toBe('$87.0B');
  });

  it('trillones (billones ES) → T, estilo $3.4T', () => {
    expect(fmtBig(3.4e12)).toBe('$3.4T');
    expect(fmtBig(1e12)).toBe('$1.0T');
  });

  it('negativos con sufijo', () => {
    expect(fmtBig(-2100000000)).toBe('-$2.1B');
    expect(fmtBig(-4500)).toBe('-$4.5K');
  });

  it('null/undefined/NaN → —', () => {
    expect(fmtBig(null)).toBe('—');
    expect(fmtBig(undefined)).toBe('—');
    expect(fmtBig(NaN)).toBe('—');
  });
});
