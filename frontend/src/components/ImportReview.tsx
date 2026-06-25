"use client";
import { FileText, Receipt, Check } from "lucide-react";
import { QuoteResponse } from "@/lib/types";

type ArtisanChoice = "keep" | "replace";
type DocumentType = "devis" | "facture";

interface Props {
  response: QuoteResponse;
  artisanChoice: ArtisanChoice;
  onArtisanChoice: (c: ArtisanChoice) => void;
  onConfirm: () => void;
  onCancel: () => void;
  documentType: DocumentType;
  documentDate: string;
}

function formatIsoDate(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const parts = iso.split("-");
  if (parts.length !== 3) return iso;
  return `${parts[2]}/${parts[1]}/${parts[0]}`;
}

export default function ImportReview({
  response,
  artisanChoice,
  onArtisanChoice,
  onConfirm,
  onCancel,
  documentType,
  documentDate,
}: Props) {
  const meta = response.import_meta;
  const devis = response.devis!;
  const emetteur = meta?.emetteur;
  const hasEmetteur = Boolean(emetteur?.nom || emetteur?.siret);
  const totalTTC = devis.totaux?.total_ttc ?? 0;
  const nbLignes = devis.lignes?.length ?? 0;

  return (
    <div className="max-w-2xl mx-auto space-y-4">

      {/* Résumé du document extrait */}
      <div className="bg-white rounded-2xl p-6" style={{ border: "0.5px solid rgba(20,83,45,0.12)" }}>
        <div className="mb-4">
          <div className="flex items-center gap-2 mb-1">
            {documentType === "facture"
              ? <Receipt className="w-4 h-4" style={{ color: "#14532D" }} />
              : <FileText className="w-4 h-4" style={{ color: "#14532D" }} />}
            <span className="text-xs font-bold uppercase tracking-wide" style={{ color: "#14532D" }}>
              {documentType === "facture" ? "Facture" : "Devis"} importé
            </span>
          </div>
          <h2 className="text-lg font-bold" style={{ color: "#18211C" }}>
            Vérifiez les informations extraites
          </h2>
          <p className="text-sm mt-0.5" style={{ color: "#7C857F" }}>
            Confirmez avant d'afficher l'aperçu.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3">
          {meta?.numero_document_original && (
            <div className="rounded-xl px-4 py-3" style={{ backgroundColor: "#F3F7F4" }}>
              <p className="text-xs font-semibold mb-0.5" style={{ color: "#7C857F" }}>N° document</p>
              <p className="text-sm font-bold" style={{ color: "#18211C" }}>{meta.numero_document_original}</p>
            </div>
          )}
          <div className="rounded-xl px-4 py-3" style={{ backgroundColor: "#F3F7F4" }}>
            <p className="text-xs font-semibold mb-0.5" style={{ color: "#7C857F" }}>Date</p>
            <p className="text-sm font-bold" style={{ color: "#18211C" }}>
              {formatIsoDate(meta?.date_document_original) ?? formatIsoDate(documentDate) ?? documentDate}
            </p>
          </div>
          {devis.client?.nom && (
            <div className="rounded-xl px-4 py-3" style={{ backgroundColor: "#F3F7F4" }}>
              <p className="text-xs font-semibold mb-0.5" style={{ color: "#7C857F" }}>Client</p>
              <p className="text-sm font-bold" style={{ color: "#18211C" }}>{devis.client.nom}</p>
              {devis.client.adresse && (
                <p className="text-xs mt-0.5" style={{ color: "#5A635D" }}>{devis.client.adresse}</p>
              )}
            </div>
          )}
          {devis.chantier?.description && (
            <div className="rounded-xl px-4 py-3" style={{ backgroundColor: "#F3F7F4" }}>
              <p className="text-xs font-semibold mb-0.5" style={{ color: "#7C857F" }}>Chantier</p>
              <p className="text-sm font-bold" style={{ color: "#18211C" }}>{devis.chantier.description}</p>
              {devis.chantier.adresse && (
                <p className="text-xs mt-0.5" style={{ color: "#5A635D" }}>{devis.chantier.adresse}</p>
              )}
            </div>
          )}
          <div className="rounded-xl px-4 py-3" style={{ backgroundColor: "#F3F7F4" }}>
            <p className="text-xs font-semibold mb-0.5" style={{ color: "#7C857F" }}>Lignes extraites</p>
            <p className="text-sm font-bold" style={{ color: "#18211C" }}>{nbLignes} postes</p>
          </div>
          <div className="rounded-xl px-4 py-3" style={{ backgroundColor: "#F3F7F4" }}>
            <p className="text-xs font-semibold mb-0.5" style={{ color: "#7C857F" }}>Total TTC</p>
            <p className="text-sm font-bold" style={{ color: "#18211C" }}>
              {totalTTC.toLocaleString("fr-FR", { style: "currency", currency: "EUR" })}
            </p>
          </div>
          {meta?.conditions_paiement && (
            <div className="rounded-xl px-4 py-3 col-span-2" style={{ backgroundColor: "#F3F7F4" }}>
              <p className="text-xs font-semibold mb-0.5" style={{ color: "#7C857F" }}>Conditions de paiement</p>
              <p className="text-sm" style={{ color: "#18211C" }}>{meta.conditions_paiement}</p>
            </div>
          )}
        </div>
      </div>

      {/* Choix artisan — uniquement si un émetteur a été extrait */}
      {hasEmetteur && (
        <div className="bg-white rounded-2xl p-6" style={{ border: "0.5px solid rgba(20,83,45,0.12)" }}>
          <p className="text-sm font-bold mb-3" style={{ color: "#18211C" }}>
            Infos entreprise à utiliser sur ce document
          </p>
          <div className="space-y-2">
            <label
              className="flex items-start gap-3 p-3 rounded-xl cursor-pointer"
              style={artisanChoice === "keep"
                ? { backgroundColor: "#EDF5EF", border: "1.5px solid #14532D" }
                : { backgroundColor: "#F3F7F4", border: "1.5px solid transparent" }}>
              <input type="radio" name="artisan_choice" value="keep"
                checked={artisanChoice === "keep"}
                onChange={() => onArtisanChoice("keep")}
                className="mt-0.5 accent-green-800" />
              <div>
                <p className="text-sm font-semibold" style={{ color: "#18211C" }}>
                  Garder mon profil enregistré
                </p>
                <p className="text-xs mt-0.5" style={{ color: "#7C857F" }}>
                  Utilise tes coordonnées, IBAN et logo sauvegardés dans l'app
                </p>
              </div>
            </label>
            <label
              className="flex items-start gap-3 p-3 rounded-xl cursor-pointer"
              style={artisanChoice === "replace"
                ? { backgroundColor: "#EDF5EF", border: "1.5px solid #14532D" }
                : { backgroundColor: "#F3F7F4", border: "1.5px solid transparent" }}>
              <input type="radio" name="artisan_choice" value="replace"
                checked={artisanChoice === "replace"}
                onChange={() => onArtisanChoice("replace")}
                className="mt-0.5 accent-green-800" />
              <div>
                <p className="text-sm font-semibold" style={{ color: "#18211C" }}>
                  Utiliser les infos extraites du document
                </p>
                <p className="text-xs mt-0.5" style={{ color: "#7C857F" }}>
                  {[emetteur?.nom, emetteur?.siret, emetteur?.iban].filter(Boolean).join(" — ")}
                </p>
              </div>
            </label>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between">
        <button
          onClick={onCancel}
          className="text-sm px-4 py-2.5 rounded-xl transition-colors"
          style={{ color: "#5A635D" }}>
          ← Revenir au formulaire
        </button>
        <button
          onClick={onConfirm}
          className="flex items-center gap-2 text-white text-sm font-semibold px-6 py-2.5 rounded-xl hover:opacity-90 transition-opacity"
          style={{ backgroundColor: "#14532D" }}>
          <Check className="w-4 h-4" /> Afficher l'aperçu
        </button>
      </div>
    </div>
  );
}
