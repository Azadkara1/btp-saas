"""
Tests des deux points d'injection post-génération (jamais envoyée à Claude) :
- claude_service.py::_inject_post_generation (flux génération)
- import_service.py::_inject_artisan (flux import)

Jamais couverts jusqu'ici (trouvé par revue de code, Batch 16). CLAUDE.md
documente ces deux points comme un piège classique : tout champ `artisan_*`
ajouté à l'un doit l'être à l'autre, sous peine de fonctionner en génération
mais de rester invisible après un import. Le test de parité ci-dessous
verifie explicitement que les champs partagés le sont bien aux deux endroits.
"""
from app.models.quote import QuoteRequest
from app.services.claude_service import _inject_post_generation
from app.services.import_service import _inject_artisan
from tests.helpers import make_devis


def _make_request(**overrides) -> QuoteRequest:
    base = dict(description="Rénovation complète d'une salle de bain de 6m²", region="Rhône-Alpes")
    base.update(overrides)
    return QuoteRequest(**base)


# ── claude_service.py::_inject_post_generation ──────────────────────────────

def test_inject_post_generation_champs_artisan():
    devis = make_devis()
    request = _make_request(
        artisan_iban="FR7630006000011234567890189",
        artisan_bic="BNPAFRPPXXX",
        artisan_assurance_nom="MAAF",
        artisan_assurance_contrat="123456",
        artisan_assurance_couverture="France entière",
        artisan_statut_juridique="societe",
        artisan_forme_juridique="SARL",
        artisan_capital_social=10000.0,
        artisan_adresse="1 rue du Chantier",
        artisan_code_postal="69001",
        artisan_ville="Lyon",
        artisan_telephone="0600000000",
        artisan_email="artisan@test.fr",
        artisan_site_web="www.artisan.fr",
        artisan_logo_base64="base64data",
    )

    updated = _inject_post_generation(devis, request)

    assert updated.artisan.iban == "FR7630006000011234567890189"
    assert updated.artisan.bic == "BNPAFRPPXXX"
    assert updated.artisan.assurance_nom == "MAAF"
    assert updated.artisan.assurance_contrat == "123456"
    assert updated.artisan.assurance_couverture == "France entière"
    assert updated.artisan.statut_juridique == "societe"
    assert updated.artisan.forme_juridique == "SARL"
    assert updated.artisan.capital_social == 10000.0
    assert updated.artisan.adresse == "1 rue du Chantier"
    assert updated.artisan.code_postal == "69001"
    assert updated.artisan.ville == "Lyon"
    assert updated.artisan.telephone == "0600000000"
    assert updated.artisan.email == "artisan@test.fr"
    assert updated.artisan.site_web == "www.artisan.fr"
    assert updated.artisan.logo_base64 == "base64data"


def test_inject_post_generation_champs_document():
    devis = make_devis()
    request = _make_request(
        client_email="client@test.fr",
        numero_document="DEV-2026-001",
        remise_type="pourcentage",
        remise_valeur=10.0,
        acompte=500.0,
        retenue_garantie_taux=5.0,
        autoliquidation=True,
        modele="pro",
        validite_jours=30,
        conditions_paiement="30 jours",
        afficher_signature=False,
    )

    updated = _inject_post_generation(devis, request)

    assert updated.client.email == "client@test.fr"
    assert updated.numero_document == "DEV-2026-001"
    assert updated.remise_type == "pourcentage"
    assert updated.remise_valeur == 10.0
    assert updated.acompte == 500.0
    assert updated.retenue_garantie_taux == 5.0
    assert updated.autoliquidation is True
    assert updated.modele == "pro"
    assert updated.validite_jours == 30
    assert updated.conditions_paiement == "30 jours"
    assert updated.afficher_signature is False


def test_inject_post_generation_modele_defaut_moderne_si_absent():
    devis = make_devis()
    request = _make_request(modele=None)

    updated = _inject_post_generation(devis, request)

    assert updated.modele == "moderne"


def test_inject_post_generation_autoliquidation_toujours_propagee_meme_false():
    """Contrairement aux autres champs (if request.x: ...), autoliquidation
    doit être propagée inconditionnellement — sinon un False explicite de
    l'utilisateur serait silencieusement ignoré (piège documenté dans
    CLAUDE.md : booléen Pydantic + valeur falsy)."""
    devis = make_devis()
    devis.autoliquidation = True  # valeur initiale à écraser
    request = _make_request(autoliquidation=False)

    updated = _inject_post_generation(devis, request)

    assert updated.autoliquidation is False


# ── import_service.py::_inject_artisan ──────────────────────────────────────

def test_inject_artisan_champs_partages_avec_claude_service():
    """Les champs communs aux deux points d'injection doivent produire le
    même résultat — c'est exactement le piège documenté dans CLAUDE.md."""
    request = _make_request(
        artisan_iban="FR7630006000011234567890189",
        artisan_bic="BNPAFRPPXXX",
        artisan_assurance_nom="MAAF",
        artisan_assurance_contrat="123456",
        artisan_assurance_couverture="France entière",
        artisan_statut_juridique="societe",
        artisan_forme_juridique="SARL",
        artisan_capital_social=10000.0,
        artisan_adresse="1 rue du Chantier",
        artisan_code_postal="69001",
        artisan_ville="Lyon",
        artisan_telephone="0600000000",
        artisan_email="artisan@test.fr",
        artisan_site_web="www.artisan.fr",
        artisan_logo_base64="base64data",
    )

    devis_claude = _inject_post_generation(make_devis(), request)

    devis_import = make_devis()
    _inject_artisan(devis_import, request)

    champs_partages = [
        "iban", "bic", "assurance_nom", "assurance_contrat", "assurance_couverture",
        "statut_juridique", "forme_juridique", "capital_social",
        "adresse", "code_postal", "ville", "telephone", "email", "site_web", "logo_base64",
    ]
    for champ in champs_partages:
        val_claude = getattr(devis_claude.artisan, champ)
        val_import = getattr(devis_import.artisan, champ)
        assert val_claude == val_import, f"Divergence sur artisan.{champ} : claude={val_claude!r} import={val_import!r}"


def test_inject_artisan_nom_et_siret_uniquement_a_limport():
    """nom/siret ne sont PAS ré-injectés en génération (Claude les produit
    lui-même depuis la description) — mais DOIVENT l'être à l'import
    (le document importé n'a pas de raison de connaître le profil artisan)."""
    devis = make_devis()
    request = _make_request(artisan_nom="SARL Dupont BTP", artisan_siret="12345678900012")

    _inject_artisan(devis, request)

    assert devis.artisan.nom == "SARL Dupont BTP"
    assert devis.artisan.siret == "12345678900012"
