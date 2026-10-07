"""List every function defined in Chadwick's C sources and say where chadwickpy ports it.

    python c_inventory.py CHADWICK_SRC > ../../docs/about/c-inventory.txt

A C function counts as *found* when its name (with or without the ``cw_`` prefix, and with the
struct-prefix removed, e.g. ``cw_gamestate_x`` -> ``x``) appears as a Python definition or in a
docstring/comment under ``src/chadwickpy``. Found is a lead, not proof; the coverage matrix
(docs/about/coverage-matrix.md) records the reviewed mapping. Development-time only.
"""

import re
import sys
from pathlib import Path

DEF = re.compile(r"^(?:static\s+)?[A-Za-z_][\w\s\*]*?\b(\w+)\s*\([^;{]*\)\s*\n?\{", re.M)
SKIP = {"if", "for", "while", "switch", "main"}


def c_functions(path: Path) -> list[str]:
    text = path.read_text(errors="replace")
    pattern = re.compile(
        r"^(?:(?:static|extern)\s+)?"
        r"(?:[A-Za-z_][\w \t\*]*\s+|[A-Za-z_][\w\*]*[ \t]*\n)?"
        r"\**(\w+)\s*\([^;{}]*\)\s*\{",
        re.M,
    )
    names = [
        m.group(1)
        for m in pattern.finditer(text)
        if m.group(1) not in SKIP | {"DECLARE_FIELDFUNC", "funcname"}
    ]
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


def main(src: Path) -> None:
    py = py_text(Path(__file__).resolve().parents[2] / "src" / "chadwickpy")
    total = missing = memory_only = 0
    for path in sorted((src / "src").rglob("*.c")):
        for name in c_functions(path):
            total += 1
            found = any(
                re.search(rf"(?<![A-Za-z0-9]){re.escape(v)}(?![A-Za-z0-9])", py)
                for v in variants(name)
            )
            memory = name.endswith("_cleanup") or name.endswith("_cleanup_tags")
            status = "ok" if found else ("n/a-mem" if memory else "MISSING")
            missing += status == "MISSING"
            memory_only += status == "n/a-mem"
            print(f"{status:<8} {path.relative_to(src / 'src')}::{name}")
    print(
        f"# total {total}, name found {total - missing - memory_only}, "
        f"memory cleanup {memory_only}, not found {missing}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main(Path(sys.argv[1]))
