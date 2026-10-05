"""The automatic number of worker processes must follow the CPUs the process may really use."""

import pytest

from chadwickpy.tools import cli


def _cpus(monkeypatch: pytest.MonkeyPatch, usable: int, *, installed: int = 40) -> None:
    monkeypatch.setattr(cli.os, "cpu_count", lambda: installed, raising=False)
    monkeypatch.setattr(cli.os, "sched_getaffinity", lambda _pid: set(range(usable)), raising=False)
    monkeypatch.delattr(cli.os, "process_cpu_count", raising=False)  # as on Python 3.11 and 3.12


def test_limited_to_two_cores_on_a_forty_core_machine(monkeypatch: pytest.MonkeyPatch) -> None:
    _cpus(monkeypatch, 2)
    assert cli.available_cpus() == 2
    assert cli.worker_count(30, None) == 2  # not 39


@pytest.mark.parametrize(("usable", "want"), [(1, 1), (2, 2), (4, 4), (5, 4), (8, 7), (40, 30)])
def test_auto_leaves_one_core_free_on_bigger_machines(
    monkeypatch: pytest.MonkeyPatch, usable: int, want: int
) -> None:
    _cpus(monkeypatch, usable)
    assert cli.worker_count(30, None) == want
    assert cli.worker_count(30, 0) == want  # -j 0 means automatic too


def test_never_more_workers_than_files(monkeypatch: pytest.MonkeyPatch) -> None:
    _cpus(monkeypatch, 40)
    assert cli.worker_count(3, None) == 3
    assert cli.worker_count(3, 16) == 3


def test_one_file_or_jobs_one_means_no_extra_processes(monkeypatch: pytest.MonkeyPatch) -> None:
    _cpus(monkeypatch, 40)
    assert cli.worker_count(1, None) == 1 and cli.worker_count(0, None) == 1
    assert cli.worker_count(30, 1) == 1


def test_an_explicit_number_is_used(monkeypatch: pytest.MonkeyPatch) -> None:
    _cpus(monkeypatch, 2)
    assert cli.worker_count(30, 6) == 6


def test_python_313_uses_process_cpu_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli.os, "process_cpu_count", lambda: 3, raising=False)
    assert cli.available_cpus() == 3


def test_without_affinity_support_falls_back_to_cpu_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delattr(cli.os, "process_cpu_count", raising=False)
    monkeypatch.delattr(cli.os, "sched_getaffinity", raising=False)
    monkeypatch.setattr(cli.os, "cpu_count", lambda: 8)
    assert cli.available_cpus() == 8
    monkeypatch.setattr(cli.os, "cpu_count", lambda: None)
    assert cli.available_cpus() == 1
