# -*- coding: utf-8 -*-
"""Tests for ``eval/harness.py`` — the P4 deterministic eval harness.

These pin the *public behaviour* of the rubric scorer against the P4
done-gate: calibration within ±2 of the known 85.4 before any corpus run, and a
byte-identical report for identical inputs.

Conventions (mirroring test_char_count.py / the P1 fences):
- Python stdlib + pytest only; version-portable (local 3.14, CI also 3.12).
- Fully offline and deterministic: no network, no timestamps, no machine paths.
- Test data is minted by the tests (``tmp_path``) — never borrowed from the
  private ``output/`` artefacts. The shipped ``eval/scores/*.json`` fixtures are
  only touched by the end-to-end calibration test, read-only.
- Imported by file location so no package ``__init__`` / ``conftest`` is needed.
"""

import importlib.util
import json
import os
import subprocess
import sys

import pytest


# --------------------------------------------------------------------------- #
# Module loading (by file location — keeps test discovery config-free).
# --------------------------------------------------------------------------- #

_REPO_ROOT = os.path.dirname(  # cv-editor/
    os.path.dirname(  # cv_builder/
        os.path.dirname(  # cv_builder/helpers/
            os.path.dirname(os.path.abspath(__file__))  # .../tests/
        )
    )
)
_HARNESS_PY = os.path.join(_REPO_ROOT, "eval", "harness.py")
# The shipped manifests live in eval/scores (private instance) or eval/fixtures
# (public engine clone) — whichever this tree carries. The end-to-end calibration
# test resolves the reference from the flag, not a hardcoded case name, so it is
# identity-agnostic and passes in either tree.
_SHIPPED_SCORES = next(
    (d for d in (
        os.path.join(_REPO_ROOT, "eval", "scores"),
        os.path.join(_REPO_ROOT, "eval", "fixtures", "scores"),
    ) if os.path.isdir(d)),
    os.path.join(_REPO_ROOT, "eval", "scores"),
)


def _load_harness():
    spec = importlib.util.spec_from_file_location("harness_under_test", _HARNESS_PY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


h = _load_harness()


# --------------------------------------------------------------------------- #
# Minted manifests.
# --------------------------------------------------------------------------- #

def _write(scores_dir, name, data):
    path = os.path.join(scores_dir, name)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh)
    return path


def _good_ref():
    """A reference manifest whose 'after' total is exactly 85.4."""
    return {
        "case": "refcase",
        "genre": "tech_student",
        "no_target": False,
        "calibration_reference": True,
        "calibration_target": 85.4,
        "source": "test://ref",
        "dimensions": {
            # 8.54 * 100 / 10 = 85.4 with a single 100%-weight dimension.
            "all": {"weight": 100, "before": 5.0, "after": 8.54},
        },
    }


def _bad_case(case="badcase", before=4.0, after=6.0):
    """A no-target corpus manifest whose 'before' total is in the low band."""
    return {
        "case": case,
        "genre": "sales_commercial",
        "no_target": True,
        "source": "test://%s" % case,
        "dimensions": {
            "bullet_quality": {"weight": 60, "before": before, "after": after},
            "narrative": {"weight": 40, "before": before, "after": after},
        },
    }


# --------------------------------------------------------------------------- #
# Weighted-sum correctness.
# --------------------------------------------------------------------------- #

def test_weighted_total_basic():
    dims = {"a": {"weight": 100, "before": 5.0, "after": 8.54}}
    assert h.weighted_total(dims, "before") == pytest.approx(50.0)
    assert h.weighted_total(dims, "after") == pytest.approx(85.4)


def test_weighted_total_mixed_weights():
    # 6*30 + 5*18 + 8*16 + 7.5*14 + 7*12 + 8*10 = 667 -> 66.7 (the Sales 'after').
    dims = {
        "bullet_quality": {"weight": 30, "before": 3.0, "after": 6.0},
        "projects_evidence": {"weight": 18, "before": 3.0, "after": 5.0},
        "narrative": {"weight": 16, "before": 6.0, "after": 8.0},
        "skills": {"weight": 14, "before": 6.0, "after": 7.5},
        "tagline": {"weight": 12, "before": 3.0, "after": 7.0},
        "page_visual": {"weight": 10, "before": 7.0, "after": 8.0},
    }
    assert h.weighted_total(dims, "after") == pytest.approx(66.7)


def test_band_thresholds():
    assert h.band_for(85.0) == "submit"
    assert h.band_for(84.9) == "strong"
    assert h.band_for(43.0) == "fundamental-issues"
    assert h.band_for(59.9) == "fundamental-issues"


# --------------------------------------------------------------------------- #
# No-target re-weighting: weights still sum to 100, total tracks the new weights.
# --------------------------------------------------------------------------- #

def test_no_target_reweighting_sums_to_100(tmp_path):
    scores = tmp_path
    _write(scores, "ref.json", _good_ref())
    # Sales-style no-target redistribution (ATS+Fit 28% pushed onto substance).
    reweighted = {
        "case": "salesy",
        "genre": "sales_commercial",
        "no_target": True,
        "source": "test://salesy",
        "dimensions": {
            "bullet_quality": {"weight": 30, "before": 3.0, "after": 6.0},
            "projects_evidence": {"weight": 18, "before": 3.0, "after": 5.0},
            "narrative": {"weight": 16, "before": 6.0, "after": 8.0},
            "skills": {"weight": 14, "before": 6.0, "after": 7.5},
            "tagline": {"weight": 12, "before": 3.0, "after": 7.0},
            "page_visual": {"weight": 10, "before": 7.0, "after": 8.0},
        },
    }
    _write(scores, "salesy.json", reweighted)
    manifests = h.load_manifests(str(scores))
    salesy = next(m for m in manifests if m["case"] == "salesy")
    assert sum(d["weight"] for d in salesy["dimensions"].values()) == 100
    assert h.weighted_total(salesy["dimensions"], "before") == pytest.approx(43.0)
    assert h.weighted_total(salesy["dimensions"], "after") == pytest.approx(66.7)


def test_weights_not_summing_to_100_fail_closed(tmp_path):
    broken = _bad_case()
    broken["dimensions"]["bullet_quality"]["weight"] = 50  # now sums to 90
    _write(tmp_path, "broken.json", broken)
    with pytest.raises(ValueError):
        h.load_manifests(str(tmp_path))


def test_malformed_json_fail_closed(tmp_path):
    path = os.path.join(str(tmp_path), "bad.json")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("{not json")
    with pytest.raises(ValueError):
        h.load_manifests(str(tmp_path))


def test_missing_field_fail_closed(tmp_path):
    incomplete = _bad_case()
    del incomplete["genre"]
    _write(tmp_path, "incomplete.json", incomplete)
    with pytest.raises(ValueError):
        h.load_manifests(str(tmp_path))


# --------------------------------------------------------------------------- #
# Calibration pass / fail.
# --------------------------------------------------------------------------- #

def test_calibration_passes_with_good_ref_and_seeded_bad(tmp_path):
    _write(tmp_path, "ref.json", _good_ref())
    _write(tmp_path, "bad.json", _bad_case())
    manifests = h.load_manifests(str(tmp_path))
    ok, lines = h.calibrate(manifests)
    assert ok
    assert any("PASS" in l for l in lines)


def test_calibration_fails_when_ref_out_of_tolerance(tmp_path):
    ref = _good_ref()
    ref["dimensions"]["all"]["after"] = 7.0  # -> 70.0, far from 85.4
    _write(tmp_path, "ref.json", ref)
    _write(tmp_path, "bad.json", _bad_case())
    manifests = h.load_manifests(str(tmp_path))
    ok, _ = h.calibrate(manifests)
    assert not ok


def test_calibration_fails_when_no_seeded_bad(tmp_path):
    _write(tmp_path, "ref.json", _good_ref())
    # A corpus case that is NOT low-band (before total 80).
    _write(tmp_path, "good.json", _bad_case(case="goodcase", before=8.0, after=9.0))
    manifests = h.load_manifests(str(tmp_path))
    ok, _ = h.calibrate(manifests)
    assert not ok


def test_multiple_references_fail_closed(tmp_path):
    # Two flagged references is an ambiguous anchor — load/resolve must raise,
    # never silently pick one (de-identification: exactly one reference per tree).
    ref1 = _good_ref()
    ref2 = _good_ref()
    ref2["case"] = "refcase2"
    _write(tmp_path, "ref1.json", ref1)
    _write(tmp_path, "ref2.json", ref2)
    _write(tmp_path, "bad.json", _bad_case())
    manifests = h.load_manifests(str(tmp_path))
    with pytest.raises(ValueError):
        h.reference_manifest(manifests)


def test_calibration_reference_requires_target(tmp_path):
    # A reference flag with no calibration_target is fail-closed at load time.
    ref = _good_ref()
    del ref["calibration_target"]
    _write(tmp_path, "ref.json", ref)
    with pytest.raises(ValueError):
        h.load_manifests(str(tmp_path))


def test_calibration_within_tolerance_boundary(tmp_path):
    # 87.4 is exactly +2.0 from 85.4 -> still PASS (tolerance is inclusive).
    ref = _good_ref()
    ref["dimensions"]["all"]["after"] = 8.74
    _write(tmp_path, "ref.json", ref)
    _write(tmp_path, "bad.json", _bad_case())
    manifests = h.load_manifests(str(tmp_path))
    ok, _ = h.calibrate(manifests)
    assert ok


# --------------------------------------------------------------------------- #
# Mean per-dimension delta excludes the calibration reference.
# --------------------------------------------------------------------------- #

def test_mean_dimension_delta_excludes_reference(tmp_path):
    _write(tmp_path, "ref.json", _good_ref())  # after-before = 3.54 on 'all'
    _write(tmp_path, "b1.json", _bad_case(case="b1", before=3.0, after=6.0))
    _write(tmp_path, "b2.json", _bad_case(case="b2", before=5.0, after=8.0))
    manifests = h.load_manifests(str(tmp_path))
    deltas = h.mean_dimension_deltas(manifests)
    # 'all' belongs only to the reference -> excluded entirely.
    assert "all" not in deltas
    # bullet_quality: (6-3) and (8-5) -> mean 3.0 over 2 cases.
    mean, count = deltas["bullet_quality"]
    assert mean == pytest.approx(3.0)
    assert count == 2


# --------------------------------------------------------------------------- #
# Byte-identical re-run + atomic write.
# --------------------------------------------------------------------------- #

def _run_cli(args, cwd=None):
    return subprocess.run(
        [sys.executable, _HARNESS_PY] + args,
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def _scores_dir(tmp_path):
    """A dedicated manifests dir, separate from where reports land, so a written
    report is never re-globbed as a manifest on the next run."""
    d = tmp_path / "scores"
    d.mkdir()
    return str(d)


def test_report_byte_identical_on_rerun(tmp_path):
    scores = _scores_dir(tmp_path)
    _write(scores, "ref.json", _good_ref())
    _write(scores, "bad.json", _bad_case())
    out1 = os.path.join(str(tmp_path), "report1.md")
    out2 = os.path.join(str(tmp_path), "report2.md")
    r1 = _run_cli(["--scores-dir", scores, "--out", out1])
    r2 = _run_cli(["--scores-dir", scores, "--out", out2])
    assert r1.returncode == 0 and r2.returncode == 0
    with open(out1, "rb") as fh:
        bytes1 = fh.read()
    with open(out2, "rb") as fh:
        bytes2 = fh.read()
    assert bytes1 == bytes2
    # No BOM, LF newlines (deterministic-output fence).
    assert not bytes1.startswith(b"\xef\xbb\xbf")
    assert b"\r\n" not in bytes1


def test_json_format_byte_identical(tmp_path):
    scores = _scores_dir(tmp_path)
    _write(scores, "ref.json", _good_ref())
    _write(scores, "bad.json", _bad_case())
    out1 = os.path.join(str(tmp_path), "r1.json")
    out2 = os.path.join(str(tmp_path), "r2.json")
    _run_cli(["--scores-dir", scores, "--format", "json", "--out", out1])
    _run_cli(["--scores-dir", scores, "--format", "json", "--out", out2])
    with open(out1, "rb") as fh:
        b1 = fh.read()
    with open(out2, "rb") as fh:
        b2 = fh.read()
    assert b1 == b2


def test_atomic_write_leaves_no_tmp(tmp_path):
    out = os.path.join(str(tmp_path), "report.md")
    h.write_atomic(out, "hello\n")
    assert os.path.exists(out)
    assert not os.path.exists(out + ".tmp")
    with open(out, "rb") as fh:
        assert fh.read() == b"hello\n"


def test_full_run_writes_nothing_when_calibration_fails(tmp_path):
    ref = _good_ref()
    ref["dimensions"]["all"]["after"] = 7.0  # out of tolerance
    _write(tmp_path, "ref.json", ref)
    _write(tmp_path, "bad.json", _bad_case())
    out = os.path.join(str(tmp_path), "report.md")
    result = _run_cli(["--scores-dir", str(tmp_path), "--out", out])
    assert result.returncode == 1
    assert not os.path.exists(out)


def test_check_flag_writes_nothing_and_exit_code(tmp_path):
    _write(tmp_path, "ref.json", _good_ref())
    _write(tmp_path, "bad.json", _bad_case())
    out = os.path.join(str(tmp_path), "report.md")
    ok = _run_cli(["--scores-dir", str(tmp_path), "--check", "--out", out])
    assert ok.returncode == 0
    assert not os.path.exists(out)


# --------------------------------------------------------------------------- #
# End-to-end against the shipped manifests: the calibration reference resolves to
# its declared target. Identity-agnostic — works against the private eval/scores
# reference or a public eval/fixtures reference, with no hardcoded case name.
# --------------------------------------------------------------------------- #

@pytest.mark.skipif(
    not os.path.isdir(_SHIPPED_SCORES), reason="no shipped manifests dir"
)
def test_shipped_reference_calibrates_to_its_declared_target():
    manifests = h.load_manifests(_SHIPPED_SCORES)
    ref = h.reference_manifest(manifests)
    assert ref is not None, "shipped manifests carry no calibration reference"
    after = h.weighted_total(ref["dimensions"], "after")
    assert abs(after - ref["calibration_target"]) <= h.CALIBRATION_TOLERANCE
    ok, _ = h.calibrate(manifests)
    assert ok
