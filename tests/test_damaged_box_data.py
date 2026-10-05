"""Retrosheet's box-score-only files (Negro Leagues, 1930s-40s) contain damaged records that the C
tools survive: a starter with no position, a ``dline`` with ``?`` or ``NA`` for a number, and start
times written as spreadsheet fractions (``0.375``). The C does not check these values; it indexes
arrays with -1 (which lands inside the same struct) and prints stack leftovers. The port reproduces
what the C does, and these tests compare it with the real C tools (skipped without them) and pin the
values observed there."""

import subprocess
import sys
from pathlib import Path

import pytest
from chadwick_tool import real_tool

NAMES = ["One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
POS = [8, 4, 3, 7, 9, 5, 6, 2, 1]
YEAR = 1947


def box_game(*, start_pos: str | None = None, dline_pos: str | None = None,
             dline_seq: str | None = None, starttime: str = "1:05PM") -> str:  # fmt: skip
    """A made-up box-score-only game with one damaged record, as in the Negro Leagues files."""
    lines = [
        f"id,AAA{YEAR}05200",
        "version,5",
        "info,visteam,BBB",
        "info,hometeam,AAA",
        f"info,date,{YEAR}/05/20",
        "info,number,0",
        f"info,starttime,{starttime}",
        "info,daynight,day",
        "info,attendance,4000",
        "info,wp,aaap9",
        "info,lp,bbbp9",
        "line,0,0,0,0,0,0,0,0,2,0",
        "line,1,0,0,0,0,0,0,0,0,1",
        "stat,tline,0,7,1,1,0",
        "stat,tline,1,8,2,0,0",
    ]
    for team, side in (("BBB", 0), ("AAA", 1)):
        for i, n in enumerate(NAMES):
            pos = str(POS[i])
            if start_pos is not None and team == "AAA" and i == 2:
                pos = start_pos  # the third home starter, e.g. an empty position
            lines.append(f'start,{team.lower()}p{i + 1},"{team} {n}",{side},{i + 1},{pos}')
    for team, side in (("BBB", 0), ("AAA", 1)):
        for i in range(9):
            lines.append(
                f"stat,bline,{team.lower()}p{i + 1},{side},{i + 1},1,4,0,1,0,0,0,0,0,"
                "-1,0,0,0,-1,0,-1,-1,0"
            )
    lines += [
        "stat,pline,bbbp9,0,1,27,-1,36,6,1,0,0,1,1,1,-1,8,1,0,0,0,-1",
        "stat,pline,aaap9,1,1,27,-1,36,6,1,0,0,2,2,1,-1,4,0,0,0,2,-1",
    ]
    for team, side in (("BBB", 0), ("AAA", 1)):
        for i in range(9):
            seq, pos = "1", str(POS[i])
            if dline_pos is not None and team == "AAA" and i == 3:
                pos = dline_pos
            if dline_seq is not None and team == "AAA" and i == 4:
                seq = dline_seq
            lines.append(f"stat,dline,{team.lower()}p{i + 1},{side},{seq},{pos},27,3,5,1,0,0,0")
    # Retrosheet's files end their lines with CR LF. It matters here: after a final comma, "\r\n"
    # makes an empty last field, while a bare "\n" makes the record one field short and drops it.
    return "\r\n".join(lines) + "\r\n"


CASES = {
    "starter with no position": {"start_pos": ""},
    "dline with ? as the position": {"dline_pos": "?"},
    "dline with NA as the sequence number": {"dline_seq": "NA"},
    "start time 0.375": {"starttime": "0.375"},
    "start time 6.25E-2": {"starttime": "6.25E-2"},
    "all of them at once": {
        "start_pos": "", "dline_pos": "?", "dline_seq": "NA", "starttime": "0.375",
    },
}  # fmt: skip
TOOLS = ["cwgame", "cwdaily", "cwbox"]
FLAGS = {
    "cwgame": ["-n", "-f", "0-84", "-x", "0-96"],
    "cwdaily": ["-n", "-f", "0-153"],
    "cwbox": [],
}


def run_both(
    tmp_path: Path, tool: str, text: str, flags: list[str]
) -> tuple[tuple[int, bytes], tuple[int, bytes]]:
    folder = tmp_path / "w"
    folder.mkdir(exist_ok=True)
    name = f"{YEAR}.EBR"
    (folder / name).write_bytes(text.encode("latin-1"))
    (folder / f"TEAM{YEAR}").write_text("")
    args = ["-q", "-y", str(YEAR), *flags, name]
    c = subprocess.run([real_tool(tool) or "", *args], cwd=folder, capture_output=True, check=False)
    p = subprocess.run(
        [sys.executable, "-m", "chadwickpy", tool, *args, "-j", "1"],
        cwd=folder, capture_output=True, check=False,
    )  # fmt: skip
    return (c.returncode, c.stdout), (p.returncode, p.stdout)


@pytest.mark.parametrize("tool", TOOLS)
@pytest.mark.parametrize("case", list(CASES))
def test_matches_the_c_tools(tmp_path: Path, tool: str, case: str) -> None:
    if real_tool(tool) is None:
        pytest.skip("the real Chadwick tools are not installed (set CHADWICK_BIN)")
    c, p = run_both(tmp_path, tool, box_game(**CASES[case]), FLAGS[tool])
    assert c[0] == 0, "the C tool should handle this game"
    assert p == c


# What the C prints, observed on Retrosheet's 1947 Negro Leagues file (no C needed to check these).


@pytest.mark.parametrize(("starttime", "expected"), [("0.375", "1947"), ("6.25E-2", "2547")])
def test_start_time_without_a_colon_prints_the_year_left_over_in_min(
    tmp_path: Path, starttime: str, expected: str
) -> None:
    folder = tmp_path / "w"
    folder.mkdir()
    (folder / f"{YEAR}.EBR").write_bytes(box_game(starttime=starttime).encode())
    (folder / f"TEAM{YEAR}").write_text("")
    done = subprocess.run(
        [sys.executable, "-m", "chadwickpy", "cwgame", "-q", "-y", str(YEAR), "-n", "-f", "0-5",
         "-j", "1", f"{YEAR}.EBR"],
        cwd=folder, capture_output=True, check=True,
    )  # fmt: skip
    header, row = done.stdout.decode().splitlines()
    assert header.split(",")[4] == '"START_GAME_TM"'
    assert row.split(",")[4] == expected


def test_start_time_without_a_colon_and_without_the_day_field_is_refused(tmp_path: Path) -> None:
    """Without the day-of-week field running first the leftover is unknowable, so it stays an error."""
    folder = tmp_path / "w"
    folder.mkdir()
    (folder / f"{YEAR}.EBR").write_bytes(box_game(starttime="0.375").encode())
    (folder / f"TEAM{YEAR}").write_text("")
    done = subprocess.run(
        [sys.executable, "-m", "chadwickpy", "cwgame", "-q", "-y", str(YEAR), "-f", "4",
         f"{YEAR}.EBR"],
        cwd=folder, capture_output=True, check=False,
    )  # fmt: skip
    assert done.returncode != 0 and b"day-of-week field did not run first" in done.stderr
