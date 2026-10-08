"""Port of Chadwick's command-line drivers: ``cwtools.c`` (``main`` and the shared option
handling) and the option parsing, messages and field lists of ``cwevent``, ``cwgame``,
``cwdaily``, ``cwsub``, ``cwcomment`` and ``cwbox``.

Chadwick is Copyright (c) 2002-2023 Dr T L Turocy and the Chadwick Baseball
Bureau, licensed GPL-2.0-or-later; this module is a derivative of it and keeps
that notice. The C keeps the options in globals and reaches each tool through function
pointers (``cwtools_parse_command_line`` and friends); here a ``Tool`` holds the same hooks
and ``Options`` the same globals. Files are read from the current directory, like the C.

``main(tool, argv)`` returns the exit status. Chadwick's ``exit(1)`` is ``Exit``; where the C
would crash or read uninitialised memory, the ports of the processing code raise
``ValueError``, which ``main`` reports on stderr and turns into status 1 after writing the
output produced so far, as the C's buffered output would be.

Deviations: ``-y`` keeps at most 5 characters, as ``strncpy(year, ..., 5)`` does, but the C
does not terminate a 5-character year and so reads on into whatever follows it in memory; the
port stops at 5. ``-m`` appears in the help of ``cwsub`` and ``cwcomment`` but, as in the C, is
not an option.
"""

import glob
import logging
import os
import signal
import sys
from collections.abc import Callable, Collection, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from chadwickpy.book import scorebook_read
from chadwickpy.file import ReportedError
from chadwickpy.game import Game
from chadwickpy.roster import League, Roster
from chadwickpy.tools import comment, cwgame, daily, events, sub
from chadwickpy.tools.cwbox import process_game as box_process_game
from chadwickpy.tools.tools import read_rosters, select_game
from chadwickpy.xmlwrite import XMLDoc, xml_document_cleanup

VERSION = "0.11.0"
log = logging.getLogger("chadwickpy")


class Exit(Exception):  # noqa: N818 - the C's exit()
    """Chadwick calling ``exit(code)``"""

    def __init__(self, code: int) -> None:
        super().__init__(code)
        self.code = code


@dataclass
class Options:
    """The globals of ``cwtools.c`` and of each tool"""

    fields: set[int]
    ext_fields: set[int] = field(default_factory=set)
    year: str = ""
    first_date: str = "0101"
    last_date: str = "1231"
    game_id: str = ""
    data_dir: str = ""  # -D: where TEAMyyyy and the roster files are (empty: current directory)
    ascii: bool = True
    quiet: bool = False
    print_header: bool = False
    use_xml: bool = False
    use_sportsml: bool = False
    jobs: int | None = None
    date_format: int = cwgame.CWGAME_DATE_NOSLASH_FULL  # cwgame -dsf, -dsp, -dnf, -dnp


@dataclass
class IO:
    """Where the C's ``stdout`` and ``stderr`` go; text is written as Latin-1 bytes"""

    out: Callable[[str], None]
    err: Callable[[str], None]


@dataclass(frozen=True)
class Tool:
    """One program: its ``program_name``, messages, options and the hooks ``cwtools.c`` calls"""

    name: str
    title: str
    help_lines: tuple[str, ...]
    max_field: int
    default_fields: Collection[int]
    max_ext_field: int | None = None  # ``None``: no ``-x``
    field_list: Callable[[], str] | None = None  # ``None``: no ``-d``
    has_f: bool = True
    has_n: bool = True
    box_options: bool = False  # ``-X`` and ``-S``
    process_game: Callable[[Options, IO, Game, Roster | None, Roster | None], None] = field(
        default=lambda o, io, g, v, h: None
    )
    header: Callable[[Options], str] | None = None
    state: dict[str, XMLDoc] = field(default_factory=dict)


def welcome_message(tool: Tool, argv0: str) -> str:
    """``<tool>_print_welcome_message``"""
    return (
        f"\n{tool.title}, version {VERSION}"
        f"\n  Type '{argv0} -h' for help.\n"
        "Copyright (c) 2002-2026\nDr T L Turocy, Chadwick Baseball Bureau (ted.turocy@gmail.com)\n"
        "This is free software, subject to the terms of the GNU GPL license.\n\n"
    )


def _digit(c: str) -> bool:
    return "0" <= c <= "9"


def parse_field_list(text: str, maxfield: int, io: IO, program_name: str) -> set[int]:
    """``cwtools_parse_field_list``: the fields named by a list such as ``0-4,7,12,20-31``"""
    mask = 0xFFFFFFFF  # the numbers are ``unsigned int``
    chosen: set[int] = set()
    i = 0
    err = False
    n = len(text)

    def at(k: int) -> str:
        return text[k] if k < n else "\0"

    while i < n:
        if not _digit(text[i]):
            break
        first = ord(text[i]) - 48
        i += 1
        while _digit(at(i)):
            first = (first * 10 + ord(at(i)) - 48) & mask
            i += 1
        if first > maxfield:
            break
        if at(i) == "-":
            i += 1
            if not _digit(at(i)):
                break
            second = ord(at(i)) - 48
            i += 1
            while _digit(at(i)):
                second = (second * 10 + ord(at(i)) - 48) & mask
                i += 1
            if second > maxfield or second < first:
                err = True
                break
            chosen.update(range(first, second + 1))
        else:
            chosen.add(first)
        if at(i) == ",":
            i += 1
        # Anything else is an error; will be caught at beginning of next iteration of loop

    if i < n or err:
        io.err(
            "\n*** Invalid field spec.  A field spec is a list of fields\n"
            "and ranges, separated by commas.  No spaces are allowed.\n"
            "Example:\n"
            f"  {program_name} -f 0-4,7,12,20-31\n"
            "The spec is invalid if any value is larger than the max\n"
            f"field number, {maxfield}.\n"
        )
        raise Exit(1)
    return chosen


_DATE_SWITCHES = {
    "-dsf": cwgame.CWGAME_DATE_SLASH_FULL,
    "-dsp": cwgame.CWGAME_DATE_SLASH_PARTIAL,
    "-dnf": cwgame.CWGAME_DATE_NOSLASH_FULL,
    "-dnp": cwgame.CWGAME_DATE_NOSLASH_PARTIAL,
}


def parse_command_line(tool: Tool, argv: list[str], opts: Options, io: IO) -> int:
    """``<tool>_parse_command_line``: returns the index of the first file argument"""
    opts.year = ""
    i = 1
    while i < len(argv):
        arg = argv[i]
        if arg == "-a":
            opts.ascii = True
        elif arg == "-d" and tool.field_list is not None:
            io.err(welcome_message(tool, argv[0]))
            io.err(tool.field_list())
            raise Exit(0)
        elif arg in _DATE_SWITCHES and tool.name == "cwgame":
            opts.date_format = _DATE_SWITCHES[arg]
        elif arg == "-D":
            i += 1
            if i < len(argv):
                opts.data_dir = argv[i][:1023]
        elif arg == "-e":
            i += 1
            if i < len(argv):
                opts.last_date = argv[i][:4]
        elif arg == "-h":
            io.err(welcome_message(tool, argv[0]))
            io.err("".join(tool.help_lines))
            raise Exit(0)
        elif arg == "-Q":
            opts.quiet = True
        elif arg == "-i":
            i += 1
            if i < len(argv):
                opts.game_id = argv[i][:19]
        elif arg == "-f" and tool.has_f:
            i += 1
            if i < len(argv):
                opts.fields = parse_field_list(argv[i], tool.max_field, io, tool.name)
        elif arg == "-n" and tool.has_n:
            opts.print_header = True
        elif arg == "-ft":
            opts.ascii = False
        elif arg == "-s":
            i += 1
            if i < len(argv):
                opts.first_date = argv[i][:4]
        elif arg == "-x" and tool.max_ext_field is not None:
            i += 1
            if i < len(argv):
                assert tool.max_ext_field is not None
                opts.ext_fields = parse_field_list(argv[i], tool.max_ext_field, io, tool.name)
        elif arg == "-y":
            i += 1
            if i < len(argv):
                opts.year = argv[i][:5]
        # This part is cwbox-specific
        elif arg == "-X" and tool.box_options:
            opts.use_xml = True
        elif arg == "-S" and tool.box_options:
            opts.use_sportsml = True
        elif arg == "-j":
            if i + 1 < len(argv) and argv[i + 1].isdigit():
                i += 1
                opts.jobs = int(argv[i])
            else:
                opts.jobs = 0
        elif arg.startswith("-j") and arg[2:].isdigit():
            opts.jobs = int(arg[2:])
        elif arg == "--jobs":
            if i + 1 < len(argv) and argv[i + 1].isdigit():
                i += 1
                opts.jobs = int(argv[i])
            else:
                opts.jobs = 0
        elif arg[:1] == "-":
            io.err(f"*** Invalid option '{arg}'.\n")
            raise Exit(1)
        else:
            break
        i += 1
    return i


def read_team_rosters(opts: Options, io: IO) -> League:
    """``cwtools_read_rosters``: ``TEAMyyyy`` (else ``teamyyyy``) and the ``.ROS`` files"""
    filename = _build_path(opts.data_dir, f"TEAM{opts.year}")
    team_file = _read(filename)
    if team_file is None:
        # Also try lowercase version
        filename = _build_path(opts.data_dir, f"team{opts.year}")
        team_file = _read(filename)
        if team_file is None:
            io.err(f"Can't find teamfile ({filename})\n")
            raise Exit(1)
    return read_rosters(team_file, opts.year, lambda name: _read(_build_path(opts.data_dir, name)))


def _build_path(data_dir: str, filename: str) -> str:
    """``cwtools_build_path``: ``-D`` directory (and a ``/`` unless it already ends in one) in
    front of ``filename``; the file name alone when no directory was given"""
    if not data_dir:
        return filename
    return data_dir + ("" if data_dir.endswith("/") else "/") + filename


def _read(filename: str) -> bytes | None:
    """``fopen(filename, "r")`` and read everything; ``None`` where the open fails"""
    try:
        return Path(filename).read_bytes()
    except OSError:
        return None


def process_scorebook(tool: Tool, opts: Options, io: IO, league: League, filename: str) -> None:
    """``cwtools_process_scorebook`` and ``cwtools_iterate_games``"""
    if not opts.quiet:
        io.err(f"[Processing file {filename}.]\n")
    data = _read(filename)
    games = scorebook_read(data) if data is not None else None
    if games is None:
        io.err(f"Warning: could not open file '{filename}'\n")
        return
    for game in games:
        if select_game(game, opts.game_id, opts.first_date, opts.last_date):
            tool.process_game(
                opts,
                io,
                game,
                league.roster_find(game.info_lookup("visteam")),
                league.roster_find(game.info_lookup("hometeam")),
            )


class _Stderr(logging.Handler):
    """The messages Chadwick prints to stderr; the "invalid record" warning echoes the record as
    read, end of line included, and every other message ends in a newline"""

    def __init__(self, io: IO) -> None:
        super().__init__(logging.WARNING)
        self.io = io

    def emit(self, record: logging.LogRecord) -> None:
        if isinstance(record.args, tuple) and any(a is None for a in record.args):
            # A NULL string passed to "%s" prints as "(null)" in glibc; Python would print None.
            record.args = tuple("(null)" if a is None else a for a in record.args)
        msg = record.getMessage()
        if msg.startswith("WARNING: reading stopped"):
            return  # the port's own diagnostic; Chadwick prints nothing here
        raw = "skipping invalid record" in msg
        self.io.err(msg if raw or msg.endswith("\n") else msg + "\n")


def _write_stdout(text: str) -> None:
    sys.stdout.buffer.write(text.encode("latin-1"))


def _write_stderr(text: str) -> None:
    sys.stderr.buffer.write(text.encode("latin-1"))


def _worker_scorebook(task: tuple[str, Options, League, str]) -> tuple[str, str, int]:
    tool_name, opts, league, filename = task
    tool = TOOLS[tool_name]
    out_chunks: list[str] = []
    err_chunks: list[str] = []
    sub_io = IO(out=out_chunks.append, err=err_chunks.append)
    handler = _Stderr(sub_io)
    # A forked worker inherits the parent's handler, which writes straight to stderr: each warning
    # would be printed a second time, early and out of order. Only this worker's handler may act.
    inherited = log.handlers[:]
    log.handlers[:] = [handler]
    prev_level = log.level
    log.setLevel(logging.WARNING)
    status = 0
    try:
        process_scorebook(tool, opts, sub_io, league, filename)
    except ReportedError:
        status = 1  # the message is already on stderr
    except (ValueError, IndexError) as e:
        sub_io.err(f"chadwickpy: {e}\n")
        status = 1
    except Exception as e:
        sub_io.err(f"chadwickpy: unexpected error processing {filename}: {e}\n")
        status = 1
    finally:
        log.handlers[:] = inherited
        log.setLevel(prev_level)
    return "".join(out_chunks), "".join(err_chunks), status


def _init_worker(sys_paths: list[str]) -> None:
    for p in reversed(sys_paths):
        if p not in sys.path:
            sys.path.insert(0, p)


def _process_files_parallel(
    tool_name: str,
    opts: Options,
    io: IO,
    league: League,
    files: list[str],
    workers: int,
) -> int:
    from concurrent.futures import ProcessPoolExecutor
    from concurrent.futures.process import BrokenProcessPool

    tasks = [(tool_name, opts, league, f) for f in files]
    overall_status = 0
    written = 0  # files whose output has already been sent; never send those again
    try:
        with ProcessPoolExecutor(
            max_workers=workers,
            initializer=_init_worker,
            initargs=(list(sys.path),),
        ) as pool:
            for out_text, err_text, st in pool.map(_worker_scorebook, tasks):
                if out_text:
                    io.out(out_text)
                if err_text:
                    io.err(err_text)
                if st != 0:
                    overall_status = st
                written += 1
    except (BrokenProcessPool, OSError, ImportError, NotImplementedError) as e:
        # A worker died or processes cannot be started here. Finish the files not yet written
        # one at a time, in order, so the output is the same as a normal run.
        io.err(f"chadwickpy: parallel run failed ({e}); finishing the remaining files in order\n")
        tool = TOOLS[tool_name]
        for filename in files[written:]:
            process_scorebook(tool, opts, io, league, filename)
    return overall_status


def _quota_cpus(quota: str, period: str) -> int | None:
    """CPUs allowed by a CFS quota/period pair (rounded up, at least one), or ``None``."""
    try:
        q, p = int(quota), int(period)
    except ValueError:
        return None
    if q <= 0 or p <= 0:
        return None  # "max", -1, 0 and other nonsense: no usable limit
    return max(1, -(-q // p))


def cgroup_cpu_limit(
    root: Path = Path("/sys/fs/cgroup"), self_cgroup: Path = Path("/proc/self/cgroup")
) -> int | None:
    """The CPU limit (whole CPUs, rounded up) a Linux container or service puts on this process.

    Docker ``--cpus``, Kubernetes limits and systemd ``CPUQuota=`` are CFS quotas in the control-
    group files, which neither CPU affinity nor ``os.process_cpu_count`` reflects. Both layouts are
    read (version 2 ``cpu.max``; version 1 ``cpu.cfs_quota_us`` / ``cpu.cfs_period_us``), for the
    process's own group and every parent group up to the root; the tightest limit wins. ``None``
    when there is no limit or the files cannot be read.
    """
    try:
        lines = self_cgroup.read_text().splitlines()
    except OSError:
        return None
    limits: list[int] = []
    for line in lines:
        parts = line.split(":", 2)
        if len(parts) != 3:
            continue
        _, controllers, path = parts
        if controllers and "cpu" not in controllers.split(","):
            continue
        group = Path(path.lstrip("/"))
        for directory in [group, *group.parents]:
            for base in (root, root / "cpu,cpuacct", root / "cpu"):
                try:
                    if controllers == "":  # version 2
                        quota, period = (base / directory / "cpu.max").read_text().split()[:2]
                    else:  # version 1
                        quota = (base / directory / "cpu.cfs_quota_us").read_text().strip()
                        period = (base / directory / "cpu.cfs_period_us").read_text().strip()
                except (OSError, ValueError):
                    continue
                limit = _quota_cpus(quota, period)
                if limit is not None:
                    limits.append(limit)
    return min(limits) if limits else None


def available_cpus() -> int:
    """CPUs this process may actually use: CPU affinity (``taskset``, cpusets) and any container
    CPU quota, whichever is tighter."""
    process_cpu_count = getattr(os, "process_cpu_count", None)  # Python 3.13+
    if process_cpu_count is not None:
        usable = process_cpu_count() or 1
    else:
        try:
            usable = len(os.sched_getaffinity(0)) or 1  # Linux: honours taskset and cpusets
        except AttributeError:  # macOS, Windows
            usable = os.cpu_count() or 1
    limit = cgroup_cpu_limit()
    return min(usable, limit) if limit is not None else usable


def _is_windows() -> bool:
    return os.name == "nt"


def expand_filespec(spec: str, windows: bool | None = None) -> list[str]:
    """``cwtools_process_filespec``: the files a command-line name stands for.

    On Unix the C program processes the name as given (the shell has already expanded any
    wildcard). On Windows and DOS it expands ``*`` and ``?`` itself (``_findfirst``), because
    ``cmd.exe`` does not: every match is used, in name order, and a name or pattern that matches
    nothing is skipped silently. Unlike the C, which keeps only the bare file name, the directory
    part of a pattern is kept so that ``sub\\*.EVA`` finds its files.
    """
    if not (_is_windows() if windows is None else windows):
        return [spec]
    # only * and ? are wildcards here; glob would also treat [ ] specially
    return sorted(glob.glob(spec.replace("[", "[[]")))


def worker_count(n_files: int, jobs: int | None) -> int:
    """How many worker processes to use for ``n_files`` files.

    One file, or ``-j 1``: no extra processes. ``-j N``: N (never more than there are files).
    Otherwise (automatic): the usable CPUs, leaving one free when there are more than four.
    """
    if n_files <= 1 or jobs == 1:
        return 1
    if jobs is not None and jobs > 1:
        target = jobs
    else:
        detected = available_cpus()
        target = max(1, detected - 1) if detected > 4 else detected
    return min(n_files, max(1, target))


def main(tool: Tool, argv: list[str] | None = None, io: IO | None = None) -> int:
    """``main`` of ``cwtools.c``: returns the exit status"""
    args = list(sys.argv if argv is None else argv)
    if io is None:
        io = IO(out=_write_stdout, err=_write_stderr)
    handler = _Stderr(io)
    log.addHandler(handler)
    previous = log.level
    log.setLevel(logging.WARNING)
    opts = Options(fields=set(tool.default_fields))
    status = 0
    try:
        i = parse_command_line(tool, args, opts, io)
        if not opts.quiet:
            io.err(welcome_message(tool, args[0]))
        league = read_team_rosters(opts, io)
        if tool.header is not None and opts.ascii and opts.print_header:
            io.out(tool.header(opts) + "\n")
        if tool.box_options and opts.use_sportsml:
            doc = XMLDoc("sports-content-set")
            tool.state["doc"] = doc
            io.out(doc.take())
        files = [name for spec in args[i:] for name in expand_filespec(spec)]
        env_jobs = os.environ.get("CHADWICK_JOBS")
        if env_jobs is not None and opts.jobs is None:
            opts.jobs = (
                0 if env_jobs.lower() == "auto" else (int(env_jobs) if env_jobs.isdigit() else 1)
            )

        workers = worker_count(len(files), opts.jobs)
        if workers > 1 and not (tool.box_options and (opts.use_sportsml or opts.use_xml)):
            parallel_status = _process_files_parallel(tool.name, opts, io, league, files, workers)
            if parallel_status != 0:
                status = parallel_status
        else:
            for filename in files:
                process_scorebook(tool, opts, io, league, filename)
        if "doc" in tool.state:
            xml_document_cleanup(tool.state["doc"])
            io.out(tool.state.pop("doc").take())
    except Exit as e:
        status = e.code
    except ReportedError:
        status = 1  # the message is already on stderr
    except (ValueError, IndexError) as e:
        io.err(f"chadwickpy: {e}\n")
        status = 1
    finally:
        log.removeHandler(handler)
        log.setLevel(previous)
        tool.state.clear()
    return status


# ---------------------------------------------------------------------------------------
# The tools

_COMMON_HELP = (
    "  -h        print this help\n",
    "  -i id     only process game given by id\n",
    "  -y year   Year to process (for teamyyyy and aaayyyy.ros).\n",
    "  -D dir    Directory to find team and roster files (default is current directory)\n",
    "  -s start  Earliest date to process (mmdd).\n",
    "  -e end    Last date to process (mmdd).\n",
)
_FORMAT_HELP = (
    "  -a        generate Ascii-delimited format files (default)\n",
    "  -ft       generate Fortran format files\n",
)
_QUIET_HELP = "  -Q        operate quietly; do not output progress messages\n"
_NAMES_HELP = "  -n        print field names in first row of output\n\n"


def _lines(io: IO, lines: Iterable[str]) -> None:
    chunk: list[str] = []
    for line in lines:
        chunk.append(line)
        if len(chunk) >= 500:
            io.out("\n".join(chunk) + "\n")
            chunk.clear()
    if chunk:
        io.out("\n".join(chunk) + "\n")


def _event_process(o: Options, io: IO, g: Game, v: Roster | None, h: Roster | None) -> None:
    _lines(io, events.game_lines(g, v, h, o.ascii, o.fields, o.ext_fields))


def _game_process(o: Options, io: IO, g: Game, v: Roster | None, h: Roster | None) -> None:
    try:
        line = cwgame.game_line(g, v, h, o.ascii, o.fields, o.ext_fields, o.date_format)
    except cwgame.BufferTruncated as e:
        io.err(f"{e}\n")  # the C prints this and calls exit(1)
        raise ReportedError(str(e)) from e
    io.out(line + "\n")


def _daily_process(o: Options, io: IO, g: Game, v: Roster | None, h: Roster | None) -> None:
    _lines(io, daily.game_lines(g, o.ascii, tuple(sorted(o.fields))))


def _sub_process(o: Options, io: IO, g: Game, v: Roster | None, h: Roster | None) -> None:
    _lines(io, sub.game_lines(g, o.ascii, tuple(sorted(o.fields))))


def _comment_process(o: Options, io: IO, g: Game, v: Roster | None, h: Roster | None) -> None:
    _lines(io, comment.game_lines(g, o.ascii, tuple(sorted(o.fields))))


CWEVENT = Tool(
    name="cwevent",
    title="Chadwick expanded event descriptor",
    help_lines=(
        "\n\ncwevent generates files suitable for use by dBase or Lotus-like programs\n",
        "Each record describes one event.\n",
        "Usage: cwevent [options] eventfile...\n",
        "options:\n",
        *_COMMON_HELP,
        *_FORMAT_HELP,
        "  -f flist  give list of fields to output\n",
        "              Default is 0-6,8-9,12-13,16-17,26-40,43-45,51,58-61\n",
        "  -x flist  give list of extended fields to output\n",
        "              Default is none\n",
        "  -d        print list of field numbers and descriptions\n",
        _QUIET_HELP,
        _NAMES_HELP,
    ),
    max_field=events.MAX_FIELD,
    default_fields=events.DEFAULT_FIELDS,
    max_ext_field=events.MAX_EXT_FIELD,
    field_list=lambda: (
        "\nThese are the available fields and the numbers to use with the -f option\n"
        "to name them.  The default fields are marked with an asterisk (*).\n"
        "\n"
        "number  field\n"
        "------  -----\n"
        + "".join(f"{i:<2}      {d}\n" for i, d in enumerate(events.DESCRIPTIONS))
        + "\n"
        "These additional fields are available in this version of cwevent.\n"
        "These are specified using the -x option, and appear in the output\n"
        "after all fields specified with -f. By default, none of these\n"
        "fields are output.\n"
        "\n"
        "number  field\n"
        "------  -----\n"
        + "".join(f"{i:<2}      {d}\n" for i, d in enumerate(events.EXT_DESCRIPTIONS))
    ),
    process_game=_event_process,
    header=lambda o: events.header_line(o.fields, o.ext_fields),
)

CWGAME = Tool(
    name="cwgame",
    title="Chadwick expanded game descriptor",
    help_lines=(
        "\n\ncwgame generates files suitable for use by dBase or Lotus-like programs\n",
        "Each record describes one game.\n",
        "Usage: cwgame [options] eventfile...\n",
        "options:\n",
        *_COMMON_HELP,
        *_FORMAT_HELP,
        "  -f flist  give list of fields to output\n",
        "              Default is 0-84\n",
        "  -x flist  give list of extended fields to output\n",
        "              Default is none\n",
        "  -d        print list of field numbers and descriptions\n",
        "  The -dxx switches choose a date format for the gamedate field.\n",
        "  -dsf      slashes, full year: mm/dd/yyyy\n",
        "  -dsp      slashes, partial year: mm/dd/yy\n",
        "  -dnf      no slashes, full year: yyyymmdd (the default)\n",
        "  -dnp      no slashes, partial year: yymmdd\n",
        _QUIET_HELP,
        _NAMES_HELP,
    ),
    max_field=cwgame.MAX_FIELD,
    default_fields=cwgame.DEFAULT_FIELDS,
    max_ext_field=cwgame.MAX_EXT_FIELD,
    field_list=lambda: (
        "\nThese are the available fields and the numbers to use with the -f option\n"
        "to name them.  All are included by default.\n"
        "\n"
        "number  field\n"
        "------  -----\n"
        + "".join(f"{i:<2}      {d}\n" for i, (_, _, d) in enumerate(cwgame.FIELDS))
        + "\n"
        "These additional fields are available in this version of cwgame.\n"
        "These are specified using the -x option, and appear in the output\n"
        "after all fields specified with -f. By default, none of these\n"
        "fields are output.\n"
        "\n"
        "number  field\n"
        "------  -----\n"
        + "".join(f"{i:<2}      {d}\n" for i, (_, _, d) in enumerate(cwgame.EXT_FIELDS))
    ),
    process_game=_game_process,
    header=lambda o: cwgame.header_line(o.fields, o.ext_fields),
)

CWDAILY = Tool(
    name="cwdaily",
    title="Chadwick player game-by-game generator",
    help_lines=(
        "\n\ncwdaily generates files suitable for use by dBase or Lotus-like programs\n",
        "Each record describes one game.\n",
        "Usage: cwdaily [options] eventfile...\n",
        "options:\n",
        *_COMMON_HELP,
        *_FORMAT_HELP,
        "  -f flist  give list of fields to output\n",
        "              Default is 0-153\n",
        "  -d        print list of field numbers and descriptions\n",
        _QUIET_HELP,
        _NAMES_HELP,
    ),
    max_field=daily.MAX_FIELD,
    default_fields=range(daily.MAX_FIELD + 1),
    field_list=lambda: (
        "\nThese are the available fields and the numbers to use with the -f option\n"
        "to name them.  All are included by default.\n"
        "\n"
        "number  field\n"
        "------  -----\n"
        + "".join(f"{i:<3}     {d}\n" for i, (_, _, d) in enumerate(daily.FIELDS))
        + "\n"
    ),
    process_game=_daily_process,
    header=lambda o: daily.header_line(tuple(sorted(o.fields))),
)

CWSUB = Tool(
    name="cwsub",
    title="Chadwick substitute descriptor",
    help_lines=(
        "\n\ncwsub generates files suitable for use by dBase or Lotus-like programs\n",
        "Each record describes one substitution.\n",
        "Usage: cwsub [options] eventfile...\n",
        "options:\n",
        *_COMMON_HELP,
        *_FORMAT_HELP,
        "  -m        use master player file instead of local roster files\n",
        "  -f flist  give list of fields to output\n",
        "              Default is 0-9.\n",
        "  -d        print list of field numbers and descriptions\n",
        _QUIET_HELP,
        _NAMES_HELP,
    ),
    max_field=sub.MAX_FIELD,
    default_fields=range(sub.MAX_FIELD + 1),
    field_list=lambda: (
        "\nThese are the available fields and the numbers to use with the -f option\n"
        "to name them.  All are included by default.\n"
        "\n"
        "number  field\n"
        "------  -----\n" + "".join(f"{i:<2}      {d}\n" for i, (_, _, d) in enumerate(sub.FIELDS))
    ),
    process_game=_sub_process,
    header=lambda o: sub.header_line(tuple(sorted(o.fields))),
)

CWCOMMENT = Tool(
    name="cwcomment",
    title="Chadwick comment extractor",
    help_lines=(
        "\n\ncwcomment generates files suitable for use by dBase or Lotus-like programs\n",
        "Each record contains one comment from the event file.\n",
        "Usage: cwcomment [options] eventfile...\n",
        "options:\n",
        *_COMMON_HELP,
        *_FORMAT_HELP,
        "  -m        use master player file instead of local roster files\n",
        "  -f flist  give list of fields to output\n",
        "              Default is 0-9.\n",
        "  -d        print list of field numbers and descriptions\n\n",
        _QUIET_HELP,
        _NAMES_HELP,
    ),
    max_field=comment.MAX_FIELD,
    default_fields=range(comment.MAX_FIELD + 1),
    field_list=lambda: (
        "\nThese are the available fields and the numbers to use with the -f option\n"
        "to name them.  All are included by default.\n"
        "\n"
        "number  field\n"
        "------  -----\n"
        + "".join(f"{i:<2}      {d}\n" for i, (_, _, d) in enumerate(comment.FIELDS))
        + "\n"
    ),
    process_game=_comment_process,
    header=lambda o: comment.header_line(tuple(sorted(o.fields))),
)


def _box_process(o: Options, io: IO, g: Game, v: Roster | None, h: Roster | None) -> None:
    doc = CWBOX.state.get("doc")
    text = box_process_game(g, v, h, o.use_xml, doc, o.use_sportsml)
    if text is not None:
        io.out(text)


CWBOX = Tool(
    name="cwbox",
    title="Chadwick boxscore generator",
    help_lines=(
        "\n\ncwbox generates boxscores from play-by-play files\n",
        "Usage: cwbox [options] eventfile...\n",
        "options:\n",
        *_COMMON_HELP,
        "  -X        output boxscores as XML.\n",
        "  -S        output boxscores as SportsML.\n",
        _QUIET_HELP,
    ),
    max_field=0,
    default_fields=(),
    has_f=False,
    has_n=False,
    box_options=True,
    process_game=_box_process,
)

TOOLS = {t.name: t for t in (CWEVENT, CWGAME, CWDAILY, CWSUB, CWCOMMENT, CWBOX)}


def run(name: str) -> int:
    """Entry point of the console script for the tool ``name``"""
    try:
        status = main(TOOLS[name], [name, *sys.argv[1:]])
        sys.stdout.flush()
    except (BrokenPipeError, OSError):
        # The reader went away (``cwevent ... | head``). The C tools die quietly from SIGPIPE;
        # point stdout at /dev/null so Python's exit-time flush does not print a traceback too.
        try:
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        except OSError:
            pass
        sigpipe = getattr(signal, "SIGPIPE", 13)
        return 128 + int(sigpipe)
    return status


def main_cwevent() -> int:
    return run("cwevent")


def main_cwgame() -> int:
    return run("cwgame")


def main_cwdaily() -> int:
    return run("cwdaily")


def main_cwsub() -> int:
    return run("cwsub")


def main_cwcomment() -> int:
    return run("cwcomment")


def main_cwbox() -> int:
    return run("cwbox")


def main_umbrella() -> int:
    """``chadwickpy TOOL [options] eventfile...``: the Chadwick tool names under one command"""
    if len(sys.argv) < 2 or sys.argv[1] not in TOOLS:
        sys.exit(f"usage: chadwickpy {{{','.join(TOOLS)}}} [options] eventfile...")
    tool = sys.argv.pop(1)
    return run(tool)
