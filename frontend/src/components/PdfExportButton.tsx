"use client";
/**
 * Bouton d'export PDF.
 * Appelle le backend et déclenche le téléchargement automatique.
 */
import { useState } from "react";
import { Download, Loader2 } from "lucide-react";
import { exportToPdf } from "@/lib/api";
import { Devis } from "@/lib/types";

interface PdfExportButtonProps {
  devis: Devis;
  documentType: "devis" | "facture";
  withTva: boolean;
  documentDate: string;
}

export default function PdfExportButton({ devis, documentType, withTva, documentDate }: PdfExportButtonProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleExport = async () => {
    setLoading(true);
    setError(null);
    try {
      await exportToPdf(devis, documentType, withTva, documentDate);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur génération PDF.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <button
        onClick={handleExport}
        disabled={loading}
        className="btn-primary flex items-center gap-2"
      >
        {loading ? (
          <><Loader2 className="w-4 h-4 animate-spin" /> Génération PDF…</>
        ) : (
          <><Download className="w-4 h-4" /> Télécharger le PDF</>
        )}
      </button>
      {error && <p className="text-red-500 text-sm mt-2">⚠️ {error}</p>}
    </div>
  );
}
