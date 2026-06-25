"use client";
import { useState } from "react";
import { FileDown, Loader2 } from "lucide-react";
import { exportToWord } from "@/lib/api";
import { Devis } from "@/lib/types";

interface WordExportButtonProps {
  devis: Devis;
  documentType: "devis" | "facture";
  withTva: boolean;
  documentDate: string;
  filename?: string;
}

export default function WordExportButton({ devis, documentType, withTva, documentDate, filename }: WordExportButtonProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleExport = async () => {
    setLoading(true);
    setError(null);
    try {
      await exportToWord(devis, documentType, withTva, documentDate, filename);
    } catch {
      setError("Erreur lors de la génération Word.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <button
        onClick={handleExport}
        disabled={loading}
        className="flex items-center gap-2 text-sm font-semibold border border-gray-300 rounded-xl px-4 py-2.5 bg-white hover:bg-gray-50 text-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        title="Télécharger en Word pour modifications avancées"
      >
        {loading ? (
          <><Loader2 className="w-4 h-4 animate-spin" /> Génération Word…</>
        ) : (
          <><FileDown className="w-4 h-4" /> Télécharger en Word</>
        )}
      </button>
      {error && <p className="text-red-500 text-xs mt-1">⚠️ {error}</p>}
    </div>
  );
}
