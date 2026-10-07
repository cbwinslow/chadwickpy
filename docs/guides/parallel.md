---
description: How chadwickpy uses several CPU cores by itself, how to choose the number of workers with -j or CHADWICK_JOBS, and how it behaves in containers and on small machines.
---

# Using several cores

Give `chadwickpy` several event files (a whole season is about 30) and it processes them in parallel
by itself. The output is the same as a one-process run, in the same order, byte for byte.

```bash
cwevent -y 2023 -n 2023*.EV* > events.csv        # automatic: uses the CPUs available
cwevent -j 1 -y 2023 -n 2023*.EV* > events.csv   # one process
cwevent -j 8 -y 2023 -n 2023*.EV* > events.csv   # eight workers
CHADWICK_JOBS=4 cwevent -y 2023 -n 2023*.EV* > events.csv
```

## How many workers

| You ask for | You get |
|---|---|
| nothing, or `-j 0`, or `CHADWICK_JOBS=auto` | one worker per usable CPU, one fewer on machines with more than four CPUs |
| `-j N` | `N` workers |
| one file, or `-j 1` | no extra processes |

In every case there are never more workers than files, so a single file gains nothing from more cores.

"Usable CPUs" means the CPUs this process is allowed to use. That honours `taskset` and similar
limits, and also a **CPU limit set on a container or service** (Docker `--cpus`, Kubernetes limits,
systemd `CPUQuota=`). A process limited to 2 CPUs on a 64-core host starts 2 workers, not 63.

## What it was tested with

* 1, 2, 3, 4, 5, 8, 16 and 40 cores: identical output every time.
* Python's `fork`, `spawn` (macOS and Windows) and `forkserver` (the Python 3.14 default on Linux)
  worker start methods: identical output and identical warnings.
* `-j` values from 2 to 100,000: capped at the number of files.
* A Docker container limited to 2 CPUs (Python 3.14): identical to the C program's output.

## Warnings and errors

Warning and error messages (for example a game that fails the sanity check) are printed once, in
file order, exactly as in a one-process run.

## Speed

On one core chadwickpy is slower than the C tools; with several files and several cores it catches
up (see [compared with Chadwick](../about/compared-with-chadwick.md) for measured times).
