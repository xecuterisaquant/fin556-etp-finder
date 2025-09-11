from __future__ import annotations
from typing import List, Dict
import os, textwrap
from reportlab.lib.pagesizes import LETTER, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, LongTable, Table, TableStyle, PageBreak, XPreformatted
from reportlab.lib.units import inch

MONO = "Courier"

def _header_footer(canvas, doc):
    canvas.saveState()
    w, h = landscape(LETTER)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(0.6 * inch, 0.4 * inch, "FIN556 ETP Scanner — Generated Report")
    canvas.drawRightString(w - 0.6 * inch, 0.4 * inch, f"Page {doc.page}")
    canvas.restoreState()

def _section_title(text: str):
    return Paragraph(f"<b>{text}</b>", getSampleStyleSheet()["Heading2"])

def _h3(text: str):
    return Paragraph(f"<b>{text}</b>", getSampleStyleSheet()["Heading3"])

def build_assignment_pdf(
    out_pdf_path: str,
    netid: str,
    records: List[Dict[str, str]],
    code_paths: List[str],
    run_meta: Dict[str, str],
):
    # Single, consistent page size across the whole document
    PAGE_SIZE = landscape(LETTER)
    doc = SimpleDocTemplate(
        out_pdf_path,
        pagesize=PAGE_SIZE,
        leftMargin=36, rightMargin=36, topMargin=48, bottomMargin=42
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Mono", fontName=MONO, fontSize=7.2, leading=8.2, wordWrap="CJK"))
    styles.add(ParagraphStyle(name="Small", fontSize=9, leading=11))
    styles.add(ParagraphStyle(name="Wrap", fontSize=7.6, leading=8.8, wordWrap="CJK"))
    styles.add(ParagraphStyle(name="WrapMono", fontName=MONO, fontSize=7.2, leading=8.2, wordWrap="CJK"))

    story = []
    story.append(Paragraph(f"{netid}_fin556_algo_trading_symbols_homework", styles["Title"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Automated NASDAQ ETP Scanner — Output and Source Code", styles["Italic"]))
    story.append(Spacer(1, 10))

    # Summary
    story.append(_section_title("Summary"))
    story.append(Paragraph(f"Total matches: <b>{len(records)}</b>", styles["BodyText"]))
    story.append(Spacer(1, 6))

    # Category counts
    cats = {}
    for r in records:
        cats[r.get("category","unknown")] = cats.get(r.get("category","unknown"), 0) + 1
    if cats:
        summary_rows = [["Category", "Count"]] + [[k, v] for k, v in sorted(cats.items(), key=lambda x: (-x[1], x[0]))]
        t = Table(summary_rows, colWidths=[4.0*inch, 1.0*inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f1f3f5")),
            ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#ced4da")),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("ALIGN", (1,1), (-1,-1), "RIGHT"),
            ("FONTSIZE", (0,0), (-1,-1), 9),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ]))
        story.append(t)

    # Run metadata
    story.append(Spacer(1, 10))
    story.append(_section_title("Run metadata"))
    meta_lines = [f"{k}: {v}" for k, v in run_meta.items()]
    story.append(XPreformatted("\n".join(meta_lines), styles["Mono"]))
    story.append(Spacer(1, 8))

    # Detected symbols table (ALL columns wrapped; includes serial #)
    story.append(_section_title("Detected Symbols (Full List)"))
    header = ["#", "symbol", "name", "etp_type", "category", "reasons", "timestamp"]
    table_data = [header]

    for i, r in enumerate(records, start=1):
        idx = Paragraph(str(i), styles["Wrap"])
        symbol = Paragraph(str(r.get("symbol","")), styles["Wrap"])
        name = Paragraph(str(r.get("name","")), styles["Wrap"])
        etp_type = Paragraph(str(r.get("etp_type","")), styles["Wrap"])
        category = Paragraph(str(r.get("category","")), styles["Wrap"])
        reasons = r.get("reasons", [])
        if isinstance(reasons, list):
            reasons_txt = ", ".join(reasons)
        else:
            reasons_txt = str(reasons)
        reasons_para = Paragraph(reasons_txt, styles["Wrap"])
        timestamp = Paragraph(str(r.get("timestamp","")), styles["Wrap"])
        table_data.append([idx, symbol, name, etp_type, category, reasons_para, timestamp])

    # === FIT TABLE TO PAGE WIDTH (no overflow) ===
    # Use exact fractions of doc.width so the table ALWAYS fits within margins.
    # Fractions sum to 1.0 → widths sum to doc.width (≈ 10 inches on landscape Letter with 0.5" margins).
    fractions = [
        0.03,  # #
        0.09,  # symbol
        0.30,  # name
        0.08,  # etp_type
        0.14,  # category
        0.28,  # reasons
        0.08,  # timestamp
    ]
    avail = doc.width  # width between margins
    col_widths = [avail * f for f in fractions]

    lt = LongTable(table_data, colWidths=col_widths, repeatRows=1, splitByRow=1)
    lt.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f1f3f5")),
        ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#ced4da")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 7.6),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 3),
        ("RIGHTPADDING", (0,0), (-1,-1), 3),
        ("TOPPADDING", (0,0), (-1,-1), 1.5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 1.5),
    ]))
    story.append(lt)

    # Code listing
    story.append(PageBreak())
    story.append(_section_title("Source Code (Full Listing)"))
    story.append(Paragraph("Note: lines are wrapped for readability.", styles["Small"]))
    story.append(Spacer(1, 6))

    wrap_width = 110  # soft wrap for code blocks on landscape pages
    for p in code_paths:
        story.append(_h3(os.path.relpath(p)))
        with open(p, "r", encoding="utf-8") as f:
            code = f.read()
        wrapped_lines = []
        for line in code.splitlines():
            if len(line) <= wrap_width:
                wrapped_lines.append(line)
            else:
                indent = len(line) - len(line.lstrip(" "))
                prefix = " " * indent
                chunks = textwrap.wrap(
                    line.rstrip("\n"),
                    width=wrap_width,
                    subsequent_indent=prefix,
                    break_long_words=False,
                    break_on_hyphens=False
                )
                wrapped_lines.extend(chunks)
        wrapped_code = "\n".join(wrapped_lines)
        story.append(XPreformatted(wrapped_code, styles["Mono"]))
        story.append(Spacer(1, 8))

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
