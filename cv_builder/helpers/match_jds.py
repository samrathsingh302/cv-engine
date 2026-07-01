#!/usr/bin/env python
"""
match_jds.py — deterministic JD reverse-matching ranker (P7, "lever 2").

The ``/match-jds`` skill scores the knowledge base against EACH saved JD on a
lightweight version of the 8 critique dimensions and captures every pairing as an
auditable JSON *match manifest*. The judgement is the skill's; this module makes
ZERO judgement calls and ZERO LLM calls — the same data-not-a-call philosophy as
``eval/harness.py``. It loads the manifests, computes a projected fit total + band
per JD, ranks the pairings best-first, and renders a <=1-page ranked report. It
carries NO owner data, so it ships in the public engine unchanged; it is the
reproducible, byte-identical backbone the P7 done-gate is tested against
(P7 done-gate: a synthetic easy pairing must rank above a synthetic hard one;
report <=1 page).

Match manifest schema (one per JD — the contract this module validates):
  {
    "jd": "acme_placement",           # stable id (the JD file stem)
    "title": "Software Engineering Placement",
    "company": "Acme Capital",
    "fictional": false,                       # true ONLY for the synthetic fixtures
    "dimensions": {                           # the lightweight 8-dim PROJECTION
      "ats_keywords":     {"weight": 15, "score": 7.5},
      "tagline":          {"weight": 8,  "score": 8.0},
      "skills":           {"weight": 10, "score": 7.0},
      "bullet_quality":   {"weight": 22, "score": 8.0},
      "projects_evidence":{"weight": 15, "score": 8.5},
      "narrative":        {"weight": 12, "score": 7.5},
      "company_role_fit": {"weight": 13, "score": 8.0},
      "page_visual":      {"weight": 5,  "score": 8.0}
    },                                        # weights sum to 100; score 0-10
    "strongest_matches": [                    # 0..3, each citing a KB evidence file
      {"jd_req": "REST APIs in Python",
       "evidence": "built a Flask ledger API",
       "source": "cv_builder/experience/experience_work.md#L12"}
    ],
    "fatal_gaps": [                           # must-haves with ZERO KB evidence
      {"requirement": "production on-call", "note": "no ops evidence in the KB"}
    ],
    "source_jd": "users/alice/JDs/acme_placement.txt"
  }

Projected total = sum(score * weight) / 10 on a 0-100 scale (identical maths to
``eval/harness.py`` ``weighted_total``); band labels mirror that module's ``_BANDS``
and ``critique_framework.md`` Part 2. The total is a PROJECTION from KB coverage —
what a CV built from this KB for this JD could score — NOT a scored CV. The skill
states that caveat in the report; this module only does the arithmetic + ranking.

House conventions (match cv_builder/helpers/* and eval/harness.py):
  - Python stdlib only; version-portable (local 3.14, CI also 3.12).
  - Offline, deterministic, fail-closed. No network, no clock, no machine paths.
  - Byte-identical output for identical inputs: sorted keys, fixed float format,
    atomic write (temp + os.replace). UTF-8 no BOM; LF newlines.
  - Repo-relative source citations only (no owner name in engine output).

CLI:
  python cv_builder/helpers/match_jds.py [--manifests-dir DIR] [--format md|json]
                                         [--out PATH] [--max-lines N]
  --manifests-dir  dir of *.json match manifests (default: the active profile's
                   users/<active>/output/_match/manifests; fail-closed if absent).
  --format         md (default) | json.
  --out            report path (default: <manifests-dir>/../match_report.md).
  --max-lines      one-page budget for the md report (default 55). Over budget is a
                   gate failure (exit 1); the report is still written so it is seen.

Exit codes: 0 ok · 1 page-budget exceeded (gate) · 2 usage/load error.
"""

import argparse
import importlib.util
import json
import os
import sys


# --------------------------------------------------------------------------- #
# Paths + the shared band table (mirrors eval/harness.py; one page, no clock).
# --------------------------------------------------------------------------- #

_HELPERS_DIR = os.path.dirname(os.path.abspath(__file__))

# Score-band labels — identical thresholds to eval/harness.py _BANDS and
# critique_framework.md Part 2 'Overall score interpretation'. Re-derived here
# (not imported) so this engine module stays cross-import-free, exactly as the
# other helpers do; the bands are a frozen rubric constant, not a moving value.
_BANDS = (
    (85.0, "submit"),
    (80.0, "strong"),
    (75.0, "good-foundation"),
    (70.0, "first-draft"),
    (0.0, "fundamental-issues"),
)

# One A4 page of monospace markdown is ~50-60 lines; 55 is the default budget so a
# real run over a handful of JDs stays glanceable on one screen (P7 done-gate).
DEFAULT_MAX_LINES = 55

DIMENSION_NAMES = (
    "ats_keywords", "tagline", "skills", "bullet_quality",
    "projects_evidence", "narrative", "company_role_fit", "page_visual",
)


# --------------------------------------------------------------------------- #
# Loading + validation (fail-closed — mirrors harness.load_manifests).
# --------------------------------------------------------------------------- #

def load_manifests(manifests_dir):
    """Load every ``*.json`` match manifest, sorted by jd id for determinism.

    Fail-closed: a missing dir, an unreadable file, malformed JSON, a missing
    required field, weights that do not sum to 100, a score out of [0, 10], or a
    duplicate jd id all raise ValueError. ``_README.md`` and other non-JSON files
    are ignored (the fixtures dir carries a fictional-marker README).
    """
    if not os.path.isdir(manifests_dir):
        raise ValueError("manifests directory not found: %s" % manifests_dir)

    paths = sorted(
        os.path.join(manifests_dir, n)
        for n in os.listdir(manifests_dir)
        if n.endswith(".json")
    )
    if not paths:
        raise ValueError("no match manifests (*.json) found in %s" % manifests_dir)

    manifests = []
    for path in paths:
        try:
            with open(path, "rb") as fh:
                raw = fh.read()
        except OSError as exc:
            raise ValueError("unreadable manifest %s: %s" % (path, exc.__class__.__name__))
        if raw.startswith(b"\xef\xbb\xbf"):
            raise ValueError("manifest %s: UTF-8 BOM present (must be UTF-8 no BOM)" % path)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("malformed manifest %s: %s" % (path, exc))
        _validate(data, path)
        manifests.append(data)

    manifests.sort(key=lambda m: m["jd"])
    ids = [m["jd"] for m in manifests]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate jd id across manifests: %s" % ids)
    return manifests


def _validate(data, path):
    if not isinstance(data, dict):
        raise ValueError("manifest %s: top level must be a JSON object" % path)
    for field in ("jd", "title", "company", "dimensions",
                  "strongest_matches", "fatal_gaps", "source_jd"):
        if field not in data:
            raise ValueError("manifest %s missing required field %r" % (path, field))
    for field in ("jd", "title", "company", "source_jd"):
        if not isinstance(data[field], str) or not data[field].strip():
            raise ValueError("manifest %s: %r must be a non-empty string" % (path, field))

    dims = data["dimensions"]
    if not isinstance(dims, dict) or not dims:
        raise ValueError("manifest %s: dimensions must be a non-empty object" % path)
    total_weight = 0
    for name, spec in dims.items():
        if name not in DIMENSION_NAMES:
            raise ValueError(
                "manifest %s: unknown dimension %r (allowed: %s)"
                % (path, name, ", ".join(DIMENSION_NAMES))
            )
        if not isinstance(spec, dict):
            raise ValueError("manifest %s dimension %r must be an object" % (path, name))
        for key in ("weight", "score"):
            if key not in spec:
                raise ValueError(
                    "manifest %s dimension %r missing %r" % (path, name, key)
                )
            if not isinstance(spec[key], (int, float)) or isinstance(spec[key], bool):
                raise ValueError(
                    "manifest %s dimension %r: %r must be a number" % (path, name, key)
                )
        if not 0 <= spec["score"] <= 10:
            raise ValueError(
                "manifest %s dimension %r: score %s out of [0, 10]"
                % (path, name, spec["score"])
            )
        if spec["weight"] < 0:
            raise ValueError(
                "manifest %s dimension %r: weight %s must be >= 0"
                % (path, name, spec["weight"])
            )
        total_weight += spec["weight"]
    if abs(total_weight - 100) > 1e-9:
        raise ValueError(
            "manifest %s: dimension weights sum to %s, expected 100"
            % (path, total_weight)
        )

    _validate_items(data["strongest_matches"], path, "strongest_matches",
                    ("jd_req", "evidence", "source"))
    _validate_items(data["fatal_gaps"], path, "fatal_gaps", ("requirement", "note"))


def _validate_items(items, path, field, keys):
    if not isinstance(items, list):
        raise ValueError("manifest %s: %r must be a list" % (path, field))
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("manifest %s: each %s entry must be an object" % (path, field))
        for key in keys:
            if key not in item or not isinstance(item[key], str):
                raise ValueError(
                    "manifest %s: each %s entry needs string %r" % (path, field, key)
                )


# --------------------------------------------------------------------------- #
# Scoring + ranking (pure).
# --------------------------------------------------------------------------- #

def projected_total(dimensions):
    """Projected fit on the 0-100 scale: sum(score * weight) / 10."""
    return sum(spec["score"] * spec["weight"] for spec in dimensions.values()) / 10.0


def band_for(total):
    for threshold, label in _BANDS:
        if total >= threshold:
            return label
    return _BANDS[-1][1]


def score_manifest(manifest):
    total = projected_total(manifest["dimensions"])
    return {
        "jd": manifest["jd"],
        "title": manifest["title"],
        "company": manifest["company"],
        "fictional": bool(manifest.get("fictional", False)),
        "projected": total,
        "band": band_for(total),
        "strongest_matches": manifest["strongest_matches"][:3],
        "fatal_gaps": manifest["fatal_gaps"],
        "source_jd": manifest["source_jd"],
    }


def rank(manifests):
    """Score every manifest and order best-first.

    Sort key: projected total descending, then jd id ascending so exact ties are
    broken deterministically (byte-identical ordering for identical inputs).
    """
    scored = [score_manifest(m) for m in manifests]
    scored.sort(key=lambda s: (-s["projected"], s["jd"]))
    return scored


# --------------------------------------------------------------------------- #
# Rendering (deterministic — fixed float format, sorted json keys, no clock).
# --------------------------------------------------------------------------- #

def _fmt(value):
    """Fixed 1-dp float formatting; normalises -0.0 to 0.0 for stable bytes."""
    rounded = round(value + 0.0, 1)
    if rounded == 0.0:
        rounded = 0.0
    return "%.1f" % rounded


def _clip(text, width):
    """Single-line, table-safe cell: collapse pipes/newlines, clip with an ellipsis."""
    flat = " ".join(text.replace("|", "/").split())
    if len(flat) <= width:
        return flat
    return flat[: width - 1].rstrip() + "…"


def render_markdown(ranked):
    out = []
    out.append("# JD reverse-match — ranked pairings")
    out.append("")
    out.append(
        "Projected fit of the knowledge base against %d saved JD(s), best first. "
        "Each score is a PROJECTION from KB coverage — what a CV built from this KB "
        "for the JD could score on the 8 critique dimensions — not a scored CV. "
        "Deterministic: byte-identical for identical manifests; no network, no "
        "timestamps." % len(ranked)
    )
    out.append("")
    out.append("| Rank | JD | Company | Projected | Band | Top match | Top fatal gap |")
    out.append("|---|---|---|---|---|---|---|")
    for i, s in enumerate(ranked, 1):
        top_match = _clip(s["strongest_matches"][0]["jd_req"], 28) if s["strongest_matches"] else "—"
        top_gap = _clip(s["fatal_gaps"][0]["requirement"], 24) if s["fatal_gaps"] else "(none)"
        out.append(
            "| %d | %s | %s | %s | %s | %s | %s |"
            % (i, _clip(s["jd"], 28), _clip(s["company"], 24), _fmt(s["projected"]),
               s["band"], top_match, top_gap)
        )
    out.append("")

    with_gaps = [s for s in ranked if s["fatal_gaps"]]
    if with_gaps:
        out.append("## Fatal gaps to close (per JD)")
        out.append("")
        for s in with_gaps:
            reqs = ", ".join(_clip(g["requirement"], 40) for g in s["fatal_gaps"])
            out.append("- **%s** (%s): %s" % (_clip(s["jd"], 28), s["band"], reqs))
        out.append("")

    out.append(
        "_Projection only. Run `/target-company` then `/make-cv` on the top "
        "pairing(s) to realise the score; close fatal gaps via the build list._"
    )
    out.append("")
    return "\n".join(out) + "\n"


def render_json(ranked):
    payload = {
        "pairings": [
            {
                "rank": i,
                "jd": s["jd"],
                "title": s["title"],
                "company": s["company"],
                "fictional": s["fictional"],
                "projected": round(s["projected"], 1),
                "band": s["band"],
                "strongest_matches": s["strongest_matches"],
                "fatal_gaps": s["fatal_gaps"],
                "source_jd": s["source_jd"],
            }
            for i, s in enumerate(ranked, 1)
        ],
        "count": len(ranked),
    }
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def over_budget(md_text, max_lines):
    """True when the rendered markdown exceeds the one-page line budget."""
    # Count rendered lines (the trailing newline yields one empty element to drop).
    return len(md_text.rstrip("\n").split("\n")) > max_lines


def write_atomic(path, text):
    """Write ``text`` atomically (temp file + os.replace). UTF-8 no BOM, LF."""
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    os.replace(tmp, path)


# --------------------------------------------------------------------------- #
# Profile-aware default manifests dir (lazy — only when --manifests-dir omitted).
# --------------------------------------------------------------------------- #

def _repo_root():
    return os.path.normpath(os.path.join(_HELPERS_DIR, "..", ".."))


def _default_manifests_dir():
    """``users/<active>/output/_match/manifests`` for the active profile.

    profile.py is loaded BY FILE PATH (not ``import profile`` — that name is owned
    by the stdlib profiler) so the validated resolver is reused with no drift and
    no cross-import. Loaded lazily so importing this module for tests (which always
    pass an explicit dir) never touches profile.py.
    """
    spec = importlib.util.spec_from_file_location(
        "cv_match_profile", os.path.join(_HELPERS_DIR, "profile.py")
    )
    profile = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(profile)
    root = _repo_root()
    name = profile.active_profile(root)
    return os.path.join(profile.profile_root(root, name),
                        "output", "_match", "manifests")


# --------------------------------------------------------------------------- #
# CLI.
# --------------------------------------------------------------------------- #

def run(argv):
    parser = argparse.ArgumentParser(
        prog="match_jds.py",
        description="Deterministic JD reverse-matching ranker (P7).",
    )
    parser.add_argument(
        "--manifests-dir", default=None,
        help="directory of *.json match manifests "
             "(default: users/<active>/output/_match/manifests).",
    )
    parser.add_argument("--format", choices=("md", "json"), default="md",
                        help="report format (default: md).")
    parser.add_argument("--out", default=None,
                        help="report path (default: <manifests-dir>/../match_report.md).")
    parser.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES,
                        help="one-page budget for the md report (default %d)." % DEFAULT_MAX_LINES)
    args = parser.parse_args(argv)

    try:
        manifests_dir = args.manifests_dir or _default_manifests_dir()
    except Exception as exc:  # profile resolution failure -> usage error
        sys.stderr.write("manifests-dir error: %s\n" % exc)
        return 2

    try:
        manifests = load_manifests(manifests_dir)
    except ValueError as exc:
        sys.stderr.write("load error: %s\n" % exc)
        return 2

    ranked = rank(manifests)
    md = render_markdown(ranked)
    text = render_json(ranked) if args.format == "json" else md

    out_path = args.out or os.path.join(
        os.path.dirname(os.path.normpath(manifests_dir)), "match_report.md"
    )
    write_atomic(out_path, text)
    sys.stdout.write("wrote %s (%d pairing(s))\n" % (out_path, len(ranked)))

    # Page-budget gate (md only): non-zero exit so a too-long report is caught, but
    # the file is written first so the operator can see what overflowed.
    if args.format == "md" and over_budget(md, args.max_lines):
        sys.stderr.write(
            "page-budget: report is %d lines (> %d) — trim per-JD detail\n"
            % (len(md.rstrip("\n").split("\n")), args.max_lines)
        )
        return 1
    return 0


def main():
    raise SystemExit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
