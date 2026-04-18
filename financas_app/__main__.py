"""Allow running as: python -m financas_app"""
from __future__ import annotations

import sys

from financas_app.cli import main

if __name__ == "__main__":
    sys.exit(main())
