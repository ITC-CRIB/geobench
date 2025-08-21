import ctypes
import os
import platform


import logging
logger = logging.getLogger(__name__)


def clear_linux_cache():
    """Clears system caches on Linux."""
    logger.info("Flushing all filesystem buffers to disk...")
    try:
        os.system('sync; echo 3 > /proc/sys/vm/drop_caches')

    except Exception as err:
        logger.info(f"Failed to flush filesystem buffers to disk: {err}")

    logger.info("Clearing filesystem cache from memory...")
    try:
        os.system('echo 3 > /proc/sys/vm/drop_caches')

    except Exception as err:
        logger.info(f"Failed to clear filesystem cache from memory: {err}")


def _clear_windows_cache():
    """Clears system caches on Windows."""
    logger.info("Trimming memory pages...")
    try:
        ctypes.windll.psapi.EmptyWorkingSet(-1)
        logger.info("Memory pages are trimmed.")

    except Exception as err:
        logger.info(f"Failed to trim memory pages: {err}")


def clear_cache():
    """Clears system caches."""
    system = platform.system()

    if system == 'Linux':
        clear_linux_cache()

    elif system == 'Windows':
        clear_windows_cache()

    else:
        logger.info(f"Unsupported operating system: {system}")
