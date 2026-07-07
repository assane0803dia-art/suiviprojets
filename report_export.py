"""
Convertit un rapport texte (format Markdown simple : ## titres, - listes) en fichiers
Word (.docx) et PDF téléchargeables.
"""

import io
from docx import Document
from docx.shared import Pt, RGBColor
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm


def _parse_lines(report_text):
    """Découpe le rapport en lignes typées : (type, texte) où type est 'h2', 'bullet' ou 'p'."""
    parsed = []
    for raw_line in report_text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("## "):
            parsed.append(("h2", line[3:].strip()))
        elif line.startswith("# "):
            parsed.append(("h1", line[2:].strip()))
        elif line.startswith("- ") or line.startswith("• "):
            parsed.append(("bullet", line[2:].strip()))
        else:
            parsed.append(("p", line))
    return parsed


def export_to_docx(report_text: str, projet_nom: str) -> bytes:
    doc = Document()

    title = doc.add_heading(f"Rapport d'exécution — {projet_nom}", level=0)

    for kind, text in _parse_lines(report_text):
        if kind == "h1":
            doc.add_heading(text, level=1)
        elif kind == "h2":
            doc.add_heading(text, level=2)
        elif kind == "bullet":
            doc.add_paragraph(text, style="List Bullet")
        else:
            doc.add_paragraph(text)

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def export_to_pdf(report_text: str, projet_nom: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleCustom", parent=styles["Title"], fontSize=16, spaceAfter=16)
    h2_style = ParagraphStyle("H2Custom", parent=styles["Heading2"], spaceBefore=12, spaceAfter=6)
    bullet_style = ParagraphStyle("BulletCustom", parent=styles["Normal"], leftIndent=14, spaceAfter=4)
    normal_style = ParagraphStyle("NormalCustom", parent=styles["Normal"], spaceAfter=6)

    story = [Paragraph(f"Rapport d'exécution — {projet_nom}", title_style), Spacer(1, 6)]

    for kind, text in _parse_lines(report_text):
        if kind in ("h1", "h2"):
            story.append(Paragraph(text, h2_style))
        elif kind == "bullet":
            story.append(Paragraph(f"• {text}", bullet_style))
        else:
            story.append(Paragraph(text, normal_style))

    doc.build(story)
    return buffer.getvalue()
