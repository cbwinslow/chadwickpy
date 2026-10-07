"""The parallel run must work however Python starts worker processes and however many it is asked
for (OpenSpec change verify-port-completeness, parallel robustness).

Linux starts workers by ``fork``; macOS and Windows use ``spawn`` (everything sent to a worker must
be picklable and importable), and Python 3.14 changes the Linux default to ``forkserver``. Each
case runs in a fresh interpreter with the start method set, and the output must equal the
single-process run (``-j 1``) byte for byte.
"""

import multiprocessing
import os
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
FIXTURES = HERE / "fixtures" / "events"
ROSTERS = HERE / "reference" / "rosters" / "regular_2007"

DRIVER = """
import multiprocessing, os, sys
from chadwickpy.tools.cli import TOOLS, main
if __name__ == "__main__":
    method, jobs, *files = sys.argv[1:]
    if method != "default":
        multiprocessing.set_start_method(method)
    tool = os.environ.get("TOOL", "cwevent")
    flags = ["-n"] if tool == "cwevent" else []
    # the real stdout and stderr, as the console command uses them
    sys.exit(main(TOOLS[tool], [tool, "-j", jobs, "-y", "2007", *flags, *files]))
"""


def season_dir(tmp_path: Path, n_files: int) -> list[str]:
    for f in ROSTERS.iterdir():
        (tmp_path / f.name).write_bytes(f.read_bytes())
    sources = [FIXTURES / "regular_2007.evt", FIXTURES / "negro_league.evt"]
    names = []
    for i in range(n_files):
        name = f"2007{i:02d}.EVA"
        (tmp_path / name).write_bytes(sources[i % 2].read_bytes())
        names.append(name)
    (tmp_path / "driver.py").write_text(DRIVER)
    return names


def run(tmp_path: Path, method: str, jobs: str, files: list[str], tool: str = "cwevent"):
    return subprocess.run(
        [sys.executable, "driver.py", method, jobs, *files],
        cwd=tmp_path,
        env={**os.environ, "TOOL": tool},
        capture_output=True,
        timeout=300,
        check=False,
    )


METHODS = [
    m for m in ("fork", "spawn", "forkserver") if m in multiprocessing.get_all_start_methods()
]


@pytest.mark.parametrize("method", METHODS)
def test_start_method_gives_the_same_output(tmp_path: Path, method: str) -> None:
    files = season_dir(tmp_path, 4)
    serial = run(tmp_path, "default", "1", files)
    parallel = run(tmp_path, method, "3", files)
    assert serial.returncode == 0 and parallel.returncode == 0, parallel.stderr
    assert parallel.stdout == serial.stdout
    assert parallel.stderr == serial.stderr


@pytest.mark.parametrize("jobs", ["2", "5", "64", "100000"])
def test_any_job_count_gives_the_same_output(tmp_path: Path, jobs: str) -> None:
    """More workers than files, or than any machine has, is capped at the file count."""
    files = season_dir(tmp_path, 5)
    serial = run(tmp_path, "default", "1", files)
    parallel = run(tmp_path, "default", jobs, files)
    assert parallel.returncode == 0, parallel.stderr
    assert parallel.stdout == serial.stdout
    assert parallel.stderr == serial.stderr


# A game that fails the sanity check makes every tool print warnings on stderr. Those must come
# out once, in file order, exactly as in a single-process run, whichever way workers are started
# (under ``fork`` a worker inherits the parent's log handler, which printed each one a second
# time, early and out of order).
BAD_GAME = (
    b"id,TOR200705310\nversion,2\ninfo,visteam,CHA\ninfo,hometeam,TOR\ninfo,date,2007/05/31\n"
    b'start,aaaa001,"A A",0,1,11\n'
)


@pytest.mark.parametrize("method", METHODS)
def test_warnings_are_printed_once_and_in_order(tmp_path: Path, method: str) -> None:
    files = season_dir(tmp_path, 4)
    (tmp_path / "2007BAD.EVA").write_bytes(BAD_GAME)
    files.insert(2, "2007BAD.EVA")
    serial = run(tmp_path, "default", "1", files, "cwbox")
    parallel = run(tmp_path, method, "3", files, "cwbox")
    assert b"Sanity check fails" in serial.stderr, "the bad game must produce a warning"
    assert parallel.stdout == serial.stdout
    assert parallel.stderr == serial.stderr
