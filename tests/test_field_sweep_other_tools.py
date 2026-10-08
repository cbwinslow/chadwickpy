"""``cwgame``, ``cwdaily``, ``cwsub`` and ``cwcomment`` field by field against the real tools
(OpenSpec change verify-port-completeness, task 3.1; ``cwevent`` has its own sweep in
``test_event_field_sweep``).

Every standard field (and for ``cwgame`` every extended field) is requested alone, in ASCII
(with the header row) and fixed-width output, plus random subsets, on all fixture event files
(every era and rule variant). Standard output, standard error and exit status must match.
"""

import random
import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from test_cli_differential import (  # noqa: E402
    pytestmark,  # noqa: F401  (skip without the real tools)
    run_port,
    run_real,
)
from test_event_differential import FIXTURES  # noqa: E402

from chadwickpy.tools.cli import TOOLS  # noqa: E402

# tool -> (number of standard fields, number of extended fields); from each tool's ``-d`` list
FIELD_COUNTS = {
    "cwgame": (85, 97),
    "cwdaily": (154, 0),
    "cwsub": (25, 0),
    "cwcomment": (10, 0),
}
FORMATS = {"ascii": ["-n"], "fixed": ["-ft"]}


@pytest.fixture(scope="module")
def season_dirs() -> list[tuple[str, str, Path]]:
    """One scratch directory per fixture: the event file plus the (empty) team file."""
    base = Path(tempfile.mkdtemp(prefix="chadwickpy_fields_"))
    dirs = []
    for fixture in FIXTURES:
        data = fixture.read_bytes()
        found = data.split(b"id,", 1)[1][3:7].decode()
        work = base / fixture.stem
        work.mkdir()
        name = f"{found}XXX.EVN"
        (work / name).write_bytes(data)
        (work / f"TEAM{found}").write_text("")
        dirs.append((found, name, work))
    return dirs


def compare(tool: str, fmt: str, flags: list[str], dirs: list[tuple[str, str, Path]]) -> None:
    assert tool in TOOLS
    for year, name, work in dirs:
        args = ["-Q", "-y", year, *FORMATS[fmt], *flags, name]
        real = run_real(tool, args, work)
        port = run_port(tool, args, work)
        assert real[0] == port[0], (tool, name, flags)
        assert real[2] == port[2], ("stderr", tool, name, flags)
        assert real[1] == port[1], ("stdout", tool, name, flags)


STANDARD = [(t, i) for t, (n, _) in FIELD_COUNTS.items() for i in range(n)]
EXTENDED = [(t, i) for t, (_, n) in FIELD_COUNTS.items() for i in range(n)]


@pytest.mark.parametrize("fmt", FORMATS)
@pytest.mark.parametrize(("tool", "field"), STANDARD)
def test_standard_field_alone(season_dirs, tool: str, field: int, fmt: str) -> None:
    compare(tool, fmt, ["-f", str(field)], season_dirs)


@pytest.mark.parametrize("fmt", FORMATS)
@pytest.mark.parametrize(("tool", "field"), EXTENDED)
def test_extended_field_alone(season_dirs, tool: str, field: int, fmt: str) -> None:
    compare(tool, fmt, ["-f", "0", "-x", str(field)], season_dirs)


@pytest.mark.parametrize("fmt", FORMATS)
@pytest.mark.parametrize("seed", range(10))
@pytest.mark.parametrize("tool", FIELD_COUNTS)
def test_random_field_subsets(season_dirs, tool: str, seed: int, fmt: str) -> None:
    rng = random.Random(seed * 31 + len(tool))
    std, ext = FIELD_COUNTS[tool]
    fields = sorted(rng.sample(range(std), rng.randint(1, min(30, std))))
    flags = ["-f", ",".join(map(str, fields))]
    if ext:
        flags += ["-x", ",".join(map(str, sorted(rng.sample(range(ext), rng.randint(1, 25)))))]
    compare(tool, fmt, flags, season_dirs)
