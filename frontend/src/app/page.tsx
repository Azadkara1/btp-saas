"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { HardHat, RefreshCw, FileText, Receipt, Percent, Calendar, LogOut, History, Send, CheckCircle } from "lucide-react";
import QuoteForm from "@/components/QuoteForm";
import QuotePreview from "@/components/QuotePreview";
import PdfExportButton from "@/components/PdfExportButton";
import WordExportButton from "@/components/WordExportButton";
import ModelPicker from "@/components/ModelPicker";
import { QuoteResponse, Devis, DocumentCreate } from "@/lib/types";
import ImportButton from "@/components/ImportButton";
import ImportReview from "@/components/ImportReview";
import HistoriqueView from "@/components/HistoriqueView";
import { createClient } from "@/lib/supabase-client";
import { saveDocument, updateDocumentStatus } from "@/lib/api";

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
  const router = useRouter();
  const [userEmail, setUserEmail] = useState<string | null>(null);

  useEffect(() => {
    createClient().auth.getUser().then(({ data }) => {
      setUserEmail(data.user?.email ?? null);
    });
  }, []);

  const handleLogout = async () => {
    await createClient().auth.signOut();
    router.push("/login");
    router.refresh();
  };

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
  const [activeView, setActiveView]                 = useState<"form" | "historique">("form");
  const [savedDocumentId, setSavedDocumentId]       = useState<string | null>(null);
  const [savedDocumentStatut, setSavedDocumentStatut] = useState<string>("brouillon");
  const [saveFeedback, setSaveFeedback]             = useState<"saving" | "saved" | "error" | null>(null);

  // Recalcule le nom de fichier si non personnalisé (numero_document ou client peut avoir changé)
  useEffect(() => {
    if (result && !filenameCustomized) {
      setFilename(buildDefaultFilename(result, documentType));
    }
  }, [result, documentType, filenameCustomized]);

  const doAutoSave = async (devis: Devis, docType: DocumentType, date: string) => {
    setSaveFeedback("saving");
    try {
      const payload: DocumentCreate = {
        type_doc: docType,
        date_document: date,
        devis_payload: devis,
        total_ttc: devis.totaux.total_ttc,
        client_nom: devis.client.nom ?? null,
        client_adresse: devis.client.adresse ?? null,
        client_code_postal: devis.client.code_postal ?? null,
        client_ville: devis.client.ville ?? null,
      };
      const created = await saveDocument(payload);
      setSavedDocumentId(created.id);
      setSavedDocumentStatut("brouillon");
      setSaveFeedback("saved");
      setTimeout(() => setSaveFeedback(null), 3000);
    } catch {
      setSaveFeedback("error");
      setTimeout(() => setSaveFeedback(null), 3000);
    }
  };

  const handleQuoteGenerated = (response: QuoteResponse) => {
    if (response.devis) {
      setFilenameCustomized(false);
      setSavedDocumentId(null);
      setSavedDocumentStatut("brouillon");
      setResult(response.devis);
      setTokensUsed(response.tokens_used || null);
      doAutoSave(response.devis, documentType, documentDate);
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
    setSavedDocumentId(null);
    setSavedDocumentStatut("brouillon");
    doAutoSave(finalDevis, documentType, documentDate);
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
    setSavedDocumentId(null);
    setSavedDocumentStatut("brouillon");
    setSaveFeedback(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleMarkEnvoye = async () => {
    if (!savedDocumentId) return;
    try {
      const r = await updateDocumentStatus(savedDocumentId, "envoyé");
      setSavedDocumentStatut("envoyé");
      if (r.numero && result) {
        setResult({ ...result, numero_document: r.numero });
      }
    } catch { /* feedback silencieux — l'artisan peut réessayer */ }
  };

  const handleOpenFromHistory = (devis: Devis, docId: string, statut: string, typeDoc: string) => {
    setSavedDocumentId(docId);
    setSavedDocumentStatut(statut);
    setDocumentType(typeDoc === "facture" ? "facture" : "devis");
    setResult(devis);
    setFilenameCustomized(false);
    setActiveView("form");
    setTimeout(() => {
      document.getElementById("quote-result")?.scrollIntoView({ behavior: "smooth" });
    }, 100);
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
          <div className="ml-auto flex items-center gap-3">
            {userEmail && (
              <span className="text-xs hidden sm:block" style={{ color: "#7C857F" }}>
                {userEmail}
              </span>
            )}
            <button
              onClick={() => setActiveView(v => v === "historique" ? "form" : "historique")}
              className="flex items-center gap-1.5 text-xs rounded-xl px-3 py-2 transition-colors"
              style={activeView === "historique"
                ? { backgroundColor: "#14532D", color: "#FFFFFF" }
                : { border: "0.5px solid rgba(20,83,45,0.15)", color: "#5A635D", backgroundColor: "white" }}>
              <History className="w-3.5 h-3.5" /> Historique
            </button>
            <button onClick={handleLogout}
              className="flex items-center gap-1.5 text-xs rounded-xl px-3 py-2 bg-white transition-colors"
              style={{ border: "0.5px solid rgba(20,83,45,0.15)", color: "#5A635D" }}
              title="Se déconnecter">
              <LogOut className="w-3.5 h-3.5" /> Déconnexion
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 py-8 space-y-8">

        {activeView === "historique" ? (
          <HistoriqueView onOpen={handleOpenFromHistory} />
        ) : result ? (
          <div id="quote-result" className="space-y-4">
            <div className="flex items-start justify-between flex-wrap gap-3">
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <h2 className="text-xl font-bold" style={{ color: "#18211C" }}>Document généré</h2>
                  {saveFeedback === "saving" && (
                    <span className="text-xs px-2 py-0.5 rounded-full animate-pulse" style={{ backgroundColor: "#E3EDE6", color: "#14532D" }}>
                      Enregistrement…
                    </span>
                  )}
                  {saveFeedback === "saved" && (
                    <span className="text-xs px-2 py-0.5 rounded-full flex items-center gap-1" style={{ backgroundColor: "#D1FAE5", color: "#14532D" }}>
                      <CheckCircle className="w-3 h-3" /> Brouillon enregistré
                    </span>
                  )}
                  {saveFeedback === "error" && (
                    <span className="text-xs px-2 py-0.5 rounded-full" style={{ backgroundColor: "#FEF2F2", color: "#B91C1C" }}>
                      Échec sauvegarde
                    </span>
                  )}
                </div>
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
                {/* Badge statut */}
                {savedDocumentId && (() => {
                  const sc: Record<string, { label: string; color: string; bg: string }> = {
                    brouillon: { label: "Brouillon", color: "#6B7280", bg: "#F3F4F6" },
                    "envoyé":  { label: "Envoyé",    color: "#1D4ED8", bg: "#DBEAFE" },
                    "signé":   { label: "Signé",     color: "#7C3AED", bg: "#EDE9FE" },
                    "payé":    { label: "Payé",      color: "#14532D", bg: "#D1FAE5" },
                  };
                  const s = sc[savedDocumentStatut] ?? { label: savedDocumentStatut, color: "#6B7280", bg: "#F3F4F6" };
                  return (
                    <span className="text-xs px-2.5 py-1.5 rounded-full font-medium"
                      style={{ color: s.color, backgroundColor: s.bg }}>
                      {s.label}
                    </span>
                  );
                })()}
                {/* Marquer envoyé */}
                {savedDocumentId && savedDocumentStatut === "brouillon" && (
                  <button onClick={handleMarkEnvoye}
                    className="flex items-center gap-1.5 text-sm rounded-xl px-3 py-2 font-medium transition-colors"
                    style={{ backgroundColor: "#1D4ED8", color: "white" }}>
                    <Send className="w-3.5 h-3.5" /> Marquer envoyé
                  </button>
                )}
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
            <QuoteForm onQuoteGenerated={handleQuoteGenerated} modele={modele} docType={documentType} onModeleLoaded={setModele} />
          </>
        )}
      </div>
    </main>
  );
}
