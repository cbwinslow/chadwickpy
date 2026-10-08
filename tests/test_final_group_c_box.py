"""Final coverage pass for ``box.py`` and ``tools/cwbox.py`` (text and XML boxscores).

Hand-built event files that reach the corners the earlier targeted tests do not, compared with the
real Chadwick C code: ``box_dump`` (the C ``cw_box_create`` harness of ``test_box_differential``)
for the boxscore builder, and the real ``cwbox`` program (text and ``-X``; ``-S`` is deprecated,
ADR-002) for the printer.

Outcome of each case, as in ``test_box_targeted_differential``: ``same`` (both succeed with equal
output), ``ub`` (the sanitised C build reports undefined behaviour; the port raises or defines
the value) or ``api`` (a guard of the port that no event file passes through, called directly;
the C has undefined behaviour or crashes there).
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
from chadwick_tool import real_tool  # noqa: E402
from test_box_differential import SRC, build, c_dump, c_is_defined  # noqa: E402
from test_box_targeted_differential import (  # noqa: E402
    NORMAL,
    c_run,
    game,
    header,
    lineup,
    port_run,
    sub,
)
from test_cwbox_differential import normalise  # noqa: E402

from chadwickpy.box import (  # noqa: E402
    BoxEvent,
    BoxFielding,
    BoxPlayer,
    put_fielding,
    set_position_slot,
)
from chadwickpy.file import ReportedError  # noqa: E402
from chadwickpy.game import read_games  # noqa: E402
from chadwickpy.tools import cwbox  # noqa: E402

pytestmark = pytest.mark.skipif(
    shutil.which("gcc") is None
    or not (SRC / "cwlib" / "box.c").exists()
    or real_tool("cwbox") is None,
    reason="needs gcc, the Chadwick sources (CHADWICK_SRC) and cwbox",
)


@pytest.fixture(scope="module")
def harness(tmp_path_factory):
    return build(tmp_path_factory, "plain")


@pytest.fixture(scope="module")
def sanitized(tmp_path_factory):
    return build(
        tmp_path_factory, "san", "-fsanitize=address,undefined", "-fno-sanitize-recover=all"
    )


@pytest.fixture(autouse=True)
def quiet():
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)


# ---------------------------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------------------------


def box_file(extra: str = "", start_pos: dict[int, int] | None = None) -> str:
    """A boxscore-only file; ``start_pos`` replaces the position of visitor slots."""
    visitors = list(NORMAL)
    for slot, pos in (start_pos or {}).items():
        visitors[slot - 1] = pos
    return header() + "".join(lineup("v", 0, visitors)) + "".join(lineup("h", 1, NORMAL)) + extra


class Lineup:
    """Batting-order bookkeeping so that generated plays bat in order (``cwbox`` lints that)."""

    def __init__(self) -> None:
        self.next = [0, 0]

    def play(self, inning: int, team: int, event: str) -> str:
        who = f"{'vh'[team]}{self.next[team] % 9 + 1}"
        self.next[team] += 1
        return f"play,{inning},{team},{who},00,X,{event}\n"

    def half(self, inning: int, team: int, events: list[str]) -> list[str]:
        return [self.play(inning, team, e) for e in events]


def innings_until(n: int, top_n: list[str], pitcher_sub: str | None = None) -> list[str]:
    """Scoreless innings 1..n-1, then the top of inning ``n`` with ``top_n`` (closed by three
    strikeouts when it does not end the half itself), a home pitching change ``pitcher_sub``
    after its second play, and a closing bottom half."""
    order = Lineup()
    plays: list[str] = []
    for inning in range(1, n):
        plays += order.half(inning, 0, ["K"] * 3)
        plays += order.half(inning, 1, ["K"] * 3)
    plays += order.half(n, 0, top_n[:2])
    if pitcher_sub is not None:
        # a substitution is applied with the state *before* the play it follows in the file: the
        # state here is after one batter, none out
        plays.append(pitcher_sub)
    plays += order.half(n, 0, top_n[2:])
    plays += order.half(n, 1, ["K"] * 3)
    return plays


def compare_cwbox(tmp_path, text: str, modes=("text", "xml")) -> None:
    data = text.encode("latin-1")
    for mode in modes:
        args = ["-X"] if mode == "xml" else []
        c = c_run(data, args, tmp_path)
        assert c is not None
        assert c[0] == 0, f"{mode}: the C should succeed"
        out = port_run(data, args)
        assert out is not None, f"{mode}: the port raised"
        assert c[1] != b""
        assert normalise(mode, c[1]) == normalise(mode, out)


# ---------------------------------------------------------------------------------------------
# box.py against cw_box_create
# ---------------------------------------------------------------------------------------------

DH_USERS = {"usedh": "true"}


def dh_game(plays: list[str]) -> str:
    """A game with the DH for the visitors: slot 9 is the DH, the pitcher bats in slot 0."""
    return (
        header(DH_USERS)
        + "".join(lineup("v", 0, [8, 9, 7, 5, 2, 3, 4, 6, 10]))
        + 'start,vp,"VP",0,0,1\n'
        + "".join(lineup("h", 1, NORMAL))
        + "".join(plays)
    )


BOX_SAME = {
    # the DH's pitcher is replaced by a second pitcher (who takes slot 0 with the first one behind
    # him); the second pitcher then assumes a field position, so slot 0 is handed back to the
    # first pitcher (``player->prev`` is set)
    "dh_pitcher_chain": dh_game(
        [
            "play,1,0,v1,00,X,K\n",
            'sub,vp2,"VP2",0,0,1\n',
            'sub,vp2,"VP2",0,5,6\n',
            "play,1,0,v2,00,X,K\n",
        ]
    ),
    # a pickoff-caught-stealing by the pitcher (``pickoff == 1``) and by the catcher
    "pocs_pitcher": game(
        plays=[
            "play,1,0,v1,00,X,S8\n",
            "play,1,0,v2,00,X,POCS2(14)\n",
            "play,1,0,v2,00,X,K\n",
            *["play,1,0,v3,00,X,K\n", "play,1,0,v4,00,X,K\n"],
        ]
    ),
    # a plain pickoff by the catcher
    "po_catcher": game(
        plays=[
            "play,1,0,v1,00,X,S8\n",
            "play,1,0,v2,00,X,PO1(23)\n",
            "play,1,0,v2,00,X,K\n",
            "play,1,0,v3,00,X,K\n",
        ]
    ),
    # a home run scored as an unearned run (advance 5) and a team-unearned one (advance 6)
    "hr_unearned": game(
        plays=[
            "play,1,0,v1,00,X,HR/F9.B-H(UR)\n",
            "play,1,0,v2,00,X,HR/F9.B-H(TUR)\n",
            "play,1,0,v3,00,X,K\n",
            "play,1,0,v4,00,X,K\n",
            "play,1,0,v5,00,X,K\n",
        ]
    ),
    # ground into a triple play
    "triple_play": game(
        plays=[
            "play,1,0,v1,00,X,S8\n",
            "play,1,0,v2,00,X,S8.1-2\n",
            "play,1,0,v3,00,X,5(2)4(1)3(B)/GTP\n",
        ]
    ),
}


@pytest.mark.parametrize("name", BOX_SAME)
def test_box_same_as_chadwick(harness, sanitized, tmp_path, name):
    data = BOX_SAME[name].encode("latin-1")
    expected = c_dump(harness, data, tmp_path)
    assert expected[1] is False
    assert c_is_defined(sanitized, tmp_path), "the C has undefined behaviour here"
    assert dump(data) == expected


BOX_UB = {
    # a starter far below fielding[-1] would overwrite the player's other members
    "start_pos_minus_20": box_file(start_pos={1: -20}),
    "start_pos_minus_25": box_file(start_pos={1: -25}),
    # a dline sequence of -2, -3 or -4 (an unreadable number is -1) writes positions[-3..-5]:
    # pr_inn, ph_inn and the member before them
    "dline_seq_minus_2": box_file("stat,dline,v1,0,-2,8,3,1,0,0,0,0,0\n"),
    "dline_seq_minus_3": box_file("stat,dline,v1,0,-3,8,3,1,0,0,0,0,0\n"),
    "dline_seq_minus_4": box_file("stat,dline,v1,0,-4,8,3,1,0,0,0,0,0\n"),
}


@pytest.mark.parametrize("name", BOX_UB)
def test_box_undefined_behaviour_in_chadwick(harness, sanitized, tmp_path, name):
    data = BOX_UB[name].encode("latin-1")
    c_dump(harness, data, tmp_path)
    assert not c_is_defined(sanitized, tmp_path), (
        "the sanitised C should report undefined behaviour"
    )
    try:
        dump(data)  # the port raises or defines a value; it must not hang or crash
    except ValueError:
        pass


def test_position_slot_helpers_directly():
    """``set_position_slot`` maps the four slots in front of ``positions`` onto the members the C
    writes (``ph_inn`` ... ``start_position``) and refuses anything lower; ``put_fielding``
    refuses a position outside the player record."""
    player = BoxPlayer("p", "P")
    for index, member in ((-1, "start_position"), (-2, "num_positions"), (-3, "pr_inn"),
                          (-4, "ph_inn")):  # fmt: skip
        set_position_slot(player, index, 7)
        assert getattr(player, member) == 7
    with pytest.raises(ValueError):
        set_position_slot(player, -5, 7)
    with pytest.raises(ValueError):
        put_fielding(player, -20, BoxFielding())
    with pytest.raises(ValueError):
        put_fielding(player, 10, BoxFielding())


# ---------------------------------------------------------------------------------------------
# tools/cwbox.py against the cwbox program
# ---------------------------------------------------------------------------------------------

LONG_POSITIONS = game(
    plays=[
        "play,1,0,v1,00,X,K\n",
        sub("v1", 0, 1, 3),
        sub("v1", 0, 1, 4),
        sub("v1", 0, 1, 5),
        sub("v1", 0, 1, 6),
        "play,1,0,v2,00,X,K\n",
        "play,1,0,v3,00,X,K\n",
        "play,1,1,h1,00,X,K\n",
        "play,1,1,h2,00,X,K\n",
        "play,1,1,h3,00,X,K\n",
    ]
)

TEN_RUN_INNING = game(
    plays=[
        *[f"play,1,0,v{i % 9 + 1},00,X,HR/F9\n" for i in range(10)],
        *[f"play,1,0,v{i % 9 + 1},00,X,K\n" for i in range(10, 13)],
        "play,1,1,h1,00,X,K\n",
        "play,1,1,h2,00,X,K\n",
        "play,1,1,h3,00,X,K\n",
    ]
)

CLI_SAME = {
    # a player with five positions prints "name, 3b,..." (position string over 10 characters)
    "positions_long": LONG_POSITIONS,
    # ten runs in an inning print "(10)" in the line score
    "ten_run_inning": TEN_RUN_INNING,
}

# A pitching change after a single batter of the 2nd, 3rd, 12th and 13th inning: the apparatus
# line "Pitched to 1 batter in the Nth" with each ordinal suffix.
for _n in (2, 3, 12, 13):
    CLI_SAME[f"pitched_to_one_in_{_n}"] = game(
        plays=innings_until(_n, ["S8", "K", "K", "K"], sub("hp", 1, 9, 1)),
    )


@pytest.mark.parametrize("name", CLI_SAME)
def test_cwbox_same(tmp_path, name):
    compare_cwbox(tmp_path, CLI_SAME[name])


def test_position_out_of_range_in_printer():
    """``positions[code]`` of the C table is read with a code the lineup checks of ``cwbox``
    (``cw_game_lint``, the substitution checks) never let through, and Chadwick 0.11.0 now
    validates a box score ``dline`` position (1-9) before it is stored (ce175ee), so the printer's
    table is only reached with a legal code. The port refuses a position outside its table anyway;
    a ``dline`` with one is the validation error."""
    assert cwbox._position(-1) == ""
    assert cwbox._position(10) == "dh"
    with pytest.raises(ValueError, match="position 13 out of range"):
        cwbox._position(13)
    games = list(read_games(box_file("stat,dline,v1,0,1,-2,3,1,0,0,0,0,0\n").encode("latin-1")))
    with pytest.raises(ReportedError, match="invalid position -2 in dline record"):
        cwbox.process_game(games[0], None, None)


UNPARSABLE_DATES = ["abc", "2020-01-01", "2020/01-01", "2020/01/x", "2020/01/", "/1/2"]


@pytest.mark.parametrize("date", UNPARSABLE_DATES)
def test_header_refuses_unparsable_date(date):
    """``tools.game_in_range`` already refuses these dates in ``cwbox``; the header refuses them
    too when the printer is called on a game directly (the C reads uninitialised integers)."""
    games = list(read_games(game(info={"date": date}).encode("latin-1")))
    assert len(games) == 1
    with pytest.raises(ValueError):
        cwbox.process_game(games[0], None, None)


def test_event_player_out_of_range():
    """The apparatus reads ``event->players[index]``; an event with fewer players (no event file
    makes one: plays add them all, a box score ``event`` record is only a dp/tp line) is refused
    where the C passes NULL to ``strcmp``."""
    event = BoxEvent()
    event.players = ["only"]
    with pytest.raises(ValueError):
        cwbox._event_player(event, 1)
    assert cwbox._event_player(event, 0) == "only"
    with pytest.raises(ValueError):
        cwbox._print_hbp_apparatus(
            next(iter(read_games(game().encode("latin-1")))), [event], None, None
        )


def test_hbp_apparatus_falls_back_to_player_ids():
    """An HBP event naming players that are in neither roster nor the game's appearance records
    prints the bare ids (``cwbox_print_hbp_apparatus``). Every player a play names is a starter or
    a substitute of the game, so no event file reaches this; the event is built directly."""
    one_game = next(iter(read_games(game().encode("latin-1"))))
    event = BoxEvent()
    event.players = ["zbat", "zpit"]
    assert cwbox._print_hbp_apparatus(one_game, [event], None, None) == "HBP -- by zpit (zbat)\n"
