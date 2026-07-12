// crypto_intel2.js — Capa estática de inteligencia cripto (lote 2: secciones B, F, G, H, I, J)
// Fuente: KHIPUS_CRIPTO_TOP50_EXPEDIENTE.md (snapshot jul-2026, CoinMarketCap semana 6-12 jul 2026).
// Esta capa es ESTÁTICA (tesis, tokenomics, riesgos): refrescar cada 3-6 meses.
// Los datos dinámicos (precio, volumen, market cap) se jalan en vivo vía CoinGecko — no viven aquí.
// Indexado por ID de CoinGecko; la UI también matchea por ticker como fallback.
// NO redefinir CRYPTO_CATS aquí — vive en crypto_intel.js.

window.CRYPTO_INTEL = Object.assign(window.CRYPTO_INTEL || {}, {

  // ── B. STABLECOINS Y ACTIVOS REFERENCIADOS ──────────────────────────────

  'tether': {
    ticker: 'USDT', name: 'Tether', rank: 3, cat: 'stable', tags: ['stable'],
    warn: null,
    es: {
      what: 'Stablecoin referenciado al dólar emitido por Tether (grupo iFinex). Colateral: reservas en efectivo y T-bills del Tesoro de EE.UU.; su auditoría ha sido cuestionada históricamente.',
      risks: 'Es el mayor stablecoin del mundo (~$184B); el riesgo central es de contraparte y de transparencia de reservas, no de dirección del precio.',
      pos: 'Columna vertebral de la liquidez cripto global; su valor está en mantener el peg 1:1 con el dólar, no en apreciarse.',
    },
    en: {
      what: 'Dollar-pegged stablecoin issued by Tether (iFinex group). Collateral: reserves in cash and U.S. Treasury bills; its audits have historically been questioned.',
      risks: 'The largest stablecoin in the world (~$184B); the core risk is counterparty exposure and reserve transparency, not price direction.',
      pos: 'Backbone of global crypto liquidity; its value lies in holding the 1:1 dollar peg, not in appreciation.',
    },
  },

  'usd-coin': {
    ticker: 'USDC', name: 'USD Coin', rank: 5, cat: 'stable', tags: ['stable'],
    warn: null,
    es: {
      what: 'Stablecoin de dólar emitido por Circle. Colateral: reservas 100% en efectivo y T-bills, auditadas por una firma Big Four.',
      risks: 'El más institucional de los grandes stablecoins; expuesto a la regulación bancaria de EE.UU.',
      pos: 'Stablecoin de referencia para instituciones y DeFi regulado; el valor está en el peg, no en apreciación.',
    },
    en: {
      what: 'Dollar stablecoin issued by Circle. Collateral: reserves 100% in cash and T-bills, audited by a Big Four firm.',
      risks: 'The most institutional of the large stablecoins; exposed to U.S. banking regulation.',
      pos: 'Reference stablecoin for institutions and regulated DeFi; the value is in the peg, not in appreciation.',
    },
  },

  'ethena-usde': {
    ticker: 'USDe', name: 'Ethena USDe', rank: 19, cat: 'stable', tags: ['stable'],
    warn: null,
    es: {
      what: 'Dólar sintético emitido por Ethena. Colateral: posiciones delta-neutral (colateral cripto cubierto con shorts de futuros), no reservas bancarias tradicionales.',
      risks: 'Riesgo de funding rate negativo prolongado y de contraparte en los exchanges de derivados donde mantiene sus coberturas.',
      pos: 'El experimento de dólar sintético más grande; ofrece rendimiento pero con un perfil de riesgo estructuralmente distinto al de un stablecoin con reservas. El valor está en el peg.',
    },
    en: {
      what: 'Synthetic dollar issued by Ethena. Collateral: delta-neutral positions (crypto collateral hedged with futures shorts), not traditional bank reserves.',
      risks: 'Risk of prolonged negative funding rates and counterparty exposure on the derivatives exchanges where it holds its hedges.',
      pos: 'The largest synthetic-dollar experiment; offers yield but with a structurally different risk profile from a reserve-backed stablecoin. The value is in the peg.',
    },
  },

  'dai': {
    ticker: 'DAI', name: 'Dai (MakerDAO)', rank: 21, cat: 'stable', tags: ['stable', 'defi'],
    warn: null,
    es: {
      what: 'Stablecoin descentralizado de MakerDAO. Colateral: colateralizado on-chain con cripto y RWA, siempre sobrecolateralizado.',
      risks: 'Ecosistema en transición hacia la marca Sky (ver ficha SKY); riesgo de liquidaciones en caídas fuertes del colateral cripto.',
      pos: 'El stablecoin descentralizado veterano; su valor está en sostener el peg mediante sobrecolateralización, no en subir de precio.',
    },
    en: {
      what: 'Decentralized stablecoin from MakerDAO. Collateral: collateralized on-chain with crypto and RWA, always overcollateralized.',
      risks: 'Ecosystem transitioning to the Sky brand (see SKY profile); liquidation risk in sharp drops of the crypto collateral.',
      pos: 'The veteran decentralized stablecoin; its value lies in holding the peg through overcollateralization, not in price upside.',
    },
  },

  'usd1-wlfi': {
    ticker: 'USD1', name: 'World Liberty Financial USD', rank: 22, cat: 'stable', tags: ['stable'],
    warn: {
      es: '⚠ Expuesto políticamente: ligado a la familia Trump; su riesgo regulatorio depende del ciclo político de EE.UU.',
      en: '⚠ Politically exposed: tied to the Trump family; its regulatory risk hinges on the U.S. political cycle.',
    },
    es: {
      what: 'Stablecoin de dólar de World Liberty Financial. Emisor/colateral: custodia de BitGo Trust y reservas en T-bills gestionadas por BlackRock.',
      risks: 'Ligado políticamente a la familia Trump; controversia reciente por colateral circular vía el protocolo Dolomite (ver ficha WLFI).',
      pos: 'Stablecoin con distribución impulsada por su afiliación política; el valor está en el peg, pero carga un riesgo reputacional y político inusual para un stablecoin.',
    },
    en: {
      what: 'Dollar stablecoin from World Liberty Financial. Issuer/collateral: BitGo Trust custody and T-bill reserves managed by BlackRock.',
      risks: 'Politically tied to the Trump family; recent controversy over circular collateral via the Dolomite protocol (see WLFI profile).',
      pos: 'Stablecoin whose distribution is boosted by its political affiliation; the value is in the peg, but it carries reputational and political risk unusual for a stablecoin.',
    },
  },

  'tether-gold': {
    ticker: 'XAUT', name: 'Tether Gold', rank: 25, cat: 'stable', tags: ['stable', 'rwa'],
    warn: null,
    es: {
      what: 'Token de Tether respaldado 1:1 por oro físico en bóveda en Suiza. Importante: sigue el precio del ORO, no el del dólar.',
      risks: 'Expone al precio del oro y al riesgo de custodia física; el emisor (Tether) arrastra el historial de transparencia cuestionada de USDT.',
      pos: 'Oro tokenizado: se comporta como el metal, no como un stablecoin de dólar; funciona como refugio dentro del ecosistema cripto.',
    },
    en: {
      what: 'Tether token backed 1:1 by physical gold vaulted in Switzerland. Important: it tracks the price of GOLD, not the dollar.',
      risks: 'Exposes you to the gold price and to physical custody risk; the issuer (Tether) carries the same questioned-transparency history as USDT.',
      pos: 'Tokenized gold: it behaves like the metal, not like a dollar stablecoin; serves as a safe-haven asset inside the crypto ecosystem.',
    },
  },

  'pax-gold': {
    ticker: 'PAXG', name: 'PAX Gold', rank: 29, cat: 'stable', tags: ['stable', 'rwa'],
    warn: null,
    es: {
      what: 'Token de Paxos respaldado 1:1 por oro físico alocado. Importante: sigue el precio del ORO, no el del dólar.',
      risks: 'Riesgo de custodia física y exposición al precio del oro; su diferenciador frente a XAUt es que Paxos es un emisor regulado.',
      pos: 'La versión regulada del oro tokenizado; replica al metal, no al dólar.',
    },
    en: {
      what: 'Paxos token backed 1:1 by allocated physical gold. Important: it tracks the price of GOLD, not the dollar.',
      risks: 'Physical custody risk and exposure to the gold price; its differentiator versus XAUt is that Paxos is a regulated issuer.',
      pos: 'The regulated version of tokenized gold; it tracks the metal, not the dollar.',
    },
  },

  'paypal-usd': {
    ticker: 'PYUSD', name: 'PayPal USD', rank: 32, cat: 'stable', tags: ['stable', 'payments'],
    warn: null,
    es: {
      what: 'Stablecoin de dólar de PayPal, emitido por Paxos y respaldado por reservas reguladas.',
      risks: 'Riesgo regulatorio ligado a PayPal como emisor; su suerte depende de la estrategia cripto de la empresa.',
      pos: 'Su ventaja es la distribución masiva vía la red PayPal/Venmo; el valor está en el peg, no en apreciación.',
    },
    en: {
      what: 'PayPal dollar stablecoin, issued by Paxos and backed by regulated reserves.',
      risks: 'Regulatory risk tied to PayPal as issuer; its fate depends on the company crypto strategy.',
      pos: 'Its edge is massive distribution through the PayPal/Venmo network; the value is in the peg, not in appreciation.',
    },
  },

  'global-dollar': {
    ticker: 'USDG', name: 'Global Dollar', rank: 37, cat: 'stable', tags: ['stable'],
    warn: null,
    es: {
      what: 'Stablecoin de dólar emitido por un consorcio liderado por Paxos junto a Robinhood, Kraken y otros.',
      risks: 'Relativamente nuevo; aún debe probar tracción frente a USDT y USDC.',
      pos: 'Busca posicionarse como el stablecoin neutral entre exchanges, con incentivos repartidos entre los miembros del consorcio; el valor está en el peg.',
    },
    en: {
      what: 'Dollar stablecoin issued by a consortium led by Paxos together with Robinhood, Kraken and others.',
      risks: 'Relatively new; still has to prove traction against USDT and USDC.',
      pos: 'Aims to position itself as the neutral stablecoin across exchanges, with incentives shared among consortium members; the value is in the peg.',
    },
  },

  'ripple-usd': {
    ticker: 'RLUSD', name: 'Ripple USD', rank: 42, cat: 'stable', tags: ['stable', 'payments'],
    warn: null,
    es: {
      what: 'Stablecoin de dólar de Ripple Labs. Colateral: reservas en efectivo y T-bills.',
      risks: 'Ligado al ecosistema XRP/Ripple; su adopción depende de los acuerdos institucionales de Ripple.',
      pos: 'Apunta a pagos institucionales transfronterizos como complemento de XRP; el valor está en el peg.',
    },
    en: {
      what: 'Ripple Labs dollar stablecoin. Collateral: reserves in cash and T-bills.',
      risks: 'Tied to the XRP/Ripple ecosystem; its adoption depends on Ripple institutional deals.',
      pos: 'Targets institutional cross-border payments as a complement to XRP; the value is in the peg.',
    },
  },

  'usdd': {
    ticker: 'USDD', name: 'USDD (Tron)', rank: 44, cat: 'stable', tags: ['stable'],
    warn: null,
    es: {
      what: 'Stablecoin del ecosistema Tron, impulsado por Justin Sun / Tron DAO; parcialmente colateralizado.',
      risks: 'Historial de descuentos del peg en 2022-2023 y menor transparencia de reservas que sus pares grandes.',
      pos: 'Stablecoin de nicho dentro del ecosistema Tron; su historial de peg lo hace de mayor riesgo relativo entre los grandes. El valor está en el peg.',
    },
    en: {
      what: 'Stablecoin of the Tron ecosystem, driven by Justin Sun / Tron DAO; partially collateralized.',
      risks: 'History of peg discounts in 2022-2023 and less reserve transparency than its larger peers.',
      pos: 'Niche stablecoin inside the Tron ecosystem; its peg history makes it relatively riskier among the majors. The value is in the peg.',
    },
  },

  // ── F. DEFI, INFRAESTRUCTURA Y TOKENS DE EXCHANGE ───────────────────────

  'leo-token': {
    ticker: 'LEO', name: 'UNUS SED LEO', rank: 11, cat: 'exchange', tags: ['exchange'],
    warn: null,
    es: {
      what: 'Token de utilidad del exchange Bitfinex/iFinex, con mecanismo de quema ligado a los ingresos de la empresa.',
      pos: 'Tesis similar a BNB, pero de un exchange más pequeño y con menor transparencia histórica.',
    },
    en: {
      what: 'Utility token of the Bitfinex/iFinex exchange, with a burn mechanism tied to company revenues.',
      pos: 'Similar thesis to BNB, but from a smaller exchange with less historical transparency.',
    },
  },

  'chainlink': {
    ticker: 'LINK', name: 'Chainlink', rank: 16, cat: 'defi', tags: ['defi'],
    warn: null,
    es: {
      what: 'Red de oráculos que conecta smart contracts con datos del mundo real: precios, eventos, APIs.',
      cats: 'Infraestructura crítica para RWA tokenizado: casi todo proyecto de tokenización institucional (incluyendo integraciones con Hyperliquid) depende de sus oráculos.',
      pos: 'Los picks and shovels de la tokenización: no compite directamente con las L1s, se beneficia de que cualquiera de ellas triunfe.',
    },
    en: {
      what: 'Oracle network connecting smart contracts to real-world data: prices, events, APIs.',
      cats: 'Critical infrastructure for tokenized RWA: nearly every institutional tokenization project (including Hyperliquid integrations) depends on its oracles.',
      pos: 'The picks and shovels of tokenization: it does not compete directly with L1s, it benefits whenever any of them succeeds.',
    },
  },

  'dexe': {
    ticker: 'DEXE', name: 'DeXe', rank: 24, cat: 'defi', tags: ['defi'],
    warn: null,
    es: {
      what: 'Protocolo de gobernanza y gestión de activos on-chain que permite crear DAOs de inversión y fondos gestionados de forma descentralizada.',
      pos: 'Nicho de asset management descentralizado, con menor liquidez y reconocimiento que los blue-chips DeFi.',
    },
    en: {
      what: 'On-chain governance and asset-management protocol for creating investment DAOs and decentrally managed funds.',
      pos: 'Decentralized asset-management niche, with less liquidity and recognition than DeFi blue chips.',
    },
  },

  'crypto-com-chain': {
    ticker: 'CRO', name: 'Cronos', rank: 30, cat: 'exchange', tags: ['exchange', 'l1'],
    warn: null,
    es: {
      what: 'Token del ecosistema Crypto.com, con cadena propia EVM-compatible (Cronos).',
      pos: 'Tesis similar a BNB/OKB: su valor va ligado al éxito del exchange y de su app de consumo masivo (tarjetas cripto, etc.).',
    },
    en: {
      what: 'Token of the Crypto.com ecosystem, with its own EVM-compatible chain (Cronos).',
      pos: 'Similar thesis to BNB/OKB: its value is tied to the success of the exchange and its mass-consumer app (crypto cards, etc.).',
    },
  },

  'uniswap': {
    ticker: 'UNI', name: 'Uniswap', rank: 35, cat: 'defi', tags: ['defi'],
    warn: null,
    es: {
      what: 'El exchange descentralizado (DEX) más grande por volumen histórico, con modelo de automated market maker (AMM).',
      cats: 'La activación del fee switch (repartir ingresos del protocolo a los holders de UNI) es un debate recurrente de gobernanza.',
      pos: 'Infraestructura DeFi de referencia, aunque compite con DEXs de nueva generación como Aster y Hyperliquid en el segmento de derivados.',
    },
    en: {
      what: 'The largest decentralized exchange (DEX) by historical volume, built on the automated market maker (AMM) model.',
      cats: 'Activating the fee switch (sharing protocol revenue with UNI holders) has been a recurring governance debate.',
      pos: 'Reference DeFi infrastructure, though it competes with next-generation DEXs like Aster and Hyperliquid in the derivatives segment.',
    },
  },

  'okb': {
    ticker: 'OKB', name: 'OKB', rank: 39, cat: 'exchange', tags: ['exchange'],
    warn: null,
    es: {
      what: 'Token del exchange OKX.',
      pos: 'Mismo modelo que BNB/CRO/BGB: utilidad de descuentos en fees y quemas ligadas al volumen del exchange.',
    },
    en: {
      what: 'Token of the OKX exchange.',
      pos: 'Same model as BNB/CRO/BGB: fee-discount utility and burns tied to exchange volume.',
    },
  },

  'ondo-finance': {
    ticker: 'ONDO', name: 'Ondo Finance', rank: 41, cat: 'defi', tags: ['defi', 'rwa'],
    warn: null,
    es: {
      what: 'Protocolo líder en tokenización de bonos del Tesoro de EE.UU. y activos de renta fija (RWA).',
      cats: 'Uno de los proyectos con integraciones institucionales más citadas del sector RWA: fondos tokenizados y partnerships con gestoras tradicionales.',
      risks: 'Depende de un marco regulatorio favorable para valores tokenizados en EE.UU.',
      pos: 'Uno de los nombres más relevantes si la tesis de Wall Street on-chain se consolida.',
    },
    en: {
      what: 'Leading protocol for tokenizing U.S. Treasury bonds and fixed-income assets (RWA).',
      cats: 'One of the most-cited projects for institutional integrations in the RWA sector: tokenized funds and partnerships with traditional asset managers.',
      risks: 'Depends on a favorable regulatory framework for tokenized securities in the U.S.',
      pos: 'One of the most relevant names if the Wall-Street-on-chain thesis consolidates.',
    },
  },

  'aave': {
    ticker: 'AAVE', name: 'Aave', rank: 43, cat: 'defi', tags: ['defi'],
    warn: null,
    es: {
      what: 'El protocolo de préstamos (lending) descentralizado más grande por TVL.',
      cats: 'Es la base técnica sobre la que corren varios forks institucionales, incluyendo el mercado de lending de World Liberty Financial.',
      pos: 'Infraestructura crítica de crédito on-chain, comparable a un banco descentralizado de facto.',
    },
    en: {
      what: 'The largest decentralized lending protocol by TVL.',
      cats: 'It is the technical base on which several institutional forks run, including the World Liberty Financial lending market.',
      pos: 'Critical on-chain credit infrastructure, comparable to a de facto decentralized bank.',
    },
  },

  'mantle': {
    ticker: 'MNT', name: 'Mantle', rank: 47, cat: 'l1', tags: ['l1', 'defi'],
    warn: null,
    es: {
      what: 'L2 de Ethereum respaldada por el tesoro de BitDAO/Bybit, enfocada en eficiencia de capital y modularidad.',
      pos: 'Compite en el saturado espacio de L2s de Ethereum (Arbitrum, Optimism, Base).',
    },
    en: {
      what: 'Ethereum L2 backed by the BitDAO/Bybit treasury, focused on capital efficiency and modularity.',
      pos: 'Competes in the crowded Ethereum L2 space (Arbitrum, Optimism, Base).',
    },
  },

  'sky': {
    ticker: 'SKY', name: 'Sky (antes MakerDAO)', rank: 48, cat: 'defi', tags: ['defi', 'stable'],
    warn: null,
    es: {
      what: 'Rebrand del protocolo MakerDAO completado en 2024: DAI pasó a llamarse USDS y MKR pasó a llamarse SKY.',
      mech: 'Stablecoin sobrecolateralizado con Reserva de Ahorro (Sky Savings Rate) que paga rendimiento a los holders de USDS.',
      risks: 'La transición de marca generó confusión y cierta resistencia comunitaria; persiste el riesgo de liquidaciones con colateral cripto volátil.',
      pos: 'Uno de los protocolos DeFi más antiguos y probados, reposicionado como banco central descentralizado con múltiples sub-marcas (Spark, etc.).',
    },
    en: {
      what: 'Rebrand of the MakerDAO protocol completed in 2024: DAI was renamed USDS and MKR was renamed SKY.',
      mech: 'Overcollateralized stablecoin with a Savings Reserve (Sky Savings Rate) that pays yield to USDS holders.',
      risks: 'The brand transition caused confusion and some community pushback; liquidation risk on volatile crypto collateral persists.',
      pos: 'One of the oldest and most battle-tested DeFi protocols, repositioned as a decentralized central bank with multiple sub-brands (Spark, etc.).',
    },
  },

  'bitget-token': {
    ticker: 'BGB', name: 'Bitget Token', rank: 50, cat: 'exchange', tags: ['exchange'],
    warn: null,
    es: {
      what: 'Token del exchange Bitget.',
      pos: 'Mismo modelo de utilidad y quema que BNB, OKB y CRO: su valor sigue de cerca el crecimiento del volumen del exchange.',
    },
    en: {
      what: 'Token of the Bitget exchange.',
      pos: 'Same utility-and-burn model as BNB, OKB and CRO: its value closely tracks the growth of exchange volume.',
    },
  },

  // ── G. NUEVA OLA: DEXs DE PERPETUOS ON-CHAIN ────────────────────────────

  'hyperliquid': {
    ticker: 'HYPE', name: 'Hyperliquid', rank: 9, cat: 'perps', tags: ['perps', 'l1'],
    warn: null,
    es: {
      what: 'L1 propia construida específicamente para trading de futuros perpetuos on-chain, con order book totalmente transparente y velocidad comparable a un exchange centralizado.',
      mech: 'Consenso HyperBFT (~200,000 órdenes por segundo) más una capa EVM (HyperEVM) para contratos inteligentes generales.',
      tok: 'El diferenciador clave: 97-99% de las fees de trading van a un Assistance Fund que compra y retira HYPE del mercado de forma continua y automática. Supply máximo 1,000M (~46% en circulación), sin asignación a VCs ni inversionistas privados: distribución 100% comunitaria vía airdrop (noviembre 2024).',
      cats: '~70% de todo el volumen de perpetuos on-chain pasa por Hyperliquid; expansión hacia mercados de acciones y commodities tokenizados (HIP-3); primeros ETFs spot institucionales de HYPE.',
      risks: 'Unlocks de tokens de contribuidores core en curso hasta 2027; competencia directa y agresiva de Aster; regulación de derivados apalancados en jurisdicciones específicas.',
      pos: 'El líder indiscutido del Wall Street on-chain: el caso de estudio más citado de tokenomics con flujo de caja real.',
    },
    en: {
      what: 'Purpose-built L1 for on-chain perpetual futures trading, with a fully transparent order book and speed comparable to a centralized exchange.',
      mech: 'HyperBFT consensus (~200,000 orders per second) plus an EVM layer (HyperEVM) for general smart contracts.',
      tok: 'The key differentiator: 97-99% of trading fees go to an Assistance Fund that continuously and automatically buys HYPE off the market and retires it. Max supply 1,000M (~46% circulating), with no allocation to VCs or private investors: 100% community distribution via airdrop (November 2024).',
      cats: '~70% of all on-chain perps volume flows through Hyperliquid; expansion into tokenized stock and commodity markets (HIP-3); first institutional spot HYPE ETFs.',
      risks: 'Core-contributor token unlocks running until 2027; direct, aggressive competition from Aster; regulation of leveraged derivatives in specific jurisdictions.',
      pos: 'The undisputed leader of on-chain Wall Street: the most-cited case study of tokenomics backed by real cash flow.',
    },
  },

  'aster-2': {
    ticker: 'ASTER', name: 'Aster', rank: 38, cat: 'perps', tags: ['perps', 'defi'],
    warn: {
      es: '⚠ Concentración extrema: 6 wallets controlan ~96% del supply, más sospechas de wash trading (DefiLlama retiró su tracking).',
      en: '⚠ Extreme concentration: 6 wallets control ~96% of supply, plus wash-trading suspicions (DefiLlama pulled its tracking).',
    },
    es: {
      what: 'DEX de perpetuos multichain (BNB Chain, Solana, Ethereum, Arbitrum) nacido de la fusión de Astherus y APX Finance a fines de 2024, respaldado por YZi Labs (ex-Binance Labs) y con el respaldo público de CZ.',
      mech: 'Modo Simple (hasta 1001x de apalancamiento sin margen inicial, con pool de liquidez interno ALP) y modo Pro (order book tradicional); acepta colateral yield-bearing que genera rendimiento mientras sirve como margen.',
      cats: 'Creció de $1.15B a más de $85B de volumen en 12 días tras su lanzamiento (septiembre 2025), llegando a superar el volumen diario de Hyperliquid.',
      risks: 'Solo 6 wallets controlan ~96% del supply (una sola tiene ~45%), con riesgo real de manipulación o venta masiva; DefiLlama retiró su tracking tras detectar volumen que replicaba casi tick a tick el de Binance (sospechas de wash trading); fuerte dependencia operativa de la infraestructura de Binance para su stablecoin USDF.',
      pos: 'El retador más agresivo de Hyperliquid: crecimiento explosivo pero con señales de alerta de concentración y de autenticidad de volumen que exigen cautela particular en una plataforma de inversión.',
    },
    en: {
      what: 'Multichain perps DEX (BNB Chain, Solana, Ethereum, Arbitrum) born from the merger of Astherus and APX Finance in late 2024, backed by YZi Labs (formerly Binance Labs) and publicly endorsed by CZ.',
      mech: 'Simple mode (up to 1001x leverage with no initial margin, using the internal ALP liquidity pool) and Pro mode (traditional order book); accepts yield-bearing collateral that keeps earning while used as margin.',
      cats: 'Grew from $1.15B to over $85B in volume in 12 days after launch (September 2025), at times surpassing Hyperliquid daily volume.',
      risks: 'Just 6 wallets control ~96% of ASTER supply (one wallet alone holds ~45%), a real risk of manipulation or mass selling; DefiLlama pulled its tracking after detecting volume patterns that mirrored Binance almost tick for tick (wash-trading suspicions); heavy operational dependence on Binance infrastructure for its USDF stablecoin.',
      pos: 'The most aggressive challenger to Hyperliquid: explosive growth, but with red flags around concentration and volume authenticity that demand particular caution on an investment platform.',
    },
  },

  // ── H. MEME COINS ───────────────────────────────────────────────────────

  'shiba-inu': {
    ticker: 'SHIB', name: 'Shiba Inu', rank: 31, cat: 'meme', tags: ['meme'],
    warn: null,
    es: {
      what: 'Meme coin lanzado en 2020 como competidor de Dogecoin, hoy con ecosistema propio (Shibarium, su propia L2).',
      risks: 'Supply extremadamente alto (cientos de billones de tokens), valor unitario cercano a cero y alta dependencia del sentimiento retail.',
      pos: 'El meme coin más maduro por el ecosistema construido a su alrededor, aunque la tesis sigue siendo mayormente especulativa y narrativa.',
    },
    en: {
      what: 'Meme coin launched in 2020 as a Dogecoin competitor, now with its own ecosystem (Shibarium, its own L2).',
      risks: 'Extremely high supply (hundreds of trillions of tokens), near-zero unit value, and heavy dependence on retail sentiment.',
      pos: 'The most mature meme coin in terms of the ecosystem built around it, though the thesis remains mostly speculative and narrative-driven.',
    },
  },

  'memecore': {
    ticker: 'M', name: 'MemeCore', rank: 40, cat: 'meme', tags: ['meme', 'l1'],
    warn: null,
    es: {
      what: 'L1 diseñada específicamente para meme coins, con un consenso propio llamado Proof of Meme que recompensa la participación cultural (crear y compartir contenido) además de la validación técnica.',
      tok: 'Supply fijo de 5,000M de tokens, usados para gas, staking y recompensas de minería social.',
      risks: 'Propuesta de valor no probada: cuantificar cultura on-chain es un experimento nuevo sin precedente de éxito sostenido; alta volatilidad (ya cayó más de 75% desde su ATH).',
      pos: 'Apuesta a que los meme coins necesitan infraestructura dedicada en vez de vivir como tokens ERC-20 sueltos sobre otras cadenas.',
    },
    en: {
      what: 'L1 designed specifically for meme coins, with its own consensus called Proof of Meme that rewards cultural participation (creating and sharing content) alongside technical validation.',
      tok: 'Fixed supply of 5,000M tokens, used for gas, staking and social-mining rewards.',
      risks: 'Unproven value proposition: quantifying culture on-chain is a new experiment with no precedent of sustained success; high volatility (already down more than 75% from its ATH).',
      pos: 'A bet that meme coins need dedicated infrastructure rather than living as loose ERC-20 tokens on other chains.',
    },
  },

  // ── I. BLOCKCHAIN INSTITUCIONAL / RWA ───────────────────────────────────

  'canton-network': {
    ticker: 'CC', name: 'Canton Network', rank: 17, cat: 'rwa', tags: ['rwa'],
    warn: null,
    es: {
      what: 'Red blockchain privacy-enabled diseñada por Digital Asset específicamente para instituciones financieras: permite sincronizar mercados financieros tradicionales sin sacrificar privacidad ni control de datos entre participantes.',
      cats: 'DTCC (la infraestructura de clearing más grande de EE.UU.) anunció planes de tokenizar bonos del Tesoro custodiados a través de Canton usando su herramienta ComposerX, un paso significativo hacia tokenización regulada institucional.',
      pos: 'Competidor directo de la tesis de Ondo/Hyperliquid en RWA, pero con enfoque más permisionado y enterprise: lo más cercano en espíritu a un Bloomberg on-chain para settlement institucional.',
    },
    en: {
      what: 'Privacy-enabled blockchain network designed by Digital Asset specifically for financial institutions: it lets traditional financial markets synchronize without sacrificing privacy or data control among participants.',
      cats: 'DTCC (the largest clearing infrastructure in the U.S.) announced plans to tokenize custodied Treasury bonds through Canton using its ComposerX tool, a significant step toward regulated institutional tokenization.',
      pos: 'A direct competitor to the Ondo/Hyperliquid thesis in RWA, but with a more permissioned, enterprise approach: the closest in spirit to a Bloomberg-on-chain for institutional settlement.',
    },
  },

  // ── J. OTROS DESTACADOS ─────────────────────────────────────────────────

  'the-open-network': {
    ticker: 'GRAM', name: 'Gram (antes Toncoin)', rank: 20, cat: 'l1', tags: ['l1', 'payments'],
    warn: null,
    es: {
      what: 'Token nativo de The Open Network (TON), la blockchain vinculada a Telegram. El 15 de junio de 2026 la comunidad votó (81.22% de aprobación) rebautizar Toncoin como Gram, el nombre del whitepaper original de 2018, retirado en su momento por la disputa legal con la SEC. Es un cambio puramente de marca y ticker (TON pasa a GRAM): balances, contratos y staking no se vieron afectados y no hizo falta ningún swap ni migración.',
      risks: 'Riesgo de datafeed: existen tokens impostores con nombres similares (GRM, GRAMPUS) sin relación alguna; el sistema debe identificar el activo correcto por su ID interno, no solo por el nombre Gram.',
      pos: 'Su tesis de fondo no cambió con el rebrand: sigue siendo la apuesta a que Telegram (mil millones de usuarios) se convierta en una superapp con pagos y cripto nativos.',
    },
    en: {
      what: 'Native token of The Open Network (TON), the blockchain linked to Telegram. On June 15, 2026 the community voted (81.22% approval) to rename Toncoin as Gram, the name from the original 2018 whitepaper, shelved back then due to the legal dispute with the SEC. It is purely a brand/ticker change (TON becomes GRAM): balances, contracts and staking were unaffected and no swap or migration was needed.',
      risks: 'Datafeed risk: impostor tokens with similar names exist (GRM, GRAMPUS) with no relation whatsoever; the system must identify the correct asset by its internal ID, not just by the name Gram.',
      pos: 'Its underlying thesis did not change with the rebrand: it remains the bet that Telegram (one billion users) becomes a superapp with native payments and crypto.',
    },
  },

  'world-liberty-financial': {
    ticker: 'WLFI', name: 'World Liberty Financial', rank: 36, cat: 'defi', tags: ['defi'],
    warn: {
      es: '⚠ Expuesto políticamente: la familia Trump recibe ~75% de los ingresos; riesgo regulatorio binario según el ciclo político de EE.UU.',
      en: '⚠ Politically exposed: the Trump family receives ~75% of revenues; binary regulatory risk tied to the U.S. political cycle.',
    },
    es: {
      what: 'Protocolo DeFi vinculado a la familia Trump, con dos productos: el stablecoin USD1 y el token de gobernanza WLFI.',
      tok: 'Token originalmente no transferible (habilitado para trading en julio 2025 tras voto comunitario), tope de 5% de poder de voto por wallet, supply máximo de 100,000M.',
      risks: 'En abril de 2026 se reportó que WLFI usó 5,000M de sus propios tokens de gobernanza como colateral para pedir prestados $75M en USD1 de Dolomite, un protocolo de lending cuyo cofundador es asesor de WLFI, drenando el pool de depositantes y generando comparaciones con la dinámica circular de FTX. Además, la familia Trump recibe ~75% de los ingresos por venta de tokens y un fondo estatal de Abu Dhabi tiene 49% de participación: conflicto de interés serio y riesgo regulatorio binario según el ciclo político de EE.UU.',
      pos: 'El proyecto cripto más políticamente expuesto de la lista: su valoración depende tanto de fundamentos DeFi como de eventos políticos y titulares.',
    },
    en: {
      what: 'DeFi protocol linked to the Trump family, with two products: the USD1 stablecoin and the WLFI governance token.',
      tok: 'Token originally non-transferable (enabled for trading in July 2025 after a community vote), 5% voting-power cap per wallet, max supply of 100,000M.',
      risks: 'In April 2026 it was reported that WLFI used 5,000M of its own governance tokens as collateral to borrow $75M in USD1 from Dolomite, a lending protocol whose co-founder advises WLFI, draining the depositor pool and drawing comparisons to the circular dynamics of FTX. In addition, the Trump family receives ~75% of token-sale revenues and an Abu Dhabi state fund holds a 49% stake: a serious conflict of interest and binary regulatory risk tied to the U.S. political cycle.',
      pos: 'The most politically exposed crypto project on the list: its valuation depends as much on DeFi fundamentals as on political events and headlines.',
    },
  },

  'worldcoin-wld': {
    ticker: 'WLD', name: 'Worldcoin', rank: 46, cat: 'ai', tags: ['ai'],
    warn: null,
    es: {
      what: 'Proyecto de Sam Altman (OpenAI) que usa escaneo biométrico del iris (el Orb) para crear una identidad digital única por persona, distribuyendo el token WLD como incentivo de registro.',
      cats: 'La narrativa de prueba de humanidad gana relevancia a medida que el contenido generado por IA satura internet.',
      risks: 'Preocupaciones regulatorias y de privacidad sobre biometría en múltiples países (varios han restringido la operación de Worldcoin); adopción de la identidad digital aún incipiente frente al volumen de tokens distribuidos.',
      pos: 'Apuesta de largo plazo y alto riesgo regulatorio a que la verificación de humanidad será infraestructura crítica en la era de agentes de IA.',
    },
    en: {
      what: 'Sam Altman (OpenAI) project that uses biometric iris scanning (the Orb) to create a unique digital identity per person, distributing the WLD token as a sign-up incentive.',
      cats: 'The proof-of-humanity narrative gains relevance as AI-generated content saturates the internet.',
      risks: 'Regulatory and privacy concerns over biometrics in multiple countries (several have restricted Worldcoin operations); digital-identity adoption still incipient relative to the volume of tokens distributed.',
      pos: 'A long-term, high-regulatory-risk bet that humanity verification will be critical infrastructure in the age of AI agents.',
    },
  },

});
