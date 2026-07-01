# Match-JDs Reference — /match-jds depth

> Read by `/match-jds`. Holds the lightweight projection rubric, the match-manifest
> schema (the contract `cv_builder/helpers/match_jds.py` validates), and the report
> shape. The SKILL.md holds the workflow and points here — content is NOT duplicated
> between the two files.
>
> Conventions (locked): British English; "CV" not "resume" in prose; dd/mm/yyyy; £.
> Sacred: every projected score cites the knowledge-base evidence that supports it;
> a score never exceeds what the evidence file can truthfully bear.

---

## 1. What this skill is (and is not)

`/match-jds` is the REVERSE of `/target-company`. Where `/target-company` deep-dives
ONE company (web research, a full relevance pass, a bundle), `/match-jds` takes the
knowledge base you already have and scores it against MANY saved JDs at once, then
ranks the pairings — so you spend your effort where you are already a strong fit.

It answers one question: **"Of the roles I have saved, which fit my evidence best
right now, and what is the one gap stopping each?"** Output is a single ranked
report, not a CV and not a bundle. The natural next step on a top pairing is
`/target-company` then `/make-cv`.

It is a PROJECTION tool. A projected band is an honest estimate of what a CV built
from this knowledge base for this JD could score — it is not a scored CV, and it
never licenses a bigger claim than the KB supports.

---

## 2. Inputs and fences

- **Input:** a folder or a list of JD files. Default = the active profile's
  `<profile_root>/JDs/`. Each JD is a saved text file you control.
- **No scraping (fence).** v1 reads ONLY JDs already saved to disk. It never fetches
  a job board or posting — that is both a terms-of-service and a prompt-injection
  surface. To match a new role, save its JD to `<profile_root>/JDs/` first.
- **Read-only enrichment (fence).** If a JD is thin and web context would help, a
  READ-ONLY enrichment agent may search for the company's own pages; the orchestrator
  synthesises a short factual summary, and only that summary informs scoring. No
  writer step ever consumes raw fetched content.
- **Anti-fabrication (fence, overrides everything).** Scores describe the candidate's
  REAL evidence only. Never invent a project, skill, or metric to lift a score. A
  missing must-have is a gap, recorded honestly — not a reason to inflate.

---

## 3. The lightweight projection rubric

Score every JD against the knowledge base on the SAME 8 dimensions and weights as
`critique_framework.md` Part 2, but as a fast PROJECTION from KB coverage rather than
a full five-perspective critique. Each dimension scores 0-10 (weights sum to 100):

| Dimension | Weight | Projection test (0-10) |
|---|---|---|
| `ats_keywords` | 15 | What share of the JD's must-have keywords the KB can cover truthfully? |
| `tagline` | 8 | Can the KB support a strong, role-matched one-line tagline for this JD? |
| `skills` | 10 | How much of the JD's named skills list does the KB actually evidence? |
| `bullet_quality` | 22 | How strong and relevant are the bullets the KB could produce for this role? |
| `projects_evidence` | 15 | How strong and relevant are the projects/repos for this role? |
| `narrative` | 12 | Does the KB tell a coherent story pointing at this role? |
| `company_role_fit` | 13 | Role-type and sector fit; potential for insider vocabulary. |
| `page_visual` | 5 | Is there enough relevant material to fill a page without padding? |

**Projected total** = `sum(score × weight) / 10` on a 0-100 scale (identical maths to
`eval/harness.py`). The Python helper computes this — you supply the per-dimension
scores, it does the arithmetic and the ranking.

**Band labels** (mirror `critique_framework.md` Part 2 and `eval/harness.py`):

| Band | Range | Reading |
|---|---|---|
| `submit` | 85+ | A CV from this KB would likely be at ceiling for this JD. |
| `strong` | 80-84 | Strong fit; one or two targeted moves reach ceiling. |
| `good-foundation` | 75-79 | Good base; a real gap to bridge. |
| `first-draft` | 70-74 | Plausible but needs reframing and/or evidence. |
| `fundamental-issues` | <70 | Weak fit; likely a background gap, not a wording one. |

Honesty rule: a projection is a CEILING estimate of a future HONEST CV, never a
promise and never a licence to overclaim. If a dimension can only score high by
claiming something the candidate cannot defend, it scores low and the gap is named.

---

## 4. Strongest matches and fatal gaps (per JD)

For each JD, alongside the scores, record:

- **Strongest matches (up to 3):** the JD requirements the KB answers best. Each cites
  BOTH the JD requirement AND the evidence file (e.g. "JD 'REST APIs in Python' ←
  `experience/experience_work.md` L12"). These are the bullets a CV would lead with.
- **Fatal gaps:** must-haves with ZERO evidence anywhere in the KB — the
  immediate-rejection risks (same fatal/serious/cosmetic semantics as
  `critique_framework.md`; only the FATAL ones go in the manifest, since those are
  what sink a pairing). For each, one line on whether it is a truthful reframe or a
  hard background gap that needs a built project to close.

---

## 5. Match-manifest schema (the contract the ranker validates)

One JSON manifest per JD, written to `<profile_root>/output/_match/manifests/<jd>.json`.
`cv_builder/helpers/match_jds.py` loads these, ranks them, and renders the report.
It is fail-closed: a missing field, weights not summing to 100, a score outside
[0, 10], or a duplicate `jd` id fails the run.

```json
{
  "jd": "acme_placement",
  "title": "Software Engineering Industrial Placement",
  "company": "Acme Capital",
  "fictional": false,
  "dimensions": {
    "ats_keywords":      {"weight": 15, "score": 8.0},
    "tagline":           {"weight": 8,  "score": 8.0},
    "skills":            {"weight": 10, "score": 7.5},
    "bullet_quality":    {"weight": 22, "score": 8.0},
    "projects_evidence": {"weight": 15, "score": 8.5},
    "narrative":         {"weight": 12, "score": 7.5},
    "company_role_fit":  {"weight": 13, "score": 8.0},
    "page_visual":       {"weight": 5,  "score": 8.0}
  },
  "strongest_matches": [
    {"jd_req": "REST APIs in Python",
     "evidence": "built a Flask API with auth and tests",
     "source": "cv_builder/experience/experience_work.md#L12"}
  ],
  "fatal_gaps": [
    {"requirement": "production on-call experience",
     "note": "no ops evidence in the KB; hard gap, not a reframe"}
  ],
  "source_jd": "users/alice/JDs/acme_placement.txt"
}
```

Set `"fictional": true` ONLY for synthetic fixtures (the locked-decision marker).
Real owner manifests are `false`.

---

## 6. Report shape (produced by the helper)

`python cv_builder/helpers/match_jds.py --manifests-dir <profile_root>/output/_match/manifests`
renders `<profile_root>/output/_match/match_report.md`: a ranked table (rank, JD,
company, projected total, band, top match, top fatal gap), a short "fatal gaps to
close" list, and a one-line "projection only" footer. It is deterministic
(byte-identical for identical manifests) and gated to one page (`--max-lines`,
default 55) — a longer report exits non-zero so per-JD detail gets trimmed.

---

## 7. Worked example (FICTIONAL — for shape only, NOT real data)

> Invented candidate (a final-year CS student) against five invented JDs. Real runs
> score the actual knowledge base against the actual saved JDs. This mirrors the
> shipped done-gate fixtures in `eval/fixtures/match_jds/`.

```text
| Rank | JD | Company | Projected | Band | Top match | Top fatal gap |
|------|----|---------|-----------|------|-----------|---------------|
| 1 | bytework_backend_placement | Bytework | 87.8 | submit | REST APIs in Python | (none) |
| 2 | lumen_fullstack_intern | Lumen | 77.3 | good-foundation | end-to-end web features | production TypeScript |
| 5 | corewell_embedded_firmware | Corewell | 23.1 | fundamental-issues | — | embedded C on microcontrollers |
```

The reading: apply to Bytework now (already at ceiling on the evidence); Lumen is
worth a reframe pass after closing the TypeScript gap; Corewell is a hard background
mismatch, not a wording problem. This block is illustrative only.
