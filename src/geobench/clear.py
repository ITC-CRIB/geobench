import ctypes
import os
import platform
import shutil
import sys

from subprocess import check_call


def clear_linux_cache():
    try:
        os.system('sync; echo 3 > /proc/sys/vm/drop_caches')
        print("Cleared disk and memory cache on Linux.")
    except Exception as e:
        print(f"Failed to clear cache on Linux: {e}")


def clear_windows_memory_cache():
    try:
        ctypes.windll.psapi.EmptyWorkingSet(-1)
        print("Cleared memory cache on Windows.")
    except Exception as e:
        print(f"Failed to clear memory cache on Windows: {e}")


def _clear_temp_files():
    temp_dirs = [os.getenv('TEMP'), os.path.join(os.getenv('WINDIR'), 'Temp')]
    for temp_dir in temp_dirs:
        print(f"Clearing temporary files in {temp_dir}...")
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
            print(f"Temporary files in {temp_dir} cleared.")
        except Exception as e:
            print(f"Failed to clear temporary files in {temp_dir}. Error: {e}")


def _clear_windows_update_cache():
    windows_update_cache = os.path.join(os.getenv('WINDIR'), 'SoftwareDistribution', 'Download')
    print("Clearing Windows Update cache...")
    try:
        check_call(["net", "stop", "wuauserv"])
        shutil.rmtree(windows_update_cache)
        os.mkdir(windows_update_cache)
        check_call(["net", "start", "wuauserv"])
        print("Windows Update cache cleared.")
    except Exception as e:
        print(f"Failed to clear Windows Update cache. Error: {e}")


def clear_windows_disk_cache():
    if ctypes.windll.shell32.IsUserAnAdmin():
        print("Clearing system cache...")
        _clear_temp_files()
        _clear_windows_update_cache()
        print("System cache cleared.")
    else:
        print("This script needs to be run as an administrator.")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)


def clear_cache():
    os_type = platform.system()

    if os_type == 'Linux':
        clear_linux_cache()
    elif os_type == 'Windows':
        clear_windows_memory_cache()
        clear_windows_disk_cache()
    else:
        print(f"Unsupported operating system: {os_type}")
