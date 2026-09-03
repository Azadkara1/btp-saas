-- ════════════════════════════════════════════════════════════════════════
-- Migration Batch 11 — T1 : Assurance professionnelle & décennale
-- À exécuter dans l'éditeur SQL Supabase (Dashboard → SQL Editor)
-- Non destructif : 3 colonnes nullable ajoutées à la table entreprises.
-- ════════════════════════════════════════════════════════════════════════

ALTER TABLE entreprises
  ADD COLUMN IF NOT EXISTS assurance_nom text,
  ADD COLUMN IF NOT EXISTS assurance_contrat text,
  ADD COLUMN IF NOT EXISTS assurance_couverture text;

-- ════════════════════════════════════════════════════════════════════════
-- Vérification rapide (optionnelle) :
--   SELECT column_name FROM information_schema.columns
--   WHERE table_name = 'entreprises' ORDER BY ordinal_position;
-- ════════════════════════════════════════════════════════════════════════
