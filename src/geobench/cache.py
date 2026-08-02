"""Cache module."""

import ctypes
import logging
import os

logger = logging.getLogger(__name__)


def clear_cache():
    """Clear system caches."""
    # Try to flush all filesystem buffers to disk (Linux)
    if hasattr(os, "sync"):
        logger.debug("Flushing all filesystem buffers to disk")
        os.sync()

    # Try to drop caches (Linux)
    try:
        with open("/proc/sys/vm/drop_caches", "w") as file:
            logger.debug("Dropping filesystem cache from memory")
            file.write("3\n")
    except FileNotFoundError:
        pass
    except (PermissionError, OSError) as err:
        logger.debug("Failed to drop caches: %s", err)

    # Try to trim memory pages (Windows)
    if hasattr(ctypes, "windll"):
        try:
            psapi = ctypes.WinDLL("psapi", use_last_error=True)
            if not psapi.EmptyWorkingSet(-1):
                raise ctypes.WinError(ctypes.get_last_error())
        except OSError as err:
            logger.debug("Failed to trim memory pages: %s", err)
