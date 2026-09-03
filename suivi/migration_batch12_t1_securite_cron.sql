-- ════════════════════════════════════════════════════════════════════════
-- Migration Batch 12 — T1 : Correctif sécurité — expire_devis_perimes()
-- À exécuter dans l'éditeur SQL Supabase (Dashboard → SQL Editor)
-- Non destructif : uniquement des REVOKE/GRANT, aucune donnée touchée.
-- ════════════════════════════════════════════════════════════════════════

-- ⚠️ Faille corrigée : la migration T5 (Batch 11) faisait
-- `GRANT EXECUTE ... TO anon`, rendant cette fonction (qui MODIFIE des
-- données — passage en statut "expiré" sur tous les utilisateurs) appelable
-- par n'importe qui via la clé anon, publique dans le bundle JS du frontend.
--
-- Rappel Postgres : EXECUTE est accordé à PUBLIC par défaut à la création
-- d'une fonction (contrairement aux tables). Donc même sans le GRANT
-- explicite de la T5, la fonction aurait été appelable par anon tant que
-- PUBLIC n'est pas explicitement révoqué — d'où le premier REVOKE ci-dessous.

REVOKE EXECUTE ON FUNCTION expire_devis_perimes() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION expire_devis_perimes() FROM anon;
GRANT  EXECUTE ON FUNCTION expire_devis_perimes() TO service_role;

-- ════════════════════════════════════════════════════════════════════════
-- Vérification rapide (optionnelle) — doit lister service_role et rien d'autre :
--   SELECT grantee, privilege_type
--   FROM information_schema.routine_privileges
--   WHERE routine_name = 'expire_devis_perimes';
-- ════════════════════════════════════════════════════════════════════════
