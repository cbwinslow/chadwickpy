"""``cwbox`` option combinations against the real ``cwbox`` (OpenSpec change
verify-port-completeness, task 3.1).

Game selection (``-i``, ``-s``, ``-e``, with dates equal to, just before and just after a game's
date) crossed with text and XML output (``-X``), ``-q`` and one or two event files. SportsML
(``-S``) is deprecated (ADR-002) and the real program crashes on it, so it is not run. The XML
``pb`` attribute depends on uninitialised memory in the C program and is removed from both sides
(as in ``tests/reference/cli_all_years.py``). Standard output, standard error and exit status must
match.
"""

import itertools
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from test_cli_differential import (  # noqa: E402
    pytestmark,  # noqa: F401  (skip without the real tools)
    run_port,
    run_real,
    scratch,
)
from test_event_option_sweep import FILES, SELECTIONS  # noqa: E402

PB = re.compile(rb' pb="\d+"')
OUTPUT = {"text": [], "xml": ["-X"]}
QUIET = {"quiet": ["-q"], "chatty": []}

CASES = list(itertools.product(SELECTIONS, OUTPUT, QUIET, FILES))


@pytest.mark.parametrize(("sel", "out", "quiet", "files"), CASES)
def test_cwbox_option_combination(tmp_path: Path, sel: str, out: str, quiet: str, files: str):
    args = [*QUIET[quiet], "-y", "2007", *SELECTIONS[sel], *OUTPUT[out], *FILES[files]]
    real = run_real("cwbox", args, scratch(tmp_path, "real"))
    port = run_port("cwbox", args, scratch(tmp_path, "port"))
    real_out, port_out = PB.sub(b"", real[1]), PB.sub(b"", port[1])
    assert real[0] == port[0], args
    assert real[2] == port[2], ("stderr", args)
    assert real_out == port_out, ("stdout", args)
    if sel in ("all", "id_hit", "window_around", "id_and_window"):
        assert real_out, args  # the sweep must compare real box scores, not empty output
