"""``Tokenizer`` must split lines exactly like a character-by-character port of
``cw_tokenizer_next`` (Chadwick 0.11.0, ``src/cwlib/file.c``)."""

import random

from chadwickpy.file import Tokenizer


class _ReferenceTokenizer:
    """``cw_tokenizer_init`` / ``cw_tokenizer_next`` on a mutable buffer, as C does it"""

    def __init__(self) -> None:
        self._buf: list[str] = []
        self._cur = 0

    def __call__(self, line: str | None) -> str | None:
        if line is not None:
            nul = line.find("\0")
            self._buf = list(line if nul < 0 else line[:nul]) + ["\0"]
            self._cur = 0
        return self.next()

    def next(self) -> str | None:
        b, s = self._buf, self._cur
        if b[s] == "\0":
            return None
        while b[s] in " \t":
            s += 1
        if b[s] == "\0":
            self._cur = s
            return None
        if b[s] == '"':
            s += 1
            start = s
            while b[s] != "\0" and b[s] != '"':
                s += 1
            end = s
            if b[s] == '"':
                b[s] = "\0"
                s += 1
            if b[s] == ",":
                s += 1
            self._cur = s
            return "".join(b[start:end])
        start = s
        while b[s] != "\0" and b[s] != ",":
            s += 1
        end = s
        if b[s] == ",":
            b[s] = "\0"
            s += 1
        self._cur = s
        return "".join(b[start:end])

    def line_text(self) -> str:
        return "".join(self._buf).split("\0")[0]


def _tokens(tok: object, line: str) -> list[str | None]:
    out: list[str | None] = []
    t = tok(line)  # type: ignore[operator]
    while t is not None:
        out.append(t)
        t = tok.next()  # type: ignore[attr-defined]
    return out


def test_matches_the_reference_on_random_lines() -> None:
    rng = random.Random(2008)
    alphabet = 'ab ,"\t\0'
    for _ in range(20000):
        line = "".join(rng.choice(alphabet) for _ in range(rng.randrange(0, 14)))
        mine, ref = Tokenizer(), _ReferenceTokenizer()
        assert _tokens(mine, line) == _tokens(ref, line), repr(line)
        assert mine.line_text() == ref.line_text(), repr(line)


def test_the_line_after_tokenizing_ends_at_the_first_terminator() -> None:
    tok = Tokenizer()
    assert tok("foo,bar,baz") == "foo"
    assert tok.line_text() == "foo"
    assert tok('"x",y') == "x"
    assert tok.line_text() == '"x'
