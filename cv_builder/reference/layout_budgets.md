# Layout Budgets — Single Source of Truth

> **This is the ONLY file that states character and page budgets.** Every other
> file (`char_count.py` and the SKILL.md files) points here instead of restating
> numbers. If a budget changes, change it HERE and nowhere else.

This kit produces a **UK student CV** on **A4 paper**. Sections, in order:
Education, Experience, Projects, Skills & Interests. One page strongly preferred,
two maximum. There is no separate "resume vs CV" distinction — in UK usage the
document is the CV. The `cv` format key in `char_count.py` is the LIVE key for the
single A4 CV geometry below; `resume` is retained only as a legacy alias that
reuses the same tiers.

---

## Page geometry (A4)

The owner pipeline's LaTeX template (its `cv.cls` document class + `cv_template.tex`,
not shipped in the public engine) loads `a4paper` and sets:

```
\geometry{a4paper, left=0.6in, right=0.6in, top=0.55in, bottom=0.55in,
          textwidth=7.07in, textheight=10.4in}
```

- A4 width = 8.27in. With left=right=0.6in margins: textwidth = 8.27 - 1.2 = **7.07in**.
- A4 height = 11.69in. With top=bottom=0.55in (+ footer space): textheight ≈ **10.4in**.

---

## Character-budget derivation (old US-letter → new A4)

The upstream kit was tuned for **US Letter** at **textwidth = 7.5in**. A4 is
narrower, so every per-line character budget scales by the text-width ratio:

```
scale = new_textwidth / old_textwidth = 7.07 / 7.5 = 0.943
```

Each old char range is multiplied by **0.943** and rounded to a whole char.
The CV body font is 11pt (unchanged from the upstream CV class).

| Variant | Old range (7.5in) | × 0.943 | New range (7.07in) | Old HARD MAX | New HARD MAX |
|---------|-------------------|---------|--------------------|--------------|--------------|
| 1L | 88–93   | 83–88   | **83–88**   | 101 | **95** |
| 2L | 168–182 | 158–172 | **158–172** | 190 | **179** |
| 3L | 250–268 | 236–253 | **236–253** | 280 | **264** |

Orphan thresholds scale the same way: old CV orphan ≥ 65 chars → **≥ 61 chars**.

> Derivation note: the upstream "resume" 10pt geometry (7.5in) is retired. There
> is one A4 CV geometry only. The 1L/2L/3L tiers above are the authoritative
> limits; the bold-width penalty below is unchanged in form, only the base shrinks.

---

## Character limits (AUTHORITATIVE — A4, 11pt)

| Target Lines | Rendered Char Range | HARD MAX | Orphan Threshold |
|--------------|---------------------|----------|------------------|
| 1 line | 83–88 chars  | 95  | -- |
| 2 lines | 158–172 chars | 179 | Last line ≥ 61 chars |
| 3 lines | 236–253 chars | 264 | Last line ≥ 61 chars |
| Tagline (1 line) | 80–95 chars | 95 | -- |
| Profile block (3–4 lines, replaces tagline when used) | 240–330 chars | 350 | Last line ≥ 61 chars |

> **AIM FOR THE MIDDLE OF THE RANGE, NOT THE HARD MAX.** A 2L bullet targets
> ~165 chars, not 179. Proportional fonts have variable char widths — a bullet at
> the hard max WILL overflow if it contains wide characters (m, w, W, capitals,
> em-dashes). Em-dash (`---`) counts as 1 char but renders ~2× wide; budget 2
> extra chars per em-dash.

### Bold width penalty (A4, 11pt)

Bold characters render wider. Effective per-line limit:

```
effective_limit = 86 - (0.25 × bold_char_count)
```

- 0 bold: safe up to ~88 chars/line (HARD MAX 95 for 1L)
- 2–3 bold tools (~10–18 bold chars): 81–83 effective → use 80–85 as default
- 5+ bold tools (~28+ bold chars): ~79 effective → tighten to 78–83

---

## Page budgets

- **1 page strongly preferred, 2 pages maximum.** A UK student CV is expected to
  be one page; a second page is only justified when placement + substantial
  project/society evidence genuinely fills it.
- A 1-page A4 CV at 11pt holds roughly **44–46 rendered text lines** of body
  content after the header, across all sections.
- **Experience + Projects bullets:** budget **~10–16 variable bullets** total
  (2L default, occasional 3L for the strongest item). Allocate more bullets to
  the most JD-relevant entry.
- **Skills & Interests:** 3–4 grouped lines (e.g. Languages / Frameworks & Tools /
  Other; plus a one-line Interests). Each grouped line = exactly 1 rendered line.
- **Cover letter:** 1 page, **250–350 words**, 3 paragraphs. Full package
  (CV + cover letter) = 2 pages.

### Variable vs fixed

- **FIXED** (template-locked, copied verbatim): header block, Education entries.
- **VARIABLE** (generated per JD): Experience bullets, Projects bullets, Skills
  & Interests group contents, and any position theme lines.

### Page-fill rule

- 1-page target: ≤ 3 lines of white space at the bottom of page 1. If short, add
  or expand a variable bullet; if it spills to a 2nd line/page, trim variable
  content only — never touch `\vspace`, `\geometry`, or FIXED sections.

---

## Where this is enforced

- `cv_builder/helpers/char_count.py` — the `cv` format implements the tiers above
  and is authoritative. Run it after each section.
- Any other file that mentions a budget carries at most a *summary table* marked
  "generated from layout_budgets.md"; it does not define the numbers.
