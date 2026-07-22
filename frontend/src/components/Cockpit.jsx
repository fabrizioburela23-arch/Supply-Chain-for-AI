/**
 * Cockpit — la CABINA de Bixby, pantalla inicial del app React (versión base).
 *
 * Réplica de la UX del clásico (`engine/cockpit.js` → stageEmpty + _homeHyper):
 *
 * 1. HERO: «Soy Bixby. Pregúntame lo que sea.» + chips de ejemplos que
 *    RELLENAN el input (no disparan nada solos — el usuario decide enviar).
 * 2. BANNER DEL HIPERGRAFO: `POST /api/matrix/insights {lang:'es',tier:'fast'}`
 *    → chips de factores activos + top insight + tarjetas por kind + cascada
 *    en vivo con barras. Si el motor no está (`available:false`, error o
 *    respuesta vacía) el banner desaparece EN SILENCIO — la Cabina nunca
 *    muestra un error por una capa opcional.
 * 3. BARRA DE ENTRADA: al enviar se intenta PRIMERO el parser KHIPU
 *    (`tryParse` de src/lib/khipu.js, mismo orden que command_center.js del
 *    clásico). Si es comando → panel «Comando KHIPU» con el parseo. Si no →
 *    aviso de que la IA conversacional llega en la siguiente oleada (NO se
 *    llama a ningún endpoint de IA todavía).
 *
 * Disclaimer fijo SIEMPRE visible: «Análisis, no asesoría financiera.»
 */
import { useEffect, useState } from 'react'
import { post } from '../api/client.js'
import { tryParse } from '../lib/khipu.js'

/**
 * @typedef {Object} HyperInsight
 * @property {string} kind - 'riesgo' | 'oportunidad' | 'estructura' (otros caen a 'estructura').
 * @property {string} title - Título corto narrado.
 * @property {string} [detail] - Detalle de una línea.
 */

/**
 * @typedef {Object} HyperData Respuesta de POST /api/matrix/insights.
 * @property {boolean} [available] - false → motor apagado, no pintar nada.
 * @property {HyperInsight[]} [insights]
 * @property {Array<{label:string, severity?:number, members?:string[]}>} [factors]
 * @property {Array<{id?:string, name?:string, impact?:number}>} [cascade]
 * @property {string} [trigger] - Qué disparó la cascada.
 * @property {number} [affected] - Nodos alcanzados.
 * @property {string} [model] - Modelo que narró (o 'plantilla').
 */

/** Chips de ejemplo del hero (mismos textos que el clásico, en español). */
const HERO_CHIPS = [
  { k: 'Radiografía completa', q: 'desármame Nvidia' },
  { k: 'Shock en el mapa', q: '¿qué pasa si cae TSMC?' },
  { k: 'Dónde invertir', q: 'muéstrame oportunidades' },
  { k: 'Dos empresas', q: 'compara Nvidia y AMD' },
]

/** Icono y color de borde por kind de insight (contrato visual del clásico). */
const KIND_META = {
  riesgo: { icon: '⚠️', color: 'var(--down)' },
  oportunidad: { icon: '📈', color: 'var(--up)' },
  estructura: { icon: '🕸', color: 'var(--neon)' },
}

/**
 * Normaliza el kind a uno de los tres conocidos.
 * @param {string|undefined} kind
 * @returns {'riesgo'|'oportunidad'|'estructura'}
 */
function normKind(kind) {
  return kind === 'riesgo' || kind === 'oportunidad' ? kind : 'estructura'
}

const S = {
  root: { maxWidth: 860, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 18, paddingBottom: 20 },
  hero: { textAlign: 'center', paddingTop: 8 },
  h2: { margin: '0 0 6px', fontSize: 26, fontWeight: 700, letterSpacing: -0.4 },
  heroP: { margin: '0 0 16px', color: 'var(--text-dim)', fontSize: 13.5 },
  chips: { display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center' },
  chip: {
    font: 'inherit', fontSize: 12.5, padding: '7px 14px', borderRadius: 999, cursor: 'pointer',
    background: 'var(--panel)', border: '1px solid var(--border)', color: 'var(--text)',
    display: 'inline-flex', alignItems: 'center', gap: 7,
  },
  chipK: { color: 'var(--neon)', fontSize: 10.5, fontWeight: 700, letterSpacing: 0.3 },

  hyperHd: { display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 },
  hyperT: { fontWeight: 700, fontSize: 13.5 },
  live: {
    fontSize: 9, fontWeight: 800, letterSpacing: '0.1em', color: 'var(--neon)',
    border: '1px solid rgba(0,224,255,0.4)', borderRadius: 999, padding: '2px 8px',
  },
  facts: { display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 10 },
  fact: {
    fontSize: 10.5, color: 'var(--warn)', border: '1px solid rgba(255,179,0,0.3)',
    borderRadius: 999, padding: '2px 9px',
  },
  topInsight: { fontSize: 13.5, marginBottom: 10 },
  icards: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 8, marginBottom: 10 },
  icard: { borderLeft: '3px solid var(--border)', padding: '10px 12px' },
  icardHd: { display: 'flex', gap: 7, alignItems: 'baseline', fontWeight: 700, fontSize: 12.5, marginBottom: 4 },
  icardDetail: { fontSize: 12, color: 'var(--text-dim)', lineHeight: 1.4, margin: 0 },
  cascHd: { fontSize: 11, color: 'var(--text-faint)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 },
  cascRow: { display: 'flex', alignItems: 'center', gap: 10, fontSize: 12, marginBottom: 4 },
  cascName: { flex: '0 0 160px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  cascBarWrap: { flex: 1, height: 6, borderRadius: 999, background: 'rgba(255,255,255,0.06)', overflow: 'hidden' },
  cascBar: { display: 'block', height: '100%', borderRadius: 999, background: 'var(--down)' },
  cascPct: { flex: '0 0 44px', textAlign: 'right', color: 'var(--text-dim)', fontVariantNumeric: 'tabular-nums' },

  answer: { borderLeft: '3px solid var(--neon)' },
  answerTitle: { fontSize: 11, fontWeight: 700, letterSpacing: '0.06em', color: 'var(--neon)', textTransform: 'uppercase', marginBottom: 8 },
  answerLine: { fontSize: 13, marginBottom: 8 },
  pre: {
    margin: 0, fontSize: 11.5, lineHeight: 1.5, color: 'var(--text-dim)',
    fontFamily: "'JetBrains Mono', ui-monospace, monospace",
    whiteSpace: 'pre-wrap', wordBreak: 'break-word',
    background: 'rgba(0,0,0,0.25)', borderRadius: 10, padding: '10px 12px',
  },
  notice: { borderLeft: '3px solid var(--violet)', fontSize: 13, color: 'var(--text-dim)' },

  form: { display: 'flex', gap: 8 },
  input: {
    flex: 1, padding: '11px 14px', borderRadius: 12, font: 'inherit',
    background: 'var(--panel)', border: '1px solid var(--border)', color: 'var(--text)',
  },
  send: {
    padding: '11px 20px', borderRadius: 12, font: 'inherit', fontWeight: 700, cursor: 'pointer',
    background: 'rgba(0,224,255,0.1)', border: '1px solid var(--border-hi)', color: 'var(--neon)',
  },
  disclaimer: { textAlign: 'center', fontSize: 11, color: 'var(--text-faint)' },
}

/**
 * Banner proactivo del hipergrafo (capa opcional, silenciosa si no está).
 * @param {{data: HyperData}} props
 * @returns {import('react').JSX.Element|null}
 */
function HyperBanner({ data }) {
  const insights = Array.isArray(data.insights) ? data.insights : []
  if (insights.length === 0) return null
  const top = insights[0]
  const factors = (Array.isArray(data.factors) ? data.factors : []).slice(0, 4)
  const cascade = (Array.isArray(data.cascade) ? data.cascade : []).slice(0, 6)
  const maxImpact = Math.max(...cascade.map((c) => c.impact || 0), 1)
  const topMeta = KIND_META[normKind(top.kind)]

  return (
    <section className="panel-card" aria-label="Lo que ve el hipergrafo">
      <div style={S.hyperHd}>
        <span style={S.hyperT}>🕸 Lo que ve el hipergrafo</span>
        <span style={S.live}>EN VIVO</span>
      </div>

      {factors.length > 0 && (
        <div style={S.facts}>
          {factors.map((f) => (
            <span key={f.label} style={S.fact}>⚡ {f.label}</span>
          ))}
        </div>
      )}

      <div style={S.topInsight}>
        <b>{topMeta.icon} {top.title}</b>
      </div>

      <div style={S.icards}>
        {insights.map((it, i) => {
          const k = normKind(it.kind)
          const meta = KIND_META[k]
          return (
            <article key={`${it.title}-${i}`} className="panel-card" style={{ ...S.icard, borderLeftColor: meta.color }}>
              <div style={S.icardHd}>
                <span aria-hidden="true">{meta.icon}</span>
                <span>{it.title}</span>
              </div>
              {it.detail && <p style={S.icardDetail}>{it.detail}</p>}
            </article>
          )
        })}
      </div>

      {cascade.length > 0 && (
        <div>
          <div style={S.cascHd}>
            Cascada en vivo
            {data.trigger ? ` · ${data.trigger}` : ''}
            {data.affected ? ` · ${data.affected} nodos alcanzados` : ''}
          </div>
          {cascade.map((c) => (
            <div key={c.id || c.name} style={S.cascRow}>
              <span style={S.cascName}>{c.name || c.id}</span>
              <span style={S.cascBarWrap}>
                <i style={{ ...S.cascBar, width: `${Math.round(((c.impact || 0) / maxImpact) * 100)}%` }} />
              </span>
              <span style={S.cascPct}>{Math.round(c.impact || 0)}%</span>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

/**
 * La Cabina de Bixby — pantalla inicial.
 * @returns {import('react').JSX.Element}
 */
export default function Cockpit() {
  const [input, setInput] = useState('')
  const [hyper, setHyper] = useState(
    /** @type {{status:'loading'|'ok'|'off', data:HyperData|null}} */
    ({ status: 'loading', data: null }),
  )
  const [result, setResult] = useState(
    /** @type {null | {type:'khipu', parsed:Object} | {type:'ai-pending', text:string}} */
    (null),
  )

  useEffect(() => {
    let alive = true
    post('/api/matrix/insights', { lang: 'es', tier: 'fast' })
      .then((d) => {
        if (!alive) return
        // Silencioso si el motor no está: available:false, error o sin insights.
        if (!d || d.available === false || d.error || !Array.isArray(d.insights) || d.insights.length === 0) {
          setHyper({ status: 'off', data: null })
          return
        }
        setHyper({ status: 'ok', data: d })
      })
      .catch(() => {
        if (alive) setHyper({ status: 'off', data: null })
      })
    return () => { alive = false }
  }, [])

  /** @param {import('react').FormEvent} e */
  const onSubmit = (e) => {
    e.preventDefault()
    const text = input.trim()
    if (!text) return
    // PRIMERO el parser KHIPU (mismo orden que el clásico: comando > IA).
    const parsed = tryParse(text)
    if (parsed) {
      setResult({ type: 'khipu', parsed })
    } else {
      setResult({ type: 'ai-pending', text })
    }
  }

  return (
    <div style={S.root}>
      {/* ── Hero ── */}
      <header style={S.hero}>
        <h2 style={S.h2}>Soy Bixby. Pregúntame lo que sea.</h2>
        <p style={S.heroP}>
          Puedo desarmar cualquier empresa, simular qué pasa si algo cae, comparar, y dibujarte los datos.
        </p>
        <div style={S.chips}>
          {HERO_CHIPS.map((c) => (
            <button key={c.q} type="button" style={S.chip} onClick={() => setInput(c.q)}>
              <span style={S.chipK}>{c.k}</span>
              {c.q}
            </button>
          ))}
        </div>
      </header>

      {/* ── Banner del hipergrafo (silencioso si el motor no está) ── */}
      {hyper.status === 'loading' && <div className="loading">Leyendo el hipergrafo…</div>}
      {hyper.status === 'ok' && hyper.data && <HyperBanner data={hyper.data} />}

      {/* ── Resultado del envío ── */}
      {result?.type === 'khipu' && (
        <section className="panel-card" style={S.answer} aria-label="Comando KHIPU">
          <div style={S.answerTitle}>Comando KHIPU · {result.parsed.cmd}</div>
          {result.parsed.answer && <div style={S.answerLine}>{result.parsed.answer}</div>}
          <pre style={S.pre}>{JSON.stringify(result.parsed, null, 2)}</pre>
        </section>
      )}
      {result?.type === 'ai-pending' && (
        <section className="panel-card" style={S.notice} aria-label="Aviso">
          IA conversacional: llega en la siguiente oleada de la migración.
        </section>
      )}

      {/* ── Barra de entrada ── */}
      <form style={S.form} onSubmit={onSubmit}>
        <input
          style={S.input}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Pregunta o comando KHIPU (ej. NVDA DES)"
          aria-label="Pregunta a Bixby"
        />
        <button type="submit" style={S.send}>Enviar</button>
      </form>

      <div style={S.disclaimer}>Análisis, no asesoría financiera.</div>
    </div>
  )
}
