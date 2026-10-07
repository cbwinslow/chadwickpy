"""Corners of ``lint.py`` (against the C ``cw_game_lint``) and of the port-only modules.

* ``lint.py``: a starter with an out-of-range position, and plays marked DP/TP with too few outs,
  compared with ``tests/reference/lint_dump.c``. A starter with a slot or team outside its range
  indexes the lineup array out of bounds in ``cw_gameiter_create`` (undefined behaviour in the C,
  reported by the sanitised build); the port's Python lists accept a negative index, so there the
  test only checks that the port logs the same messages the C code would print.
* ``guard.py`` (the new-season guard) has no counterpart in Chadwick: tested on its own.
* ``__init__.py`` (version fallback when the package is not installed) and ``__main__.py``
  (importing the module does not run the tool) are Python packaging details with no C
  counterpart.
"""

import importlib
import importlib.metadata
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "reference"))
sys.path.insert(0, str(HERE))
from lint_dump import dump  # noqa: E402
from test_box_targeted_differential import game  # noqa: E402
from test_lint_differential import (  # noqa: E402
    c_dump,
    c_is_defined,
    harness,  # noqa: F401  (fixture)
    pytestmark,  # noqa: F401  (skip without gcc / Chadwick sources)
    restore_logging,  # noqa: F401  (fixture)
    sanitized,  # noqa: F401  (fixture)
)

import chadwickpy  # noqa: E402
from chadwickpy.guard import check_event_file  # noqa: E402


VISITOR1 = 'start,v1,"V N1",0,1,8\n'
DEFINED = {
    "position_0": game().replace(VISITOR1, 'start,v1,"V N1",0,1,0\n'),
    "position_11": game().replace(VISITOR1, 'start,v1,"V N1",0,1,11\n'),
    "dp_with_one_out": game(plays=["play,1,0,v1,00,X,S9/DP\n"]),
    "dp_marked_strikeout": game(plays=["play,1,0,v1,00,X,K/DP\n"]),
    "tp_with_no_outs": game(plays=["play,1,0,v1,00,X,S9/TP\n"]),
    "dp_and_tp": game(plays=["play,1,0,v1,00,X,S9/DP/TP\n"]),
}
UNDEFINED = {
    "slot_minus_1": (game().replace(VISITOR1, 'start,v1,"V N1",0,-1,8\n'), "invalid slot -1"),
    "team_minus_1": (game().replace(VISITOR1, 'start,v1,"V N1",-1,1,8\n'), "invalid team -1"),
}


@pytest.mark.parametrize("name", DEFINED)
def test_lint_equals_chadwick(harness, sanitized, tmp_path, name):  # noqa: F811
    data = DEFINED[name].encode("latin-1")
    expected = c_dump(harness, data, tmp_path)
    assert c_is_defined(sanitized, tmp_path)
    assert dump(data) == expected
    assert "lint=0" in expected[0]


@pytest.mark.parametrize("name", UNDEFINED)
def test_lint_of_out_of_range_starter(harness, sanitized, tmp_path, name):  # noqa: F811
    text, message = UNDEFINED[name]
    data = text.encode("latin-1")
    c_dump(harness, data, tmp_path)
    assert not c_is_defined(sanitized, tmp_path), "the C should report undefined behaviour"
    lines, crashed = dump(data)
    assert not crashed
    assert any(message in line for line in lines)
    assert "lint=0" in lines


# ---------------------------------------------------------------------------------------------
# guard.py (no C counterpart)
# ---------------------------------------------------------------------------------------------

DATE = b"info,date,2020/01/01\n"


def test_guard_reports_an_empty_file() -> None:
    assert check_event_file(b"", "x.evn") == ["x.evn: file is empty or unreadable"]


def test_guard_reports_an_id_record_that_did_not_become_a_game() -> None:
    # the last id line has no newline: the reader does not take it as a game
    problems = check_event_file(b"id,A\n" + DATE + b"id,B")
    assert problems == ["2 id records but 1 games were read"]


def test_guard_accepts_a_clean_file() -> None:
    assert check_event_file(game().encode("latin-1")) == []


def test_guard_reports_unparsed_play_and_reader_warnings() -> None:
    problems = check_event_file(game(plays=["play,1,0,v1,00,X,@@@\n"]).encode("latin-1"))
    assert any("unparsed play '@@@'" in p for p in problems)


# ---------------------------------------------------------------------------------------------
# __init__.py and __main__.py
# ---------------------------------------------------------------------------------------------


def test_version_falls_back_when_the_package_is_not_installed(monkeypatch) -> None:
    def missing(name: str) -> str:
        raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(importlib.metadata, "version", missing)
    try:
        reloaded = importlib.reload(chadwickpy)
        assert reloaded.__version__ == "0+unknown"
    finally:
        monkeypatch.undo()
        importlib.reload(chadwickpy)
    assert chadwickpy.__version__


def test_importing_main_does_not_run_the_tool() -> None:
    sys.modules.pop("chadwickpy.__main__", None)
    module = importlib.import_module("chadwickpy.__main__")  # returns instead of exiting
    assert callable(module.main_umbrella)
