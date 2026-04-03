"""Register / unregister the News Clipping Tool as a Windows startup task.

Usage:
    python setup_autostart.py install     # Create scheduled task (runs at logon)
    python setup_autostart.py uninstall   # Remove the scheduled task
    python setup_autostart.py status      # Check if the task exists
"""

from __future__ import annotations

import os
import subprocess
import sys

TASK_NAME = "NewsClippingTool"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_SCRIPT = os.path.join(SCRIPT_DIR, "main.py")


def _find_pythonw() -> str:
    """Return the path to pythonw.exe (windowless Python) next to the current
    interpreter, falling back to python.exe if not found."""
    base = os.path.dirname(sys.executable)
    pythonw = os.path.join(base, "pythonw.exe")
    if os.path.isfile(pythonw):
        return pythonw
    return sys.executable


def install() -> None:
    """Create a Windows Task Scheduler task that runs at user logon."""
    pythonw = _find_pythonw()

    # Remove existing task first (ignore errors)
    subprocess.run(
        ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
        capture_output=True,
    )

    result = subprocess.run(
        [
            "schtasks", "/Create",
            "/TN", TASK_NAME,
            "/TR", f'"{pythonw}" "{MAIN_SCRIPT}"',
            "/SC", "ONLOGON",
            "/RL", "LIMITED",
            "/F",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print(f"[OK] Task '{TASK_NAME}' created. The tool will start at next logon.")
        print(f"     Executable: {pythonw}")
        print(f"     Script:     {MAIN_SCRIPT}")
    else:
        print(f"[ERROR] Failed to create task:\n{result.stderr}")
        sys.exit(1)


def uninstall() -> None:
    """Remove the Windows Task Scheduler task."""
    result = subprocess.run(
        ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print(f"[OK] Task '{TASK_NAME}' removed.")
    else:
        print(f"[WARN] Task may not exist:\n{result.stderr}")


def status() -> None:
    """Check whether the task is registered."""
    result = subprocess.run(
        ["schtasks", "/Query", "/TN", TASK_NAME],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print(f"[OK] Task '{TASK_NAME}' is registered:")
        print(result.stdout)
    else:
        print(f"[INFO] Task '{TASK_NAME}' is NOT registered.")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1].lower()
    if cmd == "install":
        install()
    elif cmd == "uninstall":
        uninstall()
    elif cmd == "status":
        status()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
