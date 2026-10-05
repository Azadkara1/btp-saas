"use client";
import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { HardHat, RefreshCw, FileText, Receipt, Percent, Calendar, LogOut, History, Send, CheckCircle, XCircle, Clock, Copy, ArrowRightLeft, Users, LayoutDashboard, Link2, Wallet } from "lucide-react";
import QuoteForm from "@/components/QuoteForm";
import QuotePreview from "@/components/QuotePreview";
import PdfExportButton from "@/components/PdfExportButton";
import WordExportButton from "@/components/WordExportButton";
import ModelPicker from "@/components/ModelPicker";
import { QuoteResponse, Devis, DocumentCreate, StatutDocument, SendEmailResponse, DocumentDetail } from "@/lib/types";
import ImportButton from "@/components/ImportButton";
import ImportReview from "@/components/ImportReview";
import HistoriqueView from "@/components/HistoriqueView";
import ClientsView from "@/components/ClientsView";
import DashboardView from "@/components/DashboardView";
import CalendrierView from "@/components/CalendrierView";
import SendEmailModal from "@/components/SendEmailModal";
import { createClient } from "@/lib/supabase-client";
import { saveDocument, updateDocument, updateDocumentStatus, convertToFacture, duplicateDocument, getSignatureLink, createAcompte, getProfile, getNumerotationStatus } from "@/lib/api";
import { formatNumeroPreview } from "@/components/QuoteForm";

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

// Badges de statut — cohérents avec HistoriqueView.tsx
const STATUT_BADGE: Record<StatutDocument, { label: string; color: string; bg: string }> = {
  brouillon: { label: "Brouillon", color: "#6B7280", bg: "#F3F4F6" },
  "envoyé":  { label: "Envoyé",    color: "#1D4ED8", bg: "#DBEAFE" },
  "signé":   { label: "Signé",     color: "#7C3AED", bg: "#EDE9FE" },
  "payé":    { label: "Payé",      color: "#14532D", bg: "#D1FAE5" },
  "refusé":  { label: "Refusé",    color: "#B91C1C", bg: "#FEE2E2" },
  "expiré":  { label: "Expiré",    color: "#4B5563", bg: "#E5E7EB" },
};

// Transitions de statut proposées dans la toolbar, selon le statut courant
const STATUT_TRANSITIONS: Record<StatutDocument, { statut: StatutDocument; label: string; icon: typeof Send; color: string }[]> = {
  brouillon: [
    { statut: "envoyé", label: "Marquer envoyé", icon: Send, color: "#1D4ED8" },
  ],
  "envoyé": [
    { statut: "signé",  label: "Marquer signé",  icon: CheckCircle, color: "#7C3AED" },
    { statut: "refusé", label: "Marquer refusé", icon: XCircle,     color: "#B91C1C" },
    { statut: "expiré", label: "Marquer expiré", icon: Clock,       color: "#4B5563" },
  ],
  "signé": [
    { statut: "payé", label: "Marquer payé", icon: CheckCircle, color: "#14532D" },
  ],
  "payé": [],
  "refusé": [],
  "expiré": [],
};

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
  const [activeView, setActiveView]                 = useState<"form" | "historique" | "clients" | "dashboard" | "calendrier">("form");
  const [savedDocumentId, setSavedDocumentId]       = useState<string | null>(null);
  const [savedDocumentStatut, setSavedDocumentStatut] = useState<StatutDocument>("brouillon");
  // Signature capturée (Batch 12 T3) — métadonnée du document, pas du devis
  // lui-même (jamais dans `result`/`Devis`). Alimente PdfExportButton/WordExportButton.
  const [signatureInfo, setSignatureInfo] = useState<{ nom?: string | null; imageBase64?: string | null; date?: string | null } | null>(null);
  // Batch 15 : suit si numero_document est encore le numéro provisoire
  // auto-rempli par nous (jamais modifié à la main) — seul cas où la
  // bascule Devis/Facture est autorisée à le recalculer automatiquement.
  const [numeroDocumentAuto, setNumeroDocumentAuto] = useState(false);
  // Batch 16 : identité du document affiché — incrémentée à chaque fois
  // qu'un NOUVEAU document remplace celui affiché dans QuotePreview
  // (génération, import, ouverture depuis l'historique, conversion,
  // duplication, facture d'acompte — ces 3 derniers passent tous par
  // handleOpenFromHistory). Utilisée comme `key` sur <QuotePreview> pour
  // forcer un remount complet : sans ça, QuotePreview reste monté et ses
  // ~12 états locaux (lignes, remise, acompte, mentions, client...)
  // restent figés sur l'ANCIEN document — un artisan pouvait exporter une
  // facture d'acompte avec les lignes/totaux du devis d'origine.
  const [documentInstanceKey, setDocumentInstanceKey] = useState(0);
  const [saveFeedback, setSaveFeedback]             = useState<"saving" | "saved" | "error" | null>(null);
  const [markEnvoyeError, setMarkEnvoyeError]       = useState<string | null>(null);
  const [actionLoading, setActionLoading]           = useState<"convert" | "duplicate" | "signature-link" | "acompte" | "statut" | null>(null);
  const [linkCopied, setLinkCopied]                 = useState(false);
  const [showSendModal, setShowSendModal]           = useState(false);
  const [sendSuccess, setSendSuccess]               = useState(false);

  // Recalcule le nom de fichier si non personnalisé (numero_document ou client peut avoir changé)
  useEffect(() => {
    if (result && !filenameCustomized) {
      setFilename(buildDefaultFilename(result, documentType));
    }
  }, [result, documentType, filenameCustomized]);

  const buildDocumentPayload = (devis: Devis, docType: DocumentType, date: string): DocumentCreate => ({
    type_doc: docType,
    titre: buildDefaultFilename(devis, docType),
    numero_document: devis.numero_document ?? null,
    date_document: date,
    devis_payload: devis,
    total_ttc: devis.totaux.total_ttc,
    client_nom: devis.client.nom ?? null,
    client_adresse: devis.client.adresse ?? null,
    client_code_postal: devis.client.code_postal ?? null,
    client_ville: devis.client.ville ?? null,
  });

  const doAutoSave = async (devis: Devis, docType: DocumentType, date: string) => {
    setSaveFeedback("saving");
    try {
      const created = await saveDocument(buildDocumentPayload(devis, docType, date));
      setSavedDocumentId(created.id);
      setSavedDocumentStatut("brouillon");
      setSaveFeedback("saved");
      setTimeout(() => setSaveFeedback(null), 3000);
    } catch {
      setSaveFeedback("error");
      setTimeout(() => setSaveFeedback(null), 3000);
    }
  };

  // Batch 16 : persiste les modifications faites APRÈS la génération initiale
  // (édition de lignes, remise, mentions, client...). Avant ça, seul l'état
  // généré au départ était jamais sauvegardé — un devis modifié puis rouvert
  // depuis l'historique perdait silencieusement toutes ses modifications.
  // Débounce : évite un appel réseau à chaque frappe. La modification en
  // attente est gardée dans pendingUpdateRef (pas seulement dans le timer)
  // pour pouvoir être déclenchée immédiatement via flushUpdateSave() —
  // sinon quitter l'aperçu (historique/clients) juste après une frappe
  // pouvait rouvrir le document avant l'écoulement des 900ms et afficher
  // la version non modifiée.
  const updateSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pendingUpdateRef = useRef<{ id: string; devis: Devis; docType: DocumentType; date: string } | null>(null);

  const persistUpdate = async (id: string, devis: Devis, docType: DocumentType, date: string) => {
    setSaveFeedback("saving");
    try {
      await updateDocument(id, buildDocumentPayload(devis, docType, date));
      setSaveFeedback("saved");
      setTimeout(() => setSaveFeedback(null), 3000);
    } catch {
      setSaveFeedback("error");
      setTimeout(() => setSaveFeedback(null), 3000);
    } finally {
      pendingUpdateRef.current = null;
    }
  };

  const doUpdateSave = (id: string, devis: Devis, docType: DocumentType, date: string) => {
    if (updateSaveTimer.current) clearTimeout(updateSaveTimer.current);
    pendingUpdateRef.current = { id, devis, docType, date };
    updateSaveTimer.current = setTimeout(() => {
      updateSaveTimer.current = null;
      const pending = pendingUpdateRef.current;
      if (pending) persistUpdate(pending.id, pending.devis, pending.docType, pending.date);
    }, 900);
  };

  // Déclenche immédiatement une sauvegarde en attente (sans attendre le
  // débounce) — appelé avant toute navigation qui quitte l'aperçu.
  const flushUpdateSave = () => {
    if (updateSaveTimer.current) {
      clearTimeout(updateSaveTimer.current);
      updateSaveTimer.current = null;
    }
    const pending = pendingUpdateRef.current;
    if (pending) persistUpdate(pending.id, pending.devis, pending.docType, pending.date);
  };

  // Batch 14 : numéro provisoire dès la génération, calculé avec le même
  // mécanisme que l'aperçu en direct de Batch 13 T2 (lecture seule, jamais
  // d'incrément) — n'écrase jamais un numero_document déjà renseigné
  // (Claude, import, ou saisie manuelle). Best-effort : une erreur réseau
  // ne doit jamais bloquer la génération, juste laisser le champ vide.
  const computeProvisionalNumero = async (docType: DocumentType): Promise<string | null> => {
    try {
      const [profile, numerotationStatus] = await Promise.all([getProfile(), getNumerotationStatus()]);
      if (!profile) return null;
      const compteur = docType === "devis" ? numerotationStatus.devis_prochain_compteur : numerotationStatus.facture_prochain_compteur;
      const prefixe = docType === "devis" ? profile.devis_numero_prefixe : profile.facture_numero_prefixe;
      const inclureAnnee = docType === "devis" ? profile.devis_numero_inclure_annee : profile.facture_numero_inclure_annee;
      const padding = docType === "devis" ? profile.devis_numero_padding : profile.facture_numero_padding;
      return formatNumeroPreview(compteur, prefixe, inclureAnnee, padding);
    } catch {
      return null;
    }
  };

  const handleQuoteGenerated = async (response: QuoteResponse) => {
    if (response.devis) {
      setFilenameCustomized(false);
      setSavedDocumentId(null);
      setSavedDocumentStatut("brouillon");
      setSignatureInfo(null);
      let devis = response.devis;
      if (!devis.numero_document) {
        const provisoire = await computeProvisionalNumero(documentType);
        if (provisoire) devis = { ...devis, numero_document: provisoire };
        setNumeroDocumentAuto(!!provisoire);
      } else {
        setNumeroDocumentAuto(false);
      }
      setResult(devis);
      setDocumentInstanceKey(k => k + 1);
      setTokensUsed(response.tokens_used || null);
      doAutoSave(devis, documentType, documentDate);
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

  const handleConfirmImport = async () => {
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
    if (!finalDevis.numero_document) {
      const provisoire = await computeProvisionalNumero(documentType);
      if (provisoire) finalDevis = { ...finalDevis, numero_document: provisoire };
      setNumeroDocumentAuto(!!provisoire);
    } else {
      setNumeroDocumentAuto(false);
    }
    setResult(finalDevis);
    setDocumentInstanceKey(k => k + 1);
    setImportedResponse(null);
    setTokensUsed(null);
    setSavedDocumentId(null);
    setSavedDocumentStatut("brouillon");
    setSignatureInfo(null);
    doAutoSave(finalDevis, documentType, documentDate);
    setTimeout(() => {
      document.getElementById("quote-result")?.scrollIntoView({ behavior: "smooth" });
    }, 100);
  };

  // Batch 15 : bascule Devis ↔ Facture sur un document déjà généré — le
  // numéro provisoire doit suivre (préfixe DEV-/FAC- + compteur du bon
  // type), mais UNIQUEMENT s'il n'a jamais été retouché à la main.
  const handleDocumentTypeChange = async (newType: DocumentType) => {
    setDocumentType(newType);
    if (numeroDocumentAuto && result) {
      const provisoire = await computeProvisionalNumero(newType);
      if (provisoire) {
        const updated = { ...result, numero_document: provisoire };
        setResult(updated);
        if (savedDocumentId && savedDocumentStatut === "brouillon") {
          doUpdateSave(savedDocumentId, updated, newType, documentDate);
        }
      }
    }
  };

  // Détecte une édition manuelle du numéro dans QuotePreview (le seul champ
  // qu'on ne doit plus jamais recalculer automatiquement après ça).
  // Batch 16 : persiste aussi la modification (débounce) — c'est le chemin
  // par lequel TOUTE édition dans QuotePreview transite (lignes, remise,
  // mentions, client...), donc le seul endroit nécessaire pour corriger
  // "les modifications ne sont pas prises en compte au retour".
  const handleQuotePreviewUpdate = (updated: Devis) => {
    if (numeroDocumentAuto && result && updated.numero_document !== result.numero_document) {
      setNumeroDocumentAuto(false);
    }
    setResult(updated);
    if (savedDocumentId && savedDocumentStatut === "brouillon") {
      doUpdateSave(savedDocumentId, updated, documentType, documentDate);
    }
  };

  const handleReset = () => {
    flushUpdateSave();
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
    setSignatureInfo(null);
    setNumeroDocumentAuto(false);
    setSaveFeedback(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleChangeStatut = async (nextStatut: StatutDocument) => {
    if (!savedDocumentId || actionLoading !== null) return;
    setMarkEnvoyeError(null);
    setActionLoading("statut");
    // Une sauvegarde de contenu en attente (debounce) viserait un document
    // qui ne sera plus un brouillon après cette transition → 409 inutile.
    if (updateSaveTimer.current) clearTimeout(updateSaveTimer.current);
    try {
      const r = await updateDocumentStatus(savedDocumentId, nextStatut);
      setSavedDocumentStatut(nextStatut);
      if (r.numero && result) {
        setResult({ ...result, numero_document: r.numero });
        setNumeroDocumentAuto(false); // numéro légal définitif attribué — plus jamais recalculé
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      console.error(`[STATUT → ${nextStatut}] échec — savedDocumentId:`, savedDocumentId, "erreur:", msg);
      setMarkEnvoyeError(msg);
      setTimeout(() => setMarkEnvoyeError(null), 8000);
    } finally {
      setActionLoading(null);
    }
  };

  const handleOpenFromHistory = (detail: DocumentDetail) => {
    setSavedDocumentId(detail.id);
    setSavedDocumentStatut(detail.statut);
    setDocumentType(detail.type_doc === "facture" ? "facture" : "devis");
    setNumeroDocumentAuto(false); // numéro déjà attribué/sauvegardé — jamais recalculé automatiquement
    setResult(detail.devis_payload);
    setDocumentInstanceKey(k => k + 1);
    setSignatureInfo(
      detail.signature_nom_signataire
        ? { nom: detail.signature_nom_signataire, imageBase64: detail.signature_image_base64, date: detail.date_signature }
        : null
    );
    setFilenameCustomized(false);
    setActiveView("form");
    setTimeout(() => {
      document.getElementById("quote-result")?.scrollIntoView({ behavior: "smooth" });
    }, 100);
  };

  const handleConvertToFacture = async () => {
    if (!savedDocumentId) return;
    setActionLoading("convert");
    setMarkEnvoyeError(null);
    try {
      const created = await convertToFacture(savedDocumentId);
      handleOpenFromHistory(created);
    } catch (err) {
      setMarkEnvoyeError(err instanceof Error ? err.message : "Erreur lors de la conversion en facture");
      setTimeout(() => setMarkEnvoyeError(null), 8000);
    } finally {
      setActionLoading(null);
    }
  };

  const handleCreateAcompte = async () => {
    if (!savedDocumentId) return;
    const saisie = window.prompt("Pourcentage d'acompte à facturer (ex : 30) :", "30");
    if (saisie === null) return;
    const pourcentage = parseFloat(saisie.replace(",", "."));
    if (!Number.isFinite(pourcentage) || pourcentage <= 0 || pourcentage > 100) {
      setMarkEnvoyeError("Pourcentage invalide (doit être entre 0 et 100).");
      setTimeout(() => setMarkEnvoyeError(null), 8000);
      return;
    }
    setActionLoading("acompte");
    setMarkEnvoyeError(null);
    try {
      const created = await createAcompte(savedDocumentId, pourcentage);
      handleOpenFromHistory(created);
    } catch (err) {
      setMarkEnvoyeError(err instanceof Error ? err.message : "Erreur lors de la création de la facture d'acompte");
      setTimeout(() => setMarkEnvoyeError(null), 8000);
    } finally {
      setActionLoading(null);
    }
  };

  const handleDuplicateDocument = async () => {
    if (!savedDocumentId) return;
    setActionLoading("duplicate");
    setMarkEnvoyeError(null);
    try {
      const created = await duplicateDocument(savedDocumentId);
      handleOpenFromHistory(created);
    } catch (err) {
      setMarkEnvoyeError(err instanceof Error ? err.message : "Erreur lors de la duplication");
      setTimeout(() => setMarkEnvoyeError(null), 8000);
    } finally {
      setActionLoading(null);
    }
  };

  const handleCopySignatureLink = async () => {
    if (!savedDocumentId) return;
    setActionLoading("signature-link");
    setMarkEnvoyeError(null);
    try {
      const { url } = await getSignatureLink(savedDocumentId);
      await navigator.clipboard.writeText(url);
      setLinkCopied(true);
      setTimeout(() => setLinkCopied(false), 5000);
    } catch (err) {
      setMarkEnvoyeError(err instanceof Error ? err.message : "Erreur lors de la génération du lien");
      setTimeout(() => setMarkEnvoyeError(null), 8000);
    } finally {
      setActionLoading(null);
    }
  };

  const handleEmailSent = (response: SendEmailResponse) => {
    setShowSendModal(false);
    setSavedDocumentStatut("envoyé");
    if (response.numero && result) {
      setResult({ ...result, numero_document: response.numero });
    }
    setSendSuccess(true);
    setTimeout(() => setSendSuccess(false), 5000);
  };

  return (
    <main className="min-h-screen" style={{ backgroundColor: "#FAFAF7" }}>
      {/* Header */}
      <header className="bg-white sticky top-0 z-10" style={{ borderBottom: "0.5px solid rgba(20,83,45,0.12)" }}>
        <div className="max-w-5xl mx-auto px-3 sm:px-4 py-3 sm:py-4 flex items-center gap-2 sm:gap-3">
          <button type="button" onClick={() => { handleReset(); setActiveView("form"); }}
            className="flex items-center gap-2 sm:gap-3 text-left shrink-0">
            <div className="text-white p-1.5 sm:p-2 rounded-xl shrink-0" style={{ backgroundColor: "#14532D" }}>
              <HardHat className="w-4 h-4 sm:w-5 sm:h-5" />
            </div>
            <div>
              <h1 className="text-base sm:text-lg font-black leading-none" style={{ color: "#18211C" }}>DevisBTP</h1>
              <p className="hidden sm:block text-xs" style={{ color: "#7C857F" }}>Devis professionnel en quelques secondes</p>
            </div>
          </button>
          <div className="ml-auto flex items-center gap-1 sm:gap-3 overflow-x-auto">
            {userEmail && (
              <span className="text-xs hidden md:block shrink-0" style={{ color: "#7C857F" }}>
                {userEmail}
              </span>
            )}
            <button
              onClick={() => { flushUpdateSave(); setActiveView(v => v === "historique" ? "form" : "historique"); }}
              title="Historique"
              className="flex items-center gap-1.5 text-xs rounded-xl px-2 sm:px-3 py-2 transition-colors shrink-0"
              style={activeView === "historique"
                ? { backgroundColor: "#14532D", color: "#FFFFFF" }
                : { border: "0.5px solid rgba(20,83,45,0.15)", color: "#5A635D", backgroundColor: "white" }}>
              <History className="w-3.5 h-3.5" /> <span className="hidden sm:inline">Historique</span>
            </button>
            <button
              onClick={() => { flushUpdateSave(); setActiveView(v => v === "clients" ? "form" : "clients"); }}
              title="Clients"
              className="flex items-center gap-1.5 text-xs rounded-xl px-2 sm:px-3 py-2 transition-colors shrink-0"
              style={activeView === "clients"
                ? { backgroundColor: "#14532D", color: "#FFFFFF" }
                : { border: "0.5px solid rgba(20,83,45,0.15)", color: "#5A635D", backgroundColor: "white" }}>
              <Users className="w-3.5 h-3.5" /> <span className="hidden sm:inline">Clients</span>
            </button>
            <button
              onClick={() => { flushUpdateSave(); setActiveView(v => v === "dashboard" ? "form" : "dashboard"); }}
              title="Dashboard"
              className="flex items-center gap-1.5 text-xs rounded-xl px-2 sm:px-3 py-2 transition-colors shrink-0"
              style={activeView === "dashboard"
                ? { backgroundColor: "#14532D", color: "#FFFFFF" }
                : { border: "0.5px solid rgba(20,83,45,0.15)", color: "#5A635D", backgroundColor: "white" }}>
              <LayoutDashboard className="w-3.5 h-3.5" /> <span className="hidden sm:inline">Dashboard</span>
            </button>
            <button
              onClick={() => { flushUpdateSave(); setActiveView(v => v === "calendrier" ? "form" : "calendrier"); }}
              title="Calendrier"
              className="flex items-center gap-1.5 text-xs rounded-xl px-2 sm:px-3 py-2 transition-colors shrink-0"
              style={activeView === "calendrier"
                ? { backgroundColor: "#14532D", color: "#FFFFFF" }
                : { border: "0.5px solid rgba(20,83,45,0.15)", color: "#5A635D", backgroundColor: "white" }}>
              <Calendar className="w-3.5 h-3.5" /> <span className="hidden sm:inline">Calendrier</span>
            </button>
            <button onClick={handleLogout}
              title="Se déconnecter"
              className="flex items-center gap-1.5 text-xs rounded-xl px-2 sm:px-3 py-2 bg-white transition-colors shrink-0"
              style={{ border: "0.5px solid rgba(20,83,45,0.15)", color: "#5A635D" }}>
              <LogOut className="w-3.5 h-3.5" /> <span className="hidden sm:inline">Déconnexion</span>
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 py-8 space-y-8">

        {activeView === "historique" ? (
          <HistoriqueView onOpen={handleOpenFromHistory} />
        ) : activeView === "clients" ? (
          <ClientsView onOpenDocument={handleOpenFromHistory} />
        ) : activeView === "dashboard" ? (
          <DashboardView />
        ) : activeView === "calendrier" ? (
          <CalendrierView />
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
                <DocTypeToggle value={documentType} onChange={handleDocumentTypeChange} size="sm" />

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
                  const s = STATUT_BADGE[savedDocumentStatut] ?? { label: savedDocumentStatut, color: "#6B7280", bg: "#F3F4F6" };
                  return (
                    <span className="text-xs px-2.5 py-1.5 rounded-full font-medium"
                      style={{ color: s.color, backgroundColor: s.bg }}>
                      {s.label}
                    </span>
                  );
                })()}
                {/* Boutons de transition de statut */}
                {savedDocumentId && (STATUT_TRANSITIONS[savedDocumentStatut] || []).map(t => (
                  <button key={t.statut} onClick={() => handleChangeStatut(t.statut)}
                    disabled={actionLoading !== null}
                    className="flex items-center gap-1.5 text-sm rounded-xl px-3 py-2 font-medium transition-colors disabled:opacity-50"
                    style={{ backgroundColor: t.color, color: "white" }}>
                    <t.icon className="w-3.5 h-3.5" /> {actionLoading === "statut" ? "…" : t.label}
                  </button>
                ))}
                {/* Envoyer par email */}
                {savedDocumentId && (
                  <button onClick={() => setShowSendModal(true)}
                    className="flex items-center gap-1.5 text-sm rounded-xl px-3 py-2 font-medium transition-colors"
                    style={{ backgroundColor: "#1D4ED8", color: "white" }}>
                    <Send className="w-3.5 h-3.5" /> Envoyer par email
                  </button>
                )}
                {/* Copier le lien de signature — devis envoyé uniquement */}
                {savedDocumentId && documentType === "devis" && savedDocumentStatut === "envoyé" && (
                  <button onClick={handleCopySignatureLink} disabled={actionLoading !== null}
                    className="flex items-center gap-1.5 text-sm rounded-xl px-3 py-2 font-medium transition-colors disabled:opacity-50"
                    style={{ backgroundColor: "#7C3AED", color: "white" }}>
                    <Link2 className="w-3.5 h-3.5" />
                    {actionLoading === "signature-link" ? "Génération…" : linkCopied ? "Lien copié !" : "Copier le lien de signature"}
                  </button>
                )}
                {/* Dupliquer */}
                {savedDocumentId && (
                  <button onClick={handleDuplicateDocument} disabled={actionLoading !== null}
                    className="flex items-center gap-1.5 text-sm rounded-xl px-3 py-2 font-medium transition-colors bg-white disabled:opacity-50"
                    style={{ border: "0.5px solid rgba(20,83,45,0.15)", color: "#5A635D" }}>
                    <Copy className="w-3.5 h-3.5" /> {actionLoading === "duplicate" ? "Duplication…" : "Dupliquer"}
                  </button>
                )}
                {/* Convertir en facture — devis signé uniquement */}
                {savedDocumentId && documentType === "devis" && savedDocumentStatut === "signé" && (
                  <button onClick={handleConvertToFacture} disabled={actionLoading !== null}
                    className="flex items-center gap-1.5 text-sm rounded-xl px-3 py-2 font-medium transition-colors disabled:opacity-50"
                    style={{ backgroundColor: "#14532D", color: "white" }}>
                    <ArrowRightLeft className="w-3.5 h-3.5" /> {actionLoading === "convert" ? "Conversion…" : "Convertir en facture"}
                  </button>
                )}
                {/* Facture d'acompte — depuis un devis, quel que soit son statut */}
                {savedDocumentId && documentType === "devis" && (
                  <button onClick={handleCreateAcompte} disabled={actionLoading !== null}
                    className="flex items-center gap-1.5 text-sm rounded-xl px-3 py-2 font-medium transition-colors disabled:opacity-50"
                    style={{ backgroundColor: "#B45309", color: "white" }}>
                    <Wallet className="w-3.5 h-3.5" /> {actionLoading === "acompte" ? "Création…" : "Facture d'acompte"}
                  </button>
                )}
                {sendSuccess && (
                  <span className="text-xs px-2.5 py-1.5 rounded-full font-medium"
                    style={{ backgroundColor: "#D1FAE5", color: "#065F46" }}>
                    ✓ Email envoyé
                  </span>
                )}
                {markEnvoyeError && (
                  <span className="text-xs px-2.5 py-1.5 rounded-full font-medium"
                    style={{ backgroundColor: "#FEF2F2", color: "#B91C1C" }}>
                    ⚠ {markEnvoyeError}
                  </span>
                )}
                <PdfExportButton devis={result} documentType={documentType} withTva={withTva} documentDate={documentDate} filename={filename || undefined} signature={signatureInfo ?? undefined} />
                <WordExportButton devis={result} documentType={documentType} withTva={withTva} documentDate={documentDate} filename={filename || undefined} signature={signatureInfo ?? undefined} />

                <button onClick={handleReset}
                  className="flex items-center gap-2 text-sm rounded-xl px-4 py-2.5 transition-colors bg-white"
                  style={{ border: "0.5px solid rgba(20,83,45,0.15)", color: "#5A635D" }}>
                  <RefreshCw className="w-4 h-4" /> Nouveau
                </button>
              </div>
            </div>

            <QuotePreview
              key={documentInstanceKey}
              devis={result}
              documentType={documentType}
              withTva={withTva}
              documentDate={documentDate}
              onUpdate={handleQuotePreviewUpdate}
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

      {showSendModal && result && savedDocumentId && (
        <SendEmailModal
          devis={result}
          documentId={savedDocumentId}
          documentType={documentType}
          onClose={() => setShowSendModal(false)}
          onSent={handleEmailSent}
        />
      )}
    </main>
  );
}
