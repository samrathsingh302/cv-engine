#!/usr/bin/env python
"""
lint_fingerprint.py — deterministic AI-fingerprint checker (FP-xxx).

Extracts the DETERMINISTIC subset of `cv_builder/support/ai_fingerprint_rules.md`
(the prose source of truth) into fail-closed rules. Judgement-call rules
(sentence-length variety, paragraph-structure repetition, passive-voice ratio,
triplet-structure counts) are deliberately NOT implemented here — a determinist
checker must not guess.

Binds the frozen CLI contract in `cv_builder/reference/claims_schema.md` §3/§3.1/§3.2.
Read-only; stdlib only; UTF-8 no BOM; repo-relative paths; no timestamps; offline.

RULES (FP-xxx, namespace per schema §3.3):
  FP-001  banned word — Tier-1 dead-giveaway, banned adjective/verb/adverb, or
          metaphorical-use noun from the banned table (whole-word, case-insensitive).
          Where the prose allows a contextual exception (literal "landscape",
          "novel" quoting a JD), the deterministic answer is: flag it, let the
          author add a `lint-allow` with a reason.
  FP-002  banned phrase — an opening/transition or CV/cover-letter cliche phrase
          ("proven track record", "passionate about", ...).
  FP-003  more than 2 em-dashes (literal `---`) in one document (rule: max 2).
  FP-004  bullet ending in a vague "-ing" phrase (the #1 structural AI marker).
          A bullet ending "...improving efficiency" fires; one ending on a concrete
          object/metric does not (a trailing number, %, or unit is treated concrete).
  FP-005  `---` used as a list-item separator inside a line of prose (list items
          should use ". ", not "---").

SCAN POLICY (documented in --help):
  FP rules check what a reader of a DELIVERABLE sees. Rulebook / documentation /
  analysis files QUOTE banned words as content (rules to avoid, reviewer dislikes,
  worked examples) so FP rules are EXEMPT there by default — else the kit's own
  honesty rules would lint themselves. Exempt: cv_builder/{reference,support,
  bundles,experience,examples,helpers,templates}/, .claude/, docs/, knowledge_base/,
  coordination/, plan.md / CLAUDE.md / DOCS.md / AGENTS.md / README* at root, and
  output/ analysis files (session_*, critique_*, *changelog*). SCANNED: the actual
  deliverables in output/ (cv_*.md and *.tex). Per-line `lint-allow` overrides on
  any scanned line (schema §3.2).

USAGE:
  python cv_builder/helpers/lint_fingerprint.py <path>... [--format text|json]
                                                [--inventory <file.claims.jsonl>]
  <path>     files or directories; directories recurse over *.md and *.tex.
  --format   text (default) | json (schema §3.1 on stdout).
  --inventory accepted for CLI symmetry with lint_provenance; an unparseable
             inventory still fails the run closed (exit 2). FP rules do not read it.

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
TOOL = "lint_fingerprint"

# --- Scan policy -----------------------------------------------------------
# FP rules check what a READER of a deliverable sees. Rulebook / documentation /
# analysis files QUOTE banned words as content (rules to avoid, reviewer dislikes,
# worked examples) and are EXEMPT by default — otherwise the kit's own honesty
# rules would lint themselves. Deliverables in output/ stay fully scanned.
#
# Classification keys on the first RECOGNISED top-level segment so it is
# identical for in-repo paths and out-of-tree fixtures mirroring the structure.
_ROOT_SEGMENTS = (
    "output", "cv_builder", "knowledge_base", "docs", ".claude", "coordination",
)
# cv_builder/<seg>/ subtrees that are doc/rulebook content (NOT deliverables).
_CV_EXEMPT_SECOND_SEG = (
    "reference", "support", "bundles", "experience", "examples", "helpers",
    "templates",
)
# Exempt exact files / file-name patterns at the repo root (rulebooks/docs/config).
# config.md is the owner's data/config (provenance flags, KB corrections, education
# lines) read BY the skills — not a generated deliverable — so its structural
# em-dashes and quoted examples are not the prose AI tell.
FP_EXEMPT_BASENAMES = ("plan.md", "claude.md", "docs.md", "agents.md", "config.md")
# Analysis / draft artefacts living under output/ that DISCUSS fingerprint
# patterns by name (critiques, session logs, change logs) — exempt; the actual
# CV/cover-letter deliverables in the same folder are NOT.
FP_EXEMPT_OUTPUT_PREFIXES = ("session_", "critique_")
FP_EXEMPT_OUTPUT_SUBSTR = ("changelog", "change_log")


def logical_repo_path(rel_path):
    """Return the path starting at the first recognised root segment."""
    p = rel_path.replace("\\", "/")
    segs = [s for s in p.split("/") if s not in ("", ".", "..")]
    for i, s in enumerate(segs):
        if s in _ROOT_SEGMENTS:
            return "/".join(segs[i:])
    return "/".join(segs)


def is_fp_exempt(rel_path):
    """True if rel_path is a rulebook/doc/analysis path exempt from FP rules."""
    p = logical_repo_path(rel_path)
    segs = p.split("/")
    base_l = segs[-1].lower()
    if base_l in FP_EXEMPT_BASENAMES or base_l.startswith("readme"):
        return True
    if segs[0] in (".claude", "docs", "knowledge_base", "coordination"):
        return True
    if segs[0] == "cv_builder" and len(segs) > 1 and segs[1] in _CV_EXEMPT_SECOND_SEG:
        return True
    if segs[0] == "output":
        if base_l.startswith(FP_EXEMPT_OUTPUT_PREFIXES):
            return True
        if any(s in base_l for s in FP_EXEMPT_OUTPUT_SUBSTR):
            return True
    return False


# --- Banned vocabulary (from ai_fingerprint_rules.md §1) -------------------
# Single words, whole-word case-insensitive. The prose file's "(as verb)" /
# "(metaphorical)" qualifiers are judgement calls; the deterministic stance is
# to flag the lemma and let the author lint-allow a true literal use.
BANNED_WORDS = {
    # Tier 1 — dead giveaways
    "delve", "tapestry", "multifaceted", "pivotal", "realm", "synergy",
    "paradigm", "holistic", "nuanced", "foster", "embark", "leverage",
    "utilize", "harness", "spearhead", "cornerstone", "landscape", "journey",
    "cutting-edge", "novel", "innovative", "groundbreaking",
    # Banned adjectives
    "robust", "comprehensive", "meticulous", "diverse", "extensive",
    # Banned verbs
    "facilitate", "showcase", "underscore", "bolster",
    # Banned adverbs
    "meticulously", "notably", "subsequently", "remarkably", "seamlessly",
    "thereby",
}

# Inflected forms of banned verbs/adjectives the prose intent clearly covers.
BANNED_WORD_INFLECTIONS = {
    "leverages", "leveraged", "leveraging",
    "utilizes", "utilized", "utilizing", "utilise", "utilises", "utilised",
    "utilising",
    "harnesses", "harnessed", "harnessing",
    "spearheads", "spearheaded", "spearheading",
    "fosters", "fostered", "fostering",
    "facilitates", "facilitated", "facilitating",
    "showcases", "showcased", "showcasing",
    "underscores", "underscored", "underscoring",
    "bolsters", "bolstered", "bolstering",
    "delves", "delved", "delving",
    "embarks", "embarked", "embarking",
}

ALL_BANNED_WORDS = BANNED_WORDS | BANNED_WORD_INFLECTIONS

# Banned phrases (multi-word, from §2). Matched case-insensitively with word
# boundaries; internal whitespace tolerant.
BANNED_PHRASES = (
    "in today's rapidly evolving",
    "at the forefront of",
    "it is worth noting that",
    "this experience has taught me",
    "i am uniquely positioned to",
    "in an era of",
    "proven track record",
    "passionate about",
    "i am excited to apply",
    "demonstrated ability to",
    "strong foundation in",
    "well-versed in",
    "adept at",
    "team player",
    "fast learner",
    "hit the ground running",
)

# --- Compiled patterns -----------------------------------------------------
# Whole-word match. Words may contain hyphens (cutting-edge), so the boundary is
# "not preceded/followed by a word char or hyphen". Case-insensitive.
_BANNED_WORD_RE = re.compile(
    r"(?<![\w-])(" + "|".join(re.escape(w) for w in sorted(ALL_BANNED_WORDS, key=len, reverse=True)) + r")(?![\w-])",
    re.IGNORECASE,
)

# Curly quote / apostrophe normalisation (so a smart apostrophe doesn't defeat a
# banned phrase). Maps the typographic forms to their ASCII equivalents before
# phrase matching. Safe: exactly one banned phrase contains an apostrophe
# ("in today's rapidly evolving"), so this can only HELP that match, never
# over-broaden others.
_CURLY_MAP = {
    "’": "'",  # ’ right single quote / apostrophe
    "‘": "'",  # ‘ left single quote
    "“": '"',  # “ left double quote
    "”": '"',  # ” right double quote
}


def normalise_curly(text):
    """Return text with curly quotes/apostrophes folded to their ASCII forms."""
    for src, dst in _CURLY_MAP.items():
        text = text.replace(src, dst)
    return text


# Intraword markdown emphasis delimiters that, when sitting BETWEEN two word
# characters, are reader-invisible inside a word: a reader of `lev*er*age` /
# `lev_er_age` / ``lev`er`age`` sees "leverage". Stripping ONLY the intraword
# delimiters reconstructs the rendered word for the FP-001 banned-word view.
# Snake_case identifiers (`use_leverage_helper`) collapse to one long run
# ("useleveragehelper") whose embedded "leverage" then has a word char before it,
# so the whole-word boundary keeps it from matching — a real identifier is safe.
_INTRAWORD_EMPHASIS_RE = re.compile(r"(?<=\w)[*_`](?=\w)")

# Whole-word (paired) emphasis wrap: `_leverage_`, `__utilize__`, `*foster*`. The
# banned-word boundary `(?<![\w-])...(?![\w-])` tolerates a flanking `*`/`` ` `` (not
# \w) but NOT a flanking `_` (underscore IS a \w char) — so markdown-italic
# `_leverage_`, which a reader sees as *leverage*, would slip (verifier F3). Strip
# a PAIRED wrap around one word, anchored on non-word boundaries OUTSIDE the
# delimiters, so an interior `use_leverage_helper` (no outside boundary) and an
# unpaired identifier `_leverage` (no matching closing delimiter) are NOT touched.
_WRAP_EMPHASIS_RE = re.compile(
    r"(?<![\w*_`])([*_`]{1,2})([A-Za-z][A-Za-z'-]*)\1(?![\w*_`])")


def strip_intraword_emphasis(text):
    """Strip markdown emphasis delimiters that sit between two word chars.

    Returns a 'rendered word' view for FP-001 so split-with-emphasis evasions
    (lev*er*age) collapse back to the banned lemma.
    """
    return _INTRAWORD_EMPHASIS_RE.sub("", text)


def strip_wrap_emphasis(text):
    """Strip a paired markdown emphasis wrap around a whole word (`_leverage_`)."""
    return _WRAP_EMPHASIS_RE.sub(lambda m: m.group(2), text)


# Zero-width / invisible-format code points that a banned lemma can be split by
# to slip the matcher while rendering as the intact word to a reader
# (lev<U+200B>erage, ut<U+00AD>ilise). None of these legitimately appears INSIDE
# a CV word, so removing them from the RENDERED word/phrase views (FP-001 /
# FP-002) reconstructs what the reader sees at a near-zero false-positive cost.
# Applied ONLY to those two views — never to the source used for finding
# locations or for the `---` / em-dash-glyph scans (a leading U+FEFF BOM is still
# caught at the file read seam; this only neutralises an INTERIOR occurrence).
_ZERO_WIDTH_CHARS = (
    "​"  # zero-width space
    "‌"  # zero-width non-joiner (ZWNJ)
    "‍"  # zero-width joiner (ZWJ)
    "﻿"  # zero-width no-break space / interior BOM
    "­"  # soft hyphen
)
_ZERO_WIDTH_RE = re.compile("[" + _ZERO_WIDTH_CHARS + "]")


def strip_zero_width(text):
    """Return text with reader-invisible zero-width / soft-hyphen chars removed.

    Reconstructs the 'rendered word' so a zero-width split (lev<U+200B>erage) or a
    soft hyphen (ut<U+00AD>ilise) collapses back to the banned lemma for FP-001 /
    FP-002. Pure, deterministic; only ever applied to the matcher views.
    """
    return _ZERO_WIDTH_RE.sub("", text)


# Hyphen-split evasion: a hyphen on either side of a banned lemma blocks the
# whole-word rule (its boundary is `(?<![\w-])...(?![\w-])`), so co-leverage /
# re-leverage / non-utilise / innovative-solution slip. A hyphenated compound
# is one banned lemma IF any of its hyphen-segments is itself a banned word.
# Scoped to the banned-lemma set, so unrelated hyphenates (state-of-the-art,
# real-time, well-known) stay clean; a single-segment banned hyphenate that the
# main rule already owns (cutting-edge) has NO banned sub-segment so it is not
# double-reported here.
_HYPHEN_TOKEN_RE = re.compile(r"(?<![\w])[A-Za-z]+(?:-[A-Za-z]+)+(?![\w])")


def banned_hyphen_segments(text):
    """Yield (lemma_lower) for each banned lemma found as a hyphen-segment.

    A banned single-word lemma (e.g. "leverage", "utilise", "innovative") that is
    one segment of a multi-segment hyphenated compound is an evasion of the
    whole-word rule and is surfaced here. Compounds whose segments are all clean
    (state-of-the-art) yield nothing. The already-banned hyphenated lemmas
    (cutting-edge) have no banned sub-segment, so they are not duplicated.
    """
    for m in _HYPHEN_TOKEN_RE.finditer(text):
        token = m.group(0)
        segs = token.split("-")
        for seg in segs:
            if seg.lower() in ALL_BANNED_WORDS:
                yield seg.lower()


# Phrases: allow flexible internal whitespace; word-boundary on the ends.
def _phrase_pattern(phrase):
    parts = [re.escape(tok) for tok in phrase.split()]
    return r"(?<!\w)" + r"\s+".join(parts) + r"(?!\w)"

_BANNED_PHRASE_RES = [
    (p, re.compile(_phrase_pattern(p), re.IGNORECASE)) for p in BANNED_PHRASES
]

# A bullet line: markdown "- ", "* ", "+ ", numbered "1. ", or LaTeX "\item".
_BULLET_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+|\\item\b)")

# A markdown structural line that legitimately uses `---`/`***`/`___` and must
# NOT be read as an em-dash run or an in-prose list separator:
#   - a thematic break (horizontal rule): a line of only -/=/_/* (>= 3).
#   - a table delimiter / header-separator row: pipes, colons, dashes, spaces
#     only, containing at least one run of dashes (e.g. |---|:--:|------|).
_HRULE_RE = re.compile(r"^\s*([-*_=])(?:\s*\1){2,}\s*$")
_TABLE_DELIM_RE = re.compile(r"^\s*\|?[\s:|-]*-{3,}[\s:|-]*\|?\s*$")


def is_markdown_structure_line(line):
    """True for a thematic-break or table-delimiter line (structural `---`)."""
    if _HRULE_RE.match(line):
        return True
    if "-" in line and _TABLE_DELIM_RE.match(line) and "|" in line:
        return True
    return False


# Lines whose em-dash GLYPH (U+2014) is legitimate structure, not the flowing-
# prose AI tell, and so are excluded from the FP-003 markdown glyph count:
#   - headings (`#`..`######`)
#   - table rows (any line that starts with `|`) and table-delim/thematic breaks
#   - bold label / sub-heading lines: content begins with a `**bold**` span, e.g.
#     "**University of Westhaven** — MEng/BSc" (em-dash AFTER the label) or
#     "**Short version (~180 chars) — founder:**" (em-dash INSIDE the label).
# An em-dash in an ordinary paragraph, blockquote sentence, or plain list-item is
# NOT structural and IS counted. (Known, documented limitation: a prose line that
# itself begins with a `**bold:**` lead-in is treated as a label line.)
_HEADING_RE = re.compile(r"^\s*#{1,6}\s")
_TABLE_ROW_RE = re.compile(r"^\s*\|")
_BOLD_LABEL_LINE_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)?\*\*")


def is_em_dash_structural_line(line):
    """True if em-dashes on this markdown line are structural, not the prose tell."""
    if _HEADING_RE.match(line):
        return True
    if _TABLE_ROW_RE.match(line):
        return True
    if is_markdown_structure_line(line):
        return True
    # A bold label / sub-heading line uses a SINGLE em-dash as a label/value
    # separator ("**University of Westhaven** — MEng"). Exempt it ONLY when it carries
    # at most one em-dash; a line with 2+ em-dashes after a "**Label:**" lead-in is
    # prose wearing a label, and its em-dashes ARE the AI tell (verifier F1).
    if _BOLD_LABEL_LINE_RE.match(line) and line.count("—") <= 1:
        return True
    return False


# Em-dash-CLASS glyphs that read as a long dash and so count toward the FP-003
# per-document budget alongside U+2014. The EN-dash U+2013 is deliberately
# EXCLUDED — it is the legitimate range glyph ("2026–27", "grades 8–9") and must
# never count. (The structural-line exemption above still keys on U+2014 alone,
# so which lines are exempt is unchanged; this only widens the per-line count on
# the lines that are already counted.)
_EM_DASH_CLASS = (
    "—"   # U+2014 em dash
    "―"   # U+2015 horizontal bar
    "‒"   # U+2012 figure dash
    "⸺"  # U+2E3A two-em dash
    "⸻"  # U+2E3B three-em dash
)


def count_em_dash_class(text):
    """Count em-dash-class glyphs (U+2014/2015/2012/2E3A/2E3B); en-dash excluded."""
    return sum(text.count(c) for c in _EM_DASH_CLASS)


def strip_latex_comment(line):
    """Return the line with a trailing LaTeX comment removed (reader-invisible).

    A `%` starts a comment unless escaped as `\\%`. Only applied to .tex content
    so markdown `%` (rare) and lint-allow markers are untouched elsewhere.
    """
    out = []
    i = 0
    while i < len(line):
        c = line[i]
        if c == "\\" and i + 1 < len(line):
            out.append(line[i:i + 2])
            i += 2
            continue
        if c == "%":
            break
        out.append(c)
        i += 1
    return "".join(out)

# Improvement / outcome modifiers (comparative participles) — the word that the
# FP-004 3-word arm requires between "to"/"of" and the abstract noun. The AI tell
# is IMPROVEMENT/OUTCOME language ("...to IMPROVED efficiency", "...to INCREASED
# adoption", "...to ENHANCED performance"). A technical-DESCRIPTIVE modifier
# (automated / encrypted / distributed / replicated / hosted / ...) is NOT in this
# set, so a concrete migration bullet ("moving to automated testing", "switching
# to encrypted storage") does NOT take the 3-word arm and stays clean (A-F3 FP
# class). -ed and -ing comparative forms are both listed.
_IMPROVE_MODIFIERS = {
    "improved", "increased", "enhanced", "reduced", "decreased", "optimized",
    "optimised", "streamlined", "boosted", "accelerated", "strengthened",
    "heightened", "elevated", "expanded", "broadened", "maximized", "maximised",
    "minimized", "minimised",
    "improving", "increasing", "enhancing", "reducing", "growing", "scaling",
}
_IMPROVE_MODIFIER_ALT = "|".join(
    re.escape(w) for w in sorted(_IMPROVE_MODIFIERS, key=len, reverse=True))

# FP-004: a bullet ending in a vague gerund-led phrase (the #1 structural AI
# marker). The prose examples are "...advancing the field", "...contributing to
# improved efficiency", "...enabling new Z", "...improving efficiency" — a
# gerund (-ing) near the end followed only by short abstract words, with NO
# concrete anchor (number / % / £ / proper-noun) in the tail. Deterministic
# scope: look at the last few words; flag if a gerund leads the ending phrase.
#   group(1) = the gerund; group(2) = the trailing abstract tail.
# The base window is up to 2 trailing words ("...advancing the field"). A 3-word
# tail is admitted ONLY for the specific IMPROVEMENT/OUTCOME shape the AI tell
# takes — gerund + "to"/"of" + an improvement-language modifier (_IMPROVE_MODIFIERS)
# + an abstract noun ("contributing to improved efficiency", "leading to enhanced
# performance"). A naive {0,3} window was rejected (A-F3): it false-fired on honest
# committed bullets where an -ing word is a preposition or plain participle and the
# tail is concrete ("...during busy weekend shifts", "...feeding and mobility
# assistance", "...covering three upland sites"). A first cut admitted "to/of + ANY
# -ed/-ing word + noun", but "any -ed/-ing word" also caught technical-descriptive
# modifiers, so honest concrete migration bullets fired wrongly ("moving to
# automated testing", "switching to encrypted storage", "moving to replicated
# databases"); the modifier is therefore restricted to the improvement allow-list
# above. The concrete anchor / whitelist guards below still apply on top.
_VAGUE_ING_END_RE = re.compile(
    r"\b([a-z]{3,}ing)\b("
    r"(?:\s+(?:to|of)\s+(?:" + _IMPROVE_MODIFIER_ALT + r")\s+[a-z]+)"  # 3-word improvement-outcome tail
    r"|(?:\s+[a-z]+){0,2}"                            # base: up to 2 trailing words
    r")\s*$", re.IGNORECASE)
# A concrete anchor anywhere in the ending excuses it (a metric/figure/proper noun).
_CONCRETE_TAIL_RE = re.compile(r"[\d%£$]|\b[A-Z][a-zA-Z]")

# A specific whitelist of -ing words that are nouns/objects, not gerund analysis
# (these legitimately end a bullet, e.g. "... pair-programming"). Conservative.
# "driving" is a participial adjective in the compound noun "driving licence" /
# "driving test" (P2 pilot false positive: "full UK driving licence").
# "computing" is the noun-object of a concrete migration bullet ("...to distributed
# computing", "cloud/quantum computing") — without it the bare-gerund base window
# would flag "moving to distributed computing", the same FP class as "...testing".
_ING_NOUN_WHITELIST = {
    "engineering", "training", "testing", "tooling", "modelling", "modeling",
    "scripting", "marketing", "accounting", "nursing", "consulting",
    "onboarding", "reporting", "forecasting", "scheduling", "pricing",
    "banking", "manufacturing", "programming", "driving", "computing",
}


# --- lint-allow handling (schema §3.2) -------------------------------------
# Markdown: <!-- lint-allow: <RULE-ID> — <reason> -->
# LaTeX / plain: % lint-allow: <RULE-ID> — <reason>
# A lint-allow with no non-empty reason, or naming a rule that did not fire on
# that line, is itself a META-001 finding. The reason is everything after the
# rule-id and an optional separator (em-dash / "--" / ":" / "-"). Comment
# delimiters (`<!--`, `-->`, leading `%`) are stripped FIRST so they never leak
# into the rule-id or reason (a naive regex eats `--` of `-->` as a separator).
_LINT_ALLOW_RE = re.compile(
    r"lint-allow:\s*(?P<rule>[A-Z]+-\d+)\s*(?P<rest>.*)$",
)
_SEP_PREFIX_RE = re.compile(r"^\s*(?:—|--|::?|-)\s*")


def parse_lint_allows(line):
    """Return list of (rule_id, reason_or_None) declared on a line.

    reason_or_None is None when the reason is empty/whitespace (-> META-001).
    """
    # Drop the trailing markdown comment close and any HTML-comment opener so the
    # reason text is clean; a trailing LaTeX comment is the whole token region.
    region = line
    region = region.replace("<!--", " ")
    region = re.sub(r"-->\s*$", "", region)
    out = []
    for m in _LINT_ALLOW_RE.finditer(region):
        rule = m.group("rule")
        rest = m.group("rest")
        # Remove any stray trailing comment close that survived mid-line.
        rest = re.sub(r"\s*-->\s*$", "", rest)
        reason = _SEP_PREFIX_RE.sub("", rest).strip()
        out.append((rule, reason if reason else None))
    return out


# --- File reading (fail-closed) --------------------------------------------
# UnparseableFile + read_text_strict are the SHARED fail-closed reader, imported at
# the top of this file from _shared_io (one definition across the three honesty
# readers; includes the NUL-byte / BOM-less-UTF-16 guard).


# --- Inventory parsing (shared semantics; FP only needs the fail-closed path)
def check_inventory_parseable(abs_path, rel_path, errors):
    """Parse a claims inventory enough to fail closed on malformed lines.

    FP does not apply consistency rules; it only honours the contract that an
    unparseable inventory FAILS the run (schema §3). Appends to `errors`.
    """
    try:
        text = read_text_strict(abs_path)
    except UnparseableFile as e:
        errors.append({"path": rel_path, "line": 0, "message": e.message})
        return
    for i, line in enumerate(text.split("\n"), 1):
        if line == "" and i == len(text.split("\n")):
            continue  # tolerate a single trailing newline producing one empty tail
        if line.strip() == "":
            errors.append({"path": rel_path, "line": i,
                           "message": "blank line in inventory (not allowed)"})
            continue
        try:
            json.loads(line)
        except json.JSONDecodeError:
            errors.append({"path": rel_path, "line": i,
                           "message": "unparseable JSON"})


# --- Rule scanners ---------------------------------------------------------
def logical_bullets(lines):
    """Yield (start_line_1based, last_text_line) for each markdown/LaTeX bullet.

    A bullet is its marker line plus the following indented (or non-blank,
    non-marker) continuation lines — i.e. how it actually renders. The ending
    test (FP-004) runs on the LAST non-blank continuation line, and the finding
    is attributed to the marker line for stable location.
    """
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if _BULLET_RE.match(line):
            start = i + 1  # 1-based marker line
            last = line
            j = i + 1
            while j < n:
                nxt = lines[j]
                if nxt.strip() == "":
                    break
                if _BULLET_RE.match(nxt):
                    break
                # A continuation line is indented; a flush-left paragraph ends it.
                if nxt[:1] in (" ", "\t"):
                    last = nxt
                    j += 1
                    continue
                break
            yield start, last
            i = j
        else:
            i += 1


def scan_file_fp(rel_path, text):
    """Run all FP rules on one (already-read) file. Returns list of raw findings.

    Each raw finding: dict(line, rule, message). `allowed`/`allow_reason` are
    resolved later against lint-allows. Markdown table-delimiter rows, thematic
    breaks and LaTeX comments are reader-invisible / structural and are excluded
    from the `---` rules (FP-003/FP-005) so they are not mistaken for em-dashes
    or in-prose separators.
    """
    findings = []
    lines = text.split("\n")
    is_tex = rel_path.replace("\\", "/").endswith(".tex")

    em_dash_total = 0  # FP-003 is per-document
    first_em_line = 0

    for idx, line in enumerate(lines, 1):
        # Prose view: drop LaTeX comments (never rendered to the reader).
        prose = strip_latex_comment(line) if is_tex else line

        # FP-001 banned words. Run over a 'rendered word' view that strips
        # intraword emphasis (lev*er*age -> leverage) and zero-width / soft-hyphen
        # splits (lev<U+200B>erage -> leverage) so neither can hide a banned word
        # from the reader. A whole-word-emphasis or snake_case form does not gain a
        # new match (whole-word boundary protects it).
        prose_word = strip_zero_width(strip_intraword_emphasis(strip_wrap_emphasis(prose)))
        for m in _BANNED_WORD_RE.finditer(prose_word):
            word = m.group(1)
            findings.append({
                "line": idx, "rule": "FP-001",
                "message": "banned word '%s'" % word.lower(),
            })
        # FP-001 hyphen-split evasion: a banned lemma worn as a hyphen-segment
        # (co-leverage, non-utilise, innovative-solution) — surfaced separately
        # because the whole-word rule's hyphen boundary deliberately ignores it.
        for seg in banned_hyphen_segments(prose_word):
            findings.append({
                "line": idx, "rule": "FP-001",
                "message": "banned word '%s' (hyphen-split)" % seg,
            })
        # FP-002 banned phrases. Fold curly quotes/apostrophes to ASCII and drop
        # zero-width / soft-hyphen splits first so neither a smart apostrophe
        # ("in today's...") nor an invisible char inside a phrase word can defeat
        # the match.
        prose_phrase = strip_zero_width(normalise_curly(prose))
        for phrase, rx in _BANNED_PHRASE_RES:
            if rx.search(prose_phrase):
                findings.append({
                    "line": idx, "rule": "FP-002",
                    "message": "banned phrase '%s'" % phrase,
                })

        # FP-003 em-dash budget (per document). Reader-visible em-dashes only.
        line_em = 0
        # LaTeX-source `---` (renders as an em-dash in .tex; some md authors use it
        # too). Skip thematic-break / table-delimiter lines & tex comments.
        if "---" in prose and not is_markdown_structure_line(prose):
            line_em += prose.count("---")
            # FP-005: `---` between non-space text on the same line (text---text),
            # not a thematic break line (already excluded above). `---` only —
            # the glyph is deliberately NOT added here (it mass-false-positives on
            # normal prose/heading punctuation, not list separators).
            if re.search(r"\S\s*---\s*\S", prose):
                findings.append({
                    "line": idx, "rule": "FP-005",
                    "message": "'---' used as an in-line separator (use '. ' for list items)",
                })
        # Markdown em-dash-class GLYPHS — the form a markdown reader actually sees
        # (the .tex `---` source spelling above doesn't exist in md). Counts U+2014
        # plus the other long-dash glyphs (U+2015 bar, U+2012 figure, U+2E3A/2E3B
        # multi-em dashes) so swapping the glyph can't evade the budget. Counted
        # only in prose lines; structural lines (headings, table rows, bold label /
        # sub-heading lines, thematic breaks) are excluded. The en-dash U+2013
        # (ranges: "2026–27", "grades 8–9") is never counted.
        if not is_tex and not is_em_dash_structural_line(line):
            line_em += count_em_dash_class(prose)
        if line_em:
            em_dash_total += line_em
            if first_em_line == 0:
                first_em_line = idx

    # FP-004 bullet ending in a vague gerund-led phrase — over LOGICAL (wrapped)
    # bullets, attributed to the marker line.
    for start, last in logical_bullets(lines):
        last_prose = strip_latex_comment(last) if is_tex else last
        tail = last_prose.rstrip()
        # Strip trailing closing punctuation/markup so "improving efficiency."
        # and "...efficiency*" test the same as "...efficiency".
        tail_clean = re.sub(r"[\.\;\:\)\]\}\"'\*`%]+\s*$", "", tail).rstrip()
        m = _VAGUE_ING_END_RE.search(tail_clean)
        if m:
            ing = m.group(1).lower()
            ending = m.group(0)  # gerund + abstract tail
            # The concrete-anchor escape applies to the tail AFTER the gerund — a
            # capitalised gerund at sentence/clause start ("...Improving speed")
            # must NOT excuse itself via its own leading capital. group(1) anchors
            # the match start, so slice it off before the concrete test. A genuine
            # proper-noun/acronym/metric AFTER the gerund ("Integrating with
            # Salesforce", "...contributing to a 15% reduction") still excuses it.
            tail_after_gerund = ending[len(m.group(1)):]
            if ing not in _ING_NOUN_WHITELIST and not _CONCRETE_TAIL_RE.search(tail_after_gerund):
                findings.append({
                    "line": start, "rule": "FP-004",
                    "message": "bullet ends with a vague '-ing' phrase ('%s')" % ending.strip(),
                })

    if em_dash_total > 2:
        findings.append({
            "line": first_em_line, "rule": "FP-003",
            "message": "%d em-dashes in document (max 2)" % em_dash_total,
        })

    findings.sort(key=lambda f: (f["line"], f["rule"]))
    return findings


# --- Allow resolution + META-001 -------------------------------------------
def resolve_allows(rel_path, text, raw_findings):
    """Attach allowed/allow_reason to each finding; emit META-001 for misuse.

    A lint-allow on the offending line or the line immediately above it, naming
    the rule that fired, with a non-empty reason, allows that finding.
    A lint-allow that names a rule which did NOT fire on its target line, or has
    an empty reason, is a META-001 finding.
    """
    lines = text.split("\n")
    # Map line -> set of rule-ids that fired on that line.
    fired_by_line = {}
    for f in raw_findings:
        fired_by_line.setdefault(f["line"], set()).add(f["rule"])

    findings = []
    meta = []

    # Pre-scan all lint-allow declarations.
    for ln, line in enumerate(lines, 1):
        if "lint-allow" not in line:
            continue
        for rule, reason in parse_lint_allows(line):
            # target = this line and the line below (rule allows "line or line above")
            targets = {ln, ln + 1}
            applies = any(rule in fired_by_line.get(t, set()) for t in targets)
            if reason is None:
                meta.append({
                    "line": ln, "rule": "META-001",
                    "message": "lint-allow for %s has no reason" % rule,
                })
            elif not applies:
                meta.append({
                    "line": ln, "rule": "META-001",
                    "message": "lint-allow names %s but it did not fire on this line" % rule,
                })

    # Resolve each real finding against allows on its line or the line above.
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
        findings.append({
            "path": rel_path, "line": f["line"], "rule": f["rule"],
            "severity": "error",
            "message": f["message"],
            "allowed": reason is not None,
            "allow_reason": reason,
        })
    for m in meta:
        findings.append({
            "path": rel_path, "line": m["line"], "rule": m["rule"],
            "severity": "error",
            "message": m["message"],
            "allowed": False,
            "allow_reason": None,
        })

    findings.sort(key=lambda f: (f["line"], f["rule"]))
    return findings


# --- File discovery --------------------------------------------------------
def repo_root():
    """The cv-editor repo root, located relative to this file."""
    return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def to_rel(abs_path, root):
    rel = os.path.relpath(abs_path, root)
    return rel.replace("\\", "/")


def gather_paths(inputs, root):
    """Expand inputs into (abs_path, rel_path) for *.md / *.tex, sorted.

    Directories recurse; files are taken as-is regardless of extension (an
    explicit inventory or odd file passed directly is still read & fail-closed).
    """
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


# --- Output ----------------------------------------------------------------
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


# --- Main ------------------------------------------------------------------
def run(argv):
    parser = argparse.ArgumentParser(
        prog="lint_fingerprint.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=True,
    )
    parser.add_argument("paths", nargs="+", help="files or directories (dirs recurse *.md/*.tex)")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--inventory", default=None,
                        help="claims inventory (*.claims.jsonl); unparseable -> exit 2")
    # Reject unknown flags with exit 2 (argparse does this, but we trap SystemExit).
    args = parser.parse_args(argv)

    root = repo_root()
    errors = []
    all_findings = []

    targets = gather_paths(args.paths, root)
    files_scanned = 0
    for abs_path, rel_path in targets:
        try:
            text = read_text_strict(abs_path)
        except UnparseableFile as e:
            errors.append({"path": rel_path, "line": 0, "message": e.message})
            continue
        files_scanned += 1
        if is_fp_exempt(rel_path):
            continue
        raw = scan_file_fp(rel_path, text)
        resolved = resolve_allows(rel_path, text, raw)
        all_findings.extend(resolved)

    if args.inventory is not None:
        inv_abs = args.inventory if os.path.isabs(args.inventory) else os.path.join(root, args.inventory)
        inv_abs = os.path.normpath(inv_abs)
        check_inventory_parseable(inv_abs, to_rel(inv_abs, root), errors)

    all_findings.sort(key=lambda f: (f["path"], f["line"], f["rule"]))
    errors.sort(key=lambda e: (e["path"], e["line"]))

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
        # argparse exits 2 on usage/unknown-flag errors; honour exit 2.
        raise SystemExit(2 if e.code not in (0, None) else e.code)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
