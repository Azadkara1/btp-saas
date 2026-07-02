"use client";
import { useState, useEffect } from "react";
import { FileText, Receipt, History } from "lucide-react";
import { DocumentSummary, Devis } from "@/lib/types";
import { listDocuments, getDocument } from "@/lib/api";

interface HistoriqueViewProps {
  onOpen: (devis: Devis, documentId: string, statut: string, type_doc: string) => void;
}

const STATUT_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  brouillon: { label: "Brouillon", color: "#6B7280", bg: "#F3F4F6" },
  "envoyé":  { label: "Envoyé",    color: "#1D4ED8", bg: "#DBEAFE" },
  "signé":   { label: "Signé",     color: "#7C3AED", bg: "#EDE9FE" },
  "payé":    { label: "Payé",      color: "#14532D", bg: "#D1FAE5" },
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
      onOpen(detail.devis_payload, doc.id, doc.statut, doc.type_doc);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur lors de l'ouverture");
      setOpeningId(null);
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

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold" style={{ color: "#18211C" }}>Historique des documents</h2>

      {error && (
        <div className="rounded-xl px-4 py-3 text-sm" style={{ backgroundColor: "#FEF2F2", color: "#B91C1C" }}>
          {error}
        </div>
      )}

      {docs.length === 0 && !error ? (
        <div className="text-center py-16 space-y-3">
          <History className="w-10 h-10 mx-auto" style={{ color: "#C3CCC5" }} />
          <p className="text-sm" style={{ color: "#7C857F" }}>Aucun document enregistré</p>
          <p className="text-xs" style={{ color: "#9CA3AF" }}>
            Les devis et factures générés apparaîtront ici automatiquement
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {docs.map(doc => {
            const sc = STATUT_CONFIG[doc.statut] ?? { label: doc.statut, color: "#6B7280", bg: "#F3F4F6" };
            const isOpening = openingId === doc.id;
            return (
              <button
                key={doc.id}
                onClick={() => handleOpen(doc)}
                disabled={isOpening}
                className="w-full text-left rounded-2xl p-4 bg-white transition-all hover:shadow-sm active:scale-[0.99]"
                style={{ border: "0.5px solid rgba(20,83,45,0.12)" }}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="shrink-0 p-2 rounded-xl" style={{ backgroundColor: "#E3EDE6" }}>
                      {doc.type_doc === "facture"
                        ? <Receipt className="w-4 h-4" style={{ color: "#14532D" }} />
                        : <FileText className="w-4 h-4" style={{ color: "#14532D" }} />
                      }
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold text-sm" style={{ color: "#18211C" }}>
                          {doc.numero ?? ((doc.type_doc === "facture" ? "Facture" : "Devis") + " — brouillon")}
                        </span>
                        <span className="text-xs px-2 py-0.5 rounded-full font-medium"
                          style={{ color: sc.color, backgroundColor: sc.bg }}>
                          {sc.label}
                        </span>
                      </div>
                      <p className="text-xs truncate mt-0.5" style={{ color: "#7C857F" }}>
                        {doc.client_nom ?? "Client non renseigné"}
                        {doc.date_document ? ` · ${fmtDate(doc.date_document)}` : ""}
                      </p>
                    </div>
                  </div>

                  <div className="shrink-0 text-right">
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
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
