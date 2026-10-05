from pathlib import Path

import pytest

from chadwickpy.tools.cli import IO, TOOLS, main

HERE = Path(__file__).parent
FIXTURES = HERE / "fixtures" / "events"
ROSTERS = HERE / "reference" / "rosters" / "regular_2007"


def test_parallel_matches_sequential_byte_for_byte(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Set up directory with roster files and two event files
    for f in ROSTERS.iterdir():
        (tmp_path / f.name).write_bytes(f.read_bytes())

    file_a = tmp_path / "2007A.EVA"
    file_b = tmp_path / "2007B.EVA"
    file_a.write_bytes((FIXTURES / "regular_2007.evt").read_bytes())
    file_b.write_bytes((FIXTURES / "negro_league.evt").read_bytes())

    monkeypatch.chdir(tmp_path)

    # 1. Run sequential (-j 1)
    seq_out: list[str] = []
    seq_err: list[str] = []
    seq_io = IO(out=seq_out.append, err=seq_err.append)
    status_seq = main(
        TOOLS["cwevent"],
        ["cwevent", "-j", "1", "-y", "2007", "-n", str(file_a), str(file_b)],
        seq_io,
    )
    assert status_seq == 0

    # 1b. Run default (no -j, which automatically defaults to multi-process parallel)
    def_out: list[str] = []
    def_err: list[str] = []
    def_io = IO(out=def_out.append, err=def_err.append)
    status_def = main(
        TOOLS["cwevent"],
        ["cwevent", "-y", "2007", "-n", str(file_a), str(file_b)],
        def_io,
    )
    assert status_def == 0

    # 2. Run parallel with explicit -j 2
    par_out: list[str] = []
    par_err: list[str] = []
    par_io = IO(out=par_out.append, err=par_err.append)
    status_par = main(
        TOOLS["cwevent"],
        ["cwevent", "-j", "2", "-y", "2007", "-n", str(file_a), str(file_b)],
        par_io,
    )
    assert status_par == 0

    # 3. Run parallel with auto -j 0
    auto_out: list[str] = []
    auto_err: list[str] = []
    auto_io = IO(out=auto_out.append, err=auto_err.append)
    status_auto = main(
        TOOLS["cwevent"],
        ["cwevent", "-j", "0", "-y", "2007", "-n", str(file_a), str(file_b)],
        auto_io,
    )
    assert status_auto == 0

    # Verify byte-for-byte exact equality
    seq_out_text = "".join(seq_out)
    seq_err_text = "".join(seq_err)
    par_out_text = "".join(par_out)
    par_err_text = "".join(par_err)
    auto_out_text = "".join(auto_out)
    auto_err_text = "".join(auto_err)

    def_out_text = "".join(def_out)
    def_err_text = "".join(def_err)

    assert seq_out_text == def_out_text, "Default parallel stdout differs from sequential!"
    assert seq_err_text == def_err_text, "Default parallel stderr differs from sequential!"
    assert seq_out_text == par_out_text, "Parallel stdout differs from sequential!"
    assert seq_err_text == par_err_text, "Parallel stderr differs from sequential!"
    assert seq_out_text == auto_out_text, "Auto parallel stdout differs from sequential!"
    assert seq_err_text == auto_err_text, "Auto parallel stderr differs from sequential!"


def test_parallel_handles_worker_exception(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Set up directory with roster files and an event file
    for f in ROSTERS.iterdir():
        (tmp_path / f.name).write_bytes(f.read_bytes())

    file_a = tmp_path / "2007A.EVA"
    file_a.write_bytes((FIXTURES / "regular_2007.evt").read_bytes())
    # Create an invalid file that raises an error
    bad_file = tmp_path / "bad.EVA"
    bad_file.write_bytes(b"nonexistent_content")

    monkeypatch.chdir(tmp_path)

    out: list[str] = []
    err: list[str] = []
    io = IO(out=out.append, err=err.append)
    status = main(
        TOOLS["cwevent"],
        ["cwevent", "-y", "2007", str(file_a), str(bad_file)],
        io,
    )
    # The process handles errors without crashing with an uncaught exception
    err_text = "".join(err)
    assert status != 0 or len(err_text) > 0
    assert "Processing file" in err_text or len(out) > 0


class _DiesAfterFirst:
    """A stand-in process pool whose worker "dies" after the first file's result is delivered."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        pass

    def __enter__(self) -> "_DiesAfterFirst":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def map(self, fn, tasks):  # type: ignore[no-untyped-def]
        from concurrent.futures.process import BrokenProcessPool

        tasks = list(tasks)
        yield fn(tasks[0])
        raise BrokenProcessPool("a worker died")


def test_a_dead_worker_does_not_duplicate_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the pool breaks part-way, files already written must not be written again."""
    for f in ROSTERS.iterdir():
        (tmp_path / f.name).write_bytes(f.read_bytes())
    file_a = tmp_path / "2007A.EVA"
    file_b = tmp_path / "2007B.EVA"
    file_a.write_bytes((FIXTURES / "regular_2007.evt").read_bytes())
    file_b.write_bytes((FIXTURES / "negro_league.evt").read_bytes())
    monkeypatch.chdir(tmp_path)
    argv = ["cwevent", "-y", "2007", "-n", str(file_a), str(file_b)]

    want: list[str] = []
    assert (
        main(TOOLS["cwevent"], ["cwevent", "-j", "1", *argv[1:]], IO(want.append, [].append)) == 0
    )

    import concurrent.futures

    monkeypatch.setattr(concurrent.futures, "ProcessPoolExecutor", _DiesAfterFirst)
    got: list[str] = []
    status = main(TOOLS["cwevent"], ["cwevent", "-j", "2", *argv[1:]], IO(got.append, [].append))
    assert status == 0
    assert "".join(got) == "".join(want)
