"""``CFile.fgets`` must follow C's ``fgets``/``feof`` rules exactly, including at the last line."""

import random
from pathlib import Path

from chadwickpy.file import CFile
from chadwickpy.tools.cli import IO, TOOLS, main


class _ReferenceFile:
    """The byte-at-a-time loop the optimised ``fgets`` replaced: slow but plainly C's rule."""

    def __init__(self, data: bytes) -> None:
        self._data, self.pos, self.eof = data, 0, False

    def fgets(self, size: int) -> str | None:
        data, pos = self._data, self.pos
        if pos >= len(data):
            self.eof = True
            return None
        want, end = size - 1, pos
        while end - pos < want:
            if end >= len(data):
                self.eof = True
                break
            end += 1
            if data[end - 1] == 0x0A:
                break
        self.pos = end
        return data[pos:end].decode("latin-1")


def test_eof_is_not_set_by_a_final_line_that_ends_in_a_newline() -> None:
    f = CFile(b"a\nb\n")
    assert f.fgets(100) == "a\n" and not f.eof
    assert f.fgets(100) == "b\n" and not f.eof  # C: feof is still false here
    assert f.fgets(100) is None and f.eof


def test_eof_is_set_by_a_final_line_without_a_newline() -> None:
    f = CFile(b"a\nb")
    assert f.fgets(100) == "a\n" and not f.eof
    assert f.fgets(100) == "b" and f.eof


def test_matches_the_reference_on_random_input() -> None:
    rng = random.Random(1998)
    for _ in range(3000):
        data = bytes(rng.choice(b"ab,\r\n") for _ in range(rng.randrange(0, 40)))
        size = rng.randrange(1, 12)
        new, ref = CFile(data), _ReferenceFile(data)
        for _ in range(len(data) + 3):
            assert new.fgets(size) == ref.fgets(size), (data, size)
            assert new.eof == ref.eof, (data, size)


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
        TOOLS["cwcomment"], ["cwcomment", "-q", "-y", "2007", str(path)], IO(out.append, [].append)
    )
    assert "first second last" in "".join(out)
