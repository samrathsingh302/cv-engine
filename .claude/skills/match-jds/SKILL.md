---
description: Rank your saved JDs by how well your existing experience already fits — score the knowledge base against each JD, project a fit band, and surface your 3 strongest matches and the one fatal gap per role. Trigger when the user says "which jobs fit me best", "rank my JDs", "where am I already a strong fit", "reverse-match my CV", or gives a folder of JDs.
user-invocable: true
---

# /match-jds

**User input:** `$ARGUMENTS`

Invocation: `/match-jds [folder or JD files] [--profile <name>]`

Parse `$ARGUMENTS`:
- A folder path → score every `*.txt`/`*.md` JD in it.
- One or more file paths → score exactly those JDs.
- Empty → default to the active profile's `<profile_root>/JDs/`.
- `--profile <name>` → resolve that profile instead of the active pointer.

This is the JD reverse-matching skill ("lever 2"). It is the REVERSE of
`/target-company`: instead of deep-diving one company, it scores the knowledge base
you already have against MANY saved JDs and ranks the pairings, so you apply where you
are already a strong fit. It produces ONE artefact: a ranked match report. It does not
write a CV or a bundle — the next step on a top pairing is `/target-company` then
`/make-cv`.

**Read the depth file once before Phase 0:** `cv_builder/reference/match_jds_reference.md`
— the projection rubric, the match-manifest schema, and the report shape. This SKILL.md
is the workflow; the reference holds the rubric and templates. Do not duplicate them here.

---

## Profile resolution (read FIRST)

Resolve the active profile before reading or writing ANY owner data: use `--profile <name>`
if given, else the one-line `users/.active` pointer; set `<profile_root>` = `users/<name>/`.
**Fail-closed** — if `users/<name>/` is absent, STOP and tell the user; never fall back to
another profile. Full rule + the SHARED-vs-profile path list: `shared_ops.md` "Profile
Resolution" (owner kit — where that file is absent, e.g. the public engine, this section IS
the full rule). In this file, `<profile_root>/...` means the resolved `users/<name>/...` path.

---

## Safety Rules (ALWAYS ENFORCED)

**Accuracy > Relevance > Impact > ATS > Brevity**

- **EVIDENCE GATE (sacred).** Every projected score cites the knowledge-base evidence
  that supports it. No score exceeds what its evidence file can truthfully bear.
- A projection is a CEILING estimate of a future HONEST CV — never a licence to claim
  more than the candidate can defend. A missing must-have is a fatal gap, recorded
  honestly, never a reason to inflate a score.
- **No scraping (fence).** Read ONLY JDs already saved to disk. Never fetch a job board
  or posting. To match a new role, the user saves its JD to `<profile_root>/JDs/` first.
- **Read-only enrichment (fence).** If a JD is thin and company context would help, a
  READ-ONLY agent may search the company's own pages; synthesise a short factual summary
  yourself and let only that summary inform scoring — no writer step sees raw fetched text.
- Read `<profile_root>/config.md` Provenance Flags and `CLAUDE.md` KB Corrections before
  scoring. British English throughout; "CV" not "resume" in prose; dd/mm/yyyy; £.

---

## User Input During Execution

If the user gives a focus directive ("only the placements", "rank for backend roles"):
1. Acknowledge it immediately.
2. If it narrows the JD set: re-gather the set, keep the KB read.
3. If it changes emphasis: carry it into Phase 1 scoring (it shifts weights of fit, not facts).
4. Never restart — resume from the current phase.

---

## Startup

Read `cv_builder/reference/shared_ops.md` for profile resolution and output conventions if it
exists (owner kit; absent in the public engine — the Profile-resolution section above governs). Then:
1. Read `CLAUDE.md` — KB Corrections; Active Sessions in the newest handoff (owner kit; skip if absent).
2. Read `<profile_root>/config.md` — Personal Info, Provenance Flags, Role Types.
3. Read the depth file: `cv_builder/reference/match_jds_reference.md`.

---

## Phase 0: Gather the JD set + read the KB once

**Goal:** the list of JDs to score, and the evidence base, read a single time.

1. Resolve the JD set from `$ARGUMENTS` (default `<profile_root>/JDs/`). List what you found:
   "Scoring N JDs: [ids]." If the set is empty, tell the user to save JDs to
   `<profile_root>/JDs/` and stop.
2. Read ALL of `<profile_root>/knowledge_base/extractions/` and
   `<profile_root>/cv_builder/experience/` — this is the evidence base, read ONCE and
   reused for every JD.

Progress: "Read the KB: N extractions, M experience files. Scoring K JDs."

---

## Phase 1: Score each JD (lightweight projection)

**Re-read the Safety Rules above.** For EACH JD, using the rubric in
`match_jds_reference.md` §3:

1. **Distil the role (lightweight):** must-have skills + the screening keywords. Keep it
   to the requirements — no full company research (that is `/target-company`'s job).
2. **Score the 8 dimensions (0-10)** as a PROJECTION from KB coverage (reference §3). Each
   score is what a truthful CV built from this KB could reach on that dimension for this JD.
3. **Pick up to 3 strongest matches** — the JD requirements the KB answers best, each citing
   the JD requirement AND the evidence file + line.
4. **List the fatal gaps** — must-haves with ZERO evidence in the KB; one line each on
   reframe-or-build.
5. **Write the manifest** to `<profile_root>/output/_match/manifests/<jd>.json` following the
   schema in reference §5 (`"fictional": false` for a real run; weights sum to 100).

Progress: "Scored <jd>: projected ~XX (band) · 3 matches · G fatal gap(s)."

---

## Self-Critique Gate (BEFORE rendering the report)

Re-read the Safety Rules. Then check, and fix before running the ranker:
- [ ] No projected score exceeds what its cited evidence file supports.
- [ ] No match invents a skill, metric, or project; every match cites a real KB file + line.
- [ ] Fatal gaps are honest (a hard background gap is not softened into a reframe).
- [ ] Every manifest has weights summing to 100 and `"fictional": false`.
- [ ] British English, "CV" not "resume", dd/mm/yyyy, £.

State the result in one line ("Self-critique: passed" or what you fixed) before Phase 2.

---

## Phase 2: Rank + report

Run the deterministic ranker over the manifests you wrote:

```bash
python cv_builder/helpers/match_jds.py --manifests-dir <profile_root>/output/_match/manifests
```

It writes `<profile_root>/output/_match/match_report.md` — a ranked table (projected total,
band, top match, top fatal gap per JD) plus the fatal-gaps-to-close list. If it exits
non-zero on the page budget, trim per-JD wording in the manifests and re-run. If the helper
is unavailable, rank by projected total by hand using reference §6 and flag it.

### >>>>>> MANDATORY STOP <<<<<<
Present: the ranked table, the top pairing's headline (company + projected band), and the
single gap to close on each of the top 2-3. Then:

"Reverse-match done — report in `<profile_root>/output/_match/match_report.md`. Next:
1. `/target-company <top company> <its JD>` — deep-dive the strongest pairing.
2. Then `/make-cv <that JD>` to realise the projected score."

**You MUST wait for the user's explicit text response before continuing.**

---

## Worked Micro-Example (FICTIONAL — for shape only, NOT real data)

> Invented candidate, five invented JDs (mirrors `eval/fixtures/match_jds/`).

Ranked top and bottom of the table:

| Rank | JD | Company | Projected | Band | Top match | Top fatal gap |
|---|---|---|---|---|---|---|
| 1 | bytework_backend_placement | Bytework | 87.8 | submit | REST APIs in Python | (none) |
| 5 | corewell_embedded_firmware | Corewell | 23.1 | fundamental-issues | — | embedded C on microcontrollers |

The reading: apply to Bytework now (already at ceiling on the evidence); Corewell is a hard
background mismatch, not a wording problem — do not chase it. *Fictional worked example; real
runs score the actual KB against the actual saved JDs.*
