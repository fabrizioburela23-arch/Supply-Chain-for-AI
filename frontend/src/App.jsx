/* App — el cascarón de pestañas del terminal. La Cabina de Bixby es la
   PANTALLA INICIAL (pedido 2026-07-13), igual que en el app clásico.
   Pestañas con implementación real primero; el resto llegan por oleadas de
   la migración (ver MIGRATION.md). */
import { lazy, Suspense, useState } from 'react'

const Cockpit = lazy(() => import('./components/Cockpit.jsx'))
const GraphView = lazy(() => import('./components/GraphView.jsx'))
const MarketPanel = lazy(() => import('./components/MarketPanel.jsx'))
const NewsPanel = lazy(() => import('./components/NewsPanel.jsx'))

const TABS = [
  { id: 'cabina', label: '✳ Bixby', component: Cockpit },
  { id: 'map', label: '🗺️ Grafo', component: GraphView },
  { id: 'market', label: '📈 Mercado', component: MarketPanel },
  { id: 'news', label: '📰 Noticias', component: NewsPanel },
]

export default function App() {
  const [tab, setTab] = useState('cabina')
  const active = TABS.find((t) => t.id === tab) || TABS[0]
  const Active = active.component

  return (
    <div className="app-shell">
      <nav className="app-tabs" aria-label="Secciones">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={'app-tab' + (t.id === tab ? ' on' : '')}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>
      <main className="app-stage">
        <Suspense fallback={<div className="loading">Cargando panel…</div>}>
          <Active />
        </Suspense>
      </main>
    </div>
  )
}
