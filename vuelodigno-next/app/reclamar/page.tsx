"use client";

import { useState, useEffect, Suspense } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter, useSearchParams } from "next/navigation";
import { calculateCompensation, formatMXN } from "@/lib/compensation";
import { AirlineName, DelayTier, FlightData, CompensationChoice } from "@/lib/types";
import Navbar from "@/components/Navbar";
import AirportAutocomplete from "@/components/AirportAutocomplete";

// Form steps
type Step = 1 | 2 | 3;

// Airlines with their display info
const AIRLINES: { value: AirlineName; label: string; emoji: string }[] = [
  { value: "Volaris", label: "Volaris", emoji: "🟣" },
  { value: "Aeromexico", label: "Aeroméxico", emoji: "🔵" },
  { value: "VivaAerobus", label: "VivaAerobus", emoji: "🟡" },
];

const DELAY_OPTIONS: { value: DelayTier; label: string; description: string }[] = [
  { value: 1.5, label: "1-2 horas", description: "Alimentos y bebidas" },
  { value: 3.0, label: "2-4 horas", description: "Alimentos + llamada/email" },
  { value: 5.0, label: "+4 horas o cancelado", description: "125% del boleto" },
];

const COMPENSATION_CHOICES: { value: CompensationChoice; label: string; description: string }[] = [
  { value: "reembolso_indemnizacion", label: "💰 Reembolso + Indemnización", description: "100% del boleto + 25% extra" },
  { value: "transporte_sustituto", label: "✈️ Vuelo Sustituto", description: "Te ponen en el siguiente vuelo" },
];

function ReclamarContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Current step
  const [step, setStep] = useState<Step>(1);

  // Form data
  const [airline, setAirline] = useState<AirlineName | "">("");
  const [delayHours, setDelayHours] = useState<DelayTier | null>(null);
  const [ticketPrice, setTicketPrice] = useState("");
  const [flightNumber, setFlightNumber] = useState("");
  const [reservationCode, setReservationCode] = useState("");
  const [flightDate, setFlightDate] = useState("");
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [passengerCount, setPassengerCount] = useState(1);
  const [compensationChoice, setCompensationChoice] = useState<CompensationChoice>("reembolso_indemnizacion");

  // Validation errors
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Computed values
  const [compensation, setCompensation] = useState<number>(0);

  // Pre-fill from URL params (from Hero mini-form)
  useEffect(() => {
    const airlineParam = searchParams.get("airline");
    const delayParam = searchParams.get("delay");

    if (airlineParam && AIRLINES.some(a => a.value === airlineParam)) {
      setAirline(airlineParam as AirlineName);
    }
    if (delayParam) {
      const delayValue = parseFloat(delayParam) as DelayTier;
      if ([1.5, 3.0, 5.0].includes(delayValue)) {
        setDelayHours(delayValue);
      }
    }
  }, [searchParams]);

  // Calculate date limits
  const today = new Date().toISOString().split("T")[0];
  const oneYearAgo = new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().split("T")[0];

  // Calculate compensation when inputs change
  useEffect(() => {
    const price = parseFloat(ticketPrice) || 0;
    if (price > 0 && delayHours && airline) {
      const flightData: FlightData = {
        origin: origin.toUpperCase() || "MEX",
        destination: destination.toUpperCase() || "CUN",
        airline: airline as AirlineName,
        flightNumber: flightNumber || "XX 000",
        date: flightDate || today,
        delayHours,
        ticketPrice: price,
        passengerCount,
        compensationChoice,
      };

      const result = calculateCompensation(flightData);
      if (result) {
        setCompensation(result.totalAmount);
      }
    }
  }, [ticketPrice, delayHours, airline, passengerCount, compensationChoice, origin, destination, flightNumber, flightDate, today]);

  // Validation functions
  const validateStep1 = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!airline) {
      newErrors.airline = "Selecciona una aerolínea";
    }

    if (!delayHours) {
      newErrors.delayHours = "Selecciona el tiempo de retraso";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const validateStep2 = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!ticketPrice || parseFloat(ticketPrice) <= 0) {
      newErrors.ticketPrice = "Ingresa el precio del boleto";
    }

    if (!flightNumber.trim()) {
      newErrors.flightNumber = "Ingresa el número de vuelo";
    }

    if (!flightDate) {
      newErrors.flightDate = "Selecciona la fecha del vuelo";
    } else {
      const selectedDate = new Date(flightDate);
      const minDate = new Date(oneYearAgo);
      const maxDate = new Date(today);

      if (selectedDate < minDate) {
        newErrors.flightDate = "El vuelo debe ser de hace menos de 1 año";
      } else if (selectedDate > maxDate) {
        newErrors.flightDate = "La fecha no puede ser en el futuro";
      }
    }

    if (!origin.trim() || origin.length < 2) {
      newErrors.origin = "Ingresa el origen (ej: MEX)";
    }

    if (!destination.trim() || destination.length < 2) {
      newErrors.destination = "Ingresa el destino (ej: CUN)";
    }

    if (passengerCount < 1 || passengerCount > 10) {
      newErrors.passengerCount = "Número de pasajeros inválido";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleNextStep = () => {
    if (step === 1 && validateStep1()) {
      setStep(2);
    } else if (step === 2 && validateStep2()) {
      setStep(3);
    }
  };

  const handlePrevStep = () => {
    if (step > 1) {
      setStep((step - 1) as Step);
    }
  };

  const handleSubmit = () => {
    // Build query params and navigate to preview
    const params = new URLSearchParams({
      airline: airline as string,
      delayHours: String(delayHours),
      ticketPrice,
      flightNumber,
      reservationCode,
      date: flightDate,
      origin: origin.toUpperCase(),
      destination: destination.toUpperCase(),
      passengerCount: String(passengerCount),
      compensationChoice,
    });

    router.push(`/preview?${params.toString()}`);
  };

  return (
    <main className="min-h-screen bg-obsidian-900">
      <Navbar />

      {/* Background effects */}
      <div className="fixed inset-0 bg-gradient-mesh pointer-events-none" />
      <div className="fixed top-1/4 left-1/4 w-96 h-96 bg-accent-500/5 rounded-full blur-[120px] animate-pulse-glow pointer-events-none" />

      <div className="relative z-10 pt-24 pb-16 px-6">
        <div className="max-w-lg mx-auto">
          {/* Progress Bar */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-neutral-300">Paso {step} de 3</span>
              {compensation > 0 && (
                <motion.span
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="text-gold-400 font-semibold"
                >
                  💰 {formatMXN(compensation)}
                </motion.span>
              )}
            </div>
            <div className="h-2 bg-white/10 rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-accent-500 to-gold-500"
                initial={{ width: "0%" }}
                animate={{ width: `${(step / 3) * 100}%` }}
                transition={{ duration: 0.5, ease: "easeOut" }}
              />
            </div>
            <div className="flex justify-between mt-2 text-xs text-neutral-400">
              <span className={step >= 1 ? "text-accent-400" : ""}>Aerolínea</span>
              <span className={step >= 2 ? "text-accent-400" : ""}>Vuelo</span>
              <span className={step >= 3 ? "text-accent-400" : ""}>Confirmar</span>
            </div>
          </div>

          {/* Form Card */}
          <motion.div
            layout
            className="glass-strong rounded-3xl p-6 md:p-8"
          >
            <AnimatePresence mode="wait">
              {/* Step 1: Airline & Delay */}
              {step === 1 && (
                <motion.div
                  key="step1"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.3 }}
                >
                  <h2 className="text-2xl font-bold text-white mb-6">
                    ¿Qué pasó con tu vuelo?
                  </h2>

                  {/* Airline Selection */}
                  <div className="mb-6">
                    <label className="block text-sm text-neutral-300 mb-3">
                      Aerolínea
                    </label>
                    <div className="grid grid-cols-3 gap-3">
                      {AIRLINES.map((a) => (
                        <button
                          key={a.value}
                          type="button"
                          onClick={() => {
                            setAirline(a.value);
                            setErrors({ ...errors, airline: "" });
                          }}
                          className={`p-4 rounded-2xl text-center transition-all ${
                            airline === a.value
                              ? "bg-accent-500/20 border-2 border-accent-500"
                              : "bg-white/5 border-2 border-transparent hover:bg-white/10"
                          }`}
                        >
                          <span className="text-2xl block mb-1">{a.emoji}</span>
                          <span className="font-medium text-white text-sm">{a.label}</span>
                        </button>
                      ))}
                    </div>
                    {errors.airline && (
                      <p className="text-red-400 text-sm mt-2">{errors.airline}</p>
                    )}
                  </div>

                  {/* Delay Selection */}
                  <div className="mb-6">
                    <label className="block text-sm text-neutral-300 mb-3">
                      ¿Cuánto se retrasó o canceló?
                    </label>
                    <div className="space-y-3">
                      {DELAY_OPTIONS.map((opt) => (
                        <button
                          key={opt.value}
                          type="button"
                          onClick={() => {
                            setDelayHours(opt.value);
                            setErrors({ ...errors, delayHours: "" });
                          }}
                          className={`w-full p-4 rounded-2xl text-left transition-all flex justify-between items-center ${
                            delayHours === opt.value
                              ? "bg-gold-500/20 border-2 border-gold-500"
                              : "bg-white/5 border-2 border-transparent hover:bg-white/10"
                          }`}
                        >
                          <div>
                            <span className="font-medium text-white">{opt.label}</span>
                            <span className="text-neutral-300 text-sm block">{opt.description}</span>
                          </div>
                          {opt.value === 5.0 && (
                            <span className="text-gold-400 font-semibold">→ 125%</span>
                          )}
                        </button>
                      ))}
                    </div>
                    {errors.delayHours && (
                      <p className="text-red-400 text-sm mt-2">{errors.delayHours}</p>
                    )}
                  </div>

                  {/* Continue Button */}
                  <motion.button
                    type="button"
                    onClick={handleNextStep}
                    disabled={!airline || !delayHours}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className={`w-full py-4 rounded-full font-semibold text-lg transition-all ${
                      airline && delayHours
                        ? "bg-white text-obsidian-900 shadow-lg shadow-white/20"
                        : "bg-white/20 text-neutral-500 cursor-not-allowed"
                    }`}
                  >
                    Continuar →
                  </motion.button>
                </motion.div>
              )}

              {/* Step 2: Flight Details */}
              {step === 2 && (
                <motion.div
                  key="step2"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.3 }}
                >
                  <h2 className="text-2xl font-bold text-white mb-6">
                    Datos de tu vuelo
                  </h2>

                  {/* Ticket Price */}
                  <div className="mb-5">
                    <label className="block text-sm text-neutral-300 mb-2">
                      Precio del boleto (MXN) <span className="text-red-400">*</span>
                    </label>
                    <div className="relative">
                      <span className="absolute left-4 top-1/2 -translate-y-1/2 text-neutral-400">$</span>
                    <input
                        type="number"
                        value={ticketPrice}
                        onChange={(e) => {
                          setTicketPrice(e.target.value);
                          setErrors({ ...errors, ticketPrice: "" });
                        }}
                        onFocus={(e) => {
                          setTimeout(() => {
                            e.target.scrollIntoView({ behavior: "smooth", block: "center" });
                          }, 300);
                        }}
                        placeholder="2,500"
                        className="w-full bg-white/5 border-2 border-white/10 rounded-xl py-3 pl-8 pr-16 text-white
                                 placeholder:text-neutral-500 focus:border-accent-500 focus:outline-none transition-colors"
                      />
                      <span className="absolute right-4 top-1/2 -translate-y-1/2 text-neutral-400 text-sm">MXN</span>
                    </div>
                    {errors.ticketPrice && (
                      <p className="text-red-400 text-sm mt-1">{errors.ticketPrice}</p>
                    )}
                  </div>

                  {/* Flight Number & Reservation Code */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5">
                    <div>
                      <label className="block text-sm text-neutral-300 mb-2">
                        Número de vuelo <span className="text-red-400">*</span>
                      </label>
                      <input
                        type="text"
                        value={flightNumber}
                        onChange={(e) => {
                          setFlightNumber(e.target.value.toUpperCase());
                          setErrors({ ...errors, flightNumber: "" });
                        }}
                        onFocus={(e) => {
                          setTimeout(() => {
                            e.target.scrollIntoView({ behavior: "smooth", block: "center" });
                          }, 300);
                        }}
                        placeholder="VB 2847"
                        className="w-full bg-white/5 border-2 border-white/10 rounded-xl py-3 px-4 text-white
                                 placeholder:text-neutral-500 focus:border-accent-500 focus:outline-none transition-colors"
                      />
                      {errors.flightNumber && (
                        <p className="text-red-400 text-sm mt-1">{errors.flightNumber}</p>
                      )}
                    </div>
                    <div>
                      <label className="block text-sm text-neutral-300 mb-2">
                        Código de reserva
                        <span className="text-neutral-500 text-xs ml-1">(opcional)</span>
                      </label>
                      <input
                        type="text"
                        value={reservationCode}
                        onChange={(e) => setReservationCode(e.target.value.toUpperCase())}
                        onFocus={(e) => {
                          setTimeout(() => {
                            e.target.scrollIntoView({ behavior: "smooth", block: "center" });
                          }, 300);
                        }}
                        placeholder="ABC123"
                        className="w-full bg-white/5 border-2 border-white/10 rounded-xl py-3 px-4 text-white
                                 placeholder:text-neutral-500 focus:border-accent-500 focus:outline-none transition-colors"
                      />
                    </div>
                  </div>

                  {/* Flight Date */}
                  <div className="mb-5">
                    <label className="block text-sm text-neutral-300 mb-2">
                      Fecha del vuelo <span className="text-red-400">*</span>
                      <span className="text-neutral-500 text-xs ml-1">(últimos 12 meses)</span>
                    </label>
                    <input
                      type="date"
                      value={flightDate}
                      min={oneYearAgo}
                      max={today}
                      onChange={(e) => {
                        setFlightDate(e.target.value);
                        setErrors({ ...errors, flightDate: "" });
                      }}
                      className="w-full bg-white/5 border-2 border-white/10 rounded-xl py-3 px-4 text-white
                               focus:border-accent-500 focus:outline-none transition-colors
                               [color-scheme:dark]"
                    />
                    {errors.flightDate && (
                      <p className="text-red-400 text-sm mt-1">{errors.flightDate}</p>
                    )}
                  </div>

                  {/* Origin & Destination with Autocomplete */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5">
                    <AirportAutocomplete
                      value={origin}
                      onChange={(code) => {
                        setOrigin(code);
                        setErrors({ ...errors, origin: "" });
                      }}
                      label="Origen"
                      placeholder="Ej: MEX, Cancún..."
                      required
                      error={errors.origin}
                    />
                    <AirportAutocomplete
                      value={destination}
                      onChange={(code) => {
                        setDestination(code);
                        setErrors({ ...errors, destination: "" });
                      }}
                      label="Destino"
                      placeholder="Ej: CUN, CDMX..."
                      required
                      error={errors.destination}
                    />
                  </div>

                  {/* Passenger Count */}
                  <div className="mb-6">
                    <label className="block text-sm text-neutral-300 mb-2">
                      Número de pasajeros
                      <span className="text-neutral-500 text-xs ml-1">(en la misma reserva)</span>
                    </label>
                    <div className="flex items-center gap-4">
                      <button
                        type="button"
                        onClick={() => setPassengerCount(Math.max(1, passengerCount - 1))}
                        className="w-12 h-12 rounded-xl bg-white/5 text-white text-xl font-bold
                                 hover:bg-white/10 transition-colors"
                      >
                        −
                      </button>
                      <span className="text-2xl font-bold text-white w-12 text-center">
                        {passengerCount}
                      </span>
                      <button
                        type="button"
                        onClick={() => setPassengerCount(Math.min(10, passengerCount + 1))}
                        className="w-12 h-12 rounded-xl bg-white/5 text-white text-xl font-bold
                                 hover:bg-white/10 transition-colors"
                      >
                        +
                      </button>
                    </div>
                    {errors.passengerCount && (
                      <p className="text-red-400 text-sm mt-1">{errors.passengerCount}</p>
                    )}
                  </div>

                  {/* Buttons */}
                  <div className="flex gap-3">
                    <button
                      type="button"
                      onClick={handlePrevStep}
                      className="px-6 py-4 rounded-full font-semibold text-neutral-400 hover:text-white
                               bg-white/5 hover:bg-white/10 transition-all"
                    >
                      ← Atrás
                    </button>
                    <motion.button
                      type="button"
                      onClick={handleNextStep}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      className="flex-1 py-4 rounded-full font-semibold text-lg bg-white text-obsidian-900
                               shadow-lg shadow-white/20 transition-all"
                    >
                      Continuar →
                    </motion.button>
                  </div>
                </motion.div>
              )}

              {/* Step 3: Confirmation */}
              {step === 3 && (
                <motion.div
                  key="step3"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.3 }}
                >
                  <h2 className="text-2xl font-bold text-white mb-6">
                    Confirma tu reclamo
                  </h2>

                  {/* Summary Card */}
                  <div className="bg-white/5 rounded-2xl p-5 mb-6">
                    <div className="space-y-3 text-sm">
                      <div className="flex justify-between">
                        <span className="text-neutral-300">Aerolínea</span>
                        <span className="text-white font-medium">{airline}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-neutral-300">Vuelo</span>
                        <span className="text-white font-medium">{flightNumber}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-neutral-300">Ruta</span>
                        <span className="text-white font-medium">{origin} → {destination}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-neutral-300">Fecha</span>
                        <span className="text-white font-medium">{flightDate}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-neutral-300">Retraso</span>
                        <span className="text-red-400 font-medium">
                          {DELAY_OPTIONS.find(d => d.value === delayHours)?.label}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-neutral-300">Precio boleto</span>
                        <span className="text-white font-medium">{formatMXN(parseFloat(ticketPrice) || 0)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-neutral-300">Pasajeros</span>
                        <span className="text-white font-medium">{passengerCount}</span>
                      </div>
                    </div>
                  </div>

                  {/* Compensation Choice (only for 4+ hours) */}
                  {delayHours === 5.0 && (
                    <div className="mb-6">
                      <p className="text-sm text-neutral-300 mb-3">
                        Con +4 horas de retraso, puedes elegir cómo quieres tu compensación:
                      </p>
                      <label className="block text-sm text-neutral-400 mb-3">
                        ¿Qué prefieres reclamar?
                      </label>
                      <div className="space-y-3">
                        {COMPENSATION_CHOICES.map((choice) => (
                          <button
                            key={choice.value}
                            type="button"
                            onClick={() => setCompensationChoice(choice.value)}
                            className={`w-full p-4 rounded-2xl text-left transition-all ${
                              compensationChoice === choice.value
                                ? "bg-gold-500/20 border-2 border-gold-500"
                                : "bg-white/5 border-2 border-transparent hover:bg-white/10"
                            }`}
                          >
                            <span className="font-medium text-white">{choice.label}</span>
                            <span className="text-neutral-300 text-sm block">{choice.description}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Total Compensation */}
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="p-6 rounded-2xl bg-gradient-to-br from-gold-500/10 to-gold-600/5 border border-gold-500/20 mb-6"
                  >
                    <div className="text-center">
                      <p className="text-neutral-300 text-sm mb-2">Tu compensación total</p>
                      <p className="text-4xl font-bold gradient-text-gold">
                        {formatMXN(compensation)}
                      </p>
                      <p className="text-neutral-500 text-sm mt-2">
                        {passengerCount > 1 && `${passengerCount} pasajeros × ${formatMXN(compensation / passengerCount)}`}
                      </p>
                    </div>
                  </motion.div>

                  {/* Buttons */}
                  <div className="flex gap-3">
                    <button
                      type="button"
                      onClick={handlePrevStep}
                      className="px-6 py-4 rounded-full font-semibold text-neutral-400 hover:text-white
                               bg-white/5 hover:bg-white/10 transition-all"
                    >
                      ← Atrás
                    </button>
                    <motion.button
                      type="button"
                      onClick={handleSubmit}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      className="flex-1 py-4 rounded-full font-semibold text-lg bg-gradient-to-r from-accent-500 to-accent-600
                               text-white shadow-lg shadow-accent-500/30 transition-all"
                    >
                      Generar mi reclamo →
                    </motion.button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>

          {/* Trust indicators */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="mt-8 flex flex-wrap justify-center gap-6 text-neutral-400 text-sm"
          >
            <div className="flex items-center gap-2">
              <span>⚖️</span>
              <span>Art. 47 Bis</span>
            </div>
            <div className="flex items-center gap-2">
              <span>🛡️</span>
              <span>PROFECO respaldado</span>
            </div>
            <div className="flex items-center gap-2">
              <span>💳</span>
              <span>100% Gratis</span>
            </div>
          </motion.div>
        </div>
      </div>
    </main>
  );
}

function ReclamarLoading() {
  return (
    <main className="min-h-screen bg-obsidian-900">
      <Navbar />
      <div className="fixed inset-0 bg-gradient-mesh pointer-events-none" />
      <div className="relative z-10 pt-24 pb-16 px-6">
        <div className="max-w-lg mx-auto">
          <div className="mb-8">
            <div className="h-2 bg-white/10 rounded-full overflow-hidden">
              <div className="h-full w-1/3 bg-gradient-to-r from-accent-500 to-gold-500 animate-pulse" />
            </div>
          </div>
          <div className="glass-strong rounded-3xl p-6 md:p-8">
            <div className="animate-pulse space-y-6">
              <div className="h-8 bg-white/10 rounded-lg w-2/3" />
              <div className="grid grid-cols-3 gap-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-20 bg-white/5 rounded-2xl" />
                ))}
              </div>
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-16 bg-white/5 rounded-2xl" />
                ))}
              </div>
              <div className="h-14 bg-white/20 rounded-full" />
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}

export default function ReclamarPage() {
  return (
    <Suspense fallback={<ReclamarLoading />}>
      <ReclamarContent />
    </Suspense>
  );
}
