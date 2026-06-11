"use client";
/**
 * Formulaire principal de saisie du chantier.
 * Conçu pour être utilisable sur téléphone, sur chantier, avec les mains sales.
 * Champs larges, police confortable, feedback immédiat.
 */
import { useState, useEffect } from "react";
import { Loader2, Wand2, Plus, X } from "lucide-react";
import { generateQuote } from "@/lib/api";
import { QuoteRequest, QuoteResponse, PrixArtisan } from "@/lib/types";

interface QuoteFormProps {
  onQuoteGenerated: (response: QuoteResponse) => void;
}

const REGIONS = [
  "Île-de-France", "Rhône-Alpes", "PACA", "Bretagne",
  "Normandie", "Occitanie", "Nouvelle-Aquitaine", "Grand Est",
  "Hauts-de-France", "Pays de la Loire", "Bourgogne-Franche-Comté",
  "Centre-Val de Loire", "Corse"
];

const UNITES_COURANTES = ["m²", "ml", "m³", "heure", "unité", "forfait", "point"];

const PRESTATIONS_BTP: { group: string; items: string[] }[] = [
  { group: "Gros œuvre / Maçonnerie", items: ["Fondations béton armé", "Élévation murs en parpaings", "Dalle béton", "Reprise en sous-œuvre", "Enduit extérieur façade"] },
  { group: "Charpente / Couverture", items: ["Charpente bois traditionnelle", "Zinguerie et évacuations pluviales", "Pose tuiles / ardoises", "Isolation combles perdus", "Fenêtre de toit (type Velux)"] },
  { group: "Isolation / Plâtrerie", items: ["Isolation thermique par l'extérieur (ITE)", "Doublage et cloisons placo", "Faux plafond BA13", "Isolation phonique"] },
  { group: "Plomberie / Sanitaire", items: ["Remplacement chaudière gaz / PAC", "Installation salle de bain complète", "Pose baignoire / douche à l'italienne", "Remplacement robinetterie", "Pose WC suspendu", "VMC double flux"] },
  { group: "Électricité", items: ["Tableau électrique — mise aux normes", "Passage de câbles", "Pose prises et interrupteurs", "Éclairage LED", "Borne de recharge véhicule électrique"] },
  { group: "Carrelage / Revêtements", items: ["Pose carrelage sol", "Pose faïence murale", "Pose parquet flottant", "Pose stratifié"] },
  { group: "Menuiserie", items: ["Remplacement fenêtres double vitrage", "Pose porte d'entrée", "Pose portes intérieures", "Installation cuisine équipée", "Pose volets roulants"] },
  { group: "Peinture / Finitions", items: ["Peinture intérieure", "Peinture extérieure façade", "Enduit décoratif / crépi", "Pose papier peint"] },
  { group: "Démolition / Déblaiement", items: ["Démolition cloison", "Dépose ancien revêtement", "Déblaiement et évacuation gravats"] },
];

const EMPTY_PRIX: PrixArtisan = { prestation: "", prix_unitaire_ht: 0, unite: "m²" };

// ── Règles de validation (avertissements non bloquants) ──────────────
type Warning = { field: string; message: string };

function validateForm(form: QuoteRequest): Warning[] {
  const warns: Warning[] = [];

  const siret = (form.artisan_siret ?? "").replace(/\s/g, "");
  if (siret && !/^\d{14}$/.test(siret)) {
    warns.push({ field: "SIRET", message: `Le SIRET doit contenir exactement 14 chiffres (${siret.replace(/\D/g, "").length} saisis).` });
  }

  const iban = (form.artisan_iban ?? "").replace(/\s/g, "").toUpperCase();
  if (iban && !/^[A-Z]{2}[0-9]{2}[A-Z0-9]{10,30}$/.test(iban)) {
    warns.push({ field: "IBAN", message: "L'IBAN semble invalide (doit commencer par 2 lettres puis des chiffres, ex : FR76…)." });
  }

  const bic = (form.artisan_bic ?? "").replace(/\s/g, "").toUpperCase();
  if (bic && !/^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$/.test(bic)) {
    warns.push({ field: "BIC", message: "Le BIC doit faire 8 ou 11 caractères (ex : BNPAFRPP ou BNPAFRPPXXX)." });
  }

  const email = (form.artisan_email ?? "").trim();
  if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    warns.push({ field: "Email", message: "L'adresse email semble incorrecte." });
  }

  const cp = (form.artisan_code_postal ?? "").trim();
  if (cp && !/^\d{5}$/.test(cp)) {
    warns.push({ field: "Code postal", message: "Le code postal doit contenir 5 chiffres." });
  }

  return warns;
}

export default function QuoteForm({ onQuoteGenerated }: QuoteFormProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<Warning[] | null>(null);
  const [prestationSelect, setPrestationSelect] = useState("");

  const ARTISAN_LS_KEY = "artisan_profile";

  const DEFAULT_FORM: QuoteRequest = {
    description: "",
    region: "Rhône-Alpes",
    artisan_nom: "", artisan_siret: "", artisan_iban: "", artisan_bic: "",
    artisan_adresse: "", artisan_code_postal: "", artisan_ville: "",
    artisan_telephone: "", artisan_email: "", artisan_site_web: "",
    artisan_logo_base64: "",
    client_nom: "", client_adresse: "",
    numero_document: "",
  };

  // Toujours initialiser avec les valeurs par défaut (identique server + client)
  // Le chargement localStorage se fait après montage dans le useEffect ci-dessous
  const [form, setForm] = useState<QuoteRequest>(DEFAULT_FORM);

  // Chargement localStorage après montage (évite l'erreur d'hydratation)
  useEffect(() => {
    try {
      const saved = localStorage.getItem(ARTISAN_LS_KEY);
      if (saved) setForm(prev => ({ ...prev, ...JSON.parse(saved) }));
    } catch {}
  }, []);

  // Persistance localStorage — uniquement les champs artisan
  useEffect(() => {
    localStorage.setItem(ARTISAN_LS_KEY, JSON.stringify({
      artisan_nom: form.artisan_nom,
      artisan_siret: form.artisan_siret,
      artisan_iban: form.artisan_iban,
      artisan_bic: form.artisan_bic,
      artisan_adresse: form.artisan_adresse,
      artisan_code_postal: form.artisan_code_postal,
      artisan_ville: form.artisan_ville,
      artisan_telephone: form.artisan_telephone,
      artisan_email: form.artisan_email,
      artisan_site_web: form.artisan_site_web,
      artisan_logo_base64: form.artisan_logo_base64,
    }));
  }, [
    form.artisan_nom, form.artisan_siret, form.artisan_iban, form.artisan_bic,
    form.artisan_adresse, form.artisan_code_postal, form.artisan_ville,
    form.artisan_telephone, form.artisan_email, form.artisan_site_web,
    form.artisan_logo_base64,
  ]);

  // Gestion upload logo — on stocke le data URL complet pour l'aperçu
  const handleLogoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const dataUrl = ev.target?.result as string;
      setForm((prev) => ({ ...prev, artisan_logo_base64: dataUrl }));
    };
    reader.readAsDataURL(file);
  };

  // Prix personnalisés de l'artisan
  const [prixList, setPrixList] = useState<PrixArtisan[]>([]);
  const [newPrix, setNewPrix] = useState<PrixArtisan>({ ...EMPTY_PRIX });

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    setForm({ ...form, [e.target.name]: e.target.value });
    setError(null);
  };

  const addPrix = () => {
    if (!newPrix.prestation.trim() || newPrix.prix_unitaire_ht <= 0) return;
    setPrixList([...prixList, { ...newPrix }]);
    setNewPrix({ ...EMPTY_PRIX });
  };

  const removePrix = (index: number) => {
    setPrixList(prixList.filter((_, i) => i !== index));
  };

  const doGenerate = async () => {
    setWarnings(null);
    setLoading(true);
    setError(null);
    try {
      const logoRaw = form.artisan_logo_base64 ?? "";
      const logoB64 = logoRaw.includes(",") ? logoRaw.split(",")[1] : logoRaw;
      const response = await generateQuote({
        ...form,
        artisan_logo_base64: logoB64 || undefined,
        prix_personnalises: prixList.length > 0 ? prixList : undefined,
      });
      if (response.success) {
        onQuoteGenerated(response);
      } else {
        setError(response.error || "Une erreur est survenue.");
      }
    } catch {
      setError("Impossible de contacter le serveur. Vérifiez que le backend est démarré.");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (form.description.trim().length < 10) {
      setError("Décrivez le chantier en quelques mots minimum.");
      return;
    }
    const warns = validateForm(form);
    if (warns.length > 0) {
      setWarnings(warns);
      return;
    }
    await doGenerate();
  };

  return (
    <div className="card space-y-6">
      {/* Zone de saisie principale — grande et visible */}
      <div>
        <label className="block text-sm font-semibold text-gray-700 mb-2">
          📋 Description du chantier <span className="text-red-500">*</span>
        </label>
        <textarea
          name="description"
          value={form.description}
          onChange={handleChange}
          placeholder={`Ex : Rénovation salle de bain 8m², dépose ancien carrelage, pose nouveau carrelage grès cérame, peinture murs, remplacement robinetterie. Client à Lyon 3e.`}
          rows={5}
          className="input-field resize-none text-base leading-relaxed"
        />
        <p className="text-xs text-gray-400 mt-1">
          Décrivez librement : surfaces, matériaux, prestations. L&apos;IA s&apos;occupe du reste.
        </p>
        <div className="mt-2">
          <select
            value={prestationSelect}
            onChange={(e) => {
              const v = e.target.value;
              if (!v) return;
              setForm(prev => ({
                ...prev,
                description: prev.description ? `${prev.description}\n${v}` : v,
              }));
              setPrestationSelect("");
            }}
            className="input-field text-sm text-gray-500"
          >
            <option value="">+ Ajouter une prestation type…</option>
            {PRESTATIONS_BTP.map(({ group, items }) => (
              <optgroup key={group} label={group}>
                {items.map((item) => (
                  <option key={item} value={item}>{item}</option>
                ))}
              </optgroup>
            ))}
          </select>
        </div>
      </div>

      {/* Numéro de document */}
      <div>
        <label className="block text-sm font-semibold text-gray-700 mb-2">
          🔢 Numéro de document <span className="text-gray-400 font-normal">(optionnel)</span>
        </label>
        <input
          name="numero_document"
          value={form.numero_document ?? ""}
          onChange={handleChange}
          placeholder="Ex : DEV-2026-001 ou FAC-2026-042"
          className="input-field"
        />
      </div>

      {/* Région */}
      <div>
        <label className="block text-sm font-semibold text-gray-700 mb-2">
          📍 Région (pour les prix du marché)
        </label>
        <select
          name="region"
          value={form.region}
          onChange={handleChange}
          className="input-field"
        >
          {REGIONS.map((r) => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
      </div>

      {/* Prix personnalisés */}
      <details className="group">
        <summary className="cursor-pointer text-sm font-semibold text-emerald-600 hover:text-emerald-700 select-none flex items-center gap-2">
          <span className="text-base">💰</span>
          Mes prix habituels
          {prixList.length > 0 && (
            <span className="bg-emerald-100 text-emerald-700 text-xs font-bold px-2 py-0.5 rounded-full">
              {prixList.length}
            </span>
          )}
        </summary>

        <div className="mt-4 space-y-3">
          <p className="text-xs text-gray-500">
            Saisissez vos tarifs — l&apos;IA les utilisera en priorité et affichera le badge <strong>Votre prix</strong>.
          </p>

          {/* Liste des prix ajoutés */}
          {prixList.length > 0 && (
            <div className="space-y-2">
              {prixList.map((p, i) => (
                <div
                  key={i}
                  className="flex items-center gap-2 bg-emerald-50 border border-emerald-200 rounded-xl px-3 py-2.5"
                >
                  <span className="flex-1 text-sm font-medium text-gray-800 truncate">
                    {p.prestation}
                  </span>
                  <span className="text-sm font-semibold text-emerald-700 whitespace-nowrap">
                    {p.prix_unitaire_ht.toFixed(2)} €/{p.unite || "unité"}
                  </span>
                  <button
                    type="button"
                    onClick={() => removePrix(i)}
                    className="text-gray-400 hover:text-red-500 transition-colors ml-1 flex-shrink-0"
                    aria-label="Supprimer"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Formulaire d'ajout d'un prix */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            <input
              value={newPrix.prestation}
              onChange={(e) => setNewPrix({ ...newPrix, prestation: e.target.value })}
              onKeyDown={(e) => e.key === "Enter" && addPrix()}
              placeholder="Prestation (ex: Pose carrelage)"
              className="input-field text-sm sm:col-span-1"
            />
            <input
              type="number"
              value={newPrix.prix_unitaire_ht || ""}
              onChange={(e) =>
                setNewPrix({ ...newPrix, prix_unitaire_ht: parseFloat(e.target.value) || 0 })
              }
              onKeyDown={(e) => e.key === "Enter" && addPrix()}
              placeholder="Prix HT (€)"
              className="input-field text-sm"
              min="0"
              step="0.01"
            />
            <select
              value={newPrix.unite}
              onChange={(e) => setNewPrix({ ...newPrix, unite: e.target.value })}
              className="input-field text-sm"
            >
              {UNITES_COURANTES.map((u) => (
                <option key={u} value={u}>{u}</option>
              ))}
            </select>
          </div>

          <button
            type="button"
            onClick={addPrix}
            disabled={!newPrix.prestation.trim() || newPrix.prix_unitaire_ht <= 0}
            className="flex items-center gap-1.5 text-sm text-emerald-700 border border-emerald-300 rounded-xl px-4 py-2 hover:bg-emerald-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <Plus className="w-4 h-4" />
            Ajouter ce prix
          </button>
        </div>
      </details>

      {/* Remise et Acompte */}
      <details className="group">
        <summary className="cursor-pointer text-sm font-semibold text-purple-600 hover:text-purple-700 select-none flex items-center gap-2">
          <span>🏷️ Remise et acompte</span>
          <span className="text-gray-400 font-normal text-xs">(optionnel)</span>
        </summary>
        <div className="mt-4 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">Type de remise</label>
              <select name="remise_type" value={form.remise_type ?? ""} onChange={handleChange} className="input-field">
                <option value="">Aucune remise</option>
                <option value="pourcentage">Remise en pourcentage (%)</option>
                <option value="montant_fixe">Remise montant fixe (€)</option>
              </select>
            </div>
            {form.remise_type && (
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1">
                  Valeur {form.remise_type === "pourcentage" ? "(%)" : "(€)"}
                </label>
                <input
                  type="number"
                  value={form.remise_valeur ?? ""}
                  onChange={(e) => setForm(prev => ({ ...prev, remise_valeur: parseFloat(e.target.value) || undefined }))}
                  min="0"
                  step="0.01"
                  placeholder={form.remise_type === "pourcentage" ? "Ex : 5" : "Ex : 200"}
                  className="input-field"
                />
              </div>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">Acompte déjà versé (€)</label>
            <input
              type="number"
              value={form.acompte ?? ""}
              onChange={(e) => setForm(prev => ({ ...prev, acompte: parseFloat(e.target.value) || undefined }))}
              min="0"
              step="0.01"
              placeholder="Ex : 500"
              className="input-field"
            />
          </div>
        </div>
      </details>

      {/* Infos optionnelles */}
      <details className="group">
        <summary className="cursor-pointer text-sm font-semibold text-blue-600 hover:text-blue-700 select-none">
          + Informations optionnelles (artisan / client)
        </summary>
        <div className="mt-4 space-y-4">

          {/* ── Artisan ── */}
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Mon entreprise</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">Nom de l&apos;entreprise</label>
              <input name="artisan_nom" value={form.artisan_nom} onChange={handleChange}
                placeholder="Ex : SARL Dupont BTP" className="input-field" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">SIRET</label>
              <input name="artisan_siret" value={form.artisan_siret} onChange={handleChange}
                placeholder="Ex : 12345678900012" className="input-field" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">Adresse</label>
              <input name="artisan_adresse" value={form.artisan_adresse} onChange={handleChange}
                placeholder="Ex : 15 rue des Artisans" className="input-field" />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1">Code postal</label>
                <input name="artisan_code_postal" value={form.artisan_code_postal} onChange={handleChange}
                  placeholder="69001" className="input-field" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1">Ville</label>
                <input name="artisan_ville" value={form.artisan_ville} onChange={handleChange}
                  placeholder="Lyon" className="input-field" />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">Téléphone</label>
              <input name="artisan_telephone" value={form.artisan_telephone} onChange={handleChange}
                placeholder="Ex : 06 12 34 56 78" className="input-field" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">Email</label>
              <input name="artisan_email" value={form.artisan_email} onChange={handleChange}
                placeholder="contact@entreprise.fr" className="input-field" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">Site web</label>
              <input name="artisan_site_web" value={form.artisan_site_web} onChange={handleChange}
                placeholder="www.entreprise.fr" className="input-field" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">Logo</label>
              <div className="flex items-center gap-3">
                {form.artisan_logo_base64 ? (
                  <div className="flex items-center gap-2">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={form.artisan_logo_base64}
                      alt="Logo"
                      className="h-10 w-auto rounded border border-gray-200 object-contain bg-white p-0.5"
                    />
                    <button
                      type="button"
                      onClick={() => setForm({ ...form, artisan_logo_base64: "" })}
                      className="text-xs text-red-500 hover:text-red-700"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <label className="cursor-pointer flex items-center gap-2 text-sm text-blue-600 border border-dashed border-blue-300 rounded-xl px-4 py-2 hover:bg-blue-50 transition-colors">
                    <span>Choisir une image</span>
                    <input type="file" accept="image/*" className="hidden" onChange={handleLogoUpload} />
                  </label>
                )}
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">IBAN</label>
              <input name="artisan_iban" value={form.artisan_iban} onChange={handleChange}
                placeholder="Ex : FR76 3000 6000 0112 3456 7890 189" className="input-field" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">BIC / SWIFT</label>
              <input name="artisan_bic" value={form.artisan_bic} onChange={handleChange}
                placeholder="Ex : BNPAFRPPXXX" className="input-field" />
            </div>
          </div>

          {/* ── Client ── */}
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mt-2">Client</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">Nom du client</label>
              <input name="client_nom" value={form.client_nom} onChange={handleChange}
                placeholder="Ex : M. Martin" className="input-field" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">Adresse chantier</label>
              <input name="client_adresse" value={form.client_adresse} onChange={handleChange}
                placeholder="Ex : 12 rue des Fleurs, 69001 Lyon" className="input-field" />
            </div>
          </div>
        </div>
      </details>

      {/* Erreur bloquante */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm">
          ⚠️ {error}
        </div>
      )}

      {/* Avertissements de saisie — non bloquants */}
      {warnings && warnings.length > 0 && (
        <div className="bg-amber-50 border border-amber-300 rounded-xl px-4 py-3 space-y-2">
          <p className="text-sm font-semibold text-amber-800">⚠️ Vérifiez vos informations avant de continuer :</p>
          <ul className="space-y-1">
            {warnings.map((w, i) => (
              <li key={i} className="text-sm text-amber-700">
                <span className="font-medium">{w.field} :</span> {w.message}
              </li>
            ))}
          </ul>
          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={() => setWarnings(null)}
              className="text-sm px-4 py-2 rounded-xl border border-amber-400 text-amber-800 hover:bg-amber-100 transition-colors"
            >
              Corriger
            </button>
            <button
              type="button"
              onClick={doGenerate}
              disabled={loading}
              className="text-sm px-4 py-2 rounded-xl bg-amber-600 text-white hover:bg-amber-700 disabled:opacity-50 transition-colors flex items-center gap-2"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />}
              Générer quand même
            </button>
          </div>
        </div>
      )}

      {/* Bouton principal */}
      {!warnings && (
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="btn-primary w-full flex items-center justify-center gap-2 text-lg py-4"
        >
          {loading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              L&apos;IA génère votre devis…
            </>
          ) : (
            <>
              <Wand2 className="w-5 h-5" />
              Générer le devis
            </>
          )}
        </button>
      )}
    </div>
  );
}
