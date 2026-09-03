"""
Tests des spécificités TVA BTP (Batch 12 T4-4 : taux réduits 10%/5.5%,
T4-5 : autoliquidation).
"""
import pytest

from tests.helpers import make_devis, make_ligne, pdf_text, docx_text


@pytest.mark.parametrize("modele", ["moderne", "pro"])
def test_tva_10_pourcent_affiche_mention_attestation(modele):
    devis = make_devis(modele=modele, lignes=[make_ligne(tva_taux=10.0)])

    pdf_txt = pdf_text(devis)
    docx_txt = docx_text(devis)

    assert "279-0 bis" in pdf_txt, f"[{modele}] mention art. 279-0 bis absente du PDF"
    assert "279-0 bis" in docx_txt, f"[{modele}] mention art. 279-0 bis absente du Word"


@pytest.mark.parametrize("modele", ["moderne", "pro"])
def test_tva_5_5_pourcent_affiche_mention_attestation(modele):
    devis = make_devis(modele=modele, lignes=[make_ligne(tva_taux=5.5)])

    pdf_txt = pdf_text(devis)
    docx_txt = docx_text(devis)

    assert "278-0 bis A" in pdf_txt, f"[{modele}] mention art. 278-0 bis A absente du PDF"
    assert "278-0 bis A" in docx_txt, f"[{modele}] mention art. 278-0 bis A absente du Word"


def test_tva_20_pourcent_naffiche_aucune_mention_taux_reduit():
    devis = make_devis(lignes=[make_ligne(tva_taux=20.0)])

    text = pdf_text(devis)

    assert "279-0 bis" not in text
    assert "278-0 bis A" not in text


def test_deux_lignes_taux_reduits_differents_affichent_les_deux_mentions():
    devis = make_devis(lignes=[
        make_ligne(poste="Isolation", tva_taux=5.5, prix_unitaire_ht=500.0),
        make_ligne(poste="Peinture", tva_taux=10.0, prix_unitaire_ht=300.0),
    ])

    text = pdf_text(devis)

    assert "279-0 bis" in text
    assert "278-0 bis A" in text


def test_tva_reduite_masquee_en_mode_sans_tva():
    devis = make_devis(lignes=[make_ligne(tva_taux=10.0)])

    text = pdf_text(devis, with_tva=False)

    assert "279-0 bis" not in text
    assert "TVA non applicable, art. 293 B" in text


@pytest.mark.parametrize("modele", ["moderne", "pro"])
def test_autoliquidation_affiche_mention_et_masque_293b(modele):
    devis = make_devis(modele=modele, autoliquidation=True)

    pdf_txt = pdf_text(devis, with_tva=False)
    docx_txt = docx_text(devis, with_tva=False)

    assert "283-2 nonies" in pdf_txt, f"[{modele}] mention autoliquidation absente du PDF"
    assert "TVA non applicable, art. 293 B" not in pdf_txt, f"[{modele}] 293 B ne doit jamais apparaître en autoliquidation"
    assert "283-2 nonies" in docx_txt, f"[{modele}] mention autoliquidation absente du Word"
    assert "293 B" not in docx_txt, f"[{modele}] 293 B ne doit jamais apparaître en autoliquidation"


def test_autoliquidation_masque_les_mentions_taux_reduit():
    devis = make_devis(lignes=[make_ligne(tva_taux=10.0)], autoliquidation=True)

    text = pdf_text(devis)

    assert "279-0 bis" not in text
    assert "283-2 nonies" in text
