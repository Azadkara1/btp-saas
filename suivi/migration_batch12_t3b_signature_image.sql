-- ════════════════════════════════════════════════════════════════════════
-- Migration Batch 12 — T3 (complément) : signature à main levée
-- À exécuter dans l'éditeur SQL Supabase (Dashboard → SQL Editor)
-- Non destructif : 1 colonne nullable.
-- ════════════════════════════════════════════════════════════════════════

ALTER TABLE documents
  ADD COLUMN IF NOT EXISTS signature_image_base64 text;

-- ════════════════════════════════════════════════════════════════════════
-- Vérification rapide (optionnelle) :
--   SELECT column_name FROM information_schema.columns
--   WHERE table_name = 'documents' AND column_name = 'signature_image_base64';
-- ════════════════════════════════════════════════════════════════════════
