-- ════════════════════════════════════════════════════════════════════════
-- Migration Batch 11 — T4 : Envoi du devis par email au client
-- À exécuter dans l'éditeur SQL Supabase (Dashboard → SQL Editor)
-- Non destructif : 2 colonnes nullable + 1 bucket de stockage privé.
-- ════════════════════════════════════════════════════════════════════════

ALTER TABLE documents
  ADD COLUMN IF NOT EXISTS date_email_envoye timestamptz,
  ADD COLUMN IF NOT EXISTS email_destinataire text;

-- ── Bucket de stockage privé pour l'archive PDF ─────────────────────────
-- Le backend utilise le client service_role (bypass RLS), donc aucune
-- policy storage.objects n'est nécessaire : toutes les lectures/écritures
-- passent exclusivement par le backend, jamais directement depuis le navigateur.
-- Chemin de rangement : documents-pdf/{user_id}/{document_id}.pdf
insert into storage.buckets (id, name, public)
values ('documents-pdf', 'documents-pdf', false)
on conflict (id) do nothing;

-- ════════════════════════════════════════════════════════════════════════
-- Vérification rapide (optionnelle) :
--   SELECT column_name FROM information_schema.columns
--   WHERE table_name = 'documents' AND column_name IN ('date_email_envoye','email_destinataire');
--   SELECT id, public FROM storage.buckets WHERE id = 'documents-pdf';
-- ════════════════════════════════════════════════════════════════════════
