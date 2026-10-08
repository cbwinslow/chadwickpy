"""``cwgame``, ``cwdaily``, ``cwsub`` and ``cwcomment`` option combinations against the real tools
(OpenSpec change verify-port-completeness, task 3.1; ``test_event_option_sweep`` does the same
for ``cwevent``).

Game selection (``-i``, ``-s``, ``-e``, with dates equal to, just before and just after a game's
date) crossed with output format (``-a``, ``-n``, ``-ft``, together), field lists and one or two
event files. Malformed option values are covered by ``test_cli_differential`` and
``test_cli_targeted_differential``. Standard output, standard error and exit status must match.
"""

import itertools
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
from test_event_option_sweep import FILES, FORMATS, SELECTIONS  # noqa: E402

# tool -> field-list option sets (default, a short list, every field)
FIELDS = {
    "cwgame": {"std": [], "low": ["-f", "0-5"], "all": ["-f", "0-84", "-x", "0-96"]},
    "cwdaily": {"std": [], "low": ["-f", "0-5"], "all": ["-f", "0-153"]},
    "cwsub": {"std": [], "low": ["-f", "0-5"], "all": ["-f", "0-24"]},
    "cwcomment": {"std": [], "low": ["-f", "0-3"], "all": ["-f", "0-9"]},
}

CASES = [
    (tool, sel, fmt, fld, files)
    for tool in FIELDS
    for sel, fmt, fld, files in itertools.product(SELECTIONS, FORMATS, FIELDS[tool], FILES)
]


@pytest.mark.parametrize(("tool", "sel", "fmt", "fld", "files"), CASES)
def test_option_combination(tmp_path: Path, tool: str, sel: str, fmt: str, fld: str, files: str):
    args = ["-Q", "-y", "2007", *SELECTIONS[sel], *FORMATS[fmt], *FIELDS[tool][fld], *FILES[files]]
    real = run_real(tool, args, scratch(tmp_path, "real"))
    port = run_port(tool, args, scratch(tmp_path, "port"))
    assert real[0] == port[0], (tool, args)
    assert real[2] == port[2], ("stderr", tool, args)
    assert real[1] == port[1], ("stdout", tool, args)
    # guard against a sweep that compares empty outputs everywhere
    if sel in ("all", "id_hit", "window_around", "id_and_window") and "-ft" not in args:
        assert real[1], (tool, args)
