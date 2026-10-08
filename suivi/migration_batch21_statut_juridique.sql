-- ════════════════════════════════════════════════════════════════════════
-- Migration Batch 21 — Statut juridique (Société / Auto-entrepreneur)
-- À exécuter dans l'éditeur SQL Supabase (Dashboard → SQL Editor)
-- Non destructif : 3 colonnes ajoutées à la table entreprises.
-- statut_juridique a un défaut 'societe' pour que les comptes existants
-- gardent exactement le rendu PDF/Word actuel (pas de mention "(EI)" ajoutée
-- tant que l'artisan n'a pas explicitement choisi "Auto-entrepreneur").
-- ════════════════════════════════════════════════════════════════════════

ALTER TABLE entreprises
  ADD COLUMN IF NOT EXISTS statut_juridique text NOT NULL DEFAULT 'societe',
  ADD COLUMN IF NOT EXISTS forme_juridique text,
  ADD COLUMN IF NOT EXISTS capital_social numeric;

-- DROP + ADD plutôt que IF NOT EXISTS : PostgreSQL ne supporte pas
-- "ADD CONSTRAINT IF NOT EXISTS" — migration rejouable malgré tout.
ALTER TABLE entreprises
  DROP CONSTRAINT IF EXISTS entreprises_statut_juridique_check;

ALTER TABLE entreprises
  ADD CONSTRAINT entreprises_statut_juridique_check
  CHECK (statut_juridique IN ('societe', 'auto_entrepreneur'));

-- ════════════════════════════════════════════════════════════════════════
-- Vérification rapide (optionnelle) :
--   SELECT column_name FROM information_schema.columns
--   WHERE table_name = 'entreprises' ORDER BY ordinal_position;
-- ════════════════════════════════════════════════════════════════════════
