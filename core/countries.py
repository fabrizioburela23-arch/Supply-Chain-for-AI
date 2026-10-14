"""core/countries.py — UNA tabla de países: ISO-2 ↔ clave del catálogo ↔ nombre ES/EN ↔ región (lote 2026-10-14).

El catálogo escribe el país de 136 formas ("EEUU", "Estados Unidos (HQ Denver, CO)", "Japón", "Taiwán",
"Hong Kong (China)"…) y `core.world.country_key()` ya las lleva a 47 claves (EEUU, Japon, Corea, ReinoUnido,
Europa, RestoMundo…). Este módulo pone encima el código ISO 3166-1 alfa-2 — lo que traen la investigación
(`hq_country`, `incorporation_country`) y el importador — y los nombres en los dos idiomas. NO reescribe el texto
guardado (las ciudades dan coordenadas finas en core/world.geo_coord): todo se DERIVA al leer.

    iso2_of('Estados Unidos (HQ Denver, CO)') → 'US'    iso2_of('Europa') → None (región)
    region_of('Europa') → 'Europa'                      region_of('Japón') → None
    catalog_key_of('GB') → 'ReinoUnido'                 catalog_key_of('BD') → 'Bangladesh' (sin clave de hoy)
    label('US', 'es') → 'Estados Unidos'                label('US', 'en') → 'United States'

Gemela JS: engine/geo_coords.js (`window.KhipuCountries`, misma tabla GENERADA desde aquí con
`python scripts/build_country_review.py --js`; tests/test_countries.py exige paridad). El NRS NO usa esta tabla: tiene
su propia tabla gobernada (`core.world._NRS_GEO_ALIAS`, nrs.formula) — cambiarla es decisión de Fabrizio
(docs/REVISION_PAISES.md).
"""
import re

# (iso2, nombre EN, nombre ES, clave del catálogo de HOY o None, ¿Europa?)
# Clave None = el país no está hoy en core/world._COUNTRY: su clave "de compatibilidad" es el nombre en inglés.
_ROWS = (
    ('AD', 'Andorra', 'Andorra', None, 1),
    ('AE', 'United Arab Emirates', 'Emiratos Árabes Unidos', 'EAU', 0),
    ('AF', 'Afghanistan', 'Afganistán', None, 0),
    ('AG', 'Antigua and Barbuda', 'Antigua y Barbuda', None, 0),
    ('AI', 'Anguilla', 'Anguila', None, 0),
    ('AL', 'Albania', 'Albania', None, 1),
    ('AM', 'Armenia', 'Armenia', None, 0),
    ('AO', 'Angola', 'Angola', None, 0),
    ('AQ', 'Antarctica', 'Antártida', None, 0),
    ('AR', 'Argentina', 'Argentina', 'Argentina', 0),
    ('AS', 'American Samoa', 'Samoa Americana', None, 0),
    ('AT', 'Austria', 'Austria', 'Austria', 1),
    ('AU', 'Australia', 'Australia', 'Australia', 0),
    ('AW', 'Aruba', 'Aruba', None, 0),
    ('AX', 'Åland Islands', 'Islas Åland', None, 1),
    ('AZ', 'Azerbaijan', 'Azerbaiyán', 'Azerbaiyan', 0),
    ('BA', 'Bosnia and Herzegovina', 'Bosnia y Herzegovina', None, 1),
    ('BB', 'Barbados', 'Barbados', None, 0),
    ('BD', 'Bangladesh', 'Bangladés', None, 0),
    ('BE', 'Belgium', 'Bélgica', 'Belgica', 1),
    ('BF', 'Burkina Faso', 'Burkina Faso', None, 0),
    ('BG', 'Bulgaria', 'Bulgaria', None, 1),
    ('BH', 'Bahrain', 'Baréin', None, 0),
    ('BI', 'Burundi', 'Burundi', None, 0),
    ('BJ', 'Benin', 'Benín', None, 0),
    ('BL', 'Saint Barthélemy', 'San Bartolomé', None, 0),
    ('BM', 'Bermuda', 'Bermudas', None, 0),
    ('BN', 'Brunei', 'Brunéi', None, 0),
    ('BO', 'Bolivia', 'Bolivia', None, 0),
    ('BQ', 'Bonaire, Sint Eustatius and Saba', 'Bonaire, San Eustaquio y Saba', None, 0),
    ('BR', 'Brazil', 'Brasil', 'Brasil', 0),
    ('BS', 'Bahamas', 'Bahamas', None, 0),
    ('BT', 'Bhutan', 'Bután', None, 0),
    ('BV', 'Bouvet Island', 'Isla Bouvet', None, 0),
    ('BW', 'Botswana', 'Botsuana', None, 0),
    ('BY', 'Belarus', 'Bielorrusia', None, 1),
    ('BZ', 'Belize', 'Belice', None, 0),
    ('CA', 'Canada', 'Canadá', 'Canada', 0),
    ('CC', 'Cocos (Keeling) Islands', 'Islas Cocos', None, 0),
    ('CD', 'Democratic Republic of the Congo', 'República Democrática del Congo', None, 0),
    ('CF', 'Central African Republic', 'República Centroafricana', None, 0),
    ('CG', 'Republic of the Congo', 'República del Congo', None, 0),
    ('CH', 'Switzerland', 'Suiza', 'Suiza', 1),
    ('CI', "Côte d'Ivoire", 'Costa de Marfil', None, 0),
    ('CK', 'Cook Islands', 'Islas Cook', None, 0),
    ('CL', 'Chile', 'Chile', 'Chile', 0),
    ('CM', 'Cameroon', 'Camerún', None, 0),
    ('CN', 'China', 'China', 'China', 0),
    ('CO', 'Colombia', 'Colombia', 'Colombia', 0),
    ('CR', 'Costa Rica', 'Costa Rica', None, 0),
    ('CU', 'Cuba', 'Cuba', None, 0),
    ('CV', 'Cape Verde', 'Cabo Verde', None, 0),
    ('CW', 'Curaçao', 'Curazao', None, 0),
    ('CX', 'Christmas Island', 'Isla de Navidad', None, 0),
    ('CY', 'Cyprus', 'Chipre', None, 1),
    ('CZ', 'Czechia', 'Chequia', 'Chequia', 1),
    ('DE', 'Germany', 'Alemania', 'Alemania', 1),
    ('DJ', 'Djibouti', 'Yibuti', None, 0),
    ('DK', 'Denmark', 'Dinamarca', 'Dinamarca', 1),
    ('DM', 'Dominica', 'Dominica', None, 0),
    ('DO', 'Dominican Republic', 'República Dominicana', None, 0),
    ('DZ', 'Algeria', 'Argelia', 'Argelia', 0),
    ('EC', 'Ecuador', 'Ecuador', None, 0),
    ('EE', 'Estonia', 'Estonia', None, 1),
    ('EG', 'Egypt', 'Egipto', 'Egipto', 0),
    ('EH', 'Western Sahara', 'Sáhara Occidental', None, 0),
    ('ER', 'Eritrea', 'Eritrea', None, 0),
    ('ES', 'Spain', 'España', 'Espana', 1),
    ('ET', 'Ethiopia', 'Etiopía', None, 0),
    ('FI', 'Finland', 'Finlandia', 'Finlandia', 1),
    ('FJ', 'Fiji', 'Fiyi', None, 0),
    ('FK', 'Falkland Islands', 'Islas Malvinas', None, 0),
    ('FM', 'Micronesia', 'Micronesia', None, 0),
    ('FO', 'Faroe Islands', 'Islas Feroe', None, 1),
    ('FR', 'France', 'Francia', 'Francia', 1),
    ('GA', 'Gabon', 'Gabón', None, 0),
    ('GB', 'United Kingdom', 'Reino Unido', 'ReinoUnido', 1),
    ('GD', 'Grenada', 'Granada', None, 0),
    ('GE', 'Georgia', 'Georgia', None, 0),
    ('GF', 'French Guiana', 'Guayana Francesa', None, 0),
    ('GG', 'Guernsey', 'Guernsey', None, 1),
    ('GH', 'Ghana', 'Ghana', None, 0),
    ('GI', 'Gibraltar', 'Gibraltar', None, 1),
    ('GL', 'Greenland', 'Groenlandia', None, 0),
    ('GM', 'Gambia', 'Gambia', None, 0),
    ('GN', 'Guinea', 'Guinea', None, 0),
    ('GP', 'Guadeloupe', 'Guadalupe', None, 0),
    ('GQ', 'Equatorial Guinea', 'Guinea Ecuatorial', None, 0),
    ('GR', 'Greece', 'Grecia', 'Grecia', 1),
    ('GS', 'South Georgia and the South Sandwich Islands', 'Islas Georgias del Sur y Sandwich del Sur', None, 0),
    ('GT', 'Guatemala', 'Guatemala', None, 0),
    ('GU', 'Guam', 'Guam', None, 0),
    ('GW', 'Guinea-Bissau', 'Guinea-Bisáu', None, 0),
    ('GY', 'Guyana', 'Guyana', None, 0),
    ('HK', 'Hong Kong', 'Hong Kong', 'HongKong', 0),
    ('HM', 'Heard Island and McDonald Islands', 'Islas Heard y McDonald', None, 0),
    ('HN', 'Honduras', 'Honduras', None, 0),
    ('HR', 'Croatia', 'Croacia', None, 1),
    ('HT', 'Haiti', 'Haití', None, 0),
    ('HU', 'Hungary', 'Hungría', 'Hungria', 1),
    ('ID', 'Indonesia', 'Indonesia', 'Indonesia', 0),
    ('IE', 'Ireland', 'Irlanda', 'Irlanda', 1),
    ('IL', 'Israel', 'Israel', 'Israel', 0),
    ('IM', 'Isle of Man', 'Isla de Man', None, 1),
    ('IN', 'India', 'India', 'India', 0),
    ('IO', 'British Indian Ocean Territory', 'Territorio Británico del Océano Índico', None, 0),
    ('IQ', 'Iraq', 'Irak', None, 0),
    ('IR', 'Iran', 'Irán', 'Iran', 0),
    ('IS', 'Iceland', 'Islandia', None, 1),
    ('IT', 'Italy', 'Italia', 'Italia', 1),
    ('JE', 'Jersey', 'Jersey', None, 1),
    ('JM', 'Jamaica', 'Jamaica', None, 0),
    ('JO', 'Jordan', 'Jordania', None, 0),
    ('JP', 'Japan', 'Japón', 'Japon', 0),
    ('KE', 'Kenya', 'Kenia', 'Kenia', 0),
    ('KG', 'Kyrgyzstan', 'Kirguistán', None, 0),
    ('KH', 'Cambodia', 'Camboya', None, 0),
    ('KI', 'Kiribati', 'Kiribati', None, 0),
    ('KM', 'Comoros', 'Comoras', None, 0),
    ('KN', 'Saint Kitts and Nevis', 'San Cristóbal y Nieves', None, 0),
    ('KP', 'North Korea', 'Corea del Norte', None, 0),
    ('KR', 'South Korea', 'Corea del Sur', 'Corea', 0),
    ('KW', 'Kuwait', 'Kuwait', 'Kuwait', 0),
    ('KY', 'Cayman Islands', 'Islas Caimán', None, 0),
    ('KZ', 'Kazakhstan', 'Kazajistán', 'Kazajistan', 0),
    ('LA', 'Laos', 'Laos', None, 0),
    ('LB', 'Lebanon', 'Líbano', None, 0),
    ('LC', 'Saint Lucia', 'Santa Lucía', None, 0),
    ('LI', 'Liechtenstein', 'Liechtenstein', None, 1),
    ('LK', 'Sri Lanka', 'Sri Lanka', None, 0),
    ('LR', 'Liberia', 'Liberia', None, 0),
    ('LS', 'Lesotho', 'Lesoto', None, 0),
    ('LT', 'Lithuania', 'Lituania', 'Lituania', 1),
    ('LU', 'Luxembourg', 'Luxemburgo', 'Luxemburgo', 1),
    ('LV', 'Latvia', 'Letonia', None, 1),
    ('LY', 'Libya', 'Libia', None, 0),
    ('MA', 'Morocco', 'Marruecos', None, 0),
    ('MC', 'Monaco', 'Mónaco', None, 1),
    ('MD', 'Moldova', 'Moldavia', None, 1),
    ('ME', 'Montenegro', 'Montenegro', None, 1),
    ('MF', 'Saint Martin', 'San Martín', None, 0),
    ('MG', 'Madagascar', 'Madagascar', None, 0),
    ('MH', 'Marshall Islands', 'Islas Marshall', None, 0),
    ('MK', 'North Macedonia', 'Macedonia del Norte', None, 1),
    ('ML', 'Mali', 'Malí', None, 0),
    ('MM', 'Myanmar', 'Birmania', None, 0),
    ('MN', 'Mongolia', 'Mongolia', None, 0),
    ('MO', 'Macao', 'Macao', None, 0),
    ('MP', 'Northern Mariana Islands', 'Islas Marianas del Norte', None, 0),
    ('MQ', 'Martinique', 'Martinica', None, 0),
    ('MR', 'Mauritania', 'Mauritania', None, 0),
    ('MS', 'Montserrat', 'Montserrat', None, 0),
    ('MT', 'Malta', 'Malta', None, 1),
    ('MU', 'Mauritius', 'Mauricio', None, 0),
    ('MV', 'Maldives', 'Maldivas', None, 0),
    ('MW', 'Malawi', 'Malaui', None, 0),
    ('MX', 'Mexico', 'México', 'Mexico', 0),
    ('MY', 'Malaysia', 'Malasia', 'Malasia', 0),
    ('MZ', 'Mozambique', 'Mozambique', None, 0),
    ('NA', 'Namibia', 'Namibia', None, 0),
    ('NC', 'New Caledonia', 'Nueva Caledonia', None, 0),
    ('NE', 'Niger', 'Níger', None, 0),
    ('NF', 'Norfolk Island', 'Isla Norfolk', None, 0),
    ('NG', 'Nigeria', 'Nigeria', 'Nigeria', 0),
    ('NI', 'Nicaragua', 'Nicaragua', None, 0),
    ('NL', 'Netherlands', 'Países Bajos', 'PaisesBajos', 1),
    ('NO', 'Norway', 'Noruega', 'Noruega', 1),
    ('NP', 'Nepal', 'Nepal', None, 0),
    ('NR', 'Nauru', 'Nauru', None, 0),
    ('NU', 'Niue', 'Niue', None, 0),
    ('NZ', 'New Zealand', 'Nueva Zelanda', 'NuevaZelanda', 0),
    ('OM', 'Oman', 'Omán', None, 0),
    ('PA', 'Panama', 'Panamá', 'Panama', 0),
    ('PE', 'Peru', 'Perú', 'Peru', 0),
    ('PF', 'French Polynesia', 'Polinesia Francesa', None, 0),
    ('PG', 'Papua New Guinea', 'Papúa Nueva Guinea', None, 0),
    ('PH', 'Philippines', 'Filipinas', 'Filipinas', 0),
    ('PK', 'Pakistan', 'Pakistán', 'Pakistan', 0),
    ('PL', 'Poland', 'Polonia', 'Polonia', 1),
    ('PM', 'Saint Pierre and Miquelon', 'San Pedro y Miquelón', None, 0),
    ('PN', 'Pitcairn Islands', 'Islas Pitcairn', None, 0),
    ('PR', 'Puerto Rico', 'Puerto Rico', None, 0),
    ('PS', 'Palestine', 'Palestina', None, 0),
    ('PT', 'Portugal', 'Portugal', 'Portugal', 1),
    ('PW', 'Palau', 'Palaos', None, 0),
    ('PY', 'Paraguay', 'Paraguay', None, 0),
    ('QA', 'Qatar', 'Catar', 'Catar', 0),
    ('RE', 'Réunion', 'Reunión', None, 0),
    ('RO', 'Romania', 'Rumania', 'Rumania', 1),
    ('RS', 'Serbia', 'Serbia', None, 1),
    ('RU', 'Russia', 'Rusia', 'Rusia', 0),
    ('RW', 'Rwanda', 'Ruanda', None, 0),
    ('SA', 'Saudi Arabia', 'Arabia Saudita', 'ArabiaSaudita', 0),
    ('SB', 'Solomon Islands', 'Islas Salomón', None, 0),
    ('SC', 'Seychelles', 'Seychelles', None, 0),
    ('SD', 'Sudan', 'Sudán', None, 0),
    ('SE', 'Sweden', 'Suecia', 'Suecia', 1),
    ('SG', 'Singapore', 'Singapur', 'Singapur', 0),
    ('SH', 'Saint Helena', 'Santa Elena', None, 0),
    ('SI', 'Slovenia', 'Eslovenia', None, 1),
    ('SJ', 'Svalbard and Jan Mayen', 'Svalbard y Jan Mayen', None, 1),
    ('SK', 'Slovakia', 'Eslovaquia', None, 1),
    ('SL', 'Sierra Leone', 'Sierra Leona', None, 0),
    ('SM', 'San Marino', 'San Marino', None, 1),
    ('SN', 'Senegal', 'Senegal', None, 0),
    ('SO', 'Somalia', 'Somalia', None, 0),
    ('SR', 'Suriname', 'Surinam', None, 0),
    ('SS', 'South Sudan', 'Sudán del Sur', None, 0),
    ('ST', 'São Tomé and Príncipe', 'Santo Tomé y Príncipe', None, 0),
    ('SV', 'El Salvador', 'El Salvador', None, 0),
    ('SX', 'Sint Maarten', 'Sint Maarten', None, 0),
    ('SY', 'Syria', 'Siria', None, 0),
    ('SZ', 'Eswatini', 'Esuatini', None, 0),
    ('TC', 'Turks and Caicos Islands', 'Islas Turcas y Caicos', None, 0),
    ('TD', 'Chad', 'Chad', None, 0),
    ('TF', 'French Southern Territories', 'Territorios Australes Franceses', None, 0),
    ('TG', 'Togo', 'Togo', None, 0),
    ('TH', 'Thailand', 'Tailandia', 'Tailandia', 0),
    ('TJ', 'Tajikistan', 'Tayikistán', None, 0),
    ('TK', 'Tokelau', 'Tokelau', None, 0),
    ('TL', 'Timor-Leste', 'Timor Oriental', None, 0),
    ('TM', 'Turkmenistan', 'Turkmenistán', None, 0),
    ('TN', 'Tunisia', 'Túnez', None, 0),
    ('TO', 'Tonga', 'Tonga', None, 0),
    ('TR', 'Turkey', 'Turquía', 'Turquia', 0),
    ('TT', 'Trinidad and Tobago', 'Trinidad y Tobago', None, 0),
    ('TV', 'Tuvalu', 'Tuvalu', None, 0),
    ('TW', 'Taiwan', 'Taiwán', 'Taiwan', 0),
    ('TZ', 'Tanzania', 'Tanzania', None, 0),
    ('UA', 'Ukraine', 'Ucrania', 'Ucrania', 1),
    ('UG', 'Uganda', 'Uganda', 'Uganda', 0),
    ('UM', 'United States Minor Outlying Islands', 'Islas Ultramarinas Menores de Estados Unidos', None, 0),
    ('US', 'United States', 'Estados Unidos', 'EEUU', 0),
    ('UY', 'Uruguay', 'Uruguay', None, 0),
    ('UZ', 'Uzbekistan', 'Uzbekistán', None, 0),
    ('VA', 'Vatican City', 'Ciudad del Vaticano', None, 1),
    ('VC', 'Saint Vincent and the Grenadines', 'San Vicente y las Granadinas', None, 0),
    ('VE', 'Venezuela', 'Venezuela', None, 0),
    ('VG', 'British Virgin Islands', 'Islas Vírgenes Británicas', None, 0),
    ('VI', 'U.S. Virgin Islands', 'Islas Vírgenes de los Estados Unidos', None, 0),
    ('VN', 'Vietnam', 'Vietnam', 'Vietnam', 0),
    ('VU', 'Vanuatu', 'Vanuatu', None, 0),
    ('WF', 'Wallis and Futuna', 'Wallis y Futuna', None, 0),
    ('WS', 'Samoa', 'Samoa', None, 0),
    ('XK', 'Kosovo', 'Kosovo', None, 1),
    ('YE', 'Yemen', 'Yemen', None, 0),
    ('YT', 'Mayotte', 'Mayotte', None, 0),
    ('ZA', 'South Africa', 'Sudáfrica', 'Sudafrica', 0),
    ('ZM', 'Zambia', 'Zambia', None, 0),
    ('ZW', 'Zimbabwe', 'Zimbabue', None, 0),
)

# Grafías que ni core.world._ALIAS ni los nombres de la tabla cubren (texto normalizado → ISO-2).
EXTRA_ALIAS = {
    'estados unidos de america': 'US', 'u s a': 'US', 'america': 'US', 'ee uu de america': 'US',
    'u k': 'GB', 'britain': 'GB', 'gran bretana': 'GB', 'scotland': 'GB', 'escocia': 'GB', 'wales': 'GB',
    'gales': 'GB', 'northern ireland': 'GB', 'irlanda del norte': 'GB',
    'holland': 'NL', 'korea republic of': 'KR', 'korea south': 'KR', 'corea sur': 'KR', 'rok': 'KR',
    'korea democratic people s republic of': 'KP', 'dprk': 'KP',
    'taiwan province of china': 'TW', 'republic of china': 'TW', 'roc': 'TW', 'chinese taipei': 'TW',
    'people s republic of china': 'CN', 'republica popular china': 'CN', 'china continental': 'CN', 'mainland china': 'CN',
    'hong kong sar': 'HK', 'hong kong china': 'HK', 'hongkong': 'HK', 'hk': 'HK', 'macau': 'MO', 'macao china': 'MO',
    'ksa': 'SA', 'kingdom of saudi arabia': 'SA', 'reino de arabia saudita': 'SA',
    'ivory coast': 'CI', 'cote d ivoire': 'CI', 'burma': 'MM',
    'swaziland': 'SZ', 'suazilandia': 'SZ', 'east timor': 'TL', 'timor este': 'TL',
    'drc': 'CD', 'congo kinshasa': 'CD', 'rd congo': 'CD', 'rdc': 'CD', 'congo brazzaville': 'CG',
    'vatican': 'VA', 'holy see': 'VA', 'vaticano': 'VA', 'santa sede': 'VA',
    'bahrein': 'BH', 'bangladesh': 'BD', 'bielorusia': 'BY', 'belarus': 'BY', 'bosnia': 'BA', 'brunei darussalam': 'BN',
    'cabo verde': 'CV', 'cape verde': 'CV', 'czech': 'CZ', 'republica checa': 'CZ', 'eslovaquia': 'SK', 'slovak republic': 'SK',
    'kyrgyz republic': 'KG', 'lao': 'LA', 'lao people s democratic republic': 'LA', 'libyan arab jamahiriya': 'LY',
    'macedonia': 'MK', 'moldova republic of': 'MD', 'republica de moldova': 'MD', 'russian federation': 'RU',
    'syrian arab republic': 'SY', 'tanzania united republic of': 'TZ', 'turkiye': 'TR', 'viet nam': 'VN',
    'virgin islands british': 'VG', 'virgin islands u s': 'VI', 'islas virgenes': 'VI',
    'emiratos arabes': 'AE', 'emiratos': 'AE', 'uae': 'AE', 'eau': 'AE',
    'palestinian territory': 'PS', 'palestinian territories': 'PS',
    'reunion': 'RE', 'curacao': 'CW', 'saint martin french part': 'MF', 'sint maarten dutch part': 'SX',
    'aland': 'AX', 'faroes': 'FO', 'falklands': 'FK', 'malvinas': 'FK', 'sahara occidental': 'EH',
    'new caledonia': 'NC', 'micronesia federated states of': 'FM', 'pitcairn': 'PN',
    'saint helena ascension and tristan da cunha': 'SH', 'st helena': 'SH', 'st kitts and nevis': 'KN',
    'st lucia': 'LC', 'st vincent and the grenadines': 'VC', 'sao tome and principe': 'ST', 'trinidad': 'TT',
    'united states virgin islands': 'VI', 'us virgin islands': 'VI', 'bolivia plurinational state of': 'BO',
    'venezuela bolivarian republic of': 'VE', 'iran islamic republic of': 'IR', 'persia': 'IR',
    'nueva zelandia': 'NZ', 'aotearoa': 'NZ',
    'kazakstan': 'KZ', 'kazajstan': 'KZ', 'kirguizistan': 'KG', 'tadjikistan': 'TJ', 'uzbekistan': 'UZ',
    'zimbabwe': 'ZW', 'zimbabue': 'ZW',
}

REGIONS = ('Europa', 'RestoEuropa', 'RestoMundo')
_REGION_LABEL = {'Europa': {'es': 'Europa', 'en': 'Europe'},
                 'RestoEuropa': {'es': 'Resto de Europa', 'en': 'Rest of Europe'},
                 'RestoMundo': {'es': 'Resto del mundo', 'en': 'Rest of World'}}

# ISO-2 → {'key', 'es', 'en', 'eu'} (contrato 1; `eu` = continente europeo, para las vistas que agrupan "Resto de Europa").
TABLE = {iso: {'key': key or en, 'es': es, 'en': en, 'eu': bool(eu)} for iso, en, es, key, eu in _ROWS}
KEY_TO_ISO = {key: iso for iso, _en, _es, key, _eu in _ROWS if key}      # clave del catálogo de hoy → ISO-2
EUROPE = frozenset(iso for iso, _en, _es, _key, eu in _ROWS if eu)
_ISO_RX = re.compile(r'^[A-Z]{2}$')


def _norm(s):
    from core.world import _js_norm
    return _js_norm(s)


def _name_index():
    """Nombres EN/ES normalizados → ISO-2 (se arma una vez; el EXTRA_ALIAS manda sobre los nombres)."""
    idx = getattr(_name_index, '_idx', None)
    if idx is None:
        idx = {}
        for iso, en, es, _key, _eu in _ROWS:
            idx.setdefault(_norm(en), iso)
            idx.setdefault(_norm(es), iso)
        idx.update(EXTRA_ALIAS)
        _name_index._idx = idx
    return idx


def is_iso2(text):
    """¿Es un código ISO-2 conocido? (solo dos MAYÚSCULAS ASCII: 'CA' sí, 'ca' no — California en un texto de evento)."""
    t = str(text or '').strip()
    return bool(_ISO_RX.match(t)) and t in TABLE


def iso2_of(text):
    """Texto de país (cualquiera de las 136 grafías del catálogo, ISO-2, nombre EN/ES) → ISO-2 o None.
    'Europa' / 'RestoEuropa' / 'RestoMundo' → None (no son un país: ver `region_of`)."""
    if text is None:
        return None
    t = str(text).strip()
    if not t:
        return None
    if is_iso2(t):
        return t
    from core.world import country_key
    k = country_key(t)
    if k in KEY_TO_ISO:
        return KEY_TO_ISO[k]
    if k in REGIONS:
        return None
    if k == 'Japan':                      # clave duplicada de core/world._COUNTRY
        return 'JP'
    idx = _name_index()
    n = _norm(t)
    if n in idx:
        return idx[n]
    first = _norm(re.split(r'[/(,;—–]', t)[0])
    return idx.get(first)


def region_of(text):
    """'Europa' | 'RestoEuropa' | 'RestoMundo' cuando el texto NO nombra un país real; None si sí lo nombra."""
    if text is None:
        return None
    t = str(text).strip()
    if not t:
        return None
    if t in REGIONS:
        return t
    from core.world import country_key
    k = country_key(t)
    return k if k in REGIONS else None


def catalog_key_of(iso2):
    """ISO-2 → clave del catálogo de HOY ('US' → 'EEUU', 'GB' → 'ReinoUnido'); sin clave → nombre en inglés;
    código desconocido → el mismo texto."""
    t = str(iso2 or '').strip().upper()
    row = TABLE.get(t)
    return row['key'] if row else (iso2 if iso2 is not None else '')


def label(code, lang='es'):
    """Nombre legible: label('US','es') → 'Estados Unidos'. Acepta ISO-2, una región o una clave del catálogo."""
    lg = 'en' if str(lang or '').lower().startswith('en') else 'es'
    t = str(code or '').strip()
    if not t:
        return ''
    if t in _REGION_LABEL:
        return _REGION_LABEL[t][lg]
    row = TABLE.get(t.upper()) if _ISO_RX.match(t.upper()) else None
    if row is None and t in KEY_TO_ISO:
        row = TABLE[KEY_TO_ISO[t]]
    return row[lg] if row else t


def is_europe(text):
    """¿El país (ISO-2, clave o texto) está en Europa? Las regiones 'Europa'/'RestoEuropa' también."""
    iso = iso2_of(text)
    if iso:
        return iso in EUROPE
    return region_of(text) in ('Europa', 'RestoEuropa')


def iso2_of_props(props):
    """ISO-2 de las propiedades de un objeto: `hq_country` (ISO del importador) > `country_iso2` > `country` >
    `loc` cuando `country` es una región (como core/world._norm_country). None si nada resuelve."""
    p = props or {}
    for k in ('hq_country', 'country_iso2'):
        v = p.get(k)
        if v and is_iso2(str(v).strip()):
            return str(v).strip()
    c = p.get('country') or p.get('pais')
    iso = iso2_of(c)
    if iso:
        return iso
    if not c or region_of(c):
        return iso2_of(p.get('loc'))
    return None


def resolve(text):
    """Todo junto: {'iso2', 'key', 'region', 'es', 'en'} (key = clave del catálogo de hoy o None)."""
    iso = iso2_of(text)
    if iso:
        row = TABLE[iso]
        return {'iso2': iso, 'key': row['key'] if row['key'] in KEY_TO_ISO else None,
                'region': None, 'es': row['es'], 'en': row['en']}
    reg = region_of(text)
    return {'iso2': None, 'key': reg, 'region': reg, 'es': label(reg, 'es') if reg else None,
            'en': label(reg, 'en') if reg else None}


def js_table():
    """La tabla para la gemela JS (engine/geo_coords.js), en JSON determinista."""
    import json
    rows = [[iso, en, es, key or '', 1 if eu else 0] for iso, en, es, key, eu in _ROWS]
    return json.dumps({'rows': rows, 'extra': EXTRA_ALIAS, 'regions': _REGION_LABEL},
                      ensure_ascii=False, separators=(',', ':'), sort_keys=True)
