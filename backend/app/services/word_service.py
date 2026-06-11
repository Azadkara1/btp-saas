"""
Génération de documents Word (.docx) pour les devis/factures.
Utilise python-docx (pur Python).
Permet à l'artisan ou au client de modifier le document après export.
"""
import base64
from datetime import date as date_class
from typing import Optional
from io import BytesIO
from app.models.quote import Devis


# Largeur utile A4 avec marges 2cm de chaque côté : 21 - 2 - 2 = 17 cm
PAGE_W_CM = 17.0


def _fmt_date(iso_date: Optional[str]) -> str:
    if iso_date:
        try:
            y, m, d = iso_date.split("-")
            return f"{d}/{m}/{y}"
        except Exception:
            pass
    return date_class.today().strftime("%d/%m/%Y")


def generate_quote_docx(
    devis: Devis,
    document_type: str = "devis",
    with_tva: bool = True,
    document_date: Optional[str] = None,
) -> bytes:
    """Génère le .docx et retourne les bytes."""
    try:
        from docx import Document
        from docx.shared import Pt, RGBColor, Cm
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.enum.table import WD_TABLE_ALIGNMENT
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement
    except ImportError:
        raise RuntimeError("python-docx n'est pas installé. Lancez : pip install python-docx")

    doc_label = "FACTURE" if document_type == "facture" else "DEVIS"
    doc_date = _fmt_date(document_date)

    def _fmt_money(amount: float) -> str:
        """Format monétaire français : '1 234,56 €'"""
        s = f"{amount:.2f}"
        int_part, dec_part = s.split(".")
        n, groups = len(int_part), []
        while n > 3:
            groups.insert(0, int_part[n - 3:n])
            n -= 3
        groups.insert(0, int_part[:n])
        return " ".join(groups) + "," + dec_part + " €"

    BLUE  = RGBColor(26, 86, 219)
    GRAY  = RGBColor(100, 116, 139)
    AMBER = RGBColor(180, 120, 0)
    WHITE = RGBColor(255, 255, 255)
    BLACK = RGBColor(30, 30, 30)

    # ── Helpers ──────────────────────────────────────────────────────

    def _set_cell_bg(cell, hex_color: str):
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), hex_color)
        tcPr.append(shd)

    def _remove_cell_borders(cell):
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        tcBorders = OxmlElement("w:tcBorders")
        for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
            b = OxmlElement(f"w:{side}")
            b.set(qn("w:val"), "none")
            tcBorders.append(b)
        tcPr.append(tcBorders)

    # 1 cm = 1440/25.4 = 566.93 twips
    TWIPS_PER_CM = 566.93

    def _fix_table(table, width_cm: float = PAGE_W_CM):
        """Fixe la largeur du tableau, supprime l'indentation et active le layout fixe."""
        w_twips = str(round(width_cm * TWIPS_PER_CM))
        tbl = table._tbl
        tblPr = tbl.find(qn("w:tblPr"))
        if tblPr is None:
            tblPr = OxmlElement("w:tblPr")
            tbl.insert(0, tblPr)
        for tag in ("w:tblInd", "w:tblW", "w:tblLayout"):
            for old in tblPr.findall(qn(tag)):
                tblPr.remove(old)
        # Indentation nulle
        tblInd = OxmlElement("w:tblInd")
        tblInd.set(qn("w:w"), "0")
        tblInd.set(qn("w:type"), "dxa")
        tblPr.append(tblInd)
        # Largeur fixe en twips
        tblW = OxmlElement("w:tblW")
        tblW.set(qn("w:w"), w_twips)
        tblW.set(qn("w:type"), "dxa")
        tblPr.append(tblW)
        # Layout fixe (pas d'autofit)
        tblLayout = OxmlElement("w:tblLayout")
        tblLayout.set(qn("w:type"), "fixed")
        tblPr.append(tblLayout)

    def _zero_para_spacing(para):
        """Supprime l'espacement avant/après d'un paragraphe."""
        pPr = para._p.get_or_add_pPr()
        spacing = OxmlElement("w:spacing")
        spacing.set(qn("w:before"), "0")
        spacing.set(qn("w:after"), "0")
        pPr.append(spacing)

    def _run(para, text: str, size: int, color: RGBColor = None,
             bold: bool = False, italic: bool = False) -> None:
        r = para.add_run(text)
        r.bold = bold
        r.italic = italic
        r.font.size = Pt(size)
        if color:
            r.font.color.rgb = color

    # ── Document ─────────────────────────────────────────────────────
    doc = Document()

    # Styles par défaut : supprimer l'espacement des paragraphes Normal
    normal_style = doc.styles["Normal"]
    normal_style.paragraph_format.space_before = Pt(0)
    normal_style.paragraph_format.space_after  = Pt(0)

    for section in doc.sections:
        section.top_margin    = Cm(1.5)
        section.bottom_margin = Cm(1.5)
        section.left_margin   = Cm(2)
        section.right_margin  = Cm(2)

    # ── EN-TÊTE : artisan (gauche) | label doc (droite) ─────────────
    # Largeurs : 10 + 7 = 17 cm
    ht = doc.add_table(rows=1, cols=2)
    ht.autofit = False
    ht.columns[0].width = Cm(10)
    ht.columns[1].width = Cm(7)
    ht.alignment = WD_TABLE_ALIGNMENT.LEFT
    _fix_table(ht)

    for cell in ht.rows[0].cells:
        _remove_cell_borders(cell)

    lc = ht.cell(0, 0)

    # Logo artisan (optionnel)
    if devis.artisan.logo_base64:
        try:
            logo_data = base64.b64decode(devis.artisan.logo_base64)
            p_logo = lc.paragraphs[0]
            _zero_para_spacing(p_logo)
            p_logo.add_run().add_picture(BytesIO(logo_data), height=Cm(4.5))
            p_name = lc.add_paragraph()
        except Exception:
            p_name = lc.paragraphs[0]
    else:
        p_name = lc.paragraphs[0]

    _zero_para_spacing(p_name)
    _run(p_name, devis.artisan.nom or "Votre Entreprise", size=14, color=BLUE, bold=True)

    # Infos artisan (SIRET, adresse, contact) — chaque champ préfixé par son libellé
    artisan_lines = [
        f"SIRET : {devis.artisan.siret}" if devis.artisan.siret else None,
        f"Adresse : {devis.artisan.adresse}" if devis.artisan.adresse else None,
        " ".join(filter(None, [devis.artisan.code_postal, devis.artisan.ville])) or None,
        f"Tél : {devis.artisan.telephone}" if devis.artisan.telephone else None,
        f"Mail : {devis.artisan.email}" if devis.artisan.email else None,
        f"Web : {devis.artisan.site_web}" if devis.artisan.site_web else None,
    ]
    for line in artisan_lines:
        if line:
            p = lc.add_paragraph()
            _zero_para_spacing(p)
            _run(p, line, size=9, color=GRAY)

    rc = ht.cell(0, 1)
    p = rc.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    _zero_para_spacing(p)
    _run(p, doc_label, size=22, color=BLUE, bold=True)

    p2 = rc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    _zero_para_spacing(p2)
    _run(p2, f"Date : {doc_date}", size=9, color=GRAY)

    if document_type == "devis":
        p3 = rc.add_paragraph()
        p3.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        _zero_para_spacing(p3)
        _run(p3, "Valable 30 jours", size=9, color=GRAY)

    if devis.numero_document:
        num_label = "N° Facture" if document_type == "facture" else "N° Devis"
        p_num = rc.add_paragraph()
        p_num.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        _zero_para_spacing(p_num)
        _run(p_num, f"{num_label} : {devis.numero_document}", size=9, color=BLUE, bold=True)

    # Séparateur
    sep = doc.add_paragraph()
    _zero_para_spacing(sep)

    # ── CLIENT + CHANTIER ────────────────────────────────────────────
    # Largeurs : 8.5 + 8.5 = 17 cm
    it = doc.add_table(rows=1, cols=2)
    it.autofit = False
    it.columns[0].width = Cm(8.5)
    it.columns[1].width = Cm(8.5)
    it.alignment = WD_TABLE_ALIGNMENT.LEFT
    _fix_table(it)

    cc = it.cell(0, 0)
    _set_cell_bg(cc, "EFF6FF")
    p = cc.paragraphs[0]
    _zero_para_spacing(p)
    _run(p, "CLIENT", size=8, color=BLUE, bold=True)
    p2 = cc.add_paragraph()
    _zero_para_spacing(p2)
    _run(p2, devis.client.nom or "—", size=10, bold=True)
    if devis.client.adresse:
        p3 = cc.add_paragraph()
        _zero_para_spacing(p3)
        _run(p3, devis.client.adresse, size=9, color=GRAY)

    ch = it.cell(0, 1)
    _set_cell_bg(ch, "FFFBEB")
    p = ch.paragraphs[0]
    _zero_para_spacing(p)
    _run(p, "CHANTIER", size=8, color=AMBER, bold=True)
    p2 = ch.add_paragraph()
    _zero_para_spacing(p2)
    _run(p2, devis.chantier.description, size=9, color=BLACK)

    sep2 = doc.add_paragraph()
    _zero_para_spacing(sep2)

    # ── TABLEAU DES PRESTATIONS ──────────────────────────────────────
    # Largeurs somment à 17 cm exactement
    if with_tva:
        headers    = ["Prestation", "Description", "Qté", "PU HT", "TVA", "Total HT"]
        col_widths = [Cm(3.0), Cm(6.5), Cm(1.3), Cm(2.5), Cm(1.5), Cm(2.2)]  # T=17.0
        col_aligns = ([WD_ALIGN_PARAGRAPH.LEFT] * 2 +
                      [WD_ALIGN_PARAGRAPH.CENTER] +
                      [WD_ALIGN_PARAGRAPH.RIGHT] * 3)
    else:
        headers    = ["Prestation", "Description", "Qté", "PU HT", "Total HT"]
        col_widths = [Cm(3.5), Cm(7.5), Cm(1.3), Cm(2.5), Cm(2.2)]  # T=17.0
        col_aligns = ([WD_ALIGN_PARAGRAPH.LEFT] * 2 +
                      [WD_ALIGN_PARAGRAPH.CENTER] +
                      [WD_ALIGN_PARAGRAPH.RIGHT] * 2)

    tbl = doc.add_table(rows=1, cols=len(headers))
    tbl.style = "Table Grid"
    tbl.autofit = False
    tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
    _fix_table(tbl)
    for i, w in enumerate(col_widths):
        tbl.columns[i].width = w

    # En-tête
    for i, (cell, h) in enumerate(zip(tbl.rows[0].cells, headers)):
        _set_cell_bg(cell, "1A56DB")
        p = cell.paragraphs[0]
        p.alignment = col_aligns[i]
        _zero_para_spacing(p)
        r = p.add_run(h)
        r.bold = True
        r.font.size = Pt(9)
        r.font.color.rgb = WHITE

    # Lignes de prestation — groupées par LOT si applicable
    has_lots = any(l.lot for l in devis.lignes)
    lot_groups: dict = {}
    for ligne in devis.lignes:
        key = ligne.lot or ""
        if key not in lot_groups:
            lot_groups[key] = []
        lot_groups[key].append(ligne)

    row_i = 0
    for lot_name, lot_lignes in lot_groups.items():

        # En-tête de LOT
        if has_lots and lot_name:
            lot_row = tbl.add_row()
            for cell in lot_row.cells:
                _set_cell_bg(cell, "475569")   # slate-600
                _remove_cell_borders(cell)
            p = lot_row.cells[0].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            _zero_para_spacing(p)
            r = p.add_run(f"  {lot_name}")
            r.bold = True
            r.font.size = Pt(9)
            r.font.color.rgb = WHITE
            for cell in lot_row.cells[1:]:
                _zero_para_spacing(cell.paragraphs[0])

        for ligne in lot_lignes:
            montant_ht = round(ligne.quantite * ligne.prix_unitaire_ht, 2)
            bg = "F8F9FA" if row_i % 2 == 1 else "FFFFFF"
            row = tbl.add_row()

            vals = (
                [ligne.poste, ligne.description,
                 f"{ligne.quantite} {ligne.unite}",
                 _fmt_money(ligne.prix_unitaire_ht),
                 f"{ligne.tva_taux:.0f}%",
                 _fmt_money(montant_ht)]
                if with_tva else
                [ligne.poste, ligne.description,
                 f"{ligne.quantite} {ligne.unite}",
                 _fmt_money(ligne.prix_unitaire_ht),
                 _fmt_money(montant_ht)]
            )

            for cell, val, align in zip(row.cells, vals, col_aligns):
                _set_cell_bg(cell, bg)
                p = cell.paragraphs[0]
                p.alignment = align
                _zero_para_spacing(p)
                r = p.add_run(val)
                r.font.size = Pt(9)
            row_i += 1

        # Sous-total du LOT (affiché seulement s'il y a plusieurs LOTs)
        if has_lots and len(lot_groups) > 1:
            lot_ht = round(sum(l.quantite * l.prix_unitaire_ht for l in lot_lignes), 2)
            sub_row = tbl.add_row()
            n = len(sub_row.cells)
            sub_label = f"Sous-total {lot_name}" if lot_name else "Sous-total"
            for idx, cell in enumerate(sub_row.cells):
                _set_cell_bg(cell, "F1F5F9")  # slate-100
                p = cell.paragraphs[0]
                _zero_para_spacing(p)
                if idx == n - 2:
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    r = p.add_run(sub_label)
                    r.italic = True
                    r.font.size = Pt(9)
                    r.font.color.rgb = GRAY
                elif idx == n - 1:
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    r = p.add_run(_fmt_money(lot_ht))
                    r.bold = True
                    r.font.size = Pt(9)
                    r.font.color.rgb = BLACK

    sep3 = doc.add_paragraph()
    _zero_para_spacing(sep3)

    # ── TOTAUX ───────────────────────────────────────────────────────
    # 4 + 3 = 7 cm, aligné à droite
    tot = doc.add_table(rows=0, cols=2)
    tot.autofit = False
    tot.columns[0].width = Cm(4)
    tot.columns[1].width = Cm(3)
    tot.alignment = WD_TABLE_ALIGNMENT.RIGHT
    _fix_table(tot, width_cm=7.0)

    def _add_total_row(label: str, value: str, bold: bool = False, blue: bool = False):
        r = tot.add_row()
        for cell in r.cells:
            _set_cell_bg(cell, "1A56DB" if blue else "F8F9FA")
        for cell, txt, align in [(r.cells[0], label, WD_ALIGN_PARAGRAPH.LEFT),
                                  (r.cells[1], value, WD_ALIGN_PARAGRAPH.RIGHT)]:
            p = cell.paragraphs[0]
            p.alignment = align
            _zero_para_spacing(p)
            run = p.add_run(txt)
            run.bold = bold
            run.font.size = Pt(10)
            if blue:
                run.font.color.rgb = WHITE

    totaux      = devis.totaux
    has_remise  = (totaux.remise_ht or 0) > 0
    has_acompte = (devis.acompte or 0) > 0

    def _add_total_row_green(label: str, value: str):
        r = tot.add_row()
        for cell in r.cells:
            _set_cell_bg(cell, "047857")
        for cell, txt, align in [(r.cells[0], label, WD_ALIGN_PARAGRAPH.LEFT),
                                  (r.cells[1], value, WD_ALIGN_PARAGRAPH.RIGHT)]:
            p = cell.paragraphs[0]
            p.alignment = align
            _zero_para_spacing(p)
            run = p.add_run(txt)
            run.bold = True
            run.font.size = Pt(10)
            run.font.color.rgb = WHITE

    if with_tva:
        ht_label = "Total HT brut" if has_remise else "Total HT"
        _add_total_row(ht_label, _fmt_money(totaux.total_ht))
        if has_remise:
            ht_net = totaux.total_ht_net if totaux.total_ht_net else (totaux.total_ht - (totaux.remise_ht or 0))
            _add_total_row("Remise", "- " + _fmt_money(totaux.remise_ht or 0))
            _add_total_row("Total HT net", _fmt_money(ht_net))
        _add_total_row("Total TVA", _fmt_money(totaux.total_tva))
        _add_total_row("TOTAL TTC", _fmt_money(totaux.total_ttc), bold=True, blue=True)
        if has_acompte:
            _add_total_row("Acompte vers\xe9", "- " + _fmt_money(devis.acompte or 0))
            net = totaux.net_a_payer if totaux.net_a_payer else max(0, totaux.total_ttc - (devis.acompte or 0))
            _add_total_row_green("NET A PAYER", _fmt_money(net))
    else:
        if has_remise:
            ht_net = totaux.total_ht_net if totaux.total_ht_net else (totaux.total_ht - (totaux.remise_ht or 0))
            _add_total_row("Total HT brut", _fmt_money(totaux.total_ht))
            _add_total_row("Remise", "- " + _fmt_money(totaux.remise_ht or 0))
            _add_total_row("TOTAL HT NET", _fmt_money(ht_net), bold=True, blue=True)
        else:
            _add_total_row("TOTAL HT",  _fmt_money(totaux.total_ht), bold=True, blue=True)
        if has_acompte:
            ht_base = totaux.total_ht_net if totaux.total_ht_net else totaux.total_ht
            _add_total_row("Acompte vers\xe9", "- " + _fmt_money(devis.acompte or 0))
            net = totaux.net_a_payer if totaux.net_a_payer else max(0, ht_base - (devis.acompte or 0))
            _add_total_row_green("NET A PAYER", _fmt_money(net))

    sep4 = doc.add_paragraph()
    _zero_para_spacing(sep4)

    # ── MENTIONS LÉGALES ─────────────────────────────────────────────
    sep5 = doc.add_paragraph("─" * 90)
    _zero_para_spacing(sep5)

    for mention in devis.mentions_legales:
        p = doc.add_paragraph(f"• {mention}")
        _zero_para_spacing(p)
        p.runs[0].font.size = Pt(8)
        p.runs[0].font.color.rgb = GRAY

    if not with_tva:
        p = doc.add_paragraph("• TVA non applicable, art. 293 B du CGI")
        _zero_para_spacing(p)
        p.runs[0].font.size = Pt(8)
        p.runs[0].font.bold = True

    # ── COORDONNÉES BANCAIRES ─────────────────────────────────────────
    if devis.artisan.iban or devis.artisan.bic:
        sep6 = doc.add_paragraph("─" * 90)
        _zero_para_spacing(sep6)
        p = doc.add_paragraph()
        _zero_para_spacing(p)
        _run(p, "Coordonnées bancaires", size=10, color=BLUE, bold=True)
        if devis.artisan.iban:
            p2 = doc.add_paragraph(f"IBAN : {devis.artisan.iban}")
            _zero_para_spacing(p2)
            p2.runs[0].font.size = Pt(9)
        if devis.artisan.bic:
            p3 = doc.add_paragraph(f"BIC/SWIFT : {devis.artisan.bic}")
            _zero_para_spacing(p3)
            p3.runs[0].font.size = Pt(9)

    # ── ZONE DE SIGNATURE ────────────────────────────────────────────
    sep_sig = doc.add_paragraph()
    _zero_para_spacing(sep_sig)

    sig_tbl = doc.add_table(rows=1, cols=2)
    sig_tbl.autofit = False
    sig_tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
    _fix_table(sig_tbl, width_cm=PAGE_W_CM)
    sig_tbl.columns[0].width = Cm(8.0)
    sig_tbl.columns[1].width = Cm(9.0)

    def _sig_cell(cell, title: str, lines: list):
        from docx.oxml.ns import qn as _qn
        from docx.oxml import OxmlElement as _el
        # Bordure fine sur la cellule
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        tcBorders = _el("w:tcBorders")
        for side in ("top", "left", "bottom", "right"):
            b = _el(f"w:{side}")
            b.set(_qn("w:val"), "single")
            b.set(_qn("w:sz"), "4")
            b.set(_qn("w:color"), "CCCCCC")
            tcBorders.append(b)
        tcPr.append(tcBorders)

        p = cell.paragraphs[0]
        _zero_para_spacing(p)
        _run(p, title, size=9, color=BLUE, bold=True)
        for line in lines:
            pl = cell.add_paragraph()
            _zero_para_spacing(pl)
            _run(pl, line, size=8, color=GRAY)
        # Espace vide pour la signature
        for _ in range(3):
            pe = cell.add_paragraph()
            _zero_para_spacing(pe)

    _sig_cell(
        sig_tbl.cell(0, 0),
        "Bon pour accord",
        ["Fait à : _________________________________",
         "Le : _______ / _______ / ___________"],
    )
    _sig_cell(
        sig_tbl.cell(0, 1),
        "Signature du client",
        [],
    )

    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()
