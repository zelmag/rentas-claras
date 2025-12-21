/**
 * TypeScript Types for VueloDigno
 *
 * Think of types like a form template - they define what information
 * we expect and what shape it should be in.
 */

// The airline options available
export type AirlineName = 'Volaris' | 'VivaAerobus' | 'Aeromexico';

// Delay tiers as values (1.5 = 1-2hrs, 3.0 = 2-4hrs, 5.0 = 4+ hrs)
export type DelayTier = 1.5 | 3.0 | 5.0;

// What the user's compensation choice can be for 4+ hour delays
export type CompensationChoice = 'reembolso_indemnizacion' | 'transporte_sustituto';

/**
 * FlightData - All the info about the user's flight
 * Like a form with all the boxes filled in
 */
export interface FlightData {
  origin: string;              // Airport code: "MEX"
  destination: string;         // Airport code: "CUN"
  airline: AirlineName;        // Which airline
  flightNumber: string;        // "VB 2847"
  reservationCode?: string;    // Optional booking reference
  date: string;                // "2024-12-15"
  delayHours: DelayTier;       // 1.5, 3.0, or 5.0
  ticketPrice: number;         // Price in MXN
  passengerName?: string;      // User's name
  passengerEmail?: string;     // User's email
  passengerCount: number;      // How many travelers
  compensationChoice: CompensationChoice;  // What they want
}

/**
 * CompensationResult - The calculated compensation
 * What we tell the user they can claim
 */
export interface CompensationResult {
  source: string;              // "Ley de Aviación Civil Mexicana"
  amount: number;              // Money in MXN (per passenger)
  totalAmount: number;         // Money × passenger count
  description: string;         // "100% reembolso + 25% indemnización"
  paymentMethod: string;       // "Transferencia Bancaria"
  isService: boolean;          // true if substitute transport (no money)
  delayText: string;           // "más de 4 horas"
}

/**
 * AirlineInfo - Data about each airline
 */
export interface AirlineInfo {
  name: string;
  email: string;
  hasPolicy: boolean;
  policyFile?: string;
}

/**
 * Airlines database structure
 */
export interface AirlinesDatabase {
  [key: string]: AirlineInfo;
}

/**
 * API Response types
 */
export interface CalculateResponse {
  success: boolean;
  data?: CompensationResult;
  error?: string;
}

export interface GenerateLetterResponse {
  success: boolean;
  letter?: string;
  airlineEmail?: string;
  error?: string;
}

export interface SendEmailResponse {
  success: boolean;
  message?: string;
  error?: string;
}
