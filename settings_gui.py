"""Simple Settings GUI — User friendly interface for configuring News Clipping Tool."""

from __future__ import annotations

import ctypes
import os
import sys
import winreg
from typing import Any

import customtkinter as ctk
from customtkinter import filedialog
from tkinter import messagebox
import tkinter as tk

from config_manager import load_config, save_config
from utils import PRESET_CATEGORIES, log, t

# Resolve blurry rendering on high-DPI displays (Windows)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def _set_autostart(enable: bool) -> None:
    import platform
    sys_os = platform.system()
    app_name = "NewsClippingTool"
    if getattr(sys, 'frozen', False):
        exe_path = f'"{sys.executable}"'
    else:
        exe_path = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
        
    if sys_os == "Windows":
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            if enable:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception:
            pass
    elif sys_os == "Darwin":
        import plistlib
        plist_path = os.path.expanduser(f"~/Library/LaunchAgents/com.{app_name}.plist")
        if enable:
            plist = {
                "Label": f"com.{app_name}",
                "ProgramArguments": [sys.executable] if getattr(sys, 'frozen', False) else [sys.executable, os.path.abspath(sys.argv[0])],
                "RunAtLoad": True
            }
            try:
                os.makedirs(os.path.dirname(plist_path), exist_ok=True)
                with open(plist_path, "wb") as f:
                    plistlib.dump(plist, f)
            except Exception:
                pass
        else:
            if os.path.exists(plist_path):
                try:
                    os.remove(plist_path)
                except Exception:
                    pass


import calendar
from datetime import datetime, date

class CTkDatePicker(ctk.CTkToplevel):
    def __init__(self, parent, current_date: date, callback):
        super().__init__(parent)
        self.callback = callback
        self.current_date = current_date
        self.display_year = current_date.year
        self.display_month = current_date.month
        
        self.title("📅")
        self.geometry("260x300")
        self.resizable(False, False)
        self.attributes('-topmost', True)
        self.grab_set() 
        
        self._build_ui()
        
    def _build_ui(self):
        for widget in self.winfo_children():
            widget.destroy()
            
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(header_frame, text="<", width=30, hover_color="#E74C3C", command=self._prev_month).pack(side="left")
        month_year_str = f"{self.display_year} - {self.display_month:02d}"
        ctk.CTkLabel(header_frame, text=month_year_str, font=("Arial", 16, "bold")).pack(side="left", expand=True)
        ctk.CTkButton(header_frame, text=">", width=30, hover_color="#E74C3C", command=self._next_month).pack(side="right")
        
        grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        days = ["M", "T", "W", "T", "F", "S", "S"]
        for i, d in enumerate(days):
            ctk.CTkLabel(grid_frame, text=d, font=("Arial", 12, "bold"), text_color="gray").grid(row=0, column=i, padx=5, pady=3)
            
        cal = calendar.monthcalendar(self.display_year, self.display_month)
        for row_idx, week in enumerate(cal):
            for col_idx, day in enumerate(week):
                if day != 0:
                    is_today = (day == self.current_date.day and self.display_month == self.current_date.month and self.display_year == self.current_date.year)
                    fg = "#1F6AA5" if is_today else ("gray75", "gray25")
                    text_col = "white" if is_today else ("black", "white")
                    
                    btn = ctk.CTkButton(
                        grid_frame, text=str(day), width=28, height=28,
                        corner_radius=14, fg_color=fg, text_color=text_col,
                        hover_color="#3498DB",
                        command=lambda d=day: self._on_date_select(d)
                    )
                    btn.grid(row=row_idx+1, column=col_idx, padx=3, pady=3)

    def _prev_month(self):
        self.display_month -= 1
        if self.display_month < 1:
            self.display_month = 12
            self.display_year -= 1
        self._build_ui()
        
    def _next_month(self):
        self.display_month += 1
        if self.display_month > 12:
            self.display_month = 1
            self.display_year += 1
        self._build_ui()
        
    def _on_date_select(self, day):
        selected = date(self.display_year, self.display_month, day)
        self.callback(selected)
        self.destroy()

class SettingsGUI:
    """A simplified, beautifully designed settings dashboard."""

    def __init__(self, on_save_callback: Any = None) -> None:
        self._on_save = on_save_callback
        self._cfg = {} # Loaded in show()
        self._root: ctk.CTk | None = None
        self._scheduled_times: set[str] = set()
        self._lang = "zh"

    def show(self) -> None:
        if self._root is not None:
            self._root.lift()
            return

        self._cfg = load_config()
        self._lang = self._cfg.get("language", "zh")
        self._scheduled_times = set(self._cfg.get("schedule", {}).get("send_times", ["08:00"]))
        
        # Configure CTk
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        
        self._root = ctk.CTk()
        self._root.title(t("ui_title", self._lang))
        
        window_width = 620
        window_height = 600
        screen_width = self._root.winfo_screenwidth()
        screen_height = self._root.winfo_screenheight()
        pos_x = (screen_width // 2) - (window_width // 2)
        pos_y = (screen_height // 2) - (window_height // 2)
        
        self._root.geometry(f"{window_width}x{window_height}+{pos_x}+{pos_y}")
        self._root.resizable(True, True)
        self._root.minsize(550, 500)

        # Fix: pack btn_frame bottom first so it never gets cropped out!
        self._btn_frame = ctk.CTkFrame(self._root, fg_color="transparent")
        self._btn_frame.pack(fill="x", side="bottom", padx=20, pady=(0, 20))

        # Main scrollable canvas takes the rest
        main_frame = ctk.CTkScrollableFrame(self._root, corner_radius=0, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=(20, 0))

        # Title
        title_lbl = ctk.CTkLabel(main_frame, text=t("ui_header", self._lang), font=("Microsoft JhengHei", 24, "bold"))
        title_lbl.pack(anchor="w", pady=(0, 20))

        # ==========================================
        # 1. System Settings Section (Card)
        # ==========================================
        sys_card = ctk.CTkFrame(main_frame, corner_radius=15, fg_color=("gray95", "gray17"))
        sys_card.pack(fill="x", pady=(0, 20), ipadx=10, ipady=10)
        
        ctk.CTkLabel(sys_card, text=t("sys_settings", self._lang), font=("Microsoft JhengHei", 18, "bold")).pack(anchor="w", padx=15, pady=(15, 10))

        # Language dropdown
        lang_frame = ctk.CTkFrame(sys_card, fg_color="transparent")
        lang_frame.pack(fill="x", padx=15, pady=(5, 15))
        ctk.CTkLabel(lang_frame, text=t("language_lbl", self._lang), font=("Microsoft JhengHei", 14)).pack(side="left")
        self._lang_var = ctk.StringVar(value="繁體中文" if self._lang == "zh" else "English")
        lang_cb = ctk.CTkComboBox(lang_frame, values=["繁體中文", "English"], variable=self._lang_var, state="readonly", command=self._on_lang_change)
        lang_cb.pack(side="left", padx=10)

        # Autostart
        self._autostart_var = tk.BooleanVar(value=self._cfg.get("autostart", False))
        ctk.CTkCheckBox(sys_card, text=t("autostart", self._lang), variable=self._autostart_var, font=("Microsoft JhengHei", 14, "bold")).pack(anchor="w", padx=15, pady=(0, 15))

        # Output Directory
        ctk.CTkLabel(sys_card, text=t("output_dir", self._lang), font=("Microsoft JhengHei", 14)).pack(anchor="w", padx=15)
        
        dir_frame = ctk.CTkFrame(sys_card, fg_color="transparent")
        dir_frame.pack(fill="x", padx=15, pady=(5, 10))
        
        default_dir = self._cfg.get("output_dir")
        if not default_dir:
             default_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        self._output_dir_var = ctk.StringVar(value=default_dir)
        
        dir_entry = ctk.CTkEntry(dir_frame, textvariable=self._output_dir_var, font=("Arial", 13), state="readonly")
        dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        ctk.CTkButton(dir_frame, text=t("browse", self._lang), width=80, command=self._choose_directory).pack(side="right")

        # ==========================================
        # 2. Schedule Section
        # ==========================================
        time_card = ctk.CTkFrame(main_frame, corner_radius=15, fg_color=("gray95", "gray17"))
        time_card.pack(fill="x", pady=(0, 20), ipadx=10, ipady=10)
        
        ctk.CTkLabel(time_card, text=t("schedule_title", self._lang), font=("Microsoft JhengHei", 18, "bold")).pack(anchor="w", padx=15, pady=(15, 10))
        ctk.CTkLabel(time_card, text=t("schedule_sub", self._lang), font=("Microsoft JhengHei", 13), text_color="gray").pack(anchor="w", padx=15, pady=(0, 15))
        
        # Time adder
        adder_frame = ctk.CTkFrame(time_card, fg_color="transparent")
        adder_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        self.hr_var = ctk.StringVar(value="08")
        hr_cb = ctk.CTkComboBox(adder_frame, values=[f"{i:02d}" for i in range(24)], variable=self.hr_var, width=80, font=("Arial", 14), state="readonly")
        hr_cb.pack(side="left")
        
        ctk.CTkLabel(adder_frame, text=" : ", font=("Arial", 16, "bold")).pack(side="left", padx=5)
        
        self.mn_var = ctk.StringVar(value="00")
        mn_cb = ctk.CTkComboBox(adder_frame, values=["00", "15", "30", "45"], variable=self.mn_var, width=80, font=("Arial", 14), state="readonly")
        mn_cb.pack(side="left")
        
        add_btn = ctk.CTkButton(adder_frame, text=t("add_time", self._lang), width=100, font=("Microsoft JhengHei", 14, "bold"), command=self._add_time)
        add_btn.pack(side="left", padx=(15, 0))

        # Selected times display (Container)
        self.time_pills_frame = ctk.CTkFrame(time_card, fg_color="transparent")
        self.time_pills_frame.pack(fill="x", padx=15, pady=(0, 10))
        self._refresh_time_pills()

        # ==========================================
        # 2.5 Date Range Section
        # ==========================================
        date_card = ctk.CTkFrame(main_frame, corner_radius=15, fg_color=("gray95", "gray17"))
        date_card.pack(fill="x", pady=(0, 20), ipadx=10, ipady=10)
        
        ctk.CTkLabel(date_card, text=t("date_filter_title", self._lang), font=("Microsoft JhengHei", 18, "bold")).pack(anchor="w", padx=15, pady=(15, 10))
        
        date_cfg = self._cfg.get("date_range", {})
        self._date_enabled_var = tk.BooleanVar(value=date_cfg.get("enabled", False))
        
        def _parse_dt(s):
            try:
                return datetime.strptime(s, "%Y-%m-%d").date()
            except:
                return datetime.now().date()
                
        self.start_dt = _parse_dt(date_cfg.get("start", ""))
        self.end_dt = _parse_dt(date_cfg.get("end", ""))
        
        def _set_start(d):
            self.start_dt = d
            self.start_btn.configure(text=f"📅 {self.start_dt.strftime('%Y-%m-%d')}")
            
        def _set_end(d):
            self.end_dt = d
            self.end_btn.configure(text=f"📅 {self.end_dt.strftime('%Y-%m-%d')}")
        
        def _toggle_date_state(*args):
            state = "normal" if self._date_enabled_var.get() else "disabled"
            self.start_btn.configure(state=state)
            self.end_btn.configure(state=state)

        ctk.CTkCheckBox(date_card, text=t("date_filter_enable", self._lang), variable=self._date_enabled_var, font=("Microsoft JhengHei", 14), command=_toggle_date_state).pack(anchor="w", padx=15, pady=(0, 15))

        date_inner_frame = ctk.CTkFrame(date_card, fg_color="transparent")
        date_inner_frame.pack(fill="x", padx=15, pady=(0, 5))

        ctk.CTkLabel(date_inner_frame, text=t("start_date", self._lang), font=("Microsoft JhengHei", 14)).pack(side="left", padx=(0, 10))
        
        self.start_btn = ctk.CTkButton(date_inner_frame, text=f"📅 {self.start_dt.strftime('%Y-%m-%d')}", width=120, command=lambda: CTkDatePicker(self._root, self.start_dt, _set_start))
        self.start_btn.pack(side="left", padx=(0, 25))

        ctk.CTkLabel(date_inner_frame, text=t("end_date", self._lang), font=("Microsoft JhengHei", 14)).pack(side="left", padx=(0, 10))
        
        self.end_btn = ctk.CTkButton(date_inner_frame, text=f"📅 {self.end_dt.strftime('%Y-%m-%d')}", width=120, command=lambda: CTkDatePicker(self._root, self.end_dt, _set_end))
        self.end_btn.pack(side="left")

        _toggle_date_state()

        # ==========================================
        # 3. Content Section
        # ==========================================
        content_card = ctk.CTkFrame(main_frame, corner_radius=15, fg_color=("gray95", "gray17"))
        content_card.pack(fill="x", pady=(0, 20), ipadx=10, ipady=10)
        
        ctk.CTkLabel(content_card, text=t("content_title", self._lang), font=("Microsoft JhengHei", 18, "bold")).pack(anchor="w", padx=15, pady=(15, 10))
        
        # Categories
        cat_inner_frame = ctk.CTkFrame(content_card, fg_color="transparent")
        cat_inner_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        saved_cats = self._cfg.get("categories", [])
        self._cat_vars = {}
        
        row, col = 0, 0
        for display, value in PRESET_CATEGORIES:
            display_name = display if self._lang == "zh" else display.split(" ")[1]
            if self._lang == "zh":
                 display_name = display.split(" ")[0]
            var = tk.BooleanVar(value=value in saved_cats)
            self._cat_vars[value] = var
            cb = ctk.CTkCheckBox(cat_inner_frame, text=display_name, variable=var, font=("Microsoft JhengHei", 14))
            cb.grid(row=row, column=col, sticky="w", padx=(0, 25), pady=8)
            col += 1
            if col > 3:
                col = 0
                row += 1

        # Keywords
        ctk.CTkLabel(content_card, text=t("keywords_lbl", self._lang), font=("Microsoft JhengHei", 14)).pack(anchor="w", padx=15, pady=(10, 5))
        keywords = self._cfg.get("keywords", [])
        self._kw_var = ctk.StringVar(value=", ".join(keywords))
        ctk.CTkEntry(content_card, textvariable=self._kw_var, width=450, font=("Arial", 14), height=35).pack(anchor="w", padx=15, pady=(0, 15))

        # ==========================================
        # Bottom Buttons
        # ==========================================
        save_btn = ctk.CTkButton(
            self._btn_frame, 
            text=t("btn_save", self._lang), 
            font=("Microsoft JhengHei", 16, "bold"),
            height=45,
            corner_radius=8,
            command=self._save_and_close
        )
        save_btn.pack(side="right", padx=(10, 0))
        
        cancel_btn = ctk.CTkButton(
            self._btn_frame, 
            text=t("btn_cancel", self._lang), 
            font=("Microsoft JhengHei", 15),
            fg_color="transparent",
            border_width=2,
            text_color=("gray10", "gray90"),
            height=45,
            corner_radius=8,
            command=self._root.destroy
        )
        cancel_btn.pack(side="right")

        self._root.protocol("WM_DELETE_WINDOW", self._root.destroy)
        self._root.lift()
        self._root.attributes('-topmost', True)
        self._root.after_idle(self._root.attributes, '-topmost', False)
        
        self._root.mainloop()

    # --- Time Editor Logic ---
    def _choose_directory(self) -> None:
        folder = filedialog.askdirectory(initialdir=self._output_dir_var.get(), parent=self._root, title="Select Dir")
        if folder:
            self._output_dir_var.set(os.path.normpath(folder))

    def _add_time(self) -> None:
        hr = self.hr_var.get()
        mn = self.mn_var.get()
        time_str = f"{hr}:{mn}"
        if time_str not in self._scheduled_times:
            self._scheduled_times.add(time_str)
            self._refresh_time_pills()
            
    def _remove_time(self, time_str: str) -> None:
        if time_str in self._scheduled_times:
            self._scheduled_times.remove(time_str)
            self._refresh_time_pills()

    def _refresh_time_pills(self) -> None:
        """Render selected times as little pill buttons."""
        for widget in self.time_pills_frame.winfo_children():
            widget.destroy()

        if not self._scheduled_times:
            ctk.CTkLabel(self.time_pills_frame, text=t("no_time", self._lang), text_color="gray", font=("Microsoft JhengHei", 12)).pack(anchor="w")
            return

        sorted_times = sorted(list(self._scheduled_times))
        for t_val in sorted_times:
            btn = ctk.CTkButton(
                self.time_pills_frame,
                text=f"{t_val} ✕",
                width=60,
                height=28,
                corner_radius=14,
                fg_color="#34495E",
                hover_color="#E74C3C",
                font=("Arial", 12, "bold"),
                command=lambda val=t_val: self._remove_time(val)
            )
            btn.pack(side="left", padx=(0, 10), pady=5)

    def _on_lang_change(self, choice: str) -> None:
        new_lang = "zh" if choice == "繁體中文" else "en"
        if new_lang != self._lang:
             self._cfg["language"] = new_lang
             # Reload the UI softly
             self._root.destroy()
             self._root = None
             save_config(self._cfg)
             self.show()

    # --- Save Logic ---
    def _save_and_close(self) -> None:
        if not self._scheduled_times:
            messagebox.showwarning("Warning", t("warn_time", self._lang), parent=self._root)
            return
            
        # Write config
        if "schedule" not in self._cfg:
            self._cfg["schedule"] = {}
        self._cfg["schedule"]["send_times"] = sorted(list(self._scheduled_times))

        self._cfg["categories"] = [val for val, var in self._cat_vars.items() if var.get()]

        kw_text = self._kw_var.get().strip()
        if kw_text:
            self._cfg["keywords"] = [k.strip() for k in kw_text.split(",") if k.strip()]
        else:
            self._cfg["keywords"] = []

        if "sources" not in self._cfg:
             self._cfg["sources"] = {}
        if "google_news" not in self._cfg["sources"]:
             self._cfg["sources"]["google_news"] = {"enabled": True, "language": "zh-TW", "region": "TW"}
             
        self._cfg["output_dir"] = self._output_dir_var.get()
        autostart_enabled = self._autostart_var.get()
        self._cfg["autostart"] = autostart_enabled
        
        self._cfg["date_range"] = {
            "enabled": self._date_enabled_var.get(),
            "start": self.start_dt.strftime("%Y-%m-%d"),
            "end": self.end_dt.strftime("%Y-%m-%d")
        }
        
        save_config(self._cfg)
        _set_autostart(autostart_enabled)
        
        log.info("Settings saved via CustomTkinter GUI")

        if self._on_save:
            self._on_save(self._cfg)

        messagebox.showinfo(t("save_title", self._lang), t("save_success", self._lang), parent=self._root)
        
        if self._root:
            self._root.destroy()
            self._root = None
