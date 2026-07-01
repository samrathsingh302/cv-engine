#!/usr/bin/env python
"""
Count rendered characters in LaTeX CV bullets.
Strips LaTeX markup to show what a reader actually sees on the page.

Budgets are the A4 11pt limits defined in
`cv_builder/reference/layout_budgets.md` (the single source of truth). If a limit
changes, change it there AND here, nowhere else. The `cv` format is the live A4
geometry; `resume` is retained only for backward compatibility and reuses the
same A4 tiers.

Usage:
  python char_count.py "\\textbf{Python} pipeline processing 2M records"
  echo "bullet text" | python char_count.py
  python char_count.py -f cv output/file.tex
  python char_count.py --raw "bullet text"               # just the number
"""

import re
import sys
import argparse


def strip_latex(text):
    """Strip LaTeX markup to get rendered text."""
    # Protect literal LaTeX escapes (\& \% \# \_ \$) BEFORE any command/math/brace
    # stripping. Each renders as ONE glyph, but otherwise: '\&' (and \% \# \_)
    # survives the generic \command strip as a backslash+char and counts as 2;
    # '\$' loses its '$' to the bare math-delimiter strip below, corrupting or
    # deleting dollar figures ('\$5m' -> '\5m', '\$bn' -> ''). Same glyph-miscount
    # class as the prior em-dash budget bug. Restored to the single glyph at the end.
    _ESCAPES = (('\\&', '&'), ('\\%', '%'), ('\\#', '#'), ('\\_', '_'), ('\\$', '$'))
    # Sentinels are Private-Use-Area code points (U+E000+) that cannot occur in
    # real CV text and survive every strip step below as a single opaque char —
    # so a literal control byte in the input can never collide with a placeholder.
    for i, (esc, _glyph) in enumerate(_ESCAPES):
        text = text.replace(esc, chr(0xE000 + i))
    # Remove \item[] prefix
    text = re.sub(r'\\item\s*(\[\s*\])?\s*', '', text)
    # \href{url}{text} -> text
    text = re.sub(r'\\href\{[^}]*\}\{([^}]*)\}', r'\1', text)
    # \textbf{X} -> X
    text = re.sub(r'\\textbf\{([^}]*)\}', r'\1', text)
    # \textit{X} -> X
    text = re.sub(r'\\textit\{([^}]*)\}', r'\1', text)
    # \underline{X} -> X
    text = re.sub(r'\\underline\{([^}]*)\}', r'\1', text)
    # \emph{X} -> X
    text = re.sub(r'\\emph\{([^}]*)\}', r'\1', text)
    # Superscripts: $^{2}$ or $^2$ -> content
    text = re.sub(r'\$\^\{([^}]*)\}\$', r'\1', text)
    text = re.sub(r'\$\^(.)\$', r'\1', text)
    # Subscripts: $_{2}$ or $_2$ -> content
    text = re.sub(r'\$_\{([^}]*)\}\$', r'\1', text)
    text = re.sub(r'\$_(.)\$', r'\1', text)
    # \sim -> 1 char (~)
    text = text.replace('$\\sim$', '~')
    text = text.replace('\\sim', '~')
    text = text.replace('\\textasciitilde', '~')
    # $<$ $>$ -> 1 char
    text = re.sub(r'\$([<>])\$', r'\1', text)
    # --- -> em-dash (1 char but ~2x wide)
    text = text.replace('---', '\u2014')
    # -- -> en-dash (1 char)
    text = text.replace('--', '\u2013')
    # Remove remaining $ (math mode delimiters)
    text = text.replace('$', '')
    # Remove remaining \commands
    text = re.sub(r'\\[a-zA-Z]+\s*', '', text)
    # Remove remaining braces
    text = text.replace('{', '').replace('}', '')
    # Collapse multiple spaces
    text = re.sub(r'  +', ' ', text)
    # Restore the protected literal escapes as their single rendered glyph.
    for i, (_esc, glyph) in enumerate(_ESCAPES):
        text = text.replace(chr(0xE000 + i), glyph)
    return text.strip()


def count_bold_chars(text):
    """Count characters inside \\textbf{} commands."""
    return sum(len(m) for m in re.findall(r'\\textbf\{([^}]*)\}', text))


def count_em_dashes(text):
    """Count em-dashes (---) which render ~2x wide."""
    return len(re.findall(r'---', text))


def classify_bullet(char_count, bold_chars, fmt):
    """Classify bullet into variant and check limits.

    Tiers are the A4 11pt budgets from layout_budgets.md. Both 'cv' (live) and
    'resume' (legacy alias) use the same A4 geometry.
    """
    # A4, 11pt: effective_limit = 86 - (0.25 x bold_chars)
    base = 86
    penalty = 0.25
    tiers = [
        ('1L', 83, 88, 95, None),
        ('2L', 158, 172, 179, 61),
        ('3L', 236, 253, 264, 61),
    ]

    effective = base - (penalty * bold_chars)

    for variant, lo, hi, hard_max, orphan in tiers:
        if char_count <= hard_max:
            if char_count < lo:
                status = 'SHORT'
            elif char_count <= hi:
                status = 'OK'
            else:
                status = 'NEAR MAX'
            return variant, status, lo, hi, hard_max, orphan, effective

    return 'OVER', 'OVER LIMIT', 0, 0, 0, None, effective


def format_one(raw, fmt):
    """Format analysis for a single bullet."""
    rendered = strip_latex(raw)
    n = len(rendered)
    bold = count_bold_chars(raw)
    em = count_em_dashes(raw)

    variant, status, lo, hi, hard_max, orphan, eff = classify_bullet(n, bold, fmt)

    parts = [f"  {n:3d} chars | {variant} {fmt.upper()} | {status} (target {lo}-{hi}, max {hard_max})"]
    if bold:
        parts.append(f"  Bold: {bold} chars -> effective limit/line: {eff:.0f}")
    if em:
        parts.append(f"  Em-dashes: {em} (each ~2x wide, budget +{em} extra)")
    parts.append(f"  Rendered: {rendered}")
    return '\n'.join(parts), variant


def extract_items(text):
    """Extract \\item lines from .tex source."""
    items = []
    for line in text.split('\n'):
        s = line.strip()
        if s.startswith('\\item'):
            items.append(s)
    return items


def main():
    parser = argparse.ArgumentParser(
        description='Count rendered characters in LaTeX CV bullets')
    parser.add_argument('input', nargs='?',
                        help='Bullet text or .tex file path')
    parser.add_argument('-f', '--format', choices=['resume', 'cv'],
                        default='cv', help='Document format (default: cv; resume is a legacy alias)')
    parser.add_argument('--raw', action='store_true',
                        help='Output only char count (for scripting)')
    args = parser.parse_args()

    if args.input and args.input.endswith('.tex'):
        # Explicit UTF-8: .tex sources are UTF-8, but the platform default is
        # cp1252 on a stock Windows shell, which mojibakes or crashes on any glyph
        # outside cp1252 (CJK name, emoji, some accents) and miscounts the budget.
        try:
            with open(args.input, encoding='utf-8') as f:
                items = extract_items(f.read())
        except UnicodeDecodeError as exc:
            # A .tex that is not valid UTF-8 (e.g. saved as cp1252) is a mis-encoded
            # source, not a budget to count: refuse with a clear message instead of a
            # raw traceback, and exit non-zero so a caller/script notices.
            print(f"Error: {args.input} is not valid UTF-8 ({exc}); re-save it as UTF-8.",
                  file=sys.stderr)
            sys.exit(2)
        if not items:
            print("No \\item lines found.")
            return
        total_lines = 0
        print(f"Found {len(items)} bullets ({args.format} format):\n")
        for i, item in enumerate(items, 1):
            if args.raw:
                print(len(strip_latex(item)))
            else:
                report, variant = format_one(item, args.format)
                print(f"Bullet {i}:")
                print(report)
                print()
                if variant not in ('OVER',):
                    total_lines += int(variant[0])
        if not args.raw:
            print(f"Total rendered lines: {total_lines}")
    elif args.input:
        if args.raw:
            print(len(strip_latex(args.input)))
        else:
            report, _ = format_one(args.input, args.format)
            print(report)
    else:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            if args.raw:
                print(len(strip_latex(line)))
            else:
                report, _ = format_one(line, args.format)
                print(report)
                print()


if __name__ == '__main__':
    main()
