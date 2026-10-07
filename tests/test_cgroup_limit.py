"""A container CPU limit (Docker ``--cpus``, Kubernetes limits, systemd ``CPUQuota=``) caps the
automatic number of workers (OpenSpec change verify-port-completeness, task 4.6).

``os.sched_getaffinity`` and ``os.process_cpu_count`` do not see such a quota: a process limited
to 2 CPUs on a 64-core host would otherwise start 63 workers. The limit is read from the Linux
control-group files; here they are written into a temporary tree, in both the version 2 and the
version 1 layouts.
"""

from pathlib import Path

import pytest

from chadwickpy.tools import cli


def v2(root: Path, text: str, group: str = "") -> None:
    d = root / group
    d.mkdir(parents=True, exist_ok=True)
    (d / "cpu.max").write_text(text)


def v1(root: Path, quota: str, period: str = "100000", group: str = "") -> None:
    d = root / "cpu,cpuacct" / group
    d.mkdir(parents=True, exist_ok=True)
    (d / "cpu.cfs_quota_us").write_text(quota)
    (d / "cpu.cfs_period_us").write_text(period)


def whoami(tmp: Path, line: str) -> Path:
    path = tmp / "self_cgroup"
    path.write_text(line + "\n")
    return path


@pytest.mark.parametrize(
    ("text", "want"),
    [
        ("max 100000\n", None),  # no limit
        ("200000 100000\n", 2),
        ("150000 100000\n", 2),  # a fraction rounds up
        ("50000 100000\n", 1),  # never below one
        ("1000000 100000\n", 10),
        ("", None),
        ("garbage\n", None),
        ("100000\n", None),
        ("0 100000\n", None),  # nonsense: ignore, do not stop the run
        ("-5 100000\n", None),
    ],
)
def test_cgroup_v2_cpu_max(tmp_path: Path, text: str, want: int | None) -> None:
    root = tmp_path / "cg"
    v2(root, text)
    assert cli.cgroup_cpu_limit(root, whoami(tmp_path, "0::/")) == want


@pytest.mark.parametrize(
    ("quota", "period", "want"),
    [
        ("-1", "100000", None),
        ("400000", "100000", 4),
        ("250000", "100000", 3),
        ("x", "100000", None),
    ],
)
def test_cgroup_v1_quota(tmp_path: Path, quota: str, period: str, want: int | None) -> None:
    root = tmp_path / "cg"
    v1(root, quota, period)
    assert cli.cgroup_cpu_limit(root, whoami(tmp_path, "4:cpu,cpuacct:/")) == want


def test_the_limit_of_a_parent_group_applies_to_a_child(tmp_path: Path) -> None:
    root = tmp_path / "cg"
    v2(root, "200000 100000\n", "job")  # the parent: 2 CPUs
    v2(root, "max 100000\n", "job/step")  # the child: no limit of its own
    assert cli.cgroup_cpu_limit(root, whoami(tmp_path, "0::/job/step")) == 2


def test_the_tightest_limit_in_the_chain_wins(tmp_path: Path) -> None:
    root = tmp_path / "cg"
    v2(root, "800000 100000\n", "job")
    v2(root, "100000 100000\n", "job/step")
    assert cli.cgroup_cpu_limit(root, whoami(tmp_path, "0::/job/step")) == 1


def test_no_control_group_files_means_no_limit(tmp_path: Path) -> None:
    assert cli.cgroup_cpu_limit(tmp_path / "nothing", tmp_path / "nothing_either") is None


def _cpus(monkeypatch: pytest.MonkeyPatch, usable: int, limit: int | None) -> None:
    monkeypatch.setattr(cli.os, "cpu_count", lambda: 64, raising=False)
    monkeypatch.setattr(cli.os, "sched_getaffinity", lambda _pid: set(range(usable)), raising=False)
    monkeypatch.delattr(cli.os, "process_cpu_count", raising=False)
    monkeypatch.setattr(cli, "cgroup_cpu_limit", lambda *a, **k: limit)


def test_a_two_cpu_limit_on_a_sixty_four_core_host_gives_two_workers(monkeypatch) -> None:
    _cpus(monkeypatch, 64, 2)
    assert cli.available_cpus() == 2
    assert cli.worker_count(100, None) == 2  # not 63


def test_a_limit_above_the_usable_cpus_changes_nothing(monkeypatch) -> None:
    _cpus(monkeypatch, 4, 16)
    assert cli.available_cpus() == 4


def test_no_limit_changes_nothing(monkeypatch) -> None:
    _cpus(monkeypatch, 8, None)
    assert cli.available_cpus() == 8
    assert cli.worker_count(100, None) == 7


def test_an_explicit_job_count_is_still_obeyed(monkeypatch) -> None:
    _cpus(monkeypatch, 64, 2)
    assert cli.worker_count(100, 12) == 12
