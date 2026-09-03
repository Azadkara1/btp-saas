"use client";
import { useState } from "react";
import { X, Send, Loader2 } from "lucide-react";
import { sendDocumentByEmail } from "@/lib/api";
import { Devis, SendEmailResponse } from "@/lib/types";

interface SendEmailModalProps {
  devis: Devis;
  documentId: string;
  documentType: "devis" | "facture";
  onClose: () => void;
  onSent: (response: SendEmailResponse) => void;
}

export default function SendEmailModal({ devis, documentId, documentType, onClose, onSent }: SendEmailModalProps) {
  const label = documentType === "facture" ? "facture" : "devis";
  const numero = devis.numero_document || "";
  const artisanNom = devis.artisan.nom || "";

  const [email, setEmail] = useState(devis.client.email ?? "");
  const [message, setMessage] = useState(
    `Bonjour,\n\nVeuillez trouver ci-joint votre ${label}${numero ? ` ${numero}` : ""}.\n\nCordialement,\n${artisanNom}`
  );
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSend = async () => {
    if (!email.trim()) {
      setError("L'adresse email du client est requise.");
      return;
    }
    setSending(true);
    setError(null);
    try {
      const res = await sendDocumentByEmail(documentId, { email_destinataire: email.trim(), message });
      onSent(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de l'envoi");
      setSending(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ backgroundColor: "rgba(24,33,28,0.45)" }}>
      <div className="bg-white rounded-2xl w-full max-w-md p-6 space-y-4" style={{ boxShadow: "0 20px 60px rgba(0,0,0,0.2)" }}>
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold" style={{ color: "#18211C" }}>
            Envoyer le {label} par email
          </h3>
          <button onClick={onClose} disabled={sending}
            className="p-1 rounded-lg hover:bg-gray-100 transition-colors disabled:opacity-40"
            style={{ color: "#7C857F" }}>
            <X className="w-5 h-5" />
          </button>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1" style={{ color: "#5A635D" }}>Email du client</label>
          <input type="email" value={email} onChange={e => setEmail(e.target.value)}
            placeholder="client@exemple.fr" className="input-field" autoFocus disabled={sending} />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1" style={{ color: "#5A635D" }}>Message</label>
          <textarea value={message} onChange={e => setMessage(e.target.value)} rows={6} disabled={sending}
            className="input-field resize-none text-sm" />
          <p className="text-xs mt-1" style={{ color: "#7C857F" }}>
            Le {label} est joint automatiquement en PDF.
          </p>
        </div>

        {error && (
          <div className="rounded-xl px-3 py-2 text-sm" style={{ backgroundColor: "#FEF2F2", color: "#B91C1C" }}>
            ⚠ {error}
          </div>
        )}

        <div className="flex items-center justify-end gap-2 pt-2">
          <button onClick={onClose} disabled={sending}
            className="text-sm rounded-xl px-4 py-2.5 transition-colors bg-white disabled:opacity-50"
            style={{ border: "0.5px solid rgba(20,83,45,0.15)", color: "#5A635D" }}>
            Annuler
          </button>
          <button onClick={handleSend} disabled={sending} className="btn-primary flex items-center gap-2">
            {sending
              ? <><Loader2 className="w-4 h-4 animate-spin" /> Envoi…</>
              : <><Send className="w-4 h-4" /> Envoyer</>}
          </button>
        </div>
      </div>
    </div>
  );
}
