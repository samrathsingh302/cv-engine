#!/usr/bin/env python
r"""
harvest_verify.py — KB unconfirmed-sentinel harvester (P5 item 2).

Sweeps the given knowledge-base paths for the FROZEN sentinel semantics defined
in `cv_builder/reference/claims_schema.md` §2 — the SAME exact, case-sensitive
patterns the linters use, never an ad-hoc regex — plus the pipeline's
unconfirmed status marker (schema §1 PV-002 + `experience_pipeline.md` gating),
and emits ONE batched, de-duplicated owner question list (K0 discipline) with the
derived-files re-sweep list per answer.

SENTINELS SWEPT (claims_schema.md §2 table — patterns copied verbatim):
  [VERIFY]            \[VERIFY(?::[^\]\n]*)?\]            fact recorded but
                      unconfirmed; owner must confirm before it ships.
  [ASK: ...]          \[ASK:[^\]\n]+\]                    fact missing; a question
                      has been issued; the slot must be filled before it ships.
  in-progress label   \(in progress, expected (0[1-9]|1[0-2])/20[0-9]{2}\)
                      planned/in-progress work — confirm it has genuinely started
                      (and the date holds) before promotion.
And, beyond the §2 table, the pipeline's unconfirmed STATUS marker (schema §1
PV-002 ties in-progress claims to `experience_pipeline.md`, whose STATUS KEY uses
`planned`/`planned — confirm` for not-yet-confirmed items):
  pipeline-status     ^\**Status:\**\s*planned\b ...      a `**Status:** planned`
                      / `planned — confirm` line — the item may NOT appear on any
                      CV until the owner confirms it genuinely started.
These are unconfirmed-fact sentinels. `[ASK: ...]` is included because, like
[VERIFY], it is a slot the owner must resolve before the claim ships; the batched
list is the single home for both ([one-comparison-mode-per-sentinel]).

This is a GENERIC engine tool: it ships in the public engine and contains ZERO
owner data. KB paths are arguments; when run with none, it defaults to the ACTIVE
profile's KB roots — users/<active>/{experience, extractions, bundles, support}
where <active> comes from users/.active (else the generic default). Those paths
simply do not exist in a public clone — an empty sweep, never an error. Output
carries no owner name.

Read-only by default (DRY-RUN): prints the batched questions + re-sweep lists,
writes nothing. `--apply` writes the batched question list to a single Markdown
file (default `<first-kb-root>/_verify_questions.md`, or `--out <path>`) —
conservative and idempotent (byte-identical content for the same KB state).

Binds the frozen CLI contract in `claims_schema.md` §3/§3.1/§3.2:
  - stdlib only; offline; UTF-8 (no BOM); repo-relative paths; no timestamps.
  - Deterministic: same input bytes -> byte-identical output.
  - Fail-closed (exit 2) on any input that cannot be parsed (unreadable file,
    BOM/undecodable bytes). A file the tool cannot read FAILS the run.
  - Read-only tool is dry-run by default with an explicit `--apply`
    ([ops-tools-dry-run-by-default]).

USAGE:
  python cv_builder/helpers/harvest_verify.py [paths...] [--format text|json]
                                              [--apply] [--out <file.md>]
  paths     KB files or directories (dirs recurse over *.md); default = the ACTIVE
            profile's KB roots under users/<active>/ (experience/, extractions/,
            bundles/, support/), resolved from users/.active.
  --format  text (default) | json (schema §3.1-style on stdout).
  --apply   write the batched question list to --out (default
            <first-existing-kb-root>/_verify_questions.md). Idempotent.
  --out     destination for --apply (repo-relative or absolute).

EXIT CODES (schema §3):
  0  swept clean OR sentinels found and reported (a harvest is informational, not
     a failure — it reports work for the owner, it does not gate a build).
  2  usage error OR any input that cannot be parsed (fail-closed; never skipped).
"""

import argparse
import json
import os
import re
import sys

# Shared fail-closed reader (UTF-8 no-BOM, NUL guard). helpers is deliberately not a
# package, so put this file's own dir on sys.path: works both as a standalone script
# (dir is already sys.path[0]) and when loaded by absolute path via importlib (the
# test harness), where the sibling import would otherwise not resolve.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _shared_io import UnparseableFile, read_text_strict  # noqa: E402

SCHEMA_VERSION = 1
TOOL = "harvest_verify"

# --- Frozen sentinel patterns (claims_schema.md §2 — EXACT, case-sensitive) --
# Copied verbatim from the schema / the linters; never paraphrased, never
# case-insensitive. A near-miss is the linter's PV-005 concern, not the
# harvester's — the harvester collects only well-formed unconfirmed sentinels.
VERIFY_RE = re.compile(r"\[VERIFY(?::[^\]\n]*)?\]")
ASK_RE = re.compile(r"\[ASK:[^\]\n]+\]")
INPROGRESS_RE = re.compile(r"\(in progress, expected (0[1-9]|1[0-2])/20[0-9]{2}\)")
# Pipeline unconfirmed status (schema §1 PV-002 + experience_pipeline.md STATUS
# KEY). A `**Status:** planned` / `planned — confirm` line: the item must be
# owner-confirmed before any CV use. Bold markers optional; leading whitespace
# tolerated; matched at the start of a line only (a status field, not prose).
PIPELINE_STATUS_RE = re.compile(r"^\s*\**Status:\**\s*planned\b", re.IGNORECASE)

# Sentinel kinds, in a fixed display order (deterministic output).
KIND_VERIFY = "verify"
KIND_ASK = "ask"
KIND_INPROGRESS = "in-progress"
KIND_PIPELINE = "pipeline-status"
KIND_ORDER = (KIND_VERIFY, KIND_ASK, KIND_INPROGRESS, KIND_PIPELINE)
KIND_LABEL = {
    KIND_VERIFY: "[VERIFY]",
    KIND_ASK: "[ASK: ...]",
    KIND_INPROGRESS: "in-progress label",
    KIND_PIPELINE: "pipeline status 'planned'",
}

# --- Default KB roots are PROFILE-AWARE (P6 multi-profile). Each profile keeps
# its KB under users/<profile>/ (the segment names are preserved so the sentinel
# patterns + the logical_repo_path classification are unchanged). The active
# profile is resolved from users/.active (else the generic DEFAULT_PROFILE) — no
# owner name appears in this engine module. Arguments override; a missing profile
# dir is an empty sweep (public clone), never an error.
#
# The per-profile KB tail segments (cv_builder/experience, knowledge_base/
# extractions, cv_builder/bundles, cv_builder/support) are unchanged; only the
# users/<profile>/ prefix is added.
_PROFILE_KB_TAILS = (
    "cv_builder/experience",
    "knowledge_base/extractions",
    "cv_builder/bundles",
    "cv_builder/support",
)


def default_kb_roots(root):
    """Resolve the active profile and return its KB roots (repo-relative).

    Resolution mirrors profile.py: users/.active (stripped first line) else the
    generic DEFAULT_PROFILE. The profile dir need not exist — a missing default
    root is simply skipped by gather_paths (an empty sweep in a public clone)."""
    name = _active_profile_name(root)
    return tuple("users/%s/%s" % (name, tail) for tail in _PROFILE_KB_TAILS)


# Generic, PII-free fallback (matches profile.DEFAULT_PROFILE). The real owner
# profile name lives only in the private users/.active pointer.
_DEFAULT_PROFILE = "default"


def _valid_profile_name(name):
    """A profile name must be a single safe path segment — no separator, no
    traversal (``..``), no dotfile, no leading/trailing whitespace, no trailing
    ``.``, no control chars. Mirrors profile.py:_valid_name IN LOCKSTEP (this pair
    drifted once before — keep them identical and verified by test) so a poisoned
    or corrupt users/.active (e.g. ``../secret``, ``alice.``, ``alice ``) can
    NEVER make default_kb_roots compose a path that escapes / aliases the
    users/<profile>/ tree (an honesty regression: the harvester sweeping
    out-of-profile content). Kept inline rather than importing profile.py — this
    engine module avoids cross-imports and the stdlib already owns the name
    ``profile``. (The EXACT-CASE existence rule is profile.py's job; harvest already
    fails safe to an empty sweep, so an unmatched case here is harmless.)"""
    if not name or name in (".", ".."):
        return False
    if "/" in name or "\\" in name or os.sep in name or (os.altsep and os.altsep in name):
        return False
    if name != name.strip():            # leading/trailing whitespace -> Win alias
        return False
    if name.endswith("."):              # trailing dot -> stripped by Win32 -> alias
        return False
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in name):  # C0 + DEL controls
        return False
    if name.startswith("."):
        return False
    return True


def _active_profile_name(root):
    """First line of users/.active (stripped), else the generic default.

    Fail-safe: a missing/empty pointer OR an unsafe name (separator / traversal /
    dotfile) both fall back to the PII-free default, so a corrupt or malicious
    .active resolves to an empty sweep — never an out-of-tree path. (A missing
    profile dir is an empty sweep by design; see the module docstring.)"""
    pointer = os.path.join(root, "users", ".active")
    try:
        with open(pointer, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        name = lines[0].strip() if lines else ""
    except OSError:
        return _DEFAULT_PROFILE
    return name if _valid_profile_name(name) else _DEFAULT_PROFILE

DEFAULT_OUT_BASENAME = "_verify_questions.md"

# Recognised root segments so a path is keyed identically whether it is given
# in-repo or as an out-of-tree fixture mirroring the structure (mirrors the
# linters' logical_repo_path). Unrecognised paths keep their basename-bearing tail.
_ROOT_SEGMENTS = ("output", "cv_builder", "knowledge_base", "docs")


# --- Fail-closed file reading (schema §3) ----------------------------------
# UnparseableFile + read_text_strict are the SHARED fail-closed reader, imported at
# the top of this file from _shared_io (one definition across the three honesty
# readers; includes the NUL-byte / BOM-less-UTF-16 guard).


# --- Path helpers (repo-relative; no absolute paths in output) -------------
def repo_root():
    return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def to_rel(abs_path, root):
    return os.path.relpath(abs_path, root).replace("\\", "/")


def logical_repo_path(rel_path):
    """Path starting at the first recognised root segment (mirrors the linters)."""
    p = rel_path.replace("\\", "/")
    segs = [s for s in p.split("/") if s not in ("", ".", "..")]
    for i, s in enumerate(segs):
        if s in _ROOT_SEGMENTS:
            return "/".join(segs[i:])
    return "/".join(segs)


def gather_paths(inputs, root):
    """Resolve files/dirs to a sorted, de-duplicated list of (abs, rel) *.md pairs.

    Directories recurse over *.md only (the KB is markdown; .tex are deliverables,
    out of scope for a KB harvest). .git is skipped. Order is deterministic.
    """
    out = []
    seen = set()
    for item in inputs:
        abs_item = item if os.path.isabs(item) else os.path.join(root, item)
        abs_item = os.path.normpath(abs_item)
        if os.path.isdir(abs_item):
            for dirpath, dirnames, filenames in os.walk(abs_item):
                dirnames.sort()
                if ".git" in dirpath.replace("\\", "/").split("/"):
                    continue
                for fn in sorted(filenames):
                    # The harvester's own --apply output is a generated artefact,
                    # not KB content — never sweep it (else a second --apply run
                    # re-harvests the question list and is no longer idempotent).
                    if fn.endswith(".md") and fn != DEFAULT_OUT_BASENAME:
                        ap = os.path.normpath(os.path.join(dirpath, fn))
                        if ap not in seen:
                            seen.add(ap)
                            out.append((ap, to_rel(ap, root)))
        elif os.path.isfile(abs_item):
            if abs_item not in seen:
                seen.add(abs_item)
                out.append((abs_item, to_rel(abs_item, root)))
        # A non-existent default root is simply skipped (public clone has none);
        # an explicitly-named non-existent path is a usage error (caught upstream).
    out.sort(key=lambda t: t[1])
    return out


# --- The sweep -------------------------------------------------------------
def question_text(kind, body):
    """Normalised question for a sentinel hit — the dedup key's human half.

    A [VERIFY: x] / [ASK: y] carries its own body, which IS the question; a bare
    [VERIFY] / in-progress / pipeline-status carries a generic prompt keyed on the
    source line so distinct items stay distinct without inventing wording.
    """
    if kind == KIND_VERIFY:
        return ("Confirm: %s" % body) if body else "Confirm this unverified fact ([VERIFY])."
    if kind == KIND_ASK:
        return body  # the [ASK: ...] body is literally the question.
    if kind == KIND_INPROGRESS:
        return ("Confirm this work has genuinely started and the date holds: %s"
                % body)
    if kind == KIND_PIPELINE:
        return ("Confirm pipeline item status (planned -> in progress / done?): %s"
                % body)
    return body


def _extract_body(kind, line, span):
    """The human-meaningful body for a hit, used to form the question + dedup key."""
    if kind == KIND_VERIFY:
        token = line[span[0]:span[1]]
        # [VERIFY: body] -> body ; bare [VERIFY] -> "".
        inner = token[len("[VERIFY"):-1]
        if inner.startswith(":"):
            return inner[1:].strip()
        return ""
    if kind == KIND_ASK:
        token = line[span[0]:span[1]]
        return token[len("[ASK:"):-1].strip()
    # in-progress / pipeline-status: the surrounding line (trimmed) carries the
    # claim being confirmed — that is the meaningful body.
    return line.strip()


def sweep_file(rel_path, text):
    """Return raw hits for one file: list of dicts {kind, line, body, question}."""
    hits = []
    lines = text.split("\n")
    for idx, line in enumerate(lines, 1):
        for m in VERIFY_RE.finditer(line):
            body = _extract_body(KIND_VERIFY, line, m.span())
            hits.append({"kind": KIND_VERIFY, "path": rel_path, "line": idx,
                         "body": body, "question": question_text(KIND_VERIFY, body)})
        for m in ASK_RE.finditer(line):
            body = _extract_body(KIND_ASK, line, m.span())
            hits.append({"kind": KIND_ASK, "path": rel_path, "line": idx,
                         "body": body, "question": question_text(KIND_ASK, body)})
        for m in INPROGRESS_RE.finditer(line):
            body = _extract_body(KIND_INPROGRESS, line, m.span())
            hits.append({"kind": KIND_INPROGRESS, "path": rel_path, "line": idx,
                         "body": body, "question": question_text(KIND_INPROGRESS, body)})
        if PIPELINE_STATUS_RE.search(line):
            body = _extract_body(KIND_PIPELINE, line, (0, len(line)))
            hits.append({"kind": KIND_PIPELINE, "path": rel_path, "line": idx,
                         "body": body, "question": question_text(KIND_PIPELINE, body)})
    return hits


# --- Derived-files re-sweep (from real references, not a hardcoded map) ----
def build_index_from_texts(texts):
    """texts: {rel_path: text}. Returns {rel_path: [referencing_rel_paths]}.

    For each file, find which OTHER files mention its basename. Self-references are
    excluded. Output lists are sorted for determinism.
    """
    by_basename = {}
    for rel in texts:
        base = rel.rsplit("/", 1)[-1]
        by_basename.setdefault(base, []).append(rel)

    index = {rel: set() for rel in texts}
    for rel, text in texts.items():
        for base, owners in by_basename.items():
            # A whole-token match on the basename (so `pipeline.md` does not match
            # inside `experience_pipeline.md`); the `.md` anchor keeps it tight.
            if re.search(r"(?<![\w./-])" + re.escape(base), text):
                for owner in owners:
                    if owner != rel:
                        index[owner].add(rel)
    return {rel: sorted(refs) for rel, refs in index.items()}


# --- Batching + dedup (K0 discipline) --------------------------------------
def batch_questions(all_hits, ref_index):
    """Group hits into ONE de-duplicated question list.

    Dedup key: (kind, normalised question). Near-identical asks across files
    collapse into one entry carrying every source `file:line` location and the
    union of derived-files re-sweep targets. Output is fully sorted for
    determinism.
    """
    groups = {}
    for h in all_hits:
        key = (h["kind"], _norm_question(h["question"]))
        g = groups.get(key)
        if g is None:
            g = {"kind": h["kind"], "question": h["question"],
                 "locations": [], "resweep": set()}
            groups[key] = g
        g["locations"].append({"path": h["path"], "line": h["line"]})
        for ref in ref_index.get(h["path"], ()):  # files derived from this source
            g["resweep"].add(ref)

    out = []
    for g in groups.values():
        g["locations"].sort(key=lambda loc: (loc["path"], loc["line"]))
        g["resweep"] = sorted(g["resweep"])
        out.append(g)
    # Deterministic order: by kind (fixed order), then question, then first loc.
    out.sort(key=lambda g: (KIND_ORDER.index(g["kind"]), g["question"],
                            g["locations"][0]["path"], g["locations"][0]["line"]))
    return out


def _norm_question(q):
    """Collapse whitespace + lowercase so near-identical asks dedup (K0)."""
    return re.sub(r"\s+", " ", q).strip().lower()


# --- Output ----------------------------------------------------------------
def _loc_str(loc):
    return "%s:%d" % (loc["path"], loc["line"])


def render_markdown(batched):
    """The batched question list as Markdown (used for --apply and text format).

    No timestamps, no absolute paths — byte-identical for the same KB state.
    """
    lines = ["# Verify-harvest question list",
             "",
             "Batched, de-duplicated owner questions for unconfirmed KB sentinels "
             "(claims_schema.md §2). Resolve each, then re-check the listed "
             "derived files.",
             ""]
    if not batched:
        lines.append("_No unconfirmed sentinels found._")
        return "\n".join(lines) + "\n"
    n = 0
    for g in batched:
        n += 1
        lines.append("## Q%d (%s) — %s" % (n, KIND_LABEL[g["kind"]], g["question"]))
        lines.append("- locations: " + ", ".join(_loc_str(l) for l in g["locations"]))
        if g["resweep"]:
            lines.append("- re-sweep on answer: " + ", ".join(g["resweep"]))
        else:
            lines.append("- re-sweep on answer: (none — no derived files reference these sources)")
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def emit_text(files_scanned, batched, errors):
    out_lines = []
    for e in errors:
        out_lines.append("ERROR %s:%d %s" % (e["path"], e["line"], e["message"]))
    out_lines.append(render_markdown(batched).rstrip("\n"))
    total_locs = sum(len(g["locations"]) for g in batched)
    out_lines.append("scanned %d file(s): %d batched question(s) from %d sentinel "
                     "location(s), %d error(s)"
                     % (files_scanned, len(batched), total_locs, len(errors)))
    return "\n".join(out_lines)


def emit_json(files_scanned, batched, errors, exit_code):
    total_locs = sum(len(g["locations"]) for g in batched)
    doc = {
        "tool": TOOL,
        "schema_version": SCHEMA_VERSION,
        "files_scanned": files_scanned,
        "questions": [
            {"kind": g["kind"], "question": g["question"],
             "locations": g["locations"], "resweep": g["resweep"]}
            for g in batched
        ],
        "errors": errors,
        "summary": {
            "errors": len(errors),
            "questions": len(batched),
            "locations": total_locs,
            "exit_code": exit_code,
        },
    }
    return json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=2)


def _write_stdout(text):
    """UTF-8 + LF, bypassing platform CRLF translation (byte-identical on CI)."""
    data = text.encode("utf-8")
    buf = getattr(sys.stdout, "buffer", None)
    if buf is not None:
        buf.write(data)
        buf.flush()
    else:
        sys.stdout.write(text)


def _atomic_write(abs_path, text):
    """Write UTF-8 (no BOM), LF, via a temp file + replace — idempotent + atomic.

    Same content -> the file already matches, so a re-run leaves identical bytes
    (idempotent). The replace is atomic so a crash never leaves a half-written
    question list.
    """
    data = text.encode("utf-8")
    tmp = abs_path + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(data)
    os.replace(tmp, abs_path)


# --- Main ------------------------------------------------------------------
def run(argv):
    parser = argparse.ArgumentParser(
        prog="harvest_verify.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=True,
    )
    parser.add_argument("paths", nargs="*",
                        help="KB files or directories (dirs recurse *.md); "
                             "default = the active profile's KB roots under users/<active>/")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--apply", action="store_true",
                        help="write the batched question list to --out (idempotent)")
    parser.add_argument("--out", default=None,
                        help="destination for --apply (default "
                             "<first-existing-kb-root>/_verify_questions.md)")
    args = parser.parse_args(argv)

    root = repo_root()
    used_defaults = not args.paths
    inputs = list(args.paths) if args.paths else list(default_kb_roots(root))

    # An explicitly-named path that does not exist is a usage error (fail-closed,
    # exit 2); a missing DEFAULT root is fine (public clone simply has fewer roots).
    if not used_defaults:
        for item in inputs:
            abs_item = item if os.path.isabs(item) else os.path.join(root, item)
            if not os.path.exists(abs_item):
                sys.stderr.write("error: path does not exist: %s\n" % item)
                return 2

    targets = gather_paths(inputs, root)

    errors = []
    texts = {}
    files_scanned = 0
    for abs_path, rel_path in targets:
        try:
            text = read_text_strict(abs_path)
        except UnparseableFile as e:
            errors.append({"path": rel_path, "line": 0, "message": e.message})
            continue
        files_scanned += 1
        texts[rel_path] = text

    ref_index = build_index_from_texts(texts)

    all_hits = []
    for rel_path, text in texts.items():
        all_hits.extend(sweep_file(rel_path, text))

    batched = batch_questions(all_hits, ref_index)

    # Fail-closed: any unparseable input -> exit 2 (never silently skipped).
    exit_code = 2 if errors else 0

    if args.format == "json":
        out = emit_json(files_scanned, batched, errors, exit_code)
    else:
        out = emit_text(files_scanned, batched, errors)
    _write_stdout(out + "\n")

    # --apply writes ONLY on a clean parse (never persist a partial sweep).
    if args.apply and not errors:
        if args.out is not None:
            out_abs = args.out if os.path.isabs(args.out) else os.path.join(root, args.out)
        else:
            out_abs = _default_out_path(inputs, root)
        out_abs = os.path.normpath(out_abs)
        _atomic_write(out_abs, render_markdown(batched))

    return exit_code


def _default_out_path(inputs, root):
    """`<first existing KB root>/_verify_questions.md`. Falls back to the first
    named input's directory so --apply always has a home even off the defaults."""
    for item in inputs:
        abs_item = item if os.path.isabs(item) else os.path.join(root, item)
        if os.path.isdir(abs_item):
            return os.path.join(abs_item, DEFAULT_OUT_BASENAME)
    # No directory among the inputs (all files): write beside the first input.
    first = inputs[0]
    abs_first = first if os.path.isabs(first) else os.path.join(root, first)
    return os.path.join(os.path.dirname(abs_first), DEFAULT_OUT_BASENAME)


def main():
    try:
        code = run(sys.argv[1:])
    except SystemExit as e:
        raise SystemExit(2 if e.code not in (0, None) else e.code)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
