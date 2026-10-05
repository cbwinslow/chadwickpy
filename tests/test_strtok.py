"""``StrTok`` must split lines exactly like the original character-by-character version."""

import random

from chadwickpy.file import StrTok


class _ReferenceStrTok:
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
            while at < n and s[at] not in '"\n\r':
                at += 1
            token = s[start:at]
            if at >= n:
                self._next = None
            else:
                self._next = at + 1
                # a comma immediately following a quote is skipped past
                if self._next < n and s[self._next] == ",":
                    self._next += 1
            return token

        start = at
        while at < n and s[at] not in ",\n\r":
            at += 1
        token = s[start:at]
        self._next = None if at >= n else at + 1
        return token


def _tokens(tok: object, line: str) -> list[str | None]:
    out: list[str | None] = []
    t = tok(line)  # type: ignore[operator]
    while t is not None:
        out.append(t)
        t = tok(None)  # type: ignore[operator]
    return out


def test_matches_the_reference_on_random_lines() -> None:
    rng = random.Random(2008)
    alphabet = 'ab ,"\r\n\t'
    for _ in range(20000):
        line = "".join(rng.choice(alphabet) for _ in range(rng.randrange(0, 14)))
        assert _tokens(StrTok(), line) == _tokens(_ReferenceStrTok(), line), repr(line)
