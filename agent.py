# agent.py
import os
from email_sender import send_claim_email

# Choose which version to use
USE_LLM = False  # Set to True when you want to use LLM version -- SET LLM OR SIMPLE VERSION @ZELMA

if USE_LLM:
    from email_generator_llm import generate_mexico_claim_letter, get_airline_email
    print("🤖 Using LLM version")
else:
    from email_generator_simple import generate_mexico_claim_letter, get_airline_email
    print("⚡ Using hardcoded version (fast)")

def get_flight_info():
    """CLI prompts to get flight information from user"""
    print("\n=== ZELMAHELPS - GENERADOR DE RECLAMACIONES ===\n")
    
    flight_data = {
        'airline': input("Aerolínea: "),
        'flight_number': input("Número de vuelo: "),
        'date': input("Fecha del vuelo (DD/MM/AAAA): "),
        'delay_hours': float(input("Horas de retraso/cancelación: ")),
        'ticket_price': float(input("Precio del boleto (MXN): ")),
        'passenger_name': input("Nombre del pasajero: "),
        'passenger_email': input("Tu email: ")
    }
    
    return flight_data

if __name__ == "__main__":
    # Get flight info
    flight_data = get_flight_info()
    
    # Auto-fetch airline email
    airline_email = get_airline_email(flight_data['airline'])
    
    if not airline_email:
        print(f"\n⚠️  No tengo el email para {flight_data['airline']}")
        airline_email = input("Por favor ingresa el email de la aerolínea: ")
    else:
        print(f"\n✓ Email encontrado: {airline_email}")
    
    # Generate letter
    if not USE_LLM:
        print("\n🔍 Comparando ley mexicana vs políticas de aerolínea...")
    
    letter = generate_mexico_claim_letter(flight_data)
    
    print("\n=== CARTA GENERADA ===")
    print(letter)
    
    # Confirm before sending
    confirm = input("\n¿Enviar esta carta? (si/no): ")
    if confirm.lower() == 'si':
        send_claim_email(letter, flight_data, airline_email)
    else:
        print("Email no enviado.")
