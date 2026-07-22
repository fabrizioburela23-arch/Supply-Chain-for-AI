/* Test del CASCARÓN: pestañas y navegación. Los paneles se mockean — cada uno
   tiene su propio test; aquí solo importa que el shell monte el panel correcto
   y que la Cabina sea la pantalla inicial (pedido explícito de Fabrizio). */
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

vi.mock('./components/Cockpit.jsx', () => ({ default: () => <div>PANEL_CABINA</div> }))
vi.mock('./components/GraphView.jsx', () => ({ default: () => <div>PANEL_GRAFO</div> }))
vi.mock('./components/MarketPanel.jsx', () => ({ default: () => <div>PANEL_MERCADO</div> }))
vi.mock('./components/NewsPanel.jsx', () => ({ default: () => <div>PANEL_NOTICIAS</div> }))

import App from './App.jsx'

describe('App shell', () => {
  it('arranca en la Cabina de Bixby (pantalla inicial)', async () => {
    render(<App />)
    await waitFor(() => expect(screen.getByText('PANEL_CABINA')).toBeInTheDocument())
    expect(screen.getByRole('button', { name: /Bixby/ })).toHaveClass('on')
  })

  it('cambia de panel al hacer clic en una pestaña', async () => {
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: /Noticias/ }))
    await waitFor(() => expect(screen.getByText('PANEL_NOTICIAS')).toBeInTheDocument())
    expect(screen.queryByText('PANEL_CABINA')).not.toBeInTheDocument()
  })

  it('todas las pestañas declaradas montan sin romper', async () => {
    const user = userEvent.setup()
    render(<App />)
    for (const [label, marker] of [
      [/Grafo/, 'PANEL_GRAFO'],
      [/Mercado/, 'PANEL_MERCADO'],
      [/Noticias/, 'PANEL_NOTICIAS'],
      [/Bixby/, 'PANEL_CABINA'],
    ]) {
      await user.click(screen.getByRole('button', { name: label }))
      await waitFor(() => expect(screen.getByText(marker)).toBeInTheDocument())
    }
  })
})
