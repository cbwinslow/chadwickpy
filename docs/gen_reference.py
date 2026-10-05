"""Build the tool reference pages from the tools themselves, so they cannot drift.

Run by mkdocs-gen-files at docs build time: each page is the real ``-h`` and ``-d`` output
of the installed commands.
"""

import subprocess
import sys

import mkdocs_gen_files

TOOLS = {
    "cwevent": ("one row per event", True),
    "cwgame": ("one row per game", True),
    "cwdaily": ("one row per player per game", True),
    "cwsub": ("one row per substitution", True),
    "cwcomment": ("one row per comment", True),
    "cwbox": ("box scores (text, XML or SportsML)", False),
}


def run(tool: str, flag: str) -> str:
    out = subprocess.run(
        [sys.executable, "-m", "chadwickpy", tool, flag],
        capture_output=True,
        text=True,
        check=False,
    )
    text = out.stdout + out.stderr
    lines = text.splitlines()
    # drop Chadwick's copyright banner (first block) and keep the content
    start = next((i for i, ln in enumerate(lines) if "Copyright" in ln), -1)
    body = lines[start + 3 :] if start >= 0 else lines
    return "\n".join(ln.rstrip() for ln in body).strip("\n")


for tool, (what, has_fields) in TOOLS.items():
    page = [
        "---",
        f"description: Options and field list for chadwickpy's {tool}, which writes {what}. "
        "Generated from the tool itself.",
        "---",
        "",
        f"# {tool}",
        "",
        f"Writes {what}. Generated from `{tool} -h`"
        + (f" and `{tool} -d`" if has_fields else "")
        + ".",
        "",
        "## Options",
        "",
        "```text",
        run(tool, "-h"),
        "```",
    ]
    if has_fields:
        page += ["", "## Fields", "", "```text", run(tool, "-d"), "```"]
    with mkdocs_gen_files.open(f"reference/{tool}.md", "w") as f:
        f.write("\n".join(page) + "\n")
