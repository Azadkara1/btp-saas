# CLAUDE.md — Contexte projet BTP SaaS

## 📍 État du projet — 13 juin 2026

### Étape 1 — MVP ✅ TERMINÉE

**Batch 1 (12 juin 2026) ✅**
Génération IA, export PDF + Word, édition inline (toutes colonnes), IBAN/BIC, logo artisan, groupement LOT, pagination multi-pages, validation formulaire artisan, numéro de document, dropdown prestations BTP (9 groupes), remise (% ou montant fixe) + acompte, format monétaire français, signature client, mentions légales + RIB.

**Batch 2 (12 juin 2026) ✅**
- Palette verte premium (`#14532D`) + modèles moderne / pro
- CP → Ville autocomplete via geo.api.gouv.fr (artisan et client)
- CP + Ville client affichés dans QuotePreview
- Prix identiques : diversification via `price_search.py` + avertissement log
- Validité devis (`validite_jours`) + conditions paiement (`conditions_paiement`) dans modèles
- Mentions légales différenciées devis / facture (+ art. 293 B CGI si sans TVA)
- TTC arrondi : dernière ligne absorbe l'écart d'arrondi
- Hauteur box client/chantier bornée à 55 mm, description tronquée à 500 chars

**Batch 3 — Passe finale (12 juin 2026) ✅**
- **PDF pagination par sections** : LOT complet = bloc insécable (bandeau + lignes + sous-total).
- **Footer insécable** : mentions légales + RIB + zone signature.
- **Numéro de document libre** : champ vide par défaut, sans auto-incrément.
- **Validité libre** : champ libre, vide → aucune mention de validité dans le PDF/Word.
- **Chantier éditable** dans QuotePreview (EditableText multiline).
- **Bug sans TVA** corrigé : mentions "TVA X%" masquées, seul art. 293 B CGI affiché.
- **CORS restreint** + **Rate limiting** 10 req/min.

**Batch 4 — Consolidation & bugfixes (13 juin 2026) ✅**
- **Fix texte invisible sur lignes prestation** : `_draw_table_header()` et `_tot_row_accent()` laissaient le text_color en blanc après leurs bandeaux → lignes prestation invisibles en cas de saut de page (big_lot) ou après la ligne TTC verte. Ajout de `_set_body()` helper + reset systématique.
- **Fix CP + Ville client dans PDF et Word** : champ `code_postal` et `ville` absents du schéma JSON du prompt → Claude ne les générait jamais. Ajout dans le schéma client du prompt + passage de ces valeurs dans le message utilisateur si l'artisan les a renseignées.
- **Consolidation `pdf_service.py`** : constante `MUTED_TEXT` par modèle, helper `_set_body()` (reset texte + trait + épaisseur), remplacement de tous les ternaires inline `P_GRAY if is_pro else (100,116,139)`.
- **Logging** : trace `[INJECT CLIENT]` dans `claude_service.py`, `[PDF]` et `[WORD]` pour déboguer la chaîne CP/Ville.

**Batch 5 — Correctifs critiques (13 juin 2026) ✅**
- **Fix texte invisible PDF (définitif)** : `_set_body()` et `_set_white()` déplacés AVANT l'en-tête (ligne ~106) pour être utilisables partout. `_set_body()` maintenant appelé : fin de l'en-tête (après `numero_document`), après chaque bandeau LOT, avant chaque sous-total. Couleur corps par modèle : moderne `#18211C`, pro `#1F2937`. Tous les `set_text_color(*WHITE)` remplacés par `_set_white()` pour la lisibilité.
- **Fix CP + Ville client (définitif)** : injection post-génération rendue INCONDITIONNELLE dans `claude_service.py` — écrase toujours ce que Claude aurait pu produire, normalise `""` → `None`. Log renommé `[INJECT CLIENT CP/VILLE]`.

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
├── models/
│   └── quote.py         # Source de vérité Pydantic
│                        #   LigneDevis    : lot?, poste, description, quantite, unite,
│                        #                   prix_unitaire_ht, tva_taux, source_prix
│                        #   ArtisanInfo   : nom, siret, adresse, code_postal, ville,
│                        #                   telephone, email, site_web, logo_base64, iban, bic
│                        #   TotauxDevis   : total_ht, total_tva, total_ttc,
│                        #                   remise_ht=0.0, total_ht_net=0.0, net_a_payer=0.0
│                        #   Devis         : client, artisan, chantier, lignes, totaux,
│                        #                   mentions_legales, notes?, numero_document?,
│                        #                   remise_type?, remise_valeur?, acompte?,
│                        #                   modele?="moderne"
│                        #   QuoteRequest  : description, region, artisan_* (11 champs),
│                        #                   client_nom, client_adresse, numero_document,
│                        #                   remise_type, remise_valeur, acompte,
│                        #                   modele?="moderne",
│                        #                   prix_personnalises?
├── routers/
│   ├── quotes.py        # POST /quotes/generate
│   ├── pdf.py           # POST /pdf/export
│   └── word.py          # POST /word/export
└── services/
    ├── claude_service.py  # Orchestration API Anthropic + boucle Tool Use agentic
    │                      #   ⚠️ Injection POST-GÉNÉRATION (jamais envoyé à Claude) :
    │                      #     adresse, cp, ville, tel, email, site_web, logo, iban, bic,
    │                      #     numero_document, remise_type, remise_valeur, acompte, modele
    ├── price_search.py    # Base de prix BTP 2026 + coefficients régionaux (12 régions)
    ├── pdf_service.py     # Génération PDF — fpdf2, A4
    │                      #   Modèle « moderne » : bandeau vert #14532D, Helvetica, lots #E3EDE6
    │                      #   Modèle « pro »     : fond blanc, Times, anthracite #1F2937,
    │                      #                        lots texte bleu acier #3B5573, filets épais
    │                      #   Logo : PIL pour aspect ratio, max 38×28 mm, décalage texte dynamique
    │                      #   Colonnes : Prestation | Description | Qté | Unité | PU HT | [TVA] | Total HT
    │                      #   Totaux enrichis : remise / HT net / TVA / TTC / acompte / net
    │                      #   Signature : 2 encadrés "Bon pour accord" + "Signature client"
    └── word_service.py    # Génération Word — python-docx
                           #   Modèle « moderne » : Calibri, fond vert #14532D en-tête
                           #   Modèle « pro »     : Georgia, anthracite, filets épais
                           #   Logo : PIL pour aspect ratio, max 4×2.5 cm
                           #   Colonnes : idem PDF
```

---

## Architecture frontend

```
frontend/src/
├── app/
│   ├── page.tsx         # Chef d'orchestre : états result (Devis|null), documentType,
│   │                    #   withTva, documentDate, modele ("moderne"|"pro")
│   │                    #   DocTypeToggle + ModelToggle côte à côte (form screen)
│   │                    #   layout max-w-5xl, palette verte #14532D
│   └── globals.css      # Palette verte :
│                        #   body #FAFAF7, .btn-primary #14532D→#0F3D21, radius 14px
│                        #   .card radius 16px, ombre discrète, bordure rgba(20,83,45,.1)
│                        #   .input-field focus ring vert, border rgba(20,83,45,.14)
├── components/
│   ├── QuoteForm.tsx    # Formulaire principal
│   │                    #   ① Textarea description + dropdown PRESTATIONS_BTP custom groupé
│   │                    #     → sélection append + fermeture au clic extérieur
│   │                    #   ② Région (select)
│   │                    #   ③ Carte « Mon entreprise » accordéon — badge « Enregistré »
│   │                    #     nom, SIRET, adresse, CP, ville, tel, email, site_web, logo, IBAN, BIC
│   │                    #   ④ Bloc client (nom client, adresse chantier)
│   │                    #   ⑤ « Mes prix habituels » accordéon
│   │                    #   ⑥ « Remise & acompte » accordéon
│   │                    #   ⑦ « Numéro de document » accordéon
│   │                    #   modele reçu en prop depuis page.tsx → envoyé dans QuoteRequest
│   │                    #   Persistance localStorage "artisan_profile" (champs artisan)
│   │                    #   ⚠️ localStorage dans useEffect uniquement (pas useState)
│   │
│   ├── QuotePreview.tsx # Aperçu éditable inline
│   │                    #   En-tête artisan : nom, SIRET, adresse, CP/ville, tél, email,
│   │                    #                     site_web, IBAN, BIC (champs conditionnels)
│   │                    #   Colonnes : Prestation | Qté | Unité | PU HT | [TVA] | Total HT
│   │                    #   Bascule modèle Moderne ↔ Pro en direct → onUpdate → PDF/Word
│   │                    #   TOTAL TTC / HT éditable : ratio = new/old appliqué à chaque PU HT
│   │                    #   Groupement LOT : headers verts (#E3EDE6/#14532D), sous-totaux
│   │                    #   Totaux enrichis (T9) : remise / HT net / TVA / TTC / acompte / net
│   │                    #   onUpdate → propage devis mis à jour à page.tsx (pour PDF/Word)
│   │
│   ├── PdfExportButton.tsx   # Bouton export PDF
│   └── WordExportButton.tsx  # Bouton export Word (.docx)
│
└── lib/
    ├── api.ts           # generateQuote, exportToPdf, exportToWord
    └── types.ts         # Miroir EXACT des modèles Pydantic — toujours synchroniser
                         #   Devis        : + modele?: string | null
                         #   QuoteRequest : + modele?: string
```

---

## Flux de données complet

```
[QuoteForm]
  ↓ QuoteRequest (description + artisan_* + numero_document + remise + acompte + modele)
[Backend /quotes/generate]
  ↓ Prompt Claude (description + région + prix artisan) — SANS infos sensibles
[Claude API — Tool Use]
  ↓ JSON brut (lignes, totaux, mentions)
[claude_service.py — injection post-Claude]
  ↓ Devis complet (+ adresse, logo, iban, bic, numero_document, remise, acompte, modele)
[QuotePreview] ← résultat affiché, éditable inline
  ↓ bascule modèle Moderne/Pro → onUpdate → page.tsx setResult
[PDF/Word export] ← envoie le Devis complet (avec devis.modele) au backend
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
| 14 | Logo artisan (aspect ratio préservé, PDF max 38×28 mm, Word max 4×2.5 cm) | `pdf_service.py`, `word_service.py` |
| 15 | Groupement par LOT (PDF + Word + aperçu) | tous les services |
| 16 | Pagination PDF multi-pages propre | `pdf_service.py` |
| 17 | Validation saisie artisan (SIRET, IBAN, BIC, email, CP) | `QuoteForm.tsx` |
| 18 | Numéro de document (DEV-…, FAC-…) | `quote.py`, `claude_service.py`, PDF, Word |
| 19 | Dropdown custom 9 groupes prestations BTP (fermeture clic extérieur) | `QuoteForm.tsx` |
| 20 | Remise (% / montant fixe) + acompte + net à payer | tous les fichiers |
| 21 | Palette verte premium #14532D + Inter | `globals.css`, `layout.tsx` |
| 22 | QuoteForm redesign : accordéons, badge Enregistré, dropdown custom | `QuoteForm.tsx` |
| 23 | Champ `modele` ("moderne"\|"pro") dans Devis + QuoteRequest | `quote.py`, `types.ts`, `claude_service.py` |
| 24 | 2 modèles PDF : moderne (vert, Helvetica) et pro (anthracite, Times) | `pdf_service.py` |
| 25 | 2 modèles Word : moderne (Calibri) et pro (Georgia) | `word_service.py` |
| 26 | Colonne Unité séparée (PDF, Word, aperçu) | `pdf_service.py`, `word_service.py`, `QuotePreview.tsx` |
| 27 | TTC éditable dans aperçu (ratio sur tous les PU HT) | `QuotePreview.tsx` |
| 28 | Bascule modèle Moderne ↔ Pro en direct + sélecteur page | `QuotePreview.tsx`, `page.tsx` |
| 29 | CP → Ville autocomplete (geo.api.gouv.fr) artisan + client | `QuoteForm.tsx` |
| 30 | CP + Ville client dans QuotePreview | `QuotePreview.tsx` |
| 31 | Prix identiques : diversification `price_search.py` + prompt + log dupliqués | `price_search.py`, `prompts.py`, `claude_service.py` |
| 32 | `validite_jours` + `conditions_paiement` dans modèles + form + PDF/Word | `quote.py`, `QuoteForm.tsx`, `pdf_service.py`, `word_service.py` |
| 33 | Mentions légales différenciées devis/facture + art. 293 B CGI | `pdf_service.py`, `word_service.py` |
| 34 | TTC arrondi — dernière ligne absorbe l'écart | `QuotePreview.tsx` |
| 35 | PDF pagination par sections (LOT = bloc insécable) | `pdf_service.py` |
| 36 | Footer insécable (mentions + RIB + signature) | `pdf_service.py` |
| 37 | Numéro de document libre (sans auto-incrément) | `QuoteForm.tsx` |
| 38 | Validité libre (vide → pas de mention) | `QuoteForm.tsx`, `quote.py`, `pdf_service.py`, `word_service.py` |
| 39 | Chantier éditable inline dans QuotePreview | `QuotePreview.tsx` |
| 40 | Bug sans TVA corrigé (masquage mentions TVA) | `pdf_service.py`, `word_service.py` |
| 41 | CORS restreint + rate limiting 10 req/min | `main.py`, `config.py`, `quotes.py` |
| 42 | CP + Ville client dans PDF et Word (via prompt + injection) | `prompts.py`, `claude_service.py`, `pdf_service.py`, `word_service.py` |
| 43 | Fix texte invisible sur lignes prestation (reset text_color après bandeaux blancs) | `pdf_service.py` |
| 44 | Consolidation pdf_service : `MUTED_TEXT`, `_set_body()`, reset systématique | `pdf_service.py` |
| 45 | Infos entreprise complètes dans l'aperçu (adresse, CP/ville, tél, email, site, IBAN, BIC) | `QuotePreview.tsx` |
| 46 | Fix définitif texte invisible PDF : `_set_body()` / `_set_white()` avant en-tête, reset LOT + sous-total, couleurs par modèle | `pdf_service.py` |
| 47 | Fix définitif CP+Ville client : injection inconditionnelle post-Claude, normalisation `""` → None | `claude_service.py` |
| 48 | Fix récurrent texte invisible PDF : double garde `_set_body()` + `pdf.set_font(FONT,"",8)` IMMÉDIATEMENT avant la boucle cellules (règle B) | `pdf_service.py` |

---

## Ce qui reste à faire — Étape 2+

| Priorité | Tâche | Détail |
|---|---|---|
| Haute | BDD PostgreSQL | Persistance des devis, comptes artisans |
| Haute | Authentification | JWT, sessions, rôles |
| Haute | Stripe | Abonnements, facturation SaaS |

---

## Décisions techniques & pièges connus

| Sujet | Décision / Piège |
|---|---|
| **fpdf2 + cp1252** | Helvetica/Times ne supportent que cp1252. La fonction `_safe()` strip les caractères hors-cp1252. `€` (0x80), `é` (0xE9), `°` (0xB0) sont valides. Pas d'espace fine U+202F. |
| **Logo PDF** | Base64 pur stocké dans `ArtisanInfo.logo_base64`. PIL (`PIL.Image.open`) pour lire les dimensions et calculer l'aspect ratio. Dimensions bornées à 38×28 mm. `text_x = 125 - text_w`, dynamique selon la largeur réelle du logo. |
| **Logo Word** | `_logo_dimensions_cm()` avec PIL, borné à 4×2.5 cm. `add_picture(width=Cm(w), height=Cm(h))` pour forcer les deux dimensions sans déformation. |
| **Logo frontend** | Data URL complet (`data:image/…;base64,…`) dans le state React. Conversion base64 pur dans `doGenerate()`. |
| **modele** | Injecté post-génération dans `claude_service.py` exactement comme `remise_type`, jamais envoyé à Claude. `pdf_service` et `word_service` lisent `devis.modele` pour choisir la palette/police. |
| **Infos artisan → Claude** | Adresse artisan, logo, IBAN, BIC, artisan_code_postal/ville, numero_document, remise, acompte, modele ne passent **jamais** dans le prompt Claude. Injection dans `claude_service.py` après génération. Client nom/adresse sont envoyés à Claude (message user) pour le JSON client. Client code_postal/ville sont injectés POST-génération de façon INCONDITIONNELLE (écrasent ce que Claude aurait pu produire), normalisant `""` → None. |
| **localStorage + SSR** | `useState` lazy initializer ne doit **pas** accéder à `localStorage` → erreur d'hydratation Next.js. Utiliser `useEffect(() => { … }, [])`. |
| **PDF Chrome** | Fix : `application/octet-stream` dans `api.ts`. |
| **Pagination PDF** | `auto_page_break=False` pendant le tableau. Stratégie : calculer `lot_total_h` (bandeau + lignes + sous-total) AVANT de dessiner. Si ça tient sur la page courante → dessin direct. Si ça tient sur une page fraîche → `add_page()` + header. Si lot > page entière (`big_lot`) → sauts par ligne avec `sub_margin` pour coller la dernière ligne au sous-total. Footer (mentions + RIB + signature) : estimation de hauteur globale, `add_page()` si insuffisant. |
| **validite_jours** | `Optional[int] = None` dans Pydantic + TypeScript. Vide → aucune mention de validité dans PDF/Word. L'injection post-Claude dans `claude_service.py` respecte `is not None`. |
| **CORS** | `allowed_origin` dans `Settings` (défaut `http://localhost:3000`). Override via `ALLOWED_ORIGIN` env var. Wildcard `*` uniquement si la valeur est `"*"`. |
| **Rate limiting** | In-memory dict par IP dans `quotes.py`. 10 requêtes / 60 s. Nettoyage de la fenêtre glissante à chaque appel. Pas de dépendance externe. |
| **Groupement LOT** | `lot: Optional[str]` sur `LigneDevis`. Order-preserving (dict Python / Map JS). Rétrocompatible : `lot=None` → rendu comme avant. |
| **Remise TVA** | Remise sur HT brut. TVA recalculée : `ratio = total_ht_net / total_ht`, `tva_par_ligne *= ratio`. |
| **TTC éditable** | `ratio = new_ttc / old_ttc` appliqué à chaque `prix_unitaire_ht`. `computeTotaux` recalcule tout. La remise fixe n'est pas rescalée (comportement voulu). |
| **Colonne Unité** | Séparée de Qté depuis la refonte. PDF with_tva : [34,54,12,13,22,14,31]. Word with_tva : [2.8,5.5,1.0,1.2,2.1,1.5,2.9] cm. |
| **Texte invisible PDF — bug récurrent** | `fpdf2` : `set_text_color` est un **état global persistant**. Le blanc des bandeaux (`_draw_table_header`, bandeau LOT, `_tot_row_accent`) saigne sur les lignes suivantes si non réinitialisé immédiatement. **3 règles à NE JAMAIS CASSER** lors de toute modification de `pdf_service.py` : (A) `_set_body()` existe et reset text_color + draw_color + line_width ; (B) `_set_body()` + `pdf.set_font(FONT,"",8)` IMMÉDIATEMENT avant la boucle de cellules de chaque ligne prestation (deux appels : en début de loop iter et juste après le rect LIGHT_GRAY) ; (C) `_set_body()` après CHAQUE élément à texte blanc (header, LOT, TTC). |

---

## Règles de développement

- **Une modification à la fois** — valider avant de continuer
- **Ne jamais modifier `quote.py`** sans cartographier l'impact sur `claude_service`, `pdf_service`, `word_service`, `lib/types.ts` et présenter le plan d'abord
- **Prompts Claude dans `prompts.py` uniquement** — jamais inline dans les services
- **`lib/types.ts` toujours synchronisé** avec les modèles Pydantic
- **UX mobile-first** — l'artisan utilise son téléphone sur le chantier
- **Les infos sensibles ne passent jamais par Claude** — injectées dans `claude_service.py` après génération. Le champ `modele` suit la même règle.
- **Nouvelles dépendances Python** → ajouter dans `requirements.txt` ET installer dans le venv
