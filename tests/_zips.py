"""Read members of a Retrosheet zip (the season drivers' only need from the archive)."""

import re
import urllib.request
import zipfile
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import IO


def iter_zip_members(path: str | Path) -> Iterator[tuple[str, IO[bytes]]]:
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            if not info.is_dir():
                with z.open(info) as member:
                    yield info.filename, member


_EVENT_NAME = re.compile(r"\.(ev|ed)[a-z]$", re.IGNORECASE)


def is_event_filename(name: str) -> bool:
    """True for Retrosheet event files (.EVN/.EVA/.EVE/.EVF/.EVR, deduced .EDx)."""
    base = name.replace("\\", "/").rsplit("/", 1)[-1]
    return not base.startswith("._") and bool(_EVENT_NAME.search(base))


def decade_zip(year: int, cache_dir: str | Path) -> Path:
    """Download (once) the Retrosheet event archive holding ``year``; for the sweep drivers only."""
    if not 1910 <= year <= date.today().year:
        raise ValueError(f"no event decade archive for {year}")
    name = f"{year // 10 * 10}seve.zip"
    target = Path(cache_dir) / name
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(
            f"https://www.retrosheet.org/events/{name}", headers={"User-Agent": "chadwickpy-tests"}
        )
        with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310
            target.write_bytes(resp.read())
    return target
