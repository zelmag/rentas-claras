/**
 * Email Letter Generator
 *
 * This creates the legal claim letter that gets sent to the airline.
 *
 * Think of it like a "Mad Libs" game:
 * - You fill in the blanks (flight info, dates, amounts)
 * - It creates a professional legal letter
 *
 * The letter cites Mexican Law (Article 47 Bis) and requests
 * the compensation that the user is entitled to.
 */

import { FlightData } from './types';
import { calculateCompensation, formatMXN } from './compensation';
import { LAW_URL } from './constants';

/**
 * Generate the claim letter in Spanish
 *
 * @param flightData - All the flight information
 * @returns The complete letter as a string (with markdown formatting)
 */
export function generateClaimLetter(flightData: FlightData): string {
  const compensation = calculateCompensation(flightData);

  if (!compensation) {
    return 'Error: Retraso no califica para compensación bajo las leyes mexicanas.';
  }

  const {
    airline,
    flightNumber,
    origin,
    destination,
    reservationCode = 'N/A',
    date,
    ticketPrice,
    passengerName = '[TU NOMBRE]',
    passengerEmail = '[TU EMAIL]',
    passengerCount,
  } = flightData;

  const {
    source,
    amount,
    totalAmount,
    description,
    paymentMethod,
    isService,
    delayText,
  } = compensation;

  // Format passenger info based on count
  const passengerText = passengerCount > 1
    ? `* Pasajeros: **${passengerName}** (${passengerCount} personas)`
    : `* Pasajero: **${passengerName}**`;

  // Format compensation text
  let compensationText: string;
  if (isService) {
    compensationText = passengerCount > 1
      ? `Transporte sustituto para ${passengerCount} pasajeros en el primer vuelo disponible`
      : 'Transporte sustituto en el primer vuelo disponible';
  } else {
    compensationText = passengerCount > 1
      ? `${formatMXN(totalAmount)} (${formatMXN(amount)} × ${passengerCount} pasajeros)`
      : formatMXN(totalAmount);
  }

  // Legal deadline text
  const plazoLegalText = isService
    ? `La [Ley de Aviación Civil](${LAW_URL}) establece que el transporte sustituto debe ser proporcionado de inmediato, y los servicios adicionales (llamadas, correos, alimentos, alojamiento) deben ser cubiertos sin cargo.`
    : `La [Ley de Aviación Civil](${LAW_URL}) establece que la indemnización debe ser cubierta en un plazo máximo de **diez días naturales** a partir de la recepción de esta reclamación.`;

  // Build the calculation section
  let calculationSection = `* Precio del boleto: ${formatMXN(ticketPrice)}
* Base legal: ${description}`;

  if (!isService) {
    calculationSection += `
* Compensación por pasajero: ${formatMXN(amount)}`;

    if (passengerCount > 1) {
      calculationSection += `
* Número de pasajeros: ${passengerCount}
* **Total compensación: ${formatMXN(totalAmount)}**`;
    }
  }

  // The actual letter template
  const letter = `**Asunto:** Reclamación Formal - Vuelo ${flightNumber}

Estimado Departamento de Atención al Cliente de ${airline},

**DATOS DE LA RESERVACIÓN:**
* Vuelo: **${flightNumber}** (${origin} → ${destination})
* Clave de reserva: **${reservationCode}**
* Fecha: **${date}**
* Retraso: **${delayText}**
${passengerText}

Solicito formalmente la compensación que me corresponde por el retraso de mi vuelo.

**FUNDAMENTO LEGAL:**
${source}
${description}

**COMPENSACIÓN SOLICITADA:**
${compensationText}

**CÁLCULO DE LA COMPENSACIÓN:**
${calculationSection}

**FORMA DE PAGO:**
${paymentMethod}

**PLAZO LEGAL:**
${plazoLegalText}

En caso de no recibir la compensación en el plazo establecido, presentaré la queja correspondiente ante la Procuraduría Federal del Consumidor (PROFECO).

Quedo a la espera de su respuesta dentro del plazo legal.

Atentamente,
${passengerName}
${passengerEmail}`;

  return letter;
}

/**
 * Convert markdown-style formatting to HTML
 * (For displaying in preview)
 */
export function markdownToHtml(markdown: string): string {
  return markdown
    // Links: [text](url) → <a href="url">text</a>
    .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" style="color: #3b82f6; text-decoration: underline;">$1</a>')
    // Bold: **text** → <strong>text</strong>
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // Line breaks
    .replace(/\n/g, '<br>');
}

/**
 * Generate tweet text for social pressure
 */
export function generateTweetText(
  flightData: FlightData,
  compensationAmount: number
): string {
  const airlineTwitterHandles: Record<string, string> = {
    volaris: '@Volaris',
    vivaaerobus: '@VivaAerobus',
    aeromexico: '@Aeromexico',
  };

  const airlineKey = flightData.airline.toLowerCase().replace(/\s/g, '');
  const handle = airlineTwitterHandles[airlineKey] || `@${flightData.airline}`;

  return `${handle} Mi vuelo ${flightData.flightNumber} del ${flightData.date} tuvo un retraso de ${flightData.delayHours > 4 ? 'más de 4 horas' : flightData.delayHours + ' horas'}. Por ley (Art. 47 Bis) me corresponden ${formatMXN(compensationAmount)}. Ya envié mi reclamo formal. ¿En cuánto tiempo puedo esperar respuesta? #DerechosDelPasajero`;
}
