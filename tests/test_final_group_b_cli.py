"""Command-line paths of ``tools/cli.py`` the earlier tests reach only in subprocesses (which the
coverage tool does not see) or not at all. Task 2.3 of
``openspec/changes/verify-port-completeness``.

* a fatal error in a box-score file whose message has a NULL string in it, which glibc prints as
  ``(null)``: run in this process, against the real tools;
* the same error raised inside a parallel worker;
* the control-group parser skipping lines it cannot use (no Chadwick counterpart: the C has no
  CPU-limit logic).
"""

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from chadwick_tool import real_tool  # noqa: E402
from test_audit_findings import FLAGS, YEAR, box_game_missing_player_field  # noqa: E402
from test_cgroup_limit import v2, whoami  # noqa: E402
from test_cli_differential import run_port, run_real  # noqa: E402
from test_final_group_b_events import top  # noqa: E402
from test_game_targeted_differential import HOME, LINEUP, head  # noqa: E402

from chadwickpy.roster import League  # noqa: E402
from chadwickpy.tools import cli  # noqa: E402

needs_tools = pytest.mark.skipif(
    any(real_tool(t) is None for t in ("cwgame", "cwdaily", "cwbox")),
    reason="needs the Chadwick tools on PATH",
)

NAME = "g.EBR"


def scratch(tmp: Path) -> Path:
    tmp.mkdir()
    (tmp / NAME).write_bytes(box_game_missing_player_field().encode("latin-1"))
    (tmp / f"TEAM{YEAR}").write_text("")
    return tmp


def args(tool: str) -> list[str]:
    return ["-Q", "-y", str(YEAR), *([] if tool == "cwbox" else FLAGS[tool]), NAME]


@needs_tools
@pytest.mark.parametrize("tool", ["cwgame", "cwdaily", "cwbox"])
def test_null_string_in_a_message_prints_null(tmp_path: Path, tool: str) -> None:
    """``cannot find entry for player '(null)' listed in dline``: exit status, stdout, stderr"""
    real = run_real(tool, args(tool), scratch(tmp_path / "real"))
    port = run_port(tool, args(tool), scratch(tmp_path / "port"))
    assert b"(null)" in real[2]
    assert port == real


@needs_tools
@pytest.mark.parametrize("tool", ["cwgame", "cwdaily", "cwbox"])
def test_worker_reports_the_same_fatal_error(tmp_path: Path, tool: str) -> None:
    """The per-file worker of a parallel run returns the C's message and exit status 1.

    cli.py 327.
    """
    real = run_real(tool, args(tool), scratch(tmp_path / "real"))
    work = scratch(tmp_path / "port")
    opts = cli.Options(fields=set(cli.TOOLS[tool].default_fields), year=str(YEAR), quiet=True)
    out, err, status = cli._worker_scorebook((tool, opts, League(), str(work / NAME)))
    # the header line is printed by the parent process, not the worker
    assert (status, out, err.encode("latin-1")) == (real[0], "", real[2])


@pytest.mark.parametrize(
    "extra",
    [
        "garbage without colons",  # not three fields: skipped
        "7:memory:/somewhere",  # a controller list without cpu: skipped
        "3:blkio,devices:/a/b",
    ],
)
def test_cgroup_lines_without_a_cpu_controller_are_skipped(tmp_path: Path, extra: str) -> None:
    root = tmp_path / "cg"
    v2(root, "200000 100000\n")
    own = whoami(tmp_path, extra + "\n0::/")
    assert cli.cgroup_cpu_limit(root, own) == 2


def no_catcher_game(play: str) -> str:
    """The home catcher is listed at position 11, so the defence has no catcher; the visitors then
    run: a stolen base or a wild pitch is credited to a catcher who is not there"""
    text = head()
    for team, lineup in ((0, LINEUP), (1, HOME)):
        for slot, (pid, pos) in enumerate(lineup, 1):
            text += f'start,{pid},"Player {pid}",{team},{slot},{11 if team and pos == 2 else pos}\n'
    return text + top("play,1,0,v1,??,,S8\n", f"play,1,0,v2,??,,{play}\n")


NO_CATCHER = {
    "stolen_base": "SB2",
    "caught_stealing": "CS2(26)",
    "wild_pitch": "WP.1-2",
    "passed_ball": "PB.1-2",
}


@needs_tools
@pytest.mark.parametrize("name", NO_CATCHER)
def test_missing_catcher_message_prints_null(tmp_path: Path, name: str) -> None:
    """the box-score messages print a NULL catcher id as ``(null)`` (cli.py 294)"""
    text = no_catcher_game(NO_CATCHER[name])
    real_dir, port_dir = tmp_path / "real", tmp_path / "port"
    for d in (real_dir, port_dir):
        d.mkdir()
        (d / NAME).write_bytes(text.encode("latin-1"))
        (d / "TEAM2020").write_text("")
    a = ["-Q", "-y", "2020", "-n", NAME]
    real = run_real("cwgame", a, real_dir)
    port = run_port("cwgame", a, port_dir)
    assert b"(null)" in real[2]
    assert port == real
