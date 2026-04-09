# encoding: utf-8
"""
@author:  liaoxingyu
@contact: sherlockliao01@gmail.com
"""


def compile_helper():
    """Compile helper function at runtime. Make sure this
    is invoked on a single process."""
    import os
    import subprocess
    import sys

    path = os.path.abspath(os.path.dirname(__file__))
    commands = []
    if os.name == "nt":
        commands.append([sys.executable, "setup.py", "build_ext", "--inplace"])
    else:
        commands.append(["make", "-C", path])
        commands.append([sys.executable, "setup.py", "build_ext", "--inplace"])

    for command in commands:
        try:
            ret = subprocess.run(
                command,
                cwd=path,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            continue
        if ret.returncode == 0:
            return True

    print("Warning: failed to build cython reid evaluation module, fallback to python evaluation.")
    return False
