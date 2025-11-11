# email_sender.py
import os
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

# --- NEW HELPER FUNCTION ---
def strip_html_tags(html):
    """
    Strips HTML tags to create a clean plain text version for email clients.
    """
    # 1. Replace common HTML line breaks with newlines
    html = html.replace('<br>', '\n').replace('<br/>', '\n').replace('<p>', '\n')
    # 2. Remove all remaining HTML tags
    clean = re.compile('<.*?>')
    return re.sub(clean, '', html)
# --------------------------

def send_claim_email(letter_text, flight_data, airline_email, use_user_email=False):
    """
    Send the claim letter via Gmail.
    
    Args:
        letter_text: The edited letter content (now HTML)
    """
    if use_user_email:
        # TODO: In production, get user's Gmail app password securely
        sender_email = flight_data['passenger_email']
        print(f"\n⚠️  Para enviar desde tu email ({sender_email}), necesitas un 'App Password' de Gmail.")
        print("Instrucciones: https://support.google.com/accounts/answer/185833")
        app_password = input("Ingresa tu Gmail App Password (o presiona Enter para enviar desde VueloDigno): ")

        if not app_password:
            use_user_email = False
            print("📧 Enviando desde email de VueloDigno...")

    if not use_user_email:
        # Use VueloDigno default email (your email for now)
        sender_email = os.getenv("GMAIL_ADDRESS")
        app_password = os.getenv("GMAIL_APP_PASSWORD")
    
    # Clean inputs
    sender_email = sender_email.strip() if sender_email else ""
    airline_email = airline_email.strip()
    
    # --- CRITICAL CHANGE ---
    # The submitted text is already HTML. Use it directly for the HTML part.
    html_letter = letter_text
    
    # Use the new helper to create a clean plain-text version for email fallback.
    plain_text_letter = strip_html_tags(html_letter)
    # -----------------------
    
    # Wrap in HTML with styling
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #333;">
        {html_letter}
      </body>
    </html>
    """
    
    # Create email
    msg = MIMEMultipart('alternative')
    msg['From'] = sender_email
    msg['To'] = airline_email
    msg['Subject'] = "Reclamacion Formal - Vuelo {}".format(flight_data['flight_number'])
    
    # Attach both plain text (part1) and HTML versions (part2)
    part1 = MIMEText(plain_text_letter, 'plain', 'utf-8') # ⬅️ Uses stripped text
    part2 = MIMEText(html_body, 'html', 'utf-8')
    msg.attach(part1)
    msg.attach(part2)
    
    try:
        # Connect to Gmail's SMTP server
        print("\nConectando al servidor de Gmail...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        
        # Login
        print("Iniciando sesión...")
        server.login(sender_email, app_password)
        
        # Send email
        print(f"Enviando email a {airline_email}...")
        server.send_message(msg)
        
        # Send copy to user
        if sender_email != flight_data['passenger_email']:
            print(f"Enviando copia a {flight_data['passenger_email']}...")
            msg['To'] = flight_data['passenger_email']
            server.send_message(msg)
        
        server.quit()
        
        print("✅ ¡Email enviado exitosamente!")
        return True
        
    except Exception as e:
        print(f"❌ Error al enviar email: {e}")
        return False
