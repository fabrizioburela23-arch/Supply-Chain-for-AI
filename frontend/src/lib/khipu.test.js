// src/lib/khipu.test.js — tests de tabla del parser KHIPU (lib/khipu.js).
// Lógica pura: sin fetch, sin red, sin DOM.
import { describe, it, expect } from 'vitest';
import { tryParse } from './khipu.js';

describe('tryParse — comandos <ENTIDAD> <FUNCIÓN>', () => {
  it.each([
    ['NVDA DES', 'DES', 'second_brain'],
    ['NVDA SUP', 'SUP', 'tkg_object'],
    ['NVDA CLI', 'CLI', 'tkg_object'],
    ['NVDA RISK', 'RISK', 'tkg_object'],
    ['NVDA NEWS', 'NEWS', 'tkg_object'],
    ['NVDA SIM', 'SIM', 'stress'],
    ['NVDA XRAY', 'XRAY', 'xray'],
  ])('%s → cmd %s con acción %s sobre NVDA', (input, cmd, actionType) => {
    const r = tryParse(input);
    expect(r).not.toBeNull();
    expect(r.cmd).toBe(cmd);
    expect(r.id).toBe('NVDA');
    expect(r.actions).toEqual([{ type: actionType, arg: 'NVDA' }]);
    expect(typeof r.answer).toBe('string');
  });

  it('GP con rango: "NVDA GP 1Y" guarda el rango y navega', () => {
    const r = tryParse('NVDA GP 1Y');
    expect(r).toMatchObject({ cmd: 'GP', id: 'NVDA', range: '1Y' });
    expect(r.actions).toEqual([{ type: 'navigate', arg: 'NVDA' }]);
  });

  it('GP sin rango: range null', () => {
    expect(tryParse('TSM GP')).toMatchObject({ cmd: 'GP', id: 'TSM', range: null });
  });

  it('FA devuelve descriptor con symbol (el fetch lo hace el llamador)', () => {
    const r = tryParse('AMD FA');
    expect(r).toMatchObject({ cmd: 'FA', id: 'AMD', symbol: 'AMD' });
    expect(r.actions).toEqual([{ type: 'second_brain', arg: 'AMD' }]);
  });

  it('THESIS con texto conserva el texto completo', () => {
    const r = tryParse('NVDA THESIS domina el mercado de GPUs para IA');
    expect(r).toMatchObject({ cmd: 'THESIS', id: 'NVDA', text: 'domina el mercado de GPUs para IA' });
    expect(r.actions).toEqual([{ type: 'tkg_object', arg: 'NVDA' }]);
  });

  it('THESIS sin texto abre la ficha (text null + answer)', () => {
    const r = tryParse('NVDA THESIS');
    expect(r).toMatchObject({ cmd: 'THESIS', text: null });
    expect(r.answer).toContain('tesis');
  });
});

describe('tryParse — PORT', () => {
  it.each([
    ['PORT VAR', 'VAR'],
    ['PORT PL', 'PL'],
  ])('%s → sub %s', (input, sub) => {
    expect(tryParse(input)).toEqual({ cmd: 'PORT', sub, actions: [] });
  });

  it('PORT con sub desconocido devuelve el uso', () => {
    const r = tryParse('PORT XYZ');
    expect(r).toMatchObject({ cmd: 'PORT', sub: null });
    expect(r.answer).toContain('VAR');
  });
});

describe('tryParse — GRAPH', () => {
  it('GRAPH ASOF <fecha>', () => {
    expect(tryParse('GRAPH ASOF 2025-06-01')).toEqual({ cmd: 'GRAPH', sub: 'ASOF', date: '2025-06-01', actions: [] });
  });

  it('GRAPH ASOF sin fecha → answer de uso', () => {
    const r = tryParse('GRAPH ASOF');
    expect(r).toMatchObject({ cmd: 'GRAPH', sub: 'ASOF', date: null });
    expect(r.answer).toContain('YYYY-MM-DD');
  });

  it('GRAPH DIFF 7d parsea los días (case-insensitive)', () => {
    const r = tryParse('graph diff 7d');
    expect(r).toMatchObject({ cmd: 'GRAPH', sub: 'DIFF', days: 7 });
    expect(r.actions).toEqual([{ type: 'switch_tab', arg: 'tkg' }]);
  });

  it('GRAPH DIFF sin argumento → 30 días por defecto', () => {
    expect(tryParse('GRAPH DIFF')).toMatchObject({ cmd: 'GRAPH', sub: 'DIFF', days: 30 });
  });

  it('GRAPH con sub desconocido devuelve el uso', () => {
    expect(tryParse('GRAPH FOO').answer).toContain('ASOF');
  });
});

describe('tryParse — ALERT (3 formas)', () => {
  it('ALERT <ticker> PX > <valor> → rule de precio (misma forma que el clásico)', () => {
    expect(tryParse('ALERT NVDA PX > 150')).toEqual({
      cmd: 'ALERT', sub: 'CREATE',
      rule: { entity: 'NVDA', metric: 'price', op: '>', value: 150 },
      actions: [],
    });
  });

  it('ALERT <ticker> NRS > <valor> → rule de NRS', () => {
    const r = tryParse('ALERT TSM NRS > 70');
    expect(r.rule).toEqual({ entity: 'TSM', metric: 'nrs', op: '>', value: 70 });
  });

  it('ALERT REGION <región> NEWS → rule news_region', () => {
    expect(tryParse('ALERT REGION Taiwan NEWS')).toEqual({
      cmd: 'ALERT', sub: 'REGION',
      rule: { metric: 'news_region', region: 'Taiwan' },
      actions: [],
    });
  });

  it('ALERT REGION sin NEWS → answer de uso', () => {
    const r = tryParse('ALERT REGION Taiwan');
    expect(r).toMatchObject({ cmd: 'ALERT', sub: null });
    expect(r.answer).toContain('REGION');
  });

  it('ALERT LIST', () => {
    expect(tryParse('ALERT LIST')).toEqual({ cmd: 'ALERT', sub: 'LIST', actions: [] });
  });

  it('ALERT malformado (valor no numérico) → answer de uso, no null', () => {
    const r = tryParse('ALERT NVDA PX > alto');
    expect(r).toMatchObject({ cmd: 'ALERT', sub: null });
    expect(r.answer).toContain('PX|NRS');
  });
});

describe('tryParse — COMPARE / SHOCK / INSIGHTS / MATRIX', () => {
  it('COMPARE A B', () => {
    const r = tryParse('COMPARE NVDA AMD');
    expect(r).toMatchObject({ cmd: 'COMPARE', a: 'NVDA', b: 'AMD' });
    expect(r.actions).toEqual([{ type: 'compare', arg: { a: 'NVDA', b: 'AMD' } }]);
  });

  it('SHOCK con severidad', () => {
    const r = tryParse('SHOCK TSM 60');
    expect(r).toMatchObject({ cmd: 'SHOCK', id: 'TSM', sev: 60 });
    expect(r.actions).toEqual([{ type: 'livesim', arg: { id: 'TSM', sev: 60 } }]);
  });

  it('SHOCK sin severidad → 100 por defecto', () => {
    expect(tryParse('SHOCK TSM').sev).toBe(100);
  });

  it('INSIGHTS y MATRIX abren insights', () => {
    expect(tryParse('INSIGHTS').actions).toEqual([{ type: 'insights' }]);
    expect(tryParse('MATRIX').actions).toEqual([{ type: 'insights' }]);
  });
});

describe('tryParse — texto libre, casing y espacios', () => {
  it.each([
    ['qué opinas de NVIDIA este trimestre'],
    ['hola'],
    ['NVDA'],           // una sola palabra que no es keyword
    [''],
    ['   '],
    ['NVDA FOO'],       // segunda palabra no es función KHIPU
  ])('texto libre %j → null', (input) => {
    expect(tryParse(input)).toBeNull();
  });

  it('null/undefined → null sin lanzar', () => {
    expect(tryParse(null)).toBeNull();
    expect(tryParse(undefined)).toBeNull();
  });

  it('minúsculas: "nvda des" parsea y normaliza el símbolo a MAYÚSCULAS', () => {
    const r = tryParse('nvda des');
    expect(r).toMatchObject({ cmd: 'DES', id: 'NVDA' });
  });

  it('espacios raros: "  NVDA    sup  " parsea igual', () => {
    const r = tryParse('  NVDA    sup  ');
    expect(r).toMatchObject({ cmd: 'SUP', id: 'NVDA' });
  });

  it('mezcla de mayúsculas: "Alert nvda px > 120" crea la alerta', () => {
    const r = tryParse('Alert nvda px > 120');
    expect(r).toMatchObject({ cmd: 'ALERT', sub: 'CREATE' });
    expect(r.rule).toEqual({ entity: 'NVDA', metric: 'price', op: '>', value: 120 });
  });
});

describe('tryParse — resolutor inyectado', () => {
  const NODES = {
    NVDA: { id: 'nvidia', label: 'NVIDIA', mkt: 'NVDA' },
    TSM: { id: 'tsmc', label: 'TSMC', mkt: 'TSM' },
  };
  /** @type {(t: string) => any} */
  const resolve = (t) => NODES[(t || '').toUpperCase()] || null;

  it('con resolve, usa id y label del nodo resuelto', () => {
    const r = tryParse('NVDA DES', resolve);
    expect(r).toMatchObject({ cmd: 'DES', id: 'nvidia', label: 'NVIDIA' });
    expect(r.actions).toEqual([{ type: 'second_brain', arg: 'nvidia' }]);
    expect(r.answer).toContain('NVIDIA');
  });

  it('con resolve, FA usa el ticker de mercado como symbol', () => {
    expect(tryParse('tsm fa', resolve).symbol).toBe('TSM');
  });

  it('con resolve, entidad desconocida → null (cae a lenguaje natural)', () => {
    expect(tryParse('ZZZZ DES', resolve)).toBeNull();
  });

  it('con resolve, COMPARE resuelve ambos lados', () => {
    const r = tryParse('COMPARE NVDA TSM', resolve);
    expect(r.actions).toEqual([{ type: 'compare', arg: { a: 'nvidia', b: 'tsmc' } }]);
  });

  it('con resolve, COMPARE con un lado desconocido → answer de uso', () => {
    const r = tryParse('COMPARE NVDA ZZZZ', resolve);
    expect(r).toMatchObject({ cmd: 'COMPARE', a: null, b: null });
    expect(r.answer).toContain('COMPARE');
  });

  it('con resolve, SHOCK desconocido → answer de uso (no null)', () => {
    const r = tryParse('SHOCK ZZZZ', resolve);
    expect(r).toMatchObject({ cmd: 'SHOCK', id: null });
    expect(r.answer).toContain('SHOCK');
  });

  it('con resolve, ALERT usa el id canónico en la rule', () => {
    const r = tryParse('ALERT NVDA NRS > 65', resolve);
    expect(r.rule).toEqual({ entity: 'nvidia', metric: 'nrs', op: '>', value: 65 });
  });
});
