"""API-level corners of ``book.py``, ``roster.py``, ``file.py``, ``write.py`` and ``xmlwrite.py``.

``tests/reference/final_a_dump.c`` is built against the real Chadwick sources (``cwlib`` and the
``cwtools`` XML writer). It calls the C functions directly: scorebook insertion, iteration and
removal (``book.c``), ``cw_roster_player_find`` with a NULL id, ``cw_atoi``, ``cw_game_write`` of
an info record without data, and the ``xml_*`` calls in odd orders (closing a closed node,
attributes on a closed node, character data while a child is open). The port makes the same
calls. Where the C crashes (``strcmp`` of a missing ``date``) the port raises ``ValueError``.
Runs only where ``gcc`` and the Chadwick sources (``CHADWICK_SRC``) are available.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "reference"))
sys.path.insert(0, str(HERE))
from test_reader_differential import FIXTURES, SRC  # noqa: E402

from chadwickpy.book import Scorebook  # noqa: E402
from chadwickpy.file import cw_atoi  # noqa: E402
from chadwickpy.game import Game, read_games  # noqa: E402
from chadwickpy.roster import Roster  # noqa: E402
from chadwickpy.write import game_write_header  # noqa: E402
from chadwickpy.xmlwrite import (  # noqa: E402
    XMLDoc,
    XMLNode,
    xml_document_cleanup,
    xml_node_attribute,
    xml_node_attribute_fmt,
    xml_node_attribute_int,
    xml_node_attribute_posint,
    xml_node_cdata,
    xml_node_close,
    xml_node_open,
)

pytestmark = pytest.mark.skipif(
    shutil.which("gcc") is None or not (SRC / "cwtools" / "xmlwrite.c").exists(),
    reason="needs gcc and the Chadwick sources (CHADWICK_SRC)",
)


@pytest.fixture(scope="module")
def harness(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("final_a") / "final_a_dump"
    cmd = ["gcc", "-O1", "-w", "-I", str(SRC / "cwlib"), "-I", str(SRC / "cwtools"), "-I", str(SRC)]
    cmd += [str(HERE / "reference" / "final_a_dump.c"), str(SRC / "cwtools" / "xmlwrite.c")]
    cmd += [*map(str, sorted((SRC / "cwlib").glob("*.c"))), "-o", str(out)]
    subprocess.run(cmd, check=True, capture_output=True)
    return out


def c_run(harness: Path, *args: str | Path) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run([str(harness), *map(str, args)], capture_output=True)


# ---------------------------------------------------------------------------------------------
# cw_atoi (file.py)
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "-2147483648",  # the longest negative number that still fits an int
        "-0000000001",
        "-2147483649",
        "-99999999999",
        "+5",
        " 12abc",
        "2147483647",
        "2147483648",
        "-",
        "",
    ],
)
def test_atoi_matches_chadwick(harness, text):
    run = c_run(harness, "atoi", text)
    assert run.returncode == 0
    assert cw_atoi(text) == int(run.stdout)


# ---------------------------------------------------------------------------------------------
# Scorebook insertion, iteration and removal (book.py)
# ---------------------------------------------------------------------------------------------


def port_book(data: bytes, script: list[list[str]]) -> str:
    book = Scorebook()
    out = [f"read={book.read(data)}\n"]
    for f in script:
        if f[0] == "new":
            game = Game(f[1])
            if f[2] != "-":
                game.info_append("date", f[2])
            if f[3] != "-":
                game.info_append("number", f[3])
            out.append(f"insert={int(book.insert_game(game))}\n")
        elif f[0] == "insertnull":
            out.append(f"insert={int(book.insert_game(None))}\n")
        elif f[0] == "appendnull":
            out.append(f"append={int(book.append_game(None))}\n")
        elif f[0] == "iter":
            flt = (lambda g: g.game_id.endswith("0")) if int(f[1]) else None
            out.extend(f"it {g.game_id}\n" for g in book.iterate(flt))
        elif f[0] == "remove":
            game = book.remove_game(f[1])
            out.append(f"removed={game.game_id if game else '(none)'}\n")
        elif f[0] == "dump":
            out.extend(f"{g.game_id}\n" for g in book.games)
    return "".join(out)


def first_game_keys(path: Path) -> tuple[str, str]:
    game = next(iter(read_games(path.read_bytes())))
    return game.info_lookup("date") or "", game.info_lookup("number") or "0"


FIXTURE = FIXTURES / "regular_2007.evt"
BOOK_SAME = {
    # later than every game: the search runs off the end of the list
    "append_after_all": ["new Z1 9999/12/31 0", "dump"],
    # earlier than every game: goes first
    "before_all": ["new Z1 0000/01/01 0", "dump"],
    # between games (some earlier, one later): skips earlier games, stops at a later one
    "same_date_later_number": ["new Z1 {date} 9", "dump"],
    "same_date_earlier_number": ["new Z1 {date} -1", "dump"],
    "same_date_same_number": ["new Z1 {date} {number}", "dump"],
    "several": [
        "new Z1 9999/12/31 0",
        "new Z2 0000/01/01 0",
        "new Z3 {date} 5",
        "new Z4 5000/01/01 1",
        "dump",
    ],
    # NULL games are refused
    "null_insert": ["insertnull", "appendnull", "dump"],
    # iterate: every game, and only those the filter accepts (ids ending in 0 only)
    "iterate_all": ["new Z1 9999/12/31 0", "new Z2 9999/12/31 1", "iter 0"],
    "iterate_filtered": [
        "new Z1 9999/12/31 0",
        "new Z2 9999/12/31 1",
        "new Z3 0000/01/01 1",
        "iter 1",
    ],
    "remove_missing": ["remove NOSUCHGAME", "dump"],
}
# the C compares the strings of a missing info record with strcmp, which crashes
BOOK_CRASH = {
    "no_date": ["new Z1 - 0"],
    "no_number_same_date": ["new Z1 {date} -"],
}


def script_for(lines: list[str]) -> list[list[str]]:
    date, number = first_game_keys(FIXTURE)
    return [ln.format(date=date, number=number).split(" ") for ln in lines]


def write_script(tmp_path: Path, script: list[list[str]]) -> Path:
    path = tmp_path / "script.txt"
    path.write_text("".join("\t".join(f) + "\n" for f in script))
    return path


@pytest.mark.parametrize("name", BOOK_SAME)
def test_book_edits_match_chadwick(harness, tmp_path, name):
    script = script_for(BOOK_SAME[name])
    run = c_run(harness, "book", FIXTURE, write_script(tmp_path, script))
    assert run.returncode == 0
    assert port_book(FIXTURE.read_bytes(), script).encode() == run.stdout


@pytest.mark.parametrize("name", BOOK_CRASH)
def test_book_insert_without_date_or_number_crashes_both(harness, tmp_path, name):
    script = script_for(BOOK_CRASH[name])
    run = c_run(harness, "book", FIXTURE, write_script(tmp_path, script))
    assert run.returncode != 0
    with pytest.raises(ValueError, match="strcmp"):
        port_book(FIXTURE.read_bytes(), script)


# ---------------------------------------------------------------------------------------------
# roster.py and write.py: NULL arguments
# ---------------------------------------------------------------------------------------------


def test_roster_find_null_id_matches_chadwick(harness, tmp_path):
    roster_file = tmp_path / "r.ros"
    roster_file.write_bytes(b"abcd001,Last,First,R,R,T,2\n")
    run = c_run(harness, "rosterfind", roster_file, "abcd001")
    assert run.stdout == b"null=1 known=abcd001\n"
    roster = Roster("T", "L", "C", "N")
    roster.read(roster_file.read_bytes())
    assert roster.player_find(None) is None
    assert roster.player_find("abcd001") is not None


def test_info_record_without_data_crashes_both(harness):
    run = c_run(harness, "infonull")
    assert run.returncode != 0
    game = Game("X", "2")
    game.info_append("foo", None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="without data"):
        game_write_header(game)


# ---------------------------------------------------------------------------------------------
# The XML writer (xmlwrite.py)
# ---------------------------------------------------------------------------------------------


def port_xml(script: list[list[str]]) -> str:
    doc = XMLDoc("root")
    nodes: list[XMLNode] = [doc.root]
    for f in script:
        op = f[0]
        if op == "open":
            nodes.append(xml_node_open(nodes[int(f[1])], f[2]))
        elif op == "close":
            xml_node_close(nodes[int(f[1])])
        elif op == "cdata":
            xml_node_cdata(nodes[int(f[1])], f[2])
        elif op == "attr":
            xml_node_attribute(nodes[int(f[1])], f[2], f[3])
        elif op == "attri":
            xml_node_attribute_int(nodes[int(f[1])], f[2], int(f[3]))
        elif op == "attrp":
            xml_node_attribute_posint(nodes[int(f[1])], f[2], int(f[3]))
        elif op == "attrf":
            xml_node_attribute_fmt(nodes[int(f[1])], f[2], f[3])
        elif op == "cleanup":
            xml_document_cleanup(doc)
    return doc.take()


XML_SCRIPTS = {
    "close_twice": ["open 0 a", "close 1", "close 1", "cleanup"],
    "close_root_then_cleanup": ["open 0 a", "close 0", "cleanup"],
    "cleanup_open_tree": ["open 0 a", "open 1 b", "cleanup"],
    "cdata_with_open_child": ["open 0 a", "cdata 0 hello", "close 1", "cleanup"],
    "cdata_twice": ["cdata 0 one", "cdata 0 two", "cleanup"],
    "cdata_after_children": ["open 0 a", "close 1", "cdata 0 text", "cdata 0 more", "cleanup"],
    "attributes_on_open_node": [
        "attr 0 x y",
        "attri 0 n -3",
        "attrp 0 p 4",
        "attrf 0 f val",
        "cleanup",
    ],
    "attributes_on_closed_node": [
        "open 0 a",
        "close 1",
        "attr 1 x y",
        "attri 1 n 5",
        "attrp 1 p 5",
        "attrf 1 f val",
        "cleanup",
    ],  # fmt: skip
    "posint_negative": ["open 0 a", "attrp 1 p -1", "attrp 1 q 0", "cleanup"],
    "reopen_reuses_node": ["open 0 a", "close 1", "open 0 b", "attr 2 k v", "cleanup"],
    "attribute_after_child": ["open 0 a", "close 1", "attr 0 late 1", "cleanup"],
}


@pytest.mark.parametrize("name", XML_SCRIPTS)
def test_xml_writer_matches_chadwick(harness, tmp_path, name):
    script = [ln.split(" ", 3) for ln in XML_SCRIPTS[name]]
    run = c_run(harness, "xml", write_script(tmp_path, script))
    assert run.returncode == 0
    assert port_xml(script).encode() == run.stdout
