"""Build the proposal and final report as Word and PDF files.

    python scripts/build_documents.py            # both documents
    python scripts/build_documents.py report     # only the report
    python scripts/build_documents.py proposal   # only the proposal

Layout follows the FAST School of Computing report format: cover page with the
university logo, a black page border on every page, Times New Roman, centred
underlined title on page 2, numbered bold underlined headings, bold table
captions above black-bordered tables, italic figure captions and centred page
numbers. The PDF is exported by Microsoft Word (COM automation through
PowerShell), so the DOCX and PDF have the same layout.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Emu, Pt, RGBColor, Twips

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
LOGO = REPORTS / "assets" / "nu_logo.png"
DOCS = {
    "report": (REPORTS / "final_report.md", REPORTS / "final_report"),
    "proposal": (ROOT / "docs" / "proposal.md", ROOT / "docs" / "proposal"),
}
FONT = "Times New Roman"
BLACK = RGBColor(0, 0, 0)
FIGURE_WIDTH_CM = {"policy_overview.png": 15.0, "type_change.png": 15.5, "strategy_medium.png": 15.0,
                   "evolutionary.png": 12.0, "tree_ch_game.png": 14.0, "tree_memory.png": 15.5}


# --------------------------------------------------------------------- helpers
def runs(par, text: str, size: float | None = None, bold=None, italic=None, underline=None):
    """Inline parser for **bold**, *italic* and `code`."""
    for tok in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)", text):
        if not tok:
            continue
        if tok.startswith("**"):
            r = par.add_run(tok[2:-2]); r.bold = True
        elif tok.startswith("*"):
            r = par.add_run(tok[1:-1]); r.italic = True
        elif tok.startswith("`"):
            r = par.add_run(tok[1:-1]); r.font.name = "Consolas"; r.font.size = Pt(9.5)
            continue
        else:
            r = par.add_run(tok)
        if size:
            r.font.size = Pt(size)
        if bold is not None:
            r.bold = bold
        if italic is not None:
            r.italic = italic
        if underline is not None:
            r.underline = underline


def para(doc, text="", size=None, align=None, after=None, before=None, bold=None, italic=None, underline=None):
    p = doc.add_paragraph()
    if text:
        runs(p, text, size, bold, italic, underline)
    if align is not None:
        p.alignment = align
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    if before is not None:
        p.paragraph_format.space_before = Pt(before)
    return p


def set_page_layout(section):
    section.page_height, section.page_width = Twips(16838), Twips(11906)   # A4
    section.top_margin = section.left_margin = section.right_margin = Twips(1440)
    section.bottom_margin = Twips(1300)
    sect = section._sectPr
    borders = OxmlElement("w:pgBorders")
    borders.set(qn("w:offsetFrom"), "page")
    for side in ("top", "left", "bottom", "right"):
        b = OxmlElement(f"w:{side}")
        b.set(qn("w:val"), "single"); b.set(qn("w:sz"), "18"); b.set(qn("w:space"), "24"); b.set(qn("w:color"), "000000")
        borders.append(b)
    # pgBorders must come after pgMar in the schema order
    pg_mar = sect.find(qn("w:pgMar"))
    pg_mar.addnext(borders)


def add_page_number(section):
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for kind, txt in (("begin", None), (None, "PAGE"), ("end", None)):
        r = p.add_run()
        if kind:
            fc = OxmlElement("w:fldChar"); fc.set(qn("w:fldCharType"), kind); r._r.append(fc)
        else:
            it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = txt; r._r.append(it)
        r.font.size = Pt(11)


def style_document(doc):
    normal = doc.styles["Normal"]
    normal.font.name = FONT; normal.font.size = Pt(11); normal.font.color.rgb = BLACK
    rpr = normal.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(attr), FONT)
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing = 1.1
    for name, size, before, after in (("Heading 1", 14, 11, 5), ("Heading 2", 12, 7, 3)):
        hs = doc.styles[name]
        hs.font.name = FONT; hs.font.size = Pt(size); hs.font.bold = True; hs.font.italic = False
        hs.font.color.rgb = BLACK
        hrpr = hs.element.get_or_add_rPr()
        hf = hrpr.find(qn("w:rFonts"))
        if hf is None:
            hf = OxmlElement("w:rFonts"); hrpr.insert(0, hf)
        for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
            hf.set(qn(attr), FONT)
        for theme in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
            if hf.get(qn(theme)) is not None:
                del hf.attrib[qn(theme)]
        hs.paragraph_format.space_before = Pt(before); hs.paragraph_format.space_after = Pt(after)
        hs.paragraph_format.keep_with_next = True


def cover_page(doc, meta):
    C = WD_ALIGN_PARAGRAPH.CENTER
    para(doc, "National University of Computer and Emerging", 22, C, after=0, bold=True)
    para(doc, "Sciences, Islamabad", 22, C, after=10, bold=True)
    para(doc, "FAST School of Computing", 22, C, after=15, bold=True)
    p = doc.add_paragraph(); p.alignment = C; p.paragraph_format.space_after = Pt(15)
    p.add_run().add_picture(str(LOGO), width=Emu(1663700))
    para(doc, "", after=6)
    para(doc, meta["cover_title"], 24, C, after=3, bold=True)
    para(doc, meta["cover_subtitle"], 14, C, after=13)
    para(doc, "", after=4)
    para(doc, "Submitted by:", 21, C, after=8, bold=True)
    members = [m.strip() for m in meta["team"].split(";")]
    for i, m in enumerate(members):
        para(doc, m, 16, C, after=15 if i == len(members) - 1 else 3)
    para(doc, "", after=2)
    para(doc, meta["degree"], 21, C, after=10, bold=True)
    day, rest = re.match(r"(\d+)(.*)", meta["date"]).groups()
    suffix = "th" if 10 <= int(day) % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(int(day) % 10, "th")
    p = doc.add_paragraph(); p.alignment = C; p.paragraph_format.space_after = Pt(10)
    for text, sup in (("Date of Submission: " + day, False), (suffix, True), (rest, False)):
        r = p.add_run(text); r.italic = True; r.font.size = Pt(21); r.font.superscript = sup
    para(doc, "", after=2)
    para(doc, "Lecturer:", 21, C, after=6, bold=True)
    para(doc, meta["lecturer"], 21, C, after=0)
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def title_block(doc, meta):
    for line in meta["title_lines"].split("|"):
        p = para(doc, line.strip(), 18, WD_ALIGN_PARAGRAPH.CENTER, after=0, bold=True, underline=True)
        p.paragraph_format.line_spacing = 1.0
    para(doc, meta["title_note"], 12, WD_ALIGN_PARAGRAPH.CENTER, before=4, after=10, italic=True)


def cell_borders(cell):
    tc_pr = cell._tc.get_or_add_tcPr()
    b = OxmlElement("w:tcBorders")
    for side in ("top", "left", "bottom", "right"):
        e = OxmlElement(f"w:{side}")
        e.set(qn("w:val"), "single"); e.set(qn("w:sz"), "4"); e.set(qn("w:space"), "0"); e.set(qn("w:color"), "000000")
        b.append(e)
    tc_pr.append(b)
    mar = OxmlElement("w:tcMar")
    for side, w in (("top", 40), ("left", 70), ("bottom", 40), ("right", 70)):
        e = OxmlElement(f"w:{side}"); e.set(qn("w:w"), str(w)); e.set(qn("w:type"), "dxa"); mar.append(e)
    tc_pr.append(mar)


def add_table(doc, rows):
    header, body = rows[0], rows[2:]
    t = doc.add_table(rows=1 + len(body), cols=len(header))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    numeric = [bool(body) and all(re.fullmatch(r"[−+\-\d.,%() /a-zA-Z]*", r[i].replace("**", "")) is not None
                                  and any(ch.isdigit() for ch in r[i]) for r in body if r[i].strip())
               for i in range(len(header))]
    for ri, row in enumerate([header] + body):
        for ci, val in enumerate(row):
            c = t.rows[ri].cells[ci]
            cell_borders(c)
            p = c.paragraphs[0]
            p.paragraph_format.space_after = Pt(0); p.paragraph_format.line_spacing = 1.0
            runs(p, val.replace("**", "") if ri == 0 else val, 9.5, bold=True if ri == 0 else None)
            if ri > 0 and numeric[ci] and ci > 0:
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    # Column widths in proportion to their longest entry (text width 15.9 cm)
    t.autofit = False
    longest = [max(len(r[ci].replace("**", "")) for r in [header] + body) for ci in range(len(header))]
    weights = [min(max(n, 5), 60) for n in longest]
    total = sum(weights)
    for ci, w in enumerate(weights):
        width = Cm(15.9 * w / total)
        for row in t.rows:
            row.cells[ci].width = width
    tr_pr = t.rows[0]._tr.get_or_add_trPr()
    hdr = OxmlElement("w:tblHeader"); tr_pr.append(hdr)
    para(doc, "", after=2).paragraph_format.line_spacing = 0.6


# --------------------------------------------------------------------- main
def build(kind: str) -> Path:
    src, out = DOCS[kind]
    text = src.read_text(encoding="utf-8")
    fm = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    meta = dict(re.findall(r'^(\w+):\s*"(.*)"$', fm.group(1), re.M))
    body = text[fm.end():]

    doc = Document()
    sec = doc.sections[0]
    set_page_layout(sec)
    add_page_number(sec)
    style_document(doc)
    cover_page(doc, meta)
    title_block(doc, meta)

    lines = body.split("\n")
    table_buf: list[list[str]] = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if line.startswith("|"):
            table_buf.append([c.strip() for c in line.strip("|").split("|")])
            i += 1
            if i >= len(lines) or not lines[i].startswith("|"):
                add_table(doc, table_buf); table_buf = []
            continue
        if line.startswith("<!--"):
            i += 1
            continue
        if line.startswith("# "):
            title = line[2:]
            if title.startswith("References") or title.startswith("Appendix"):
                doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
            h = doc.add_heading(level=1)
            r = h.add_run(title); r.underline = True; r.font.color.rgb = BLACK
        elif line.startswith("## "):
            h = doc.add_heading(level=2)
            r = h.add_run(line[3:]); r.font.color.rgb = BLACK
        elif m := re.match(r"!\[(.*?)\]\((.*?)\)", line):
            cap, path = m.groups()
            img = (src.parent / path).resolve()
            p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.keep_with_next = True; p.paragraph_format.space_after = Pt(2)
            p.add_run().add_picture(str(img), width=Cm(FIGURE_WIDTH_CM.get(img.name, 14)))
            para(doc, cap, 10, WD_ALIGN_PARAGRAPH.CENTER, after=8, italic=True)
        elif line.startswith("* ") or line.startswith("- "):
            p = doc.add_paragraph(style="List Bullet")
            runs(p, line[2:])
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.space_after = Pt(2.5); p.paragraph_format.line_spacing = 1.05
        elif line.strip().startswith("*U = "):
            para(doc, line.strip(), align=WD_ALIGN_PARAGRAPH.CENTER)
        elif re.match(r"^\*\*Table \d", line):
            p = para(doc, line.replace("**", ""), 10, before=5, after=3, bold=True)
            p.paragraph_format.keep_with_next = True
        elif line.strip():
            p = doc.add_paragraph()
            runs(p, line.strip())
            if re.match(r"^\[\d+\]", line):
                p.paragraph_format.left_indent = Cm(0.7)
                p.paragraph_format.first_line_indent = Cm(-0.7)
                p.paragraph_format.space_after = Pt(4)
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        i += 1

    props = doc.core_properties
    props.author = ", ".join(m.split(" (")[0].strip() for m in meta["team"].split(";"))
    props.title = f'{meta["cover_title"]}: {meta["cover_subtitle"]}'
    props.comments = ""
    docx_path = out.with_suffix(".docx")
    doc.save(docx_path)
    print(f"wrote {docx_path.relative_to(ROOT)}")
    return docx_path


def to_pdf(docx_path: Path) -> Path:
    pdf_path = docx_path.with_suffix(".pdf")
    ps = (
        "$w = New-Object -ComObject Word.Application; $w.Visible = $false; "
        f"$d = $w.Documents.Open('{docx_path}'); "
        f"$d.ExportAsFixedFormat('{pdf_path}', 17); $d.Close($false); $w.Quit()"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
    print(f"wrote {pdf_path.relative_to(ROOT)}")
    return pdf_path


def page_report(pdf_path: Path) -> None:
    from pypdf import PdfReader
    r = PdfReader(str(pdf_path))
    starts = {}
    for n, page in enumerate(r.pages, start=1):
        t = page.extract_text() or ""
        for key in ("References", "Appendix A"):
            if key not in starts and re.search(rf"(^|\n){key}", t):
                starts[key] = n
    total = len(r.pages)
    end = starts.get("References", total + 1) - 1
    print(f"  {pdf_path.name}: {total} pages; cover p.1; body pages 2-{end} ({end - 1} pages)"
          + (f"; references p.{starts['References']}" if "References" in starts else "")
          + (f"; appendix from p.{starts['Appendix A']}" if "Appendix A" in starts else ""))


if __name__ == "__main__":
    kinds = [a for a in sys.argv[1:] if a in DOCS] or list(DOCS)
    for k in kinds:
        path = build(k)
        if "--no-pdf" not in sys.argv:
            page_report(to_pdf(path))
