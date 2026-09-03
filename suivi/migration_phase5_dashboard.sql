-- ════════════════════════════════════════════════════════════════════════
-- Migration Phase 5 — Fonction Postgres get_dashboard_stats
-- À exécuter dans l'éditeur SQL Supabase (Dashboard → SQL Editor)
-- Prérequis : migration_phase1_phase2.sql déjà exécutée (colonnes date_envoi,
-- date_signature, date_paiement, date_refus, index user_id/statut/date_document)
-- ════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION get_dashboard_stats(p_user_id uuid)
RETURNS jsonb
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
  result jsonb;
BEGIN
  WITH docs AS (
    SELECT * FROM documents WHERE user_id = p_user_id
  ),
  ca_par_statut AS (
    SELECT
      COALESCE(SUM(total_ttc) FILTER (WHERE statut = 'signé'), 0)  AS ca_signe,
      COALESCE(SUM(total_ttc) FILTER (WHERE statut = 'envoyé'), 0) AS ca_en_attente,
      COALESCE(SUM(total_ttc) FILTER (WHERE statut = 'payé'), 0)   AS ca_encaisse
    FROM docs
  ),
  -- Conversion devis → signé : parmi les devis sortis du brouillon (date_envoi renseignée),
  -- quelle proportion a atteint le statut signé (date_signature renseignée).
  conversion AS (
    SELECT
      COUNT(*) FILTER (WHERE type_doc = 'devis' AND date_envoi IS NOT NULL)     AS nb_envoyes,
      COUNT(*) FILTER (WHERE type_doc = 'devis' AND date_signature IS NOT NULL) AS nb_signes
    FROM docs
  ),
  -- Panier moyen et CA mensuel excluent les brouillons (pas encore de business réel)
  panier AS (
    SELECT COALESCE(AVG(total_ttc), 0) AS panier_moyen
    FROM docs WHERE statut <> 'brouillon' AND total_ttc IS NOT NULL
  ),
  delai AS (
    SELECT AVG(EXTRACT(EPOCH FROM (date_signature - date_envoi)) / 86400.0) AS delai_moyen
    FROM docs WHERE date_envoi IS NOT NULL AND date_signature IS NOT NULL
  ),
  repartition AS (
    SELECT jsonb_object_agg(statut, cnt) AS data
    FROM (SELECT statut, COUNT(*) AS cnt FROM docs GROUP BY statut) s
  ),
  -- Série des 12 derniers mois (y compris ceux sans documents → CA à 0)
  mois_serie AS (
    SELECT to_char(d, 'YYYY-MM') AS mois, d AS mois_date
    FROM generate_series(
      date_trunc('month', now()) - interval '11 months',
      date_trunc('month', now()),
      interval '1 month'
    ) AS d
  ),
  ca_mois AS (
    SELECT ms.mois, ms.mois_date, COALESCE(SUM(docs.total_ttc), 0) AS ca
    FROM mois_serie ms
    LEFT JOIN docs
      ON date_trunc('month', docs.date_document) = ms.mois_date
     AND docs.statut <> 'brouillon'
    GROUP BY ms.mois, ms.mois_date
  ),
  ca_par_mois_json AS (
    SELECT jsonb_agg(jsonb_build_object('mois', mois, 'ca', ca) ORDER BY mois_date) AS data
    FROM ca_mois
  ),
  -- Top prestations : éclate le JSONB devis_payload->lignes de chaque document
  lignes AS (
    SELECT
      (ligne->>'poste') AS poste,
      COALESCE((ligne->>'prix_unitaire_ht')::numeric, 0)
        * COALESCE((ligne->>'quantite')::numeric, 1) AS montant
    FROM docs, jsonb_array_elements(COALESCE(docs.devis_payload->'lignes', '[]'::jsonb)) AS ligne
    WHERE docs.statut <> 'brouillon'
  ),
  top_prestations AS (
    SELECT jsonb_agg(jsonb_build_object('poste', poste, 'ca', ca) ORDER BY ca DESC) AS data
    FROM (
      SELECT poste, ROUND(SUM(montant)::numeric, 2) AS ca
      FROM lignes
      WHERE poste IS NOT NULL
      GROUP BY poste
      ORDER BY SUM(montant) DESC
      LIMIT 10
    ) t
  )
  SELECT jsonb_build_object(
    'ca_signe',       (SELECT ca_signe FROM ca_par_statut),
    'ca_en_attente',  (SELECT ca_en_attente FROM ca_par_statut),
    'ca_encaisse',    (SELECT ca_encaisse FROM ca_par_statut),
    'taux_conversion', (
      SELECT CASE WHEN nb_envoyes > 0 THEN ROUND((nb_signes::numeric / nb_envoyes) * 100, 1) ELSE 0 END
      FROM conversion
    ),
    'panier_moyen', (SELECT ROUND(panier_moyen::numeric, 2) FROM panier),
    'delai_moyen_signature_jours', (SELECT ROUND(delai_moyen::numeric, 1) FROM delai),
    'repartition_statuts', COALESCE((SELECT data FROM repartition), '{}'::jsonb),
    'ca_par_mois',         COALESCE((SELECT data FROM ca_par_mois_json), '[]'::jsonb),
    'top_prestations',     COALESCE((SELECT data FROM top_prestations), '[]'::jsonb)
  ) INTO result;

  RETURN result;
END;
$$;

-- ════════════════════════════════════════════════════════════════════════
-- Vérification rapide (remplacer par un vrai user_id) :
--   SELECT get_dashboard_stats('00000000-0000-0000-0000-000000000000'::uuid);
-- ════════════════════════════════════════════════════════════════════════
