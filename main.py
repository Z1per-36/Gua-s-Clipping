"""News Clipping Tool — entry point.

Starts the scheduler and system tray icon for background operation.
"""

from __future__ import annotations

import sys
import os

# Ensure the project root is on sys.path so relative imports work
# regardless of CWD.
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from config_manager import load_config
from scheduler import NewsScheduler
from settings_gui import SettingsGUI
from tray_app import TrayApp
from utils import log


def _send_ipc_message(msg: str):
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", 49152))
        s.sendall(msg.encode('utf-8'))
        s.close()
    except Exception:
        pass


def main() -> None:
    import socket
    import threading
    import subprocess
    
    # 1. Try to become Master
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    is_master = False
    try:
        s.bind(("127.0.0.1", 49152))
        s.listen(1)
        is_master = True
    except OSError:
        pass # Port in use, we are client

    if not is_master:
        # We are Client: Background agent is running. We just show GUI and send save event.
        log.info("Agent is already running. Operating in UI-only mode.")
        gui = SettingsGUI(on_save_callback=lambda cfg: _send_ipc_message("RELOAD_CONFIG"))
        gui.show()
        sys.exit(0)

    # 2. We are Master
    log.info("======== News Clipping Tool Background Agent starting ========")
    cfg = load_config()
    scheduler = NewsScheduler()
    scheduler.start(cfg)

    # IPC Listener Thread
    def _ipc_listener():
        while True:
            try:
                conn, _ = s.accept()
                data = conn.recv(1024).decode('utf-8')
                conn.close()
                if data == "RELOAD_CONFIG":
                    log.info("IPC: Received RELOAD_CONFIG")
                    scheduler.reload(load_config())
                elif data == "TRIGGER_NOW":
                    log.info("IPC: Received TRIGGER_NOW")
                    scheduler.trigger_now()
            except Exception:
                pass
                
    t = threading.Thread(target=_ipc_listener, daemon=True)
    t.start()

    def _open_settings_via_subprocess():
        # Spawn ourselves to enter UI mode safely on any OS
        if getattr(sys, 'frozen', False):
            subprocess.Popen([sys.executable])
        else:
            subprocess.Popen([sys.executable, os.path.abspath(sys.argv[0])])

    # First run check
    if not cfg.get("keywords") and len(cfg.get("categories", [])) <= 1:
        log.info("Assuming first launch. Auto-opening Settings GUI via subprocess.")
        _open_settings_via_subprocess()

    # --- System tray (blocks main thread) ---
    tray = TrayApp(
        on_trigger_now=lambda: scheduler.trigger_now(),
        on_open_settings=_open_settings_via_subprocess,
        on_quit=lambda: None,
        get_next_run=lambda: scheduler.next_run,
    )

    try:
        tray.run()  # Blocks here cleanly
    except KeyboardInterrupt:
        pass
    finally:
        scheduler.stop()
        log.info("======== News Clipping Tool stopped ========")


if __name__ == "__main__":
    main()
