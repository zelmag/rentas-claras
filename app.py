# app.py
from flask import Flask, render_template, request, redirect, url_for, flash # ⬅️ ADDED 'flash'
from email_generator_simple import generate_mexico_claim_letter, get_airline_email
from email_sender import send_claim_email
from datetime import datetime, timedelta
import re
import os
import locale

# Try to set Spanish locale for date formatting
try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'es_MX.UTF-8')
    except:
        # If locale setting fails, we'll use manual month translation
        pass

# Optional Resend integration - only import if available
try:
    from email_sender_resend import send_claim_email_resend, send_confirmation_to_user
    RESEND_AVAILABLE = True
except ImportError:
    RESEND_AVAILABLE = False
    print("⚠️ Resend not available - install with: pip3 install resend")

def convert_markdown_to_html(text):
    """Convert markdown formatting to HTML for the front-end preview."""
    # Bold: **text**
    text = re.sub(r'\*\*([^\*]+?)\*\*', r'<strong>\1</strong>', text)

    # Bullet points: * item
    text = re.sub(r'^\*\s+(.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    # Wrap consecutive list items in <ul>
    text = re.sub(r'(<li>.+?</li>\n)+', lambda m: f'<ul>{m.group(0)}</ul>', text)

    # Line breaks
    text = text.replace('\n', '<br>\n')

    return text

def format_date_spanish(date_obj):
    """Format date in Spanish: DD de MONTH de YYYY"""
    months_spanish = {
        'January': 'enero', 'February': 'febrero', 'March': 'marzo',
        'April': 'abril', 'May': 'mayo', 'June': 'junio',
        'July': 'julio', 'August': 'agosto', 'September': 'septiembre',
        'October': 'octubre', 'November': 'noviembre', 'December': 'diciembre'
    }

    # Try using locale first
    try:
        date_str = date_obj.strftime('%d de %B de %Y')
        # If month is in English, translate it
        for eng, esp in months_spanish.items():
            date_str = date_str.replace(eng, esp)
        return date_str
    except:
        # Fallback to manual formatting
        day = date_obj.day
        month = months_spanish.get(date_obj.strftime('%B'), date_obj.strftime('%B'))
        year = date_obj.year
        return f"{day} de {month} de {year}"

app = Flask(__name__)
app.secret_key = 'una_clave_secreta_fuerte_aqui' # ⬅️ REQUIRED for flash messages

@app.route('/')
def index():
    """Home page with form"""
    # 📆 Calculate the date 365 days ago for the MINimum date limit
    one_year_ago = datetime.now() - timedelta(days=365)

    # Format it as a string: YYYY-MM-DD
    min_date_limit = one_year_ago.strftime('%Y-%m-%d')

    # Also calculate today's date for the MAX date limit (no future claims)
    today = datetime.now().strftime('%Y-%m-%d')

    # Check if user is coming back from preview page
    back_data = None
    if request.args.get('back') == 'true':
        back_data = {
            'delay_hours': request.args.get('delay_hours', ''),
            'ticket_price': request.args.get('ticket_price', ''),
            'airline': request.args.get('airline', ''),
            'flight_number': request.args.get('flight_number', ''),
            'reservation_code': request.args.get('reservation_code', ''),
            'date': request.args.get('date', ''),
            'passenger_name': request.args.get('passenger_name', ''),
            'passenger_email': request.args.get('passenger_email', ''),
            'compensation_choice': request.args.get('compensation_choice', 'reembolso_indemnizacion')
        }

    return render_template('index.html',
                           min_date=min_date_limit, # Pass the minimum date
                           max_date=today,          # Pass today's date
                           back_data=back_data)     # Pass back navigation data

@app.route('/preview', methods=['POST'])
def preview():
    """Generate and show letter preview"""

    # ⚠️ Input Validation and Data Gathering
    try:
        passenger_count = int(request.form.get('passenger_count', 1))
        if passenger_count < 1 or passenger_count > 10:
            passenger_count = 1

        passenger_name = request.form['passenger_name'].strip()

        # Validate that the number of names matches passenger_count
        name_list = [n.strip() for n in passenger_name.split(',') if n.strip()]
        if len(name_list) != passenger_count:
            flash(f'Error: Ingresaste {len(name_list)} nombre(s), pero indicaste {passenger_count} pasajero(s). Deben coincidir.', 'error')
            return redirect(url_for('index'))

        flight_data = {
            'airline': request.form['airline'],
            'flight_number': request.form['flight_number'],
            'reservation_code': request.form.get('reservation_code', 'N/A'),  # Optional, defaults to N/A
            'date': request.form['date'],
            'delay_hours': float(request.form['delay_hours']), # Convert to float
            'ticket_price': float(request.form['ticket_price']), # Convert to float
            'passenger_name': passenger_name,
            'passenger_email': request.form['passenger_email'],
            'passenger_count': passenger_count,
            'compensation_choice': request.form.get('compensation_choice', 'reembolso_indemnizacion')  # Only relevant for 4+ hour delays
        }
    except ValueError:
        # Handle case where user inputs text for a number field (e.g., ticket_price)
        flash('Error: Asegúrate de que los campos de precio y horas de retraso sean números válidos.', 'error')
        return redirect(url_for('index'))


    # --- LEGAL VALIDATIONS ---

    # 1. Date Validation: Max 1 Year Ago (As per your law requirement)
    one_year_ago = datetime.now() - timedelta(days=365)

    try:
        # Assuming date input format is 'YYYY-MM-DD'
        flight_date = datetime.strptime(flight_data['date'], '%Y-%m-%d')
    except ValueError:
        flash('Error: El formato de la fecha es inválido. Utiliza YYYY-MM-DD.', 'error')
        return redirect(url_for('index'))

    if flight_date < one_year_ago:
        flash('Error: La ley limita la compensación a vuelos que ocurrieron hace menos de un año.', 'error')
        return redirect(url_for('index'))

    # 2. Delay Validation: Must be over 1 Hour (As per your policy requirement)
    # Using '>= 1.0' for robustness, but flagging less than 1.0 as an error
    if flight_data['delay_hours'] < 1.0:
        flash('Error: El retraso debe ser de al menos 1.0 hora para que la reclamación sea válida.', 'error')
        return redirect(url_for('index'))

    # --- END VALIDATIONS ---

    # Calculate compensation using backend logic (single source of truth)
    from email_generator_simple import compare_compensations
    comp_data = compare_compensations(flight_data)
    per_passenger_amount = comp_data['amount'] if comp_data else 0
    total_compensation = per_passenger_amount * passenger_count

    # Generate letter
    letter = generate_mexico_claim_letter(flight_data)
    formatted_letter = convert_markdown_to_html(letter)

    # Get airline email
    airline_email = get_airline_email(flight_data['airline'])
    if not airline_email:
        airline_email = "No encontrado - ingresa manualmente"

    return render_template('preview.html',
                         letter=formatted_letter,
                         flight_data=flight_data,
                         airline_email=airline_email,
                         compensation_amount=total_compensation,
                         per_passenger_amount=per_passenger_amount)

@app.route('/send', methods=['POST'])
def send():
    """Send the claim email"""
    # Rebuild flight_data from form
    flight_data = {
        'airline': request.form['airline'],
        'flight_number': request.form['flight_number'],
        'date': request.form['date'],
        'delay_hours': float(request.form['delay_hours']),
        'ticket_price': float(request.form['ticket_price']),
        'passenger_name': request.form['passenger_name'],
        'passenger_email': request.form['passenger_email']
    }

    airline_email = request.form['airline_email']
    letter = request.form['letter']  # The editable letter content
    today = datetime.now()

    # Calculate deadline (10 days)
    deadline = today + timedelta(days=10)
    deadline_date_str = format_date_spanish(deadline)

    # Calculate reminder date (10 days from now)
    reminder_date = deadline
    reminder_date_str = format_date_spanish(reminder_date)

    # Calculate PROFECO deadline (same as airline deadline, 10 days)
    profeco_deadline_str = deadline_date_str

    # Calculate compensation for confirmation email
    from email_generator_simple import compare_compensations
    comp_data = compare_compensations(flight_data)
    compensation_amount = comp_data['amount'] if comp_data else 0

    success = False

    print("\n" + "="*50)
    print("📧 ATTEMPTING TO SEND EMAIL")
    print("="*50)
    print(f"To: {airline_email}")
    print(f"Passenger: {flight_data['passenger_email']}")
    print(f"Flight: {flight_data['flight_number']}")

    # Try Resend first if available
    if RESEND_AVAILABLE:
        print("\n🔄 Trying Resend.com...")
        success = send_claim_email_resend(letter, flight_data, airline_email)
        if success:
            print("✅ Resend successful! Sending confirmation email...")
            send_confirmation_to_user(flight_data, airline_email, compensation_amount, deadline_date_str)
        else:
            print("❌ Resend failed")

    # Fallback to original SMTP if Resend not available or failed
    if not success:
        print("\n🔄 Using fallback SMTP method...")
        success = send_claim_email(letter, flight_data, airline_email, use_user_email=False)
        if success:
            print("✅ SMTP successful!")
        else:
            print("❌ SMTP also failed")

    print("="*50)
    print(f"FINAL RESULT: {'SUCCESS' if success else 'FAILED'}")
    print("="*50 + "\n")

    return render_template('success.html',
                           success=success,
                           flight_data=flight_data,
                           deadline_date=deadline_date_str,
                           reminder_date=reminder_date_str,
                           profeco_deadline=profeco_deadline_str)

if __name__ == '__main__':
    # Use PORT from environment variable (for production) or default to 8080 (for local dev)
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)
