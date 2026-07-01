# claims_schema.md — frozen contracts (M3)

> **FROZEN at P0 (13/06/2026).** P1 linters, P2 validation, P4 eval harness and
> P5 harvester all build against this file. Change requests route to the orchestrator — never
> edit mid-wave. One definition per concept lives HERE; other files may link, never restate
> ([facts-rot-wherever-they-are-restated], [one-comparison-mode-per-sentinel]).

## 1. Claims-inventory file format

A claims inventory is a **JSON Lines** file (`*.claims.jsonl`): UTF-8, **no BOM**, LF line
endings, one JSON object per line, no blank lines, no comments. Field set (all required;
empty values explicit, never omitted):

| Field | Type | Allowed values / shape |
|---|---|---|
| `id` | string | `C-` + 3 digits, unique within the file (e.g. `C-007`) |
| `claim` | string | the claim text exactly as it appears (or will appear) in the deliverable |
| `verb_class` | enum | `full-ownership` \| `hedged` \| `in-progress` \| `neutral` (facts with no ownership verb, e.g. education lines) |
| `source` | string | repo-relative path, optionally `#L<n>` anchor (e.g. `users/<profile>/cv_builder/experience/experience_coding_society.md#L42`). For non-owner CVs (/improve-cv): the subject's CV path — NEVER the `users/<profile>/` owner data |
| `status` | enum | `verified` \| `needs-verify` \| `ask` (fact missing — question issued, claim must not ship) |
| `sentinels` | array of strings | each entry one literal sentinel token from §2 present on/attached to the claim; `[]` if none |
| `evidence` | string | what proves it (repo, deployment, document, person who confirmed + date); `""` only when `status` ≠ `verified` |

**Gold example:**

```json
{"id":"C-007","claim":"Co-built a committee portal used by a 15-member committee","verb_class":"hedged","source":"experience_coding_society.md#L42","status":"verified","sentinels":[],"evidence":"live deployment + repo"}
```

Consistency rules a linter MUST enforce on inventories:
- `verb_class: full-ownership` requires `status: verified` AND `evidence` naming solo work.
- `verb_class: in-progress` requires the §2.3 label inside `claim`, and `source` =
  `cv_builder/experience/experience_pipeline.md` for owner CVs.
- `status: ask` requires an `[ASK: …]` sentinel listed in `sentinels`.

> **Path prefix (both accepted):** a `source` path — and the KB paths in the §2 table below — may be
> written **with or without** a `users/<profile>/` prefix (e.g. `experience_pipeline.md`,
> `cv_builder/experience/…`, or `users/<profile>/cv_builder/experience/…`); all resolve to the active
> profile root for owner CVs and the linter accepts each form. (Reconciles the prefixed example above
> with the bare-rooted in-progress rule and KB table — not a drift.)

## 2. Sentinel definitions (ONE comparison mode each — exact, case-sensitive regex)

| Sentinel | Regex (Python `re`, no flags) | Meaning |
|---|---|---|
| `[VERIFY]` | `\[VERIFY(?::[^\]\n]*)?\]` | fact recorded but unconfirmed; owner must confirm before it may ship |
| `[ASK: …]` | `\[ASK:[^\]\n]+\]` | fact missing; a question has been issued; bullet may not ship with the slot unfilled |
| in-progress label | `\(in progress, expected (0[1-9]|1[0-2])/20[0-9]{2}\)` | planned/in-progress work, present/future tense, max 2 per CV |

Every tool (linter, harvester, skill) MUST use these exact patterns — never a paraphrase,
never a case-insensitive variant. A token that *almost* matches (e.g. `[verify]`,
`(in progress, expected June 2026)`) is a **malformed-sentinel finding**, not a silent pass.

**Where each sentinel is allowed:**

| Location | `[VERIFY]` | `[ASK: …]` | in-progress label |
|---|---|---|---|
| KB (`knowledge_base/`, `cv_builder/experience|support|bundles/`) | yes | yes | yes |
| Drafts, session files, change logs, Open Questions lists | yes | yes | yes |
| **Final deliverables** (see definition below) | **no** | **no** | yes (≤ 2 items, future expected date) |

**Final-deliverable definition (broadened 13/06/2026 — kit-owner approved, RT-2):** under
`output/`, a final deliverable is any `.tex` output, OR a `.md` whose basename stem (extension
stripped, lowercased, with hyphens folded to `_` so `cover-letter.md` matches `cover_letter.md`)
is `cv_*` / `*_cv_improved` / equals one of `cv`, `resume`,
`curriculum_vitae`, `curriculumvitae`, `cover_letter`, `coverletter` / ends with one of `_cv`,
`_resume`, `_cover_letter`, `_coverletter`, `_cv_improved`. The match is on **word boundaries**
(exact stem or an `_`-delimited suffix), never a bare substring. A draft/analysis artefact whose
name carries a `session` / `critique` / `notes` / `draft` component, or `changelog` / `change_log`
anywhere, stays a DRAFT even if it also contains `cv`/`resume` (e.g. `cv_critique.md`,
`resume_changelog.md`) — drafts are checked first. *Was:* `cv_*.md`, `*_cv_improved.md`, `.tex`
only — a CV named `resume.md` / `cover_letter.md` slipped to DRAFT and silently escaped the
deliverable-only rules; the broadening closes that gap.

**Hyphen fold (14/06/2026, A-F1):** the stem folds `-` to `_` before matching, so a
hyphen-spelled CV or cover letter (`cover-letter.md`, `curriculum-vitae.md`, `jane-resume.md`)
classifies the same as its underscore form. Matching only `_` let it slip to DRAFT and escape
PV-006/007/009 (same gap class as the RT-2 broadening). Draft components match on the folded
stem too, so a hyphen-spelled draft (`cv-critique.md`) stays DRAFT.

## 3. Linter CLI contract (binds `lint_fingerprint.py`, `lint_provenance.py`, and successors)

- **Invocation:** `python cv_builder/helpers/lint_<name>.py <path>... [--format text|json] [--inventory <file.claims.jsonl>]`
  - `<path>` = files or directories; directories recurse over `*.md` and `*.tex`.
  - `--format` defaults to `text`; `json` emits the §3.1 schema on stdout.
  - Unknown flags are **rejected** with exit 2 (never ignored) ([ops-tools-dry-run-by-default]).
  - Linters are read-only — they never modify scanned files. Any future KB-WRITING helper
    (e.g. the P5 harvester) is dry-run by default with an explicit `--apply`.
- **Exit codes:** `0` clean (findings may exist but all carry a valid lint-allow) · `1` at
  least one unallowed finding · `2` usage error OR **any input that cannot be parsed**
  (unreadable file, BOM/undecodable bytes, malformed inventory line). Fail-closed: a file the
  linter cannot parse FAILS the run — it is never skipped ([fail-closed-when-enforcement-state-wont-parse]).
- **Determinism:** same input bytes → byte-identical output. No timestamps, no absolute
  paths (repo-relative only), no dict-ordering nondeterminism, zero network, stdlib only,
  UTF-8 (no BOM) throughout. P4 depends on this for reproducible reports.
- **Performance:** full-repo scan completes in < 5 s (P1 gate).

### 3.1 JSON output schema

```json
{
  "tool": "lint_fingerprint",
  "schema_version": 1,
  "files_scanned": 12,
  "findings": [
    {"path": "output/X/cv_x.md", "line": 14, "rule": "FP-001", "severity": "error",
     "message": "banned word 'leverage'", "allowed": false, "allow_reason": null}
  ],
  "errors": [
    {"path": "bad.claims.jsonl", "line": 3, "message": "unparseable JSON"}
  ],
  "summary": {"errors": 1, "findings": 1, "allowed": 0, "exit_code": 2}
}
```

`errors` non-empty ⇒ exit 2, regardless of findings. Allowed findings stay in `findings`
with `allowed: true` and the reason — bypasses are surfaced, never hidden
([self-protecting-guards-need-a-documented-bypass]).

### 3.2 lint-allow syntax (the documented bypass — per line, never global)

On the offending line or the line immediately above it:

- Markdown: `<!-- lint-allow: <RULE-ID> — <reason> -->`
- LaTeX / plain text: `% lint-allow: <RULE-ID> — <reason>`
- JSON Lines inventories: not allowed — fix the row instead.

A lint-allow without a non-empty reason, or naming a rule that did not fire on that line, is
itself a finding (`META-001`). Rules are never weakened globally.

### 3.3 Rule-ID namespaces (rule selection is P1 builder work; IDs and sources are fixed)

| Namespace | Linter | Extracted from (prose source of truth) |
|---|---|---|
| `FP-xxx` | `lint_fingerprint.py` | `cv_builder/support/ai_fingerprint_rules.md` (deterministic subset: banned words/phrases/adverbs, em-dash count, `-ing` bullet endings, `---` list separators) |
| `PV-xxx` | `lint_provenance.py` | CLAUDE.md Anti-Fabrication Rules + Generation rules + §1–§2 of this file (verb-class consistency, sentinel placement/malformation, in-progress count ≤ 2, LOC/test-count claims) |
| `META-xxx` | both | lint-allow misuse, schema-version mismatch |

Tuning set: the shipped clean fictional deliverables under `eval/fixtures/lint/output/`
(`cv_priya_sharma.md`, `priya_sharma_cover_letter.tex`) must produce **0 false positives**
([guards-ship-with-tests-and-tune-on-real-hits]) — a fresh clone with zero kit-owner data
passes this gate. The kit owner's private instance additionally tunes on its own shipped
deliverables when present. P2 false positives become regression tests.
