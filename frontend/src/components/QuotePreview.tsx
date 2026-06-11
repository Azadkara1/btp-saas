"use client";
/**
 * Aperçu du devis/facture généré.
 * - Quantité, PU HT et Total HT sont éditables en clic.
 * - TVA activable/désactivable globalement.
 * - Les totaux se recalculent en temps réel.
 */
import { useState, useMemo, Fragment } from "react";
import { Pencil } from "lucide-react";
import { Devis, LigneDevis, TotauxDevis } from "@/lib/types";

interface QuotePreviewProps {
  devis: Devis;
  documentType: "devis" | "facture";
  withTva: boolean;
  documentDate: string;           // format ISO "YYYY-MM-DD"
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

function round2(n: number) {
  return Math.round(n * 100) / 100;
}

function fmtMoney(amount: number): string {
  return amount.toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " €";
}

function computeTotaux(
  lignes: LigneDevis[],
  withTva: boolean,
  remise_type?: string | null,
  remise_valeur?: number | null,
  acompte?: number | null,
): TotauxDevis {
  const total_ht = round2(lignes.reduce((s, l) => s + l.quantite * l.prix_unitaire_ht, 0));

  let remise_ht = 0;
  if (remise_type === "pourcentage" && remise_valeur) {
    remise_ht = round2(total_ht * remise_valeur / 100);
  } else if (remise_type === "montant_fixe" && remise_valeur) {
    remise_ht = round2(Math.min(remise_valeur, total_ht));
  }
  const total_ht_net = round2(total_ht - remise_ht);

  let total_tva = 0;
  if (withTva) {
    const ratio = total_ht > 0 ? total_ht_net / total_ht : 1;
    total_tva = round2(
      lignes.reduce((s, l) => s + l.quantite * l.prix_unitaire_ht * l.tva_taux / 100, 0) * ratio
    );
  }

  const total_ttc = round2(total_ht_net + total_tva);
  const net_a_payer = round2(Math.max(0, total_ttc - (acompte || 0)));

  return { total_ht, total_tva, total_ttc, remise_ht, total_ht_net, net_a_payer };
}

/** Cellule texte — valeur normale, clic → input de saisie */
function EditableText({
  value, onChange, className = "", multiline = false,
}: {
  value: string; onChange: (v: string) => void; className?: string; multiline?: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");

  const commit = () => {
    const v = draft.trim();
    if (v) onChange(v);
    setEditing(false);
  };

  if (editing) {
    if (multiline) {
      return (
        <textarea
          value={draft}
          autoFocus
          rows={3}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => { if (e.key === "Escape") setEditing(false); }}
          className={`border border-blue-400 rounded px-1.5 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400 w-full resize-none ${className}`}
        />
      );
    }
    return (
      <input
        type="text"
        value={draft}
        autoFocus
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === "Enter") commit();
          if (e.key === "Escape") setEditing(false);
        }}
        className={`border border-blue-400 rounded px-1.5 py-0.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400 w-full ${className}`}
      />
    );
  }

  return (
    <button
      type="button"
      onClick={() => { setDraft(value); setEditing(true); }}
      title="Cliquer pour modifier"
      className={`group inline-flex items-start gap-1 hover:text-blue-600 rounded px-1 py-0.5 hover:bg-blue-50 transition-colors text-left w-full ${className}`}
    >
      <span className="flex-1">{value}</span>
      <Pencil className="w-3 h-3 opacity-0 group-hover:opacity-50 flex-shrink-0 mt-0.5" />
    </button>
  );
}

/** Cellule numérique — valeur normale, clic → input de saisie */
function EditableNumber({
  value, onChange, step = "1", className = "",
}: {
  value: number; onChange: (v: number) => void; step?: string; className?: string;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");

  const commit = () => {
    const v = parseFloat(draft);
    if (!isNaN(v) && v >= 0) onChange(v);
    setEditing(false);
  };

  if (editing) {
    return (
      <input
        type="number"
        value={draft}
        min="0"
        step={step}
        autoFocus
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === "Enter") commit();
          if (e.key === "Escape") setEditing(false);
        }}
        className={`w-20 border border-blue-400 rounded px-1.5 py-0.5 text-sm text-right focus:outline-none focus:ring-1 focus:ring-blue-400 ${className}`}
      />
    );
  }

  return (
    <button
      type="button"
      onClick={() => { setDraft(value.toString()); setEditing(true); }}
      title="Cliquer pour modifier"
      className={`group inline-flex items-center justify-end gap-1 hover:text-blue-600 rounded px-1 py-0.5 hover:bg-blue-50 transition-colors w-full ${className}`}
    >
      <span>{step === "0.01" ? value.toFixed(2) : value}</span>
      <Pencil className="w-3 h-3 opacity-0 group-hover:opacity-50 flex-shrink-0" />
    </button>
  );
}

function LigneRow({
  ligne, withTva, onUpdate,
}: {
  ligne: LigneDevis;
  withTva: boolean;
  onUpdate: (field: string, value: number | string) => void;
}) {
  const montantHt = round2(ligne.quantite * ligne.prix_unitaire_ht);
  const badge = SOURCE_BADGE[ligne.source_prix] || SOURCE_BADGE.estimation;

  return (
    <tr className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
      <td className="py-3 px-2">
        <EditableText
          value={ligne.poste}
          onChange={(v) => onUpdate("poste", v)}
          className="font-medium text-gray-900 text-sm"
        />
        <EditableText
          value={ligne.description}
          onChange={(v) => onUpdate("description", v)}
          multiline
          className="text-xs text-gray-500 mt-0.5"
        />
        <div className="flex items-center gap-2 mt-1 flex-wrap">
          <span className={`inline-block text-xs px-2 py-0.5 rounded-full ${badge.color}`}>
            {badge.label}
          </span>
          {/* Lot — éditable inline */}
          <EditableText
            value={ligne.lot || "— lot"}
            onChange={(v) => onUpdate("lot", v === "— lot" ? "" : v)}
            className="text-xs text-slate-500 bg-slate-100 rounded-full px-2 py-0.5"
          />
        </div>
      </td>

      {/* Quantité + Unité — éditables */}
      <td className="py-3 px-2 text-center text-sm text-gray-600 whitespace-nowrap">
        <div className="flex items-center justify-center gap-1">
          <EditableNumber
            value={ligne.quantite}
            onChange={(v) => onUpdate("quantite", v)}
            step="0.5"
          />
          <EditableText
            value={ligne.unite}
            onChange={(v) => onUpdate("unite", v)}
            className="text-xs text-gray-400 min-w-[28px]"
          />
        </div>
      </td>

      {/* PU HT — éditable */}
      <td className="py-3 px-2 text-right text-sm text-gray-600 whitespace-nowrap">
        <div className="flex items-center justify-end gap-0.5">
          <EditableNumber
            value={ligne.prix_unitaire_ht}
            onChange={(v) => onUpdate("prix_unitaire_ht", v)}
            step="0.01"
          />
          <span className="text-xs text-gray-400">€</span>
        </div>
      </td>

      {/* TVA — select, masqué si sans TVA */}
      {withTva && (
        <td className="py-3 px-2 text-center text-sm text-gray-500">
          <select
            value={ligne.tva_taux}
            onChange={(e) => onUpdate("tva_taux", parseFloat(e.target.value))}
            className="border border-transparent hover:border-gray-300 focus:border-blue-400 rounded px-1 py-0.5 text-sm bg-transparent cursor-pointer focus:outline-none"
          >
            {TVA_OPTIONS.map((t) => (
              <option key={t} value={t}>{t}%</option>
            ))}
          </select>
        </td>
      )}

      {/* Total HT — éditable, back-calcule le PU HT */}
      <td className="py-3 px-2 text-right font-semibold text-gray-900 whitespace-nowrap">
        <div className="flex items-center justify-end gap-0.5">
          <EditableNumber
            value={montantHt}
            onChange={(newTotal) => {
              if (ligne.quantite > 0) {
                onUpdate("prix_unitaire_ht", round2(newTotal / ligne.quantite));
              }
            }}
            step="0.01"
            className="font-semibold"
          />
          <span className="text-xs text-gray-500">€</span>
        </div>
      </td>
    </tr>
  );
}

export default function QuotePreview({ devis, documentType, withTva, documentDate, onUpdate }: QuotePreviewProps) {
  const [lignes, setLignes] = useState<LigneDevis[]>(devis.lignes);
  const [remiseType, setRemiseType] = useState<string>(devis.remise_type || "");
  const [remiseValeur, setRemiseValeur] = useState<number>(devis.remise_valeur || 0);
  const [acompte, setAcompte] = useState<number>(devis.acompte || 0);

  const totaux = useMemo(
    () => computeTotaux(lignes, withTva, remiseType || null, remiseValeur || null, acompte || null),
    [lignes, withTva, remiseType, remiseValeur, acompte]
  );

  // Groupement par LOT (order-preserving)
  const hasLots = useMemo(() => lignes.some(l => l.lot), [lignes]);
  const lotGroups = useMemo(() => {
    const map = new Map<string, { lot: string; entries: { ligne: LigneDevis; index: number }[] }>();
    lignes.forEach((ligne, index) => {
      const key = ligne.lot || "";
      if (!map.has(key)) map.set(key, { lot: ligne.lot || "", entries: [] });
      map.get(key)!.entries.push({ ligne, index });
    });
    return Array.from(map.values());
  }, [lignes]);

  const _buildDevis = (l: LigneDevis[], rt: string, rv: number, ac: number) => ({
    ...devis,
    lignes: l,
    totaux: computeTotaux(l, withTva, rt || null, rv || null, ac || null),
    remise_type: rt || null,
    remise_valeur: rv || null,
    acompte: ac || null,
  });

  const updateLigne = (index: number, field: string, value: number | string) => {
    const updated = lignes.map((l, i) => i === index ? { ...l, [field]: value } : l);
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

  const docLabel = documentType === "facture" ? "Facture" : "Devis";

  return (
    <div className="card space-y-6">
      {/* En-tête */}
      <div className="flex justify-between items-start flex-wrap gap-4">
        <div>
          <h2 className="text-xl font-bold text-gray-900">
            {devis.artisan.nom || "Votre Entreprise"}
          </h2>
          {devis.artisan.siret && (
            <p className="text-sm text-gray-500">SIRET : {devis.artisan.siret}</p>
          )}
          {devis.artisan.iban && (
            <p className="text-xs text-gray-400">IBAN : {devis.artisan.iban}</p>
          )}
          {devis.artisan.bic && (
            <p className="text-xs text-gray-400">BIC : {devis.artisan.bic}</p>
          )}
        </div>
        <div className="text-right">
          <div className="text-2xl font-black text-blue-700 uppercase tracking-tight">
            {docLabel}
          </div>
          <div className="text-sm text-gray-400">
            {fmtDate(documentDate)}
          </div>
        </div>
      </div>

      {/* Parties */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {devis.client.nom && (
          <div className="bg-gray-50 rounded-xl p-4 border-l-4 border-blue-500">
            <div className="text-xs font-semibold text-blue-600 uppercase tracking-wide mb-1">Client</div>
            <div className="font-semibold">{devis.client.nom}</div>
            {devis.client.adresse && (
              <div className="text-sm text-gray-500">{devis.client.adresse}</div>
            )}
          </div>
        )}
        <div className="bg-amber-50 rounded-xl p-4 border-l-4 border-amber-400">
          <div className="text-xs font-semibold text-amber-600 uppercase tracking-wide mb-1">Chantier</div>
          <div className="text-sm text-gray-700">{devis.chantier.description.substring(0, 120)}…</div>
        </div>
      </div>

      {/* Indice d'édition */}
      <p className="text-xs text-gray-400 flex items-center gap-1.5">
        <Pencil className="w-3 h-3" />
        Cliquez sur Qté, Unité, PU HT, Total HT, Lot ou les libellés pour modifier — les totaux se recalculent automatiquement.
      </p>

      {/* Tableau des lignes */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-blue-700 text-white">
              <th className="py-3 px-2 text-left font-semibold">Prestation</th>
              <th className="py-3 px-2 text-center font-semibold">Qté</th>
              <th className="py-3 px-2 text-right font-semibold">PU HT</th>
              {withTva && <th className="py-3 px-2 text-center font-semibold">TVA</th>}
              <th className="py-3 px-2 text-right font-semibold">Total HT</th>
            </tr>
          </thead>
          <tbody>
            {hasLots ? (
              lotGroups.map(({ lot, entries }) => (
                <Fragment key={lot || "__no_lot__"}>
                  {/* En-tête de LOT */}
                  {lot && (
                    <tr className="bg-slate-600">
                      <td
                        colSpan={withTva ? 5 : 4}
                        className="py-2 px-3 text-white font-semibold text-sm"
                      >
                        {lot}
                      </td>
                    </tr>
                  )}
                  {/* Lignes du lot */}
                  {entries.map(({ ligne, index }) => (
                    <LigneRow
                      key={index}
                      ligne={ligne}
                      withTva={withTva}
                      onUpdate={(field, value) => updateLigne(index, field, value)}
                    />
                  ))}
                  {/* Sous-total du LOT (si plusieurs lots) */}
                  {lotGroups.length > 1 && (
                    <tr className="bg-slate-50 border-b-2 border-slate-300">
                      <td
                        colSpan={withTva ? 4 : 3}
                        className="py-2 px-3 text-right text-sm text-gray-500 italic"
                      >
                        {lot ? `Sous-total ${lot}` : "Sous-total"}
                      </td>
                      <td className="py-2 px-3 text-right text-sm font-semibold text-gray-900">
                        {fmtMoney(round2(
                          entries.reduce((s, { ligne }) => s + ligne.quantite * ligne.prix_unitaire_ht, 0)
                        ))}
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))
            ) : (
              lignes.map((ligne, i) => (
                <LigneRow
                  key={i}
                  ligne={ligne}
                  withTva={withTva}
                  onUpdate={(field, value) => updateLigne(i, field, value)}
                />
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Totaux */}
      <div className="flex justify-end">
        <div className="w-full sm:w-80 bg-gray-50 rounded-xl overflow-hidden border border-gray-200">

          {/* Total HT (brut) */}
          <div className="flex justify-between px-4 py-2.5 text-sm">
            <span className="text-gray-600">{remiseType ? "Total HT brut" : "Total HT"}</span>
            <span className="font-semibold">{fmtMoney(totaux.total_ht)}</span>
          </div>

          {/* Remise */}
          <div className="flex items-center justify-between px-4 py-2 text-sm border-t border-gray-200 gap-2">
            <span className="text-gray-600 flex-shrink-0">Remise</span>
            <div className="flex items-center gap-1.5 ml-auto flex-wrap justify-end">
              <select
                value={remiseType}
                onChange={(e) => handleRemiseType(e.target.value)}
                className="text-xs border border-gray-300 rounded px-1.5 py-0.5 bg-white"
              >
                <option value="">Aucune</option>
                <option value="pourcentage">%</option>
                <option value="montant_fixe">€ fixe</option>
              </select>
              {remiseType && (
                <input
                  type="number"
                  value={remiseValeur || ""}
                  min="0"
                  step="0.01"
                  onChange={(e) => handleRemiseValeur(parseFloat(e.target.value) || 0)}
                  className="w-16 text-xs border border-gray-300 rounded px-1.5 py-0.5 text-right bg-white"
                />
              )}
              {(totaux.remise_ht ?? 0) > 0 && (
                <span className="text-red-600 font-semibold whitespace-nowrap text-xs">
                  - {fmtMoney(totaux.remise_ht ?? 0)}
                </span>
              )}
            </div>
          </div>

          {/* Total HT net — affiché seulement si remise */}
          {(totaux.remise_ht ?? 0) > 0 && (
            <div className="flex justify-between px-4 py-2 text-sm border-t border-gray-200">
              <span className="text-gray-600">Total HT net</span>
              <span className="font-semibold">{fmtMoney(totaux.total_ht_net ?? totaux.total_ht)}</span>
            </div>
          )}

          {/* TVA */}
          {withTva && (
            <div className="flex justify-between px-4 py-2.5 text-sm border-t border-gray-200">
              <span className="text-gray-600">Total TVA</span>
              <span>{fmtMoney(totaux.total_tva)}</span>
            </div>
          )}

          {/* Total final (TTC ou HT selon mode) */}
          <div className="flex justify-between px-4 py-3.5 bg-blue-700 text-white font-bold text-base">
            <span>{withTva ? "TOTAL TTC" : "TOTAL HT"}</span>
            <span>{fmtMoney(withTva ? totaux.total_ttc : (totaux.total_ht_net ?? totaux.total_ht))}</span>
          </div>

          {/* Acompte */}
          <div className="flex items-center justify-between px-4 py-2 text-sm border-t border-gray-200 gap-2">
            <span className="text-gray-600 flex-shrink-0">Acompte versé</span>
            <div className="flex items-center gap-1">
              <input
                type="number"
                value={acompte || ""}
                min="0"
                step="0.01"
                placeholder="0"
                onChange={(e) => handleAcompte(parseFloat(e.target.value) || 0)}
                className="w-20 text-xs border border-gray-300 rounded px-1.5 py-0.5 text-right bg-white"
              />
              <span className="text-xs text-gray-400">€</span>
            </div>
          </div>

          {/* Net à payer — affiché seulement si acompte */}
          {acompte > 0 && (
            <div className="flex justify-between px-4 py-3 bg-emerald-700 text-white font-bold text-sm">
              <span>NET À PAYER</span>
              <span>{fmtMoney(totaux.net_a_payer ?? totaux.total_ttc)}</span>
            </div>
          )}

        </div>
      </div>

      {/* Mentions légales */}
      <div className="border-t pt-4">
        <ul className="text-xs text-gray-400 space-y-1">
          {devis.mentions_legales.map((m, i) => <li key={i}>• {m}</li>)}
          {!withTva && (
            <li className="text-gray-500 font-medium">• TVA auto liquidation</li>
          )}
        </ul>
      </div>
    </div>
  );
}
