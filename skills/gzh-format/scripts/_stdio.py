"""Cross-platform UTF-8 console configuration for CLI scripts."""

from __future__ import annotations

import sys


def configure_utf8_stdio() -> None:
    """Prevent Windows legacy code pages from crashing on Chinese or emoji output."""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            # Embedded hosts and redirected streams may reject reconfiguration.
            pass
