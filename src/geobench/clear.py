import ctypes
import os
import platform
import shutil

from subprocess import check_call


import logging
logger = logging.getLogger(__name__)


def clear_linux_cache():
    try:
        os.system('sync; echo 3 > /proc/sys/vm/drop_caches')
        logger.info("Cleared disk and memory cache on Linux.")

    except Exception as err:
        logger.info(f"Failed to clear cache on Linux: {err}.")


def clear_windows_memory_cache():
    try:
        ctypes.windll.psapi.EmptyWorkingSet(-1)
        logger.info("Cleared memory cache on Windows.")

    except Exception as err:
        logger.info(f"Failed to clear memory cache on Windows: {err}")


def _clear_temp_files():
    temp_dirs = [os.getenv('TEMP'), os.path.join(os.getenv('WINDIR'), 'Temp')]

    for temp_dir in temp_dirs:
        logger.info(f"Clearing temporary files in {temp_dir}...")

        try:
            for root, dirs, files in os.walk(temp_dir):

                for name in files:
                    file_path = os.path.join(root, name)
                    try:
                        os.remove(file_path)
                    except PermissionError:
                        pass

                for name in dirs:
                    dir_path = os.path.join(root, name)
                    try:
                        shutil.rmtree(dir_path)
                    except PermissionError:
                        pass

            logger.info(f"Temporary files in {temp_dir} cleared.")

        except Exception as err:
            logger.info(f"Failed to clear temporary files in {temp_dir}: {err}")


def _clear_windows_update_cache():
    windows_update_cache = os.path.join(os.getenv('WINDIR'), 'SoftwareDistribution', 'Download')
    logger.info("Clearing Windows Update cache...")
    try:
        check_call(["net", "stop", "wuauserv"])
        shutil.rmtree(windows_update_cache)
        os.mkdir(windows_update_cache)
        check_call(["net", "start", "wuauserv"])
        logger.info("Windows Update cache cleared.")

    except Exception as err:
        logger.info(f"Failed to clear Windows Update cache: {err}")


def clear_windows_disk_cache():
    if ctypes.windll.shell32.IsUserAnAdmin():
        logger.info("Clearing system cache...")
        _clear_temp_files()
        _clear_windows_update_cache()
        logger.info("System cache cleared.")

    else:
        logger.info("Clearing system cache needs administrator rights, skipping.")


def clear_cache():
    os_type = platform.system()

    if os_type == 'Linux':
        clear_linux_cache()

    elif os_type == 'Windows':
        clear_windows_memory_cache()
        clear_windows_disk_cache()

    else:
        logger.info(f"Unsupported operating system: {os_type}")
