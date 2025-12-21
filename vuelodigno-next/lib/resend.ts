/**
 * Resend Email Sender
 *
 * This sends the actual emails using Resend.com service.
 *
 * Think of Resend like a post office:
 * - You give them a letter and an address
 * - They deliver it for you
 *
 * Why we use Resend instead of sending directly:
 * - Emails sent directly often go to spam
 * - Resend makes sure emails actually arrive
 * - It's like using FedEx instead of walking the letter there yourself
 */

import { FlightData } from './types';
import { formatMXN } from './compensation';
import { LAW_URL } from './constants';

// The Resend API key comes from environment variables
// (Like a password stored in a secret place)
const RESEND_API_KEY = process.env.RESEND_API_KEY;
const FROM_EMAIL = process.env.FROM_EMAIL || 'reclamos@vuelodigno.com';

interface SendEmailParams {
  to: string;
  subject: string;
  html: string;
  cc?: string;
  replyTo?: string;
}

/**
 * Send an email using Resend API
 */
async function sendEmail(params: SendEmailParams): Promise<boolean> {
  if (!RESEND_API_KEY) {
    console.error('❌ RESEND_API_KEY not configured');
    return false;
  }

  try {
    const response = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${RESEND_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        from: FROM_EMAIL,
        to: params.to,
        cc: params.cc,
        reply_to: params.replyTo,
        subject: params.subject,
        html: params.html,
      }),
    });

    if (!response.ok) {
      const error = await response.text();
      console.error('❌ Resend API error:', error);
      return false;
    }

    console.log('✅ Email sent successfully via Resend');
    return true;
  } catch (error) {
    console.error('❌ Error sending email:', error);
    return false;
  }
}

/**
 * Send the claim email to the airline
 *
 * @param letter - The claim letter content (HTML formatted)
 * @param flightData - Flight information
 * @param airlineEmail - Airline's customer service email
 */
export async function sendClaimEmail(
  letter: string,
  flightData: FlightData,
  airlineEmail: string
): Promise<boolean> {
  const subject = `Reclamación Formal - Vuelo ${flightData.flightNumber} - ${flightData.date}`;

  // Convert markdown-style formatting to HTML
  const htmlLetter = letter
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>');

  const html = `
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
      <div style="background: #1a1a1a; color: white; padding: 20px; border-radius: 10px 10px 0 0;">
        <h1 style="margin: 0; font-size: 18px;">✈️ VueloDigno</h1>
        <p style="margin: 5px 0 0; opacity: 0.8; font-size: 14px;">Reclamación Legal de Compensación</p>
      </div>
      <div style="background: #f9f9f9; padding: 25px; border: 1px solid #ddd; border-top: none; border-radius: 0 0 10px 10px;">
        ${htmlLetter}
      </div>
      <p style="text-align: center; color: #888; font-size: 12px; margin-top: 20px;">
        Este correo fue generado automáticamente por VueloDigno.com<br>
        Basado en la <a href="${LAW_URL}" style="color: #3b82f6; text-decoration: underline;">Ley de Aviación Civil Mexicana</a> - Artículo 47 Bis
      </p>
    </div>
  `;

  return sendEmail({
    to: airlineEmail,
    subject,
    html,
    cc: flightData.passengerEmail,
    replyTo: flightData.passengerEmail,
  });
}

/**
 * Send confirmation email to the user
 */
export async function sendConfirmationEmail(
  flightData: FlightData,
  _airlineEmail: string,
  compensationAmount: number,
  deadlineDate: string
): Promise<boolean> {
  if (!flightData.passengerEmail) {
    console.error('❌ No passenger email provided');
    return false;
  }

  const subject = `✅ Tu reclamo ha sido enviado - Vuelo ${flightData.flightNumber}`;

  const html = `
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
      <div style="background: linear-gradient(135deg, #10b981, #059669); color: white; padding: 25px; border-radius: 10px 10px 0 0; text-align: center;">
        <h1 style="margin: 0; font-size: 24px;">✅ ¡Reclamo Enviado!</h1>
      </div>
      <div style="background: #f9f9f9; padding: 25px; border: 1px solid #ddd; border-top: none; border-radius: 0 0 10px 10px;">
        <p style="font-size: 16px; margin-bottom: 20px;">
          Hola <strong>${flightData.passengerName || 'Pasajero'}</strong>,
        </p>
        <p style="margin-bottom: 20px;">
          Tu reclamo por el vuelo <strong>${flightData.flightNumber}</strong> ha sido enviado exitosamente a <strong>${flightData.airline}</strong>.
        </p>

        <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #f59e0b;">
          <p style="margin: 0 0 10px; color: #666;">Compensación solicitada:</p>
          <p style="margin: 0; font-size: 28px; font-weight: bold; color: #f59e0b;">
            ${formatMXN(compensationAmount)}
          </p>
        </div>

        <h3 style="margin-top: 25px; color: #333;">📅 ¿Qué sigue?</h3>
        <ul style="line-height: 1.8;">
          <li>La aerolínea tiene hasta el <strong>${deadlineDate}</strong> (10 días naturales) para responder</li>
          <li>Te llegará una copia del correo que enviamos</li>
          <li>Si no responden, puedes escalar a PROFECO</li>
        </ul>

        <p style="margin-top: 25px; padding: 15px; background: #fef3c7; border-radius: 8px;">
          💡 <strong>Tip:</strong> Guarda este correo como comprobante de que enviaste tu reclamo formal.
        </p>
      </div>
      <p style="text-align: center; color: #888; font-size: 12px; margin-top: 20px;">
        VueloDigno.com - Defiende tus derechos como pasajero 🇲🇽
      </p>
    </div>
  `;

  return sendEmail({
    to: flightData.passengerEmail,
    subject,
    html,
  });
}
