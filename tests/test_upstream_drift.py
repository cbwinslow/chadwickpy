"""Fail when the Chadwick C sources differ from the version the port was reviewed against.

``docs/about/c-function-hashes.txt`` holds a fingerprint of every C function (text with comments
and white space removed) at the pinned Chadwick commit, taken with
``python tests/reference/c_inventory.py --hashes CHECKOUT``. Point ``CHADWICK_SRC`` at a newer
Chadwick and this test names every function that was **added**, **removed** or **changed**, so a
new or modified C function cannot slip in unnoticed: each one must be reviewed against the port
(port it, or record why not), then the file regenerated. Name matching is deliberately not used:
it cannot tell a port from an unrelated word in a docstring (OpenSpec change
verify-port-completeness, task 4.5).
"""

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "reference"))
from c_inventory import function_hashes  # noqa: E402
from chadwick_tool import SRC  # noqa: E402

BASELINE = HERE.parent / "docs" / "about" / "c-function-hashes.txt"

pytestmark = pytest.mark.skipif(
    not (SRC / "cwlib").is_dir(), reason="needs the Chadwick sources (CHADWICK_SRC)"
)


def reviewed() -> dict[str, str]:
    rows = {}
    for line in BASELINE.read_text().splitlines():
        digest, _, ref = line.partition(" ")
        rows[ref] = digest
    return rows


def test_c_functions_match_the_reviewed_version() -> None:
    known, now = reviewed(), function_hashes(SRC.parent)
    added = sorted(set(now) - set(known))
    removed = sorted(set(known) - set(now))
    changed = sorted(ref for ref in set(now) & set(known) if now[ref] != known[ref])
    assert not (added or removed or changed), (
        "The Chadwick C sources differ from the version chadwickpy was reviewed against.\n"
        "Review each function against the port, then regenerate docs/about/c-function-hashes.txt.\n"
        f"added ({len(added)}): {added[:20]}\n"
        f"removed ({len(removed)}): {removed[:20]}\n"
        f"changed ({len(changed)}): {changed[:20]}"
    )
