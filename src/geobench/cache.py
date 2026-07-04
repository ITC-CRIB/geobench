"""Cache module."""

import ctypes
import os
import platform

import logging

logger = logging.getLogger(__name__)


def _clear_linux_cache():
    """Clear system caches on Linux."""
    logger.debug("Flushing all filesystem buffers to disk")
    try:
        os.system("sync")

    except Exception as err:
        logger.debug("Failed to flush filesystem buffers to disk: %s", err)

    logger.debug("Clearing filesystem cache from memory")
    try:
        os.system("echo 3 > /proc/sys/vm/drop_caches")

    except Exception as err:
        logger.debug("Failed to clear filesystem cache from memory: %s", err)


def _clear_windows_cache():
    """Clear system caches on Windows."""
    logger.debug("Trimming memory pages")
    try:
        ctypes.windll.psapi.EmptyWorkingSet(-1)

    except Exception as err:
        logger.debug("Failed to trim memory pages: %s", err)


def clear_cache():
    """Clear system caches."""
    system = platform.system()

    if system == "Linux":
        _clear_linux_cache()

    elif system == "Windows":
        _clear_windows_cache()

    else:
        logger.debug("Unsupported operating system: %s", system)
