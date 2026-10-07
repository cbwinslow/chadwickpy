"""Branches of ``tools/daily.py``, ``tools/comment.py``, ``game.py`` and ``tools/tools.py`` reached
only by hand-built games, run through the real ``cwdaily`` and ``cwcomment``.

Box-score files carry ``-1`` for statistics Retrosheet does not know; ``cwdaily`` then prints null
for the total bases of a pitcher and the total chances of a fielder. Task 2.3 of
``openspec/changes/verify-port-completeness``.
"""

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from chadwick_tool import real_tool  # noqa: E402
from test_final_group_b_events import check, outcome, play, top, with_game  # noqa: E402
from test_game_targeted_differential import HOME, LINEUP, game, head  # noqa: E402

from chadwickpy.game import read_games  # noqa: E402
from chadwickpy.gameiter import GameIter  # noqa: E402
from chadwickpy.tools.comment import comment_lines  # noqa: E402
from chadwickpy.tools.comment import header_line as comment_header  # noqa: E402
from chadwickpy.tools.daily import daily_lines  # noqa: E402
from chadwickpy.tools.daily import header_line as daily_header  # noqa: E402
from chadwickpy.tools.tools import date_digits  # noqa: E402

needs_daily = pytest.mark.skipif(real_tool("cwdaily") is None, reason="needs cwdaily on PATH")
needs_comment = pytest.mark.skipif(real_tool("cwcomment") is None, reason="needs cwcomment on PATH")


def daily_port(data: bytes) -> bytes:
    lines = [daily_header(), *daily_lines(data)]
    return "".join(line + "\n" for line in lines).encode("latin-1")


def comment_port(fields: tuple[int, ...]):
    def port(data: bytes) -> bytes:
        lines = [comment_header(fields), *comment_lines(data, fields=fields)]
        return "".join(line + "\n" for line in lines).encode("latin-1")

    return port


def box_game(
    pitching: dict[str, str] | None = None,
    fielding: dict[str, str] | None = None,
    info: dict[str, str] | None = None,
) -> str:
    """A box-score game (starters and ``stat`` records, no plays). ``pitching`` and ``fielding``
    override the starting pitcher's record per team ("0"/"1"); the pitcher is the lineup's ninth."""
    text = head(info)
    for team, lineup in ((0, LINEUP), (1, HOME)):
        for slot, (pid, pos) in enumerate(lineup, 1):
            text += f'start,{pid},"Player {pid}",{team},{slot},{pos}\n'
    for team, lineup in ((0, LINEUP), (1, HOME)):
        for slot, (pid, _pos) in enumerate(lineup, 1):
            text += f"stat,bline,{pid},{team},{slot},1," + ",".join(["2"] * 17) + "\n"
        pid = lineup[8][0]
        text += f"stat,pline,{pid},{team},1," + (pitching or {}).get(str(team), _PLINE) + "\n"
        for pid, pos in lineup:
            rec = (fielding or {}).get(str(team)) if pos == 1 else None
            text += f"stat,dline,{pid},{team},1,{pos}," + (rec or "3,2,1,0,0,0,0") + "\n"
        text += f"stat,tline,{team},1,2,0,0\nline,{team},0,0,0,1,0,0,0,0,0\n"
    return text + "data,er,v9,1\n"


# outs xb bf h b2 b3 hr r er bb ibb so hb wp bk sh sf
_PLINE = "27,0,30,5,1,0,1,2,2,1,0,4,0,0,0,0,0"


def pline(**changes: int) -> str:
    names = "outs xb bf h b2 b3 hr r er bb ibb so hb wp bk sh sf".split()
    values = dict(zip(names, _PLINE.split(","), strict=True))
    values.update({k: str(v) for k, v in changes.items()})
    return ",".join(values[n] for n in names)


DAILY_CASES = {
    "plain_box": box_game(),
    "pitches_info_box": box_game(info={"pitches": "pitches"}),
    **{
        f"unknown_pitching_{stat}": box_game(pitching={"0": pline(**{stat: -1})})
        for stat in ("h", "b2", "b3", "hr")
    },
    **{
        f"unknown_fielding_{i}": box_game(fielding={"1": rec})
        for i, rec in enumerate(["3,-1,1,0,0,0,0", "3,2,-1,0,0,0,0", "3,2,1,-1,0,0,0"])
    },
}


@needs_daily
@pytest.mark.parametrize("name", DAILY_CASES)
def test_box_game_matches_cwdaily(name: str) -> None:
    real, mine = outcome("cwdaily", DAILY_CASES[name], ["-n"], daily_port)
    assert real is not None
    check(real, mine)


# --- cwcomment: ejections and umpire changes -----------------------------------------------

COMMENT_FIELDS = tuple(range(10))
EJECT = (3, 4, 5, 6)


def com(text: str) -> str:
    return f'com,"{text}"\n'


COMMENT_CASES = {
    "ejection_full": top(play(1, 0, "v1", "??", "K"), com("ej,v3,P,u1,arguing balls and strikes")),
    "ejection_short": top(play(1, 0, "v1", "??", "K"), com("ej,v3")),
    "ejection_two": top(play(1, 0, "v1", "??", "K"), com("ej,v3,P")),
    "ejection_no_fields": top(play(1, 0, "v1", "??", "K"), com("ej,")),
    "ejection_before_play": com("ej,v3,M,u1,reason"),
    "ejection_then_plain": top(
        play(1, 0, "v1", "??", "K"), com("ej,v3,P,u1,x"), com("plain after")
    ),
    "plain_then_ejection": top(
        play(1, 0, "v1", "??", "K"), com("plain before"), com("ej,v3,P,u1,x")
    ),
    "ejection_and_umpchange": top(
        play(1, 0, "v1", "??", "K"), com("ej,v3,P,u1,x"), com("umpchange,2,1B,u2")
    ),
    # an umpire change has no ejection, so the ejection fields print empty (comment.py 37)
    "umpchange_only": top(play(1, 0, "v1", "??", "K"), com("umpchange,2,1B,u2")),
    "umpchange_short": top(play(1, 0, "v1", "??", "K"), com("umpchange,2")),
}


@needs_comment
@pytest.mark.parametrize("fields", [COMMENT_FIELDS, EJECT], ids=["all", "ejection"])
@pytest.mark.parametrize("name", COMMENT_CASES)
def test_comment_matches_cwcomment(name: str, fields: tuple[int, ...]) -> None:
    text = with_game(COMMENT_CASES[name])
    args = ["-n", "-f", ",".join(map(str, fields))]
    real, mine = outcome("cwcomment", text, args, comment_port(fields))
    check(real, mine)


@needs_comment
def test_ejection_case_has_output() -> None:
    """guard against a vacuous comparison: the real tool prints the ejection rows"""
    text = with_game(COMMENT_CASES["ejection_full"])
    real, _ = outcome("cwcomment", text, ["-n"], comment_port(COMMENT_FIELDS))
    assert real is not None
    assert b"v3" in real


# --- no C counterpart: the C dereferences a missing date -------------------------------------


def test_iterator_needs_a_date() -> None:
    """``cw_gameiter_reset`` crashes in C on a game without a date record (the tools never get that
    far: ``cwtools_game_in_range`` crashes first, see ``test_game_without_date_matches_cwevent``);
    the port raises"""
    (undated,) = read_games(game(drop=("date",)).encode())
    with pytest.raises(ValueError, match="no date"):
        GameIter(undated)


@pytest.mark.parametrize("date", ["2020/07", "2020"])
def test_date_digits_shorter_than_the_c_reads(date: str) -> None:
    """``cwdaily``'s date field reads fixed positions of the string; the C reads past the end of a
    short date, which is undefined, so the port raises (tools.py 99)"""
    with pytest.raises(ValueError, match="shorter than the C reads"):
        date_digits(date)
