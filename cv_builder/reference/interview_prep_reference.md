# Interview-Prep Reference — /prep-interview depth

> Read by `/prep-interview`. Holds the question taxonomy, the STAR answer template, the
> honest-gap and commitment-collision patterns, the cheat-sheet format, and the verifier
> checklist. The SKILL.md holds the workflow and points here — content is NOT duplicated
> between the two files.
>
> Conventions (locked): British English; "CV" not "resume" in prose; dd/mm/yyyy; £.
> Sacred: every answer traces to a fact in the knowledge base or session file. An answer the
> KB cannot evidence is NOT generated — a gap is handled honestly, never invented over.

---

## 1. What this skill is

`/prep-interview` is the post-critique lever ("lever 3"). After a CV + cover letter exist for a
JD (a session file), it turns the SAME verified evidence into an interview preparation pack:
predicted questions, STAR answers built only from real evidence, honest scripts for the gaps the
critique already found, and a one-page cheat sheet. It converts a strong paper application into
interview readiness — it does not raise the score and it never manufactures new claims.

It reads the session file (JD analysis, company context, framing, gap assessment) and the
knowledge base. It writes ONE pack. It never fetches or invents; if the session file lacks
company context, it says so and works from what is recorded.

---

## 2. Fences

- **KB-only sourcing (sacred).** Every STAR answer and talking point is built from a fact in the
  knowledge base, the experience files, or the session file — cited by source. Nothing is
  generated that the candidate cannot defend in the room.
- **A gap is not an answer to fabricate.** Where the JD wants something the candidate lacks, the
  pack produces an HONEST-GAP script (§5), never a pretend-competent answer. Pipeline / roadmap
  items appear only as future intent, exactly as the anti-fabrication rules require — never as a
  present claim.
- **Verb discipline carries into speech.** Group and AI-assisted work stays hedged in the spoken
  answers too ("I contributed to…", "I co-built…"), same as on the CV.
- British English; dd/mm/yyyy; £.

---

## 3. Question taxonomy (predict at least 10, across all five categories)

Generate the likely questions for THIS role from the session file's JD analysis, company context,
and reviewer persona. Cover all five categories; the pack must include the commitment/logistics
category explicitly (it is the one candidates least prepare and interviewers most probe).

| # | Category | Where it comes from | Example shape |
|---|----------|---------------------|---------------|
| 1 | Motivation / "why us, why this role" | company context + "why them" angle | "Why this company over a larger graduate scheme?" |
| 2 | Behavioural / STAR | leadership, teamwork, conflict, failure — from roles/society/work | "Tell me about a time you led a team through a problem." |
| 3 | Technical / project deep-dive | the strongest projects (their vocabulary) | "Walk me through how your pipeline avoids hallucination." |
| 4 | Gap-probing | the JD's fatal/serious gaps (critique) | "Do you have any hands-on experience with <their stack>?" |
| 5 | Commitment / logistics collision | dates, availability, competing roles, location | see §6 |

For each predicted question, note which reader persona asks it (recruiter / HM / technical) so the
candidate pitches the depth correctly.

---

## 4. STAR answer template (evidence-cited)

For each behavioural / technical question, draft a STAR answer sourced only from the KB:

- **Situation** — the real context (which project / role / event).
- **Task** — what the candidate was actually responsible for (honest scope — hedge shared work).
- **Action** — what THEY did, in the target role's vocabulary (reframe, never invent).
- **Result** — the real outcome; a number only if the KB records one (else a qualitative result,
  never an estimated figure).

Each answer ends with a `Source:` line citing the evidence (e.g. `Source: event check-in
automation, experience_events_society.md#L20`). If a compelling story has no KB source, it is NOT included.

Keep each answer speakable — 4–6 sentences, not a paragraph wall.

---

## 5. Honest-gap script pattern

For every gap the JD probes (category 4), produce a three-move script — never a fake answer:

1. **Acknowledge honestly** — "I haven't used <X> in production."
2. **Bridge to real, transferable evidence** — the nearest thing the candidate HAS actually done,
   cited. "The closest is <real work> — the underlying method transfers because…"
3. **Name the labelled intent** — if (and only if) it is a genuine recorded roadmap item, state it
   as future intent: "it's next on my roadmap — I've planned <the concrete step>." Never claim it
   is done; never state a cert as passed unless it is.

The script's power is credibility: an interviewer trusts a candidate who is precise about the edge
of their experience far more than one who bluffs.

---

## 6. Commitment / logistics collision (the named category)

Interviewers probe practical collisions hard, and candidates rarely prepare them. Detect them from
the session file + config: competing time commitments (a society leadership role vs a placement
year), location/relocation, start date, availability, visa/right-to-work if relevant.

For each collision, prepare an honest resolution:
- **Name it before they do** — surface the tension truthfully rather than hoping it is missed.
- **Show it is handled** — the concrete plan (delegation, timing, term dates) that makes both
  commitments compatible, OR an honest statement of which takes priority and why.
- **Never paper over it** — a false "no problem at all" reads as either naïve or evasive.

Example collision to always check for a placement applicant: an incoming committee/president role
whose term overlaps the placement year. The honest answer states the term dates, how duties are
delegated or timed, and the candidate's priority — not a hand-wave.

---

## 7. Cheat sheet (10 lines, on-the-day)

Close the pack with a scannable one-pager the candidate can glance at before the call:
- 3 lines: the three strongest stories (one phrase each + the metric if real).
- 3 lines: the three "why us" points (their vocabulary).
- 2 lines: the two gap scripts (one line each).
- 1 line: the commitment-collision answer.
- 1 line: two strong questions to ask them (from the company context).

Ten lines, no more — it is a glance aid, not a script to read aloud.

---

## 8. Self-critique + verifier checklist (before presenting)

Run this gate; then a fresh-eyes re-read (ideally a fresh-context verifier) checks the same:
- [ ] At least 10 predicted questions, covering all five categories, including one commitment
      collision.
- [ ] Every STAR answer and talking point carries a `Source:` citing the KB / session file.
- [ ] Zero unevidenced answers — nothing the candidate could not defend from real evidence.
- [ ] Every gap uses the honest-gap script; no pipeline item or cert stated as a present claim.
- [ ] Group / AI-assisted work stays hedged in the spoken answers.
- [ ] British English; dd/mm/yyyy; £.

State the result in one line before presenting.

---

## 9. Output template — `<profile_root>/output/<Folder>/prep_<name>.md`

```markdown
# Interview Prep — [Company] · [Role]

> Generated dd/mm/yyyy by /prep-interview from session_<name>.md. Every answer traces to the
> knowledge base; gaps are handled honestly, never invented over.

## Predicted questions (N, all five categories)
| # | Category | Question | Asked by |
|---|----------|----------|----------|

## STAR answers
### Q[n]: [question]
- **S / T / A / R** …
- *Source:* [evidence file + line]

## Honest-gap scripts
### Gap: [JD requirement the candidate lacks]
1. Acknowledge … 2. Bridge (cited) … 3. Roadmap intent (if labelled) …

## Commitment / logistics
### Collision: [e.g. incoming president term vs placement year]
- Name it … how it is handled … priority …

## Cheat sheet (10 lines)
1. … (three stories · three why-us · two gap scripts · one collision · two questions to ask)
```

---

## 10. Worked example (FICTIONAL — for shape only, NOT real data)

> Invented candidate applying to an invented consultancy. Real runs read the actual session file
> and knowledge base.

**One honest-gap script (fictional):**

> **Gap: hands-on with their low-code automation stack.** 1. "I haven't built on it in
> production." 2. "The closest is a citation-verified LLM pipeline I built — the grounding and
> evaluation ideas transfer directly to low-code agents." 3. "It's next on my roadmap; I've
> planned the foundation certificate as the first step." *(Never claims the cert or the tool.)*

*This block is illustrative only.*
