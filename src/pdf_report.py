
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
    canvas.drawString(0.6 * inch, 0.4 * inch, f"FIN556 ETP Scanner — Generated Report")
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
    # Use a single, consistent page size across all pages
    PAGE_SIZE = landscape(LETTER)
    doc = SimpleDocTemplate(
        out_pdf_path,
        pagesize=PAGE_SIZE,
        leftMargin=36, rightMargin=36, topMargin=48, bottomMargin=42
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Mono", fontName=MONO, fontSize=7.4, leading=8.5, wordWrap="CJK"))
    styles.add(ParagraphStyle(name="Small", fontSize=9, leading=11))
    styles.add(ParagraphStyle(name="Wrap", fontSize=8, leading=9.5, wordWrap="CJK"))
    styles.add(ParagraphStyle(name="WrapMono", fontName=MONO, fontSize=7.4, leading=8.5, wordWrap="CJK"))

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
        t = Table(summary_rows, colWidths=[4.2*inch, 1.0*inch])
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

    # Detected symbols table
    story.append(_section_title("Detected Symbols (Full List)"))

    # Header now includes a serial number column
    header = ["#", "symbol", "name", "etp_type", "category", "reasons", "timestamp"]
    table_data = [header]

    # Wrap EVERY column to prevent overflow/overlap
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

    # Column widths tuned for landscape Letter; ensure all fit comfortably
    col_widths = [
        0.4*inch,   # #
        0.8*inch,   # symbol
        3.2*inch,   # name
        0.9*inch,   # etp_type
        1.5*inch,   # category
        3.9*inch,   # reasons
        1.6*inch,   # timestamp
    ]

    lt = LongTable(table_data, colWidths=col_widths, repeatRows=1, splitByRow=1)
    lt.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f1f3f5")),
        ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#ced4da")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 2),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
    ]))
    story.append(lt)

    # New page for code listing, same fixed page size
    story.append(PageBreak())
    story.append(_section_title("Source Code (Full Listing)"))
    story.append(Paragraph("Note: lines are wrapped for readability.", styles["Small"]))
    story.append(Spacer(1, 6))

    wrap_width = 110  # soft wrap in code
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
