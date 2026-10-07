"""``cwevent`` field by field: every standard field and every extended field requested on its own,
and random field subsets, against the real ``cwevent`` (OpenSpec change verify-port-completeness,
task 2.1).

``test_event_differential`` already compares all fields at once. Asking for one field alone also
checks that no field depends on another being computed in the same run (several fields are
computed lazily and cached per event). Every fixture event file (all eras and rule variants) is
used, in both output formats; subsets also run with and without synthesised rosters.
"""

import random
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from chadwick_tool import real_tool, run_tool  # noqa: E402
from test_cwbox_differential import synthetic_rosters  # noqa: E402
from test_event_differential import FIXTURES, port_output  # noqa: E402

pytestmark = pytest.mark.skipif(real_tool("cwevent") is None, reason="needs cwevent on PATH")

N_FIELDS = 97
N_EXT = 67
FORMATS = {"ascii": (["-n"], True), "fixed": (["-ft"], False)}


def arg_list(values: list[int]) -> str:
    return ",".join(str(v) for v in values)


def compare_all_fixtures(
    fmt: str, fields: list[int], ext: list[int], rosters: bool = False
) -> None:
    flags, ascii_ = FORMATS[fmt]
    args = [*flags]
    if fields:
        args += ["-f", arg_list(fields)]
    if ext:
        args += ["-x", arg_list(ext)]
    for fixture in FIXTURES:
        data = fixture.read_bytes()
        support = synthetic_rosters(data) if rosters else None
        run = run_tool("cwevent", fixture, args, support)
        assert run is not None
        assert run[0] == 0, (fixture.name, args)
        # With -f the standard fields are exactly those listed; without -f the defaults apply.
        std = tuple(fields) if fields else None
        if std is None:
            from chadwickpy.tools.events import DEFAULT_FIELDS

            std = tuple(DEFAULT_FIELDS)
        expected = port_output(data, ascii_, std, tuple(ext), "-n" in args, support)
        assert run[1] == expected, (fixture.name, args)


@pytest.mark.parametrize("fmt", FORMATS)
@pytest.mark.parametrize("field", range(N_FIELDS))
def test_standard_field_alone(field: int, fmt: str) -> None:
    compare_all_fixtures(fmt, [field], [])


@pytest.mark.parametrize("fmt", FORMATS)
@pytest.mark.parametrize("ext", range(N_EXT))
def test_extended_field_alone(ext: int, fmt: str) -> None:
    compare_all_fixtures(fmt, [0], [ext])


@pytest.mark.parametrize("fmt", FORMATS)
@pytest.mark.parametrize("seed", range(25))
def test_random_field_subsets(seed: int, fmt: str) -> None:
    rng = random.Random(seed * 7 + len(fmt))
    fields = sorted(rng.sample(range(N_FIELDS), rng.randint(1, 40)))
    ext = sorted(rng.sample(range(N_EXT), rng.randint(0, 25)))
    compare_all_fixtures(fmt, fields, ext, rosters=seed % 2 == 1)
