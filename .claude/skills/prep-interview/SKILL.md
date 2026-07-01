---
description: Generate an interview preparation pack from a finished session file — predicted questions, STAR answers built only from your real evidence, honest scripts for the gaps, a commitment/logistics collision check, and a 10-line cheat sheet. Trigger when the user says "prep me for the interview", "interview questions for X", "help me prepare for the X interview", or gives a session file after a critique.
user-invocable: true
---

# /prep-interview

**User input:** `$ARGUMENTS`

Invocation: `/prep-interview <session file> [--profile <name>]`

Parse `$ARGUMENTS`:
- Session file path (e.g. `<profile_root>/output/Acme_Engineer/session_acme_engineer.md`) → read it.
- Session name (e.g. `acme_engineer`) → find `<profile_root>/output/**/session_<name>.md`
  (full search order: `shared_ops.md` "Session File Derivation", owner kit — else that glob).
- Empty → check the newest handoff's Active Sessions for the latest session file (owner kit);
  if none, ask.

This is the post-critique lever ("lever 3"). It turns the SAME verified evidence behind the CV +
cover letter into interview readiness: predicted questions, STAR answers built ONLY from real
evidence, honest scripts for the gaps the critique already found, a commitment/logistics collision
check, and a one-page cheat sheet. It produces ONE artefact: the prep pack. It does not change the
CV or the score.

**Read the depth file once before Phase 1:** `cv_builder/reference/interview_prep_reference.md` —
the question taxonomy, STAR template, honest-gap + commitment-collision patterns, cheat-sheet
format, and verifier checklist. This SKILL.md is the workflow; the reference holds the templates.

---

## Profile resolution (read FIRST)

Resolve the active profile before reading or writing ANY owner data: use `--profile <name>` if
given, else the one-line `users/.active` pointer; set `<profile_root>` = `users/<name>/`.
**Fail-closed** — if `users/<name>/` is absent, STOP and tell the user; never fall back to another
profile. Full rule + the SHARED-vs-profile path list: `shared_ops.md` "Profile Resolution" (owner
kit — where that file is absent, e.g. the public engine, this section IS the full rule). In this
file, `<profile_root>/...` means the resolved `users/<name>/...` path.

---

## Safety Rules (ALWAYS ENFORCED)

**Accuracy > Relevance > Impact > ATS > Brevity**

- **EVIDENCE GATE (sacred).** Every STAR answer and talking point traces to a fact in the knowledge
  base, the experience files, or the session file — cited by `Source:`. An answer the candidate
  cannot defend from real evidence is NOT generated.
- **A gap is handled honestly, never invented over.** Where the JD wants something the candidate
  lacks, produce the honest-gap script (reference §5). Pipeline / roadmap items appear ONLY as
  future intent, never as a present claim; a certification is never stated as passed unless it is.
- Read `<profile_root>/config.md` Provenance Flags + KB Corrections Log before generating. Group and
  AI-assisted work stays hedged in the spoken answers too ("I contributed to…", "I co-built…").
- British English throughout; "CV" not "resume" in prose; dd/mm/yyyy; £.

---

## User Input During Execution

If the user gives a focus directive ("go deep on the technical round", "they'll grill me on ML"):
1. Acknowledge it immediately.
2. If it changes emphasis: weight that question category more heavily in Phase 2.
3. Never restart — resume from the current phase.

---

## Startup

Read `cv_builder/reference/shared_ops.md` for profile resolution and session-file derivation if it
exists (owner kit; absent in the public engine — use the Profile-resolution section above + the
`<profile_root>/output/**/session_<name>.md` glob). Then:
1. Read `CLAUDE.md` — KB Corrections; Active Sessions in the newest handoff (owner kit; skip if absent).
2. Read `<profile_root>/config.md` — Personal Info, Provenance Flags, Role Types (for commitment
   facts like an incoming committee role or availability).
3. Find and read the session file.
4. Read the depth file: `cv_builder/reference/interview_prep_reference.md`.

**Recovery check:** if `prep_<name>.md` already exists, read it and offer to refine or regenerate.

---

## Phase 1: Load context

Read, in this order:
1. **The session file** — JD Analysis (requirements + gaps), Company Context, Framing Strategy,
   Critique Context (reviewer persona, competitive landscape, domain vocabulary).
2. **The knowledge base** — every file in `<profile_root>/knowledge_base/extractions/` and
   `<profile_root>/cv_builder/experience/`, plus `<profile_root>/cv_builder/support/significance_*.md`
   for the depth behind each achievement. This is the STAR evidence base.
3. **`<profile_root>/config.md`** — for commitment/logistics facts (competing roles, availability,
   location, start date).

Progress: "Loaded session + KB: N requirements, G gaps, M evidence items. Building the pack."

---

## Phase 2: Generate the pack

Following `interview_prep_reference.md`:
1. **Predict ≥10 questions** across all five categories (reference §3), INCLUDING one
   commitment/logistics collision (reference §6). Tag each with the reader persona who asks it.
2. **Draft STAR answers** (reference §4) for the behavioural + technical questions, each sourced
   ONLY from the KB and closed with a `Source:` line. Reframe into the role's vocabulary; never
   invent. Hedge shared / AI-assisted work.
3. **Write honest-gap scripts** (reference §5) for each JD gap: acknowledge → bridge to real cited
   evidence → name the labelled roadmap intent (only if genuinely recorded), never a present claim.
4. **Prepare the commitment collision(s)** (reference §6): name it, show the concrete plan that
   makes both commitments compatible or the honest priority.
5. **Write the 10-line cheat sheet** (reference §7).

Write to `<profile_root>/output/<FolderName>/prep_<name>.md` using the reference §9 template.

Progress: "Drafted N questions, K STAR answers (all cited), G gap scripts, 1 collision, cheat sheet."

---

## Self-Critique + Verify Gate (BEFORE presenting)

Run the reference §8 checklist and fix anything before presenting. Then do a **fresh-eyes re-read**
(ideally in a fresh context / verifier) confirming: every answer carries a `Source:`; zero
unevidenced answers; every gap uses the honest script; nothing pipeline/cert is stated as present;
≥10 questions incl. the commitment collision; British English. State the result in one line
("Verify: passed — 0 unevidenced answers" or what you fixed).

---

## >>>>>> MANDATORY STOP <<<<<<
Present: the question count by category, the commitment collision you found, the gap scripts in one
line each, and the cheat sheet. Then:

"Interview prep done — pack in `<profile_root>/output/<FolderName>/prep_<name>.md`. Rehearse the
STAR answers out loud; the cheat sheet is your on-the-day glance aid. Want me to go deeper on any
round (technical / behavioural / the collision)?"

**You MUST wait for the user's explicit text response before continuing.**

---

## Worked Micro-Example (FICTIONAL — for shape only, NOT real data)

> Invented candidate, invented consultancy.

**One commitment collision (fictional):**

> **Collision: incoming society-president term overlaps the placement year.** "I'm the incoming
> president for the 2026–27 term. I've thought about the overlap: my committee handbook lets me
> hand day-to-day running to the vice-president and events team, so I'd chair remotely and keep the
> placement as my priority during working hours. I'd rather name that now than have you wonder."
> *Honest, specific, not a hand-wave.*

*This block is illustrative only; real runs read the actual session file and knowledge base.*
