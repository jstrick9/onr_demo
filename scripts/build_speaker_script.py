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
        "This is Project Compass, the Code 08 portfolio console. Four hundred synthetic grants, about four hundred thirty-seven million dollars. Everything you’re looking at is mock data. No Controlled Unclassified Information, no personally identifiable information, nothing classified. Let me show you what’s actually running, then we’ll take a file.",
    )
    do_this(doc, "Click Infrastructure.")

    heading(doc, "Infrastructure  ·  Element 2, briefly")
    do_this(
        doc,
        "Cursor on Estate. Three tiles: warehouse, score cluster, file-arrival job. Do not open Inventory, Identity, or Full bundle. Do not look for a Deploy button — there is not one.",
    )
    speak(
        doc,
        "This is what’s live. The query engine this console uses, the compute that scores the models, and a file-arrival job we left paused so nothing new lands while we’re talking. That’s Element two. The infrastructure is defined in version control, and this page is just the inventory of what’s running. Let’s take the grants file.",
    )
    do_this(doc, "Click Ingestion. Do not return to Infrastructure.")

    heading(doc, "Ingestion  ·  Element 3  ·  prompts (a) and (d)")
    speak(
        doc,
        "Element three is data operations. A grants file showed up. I’m not recoding a pipeline to take it. Inbound grants is the good file. Quarantine sample is the three bad rows: empty grant number, negative amount, and a duplicate. I’ll take both so you can see publish and hold in the same pass.",
    )
    do_this(
        doc,
        "Confirm both Inbound grants and Quarantine sample are selected. Click Ingest selected files. Keep talking.",
    )
    speak(
        doc,
        "While that’s landing, this is prompt (a), the legacy footprint. We’re not cutting over the D-and-A Portal, the reporting stack, or the existing extract, transform, and load jobs this weekend. We wrap the old system instead of ripping it out. New files go to a governed landing zone. This button, and the file-arrival path I’m about to start, both write the same landing table. Legacy reports keep reading the serving layer over a standard connection. When a report is ready to retire, we point it at the table this console already uses. Rollback means we delete that batch. We don’t rebuild the whole environment.",
    )
    do_this(
        doc,
        "Point at Active grants 400 → 408 and Quarantined +3. Point at the Hold tray — chips empty, dup, amt.",
    )
    speak(
        doc,
        "There it is. Eight rows published. Those three never entered the landing table. They’re held: empty grant number, duplicate, and a bad amount. One of the live grants went through with a warning because the abstract is missing. The Quality tab is there if you want the scoreboard. We don’t need it for this.",
    )
    speak(
        doc,
        "Same Element three. That was the query path. Next is file arrival, as if the file just showed up on its own. I’m staying right here.",
    )
    do_this(
        doc,
        "Click Start stream. Do not Restore baseline — that control is at the bottom of the page and is not on this tape. If bronze does not tick, Workspace strip 01b stream, Run all, come straight back.",
    )
    speak(
        doc,
        "The console just dropped a new file into the landing zone and loaded it into the same landing table. That’s file arrival, not a scheduled batch. If you want to see the job behind it, that open-notebook control is right there. We’re not waiting on a cold start.",
    )
    do_this(doc, "Point at bronze count, last 2 min, last file ago, then Delta time travel.")
    speak(
        doc,
        "The landing count just moved. The trusted table stays at four hundred and eight because it de-duplicates on grant number, so we don’t count the same award twice.",
    )
    speak(
        doc,
        "That’s also prompt (d), disaster recovery. Recovery point objective is fifteen minutes on the serving layer, and essentially zero on landing, because the file is still sitting in object storage. Time travel lets us compare the baseline snapshot to right now, row by row. We’re not restoring on camera. Recovery time objective is thirty minutes to serving data, about five minutes to serving this console. Annual disaster recovery is non-disruptive: we pause file arrival, restore yesterday’s serving data into a side environment, point a copy of the console at it, validate, and tear it down. Let’s look at lineage on those eight.",
    )
    do_this(doc, "Click Catalog. Do not return to Ingestion.")

    heading(doc, "Catalog  ·  Element 4  ·  prompt (e)")
    speak(
        doc,
        "Element four is governance. I want you to see the real lineage graph, not a picture we drew in this console.",
    )
    do_this(
        doc,
        "Click Open lineage · gold.grants_summary. That is the only workspace jump. If the graph is empty, open gold.grants_summary from the same explorer. Come back immediately.",
    )
    speak(
        doc,
        "That’s the catalog’s own graph. Landing, to the raw table, to the trusted table, to the serving layer, to this console. That’s the Element four visual. This screen is the operator view, not the system of record.",
    )
    do_this(doc, "Back on Catalog — Registry. Show bronze, silver, gold, app.")
    speak(
        doc,
        "Four layers. The eight we just took in are already registered. Source file, ingest time, tags — on the table, not in a spreadsheet.",
    )
    do_this(doc, "Quality tab. Point at the health scores. Do not open every expander.")
    speak(
        doc,
        "Completeness, accuracy, consistency, timeliness. If a vendor feed lapses, you see it here as a timeliness drop, not a blank dashboard.",
    )
    do_this(doc, "Policies and tags. Point at data_source = mock.")
    speak(
        doc,
        "And that’s prompt (e), vendor and lifecycle. Every external feed is a licensed product: owner, renewal date, and a quality service level. Today the tags are data source, domain, and data sensitivity. In production we add vendor, license identifier, and renewal date. Usage is metered on every search and every export. If a subscription stops, nothing new lands. The last good serving data stays. We don’t auto-delete. Let’s score what we just took in.",
    )
    do_this(doc, "Click Analytics. Do not return to Catalog.")

    heading(doc, "Analytics  ·  Element 5  ·  prompt (b)")
    speak(
        doc,
        "Element five is decision support. The models were trained last night and registered in the catalog. I’m not retraining. I’m scoring the portfolio we just ingested, including those eight.",
    )
    do_this(
        doc,
        "Click Score registered models. Point at Scores — Fund, Review, Defer, Flagged. Do not hunt tabs first. If the run does not submit, Workspace strip 04c score, Run all, come straight back. Keep talking.",
    )
    speak(
        doc,
        "That button scores from models already in the catalog. It doesn’t train. While it runs, this is prompt (b), financial and budgetary integration. Execution is a first-class feed. Twelve hundred financial lines from the enterprise system: budget, actual, and execution rate. Three models, all on this same portfolio, not a second dataset.",
    )
    speak(
        doc,
        "Descriptive is the page a resource officer actually opens: dollars, execution, on target, warning, and at risk. That’s Portfolio, next.",
    )
    speak(
        doc,
        "Predictive: a random forest that returns Fund, Review, or Defer on large awards. An isolation forest for budget spike, execution collapse, and low-return concentration. And ordinary least squares: two-year horizon, ninety-five percent band, trend accelerating, trend steady, and trend declining. That’s ordinary least squares, not a neural net.",
    )
    speak(
        doc,
        "Prescriptive: protect on-target work, move dollars off at-risk and trend-declining programs, and review large-award concentration. The engineer owns landing and trusted data. The scientist owns the registered models. The analyst owns the serving layer and the daily brief. Same catalog.",
    )
    do_this(doc, "Point at Resource action. Then Drift — program-mix PSI, award-size PSI, Fund share.")
    speak(
        doc,
        "That’s feature mix and score mix versus the baseline snapshot, not a fake accuracy drop. The live grants moved the mix.",
    )
    do_this(
        doc,
        "Predictions tab. Point at model_name. Then Anomalies. Then Forecasting — orange horizon and one TREND-DECLINE row. Skip Metrics.",
    )
    speak(
        doc,
        "Resource action is the sentence a resource officer would sign: defer dollars off one area onto at-risk plus trend-declining. That declining program is the reallocation candidate. Let’s look at it the way they would.",
    )
    do_this(doc, "Click Portfolio. Do not return to Analytics.")

    heading(doc, "Portfolio  ·  Element 6")
    speak(
        doc,
        "Element six. This is the officer view. Nobody here needs to write a query. Active grants is still four hundred and eight.",
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
        "Same serving layer the forecast used. At-risk plus trend-declining is the reallocation set. Last stop: we get it out of here in an open format.",
    )

    heading(doc, "Export  ·  Element 7  ·  prompt (c)")
    speak(
        doc,
        "Element seven is interoperability. Filtered extract, not every column, every year.",
    )
    do_this(
        doc,
        "Date range is already 2025 to 2026. Leave CSV and Parquet on. Dataset Grants Summary. Click Execute export. Download Parquet or CSV once. Stay on this screen.",
    )
    speak(
        doc,
        "Open formats: comma-separated values, JSON, and Parquet. The column names travel with the file: grant number, program area, amount, awardee.",
    )
    do_this(doc, "Open History. Point at the new row.")
    speak(
        doc,
        "Who, what, filter, row count. Continuous authorization, not a static password file.",
    )
    do_this(
        doc,
        "Click Execute live Statement API call. Point at the statement receipt — statement_id, SUCCEEDED, row_count, warehouse, elapsed.",
    )
    speak(
        doc,
        "That’s the documented query interface over the web. Short-lived token, same query engine this dashboard uses. That’s what Advana or Cloud One would call. Not a vendor-only extract, not a made-up host.",
    )
    speak(
        doc,
        "And that’s prompt (c), Zero Trust and Impact Level 5. Three planes, same identity. This application has its own service identity; it doesn’t borrow mine. The query engine and the scoring compute are separate. That’s micro-segmentation at the control plane. The catalog is the data-plane firewall. Least privilege: analysts read the serving layer, they never see the landing data. This cell is unclassified mock data on commercial Amazon Web Services at the FedRAMP Moderate baseline. The Impact Level 5 production cell is government cloud, private connectivity, customer-managed keys, and continuous compliance against the same least-privilege grants. We’re not claiming this proof of concept is Impact Level 5.",
    )
    speak(
        doc,
        "Tomorrow another file lands in the same landing zone. Same serving data. Same registered models. We rescore from this console. Mock data only.",
    )
    do_this(doc, "Stop talking. Leave Export on screen.")

    doc.save(OUT)
    print("wrote", OUT, "bytes", OUT.stat().st_size)


if __name__ == "__main__":
    build()
