-- ════════════════════════════════════════════════════════════════════════
-- Migration Batch 20 — Calendrier partagé (table evenements)
-- À exécuter dans l'éditeur SQL Supabase (Dashboard → SQL Editor)
-- Rejouable : chaque instruction est protégée par IF NOT EXISTS, un second
-- lancement ne provoque aucune erreur.
--
-- ⚠️ Pas de RLS ici, volontairement — cohérent avec toutes les autres tables
-- du projet (documents, clients, entreprises) : la sécurité repose
-- exclusivement sur le filtrage user_id fait côté backend (client
-- service_role), jamais sur des policies Postgres. Voir CLAUDE.md.
-- ════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS evenements (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id          uuid NOT NULL,
  titre            text NOT NULL,
  description      text,
  date_debut       timestamptz NOT NULL,
  date_fin         timestamptz NOT NULL,
  toute_la_journee boolean NOT NULL DEFAULT false,
  cree_par         text NOT NULL,
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now()
);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'evenements_date_fin_check'
  ) THEN
    ALTER TABLE evenements
      ADD CONSTRAINT evenements_date_fin_check CHECK (date_fin >= date_debut);
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_evenements_user_date
  ON evenements (user_id, date_debut);

-- ════════════════════════════════════════════════════════════════════════
-- Vérification rapide (optionnelle) :
--   SELECT * FROM evenements LIMIT 1;
-- ════════════════════════════════════════════════════════════════════════
