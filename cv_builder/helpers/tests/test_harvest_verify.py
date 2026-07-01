# -*- coding: utf-8 -*-
r"""Tests for ``cv_builder/helpers/harvest_verify.py`` — the P5 VERIFY harvester.

Pins the P5 done-gate: the harvester finds 100% of planted sentinels in
a seeded KB test (and ZERO decoys — no false positives). Also covers dedup /
batching (K0), the derived-files re-sweep list, dry-run writes nothing, --apply
idempotence, fail-closed on bad input, and byte-identical determinism.

Conventions (mirroring test_harness.py / the lint suite):
- Python stdlib + pytest only; version-portable (local 3.14, CI also 3.12).
- Fully offline + deterministic: no network, no timestamps, no machine paths in
  asserted output.
- Test data is minted by the tests (``tmp_path``) — never borrowed from the
  private KB. The real-KB dry-run is the operator's job, not the suite's.
- Imported by file location, so no package __init__ / conftest is needed (the
  parent tests/ dir uses this idiom; the lint/ subdir has its own conftest).
"""

import importlib.util
import io
import json
import os
import subprocess
import sys
from contextlib import redirect_stdout

import pytest


# --------------------------------------------------------------------------- #
# Module loading (by file location — keeps discovery config-free).
# --------------------------------------------------------------------------- #
_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_HELPERS_DIR = os.path.dirname(_TESTS_DIR)
_REPO_ROOT = os.path.dirname(os.path.dirname(_HELPERS_DIR))
_HARVEST_PY = os.path.join(_HELPERS_DIR, "harvest_verify.py")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def hv():
    return _load("harvest_verify_undertest", _HARVEST_PY)


def run_inproc(mod, argv):
    """Run mod.run(argv) capturing stdout. Returns (exit_code, stdout_str)."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = mod.run(list(argv))
    return code, buf.getvalue()


def run_json(mod, argv):
    code, out = run_inproc(mod, [*argv, "--format", "json"])
    return code, json.loads(out)


def run_cli(argv):
    """Shell out so the real process exit code (0/2) is exercised."""
    proc = subprocess.run(
        [sys.executable, _HARVEST_PY, *argv],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return proc.returncode, proc.stdout


def write(tmp_path, name, text):
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(text.encode("utf-8"))
    return str(p)


# --------------------------------------------------------------------------- #
# The seeded fixture KB: N planted sentinels + decoys (fictional content).
# --------------------------------------------------------------------------- #
# Planted sentinels (the harvester MUST find every one):
#   [VERIFY] (bare)            x1
#   [VERIFY: body]             x2  (distinct bodies)
#   [ASK: body]                x2  (one duplicated across two files -> dedups)
#   in-progress label          x1
#   pipeline status 'planned'  x2  (two "planned — confirm" lines)
# Total planted SENTINEL LOCATIONS = 8 (one [ASK] body repeats -> 7 questions
# after dedup; see the dedup test).
N_PLANTED_LOCATIONS = 8

_EXPERIENCE = (
    "# Fictional experience: Avery Quillfeather\n"
    "\n"
    "## Marketplace ops\n"
    "**Context:** ran listings and courier coordination [VERIFY: order volumes].\n"
    "Team size: [VERIFY]\n"
    "Sponsorship deals secured [VERIFY: sponsorship values].\n"
    "Started a retrieval assistant (in progress, expected 09/2026).\n"
    "Open question for the owner: [ASK: which marketplaces were used?]\n"
    "\n"
    "<!-- decoy 1: the literal word verify in prose is NOT a sentinel -->\n"
    "We verify each order before dispatch and ask the courier to confirm.\n"
    "<!-- decoy 2: lowercase near-miss is a PV-005 concern, not a harvest hit -->\n"
    "A note recorded [verify] in the wrong case, and an [ask: lowercase] too.\n"
    "<!-- decoy 3: an already-CONFIRMED status line is not unconfirmed -->\n"
    "**Status:** done\n"
)

_PIPELINE = (
    "# Fictional pipeline (planned & in-progress work)\n"
    "\n"
    "### Build A\n"
    "**Status:** planned — confirm\n"
    "**Expected:** 09/2026\n"
    "\n"
    "### Build B\n"
    "**Status:** planned — confirm\n"
    "Open question for the owner: [ASK: which marketplaces were used?]\n"
)

# A downstream file that REFERENCES the experience file by basename — the
# derived-files re-sweep target. It carries no sentinel of its own.
_BUNDLE = (
    "# Fictional bundle\n"
    "\n"
    "Pulls claims from experience_avery.md for the placement narrative.\n"
    "Also cites layout_budgets.md (a non-sentinel reference).\n"
)


@pytest.fixture
def seeded_kb(tmp_path):
    """Write the seeded KB under a mirrored cv_builder/ tree; return the dir."""
    root = tmp_path / "cv_builder" / "experience"
    bundles = tmp_path / "cv_builder" / "bundles"
    write(tmp_path, "cv_builder/experience/experience_avery.md", _EXPERIENCE)
    write(tmp_path, "cv_builder/experience/experience_pipeline.md", _PIPELINE)
    write(tmp_path, "cv_builder/bundles/bundle_avery.md", _BUNDLE)
    return tmp_path


# --------------------------------------------------------------------------- #
# THE DONE-GATE TEST: 100% of planted sentinels, ZERO decoys.
# --------------------------------------------------------------------------- #
def test_done_gate_finds_all_planted_and_no_decoys(hv, seeded_kb):
    code, doc = run_json(hv, [str(seeded_kb / "cv_builder")])
    assert code == 0, doc

    # Every planted sentinel LOCATION is found (count across all questions).
    assert doc["summary"]["locations"] == N_PLANTED_LOCATIONS, doc

    # Per-kind tallies prove each frozen sentinel kind was swept.
    by_kind = {}
    flat_locs = []
    for q in doc["questions"]:
        by_kind.setdefault(q["kind"], 0)
        by_kind[q["kind"]] += len(q["locations"])
        flat_locs.extend("%s:%d" % (l["path"], l["line"]) for l in q["locations"])
    assert by_kind.get("verify") == 3, by_kind          # bare + 2 bodies
    assert by_kind.get("ask") == 2, by_kind             # 2 locations (one dup body)
    assert by_kind.get("in-progress") == 1, by_kind
    assert by_kind.get("pipeline-status") == 2, by_kind

    # ZERO decoys: no hit may land on a decoy line. The decoy lines are:
    #   line "We verify each order ..."   (prose 'verify' / 'ask' / 'confirm')
    #   line "[verify]" + "[ask: lowercase]" (PV-005 near-misses, not harvest hits)
    #   line "**Status:** done"           (a confirmed status, not 'planned')
    decoy_lines = {11, 13, 15}  # 1-based line numbers of the three decoy lines
    for loc in flat_locs:
        ln = int(loc.rsplit(":", 1)[1])
        assert ln not in decoy_lines, "hit landed on a decoy line: %s" % loc
    # And no decoy CONTENT leaked into any question text.
    blob = json.dumps(doc)
    assert "We verify each order" not in blob
    assert "lowercase" not in blob          # neither [ask: lowercase] nor prose decoy
    assert "Status:** done" not in blob


# --------------------------------------------------------------------------- #
# Dedup / batching (K0 discipline).
# --------------------------------------------------------------------------- #
def test_identical_ask_dedups_with_both_locations(hv, seeded_kb):
    _, doc = run_json(hv, [str(seeded_kb / "cv_builder")])
    asks = [q for q in doc["questions"]
            if q["kind"] == "ask" and "which marketplaces" in q["question"]]
    # The same [ASK: which marketplaces were used?] appears in both the experience
    # file and the pipeline file -> ONE batched question, TWO locations.
    assert len(asks) == 1, asks
    paths = sorted(l["path"] for l in asks[0]["locations"])
    assert len(paths) == 2
    assert any(p.endswith("experience_avery.md") for p in paths)
    assert any(p.endswith("experience_pipeline.md") for p in paths)


def test_distinct_verify_bodies_stay_separate(hv, seeded_kb):
    _, doc = run_json(hv, [str(seeded_kb / "cv_builder")])
    verifies = [q for q in doc["questions"] if q["kind"] == "verify"]
    questions = {q["question"] for q in verifies}
    # bare [VERIFY] + two distinct bodies = three distinct questions.
    assert len(questions) == 3, questions


# --------------------------------------------------------------------------- #
# Derived-files re-sweep list correctness (from real references).
# --------------------------------------------------------------------------- #
def test_resweep_lists_files_that_reference_the_source(hv, seeded_kb):
    _, doc = run_json(hv, [str(seeded_kb / "cv_builder")])
    # Sentinels in experience_avery.md must list bundle_avery.md (which cites
    # "experience_avery.md") in the re-sweep, derived from the actual reference.
    for q in doc["questions"]:
        avery_loc = any(l["path"].endswith("experience_avery.md") for l in q["locations"])
        if avery_loc:
            assert any(r.endswith("bundle_avery.md") for r in q["resweep"]), q


def test_resweep_excludes_unreferenced_source(hv, seeded_kb):
    _, doc = run_json(hv, [str(seeded_kb / "cv_builder")])
    # Nothing references experience_pipeline.md in this fixture -> its
    # pipeline-status questions carry an empty re-sweep.
    for q in doc["questions"]:
        only_pipeline = q["locations"] and all(
            l["path"].endswith("experience_pipeline.md") for l in q["locations"])
        if only_pipeline:
            assert q["resweep"] == [], q


def test_basename_match_is_whole_token(hv, tmp_path):
    # `pipeline.md` referenced elsewhere must NOT match `experience_pipeline.md`
    # (whole-token guard), so a sentinel in experience_pipeline.md gets no spurious
    # re-sweep from a file mentioning a different `pipeline.md`.
    write(tmp_path, "cv_builder/experience/experience_pipeline.md",
          "**Status:** planned — confirm\n")
    write(tmp_path, "cv_builder/support/other.md",
          "See pipeline.md for the deploy steps.\n")  # different file, substring
    _, doc = run_json(hv, [str(tmp_path / "cv_builder")])
    for q in doc["questions"]:
        assert q["resweep"] == [], q


# --------------------------------------------------------------------------- #
# Dry-run writes nothing; --apply is idempotent.
# --------------------------------------------------------------------------- #
def test_dry_run_writes_nothing(hv, seeded_kb):
    before = sorted(os.listdir(str(seeded_kb / "cv_builder" / "experience")))
    run_inproc(hv, [str(seeded_kb / "cv_builder")])
    after = sorted(os.listdir(str(seeded_kb / "cv_builder" / "experience")))
    assert before == after
    # No question file anywhere under the KB.
    for dirpath, _dirs, files in os.walk(str(seeded_kb)):
        assert "_verify_questions.md" not in files


def test_apply_writes_to_default_and_is_idempotent(hv, seeded_kb):
    kb = str(seeded_kb / "cv_builder")
    run_inproc(hv, [kb, "--apply"])
    # Default out = first existing KB *directory* root passed in -> kb/_verify...
    out_path = os.path.join(kb, "_verify_questions.md")
    assert os.path.exists(out_path)
    first = open(out_path, "rb").read()
    # Re-running --apply yields byte-identical content (idempotent).
    run_inproc(hv, [kb, "--apply"])
    second = open(out_path, "rb").read()
    assert first == second
    assert not first.startswith(b"\xef\xbb\xbf")  # no BOM
    assert b"\r\n" not in first                    # LF only


def test_apply_out_flag_targets_named_path(hv, seeded_kb, tmp_path):
    kb = str(seeded_kb / "cv_builder")
    dest = str(tmp_path / "questions_out.md")
    run_inproc(hv, [kb, "--apply", "--out", dest])
    assert os.path.exists(dest)
    body = open(dest, "rb").read().decode("utf-8")
    assert body.startswith("# Verify-harvest question list")


# --------------------------------------------------------------------------- #
# Fail-closed on bad input.
# --------------------------------------------------------------------------- #
def test_fail_closed_on_bom(hv, tmp_path):
    p = tmp_path / "cv_builder" / "experience" / "bad.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"\xef\xbb\xbf# has a BOM\n[VERIFY: x]\n")
    code, doc = run_json(hv, [str(tmp_path / "cv_builder")])
    assert code == 2, doc
    assert doc["summary"]["errors"] >= 1


def test_fail_closed_on_undecodable_bytes(hv, tmp_path):
    p = tmp_path / "cv_builder" / "experience" / "bad.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"\xff\xfe not utf-8 \x80\x81\n")
    code, _ = run_json(hv, [str(tmp_path / "cv_builder")])
    assert code == 2


def test_fail_closed_on_bomless_utf16(hv, tmp_path):
    # Regression (morning-2026-06-16 #3): a BOM-less UTF-16-LE source decodes as VALID
    # UTF-8 (NUL-interleaved), so the old reader did NOT raise — the sentinel sweep then
    # ran over mangled bytes and silently harvested nothing (fail-OPEN). The shared
    # reader's NUL-byte guard must fail it closed (exit 2). The body holds a [VERIFY]
    # sentinel that a successful read WOULD have harvested.
    p = tmp_path / "cv_builder" / "experience" / "bad.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes("[VERIFY: confirm the placement dates]\n".encode("utf-16-le"))
    code, doc = run_json(hv, [str(tmp_path / "cv_builder")])
    assert code == 2
    assert doc["summary"]["errors"] >= 1


_LINE_ENDING_SOURCE = (
    "# Fictional source\n"
    "\n"
    "Team size: [VERIFY]\n"
    "Sponsorship deals secured [VERIFY: sponsorship values].\n"
    "Open question: [ASK: which marketplaces were used?]\n"
    "Started a retrieval assistant (in progress, expected 09/2026).\n"
)


def _harvest_projection(doc):
    """Harvested questions as an ending-agnostic projection (drop the temp path)."""
    return sorted(
        (q["kind"], q["question"], tuple(loc["line"] for loc in q["locations"]))
        for q in doc["questions"]
    )


@pytest.mark.parametrize("eol", ["\n", "\r\n"])
def test_harvest_identical_across_endings(hv, tmp_path, eol):
    # Regression (morning-2026-06-16 #6): the sweep splits on "\n", so a CRLF source
    # (Git autocrlf checkout / a committed CRLF file) leaves a trailing "\r" per line —
    # it must not move a sentinel's line or change a harvested question. Same content as
    # LF and CRLF must yield identical questions. CR-only is out of scope (.gitattributes
    # pins LF; nothing here emits it). Two dirs so each file owns its own line ending.
    lf_dir = tmp_path / "lf" / "cv_builder" / "experience"
    eol_dir = tmp_path / "eol" / "cv_builder" / "experience"
    lf_dir.mkdir(parents=True, exist_ok=True)
    eol_dir.mkdir(parents=True, exist_ok=True)
    (lf_dir / "e.md").write_bytes(_LINE_ENDING_SOURCE.encode("utf-8"))
    (eol_dir / "e.md").write_bytes(_LINE_ENDING_SOURCE.replace("\n", eol).encode("utf-8"))
    code_lf, doc_lf = run_json(hv, [str(tmp_path / "lf" / "cv_builder")])
    code_eol, doc_eol = run_json(hv, [str(tmp_path / "eol" / "cv_builder")])
    assert _harvest_projection(doc_lf), "fixture should harvest questions"
    assert _harvest_projection(doc_eol) == _harvest_projection(doc_lf), eol
    assert code_eol == code_lf


def test_apply_does_not_write_on_parse_error(hv, tmp_path):
    p = tmp_path / "cv_builder" / "experience" / "bad.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"\xef\xbb\xbf[VERIFY: x]\n")
    code, _ = run_inproc(hv, [str(tmp_path / "cv_builder"), "--apply"])
    assert code == 2
    # Fail-closed: no partial question list is persisted.
    for dirpath, _dirs, files in os.walk(str(tmp_path)):
        assert "_verify_questions.md" not in files


def test_named_missing_path_is_usage_error(hv, tmp_path):
    code, _ = run_inproc(hv, [str(tmp_path / "does_not_exist")])
    assert code == 2


# --------------------------------------------------------------------------- #
# Determinism: byte-identical output for the same KB state.
# --------------------------------------------------------------------------- #
def test_byte_identical_output(hv, seeded_kb):
    kb = str(seeded_kb / "cv_builder")
    _, a = run_inproc(hv, [kb, "--format", "json"])
    _, b = run_inproc(hv, [kb, "--format", "json"])
    assert a == b
    _, c = run_inproc(hv, [kb])  # text format too
    _, d = run_inproc(hv, [kb])
    assert c == d


def test_cli_clean_kb_exit0_and_lf(seeded_kb):
    kb = str(seeded_kb / "cv_builder")
    code, out = run_cli([kb, "--format", "json"])
    assert code == 0
    assert b"\r\n" not in out
    assert not out.startswith(b"\xef\xbb\xbf")


def test_cli_unknown_flag_exit2(seeded_kb):
    code, _ = run_cli([str(seeded_kb / "cv_builder"), "--definitely-not-a-flag"])
    assert code == 2


def test_empty_sweep_is_clean(hv, tmp_path):
    # A KB dir with a sentinel-free file -> exit 0, zero questions.
    write(tmp_path, "cv_builder/experience/clean.md",
          "# Clean\nAll facts confirmed; nothing to ask.\n")
    code, doc = run_json(hv, [str(tmp_path / "cv_builder")])
    assert code == 0
    assert doc["summary"]["questions"] == 0


def test_default_kb_roots_are_profile_scoped(hv, tmp_path):
    # P6: default roots are users/<active>/<tail> where <active> comes from
    # users/.active (else the generic default). The tail segments are unchanged.
    root = str(tmp_path)
    p = tmp_path / "users" / ".active"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("acme\n", encoding="utf-8")
    roots = hv.default_kb_roots(root)
    assert roots == (
        "users/acme/cv_builder/experience",
        "users/acme/knowledge_base/extractions",
        "users/acme/cv_builder/bundles",
        "users/acme/cv_builder/support",
    )
    # Missing pointer -> generic default profile, never a crash, never a name.
    roots2 = hv.default_kb_roots(str(tmp_path / "no_such_repo"))
    assert all(r.startswith("users/default/") for r in roots2)


def test_poisoned_active_pointer_cannot_escape_users_tree(hv, tmp_path):
    # Security regression (overnight-audit B-F1): a corrupt or malicious
    # users/.active must NOT let default_kb_roots compose a path that climbs out
    # of users/<profile>/. A traversal / separator / dotfile payload falls back to
    # the PII-free default (an empty sweep), exactly like a missing pointer. Before
    # the fix, ".active" = "../secret" produced "users/../secret/..." — escaping
    # the tree, so the harvester would sweep out-of-profile content.
    root = str(tmp_path)
    p = tmp_path / "users" / ".active"
    p.parent.mkdir(parents=True, exist_ok=True)
    for payload in ("../secret", "..", ".", "a/b", "a\\b", ".hidden", "demo/../alice"):
        p.write_text(payload + "\n", encoding="utf-8")
        roots = hv.default_kb_roots(root)
        assert all(r.startswith("users/default/") for r in roots), payload
        assert not any(seg == ".." for r in roots for seg in r.split("/")), payload
    # The happy path is unchanged — a valid name still resolves normally.
    p.write_text("alice\n", encoding="utf-8")
    assert hv.default_kb_roots(root)[0] == "users/alice/cv_builder/experience"


def test_valid_profile_name_rejects_trailing_dot_space_control(hv):
    # B-F2 MIRROR: _valid_profile_name must reject the same trailing dot / leading-
    # trailing whitespace / control-char names profile.py:_valid_name now rejects —
    # the two validity gates stay in LOCKSTEP (this pair drifted once before).
    assert hv._valid_profile_name("alice")          # a normal name still passes
    for bad in ("alice.",                            # trailing dot -> Win alias
                "alice ", " alice", "alice\t",       # leading/trailing whitespace
                "alice\n", "\talice",
                "al\x00ice",                         # interior NUL (survives strip)
                "ali\x1fce", "ali\x7fce"):           # interior C0 / DEL control
        assert not hv._valid_profile_name(bad), bad
    # Lockstep check: profile.py:_valid_name agrees on every one of these.
    profile = _load("profile_for_harvest_lockstep", os.path.join(_HELPERS_DIR, "profile.py"))
    for name in ("alice", "alice.", "alice ", " alice", "al\x00ice", "ali\x7fce",
                 "..", ".", "a/b", ".hidden"):
        assert hv._valid_profile_name(name) == profile._valid_name(name), name


def test_poisoned_dot_or_control_active_falls_back_to_default(hv, tmp_path):
    # B-F2: a users/.active poisoned with a trailing-dot or interior-control name
    # now falls back to the PII-free default (an empty sweep) — exactly the existing
    # fail-safe for a traversal/separator payload. Never an out-of-tree or aliased
    # sweep. (Leading/trailing WHITESPACE in the pointer is normalised by the
    # existing lines[0].strip() in _active_profile_name, so "alice " resolves to
    # "alice" — not an alias; _valid_profile_name still rejects raw whitespace
    # names directly, pinned by the lockstep test above. The trailing DOT survives
    # the strip and is the real new catch.)
    root = str(tmp_path)
    p = tmp_path / "users" / ".active"
    p.parent.mkdir(parents=True, exist_ok=True)
    for payload in ("alice.", "sam\x00rath", "sam\x7frath"):
        p.write_text(payload + "\n", encoding="utf-8")
        roots = hv.default_kb_roots(root)
        assert all(r.startswith("users/default/") for r in roots), repr(payload)
    # A valid name still composes its own roots (no over-rejection).
    p.write_text("alice\n", encoding="utf-8")
    assert hv.default_kb_roots(root)[0] == "users/alice/cv_builder/experience"


def test_case_variant_active_composes_in_tree_root_no_traversal(hv, tmp_path):
    # A case-variant .active (e.g. "ALICE") is a valid path segment, so the
    # harvester composes users/ALICE/... verbatim — an in-tree path with no
    # separator and no traversal. On a case-sensitive FS that dir simply does not
    # exist (an empty sweep); the EXACT-CASE alias guard is profile.py's job, while
    # harvest's fail-safe is the empty sweep. The load-bearing property here is that
    # the composed root never climbs out of users/<profile>/ and is never an alias
    # token like ".." — it is the variant string itself, which gather_paths will
    # simply skip if absent.
    root = str(tmp_path)
    p = tmp_path / "users" / ".active"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("ALICE\n", encoding="utf-8")
    roots = hv.default_kb_roots(root)
    assert roots[0] == "users/ALICE/cv_builder/experience"
    assert not any(seg == ".." for r in roots for seg in r.split("/"))


def test_default_roots_run_without_error(hv):
    # No-args run over the active profile's KB roots under users/<active>/ (or none
    # in a public clone): it must complete cleanly (exit 0), never crash, never write.
    code, doc = run_json(hv, [])
    assert code in (0, 2)  # 0 normally; 2 only if a real KB file is unparseable
    assert "questions" in doc
