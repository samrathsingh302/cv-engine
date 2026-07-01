"""Cross-cutting CLI-contract tests for both linters (schema §3).

The tuning-set 0-false-positive check (the ONE place tests read shipped outputs by
design), unknown-flag -> exit 2, usage-error -> exit 2, and the directory-recurse
+ exit-code mapping. Run via subprocess so the real process exit codes are
exercised, matching what CI asserts.

The PUBLIC tuning set is the fictional clean deliverables under
``eval/fixtures/lint/output/`` — they ship with the engine, so a fresh clone with
zero owner data passes these tests. The kit owner's own shipped deliverables under
``output/`` are an ADDITIONAL tuning check, discovered generically (no instance
name is hardcoded) and simply skipped in a public clone where ``output/`` is absent.
"""

import glob
import os

import pytest

from _runner import run_cli


# Public tuning set: fictional clean deliverables shipped in eval/fixtures.
TUNING = [
    "eval/fixtures/lint/output/cv_priya_sharma.md",
    "eval/fixtures/lint/output/priya_sharma_cover_letter.tex",
]


def _abs(repo_root, rels):
    return [os.path.join(repo_root, r) for r in rels]


def _private_deliverables(repo_root):
    """Every profile's shipped deliverables, discovered generically from the
    private ``users/*/output/`` trees (cv_*.md and *.tex). P6 multi-profile: owner
    data lives under ``users/<profile>/`` so the glob spans all profiles. No
    instance/company/person name is hardcoded, so nothing private leaks into this
    shipped test. Empty in a public clone (no ``users/`` profiles)."""
    base = os.path.join(repo_root, "users")
    if not os.path.isdir(base):
        return []
    found = sorted(
        glob.glob(os.path.join(base, "*", "output", "**", "cv_*.md"), recursive=True)
        + glob.glob(os.path.join(base, "*", "output", "**", "*.tex"), recursive=True)
    )
    return found


# --- Tuning set: 0 false positives (guards-ship-with-tests-and-tune-on-real-hits)
def test_fingerprint_clean_on_tuning_set(fp_script, repo_root):
    paths = _abs(repo_root, TUNING)
    for p in paths:
        assert os.path.exists(p), p
    code, out = run_cli(fp_script, [*paths, "--format", "json"])
    assert code == 0, out.decode("utf-8", "replace")


def test_provenance_clean_on_tuning_set(pv_script, repo_root):
    paths = _abs(repo_root, TUNING)
    code, out = run_cli(pv_script, [*paths, "--format", "json", "--today", "2026-06"])
    assert code == 0, out.decode("utf-8", "replace")


# --- Private instance only: the owner's shipped deliverables stay 0-FP ---------
def test_fingerprint_clean_on_private_deliverables(fp_script, repo_root):
    paths = _private_deliverables(repo_root)
    if not paths:
        pytest.skip("no private output/ deliverables (public clone)")
    code, out = run_cli(fp_script, [*paths, "--format", "json"])
    assert code == 0, out.decode("utf-8", "replace")


def test_provenance_clean_on_private_deliverables(pv_script, repo_root):
    paths = _private_deliverables(repo_root)
    if not paths:
        pytest.skip("no private output/ deliverables (public clone)")
    code, out = run_cli(pv_script, [*paths, "--format", "json", "--today", "2026-06"])
    assert code == 0, out.decode("utf-8", "replace")


# --- Unknown flag -> exit 2 (never ignored) --------------------------------
@pytest.mark.parametrize("script_fixture", ["fp_script", "pv_script"])
def test_unknown_flag_exit2(request, script_fixture, repo_root):
    script = request.getfixturevalue(script_fixture)
    target = os.path.join(repo_root, TUNING[0])
    code, _ = run_cli(script, [target, "--definitely-not-a-flag"])
    assert code == 2


@pytest.mark.parametrize("script_fixture", ["fp_script", "pv_script"])
def test_bad_format_value_exit2(request, script_fixture, repo_root):
    script = request.getfixturevalue(script_fixture)
    target = os.path.join(repo_root, TUNING[0])
    code, _ = run_cli(script, [target, "--format", "yaml"])
    assert code == 2


@pytest.mark.parametrize("script_fixture", ["fp_script", "pv_script"])
def test_no_paths_exit2(request, script_fixture):
    script = request.getfixturevalue(script_fixture)
    code, _ = run_cli(script, [])
    assert code == 2


# --- Clean input -> exit 0 -------------------------------------------------
@pytest.mark.parametrize("script_fixture", ["fp_script", "pv_script"])
def test_clean_file_exit0(request, script_fixture, writer):
    script = request.getfixturevalue(script_fixture)
    p = writer("output/cv_x.md", "- Built a tested system, cutting latency by 30%.\n")
    extra = ["--today", "2026-06"] if script_fixture == "pv_script" else []
    code, _ = run_cli(script, [p, *extra])
    assert code == 0


# --- Directory recursion over *.md/*.tex -----------------------------------
@pytest.mark.parametrize("script_fixture", ["fp_script", "pv_script"])
def test_output_is_lf_only_no_bom(request, script_fixture, repo_root):
    # Cross-platform determinism: output bytes use LF, never CRLF, and no BOM —
    # the laptop is Windows but CI is Linux; the bytes must match (schema §3).
    script = request.getfixturevalue(script_fixture)
    target = os.path.join(repo_root, TUNING[0])
    extra = ["--today", "2026-06"] if script_fixture == "pv_script" else []
    code, out = run_cli(script, [target, "--format", "json", *extra])
    assert b"\r\n" not in out
    assert not out.startswith(b"\xef\xbb\xbf")


@pytest.mark.parametrize("script_fixture", ["fp_script", "pv_script"])
def test_directory_recurses_md_tex(request, script_fixture, tmp_path, writer):
    script = request.getfixturevalue(script_fixture)
    # Two scannable files + one ignored extension.
    out = tmp_path / "output"
    out.mkdir()
    (out / "cv_a.md").write_bytes(b"- clean bullet ending on a result of 5%.\n")
    (out / "b.txt").write_bytes(b"- leverage this should be ignored (.txt).\n")
    extra = ["--today", "2026-06"] if script_fixture == "pv_script" else []
    code, out_bytes = run_cli(script, [str(tmp_path), "--format", "json", *extra])
    import json
    doc = json.loads(out_bytes)
    # Only the .md was scanned (the .txt is skipped by the recurse filter).
    assert doc["files_scanned"] == 1
