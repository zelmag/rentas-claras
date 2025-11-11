# letter_generator.py
import json
from setup_rag import setup_mexico_rag_index, setup_airline_policies_index, llm

# Load RAG indexes
mexico_index = setup_mexico_rag_index()
airline_policies_index = setup_airline_policies_index()

mexico_query_engine = mexico_index.as_query_engine(llm=llm)
airline_query_engine = airline_policies_index.as_query_engine(llm=llm)

def load_airline_database():
    """Load airline contact info"""
    with open('airlines.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def get_airline_email(airline_name):
    """Get customer service email for airline"""
    airlines = load_airline_database()
    airline_key = airline_name.lower().replace(' ', '')
    
    if airline_key in airlines:
        return airlines[airline_key]['email']
    else:
        return None

def compare_compensations(flight_data):
    """
    Compare Mexican law vs airline policy and pick the best
    Returns: (source, compensation_details)
    """
    airline = flight_data['airline'].lower().replace(' ', '')
    delay_hours = flight_data['delay_hours']
    
    # Query Mexican law
    mexico_query = f"¿Cuál es la compensación para un retraso de {delay_hours} horas según el Artículo 47 Bis?"
    mexico_response = mexico_query_engine.query(mexico_query)
    
    # Query airline policy if available
    airlines = load_airline_database()
    if airline in airlines and airlines[airline]['has_policy']:
        airline_query = f"¿Cuál es la compensación que ofrece {airlines[airline]['name']} para un retraso de {delay_hours} horas?"
        airline_response = airline_query_engine.query(airline_query)
        
        # Use LLM to compare and pick the best
        comparison_prompt = f"""
Compara estas dos compensaciones y determina cuál es mejor para el pasajero:

COMPENSACIÓN LEY MEXICANA:
{mexico_response}

COMPENSACIÓN POLÍTICA DE AEROLÍNEA:
{airline_response}

Precio del boleto: ${flight_data['ticket_price']} MXN

Responde en formato JSON:
{{
  "mejor_opcion": "ley" o "aerolinea",
  "compensacion_total": [monto en MXN],
  "razon": "[explicación breve]"
}}
"""
        comparison = llm.complete(comparison_prompt)
        # Parse the JSON response to determine which to use
        # For now, return both
        return {
            'mexico': str(mexico_response),
            'airline': str(airline_response),
            'comparison': str(comparison)
        }
    else:
        # Only Mexican law applies
        return {
            'mexico': str(mexico_response),
            'airline': None,
            'comparison': 'Solo aplica ley mexicana'
        }

def generate_mexico_claim_letter(flight_data):
    """
    Generate letter using best compensation source
    """
    # Get compensation comparison
    comp_data = compare_compensations(flight_data)
    
    # Generate letter citing the best option
    prompt = f"""
Genera una carta de reclamación formal.

DATOS:
{flight_data}

ANÁLISIS DE COMPENSACIÓN:
{comp_data}

Genera la carta citando la fuente que ofrece la mejor compensación (ley mexicana o política de aerolínea).
"""
    
    response = mexico_query_engine.query(prompt)
    return str(response)
