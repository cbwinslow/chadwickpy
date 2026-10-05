"""A reader that closes the pipe early ends the tool quietly, as SIGPIPE ends the C tools."""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent


def test_closed_pipe_prints_no_traceback(tmp_path):
    folder = HERE / "reference" / "rosters" / "regular_2007"
    for f in folder.iterdir():
        (tmp_path / f.name).write_bytes(f.read_bytes())
    event_file = tmp_path / "2007TST.EVA"
    event_file.write_bytes((HERE / "fixtures" / "events" / "regular_2007.evt").read_bytes())
    proc = subprocess.Popen(
        [sys.executable, "-m", "chadwickpy", "cwevent", "-q", "-y", "2007", str(event_file)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=tmp_path,
    )
    assert proc.stdout is not None and proc.stderr is not None
    proc.stdout.close()  # the reader is gone before the tool writes
    err = proc.stderr.read().decode()
    proc.wait()
    assert "Traceback" not in err and "BrokenPipeError" not in err, err
