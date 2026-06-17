# BTP SaaS — Générateur de devis IA

## Stack
- **Frontend** : Next.js 14 + Tailwind CSS + shadcn/ui
- **Backend** : FastAPI (Python)
- **IA** : Anthropic Claude Sonnet (claude-sonnet-4-6)

## Variables d'environnement (backend/.env)

| Variable | Requis | Défaut | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ | — | Clé API Anthropic |
| `CLAUDE_MODEL` | Non | `claude-sonnet-4-6` | Modèle Claude à utiliser |
| `ALLOWED_ORIGIN` | Non | `http://localhost:3000` | Domaine autorisé en CORS (mettre l'URL du frontend en prod) |
| `DEBUG` | Non | `false` | Mode debug FastAPI |

## Lancer le projet en local

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Étapes Roadmap
- ✅ Étape 1 : MVP complet (texte → devis JSON → PDF + Word, 2 modèles, pagination, sécurité)
- ⬜ Étape 2 : PostgreSQL + Auth + Stripe
- ⬜ Étape 3 : Voix + Vision IA
