/**
 * Tests de GraphView — fetch SIEMPRE mockeado (nunca red real).
 * Con la API caída el componente debe caer al snapshot local.
 */
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import GraphView, { normalizeGraph } from './GraphView.jsx';
import snapshot from '../data/grafo_v0.json';

/** fetch que simula red caída → fuerza el fallback al snapshot. */
function failFetch() {
  return vi.fn(async () => {
    throw new TypeError('Failed to fetch');
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('GraphView', () => {
  it('con la API caída usa el snapshot: renderiza <svg> con ≥100 círculos', async () => {
    vi.stubGlobal('fetch', failFetch());
    const { container } = render(<GraphView />);

    // Estado de carga con icono animado (regla 6 de MIGRATION.md).
    expect(container.querySelector('.loading')).toBeInTheDocument();

    await waitFor(() =>
      expect(container.querySelectorAll('svg circle').length).toBeGreaterThanOrEqual(100)
    );
    expect(container.querySelector('svg')).toBeInTheDocument();
    expect(container.querySelector('.loading')).not.toBeInTheDocument();

    // Intentó la API viva primero, por el endpoint correcto.
    expect(fetch.mock.calls[0][0]).toBe('/api/ontology/graph');

    // Aviso de origen: snapshot local, no datos vivos.
    expect(screen.getByText(/snapshot local/)).toBeInTheDocument();
  });

  it('click en un nodo abre la tarjeta lateral con su label, sector y conexiones', async () => {
    vi.stubGlobal('fetch', failFetch());
    const { container } = render(<GraphView />);
    await waitFor(() =>
      expect(container.querySelectorAll('svg circle').length).toBeGreaterThanOrEqual(100)
    );

    // Nodo conocido del snapshot con conexiones.
    const node =
      snapshot.nodes.find((n) => n.id === 'IBMQuantum') || snapshot.nodes[0];
    const circle = container.querySelector(`circle[data-node-id="${node.id}"]`);
    expect(circle).not.toBeNull();

    fireEvent.click(circle);

    const card = await screen.findByTestId('graph-card');
    expect(within(card).getByRole('heading', { name: node.label })).toBeInTheDocument();
    expect(within(card).getByText('Conexiones')).toBeInTheDocument();
    // Lista de conexiones acotada a 12.
    expect(within(card).getAllByRole('listitem').length).toBeLessThanOrEqual(12);

    // Cerrar la tarjeta.
    fireEvent.click(within(card).getByRole('button', { name: /cerrar/i }));
    expect(screen.queryByTestId('graph-card')).not.toBeInTheDocument();
  });
});

describe('normalizeGraph', () => {
  it('filtra links colgantes y hereda sectores del snapshot si el payload no los trae', () => {
    const g = normalizeGraph(
      {
        nodes: [{ id: 'A', label: 'Alfa', cat: 'gpu' }, { id: 'B' }],
        links: [
          { source: 'A', target: 'B', w: 2, type: 'supply' },
          { source: 'A', target: 'ZZZ_no_existe', w: 1, type: 'supply' },
        ],
      },
      'api'
    );
    expect(g.nodes).toHaveLength(2);
    expect(g.links).toHaveLength(1);
    expect(g.nodes[1].label).toBe('B'); // label cae al id
    expect(g.sectors9).toBe(snapshot.sectors9);
    expect(g.catToSector).toBe(snapshot.cat_to_sector);
  });

  it('payload sin nodos → null (dispara el fallback)', () => {
    expect(normalizeGraph({}, 'api')).toBeNull();
    expect(normalizeGraph({ nodes: [] }, 'api')).toBeNull();
  });
});
