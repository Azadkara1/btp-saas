"""
Tests de la retenue de garantie (Batch 12 T4-3).

Vérifie le rendu PDF/Word : ligne de déduction visible, montant correct,
et chaînage correct avec l'acompte quand les deux s'appliquent en même temps
(ex: facture de solde avec retenue de garantie).
"""
import pytest

from tests.helpers import make_devis, make_ligne, pdf_text, docx_text


@pytest.mark.parametrize("modele", ["moderne", "pro"])
def test_retenue_garantie_affiche_ligne_et_montant_avec_tva(modele):
    devis = make_devis(
        modele=modele,
        lignes=[make_ligne(prix_unitaire_ht=1000.0, tva_taux=20.0, quantite=1)],
        retenue_garantie_taux=5.0,
    )
    # total_ht=1000, total_tva=200, total_ttc=1200 -> retenue 5% = 60.00

    text = pdf_text(devis, document_type="facture")
    docx_txt = docx_text(devis, document_type="facture")

    assert "Retenue de garantie (5%)" in text, f"[{modele}] ligne retenue absente du PDF"
    assert "60,00" in text, f"[{modele}] montant retenue incorrect dans le PDF"
    assert "Retenue de garantie (5%)" in docx_txt, f"[{modele}] ligne retenue absente du Word"
    assert "60,00" in docx_txt, f"[{modele}] montant retenue incorrect dans le Word"


def test_retenue_garantie_absente_si_taux_non_renseigne():
    devis = make_devis(retenue_garantie_taux=None)

    text = pdf_text(devis, document_type="facture")

    assert "Retenue de garantie" not in text


def test_retenue_garantie_se_chaine_apres_acompte():
    """Cas facture de solde (T4-2) : acompte ET retenue de garantie sur le même document."""
    devis = make_devis(
        lignes=[make_ligne(prix_unitaire_ht=1000.0, tva_taux=20.0, quantite=1)],
        acompte=360.0,
        retenue_garantie_taux=5.0,
    )
    # total_ttc=1200, acompte=360 -> net intermédiaire 840, retenue 5% de 1200 = 60 -> net final 780

    text = pdf_text(devis, document_type="facture")

    assert "Acompte" in text
    assert "Retenue de garantie (5%)" in text
    assert "780,00" in text, "le net à payer final doit déduire l'acompte PUIS la retenue de garantie"
