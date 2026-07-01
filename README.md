# cv-engine

An honesty-gated CV improvement engine: three [Claude Code](https://claude.com/claude-code)
skills plus deterministic Python tooling (stdlib only, fully offline). It fixes and improves
existing CVs — any person, any industry — under one non-negotiable rule: **improving never
means inventing.** Missing facts become questions back to the subject, never invented claims.

> **Everything in this repository is fictional.** Every person, company, CV and job description
> in the eval corpus, fixtures and worked examples is invented, and each such file carries an
> in-file fictional marker. The engine makes exactly one effectiveness claim — the measured
> rubric delta below — and no claims about real users or hiring outcomes.

## The three skills

| Skill | Input | Output |
|---|---|---|
| `/improve-cv <cv> [JD/company]` | Any existing CV (md/txt/tex; pdf via extraction) | Improved content-first markdown CV + change log + open questions |
| `/match-jds [folder or JD files]` | JDs you saved to disk + your profile's knowledge base | Ranked match report: projected fit band per JD, strongest evidence matches, the fatal gap per role |
| `/prep-interview <session file>` | A finished tailoring/critique session record | Interview pack: predicted questions, evidence-cited STAR answers, honest gap scripts, cheat sheet |

`/improve-cv` needs zero setup — it reads only the CV you give it. `/match-jds` and
`/prep-interview` read your own evidence base from a profile you create under `users/<name>/`
(gitignored: personal data never commits to this repo).

## Quickstart

Requires Python 3.12+ and [Claude Code](https://claude.com/claude-code) for the skills
themselves. The engine and its tools are stdlib-only; the test suite is the one thing
that needs an install (`pytest`).

```bash
git clone <this-repo> && cd cv-engine
python -m pip install pytest
python -m pytest -q          # the deterministic suite — green, offline
```

Then open the folder in Claude Code and improve a fictional CV from the corpus:

```
/improve-cv eval/corpus/sales_jordan_pryce.md
```

The deterministic tools also run standalone, no Claude required:

```bash
# Reproduce the measured improvement number (byte-identical on identical inputs)
python eval/harness.py --scores-dir eval/fixtures/scores --out report.md

# Rank the fictional fixture pairings with the JD reverse-matching ranker
python cv_builder/helpers/match_jds.py --manifests-dir eval/fixtures/match_jds --out match_report.md

# Honesty linters (fail-closed) over any markdown/LaTeX you point them at
python cv_builder/helpers/lint_provenance.py README.md
python cv_builder/helpers/lint_fingerprint.py README.md
```

## Measured effectiveness — the only claim this project makes

Running the eval harness over the seven-genre fictional corpus (academic, clinical, corporate,
creative, public sector, sales, trades — each CV deliberately seeded with known failure modes):

- **Mean improvement: +26.3 points** on a weighted 0–100 eight-dimension rubric
  (per-genre deltas +23.7 to +28.5).
- Calibration gate: the scorer must reproduce a known reference case (70.2 → 83.5) within
  ±2 points and score all seven seeded known-bad CVs below 60 before any corpus number is
  reported. `python eval/harness.py --check` runs just this gate; CI runs it on every push.

Read the number honestly: the corpus CVs improve from the high 30s to the mid 60s — they do
not become excellent, because the engine refuses to invent the evidence they lack. What it
adds is structure, honest reframing, genre-correct emphasis, and a list of open questions
whose answers would raise the score further. Real hiring outcomes are deliberately not
measured or claimed.

## How the honesty gate works

- **Claims inventory.** Every improvement run builds an inventory of claims sourced ONLY from
  the subject's own CV and answers. Format and sentinel semantics (`[VERIFY]`, `[ASK: …]`,
  the "(in progress, expected mm/yyyy)" label) are frozen in
  `cv_builder/reference/claims_schema.md` — one definition, every tool conforms.
- **Deterministic linters.** `lint_provenance.py` (fabrication-shaped claims, sentinel misuse,
  unverified-as-final) and `lint_fingerprint.py` (AI-tell phrasing, per
  `cv_builder/support/ai_fingerprint_rules.md`) both fail closed: input they cannot parse
  fails the run rather than being skipped. Documented per-line `lint-allow: <reason>` is the
  only bypass.
- **Genre packs.** `cv_builder/reference/genre_packs.md` defines detection and emphasis rules
  per CV genre, so a nurse's CV is not judged like a developer's.
- **Verification debt is explicit.** `cv_builder/helpers/harvest_verify.py` sweeps a knowledge
  base for unresolved `[VERIFY]`/`[ASK]` sentinels and emits one batched question list
  (dry-run by default).

## Repository map

| Path | What it is |
|---|---|
| `.claude/skills/` | The three skills (each `SKILL.md` is the workflow) |
| `cv_builder/reference/` | Frozen claims schema, genre packs, critique framework, layout budgets, skill depth files |
| `cv_builder/helpers/` | Deterministic tooling + its test suite (stdlib only) |
| `cv_builder/support/ai_fingerprint_rules.md` | The AI-tell ban list the fingerprint linter enforces |
| `eval/` | Harness + fictional seven-genre corpus + fixtures (scores, match manifests, lint cases) |
| `users/` | Your profiles live here locally; gitignored by design |

## Provenance

This is the public engine extract of a private CV kit. The owner-pipeline skills (CV/cover-letter
generation, company deep-dives, knowledge-base building) remain private with the owner's data;
everything the engine needs ships here, with a clean history. Where a skill mentions an owner-kit
file such as `shared_ops.md`, the skill's own inline rule applies in this repository.

## License

MIT — see [LICENSE](LICENSE).
