/**
 * Compensation Calculator
 *
 * This is the "brain" that calculates how much money the user can claim.
 *
 * Think of it like a vending machine:
 * - You put in: flight info (airline, delay, ticket price)
 * - You get out: compensation amount + legal source
 *
 * Mexican Law (Art. 47 Bis) has 3 tiers:
 * - Tier 1: 1-2 hours delay → Small compensation (policy-dependent)
 * - Tier 2: 2-4 hours delay → At least 7.5% of ticket price
 * - Tier 3: 4+ hours or cancelled → 100% refund + 25% extra!
 */

import { FlightData, CompensationResult, DelayTier } from './types';
import airlinesData from '@/data/airlines.json';

/**
 * Get the airline's customer service email
 */
export function getAirlineEmail(airlineName: string): string | null {
  const airlineKey = airlineName.toLowerCase().replace(/\s/g, '');
  const airline = airlinesData[airlineKey as keyof typeof airlinesData];
  return airline?.email || null;
}

/**
 * Convert delay tier to human-readable Spanish text
 */
function getDelayText(delayHours: DelayTier): string {
  switch (delayHours) {
    case 1.5:
      return 'entre 1 y 2 horas';
    case 3.0:
      return 'entre 2 y 4 horas';
    case 5.0:
      return 'más de 4 horas';
    default:
      return `${delayHours} horas`;
  }
}

/**
 * Calculate compensation based on Mexican Law Art. 47 Bis
 *
 * @param flightData - All the flight information
 * @returns CompensationResult with amount, source, and description
 */
export function calculateCompensation(flightData: FlightData): CompensationResult | null {
  const { delayHours, ticketPrice, airline, passengerCount, compensationChoice } = flightData;
  const airlineKey = airline.toLowerCase().replace(/\s/g, '');

  let source: string;
  let amount: number;
  let description: string;
  let paymentMethod: string;

  // =============================================
  // TIER 3: More than 4 hours delay (value: 5.0)
  // This is the BEST compensation tier
  // =============================================
  if (delayHours === 5.0) {
    source = 'Ley de Aviación Civil Mexicana - Artículo 47 Bis';

    if (compensationChoice === 'transporte_sustituto') {
      // User chose substitute flight instead of money
      return {
        source,
        amount: 0,
        totalAmount: 0,
        description: 'Transporte sustituto en el primer vuelo disponible + servicios sin cargo (llamadas, correos, alimentos, alojamiento y transporte terrestre si es necesaria pernocta)',
        paymentMethod: 'Transporte sustituto (servicio, no pago en efectivo)',
        isService: true,
        delayText: getDelayText(delayHours),
      };
    }

    // Default: 100% refund + 25% extra
    amount = ticketPrice * 1.25;
    return {
      source,
      amount,
      totalAmount: amount * passengerCount,
      description: '100% reembolso + 25% indemnización (mínimo)',
      paymentMethod: 'Transferencia Bancaria / Efectivo - La Ley otorga al pasajero la libre elección de compensación.',
      isService: false,
      delayText: getDelayText(delayHours),
    };
  }

  // =============================================
  // TIER 1: 1-2 hours delay (value: 1.5)
  // Smallest compensation - varies by airline
  // =============================================
  if (delayHours === 1.5) {
    if (airlineKey === 'volaris') {
      amount = 50.00;
      source = 'Política de Volaris';
      description = 'Voucher Electrónico de $50 MXN';
      paymentMethod = 'Voucher Electrónico';
    } else if (airlineKey === 'vivaaerobus') {
      amount = 75.00;
      source = 'Política de VivaAerobus';
      description = 'Cupón de descuento o Viva Cash de $75 MXN';
      paymentMethod = 'Cupón de descuento o Viva Cash';
    } else {
      // Aeromexico and others: 5% of ticket
      amount = ticketPrice * 0.05;
      source = 'Política de Aeroméxico / Ley de Aviación Civil';
      description = '5% del precio del boleto';
      paymentMethod = 'Cupón de descuento';
    }

    const tierPrefix = '(1-2 horas) Servicios de asistencia (alimentos, bebidas, comunicación) y ';

    return {
      source,
      amount,
      totalAmount: amount * passengerCount,
      description: tierPrefix + description,
      paymentMethod,
      isService: false,
      delayText: getDelayText(delayHours),
    };
  }

  // =============================================
  // TIER 2: 2-4 hours delay (value: 3.0)
  // Law guarantees minimum 7.5%
  // =============================================
  if (delayHours === 3.0) {
    // Start with the legal minimum (7.5%)
    let bestAmount = ticketPrice * 0.075;
    source = 'Ley de Aviación Civil Mexicana - Artículo 47 Bis';
    paymentMethod = 'Cupón de Descuento o Servicios';
    description = '7.5% mínimo del precio del boleto';

    // Check if airline offers MORE than the legal minimum
    if (airlineKey === 'volaris') {
      // Volaris: max($250 or 7.5%)
      const volarisOffer = Math.max(250.00, ticketPrice * 0.075);
      if (volarisOffer > bestAmount) {
        bestAmount = volarisOffer;
        source = 'Política de Volaris';
        description = `$${bestAmount.toLocaleString('es-MX', { minimumFractionDigits: 2 })} MXN (mayor entre $250 o 7.5%)`;
        paymentMethod = 'Voucher Electrónico';
      }
    } else if (airlineKey === 'vivaaerobus') {
      // VivaAerobus: 8% (better than law's 7.5%)
      const vivaOffer = ticketPrice * 0.08;
      if (vivaOffer > bestAmount) {
        bestAmount = vivaOffer;
        source = 'Política de VivaAerobus';
        description = '8% de la tarifa base e impuestos';
        paymentMethod = 'Cupón de descuento o Viva Cash';
      }
    }
    // Aeromexico uses law minimum (7.5%)

    const tierPrefix = '(2-4 horas) Servicios de asistencia y ';

    return {
      source,
      amount: bestAmount,
      totalAmount: bestAmount * passengerCount,
      description: tierPrefix + description,
      paymentMethod,
      isService: false,
      delayText: getDelayText(delayHours),
    };
  }

  // No valid delay tier selected
  return null;
}

/**
 * Quick helper to format money in Mexican Pesos
 */
export function formatMXN(amount: number): string {
  return `$${amount.toLocaleString('es-MX', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })} MXN`;
}
