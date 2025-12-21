/**
 * API Route: /api/generate-letter
 *
 * This creates the legal claim letter.
 *
 * How it works:
 * 1. Website sends flight info (POST request)
 * 2. This route generates a professional letter
 * 3. Sends back the letter text + airline email
 *
 * It's like asking a lawyer friend to write a letter for you.
 */

import { NextRequest, NextResponse } from 'next/server';
import { generateClaimLetter } from '@/lib/email-generator';
import { getAirlineEmail } from '@/lib/compensation';
import { FlightData, GenerateLetterResponse } from '@/lib/types';

export async function POST(request: NextRequest) {
  try {
    // Get the flight data from the request body
    const flightData: FlightData = await request.json();

    // Validate required fields
    if (!flightData.airline || !flightData.flightNumber || !flightData.date) {
      return NextResponse.json<GenerateLetterResponse>(
        {
          success: false,
          error: 'Faltan campos requeridos: airline, flightNumber, date'
        },
        { status: 400 }
      );
    }

    // Generate the letter
    const letter = generateClaimLetter(flightData);

    // Get airline email
    const airlineEmail = getAirlineEmail(flightData.airline) || 'No encontrado - ingresa manualmente';

    // Return the result
    return NextResponse.json<GenerateLetterResponse>({
      success: true,
      letter,
      airlineEmail,
    });

  } catch (error) {
    console.error('Error in /api/generate-letter:', error);
    return NextResponse.json<GenerateLetterResponse>(
      {
        success: false,
        error: 'Error interno del servidor'
      },
      { status: 500 }
    );
  }
}
