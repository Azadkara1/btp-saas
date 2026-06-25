"use client";
import { useState, useEffect } from "react";
import { HardHat, RefreshCw, FileText, Receipt, Percent, Calendar } from "lucide-react";
import QuoteForm from "@/components/QuoteForm";
import QuotePreview from "@/components/QuotePreview";
import PdfExportButton from "@/components/PdfExportButton";
import WordExportButton from "@/components/WordExportButton";
import ModelPicker from "@/components/ModelPicker";
import { QuoteResponse, Devis } from "@/lib/types";
import ImportButton from "@/components/ImportButton";
import ImportReview from "@/components/ImportReview";

type DocumentType = "devis" | "facture";

function sanitizeFilename(s: string): string {
  return s.replace(/[\\/:*?"<>|]/g, "").replace(/\s+/g, "_").slice(0, 80).trim() || "document";
}

function buildDefaultFilename(devis: Devis, documentType: DocumentType): string {
  const prefix = documentType === "facture" ? "Facture" : "Devis";
  const num    = devis.numero_document || "";
  const client = devis.client?.nom || "";
  return sanitizeFilename([prefix, num, client].filter(Boolean).join("_"));
}

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
  const [filename, setFilename]           = useState<string>("");
  const [filenameCustomized, setFilenameCustomized] = useState(false);
  const [importedResponse, setImportedResponse]     = useState<QuoteResponse | null>(null);
  const [importArtisanChoice, setImportArtisanChoice] = useState<"keep" | "replace">("keep");

  // Recalcule le nom de fichier si non personnalisé (numero_document ou client peut avoir changé)
  useEffect(() => {
    if (result && !filenameCustomized) {
      setFilename(buildDefaultFilename(result, documentType));
    }
  }, [result, documentType, filenameCustomized]);

  const handleQuoteGenerated = (response: QuoteResponse) => {
    if (response.devis) {
      setFilenameCustomized(false);
      setResult(response.devis);
      setTokensUsed(response.tokens_used || null);
      setTimeout(() => {
        document.getElementById("quote-result")?.scrollIntoView({ behavior: "smooth" });
      }, 100);
    }
  };

  const handleImported = (response: QuoteResponse) => {
    if (response.devis) {
      setFilenameCustomized(false);
      setImportArtisanChoice("keep");
      // Applique le type et la date du document importé
      const meta = response.import_meta;
      if (meta?.document_type === "facture" || meta?.document_type === "devis") {
        setDocumentType(meta.document_type);
      }
      if (meta?.date_document_original) {
        setDocumentDate(meta.date_document_original);
      }
      // Affiche ImportReview — pas encore QuotePreview
      setImportedResponse(response);
    }
  };

  const handleConfirmImport = () => {
    if (!importedResponse?.devis) return;
    let finalDevis = importedResponse.devis;
    // "replace" : merge l'émetteur extrait sur l'artisan (zéro appel réseau)
    if (importArtisanChoice === "replace" && importedResponse.import_meta?.emetteur) {
      const e = importedResponse.import_meta.emetteur;
      finalDevis = {
        ...finalDevis,
        artisan: {
          ...finalDevis.artisan,
          nom:         e.nom         ?? finalDevis.artisan.nom,
          siret:       e.siret       ?? finalDevis.artisan.siret,
          adresse:     e.adresse     ?? finalDevis.artisan.adresse,
          code_postal: e.code_postal ?? finalDevis.artisan.code_postal,
          ville:       e.ville       ?? finalDevis.artisan.ville,
          telephone:   e.telephone   ?? finalDevis.artisan.telephone,
          email:       e.email       ?? finalDevis.artisan.email,
          site_web:    e.site_web    ?? finalDevis.artisan.site_web,
          iban:        e.iban        ?? finalDevis.artisan.iban,
          bic:         e.bic        ?? finalDevis.artisan.bic,
        },
      };
    }
    setResult(finalDevis);
    setImportedResponse(null);
    setTokensUsed(null);
    setTimeout(() => {
      document.getElementById("quote-result")?.scrollIntoView({ behavior: "smooth" });
    }, 100);
  };

  const handleReset = () => {
    setResult(null);
    setImportedResponse(null);
    setImportArtisanChoice("keep");
    setTokensUsed(null);
    setWithTva(true);
    setDocumentDate(new Date().toISOString().split("T")[0]);
    setFilename("");
    setFilenameCustomized(false);
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

        {result ? (
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

                {/* Nom du fichier partagé PDF/Word */}
                <label className="flex items-center gap-1.5 rounded-xl px-3 py-2 bg-white min-w-0"
                  style={{ border: "0.5px solid rgba(20,83,45,0.15)", color: "#5A635D" }}
                  title="Nom du fichier téléchargé (sans extension)">
                  <FileText className="w-4 h-4 shrink-0" style={{ color: "#7C857F" }} />
                  <input
                    type="text"
                    value={filename}
                    onChange={e => { setFilename(e.target.value); setFilenameCustomized(true); }}
                    placeholder="Nom du fichier"
                    className="outline-none bg-transparent text-sm min-w-0 w-32"
                    style={{ color: "#18211C" }}
                  />
                  <span className="text-xs shrink-0" style={{ color: "#7C857F" }}>.pdf / .docx</span>
                </label>
                <PdfExportButton devis={result} documentType={documentType} withTva={withTva} documentDate={documentDate} filename={filename || undefined} />
                <WordExportButton devis={result} documentType={documentType} withTva={withTva} documentDate={documentDate} filename={filename || undefined} />

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
        ) : importedResponse ? (
          <ImportReview
            response={importedResponse}
            artisanChoice={importArtisanChoice}
            onArtisanChoice={setImportArtisanChoice}
            onConfirm={handleConfirmImport}
            onCancel={() => { setImportedResponse(null); setImportArtisanChoice("keep"); }}
            documentType={documentType}
            documentDate={documentDate}
          />
        ) : (
          <>
            <div className="text-center space-y-5">
              <h2 className="text-2xl font-black" style={{ color: "#18211C" }}>Décrivez votre chantier</h2>
              <p className="text-sm" style={{ color: "#5A635D" }}>
                En texte libre — le document se construit avec les prix du marché
              </p>
              <div className="flex justify-center">
                <DocTypeToggle value={documentType} onChange={setDocumentType} size="md" />
              </div>
              <div>
                <p className="text-xs font-semibold mb-3" style={{ color: "#5A635D" }}>Choisissez le style du document</p>
                <div className="flex justify-center">
                  <ModelPicker value={modele} onChange={setModele} />
                </div>
              </div>
            </div>
            <div className="flex flex-col items-center gap-3">
              <ImportButton modele={modele} onImported={handleImported} />
              <div className="flex items-center gap-3 w-full max-w-sm">
                <div className="flex-1 h-px" style={{ backgroundColor: "rgba(20,83,45,0.12)" }} />
                <span className="text-xs font-semibold" style={{ color: "#7C857F" }}>ou décrivez votre chantier</span>
                <div className="flex-1 h-px" style={{ backgroundColor: "rgba(20,83,45,0.12)" }} />
              </div>
            </div>
            <QuoteForm onQuoteGenerated={handleQuoteGenerated} modele={modele} docType={documentType} />
          </>
        )}
      </div>
    </main>
  );
}
