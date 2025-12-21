import Link from "next/link";

export default function NotFound() {
  return (
    <main className="min-h-screen bg-obsidian-900 flex items-center justify-center px-6">
      <div className="fixed inset-0 bg-gradient-mesh pointer-events-none" />

      <div className="relative z-10 text-center max-w-md">
        <div className="text-6xl mb-6">🔍</div>
        <h1 className="text-3xl font-bold text-white mb-4">
          Página no encontrada
        </h1>
        <p className="text-neutral-400 mb-8">
          La página que buscas no existe o ha sido movida.
        </p>

        <Link
          href="/"
          className="inline-block px-6 py-3 bg-white text-obsidian-900 rounded-full font-semibold
                   hover:bg-neutral-200 transition-colors"
        >
          Volver al inicio
        </Link>
      </div>
    </main>
  );
}
