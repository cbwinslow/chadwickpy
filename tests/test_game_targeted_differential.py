"""Targeted ``cwgame`` / game-record cases against the real ``cwgame``.

Each case is hand-built event-file text that reaches a branch of ``game.py`` or ``tools/cwgame.py``
that the season files and the random synthetic games never do. Every case runs the real
``cwgame`` (ASCII, every field and extended field, header off) and the port; where the real tool
exits cleanly the output must match byte for byte, where it fails (crash or ``exit(1)``) the port
must raise rather than print something else.
"""

import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from chadwick_tool import real_tool, run_tool  # noqa: E402
from test_game_differential import ALL, EXT  # noqa: E402

from chadwickpy.game import Event, Game, read_games  # noqa: E402
from chadwickpy.tools.cwgame import game_line, game_lines  # noqa: E402

pytestmark = pytest.mark.skipif(real_tool("cwgame") is None, reason="needs cwgame on PATH")

LINEUP = [
    ("v1", 2),
    ("v2", 8),
    ("v3", 3),
    ("v4", 5),
    ("v5", 6),
    ("v6", 4),
    ("v7", 7),
    ("v8", 9),
    ("v9", 1),
]
HOME = [
    ("h1", 2),
    ("h2", 8),
    ("h3", 3),
    ("h4", 5),
    ("h5", 6),
    ("h6", 4),
    ("h7", 7),
    ("h8", 9),
    ("h9", 1),
]


def head(
    info: dict[str, str] | None = None, drop: tuple[str, ...] = (), gid: str = "HOM202007020"
) -> str:
    base = {
        "visteam": "VIS",
        "hometeam": "HOM",
        "date": "2020/07/02",
        "number": "0",
        "usedh": "false",
        "site": "TST01",
    }
    base.update(info or {})
    for key in drop:
        base.pop(key, None)
    text = f"id,{gid}\nversion,2\n"
    text += "".join(f"info,{k},{v}\n" for k, v in base.items())
    return text


def starts() -> str:
    out = ""
    for team, lineup in ((0, LINEUP), (1, HOME)):
        for slot, (pid, pos) in enumerate(lineup, 1):
            out += f'start,{pid},"Player {pid}",{team},{slot},{pos}\n'
    return out


def plays(extra: str = "") -> str:
    return (
        "play,1,0,v1,??,,K\nplay,1,0,v2,??,,K\nplay,1,0,v3,??,,K\n"
        + extra
        + "play,1,1,h1,??,,K\nplay,1,1,h2,??,,K\nplay,1,1,h3,??,,K\n"
    )


def game(
    info: dict[str, str] | None = None, drop: tuple[str, ...] = (), body: str | None = None
) -> str:
    return head(info, drop) + starts() + (plays() if body is None else body)


def outcome(
    text: str, fields: tuple[int, ...] = ALL, ext: tuple[int, ...] = EXT, wide: bool = False
) -> tuple[bytes | None, bytes | None]:
    """(real output or None if it failed, port output or None if it raised); ASCII, no header"""
    data = text.encode("latin-1")
    args = ["-n", "-f", ",".join(map(str, fields)) or "0"]
    if wide:
        args += ["-s", "0000", "-e", "9999"]
    if ext:
        args += ["-x", ",".join(map(str, ext))]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "case.evt"
        path.write_bytes(data)
        real = run_tool("cwgame", path, args)
    assert real is not None
    try:
        dates = {"first_date": "0000", "last_date": "9999"} if wide else {}
        lines = list(game_lines(data, ascii_=True, fields=fields, ext_fields=ext, **dates))
        port: bytes | None = "".join(line + "\n" for line in lines).encode("latin-1")
    except (ValueError, IndexError, KeyError, TypeError):
        port = None
    if real[0] != 0:
        return None, port
    return real[1].split(b"\n", 1)[1], port


def many(kind: str, n: int = 300) -> str:
    return kind + "," + ",".join(["a"] * n) + "\n"


def boxgame(extra: str, info: dict[str, str] | None = None) -> str:
    return head(info) + starts() + extra


def _bpl(n: int) -> str:
    return ",".join(["1"] * n)


DOW, DATE = (3,), (1,)
ALLF = tuple(range(46))
CASES: dict[str, tuple[str, tuple[int, ...], tuple[int, ...]]] = {
    "dow_plain": (game(), DOW, ()),
    "dow_no_date": (game(drop=("date",)), DOW, ()),
    "date_no_date": (game(drop=("date",)), DATE, ()),
    "dow_unparsable": (game({"date": "garbage"}), DOW, ()),
    "dow_year_no_slash": (game({"date": "2020-07-02"}), DOW, ()),
    "dow_month_no_slash": (game({"date": "2020/07-02"}), DOW, ()),
    "dow_no_day": (game({"date": "2020/07/"}), DOW, ()),
    "dow_two_digit_year": (game({"date": "20/07/02"}), DOW, ()),
    "dow_month13_filtered_out": (game({"date": "2020/13/02"}), DOW, ()),
    "date_short": (game({"date": "2020/7/2"}), DATE, ()),
    "date_short_all": (game({"date": "2020/7/2"}), ALLF, ()),
    "dow_jan": (game({"date": "2020/01/02"}), DOW, ()),
    "bline_short": (boxgame("stat,bline,v1,0,1,1\n"), tuple(range(46)) + (84,), ()),
    "bline_short_all": (boxgame("stat,bline,v1,0,1,1\nstat,bline,h1,1,1,1\n"), ALL, EXT),
    "dline_short": (boxgame("stat,dline,v1,0,1,2\n"), ALL, EXT),
    "dline_short_home": (boxgame("stat,dline,h1,1,1,2,1\nstat,dline,v1,0,1,2,1,1\n"), ALL, EXT),
    "line49": (boxgame("line,0," + _bpl(49) + "\nline,1," + _bpl(49) + "\n"), ALL, EXT),
    "line5": (boxgame("line,0," + _bpl(5) + "\nline,1,1,x,3\n"), ALL, EXT),
    "line_10plus": (boxgame("line,0,1,12,3\nline,1,0,x,15\n"), ALL, EXT),
    "version_empty": (game().replace("version,2", "version,"), ALL, EXT),
    "com_empty": (game(body=plays("com,\n")), ALL, EXT),
    "data_overflow": (game(body=plays() + many("data")), ALL, EXT),
    "stat_overflow": (game(body=plays() + many("stat")), ALL, EXT),
    "event_overflow": (game(body=plays() + many("event")), ALL, EXT),
    "line_overflow": (game(body=plays() + many("line")), ALL, EXT),
    "radj_short": (game(body=plays("radj,v1\n")), ALL, EXT),
    "presadj_short": (game(body=plays("presadj,v1\n")), ALL, EXT),
    "padj_before_play": (game(body="padj,h9,L\n" + plays()), ALL, EXT),
    "badj_slow_play": (
        game(body=plays('badj,v1,L\nplay,1,0,v1,??,,"K"\n')),
        ALL,
        EXT,
    ),
    "padj_slow_play": (
        game(body=plays('padj,h9,L\nplay,1,0,v1,??,,"K"\n')),
        ALL,
        EXT,
    ),
    "badj_no_event": (game(body="badj,v1,L\nplay,1,0\n" + plays()), ALL, EXT),
    "padj_no_event": (game(body="padj,v1,L\nplay,1,0\n" + plays()), ALL, EXT),
    "ladj_no_event": (game(body="ladj,0,3\nplay,1,0\n" + plays()), ALL, EXT),
    "radj_no_event": (game(body="radj,v1,2\nplay,1,0\n" + plays()), ALL, EXT),
    "presadj_no_event": (game(body="presadj,v1,2\nplay,1,0\n" + plays()), ALL, EXT),
    "sub_no_event": (game(body='sub,v1x,"X",0,1,2\n' + plays()), ALL, EXT),
}

# Cases where the two programs differ on purpose or where the C is undefined; each is asserted as
# recorded, so a change on either side is noticed.
KNOWN: dict[str, tuple[str, tuple[int, ...], tuple[int, ...]]] = {
    # month 0 or 13 (needs -s/-e to pass the date filter): get_day_of_week indexes its 12-entry
    # table out of bounds; the port raises instead of imitating the over-read
    "dow_month13": (game({"date": "2020/13/02"}), DOW, ()),
    "dow_month0": (game({"date": "2020/00/02"}), DOW, ()),
    # info,date shorter than 10 characters: cwgame copies date[5:7] and date[8:10] past the end of
    # the string; the port raises instead of imitating the over-read
    "date_short": CASES.pop("date_short"),
    "date_short_all": CASES.pop("date_short_all"),
    # badj and then a play record with no fields, before any play: the C compares the missing
    # batter with strcmp (crash); the port treats a missing batter as no match
    "badj_no_event": CASES.pop("badj_no_event"),
    # 60 line scores: the C writes past linescore[50][2] into the totals that follow it
    "line60": (boxgame("line,0," + _bpl(60) + "\n"), ALL, EXT),
}


# The same, with ``-s 0000 -e 9999`` so that months outside 1-12 pass the date filter
WIDE: dict[str, tuple[str, tuple[int, ...], tuple[int, ...]]] = {
    "dow_spaced": (game({"date": "2020/ 7/ 2"}), DOW, ()),
    "dow_signed": (game({"date": "+2020/+7/+2"}), DOW, ()),
    "dow_year0": (game({"date": "0/07/02"}), DOW, ()),
    "dow_year100": (game({"date": "100/07/02"}), DOW, ()),
}


@pytest.mark.parametrize("name", sorted(WIDE))
def test_wide_case_matches_cwgame(name: str) -> None:
    text, fields, ext = WIDE[name]
    real, port = outcome(text, fields, ext, wide=True)
    if real is None:
        assert port is None, "cwgame fails here, the port must raise too"
    else:
        assert port == real


@pytest.mark.parametrize("name", sorted(CASES))
def test_case_matches_cwgame(name: str) -> None:
    text, fields, ext = CASES[name]
    real, port = outcome(text, fields, ext)
    if real is None:
        assert port is None, "cwgame fails here, the port must raise too"
    else:
        assert port == real


def test_known_differences_are_as_recorded() -> None:
    for name in ("date_short", "date_short_all"):  # matched since #24 (reads past the date like C)
        real, port = outcome(*KNOWN[name])
        assert real is not None and port == real
    for name in ("dow_month13", "dow_month0"):
        real, port = outcome(*KNOWN[name], wide=True)
        assert real is not None and port is None
    real, port = outcome(*KNOWN["badj_no_event"])
    assert real is None and port is not None
    real, port = outcome(*KNOWN["line60"])
    assert real is not None and port is not None and real != port


# Guards for C undefined behaviour in the record API that no event file can reach: nothing in the
# package calls these three methods, and ``data`` tuples never hold ``None`` (a record with 256
# tokens is dropped by the reader).
def test_api_guards() -> None:
    g = Game("X")
    with pytest.raises(ValueError):
        g.truncate(Event(1, 0, "b", "", "", "K"))
    with pytest.raises(ValueError):
        g.substitute_append("p", "P", 0, 1, 2)
    g.data_append(["er", "p", "1"])
    with pytest.raises(ValueError):
        g.data_set_er("p", 10**9)
    g.data_append([None, "p", "1"])
    with pytest.raises(ValueError):
        g.data_set_er("q", 1)
    assert [x.game_id for x in read_games(game().encode())] == ["HOM202007020"]


# ``cwgame`` selects games by date before it prints a field, and the port's selection raises for a
# game with no date or one that ``sscanf("%d/%d/%d")`` cannot read; so through the tool the dow
# field never sees such a game. Called directly it guards the same C undefined behaviour (an
# uninitialised read), which the port reports as an error. Unreachable: ``_date`` with no date
# (line 45) and ``_day_of_week`` with no date (line 168), because ``box_create`` and ``GameIter``
# both raise on a game with no date first.
@pytest.mark.parametrize(
    ("info", "drop", "field"),
    [
        ({"date": "garbage"}, (), 3),
        ({"date": "2020-07-02"}, (), 3),
        ({"date": "2020/07-02"}, (), 3),
        ({"date": "2020/07/"}, (), 3),
    ],
    ids=["dow_garbage", "dow_no_slash1", "dow_no_slash2", "dow_no_day"],
)
def test_date_fields_reject_unreadable_dates(
    info: dict[str, str], drop: tuple[str, ...], field: int
) -> None:
    (parsed,) = read_games(game(info, drop).encode())
    with pytest.raises(ValueError):
        game_line(parsed, None, None, True, (field,), ())
