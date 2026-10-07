"""Plays aimed at parser branches that real seasons and the random grammar never reach.

Found by running the suite and a multi-era CLI sample under branch coverage
(``openspec/changes/verify-port-completeness``, task 2.3). Each play is run through Chadwick's
``cw_parse_event`` and the port and the two dumps must agree. The harness is the one built by
``test_parse_grammar_differential``.
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

# interference: error / assist modifiers, repeated errors, batted-ball type
INTERFERENCE = [
    f"C/{m}"
    for m in ("E1", "E2", "E3", "E4", "E6", "4E1", "INT", "G", "E1/E2", "E1/4E1", "E5", "XX")
]
# plays whose trailing modifiers go through the "other advance" / passed ball / wild pitch loops
TRAILING = [
    f"{p}/{m}"
    for p in ("OA", "DI", "PB", "WP", "SB2", "CS2", "BK", "NP")
    for m in (
        "DP",
        "TP",
        "INT",
        "BINT",
        "AP",
        "MREV",
        "UREV",
        "NDP",
        "OBS",
        "R1",
        "R",
        "BOOT",
        "COUR",
        "UINT",
        "XX",
    )
]
# putouts with modifiers and nested parentheses in the advance
ADVANCE = [
    "54(1)/FO",
    "5(1)/INT",
    "64(1)/OBS",
    "6(1)3/AP",
    "8(1)/G",
    "3(1)(2)",
    "1X2(E5/TH)",
    "1X2(E5/THH)",
    "1X2(E5/TH/G)",
    "1X2(5E4)(E5)",
    "8.2XH(9S)",
    "8.2XH(9S)(E2)",
    "K23+WP.B-1",
    "K+WP.BX1(2E3)",
    "K.BX1(2E3)",
    "K.BX1(23)",
    "K.1X2(E4)",
    "S8.2-H(E)",
    "S8.1-2(E)",
    "S8.1-2(",
    "S8.1-2(E5",
    "S8.1-2(E5)(",
    "S8.1-2(E5/TH",
    "S8.1-2(NR)(",
    "FC5.1-2(E0)",
    "FC5.1-2(EX)",
    "FC5.1-2(E)",
    "64(1/DP",
    "64(1X",
    "46(1)3/GDP",
    "46(1)3/DP",
    "8(B)/F",
    "9/F",
    "9/L",
    "E",
    "E5",
    "55E",
    "5E5",
    "5E",
    "54E3",
    "5(E)",
    "6E",
    "E5/TH",
    "E5/G",
]
# fielding credit followed by a modifier inside an advance, and the archaic SBH(UR) forms
IN_PAREN = [
    f"{play}({credit}/{m})"
    for play in ("S8.1-2", "S8.2XH", "S8.1X2", "S7.2-3")
    for credit in ("5", "64", "5E4", "E5", "8")
    for m in ("INT", "BINT", "OBS", "G", "U", "AP", "BR", "FO", "TH", "XX")
] + [
    f"{b}{x}"
    for b in ("SBH", "SB4", "SB2", "SB3", "SB1")
    for x in ("(UR)", "(TUR)", "(UR", "(U", "(X", "(T", "(TX", "(URX", "()")
]
# a parenthesised modifier directly after a putout's own modifier
NESTED = [
    f"S8.1X2({credit}{mod}({inner}))"
    for credit in ("5", "64", "E5", "5E4")
    for mod in ("", "/TH", "/G", "/INT", "/FO", "/XX")
    for inner in ("E4", "UR", "NR", "TH", "5", "E", "XX", "(", "")
]
# pickoffs and caught stealing, including a base character the C code indexes out of range with
PICKOFF = [
    f"{p}{b}({c})"
    for p in ("PO", "POCS")
    for b in ("1", "2", "3", "H")
    for c in ("14", "1E3", "13/TH", "E3", "3E4")
] + ["PO1", "POCS2", "POCSH", "POCSH(2346)", "POCS3(1361)"]
# default batted-ball types
BATTED = [
    "8",
    "9",
    "54",
    "63",
    "3",
    "63/DP",
    "6/BG",
    "5/BP",
    "1/SH",
    "54/SH",
    "8/SF",
    "2/G",
    "8/G",
    "8/F",
]

PLAYS = INTERFERENCE + TRAILING + ADVANCE + IN_PAREN + NESTED + PICKOFF + BATTED


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


def test_targeted_plays_parse_like_chadwick(harness: Path) -> None:
    compared, diffs, skipped = compare(PLAYS, str(harness))
    assert not diffs, "\n".join(diffs[:3])
    assert compared > len(PLAYS) * 0.8, (compared, skipped)
