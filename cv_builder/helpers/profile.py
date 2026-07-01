#!/usr/bin/env python
"""
profile.py — multi-profile resolver (P6).

cv-editor keeps each person's owner data under ``users/<profile>/`` (config.md,
knowledge_base/, output/, JDs/, and the per-profile cv_builder/{experience,
bundles,support} subtrees). A skill resolves WHICH profile it is operating on
from, in order:

  1. an explicit ``--profile <name>`` argument, else
  2. the one-line pointer file ``users/.active`` — the SINGLE place a profile name
     is recorded. The private repo ships ``users/.active`` containing the owner's
     profile name; this engine module carries NO owner name (it stays public-clean),
     so when the pointer is missing/empty it falls back to the generic
     ``DEFAULT_PROFILE`` below, never a person's name.

Fail-closed: if the resolved profile directory does not exist, raise — NEVER
silently fall back to another profile (a fence-3 honesty regression: writing one
person's data into another's CV). Profile names may not contain a path separator
or ``..`` (no traversal / no absolute-path escape).

stdlib only; offline; no side effects (read-only).
"""
from __future__ import annotations

import os

ACTIVE_POINTER = "users/.active"
# Generic, PII-free fallback used ONLY when users/.active is absent/empty. The
# real owner profile name lives in the (private) users/.active pointer, so this
# engine module ships publicly without carrying anyone's name.
DEFAULT_PROFILE = "default"
USERS_DIR = "users"


class ProfileError(Exception):
    """A profile could not be resolved (missing dir, or an unsafe name)."""


def _valid_name(name: str) -> bool:
    """A profile name is a single safe path segment (no separators, no traversal).

    PURE — no disk access (deliberately: a bad name is rejected before any disk
    touch, so there is no TOCTOU window). The exact-CASE existence rule lives at
    the disk-check seam in resolve_profile; this is the static, on-the-string gate.
    """
    if not name or name in (".", ".."):
        return False
    if "/" in name or "\\" in name or os.sep in name or (os.altsep and os.altsep in name):
        return False
    if name != name.strip():
        # Leading/trailing whitespace ("alice ", " alice", "alice\n"): a
        # Windows path quirk that can alias to the stripped name — reject it.
        return False
    if name.endswith("."):
        # A trailing dot ("alice.") is stripped by the Win32 path layer, so it
        # would alias to "alice" — reject it. (Leading "." handled below.)
        return False
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in name):
        # Control chars (C0 + DEL) never belong in a profile dir name; an interior
        # one (e.g. "sam\x00rath") survives strip() above, so scan the whole name.
        return False
    if name.startswith("."):
        # `.active` and other dotfiles are pointers/metadata, never a profile dir.
        return False
    return True


def active_profile(repo_root: str) -> str:
    """The active profile name from ``users/.active`` (stripped, first line).

    Missing pointer => the generic ``DEFAULT_PROFILE``. A pointer present but
    empty/whitespace also falls back to the default. The named profile's
    existence is NOT checked here — that is resolve_profile's fail-closed job.
    """
    pointer = os.path.join(repo_root, *ACTIVE_POINTER.split("/"))
    try:
        with open(pointer, encoding="utf-8") as fh:
            first = fh.read().splitlines()[0].strip() if fh else ""
    except (OSError, IndexError):
        return DEFAULT_PROFILE
    return first or DEFAULT_PROFILE


def profile_root(repo_root: str, name: str) -> str:
    """Absolute ``users/<name>/`` for a validated name (no existence check)."""
    if not _valid_name(name):
        raise ProfileError("invalid profile name %r (no separators / '..' allowed)" % name)
    return os.path.join(repo_root, USERS_DIR, name)


def resolve_profile(arg: str | None, repo_root: str) -> str:
    """Resolve the active profile to its absolute ``users/<name>/`` root.

    `arg` is the optional ``--profile`` value; when None the active pointer
    (``users/.active``, else the generic DEFAULT_PROFILE) is used. Fail-closed: a
    missing profile directory raises ProfileError — never a silent fallback.
    """
    name = arg.strip() if arg is not None else active_profile(repo_root)
    root = profile_root(repo_root, name)
    if not os.path.isdir(root):
        raise ProfileError(
            "profile %r not found at %s (no fallback — create it or fix users/.active)"
            % (name, os.path.relpath(root, repo_root).replace("\\", "/"))
        )
    # EXACT-CASE gate (the only new disk read, here where isdir already touched
    # disk — _valid_name stays pure). On a case-INSENSITIVE FS, isdir(users/ALICE)
    # is True against the real users/alice/ dir, so without this check one
    # person's data would load under a different-case name (a silent alias / fence-3
    # honesty regression). Require the resolved name to appear with EXACTLY that case
    # among the actual directory entries; otherwise fail closed — never alias.
    users_dir = os.path.join(repo_root, USERS_DIR)
    if name not in os.listdir(users_dir):
        raise ProfileError(
            "profile %r not found with exact case in %s/ (no case-alias fallback — "
            "use the directory's exact name or fix users/.active)" % (name, USERS_DIR)
        )
    return root
