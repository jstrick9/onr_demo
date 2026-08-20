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
        "One Key Personnel  ·  live console  ·  no slides  ·  mock data only",
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
        "This is Project Compass, the Code 08 portfolio console. Four hundred synthetic grants, four hundred thirty-seven million dollars. Everything on this tape is mock data. No CUI, no PII, no classified.",
    )
    do_this(doc, "Click Infrastructure.")

    heading(doc, "Infrastructure  ·  Element 2, briefly")
    do_this(
        doc,
        "Cursor on Estate. Three tiles: warehouse, score cluster, file-arrival job. Do not open Inventory, Identity, or Full bundle. Do not look for a Deploy button — there is not one.",
    )
    speak(doc, "Element two: infrastructure as code.")
    speak(
        doc,
        "This page is the inventory of the estate that was deployed from version control. It is not a second provision. The warehouse serves this console. The score cluster is dedicated to the application identity, not to me. File-arrival is paused. There is no Deploy button in this console. Configuration is reviewed in Git, not clicked here.",
    )
    do_this(doc, "Click Ingestion. Do not return to Infrastructure.")

    heading(doc, "Ingestion  ·  Element 3  ·  prompts (a) and (d)")
    speak(doc, "Element three: automated ingestion, data operations, and streaming.")
    speak(
        doc,
        "A new grants file has arrived. I am not recoding a pipeline. Inbound grants is the good file. Quarantine sample is three bad rows — empty grant number, negative amount, and a duplicate.",
    )
    do_this(
        doc,
        "Confirm both Inbound grants and Quarantine sample are selected. Click Ingest selected files. Keep talking.",
    )
    speak(doc, "Strategic prompt (a) — sustainment of the legacy footprint.")
    speak(
        doc,
        "We do not cut over the D-and-A Portal, the reporting stack, or the existing ETL in a weekend. The pattern is strangler-fig coexistence. New files land in a governed landing zone. Both the path this button just used and the file-arrival path I will start next write the same bronze table — the landing table. Legacy reports keep reading the serving layer over a standard connection. When a report is ready to retire, we point it at the table this console already uses. Rollback is delete-the-batch, not rewrite-the-estate.",
    )
    do_this(
        doc,
        "Point at Active grants 400 → 408 and Quarantined +3. Point at the Hold tray — chips empty, dup, amt.",
    )
    speak(
        doc,
        "Eight rows published. The three quarantine rows never entered the landing table — they are held. One live grant published with a warning, missing abstract. Quality is the tab if a reviewer wants the scoreboard. We do not need it here.",
    )
    speak(
        doc,
        "Same Element three. That button was the warehouse path. Next is file arrival. I am not leaving this console.",
    )
    do_this(
        doc,
        "Click Start stream. Do not Restore baseline — that control is at the bottom of the page and is not on this tape. If bronze does not tick, Workspace strip 01b stream, Run all, come straight back.",
    )
    speak(
        doc,
        "The console just landed a new file and loaded it into the same bronze table. That is file-arrival, not a scheduled batch. Open stream notebook is there if a reviewer wants the job. We do not wait on a cold start.",
    )
    do_this(doc, "Point at bronze count, last 2 min, last file ago, then Delta time travel.")
    speak(
        doc,
        "Bronze ticks. Silver — the trusted table — stays at four hundred and eight because it dedupes on grant number. The serving layer does not double-count the same award.",
    )
    speak(doc, "Strategic prompt (d) — disaster recovery, resilience, and failover.")
    speak(
        doc,
        "Contract targets: RPO fifteen minutes for the serving layer, essentially zero for landing — the file is still sitting in object storage. Time travel is the row-level RPO — baseline snapshot versus now. We are not restoring on camera. RTO thirty minutes to serving gold, about five minutes to serving the app. Annual DR is non-disruptive: pause file-arrival, restore yesterday’s gold into a side catalog, point a clone of the console at it, validate, tear down.",
    )
    do_this(doc, "Click Catalog. Do not return to Ingestion.")

    heading(doc, "Catalog  ·  Element 4  ·  prompt (e)")
    speak(doc, "Element four: data governance, quality, and cataloging.")
    do_this(
        doc,
        "Click Open lineage · gold.grants_summary. That is the only workspace jump. If the graph is empty, open gold.grants_summary from the same explorer. Come back immediately.",
    )
    speak(
        doc,
        "Open lineage is the catalog’s native graph — landing, to bronze, to silver, to gold, to this console. That graph is the Element four visual. This console is the operator surface, not the system of record.",
    )
    do_this(doc, "Back on Catalog — Registry. Show bronze, silver, gold, app.")
    speak(
        doc,
        "Four schemas. The eight grants we just ingested are already registered. Metadata — source file, ingest time, tags — is on the table, not in a spreadsheet.",
    )
    do_this(doc, "Quality tab. Point at the health scores. Do not open every expander.")
    speak(
        doc,
        "Completeness, accuracy, consistency, timeliness. A lapsed vendor feed shows up here as a timeliness drop, not a blank dashboard.",
    )
    do_this(doc, "Policies and tags. Point at data_source = mock.")
    speak(doc, "Strategic prompt (e) — data vendor and lifecycle management.")
    speak(
        doc,
        "Every external feed is a licensed product: owner, renewal date, quality SLO. Today the tags are data_source, domain, data_sensitivity. In production we add vendor, license_id, renewal_date. Usage is metered on every search and every export. If a subscription stops, nothing new lands. Last-good gold stays. We do not auto-delete.",
    )
    do_this(doc, "Click Analytics. Do not return to Catalog.")

    heading(doc, "Analytics  ·  Element 5  ·  prompt (b)")
    speak(doc, "Element five: decision-support analytics and modeling.")
    speak(
        doc,
        "The models were trained last night and registered in the catalog. I am not retraining on camera. I am triggering a live score against the portfolio we just ingested — including the eight new grants.",
    )
    do_this(
        doc,
        "Click Score registered models. Point at Scores — Fund, Review, Defer, Flagged. Do not hunt tabs first. If the run does not submit, Workspace strip 04c score, Run all, come straight back. Keep talking.",
    )
    speak(
        doc,
        "Score registered models — that button scores the current portfolio from models already in the catalog. It does not train.",
    )
    speak(doc, "Strategic prompt (b) — financial and budgetary analytical integration.")
    speak(
        doc,
        "Financial execution is a first-class feed: twelve hundred ERP lines — budget, actual, execution rate. Three complementary models, all on this ingested portfolio, not a second dataset.",
    )
    speak(
        doc,
        "Descriptive: the Portfolio page a Code 08 resource officer opens — dollars, execution, ON_TARGET, WARNING, AT_RISK.",
    )
    speak(
        doc,
        "Predictive: a Random Forest large-award classifier — Fund, Review, or Defer. An IsolationForest for budget spike, execution collapse, and low-return concentration. And ordinary least squares, two-year horizon, ninety-five percent band, trend IDs TREND-ACCEL, TREND-STEADY, TREND-DECLINE. That is OLS, not Prophet.",
    )
    speak(
        doc,
        "Prescriptive: protect ON_TARGET, move dollars off AT_RISK and TREND-DECLINE, review large-award concentration. Engineer owns landing and trusted. Scientist owns the registered models. Analyst owns the serving layer and the daily brief. Same catalog.",
    )
    do_this(doc, "Point at Resource action. Then Drift — program-mix PSI, award-size PSI, Fund share.")
    speak(
        doc,
        "That is feature and score mix versus the baseline snapshot, not a fake accuracy drop. The live grants moved the mix.",
    )
    do_this(
        doc,
        "Predictions tab. Point at model_name. Then Anomalies. Then Forecasting — orange horizon and one TREND-DECLINE row. Skip Metrics.",
    )
    speak(
        doc,
        "The Resource action sentence is the close a resource officer would sign — Defer dollars off one area onto AT_RISK plus TREND-DECLINE. The declining program is the reallocation candidate on the next page.",
    )
    do_this(doc, "Click Portfolio. Do not return to Analytics.")

    heading(doc, "Portfolio  ·  Element 6")
    speak(doc, "Element six: unified dashboard, visualizations, and process automation.")
    speak(doc, "A non-technical leader does not need SQL. Active grants is still four hundred and eight.")
    do_this(
        doc,
        "Search box on this page. Type quantum. Press enter. Point at Routing. Accept or Defer one flagged grant.",
    )
    speak(
        doc,
        "Search is live against the serving layer. It is written to the search history. That is the audit Zero Trust asked for, and it is the usage meter for prompt (e).",
    )
    do_this(doc, "Click Generate daily brief. Wait for the letterhead. Stay on this page.")
    speak(
        doc,
        "Generate daily brief — automated summary. Classification banner, three bullets, one recommended action. A row lands in the brief log. That is process automation — not a staffer writing the morning book.",
    )
    do_this(doc, "Budget tab. Point at one AT_RISK row. Then click Export.")
    speak(
        doc,
        "Same serving layer the forecast used. AT_RISK plus TREND-DECLINE is the reallocation set. Extract is next.",
    )

    heading(doc, "Export  ·  Element 7  ·  prompt (c)")
    speak(doc, "Element seven: interoperability, data portability, and secure export.")
    do_this(
        doc,
        "Date range is already 2025 to 2026. Leave CSV and Parquet on. Dataset Grants Summary. Click Execute export. Download Parquet or CSV once. Stay on this screen.",
    )
    speak(
        doc,
        "Filtered bulk extract — not every column, every year. Open formats: CSV, JSON, Parquet. Schema travels with the file: grant number, program area, amount, awardee.",
    )
    do_this(doc, "Open History. Point at the new row.")
    speak(
        doc,
        "Export history — who, what, filter, row count. Continuous authorization, not a static password file.",
    )
    do_this(
        doc,
        "Click Execute live Statement API call. Point at the statement receipt — statement_id, SUCCEEDED, row_count, warehouse, elapsed.",
    )
    speak(
        doc,
        "Execute live Statement API call — that is the documented SQL REST contract. Short-lived token, same warehouse this dashboard uses. That is what Advana or Cloud One would call. It is not a vendor-only extract and it is not a fictional host.",
    )
    speak(doc, "Strategic prompt (c) — Zero Trust and IL5.")
    speak(
        doc,
        "Three planes, same identity. The application has its own service principal; it does not borrow mine. The warehouse and the cluster are separate compute — micro-segmentation at the control plane. The catalog is the data-plane firewall. Least privilege: analysts read gold, they never see bronze. This cell is unclassified mock on commercial AWS — FedRAMP Moderate. The IL5 production cell is GovCloud, PrivateLink, customer-managed keys, continuous compliance against the same least-privilege grants. We are not claiming this POC is IL5.",
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
