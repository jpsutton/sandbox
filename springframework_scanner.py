#!/usr/bin/env python

import os
import sys
import platform
import tempfile
from zipfile import ZipFile

if platform.system() == "Windows":
    import win32api, win32con, win32process
    import wmi


def lower_priority():
    pid = win32api.GetCurrentProcessId()
    handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, True, pid)
    win32process.SetPriorityClass(handle, win32process.BELOW_NORMAL_PRIORITY_CLASS)


# Generate a list of files by walking recursively down a path
def walk_tree(path):
    for root, d_names, f_names in os.walk(path):
        for f in f_names:
            yield os.path.join(root, f).lower()


def main(root_tmpdir):
    if platform.system() == "Windows":
        c = wmi.WMI()
        drives = [f"{drive.Caption}\\" for drive in c.Win32_LogicalDisk(DriveType=3)]
    else:
        drives = ["/"]

    for drive in drives:
        print(f"scanning {drive}")
        for file in walk_tree(drive):
            if file.endswith(".jar") or file.endswith(".war"):
                if "spring" in file or "debug" in sys.argv:
                    print(file)
                    continue
                else:
                    try:
                        with ZipFile(file, 'r') as zipObj:
                            for item in zipObj.namelist():
                                item = item.lower()

                                if "springframework" in item:
                                    print(f"{file}::{item}")
                    except:
                        pass

                    # with tempfile.TemporaryDirectory(dir=root_tmpdir) as unpack_tmpdir:


if __name__ == '__main__':
    if platform.system() == "Windows":
        lower_priority()

    with tempfile.TemporaryDirectory() as tmpdir:
        main(tmpdir)
        
