---
description: Fix and improve ANY existing CV — any person, any industry — and optionally tailor it to a company. Takes a CV file (md/txt/tex/pdf/docx-extracted); outputs an improved content-first markdown CV + change log + open questions. Trigger when the user gives a CV that is not the kit owner's, or says "improve this CV", "fix my friend's CV", "tailor this CV to <company>".
user-invocable: true
---

# /improve-cv

**User input:** `$ARGUMENTS`

Parse `$ARGUMENTS`:
- First path = the CV to improve (md/txt/tex; pdf → Read tool; docx → ask for an export)
- Optional second path or text = JD / company name / careers URL
- Optional quoted text = owner notes ("she's a nurse moving into management")

If no CV path: ask for one. This skill works for ANYONE — it does NOT assume the kit owner.

---

## Scope rules (how this differs from the owner pipeline)

- **The owner profiles under `users/` (each with its own `config.md`,
  `cv_builder/experience/`, `knowledge_base/`, etc.) are OWNER data — improve-cv NEVER reads them.**
  The subject's identity, claims and contact details come from THEIR CV and THEIR answers only.
- Deliverable is a **content-first markdown CV** (no LaTeX/formatting/compiles — formatting is
  the owner's concern, per kit doctrine).
- Genre is detected, not assumed: read `cv_builder/reference/genre_packs.md` and state the
  detected genre + region + career stage as an assumption the user can correct.

## Safety rules (ALWAYS ENFORCED — the generalised anti-fabrication gate)

**Accuracy > Relevance > Impact > ATS > Brevity**

1. **Improving NEVER means inventing.** Rephrase, restructure, reorder, deduplicate, sharpen
   verbs, surface buried outcomes — but never add a fact (number, tool, title, date, outcome)
   that is not on the CV or explicitly confirmed by the user.
2. Where a stronger bullet NEEDS a missing fact, write the bullet with a `[ASK: …]` slot and
   add it to the Open Questions list instead of guessing.
3. Provenance is preserved: "we/team" claims stay hedged; solo verbs only where the CV/owner
   states solo work. Ambiguous claims → Open Questions.
4. Read `cv_builder/support/ai_fingerprint_rules.md` — all bans apply to rewritten text.
5. Company facts used in tailoring MUST be web-verified (hook-verification rule): verify or
   mark **"UNVERIFIED — confirm before use"**. Never guess company facts.

---

## Phase 1 — Intake & claims inventory

1. Read the CV. Identify: person, target role (stated or implied), genre/region/stage per
   `genre_packs.md` detection heuristics. State assumptions in one line.
2. Build the **claims inventory**: every claim → (claim · evidence present on CV · provenance
   clear/ambiguous · metric present/missing).
3. Produce ONE batch of provenance + missing-fact questions (solo vs team, sources of numbers,
   date gaps, current vs past). Do not drip questions. Low-stakes ambiguities: choose the
   conservative reading, state it, continue.

## Phase 2 — Company / JD tailoring (only if a target was given)

1. If a JD: extract the top 10–15 keywords and the implicit priority order.
2. If a company: 2–4 web searches (what they make/sell, vocabulary, values, recent work).
   Verify any fact you plan to use (rule 5 above).
3. Write a mini reframing map: subject's claims → target's vocabulary (truthful swaps only).

## Phase 3 — Critique (genre-adjusted)

Run `cv_builder/reference/critique_framework.md` with the genre pack substituted for the
UK-student assumptions: reviewer persona from THEIR industry, section/length norms from the
pack, dimension weights re-read through the genre (e.g. Sales: metrics dominate Bullet
Quality; Academic: Publications replace Projects; the 8 dimensions still sum to 100 — state
your adjusted weights). Score it; list Tier 1/2/3 improvements.

## Phase 4 — Improve

1. Rewrite as `<output_dir>/<name>_cv_improved_draft.md` — a **draft** while it still carries
   `[ASK: …]` slots (the honesty rules forbid `[ASK]`/`[VERIFY]` in a *final* deliverable, so a
   pre-answers output is named as a draft and the `_draft` suffix keeps the provenance linter
   from treating it as shippable). Genre-correct section order, every bullet outcome-first in the
   genre's idiom, JD/company vocabulary where truthful, fingerprint-clean.
   - **Profile/summary line = highest invention risk.** "Summarising" the CV is where a synthesised
     industry, seniority span, or tenure total ("8 years in X", "enterprise software") slips in
     stated as fact. Every word of the profile must trace to a claim already on the source CV;
     a span/total/classification the CV does not state is an `[ASK]`, never a synthesis. (P2
     regressions: a Sales draft invented "enterprise software" + "around eight years"; a Creative
     draft invented "seven years in studio".)
   - **NEVER compute years-of-experience from dates.** Subtracting a start year from "now" is
     invention twice over: the CV states no total, and your "now" is unreliable. A tenure/years
     figure is `[ASK: total years in X? your earliest dated role is YYYY]` or omitted — never stated.
   - **Sharpening a bullet ≠ adding scope.** You may strengthen a verb, reorder, de-hype and cut
     filler — but you may NOT add an unstated specific to a real activity: an equipment *type*
     ("counterbalance" forklift from "a forklift"), a working *context* ("live"/energised, "to the
     boards"), a client *name*, a tool, a credential, or a place the source doesn't give. Each is an
     invention, not an improvement; it becomes an `[ASK]`. (P2 regression: a Trades draft added
     "live", "counterbalance" and "to the boards".)
2. Alongside it write `<name>_cv_changelog.md`: per change — before → after → why (one line).
3. End with **Open Questions** (the `[ASK: …]` slots): each one = "if you confirm X, bullet Y
   strengthens to Z".

Default `<output_dir>`: `users/<profile>/output/Improve_<FirstnameLastname>/` (the profile
owner's workspace — matches the P6 layout). A session file
(`session_<name>.md`) records genre, target, assumptions, score, and open questions. If the
subject's name is a placeholder/anonymous, use a descriptive slug (e.g. `Improve_<Genre>Example`).

## Phase 5 — Present & stop

Present: detected genre + score (before → projected after) + the top 5 changes + Open
Questions. **STOP and wait for answers/approval.** When answers arrive, fold them in (filled
`[ASK]` slots become real claims, removing every sentinel), re-score the changed dimensions only,
and write the final `<name>_cv_improved.md` (now `[ASK]`-free — the deliverable).

---

## Done criteria

- Improved md CV with zero invented facts, zero `[ASK]` slots presented as claims
- Change log explaining every edit
- Open Questions list (possibly empty)
- Session file updated; owner formats and submits — nothing is sent by the skill
