"""Port of the reading helpers in Chadwick's ``src/cwlib/file.c``.

Chadwick is Copyright (c) 2002-2026 Dr T L Turocy and the Chadwick Baseball
Bureau, licensed GPL-2.0-or-later; this module is a derivative of it and keeps
that notice.

Chadwick 0.11.0 reads event, roster and team files with a record reader
(``CWRecordReader``) and splits each line with a tokenizer (``CWTokenizer``). Both
are reproduced here, including the quirks that decide what a file means: a line may
be any length, every ``\r`` is dropped wherever it stands (so CRLF and CR-only
breaks inside a line vanish), a last line with no trailing newline is read like any
other, and text is handled as C strings, so a NUL byte ends a line. Text is held as
``latin-1`` so that one byte is one character, as in C.
"""

import logging
import re

log = logging.getLogger("chadwickpy")

BUFSIZE = 1024  # ``char batHandBatter[1024]`` and its siblings in ``cw_game_read``


class ReportedError(ValueError):
    """The C prints this message itself (on stderr) and calls ``exit(1)``.

    The port logs the message and raises this, so the command line ends with status 1 without
    printing the message a second time."""


class CFile:
    """The part of a C ``FILE *`` that the record reader uses on a file."""

    def __init__(self, data: bytes) -> None:
        self._data = data
        self.pos = 0
        self.eof = False

    def getline(self) -> str | None:
        """``cw_record_reader_next``: the next line without its ``\n`` and without any ``\r``.

        Returns ``None`` at the end of the file: ``cw_getline`` reports -1 when the end was
        reached with nothing kept, which includes a final stretch of nothing but ``\r``. The
        end-of-file flag is set when the read ran into the end of the data, as ``feof`` is.
        """
        data, pos = self._data, self.pos
        nl = data.find(b"\n", pos)
        if nl != -1:
            self.pos = nl + 1
            return data[pos:nl].replace(b"\r", b"").decode("latin-1")
        self.pos = len(data)
        self.eof = True
        line = data[pos:].replace(b"\r", b"")
        return line.decode("latin-1") if line else None

    def getpos(self) -> int:
        """``fgetpos``"""
        return self.pos

    def setpos(self, pos: int) -> None:
        """``fsetpos``: also clears the end-of-file flag"""
        self.pos = pos
        self.eof = False


class Tokenizer:
    """``CWTokenizer``: split a line on commas, honouring a quote at the start of a field.

    ``tok(line)`` is ``cw_tokenizer_init`` followed by the first ``cw_tokenizer_next``;
    ``tok(None)`` is a further ``cw_tokenizer_next``. The C tokenizer writes a NUL over each
    comma or closing quote that ends a field, so the line it was given afterwards reads as
    the text up to the first such NUL; :meth:`line_text` gives that text, which the
    "invalid record" warning prints.
    """

    def __init__(self) -> None:
        self._s = ""
        self._at = 0
        self._nul: int | None = None

    def __call__(self, line: str | None) -> str | None:
        if line is not None:
            nul = line.find("\0")
            self._s = line if nul < 0 else line[:nul]  # a C string ends at its first NUL
            self._at = 0
            self._nul = None
        return self.next()

    def line_text(self) -> str:
        """The line as the C sees it after tokenizing: up to the first NUL written so far"""
        return self._s if self._nul is None else self._s[: self._nul]

    def next(self) -> str | None:
        """``cw_tokenizer_next``"""
        s, at = self._s, self._at
        n = len(s)
        if at >= n:
            return None
        while at < n and s[at] in " \t":
            at += 1
        if at >= n:
            self._at = at
            return None

        if s[at] == '"':
            at += 1
            start = at
            quote = s.find('"', at)
            if quote == -1:
                token, at = s[start:], n
            else:
                token = s[start:quote]
                if self._nul is None:
                    self._nul = quote
                at = quote + 1
            if at < n and s[at] == ",":
                at += 1
            self._at = at
            return token

        start = at
        comma = s.find(",", at)
        if comma == -1:
            self._at = n
            return s[start:]
        if self._nul is None:
            self._nul = comma
        self._at = comma + 1
        return s[start:comma]


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
