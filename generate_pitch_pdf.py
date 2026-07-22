"""
BobSentry Hackathon Pitch PDF Generator
Produces a 3-page IBM-styled pitch document for the WatsonX Challenge July 2026.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.graphics.shapes import Drawing, Rect, Line, Polygon, String
from reportlab.graphics import renderPDF

# ── Colour palette (IBM brand) ─────────────────────────────────────────────
IBM_BLUE    = colors.HexColor("#0F62FE")
IBM_DARK    = colors.HexColor("#161616")
IBM_GRAY_80 = colors.HexColor("#393939")
IBM_GRAY_60 = colors.HexColor("#6F6F6F")
IBM_GRAY_20 = colors.HexColor("#DDE1E6")
IBM_GRAY_10 = colors.HexColor("#F4F4F4")
IBM_RED     = colors.HexColor("#DA1E28")
IBM_GREEN   = colors.HexColor("#24A148")
IBM_TEAL    = colors.HexColor("#009D9A")
IBM_PURPLE  = colors.HexColor("#8A3FFC")
IBM_YELLOW  = colors.HexColor("#F1C21B")
WHITE       = colors.white

W, H = A4  # 595.27 x 841.89 pt

# ── Style helpers ─────────────────────────────────────────────────────────

def style(name, **kw):
    base = getSampleStyleSheet()[name]
    return ParagraphStyle(name + "_custom", parent=base, **kw)

TITLE_STYLE   = style("Title",    fontSize=26, textColor=WHITE,
                       leading=32, spaceAfter=4, fontName="Helvetica-Bold")
SUBTITLE_STYLE= style("Normal",   fontSize=13, textColor=IBM_GRAY_20,
                       leading=17, spaceAfter=0, fontName="Helvetica")
H1            = style("Heading1", fontSize=14, textColor=IBM_BLUE,
                       leading=18, spaceBefore=10, spaceAfter=4,
                       fontName="Helvetica-Bold")
H2            = style("Heading2", fontSize=11, textColor=IBM_DARK,
                       leading=14, spaceBefore=6, spaceAfter=2,
                       fontName="Helvetica-Bold")
BODY          = style("Normal",   fontSize=9,  textColor=IBM_GRAY_80,
                       leading=13, spaceAfter=4, fontName="Helvetica")
BODY_SM       = style("Normal",   fontSize=8,  textColor=IBM_GRAY_80,
                       leading=11, spaceAfter=2, fontName="Helvetica")
LABEL         = style("Normal",   fontSize=7.5,textColor=IBM_GRAY_60,
                       leading=10, spaceAfter=1, fontName="Helvetica-Bold")
BIG_NUM       = style("Normal",   fontSize=30, textColor=IBM_BLUE,
                       leading=34, spaceAfter=0, fontName="Helvetica-Bold",
                       alignment=TA_CENTER)
BIG_CAP       = style("Normal",   fontSize=8,  textColor=IBM_GRAY_60,
                       leading=11, spaceAfter=6, fontName="Helvetica",
                       alignment=TA_CENTER)
FOOTER_ST     = style("Normal",   fontSize=7,  textColor=IBM_GRAY_60,
                       leading=9,  fontName="Helvetica",
                       alignment=TA_RIGHT)

# ── Page template with header bar + footer ────────────────────────────────

def on_page(canvas, doc):
    canvas.saveState()
    # Top IBM-blue bar
    canvas.setFillColor(IBM_BLUE)
    canvas.rect(0, H - 6*mm, W, 6*mm, fill=1, stroke=0)
    # Footer rule
    canvas.setStrokeColor(IBM_GRAY_20)
    canvas.setLineWidth(0.5)
    canvas.line(15*mm, 12*mm, W - 15*mm, 12*mm)
    # Footer text
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(IBM_GRAY_60)
    canvas.drawString(15*mm, 8*mm, "BobSentry  ·  WatsonX Challenge July 2026")
    canvas.drawRightString(W - 15*mm, 8*mm, f"Page {doc.page}")
    canvas.restoreState()

def build_doc(path):
    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=16*mm, bottomMargin=18*mm,
        title="BobSentry — Hackathon Pitch",
        author="WatsonX Challenge 2026",
    )

    story = []
    _page1(story)
    story.append(PageBreak())
    _page2(story)
    story.append(PageBreak())
    _page3(story)

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"✅  PDF written → {path}")

# ═════════════════════════════════════════════════════════════════════════════
# PAGE 1 — Problem, Solution, Bob Usage
# ═════════════════════════════════════════════════════════════════════════════

def _page1(story):
    # Hero banner
    d = Drawing(W - 30*mm, 38*mm)
    d.add(Rect(0, 0, W - 30*mm, 38*mm, fillColor=IBM_DARK, strokeColor=None))
    d.add(Rect(0, 0, 6*mm, 38*mm,       fillColor=IBM_BLUE, strokeColor=None))
    d.add(String(10*mm, 22*mm, "BobSentry",
                 fontSize=28, fillColor=colors.white, fontName="Helvetica-Bold"))
    d.add(String(10*mm, 12*mm, "Semi-autonomous AI security triage for IAM projects",
                 fontSize=11, fillColor=IBM_GRAY_20, fontName="Helvetica"))
    d.add(String(10*mm, 4*mm,  "WatsonX Challenge · July 2026",
                 fontSize=8,  fillColor=IBM_GRAY_60, fontName="Helvetica"))
    story.append(d)
    story.append(Spacer(1, 5*mm))

    # ── The Problem ────────────────────────────────────────────────────────
    story.append(Paragraph("The Problem", H1))
    story.append(HRFlowable(width="100%", thickness=1, color=IBM_GRAY_20, spaceAfter=3))
    story.append(Paragraph(
        "Security teams triaging open-source IAM vulnerabilities face a three-part bottleneck:",
        BODY))

    prob_data = [
        ["⏱", "Time",     "3–5 hours per CVE — reading the issue, spinning up a sandbox,\nwriting exploit scripts, and classifying the result manually."],
        ["🔁", "Repeat",   "No artefact reuse — each engineer starts from scratch even when\nthe attack class was seen last week."],
        ["🔒", "Risk",     "Inconsistent guardrails — real credentials, live endpoints, and\npersistent containers create compliance and data-leak exposure."],
    ]
    prob_tbl = Table(prob_data, colWidths=[8*mm, 18*mm, W - 30*mm - 8*mm - 18*mm - 8*mm])
    prob_tbl.setStyle(TableStyle([
        ("FONTNAME",    (0,0),(-1,-1), "Helvetica"),
        ("FONTSIZE",    (0,0),(-1,-1), 8.5),
        ("FONTNAME",    (0,0),(1,-1),  "Helvetica-Bold"),
        ("TEXTCOLOR",   (1,0),(1,-1),  IBM_BLUE),
        ("TEXTCOLOR",   (2,0),(2,-1),  IBM_GRAY_80),
        ("VALIGN",      (0,0),(-1,-1), "TOP"),
        ("TOPPADDING",  (0,0),(-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1),3),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[IBM_GRAY_10, WHITE]),
        ("LEADING",     (0,0),(-1,-1), 12),
    ]))
    story.append(prob_tbl)
    story.append(Spacer(1, 4*mm))

    # ── The Solution ───────────────────────────────────────────────────────
    story.append(Paragraph("The Solution — BobSentry", H1))
    story.append(HRFlowable(width="100%", thickness=1, color=IBM_GRAY_20, spaceAfter=3))
    story.append(Paragraph(
        "BobSentry converts a raw GitHub issue number into a structured verdict — "
        "<b>confirmed / patch-verified / escalated</b> — with reproducible scripts, "
        "a live sandbox execution log, CVSS v3.1 score, and a Markdown report, all without "
        "touching production systems. A single slash command does everything:",
        BODY))

    cmd_data = [["<font name='Courier-Bold' size='10' color='#0F62FE'>"
                 "/triage &lt;github-repo-url&gt; &lt;issue-number&gt;</font>"]]
    cmd_tbl = Table(cmd_data, colWidths=[W - 30*mm])
    cmd_tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0,0),(-1,-1), IBM_DARK),
        ("TEXTCOLOR",   (0,0),(-1,-1), IBM_BLUE),
        ("LEFTPADDING", (0,0),(-1,-1), 8),
        ("TOPPADDING",  (0,0),(-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1),5),
    ]))
    story.append(cmd_tbl)
    story.append(Spacer(1, 4*mm))

    # ── How Bob Was Used ──────────────────────────────────────────────────
    story.append(Paragraph("How IBM Bob Powered This", H1))
    story.append(HRFlowable(width="100%", thickness=1, color=IBM_GRAY_20, spaceAfter=3))

    bob_rows = [
        ["Bob Capability",         "How BobSentry Uses It"],
        ["Custom Modes",           "Security Sentry mode loads guardrails, CVE knowledge base,\nand multi-model routing automatically on activation."],
        ["Skills (CVE Analyzer)",  "6-step pattern engine scores the issue against 5 trained CVE\nprofiles and 20-class vulnerability matrix; outputs threat JSON."],
        ["Slash Commands",         "/triage drives a 6-step pipeline across Plan → Code → Agent\nmodes without manual orchestration."],
        ["Multi-Mode Orchestration","Plan mode produces a 4-stage triage plan (awaits approval);\nCode mode generates exploit scripts (awaits review);\nAgent mode runs sandbox, captures logs, tears it all down."],
        ["Skills (Env Manager)",   "Declarative Podman/Docker sandbox lifecycle — spin-up,\nhealthcheck, teardown — all within the triage session."],
        ["Artefact Accumulation",  "Each session writes context.json + scripts to an attack-class\nfolder; future triages read prior artefacts as scaffolding,\nprogressively reducing script iterations."],
    ]
    bob_tbl = Table(bob_rows,
                    colWidths=[45*mm, W - 30*mm - 45*mm - 4*mm],
                    spaceBefore=0)
    bob_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,0),  IBM_BLUE),
        ("TEXTCOLOR",    (0,0),(-1,0),  WHITE),
        ("FONTNAME",     (0,0),(-1,0),  "Helvetica-Bold"),
        ("FONTNAME",     (0,1),(-1,-1), "Helvetica"),
        ("FONTSIZE",     (0,0),(-1,-1), 8),
        ("LEADING",      (0,0),(-1,-1), 11),
        ("VALIGN",       (0,0),(-1,-1), "TOP"),
        ("TOPPADDING",   (0,0),(-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
        ("LEFTPADDING",  (0,0),(-1,-1), 5),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[IBM_GRAY_10, WHITE]),
        ("GRID",         (0,0),(-1,-1), 0.25, IBM_GRAY_20),
    ]))
    story.append(bob_tbl)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 2 — Pipeline Flow Diagram + Productivity Impact
# ═════════════════════════════════════════════════════════════════════════════

def _page2(story):
    story.append(Paragraph("6-Step Triage Pipeline", H1))
    story.append(HRFlowable(width="100%", thickness=1, color=IBM_GRAY_20, spaceAfter=4))

    # Flow diagram as a drawing
    dw = W - 30*mm
    dh = 52*mm
    d = Drawing(dw, dh)

    steps = [
        ("1", "Fetch Issue",    "gh issue view\n(read-only)",    IBM_BLUE),
        ("2", "CVE Analyzer",   "Pattern match\n5 CVE profiles", IBM_TEAL),
        ("3", "Triage Plan",    "Plan mode\n⏸ Approval",         IBM_PURPLE),
        ("4", "Script Gen",     "Code mode\n⏸ Review",           IBM_PURPLE),
        ("5", "Sandbox Run",    "Agent mode\nDocker + logs",     IBM_GREEN),
        ("6", "Retrospective",  "KB update\n⏸ Approval",         IBM_GRAY_60),
    ]

    bw = (dw - 5*mm) / 6
    bh = 26*mm
    by = 22*mm

    for i, (num, title, detail, col) in enumerate(steps):
        x = i * bw
        # box
        d.add(Rect(x + 1, by, bw - 2, bh,
                   fillColor=col, strokeColor=WHITE, strokeWidth=0.5,
                   rx=2, ry=2))
        # step number circle
        d.add(Rect(x + 2, by + bh - 8, 7, 7,
                   fillColor=WHITE, strokeColor=None, rx=3, ry=3))
        d.add(String(x + 3, by + bh - 5.5, num,
                     fontSize=5.5, fillColor=col, fontName="Helvetica-Bold"))
        # title
        d.add(String(x + 3, by + bh - 17, title,
                     fontSize=7.5, fillColor=WHITE, fontName="Helvetica-Bold"))
        # detail (first line only to save space)
        lines = detail.split("\n")
        for li, ln in enumerate(lines):
            d.add(String(x + 3, by + bh - 25 - li * 8, ln,
                         fontSize=6.5, fillColor=IBM_GRAY_20, fontName="Helvetica"))

        # arrow between boxes
        if i < 5:
            ax = x + bw - 1
            ay = by + bh / 2
            d.add(Line(ax, ay, ax + 2, ay,
                       strokeColor=IBM_GRAY_20, strokeWidth=1))
            # arrowhead
            d.add(Polygon([ax+2, ay, ax, ay-2, ax, ay+2],
                          fillColor=IBM_GRAY_20, strokeColor=None))

    # Sandbox isolation label
    d.add(Rect(3*bw + 1, 1, 2*bw - 2, 18,
               fillColor=IBM_GRAY_10, strokeColor=IBM_GRAY_20,
               strokeWidth=0.5, rx=2, ry=2))
    d.add(String(3*bw + 4, 6,
                 "🐳  Isolated Docker sandbox  ·  docker compose down -v on exit",
                 fontSize=6.5, fillColor=IBM_GRAY_60, fontName="Helvetica"))

    story.append(d)
    story.append(Spacer(1, 3*mm))

    # ── Productivity Impact ───────────────────────────────────────────────
    story.append(Paragraph("Productivity Impact — 5 Confirmed Triage Sessions", H1))
    story.append(HRFlowable(width="100%", thickness=1, color=IBM_GRAY_20, spaceAfter=4))

    # Big-number KPIs
    kpi_data = [
        [Paragraph("~18 min", BIG_NUM), Paragraph("~3 hrs", BIG_NUM),
         Paragraph("16.1 hrs", BIG_NUM), Paragraph("94%", BIG_NUM)],
        [Paragraph("Avg triage time\n(Bob-Sentry)", BIG_CAP),
         Paragraph("Avg manual\nbaseline", BIG_CAP),
         Paragraph("Total time\nsaved (5 issues)", BIG_CAP),
         Paragraph("Time saving\nper issue", BIG_CAP)],
    ]
    kpi_tbl = Table(kpi_data, colWidths=[(W-30*mm)/4]*4)
    kpi_tbl.setStyle(TableStyle([
        ("ALIGN",        (0,0),(-1,-1), "CENTER"),
        ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",   (0,0),(-1,-1), 2),
        ("BOTTOMPADDING",(0,0),(-1,-1), 2),
        ("BACKGROUND",   (0,0),(-1,0),  IBM_GRAY_10),
        ("GRID",         (0,0),(-1,-1), 0.25, IBM_GRAY_20),
    ]))
    story.append(kpi_tbl)
    story.append(Spacer(1, 4*mm))

    # Per-session table
    story.append(Paragraph("Per-Session Results", H2))
    session_data = [
        ["Issue",   "Attack Class",                    "CVE",              "Severity",  "Triage Time", "Saved"],
        ["#49915",  "Blind SSRF — CIBA Backchannel",   "CVE-2026-1518",    "HIGH",      "~8 min",      "~1.4 h"],
        ["#49570",  "DoS — OTel Baggage (novel)",      "CVE-2026-45292",   "IMPORTANT", "~15 min",     "~2.9 h"],
        ["#50445",  "Privilege Esc — Role Mapper",     "CVE-2026-4629",    "BLOCKER 🔴","~15 min",     "~3.3 h"],
        ["#50983",  "AuthZ Bypass — FGAP flow leak",   "none assigned",    "MEDIUM",    "~17 min",     "~2.7 h"],
        ["#50981",  "AuthZ Bypass — FGAP session leak","none assigned",    "MEDIUM",    "~20 min",     "~2.7 h"],
    ]
    col_w = [(W-30*mm)*f for f in [0.10, 0.32, 0.17, 0.13, 0.14, 0.14]]
    s_tbl = Table(session_data, colWidths=col_w)
    s_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,0),  IBM_DARK),
        ("TEXTCOLOR",    (0,0),(-1,0),  WHITE),
        ("FONTNAME",     (0,0),(-1,0),  "Helvetica-Bold"),
        ("FONTNAME",     (0,1),(-1,-1), "Helvetica"),
        ("FONTSIZE",     (0,0),(-1,-1), 7.5),
        ("LEADING",      (0,0),(-1,-1), 10),
        ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",   (0,0),(-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
        ("LEFTPADDING",  (0,0),(-1,-1), 4),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[IBM_GRAY_10, WHITE]),
        ("GRID",         (0,0),(-1,-1), 0.25, IBM_GRAY_20),
        ("TEXTCOLOR",    (3,3),(3,3),   IBM_RED),
    ]))
    story.append(s_tbl)
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph(
        "All 5 issues were MEDIUM severity or above — including one BLOCKER (CVSS 9.1) achieving full "
        "realm takeover via a single Admin API call. Two FGAP sub-variants (#50983, #50981) were "
        "confirmed in a single session using prior-session artefacts as scaffolding, demonstrating "
        "the compound learning effect as the knowledge base grows.",
        BODY_SM))

    story.append(Spacer(1, 3*mm))
    story.append(Paragraph("Portability Demonstrated", H2))
    story.append(Paragraph(
        "The same pipeline was applied to <b>Pac4j</b> (SAML/Spring Boot) and "
        "<b>Quarkus OIDC</b> — projects with different languages, protocols, and architectures — "
        "with <b>zero changes to security guardrails</b> and only minimal adaptation to setup scripts. "
        "Any HTTP-accessible auth project that runs in Docker is a candidate.",
        BODY_SM))


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 3 — Design & Usability, Creativity, Roadmap
# ═════════════════════════════════════════════════════════════════════════════

def _page3(story):
    # ── Design & Usability ────────────────────────────────────────────────
    story.append(Paragraph("Design & Usability", H1))
    story.append(HRFlowable(width="100%", thickness=1, color=IBM_GRAY_20, spaceAfter=3))

    ux_data = [
        ["Zero config",          "No env vars, no YAML edits — open the repo in Bob, switch to Security\nSentry mode, run /triage. Prerequisites: Docker, gh CLI, Python 3.9+."],
        ["Human in the loop",    "Pipeline pauses at Step 3 (triage plan), Step 4 (script review), and\nStep 6 (KB update). No autonomous code runs without engineer sign-off."],
        ["Deterministic verdicts","HTTP response codes drive verdicts (200 = vulnerable, 401/403 = patched,\n500 = escalate). No subjective interpretation; auditable by anyone."],
        ["Structured output",    "Every session produces a consistent Markdown report with CVSS v3.1\nvector, severity label, executive summary, and reproduction steps."],
        ["Safe by default",      "8 non-negotiable guardrails: localhost-only network, no real credentials,\nauto-cleanup, read-only GitHub access, pre-execution secret scan."],
    ]
    ux_tbl = Table(ux_data, colWidths=[38*mm, W - 30*mm - 38*mm - 4*mm])
    ux_tbl.setStyle(TableStyle([
        ("FONTNAME",     (0,0),(0,-1),  "Helvetica-Bold"),
        ("FONTNAME",     (1,0),(1,-1),  "Helvetica"),
        ("FONTSIZE",     (0,0),(-1,-1), 8),
        ("LEADING",      (0,0),(-1,-1), 11),
        ("TEXTCOLOR",    (0,0),(0,-1),  IBM_BLUE),
        ("TEXTCOLOR",    (1,0),(1,-1),  IBM_GRAY_80),
        ("VALIGN",       (0,0),(-1,-1), "TOP"),
        ("TOPPADDING",   (0,0),(-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
        ("LEFTPADDING",  (0,0),(-1,-1), 5),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[IBM_GRAY_10, WHITE]),
        ("GRID",         (0,0),(-1,-1), 0.25, IBM_GRAY_20),
    ]))
    story.append(ux_tbl)
    story.append(Spacer(1, 4*mm))

    # ── Creativity & Innovation ───────────────────────────────────────────
    story.append(Paragraph("Creativity & Innovation", H1))
    story.append(HRFlowable(width="100%", thickness=1, color=IBM_GRAY_20, spaceAfter=3))

    inno_data = [
        ["Multi-mode orchestration",
         "Bob's Plan / Code / Agent modes are used as specialised stages in a\n"
         "single pipeline — not just as a coding assistant. Plan writes the\n"
         "triage strategy; Code generates exploit scripts; Agent executes them.\n"
         "The modes act as a lightweight multi-agent system inside one tool."],
        ["Self-improving knowledge base",
         "After each confirmed triage, a retrospective proposes targeted updates\n"
         "to keycloak-cve-history.md and admin-api-schemas.md. Over time the\n"
         "system gets faster and produces fewer script iterations per issue."],
        ["Portable methodology",
         "Security guardrails, HTTP classification, and Docker isolation are fully\n"
         "project-agnostic. The pipeline transferred to Pac4j and Quarkus OIDC\n"
         "without rule changes — only setup scripts adapted."],
        ["CVE skill as threat oracle",
         "The CVE Analyzer skill encodes IBM-style Winning Products thinking:\n"
         "it extracts a structured threat profile before any code runs, ensuring\n"
         "the triage plan is hypothesis-driven rather than exploratory."],
    ]
    inno_tbl = Table(inno_data, colWidths=[46*mm, W - 30*mm - 46*mm - 4*mm])
    inno_tbl.setStyle(TableStyle([
        ("FONTNAME",     (0,0),(0,-1),  "Helvetica-Bold"),
        ("FONTNAME",     (1,0),(1,-1),  "Helvetica"),
        ("FONTSIZE",     (0,0),(-1,-1), 8),
        ("LEADING",      (0,0),(-1,-1), 11),
        ("TEXTCOLOR",    (0,0),(0,-1),  IBM_BLUE),
        ("TEXTCOLOR",    (1,0),(1,-1),  IBM_GRAY_80),
        ("VALIGN",       (0,0),(-1,-1), "TOP"),
        ("TOPPADDING",   (0,0),(-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
        ("LEFTPADDING",  (0,0),(-1,-1), 5),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[IBM_GRAY_10, WHITE]),
        ("GRID",         (0,0),(-1,-1), 0.25, IBM_GRAY_20),
    ]))
    story.append(inno_tbl)
    story.append(Spacer(1, 4*mm))

    # ── Roadmap ───────────────────────────────────────────────────────────
    story.append(Paragraph("Roadmap for Future Use", H1))
    story.append(HRFlowable(width="100%", thickness=1, color=IBM_GRAY_20, spaceAfter=3))

    road_data = [
        ["Horizon",     "Milestone",                                              "Impact"],
        ["Now\n(done)", "5 Keycloak CVEs triaged · Pac4j & Quarkus OIDC ported\n"
                        "· 8-rule guardrail framework · HTML report UI",
                        "Proof of concept:\n16 hrs saved in first run"],
        ["Q3 2026",     "Project template library (Spring Security, ORY Hydra,\n"
                        "Authentik) · Auto-detect framework from issue text\n"
                        "· Slack/webhook notification on confirmed BLOCKER",
                        "3–5 projects supported\nout of the box"],
        ["Q4 2026",     "CVE feed integration (NVD, OSV) — auto-open triage\n"
                        "for new disclosures matching watched projects\n"
                        "· Patch-verification re-triage triggered by PR merge",
                        "Continuous monitoring\nwith zero manual intake"],
        ["2027",        "Multi-team deployment: shared KB across security\n"
                        "teams, cross-project pattern correlation, and\n"
                        "CVSS trend dashboards for portfolio risk view",
                        "Enterprise-scale IAM\nsecurity observability"],
    ]
    col_w2 = [(W-30*mm)*f for f in [0.11, 0.60, 0.29]]
    r_tbl = Table(road_data, colWidths=col_w2)
    r_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,0),  IBM_BLUE),
        ("TEXTCOLOR",    (0,0),(-1,0),  WHITE),
        ("FONTNAME",     (0,0),(-1,0),  "Helvetica-Bold"),
        ("FONTNAME",     (0,1),(-1,-1), "Helvetica"),
        ("FONTSIZE",     (0,0),(-1,-1), 7.5),
        ("LEADING",      (0,0),(-1,-1), 10),
        ("VALIGN",       (0,0),(-1,-1), "TOP"),
        ("TOPPADDING",   (0,0),(-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
        ("LEFTPADDING",  (0,0),(-1,-1), 4),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[IBM_GRAY_10, WHITE]),
        ("GRID",         (0,0),(-1,-1), 0.25, IBM_GRAY_20),
        ("FONTNAME",     (0,1),(0,-1),  "Helvetica-Bold"),
        ("TEXTCOLOR",    (0,1),(0,-1),  IBM_BLUE),
        ("BACKGROUND",   (0,1),(0,1),   colors.HexColor("#DEFBE6")),  # green tint = done
    ]))
    story.append(r_tbl)
    story.append(Spacer(1, 5*mm))

    # Closing statement
    close_tbl = Table(
        [[Paragraph(
            "BobSentry turns a 3-hour manual CVE triage into an 18-minute, reproducible, "
            "guardrail-enforced pipeline — using IBM Bob's custom modes, skills, and "
            "multi-mode orchestration as its engine. Every artefact it produces makes the "
            "next triage faster.",
            style("Normal", fontSize=9, textColor=WHITE, leading=13,
                  fontName="Helvetica-Bold")
        )]],
        colWidths=[W - 30*mm]
    )
    close_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,-1), IBM_BLUE),
        ("TOPPADDING",   (0,0),(-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
        ("LEFTPADDING",  (0,0),(-1,-1), 10),
        ("RIGHTPADDING", (0,0),(-1,-1), 10),
    ]))
    story.append(close_tbl)


if __name__ == "__main__":
    import os
    out_dir = "pitch"
    os.makedirs(out_dir, exist_ok=True)
    build_doc(os.path.join(out_dir, "BobSentry-Pitch.pdf"))
