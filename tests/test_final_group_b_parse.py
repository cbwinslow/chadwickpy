"""Plays aimed at parser branches that ``test_parse_targeted_differential`` does not reach.

Each play goes through Chadwick's ``cw_parse_event`` (the sanitised harness of
``test_parse_grammar_differential``) and through the port; the dumps of every field must agree.
Task 2.3 of
``openspec/changes/verify-port-completeness``.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "reference"))
from chadwick_tool import SRC  # noqa: E402
from parse_fuzz import compare  # noqa: E402

pytestmark = pytest.mark.skipif(
    shutil.which("gcc") is None or not (SRC / "cwlib" / "parse.c").exists(),
    reason="needs gcc and the Chadwick sources (CHADWICK_SRC)",
)

GROUPS = {
    # a fielder's choice whose fielder is unknown ("?"): parse.py 664
    "fc_unknown_fielder": ["FC?", "FC?.1-2", "FC?.B-1", "FC?/F", "FC?/G", "FC?9", "FC??"],
    # ground-rule double with fielders listed after it (newer files): parse.py 889
    "dgr_fielders": ["DGR8", "DGR89", "DGR7/G", "DGR98", "DGR.1-3", "DGR9/F.2-H", "DGR1234"],
    # a walk with an error already recorded, then a throwing-error flag: parse.py 982
    "walk_throw_flag": [
        f"W+{a}/{f}" for a in ("E2", "PO1(E3)", "POCS2(1E3)") for f in ("TH", "TH1", "TH2", "THH")
    ],
    # an error credit after a "?" fielder, so the previous symbol is not a digit: parse.py 265
    "error_after_unknown": ["?E3", "54?E3", "5??E3", "?5E3", "5?E3", "?6E4", "9?E9"],
    # a putout by an unknown fielder from a base: no fielder token, batted-ball type unset
    "unknown_putout": ["?(B)", "?(B)/F", "??(B)", "?(B)/G", "?(B)/L"],
    # caught stealing credited to a base character; bases outside 1-4 are undefined behaviour in the
    # C (the harness skips them); they are compared in test_final_group_b_events instead
    "pocs_bases": [f"POCS{b}(2)" for b in "012345?H"] + ["POCS(2)", "POCS3(1361)"],
}


@pytest.fixture(scope="module")
def harness(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("parse_dump") / "parse_dump"
    cmd = [
        "gcc",
        "-w",
        "-g",
        "-fsanitize=address,undefined,bounds-strict",
        "-fno-sanitize-recover=all",
    ]
    cmd += ["-I", str(SRC / "cwlib"), "-I", str(SRC), str(HERE / "reference" / "parse_dump.c")]
    cmd += [*map(str, sorted((SRC / "cwlib").glob("*.c"))), "-o", str(out)]
    subprocess.run(cmd, check=True, capture_output=True)
    return out


@pytest.mark.parametrize("group", GROUPS)
def test_play_parses_like_chadwick(harness: Path, group: str) -> None:
    plays = GROUPS[group]
    compared, diffs, skipped = compare(plays, str(harness))
    assert not diffs, "\n".join(diffs[:3])
    # a play the C harness flags as undefined behaviour is skipped; most of each group must run
    assert compared >= len(plays) * 0.5, (group, compared, skipped)
