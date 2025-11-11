# jurisdiction.py
"""
Validate that Mexican Aviation Law (Article 47 Bis) applies to a flight.

Mexican law applies if:
1. Flight originates in Mexico, OR
2. Flight lands in Mexico

Does NOT apply if covered by EU Regulation 261/2004 (we redirect to AirHelp).
"""

# Mexican airports (IATA codes)
MEXICO_AIRPORTS = {
    'AGU': 'Aguascalientes',
    'BJX': 'Bajío (León/Guanajuato)',
    'CEN': 'Ciudad Obregón',
    'CJS': 'Ciudad Juárez',
    'CME': 'Ciudad del Carmen',
    'CPE': 'Campeche',
    'CTM': 'Chetumal',
    'CUL': 'Culiacán',
    'CUN': 'Cancún',
    'CUU': 'Chihuahua',
    'CVM': 'Ciudad Victoria',
    'CZM': 'Cozumel',
    'DGO': 'Durango',
    'GDL': 'Guadalajara',
    'GYM': 'Guaymas',
    'HMO': 'Hermosillo',
    'HUX': 'Huatulco',
    'IZT': 'Ixtepec',
    'JAL': 'Jalapa',
    'LAP': 'La Paz',
    'LMM': 'Los Mochis',
    'LTO': 'Loreto',
    'MAM': 'Matamoros',
    'MEX': 'Ciudad de México (AICM)',
    'MID': 'Mérida',
    'MLM': 'Morelia',
    'MTY': 'Monterrey',
    'MZT': 'Mazatlán',
    'NLD': 'Nuevo Laredo',
    'NOG': 'Nogales',
    'OAX': 'Oaxaca',
    'PAZ': 'Poza Rica',
    'PBC': 'Puebla',
    'PPE': 'Puerto Peñasco',
    'PVR': 'Puerto Vallarta',
    'PXM': 'Puerto Escondido',
    'QRO': 'Querétaro',
    'REX': 'Reynosa',
    'SJD': 'Los Cabos',
    'SLP': 'San Luis Potosí',
    'TAM': 'Tampico',
    'TAP': 'Tapachula',
    'TGZ': 'Tuxtla Gutiérrez',
    'TIJ': 'Tijuana',
    'TLC': 'Toluca',
    'TRC': 'Torreón',
    'TSL': 'Tamuin',
    'VER': 'Veracruz',
    'VSA': 'Villahermosa',
    'ZCL': 'Zacatecas',
    'ZIH': 'Ixtapa/Zihuatanejo',
    'ZLO': 'Manzanillo',
}

# EU/EEA/UK airports (to detect EU 261 jurisdiction and redirect)
EU_AIRPORTS = {
    # Spain
    'MAD', 'BCN', 'AGP', 'PMI', 'ALC', 'SVQ', 'VLC', 'BIO', 'IBZ', 'FUE', 'TFS', 'ACE',
    # France
    'CDG', 'ORY', 'NCE', 'LYS', 'MRS', 'TLS', 'BOD', 'NTE', 'BSL',
    # Germany
    'FRA', 'MUC', 'TXL', 'DUS', 'HAM', 'CGN', 'STR', 'BER', 'NUE',
    # UK
    'LHR', 'LGW', 'MAN', 'STN', 'EDI', 'BHX', 'GLA', 'LTN', 'BRS',
    # Italy
    'FCO', 'MXP', 'LIN', 'VCE', 'NAP', 'BGY', 'BLQ', 'PSA', 'CAG',
    # Netherlands
    'AMS', 'EIN', 'RTM',
    # Portugal
    'LIS', 'OPO', 'FAO',
    # Belgium
    'BRU',
    # Austria
    'VIE',
    # Switzerland
    'ZRH', 'GVA',
    # Nordics
    'ARN', 'CPH', 'OSL', 'HEL',
    # Ireland
    'DUB',
    # Greece
    'ATH',
    # Eastern Europe
    'PRG', 'WAW', 'BUD', 'OTP', 'SOF', 'RIX', 'TLL', 'VNO',
}

# European airlines (EU 261 applies to their flights)
EUROPEAN_AIRLINES = {
    'Lufthansa', 'Air France', 'KLM', 'British Airways', 'Iberia', 'Ryanair',
    'EasyJet', 'Vueling', 'Wizz Air', 'Norwegian', 'TAP Portugal', 'Alitalia', 'ITA Airways',
    'Swiss', 'Austrian Airlines', 'Brussels Airlines', 'Finnair', 'SAS',
    'Aegean Airlines', 'Air Europa', 'Eurowings', 'Condor', 'Transavia', 'LOT Polish'
}

def is_mexican_airport(airport_code):
    """Check if airport is in Mexico"""
    return airport_code.upper().strip() in MEXICO_AIRPORTS

def is_eu_airport(airport_code):
    """Check if airport is in EU/EEA/UK territory"""
    return airport_code.upper().strip() in EU_AIRPORTS

def is_european_airline(airline_name):
    """Check if airline is European"""
    return airline_name in EUROPEAN_AIRLINES

def validate_mexican_jurisdiction(origin_code, destination_code, airline_name):
    """
    Validate that Mexican aviation law applies to this flight.

    Returns:
        dict with keys:
            - applies: Boolean - True if Mexican law applies
            - reason: String - Why it applies or doesn't
            - redirect_url: String or None - Where to redirect if not applicable
            - jurisdiction_type: String - MEXICO_ORIGIN, MEXICO_DEST, EU_261, or NOT_APPLICABLE
    """

    origin = origin_code.upper().strip()
    dest = destination_code.upper().strip()

    origin_is_mexico = is_mexican_airport(origin)
    dest_is_mexico = is_mexican_airport(dest)
    origin_is_eu = is_eu_airport(origin)
    airline_is_eu = is_european_airline(airline_name)

    # Case 1: EU 261 applies (redirect to AirHelp)
    if origin_is_eu or (airline_is_eu and dest_is_mexico):
        return {
            'applies': False,
            'reason': '🇪🇺 Este vuelo está cubierto por la <strong>Regulación Europea EU 261/2004</strong>, no por la ley mexicana.',
            'redirect_message': 'Las compensaciones europeas son más altas (€250-€600 fijos). Te recomendamos usar servicios especializados en reclamos europeos:',
            'redirect_url': 'https://www.airhelp.com',
            'redirect_service': 'AirHelp',
            'jurisdiction_type': 'EU_261'
        }

    # Case 2: Flight originates in Mexico → Mexican law applies
    if origin_is_mexico:
        origin_name = MEXICO_AIRPORTS.get(origin, origin)
        return {
            'applies': True,
            'reason': f'✅ Tu vuelo sale de <strong>{origin_name}</strong>, México. Aplica la <strong>Ley de Aviación Civil Mexicana (Artículo 47 Bis)</strong>.',
            'redirect_message': None,
            'redirect_url': None,
            'redirect_service': None,
            'jurisdiction_type': 'MEXICO_ORIGIN'
        }

    # Case 3: Flight lands in Mexico → Mexican law applies (Montreal Convention)
    if dest_is_mexico:
        dest_name = MEXICO_AIRPORTS.get(dest, dest)
        return {
            'applies': True,
            'reason': f'✅ Tu vuelo aterriza en <strong>{dest_name}</strong>, México. Bajo el <strong>Convenio de Montreal</strong>, puedes reclamar usando los estándares de la Ley de Aviación Civil Mexicana (Artículo 47 Bis).',
            'redirect_message': None,
            'redirect_url': None,
            'redirect_service': None,
            'jurisdiction_type': 'MEXICO_DESTINATION'
        }

    # Case 4: No Mexican connection
    return {
        'applies': False,
        'reason': f'❌ Este vuelo ({origin} → {dest}) no tiene conexión con México.',
        'redirect_message': 'VueloDigno solo procesa reclamos para vuelos que salen de o llegan a México. Consulta las leyes de aviación del país de origen del vuelo.',
        'redirect_url': None,
        'redirect_service': None,
        'jurisdiction_type': 'NOT_APPLICABLE'
    }

def get_mexican_airports_list():
    """Return list of Mexican airports for dropdown"""
    return [
        {'code': code, 'name': f"{code} - {name}"}
        for code, name in sorted(MEXICO_AIRPORTS.items(), key=lambda x: x[1])
    ]
