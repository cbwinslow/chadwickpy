"""``cwgame`` date formats (-dsf, -dsp, -dnf, -dnp, Chadwick 0.11.0) against the real tool."""

import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from chadwick_tool import real_tool, run_tool  # noqa: E402
from test_game_targeted_differential import game  # noqa: E402

from chadwickpy.tools.cwgame import (  # noqa: E402
    CWGAME_DATE_NOSLASH_FULL,
    CWGAME_DATE_NOSLASH_PARTIAL,
    CWGAME_DATE_SLASH_FULL,
    CWGAME_DATE_SLASH_PARTIAL,
    game_lines,
)

pytestmark = pytest.mark.skipif(real_tool("cwgame") is None, reason="needs cwgame on PATH")

SWITCHES = {
    "-dsf": CWGAME_DATE_SLASH_FULL,
    "-dsp": CWGAME_DATE_SLASH_PARTIAL,
    "-dnf": CWGAME_DATE_NOSLASH_FULL,
    "-dnp": CWGAME_DATE_NOSLASH_PARTIAL,
}


@pytest.mark.parametrize("ft", [False, True], ids=["ascii", "fixed"])
@pytest.mark.parametrize("switch", sorted(SWITCHES))
def test_date_format_matches_cwgame(switch: str, ft: bool) -> None:
    data = game().encode("latin-1")
    args = ["-n", "-f", "0-5", switch] + (["-ft"] if ft else [])
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "case.evt"
        path.write_bytes(data)
        real = run_tool("cwgame", path, args)
    assert real is not None
    lines = game_lines(data, ascii_=not ft, fields=range(6), date_format=SWITCHES[switch])
    port = "".join(line + "\n" for line in lines).encode("latin-1")
    expected = {"-dsf": b"07/02/2020", "-dsp": b"07/02/20", "-dnf": b"20200702", "-dnp": b"200702"}
    assert expected[switch] in port
    # the real tool's data line is the port's line (the header is not compared here)
    assert real[1].split(b"\n")[-2] + b"\n" == port
