# -*- coding: utf-8 -*-
"""Tests for ``cv_builder/helpers/char_count.py`` — the kit's rendered-character
budget tool.

These tests pin the *public behaviour* of ``char_count.py`` against the budgets
in ``cv_builder/reference/layout_budgets.md`` (the single source of truth) and
must not contradict ``cv_builder/reference/claims_schema.md``.

Conventions (P1 fences):
- Python stdlib + pytest only; version-portable (local 3.14, CI also 3.12).
- Fully offline and deterministic: no network, no timestamps, no machine paths.
- All test data is minted by the tests themselves (``tmp_path`` for files) —
  never borrowed from real ``output/`` artefacts.
- No shared helper modules with the sibling linter agent (duplication is fine
  in P1).

The module under test is imported by file location so no package ``__init__`` /
``conftest`` / ``pytest.ini`` is required for discovery.
"""

import importlib.util
import os
import subprocess
import sys

import pytest


# --------------------------------------------------------------------------- #
# Module loading (by file location — keeps test discovery config-free).
# --------------------------------------------------------------------------- #

_HELPERS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CHAR_COUNT_PY = os.path.join(_HELPERS_DIR, "char_count.py")


def _load_char_count():
    spec = importlib.util.spec_from_file_location("char_count_under_test", _CHAR_COUNT_PY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cc = _load_char_count()


# Budgets mirrored from layout_budgets.md (A4, 11pt). Kept local on purpose:
# if char_count.py ever drifts from the source-of-truth table, these tests fail
# rather than silently tracking the drift.
BASE_LIMIT = 86
BOLD_PENALTY = 0.25
TIERS = {
    "1L": dict(lo=83, hi=88, hard_max=95, orphan=None),
    "2L": dict(lo=158, hi=172, hard_max=179, orphan=61),
    "3L": dict(lo=236, hi=253, hard_max=264, orphan=61),
}


# --------------------------------------------------------------------------- #
# strip_latex — what a reader actually sees on the page.
# --------------------------------------------------------------------------- #

class TestStripLatex:
    def test_plain_text_unchanged(self):
        assert cc.strip_latex("Plain bullet text") == "Plain bullet text"

    def test_empty_input(self):
        assert cc.strip_latex("") == ""

    def test_whitespace_only_input_strips_to_empty(self):
        assert cc.strip_latex("   \t  ") == ""

    def test_leading_and_trailing_whitespace_trimmed(self):
        assert cc.strip_latex("   padded   ") == "padded"

    def test_multiple_spaces_collapsed_to_one(self):
        assert cc.strip_latex("a    b") == "a b"

    def test_textbf_unwrapped(self):
        assert cc.strip_latex(r"\textbf{Python} pipeline") == "Python pipeline"

    def test_textit_unwrapped(self):
        assert cc.strip_latex(r"\textit{emphasis} here") == "emphasis here"

    def test_underline_unwrapped(self):
        assert cc.strip_latex(r"\underline{name}") == "name"

    def test_emph_unwrapped(self):
        assert cc.strip_latex(r"\emph{key} point") == "key point"

    def test_item_prefix_removed(self):
        assert cc.strip_latex(r"\item bullet body") == "bullet body"

    def test_item_with_empty_brackets_removed(self):
        assert cc.strip_latex(r"\item[] bullet body") == "bullet body"

    def test_href_keeps_link_text_drops_url(self):
        assert cc.strip_latex(r"\href{https://example.com}{link text} rest") == "link text rest"

    def test_superscript_braced(self):
        assert cc.strip_latex(r"area m$^{2}$ here") == "area m2 here"

    def test_superscript_single_char(self):
        assert cc.strip_latex(r"x$^2$ y") == "x2 y"

    def test_subscript_braced(self):
        assert cc.strip_latex(r"H$_{2}$O molecule") == "H2O molecule"

    def test_subscript_single_char(self):
        assert cc.strip_latex(r"a$_1$ b") == "a1 b"

    def test_sim_command_becomes_tilde(self):
        # \sim is replaced by the literal ~ before generic command stripping.
        assert cc.strip_latex(r"\sim 5 records") == "~ 5 records"

    def test_dollar_sim_becomes_tilde(self):
        assert cc.strip_latex(r"$\sim$5 records") == "~5 records"

    def test_textasciitilde_becomes_tilde(self):
        assert cc.strip_latex(r"\textasciitilde 5") == "~ 5"

    def test_math_less_than_unwrapped(self):
        assert cc.strip_latex(r"$<$5 cases") == "<5 cases"

    def test_math_greater_than_unwrapped(self):
        assert cc.strip_latex(r"$>$3 cases") == ">3 cases"

    def test_em_dash_renders_as_single_em_dash_char(self):
        # '---' -> U+2014 (1 rendered char, though ~2x wide on the page).
        out = cc.strip_latex("scope --- outcome")
        assert "—" in out
        assert out == "scope — outcome"
        assert "---" not in out

    def test_en_dash_renders_as_single_en_dash_char(self):
        # '--' -> U+2013 (1 rendered char).
        out = cc.strip_latex("2019--2021 range")
        assert out == "2019–2021 range"

    def test_triple_hyphen_is_em_not_en_plus_hyphen(self):
        # The '---' rule must run before '--'; otherwise we'd get en-dash + hyphen.
        out = cc.strip_latex("a---b")
        assert out == "a—b"
        assert "–" not in out

    def test_unknown_command_stripped(self):
        assert cc.strip_latex(r"\foobar text") == "text"

    def test_remaining_braces_removed(self):
        assert cc.strip_latex("{grouped} word") == "grouped word"

    def test_nested_braces_in_textbf_flattened(self):
        # \textbf{...} is non-greedy: it captures up to the first '}', the rest
        # falls through to the generic brace-stripping. Net result: no braces.
        assert cc.strip_latex(r"\textbf{A {B} C}") == "A B C"

    def test_lone_dollar_signs_removed(self):
        assert cc.strip_latex("cost $5 or $10") == "cost 5 or 10"


class TestStripLatexEscapes:
    """Literal LaTeX escapes render as ONE glyph each — overnight-audit C-2/C-3
    (same glyph-miscount class as the em-dash budget bug). Before the fix '\\&'
    counted as 2 chars and '\\$' was corrupted/deleted by the math-delimiter strip."""

    def test_escaped_ampersand_is_one_glyph(self):
        assert cc.strip_latex(r"Research \& Development") == "Research & Development"

    def test_escaped_percent_hash_underscore_are_one_glyph_each(self):
        assert cc.strip_latex(r"95\% uptime") == "95% uptime"
        assert cc.strip_latex(r"issue \#42 fixed") == "issue #42 fixed"
        assert cc.strip_latex(r"the my\_var flag") == "the my_var flag"

    def test_escaped_dollar_preserved_not_deleted(self):
        # '\$' is a literal dollar; it must survive the bare-$ math-delimiter strip.
        assert cc.strip_latex(r"\$5m budget") == "$5m budget"
        assert cc.strip_latex(r"raised \$2bn revenue") == "raised $2bn revenue"

    def test_escaped_and_math_dollar_coexist(self):
        # Bare $...$ is math (removed); \$ is literal (kept).
        assert cc.strip_latex(r"\$5 over $x$") == "$5 over x"

    def test_escape_glyph_lengths(self):
        # The whole point: rendered length counts each escape as 1, not 2.
        assert len(cc.strip_latex(r"R\&D")) == len("R&D") == 3
        assert len(cc.strip_latex(r"\$5m")) == len("$5m") == 3


class TestStripLatexUnicode:
    """Non-ASCII text must survive unchanged — char counting is on rendered
    text, and ``valid-encoding-is-not-correct-text``: we assert on code points,
    not console rendering."""

    def test_accented_latin_preserved(self):
        out = cc.strip_latex("Sandérs café")
        assert out == "Sandérs café"
        # 'Sandérs'(7) + ' '(1) + 'café'(4) = 12 code points; the accented
        # letters survive as single code points, not as LaTeX escapes.
        assert len(out) == 12

    def test_accented_text_inside_textbf(self):
        assert cc.strip_latex(r"\textbf{Zürich}".replace(r"ü", "ü")) == "Zürich"

    def test_emoji_preserved_as_single_code_point(self):
        out = cc.strip_latex("ship \U0001F680 it")
        assert out == "ship \U0001F680 it"
        # 'ship'(4) + ' '(1) + rocket(1) + ' '(1) + 'it'(2) = 9 code points;
        # the astral char counts as 1 on a wide CPython build (3.12 / 3.14).
        assert len(out) == 9

    def test_cjk_preserved(self):
        out = cc.strip_latex("你好 world")
        assert out == "你好 world"
        assert len(out) == 8


# --------------------------------------------------------------------------- #
# count_bold_chars — drives the bold-width penalty.
# --------------------------------------------------------------------------- #

class TestCountBoldChars:
    def test_no_bold_is_zero(self):
        assert cc.count_bold_chars("plain text, no bold") == 0

    def test_empty_input_is_zero(self):
        assert cc.count_bold_chars("") == 0

    def test_single_bold_block(self):
        assert cc.count_bold_chars(r"\textbf{Python} pipeline") == len("Python")

    def test_two_bold_blocks_summed(self):
        assert cc.count_bold_chars(r"\textbf{Python} and \textbf{SQL}") == len("Python") + len("SQL")

    def test_empty_bold_block_counts_zero(self):
        assert cc.count_bold_chars(r"\textbf{} nothing") == 0

    def test_other_commands_not_counted(self):
        # Only \textbf counts toward the bold penalty, not \textit/\underline.
        assert cc.count_bold_chars(r"\textit{x} \underline{y}") == 0

    def test_non_greedy_stops_at_first_brace(self):
        # \textbf{A {B}} -> non-greedy capture is 'A {B' = 4 chars.
        assert cc.count_bold_chars(r"\textbf{A {B}}") == len("A {B")


# --------------------------------------------------------------------------- #
# count_em_dashes — each '---' budgets ~2 extra chars of width.
# --------------------------------------------------------------------------- #

class TestCountEmDashes:
    def test_none(self):
        assert cc.count_em_dashes("no dashes here") == 0

    def test_empty_input(self):
        assert cc.count_em_dashes("") == 0

    def test_single(self):
        assert cc.count_em_dashes("scope --- outcome") == 1

    def test_two(self):
        assert cc.count_em_dashes("a --- b --- c") == 2

    def test_en_dash_not_counted(self):
        assert cc.count_em_dashes("2019--2021") == 0

    def test_four_hyphens_counts_one_run(self):
        # re.findall('---', 'a ---- b') finds one non-overlapping match.
        assert cc.count_em_dashes("a ---- b") == 1


# --------------------------------------------------------------------------- #
# classify_bullet — the core budget logic (tiers + status + penalty + orphan).
# --------------------------------------------------------------------------- #

class TestClassifyBulletTiersAndStatus:
    @pytest.mark.parametrize(
        "n, exp_variant, exp_status",
        [
            # 1L tier (hard_max 95)
            (0, "1L", "SHORT"),
            (82, "1L", "SHORT"),     # just below lo
            (83, "1L", "OK"),        # lo boundary -> OK
            (88, "1L", "OK"),        # hi boundary -> OK
            (89, "1L", "NEAR MAX"),  # just over hi
            (95, "1L", "NEAR MAX"),  # hard_max boundary still 1L
            # 2L tier (hard_max 179)
            (96, "2L", "SHORT"),     # just over 1L hard_max
            (157, "2L", "SHORT"),
            (158, "2L", "OK"),
            (172, "2L", "OK"),
            (173, "2L", "NEAR MAX"),
            (179, "2L", "NEAR MAX"),
            # 3L tier (hard_max 264)
            (180, "3L", "SHORT"),
            (235, "3L", "SHORT"),
            (236, "3L", "OK"),
            (253, "3L", "OK"),
            (254, "3L", "NEAR MAX"),
            (264, "3L", "NEAR MAX"),
            # over everything
            (265, "OVER", "OVER LIMIT"),
            (1000, "OVER", "OVER LIMIT"),
        ],
    )
    def test_variant_and_status_at_boundaries(self, n, exp_variant, exp_status):
        variant, status, lo, hi, hard_max, orphan, eff = cc.classify_bullet(n, 0, "cv")
        assert variant == exp_variant
        assert status == exp_status

    def test_tier_limits_match_layout_budgets(self):
        # Each in-range count returns the lo/hi/hard_max/orphan from the SoT table.
        for variant, b in TIERS.items():
            n = b["lo"]  # a count that lands squarely in this tier
            got = cc.classify_bullet(n, 0, "cv")
            assert got[0] == variant
            assert (got[2], got[3], got[4], got[5]) == (b["lo"], b["hi"], b["hard_max"], b["orphan"])

    def test_one_line_has_no_orphan_threshold(self):
        assert cc.classify_bullet(85, 0, "cv")[5] is None

    def test_two_and_three_line_orphan_threshold_is_61(self):
        assert cc.classify_bullet(165, 0, "cv")[5] == 61
        assert cc.classify_bullet(245, 0, "cv")[5] == 61

    def test_over_limit_returns_zeroed_limits_and_no_orphan(self):
        variant, status, lo, hi, hard_max, orphan, eff = cc.classify_bullet(300, 0, "cv")
        assert (variant, status) == ("OVER", "OVER LIMIT")
        assert (lo, hi, hard_max) == (0, 0, 0)
        assert orphan is None


class TestClassifyBulletBoldPenalty:
    def test_zero_bold_effective_equals_base(self):
        assert cc.classify_bullet(80, 0, "cv")[6] == BASE_LIMIT

    @pytest.mark.parametrize("bold", [0, 1, 10, 18, 28, 40])
    def test_effective_limit_formula(self, bold):
        expected = BASE_LIMIT - (BOLD_PENALTY * bold)
        assert cc.classify_bullet(80, bold, "cv")[6] == expected

    def test_penalty_examples_from_layout_budgets(self):
        # 0 bold -> 86; ~10 bold -> 83.5; 28 bold -> 79 (matches the doc table).
        assert cc.classify_bullet(80, 0, "cv")[6] == 86.0
        assert cc.classify_bullet(80, 10, "cv")[6] == 83.5
        assert cc.classify_bullet(80, 28, "cv")[6] == 79.0

    def test_effective_limit_is_independent_of_char_count(self):
        # The penalty depends only on bold_chars, not on the bullet length.
        a = cc.classify_bullet(40, 12, "cv")[6]
        b = cc.classify_bullet(250, 12, "cv")[6]
        assert a == b

    def test_effective_limit_present_even_when_over_limit(self):
        eff = cc.classify_bullet(300, 4, "cv")[6]
        assert eff == BASE_LIMIT - (BOLD_PENALTY * 4)


class TestClassifyBulletFormatAlias:
    """'cv' is the live key; 'resume' is a legacy alias that reuses the SAME A4
    tiers (layout_budgets.md). The format must not change classification."""

    @pytest.mark.parametrize("n", [0, 88, 96, 160, 179, 200, 264, 400])
    def test_resume_and_cv_classify_identically(self, n):
        assert cc.classify_bullet(n, 0, "cv") == cc.classify_bullet(n, 0, "resume")

    @pytest.mark.parametrize("n", [0, 88, 160, 264, 400])
    def test_unknown_format_string_still_uses_a4_tiers(self, n):
        # classify_bullet does not validate fmt; any string yields the A4 tiers.
        assert cc.classify_bullet(n, 0, "xyz") == cc.classify_bullet(n, 0, "cv")


# --------------------------------------------------------------------------- #
# format_one — the human-readable report + variant string.
# --------------------------------------------------------------------------- #

class TestFormatOne:
    def test_returns_report_and_variant(self):
        report, variant = cc.format_one(r"\textbf{Python} pipeline ok", "cv")
        assert isinstance(report, str)
        assert variant == "1L"

    def test_report_counts_rendered_not_raw_chars(self):
        # 'Python pipeline ok' = 18 rendered chars (markup stripped).
        report, _ = cc.format_one(r"\textbf{Python} pipeline ok", "cv")
        assert "18 chars" in report
        assert "Rendered: Python pipeline ok" in report

    def test_report_shows_bold_effective_limit_when_bold_present(self):
        report, _ = cc.format_one(r"\textbf{Python} ok", "cv")
        assert "Bold: 6 chars" in report
        # effective = 86 - 0.25*6 = 84.5 -> formatted with :.0f -> 84.
        assert "effective limit/line: 84" in report

    def test_report_omits_bold_line_when_no_bold(self):
        report, _ = cc.format_one("plain bullet text only", "cv")
        assert "Bold:" not in report

    def test_report_shows_em_dash_line_when_present(self):
        report, _ = cc.format_one("scope --- outcome here", "cv")
        assert "Em-dashes: 1" in report

    def test_report_omits_em_dash_line_when_absent(self):
        report, _ = cc.format_one("scope to outcome here", "cv")
        assert "Em-dashes:" not in report

    def test_format_label_uppercased_in_report(self):
        report, _ = cc.format_one("plain bullet", "resume")
        assert "RESUME" in report

    def test_over_limit_bullet_reports_over(self):
        long_bullet = "x" * 300
        report, variant = cc.format_one(long_bullet, "cv")
        assert variant == "OVER"
        assert "OVER LIMIT" in report


# --------------------------------------------------------------------------- #
# extract_items — pull \item lines out of a .tex source.
# --------------------------------------------------------------------------- #

class TestExtractItems:
    def test_empty_source_yields_no_items(self):
        assert cc.extract_items("") == []

    def test_source_without_items_yields_nothing(self):
        assert cc.extract_items("intro\nbody text\nno bullets") == []

    def test_extracts_plain_item_lines(self):
        src = "intro\n\\item first\n\\item second\n"
        assert cc.extract_items(src) == ["\\item first", "\\item second"]

    def test_item_with_empty_brackets(self):
        src = "\\item[] only one"
        assert cc.extract_items(src) == ["\\item[] only one"]

    def test_leading_whitespace_is_stripped_from_match(self):
        src = "    \\item indented body  "
        assert cc.extract_items(src) == ["\\item indented body"]

    def test_non_item_lines_ignored(self):
        src = "\\begin{itemize}\ntext\n\\item kept\n\\end{itemize}"
        assert cc.extract_items(src) == ["\\item kept"]


@pytest.mark.xfail(
    reason="BUG: extract_items uses startswith('\\\\item'), which also matches "
    "\\itemize / \\itemsep / \\item-prefixed control words. char_count.py:128. "
    "Surfaced, not fixed (P1 tests-builder may not fix code).",
    strict=True,
)
def test_extract_items_should_not_match_itemize_environment():
    # '\itemize' is an environment opener, not a bullet, but the current
    # startswith check captures it. A correct implementation would require a
    # word boundary after '\item'.
    src = "\\itemize start\n\\item real bullet"
    assert cc.extract_items(src) == ["\\item real bullet"]


# --------------------------------------------------------------------------- #
# CLI (main) — exercised via subprocess so argparse/stdin/exit codes are real.
# UTF-8 is forced for deterministic output across OS + Python 3.12/3.14.
# --------------------------------------------------------------------------- #

def _run_cli(args, stdin_text=None):
    """Run char_count.py as a subprocess. Returns CompletedProcess.

    Forces UTF-8 I/O so the suite is deterministic on Windows (cp1252) and
    Linux CI alike — offline, no machine-specific state.
    """
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return subprocess.run(
        [sys.executable, "-X", "utf8", _CHAR_COUNT_PY, *args],
        input=stdin_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )


class TestCli:
    def test_positional_bullet_default_cv(self):
        result = _run_cli(["Plain bullet here"])
        assert result.returncode == 0
        assert "1L CV" in result.stdout
        assert "Rendered: Plain bullet here" in result.stdout

    def test_raw_positional_prints_only_count(self):
        result = _run_cli(["--raw", "Plain bullet"])
        assert result.returncode == 0
        assert result.stdout.strip() == str(len("Plain bullet"))

    def test_raw_counts_rendered_chars_not_markup(self):
        result = _run_cli(["--raw", r"\textbf{Python} ok"])
        assert result.returncode == 0
        assert result.stdout.strip() == str(len("Python ok"))

    def test_format_resume_alias_accepted(self):
        result = _run_cli(["-f", "resume", "--raw", "abc"])
        assert result.returncode == 0
        assert result.stdout.strip() == "3"

    def test_stdin_raw_one_count_per_nonblank_line(self):
        result = _run_cli(["--raw"], stdin_text="one line\n\nsecond line\n")
        assert result.returncode == 0
        # Blank line is skipped; one count per remaining line.
        assert result.stdout.split() == ["8", "11"]

    def test_unknown_flag_is_rejected_with_exit_2(self):
        result = _run_cli(["--definitely-not-a-flag", "x"])
        assert result.returncode == 2

    def test_invalid_format_choice_rejected(self):
        result = _run_cli(["-f", "letter", "x"])
        assert result.returncode == 2

    def test_unicode_bullet_round_trips_through_cli(self):
        result = _run_cli(["--raw", "café résumé"])
        assert result.returncode == 0
        assert result.stdout.strip() == str(len("café résumé"))


class TestCliTexFile:
    """File mode: test .tex inputs are MINTED in tmp_path, never borrowed from
    real output/ artefacts (test-helpers-own-throwaway-data)."""

    def _write_tex(self, tmp_path, body):
        p = tmp_path / "sample.tex"
        p.write_text(body, encoding="utf-8")
        return p

    def test_tex_file_reports_each_bullet(self, tmp_path):
        body = (
            "\\begin{itemize}\n"
            "\\item Built a data pipeline processing daily records\n"
            "\\item Co-built a committee portal used by the committee\n"
            "\\end{itemize}\n"
        )
        tex = self._write_tex(tmp_path, body)
        result = _run_cli([str(tex)])
        assert result.returncode == 0
        assert "Found 2 bullets" in result.stdout
        assert "Bullet 1:" in result.stdout
        assert "Bullet 2:" in result.stdout
        assert "Total rendered lines:" in result.stdout

    def test_tex_file_with_no_items_reports_none(self, tmp_path):
        tex = self._write_tex(tmp_path, "\\section{Experience}\nNo bullets at all.\n")
        result = _run_cli([str(tex)])
        assert result.returncode == 0
        assert "No \\item lines found." in result.stdout

    def test_tex_file_raw_prints_count_per_bullet(self, tmp_path):
        body = "\\item " + ("a" * 40) + "\n\\item " + ("b" * 50) + "\n"
        tex = self._write_tex(tmp_path, body)
        result = _run_cli(["--raw", str(tex)])
        assert result.returncode == 0
        # Two counts emitted, one per bullet (header line also printed).
        nums = [tok for tok in result.stdout.split() if tok.isdigit()]
        assert "40" in nums
        assert "50" in nums

    def test_tex_file_read_as_utf8_under_legacy_console_encoding(self, tmp_path):
        # Regression (overnight-audit C-1): char_count must read the .tex as UTF-8
        # even when the platform default is cp1252 (stock Windows shell). Run the
        # CLI WITHOUT forcing UTF-8 mode; --raw prints only a number, so stdout
        # encoding is irrelevant — the bug is purely the INPUT open() encoding.
        # (On Linux CI open() defaults to UTF-8 anyway, so this is a benign pass
        # there; on Windows it fails before the fix and passes after.)
        body = "\\item built a 你好 pipeline serving the whole team well\n"
        tex = tmp_path / "u.tex"
        tex.write_text(body, encoding="utf-8")
        env = dict(os.environ)
        env["PYTHONUTF8"] = "0"  # legacy: open() uses the locale default (cp1252 on Windows)
        env.pop("PYTHONIOENCODING", None)
        result = subprocess.run(
            [sys.executable, _CHAR_COUNT_PY, "--raw", str(tex)],
            capture_output=True, text=True, encoding="utf-8", env=env,
        )
        assert result.returncode == 0, result.stderr
        expected = len(cc.strip_latex("\\item built a 你好 pipeline serving the whole team well"))
        # The .tex --raw path also prints a "Found N bullets" header; pull the count.
        nums = [tok for tok in result.stdout.split() if tok.isdigit()]
        assert str(expected) in nums, result.stdout

    def test_non_utf8_tex_fails_cleanly_not_traceback(self, tmp_path):
        # Regression (morning-audit NEW-2): a .tex that is genuinely NOT UTF-8 (e.g.
        # saved as cp1252, with £ = byte 0xA3) must fail with a clear message and a
        # non-zero exit — not a raw UnicodeDecodeError traceback. UTF-8 is the correct
        # canonical encoding (overnight-audit C-1); this only makes the rejection clean.
        # Before the fix: uncaught UnicodeDecodeError → exit 1 with a traceback.
        tex = tmp_path / "cp.tex"
        tex.write_bytes("\\item raised \xa3500k for the whole team this year ok\n".encode("cp1252"))
        result = subprocess.run(
            [sys.executable, _CHAR_COUNT_PY, str(tex)],
            capture_output=True, text=True, encoding="utf-8",
        )
        assert result.returncode == 2, result.stdout
        assert "not valid UTF-8" in result.stderr
        assert "Traceback" not in result.stderr
