/* El vocabulario es el REGISTRO ÚNICO del server; si el server no está,
   el fallback local debe tener los valores históricos exactos (paridad con
   ontology/vocabulary.json v1) — nunca una app sin vocabulario. */
import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { VocabularyProvider, relLabel, useVocabulary } from './VocabularyContext.jsx'

function Probe() {
  const { vocab, loading, offline } = useVocabulary()
  return (
    <div>
      <span data-testid="rels">{(vocab.structural_relations || []).join(',')}</span>
      <span data-testid="state">{loading ? 'loading' : offline ? 'offline' : 'online'}</span>
    </div>
  )
}

const HIST = 'supply,cloud,fab,license,partner,invest,deploy,owns,ppa'

afterEach(() => vi.unstubAllGlobals())

describe('VocabularyContext', () => {
  it('sirve el vocabulario del server cuando /api/vocabulary responde', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify({
        version: 9,
        structural_relations: ['supply', 'nueva_rel'],
        relation_types: { nueva_rel: { es: 'transporta a' } },
      }),
    }))
    render(<VocabularyProvider><Probe /></VocabularyProvider>)
    await waitFor(() => expect(screen.getByTestId('state')).toHaveTextContent('online'))
    expect(screen.getByTestId('rels')).toHaveTextContent('supply,nueva_rel')
  })

  it('cae al fallback HISTÓRICO exacto si el server no está', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('sin red')))
    render(<VocabularyProvider><Probe /></VocabularyProvider>)
    await waitFor(() => expect(screen.getByTestId('state')).toHaveTextContent('offline'))
    expect(screen.getByTestId('rels')).toHaveTextContent(HIST)
  })

  it('relLabel devuelve la etiqueta del registro y el id crudo si no está catalogada', () => {
    const vocab = { relation_types: { supply: { es: 'provee a', en: 'supplies' } } }
    expect(relLabel(vocab, 'supply')).toBe('provee a')
    expect(relLabel(vocab, 'supply', 'en')).toBe('supplies')
    expect(relLabel(vocab, 'rel_desconocida')).toBe('rel_desconocida')
  })
})
