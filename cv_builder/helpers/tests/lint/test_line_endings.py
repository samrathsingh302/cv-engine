"""Line-ending invariance for the honesty linters (morning-2026-06-16 #6).

The linters read files as UTF-8 and split on "\n", and their CLI emits
byte-identical output by design — but every other test writes LF-only fixtures, so
the CRLF path (Git's autocrlf checkout on Windows; a committed CRLF file) was
unguarded. A trailing "\r" left on each line must not move a finding's line/rule or
change its message. These tests write the SAME content as LF and as CRLF and assert
the findings are identical (path normalised away — it is the only field that varies
with the temp dir, never with the line ending).

CR-only ("\r", classic-Mac) is deliberately NOT asserted: nothing in this kit emits
it, .gitattributes pins LF, and "\r"-only would collapse a file to one logical line
under split("\n") — out of scope for this guard, which targets the real CRLF risk.
A .gitattributes (text eol=lf) is the primary fix; these tests lock the behaviour.
"""

import pytest

from _runner import run_json


def _findings(doc):
    """Findings as ending-agnostic (line, rule, message) tuples; drop the temp path."""
    return sorted((f["line"], f["rule"], f["message"]) for f in doc["findings"])


# Deliberately dirty content so each linter has real findings to compare across
# endings. Trailing-content lines (the bullets) are where a stray "\r" would bite.
_FP_DIRTY = (
    "# Heading\n"
    "\n"
    "- Built a seamless solution to leverage synergy.\n"
    "- Delivered a robust, cutting-edge platform.\n"
)
_PV_DIRTY = (
    "# Heading\n"
    "\n"
    "- Built the backend with the engineering team.\n"
    "- Shipped 484 comprehensive tests and 40,000 lines in the codebase.\n"
)


@pytest.mark.parametrize("eol", ["\n", "\r\n"])
def test_fingerprint_findings_identical_across_endings(fp_mod, writer, eol):
    lf = writer("output/cv_lf.md", _FP_DIRTY)
    other = writer("output/cv_eol.md", _FP_DIRTY.replace("\n", eol))
    code_lf, doc_lf = run_json(fp_mod, [lf])
    code_o, doc_o = run_json(fp_mod, [other])
    assert _findings(doc_lf), "fixture should produce findings"
    assert _findings(doc_o) == _findings(doc_lf), eol
    assert code_o == code_lf


@pytest.mark.parametrize("eol", ["\n", "\r\n"])
def test_provenance_findings_identical_across_endings(pv_mod, writer, eol):
    today = ["--today", "2026-06"]
    lf = writer("output/cv_lf.md", _PV_DIRTY)
    other = writer("output/cv_eol.md", _PV_DIRTY.replace("\n", eol))
    code_lf, doc_lf = run_json(pv_mod, [lf, *today])
    code_o, doc_o = run_json(pv_mod, [other, *today])
    assert _findings(doc_lf), "fixture should produce findings"
    assert _findings(doc_o) == _findings(doc_lf), eol
    assert code_o == code_lf
