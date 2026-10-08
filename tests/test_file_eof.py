"""``CFile.getline`` follows the 0.11.0 record reader and C's ``feof`` rules at the last line."""

import random
from pathlib import Path

from chadwickpy.file import CFile
from chadwickpy.tools.cli import IO, TOOLS, main


class _ReferenceReader:
    """``cw_getline`` of Chadwick 0.11.0, one ``fgetc`` at a time"""

    def __init__(self, data: bytes) -> None:
        self._data, self.pos, self.eof = data, 0, False

    def getline(self) -> str | None:
        out = bytearray()
        while True:
            if self.pos >= len(self._data):
                self.eof = True
                break
            c = self._data[self.pos]
            self.pos += 1
            if c == 0x0A:
                return out.decode("latin-1")
            if c != 0x0D:
                out.append(c)
        return out.decode("latin-1") if out else None


def test_eof_is_not_set_by_a_final_line_that_ends_in_a_newline() -> None:
    f = CFile(b"a\nb\n")
    assert f.getline() == "a" and not f.eof
    assert f.getline() == "b" and not f.eof  # C: feof is still false here
    assert f.getline() is None and f.eof


def test_a_final_line_without_a_newline_is_read_and_sets_eof() -> None:
    f = CFile(b"a\nb")
    assert f.getline() == "a" and not f.eof
    assert f.getline() == "b" and f.eof
    assert f.getline() is None


def test_every_carriage_return_is_dropped_and_long_lines_are_whole() -> None:
    f = CFile(b"a\rb\r\n" + b"x" * 5000 + b"\r")
    assert f.getline() == "ab"
    assert f.getline() == "x" * 5000


def test_matches_the_reference_on_random_input() -> None:
    rng = random.Random(1998)
    for _ in range(3000):
        data = bytes(rng.choice(b"ab,\r\n") for _ in range(rng.randrange(0, 40)))
        new, ref = CFile(data), _ReferenceReader(data)
        for _ in range(len(data) + 3):
            assert new.getline() == ref.getline(), data
            assert new.eof == ref.eof, data


def test_a_comment_on_the_last_line_is_not_lost(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Real case (1998 Toronto): a file ending in ``com`` lines. Chadwick joins them into one."""
    here = Path(__file__).parent
    for f in (here / "reference" / "rosters" / "regular_2007").iterdir():
        (tmp_path / f.name).write_bytes(f.read_bytes())
    body = (here / "fixtures" / "events" / "regular_2007.evt").read_bytes().rstrip(b"\r\n")
    path = tmp_path / "2007A.EVA"
    path.write_bytes(body + b'\r\ncom,"first"\r\ncom,"second"\r\ncom,"last"\r\n')
    monkeypatch.chdir(tmp_path)
    out: list[str] = []
    main(
        TOOLS["cwcomment"], ["cwcomment", "-Q", "-y", "2007", str(path)], IO(out.append, [].append)
    )
    assert "first second last" in "".join(out)
