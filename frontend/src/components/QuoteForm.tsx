"use client";
import { useState, useEffect, useRef } from "react";
import { Loader2, Wand2, Plus, X, ChevronDown, Building2, CheckCircle2, Save, Hash, Lock } from "lucide-react";
import { generateQuote, getProfile, saveProfile, getNumerotationStatus } from "@/lib/api";
import { QuoteRequest, QuoteResponse, PrixArtisan, ProfileEntreprise, NumerotationStatus } from "@/lib/types";

interface QuoteFormProps {
  onQuoteGenerated: (response: QuoteResponse) => void;
  modele?: string;
  docType?: "devis" | "facture";
  onModeleLoaded?: (m: string) => void;
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

interface NumerotationConfig {
  devis_numero_debut: number;
  devis_numero_prefixe: string;
  devis_numero_inclure_annee: boolean;
  devis_numero_padding: number;
  facture_numero_debut: number;
  facture_numero_prefixe: string;
  facture_numero_inclure_annee: boolean;
  facture_numero_padding: number;
  numero_reset_annuel: boolean;
}

const DEFAULT_NUMEROTATION: NumerotationConfig = {
  devis_numero_debut: 1,
  devis_numero_prefixe: "DEV-",
  devis_numero_inclure_annee: true,
  devis_numero_padding: 3,
  facture_numero_debut: 1,
  facture_numero_prefixe: "FAC-",
  facture_numero_inclure_annee: true,
  facture_numero_padding: 3,
  numero_reset_annuel: true,
};

// Reflète EXACTEMENT app.services.numero_service.format_numero (backend) —
// même formule, pour un aperçu en direct sans round-trip serveur à chaque frappe.
// Exportée : réutilisée par page.tsx pour le numéro provisoire à la génération (Batch 14).
export function formatNumeroPreview(compteur: number, prefixe: string, inclureAnnee: boolean, padding: number): string {
  const annee = new Date().getFullYear();
  const anneePart = inclureAnnee ? `${annee}-` : "";
  return `${prefixe}${anneePart}${String(compteur).padStart(padding, "0")}`;
}

type Warning = { field: string; message: string };

function validateForm(form: QuoteRequest): Warning[] {
  const warns: Warning[] = [];
  const siret = (form.artisan_siret ?? "").replace(/\s/g, "");
  if (siret && !/^\d{14}$/.test(siret))
    warns.push({ field: "SIRET", message: `Le SIRET doit contenir exactement 14 chiffres (${siret.replace(/\D/g, "").length} saisis).` });
  const iban = (form.artisan_iban ?? "").replace(/\s/g, "").toUpperCase();
  if (iban && !/^[A-Z]{2}[0-9]{2}[A-Z0-9]{10,30}$/.test(iban))
    warns.push({ field: "IBAN", message: "L'IBAN semble invalide (doit commencer par 2 lettres puis des chiffres, ex : FR76…)." });
  const bic = (form.artisan_bic ?? "").replace(/\s/g, "").toUpperCase();
  if (bic && !/^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$/.test(bic))
    warns.push({ field: "BIC", message: "Le BIC doit faire 8 ou 11 caractères (ex : BNPAFRPP ou BNPAFRPPXXX)." });
  const email = (form.artisan_email ?? "").trim();
  if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))
    warns.push({ field: "Email", message: "L'adresse email semble incorrecte." });
  const cp = (form.artisan_code_postal ?? "").trim();
  if (cp && !/^\d{5}$/.test(cp))
    warns.push({ field: "Code postal", message: "Le code postal doit contenir 5 chiffres." });
  return warns;
}

// ── Composant section repliable ──────────────────────────────────
function Collapsible({
  label, icon, badge, children, defaultOpen = false,
}: {
  label: string; icon?: React.ReactNode; badge?: React.ReactNode;
  children: React.ReactNode; defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="card !p-0 overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2.5 text-sm font-semibold text-gray-700">
          {icon}
          {label}
          {badge}
        </div>
        <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${open ? "rotate-180" : ""}`} />
      </button>
      {open && <div className="px-5 pb-5 space-y-4 border-t border-gray-100">{children}</div>}
    </div>
  );
}

export default function QuoteForm({ onQuoteGenerated, modele: modeleFromPage, docType = "devis", onModeleLoaded }: QuoteFormProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<Warning[] | null>(null);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // CP → Ville autocomplete
  const [artisanVilleOptions, setArtisanVilleOptions] = useState<string[]>([]);
  const artisanCpTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const ARTISAN_LS_KEY = "artisan_profile";

  const DEFAULT_FORM: QuoteRequest = {
    description: "",
    region: "Rhône-Alpes",
    artisan_nom: "", artisan_siret: "", artisan_iban: "", artisan_bic: "",
    artisan_assurance_nom: "", artisan_assurance_contrat: "", artisan_assurance_couverture: "",
    artisan_adresse: "", artisan_code_postal: "", artisan_ville: "",
    artisan_telephone: "", artisan_email: "", artisan_site_web: "",
    artisan_logo_base64: "",
    client_nom: "", client_adresse: "", client_email: "",
    numero_document: "",
    conditions_paiement: "",
    afficher_signature: true,
  };

  const [form, setForm] = useState<QuoteRequest>(DEFAULT_FORM);
  const [hasStoredProfile, setHasStoredProfile] = useState(false);

  // ── États Lot 2 ─────────────────────────────────────────────────
  const [showMigrationBanner, setShowMigrationBanner] = useState(false);
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileSaveOk, setProfileSaveOk] = useState(false);
  const [profileSaveError, setProfileSaveError] = useState<string | null>(null);

  // ── Numérotation personnalisable par compte (Batch 13 T2) ────────
  const [numerotation, setNumerotation] = useState<NumerotationConfig>(DEFAULT_NUMEROTATION);
  const [numerotationStatus, setNumerotationStatus] = useState<NumerotationStatus | null>(null);

  const refreshNumerotationStatus = async () => {
    try {
      setNumerotationStatus(await getNumerotationStatus());
    } catch {
      // Silencieux : l'aperçu est un confort, pas une donnée critique.
      // Si le profil n'existe pas encore en base, l'appel échoue simplement (404).
    }
  };

  // Point de départ ≠ 1 : décoche automatiquement le reset annuel (piège #1)
  // — les deux réglages sont légaux mais s'excluent en pratique la plupart
  // du temps, donc le défaut aide sans jamais interdire.
  const setNumeroDebut = (type: "devis" | "facture", val: number) => {
    setNumerotation(prev => ({
      ...prev,
      [type === "devis" ? "devis_numero_debut" : "facture_numero_debut"]: val,
      numero_reset_annuel: val !== 1 ? false : prev.numero_reset_annuel,
    }));
  };

  // ── Chargement profil au montage (backend → localStorage en fallback) ──
  useEffect(() => {
    async function initProfile() {
      try {
        const profile = await getProfile();
        if (profile) {
          // Source de vérité : base Supabase
          setForm(prev => ({
            ...prev,
            artisan_nom:          profile.nom          ?? "",
            artisan_siret:        profile.siret        ?? "",
            artisan_adresse:      profile.adresse      ?? "",
            artisan_code_postal:  profile.code_postal  ?? "",
            artisan_ville:        profile.ville        ?? "",
            artisan_telephone:    profile.telephone    ?? "",
            artisan_email:        profile.email        ?? "",
            artisan_site_web:     profile.site_web     ?? "",
            artisan_logo_base64:  profile.logo_base64  ?? "",
            artisan_iban:         profile.iban         ?? "",
            artisan_bic:          profile.bic          ?? "",
            artisan_assurance_nom:         profile.assurance_nom         ?? "",
            artisan_assurance_contrat:     profile.assurance_contrat     ?? "",
            artisan_assurance_couverture:  profile.assurance_couverture  ?? "",
          }));
          setHasStoredProfile(!!(profile.nom || profile.siret));
          if (profile.modele_prefere && onModeleLoaded) {
            onModeleLoaded(profile.modele_prefere);
          }
          setNumerotation({
            devis_numero_debut: profile.devis_numero_debut,
            devis_numero_prefixe: profile.devis_numero_prefixe,
            devis_numero_inclure_annee: profile.devis_numero_inclure_annee,
            devis_numero_padding: profile.devis_numero_padding,
            facture_numero_debut: profile.facture_numero_debut,
            facture_numero_prefixe: profile.facture_numero_prefixe,
            facture_numero_inclure_annee: profile.facture_numero_inclure_annee,
            facture_numero_padding: profile.facture_numero_padding,
            numero_reset_annuel: profile.numero_reset_annuel,
          });
          refreshNumerotationStatus();
        } else {
          // Aucun profil en base → chercher une migration localStorage
          try {
            const saved = localStorage.getItem(ARTISAN_LS_KEY);
            if (saved) {
              const parsed = JSON.parse(saved);
              if (parsed.artisan_nom || parsed.artisan_siret) {
                setShowMigrationBanner(true);
              }
            }
          } catch {}
        }
      } catch {
        // Erreur réseau ou auth → fallback localStorage silencieux
        try {
          const saved = localStorage.getItem(ARTISAN_LS_KEY);
          if (saved) {
            const parsed = JSON.parse(saved);
            setForm(prev => ({ ...prev, ...parsed }));
            setHasStoredProfile(!!(parsed.artisan_nom || parsed.artisan_siret));
          }
        } catch {}
      }
    }
    initProfile();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Cache localStorage (backup — la base reste la source de vérité) ──
  useEffect(() => {
    localStorage.setItem(ARTISAN_LS_KEY, JSON.stringify({
      artisan_nom: form.artisan_nom,
      artisan_siret: form.artisan_siret,
      artisan_iban: form.artisan_iban,
      artisan_bic: form.artisan_bic,
      artisan_assurance_nom: form.artisan_assurance_nom,
      artisan_assurance_contrat: form.artisan_assurance_contrat,
      artisan_assurance_couverture: form.artisan_assurance_couverture,
      artisan_adresse: form.artisan_adresse,
      artisan_code_postal: form.artisan_code_postal,
      artisan_ville: form.artisan_ville,
      artisan_telephone: form.artisan_telephone,
      artisan_email: form.artisan_email,
      artisan_site_web: form.artisan_site_web,
      artisan_logo_base64: form.artisan_logo_base64,
    }));
    setHasStoredProfile(!!(form.artisan_nom || form.artisan_siret));
  }, [
    form.artisan_nom, form.artisan_siret, form.artisan_iban, form.artisan_bic,
    form.artisan_assurance_nom, form.artisan_assurance_contrat, form.artisan_assurance_couverture,
    form.artisan_adresse, form.artisan_code_postal, form.artisan_ville,
    form.artisan_telephone, form.artisan_email, form.artisan_site_web,
    form.artisan_logo_base64,
  ]);

  // Fermeture du dropdown au clic extérieur
  useEffect(() => {
    if (!dropdownOpen) return;
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node))
        setDropdownOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [dropdownOpen]);

  // CP → Ville via geo.api.gouv.fr
  const fetchVillesByCp = async (
    cp: string,
    setOptions: (opts: string[]) => void,
    autoFill: (ville: string) => void,
  ) => {
    if (!/^\d{5}$/.test(cp)) { setOptions([]); return; }
    try {
      const res = await fetch(
        `https://geo.api.gouv.fr/communes?codePostal=${cp}&fields=nom&format=json`,
      );
      if (!res.ok) { setOptions([]); return; }
      const data: { nom: string }[] = await res.json();
      const noms = data.map(d => d.nom);
      if (noms.length === 1) { autoFill(noms[0]); setOptions([]); }
      else if (noms.length > 1) setOptions(noms);
      else setOptions([]);
    } catch { setOptions([]); }
  };

  const handleLogoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const dataUrl = ev.target?.result as string;
      setForm(prev => ({ ...prev, artisan_logo_base64: dataUrl }));
    };
    reader.readAsDataURL(file);
  };

  // ── Sauvegarde profil en base (infos entreprise + numérotation) ──
  const handleSaveProfile = async () => {
    setProfileSaving(true);
    setProfileSaveOk(false);
    setProfileSaveError(null);
    try {
      const profile: ProfileEntreprise = {
        nom:          form.artisan_nom          || null,
        siret:        form.artisan_siret        || null,
        adresse:      form.artisan_adresse      || null,
        code_postal:  form.artisan_code_postal  || null,
        ville:        form.artisan_ville        || null,
        telephone:    form.artisan_telephone    || null,
        email:        form.artisan_email        || null,
        site_web:     form.artisan_site_web     || null,
        logo_base64:  form.artisan_logo_base64  || null,
        iban:         form.artisan_iban         || null,
        bic:          form.artisan_bic          || null,
        assurance_nom:         form.artisan_assurance_nom         || null,
        assurance_contrat:     form.artisan_assurance_contrat     || null,
        assurance_couverture:  form.artisan_assurance_couverture  || null,
        modele_prefere: modeleFromPage || "moderne",
        ...numerotation,
      };
      await saveProfile(profile);
      setProfileSaveOk(true);
      setHasStoredProfile(!!(form.artisan_nom || form.artisan_siret));
      setTimeout(() => setProfileSaveOk(false), 3000);
      refreshNumerotationStatus();
    } catch (err) {
      setProfileSaveError(err instanceof Error ? err.message : "Erreur lors de la sauvegarde");
      setTimeout(() => setProfileSaveError(null), 8000);
    } finally {
      setProfileSaving(false);
    }
  };

  // ── Import depuis localStorage (migration) ──────────────────────
  const handleImportFromLocalStorage = () => {
    try {
      const saved = localStorage.getItem(ARTISAN_LS_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        setForm(prev => ({ ...prev, ...parsed }));
        setHasStoredProfile(!!(parsed.artisan_nom || parsed.artisan_siret));
      }
    } catch {}
    setShowMigrationBanner(false);
  };

  const [prixList, setPrixList] = useState<PrixArtisan[]>([]);
  const [newPrix, setNewPrix] = useState<PrixArtisan>({ ...EMPTY_PRIX });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value });
    setError(null);
  };

  const addPrix = () => {
    if (!newPrix.prestation.trim() || newPrix.prix_unitaire_ht <= 0) return;
    setPrixList([...prixList, { ...newPrix }]);
    setNewPrix({ ...EMPTY_PRIX });
  };

  const removePrix = (index: number) => setPrixList(prixList.filter((_, i) => i !== index));

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
        modele: modeleFromPage || "moderne",
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
    <div className="space-y-4">

      {/* ── Bannière migration localStorage ─────────────────────── */}
      {showMigrationBanner && (
        <div className="rounded-xl px-4 py-3 flex flex-wrap items-start justify-between gap-3"
          style={{ backgroundColor: "#FFFBEB", border: "1px solid #FCD34D" }}>
          <div>
            <p className="text-sm font-semibold" style={{ color: "#92400E" }}>
              Profil enregistré localement détecté
            </p>
            <p className="text-xs mt-0.5" style={{ color: "#B45309" }}>
              Importez vos infos entreprise puis cliquez sur &ldquo;Enregistrer le profil&rdquo; pour les sauvegarder en base.
            </p>
          </div>
          <div className="flex gap-2 flex-shrink-0">
            <button type="button" onClick={handleImportFromLocalStorage}
              className="text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors"
              style={{ backgroundColor: "#F59E0B", color: "#fff" }}>
              Importer mon ancien profil enregistré
            </button>
            <button type="button" onClick={() => setShowMigrationBanner(false)}
              className="text-xs font-medium px-3 py-1.5 rounded-lg border transition-colors"
              style={{ borderColor: "#FCD34D", color: "#92400E" }}>
              Ignorer
            </button>
          </div>
        </div>
      )}

      {/* ── Carte principale : description ───────────────────────── */}
      <div className="card space-y-4">
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Description du chantier <span className="text-red-400">*</span>
          </label>
          <textarea
            name="description"
            value={form.description}
            onChange={handleChange}
            placeholder="Ex : Rénovation salle de bain 8m², dépose carrelage, pose grès cérame, peinture murs, remplacement robinetterie. Client à Lyon 3e."
            rows={5}
            className="input-field resize-none leading-relaxed"
          />
          <p className="text-xs mt-1" style={{ color: "#7C857F" }}>
            Décrivez librement : surfaces, matériaux, prestations. Le document se construit tout seul.
          </p>
        </div>

        {/* Chips de suggestions rapides */}
        <div className="flex flex-wrap gap-2">
          {[
            "Pose carrelage sol", "Peinture intérieure", "Pose WC suspendu",
            "Tableau électrique", "Cloisons placo", "Fenêtres double vitrage",
            "Démolition cloison", "Dalle béton",
          ].map(chip => (
            <button
              key={chip}
              type="button"
              onClick={() => setForm(prev => ({
                ...prev,
                description: prev.description ? `${prev.description}\n${chip}` : chip,
              }))}
              className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-full transition-colors"
              style={{ border: "1px solid rgba(20,83,45,0.25)", color: "#14532D", backgroundColor: "transparent" }}
              onMouseOver={e => (e.currentTarget.style.backgroundColor = "#E3EDE6")}
              onMouseOut={e => (e.currentTarget.style.backgroundColor = "transparent")}
            >
              <span>+</span> {chip}
            </button>
          ))}
        </div>

        {/* Dropdown prestations type */}
        <div ref={dropdownRef} className="relative">
          <button
            type="button"
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center gap-2 text-sm px-4 py-2.5 rounded-xl border transition-colors"
            style={{ borderColor: "rgba(20,83,45,0.2)", color: "#14532D", backgroundColor: "#F0F7F3" }}
          >
            <Plus className="w-4 h-4" />
            Ajouter une prestation type
            <ChevronDown className={`w-4 h-4 transition-transform duration-200 ${dropdownOpen ? "rotate-180" : ""}`} />
          </button>

          {dropdownOpen && (
            <div className="absolute left-0 top-full mt-1 z-50 bg-white rounded-xl shadow-lg border overflow-y-auto w-80 max-h-72"
              style={{ borderColor: "rgba(20,83,45,0.15)" }}>
              {PRESTATIONS_BTP.map(({ group, items }) => (
                <div key={group}>
                  <div className="px-3 py-1.5 text-xs font-semibold uppercase tracking-wide sticky top-0 bg-gray-50"
                    style={{ color: "#5A635D" }}>
                    {group}
                  </div>
                  {items.map(item => (
                    <button
                      key={item}
                      type="button"
                      onClick={() => {
                        setForm(prev => ({
                          ...prev,
                          description: prev.description ? `${prev.description}\n${item}` : item,
                        }));
                        setDropdownOpen(false);
                      }}
                      className="w-full text-left px-4 py-2 text-sm transition-colors hover:bg-green-50 hover:text-green-900"
                      style={{ color: "#18211C" }}
                    >
                      {item}
                    </button>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Région */}
        <div>
          <label className="block text-xs font-semibold mb-1.5" style={{ color: "#5A635D" }}>
            Région (pour les prix du marché)
          </label>
          <select name="region" value={form.region} onChange={handleChange} className="input-field text-sm">
            {REGIONS.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
      </div>

      {/* ── Infos entreprise ─────────────────────────────────────── */}
      <Collapsible
        label="Mon entreprise"
        icon={<Building2 className="w-4 h-4" style={{ color: "#14532D" }} />}
        badge={
          hasStoredProfile ? (
            <span className="flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full"
              style={{ backgroundColor: "#E3EDE6", color: "#14532D" }}>
              <CheckCircle2 className="w-3 h-3" /> Enregistré
            </span>
          ) : null
        }
        defaultOpen={false}
      >
        <div className="pt-2 grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Nom de l'entreprise">
            <input name="artisan_nom" value={form.artisan_nom} onChange={handleChange}
              placeholder="Ex : SARL Dupont BTP" className="input-field" />
          </Field>
          <Field label="SIRET">
            <input name="artisan_siret" value={form.artisan_siret} onChange={handleChange}
              placeholder="14 chiffres" className="input-field" />
          </Field>
          <Field label="Adresse">
            <input name="artisan_adresse" value={form.artisan_adresse} onChange={handleChange}
              placeholder="15 rue des Artisans" className="input-field" />
          </Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Code postal">
              <div className="relative">
                <input name="artisan_code_postal" value={form.artisan_code_postal}
                  onChange={e => {
                    handleChange(e);
                    const cp = e.target.value;
                    if (artisanCpTimer.current) clearTimeout(artisanCpTimer.current);
                    artisanCpTimer.current = setTimeout(() => fetchVillesByCp(
                      cp, setArtisanVilleOptions,
                      ville => setForm(prev => ({ ...prev, artisan_ville: ville })),
                    ), 400);
                  }}
                  placeholder="69001" className="input-field" />
                {artisanVilleOptions.length > 1 && (
                  <ul className="absolute z-50 w-full bg-white border rounded-xl shadow-md mt-1 max-h-48 overflow-y-auto"
                    style={{ borderColor: "rgba(20,83,45,0.2)" }}>
                    {artisanVilleOptions.map(v => (
                      <li key={v}>
                        <button type="button"
                          onClick={() => { setForm(prev => ({ ...prev, artisan_ville: v })); setArtisanVilleOptions([]); }}
                          className="w-full text-left px-3 py-2 text-sm hover:bg-green-50" style={{ color: "#18211C" }}>
                          {v}
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </Field>
            <Field label="Ville">
              <input name="artisan_ville" value={form.artisan_ville} onChange={e => { handleChange(e); setArtisanVilleOptions([]); }}
                placeholder="Lyon" className="input-field" />
            </Field>
          </div>
          <Field label="Téléphone">
            <input name="artisan_telephone" value={form.artisan_telephone} onChange={handleChange}
              placeholder="06 12 34 56 78" className="input-field" />
          </Field>
          <Field label="Email">
            <input name="artisan_email" value={form.artisan_email} onChange={handleChange}
              placeholder="contact@entreprise.fr" className="input-field" />
          </Field>
          <Field label="Site web (facultatif)">
            <input name="artisan_site_web" value={form.artisan_site_web} onChange={handleChange}
              placeholder="www.entreprise.fr" className="input-field" />
          </Field>
          <Field label="Logo">
            <div className="flex items-center gap-3">
              {form.artisan_logo_base64 ? (
                <div className="flex items-center gap-2">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={form.artisan_logo_base64} alt="Logo"
                    className="h-10 w-auto rounded border object-contain bg-white p-0.5"
                    style={{ borderColor: "rgba(20,83,45,0.15)" }} />
                  <button type="button" onClick={() => setForm({ ...form, artisan_logo_base64: "" })}
                    className="text-gray-400 hover:text-red-500 transition-colors">
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                <label className="cursor-pointer flex items-center gap-2 text-sm border border-dashed rounded-xl px-4 py-2 transition-colors hover:bg-green-50"
                  style={{ borderColor: "rgba(20,83,45,0.3)", color: "#14532D" }}>
                  <span>Choisir une image</span>
                  <input type="file" accept="image/*" className="hidden" onChange={handleLogoUpload} />
                </label>
              )}
            </div>
          </Field>
          <Field label="IBAN">
            <input name="artisan_iban" value={form.artisan_iban} onChange={handleChange}
              placeholder="FR76 3000 6000 0112 3456 7890 189" className="input-field" />
          </Field>
          <Field label="BIC / SWIFT">
            <input name="artisan_bic" value={form.artisan_bic} onChange={handleChange}
              placeholder="BNPAFRPPXXX" className="input-field" />
          </Field>
          <div className="sm:col-span-2">
            <p className="text-xs mb-2" style={{ color: "#7C857F" }}>
              Mention obligatoire pour le BTP : coordonnées de votre assurance RC Pro / garantie décennale.
            </p>
          </div>
          <Field label="Assureur (facultatif)">
            <input name="artisan_assurance_nom" value={form.artisan_assurance_nom ?? ""} onChange={handleChange}
              placeholder="Ex : MAAF Assurances" className="input-field" />
          </Field>
          <Field label="N° de contrat (facultatif)">
            <input name="artisan_assurance_contrat" value={form.artisan_assurance_contrat ?? ""} onChange={handleChange}
              placeholder="Ex : 123456789" className="input-field" />
          </Field>
          <Field label="Zone de couverture (facultatif)">
            <input name="artisan_assurance_couverture" value={form.artisan_assurance_couverture ?? ""} onChange={handleChange}
              placeholder="Ex : France métropolitaine" className="input-field" />
          </Field>
        </div>

        {/* ── Bouton Enregistrer le profil en base ── */}
        <div className="pt-2 flex items-center gap-3 border-t border-gray-100">
          <button
            type="button"
            onClick={handleSaveProfile}
            disabled={profileSaving}
            className="flex items-center gap-2 text-sm font-semibold px-4 py-2.5 rounded-xl transition-colors disabled:opacity-50"
            style={{ backgroundColor: "#14532D", color: "#fff" }}
          >
            {profileSaving
              ? <Loader2 className="w-4 h-4 animate-spin" />
              : <Save className="w-4 h-4" />}
            Enregistrer le profil
          </button>
          {profileSaveOk && (
            <span className="flex items-center gap-1 text-sm font-medium" style={{ color: "#14532D" }}>
              <CheckCircle2 className="w-4 h-4" /> Profil enregistré en base
            </span>
          )}
          {profileSaveError && (
            <span className="text-sm font-medium" style={{ color: "#B91C1C" }}>
              {profileSaveError}
            </span>
          )}
        </div>
      </Collapsible>

      {/* ── Numérotation personnalisable par compte (Batch 13 T2) ─── */}
      <Collapsible
        label="Numérotation"
        icon={<Hash className="w-4 h-4" style={{ color: "#14532D" }} />}
      >
        <p className="text-xs" style={{ color: "#7C857F" }}>
          Vous migrez depuis un autre outil ? Réglez ici le point de départ, le préfixe et le format
          de vos numéros de devis et factures.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-2">
          {(["devis", "facture"] as const).map(type => {
            const locked = type === "devis" ? numerotationStatus?.devis_locked : numerotationStatus?.facture_locked;
            const prochainCompteur = numerotationStatus
              ? (locked
                  ? (type === "devis" ? numerotationStatus.devis_prochain_compteur : numerotationStatus.facture_prochain_compteur)
                  : numerotation[type === "devis" ? "devis_numero_debut" : "facture_numero_debut"])
              : null;
            const apercu = prochainCompteur !== null
              ? formatNumeroPreview(
                  prochainCompteur,
                  numerotation[type === "devis" ? "devis_numero_prefixe" : "facture_numero_prefixe"],
                  numerotation[type === "devis" ? "devis_numero_inclure_annee" : "facture_numero_inclure_annee"],
                  numerotation[type === "devis" ? "devis_numero_padding" : "facture_numero_padding"],
                )
              : null;
            return (
              <div key={type} className="space-y-3">
                <p className="text-sm font-semibold capitalize" style={{ color: "#18211C" }}>
                  {type === "devis" ? "Devis" : "Factures"}
                </p>
                <Field label="Point de départ">
                  <input type="number" min="1"
                    value={numerotation[type === "devis" ? "devis_numero_debut" : "facture_numero_debut"]}
                    disabled={!!locked}
                    onChange={e => setNumeroDebut(type, parseInt(e.target.value) || 1)}
                    className="input-field disabled:opacity-50 disabled:cursor-not-allowed" />
                  {locked && (
                    <p className="flex items-center gap-1 text-xs mt-1" style={{ color: "#B45309" }}>
                      <Lock className="w-3 h-3" /> Verrouillé : un numéro a déjà été attribué à un {type}.
                    </p>
                  )}
                </Field>
                <Field label="Préfixe">
                  <input type="text"
                    value={numerotation[type === "devis" ? "devis_numero_prefixe" : "facture_numero_prefixe"]}
                    onChange={e => setNumerotation(prev => ({
                      ...prev,
                      [type === "devis" ? "devis_numero_prefixe" : "facture_numero_prefixe"]: e.target.value,
                    }))}
                    placeholder="Ex : DEV- (peut être vide)" className="input-field" />
                </Field>
                <Field label="Nombre de chiffres (padding)">
                  <input type="number" min="1" max="10"
                    value={numerotation[type === "devis" ? "devis_numero_padding" : "facture_numero_padding"]}
                    onChange={e => setNumerotation(prev => ({
                      ...prev,
                      [type === "devis" ? "devis_numero_padding" : "facture_numero_padding"]: parseInt(e.target.value) || 1,
                    }))}
                    className="input-field" />
                </Field>
                <label className="flex items-center gap-2 text-sm cursor-pointer" style={{ color: "#18211C" }}>
                  <input type="checkbox"
                    checked={numerotation[type === "devis" ? "devis_numero_inclure_annee" : "facture_numero_inclure_annee"]}
                    onChange={e => setNumerotation(prev => ({
                      ...prev,
                      [type === "devis" ? "devis_numero_inclure_annee" : "facture_numero_inclure_annee"]: e.target.checked,
                    }))}
                    className="w-4 h-4 rounded" style={{ accentColor: "#14532D" }} />
                  Inclure l&apos;année dans le numéro
                </label>
                {apercu && (
                  <p className="text-sm font-medium px-3 py-2 rounded-lg" style={{ backgroundColor: "#E3EDE6", color: "#14532D" }}>
                    Prochain {type} : {apercu}
                  </p>
                )}
              </div>
            );
          })}
        </div>
        <div className="pt-2 border-t border-gray-100">
          <label className="flex items-center gap-2 text-sm cursor-pointer" style={{ color: "#18211C" }}>
            <input type="checkbox"
              checked={numerotation.numero_reset_annuel}
              onChange={e => setNumerotation(prev => ({ ...prev, numero_reset_annuel: e.target.checked }))}
              className="w-4 h-4 rounded" style={{ accentColor: "#14532D" }} />
            Remise à zéro annuelle (recommencer au point de départ chaque 1er janvier)
          </label>
          <p className="text-xs mt-1 ml-6" style={{ color: "#7C857F" }}>
            Partagée entre devis et factures. Se décoche automatiquement si vous personnalisez un point de départ —
            les deux réglages sont possibles, mais rarement utiles ensemble.
          </p>
        </div>
        <div className="pt-2">
          <button
            type="button"
            onClick={handleSaveProfile}
            disabled={profileSaving}
            className="flex items-center gap-2 text-sm font-semibold px-4 py-2.5 rounded-xl transition-colors disabled:opacity-50"
            style={{ backgroundColor: "#14532D", color: "#fff" }}
          >
            {profileSaving
              ? <Loader2 className="w-4 h-4 animate-spin" />
              : <Save className="w-4 h-4" />}
            Enregistrer la numérotation
          </button>
          {profileSaveOk && (
            <span className="ml-3 text-sm font-medium" style={{ color: "#14532D" }}>
              <CheckCircle2 className="w-4 h-4 inline mr-1" />Enregistré
            </span>
          )}
          {profileSaveError && (
            <span className="ml-3 text-sm font-medium" style={{ color: "#B91C1C" }}>
              {profileSaveError}
            </span>
          )}
        </div>
      </Collapsible>

      {/* ── Client ───────────────────────────────────────────────── */}
      <div className="card space-y-3">
        <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: "#5A635D" }}>Client</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Nom du client">
            <input name="client_nom" value={form.client_nom} onChange={handleChange}
              placeholder="M. Martin" className="input-field" />
          </Field>
          <Field label="Adresse complète">
            <textarea name="client_adresse" value={form.client_adresse ?? ""} onChange={handleChange}
              placeholder={"12 rue des Fleurs\n69001 Lyon"} rows={3}
              className="input-field resize-none" />
          </Field>
          <Field label="Email du client (optionnel)">
            <input type="email" name="client_email" value={form.client_email ?? ""} onChange={handleChange}
              placeholder="client@exemple.fr" className="input-field" />
            <p className="text-xs mt-1" style={{ color: "#7C857F" }}>
              Pré-remplit l'envoi du devis par email — modifiable à tout moment avant l'envoi.
            </p>
          </Field>
        </div>
      </div>

      {/* ── Mes prix habituels ───────────────────────────────────── */}
      <Collapsible
        label="Mes prix habituels"
        badge={prixList.length > 0 ? (
          <span className="text-xs font-bold px-2 py-0.5 rounded-full"
            style={{ backgroundColor: "#E3EDE6", color: "#14532D" }}>
            {prixList.length}
          </span>
        ) : null}
      >
        <p className="text-xs pt-2" style={{ color: "#7C857F" }}>
          Saisissez vos tarifs — ils seront utilisés en priorité et afficheront le badge <strong>Votre prix</strong>.
        </p>
        {prixList.length > 0 && (
          <div className="space-y-2">
            {prixList.map((p, i) => (
              <div key={i} className="flex items-center gap-2 rounded-xl px-3 py-2.5"
                style={{ backgroundColor: "#F0F7F3", border: "1px solid rgba(20,83,45,0.15)" }}>
                <span className="flex-1 text-sm font-medium truncate" style={{ color: "#18211C" }}>{p.prestation}</span>
                <span className="text-sm font-semibold whitespace-nowrap" style={{ color: "#14532D" }}>
                  {p.prix_unitaire_ht.toFixed(2)} €/{p.unite || "unité"}
                </span>
                <button type="button" onClick={() => removePrix(i)}
                  className="text-gray-400 hover:text-red-500 transition-colors ml-1 flex-shrink-0">
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          <input value={newPrix.prestation}
            onChange={e => setNewPrix({ ...newPrix, prestation: e.target.value })}
            onKeyDown={e => e.key === "Enter" && addPrix()}
            placeholder="Prestation (ex: Pose carrelage)" className="input-field text-sm sm:col-span-1" />
          <input type="number" value={newPrix.prix_unitaire_ht || ""}
            onChange={e => setNewPrix({ ...newPrix, prix_unitaire_ht: parseFloat(e.target.value) || 0 })}
            onKeyDown={e => e.key === "Enter" && addPrix()}
            placeholder="Prix HT (€)" className="input-field text-sm" min="0" step="0.01" />
          <select value={newPrix.unite}
            onChange={e => setNewPrix({ ...newPrix, unite: e.target.value })}
            className="input-field text-sm">
            {UNITES_COURANTES.map(u => <option key={u} value={u}>{u}</option>)}
          </select>
        </div>
        <button type="button" onClick={addPrix}
          disabled={!newPrix.prestation.trim() || newPrix.prix_unitaire_ht <= 0}
          className="flex items-center gap-1.5 text-sm border rounded-xl px-4 py-2 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          style={{ color: "#14532D", borderColor: "rgba(20,83,45,0.3)", backgroundColor: "transparent" }}
          onMouseOver={e => (e.currentTarget.style.backgroundColor = "#F0F7F3")}
          onMouseOut={e => (e.currentTarget.style.backgroundColor = "transparent")}>
          <Plus className="w-4 h-4" />
          Ajouter ce prix
        </button>
      </Collapsible>

      {/* ── Remise & acompte ─────────────────────────────────────── */}
      <Collapsible label="Remise & acompte">
        <div className="pt-2 grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Type de remise">
            <select name="remise_type" value={form.remise_type ?? ""} onChange={handleChange} className="input-field">
              <option value="">Aucune remise</option>
              <option value="pourcentage">Remise en pourcentage (%)</option>
              <option value="montant_fixe">Remise montant fixe (€)</option>
            </select>
          </Field>
          {form.remise_type && (
            <Field label={`Valeur ${form.remise_type === "pourcentage" ? "(%)" : "(€)"}`}>
              <input type="number"
                value={form.remise_valeur ?? ""}
                onChange={e => setForm(prev => ({ ...prev, remise_valeur: parseFloat(e.target.value) || undefined }))}
                min="0" step="0.01"
                placeholder={form.remise_type === "pourcentage" ? "Ex : 5" : "Ex : 200"}
                className="input-field" />
            </Field>
          )}
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Acompte déjà versé (€)">
            <input type="number"
              value={form.acompte ?? ""}
              onChange={e => setForm(prev => ({ ...prev, acompte: parseFloat(e.target.value) || undefined }))}
              min="0" step="0.01" placeholder="Ex : 500" className="input-field" />
          </Field>
          <Field label="Retenue de garantie (%)">
            <input type="number"
              value={form.retenue_garantie_taux ?? ""}
              onChange={e => setForm(prev => ({ ...prev, retenue_garantie_taux: parseFloat(e.target.value) || undefined }))}
              min="0" max="5" step="0.1" placeholder="Ex : 5" className="input-field" />
          </Field>
        </div>
      </Collapsible>

      {/* ── Paramètres du document ───────────────────────────────── */}
      <Collapsible label="Paramètres du document">
        <div className="pt-2 space-y-4">
          <Field label="Numéro de document">
            <input name="numero_document" value={form.numero_document ?? ""} onChange={handleChange}
              placeholder="Ex : DEV-2026-001" className="input-field" />
          </Field>
          {docType === "devis" && (
            <Field label="Validité du devis (jours)">
              <input type="number" name="validite_jours"
                value={form.validite_jours ?? ""}
                onChange={e => {
                  const v = parseInt(e.target.value);
                  setForm(prev => ({ ...prev, validite_jours: isNaN(v) || v <= 0 ? undefined : v }));
                }}
                min="1" max="365" placeholder="Ex: 30" className="input-field" />
              <p className="text-xs mt-1" style={{ color: "#7C857F" }}>
                Laisser vide → aucune mention de validité dans le document.
              </p>
            </Field>
          )}
          <Field label="Conditions de paiement">
            <input name="conditions_paiement" value={form.conditions_paiement ?? ""} onChange={handleChange}
              placeholder="Ex : 30% à la commande, solde à réception" className="input-field" />
          </Field>
          <label className="flex items-center gap-2 text-sm cursor-pointer" style={{ color: "#18211C" }}>
            <input type="checkbox"
              checked={form.afficher_signature ?? true}
              onChange={e => setForm(prev => ({ ...prev, afficher_signature: e.target.checked }))}
              className="w-4 h-4 rounded" style={{ accentColor: "#14532D" }} />
            Afficher l'encadré "Bon pour accord" / signature client
          </label>
          <div>
            <label className="flex items-center gap-2 text-sm cursor-pointer" style={{ color: "#18211C" }}>
              <input type="checkbox"
                checked={form.autoliquidation ?? false}
                onChange={e => setForm(prev => ({ ...prev, autoliquidation: e.target.checked }))}
                className="w-4 h-4 rounded" style={{ accentColor: "#14532D" }} />
              Autoliquidation de la TVA (sous-traitance BTP)
            </label>
            <p className="text-xs mt-1 ml-6" style={{ color: "#7C857F" }}>
              Facture à un donneur d'ordre en tant que sous-traitant : la TVA n'est pas facturée, mention légale ajoutée automatiquement (art. 283-2 nonies du CGI).
            </p>
          </div>
        </div>
      </Collapsible>

      {/* ── Erreur bloquante ─────────────────────────────────────── */}
      {error && (
        <div className="rounded-xl px-4 py-3 text-sm" style={{ backgroundColor: "#FEF2F2", border: "1px solid #FECACA", color: "#B91C1C" }}>
          {error}
        </div>
      )}

      {/* ── Avertissements non bloquants ─────────────────────────── */}
      {warnings && warnings.length > 0 && (
        <div className="rounded-xl px-4 py-3 space-y-2" style={{ backgroundColor: "#FFFBEB", border: "1px solid #FCD34D" }}>
          <p className="text-sm font-semibold" style={{ color: "#92400E" }}>Vérifiez vos informations avant de continuer :</p>
          <ul className="space-y-1">
            {warnings.map((w, i) => (
              <li key={i} className="text-sm" style={{ color: "#B45309" }}>
                <span className="font-medium">{w.field} :</span> {w.message}
              </li>
            ))}
          </ul>
          <div className="flex gap-3 pt-1">
            <button type="button" onClick={() => setWarnings(null)}
              className="text-sm px-4 py-2 rounded-xl border transition-colors"
              style={{ borderColor: "#F59E0B", color: "#92400E" }}>
              Corriger
            </button>
            <button type="button" onClick={doGenerate} disabled={loading}
              className="text-sm px-4 py-2 rounded-xl text-white disabled:opacity-50 transition-colors flex items-center gap-2"
              style={{ backgroundColor: "#D97706" }}>
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />}
              Générer quand même
            </button>
          </div>
        </div>
      )}

      {/* ── Bouton principal ─────────────────────────────────────── */}
      {!warnings && (
        <button onClick={handleSubmit} disabled={loading}
          className="btn-primary w-full flex items-center justify-center gap-2 text-lg py-4">
          {loading ? (
            <><Loader2 className="w-5 h-5 animate-spin" /> Le document se construit…</>
          ) : (
            <><Wand2 className="w-5 h-5" /> Générer le document</>
          )}
        </button>
      )}
    </div>
  );
}

// ── Mini composant champ labellisé ────────────────────────────────
function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-medium mb-1" style={{ color: "#5A635D" }}>{label}</label>
      {children}
    </div>
  );
}
