import Link from "next/link";

export default function TerminosPage() {
  return (
    <main className="min-h-screen bg-obsidian-900 py-20 px-6">
      <div className="max-w-3xl mx-auto">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-neutral-400 hover:text-white transition-colors mb-8"
        >
          ← Volver a inicio
        </Link>

        <h1 className="text-4xl font-bold gradient-text mb-8">
          Términos de Uso
        </h1>

        <div className="prose prose-invert prose-neutral max-w-none space-y-6 text-neutral-300">
          <p className="text-neutral-400 text-sm">
            Última actualización: Diciembre 2025
          </p>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              1. Aceptación de Términos
            </h2>
            <p>
              Al usar VueloDigno, aceptas estos términos. Si no estás de acuerdo,
              por favor no uses el servicio.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              2. Descripción del Servicio
            </h2>
            <p>
              VueloDigno es una herramienta gratuita que ayuda a los pasajeros a
              generar cartas de reclamación basadas en la Ley de Aviación Civil
              Mexicana (Art. 47 Bis). No somos un bufete de abogados ni
              proporcionamos asesoría legal.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              3. Uso del Servicio
            </h2>
            <ul className="list-disc pl-6 space-y-2">
              <li>
                La información que proporcionas debe ser veraz y precisa.
              </li>
              <li>
                Eres responsable de enviar la carta a la aerolínea correspondiente.
              </li>
              <li>
                VueloDigno no garantiza resultados específicos con las aerolíneas.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              4. Limitación de Responsabilidad
            </h2>
            <p>
              VueloDigno proporciona herramientas informativas basadas en la ley
              mexicana. No somos responsables de:
            </p>
            <ul className="list-disc pl-6 space-y-2 mt-2">
              <li>Las decisiones de las aerolíneas respecto a tu reclamación.</li>
              <li>Errores en la información proporcionada por el usuario.</li>
              <li>Cambios en la legislación aplicable.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              5. Propiedad Intelectual
            </h2>
            <p>
              Todo el contenido de VueloDigno, incluyendo diseño, textos y código,
              está protegido por derechos de autor. Las cartas generadas son para
              tu uso personal.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              6. Modificaciones
            </h2>
            <p>
              Podemos modificar estos términos en cualquier momento. Los cambios
              entran en vigor al publicarse en esta página.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              7. Contacto
            </h2>
            <p>
              Para preguntas sobre estos términos, escríbenos a{" "}
              <a
                href="mailto:hola@vuelodigno.com"
                className="text-gold-400 hover:text-gold-300 transition-colors"
              >
                hola@vuelodigno.com
              </a>
            </p>
          </section>
        </div>
      </div>
    </main>
  );
}
