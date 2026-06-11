"use client";
/**
 * Page principale — interface de génération de devis/facture.
 * UX pensée pour le chantier : simple, lisible, efficace sur mobile.
 */
import { useState } from "react";
import { HardHat, RefreshCw, FileText, Receipt, Percent, Calendar } from "lucide-react";
import QuoteForm from "@/components/QuoteForm";
import QuotePreview from "@/components/QuotePreview";
import PdfExportButton from "@/components/PdfExportButton";
import WordExportButton from "@/components/WordExportButton";
import { QuoteResponse, Devis } from "@/lib/types";

type DocumentType = "devis" | "facture";

function DocTypeToggle({
  value, onChange, size = "md",
}: {
  value: DocumentType;
  onChange: (v: DocumentType) => void;
  size?: "sm" | "md";
}) {
  const cls = size === "md"
    ? "flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition-all"
    : "flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-semibold transition-all";

  return (
    <div className="flex items-center bg-gray-100 rounded-2xl p-1.5 gap-1">
      <button onClick={() => onChange("devis")}
        className={`${cls} ${value === "devis" ? "bg-white shadow-sm text-blue-700" : "text-gray-500 hover:text-gray-700"}`}>
        <FileText className="w-4 h-4" /> Devis
      </button>
      <button onClick={() => onChange("facture")}
        className={`${cls} ${value === "facture" ? "bg-white shadow-sm text-blue-700" : "text-gray-500 hover:text-gray-700"}`}>
        <Receipt className="w-4 h-4" /> Facture
      </button>
    </div>
  );
}

export default function HomePage() {
  const [result, setResult] = useState<Devis | null>(null);
  const [tokensUsed, setTokensUsed] = useState<number | null>(null);
  const [documentType, setDocumentType] = useState<DocumentType>("devis");
  const [withTva, setWithTva] = useState(true);
  const [documentDate, setDocumentDate] = useState<string>(
    () => new Date().toISOString().split("T")[0]   // format "YYYY-MM-DD"
  );

  const handleQuoteGenerated = (response: QuoteResponse) => {
    if (response.devis) {
      setResult(response.devis);
      setTokensUsed(response.tokens_used || null);
      setTimeout(() => {
        document.getElementById("quote-result")?.scrollIntoView({ behavior: "smooth" });
      }, 100);
    }
  };

  const handleReset = () => {
    setResult(null);
    setTokensUsed(null);
    setWithTva(true);
    setDocumentDate(new Date().toISOString().split("T")[0]);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <main className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center gap-3">
          <div className="bg-blue-700 text-white p-2 rounded-xl">
            <HardHat className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-lg font-black text-gray-900 leading-none">DevisBTP</h1>
            <p className="text-xs text-gray-500">Devis IA en 30 secondes</p>
          </div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 py-8 space-y-8">

        {!result ? (
          /* ── Formulaire ── */
          <>
            <div className="text-center space-y-4">
              <h2 className="text-2xl font-black text-gray-900">Décrivez votre chantier</h2>
              <p className="text-gray-500 text-sm">
                En texte libre — l&apos;IA génère le document complet avec les prix du marché
              </p>
              {/* Choix du type de document AVANT génération */}
              <div className="flex justify-center">
                <DocTypeToggle value={documentType} onChange={setDocumentType} size="md" />
              </div>
            </div>
            <QuoteForm onQuoteGenerated={handleQuoteGenerated} />
          </>
        ) : (
          /* ── Résultat ── */
          <div id="quote-result" className="space-y-4">
            <div className="flex items-start justify-between flex-wrap gap-3">
              <div>
                <h2 className="text-xl font-bold text-gray-900">✅ Document généré</h2>
                {tokensUsed && (
                  <p className="text-xs text-gray-400">{tokensUsed.toLocaleString()} tokens utilisés</p>
                )}
              </div>

              <div className="flex gap-2 flex-wrap items-center">
                {/* Type de document */}
                <DocTypeToggle value={documentType} onChange={setDocumentType} size="sm" />

                {/* Date du document */}
                <label className="flex items-center gap-1.5 border border-gray-300 rounded-xl px-3 py-2 bg-white text-sm text-gray-600 cursor-pointer hover:border-blue-400 transition-colors">
                  <Calendar className="w-4 h-4 text-gray-400" />
                  <input
                    type="date"
                    value={documentDate}
                    onChange={(e) => setDocumentDate(e.target.value)}
                    className="outline-none bg-transparent text-sm text-gray-700 cursor-pointer"
                  />
                </label>

                {/* Toggle TVA */}
                <div className="flex items-center bg-gray-100 rounded-xl p-1">
                  <button
                    onClick={() => setWithTva(true)}
                    className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-semibold transition-all ${
                      withTva ? "bg-white shadow text-blue-700" : "text-gray-500 hover:text-gray-700"
                    }`}
                  >
                    <Percent className="w-4 h-4" />
                    Avec TVA
                  </button>
                  <button
                    onClick={() => setWithTva(false)}
                    className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-semibold transition-all ${
                      !withTva ? "bg-white shadow text-orange-600" : "text-gray-500 hover:text-gray-700"
                    }`}
                  >
                    Sans TVA
                  </button>
                </div>

                <PdfExportButton
                  devis={result}
                  documentType={documentType}
                  withTva={withTva}
                  documentDate={documentDate}
                />
                <WordExportButton
                  devis={result}
                  documentType={documentType}
                  withTva={withTva}
                  documentDate={documentDate}
                />

                <button
                  onClick={handleReset}
                  className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 border border-gray-300 rounded-xl px-4 py-2.5 transition-colors hover:bg-gray-50"
                >
                  <RefreshCw className="w-4 h-4" />
                  Nouveau
                </button>
              </div>
            </div>

            <QuotePreview
              devis={result}
              documentType={documentType}
              withTva={withTva}
              documentDate={documentDate}
              onUpdate={(updated) => setResult(updated)}
            />
          </div>
        )}
      </div>
    </main>
  );
}
