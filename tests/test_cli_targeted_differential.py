"""Command-line branches of ``tools/cli.py`` and ``tools/tools.py`` the broad sweep misses.

Every case in ``CASES`` runs the real Chadwick tool and the port on identical scratch
directories and compares exit status, stderr and stdout byte for byte. The port-only tests at
the end cover what the C tools do not have (``-j``/``--jobs``, ``CHADWICK_JOBS``, worker error
reports, the console-script wrappers); the C tools reject ``-j`` as an invalid option.
"""

import logging
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from test_cli_differential import (  # noqa: E402
    ALL_TOOLS,
    EVENT,
    pytestmark,  # noqa: F401  (skip without the real tools)
    run_port,
    run_real,
    scratch,
)

from chadwickpy.tools import cli  # noqa: E402
from chadwickpy.tools.cli import IO  # noqa: E402

JUNK_THEN_GAMES = b"this is not a record\n" + EVENT
UNDATED = b"id,TOR200705310\nversion,2\ninfo,visteam,BAL\ninfo,hometeam,TOR\n"

CASES = {
    # field lists: a range whose end is missing ("5-"), one that is too big, a trailing comma
    "field_range_no_end": ["-Q", "-y", "2007", "-f", "5-", "a.evt"],
    "field_range_no_end_x": ["-Q", "-y", "2007", "-x", "2-", "a.evt"],
    "field_trailing_comma": ["-Q", "-y", "2007", "-n", "-f", "0-2,", "a.evt"],
    "field_ext_too_big": ["-Q", "-y", "2007", "-x", "9999", "a.evt"],
    "field_ext_reversed": ["-Q", "-y", "2007", "-x", "4-1", "a.evt"],
    "field_huge_number": ["-Q", "-y", "2007", "-f", "99999999999", "a.evt"],
    # an option that needs a value, given as the last argument
    "last_e": ["-Q", "-y", "2007", "-e"],
    "last_s": ["-Q", "-y", "2007", "-s"],
    "last_i": ["-Q", "-y", "2007", "-i"],
    "last_y": ["-Q", "-y"],
    "last_x": ["-Q", "-y", "2007", "-x"],
    "last_f": ["-Q", "-y", "2007", "-f"],
    # no file argument, option-only command lines, option after the files
    "no_files": ["-Q", "-y", "2007"],
    "only_quiet": ["-Q"],
    "empty_args": [],
    "options_after_file": ["-y", "2007", "a.evt", "-Q", "-n"],
    "dash_alone": ["-y", "2007", "-"],
    "long_option": ["-y", "2007", "--help"],
    # value truncation (date 4 characters, id 19, year 5)
    "long_dates": ["-Q", "-y", "2007", "-s", "06011234", "-e", "06301234", "a.evt"],
    "long_game_id": ["-Q", "-y", "2007", "-i", "TOR200705310123456789", "a.evt"],
    # selection that rejects every game, and one that picks games by id and date together
    "no_game_in_range": ["-Q", "-y", "2007", "-s", "1231", "-e", "1231", "a.evt"],
    "id_mismatch": ["-Q", "-y", "2007", "-i", "ZZZ200701010", "a.evt"],
    "reversed_dates": ["-Q", "-y", "2007", "-s", "0901", "-e", "0301", "a.evt"],
    # files
    "junk_before_games": ["-Q", "-y", "2007", "junk.evt"],
    "junk_before_games_verbose": ["-y", "2007", "junk.evt"],
    "directory_as_file": ["-Q", "-y", "2007", "adir"],
    "no_such_year": ["-Q", "-y", "1999", "a.evt"],
    "bad_year_text": ["-y", "2007x", "a.evt"],
    # repeated and conflicting options
    "ascii_then_fortran": ["-Q", "-y", "2007", "-a", "-ft", "a.evt"],
    "fortran_then_ascii": ["-Q", "-y", "2007", "-ft", "-a", "-n", "a.evt"],
    "repeated_y": ["-Q", "-y", "1999", "-y", "2007", "a.evt"],
    "header_fortran": ["-Q", "-y", "2007", "-ft", "-n", "a.evt"],
    "help_after_bad": ["-z", "-h"],
    "help_after_good": ["-Q", "-h"],
    "list_after_good": ["-Q", "-d"],
    "list_then_bad": ["-d", "-z"],
    "bad_after_good": ["-Q", "-y", "2007", "-Q", "a.evt"],
    "xml_and_sportsml": ["-Q", "-y", "2007", "-X", "-S", "a.evt"],
    "sportsml_only": ["-Q", "-y", "2007", "-S", "a.evt"],
    "sportsml_header": ["-Q", "-y", "2007", "-S", "-n", "a.evt"],
    "xml_two_files": ["-Q", "-y", "2007", "-X", "a.evt", "b.evt"],
}


def check(tool: str, args: list[str], tmp: Path, setup=None) -> None:
    works = []
    for name in ("real", "port"):
        work = scratch(tmp, name)
        (work / "junk.evt").write_bytes(JUNK_THEN_GAMES)
        (work / "adir").mkdir()
        if setup is not None:
            setup(work)
        works.append(work)
    real = run_real(tool, args, works[0])
    port = run_port(tool, args, works[1])
    assert real[0] == port[0], (real, port)
    assert real[2] == port[2], "stderr"
    assert real[1] == port[1], "stdout"


# The real ``cwbox -S`` (SportsML, deprecated: ADR-002) crashes unless ``-X`` is also given.
CLI_CASES = [
    (tool, case)
    for case, args in CASES.items()
    for tool in ALL_TOOLS
    if not (tool == "cwbox" and "-S" in args and "-X" not in args)
]


@pytest.mark.parametrize(("tool", "case"), CLI_CASES)
def test_targeted_cli_matches_chadwick(tmp_path: Path, tool: str, case: str) -> None:
    check(tool, CASES[case], tmp_path)


BAD_STARTER = (
    b"id,TOR200705310\nversion,2\ninfo,visteam,CHA\ninfo,hometeam,TOR\ninfo,date,2007/05/31\n"
    b'start,aaaa001,"A A",0,1,11\n'
)


SANITY_CASES = [(tool, []) for tool in ALL_TOOLS] + [
    ("cwbox", args) for args in (["-S"], ["-X"], ["-S", "-X"])
]


@pytest.mark.parametrize(("tool", "args"), SANITY_CASES)
def test_game_failing_the_sanity_check(tmp_path: Path, tool: str, args: list[str]) -> None:
    """A game failing ``cw_game_lint`` is skipped; with ``cwbox -S`` that leaves a ``None``
    result to write (the real ``cwbox -S`` does not crash on it, unlike on a printed game)."""

    def add(work: Path) -> None:
        (work / "bad.evt").write_bytes(BAD_STARTER)

    check(tool, ["-Q", "-y", "2007", *args, "bad.evt"], tmp_path, add)


@pytest.mark.parametrize("tool", ["cwevent", "cwgame", "cwdaily", "cwsub", "cwcomment"])
def test_output_over_500_lines(tmp_path: Path, tool: str) -> None:
    """More lines than one output chunk (500)."""

    def add(work: Path) -> None:
        (work / "big.evt").write_bytes(EVENT * 12)

    check(tool, ["-Q", "-y", "2007", "big.evt"], tmp_path, add)


def test_output_chunks_exactly() -> None:
    out: list[str] = []
    cli._lines(IO(out.append, str), (f"line {n}" for n in range(1000)))
    assert [c.count("\n") for c in out] == [500, 500]
    out.clear()
    cli._lines(IO(out.append, str), iter(()))
    assert out == []


def test_reading_stopped_warning_is_not_printed() -> None:
    """The port's own "reading stopped" diagnostic is not something Chadwick prints."""
    err: list[str] = []
    handler = cli._Stderr(IO(str, err.append))
    for text in ("WARNING: reading stopped at byte 3 of 9", "other"):
        handler.emit(logging.LogRecord("x", logging.WARNING, "f", 1, text, (), None))
    assert err == ["other\n"]


@pytest.mark.parametrize("tool", ALL_TOOLS)
def test_lowercase_team_file(tmp_path: Path, tool: str) -> None:
    """``TEAMyyyy`` missing: the lowercase ``teamyyyy`` is read instead."""

    def lower(work: Path) -> None:
        (work / "TEAM2007").rename(work / "team2007")

    check(tool, ["-Q", "-y", "2007", "-n", "a.evt"], tmp_path, lower)


@pytest.mark.parametrize("tool", ALL_TOOLS)
def test_missing_team_file(tmp_path: Path, tool: str) -> None:
    def remove(work: Path) -> None:
        (work / "TEAM2007").unlink()

    check(tool, ["-Q", "-y", "2007", "a.evt"], tmp_path, remove)


@pytest.mark.parametrize("tool", ALL_TOOLS)
def test_missing_roster_files(tmp_path: Path, tool: str) -> None:
    def remove(work: Path) -> None:
        for ros in work.glob("*.ROS"):
            ros.unlink()

    check(tool, ["-Q", "-y", "2007", "-n", "a.evt"], tmp_path, remove)


def _into_data_dir(work: Path, lower_team: bool = False) -> None:
    """Move the team and roster files into ``work/data``, leaving only the event files here."""
    data = work / "data"
    data.mkdir()
    for path in [*work.glob("TEAM*"), *work.glob("*.ROS")]:
        path.rename(data / path.name)
    if lower_team:
        (data / "TEAM2007").rename(data / "team2007")


DATA_DIR_ARGS = {
    "no_slash": ["-D", "data"],
    "trailing_slash": ["-D", "data/"],
    "absent_directory": ["-D", "nowhere"],
    "dot_slash": ["-D", "./data"],
    "before_other_options": ["-Q", "-n", "-D", "data"],
}


@pytest.mark.parametrize("case", DATA_DIR_ARGS)
@pytest.mark.parametrize("tool", ALL_TOOLS)
def test_data_dir_finds_team_and_roster_files(tmp_path: Path, tool: str, case: str) -> None:
    """``-D dir``: TEAMyyyy and the rosters come from ``dir``, with or without a trailing slash;
    an absent directory gives Chadwick's own missing-team-file error."""
    args = [*DATA_DIR_ARGS[case], "-Q", "-y", "2007", "-n", "a.evt"]
    check(tool, args, tmp_path, _into_data_dir)


@pytest.mark.parametrize("tool", ALL_TOOLS)
def test_data_dir_with_lowercase_team_file(tmp_path: Path, tool: str) -> None:
    check(
        tool,
        ["-D", "data", "-Q", "-y", "2007", "-n", "a.evt"],
        tmp_path,
        lambda work: _into_data_dir(work, lower_team=True),
    )


@pytest.mark.parametrize("tool", ALL_TOOLS)
def test_data_dir_without_the_files_there(tmp_path: Path, tool: str) -> None:
    """Files in the current directory are not found once ``-D`` names another one."""

    def empty_data(work: Path) -> None:
        (work / "data").mkdir()

    check(tool, ["-D", "data", "-Q", "-y", "2007", "a.evt"], tmp_path, empty_data)


@pytest.mark.parametrize("tool", ALL_TOOLS)
def test_data_dir_missing_argument(tmp_path: Path, tool: str) -> None:
    check(tool, ["-Q", "-y", "2007", "a.evt", "-D"], tmp_path)


# --- port-only: the C tools have no -j/--jobs (they print "Invalid option '-j'") ---------------


@pytest.mark.parametrize("flag", ["-j", "-j2", "--jobs"])
def test_real_tools_reject_jobs(tmp_path: Path, flag: str) -> None:
    """The C tools do not have the port's ``-j``; the port's extra option is deliberate."""
    status, _, err = run_real("cwevent", ["-y", "2007", flag, "a.evt"], scratch(tmp_path, "w"))
    assert status == 1 and err == f"*** Invalid option '{flag}'.\n".encode()


def port_run(tool: str, args: list[str], work: Path) -> tuple[int, bytes, bytes]:
    return run_port(tool, args, work)


@pytest.mark.parametrize("jobs", [["-j", "2"], ["-j2"], ["--jobs", "2"], ["-j"], ["--jobs"]])
def test_jobs_option_matches_serial(tmp_path: Path, jobs: list[str]) -> None:
    work = scratch(tmp_path, "w")
    base = ["-Q", "-y", "2007", "-n"]
    serial = port_run("cwevent", [*base, "-j", "1", "a.evt", "b.evt"], work)
    parallel = port_run("cwevent", [*base, *jobs, "a.evt", "b.evt"], work)
    assert serial[0] == 0 and serial[1]
    assert parallel == serial


def test_jobs_value_after_nondigit_is_a_file(tmp_path: Path) -> None:
    work = scratch(tmp_path, "w")
    status, out, err = port_run("cwevent", ["-y", "2007", "-j", "a.evt"], work)
    assert status == 0 and b"[Processing file a.evt.]" in err and out


def test_environment_jobs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    work = scratch(tmp_path, "w")
    args = ["-Q", "-y", "2007", "a.evt", "b.evt"]
    serial = port_run("cwevent", ["-j", "1", *args], work)
    for value in ("2", "auto", "junk"):
        monkeypatch.setenv("CHADWICK_JOBS", value)
        assert port_run("cwevent", args, work) == serial
    # the command line wins over the environment
    monkeypatch.setenv("CHADWICK_JOBS", "2")
    assert port_run("cwevent", ["-j", "1", *args], work) == serial


def test_undated_game_is_reported_not_crashed(tmp_path: Path) -> None:
    """The C tool dereferences a NULL date; the port reports an error (serially and in a worker)."""
    work = scratch(tmp_path, "w")
    (work / "undated.evt").write_bytes(UNDATED)
    serial = port_run("cwevent", ["-Q", "-y", "2007", "undated.evt"], work)
    assert serial[0] == 1 and b"has no date" in serial[2]
    parallel = port_run("cwevent", ["-Q", "-y", "2007", "-j", "2", "a.evt", "undated.evt"], work)
    assert parallel[0] == 1 and b"has no date" in parallel[2] and parallel[1]


def test_unreadable_date_is_reported(tmp_path: Path) -> None:
    work = scratch(tmp_path, "w")
    (work / "baddate.evt").write_bytes(UNDATED + b"info,date,yesterday\n")
    status, _, err = port_run("cwevent", ["-Q", "-y", "2007", "baddate.evt"], work)
    assert status == 1 and b"unreadable date" in err


def test_worker_reports_unexpected_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def boom(*args: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(cli, "process_scorebook", boom)
    out, err, status = cli._worker_scorebook(("cwevent", cli.Options(fields=set()), None, "a.evt"))  # type: ignore[arg-type]
    assert (out, status) == ("", 1)
    assert err == "chadwickpy: unexpected error processing a.evt: boom\n"


def test_init_worker_adds_missing_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "path", ["/already"])
    cli._init_worker(["/already", "/new1", "/new2"])
    assert sys.path == ["/new1", "/new2", "/already"]


def test_parallel_failure_finishes_serially(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    work = scratch(tmp_path, "w")
    args = ["-Q", "-y", "2007", "a.evt", "b.evt"]
    serial = port_run("cwevent", ["-j", "1", *args], work)

    class Broken:
        def __init__(self, *a: object, **k: object) -> None:
            raise OSError("no processes here")

    monkeypatch.setattr("concurrent.futures.ProcessPoolExecutor", Broken)
    status, out, err = port_run("cwevent", ["-j", "2", *args], work)
    assert (status, out) == (serial[0], serial[1])
    assert b"parallel run failed (no processes here)" in err


def test_run_quiet_on_closed_pipe(monkeypatch: pytest.MonkeyPatch) -> None:
    def closed(*args: object) -> int:
        raise BrokenPipeError

    redirected: list[tuple[int, int]] = []
    monkeypatch.setattr(cli, "main", closed)
    monkeypatch.setattr(cli.os, "dup2", lambda src, dst: redirected.append((src, dst)))
    assert cli.run("cwevent") == 128 + 13
    assert len(redirected) == 1


def test_run_closed_pipe_survives_devnull_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def closed(*args: object) -> int:
        raise BrokenPipeError

    def refuse(*args: object) -> int:
        raise OSError("no /dev/null")

    monkeypatch.setattr(cli, "main", closed)
    monkeypatch.setattr(cli.os, "open", refuse)
    assert cli.run("cwevent") == 128 + 13


def test_run_returns_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "main", lambda *a: 7)
    assert cli.run("cwevent") == 7


def test_umbrella_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    for argv in (["chadwickpy"], ["chadwickpy", "cwnothing"]):
        monkeypatch.setattr(sys, "argv", argv)
        with pytest.raises(SystemExit) as stop:
            cli.main_umbrella()
        assert "usage: chadwickpy {cwevent," in str(stop.value)


def test_umbrella_dispatches(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []
    monkeypatch.setattr(cli, "run", lambda name: seen.append(name) or 0)
    monkeypatch.setattr(sys, "argv", ["chadwickpy", "cwbox", "-h"])
    assert cli.main_umbrella() == 0 and seen == ["cwbox"] and sys.argv == ["chadwickpy", "-h"]


def test_stdout_stderr_writers(capfdbinary: pytest.CaptureFixture[bytes]) -> None:
    cli._write_stdout("caf\xe9")
    cli._write_stderr("\xe9")
    sys.stdout.flush()
    out, err = capfdbinary.readouterr()
    assert (out, err) == (b"caf\xe9", b"\xe9")


def test_wrappers_call_run(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []
    monkeypatch.setattr(cli, "run", lambda name: seen.append(name) or 0)
    for fn in (
        cli.main_cwevent,
        cli.main_cwgame,
        cli.main_cwdaily,
        cli.main_cwsub,
        cli.main_cwcomment,
        cli.main_cwbox,
    ):
        assert fn() == 0
    assert seen == ["cwevent", "cwgame", "cwdaily", "cwsub", "cwcomment", "cwbox"]


def test_worker_reports_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Called in-process (a pool worker's coverage is not measured): ``ValueError`` becomes a
    ``chadwickpy:`` message and status 1."""

    def refuse(*args: object) -> None:
        raise ValueError("no date")

    monkeypatch.setattr(cli, "process_scorebook", refuse)
    result = cli._worker_scorebook(("cwevent", cli.Options(fields=set()), None, "a.evt"))  # type: ignore[arg-type]
    assert result == ("", "chadwickpy: no date\n", 1)


def test_iterate_games_selects_and_skips() -> None:
    from chadwickpy.tools.tools import iterate_games

    everything = list(iterate_games(EVENT))
    assert everything and all(v is None and h is None for _, v, h in everything)
    assert list(iterate_games(b"")) == []
    first = everything[0][0].game_id
    assert [g.game_id for g, _, _ in iterate_games(EVENT, game_id=first)] == [first]
    assert list(iterate_games(EVENT, first="1231", last="1231")) == []
