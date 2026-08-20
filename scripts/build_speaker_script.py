#!/usr/bin/env python3
"""Build the Project Compass speaker script (Elements 3–7) as a Word document."""

from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

NAVY = RGBColor(0x08, 0x2B, 0x46)
GOLD = RGBColor(0x8C, 0x6A, 0x22)
INK = RGBColor(0x03, 0x15, 0x22)
MUTED = RGBColor(0x5B, 0x6B, 0x80)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
PALE = "F5EDD9"
NAVY_HEX = "082B46"
ROW_ALT = "E7EFF4"

OUT = Path(__file__).resolve().parents[1] / "ONR_ITSS_Databricks_Speaker_Script.docx"


def _shade(cell, hex_color: str) -> None:
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), hex_color)
    shd.set(qn("w:val"), "clear")
    tcPr.append(shd)


def _set_run(run, *, bold=False, italic=False, size=11, color=INK, font="Calibri"):
    run.bold = bold
    run.italic = italic
    run.font.size = Pt(size)
    run.font.color.rgb = color
    run.font.name = font
    r = run._element
    rPr = r.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), font)
    rFonts.set(qn("w:hAnsi"), font)


def p(doc, text="", *, bold=False, italic=False, size=11, color=INK, space_after=8, space_before=0, align=None):
    para = doc.add_paragraph()
    para.paragraph_format.space_after = Pt(space_after)
    para.paragraph_format.space_before = Pt(space_before)
    para.paragraph_format.line_spacing = 1.15
    if align:
        para.alignment = align
    if text:
        r = para.add_run(text)
        _set_run(r, bold=bold, italic=italic, size=size, color=color)
    return para


def mixed(doc, parts, *, space_after=8, space_before=0):
    para = doc.add_paragraph()
    para.paragraph_format.space_after = Pt(space_after)
    para.paragraph_format.space_before = Pt(space_before)
    para.paragraph_format.line_spacing = 1.15
    for text, kw in parts:
        r = para.add_run(text)
        _set_run(r, **kw)
    return para


def heading(doc, text, level=1):
    para = doc.add_paragraph()
    para.paragraph_format.space_before = Pt(16 if level == 1 else 12)
    para.paragraph_format.space_after = Pt(6)
    r = para.add_run(text)
    _set_run(r, bold=True, size=16 if level == 1 else 13, color=NAVY if level == 1 else GOLD)
    if level == 1:
        pPr = para._p.get_or_add_pPr()
        pBdr = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), "12")
        bottom.set(qn("w:space"), "4")
        bottom.set(qn("w:color"), "8C6A22")
        pBdr.append(bottom)
        pPr.append(pBdr)
    return para


def do_this(doc, text):
    para = doc.add_paragraph()
    para.paragraph_format.space_before = Pt(8)
    para.paragraph_format.space_after = Pt(8)
    para.paragraph_format.left_indent = Inches(0.15)
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), PALE)
    shd.set(qn("w:val"), "clear")
    para._p.get_or_add_pPr().append(shd)
    r1 = para.add_run("[DO THIS]  ")
    _set_run(r1, bold=True, italic=True, size=11, color=GOLD)
    r2 = para.add_run(text)
    _set_run(r2, italic=True, size=11, color=INK)
    return para


def speak(doc, text):
    return p(doc, text, size=11, color=INK, space_after=8)


def table(doc, headers, rows, col_widths=None):
    tbl = doc.add_table(rows=1 + len(rows), cols=len(headers))
    tbl.style = "Table Grid"
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        cell = tbl.rows[0].cells[i]
        cell.text = ""
        para = cell.paragraphs[0]
        r = para.add_run(h)
        _set_run(r, bold=True, size=10, color=WHITE)
        _shade(cell, NAVY_HEX)
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = tbl.rows[ri + 1].cells[ci]
            cell.text = ""
            para = cell.paragraphs[0]
            r = para.add_run(str(val))
            _set_run(r, bold=(ci == 0), size=10, color=INK)
            if ri % 2 == 1:
                _shade(cell, ROW_ALT)
    if col_widths:
        for row in tbl.rows:
            for i, w in enumerate(col_widths):
                row.cells[i].width = Inches(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(8)
    return tbl


def set_header_footer(doc):
    section = doc.sections[0]
    section.top_margin = Inches(0.85)
    section.bottom_margin = Inches(0.8)
    section.left_margin = Inches(0.9)
    section.right_margin = Inches(0.9)
    header = section.header
    header.is_linked_to_previous = False
    hp = header.paragraphs[0]
    hp.clear()
    r = hp.add_run("ONR ITSS Factor 3  ·  Project Compass  ·  Code 08 portfolio")
    _set_run(r, bold=True, size=9, color=GOLD)
    hp.alignment = WD_ALIGN_PARAGRAPH.LEFT
    footer = section.footer
    footer.is_linked_to_previous = False
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = fp.add_run("Project Compass speaker script  ·  Elements 3–7  ·  page ")
    _set_run(r, size=9, color=MUTED)
    fld = OxmlElement("w:fldChar")
    fld.set(qn("w:fldCharType"), "begin")
    r2 = fp.add_run()
    r2._r.append(fld)
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    r3 = fp.add_run()
    r3._r.append(instr)
    _set_run(r3, size=9, color=MUTED)
    fld2 = OxmlElement("w:fldChar")
    fld2.set(qn("w:fldCharType"), "end")
    r4 = fp.add_run()
    r4._r.append(fld2)


def build():
    doc = Document()
    set_header_footer(doc)

    p(
        doc,
        "ONR ITSS  ·  Factor 3 Technical Demonstration",
        bold=True,
        size=11,
        color=GOLD,
        space_after=2,
        align=WD_ALIGN_PARAGRAPH.CENTER,
    )
    p(
        doc,
        "Project Compass Speaker Script",
        bold=True,
        size=26,
        color=NAVY,
        space_after=4,
        align=WD_ALIGN_PARAGRAPH.CENTER,
    )
    p(
        doc,
        "Code 08 portfolio  ·  Elements 3–7, with a brief Element 2 inventory",
        italic=True,
        size=12,
        color=MUTED,
        space_after=4,
        align=WD_ALIGN_PARAGRAPH.CENTER,
    )
    p(
        doc,
        "Word-for-word  ·  roman is what you say  ·  gold is what you click",
        size=11,
        color=INK,
        space_after=14,
        align=WD_ALIGN_PARAGRAPH.CENTER,
    )

    heading(doc, "Night before — not recorded")
    bullets = [
        "Workspace Git folder: git pull main. Redeploy / restart onr-demo-poc.",
        "Start onr demo warehouse, onr demo cluster (your 04 / 04b), and onr demo ml (app Score). Leave them running.",
        "Compass Home = live 400, not fixture. If fixture: sql/grant_app_principal.sql + warehouse CAN USE for the app service principal.",
        "If silver ≠ 400: run 05_reset_demo.py on onr demo cluster.",
        "Run 04_mlflow_grant_model.py, then 04b_funding_anomaly.py. Champion alias on funding_anomaly_detector. Do not train on camera.",
        "onr demo ml: Dedicated to the app SP, mlflow library installed, app SP has CAN RESTART + CAN ATTACH TO.",
        "Volume /Volumes/onr_demo/bronze/landing/_staged/batch_live_grants.csv exists.",
        "Mute notifications. 1920×1080, zoom 110–125%, hide bookmarks.",
        "Open Compass on Home. Do not Restore baseline. Do not unpause file-arrival. Do not retrain.",
    ]
    for b in bullets:
        para = doc.add_paragraph(style="List Number")
        para.clear()
        r = para.add_run(b)
        _set_run(r, size=11)
        para.paragraph_format.space_after = Pt(3)

    heading(doc, "Home")
    do_this(
        doc,
        "Recording starts with Compass open on Home. Do not open Architecture. Do not linger on Access.",
    )
    speak(
        doc,
        "This is Project Compass — Code 08’s portfolio console. Four hundred synthetic grants, about four hundred thirty-seven million dollars. All mock. No CUI, no PII, nothing classified. Let me show you the estate real quick, then we’ll take a file.",
    )
    do_this(doc, "Click Infrastructure.")

    heading(doc, "Infrastructure  ·  Element 2, briefly")
    do_this(
        doc,
        "Cursor on Estate. Three tiles: warehouse, score cluster, file-arrival job. Do not open Inventory, Identity, or Full bundle. Do not look for a Deploy button — there is not one.",
    )
    speak(
        doc,
        "Quick beat on Element two. This is the inventory of what we deployed from version control — we didn’t provision it from this screen. Warehouse serving the console. Score cluster dedicated to the application identity, not to me. File-arrival is paused. There’s no Deploy button in here. Config gets reviewed in Git, not clicked in a console. File’s waiting — let’s take it.",
    )
    do_this(doc, "Click Ingestion. Do not return to Infrastructure.")

    heading(doc, "Ingestion  ·  Element 3  ·  prompts (a) and (d)")
    speak(
        doc,
        "Element three is data operations. A grants file showed up. I’m not recoding a pipeline to take it. Inbound grants is the good file. Quarantine sample is the three bad rows — empty grant number, negative amount, and a duplicate. I’ll take both so you can see publish and hold in the same pass.",
    )
    do_this(
        doc,
        "Confirm both Inbound grants and Quarantine sample are selected. Click Ingest selected files. Keep talking.",
    )
    speak(
        doc,
        "While that’s landing — this is prompt (a), the legacy footprint. We’re not cutting over the D-and-A Portal, the reporting stack, or the existing ETL this weekend. Strangler-fig. New files go to a governed landing zone. This button and the file-arrival path I’m about to start both write the same bronze table. Legacy reports keep reading the serving layer over a standard connection. When a report’s ready to retire, we point it at the table this console already uses. Rollback is delete-the-batch, not rewrite-the-estate.",
    )
    do_this(
        doc,
        "Point at Active grants 400 → 408 and Quarantined +3. Point at the Hold tray — chips empty, dup, amt.",
    )
    speak(
        doc,
        "There it is. Eight published. Those three never entered landing — they’re held. Empty, dup, amt. One of the live grants went through with a warning, missing abstract. Quality tab’s there if you want the scoreboard. We don’t need it.",
    )
    speak(
        doc,
        "Same Element three. That was the warehouse path. Next is file arrival. I’m staying right here.",
    )
    do_this(
        doc,
        "Click Start stream. Do not Restore baseline — that control is at the bottom of the page and is not on this tape. If bronze does not tick, Workspace strip 01b stream, Run all, come straight back.",
    )
    speak(
        doc,
        "Console just dropped a new file into the landing zone and loaded it into the same bronze table. That’s file-arrival, not a scheduled batch. Open stream notebook is there if you want the job. We’re not waiting on a cold start.",
    )
    do_this(doc, "Point at bronze count, last 2 min, last file ago, then Delta time travel.")
    speak(
        doc,
        "Bronze ticks. Silver — the trusted table — stays at four hundred and eight. It dedupes on grant number, so we don’t double-count the same award.",
    )
    speak(
        doc,
        "That’s also prompt (d), disaster recovery. Contract is RPO fifteen minutes on the serving layer, essentially zero on landing, because the file’s still sitting in object storage. Time travel is the row-level RPO — baseline versus now. We’re not restoring on camera. RTO thirty minutes to serving gold, about five to serving the app. Annual DR is non-disruptive: pause file-arrival, restore yesterday’s gold into a side catalog, point a clone of the console at it, validate, tear down. Let’s look at lineage on those eight.",
    )
    do_this(doc, "Click Catalog. Do not return to Ingestion.")

    heading(doc, "Catalog  ·  Element 4  ·  prompt (e)")
    speak(
        doc,
        "Element four is governance. I want you to see the graph, not a picture we drew in this console.",
    )
    do_this(
        doc,
        "Click Open lineage · gold.grants_summary. That is the only workspace jump. If the graph is empty, open gold.grants_summary from the same explorer. Come back immediately.",
    )
    speak(
        doc,
        "That’s the catalog’s own graph. Landing, bronze, silver, gold, this console. That’s the Element four visual. This screen is the operator surface, not the system of record.",
    )
    do_this(doc, "Back on Catalog — Registry. Show bronze, silver, gold, app.")
    speak(
        doc,
        "Four schemas. The eight we just took in are already registered. Source file, ingest time, tags — on the table, not in a spreadsheet.",
    )
    do_this(doc, "Quality tab. Point at the health scores. Do not open every expander.")
    speak(
        doc,
        "Completeness, accuracy, consistency, timeliness. If a vendor feed lapses, you see it here as a timeliness drop — not a blank dashboard.",
    )
    do_this(doc, "Policies and tags. Point at data_source = mock.")
    speak(
        doc,
        "And that’s prompt (e), vendor and lifecycle. Every external feed is a licensed product — owner, renewal date, quality SLO. Today the tags are data_source, domain, data_sensitivity. In production we add vendor, license_id, renewal_date. Usage is metered on every search and every export. If a subscription stops, nothing new lands. Last-good gold stays. We don’t auto-delete. Let’s score what we just took in.",
    )
    do_this(doc, "Click Analytics. Do not return to Catalog.")

    heading(doc, "Analytics  ·  Element 5  ·  prompt (b)")
    speak(
        doc,
        "Element five is decision support. Models were trained last night and registered in the catalog. I’m not retraining. I’m scoring the portfolio we just ingested — including those eight.",
    )
    do_this(
        doc,
        "Click Score registered models. Point at Scores — Fund, Review, Defer, Flagged. Do not hunt tabs first. If the run does not submit, Workspace strip 04c score, Run all, come straight back. Keep talking.",
    )
    speak(
        doc,
        "That button scores from models already in the catalog. It doesn’t train. While it runs — this is prompt (b), financial and budgetary integration. Execution is a first-class feed. Twelve hundred ERP lines: budget, actual, execution rate. Three models, all on this same portfolio, not a second dataset.",
    )
    speak(
        doc,
        "Descriptive is the page a resource officer actually opens — dollars, execution, ON_TARGET, WARNING, AT_RISK. That’s Portfolio, next.",
    )
    speak(
        doc,
        "Predictive: a Random Forest that returns Fund, Review, or Defer on large awards. An IsolationForest for budget spike, execution collapse, and low-return concentration. And ordinary least squares — two-year horizon, ninety-five percent band, TREND-ACCEL, TREND-STEADY, TREND-DECLINE. That’s OLS, not Prophet.",
    )
    speak(
        doc,
        "Prescriptive: protect ON_TARGET, move dollars off AT_RISK and TREND-DECLINE, review large-award concentration. Engineer owns landing and trusted. Scientist owns the registered models. Analyst owns the serving layer and the daily brief. Same catalog.",
    )
    do_this(doc, "Point at Resource action. Then Drift — program-mix PSI, award-size PSI, Fund share.")
    speak(
        doc,
        "That’s feature and score mix versus the baseline snapshot — not a fake accuracy drop. The live grants moved the mix.",
    )
    do_this(
        doc,
        "Predictions tab. Point at model_name. Then Anomalies. Then Forecasting — orange horizon and one TREND-DECLINE row. Skip Metrics.",
    )
    speak(
        doc,
        "Resource action is the sentence a resource officer would sign — Defer dollars off one area onto AT_RISK plus TREND-DECLINE. That declining program is the reallocation candidate. Let’s look at it the way they would.",
    )
    do_this(doc, "Click Portfolio. Do not return to Analytics.")

    heading(doc, "Portfolio  ·  Element 6")
    speak(
        doc,
        "Element six — this is the officer view. Nobody here needs SQL. Active grants is still four hundred and eight.",
    )
    do_this(
        doc,
        "Search box on this page. Type quantum. Press enter. Point at Routing. Accept or Defer one flagged grant.",
    )
    speak(
        doc,
        "Search is live against the serving layer, and it writes a history row. That’s the audit Zero Trust asked for, and it’s the usage meter for prompt (e).",
    )
    do_this(doc, "Click Generate daily brief. Wait for the letterhead. Stay on this page.")
    speak(
        doc,
        "That’s the morning book, without a staffer writing it. Classification banner, three bullets, one recommended action. A row lands in the brief log.",
    )
    do_this(doc, "Budget tab. Point at one AT_RISK row. Then click Export.")
    speak(
        doc,
        "Same serving layer the forecast used. AT_RISK plus TREND-DECLINE is the reallocation set. Last stop — get it out of here in an open format.",
    )

    heading(doc, "Export  ·  Element 7  ·  prompt (c)")
    speak(doc, "Element seven is interoperability. Filtered extract — not every column, every year.")
    do_this(
        doc,
        "Date range is already 2025 to 2026. Leave CSV and Parquet on. Dataset Grants Summary. Click Execute export. Download Parquet or CSV once. Stay on this screen.",
    )
    speak(
        doc,
        "Open formats — CSV, JSON, Parquet. Schema travels with the file: grant number, program area, amount, awardee.",
    )
    do_this(doc, "Open History. Point at the new row.")
    speak(doc, "Who, what, filter, row count. Continuous authorization — not a static password file.")
    do_this(
        doc,
        "Click Execute live Statement API call. Point at the statement receipt — statement_id, SUCCEEDED, row_count, warehouse, elapsed.",
    )
    speak(
        doc,
        "That’s the documented SQL REST contract. Short-lived token, same warehouse this dashboard uses. That’s what Advana or Cloud One would call. Not a vendor-only extract, not a fictional host. And that’s prompt (c), Zero Trust and IL5. Three planes, same identity. The application has its own service principal; it doesn’t borrow mine. Warehouse and cluster are separate compute — micro-segmentation at the control plane. The catalog is the data-plane firewall. Least privilege: analysts read gold, they never see bronze. This cell is unclassified mock on commercial AWS, FedRAMP Moderate. The IL5 production cell is GovCloud, PrivateLink, customer-managed keys, continuous compliance against the same least-privilege grants. We’re not claiming this POC is IL5.",
    )
    speak(
        doc,
        "Tomorrow another file lands in the same landing zone. Same gold. Same registered models — we rescore from this console. Mock data only.",
    )
    do_this(doc, "Stop talking. Leave Export on screen.")

    doc.save(OUT)
    print("wrote", OUT, "bytes", OUT.stat().st_size)


if __name__ == "__main__":
    build()
