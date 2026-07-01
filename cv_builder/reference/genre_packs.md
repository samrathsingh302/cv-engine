# Genre Packs — field-agnostic CV conventions

> Read by `/improve-cv` (and any skill working on a non-owner CV). Detect the genre from the
> CV itself + any JD, then apply that pack's conventions. When genres conflict, the JD's
> industry wins. Default pack: Corporate-Professional.
> Page/character budgets for any genre live in `layout_budgets.md`.

## Detection heuristics

Read the CV for: job titles, section names, qualification types (degree vs certification vs
licence vs portfolio), region signals (spelling, date format, "CV" vs "resume", A4/letter),
career stage (years of experience, seniority of titles). State the detected genre + region +
stage to the user as an assumption; proceed unless corrected.

## Packs

| Pack | Section order | Length norm | Tone & verbs | Metrics norm | Red flags to fix |
|---|---|---|---|---|---|
| **Corporate-Professional (default)** | Profile → Experience → Skills → Education | 2pp (UK), 1–2pp (US) | active verbs, outcome-first | £/%/time saved, team sizes, budgets | duty-lists with no outcomes; first person pronouns everywhere |
| **Tech / Engineering** | Profile → Skills or Experience → Projects → Education | 1–2pp | built/shipped language, stack named | users, latency, scale, uptime | tool soup with no evidence; projects without outcomes |
| **Academic / Research** | Education → Research → Publications → Teaching → Grants | no page cap | discipline-standard, third-person-ish | citations, grants £, cohort sizes | publications missing/cut; page-count anxiety (don't trim) |
| **Clinical / Healthcare** | Registration/Licences → Experience → Education → CPD | 2pp+ | precise, protocol-aware | caseloads, audit results | missing registration numbers/CPD; vague claims about patient outcomes |
| **Trades / Operations** | Tickets/Certs → Experience → Skills | 1–2pp | concrete, safety-aware | jobs completed, safety record, equipment | missing tickets/cards (CSCS etc.); soft-skill padding |
| **Creative / Portfolio** | Profile → Selected work (linked) → Experience → Education | 1pp + portfolio link | voice allowed, client-first | audiences, engagement, clients | no portfolio link; describing instead of showing |
| **Sales / Commercial** | Profile → Experience (numbers-led) → Education | 1–2pp | target/quota language | % of quota, pipeline £, retention | numberless bullets (fatal in this genre) |
| **Public Sector / NGO (UK)** | Profile → Experience vs person-spec → Education | 2pp, spec-driven | criteria-mirroring | service volumes, outcomes | ignoring the person specification's exact wording |

## Universal rules (all genres — these never vary)

1. **Anti-fabrication:** improving a CV NEVER adds facts. Rephrase, reorder, sharpen — but any
   strengthening that needs a new fact (a number, a tool, an outcome) becomes a QUESTION for
   the owner, never an invention.
2. **Provenance:** solo vs team framing preserved unless the owner confirms otherwise.
3. **Dates:** one consistent format; gaps surfaced to the owner, not papered over.
4. **AI-fingerprint rules** (`ai_fingerprint_rules.md`) apply to all genres.
5. **Accuracy > Relevance > Impact > ATS > Brevity** — unchanged everywhere.
