"""
Génération de PDF pour les devis/factures.
Utilise fpdf2 (pur Python, pas de dépendances système).

Deux modèles visuels :
  - "moderne" (défaut) : bandeau vert forêt #14532D, texte blanc, lots fond #E3EDE6
  - "pro"             : fond blanc, texte anthracite #1F2937, Times, accents #3B5573
"""
import base64
import logging
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


def _fmt_signature_date(iso_datetime: Optional[str]) -> Optional[str]:
    """Formate un horodatage de signature (colonne `date_signature`, ISO avec fuseau)
    en 'JJ/MM/AAAA à HH:MM'. None si absent — ne jamais inventer une date."""
    if not iso_datetime:
        return None
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(iso_datetime.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y à %H:%M")
    except Exception:
        return iso_datetime  # repli : brut plutôt que rien


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
    signature_nom_signataire: Optional[str] = None,
    signature_image_base64: Optional[str] = None,
    signature_date: Optional[str] = None,
) -> bytes:
    """Génère le PDF et retourne les bytes.

    signature_nom_signataire / signature_image_base64 : capturés lors de la
    signature électronique (Batch 12 T3), métadonnée du document — pas du
    devis lui-même, donc jamais dans `Devis`/`quote.py`. Si renseignés,
    l'encadré "Signature du client" affiche la vraie signature au lieu de
    rester vide.
    """
    logging.info("[PDF] afficher_signature=%s document_type=%s signe=%s", devis.afficher_signature, document_type, bool(signature_nom_signataire))
    try:
        from fpdf import FPDF
    except ImportError:
        raise RuntimeError("fpdf2 n'est pas installé. Lancez : pip install fpdf2")

    modele    = (devis.modele or "moderne").lower()
    is_pro    = (modele == "pro")
    FONT      = "Times" if is_pro else "Helvetica"
    if devis.type_facture == "acompte":
        doc_label = "FACTURE D'ACOMPTE"
    elif devis.type_facture == "solde":
        doc_label = "FACTURE DE SOLDE"
    else:
        doc_label = "FACTURE" if document_type == "facture" else "DEVIS"
    doc_date  = _fmt_date(document_date)

    pdf = FPDF(format="A4")
    pdf.core_fonts_encoding = "cp1252"
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    W = 180.0  # largeur utile (210 - 2×15 mm)

    # ── Helpers couleur (définis ici pour être utilisables dans tout le corps du PDF) ──
    def _set_body() -> None:
        """Remet texte+trait à leurs valeurs corps — évite tout saignement de couleur."""
        body_color = (24, 33, 28) if not is_pro else (31, 41, 55)
        pdf.set_text_color(*body_color)
        pdf.set_draw_color(*BORDER)
        pdf.set_line_width(0.2)

    def _set_white() -> None:
        pdf.set_text_color(*WHITE)

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

    # Mention forme juridique + capital social (sociétés uniquement) — mention
    # légale obligatoire distincte du SIRET. None si auto-entrepreneur (pas de
    # capital social) ou si statut_juridique absent (devis antérieurs à Batch 21,
    # rétrocompatible : pas de ligne ajoutée).
    forme_capital_line = None
    if devis.artisan.statut_juridique == "societe":
        forme = devis.artisan.forme_juridique
        capital = devis.artisan.capital_social
        if forme and capital is not None:
            forme_capital_line = f"{forme} au capital de {_fmt_money(capital)}"
        elif forme:
            forme_capital_line = forme
        elif capital is not None:
            forme_capital_line = f"Capital social : {_fmt_money(capital)}"

    # Calcul de la hauteur header (pour le bandeau moderne)
    artisan_info_lines = [
        devis.artisan.siret,
        forme_capital_line,
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
        _set_white()
    nom_affiche = devis.artisan.nom or "Votre Entreprise"
    if devis.artisan.statut_juridique == "auto_entrepreneur":
        nom_affiche = f"{nom_affiche} (EI)"
    pdf.cell(text_w, 7, _safe(nom_affiche), border=0)
    left_y += 8

    # Infos artisan
    pdf.set_font(FONT, "", 8)
    if is_pro:
        pdf.set_text_color(*P_GRAY)
    else:
        pdf.set_text_color(200, 230, 210)  # blanc cassé sur vert

    info_pairs = [
        (f"SIRET : {devis.artisan.siret}",        devis.artisan.siret),
        (forme_capital_line,                      forme_capital_line),
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
        _set_white()
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

    if document_type == "devis" and devis.validite_jours:
        pdf.set_xy(LABEL_X, label_y)
        pdf.cell(70, 4, _safe(f"Valable {devis.validite_jours} jours"), border=0, align="R")
        label_y += 4

    if devis.numero_document:
        num_label = "N Facture" if document_type == "facture" else "N Devis"
        pdf.set_xy(LABEL_X, label_y)
        pdf.set_font(FONT, "B", 8)
        if is_pro:
            pdf.set_text_color(*P_STEEL)
        else:
            _set_white()
        pdf.cell(70, 4, _safe(f"{num_label} : {devis.numero_document}"), border=0, align="R")
    _set_body()  # reset systématique après fin de l'en-tête (texte blanc peut rester actif)

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
    client_bh     = 13 + n_client_addr * 4 + 2
    bh = min(max(26.0, 11 + n_chantier * 4, client_bh), 55.0)  # cap à 55 mm

    ACCENT     = M_GREEN if not is_pro else P_STEEL
    MUTED_TEXT = P_GRAY if is_pro else (100, 116, 139)  # texte grisé secondaire

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
        pdf.set_text_color(*MUTED_TEXT)
        pdf.multi_cell(bw - 3, 4, _safe(devis.client.adresse))


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
        _set_white()
        pdf.set_font(FONT, "B", 8)
        pdf.set_draw_color(*BORDER)
        for h, w, a in zip(col_h, col_w, col_a):
            pdf.cell(w, 8, _safe(h), border=0, align=a, fill=True)
        pdf.ln()
        _set_body()       # reset text color — évite le saignement de blanc
        pdf.set_font(FONT, "", 8)  # reset Regular — _draw_table_header laisse Bold

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

        # Batch 16 : la police active peut avoir été laissée en Bold par le
        # sous-total du lot précédent (dernier pdf.set_font de la boucle
        # d'avant) — _row_height() mesurerait alors le texte du prochain lot
        # avec la mauvaise police, surestimant lot_total_h et déclenchant un
        # saut de page un peu trop tôt. Jamais de perte de contenu (le dessin
        # réel reset déjà la police), juste une pagination trop pessimiste.
        pdf.set_font(FONT, "", 8)

        # ── T1 : LOT = bloc insécable ────────────────────────────────────
        # Calculer la hauteur totale du lot avant de le dessiner.
        band_h_lot  = 7 if (has_lots and lot_name) else 0
        lines_h_tot = sum(
            _row_height(_safe(l.poste), _safe(l.description)) for l in lot_lignes
        )
        sub_h_const = 6 if show_sub else 0
        lot_total_h = band_h_lot + lines_h_tot + sub_h_const

        # Y de départ d'une page fraîche (après add_page + header)
        FRESH_TOP     = 23.0
        available_now = PAGE_BOT - pdf.get_y()
        fresh_space   = PAGE_BOT - FRESH_TOP
        fits_now      = lot_total_h <= available_now
        fits_fresh    = lot_total_h <= fresh_space
        big_lot       = not fits_fresh  # lot plus grand qu'une page entière

        if not fits_now:
            if not big_lot:
                # Le lot entier tient sur une nouvelle page → saut avant titre
                pdf.add_page()
                _draw_table_header()
            else:
                # Lot trop grand pour une page : saut si le début ne tient pas
                first_h = _row_height(_safe(lot_lignes[0].poste), _safe(lot_lignes[0].description))
                if available_now < band_h_lot + first_h:
                    pdf.add_page()
                    _draw_table_header()

        # ── Bandeau de LOT ───────────────────────────────────────────────
        if has_lots and lot_name:
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
            _set_body()  # reset après bandeau LOT — évite saignement sur la première ligne

        # ── Lignes ───────────────────────────────────────────────────────
        for i_ligne, ligne in enumerate(lot_lignes):
            is_last    = (i_ligne == n_lot - 1)
            _qty = ligne.quantite if ligne.quantite is not None else 1.0
            montant_ht = round(_qty * ligne.prix_unitaire_ht, 2)
            qty_str = "au réel" if ligne.quantite is None else f"{ligne.quantite:g}"
            _set_body()  # toujours forcer la couleur corps avant chaque ligne prestation
            pdf.set_font(FONT, "", 8)

            if with_tva:
                vals = [
                    _safe(ligne.poste), _safe(ligne.description),
                    qty_str, _safe(ligne.unite),
                    _fmt_money(ligne.prix_unitaire_ht), f"{ligne.tva_taux:.0f}%",
                    _fmt_money(montant_ht),
                ]
            else:
                vals = [
                    _safe(ligne.poste), _safe(ligne.description),
                    qty_str, _safe(ligne.unite),
                    _fmt_money(ligne.prix_unitaire_ht), _fmt_money(montant_ht),
                ]

            row_h = _row_height(vals[0], vals[1])

            # Saut de page individuel uniquement pour les gros lots
            if big_lot:
                sub_margin = sub_h_const if is_last else 0
                if pdf.get_y() + row_h + sub_margin > PAGE_BOT:
                    pdf.add_page()
                    _draw_table_header()  # reset text=body + font=Regular intégré

            y_start = pdf.get_y()
            if row_i % 2 == 1:
                pdf.set_fill_color(*LIGHT_GRAY)
                pdf.rect(15, y_start, W, row_h, "F")

            _set_body()             # défensif : garantit texte foncé juste avant chaque cellule
            pdf.set_font(FONT, "", 8)  # garantit Regular juste avant chaque cellule
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
        if show_sub:
            lot_ht    = round(sum((l.quantite if l.quantite is not None else 1.0) * l.prix_unitaire_ht for l in lot_lignes), 2)
            sub_label = _safe(f"Sous-total {lot_name}" if lot_name else "Sous-total")
            if pdf.get_y() + 6 > PAGE_BOT:
                pdf.add_page()
                _draw_table_header()  # redessiner l'entête + _set_body() intégré
            _set_body()  # reset avant sous-total
            y_sub = pdf.get_y()
            pdf.set_fill_color(*LIGHT_GRAY)
            pdf.rect(15, y_sub, W, 6, "F")
            pdf.set_xy(15, y_sub)
            pdf.set_font(FONT, "BI" if not is_pro else "I", 7.5)
            pdf.set_text_color(*MUTED_TEXT)
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
    has_retenue = (devis.retenue_garantie_taux or 0) > 0

    pdf.set_fill_color(*LIGHT_GRAY)

    def _tot_row(label: str, value_str: str, first: bool = False) -> None:
        border = "TB" if first else "B"
        pdf.set_xy(tot_x, pdf.get_y())
        pdf.set_font(FONT, "", 9)
        pdf.set_text_color(*MUTED_TEXT)
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
            _set_white()
            pdf.set_font(FONT, "B", 10)
            pdf.cell(35, 9, label, border=0, fill=True)
            pdf.cell(30, 9, value_str, border=0, align="R", fill=True)
            pdf.set_fill_color(*LIGHT_GRAY)
        pdf.ln()
        _set_body()  # reset systématique après potentiel texte blanc

    if with_tva:
        ht_label = "Total HT brut" if has_remise else "Total HT"
        _tot_row(ht_label, _fmt_money(totaux.total_ht), first=True)
        if has_remise:
            ht_net = totaux.total_ht_net if totaux.total_ht_net else (totaux.total_ht - (totaux.remise_ht or 0))
            _tot_row("Remise", "- " + _fmt_money(totaux.remise_ht or 0))
            _tot_row("Total HT net", _fmt_money(ht_net))
        _tot_row("Total TVA", _fmt_money(totaux.total_tva))
        _tot_row_accent("TOTAL TTC", _fmt_money(totaux.total_ttc))
        net = totaux.total_ttc
        if has_acompte:
            pdf.ln(2)
            _tot_row(_safe("Acompte vers\xe9"), "- " + _fmt_money(devis.acompte or 0), first=True)
            net = totaux.net_a_payer if totaux.net_a_payer else max(0, totaux.total_ttc - (devis.acompte or 0))
            _tot_row_accent("NET A PAYER", _fmt_money(net))
        if has_retenue:
            pdf.ln(2)
            retenue_montant = round(totaux.total_ttc * (devis.retenue_garantie_taux or 0) / 100, 2)
            retenue_label = _safe(f"Retenue de garantie ({devis.retenue_garantie_taux:g}%)")
            _tot_row(retenue_label, "- " + _fmt_money(retenue_montant), first=True)
            net = max(0, net - retenue_montant)
            _tot_row_accent("NET A PAYER", _fmt_money(net))
    else:
        if has_remise:
            ht_net = totaux.total_ht_net if totaux.total_ht_net else (totaux.total_ht - (totaux.remise_ht or 0))
            _tot_row("Total HT brut", _fmt_money(totaux.total_ht), first=True)
            _tot_row("Remise", "- " + _fmt_money(totaux.remise_ht or 0))
            _tot_row_accent("TOTAL HT NET", _fmt_money(ht_net))
        else:
            _tot_row_accent("TOTAL HT", _fmt_money(totaux.total_ht))
        ht_base = totaux.total_ht_net if totaux.total_ht_net else totaux.total_ht
        net = ht_base
        if has_acompte:
            pdf.ln(2)
            _tot_row(_safe("Acompte vers\xe9"), "- " + _fmt_money(devis.acompte or 0), first=True)
            net = totaux.net_a_payer if totaux.net_a_payer else max(0, ht_base - (devis.acompte or 0))
            _tot_row_accent("NET A PAYER", _fmt_money(net))
        if has_retenue:
            pdf.ln(2)
            retenue_montant = round(ht_base * (devis.retenue_garantie_taux or 0) / 100, 2)
            retenue_label = _safe(f"Retenue de garantie ({devis.retenue_garantie_taux:g}%)")
            _tot_row(retenue_label, "- " + _fmt_money(retenue_montant), first=True)
            net = max(0, net - retenue_montant)
            _tot_row_accent("NET A PAYER", _fmt_money(net))

    pdf.ln(4)

    # ── T2 : Préparer les mentions AVANT le saut de page ─────────────
    # T4 : validite=None → pas de mention de validité
    # T6 : masquer les mentions TVA en mode "Sans TVA"
    validite = devis.validite_jours  # None si non renseigné
    final_mentions = []
    for m in devis.mentions_legales:
        ml = m.lower()
        if "valable" in ml and "jours" in ml:
            if document_type == "devis" and validite:
                final_mentions.append(f"Devis valable {validite} jours a compter de la date d'emission")
        elif not with_tva and "tva" in ml:
            pass  # Masquer toutes les mentions TVA taux en mode sans TVA
        elif not devis.afficher_signature and "accord" in ml:
            pass  # Masquer toute mention "Bon pour accord" si l'encadré signature est désactivé
        else:
            final_mentions.append(m)

    if document_type == "devis":
        if validite and not any("valable" in m.lower() for m in final_mentions):
            final_mentions.insert(0, f"Devis valable {validite} jours a compter de la date d'emission")
        if devis.afficher_signature and not any("accord" in m.lower() for m in final_mentions):
            final_mentions.append("Signature du client precedee de la mention 'Bon pour accord'")
    else:
        if not any("retard" in m.lower() or "penalite" in m.lower() for m in final_mentions):
            final_mentions.append(
                "Tout retard de paiement entraine des penalites de retard au taux legal en vigueur "
                "majore de 10 points + indemnite forfaitaire de 40 EUR pour frais de recouvrement"
            )

    if devis.conditions_paiement:
        final_mentions.append(f"Conditions de paiement : {devis.conditions_paiement}")

    # T4-4 : TVA a taux reduit (10%/5.5%) specifique travaux — mention obligatoire
    # de l'attestation client. Non pertinent en autoliquidation (TVA due par le
    # preneur, pas de taux reduit a justifier sur CETTE facture).
    if with_tva and not devis.autoliquidation:
        taux_presents = {round(l.tva_taux, 2) for l in devis.lignes}
        if 10.0 in taux_presents:
            final_mentions.append(
                "TVA a 10% appliquee sur attestation du client certifiant l'eligibilite des travaux "
                "(art. 279-0 bis du CGI - logement acheve depuis plus de 2 ans)"
            )
        if 5.5 in taux_presents:
            final_mentions.append(
                "TVA a 5,5% appliquee sur attestation du client certifiant l'eligibilite des travaux "
                "(art. 278-0 bis A du CGI - amelioration de la qualite energetique)"
            )

    # T4-5 : Autoliquidation (sous-traitance BTP) — mention obligatoire,
    # remplace toute mention de franchise en base (art. 293 B) : ce sont deux
    # regimes distincts et mutuellement exclusifs.
    if devis.autoliquidation:
        final_mentions.append(
            "Autoliquidation de la TVA - Article 283-2 nonies du CGI - TVA due par le preneur"
        )

    # T2 : Estimation de la hauteur du bloc footer → saut de page si besoin
    has_rib   = bool(devis.artisan.iban or devis.artisan.bic)
    rib_lines = (1 if devis.artisan.iban else 0) + (1 if devis.artisan.bic else 0)
    has_assurance = bool(
        devis.artisan.assurance_nom or devis.artisan.assurance_contrat or devis.artisan.assurance_couverture
    )
    assurance_lines = (
        (1 if devis.artisan.assurance_nom else 0)
        + (1 if devis.artisan.assurance_contrat else 0)
        + (1 if devis.artisan.assurance_couverture else 0)
    )
    footer_h  = (
        5                                                 # séparateur + espacement
        + len(final_mentions) * 4                        # mentions (1 ligne ≈ 4 mm)
        + (4 if (not with_tva and not devis.autoliquidation) else 0)  # art. 293 B
        + (4 + 4 + rib_lines * 4 + 4 if has_rib else 0) # RIB section
        + (4 + 4 + assurance_lines * 4 + 4 if has_assurance else 0)  # assurance pro (T1 Batch 11)
        + (34 if devis.afficher_signature else 0)        # signature (ln6 + sig_h22 + marges)
    )
    if pdf.get_y() + footer_h > pdf.h - 15:
        pdf.add_page()

    # ── MENTIONS LÉGALES ──────────────────────────────────────────────
    pdf.set_draw_color(*BORDER)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(3)

    pdf.set_font(FONT, "", 7)
    pdf.set_text_color(*MUTED_TEXT)

    for m in final_mentions:
        pdf.cell(0, 4, _safe(f"* {m}"), ln=True)

    if not with_tva and not devis.autoliquidation:
        pdf.set_font(FONT, "B", 7)
        pdf.cell(0, 4, "* TVA non applicable, art. 293 B du CGI", ln=True)

    # ── RIB / COORDONNÉES BANCAIRES ──────────────────────────────────
    if has_rib:
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

    # ── ASSURANCE PROFESSIONNELLE / DÉCENNALE (mention obligatoire BTP) ──
    if has_assurance:
        pdf.ln(4)
        pdf.set_draw_color(*BORDER)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(3)
        pdf.set_font(FONT, "B", 8)
        pdf.set_text_color(*ACCENT)
        pdf.cell(0, 4, "Assurance professionnelle", ln=True)
        pdf.set_font(FONT, "", 8)
        pdf.set_text_color(*BLACK)
        if devis.artisan.assurance_nom:
            pdf.cell(0, 4, _safe(f"Assureur : {devis.artisan.assurance_nom}"), ln=True)
        if devis.artisan.assurance_contrat:
            pdf.cell(0, 4, _safe(f"N\xb0 de contrat : {devis.artisan.assurance_contrat}"), ln=True)
        if devis.artisan.assurance_couverture:
            pdf.cell(0, 4, _safe(f"Couverture geographique : {devis.artisan.assurance_couverture}"), ln=True)

    # ── ZONE DE SIGNATURE ────────────────────────────────────────────
    if devis.afficher_signature:
        pdf.ln(6)
        sig_y = pdf.get_y()
        pdf.set_y(sig_y)

        sig_w  = 82.0
        sig_h  = 22.0
        sig_x2 = 15 + sig_w + 16

        pdf.set_draw_color(*BORDER)
        pdf.set_line_width(0.4)

        pdf.rect(15, sig_y, sig_w, sig_h)
        pdf.set_xy(17, sig_y + 2)
        pdf.set_font(FONT, "B", 8)
        pdf.set_text_color(*ACCENT)
        pdf.cell(sig_w - 4, 5, "Bon pour accord", border=0)
        pdf.set_font(FONT, "", 7.5)
        pdf.set_text_color(*MUTED_TEXT)
        if signature_nom_signataire:
            pdf.set_xy(17, sig_y + 9)
            pdf.cell(sig_w - 4, 4, _safe(f"Signe electroniquement par {signature_nom_signataire}"), border=0)
            formatted_sig_date = _fmt_signature_date(signature_date)
            if formatted_sig_date:
                pdf.set_xy(17, sig_y + 14)
                pdf.cell(sig_w - 4, 4, _safe(f"Le {formatted_sig_date}"), border=0)
        else:
            pdf.set_xy(17, sig_y + 9)
            pdf.cell(sig_w - 4, 4, _safe("Fait a : _________________________________"), border=0)
            pdf.set_xy(17, sig_y + 14)
            pdf.cell(sig_w - 4, 4, "Le : _______ / _______ / ___________", border=0)

        pdf.rect(sig_x2, sig_y, sig_w, sig_h)
        pdf.set_xy(sig_x2 + 2, sig_y + 2)
        pdf.set_font(FONT, "B", 8)
        pdf.set_text_color(*ACCENT)
        pdf.cell(sig_w - 4, 5, "Signature du client", border=0)

        # Signature capturée (Batch 12 T3) : dessin à main levée en priorité,
        # sinon le nom en italique comme repli. Ne touche jamais le rendu si
        # le document n'est pas encore signé (comportement inchangé).
        image_inseree = False
        if signature_image_base64:
            try:
                img_bytes = base64.b64decode(signature_image_base64)
                pdf.image(BytesIO(img_bytes), x=sig_x2 + 4, y=sig_y + 8, w=sig_w - 8, h=sig_h - 10)
                image_inseree = True
            except Exception as exc:
                logging.warning("[PDF] echec insertion image signature, repli sur le nom : %s", exc)

        if not image_inseree and signature_nom_signataire:
            pdf.set_font(FONT, "I", 13)
            pdf.set_text_color(*BLACK)
            pdf.set_xy(sig_x2 + 4, sig_y + 11)
            pdf.cell(sig_w - 8, 6, _safe(signature_nom_signataire), border=0)
            # Reset — dernier élément dessiné, mais on respecte la règle (C)
            # (toujours reposer un état propre après un texte non "body").
            _set_body()

    return bytes(pdf.output())
