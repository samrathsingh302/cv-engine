"""Pytest fixtures for the lint suite.

These tests own their throwaway data (test-helpers-own-throwaway-data): every
fixture is a tiny inline string written to tmp_path, never a copy of a real
output file. The ONE exception is the explicit 0-false-positive tuning check,
which reads the shipped clean deliverables by design (the tuning set).

The linters are loaded by absolute path because cv_builder/helpers is not a
package (the integrator owns any packaging). Each linter is imported as its own
module object so tests can call run()/scan helpers directly and drive the CLI via
a subprocess for the exit-code contract.
"""

import importlib.util
import os
import sys

import pytest

HELPERS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)
REPO_ROOT = os.path.normpath(os.path.join(HELPERS_DIR, "..", ".."))
FP_PATH = os.path.join(HELPERS_DIR, "lint_fingerprint.py")
PV_PATH = os.path.join(HELPERS_DIR, "lint_provenance.py")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def fp_mod():
    return _load("lint_fingerprint_undertest", FP_PATH)


@pytest.fixture(scope="session")
def pv_mod():
    return _load("lint_provenance_undertest", PV_PATH)


@pytest.fixture(scope="session")
def repo_root():
    return REPO_ROOT


@pytest.fixture(scope="session")
def fp_script():
    return FP_PATH


@pytest.fixture(scope="session")
def pv_script():
    return PV_PATH


def write(tmp_path, name, text):
    """Write `text` to tmp_path/name as UTF-8 (LF), no BOM. Return abs path str.

    Parent directories (e.g. an `output/` segment used to drive the deliverable
    scan policy) are created on demand.
    """
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(text.encode("utf-8"))
    return str(p)


@pytest.fixture
def writer(tmp_path):
    def _w(name, text):
        return write(tmp_path, name, text)
    return _w
