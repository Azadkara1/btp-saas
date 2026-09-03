"""
Tests de la facture d'acompte (Batch 12 T4-1).

`_build_acompte_devis` est une fonction pure (même pattern que `_is_signable`
dans public.py) : testée directement, sans base de données.
"""
import pytest

from app.models.quote import TotauxDevis
from app.routers.documents import _apply_montant_deja_verse, _build_acompte_devis
from tests.helpers import docx_text, make_devis, make_ligne, pdf_text


def test_build_acompte_devis_calcule_montant_et_tva_correctement():
    devis = make_devis(
        lignes=[make_ligne(prix_unitaire_ht=1000.0, tva_taux=20.0, quantite=1)],
        numero_document="DEVIS-042",
    )

    acompte = _build_acompte_devis(devis, 30, numero_devis_fallback=None)

    assert len(acompte.lignes) == 1
    assert acompte.lignes[0].prix_unitaire_ht == 300.0
    assert acompte.lignes[0].tva_taux == 20.0
    assert "DEVIS-042" in acompte.lignes[0].description
    assert acompte.totaux.total_ht == 300.0
    assert acompte.totaux.total_tva == 60.0
    assert acompte.totaux.total_ttc == 360.0
    assert acompte.type_facture == "acompte"
    assert acompte.numero_document is None


def test_build_acompte_devis_taux_tva_moyen_pondere_si_taux_multiples():
    devis = make_devis(lignes=[
        make_ligne(prix_unitaire_ht=800.0, tva_taux=20.0, quantite=1),
        make_ligne(prix_unitaire_ht=200.0, tva_taux=10.0, quantite=1),
    ])
    # total_tva = 800*20% + 200*10% = 160 + 20 = 180 -> taux moyen 18%
    devis = devis.model_copy(update={
        "totaux": TotauxDevis(total_ht=1000.0, total_tva=180.0, total_ttc=1180.0)
    })

    acompte = _build_acompte_devis(devis, 50, numero_devis_fallback="FALLBACK-1")

    assert acompte.lignes[0].tva_taux == 18.0
    assert acompte.totaux.total_ht == 500.0
    assert acompte.totaux.total_tva == 90.0
    assert acompte.totaux.total_ttc == 590.0


def test_build_acompte_devis_utilise_fallback_numero_si_devis_sans_numero():
    devis = make_devis(numero_document=None)

    acompte = _build_acompte_devis(devis, 30, numero_devis_fallback="DEV-2026-007")

    assert "DEV-2026-007" in acompte.lignes[0].description


@pytest.mark.parametrize("modele", ["moderne", "pro"])
def test_facture_acompte_affiche_le_bon_libelle_pdf_et_word(modele):
    devis = make_devis(modele=modele, type_facture="acompte")

    pdf_txt = pdf_text(devis, document_type="facture")
    docx_txt = docx_text(devis, document_type="facture")

    assert "FACTURE D'ACOMPTE" in pdf_txt, f"[{modele}] libellé FACTURE D'ACOMPTE absent du PDF"
    assert "FACTURE D'ACOMPTE" in docx_txt, f"[{modele}] libellé FACTURE D'ACOMPTE absent du Word"


# ── Facture de solde (Batch 12 T4-2) ─────────────────────────────────────────

def test_apply_montant_deja_verse_sans_acompte_ne_change_rien():
    devis = make_devis()
    devis = devis.model_copy(update={"totaux": TotauxDevis(total_ht=1000.0, total_tva=200.0, total_ttc=1200.0)})

    updated, total_ttc = _apply_montant_deja_verse(devis, 0)

    assert updated is devis
    assert updated.type_facture is None
    assert total_ttc == 1200.0


def test_apply_montant_deja_verse_deduit_et_recalcule_net_a_payer():
    devis = make_devis()
    devis = devis.model_copy(update={"totaux": TotauxDevis(total_ht=1000.0, total_tva=200.0, total_ttc=1200.0)})

    updated, total_ttc = _apply_montant_deja_verse(devis, 360.0)

    assert updated.type_facture == "solde"
    assert updated.acompte == 360.0
    assert updated.totaux.net_a_payer == 840.0
    assert updated.totaux.total_ttc == 1200.0  # le total légal complet reste affiché dans le PDF
    assert total_ttc == 840.0  # mais la colonne DB (dashboard) ne compte que le reste à payer


def test_apply_montant_deja_verse_ne_descend_jamais_sous_zero():
    devis = make_devis()
    devis = devis.model_copy(update={"totaux": TotauxDevis(total_ht=100.0, total_tva=20.0, total_ttc=120.0)})

    updated, total_ttc = _apply_montant_deja_verse(devis, 500.0)  # acompte > total (cas anormal)

    assert updated.totaux.net_a_payer == 0.0
    assert total_ttc == 0.0


@pytest.mark.parametrize("modele", ["moderne", "pro"])
def test_facture_solde_affiche_le_bon_libelle_et_le_montant_deja_verse(modele):
    devis = make_devis(modele=modele, type_facture="solde", acompte=360.0)
    devis = devis.model_copy(update={"totaux": TotauxDevis(total_ht=1000.0, total_tva=200.0, total_ttc=1200.0, net_a_payer=840.0)})

    pdf_txt = pdf_text(devis, document_type="facture")
    docx_txt = docx_text(devis, document_type="facture")

    assert "FACTURE DE SOLDE" in pdf_txt, f"[{modele}] libellé FACTURE DE SOLDE absent du PDF"
    assert "FACTURE DE SOLDE" in docx_txt, f"[{modele}] libellé FACTURE DE SOLDE absent du Word"
