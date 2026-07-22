import { describe, it, expect } from 'vitest';
import { computeNRS, computeNRSBreakdown, buildDegreeMap, GEO_RISK } from './nrs';

/** Nodo base para tests de tabla: público, margen sano, país base. */
const BASE = { country: 'EEUU', margin: 0.25, preipo: false, growth: '🟢 +20%' };

describe('computeNRS', () => {
  it('devuelve SIEMPRE un número finito (nunca objeto)', () => {
    const casos = [
      [BASE, { degree: 4 }],
      [{}, undefined],
      [{ country: 'Marte' }, { degree: 0 }],
      [{ margin: -3.5, preipo: true, growth: '🔴 -40%' }, { degree: 999 }],
      [{ country: 'China', margin: null }, {}],
      [null, { degree: 2 }],
      [undefined, undefined],
    ];
    for (const [node, ctx] of casos) {
      const v = computeNRS(node, ctx);
      expect(typeof v).toBe('number');
      expect(Number.isFinite(v)).toBe(true);
      expect(Number.isInteger(v)).toBe(true);
    }
  });

  it('nodo ausente → 50 (paridad con el clásico)', () => {
    expect(computeNRS(null)).toBe(50);
    expect(computeNRS(undefined, { degree: 10 })).toBe(50);
  });

  it('acota el TOTAL a [0,100] aunque el término de margen se dispare', () => {
    // margin muy negativo (pre-revenue extremo): el término de margen NO
    // tiene tope (bug reproducido) pero el total sí clampa a 100.
    const preRevenue = { country: 'China', margin: -10, preipo: true, growth: '🔴' };
    const v = computeNRS(preRevenue, { degree: 50 });
    expect(v).toBe(100);
    // y nunca baja de 0 (la suma mínima real es positiva, pero el clamp existe)
    const minimo = computeNRS({ country: 'EEUU', margin: 0.4 }, { degree: 0 });
    expect(minimo).toBeGreaterThanOrEqual(0);
    expect(minimo).toBeLessThanOrEqual(100);
  });

  it('BUG documentado: margen negativo infla el término más allá de 20', () => {
    // margin = -0.5 → market = round((1 - (-1.25)) * 20) = 45 > 20.
    // Se verifica vía breakdown: el término Margen supera su max nominal.
    const b = computeNRSBreakdown({ ...BASE, margin: -0.5 }, { degree: 0 });
    const margen = b.terms.find((t) => t.key === 'Margen');
    expect(margen.val).toBe(45);
    expect(margen.val).toBeGreaterThan(margen.max);
  });

  it('país de alto riesgo puntúa más que país base, resto igual', () => {
    const ctx = { degree: 3 };
    const china = computeNRS({ ...BASE, country: 'China' }, ctx);
    const taiwan = computeNRS({ ...BASE, country: 'Taiwan' }, ctx);
    const eeuu = computeNRS({ ...BASE, country: 'EEUU' }, ctx);
    expect(china).toBeGreaterThan(eeuu);
    expect(taiwan).toBeGreaterThan(eeuu);
    // China también arrastra +6 de concentración (10 vs 4) además del geo
    expect(china - eeuu).toBe(GEO_RISK.China - GEO_RISK.EEUU + 6);
  });

  it('país desconocido usa el default 15 de geo', () => {
    const desconocido = computeNRS({ ...BASE, country: 'Atlantis' }, { degree: 0 });
    const eeuu = computeNRS(BASE, { degree: 0 });
    expect(desconocido - eeuu).toBe(15 - GEO_RISK.EEUU);
  });

  it('margin ausente usa 0.15 por defecto', () => {
    const sinMargen = computeNRS({ country: 'EEUU' }, { degree: 0 });
    const conDefault = computeNRS({ country: 'EEUU', margin: 0.15 }, { degree: 0 });
    expect(sinMargen).toBe(conDefault);
  });

  it('valores de tabla: términos suman como el clásico', () => {
    // geo 8 + chain min(25, 4*2.5)=10 + market round((1-0.25/0.4)*20)=8
    // + fundamental 0 + concentración 4 = 30
    expect(computeNRS(BASE, { degree: 4 })).toBe(30);
    // pre-IPO 🟡: fundamental = min(15, 10+2) = 12 → 42
    expect(computeNRS({ ...BASE, preipo: true, growth: '🟡 plano' }, { degree: 4 })).toBe(42);
    // grado enorme: chain topa en 25
    expect(computeNRS(BASE, { degree: 1000 })).toBe(45);
  });

  it('sin ctx el grado es 0 (chain = 0)', () => {
    expect(computeNRS(BASE)).toBe(computeNRS(BASE, { degree: 0 }));
  });
});

describe('computeNRSBreakdown', () => {
  it('nodo ausente → null (paridad con el clásico)', () => {
    expect(computeNRSBreakdown(null)).toBeNull();
    expect(computeNRSBreakdown(undefined, { degree: 1 })).toBeNull();
  });

  it('total coincide con computeNRS para los mismos inputs', () => {
    const casos = [
      [BASE, { degree: 4 }],
      [{ country: 'China', margin: -0.5, preipo: true, growth: '🔴' }, { degree: 7 }],
      [{ country: 'Taiwan', margin: 0.55 }, { degree: 1 }], // chain fraccional 2.5
      [{}, undefined],
      [{ country: 'Japan', growth: '🟡' }, { degree: 12 }],
    ];
    for (const [node, ctx] of casos) {
      const b = computeNRSBreakdown(node, ctx);
      expect(b.total).toBe(computeNRS(node, ctx));
    }
  });

  it('trae los 5 términos en orden con sus máximos nominales', () => {
    const b = computeNRSBreakdown(BASE, { degree: 4 });
    expect(b.terms.map((t) => t.key)).toEqual([
      'Geopolítica', 'Cadena', 'Margen', 'Fundamental', 'Concentración',
    ]);
    expect(b.terms.map((t) => t.max)).toEqual([30, 25, 20, 15, 10]);
    for (const t of b.terms) {
      expect(Number.isFinite(t.val)).toBe(true);
      expect(typeof t.hot).toBe('boolean');
      expect(typeof t.detail).toBe('string');
    }
  });

  it('detalles legibles: grado, % de margen y pre-IPO', () => {
    const b = computeNRSBreakdown({ ...BASE, margin: 0.25, preipo: true }, { degree: 4 });
    expect(b.terms[1].detail).toBe('grado 4');
    expect(b.terms[2].detail).toBe('25%');
    expect(b.terms[3].detail).toBe('pre-IPO');
    const sinMargen = computeNRSBreakdown({ country: 'EEUU' }, { degree: 0 });
    expect(sinMargen.terms[2].detail).toBe('s/d');
  });

  it('hot marca los umbrales del clásico', () => {
    const caliente = computeNRSBreakdown(
      { country: 'China', margin: 0.0, preipo: true, growth: '🔴' },
      { degree: 10 },
    );
    // geo 28>=20, chain 25>=20, market 20>=14, fundamental 15>=10, conc 10>=10
    expect(caliente.terms.every((t) => t.hot)).toBe(true);
    const frio = computeNRSBreakdown(BASE, { degree: 2 });
    expect(frio.terms.every((t) => !t.hot)).toBe(true);
  });
});

describe('buildDegreeMap', () => {
  it('cuenta aristas incidentes con endpoints string u objeto', () => {
    const m = buildDegreeMap([
      { source: 'a', target: 'b' },
      { source: { id: 'a' }, target: { id: 'c' } },
      { source: 'b', target: 'c' },
    ]);
    expect(m.get('a')).toBe(2);
    expect(m.get('b')).toBe(2);
    expect(m.get('c')).toBe(2);
  });

  it('un self-loop cuenta 1 (paridad con _buildNrsDegree)', () => {
    const m = buildDegreeMap([{ source: 'x', target: 'x' }]);
    expect(m.get('x')).toBe(1);
  });

  it('links vacíos o ausentes → mapa vacío', () => {
    expect(buildDegreeMap([]).size).toBe(0);
    expect(buildDegreeMap(undefined).size).toBe(0);
  });

  it('alimenta ctx.degree para computeNRS', () => {
    const links = [
      { source: 'nvda', target: 'tsmc' },
      { source: 'tsmc', target: 'asml' },
    ];
    const deg = buildDegreeMap(links);
    const v = computeNRS({ country: 'Taiwan', margin: 0.45 }, { degree: deg.get('tsmc') });
    // geo 25 + chain 5 + market round((1-1)*20)=0... margin 0.45 → min(1, 1.125)=1 → 0
    // + fundamental 0 + concentración 10 = 40
    expect(v).toBe(40);
  });
});
