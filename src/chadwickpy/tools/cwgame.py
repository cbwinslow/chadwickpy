"""Port of Chadwick's ``cwgame`` (``src/cwtools/cwgame.c``), the game descriptor generator.

Chadwick is Copyright (c) 2002-2026 Dr T L Turocy and the Chadwick Baseball
Bureau, licensed GPL-2.0-or-later; this module is a derivative of it and keeps
that notice. One function per ``cwgame`` field, each writing to a ``CWBuffer`` what the C
``cw_buffer_emit*`` calls write; ``FIELDS`` and ``EXT_FIELDS`` are the C ``field_data`` and
``ext_field_data`` tables (function, header, description) in the same order. The
C declares the tabulated team totals with macros (``DECLARE_TABULATED_*_FUNC``);
the port builds the same functions with the factories below. The buffer's
``use_delimiter`` is the C global ``ascii``: true for the comma-delimited quoted format (``-a``,
the default), false for the fixed-width Fortran format (``-ft``).

A C ``NULL`` string printed through ``%s`` is "(null)" (glibc). Where the C dereferences ``NULL``,
reads an uninitialised variable (a short date, an unparsable start time) or indexes an array out
of range, this port raises ``ValueError``. Like the C, each line is built in a 4096-byte buffer
and a line that does not fit is an error (``BufferTruncated``, the C's ``exit(1)``). Entries of
``FIELDS`` that are ``None`` (lineup and finishing pitcher fields, 46-83) are written by
``game_line`` itself, as in the C.
"""

from collections.abc import Callable, Collection, Iterator
from typing import TypeVar

from chadwickpy.box import (
    BoxPitcher,
    BoxPlayer,
    Boxscore,
    box_create,
    get_starter,
    get_starting_pitcher,
)
from chadwickpy.file import cw_atoi, scan_int
from chadwickpy.game import Game
from chadwickpy.gameiter import GameIter
from chadwickpy.roster import League, Roster
from chadwickpy.tools.tools import cut_at_nul, date_digits, iterate_games

# Format of the gamedate field (-dsf, -dsp, -dnf, -dnp). Unlike BGAME, whose default is a
# two-digit year, cwgame defaults to a four-digit year (no slashes).
CWGAME_DATE_NOSLASH_FULL = 0
CWGAME_DATE_NOSLASH_PARTIAL = 1
CWGAME_DATE_SLASH_FULL = 2
CWGAME_DATE_SLASH_PARTIAL = 3

BUFFER_SIZE = 4096  # ``char output_line[4096]``


class BufferTruncated(ValueError):
    """The line (or header) does not fit the C's 4096-byte buffer: the C prints ``message`` to
    stderr and calls ``exit(1)``"""


class CWBuffer:
    """``buffer.h``: a bounded output buffer with an optional field delimiter"""

    def __init__(self, size: int, use_delimiter: bool, delimiter: str = ",") -> None:
        self.size = size
        self.length = 0  # ``current - storage``
        self.parts: list[str] = []
        self.truncated = False
        self.need_sep = False
        self.field_open = False
        self.use_delimiter = use_delimiter
        self.delimiter = delimiter

    def text(self) -> str:
        return "".join(self.parts)

    def emit(self, text: str) -> int:
        """``cw_buffer_emit``, given the already formatted ``text``"""
        if self.length >= self.size:
            self.truncated = True
            return 0
        # Add delimiter if required
        if self.use_delimiter and self.need_sep and not self.field_open:
            if self.size - self.length > 1:
                self.parts.append(self.delimiter)
                self.length += 1
            else:
                self.truncated = True
                return 0
        if not self.field_open:
            self.need_sep = True
        available = self.size - self.length
        n = len(text)
        if n >= available:
            self.parts.append(text[: available - 1])
            self.length = self.size - 1
            self.truncated = True
            return available - 1
        self.parts.append(text)
        self.length += n
        return n

    def begin_field(self) -> None:
        if self.use_delimiter and self.need_sep:
            if self.size - self.length > 1:
                self.parts.append(self.delimiter)
                self.length += 1
            else:
                self.truncated = True
        self.need_sep = False
        self.field_open = True

    def end_field(self) -> None:
        self.field_open = False
        self.need_sep = True

    def emit_string(self, s: str | None, width: int) -> int:
        """``cw_buffer_emit_string``: quoted, or left-justified in ``width``"""
        text = "" if s is None else s
        if self.use_delimiter:
            return self.emit(f'"{text}"')
        return self.emit(f"{text:<{width}}")

    def emit_int(self, value: int, width: int) -> int:
        """``cw_buffer_emit_int``: right-justified in ``width`` unless delimited"""
        if self.use_delimiter or width == 0:
            return self.emit(str(value))
        return self.emit(f"{value:{width}d}")


Field = Callable[[CWBuffer, GameIter, Boxscore, Roster | None, Roster | None], int]

_T = TypeVar("_T")


def _deref(value: _T | None) -> _T:
    if value is None:
        raise ValueError("NULL dereference in Chadwick")
    return value


def _s(value: str | None) -> str:
    return "(null)" if value is None else value


def _cdiv(a: int, b: int) -> int:
    """C integer division (truncates toward zero)"""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def _cmod(a: int, b: int) -> int:
    return a - b * _cdiv(a, b)


def _info(gi: GameIter, key: str) -> str | None:
    return gi.game.info_lookup(key)


def _print_integer_or_null(buf: CWBuffer, value: int) -> int:
    """``cwgame_print_integer_or_null``: a negative number is a null, shown as nothing"""
    return buf.emit(str(value) if value >= 0 else "")


def _info_text(key: str, width: int) -> Field:
    """``cwgame_print_string_or_null`` of ``cw_game_info_lookup(game, key)``"""

    def f(buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None) -> int:
        return buf.emit_string(_info(gi, key), width)

    return f


def _game_find_name(game: Game, player_id: str | None) -> str | None:
    """``cwgame_game_find_name``: a player's name from an appearance record"""
    for app in game.starters:
        if app.player_id == _deref(player_id):
            return app.name
    for event in game.events:
        for app in event.subs:
            if app.player_id == _deref(player_id):
                return app.name
    return None


def _find_player_name(
    game: Game, buf: CWBuffer, player_id: str, visitors: Roster | None, home: Roster | None
) -> int:
    """``cwgame_find_player_name``"""
    bio = visitors.player_find(player_id) if visitors is not None else None
    if bio is None and home is not None:
        bio = home.player_find(player_id)
    if bio is not None:
        return buf.emit(f'"{bio.first_name} {bio.last_name}"')
    return buf.emit(f'"{_s(_game_find_name(game, player_id))}"')


def _day_of_week_index(month: int, day: int, year: int) -> int:
    """``get_day_of_week`` (Tomohiko Sakamoto); 0 is Sunday"""
    t = [0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4]
    if not 1 <= month <= 12:
        raise ValueError(f"month {month} out of range (undefined behaviour in C)")
    year -= month < 3
    total = year + _cdiv(year, 4) - _cdiv(year, 100) + _cdiv(year, 400) + t[month - 1] + day
    return _cmod(total, 7)


def _lookup(text: str | None, table: tuple[tuple[int, str], ...]) -> int:
    """``cwgame_lookup``"""
    if text is None:
        return 0
    for code, name in table:
        if name == text:
            return code
    return 0


def _lookup_field(key: str, table: tuple[tuple[int, str], ...]) -> Field:
    def f(buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None) -> int:
        return buf.emit_int(_lookup(_info(gi, key), table), 1)

    return f


# Fields 0-45, 84, 85 ------------------------------------------------------------------------


def _game_id(buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None) -> int:
    return buf.emit_string(gi.game.game_id, 12)


# The characters of the date that each format prints, in print order
_DATE_FORMATS = {
    CWGAME_DATE_SLASH_FULL: (5, 6, 8, 9, 0, 1, 2, 3),
    CWGAME_DATE_SLASH_PARTIAL: (5, 6, 8, 9, 2, 3),
    CWGAME_DATE_NOSLASH_PARTIAL: (2, 3, 5, 6, 8, 9),
    CWGAME_DATE_NOSLASH_FULL: (0, 1, 2, 3, 5, 6, 8, 9),
}


def _date(
    buf: CWBuffer,
    gi: GameIter,
    box: Boxscore,
    v: Roster | None,
    h: Roster | None,
    date_format: int = CWGAME_DATE_NOSLASH_FULL,
) -> int:
    """``cwgame_date``; the C reads the global ``date_format``, here a parameter"""
    date = _deref(_info(gi, "date"))
    indices = _DATE_FORMATS.get(date_format, _DATE_FORMATS[CWGAME_DATE_NOSLASH_FULL])
    c = date_digits(date, indices)
    if date_format == CWGAME_DATE_SLASH_FULL:
        text = f"{c[0:2]}/{c[2:4]}/{c[4:8]}"
    elif date_format == CWGAME_DATE_SLASH_PARTIAL:
        text = f"{c[0:2]}/{c[2:4]}/{c[4:6]}"
    else:
        text = c
    return buf.emit(f'"{text}"' if buf.use_delimiter else text)


def _number(buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None) -> int:
    tmp = _info(gi, "number")
    return buf.emit_int(cw_atoi(tmp) if tmp is not None else 0, 5)


DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


def _day_of_week(
    buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None
) -> int:
    date = _info(gi, "date")
    if date is None:
        buf.emit_string("", 9)
        return 0
    year = scan_int(date, 0)
    month = day = None
    if year is not None and date[year[1] : year[1] + 1] == "/":
        month = scan_int(date, year[1] + 1)
        if month is not None and date[month[1] : month[1] + 1] == "/":
            day = scan_int(date, month[1] + 1)
    if year is None or month is None or day is None:
        raise ValueError(f"unparsable date {date!r} (uninitialised values in Chadwick)")
    y = year[0]
    if 0 < y <= 99:
        y += 1900  # assume that two-digit years are in the 20th century
    gi.leftovers["year"] = y  # the C local `year`; see _start_time
    return buf.emit_string(DAY_NAMES[_day_of_week_index(month[0], day[0], y)], 9)


def _start_time(
    buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None
) -> int:
    text = _info(gi, "starttime")
    if text is None:
        return buf.emit("0" if buf.use_delimiter else "   0")
    hour = scan_int(text, 0)
    minute = None
    if hour is not None and text[hour[1] : hour[1] + 1] == ":":
        minute = scan_int(text, hour[1] + 1)
    if hour is None:
        raise ValueError(f"unparsable start time {text!r} (uninitialised values in Chadwick)")
    if minute is None:
        # sscanf("%d:%d") stopped before filling `min`, so the C prints whatever was in that stack
        # slot. Retrosheet's Negro Leagues files hold times such as "0.375" (a spreadsheet
        # fraction). In the reference build `min` shares its slot with the `year` local of the
        # cwgame_day_of_week field that runs just before this one, so it prints year (checked
        # against the C tool on those files: "0.375" gives 0*100 + 1947 in 1947). Without that
        # field running first the slot holds something we cannot know.
        year = gi.leftovers.get("year")
        if year is None:
            raise ValueError(
                f"unparsable start time {text!r} (uninitialised value in Chadwick; "
                "the day-of-week field did not run first)"
            )
        return buf.emit_int(hour[0] * 100 + year, 4)
    return buf.emit_int(hour[0] * 100 + minute[0], 4)


def _use_dh(buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None) -> int:
    tmp = _info(gi, "usedh")
    c = "T" if tmp is not None and tmp == "true" else "F"
    return buf.emit(f'"{c}"' if buf.use_delimiter else c)


def _day_night(
    buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None
) -> int:
    tmp = _info(gi, "daynight")
    c = "N" if tmp is not None and tmp == "night" else "D"
    return buf.emit(f'"{c}"' if buf.use_delimiter else c)


def _starter_pitcher(team: int) -> Field:
    def f(buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None) -> int:
        app = gi.game.starter_by_position(team, 1)
        return buf.emit_string(app.player_id if app is not None else "", 8)

    return f


def _attendance(
    buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None
) -> int:
    tmp = _info(gi, "attendance")
    value = (
        cw_atoi(tmp, "Warning: invalid value '%s' for info,attendance\n")
        if tmp is not None and tmp != ""
        else 0
    )
    return buf.emit(str(value) if buf.use_delimiter else f"{value:5d}")


def _temperature(
    buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None
) -> int:
    value = _info(gi, "temp")
    if value is None or value == "" or value == "unknown":
        return buf.emit_int(0, 3)
    return buf.emit_int(cw_atoi(value, "Warning: invalid value '%s' for info,temp\n"), 3)


def _wind_speed(
    buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None
) -> int:
    value = _info(gi, "windspeed")
    if value is None or value == "" or value == "unknown":
        return buf.emit_int(0, 2)
    return buf.emit_int(cw_atoi(value, "Warning: invalid value '%s' for info,windspeed\n"), 2)


def _time_of_game(
    buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None
) -> int:
    tmp = _info(gi, "timeofgame")
    value = (
        cw_atoi(tmp, "Warning: invalid value '%s' for info,timeofgame\n")
        if tmp is not None and tmp != ""
        else 0
    )
    return buf.emit(str(value) if buf.use_delimiter else f"{value:5d}")


def _innings(buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None) -> int:
    if gi.game.events:
        return buf.emit_int(gi.state.inning, 2)
    i = 1
    while i < 50:
        if box.linescore[i][0] < 0 and box.linescore[i][1] < 0:
            break
        i += 1
    return buf.emit_int(i - 1, 2)


def _box_pair(attr: str, team: int) -> Field:
    """``box->score[t]``, ``box->hits[t]``, ``box->errors[t]``"""

    def f(buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None) -> int:
        return buf.emit_int(getattr(box, attr)[team], 2)

    return f


def _lob(team: int) -> Field:
    def f(buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None) -> int:
        if gi.game.events:
            return buf.emit_int(gi.state.left_on_base(team), 2)
        return buf.emit_int(box.lob[team], 2)

    return f


def _game_type(
    buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None
) -> int:
    tmp = _info(gi, "gametype")
    return buf.emit_string(tmp if tmp is not None and tmp != "" else "regular", 12)


def starting_player(buf: CWBuffer, game: Game, team: int, slot: int) -> int:
    """``cwgame_starting_player``"""
    starter = game.starter_find(team, slot)
    if starter is not None:
        return buf.emit_string(starter.player_id, 8)
    return buf.emit_string("(null)", 8)


def starting_position(buf: CWBuffer, game: Game, team: int, slot: int) -> int:
    """``cwgame_starting_position``"""
    starter = game.starter_find(team, slot)
    return buf.emit_int(starter.pos if starter is not None else 0, 1)


def final_pitcher(buf: CWBuffer, box: Boxscore, team: int) -> int:
    """``cwgame_final_pitcher``: the last pitcher used, unless the starter went the distance"""
    pitcher = box.pitchers[team]
    player_id = pitcher.player_id if pitcher is not None and pitcher.prev is not None else ""
    return buf.emit_string(player_id, 8)


# Extended fields ----------------------------------------------------------------------------


def _league(team: int) -> Field:
    def f(buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None) -> int:
        roster = v if team == 0 else h
        return buf.emit_string(roster.league if roster is not None else "", 2)

    return f


def _empty_string(width: int) -> Field:
    """``cw_buffer_emit_string(buffer, "", width)``"""

    def f(buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None) -> int:
        return buf.emit_string("", width)

    return f


def _protest_info(
    buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None
) -> int:
    return buf.emit("")


def _length_outs(
    buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None
) -> int:
    outs = 0
    for t in range(2):
        pitcher = get_starting_pitcher(box, t)
        while pitcher is not None:
            outs += pitcher.pitching.outs
            pitcher = pitcher.next
    return buf.emit_int(outs, 3)


def generate_linescore(buf: CWBuffer, box: Boxscore, team: int) -> int:
    """``cwgame_generate_linescore``"""
    count = 0
    buf.begin_field()
    i = 1
    while i < 50:
        if box.linescore[i][team] < 0 and box.linescore[i][1] < 0:
            break
        if box.linescore[i][team] >= 10:
            count += buf.emit(f"({box.linescore[i][team]})")
        elif box.linescore[i][0] >= 0:
            count += buf.emit(str(box.linescore[i][team]))
        else:
            count += buf.emit("x")
        i += 1
    buf.end_field()
    return count


def _line(team: int) -> Field:
    """``cwgame_visitors_line`` and ``cwgame_home_line``"""

    def f(buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None) -> int:
        return generate_linescore(buf, box, team)

    return f


def _tabulated_batter(team: int, attr: str) -> Field:
    """``DECLARE_TABULATED_BATTER_FUNC``: a negative (null) stat stops that slot's walk and sets
    the total to -1, but the next slot goes on adding to it"""

    def f(buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None) -> int:
        tot = 0
        for slot in range(1, 10):
            player: BoxPlayer | None = get_starter(box, team, slot)
            while player is not None:
                value = getattr(player.batting, attr)
                if value < 0:
                    tot = -1
                    break
                tot += value
                player = player.next
        return _print_integer_or_null(buf, tot)

    return f


def _tabulated_pitcher(team: int, attr: str) -> Field:
    """``DECLARE_TABULATED_PITCHER_FUNC``"""

    def f(buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None) -> int:
        tot = 0
        pitcher: BoxPitcher | None = get_starting_pitcher(box, team)
        while pitcher is not None:
            tot += getattr(pitcher.pitching, attr)
            pitcher = pitcher.next
        return _print_integer_or_null(buf, tot)

    return f


def _tabulated_fielder(team: int, attr: str, frompos: int, topos: int) -> Field:
    """``DECLARE_TABULATED_FIELDER_FUNC``"""

    def f(buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None) -> int:
        tot = 0
        for slot in range(10):
            player = get_starter(box, team, slot)
            while player is not None:
                for pos in range(frompos, topos + 1):
                    fielding = player.fielding[pos]
                    if fielding is not None:
                        value = getattr(fielding, attr)
                        if value < 0:
                            return buf.emit("-1")
                        tot += value
                player = player.next
        return _print_integer_or_null(buf, tot)

    return f


def _pitcher_count(team: int) -> Field:
    def f(buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None) -> int:
        pitcher = get_starting_pitcher(box, team)
        i = 0
        while pitcher is not None:
            pitcher = pitcher.next
            i += 1
        return buf.emit_int(i, 2)

    return f


def _box_count(attr: str, team: int) -> Field:
    """``box->er[t]``, ``box->dp[t]``, ``box->tp[t]``"""

    def f(buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None) -> int:
        return buf.emit_int(getattr(box, attr)[team], 2)

    return f


def _named(key: str, quoted_none: bool = True) -> Field:
    """``cwgame_winning_pitcher_name`` and its losing/save twins. The C save version prints its
    "(none)" with ``cw_buffer_emit``, so it is neither quoted nor padded."""

    def f(buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None) -> int:
        tmp = _info(gi, key)
        if tmp is not None and tmp != "":
            return _find_player_name(gi.game, buf, tmp, v, h)
        if quoted_none:
            return buf.emit_string("(none)", 30)
        return buf.emit("(none)")

    return f


def _goahead_rbi_id(
    buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None
) -> int:
    return buf.emit_string(gi.state.go_ahead_rbi or "", 8)


def _goahead_rbi_name(
    buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None
) -> int:
    tmp = gi.state.go_ahead_rbi
    if tmp is not None and tmp != "":
        return _find_player_name(gi.game, buf, tmp, v, h)
    return buf.emit_string("(none)", 30)


def _lineup_name(team: int, slot: int) -> Field:
    """``cwgame_find_lineup_name``"""

    def f(buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None) -> int:
        starter = gi.game.starter_find(team, slot)
        if starter is not None:
            return _find_player_name(gi.game, buf, starter.player_id, v, h)
        return buf.emit_string("(null)", 30)

    return f


def _additional_info(
    buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None
) -> int:
    htbf = _info(gi, "htbf")
    return buf.emit_string("HTBF" if htbf is not None and htbf == "true" else "", 30)


def _scheduled_innings(
    buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None
) -> int:
    tmp = _info(gi, "innings")
    return buf.emit(tmp if tmp is not None else "9")


def _tiebreaker(
    buf: CWBuffer, gi: GameIter, box: Boxscore, v: Roster | None, h: Roster | None
) -> int:
    return buf.emit(f'"{_info(gi, "tiebreaker") or ""}"')


_HOWSCORED = ((0, "unknown"), (1, "park"), (2, "tv"), (3, "radio"))
_PITCHES = ((0, "unknown"), (1, "pitches"), (2, "count"), (0, "none"))
_WINDDIR = (
    (0, "unknown"), (1, "tolf"), (2, "tocf"), (3, "torf"), (4, "ltor"),
    (5, "fromlf"), (6, "fromcf"), (7, "fromrf"), (8, "rtol"),
)  # fmt: skip
_FIELDCOND = ((0, "unknown"), (1, "soaked"), (2, "wet"), (3, "damp"), (4, "dry"))
_PRECIP = ((0, "unknown"), (1, "none"), (2, "drizzle"), (3, "showers"), (4, "rain"), (5, "snow"))
_SKY = ((0, "unknown"), (1, "sunny"), (2, "cloudy"), (3, "overcast"), (4, "night"), (5, "dome"))


FIELDS: tuple[tuple[Field | None, str, str], ...] = (
    (_game_id, "GAME_ID", "game id"),
    (_date, "GAME_DT", "date"),
    (_number, "GAME_CT", "game number (0 = no double header)"),
    (_day_of_week, "GAME_DY", "day of week"),
    (_start_time, "START_GAME_TM", "start time"),
    (_use_dh, "DH_FL", "DH used flag"),
    (_day_night, "DAYNIGHT_PARK_CD", "day/night flag"),
    (_info_text("visteam", 3), "AWAY_TEAM_ID", "visiting team"),
    (_info_text("hometeam", 3), "HOME_TEAM_ID", "home team"),
    (_info_text("site", 5), "PARK_ID", "game site"),
    (_starter_pitcher(0), "AWAY_START_PIT_ID", "vis. starting pitcher"),
    (_starter_pitcher(1), "HOME_START_PIT_ID", "home starting pitcher"),
    (_info_text("umphome", 30), "BASE4_UMP_ID", "home plate umpire"),
    (_info_text("ump1b", 30), "BASE1_UMP_ID", "first base umpire"),
    (_info_text("ump2b", 30), "BASE2_UMP_ID", "second base umpire"),
    (_info_text("ump3b", 30), "BASE3_UMP_ID", "third base umpire"),
    (_info_text("umplf", 30), "LF_UMP_ID", "left field umpire"),
    (_info_text("umprf", 30), "RF_UMP_ID", "right field umpire"),
    (_attendance, "ATTEND_PARK_CT", "attendance"),
    (_info_text("scorer", 30), "SCORER_RECORD_ID", "PS scorer"),
    (_info_text("translator", 30), "TRANSLATOR_RECORD_ID", "translator"),
    (_info_text("inputter", 30), "INPUTTER_RECORD_ID", "inputter"),
    (_info_text("inputtime", 30), "INPUT_RECORD_TS", "input time"),
    (_info_text("edittime", 30), "EDIT_RECORD_TS", "edit time"),
    (_lookup_field("howscored", _HOWSCORED), "METHOD_RECORD_CD", "how scored"),
    (_lookup_field("pitches", _PITCHES), "PITCHES_RECORD_CD", "pitches entered?"),
    (_temperature, "TEMP_PARK_CT", "temperature"),
    (_lookup_field("winddir", _WINDDIR), "WIND_DIRECTION_PARK_CD", "wind direction"),
    (_wind_speed, "WIND_SPEED_PARK_CT", "wind speed"),
    (_lookup_field("fieldcond", _FIELDCOND), "FIELD_PARK_CD", "field condition"),
    (_lookup_field("precip", _PRECIP), "PRECIP_PARK_CD", "precipitation"),
    (_lookup_field("sky", _SKY), "SKY_PARK_CD", "sky"),
    (_time_of_game, "MINUTES_GAME_CT", "time of game"),
    (_innings, "INN_CT", "number of innings"),
    (_box_pair("score", 0), "AWAY_SCORE_CT", "visitor final score"),
    (_box_pair("score", 1), "HOME_SCORE_CT", "home final score"),
    (_box_pair("hits", 0), "AWAY_HITS_CT", "visitor hits"),
    (_box_pair("hits", 1), "HOME_HITS_CT", "home hits"),
    (_box_pair("errors", 0), "AWAY_ERR_CT", "visitor errors"),
    (_box_pair("errors", 1), "HOME_ERR_CT", "home errors"),
    (_lob(0), "AWAY_LOB_CT", "visitor left on base"),
    (_lob(1), "HOME_LOB_CT", "home left on base"),
    (_info_text("wp", 8), "WIN_PIT_ID", "winning pitcher"),
    (_info_text("lp", 8), "LOSE_PIT_ID", "losing pitcher"),
    (_info_text("save", 8), "SAVE_PIT_ID", "save for"),
    (_info_text("gwrbi", 8), "GWRBI_BAT_ID", "GW RBI"),
    (None, "AWAY_LINEUP1_BAT_ID", "visitor batter 1"),
    (None, "AWAY_LINEUP1_FLD_CD", "visitor position 1"),
    (None, "AWAY_LINEUP2_BAT_ID", "visitor batter 2"),
    (None, "AWAY_LINEUP2_FLD_CD", "visitor position 2"),
    (None, "AWAY_LINEUP3_BAT_ID", "visitor batter 3"),
    (None, "AWAY_LINEUP3_FLD_CD", "visitor position 3"),
    (None, "AWAY_LINEUP4_BAT_ID", "visitor batter 4"),
    (None, "AWAY_LINEUP4_FLD_CD", "visitor position 4"),
    (None, "AWAY_LINEUP5_BAT_ID", "visitor batter 5"),
    (None, "AWAY_LINEUP5_FLD_CD", "visitor position 5"),
    (None, "AWAY_LINEUP6_BAT_ID", "visitor batter 6"),
    (None, "AWAY_LINEUP6_FLD_CD", "visitor position 6"),
    (None, "AWAY_LINEUP7_BAT_ID", "visitor batter 7"),
    (None, "AWAY_LINEUP7_FLD_CD", "visitor position 7"),
    (None, "AWAY_LINEUP8_BAT_ID", "visitor batter 8"),
    (None, "AWAY_LINEUP8_FLD_CD", "visitor position 8"),
    (None, "AWAY_LINEUP9_BAT_ID", "visitor batter 9"),
    (None, "AWAY_LINEUP9_FLD_CD", "visitor position 9"),
    (None, "HOME_LINEUP1_BAT_ID", "home batter 1"),
    (None, "HOME_LINEUP1_FLD_CD", "home position 1"),
    (None, "HOME_LINEUP2_BAT_ID", "home batter 2"),
    (None, "HOME_LINEUP2_FLD_CD", "home position 2"),
    (None, "HOME_LINEUP3_BAT_ID", "home batter 3"),
    (None, "HOME_LINEUP3_FLD_CD", "home position 3"),
    (None, "HOME_LINEUP4_BAT_ID", "home batter 4"),
    (None, "HOME_LINEUP4_FLD_CD", "home position 4"),
    (None, "HOME_LINEUP5_BAT_ID", "home batter 5"),
    (None, "HOME_LINEUP5_FLD_CD", "home position 5"),
    (None, "HOME_LINEUP6_BAT_ID", "home batter 6"),
    (None, "HOME_LINEUP6_FLD_CD", "home position 6"),
    (None, "HOME_LINEUP7_BAT_ID", "home batter 7"),
    (None, "HOME_LINEUP7_FLD_CD", "home position 7"),
    (None, "HOME_LINEUP8_BAT_ID", "home batter 8"),
    (None, "HOME_LINEUP8_FLD_CD", "home position 8"),
    (None, "HOME_LINEUP9_BAT_ID", "home batter 9"),
    (None, "HOME_LINEUP9_FLD_CD", "home position 9"),
    (None, "AWAY_FINISH_PIT_ID", "visiting finisher (NULL if complete game)"),
    (None, "HOME_FINISH_PIT_ID", "home finisher (NULL if complete game)"),
    (_info_text("oscorer", 8), "OFFICIAL_SCORER_ID", "official scorer"),
    (_game_type, "GAME_TYPE_TX", "game type"),
)

EXT_FIELDS: tuple[tuple[Field | None, str, str], ...] = (
    (_league(0), "AWAY_TEAM_LEAGUE_ID", "visiting team league"),
    (_league(1), "HOME_TEAM_LEAGUE_ID", "home team league"),
    (_empty_string(3), "AWAY_TEAM_GAME_CT", "visiting team game number"),
    (_empty_string(3), "HOME_TEAM_GAME_CT", "home team game number"),
    (_length_outs, "OUTS_CT", "length of game in outs"),
    (_empty_string(30), "COMPLETION_TX", "information on completion of game"),
    (_empty_string(30), "FORFEIT_TX", "information on forfeit of game"),
    (_protest_info, "PROTEST_TX", "information on protest of game"),
    (_line(0), "AWAY_LINE_TX", "visiting team linescore"),
    (_line(1), "HOME_LINE_TX", "home team linescore"),
    (_tabulated_batter(0, "ab"), "AWAY_AB_CT", "visiting team AB"),
    (_tabulated_batter(0, "b2"), "AWAY_2B_CT", "visiting team 2B"),
    (_tabulated_batter(0, "b3"), "AWAY_3B_CT", "visiting team 3B"),
    (_tabulated_batter(0, "hr"), "AWAY_HR_CT", "visiting team HR"),
    (_tabulated_batter(0, "bi"), "AWAY_BI_CT", "visiting team RBI"),
    (_tabulated_batter(0, "sh"), "AWAY_SH_CT", "visiting team SH"),
    (_tabulated_batter(0, "sf"), "AWAY_SF_CT", "visiting team SF"),
    (_tabulated_batter(0, "hp"), "AWAY_HP_CT", "visiting team HP"),
    (_tabulated_batter(0, "bb"), "AWAY_BB_CT", "visiting team BB"),
    (_tabulated_batter(0, "ibb"), "AWAY_IBB_CT", "visiting team IBB"),
    (_tabulated_batter(0, "so"), "AWAY_SO_CT", "visiting team SO"),
    (_tabulated_batter(0, "sb"), "AWAY_SB_CT", "visiting team SB"),
    (_tabulated_batter(0, "cs"), "AWAY_CS_CT", "visiting team CS"),
    (_tabulated_batter(0, "gdp"), "AWAY_GDP_CT", "visiting team GDP"),
    (_tabulated_batter(0, "xi"), "AWAY_XI_CT", "visiting team reach on interference"),
    (_pitcher_count(0), "AWAY_PITCHER_CT", "number of pitchers used by visiting team"),
    (_tabulated_pitcher(0, "er"), "AWAY_ER_CT", "visiting team individual ER allowed"),
    (_box_count("er", 0), "AWAY_TER_CT", "visiting team team ER allowed"),
    (_tabulated_pitcher(0, "wp"), "AWAY_WP_CT", "visiting team WP"),
    (_tabulated_pitcher(0, "bk"), "AWAY_BK_CT", "visiting team BK"),
    (_tabulated_fielder(0, "po", 1, 9), "AWAY_PO_CT", "visiting team PO"),
    (_tabulated_fielder(0, "a", 1, 9), "AWAY_A_CT", "visiting team A"),
    (_tabulated_fielder(0, "pb", 2, 2), "AWAY_PB_CT", "visiting team PB"),
    (_box_count("dp", 0), "AWAY_DP_CT", "visiting team DP"),
    (_box_count("tp", 0), "AWAY_TP_CT", "visiting team TP"),
    (_tabulated_batter(1, "ab"), "HOME_AB_CT", "home team AB"),
    (_tabulated_batter(1, "b2"), "HOME_2B_CT", "home team 2B"),
    (_tabulated_batter(1, "b3"), "HOME_3B_CT", "home team 3B"),
    (_tabulated_batter(1, "hr"), "HOME_HR_CT", "home team HR"),
    (_tabulated_batter(1, "bi"), "HOME_BI_CT", "home team RBI"),
    (_tabulated_batter(1, "sh"), "HOME_SH_CT", "home team SH"),
    (_tabulated_batter(1, "sf"), "HOME_SF_CT", "home team SF"),
    (_tabulated_batter(1, "hp"), "HOME_HP_CT", "home team HP"),
    (_tabulated_batter(1, "bb"), "HOME_BB_CT", "home team BB"),
    (_tabulated_batter(1, "ibb"), "HOME_IBB_CT", "home team IBB"),
    (_tabulated_batter(1, "so"), "HOME_SO_CT", "home team SO"),
    (_tabulated_batter(1, "sb"), "HOME_SB_CT", "home team SB"),
    (_tabulated_batter(1, "cs"), "HOME_CS_CT", "home team CS"),
    (_tabulated_batter(1, "gdp"), "HOME_GDP_CT", "home team GDP"),
    (_tabulated_batter(1, "xi"), "HOME_XI_CT", "home team reach on interference"),
    (_pitcher_count(1), "HOME_PITCHER_CT", "number of pitchers used by home team"),
    (_tabulated_pitcher(1, "er"), "HOME_ER_CT", "home team individual ER allowed"),
    (_box_count("er", 1), "HOME_TER_CT", "home team team ER allowed"),
    (_tabulated_pitcher(1, "wp"), "HOME_WP_CT", "home team WP"),
    (_tabulated_pitcher(1, "bk"), "HOME_BK_CT", "home team BK"),
    (_tabulated_fielder(1, "po", 1, 9), "HOME_PO_CT", "home team PO"),
    (_tabulated_fielder(1, "a", 1, 9), "HOME_A_CT", "home team A"),
    (_tabulated_fielder(1, "pb", 2, 2), "HOME_PB_CT", "home team PB"),
    (_box_count("dp", 1), "HOME_DP_CT", "home team DP"),
    (_box_count("tp", 1), "HOME_TP_CT", "home team TP"),
    (_empty_string(30), "UMP_HOME_NAME_TX", "home plate umpire name"),
    (_empty_string(30), "UMP_1B_NAME_TX", "first base umpire name"),
    (_empty_string(30), "UMP_2B_NAME_TX", "second base umpire name"),
    (_empty_string(30), "UMP_3B_NAME_TX", "third base umpire name"),
    (_empty_string(30), "UMP_LF_NAME_TX", "left field umpire name"),
    (_empty_string(30), "UMP_RF_NAME_TX", "right field umpire name"),
    (_empty_string(8), "AWAY_MANAGER_ID", "visitors manager ID"),
    (_empty_string(30), "AWAY_MANAGER_NAME_TX", "visitors manager name"),
    (_empty_string(8), "HOME_MANAGER_ID", "home manager ID"),
    (_empty_string(30), "HOME_MANAGER_NAME_TX", "home manager name"),
    (_named("wp"), "WIN_PIT_NAME_TX", "winning pitcher name"),
    (_named("lp"), "LOSE_PIT_NAME_TX", "losing pitcher name"),
    (_named("save", quoted_none=False), "SAVE_PIT_NAME_TX", "save pitcher name"),
    (_goahead_rbi_id, "GOAHEAD_RBI_ID", "batter with goahead RBI ID"),
    (_goahead_rbi_name, "GOAHEAD_RBI_NAME_TX", "batter with goahead RBI"),
    (_lineup_name(0, 1), "AWAY_LINEUP1_BAT_NAME_TX", "visitor batter 1 name"),
    (_lineup_name(0, 2), "AWAY_LINEUP2_BAT_NAME_TX", "visitor batter 2 name"),
    (_lineup_name(0, 3), "AWAY_LINEUP3_BAT_NAME_TX", "visitor batter 3 name"),
    (_lineup_name(0, 4), "AWAY_LINEUP4_BAT_NAME_TX", "visitor batter 4 name"),
    (_lineup_name(0, 5), "AWAY_LINEUP5_BAT_NAME_TX", "visitor batter 5 name"),
    (_lineup_name(0, 6), "AWAY_LINEUP6_BAT_NAME_TX", "visitor batter 6 name"),
    (_lineup_name(0, 7), "AWAY_LINEUP7_BAT_NAME_TX", "visitor batter 7 name"),
    (_lineup_name(0, 8), "AWAY_LINEUP8_BAT_NAME_TX", "visitor batter 8 name"),
    (_lineup_name(0, 9), "AWAY_LINEUP9_BAT_NAME_TX", "visitor batter 9 name"),
    (_lineup_name(1, 1), "HOME_LINEUP1_BAT_NAME_TX", "home batter 1 name"),
    (_lineup_name(1, 2), "HOME_LINEUP2_BAT_NAME_TX", "home batter 2 name"),
    (_lineup_name(1, 3), "HOME_LINEUP3_BAT_NAME_TX", "home batter 3 name"),
    (_lineup_name(1, 4), "HOME_LINEUP4_BAT_NAME_TX", "home batter 4 name"),
    (_lineup_name(1, 5), "HOME_LINEUP5_BAT_NAME_TX", "home batter 5 name"),
    (_lineup_name(1, 6), "HOME_LINEUP6_BAT_NAME_TX", "home batter 6 name"),
    (_lineup_name(1, 7), "HOME_LINEUP7_BAT_NAME_TX", "home batter 7 name"),
    (_lineup_name(1, 8), "HOME_LINEUP8_BAT_NAME_TX", "home batter 8 name"),
    (_lineup_name(1, 9), "HOME_LINEUP9_BAT_NAME_TX", "home batter 9 name"),
    (_additional_info, "ADD_INFO_TX", "additional information"),
    (_empty_string(30), "ACQ_INFO_TX", "acquisition information"),
    (_scheduled_innings, "SCHED_INN_CT", "scheduled length of game in innings "),
    (_tiebreaker, "TIEBREAK_CD", "tiebreaker rule type in use"),
)

MAX_FIELD = len(FIELDS) - 1
MAX_EXT_FIELD = len(EXT_FIELDS) - 1


def game_line(
    game: Game,
    visitors: Roster | None,
    home: Roster | None,
    ascii_: bool,
    fields: Collection[int],
    ext_fields: Collection[int],
    date_format: int = CWGAME_DATE_NOSLASH_FULL,
) -> str:
    """``cwgame_process_game``: the line describing one game"""
    box = box_create(game)
    gi = GameIter(game)
    while gi.event is not None:
        gi.next()

    buf = CWBuffer(BUFFER_SIZE, ascii_)
    for i in range(46):
        if i in fields:
            if i == 1:
                _date(buf, gi, box, visitors, home, date_format)
            else:
                _deref(FIELDS[i][0])(buf, gi, box, visitors, home)
    for t in range(2):
        for i in range(1, 10):
            for j in range(2):
                if 46 + t * 18 + 2 * (i - 1) + j in fields:
                    if j == 0:
                        starting_player(buf, game, t, i)
                    else:
                        starting_position(buf, game, t, i)
    for t, i in enumerate((82, 83)):
        if i in fields:
            final_pitcher(buf, box, t)
    for i in range(84, MAX_FIELD + 1):
        if i in fields:
            _deref(FIELDS[i][0])(buf, gi, box, visitors, home)
    for i in range(MAX_EXT_FIELD + 1):
        if i in ext_fields:
            _deref(EXT_FIELDS[i][0])(buf, gi, box, visitors, home)
    if buf.truncated:
        raise BufferTruncated(f"Error: output buffer truncated for game {game.game_id}")
    return cut_at_nul(buf.text())


def header_line(fields: Collection[int], ext_fields: Collection[int]) -> str:
    """``cwgame_initialize`` with ``-n``: the field names, quoted and comma separated"""
    buf = CWBuffer(BUFFER_SIZE, True)
    for i in range(MAX_FIELD + 1):
        if i in fields:
            buf.emit(f'"{FIELDS[i][1]}"')
    for i in range(MAX_EXT_FIELD + 1):
        if i in ext_fields:
            buf.emit(f'"{EXT_FIELDS[i][1]}"')
    if buf.truncated:
        raise BufferTruncated("Error: output buffer truncated while generating header")
    return buf.text()


DEFAULT_FIELDS = tuple(range(85))


def game_lines(
    data: bytes,
    league: League | None = None,
    game_id: str = "",
    first_date: str = "0101",
    last_date: str = "1231",
    ascii_: bool = True,
    fields: Collection[int] = DEFAULT_FIELDS,
    ext_fields: Collection[int] = (),
    date_format: int = CWGAME_DATE_NOSLASH_FULL,
) -> Iterator[str]:
    """Lines for the selected games of an event file, as ``cwgame`` prints them."""
    for game, visitors, home in iterate_games(data, league, game_id, first_date, last_date):
        yield game_line(game, visitors, home, ascii_, fields, ext_fields, date_format)
