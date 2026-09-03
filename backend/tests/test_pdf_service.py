"""
Tests de non-régression pdf_service.py — Batch 11 T3.

Le bug "texte invisible" (set_text_color persistant dans fpdf2) est réapparu
3 fois (Batch 4, Batch 5, règle B du Batch 10). Ces tests remplacent les
règles A/B/C documentées dans CLAUDE.md par des assertions automatiques :
si une future modification de pdf_service.py fait redisparaître du texte,
ces tests échouent au lieu de laisser passer un PDF cassé en production.

Tous les cas sont exécutés pour les 2 modèles ("moderne" et "pro").
"""
import pytest

from helpers import make_devis, make_ligne, make_signature_png_base64, pdf_text

MODELES = ["moderne", "pro"]


@pytest.mark.parametrize("modele", MODELES)
def test_un_lot_cinq_lignes_toutes_visibles(modele):
    lignes = [
        make_ligne(lot="LOT 1 - Peinture", poste=f"Poste{i}", description=f"DescriptionDetaillee{i}")
        for i in range(5)
    ]
    devis = make_devis(lignes=lignes, modele=modele)

    text = pdf_text(devis)

    for i in range(5):
        assert f"Poste{i}" in text, f"[{modele}] Poste{i} invisible dans le PDF"
        assert f"DescriptionDetaillee{i}" in text, f"[{modele}] DescriptionDetaillee{i} invisible dans le PDF"


@pytest.mark.parametrize("modele", MODELES)
def test_big_lot_40_lignes_saut_de_page_aucune_ligne_perdue(modele):
    lignes = [
        make_ligne(lot="LOT UNIQUE", poste=f"Poste{i}", description=f"Desc{i}")
        for i in range(40)
    ]
    devis = make_devis(lignes=lignes, modele=modele)

    text = pdf_text(devis)

    manquantes = [i for i in range(40) if f"Poste{i}" not in text or f"Desc{i}" not in text]
    assert not manquantes, f"[{modele}] lignes invisibles après saut de page : {manquantes}"


@pytest.mark.parametrize("modele", MODELES)
def test_afficher_signature_false_masque_toute_mention_accord(modele):
    devis = make_devis(
        modele=modele,
        afficher_signature=False,
        mentions_legales=["Signature du client precedee de la mention 'Bon pour accord'"],
    )

    text = pdf_text(devis, document_type="devis")

    assert "accord" not in text.lower(), f"[{modele}] mention 'accord' encore visible alors que afficher_signature=False"


@pytest.mark.parametrize("modele", MODELES)
def test_quantite_none_affiche_au_reel(modele):
    devis = make_devis(lignes=[make_ligne(quantite=None)], modele=modele)

    text = pdf_text(devis)

    assert "au réel" in text, f"[{modele}] 'au réel' absent pour une quantite=None"


@pytest.mark.parametrize("modele", MODELES)
def test_sans_tva_affiche_293b_sans_mention_tva_residuelle(modele):
    devis = make_devis(modele=modele, mentions_legales=["TVA applicable selon taux en vigueur"])

    text = pdf_text(devis, with_tva=False)

    assert "293 B" in text, f"[{modele}] mention art. 293 B absente en mode sans TVA"
    assert "TVA applicable" not in text, f"[{modele}] mention TVA générique non masquée en mode sans TVA"


@pytest.mark.parametrize("modele", MODELES)
def test_signature_nom_sans_image_affiche_le_nom(modele):
    devis = make_devis(modele=modele)

    text = pdf_text(devis, signature_nom_signataire="Jean Dupont", signature_date="25/08/2026")

    assert "Jean Dupont" in text, f"[{modele}] nom du signataire absent du PDF"
    assert "25/08/2026" in text, f"[{modele}] date de signature absente du PDF"
    assert "Fait a" not in text, f"[{modele}] le champ 'Fait à ...' ne doit plus apparaître une fois signé"


@pytest.mark.parametrize("modele", MODELES)
def test_signature_image_generee_sans_erreur_et_texte_toujours_visible(modele):
    lignes = [make_ligne(poste=f"Poste{i}", description=f"Desc{i}") for i in range(3)]
    devis = make_devis(lignes=lignes, modele=modele)
    image_b64 = make_signature_png_base64()

    text = pdf_text(devis, signature_nom_signataire="Jean Dupont", signature_image_base64=image_b64)

    for i in range(3):
        assert f"Poste{i}" in text, f"[{modele}] Poste{i} invisible après ajout d'une image de signature"
    assert "Bon pour accord" in text
