"""Tests for lint_provenance.py (PV-xxx).

Covers every PV rule on a minimal inline fixture, the inventory consistency
rules (schema §1), the fail-closed unparseable-inventory -> exit 2 path (a named
§9 done-gate item), malformed/placed sentinels, the in-progress budget, expired
expected-dates, LOC/test-count claims, lint-allow + META-001, JSON shape and
determinism. Fixtures are minted here (test-helpers-own-throwaway-data).

Paths matter: output/cv_*.md, output/*_cv_improved.md, output/*.tex and the
broadened CV/cover-letter name-set (resume.md / curriculum_vitae.md /
cover_letter.md / jane_resume.md, etc.; RT-2, 13/06/2026) classify as DELIVER; KB
paths (cv_builder/experience|support|bundles, knowledge_base) as KB; session_/
critique_/changelog/notes artefacts as DRAFT even when the name contains
"resume"/"cv". A pinned --today 2026-06 keeps PV-008 deterministic regardless of clock.
"""

import json

import pytest

from _runner import run_json


TODAY = ["--today", "2026-06"]


def _rules(mod, argv):
    code, doc = run_json(mod, [*argv, *TODAY])
    return code, [f["rule"] for f in doc["findings"]], doc


# A minimal valid inventory row builder.
def _row(**over):
    base = {
        "id": "C-001",
        "claim": "Co-built a portal used by a committee",
        "verb_class": "hedged",
        "source": "experience_coding_society.md#L42",
        "status": "verified",
        "sentinels": [],
        "evidence": "live deployment + repo",
    }
    base.update(over)
    return json.dumps(base)


# --- Text rules ------------------------------------------------------------
def test_pv005_malformed_lowercase_verify(pv_mod, writer):
    p = writer("output/session_x.md", "- claim recorded [verify] before it ships\n")
    _, rules, doc = _rules(pv_mod, [p])
    assert "PV-005" in rules


def test_pv005_malformed_prose_inprogress_month_name(pv_mod, writer):
    p = writer("output/cv_x.md", "- Building X (in progress, expected June 2026)\n")
    _, rules, _ = _rules(pv_mod, [p])
    assert "PV-005" in rules


def test_pv005_malformed_prose_inprogress_single_digit_month(pv_mod, writer):
    p = writer("output/cv_x.md", "- Building X (in progress, expected 6/2026)\n")
    _, rules, _ = _rules(pv_mod, [p])
    assert "PV-005" in rules


def test_pv005_canonical_label_not_flagged(pv_mod, writer):
    p = writer("output/cv_x.md", "- Building X (in progress, expected 09/2026)\n")
    _, rules, _ = _rules(pv_mod, [p])
    assert "PV-005" not in rules


def test_benign_in_progress_prose_not_flagged(pv_mod, writer):
    # The experience-file form "(v1/MVP in progress -- single domain)" is prose,
    # not an attempt at the label -> no PV-005.
    p = writer("cv_builder/experience/x.md",
               "**Status:** prototype (v1/MVP in progress -- single domain)\n")
    _, rules, _ = _rules(pv_mod, [p])
    assert "PV-005" not in rules


def test_pv006_verify_in_deliverable(pv_mod, writer):
    p = writer("output/cv_x.md", "- Built a thing [VERIFY: detail]\n")
    code, rules, _ = _rules(pv_mod, [p])
    assert "PV-006" in rules
    assert code == 1


def test_pv006_ask_in_deliverable(pv_mod, writer):
    p = writer("output/x.tex", "\\item Built a thing [ASK: which year?]\n")
    _, rules, _ = _rules(pv_mod, [p])
    assert "PV-006" in rules


def test_verify_in_kb_allowed(pv_mod, writer):
    # Same sentinel in a KB path is allowed (schema §2 location table).
    p = writer("cv_builder/experience/x.md", "Context [VERIFY: committee size]\n")
    _, rules, _ = _rules(pv_mod, [p])
    assert "PV-006" not in rules


def test_pv007_inprogress_budget_exceeded(pv_mod, writer):
    body = (
        "- A (in progress, expected 09/2026)\n"
        "- B (in progress, expected 10/2026)\n"
        "- C (in progress, expected 11/2026)\n"
    )
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(pv_mod, [p])
    assert "PV-007" in rules


def test_pv007_two_inprogress_ok(pv_mod, writer):
    body = (
        "- A (in progress, expected 09/2026)\n"
        "- B (in progress, expected 10/2026)\n"
    )
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(pv_mod, [p])
    assert "PV-007" not in rules


def test_pv008_expected_date_in_past(pv_mod, writer):
    p = writer("output/cv_x.md", "- A (in progress, expected 03/2026)\n")
    _, rules, _ = _rules(pv_mod, [p])
    assert "PV-008" in rules


def test_pv008_expected_date_current_month_in_past(pv_mod, writer):
    # The reference month itself is not in the future.
    p = writer("output/cv_x.md", "- A (in progress, expected 06/2026)\n")
    _, rules, _ = _rules(pv_mod, [p])
    assert "PV-008" in rules


def test_pv008_future_date_clean(pv_mod, writer):
    p = writer("output/cv_x.md", "- A (in progress, expected 07/2026)\n")
    _, rules, _ = _rules(pv_mod, [p])
    assert "PV-008" not in rules


def test_pv009_loc_claim_in_deliverable(pv_mod, writer):
    p = writer("output/cv_x.md", "- Wrote 12,000 lines of code for the system.\n")
    code, rules, _ = _rules(pv_mod, [p])
    assert "PV-009" in rules
    assert code == 1


def test_pv009_testcount_claim_in_deliverable(pv_mod, writer):
    p = writer("output/x.tex", "\\item Authored 240 unit tests for the module.\n")
    _, rules, _ = _rules(pv_mod, [p])
    assert "PV-009" in rules


def test_pv009_not_in_draft(pv_mod, writer):
    # LOC/test counts are fine in a session/draft, only barred in deliverables.
    p = writer("output/session_x.md", "- note: the repo has 12,000 lines of code.\n")
    _, rules, _ = _rules(pv_mod, [p])
    assert "PV-009" not in rules


# --- PV-009 broadened LOC phrasings (RT-5; was a false negative) -----------
# Each missed string is now a regression fixture; the negatives below prove the
# code-nexus gate keeps non-LOC "lines" prose clean.
@pytest.mark.parametrize("body", [
    "- Wrote 12k lines of code for the system.\n",
    "- Refactored 8,000 lines of Rust into modules.\n",
    "- Ported 8000 lines of Go to the new runtime.\n",
    "- Rewrote 3000 lines of C in Python.\n",
    "- Trimmed the 40k LOC codebase.\n",
    "- Shipped a 200-line parser.\n",
    "- Maintained a 12k-line codebase.\n",
    "- Authored 340 SLOC of glue.\n",
])
def test_pv009_loc_phrasings_caught(pv_mod, writer, body):
    p = writer("output/cv_x.md", body)
    code, rules, _ = _rules(pv_mod, [p])
    assert "PV-009" in rules
    assert code == 1


@pytest.mark.parametrize("body", [
    "- This is ~34 bullet-lines of content for the CV.\n",   # CV bullet-line-count class
    "- The cut leaves ~34 lines vs a 1-page target.\n",      # page-length critique class
    "- The work has lines spanning two teams.\n",
    "- He recited 3 lines of poetry at the event.\n",
    "- Verified at 14 lines, tectonic one page.\n",          # page-verification class
    "- Synced 285 workouts, 29 measurements and 486 templates.\n",  # data-count (not LOC) class
])
def test_pv009_loc_negatives_stay_clean(pv_mod, writer, body):
    # No code nexus -> not a LOC claim, even in a DELIVER file.
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(pv_mod, [p])
    assert "PV-009" not in rules


# --- PV-009 code-nexus "N lines" (A-F4; was a false negative) ---------------
# A bare "N lines" magnitude that co-occurs with a repo-shaped code nexus
# (codebase|repo|repository) in a tight same-line window is a LOC brag, in either
# order. Bare/non-code "N lines" prose (the negatives above) still stays clean.
@pytest.mark.parametrize("body", [
    "- Built a codebase of 40,000 lines for the platform.\n",   # nexus -> N lines
    "- Shipped a repo with 12000 lines this term.\n",
    "- A 40,000-line repository, owned end to end.\n",          # already via _LOC_RE2; stays caught
    "- Rewrote 40,000 lines across the codebase.\n",            # reverse order: N lines -> nexus
    "- Owns 12k lines in our repo this term.\n",                # reverse, 'in' size-connector
    "- Maintains 200,000 lines within the repository.\n",       # reverse, 'within' size-connector
])
def test_pv009_loc_code_nexus_caught(pv_mod, writer, body):
    p = writer("output/cv_x.md", body)
    code, rules, _ = _rules(pv_mod, [p])
    assert "PV-009" in rules
    assert code == 1


# --- PV-009 reverse arm: delta/edit "N lines ... <nexus>" stays clean (A-F4 ---
# follow-up). The reverse arm must MATCH the forward arm's anti-delta intent: it
# fires only when "N lines" SIZES the nexus. A delta preposition (from) or a delta
# verb before the number (removed/deleted/changed/reviewed/added) keeps it clean,
# so honest "shrank the repo" edit phrasings do not false-fire.
@pytest.mark.parametrize("body", [
    "- removed 200 lines from the repo last sprint.\n",         # 'from' delta preposition
    "- deleted 500 lines from the codebase in review.\n",       # 'from' delta preposition
    "- changed 3 lines in the repo for the hotfix.\n",          # delta verb before number, 'in'
    "- we reviewed 50 lines in the repo together.\n",           # delta verb before number, 'in'
])
def test_pv009_loc_reverse_delta_stays_clean(pv_mod, writer, body):
    # Even in a DELIVER file, a delta/edit on the codebase is not a size brag.
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(pv_mod, [p])
    assert "PV-009" not in rules


@pytest.mark.parametrize("body", [
    "- wrote ~34 lines of notes for the README.\n",            # magnitude, no code nexus
    "- He recited 3 lines of poetry before the talk.\n",
    "- The work has lines spanning two teams here.\n",         # 'spanning' but no nexus/number
    "- Gave a few lines of feedback on the draft.\n",
    "- Reduced support lines after the migration.\n",          # bare magnitude word, no number
    "- Noted the codebase, then unrelated text, then 9000 lines of dialogue much later on this row.\n",
])
def test_pv009_loc_code_nexus_negatives_stay_clean(pv_mod, writer, body):
    # No code nexus near the magnitude (or no number) -> not a LOC claim. The last
    # case proves the window is tight: a far-apart nexus co-mention does not fire.
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(pv_mod, [p])
    assert "PV-009" not in rules


def test_pv009_loc_code_nexus_fail_before(pv_mod):
    # Fail-before guard: "codebase of 40,000 lines" must NOT be caught by the two
    # pre-A-F4 patterns (only the new _LOC_RE3 catches it). If this ever passes on
    # _LOC_RE/_LOC_RE2 alone the rule has drifted; the firing test above proves the
    # post-fix catch via the wired-in _LOC_RE3.
    line = "Built a codebase of 40,000 lines"
    assert not (pv_mod._LOC_RE.search(line) or pv_mod._LOC_RE2.search(line))
    assert pv_mod._LOC_RE3.search(line)


def test_pv009_loc_code_nexus_not_in_draft(pv_mod, writer):
    # PV-009 is DELIVER-gated: the same code-nexus LOC brag in a session/draft is fine.
    p = writer("output/session_x.md", "- note: a codebase of 40,000 lines now.\n")
    _, rules, _ = _rules(pv_mod, [p])
    assert "PV-009" not in rules


def test_pv009_loc_re3_forward_arm_unchanged(pv_mod):
    # Lock the forward arm at the regex level so a reverse-arm tweak cannot regress it:
    # size phrasings fire; the honest "by" delta stays clean (the forward arm omits "by").
    for s in ("codebase of 40,000 lines", "repo with 12000 lines",
              "repository containing 12k lines"):
        assert pv_mod._LOC_RE3.search(s), s
    assert not pv_mod._LOC_RE3.search("reduced the codebase by 4,000 lines")


# --- PV-009 broadened test-count phrasings (RT-5) --------------------------
@pytest.mark.parametrize("body", [
    "- Authored 200 tests for the module.\n",
    "- Added 350 integration tests to the suite.\n",
    "- Wrote 90 specs for the parser.\n",
    "- Built a 340-test suite for the API.\n",
    "- Added a suite of 200 tests overnight.\n",
    "- Added 200 tests covering the edge cases.\n",
])
def test_pv009_testcount_phrasings_caught(pv_mod, writer, body):
    p = writer("output/cv_x.md", body)
    code, rules, _ = _rules(pv_mod, [p])
    assert "PV-009" in rules
    assert code == 1


@pytest.mark.parametrize("body", [
    "- Ran 4 user tests before the demo.\n",         # number not adjacent to "tests"
    "- Hosted 5 test events this term.\n",            # singular "test", different noun
    "- SQL-level tests proving the denial path.\n",   # qualitative-tests (no count) class
    "- SQL RLS tests kept green in CI.\n",            # qualitative-tests (no count) class
    "- Ran 12 acceptance tests with the client.\n",   # type-qualifier noun, not a size brag
    "- Wrote 8 smoke tests for the deploy.\n",        # type-qualifier noun
    "- Did 3 manual tests before release.\n",         # type-qualifier noun
])
def test_pv009_testcount_negatives_stay_clean(pv_mod, writer, body):
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(pv_mod, [p])
    assert "PV-009" not in rules


# Regression (morning-2026-06-16 #5): the bare-plural arm "\d+ tests" only fired when
# the number was ADJACENT to "tests", so "N <adjective> tests" — an evaluative count
# brag with a descriptor in between — slipped the rule ("484 comprehensive tests",
# "120 automated tests"). (The audit's cited "484 passing tests" already fired via the
# passing-tests arm; the gap was the OTHER descriptors.) A bounded evaluative-adjective
# window (1-2 stacked) now catches them, while type-qualifier nouns stay clean above.
@pytest.mark.parametrize("body", [
    "- Authored 484 comprehensive tests for the engine.\n",
    "- Added 120 automated tests this sprint.\n",
    "- Wrote 42 new tests for the parser.\n",
    "- Kept 53 green tests in CI.\n",
    "- Built 200 thorough automated tests overnight.\n",   # 2 stacked adjectives
    "- Added 30 end-to-end tests for the flow.\n",
])
def test_pv009_descriptor_testcount_caught(pv_mod, writer, body):
    p = writer("output/cv_x.md", body)
    code, rules, _ = _rules(pv_mod, [p])
    assert "PV-009" in rules
    assert code == 1


# --- PV-005 broken-bracket sentinels (SC-1; was a false negative) ----------
@pytest.mark.parametrize("body", [
    "- claim recorded [ASK:] before it ships\n",       # empty body
    "- claim recorded [ASK: ] before it ships\n",      # whitespace body
    "- claim recorded [VERIFY:] empty colon\n",        # verify empty body
    "- fact [ VERIFY ] here\n",                         # spaced
    "- fact [ ASK: which company] here\n",              # spaced ask
    "- place [ASK where] is it\n",                      # colon-less
    "- place [ASK :where] is it\n",                     # space-before-colon
    "- tail fragment [VERIFY\n",                         # unclosed
    "- tail fragment [ask\n",                            # unclosed lowercase
])
def test_pv005_broken_bracket_sentinels_caught(pv_mod, writer, body):
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(pv_mod, [p])
    assert "PV-005" in rules


@pytest.mark.parametrize("body", [
    "- canonical [VERIFY] sentinel in KB context\n",   # valid -> no malformed finding
    "- canonical [VERIFY: detail] sentinel\n",
    "- canonical [ASK: which year?] here\n",
    "- ordinary [note] bracket and array [1, 2, 3]\n",
    "- markdown [link](http://example.test) and [3] note\n",
])
def test_pv005_valid_or_plain_brackets_stay_clean(pv_mod, writer, body):
    # In a KB path the canonical sentinels are allowed AND not malformed; plain
    # markdown/array brackets never trip the broken-bracket patterns.
    p = writer("cv_builder/experience/x.md", body)
    _, rules, _ = _rules(pv_mod, [p])
    assert "PV-005" not in rules


# --- PV-005 broadened prose in-progress (SC-2; non-date tails) -------------
@pytest.mark.parametrize("body", [
    "- Building X (in progress, expected Q3 2026)\n",
    "- Building X (in progress, expected late 2026)\n",
    "- Building X (in progress, expected autumn 2026)\n",
    "- Building X (in progress, expected 2026)\n",
    "- Building X (in progress, expected TBC)\n",
])
def test_pv005_prose_inprogress_nondate_tails_caught(pv_mod, writer, body):
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(pv_mod, [p])
    assert "PV-005" in rules


def test_pv005_literal_mm_yyyy_placeholder_excluded(pv_mod, writer):
    # A deliverable that quotes the literal placeholder as documentation; the
    # naive broadening would fire on it. It must stay clean.
    p = writer("output/cv_x.md",
               '- labelled "(in progress, expected mm/yyyy)" via the pipeline file.\n')
    _, rules, _ = _rules(pv_mod, [p])
    assert "PV-005" not in rules


# --- PV-010 prose ownership (RT-1; the unenforced solo-only verb rule) ------
@pytest.mark.parametrize("body", [
    "- Built the entire backend (group project)\n",
    "- Developed the model our team trained\n",
    "* Designed the schema, and we shipped it together\n",
    "\\item Implemented the parser that we wrote\n",
    "- Created the API; we maintained it as a group project\n",
    "- Architected the service together with the team\n",
])
def test_pv010_fullownership_with_collab_caught(pv_mod, writer, body):
    p = writer("output/cv_x.md", body)
    code, rules, _ = _rules(pv_mod, [p])
    assert "PV-010" in rules
    assert code == 1


# Regression (morning-2026-06-16 #4): PV-010's lead-verb anchor only accepted -/* and
# a bare \item, so a NUMBERED bullet ("1." / "2)") or an \item[<opt>] with an optional
# argument silently escaped the solo-only-verb rule (the sibling _BULLET_RE in
# lint_fingerprint already accepted these). The bullet alternation now mirrors it, so
# the same full-ownership-verb-with-collaboration line fires regardless of bullet form.
@pytest.mark.parametrize("body", [
    "1. Built the entire backend (group project)\n",
    "2) Developed the model our team trained\n",
    "10. Designed the schema, and we shipped it together\n",
    "\\item[\\textbullet] Implemented the parser that we wrote\n",
    "\\item[--] Created the API as part of a team\n",
    "\\item[1.] Architected the service together with the team\n",
])
def test_pv010_numbered_and_item_arg_bullets_caught(pv_mod, writer, body):
    p = writer("output/cv_x.md", body)
    code, rules, _ = _rules(pv_mod, [p])
    assert "PV-010" in rules
    assert code == 1


# Regression: the collab marker must fire even when modifier words sit between
# "with the/my/our" and the team noun (audit false-negative — the old pattern
# required an immediately-adjacent noun, so "with the engineering team" evaded it).
@pytest.mark.parametrize("body", [
    "- Built the dashboard with the engineering team\n",
    "- Developed the pipeline with my data science team\n",
    "- Designed the layout with our small design squad\n",
    "- Implemented the rota with the events committee\n",
    "- Created the report with our finance department\n",
])
def test_pv010_collab_with_modifier_words_caught(pv_mod, writer, body):
    p = writer("output/cv_x.md", body)
    code, rules, _ = _rules(pv_mod, [p])
    assert "PV-010" in rules
    assert code == 1


# Regression A-F2 (overnight audit): common shared-authorship phrasings the collab
# marker missed — each must now fire PV-010 alongside a full-ownership lead verb.
@pytest.mark.parametrize("body", [
    "- Built the backend as part of a team\n",
    "- Developed the model in a team of five\n",
    "- Designed the schema alongside the platform team\n",
    "- Implemented the parser, pair-programmed with a colleague\n",
    "- Created the API jointly with the maintainers\n",
    "- Built the survey tool with the research group\n",   # human "<x> group" kept
    "- Designed the revision plan in a study group\n",
    "- Developed the platform in a team of a dozen\n",      # count word
    "- Built the API in a team of 5 engineers\n",          # human noun after count fires
])
def test_pv010_additional_collab_phrasings_caught(pv_mod, writer, body):
    p = writer("output/cv_x.md", body)
    code, rules, _ = _rules(pv_mod, [p])
    assert "PV-010" in rules
    assert code == 1


# A-F2 false-positive guards: lookalikes that are NOT shared-authorship stay clean.
@pytest.mark.parametrize("body", [
    "- Built it on time as part of a release\n",          # "as part of a release" != team
    "- Developed it in a team-friendly culture\n",        # "team-friendly", no "of"
    "- Designed it to run alongside a tight deadline\n",  # "alongside ... deadline" != team
])
def test_pv010_new_phrasing_lookalikes_stay_clean(pv_mod, writer, body):
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(pv_mod, [p])
    assert "PV-010" not in rules


# A-F2 precision (verifier-found false positives): overloaded CS/data CV prose must
# NOT fire. "group" is consumer/control/resource/security/thread group (not a team);
# "jointly with <tool>" is not co-authorship; "in a group of N <things>" is data, not
# people; "team of one" is solo. These reproduce real bullets a CS CV would contain.
@pytest.mark.parametrize("body", [
    "- Built sharding that partitions writes in a group of 16 shards\n",
    "- Designed a pipeline that batches records in a group of 500\n",
    "- Developed a scheduler running each job in a team of one worker\n",
    "- Implemented retries jointly with the package manager during deploys\n",
    "- Created firewall rules alongside the security group in AWS\n",
    "- Built a rebalancer alongside the consumer group coordinator in Kafka\n",
    "- Implemented IaC that provisions alongside the resource group in Azure\n",
    "- Designed alerts that run alongside the control group in each A/B test\n",
    "- Built ingestion with the kafka consumer group offsets\n",
    # 2nd-pass verifier: article-"a" + non-human "team" (security/automation prose).
    "- Built a fuzzer with a red team of automated probes\n",
    "- Designed monitors with a blue team of bots\n",
    "- Created a sandbox with a team of bots\n",
    "- Designed a migration with a department of 200 rows\n",
    # Codex: numeric one-person team, and a machine count after "team of N".
    "- Developed a scheduler in a team of 1\n",
    "- Built a worker pool in a team of 8 threads\n",
    # 3rd-pass verifier: "team of N <machine>" leaked for plurals off the old list.
    "- Built a gateway routing requests in a team of 5 microservices\n",
    "- Designed a runtime in a team of 8 agents\n",
])
def test_pv010_technical_group_and_tool_lookalikes_stay_clean(pv_mod, writer, body):
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(pv_mod, [p])
    assert "PV-010" not in rules


# PV-010 precision v3 (Codex-found false positives in the A-F2 v2 hardening). Two
# honest SOLO shapes wrongly fired and must now stay clean:
#  (A) team-compound: the team noun was the PREFIX of a hyphenated compound
#      ("team-friendly", "team-building", "squad-based"); the \b is true before "-",
#      so "as part of a team-friendly process" / "with the team-building toolkit" fired.
#  (B) descriptor-before-machine-count: a descriptor word ("async", "lightweight",
#      "long-running") between the count and the machine noun slipped the adjacent-only
#      lookahead, so "in a team of 8 async workers" (8 MACHINES) fired.
# These ALL fire on the pre-v3 regex (proven fail-before) and must NOT fire now.
@pytest.mark.parametrize("body", [
    # (A) team-noun as a hyphenated-compound prefix — honest solo lines.
    "- Built the onboarding flow as part of a team-friendly process\n",
    "- Implemented the API as part of a team-friendly onboarding flow\n",
    "- Designed the kit with the team-building toolkit\n",
    "- Developed a planner with my squad-based workflow\n",
    # (B) machine count reached via a descriptor word (1-3 tokens, incl. hyphenated).
    "- Built a scheduler in a team of 8 async workers\n",
    "- Built a runtime in a team of 4 lightweight workers\n",
    "- Built a runtime in a team of 4 lightweight background workers\n",
    "- Designed a pool in a team of 16 long-running threads\n",
])
def test_pv010_v3_false_positives_stay_clean(pv_mod, writer, body):
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(pv_mod, [p])
    assert "PV-010" not in rules


# Guard the v3 narrowing: the named genuine collaboration catches MUST still fire so
# the precision fix did not weaken the rule (people-count and bare team-noun arms).
@pytest.mark.parametrize("body", [
    "- Built X as part of a team\n",                     # bare "team" still a catch
    "- Designed Y in a team of 8 engineers\n",           # human noun after count
    "- Implemented Z with the platform team\n",          # "with the <noun> team"
    "- Built it in a team of 8 people\n",                # "people" is human
    "- Developed it in a team of 8 of us\n",             # "of us" is human
    # v3 window tighten {0,3}->{0,2}: a machine noun 3-4 tokens AFTER the human count must
    # no longer suppress the catch — these were silently dropped under {0,3} (verifier-found).
    "- Designed Y in a team of 8 engineers using a worker pool\n",
    "- Built X in a team of 5 staff managing the servers\n",
])
def test_pv010_v3_genuine_catches_still_fire(pv_mod, writer, body):
    p = writer("output/cv_x.md", body)
    code, rules, _ = _rules(pv_mod, [p])
    assert "PV-010" in rules
    assert code == 1


# PV-010 v3 window regression (verifier-found, post-1f0e8ea). At {0,3} the negative
# lookahead reached a machine noun up to 4 tokens past the human count, so a genuine
# "team of N <humans> ... <machine>" line was silently DROPPED. Tightening the descriptor
# window to {0,2} recovers it: the human noun ("engineers"/"staff") follows the count
# directly, and the trailing machine noun ("worker pool"/"servers") sits beyond the
# 2-token window so it can no longer suppress the catch. These FIRE at {0,2}, were MISSED
# at {0,3}; the descriptor-FP cases above prove {0,2} stays clean (their descriptors are
# only 1-2 tokens). Locks the strictly-better direction of the tighten.
@pytest.mark.parametrize("body", [
    "- Designed Y in a team of 8 engineers using a worker pool\n",
    "- Built X in a team of 5 staff managing the servers\n",
])
def test_pv010_v3_window_recovers_human_team_before_machine(pv_mod, writer, body):
    p = writer("output/cv_x.md", body)
    code, rules, _ = _rules(pv_mod, [p])
    assert "PV-010" in rules
    assert code == 1


def test_pv010_fires_in_draft_too(pv_mod, writer):
    # The rule covers DRAFT prose as well as DELIVER (spec: DELIVER/DRAFT bullets).
    p = writer("output/session_x.md", "- Built the whole thing (group project)\n")
    _, rules, _ = _rules(pv_mod, [p])
    assert "PV-010" in rules


@pytest.mark.parametrize("body", [
    "- Built the API; our customers rely on it daily.\n",   # bare "our" != collab
    "- Co-built a portal with the committee together.\n",   # hedged lead verb
    "- Contributed to a workflow we built together.\n",     # hedged lead verb
    "- Designed, built and deployed the live portal solo.\n",  # full-ownership, no collab
    "Designed the system together with the team.\n",        # not a bullet (no marker)
    "- Built a tool that lets us ship faster.\n",           # F2: bare "us" != collab
    "- Designed a system that brings data together.\n",     # F2: bare "together" != collab
])
def test_pv010_negatives_stay_clean(pv_mod, writer, body):
    p = writer("output/cv_x.md", body)
    _, rules, _ = _rules(pv_mod, [p])
    assert "PV-010" not in rules


def test_pv010_not_in_kb(pv_mod, writer):
    # KB experience notes may describe team work with full-ownership verbs; the
    # hedge is applied at generation time, so PV-010 does not fire in KB.
    p = writer("cv_builder/experience/x.md", "- Built the backend (group project)\n")
    _, rules, _ = _rules(pv_mod, [p])
    assert "PV-010" not in rules


# --- PV-007 now gated on DELIVER, so cover-letter .tex is covered (RT-4) ----
def test_pv007_cover_letter_tex_inprogress_overflow(pv_mod, writer):
    # e2e_<name>_cover_letter.tex has no "_cv" in its name, so the old
    # is_cv_deliverable() gate skipped PV-007. It is DELIVER, so >2 now fires.
    body = (
        "\\item A (in progress, expected 09/2026)\n"
        "\\item B (in progress, expected 10/2026)\n"
        "\\item C (in progress, expected 11/2026)\n"
    )
    p = writer("output/e2e_x_cover_letter.tex", body)
    _, rules, _ = _rules(pv_mod, [p])
    assert "PV-007" in rules


# --- RT-2: deliverable detection is case-insensitive ------------------------
def test_uppercase_cv_classifies_deliverable(pv_mod, writer):
    # CV_sample.md (uppercase) previously classified DRAFT, skipping PV-009.
    # Lower-casing the basename keeps it DELIVER so PV-009 fires.
    p = writer("output/CV_sample.md", "- Wrote 12,000 lines of code for the system.\n")
    code, rules, _ = _rules(pv_mod, [p])
    assert "PV-009" in rules
    assert code == 1


# --- RT-2: broadened deliverable name-set (kit-owner approved 13/06/2026) ----
# A CV/cover letter named resume.md / curriculum_vitae.md / cover_letter.md /
# jane_resume.md previously classified DRAFT and silently escaped the
# deliverable-only rules (PV-006 sentinel placement, PV-009 LOC/test counts).
# Each must now be DELIVER so both rules fire. Body carries a [VERIFY] token (PV-006)
# AND a LOC claim (PV-009).
_BROADENED_BODY = "- Built a thing [VERIFY: detail] in 10,000 lines of code.\n"


@pytest.mark.parametrize("name", [
    "resume.md",
    "curriculum_vitae.md",
    "curriculumvitae.md",
    "cover_letter.md",
    "coverletter.md",
    "cv.md",
    "jane_resume.md",
    "jane_cover_letter.md",
    "jane_coverletter.md",
])
def test_broadened_deliverable_names_fire_pv006_and_pv009(pv_mod, writer, name):
    p = writer("output/%s" % name, _BROADENED_BODY)
    code, rules, _ = _rules(pv_mod, [p])
    assert "PV-006" in rules
    assert "PV-009" in rules
    assert code == 1


# Draft/analysis artefacts whose name contains "resume"/"cv" must STAY DRAFT, so
# PV-006/PV-009 do NOT fire from those rules (a substring match must not leak a
# session/critique/changelog/notes file into DELIVER — the false-positive trap).
@pytest.mark.parametrize("name", [
    "session_resume_notes.md",
    "cv_critique.md",
    "resume_changelog.md",
    "resume_change_log.md",
    "my_resume_draft_notes.md",
])
def test_draft_named_with_cv_substring_stays_draft(pv_mod, writer, name):
    p = writer("output/%s" % name, _BROADENED_BODY)
    code, rules, _ = _rules(pv_mod, [p])
    assert "PV-006" not in rules
    assert "PV-009" not in rules


# --- A-F1 (overnight audit): hyphen-spelled deliverable names ----------------
# cover-letter.md / curriculum-vitae.md / jane-resume.md previously classified
# DRAFT (the stem matched only underscore forms) and silently escaped the
# deliverable-only rules. _output_stem now folds '-'->'_' so they are DELIVER.
@pytest.mark.parametrize("name", [
    "cover-letter.md",
    "curriculum-vitae.md",
    "jane-resume.md",
    "jane-cover-letter.md",
    "cv-jane.md",          # cv-* prefix on the folded stem (Codex-found gap)
    "cv-jane-smith.md",
    "cv-improved.md",
])
def test_hyphenated_deliverable_names_fire_pv006_and_pv009(pv_mod, writer, name):
    p = writer("output/%s" % name, _BROADENED_BODY)
    code, rules, _ = _rules(pv_mod, [p])
    assert "PV-006" in rules
    assert "PV-009" in rules
    assert code == 1


# Hyphen-spelled draft/analysis artefacts must STILL stay DRAFT — the fold makes the
# draft-name check hyphen-aware too, so it wins first (no false DELIVER escalation).
@pytest.mark.parametrize("name", [
    "cv-critique.md",
    "session-notes.md",
    "resume-changelog.md",
    "resume-change-log.md",
])
def test_hyphenated_draft_names_stay_draft(pv_mod, writer, name):
    p = writer("output/%s" % name, _BROADENED_BODY)
    _, rules, _ = _rules(pv_mod, [p])
    assert "PV-006" not in rules
    assert "PV-009" not in rules


def test_existing_cv_md_behaviour_unchanged(pv_mod, writer):
    # cv_*.md remains DELIVER (PV-009 fires) — broadening did not regress it.
    p = writer("output/cv_x.md", "- Wrote 12,000 lines of code for the system.\n")
    code, rules, _ = _rules(pv_mod, [p])
    assert "PV-009" in rules
    assert code == 1


def test_existing_cv_improved_md_behaviour_unchanged(pv_mod, writer):
    # *_cv_improved.md remains DELIVER.
    p = writer("output/name_cv_improved.md",
               "- Wrote 12,000 lines of code for the system.\n")
    code, rules, _ = _rules(pv_mod, [p])
    assert "PV-009" in rules
    assert code == 1


def test_existing_tex_behaviour_unchanged(pv_mod, writer):
    # Any .tex output remains DELIVER.
    p = writer("output/x.tex", "\\item Built a thing [VERIFY: detail]\n")
    code, rules, _ = _rules(pv_mod, [p])
    assert "PV-006" in rules
    assert code == 1


def test_other_output_prose_md_still_draft(pv_mod, writer):
    # A non-CV-named output prose file (pitch/outreach) stays DRAFT.
    p = writer("output/x_pitch_and_outreach.md", _BROADENED_BODY)
    _, rules, _ = _rules(pv_mod, [p])
    assert "PV-006" not in rules
    assert "PV-009" not in rules


# --- Inventory consistency (schema §1) -------------------------------------
def test_pv001_full_ownership_requires_verified_and_solo(pv_mod, writer):
    # full-ownership but status needs-verify and no solo evidence.
    inv = writer("x.claims.jsonl",
                 _row(id="C-002", verb_class="full-ownership",
                      status="needs-verify", evidence="repo") + "\n")
    nothing = writer("docs/empty.md", "noop\n")  # a scanned path that fires nothing
    code, rules, _ = _rules(pv_mod, [nothing, "--inventory", inv])
    assert rules.count("PV-001") == 2  # not-verified + not-solo
    assert code == 1


def test_pv001_full_ownership_solo_verified_ok(pv_mod, writer):
    inv = writer("x.claims.jsonl",
                 _row(id="C-003", verb_class="full-ownership", status="verified",
                      evidence="solo build, live repo") + "\n")
    nothing = writer("docs/empty.md", "noop\n")
    code, rules, _ = _rules(pv_mod, [nothing, "--inventory", inv])
    assert "PV-001" not in rules


def test_pv002_in_progress_requires_label_and_pipeline_source(pv_mod, writer):
    inv = writer("x.claims.jsonl",
                 _row(id="C-004", verb_class="in-progress", status="needs-verify",
                      claim="Building an assistant", evidence="",
                      source="experience_personal_projects.md") + "\n")
    nothing = writer("docs/empty.md", "noop\n")
    _, rules, _ = _rules(pv_mod, [nothing, "--inventory", inv])
    assert rules.count("PV-002") == 2  # missing label + wrong source


def test_pv002_in_progress_valid_profile_prefixed_source(pv_mod, writer):
    # P6: the canonical owner-data pipeline source now lives under users/<profile>/.
    # PV-002 must ACCEPT the profile-prefixed path.
    inv = writer("x.claims.jsonl",
                 _row(id="C-005", verb_class="in-progress", status="needs-verify",
                      claim="Building an assistant (in progress, expected 09/2026)",
                      evidence="",
                      source="users/demo/cv_builder/experience/experience_pipeline.md") + "\n")
    nothing = writer("docs/empty.md", "noop\n")
    _, rules, _ = _rules(pv_mod, [nothing, "--inventory", inv])
    assert "PV-002" not in rules


def test_pv002_in_progress_valid_bare_root_source(pv_mod, writer):
    # The bare/old-root source (pre-migration inventory, or a public clone with no
    # users/ tree) is still accepted per the broadened rule.
    inv = writer("x.claims.jsonl",
                 _row(id="C-005", verb_class="in-progress", status="needs-verify",
                      claim="Building an assistant (in progress, expected 09/2026)",
                      evidence="",
                      source="cv_builder/experience/experience_pipeline.md") + "\n")
    nothing = writer("docs/empty.md", "noop\n")
    _, rules, _ = _rules(pv_mod, [nothing, "--inventory", inv])
    assert "PV-002" not in rules


def test_pv003_status_ask_requires_ask_sentinel(pv_mod, writer):
    inv = writer("x.claims.jsonl",
                 _row(id="C-006", status="ask", evidence="",
                      claim="Built a thing", sentinels=[]) + "\n")
    nothing = writer("docs/empty.md", "noop\n")
    _, rules, _ = _rules(pv_mod, [nothing, "--inventory", inv])
    assert "PV-003" in rules


def test_pv003_status_ask_with_sentinel_ok(pv_mod, writer):
    inv = writer("x.claims.jsonl",
                 _row(id="C-007", status="ask", evidence="",
                      claim="Built a thing [ASK: which year?]",
                      sentinels=["[ASK: which year?]"]) + "\n")
    nothing = writer("docs/empty.md", "noop\n")
    _, rules, _ = _rules(pv_mod, [nothing, "--inventory", inv])
    assert "PV-003" not in rules


def test_pv004_verified_requires_evidence(pv_mod, writer):
    inv = writer("x.claims.jsonl",
                 _row(id="C-008", status="verified", evidence="") + "\n")
    nothing = writer("docs/empty.md", "noop\n")
    _, rules, _ = _rules(pv_mod, [nothing, "--inventory", inv])
    assert "PV-004" in rules


def test_pv004_listed_sentinel_must_be_in_claim(pv_mod, writer):
    inv = writer("x.claims.jsonl",
                 _row(id="C-009", status="needs-verify", evidence="",
                      claim="Built a thing", sentinels=["[VERIFY]"]) + "\n")
    nothing = writer("docs/empty.md", "noop\n")
    _, rules, _ = _rules(pv_mod, [nothing, "--inventory", inv])
    assert "PV-004" in rules


def test_gold_example_row_clean(pv_mod, writer):
    # The schema §1 gold example must pass all inventory rules.
    gold = ('{"id":"C-007","claim":"Co-built a committee portal used by a '
            '15-member committee","verb_class":"hedged","source":'
            '"experience_coding_society.md#L42","status":"verified",'
            '"sentinels":[],"evidence":"live deployment + repo"}\n')
    inv = writer("x.claims.jsonl", gold)
    nothing = writer("docs/empty.md", "noop\n")
    code, rules, _ = _rules(pv_mod, [nothing, "--inventory", inv])
    assert rules == []
    assert code == 0


def test_scan_policy_exempts_coordination_and_config(pv_mod, writer):
    # coordination/ (session logs, ACTIVE.md, dated handoffs) and config.md quote
    # sentinels and ownership verbs as DOCUMENTATION — they are process/config
    # files, never CV content. Same content under a deliverable path must fire.
    body = "- Built the entire backend (group project) with a [VERIFY left open.\n"
    p_coord = writer("coordination/sessions/agent.md", body)
    p_cfg = writer("config.md", body)
    p_del = writer("output/cv_x.md", body)
    _, rules_coord, _ = _rules(pv_mod, [p_coord])
    _, rules_cfg, _ = _rules(pv_mod, [p_cfg])
    _, rules_del, _ = _rules(pv_mod, [p_del])
    assert rules_coord == []
    assert rules_cfg == []
    assert "PV-005" in rules_del  # the malformed sentinel fires under a deliverable


# --- Fail-closed: unparseable inventory -> exit 2 (named §9 done-gate) ------
def test_unparseable_inventory_malformed_json_exit2(pv_mod, writer):
    inv = writer("bad.claims.jsonl", _row() + "\n{ not json\n")
    nothing = writer("docs/empty.md", "noop\n")
    code, doc = run_json(pv_mod, [nothing, "--inventory", inv, *TODAY])
    assert code == 2
    assert doc["summary"]["exit_code"] == 2
    assert any(e["message"] == "unparseable JSON" for e in doc["errors"])
    assert doc["errors"][0]["line"] >= 1


def test_unparseable_inventory_blank_line_exit2(pv_mod, writer):
    inv = writer("bad.claims.jsonl", _row() + "\n\n" + _row(id="C-010") + "\n")
    nothing = writer("docs/empty.md", "noop\n")
    code, doc = run_json(pv_mod, [nothing, "--inventory", inv, *TODAY])
    assert code == 2
    assert any("blank line" in e["message"] for e in doc["errors"])


def test_inventory_bom_exit2(pv_mod, writer, tmp_path):
    # UTF-8 BOM must fail closed.
    p = tmp_path / "bom.claims.jsonl"
    p.write_bytes(b"\xef\xbb\xbf" + (_row() + "\n").encode("utf-8"))
    nothing = writer("docs/empty.md", "noop\n")
    code, doc = run_json(pv_mod, [nothing, "--inventory", str(p), *TODAY])
    assert code == 2
    assert any("BOM" in e["message"] for e in doc["errors"])


def test_inventory_missing_field_exit2(pv_mod, writer):
    bad = ('{"id":"C-011","claim":"x","verb_class":"hedged","source":"y.md",'
           '"status":"verified","evidence":"z"}\n')  # no "sentinels"
    inv = writer("bad.claims.jsonl", bad)
    nothing = writer("docs/empty.md", "noop\n")
    code, doc = run_json(pv_mod, [nothing, "--inventory", inv, *TODAY])
    assert code == 2
    assert any("missing field" in e["message"] for e in doc["errors"])


# --- TQ-1: every STRUCTURAL fail-closed branch -> exit 2 (was untested) -----
# The code is correct today; these regression-pin each branch so a future edit
# cannot silently turn a structural defect into a silent pass. Each asserts the
# specific error-message substring so the branch identity is pinned, not just the
# exit code.
def test_inventory_extra_field_exit2(pv_mod, writer):
    inv = writer("bad.claims.jsonl", _row(extra_key="x") + "\n")
    nothing = writer("docs/empty.md", "noop\n")
    code, doc = run_json(pv_mod, [nothing, "--inventory", inv, *TODAY])
    assert code == 2
    assert any("unexpected field" in e["message"] for e in doc["errors"])


def test_inventory_bad_verb_class_exit2(pv_mod, writer):
    inv = writer("bad.claims.jsonl", _row(verb_class="wizardry") + "\n")
    nothing = writer("docs/empty.md", "noop\n")
    code, doc = run_json(pv_mod, [nothing, "--inventory", inv, *TODAY])
    assert code == 2
    assert any("verb_class 'wizardry' not in" in e["message"] for e in doc["errors"])


def test_inventory_bad_status_exit2(pv_mod, writer):
    inv = writer("bad.claims.jsonl", _row(status="maybe") + "\n")
    nothing = writer("docs/empty.md", "noop\n")
    code, doc = run_json(pv_mod, [nothing, "--inventory", inv, *TODAY])
    assert code == 2
    assert any("status 'maybe' not in" in e["message"] for e in doc["errors"])


def test_inventory_bad_id_format_exit2(pv_mod, writer):
    inv = writer("bad.claims.jsonl", _row(id="C-7") + "\n")  # not C-NNN
    nothing = writer("docs/empty.md", "noop\n")
    code, doc = run_json(pv_mod, [nothing, "--inventory", inv, *TODAY])
    assert code == 2
    assert any("is not C-NNN" in e["message"] for e in doc["errors"])


def test_inventory_duplicate_id_exit2(pv_mod, writer):
    inv = writer("bad.claims.jsonl", _row(id="C-020") + "\n" + _row(id="C-020") + "\n")
    nothing = writer("docs/empty.md", "noop\n")
    code, doc = run_json(pv_mod, [nothing, "--inventory", inv, *TODAY])
    assert code == 2
    assert any("duplicate id 'C-020'" in e["message"] for e in doc["errors"])


def test_inventory_not_a_dict_exit2(pv_mod, writer):
    inv = writer("bad.claims.jsonl", '["not", "an", "object"]\n')
    nothing = writer("docs/empty.md", "noop\n")
    code, doc = run_json(pv_mod, [nothing, "--inventory", inv, *TODAY])
    assert code == 2
    assert any("not a JSON object" in e["message"] for e in doc["errors"])


def test_inventory_non_string_field_exit2(pv_mod, writer):
    # A required string field carrying a non-string value -> structural error.
    bad = ('{"id":123,"claim":"x","verb_class":"hedged","source":"y.md",'
           '"status":"verified","sentinels":[],"evidence":"z"}\n')
    inv = writer("bad.claims.jsonl", bad)
    nothing = writer("docs/empty.md", "noop\n")
    code, doc = run_json(pv_mod, [nothing, "--inventory", inv, *TODAY])
    assert code == 2
    assert any("'id' must be a string" in e["message"] for e in doc["errors"])


def test_inventory_sentinels_not_array_exit2(pv_mod, writer):
    bad = ('{"id":"C-021","claim":"x","verb_class":"hedged","source":"y.md",'
           '"status":"verified","sentinels":"[VERIFY]","evidence":"z"}\n')
    inv = writer("bad.claims.jsonl", bad)
    nothing = writer("docs/empty.md", "noop\n")
    code, doc = run_json(pv_mod, [nothing, "--inventory", inv, *TODAY])
    assert code == 2
    assert any("'sentinels' must be an array" in e["message"] for e in doc["errors"])


def test_inventory_sentinel_entry_not_string_exit2(pv_mod, writer):
    bad = ('{"id":"C-022","claim":"x","verb_class":"hedged","source":"y.md",'
           '"status":"needs-verify","sentinels":[123],"evidence":""}\n')
    inv = writer("bad.claims.jsonl", bad)
    nothing = writer("docs/empty.md", "noop\n")
    code, doc = run_json(pv_mod, [nothing, "--inventory", inv, *TODAY])
    assert code == 2
    assert any("sentinel entries must be strings" in e["message"] for e in doc["errors"])


def test_undecodable_scanned_file_exit2(pv_mod, writer, tmp_path):
    # A scanned .md with invalid UTF-8 fails the run (never skipped).
    p = tmp_path / "output"
    p.mkdir()
    f = p / "cv_x.md"
    f.write_bytes(b"- valid start\n\xff\xfe bad bytes\n")
    code, doc = run_json(pv_mod, [str(f), *TODAY])
    assert code == 2
    assert any("undecodable" in e["message"] for e in doc["errors"])


def test_bomless_utf16_scanned_file_fails_closed(pv_mod, writer, tmp_path):
    # Regression (morning-2026-06-16 #3): a BOM-less UTF-16-LE deliverable decodes as
    # VALID UTF-8 (NUL-interleaved), so the old reader did NOT raise and the PV rules
    # silently ran over mangled text (fail-OPEN). The shared reader's NUL-byte guard
    # must fail it closed (exit 2). Content carries a test-count brag (PV-009) so a
    # successful read WOULD have produced a finding.
    p = tmp_path / "output"
    p.mkdir()
    f = p / "cv_x.md"
    f.write_bytes("- shipped with 484 passing tests\n".encode("utf-16-le"))
    code, doc = run_json(pv_mod, [str(f), *TODAY])
    assert code == 2
    assert any("NUL" in e["message"] for e in doc["errors"])


def test_errors_force_exit2_even_with_findings(pv_mod, writer):
    # A real finding (exit 1) is overridden to exit 2 by a parse error.
    p = writer("output/cv_x.md", "- A (in progress, expected 03/2026)\n")  # PV-008
    inv = writer("bad.claims.jsonl", "{ not json\n")
    code, doc = run_json(pv_mod, [p, "--inventory", inv, *TODAY])
    assert code == 2
    assert doc["summary"]["findings"] >= 1
    assert doc["summary"]["errors"] >= 1


# --- lint-allow + META-001 (text findings) ---------------------------------
def test_lint_allow_pv_finding(pv_mod, writer):
    body = "- A (in progress, expected 03/2026) % lint-allow: PV-008 — backdated demo fixture\n"
    p = writer("output/x.tex", body)
    code, doc = run_json(pv_mod, [p, *TODAY])
    f = next(f for f in doc["findings"] if f["rule"] == "PV-008")
    assert f["allowed"] is True
    assert f["allow_reason"] == "backdated demo fixture"
    assert code == 0


def test_meta001_on_pv_misuse(pv_mod, writer):
    # Names PV-006 but PV-008 fired here.
    body = "- A (in progress, expected 03/2026) % lint-allow: PV-006 — wrong rule\n"
    p = writer("output/x.tex", body)
    code, doc = run_json(pv_mod, [p, *TODAY])
    rules = [f["rule"] for f in doc["findings"]]
    assert "META-001" in rules


def test_meta001_empty_reason_pv(pv_mod, writer):
    # TQ-3: PV's allow-resolution code is an independent copy of fingerprint's, so
    # the empty-reason META-001 branch needs its own guard. A lint-allow naming a
    # rule that DID fire here (PV-008), but with NO reason, is itself a finding —
    # and the underlying PV-008 is NOT allowed (no valid reason).
    body = "- A (in progress, expected 03/2026) % lint-allow: PV-008\n"
    p = writer("output/x.tex", body)
    code, doc = run_json(pv_mod, [p, *TODAY])
    rules = [f["rule"] for f in doc["findings"]]
    assert "META-001" in rules
    pv008 = next(f for f in doc["findings"] if f["rule"] == "PV-008")
    assert pv008["allowed"] is False
    assert code == 1


# --- JSON shape + determinism ----------------------------------------------
def test_json_shape(pv_mod, writer):
    p = writer("output/cv_x.md", "- Built a thing [VERIFY: x]\n")
    code, doc = run_json(pv_mod, [p, *TODAY])
    assert doc["tool"] == "lint_provenance"
    assert doc["schema_version"] == 1
    assert set(doc.keys()) == {
        "tool", "schema_version", "files_scanned", "findings", "errors", "summary"}
    for f in doc["findings"]:
        assert set(f.keys()) == {
            "path", "line", "rule", "severity", "message", "allowed", "allow_reason"}
    assert doc["summary"]["exit_code"] == code


def test_determinism_identical_bytes(pv_script, writer):
    from _runner import run_cli
    body = (
        "- A (in progress, expected 03/2026)\n"
        "- B [VERIFY: x] and [verify] malformed\n"
        "- Wrote 5,000 lines of code.\n"
    )
    p = writer("output/cv_x.md", body)
    c1, b1 = run_cli(pv_script, [p, "--format", "json", *TODAY])
    c2, b2 = run_cli(pv_script, [p, "--format", "json", *TODAY])
    assert c1 == c2 == 1
    assert b1 == b2
    assert not b1.startswith(b"\xef\xbb\xbf")
