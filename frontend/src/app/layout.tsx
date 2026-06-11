import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DevisBTP — Devis IA pour artisans",
  description: "Générez vos devis professionnels en 30 secondes grâce à l'IA",
  viewport: "width=device-width, initial-scale=1, maximum-scale=1",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr">
      <body className="min-h-screen bg-gray-50">
        {children}
      </body>
    </html>
  );
}
