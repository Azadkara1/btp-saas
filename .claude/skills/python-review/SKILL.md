---
name: python-review
description: Effectue une revue de code Python priorisée (sécurité, conformité aux conventions du projet, bugs logiques) sans dupliquer ce qu'un linter fait déjà. Se déclenche sur toute demande de review, vérification, audit de code Python, d'un fichier .py, d'un diff, ou avant de commit/finaliser une fonctionnalité backend. Utiliser dès que l'utilisateur dit "review ce fichier", "vérifie mon code", "relis ça", "audit ce module", même sans mention explicite du mot "skill".
paths: ["**/*.py"]
---

# Python Code Review

## Contexte à charger avant de commencer
- Diff Python en cours (non committé) : !`git diff HEAD -- '*.py'`
- Fichiers Python modifiés : !`git diff --name-only HEAD -- '*.py'`

Si le diff est vide, demander quel(s) fichier(s) reviewer plutôt que de t'arrêter là.

## Ordre de priorité (du plus important au moins important)

### 1. 🔴 Sécurité — bloquant
- Toute requête via un client `service_role` (ou équivalent bypassant une politique de sécurité niveau ligne) DOIT filtrer explicitement par l'identifiant de l'utilisateur courant. L'absence de ce filtre = fuite de données inter-utilisateurs.
- Secrets (clés API, clés de service, IBAN, tokens...) : jamais en dur dans le code, jamais loggués, jamais transmis à un LLM externe si les conventions du projet l'interdisent explicitement.
- Toute route publique (sans authentification) : vérifier qu'elle ne renvoie jamais un modèle de données interne complet — seulement un modèle "liste blanche" dédié et minimal.
- Toute entrée utilisateur : validée avant d'être utilisée dans un calcul, une requête SQL, ou un prompt LLM.

### 2. 🟡 Conformité aux conventions du projet
- Si un fichier `CLAUDE.md` existe à la racine du projet, croiser systématiquement le code modifié avec sa table de décisions/pièges connus et sa section règles de développement. Signaler toute violation d'un piège déjà documenté (pattern à ne pas répéter, fichier à ne pas modifier sans plan, double point d'injection à synchroniser, filtre obligatoire oublié, etc.).
- Si le projet n'a pas de doc de conventions, le signaler une fois — ne pas insister à chaque review.

### 3. 🟠 Bugs & edge cases
- `None`/valeurs manquantes mal gérées, `except` trop large qui masque une erreur, valeur par défaut qui cache un bug silencieux.
- Race conditions (incrément non-atomique là où une transaction/verrou serait nécessaire).
- Cas limites métier : listes vides, division par zéro, dates invalides, montants négatifs, débordement de types.

### 4. 🟢 Style — léger, seulement si non couvert par le linter du projet
- Ne pas re-signaler ce qu'un linter/CI déjà configuré (ruff, flake8, black...) attraperait automatiquement.
- Se concentrer sur la lisibilité structurelle : fonction qui fait trop de choses à la fois, nommage trompeur, duplication évidente.

## Format de sortie
Grouper les remarques par gravité, dans cet ordre : 🔴 Bloquant → 🟡 À corriger → 🟠 Bug potentiel → 🟢 Suggestion.

Pour chaque remarque : `fichier:ligne` — description courte — pourquoi c'est un problème — correctif suggéré en 1-2 lignes (pas de réécriture complète du fichier, sauf demande explicite).

Ne pas afficher une catégorie si elle est vide (pas de "RAS" bruyant section par section). Terminer par une phrase de synthèse : nombre de points bloquants, et si le code peut être committé en l'état ou non.

## Hors scope
- Ne réécrit pas automatiquement les fichiers.
- Ne fait pas de review de fichiers non-Python (JS/TS, SQL, config...).
- Ne remplace pas les tests (pytest) ni le linter (ruff) — les complète.
