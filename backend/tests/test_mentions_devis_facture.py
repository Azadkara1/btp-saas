"""
Tests Batch 23 — mentions légales spécifiques au devis masquées en facture.

Avant ce correctif, seules 2 mentions précises ("valable X jours" et "bon
pour accord") étaient conditionnées au document_type. Toute AUTRE mention
générée par Claude contenant le mot "devis" fuitait telle quelle sur une
facture (y compris une facture d'acompte) — ce ne sont pas les mêmes
mentions légales qu'un devis.
"""
import pytest

from helpers import docx_text, make_devis, pdf_text

MODELES = ["moderne", "pro"]


@pytest.mark.parametrize("modele", MODELES)
def test_mention_custom_contenant_devis_disparait_en_facture(modele):
    devis = make_devis(
        modele=modele,
        mentions_legales=["Ce devis engage les deux parties des sa signature"],
    )

    pdf = pdf_text(devis, document_type="facture")
    word = docx_text(devis, document_type="facture")

    assert "engage les deux parties" not in pdf, f"[{modele}] mention devis fuite dans le PDF facture"
    assert "engage les deux parties" not in word, f"[{modele}] mention devis fuite dans le Word facture"


@pytest.mark.parametrize("modele", MODELES)
def test_mention_custom_contenant_devis_visible_en_devis(modele):
    devis = make_devis(
        modele=modele,
        mentions_legales=["Ce devis engage les deux parties des sa signature"],
    )

    pdf = pdf_text(devis, document_type="devis")
    word = docx_text(devis, document_type="devis")

    assert "engage les deux parties" in pdf, f"[{modele}] mention devis absente du PDF devis"
    assert "engage les deux parties" in word, f"[{modele}] mention devis absente du Word devis"


@pytest.mark.parametrize("modele", MODELES)
def test_mention_bon_pour_accord_disparait_en_facture_acompte(modele):
    """Avant correctif : cette mention ne disparaissait que si
    afficher_signature=False — jamais simplement parce que document_type
    était une facture (y compris d'acompte)."""
    devis = make_devis(
        modele=modele,
        type_facture="acompte",
        afficher_signature=True,
        mentions_legales=["Signature du client precedee de la mention 'Bon pour accord'"],
    )

    pdf = pdf_text(devis, document_type="facture")
    word = docx_text(devis, document_type="facture")

    assert "pour accord" not in pdf.lower(), f"[{modele}] mention accord fuite dans le PDF facture d'acompte"
    assert "pour accord" not in word.lower(), f"[{modele}] mention accord fuite dans le Word facture d'acompte"


@pytest.mark.parametrize("modele", MODELES)
def test_mention_neutre_reste_visible_en_facture(modele):
    """Garde-fou : le filtre ne doit retirer QUE les mentions contenant
    'devis' ou 'accord', pas toutes les mentions en mode facture."""
    devis = make_devis(
        modele=modele,
        mentions_legales=["Garantie decennale couvrant les travaux realises"],
    )

    pdf = pdf_text(devis, document_type="facture")
    word = docx_text(devis, document_type="facture")

    assert "Garantie decennale" in pdf, f"[{modele}] mention neutre retiree a tort du PDF facture"
    assert "Garantie decennale" in word, f"[{modele}] mention neutre retiree a tort du Word facture"
