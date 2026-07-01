# -*- coding: utf-8 -*-
"""Tests for ``cv_builder/helpers/match_jds.py`` — the P7 JD reverse-match ranker.

Pins the P7 done-gate as a reproducible check: given >=5 JDs incl. a
synthetic easy and a synthetic hard pairing, the easy ranks above the hard, and
the rendered report fits a one-page budget. Also covers the projected-fit maths,
deterministic ordering + tie-break, byte-identical output, atomic write, the
page-budget gate, and fail-closed loading.

Conventions (mirroring test_harness.py / the lint suite):
- Python stdlib + pytest only; version-portable (local 3.14, CI also 3.12).
- Fully offline + deterministic: no network, no timestamps, no machine paths.
- Test data is minted by the tests (``tmp_path``); the shipped fictional
  ``eval/fixtures/match_jds/`` manifests are touched read-only by the end-to-end
  gate test.
- Imported by file location, so no package __init__ / conftest is needed.
"""

import importlib.util
import json
import os
import subprocess
import sys

import pytest


# --------------------------------------------------------------------------- #
# Module loading (by file location — keeps discovery config-free).
# --------------------------------------------------------------------------- #
_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_HELPERS_DIR = os.path.dirname(_TESTS_DIR)
_REPO_ROOT = os.path.dirname(os.path.dirname(_HELPERS_DIR))
_MATCH_PY = os.path.join(_HELPERS_DIR, "match_jds.py")
_FIXTURES = os.path.join(_REPO_ROOT, "eval", "fixtures", "match_jds")


def _load_match():
    spec = importlib.util.spec_from_file_location("match_jds_under_test", _MATCH_PY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m = _load_match()

_WEIGHTS = {
    "ats_keywords": 15, "tagline": 8, "skills": 10, "bullet_quality": 22,
    "projects_evidence": 15, "narrative": 12, "company_role_fit": 13, "page_visual": 5,
}


def _dims(score):
    """The 8 canonical dims, all at ``score`` (weights sum to 100 -> total = score*10)."""
    return {k: {"weight": w, "score": score} for k, w in _WEIGHTS.items()}


def _manifest(jd, score, company="Acme", matches=None, gaps=None):
    return {
        "jd": jd,
        "title": jd.replace("_", " ").title(),
        "company": company,
        "dimensions": _dims(score),
        "strongest_matches": matches or [],
        "fatal_gaps": gaps or [],
        "source_jd": "x/%s.txt" % jd,
    }


def _write(d, name, data):
    path = os.path.join(str(d), name)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh)
    return path


def _run_cli(args):
    return subprocess.run(
        [sys.executable, _MATCH_PY] + args, capture_output=True, text=True
    )


# --------------------------------------------------------------------------- #
# Projected-fit maths + bands.
# --------------------------------------------------------------------------- #

def test_projected_total_uniform():
    assert m.projected_total(_dims(7.0)) == pytest.approx(70.0)
    assert m.projected_total(_dims(8.7)) == pytest.approx(87.0)


def test_projected_total_mixed_weights():
    # Bytework fixture maths: 9*15 + 8*8 + 8.5*10 + 9*22 + 9.5*15 + 8*12 + 9*13 + 8*5
    # = 877.5 -> 87.75.
    dims = {
        "ats_keywords": {"weight": 15, "score": 9.0},
        "tagline": {"weight": 8, "score": 8.0},
        "skills": {"weight": 10, "score": 8.5},
        "bullet_quality": {"weight": 22, "score": 9.0},
        "projects_evidence": {"weight": 15, "score": 9.5},
        "narrative": {"weight": 12, "score": 8.0},
        "company_role_fit": {"weight": 13, "score": 9.0},
        "page_visual": {"weight": 5, "score": 8.0},
    }
    assert m.projected_total(dims) == pytest.approx(87.75)


def test_band_thresholds():
    assert m.band_for(85.0) == "submit"
    assert m.band_for(84.9) == "strong"
    assert m.band_for(70.0) == "first-draft"
    assert m.band_for(59.9) == "fundamental-issues"


# --------------------------------------------------------------------------- #
# Ranking — the P7 gate at unit level.
# --------------------------------------------------------------------------- #

def test_rank_orders_by_projected_desc():
    manifests = [
        _manifest("mid", 6.0), _manifest("easy", 8.7), _manifest("hard", 2.0),
    ]
    ranked = m.rank(manifests)
    assert [s["jd"] for s in ranked] == ["easy", "mid", "hard"]
    assert ranked[0]["projected"] == pytest.approx(87.0)
    assert ranked[-1]["projected"] == pytest.approx(20.0)


def test_rank_tiebreak_by_jd_id():
    # Equal projected -> deterministic ascending jd id.
    ranked = m.rank([_manifest("zeta", 7.0), _manifest("alpha", 7.0)])
    assert [s["jd"] for s in ranked] == ["alpha", "zeta"]


def test_rank_easy_above_hard_five_jds():
    manifests = [
        _manifest("easy", 8.7), _manifest("upper", 7.7), _manifest("middle", 7.0),
        _manifest("lower", 6.0), _manifest("hard", 2.0),
    ]
    ranked = m.rank(manifests)
    assert ranked[0]["jd"] == "easy"
    assert ranked[-1]["jd"] == "hard"
    totals = [s["projected"] for s in ranked]
    assert totals == sorted(totals, reverse=True)


# --------------------------------------------------------------------------- #
# Fail-closed loading.
# --------------------------------------------------------------------------- #

def test_missing_dir_fail_closed(tmp_path):
    with pytest.raises(ValueError):
        m.load_manifests(os.path.join(str(tmp_path), "nope"))


def test_empty_dir_fail_closed(tmp_path):
    with pytest.raises(ValueError):
        m.load_manifests(str(tmp_path))


def test_malformed_json_fail_closed(tmp_path):
    path = os.path.join(str(tmp_path), "bad.json")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("{not json")
    with pytest.raises(ValueError):
        m.load_manifests(str(tmp_path))


def test_missing_field_fail_closed(tmp_path):
    bad = _manifest("x", 7.0)
    del bad["company"]
    _write(tmp_path, "x.json", bad)
    with pytest.raises(ValueError):
        m.load_manifests(str(tmp_path))


def test_weights_not_100_fail_closed(tmp_path):
    bad = _manifest("x", 7.0)
    bad["dimensions"]["page_visual"]["weight"] = 4  # now sums to 99
    _write(tmp_path, "x.json", bad)
    with pytest.raises(ValueError):
        m.load_manifests(str(tmp_path))


def test_score_out_of_range_fail_closed(tmp_path):
    bad = _manifest("x", 7.0)
    bad["dimensions"]["tagline"]["score"] = 11.0
    _write(tmp_path, "x.json", bad)
    with pytest.raises(ValueError):
        m.load_manifests(str(tmp_path))


def test_unknown_dimension_name_fail_closed(tmp_path):
    # The 8-dim contract is enforced, not just documented (01/07/2026 review P3:
    # DIMENSION_NAMES was a dead constant — any invented dimension name passed).
    bad = _manifest("x", 7.0)
    bad["dimensions"]["zz_invented"] = bad["dimensions"].pop("tagline")
    _write(tmp_path, "x.json", bad)
    with pytest.raises(ValueError):
        m.load_manifests(str(tmp_path))


def test_negative_weight_fail_closed(tmp_path):
    # Weights must be non-negative — {200, -100} sums to 100 but can push the
    # projected total outside [0, 100] (01/07/2026 review P3).
    bad = _manifest("x", 7.0)
    bad["dimensions"]["page_visual"]["weight"] -= 100
    bad["dimensions"]["tagline"]["weight"] += 100  # keep the sum at 100
    _write(tmp_path, "x.json", bad)
    with pytest.raises(ValueError):
        m.load_manifests(str(tmp_path))


def test_write_atomic_creates_missing_out_dir(tmp_path):
    # A user-supplied --out under a directory that doesn't exist yet must not
    # traceback (01/07/2026 review P3).
    out = os.path.join(str(tmp_path), "no", "such", "dir", "report.md")
    m.write_atomic(out, "hello\n")
    with open(out, encoding="utf-8") as fh:
        assert fh.read() == "hello\n"


def test_strongest_match_missing_key_fail_closed(tmp_path):
    bad = _manifest("x", 7.0, matches=[{"jd_req": "a", "evidence": "b"}])  # no source
    _write(tmp_path, "x.json", bad)
    with pytest.raises(ValueError):
        m.load_manifests(str(tmp_path))


def test_duplicate_jd_fail_closed(tmp_path):
    _write(tmp_path, "a.json", _manifest("dup", 7.0))
    _write(tmp_path, "b.json", _manifest("dup", 6.0))
    with pytest.raises(ValueError):
        m.load_manifests(str(tmp_path))


def test_bom_fail_closed(tmp_path):
    path = os.path.join(str(tmp_path), "bom.json")
    with open(path, "wb") as fh:
        fh.write(b"\xef\xbb\xbf" + json.dumps(_manifest("x", 7.0)).encode("utf-8"))
    with pytest.raises(ValueError):
        m.load_manifests(str(tmp_path))


def test_readme_md_is_ignored(tmp_path):
    _write(tmp_path, "x.json", _manifest("x", 7.0))
    with open(os.path.join(str(tmp_path), "_README.md"), "w", encoding="utf-8") as fh:
        fh.write("# not a manifest\n")
    manifests = m.load_manifests(str(tmp_path))
    assert [mm["jd"] for mm in manifests] == ["x"]


# --------------------------------------------------------------------------- #
# Rendering — byte-identical, atomic, page-budget gate.
# --------------------------------------------------------------------------- #

def test_report_byte_identical_on_rerun(tmp_path):
    scores = tmp_path / "manifests"
    scores.mkdir()
    _write(scores, "easy.json", _manifest("easy", 8.7))
    _write(scores, "hard.json", _manifest("hard", 2.0))
    out1 = os.path.join(str(tmp_path), "r1.md")
    out2 = os.path.join(str(tmp_path), "r2.md")
    r1 = _run_cli(["--manifests-dir", str(scores), "--out", out1])
    r2 = _run_cli(["--manifests-dir", str(scores), "--out", out2])
    assert r1.returncode == 0 and r2.returncode == 0
    with open(out1, "rb") as fh:
        b1 = fh.read()
    with open(out2, "rb") as fh:
        b2 = fh.read()
    assert b1 == b2
    assert not b1.startswith(b"\xef\xbb\xbf")  # no BOM
    assert b"\r\n" not in b1                    # LF only


def test_json_format_byte_identical(tmp_path):
    scores = tmp_path / "manifests"
    scores.mkdir()
    _write(scores, "easy.json", _manifest("easy", 8.7))
    _write(scores, "hard.json", _manifest("hard", 2.0))
    out1 = os.path.join(str(tmp_path), "r1.json")
    out2 = os.path.join(str(tmp_path), "r2.json")
    _run_cli(["--manifests-dir", str(scores), "--format", "json", "--out", out1])
    _run_cli(["--manifests-dir", str(scores), "--format", "json", "--out", out2])
    with open(out1, "rb") as fh:
        b1 = fh.read()
    with open(out2, "rb") as fh:
        b2 = fh.read()
    assert b1 == b2
    payload = json.loads(b1.decode("utf-8"))
    assert [p["jd"] for p in payload["pairings"]] == ["easy", "hard"]
    assert payload["pairings"][0]["rank"] == 1


def test_default_out_path(tmp_path):
    scores = tmp_path / "manifests"
    scores.mkdir()
    _write(scores, "easy.json", _manifest("easy", 8.7))
    r = _run_cli(["--manifests-dir", str(scores)])
    assert r.returncode == 0
    assert os.path.exists(os.path.join(str(tmp_path), "match_report.md"))


def test_atomic_write_leaves_no_tmp(tmp_path):
    out = os.path.join(str(tmp_path), "report.md")
    m.write_atomic(out, "hello\n")
    assert os.path.exists(out)
    assert not os.path.exists(out + ".tmp")
    with open(out, "rb") as fh:
        assert fh.read() == b"hello\n"


def test_page_budget_gate_trips_and_still_writes(tmp_path):
    scores = tmp_path / "manifests"
    scores.mkdir()
    _write(scores, "a.json", _manifest("a", 7.0))
    out = os.path.join(str(tmp_path), "report.md")
    # max-lines 1 forces any real report over budget -> exit 1, but the file is
    # written first so the operator can see what overflowed.
    r = _run_cli(["--manifests-dir", str(scores), "--out", out, "--max-lines", "1"])
    assert r.returncode == 1
    assert os.path.exists(out)


def test_page_budget_ok_under_generous_limit(tmp_path):
    scores = tmp_path / "manifests"
    scores.mkdir()
    _write(scores, "a.json", _manifest("a", 7.0))
    out = os.path.join(str(tmp_path), "report.md")
    r = _run_cli(["--manifests-dir", str(scores), "--out", out, "--max-lines", "999"])
    assert r.returncode == 0


def test_default_manifests_dir_shape():
    # No --manifests-dir -> resolves under the active profile's output/_match.
    d = m._default_manifests_dir()
    assert d.replace("\\", "/").endswith("output/_match/manifests")


# --------------------------------------------------------------------------- #
# End-to-end against the shipped fictional fixtures — the P7 done-gate.
# --------------------------------------------------------------------------- #

@pytest.mark.skipif(not os.path.isdir(_FIXTURES), reason="no shipped match_jds fixtures")
def test_shipped_fixtures_rank_easy_above_hard():
    manifests = m.load_manifests(_FIXTURES)
    ranked = m.rank(manifests)
    ids = [s["jd"] for s in ranked]
    # The gate: the obvious easy pairing ranks first, the obvious hard one last.
    assert ids[0] == "bytework_backend_placement"
    assert ids[-1] == "corewell_embedded_firmware"
    # Strictly decreasing projected totals across the five.
    totals = [s["projected"] for s in ranked]
    assert all(a > b for a, b in zip(totals, totals[1:]))
    # Bands are meaningfully separated: easy is submit/strong, hard is the floor.
    assert ranked[0]["band"] in ("submit", "strong")
    assert ranked[-1]["band"] == "fundamental-issues"
    # Every shipped fixture is flagged fictional.
    assert all(s["fictional"] for s in ranked)


@pytest.mark.skipif(not os.path.isdir(_FIXTURES), reason="no shipped match_jds fixtures")
def test_shipped_fixtures_report_fits_one_page():
    manifests = m.load_manifests(_FIXTURES)
    md = m.render_markdown(m.rank(manifests))
    assert not m.over_budget(md, m.DEFAULT_MAX_LINES)
