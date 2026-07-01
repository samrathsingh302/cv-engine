#!/usr/bin/env python
"""
lint_provenance.py — deterministic provenance / anti-fabrication checker (PV-xxx).

Turns CLAUDE.md's Anti-Fabrication + Generation rules and the frozen
`cv_builder/reference/claims_schema.md` §§1-2 into fail-closed checkers:
inventory consistency, sentinel malformation, sentinel placement, in-progress
label budget, expired expected-dates, and LOC/test-count claims in deliverables.

Binds the frozen CLI contract in `claims_schema.md` §3/§3.1/§3.2.
Read-only; stdlib only; UTF-8 no BOM; repo-relative paths; no timestamps; offline.
DETERMINISM NOTE: "today" is a FIXED reference (TODAY_REF below), never the wall
clock — the contract forbids timestamps and requires byte-identical output. The
reference is overridable with --today YYYY-MM for tests and for advancing the kit.

RULES (PV-xxx, namespace per schema §3.3):
  Inventory rules (require --inventory; schema §1):
    PV-001  verb_class 'full-ownership' requires status 'verified' AND evidence
            naming solo work ("solo" / "sole" / "alone" / "myself" / "single-handed").
    PV-002  verb_class 'in-progress' requires the §2.3 label inside `claim`, and
            `source` = cv_builder/experience/experience_pipeline.md (owner CVs) —
            with or without a users/<profile>/ prefix (P6 owner-data location).
    PV-003  status 'ask' requires an [ASK: ...] sentinel listed in `sentinels`.
    PV-004  row schema validity: required fields present, enums in range, id =
            C-NNN unique, evidence "" only when status != verified, sentinels
            listed must literally appear in `claim`.
  Text rules (over scanned *.md / *.tex):
    PV-005  malformed sentinel — a near-miss of a §2 token: wrong case ([verify],
            [ask: ...]); a broken bracket — empty colon body ([ASK:], [VERIFY:]),
            stray spaces inside the brackets ([ VERIFY ], [ ASK: x]), a colon-less
            ASK ([ASK where]) or a misplaced colon ([ASK :where]), or an unclosed
            fragment ([VERIFY, [ask); or a prose in-progress label whose expected
            tail is non-canonical ("(in progress, expected June 2026)",
            "(in progress, expected 6/2026)", "Q3 2026", "late 2026", "2026",
            "TBC"). The literal placeholder "(in progress, expected mm/yyyy)" — as
            quoted in docs/draft prose — is excluded; only canonical mm/yyyy is
            valid.
    PV-006  sentinel placement — [VERIFY] or [ASK: ...] in a FINAL DELIVERABLE
            (schema §2 location table: not allowed there).
    PV-007  more than 2 valid in-progress labels in one DELIVERABLE (schema §2;
            gated on DELIVER, so cover-letter .tex outputs are counted too).
    PV-008  in-progress label whose expected mm/yyyy is at or before TODAY_REF
            (a planned item dated in the past cannot still be "in progress").
    PV-009  lines-of-code or test-count claim in a deliverable (CLAUDE.md
            generation rule 2: no LOC/test counts in CV/cover-letter output).
            LOC: "N lines of code/<language>", "Nk LOC", "N-line", SLOC, with a
            CODE NEXUS required so bare "N lines" of prose stays clean. Test count:
            "N unit/integration tests", "N specs", "N-test suite", "suite of N
            tests", "N tests covering ...", or a bare "N tests" — but NOT
            "N <noun> tests" (e.g. "4 user tests") or singular "N test <noun>".
    PV-010  full-ownership lead verb (Built/Developed/Designed/Implemented/Created/
            Architected) on a DELIVER/DRAFT bullet line that ALSO carries a genuine
            collaboration marker (we / our team / group project / collaborated /
            "together with" / "with the|my|our team|group|committee" / "as a team|
            group" / co-built|developed|authored|wrote|designed) — CLAUDE.md's
            most-emphasised rule: full-ownership verbs are solo-only; team work
            uses a hedged verb. Bare "our"/"us"/"together" ("our customers", "lets
            us ship", "brings data together") are NOT collaboration signals.

PATH CLASSIFICATION (schema §2 location table):
  KB         knowledge_base/** ; cv_builder/experience|support|bundles/**
  DELIVER    output/**/*.tex ; output/**/cv_*.md ; output/**/*_cv_improved.md ;
             output/** CV/cover-letter names — stem (ext stripped) equals cv /
             resume / curriculum_vitae / curriculumvitae / cover_letter /
             coverletter, OR ends with _cv / _resume / _cover_letter /
             _coverletter / _cv_improved (broadened with the kit owner's
             approval 13/06/2026, RT-2). Word-boundary match, never a bare substring.
  DRAFT      output/** draft/analysis artefacts — name carries a session /
             critique / notes / draft component, or changelog / change_log
             anywhere (checked BEFORE the deliverable branches so e.g.
             cv_critique.md, resume_changelog.md stay DRAFT) ; other output/**/*.md
             (pitches/outreach)
  Rulebook/doc paths (cv_builder/reference/, .claude/, docs/, plan.md, README) and
  this helpers/ tree are EXEMPT from text rules — they quote sentinels as content.
  PV-005 malformed-sentinel detection still skips exempt docs (they show malformed
  examples on purpose). Per-line `lint-allow` overrides on any scanned line.

USAGE:
  python cv_builder/helpers/lint_provenance.py <path>... [--format text|json]
                                                [--inventory <file.claims.jsonl>]
                                                [--today YYYY-MM]
EXIT CODES (schema §3):
  0 clean (any findings all carry a valid lint-allow)
  1 at least one unallowed finding
  2 usage error OR any input that cannot be parsed (fail-closed; never skipped)
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
TOOL = "lint_provenance"

# Fixed deterministic "today" (year, month). The kit's current date is
# 13/06/2026; PV-008 uses this, never the wall clock. Override with --today.
TODAY_REF = (2026, 6)

# --- Frozen sentinel patterns (claims_schema.md §2 — EXACT, case-sensitive) --
VERIFY_RE = re.compile(r"\[VERIFY(?::[^\]\n]*)?\]")
ASK_RE = re.compile(r"\[ASK:[^\]\n]+\]")
INPROGRESS_RE = re.compile(r"\(in progress, expected (0[1-9]|1[0-2])/20[0-9]{2}\)")

# --- Path classification ---------------------------------------------------
# Classification keys on the first RECOGNISED top-level segment, so it is
# identical whether a file is given in-repo (output/...) or as an out-of-tree
# fixture mirroring the structure (.../tmp/output/...). Unrecognised paths
# default to DRAFT (the most permissive class still subject to malformed-sentinel
# and KB rules).
_ROOT_SEGMENTS = (
    "output", "cv_builder", "knowledge_base", "docs", ".claude", "coordination",
)
PV_EXEMPT_BASENAMES = ("plan.md", "agents.md", "config.md")
KB_SECOND_SEG = ("experience", "support", "bundles")


def logical_repo_path(rel_path):
    """Return the path starting at the first recognised root segment.

    '../../../tmp/output/cv_x.md' -> 'output/cv_x.md'. If no recognised segment
    is found, the basename-bearing tail is returned unchanged.
    """
    p = rel_path.replace("\\", "/")
    segs = [s for s in p.split("/") if s not in ("", ".", "..")]
    for i, s in enumerate(segs):
        if s in _ROOT_SEGMENTS:
            return "/".join(segs[i:])
    return "/".join(segs)


def is_pv_exempt(rel_path):
    p = logical_repo_path(rel_path)
    segs = p.split("/")
    base = segs[-1].lower()
    if base in PV_EXEMPT_BASENAMES or base.startswith("readme"):
        return True
    if segs[0] in (".claude", "docs", "coordination"):
        # coordination/ holds process files — session logs (which quote sentinels
        # and ownership verbs as documentation), ACTIVE.md, dated handoffs — never
        # CV content. Exempt like docs/ (FP already exempts coordination/).
        return True
    if segs[0] == "cv_builder" and len(segs) > 1 and segs[1] in ("reference", "helpers", "templates"):
        return True
    return False


def classify(rel_path):
    """Return 'KB' | 'DELIVER' | 'DRAFT' for a scanned (non-exempt) path."""
    p = logical_repo_path(rel_path)
    segs = p.split("/")
    base = segs[-1]
    if segs[0] == "knowledge_base":
        return "KB"
    if segs[0] == "cv_builder" and len(segs) > 1 and segs[1] in KB_SECOND_SEG:
        return "KB"
    if segs[0] == "output":
        # Final deliverables: cv_*.md, *_cv_improved.md and any .tex output, plus
        # the broadened CV/cover-letter name-set below. Case-insensitive on the
        # basename: CV_jordan.md must classify as DELIVER, not slip to DRAFT.
        lbase = base.lower()
        if lbase.endswith(".tex"):
            return "DELIVER"
        # DRAFT/analysis artefacts win FIRST so a session/critique/changelog file
        # whose name happens to contain "resume"/"cv" (e.g. session_resume_notes,
        # cv_critique, resume_changelog) stays DRAFT and never escapes via the
        # deliverable-name test below (the verifier's false-positive trap).
        if _is_output_draft_name(lbase):
            return "DRAFT"
        # cv_* prefix on the hyphen-folded stem (A-F1) so cv-jane.md classifies like
        # cv_jane.md, not DRAFT — the prefix check, unlike the exact/suffix set, did not
        # see the fold (Codex-found).
        if lbase.endswith(".md") and _output_stem(lbase).startswith("cv_"):
            return "DELIVER"
        if lbase.endswith("_cv_improved.md"):
            return "DELIVER"
        # Broadened deliverable name-set (kit-owner approved 13/06/2026, RT-2): a CV
        # or cover letter named resume.md / curriculum_vitae.md / cover_letter.md /
        # jane_resume.md was previously DRAFT and silently escaped the
        # deliverable-only rules (PV-006, PV-009). Match the stem (extension
        # stripped) on WORD BOUNDARIES — exact stem or an _-prefixed suffix — so a
        # bare substring (my_resume_draft_notes, session_resume_notes) never fires.
        if _is_output_deliverable_name(lbase):
            return "DELIVER"
        # session / critique / changelog and other output prose = drafts.
        return "DRAFT"
    return "DRAFT"


# Draft/analysis artefacts under output/: classified DRAFT regardless of any
# CV/cover-letter substring in the name (checked BEFORE every deliverable branch,
# the cv_*.md one included). These are process/analysis files that quote CV
# content, never the shipped deliverable. The components are matched at word
# boundaries (start, end, or _-delimited) so a genuine deliverable name is never
# mistaken for one:
#   session / critique / notes / draft  components (session_acme, cv_critique,
#   session_resume_notes, my_resume_draft_notes); changelog / change_log anywhere
#   (resume_changelog). e.g. cv_critique.md and resume_changelog.md stay DRAFT
#   even though they would otherwise hit a deliverable branch.
_OUTPUT_DRAFT_NAME_RE = re.compile(
    r"(?:^|_)(?:session|critique|notes|draft)(?:_|$)"
    r"|change_?log",
    re.IGNORECASE)

# Broadened deliverable stems (lowercased, extension stripped). Exact stem OR an
# _-delimited suffix — a word boundary, never a bare substring.
_DELIVER_STEM_EXACT = frozenset((
    "cv", "resume", "curriculum_vitae", "curriculumvitae",
    "cover_letter", "coverletter",
))
_DELIVER_STEM_SUFFIXES = (
    "_cv", "_resume", "_cover_letter", "_coverletter", "_cv_improved",
)


def _output_stem(lbase):
    """Lowercased output/ basename, trailing .md/.tex stripped, then hyphens folded
    to underscores so a hyphen- and an underscore-spelled name classify identically
    (cover-letter.md == cover_letter.md). '-' and '_' are both ordinary filename word
    separators; matching only '_' let a hyphenated CV/cover-letter (cover-letter.md,
    curriculum-vitae.md, jane-resume.md) slip to DRAFT and silently escape the
    deliverable-only rules PV-006/007/009 (overnight-audit A-F1). The fold also keeps
    the draft-name check (_is_output_draft_name) hyphen-aware, consistently."""
    stem = lbase
    for ext in (".md", ".tex"):
        if stem.endswith(ext):
            stem = stem[:-len(ext)]
            break
    return stem.replace("-", "_")


def _is_output_draft_name(lbase):
    """True if a lowercased output/ basename is a draft/analysis artefact.

    Matched on the stem (extension stripped) so a trailing component lands on a
    real word boundary — cv_critique.md -> stem 'cv_critique' -> '_critique$'."""
    return _OUTPUT_DRAFT_NAME_RE.search(_output_stem(lbase)) is not None


def _is_output_deliverable_name(lbase):
    """True if a lowercased output/ .md basename is a broadened CV/cover-letter
    deliverable name. Matched on the stem (extension stripped) at word
    boundaries: exact stem or an _-prefixed suffix, never a bare substring."""
    if not lbase.endswith(".md"):
        return False
    stem = _output_stem(lbase)
    if stem in _DELIVER_STEM_EXACT:
        return True
    return any(stem.endswith(suf) for suf in _DELIVER_STEM_SUFFIXES)


def is_cv_deliverable(rel_path):
    """A CV deliverable for the per-CV in-progress budget (PV-007)."""
    p = logical_repo_path(rel_path)
    segs = p.split("/")
    base = segs[-1]
    if segs[0] != "output":
        return False
    if base.startswith("cv_") and base.endswith(".md"):
        return True
    if base.endswith("_cv_improved.md"):
        return True
    if base.endswith(".tex") and ("_cv" in base or base.startswith("cv_")):
        return True
    return False


# --- lint-allow handling (schema §3.2) -------------------------------------
# Comment delimiters are stripped FIRST so `-->` is never read as a separator.
_LINT_ALLOW_RE = re.compile(
    r"lint-allow:\s*(?P<rule>[A-Z]+-\d+)\s*(?P<rest>.*)$",
)
_SEP_PREFIX_RE = re.compile(r"^\s*(?:—|--|::?|-)\s*")


def parse_lint_allows(line):
    """Return list of (rule_id, reason_or_None) declared on a line."""
    region = line.replace("<!--", " ")
    region = re.sub(r"-->\s*$", "", region)
    out = []
    for m in _LINT_ALLOW_RE.finditer(region):
        rule = m.group("rule")
        rest = re.sub(r"\s*-->\s*$", "", m.group("rest"))
        reason = _SEP_PREFIX_RE.sub("", rest).strip()
        out.append((rule, reason if reason else None))
    return out


# --- File reading (fail-closed) --------------------------------------------
# UnparseableFile + read_text_strict are the SHARED fail-closed reader, imported at
# the top of this file from _shared_io (one definition across the three honesty
# readers; includes the NUL-byte / BOM-less-UTF-16 guard).


# --- Inventory parsing + consistency (schema §1) ---------------------------
REQUIRED_FIELDS = ("id", "claim", "verb_class", "source", "status", "sentinels", "evidence")
VERB_CLASSES = {"full-ownership", "hedged", "in-progress", "neutral"}
STATUSES = {"verified", "needs-verify", "ask"}
_ID_RE = re.compile(r"^C-\d{3}$")
_SOLO_RE = re.compile(r"\b(solo|sole|alone|myself|single-handed(?:ly)?|by myself|on my own)\b",
                      re.IGNORECASE)
PIPELINE_SOURCE = "cv_builder/experience/experience_pipeline.md"
# P6 multi-profile: owner data now lives under users/<profile>/, so the canonical
# in-progress pipeline source is users/<name>/cv_builder/experience/experience_pipeline.md.
# PV-002 must accept that profile-prefixed path AND the bare/old-root form (a
# pre-migration inventory, or a public clone with no users/ tree) — matched on the
# TAIL, mirroring logical_repo_path's segment logic. The rule semantics, id, exit
# codes and CLI contract are unchanged; only the path it recognises is broadened.
_PROFILE_PREFIX_RE = re.compile(r"^users/[^/]+/")


def is_pipeline_source(src):
    """True if `src` is the in-progress pipeline source (schema §1 PV-002).

    Accepts the bare/old root `cv_builder/experience/experience_pipeline.md` and a
    profile-prefixed `users/<name>/cv_builder/experience/experience_pipeline.md`
    (the post-P6 owner-data location). The `users/<name>/` prefix is stripped on the
    TAIL — never a bare substring — so only a real path segment matches.
    """
    s = src.replace("\\", "/").lstrip("./")
    s = _PROFILE_PREFIX_RE.sub("", s, count=1)
    return s == PIPELINE_SOURCE


def lint_inventory(abs_path, rel_path, errors):
    """Parse + consistency-check a claims inventory. Returns inventory findings.

    Parse failures (BOM, undecodable, malformed JSON, blank line, missing/extra
    fields, bad enum, bad id) are fail-closed ERRORS (exit 2). Consistency rule
    breaches (PV-001..PV-004 semantic) are FINDINGS (exit 1).
    """
    findings = []
    try:
        text = read_text_strict(abs_path)
    except UnparseableFile as e:
        errors.append({"path": rel_path, "line": 0, "message": e.message})
        return findings

    raw_lines = text.split("\n")
    # A single trailing newline yields one empty tail element — tolerate it.
    if raw_lines and raw_lines[-1] == "":
        raw_lines = raw_lines[:-1]

    seen_ids = {}
    for i, line in enumerate(raw_lines, 1):
        if line.strip() == "":
            errors.append({"path": rel_path, "line": i,
                           "message": "blank line in inventory (not allowed)"})
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            errors.append({"path": rel_path, "line": i, "message": "unparseable JSON"})
            continue
        if not isinstance(obj, dict):
            errors.append({"path": rel_path, "line": i,
                           "message": "inventory line is not a JSON object"})
            continue
        # Field set: all required, none extra.
        missing = [f for f in REQUIRED_FIELDS if f not in obj]
        extra = [k for k in obj if k not in REQUIRED_FIELDS]
        if missing:
            errors.append({"path": rel_path, "line": i,
                           "message": "missing field(s): %s" % ", ".join(sorted(missing))})
            continue
        if extra:
            errors.append({"path": rel_path, "line": i,
                           "message": "unexpected field(s): %s" % ", ".join(sorted(extra))})
            continue
        # Types.
        if not isinstance(obj["sentinels"], list):
            errors.append({"path": rel_path, "line": i,
                           "message": "'sentinels' must be an array"})
            continue
        for key in ("id", "claim", "verb_class", "source", "status", "evidence"):
            if not isinstance(obj[key], str):
                errors.append({"path": rel_path, "line": i,
                               "message": "'%s' must be a string" % key})
                obj = None
                break
        if obj is None:
            continue

        # id format + uniqueness -> structural ERROR (fail-closed).
        if not _ID_RE.match(obj["id"]):
            errors.append({"path": rel_path, "line": i,
                           "message": "id '%s' is not C-NNN" % obj["id"]})
            continue
        if obj["id"] in seen_ids:
            errors.append({"path": rel_path, "line": i,
                           "message": "duplicate id '%s' (first at line %d)"
                                      % (obj["id"], seen_ids[obj["id"]])})
            continue
        seen_ids[obj["id"]] = i

        # enum ranges -> structural ERROR.
        if obj["verb_class"] not in VERB_CLASSES:
            errors.append({"path": rel_path, "line": i,
                           "message": "verb_class '%s' not in %s"
                                      % (obj["verb_class"], sorted(VERB_CLASSES))})
            continue
        if obj["status"] not in STATUSES:
            errors.append({"path": rel_path, "line": i,
                           "message": "status '%s' not in %s"
                                      % (obj["status"], sorted(STATUSES))})
            continue

        # --- Semantic consistency (FINDINGS, exit 1) ---
        # PV-004: evidence "" only when status != verified.
        if obj["status"] == "verified" and obj["evidence"].strip() == "":
            findings.append(_inv_finding(rel_path, i, "PV-004",
                "status 'verified' requires non-empty evidence"))
        # PV-004: listed sentinels must literally appear in the claim text.
        for s in obj["sentinels"]:
            if not isinstance(s, str):
                errors.append({"path": rel_path, "line": i,
                               "message": "sentinel entries must be strings"})
                continue
            if s not in obj["claim"]:
                findings.append(_inv_finding(rel_path, i, "PV-004",
                    "sentinel '%s' listed but not present in claim text" % s))
        # PV-001: full-ownership requires verified + solo evidence.
        if obj["verb_class"] == "full-ownership":
            if obj["status"] != "verified":
                findings.append(_inv_finding(rel_path, i, "PV-001",
                    "verb_class 'full-ownership' requires status 'verified'"))
            if not _SOLO_RE.search(obj["evidence"]):
                findings.append(_inv_finding(rel_path, i, "PV-001",
                    "verb_class 'full-ownership' requires evidence naming solo work"))
        # PV-002: in-progress requires the §2.3 label in claim + pipeline source.
        # SCOPE: the pipeline-source half is schema §1's OWNER-CV rule. A future
        # non-owner (/improve-cv) inventory sources in-progress items from the
        # subject's own CV; that path (P2+) must relax this half, e.g. an
        # --owner/--subject mode. Today every inventory is the owner's, so the
        # rule is enforced as written rather than silently skipped.
        if obj["verb_class"] == "in-progress":
            if not INPROGRESS_RE.search(obj["claim"]):
                findings.append(_inv_finding(rel_path, i, "PV-002",
                    "verb_class 'in-progress' requires the '(in progress, expected mm/yyyy)' label in claim"))
            src = obj["source"].split("#")[0].replace("\\", "/")
            if not is_pipeline_source(src):
                findings.append(_inv_finding(rel_path, i, "PV-002",
                    "verb_class 'in-progress' source must be %s "
                    "(owner CV; a users/<profile>/ prefix is accepted)" % PIPELINE_SOURCE))
        # PV-003: status 'ask' requires an [ASK: ...] sentinel listed.
        if obj["status"] == "ask":
            if not any(isinstance(s, str) and ASK_RE.fullmatch(s) for s in obj["sentinels"]):
                findings.append(_inv_finding(rel_path, i, "PV-003",
                    "status 'ask' requires an '[ASK: ...]' sentinel in 'sentinels'"))

    findings.sort(key=lambda f: (f["line"], f["rule"]))
    return findings


def _inv_finding(rel_path, line, rule, message):
    # Inventory lint-allow is NOT permitted (schema §3.2) — always unallowed.
    return {"path": rel_path, "line": line, "rule": rule, "severity": "error",
            "message": message, "allowed": False, "allow_reason": None}


# --- Text rules ------------------------------------------------------------
# Malformed-sentinel near-misses (PV-005). Wrong case ([verify], [ask: ...]).
_BAD_CASE_VERIFY_RE = re.compile(r"\[(?!VERIFY\b)[Vv][Ee][Rr][Ii][Ff][Yy](?::[^\]\n]*)?\]")
_BAD_CASE_ASK_RE = re.compile(r"\[(?!ASK:)[Aa][Ss][Kk]:[^\]\n]+\]")
# Broken-bracket near-misses (schema §2 line 46: an almost-match is a finding).
# Each is tightly scoped so an ordinary "[" in KB/draft prose does not fire.
#   empty-body — colon present but nothing after it: [ASK:] [ASK: ] [VERIFY:]
#   (canonical [VERIFY] with no colon is valid and must NOT match -> colon required)
_BAD_EMPTY_SENTINEL_RE = re.compile(r"\[\s*(?:VERIFY|ASK)\s*:\s*\]", re.IGNORECASE)
#   spaced — leading/trailing space inside the brackets around the token/body:
#   [ VERIFY ]  [ ASK: x]  [VERIFY ]
_BAD_SPACED_SENTINEL_RE = re.compile(
    r"\[\s+(?:VERIFY|ASK)\b[^\]\n]*\]|\[(?:VERIFY|ASK)\b[^\]\n]*\s+\]", re.IGNORECASE)
#   colon-less ASK ([ASK where]) or space-before-colon ([ASK :where]).
_BAD_COLONLESS_ASK_RE = re.compile(
    r"\[\s*ASK\s+[^\]\n:][^\]\n]*\]|\[\s*ASK\s+:[^\]\n]*\]", re.IGNORECASE)
#   unclosed fragment — no closing ] before end of line: [VERIFY  /  [ask
_BAD_UNCLOSED_SENTINEL_RE = re.compile(r"\[\s*(?:VERIFY|ASK)\b[^\]\n]*$", re.IGNORECASE)
# Prose in-progress label that is NOT the canonical (in progress, expected mm/yyyy).
# Capture the whole "expected <tail>" span; the tail is judged against the
# canonical mm/yyyy form (valid) and the literal "mm/yyyy" placeholder (excluded —
# it is documentation, e.g. a CV that quotes the literal placeholder). Anything else (month name,
# m/yyyy, yyyy-mm, "Q3 2026", "late 2026", "2026", "TBC", ...) is malformed.
_PROSE_INPROGRESS_RE = re.compile(
    r"\(in progress,\s*expected\s+(?P<tail>[^)\n]*)\)", re.IGNORECASE)
_CANON_INPROGRESS_TAIL_RE = re.compile(r"^(0[1-9]|1[0-2])/20[0-9]{2}$")

# LOC / test-count claims (PV-009). Numbers next to lines-of-code or test units.
# A "lines"/"N-line" magnitude alone is NOT enough — it is GATED on a code nexus
# (lines of code|codebase|repo|<language>, or LOC/SLOC), so non-LOC prose such as
# "~34 lines" / "lines spanning two teams" / "3 lines of poetry" stays clean.
_LANG = (r"code|codebase|repo|python|java|c\+\+|c#|typescript|javascript|rust|go|"
         r"c|ruby|kotlin|swift|scala|php|sql")
_LOC_RE = re.compile(
    r"\b\d[\d,]*\s*(?:k\b|thousand\b)?\s*(?:\+\s*)?"
    r"(?:s?loc\b"                                          # 340 LOC / SLOC, 40k LOC
    r"|lines?\s+of\s+(?:%s)\b)" % _LANG,                   # N lines of code/<language>
    re.IGNORECASE,
)
# Magnitude-suffix and "N-line" forms: "12k lines of code", "40k LOC", "200-line",
# "12k-line codebase". A k/thousand suffix or a hyphenated "-line" both qualify.
_LOC_RE2 = re.compile(
    r"\b\d[\d,]*\s*k?\s*-\s*line\b"                        # 200-line, 12k-line
    r"|\b\d[\d,]*\s*k?\s+(?:lines?\s+of\s+code|loc|sloc)\b"  # 12k lines of code, 40k LOC
    r"|\b\d[\d,]*\s*k?\s+lines?\s+of\s+(?:%s)\b" % _LANG,  # 8k lines of Rust
    re.IGNORECASE,
)
# A bare "N lines" magnitude STILL needs a code nexus, but the nexus can be a
# repo-shaped noun (codebase|repo|repository) sitting nearby on the SAME line rather
# than the word "code" immediately after "lines" — "codebase of 40,000 lines",
# "repo with 12000 lines", "40,000 lines across the codebase" (A-F4, was a false
# negative). The window is kept TIGHT (a couple of filler words) in EITHER order so an
# unrelated co-mention on a long line does not fire; "~34 lines" / "3 lines of poetry" /
# "lines spanning two teams" have no nexus and stay clean. Number form matches the
# patterns above (commas + an optional k: "40,000", "12000", "12k").
#
# Both arms fire only when "N lines" is SIZING the nexus (a brag), not when it is a
# delta/edit. The FORWARD arm omits "by" so an honest delta ("reduced the codebase by
# 4,000 lines") stays clean. The REVERSE arm is gated to MATCH (A-F4 follow-up): its
# connector is restricted to size-framing words (of|in|across|within|spanning|
# comprising) — the delta prepositions from|to|off|by are excluded, so "removed 200
# lines from the repo" / "deleted 500 lines from the codebase" stay clean — AND a
# delta VERB immediately before the number (removed|deleted|changed|reviewed|added)
# vetoes the match, so "changed 3 lines in the repo" / "we reviewed 50 lines in the
# repo" stay clean while a static-size "12k lines in our repo" still fires.
_REPO_NEXUS = r"(?:codebase|repos?|repository)"
_LOC_NUM = r"\d[\d,]*\s*k?"
# Delta verbs that, sitting right before the number, mark an edit not a size brag.
_LOC_DELTA_VERB = r"(?<!removed )(?<!deleted )(?<!changed )(?<!reviewed )(?<!added )"
_LOC_RE3 = re.compile(
    # <repo-nexus> [<=1 word] of|with|containing|spanning|across [<=2 words] N lines
    r"\b" + _REPO_NEXUS + r"\b(?:\s+\w+){0,1}\s+"
    r"(?:of|with|containing|spanning|across)\s+(?:\w+\s+){0,2}"
    + _LOC_NUM + r"\s+lines?\b"
    # N lines <size-connector> [<=2 words] <repo-nexus>  (40,000 lines across the
    # codebase). Connector is size-framing only; a leading delta verb vetoes it.
    r"|\b" + _LOC_DELTA_VERB + _LOC_NUM + r"\s+lines?\b\s+"
    r"(?:of|in|across|within|spanning|comprising)\s+(?:\w+\s+){0,2}"
    + _REPO_NEXUS + r"\b",
    re.IGNORECASE,
)
# Test counts. Genuine suite units only: NOT any "N <noun> tests" ("4 user tests")
# and NOT singular "N test <noun>" ("5 test events"). A bare PLURAL "N tests" is a
# count; a "N <word> tests" with a TYPE-qualifier noun is gated out (the count brags
# about a subtype, e.g. "user"/"acceptance"/"smoke" tests, not the suite size).
#
# EVALUATIVE descriptors are different — "484 comprehensive tests", "120 automated
# tests", "42 new tests" ARE suite-size brags with an adjective between the count and
# "tests" (the count IS the claim), and the bare-plural arm missed them because the
# number was not adjacent to "tests". Allow 1-2 such adjectives from a BOUNDED set
# (PV-009 morning-2026-06-16 #5) — bounded, not arbitrary, so type-qualifier nouns
# like "user"/"acceptance"/"smoke" still stay clean.
_TEST_ADJ = (r"(?:passing|comprehensive|automated|additional|new|extra|more|further"
             r"|green|fast|thorough|exhaustive|dedicated|bespoke|custom|rigorous"
             r"|unit|integration|regression|end-to-end|e2e|functional|parametrised"
             r"|parameterized|parameterised|targeted|focused|focussed)")
_TEST_ADJ_RUN = _TEST_ADJ + r"(?:\s+" + _TEST_ADJ + r")?"   # 1-2 stacked adjectives
_TESTCOUNT_RE = re.compile(
    r"\b\d[\d,]*\s*(?:\+\s*)?(?:unit\s+tests?|integration\s+tests?|tests?\s+passing"
    r"|passing\s+tests?|test\s+cases?|assertions?|specs?\b)\b"
    r"|\bsuite\s+of\s+\d[\d,]*\s+tests?\b"                 # suite of 200 tests
    r"|\b\d[\d,]*\s*-\s*test\s+suite\b"                    # 340-test suite
    r"|\ba?\s*\d[\d,]*\s*-\s*test\b"                       # a 340-test ...
    r"|\b\d[\d,]*\s+tests?\s+covering\b"                   # 200 tests covering ...
    r"|\b\d[\d,]*\s+" + _TEST_ADJ_RUN + r"\s+tests\b"      # 484 comprehensive tests
    r"|\b\d[\d,]*\s+tests\b",                              # bare plural: 200 tests
    re.IGNORECASE,
)

# PV-010 prose ownership. A full-ownership lead verb at the START of a bullet
# (markdown -/*/+, numbered "1." / "2)", or LaTeX \item — including an \item[<opt>]
# optional argument), co-occurring on the SAME line with a genuine collaboration
# marker. The bullet alternation mirrors lint_fingerprint's _BULLET_RE (so a numbered
# or \item[...] bullet is not silently exempt from PV-010 the way it used to be). Bare
# "our", "us" and "together" are deliberately excluded (they over-flag legitimate solo
# prose: "lets us ship faster", "brings data together") — only unambiguous
# shared-authorship signals count.
_PV010_LEAD_VERB_RE = re.compile(
    r"^\s*(?:[-*+]\s+|\d+[.)]\s+|\\item\b(?:\[[^\]]*\])?\s*)"
    r"(?:Built|Developed|Designed|Implemented|Created|Architected)\b",
    re.IGNORECASE,
)
# Person/team nouns that denote shared HUMAN authorship. Deliberately EXCLUDES a bare
# "group": in CS/data prose "group" is overloaded (consumer / control / resource /
# security / thread / user group), so "alongside the consumer group" or "with the
# control group" is solo technical work, not collaboration (verifier-found A-F2 false
# positives). The unambiguous human-"group" phrasings keep their own arms below
# ("group project", "as a group").
# The trailing (?!-\w) requires the noun to END on whitespace / line-end / non-hyphen
# punctuation, NOT a hyphen that continues into another word: "team-friendly",
# "team-building", "squad-based" are honest SOLO compounds and must NOT satisfy the
# team-noun (Codex-found v3 false positive — the word boundary alone is true before "-").
_TEAM_NOUN = (r"(?:team|committee|cohort|squad|department"
              r"|colleagues?|teammates?|maintainers?|classmates?)(?!-\w)")
# Non-human plurals that follow "team of N" in distributed-systems / data prose
# ("a team of 8 threads", "a team of 4 workers") — a count of MACHINES, not people;
# excluded so the "in a team of N" arm flags people, not infrastructure.
_NONHUMAN_AFTER_COUNT = (r"(?:threads?|workers?|shards?|nodes?|replicas?|processes"
                         r"|cores?|gpus?|machines?|servers?|instances?|containers?|pods?"
                         r"|microservices?|services?|agents?|models?|clusters?|pipelines?"
                         r"|jobs?|tasks?|queues?|executors?|actors?|crawlers?|bots?)")

_PV010_COLLAB_RE = re.compile(
    r"\b(?:we|our\s+team|group\s+project|collaborated"
    r"|together\s+with"
    # "with/alongside the/my/our <0-3 modifier words> <team-noun>". Article "a" is
    # excluded on purpose: "with a red team" / "alongside a team of bots" is security/
    # automation vocabulary, not human collaboration (verifier-found). Indefinite-article
    # collaboration is still caught by the "as part of a team" / "in a team of N" arms.
    r"|(?:with|alongside)\s+(?:the|my|our)(?:\s+\w+){0,3}\s+" + _TEAM_NOUN +
    # Genuine human "<x> group" compounds (a bare "group" is excluded as overloaded,
    # but these read unambiguously as people).
    r"|(?:working|research|study|project)\s+group"
    r"|as\s+a\s+(?:team|group)|co-(?:built|developed|authored|wrote|designed)"
    # A-F2 (overnight audit): shared-authorship phrasings the rule missed, held to the
    # same unambiguous-only bar. Verifier-tightened so realistic SOLO CS prose stays
    # clean (no bare "group", no tool object after "jointly with", no machine count).
    r"|as\s+part\s+of\s+(?:a|an|the|our|my)\s+" + _TEAM_NOUN +    # as part of a team
    # "in a team of N [people]" — a count of PEOPLE; excludes "team of one" (solo) and a
    # machine-count plural ("team of 8 threads"). The negative lookahead allows up to 2
    # optional descriptor tokens (hyphen-aware, so "long-running" counts as one) between
    # the count and the machine noun, so "team of 8 async workers" / "team of 4 lightweight
    # background workers" / "team of 16 long-running threads" are excluded as machines too
    # (Codex-found v3 false positive — a descriptor word slipped past the adjacent-only
    # lookahead). The window is 2, not 3: at {0,3} a machine noun 1-4 tokens after the count
    # silently dropped genuine human-team catches ("team of 8 engineers using a worker pool" —
    # verifier-found v3 regression); every reported descriptor FP is only 1-2 tokens, so {0,2}
    # keeps them clean while recovering the catches. "team of 8 engineers" / "team of 8 people"
    # / "team of 8 of us" STILL fire.
    r"|in\s+a\s+team\s+of\s+~?(?:[2-9]|[1-9]\d{1,2}|two|three|four|five|six|seven|eight|nine|ten"
    r"|eleven|twelve|a\s+dozen|dozens?|several|a\s+few)"
    r"(?!(?:\s+[\w-]+){0,2}\s+" + _NONHUMAN_AFTER_COUNT + r")\b"
    r"|jointly\s+with(?:\s+\w+){0,3}\s+" + _TEAM_NOUN +          # jointly with the maintainers
    r"|pair-?programm(?:ed|ing)\s+with"                          # pair-programmed with
    r")\b",
    re.IGNORECASE)


def scan_text_pv(rel_path, text, cls, today_ref):
    """Run text PV rules on one file. Returns raw findings (pre lint-allow)."""
    findings = []
    lines = text.split("\n")
    inprogress_count = 0

    for idx, line in enumerate(lines, 1):
        # PV-005 malformed sentinels (skip exempt docs handled by caller).
        for m in _BAD_CASE_VERIFY_RE.finditer(line):
            findings.append({"line": idx, "rule": "PV-005",
                             "message": "malformed sentinel '%s' (expected exact '[VERIFY]')"
                                        % m.group(0)})
        for m in _BAD_CASE_ASK_RE.finditer(line):
            findings.append({"line": idx, "rule": "PV-005",
                             "message": "malformed sentinel '%s' (expected exact '[ASK: ...]')"
                                        % m.group(0)})
        # Broken-bracket near-misses. Patterns are mutually distinct enough that a
        # single token rarely matches two; dedupe by matched span to keep output
        # deterministic and avoid double findings on one malformed token.
        seen_spans = set()
        for rx in (_BAD_EMPTY_SENTINEL_RE, _BAD_SPACED_SENTINEL_RE,
                   _BAD_COLONLESS_ASK_RE, _BAD_UNCLOSED_SENTINEL_RE):
            for m in rx.finditer(line):
                if m.span() in seen_spans:
                    continue
                seen_spans.add(m.span())
                findings.append({"line": idx, "rule": "PV-005",
                                 "message": "malformed sentinel '%s' "
                                            "(expected exact '[VERIFY]' or '[ASK: ...]')"
                                            % m.group(0).strip()})
        for m in _PROSE_INPROGRESS_RE.finditer(line):
            tail = m.group("tail").strip()
            # Canonical mm/yyyy is valid; the literal "mm/yyyy" placeholder is
            # documentation (a CV quoting the literal placeholder) -> not a finding.
            if _CANON_INPROGRESS_TAIL_RE.match(tail) or tail.lower() == "mm/yyyy":
                continue
            findings.append({"line": idx, "rule": "PV-005",
                             "message": "malformed in-progress label '%s' "
                                        "(expected '(in progress, expected mm/yyyy)')"
                                        % m.group(0).strip()})

        # Valid in-progress labels: count + expired-date check.
        for m in INPROGRESS_RE.finditer(line):
            inprogress_count += 1
            mm = int(m.group(1))
            yyyy = int(m.group(0)[m.group(0).rindex("/") + 1:m.group(0).rindex(")")])
            if (yyyy, mm) <= today_ref:
                findings.append({"line": idx, "rule": "PV-008",
                                 "message": "in-progress expected date %02d/%d is not in the future"
                                            % (mm, yyyy)})

        # PV-006 sentinel placement: [VERIFY]/[ASK] in a final deliverable.
        if cls == "DELIVER":
            for m in VERIFY_RE.finditer(line):
                findings.append({"line": idx, "rule": "PV-006",
                                 "message": "'[VERIFY]' sentinel not allowed in a final deliverable"})
            for m in ASK_RE.finditer(line):
                findings.append({"line": idx, "rule": "PV-006",
                                 "message": "'[ASK: ...]' sentinel not allowed in a final deliverable"})

        # PV-009 LOC / test-count claims in a deliverable.
        if cls == "DELIVER":
            if _LOC_RE.search(line) or _LOC_RE2.search(line) or _LOC_RE3.search(line):
                findings.append({"line": idx, "rule": "PV-009",
                                 "message": "lines-of-code claim not allowed in a deliverable"})
            if _TESTCOUNT_RE.search(line):
                findings.append({"line": idx, "rule": "PV-009",
                                 "message": "test-count claim not allowed in a deliverable"})

        # PV-010 full-ownership lead verb + collaboration marker on one bullet
        # (DELIVER or DRAFT prose). Solo-only verbs must be hedged for team work.
        if cls in ("DELIVER", "DRAFT"):
            if _PV010_LEAD_VERB_RE.search(line) and _PV010_COLLAB_RE.search(line):
                findings.append({"line": idx, "rule": "PV-010",
                                 "message": "full-ownership lead verb with a collaboration "
                                            "marker on one bullet; use a hedged verb "
                                            "(Co-built/Contributed/Supported) for team work"})

    # PV-007 in-progress budget per deliverable (> 2). Gated on the DELIVER class
    # (schema §2) rather than the narrower is_cv_deliverable() name test, so a
    # cover-letter .tex (e2e_<name>_cover_letter.tex) is covered too — a strict
    # superset of the old behaviour (every cv_*/_cv_improved/_cv.tex is DELIVER).
    if cls == "DELIVER" and inprogress_count > 2:
        loc = 0
        for idx, line in enumerate(lines, 1):
            if INPROGRESS_RE.search(line):
                loc = idx
                break
        findings.append({"line": loc, "rule": "PV-007",
                         "message": "%d in-progress labels in one deliverable (max 2)"
                                    % inprogress_count})

    findings.sort(key=lambda f: (f["line"], f["rule"]))
    return findings


# --- Allow resolution + META-001 (shared with fingerprint semantics) -------
def resolve_allows(rel_path, text, raw_findings):
    lines = text.split("\n")
    fired_by_line = {}
    for f in raw_findings:
        fired_by_line.setdefault(f["line"], set()).add(f["rule"])

    findings = []
    meta = []

    for ln, line in enumerate(lines, 1):
        if "lint-allow" not in line:
            continue
        for rule, reason in parse_lint_allows(line):
            targets = {ln, ln + 1}
            applies = any(rule in fired_by_line.get(t, set()) for t in targets)
            if reason is None:
                meta.append({"line": ln, "rule": "META-001",
                             "message": "lint-allow for %s has no reason" % rule})
            elif not applies:
                meta.append({"line": ln, "rule": "META-001",
                             "message": "lint-allow names %s but it did not fire on this line" % rule})

    def allow_for(target_line, rule_id):
        for cand in (target_line, target_line - 1):
            if cand < 1 or cand > len(lines):
                continue
            if "lint-allow" not in lines[cand - 1]:
                continue
            for rule, reason in parse_lint_allows(lines[cand - 1]):
                if rule == rule_id and reason:
                    return reason
        return None

    for f in raw_findings:
        reason = allow_for(f["line"], f["rule"])
        findings.append({"path": rel_path, "line": f["line"], "rule": f["rule"],
                         "severity": "error", "message": f["message"],
                         "allowed": reason is not None, "allow_reason": reason})
    for m in meta:
        findings.append({"path": rel_path, "line": m["line"], "rule": m["rule"],
                         "severity": "error", "message": m["message"],
                         "allowed": False, "allow_reason": None})

    findings.sort(key=lambda f: (f["line"], f["rule"]))
    return findings


# --- File discovery (duplicated; P1 accepts duplication) -------------------
def repo_root():
    return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def to_rel(abs_path, root):
    return os.path.relpath(abs_path, root).replace("\\", "/")


def gather_paths(inputs, root):
    md_tex = (".md", ".tex")
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
                    if fn.endswith(md_tex):
                        ap = os.path.normpath(os.path.join(dirpath, fn))
                        if ap not in seen:
                            seen.add(ap)
                            out.append((ap, to_rel(ap, root)))
        else:
            if abs_item not in seen:
                seen.add(abs_item)
                out.append((abs_item, to_rel(abs_item, root)))
    out.sort(key=lambda t: t[1])
    return out


# --- Output (duplicated) ---------------------------------------------------
def emit_text(files_scanned, findings, errors):
    lines = []
    for e in errors:
        lines.append("ERROR %s:%d %s" % (e["path"], e["line"], e["message"]))
    for f in findings:
        tag = "ALLOWED" if f["allowed"] else "FINDING"
        msg = "%s %s:%d %s %s" % (tag, f["path"], f["line"], f["rule"], f["message"])
        if f["allowed"]:
            msg += "  (lint-allow: %s)" % f["allow_reason"]
        lines.append(msg)
    allowed_n = sum(1 for f in findings if f["allowed"])
    unallowed_n = sum(1 for f in findings if not f["allowed"])
    lines.append("scanned %d file(s): %d finding(s) (%d unallowed, %d allowed), %d error(s)"
                 % (files_scanned, len(findings), unallowed_n, allowed_n, len(errors)))
    return "\n".join(lines)


def emit_json(files_scanned, findings, errors, exit_code):
    allowed_n = sum(1 for f in findings if f["allowed"])
    doc = {
        "tool": TOOL,
        "schema_version": SCHEMA_VERSION,
        "files_scanned": files_scanned,
        "findings": findings,
        "errors": errors,
        "summary": {
            "errors": len(errors),
            "findings": len(findings),
            "allowed": allowed_n,
            "exit_code": exit_code,
        },
    }
    return json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=2)


def parse_today(s):
    m = re.fullmatch(r"(20[0-9]{2})-(0[1-9]|1[0-2])", s)
    if not m:
        raise argparse.ArgumentTypeError("--today must be YYYY-MM (e.g. 2026-06)")
    return (int(m.group(1)), int(m.group(2)))


# --- Main ------------------------------------------------------------------
def run(argv):
    parser = argparse.ArgumentParser(
        prog="lint_provenance.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=True,
    )
    parser.add_argument("paths", nargs="+", help="files or directories (dirs recurse *.md/*.tex)")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--inventory", default=None,
                        help="claims inventory (*.claims.jsonl) for PV-001..PV-004")
    parser.add_argument("--today", type=parse_today, default=TODAY_REF,
                        help="fixed reference month YYYY-MM for PV-008 (default 2026-06)")
    args = parser.parse_args(argv)

    root = repo_root()
    errors = []
    all_findings = []
    today_ref = args.today

    targets = gather_paths(args.paths, root)
    files_scanned = 0
    for abs_path, rel_path in targets:
        try:
            text = read_text_strict(abs_path)
        except UnparseableFile as e:
            errors.append({"path": rel_path, "line": 0, "message": e.message})
            continue
        files_scanned += 1
        if is_pv_exempt(rel_path):
            continue
        cls = classify(rel_path)
        raw = scan_text_pv(rel_path, text, cls, today_ref)
        resolved = resolve_allows(rel_path, text, raw)
        all_findings.extend(resolved)

    if args.inventory is not None:
        inv_abs = args.inventory if os.path.isabs(args.inventory) else os.path.join(root, args.inventory)
        inv_abs = os.path.normpath(inv_abs)
        all_findings.extend(lint_inventory(inv_abs, to_rel(inv_abs, root), errors))

    all_findings.sort(key=lambda f: (f["path"], f["line"], f["rule"], f["message"]))
    errors.sort(key=lambda e: (e["path"], e["line"], e["message"]))

    unallowed = [f for f in all_findings if not f["allowed"]]
    if errors:
        exit_code = 2
    elif unallowed:
        exit_code = 1
    else:
        exit_code = 0

    if args.format == "json":
        out = emit_json(files_scanned, all_findings, errors, exit_code)
    else:
        out = emit_text(files_scanned, all_findings, errors)
    _write_stdout(out + "\n")
    return exit_code


def _write_stdout(text):
    """Write UTF-8 with LF newlines, bypassing platform CRLF translation so the
    same input yields byte-identical output on Windows and Linux (CI). Falls back
    to a text write when stdout has no binary buffer (e.g. captured StringIO)."""
    data = text.encode("utf-8")
    buf = getattr(sys.stdout, "buffer", None)
    if buf is not None:
        buf.write(data)
        buf.flush()
    else:
        sys.stdout.write(text)


def main():
    try:
        code = run(sys.argv[1:])
    except SystemExit as e:
        raise SystemExit(2 if e.code not in (0, None) else e.code)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
