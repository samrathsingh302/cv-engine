"""Shared fail-closed file reader for the honesty tools (schema §3).

ONE definition of "read a deliverable as text", imported by the three honesty
readers — lint_fingerprint.py, lint_provenance.py, harvest_verify.py — so the
fail-closed contract cannot drift between them (it used to be copy-pasted three
ways, and a guard added to one was missed by the other two).

Contract (UTF-8, NO BOM, fail-closed on anything we cannot certify as text):
  - unreadable file           -> UnparseableFile("unreadable file: <ExcType>")
  - leading UTF-8 BOM         -> UnparseableFile("UTF-8 BOM present ...")
  - a NUL byte anywhere       -> UnparseableFile("contains NUL byte ...")   [*]
  - bytes that aren't UTF-8   -> UnparseableFile("undecodable bytes ...")

[*] The NUL guard is the one the three readers were missing (it already lived in
scripts/leak_audit.py). A BOM-LESS UTF-16/UTF-32 file is the decisive case: its
ASCII range is <char>\x00 pairs that DO decode as valid UTF-8, so the decode below
would NOT raise — but the honesty rules would then run over NUL-interleaved text and
silently miss the real content (a fail-OPEN). A NUL byte means "not UTF-8 text", so
we fail closed before the decode, same as a BOM or undecodable bytes. (UTF-16 WITH a
BOM already failed the decode; this also covers the BOM-less variant and any binary
that slips a text extension.)

Read-only, stdlib only. No timestamps, no network. Importing modules add their own
directory to sys.path so this resolves both as a standalone script run
(`python cv_builder/helpers/<reader>.py`) and when a reader is loaded by absolute
path via importlib (the test harness / an integrator) — helpers is deliberately not
a package.
"""
from __future__ import annotations


class UnparseableFile(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


def read_text_strict(abs_path):
    """Read a file as UTF-8 with NO BOM tolerance. Fail closed on any problem."""
    try:
        raw = open(abs_path, "rb").read()
    except OSError as e:
        raise UnparseableFile("unreadable file: %s" % e.__class__.__name__)
    if raw.startswith(b"\xef\xbb\xbf"):
        raise UnparseableFile("UTF-8 BOM present (must be UTF-8 no BOM)")
    if b"\x00" in raw:
        # Not UTF-8 text: a BOM-less UTF-16/UTF-32 file decodes cleanly here but hides
        # its content behind interleaved NUL bytes, so the honesty rules would fail
        # OPEN. Fail closed before the decode (same contract as the BOM/undecodable
        # branches) — we cannot honestly lint NUL-interleaved bytes.
        raise UnparseableFile("contains NUL byte (not UTF-8 text)")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise UnparseableFile("undecodable bytes (not valid UTF-8)")
    return text
