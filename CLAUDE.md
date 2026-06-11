# CLAUDE.md — Contexte projet BTP SaaS

## 📍 État du projet — 11 juin 2026

### Étape 1 — MVP (en cours · ~93 % fait)

**Tout ce qui est implémenté ✅**
Génération IA, export PDF + Word, édition inline (toutes colonnes), IBAN/BIC, logo artisan, groupement LOT, pagination multi-pages, validation formulaire artisan, numéro de document, dropdown prestations BTP (9 groupes), remise (% ou montant fixe) + acompte, format monétaire français, signature client, mentions légales + RIB.

**Ce qui reste à faire ⏳**
- **Bug prix** : l'IA retourne parfois des tarifs identiques pour plusieurs postes → retravailler `price_search.py` ou le prompt
- **Numéro de document auto-incrémenté** : actuellement saisie manuelle uniquement

### Étape 2 — Persistance & Monétisation — non commencée
PostgreSQL, authentification utilisateurs, abonnements Stripe.

### Étape 3 — Mobile & Vision — non commencée
Saisie vocale (speech-to-text), vision IA (analyse plans/photos).

---

## Rôle
Tu es Lead Developer et Architecte Solutions IA sur ce projet.
Tu travailles avec un Data Analyst (pas développeur). Explique chaque modification
simplement avant de l'appliquer. Une tâche à la fois, attends validation avant de continuer.

---

## Vision produit
SaaS permettant aux artisans et PME du BTP de générer des **devis et factures professionnels**
à partir d'une description texte libre. L'IA interprète, recherche les prix du marché,
et produit un document PDF + Word prêt à envoyer au client.

---

## Stack technique

| Couche | Techno | Détail |
|---|---|---|
| Frontend | Next.js 14 + Tailwind CSS | port 3000 |
| Backend | FastAPI, Python 3.11, venv | port 8000 |
| IA | API Anthropic `claude-sonnet-4-6` | Tool Use pour les prix |
| PDF | fpdf2 (pur Python) | WeasyPrint abandonné — incompatible Windows |
| Word | python-docx (pur Python) | export .docx modifiable |
| BDD | — | Étape 2 : PostgreSQL |
| Auth | — | Étape 2 |

---

## Commandes de démarrage (Windows)

### Backend
```bash
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm run dev
```

> ⚠️ Modifier un `.py` → rechargement auto uvicorn  
> ⚠️ Modifier `.env` → redémarrage manuel obligatoire (Ctrl+C puis relancer)

---

## Architecture backend

```
backend/app/
├── core/
│   ├── config.py        # Settings via pydantic-settings (.env)
│   └── prompts.py       # ⚠️ Prompts Claude ICI UNIQUEMENT — jamais inline dans les services
│                        #   Inclut les règles de groupement par LOT
├── models/
│   └── quote.py         # Source de vérité Pydantic — TOUJOURS vérifier l'impact sur
│                        #   claude_service / pdf_service / word_service / lib/types.ts
│                        #   avant toute modification
│                        #
│                        #   LigneDevis    : lot?, poste, description, quantite, unite,
│                        #                   prix_unitaire_ht, tva_taux, source_prix
│                        #   ArtisanInfo   : nom, siret, adresse, code_postal, ville,
│                        #                   telephone, email, site_web, logo_base64, iban, bic
│                        #   TotauxDevis   : total_ht, total_tva, total_ttc,
│                        #                   remise_ht=0.0, total_ht_net=0.0, net_a_payer=0.0
│                        #   Devis         : client, artisan, chantier, lignes, totaux,
│                        #                   mentions_legales, notes?, numero_document?,
│                        #                   remise_type?, remise_valeur?, acompte?
│                        #   QuoteRequest  : description, region, artisan_* (11 champs),
│                        #                   client_nom, client_adresse, numero_document,
│                        #                   remise_type, remise_valeur, acompte,
│                        #                   prix_personnalises?
├── routers/
│   ├── quotes.py        # POST /quotes/generate
│   ├── pdf.py           # POST /pdf/export
│   └── word.py          # POST /word/export
└── services/
    ├── claude_service.py  # Orchestration API Anthropic + boucle Tool Use agentic
    │                      #   ⚠️ Injection POST-GÉNÉRATION (jamais envoyé à Claude) :
    │                      #     adresse, cp, ville, tel, email, site_web, logo, iban, bic,
    │                      #     numero_document, remise_type, remise_valeur, acompte
    ├── price_search.py    # Base de prix BTP 2026 + coefficients régionaux (12 régions)
    ├── pdf_service.py     # Génération PDF — fpdf2, A4, Helvetica + cp1252
    │                      #   Logo : w=38 mm côte-à-côte avec le texte artisan (x=57)
    │                      #   Tableau : auto_page_break=False pendant rendu, sauts manuels
    │                      #   Totaux enrichis : remise / HT net / TVA / TTC / acompte / net
    │                      #   Signature : 2 encadrés "Bon pour accord" + "Signature client"
    └── word_service.py    # Génération Word — python-docx
                           #   Logo : Cm(4.5) dans cell gauche de l'en-tête
                           #   Totaux enrichis : idem PDF, ligne verte pour NET À PAYER
```

---

## Architecture frontend

```
frontend/src/
├── app/
│   ├── page.tsx         # Chef d'orchestre : états result (Devis|null), documentType,
│   │                    #   withTva, documentDate — layout max-w-5xl (1024px)
│   └── globals.css      # Styles globaux Tailwind
├── components/
│   ├── QuoteForm.tsx    # Formulaire principal
│   │                    #   ① Textarea description + dropdown PRESTATIONS_BTP (9 groupes)
│   │                    #     → sélection append au textarea, select reset à ""
│   │                    #   ② Numéro de document (libre, ex: DEV-2026-001)
│   │                    #   ③ Région (pour prix du marché)
│   │                    #   ④ "Mes prix habituels" : saisie nom/prix/unité, badge Votre prix
│   │                    #   ⑤ "Remise et acompte" : type (%/fixe), valeur, acompte versé
│   │                    #   ⑥ "Informations optionnelles" : artisan (nom, siret, adresse,
│   │                    #     cp, ville, tel, email, site_web, logo, iban, bic) + client
│   │                    #   Validation non bloquante : SIRET 14 chiffres, IBAN, BIC, email,
│   │                    #     code postal 5 chiffres → panneau avertissements + "Générer quand même"
│   │                    #   Persistance localStorage "artisan_profile" (champs artisan)
│   │                    #   ⚠️ localStorage dans useEffect uniquement (pas useState → hydratation SSR)
│   │
│   ├── QuotePreview.tsx # Aperçu éditable inline
│   │                    #   Champs éditables : Poste, Description, Lot, Qté, Unité,
│   │                    #     PU HT, TVA (select), Total HT (back-calcule PU)
│   │                    #   Groupement LOT : headers slate-600, sous-totaux par groupe
│   │                    #   Totaux enrichis (T9) :
│   │                    #     - Remise : select type + input valeur → affiche - X €
│   │                    #     - Total HT net (si remise)
│   │                    #     - TVA recalculée proportionnellement (ratio ht_net/ht_brut)
│   │                    #     - Total TTC ou Total HT (selon mode TVA)
│   │                    #     - Acompte versé (input numérique)
│   │                    #     - NET À PAYER (fond vert, si acompte > 0)
│   │                    #   onUpdate → propage devis mis à jour à page.tsx (pour PDF/Word)
│   │
│   ├── PdfExportButton.tsx   # Bouton export PDF
│   └── WordExportButton.tsx  # Bouton export Word (.docx)
│
└── lib/
    ├── api.ts           # generateQuote, exportToPdf (application/octet-stream), exportToWord
    └── types.ts         # ⚠️ Miroir EXACT des modèles Pydantic — toujours synchroniser
                         #   TotauxDevis  : total_ht, total_tva, total_ttc,
                         #                  remise_ht?, total_ht_net?, net_a_payer?
                         #   Devis        : + numero_document?, remise_type?,
                         #                  remise_valeur?, acompte?
                         #   QuoteRequest : + numero_document?, remise_type?,
                         #                  remise_valeur?, acompte?
```

---

## Flux de données complet

```
[QuoteForm]
  ↓ QuoteRequest (description + artisan_* + numero_document + remise + acompte)
[Backend /quotes/generate]
  ↓ Prompt Claude (description + région + prix artisan) — SANS infos sensibles
[Claude API — Tool Use]
  ↓ JSON brut (lignes, totaux, mentions)
[claude_service.py — injection post-Claude]
  ↓ Devis complet (+ adresse, logo, iban, bic, numero_document, remise, acompte)
[QuotePreview] ← résultat affiché, éditable inline
[PDF/Word export] ← envoie le Devis complet au backend
```

---

## Fonctionnalités implémentées ✅

| # | Fonctionnalité | Fichiers clés |
|---|---|---|
| 1 | Génération devis par texte libre → JSON Claude | `claude_service.py`, `prompts.py` |
| 2 | Tool Use : recherche prix du marché manquants | `price_search.py`, `claude_service.py` |
| 3 | Mes prix habituels (badge "Votre prix") | `QuoteForm.tsx` |
| 4 | Édition inline : Poste, Desc, Lot, Qté, Unité, PU HT, TVA, Total HT | `QuotePreview.tsx` |
| 5 | Toggle Devis / Facture | `page.tsx` |
| 6 | Toggle Avec / Sans TVA (+ mention art. 293 B CGI) | `page.tsx`, `pdf_service.py` |
| 7 | Sélecteur de date | `page.tsx` |
| 8 | Export PDF professionnel (fpdf2) | `pdf_service.py` |
| 9 | Export Word (.docx) | `word_service.py` |
| 10 | IBAN / BIC artisan dans PDF et Word | `quote.py`, `claude_service.py`, `pdf_service.py`, `word_service.py` |
| 11 | Prompt IA détaillé (DTU, normes, 5–10 lignes) | `prompts.py` |
| 12 | Layout large max-w-5xl | `page.tsx` |
| 13 | Infos entreprise complètes + persistance localStorage | `QuoteForm.tsx` |
| 14 | Logo artisan (PDF h=38 mm côte-à-côte, Word Cm(4.5)) | `pdf_service.py`, `word_service.py` |
| 15 | Groupement par LOT (PDF + Word + aperçu) | tous les services |
| 16 | Pagination PDF multi-pages propre | `pdf_service.py` |
| 17 | Validation saisie artisan (SIRET, IBAN, BIC, email, CP) | `QuoteForm.tsx` |
| 18 | Numéro de document (DEV-…, FAC-…) | `quote.py`, `claude_service.py`, PDF, Word |
| 19 | Dropdown 9 groupes prestations BTP | `QuoteForm.tsx` |
| 20 | Remise (% / montant fixe) + acompte + net à payer | tous les fichiers |

---

## Ce qui reste à faire — Étape 1

| Priorité | Tâche | Détail |
|---|---|---|
| Haute | Bug prix identiques | L'IA retourne parfois le même prix pour tous les postes. Piste : enrichir `price_search.py` ou améliorer le prompt pour forcer la variété. |
| Basse | Numéro auto-incrémenté | Actuellement : saisie manuelle. Futur : compteur persisté en BDD (Étape 2) ou localStorage. |

---

## Décisions techniques & pièges connus

| Sujet | Décision / Piège |
|---|---|
| **fpdf2 + cp1252** | Helvetica ne supporte que cp1252. La fonction `_safe()` strip les caractères hors-cp1252. `€` (0x80), `é` (0xE9), `°` (0xB0) sont valides. Pas d'espace fine U+202F (0x202F hors cp1252 → crash). |
| **Logo PDF** | Base64 pur stocké dans `ArtisanInfo.logo_base64`. Frontend envoie `split(",")[1]` du data URL. Largeur fixe `w=38 mm`, texte artisan démarre à `x=57`. |
| **Logo frontend** | Data URL complet (`data:image/…;base64,…`) dans le state React. Conversion base64 pur dans `doGenerate()`. |
| **Infos artisan → Claude** | Adresse, logo, IBAN, BIC, numero_document, remise, acompte ne passent **jamais** dans le prompt Claude. Injection dans `claude_service.py` après génération. |
| **localStorage + SSR** | `useState` lazy initializer ne doit **pas** accéder à `localStorage` → erreur d'hydratation Next.js. Utiliser `useEffect(() => { … }, [])`. |
| **PDF Chrome** | Le viewer natif Chrome intercepte les blobs `application/pdf` même avec `download`. Fix : `application/octet-stream` dans `api.ts`. |
| **Pagination PDF** | `auto_page_break=True` + `multi_cell` → cascade si saut en milieu de ligne (`y_start` obsolète). Fix : `auto_page_break=False` pendant le tableau, sauts gérés manuellement avant chaque ligne. |
| **Groupement LOT** | `lot: Optional[str]` sur `LigneDevis`. Order-preserving (dict Python / Map JS). Rétrocompatible : `lot=None` → rendu comme avant. |
| **Remise TVA** | Remise sur HT brut. TVA recalculée : `ratio = total_ht_net / total_ht`, `tva_par_ligne *= ratio`. |
| **Remise/acompte → Claude** | `remise_type`, `remise_valeur`, `acompte` injectés post-génération, jamais envoyés à Claude. |

---

## Règles de développement

- **Une modification à la fois** — valider avant de continuer
- **Ne jamais modifier `quote.py`** sans cartographier l'impact sur `claude_service`, `pdf_service`, `word_service`, `lib/types.ts` et présenter le plan d'abord
- **Prompts Claude dans `prompts.py` uniquement** — jamais inline dans les services
- **`lib/types.ts` toujours synchronisé** avec les modèles Pydantic
- **UX mobile-first** — l'artisan utilise son téléphone sur le chantier
- **Les infos sensibles ne passent jamais par Claude** — injectées dans `claude_service.py` après génération
- **Nouvelles dépendances Python** → ajouter dans `requirements.txt` ET installer dans le venv
- **NE PAS** faire un système de choix entre templates / modèles de documents
