# CLAUDE.md — Contexte projet BTP SaaS

> 📜 Historique détaillé de chaque batch/lot (ce qui a été fait, quand, pourquoi) : voir [CHANGELOG.md](./CHANGELOG.md). Ce fichier-ci ne garde que ce qui aide à écrire du code aujourd'hui.

## 📍 État d'avancement

- **Étape 1 (MVP)** ✅ en production (Render + Vercel) — génération IA, PDF/Word, 2 modèles, import.
- **Étape 2 (Persistance & Monétisation)** en cours : Auth Supabase, profil, documents/historique, numérotation auto, dashboard, clients ✅ faits. **Reste : Lot 5 — Stripe** (abonnements Freemium/Pro, quotas devis/mois).
- **Batch 11** ✅ : assurance pro obligatoire, soft delete documents, tests pytest PDF/Word (non-régression), envoi par email (Resend), expiration auto des devis.
- **Batch 12** ✅ : sécurité du cron, CI (ruff+pytest, tsc+build), signature électronique publique (+ signature à main levée), spécificités BTP (facture d'acompte/solde, retenue de garantie, TVA réduite, autoliquidation).
- **Batch 13** ✅ : `CLAUDE.md` allégé (historique déplacé dans `CHANGELOG.md`), numérotation devis/facture personnalisable par compte (point de départ, préfixe, padding, reset annuel).
- **Batch 14** ✅ : notification email auto à la signature (PDF signé), numéro provisoire dès la génération, historique en onglets Devis/Facture, suppression élargie à tous les statuts, nom client éditable, logo → accueil.
- **Batch 15** ✅ : hotfixes post-déploiement (retour accueil réel, header mobile responsive, numéro provisoire synchronisé sur la bascule Devis/Facture) + config Render/Vercel/GitHub Actions corrigée (3 incidents de variables manquantes).
- **Batch 16** ✅ : revue de code complète (4 axes) — 3 bugs bloquants corrigés (mélange de données entre documents dans QuotePreview, transitions de statut non validées côté serveur, double-facturation silencieuse possible sur `convert_to_facture`) + persistance des modifications post-génération (`PUT /documents/{id}`, restreint aux brouillons).
- **Batch 17** ✅ : apurement complet de la dette technique identifiée au Batch 16 — validation Pydantic (bornes remise/acompte/retenue), fuite de police PDF pagination, `convert_to_facture` exige un devis signé, boutons de statut non désactivés, migration SQL rejouable, rate limiter (IP réelle derrière le proxy + fuite mémoire), 27 messages d'erreur bruts assainis, couverture de tests élargie (numéro légal RPC, clients, dashboard, email, storage, rate limiter, parité des injections artisan). **125/125 tests.**
- **Batch 18** ✅ : CI backend cassé (import de `claude_service.py` au niveau module → `get_settings()` échoue sans secrets CI, valeurs factices ajoutées à `ci.yml`), retrait de la condition "devis signé" sur `create-acompte` (trop restrictive, jamais demandée telle quelle), `flushUpdateSave()` pour éliminer la fenêtre de course où naviguer vers Historique/Clients juste après une frappe pouvait rouvrir le document avant l'envoi du `PUT` débattu.
- **Batch 19** ✅ : `MAX_OUTPUT_TOKENS` (génération ET import PDF/.docx) relevé de 8192/8000 à 64000 — un gros devis (chantier multi-lots) ou un document importé volumineux se terminait en erreur "trop volumineux" (réponse Claude tronquée). Les 3 appels concernés passent en streaming (`client.messages.stream()` + `get_final_message()`) car le SDK refuse un `max_tokens` aussi élevé sur une requête non-streamée. Vérifié en conditions réelles contre l'API (pas seulement mocké) : devis 8 lots/22 lignes généré sans troncature.
- **Étape 3 (Mobile & Vision)** — non commencée (saisie vocale, vision IA plans/photos).

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
| BDD | Supabase (Postgres managé) | 3 tables avec RLS — Lot 2 : persistance |
| Auth | Supabase Auth | JWT asymétrique ES256/RS256 via JWKS, cookie SSR, `PyJWT[crypto]` |
| Graphiques | recharts | Dashboard — BarChart CA/mois, PieChart statuts |

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

> ⚠️ Modifier un `.py` → rechargement auto uvicorn (peut se figer en session longue, cf. pièges ci-dessous)
> ⚠️ Modifier `.env` → redémarrage manuel obligatoire (Ctrl+C puis relancer)

### Tests (non-régression PDF/Word)
```bash
cd backend
venv\Scripts\activate
pytest
```

---

## Déploiement (Render + Vercel)

Backend → **Render**. Frontend → **Vercel**.

> ⚠️ **Toute fonctionnalité qui lit une nouvelle variable d'environnement doit être ajoutée
> ici ET dans le dashboard concerné, dans le même batch.** C'est la cause n°1 des pannes de
> production sur ce projet (3 incidents : crash du middleware Vercel, 401 généralisés,
> lien de signature pointant vers `localhost` en prod — `FRONTEND_URL` oubliée sur Render).
> Vérifier cette section fait partie de la définition de « terminé » pour toute feature.
> ⚠️ Piège aggravant : la plupart de ces variables ont un défaut silencieux dans `config.py`
> (`frontend_url`, `supabase_url`, etc.) — leur absence ne fait PAS planter le démarrage,
> elle casse juste une fonctionnalité précise, découverte bien plus tard par un utilisateur.

### Variables Render (backend)

| Variable | Où la récupérer | Note |
|---|---|---|
| `ANTHROPIC_API_KEY` | console Anthropic | — |
| `PYTHON_VERSION` | — | 3.11 |
| `ALLOWED_ORIGIN` | URL Vercel de production | Pas `localhost:3000` en prod, sinon erreur CORS |
| `FRONTEND_URL` | URL Vercel de production | Sert à construire les liens publics envoyés au client (ex. lien de signature `/devis/{token}`) — défaut `http://localhost:3000` si absente, donc **silencieux** : le lien généré en prod pointe vers un poste local si on l'oublie. Incident réel : Batch 15. |
| `SUPABASE_URL` | Supabase → Project Settings → Data API → *Project URL* | **Doit être identique** à `NEXT_PUBLIC_SUPABASE_URL` côté Vercel |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase → Project Settings → API Keys (`service_role` / `sb_secret_*`) | Jamais côté frontend, jamais dans git |
| `RESEND_API_KEY` | dashboard Resend | Jamais côté frontend |
| `RESEND_FROM_EMAIL` | — | Format `DevisBTP <noreply@domaine.fr>` — à définir une fois un domaine vérifié sur resend.com/domains. ⚠️ Cette table citait auparavant `EMAIL_FROM`, un nom qui n'existe nulle part dans le code (`config.py::resend_from_email` lit `RESEND_FROM_EMAIL`) — corrigé le 29/09/2026, trouvé par revue de code. Sans le bon nom, `extra="ignore"` avale la variable silencieusement et l'expéditeur reste `onboarding@resend.dev`. |
| `CLAUDE_MODEL` | — | Optionnel, défaut `claude-sonnet-4-6` dans `config.py` |

### Variables Vercel (frontend)

| Variable | Où la récupérer |
|---|---|
| `NEXT_PUBLIC_API_URL` | URL du service Render, **sans slash final** |
| `NEXT_PUBLIC_SUPABASE_URL` | même valeur que `SUPABASE_URL` côté Render |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Supabase → API Keys (`sb_publishable_*`) |

### Règles de configuration

- **Aucune variable `NEXT_PUBLIC_*` ne doit être marquée « Sensitive » / « Secret » sur
  Vercel.** Elles sont inlinées dans le bundle envoyé au navigateur, donc publiques par
  nature. Le type secret les rend illisibles au build → valeur vide, sans erreur explicite.
- **Les `NEXT_PUBLIC_*` sont gravées dans le bundle au moment du build** → toute
  modification exige un **redéploiement**. Changer la valeur sans rebuild ne change rien.
- **Une même variable se coche sur plusieurs environnements** (Production + Preview), on ne
  duplique pas l'entrée — sauf si la valeur doit réellement différer (ex. un backend de test
  distinct par environnement).
- Render redémarre le service automatiquement après un changement de variable (vérifier
  l'onglet *Events*) ; Vercel non.

---

## Architecture backend

```
backend/app/
├── core/
│   ├── config.py        # Settings via pydantic-settings (.env)
│   │                    #   supabase_url: str + supabase_jwks_url (dérivée)
│   │                    #   supabase_service_role_key: str (requis, Lot 2)
│   ├── auth.py          # Dépendance get_current_user (Étape 2 Lot 1)
│   │                    #   PyJWKClient singleton (cache 5 min), vérifie RS256/ES256
│   │                    #   Retourne CurrentUser(user_id=sub, email)
│   │                    #   HTTP 401 si token invalide/expiré, 403 si header absent
│   ├── supabase_client.py  # Singleton get_supabase_admin() — client service_role (Lot 2)
│   │                    #   ⚠️ Bypass RLS → filtrage user_id OBLIGATOIRE sur chaque requête
│   └── prompts.py       # ⚠️ Prompts Claude ICI UNIQUEMENT — jamais inline dans les services
├── models/
│   ├── quote.py         # Source de vérité Pydantic (NE PAS MODIFIER sans plan)
│   ├── profile.py       # ProfileEntreprise (Lot 2) — distinct d'ArtisanInfo
│                        #   + assurance_nom/contrat/couverture (Batch 11 T1)
│                        #   + devis_numero_*/facture_numero_*/numero_reset_annuel
│                        #     (config numérotation, Batch 13 T2 — pas les compteurs runtime)
│                        #   LigneDevis    : lot?, poste, description, quantite, unite,
│                        #                   prix_unitaire_ht, tva_taux, source_prix
│                        #   ArtisanInfo   : nom, siret, adresse, code_postal, ville,
│                        #                   telephone, email, site_web, logo_base64, iban, bic,
│                        #                   assurance_nom/contrat/couverture (Batch 11 T1)
│                        #   TotauxDevis   : total_ht, total_tva, total_ttc,
│                        #                   remise_ht=0.0, total_ht_net=0.0, net_a_payer=0.0
│                        #   Devis         : client, artisan, chantier, lignes, totaux,
│                        #                   mentions_legales, notes?, numero_document?,
│                        #                   remise_type?, remise_valeur?, acompte?,
│                        #                   retenue_garantie_taux?, type_facture?, autoliquidation,
│                        #                   modele?="moderne", afficher_signature=True
│                        #   QuoteRequest  : description, region, artisan_* (11 champs),
│                        #                   client_nom, client_adresse, numero_document,
│                        #                   remise_type, remise_valeur, acompte,
│                        #                   retenue_garantie_taux, autoliquidation,
│                        #                   modele?="moderne",
│                        #                   prix_personnalises?
│                        #   QuoteResponse : success, devis?, error?, tokens_used?,
│                        #                   import_meta? (UNIQUEMENT renseigné par l'import)
│   ├── document.py      # DocumentCreate, DocumentSummary, DocumentDetail,
│   │                    #   StatusUpdate, StatusPatchResponse, CreateAcompteRequest
│   │                    #   StatutDocument = Literal[...6 statuts...]
│   │                    #   + document_source_id, date_envoi/signature/paiement/refus,
│   │                    #   signature_nom_signataire, signature_image_base64 (Detail seul)
│   ├── client.py        # ClientSummary, ClientDetail, ClientUpdate
│   ├── public.py        # PublicArtisanInfo/PublicClientInfo (whitelists), PublicDevisView,
│   │                    #   AcceptSignatureRequest, PublicActionResponse (Batch 12 T3)
│   ├── pdf.py            # PdfRequest — devis + signature_nom_signataire/image/date (métadonnées
│   │                    #   document, jamais dans Devis)
│   └── dashboard.py     # DashboardStats, CaMoisPoint, TopPrestation
├── routers/
│   ├── quotes.py        # POST /quotes/generate  +  POST /quotes/import
│   ├── pdf.py           # POST /pdf/export
│   ├── word.py          # POST /word/export
│   ├── profile.py       # GET /profile (404 si absent) + PUT /profile (upsert) — Lot 2
│   │                    #   PUT verrouille devis/facture_numero_debut si un numéro existe déjà
│   │                    #     pour ce type (_numero_debut_locked, 409 sinon) — Batch 13 T2
│   │                    #   GET /profile/numerotation-status → locked + prochain compteur brut
│   │                    #     (devis + facture), lecture seule (Batch 13 T2)
│   │                    #   Dépend de get_current_user + get_supabase_admin
│   │                    #   Filtrage user_id obligatoire (client service_role bypass RLS)
│   ├── documents.py     # POST /documents (brouillon + upsert client par nom)
│   │                    #   GET /documents (historique, batch-fetch noms clients)
│   │                    #   GET /documents/{id} (devis_payload complet pour réouverture)
│   │                    #   PATCH /documents/{id} (statut ; horodatage idempotent ;
│   │                    #     brouillon→envoyé → get_next_numero)
│   │                    #   POST /documents/{id}/convert (devis→facture, document_source_id ;
│   │                    #     détecte une facture d'acompte existante → devient facture de solde)
│   │                    #   POST /documents/{id}/duplicate (copie conforme)
│   │                    #   POST /documents/{id}/create-acompte (facture d'acompte séparée,
│   │                    #     devis signé requis — fonction pure _build_acompte_devis)
│   │                    #   DELETE /documents/{id} (soft delete deleted_at, 409 si non-brouillon/refusé)
│   │                    #   GET /documents/{id}/signature-link (génère token à la demande)
│   │                    #   POST /documents/{id}/send (email Resend + archivage + transition)
│   │                    #   _row_to_detail() helper commun ; _statut_transition_update() partagé
│   │                    #   avec routers/public.py ; Filtrage user_id obligatoire partout
│   ├── public.py        # ⚠️ AUCUNE authentification — routeur séparé par design (Batch 12 T3)
│   │                    #   GET /public/devis/{token}, POST .../accept, POST .../refuse
│   ├── clients.py       # GET /clients (nb docs + CA total, agrégés en Python)
│   │                    #   GET /clients/{id} (fiche + historique) — PUT /clients/{id}
│   │                    #   Filtrage user_id obligatoire
│   └── dashboard.py     # GET /dashboard/stats → appelle la RPC get_dashboard_stats
│                        #   (agrégation 100% SQL, jamais de boucle Python)
└── services/
    ├── claude_service.py  # Orchestration API Anthropic + boucle Tool Use agentic
    │                      #   ⚠️ Injection POST-GÉNÉRATION (jamais envoyé à Claude) :
    │                      #     adresse, cp, ville, tel, email, site_web, logo, iban, bic,
    │                      #     assurance_nom/contrat/couverture, numero_document,
    │                      #     remise_type, remise_valeur, acompte, retenue_garantie_taux,
    │                      #     autoliquidation, modele, afficher_signature
    │                      #   ⚠️ Tout champ artisan_* doit AUSSI être injecté dans
    │                      #     import_service.py::_inject_artisan (2e point d'injection)
    ├── import_service.py  # Import PDF/.docx → extraction Claude → QuoteResponse + import_meta
    │                      #   PDF : bloc document natif base64 (Claude lit directement)
    │                      #   .docx : python-docx → texte plat → Claude texte
    │                      #   MAX_OUTPUT_TOKENS = 64000, appel en streaming (Batch 19)
    │                      #   _parse_import_response : détecte stop_reason="max_tokens",
    │                      #                            logue réponse brute sur échec
    │                      #   _inject_artisan : écrase artisan extrait par profil localStorage
    ├── numero_service.py  # get_next_numero(user_id, type_doc) — appelle RPC Postgres (numérotation
    │                      #     LÉGALE, atomique, formatage inclus dans la fonction SQL)
    │                      #   Jamais d'incrément côté Python (race condition) — toujours via RPC
    │                      #   format_numero()/compute_next_compteur() : fonctions PURES, reflètent
    │                      #     le CASE SQL — utilisées UNIQUEMENT par preview_next_compteur()
    │                      #     (lecture seule, aperçu UI, jamais le numéro légal) — Batch 13 T2
    ├── dashboard_service.py  # get_dashboard_stats_raw(user_id) — appelle la RPC get_dashboard_stats
    │                      #   Normalisation défensive du retour (même pattern que numero_service.py)
    ├── email_service.py    # send_devis_email() — Resend, appel REST direct via httpx
    ├── storage_service.py  # archive_document_pdf() — Storage bucket privé, best-effort
    ├── price_search.py    # Base de prix BTP 2026 + coefficients régionaux (12 régions)
    ├── pdf_service.py     # Génération PDF — fpdf2, A4
    │                      #   Modèle « moderne » : bandeau vert #14532D, Helvetica, lots #E3EDE6
    │                      #   Modèle « pro »     : fond blanc, Times, anthracite #1F2937,
    │                      #                        lots texte bleu acier #3B5573, filets épais
    │                      #   Logo : PIL pour aspect ratio, max 38×28 mm, décalage texte dynamique
    │                      #   Colonnes : Prestation | Description | Qté | Unité | PU HT | [TVA] | Total HT
    │                      #   Totaux enrichis : remise / HT net / TVA / TTC / acompte / retenue
    │                      #     de garantie (chaînable avec l'acompte) / net à payer
    │                      #   Mentions TVA calculées à l'affichage (jamais stockées) : art. 293 B,
    │                      #     taux réduit 10%/5.5% (attestation), autoliquidation — mutuellement
    │                      #     exclusives, cf. pièges
    │                      #   Signature : 2 encadrés "Bon pour accord" + "Signature client"
    │                      #     — conditionnels à devis.afficher_signature (footer_h -34mm si masqué)
    │                      #     — signature électronique (nom/image/date) passée en paramètres de
    │                      #       fonction séparés, jamais lue depuis Devis (cf. pièges)
    └── word_service.py    # Génération Word — python-docx, même logique que pdf_service.py
                           #   Modèle « moderne » : Calibri, fond vert #14532D en-tête
                           #   Modèle « pro »     : Georgia, anthracite, filets épais
                           #   Logo : PIL pour aspect ratio, max 4×2.5 cm
```

---

## Architecture frontend

```
frontend/src/
├── app/
│   ├── page.tsx         # Chef d'orchestre : états result (Devis|null), documentType,
│   │                    #   withTva, documentDate, modele ("moderne"|"pro")
│   │                    #   userEmail + handleLogout
│   │                    #   activeView: "form"|"historique"|"clients"|"dashboard"
│   │                    #   STATUT_BADGE + STATUT_TRANSITIONS (non exportés — un export
│   │                    #     nommé depuis un fichier page.tsx casse le typing Next.js)
│   │                    #   handleChangeStatut(), handleConvertToFacture(),
│   │                    #   handleDuplicateDocument(), handleCreateAcompte()
│   │                    #   handleOpenFromHistory(detail: DocumentDetail) — un seul objet,
│   │                    #     pas de params positionnels (cf. pièges)
│   │                    #   signatureInfo state → alimente PdfExportButton/WordExportButton
│   │                    #   layout max-w-5xl, palette verte #14532D
│   ├── login/page.tsx     # Login + inscription + écran "vérifiez votre e-mail"
│   ├── auth/confirm/route.ts # Callback confirmation e-mail : verifyOtp → session → redirect /
│   ├── devis/[token]/page.tsx # Page publique de signature (non authentifiée) — lecture,
│   │                    #   accepter/refuser, composant SignaturePad (canvas + Pointer Events)
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
│   │                    #     Bouton « Enregistrer le profil » → PUT /profile
│   │                    #   ③bis « Numérotation » accordéon (Batch 13 T2) — état local
│   │                    #     NumerotationConfig (distinct de form: QuoteRequest), point de
│   │                    #     départ/préfixe/padding/inclure année par type + reset annuel
│   │                    #     partagé ; aperçu en direct via GET /profile/numerotation-status
│   │                    #     + reformatage local (formatNumeroPreview, miroir JS du backend) ;
│   │                    #     sauvegardé par le même bouton/PUT que le reste du profil
│   │                    #   ④ Bloc client (nom client, adresse chantier)
│   │                    #   ⑤ « Mes prix habituels » accordéon
│   │                    #   ⑥ « Remise & acompte » accordéon (+ retenue de garantie %)
│   │                    #   ⑦ « Paramètres du document » accordéon (numéro, validité,
│   │                    #     conditions paiement, afficher_signature, autoliquidation)
│   │                    #   modele reçu en prop + onModeleLoaded callback
│   │                    #   Au montage : getProfile() → pré-rempli ; 404 → bannière migration LS
│   │                    #   localStorage "artisan_profile" = cache/backup (plus source de vérité)
│   │                    #   ⚠️ localStorage dans useEffect uniquement (pas useState)
│   │
│   ├── QuotePreview.tsx # Aperçu éditable inline
│   │                    #   En-tête artisan : nom, SIRET, adresse, CP/ville, tél, email,
│   │                    #                     site_web, IBAN, BIC (champs conditionnels)
│   │                    #   Colonnes : Prestation | Qté | Unité | PU HT | [TVA] | Total HT
│   │                    #   Bascule modèle Moderne ↔ Pro en direct → onUpdate → PDF/Word
│   │                    #   TOTAL TTC / HT éditable : ratio = new/old appliqué à chaque PU HT
│   │                    #   Groupement LOT : headers verts (#E3EDE6/#14532D), sous-totaux
│   │                    #     — nom de lot éditable (EditableText), renameLot() propage
│   │                    #       à toutes les lignes du groupe (pas seulement la ligne cliquée)
│   │                    #   Totaux enrichis : remise / HT net / TVA / TTC / acompte / net
│   │                    #   validite_jours : input inline sous la date (en-tête droit)
│   │                    #   conditions_paiement : input texte bas de page
│   │                    #   mentions_legales : éditables inline (EditableText) + add/remove
│   │                    #                     + bouton "Régénérer" (retour mentions Claude)
│   │                    #   Ajout/suppression lignes : bouton + par lot ou global, poubelle hover
│   │                    #   quantite null = "au réel" : bouton × pour vider, clic pour définir
│   │                    #   afficher_signature : toggle checkbox bas de page (défaut coché)
│   │                    #   Gestion des lots : bouton "+ Nouveau lot" (nom unique auto-incrémenté),
│   │                    #     suppression de lot (lignes → sans lot, jamais supprimées),
│   │                    #     réassignation de ligne via <select> (lotOptions)
│   │                    #   ⚠️ retenue_garantie_taux / autoliquidation NE sont PAS édités ici
│   │                    #     (réglés une fois dans QuoteForm, survivent aux édits via _buildDevis
│   │                    #     qui part de ...devis) — cf. pièges
│   │                    #   onUpdate → propage devis mis à jour à page.tsx (pour PDF/Word)
│   │
│   ├── ImportButton.tsx      # Bouton d'import — lit localStorage artisan_profile, FormData
│   ├── ImportReview.tsx      # Écran de validation post-import (résumé + toggle artisan)
│   ├── PdfExportButton.tsx   # Bouton export PDF — prend un prop signature? (SignatureExportOptions)
│   ├── WordExportButton.tsx  # Bouton export Word (.docx) — idem
│   ├── HistoriqueView.tsx   # Liste des documents — onOpen: (detail: DocumentDetail) => void
│   │                         #   Onglets Devis/Facture (Batch 14) — filtrage client-side de
│   │                         #     GET /documents, aucun paramètre backend
│   │                         #   Badges statut : 6 statuts. Icônes : Dupliquer, Convertir en facture,
│   │                         #     Supprimer (tout statut depuis Batch 14, confirm renforcé si numero)
│   │                         #   Clic → getDocument(id) → onOpen → QuotePreview
│   ├── ClientsView.tsx      # Liste triable (nom/CA/nb documents), fiche client éditable,
│   │                         #   historique cliquable — onOpenDocument même callback que HistoriqueView
│   └── DashboardView.tsx    # KPI (StatTile) + recharts — BarChart CA/mois + PieChart statuts
│                             #   (labels directs sur chaque part, cf. skill dataviz)
│
└── lib/
    ├── api.ts           # generateQuote, importQuote, exportToPdf, exportToWord (avec signature?)
    │                    #   getProfile()/saveProfile() — profil entreprise (+ config numérotation)
    │                    #   getNumerotationStatus() — verrouillage + prochain compteur brut (T2)
    │                    #   saveDocument(), listDocuments(), getDocument(id), updateDocumentStatus()
    │                    #   convertToFacture(id), duplicateDocument(id), createAcompte(id, pct)
    │                    #   listClients(), getClient(id), updateClient(id, upd)
    │                    #   getDashboardStats()
    │                    #   getSignatureLink(id), getPublicDevis(token), acceptPublicDevis(),
    │                    #     refusePublicDevis() — ⚠️ pas de authHeader() sur ces 3 dernières
    │                    #     (routes publiques volontairement non authentifiées)
    │                    #   authHeader() : getSession() → Authorization: Bearer
    ├── supabase-client.ts  # createBrowserClient — composants "use client"
    ├── supabase-server.ts  # createServerClient + cookies SSR — Server Components
    └── types.ts         # Miroir EXACT des modèles Pydantic — toujours synchroniser
                         #   ProfileEntreprise : 11 champs + modele_prefere
                         #   Devis : + modele?, afficher_signature?, type_facture?,
                         #           retenue_garantie_taux?, autoliquidation?
                         #   QuoteRequest : mêmes champs en miroir
                         #   QuoteResponse: + import_meta?: ImportMeta
                         #   StatutDocument : 6 statuts
                         #   DocumentSummary/DocumentDetail : + document_source_id,
                         #     date_envoi/signature/paiement/refus, signature_nom_signataire,
                         #     signature_image_base64 (Detail seul)
                         #   ClientSummary, ClientDetail, ClientUpdate
                         #   DashboardStats, CaMoisPoint, TopPrestation
                         #   PublicArtisanInfo, PublicClientInfo, PublicDevisView,
                         #     SignatureLinkResponse
```

---

## Flux de données complet

```
[QuoteForm]
  ↓ QuoteRequest (description + artisan_* + numero_document + remise + acompte + modele + ...)
[Backend /quotes/generate]
  ↓ Prompt Claude (description + région + prix artisan) — SANS infos sensibles
[Claude API — Tool Use]
  ↓ JSON brut (lignes, totaux, mentions)
[claude_service.py — injection post-Claude]
  ↓ Devis complet (+ adresse, logo, iban, bic, numero_document, remise, acompte, modele, ...)
[QuotePreview] ← résultat affiché, éditable inline
  ↓ bascule modèle Moderne/Pro → onUpdate → page.tsx setResult
[PDF/Word export] ← envoie le Devis complet (avec devis.modele) au backend
```

---

## Décisions techniques & pièges connus

| Sujet | Décision / Piège |
|---|---|
| **fpdf2 + cp1252** | Helvetica/Times ne supportent que cp1252. La fonction `_safe()` strip les caractères hors-cp1252. `€` (0x80), `é` (0xE9), `°` (0xB0) sont valides. Pas d'espace fine U+202F. |
| **Logo PDF** | Base64 pur stocké dans `ArtisanInfo.logo_base64`. PIL (`PIL.Image.open`) pour lire les dimensions et calculer l'aspect ratio. Dimensions bornées à 38×28 mm. `text_x = 125 - text_w`, dynamique selon la largeur réelle du logo. |
| **Logo Word** | `_logo_dimensions_cm()` avec PIL, borné à 4×2.5 cm. `add_picture(width=Cm(w), height=Cm(h))` pour forcer les deux dimensions sans déformation. |
| **Logo frontend** | Data URL complet (`data:image/…;base64,…`) dans le state React. Conversion base64 pur dans `doGenerate()`. |
| **modele** | Injecté post-génération dans `claude_service.py` exactement comme `remise_type`, jamais envoyé à Claude. `pdf_service` et `word_service` lisent `devis.modele` pour choisir la palette/police. |
| **afficher_signature** | `bool = True` par défaut sur `Devis` et `QuoteRequest`, même pattern d'injection post-génération que `modele` (inconditionnelle, jamais envoyée à Claude). Contrôle l'encadré "Bon pour accord"/"Signature client" **et** la mention légale associée (les deux sont liés : pas de mention sans encadré). `pdf_service.py` retire 34 mm du calcul `footer_h` quand masqué — ne pas oublier ce terme si la zone de signature est un jour redimensionnée. |
| **Infos artisan → Claude (génération)** | Adresse artisan, logo, IBAN, BIC, assurance, numero_document, remise, acompte, retenue_garantie_taux, autoliquidation, modele ne passent **jamais** dans le prompt Claude de génération. Injection dans `claude_service.py` après génération. `QuoteRequest.client_code_postal`/`client_ville` existent dans `quote.py` mais ne sont lus nulle part ni remplis par aucun formulaire — champ mort, à nettoyer ou réactiver un jour. `client_email` suit bien le pattern injection post-génération inconditionnelle, comme IBAN/BIC/assurance. |
| **IBAN/BIC à l'import** | La règle "infos sensibles jamais par Claude" s'applique à la **génération** uniquement. Pour l'**import**, l'IBAN et le BIC figurent déjà dans le document uploadé et sont renvoyés à son propre frontend → extraction normale dans `import_meta.emetteur`. `_inject_artisan` (qui ne les envoie pas à Claude) continue de s'appliquer sur `devis.artisan` côté génération — les deux règles coexistent sans conflit. |
| **import_meta** | Champ `Optional[dict]` dans `QuoteResponse`. **Uniquement renseigné par `import_service.py`**, jamais par `claude_service.py`. Contient : `document_type`, `numero_document_original`, `date_document_original`, `emetteur`, `conditions_paiement`, `acompte`. Le frontend lit ces valeurs dans `handleImported`. |
| **localStorage + SSR** | `useState` lazy initializer ne doit **pas** accéder à `localStorage` → erreur d'hydratation Next.js. Utiliser `useEffect(() => { … }, [])`. |
| **PDF Chrome** | Fix : `application/octet-stream` dans `api.ts`. |
| **Pagination PDF** | `auto_page_break=False` pendant le tableau. Stratégie : calculer `lot_total_h` (bandeau + lignes + sous-total) AVANT de dessiner. Si ça tient sur la page courante → dessin direct. Si ça tient sur une page fraîche → `add_page()` + header. Si lot > page entière (`big_lot`) → sauts par ligne avec `sub_margin` pour coller la dernière ligne au sous-total. Footer (mentions + RIB + signature) : estimation de hauteur globale, `add_page()` si insuffisant. |
| **validite_jours** | `Optional[int] = None` dans Pydantic + TypeScript. Vide → aucune mention de validité dans PDF/Word. |
| **CORS** | `allowed_origin` dans `Settings` (défaut `http://localhost:3000`). Override via `ALLOWED_ORIGIN` env var. Wildcard `*` uniquement si la valeur est `"*"`. |
| **Rate limiting** | In-memory dict par IP dans `quotes.py`. 10 requêtes / 60 s. Nettoyage de la fenêtre glissante à chaque appel. Pas de dépendance externe. |
| **Groupement LOT** | `lot: Optional[str]` sur `LigneDevis`. Order-preserving (dict Python / Map JS). Rétrocompatible : `lot=None` → rendu comme avant. |
| **Remise TVA** | Remise sur HT brut. TVA recalculée : `ratio = total_ht_net / total_ht`, `tva_par_ligne *= ratio`. |
| **TTC éditable** | `ratio = new_ttc / old_ttc` appliqué à chaque `prix_unitaire_ht`. `computeTotaux` recalcule tout. La remise fixe n'est pas rescalée (comportement voulu). |
| **Colonne Unité** | Séparée de Qté depuis la refonte. PDF with_tva : [34,54,12,13,22,14,31]. Word with_tva : [2.8,5.5,1.0,1.2,2.1,1.5,2.9] cm. |
| **Supabase service_role + user_id** | Client service_role dans `supabase_client.py` bypass toute la RLS. En contrepartie, CHAQUE requête SQL DOIT appliquer `.eq("user_id", current_user.user_id)` manuellement. Ne jamais oublier ce filtre dans un nouveau routeur. |
| **ProfileEntreprise ≠ ArtisanInfo** | `ProfileEntreprise` (`models/profile.py`) est distinct d'`ArtisanInfo` (`quote.py`) pour ne pas modifier `quote.py`. Le frontend mappe l'un vers l'autre dans `QuoteForm.tsx`. |
| **Source de vérité profil** | Backend Supabase = source de vérité. `localStorage["artisan_profile"]` = cache/backup uniquement, utilisé sur erreur réseau/auth. |
| **Numérotation atomique via RPC Postgres** | `get_next_numero(user_id, type)` fait un seul `UPDATE ... SET compteur = CASE WHEN annee != annee_courante THEN 1 ELSE compteur+1 END RETURNING`. Verrou de ligne PostgreSQL = pas de race condition. Jamais d'incrément côté Python. Le numéro est attribué uniquement à la transition brouillon→envoyé. |
| **`devis_payload` JSONB + colonnes indexées** | Le `Devis` complet est stocké en JSONB dans `documents.devis_payload`. Les colonnes `type_doc`, `numero`, `total_ttc`, `statut`, `date_document`, `client_id` sont des colonnes séparées pour la liste (évite de parser le JSONB). |
| **Statuts document** | `brouillon` (défaut) → `envoyé` (assigne numéro définitif via RPC) → `signé` → `payé`. La transition brouillon→envoyé est la seule qui déclenche la numérotation. |
| **Contrainte `documents_statut_check`** | Le CHECK doit lister les valeurs avec accent : `CHECK (statut IN ('brouillon', 'envoyé', 'signé', 'payé', 'refusé', 'expiré'))`. Sans accent → PATCH renvoie 500 (`23514`). |
| **`titre` vs `numero` dans `documents`** | `documents.numero` = numéro séquentiel légal (`DEV-2026-009`). `documents.titre` = nom du fichier PDF/Word (`Devis_DEVIS-001_Martin`). `documents.numero_document` = référence saisie dans le formulaire ou générée par l'IA (`DEVIS-001`). L'historique affiche `titre` + `numero_document`, pas `numero`. |
| **Texte invisible PDF — bug récurrent** | `fpdf2` : `set_text_color` est un **état global persistant** qui peut "saigner" (rester blanc) sur les lignes suivantes si non réinitialisé après un bandeau blanc. Couvert par `backend/tests/test_pdf_service.py` (échoue si une règle est cassée) — **s'y référer avant toute modification de `pdf_service.py`** plutôt que de re-détailler les règles ici. Le helper central est `_set_body()`. |
| **Piège champ booléen Pydantic + état React** | Un champ Pydantic `bool = True` combiné à un état React qui pourrait valoir `undefined` est dangereux : `JSON.stringify` **supprime silencieusement** toute clé à `undefined`, et le backend applique alors son défaut — un `False` voulu par l'utilisateur disparaît sans erreur visible. Toujours initialiser l'état React avec `?? <défaut>` (jamais laisser `undefined` possible) pour tout futur champ booléen éditable. |
| **Dates de transition non rattrapables** | `date_envoi`/`date_signature`/`date_paiement`/`date_refus` ne sont renseignées qu'au moment RÉEL de la transition (jamais de backfill). `NULL` = "jamais atteint ce statut" — une donnée en soi. |
| **`document_source_id` — filiation devis→facture** | Colonne `uuid REFERENCES documents(id) ON DELETE SET NULL`. `NULL` pour tout document créé normalement. `ON DELETE SET NULL` (pas `CASCADE`) : la filiation est une métadonnée de traçabilité, pas une dépendance structurelle. |
| **Export nommé depuis `app/page.tsx`** | Next.js 14 (App Router) génère un type strict pour chaque `page.tsx` qui n'autorise que les exports connus. Exporter une constante arbitraire casse `tsc --noEmit`. Fix : ne jamais `export` une constante utilitaire dans un `page.tsx`. |
| **Deux points d'injection pour tout champ `artisan_*`** | `QuoteRequest.artisan_*` est injecté dans `devis.artisan` à **deux** endroits : `claude_service.py` (génération) **et** `import_service.py::_inject_artisan` (import). Un nouveau champ `artisan_xxx` ajouté seulement dans `claude_service.py` fonctionnera en génération mais restera invisible après un import. Toujours dupliquer l'injection dans les deux fichiers. |
| **`allow_methods` CORS à tenir à jour** | `main.py` liste explicitement les verbes HTTP autorisés. Chaque nouveau verbe utilisé par un routeur doit y être ajouté, sinon le navigateur bloque en préflight CORS (`Failed to fetch`, pas de detail HTTP). |
| **Soft delete = jamais de `DELETE` SQL** | `documents.deleted_at timestamptz`, nullable. Toute suppression passe par `UPDATE deleted_at = now()`. Chaque requête qui liste des documents DOIT explicitement filtrer `deleted_at IS NULL` — l'oubli est silencieux. Depuis le Batch 14, `DELETE /documents/{id}` accepte **n'importe quel statut** (plus de restriction brouillon/refusé) — jugé sûr car le numéro légal reste protégé par la contrainte `UNIQUE (user_id, type_doc, numero)` (Batch 13 T2) même sur une ligne "supprimée", et la ligne elle-même n'est jamais physiquement retirée. |
| **Numéro provisoire ≠ numéro légal** | Batch 14 : `numero_document` (champ libre, affiché dans le PDF/Word) est pré-rempli à la génération avec un numéro **prévisionnel** calculé côté frontend (`page.tsx::computeProvisionalNumero`, réutilise `getNumerotationStatus()` + `formatNumeroPreview()` de Batch 13 T2) si vide. `documents.numero` (le numéro légal, séquentiel, gapless) continue à n'être attribué **qu'à l'envoi**, via la RPC atomique — jamais touché par ce mécanisme. Le provisoire peut différer du numéro réellement attribué si d'autres documents sont envoyés entre-temps ; c'est un compromis assumé pour ne jamais réserver de numéro légal sur un brouillon abandonné. Ne jamais faire dépendre un calcul de CA/audit de `numero_document` — seul `documents.numero` fait foi. |
| **Notification email = best-effort, ne bloque jamais l'action principale déjà actée** | `_notifier_artisan_signature()` (`routers/public.py`, Batch 14) envoie le PDF signé à l'artisan APRÈS que le statut soit déjà mis à jour en base — toute erreur (email absent, Resend en échec) est loguée et avalée, jamais renvoyée au client qui vient de signer. Pattern à réutiliser pour toute future notification déclenchée par une action déjà validée : ne jamais faire échouer la réponse HTTP pour un envoi secondaire. (Différent de `POST /documents/{id}/send`, où l'email EST l'action principale et DOIT bloquer si Resend échoue — cf. piège dédié plus haut.) |
| **`with_tva` non persisté** | Le toggle "Avec/Sans TVA" n'est jamais stocké en base — paramètre d'affichage passé à chaque export. `POST /documents/{id}/send` le déduit par heuristique : `devis.totaux.total_tva > 0`. Fiable en pratique, imparfait en théorie. Si ça devient un problème, ajouter une colonne `with_tva` dédiée. |
| **Ordre des opérations dans `/documents/{id}/send`** | L'email est envoyé **avant** toute écriture en base. Si Resend échoue, rien n'est écrit, aucun numéro gaspillé. L'archivage Storage est **après** et **best-effort** (erreur juste loguée). Ne jamais inverser cet ordre. |
| **RPC de mutation appelée depuis un GitHub Action → `service_role`, jamais `anon`** | Un workflow qui ne fait que LIRE → clé anon suffit (`supabase-keepalive.yml`). Un workflow qui ÉCRIT/MODIFIE → secret service_role dédié, toujours jamais anon (`expire-devis.yml`), même si la fonction Postgres est `SECURITY DEFINER` (bypass la RLS mais ne remplace pas un contrôle d'accès sur qui peut l'appeler — mécanismes complémentaires, pas interchangeables). Erreur commise puis corrigée en Batch 12 T1 : ne pas la répéter. |
| **Route publique non authentifiée → routeur dédié, modèle Pydantic dédié** | Toute future route publique (sans `Depends(get_current_user)`) doit vivre dans un fichier **séparé** des routeurs authentifiés (pattern `routers/public.py`) — rend l'absence d'auth visuellement évidente. Ne **jamais** renvoyer un modèle interne (`Devis`, `devis_payload` brut) sur une route publique — construire un modèle Pydantic dédié en **liste blanche explicite** (`PublicArtisanInfo`, etc.), jamais une liste d'exclusion sur le modèle complet. |
| **Nouvelle route publique → penser à `middleware.ts`** | `middleware.ts` protège par défaut **toutes** les routes sauf celles explicitement exemptées (`/login`, `/auth/*`, `/devis/*`). Toute future page publique doit être ajoutée à `isPublicPath`, sinon redirection silencieuse vers `/login`. |
| **`extra = "ignore"` sur `Settings`** | `.env` est partagé entre plusieurs consommateurs (backend, workflows, parfois frontend). Sans `extra = "ignore"` dans `Settings.Config`, toute variable ajoutée pour UN SEUL consommateur fait planter **tout démarrage du backend**. Un champ *requis* toujours absent lève toujours une erreur claire — seules les variables *en trop* sont ignorées. |
| **Signature image = métadonnée document, jamais champ `Devis`** | `signature_image_base64`/`signature_nom_signataire` vivent sur `documents`, pas sur `Devis`. `generate_quote_pdf()`/`generate_quote_docx()` les reçoivent en paramètres de fonction séparés, jamais en les lisant depuis l'objet `Devis`. Toute nouvelle donnée liée à la signature doit suivre le même chemin : colonne `documents` → paramètre de fonction PDF/Word, jamais `quote.py`. |
| **Limite taille image signature (2,8 Mo)** | `routers/public.py::accept_devis` refuse (HTTP 400) toute image décodée dépassant 2,8 Mo. Pas de compression côté serveur ni client — si la limite s'avère trop stricte, ajouter une compression côté client plutôt que remonter la limite brute. |
| **`handleOpenFromHistory(detail: DocumentDetail)`** | Remplace l'ancienne signature à 4 paramètres positionnels par un seul objet `DocumentDetail`. Tout nouveau champ ajouté à `DocumentDetail` devient automatiquement disponible partout où ce callback est utilisé — préférer étendre `DocumentDetail` plutôt que réintroduire des paramètres positionnels séparés. |
| **`uvicorn --reload` peut se figer silencieusement** | Après de nombreux cycles d'édition dans une session longue, `WatchFiles` peut cesser de détecter les changements `.py` sans erreur visible — le process répond `200` sur `/health` mais sert du code obsolète. **Vérification rapide** : `GET /openapi.json`, chercher le nouveau chemin/champ — absent = pas rechargé. Fix : tuer le process et relancer à froid. Toujours vérifier ce point avant de chercher un bug applicatif dans un changement "sans effet". |
| **Signature image / type_facture / retenue_garantie_taux / autoliquidation → jamais éditables dans `QuotePreview`** | Contrairement à `acompte` (édition live + recalcul des totaux), ces champs se règlent une fois (formulaire ou action dédiée) et ne sont plus retouchés dans l'aperçu — ils survivent aux éditions car `_buildDevis()` part de `...devis`. Cohérent avec le traitement des champs assurance (Batch 11 T1). |
| **`documents.total_ttc` peut diverger de `devis_payload.totaux.total_ttc`** | Cas de la facture de solde (T4-2) : `documents.total_ttc` (utilisé par le dashboard pour le CA) = reste à payer, alors que `devis_payload.totaux.total_ttc` reste le total légal complet affiché dans le PDF — sinon le montant de l'acompte serait compté deux fois dans le CA. Seule divergence intentionnelle connue entre ces deux valeurs à ce jour. |
| **Mentions TVA (293 B / taux réduit / autoliquidation) sont mutuellement exclusives** | Calculées à l'affichage dans `pdf_service.py`/`word_service.py` à partir de `with_tva`, `devis.autoliquidation` et `devis.lignes[].tva_taux` — jamais stockées, jamais éditables. `autoliquidation=True` supprime automatiquement les deux autres. Ne jamais les faire cohabiter : ce sont des régimes fiscaux différents. |
| **Composant qui reste monté entre deux documents différents → états locaux figés** | `QuotePreview.tsx` a ~12 `useState(devis.xxx)` initialisés une seule fois au montage. Si le composant ne démonte jamais entre deux documents (ex. `handleOpenFromHistory` appelé alors que `QuotePreview` est déjà affiché — c'est le cas pour "Convertir en facture"/"Facture d'acompte"/"Dupliquer"), ces champs restent figés sur l'ANCIEN document. Fix retenu (Batch 16) : `key={documentInstanceKey}` sur `<QuotePreview>` dans `page.tsx`, ce compteur étant incrémenté à chaque nouveau document affiché — force un remount complet plutôt que d'ajouter un `useEffect` de resync par champ. Tout futur état local ajouté à `QuotePreview` bénéficie automatiquement de cette protection ; ne pas la contourner en donnant un jour un `key` fixe ou en supprimant l'incrément dans un des 3 points d'entrée (génération, import, `handleOpenFromHistory`). |
| **Transitions de statut validées côté serveur (`_TRANSITIONS_AUTORISEES`)** | `routers/documents.py::_statut_transition_update()` refuse (409) toute transition hors du graphe `brouillon→envoyé→{signé,refusé,expiré}→payé` (miroir exact de `STATUT_TRANSITIONS` dans `page.tsx`). `envoyé→envoyé` reste autorisé (ré-envoi d'email via `/send`). Avant Batch 16, un appel API direct pouvait sauter des statuts sans jamais attribuer de numéro légal, ou marquer "signé" sans preuve de signature. Tout nouveau statut ou toute nouvelle transition doit être ajoutée aux DEUX endroits (le graphe Python ET `STATUT_TRANSITIONS` côté frontend), sinon l'un des deux bloque ce que l'autre autorise. |
| **`PUT /documents/{id}` — édition de contenu restreinte au brouillon** | Persiste les modifications faites dans `QuotePreview` après la génération initiale (Batch 16 — avant ça, aucune édition post-génération n'était jamais sauvegardée). Refuse (409) toute modification si `statut != "brouillon"` : au-delà, le client a potentiellement déjà vu/signé une version précise du document, son contenu ne doit plus bouger silencieusement. Frontend : `doUpdateSave()` débattue à 900 ms, déclenchée uniquement si `savedDocumentId` existe et `savedDocumentStatut === "brouillon"` ; toute sauvegarde en attente est annulée avant une transition de statut (`handleChangeStatut`) pour éviter un 409 parasite juste après un envoi réussi. Batch 18 : la modification en attente est aussi gardée dans `pendingUpdateRef` (pas seulement la closure du timer), pour pouvoir être envoyée immédiatement via `flushUpdateSave()` — appelé avant toute navigation qui quitte l'aperçu (Historique/Clients/Dashboard, retour accueil), sinon le `PUT` pouvait ne pas être encore parti quand l'utilisateur rouvrait aussitôt le même document. |
| **Un `Settings` requis (sans défaut) lu au niveau module casse l'import en CI, pas seulement au runtime** | `claude_service.py` instancie `anthropic.Anthropic(api_key=settings.anthropic_api_key)` en haut du fichier (pas dans une fonction) — importer ce module force donc `get_settings()` à s'exécuter immédiatement. En local un `.env` fournit les champs requis (`anthropic_api_key`, `supabase_service_role_key`), mais GitHub Actions n'a ni `.env` ni ces secrets configurés pour les tests : `pytest` plantait dès qu'un test importait (même indirectement) `claude_service.py` (Batch 18, révélé par `test_injection_post_generation.py`, premier test à le faire). Fix : valeurs factices dans le `env:` du step `pytest` de `ci.yml` (jamais utilisées pour un vrai appel réseau). Piège généralisable : toute lecture de `Settings` au niveau module (plutôt que lazy, dans une fonction) rend ce module impossible à importer sans configurer TOUS ses champs requis — préférer le pattern lazy (`email_service.py::get_settings()` appelé à l'intérieur de la fonction) sauf besoin explicite d'un singleton au chargement. |
| **Pause Supabase (plan gratuit)** | Un projet Supabase gratuit se met en pause après ~1 semaine d'inactivité. **Symptôme : `ERR_NAME_NOT_RESOLVED`** sur `*.supabase.co` (pas une erreur HTTP — facile à confondre avec un problème réseau local). Mitigé par `.github/workflows/supabase-keepalive.yml` (ping tous les 3 jours). |
| **Numérotation : formatage/atomicité toujours en SQL, jamais en Python** | `get_next_numero` (Postgres) reste la SEULE source de vérité pour un numéro légal — formatage (préfixe/année/padding) et incrément dans la même fonction, même `UPDATE...RETURNING`. `numero_service.py::format_numero()`/`compute_next_compteur()` sont des fonctions Python **pures qui dupliquent volontairement cette logique**, mais UNIQUEMENT pour `preview_next_compteur()` (aperçu UI en lecture seule, jamais d'écriture) — un écart entre les deux ne peut jamais produire un doublon de numéro, juste un aperçu temporairement imprécis. Si la règle de reset ou le format changent un jour, mettre à jour les DEUX (SQL et Python) — ce n'est pas automatique. |
| **401 généralisé en production ≠ problème de connexion utilisateur** | `auth.py` renvoie **403 si le header est absent, 401 si le token est invalide/expiré**. Un 401 signifie donc que le frontend envoie bien un token mais que le backend le refuse. Cause déjà rencontrée : `SUPABASE_URL` absente sur Render → `supabase_jwks_url` (dérivée) ne pointe nulle part → aucune signature vérifiable. Le service démarre normalement et répond `200` sur `/health`, seule l'authentification échoue — d'où la confusion avec un bug applicatif. Toujours vérifier les variables Render avant de chercher plus loin. |
| **Déploiements Preview Vercel → erreurs CORS attendues** | Les déploiements de branche ont une URL différente à chaque commit, jamais couverte par l'`ALLOWED_ORIGIN` de Render (qui pointe sur l'URL de production). Un Preview refusera donc les appels API : c'est **le comportement normal**, pas un bug à corriger. Le développement se fait en local, seule la production compte. Si un jour les Previews doivent réellement fonctionner, il faudra une regex d'origine côté backend plutôt qu'une valeur fixe — ne pas ouvrir le CORS en wildcard pour contourner le symptôme. |
| **`devis_numero_debut`/`facture_numero_debut` verrouillés après le premier numéro attribué** | `PUT /profile` (`routers/profile.py::_numero_debut_locked`) vérifie côté backend — pas seulement dans le formulaire — si un document de ce type a déjà un `numero` non `NULL` avant d'accepter un changement de point de départ (409 sinon). Les 3 autres champs par type (préfixe, année, padding) restent librement modifiables. Le reset annuel (`numero_reset_annuel`, partagé devis/facture) n'est jamais verrouillé, seul le point de départ l'est. |
| **Jamais `detail=str(exc)` sur un `except Exception` générique** | Règle ajoutée au Batch 17 après un passage sur 27 occurrences : un message d'exception brut peut exposer des détails d'implémentation interne (schéma Supabase, requête SQL) au client — particulièrement sensible sur les routes **publiques** (`routers/public.py`). Pattern à suivre systématiquement : `logger.error("...: %s", exc, exc_info=True)` puis `raise HTTPException(..., detail="Erreur interne du serveur.")` (message générique fixe). Exception documentée : `email_service.py` relaie volontairement le message d'erreur de Resend (service externe, utile à l'artisan pour comprendre un échec d'envoi — pas une fuite d'implémentation interne). |
| **IP réelle du visiteur derrière un proxy (Render)** | `req.client.host` reflète l'IP interne du proxy pour toutes les requêtes en production — jamais l'IP du visiteur. Toute logique par-IP (rate limiting, logs, géolocalisation future) doit lire `X-Forwarded-For` en premier (`routers/quotes.py::_get_client_ip`), avec repli sur `req.client.host` seulement si l'en-tête est absent (utile en local/tests). Ne faire confiance à cet en-tête que parce qu'on est nous-mêmes derrière un proxy connu — jamais pour un contrôle de sécurité critique. |
| **`max_tokens` élevé ⇒ appel Claude obligatoirement en streaming** | Le SDK Anthropic refuse une requête non-streamée dont le `max_tokens` est estimé dépasser ~10 min (la connexion HTTP resterait ouverte trop longtemps sans rien recevoir). `claude_service.py::generate_quote()` et `import_service.py::_extract_from_pdf/_extract_from_docx` passent tous les trois par `client.messages.stream(...)` + `stream.get_final_message()` (même objet `Message` en retour qu'un `.create()` non-streamé, donc le reste du code — `response.stop_reason`, `.usage`, `.content` — ne change pas). Tout nouvel appel Claude avec un `max_tokens` généreux doit suivre le même pattern dès le départ plutôt que de découvrir l'erreur en production. |
| **Extraire une fonction juste pour la rendre testable est justifié ici** | `claude_service.py::_inject_post_generation()` et `import_service.py::_inject_artisan()` sont volontairement deux fonctions **pures** séparées (mutent et retournent/modifient un `Devis` à partir d'un `QuoteRequest`), plutôt que du code inline dans `generate_quote()`/`import_quote()` — ça permet de les tester sans jamais appeler l'API Anthropic. `tests/test_injection_post_generation.py` inclut un test de **parité automatisée** entre les deux : si un futur champ `artisan_*` est ajouté à l'une sans l'autre, le test échoue au lieu de compter sur une relecture manuelle du piège documenté plus haut ("Deux points d'injection..."). |

---

## Règles de développement

- **Une modification à la fois** — valider avant de continuer
- **Ne jamais modifier `quote.py`** sans cartographier l'impact sur `claude_service`, `pdf_service`, `word_service`, `lib/types.ts` et présenter le plan d'abord
- **Prompts Claude dans `prompts.py` uniquement** — jamais inline dans les services
- **`lib/types.ts` toujours synchronisé** avec les modèles Pydantic
- **UX mobile-first** — l'artisan utilise son téléphone sur le chantier
- **Les infos sensibles ne passent jamais par Claude** — injectées dans `claude_service.py` après génération. Le champ `modele` suit la même règle.
- **Nouvelles dépendances Python** → ajouter dans `requirements.txt` ET installer dans le venv
- **Variables d'env en production** → ne jamais les coder en dur ; les définir dans le dashboard Render (backend) ou Vercel (frontend). **Toute nouvelle variable doit être ajoutée à la section « Déploiement » de ce fichier dans le même batch que le code qui la lit** — une feature n'est pas terminée tant que ce n'est pas fait.
- **`SUPABASE_SERVICE_ROLE_KEY`** → jamais côté frontend, jamais dans git (appels admin Supabase depuis le backend)
- **`RESEND_API_KEY`** → jamais côté frontend, jamais dans git (`backend/.env` en local, dashboard Render en production). Sans elle, `POST /documents/{id}/send` répond une erreur claire plutôt que de planter au démarrage.
- **`NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`** (`sb_publishable_*`) → sûre côté frontend, protégée par RLS
- **`get_current_user`** → dépendance FastAPI dans tous les routers qui touchent les données utilisateur. Ne jamais bypasser. `/health` seul endpoint public authentifié-exempté côté API (les routes `routers/public.py` sont, elles, publiques par design).
