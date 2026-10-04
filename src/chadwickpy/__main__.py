"""``python -m chadwickpy TOOL [options] eventfile...`` runs one of the ported tools."""

import sys

from chadwickpy.tools.cli import main_umbrella

if __name__ == "__main__":
    sys.exit(main_umbrella())
