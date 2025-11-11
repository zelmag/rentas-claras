# flight_api.py
import requests
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

AVIATIONSTACK_API_KEY = os.environ.get("AVIATIONSTACK_API_KEY")
AVIATIONSTACK_BASE_URL = "http://api.aviationstack.com/v1"

def lookup_flight(flight_number, flight_date):
    """
    Look up flight information from AviationStack API

    Args:
        flight_number: Flight number (e.g., "Y4408" or "408")
        flight_date: Flight date in YYYY-MM-DD format

    Returns:
        dict: Flight information or None if not found
        {
            'airline': 'Volaris',
            'airline_iata': 'Y4',
            'flight_number': 'Y4408',
            'flight_date': '2025-01-15',
            'delay_minutes': 120,
            'delay_hours': 2.0,
            'status': 'landed' | 'cancelled' | 'delayed',
            'departure_scheduled': '2025-01-15T10:00:00',
            'departure_actual': '2025-01-15T12:00:00',
            'arrival_delay_minutes': 120
        }
    """

    if not AVIATIONSTACK_API_KEY or AVIATIONSTACK_API_KEY == "your_api_key_here":
        print("⚠️ AviationStack API key not configured")
        return None

    try:
        # Clean up flight number (remove spaces, convert to uppercase)
        flight_number = flight_number.strip().upper().replace(" ", "")

        # ⚡ TEST MODE - Return mock data for test flight numbers
        test_flights = {
            'TEST1': {
                'airline': 'Volaris',
                'airline_iata': 'Y4',
                'flight_number': 'TEST1',
                'flight_date': flight_date,
                'delay_minutes': 90,
                'delay_hours': 1.5,
                'status': 'landed',
                'departure_scheduled': f'{flight_date}T10:00:00',
                'departure_actual': f'{flight_date}T11:30:00',
                'arrival_delay_minutes': 90
            },
            'TEST2': {
                'airline': 'VivaAerobus',
                'airline_iata': 'VB',
                'flight_number': 'TEST2',
                'flight_date': flight_date,
                'delay_minutes': 180,
                'delay_hours': 3.0,
                'status': 'landed',
                'departure_scheduled': f'{flight_date}T14:00:00',
                'departure_actual': f'{flight_date}T17:00:00',
                'arrival_delay_minutes': 180
            },
            'TEST3': {
                'airline': 'Aeromexico',
                'airline_iata': 'AM',
                'flight_number': 'TEST3',
                'flight_date': flight_date,
                'delay_minutes': 300,
                'delay_hours': 5.0,
                'status': 'landed',
                'departure_scheduled': f'{flight_date}T08:00:00',
                'departure_actual': f'{flight_date}T13:00:00',
                'arrival_delay_minutes': 300
            },
            'DEMO1': {
                'airline': 'Volaris',
                'airline_iata': 'Y4',
                'flight_number': 'DEMO1',
                'flight_date': flight_date,
                'delay_minutes': 90,
                'delay_hours': 1.5,
                'status': 'landed',
                'departure_scheduled': f'{flight_date}T10:00:00',
                'departure_actual': f'{flight_date}T11:30:00',
                'arrival_delay_minutes': 90
            },
            'DEMO2': {
                'airline': 'VivaAerobus',
                'airline_iata': 'VB',
                'flight_number': 'DEMO2',
                'flight_date': flight_date,
                'delay_minutes': 180,
                'delay_hours': 3.0,
                'status': 'landed',
                'departure_scheduled': f'{flight_date}T14:00:00',
                'departure_actual': f'{flight_date}T17:00:00',
                'arrival_delay_minutes': 180
            },
            'DEMO3': {
                'airline': 'Aeromexico',
                'airline_iata': 'AM',
                'flight_number': 'DEMO3',
                'flight_date': flight_date,
                'delay_minutes': 300,
                'delay_hours': 5.0,
                'status': 'landed',
                'departure_scheduled': f'{flight_date}T08:00:00',
                'departure_actual': f'{flight_date}T13:00:00',
                'arrival_delay_minutes': 300
            }
        }

        if flight_number in test_flights:
            result = test_flights[flight_number]
            print(f"🧪 TEST MODE: Using mock data for {flight_number}")
            print(f"✅ Flight found: {result['airline']} - Delay: {result['delay_hours']}h ({result['delay_minutes']}min) - Status: {result['status']}")
            return result

        # AviationStack API endpoint
        url = f"{AVIATIONSTACK_BASE_URL}/flights"

        params = {
            'access_key': AVIATIONSTACK_API_KEY,
            'flight_iata': flight_number,
            'flight_date': flight_date,
            'limit': 1
        }

        print(f"\n🔍 Looking up flight {flight_number} on {flight_date}...")
        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            print(f"❌ API Error: {response.status_code}")
            return None

        data = response.json()

        # Check if flight was found
        if not data.get('data') or len(data['data']) == 0:
            print(f"❌ Flight not found: {flight_number}")
            return None

        flight_data = data['data'][0]

        # Extract relevant information
        airline_name = flight_data.get('airline', {}).get('name', 'Unknown')
        airline_iata = flight_data.get('airline', {}).get('iata', '')
        flight_status = flight_data.get('flight_status', 'unknown')

        # Get delay information (in minutes)
        departure_delay = flight_data.get('departure', {}).get('delay', 0) or 0
        arrival_delay = flight_data.get('arrival', {}).get('delay', 0) or 0

        # Use the larger delay (either departure or arrival)
        delay_minutes = max(departure_delay, arrival_delay)
        delay_hours = round(delay_minutes / 60, 1) if delay_minutes > 0 else 0

        # Get scheduled and actual times
        departure_scheduled = flight_data.get('departure', {}).get('scheduled', '')
        departure_actual = flight_data.get('departure', {}).get('actual', '')

        result = {
            'airline': airline_name,
            'airline_iata': airline_iata,
            'flight_number': flight_number,
            'flight_date': flight_date,
            'delay_minutes': delay_minutes,
            'delay_hours': delay_hours,
            'status': flight_status,
            'departure_scheduled': departure_scheduled,
            'departure_actual': departure_actual,
            'arrival_delay_minutes': arrival_delay
        }

        print(f"✅ Flight found: {airline_name} - Delay: {delay_hours}h ({delay_minutes}min) - Status: {flight_status}")
        return result

    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {str(e)}")
        return None
    except Exception as e:
        print(f"❌ Error looking up flight: {str(e)}")
        return None


def convert_delay_to_tier(delay_hours):
    """
    Convert delay hours to the tier system used in the form

    Args:
        delay_hours: Delay in hours (float)

    Returns:
        float: 1.5, 3.0, or 5.0 (tier values)
    """
    if delay_hours < 1.0:
        return None  # Not eligible
    elif delay_hours < 2.0:
        return 1.5  # 1-2 hours
    elif delay_hours < 4.0:
        return 3.0  # 2-4 hours
    else:
        return 5.0  # 4+ hours or cancelled


def map_airline_name(api_airline_name):
    """
    Map AviationStack airline names to our system's airline names

    Args:
        api_airline_name: Airline name from API

    Returns:
        str: Standardized airline name
    """
    airline_mapping = {
        'Volaris': 'Volaris',
        'VivaAerobus': 'VivaAerobus',
        'Viva Aerobus': 'VivaAerobus',
        'Aeromexico': 'Aeromexico',
        'Aeroméxico': 'Aeromexico',
        'AeroMexico': 'Aeromexico'
    }

    return airline_mapping.get(api_airline_name, api_airline_name)
