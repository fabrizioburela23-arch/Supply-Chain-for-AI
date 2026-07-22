/**
 * Clasificador de sentimiento de titulares por palabras clave.
 * Portado 1:1 del clásico (`app.html`, función `sentiment(headline)`):
 * mismas regex bilingües ES/EN; solo cambia el contrato de salida —
 * el clásico devolvía `{cls:'pos'|'neg'|'neu', icon}`, aquí devolvemos
 * la etiqueta plana ('neu' → 'neutral') y la UI decide el icono.
 */

/** Palabras/raíces positivas (EN + ES), igual que el clásico. */
const POS =
  /(beat|record|surge|soar|jump|gain|rise|grow|strong|win|up |raise|outperform|upgrade|profit|bullish|rally|高|récord|sube|gana|crece)/;

/** Palabras/raíces negativas (EN + ES), igual que el clásico. */
const NEG =
  /(miss|fall|drop|plunge|cut|loss|weak|down |decline|sue|fine|ban|probe|warn|downgrade|bearish|slump|baja|cae|pierde|riesgo|sanción)/;

/**
 * Clasifica un titular como positivo, negativo o neutral.
 * Si el titular contiene señales de AMBOS lados (o de ninguno) es 'neutral',
 * igual que el clásico.
 *
 * @param {string|null|undefined} headline - Titular de noticia.
 * @returns {'pos'|'neg'|'neutral'} Etiqueta de sentimiento.
 */
export function classify(headline) {
  const h = (headline || '').toLowerCase();
  const isPos = POS.test(h);
  const isNeg = NEG.test(h);
  if (isPos && !isNeg) return 'pos';
  if (isNeg && !isPos) return 'neg';
  return 'neutral';
}
