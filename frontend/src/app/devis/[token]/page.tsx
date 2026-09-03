"use client";
import { useState, useEffect, useRef } from "react";
import { useParams } from "next/navigation";
import { HardHat, CheckCircle, XCircle, Loader2, AlertTriangle, Eraser } from "lucide-react";
import { getPublicDevis, acceptPublicDevis, refusePublicDevis } from "@/lib/api";
import { PublicDevisView } from "@/lib/types";

function fmtMoney(n: number): string {
  return n.toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " €";
}

function fmtDate(iso?: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("fr-FR");
}

// ── Pavé de signature à main levée (optionnel — repli sur le nom tapé si vide) ──
function SignaturePad({ onChange }: { onChange: (dataUrl: string | null) => void }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const drawingRef = useRef(false);
  const [hasDrawn, setHasDrawn] = useState(false);

  const getPos = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    return {
      x: (e.clientX - rect.left) * (canvas.width / rect.width),
      y: (e.clientY - rect.top) * (canvas.height / rect.height),
    };
  };

  const handlePointerDown = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    canvas.setPointerCapture(e.pointerId);
    const { x, y } = getPos(e);
    ctx.beginPath();
    ctx.moveTo(x, y);
    drawingRef.current = true;
  };

  const handlePointerMove = (e: React.PointerEvent<HTMLCanvasElement>) => {
    if (!drawingRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!ctx) return;
    const { x, y } = getPos(e);
    ctx.strokeStyle = "#18211C";
    ctx.lineWidth = 2.5;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.lineTo(x, y);
    ctx.stroke();
    if (!hasDrawn) setHasDrawn(true);
  };

  const handlePointerUp = () => {
    if (!drawingRef.current) return;
    drawingRef.current = false;
    const canvas = canvasRef.current;
    if (canvas) onChange(canvas.toDataURL("image/png"));
  };

  const handleClear = () => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (canvas && ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
    setHasDrawn(false);
    onChange(null);
  };

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <label className="text-xs font-semibold" style={{ color: "#5A635D" }}>
          Votre signature (optionnel — dessinez avec le doigt ou la souris)
        </label>
        {hasDrawn && (
          <button type="button" onClick={handleClear}
            className="flex items-center gap-1 text-xs font-medium" style={{ color: "#B91C1C" }}>
            <Eraser className="w-3 h-3" /> Effacer
          </button>
        )}
      </div>
      <canvas
        ref={canvasRef}
        width={600}
        height={180}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerLeave={handlePointerUp}
        className="w-full rounded-xl bg-white"
        style={{ border: "1px dashed rgba(20,83,45,0.3)", touchAction: "none", height: 140 }}
      />
      {!hasDrawn && (
        <p className="text-xs" style={{ color: "#9CA3AF" }}>
          Si vous ne dessinez rien, votre nom tapé ci-dessus fera foi de signature.
        </p>
      )}
    </div>
  );
}

export default function PublicDevisPage() {
  const params = useParams();
  const token = params.token as string;

  const [devis, setDevis] = useState<PublicDevisView | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<{ status?: number; message: string } | null>(null);
  const [actionDone, setActionDone] = useState<"signe" | "refuse" | null>(null);

  const [nom, setNom] = useState("");
  const [accepteConditions, setAccepteConditions] = useState(false);
  const [signatureDataUrl, setSignatureDataUrl] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [showRefuseConfirm, setShowRefuseConfirm] = useState(false);

  useEffect(() => {
    setLoading(true);
    getPublicDevis(token)
      .then(setDevis)
      .catch(err => setLoadError({ status: err.status, message: err.message }))
      .finally(() => setLoading(false));
  }, [token]);

  const handleAccept = async () => {
    if (!nom.trim()) { setFormError("Merci d'indiquer votre nom."); return; }
    if (!accepteConditions) { setFormError("Merci de cocher la case d'acceptation."); return; }
    setSubmitting(true);
    setFormError(null);
    try {
      const imageBase64 = signatureDataUrl ? signatureDataUrl.split(",", 2)[1] : undefined;
      await acceptPublicDevis(token, nom.trim(), imageBase64);
      setActionDone("signe");
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Erreur lors de la signature");
    } finally {
      setSubmitting(false);
    }
  };

  const handleRefuse = async () => {
    setSubmitting(true);
    setFormError(null);
    try {
      await refusePublicDevis(token);
      setActionDone("refuse");
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Erreur lors du refus");
    } finally {
      setSubmitting(false);
      setShowRefuseConfirm(false);
    }
  };

  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center" style={{ backgroundColor: "#FAFAF7" }}>
        <Loader2 className="w-8 h-8 animate-spin" style={{ color: "#14532D" }} />
      </main>
    );
  }

  if (loadError) {
    const isExpired = loadError.status === 410;
    return (
      <main className="min-h-screen flex items-center justify-center px-4" style={{ backgroundColor: "#FAFAF7" }}>
        <div className="bg-white rounded-2xl p-8 max-w-sm w-full text-center space-y-3"
          style={{ border: "0.5px solid rgba(20,83,45,0.12)", boxShadow: "0 4px 24px rgba(0,0,0,0.06)" }}>
          <AlertTriangle className="w-8 h-8 mx-auto" style={{ color: "#B45309" }} />
          <h1 className="text-lg font-black" style={{ color: "#18211C" }}>
            {isExpired ? "Lien expiré" : "Lien invalide"}
          </h1>
          <p className="text-sm" style={{ color: "#5A635D" }}>
            {isExpired
              ? "Ce lien de signature n'est plus valide. Contactez votre artisan pour en recevoir un nouveau."
              : "Ce lien n'existe pas ou n'est plus disponible."}
          </p>
        </div>
      </main>
    );
  }

  if (!devis) return null;

  const displayStatut = actionDone === "signe" ? "signé" : actionDone === "refuse" ? "refusé" : devis.statut;

  return (
    <main className="min-h-screen py-6 px-4" style={{ backgroundColor: "#FAFAF7" }}>
      <div className="max-w-2xl mx-auto space-y-4">
        {/* En-tête */}
        <div className="flex items-center gap-3">
          <div className="text-white p-2 rounded-xl shrink-0" style={{ backgroundColor: "#14532D" }}>
            <HardHat className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs" style={{ color: "#7C857F" }}>Devis proposé par</p>
            <p className="font-bold" style={{ color: "#18211C" }}>{devis.artisan.nom || "votre artisan"}</p>
          </div>
        </div>

        {displayStatut === "signé" && (
          <div className="rounded-xl p-4 flex items-start gap-2" style={{ backgroundColor: "#D1FAE5", color: "#065F46" }}>
            <CheckCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <p className="text-sm font-medium">
              {actionDone === "signe"
                ? "Merci, votre acceptation a bien été enregistrée."
                : `Ce devis a déjà été signé${devis.deja_signe_par ? ` par ${devis.deja_signe_par}` : ""}${devis.deja_signe_le ? ` le ${fmtDate(devis.deja_signe_le)}` : ""}.`}
            </p>
          </div>
        )}
        {displayStatut === "refusé" && (
          <div className="rounded-xl p-4 flex items-start gap-2" style={{ backgroundColor: "#FEE2E2", color: "#991B1B" }}>
            <XCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <p className="text-sm font-medium">
              {actionDone === "refuse" ? "Votre refus a bien été enregistré." : "Ce devis a été refusé."}
            </p>
          </div>
        )}
        {displayStatut === "expiré" && !actionDone && (
          <div className="rounded-xl p-4 flex items-start gap-2" style={{ backgroundColor: "#FFFBEB", color: "#92400E" }}>
            <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
            <p className="text-sm font-medium">Ce devis a expiré. Contactez votre artisan pour un nouveau devis.</p>
          </div>
        )}

        {/* Carte devis */}
        <div className="bg-white rounded-2xl p-5 space-y-5"
          style={{ border: "0.5px solid rgba(20,83,45,0.12)", boxShadow: "0 4px 24px rgba(0,0,0,0.06)" }}>
          <div className="flex justify-between items-start flex-wrap gap-3">
            <div>
              <h1 className="text-lg font-bold" style={{ color: "#18211C" }}>
                Devis {devis.numero_document ?? ""}
              </h1>
              {devis.date_document && <p className="text-xs" style={{ color: "#7C857F" }}>{fmtDate(devis.date_document)}</p>}
            </div>
            <div className="text-right">
              <p className="text-xs" style={{ color: "#7C857F" }}>Montant TTC</p>
              <p className="text-xl font-bold" style={{ color: "#14532D" }}>{fmtMoney(devis.totaux.total_ttc)}</p>
            </div>
          </div>

          {devis.client.nom && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: "#7C857F" }}>Client</p>
              <p className="text-sm" style={{ color: "#18211C" }}>{devis.client.nom}</p>
              {devis.client.adresse && <p className="text-xs" style={{ color: "#5A635D" }}>{devis.client.adresse}</p>}
              {(devis.client.code_postal || devis.client.ville) && (
                <p className="text-xs" style={{ color: "#5A635D" }}>
                  {[devis.client.code_postal, devis.client.ville].filter(Boolean).join(" ")}
                </p>
              )}
            </div>
          )}

          <div>
            <p className="text-xs font-semibold uppercase tracking-wide mb-1" style={{ color: "#7C857F" }}>Chantier</p>
            <p className="text-sm whitespace-pre-line" style={{ color: "#18211C" }}>{devis.chantier.description}</p>
          </div>

          <div className="space-y-1">
            <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: "#7C857F" }}>Prestations</p>
            {devis.lignes.map((l, i) => (
              <div key={i} className="flex justify-between gap-3 py-2 border-b border-gray-100 text-sm">
                <div className="min-w-0">
                  <p className="font-medium" style={{ color: "#18211C" }}>{l.poste}</p>
                  <p className="text-xs" style={{ color: "#7C857F" }}>{l.description}</p>
                  <p className="text-xs" style={{ color: "#9CA3AF" }}>
                    {l.quantite ?? "au réel"} {l.unite} × {fmtMoney(l.prix_unitaire_ht)}
                  </p>
                </div>
                <p className="font-semibold shrink-0" style={{ color: "#18211C" }}>
                  {fmtMoney((l.quantite ?? 1) * l.prix_unitaire_ht)}
                </p>
              </div>
            ))}
          </div>

          <div className="rounded-xl p-3 space-y-1 text-sm" style={{ backgroundColor: "#F0F7F3" }}>
            <div className="flex justify-between">
              <span style={{ color: "#5A635D" }}>Total HT</span>
              <span style={{ color: "#18211C" }}>{fmtMoney(devis.totaux.total_ht)}</span>
            </div>
            {devis.totaux.total_tva > 0 && (
              <div className="flex justify-between">
                <span style={{ color: "#5A635D" }}>TVA</span>
                <span style={{ color: "#18211C" }}>{fmtMoney(devis.totaux.total_tva)}</span>
              </div>
            )}
            <div className="flex justify-between font-bold pt-1 mt-1" style={{ borderTop: "1px solid rgba(20,83,45,0.15)", color: "#18211C" }}>
              <span>Total TTC</span>
              <span>{fmtMoney(devis.totaux.total_ttc)}</span>
            </div>
          </div>

          {devis.conditions_paiement && (
            <p className="text-xs" style={{ color: "#5A635D" }}>Conditions de paiement : {devis.conditions_paiement}</p>
          )}

          {devis.mentions_legales.length > 0 && (
            <ul className="text-xs space-y-0.5" style={{ color: "#9CA3AF" }}>
              {devis.mentions_legales.map((m, i) => <li key={i}>• {m}</li>)}
            </ul>
          )}

          {(devis.artisan.assurance_nom || devis.artisan.assurance_contrat) && (
            <p className="text-xs" style={{ color: "#9CA3AF" }}>
              Assurance : {devis.artisan.assurance_nom}
              {devis.artisan.assurance_contrat ? ` — n° ${devis.artisan.assurance_contrat}` : ""}
            </p>
          )}
        </div>

        {devis.signable && !actionDone && (
          <div className="bg-white rounded-2xl p-5 space-y-4"
            style={{ border: "0.5px solid rgba(20,83,45,0.12)", boxShadow: "0 4px 24px rgba(0,0,0,0.06)" }}>
            <h2 className="font-bold" style={{ color: "#18211C" }}>Votre réponse</h2>
            {!showRefuseConfirm ? (
              <>
                <div className="space-y-1">
                  <label className="text-xs font-semibold" style={{ color: "#5A635D" }}>Votre nom</label>
                  <input type="text" value={nom} onChange={e => setNom(e.target.value)}
                    placeholder="Jean Dupont" className="input-field" disabled={submitting} />
                </div>
                <label className="flex items-start gap-2 text-sm" style={{ color: "#18211C" }}>
                  <input type="checkbox" checked={accepteConditions} disabled={submitting}
                    onChange={e => setAccepteConditions(e.target.checked)}
                    className="mt-1 w-4 h-4 shrink-0" style={{ accentColor: "#14532D" }} />
                  <span>Je reconnais avoir pris connaissance de ce devis et j&apos;appose ma signature électronique valant &laquo;&nbsp;Bon pour accord&nbsp;&raquo;.</span>
                </label>
                <SignaturePad onChange={setSignatureDataUrl} />
                {formError && (
                  <p className="text-xs rounded-lg px-3 py-2" style={{ backgroundColor: "#FEF2F2", color: "#B91C1C" }}>{formError}</p>
                )}
                <div className="flex flex-col sm:flex-row gap-2">
                  <button onClick={handleAccept} disabled={submitting}
                    className="btn-primary flex-1 flex items-center justify-center gap-2">
                    {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
                    Bon pour accord
                  </button>
                  <button onClick={() => setShowRefuseConfirm(true)} disabled={submitting}
                    className="flex-1 text-sm rounded-xl py-2.5 font-medium transition-colors"
                    style={{ border: "0.5px solid rgba(185,28,28,0.3)", color: "#B91C1C" }}>
                    Refuser ce devis
                  </button>
                </div>
              </>
            ) : (
              <div className="space-y-3">
                <p className="text-sm" style={{ color: "#5A635D" }}>Confirmez-vous que vous souhaitez refuser ce devis ?</p>
                {formError && (
                  <p className="text-xs rounded-lg px-3 py-2" style={{ backgroundColor: "#FEF2F2", color: "#B91C1C" }}>{formError}</p>
                )}
                <div className="flex flex-col sm:flex-row gap-2">
                  <button onClick={handleRefuse} disabled={submitting}
                    className="flex-1 text-sm rounded-xl py-2.5 font-bold text-white transition-colors"
                    style={{ backgroundColor: "#B91C1C", opacity: submitting ? 0.6 : 1 }}>
                    {submitting ? "…" : "Confirmer le refus"}
                  </button>
                  <button onClick={() => setShowRefuseConfirm(false)} disabled={submitting}
                    className="flex-1 text-sm rounded-xl py-2.5 font-medium"
                    style={{ border: "0.5px solid rgba(20,83,45,0.15)", color: "#5A635D" }}>
                    Annuler
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
