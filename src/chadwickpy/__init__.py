"""Pure-Python port of the Chadwick baseball tools (GPL-2.0-or-later source; see module headers)."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("chadwickpy")
except PackageNotFoundError:  # running from a source tree that is not installed
    __version__ = "0+unknown"
