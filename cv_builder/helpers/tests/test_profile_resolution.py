# -*- coding: utf-8 -*-
"""Tests for cv_builder/helpers/profile.py — the P6 multi-profile resolver.

Pins the done-gate's no-bleed property: a resolved profile path NEVER points at
another profile's data, and the honesty linters still classify a profile-prefixed
path (users/<name>/...) by its recognised tail segment with NO linter change.

This test ships in the public engine (cv_builder/helpers/tests/), so it carries
NO owner name — it uses generic profile names ('alice', 'demo') and the module's
own generic DEFAULT_PROFILE constant. The real owner profile name lives only in
the private users/.active pointer, never in shipped code (leak-audit clean).

stdlib + pytest only; offline. Modules are loaded by file location (the helpers/
tree uses this idiom — no package __init__ needed).
"""

import importlib.util
import io
import json
import os
import sys
from contextlib import redirect_stdout

import pytest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_HELPERS_DIR = os.path.dirname(_TESTS_DIR)


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_HELPERS_DIR, filename))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


profile = _load("profile_undertest", "profile.py")
lint_provenance = _load("lint_provenance_undertest", "lint_provenance.py")
lint_fingerprint = _load("lint_fingerprint_undertest", "lint_fingerprint.py")
harvest_verify = _load("harvest_verify_undertest_pr", "harvest_verify.py")

OWNER = profile.DEFAULT_PROFILE  # the active profile a missing pointer falls back to


def _write(root, rel, text="x"):
    path = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def _fake_repo(tmp_path, active=None):
    """Minimal two-profile repo: an OWNER profile + a DEMO profile.

    ``active`` defaults to the OWNER (the resolver's generic DEFAULT_PROFILE) so
    no person's name is ever written. Pass a name to set users/.active.
    """
    root = str(tmp_path)
    name = active if active is not None else OWNER
    _write(root, "users/.active", name + "\n")
    _write(root, "users/%s/config.md" % OWNER, "OWNER")
    _write(root, "users/demo/config.md", "DEMO")
    return root


# --- (a) default resolution -------------------------------------------------
def test_default_resolution_returns_owner_never_demo(tmp_path):
    root = _fake_repo(tmp_path, active=OWNER)
    resolved = profile.resolve_profile(None, root)
    assert resolved == os.path.join(root, "users", OWNER)
    assert resolved != os.path.join(root, "users", "demo")


def test_missing_pointer_defaults_to_generic_owner(tmp_path):
    root = str(tmp_path)
    _write(root, "users/%s/config.md" % OWNER, "OWNER")  # no users/.active written
    assert profile.active_profile(root) == OWNER
    assert profile.resolve_profile(None, root) == os.path.join(root, "users", OWNER)


# --- (b) --profile override -------------------------------------------------
def test_profile_arg_overrides_active_pointer(tmp_path):
    root = _fake_repo(tmp_path, active=OWNER)  # .active says the owner
    resolved = profile.resolve_profile("demo", root)  # arg wins
    assert resolved == os.path.join(root, "users", "demo")


# --- (c) missing profile fails closed (no fallback) -------------------------
def test_missing_profile_raises_no_fallback(tmp_path):
    root = _fake_repo(tmp_path, active="ghost")  # users/ghost/ does not exist
    with pytest.raises(profile.ProfileError):
        profile.resolve_profile(None, root)
    with pytest.raises(profile.ProfileError):
        profile.resolve_profile("ghost", root)


# --- (d) NO BLEED + no traversal -------------------------------------------
def test_no_bleed_each_profile_reads_only_its_own_config(tmp_path):
    root = _fake_repo(tmp_path)
    owner = profile.resolve_profile(OWNER, root)
    demo = profile.resolve_profile("demo", root)

    # Every resolved path is confined under its own users/<name>/.
    assert owner.replace("\\", "/").endswith("users/%s" % OWNER)
    assert demo.replace("\\", "/").endswith("users/demo")

    with open(os.path.join(demo, "config.md"), encoding="utf-8") as fh:
        assert fh.read() == "DEMO"  # demo yields DEMO, never OWNER
    with open(os.path.join(owner, "config.md"), encoding="utf-8") as fh:
        assert fh.read() == "OWNER"  # owner yields OWNER, never DEMO


def test_traversal_and_absolute_names_rejected(tmp_path):
    root = _fake_repo(tmp_path)
    for bad in ("..", "../demo", "demo/../x", "/etc", "a\\b", ".active", "."):
        with pytest.raises(profile.ProfileError):
            profile.resolve_profile(bad, root)


# --- (d2) B-F2: trailing dot/space/control names rejected (pure, no disk) ----
def test_valid_name_rejects_whitespace_dot_and_control():
    # _valid_name is the PURE on-the-string gate (no disk touch). These are all
    # Windows path quirks ("alice." / "alice " strip to "alice" => alias) or
    # control chars that never belong in a profile dir name.
    assert profile._valid_name("alice")          # a normal name still passes
    for bad in ("alice.",                          # trailing dot -> Win alias
                "alice ", " alice", "alice\t",     # leading/trailing whitespace
                "alice\n", "\talice",              # ... incl. tab / newline
                "al\x00ice",                       # interior NUL (survives strip)
                "ali\x1fce", "ali\x7fce"):         # interior C0 / DEL control
        assert not profile._valid_name(bad), bad
    # And profile_root surfaces the same rejection as a ProfileError (no disk).
    for bad in ("alice.", "alice ", "al\x00ice"):
        with pytest.raises(profile.ProfileError):
            profile.profile_root("/some/repo", bad)


def test_resolve_profile_rejects_trailing_dot_and_control(tmp_path):
    # End-to-end: a trailing-dot / interior-control arg never resolves a real dir,
    # even though on a case-insensitive FS os.path.isdir(users/alice.) is True.
    # (Leading/trailing WHITESPACE on the --profile arg is normalised by the
    # existing arg.strip() in resolve_profile, so " alice"/"alice " legitimately
    # resolve to "alice" — not an alias; _valid_name still rejects them directly,
    # which the pure test above pins. The trailing DOT is NOT whitespace, so it
    # survives the strip and must be rejected by validation — the real new catch.)
    root = _fake_repo(tmp_path)
    _write(root, "users/alice/config.md", "ALICE")
    for bad in ("alice.", "al\x00ice", "ali\x7fce"):
        with pytest.raises(profile.ProfileError):
            profile.resolve_profile(bad, root)


# --- (d3) B-F2: EXACT-CASE existence — no silent case-alias --------------------
def test_resolve_profile_rejects_case_variant_no_silent_alias(tmp_path):
    # The headline B-F2 defect. Only users/alice/ exists. A different-case arg
    # ("ALICE"/"Alice") must FAIL CLOSED — never silently alias onto users/alice/.
    root = str(tmp_path)
    _write(root, "users/.active", "alice\n")
    _write(root, "users/alice/config.md", "ALICE")
    users_dir = os.path.join(root, "users")

    # FAIL-BEFORE PROOF (this assertion captures the pre-fix bug): on a
    # case-INSENSITIVE FS os.path.isdir(users/ALICE) is True against users/alice/,
    # so the pre-fix resolve_profile (which only did the isdir check) WOULD have
    # resolved "ALICE" onto another-case dir. We make that visible, then assert the
    # post-fix code rejects it. On a case-SENSITIVE FS isdir is False, so the case
    # variant never existed there in the first place — either way it must not alias.
    isdir_case_variant = os.path.isdir(os.path.join(users_dir, "ALICE"))
    exact_case_listing = os.listdir(users_dir)
    assert "alice" in exact_case_listing          # the real dir, exact case
    assert "ALICE" not in exact_case_listing       # the variant is NOT a real entry
    if isdir_case_variant:
        # Case-insensitive FS (e.g. Windows): isdir lied; the exact-case listdir
        # gate is the ONLY thing that catches the alias. Prove it would have aliased
        # under the old (isdir-only) rule by reconstructing that rule here.
        old_rule_would_resolve = os.path.isdir(os.path.join(users_dir, "ALICE"))
        assert old_rule_would_resolve, "pre-fix isdir-only rule resolved the alias"

    # POST-FIX: the case variant fails closed (raises), never silently aliases.
    for variant in ("ALICE", "Alice"):
        with pytest.raises(profile.ProfileError):
            profile.resolve_profile(variant, root)
    # The exact-case name still resolves to its own dir (no over-rejection).
    assert profile.resolve_profile("alice", root) == os.path.join(root, "users", "alice")


# --- (e) linter classification survives the users/<name>/ prefix ------------
def test_provenance_classify_survives_profile_prefix():
    # KB path keeps its KB class; output deliverable keeps its DELIVER class —
    # the linter keys on the first recognised segment (cv_builder / output), so
    # the users/<name>/ prefix is transparent (NO linter change for P6).
    assert lint_provenance.classify("users/alice/cv_builder/experience/x.md") == "KB"
    assert lint_provenance.classify("users/demo/output/Foo/cv_x.md") == "DELIVER"
    # and the bare (unprefixed) forms classify identically — proving the prefix
    # is genuinely transparent, not accidentally re-routed.
    assert lint_provenance.classify("cv_builder/experience/x.md") == "KB"
    assert lint_provenance.classify("output/Foo/cv_x.md") == "DELIVER"


def test_fingerprint_exemption_matches_kb_under_profile_prefix():
    # The KB path under users/<name>/ is FP-exempt (it quotes banned words as
    # rules/examples) — the exemption must still fire through the prefix.
    assert lint_fingerprint.is_fp_exempt("users/alice/cv_builder/experience/x.md")
    assert lint_fingerprint.is_fp_exempt("users/demo/knowledge_base/extractions/e.md")
    # a deliverable under the prefix is NOT exempt (it is scanned), same as bare.
    assert not lint_fingerprint.is_fp_exempt("users/demo/output/Foo/cv_x.md")


# --- (f) harvester default resolves the active profile ----------------------
def _run_harvest_json(monkeypatch, repo_root):
    """Run harvest_verify with NO path args against a fake repo_root."""
    monkeypatch.setattr(harvest_verify, "repo_root", lambda: repo_root)
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = harvest_verify.run(["--format", "json"])
    return code, json.loads(buf.getvalue())


def test_harvester_default_resolves_active_profile(tmp_path, monkeypatch):
    root = _fake_repo(tmp_path, active="demo")
    # Plant a [VERIFY] sentinel ONLY in the demo profile's experience KB.
    _write(root, "users/demo/cv_builder/experience/work.md",
           "# Fictional demo\nA claim recorded [VERIFY: demo fact].\n")
    _write(root, "users/%s/cv_builder/experience/work.md" % OWNER,
           "# Owner\nAll confirmed.\n")

    code, doc = _run_harvest_json(monkeypatch, root)
    assert code == 0, doc
    # .active=demo => the demo sentinel IS found; the owner KB is NOT swept.
    assert "demo fact" in json.dumps(doc)

    # Flip the active pointer to the owner: the demo sentinel must NO LONGER be
    # found (the harvester swept the owner KB, which is clean).
    _write(root, "users/.active", OWNER + "\n")
    code2, doc2 = _run_harvest_json(monkeypatch, root)
    assert code2 == 0, doc2
    assert "demo fact" not in json.dumps(doc2)
