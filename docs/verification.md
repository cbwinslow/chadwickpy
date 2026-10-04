---
description: How chadwickpy output is proven identical to the real Chadwick tools across 116 seasons.
---

# How it was verified

* Each of the six tools was run for every season 1910-2025 against the real Chadwick built
  from commit `c685ab5` (reports 0.10.0): zero differences.
* Command-line sweeps, parser fuzzing, synthetic games and the write side are also compared.
* CI rebuilds Chadwick at that commit and runs the whole suite on Python 3.11-3.13; a skipped
  parity test fails the build.
