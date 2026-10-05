"""Port of the parts of Chadwick's ``src/cwtools/cwtools.c`` that every tool shares.

Chadwick is Copyright (c) 2002-2023 Dr T L Turocy and the Chadwick Baseball
Bureau, licensed GPL-2.0-or-later; this module is a derivative of it and keeps
that notice.

``cwtools.c`` is the driver of ``cwevent``, ``cwgame`` and the other tools: it reads the
team file and rosters, reads each event file as a scorebook, picks the games the options
select, and hands each game with its two rosters to the tool. Reading files from disk
and the command line are left to the caller; these functions take bytes.
"""

import re
from collections.abc import Callable, Iterator

from chadwickpy.book import scorebook_read
from chadwickpy.game import Game
from chadwickpy.roster import League, Roster


def read_rosters(team_file: bytes, year: str, roster_file: Callable[[str], bytes | None]) -> League:
    """``cwtools_read_rosters``: the team file, then each team's ``<team><year>.ROS`` if present.

    ``roster_file`` is given a file name and returns its contents, or ``None`` where Chadwick's
    ``fopen`` fails; a missing roster file is silently skipped, as in Chadwick.
    """
    league = League()
    league.read(team_file)
    for roster in league.rosters:
        data = roster_file(f"{roster.team_id}{year}.ROS")
        if data is None:
            continue
        roster.read(data)
    return league


_SSCANF_DATE = re.compile(r"\s*([+-]?\d+)/\s*([+-]?\d+)/\s*([+-]?\d+)")


def game_in_range(game: Game, first: str, last: str) -> bool:
    """``cwtools_game_in_range``: is the game's month and day between ``first`` and ``last``"""
    date = game.info_lookup("date")
    if date is None:
        raise ValueError(f"game {game.game_id} has no date (Chadwick would crash)")
    found = _SSCANF_DATE.match(date)
    if found is None:
        raise ValueError(f"unreadable date {date!r} in {game.game_id} (undefined in Chadwick)")
    month, day = int(found.group(2)), int(found.group(3))
    date_string = f"{month:02d}{day:02d}"
    return first <= date_string <= last


def select_game(game: Game, game_id: str = "", first: str = "0101", last: str = "1231") -> bool:
    """``cwtools_select_game``"""
    return (game_id == "" or game_id == game.game_id) and game_in_range(game, first, last)


def iterate_games(
    data: bytes,
    league: League | None = None,
    game_id: str = "",
    first: str = "0101",
    last: str = "1231",
) -> Iterator[tuple[Game, Roster | None, Roster | None]]:
    """``cwtools_process_scorebook`` + ``cwtools_iterate_games``: the selected games of one event
    file with the visiting and home rosters (``None`` where the team is not in the team file).

    An empty file yields nothing (Chadwick prints "could not open file").
    """
    games = scorebook_read(data)
    if games is None:
        return
    league = league if league is not None else League()
    for game in games:
        if select_game(game, game_id, first, last):
            yield (
                game,
                league.roster_find(game.info_lookup("visteam")),
                league.roster_find(game.info_lookup("hometeam")),
            )


def date_digits(date: str) -> str:
    """The eight characters ``cwgame_date`` and ``cwdaily_date`` print: date[0..3], [5], [6], [8],
    [9] (``YYYYMMDD`` for a ``YYYY/MM/DD`` date), read with ``%c`` and no length check.

    For a date shorter than 10 characters the C reads the string's terminating NUL, which is in
    bounds, as one of those characters. ``printf("%s")`` then stops at it, so the text ends there
    and the rest of the output row is lost. The result holds that NUL (the caller cuts the row at
    it). Where the C would read beyond the terminator the bytes are leftovers, so that raises."""
    out: list[str] = []
    for index in (0, 1, 2, 3, 5, 6, 8, 9):
        if index < len(date):
            out.append(date[index])
        elif index == len(date):
            out.append("\0")
            return "".join(out)
        else:
            raise ValueError(f"date {date!r} is shorter than the C reads (undefined behaviour)")
    return "".join(out)


def cut_at_nul(row: str) -> str:
    """``printf("%s")`` of an output row stops at the first NUL byte that a field wrote."""
    return row.split("\0", 1)[0]
