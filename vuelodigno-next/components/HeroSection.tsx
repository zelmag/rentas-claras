"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { LAW_URL } from "@/lib/constants";

export default function HeroSection() {
  return (
    <section className="relative min-h-[90vh] flex flex-col items-center justify-center px-6 overflow-hidden">
      {/* Hero content */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 1, ease: "easeOut" }}
        className="relative z-10 text-center max-w-5xl"
      >
        {/* Eyebrow */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.6 }}
          className="inline-flex items-center gap-2 px-4 py-2 mb-8 glass rounded-full"
        >
          <span className="text-sm">🇲🇽</span>
          <a
            href={LAW_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-neutral-300 hover:text-accent-400 transition-colors"
          >
            Ley de Aviación Civil Mexicana
          </a>
        </motion.div>

        {/* Main headline */}
        <motion.h1
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.8 }}
          className="text-4xl md:text-7xl lg:text-8xl font-bold tracking-tight leading-[0.95] mb-6"
        >
          <span className="gradient-text">Tu vuelo.</span>
          <br />
          <span className="gradient-text">Tu derecho.</span>
          <br />
          <span className="gradient-text-gold">Tu compensación.</span>
        </motion.h1>

        {/* Subheadline */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.8 }}
          className="text-xl md:text-2xl text-neutral-300 max-w-2xl mx-auto mb-4 leading-relaxed"
        >
          Recupera hasta el{" "}
          <span className="text-gold-400 font-semibold">125%</span> del precio
          de tu boleto por retrasos o cancelaciones.
        </motion.p>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 0.8 }}
          className="text-lg text-neutral-400 max-w-2xl mx-auto mb-10"
        >
          En 3 minutos recibes tu carta legal lista para enviar.
        </motion.p>

        {/* CTA Button */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7, duration: 0.5 }}
          className="flex flex-col items-center gap-4"
        >
          <Link href="/reclamar">
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.98 }}
              className="px-8 py-4 bg-white text-obsidian-900 rounded-full font-semibold text-lg
                         shadow-[0_0_40px_rgba(255,255,255,0.15)] hover:shadow-[0_0_60px_rgba(255,255,255,0.25)]
                         transition-all duration-300"
            >
              Ver cuánto me deben →
            </motion.button>
          </Link>

          <div className="flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-neutral-400 text-sm">
            <span className="flex items-center gap-1">
              <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
              3 pasos
            </span>
            <span className="hidden sm:inline text-neutral-500">•</span>
            <span>Sin registro</span>
            <span className="hidden sm:inline text-neutral-500">•</span>
            <span>100% gratis</span>
          </div>
        </motion.div>

        {/* Trust indicators */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1, duration: 0.8 }}
          className="mt-16 flex flex-wrap justify-center gap-8 text-neutral-400 text-sm"
        >
          <div className="flex items-center gap-2">
            <span className="text-lg">⚖️</span>
            <span>Art. 47 Bis</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-lg">🛡️</span>
            <span>PROFECO respaldado</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-lg">💳</span>
            <span>100% Gratis</span>
          </div>
        </motion.div>
      </motion.div>

      {/* Floating glass orbs - hidden on mobile */}
      <motion.div
        animate={{ y: [0, -20, 0], rotate: [0, 5, 0] }}
        transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
        className="hidden md:block absolute top-1/4 right-[15%] w-32 h-32 glass rounded-full opacity-15"
      />
      <motion.div
        animate={{ y: [0, 15, 0], rotate: [0, -3, 0] }}
        transition={{ duration: 6, repeat: Infinity, ease: "easeInOut", delay: 1 }}
        className="hidden md:block absolute bottom-1/3 left-[10%] w-24 h-24 glass rounded-full opacity-10"
      />
    </section>
  );
}
