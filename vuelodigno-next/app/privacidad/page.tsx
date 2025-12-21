import Link from "next/link";

export default function PrivacidadPage() {
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
          Política de Privacidad
        </h1>

        <div className="prose prose-invert prose-neutral max-w-none space-y-6 text-neutral-300">
          <p className="text-neutral-400 text-sm">
            Última actualización: Diciembre 2025
          </p>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              1. Información que Recopilamos
            </h2>
            <p>
              Para generar tu carta de reclamación, recopilamos:
            </p>
            <ul className="list-disc pl-6 space-y-2 mt-2">
              <li>Nombre completo</li>
              <li>Correo electrónico</li>
              <li>Información del vuelo (aerolínea, número de vuelo, fechas)</li>
              <li>Precio del boleto</li>
              <li>Descripción del problema</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              2. Cómo Usamos tu Información
            </h2>
            <p>Tu información se utiliza exclusivamente para:</p>
            <ul className="list-disc pl-6 space-y-2 mt-2">
              <li>Generar tu carta de reclamación personalizada</li>
              <li>Enviarte la carta por correo electrónico</li>
              <li>Responder a tus consultas de soporte</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              3. Compartir Información
            </h2>
            <p>
              <strong>No vendemos ni compartimos tu información personal</strong> con
              terceros, excepto:
            </p>
            <ul className="list-disc pl-6 space-y-2 mt-2">
              <li>
                Proveedores de servicios necesarios (como servicios de email)
              </li>
              <li>Cuando la ley lo requiera</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              4. Seguridad
            </h2>
            <p>
              Implementamos medidas de seguridad para proteger tu información,
              incluyendo cifrado en tránsito (HTTPS) y almacenamiento seguro.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              5. Retención de Datos
            </h2>
            <p>
              Mantenemos tu información solo mientras sea necesario para
              proporcionarte el servicio. Puedes solicitar la eliminación de tus
              datos en cualquier momento.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              6. Tus Derechos
            </h2>
            <p>Tienes derecho a:</p>
            <ul className="list-disc pl-6 space-y-2 mt-2">
              <li>Acceder a tus datos personales</li>
              <li>Solicitar la corrección de datos incorrectos</li>
              <li>Solicitar la eliminación de tus datos</li>
              <li>Retirar tu consentimiento en cualquier momento</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              7. Cookies
            </h2>
            <p>
              Usamos cookies esenciales para el funcionamiento del sitio. No
              usamos cookies de rastreo ni publicidad.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              8. Cambios a esta Política
            </h2>
            <p>
              Podemos actualizar esta política ocasionalmente. Los cambios se
              publicarán en esta página con la fecha de actualización.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              9. Contacto
            </h2>
            <p>
              Para ejercer tus derechos o preguntas sobre privacidad, escríbenos
              a{" "}
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
