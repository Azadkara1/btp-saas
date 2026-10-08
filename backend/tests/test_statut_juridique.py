"""
Tests de non-régression PDF/Word — statut juridique (Batch 21).

Vérifie que la mention "(EI)" (auto-entrepreneur) et la ligne forme
juridique + capital social (société) apparaissent bien dans le document
généré, et que les devis sans statut_juridique (antérieurs à Batch 21)
ne voient aucune mention ajoutée (rétrocompatibilité).
"""
import pytest

from app.models.quote import ArtisanInfo
from helpers import docx_text, make_devis, pdf_text

MODELES = ["moderne", "pro"]


@pytest.mark.parametrize("modele", MODELES)
def test_auto_entrepreneur_affiche_mention_ei(modele):
    devis = make_devis(
        modele=modele,
        artisan=ArtisanInfo(nom="Jean Dupont", statut_juridique="auto_entrepreneur"),
    )

    assert "Jean Dupont (EI)" in pdf_text(devis), f"[{modele}] mention (EI) absente du PDF"
    assert "Jean Dupont (EI)" in docx_text(devis), f"[{modele}] mention (EI) absente du Word"


@pytest.mark.parametrize("modele", MODELES)
def test_societe_affiche_forme_et_capital_social(modele):
    devis = make_devis(
        modele=modele,
        artisan=ArtisanInfo(
            nom="SARL Dupont BTP",
            statut_juridique="societe",
            forme_juridique="SARL",
            capital_social=10000.0,
        ),
    )

    pdf = pdf_text(devis)
    word = docx_text(devis)

    assert "SARL" in pdf and "capital" in pdf.lower(), f"[{modele}] mention forme/capital absente du PDF"
    assert "SARL" in word and "capital" in word.lower(), f"[{modele}] mention forme/capital absente du Word"
    assert "(EI)" not in pdf and "(EI)" not in word, f"[{modele}] mention (EI) ne doit pas apparaître pour une société"


@pytest.mark.parametrize("modele", MODELES)
def test_statut_juridique_absent_aucune_mention_ajoutee(modele):
    """Rétrocompatibilité : un devis généré avant Batch 21 (statut_juridique
    absent, donc None) ne doit voir aucune nouvelle mention apparaître."""
    devis = make_devis(modele=modele, artisan=ArtisanInfo(nom="Artisan Sans Statut"))

    pdf = pdf_text(devis)
    word = docx_text(devis)

    assert "(EI)" not in pdf and "(EI)" not in word
    assert "capital" not in pdf.lower() and "capital" not in word.lower()
