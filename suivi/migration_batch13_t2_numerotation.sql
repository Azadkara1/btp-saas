-- ════════════════════════════════════════════════════════════════════════
-- Migration Batch 13 T2 — Numérotation personnalisable par compte
-- À exécuter dans l'éditeur SQL Supabase (Dashboard → SQL Editor)
--
-- Non destructif : 9 colonnes nullable/à défaut sur `entreprises`
-- (backfillées automatiquement par Postgres avec le comportement ACTUEL,
-- rien ne change pour les comptes existants), + 1 contrainte d'unicité
-- sur `documents`, + remplacement de la fonction get_next_numero.
-- ════════════════════════════════════════════════════════════════════════

-- ── 1. Nouvelles colonnes de configuration sur entreprises ────────────────

ALTER TABLE entreprises
  ADD COLUMN IF NOT EXISTS devis_numero_debut         int  NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS devis_numero_prefixe        text NOT NULL DEFAULT 'DEV-',
  ADD COLUMN IF NOT EXISTS devis_numero_inclure_annee  bool NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS devis_numero_padding        int  NOT NULL DEFAULT 3,
  ADD COLUMN IF NOT EXISTS facture_numero_debut        int  NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS facture_numero_prefixe      text NOT NULL DEFAULT 'FAC-',
  ADD COLUMN IF NOT EXISTS facture_numero_inclure_annee bool NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS facture_numero_padding      int  NOT NULL DEFAULT 3,
  ADD COLUMN IF NOT EXISTS numero_reset_annuel         bool NOT NULL DEFAULT true;

-- ── 2. Unicité du numéro légal par utilisateur + type de document ─────────
-- UNIQUE ignore nativement les NULL (brouillons sans numéro) en SQL standard
-- — pas besoin d'index partiel. Filet de sécurité : deux documents avec le
-- même numéro deviennent une erreur SQL visible, pas une découverte lors
-- d'un contrôle fiscal.

ALTER TABLE documents
  ADD CONSTRAINT documents_numero_unique UNIQUE (user_id, type_doc, numero);

-- ── 3. Remplacement de get_next_numero — formatage dans la fonction,  ─────
--       toujours un seul UPDATE ... RETURNING (atomicité, piège #4)

CREATE OR REPLACE FUNCTION get_next_numero(p_user_id uuid, p_type text)
RETURNS text AS $$
DECLARE
  v_annee   int := extract(year from now());
  v_compteur int;
  v_prefixe  text;
  v_inclure_annee bool;
  v_padding  int;
BEGIN
  IF p_type = 'devis' THEN
    UPDATE entreprises SET
      compteur_devis = CASE
        WHEN compteur_devis_annee IS NULL THEN devis_numero_debut
        WHEN numero_reset_annuel AND compteur_devis_annee IS DISTINCT FROM v_annee
          THEN devis_numero_debut
        ELSE compteur_devis + 1
      END,
      compteur_devis_annee = v_annee
    WHERE user_id = p_user_id
    RETURNING compteur_devis, devis_numero_prefixe, devis_numero_inclure_annee, devis_numero_padding
    INTO v_compteur, v_prefixe, v_inclure_annee, v_padding;
  ELSE
    UPDATE entreprises SET
      compteur_factures = CASE
        WHEN compteur_factures_annee IS NULL THEN facture_numero_debut
        WHEN numero_reset_annuel AND compteur_factures_annee IS DISTINCT FROM v_annee
          THEN facture_numero_debut
        ELSE compteur_factures + 1
      END,
      compteur_factures_annee = v_annee
    WHERE user_id = p_user_id
    RETURNING compteur_factures, facture_numero_prefixe, facture_numero_inclure_annee, facture_numero_padding
    INTO v_compteur, v_prefixe, v_inclure_annee, v_padding;
  END IF;

  RETURN v_prefixe
    || (CASE WHEN v_inclure_annee THEN v_annee || '-' ELSE '' END)
    || lpad(v_compteur::text, v_padding, '0');
END;
$$ LANGUAGE plpgsql;

-- ════════════════════════════════════════════════════════════════════════
-- Vérification rapide (optionnelle) :
--   SELECT devis_numero_debut, devis_numero_prefixe, devis_numero_inclure_annee,
--          devis_numero_padding, facture_numero_debut, facture_numero_prefixe,
--          facture_numero_inclure_annee, facture_numero_padding, numero_reset_annuel
--   FROM entreprises LIMIT 5;
-- ════════════════════════════════════════════════════════════════════════
