"""Hand-built games that reach the odd corners of ``box.py`` and ``tools/cwbox.py``.

Each case is a small event file fed to the real Chadwick C code and to the port:

* ``box_dump`` (the C ``cw_box_create`` harness of ``test_box_differential``) for the boxscore
  builder, without ``cwbox``'s sanity check in front of it;
* the real ``cwbox`` program (text and ``-X``; ``-S`` is deprecated, ADR-002) for the printer.

Every case states what the C does. ``same``: both succeed with identical output. ``fail``: the C
exits or crashes and the port raises. ``ub``: the C has undefined behaviour here (an out-of-range
array index, a read of an uninitialised value); the sanitised C build must report it, and the
port raises ``ValueError`` where it can, or defines the value. Runs only where ``gcc`` and the
Chadwick sources (``CHADWICK_SRC``) and the ``cwbox`` binary are available.
"""

import logging
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "reference"))
sys.path.insert(0, str(HERE))
from box_dump import dump  # noqa: E402
from chadwick_tool import real_tool, run_tool  # noqa: E402
from test_box_differential import SRC, build, c_dump, c_is_defined  # noqa: E402
from test_cwbox_differential import normalise, port_output  # noqa: E402

pytestmark = pytest.mark.skipif(
    shutil.which("gcc") is None
    or not (SRC / "cwlib" / "box.c").exists()
    or real_tool("cwbox") is None,
    reason="needs gcc, the Chadwick sources (CHADWICK_SRC) and cwbox",
)

PORT_ERRORS = (ValueError, IndexError)

# ---------------------------------------------------------------------------------------------
# Event-file builders
# ---------------------------------------------------------------------------------------------

# slot -> fielding position of a normal lineup (slot 1 is the first entry)
NORMAL = [8, 9, 7, 5, 2, 3, 4, 6, 1]
NO_PITCHER = [8, 9, 7, 5, 2, 3, 4, 6, 3]
THREE_UP = [
    "play,1,0,v1,00,X,K\n",
    "play,1,0,v2,00,X,K\n",
    "play,1,0,v3,00,X,K\n",
    "play,1,1,h1,00,X,K\n",
    "play,1,1,h2,00,X,K\n",
    "play,1,1,h3,00,X,K\n",
]


def lineup(prefix: str, team: int, positions: list[int]) -> list[str]:
    return [
        f'start,{prefix}{i},"{prefix.upper()} N{i}",{team},{i},{pos}\n'
        for i, pos in enumerate(positions, 1)
    ]


def header(info: dict[str, str] | None = None) -> str:
    fields = {
        "visteam": "AAA",
        "hometeam": "BBB",
        "date": "2020/01/01",
        "number": "0",
        "daynight": "night",
        "usedh": "false",
        "timeofgame": "120",
    }
    fields.update(info or {})
    return "id,TST202001010\nversion,2\n" + "".join(f"info,{k},{v}\n" for k, v in fields.items())


def game(
    visitors: list[int] | None = None,
    home: list[int] | None = None,
    plays: list[str] | None = None,
    info: dict[str, str] | None = None,
) -> str:
    """A play-by-play game; ``visitors``/``home`` are the fielding positions of slots 1-9."""
    return (
        header(info)
        + "".join(lineup("v", 0, visitors or NORMAL))
        + "".join(lineup("h", 1, home or NORMAL))
        + "".join(plays if plays is not None else THREE_UP)
    )


def box_file(extra: str = "") -> str:
    """A boxscore-only file (no plays), plus ``extra`` records."""
    return header() + "".join(lineup("v", 0, NORMAL)) + "".join(lineup("h", 1, NORMAL)) + extra


def dh_box_file(extra: str = "") -> str:
    """A boxscore-only file whose visitors have a DH and a starting pitcher in slot 0."""
    return (
        header({"usedh": "true"})
        + "".join(lineup("v", 0, [8, 9, 7, 5, 2, 3, 4, 6, 10]))
        + 'start,vp,"VP",0,0,1\n'
        + "".join(lineup("h", 1, NORMAL))
        + extra
    )


def sub(player: str, team: int, slot: int, pos: int) -> str:
    return f'sub,{player},"{player.upper()}",{team},{slot},{pos}\n'


# ---------------------------------------------------------------------------------------------
# The boxscore builder (box.py) against cw_box_create
# ---------------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def harness(tmp_path_factory):
    return build(tmp_path_factory, "plain")


@pytest.fixture(scope="module")
def sanitized(tmp_path_factory):
    try:
        return build(
            tmp_path_factory, "san", "-fsanitize=address,undefined", "-fno-sanitize-recover=all"
        )
    except Exception:  # noqa: BLE001 - any build failure means no sanitizers here
        pytest.skip("this gcc cannot build with sanitizers")


@pytest.fixture(autouse=True)
def quiet():
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)


BOX_SAME = {
    # a pitcher subbed in later, DH-free: the plain paths (control)
    "sub_pitcher": game(
        plays=[THREE_UP[0], sub("vp", 0, 9, 1), *THREE_UP[1:]],
    ),
    # a stat line of a player not in the box score is only legal for the phline/prline kinds
    # (0.11.0: the team is validated, so the lines need a team; phline/prline also put PH/PR in
    # the player's position list, a036277)
    "phline_prline": box_file("stat,phline,v2,7,0\nstat,prline,v3,5,0\n"),
    # a bline whose slot-zero sequence is 0 for the starting pitcher (e1f1f30)
    "bline_zero_seq_starter": dh_box_file("stat,bline,vp,0,0,0,3,0,0\n"),
    "bline_zero_seq_starter_other_id": dh_box_file("stat,bline,xx,0,0,0,3,0,0\n"),
    # dline with a sequence beyond the entries so far, at a legal position
    "dline_ok": box_file("stat,dline,v1,0,1,8,3,1,0,0,0,0,0\n"),
    # a double-play line of 20 players (the C array holds exactly 20)
    "dpline_20": box_file("event,dpline,0," + ",".join(f"p{i}" for i in range(20)) + "\n"),
    # an ``event`` record of a kind the boxscore does not use is skipped
    "evdata_other": box_file("event,xxline,0,a,b\n"),
    # a game of 49 innings: the whole of the C linescore array
    "line_49": box_file("line,0," + ",".join(["1"] * 49) + "\n"),
    # a play inning of 0 and of 60 (the port's linescore grows; the C reads past 50 rows only
    # when it is below 0 or above 49, and writes zeros that nothing reads)
    "inning_zero": game(plays=["play,0,0,v1,00,X,K\n"]),
}

BOX_FAIL = {
    # cw_box_add_substitute exits on a bad slot, team or position
    "sub_slot_10": game(plays=[THREE_UP[0], sub("x", 0, 10, 5), *THREE_UP[1:3]]),
    "sub_slot_neg": game(plays=[THREE_UP[0], sub("x", 0, -1, 5), *THREE_UP[1:3]]),
    "sub_team_2": game(plays=[THREE_UP[0], sub("x", 2, 1, 5), *THREE_UP[1:3]]),
    "sub_team_neg": game(plays=[THREE_UP[0], sub("x", -1, 1, 5), *THREE_UP[1:3]]),
    "sub_pos_13": game(plays=[THREE_UP[0], sub("x", 0, 1, 13), *THREE_UP[1:3]]),
    "sub_pos_0": game(plays=[THREE_UP[0], sub("x", 0, 1, 0), *THREE_UP[1:3]]),
    # a team without a pitcher: the first plate appearance exits (batter_stats)
    "no_pitcher_home": game(home=NO_PITCHER),
    "no_pitcher_visitors": game(visitors=NO_PITCHER),
    # ... also when the pitches are tabulated first (pitch_stats logs and returns, then
    # batter_stats exits)
    "no_pitcher_pitches": game(
        visitors=NO_PITCHER, home=NO_PITCHER, plays=["play,1,0,v1,01,CX,K\n", *THREE_UP[1:]]
    ),
    "no_pitcher_pitches_home": game(
        home=NO_PITCHER, plays=["play,1,0,v1,01,CX,K\n", *THREE_UP[1:]]
    ),
    # a pitching change for a team that never had a pitcher: NULL dereference (the event before
    # it is an NP, which does not reach batter_stats)
    "sub_pitcher_no_pitcher_v": game(
        visitors=NO_PITCHER, plays=["play,1,0,v1,00,,NP\n", sub("vp", 0, 3, 1), THREE_UP[1]]
    ),
    "sub_pitcher_no_pitcher_h": game(
        home=NO_PITCHER, plays=["play,1,0,v1,00,,NP\n", sub("hp", 1, 3, 1), THREE_UP[1]]
    ),
    # Chadwick 0.11.0 validates team, slot and position in a boxscore event file (ce175ee): a team
    # index of 2 or a dline sequence of 0 or 41 used to index outside the arrays (undefined
    # behaviour); they are now a reported error and exit(1)
    "dline_team_2": box_file("stat,dline,v1,2,1,8,3,1,0,0,0,0,0\n"),
    "dline_seq_0": box_file("stat,dline,v1,0,0,8,3,1,0,0,0,0,0\n"),
    "dline_seq_41": box_file("stat,dline,v1,0,41,8,3,1,0,0,0,0,0\n"),
    "tline_team_2": box_file("stat,tline,2,3,1,0,0\n"),
    "line_team_2": box_file("line,2,1,0,2\n"),
    "pline_team_2": box_file("stat,pline,v1,2,1,3,10,0,0\n"),
    "bline_team_2": box_file("stat,bline,v1,2,1,1,4,0,0\n"),
    "bline_slot_10": box_file("stat,bline,v1,0,10,1,4,0,0\n"),
    "bline_slot_neg": box_file("stat,bline,v1,0,-1,1,4,0,0\n"),
    # ... a missing team reads as -1
    "phline_no_team": box_file("stat,phline,v2,7\n"),
    "dline_pos_0": box_file("stat,dline,v1,0,1,0,3,1,0,0,0,0,0\n"),
    "phline_team_2": box_file("stat,phline,v2,7,2\n"),
    "prline_team_neg": box_file("stat,prline,v3,5,-1\n"),
    "dpline_team_2": box_file("event,dpline,2,a,b\n"),
    "tpline_team_2": box_file("event,tpline,2,a,b,c\n"),
    # box-score lines naming players that are not in the game
    "dline_unknown": box_file("stat,dline,zz,0,1,5,3,1,0,0,0,0,0\n"),
    "dline_pos_10": box_file("stat,dline,v1,0,1,10,3,1,0,0,0,0,0\n"),
    "phline_unknown": box_file("stat,phline,zz,7\n"),
    "prline_unknown": box_file("stat,prline,zz,7\n"),
}

BOX_UB = {
    # a starter at a negative position indexes fielding[-1]
    "start_pos_neg": game(visitors=[-1, *NORMAL[1:]]),
    # positions[] holds 40 entries; the 41st write goes into the next member of the struct
    "positions_46": game(
        plays=[THREE_UP[0], *[sub("v1", 0, 1, 2 + i % 10) for i in range(45)], THREE_UP[1]]
    ),
    "positions_46_same": game(
        plays=[THREE_UP[0], *[sub("v1", 0, 1, 8)] * 45, THREE_UP[1]],
    ),
    # event->players[] holds 20 pointers
    "dpline_23": box_file("event,dpline,0," + ",".join(f"p{i}" for i in range(23)) + "\n"),
    # linescore[50][2]: the 51st inning is outside
    "line_55": box_file("line,0," + ",".join(["1"] * 55) + "\n"),
    # a negative inning on a later play: linescore[-2]
    "inning_negative": game(plays=["play,-1,0,v1,00,X,K\n", "play,-2,1,h1,00,X,K\n"]),
}


@pytest.mark.parametrize("name", BOX_SAME)
def test_box_same_as_chadwick(harness, sanitized, tmp_path, name):
    data = BOX_SAME[name].encode("latin-1")
    expected = c_dump(harness, data, tmp_path)
    assert expected[1] is False
    assert c_is_defined(sanitized, tmp_path), "the C has undefined behaviour here"
    assert dump(data) == expected


@pytest.mark.parametrize("name", BOX_FAIL)
def test_box_failure_same_as_chadwick(harness, tmp_path, name):
    data = BOX_FAIL[name].encode("latin-1")
    expected = c_dump(harness, data, tmp_path)
    assert expected[1] is True, "the C should exit or crash here"
    assert dump(data) == expected  # the port raised too (dump reports it as a flag)


@pytest.mark.parametrize("name", BOX_UB)
def test_box_undefined_behaviour_in_chadwick(harness, sanitized, tmp_path, name):
    data = BOX_UB[name].encode("latin-1")
    c_dump(harness, data, tmp_path)
    assert not c_is_defined(sanitized, tmp_path), (
        "the sanitised C should report undefined behaviour"
    )
    dump(data)  # the port raises or defines a value; it must not hang or crash


# ---------------------------------------------------------------------------------------------
# The cwbox printer (tools/cwbox.py) against the cwbox program
# ---------------------------------------------------------------------------------------------

CLI_SAME = {
    # info,daynight,g_day prints " (D)" (the C compares with "g_day", not "day")
    "daynight_g_day": game(info={"daynight": "g_day"}),
    "daynight_day": game(info={"daynight": "day"}),
    "date_trailing_text": game(info={"date": "2020/01/01x"}),
    "timeofgame_text": game(info={"timeofgame": "abc"}),
    "timeofgame_minutes": game(info={"timeofgame": "197"}),
    # a batting line without the RBI column prints no RBI total
    "bline_without_rbi": box_file("stat,bline,v1,0,1,8,4,1,1,0,0\n"),
    "bline_with_rbi": box_file("stat,bline,v1,0,1,8,4,1,1,0,0,2,0,0,0,0,0,0,0,0\n"),
    "bline_one_team_without_rbi": box_file(
        "stat,bline,v1,0,1,8,4,1,1,0,0\nstat,bline,h1,1,1,8,4,1,1,0,0,3,0,0,0,0,0,0,0,0\n"
    ),
    # 49 innings: the linescore loop runs to its limit of 50 rows without a break
    "linescore_49": box_file(
        "line,0," + ",".join(["1"] * 49) + "\nline,1," + ",".join(["0"] * 49) + "\n"
    ),
}

CLI_FAIL = {
    # no date: the C reads NULL; an unparsable date aborts it
    "no_date": game().replace("info,date,2020/01/01\n", ""),
    "date_dashes": game(info={"date": "2020-01-01"}),
    "date_unreadable": game(info={"date": "abc"}),
    "no_number_text": game().replace("info,number,0\n", ""),
}

CLI_UB = {
    # sscanf("%d/%d/%d") stops after the month, so cwtools_game_in_range tests an uninitialised
    # day (0.11.0: the real cwbox now exits 0 with no output; the 0.10 build crashed)
    "date_month_only": game(info={"date": "2020/01"}),
    # an empty timeofgame makes the C read an uninitialised number
    "timeofgame_empty": game(info={"timeofgame": '""'}),
}


def port_run(data: bytes, args: list[str]) -> bytes | None:
    try:
        return port_output(data, None, "-X" in args)
    except PORT_ERRORS:
        return None


def c_run(data: bytes, args: list[str], tmp_path: Path) -> tuple[int, bytes] | None:
    path = tmp_path / "x.evt"
    path.write_bytes(data)
    return run_tool("cwbox", path, args)


@pytest.mark.parametrize("args", [[], ["-X"]], ids=["text", "xml"])
@pytest.mark.parametrize("name", CLI_SAME)
def test_cwbox_same(tmp_path, name, args):
    data = CLI_SAME[name].encode("latin-1")
    mode = "xml" if args else "text"
    c = c_run(data, args, tmp_path)
    assert c is not None
    assert c[0] == 0
    out = port_run(data, args)
    assert out is not None
    assert normalise(mode, c[1]) == normalise(mode, out)


@pytest.mark.parametrize("args", [[], ["-X"]], ids=["text", "xml"])
@pytest.mark.parametrize("name", CLI_FAIL)
def test_cwbox_failure(tmp_path, name, args):
    """Where the C fails the port raises; where the C succeeds (a field the XML never reads) the
    outputs must be equal."""
    data = CLI_FAIL[name].encode("latin-1")
    mode = "xml" if args else "text"
    c = c_run(data, args, tmp_path)
    assert c is not None
    out = port_run(data, args)
    if c[0] != 0:
        assert out is None
    else:
        assert out is not None
        assert normalise(mode, c[1]) == normalise(mode, out)


@pytest.mark.parametrize("name", CLI_UB)
def test_cwbox_uninitialised_value(tmp_path, name):
    """The C succeeds with a value taken from an uninitialised variable; the port refuses the
    input rather than guess it."""
    data = CLI_UB[name].encode("latin-1")
    c = c_run(data, [], tmp_path)
    assert c is not None
    assert c[0] == 0
    assert port_run(data, []) is None
