/**
 * Types TypeScript partagés — miroir des modèles Pydantic backend.
 * Source de vérité côté frontend.
 * À l'Étape 2, ces types seront générés automatiquement depuis OpenAPI.
 */

export type SourcePrix = "artisan" | "recherche_marche" | "estimation";

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
  artisan_adresse?: string;
  artisan_code_postal?: string;
  artisan_ville?: string;
  artisan_telephone?: string;
  artisan_email?: string;
  artisan_site_web?: string;
  artisan_logo_base64?: string;
  client_nom?: string;
  client_adresse?: string;
  numero_document?: string;
  validite_jours?: number;
  conditions_paiement?: string;
  remise_type?: string;
  remise_valeur?: number;
  acompte?: number;
  modele?: string;
  prix_personnalises?: PrixArtisan[];
}

export interface QuoteResponse {
  success: boolean;
  devis?: Devis;
  error?: string;
  tokens_used?: number;
}
