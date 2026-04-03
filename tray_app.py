"""System tray application — provides background presence and quick actions."""

from __future__ import annotations

import threading
from typing import Any, Callable

from PIL import Image, ImageDraw, ImageFont
import pystray

from utils import log


def _create_icon_image() -> Image.Image:
    """Programmatically draw a small newspaper icon (no external file needed)."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded background
    draw.rounded_rectangle([4, 4, 60, 60], radius=10, fill="#302b63")

    # "N" letter
    try:
        font = ImageFont.truetype("arial.ttf", 34)
    except OSError:
        font = ImageFont.load_default()
    draw.text((17, 10), "N", fill="white", font=font)

    # Small underline bar
    draw.rounded_rectangle([16, 48, 48, 52], radius=2, fill="#6c63ff")

    return img


class TrayApp:
    """System tray icon with menu for controlling the News Clipping Tool."""

    def __init__(
        self,
        *,
        on_trigger_now: Callable[[], None],
        on_open_settings: Callable[[], None],
        on_quit: Callable[[], None],
        get_next_run: Callable[[], str | None],
    ) -> None:
        self._on_trigger_now = on_trigger_now
        self._on_open_settings = on_open_settings
        self._on_quit = on_quit
        self._get_next_run = get_next_run
        self._icon: pystray.Icon | None = None

    def run(self) -> None:
        """Create and run the tray icon (blocks the calling thread)."""
        icon_image = _create_icon_image()
        self._icon = pystray.Icon(
            name="NewsClipping",
            icon=icon_image,
            title="News Clipping Tool",
            menu=self._build_menu(),
        )
        log.info("System tray icon started")
        self._icon.run()

    def stop(self) -> None:
        if self._icon is not None:
            self._icon.stop()

    # ------------------------------------------------------------------

    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem("News Clipping Tool", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda _: self._next_run_label(),
                None,
                enabled=False,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("立即擷取並寄送", self._handle_trigger),
            pystray.MenuItem("開啟設定", self._handle_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("結束", self._handle_quit),
        )

    def _next_run_label(self) -> str:
        nxt = self._get_next_run()
        if nxt:
            return f"Next: {nxt}"
        return "No scheduled runs"

    def _handle_trigger(self, icon: Any, item: Any) -> None:
        log.info("Tray: manual trigger")
        t = threading.Thread(target=self._on_trigger_now, daemon=True)
        t.start()

    def _handle_settings(self, icon: Any, item: Any) -> None:
        log.info("Tray: open settings")
        t = threading.Thread(target=self._on_open_settings, daemon=True)
        t.start()

    def _handle_quit(self, icon: Any, item: Any) -> None:
        log.info("Tray: quit requested")
        self._on_quit()
        self.stop()
