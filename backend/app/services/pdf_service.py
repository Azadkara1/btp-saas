"""
Génération de PDF pour les devis/factures.
Utilise fpdf2 (pur Python, pas de dépendances système).

Deux modèles visuels :
  - "moderne" (défaut) : bandeau vert forêt #14532D, texte blanc, lots fond #E3EDE6
  - "pro"             : fond blanc, texte anthracite #1F2937, Times, accents #3B5573
"""
import base64
from datetime import date as date_class
from io import BytesIO
from typing import Optional
from app.models.quote import Devis

# ── Palettes communes ────────────────────────────────────────────
WHITE      = (255, 255, 255)
BLACK      = (30,   30,  30)
BORDER     = (229, 231, 235)
LIGHT_GRAY = (248, 249, 250)

# Moderne
M_GREEN    = (20,  83,  45)    # #14532D — en-tête & NET À PAYER
M_LOT_BG   = (227, 237, 230)   # #E3EDE6 — fond bandeaux lot
M_LOT_TEXT = (20,  83,  45)    # #14532D
AMBER      = (245, 158,  11)
AMBER_BG   = (255, 248, 225)

# Pro
P_ANTHRACITE = (31,  41,  55)  # #1F2937
P_STEEL      = (59,  85, 115)  # #3B5573
P_GRAY       = (90,  99,  93)  # #5A635D


def _safe(text: str) -> str:
    """Supprime les caractères hors cp1252 incompatibles avec Helvetica/Times."""
    if not text:
        return ""
    return text.encode("cp1252", errors="ignore").decode("cp1252")


def _fmt_money(amount: float) -> str:
    """Format monétaire français : '1 234,56 EUR' compatible cp1252/Helvetica."""
    s = f"{amount:.2f}"
    int_part, dec_part = s.split(".")
    n, groups = len(int_part), []
    while n > 3:
        groups.insert(0, int_part[n - 3:n])
        n -= 3
    groups.insert(0, int_part[:n])
    return " ".join(groups) + "," + dec_part + " EUR"


def _fmt_date(iso_date: Optional[str]) -> str:
    if iso_date:
        try:
            y, m, d = iso_date.split("-")
            return f"{d}/{m}/{y}"
        except Exception:
            pass
    return date_class.today().strftime("%d/%m/%Y")


def _logo_dimensions(logo_data: bytes) -> tuple[float, float]:
    """Calcule la largeur et hauteur du logo (mm) en respectant l'aspect ratio."""
    W_MAX, H_MAX = 38.0, 28.0
    try:
        from PIL import Image as PILImage
        img = PILImage.open(BytesIO(logo_data))
        iw, ih = img.size
        aspect = iw / ih
        if aspect >= W_MAX / H_MAX:
            return W_MAX, W_MAX / aspect
        else:
            return H_MAX * aspect, H_MAX
    except Exception:
        return W_MAX, 24.0   # fallback si PIL indisponible


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

    modele    = (devis.modele or "moderne").lower()
    is_pro    = (modele == "pro")
    FONT      = "Times" if is_pro else "Helvetica"
    doc_label = "FACTURE" if document_type == "facture" else "DEVIS"
    doc_date  = _fmt_date(document_date)

    pdf = FPDF(format="A4")
    pdf.core_fonts_encoding = "cp1252"
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    W = 180.0  # largeur utile (210 - 2×15 mm)

    # ── EN-TÊTE ──────────────────────────────────────────────────────
    y0     = 15.0
    LOGO_GAP = 4.0
    LABEL_X  = 125.0   # x de départ du bloc DEVIS / date (70mm de large jusqu'à 195)

    # Lecture logo
    has_logo   = False
    logo_w     = 0.0
    logo_h     = 0.0
    logo_bytes = None

    if devis.artisan.logo_base64:
        try:
            logo_bytes = base64.b64decode(devis.artisan.logo_base64)
            logo_w, logo_h = _logo_dimensions(logo_bytes)
            has_logo = True
        except Exception:
            has_logo = False

    # Calcul de la hauteur header (pour le bandeau moderne)
    artisan_info_lines = [
        devis.artisan.siret,
        devis.artisan.adresse,
        " ".join(filter(None, [devis.artisan.code_postal, devis.artisan.ville])) or None,
        devis.artisan.telephone,
        devis.artisan.email,
        devis.artisan.site_web,
    ]
    n_info = sum(1 for x in artisan_info_lines if x)
    text_block_h = 8 + n_info * 4 + 4   # nom (8mm) + lignes infos + marge
    header_h = max(text_block_h, 32.0)
    if has_logo:
        header_h = max(header_h, logo_h + 4)

    # ── Bandeau moderne (fond vert plein) ────────────────────────────
    if not is_pro:
        pdf.set_fill_color(*M_GREEN)
        pdf.rect(15, y0, W, header_h, "F")

    # Placement du logo
    disp_w = logo_w  # largeur affichée — peut être réduite en mode moderne
    if has_logo and logo_bytes:
        disp_h = logo_h
        # Moderne : borner la hauteur à 22 mm pour que la pastille (+ 4 mm padding) tienne dans l'en-tête
        if not is_pro and disp_h > 22.0:
            disp_w = logo_w * 22.0 / logo_h
            disp_h = 22.0
        logo_y = y0 + (header_h - disp_h) / 2
        if not is_pro:
            # Cartouche blanc derrière le logo (padding 2 mm)
            pad = 2.0
            pdf.set_fill_color(*WHITE)
            pdf.rect(15 - pad, logo_y - pad, disp_w + 2 * pad, disp_h + 2 * pad, "F")
        pdf.image(BytesIO(logo_bytes), x=15, y=logo_y, w=disp_w, h=disp_h)

    text_x = (15 + disp_w + LOGO_GAP) if has_logo else 15.0
    text_w = LABEL_X - text_x  # jusqu'au bloc DEVIS

    left_y = y0 + 4  # marge top dans le bandeau

    # Nom artisan
    pdf.set_xy(text_x, left_y)
    pdf.set_font(FONT, "B", 13)
    if is_pro:
        pdf.set_text_color(*P_ANTHRACITE)
    else:
        pdf.set_text_color(*WHITE)
    pdf.cell(text_w, 7, _safe(devis.artisan.nom or "Votre Entreprise"), border=0)
    left_y += 8

    # Infos artisan
    pdf.set_font(FONT, "", 8)
    if is_pro:
        pdf.set_text_color(*P_GRAY)
    else:
        pdf.set_text_color(200, 230, 210)  # blanc cassé sur vert

    info_pairs = [
        (f"SIRET : {devis.artisan.siret}",        devis.artisan.siret),
        (f"Adresse : {devis.artisan.adresse}",    devis.artisan.adresse),
        (" ".join(filter(None, [devis.artisan.code_postal, devis.artisan.ville])),
         devis.artisan.code_postal or devis.artisan.ville),
        (f"Tel : {devis.artisan.telephone}",      devis.artisan.telephone),
        (f"Mail : {devis.artisan.email}",         devis.artisan.email),
        (f"Web : {devis.artisan.site_web}",       devis.artisan.site_web),
    ]
    for line_text, condition in info_pairs:
        if condition:
            pdf.set_xy(text_x, left_y)
            pdf.cell(text_w, 4, _safe(line_text), border=0)
            left_y += 4

    # Label DEVIS / FACTURE — droite
    pdf.set_xy(LABEL_X, y0 + 2)
    pdf.set_font(FONT, "B", 26)
    if is_pro:
        pdf.set_text_color(*P_ANTHRACITE)
    else:
        pdf.set_text_color(*WHITE)
    pdf.cell(70, 10, doc_label, border=0, align="R")

    # Date, validité, numéro
    pdf.set_font(FONT, "", 8)
    if is_pro:
        pdf.set_text_color(*P_GRAY)
    else:
        pdf.set_text_color(200, 230, 210)

    label_y = y0 + 14
    pdf.set_xy(LABEL_X, label_y)
    pdf.cell(70, 4, f"Date : {doc_date}", border=0, align="R")
    label_y += 4

    if document_type == "devis":
        validite = devis.validite_jours or 30
        pdf.set_xy(LABEL_X, label_y)
        pdf.cell(70, 4, _safe(f"Valable {validite} jours"), border=0, align="R")
        label_y += 4

    if devis.numero_document:
        num_label = "N Facture" if document_type == "facture" else "N Devis"
        pdf.set_xy(LABEL_X, label_y)
        pdf.set_font(FONT, "B", 8)
        if is_pro:
            pdf.set_text_color(*P_STEEL)
        else:
            pdf.set_text_color(*WHITE)
        pdf.cell(70, 4, _safe(f"{num_label} : {devis.numero_document}"), border=0, align="R")

    # Fin du bandeau
    header_bottom = y0 + header_h + 3

    if is_pro:
        # Filet épais anthracite sous l'en-tête
        pdf.set_draw_color(*P_ANTHRACITE)
        pdf.set_line_width(0.7)
        pdf.line(15, y0 + header_h, 195, y0 + header_h)
        pdf.set_line_width(0.2)
        pdf.set_draw_color(*BORDER)
    else:
        # Pas de filet séparateur pour le modèle moderne (le bandeau suffit)
        pass

    pdf.set_y(header_bottom)

    # ── ENCADRÉS CLIENT + CHANTIER ───────────────────────────────────
    pdf.ln(2)
    y_box = pdf.get_y()
    bw = 87.0

    pdf.set_font(FONT, "", 8)
    n_chantier = len(pdf.multi_cell(bw - 3, 4, _safe(devis.chantier.description),
                                    dry_run=True, output="LINES"))
    # Hauteur client : header+nom (13mm) + adresse + CP/ville + 2mm marge
    n_client_addr = len(pdf.multi_cell(bw - 3, 4, _safe(devis.client.adresse or ""),
                                       dry_run=True, output="LINES")) if devis.client.adresse else 0
    n_client_cpv  = 1 if (devis.client.code_postal or devis.client.ville) else 0
    client_bh     = 13 + n_client_addr * 4 + n_client_cpv * 4 + 2
    bh = min(max(26.0, 11 + n_chantier * 4, client_bh), 55.0)  # cap à 55 mm

    ACCENT = M_GREEN if not is_pro else P_STEEL

    # Encadré Client
    pdf.set_fill_color(*LIGHT_GRAY)
    pdf.set_draw_color(*LIGHT_GRAY)
    pdf.rect(15, y_box, bw, bh, "F")
    pdf.set_draw_color(*ACCENT)
    pdf.set_line_width(1.2)
    pdf.line(15, y_box, 15, y_box + bh)
    pdf.set_line_width(0.2)

    pdf.set_xy(18, y_box + 2)
    pdf.set_font(FONT, "B", 7)
    pdf.set_text_color(*ACCENT)
    pdf.cell(bw - 3, 4, "CLIENT")

    pdf.set_xy(18, y_box + 7)
    pdf.set_font(FONT, "B", 10)
    pdf.set_text_color(*BLACK)
    pdf.cell(bw - 3, 5, _safe(devis.client.nom or "—"))

    if devis.client.adresse:
        pdf.set_xy(18, y_box + 13)
        pdf.set_font(FONT, "", 8)
        pdf.set_text_color(*P_GRAY if is_pro else (100, 116, 139))
        pdf.multi_cell(bw - 3, 4, _safe(devis.client.adresse))

    cp_ville_client = " ".join(filter(None, [devis.client.code_postal, devis.client.ville]))
    if cp_ville_client:
        y_cpv = pdf.get_y() if devis.client.adresse else y_box + 13
        pdf.set_xy(18, y_cpv)
        pdf.set_font(FONT, "", 8)
        pdf.set_text_color(*P_GRAY if is_pro else (100, 116, 139))
        pdf.cell(bw - 3, 4, _safe(cp_ville_client))

    # Encadré Chantier
    x2 = 15 + bw + 6
    pdf.set_fill_color(*AMBER_BG)
    pdf.set_draw_color(*AMBER_BG)
    pdf.rect(x2, y_box, bw, bh, "F")
    pdf.set_draw_color(*AMBER)
    pdf.set_line_width(1.2)
    pdf.line(x2, y_box, x2, y_box + bh)
    pdf.set_line_width(0.2)

    pdf.set_xy(x2 + 3, y_box + 2)
    pdf.set_font(FONT, "B", 7)
    pdf.set_text_color(*AMBER)
    pdf.cell(bw - 3, 4, "CHANTIER")

    pdf.set_xy(x2 + 3, y_box + 7)
    pdf.set_font(FONT, "", 8)
    pdf.set_text_color(*BLACK)
    pdf.multi_cell(bw - 3, 4, _safe((devis.chantier.description or "")[:500]))

    pdf.set_y(y_box + bh + 6)

    # ── TABLEAU ───────────────────────────────────────────────────────
    # Colonnes : Prestation | Description | Qté | Unité | PU HT | [TVA] | Total HT
    if with_tva:
        col_w = [34, 54, 12, 13, 22, 14, 31]
        col_h = ["Prestation", "Description", "Qte", "Unite", "PU HT", "TVA", "Total HT"]
        col_a = ["L", "L", "C", "C", "R", "C", "R"]
    else:
        col_w = [36, 64, 12, 14, 25, 29]
        col_h = ["Prestation", "Description", "Qte", "Unite", "PU HT", "Total HT"]
        col_a = ["L", "L", "C", "C", "R", "R"]

    x_cols = [15]
    for cw in col_w[:-1]:
        x_cols.append(x_cols[-1] + cw)

    def _draw_table_header() -> None:
        if is_pro:
            pdf.set_fill_color(*P_STEEL)
        else:
            pdf.set_fill_color(*M_GREEN)
        pdf.set_text_color(*WHITE)
        pdf.set_font(FONT, "B", 8)
        pdf.set_draw_color(*BORDER)
        for h, w, a in zip(col_h, col_w, col_a):
            pdf.cell(w, 8, _safe(h), border=0, align=a, fill=True)
        pdf.ln()

    _draw_table_header()

    LINE_H   = 5.5
    PAGE_BOT = pdf.h - 20

    pdf.set_auto_page_break(False)

    has_lots  = any(l.lot for l in devis.lignes)
    lot_groups: dict = {}
    for ligne in devis.lignes:
        key = ligne.lot or ""
        if key not in lot_groups:
            lot_groups[key] = []
        lot_groups[key].append(ligne)

    pdf.set_draw_color(*BORDER)
    row_i  = 0
    n_lots = len(lot_groups)
    show_sub = has_lots and n_lots > 1

    def _row_height(poste_txt: str, desc_txt: str) -> float:
        """Hauteur réelle d'une ligne (dry_run multi_cell)."""
        np_ = len(pdf.multi_cell(col_w[0], LINE_H, poste_txt, dry_run=True, output="LINES"))
        nd_ = len(pdf.multi_cell(col_w[1], LINE_H, desc_txt,  dry_run=True, output="LINES"))
        return max(max(np_, nd_, 1) * LINE_H, 7.0)

    for lot_name, lot_lignes in lot_groups.items():
        n_lot = len(lot_lignes)

        # ── Bandeau de LOT ───────────────────────────────────────────────
        # Règle : _draw_table_header() uniquement avant une LIGNE DE PRESTATION,
        # jamais avant un sous-total isolé.
        # Bloc insécable lot à 1 ligne : bandeau (7) + ligne + sous-total (6).
        if has_lots and lot_name:
            first_h = _row_height(_safe(lot_lignes[0].poste), _safe(lot_lignes[0].description))
            sub_margin = 6 if (n_lot == 1 and show_sub) else 0
            if pdf.get_y() + 7 + first_h + sub_margin > PAGE_BOT:
                pdf.add_page()
                _draw_table_header()  # en-tête avant le bandeau → ordre correct
            y_lot = pdf.get_y()

            if is_pro:
                pdf.set_xy(15, y_lot + 1)
                pdf.set_font(FONT, "B", 8.5)
                pdf.set_text_color(*P_STEEL)
                pdf.cell(W, 5, _safe(f"  {lot_name}"), border=0, align="L")
                pdf.set_draw_color(*P_STEEL)
                pdf.set_line_width(0.3)
                pdf.line(15, y_lot + 7, 195, y_lot + 7)
                pdf.set_line_width(0.2)
                pdf.set_draw_color(*BORDER)
            else:
                pdf.set_fill_color(*M_LOT_BG)
                pdf.rect(15, y_lot, W, 7, "F")
                pdf.set_xy(17, y_lot + 1.5)
                pdf.set_font(FONT, "B", 8)
                pdf.set_text_color(*M_LOT_TEXT)
                pdf.cell(W - 2, 4, _safe(lot_name), border=0, align="L", fill=False)
            pdf.set_y(y_lot + 7)

        # ── Lignes ───────────────────────────────────────────────────────
        for i_ligne, ligne in enumerate(lot_lignes):
            is_last = (i_ligne == n_lot - 1)
            montant_ht = round(ligne.quantite * ligne.prix_unitaire_ht, 2)
            pdf.set_text_color(*BLACK)
            pdf.set_font(FONT, "", 8)

            if with_tva:
                vals = [
                    _safe(ligne.poste), _safe(ligne.description),
                    f"{ligne.quantite:g}", _safe(ligne.unite),
                    _fmt_money(ligne.prix_unitaire_ht), f"{ligne.tva_taux:.0f}%",
                    _fmt_money(montant_ht),
                ]
            else:
                vals = [
                    _safe(ligne.poste), _safe(ligne.description),
                    f"{ligne.quantite:g}", _safe(ligne.unite),
                    _fmt_money(ligne.prix_unitaire_ht), _fmt_money(montant_ht),
                ]

            row_h = _row_height(vals[0], vals[1])

            # Bloc insécable dernière ligne + sous-total.
            # _draw_table_header() : une ligne de prestation suit → correct.
            sub_h = 6 if (is_last and show_sub) else 0
            if pdf.get_y() + row_h + sub_h > PAGE_BOT:
                pdf.add_page()
                _draw_table_header()

            y_start = pdf.get_y()
            if row_i % 2 == 1:
                pdf.set_fill_color(*LIGHT_GRAY)
                pdf.rect(15, y_start, W, row_h, "F")

            for i, (v, w, a, x) in enumerate(zip(vals, col_w, col_a, x_cols)):
                pdf.set_xy(x, y_start)
                if i < 2:
                    pdf.multi_cell(w, LINE_H, v, border=0, align=a, fill=False)
                else:
                    pdf.set_xy(x, y_start + (row_h - LINE_H) / 2)
                    pdf.cell(w, LINE_H, v, border=0, align=a, fill=False)

            pdf.set_draw_color(*BORDER)
            pdf.set_line_width(0.2)
            pdf.line(15, y_start + row_h, 195, y_start + row_h)
            pdf.set_y(y_start + row_h)
            row_i += 1

        # ── Sous-total ───────────────────────────────────────────────────
        # Jamais de _draw_table_header() ici : aucune ligne de prestation ne suit.
        if show_sub:
            lot_ht    = round(sum(l.quantite * l.prix_unitaire_ht for l in lot_lignes), 2)
            sub_label = _safe(f"Sous-total {lot_name}" if lot_name else "Sous-total")
            if pdf.get_y() + 6 > PAGE_BOT:
                pdf.add_page()
            y_sub = pdf.get_y()
            pdf.set_fill_color(*LIGHT_GRAY)
            pdf.rect(15, y_sub, W, 6, "F")
            pdf.set_xy(15, y_sub)
            pdf.set_font(FONT, "BI" if not is_pro else "I", 7.5)
            pdf.set_text_color(*P_GRAY if is_pro else (100, 116, 139))
            pdf.cell(sum(col_w[:-1]), 6, sub_label, border=0, align="R")
            pdf.set_font(FONT, "B", 8)
            pdf.set_text_color(*BLACK)
            pdf.cell(col_w[-1], 6, _fmt_money(lot_ht), border=0, align="R")
            pdf.set_draw_color(71, 85, 105)
            pdf.set_line_width(0.3)
            pdf.line(15, y_sub + 6, 195, y_sub + 6)
            pdf.set_line_width(0.2)
            pdf.set_draw_color(*BORDER)
            pdf.set_y(y_sub + 6)

    pdf.set_auto_page_break(True, margin=15)
    pdf.ln(5)

    # ── TOTAUX ────────────────────────────────────────────────────────
    tot_x   = 195 - 65
    totaux  = devis.totaux
    has_remise  = (totaux.remise_ht or 0) > 0
    has_acompte = (devis.acompte or 0) > 0

    pdf.set_fill_color(*LIGHT_GRAY)

    def _tot_row(label: str, value_str: str, first: bool = False) -> None:
        border = "TB" if first else "B"
        pdf.set_xy(tot_x, pdf.get_y())
        pdf.set_font(FONT, "", 9)
        pdf.set_text_color(*P_GRAY if is_pro else (100, 116, 139))
        pdf.set_draw_color(*BORDER)
        pdf.cell(35, 7, label, border=border, fill=True)
        pdf.set_font(FONT, "B", 9)
        pdf.set_text_color(*BLACK)
        pdf.cell(30, 7, value_str, border=border, align="R", fill=True)
        pdf.ln()

    def _tot_row_accent(label: str, value_str: str) -> None:
        """Ligne mise en évidence pour TOTAL TTC / NET À PAYER."""
        pdf.set_xy(tot_x, pdf.get_y())
        if is_pro:
            # Pro : filet épais anthracite, texte anthracite gras (pas de fond coloré)
            pdf.set_fill_color(*LIGHT_GRAY)
            pdf.set_font(FONT, "B", 10)
            pdf.set_text_color(*P_ANTHRACITE)
            pdf.set_draw_color(*P_ANTHRACITE)
            pdf.cell(35, 9, label, border="TB", fill=True)
            pdf.cell(30, 9, value_str, border="TB", align="R", fill=True)
            pdf.set_draw_color(*BORDER)
        else:
            pdf.set_fill_color(*M_GREEN)
            pdf.set_text_color(*WHITE)
            pdf.set_font(FONT, "B", 10)
            pdf.cell(35, 9, label, border=0, fill=True)
            pdf.cell(30, 9, value_str, border=0, align="R", fill=True)
            pdf.set_fill_color(*LIGHT_GRAY)
        pdf.ln()

    if with_tva:
        ht_label = "Total HT brut" if has_remise else "Total HT"
        _tot_row(ht_label, _fmt_money(totaux.total_ht), first=True)
        if has_remise:
            ht_net = totaux.total_ht_net if totaux.total_ht_net else (totaux.total_ht - (totaux.remise_ht or 0))
            _tot_row("Remise", "- " + _fmt_money(totaux.remise_ht or 0))
            _tot_row("Total HT net", _fmt_money(ht_net))
        _tot_row("Total TVA", _fmt_money(totaux.total_tva))
        _tot_row_accent("TOTAL TTC", _fmt_money(totaux.total_ttc))
        if has_acompte:
            pdf.ln(2)
            _tot_row(_safe("Acompte vers\xe9"), "- " + _fmt_money(devis.acompte or 0), first=True)
            net = totaux.net_a_payer if totaux.net_a_payer else max(0, totaux.total_ttc - (devis.acompte or 0))
            _tot_row_accent("NET A PAYER", _fmt_money(net))
    else:
        if has_remise:
            ht_net = totaux.total_ht_net if totaux.total_ht_net else (totaux.total_ht - (totaux.remise_ht or 0))
            _tot_row("Total HT brut", _fmt_money(totaux.total_ht), first=True)
            _tot_row("Remise", "- " + _fmt_money(totaux.remise_ht or 0))
            _tot_row_accent("TOTAL HT NET", _fmt_money(ht_net))
        else:
            _tot_row_accent("TOTAL HT", _fmt_money(totaux.total_ht))
        if has_acompte:
            pdf.ln(2)
            ht_base = totaux.total_ht_net if totaux.total_ht_net else totaux.total_ht
            _tot_row(_safe("Acompte vers\xe9"), "- " + _fmt_money(devis.acompte or 0), first=True)
            net = totaux.net_a_payer if totaux.net_a_payer else max(0, ht_base - (devis.acompte or 0))
            _tot_row_accent("NET A PAYER", _fmt_money(net))

    pdf.ln(8)

    # ── MENTIONS LÉGALES ──────────────────────────────────────────────
    pdf.set_draw_color(*BORDER)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(3)

    pdf.set_font(FONT, "", 7)
    pdf.set_text_color(*P_GRAY if is_pro else (100, 116, 139))

    # Construire la liste finale des mentions (filtrer + enrichir selon type)
    validite = devis.validite_jours or 30
    mentions_lower = " ".join(m.lower() for m in devis.mentions_legales)
    final_mentions = []
    for m in devis.mentions_legales:
        ml = m.lower()
        if "valable" in ml and "jours" in ml:
            if document_type == "devis":
                final_mentions.append(f"Devis valable {validite} jours a compter de la date d'emission")
            # omis pour facture
        else:
            final_mentions.append(m)

    if document_type == "devis":
        if not any("valable" in m.lower() for m in final_mentions):
            final_mentions.insert(0, f"Devis valable {validite} jours a compter de la date d'emission")
        if not any("accord" in m.lower() for m in final_mentions):
            final_mentions.append("Signature du client precedee de la mention 'Bon pour accord'")
    else:
        if not any("retard" in m.lower() or "penalite" in m.lower() for m in final_mentions):
            final_mentions.append(
                "Tout retard de paiement entraine des penalites de retard au taux legal en vigueur "
                "majoré de 10 points + indemnite forfaitaire de 40 EUR pour frais de recouvrement"
            )

    if devis.conditions_paiement:
        final_mentions.append(f"Conditions de paiement : {devis.conditions_paiement}")

    for m in final_mentions:
        pdf.cell(0, 4, _safe(f"* {m}"), ln=True)

    if not with_tva:
        pdf.set_font(FONT, "B", 7)
        pdf.cell(0, 4, "* TVA non applicable, art. 293 B du CGI", ln=True)

    # ── RIB / COORDONNÉES BANCAIRES ──────────────────────────────────
    if devis.artisan.iban or devis.artisan.bic:
        pdf.ln(4)
        pdf.set_draw_color(*BORDER)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(3)
        pdf.set_font(FONT, "B", 8)
        pdf.set_text_color(*ACCENT)
        pdf.cell(0, 4, "Coordonnees bancaires", ln=True)
        pdf.set_font(FONT, "", 8)
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
    sig_x2 = 15 + sig_w + 16

    pdf.set_draw_color(*BORDER)
    pdf.set_line_width(0.4)

    pdf.rect(15, sig_y, sig_w, sig_h)
    pdf.set_xy(17, sig_y + 2)
    pdf.set_font(FONT, "B", 8)
    pdf.set_text_color(*ACCENT)
    pdf.cell(sig_w - 4, 5, "Bon pour accord", border=0)
    pdf.set_font(FONT, "", 7.5)
    pdf.set_text_color(*P_GRAY if is_pro else (100, 116, 139))
    pdf.set_xy(17, sig_y + 9)
    pdf.cell(sig_w - 4, 4, _safe("Fait a : _________________________________"), border=0)
    pdf.set_xy(17, sig_y + 14)
    pdf.cell(sig_w - 4, 4, "Le : _______ / _______ / ___________", border=0)

    pdf.rect(sig_x2, sig_y, sig_w, sig_h)
    pdf.set_xy(sig_x2 + 2, sig_y + 2)
    pdf.set_font(FONT, "B", 8)
    pdf.set_text_color(*ACCENT)
    pdf.cell(sig_w - 4, 5, "Signature du client", border=0)

    return bytes(pdf.output())
