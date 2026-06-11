# BTP SaaS — Générateur de devis IA

## Stack
- **Frontend** : Next.js 14 + Tailwind CSS + shadcn/ui
- **Backend** : FastAPI (Python)
- **IA** : Anthropic Claude Sonnet (claude-sonnet-4-20250514)

## Lancer le projet en local

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows : venv\Scripts\activate
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
- ✅ Étape 1 : MVP (texte → devis JSON → PDF)
- ⬜ Étape 2 : PostgreSQL + Auth + Stripe
- ⬜ Étape 3 : Voix + Vision IA
