# email_sender_resend.py
import resend
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def send_claim_email_resend(letter_html, flight_data, airline_email):
    """
    Send claim email using Resend.com

    Args:
        letter_html: HTML content of the email
        flight_data: Dictionary with flight information
        airline_email: Airline's customer service email

    Returns:
        bool: True if email sent successfully, False otherwise
    """

    # Get API key from environment variable
    resend.api_key = os.environ.get("RESEND_API_KEY")

    if not resend.api_key:
        print("ERROR: RESEND_API_KEY not found in environment variables")
        return False

    try:
        # Build email parameters
        params = {
            "from": "VueloDigno <noreply@vuelodigno.com>",  # Your verified domain
            "to": [airline_email],
            "cc": [flight_data['passenger_email']],  # User gets a copy
            "reply_to": flight_data['passenger_email'],  # Airline replies go to user
            "subject": f"Reclamación Formal - Vuelo {flight_data['flight_number']}",
            "html": letter_html,
        }

        # Send email
        response = resend.Emails.send(params)

        print(f"✅ Email sent successfully via Resend! ID: {response['id']}")
        return True

    except Exception as e:
        print(f"❌ Error sending email via Resend: {str(e)}")
        return False


def send_confirmation_to_user(flight_data, airline_email, compensation_amount, deadline_date):
    """
    Send a confirmation email to the user after their claim is submitted

    Args:
        flight_data: Dictionary with flight information
        airline_email: Airline's customer service email
        compensation_amount: Calculated compensation
        deadline_date: Formatted deadline date string

    Returns:
        bool: True if email sent successfully
    """

    resend.api_key = os.environ.get("RESEND_API_KEY")

    if not resend.api_key:
        return False

    try:
        confirmation_html = f"""
        <html>
        <body style="font-family: 'Montserrat', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h1 style="color: #27ae60;">✅ Tu reclamación fue enviada</h1>

            <p>Hola {flight_data['passenger_name']},</p>

            <p>Tu reclamación formal ha sido enviada exitosamente a <strong>{flight_data['airline']}</strong>.</p>

            <div style="background: #e8f4f8; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0;">Detalles de tu Reclamación:</h3>
                <ul style="line-height: 1.8;">
                    <li><strong>Vuelo:</strong> {flight_data['flight_number']}</li>
                    <li><strong>Fecha:</strong> {flight_data['date']}</li>
                    <li><strong>Compensación Solicitada:</strong> ${compensation_amount:,.2f} MXN</li>
                    <li><strong>Enviado a:</strong> {airline_email}</li>
                </ul>
            </div>

            <h3>⏰ Próximos Pasos:</h3>
            <ol style="line-height: 1.8;">
                <li><strong>{flight_data['airline']} debe responder antes del {deadline_date}</strong> según la Ley de Aviación Civil (10 días naturales).</li>
                <li>Revisa tu email regularmente para ver su respuesta.</li>
                <li>Si no responden, presenta tu queja en <a href="https://www.gob.mx/profeco/articulos/proceso-y-requisitos-de-quejas-y-denuncias" target="_blank">PROFECO</a>.</li>
            </ol>

            <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ffc107;">
                <p style="margin: 0;"><strong>📅 ¿Quieres un recordatorio?</strong></p>
                <p style="margin: 10px 0 0 0;">Si la aerolínea no responde en 10 días, podemos recordarte que envíes un seguimiento.</p>
                <p style="margin: 10px 0 0 0;"><strong>Responde este email con "SÍ"</strong> y te enviaremos un recordatorio automático.</p>
            </div>

            <div style="background: #f3f4f6; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p style="margin: 0;"><strong>💡 Consejo:</strong> Guarda este email como comprobante de que enviaste tu reclamación.</p>
            </div>

            <p>¡Buena suerte!</p>
            <p><strong>El equipo de VueloDigno</strong></p>

            <hr style="margin: 30px 0; border: none; border-top: 1px solid #e5e7eb;">
            <p style="font-size: 0.85em; color: #6b7280;">
                Este es un email automático de confirmación. Tu reclamación fue enviada a {airline_email} con copia a ti.
            </p>
        </body>
        </html>
        """

        params = {
            "from": "VueloDigno <noreply@vuelodigno.com>",  # Your verified domain
            "to": [flight_data['passenger_email']],
            "subject": f"✅ Reclamación Enviada - Vuelo {flight_data['flight_number']}",
            "html": confirmation_html,
        }

        resend.Emails.send(params)
        return True

    except Exception as e:
        print(f"❌ Error sending confirmation: {str(e)}")
        return False
