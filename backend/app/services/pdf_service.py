"""
Génération de PDF pour les devis/factures.
Utilise fpdf2 (pur Python, pas de dépendances système) au lieu de WeasyPrint.
"""
import base64
from datetime import date as date_class
from io import BytesIO
from typing import Optional
from app.models.quote import Devis

# ── Palette de couleurs (RGB) ────────────────────────────────────
BLUE       = (26,  86,  219)
GRAY       = (100, 116, 139)
LIGHT_GRAY = (248, 249, 250)
AMBER      = (245, 158,  11)
AMBER_BG   = (255, 248, 225)
BLACK      = (30,   30,  30)
WHITE      = (255, 255, 255)
BORDER     = (229, 231, 235)


def _safe(text: str) -> str:
    """Supprime les caractères hors cp1252 (emojis, ⚠, etc.) incompatibles avec Helvetica."""
    if not text:
        return ""
    return text.encode("cp1252", errors="ignore").decode("cp1252")


def _fmt_money(amount: float) -> str:
    """Format monétaire français : '1 234,56 €'
    Séparateur de milliers = espace insécable U+00A0 (cp1252 0xA0, safe pour Helvetica).
    """
    s = f"{amount:.2f}"
    int_part, dec_part = s.split(".")
    n, groups = len(int_part), []
    while n > 3:
        groups.insert(0, int_part[n - 3:n])
        n -= 3
    groups.insert(0, int_part[:n])
    return " ".join(groups) + "," + dec_part + " €"


def _fmt_date(iso_date: Optional[str]) -> str:
    """Convertit 'YYYY-MM-DD' en 'DD/MM/YYYY'. Retourne aujourd'hui si absent."""
    if iso_date:
        try:
            y, m, d = iso_date.split("-")
            return f"{d}/{m}/{y}"
        except Exception:
            pass
    return date_class.today().strftime("%d/%m/%Y")


def generate_quote_pdf(
    devis: Devis,
    document_type: str = "devis",
    with_tva: bool = True,
    document_date: Optional[str] = None,
) -> bytes:
    """Génère le PDF et retourne les bytes."""
    try:
        from fpdf import FPDF
    except ImportError:
        raise RuntimeError("fpdf2 n'est pas installé. Lancez : pip install fpdf2")

    doc_label = "FACTURE" if document_type == "facture" else "DEVIS"
    doc_date  = _fmt_date(document_date)

    pdf = FPDF(format="A4")
    pdf.core_fonts_encoding = "cp1252"  # permet € et • avec les polices Helvetica/Times
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    W = 180.0  # largeur utile (210 - 2×15 mm)

    # ── EN-TÊTE ──────────────────────────────────────────────────────
    y0       = 15.0
    LOGO_W   = 38.0   # largeur fixe réservée au logo (mm) — hauteur auto proportionnelle
    LOGO_GAP = 4.0    # espace horizontal logo → texte
    LOGO_RES = 24.0   # hauteur verticale minimale réservée pour le bloc logo

    # Avec logo : texte décalé à droite ; sans logo : texte à x=15
    has_logo = False
    text_x   = 15.0
    text_w   = 110.0  # largeur colonne texte artisan (jusqu'à x=125)

    if devis.artisan.logo_base64:
        try:
            logo_data = base64.b64decode(devis.artisan.logo_base64)
            pdf.image(BytesIO(logo_data), x=15, y=y0, w=LOGO_W)
            has_logo = True
            text_x = 15 + LOGO_W + LOGO_GAP   # décalage : x = 57 mm
            text_w = 110 - LOGO_W - LOGO_GAP  # 68 mm disponibles pour le texte
        except Exception:
            pass  # logo invalide → layout sans logo

    left_y = y0  # curseur vertical colonne texte

    # Nom artisan
    pdf.set_xy(text_x, left_y)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*BLUE)
    pdf.cell(text_w, 7, _safe(devis.artisan.nom or "Votre Entreprise"), border=0)
    left_y += 8

    # Infos artisan (police 8 grise)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*GRAY)

    if devis.artisan.siret:
        pdf.set_xy(text_x, left_y)
        pdf.cell(text_w, 4, _safe(f"SIRET : {devis.artisan.siret}"), border=0)
        left_y += 4

    if devis.artisan.adresse:
        pdf.set_xy(text_x, left_y)
        pdf.cell(text_w, 4, _safe(f"Adresse : {devis.artisan.adresse}"), border=0)
        left_y += 4

    ville_line = _safe(" ".join(filter(None, [devis.artisan.code_postal, devis.artisan.ville])))
    if ville_line:
        pdf.set_xy(text_x, left_y)
        pdf.cell(text_w, 4, ville_line, border=0)
        left_y += 4

    if devis.artisan.telephone:
        pdf.set_xy(text_x, left_y)
        pdf.cell(text_w, 4, _safe(f"Tél : {devis.artisan.telephone}"), border=0)
        left_y += 4

    if devis.artisan.email:
        pdf.set_xy(text_x, left_y)
        pdf.cell(text_w, 4, _safe(f"Mail : {devis.artisan.email}"), border=0)
        left_y += 4

    if devis.artisan.site_web:
        pdf.set_xy(text_x, left_y)
        pdf.cell(text_w, 4, _safe(f"Web : {devis.artisan.site_web}"), border=0)
        left_y += 4

    # Garantir que left_y dépasse le bas du logo si logo présent
    if has_logo:
        left_y = max(left_y, y0 + LOGO_RES)

    # Label doc — droite
    pdf.set_xy(125, y0)
    pdf.set_font("Helvetica", "B", 26)
    pdf.set_text_color(*BLUE)
    pdf.cell(70, 10, doc_label, border=0, align="R")

    # Date — droite
    pdf.set_xy(125, y0 + 11)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*GRAY)
    pdf.cell(70, 4, f"Date : {doc_date}", border=0, align="R")

    if document_type == "devis":
        pdf.set_xy(125, y0 + 16)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*GRAY)
        pdf.cell(70, 4, "Valable 30 jours", border=0, align="R")

    if devis.numero_document:
        num_label = "N° Facture" if document_type == "facture" else "N° Devis"
        pdf.set_xy(125, y0 + 21)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*BLUE)
        pdf.cell(70, 4, _safe(f"{num_label} : {devis.numero_document}"), border=0, align="R")

    pdf.set_y(max(left_y + 2, y0 + 24))

    # ── SÉPARATEUR ───────────────────────────────────────────────────
    pdf.set_draw_color(*BORDER)
    pdf.set_line_width(0.2)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(4)

    # ── ENCADRÉS CLIENT + CHANTIER ───────────────────────────────────
    y_box = pdf.get_y()
    bw = 87.0

    # Hauteur dynamique : s'adapte à la longueur de la description chantier
    pdf.set_font("Helvetica", "", 8)
    n_chantier = len(pdf.multi_cell(bw - 6, 4, _safe(devis.chantier.description), dry_run=True, output="LINES"))
    bh = max(26.0, 11 + n_chantier * 4)

    # Client
    pdf.set_fill_color(*LIGHT_GRAY)
    pdf.set_draw_color(*LIGHT_GRAY)
    pdf.rect(15, y_box, bw, bh, "F")
    pdf.set_draw_color(*BLUE)
    pdf.set_line_width(1.2)
    pdf.line(15, y_box, 15, y_box + bh)
    pdf.set_line_width(0.2)

    pdf.set_xy(18, y_box + 2)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(*BLUE)
    pdf.cell(bw - 3, 4, "CLIENT")

    pdf.set_xy(18, y_box + 7)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*BLACK)
    pdf.cell(bw - 3, 5, _safe(devis.client.nom or "—"))

    if devis.client.adresse:
        pdf.set_xy(18, y_box + 13)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*GRAY)
        pdf.multi_cell(bw - 3, 4, _safe(devis.client.adresse))

    # Chantier
    x2 = 15 + bw + 6
    pdf.set_fill_color(*AMBER_BG)
    pdf.set_draw_color(*AMBER_BG)
    pdf.rect(x2, y_box, bw, bh, "F")
    pdf.set_draw_color(*AMBER)
    pdf.set_line_width(1.2)
    pdf.line(x2, y_box, x2, y_box + bh)
    pdf.set_line_width(0.2)

    pdf.set_xy(x2 + 3, y_box + 2)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(*AMBER)
    pdf.cell(bw - 3, 4, "CHANTIER")

    pdf.set_xy(x2 + 3, y_box + 7)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*BLACK)
    pdf.multi_cell(bw - 3, 4, _safe(devis.chantier.description))

    pdf.set_y(y_box + bh + 6)

    # ── TABLEAU ───────────────────────────────────────────────────────
    if with_tva:
        col_w = [36, 62, 16, 22, 16, 28]   # T=180 : +espace Description, -Prestation/-Qté
        col_h = ["Prestation", "Description", "Qté", "PU HT", "TVA", "Total HT"]
        col_a = ["L", "L", "C", "R", "C", "R"]
    else:
        col_w = [42, 72, 16, 24, 26]        # T=180 : Description large, Qté réduite
        col_h = ["Prestation", "Description", "Qté", "PU HT", "Total HT"]
        col_a = ["L", "L", "C", "R", "R"]

    # Positions X cumulatives des colonnes
    x_cols = [15]
    for cw in col_w[:-1]:
        x_cols.append(x_cols[-1] + cw)

    def _draw_table_header() -> None:
        pdf.set_fill_color(*BLUE)
        pdf.set_text_color(*WHITE)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_draw_color(*BLUE)
        for h, w, a in zip(col_h, col_w, col_a):
            pdf.cell(w, 8, h, border=0, align=a, fill=True)
        pdf.ln()

    _draw_table_header()

    LINE_H    = 5.5    # hauteur d'une ligne de texte (mm)
    PAGE_BOT  = pdf.h - 20  # limite basse (marge de sécurité avant bas de page)

    # Désactivation auto_page_break : on gère les sauts manuellement pour éviter
    # qu'un multi_cell en milieu de ligne déclenche un saut et déplace les colonnes
    # suivantes sur la mauvaise page (y_start deviendrait obsolète).
    pdf.set_auto_page_break(False)

    # ── Groupement par LOT ──────────────────────────────────────────
    has_lots = any(l.lot for l in devis.lignes)
    lot_groups: dict = {}
    for ligne in devis.lignes:
        key = ligne.lot or ""
        if key not in lot_groups:
            lot_groups[key] = []
        lot_groups[key].append(ligne)

    pdf.set_draw_color(*BORDER)
    row_i = 0

    for lot_name, lot_lignes in lot_groups.items():

        # En-tête de LOT
        if has_lots and lot_name:
            if pdf.get_y() + 7 > PAGE_BOT:
                pdf.add_page()
                _draw_table_header()
            y_lot = pdf.get_y()
            pdf.set_fill_color(71, 85, 105)   # slate-600
            pdf.rect(15, y_lot, W, 7, "F")
            pdf.set_xy(17, y_lot + 1.5)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*WHITE)
            pdf.cell(W - 2, 4, _safe(lot_name), border=0, align="L", fill=False)
            pdf.set_y(y_lot + 7)

        # Lignes du lot
        for ligne in lot_lignes:
            montant_ht = round(ligne.quantite * ligne.prix_unitaire_ht, 2)
            pdf.set_text_color(*BLACK)
            pdf.set_font("Helvetica", "", 8)

            if with_tva:
                vals = [
                    _safe(ligne.poste),
                    _safe(ligne.description),
                    _safe(f"{ligne.quantite} {ligne.unite}"),
                    _fmt_money(ligne.prix_unitaire_ht),
                    f"{ligne.tva_taux:.0f}%",
                    _fmt_money(montant_ht),
                ]
            else:
                vals = [
                    _safe(ligne.poste),
                    _safe(ligne.description),
                    _safe(f"{ligne.quantite} {ligne.unite}"),
                    _fmt_money(ligne.prix_unitaire_ht),
                    _fmt_money(montant_ht),
                ]

            # Pré-calcul de la hauteur de la ligne (dry_run → pas de rendu)
            n_poste = len(pdf.multi_cell(col_w[0] - 2, LINE_H, vals[0], dry_run=True, output="LINES"))
            n_desc  = len(pdf.multi_cell(col_w[1] - 2, LINE_H, vals[1], dry_run=True, output="LINES"))
            row_h   = max(n_poste, n_desc, 1) * LINE_H
            row_h   = max(row_h, 7)

            # Saut de page manuel si la ligne ne tient pas sur la page courante
            if pdf.get_y() + row_h > PAGE_BOT:
                pdf.add_page()
                _draw_table_header()

            y_start = pdf.get_y()
            is_fill = row_i % 2 == 1

            if is_fill:
                pdf.set_fill_color(*LIGHT_GRAY)
                pdf.rect(15, y_start, W, row_h, "F")

            for i, (v, w, a, x) in enumerate(zip(vals, col_w, col_a, x_cols)):
                pdf.set_xy(x, y_start)
                if i < 2:
                    pdf.multi_cell(w, LINE_H, v, border=0, align=a, fill=False)
                else:
                    y_v = y_start + (row_h - LINE_H) / 2
                    pdf.set_xy(x, y_v)
                    pdf.cell(w, LINE_H, v, border=0, align=a, fill=False)

            pdf.set_draw_color(*BORDER)
            pdf.set_line_width(0.2)
            pdf.line(15, y_start + row_h, 195, y_start + row_h)
            pdf.set_y(y_start + row_h)
            row_i += 1

        # Sous-total du LOT (affiché seulement s'il y a plusieurs LOTs)
        if has_lots and len(lot_groups) > 1:
            lot_ht = round(sum(l.quantite * l.prix_unitaire_ht for l in lot_lignes), 2)
            sub_label = _safe(f"Sous-total {lot_name}" if lot_name else "Sous-total")
            if pdf.get_y() + 6 > PAGE_BOT:
                pdf.add_page()
                _draw_table_header()
            y_sub = pdf.get_y()
            pdf.set_fill_color(*LIGHT_GRAY)
            pdf.rect(15, y_sub, W, 6, "F")
            pdf.set_xy(15, y_sub)
            pdf.set_font("Helvetica", "BI", 7.5)
            pdf.set_text_color(*GRAY)
            pdf.cell(sum(col_w[:-1]), 6, sub_label, border=0, align="R")
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*BLACK)
            pdf.cell(col_w[-1], 6, _fmt_money(lot_ht), border=0, align="R")
            pdf.set_draw_color(71, 85, 105)
            pdf.set_line_width(0.3)
            pdf.line(15, y_sub + 6, 195, y_sub + 6)
            pdf.set_line_width(0.2)
            pdf.set_draw_color(*BORDER)
            pdf.set_y(y_sub + 6)

    # Réactivation auto_page_break pour totaux / notes / mentions légales
    pdf.set_auto_page_break(True, margin=15)
    pdf.ln(5)

    # ── TOTAUX ────────────────────────────────────────────────────────
    tot_x = 195 - 65
    totaux = devis.totaux
    has_remise  = (totaux.remise_ht or 0) > 0
    has_acompte = (devis.acompte or 0) > 0

    pdf.set_draw_color(*BORDER)
    pdf.set_fill_color(*LIGHT_GRAY)

    def _tot_row(label: str, value_str: str, first: bool = False) -> None:
        border = "TB" if first else "B"
        pdf.set_xy(tot_x, pdf.get_y())
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*GRAY)
        pdf.cell(35, 7, label, border=border, fill=True)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*BLACK)
        pdf.cell(30, 7, value_str, border=border, align="R", fill=True)
        pdf.ln()

    def _tot_row_blue(label: str, value_str: str) -> None:
        pdf.set_xy(tot_x, pdf.get_y())
        pdf.set_fill_color(*BLUE)
        pdf.set_text_color(*WHITE)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(35, 9, label, border=0, fill=True)
        pdf.cell(30, 9, value_str, border=0, align="R", fill=True)
        pdf.ln()
        pdf.set_fill_color(*LIGHT_GRAY)

    if with_tva:
        ht_label = "Total HT brut" if has_remise else "Total HT"
        _tot_row(ht_label, _fmt_money(totaux.total_ht), first=True)
        if has_remise:
            ht_net = totaux.total_ht_net if totaux.total_ht_net else (totaux.total_ht - (totaux.remise_ht or 0))
            _tot_row("Remise", "- " + _fmt_money(totaux.remise_ht or 0))
            _tot_row("Total HT net", _fmt_money(ht_net))
        _tot_row("Total TVA", _fmt_money(totaux.total_tva))
        _tot_row_blue("TOTAL TTC", _fmt_money(totaux.total_ttc))
        if has_acompte:
            pdf.ln(2)
            _tot_row(_safe("Acompte vers\xe9"), "- " + _fmt_money(devis.acompte or 0), first=True)
            net = totaux.net_a_payer if totaux.net_a_payer else max(0, totaux.total_ttc - (devis.acompte or 0))
            _tot_row_blue("NET A PAYER", _fmt_money(net))
    else:
        if has_remise:
            ht_net = totaux.total_ht_net if totaux.total_ht_net else (totaux.total_ht - (totaux.remise_ht or 0))
            _tot_row("Total HT brut", _fmt_money(totaux.total_ht), first=True)
            _tot_row("Remise", "- " + _fmt_money(totaux.remise_ht or 0))
            _tot_row_blue("TOTAL HT NET", _fmt_money(ht_net))
        else:
            _tot_row_blue("TOTAL HT", _fmt_money(totaux.total_ht))
        if has_acompte:
            pdf.ln(2)
            ht_base = totaux.total_ht_net if totaux.total_ht_net else totaux.total_ht
            _tot_row(_safe("Acompte vers\xe9"), "- " + _fmt_money(devis.acompte or 0), first=True)
            net = totaux.net_a_payer if totaux.net_a_payer else max(0, ht_base - (devis.acompte or 0))
            _tot_row_blue("NET A PAYER", _fmt_money(net))

    pdf.ln(8)

    # ── MENTIONS LÉGALES ──────────────────────────────────────────────
    pdf.set_draw_color(*BORDER)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(3)

    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*GRAY)
    for m in devis.mentions_legales:
        pdf.cell(0, 4, _safe(f"• {m}"), ln=True)

    if not with_tva:
        pdf.set_font("Helvetica", "B", 7)
        pdf.cell(0, 4, "• TVA non applicable, art. 293 B du CGI", ln=True)

    # ── RIB / COORDONNÉES BANCAIRES ──────────────────────────────────
    if devis.artisan.iban or devis.artisan.bic:
        pdf.ln(4)
        pdf.set_draw_color(*BORDER)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*BLUE)
        pdf.cell(0, 4, "Coordonnées bancaires", ln=True)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*BLACK)
        if devis.artisan.iban:
            pdf.cell(0, 4, _safe(f"IBAN : {devis.artisan.iban}"), ln=True)
        if devis.artisan.bic:
            pdf.cell(0, 4, _safe(f"BIC/SWIFT : {devis.artisan.bic}"), ln=True)

    # ── ZONE DE SIGNATURE ────────────────────────────────────────────
    pdf.ln(10)
    sig_y = pdf.get_y()
    if sig_y + 30 > pdf.h - 15:
        pdf.add_page()
        sig_y = 20.0
    pdf.set_y(sig_y)

    sig_w  = 82.0
    sig_h  = 28.0
    sig_x2 = 15 + sig_w + 16   # x du bloc droit

    pdf.set_draw_color(*BORDER)
    pdf.set_line_width(0.4)

    # Bloc gauche — bon pour accord
    pdf.rect(15, sig_y, sig_w, sig_h)
    pdf.set_xy(17, sig_y + 2)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*BLUE)
    pdf.cell(sig_w - 4, 5, "Bon pour accord", border=0)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(*GRAY)
    pdf.set_xy(17, sig_y + 9)
    pdf.cell(sig_w - 4, 4, _safe("Fait à : _________________________________"), border=0)
    pdf.set_xy(17, sig_y + 14)
    pdf.cell(sig_w - 4, 4, "Le : _______ / _______ / ___________", border=0)

    # Bloc droit — signature
    pdf.rect(sig_x2, sig_y, sig_w, sig_h)
    pdf.set_xy(sig_x2 + 2, sig_y + 2)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*BLUE)
    pdf.cell(sig_w - 4, 5, "Signature du client", border=0)

    return bytes(pdf.output())
