-- ════════════════════════════════════════════════════════════════════════
-- Migration Batch 11 — T5 : Expiration automatique des devis
-- À exécuter dans l'éditeur SQL Supabase (Dashboard → SQL Editor)
-- Non destructif : 1 colonne nullable + 1 fonction.
-- ════════════════════════════════════════════════════════════════════════

-- Colonne dédiée — distincte de date_refus (deux événements différents :
-- un client peut refuser explicitement OU laisser un devis expirer sans
-- réponse, ce ne sont pas la même donnée). Jamais rétroactive : seule la
-- transition réelle (déclenchée par la RPC ci-dessous) la renseigne.
ALTER TABLE documents
  ADD COLUMN IF NOT EXISTS date_expiration timestamptz;

-- ── Fonction d'expiration automatique ────────────────────────────────────
-- SECURITY DEFINER : nécessaire car cette fonction est appelée quotidiennement
-- par un GitHub Action via la clé ANON (même clé que le ping anti-pause,
-- cf. supabase-keepalive.yml — aucun nouveau secret). La clé anon seule ne
-- pourrait pas mettre à jour des documents appartenant à tous les
-- utilisateurs à cause de la RLS ; SECURITY DEFINER fait tourner la fonction
-- avec les privilèges de son créateur (postgres), qui bypass la RLS — comme
-- le fait déjà le backend via le client service_role pour ses propres requêtes.
-- validite_jours vit dans le JSONB devis_payload (pas de colonne dédiée) :
-- (devis_payload->>'validite_jours') IS NULL exclut tout devis sans durée
-- de validité définie, qui ne doit donc JAMAIS expirer automatiquement.
CREATE OR REPLACE FUNCTION expire_devis_perimes()
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  nb_expires integer;
BEGIN
  UPDATE documents
  SET statut = 'expiré',
      date_expiration = now()
  WHERE type_doc = 'devis'
    AND statut = 'envoyé'
    AND deleted_at IS NULL
    AND date_envoi IS NOT NULL
    AND (devis_payload->>'validite_jours') IS NOT NULL
    AND date_envoi + ((devis_payload->>'validite_jours')::integer || ' days')::interval < now();

  GET DIAGNOSTICS nb_expires = ROW_COUNT;
  RETURN nb_expires;
END;
$$;

-- Autorise l'appel via la clé anon (utilisée par le GitHub Action quotidien)
GRANT EXECUTE ON FUNCTION expire_devis_perimes() TO anon;

-- ════════════════════════════════════════════════════════════════════════
-- Vérification rapide (optionnelle, exécute réellement l'expiration) :
--   SELECT expire_devis_perimes();  -- retourne le nombre de devis expirés
-- ════════════════════════════════════════════════════════════════════════
