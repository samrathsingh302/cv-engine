# Critique Framework — Consolidated Multi-Perspective Protocol

**Purpose:** Single-pass comprehensive critique that catches what would otherwise take multiple passes. Run AFTER generation but BEFORE presenting to user.

**Key insight:** 85% of score improvement typically comes from ONE thing — domain reframing. Reframing means restating each achievement in the target domain's vocabulary and showing how the underlying method transfers, WITHOUT inventing anything: the facts stay fixed, only the framing changes (an honest gap stays a gap). Generation should already apply this principle, so the critique's job is to catch what leaked through, identify remaining gaps, and assess interview likelihood from multiple reader perspectives.

---

## Part 0: Domain-Specialist Lens (generate BEFORE the five perspectives)

Before running the five-perspective read-through, construct a domain-specialist lens for THIS specific JD + company. The lens is not a static lookup — it is generated fresh each time by analysing the JD, the company, and the hiring context.

### Build the Lens

**If a session file exists** (`<profile_root>/output/<Folder>/session_<name>.md`) with JD Analysis and Company Context sections, use those as the foundation for the lens instead of re-researching from scratch. Supplement only the elements not already covered (competitive landscape, methodology transfer test, reviewer persona details).

**If no session file exists,** research THIS company + THIS JD from scratch. No pre-built templates. No reference lenses.

**For each critique, produce these 7 elements:**

1. **Reviewer persona construction:** Who actually reads this CV? Construct from the JD's reporting line, team name, level, and company context.
   - Their job title and seniority
   - What they do daily (what tools they use, what problems they solve)
   - How many CVs they've read for this posting (estimate from company size + role level)
   - What they've seen 100 times before that makes them roll their eyes
   - What would genuinely surprise or impress them

2. **Company research:** What does this company MAKE, SELL, or RESEARCH?
   - Core business and revenue model
   - R&D culture: academic-leaning? patent-driven? product-shipping? mission-driven?
   - Recent news, strategic priorities, or technology bets (if known)
   - What vocabulary signals "insider who understands our business" vs "outsider applying generically"?
   - Note any assumptions and flag uncertainty

3. **JD deep read — vocabulary extraction:**
   - Read the JD 3 times. First for requirements, second for culture signals, third for vocabulary.
   - Extract the 8-10 most important terms/phrases (ranked by: frequency in JD, placement in title/header vs body, and whether they represent binary capabilities vs spectrum skills)
   - For each: what does THIS company mean by this term? (e.g., "emerging computing paradigms" at a given company might mean quantum/neuromorphic — not just "we use ML")
   - Identify the JD's implicit hierarchy: what's the #1 thing they need vs nice-to-haves?

4. **Domain vocabulary map:** For this specific JD, what are the 5-8 vocabulary swaps that separate "outsider applying" from "insider who gets it"? Generate these purely from the JD's language and the company context you just researched.

   Format:
   | CV currently says | Should say for THIS JD | Why |
   |---|---|---|
   | [term] | [replacement] | [JD uses this language because...] |

5. **Fatal vs cosmetic gap ranking:** Which missing JD keywords would cause immediate rejection vs which are nice-to-have?
   - **Fatal gaps:** Binary capabilities the JD requires (e.g., "CFD" — you either do it or you don't), terms in the JD title, or phrases repeated 3+ times
   - **Serious gaps:** Preferred qualifications that multiple competitive candidates will have
   - **Cosmetic gaps:** Terms buried in preferred quals that most candidates also won't have
   - For each gap: can it be bridged truthfully? Or is it a hard limitation of the candidate's background?

6. **Methodology transfer test:** For each of the candidate's top 5 CV achievements, write one sentence explaining how a domain expert at THIS company would see it mapping to THEIR work.
   - If you CAN write that sentence naturally: the CV has bridged the gap
   - If you STRUGGLE to write it: the CV hasn't made the transfer explicit enough
   - If you CAN'T write it honestly: this is a hard gap, not a reframing problem

7. **Competitive landscape intuition:** Who else is applying for this role?
   - What background does the "obvious fit" candidate have?
   - What does THIS candidate offer that the obvious fit doesn't? (e.g., shipped side project, breadth, a strong relevant module)
   - What does the obvious fit offer that this candidate doesn't? (e.g., prior placement, direct stack experience)
   - This determines what the CV must EMPHASISE (unique strengths) and what it must BRIDGE (gaps relative to the obvious fit)

### Output and persist the lens

Write out all 7 elements as a structured section at the top of the critique file. This lens then informs EVERY subsequent perspective in Parts 1-6. The five readers (ATS, Recruiter, HR, HM, Technical) all read through this lens — they are people at THIS company, not generic archetypes.

**Persistence rule:** The lens is built ONCE per JD, during the first critique. If the CV is revised and critiqued again (multi-pass), reuse the same lens — do NOT re-research. The lens lives in the critique output file (`<profile_root>/output/<Folder>/critique_<name>.md`) and is carried forward across passes. Only rebuild the lens if the JD itself changes.

---

## Part 1: Five-Perspective Read-Through

Read the CV from five different personas, in order. Each persona sees only what they'd actually read in their time window. Flag issues per persona.

### Perspective 1: ATS Robot (0 seconds — keyword scan)

**What it does:** Pattern-matches JD keywords against CV text. No context, no synonyms (unless configured), no reading comprehension.

**Check:**
- Extract top 20 JD keywords/phrases (tools, methods, domain terms, soft skills)
- For each: verbatim match? Semantic match? Absent?
- Count match rate: >=70% = PASS, 60-69% = MARGINAL, <60% = FAIL
- Flag any JD keyword that appears 3+ times in JD but 0 times in CV (high-priority gap)
- Check domain bridges — do they appear enough to pass a domain-specific ATS filter?

**Output:** Keyword match table + match rate + top 3 missing keywords that could be added truthfully.

### Perspective 2: Recruiter Glance (10 seconds)

**What they read:** Name, education line (degree + university + year), header tagline, the first Experience/Project entry. Nothing else.

**What they decide:** "Forward to hiring manager or reject?"

**Check:**
- Does the header tagline use target-role language (not generic)?
- Does the education line (degree, university, year of study) clear the bar for this placement/internship?
- Does the strongest project or experience appear high enough to catch a 10-second glance?
- Is there a concrete signal in the first lines (a named project, a real metric)?
- Would a non-technical recruiter understand what this person does?

**Output:** "Forward" / "Maybe" / "Reject" + one-sentence reasoning.

### Perspective 3: HR Screen (30 seconds)

**What they read:** Tagline + Skills group headers + first bullet per entry + education.

**What they decide:** "Does this person meet the basic requirements? Schedule a call?"

**Check:**
- Does the tagline signal the target role and what the candidate brings?
- Do skills group NAMES (not just content) signal target-role relevance?
- Does the first bullet under each entry deliver the strongest JD-relevant point?
- Is the year of study / availability consistent with the placement/internship dates?
- Are required languages/tools visibly present?

**Output:** "Phone screen" / "Borderline" / "Pass" + one-sentence reasoning.

### Perspective 4: Hiring Manager Read (2 minutes)

**What they read:** Everything on the CV. They're a domain expert.

**What they decide:** "Interview or not? What would I ask?"

**Check:**
- **Methodology transfer:** For each major bullet, can the HM see how this applies to THEIR work? Or do they have to imagine the transfer themselves? (If the HM has to do the translation, you've lost points)
- **Narrative arc:** Does the story progress logically? (Typical good arc: degree → coursework/projects → real builds → roles/societies)
- **Red flags:** Any overclaiming? Any "this person doesn't know what we do" signals? Any keyword stuffing that feels forced?
- **Differentiation:** What makes this candidate different from other applicants? Is that differentiator visible?
- **Domain gap honesty:** Does the CV acknowledge what it ISN'T (transparent about actual domain) while showing what transfers? Honest reframing beats pretend expertise.

**Output:** "Interview" / "Maybe" / "No" + top 3 things HM would notice + predicted first interview question.

### Perspective 5: Deep Technical Reviewer (10 minutes)

**What they do:** Read every bullet carefully. Check the projects/repos. Assess truthfulness. Look for inconsistencies.

**Check:**
- **Truthfulness audit:** For each quantitative claim, is it verified against extractions/experience files?
- **Provenance flags:** Group projects and AI-assisted builds framed honestly? No unconfirmed grades stated as final?
- **Verb discipline:** Group/shared-work bullets use hedged verbs ("contributed to", "co-built")? Full-ownership verbs only for solo work?
- **Project coherence:** Do project bullets match the repos/links? Does the stated stack match what the project actually uses?
- **Internal consistency:** Does the tagline match the bullets? Does the cover letter match the CV?
- **Over-saturation:** Any keyword repeated >8 times? (Borderline at 6-8, concern at 9+)

**Output:** Truthfulness table (claim → verified? → source) + any inconsistencies found.

---

## Part 2: Eight-Dimension Scoring

Score each dimension independently, then compute weighted total.

| # | Dimension | Weight | What to Assess |
|---|-----------|--------|---------------|
| 1 | ATS Keyword Match | 15% | JD keyword coverage rate, verbatim vs semantic, missing high-value terms |
| 2 | Tagline | 8% | Target-role language, what the candidate brings, no fluff, fits 1 line |
| 3 | Skills & Interests | 10% | Group names (role signal), content relevance, bold accuracy, no wasted entries |
| 4 | Bullet Quality | 22% | Per-bullet JD alignment (HIGH/MEDIUM/LOW), reframing quality, quantification, action verbs |
| 5 | Projects & Technical Evidence | 15% | Strength and relevance of projects/repos, honest solo-vs-team framing, demonstrated build skill |
| 6 | Narrative Coherence | 12% | Education-to-experience-to-projects story, role thread count, first-impression timing |
| 7 | Company & Role Fit | 13% | "Why this company" signal, role-type match, insider vocabulary, credibility for the level |
| 8 | Page Fill & Visual | 5% | LaTeX/owner pipeline: 1-page budget compliance, orphan check, compile clean, slack acceptable. Content-first markdown (/improve-cv): no compile/page-fill — score length discipline and section ordering instead (no padding, no sprawl, strongest material first) |

**Note:** there is no Publications dimension — a UK student CV has none. Publication weight
was folded into **Projects & Technical Evidence**, and **Company & Role Fit** was added.
Weights sum to 100.

**Scoring rubric per dimension:**
- 9-10: Essentially optimal for this candidate-JD pairing
- 8-8.5: Strong, minor improvements possible but diminishing returns
- 7-7.5: Good but identifiable gaps that reframing could close
- 6-6.5: Significant gaps — missing domain bridge, wrong vocabulary, weak bullets
- <6: Major problems — wrong role framing, overclaiming, format violations

**Overall score interpretation:**
- 85+: At or near ceiling. Submit.
- 80-84: Strong. 1-2 targeted improvements could push to ceiling.
- 75-79: Good foundation but missing domain reframing or key bullets.
- 70-74: First-draft quality. Needs systematic reframing pass.
- <70: Fundamental issues (wrong role type, missing sections, accuracy problems).

---

## Part 3: Interview Likelihood Assessment

After scoring, assess interview probability from each reader's perspective.

### Assessment Matrix

| Reader | Time | Question They Ask | Likely Outcome |
|--------|------|-------------------|----------------|
| ATS | 0 sec | "Do keywords match?" | PASS / FAIL |
| Recruiter | 10 sec | "Credible for this level?" | FORWARD / REJECT |
| HR | 30 sec | "Meets basic quals?" | PHONE SCREEN / PASS |
| Hiring Manager | 2 min | "Would I learn something in an interview?" | INTERVIEW / MAYBE / NO |
| Technical Panel | 10 min | "Can this person do the work?" | STRONG YES / YES / CONCERNS |

For each reader, give a probability estimate (e.g., "80% forward") and the single factor that most influences their decision.

### Ceiling Analysis

| Scenario | Estimated Score |
|----------|----------------|
| Current CV | [X] |
| + Top 3 improvements applied | [X + delta] |
| Theoretical max (this candidate + this JD) | [X_max] |
| Hard ceiling (structural background gap) | [X_ceiling] |
| What would close the gap | [e.g., "1 shipped project in their stack → +3 pts"] |

---

## Part 4: Actionable Improvements (Ranked)

List ALL identified improvements in three tiers:

### Tier 1: HIGH IMPACT (each worth >= 1 point)
These are the improvements that move the score meaningfully. Typically:
- Domain reframing that was missed during generation
- Missing JD keyword that can be added truthfully
- Bullet swap (weak bullet → stronger unused project/experience)
- Tagline missing or weak

For each: Current text → Proposed text → Why → Expected point impact.

### Tier 2: MEDIUM IMPACT (each worth 0.3-0.9 points)
- Minor reframing (vocabulary swap)
- Project framing refinements
- Skills group name adjustments
- One additional keyword insertion

### Tier 3: COSMETIC / DIMINISHING RETURNS (each worth < 0.3 points)
- Keyword saturation reduction
- Minor wording polish
- Alternative project selection

### Verdict
State clearly: "Apply Tier 1 changes. Tier 2 are optional. Tier 3 are not worth the edit."

---

## Part 5: Interview Bridge Points

For each major CV topic, provide the verbal bridge the candidate should use if asked in an interview. Format:

| CV Topic | Target Equivalent | Opening Line for Interview |
|---|---|---|
| [Project/experience X] | [How it maps to the role] | "The same approach I used for X applies directly to Y because..." |

This section converts CV claims into interview talking points. Include 5-7 bridges covering highlights from all entries.

---

## Part 6: Cover Letter Critique (Context-Aware)

If a cover letter was generated in the same session, run all checks below. Detect employer type first: Big tech / Startup or scale-up / Grad scheme or corporate.

### 6A. Anti-Pattern Checklist
- [ ] Does NOT open with "I am writing to express my interest" or similar generic opener
- [ ] Does NOT rehash CV bullet points in prose (adds narrative context instead)
- [ ] Names a specific product/team/project from the target company
- [ ] Has a clear "why THIS role at THIS company" sentence (not generic)
- [ ] Strongest qualification appears in paragraph 1, not buried in P2/P3
- [ ] No defensive/apologetic language about gaps ("Although I'm only a second year...")
- [ ] Closing has active call to action, not passive "Thank you for your consideration"
- [ ] Honesty: no solo-ownership claims for group/AI-assisted work

### 6B. Tailoring Signal Checklist
- [ ] Names a specific product/technology/team at the company
- [ ] Uses at least 3 JD terms that supplement (not just duplicate) CV keywords
- [ ] References the company's mission, culture, or recent work
- [ ] Proposes a specific connection between the candidate's projects and their need
- [ ] Correctly identifies employer type and adjusts tone/emphasis accordingly

### 6C. Context-Specific Checks

**Big tech:**
- [ ] Concrete impact translation present for each project? ("handling X, reducing Y")
- [ ] Scale/engineering signals present (testing, performance, real users)?
- [ ] Jargon minimised for a recruiter first reader?

**Startup or scale-up:**
- [ ] Initiative and shipped work emphasised (side projects, hackathons, ownership)?
- [ ] Breadth/adaptability signalled?
- [ ] "Why this company specifically" beyond "you're growing fast"?

**Grad scheme or corporate:**
- [ ] Motivation for the scheme/programme stated clearly?
- [ ] Structured fit articulated? ("Your placement in X aligns with...")
- [ ] Professional, well-organised tone?

### 6D. Cover Letter ATS Keyword Check
- Extract 10 high-priority JD keywords
- Check how many appear in the cover letter (target: 5-8 that supplement CV keywords)
- Most large UK employers screen applications, so keywords still matter.

### 6E. Structural Checks
- [ ] **Consistency:** Key claims match CV bullets (no contradictions, no unsupported new claims)
- [ ] **Complementarity:** Adds narrative context the CV cannot (motivation, "why this company")
- [ ] **Word count:** 250-350 words
- [ ] **Tone match:** Big tech = impact-driven, Startup = initiative, Grad scheme = structured fit
- [ ] **Quantification:** 3-5 quantified claims (more = fact sheet, fewer = vague)
- [ ] **Honest framing:** group/AI-assisted work hedged, not overclaimed

### 6F. Package Cohesion Check
- [ ] **CV stands alone:** If the cover letter were deleted, does the CV independently earn an interview? No critical context only in the letter.
- [ ] **Cover letter deepens, not introduces:** Every major claim is traceable to a CV bullet. It adds context/motivation, not new achievements.
- [ ] **No contradictions:** Dates, metrics, claims, and framing consistent across both documents.
- [ ] **Complement, not repeat:** The cover letter is NOT a prose restatement of CV bullets. It adds motivation and "why this company".
- [ ] **Page budget:** CV (1 page preferred, 2 max) + cover letter (1 page) = 2-page package.

---

## Critique Output Template

```markdown
# Critique: [Company] [Role Title] ([Job ID])

**CV File:** `[path to the CV — .tex for the owner LaTeX pipeline, .md for /improve-cv]`
**Date:** [date]

---

## Domain-Specialist Lens (researched for this JD)

### Reviewer Persona
[Constructed persona — who reads this, what they do daily, what they've seen before]

### Company Context
[What they make/do, R&D culture, strategic priorities]

### JD Vocabulary Extraction (top 8-10 terms, ranked)
| # | JD Term | Frequency | Meaning at THIS Company | CV Match? |
|---|---|---|---|---|
| 1 | [term] | [N times] | [what they mean by it] | YES/PARTIAL/NO |

### Domain Vocabulary Map
| CV Currently Says | Should Say for This JD | Why |
|---|---|---|
| [term] | [replacement] | [reasoning] |

### Gap Ranking
- **Fatal:** [gaps that cause rejection]
- **Serious:** [gaps competitive candidates won't have]
- **Cosmetic:** [nice-to-have, most candidates also miss]

### Methodology Transfer Test
| Achievement | How THIS Company's Expert Sees It |
|---|---|
| [achievement] | "[one sentence transfer explanation]" |

### Competitive Landscape
- **Obvious fit candidate:** [description]
- **Our advantage:** [what we offer they don't]
- **Their advantage:** [what they offer we don't]

---

## Five-Perspective Read-Through

### ATS Robot (keyword scan)
[Keyword match table]
**Match rate:** X/20 = Y%

### Recruiter Glance (10 seconds)
**Verdict:** [Forward/Maybe/Reject]
[Reasoning]

### HR Screen (30 seconds)
**Verdict:** [Phone screen/Borderline/Pass]
[Reasoning]

### Hiring Manager (2 minutes)
**Verdict:** [Interview/Maybe/No]
**Top 3 observations:**
1. [What they notice first]
2. [What impresses or concerns them]
3. [What they'd ask about]
**Predicted first interview question:** "[question]"

### Technical Reviewer (10 minutes)
**Truthfulness:** [All verified / N concerns]
**Consistency:** [Clean / N issues]

---

## Eight-Dimension Scoring

| Dimension | Score | Weight | Weighted | Notes |
|---|---|---|---|---|
| ATS Keywords | X/10 | 15% | X.XX | [1-line note] |
| Tagline | X/10 | 8% | X.XX | |
| Skills & Interests | X/10 | 10% | X.XX | |
| Bullet Quality | X/10 | 22% | X.XX | |
| Projects & Technical Evidence | X/10 | 15% | X.XX | |
| Narrative Coherence | X/10 | 12% | X.XX | |
| Company & Role Fit | X/10 | 13% | X.XX | |
| Page Fill & Visual | X/10 | 5% | X.XX | |
| **Total** | | **100%** | **XX.X** | |

---

## Interview Likelihood

| Reader | Probability | Key Factor |
|--------|------------|------------|
| ATS | X% | [factor] |
| Recruiter (10s) | X% | [factor] |
| HR (30s) | X% | [factor] |
| Hiring Manager (2m) | X% | [factor] |
| Technical Panel (10m) | X% | [factor] |

**Ceiling:** Current [X] → Max achievable [Y] → Hard ceiling [Z]

---

## Actionable Improvements

### Tier 1 (HIGH — do these)
1. [Change] — [+N pts]

### Tier 2 (MEDIUM — optional)
1. [Change] — [+N pts]

### Tier 3 (COSMETIC — skip)
1. [Change]

---

## Interview Bridge Points

| CV Topic | Target Equivalent | Opening Line |
|---|---|---|
| [topic] | [equivalent] | "[bridge statement]" |

---

*End of critique.*
```

---

## Part 6G: AI Fingerprint Scan

Run the 12-item checklist from `cv_builder/support/ai_fingerprint_rules.md` Section 6. Key scans:
- Count em-dashes (`---`) in full document — flag if >2
- Scan all bullet endings for -ing analysis phrases (the #1 structural AI marker)
- Search for any Tier 1 banned word (delve, tapestry, multifaceted, pivotal, etc.)
- Check the cover letter for generic opener and uniform sentence length

Any failure is a Tier 1 fix in Part 4.

---

## Part 7: Post-Generation Verification

Final mechanical checklist. Run AFTER all other critique parts. These are pass/fail checks, not scored dimensions.

> **Pipeline note:** items marked **(LaTeX/owner pipeline only)** apply when producing a
> compiled `.tex` CV via the owner pipeline (`/make-cv`, `/critique`). For a content-first
> markdown CV (`/improve-cv`), skip those compile/page-fill checks; the provenance and
> identity facts come from the **subject's own CV**, never `config.md` (that is the kit
> owner's data and is not part of the public engine).

### Mechanical Checks
- [ ] **(LaTeX/owner pipeline only)** All bullets within char limits (no OVER violations from char_count.py)
- [ ] **(LaTeX/owner pipeline only)** All multi-line bullets pass orphan check (last line >= 70% fill)
- [ ] **(LaTeX/owner pipeline only)** Page fill within budget (1-page target: <= 3 lines white space; see layout_budgets.md)
- [ ] No ordering errors in bullet sequencing
- [ ] Markdown CVs (/improve-cv): length discipline (no padding/sprawl) and strongest material first

### Content Checks
- [ ] ATS keywords present (>= 70% match rate)
- [ ] All provenance flags correct (owner pipeline: see config.md / CLAUDE.md; /improve-cv: derive provenance from the subject's own CV, never config.md)
- [ ] No forbidden terms (owner pipeline: see config.md KB Corrections Log; /improve-cv: the subject's stated facts and the AI-tell ban-list in `cv_builder/support/ai_fingerprint_rules.md`)
- [ ] No inflation (group/AI-assisted work hedged, no false claims)
- [ ] Project bullets match the actual repos/links and stated stack
- [ ] Cover letter claims traceable to CV bullets

### Structural Checks
- [ ] Company name spelled correctly throughout
- [ ] **(LaTeX/owner pipeline only)** .tex file has complete preamble (will compile standalone)
- [ ] Date format consistent (dd/mm/yyyy or Mon YYYY -- Mon YYYY)
- [ ] Contact details correct (owner pipeline: email per config.md; /improve-cv: match the subject's own CV)
- [ ] **(LaTeX/owner pipeline only)** Page count correct after compile (1 preferred, 2 max)

**If any check fails, flag it as a Tier 1 fix in Part 4.**

---

## Part 8: Evidence-Acquisition Plan

The Ceiling Analysis (Part 3) names a hard ceiling — the score this candidate cannot pass on
wording alone, because what's missing is *evidence*, not phrasing. Part 8 turns that ceiling
into a ranked, dated plan of how to raise it. It is written AFTER all scoring, as the closing
section of the critique, and is the ONE place a "what to do next" plan lives (the orchestrating
skill persists it to the session file — there is no separate plan artefact).

### The hard rule (overrides everything in this section)

Every action raises the score by **acquiring, verifying, or measuring evidence**, or by
**improving JD pairing / interview preparation** — NEVER by inflating or inventing a claim. An
action is legitimate only if it makes a true thing provable, a vague thing precise, or an
unconfirmed thing confirmed. It is illegitimate if it makes the CV *say more than the candidate
can defend*. The anti-fabrication rules apply unchanged: a gap that can only be closed by a
claim the candidate cannot evidence is recorded as a hard limitation, not as an action.

**Past ~90 the plan offers ONLY evidence-acquisition, better JD pairing, and interview
conversion — explicitly never bigger claims.** Above that band the wording is already at
ceiling; the only honest levers left are (a) acquiring real new evidence (ship the thing,
get the number, pass the cert), (b) pointing the same evidence at a JD it fits better, and
(c) converting the CV's strengths in the interview. State this constraint at the top of the
emitted plan so the reader sees the kit is not chasing a number by inflation.

### Action types

Each action is typed. The three verbs are deliberate and exhaustive:

- **build X** — create a new piece of real evidence that doesn't exist yet (ship a project in
  the target stack, complete a course, produce an artefact). Highest point value, highest
  effort, longest lead time. Subject to the in-progress labelling rule until it actually ships.
- **verify Y** — resolve an open `[VERIFY]` / unconfirmed sentinel (per `claims_schema.md`
  semantics) so a hedged or caveated claim can stand at full strength, or so a number can be
  stated. Usually low effort (a message, a record lookup); turns an asterisked claim into a
  clean one. Never invents the answer — if verification comes back negative, the claim weakens
  or drops.
- **measure Z** — attach a real, defensible metric to an achievement that is currently
  qualitative ("log throughput at the next event", "pull the before/after figure from the
  logs"). Raises Bullet Quality and Projects evidence without changing what was done.

### Estimating point value (grounded, not guessed)

Point values are **grounded in the eval harness's measured per-dimension deltas**, not invented.
The harness (`eval/`) ran critique → improve → re-critique over the genre corpus and reported the
mean /10 movement per dimension. As a calibration anchor, the measured corpus means (from
`python eval/harness.py --scores-dir eval/fixtures/scores` over the shipped fictional corpus) are:
tagline ~4.4, bullet quality ~3.0, narrative ~2.5, skills ~2.4, projects & technical evidence
~2.1, page/visual ~1.1 (upper-bound *full-reframe* movements; cite that they come from the eval
harness, not a guess). Company & role fit (~1.5) and ATS keywords (~1.0) were measured on a
private targeted-JD instance — the shipped corpus manifests are all no-target, so those two
dimensions do not appear in the shipped harness report; treat them as indicative only.

To estimate an action's point value:
1. Identify which of the 8 dimensions the action moves (often 2–3).
2. For each, the marginal gain of a single evidence action is a *fraction* of that dimension's
   measured full-reframe delta — a verified number that lifts one bullet is a slice of the ~3.0
   bullet-quality movement, weighted by the dimension's weight (Part 2). A whole new shipped
   project in the target stack can move Projects & Technical Evidence and Company & Role Fit
   together and is the rare action worth >1 weighted point.
3. Express the estimate as a weighted-point range (e.g. "+0.8–1.2 pts, Bullet Quality + ATS"),
   and name the dimension(s) so the reader can sanity-check it against the scoring table.
4. If a dimension is already at 9–10, its remaining headroom is near zero — do not promise
   points there; that is the diminishing-returns wall the ceiling described.

Keep estimates honest and conservative. The plan's credibility is that its numbers trace to a
measured harness, not to optimism.

### Effort and deadline

- **Effort:** S / M / L (or an hours estimate). S = minutes-to-an-hour (a message, a lookup, a
  one-line metric); M = an evening to a few days (write-up, small build, sit a short cert);
  L = a week-plus (ship a real project, complete a substantial course).
- **Deadline vs the application window:** every action is dated against when the application
  must go in. Mark each: **before the window closes** (do it — the points land in time),
  **tight** (only if the window allows), or **post-submission / next cycle** (real but won't
  help this application — note it for the next CV). An L-effort build with a deadline past the
  window is honestly flagged as not-this-time, never quietly promised as a quick win.

### Output format (written into the session file)

Emit a ranked table — highest net value (point value weighed against effort and whether it
lands before the window) first:

```
## Evidence-Acquisition Plan ([date])

> Past ~90 this plan offers only evidence/pairing/interview-conversion — never bigger claims.
> Point values are grounded in the eval harness's measured per-dimension deltas, not guessed.

| # | Type | Action | Point value (dimension) | Effort | Deadline vs window | Clears |
|---|------|--------|-------------------------|--------|--------------------|--------|
| A1 | verify | [resolve a named [VERIFY] sentinel] | +X pts ([dimension]) | S | before window | [sentinel id] |
| A2 | measure | [attach a real metric to an achievement] | +X pts ([dimension]) | S/M | before window | — |
| A3 | build | [ship a real artefact in the target stack] | +X pts ([dimensions]) | L | [tight / next cycle] | — |
```

Below the table, one line per action stating exactly what "done" looks like and the honest
downside if it comes back negative (for `verify` actions especially). Close with a one-line
verdict: which actions are worth doing before this window, and which are for the next cycle.

If `/improve-cv` runs this (no owner KB), the same structure applies — `verify` actions become
"questions for the subject" and `build`/`measure` actions become advisory suggestions, since the
engine cannot acquire the subject's evidence for them.

---

## When to Use Multi-Pass vs Single-Pass

**Single pass (this framework):** Use for ALL new generations going forward. Generation should already apply the domain-reframing principle (above) so the first draft is reframed, meaning one comprehensive critique should catch remaining issues.

**Multi-pass (iterative refinement):** Only needed when:
- Score is below 80 after first critique (indicates systematic reframing failure)
- User requests specific changes and wants re-evaluation
- A fundamentally new approach is tried (e.g., switching role-type framing mid-stream)

When doing multi-pass, each subsequent critique should:
1. State "Changes Since Pass N" at the top
2. Only re-score dimensions that changed
3. Track score trajectory (Pass 1 → Pass 2 → ...)
4. Declare ceiling when score stops moving (typically after 2-3 passes once reframing is applied)
