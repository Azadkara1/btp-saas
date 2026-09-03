-- ════════════════════════════════════════════════════════════════════════
-- Migration Phase 1 + Phase 2 — Dates de transition, nouveaux statuts,
-- filiation devis→facture (document_source_id)
-- À exécuter dans l'éditeur SQL Supabase (Dashboard → SQL Editor)
-- ════════════════════════════════════════════════════════════════════════

-- ── 1. Dates de transition (Phase 1a) ──────────────────────────────────
-- Nullable : renseignées uniquement au moment de la transition réelle.
-- Ne PAS backfiller avec la date actuelle — l'absence de valeur signifie
-- "jamais atteint ce statut", ce qui est une donnée en soi (cf. CLAUDE.md).
ALTER TABLE documents
  ADD COLUMN IF NOT EXISTS date_envoi     timestamptz,
  ADD COLUMN IF NOT EXISTS date_signature timestamptz,
  ADD COLUMN IF NOT EXISTS date_paiement  timestamptz,
  ADD COLUMN IF NOT EXISTS date_refus     timestamptz;

-- ── 2. Filiation devis → facture (Phase 2a) ────────────────────────────
-- NULL pour tout document créé normalement (génération, import).
-- Renseigné uniquement par POST /documents/{id}/convert.
-- ON DELETE SET NULL : si le devis source est supprimé un jour, la facture
-- convertie doit rester consultable (pas de suppression en cascade).
ALTER TABLE documents
  ADD COLUMN IF NOT EXISTS document_source_id uuid REFERENCES documents(id) ON DELETE SET NULL;

-- ── 3. Nouveaux statuts : refusé, expiré ────────────────────────────────
-- ⚠️ Piège déjà rencontré (cf. CLAUDE.md) : la contrainte CHECK doit
-- utiliser les valeurs AVEC accents, sinon les PATCH statut='refusé'
-- échouent en 500 (violation contrainte 23514).
ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_statut_check;
ALTER TABLE documents ADD CONSTRAINT documents_statut_check
  CHECK (statut IN ('brouillon', 'envoyé', 'signé', 'payé', 'refusé', 'expiré'));

-- ── 4. Index pour les agrégations du futur dashboard (Phase 5) ─────────
-- (user_id, statut) : répartition par statut, filtres statut dans l'historique.
-- (user_id, date_document) : CA par mois, tri chronologique.
CREATE INDEX IF NOT EXISTS idx_documents_user_statut
  ON documents (user_id, statut);

CREATE INDEX IF NOT EXISTS idx_documents_user_date_document
  ON documents (user_id, date_document);

-- ════════════════════════════════════════════════════════════════════════
-- Fin de la migration. Vérification rapide (optionnelle) :
--   SELECT column_name FROM information_schema.columns
--   WHERE table_name = 'documents' ORDER BY ordinal_position;
-- ════════════════════════════════════════════════════════════════════════
