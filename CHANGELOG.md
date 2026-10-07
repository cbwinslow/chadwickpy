# Changelog

## [0.3.0](https://github.com/cbwinslow/chadwickpy/compare/v0.2.1...v0.3.0) (2026-10-07)


### Features

* automatic worker count honours container CPU limits (Docker --cpus, Kubernetes, systemd; cgroup v1 and v2) ([f54941a](https://github.com/cbwinslow/chadwickpy/commit/f54941aec0855d6c15ab85ca437f0e3e4e73519e))
* expand wildcard file names on Windows like cwtools_process_filespec ([f54941a](https://github.com/cbwinslow/chadwickpy/commit/f54941aec0855d6c15ab85ca437f0e3e4e73519e))


### Bug Fixes

* parallel workers printed every warning twice and out of order under fork (inherited log handler) ([f54941a](https://github.com/cbwinslow/chadwickpy/commit/f54941aec0855d6c15ab85ca437f0e3e4e73519e))

## [0.2.1](https://github.com/cbwinslow/chadwickpy/compare/v0.2.0...v0.2.1) (2026-10-07)


### Bug Fixes

* a dead worker no longer makes the parallel run print files twice ([#18](https://github.com/cbwinslow/chadwickpy/issues/18)) ([212b445](https://github.com/cbwinslow/chadwickpy/commit/212b445d4215c046dbc12639e789e2df1f057ecf))
* audit findings - differences from the C tools on defined behaviour (stacked on [#23](https://github.com/cbwinslow/chadwickpy/issues/23)) ([#24](https://github.com/cbwinslow/chadwickpy/issues/24)) ([e9a2531](https://github.com/cbwinslow/chadwickpy/commit/e9a25311879619da77814c521d56974ff15f96cd))
* automatic worker count follows the CPUs the process may use (not all installed CPUs) ([#19](https://github.com/cbwinslow/chadwickpy/issues/19)) ([6a7015f](https://github.com/cbwinslow/chadwickpy/commit/6a7015f260d9e88ae6c08ecc85f66a5f5dcd6707))
* reproduce what the C does with damaged box-score records ([#23](https://github.com/cbwinslow/chadwickpy/issues/23)) ([e0fa81d](https://github.com/cbwinslow/chadwickpy/commit/e0fa81dbbe4c0bbf7e39b4592f23b74bc8dc63d0))
* restore parity with Chadwick on end-of-file and odd input (0.2.0 regressions) ([#17](https://github.com/cbwinslow/chadwickpy/issues/17)) ([062f94f](https://github.com/cbwinslow/chadwickpy/commit/062f94f76e480df9943322174080a875b5b3e773))

## [0.2.0](https://github.com/cbwinslow/chadwickpy/compare/v0.1.1...v0.2.0) (2026-10-05)


### Features

* optimize parser hot paths and enable automatic multi-core parallelism ([#15](https://github.com/cbwinslow/chadwickpy/issues/15)) ([73ef97e](https://github.com/cbwinslow/chadwickpy/commit/73ef97ed172222ad0ab2f7eb4c2df75087d2f19d))

## [0.1.1](https://github.com/cbwinslow/chadwickpy/compare/v0.1.0...v0.1.1) (2026-10-05)


### Bug Fixes

* end quietly when the reader closes the pipe (cwevent | head) ([#8](https://github.com/cbwinslow/chadwickpy/issues/8)) ([3e4b2a3](https://github.com/cbwinslow/chadwickpy/commit/3e4b2a378bab87a1255ca9ca0827d3f10ccc7896))

## 0.1.0 (2026-10-04)


### Features

* chadwickpy, pure-Python port of the Chadwick tools ([fbb5745](https://github.com/cbwinslow/chadwickpy/commit/fbb5745404f10dede6e2fbffb4950a5caa42073b))

## Changelog
