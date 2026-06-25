"use client";
import { useRef, useState } from "react";
import { Upload, Loader2, FileText } from "lucide-react";
import { QuoteResponse } from "@/lib/types";
import { importQuote } from "@/lib/api";

interface ImportButtonProps {
  modele?: string;
  onImported: (response: QuoteResponse) => void;
}

export default function ImportButton({ modele = "moderne", onImported }: ImportButtonProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState<string | null>(null);
  const [filename, setFilename] = useState<string | null>(null);

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setError(null);
    setFilename(file.name);
    setLoading(true);

    try {
      // Lit le profil artisan depuis localStorage (même clé que QuoteForm)
      let artisanFields: Record<string, string> = { modele };
      try {
        const saved = localStorage.getItem("artisan_profile");
        if (saved) {
          artisanFields = { ...JSON.parse(saved), modele };
        }
      } catch {
        // Pas de profil sauvegardé — l'artisan sera vide
      }

      const result = await importQuote(file, artisanFields);
      if (result.success) {
        onImported(result);
      } else {
        setError(result.error || "L'extraction a échoué. Vérifiez que le fichier est lisible.");
        setFilename(null);
      }
    } catch {
      setError("Erreur réseau. Vérifiez votre connexion.");
      setFilename(null);
    } finally {
      setLoading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <div className="flex flex-col items-center gap-2">
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx"
        onChange={handleFile}
        disabled={loading}
        className="sr-only"
        id="import-file-input"
      />

      <label
        htmlFor="import-file-input"
        className={`
          inline-flex items-center gap-2.5 text-sm font-semibold rounded-2xl px-6 py-3
          border-2 border-dashed transition-colors select-none
          ${loading
            ? "opacity-60 cursor-not-allowed pointer-events-none"
            : "cursor-pointer hover:border-green-700 hover:bg-[#E3EDE6]"
          }
        `}
        style={{
          borderColor: "rgba(20,83,45,0.4)",
          color: "#14532D",
          backgroundColor: "#F0F7F3",
        }}
      >
        {loading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Extraction en cours…
            {filename && (
              <span className="text-xs font-normal opacity-70 truncate max-w-[160px]">
                {filename}
              </span>
            )}
          </>
        ) : (
          <>
            <Upload className="w-4 h-4" />
            Importer un devis existant
          </>
        )}
      </label>

      {!loading && !error && (
        <p className="flex items-center gap-1 text-xs" style={{ color: "#7C857F" }}>
          <FileText className="w-3 h-3" />
          PDF ou .docx — max 10 Mo
        </p>
      )}

      {error && (
        <p className="text-xs text-red-600 text-center max-w-xs">{error}</p>
      )}
    </div>
  );
}
