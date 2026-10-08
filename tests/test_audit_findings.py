"""Differences found by auditing every tool against the real C tools, now fixed. Each test runs the
real C tool and the port on a small hand-made game (CRLF line ends, like Retrosheet's files) and
compares stdout, stderr and exit status. Skipped without the C tools (set CHADWICK_BIN)."""

import subprocess
import sys
from pathlib import Path

import pytest
from chadwick_tool import real_tool

YEAR = 2010
NAMES = ["One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
POS = [8, 4, 3, 7, 9, 5, 6, 2, 1]


def _starts(team: str, side: int) -> list[str]:
    return [
        f'start,{team.lower()}p{i + 1},"{team} {n}",{side},{i + 1},{POS[i]}'
        for i, n in enumerate(NAMES)
    ]


def pbp_game(
    *,
    date: str = f"{YEAR}/04/05",
    visteam: str = "BBB",
    start_team: str = "0",
    start_slot: str = "1",
    start_pos: str = "8",
    play_inning: str = "1",
    play_team: str = "0",
    after_first_play: tuple[str, ...] = (),
) -> str:
    lines = [
        f"id,AAA{YEAR}04050",
        "version,2",
        f"info,visteam,{visteam}",
        "info,hometeam,AAA",
        f"info,date,{date}",
        "info,number,0",
        "info,starttime,1:05PM",
        "info,daynight,day",
        "info,usedh,false",
        *_starts("BBB", 0)[1:],
        f'start,bbbp1,"BBB One",{start_team},{start_slot},{start_pos}',
        *_starts("AAA", 1),
        f"play,{play_inning},{play_team},bbbp1,22,CFBX,8",
        *after_first_play,
        "play,1,0,bbbp2,00,X,63",
        "play,1,0,bbbp3,11,CBX,S7",
        "play,1,0,bbbp4,00,X,K",
        "data,er,aaap9,0",
    ]
    return "\r\n".join(lines) + "\r\n"


def box_game_missing_player_field() -> str:
    """A box-score-only game whose `stat,dline` record has no player field at all."""
    lines = [
        f"id,AAA{YEAR}04050",
        "version,5",
        "info,visteam,BBB",
        "info,hometeam,AAA",
        f"info,date,{YEAR}/04/05",
        "info,number,0",
        "info,daynight,day",
        "line,0,0,0,0,0,0,0,0,2,0",
        "line,1,0,0,0,0,0,0,0,0,1",
        "stat,tline,0,7,1,1,0",
        "stat,tline,1,8,2,0,0",
        *_starts("BBB", 0),
        *_starts("AAA", 1),
        "stat,dline",
    ]
    return "\r\n".join(lines) + "\r\n"


def run_both(tmp_path: Path, tool: str, text: str, flags: list[str], name: str = "g.EVA"):  # type: ignore[no-untyped-def]
    exe = real_tool(tool)
    if exe is None:
        pytest.skip("the real Chadwick tools are not installed (set CHADWICK_BIN)")
    folder = tmp_path / "w"
    folder.mkdir(exist_ok=True)
    (folder / name).write_bytes(text.encode("latin-1"))
    (folder / f"TEAM{YEAR}").write_text("")
    args = ["-Q", "-y", str(YEAR), *flags]
    c = subprocess.run([exe, *args, name], cwd=folder, capture_output=True, check=False)
    p = subprocess.run(
        [sys.executable, "-m", "chadwickpy", tool, *args, "-j", "1", name],
        cwd=folder, capture_output=True, check=False,
    )  # fmt: skip
    return c, p


FLAGS = {
    "cwevent": ["-n", "-f", "0-96", "-x", "0-66"],
    "cwgame": ["-n", "-f", "0-85", "-x", "0-96"],
    "cwdaily": ["-n", "-f", "0-153"],
}


@pytest.mark.parametrize("tool", ["cwevent", "cwgame", "cwdaily"])
def test_an_empty_team_id_is_empty_not_null(tmp_path: Path, tool: str) -> None:
    """An empty `info,visteam,` prints "" in the C; only a missing record prints "(null)"."""
    c, p = run_both(tmp_path, tool, pbp_game(visteam=""), FLAGS[tool])
    assert (p.returncode, p.stdout) == (c.returncode, c.stdout)


@pytest.mark.parametrize("tool", ["cwgame", "cwdaily"])
@pytest.mark.parametrize("date", ["2010/04/5", "2010/4/05", "2010/4/5", "10/04/05", "10/4/5"])
def test_a_short_date_ends_the_row_where_the_c_does(tmp_path: Path, tool: str, date: str) -> None:
    """The C reads date[9] (the string's NUL for a 9-character date) and the row stops there."""
    c, p = run_both(tmp_path, tool, pbp_game(date=date), FLAGS[tool])
    assert (p.returncode, p.stdout) == (c.returncode, c.stdout)


def test_invalid_integers_warn_right_to_left(tmp_path: Path) -> None:
    """The C evaluates the arguments of one call right to left, so with two unreadable numbers in a
    start record the warnings come in reverse order (stderr)."""
    text = pbp_game(start_team="x", start_slot="y", start_pos="z")
    c, p = run_both(tmp_path, "cwevent", text, FLAGS["cwevent"])
    assert c.stderr == p.stderr and c.stderr.count(b"Invalid integer value") >= 3
    text = pbp_game(play_inning="x", play_team="y")
    c, p = run_both(tmp_path, "cwevent", text, FLAGS["cwevent"])
    assert c.stderr == p.stderr and c.stderr.count(b"Invalid integer value") >= 2


@pytest.mark.parametrize("tool", ["cwgame", "cwdaily", "cwbox"])
def test_a_fatal_error_the_c_reports_is_reported_once(tmp_path: Path, tool: str) -> None:
    """A fatal box-score error ends the run (exit 1); stderr must carry the message once, as the C
    prints it, not a second time with a prefix. A bare `stat,dline` has no team field, which
    0.11.0 rejects before it looks for the player (it used to be `player '(null)' ... dline`)."""
    text = box_game_missing_player_field()
    c, p = run_both(tmp_path, tool, text, [] if tool == "cwbox" else FLAGS[tool], "g.EBR")
    assert (p.returncode, p.stdout, p.stderr) == (c.returncode, c.stdout, c.stderr)
    assert c.returncode == 1
    assert c.stderr.count(b"invalid team -1 in dline record") == 1


def test_a_player_removed_for_a_pinch_hitter_with_an_empty_id_still_counts_as_removed(
    tmp_path: Path,
) -> None:
    """C asks whether the removed player is NULL, and an empty id is not NULL (cwevent field 87)."""
    text = pbp_game(
        after_first_play=('sub,,"Empty Id",0,2,4', 'sub,bbbph,"Pinch Hitter",0,2,11'),
    )
    c, p = run_both(tmp_path, "cwevent", text, FLAGS["cwevent"])
    assert (p.returncode, p.stdout, p.stderr) == (c.returncode, c.stdout, c.stderr)
