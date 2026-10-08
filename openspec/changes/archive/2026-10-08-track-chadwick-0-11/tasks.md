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
- [x] 4.2 CI builds Chadwick `v0.11.0` (`CHADWICK_REF: v0.11.0`; green on main 2026-10-08 on Python 3.11-3.13); the weekly newest-Chadwick workflow ran by hand after the release (see Notes)
- [x] 4.3 Re-run the proof (2026-10-08): full suite against the real 0.11.0 tools 5,163 passed / 0 failed; every season 1908-2025, six tools, 16 option sets: 1,888 comparisons, 22 GB, 0 differences; 1897-1907 box scores: 176 comparisons, only the 14 known cwbox-text crashes (C SIGSEGV, 1901-1907) differ; drift fingerprints regenerated (672 functions). Coverage was not re-measured (99.06% measured on 0.3.0).
- [x] 4.4 Docs and website for 0.11.0 (`-Q`, `-D`, seasons, verification page); ADR for following 0.11.0
- [x] 4.5 Release 0.4.0 published 2026-10-08 (release PR #31, owner approved the publish); `pip install chadwickpy==0.4.0` from PyPI in a clean environment: cwevent, cwgame, cwdaily, cwsub, cwcomment, cwbox stdout and stderr identical to the real Chadwick 0.11.0 tools (with a bad game, `-D`, 1 and 4 workers); `-q` rejected like the C; website and PyPI page checked

## Notes

- 2026-10-08: four groups ported the upstream changes in parallel and were merged without conflicts: full suite against the real 0.11.0 went 4,680 failed -> 855 -> 16 failed / 5,145 passed. The 16 were damaged-input cases and expectations of the old 0.10 error texts, handled by two more agents; the drift fingerprints (`docs/about/c-function-hashes.txt`, now 672 functions) and `c-inventory.txt` were regenerated for 0.11.0. Of the 20 C functions new in 0.11.0, 19 have a Python counterpart; `cwevent_fielder_id` is an output helper whose fields all match the real tool in the field sweep. `cw_strtok` was removed upstream.
- 2026-10-08: after #30 was merged without waiting for CI, CI on main failed on 5 tests that asserted what the real C tool does with an unreadable date (uninitialised read: crash on some runners, output on others). #32 made them assert only the port (ADR-003). The release PR was then updated with GitHub's update-branch so it carried the fix.
