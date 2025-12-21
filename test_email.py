#!/usr/bin/env python3
"""
Script de prueba para verificar que reclamos@vuelodigno.com funciona
"""
import resend
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get config from .env
resend.api_key = os.environ.get("RESEND_API_KEY")
from_email = os.environ.get("FROM_EMAIL", "reclamos@vuelodigno.com")

print("🔍 Verificando configuración...")
print(f"   FROM_EMAIL: {from_email}")
print(f"   API Key: {resend.api_key[:15]}..." if resend.api_key else "   ❌ API Key no encontrada")

if not resend.api_key:
    print("\n❌ ERROR: RESEND_API_KEY no está configurada en .env")
    exit(1)

# Ask for test email
test_email = input("\n📧 Ingresa tu email para recibir el email de prueba: ").strip()

if not test_email or "@" not in test_email:
    print("❌ Email inválido")
    exit(1)

print(f"\n📤 Enviando email de prueba a {test_email}...")
print(f"   Desde: {from_email}")

try:
    params = {
        "from": from_email,
        "to": [test_email],
        "subject": "✅ Test de VueloDigno - reclamos@vuelodigno.com funciona!",
        "html": """
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h1 style="color: #27ae60;">✅ Email de Prueba Exitoso!</h1>

            <p>Este email fue enviado desde <strong>reclamos@vuelodigno.com</strong> usando Resend.</p>

            <div style="background: #e8f4f8; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h3>✅ Configuración Correcta:</h3>
                <ul>
                    <li>✅ FROM_EMAIL está configurado en .env</li>
                    <li>✅ Resend API Key funciona</li>
                    <li>✅ El dominio vuelodigno.com está verificado</li>
                    <li>✅ Los emails se enviarán desde reclamos@vuelodigno.com</li>
                </ul>
            </div>

            <p><strong>Próximo paso:</strong> Haz una prueba completa enviando un reclamo desde http://localhost:8080</p>

            <hr style="margin: 30px 0; border: none; border-top: 1px solid #e5e7eb;">
            <p style="font-size: 0.85em; color: #6b7280;">
                VueloDigno - Test Email
            </p>
        </body>
        </html>
        """
    }

    response = resend.Emails.send(params)

    print(f"\n✅ EMAIL ENVIADO EXITOSAMENTE!")
    print(f"   Email ID: {response['id']}")
    print(f"   Desde: {from_email}")
    print(f"   Para: {test_email}")
    print(f"\n📬 Revisa tu bandeja de entrada (puede tardar 10-30 segundos)")
    print(f"   Si no lo ves, revisa SPAM/Correo no deseado")

except Exception as e:
    print(f"\n❌ ERROR al enviar email:")
    print(f"   {str(e)}")
    print(f"\n💡 Posibles causas:")
    print(f"   1. El dominio vuelodigno.com no está verificado en Resend")
    print(f"   2. La API Key no tiene permisos de envío")
    print(f"   3. Problemas de DNS (registros SPF/DKIM)")
    exit(1)
