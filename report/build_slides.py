#!/usr/bin/env python3
"""Build the ASM II group-project presentation (report/ASM2_Group_Project_Slides.pptx).

All numbers are taken from committed results (docs/q1_report.md, results/survival/*).
Run from the repository root:  python report/build_slides.py
"""
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "report/ASM2_Group_Project_Slides.pptx"
KM = ROOT / "results/survival/km_primary.png"

NAVY, RED, GREY, LIGHT = RGBColor(0x1F, 0x2A, 0x44), RGBColor(0xC0, 0x39, 0x2B), RGBColor(0x55, 0x55, 0x55), RGBColor(0xF2, 0xF4, 0xF7)
prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]


def text(slide, x, y, w, h, lines, size=20, color=NAVY, bold_first=False, align=PP_ALIGN.LEFT):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        bullet = isinstance(line, tuple)
        content = line[0] if bullet else line
        p.text = ("•  " if bullet and line[1] == 0 else "–  " if bullet else "") + content
        p.level = line[1] if bullet else 0
        p.alignment = align
        p.space_after = Pt(8)
        for r in p.runs:
            r.font.size = Pt(size - (3 if bullet and line[1] else 0))
            r.font.color.rgb = color
            r.font.bold = bold_first and i == 0
    return box


def slide(title, notes, number=True):
    s = prs.slides.add_slide(BLANK)
    bar = s.shapes.add_shape(1, 0, 0, prs.slide_width, Inches(1.05))
    bar.fill.solid(); bar.fill.fore_color.rgb = NAVY; bar.line.fill.background()
    t = text(s, 0.5, 0.18, 12.3, 0.8, [title], size=28, color=RGBColor(0xFF, 0xFF, 0xFF))
    t.text_frame.paragraphs[0].runs[0].font.bold = True
    if number:
        text(s, 11.8, 7.0, 1.3, 0.4, [str(len(prs.slides))], size=11, color=GREY, align=PP_ALIGN.RIGHT)
    s.notes_slide.notes_text_frame.text = notes
    return s


def table(s, x, y, w, rows, col_w, size=15, bold_rows=()):
    shape = s.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(0.45 * len(rows)))
    tbl = shape.table
    for j, cw in enumerate(col_w):
        tbl.columns[j].width = Inches(cw)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = tbl.cell(i, j)
            c.text = str(val)
            para = c.text_frame.paragraphs[0]
            para.alignment = PP_ALIGN.CENTER if j else PP_ALIGN.LEFT
            run = para.runs[0]
            run.font.size = Pt(size)
            run.font.bold = i == 0 or i in bold_rows
            run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF) if i == 0 else NAVY
            c.fill.solid()
            c.fill.fore_color.rgb = NAVY if i == 0 else (LIGHT if i % 2 else RGBColor(0xFF, 0xFF, 0xFF))
    return tbl


# 1 Title
s = prs.slides.add_slide(BLANK)
bg = s.shapes.add_shape(1, 0, 0, prs.slide_width, prs.slide_height)
bg.fill.solid(); bg.fill.fore_color.rgb = NAVY; bg.line.fill.background()
W = RGBColor(0xFF, 0xFF, 0xFF)
text(s, 0.9, 1.6, 11.5, 2.2, ["Does a Pending-Sector Warning Predict Hard-Drive Failure?"], size=40, color=W).text_frame.paragraphs[0].runs[0].font.bold = True
text(s, 0.9, 3.4, 11.5, 1.0, ["A survival analysis of Backblaze Drive Stats, Q1 2026"], size=24, color=W)
text(s, 0.9, 4.8, 11.5, 1.6, ["Aayush Jha  ·  Ankit Roy  ·  Faaz Noushad",
                             "Advanced Statistical Methods II — Group Project (Type I)  ·  ISI  ·  November 2026"], size=18, color=W)
s.notes_slide.notes_text_frame.text = (
    "Introduce the team and the one-line question: does a SMART 197 'pending sector' warning on a fixed day "
    "go with a higher chance of the drive being recorded as failed over the next three months?")

# 2 Question
s = slide("Question and hypotheses", (
    "SMART 197 counts sectors the drive could not read and has queued for reallocation. Our approved proposal asked whether a "
    "pre-specified SMART indicator is associated with subsequent failure after accounting for drive age. We fix the indicator "
    "(SMART 197), the drive model and the cohort before looking at outcomes. Survival analysis is needed because most drives "
    "never fail in the window (right censoring) and some leave observation early."))
text(s, 0.7, 1.4, 12, 5.5, [
    ("Drives report SMART health counters; SMART 197 = Current Pending Sector Count (unreadable sectors awaiting reallocation)", 0),
    ("Question: is a nonzero SMART 197 on 1 Jan 2026 associated with a later recorded failure — after accounting for age?", 0),
    ("H₀: baseline SMART 197 status has no association with the subsequent failure hazard", 0),
    ("Hₐ: baseline SMART 197 status is associated with the subsequent failure hazard", 0),
    ("Survival framing: follow-up lengths differ, most drives never fail (censoring), some leave observation early", 0)], size=22)

# 3 Data
s = slide("Data: Backblaze Drive Stats, Q1 2026", (
    "Backblaze publishes a daily snapshot of every drive in its data centres. Q1 2026 is 90 daily files, about 30.6 million "
    "drive-days. We verified the archive hash and every file's checksum. We restricted to one model so that manufacturer and "
    "firmware differences cannot confound the comparison. The failure flag is Backblaze's own definition — we come back to this."))
text(s, 0.7, 1.4, 12, 5.5, [
    ("Public daily snapshots of every drive: date, serial, model, failure flag (0/1), ~90 SMART pairs", 0),
    ("Q1 2026: 90 daily files, 1 Jan – 31 Mar, 30.6 million drive-days (archive hash and all file checksums verified)", 0),
    ("One drive model only: Seagate ST12000NM0008 (12 TB) — 18,650 drives, 129 failure flags in Q1", 0),
    ("removes manufacturer / firmware / capacity differences from the comparison", 1),
    ("Outcome = Backblaze's recorded failure flag (definition matters — slide 10)", 0)], size=22)

# 4 Cohort
s = slide("Cohort, outcome and censoring", (
    "Baseline is 1 January. Only drives present that day are in the cohort, giving 18,533 drives and 111 failures. Exposure is "
    "taken from the 1 January row only, so it cannot use future information. Drives still present on 31 March are censored there. "
    "96 drives disappeared earlier without a flag: they are censored at their last day and never counted as failures. A later "
    "check showed 93 of those 96 reappeared in early April, i.e. they were data gaps."))
table(s, 0.7, 1.45, 7.6, [
    ["Baseline SMART 197", "Drives", "Failures", "Censored 31 Mar", "Exits"],
    ["= 0", "18,371", "83", "18,195", "93"],
    ["> 0", "162", "28", "131", "3"],
    ["Total", "18,533", "111", "18,326", "96"]], [2.1, 1.3, 1.2, 1.8, 1.2], bold_rows=(3,))
text(s, 8.7, 1.4, 4.3, 5.6, [
    ("Day 0 = 1 Jan 2026; follow-up to day 89", 0),
    ("Excluded: 116 later arrivals, 1 failure on day 0", 0),
    ("Event: first failure flag after day 0", 0),
    ("Unexplained exits are censored, never failures", 0),
    ("Exposure from the 1 Jan row only", 0)], size=17)
text(s, 0.7, 3.9, 7.6, 3.0, [
    ("Data checks: no duplicate drive-days, no rows after a failure, no missing baseline SMART 197 / 5 / 9", 0),
    ("10.2% of drives have an observation gap (22% in the SMART 197 > 0 group)", 0)], size=17)

# 5 Methods
s = slide("Methods", (
    "Kaplan–Meier by group with Greenwood log-log confidence intervals. One Cox model with a single binary covariate, Efron ties, "
    "Wald test for H0, and a Grambsch–Therneau proportional-hazards test. Two pre-specified sensitivity analyses and one "
    "age-adjusted model using powered-on hours, because installation dates are not published. Importantly, the rule for keeping "
    "SMART 197 versus switching to SMART 5, and the full analysis plan, were committed before we looked at failures by group."))
text(s, 0.7, 1.4, 12, 5.6, [
    ("Kaplan–Meier by baseline group; 95% CI by Greenwood, log(−log) scale", 0),
    ("Cox PH: h(t|x) = h₀(t)·exp(βx), Efron ties; Wald test of H₀: β = 0", 0),
    ("PH check: scaled-Schoenfeld test (Grambsch–Therneau) — reported, not used to change the model", 1),
    ("Sensitivity S1: 93 exits that reappeared in April → censored at day 89", 0),
    ("Sensitivity S2: remove gap days from the risk set (start–stop intervals)", 0),
    ("Age adjustment: + baseline powered years (SMART 9 ÷ 8,766), since install dates are unknown", 0),
    ("Rules and plan committed before looking at failures by group; lifelines results cross-checked in statsmodels", 0)], size=20)

# 6 KM figure
s = slide("Kaplan–Meier: drives with a pending-sector warning fail far more often", (
    "Blue: the 18,371 drives with zero pending sectors stay near 1 throughout. Red: the 162 drives with a warning drop to about "
    "0.83 by day 89. The drop is steepest in the first month. Shading is the 95% pointwise confidence band — wide for the red "
    "group because it is small."))
s.shapes.add_picture(str(KM), Inches(1.6), Inches(1.25), height=Inches(6.0))

# 7 Landmarks
s = slide("How big is the difference?", (
    "At 30 days, 90% of warned drives are still without a recorded failure versus 99.9% of the others; at 89 days, 83% versus "
    "99.5%. In absolute terms about 17 in 100 warned drives versus fewer than 1 in 200 unwarned ones. The warned group is under "
    "1% of drives but has a quarter of the failures."))
table(s, 0.7, 1.5, 11.9, [
    ["Proportion without a recorded failure", "Day 30", "Day 60", "Day 89"],
    ["SMART 197 = 0 (n = 18,371)", "0.9989", "0.9976", "0.9955 (0.9944–0.9964)"],
    ["SMART 197 > 0 (n = 162)", "0.9007", "0.8635", "0.8262 (0.7583–0.8766)"]], [4.6, 2.0, 2.0, 3.3], size=17)
text(s, 0.7, 3.5, 12, 3.5, [
    ("≈ 17 in 100 warned drives vs < 1 in 200 others had a recorded failure within 3 months", 0),
    ("Warned drives: < 1% of the fleet, but 25% of the failures (28 of 111)", 0)], size=22)

# 8 Cox
s = slide("Cox model: reject H₀", (
    "The hazard ratio is about 43 and the confidence interval is far from 1, so we reject H0 at any conventional level. It hardly "
    "moves when exits are reclassified, when gap days are removed, or when we adjust for powered-on age. Powered years themselves "
    "show no clear effect, HR 1.11 per year, but nearly all drives are 5.5 to 6.2 powered years old, so we can only adjust within "
    "that narrow range."))
table(s, 0.7, 1.4, 11.9, [
    ["Analysis", "HR (SMART 197 > 0 vs 0)", "95% CI", "Wald p"],
    ["Primary", "43.2", "28.1 – 66.3", "1.7 × 10⁻⁶⁶"],
    ["S1: exits reclassified", "43.2", "28.1 – 66.3", "1.7 × 10⁻⁶⁶"],
    ["S2: gap days removed", "44.1", "28.7 – 67.7", "3.5 × 10⁻⁶⁷"],
    ["Adjusted for powered years", "43.6", "28.4 – 66.9", "9.5 × 10⁻⁶⁷"]], [4.2, 3.0, 2.6, 2.1], size=17, bold_rows=(1,))
text(s, 0.7, 4.4, 12, 2.6, [
    ("Powered years: HR 1.11 per year (0.85–1.43), p = 0.44 — but almost all drives are 5.5–6.2 years", 0),
    ("Decision: reject H₀ — with and without age adjustment", 0)], size=21)

# 9 Non-PH
s = slide("The risk is front-loaded: proportional hazards fail", (
    "The Grambsch–Therneau test rejects proportional hazards, p = 0.007. About 10% of warned drives fail in the first 30 days, then "
    "about 4% per month. So the hazard ratio of 43 is an average over the quarter — higher early, lower later — and the "
    "Kaplan–Meier curves are the more honest summary. We kept the pre-specified model rather than changing it after seeing this."))
text(s, 0.7, 1.4, 12, 5.6, [
    ("PH test (scaled Schoenfeld): χ² = 7.29, p = 0.0069", 0),
    ("Warned drives: ~10% fail in the first 30 days, then ~4% per 30 days", 0),
    ("HR = 43 is a quarter-average of a ratio that is larger early and smaller later", 0),
    ("We report KM curves and landmark survival alongside the HR; model left as pre-specified", 0)], size=22)

# 10 Interpretation
s = slide("What the result does — and does not — mean", (
    "Backblaze's own definition: a drive counts as failed when it is removed and replaced, either because it died (reactive) or "
    "because SMART stats or file-system checks said failure was highly probable (proactive). In Q3 2024, 53% of their failures were "
    "proactive, and the public flag does not say which. So part of our association is the replacement policy reacting to warnings "
    "like SMART 197. Google's 2007 study found a 16-fold higher 60-day failure risk after a first pending-sector event, so the "
    "direction agrees, but SMART alone misses most failures."))
text(s, 0.7, 1.4, 12, 5.6, [
    ("Backblaze counts proactive replacements (triggered by SMART stats, FSCK checks …) as failures", 0),
    ("Q3 2024: 721 of 1,361 failures (53%) were proactive; the public 0/1 flag does not distinguish them", 1),
    ("→ part of the association is built into the outcome: strong association, not a causal effect", 0),
    ("Consistent with Pinheiro et al. (Google, 2007): after a first pending-sector count, 16× more likely to fail within 60 days", 0),
    ("…but > 56% of their failed drives showed no strong SMART signal — not a stand-alone predictor", 1)], size=20)

# 11 Limitations
s = slide("Limitations", (
    "Run through these quickly; the first is the most important. The others: no installation dates, so only a narrow-range "
    "powered-hours proxy; daily snapshots so dates can lag; a few exits were informative; overlap with reallocated-sector warnings; "
    "one model, one quarter, 28 exposed failures."))
text(s, 0.7, 1.4, 12, 5.6, [
    ("Outcome includes SMART-informed proactive replacements (circularity)", 0),
    ("Prevalent cohort, no install dates; age proxy (powered hours) spans a narrow range", 0),
    ("Daily snapshots: 21 of 44 post-gap failures flagged on the return day", 0),
    ("4 'exited' drives were flagged as failed in early April — exits not fully uninformative", 0),
    ("110 of 162 warned drives also had reallocated sectors (SMART 5) — not specific to pending sectors", 0),
    ("One model, one quarter, 28 exposed failures → wide confidence interval", 0)], size=20)

# 12 Conclusion
s = slide("Conclusion", (
    "Summarise in three sentences: a nonzero pending-sector count on 1 January marks under 1% of drives with a much higher "
    "three-month rate of recorded failure, HR about 43, robust to exits, gaps and age. The excess is front-loaded. Because "
    "Backblaze counts SMART-informed replacements as failures, it is a strong association with recorded removal or failure, not "
    "proof that pending sectors cause failure."))
text(s, 0.7, 1.5, 12, 5.5, [
    ("A nonzero SMART 197 on 1 Jan marks < 1% of drives with a far higher 3-month recorded-failure rate", 0),
    ("HR 43.2 (28.1–66.3); 43.6 after adjusting for powered-on age — H₀ rejected", 0),
    ("Robust to exit and gap handling; excess risk concentrated in the first month", 0),
    ("Interpretation: strong association with recorded removal-or-failure — not causal, not a validated predictor", 0)], size=23)
text(s, 0.7, 6.4, 12, 0.6, ["Thank you — questions?"], size=22, color=RED)

# 13 Backup
s = slide("Backup: safeguards and reproducibility", (
    "Only if asked. The decision rule and analysis plan were committed to the repository before the relevant results existed, the "
    "cohort was rebuilt independently from a freshly downloaded archive and reproduced byte for byte, and the two software packages "
    "agree on every coefficient."))
text(s, 0.7, 1.4, 12, 5.6, [
    ("Commit order: decision rules (e3cf5dd) → group counts (4259dc3) → analysis plan (2b91f38) → results (28cb715)", 0),
    ("Age model: plan (e117f03) committed before fit (714fb97)", 0),
    ("Cohort rebuilt from a re-downloaded, SHA1-verified archive: byte-identical", 0),
    ("lifelines vs statsmodels: coefficients agree to < 10⁻⁶; 49 automated tests pass", 0),
    ("Repository: aayush-0131/backblaze-survival-analysis (no raw or drive-level data committed)", 0)], size=19)

prs.save(OUT)
print(f"wrote {OUT} ({len(prs.slides)} slides)")
