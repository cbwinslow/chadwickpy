---
description: chadwickpy is a pure-Python port of the Chadwick baseball tools; install with pip and run cwevent, cwgame, cwdaily, cwsub, cwcomment and cwbox on Retrosheet files.
---

# chadwickpy

A pure-Python port of the [Chadwick](https://github.com/chadwickbureau/chadwick) baseball
tools. It turns [Retrosheet](https://www.retrosheet.org) event files into the same tables
Chadwick's `cwevent`, `cwgame`, `cwdaily`, `cwsub`, `cwcomment` and `cwbox` produce.
No compiler, no C library, no dependencies.

```bash
pip install chadwickpy
```

* Output is byte-identical to the real Chadwick tools on every season 1910-2025.
* About 25 times slower than the C.
* Licence: AGPL-3.0-or-later; a derivative of Chadwick (GPL-2.0-or-later).

See [Install and use](usage.md) to get started.
