import { describe, it, expect } from 'vitest';
import { mergeGraph, resolveAlias } from './mergeGraph.js';

/** Congela recursivamente para detectar cualquier mutación de entradas. */
function deepFreeze(obj) {
  if (obj && typeof obj === 'object' && !Object.isFrozen(obj)) {
    Object.freeze(obj);
    for (const k of Object.keys(obj)) deepFreeze(obj[k]);
  }
  return obj;
}

const ALIASES = {
  NVIDIA: 'Nvidia',
  AWS: 'Amazon',
  Lam_Research: 'Lam',
  // cadena de dos saltos: X → Y → Nvidia
  NVIDIA_NIM: 'NVIDIA',
};

const NODES = [
  { id: 'Nvidia', label: 'NVIDIA Corp', cat: 'fabless' },
  { id: 'Amazon', label: 'Amazon', cat: 'cloud' },
  { id: 'Lam', label: 'Lam Research', cat: 'equip' },
  { id: 'TSMC', label: 'TSMC', cat: 'foundry' },
];

describe('resolveAlias', () => {
  it('devuelve el id tal cual si no es alias', () => {
    expect(resolveAlias('TSMC', ALIASES)).toBe('TSMC');
  });

  it('resuelve alias directos y cadenas de alias', () => {
    expect(resolveAlias('AWS', ALIASES)).toBe('Amazon');
    expect(resolveAlias('NVIDIA_NIM', ALIASES)).toBe('Nvidia'); // 2 saltos
  });
});

describe('mergeGraph — links', () => {
  it('resuelve alias en source Y en target', () => {
    const { links } = mergeGraph({
      nodes: NODES,
      rawLinks: [['NVIDIA', 'AWS', 3, 'GPUs para EC2', 'supply']],
      aliases: ALIASES,
    });
    expect(links).toEqual([
      { source: 'Nvidia', target: 'Amazon', w: 3, rel: 'GPUs para EC2', type: 'supply' },
    ]);
  });

  it('acepta array-links y object-links mezclados, con defaults del clásico', () => {
    const { links } = mergeGraph({
      nodes: NODES,
      rawLinks: [
        ['TSMC', 'Nvidia', 4, 'wafers', 'supply'],
        { s: 'Lam_Research', t: 'TSMC', type: 'equipment' }, // sin w ni rel
      ],
      aliases: ALIASES,
    });
    expect(links).toContainEqual({ source: 'TSMC', target: 'Nvidia', w: 4, rel: 'wafers', type: 'supply' });
    // objeto sin w → 2, sin rel → '', alias Lam_Research → Lam
    expect(links).toContainEqual({ source: 'Lam', target: 'TSMC', w: 2, rel: '', type: 'equipment' });
    expect(links).toHaveLength(2);
  });

  it('descarta links hacia nodos inexistentes (y avisa por warn)', () => {
    const warnings = [];
    const { links } = mergeGraph({
      nodes: NODES,
      rawLinks: [
        ['TSMC', 'NoExiste', 3, '', 'supply'],
        ['Fantasma', 'Nvidia', 3, '', 'supply'],
        ['TSMC', 'Nvidia', 3, '', 'supply'],
      ],
      aliases: ALIASES,
      warn: (m) => warnings.push(m),
    });
    expect(links).toHaveLength(1);
    expect(links[0]).toMatchObject({ source: 'TSMC', target: 'Nvidia' });
    expect(warnings).toHaveLength(2);
    expect(warnings[0]).toContain('NoExiste');
  });

  it('descarta self-links tras resolver alias y pesos no positivos', () => {
    const { links } = mergeGraph({
      nodes: NODES,
      rawLinks: [
        ['NVIDIA', 'Nvidia', 3, '', 'supply'], // self tras alias
        ['TSMC', 'Nvidia', 0, '', 'supply'],   // w explícito 0 → fuera
      ],
      aliases: ALIASES,
    });
    expect(links).toEqual([]);
  });

  it('deduplica por (source, target, type): gana mayor peso y rel más larga', () => {
    const { links } = mergeGraph({
      nodes: NODES,
      rawLinks: [
        ['TSMC', 'Nvidia', 2, 'wafers', 'supply'],
        ['TSMC', 'NVIDIA', 5, '', 'supply'],                  // mismo canónico, más peso
        ['TSMC', 'Nvidia', 1, 'wafers 3nm y 5nm', 'supply'],  // rel más larga
        ['TSMC', 'Nvidia', 1, '', 'partnership'],             // otro type: NO se fusiona
      ],
      aliases: ALIASES,
    });
    expect(links).toHaveLength(2);
    expect(links).toContainEqual({
      source: 'TSMC', target: 'Nvidia', w: 5, rel: 'wafers 3nm y 5nm', type: 'supply',
    });
    expect(links).toContainEqual({
      source: 'TSMC', target: 'Nvidia', w: 1, rel: '', type: 'partnership',
    });
  });
});

describe('mergeGraph — nodos', () => {
  it('absorbe nodos alias en el canónico: campos del canónico ganan, huecos se rellenan', () => {
    const { nodes } = mergeGraph({
      nodes: [
        { id: 'AWS', label: 'AWS', country: 'EEUU', extra: 'ground station' },
        { id: 'Amazon', label: 'Amazon', country: '' }, // country vacío → lo rellena el alias
      ],
      rawLinks: [],
      aliases: ALIASES,
    });
    expect(nodes).toHaveLength(1);
    expect(nodes[0]).toEqual({
      id: 'Amazon',
      label: 'Amazon',          // campo del canónico GANA sobre 'AWS'
      country: 'EEUU',          // hueco ('') rellenado por el alias
      extra: 'ground station',  // campo que solo tenía el alias
    });
  });

  it('deduplica nodos con id repetido (el primero es la base, el resto rellena)', () => {
    const { nodes } = mergeGraph({
      nodes: [
        { id: 'TSMC', label: 'TSMC', country: 'Taiwan' },
        { id: 'TSMC', label: 'TSMC dup', country: 'Taiwan', mktcap_b: 800 },
      ],
      rawLinks: [],
      aliases: {},
    });
    expect(nodes).toHaveLength(1);
    expect(nodes[0]).toEqual({ id: 'TSMC', label: 'TSMC', country: 'Taiwan', mktcap_b: 800 });
  });

  it('los links del alias se redirigen al nodo canónico absorbido', () => {
    const { nodes, links } = mergeGraph({
      nodes: [
        { id: 'Nvidia', label: 'NVIDIA Corp' },
        { id: 'NVIDIA', label: 'dup' },
        { id: 'TSMC', label: 'TSMC' },
      ],
      rawLinks: [['TSMC', 'NVIDIA', 3, 'wafers', 'supply']],
      aliases: ALIASES,
    });
    expect(nodes.map((n) => n.id).sort()).toEqual(['Nvidia', 'TSMC']);
    expect(links).toEqual([
      { source: 'TSMC', target: 'Nvidia', w: 3, rel: 'wafers', type: 'supply' },
    ]);
  });
});

describe('mergeGraph — pureza', () => {
  it('no muta nodes, rawLinks ni aliases (entradas congeladas)', () => {
    const nodes = deepFreeze([
      { id: 'AWS', label: 'AWS', extra: 'x' },
      { id: 'Amazon', label: 'Amazon' },
      { id: 'TSMC', label: 'TSMC' },
    ]);
    const rawLinks = deepFreeze([
      ['TSMC', 'AWS', 3, 'chips', 'supply'],
      { s: 'TSMC', t: 'Amazon', w: 5, rel: 'más chips', type: 'supply' },
    ]);
    const aliases = deepFreeze({ AWS: 'Amazon' });

    // Con entradas congeladas, cualquier mutación lanzaría TypeError (strict mode de ESM)
    const out = mergeGraph({ nodes, rawLinks, aliases });

    expect(out.nodes).toHaveLength(2);
    expect(out.links).toEqual([
      { source: 'TSMC', target: 'Amazon', w: 5, rel: 'más chips', type: 'supply' },
    ]);
    // y las entradas siguen intactas
    expect(nodes).toHaveLength(3);
    expect(nodes[0]).toEqual({ id: 'AWS', label: 'AWS', extra: 'x' });
    expect(rawLinks[0]).toEqual(['TSMC', 'AWS', 3, 'chips', 'supply']);
  });
});
