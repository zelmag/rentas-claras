"use client";

import { useEffect } from "react";
import Link from "next/link";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="min-h-screen bg-obsidian-900 flex items-center justify-center px-6">
      <div className="fixed inset-0 bg-gradient-mesh pointer-events-none" />

      <div className="relative z-10 text-center max-w-md">
        <div className="text-6xl mb-6">⚠️</div>
        <h1 className="text-3xl font-bold text-white mb-4">
          ¡Algo salió mal!
        </h1>
        <p className="text-neutral-400 mb-8">
          Ocurrió un error inesperado. Por favor, intenta de nuevo.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <button
            onClick={() => reset()}
            className="px-6 py-3 bg-white text-obsidian-900 rounded-full font-semibold
                     hover:bg-neutral-200 transition-colors"
          >
            Intentar de nuevo
          </button>
          <Link
            href="/"
            className="px-6 py-3 bg-white/10 text-white rounded-full font-semibold
                     hover:bg-white/20 transition-colors"
          >
            Volver al inicio
          </Link>
        </div>
      </div>
    </main>
  );
}
