"use client";
import { useState, useEffect } from "react";
import { FileText, Receipt, History, Copy, ArrowRightLeft, Trash2 } from "lucide-react";
import { DocumentSummary, DocumentDetail } from "@/lib/types";
import { listDocuments, getDocument, convertToFacture, duplicateDocument, deleteDocument } from "@/lib/api";

interface HistoriqueViewProps {
  onOpen: (detail: DocumentDetail) => void;
}

const STATUT_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  brouillon: { label: "Brouillon", color: "#6B7280", bg: "#F3F4F6" },
  "envoyé":  { label: "Envoyé",    color: "#1D4ED8", bg: "#DBEAFE" },
  "signé":   { label: "Signé",     color: "#7C3AED", bg: "#EDE9FE" },
  "payé":    { label: "Payé",      color: "#14532D", bg: "#D1FAE5" },
  "refusé":  { label: "Refusé",    color: "#B91C1C", bg: "#FEE2E2" },
  "expiré":  { label: "Expiré",    color: "#4B5563", bg: "#E5E7EB" },
};

function fmtDate(iso: string): string {
  if (!iso) return "";
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}

function fmtMoney(n: number | null | undefined): string {
  if (n == null) return "—";
  return n.toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " €";
}

export default function HistoriqueView({ onOpen }: HistoriqueViewProps) {
  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [openingId, setOpeningId] = useState<string | null>(null);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"devis" | "facture">("devis");

  useEffect(() => {
    listDocuments()
      .then(setDocs)
      .catch(e => setError(e instanceof Error ? e.message : "Erreur"))
      .finally(() => setLoading(false));
  }, []);

  const handleOpen = async (doc: DocumentSummary) => {
    setOpeningId(doc.id);
    try {
      const detail = await getDocument(doc.id);
      onOpen(detail);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur lors de l'ouverture");
      setOpeningId(null);
    }
  };

  const handleDuplicate = async (doc: DocumentSummary, e: React.MouseEvent) => {
    e.stopPropagation();
    setActionLoadingId(doc.id);
    setError(null);
    try {
      const created = await duplicateDocument(doc.id);
      onOpen(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de la duplication");
      setActionLoadingId(null);
    }
  };

  const handleConvert = async (doc: DocumentSummary, e: React.MouseEvent) => {
    e.stopPropagation();
    setActionLoadingId(doc.id);
    setError(null);
    try {
      const created = await convertToFacture(doc.id);
      onOpen(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de la conversion");
      setActionLoadingId(null);
    }
  };

  const handleDelete = async (doc: DocumentSummary, e: React.MouseEvent) => {
    e.stopPropagation();
    const label = doc.titre ?? (doc.type_doc === "facture" ? "cette facture" : "ce devis");
    const message = doc.numero
      ? `Supprimer ${label} (n° ${doc.numero}) ? Il disparaîtra de vos listes — son numéro reste réservé et ne sera jamais réattribué.`
      : `Supprimer définitivement ${label} ? Cette action est irréversible.`;
    if (!window.confirm(message)) return;
    setActionLoadingId(doc.id);
    setError(null);
    try {
      await deleteDocument(doc.id);
      setDocs(prev => prev.filter(d => d.id !== doc.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de la suppression");
    } finally {
      setActionLoadingId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-8 w-8 border-2"
          style={{ borderColor: "#14532D", borderTopColor: "transparent" }} />
      </div>
    );
  }

  const docsFiltres = docs.filter(d => d.type_doc === activeTab);
  const nbDevis = docs.filter(d => d.type_doc === "devis").length;
  const nbFactures = docs.filter(d => d.type_doc === "facture").length;

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold" style={{ color: "#18211C" }}>Historique des documents</h2>

      <div className="flex gap-2">
        {(["devis", "facture"] as const).map(tab => (
          <button key={tab} type="button" onClick={() => setActiveTab(tab)}
            className="flex items-center gap-1.5 text-sm font-medium rounded-xl px-4 py-2 transition-colors"
            style={activeTab === tab
              ? { backgroundColor: "#14532D", color: "#FFFFFF" }
              : { border: "0.5px solid rgba(20,83,45,0.15)", color: "#5A635D", backgroundColor: "white" }}>
            {tab === "devis" ? <FileText className="w-3.5 h-3.5" /> : <Receipt className="w-3.5 h-3.5" />}
            {tab === "devis" ? `Devis (${nbDevis})` : `Factures (${nbFactures})`}
          </button>
        ))}
      </div>

      {error && (
        <div className="rounded-xl px-4 py-3 text-sm" style={{ backgroundColor: "#FEF2F2", color: "#B91C1C" }}>
          {error}
        </div>
      )}

      {docsFiltres.length === 0 && !error ? (
        <div className="text-center py-16 space-y-3">
          <History className="w-10 h-10 mx-auto" style={{ color: "#C3CCC5" }} />
          <p className="text-sm" style={{ color: "#7C857F" }}>
            {activeTab === "devis" ? "Aucun devis enregistré" : "Aucune facture enregistrée"}
          </p>
          <p className="text-xs" style={{ color: "#9CA3AF" }}>
            Les devis et factures générés apparaîtront ici automatiquement
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {docsFiltres.map(doc => {
            const sc = STATUT_CONFIG[doc.statut] ?? { label: doc.statut, color: "#6B7280", bg: "#F3F4F6" };
            const isOpening = openingId === doc.id;
            const isActing = actionLoadingId === doc.id;
            const canConvert = doc.type_doc === "devis" && doc.statut === "signé";
            return (
              <div
                key={doc.id}
                className="w-full rounded-2xl p-4 bg-white transition-all hover:shadow-sm"
                style={{ border: "0.5px solid rgba(20,83,45,0.12)" }}
              >
                <div className="flex items-center justify-between gap-3">
                  <button
                    onClick={() => handleOpen(doc)}
                    disabled={isOpening || isActing}
                    className="flex items-center gap-3 min-w-0 flex-1 text-left active:scale-[0.99] transition-transform"
                  >
                    <div className="shrink-0 p-2 rounded-xl" style={{ backgroundColor: "#E3EDE6" }}>
                      {doc.type_doc === "facture"
                        ? <Receipt className="w-4 h-4" style={{ color: "#14532D" }} />
                        : <FileText className="w-4 h-4" style={{ color: "#14532D" }} />
                      }
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold text-sm" style={{ color: "#18211C" }}>
                          {doc.titre ?? (doc.type_doc === "facture" ? "Facture" : "Devis")}
                        </span>
                        <span className="text-xs px-2 py-0.5 rounded-full font-medium"
                          style={{ color: sc.color, backgroundColor: sc.bg }}>
                          {sc.label}
                        </span>
                      </div>
                      <p className="text-xs truncate mt-0.5" style={{ color: "#7C857F" }}>
                        {[doc.numero_document, doc.client_nom].filter(Boolean).join(" · ")}
                        {doc.date_document ? ` · ${fmtDate(doc.date_document)}` : ""}
                      </p>
                    </div>
                  </button>

                  <div className="shrink-0 flex items-center gap-1.5">
                    <div className="text-right mr-1">
                      <p className="font-semibold text-sm" style={{ color: "#18211C" }}>
                        {fmtMoney(doc.total_ttc)}
                      </p>
                      {isOpening ? (
                        <div className="mt-1 animate-spin rounded-full h-4 w-4 border-2 ml-auto"
                          style={{ borderColor: "#14532D", borderTopColor: "transparent" }} />
                      ) : (
                        <p className="text-xs mt-0.5" style={{ color: "#9CA3AF" }}>Ouvrir →</p>
                      )}
                    </div>
                    <button
                      onClick={e => handleDuplicate(doc, e)}
                      disabled={isActing || isOpening}
                      title="Dupliquer ce document"
                      className="p-2 rounded-lg transition-colors hover:bg-gray-100 disabled:opacity-40"
                      style={{ color: "#5A635D" }}
                    >
                      <Copy className="w-4 h-4" />
                    </button>
                    {canConvert && (
                      <button
                        onClick={e => handleConvert(doc, e)}
                        disabled={isActing || isOpening}
                        title="Convertir en facture"
                        className="p-2 rounded-lg transition-colors hover:bg-green-50 disabled:opacity-40"
                        style={{ color: "#14532D" }}
                      >
                        <ArrowRightLeft className="w-4 h-4" />
                      </button>
                    )}
                    <button
                      onClick={e => handleDelete(doc, e)}
                      disabled={isActing || isOpening}
                      title="Supprimer ce document"
                      className="p-2 rounded-lg transition-colors hover:bg-red-50 disabled:opacity-40"
                      style={{ color: "#B91C1C" }}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
