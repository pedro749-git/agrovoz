"""Lightweight timing helper for diagnosing slow requests.

Wrap a crucial (usually I/O-bound) step in ``with timed("label"):`` and it logs
the wall-clock milliseconds it took, at INFO. Purely observational: it never
changes behaviour and never swallows errors — on an exception it still logs the
elapsed time (marked as failed) and re-raises. Used to locate which stage of a
request is slow (the Qwen calls, the OSS upload, the AEMET call) from the logs.
"""

import logging
import time
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@contextmanager
def timed(label: str):
    start = time.perf_counter()
    failed = False
    try:
        yield
    except Exception:
        failed = True
        raise
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info("%s took %.0f ms%s", label, elapsed_ms, " (failed)" if failed else "")
