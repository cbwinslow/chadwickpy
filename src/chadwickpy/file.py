"""Port of the reading helpers in Chadwick's ``src/cwlib/file.c``.

Chadwick is Copyright (c) 2002-2023 Dr T L Turocy and the Chadwick Baseball
Bureau, licensed GPL-2.0-or-later; this module is a derivative of it and keeps
that notice.

Chadwick reads event files with ``fgets(buf, 1024, file)`` and splits each line
with ``cw_strtok``. Both are reproduced here byte for byte, including the
quirks that decide what a file means: a line longer than 1023 bytes is read in
pieces, a last line with no trailing newline is dropped, and text is handled as
C strings, so a NUL byte ends a line. Text is held as ``latin-1`` so that one
byte is one character, as in C.
"""

import logging
import re

log = logging.getLogger("chadwickpy")

BUFSIZE = 1024  # ``char buf[1024]`` in ``cw_game_read``


class ReportedError(ValueError):
    """The C prints this message itself (on stderr) and calls ``exit(1)``.

    The port logs the message and raises this, so the command line ends with status 1 without
    printing the message a second time."""


class CFile:
    """The part of a C ``FILE *`` that ``cw_game_read`` uses on an event file."""

    def __init__(self, data: bytes) -> None:
        self._data = data
        self.pos = 0
        self.eof = False

    def fgets(self, size: int) -> str | None:
        """``fgets(buf, size, file)``: up to ``size - 1`` bytes, stopping after a newline.

        Returns ``None`` when no byte could be read. The end-of-file flag is set
        when the read ran into the end of the file, even if bytes were returned.
        """
        data, pos = self._data, self.pos
        if pos >= len(data):
            self.eof = True
            return None
        want = size - 1
        limit = min(pos + want, len(data))
        nl = data.find(b"\n", pos, limit)
        if nl != -1:
            end = nl + 1
        else:
            end = limit
        # Like C's feof(): set only when the read itself ran into the end. A line that ends with
        # its newline exactly at the end of the data has not, so the next read still reports EOF.
        if nl == -1 and len(data) - pos < want:
            self.eof = True
        self.pos = end
        return data[pos:end].decode("latin-1")

    def getpos(self) -> int:
        """``fgetpos``"""
        return self.pos

    def setpos(self, pos: int) -> None:
        """``fsetpos``: also clears the end-of-file flag"""
        self.pos = pos
        self.eof = False


class StrTok:
    """``cw_strtok``: split on commas, honouring a quote at the start and end of a field.

    The C function keeps its position in a static variable; the position is
    kept here on the instance. A new line is started by passing it in, and
    ``None`` continues the line.
    """

    def __init__(self) -> None:
        self._s = ""
        self._next: int | None = None

    def __call__(self, line: str | None) -> str | None:
        if line is not None:
            nul = line.find("\0")
            self._s = line if nul < 0 else line[:nul]  # a C string ends at its first NUL
            at = 0
        elif self._next is not None:
            at = self._next
        else:
            return None
        s = self._s
        n = len(s)

        if at >= n:
            self._next = None
            return None

        while at < n and s[at] in " \t\n":
            at += 1
        if at >= n:
            self._next = None
            return None

        if s[at] == '"':
            at += 1
            start = at
            q = s.find('"', at)
            nl = s.find("\n", at)
            cr = s.find("\r", at)
            end = n
            for cand in (q, nl, cr):
                if cand != -1 and cand < end:
                    end = cand
            token = s[start:end]
            # The original loop stopped at a quote, newline or CR alike and resumed just after it.
            if end >= n:
                self._next = None
            else:
                self._next = end + 1
                if self._next < n and s[self._next] == ",":
                    self._next += 1
            return token

        start = at
        comma = s.find(",", at)
        if comma != -1:
            nl = s.find("\n", at, comma)
            cr = s.find("\r", at, comma)
            end = comma
            if nl != -1:
                end = nl
            if cr != -1 and cr < end:
                end = cr
            token = s[start:end]
            self._next = None if end >= n else end + 1
            return token
        else:
            nl = s.find("\n", at)
            cr = s.find("\r", at)
            end = n
            if nl != -1:
                end = nl
            if cr != -1 and cr < end:
                end = cr
            token = s[start:end]
            self._next = None if end >= n else end + 1
            return token


_INT_MIN, _INT_MAX = -(2**31), 2**31 - 1
_LONG_MIN, _LONG_MAX = -(2**63), 2**63 - 1


def cw_atoi(text: str, msg: str | None = None) -> int:
    """``cw_atoi``: ``strtol`` with validity checking; -1 (Retrosheet's null) when invalid.

    Like ``strtol``, it skips leading white space, accepts a sign, and stops at
    the first non-digit, so trailing text is ignored. Only a string with no
    digits at all, or a value outside ``int``, is invalid.
    """
    # Fast path for plain ASCII numbers. isdigit() alone is not enough: it is also true for
    # characters like "\u00b2" that int() rejects and that C's strtol does not treat as digits.
    if text.isascii() and text.isdigit():
        if len(text) < 10:
            return int(text)
        val = int(text)
        if val <= _INT_MAX:
            return val
    elif text.startswith("-") and text.isascii() and text[1:].isdigit():
        if len(text) < 11:
            return -int(text[1:])
        val = -int(text[1:])
        if val >= _INT_MIN:
            return val

    i, n = 0, len(text)
    while i < n and text[i] in " \t\n\v\f\r":
        i += 1
    sign = 1
    if i < n and text[i] in "+-":
        sign = -1 if text[i] == "-" else 1
        i += 1
    start = i
    while i < n and "0" <= text[i] <= "9":
        i += 1
    if i > start:
        value = sign * int(text[start:i])
        if _INT_MIN <= value <= _INT_MAX and _LONG_MIN <= value <= _LONG_MAX:
            return value
    log.warning(msg % text if msg is not None else f"WARNING: Invalid integer value '{text}'")
    return -1


_SCAN_INT = re.compile(r"[ \t\n\v\f\r]*([+-]?[0-9]+)")


def scan_int(text: str, pos: int = 0) -> tuple[int, int] | None:
    """One ``%d`` conversion of ``sscanf`` at ``pos``: (value, position after it), or ``None``
    when no integer is there (``sscanf`` then stops and leaves its outputs unset)"""
    found = _SCAN_INT.match(text, pos)
    return None if found is None else (int(found.group(1)), found.end())
