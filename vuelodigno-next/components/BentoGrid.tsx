"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { LAW_URL } from "@/lib/constants";

interface BentoItemProps {
  icon: string;
  title: string;
  description: string;
  highlight?: string;
  delay?: number;
  isCarousel?: boolean;
  featured?: boolean;
}

function BentoItem({
  icon,
  title,
  description,
  highlight,
  delay = 0,
  isCarousel = false,
  featured = false,
}: BentoItemProps) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, amount: 0.3 });

  // Carousel items have fixed width, grid items are flexible
  // Featured items span 2 columns on desktop
  const baseClasses = isCarousel
    ? "flex-shrink-0 w-[85vw] max-w-[320px] snap-center"
    : featured
    ? "md:col-span-2"
    : "";

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 30 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.6, delay }}
      whileHover={{ scale: 1.02 }}
      className={`${baseClasses} bento-item glass p-6 md:p-8 cursor-default group relative overflow-hidden ${
        featured ? "border-gold-500/20" : ""
      }`}
    >
      {/* Hover glow overlay */}
      <div className="absolute inset-0 rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 bg-gradient-to-br from-accent-500/5 to-transparent pointer-events-none" />

      <motion.div
        initial={{ scale: 1 }}
        whileHover={{ scale: 1.1, rotate: [0, -5, 5, 0] }}
        transition={{ duration: 0.4 }}
        className="text-4xl mb-4"
      >
        {icon}
      </motion.div>

      <h3 className="text-lg md:text-xl font-bold mb-2 text-white">{title}</h3>

      {highlight && (
        <p className="text-2xl md:text-3xl font-bold gradient-text-gold mb-3">
          {highlight}
        </p>
      )}

      <p className="text-neutral-400 text-sm leading-relaxed">
        {description}
      </p>
    </motion.div>
  );
}

// Carousel card data
const bentoCards = [
  {
    icon: "🚫",
    title: "+4 horas o Cancelación",
    highlight: "125%",
    description: "Reembolso completo (100%) más 25% de indemnización.",
    featured: true,
  },
  {
    icon: "⏱️",
    title: "Demoras 1-4 horas",
    highlight: "7.5%+",
    description: "Mínimo 7.5% del boleto más alimentos y asistencia.",
    featured: false,
  },
  {
    icon: "📅",
    title: "Plazo de pago",
    highlight: "10 días",
    description: "La aerolínea debe pagarte en máximo 10 días naturales.",
    featured: false,
  },
  {
    icon: "🛡️",
    title: "PROFECO te respalda",
    highlight: undefined,
    description: "Si no responden, escalas tu queja y la aerolínea recibe sanciones.",
    featured: false,
  },
];

export default function BentoGrid() {
  const sectionRef = useRef<HTMLDivElement>(null);
  const isInView = useInView(sectionRef, { once: true, amount: 0.1 });

  return (
    <section
      ref={sectionRef}
      className="relative py-24 flex flex-col items-center justify-center"
    >
      {/* Section header */}
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={isInView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.8 }}
        className="text-center max-w-3xl mb-12 px-6"
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={isInView ? { opacity: 1, scale: 1 } : {}}
          transition={{ delay: 0.2, duration: 0.6 }}
          className="inline-flex items-center gap-2 px-4 py-2 mb-6 glass rounded-full"
        >
          <span>⚖️</span>
          <span className="text-sm text-neutral-300">
            Artículo 47 Bis
          </span>
        </motion.div>

        <h2 className="text-3xl md:text-5xl font-bold mb-4 gradient-text">
          Tus derechos por ley
        </h2>
        <p className="text-lg text-neutral-400">
          La{" "}
          <a
            href={LAW_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="text-neutral-300 hover:text-white underline underline-offset-2 decoration-neutral-600 hover:decoration-neutral-400 transition-colors"
          >
            Ley de Aviación Civil Mexicana
          </a>{" "}
          te protege.
        </p>
      </motion.div>

      {/* Mobile: Horizontal scroll carousel */}
      <div className="md:hidden w-full overflow-hidden">
        <div className="flex gap-4 overflow-x-auto snap-x snap-mandatory px-6 pb-4 scrollbar-hide">
          {bentoCards.map((card, index) => (
            <BentoItem
              key={card.title}
              icon={card.icon}
              title={card.title}
              highlight={card.highlight}
              description={card.description}
              delay={index * 0.1}
              isCarousel={true}
            />
          ))}
          {/* Extra padding at end for last card visibility */}
          <div className="flex-shrink-0 w-4" />
        </div>
        {/* Scroll hint indicator */}
        <div className="flex justify-center gap-2 mt-4">
          {bentoCards.map((_, index) => (
            <div
              key={index}
              className="w-2 h-2 rounded-full bg-neutral-600"
            />
          ))}
        </div>
      </div>

      {/* Desktop: Grid layout */}
      <div className="hidden md:grid w-full max-w-4xl grid-cols-2 gap-6 px-6">
        {bentoCards.map((card, index) => (
          <BentoItem
            key={card.title}
            icon={card.icon}
            title={card.title}
            highlight={card.highlight}
            description={card.description}
            delay={index * 0.1}
            isCarousel={false}
            featured={card.featured}
          />
        ))}
      </div>
    </section>
  );
}
