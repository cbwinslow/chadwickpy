"""Game-state branches of ``gameiter.py`` and ``tools/events.py`` that no season, fixture or random
synthetic game reaches, run through the real ``cwevent`` (every field and extended field).

Each case is a hand-built game. Where the real tool exits cleanly the port must print the same
bytes; where the real tool fails (crash or ``exit(1)``) the port must raise instead of printing
anything.
Task 2.3 of ``openspec/changes/verify-port-completeness``.
"""

import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

import pytest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from chadwick_tool import real_tool, run_tool  # noqa: E402
from test_cwbox_differential import synthetic_rosters  # noqa: E402
from test_event_differential import ALL, EXT, port_output  # noqa: E402
from test_game_targeted_differential import game, head, starts  # noqa: E402

pytestmark = pytest.mark.skipif(real_tool("cwevent") is None, reason="needs cwevent on PATH")

EVENT_ARGS = ["-n", "-f", "0-96", "-x", "0-66"]


def outcome(
    tool: str,
    text: str,
    args: list[str],
    port: Callable[[bytes], bytes],
) -> tuple[bytes | None, bytes | None]:
    """(real output or None if the real tool failed, port output or None if it raised)"""
    data = text.encode("latin-1")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "case.evt"
        path.write_bytes(data)
        real = run_tool(tool, path, args)
    assert real is not None
    try:
        mine: bytes | None = port(data)
    except (ValueError, IndexError, KeyError, TypeError):
        mine = None
    return (real[1] if real[0] == 0 else None), mine


def check(real: bytes | None, mine: bytes | None) -> None:
    if real is None:
        assert mine is None, "the real tool failed but the port printed output"
    else:
        assert mine == real


def play(inning: int, team: int, batter: str, count: str, event: str, pitches: str = "") -> str:
    return f"play,{inning},{team},{batter},{count},{pitches},{event}\n"


def top(*plays: str) -> str:
    """A top half-inning body: the given plays, then strikeouts to end it (and the bottom half)"""
    return (
        "".join(plays)
        + "play,1,0,v7,??,,K\nplay,1,0,v8,??,,K\nplay,1,0,v9,??,,K\n"
        + "play,1,1,h1,??,,K\nplay,1,1,h2,??,,K\nplay,1,1,h3,??,,K\n"
    )


def with_game(body: str) -> str:
    return head() + starts() + body


def event_case(text: str, rosters: bool) -> None:
    data = text.encode("latin-1")
    support = synthetic_rosters(data) if rosters else None

    def mine(d: bytes) -> bytes:
        return port_output(d, True, ALL, EXT, True, support)

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "case.evt"
        path.write_bytes(data)
        real = run_tool("cwevent", path, EVENT_ARGS, support)
    assert real is not None
    try:
        out: bytes | None = mine(data)
    except (ValueError, IndexError, KeyError, TypeError):
        out = None
    check(real[1] if real[0] == 0 else None, out)


SUB_P = 'sub,h10,"Player h10",1,9,1\n'
SUB_PH = 'sub,v10,"Player v10",0,1,11\n'

CASES = {
    # a pitcher comes in at 2-0, 2-1 or 3-x and the batter then walks: the walk is charged to the
    # pitcher who left (gameiter 161 and 391)
    **{
        f"walk_after_pitcher_change_{count}_{ev.lower()}": with_game(
            top(
                play(1, 0, "v1", count, "NP"),
                SUB_P,
                play(1, 0, "v1", count, ev),
                play(1, 0, "v2", "??", "S8.1-2"),
                play(1, 0, "v3", "??", "S9.2-H;1-3"),
            )
        )
        for count in ("20", "21", "30", "31", "32")
        for ev in ("W", "IW", "I")
    },
    # the same pitcher change at a count that does not qualify (the other side of the branch)
    "pitcher_change_at_10": with_game(
        top(play(1, 0, "v1", "10", "NP"), SUB_P, play(1, 0, "v1", "10", "W"))
    ),
    # a pinch hitter comes in at two strikes and strikes out: the strikeout is charged to the
    # replaced batter, with his batting hand (gameiter 407)
    **{
        f"strikeout_pinch_hitter_{hand}": with_game(
            top(
                f"badj,v1,{hand}\n",
                play(1, 0, "v1", "12", "NP"),
                SUB_PH,
                play(1, 0, "v10", "12", "K"),
            )
        )
        for hand in ("L", "R", "B")
    },
    "strikeout_pinch_hitter_no_hand": with_game(
        top(play(1, 0, "v1", "12", "NP"), SUB_PH, play(1, 0, "v10", "12", "K"))
    ),
    "strikeout_pinch_hitter_then_walk": with_game(
        top(
            "badj,v1,L\n",
            play(1, 0, "v1", "12", "NP"),
            SUB_PH,
            play(1, 0, "v10", "12", "W"),
        )
    ),
}

BASES_LOADED = (
    play(1, 0, "v1", "??", "W"),
    play(1, 0, "v2", "??", "W"),
    play(1, 0, "v3", "??", "W"),
)
RUNNERS_1_3 = (play(1, 0, "v1", "??", "S8"), play(1, 0, "v2", "??", "S9.1-3"))
RUNNERS_2_3 = (play(1, 0, "v1", "??", "D8"), play(1, 0, "v2", "??", "S9.2-3;1-2"))

# responsibility when the runner from third is put out on a fielder's choice (gameiter 428, 430)
for i, (prefix, last) in enumerate(
    [
        (BASES_LOADED, "52(3)/FO/G.2-H"),
        (BASES_LOADED, "52(3)/FO.2-H;1-3"),
        (BASES_LOADED, "52(3)/FO.1-H"),
        (RUNNERS_2_3, "52(3)/FO.2-H"),
        (RUNNERS_2_3, "52(3)/FO.2-H;B-1"),
        (RUNNERS_1_3, "52(3)/FO.1-H"),
        (RUNNERS_1_3, "52(3)/FO.1-H;B-2"),
        (RUNNERS_1_3, "FC5/G.3XH(52);1-H"),
        (RUNNERS_1_3, "FC5/G.3XH(52);1-2"),
        (BASES_LOADED, "FC5/G.3XH(52);2-H;1-3"),
        (BASES_LOADED, "FC5/G.3XH(52);2-H"),
    ]
):
    CASES[f"third_out_fc_{i}"] = with_game(top(*prefix, play(1, 0, "v4", "??", last)))

# A pickoff-caught-stealing play whose base character is not 1-4: the parser's po flag is indexed
# by that character (parse.py 832->834) and the C writes past the array, into the struct's
# following fields (undefined behaviour, so the sanitised parser harness cannot be used). With
# 6, 7 and 9 nothing that is printed changes, so the port, which skips the write, matches; with
# 0, 5, 8 and "?" the write lands on a printed field and the C output differs (reported, not
# imitated).
for pocs in ["POCS6(2)", "POCS7(2)", "POCS9(2)", "POCS6(2346)"]:
    CASES[f"pickoff_caught_stealing_{pocs}"] = with_game(
        top(play(1, 0, "v1", "??", "W"), play(1, 0, "v2", "??", pocs))
    )

NO_DATE = game(drop=("date",))


@pytest.mark.parametrize("rosters", [False, True], ids=["no_rosters", "rosters"])
@pytest.mark.parametrize("name", CASES)
def test_case_matches_cwevent(name: str, rosters: bool) -> None:
    event_case(CASES[name], rosters)


def test_game_without_date_matches_cwevent() -> None:
    """A game without a date crashes the C; the port raises (the check is in tools.py)"""
    event_case(NO_DATE, False)
