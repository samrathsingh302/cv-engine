"""Shared in-process + subprocess runners for the lint CLIs.

In-process (`run_inproc`) calls the module's run() and captures stdout + the
returned exit code — fast, used for rule-firing and determinism assertions.

Subprocess (`run_cli`) shells out to `python <script> ...` so the real exit-code
contract (0/1/2, argparse unknown-flag = 2) is exercised end to end, with stdout
captured as raw bytes to assert byte-identical determinism and UTF-8 (no BOM).
"""

import io
import json
import subprocess
import sys
from contextlib import redirect_stdout


def run_inproc(mod, argv):
    """Run mod.run(argv) capturing stdout. Returns (exit_code, stdout_str)."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = mod.run(list(argv))
    return code, buf.getvalue()


def run_cli(script, argv):
    """Run the linter as a subprocess. Returns (exit_code, stdout_bytes)."""
    proc = subprocess.run(
        [sys.executable, script, *argv],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc.returncode, proc.stdout


def run_json(mod, argv):
    """Run in-process with --format json; return (exit_code, parsed_doc)."""
    code, out = run_inproc(mod, [*argv, "--format", "json"])
    return code, json.loads(out)
