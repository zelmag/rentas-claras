"use client";

import { useState, useEffect, Suspense } from "react";
import { motion } from "framer-motion";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import { formatMXN } from "@/lib/compensation";

function SuccessContent() {
  const searchParams = useSearchParams();

  // Data from URL params
  const [airline, setAirline] = useState("");
  const [flightNumber, setFlightNumber] = useState("");
  const [passengerEmail, setPassengerEmail] = useState("");
  const [compensation, setCompensation] = useState(0);

  // Calculated dates
  const [deadlineDate, setDeadlineDate] = useState("");
  const [profecoDeadline, setProfecoDeadline] = useState("");

  // Tweet state
  const [tweetCopied, setTweetCopied] = useState(false);

  // Parse URL params
  useEffect(() => {
    setAirline(searchParams.get("airline") || "");
    setFlightNumber(searchParams.get("flightNumber") || "");
    setPassengerEmail(searchParams.get("passengerEmail") || "");
    setCompensation(parseFloat(searchParams.get("compensation") || "0"));

    // Calculate deadline (10 days from now)
    const deadline = new Date();
    deadline.setDate(deadline.getDate() + 10);
    setDeadlineDate(formatDateSpanish(deadline));
    setProfecoDeadline(formatDateSpanish(deadline));
  }, [searchParams]);

  // Format date in Spanish
  function formatDateSpanish(date: Date): string {
    const months = [
      "enero", "febrero", "marzo", "abril", "mayo", "junio",
      "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ];
    const day = date.getDate();
    const month = months[date.getMonth()];
    const year = date.getFullYear();
    return `${day} de ${month} de ${year}`;
  }

  // Generate tweet text
  const tweetText = `@${getTwitterHandle(airline)} Mi vuelo ${flightNumber} tuvo un retraso significativo. Por ley (Art. 47 Bis) me corresponden ${formatMXN(compensation)}. Ya envié mi reclamo formal. ¿En cuánto tiempo puedo esperar respuesta? #DerechosDelPasajero #VueloDigno`;

  function getTwitterHandle(airlineName: string): string {
    const handles: Record<string, string> = {
      Volaris: "Volaris",
      VivaAerobus: "VivaAerobus",
      Aeromexico: "Aeromexico",
    };
    return handles[airlineName] || airlineName;
  }

  const handleCopyTweet = async () => {
    try {
      await navigator.clipboard.writeText(tweetText);
      setTweetCopied(true);
      setTimeout(() => setTweetCopied(false), 3000);
    } catch (err) {
      console.error("Copy failed:", err);
    }
  };

  const handleTweetNow = () => {
    const encodedTweet = encodeURIComponent(tweetText);
    window.open(`https://twitter.com/intent/tweet?text=${encodedTweet}`, "_blank");
  };

  // Confetti effect on mount
  useEffect(() => {
    // Dynamic import for confetti
    const shootConfetti = async () => {
      try {
        const confetti = (await import("canvas-confetti")).default;

        // First burst
        confetti({
          particleCount: 100,
          spread: 70,
          origin: { y: 0.6 },
          colors: ["#10b981", "#f59e0b", "#ffffff"],
        });

        // Second burst after delay
        setTimeout(() => {
          confetti({
            particleCount: 50,
            spread: 100,
            origin: { y: 0.7 },
            colors: ["#22c55e", "#eab308", "#3b82f6"],
          });
        }, 300);
      } catch (err) {
        console.log("Confetti not available:", err);
      }
    };

    shootConfetti();
  }, []);

  return (
    <main className="min-h-screen bg-obsidian-900">
      <Navbar />

      {/* Background effects */}
      <div className="fixed inset-0 bg-gradient-mesh pointer-events-none" />
      <div className="fixed top-1/3 left-1/3 w-96 h-96 bg-green-500/10 rounded-full blur-[120px] animate-pulse-glow pointer-events-none" />

      <div className="relative z-10 pt-24 pb-16 px-6">
        <div className="max-w-2xl mx-auto">
          {/* Progress Bar - Complete */}
          <div className="mb-8">
            <div className="h-2 bg-white/10 rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-green-500 to-green-400"
                initial={{ width: "80%" }}
                animate={{ width: "100%" }}
                transition={{ duration: 0.8, ease: "easeOut" }}
              />
            </div>
            <div className="flex justify-between mt-2 text-xs">
              <span className="text-green-400">✓ Aerolínea</span>
              <span className="text-green-400">✓ Vuelo</span>
              <span className="text-green-400">✓ Enviado</span>
            </div>
          </div>

          {/* Success Header */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
            className="text-center mb-8"
          >
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: "spring", stiffness: 200, delay: 0.2 }}
              className="text-7xl mb-4"
            >
              ✅
            </motion.div>
            <h1 className="text-3xl md:text-4xl font-bold text-white mb-3">
              ¡Lo lograste!
            </h1>
            <p className="text-xl text-neutral-300">
              Tu reclamación fue enviada a <span className="text-gold-400 font-semibold">{airline}</span>
            </p>
          </motion.div>

          {/* Next Steps Card */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="glass-strong rounded-2xl p-6 mb-6"
          >
            <div className="flex items-center gap-2 mb-4">
              <span className="text-green-400">📋</span>
              <h2 className="font-semibold text-white text-lg">Próximos Pasos</h2>
            </div>
            <ol className="space-y-4 text-neutral-300">
              <li className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-accent-500/20 text-accent-400 text-sm flex items-center justify-center font-semibold">1</span>
                <div>
                  <p>Recibirás una copia del reclamo en tu email</p>
                  <p className="text-sm text-neutral-500 mt-1">
                    Revisa: <span className="text-white">{passengerEmail}</span>
                  </p>
                </div>
              </li>
              <li className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-accent-500/20 text-accent-400 text-sm flex items-center justify-center font-semibold">2</span>
                <div>
                  <p>{airline} debe responder a más tardar el:</p>
                  <p className="text-white font-semibold mt-1">{deadlineDate}</p>
                  <p className="text-sm text-neutral-500 mt-1">(10 días naturales según la Ley de Aviación Civil)</p>
                </div>
              </li>
              <li className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-gold-500/20 text-gold-400 text-sm flex items-center justify-center font-semibold">3</span>
                <div>
                  <p>Si {airline} no responde antes del <span className="text-white font-semibold">{profecoDeadline}</span>:</p>
                  <a
                    href="https://consumidoras.profeco.gob.mx/conciliaexpress/solicitud.php"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 mt-2 px-4 py-2 bg-gold-500/10 text-gold-400 rounded-lg hover:bg-gold-500/20 transition-colors text-sm font-medium"
                  >
                    Presenta tu queja en PROFECO →
                  </a>
                </div>
              </li>
            </ol>
          </motion.div>

          {/* Compensation Reminder */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="p-6 rounded-2xl bg-gradient-to-br from-gold-500/10 to-gold-600/5 border border-gold-500/20 mb-6 text-center"
          >
            <p className="text-neutral-400 text-sm mb-1">Reclamaste</p>
            <p className="text-4xl font-bold gradient-text-gold">{formatMXN(compensation)}</p>
          </motion.div>

          {/* Twitter Pressure Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="glass rounded-2xl p-6 mb-6"
          >
            <div className="flex items-center gap-2 mb-4">
              <span className="text-2xl">💥</span>
              <h2 className="font-semibold text-white text-lg">
                ¿No te contestan? Presiónalos en X
              </h2>
            </div>

            {/* Tweet Preview */}
            <div className="bg-obsidian-800 rounded-xl p-4 mb-4 border border-white/5">
              <div className="flex items-center gap-3 mb-3 pb-3 border-b border-white/10">
                <div className="w-10 h-10 bg-black rounded-full flex items-center justify-center">
                  <span className="text-white text-lg font-bold">𝕏</span>
                </div>
                <div>
                  <p className="font-semibold text-white text-sm">Tu reclamación pública</p>
                  <p className="text-neutral-500 text-xs">Lista para compartir</p>
                </div>
              </div>
              <p className="text-neutral-300 text-sm leading-relaxed whitespace-pre-wrap">
                {tweetText}
              </p>
            </div>

            {/* Tweet Actions */}
            <div className="flex gap-3">
              <button
                onClick={handleCopyTweet}
                className={`flex-1 py-3 px-4 rounded-full font-medium text-sm transition-all flex items-center justify-center gap-2 ${
                  tweetCopied
                    ? "bg-green-500 text-white"
                    : "bg-white/10 text-white hover:bg-white/20"
                }`}
              >
                {tweetCopied ? "✓ Copiado!" : "📋 Copiar Texto"}
              </button>
              <button
                onClick={handleTweetNow}
                className="flex-1 py-3 px-4 rounded-full font-medium text-sm bg-black text-white hover:bg-neutral-800 transition-all flex items-center justify-center gap-2"
              >
                Editar en 𝕏
              </button>
            </div>
          </motion.div>

          {/* Feedback Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
            className="glass rounded-2xl p-6 mb-8"
          >
            <div className="flex items-center gap-2 mb-3">
              <span>💬</span>
              <h2 className="font-semibold text-white">Ayúdanos a mejorar</h2>
            </div>
            <p className="text-neutral-400 text-sm mb-4">
              Tu experiencia nos ayuda a hacer VueloDigno mejor para todos.
            </p>
            <a
              href="https://docs.google.com/forms/d/e/1FAIpQLSdcpq8h1YahgWGUivulhVnxDi8yGqrtClunlMu7SHYm48Ia4w/viewform"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2 bg-accent-500/10 text-accent-400 rounded-lg hover:bg-accent-500/20 transition-colors text-sm font-medium"
            >
              Responder encuesta (1 min) →
            </a>
          </motion.div>

          {/* New Claim Button */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.7 }}
            className="text-center"
          >
            <Link href="/">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="px-8 py-4 bg-white/10 text-white rounded-full font-semibold hover:bg-white/20 transition-all"
              >
                ← Volver al Inicio
              </motion.button>
            </Link>
          </motion.div>

          {/* Trust message */}
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8 }}
            className="text-center text-neutral-500 text-sm mt-8"
          >
            🙌 ¡Gracias por usar VueloDigno!
          </motion.p>
        </div>
      </div>
    </main>
  );
}

export default function SuccessPage() {
  return (
    <Suspense
      fallback={
        <main className="min-h-screen bg-obsidian-900 flex items-center justify-center">
          <div className="text-white">Cargando...</div>
        </main>
      }
    >
      <SuccessContent />
    </Suspense>
  );
}
