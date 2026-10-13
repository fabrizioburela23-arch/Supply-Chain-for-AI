"""ontology/history_models.py — LA MEMORIA DE LOS NÚMEROS (docs/BRECHAS_V2.md bloque 2: L3-01, L2-12, L3-14, L3-13).

Antes Khipus no guardaba ni un precio: cada pantalla bajaba 1 año de Yahoo por su cuenta y la historia de cada día
se perdía. Estas tablas viven en el MISMO `Base` de la ontología (init_schema las crea; sin DATABASE_URL no existen
y todo sigue como antes, en vivo):

  instruments        empresa ≠ instrumento (L3-13): un instrumento por símbolo (acción, ADR, OTC, ETF, índice, FX);
                     se siembra desde el catálogo (el `mkt` de hoy es el PRIMARIO; los casos dudosos quedan con
                     `review` para que Fabrizio elija — docs/REVISION_INSTRUMENTOS.md —, nada se cambia solo)
  prices_eod         cierres diarios (open/high/low/close/adj_close/volume) por (instrumento, fuente, fecha)
  price_adjustments  splits/dividendos detectados al re-bajar una ventana: el factor que hay que aplicar a las
                     filas YA guardadas (append-only: nunca se reescribe un precio; la corrección es una fila nueva)
  fx_daily           tipo de cambio diario moneda→USD (L3-14 / L2-01: la historia se convierte FECHA A FECHA)
  metrics_eod        foto diaria por empresa: NRS, grado de flujo, cierre, capitalización
  positions_eod      foto diaria de posiciones: las del usuario (eco_pos / kh_portfolios sincronizadas por
                     /api/user-state) y las de las cuentas de corretaje

Todas menos `instruments` son APPEND-ONLY en la base (core/ledger_ddl.APPEND_ONLY_TABLES: UPDATE/DELETE/TRUNCATE
fallan). `instruments` es catálogo de referencia: el código solo INSERTA (ON CONFLICT DO NOTHING).
"""
from sqlalchemy import (
    BigInteger, Boolean, Column, Date, DateTime, Float, Identity, Index, Integer, PrimaryKeyConstraint, String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB

from ontology.models import Base


class Instrument(Base):
    __tablename__ = 'instruments'

    id = Column(String(32), primary_key=True)                 # el símbolo tal como lo pide Yahoo: NVDA, 2330.TW, JPYUSD=X
    company_id = Column(String(120), nullable=True, index=True)   # nodo del grafo (None para FX/índices)
    ticker = Column(String(32), nullable=False)
    exchange = Column(String(40), nullable=True)
    currency = Column(String(8), nullable=True)               # moneda esperada (la REAL de cada cierre va en prices_eod)
    kind = Column(String(12), nullable=False, default='equity')   # equity | adr | otc | etf | index | rate | fx
    is_primary = Column(Boolean, nullable=False, default=True)
    review = Column(String(24), nullable=True)                # multi_listed | otc_adr | None
    note = Column(JSONB, nullable=True)                       # texto 'ticker' del catálogo y otros listados
    source = Column(String(24), nullable=False, default='catalog')
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PriceEOD(Base):
    __tablename__ = 'prices_eod'
    __table_args__ = (PrimaryKeyConstraint('instrument_id', 'source', 'date', name='pk_prices_eod'),
                      Index('ix_prices_eod_date', 'date'))

    instrument_id = Column(String(32), nullable=False)
    source = Column(String(24), nullable=False)               # yahoo
    date = Column(Date, nullable=False)                       # día de la BOLSA (gmtoffset), no el UTC
    open = Column(Float, nullable=True)
    high = Column(Float, nullable=True)
    low = Column(Float, nullable=True)
    close = Column(Float, nullable=True)
    adj_close = Column(Float, nullable=True)                  # ajustado por splits y dividendos AL BAJARLO
    volume = Column(BigInteger, nullable=True)
    currency = Column(String(8), nullable=True)
    ingested_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PriceAdjustment(Base):
    __tablename__ = 'price_adjustments'
    __table_args__ = (Index('ix_price_adj_inst', 'instrument_id', 'source'),)

    id = Column(BigInteger, Identity(always=False), primary_key=True)
    instrument_id = Column(String(32), nullable=False)
    source = Column(String(24), nullable=False)
    before_date = Column(Date, nullable=False)                # se aplica a las filas con fecha < before_date …
    factor = Column(Float, nullable=False)                    # … guardadas ANTES de detected_at
    detected_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    evidence = Column(JSONB, nullable=True)                   # {date, stored, fetched}


class FxDaily(Base):
    __tablename__ = 'fx_daily'
    __table_args__ = (PrimaryKeyConstraint('ccy', 'source', 'date', name='pk_fx_daily'),)

    ccy = Column(String(8), nullable=False)                   # JPY, EUR… (moneda MAYOR: GBp/ZAc/ILA se dividen al leer)
    source = Column(String(24), nullable=False)
    date = Column(Date, nullable=False)
    rate_to_usd = Column(Float, nullable=False)               # 1 unidad de ccy = rate USD
    ingested_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class MetricsEOD(Base):
    __tablename__ = 'metrics_eod'
    __table_args__ = (PrimaryKeyConstraint('entity_id', 'date', name='pk_metrics_eod'),
                      Index('ix_metrics_eod_date', 'date'))

    entity_id = Column(String(120), nullable=False)
    date = Column(Date, nullable=False)
    nrs = Column(Integer, nullable=True)
    flow_degree = Column(Integer, nullable=True)
    instrument_id = Column(String(32), nullable=True)
    close = Column(Float, nullable=True)                      # moneda local
    currency = Column(String(8), nullable=True)
    price_usd = Column(Float, nullable=True)
    mcap_usd_b = Column(Float, nullable=True)
    graph_generation = Column(String(64), nullable=True)
    source = Column(JSONB, nullable=True)                     # {nrs: 'hot_card'|'catalog', price: 'prices_eod'|…}
    ingested_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PositionEOD(Base):
    __tablename__ = 'positions_eod'
    __table_args__ = (PrimaryKeyConstraint('owner_hash', 'portfolio', 'instrument_id', 'date', name='pk_positions_eod'),
                      Index('ix_positions_eod_date', 'date'))

    owner_hash = Column(String(64), nullable=False)           # hash del dueño (user_state) o 'broker:<cliente>'
    portfolio = Column(String(80), nullable=False)            # market | pf:<id> | alpaca
    instrument_id = Column(String(32), nullable=False)
    date = Column(Date, nullable=False)
    qty = Column(Float, nullable=False)
    price = Column(Float, nullable=True)                      # cierre local de ese día
    currency = Column(String(8), nullable=True)
    price_usd = Column(Float, nullable=True)
    value_usd = Column(Float, nullable=True)
    source = Column(String(32), nullable=False)               # user_state:eco_pos | user_state:kh_portfolios | alpaca
    ingested_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


HISTORY_APPEND_ONLY = ('prices_eod', 'price_adjustments', 'fx_daily', 'metrics_eod', 'positions_eod')
