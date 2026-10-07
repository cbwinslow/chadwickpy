"""The parallel run must work however Python starts worker processes and however many it is asked
for (OpenSpec change verify-port-completeness, parallel robustness).

Linux starts workers by ``fork``; macOS and Windows use ``spawn`` (everything sent to a worker must
be picklable and importable), and Python 3.14 changes the Linux default to ``forkserver``. Each
case runs in a fresh interpreter with the start method set, and the output must equal the
single-process run (``-j 1``) byte for byte.
"""

import multiprocessing
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
FIXTURES = HERE / "fixtures" / "events"
ROSTERS = HERE / "reference" / "rosters" / "regular_2007"

DRIVER = """
import multiprocessing, sys
from chadwickpy.tools.cli import TOOLS, IO, main
if __name__ == "__main__":
    method, jobs, *files = sys.argv[1:]
    if method != "default":
        multiprocessing.set_start_method(method)
    out, err = [], []
    status = main(TOOLS["cwevent"],
                  ["cwevent", "-j", jobs, "-y", "2007", "-n", *files],
                  IO(out=out.append, err=err.append))
    sys.stdout.write("".join(out))
    sys.stderr.write("".join(err))
    sys.exit(status)
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


def run(tmp_path: Path, method: str, jobs: str, files: list[str]):
    return subprocess.run(
        [sys.executable, "driver.py", method, jobs, *files],
        cwd=tmp_path,
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
