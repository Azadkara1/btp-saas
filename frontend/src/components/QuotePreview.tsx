"use client";
import { useState, useMemo, Fragment, useRef } from "react";
import { Pencil, Plus, Trash2, RotateCcw } from "lucide-react";
import { Devis, LigneDevis, TotauxDevis } from "@/lib/types";
import ModelPicker from "@/components/ModelPicker";

interface QuotePreviewProps {
  devis: Devis;
  documentType: "devis" | "facture";
  withTva: boolean;
  documentDate: string;
  onUpdate: (updated: Devis) => void;
}

function fmtDate(iso: string): string {
  if (!iso) return "";
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}

const SOURCE_BADGE: Record<string, { label: string; color: string }> = {
  artisan:          { label: "Votre prix",  color: "bg-green-100 text-green-700" },
  recherche_marche: { label: "Prix marché", color: "bg-blue-100 text-blue-700" },
  estimation:       { label: "Estimation",  color: "bg-yellow-100 text-yellow-700" },
};

const TVA_OPTIONS = [5.5, 10, 20];

function round2(n: number) { return Math.round(n * 100) / 100; }

function fmtMoney(amount: number): string {
  return amount.toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " €";
}

// T4 : (l.quantite ?? 1) partout dans les calculs
function computeTotaux(
  lignes: LigneDevis[],
  withTva: boolean,
  remise_type?: string | null,
  remise_valeur?: number | null,
  acompte?: number | null,
): TotauxDevis {
  const total_ht = round2(lignes.reduce((s, l) => s + (l.quantite ?? 1) * l.prix_unitaire_ht, 0));

  let remise_ht = 0;
  if (remise_type === "pourcentage" && remise_valeur)
    remise_ht = round2(total_ht * remise_valeur / 100);
  else if (remise_type === "montant_fixe" && remise_valeur)
    remise_ht = round2(Math.min(remise_valeur, total_ht));

  const total_ht_net = round2(total_ht - remise_ht);

  let total_tva = 0;
  if (withTva) {
    const ratio = total_ht > 0 ? total_ht_net / total_ht : 1;
    total_tva = round2(
      lignes.reduce((s, l) => s + (l.quantite ?? 1) * l.prix_unitaire_ht * l.tva_taux / 100, 0) * ratio
    );
  }

  const total_ttc   = round2(total_ht_net + total_tva);
  const net_a_payer = round2(Math.max(0, total_ttc - (acompte || 0)));
  return { total_ht, total_tva, total_ttc, remise_ht, total_ht_net, net_a_payer };
}

// ── Cellule texte éditable ──────────────────────────────────────
function EditableText({
  value, onChange, className = "", multiline = false, allowEmpty = false,
}: { value: string; onChange: (v: string) => void; className?: string; multiline?: boolean; allowEmpty?: boolean }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const commit = () => {
    const v = draft.trim();
    if (v || allowEmpty) onChange(v);
    setEditing(false);
  };
  if (editing) {
    if (multiline)
      return <textarea value={draft} autoFocus rows={3}
        onChange={e => setDraft(e.target.value)} onBlur={commit}
        onKeyDown={e => { if (e.key === "Escape") setEditing(false); }}
        className={`border border-blue-400 rounded px-1.5 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400 w-full resize-none ${className}`} />;
    return <input type="text" value={draft} autoFocus
      onChange={e => setDraft(e.target.value)} onBlur={commit}
      onKeyDown={e => { if (e.key === "Enter") commit(); if (e.key === "Escape") setEditing(false); }}
      className={`border border-blue-400 rounded px-1.5 py-0.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400 w-full ${className}`} />;
  }
  return (
    <button type="button" onClick={() => { setDraft(value); setEditing(true); }} title="Modifier"
      className={`group inline-flex items-start gap-1 hover:text-blue-600 rounded px-1 py-0.5 hover:bg-blue-50 transition-colors text-left w-full ${className}`}>
      <span className="flex-1">{value}</span>
      <Pencil className="w-3 h-3 opacity-0 group-hover:opacity-50 flex-shrink-0 mt-0.5" />
    </button>
  );
}

// ── Cellule numérique éditable ──────────────────────────────────
function EditableNumber({
  value, onChange, step = "1", className = "",
}: { value: number; onChange: (v: number) => void; step?: string; className?: string }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const commit = () => { const v = parseFloat(draft); if (!isNaN(v) && v >= 0) onChange(v); setEditing(false); };
  if (editing)
    return <input type="number" value={draft} min="0" step={step} autoFocus
      onChange={e => setDraft(e.target.value)} onBlur={commit}
      onKeyDown={e => { if (e.key === "Enter") commit(); if (e.key === "Escape") setEditing(false); }}
      className={`w-20 border border-blue-400 rounded px-1.5 py-0.5 text-sm text-right focus:outline-none focus:ring-1 focus:ring-blue-400 ${className}`} />;
  return (
    <button type="button" onClick={() => { setDraft(value.toString()); setEditing(true); }} title="Modifier"
      className={`group inline-flex items-center justify-end gap-1 hover:text-blue-600 rounded px-1 py-0.5 hover:bg-blue-50 transition-colors w-full ${className}`}>
      <span>{step === "0.01" ? value.toFixed(2) : value}</span>
      <Pencil className="w-3 h-3 opacity-0 group-hover:opacity-50 flex-shrink-0" />
    </button>
  );
}

// ── Ligne de prestation ─────────────────────────────────────────
// T3 : onDelete + canDelete ; T4 : quantite null → "au réel"
function LigneRow({
  ligne, withTva, onUpdate, onDelete, canDelete,
}: {
  ligne: LigneDevis;
  withTva: boolean;
  onUpdate: (field: string, value: number | string | null) => void;
  onDelete: () => void;
  canDelete: boolean;
}) {
  const qty = ligne.quantite ?? 1;
  const montantHt = round2(qty * ligne.prix_unitaire_ht);
  const badge = SOURCE_BADGE[ligne.source_prix] || SOURCE_BADGE.estimation;

  // T4 : édition inline de la quantité avec support null
  const [editingQty, setEditingQty] = useState(false);
  const [qtyDraft, setQtyDraft] = useState("");

  const commitQty = () => {
    const v = parseFloat(qtyDraft);
    if (!isNaN(v) && v > 0) {
      onUpdate("quantite", v);
    } else if (qtyDraft.trim() === "") {
      onUpdate("quantite", null); // au réel
    }
    setEditingQty(false);
  };

  return (
    <tr className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
      {/* Prestation + Description + badges */}
      <td className="py-3 px-2">
        <EditableText value={ligne.poste} onChange={v => onUpdate("poste", v)}
          className="font-medium text-gray-900 text-sm" />
        <EditableText value={ligne.description} onChange={v => onUpdate("description", v)} multiline
          className="text-xs text-gray-500 mt-0.5" />
        <div className="flex items-center gap-2 mt-1 flex-wrap">
          <span className={`inline-block text-xs px-2 py-0.5 rounded-full ${badge.color}`}>{badge.label}</span>
          <EditableText value={ligne.lot || "— lot"} onChange={v => onUpdate("lot", v === "— lot" ? "" : v)}
            className="text-xs text-slate-500 bg-slate-100 rounded-full px-2 py-0.5" />
          {/* T3 : bouton suppression par ligne */}
          {canDelete && (
            <button type="button" onClick={onDelete} title="Supprimer cette ligne"
              className="text-red-300 hover:text-red-500 transition-colors ml-auto">
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </td>
      {/* Quantité — T4 : null = "au réel" */}
      <td className="py-3 px-2 text-center text-sm text-gray-600 whitespace-nowrap">
        {editingQty ? (
          <input type="number" value={qtyDraft} autoFocus min="0" step="0.5"
            onChange={e => setQtyDraft(e.target.value)}
            onBlur={commitQty}
            onKeyDown={e => { if (e.key === "Enter") commitQty(); if (e.key === "Escape") setEditingQty(false); }}
            placeholder="vide = au réel"
            className="w-20 border border-blue-400 rounded px-1.5 py-0.5 text-sm text-center focus:outline-none focus:ring-1 focus:ring-blue-400" />
        ) : ligne.quantite === null ? (
          <button type="button" onClick={() => { setQtyDraft(""); setEditingQty(true); }}
            title="Cliquer pour définir une quantité (laisser vide = au réel)"
            className="text-xs text-gray-400 italic hover:text-blue-600 transition-colors px-1 border-b border-dashed border-gray-300">
            au réel
          </button>
        ) : (
          <div className="flex items-center justify-center gap-0.5">
            <button type="button" onClick={() => { setQtyDraft(String(ligne.quantite)); setEditingQty(true); }}
              className="group inline-flex items-center gap-0.5 hover:text-blue-600 rounded px-1 py-0.5 hover:bg-blue-50 transition-colors">
              <span>{Number.isInteger(ligne.quantite) ? ligne.quantite : ligne.quantite}</span>
              <Pencil className="w-3 h-3 opacity-0 group-hover:opacity-50" />
            </button>
            <button type="button" onClick={() => onUpdate("quantite", null)}
              title="Passer en 'au réel' (quantité variable)"
              className="text-gray-300 hover:text-gray-500 transition-colors text-xs leading-none">
              ×
            </button>
          </div>
        )}
      </td>
      {/* Unité */}
      <td className="py-3 px-2 text-center text-sm text-gray-500 whitespace-nowrap">
        <EditableText value={ligne.unite} onChange={v => onUpdate("unite", v)}
          className="text-xs text-gray-400 min-w-[28px]" />
      </td>
      {/* PU HT */}
      <td className="py-3 px-2 text-right text-sm text-gray-600 whitespace-nowrap">
        <div className="flex items-center justify-end gap-0.5">
          <EditableNumber value={ligne.prix_unitaire_ht} onChange={v => onUpdate("prix_unitaire_ht", v)} step="0.01" />
          <span className="text-xs text-gray-400">€</span>
        </div>
      </td>
      {/* TVA */}
      {withTva && (
        <td className="py-3 px-2 text-center text-sm text-gray-500">
          <select value={ligne.tva_taux} onChange={e => onUpdate("tva_taux", parseFloat(e.target.value))}
            className="border border-transparent hover:border-gray-300 focus:border-blue-400 rounded px-1 py-0.5 text-sm bg-transparent cursor-pointer focus:outline-none">
            {TVA_OPTIONS.map(t => <option key={t} value={t}>{t}%</option>)}
          </select>
        </td>
      )}
      {/* Total HT — back-calcule PU HT ; T4 : qty = null → 1 */}
      <td className="py-3 px-2 text-right font-semibold text-gray-900 whitespace-nowrap">
        <div className="flex items-center justify-end gap-0.5">
          <EditableNumber value={montantHt}
            onChange={newTotal => {
              const q = ligne.quantite ?? 1;
              if (q > 0) onUpdate("prix_unitaire_ht", round2(newTotal / q));
            }}
            step="0.01" className="font-semibold" />
          <span className="text-xs text-gray-500">€</span>
        </div>
      </td>
    </tr>
  );
}

// ── Composant principal ─────────────────────────────────────────
export default function QuotePreview({ devis, documentType, withTva, documentDate, onUpdate }: QuotePreviewProps) {
  const [lignes, setLignes]             = useState<LigneDevis[]>(devis.lignes);
  const [remiseType, setRemiseType]     = useState<string>(devis.remise_type || "");
  const [remiseValeur, setRemiseValeur] = useState<number>(devis.remise_valeur || 0);
  const [acompte, setAcompte]           = useState<number>(devis.acompte || 0);
  const [currentModele, setCurrentModele] = useState<string>(devis.modele || "moderne");
  const [chantierDesc, setChantierDesc] = useState<string>(devis.chantier.description || "");

  // T1+T2 : état local pour les champs éditables post-génération
  const [localValiditeJours, setLocalValiditeJours]         = useState<number | null>(devis.validite_jours ?? null);
  const [localConditionsPaiement, setLocalConditionsPaiement] = useState<string>(devis.conditions_paiement || "");
  const [localMentions, setLocalMentions]                   = useState<string[]>([...devis.mentions_legales]);
  const [mentionsEditedByUser, setMentionsEditedByUser]     = useState(false);
  // Conserve les mentions Claude originales pour le bouton "Régénérer"
  const originalMentionsRef = useRef<string[]>([...devis.mentions_legales]);

  // TTC éditable
  const [editingTtc, setEditingTtc] = useState(false);
  const [ttcDraft, setTtcDraft]     = useState("");

  const totaux = useMemo(
    () => computeTotaux(lignes, withTva, remiseType || null, remiseValeur || null, acompte || null),
    [lignes, withTva, remiseType, remiseValeur, acompte]
  );

  const hasLots   = useMemo(() => lignes.some(l => l.lot), [lignes]);
  const lotGroups = useMemo(() => {
    const map = new Map<string, { lot: string; entries: { ligne: LigneDevis; index: number }[] }>();
    lignes.forEach((ligne, index) => {
      const key = ligne.lot || "";
      if (!map.has(key)) map.set(key, { lot: ligne.lot || "", entries: [] });
      map.get(key)!.entries.push({ ligne, index });
    });
    return Array.from(map.values());
  }, [lignes]);

  // _buildDevis inclut désormais tous les champs locaux (T1+T2)
  const _buildDevis = (l: LigneDevis[], rt: string, rv: number, ac: number, mod?: string) => ({
    ...devis,
    chantier: { ...devis.chantier, description: chantierDesc },
    lignes: l,
    totaux: computeTotaux(l, withTva, rt || null, rv || null, ac || null),
    remise_type:          rt || null,
    remise_valeur:        rv || null,
    acompte:              ac || null,
    modele:               mod ?? currentModele,
    validite_jours:       localValiditeJours,
    conditions_paiement:  localConditionsPaiement || null,
    mentions_legales:     localMentions,
  });

  // T4 : field accepte null pour quantite
  const updateLigne = (index: number, field: string, value: number | string | null) => {
    const updated = lignes.map((l, i) => i === index ? { ...l, [field]: value } : l);
    setLignes(updated);
    onUpdate(_buildDevis(updated, remiseType, remiseValeur, acompte));
  };

  // T3 : ajout d'une ligne (lot = nom du lot cible ou null)
  const addLigne = (lot: string | null = null) => {
    const newLigne: LigneDevis = {
      lot: lot || null,
      poste: "Nouvelle prestation",
      description: "À compléter",
      quantite: 1,
      unite: "forfait",
      prix_unitaire_ht: 0,
      tva_taux: 10,
      source_prix: "estimation",
    };
    const updated = [...lignes, newLigne];
    setLignes(updated);
    onUpdate(_buildDevis(updated, remiseType, remiseValeur, acompte));
  };

  // T3 : suppression d'une ligne (garde au moins 1)
  const removeLigne = (index: number) => {
    if (lignes.length <= 1) return;
    const updated = lignes.filter((_, i) => i !== index);
    setLignes(updated);
    onUpdate(_buildDevis(updated, remiseType, remiseValeur, acompte));
  };

  const handleRemiseType = (v: string) => {
    const rv = v ? remiseValeur : 0;
    setRemiseType(v);
    if (!v) setRemiseValeur(0);
    onUpdate(_buildDevis(lignes, v, rv, acompte));
  };

  const handleRemiseValeur = (v: number) => {
    setRemiseValeur(v);
    onUpdate(_buildDevis(lignes, remiseType, v, acompte));
  };

  const handleAcompte = (v: number) => {
    setAcompte(v);
    onUpdate(_buildDevis(lignes, remiseType, remiseValeur, v));
  };

  const handleModele = (m: string) => {
    setCurrentModele(m);
    onUpdate(_buildDevis(lignes, remiseType, remiseValeur, acompte, m));
  };

  // T2 : handlers champs éditables — override après _buildDevis car closure a l'ancienne valeur
  const handleValiditeJours = (val: number | null) => {
    setLocalValiditeJours(val);
    onUpdate({ ..._buildDevis(lignes, remiseType, remiseValeur, acompte), validite_jours: val });
  };

  const handleConditionsPaiement = (val: string) => {
    setLocalConditionsPaiement(val);
    onUpdate({ ..._buildDevis(lignes, remiseType, remiseValeur, acompte), conditions_paiement: val || null });
  };

  const handleMentionChange = (index: number, value: string) => {
    const updated = localMentions.map((m, i) => i === index ? value : m);
    setLocalMentions(updated);
    setMentionsEditedByUser(true);
    onUpdate({ ..._buildDevis(lignes, remiseType, remiseValeur, acompte), mentions_legales: updated });
  };

  const handleAddMention = () => {
    const updated = [...localMentions, "Nouvelle mention légale"];
    setLocalMentions(updated);
    setMentionsEditedByUser(true);
    onUpdate({ ..._buildDevis(lignes, remiseType, remiseValeur, acompte), mentions_legales: updated });
  };

  const handleRemoveMention = (index: number) => {
    const updated = localMentions.filter((_, i) => i !== index);
    setLocalMentions(updated);
    setMentionsEditedByUser(true);
    onUpdate({ ..._buildDevis(lignes, remiseType, remiseValeur, acompte), mentions_legales: updated });
  };

  const handleRegenerMentions = () => {
    const orig = [...originalMentionsRef.current];
    setLocalMentions(orig);
    setMentionsEditedByUser(false);
    onUpdate({ ..._buildDevis(lignes, remiseType, remiseValeur, acompte), mentions_legales: orig });
  };

  // Valeur TTC / HT courante affichée dans le bandeau principal
  const currentTtcDisplay = withTva ? totaux.total_ttc : (totaux.total_ht_net ?? totaux.total_ht);

  const commitTtc = () => {
    const newTtc = parseFloat(ttcDraft);
    if (isNaN(newTtc) || newTtc <= 0 || currentTtcDisplay <= 0) { setEditingTtc(false); return; }
    const ratio = newTtc / currentTtcDisplay;
    const scaled = lignes.map(l => ({
      ...l,
      prix_unitaire_ht: round2(l.prix_unitaire_ht * ratio),
    }));
    // Absorber l'écart d'arrondi centimes sur la dernière ligne
    const scaledTotaux = computeTotaux(scaled, withTva, remiseType || null, remiseValeur || null, acompte || null);
    const actual = withTva ? scaledTotaux.total_ttc : (scaledTotaux.total_ht_net ?? scaledTotaux.total_ht);
    const diff = round2(newTtc - actual);
    if (diff !== 0 && scaled.length > 0) {
      const lastIdx = scaled.length - 1;
      const last = scaled[lastIdx];
      // T4 : quantite null → 1 pour l'ajustement
      const q = last.quantite ?? 1;
      if (q > 0) {
        const tvaMult = withTva ? (1 + last.tva_taux / 100) : 1;
        scaled[lastIdx] = {
          ...last,
          prix_unitaire_ht: round2(last.prix_unitaire_ht + diff / (q * tvaMult)),
        };
      }
    }
    setLignes(scaled);
    onUpdate(_buildDevis(scaled, remiseType, remiseValeur, acompte));
    setEditingTtc(false);
  };

  const docLabel = documentType === "facture" ? "Facture" : "Devis";
  const colCount = withTva ? 6 : 5;  // Prestation | Qté | Unité | PU HT | [TVA] | Total HT

  return (
    <div className="card space-y-6">
      {/* En-tête */}
      <div className="flex justify-between items-start flex-wrap gap-4">
        <div>
          <h2 className="text-xl font-bold" style={{ color: "#18211C" }}>
            {devis.artisan.nom || "Votre Entreprise"}
          </h2>
          {devis.artisan.siret     && <p className="text-sm" style={{ color: "#5A635D" }}>SIRET : {devis.artisan.siret}</p>}
          {devis.artisan.adresse   && <p className="text-sm" style={{ color: "#5A635D" }}>{devis.artisan.adresse}</p>}
          {(devis.artisan.code_postal || devis.artisan.ville) && (
            <p className="text-sm" style={{ color: "#5A635D" }}>
              {[devis.artisan.code_postal, devis.artisan.ville].filter(Boolean).join(" ")}
            </p>
          )}
          {devis.artisan.telephone && <p className="text-sm" style={{ color: "#5A635D" }}>{devis.artisan.telephone}</p>}
          {devis.artisan.email     && <p className="text-sm" style={{ color: "#5A635D" }}>{devis.artisan.email}</p>}
          {devis.artisan.site_web  && <p className="text-xs" style={{ color: "#7C857F" }}>{devis.artisan.site_web}</p>}
          {devis.artisan.iban      && <p className="text-xs" style={{ color: "#7C857F" }}>IBAN : {devis.artisan.iban}</p>}
          {devis.artisan.bic       && <p className="text-xs" style={{ color: "#7C857F" }}>BIC : {devis.artisan.bic}</p>}
        </div>
        <div className="text-right space-y-2">
          <div className="text-2xl font-black uppercase tracking-tight" style={{ color: "#14532D" }}>
            {docLabel}
          </div>
          <div className="text-sm" style={{ color: "#7C857F" }}>{fmtDate(documentDate)}</div>
          {/* T1+T2 : validite_jours visible et éditable sous la date */}
          {documentType === "devis" && (
            <div className="flex items-center justify-end gap-1 text-xs" style={{ color: "#7C857F" }}>
              <span>Valable</span>
              <input
                type="number"
                min="1"
                max="365"
                value={localValiditeJours ?? ""}
                onChange={e => {
                  const v = parseInt(e.target.value);
                  handleValiditeJours(isNaN(v) || v <= 0 ? null : v);
                }}
                placeholder="—"
                title="Durée de validité du devis en jours"
                className="w-12 text-right bg-transparent border-b outline-none text-xs appearance-none"
                style={{ borderColor: "rgba(20,83,45,0.3)", color: "#5A635D" }}
              />
              <span>jours</span>
            </div>
          )}
          {/* Bascule Modèle */}
          <div className="flex justify-end">
            <ModelPicker value={currentModele} onChange={handleModele} compact={true} />
          </div>
        </div>
      </div>

      {/* Client + Chantier */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {devis.client.nom && (
          <div className="rounded-xl p-4" style={{ backgroundColor: "#F0F7F3", borderLeft: "4px solid #14532D" }}>
            <div className="text-xs font-semibold uppercase tracking-wide mb-1" style={{ color: "#14532D" }}>Client</div>
            <div className="font-semibold" style={{ color: "#18211C" }}>{devis.client.nom}</div>
            {devis.client.adresse && <div className="text-sm" style={{ color: "#5A635D" }}>{devis.client.adresse}</div>}
            {(devis.client.code_postal || devis.client.ville) && (
              <div className="text-sm" style={{ color: "#5A635D" }}>
                {[devis.client.code_postal, devis.client.ville].filter(Boolean).join(" ")}
              </div>
            )}
          </div>
        )}
        <div className="rounded-xl p-4 bg-amber-50" style={{ borderLeft: "4px solid #F59E0B" }}>
          <div className="text-xs font-semibold uppercase tracking-wide mb-1 text-amber-600">Chantier</div>
          <EditableText
            value={chantierDesc}
            onChange={v => {
              setChantierDesc(v);
              onUpdate({
                ..._buildDevis(lignes, remiseType, remiseValeur, acompte),
                chantier: { ...devis.chantier, description: v },
              });
            }}
            multiline
            className="text-sm text-gray-700"
          />
        </div>
      </div>

      <p className="text-xs flex items-center gap-1.5" style={{ color: "#7C857F" }}>
        <Pencil className="w-3 h-3" />
        Cliquez sur n'importe quelle valeur pour la modifier · × sur la Qté = "au réel" · <Trash2 className="w-3 h-3 inline" /> = supprimer la ligne
      </p>

      {/* Tableau */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr style={{ backgroundColor: "#14532D", color: "#FFFFFF" }}>
              <th className="py-3 px-2 text-left font-semibold">Prestation</th>
              <th className="py-3 px-2 text-center font-semibold">Qté</th>
              <th className="py-3 px-2 text-center font-semibold">Unité</th>
              <th className="py-3 px-2 text-right font-semibold">PU HT</th>
              {withTva && <th className="py-3 px-2 text-center font-semibold">TVA</th>}
              <th className="py-3 px-2 text-right font-semibold">Total HT</th>
            </tr>
          </thead>
          <tbody>
            {hasLots ? (
              lotGroups.map(({ lot, entries }) => (
                <Fragment key={lot || "__no_lot__"}>
                  {lot && (
                    <tr style={{ backgroundColor: "#E3EDE6" }}>
                      <td colSpan={colCount} className="py-2 px-3 font-semibold text-sm"
                        style={{ color: "#14532D" }}>
                        {lot}
                      </td>
                    </tr>
                  )}
                  {entries.map(({ ligne, index }) => (
                    <LigneRow key={index} ligne={ligne} withTva={withTva}
                      onUpdate={(field, value) => updateLigne(index, field, value)}
                      onDelete={() => removeLigne(index)}
                      canDelete={lignes.length > 1} />
                  ))}
                  {/* T3 : bouton ajouter dans ce lot */}
                  <tr>
                    <td colSpan={colCount} className="px-2 py-1.5">
                      <button type="button"
                        onClick={() => addLigne(lot || null)}
                        className="flex items-center gap-1 text-xs px-2 py-1 rounded-lg transition-colors"
                        style={{ color: "#14532D", border: "1px dashed rgba(20,83,45,0.35)" }}
                        onMouseOver={e => (e.currentTarget.style.backgroundColor = "#E3EDE6")}
                        onMouseOut={e => (e.currentTarget.style.backgroundColor = "transparent")}>
                        <Plus className="w-3 h-3" />
                        {lot ? `Ajouter dans ${lot}` : "Ajouter une ligne (sans lot)"}
                      </button>
                    </td>
                  </tr>
                  {lotGroups.length > 1 && (
                    <tr className="border-b-2 border-gray-300" style={{ backgroundColor: "#F8FAFB" }}>
                      <td colSpan={colCount - 1} className="py-2 px-3 text-right text-sm text-gray-500 italic">
                        {lot ? `Sous-total ${lot}` : "Sous-total"}
                      </td>
                      {/* T4 : (l.quantite ?? 1) dans le sous-total */}
                      <td className="py-2 px-3 text-right text-sm font-semibold text-gray-900">
                        {fmtMoney(round2(entries.reduce((s, { ligne }) => s + (ligne.quantite ?? 1) * ligne.prix_unitaire_ht, 0)))}
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))
            ) : (
              lignes.map((ligne, i) => (
                <LigneRow key={i} ligne={ligne} withTva={withTva}
                  onUpdate={(field, value) => updateLigne(i, field, value)}
                  onDelete={() => removeLigne(i)}
                  canDelete={lignes.length > 1} />
              ))
            )}
          </tbody>
        </table>
        {/* T3 : bouton ajouter (mode sans lots) */}
        {!hasLots && (
          <div className="mt-2 px-2">
            <button type="button"
              onClick={() => addLigne(null)}
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg transition-colors"
              style={{ color: "#14532D", border: "1px dashed rgba(20,83,45,0.35)" }}
              onMouseOver={e => (e.currentTarget.style.backgroundColor = "#E3EDE6")}
              onMouseOut={e => (e.currentTarget.style.backgroundColor = "transparent")}>
              <Plus className="w-3 h-3" />
              Ajouter une ligne
            </button>
          </div>
        )}
      </div>

      {/* Totaux */}
      <div className="flex justify-end">
        <div className="w-full sm:w-80 rounded-xl overflow-hidden" style={{ border: "0.5px solid rgba(20,83,45,0.15)" }}>

          {/* Total HT brut */}
          <div className="flex justify-between px-4 py-2.5 text-sm bg-white">
            <span style={{ color: "#5A635D" }}>{remiseType ? "Total HT brut" : "Total HT"}</span>
            <span className="font-semibold" style={{ color: "#18211C" }}>{fmtMoney(totaux.total_ht)}</span>
          </div>

          {/* Remise */}
          <div className="flex items-center justify-between px-4 py-2 text-sm border-t border-gray-100 gap-2 bg-white">
            <span style={{ color: "#5A635D" }} className="flex-shrink-0">Remise</span>
            <div className="flex items-center gap-1.5 ml-auto flex-wrap justify-end">
              <select value={remiseType} onChange={e => handleRemiseType(e.target.value)}
                className="text-xs border border-gray-300 rounded px-1.5 py-0.5 bg-white">
                <option value="">Aucune</option>
                <option value="pourcentage">%</option>
                <option value="montant_fixe">€ fixe</option>
              </select>
              {remiseType && (
                <input type="number" value={remiseValeur || ""} min="0" step="0.01"
                  onChange={e => handleRemiseValeur(parseFloat(e.target.value) || 0)}
                  className="w-16 text-xs border border-gray-300 rounded px-1.5 py-0.5 text-right bg-white" />
              )}
              {(totaux.remise_ht ?? 0) > 0 && (
                <span className="text-red-600 font-semibold whitespace-nowrap text-xs">
                  - {fmtMoney(totaux.remise_ht ?? 0)}
                </span>
              )}
            </div>
          </div>

          {/* Total HT net */}
          {(totaux.remise_ht ?? 0) > 0 && (
            <div className="flex justify-between px-4 py-2 text-sm border-t border-gray-100 bg-white">
              <span style={{ color: "#5A635D" }}>Total HT net</span>
              <span className="font-semibold">{fmtMoney(totaux.total_ht_net ?? totaux.total_ht)}</span>
            </div>
          )}

          {/* TVA */}
          {withTva && (
            <div className="flex justify-between px-4 py-2.5 text-sm border-t border-gray-100 bg-white">
              <span style={{ color: "#5A635D" }}>Total TVA</span>
              <span>{fmtMoney(totaux.total_tva)}</span>
            </div>
          )}

          {/* TOTAL TTC / HT — éditable */}
          <div className="flex justify-between items-center px-4 py-3.5 font-bold text-base"
            style={{ backgroundColor: "#14532D", color: "#FFFFFF" }}>
            <span>{withTva ? "TOTAL TTC" : "TOTAL HT"}</span>
            {editingTtc ? (
              <input type="number" value={ttcDraft} autoFocus min="0" step="0.01"
                onChange={e => setTtcDraft(e.target.value)}
                onBlur={commitTtc}
                onKeyDown={e => { if (e.key === "Enter") commitTtc(); if (e.key === "Escape") setEditingTtc(false); }}
                className="w-28 text-right bg-transparent border-b border-white focus:outline-none text-white placeholder-green-300"
                style={{ borderBottom: "1px solid rgba(255,255,255,0.6)" }} />
            ) : (
              <button type="button"
                onClick={() => { setTtcDraft(currentTtcDisplay.toFixed(2)); setEditingTtc(true); }}
                title="Cliquer pour ajuster le total (redimensionne tous les PU)"
                className="group flex items-center gap-1.5 hover:opacity-80 transition-opacity">
                <span>{fmtMoney(currentTtcDisplay)}</span>
                <Pencil className="w-3.5 h-3.5 opacity-50 group-hover:opacity-100" />
              </button>
            )}
          </div>

          {/* Acompte */}
          <div className="flex items-center justify-between px-4 py-2 text-sm border-t border-gray-100 gap-2 bg-white">
            <span style={{ color: "#5A635D" }} className="flex-shrink-0">Acompte versé</span>
            <div className="flex items-center gap-1">
              <input type="number" value={acompte || ""} min="0" step="0.01" placeholder="0"
                onChange={e => handleAcompte(parseFloat(e.target.value) || 0)}
                className="w-20 text-xs border border-gray-300 rounded px-1.5 py-0.5 text-right bg-white" />
              <span className="text-xs text-gray-400">€</span>
            </div>
          </div>

          {/* NET À PAYER */}
          {acompte > 0 && (
            <div className="flex justify-between px-4 py-3 font-bold text-sm text-white"
              style={{ backgroundColor: "#047857" }}>
              <span>NET À PAYER</span>
              <span>{fmtMoney(totaux.net_a_payer ?? totaux.total_ttc)}</span>
            </div>
          )}
        </div>
      </div>

      {/* T2 : Conditions de paiement éditables */}
      <div className="border-t pt-3" style={{ borderColor: "rgba(20,83,45,0.1)" }}>
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold shrink-0" style={{ color: "#5A635D" }}>
            Conditions de paiement :
          </span>
          <input
            type="text"
            value={localConditionsPaiement}
            onChange={e => setLocalConditionsPaiement(e.target.value)}
            onBlur={() => handleConditionsPaiement(localConditionsPaiement)}
            placeholder="Ex : 30% à la commande, solde à réception"
            className="text-xs flex-1 bg-transparent border-b outline-none focus:border-green-600"
            style={{ borderColor: "rgba(20,83,45,0.2)", color: "#5A635D" }}
          />
        </div>
      </div>

      {/* T2 : Mentions légales éditables */}
      <div className="border-t pt-4" style={{ borderColor: "rgba(20,83,45,0.1)" }}>
        <div className="flex items-center justify-between mb-2 gap-2 flex-wrap">
          <span className="text-xs font-semibold" style={{ color: "#5A635D" }}>Mentions légales</span>
          <div className="flex items-center gap-2">
            {mentionsEditedByUser && (
              <button type="button" onClick={handleRegenerMentions}
                className="flex items-center gap-1 text-xs px-2 py-1 rounded-lg transition-colors"
                style={{ color: "#B45309", border: "1px solid rgba(180,83,9,0.3)", backgroundColor: "#FFFBEB" }}>
                <RotateCcw className="w-3 h-3" />
                Régénérer les mentions
              </button>
            )}
            <button type="button" onClick={handleAddMention}
              className="flex items-center gap-1 text-xs px-2 py-1 rounded-lg transition-colors"
              style={{ color: "#14532D", border: "1px dashed rgba(20,83,45,0.35)" }}
              onMouseOver={e => (e.currentTarget.style.backgroundColor = "#E3EDE6")}
              onMouseOut={e => (e.currentTarget.style.backgroundColor = "transparent")}>
              <Plus className="w-3 h-3" />
              Ajouter
            </button>
          </div>
        </div>
        <ul className="space-y-1">
          {localMentions.map((m, i) => (
            <li key={i} className="flex items-start gap-1 group/mention">
              <span className="text-xs mt-1.5 shrink-0" style={{ color: "#7C857F" }}>•</span>
              <EditableText value={m} onChange={v => handleMentionChange(i, v)} multiline
                className="text-xs flex-1" />
              <button type="button" onClick={() => handleRemoveMention(i)}
                title="Supprimer cette mention"
                className="opacity-0 group-hover/mention:opacity-100 text-gray-300 hover:text-red-400 transition-all mt-1 shrink-0">
                <Trash2 className="w-3 h-3" />
              </button>
            </li>
          ))}
          {!withTva && (
            <li className="flex items-start gap-1">
              <span className="text-xs mt-1" style={{ color: "#5A635D" }}>•</span>
              <span className="text-xs font-medium" style={{ color: "#5A635D" }}>TVA non applicable, art. 293 B du CGI</span>
            </li>
          )}
        </ul>
      </div>
    </div>
  );
}
