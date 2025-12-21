/**
 * API Route: /api/send-email
 *
 * This is the "send button" that actually emails the airline.
 *
 * How it works:
 * 1. Website sends flight info + letter (POST request)
 * 2. This route sends the email via Resend
 * 3. Also sends a confirmation email to the user
 * 4. Returns success/failure
 *
 * It's like dropping a letter in a mailbox - once you do it,
 * the post office (Resend) takes care of delivery.
 */

import { NextRequest, NextResponse } from 'next/server';
import { sendClaimEmail, sendConfirmationEmail } from '@/lib/resend';
import { calculateCompensation, getAirlineEmail } from '@/lib/compensation';
import { FlightData, SendEmailResponse } from '@/lib/types';

/**
 * Format date to Spanish readable format
 * e.g., "25 de diciembre de 2024"
 */
function formatDateSpanish(date: Date): string {
  const months = [
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
  ];
  const day = date.getDate();
  const month = months[date.getMonth()];
  const year = date.getFullYear();
  return `${day} de ${month} de ${year}`;
}

export async function POST(request: NextRequest) {
  try {
    // Get the data from the request
    const body = await request.json();
    const { flightData, letter, airlineEmail: providedAirlineEmail } = body as {
      flightData: FlightData;
      letter: string;
      airlineEmail?: string;
    };

    // Validate required fields
    if (!flightData || !letter) {
      return NextResponse.json<SendEmailResponse>(
        {
          success: false,
          error: 'Faltan campos requeridos: flightData, letter'
        },
        { status: 400 }
      );
    }

    // Get airline email (use provided or look it up)
    const airlineEmail = providedAirlineEmail || getAirlineEmail(flightData.airline);

    if (!airlineEmail) {
      return NextResponse.json<SendEmailResponse>(
        {
          success: false,
          error: 'No se encontró el email de la aerolínea'
        },
        { status: 400 }
      );
    }

    console.log('\n' + '='.repeat(50));
    console.log('📧 ATTEMPTING TO SEND EMAIL');
    console.log('='.repeat(50));
    console.log(`To: ${airlineEmail}`);
    console.log(`Passenger: ${flightData.passengerEmail}`);
    console.log(`Flight: ${flightData.flightNumber}`);

    // Send the claim email to the airline
    const success = await sendClaimEmail(letter, flightData, airlineEmail);

    if (success) {
      console.log('✅ Email sent successfully!');

      // Calculate deadline (10 days from now)
      const deadline = new Date();
      deadline.setDate(deadline.getDate() + 10);
      const deadlineStr = formatDateSpanish(deadline);

      // Calculate compensation for confirmation email
      const compensation = calculateCompensation(flightData);
      const compensationAmount = compensation?.totalAmount || 0;

      // Send confirmation email to user
      if (flightData.passengerEmail) {
        await sendConfirmationEmail(
          flightData,
          airlineEmail,
          compensationAmount,
          deadlineStr
        );
        console.log('✅ Confirmation email sent to user!');
      }

      return NextResponse.json<SendEmailResponse>({
        success: true,
        message: 'Email enviado exitosamente',
      });
    } else {
      console.log('❌ Failed to send email');
      return NextResponse.json<SendEmailResponse>(
        {
          success: false,
          error: 'Error al enviar el email. Por favor intenta de nuevo.'
        },
        { status: 500 }
      );
    }

  } catch (error) {
    console.error('❌ Error in /api/send-email:', error);
    return NextResponse.json<SendEmailResponse>(
      {
        success: false,
        error: 'Error interno del servidor'
      },
      { status: 500 }
    );
  }
}
