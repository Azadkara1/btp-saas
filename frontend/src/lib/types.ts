/**
 * Types TypeScript partagés — miroir des modèles Pydantic backend.
 * Source de vérité côté frontend.
 * À l'Étape 2, ces types seront générés automatiquement depuis OpenAPI.
 */

export type SourcePrix = "artisan" | "recherche_marche" | "estimation";

export type StatutJuridique = "societe" | "auto_entrepreneur";

export interface LigneDevis {
  lot?: string | null;
  poste: string;
  description: string;
  quantite: number | null;
  unite: string;
  prix_unitaire_ht: number;
  tva_taux: number;
  source_prix: SourcePrix;
}

export interface ClientInfo {
  nom?: string | null;
  adresse?: string | null;
  code_postal?: string | null;
  ville?: string | null;
  email?: string | null;
}

export interface ArtisanInfo {
  nom?: string | null;
  siret?: string | null;
  adresse?: string | null;
  code_postal?: string | null;
  ville?: string | null;
  telephone?: string | null;
  email?: string | null;
  site_web?: string | null;
  logo_base64?: string | null;
  iban?: string | null;
  bic?: string | null;
  assurance_nom?: string | null;
  assurance_contrat?: string | null;
  assurance_couverture?: string | null;
  statut_juridique?: StatutJuridique | null;
  forme_juridique?: string | null;
  capital_social?: number | null;
}

export interface ChantierInfo {
  description: string;
  adresse?: string | null;
}

export interface TotauxDevis {
  total_ht: number;
  total_tva: number;
  total_ttc: number;
  remise_ht?: number;
  total_ht_net?: number;
  net_a_payer?: number;
}

export interface Devis {
  client: ClientInfo;
  artisan: ArtisanInfo;
  chantier: ChantierInfo;
  lignes: LigneDevis[];
  totaux: TotauxDevis;
  mentions_legales: string[];
  notes?: string | null;
  numero_document?: string | null;
  remise_type?: string | null;
  remise_valeur?: number | null;
  acompte?: number | null;
  modele?: string | null;
  validite_jours?: number | null;
  conditions_paiement?: string | null;
  afficher_signature?: boolean;
  type_facture?: "acompte" | "solde" | null;
  retenue_garantie_taux?: number | null;
  autoliquidation?: boolean;
}

// ── Profil entreprise (Lot 2) ────────────────────────────────────
export interface ProfileEntreprise {
  nom?: string | null;
  siret?: string | null;
  adresse?: string | null;
  code_postal?: string | null;
  ville?: string | null;
  telephone?: string | null;
  email?: string | null;
  site_web?: string | null;
  logo_base64?: string | null;
  iban?: string | null;
  bic?: string | null;
  assurance_nom?: string | null;
  assurance_contrat?: string | null;
  assurance_couverture?: string | null;
  statut_juridique: StatutJuridique;
  forme_juridique?: string | null;
  capital_social?: number | null;
  modele_prefere: string;
  // Numérotation personnalisable par compte (Batch 13 T2)
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

export interface NumerotationStatus {
  devis_locked: boolean;
  devis_prochain_compteur: number;
  facture_locked: boolean;
  facture_prochain_compteur: number;
}

// ── Import meta ─────────────────────────────────────────────────
export interface EmetteurExtrait {
  nom?: string | null;
  siret?: string | null;
  adresse?: string | null;
  code_postal?: string | null;
  ville?: string | null;
  telephone?: string | null;
  email?: string | null;
  site_web?: string | null;
  iban?: string | null;
  bic?: string | null;
}

export interface ImportMeta {
  document_type?: "devis" | "facture" | null;
  numero_document_original?: string | null;
  date_document_original?: string | null;
  emetteur?: EmetteurExtrait | null;
  conditions_paiement?: string | null;
  acompte?: number | null;
}

// ── Requête / Réponse API ────────────────────────────────────────
export interface PrixArtisan {
  prestation: string;
  prix_unitaire_ht: number;
  unite: string;
}

export interface QuoteRequest {
  description: string;
  region?: string;
  artisan_nom?: string;
  artisan_siret?: string;
  artisan_iban?: string;
  artisan_bic?: string;
  artisan_assurance_nom?: string;
  artisan_assurance_contrat?: string;
  artisan_assurance_couverture?: string;
  artisan_statut_juridique?: StatutJuridique;
  artisan_forme_juridique?: string;
  artisan_capital_social?: number;
  artisan_adresse?: string;
  artisan_code_postal?: string;
  artisan_ville?: string;
  artisan_telephone?: string;
  artisan_email?: string;
  artisan_site_web?: string;
  artisan_logo_base64?: string;
  client_nom?: string;
  client_adresse?: string;
  client_email?: string;
  numero_document?: string;
  validite_jours?: number;
  conditions_paiement?: string;
  remise_type?: string;
  remise_valeur?: number;
  acompte?: number;
  retenue_garantie_taux?: number;
  autoliquidation?: boolean;
  modele?: string;
  afficher_signature?: boolean;
  prix_personnalises?: PrixArtisan[];
}

export interface QuoteResponse {
  success: boolean;
  devis?: Devis;
  error?: string;
  tokens_used?: number;
  import_meta?: ImportMeta;
}

// ── Documents (Lots 3 & 4) ───────────────────────────────────────
export type StatutDocument = "brouillon" | "envoyé" | "signé" | "payé" | "refusé" | "expiré";

export interface DocumentCreate {
  type_doc: string;
  titre?: string | null;
  numero_document?: string | null;
  date_document?: string | null;
  devis_payload: Devis;
  total_ttc?: number | null;
  client_nom?: string | null;
  client_adresse?: string | null;
  client_code_postal?: string | null;
  client_ville?: string | null;
}

export interface DocumentSummary {
  id: string;
  type_doc: string;
  titre?: string | null;
  numero?: string | null;
  numero_document?: string | null;
  client_nom?: string | null;
  total_ttc?: number | null;
  statut: StatutDocument;
  date_document?: string | null;
  created_at: string;
  document_source_id?: string | null;
  date_envoi?: string | null;
  date_signature?: string | null;
  date_paiement?: string | null;
  date_refus?: string | null;
  date_expiration?: string | null;
  date_email_envoye?: string | null;
  email_destinataire?: string | null;
  signature_nom_signataire?: string | null;
}

export interface DocumentDetail extends DocumentSummary {
  devis_payload: Devis;
  signature_image_base64?: string | null;
}

export interface StatusPatchResponse {
  statut: string;
  numero?: string | null;
}

// ── Envoi par email (Batch 11 T4) ──────────────────────────────────
export interface SendEmailRequest {
  email_destinataire: string;
  message?: string;
}

export interface SendEmailResponse {
  statut: string;
  numero?: string | null;
  date_email_envoye: string;
}

// ── Signature électronique publique (Batch 12 T3) ──────────────────
// ⚠️ Ces types sont volontairement un sous-ensemble restreint — jamais
// d'IBAN/BIC/email artisan, jamais de user_id. Miroir de app/models/public.py.
export interface PublicArtisanInfo {
  nom?: string | null;
  siret?: string | null;
  adresse?: string | null;
  code_postal?: string | null;
  ville?: string | null;
  telephone?: string | null;
  site_web?: string | null;
  logo_base64?: string | null;
  assurance_nom?: string | null;
  assurance_contrat?: string | null;
  assurance_couverture?: string | null;
  statut_juridique?: StatutJuridique | null;
  forme_juridique?: string | null;
  capital_social?: number | null;
}

export interface PublicClientInfo {
  nom?: string | null;
  adresse?: string | null;
  code_postal?: string | null;
  ville?: string | null;
}

export interface PublicDevisView {
  numero_document?: string | null;
  statut: StatutDocument;
  date_document?: string | null;
  validite_jours?: number | null;
  conditions_paiement?: string | null;
  modele?: string | null;
  afficher_signature: boolean;
  client: PublicClientInfo;
  artisan: PublicArtisanInfo;
  chantier: ChantierInfo;
  lignes: LigneDevis[];
  totaux: TotauxDevis;
  mentions_legales: string[];
  signable: boolean;
  deja_signe_par?: string | null;
  deja_signe_le?: string | null;
}

export interface SignatureLinkResponse {
  url: string;
}

// ── Clients (Phase 4) ────────────────────────────────────────────
export interface ClientSummary {
  id: string;
  nom: string;
  adresse?: string | null;
  code_postal?: string | null;
  ville?: string | null;
  nb_documents: number;
  ca_total: number;
}

export interface ClientDetail extends ClientSummary {
  documents: DocumentSummary[];
}

export interface ClientUpdate {
  nom?: string;
  adresse?: string;
  code_postal?: string;
  ville?: string;
}

// ── Dashboard (Phase 5) ───────────────────────────────────────────
export interface CaMoisPoint {
  mois: string; // "YYYY-MM"
  ca: number;
}

export interface TopPrestation {
  poste: string;
  ca: number;
}

export interface DashboardStats {
  ca_signe: number;
  ca_en_attente: number;
  ca_encaisse: number;
  taux_conversion: number;
  panier_moyen: number;
  delai_moyen_signature_jours?: number | null;
  repartition_statuts: Record<string, number>;
  ca_par_mois: CaMoisPoint[];
  top_prestations: TopPrestation[];
}

// ── Calendrier (Batch 20) ─────────────────────────────────────────
export interface Evenement {
  id: string;
  titre: string;
  description?: string | null;
  date_debut: string; // ISO 8601
  date_fin: string;   // ISO 8601
  toute_la_journee: boolean;
  cree_par: string;
  created_at: string;
  updated_at: string;
}

export interface EvenementCreate {
  titre: string;
  description?: string | null;
  date_debut: string;
  date_fin: string;
  toute_la_journee: boolean;
  cree_par: string;
}

export interface EvenementUpdate {
  titre?: string;
  description?: string | null;
  date_debut?: string;
  date_fin?: string;
  toute_la_journee?: boolean;
  cree_par?: string;
}
