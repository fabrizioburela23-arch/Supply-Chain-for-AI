import { describe, it, expect } from 'vitest';
import { classify } from './sentiment.js';

describe('classify — titulares positivos (EN)', () => {
  it.each([
    ['Nvidia earnings beat expectations', 'pos'],
    ['TSMC posts record quarterly revenue', 'pos'],
    ['AMD shares surge after AI chip launch', 'pos'],
    ['Micron stock soars on HBM demand', 'pos'],
    ['Broadcom jumps 8% on guidance', 'pos'],
    ['Intel gains after foundry deal', 'pos'],
    ['ASML orders rise sharply', 'pos'],
    ['Strong demand lifts SK Hynix', 'pos'],
    ['Analyst upgrades Marvell to buy', 'pos'],
    ['Palantir rally continues into Q3', 'pos'],
  ])('%s → %s', (h, exp) => {
    expect(classify(h)).toBe(exp);
  });
});

describe('classify — titulares positivos (ES)', () => {
  it.each([
    ['Nvidia sube tras resultados', 'pos'],
    ['TSMC gana terreno en bolsa', 'pos'],
    ['La demanda de chips crece en Asia', 'pos'],
    ['Récord de ingresos para ASML', 'pos'],
    ['Samsung sube con fuerza en Seúl', 'pos'],
    ['AMD gana cuota de mercado en datacenter', 'pos'],
    ['El sector crece impulsado por la IA', 'pos'],
    ['Micron sube tras nuevo contrato de HBM', 'pos'],
    ['Ingreso récord trimestral para Broadcom', 'pos'],
    ['Intel gana un cliente clave de foundry', 'pos'],
  ])('%s → %s', (h, exp) => {
    expect(classify(h)).toBe(exp);
  });
});

describe('classify — titulares negativos (EN)', () => {
  it.each([
    ['Intel earnings miss estimates', 'neg'],
    ['Nvidia shares fall on export curbs', 'neg'],
    ['Chip stocks drop after tariff news', 'neg'],
    ['Micron plunges on weak guidance', 'neg'],
    ['Samsung to cut memory output', 'neg'],
    ['AMD posts quarterly loss', 'neg'],
    ['Regulators probe TSMC subsidiary', 'neg'],
    ['Analysts warn of oversupply', 'neg'],
    ['Broker downgrades Marvell', 'neg'],
    ['Semiconductor slump deepens', 'neg'],
  ])('%s → %s', (h, exp) => {
    expect(classify(h)).toBe(exp);
  });
});

describe('classify — titulares negativos (ES)', () => {
  it.each([
    ['Nvidia baja tras las restricciones', 'neg'],
    ['La acción de Intel cae con fuerza', 'neg'],
    ['TSMC pierde terreno en la sesión', 'neg'],
    ['Aumenta el riesgo geopolítico para los chips', 'neg'],
    ['Nueva sanción golpea a los fabricantes chinos', 'neg'],
    ['Samsung baja por menor demanda de memoria', 'neg'],
    ['El sector cae ante nuevos aranceles', 'neg'],
    ['ASML pierde un pedido clave', 'neg'],
    ['Riesgo de sobreoferta en memorias', 'neg'],
    ['Micron cae tras resultados', 'neg'],
  ])('%s → %s', (h, exp) => {
    expect(classify(h)).toBe(exp);
  });
});

describe('classify — neutrales y casos borde', () => {
  it.each([
    ['Nvidia presenta su nueva arquitectura', 'neutral'],
    ['TSMC celebra su junta anual de accionistas', 'neutral'],
    ['El CEO de Intel visita la planta de Arizona', 'neutral'],
    ['Samsung announces developer conference', 'neutral'],
    // señales mixtas (pos Y neg) → neutral, igual que el clásico
    ['Nvidia beats estimates but shares fall', 'neutral'],
    ['Micron sube pese al riesgo de sobreoferta', 'neutral'],
  ])('%s → %s', (h, exp) => {
    expect(classify(h)).toBe(exp);
  });

  it('vacío, null y undefined → neutral', () => {
    expect(classify('')).toBe('neutral');
    expect(classify(null)).toBe('neutral');
    expect(classify(undefined)).toBe('neutral');
  });
});
