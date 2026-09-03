-- ════════════════════════════════════════════════════════════════════════
-- Migration Batch 12 — T3 : Signature électronique du devis par le client
-- À exécuter dans l'éditeur SQL Supabase (Dashboard → SQL Editor)
-- Non destructif : colonnes nullable uniquement.
-- Réutilise la colonne date_signature existante (Batch 10) — pas de doublon.
-- ════════════════════════════════════════════════════════════════════════

ALTER TABLE documents
  ADD COLUMN IF NOT EXISTS signature_token             text,
  ADD COLUMN IF NOT EXISTS signature_token_expires_at  timestamptz,
  ADD COLUMN IF NOT EXISTS signature_nom_signataire    text,
  ADD COLUMN IF NOT EXISTS signature_ip                text,
  ADD COLUMN IF NOT EXISTS signature_user_agent        text;

-- Index unique : le token doit être trouvable rapidement par la route
-- publique (GET /public/devis/{token}), et deux documents ne doivent
-- jamais partager le même token.
CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_signature_token
  ON documents (signature_token)
  WHERE signature_token IS NOT NULL;

-- ════════════════════════════════════════════════════════════════════════
-- Vérification rapide (optionnelle) :
--   SELECT column_name FROM information_schema.columns
--   WHERE table_name = 'documents' AND column_name LIKE 'signature_%';
-- ════════════════════════════════════════════════════════════════════════
