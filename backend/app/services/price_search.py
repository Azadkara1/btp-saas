"""
Service de recherche des prix du marché BTP.
Étape 1 : base de données de prix de référence + matching intelligent par mots.
Étape 2+ : pourra être remplacé par une API de prix dédiée (ex: Batiprix).
"""
import re
from typing import Optional
from app.core.config import get_settings

settings = get_settings()

# Mots vides français ignorés lors du matching
STOP_WORDS = {
    "de", "du", "la", "le", "les", "des", "un", "une", "et",
    "à", "au", "par", "en", "sur", "pour", "avec", "dans"
}

# ── Base de prix de référence BTP France 2026 ───────────────────
# Fourchettes moyennes nationales — clés en minuscules, séparées par espaces
PRIX_REFERENCE = {
    # Terrassement / Gros œuvre
    "maçonnerie":                     {"prix": 45.0,   "unite": "m²",      "fourchette": "35-60"},
    "béton":                          {"prix": 95.0,   "unite": "m³",      "fourchette": "80-120"},
    "dalle béton":                    {"prix": 85.0,   "unite": "m²",      "fourchette": "65-110"},
    "terrassement":                   {"prix": 12.0,   "unite": "m³",      "fourchette": "8-20"},
    "fondations":                     {"prix": 280.0,  "unite": "ml",      "fourchette": "200-380"},
    "parpaings élévation murs":       {"prix": 75.0,   "unite": "m²",      "fourchette": "55-95"},
    "enduit extérieur façade":        {"prix": 42.0,   "unite": "m²",      "fourchette": "30-60"},
    "charpente":                      {"prix": 80.0,   "unite": "m²",      "fourchette": "60-110"},
    "reprise sous-oeuvre":            {"prix": 450.0,  "unite": "ml",      "fourchette": "300-700"},

    # Couverture / Toiture
    "toiture tuiles":                 {"prix": 120.0,  "unite": "m²",      "fourchette": "90-160"},
    "toiture ardoises":               {"prix": 145.0,  "unite": "m²",      "fourchette": "110-200"},
    "zinguerie":                      {"prix": 55.0,   "unite": "ml",      "fourchette": "40-80"},
    "fenêtre toit velux":             {"prix": 900.0,  "unite": "unité",   "fourchette": "600-1400"},
    "isolation combles":              {"prix": 30.0,   "unite": "m²",      "fourchette": "20-45"},

    # Carrelage — entrées distinctes
    "dépose carrelage":               {"prix": 15.0,   "unite": "m²",      "fourchette": "10-22"},
    "pose carrelage":                 {"prix": 35.0,   "unite": "m²",      "fourchette": "25-50"},
    "fourniture carrelage":           {"prix": 30.0,   "unite": "m²",      "fourchette": "15-60"},
    "carrelage fourniture pose":      {"prix": 65.0,   "unite": "m²",      "fourchette": "50-90"},
    "faïence murale":                 {"prix": 55.0,   "unite": "m²",      "fourchette": "40-80"},
    "ragréage sol":                   {"prix": 18.0,   "unite": "m²",      "fourchette": "12-28"},

    # Peinture
    "peinture intérieure":            {"prix": 18.0,   "unite": "m²",      "fourchette": "12-25"},
    "peinture façade":                {"prix": 25.0,   "unite": "m²",      "fourchette": "18-35"},
    "enduit décoratif":               {"prix": 32.0,   "unite": "m²",      "fourchette": "22-50"},
    "papier peint pose":              {"prix": 22.0,   "unite": "m²",      "fourchette": "15-35"},

    # Plâtrerie / Cloisons / Isolation
    "enduit plâtre":                  {"prix": 22.0,   "unite": "m²",      "fourchette": "15-30"},
    "placo cloison":                  {"prix": 28.0,   "unite": "m²",      "fourchette": "20-38"},
    "faux plafond":                   {"prix": 35.0,   "unite": "m²",      "fourchette": "25-50"},
    "isolation thermique":            {"prix": 25.0,   "unite": "m²",      "fourchette": "18-40"},
    "isolation phonique":             {"prix": 30.0,   "unite": "m²",      "fourchette": "22-45"},
    "ite isolation extérieure":       {"prix": 120.0,  "unite": "m²",      "fourchette": "90-160"},
    "doublage intérieur":             {"prix": 35.0,   "unite": "m²",      "fourchette": "25-50"},

    # Électricité
    "prise électrique":               {"prix": 45.0,   "unite": "unité",   "fourchette": "35-65"},
    "interrupteur":                   {"prix": 35.0,   "unite": "unité",   "fourchette": "25-55"},
    "point lumineux":                 {"prix": 85.0,   "unite": "point",   "fourchette": "60-120"},
    "tableau électrique":             {"prix": 900.0,  "unite": "forfait", "fourchette": "600-1400"},
    "passage câbles":                 {"prix": 22.0,   "unite": "ml",      "fourchette": "15-35"},
    "borne recharge véhicule":        {"prix": 1200.0, "unite": "forfait", "fourchette": "800-1800"},
    "éclairage led":                  {"prix": 65.0,   "unite": "point",   "fourchette": "45-90"},

    # Plomberie
    "plomberie evacuation":           {"prix": 55.0,   "unite": "ml",      "fourchette": "40-75"},
    "robinetterie":                   {"prix": 120.0,  "unite": "point",   "fourchette": "80-200"},
    "wc suspendu":                    {"prix": 550.0,  "unite": "unité",   "fourchette": "350-800"},
    "baignoire":                      {"prix": 700.0,  "unite": "unité",   "fourchette": "450-1100"},
    "douche italienne":               {"prix": 900.0,  "unite": "unité",   "fourchette": "600-1400"},
    "chaudière gaz":                  {"prix": 2800.0, "unite": "forfait", "fourchette": "2000-4000"},
    "pompe à chaleur":                {"prix": 8500.0, "unite": "forfait", "fourchette": "6000-12000"},
    "vmc double flux":                {"prix": 3200.0, "unite": "forfait", "fourchette": "2400-4500"},
    "remplacement robinetterie":      {"prix": 150.0,  "unite": "point",   "fourchette": "100-250"},

    # Menuiserie
    "fenêtre pvc":                    {"prix": 650.0,  "unite": "unité",   "fourchette": "450-900"},
    "porte intérieure":               {"prix": 350.0,  "unite": "unité",   "fourchette": "200-600"},
    "porte entrée":                   {"prix": 1200.0, "unite": "unité",   "fourchette": "800-2000"},
    "volet roulant":                  {"prix": 500.0,  "unite": "unité",   "fourchette": "350-800"},
    "cuisine équipée":                {"prix": 5500.0, "unite": "forfait", "fourchette": "3500-9000"},

    # Revêtements sols
    "parquet pose":                   {"prix": 30.0,   "unite": "m²",      "fourchette": "20-45"},
    "parquet fourniture pose":        {"prix": 65.0,   "unite": "m²",      "fourchette": "45-100"},
    "stratifié pose":                 {"prix": 22.0,   "unite": "m²",      "fourchette": "15-35"},
    "moquette":                       {"prix": 18.0,   "unite": "m²",      "fourchette": "12-28"},

    # Démolition
    "démolition cloison":             {"prix": 35.0,   "unite": "m²",      "fourchette": "25-55"},
    "dépose revêtement":              {"prix": 12.0,   "unite": "m²",      "fourchette": "8-20"},
    "évacuation gravats":             {"prix": 80.0,   "unite": "m³",      "fourchette": "60-120"},

    # Main d'œuvre générique (dernier recours)
    "main d'oeuvre":                  {"prix": 45.0,   "unite": "heure",   "fourchette": "35-60"},
}

# Coefficient régional approximatif
COEFF_REGION = {
    "Île-de-France": 1.20,
    "PACA":          1.10,
    "Rhône-Alpes":   1.05,
    "Bretagne":      0.95,
    "Normandie":     0.95,
    "Occitanie":     0.98,
    "default":       1.00
}


def _tokenize(text: str) -> set:
    """Extrait les mots significatifs d'un texte (ignore ponctuation et accents composés)."""
    return set(re.findall(r"[a-zàâäéèêëîïôöùûüç]+", text.lower()))


def _word_matches(kw: str, item_words: set) -> bool:
    """
    Vérifie si un mot-clé correspond à l'un des mots de l'item.
    Tolère les variations de genre/nombre (ex: prise → prises, électrique → électriques)
    en comparant les 5 premiers caractères.
    """
    if kw in item_words:
        return True
    if len(kw) >= 5:
        return any(iw.startswith(kw[:5]) or kw.startswith(iw[:5]) for iw in item_words)
    return False


async def search_market_price(
    item: str,
    region: str = "Île-de-France",
    unite: Optional[str] = None
) -> dict:
    """
    Retourne le prix du marché pour une prestation BTP.
    Matching intelligent : tous les mots-clés doivent correspondre (pas de faux positifs).
    """
    item_lower = item.lower().strip()
    item_words = _tokenize(item_lower) - STOP_WORDS
    coeff = COEFF_REGION.get(region, COEFF_REGION["default"])

    best_key = None
    best_score = 0

    for key, data in PRIX_REFERENCE.items():
        key_words = _tokenize(key) - STOP_WORDS
        if not key_words:
            continue

        # Tous les mots de la clé doivent avoir au moins un équivalent dans l'item
        matched = [kw for kw in key_words if _word_matches(kw, item_words)]
        if len(matched) < len(key_words):
            continue  # au moins un mot-clé manque → pas de correspondance

        # Score = nombre de mots matchés (favorise les clés plus spécifiques)
        score = len(matched)
        if score > best_score:
            best_score = score
            best_key = key

    if best_key:
        data = PRIX_REFERENCE[best_key]
        prix_ajuste = round(data["prix"] * coeff, 2)
        return {
            "item": item,
            "prix_unitaire_ht": prix_ajuste,
            "unite": unite or data["unite"],
            "fourchette": data["fourchette"],
            "region": region,
            "source": "base_reference_btp_2026",
            "note": f"Prix moyen {region}, fourchette : {data['fourchette']} €/{data['unite']}"
        }

    # Aucune correspondance → estimation générique main d'œuvre
    return {
        "item": item,
        "prix_unitaire_ht": round(45.0 * coeff, 2),
        "unite": unite or "heure",
        "region": region,
        "source": "estimation_main_oeuvre",
        "note": "Prix estimé - à vérifier avec vos fournisseurs locaux"
    }
