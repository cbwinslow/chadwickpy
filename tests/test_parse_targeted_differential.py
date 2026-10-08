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
# Chadwick 0.11.0: C/ takes its fielding credit as the first flag only (2abbe0c)
CATCHER_INTERFERENCE = [
    "C/E2",
    "C/E1",
    "C/E3/G",
    "C/4E1",
    "C/46E1",
    "C/E2/L8",
    "C/F8/E2",
    "C/INT",
    "C",
    "C/G/E2",
    "C/E0",
    "C/E2.1-2",
]
# '#', '!' and '?' are stripped before parsing (b7f8b62, d55c9df); '?' is no fielder
STRIPPED = [
    "8!",
    "6#3/G",
    "S8?",
    "?3",
    "64?3",
    "E?4",
    "E4?",
    "FC?",
    "FC5?/G",
    "K+SB2#.1-2",
    "8/F#",
    "S/8#.2-H!",
]
# SB inside an advance modifier (8b706d0)
SB_IN_ADVANCE = [
    "BK.1-2(SB2)",
    "BK.2-3(SB3);1-2(SB2)",
    "BK.3-H(SBH)",
    "BK.3-H(SB4)",
    "BK.1-2(SB)",
    "BK.B-1(SB2)",
    "BK.1-2(SB5)",
]
# pickoffs and stolen bases after a CS or SB (be452bc)
CS_THEN_PICKOFF = [
    "CS2(24);PO1(13)",
    "CS2(24);POCS3(1361)",
    "CS2(24);POSB2",
    "SB2;PO1(13)",
    "SB2;POCS3(1361)",
    "SB3;POSB2",
    "CS3(25);POCSH(2346)",
]
# /TH and /THn on OA (c3e1e75)
OA_THROW = [f"OA/{m}" for m in ("TH", "TH1", "TH2", "TH3", "THH", "TH4", "THX")]
# placeholder 99 credits are rolled back and not inferred from (6a783ac)
NINETY_NINE = ["99", "99(1)", "99/G", "99(B)99(1)", "9(1)99", "64(1)99", "99/F8", "S99", "99/SH"]
# inferred versus explicit batted ball types (0a706f6)
INFERRED = [
    "E5/SF",
    "E4/SF",
    "8/SF",
    "5/IF",
    "5/IF/G",
    "5/G/IF",
    "FC5",
    "FC5/F",
    "E6",
    "E9/G",
    "54(1)/FO",
    "8/FO",
    "54(1)3/DP",
    "64(1)3/DP/G",
    "6(1)/FO/L",
    "S5/SF",
]
# explicit-credit strikeouts and out-based force flags (3f77b98, 14fae82)
STRIKEOUT_ADVANCE = [
    "K+WP.BX3(E2/TH)(2)",
    "K+WP.BX1(2E3)",
    "K+WP.B-1(2)",
    "K.BX1(23)",
    "K.BX1(2E3)(3)",
    "K+PB.B-1(E2)(2)",
    "K23",
    "K23+WP.B-1",
    "64(1)3/DP/RINT",
    "64(1)3/DP",
    "46(1)3/DP/FO",
    "6(1)4(2)/DP",
    "54(2)/FO/DP",
]
# /SAC is no longer a sacrifice-hit flag (0381790)
SAC = ["1/SAC", "54/SAC", "5/SH", "1/SH/SAC", "1/B/SAC"]


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


GROUPS = {
    "interference": INTERFERENCE,
    "trailing": TRAILING,
    "advance": ADVANCE,
    "in_paren": IN_PAREN,
    "nested": NESTED,
    "pickoff": PICKOFF,
    "batted": BATTED,
    "catcher_interference": CATCHER_INTERFERENCE,
    "stripped": STRIPPED,
    "sb_in_advance": SB_IN_ADVANCE,
    "cs_then_pickoff": CS_THEN_PICKOFF,
    "oa_throw": OA_THROW,
    "ninety_nine": NINETY_NINE,
    "inferred": INFERRED,
    "strikeout_advance": STRIKEOUT_ADVANCE,
    "sac": SAC,
}


@pytest.mark.parametrize("group", GROUPS)
def test_targeted_plays_parse_like_chadwick(harness: Path, group: str) -> None:
    """Each group is checked on its own, so a group the C harness skips as undefined behaviour
    cannot hide behind the others."""
    plays = GROUPS[group]
    compared, diffs, skipped = compare(plays, str(harness))
    assert not diffs, "\n".join(diffs[:3])
    assert compared >= len(plays) * 0.5, (group, compared, skipped)
