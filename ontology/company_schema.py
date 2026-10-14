"""ontology/company_schema.py — espejo Pydantic v2 de `data/import/company.schema.json` (khipus.company/1; E2.1).

`jsonschema` NO está en requirements: la ficha de UNA empresa se valida con estos modelos (estrictos: `extra='forbid'`
en todos los niveles = `additionalProperties`/`unevaluatedProperties: false`; modo JSON estricto: un número no es
texto, un bool no es "true"). El artefacto `ontology.import_schema` lleva el JSON Schema; tests/test_import_schema.py
exige que `model_json_schema()` sea EQUIVALENTE al artefacto (forma normalizada: propiedades, obligatorios,
enumeraciones, patrones, rangos, cierre) y que los 13 negativos del plan se rechacen.

Lo que el JSON Schema expresa con if/then/anyOf va en validadores (`_coherent`): papel coherente con el tipo de
vínculo, `ended` exige `end`, puesto de mercado con rango o cuota, planta por id o por nombre + país.
"""
import json
from datetime import date, datetime
from typing import Annotated, Any, List, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

SCHEMA_ID = 'khipus.company/1'

# ── patrones (copiados del artefacto; la prueba de equivalencia los compara) ────────────────────────────────────
DATE_PARTIAL = r'^(19|20)[0-9]{2}(-(0[1-9]|1[0-2])(-(0[1-9]|[12][0-9]|3[01]))?)?$'
URL = r'^https?://[^\s/]+\.[^\s]+$'
COUNTRY = r'^[A-Z]{2}$'
CURRENCY = r'^[A-Z]{3}$'
MIC = r'^[A-Z0-9]{4}$'
LEI = r'^[A-Z0-9]{18}[0-9]{2}$'
ISIN = r'^[A-Z]{2}[A-Z0-9]{9}[0-9]$'
CIK = r'^[0-9]{10}$'
QID = r'^Q[1-9][0-9]*$'
FIGI = r'^BBG[A-Z0-9]{9}$'
YAHOO = r'^[A-Z0-9^][A-Z0-9.=\-^]{0,19}$'
TICKER = r'^[A-Z0-9][A-Z0-9.\-]{0,14}$'
DOMAIN = r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$'
RECORD_ID = r'^[A-Za-z0-9][A-Za-z0-9._:-]{2,79}$'
KHIPUS_ID = r'^[A-Za-z][A-Za-z0-9_]{1,79}$'
CAT = r'^[a-z][a-z0-9_]{1,39}$'
PERIOD = r'^(FY[0-9]{4}|[0-9]{4}-Q[1-4]|TTM-[0-9]{4}-[0-9]{2}|point)$'
LANG = r'^[a-z]{2}(-[A-Za-z]{2,4})?$'
REGION_MP = r'^(GLOBAL|[A-Z]{2}|EU|ASIA|LATAM)$'
REGION_EXPO = r'^(GLOBAL|OTHER|[A-Z]{2}|EU|ASIA|LATAM|NA|EMEA|APAC)$'
PROD_ID = r'^prod-[0-9]{3}$'
FAC_ID = r'^fac-[0-9]{3}$'
REL_ID = r'^[A-Za-z0-9._-]{1,40}$'
NAICS = r'^[0-9]{2,6}$'
FYE = r'^(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$'
QPERIOD = r'^[0-9]{4}-Q[1-4]$'

SourceKind = Literal['primary', 'press', 'trade', 'corporate', 'rumor', 'aggregator', 'state']
RelType = Literal['supply', 'fab', 'cloud', 'license', 'ppa', 'deploy', 'owns', 'invest', 'partner']
ThisRole = Literal['supplier', 'customer', 'investor', 'investee', 'owner', 'owned', 'partner']
FLOW_RELS = ('supply', 'fab', 'cloud', 'license', 'ppa', 'deploy')
# papel admitido por tipo de vínculo (el if/then del artefacto)
ROLE_BY_REL = {**{r: ('supplier', 'customer') for r in FLOW_RELS}, 'invest': ('investor', 'investee'),
               'owns': ('owner', 'owned'), 'partner': ('partner',)}
# claves que el servidor trae EN VIVO o calcula: nunca entran en una ficha ($comment del artefacto)
FORBIDDEN_KEYS = ('price', 'market_cap', 'mktcap', 'mktcap_b', 'enterprise_value', 'ev', 'pe', 'pe_ratio', 'volume',
                  'fx_rate', 'shares_outstanding', 'valuation_in_talks', 'nrs', 'flow_degree', 'impact')

DatePartial = Annotated[str, Field(pattern=DATE_PARTIAL)]
Url = Annotated[str, Field(max_length=600, pattern=URL)]
Country = Annotated[str, Field(pattern=COUNTRY)]
Currency = Annotated[str, Field(pattern=CURRENCY)]
Mic = Annotated[str, Field(pattern=MIC)]
Conf = Annotated[float, Field(ge=0, le=1)]


class _M(BaseModel):
    """Base: campos desconocidos = error; JSON estricto (validar con `validate_record`)."""
    model_config = ConfigDict(extra='forbid', strict=True)


# ── procedencia ─────────────────────────────────────────────────────────────────────────────────────────────────
class Evidence(_M):
    source_url: Url
    source_name: Annotated[str, Field(max_length=160)] = None
    source_kind: SourceKind = None
    published_at: DatePartial = None
    as_of: DatePartial
    retrieved_at: date = None
    quote: Annotated[str, Field(max_length=500)] = None


class RelationEvidence(Evidence):
    """La evidencia de un vínculo exige tipo de fuente y cita textual."""
    source_kind: SourceKind
    quote: Annotated[str, Field(max_length=500)]


class FactBase(_M):
    value: Any
    source_url: Url
    source_name: Annotated[str, Field(max_length=160)] = None
    source_kind: SourceKind = None
    as_of: DatePartial
    retrieved_at: date = None
    confidence: Conf
    quote: Annotated[str, Field(max_length=500)] = None
    also_sources: Annotated[List[Evidence], Field(max_length=5)] = None
    note: Annotated[str, Field(max_length=300)] = None


class FStr(FactBase):
    value: Annotated[str, Field(min_length=1, max_length=2000)]


class FTextEs(FactBase):
    value: Annotated[str, Field(min_length=10, max_length=1200)]
    value_en: Annotated[str, Field(min_length=10, max_length=1200)]


class FNum(FactBase):
    value: float
    unit: Annotated[str, Field(max_length=30)] = None


class FInt(FactBase):
    value: Annotated[int, Field(ge=0)]


class FPct(FactBase):
    value: Annotated[float, Field(ge=-100000, le=100)]


class FDate(FactBase):
    value: DatePartial


class FBool(FactBase):
    value: bool


class FMoney(FactBase):
    value: float
    currency: Currency
    period: Annotated[str, Field(pattern=PERIOD)] = None


class FCountry(FactBase):
    value: Country


class FSharePct(FactBase):
    value: Annotated[float, Field(ge=0, le=100)]


class FQty(FactBase):
    value: Annotated[float, Field(ge=0)]
    unit: Annotated[str, Field(min_length=1, max_length=30)]


class FStatus(FactBase):
    value: Literal['public', 'private', 'subsidiary', 'state_owned', 'cooperative', 'delisted', 'bankrupt',
                   'acquired', 'merged', 'defunct']


# ── identidad ───────────────────────────────────────────────────────────────────────────────────────────────────
class NationalRegistry(_M):
    country: Country
    registry: Annotated[str, Field(max_length=80)] = None
    number: Annotated[str, Field(max_length=40)]


class CounterpartyIds(_M):
    lei: Annotated[str, Field(pattern=LEI)] = None
    isin: Annotated[List[Annotated[str, Field(pattern=ISIN)]], Field(max_length=10)] = None
    cik: Annotated[str, Field(pattern=CIK)] = None
    wikidata_qid: Annotated[str, Field(pattern=QID)] = None
    figi: Annotated[List[Annotated[str, Field(pattern=FIGI)]], Field(max_length=10)] = None
    yahoo_symbol: Annotated[str, Field(pattern=YAHOO)] = None
    ticker: Annotated[str, Field(pattern=TICKER)] = None
    exchange_mic: Mic = None
    domain: Annotated[str, Field(pattern=DOMAIN)] = None
    national_registry: Annotated[List[NationalRegistry], Field(max_length=4)] = None


class Counterparty(_M):
    name: Annotated[str, Field(min_length=2, max_length=160)]
    khipus_id: Annotated[str, Field(pattern=KHIPUS_ID)] = None
    record_id: Annotated[str, Field(max_length=80)] = None
    ids: CounterpartyIds = None
    country: Country = None
    object_type: Literal['Company', 'Org', 'Country', 'Policy', 'Product', 'Tech', 'Material', 'Energy'] = None


class OtherName(_M):
    name: Annotated[str, Field(min_length=2, max_length=160)]
    kind: Literal['acronym', 'local_script', 'brand', 'former', 'transliteration', 'common']
    lang: Annotated[str, Field(pattern=LANG)] = None
    until: DatePartial = None


class GeoPoint(_M):
    lat: Annotated[float, Field(ge=-90, le=90)]
    lon: Annotated[float, Field(ge=-180, le=180)]
    precision: Literal['exact', 'city', 'region', 'country']
    source_url: Url
    as_of: DatePartial


class Identity(_M):
    legal_name: FStr
    short_name: Annotated[str, Field(min_length=2, max_length=120)]
    other_names: Annotated[List[OtherName], Field(max_length=25)] = None
    ids: CounterpartyIds = None
    ids_source: Evidence = None
    status: FStatus
    founded: FDate = None
    hq_country: FCountry
    hq_city: FStr = None
    website: Url = None
    hq_coords: GeoPoint = None
    incorporation_country: FCountry = None
    successor: Counterparty = None


class ResearchMeta(_M):
    researcher: Annotated[str, Field(max_length=80)]
    researched_at: datetime
    method: Literal['manual', 'ai_assisted', 'mixed']
    tools: Annotated[List[Annotated[str, Field(max_length=60)]], Field(max_length=10)] = None
    tier: Literal['A', 'B', 'C']
    revision: Annotated[int, Field(ge=1)] = None
    not_found: Annotated[List[Annotated[str, Field(max_length=120)]], Field(max_length=80)] = None
    notes: Annotated[str, Field(max_length=2000)] = None
    priority: Literal['P1', 'P2', 'P3'] = None
    batch: Annotated[str, Field(max_length=60)] = None
    sources_consulted: Annotated[List[Url], Field(max_length=40)] = None


# ── cotizaciones / clasificación / perfil ───────────────────────────────────────────────────────────────────────
class Listing(_M):
    ticker: Annotated[str, Field(pattern=TICKER)]
    exchange_mic: Mic
    yahoo_symbol: Annotated[str, Field(pattern=YAHOO)]
    finnhub_symbol: Annotated[str, Field(max_length=24)] = None
    isin: Annotated[str, Field(pattern=ISIN)] = None
    currency: Currency
    kind: Literal['equity', 'a_share', 'h_share', 'adr', 'gdr', 'otc', 'preferred', 'dual_class']
    is_primary: bool
    share_class: Annotated[str, Field(max_length=20)] = None
    listed_since: DatePartial = None
    delisted_at: DatePartial = None
    source_url: Url
    as_of: DatePartial
    confidence: Conf = None
    ordinary_per_depositary: Annotated[float, Field(gt=0)] = None
    figi: Annotated[str, Field(pattern=FIGI)] = None


class CatProposed(_M):
    id: Annotated[str, Field(pattern=CAT)]
    label_es: Annotated[str, Field(max_length=60)]
    label_en: Annotated[str, Field(max_length=60)]
    sector: Annotated[str, Field(max_length=30)]


ChainLayer = Literal['raw_materials', 'refining', 'components', 'equipment', 'fabrication', 'packaging', 'systems',
                     'networking', 'power', 'datacenter', 'cloud', 'models', 'software', 'applications',
                     'distribution', 'logistics', 'finance', 'real_estate', 'government', 'space', 'defense',
                     'robotics']


class Classification(_M):
    cat: Annotated[str, Field(pattern=CAT)]
    cat_proposed: CatProposed = None
    chain_layers: Annotated[List[ChainLayer], Field(max_length=8, json_schema_extra={'uniqueItems': True})] = None
    naics: Annotated[str, Field(pattern=NAICS)] = None
    gics_industry: Annotated[str, Field(max_length=80)] = None
    source_url: Url = None
    cats_secondary: Annotated[List[Annotated[str, Field(pattern=CAT)]],
                              Field(max_length=5, json_schema_extra={'uniqueItems': True})] = None

    @field_validator('chain_layers', 'cats_secondary')
    @classmethod
    def _unique(cls, v):
        if v is not None and len(set(v)) != len(v):
            raise ValueError('elementos repetidos (uniqueItems) / repeated items (uniqueItems)')
        return v


class KeyPerson(_M):
    name: Annotated[str, Field(max_length=120)]
    role: Annotated[str, Field(max_length=80)]
    since: DatePartial = None
    source_url: Url
    as_of: DatePartial


class Profile(_M):
    summary: FTextEs
    what_it_supplies: FTextEs = None
    moat: FTextEs = None
    growth: FTextEs = None
    strategy: FTextEs = None
    employees: FInt = None
    key_people: Annotated[List[KeyPerson], Field(max_length=12)] = None
    description: FTextEs = None
    geo_risk: FTextEs = None
    technologies: Annotated[List[Annotated[str, Field(max_length=80)]], Field(max_length=30)] = None


# ── estructura / mercado / productos / plantas ──────────────────────────────────────────────────────────────────
class Holding(_M):
    entity: Counterparty
    pct: FSharePct
    voting_pct: FSharePct = None
    since: DatePartial = None
    until: DatePartial = None


class Corporate(_M):
    parent: Holding = None
    ultimate_parent: Holding = None
    major_shareholders: Annotated[List[Holding], Field(max_length=20)] = None
    subsidiaries: Annotated[List[Holding], Field(max_length=40)] = None
    state_ownership_pct: FSharePct = None
    merged_into: Counterparty = None


class MarketPosition(_M):
    market: Annotated[str, Field(max_length=160)]
    market_en: Annotated[str, Field(max_length=160)] = None
    metric: Literal['revenue', 'units', 'capacity', 'installed_gwh', 'shipments', 'volume', 'other']
    region: Annotated[str, Field(pattern=REGION_MP)]
    rank: Annotated[int, Field(ge=1, le=100)] = None
    share_pct: Annotated[float, Field(ge=0, le=100)] = None
    period: Annotated[str, Field(max_length=20)] = None
    source_url: Url
    source_name: Annotated[str, Field(max_length=160)] = None
    source_kind: SourceKind = None
    as_of: DatePartial
    confidence: Conf
    quote: Annotated[str, Field(max_length=500)] = None

    @model_validator(mode='after')
    def _coherent(self):
        if self.rank is None and self.share_pct is None:
            raise ValueError('un puesto de mercado necesita rank o share_pct / a market position needs rank or share_pct')
        return self


class Product(_M):
    name: Annotated[str, Field(max_length=120)]
    category: Annotated[str, Field(max_length=80)] = None
    description_es: Annotated[str, Field(max_length=500)] = None
    description_en: Annotated[str, Field(max_length=500)] = None
    share_of_revenue: FSharePct = None
    launched: DatePartial = None
    discontinued: DatePartial = None
    source_url: Url = None
    product_id: Annotated[str, Field(pattern=PROD_ID)] = None


class Capacity(_M):
    value: Annotated[float, Field(ge=0)]
    unit: Annotated[str, Field(max_length=30)]


class Facility(_M):
    name: Annotated[str, Field(max_length=160)]
    kind: Literal['fab', 'assembly', 'cell_plant', 'mine', 'refinery', 'smelter', 'chemical_plant', 'datacenter',
                  'power_plant', 'substation', 'r_and_d', 'hq', 'warehouse', 'port', 'launch_site', 'office', 'other']
    country: Country
    region: Annotated[str, Field(max_length=80)] = None
    city: Annotated[str, Field(max_length=80)] = None
    lat: Annotated[float, Field(ge=-90, le=90)] = None
    lon: Annotated[float, Field(ge=-180, le=180)] = None
    capacity: Capacity = None
    status: Literal['operating', 'ramping', 'construction', 'planned', 'paused', 'closed']
    start: DatePartial = None
    end: DatePartial = None
    owner_share_pct: Annotated[float, Field(ge=0, le=100)] = None
    source_url: Url
    as_of: DatePartial
    confidence: Conf = None
    facility_id: Annotated[str, Field(pattern=FAC_ID)] = None


# ── financieros / rondas / exposición / regulación / riesgos ────────────────────────────────────────────────────
class Segment(_M):
    name: Annotated[str, Field(max_length=80)]
    revenue: FMoney


class AnnualFinancials(_M):
    fiscal_year: Annotated[int, Field(ge=1990, le=2100)]
    revenue: FMoney = None
    gross_margin_pct: FPct = None
    operating_margin_pct: FPct = None
    net_income: FMoney = None
    capex: FMoney = None
    r_and_d: FMoney = None
    backlog: FMoney = None
    segments: Annotated[List[Segment], Field(max_length=15)] = None


class QuarterlyFinancials(_M):
    period: Annotated[str, Field(pattern=QPERIOD)]
    revenue: FMoney = None
    gross_margin_pct: FPct = None
    operating_margin_pct: FPct = None
    net_income: FMoney = None
    capex: FMoney = None
    r_and_d: FMoney = None
    backlog: FMoney = None
    segments: Annotated[List[Segment], Field(max_length=15)] = None


class Financials(_M):
    fiscal_year_end: Annotated[str, Field(pattern=FYE)] = None
    reporting_currency: Currency = None
    annual: Annotated[List[AnnualFinancials], Field(max_length=10)] = None
    capex_guidance: FMoney = None
    quarterly: Annotated[List[QuarterlyFinancials], Field(max_length=12)] = None
    capacity_total: Annotated[List[FQty], Field(max_length=10)] = None


class FundingRound(_M):
    date: DatePartial
    round: Annotated[str, Field(max_length=40)]
    amount: Annotated[float, Field(ge=0)] = None
    post_money_valuation: Annotated[float, Field(ge=0)] = None
    currency: Currency = None
    lead_investors: Annotated[List[Counterparty], Field(max_length=10)] = None
    other_investors: Annotated[List[Counterparty], Field(max_length=30)] = None
    status: Literal['closed', 'announced'] = None
    source_url: Url
    source_kind: SourceKind = None
    as_of: DatePartial
    confidence: Conf
    quote: Annotated[str, Field(max_length=500)] = None


class RevenueByRegion(_M):
    region: Annotated[str, Field(pattern=REGION_EXPO)]
    pct: FSharePct


class Subsidy(_M):
    program: Annotated[str, Field(max_length=160)]
    country: Country = None
    amount: FMoney = None
    date: DatePartial = None
    status: Literal['awarded', 'announced', 'disbursed', 'cancelled'] = None
    source_url: Url
    as_of: DatePartial


class Exposure(_M):
    revenue_by_region: Annotated[List[RevenueByRegion], Field(max_length=20)] = None
    customer_concentration_top1_pct: FSharePct = None
    customer_concentration_top5_pct: FSharePct = None
    export_controls: FStr = None
    sanctions: FStr = None
    subsidies: Annotated[List[Subsidy], Field(max_length=15)] = None


class RestrictedList(_M):
    list: Literal['BIS_entity_list', 'BIS_MEU', 'BIS_unverified', 'OFAC_SDN', 'OFAC_NS_CMIC', 'DoD_1260H',
                  'FCC_covered', 'UFLPA', 'EU_sanctions', 'UK_sanctions', 'CN_unreliable_entity', 'CN_export_control',
                  'other']
    list_other: Annotated[str, Field(max_length=120)] = None
    since: DatePartial
    until: DatePartial = None
    entity_named: Annotated[str, Field(max_length=200)] = None
    source_url: Url
    as_of: DatePartial
    confidence: Conf


class Litigation(_M):
    kind: Literal['antitrust', 'patent', 'trade', 'regulatory', 'securities', 'other']
    text_es: Annotated[str, Field(max_length=500)]
    text_en: Annotated[str, Field(max_length=500)]
    status: Literal['open', 'settled', 'won', 'lost', 'appeal']
    since: DatePartial = None
    source_url: Url
    as_of: DatePartial


class Regulatory(_M):
    restricted_lists: Annotated[List[RestrictedList], Field(max_length=20)] = None
    litigation: Annotated[List[Litigation], Field(max_length=15)] = None


class Risk(_M):
    kind: Literal['geopolitical', 'regulatory', 'concentration', 'technology', 'financial', 'legal', 'supply', 'esg',
                  'governance']
    text_es: Annotated[str, Field(max_length=500)]
    text_en: Annotated[str, Field(max_length=500)]
    factor_hint: Annotated[str, Field(max_length=80)] = None
    source_url: Url
    as_of: DatePartial


class Innovation(_M):
    patent_families: FInt = None
    r_and_d_staff: FInt = None
    notable_ip: FTextEs = None


class Esg(_M):
    emissions_scope1_tco2e: FNum = None
    emissions_scope2_tco2e: FNum = None
    energy_use_mwh: FNum = None
    water_use_m3: FNum = None
    renewable_share_pct: FSharePct = None
    controversies: Annotated[List[Risk], Field(max_length=10)] = None


class TimelineEvent(_M):
    date: DatePartial
    kind: Literal['founded', 'ipo', 'delisting', 'acquisition', 'divestiture', 'merger', 'funding', 'plant_announced',
                  'plant_opened', 'plant_closed', 'major_contract', 'product_launch', 'sanction', 'leadership_change',
                  'bankruptcy', 'guidance_change', 'other']
    text_es: Annotated[str, Field(max_length=400)]
    text_en: Annotated[str, Field(max_length=400)]
    counterparty: Counterparty = None
    source_url: Url
    source_kind: SourceKind = None
    as_of: DatePartial
    confidence: Conf


# ── vínculos ────────────────────────────────────────────────────────────────────────────────────────────────────
class FacilityRef(_M):
    facility_id: Annotated[str, Field(pattern=FAC_ID)] = None
    name: Annotated[str, Field(max_length=160)] = None
    country: Country = None
    city: Annotated[str, Field(max_length=80)] = None
    share_of_flow_pct: Annotated[float, Field(ge=0, le=100)] = None
    source_url: Url = None
    as_of: DatePartial = None
    quote: Annotated[str, Field(max_length=500)] = None

    @model_validator(mode='after')
    def _coherent(self):
        if self.facility_id is None and (self.name is None or self.country is None):
            raise ValueError('una planta se identifica por facility_id o por name + country / '
                             'a facility is identified by facility_id or by name + country')
        return self


class Dependency(_M):
    criticality: Annotated[int, Field(ge=1, le=6)]
    sole_source: bool = None
    share_of_supplier_revenue: FSharePct = None
    share_of_customer_purchases: FSharePct = None
    contract_value: FMoney = None
    volume: FQty = None
    substitutability_months: Annotated[int, Field(ge=0, le=120)] = None
    supplier_facility: FacilityRef = None
    customer_facility: FacilityRef = None
    component: Annotated[str, Field(max_length=120)] = None
    product_affected: Annotated[str, Field(max_length=120)] = None
    bom_share_pct: FSharePct = None
    tier: Annotated[int, Field(ge=1, le=4)] = None
    alternatives: Annotated[List[Annotated[str, Field(max_length=160)]], Field(max_length=10)] = None


class Relation(_M):
    relation_id: Annotated[str, Field(pattern=REL_ID)]
    counterparty: Counterparty
    rel_type: RelType
    this_role: ThisRole
    label_es: Annotated[str, Field(min_length=3, max_length=300)]
    label_en: Annotated[str, Field(min_length=3, max_length=300)]
    product: Annotated[str, Field(max_length=120)] = None
    status: Literal['active', 'ended', 'announced', 'planned', 'rumored', 'disputed']
    start: DatePartial = None
    end: DatePartial = None
    dependency: Dependency
    evidence: Annotated[List[RelationEvidence], Field(min_length=1, max_length=6)]
    confidence: Conf

    @model_validator(mode='after')
    def _coherent(self):
        ok = ROLE_BY_REL.get(self.rel_type, ())
        if self.this_role not in ok:
            raise ValueError(f'this_role {self.this_role!r} no corresponde a rel_type {self.rel_type!r} (admite '
                             f'{"/".join(ok)}) / this_role does not match rel_type')
        if self.status == 'ended' and self.end is None:
            raise ValueError('un vínculo terminado (ended) necesita end / an ended relation needs end')
        return self


class LiveHooks(_M):
    news_keywords: Annotated[List[Annotated[str, Field(max_length=80)]], Field(max_length=12)] = None
    ir_url: Url = None
    filings_feed: Annotated[str, Field(max_length=200)] = None
    rss_urls: Annotated[List[Url], Field(max_length=5)] = None
    valuation_watch: bool = None


# ── la ficha ────────────────────────────────────────────────────────────────────────────────────────────────────
class CompanyRecord(_M):
    """UNA empresa = una ficha khipus.company/1 (una línea de un .jsonl)."""
    schema_: Literal['khipus.company/1'] = Field(alias='schema')
    record_id: Annotated[str, Field(pattern=RECORD_ID)]
    khipus_id_hint: Annotated[str, Field(pattern=KHIPUS_ID)] = None
    research_meta: ResearchMeta
    identity: Identity
    listings: Annotated[List[Listing], Field(max_length=12)] = None
    classification: Classification
    profile: Profile
    corporate: Corporate = None
    market_position: Annotated[List[MarketPosition], Field(max_length=30)] = None
    products: Annotated[List[Product], Field(max_length=40)] = None
    facilities: Annotated[List[Facility], Field(max_length=80)] = None
    financials: Financials = None
    funding: Annotated[List[FundingRound], Field(max_length=40)] = None
    exposure: Exposure = None
    regulatory: Regulatory = None
    risks: Annotated[List[Risk], Field(max_length=30)] = None
    innovation: Innovation = None
    esg: Esg = None
    timeline: Annotated[List[TimelineEvent], Field(max_length=60)] = None
    relations: Annotated[List[Relation], Field(max_length=300)] = None
    live_hooks: LiveHooks = None


# ── validación con mensajes bilingües ───────────────────────────────────────────────────────────────────────────
_ES = {
    'missing': 'falta el campo obligatorio', 'extra_forbidden': 'campo no permitido (desconocido o prohibido)',
    'string_pattern_mismatch': 'formato inválido', 'string_too_short': 'texto demasiado corto',
    'string_too_long': 'texto demasiado largo', 'too_long': 'lista demasiado larga',
    'too_short': 'lista demasiado corta', 'greater_than_equal': 'por debajo del mínimo',
    'less_than_equal': 'por encima del máximo', 'greater_than': 'debe ser mayor que el mínimo',
    'literal_error': 'valor fuera de la lista permitida', 'string_type': 'debe ser texto',
    'int_type': 'debe ser un entero', 'float_type': 'debe ser un número', 'bool_type': 'debe ser verdadero/falso',
    'list_type': 'debe ser una lista', 'dict_type': 'debe ser un objeto', 'model_type': 'debe ser un objeto',
    'datetime_parsing': 'fecha-hora inválida', 'date_parsing': 'fecha inválida', 'date_type': 'fecha inválida',
    'datetime_type': 'fecha-hora inválida', 'value_error': 'regla de coherencia', 'json_invalid': 'JSON inválido',
    'int_parsing': 'debe ser un entero', 'float_parsing': 'debe ser un número', 'set_type': 'debe ser una lista',
    'int_from_float': 'debe ser un entero (sin decimales)',
}


def _path(loc):
    out = []
    for x in loc:
        if isinstance(x, int):
            out.append(f'[{x}]')
        else:
            out.append(('.' if out else '') + str(x))
    return ''.join(out) or '(raíz)'


def validate_record(data):
    """Dict (o texto JSON) → (CompanyRecord | None, errores). Modo JSON estricto: lo que no entra en el artefacto no
    entra aquí. Cada error: {path, type, msg_es, msg_en}."""
    raw = data if isinstance(data, (str, bytes)) else json.dumps(data, ensure_ascii=False, default=str)
    try:
        return CompanyRecord.model_validate_json(raw), []
    except ValidationError as e:
        errs = []
        for x in e.errors(include_url=False):
            t = x.get('type') or 'error'
            loc = _path(x.get('loc') or ())
            raw_msg = str(x.get('msg') or '')
            last = (x.get('loc') or ('',))[-1]
            hint = ''
            if t == 'extra_forbidden' and str(last) in FORBIDDEN_KEYS:
                hint = ' — dato EN VIVO: lo trae el servidor / LIVE field: the server fetches it'
            errs.append({'path': loc, 'type': t,
                         'msg_es': f'{loc}: {_ES.get(t, raw_msg)}{hint}',
                         'msg_en': f'{loc}: {raw_msg}{hint}'})
        return None, errs


def json_schema():
    """El JSON Schema que Pydantic genera para la ficha (la prueba lo compara con el artefacto)."""
    return CompanyRecord.model_json_schema(by_alias=True)


# ── forma normalizada: para comparar DOS esquemas que dicen lo mismo con distinta sintaxis ───────────────────────
_KEEP = ('type', 'enum', 'const', 'pattern', 'minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum',
         'minLength', 'maxLength', 'minItems', 'maxItems', 'uniqueItems', 'format')


def canonical_shape(schema):
    """Expande $ref/allOf, quita títulos/descripciones/defaults/condicionales (if-then-anyOf de obligatorios, que
    aquí son validadores) y deja {type, properties, required, enum, pattern, rangos, items, closed}. Un `anyOf`
    con rama null (Optional de Pydantic) se reduce a la otra rama. Resultado comparable con ==."""
    defs = dict(schema.get('$defs') or schema.get('definitions') or {})

    def resolve(node, depth=0):
        if depth > 40:
            raise RecursionError('esquema demasiado anidado')
        if not isinstance(node, dict):
            return node
        if '$ref' in node:
            name = node['$ref'].rsplit('/', 1)[-1]
            base = dict(defs[name])
            merged = {**base, **{k: v for k, v in node.items() if k != '$ref'}}
            return resolve(merged, depth + 1)
        if 'allOf' in node:
            merged = {k: v for k, v in node.items() if k != 'allOf'}
            props, req = {}, []
            for part in node['allOf']:
                p = resolve(part, depth + 1)
                props.update(p.get('properties') or {})
                req += list(p.get('required') or [])
                for k in ('closed', *_KEEP):
                    if k in p and k not in merged:
                        merged[k] = p[k]
            props.update(merged.get('properties') or {})
            req += list(merged.get('required') or [])
            merged['properties'] = props
            merged['required'] = req
            return resolve(merged, depth + 1)
        if 'anyOf' in node:
            branches = [b for b in node['anyOf'] if not (isinstance(b, dict) and b.get('type') == 'null')]
            if len(branches) == 1 and all(isinstance(b, dict) for b in node['anyOf']):
                # Optional de Pydantic: la rama no nula + lo demás del nodo (sin default)
                return resolve({**{k: v for k, v in node.items() if k not in ('anyOf', 'default')}, **branches[0]},
                               depth + 1)
            node = {k: v for k, v in node.items() if k != 'anyOf'}     # anyOf de obligatorios: validador
        out = {}
        for k in _KEEP:
            if k in node:
                out[k] = sorted(node[k]) if k == 'enum' else node[k]
        if 'const' in out or 'enum' in out:
            out.pop('type', None)        # un enum/const ya fija el tipo (el artefacto no lo repite)
        if 'properties' in node:
            out['properties'] = {k: resolve(v, depth + 1) for k, v in sorted(node['properties'].items())}
            out['required'] = sorted(set(node.get('required') or []))
        if node.get('additionalProperties') is False or node.get('unevaluatedProperties') is False or node.get('closed'):
            out['closed'] = True
        if 'items' in node:
            out['items'] = resolve(node['items'], depth + 1)
        if out.get('type') == 'number' and 'format' in out:
            out.pop('format')           # Pydantic no marca formato en números
        return out
    return resolve({k: v for k, v in schema.items() if k not in ('$defs', 'definitions')})


def load_artifact_schema(path=None):
    """El JSON Schema del repositorio (data/import/company.schema.json)."""
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(path or os.path.join(root, 'data', 'import', 'company.schema.json'), encoding='utf-8') as fh:
        return json.load(fh)
