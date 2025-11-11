# letter_generator_simple.py
import json

# --- Helper Functions (No changes needed) ---

def load_airline_database():
    """Load airline contact info (Assuming 'airlines.json' exists)"""
    with open('airlines.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def get_airline_email(airline_name):
    """Get customer service email for airline"""
    airlines = load_airline_database()
    airline_key = airline_name.lower().replace(' ', '')
    
    if airline_key in airlines:
        return airlines[airline_key]['email']
    return None

def compare_compensations(flight_data):
    """
    Determine compensation based on the three legal tiers (Mexican Law Art. 47 Bis).
    Uses representative values: 1.5, 3.0, 5.0.
    """
    delay = flight_data['delay_hours']
    price = flight_data['ticket_price']
    airline_key = flight_data['airline'].lower().replace(' ', '')
    
    # --- TIER 3: Retraso > 4 Horas (Value: 5.0) ---
    if delay == 5.0:
        # Law requires 100% refund + 25% minimum indemnification = 125%
        amount = price * 1.25
        
        # Demand cash/transfer, as the law grants the passenger the right to choose.
        source = "Ley de Aviación Civil Mexicana - Artículo 47 Bis (Derecho a elegir Efectivo/Transferencia)"
        payment_method = "Transferencia Bancaria / Efectivo - La Ley otorga al pasajero la libre elección de compensación."
        
        return {
            'source': source,
            'amount': amount,
            'description': "100% reembolso + 25% indemnización (mínimo)",
            'payment_method': payment_method
        }
    
    # --- TIER 1: Delays 1-2 hours (Value: 1.5) ---
    elif delay == 1.5:
        # For 1-2 hours, airlines offer FLAT amounts (not percentages)

        if airline_key == 'volaris':
            amount = 50.00
            source = 'Política de Volaris'
            description = 'Voucher Electrónico de $50 MXN'
            payment_method = 'Voucher Electrónico'

        elif airline_key == 'vivaaerobus':
            amount = 75.00
            source = 'Política de VivaAerobus'
            description = 'Cupón de descuento o Viva Cash de $75 MXN'
            payment_method = 'Cupón de descuento o Viva Cash'

        else:  # Aeromexico and others: 5% per law for 1-2 hours
            amount = price * 0.05
            source = 'Política de Aeroméxico / Ley de Aviación Civil'
            description = '5% del precio del boleto'
            payment_method = 'Cupón de descuento'

        tier_prefix = "(1-2 horas) Servicios de asistencia (alimentos, bebidas, comunicación) y "

        return {
            'source': source,
            'amount': amount,
            'description': tier_prefix + description,
            'payment_method': payment_method
        }

    # --- TIER 2: Delays 2-4 hours (Value: 3.0) ---
    elif delay == 3.0:
        # 1. Baseline is the Mexican law minimum (7.5% for 2-4 hour delays)
        best_amount = price * 0.075
        source = 'Ley de Aviación Civil Mexicana - Artículo 47 Bis'
        payment_method = 'Cupón de Descuento o Servicios'
        description = '7.5% mínimo del precio del boleto'

        # 2. Check for better Airline Policies (take MAX of airline vs law)
        if airline_key == 'volaris':
            # Volaris policy: max(250, price * 0.075)
            volaris_offer = max(250.00, price * 0.075)
            if volaris_offer > best_amount:
                best_amount = volaris_offer
                source = 'Política de Volaris'
                description = f'${best_amount:,.2f} MXN (mayor entre $250 o 7.5%)'
                payment_method = 'Voucher Electrónico'

        elif airline_key == 'vivaaerobus':
            # VivaAerobus policy: 8% (better than 7.5% law minimum)
            viva_offer = price * 0.08
            if viva_offer > best_amount:
                best_amount = viva_offer
                source = 'Política de VivaAerobus'
                description = '8% de la tarifa base e impuestos'
                payment_method = 'Cupón de descuento o Viva Cash'

        # Aeromexico: uses 7.5% for 2-4 hours (same as law minimum)

        tier_prefix = "(2-4 horas) Servicios de asistencia y "

        return {
            'source': source,
            'amount': best_amount,
            'description': tier_prefix + description,
            'payment_method': payment_method
        }

    # --- Tier 0: No compensation ---
    else:
        # This should only happen if the dropdown is bypassed, since 1.5 is the minimum
        return None 


# --- Letter Generation (Updated to use descriptive text) ---

def generate_mexico_claim_letter(flight_data):
    """
    Generate letter using the logic from compare_compensations
    """
    comp_data = compare_compensations(flight_data)

    if not comp_data:
        return "Error: Retraso no califica para compensación bajo las leyes mexicanas."

    # Determine the readable text for the delay hours
    if flight_data['delay_hours'] == 1.5:
        delay_text = "entre 1 y 2 horas"
    elif flight_data['delay_hours'] == 3.0:
        delay_text = "entre 2 y 4 horas"
    elif flight_data['delay_hours'] == 5.0:
        delay_text = "más de 4 horas"
    else:
        delay_text = f"{flight_data['delay_hours']} horas"

    # Calculate total compensation based on passenger count
    passenger_count = flight_data.get('passenger_count', 1)
    per_passenger_amount = comp_data['amount']
    total_amount = per_passenger_amount * passenger_count

    # Format passenger information
    if passenger_count > 1:
        passenger_text = f"* Pasajeros: **{flight_data['passenger_name']}** ({passenger_count} personas)"
        compensation_text = f"${total_amount:,.2f} MXN (${per_passenger_amount:,.2f} MXN × {passenger_count} pasajeros)"
    else:
        passenger_text = f"* Pasajero: **{flight_data['passenger_name']}**"
        compensation_text = f"${total_amount:,.2f} MXN"


    letter = f"""**Asunto:** Reclamación Formal - Vuelo {flight_data['flight_number']}

Estimado Departamento de Atención al Cliente de {flight_data['airline'].title()},

**DATOS DE LA RESERVACIÓN:**
* Vuelo: **{flight_data['flight_number']}**
* Clave de reserva: **{flight_data['reservation_code']}**
* Fecha: **{flight_data['date']}**
* Retraso: **{delay_text}**
{passenger_text}

Solicito formalmente la compensación que me corresponde por el retraso de mi vuelo.

**FUNDAMENTO LEGAL:**
{comp_data['source']}
{comp_data['description']}

**COMPENSACIÓN SOLICITADA:**
{compensation_text}

**FORMA DE PAGO:**
{comp_data['payment_method']}

**PLAZO LEGAL:**
La Ley de Aviación Civil establece que la indemnización debe ser cubierta en un plazo máximo de **diez días naturales** a partir de la recepción de esta reclamación.

En caso de no recibir la compensación en el plazo establecido, presentaré la queja correspondiente ante la Procuraduría Federal del Consumidor (PROFECO).

Quedo a la espera de su respuesta dentro del plazo legal.

Atentamente,
{flight_data['passenger_name']}
{flight_data['passenger_email']}
"""

    return letter
