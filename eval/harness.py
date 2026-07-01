#!/usr/bin/env python
"""
harness.py — deterministic eval harness for the CV-tailoring kit (P4).

Loads the score manifests in ``eval/scores/*.json`` (captured critique results,
turned into auditable data — NOT an LLM call at runtime), computes weighted
totals per case, the mean per-dimension delta (after - before) across the P2
corpus, and writes ``eval/report.md``.

Calibration first (the P4 done-gate): the rubric scorer is proved against
the calibration reference manifest (the one flagged ``calibration_reference``,
whose own ``calibration_target`` is the known weighted total ±2) and at least one
seeded known-bad CV (a corpus 'before' score, which must land in a low band <60)
BEFORE any corpus aggregation. If calibration fails, the harness writes nothing
and exits non-zero.

The calibration reference is resolved purely from the manifests present — no
hardcoded case name — so the same code calibrates the private instance against
its private reference and a public clone against a public fictional reference.
Exactly one reference must resolve in a tree (fail-closed on zero or multiple).

House conventions (match cv_builder/helpers/*):
- Python stdlib only; version-portable (local 3.14, CI also 3.12).
- Fully offline, deterministic, fail-closed. No network, no wall-clock, no
  timestamps, no machine paths in output.
- Output is byte-identical for identical inputs: sorted keys, fixed float
  formatting, atomic write (temp file + os.replace).
- UTF-8 no BOM; LF newlines; repo-relative source citations.

CLI:
  python eval/harness.py                 full run -> writes eval/report.md
  python eval/harness.py --check         calibration only; non-zero on failure
  python eval/harness.py --format json   emit the report as JSON instead of md

Exit codes: 0 ok · 1 calibration failed · 2 usage/load error.
"""

import argparse
import json
import os
import sys


# --------------------------------------------------------------------------- #
# Paths (repo-relative; resolved from this file's location, config-free).
# --------------------------------------------------------------------------- #

_EVAL_DIR = os.path.dirname(os.path.abspath(__file__))


def _default_scores_dir():
    """Resolve the no-arg default scores directory, identity-agnostic.

    The private instance carries ``eval/scores`` (its calibration manifests);
    the public engine clone carves that out and ships only the fictional
    ``eval/fixtures/scores``. Prefer the private dir when present, else fall
    back to the public fixtures — the same resolution the tests use — so
    ``python eval/harness.py`` (no args) works in BOTH trees. If neither
    exists yet, return the private path so load_manifests fails closed on it.
    """
    candidates = (
        os.path.join(_EVAL_DIR, "scores"),
        os.path.join(_EVAL_DIR, "fixtures", "scores"),
    )
    for d in candidates:
        if os.path.isdir(d):
            return d
    return candidates[0]


_SCORES_DIR = _default_scores_dir()
_REPORT_PATH = os.path.join(_EVAL_DIR, "report.md")

# Calibration constants (P4 done-gate). The target is NOT a module
# constant: each reference manifest declares its own ``calibration_target`` (the
# known weighted total), so the harness carries no instance-specific value.
CALIBRATION_TOLERANCE = 2.0
KNOWN_BAD_BAND = 60.0  # a seeded known-bad 'before' must score strictly below this.

# Score-band labels (critique_framework.md Part 2 'Overall score interpretation').
_BANDS = (
    (85.0, "submit"),
    (80.0, "strong"),
    (75.0, "good-foundation"),
    (70.0, "first-draft"),
    (0.0, "fundamental-issues"),
)


# --------------------------------------------------------------------------- #
# Loading + scoring (pure functions — no I/O side effects except load_manifests).
# --------------------------------------------------------------------------- #

def load_manifests(scores_dir=_SCORES_DIR):
    """Load every ``*.json`` manifest, sorted by case id for determinism.

    Fail-closed: a missing dir, an unreadable file, malformed JSON, a missing
    required field, or weights that do not sum to 100 all raise ValueError.
    """
    if not os.path.isdir(scores_dir):
        raise ValueError("scores directory not found: %s" % scores_dir)

    paths = sorted(
        os.path.join(scores_dir, n)
        for n in os.listdir(scores_dir)
        if n.endswith(".json")
    )
    if not paths:
        raise ValueError("no score manifests found in %s" % scores_dir)

    manifests = []
    for path in paths:
        with open(path, encoding="utf-8") as fh:
            try:
                data = json.load(fh)
            except json.JSONDecodeError as exc:
                raise ValueError("malformed manifest %s: %s" % (path, exc))
        _validate(data, path)
        manifests.append(data)

    manifests.sort(key=lambda m: m["case"])
    cases = [m["case"] for m in manifests]
    if len(set(cases)) != len(cases):
        raise ValueError("duplicate case id across manifests: %s" % cases)
    return manifests


def _validate(data, path):
    for field in ("case", "genre", "no_target", "dimensions", "source"):
        if field not in data:
            raise ValueError("manifest %s missing required field %r" % (path, field))
    if not isinstance(data["no_target"], bool):
        raise ValueError("manifest %s: no_target must be a bool" % path)
    dims = data["dimensions"]
    if not isinstance(dims, dict) or not dims:
        raise ValueError("manifest %s: dimensions must be a non-empty object" % path)
    total_weight = 0
    for name, spec in dims.items():
        for key in ("weight", "before", "after"):
            if key not in spec:
                raise ValueError(
                    "manifest %s dimension %r missing %r" % (path, name, key)
                )
        total_weight += spec["weight"]
    # Weights are percentages: a manifest's set must sum to 100 (the re-weighting
    # in a no_target manifest still redistributes to a full 100, never drops it).
    if abs(total_weight - 100) > 1e-9:
        raise ValueError(
            "manifest %s: dimension weights sum to %s, expected 100"
            % (path, total_weight)
        )
    # A calibration reference must declare its known total so the harness needs
    # no instance-specific constant (de-identification: no hardcoded case name).
    if data.get("calibration_reference"):
        target = data.get("calibration_target")
        if not isinstance(target, (int, float)) or isinstance(target, bool):
            raise ValueError(
                "manifest %s: calibration_reference requires a numeric "
                "calibration_target" % path
            )


def weighted_total(dimensions, field):
    """Weighted score on the 0-100 scale for the given field ('before'/'after').

    Each dimension scores 0-10 with a percentage weight; the weights sum to 100,
    so sum(score * weight) / 10 yields the familiar 0-100 critique total.
    """
    return sum(spec[field] * spec["weight"] for spec in dimensions.values()) / 10.0


def band_for(total):
    for threshold, label in _BANDS:
        if total >= threshold:
            return label
    return _BANDS[-1][1]


def score_case(manifest):
    dims = manifest["dimensions"]
    before = weighted_total(dims, "before")
    after = weighted_total(dims, "after")
    return {
        "case": manifest["case"],
        "genre": manifest["genre"],
        "no_target": manifest["no_target"],
        "source": manifest["source"],
        "before": before,
        "after": after,
        "delta": after - before,
        "band_before": band_for(before),
        "band_after": band_for(after),
    }


def reference_manifest(manifests):
    """The calibration reference: the single manifest flagged
    ``calibration_reference``. Fail-closed — exactly one must resolve.

    Returns the reference, or None when none is flagged (calibrate reports a
    FAIL in that case). Raises ValueError when more than one is flagged, so a
    tree can never silently calibrate against an ambiguous anchor.
    """
    flagged = [m for m in manifests if m.get("calibration_reference")]
    if len(flagged) > 1:
        raise ValueError(
            "multiple calibration_reference manifests: %s"
            % sorted(m["case"] for m in flagged)
        )
    return flagged[0] if flagged else None


def mean_dimension_deltas(manifests):
    """Mean per-dimension delta (after - before) across the *corpus* only.

    The calibration reference is excluded from corpus aggregation — it is the
    verifier's proof point, not a /improve-cv before/after case. A dimension's
    mean is taken over the manifests in which it appears.
    """
    ref = reference_manifest(manifests)
    sums = {}
    counts = {}
    for manifest in manifests:
        if manifest is ref:
            continue
        for name, spec in manifest["dimensions"].items():
            sums[name] = sums.get(name, 0.0) + (spec["after"] - spec["before"])
            counts[name] = counts.get(name, 0) + 1
    return {name: (sums[name] / counts[name], counts[name]) for name in sums}


# --------------------------------------------------------------------------- #
# Calibration gate (runs before any corpus aggregation).
# --------------------------------------------------------------------------- #

def calibrate(manifests):
    """Return (ok, lines) where lines explain each calibration assertion.

    Assertions (P4 done-gate):
      1. The reference manifest's weighted 'after' total = its declared
         ``calibration_target`` ±2.
      2. At least one seeded known-bad (a corpus 'before' total) lands <60.
    """
    lines = []

    ok_ref = False
    ref = reference_manifest(manifests)
    if ref is None:
        lines.append("FAIL: no calibration reference manifest present")
    else:
        ref_after = weighted_total(ref["dimensions"], "after")
        target = ref["calibration_target"]
        delta = abs(ref_after - target)
        ok_ref = delta <= CALIBRATION_TOLERANCE
        lines.append(
            "%s: %s after = %s vs known %s (|d|=%s, tol %s)"
            % (
                "PASS" if ok_ref else "FAIL",
                ref["case"],
                _fmt(ref_after),
                _fmt(target),
                _fmt(delta),
                _fmt(CALIBRATION_TOLERANCE),
            )
        )

    # Seeded known-bad: any corpus 'before' total in the low band.
    bad_cases = sorted(
        m["case"]
        for m in manifests
        if m is not ref
        and weighted_total(m["dimensions"], "before") < KNOWN_BAD_BAND
    )
    ok_bad = bool(bad_cases)
    lines.append(
        "%s: %d seeded known-bad before-score(s) < %s%s"
        % (
            "PASS" if ok_bad else "FAIL",
            len(bad_cases),
            _fmt(KNOWN_BAD_BAND),
            (" (" + ", ".join(bad_cases) + ")") if bad_cases else "",
        )
    )

    return (ok_ref and ok_bad), lines


# --------------------------------------------------------------------------- #
# Report rendering (deterministic — sorted keys, fixed float format, no clock).
# --------------------------------------------------------------------------- #

def _fmt(value):
    """Fixed 1-dp float formatting; normalises -0.0 to 0.0 for stable bytes."""
    rounded = round(value + 0.0, 1)
    if rounded == 0.0:
        rounded = 0.0
    return "%.1f" % rounded


def build_report_data(manifests):
    calib_ok, calib_lines = calibrate(manifests)
    ref = reference_manifest(manifests)
    corpus = [m for m in manifests if m is not ref]
    cases = [score_case(m) for m in corpus]
    deltas = mean_dimension_deltas(manifests)
    return {
        "calibration": {"ok": calib_ok, "lines": calib_lines},
        "calibration_reference": score_case(ref),
        "corpus": cases,
        "corpus_mean_delta": (
            sum(c["delta"] for c in cases) / len(cases) if cases else 0.0
        ),
        "dimension_deltas": deltas,
    }


def render_markdown(data):
    out = []
    out.append("# CV-kit eval report")
    out.append("")
    out.append(
        "Deterministic rubric-scorer run over captured critique results "
        "(`eval/scores/*.json`). No network, no timestamps; byte-identical for "
        "identical inputs."
    )
    out.append("")

    out.append("## Calibration (gate — run before corpus aggregation)")
    out.append("")
    for line in data["calibration"]["lines"]:
        out.append("- %s" % line)
    out.append("")
    out.append("Result: **%s**" % ("PASS" if data["calibration"]["ok"] else "FAIL"))
    out.append("")
    ref = data["calibration_reference"]
    out.append(
        "Reference `%s`: before %s -> after %s (delta %s); source `%s`."
        % (
            ref["case"],
            _fmt(ref["before"]),
            _fmt(ref["after"]),
            _fmt(ref["delta"]),
            ref["source"],
        )
    )
    out.append("")

    out.append("## Corpus before/after (weighted total, 0-100)")
    out.append("")
    out.append("| Case | Genre | No target | Before | After | Delta | After band |")
    out.append("|---|---|---|---|---|---|---|")
    for c in data["corpus"]:
        out.append(
            "| %s | %s | %s | %s | %s | %s | %s |"
            % (
                c["case"],
                c["genre"],
                "yes" if c["no_target"] else "no",
                _fmt(c["before"]),
                _fmt(c["after"]),
                _fmt(c["delta"]),
                c["band_after"],
            )
        )
    out.append(
        "| **mean** | | | | | **%s** | |" % _fmt(data["corpus_mean_delta"])
    )
    out.append("")

    out.append("## Mean per-dimension delta (after - before, corpus)")
    out.append("")
    out.append("| Dimension | Mean delta | Cases |")
    out.append("|---|---|---|")
    for name in sorted(data["dimension_deltas"]):
        mean, count = data["dimension_deltas"][name]
        out.append("| %s | %s | %d |" % (name, _fmt(mean), count))
    out.append("")
    out.append(
        "Deltas are mean per-dimension /10 movement across the corpus; a "
        "dimension's mean is over the cases in which it appears."
    )
    out.append("")
    return "\n".join(out) + "\n"


def render_json(data):
    payload = {
        "calibration": data["calibration"],
        "calibration_reference": _round_case(data["calibration_reference"]),
        "corpus": [_round_case(c) for c in data["corpus"]],
        "corpus_mean_delta": round(data["corpus_mean_delta"], 1),
        "dimension_deltas": {
            name: {"mean_delta": round(mean, 1), "cases": count}
            for name, (mean, count) in data["dimension_deltas"].items()
        },
    }
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _round_case(case):
    out = dict(case)
    for key in ("before", "after", "delta"):
        out[key] = round(out[key], 1)
    return out


def write_atomic(path, text):
    """Write ``text`` to ``path`` atomically (temp file + os.replace).

    UTF-8 no BOM, LF newlines. The temp file lives in the target dir so
    os.replace is a same-filesystem rename.
    """
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    os.replace(tmp, path)


# --------------------------------------------------------------------------- #
# CLI.
# --------------------------------------------------------------------------- #

def run(argv):
    parser = argparse.ArgumentParser(
        prog="harness.py",
        description="Deterministic CV-kit eval harness (P4).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="calibration only; write nothing; non-zero exit on failure.",
    )
    parser.add_argument(
        "--format",
        choices=("md", "json"),
        default="md",
        help="report format for a full run (default: md).",
    )
    parser.add_argument(
        "--scores-dir",
        default=_SCORES_DIR,
        help="directory of score manifests (default: eval/scores).",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="report output path (default: eval/report.md).",
    )
    args = parser.parse_args(argv)

    try:
        manifests = load_manifests(args.scores_dir)
    except ValueError as exc:
        sys.stderr.write("load error: %s\n" % exc)
        return 2

    calib_ok, calib_lines = calibrate(manifests)

    if args.check:
        for line in calib_lines:
            sys.stdout.write(line + "\n")
        sys.stdout.write("calibration %s\n" % ("PASS" if calib_ok else "FAIL"))
        return 0 if calib_ok else 1

    # Full run: calibration gates corpus aggregation. On failure, write nothing.
    if not calib_ok:
        for line in calib_lines:
            sys.stderr.write(line + "\n")
        sys.stderr.write("calibration FAIL — wrote nothing\n")
        return 1

    data = build_report_data(manifests)
    text = render_json(data) if args.format == "json" else render_markdown(data)
    out_path = args.out or _REPORT_PATH
    write_atomic(out_path, text)
    sys.stdout.write("wrote %s\n" % out_path)
    return 0


def main():
    raise SystemExit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
