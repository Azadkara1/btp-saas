"""
Tests de non-régression word_service.py — Batch 11 T3.
Version plus légère de test_pdf_service.py (python-docx n'a pas de bug de
couleur persistante comme fpdf2, mais les mêmes règles métier doivent
produire le même texte que côté PDF).
"""
import pytest

from helpers import make_devis, make_ligne, make_signature_png_base64, docx_text

MODELES = ["moderne", "pro"]


@pytest.mark.parametrize("modele", MODELES)
def test_un_lot_cinq_lignes_toutes_visibles(modele):
    lignes = [
        make_ligne(lot="LOT 1 - Peinture", poste=f"Poste{i}", description=f"DescriptionDetaillee{i}")
        for i in range(5)
    ]
    devis = make_devis(lignes=lignes, modele=modele)

    text = docx_text(devis)

    for i in range(5):
        assert f"Poste{i}" in text
        assert f"DescriptionDetaillee{i}" in text


@pytest.mark.parametrize("modele", MODELES)
def test_afficher_signature_false_masque_toute_mention_accord(modele):
    devis = make_devis(
        modele=modele,
        afficher_signature=False,
        mentions_legales=["Signature du client precedee de la mention 'Bon pour accord'"],
    )

    text = docx_text(devis, document_type="devis")

    assert "accord" not in text.lower()


@pytest.mark.parametrize("modele", MODELES)
def test_quantite_none_affiche_au_reel(modele):
    devis = make_devis(lignes=[make_ligne(quantite=None)], modele=modele)

    text = docx_text(devis)

    assert "au réel" in text


@pytest.mark.parametrize("modele", MODELES)
def test_sans_tva_affiche_293b_sans_mention_tva_residuelle(modele):
    devis = make_devis(modele=modele, mentions_legales=["TVA applicable selon taux en vigueur"])

    text = docx_text(devis, with_tva=False)

    assert "293 B" in text
    assert "TVA applicable" not in text


@pytest.mark.parametrize("modele", MODELES)
def test_signature_nom_sans_image_affiche_le_nom(modele):
    devis = make_devis(modele=modele)

    text = docx_text(devis, signature_nom_signataire="Jean Dupont", signature_date="25/08/2026")

    assert "Jean Dupont" in text
    assert "25/08/2026" in text
    assert "Fait a" not in text


@pytest.mark.parametrize("modele", MODELES)
def test_signature_image_generee_sans_erreur_et_texte_toujours_visible(modele):
    lignes = [make_ligne(poste=f"Poste{i}", description=f"Desc{i}") for i in range(3)]
    devis = make_devis(lignes=lignes, modele=modele)
    image_b64 = make_signature_png_base64()

    text = docx_text(devis, signature_nom_signataire="Jean Dupont", signature_image_base64=image_b64)

    for i in range(3):
        assert f"Poste{i}" in text
    assert "Bon pour accord" in text
