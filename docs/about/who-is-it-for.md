---
description: Who chadwickpy is for - researchers, data scientists and developers who need Retrosheet play-by-play as tables without building Chadwick - and when another tool is a better fit.
---

# Who is it for?

## It is a good fit if you

* want **play-by-play data from Retrosheet as tables** (CSV, SQL, pandas) and need Chadwick's
  well-known columns, such as `cwevent`'s 97 standard fields and 67 extended ones;
* work somewhere you **cannot or would rather not compile C**: a managed notebook, a locked-down
  work laptop, Windows, a CI job, a container with no build tools;
* are **reproducing or extending work** that used the Chadwick tools and want the same
  definitions for events, runner advances, and counts;
* want to **call the parser from Python** without shelling out to a separate program;
* want one `pip install` and nothing else: there are no dependencies.

## Use something else if you

* process **many seasons repeatedly** and speed matters more than convenience: per core the C tools
  are about 10 to 40 times faster, and they can also be run on several cores
  (see [compared with Chadwick](compared-with-chadwick.md));
* want **ready-made tables with no tool at all**: Retrosheet publishes its own CSV downloads,
  which use Retrosheet's columns rather than Chadwick's;
* want **pitch-by-pitch tracking data** (velocity, spin, location): Retrosheet event files
  record the result of each pitch (ball, strike, foul...), not measurements. That data comes from
  other sources.
* need **live or current-season feeds**: chadwickpy reads files you give it.

## What you need to know

* Basic command-line use, or basic Python.
* Where to get Retrosheet's event files (see [Getting started](../getting-started.md)).
* Retrosheet's data-use notice applies to anything you publish (see the [FAQ](faq.md)).
