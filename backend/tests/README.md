# Tests de non-régression PDF/Word

Vérifient automatiquement les 3 règles anti-"texte invisible" documentées dans
`CLAUDE.md` (bug récurrent de `fpdf2`), ainsi que les règles métier (quantité
"au réel", mention art. 293 B sans TVA, encadré signature masquable).

## Lancer les tests (Windows)

Depuis la racine du projet :

```bash
cd backend
venv\Scripts\activate
pip install -r requirements.txt
pytest
```

Pour un test précis :

```bash
pytest tests/test_pdf_service.py -k big_lot -v
```

## Pourquoi ces tests existent

Le bug "texte invisible" (des lignes de prestation dessinées en blanc sur
fond blanc après un bandeau coloré) est réapparu 3 fois au fil du projet
(Batch 4, Batch 5, règle B du Batch 10) car les 3 règles qui l'empêchent
n'étaient documentées qu'en commentaire — rien ne les faisait respecter
automatiquement. Ces tests extraient le texte réel du PDF généré (`pypdf`)
et vérifient que chaque ligne attendue y figure bien. Si une future
modification de `pdf_service.py` recasse une des 3 règles, un test échoue
au lieu de laisser passer un document cassé jusqu'en production.
