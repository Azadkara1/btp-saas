"use client";
import { useState } from "react";
import { HardHat, RefreshCw, FileText, Receipt, Percent, Calendar } from "lucide-react";
import QuoteForm from "@/components/QuoteForm";
import QuotePreview from "@/components/QuotePreview";
import PdfExportButton from "@/components/PdfExportButton";
import WordExportButton from "@/components/WordExportButton";
import ModelPicker from "@/components/ModelPicker";
import { QuoteResponse, Devis } from "@/lib/types";

type DocumentType = "devis" | "facture";

function DocTypeToggle({
  value, onChange, size = "md",
}: { value: DocumentType; onChange: (v: DocumentType) => void; size?: "sm" | "md" }) {
  const cls = size === "md"
    ? "flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition-all"
    : "flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-semibold transition-all";
  return (
    <div className="flex items-center rounded-2xl p-1.5 gap-1" style={{ backgroundColor: "#E3EDE6" }}>
      <button onClick={() => onChange("devis")}
        className={cls}
        style={value === "devis"
          ? { backgroundColor: "#FFFFFF", color: "#14532D", boxShadow: "0 1px 3px rgba(0,0,0,0.08)" }
          : { color: "#5A635D" }}>
        <FileText className="w-4 h-4" /> Devis
      </button>
      <button onClick={() => onChange("facture")}
        className={cls}
        style={value === "facture"
          ? { backgroundColor: "#FFFFFF", color: "#14532D", boxShadow: "0 1px 3px rgba(0,0,0,0.08)" }
          : { color: "#5A635D" }}>
        <Receipt className="w-4 h-4" /> Facture
      </button>
    </div>
  );
}

export default function HomePage() {
  const [result, setResult]             = useState<Devis | null>(null);
  const [tokensUsed, setTokensUsed]     = useState<number | null>(null);
  const [documentType, setDocumentType] = useState<DocumentType>("devis");
  const [withTva, setWithTva]           = useState(true);
  const [documentDate, setDocumentDate] = useState<string>(
    () => new Date().toISOString().split("T")[0]
  );
  const [modele, setModele] = useState<string>("moderne");

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
    <main className="min-h-screen" style={{ backgroundColor: "#FAFAF7" }}>
      {/* Header */}
      <header className="bg-white sticky top-0 z-10" style={{ borderBottom: "0.5px solid rgba(20,83,45,0.12)" }}>
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center gap-3">
          <div className="text-white p-2 rounded-xl" style={{ backgroundColor: "#14532D" }}>
            <HardHat className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-lg font-black leading-none" style={{ color: "#18211C" }}>DevisBTP</h1>
            <p className="text-xs" style={{ color: "#7C857F" }}>Devis professionnel en quelques secondes</p>
          </div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 py-8 space-y-8">

        {!result ? (
          <>
            <div className="text-center space-y-5">
              <h2 className="text-2xl font-black" style={{ color: "#18211C" }}>Décrivez votre chantier</h2>
              <p className="text-sm" style={{ color: "#5A635D" }}>
                En texte libre — le document se construit avec les prix du marché
              </p>
              {/* Toggle Devis/Facture */}
              <div className="flex justify-center">
                <DocTypeToggle value={documentType} onChange={setDocumentType} size="md" />
              </div>
              {/* Sélecteur de modèle — vignettes */}
              <div>
                <p className="text-xs font-semibold mb-3" style={{ color: "#5A635D" }}>Choisissez le style du document</p>
                <div className="flex justify-center">
                  <ModelPicker value={modele} onChange={setModele} />
                </div>
              </div>
            </div>
            <QuoteForm onQuoteGenerated={handleQuoteGenerated} modele={modele} docType={documentType} />
          </>
        ) : (
          <div id="quote-result" className="space-y-4">
            <div className="flex items-start justify-between flex-wrap gap-3">
              <div>
                <h2 className="text-xl font-bold" style={{ color: "#18211C" }}>Document généré</h2>
                {tokensUsed && (
                  <p className="text-xs" style={{ color: "#7C857F" }}>{tokensUsed.toLocaleString()} tokens utilisés</p>
                )}
              </div>

              <div className="flex gap-2 flex-wrap items-center">
                <DocTypeToggle value={documentType} onChange={setDocumentType} size="sm" />

                {/* Date du document */}
                <label className="flex items-center gap-1.5 rounded-xl px-3 py-2 bg-white text-sm cursor-pointer"
                  style={{ border: "0.5px solid rgba(20,83,45,0.15)", color: "#5A635D" }}>
                  <Calendar className="w-4 h-4" style={{ color: "#7C857F" }} />
                  <input type="date" value={documentDate} onChange={e => setDocumentDate(e.target.value)}
                    className="outline-none bg-transparent text-sm cursor-pointer" style={{ color: "#18211C" }} />
                </label>

                {/* Toggle TVA */}
                <div className="flex items-center rounded-xl p-1" style={{ backgroundColor: "#E3EDE6" }}>
                  <button onClick={() => setWithTva(true)}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-semibold transition-all"
                    style={withTva
                      ? { backgroundColor: "#FFFFFF", color: "#14532D", boxShadow: "0 1px 2px rgba(0,0,0,0.08)" }
                      : { color: "#5A635D" }}>
                    <Percent className="w-4 h-4" /> Avec TVA
                  </button>
                  <button onClick={() => setWithTva(false)}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-semibold transition-all"
                    style={!withTva
                      ? { backgroundColor: "#FFFFFF", color: "#B45309", boxShadow: "0 1px 2px rgba(0,0,0,0.08)" }
                      : { color: "#5A635D" }}>
                    Sans TVA
                  </button>
                </div>

                <PdfExportButton devis={result} documentType={documentType} withTva={withTva} documentDate={documentDate} />
                <WordExportButton devis={result} documentType={documentType} withTva={withTva} documentDate={documentDate} />

                <button onClick={handleReset}
                  className="flex items-center gap-2 text-sm rounded-xl px-4 py-2.5 transition-colors bg-white"
                  style={{ border: "0.5px solid rgba(20,83,45,0.15)", color: "#5A635D" }}>
                  <RefreshCw className="w-4 h-4" /> Nouveau
                </button>
              </div>
            </div>

            <QuotePreview
              devis={result}
              documentType={documentType}
              withTva={withTva}
              documentDate={documentDate}
              onUpdate={updated => setResult(updated)}
            />
          </div>
        )}
      </div>
    </main>
  );
}
