"use client";
import { useState } from "react";
import { X, Wallet, Loader2 } from "lucide-react";
import { CreateAcompteRequest } from "@/lib/types";

interface AcompteModalProps {
  onClose: () => void;
  onConfirm: (body: CreateAcompteRequest) => Promise<void>;
}

export default function AcompteModal({ onClose, onConfirm }: AcompteModalProps) {
  const [mode, setMode] = useState<"pourcentage" | "montant_fixe">("pourcentage");
  const [pourcentage, setPourcentage] = useState("30");
  const [montantTtc, setMontantTtc] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleConfirm = async () => {
    setError(null);
    let body: CreateAcompteRequest;
    if (mode === "pourcentage") {
      const val = parseFloat(pourcentage.replace(",", "."));
      if (!Number.isFinite(val) || val <= 0 || val > 100) {
        setError("Pourcentage invalide (doit être entre 0 et 100).");
        return;
      }
      body = { mode, pourcentage: val };
    } else {
      const val = parseFloat(montantTtc.replace(",", "."));
      if (!Number.isFinite(val) || val <= 0) {
        setError("Montant invalide (doit être supérieur à 0).");
        return;
      }
      body = { mode, montant_ttc: val };
    }
    setSaving(true);
    try {
      await onConfirm(body);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de la création de la facture d'acompte");
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ backgroundColor: "rgba(24,33,28,0.45)" }}>
      <div className="bg-white rounded-2xl w-full max-w-md p-6 space-y-4" style={{ boxShadow: "0 20px 60px rgba(0,0,0,0.2)" }}>
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold flex items-center gap-2" style={{ color: "#18211C" }}>
            <Wallet className="w-5 h-5" style={{ color: "#B45309" }} /> Facture d&apos;acompte
          </h3>
          <button onClick={onClose} disabled={saving}
            className="p-1 rounded-lg hover:bg-gray-100 transition-colors disabled:opacity-40"
            style={{ color: "#7C857F" }}>
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex gap-2">
          {(["pourcentage", "montant_fixe"] as const).map(m => (
            <button key={m} type="button" onClick={() => setMode(m)} disabled={saving}
              className="flex-1 text-sm font-medium rounded-xl px-3 py-2 transition-colors"
              style={mode === m
                ? { backgroundColor: "#14532D", color: "white" }
                : { border: "0.5px solid rgba(20,83,45,0.15)", color: "#5A635D", backgroundColor: "white" }}>
              {m === "pourcentage" ? "Pourcentage" : "Montant fixe"}
            </button>
          ))}
        </div>

        {mode === "pourcentage" ? (
          <div>
            <label className="block text-sm font-medium mb-1" style={{ color: "#5A635D" }}>
              Pourcentage du devis (%)
            </label>
            <input type="number" min="1" max="100" value={pourcentage} onChange={e => setPourcentage(e.target.value)}
              className="input-field" autoFocus disabled={saving} />
          </div>
        ) : (
          <div>
            <label className="block text-sm font-medium mb-1" style={{ color: "#5A635D" }}>
              Montant de l&apos;acompte (€ TTC)
            </label>
            <input type="number" min="0.01" step="0.01" value={montantTtc} onChange={e => setMontantTtc(e.target.value)}
              placeholder="Ex : 500" className="input-field" autoFocus disabled={saving} />
            <p className="text-xs mt-1" style={{ color: "#7C857F" }}>
              Montant TTC réellement payé par le client — la TVA est recalculée automatiquement.
            </p>
          </div>
        )}

        {error && (
          <div className="rounded-xl px-3 py-2 text-sm" style={{ backgroundColor: "#FEF2F2", color: "#B91C1C" }}>
            ⚠ {error}
          </div>
        )}

        <div className="flex items-center justify-end gap-2 pt-2">
          <button onClick={onClose} disabled={saving}
            className="text-sm rounded-xl px-4 py-2.5 transition-colors bg-white disabled:opacity-50"
            style={{ border: "0.5px solid rgba(20,83,45,0.15)", color: "#5A635D" }}>
            Annuler
          </button>
          <button onClick={handleConfirm} disabled={saving}
            className="flex items-center gap-2 text-sm font-semibold px-4 py-2.5 rounded-xl text-white transition-colors disabled:opacity-50"
            style={{ backgroundColor: "#B45309" }}>
            {saving
              ? <><Loader2 className="w-4 h-4 animate-spin" /> Création…</>
              : <>Créer la facture</>}
          </button>
        </div>
      </div>
    </div>
  );
}
