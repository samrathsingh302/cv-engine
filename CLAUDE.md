# cv-engine — Project Instructions

> Auto-loaded by Claude Code. Honesty-gated CV improvement engine.
> Skills: `/improve-cv` · `/match-jds` · `/prep-interview`. All example people are FICTIONAL.

## Conventions

- British English; dd/mm/yyyy; £. "CV" not "resume" in prose (US terms only when explaining US concepts).
- Commands: `python` (never `python3`). Optional LaTeX check: `tectonic <file>.tex`.
- Deterministic tooling lives in `cv_builder/helpers/`; run `python -m pytest` for the suite.

## Anti-Fabrication Rules (CRITICAL — override everything else)

- **Accuracy > Relevance > Impact > ATS > Brevity.** When torn between an impressive-but-inaccurate
  claim and an accurate one, ALWAYS choose accuracy.
- Claims come ONLY from the subject's own CV, their answers, or their own profile data. Never invent
  facts, metrics, employers, dates, or credentials. Missing facts become open questions.
- **Full-ownership verbs** (Built, Developed, Designed, Implemented) only for solo work; **hedged
  verbs** (Contributed, Co-built, Supported) for shared or team work. When in doubt, hedge.
- Planned/in-progress work appears ONLY labelled "(in progress, expected mm/yyyy)" — never as completed.
- No lines-of-code or test counts in CV output; no code folder/repo names used as if they are products.
- Claims-inventory format and sentinel semantics (`[VERIFY]` / `[ASK: …]` / in-progress label) are
  FROZEN in `cv_builder/reference/claims_schema.md` — one definition, every tool conforms.

## Profiles

- A user's own data lives under `users/<profile>/` (gitignored — personal data never commits here).
- Skills resolve `--profile <name>`, else the one-line `users/.active` pointer, else the generic
  `default`. **Fail closed** if the profile dir is missing — never a silent fallback to another
  profile. Resolver: `cv_builder/helpers/profile.py`.
- `/improve-cv` needs NO profile — it works from the subject's CV alone and never reads `users/`.

## The engine's own claims

- The only effectiveness claim is the eval harness's measured rubric delta on the FICTIONAL corpus:
  `python eval/harness.py --scores-dir eval/fixtures/scores` — never anything about real users or
  hiring outcomes. Every fictional artefact carries an in-file fictional marker.
