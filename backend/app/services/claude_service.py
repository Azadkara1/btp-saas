"""
Orchestration des appels à l'API Anthropic.
Gère le Tool Use pour la recherche de prix du marché.
Isolé ici pour faciliter les tests et l'évolution (Étape 3 : vision, voix).
"""
import json
import logging
import re
from collections import Counter
import anthropic
from typing import Optional

from app.core.config import get_settings
from app.core.prompts import QUOTE_SYSTEM_PROMPT
from app.models.quote import QuoteRequest, QuoteResponse, Devis
from app.services.price_search import search_market_price

settings = get_settings()
client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

# ── Définition du Tool Use Claude ───────────────────────────────
TOOLS = [
    {
        "name": "search_market_price",
        "description": (
            "Recherche le prix du marché actuel (2026) pour une prestation BTP en France. "
            "À utiliser uniquement quand l'artisan n'a pas fourni de prix."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "item": {
                    "type": "string",
                    "description": "La prestation ou le matériau dont on cherche le prix (ex: 'pose carrelage sol', 'béton prêt à l emploi')"
                },
                "region": {
                    "type": "string",
                    "description": "Région française pour adapter les prix locaux"
                },
                "unite": {
                    "type": "string",
                    "description": "Unité souhaitée (m², ml, heure, forfait...)"
                }
            },
            "required": ["item", "region"]
        }
    }
]


async def generate_quote(request: QuoteRequest) -> QuoteResponse:
    """
    Génère un devis structuré à partir d'une description textuelle.
    Utilise le Tool Use Claude pour rechercher les prix manquants.
    """
    user_message = _build_user_message(request)

    messages = [{"role": "user", "content": user_message}]
    total_tokens = 0

    # ── Boucle agentic Tool Use ──────────────────────────────────
    while True:
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=4096,
            system=QUOTE_SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages
        )

        total_tokens += response.usage.input_tokens + response.usage.output_tokens

        # Claude a terminé → on parse le JSON
        if response.stop_reason == "end_turn":
            result = _parse_final_response(response, total_tokens)
            if result.success and result.devis:
                a = result.devis.artisan
                if request.artisan_iban:         a.iban         = request.artisan_iban
                if request.artisan_bic:          a.bic          = request.artisan_bic
                if request.artisan_adresse:      a.adresse      = request.artisan_adresse
                if request.artisan_code_postal:  a.code_postal  = request.artisan_code_postal
                if request.artisan_ville:        a.ville        = request.artisan_ville
                if request.artisan_telephone:    a.telephone    = request.artisan_telephone
                if request.artisan_email:        a.email        = request.artisan_email
                if request.artisan_site_web:     a.site_web     = request.artisan_site_web
                if request.artisan_logo_base64:  a.logo_base64  = request.artisan_logo_base64
                if request.numero_document:
                    result.devis.numero_document = request.numero_document
                if request.remise_type:    result.devis.remise_type   = request.remise_type
                if request.remise_valeur:  result.devis.remise_valeur = request.remise_valeur
                if request.acompte:        result.devis.acompte       = request.acompte
                result.devis.modele = request.modele or "moderne"
                result.devis.validite_jours = request.validite_jours  # toujours depuis le formulaire (None si vide)
                if request.conditions_paiement: result.devis.conditions_paiement = request.conditions_paiement
                # Garde-fou : avertir si plusieurs lignes de natures différentes ont le même PU
                pus = [round(l.prix_unitaire_ht, 2) for l in result.devis.lignes]
                duplicates = [pu for pu, cnt in Counter(pus).items() if cnt > 1]
                if duplicates:
                    logging.warning("[DEVIS] PU identiques sur plusieurs lignes : %s", duplicates)
            return result

        # Claude veut utiliser un outil
        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = await _handle_tool_calls(response.content, request.region)
            messages.append({"role": "user", "content": tool_results})
            continue

        # Cas inattendu
        break

    return QuoteResponse(success=False, error="Réponse inattendue du modèle.")


def _build_user_message(request: QuoteRequest) -> str:
    """Construit le message utilisateur enrichi avec le contexte artisan."""
    parts = [f"Description du chantier :\n{request.description}"]

    if request.artisan_nom:
        parts.append(f"Artisan : {request.artisan_nom}")
    if request.artisan_siret:
        parts.append(f"SIRET : {request.artisan_siret}")
    if request.client_nom:
        parts.append(f"Client : {request.client_nom}")
    if request.client_adresse:
        parts.append(f"Adresse chantier : {request.client_adresse}")

    parts.append(f"Région pour les prix du marché : {request.region}")

    if request.prix_personnalises:
        lignes = "\n".join(
            f"- {p.prestation} : {p.prix_unitaire_ht} €/{p.unite}" if p.unite
            else f"- {p.prestation} : {p.prix_unitaire_ht} €"
            for p in request.prix_personnalises
        )
        parts.append(
            f"\nPrix fournis par l'artisan (PRIORITÉ ABSOLUE — utilise ces prix, source_prix = 'artisan') :\n{lignes}"
        )

    return "\n".join(parts)


async def _handle_tool_calls(content_blocks: list, region: str) -> list:
    """Exécute les appels d'outils demandés par Claude et retourne les résultats."""
    tool_results = []

    for block in content_blocks:
        if block.type != "tool_use":
            continue

        if block.name == "search_market_price":
            result = await search_market_price(
                item=block.input.get("item", ""),
                region=block.input.get("region", region),
                unite=block.input.get("unite", "")
            )
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result, ensure_ascii=False)
            })

    return tool_results


def _parse_final_response(response, total_tokens: int) -> QuoteResponse:
    """Parse la réponse finale de Claude en objet Devis."""
    try:
        text_content = next(
            (block.text for block in response.content if hasattr(block, "text")),
            None
        )

        if not text_content:
            return QuoteResponse(success=False, error="Aucun contenu texte dans la réponse.")

        clean_text = text_content.strip()

        if not clean_text:
            return QuoteResponse(success=False, error="Réponse Claude vide après nettoyage.")

        # Extraction robuste : capture du premier { jusqu'au dernier }
        # Résiste aux backticks markdown ou texte explicatif ajouté par Claude
        match = re.search(r'\{.*\}', clean_text, re.DOTALL)
        if not match:
            return QuoteResponse(success=False, error="Aucun bloc JSON trouvé dans la réponse Claude.")

        json_text = match.group(0)
        data = json.loads(json_text)
        devis = Devis(**data)

        return QuoteResponse(
            success=True,
            devis=devis,
            tokens_used=total_tokens
        )

    except json.JSONDecodeError as e:
        return QuoteResponse(success=False, error=f"Erreur de parsing du devis : {str(e)}")
    except Exception as e:
        return QuoteResponse(success=False, error=f"Erreur de parsing du devis : {str(e)}")
