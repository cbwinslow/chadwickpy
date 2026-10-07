"""Corners of ``tools/cwboxxml.py`` against the real ``cwbox -X``.

* ``info,gwrbi``: the batter named there gets ``gwrbi="1"`` on his ``<batting>`` element.
* ``pb``: a ``<fielding>`` element for the catcher carries ``pb`` only when ``positions[pos] == 2``
  for ``pos`` = 2, i.e. when the player's *third* listed position is catcher. The C reads
  ``positions[]`` entries it never filled in other cases (uninitialised memory), so the ``pb``
  attributes are removed from both sides before comparing, as in ``test_cwbox_differential``;
  a separate check shows the port does print ``pb`` in this case.

The ``_player`` guard in ``cwboxxml.py`` (an event with more than 20 players) cannot be reached:
the port always allocates the 20 slots of the C ``CWBoxEvent`` and only indexes 0 and 1.
Runs only where the real ``cwbox`` is installed.
"""

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from chadwick_tool import real_tool, run_tool  # noqa: E402
from test_box_targeted_differential import THREE_UP, game, sub  # noqa: E402
from test_cwbox_differential import normalise, port_output  # noqa: E402

pytestmark = pytest.mark.skipif(real_tool("cwbox") is None, reason="needs cwbox on PATH")

CASES = {
    "gwrbi_visitor_batter": game(info={"gwrbi": "v3"}),
    "gwrbi_home_batter": game(info={"gwrbi": "h2"}),
    "gwrbi_nobody": game(info={"gwrbi": "nosuchplayer"}),
    # the home catcher moves to first base and back: positions are [2, 3, 2]
    "catcher_third_position_is_catcher": game(
        plays=[THREE_UP[0], sub("h5", 1, 5, 3), sub("h5", 1, 5, 2), *THREE_UP[1:]]
    ),
    # [2, 3, 4]: the third position is not catcher
    "catcher_third_position_second_base": game(
        plays=[THREE_UP[0], sub("h5", 1, 5, 3), sub("h5", 1, 5, 4), *THREE_UP[1:]]
    ),
}


@pytest.mark.parametrize("name", CASES)
def test_cwbox_xml_matches_chadwick(tmp_path, name):
    data = CASES[name].encode("latin-1")
    path = tmp_path / "x.evt"
    path.write_bytes(data)
    run = run_tool("cwbox", path, ["-X"])
    assert run is not None
    assert run[0] == 0
    assert normalise("xml", run[1]) == normalise("xml", port_output(data, None, True))


def test_gwrbi_attribute_is_written_for_the_named_batter() -> None:
    out = port_output(CASES["gwrbi_visitor_batter"].encode("latin-1"), None, True).decode("latin-1")
    marked = [ln for ln in out.splitlines() if 'gwrbi="1"' in ln]
    assert len(marked) == 1


def test_pb_is_written_when_the_third_position_is_catcher() -> None:
    out = port_output(
        CASES["catcher_third_position_is_catcher"].encode("latin-1"), None, True
    ).decode("latin-1")
    assert ' pb="' in out
