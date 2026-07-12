// crypto_intel.js — Capa estática de inteligencia cripto (expediente jul-2026).
// Fuente: KHIPUS_CRIPTO_TOP50_EXPEDIENTE.md (snapshot CoinMarketCap, semana 6-12 jul 2026).
// Esta capa cualitativa (tesis, tokenomics, riesgos) debe refrescarse cada 3-6 meses;
// los datos dinámicos (precio, volumen, market cap) se jalan en vivo vía CoinGecko/CMC.
// Indexado por ID de CoinGecko; la UI también matchea por ticker como fallback.

window.CRYPTO_CATS = {
  store:    { icon: '🏦', es: 'Reserva de valor', en: 'Store of value',
              bes: 'Activos pensados para guardar valor a largo plazo, como una versión digital del oro.',
              ben: 'Assets meant to hold value over the long run, like a digital version of gold.' },
  l1:       { icon: '⛓', es: 'Plataformas de contratos', en: 'Smart-contract platforms',
              bes: 'Redes donde se construyen aplicaciones cripto — su valor crece si mucha gente las usa.',
              ben: 'Networks where crypto apps get built — their value grows when lots of people use them.' },
  stable:   { icon: '💵', es: 'Stablecoins', en: 'Stablecoins',
              bes: 'Monedas que valen siempre $1 — su riesgo no es el precio sino quién las respalda.',
              ben: 'Coins that always aim to be worth $1 — the risk is not the price but who backs them.' },
  payments: { icon: '💸', es: 'Pagos', en: 'Payments',
              bes: 'Criptomonedas pensadas para enviar dinero rápido y barato, como una remesa digital.',
              ben: 'Cryptocurrencies built to send money fast and cheap, like a digital remittance.' },
  privacy:  { icon: '🕶', es: 'Privacidad', en: 'Privacy',
              bes: 'Monedas que ocultan quién envía y quién recibe — útiles, pero bajo la lupa de los reguladores.',
              ben: 'Coins that hide who sends and who receives — useful, but under close watch by regulators.' },
  defi:     { icon: '🔄', es: 'DeFi e infraestructura', en: 'DeFi & infrastructure',
              bes: 'Los bancos y tuberías del mundo cripto: préstamos, intercambios y datos sin intermediarios.',
              ben: 'The banks and plumbing of crypto: lending, trading and data with no middlemen.' },
  exchange: { icon: '🏛', es: 'Tokens de exchange', en: 'Exchange tokens',
              bes: 'Tokens de casas de cambio — su valor sigue de cerca el éxito del exchange que los emite.',
              ben: 'Tokens issued by crypto exchanges — their value closely tracks the success of the exchange behind them.' },
  perps:    { icon: '⚡', es: 'DEXs de perpetuos', en: 'Perps DEXs',
              bes: 'Plataformas de trading con apalancamiento que viven completamente dentro de la blockchain.',
              ben: 'Leveraged trading platforms that live entirely on the blockchain.' },
  meme:     { icon: '🐕', es: 'Meme coins', en: 'Meme coins',
              bes: 'Monedas nacidas de bromas de internet — valen lo que su comunidad crea que valen.',
              ben: 'Coins born from internet jokes — worth whatever their community believes they are worth.' },
  rwa:      { icon: '🏢', es: 'Institucional / RWA', en: 'Institutional / RWA',
              bes: 'Proyectos que llevan activos del mundo real (bonos, fondos) a la blockchain.',
              ben: 'Projects bringing real-world assets (bonds, funds) onto the blockchain.' },
  ai:       { icon: '🤖', es: 'IA + cripto', en: 'AI + crypto',
              bes: 'Proyectos que combinan inteligencia artificial con blockchain.',
              ben: 'Projects combining artificial intelligence with blockchain.' },
};

window.CRYPTO_INTEL = Object.assign(window.CRYPTO_INTEL || {}, {

  // ── A. RESERVAS DE VALOR / FUNDACIONALES ────────────────────────────────

  'bitcoin': {
    ticker: 'BTC', name: 'Bitcoin', rank: 1, cat: 'store', tags: ['store'],
    warn: null,
    es: {
      what: 'El primer criptoactivo, protocolo de pagos peer-to-peer con supply fijo.',
      mech: 'Proof-of-Work, minería, halving cada ~4 años (el próximo ~2028).',
      tok: 'Supply máximo de 21M, ~20.05M en circulación; altamente distribuido pero con concentración notable en ballenas y ETFs institucionales.',
      cats: 'Los flujos de los ETFs spot de Bitcoin en EE.UU. siguen siendo el driver dominante del precio; la dominancia de BTC ronda el 56-58% del mercado total.',
      risks: 'Regulación de ETFs, riesgo de cola en eventos macro (tasas, geopolítica), competencia narrativa de otros "oro digital" (oro tokenizado, Zcash).',
      pos: 'Activo ancla de todo el mercado cripto; el resto de las monedas se mueven en relación a su dominancia.',
    },
    en: {
      what: 'The first crypto asset, a peer-to-peer payments protocol with a fixed supply.',
      mech: 'Proof-of-Work, mining, halving every ~4 years (the next one ~2028).',
      tok: 'Max supply of 21M, ~20.05M in circulation; highly distributed but with notable concentration among whales and institutional ETFs.',
      cats: 'Flows into US spot Bitcoin ETFs remain the dominant price driver; BTC dominance hovers around 56-58% of the total market.',
      risks: 'ETF regulation, tail risk from macro events (rates, geopolitics), narrative competition from other "digital gold" plays (tokenized gold, Zcash).',
      pos: 'The anchor asset of the entire crypto market; every other coin trades relative to its dominance.',
    },
  },

  'ethereum': {
    ticker: 'ETH', name: 'Ethereum', rank: 2, cat: 'l1', tags: ['l1'],
    warn: null,
    es: {
      what: 'La plataforma de contratos inteligentes original, base de la mayoría de DeFi, stablecoins y tokenización.',
      mech: 'Proof-of-Stake desde 2022; quema de fees (EIP-1559) parcialmente compensada por la emisión de staking.',
      tok: '~120.7M ETH en circulación, sin supply máximo pero con presión deflacionaria en momentos de alta actividad.',
      cats: 'ETFs spot de ETH con staking habilitado; crecimiento de las L2s (Arbitrum, Base, Optimism), que drenan actividad pero también validan la tesis de "capa de settlement".',
      risks: 'Competencia de L1s más rápidas (Solana, Hyperliquid), ingresos por fees on-chain reducidos por las L2s, complejidad regulatoria del staking.',
      pos: 'Infraestructura dominante para RWA y tokenización institucional (BlackRock BUIDL, etc.).',
    },
    en: {
      what: 'The original smart-contract platform, the base layer for most of DeFi, stablecoins and tokenization.',
      mech: 'Proof-of-Stake since 2022; fee burning (EIP-1559) partially offset by staking issuance.',
      tok: '~120.7M ETH in circulation, no max supply but with deflationary pressure during periods of high activity.',
      cats: 'Spot ETH ETFs with staking enabled; growth of L2s (Arbitrum, Base, Optimism), which drain activity but also validate the "settlement layer" thesis.',
      risks: 'Competition from faster L1s (Solana, Hyperliquid), on-chain fee revenue reduced by L2s, regulatory complexity around staking.',
      pos: 'The dominant infrastructure for RWA and institutional tokenization (BlackRock BUIDL, etc.).',
    },
  },

  // ── C. PLATAFORMAS DE CONTRATOS INTELIGENTES / L1s ──────────────────────

  'binancecoin': {
    ticker: 'BNB', name: 'BNB', rank: 4, cat: 'l1', tags: ['l1', 'exchange'],
    warn: null,
    es: {
      what: 'Token nativo de BNB Chain y del ecosistema Binance.',
      mech: 'Quema trimestral de tokens (BEP-95 / auto-burn) que reduce el supply progresivamente.',
      tok: '~135M en circulación, con mecanismo deflacionario activo.',
      cats: 'BNB Chain sigue siendo la base de lanzamiento de proyectos DeFi de alto volumen (incluyendo Aster).',
      risks: 'Dependencia regulatoria del ecosistema Binance/CZ; concentración de poder en el exchange.',
      pos: 'El "exchange token" dominante: se beneficia directamente del volumen de Binance.',
    },
    en: {
      what: 'Native token of BNB Chain and the Binance ecosystem.',
      mech: 'Quarterly token burns (BEP-95 / auto-burn) progressively reduce the supply.',
      tok: '~135M in circulation, with an active deflationary mechanism.',
      cats: 'BNB Chain remains the launchpad for high-volume DeFi projects (including Aster).',
      risks: 'Regulatory dependence on the Binance/CZ ecosystem; concentration of power in the exchange.',
      pos: 'The dominant exchange token: it benefits directly from Binance trading volume.',
    },
  },

  'solana': {
    ticker: 'SOL', name: 'Solana', rank: 7, cat: 'l1', tags: ['l1'],
    warn: null,
    es: {
      what: 'L1 de alto rendimiento enfocada en velocidad y bajo costo de transacción.',
      mech: 'Proof-of-History + Proof-of-Stake.',
      tok: '~582M SOL en circulación, con inflación programada decreciente.',
      cats: 'ETFs spot de Solana, dominancia en meme coins y pagos de consumo (Solana Pay), fuerte actividad de stablecoins.',
      risks: 'Historial de caídas de red (aunque ha mejorado), competencia directa de Hyperliquid en algunos nichos de trading.',
      pos: 'La principal alternativa a Ethereum para aplicaciones de consumo y trading de alta frecuencia on-chain.',
    },
    en: {
      what: 'High-performance L1 focused on speed and low transaction cost.',
      mech: 'Proof-of-History + Proof-of-Stake.',
      tok: '~582M SOL in circulation, with a decreasing programmed inflation schedule.',
      cats: 'Spot Solana ETFs, dominance in meme coins and consumer payments (Solana Pay), strong stablecoin activity.',
      risks: 'A history of network outages (though much improved), direct competition from Hyperliquid in some trading niches.',
      pos: 'The main alternative to Ethereum for consumer applications and high-frequency on-chain trading.',
    },
  },

  'tron': {
    ticker: 'TRX', name: 'TRON', rank: 8, cat: 'l1', tags: ['l1'],
    warn: null,
    es: {
      what: 'L1 fundada por Justin Sun, dominante en transferencias de stablecoins (especialmente USDT) en mercados emergentes.',
      mech: 'Delegated Proof-of-Stake.',
      cats: 'El volumen de USDT sobre TRON sigue siendo enorme en remesas y comercio informal en LatAm y Asia.',
      risks: 'Reputación regulatoria de Justin Sun, alta concentración de validadores.',
      pos: 'Infraestructura de facto para stablecoins de bajo costo en mercados no bancarizados — relevante para el contexto boliviano y latinoamericano.',
    },
    en: {
      what: 'L1 founded by Justin Sun, dominant in stablecoin transfers (especially USDT) across emerging markets.',
      mech: 'Delegated Proof-of-Stake.',
      cats: 'USDT volume on TRON remains enormous in remittances and informal commerce across LatAm and Asia.',
      risks: 'Justin Sun regulatory reputation, high validator concentration.',
      pos: 'The de facto infrastructure for low-cost stablecoins in underbanked markets — relevant to the Bolivian and Latin American context.',
    },
  },

  'cardano': {
    ticker: 'ADA', name: 'Cardano', rank: 14, cat: 'l1', tags: ['l1'],
    warn: null,
    es: {
      what: 'L1 académica, con desarrollo basado en peer-review.',
      mech: 'Proof-of-Stake (Ouroboros).',
      cats: 'Ecosistema más lento en adopción DeFi comparado con Solana o Ethereum, pero con una base de usuarios fiel.',
      risks: 'Percepción de lentitud en el lanzamiento de funcionalidades frente a competidores.',
      pos: 'Nicho de gobernanza on-chain y adopción institucional/gubernamental en mercados emergentes (África).',
    },
    en: {
      what: 'Academic L1, with peer-review-driven development.',
      mech: 'Proof-of-Stake (Ouroboros).',
      cats: 'An ecosystem slower in DeFi adoption compared to Solana or Ethereum, but with a loyal user base.',
      risks: 'Perception of slow feature shipping relative to competitors.',
      pos: 'A niche in on-chain governance and institutional/governmental adoption in emerging markets (Africa).',
    },
  },

  'hedera-hashgraph': {
    ticker: 'HBAR', name: 'Hedera', rank: 26, cat: 'l1', tags: ['l1'],
    warn: null,
    es: {
      what: 'Red basada en Hashgraph (no una blockchain tradicional), gobernada por un consejo de grandes corporaciones (Google, IBM, Boeing, etc.).',
      cats: 'Foco en tokenización empresarial y stablecoins reguladas.',
      risks: 'La gobernanza centralizada en el consejo genera dudas sobre su descentralización real.',
      pos: 'Juega la carta "institucional / enterprise-grade" frente a L1s más cripto-nativas.',
    },
    en: {
      what: 'Network based on Hashgraph (not a traditional blockchain), governed by a council of large corporations (Google, IBM, Boeing, etc.).',
      cats: 'Focus on enterprise tokenization and regulated stablecoins.',
      risks: 'Governance centralized in the council raises doubts about its real decentralization.',
      pos: 'Plays the "institutional / enterprise-grade" card against more crypto-native L1s.',
    },
  },

  'sui': {
    ticker: 'SUI', name: 'Sui', rank: 27, cat: 'l1', tags: ['l1'],
    warn: null,
    es: {
      what: 'L1 de alto rendimiento creada por el ex-equipo de Meta/Diem; usa un modelo de objetos paralelo (no de cuentas).',
      cats: 'Ecosistema DeFi y gaming en crecimiento; los unlocks mensuales de tokens del equipo generan presión de venta recurrente.',
      risks: 'Unlocks programados, competencia directa con Solana y Aptos.',
      pos: 'Apuesta técnica a la paralelización de transacciones como ventaja de escalabilidad.',
    },
    en: {
      what: 'High-performance L1 built by the ex-Meta/Diem team; uses a parallel object model (rather than accounts).',
      cats: 'Growing DeFi and gaming ecosystem; monthly team token unlocks create recurring sell pressure.',
      risks: 'Scheduled unlocks, direct competition with Solana and Aptos.',
      pos: 'A technical bet on transaction parallelization as a scalability edge.',
    },
  },

  'avalanche-2': {
    ticker: 'AVAX', name: 'Avalanche', rank: 28, cat: 'l1', tags: ['l1'],
    warn: null,
    es: {
      what: 'L1 con arquitectura de subnets (cadenas personalizadas).',
      cats: 'Adopción institucional vía subnets privadas (ej. BlackRock BUIDL desplegado en Avalanche).',
      risks: 'Fragmentación de liquidez entre subnets.',
      pos: 'Apunta a instituciones que quieren su propia cadena permisionada con interoperabilidad.',
    },
    en: {
      what: 'L1 with a subnet architecture (customizable chains).',
      cats: 'Institutional adoption via private subnets (e.g. BlackRock BUIDL deployed on Avalanche).',
      risks: 'Liquidity fragmentation across subnets.',
      pos: 'Targets institutions that want their own permissioned chain with interoperability.',
    },
  },

  'near': {
    ticker: 'NEAR', name: 'NEAR Protocol', rank: 33, cat: 'l1', tags: ['l1', 'ai'],
    warn: null,
    es: {
      what: 'L1 con sharding nativo y un pivote reciente hacia la narrativa de "IA + blockchain" (agentes de IA on-chain).',
      risks: 'La narrativa de IA es reciente y no está comprobada en tracción real de usuarios.',
      pos: 'Intenta diferenciarse combinando escalabilidad técnica con la ola de agentes autónomos.',
    },
    en: {
      what: 'L1 with native sharding and a recent pivot toward the "AI + blockchain" narrative (on-chain AI agents).',
      risks: 'The AI narrative is recent and unproven in terms of real user traction.',
      pos: 'Tries to differentiate itself by combining technical scalability with the autonomous-agents wave.',
    },
  },

  'bittensor': {
    ticker: 'TAO', name: 'Bittensor', rank: 34, cat: 'ai', tags: ['ai'],
    warn: null,
    es: {
      what: 'Red descentralizada de subredes especializadas en machine learning, donde mineros compiten aportando cómputo y modelos de IA.',
      mech: '"Proof of Intelligence": se recompensa la calidad del output de IA de cada subred.',
      risks: 'Mecanismo de incentivos complejo y difícil de auditar; valoración muy ligada al hype de la IA.',
      pos: 'El proyecto cripto más directamente expuesto a la narrativa de IA descentralizada.',
    },
    en: {
      what: 'A decentralized network of specialized machine-learning subnets, where miners compete by contributing compute and AI models.',
      mech: '"Proof of Intelligence": each subnet is rewarded for the quality of its AI output.',
      risks: 'A complex incentive mechanism that is hard to audit; valuation tightly linked to AI hype.',
      pos: 'The crypto project most directly exposed to the decentralized-AI narrative.',
    },
  },

  'polkadot': {
    ticker: 'DOT', name: 'Polkadot', rank: 45, cat: 'l1', tags: ['l1'],
    warn: null,
    es: {
      what: 'Red de parachains interoperables, diseñada por Gavin Wood (co-fundador de Ethereum).',
      risks: 'Adopción de parachains más lenta de lo proyectado en su lanzamiento (2020-2021).',
      pos: 'Tesis de interoperabilidad multi-cadena; hoy compite con soluciones más simples (bridges, L2s).',
    },
    en: {
      what: 'A network of interoperable parachains, designed by Gavin Wood (Ethereum co-founder).',
      risks: 'Parachain adoption has been slower than projected at launch (2020-2021).',
      pos: 'A multi-chain interoperability thesis; today it competes with simpler solutions (bridges, L2s).',
    },
  },

  'internet-computer': {
    ticker: 'ICP', name: 'Internet Computer', rank: 49, cat: 'l1', tags: ['l1'],
    warn: null,
    es: {
      what: 'Intenta alojar aplicaciones web completas (frontend + backend) directamente on-chain, sin servidores tradicionales.',
      risks: 'Adopción de desarrolladores limitada frente a la promesa inicial; alta caída desde su máximo histórico.',
      pos: 'Nicho de "internet completamente descentralizado": una tesis ambiciosa con tracción moderada.',
    },
    en: {
      what: 'Aims to host complete web applications (frontend + backend) directly on-chain, with no traditional servers.',
      risks: 'Developer adoption limited relative to the initial promise; a steep drop from its all-time high.',
      pos: 'The "fully decentralized internet" niche: an ambitious thesis with moderate traction.',
    },
  },

  // ── D. PAGOS Y CRIPTO "LEGACY" ──────────────────────────────────────────

  'ripple': {
    ticker: 'XRP', name: 'XRP', rank: 6, cat: 'payments', tags: ['payments'],
    warn: null,
    es: {
      what: 'Token para liquidación transfronteriza vía la red de Ripple Labs.',
      cats: 'La resolución del litigio con la SEC (2023-2025) despejó gran parte de la incertidumbre regulatoria; expansión de RLUSD como stablecoin propio.',
      risks: 'Dependencia de los acuerdos institucionales de Ripple con bancos; competencia de las stablecoins en el caso de uso de remesas.',
      pos: 'De interés directo para Bolivia y LatAm por su enfoque en corredores de remesas y pagos transfronterizos.',
    },
    en: {
      what: 'A token for cross-border settlement via the Ripple Labs network.',
      cats: 'The resolution of the SEC lawsuit (2023-2025) cleared much of the regulatory uncertainty; expansion of RLUSD as its own stablecoin.',
      risks: 'Dependence on Ripple institutional deals with banks; competition from stablecoins in the remittances use case.',
      pos: 'Of direct interest for Bolivia and LatAm given its focus on remittance corridors and cross-border payments.',
    },
  },

  'dogecoin': {
    ticker: 'DOGE', name: 'Dogecoin', rank: 10, cat: 'payments', tags: ['payments', 'meme'],
    warn: null,
    es: {
      what: 'El meme coin original, Proof-of-Work basado en Litecoin.',
      cats: 'Ciclos de atención ligados a Elon Musk/X, adopción esporádica como método de pago.',
      risks: 'Cero utilidad técnica diferenciada; su valor es puramente narrativo y comunitario.',
      pos: 'Barómetro del apetito de riesgo retail: sube fuerte en euforia y cae fuerte en aversión al riesgo.',
    },
    en: {
      what: 'The original meme coin, Proof-of-Work based on Litecoin.',
      cats: 'Attention cycles tied to Elon Musk/X, sporadic adoption as a payment method.',
      risks: 'Zero differentiated technical utility; its value is purely narrative and community-driven.',
      pos: 'A barometer of retail risk appetite: it rallies hard in euphoria and falls hard in risk-off moods.',
    },
  },

  'stellar': {
    ticker: 'XLM', name: 'Stellar', rank: 13, cat: 'payments', tags: ['payments'],
    warn: null,
    es: {
      what: 'Red de pagos enfocada en remesas y tokenización de activos, hermana técnica de Ripple.',
      cats: 'Partnerships con instituciones financieras para stablecoins reguladas y corredores de pago.',
      pos: 'Similar a XRP pero con un enfoque más de red abierta y sin fines de lucro vía la Stellar Development Foundation.',
    },
    en: {
      what: 'A payments network focused on remittances and asset tokenization, a technical sibling of Ripple.',
      cats: 'Partnerships with financial institutions for regulated stablecoins and payment corridors.',
      pos: 'Similar to XRP but with a more open-network, non-profit approach via the Stellar Development Foundation.',
    },
  },

  'bitcoin-cash': {
    ticker: 'BCH', name: 'Bitcoin Cash', rank: 18, cat: 'payments', tags: ['payments'],
    warn: null,
    es: {
      what: 'Hard fork de Bitcoin (2017) que prioriza bloques más grandes para pagos cotidianos.',
      risks: 'Ha perdido relevancia frente a Lightning Network y las L2s de Bitcoin.',
      pos: 'Nicho decreciente: mantiene una comunidad leal pero sin un catalizador de crecimiento claro.',
    },
    en: {
      what: 'A Bitcoin hard fork (2017) that prioritizes larger blocks for everyday payments.',
      risks: 'It has lost relevance to the Lightning Network and Bitcoin L2s.',
      pos: 'A shrinking niche: it keeps a loyal community but has no clear growth catalyst.',
    },
  },

  'litecoin': {
    ticker: 'LTC', name: 'Litecoin', rank: 23, cat: 'payments', tags: ['payments'],
    warn: null,
    es: {
      what: 'Fork temprano de Bitcoin ("plata digital"), Proof-of-Work.',
      risks: 'Sin diferenciación técnica fuerte en 2026; se sostiene mayormente por reconocimiento de marca y liquidez histórica.',
      pos: 'Activo "legacy" de riesgo relativo bajo por su antigüedad, pero sin una narrativa de crecimiento activa.',
    },
    en: {
      what: 'An early Bitcoin fork ("digital silver"), Proof-of-Work.',
      risks: 'No strong technical differentiation in 2026; mostly sustained by brand recognition and historical liquidity.',
      pos: 'A "legacy" asset with relatively low risk due to its age, but no active growth narrative.',
    },
  },

  // ── E. PRIVACIDAD ───────────────────────────────────────────────────────

  'zcash': {
    ticker: 'ZEC', name: 'Zcash', rank: 12, cat: 'privacy', tags: ['privacy'],
    warn: {
      es: '⚠ Riesgo de deslistado regulatorio: exchanges y jurisdicciones han retirado coins de privacidad por presión regulatoria (FATF Travel Rule).',
      en: '⚠ Regulatory delisting risk: exchanges and jurisdictions have removed privacy coins under regulatory pressure (FATF Travel Rule).',
    },
    es: {
      what: 'Blockchain con transacciones privadas opcionales vía pruebas zero-knowledge (zk-SNARKs).',
      cats: 'Fuerte repunte reciente ligado a la revalorización de las "privacy coins" en un entorno de mayor vigilancia financiera y demanda institucional por privacidad transaccional legítima.',
      risks: 'Exchanges y jurisdicciones han deslistado coins de privacidad por presión regulatoria (FATF Travel Rule); la mayoría de los holders usa poco la función privada.',
      pos: 'Referente técnico en criptografía de privacidad, con el riesgo regulatorio más alto de la lista.',
    },
    en: {
      what: 'A blockchain with optional private transactions via zero-knowledge proofs (zk-SNARKs).',
      cats: 'A strong recent rally tied to a re-rating of privacy coins amid growing financial surveillance and institutional demand for legitimate transactional privacy.',
      risks: 'Exchanges and jurisdictions have delisted privacy coins under regulatory pressure (FATF Travel Rule); most holders make limited use of the private feature.',
      pos: 'The technical benchmark in privacy cryptography, carrying the highest regulatory risk on this list.',
    },
  },

  'monero': {
    ticker: 'XMR', name: 'Monero', rank: 15, cat: 'privacy', tags: ['privacy'],
    warn: {
      es: '⚠ Riesgo de deslistado regulatorio: ya retirado de los principales exchanges de EE.UU., Europa y Japón por presión regulatoria.',
      en: '⚠ Regulatory delisting risk: already removed from major exchanges in the US, Europe and Japan under regulatory pressure.',
    },
    es: {
      what: 'Privacidad por defecto (no opcional) vía ring signatures y direcciones stealth.',
      risks: 'Deslistado de los principales exchanges en EE.UU., Europa y Japón por presión regulatoria; asociado a mercados ilícitos en la percepción pública.',
      pos: 'El estándar de privacidad "máxima", pero con liquidez decreciente en plataformas reguladas.',
    },
    en: {
      what: 'Privacy by default (not optional) via ring signatures and stealth addresses.',
      risks: 'Delisted from major exchanges in the US, Europe and Japan under regulatory pressure; associated with illicit markets in public perception.',
      pos: 'The standard for "maximum" privacy, but with declining liquidity on regulated platforms.',
    },
  },

});
