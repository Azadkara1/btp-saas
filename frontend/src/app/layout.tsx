import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "DevisBTP — Devis professionnel pour artisans",
  description: "Générez vos devis professionnels en quelques secondes",
  viewport: "width=device-width, initial-scale=1, maximum-scale=1",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr" className={inter.variable}>
      <body className={`min-h-screen ${inter.className}`} style={{ backgroundColor: "#FAFAF7" }}>
        {children}
      </body>
    </html>
  );
}
