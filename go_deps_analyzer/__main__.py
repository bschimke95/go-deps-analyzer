"""Console script for go_deps_analyzer.

This module serves as the main entry point for the command-line interface.
"""

import sys

from go_deps_analyzer.cli import main

if __name__ == "__main__":
    sys.exit(main())
