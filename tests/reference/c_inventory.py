"""List every function defined in Chadwick's C sources and say where chadwickpy ports it.

    python c_inventory.py CHADWICK_SRC > ../../docs/about/c-inventory.txt

A C function counts as *found* when its name (with or without the ``cw_`` prefix, and with the
struct-prefix removed, e.g. ``cw_gamestate_x`` -> ``x``) appears as a Python definition or in a
docstring/comment under ``src/chadwickpy``. Found is a lead, not proof; the coverage matrix
(docs/about/coverage-matrix.md) records the reviewed mapping. Development-time only.
"""

import hashlib
import re
import sys
from pathlib import Path

DEF = re.compile(r"^(?:static\s+)?[A-Za-z_][\w\s\*]*?\b(\w+)\s*\([^;{]*\)\s*\n?\{", re.M)
SKIP = {"if", "for", "while", "switch", "main"}


_DEFINITION = re.compile(
    r"^(?:(?:static|extern)\s+)?"
    r"(?:[A-Za-z_][\w \t\*]*\s+|[A-Za-z_][\w\*]*[ \t]*\n)?"
    r"\**(\w+)\s*\([^;{}]*\)\s*\{",
    re.M,
)
_NOT_FUNCS = {"DECLARE_FIELDFUNC", "funcname"}


def c_functions(path: Path) -> list[str]:
    text = path.read_text(errors="replace")
    names = [m.group(1) for m in _DEFINITION.finditer(text) if m.group(1) not in SKIP | _NOT_FUNCS]
    # cwevent/cwgame/cwdaily/cwsub/cwcomment declare one function per output field through a macro.
    names += re.findall(r"^DECLARE_FIELDFUNC\((\w+)\)", text, re.M)
    return [n for n in names if n != "funcname"]


def py_text(root: Path) -> str:
    return "\n".join(p.read_text() for p in sorted(root.rglob("*.py")))


def variants(name: str) -> set[str]:
    base = name[3:] if name.startswith("cw_") else name
    out = {name, base}
    parts = base.split("_")
    for i in range(1, len(parts)):
        out.add("_".join(parts[i:]))
    return {v for v in out if len(v) > 3}


def _blank_comments_and_literals(text: str) -> str:
    """``text`` with comments and string/char literals replaced by spaces (same length), so that
    braces inside them are not counted."""
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        two = text[i : i + 2]
        if two == "//":
            j = text.find("\n", i)
            j = n if j < 0 else j
        elif two == "/*":
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
        elif text[i] in "\"'":
            quote, j = text[i], i + 1
            while j < n and text[j] != quote and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            j = min(j + 1, n)
        else:
            i += 1
            continue
        for k in range(i, j):
            if out[k] != "\n":
                out[k] = " "
        i = j
    return "".join(out)


def function_hashes(src: Path) -> dict[str, str]:
    """``file::function`` -> a short hash of the function's text (comments and white space
    removed) for every function in the C sources. A change to a function changes its hash."""
    hashes: dict[str, str] = {}
    for path in sorted((src / "src").rglob("*.c")):
        raw = path.read_text(errors="replace")
        text = _blank_comments_and_literals(raw)
        starts = [m for m in _DEFINITION.finditer(text) if m.group(1) not in SKIP | _NOT_FUNCS]
        macro = [m for m in re.finditer(r"^DECLARE_FIELDFUNC\((\w+)\)[^{;]*\{", text, re.M)]
        rel = path.relative_to(src / "src")
        for m in [*starts, *(m for m in macro if m.group(1) not in _NOT_FUNCS)]:
            depth, i = 1, m.end()
            while i < len(text) and depth:
                depth += (text[i] == "{") - (text[i] == "}")
                i += 1
            body = re.sub(r"\s+", " ", text[m.start() : i]).strip()
            digest = hashlib.sha256(body.encode()).hexdigest()[:16]
            key = f"{rel}::{m.group(1)}"
            while key in hashes:  # the same name defined more than once (platform variants)
                key += "#"
            hashes[key] = digest
    return hashes


def scan(src: Path) -> list[tuple[str, str, str]]:
    """(status, file, function) for every C function: ``ok``, ``n/a-mem`` or ``MISSING``."""
    py = py_text(Path(__file__).resolve().parents[2] / "src" / "chadwickpy")
    rows = []
    for path in sorted((src / "src").rglob("*.c")):
        for name in c_functions(path):
            found = any(
                re.search(rf"(?<![A-Za-z0-9]){re.escape(v)}(?![A-Za-z0-9])", py)
                for v in variants(name)
            )
            memory = name.endswith("_cleanup") or name.endswith("_cleanup_tags")
            status = "ok" if found else ("n/a-mem" if memory else "MISSING")
            rows.append((status, str(path.relative_to(src / "src")), name))
    return rows


def main(src: Path) -> None:
    rows = scan(src)
    for status, path, name in rows:
        print(f"{status:<8} {path}::{name}")
    missing = sum(r[0] == "MISSING" for r in rows)
    memory_only = sum(r[0] == "n/a-mem" for r in rows)
    print(
        f"# total {len(rows)}, name found {len(rows) - missing - memory_only}, "
        f"memory cleanup {memory_only}, not found {missing}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    if sys.argv[1:2] == ["--hashes"]:
        for ref, digest in sorted(function_hashes(Path(sys.argv[2])).items()):
            print(f"{digest} {ref}")
    else:
        main(Path(sys.argv[1]))
