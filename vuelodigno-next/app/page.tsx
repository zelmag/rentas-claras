"use client";

import { useRef } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import HeroSection from "@/components/HeroSection";
import HowItWorksSection from "@/components/HowItWorksSection";
import BentoGrid from "@/components/BentoGrid";
import WhatsAppButton from "@/components/WhatsAppButton";
import { LAW_URL } from "@/lib/constants";

export default function Home() {
  const containerRef = useRef<HTMLDivElement>(null);

  return (
    <main
      ref={containerRef}
      className="relative min-h-screen bg-obsidian-900"
    >
      {/* Sticky Navigation */}
      <Navbar />

      {/* Background gradient mesh - z-0 to stay behind content */}
      <div className="fixed inset-0 bg-gradient-mesh pointer-events-none z-0" />

      {/* Ambient glow orbs - z-0 to stay behind content */}
      <div className="fixed top-1/4 left-1/4 w-96 h-96 bg-accent-500/5 rounded-full blur-[120px] animate-pulse-glow pointer-events-none z-0" />
      <div className="fixed bottom-1/4 right-1/4 w-80 h-80 bg-gold-500/5 rounded-full blur-[100px] animate-pulse-glow pointer-events-none z-0" />

      {/* Content wrapper with proper z-index to appear above fixed backgrounds */}
      <div className="relative z-10">
        {/* Hero Section */}
        <HeroSection />

        {/* How It Works Section - "Cómo Funciona" */}
        <HowItWorksSection />

        {/* Bento Grid - Mexican Law Section - "Tus Derechos" */}
        <section id="tus-derechos">
          <BentoGrid />
        </section>

        {/* FAQ Section */}
        <section id="preguntas-frecuentes" className="relative py-24 px-6">
          <div className="max-w-3xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8 }}
              viewport={{ once: true }}
              className="text-center mb-12"
            >
              <h2 className="text-3xl md:text-5xl font-bold mb-4 gradient-text">
                Preguntas Frecuentes
              </h2>
            </motion.div>

            <div className="space-y-4">
              {[
                {
                  q: "¿Cuánto tiempo tengo para reclamar?",
                  a: "Tienes hasta 2 años desde la fecha del vuelo para presentar tu reclamo ante la aerolínea o PROFECO. Aún estás a tiempo.",
                },
                {
                  q: "¿Qué documentos necesito?",
                  a: "Solo necesitas tu pase de abordar o confirmación de vuelo. Nosotros generamos la carta legal por ti, lista para enviar.",
                },
                {
                  q: "¿Realmente es gratis?",
                  a: "Sí, 100% gratis. Las aerolíneas te deben este dinero por ley. VueloDigno solo te ayuda a reclamarlo — sin comisiones ni costos ocultos.",
                },
                {
                  q: "¿Qué pasa si la aerolínea no responde?",
                  a: "Tienes 10 días para recibir respuesta. Si no responden, puedes escalar a PROFECO y la aerolínea recibe sanciones. No te preocupes, te guiamos en cada paso.",
                },
              ].map((faq, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                  viewport={{ once: true }}
                  className="glass p-6 rounded-2xl"
                >
                  <h3 className="font-semibold text-white mb-2">{faq.q}</h3>
                  <p className="text-neutral-300 text-sm">{faq.a}</p>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="relative py-24 flex items-center justify-center px-6">
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
            className="text-center max-w-3xl"
          >
            <h2 className="text-4xl md:text-6xl font-bold mb-6 gradient-text">
              De la demora a tus pesos
            </h2>
            <p className="text-xl text-neutral-300 mb-10">
              En 3 minutos, genera tu reclamo legal y recupera lo que te
              corresponde por ley.
            </p>
            <Link href="/reclamar">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.98 }}
                className="px-10 py-5 bg-white text-obsidian-900 rounded-full font-semibold text-lg
                           shadow-[0_0_40px_rgba(255,255,255,0.2)] hover:shadow-[0_0_60px_rgba(255,255,255,0.3)]
                           transition-all duration-300"
              >
                Ver cuánto me deben →
              </motion.button>
            </Link>
          </motion.div>
        </section>

        {/* WhatsApp Floating Button */}
        <WhatsAppButton />

        {/* Footer */}
        <footer id="footer" className="py-16 px-6 border-t border-white/5 bg-obsidian-900/50">
          <div className="max-w-6xl mx-auto">
            {/* Top section - 4 columns */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-10 mb-12 text-center md:text-left">
              {/* Brand column */}
              <div className="md:col-span-1">
                <div className="flex items-center justify-center md:justify-start gap-2 mb-4">
                  <span className="text-2xl">✈️</span>
                  <span className="font-bold text-xl text-white">VueloDigno</span>
                </div>
                <p className="text-neutral-400 text-sm leading-relaxed mb-4">
                  Reclama tu compensación por ley.
                  Basado en la{" "}
                  <a
                    href={LAW_URL}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-neutral-300 border-b border-neutral-600 hover:border-neutral-300 transition-colors"
                  >
                    Ley de Aviación Civil Mexicana
                  </a>{" "}
                  (Art. 47 Bis).
                </p>
                <p className="text-neutral-500 text-xs">
                  © 2025 VueloDigno
                </p>
              </div>

              {/* Navigation column */}
              <div>
                <h4 className="font-semibold text-white mb-4">Navegación</h4>
                <ul className="space-y-3 text-sm">
                  <li>
                    <a href="#como-funciona" className="text-neutral-400 hover:text-white transition-colors">
                      Cómo Funciona
                    </a>
                  </li>
                  <li>
                    <a href="#tus-derechos" className="text-neutral-400 hover:text-white transition-colors">
                      Tus Derechos
                    </a>
                  </li>
                  <li>
                    <a href="#preguntas-frecuentes" className="text-neutral-400 hover:text-white transition-colors">
                      Preguntas Frecuentes
                    </a>
                  </li>
                </ul>
              </div>

              {/* Airlines column */}
              <div>
                <h4 className="font-semibold text-white mb-4">Aerolíneas</h4>
                <ul className="space-y-3 text-sm">
                  <li className="flex items-center justify-center md:justify-start gap-2">
                    <span className="text-green-500">✓</span>
                    <span className="text-neutral-400">Aeroméxico</span>
                  </li>
                  <li className="flex items-center justify-center md:justify-start gap-2">
                    <span className="text-green-500">✓</span>
                    <span className="text-neutral-400">Volaris</span>
                  </li>
                  <li className="flex items-center justify-center md:justify-start gap-2">
                    <span className="text-green-500">✓</span>
                    <span className="text-neutral-400">VivaAerobus</span>
                  </li>
                </ul>
              </div>

              {/* Contact & Support column */}
              <div>
                <h4 className="font-semibold text-white mb-4">Soporte</h4>
                <ul className="space-y-3 text-sm">
                  <li>
                    <a
                      href="mailto:hola@vuelodigno.com"
                      className="text-gold-400 hover:text-gold-300 transition-colors inline-flex items-center justify-center md:justify-start gap-2"
                    >
                      <span>✉️</span>
                      hola@vuelodigno.com
                    </a>
                  </li>
                  <li className="pt-2">
                    <a
                      href="https://www.linkedin.com/in/zelmag/"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-neutral-400 hover:text-white transition-colors inline-flex items-center justify-center md:justify-start gap-2"
                    >
                      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
                      </svg>
                      Zelma Garza
                    </a>
                  </li>
                </ul>
              </div>
            </div>

            {/* About section */}
            <div className="glass p-6 rounded-2xl mb-10">
              <div className="flex flex-col md:flex-row items-start gap-4">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src="/zelma_pfp.png"
                  alt="Zelma Garza"
                  className="w-16 h-16 rounded-full object-cover flex-shrink-0 border-2 border-white/10"
                />
                <div>
                  <h4 className="font-semibold text-white mb-2 flex items-center gap-2">
                    Hola, soy Zelma
                    <a
                      href="https://www.linkedin.com/in/zelmag/"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-accent-400 hover:text-accent-300"
                    >
                      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
                      </svg>
                    </a>
                  </h4>
                  <p className="text-neutral-400 text-sm leading-relaxed">
                    Ingeniera de software mexicana 🇲🇽. Cuando les cancelaron a mis papás su vuelo a último minuto y ya no iban a poder verme correr un maratón en Islandia, investigué la ley, llamé a la aerolínea (no contestaron), mandé mensajes, tuiteé, hasta que nos dieron un vuelo sustituto.
                    Hice VueloDigno para que no tengas que pasar horas investigando para recibir tu compensación.
                  </p>
                  <p className="text-neutral-500 text-sm mt-2">
                    <strong className="text-gold-400">Es gratis</strong> porque las aerolíneas te deben este dinero por ley y me da coraje que no respondan.
                  </p>
                </div>
              </div>
            </div>

            {/* Bottom section - legal links */}
            <div className="flex flex-col md:flex-row items-center justify-between gap-4 pt-8 border-t border-white/5">
              <div className="flex gap-6 text-neutral-500 text-sm">
                <a href="/terminos" className="hover:text-white transition-colors">
                  Términos de Uso
                </a>
                <a href="/privacidad" className="hover:text-white transition-colors">
                  Política de Privacidad
                </a>
              </div>
              <p className="text-neutral-600 text-xs">
                Creado con ❤️ en México
              </p>
            </div>
          </div>
        </footer>
      </div>
    </main>
  );
}
