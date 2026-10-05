"""core/country_geo.py — coordenadas de referencia por PAÍS (la capital), para capas
que solo dicen "qué país" (avisos de viaje del Departamento de Estado, cortes de
internet). Nombre en inglés normalizado → (lat, lon, nombre_es). Se marca
precisión 'country' en la UI: es un punto de referencia, no el lugar exacto."""
import re
import unicodedata

_RAW = """
Afghanistan|34.53|69.17|Afganistán
Albania|41.33|19.82|Albania
Algeria|36.75|3.06|Argelia
Angola|-8.84|13.23|Angola
Argentina|-34.60|-58.38|Argentina
Armenia|40.18|44.51|Armenia
Australia|-35.28|149.13|Australia
Austria|48.21|16.37|Austria
Azerbaijan|40.41|49.87|Azerbaiyán
Bahamas|25.05|-77.35|Bahamas
Bahrain|26.23|50.59|Baréin
Bangladesh|23.81|90.41|Bangladés
Belarus|53.90|27.57|Bielorrusia
Belgium|50.85|4.35|Bélgica
Belize|17.25|-88.77|Belice
Benin|6.50|2.60|Benín
Bhutan|27.47|89.64|Bután
Bolivia|-16.50|-68.15|Bolivia
Bosnia and Herzegovina|43.86|18.41|Bosnia y Herzegovina
Botswana|-24.65|25.91|Botsuana
Brazil|-15.79|-47.88|Brasil
Brunei|4.90|114.94|Brunéi
Bulgaria|42.70|23.32|Bulgaria
Burkina Faso|12.37|-1.52|Burkina Faso
Burma|19.76|96.08|Birmania (Myanmar)
Myanmar|19.76|96.08|Birmania (Myanmar)
Burundi|-3.38|29.36|Burundi
Cambodia|11.56|104.92|Camboya
Cameroon|3.85|11.50|Camerún
Canada|45.42|-75.70|Canadá
Cabo Verde|14.93|-23.51|Cabo Verde
Central African Republic|4.39|18.56|República Centroafricana
Chad|12.13|15.06|Chad
Chile|-33.45|-70.67|Chile
China|39.90|116.40|China
Colombia|4.71|-74.07|Colombia
Comoros|-11.70|43.26|Comoras
Congo|-4.27|15.28|Congo
Republic of the Congo|-4.27|15.28|Congo
Democratic Republic of the Congo|-4.32|15.31|R. D. del Congo
Costa Rica|9.93|-84.08|Costa Rica
Cote d'Ivoire|6.83|-5.29|Costa de Marfil
Croatia|45.81|15.98|Croacia
Cuba|23.11|-82.37|Cuba
Cyprus|35.19|33.38|Chipre
Czech Republic|50.08|14.44|Chequia
Czechia|50.08|14.44|Chequia
Denmark|55.68|12.57|Dinamarca
Djibouti|11.59|43.15|Yibuti
Dominican Republic|18.49|-69.93|República Dominicana
Ecuador|-0.18|-78.47|Ecuador
Egypt|30.04|31.24|Egipto
El Salvador|13.69|-89.22|El Salvador
Equatorial Guinea|3.75|8.78|Guinea Ecuatorial
Eritrea|15.32|38.93|Eritrea
Estonia|59.44|24.75|Estonia
Eswatini|-26.31|31.14|Esuatini
Ethiopia|9.03|38.74|Etiopía
Fiji|-18.14|178.44|Fiyi
Finland|60.17|24.94|Finlandia
France|48.86|2.35|Francia
Gabon|0.42|9.47|Gabón
Gambia|13.45|-16.58|Gambia
The Gambia|13.45|-16.58|Gambia
Georgia|41.72|44.79|Georgia
Germany|52.52|13.40|Alemania
Ghana|5.60|-0.19|Ghana
Greece|37.98|23.73|Grecia
Guatemala|14.63|-90.51|Guatemala
Guinea|9.64|-13.58|Guinea
Guinea-Bissau|11.86|-15.60|Guinea-Bisáu
Guyana|6.80|-58.16|Guyana
Haiti|18.59|-72.31|Haití
Honduras|14.07|-87.19|Honduras
Hong Kong|22.32|114.17|Hong Kong
Hungary|47.50|19.04|Hungría
Iceland|64.15|-21.94|Islandia
India|28.61|77.21|India
Indonesia|-6.21|106.85|Indonesia
Iran|35.69|51.39|Irán
Iraq|33.32|44.36|Irak
Ireland|53.35|-6.26|Irlanda
Israel|31.77|35.21|Israel
Italy|41.90|12.50|Italia
Jamaica|18.02|-76.80|Jamaica
Japan|35.68|139.69|Japón
Jordan|31.95|35.93|Jordania
Kazakhstan|51.17|71.45|Kazajistán
Kenya|-1.29|36.82|Kenia
Kosovo|42.66|21.17|Kosovo
Kuwait|29.38|47.99|Kuwait
Kyrgyzstan|42.87|74.59|Kirguistán
Kyrgyz Republic|42.87|74.59|Kirguistán
Laos|17.97|102.63|Laos
Latvia|56.95|24.11|Letonia
Lebanon|33.89|35.50|Líbano
Lesotho|-29.31|27.48|Lesoto
Liberia|6.30|-10.80|Liberia
Libya|32.89|13.19|Libia
Lithuania|54.69|25.28|Lituania
Luxembourg|49.61|6.13|Luxemburgo
Macau|22.20|113.54|Macao
Madagascar|-18.88|47.51|Madagascar
Malawi|-13.96|33.79|Malaui
Malaysia|3.14|101.69|Malasia
Maldives|4.18|73.51|Maldivas
Mali|12.64|-8.00|Malí
Malta|35.90|14.51|Malta
Mauritania|18.08|-15.98|Mauritania
Mauritius|-20.16|57.50|Mauricio
Mexico|19.43|-99.13|México
Moldova|47.01|28.86|Moldavia
Mongolia|47.89|106.91|Mongolia
Montenegro|42.44|19.26|Montenegro
Morocco|34.02|-6.83|Marruecos
Mozambique|-25.97|32.57|Mozambique
Namibia|-22.56|17.08|Namibia
Nepal|27.72|85.32|Nepal
Netherlands|52.37|4.90|Países Bajos
New Zealand|-41.29|174.78|Nueva Zelanda
Nicaragua|12.11|-86.24|Nicaragua
Niger|13.51|2.11|Níger
Nigeria|9.08|7.40|Nigeria
North Korea|39.04|125.76|Corea del Norte
North Macedonia|42.00|21.43|Macedonia del Norte
Norway|59.91|10.75|Noruega
Oman|23.59|58.41|Omán
Pakistan|33.69|73.05|Pakistán
Panama|8.98|-79.52|Panamá
Papua New Guinea|-9.44|147.18|Papúa Nueva Guinea
Paraguay|-25.26|-57.58|Paraguay
Peru|-12.05|-77.04|Perú
Philippines|14.60|120.98|Filipinas
Poland|52.23|21.01|Polonia
Portugal|38.72|-9.14|Portugal
Qatar|25.29|51.53|Catar
Romania|44.43|26.10|Rumania
Russia|55.76|37.62|Rusia
Rwanda|-1.94|30.06|Ruanda
Saudi Arabia|24.71|46.68|Arabia Saudita
Senegal|14.72|-17.47|Senegal
Serbia|44.79|20.45|Serbia
Sierra Leone|8.48|-13.23|Sierra Leona
Singapore|1.29|103.85|Singapur
Slovakia|48.15|17.11|Eslovaquia
Slovenia|46.06|14.51|Eslovenia
Somalia|2.05|45.32|Somalia
South Africa|-25.75|28.19|Sudáfrica
South Korea|37.57|126.98|Corea del Sur
South Sudan|4.86|31.57|Sudán del Sur
Spain|40.42|-3.70|España
Sri Lanka|6.93|79.85|Sri Lanka
Sudan|15.50|32.56|Sudán
Suriname|5.85|-55.20|Surinam
Sweden|59.33|18.07|Suecia
Switzerland|46.95|7.45|Suiza
Syria|33.51|36.29|Siria
Taiwan|25.03|121.57|Taiwán
Tajikistan|38.56|68.79|Tayikistán
Tanzania|-6.79|39.21|Tanzania
Thailand|13.76|100.50|Tailandia
Timor-Leste|-8.56|125.57|Timor Oriental
Togo|6.13|1.22|Togo
Trinidad and Tobago|10.65|-61.52|Trinidad y Tobago
Tunisia|36.81|10.18|Túnez
Turkey|39.93|32.86|Turquía
Turkiye|39.93|32.86|Turquía
Turkmenistan|37.96|58.33|Turkmenistán
Uganda|0.35|32.58|Uganda
Ukraine|50.45|30.52|Ucrania
United Arab Emirates|24.45|54.38|Emiratos Árabes Unidos
United Kingdom|51.51|-0.13|Reino Unido
United States|38.90|-77.04|Estados Unidos
Uruguay|-34.90|-56.16|Uruguay
Uzbekistan|41.30|69.24|Uzbekistán
Venezuela|10.48|-66.90|Venezuela
Vietnam|21.03|105.85|Vietnam
West Bank|31.90|35.20|Cisjordania
Gaza|31.50|34.47|Gaza
Israel, The West Bank and Gaza|31.77|35.21|Israel, Cisjordania y Gaza
Yemen|15.37|44.19|Yemen
Zambia|-15.39|28.32|Zambia
Zimbabwe|-17.83|31.05|Zimbabue
"""


def _norm(s):
    s = unicodedata.normalize('NFD', str(s or ''))
    s = ''.join(ch for ch in s if not (0x300 <= ord(ch) <= 0x36F)).lower()
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


COUNTRIES = {}
for _ln in _RAW.strip().splitlines():
    _n, _la, _lo, _es = _ln.split('|')
    COUNTRIES[_norm(_n)] = (float(_la), float(_lo), _es, _n)
_ALIASES = {'mainland china': 'china', 'the bahamas': 'bahamas', 'republic of korea': 'south korea',
            'korea south': 'south korea', 'korea north': 'north korea', 'korea republic of': 'south korea',
            'democratic republic of congo': 'democratic republic of the congo', 'drc': 'democratic republic of the congo',
            'ivory coast': 'cote d ivoire', 'uae': 'united arab emirates', 'uk': 'united kingdom', 'usa': 'united states',
            'russian federation': 'russia', 'viet nam': 'vietnam', 'lao pdr': 'laos', 'syrian arab republic': 'syria',
            'iran islamic republic of': 'iran', 'burma myanmar': 'burma', 'turkiye': 'turkey'}


def lookup(name):
    """Nombre de país (inglés) → {lat, lon, es, en} o None."""
    n = _norm(name)
    n = _ALIASES.get(n, n)
    hit = COUNTRIES.get(n)
    if not hit and ' and ' in n:
        hit = COUNTRIES.get(n.split(' and ')[0])
    if not hit:
        return None
    return {'lat': hit[0], 'lon': hit[1], 'es': hit[2], 'en': hit[3]}
