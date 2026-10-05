---
description: How chadwickpy output is proven identical to the real Chadwick tools - 116 seasons, six tools, command-line sweeps, parser fuzzing - and how to run the checks yourself.
---

# How it was verified

A translation is only useful if it gives the same answers. The checks compare
`chadwickpy` with the real Chadwick programs, built from commit `c685ab5`:

* **All six tools on every season 1910-2025**: whole-season output compared byte for byte.
  Result: zero differences.
* **Command-line behaviour**: option parsing, messages, exit status and error output.
* **Parser fuzzing**: damaged and unusual lines fed to both parsers.
* **Synthetic games** covering rare plays, and the **write side** (re-writing event files).
* **Captured fixtures** committed to the repo, so the tests run even without Chadwick.

## Run them yourself

```bash
git clone https://github.com/cbwinslow/chadwickpy
cd chadwickpy
uv run --with pytest pytest          # compares with captured Chadwick output
```

To compare against the live C tools, build Chadwick at the pinned commit and set
`CHADWICK_BIN` (the folder with `cwevent`) and `CHADWICK_SRC`. CI does exactly this on
Python 3.11, 3.12 and 3.13, and fails if any parity test is skipped.

The season-sweep scripts in `tests/reference/` need the Retrosheet decade archives.
