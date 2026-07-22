/* VocabularyContext — el vocabulario del grafo viene del REGISTRO ÚNICO del
   server (GET /api/vocabulary). Este contexto es la muerte de las 5 copias
   divergentes del app clásico: los componentes leen de aquí, nunca definen
   sus propias listas de tipos/relaciones/sectores.
   Fallback: snapshot local (mismos valores históricos) si el server no está. */
import { createContext, useContext, useEffect, useState } from 'react'
import { get } from '../api/client.js'

// Valores históricos exactos (ontology/vocabulary.json v1) — solo fallback.
const FALLBACK = {
  version: 0,
  structural_relations: ['supply', 'cloud', 'fab', 'license', 'partner', 'invest', 'deploy', 'owns', 'ppa'],
  relation_weights: { supply: 1.0, fab: 1.0, cloud: 0.9, license: 0.8, ppa: 0.7, deploy: 0.4, partner: 0.3, owns: 0.6, invest: 0.25 },
  symmetric_relations: ['partner'],
  economic_types: ['Company', 'Country', 'Energy', 'Material', 'Org', 'Policy', 'Product', 'Tech'],
  relation_types: {},
  source_kinds: {},
}

const VocabularyContext = createContext({ vocab: FALLBACK, loading: true, offline: true })

export function VocabularyProvider({ children }) {
  const [state, setState] = useState({ vocab: FALLBACK, loading: true, offline: false })

  useEffect(() => {
    let alive = true
    get('/api/vocabulary')
      .then((v) => { if (alive && v && v.structural_relations) setState({ vocab: v, loading: false, offline: false }) })
      .catch(() => { if (alive) setState({ vocab: FALLBACK, loading: false, offline: true }) })
    return () => { alive = false }
  }, [])

  return <VocabularyContext.Provider value={state}>{children}</VocabularyContext.Provider>
}

export function useVocabulary() {
  return useContext(VocabularyContext)
}

/* Etiqueta humana de una relación ('supply' → 'provee a'), con el idioma del
   registro; si la relación no está catalogada devuelve el id crudo — visible,
   no degradado en silencio (regla del proyecto). */
export function relLabel(vocab, rel, lang = 'es') {
  const meta = vocab?.relation_types?.[rel]
  return (meta && (meta[lang] || meta.es)) || rel
}
