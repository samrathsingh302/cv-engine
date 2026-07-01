"""Tests for lint_fingerprint.py (FP-xxx).

Each FP rule fires on a minimal inline fixture; the scan policy, lint-allow
honouring + META-001 misuse, JSON shape, and determinism are covered. All
fixtures are minted here (test-helpers-own-throwaway-data) — never copied from
real outputs. Fixtures live under output/ paths inside tmp_path so the FP scan
policy treats them as deliverables (not exempt docs).
"""

from _runner import run_json


def _rules(mod, path):
    code, doc = run_json(mod, [path])
    return code, [f["rule"] for f in doc["findings"]], doc


# --- Each rule fires on a minimal fixture ----------------------------------
def test_fp001_banned_word_fires(fp_mod, writer):
    # A deliverable CV under output/ so FP rules apply.
    p = writer("output/cv_x.md", "- We will leverage the platform to ship faster.\n")
    code, rules, doc = _rules(fp_mod, p)
    assert "FP-001" in rules
    assert code == 1
    msg = next(f["message"] for f in doc["findings"] if f["rule"] == "FP-001")
    assert "leverage" in msg


def test_fp001_inflection_fires(fp_mod, writer):
    p = writer("output/cv_x.md", "- Utilised the API and showcased the result.\n")
    _, rules, _ = _rules(fp_mod, p)
    assert rules.count("FP-001") == 2  # utilised + showcased


def test_fp001_whole_word_only(fp_mod, writer):
    # "noveltea" must NOT match banned "novel"; "delved" must.
    p = writer("output/cv_x.md", "- The noveltea shop was nice.\n")
    _, rules, _ = _rules(fp_mod, p)
    assert "FP-001" not in rules


def test_fp001_emphasis_split_fires(fp_mod, writer):
    # RT-3 regression: markdown emphasis used to hide a banned word from the
    # reader's eye ("lev*er*age" / "lev_er_age" render as italic "leverage").
    # The FP-001 view strips intraword emphasis, so both now fire.
    body = "- We lev*er*age the platform and lev_er_age the data.\n"
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(fp_mod, p)
    assert rules.count("FP-001") == 2


def test_fp001_snake_case_identifier_ok(fp_mod, writer):
    # RT-3 caveat: a snake_case identifier embedding a banned lemma must NOT match
    # — it is not a standalone word a reader reads as the banned term.
    body = "- Called the use_leverage_helper and read the leverage_score column.\n"
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(fp_mod, p)
    assert "FP-001" not in rules


def test_fp001_hyphen_split_fires(fp_mod, writer):
    # RT-3 regression: a hyphen on either side of a banned lemma used to block the
    # whole-word rule. co-leverage / non-utilise / innovative-solution now fire.
    body = (
        "- A co-leverage and re-leverage and non-utilise approach.\n"
        "- An innovative-solution wins.\n"
    )
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(fp_mod, p)
    # leverage (x2) + utilise + innovative
    assert rules.count("FP-001") == 4
    msgs = [f["message"] for f in _rules(fp_mod, p)[2]["findings"] if f["rule"] == "FP-001"]
    assert any("hyphen-split" in m for m in msgs)


def test_fp001_unrelated_hyphenates_ok(fp_mod, writer):
    # RT-3 caveat: ordinary hyphenated compounds with no banned segment stay clean.
    body = "- A state-of-the-art real-time well-known event-driven system.\n"
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(fp_mod, p)
    assert "FP-001" not in rules


def test_fp001_cutting_edge_still_caught(fp_mod, writer):
    # The already-banned hyphenated lemma must STAY caught (no regression) and not
    # be double-reported by the hyphen-split path (its segments aren't banned).
    p = writer("output/cv_x.md", "- A cutting-edge tool.\n")
    _, rules, _ = _rules(fp_mod, p)
    assert rules.count("FP-001") == 1


def test_fp001_zero_width_split_fires(fp_mod, writer):
    # A-F5 regression: a zero-width space (U+200B) splits the banned word so it
    # renders as "leverage" to a reader but used to slip the whole-word matcher.
    # The FP-001 view strips zero-width chars, so it now fires.
    body = "- We lev​erage the platform to ship faster.\n"
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(fp_mod, p)
    assert "FP-001" in rules


def test_fp001_soft_hyphen_split_fires(fp_mod, writer):
    # A-F5 regression: a soft hyphen (U+00AD) is reader-invisible inside a word;
    # "ut­ilise" renders as "utilise". The FP-001 view strips it, so it fires.
    body = "- We ut­ilise the API across the stack.\n"
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(fp_mod, p)
    assert "FP-001" in rules


def test_fp001_no_zero_width_unchanged(fp_mod, writer):
    # A-F5 negative: a clean line with no invisible chars gains no new finding.
    body = "- Built a tested parser, cutting parse time by 30%.\n"
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(fp_mod, p)
    assert rules == []


def test_fp002_zero_width_split_fires(fp_mod, writer):
    # A-F5 regression: a zero-width joiner (U+200D) split inside a phrase word
    # ("pro‍ven track record") renders as the banned phrase but slipped the
    # phrase matcher; the FP-002 view now strips zero-width chars, so it fires.
    body = "- I have a pro‍ven track record of delivery.\n"
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(fp_mod, p)
    assert "FP-002" in rules


def test_fp002_banned_phrase_fires(fp_mod, writer):
    p = writer("output/cv_x.md", "- I have a proven track record of delivery.\n")
    code, rules, doc = _rules(fp_mod, p)
    assert "FP-002" in rules
    assert "proven track record" in next(
        f["message"] for f in doc["findings"] if f["rule"] == "FP-002")


def test_fp002_curly_apostrophe_fires(fp_mod, writer):
    # FP-2-1 regression: a curly apostrophe (U+2019) used to defeat the banned
    # phrase "in today's rapidly evolving". Curly quotes/apostrophes are folded to
    # ASCII before phrase matching, so it now fires.
    body = "In today’s rapidly evolving market we win.\n"
    p = writer("output/cv_x.md", body)
    code, rules, doc = _rules(fp_mod, p)
    assert "FP-002" in rules
    assert "in today's rapidly evolving" in next(
        f["message"] for f in doc["findings"] if f["rule"] == "FP-002")


def test_fp002_clean_phrase_ok(fp_mod, writer):
    # TQ-4: a clean negative for FP-002 — near-misses of the banned phrases must
    # NOT fire. "a track record of wins" lacks "proven"; "I am excited about the
    # role and the team" lacks "to apply". No -ing ending (so FP-004 stays quiet).
    body = (
        "- I have a track record of wins across the team.\n"
        "- I am excited about the role and the team here.\n"
    )
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(fp_mod, p)
    assert "FP-002" not in rules


def test_fp003_em_dash_over_two(fp_mod, writer):
    # Three in-prose `---` runs in one document -> FP-003 (max 2).
    body = "Alpha --- beta and gamma --- delta and epsilon --- zeta.\n"
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(fp_mod, p)
    assert "FP-003" in rules


def test_fp003_two_em_dashes_ok(fp_mod, writer):
    body = "Alpha---beta then gamma---delta only.\n"
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(fp_mod, p)
    assert "FP-003" not in rules


def test_fp004_ing_bullet_ending_fires(fp_mod, writer):
    p = writer("output/cv_x.md", "- Refactored the service, improving efficiency\n")
    code, rules, doc = _rules(fp_mod, p)
    assert "FP-004" in rules
    assert "improving" in next(
        f["message"] for f in doc["findings"] if f["rule"] == "FP-004")


def test_fp004_concrete_metric_ending_ok(fp_mod, writer):
    p = writer("output/cv_x.md", "- Refactored the service, cutting latency by 30%\n")
    _, rules, _ = _rules(fp_mod, p)
    assert "FP-004" not in rules


def test_fp004_capitalized_gerund_fires(fp_mod, writer):
    # FP-4-1 regression: a CAPITALISED trailing gerund used to slip because the
    # concrete-tail escape matched the gerund's OWN leading capital. The escape
    # must now look at the tail AFTER the gerund, so these vague endings fire.
    body = (
        "- Refactored the service, Improving deployment speed\n"
        "- Tuned the query layer, Enabling cleaner queries\n"
        "- Sped up the build, Accelerating delivery\n"
    )
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(fp_mod, p)
    assert rules.count("FP-004") == 3


def test_fp004_propernoun_after_gerund_ok(fp_mod, writer):
    # A genuine proper-noun / acronym AFTER the gerund still excuses the bullet:
    # the concrete anchor is real, not the gerund's own capital.
    body = (
        "- Worked on integration, Integrating with Salesforce\n"
        "- Shipped the service, Building the API\n"
    )
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(fp_mod, p)
    assert "FP-004" not in rules


def test_fp004_metric_after_gerund_ok(fp_mod, writer):
    # A metric tail after the gerund excuses it (ends on a concrete figure).
    p = writer("output/cv_x.md", "- Cut spend, contributing to a 15% reduction\n")
    _, rules, _ = _rules(fp_mod, p)
    assert "FP-004" not in rules


def test_fp004_driving_licence_not_flagged(fp_mod, writer):
    # P2 pilot false positive: "driving" is a participial adjective in the
    # compound noun "driving licence", not a vague gerund analysis ending.
    p = writer("output/cv_x.md", "- Other: full UK driving licence\n")
    _, rules, _ = _rules(fp_mod, p)
    assert "FP-004" not in rules


def test_fp004_wrapped_bullet_not_misread(fp_mod, writer):
    # The wrapped-bullet false-positive class: a multi-line bullet whose SOURCE
    # line ends in "...a running" but whose LOGICAL ending is "...exactly." must
    # not fire FP-004.
    body = (
        "- Financial correctness by design: money held in integer pence, a running\n"
        "  In/Out ledger, and a CSV export so the treasurer can reconcile exactly.\n"
    )
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(fp_mod, p)
    assert "FP-004" not in rules


def test_fp004_three_word_abstract_outcome_fires(fp_mod, writer):
    # A-F3: FP-004 used to MISS its own documented example because the gerund-tail
    # window was {0,2} and "to improved efficiency" is three words. The precise
    # to/of + modifier arm now catches this abstract-outcome ending.
    body = (
        "- Refactored the service, contributing to improved efficiency\n"
        "- Tuned the pipeline, leading to enhanced performance\n"
    )
    p = writer("output/cv_x.md", body)
    _, rules, doc = _rules(fp_mod, p)
    assert rules.count("FP-004") == 2
    assert "contributing to improved efficiency" in next(
        f["message"] for f in doc["findings"] if f["rule"] == "FP-004")


def test_fp004_three_word_abstract_outcome_fail_before(fp_mod, writer):
    # Fail-before proof: the OLD {0,2} pattern did NOT fire on the documented
    # example (no match -> no finding), so the new behaviour is a real change, not
    # a tautology. We rebuild the pre-fix pattern and confirm it leaves the tail
    # un-flagged, then confirm the LIVE rule flags it.
    import re
    old_pattern = re.compile(r"\b([a-z]{3,}ing)\b((?:\s+[a-z]+){0,2})\s*$",
                             re.IGNORECASE)
    tail = "contributing to improved efficiency"
    assert old_pattern.search(tail) is None  # old window misses it (the bug)
    p = writer("output/cv_x.md", "- Refactored the service, %s\n" % tail)
    _, rules, _ = _rules(fp_mod, p)
    assert "FP-004" in rules  # live rule now catches it


def test_fp004_honest_three_word_tails_stay_clean(fp_mod, writer):
    # A-F3 false-positive guard (the red-gate risk a naive {0,3} window created):
    # honest committed bullets whose -ing word is a preposition or plain participle
    # and whose 3-word tail is concrete/real MUST stay clean. These mirror real
    # deliverables in the corpus (retail / clinical / ecology CV bullets).
    body = (
        "- Served customers and handled cash during busy weekend shifts\n"
        "- Supported ward nurses: washing, feeding and mobility assistance\n"
        "- Built the data pipeline, covering three upland sites\n"
        "- Drafted the section, framing in any form\n"
        '- Avoid the phrase "I am writing to apply for"\n'
    )
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(fp_mod, p)
    assert "FP-004" not in rules


def test_fp004_pair_programming_not_flagged(fp_mod, writer):
    # A whitelisted -ing noun ending a bullet ("pair-programming") is an object,
    # not a vague gerund analysis ending; it must not fire.
    p = writer("output/cv_x.md", "- Skills: code review and pair-programming\n")
    _, rules, _ = _rules(fp_mod, p)
    assert "FP-004" not in rules


def test_fp004_concrete_anchor_in_three_word_tail_ok(fp_mod, writer):
    # The concrete-anchor escape still applies inside the wider arm: a metric or a
    # proper noun after the gerund excuses the bullet even when the tail is long.
    body = (
        "- Cut spend, contributing to a 15% reduction\n"
        "- Migrated the stack, moving to managed Azure\n"
    )
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(fp_mod, p)
    assert "FP-004" not in rules


def test_fp004_improvement_modifier_three_word_fires(fp_mod, writer):
    # A-F3 (S4b): the 3-word arm fires on the IMPROVEMENT/OUTCOME shape — gerund +
    # to/of + an improvement modifier + an abstract noun. All four documented
    # must-fire endings (improved/increased/enhanced/reduced) are caught.
    body = (
        "- Refactored the service, contributing to improved efficiency\n"
        "- Tuned the pipeline, leading to increased adoption\n"
        "- Reworked the layer, contributing to enhanced performance\n"
        "- Trimmed the budget, moving to reduced costs\n"
    )
    p = writer("output/cv_x.md", body)
    _, rules, doc = _rules(fp_mod, p)
    assert rules.count("FP-004") == 4
    msgs = [f["message"] for f in doc["findings"] if f["rule"] == "FP-004"]
    assert any("moving to reduced costs" in m for m in msgs)


def test_fp004_technical_migration_three_word_stays_clean(fp_mod, writer):
    # A-F3 (S4b) — the residual FP class an independent verifier found: the precise
    # 3-word arm used to admit "to/of + ANY -ed/-ing word + noun", so honest concrete
    # migration bullets fired wrongly because automated/encrypted/distributed/
    # replicated/hosted are TECHNICAL-DESCRIPTIVE modifiers, not improvement language.
    # Restricting the modifier to the improvement allow-list (plus "computing" in the
    # -ing noun whitelist for the bare-gerund tail) keeps all six clean.
    body = (
        "- Reduced toil, moving to automated testing\n"
        "- Adopted CI, transitioning to automated deployment\n"
        "- Hardened the store, switching to encrypted storage\n"
        "- Re-platformed, moving to distributed computing\n"
        "- Re-platformed, moving to replicated databases\n"
        "- Re-platformed, scaling to hosted infrastructure\n"
    )
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(fp_mod, p)
    assert "FP-004" not in rules


def test_fp004_technical_migration_fired_before_fix(fp_mod, writer):
    # Fail-before proof for the S4b fix: the A-F3 "any -ed/-ing word" arm WOULD have
    # fired on these honest migration bullets (the bug), proving the allow-list is a
    # real narrowing, not a tautology. We rebuild the pre-S4b pattern and confirm it
    # matches the descriptive-modifier tails; the LIVE rule now leaves them clean.
    import re
    old_arm = re.compile(
        r"\b([a-z]{3,}ing)\b("
        r"(?:\s+(?:to|of)\s+[a-z]+(?:ed|ing)\s+[a-z]+)"  # the over-broad A-F3 arm
        r"|(?:\s+[a-z]+){0,2}"
        r")\s*$", re.IGNORECASE)
    for tail in ("moving to automated deployment",
                 "switching to encrypted storage",
                 "moving to replicated databases"):
        m = old_arm.search(tail)
        # The over-broad arm matched the WHOLE descriptive-modifier tail (3 words),
        # not just a bare trailing gerund — that was the false positive.
        assert m is not None and m.group(0).strip() == tail
    p = writer("output/cv_x.md",
               "- Adopted CI, switching to encrypted storage\n")
    _, rules, _ = _rules(fp_mod, p)
    assert "FP-004" not in rules  # live rule now leaves it clean


def test_fp004_computing_noun_ending_not_flagged(fp_mod, writer):
    # "computing" is a noun-object ending (distributed/cloud/quantum computing),
    # added to the -ing noun whitelist so a bare-gerund base-window tail stays clean.
    body = (
        "- Migrated the stack to distributed computing\n"
        "- Specialise in cloud computing\n"
    )
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(fp_mod, p)
    assert "FP-004" not in rules


def test_fp005_inline_separator_fires(fp_mod, writer):
    p = writer("output/cv_x.md", "Did X --- then did Y as a follow-up.\n")
    _, rules, _ = _rules(fp_mod, p)
    assert "FP-005" in rules


def test_fp005_markdown_table_delim_not_flagged(fp_mod, writer):
    # A markdown table delimiter row legitimately uses --- and must NOT fire
    # FP-003 or FP-005 (the table-delimiter false-positive class).
    body = (
        "| Claim | Evidence | Source |\n"
        "|---|---|---|\n"
        "| a | b | c |\n"
    )
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(fp_mod, p)
    assert "FP-005" not in rules
    assert "FP-003" not in rules


def test_fp003_thematic_break_not_counted(fp_mod, writer):
    # Three horizontal-rule lines are structure, not em-dashes.
    body = "Intro\n\n---\n\nmiddle\n\n---\n\nmore\n\n---\n\nend\n"
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(fp_mod, p)
    assert "FP-003" not in rules


def test_fp003_em_dash_glyph_prose_over_two_fires(fp_mod, writer):
    # The reader-visible em-dash glyph (U+2014) in flowing markdown prose is the
    # actual AI tell — three in a sentence must fire FP-003 (the .tex `---` source
    # spelling does not exist in markdown, so glyph-blindness was a real gap).
    body = "I built the system — and shipped it — then iterated — fast.\n"
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(fp_mod, p)
    assert "FP-003" in rules


def test_fp003_em_dash_glyph_structural_lines_ok(fp_mod, writer):
    # Em-dash glyphs in markdown HEADINGS and `**Label** — value` entries are
    # legitimate CV structure, not the prose tell (the heading / label-line
    # false-positive class) — six of them must NOT fire FP-003.
    body = (
        "# Jane Roe — CV\n\n"
        "### Acme — Engineer\n"
        "### Globex — Analyst\n\n"
        "**MIT** — BSc Computer Science\n"
        "**Eton** — A-levels\n\n"
        "- Built the parser solo.\n"
    )
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(fp_mod, p)
    assert "FP-003" not in rules


def test_fp003_em_dash_glyph_blockquote_prose_fires(fp_mod, writer):
    # A blockquote is quoted PROSE — em-dash overuse inside it is still the tell.
    body = "> I led the team — shipped it — and scaled it — well.\n"
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(fp_mod, p)
    assert "FP-003" in rules


def test_fp003_en_dash_ranges_not_counted(fp_mod, writer):
    # The en-dash U+2013 (date/number ranges) is never an em-dash — four ranges
    # in one document must NOT fire FP-003.
    body = "Westhaven 2023–28, term 2026–27, grades 8–9, weeks 4–6 of work.\n"
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(fp_mod, p)
    assert "FP-003" not in rules


def test_fp003_mixed_em_dash_class_glyphs_fire(fp_mod, writer):
    # A-F5 regression: only U+2014 used to count, so swapping in U+2015 (horizontal
    # bar) / U+2012 (figure dash) evaded the budget. Three mixed em-dash-class
    # glyphs (one each of U+2014, U+2015, U+2012) in prose must now fire FP-003.
    body = "I built it — shipped it ― then iterated ‒ fast.\n"
    p = writer("output/cv_x.md", body)
    _, rules, doc = _rules(fp_mod, p)
    assert "FP-003" in rules
    assert "3 em-dashes" in next(
        f["message"] for f in doc["findings"] if f["rule"] == "FP-003")


def test_fp003_horizontal_bar_glyph_counts(fp_mod, writer):
    # A-F5: three U+2015 horizontal bars alone (no U+2014) must fire — the widened
    # count is not limited to the original em-dash glyph.
    body = "I led it ― scaled it ― and shipped it ― well.\n"
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(fp_mod, p)
    assert "FP-003" in rules


def test_fp003_two_mixed_class_glyphs_ok(fp_mod, writer):
    # A-F5 boundary: exactly two em-dash-class glyphs (one U+2014, one U+2015) are
    # within the max-2 budget and must NOT fire (no over-count off-by-one).
    body = "I built it — and shipped it ― only.\n"
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(fp_mod, p)
    assert "FP-003" not in rules


def test_fp003_bold_lead_prose_not_exempt(fp_mod, writer):
    # A prose line that merely STARTS with a **Label:** lead-in but carries 2+
    # em-dashes is prose wearing a label — its em-dashes are the tell (verifier F1).
    body = "**Profile:** I built it — shipped it — scaled it — fast.\n"
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(fp_mod, p)
    assert "FP-003" in rules


def test_fp001_underscore_wrap_fires(fp_mod, writer):
    # Markdown-italic _leverage_ / __utilize__ render as the banned word (verifier
    # F3): the `_` is a word char so the banned boundary alone misses them.
    p = writer("output/cv_x.md", "- We _leverage_ and __utilize__ the stack.\n")
    _, rules, _ = _rules(fp_mod, p)
    assert rules.count("FP-001") >= 2


def test_fp001_unpaired_underscore_identifier_ok(fp_mod, writer):
    # An unpaired leading-underscore identifier (_leverage) and snake_case
    # (use_leverage_helper) must NOT be flagged — only PAIRED wraps are stripped.
    p = writer("output/cv_x.md", "- Called _leverage and use_leverage_helper here.\n")
    _, rules, _ = _rules(fp_mod, p)
    assert "FP-001" not in rules


def test_tex_comment_excluded(fp_mod, writer):
    # A LaTeX comment banner with --- and a banned word is reader-invisible.
    body = (
        "% --- Letterhead with leverage and harness ---\n"
        "\\item Built a thing with measured results.\n"
    )
    p = writer("output/x.tex", body)
    _, rules, _ = _rules(fp_mod, p)
    assert rules == []


# --- Scan policy: rulebook/doc paths exempt --------------------------------
def test_scan_policy_exempts_docs(fp_mod, writer):
    # Same banned content under a doc path is exempt; under output/ it fires.
    text = "- We leverage a robust comprehensive approach.\n"
    p_doc = writer("docs/notes.md", text)
    p_del = writer("output/cv_x.md", text)
    _, rules_doc, _ = _rules(fp_mod, p_doc)
    _, rules_del, _ = _rules(fp_mod, p_del)
    assert rules_doc == []
    assert "FP-001" in rules_del


def test_scan_policy_exempts_output_analysis(fp_mod, writer):
    # critique_/session_ files under output/ discuss banned phrases by name.
    text = '- reviewer eye-rolls at "passionate about AI" and leverage-speak.\n'
    p = writer("output/critique_x.md", text)
    _, rules, _ = _rules(fp_mod, p)
    assert rules == []


def test_scan_policy_exempts_config_md(fp_mod, writer):
    # config.md is owner data/config (provenance flags, education lines), read BY
    # the skills — not a generated deliverable. Same prose em-dash run that fires
    # under a deliverable path must be exempt under config.md.
    body = "I built it — shipped it — scaled it — fast.\n"
    p_cfg = writer("config.md", body)
    p_del = writer("output/cv_x.md", body)
    _, rules_cfg, _ = _rules(fp_mod, p_cfg)
    _, rules_del, _ = _rules(fp_mod, p_del)
    assert rules_cfg == []
    assert "FP-003" in rules_del  # same content IS the tell under a deliverable path


# --- lint-allow honoured + META-001 ----------------------------------------
def test_lint_allow_honoured_same_line(fp_mod, writer):
    body = "- We leverage X. <!-- lint-allow: FP-001 — quoting the JD verbatim -->\n"
    p = writer("output/cv_x.md", body)
    code, doc = run_json(fp_mod, [p])
    f = next(f for f in doc["findings"] if f["rule"] == "FP-001")
    assert f["allowed"] is True
    assert f["allow_reason"] == "quoting the JD verbatim"
    assert code == 0  # allowed-only findings -> clean exit


def test_lint_allow_honoured_line_above(fp_mod, writer):
    body = (
        "<!-- lint-allow: FP-001 — literal landscape term -->\n"
        "- The free energy landscape was mapped.\n"
    )
    p = writer("output/cv_x.md", body)
    code, doc = run_json(fp_mod, [p])
    f = next(f for f in doc["findings"] if f["rule"] == "FP-001")
    assert f["allowed"] is True
    assert code == 0


def test_meta001_empty_reason(fp_mod, writer):
    body = "- We leverage X. <!-- lint-allow: FP-001 -->\n"
    p = writer("output/cv_x.md", body)
    code, doc = run_json(fp_mod, [p])
    rules = [f["rule"] for f in doc["findings"]]
    assert "META-001" in rules
    # FP-001 still present and NOT allowed (no reason).
    fp1 = next(f for f in doc["findings"] if f["rule"] == "FP-001")
    assert fp1["allowed"] is False
    assert code == 1


def test_meta001_rule_did_not_fire(fp_mod, writer):
    # Allow names FP-002 but only FP-001 fired here.
    body = "- We leverage X. <!-- lint-allow: FP-002 — wrong rule named -->\n"
    p = writer("output/cv_x.md", body)
    code, doc = run_json(fp_mod, [p])
    rules = [f["rule"] for f in doc["findings"]]
    assert "META-001" in rules
    assert "FP-001" in rules


# --- JSON shape (schema §3.1) ----------------------------------------------
def test_json_shape(fp_mod, writer):
    p = writer("output/cv_x.md", "- We leverage X.\n")
    code, doc = run_json(fp_mod, [p])
    assert doc["tool"] == "lint_fingerprint"
    assert doc["schema_version"] == 1
    assert set(doc.keys()) == {
        "tool", "schema_version", "files_scanned", "findings", "errors", "summary"}
    assert set(doc["summary"].keys()) == {"errors", "findings", "allowed", "exit_code"}
    for f in doc["findings"]:
        assert set(f.keys()) == {
            "path", "line", "rule", "severity", "message", "allowed", "allow_reason"}
    assert doc["summary"]["exit_code"] == code


# --- Fail-closed: the SCANNED-file path (BOM, undecodable bytes) -----------
def test_fp_scanned_bom_exit2(fp_mod, tmp_path):
    # TQ-2: a scanned deliverable with a leading UTF-8 BOM fails the run closed
    # (the FP read path mirrors the provenance linter's fail-closed contract).
    out = tmp_path / "output"
    out.mkdir()
    f = out / "cv_x.md"
    f.write_bytes(b"\xef\xbb\xbf- a clean bullet ending on a 5% result.\n")
    code, doc = run_json(fp_mod, [str(f)])
    assert code == 2
    assert any("BOM" in e["message"] for e in doc["errors"])


def test_fp_scanned_undecodable_exit2(fp_mod, tmp_path):
    # TQ-2: a scanned deliverable with invalid UTF-8 bytes fails the run closed —
    # the linter never silently skips a file it cannot parse.
    out = tmp_path / "output"
    out.mkdir()
    f = out / "cv_x.md"
    f.write_bytes(b"- valid start\n\xff\xfe bad bytes\n")
    code, doc = run_json(fp_mod, [str(f)])
    assert code == 2
    assert any("undecodable" in e["message"] for e in doc["errors"])


def test_fp_scanned_bomless_utf16_fails_closed(fp_mod, tmp_path):
    # Regression (morning-2026-06-16 #3): a BOM-less UTF-16-LE deliverable decodes as
    # VALID UTF-8 (every ASCII char becomes <char>\x00), so the old reader did NOT
    # raise — the FP rules then ran over NUL-interleaved text and silently missed the
    # banned words (a fail-OPEN). The shared reader's NUL-byte guard must fail it
    # closed (exit 2), like leak_audit already did. The content is fingerprint-dirty
    # ("leverage", "synergy") so a successful read WOULD have produced FP-001 findings.
    out = tmp_path / "output"
    out.mkdir()
    f = out / "cv_x.md"
    f.write_bytes("- leverage synergy to deliver value\n".encode("utf-16-le"))
    code, doc = run_json(fp_mod, [str(f)])
    assert code == 2
    assert any("NUL" in e["message"] for e in doc["errors"])


# --- Fail-closed: FP also rejects an unparseable inventory (shared contract) -
def test_fp_unparseable_inventory_exit2(fp_mod, writer):
    # FP does not apply consistency rules, but an unparseable inventory still
    # FAILS the run (schema §3 fail-closed); the linter never silently skips it.
    inv = writer("bad.claims.jsonl", "{ not valid json\n")
    clean = writer("output/cv_x.md", "- Built a tested system, cutting latency 30%.\n")
    code, doc = run_json(fp_mod, [clean, "--inventory", inv])
    assert code == 2
    assert any(e["message"] == "unparseable JSON" for e in doc["errors"])


# --- Determinism: two runs, identical bytes --------------------------------
def test_determinism_identical_bytes(fp_script, writer):
    from _runner import run_cli
    body = (
        "- We leverage a robust approach, improving outcomes\n"
        "Did X --- then Y --- then Z extra.\n"
    )
    p = writer("output/cv_x.md", body)
    c1, b1 = run_cli(fp_script, [p, "--format", "json"])
    c2, b2 = run_cli(fp_script, [p, "--format", "json"])
    assert c1 == c2 == 1
    assert b1 == b2
    assert not b1.startswith(b"\xef\xbb\xbf")  # no BOM on output
