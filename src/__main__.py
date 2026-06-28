"""Entry point for `python -m src`.

Delegates to the daily wake routine defined in `src.wake`.
"""

import sys

from .wake import main

sys.exit(main())
