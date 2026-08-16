"""Enable ``python -m gemma_qat_bench``."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
