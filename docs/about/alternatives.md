---
description: How chadwickpy compares with the Chadwick C tools, pychadwick, pyretrosheet, Retrosheet's own CSV files and the R retrosheet package, and when to pick each.
---

# Other ways to work with Retrosheet data

There are several good options. This is a fair summary as of October 2026; check each
project's own page for current details.

| Option | What it is | Needs | Good for |
|---|---|---|---|
| **chadwickpy** | Pure-Python port of the six Chadwick tools | Python 3.11+ only | Chadwick's exact tables with one `pip install`, anywhere |
| **[Chadwick](https://github.com/chadwickbureau/chadwick)** (C) | The reference tools | C compiler to build, or a packaged build | Speed; the original |
| **[pychadwick](https://pypi.org/project/pychadwick/)** | Python bindings to Chadwick's C library | The compiled C library | Calling Chadwick from Python; per its page it supports event data only |
| **[pyretrosheet](https://pypi.org/project/pyretrosheet)** | Python library that downloads and parses Retrosheet play-by-play into Python objects | Python | Working with games as Python objects |
| **Retrosheet's CSV downloads** | Pre-parsed yearly tables from [Retrosheet](https://www.retrosheet.org) | Nothing | A table with no tooling, using Retrosheet's columns |
| **R [`retrosheet`](https://cran.r-project.org/package=retrosheet)** | R package that imports Retrosheet data | R | R users |

## Where chadwickpy fits

* It reproduces **Chadwick's output**, verified on every season from 1910 to 2025 (see
  [how it was verified](verification.md)), without needing the C library.
* It covers **all six tools**, not just `cwevent`.
* It is **slower** than the C original.

If you only want a CSV and are happy with Retrosheet's columns, you may not need any tool. If
you want Chadwick's definitions (the ones most published baseball research and tutorials use),
chadwickpy is the easiest way to get them.

!!! note "Corrections welcome"
    If something here is out of date or unfair to another project,
    [open an issue](https://github.com/cbwinslow/chadwickpy/issues/new?template=docs.yml).
