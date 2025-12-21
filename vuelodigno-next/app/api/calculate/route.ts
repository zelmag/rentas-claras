/**
 * API Route: /api/calculate
 *
 * This is like a "calculator service" that the website calls.
 *
 * How it works:
 * 1. Website sends flight info (POST request)
 * 2. This route calculates compensation
 * 3. Sends back the result
 *
 * It's like texting a friend "how much is 2+2?" and getting "4" back.
 */

import { NextRequest, NextResponse } from 'next/server';
import { calculateCompensation } from '@/lib/compensation';
import { FlightData, CalculateResponse } from '@/lib/types';

export async function POST(request: NextRequest) {
  try {
    // Get the flight data from the request body
    const flightData: FlightData = await request.json();

    // Validate required fields
    if (!flightData.airline || !flightData.delayHours || !flightData.ticketPrice) {
      return NextResponse.json<CalculateResponse>(
        {
          success: false,
          error: 'Faltan campos requeridos: airline, delayHours, ticketPrice'
        },
        { status: 400 }
      );
    }

    // Calculate compensation
    const compensation = calculateCompensation(flightData);

    if (!compensation) {
      return NextResponse.json<CalculateResponse>(
        {
          success: false,
          error: 'El retraso no califica para compensación'
        },
        { status: 400 }
      );
    }

    // Return the result
    return NextResponse.json<CalculateResponse>({
      success: true,
      data: compensation,
    });

  } catch (error) {
    console.error('Error in /api/calculate:', error);
    return NextResponse.json<CalculateResponse>(
      {
        success: false,
        error: 'Error interno del servidor'
      },
      { status: 500 }
    );
  }
}
