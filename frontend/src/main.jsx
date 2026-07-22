import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import { VocabularyProvider } from './context/VocabularyContext.jsx'
import './styles.css'

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <VocabularyProvider>
      <App />
    </VocabularyProvider>
  </React.StrictMode>,
)
