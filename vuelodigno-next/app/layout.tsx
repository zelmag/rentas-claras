import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VueloDigno - Reclama tu compensación",
  description:
    "Recupera hasta 125% del precio de tu boleto por vuelos retrasados o cancelados en México. Basado en la Ley de Aviación Civil.",
  icons: {
    icon: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body className="antialiased">{children}</body>
    </html>
  );
}
