"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import Link from "next/link";

const steps = [
  {
    number: "1",
    icon: "✈️",
    title: "Cuéntanos qué pasó",
    description: "Ingresa los datos de tu vuelo retrasado o cancelado en menos de 2 minutos.",
  },
  {
    number: "2",
    icon: "🧮",
    title: "Calculamos tu compensación",
    description: "Te mostramos exactamente cuánto te debe la aerolínea según la ley mexicana.",
  },
  {
    number: "3",
    icon: "📧",
    title: "Recibe tu carta legal",
    description: "Te enviamos un documento profesional listo para enviar a la aerolínea.",
  },
];

export default function HowItWorksSection() {
  const sectionRef = useRef<HTMLDivElement>(null);
  const isInView = useInView(sectionRef, { once: true, amount: 0.2 });

  return (
    <section
      id="como-funciona"
      ref={sectionRef}
      className="relative py-24 px-6"
    >
      {/* Section header */}
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={isInView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.8 }}
        className="text-center max-w-3xl mx-auto mb-16"
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={isInView ? { opacity: 1, scale: 1 } : {}}
          transition={{ delay: 0.2, duration: 0.6 }}
          className="inline-flex items-center gap-2 px-4 py-2 mb-6 glass rounded-full"
        >
          <span>⚡</span>
          <span className="text-sm text-neutral-300">3 pasos simples</span>
        </motion.div>

        <h2 className="text-3xl md:text-5xl font-bold mb-4 gradient-text">
          Cómo Funciona
        </h2>
        <p className="text-lg text-neutral-300">
          Reclama tu compensación en minutos, no en horas.
        </p>
      </motion.div>

      {/* Steps */}
      <div className="max-w-4xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {steps.map((step, index) => (
            <motion.div
              key={step.number}
              initial={{ opacity: 0, y: 40 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.6, delay: 0.2 + index * 0.15 }}
              className="relative"
            >
              {/* Connecting line (hidden on mobile, visible on desktop) */}
              {index < steps.length - 1 && (
                <motion.div
                  initial={{ scaleX: 0 }}
                  animate={isInView ? { scaleX: 1 } : {}}
                  transition={{ duration: 0.8, delay: 0.5 + index * 0.15 }}
                  className="hidden md:block absolute top-12 left-[60%] w-[80%] h-[2px] bg-gradient-to-r from-accent-500/40 to-transparent origin-left"
                />
              )}

              {/* Step card */}
              <motion.div
                whileHover={{ scale: 1.03, y: -5 }}
                transition={{ duration: 0.3 }}
                className="glass p-8 rounded-3xl text-center relative overflow-hidden group h-full flex flex-col"
              >
                {/* Hover glow */}
                <div className="absolute inset-0 rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 bg-gradient-to-br from-accent-500/10 to-transparent pointer-events-none" />

                {/* Step number */}
                <motion.div
                  initial={{ scale: 0 }}
                  animate={isInView ? { scale: 1 } : {}}
                  transition={{
                    type: "spring",
                    stiffness: 200,
                    delay: 0.3 + index * 0.15,
                  }}
                  className="inline-flex items-center justify-center w-10 h-10 mb-4 rounded-full bg-accent-500/20 text-accent-400 font-bold text-lg"
                >
                  {step.number}
                </motion.div>

                {/* Icon */}
                <motion.div
                  animate={isInView ? { rotate: [0, -10, 10, 0] } : {}}
                  transition={{
                    duration: 0.6,
                    delay: 0.5 + index * 0.15,
                    repeat: 0,
                  }}
                  className="text-5xl mb-4"
                >
                  {step.icon}
                </motion.div>

                {/* Title */}
                <h3 className="text-xl font-bold text-white mb-3">
                  {step.title}
                </h3>

                {/* Description */}
                <p className="text-neutral-300 text-sm leading-relaxed flex-grow">
                  {step.description}
                </p>
              </motion.div>
            </motion.div>
          ))}
        </div>

        {/* CTA */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, delay: 0.8 }}
          className="text-center mt-12"
        >
          <Link href="/reclamar">
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.98 }}
              className="px-8 py-4 bg-white text-obsidian-900 rounded-full font-semibold text-lg
                         shadow-[0_0_30px_rgba(255,255,255,0.15)] hover:shadow-[0_0_50px_rgba(255,255,255,0.25)]
                         transition-all duration-300"
            >
              Comenzar ahora →
            </motion.button>
          </Link>
        </motion.div>
      </div>
    </section>
  );
}
