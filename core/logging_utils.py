from __future__ import annotations

import logging
import sys


def setup_logging() -> None:
    root = logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )
    handler.setFormatter(formatter)
    root.handlers = [handler]
    root.setLevel(logging.INFO)
