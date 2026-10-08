"""``cwevent`` option combinations against the real ``cwevent`` (OpenSpec change
verify-port-completeness, task 2.1).

Game selection (``-i``, ``-s``, ``-e``, with dates equal to, just before and just after a game's
date) crossed with output format (``-a``, ``-n``, ``-ft``, together), field lists (``-f``, ``-x``)
and one or two event files. Malformed option values are covered by ``test_cli_differential`` and
``test_cli_targeted_differential``; this file runs the valid combinations. Standard output,
standard error and exit status must all match.
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

# regular_2007.evt holds TOR200705310 (May 31); negro_league.evt is another year and is a
# second file in the same run
SELECTIONS = {
    "all": [],
    "id_hit": ["-i", "TOR200705310"],
    "id_miss": ["-i", "TOR200705311"],
    "start_on_day": ["-s", "0531"],
    "start_after_day": ["-s", "0601"],
    "end_on_day": ["-e", "0531"],
    "end_before_day": ["-e", "0530"],
    "window_on_day": ["-s", "0531", "-e", "0531"],
    "window_around": ["-s", "0501", "-e", "0630"],
    "window_misses": ["-s", "0601", "-e", "0630"],
    "id_and_window": ["-i", "TOR200705310", "-s", "0501", "-e", "0630"],
    "id_outside_window": ["-i", "TOR200705310", "-s", "0601", "-e", "0630"],
}
FORMATS = {
    "default": [],
    "a": ["-a"],
    "n": ["-n"],
    "ft": ["-ft"],
    "ft_n": ["-ft", "-n"],
    "a_n": ["-a", "-n"],
}
FIELDS = {
    "std": [],
    "f_low": ["-f", "0-10"],
    "f_one_x_one": ["-f", "5", "-x", "5"],
    "x_only": ["-x", "0-20"],
    "all": ["-f", "0-96", "-x", "0-66"],
}
FILES = {"one": ["a.evt"], "two": ["a.evt", "b.evt"]}

CASES = [
    (sel, fmt, fld, files)
    for sel, fmt, fld, files in itertools.product(SELECTIONS, FORMATS, FIELDS, FILES)
]


@pytest.mark.parametrize(("sel", "fmt", "fld", "files"), CASES)
def test_cwevent_option_combination(tmp_path: Path, sel: str, fmt: str, fld: str, files: str):
    args = [
        "-Q",
        "-y",
        "2007",
        *SELECTIONS[sel],
        *FORMATS[fmt],
        *FIELDS[fld],
        *FILES[files],
    ]
    real = run_real("cwevent", args, scratch(tmp_path, "real"))
    port = run_port("cwevent", args, scratch(tmp_path, "port"))
    assert real[0] == port[0], args
    assert real[2] == port[2], ("stderr", args)
    assert real[1] == port[1], ("stdout", args)
    # a combination must produce rows exactly when it should: guard against a sweep that
    # compares two empty outputs everywhere
    if sel in ("all", "id_hit", "window_around", "id_and_window") and "-ft" not in args:
        assert real[1], args


@pytest.mark.parametrize(
    "extra", [[], ["-Q"], ["-n"], ["-f", "0-3"], ["-x", "0-3"], ["-y", "2007"]]
)
def test_field_list_option_prints_the_field_table(tmp_path: Path, extra: list[str]) -> None:
    args = ["-d", *extra]
    real = run_real("cwevent", args, scratch(tmp_path, "real"))
    port = run_port("cwevent", args, scratch(tmp_path, "port"))
    assert real == port
    assert b"0" in real[1] or b"0" in real[2]
