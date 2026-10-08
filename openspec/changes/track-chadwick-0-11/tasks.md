# Tasks: track-chadwick-0-11

- [x] 1.1 Build the real 0.11.0 tools and run the suite against them (4,680 of 5,083 differ; almost all from `-q` and the version text)
- [x] 1.2 Command line: `-Q`, `-D dir`, version 0.11.0, copyright, help text (5 of 6 tools' `-h` identical to 0.11.0; `cwgame` still differs, see 2.x)
- [x] 1.3 Tests moved from `-q` to `-Q`; rerun to see the true differences (4,680 -> 855 failures)
- [x] 2.1 `cwgame`: `-d` date formats, default fields 0-84, BEVENT-matching fields, finishing pitcher, linescore
- [x] 2.2 `cwsub`: `COUNT_TX`; `cwevent`: pinch-runner position 12, `FLD_TEAM_ID` quoting
- [x] 3.1 Parser: each upstream parser change, test first (see proposal)
- [x] 3.2 Box scores: validation, PH/PR entries, zero sequence, day/night lookup
- [x] 3.3 File reading: record reader and tokenizer, `padj` semantics
- [x] 4.1 Re-capture stored reference outputs from 0.11.0
- [~] 4.2 CI builds Chadwick `v0.11.0` (done: `CHADWICK_REF: v0.11.0`; the build itself is checked by the PR's CI); weekly newest-Chadwick workflow passes
- [ ] 4.3 Re-run the proof: every season, every field and option, coverage, drift fingerprints
- [ ] 4.4 Docs and website for 0.11.0 (`-Q`, `-D`, seasons, verification page); ADR for following 0.11.0
- [ ] 4.5 Release 0.4.0 (owner approves the publish)

## Notes

- 2026-10-08: four groups ported the upstream changes in parallel and were merged without conflicts: full suite against the real 0.11.0 went 4,680 failed -> 855 -> 16 failed / 5,145 passed. The 16 were damaged-input cases and expectations of the old 0.10 error texts, handled by two more agents; the drift fingerprints (`docs/about/c-function-hashes.txt`, now 672 functions) and `c-inventory.txt` were regenerated for 0.11.0. Of the 20 C functions new in 0.11.0, 19 have a Python counterpart; `cwevent_fielder_id` is an output helper whose fields all match the real tool in the field sweep. `cw_strtok` was removed upstream.
