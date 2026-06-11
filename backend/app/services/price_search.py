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
    "maçonnerie":               {"prix": 45.0,  "unite": "m²",      "fourchette": "35-60"},
    "béton":                    {"prix": 95.0,  "unite": "m³",      "fourchette": "80-120"},
    "terrassement":             {"prix": 12.0,  "unite": "m³",      "fourchette": "8-20"},
    "charpente":                {"prix": 80.0,  "unite": "m²",      "fourchette": "60-110"},

    # Carrelage — entrées distinctes pour éviter les confusions
    "dépose carrelage":         {"prix": 15.0,  "unite": "m²",      "fourchette": "10-22"},
    "pose carrelage":           {"prix": 35.0,  "unite": "m²",      "fourchette": "25-50"},
    "fourniture carrelage":     {"prix": 30.0,  "unite": "m²",      "fourchette": "15-60"},
    "carrelage fourniture pose":{"prix": 65.0,  "unite": "m²",      "fourchette": "50-90"},

    # Peinture
    "peinture intérieure":      {"prix": 18.0,  "unite": "m²",      "fourchette": "12-25"},
    "peinture façade":          {"prix": 25.0,  "unite": "m²",      "fourchette": "18-35"},

    # Plâtrerie / Cloisons / Isolation
    "enduit plâtre":            {"prix": 22.0,  "unite": "m²",      "fourchette": "15-30"},
    "placo pose":               {"prix": 28.0,  "unite": "m²",      "fourchette": "20-38"},
    "isolation thermique":      {"prix": 25.0,  "unite": "m²",      "fourchette": "18-40"},

    # Électricité — une entrée par type de prestation
    "prise électrique":         {"prix": 45.0,  "unite": "unité",   "fourchette": "35-65"},
    "interrupteur":             {"prix": 35.0,  "unite": "unité",   "fourchette": "25-55"},
    "point lumineux":           {"prix": 85.0,  "unite": "point",   "fourchette": "60-120"},
    "tableau électrique":       {"prix": 900.0, "unite": "forfait", "fourchette": "600-1400"},

    # Plomberie
    "plomberie evacuation":     {"prix": 55.0,  "unite": "ml",      "fourchette": "40-75"},
    "robinetterie":             {"prix": 120.0, "unite": "point",   "fourchette": "80-200"},
    "sanitaire":                {"prix": 250.0, "unite": "point",   "fourchette": "150-400"},

    # Menuiserie
    "fenêtre pvc":              {"prix": 650.0, "unite": "unité",   "fourchette": "450-900"},
    "porte intérieure":         {"prix": 350.0, "unite": "unité",   "fourchette": "200-600"},
    "volet roulant":            {"prix": 500.0, "unite": "unité",   "fourchette": "350-800"},

    # Revêtements sols
    "parquet pose":             {"prix": 30.0,  "unite": "m²",      "fourchette": "20-45"},
    "moquette":                 {"prix": 18.0,  "unite": "m²",      "fourchette": "12-28"},

    # Toiture
    "toiture tuiles":           {"prix": 120.0, "unite": "m²",      "fourchette": "90-160"},

    # Main d'œuvre générique (dernier recours)
    "main d'oeuvre":            {"prix": 45.0,  "unite": "heure",   "fourchette": "35-60"},
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
