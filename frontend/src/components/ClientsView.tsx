"use client";
import { useState, useEffect } from "react";
import { Users, FileText, Receipt, ArrowLeft, Pencil, Check, X } from "lucide-react";
import { ClientSummary, ClientDetail, DocumentDetail } from "@/lib/types";
import { listClients, getClient, updateClient, getDocument } from "@/lib/api";

interface ClientsViewProps {
  onOpenDocument: (detail: DocumentDetail) => void;
}

type SortKey = "nom" | "ca_total" | "nb_documents";

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

export default function ClientsView({ onOpenDocument }: ClientsViewProps) {
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("nom");

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ClientDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [openingDocId, setOpeningDocId] = useState<string | null>(null);

  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState({ nom: "", adresse: "", code_postal: "", ville: "" });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    listClients()
      .then(setClients)
      .catch(e => setError(e instanceof Error ? e.message : "Erreur"))
      .finally(() => setLoading(false));
  }, []);

  const openClient = async (id: string) => {
    setSelectedId(id);
    setDetailLoading(true);
    setError(null);
    try {
      const d = await getClient(id);
      setDetail(d);
      setEditForm({ nom: d.nom, adresse: d.adresse ?? "", code_postal: d.code_postal ?? "", ville: d.ville ?? "" });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur lors du chargement");
      setSelectedId(null);
    } finally {
      setDetailLoading(false);
    }
  };

  const backToList = () => {
    setSelectedId(null);
    setDetail(null);
    setEditing(false);
  };

  const handleSave = async () => {
    if (!selectedId) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await updateClient(selectedId, editForm);
      setDetail(prev => prev ? { ...prev, ...updated } : prev);
      setClients(prev => prev.map(c => c.id === selectedId ? { ...c, ...updated } : c));
      setEditing(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur lors de l'enregistrement");
    } finally {
      setSaving(false);
    }
  };

  const handleOpenDoc = async (docId: string) => {
    setOpeningDocId(docId);
    try {
      const d = await getDocument(docId);
      onOpenDocument(d);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur lors de l'ouverture");
      setOpeningDocId(null);
    }
  };

  const sortedClients = [...clients].sort((a, b) => {
    if (sortKey === "nom") return a.nom.localeCompare(b.nom);
    if (sortKey === "ca_total") return b.ca_total - a.ca_total;
    return b.nb_documents - a.nb_documents;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-8 w-8 border-2"
          style={{ borderColor: "#14532D", borderTopColor: "transparent" }} />
      </div>
    );
  }

  // ── Fiche client ──────────────────────────────────────────────
  if (selectedId) {
    return (
      <div className="space-y-4">
        <button onClick={backToList} className="flex items-center gap-1.5 text-sm font-medium"
          style={{ color: "#5A635D" }}>
          <ArrowLeft className="w-4 h-4" /> Retour aux clients
        </button>

        {error && (
          <div className="rounded-xl px-4 py-3 text-sm" style={{ backgroundColor: "#FEF2F2", color: "#B91C1C" }}>
            {error}
          </div>
        )}

        {detailLoading || !detail ? (
          <div className="flex items-center justify-center py-16">
            <div className="animate-spin rounded-full h-6 w-6 border-2"
              style={{ borderColor: "#14532D", borderTopColor: "transparent" }} />
          </div>
        ) : (
          <>
            <div className="card space-y-3">
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <h2 className="text-xl font-bold" style={{ color: "#18211C" }}>{detail.nom}</h2>
                {!editing ? (
                  <button onClick={() => setEditing(true)}
                    className="flex items-center gap-1 text-xs px-2.5 py-1.5 rounded-lg transition-colors"
                    style={{ color: "#14532D", border: "1px solid rgba(20,83,45,0.2)" }}>
                    <Pencil className="w-3.5 h-3.5" /> Modifier
                  </button>
                ) : (
                  <div className="flex items-center gap-1.5">
                    <button onClick={handleSave} disabled={saving}
                      className="flex items-center gap-1 text-xs px-2.5 py-1.5 rounded-lg text-white disabled:opacity-50"
                      style={{ backgroundColor: "#14532D" }}>
                      <Check className="w-3.5 h-3.5" /> Enregistrer
                    </button>
                    <button onClick={() => setEditing(false)} disabled={saving}
                      className="flex items-center gap-1 text-xs px-2.5 py-1.5 rounded-lg"
                      style={{ color: "#5A635D", border: "1px solid rgba(20,83,45,0.15)" }}>
                      <X className="w-3.5 h-3.5" /> Annuler
                    </button>
                  </div>
                )}
              </div>

              {editing ? (
                <div className="grid sm:grid-cols-2 gap-3">
                  <label className="text-sm">
                    <span className="text-xs font-medium block mb-1" style={{ color: "#5A635D" }}>Nom</span>
                    <input value={editForm.nom} onChange={e => setEditForm({ ...editForm, nom: e.target.value })}
                      className="input-field" />
                  </label>
                  <label className="text-sm">
                    <span className="text-xs font-medium block mb-1" style={{ color: "#5A635D" }}>Adresse</span>
                    <input value={editForm.adresse} onChange={e => setEditForm({ ...editForm, adresse: e.target.value })}
                      className="input-field" />
                  </label>
                  <label className="text-sm">
                    <span className="text-xs font-medium block mb-1" style={{ color: "#5A635D" }}>Code postal</span>
                    <input value={editForm.code_postal} onChange={e => setEditForm({ ...editForm, code_postal: e.target.value })}
                      className="input-field" />
                  </label>
                  <label className="text-sm">
                    <span className="text-xs font-medium block mb-1" style={{ color: "#5A635D" }}>Ville</span>
                    <input value={editForm.ville} onChange={e => setEditForm({ ...editForm, ville: e.target.value })}
                      className="input-field" />
                  </label>
                </div>
              ) : (
                <p className="text-sm" style={{ color: "#5A635D" }}>
                  {[detail.adresse, [detail.code_postal, detail.ville].filter(Boolean).join(" ")]
                    .filter(Boolean).join(" · ") || "Aucune coordonnée renseignée"}
                </p>
              )}

              <div className="flex gap-4 pt-2 border-t" style={{ borderColor: "rgba(20,83,45,0.1)" }}>
                <div>
                  <p className="text-xs" style={{ color: "#7C857F" }}>Documents</p>
                  <p className="font-semibold text-sm" style={{ color: "#18211C" }}>{detail.nb_documents}</p>
                </div>
                <div>
                  <p className="text-xs" style={{ color: "#7C857F" }}>CA total</p>
                  <p className="font-semibold text-sm" style={{ color: "#18211C" }}>{fmtMoney(detail.ca_total)}</p>
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <h3 className="text-sm font-semibold" style={{ color: "#18211C" }}>Historique</h3>
              {detail.documents.length === 0 ? (
                <p className="text-sm py-6 text-center" style={{ color: "#9CA3AF" }}>Aucun document pour ce client</p>
              ) : (
                detail.documents.map(doc => {
                  const sc = STATUT_CONFIG[doc.statut] ?? { label: doc.statut, color: "#6B7280", bg: "#F3F4F6" };
                  const isOpening = openingDocId === doc.id;
                  return (
                    <button key={doc.id} onClick={() => handleOpenDoc(doc.id)} disabled={isOpening}
                      className="w-full text-left rounded-2xl p-4 bg-white transition-all hover:shadow-sm active:scale-[0.99] flex items-center justify-between gap-3"
                      style={{ border: "0.5px solid rgba(20,83,45,0.12)" }}>
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="shrink-0 p-2 rounded-xl" style={{ backgroundColor: "#E3EDE6" }}>
                          {doc.type_doc === "facture"
                            ? <Receipt className="w-4 h-4" style={{ color: "#14532D" }} />
                            : <FileText className="w-4 h-4" style={{ color: "#14532D" }} />}
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
                            {doc.date_document ? fmtDate(doc.date_document) : ""}
                          </p>
                        </div>
                      </div>
                      <p className="font-semibold text-sm shrink-0" style={{ color: "#18211C" }}>
                        {fmtMoney(doc.total_ttc)}
                      </p>
                    </button>
                  );
                })
              )}
            </div>
          </>
        )}
      </div>
    );
  }

  // ── Liste des clients ────────────────────────────────────────────
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <h2 className="text-xl font-bold" style={{ color: "#18211C" }}>Clients</h2>
        <div className="flex items-center gap-1.5">
          {(["nom", "ca_total", "nb_documents"] as SortKey[]).map(k => (
            <button key={k} onClick={() => setSortKey(k)}
              className="text-xs px-2.5 py-1.5 rounded-lg font-medium transition-colors"
              style={sortKey === k
                ? { backgroundColor: "#14532D", color: "white" }
                : { color: "#5A635D", border: "1px solid rgba(20,83,45,0.15)" }}>
              {k === "nom" ? "Nom" : k === "ca_total" ? "CA" : "Nb documents"}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="rounded-xl px-4 py-3 text-sm" style={{ backgroundColor: "#FEF2F2", color: "#B91C1C" }}>
          {error}
        </div>
      )}

      {sortedClients.length === 0 && !error ? (
        <div className="text-center py-16 space-y-3">
          <Users className="w-10 h-10 mx-auto" style={{ color: "#C3CCC5" }} />
          <p className="text-sm" style={{ color: "#7C857F" }}>Aucun client enregistré</p>
          <p className="text-xs" style={{ color: "#9CA3AF" }}>
            Les clients des devis et factures générés apparaîtront ici automatiquement
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {sortedClients.map(c => (
            <button key={c.id} onClick={() => openClient(c.id)}
              className="w-full text-left rounded-2xl p-4 bg-white transition-all hover:shadow-sm active:scale-[0.99] flex items-center justify-between gap-3"
              style={{ border: "0.5px solid rgba(20,83,45,0.12)" }}>
              <div className="flex items-center gap-3 min-w-0">
                <div className="shrink-0 p-2 rounded-xl" style={{ backgroundColor: "#E3EDE6" }}>
                  <Users className="w-4 h-4" style={{ color: "#14532D" }} />
                </div>
                <div className="min-w-0">
                  <p className="font-semibold text-sm" style={{ color: "#18211C" }}>{c.nom}</p>
                  <p className="text-xs truncate mt-0.5" style={{ color: "#7C857F" }}>
                    {[c.code_postal, c.ville].filter(Boolean).join(" ") || "—"}
                  </p>
                </div>
              </div>
              <div className="text-right shrink-0">
                <p className="font-semibold text-sm" style={{ color: "#18211C" }}>{fmtMoney(c.ca_total)}</p>
                <p className="text-xs mt-0.5" style={{ color: "#9CA3AF" }}>
                  {c.nb_documents} document{c.nb_documents > 1 ? "s" : ""}
                </p>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
