"""Wildcard file names, as ``cwtools_process_filespec`` handles them (OpenSpec change
verify-port-completeness, task 4.4).

The C program has three versions of this function. On Unix it processes the name it is given (the
shell has already expanded ``*.EVA``). On Windows and DOS it expands the pattern itself with
``_findfirst`` / ``findfirst``: every match is processed, and a pattern or name that matches
nothing is skipped silently. ``cmd.exe`` does not expand wildcards, so without this
``cwevent -y 1950 1950*.EV*`` finds nothing on Windows. The Windows behaviour is tested here with
the platform check switched on, since the real C Windows build cannot run on Linux.
"""

from pathlib import Path

import pytest

from chadwickpy.tools import cli
from chadwickpy.tools.cli import IO, TOOLS, expand_filespec, main

HERE = Path(__file__).parent
EVENT = (HERE / "fixtures" / "events" / "regular_2007.evt").read_bytes()
ROSTERS = HERE / "reference" / "rosters" / "regular_2007"


def make(tmp: Path, *names: str) -> None:
    for name in names:
        (tmp / name).write_bytes(EVENT)


def test_unix_leaves_the_name_alone_even_with_wildcard_characters(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    make(tmp_path, "a.EVA")
    assert expand_filespec("*.EVA", windows=False) == ["*.EVA"]
    assert expand_filespec("missing.EVA", windows=False) == ["missing.EVA"]


def test_windows_expands_a_pattern_in_name_order(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    make(tmp_path, "1950B.EVA", "1950A.EVA", "1950C.EVN", "other.txt")
    assert expand_filespec("1950*.EV?", windows=True) == ["1950A.EVA", "1950B.EVA", "1950C.EVN"]
    assert expand_filespec("1950?.EVA", windows=True) == ["1950A.EVA", "1950B.EVA"]


def test_windows_pattern_with_no_match_gives_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert expand_filespec("*.EVA", windows=True) == []


def test_windows_plain_name_is_kept_only_if_it_exists(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    make(tmp_path, "a.EVA")
    assert expand_filespec("a.EVA", windows=True) == ["a.EVA"]
    assert expand_filespec("nothere.EVA", windows=True) == []  # silent, as the C is


def test_windows_square_brackets_are_not_wildcards(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    make(tmp_path, "a[1].EVA", "a1.EVA")
    assert expand_filespec("a[1].EVA", windows=True) == ["a[1].EVA"]


def test_windows_keeps_the_directory_of_a_pattern(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "sub").mkdir()
    make(tmp_path / "sub", "x.EVA", "y.EVA")
    found = expand_filespec("sub/*.EVA", windows=True)
    assert [Path(f).name for f in found] == ["x.EVA", "y.EVA"]
    assert all((tmp_path / f).exists() for f in found)


def run(tool: str, args: list[str]) -> tuple[int, str, str]:
    out: list[str] = []
    err: list[str] = []
    status = main(TOOLS[tool], [tool, *args], IO(out.append, err.append))
    return status, "".join(out), "".join(err)


@pytest.mark.parametrize("tool", ["cwevent", "cwgame", "cwbox", "cwdaily", "cwsub", "cwcomment"])
def test_a_wildcard_run_equals_naming_the_files(tmp_path, monkeypatch, tool):
    """With the Windows check on, ``2007*.EV?`` gives the output of naming the files."""
    for f in ROSTERS.iterdir():
        (tmp_path / f.name).write_bytes(f.read_bytes())
    make(tmp_path, "2007B.EVA", "2007A.EVA", "2007C.EVN")
    monkeypatch.chdir(tmp_path)
    explicit = run(tool, ["-Q", "-y", "2007", "2007A.EVA", "2007B.EVA", "2007C.EVN"])
    monkeypatch.setattr(cli, "_is_windows", lambda: True)
    wild = run(tool, ["-Q", "-y", "2007", "2007*.EV?"])
    assert explicit[0] == wild[0] == 0
    assert explicit[1] and wild == explicit


def test_a_wildcard_with_no_match_processes_nothing_and_succeeds(tmp_path, monkeypatch):
    for f in ROSTERS.iterdir():
        (tmp_path / f.name).write_bytes(f.read_bytes())
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "_is_windows", lambda: True)
    status, out, err = run("cwevent", ["-Q", "-y", "2007", "*.NOPE"])
    assert (status, out, err) == (0, "", "")
