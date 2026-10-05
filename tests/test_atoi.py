"""``cw_atoi`` must give the same answer as the original digit-by-digit version."""

import logging
import random

from chadwickpy.file import cw_atoi

_INT_MIN, _INT_MAX = -(2**31), 2**31 - 1
_LONG_MIN, _LONG_MAX = -(2**63), 2**63 - 1
log = logging.getLogger("chadwickpy.atoi-reference")


def _reference(text: str) -> int:
    i, n = 0, len(text)
    while i < n and text[i] in " \t\n\v\f\r":
        i += 1
    sign = 1
    if i < n and text[i] in "+-":
        sign = -1 if text[i] == "-" else 1
        i += 1
    start = i
    while i < n and "0" <= text[i] <= "9":
        i += 1
    if i > start:
        value = sign * int(text[start:i])
        if _INT_MIN <= value <= _INT_MAX and _LONG_MIN <= value <= _LONG_MAX:
            return value
    return -1


def test_matches_the_reference_on_random_text() -> None:
    rng = random.Random(1871)
    # Latin-1 text can hold characters Python calls digits ("²", "¹", "³") that C does not.
    alphabet = "0123456789 -+ab\t²¹³"
    for _ in range(30000):
        text = "".join(rng.choice(alphabet) for _ in range(rng.randrange(0, 13)))
        assert cw_atoi(text) == _reference(text), repr(text)


def test_big_numbers_are_invalid() -> None:
    for text in ("2147483648", "-2147483649", "99999999999999999999"):
        assert cw_atoi(text) == _reference(text) == -1
