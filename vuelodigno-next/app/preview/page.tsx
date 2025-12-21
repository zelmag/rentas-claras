"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter, useSearchParams } from "next/navigation";
import { calculateCompensation, formatMXN, getAirlineEmail } from "@/lib/compensation";
import { generateClaimLetter, markdownToHtml } from "@/lib/email-generator";
import { AirlineName, DelayTier, FlightData, CompensationChoice } from "@/lib/types";
import Navbar from "@/components/Navbar";

function PreviewContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const editorRef = useRef<HTMLDivElement>(null);

  // Form data from URL params
  const [flightData, setFlightData] = useState<FlightData | null>(null);
  const [letter, setLetter] = useState("");
  const [letterHtml, setLetterHtml] = useState("");
  const [airlineEmail, setAirlineEmail] = useState("");
  const [compensation, setCompensation] = useState(0);

  // User inputs on this page
  const [passengerName, setPassengerName] = useState("");
  const [passengerEmail, setPassengerEmail] = useState("");

  // Validation state for highlighting
  const [emailError, setEmailError] = useState(false);
  const [nameError, setNameError] = useState(false);

  // UI state
  const [isSending, setIsSending] = useState(false);
  const [showCopySuccess, setShowCopySuccess] = useState(false);
  const [error, setError] = useState("");

  // Parse URL params and generate letter
  useEffect(() => {
    const airline = searchParams.get("airline") as AirlineName;
    const delayHours = parseFloat(searchParams.get("delayHours") || "0") as DelayTier;
    const ticketPrice = parseFloat(searchParams.get("ticketPrice") || "0");
    const flightNumber = searchParams.get("flightNumber") || "";
    const reservationCode = searchParams.get("reservationCode") || "";
    const date = searchParams.get("date") || "";
    const origin = searchParams.get("origin") || "";
    const destination = searchParams.get("destination") || "";
    const passengerCount = parseInt(searchParams.get("passengerCount") || "1");
    const compensationChoice = (searchParams.get("compensationChoice") || "reembolso_indemnizacion") as CompensationChoice;

    if (!airline || !delayHours || !ticketPrice) {
      router.push("/reclamar");
      return;
    }

    const data: FlightData = {
      airline,
      delayHours,
      ticketPrice,
      flightNumber,
      reservationCode,
      date,
      origin,
      destination,
      passengerCount,
      compensationChoice,
    };

    setFlightData(data);

    // Get airline email
    const email = getAirlineEmail(airline);
    setAirlineEmail(email || "atencion@aerolinea.com");

    // Calculate compensation
    const comp = calculateCompensation(data);
    if (comp) {
      setCompensation(comp.totalAmount);
    }

    // Generate letter
    const generatedLetter = generateClaimLetter(data);
    setLetter(generatedLetter);
    setLetterHtml(markdownToHtml(generatedLetter));
  }, [searchParams, router]);

  // Update letter when passenger info changes
  useEffect(() => {
    if (flightData && (passengerName || passengerEmail)) {
      const updatedData = {
        ...flightData,
        passengerName: passengerName || "[TU NOMBRE]",
        passengerEmail: passengerEmail || "[TU EMAIL]",
      };
      const updatedLetter = generateClaimLetter(updatedData);
      setLetter(updatedLetter);
      setLetterHtml(markdownToHtml(updatedLetter));
    }
  }, [passengerName, passengerEmail, flightData]);

  const handleCopyToClipboard = async () => {
    try {
      const plainText = letter;
      const fullEmail = `Para: ${airlineEmail}\nDe: ${passengerEmail}\n\n${plainText}`;

      // Try to copy both HTML and plain text
      try {
        const htmlBlob = new Blob([letterHtml], { type: "text/html" });
        const textBlob = new Blob([fullEmail], { type: "text/plain" });
        await navigator.clipboard.write([
          new ClipboardItem({
            "text/html": htmlBlob,
            "text/plain": textBlob,
          }),
        ]);
      } catch {
        // Fallback to plain text
        await navigator.clipboard.writeText(fullEmail);
      }

      setShowCopySuccess(true);
      setTimeout(() => setShowCopySuccess(false), 5000);
    } catch (err) {
      console.error("Copy failed:", err);
      setError("No se pudo copiar. Selecciona y copia manualmente.");
    }
  };

  const handleSendEmail = async () => {
    // Reset error states
    setEmailError(false);
    setNameError(false);
    setError("");

    if (!passengerName.trim()) {
      setError("Por favor ingresa tu nombre");
      setNameError(true);
      return;
    }
    if (!passengerEmail.trim() || !passengerEmail.includes("@")) {
      setError("Por favor ingresa un email válido");
      setEmailError(true);
      return;
    }

    setIsSending(true);
    setError("");

    try {
      const response = await fetch("/api/send-email", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          flightData: {
            ...flightData,
            passengerName,
            passengerEmail,
          },
          letter,
          airlineEmail,
        }),
      });

      const result = await response.json();

      if (result.success) {
        // Navigate to success page
        const params = new URLSearchParams({
          airline: flightData?.airline || "",
          flightNumber: flightData?.flightNumber || "",
          passengerEmail,
          compensation: String(compensation),
        });
        router.push(`/success?${params.toString()}`);
      } else {
        setError(result.error || "Error al enviar. Intenta de nuevo.");
      }
    } catch (err) {
      console.error("Send failed:", err);
      setError("Error de conexión. Intenta de nuevo.");
    } finally {
      setIsSending(false);
    }
  };

  const handleGoBack = () => {
    if (flightData) {
      const params = new URLSearchParams({
        airline: flightData.airline,
        delay: String(flightData.delayHours),
      });
      router.push(`/reclamar?${params.toString()}`);
    } else {
      router.push("/reclamar");
    }
  };

  if (!flightData) {
    return (
      <main className="min-h-screen bg-obsidian-900 flex items-center justify-center">
        <div className="text-white">Cargando...</div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-obsidian-900">
      <Navbar />

      {/* Background effects */}
      <div className="fixed inset-0 bg-gradient-mesh pointer-events-none" />
      <div className="fixed top-1/4 right-1/4 w-96 h-96 bg-gold-500/5 rounded-full blur-[120px] animate-pulse-glow pointer-events-none" />

      <div className="relative z-10 pt-24 pb-16 px-6">
        <div className="max-w-2xl mx-auto">
          {/* Progress Bar */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-neutral-300">Paso final</span>
              <motion.span
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="text-gold-400 font-semibold"
              >
                💰 {formatMXN(compensation)}
              </motion.span>
            </div>
            <div className="h-2 bg-white/10 rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-accent-500 to-gold-500"
                initial={{ width: "66%" }}
                animate={{ width: "100%" }}
                transition={{ duration: 0.5, ease: "easeOut" }}
              />
            </div>
            <div className="flex justify-between mt-2 text-xs text-neutral-400">
              <span className="text-accent-400">✓ Aerolínea</span>
              <span className="text-accent-400">✓ Vuelo</span>
              <span className="text-gold-400 font-semibold">Enviar</span>
            </div>
          </div>

          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center mb-8"
          >
            <h1 className="text-3xl font-bold text-white mb-2">
              🚀 ¡Tu Reclamo está Listo!
            </h1>
            <p className="text-neutral-400">
              Revisa y personaliza tu carta antes de enviarla
            </p>
          </motion.div>

          {/* Contact Info Card */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="glass-strong rounded-2xl p-5 mb-6"
          >
            <div className="flex items-center gap-2 mb-4">
              <span className="text-accent-400">🔒</span>
              <span className="font-semibold text-white">Tus Datos</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-neutral-300 mb-2">
                  Nombre(s) <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={passengerName}
                  onChange={(e) => {
                    setPassengerName(e.target.value);
                    setNameError(false);
                    setError("");
                  }}
                  placeholder={flightData.passengerCount > 1 ? "Ej: Juan Pérez, María Pérez" : "Ej: Juan Pérez"}
                  className={`w-full bg-white/5 border-2 rounded-xl py-3 px-4 text-white
                           placeholder:text-neutral-500 focus:border-accent-500 focus:outline-none transition-colors
                           ${nameError ? "border-red-500" : "border-white/10"}`}
                />
              </div>
              <div>
                <label className="block text-sm text-neutral-300 mb-2">
                  Tu email <span className="text-red-400">*</span>
                </label>
                <input
                  type="email"
                  value={passengerEmail}
                  onChange={(e) => {
                    setPassengerEmail(e.target.value);
                    setEmailError(false);
                    setError("");
                  }}
                  placeholder="tu@email.com"
                  className={`w-full bg-white/5 border-2 rounded-xl py-3 px-4 text-white
                           placeholder:text-neutral-500 focus:border-accent-500 focus:outline-none transition-colors
                           ${emailError ? "border-red-500" : "border-white/10"}`}
                />
              </div>
            </div>
          </motion.div>

          {/* Letter Editor */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="mb-6"
          >
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-semibold text-white">
                📝 Tu carta legal
              </h2>
              <span className="text-xs text-gold-400 bg-gold-500/10 px-3 py-1 rounded-full">
                💡 Haz clic para editar
              </span>
            </div>

            {/* Copy Success Message */}
            <AnimatePresence>
              {showCopySuccess && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="mb-4 p-4 bg-green-500/10 border border-green-500/30 rounded-xl"
                >
                  <div className="flex items-start gap-3">
                    <span className="text-2xl">✅</span>
                    <div>
                      <p className="font-semibold text-green-400">¡Email copiado!</p>
                      <p className="text-sm text-neutral-400 mt-1">
                        1. Abre tu cliente de email (Gmail, Outlook, etc.)<br />
                        2. Pega el email (Ctrl+V o Cmd+V)<br />
                        3. Envíalo a: <strong className="text-white">{airlineEmail}</strong>
                      </p>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Editable Letter */}
            <div
              ref={editorRef}
              contentEditable
              suppressContentEditableWarning
              dangerouslySetInnerHTML={{ __html: letterHtml }}
              className="bg-white/5 border-2 border-accent-500/50 rounded-2xl p-4 md:p-6 text-white text-sm leading-relaxed
                       focus:border-accent-500 focus:outline-none min-h-[300px] md:min-h-[400px] max-h-[400px] md:max-h-[500px] overflow-y-auto
                       [&_strong]:text-gold-400 [&_a]:text-accent-400 [&_a]:underline"
              style={{ fontFamily: "system-ui, sans-serif" }}
            />

            {/* Airline Email Badge */}
            <div className="mt-4 p-3 bg-green-500/10 border border-green-500/20 rounded-xl flex items-center gap-2">
              <span className="text-green-400">📧</span>
              <span className="text-neutral-400 text-sm">Para:</span>
              <span className="text-white font-medium">{airlineEmail}</span>
            </div>
          </motion.div>

          {/* Error Message */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="mb-4 p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm"
              >
                ⚠️ {error}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Action Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="flex flex-col sm:flex-row gap-3"
          >
            <button
              type="button"
              onClick={handleGoBack}
              className="px-6 py-4 rounded-full font-semibold text-neutral-400 hover:text-white
                       bg-white/5 hover:bg-white/10 transition-all"
            >
              ← Volver
            </button>

            <button
              type="button"
              onClick={handleCopyToClipboard}
              className="flex-1 sm:flex-none px-6 py-4 rounded-full font-semibold text-white
                       bg-white/10 hover:bg-white/20 transition-all flex items-center justify-center gap-2"
            >
              📋 Copiar Email
            </button>

            <motion.button
              type="button"
              onClick={handleSendEmail}
              disabled={isSending}
              whileHover={{ scale: isSending ? 1 : 1.02 }}
              whileTap={{ scale: isSending ? 1 : 0.98 }}
              className={`flex-1 py-4 rounded-full font-semibold text-lg transition-all flex items-center justify-center gap-2 ${
                isSending
                  ? "bg-neutral-600 text-neutral-400 cursor-not-allowed"
                  : "bg-gradient-to-r from-accent-500 to-accent-600 text-white shadow-lg shadow-accent-500/30"
              }`}
            >
              {isSending ? (
                <>
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Enviando...
                </>
              ) : (
                <>✉️ Enviar Ahora</>
              )}
            </motion.button>
          </motion.div>

          {/* Trust indicators */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="mt-8 flex flex-wrap justify-center gap-6 text-neutral-400 text-sm"
          >
            <div className="flex items-center gap-2">
              <span>🔐</span>
              <span>Enviado desde VueloDigno</span>
            </div>
            <div className="flex items-center gap-2">
              <span>📧</span>
              <span>Copia a tu email</span>
            </div>
          </motion.div>
        </div>
      </div>
    </main>
  );
}

export default function PreviewPage() {
  return (
    <Suspense fallback={
      <main className="min-h-screen bg-obsidian-900 flex items-center justify-center">
        <div className="text-white">Cargando...</div>
      </main>
    }>
      <PreviewContent />
    </Suspense>
  );
}
