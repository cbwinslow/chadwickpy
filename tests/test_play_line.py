"""A ``play`` record must be split exactly as the tokenizer would split it, even when damaged."""

import logging
import random

import pytest

from chadwickpy.file import StrTok, cw_atoi
from chadwickpy.game import read_games


def _read_play(line: str):  # type: ignore[no-untyped-def]
    games = list(read_games(f"id,TST201001010\nversion,2\n{line}\n".encode("latin-1")))
    assert len(games) == 1
    return games[0].events


def _tokens(line: str) -> list[str]:
    tok, out = StrTok(), []
    t = tok(line)
    while t is not None:
        out.append(t)
        t = tok(None)
    return out


def test_fields_past_the_sixth_are_ignored() -> None:
    (ev,) = _read_play("play,1,0,aaap1,22,CFBX,8,extra,fields,here")
    assert (ev.inning, ev.batting_team, ev.batter, ev.count, ev.pitches, ev.event_text) == (
        1, 0, "aaap1", "22", "CFBX", "8"
    )  # fmt: skip


def test_leading_spaces_in_fields_are_skipped() -> None:
    (ev,) = _read_play("play, 1, 0, aaap1, 22, CFBX, 8")
    assert ev.batter == "aaap1" and ev.event_text == "8" and ev.inning == 1


def test_quoted_play_field_follows_the_tokenizer() -> None:
    (ev,) = _read_play('play,1,0,aaap1,22,CFBX,"8,3"')
    assert ev.event_text == "8,3"


def test_matches_the_tokenizer_on_random_play_lines(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.ERROR, logger="chadwickpy")  # damaged lines warn; that is expected
    rng = random.Random(1957)
    pieces = ["1", "0", "x", "S8", "22", ' "q" ', ",", ",", ",", " ", "\t", "99", "?", "CFBX"]
    compared = 0
    for _ in range(4000):
        line = "play," + "".join(rng.choice(pieces) for _ in range(rng.randrange(4, 22)))
        want = _tokens(line)[1:]
        got = _read_play(line)
        if len(want) < 6:
            assert got == [], line  # too few fields: Chadwick skips the record
            continue
        assert len(got) == 1, line
        ev = got[0]
        assert (ev.inning, ev.batting_team) == (cw_atoi(want[0]), cw_atoi(want[1])), line
        assert (ev.batter, ev.count, ev.pitches, ev.event_text) == tuple(want[2:6]), line
        compared += 1
    assert compared > 500
