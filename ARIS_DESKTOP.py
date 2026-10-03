"""A.R.I.S. desktop window with a Windows tray icon and Ctrl+Alt+Space hotkey."""
from __future__ import annotations

import ctypes
import importlib.util
import queue
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk
from pathlib import Path
from typing import Any
import webbrowser

CORE_PATH = Path(__file__).with_name("A.R.I.S.py")
spec = importlib.util.spec_from_file_location("aris_core", CORE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load ARIS core from {CORE_PATH}")
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
ARIS = core.ARIS


class TrayHotkey:
    """Small dependency-free Win32 tray icon and global hotkey host."""

    def __init__(self, events: queue.Queue[tuple[str, Any]]) -> None:
        self.events = events
        self.thread: threading.Thread | None = None
        self.ready = threading.Event()
        self.error: str | None = None
        self.hwnd = None
        self._callback = None

    def start(self) -> bool:
        if __import__("os").name != "nt":
            self.error = "The tray icon and global hotkey are Windows-only."
            return False
        self.thread = threading.Thread(target=self._run, name="ARIS-tray", daemon=True)
        self.thread.start()
        self.ready.wait(5)
        return self.error is None and self.hwnd is not None

    def _run(self) -> None:
        try:
            self._win32_loop()
        except Exception as exc:
            self.error = str(exc)
            self.ready.set()
            self.events.put(("status", f"Tray/hotkey unavailable: {exc}"))

    def _win32_loop(self) -> None:
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        shell32 = ctypes.windll.shell32
        kernel32 = ctypes.windll.kernel32
        CALLBACK = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

        class WNDCLASSW(ctypes.Structure):
            _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", CALLBACK),
                        ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                        ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON),
                        ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HANDLE),
                        ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR)]

        class NOTIFYICONDATAW(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.DWORD), ("hWnd", wintypes.HWND), ("uID", wintypes.UINT),
                        ("uFlags", wintypes.UINT), ("uCallbackMessage", wintypes.UINT),
                        ("hIcon", wintypes.HICON), ("szTip", wintypes.WCHAR * 128)]

        class POINT(ctypes.Structure):
            _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

        user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
        user32.RegisterClassW.restype = wintypes.ATOM
        user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
                                           ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                           wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID]
        user32.CreateWindowExW.restype = wintypes.HWND
        user32.LoadIconW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR]
        user32.LoadIconW.restype = wintypes.HICON
        user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        user32.DefWindowProcW.restype = ctypes.c_ssize_t
        user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        user32.RegisterHotKey.restype = wintypes.BOOL
        user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
        user32.GetMessageW.restype = ctypes.c_int
        user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
        user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
        user32.PostQuitMessage.argtypes = [ctypes.c_int]
        user32.DestroyWindow.argtypes = [wintypes.HWND]
        user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        user32.PostMessageW.restype = wintypes.BOOL
        user32.CreatePopupMenu.restype = wintypes.HMENU
        user32.AppendMenuW.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_size_t, wintypes.LPCWSTR]
        user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
        user32.SetForegroundWindow.argtypes = [wintypes.HWND]
        user32.TrackPopupMenu.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_int, ctypes.c_int,
                                          ctypes.c_int, wintypes.HWND, wintypes.LPVOID]
        user32.TrackPopupMenu.restype = wintypes.UINT
        user32.DestroyMenu.argtypes = [wintypes.HMENU]
        shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.c_void_p]
        shell32.Shell_NotifyIconW.restype = wintypes.BOOL
        kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        kernel32.GetModuleHandleW.restype = wintypes.HMODULE

        class_name = "ARIS_TrayHost_Window"
        message_tray = 0x8000 + 17
        WM_HOTKEY, WM_CLOSE, WM_DESTROY = 0x0312, 0x0010, 0x0002
        WM_LBUTTONDBLCLK, WM_RBUTTONUP = 0x0203, 0x0205
        NIM_ADD, NIM_DELETE, NIF_MESSAGE, NIF_ICON, NIF_TIP = 0, 2, 1, 2, 4
        MOD_ALT, MOD_CONTROL, MOD_NOREPEAT, VK_SPACE = 0x0001, 0x0002, 0x4000, 0x20
        hinstance = kernel32.GetModuleHandleW(None)

        def wndproc(hwnd: int, msg: int, wparam: int, lparam: int) -> int:
            if msg == WM_HOTKEY:
                self.events.put(("show", None))
                return 0
            if msg == message_tray:
                if lparam == WM_LBUTTONDBLCLK:
                    self.events.put(("show", None))
                elif lparam == WM_RBUTTONUP:
                    menu = user32.CreatePopupMenu()
                    user32.AppendMenuW(menu, 0, 1, "Show ARIS")
                    user32.AppendMenuW(menu, 0, 2, "Exit ARIS")
                    point = POINT()
                    user32.GetCursorPos(ctypes.byref(point))
                    user32.SetForegroundWindow(hwnd)
                    selected = user32.TrackPopupMenu(menu, 0x0100, point.x, point.y, 0, hwnd, None)
                    user32.DestroyMenu(menu)
                    if selected == 1:
                        self.events.put(("show", None))
                    elif selected == 2:
                        self.events.put(("exit", None))
                return 0
            if msg == WM_CLOSE:
                user32.DestroyWindow(hwnd)
                return 0
            if msg == WM_DESTROY:
                user32.PostQuitMessage(0)
                return 0
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        self._callback = CALLBACK(wndproc)
        window_class = WNDCLASSW()
        window_class.lpfnWndProc = self._callback
        window_class.hInstance = hinstance
        window_class.lpszClassName = class_name
        if not user32.RegisterClassW(ctypes.byref(window_class)):
            error = ctypes.get_last_error()
            if error != 1410:  # ERROR_CLASS_ALREADY_EXISTS
                raise ctypes.WinError(error)
        hwnd = user32.CreateWindowExW(0, class_name, "ARIS tray host", 0, 0, 0, 0, 0, None, None, hinstance, None)
        if not hwnd:
            raise ctypes.WinError(ctypes.get_last_error())
        self.hwnd = hwnd
        icon_id = ctypes.cast(ctypes.c_void_p(32512), wintypes.LPCWSTR)  # IDI_APPLICATION
        icon = user32.LoadIconW(None, icon_id)
        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(nid)
        nid.hWnd = hwnd
        nid.uID = 1
        nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = message_tray
        nid.hIcon = icon
        nid.szTip = "A.R.I.S assistant"
        if not shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid)):
            raise ctypes.WinError(ctypes.get_last_error())
        if not user32.RegisterHotKey(hwnd, 1, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_SPACE):
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))
            raise RuntimeError("Could not register Ctrl+Alt+Space; another app may be using it.")
        self.ready.set()
        message = wintypes.MSG()
        while True:
            result = user32.GetMessageW(ctypes.byref(message), None, 0, 0)
            if result <= 0:
                break
            user32.TranslateMessage(ctypes.byref(message))
            user32.DispatchMessageW(ctypes.byref(message))
        user32.UnregisterHotKey(hwnd, 1)
        shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))
        self.hwnd = None

    def stop(self) -> None:
        if self.hwnd:
            ctypes.windll.user32.PostMessageW(self.hwnd, 0x0010, 0, 0)


class ARISDesktop:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("A.R.I.S. — Personal Assistant")
        self.root.geometry("900x650")
        self.root.minsize(680, 480)
        self.aris = ARIS()
        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.tray = TrayHotkey(self.events)
        self.tray_active = False
        self.busy = False
        self.voice_stop = threading.Event()
        self.voice_running = False
        self.model_names: list[str] = []
        self.last_lookup = ""
        self._link_tag_counter = 0
        self.health_summary = "Starting health check..."
        self.status_var = tk.StringVar(value=f"Local model: {self.aris.ollama_model}")
        self.reminder_var = tk.StringVar(value=str(self.aris.settings.get("reminder_interval_seconds", 15)))
        self.aris.output_callback = lambda text: self.events.put(("assistant", text))
        self.aris.approval_callback = self._approval_from_worker
        self._build_ui()
        self._show_history()
        if not self.aris._reminder_thread_started:
            threading.Thread(target=self.aris._reminder_loop, name="ARIS-reminders", daemon=True).start()
            self.aris._reminder_thread_started = True
        self.root.after(100, self._poll_events)
        self.root.after(250, self._load_models)
        self.root.after(650, lambda: self._run_health_check(startup=True))
        self.root.protocol("WM_DELETE_WINDOW", self._close_window)
        self.root.bind("<Control-Return>", lambda _event: self._submit())

    def _build_ui(self) -> None:
        toolbar = ttk.Frame(self.root, padding=(8, 8, 8, 3))
        toolbar.pack(fill=tk.X)
        ttk.Label(toolbar, text="Model").pack(side=tk.LEFT)
        self.model_var = tk.StringVar(value=self.aris.ollama_model)
        self.model_box = ttk.Combobox(toolbar, textvariable=self.model_var, state="readonly", width=20)
        self.model_box.pack(side=tk.LEFT, padx=(4, 5))
        self.model_box.bind("<<ComboboxSelected>>", self._model_selected)
        ttk.Button(toolbar, text="Refresh", command=self._load_models).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Folders", command=self._manage_folders).pack(side=tk.LEFT, padx=3)
        ttk.Button(toolbar, text="Tasks", command=self._show_tasks).pack(side=tk.LEFT, padx=3)
        ttk.Button(toolbar, text="Preview file", command=self._choose_preview_file).pack(side=tk.LEFT, padx=3)
        ttk.Button(toolbar, text="Analyze image", command=self._choose_image).pack(side=tk.LEFT, padx=3)
        ttk.Button(toolbar, text="Analyze screen", command=self._analyze_screen).pack(side=tk.LEFT, padx=3)
        ttk.Button(toolbar, text="Voice", command=self._toggle_voice).pack(side=tk.LEFT, padx=3)
        ttk.Label(toolbar, text="Reminder sec").pack(side=tk.LEFT, padx=(8, 2))
        ttk.Spinbox(toolbar, from_=5, to=3600, textvariable=self.reminder_var, width=5).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Set", command=self._set_reminder_interval).pack(side=tk.LEFT, padx=(3, 0))

        tools_row = ttk.Frame(self.root, padding=(8, 0, 8, 3))
        tools_row.pack(fill=tk.X)
        ttk.Button(tools_row, text="Capabilities", command=self._show_capabilities).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(tools_row, text="Health check", command=self._show_health).pack(side=tk.LEFT, padx=3)
        self.copy_lookup_button = ttk.Button(tools_row, text="Copy last lookup", command=self._copy_last_lookup, state=tk.DISABLED)
        self.copy_lookup_button.pack(side=tk.LEFT, padx=3)
        lookup_enabled = "web_lookup" in self.aris.loaded_plugins
        self.web_toggle_button = ttk.Button(
            tools_row,
            text="Turn web lookups off" if lookup_enabled else "Turn web lookups on",
            command=self._toggle_web_lookups,
        )
        self.web_toggle_button.pack(side=tk.LEFT, padx=3)
        self.stop_button = ttk.Button(tools_row, text="Stop task", command=self._stop_current, state=tk.DISABLED)
        self.stop_button.pack(side=tk.RIGHT, padx=3)

        self.chat = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, state=tk.DISABLED, font=("Segoe UI", 10), padx=10, pady=8)
        self.chat.pack(fill=tk.BOTH, expand=True, padx=8, pady=5)
        self.chat.tag_configure("user", foreground="#195cb8", spacing1=8)
        self.chat.tag_configure("assistant", foreground="#111111", spacing1=8)
        self.chat.tag_configure("system", foreground="#666666", spacing1=6)
        self.chat.tag_configure("url", foreground="#1769aa", underline=True)
        composer = ttk.Frame(self.root, padding=(8, 4, 8, 4))
        composer.pack(fill=tk.X)
        self.entry = ttk.Entry(composer)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind("<Return>", lambda _event: self._submit())
        self.send_button = ttk.Button(composer, text="Send", command=self._submit)
        self.send_button.pack(side=tk.LEFT, padx=(6, 0))
        ttk.Label(self.root, textvariable=self.status_var, anchor=tk.W, padding=(9, 3)).pack(fill=tk.X)
        self.entry.focus_set()

    def _show_history(self) -> None:
        for item in self.aris.messages[-12:]:
            self._append("You" if item["role"] == "user" else "ARIS", item["content"], item["role"])
        self._append("ARIS", "Ready. Use /help for commands. Ctrl+Alt+Space opens this window.", "system")

    def _append(self, speaker: str, text: str, tag: str) -> None:
        if speaker == "ARIS" and (text.startswith("Web results for:") or re.search(r"https?://", text)):
            self.last_lookup = text
            if hasattr(self, "copy_lookup_button"):
                self.copy_lookup_button.configure(state=tk.NORMAL)
        self.chat.configure(state=tk.NORMAL)
        self.chat.insert(tk.END, f"{speaker}: ", tag)
        cursor = 0
        for match in re.finditer(r"https?://[^\s<>]+", text):
            self.chat.insert(tk.END, text[cursor:match.start()], tag)
            url = match.group(0)
            clean_url = url.rstrip(".,;:!?)\u005d}")
            suffix = url[len(clean_url):]
            self._link_tag_counter += 1
            link_tag = f"url_{self._link_tag_counter}"
            self.chat.tag_configure(link_tag, foreground="#1769aa", underline=True)
            self.chat.insert(tk.END, clean_url, (tag, link_tag))
            self.chat.insert(tk.END, suffix, tag)
            self.chat.tag_bind(link_tag, "<Button-1>", lambda _event, target=clean_url: self._open_chat_url(target))
            self.chat.tag_bind(link_tag, "<Button-3>", lambda event, target=clean_url: self._show_link_menu(event, target))
            self.chat.tag_bind(link_tag, "<Enter>", lambda _event: self.chat.configure(cursor="hand2"))
            self.chat.tag_bind(link_tag, "<Leave>", lambda _event: self.chat.configure(cursor=""))
            cursor = match.start() + len(url)
        self.chat.insert(tk.END, text[cursor:] + "\n\n", tag)
        self.chat.see(tk.END)
        self.chat.configure(state=tk.DISABLED)

    def _open_chat_url(self, url: str) -> None:
        if webbrowser.open(url):
            self.status_var.set("Opened source link in your browser.")
        else:
            self.status_var.set("The default browser did not open that link.")

    def _show_link_menu(self, event: Any, url: str) -> None:
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Open link", command=lambda: self._open_chat_url(url))
        menu.add_command(label="Copy link", command=lambda: self._copy_text(url, "Copied source link."))
        menu.tk_popup(event.x_root, event.y_root)

    def _copy_text(self, text: str, message: str) -> None:
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update_idletasks()
            self.status_var.set(message)
        except tk.TclError as exc:
            self.status_var.set(f"Clipboard unavailable: {exc}")

    def _copy_last_lookup(self) -> None:
        if self.last_lookup:
            self._copy_text(self.last_lookup, "Copied the last lookup, including its source links.")

    def _load_models(self) -> None:
        def work() -> None:
            try:
                names = [str(item["name"]) for item in self.aris._installed_models()]
                self.events.put(("models", names))
            except Exception as exc:
                self.events.put(("status", f"Ollama unavailable: {exc}"))
        threading.Thread(target=work, name="ARIS-model-list", daemon=True).start()

    def _run_health_check(self, startup: bool = False) -> None:
        if startup:
            self.health_summary = "Checking Ollama, plugins, and desktop support..."
            self.status_var.set(self.health_summary)
        def work() -> None:
            try:
                report = self.aris._health_report()
            except Exception as exc:
                report = {"ok": False, "summary": "Health check failed", "details": [], "issues": [str(exc)]}
            self.events.put(("health", {**report, "startup": startup}))
        threading.Thread(target=work, name="ARIS-health-check", daemon=True).start()

    def _show_health(self) -> None:
        self._run_health_check(startup=False)

    def _show_capabilities(self) -> None:
        window = tk.Toplevel(self.root)
        window.title("ARIS capabilities and privacy")
        window.geometry("640x460")
        window.transient(self.root)
        body = scrolledtext.ScrolledText(window, wrap=tk.WORD, font=("Segoe UI", 10), padx=10, pady=8)
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        body.insert(tk.END, self.aris._capabilities_report())
        body.configure(state=tk.DISABLED)
        controls = ttk.Frame(window, padding=(8, 0, 8, 8))
        controls.pack(fill=tk.X)
        state = "on" if "web_lookup" in self.aris.loaded_plugins else "off"
        ttk.Label(controls, text=f"Online lookups are {state}.").pack(side=tk.LEFT)
        ttk.Button(controls, text="Close", command=window.destroy).pack(side=tk.RIGHT)
        lookup_button = ttk.Button(
            controls,
            text="Turn web lookups off" if state == "on" else "Turn web lookups on",
            command=lambda: self._toggle_web_lookups(window),
        )
        lookup_button.pack(side=tk.RIGHT, padx=6)

    def _toggle_web_lookups(self, parent: tk.Misc | None = None) -> None:
        if self.busy:
            self.status_var.set("Wait for the current ARIS task to finish before changing lookup settings.")
            return
        if "web_lookup" in self.aris.loaded_plugins:
            if not messagebox.askyesno(
                "Disable online lookups?",
                "ARIS will stop sending search queries and weather locations to online providers. You can re-enable them with /plugin enable web_lookup.",
                parent=parent or self.root,
            ):
                return
            self._run_input("/plugin disable web_lookup")
        else:
            self._run_input("/plugin enable web_lookup")

    def _model_selected(self, _event: Any = None) -> None:
        name = self.model_var.get()
        try:
            answer = self.aris._select_local_model(name)
            self.status_var.set(f"Local model: {name}")
            self._append("ARIS", answer, "system")
        except Exception as exc:
            messagebox.showerror("Model", str(exc), parent=self.root)

    def _manage_folders(self) -> None:
        folder = filedialog.askdirectory(parent=self.root, title="Choose a folder ARIS can access")
        if folder:
            try:
                self._append("ARIS", self.aris._add_folder(folder), "system")
            except Exception as exc:
                messagebox.showerror("Folder", str(exc), parent=self.root)
        self._append("ARIS", self.aris._folder_list(), "system")

    def _show_tasks(self) -> None:
        self._append("ARIS", self.aris._format_tasks(), "system")
        title = simpledialog.askstring("Add a task", "Task title (leave blank to cancel):", parent=self.root)
        if title:
            due = simpledialog.askstring("Due time", "Optional local time: YYYY-MM-DD HH:MM", parent=self.root)
            try:
                task = self.aris._add_task(title, due.strip() if due and due.strip() else None)
                self._append("ARIS", f"Added task #{task['id']}: {task['title']}" + (f" due {task['due']}" if task["due"] else ""), "system")
            except Exception as exc:
                messagebox.showerror("Task", str(exc), parent=self.root)

    def _set_reminder_interval(self) -> None:
        try:
            value = int(self.reminder_var.get())
            if not 5 <= value <= 3600:
                raise ValueError("Choose an interval from 5 to 3600 seconds.")
            self.aris.settings["reminder_interval_seconds"] = value
            self.aris._save_settings()
            self.aris._reminder_wake.set()
            self.status_var.set(f"Due tasks checked every {value} seconds")
        except Exception as exc:
            messagebox.showerror("Reminder interval", str(exc), parent=self.root)

    def _approval_from_worker(self, prompt: str, exact_word: str) -> bool:
        event = threading.Event()
        request = {"prompt": prompt, "word": exact_word, "event": event, "accepted": False}
        self.events.put(("confirm", request))
        if not event.wait(600):
            return False
        return bool(request["accepted"])

    def _poll_events(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "assistant":
                    self._append("ARIS", str(payload), "assistant")
                elif kind == "user":
                    self._append("You", str(payload), "user")
                elif kind == "voice-submit":
                    if not self.busy:
                        self._run_input(str(payload))
                    else:
                        self.status_var.set("ARIS is busy; voice input was skipped.")
                elif kind == "status":
                    self.status_var.set(str(payload))
                elif kind == "health":
                    self.health_summary = str(payload.get("summary", "Health check completed."))
                    self.status_var.set(self.health_summary)
                    details = [*payload.get("details", [])]
                    issues = list(payload.get("issues", []))
                    if issues:
                        details.extend(["Needs attention:", *(f"- {issue}" for issue in issues)])
                    if not payload.get("startup") or issues:
                        self._append("ARIS", "Health check\n" + "\n".join(details), "system")
                elif kind == "models":
                    self.model_names = payload
                    self.model_box["values"] = payload
                    if self.aris.ollama_model in payload:
                        self.model_var.set(self.aris.ollama_model)
                    self.status_var.set(f"{len(payload)} local model(s); active: {self.aris.ollama_model}")
                elif kind == "confirm":
                    typed = simpledialog.askstring("ARIS approval required", f"{payload['prompt']}\n\nType {payload['word']} exactly to approve:", parent=self.root)
                    payload["accepted"] = typed == payload["word"]
                    payload["event"].set()
                elif kind == "show":
                    self.root.deiconify()
                    self.root.state("normal")
                    self.root.lift()
                    self.root.focus_force()
                elif kind == "exit":
                    self._exit()
                elif kind == "busy":
                    self.busy = bool(payload)
                    self.send_button.configure(state=tk.DISABLED if self.busy else tk.NORMAL)
                    self.stop_button.configure(state=tk.NORMAL if self.busy else tk.DISABLED)
                    if hasattr(self, "web_toggle_button"):
                        self.web_toggle_button.configure(text="Turn web lookups off" if "web_lookup" in self.aris.loaded_plugins else "Turn web lookups on")
                    self.status_var.set("Working..." if self.busy else self.health_summary)
                elif kind == "quit-after-response":
                    self._exit()
        except queue.Empty:
            pass
        if self.root.winfo_exists():
            self.root.after(100, self._poll_events)

    def _run_input(self, text: str, image: bytes | None = None) -> None:
        if self.busy:
            self.status_var.set("ARIS is already working; wait for its reply.")
            return
        self.busy = True
        self.aris._stop_event.clear()
        self.events.put(("user", text))
        self.events.put(("busy", True))
        def work() -> None:
            try:
                if image is not None:
                    answer = self.aris._ollama_chat(text, image_bytes=image)
                    self.aris.speak(answer)
                elif text.startswith("/"):
                    keep_running = self.aris.handle_command(text)
                    if not keep_running:
                        self.events.put(("quit-after-response", None))
                else:
                    local_result = self.aris._direct_workspace_action(text)
                    if local_result is not None:
                        self.aris.speak(local_result)
                    elif self.aris.backend == "ollama":
                        self.aris.speak(self.aris._ollama_chat(text))
                    elif self.aris.backend == "api":
                        self.aris.speak(self.aris._api_chat(text))
                    else:
                        self.aris.speak("No model is configured. Use /models or set up Ollama.")
            except Exception as exc:
                self.aris.speak(f"ARIS encountered an error: {exc}")
            finally:
                self.events.put(("busy", False))
        threading.Thread(target=work, name="ARIS-turn", daemon=True).start()

    def _stop_current(self) -> None:
        if not self.busy:
            return
        self.aris._stop_event.set()
        self.status_var.set("Stop requested. ARIS will finish any required verification and stop before another step.")

    def _submit(self) -> None:
        if self.busy:
            return
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, tk.END)
        if text.casefold() == "/voice":
            self._append("You", text, "user")
            if not self.voice_running:
                self._toggle_voice()
            return
        if text.casefold() == "/text":
            self._append("You", text, "user")
            self.voice_stop.set()
            self.voice_running = False
            self.aris.voice_enabled = False
            self.status_var.set("Keyboard mode enabled.")
            return
        if text.casefold() == "/see":
            self._choose_image()
            return
        if text.casefold() == "/folder add":
            self._manage_folders()
            return
        if text.startswith("/"):
            command = text.split(maxsplit=1)[0].casefold()
            if command in {"/see", "/screen"} or text.casefold() == "/folder add":
                self._run_input(text)
                return
        self._run_input(text)

    def _choose_image(self) -> None:
        path = filedialog.askopenfilename(parent=self.root, title="Choose an image for local analysis", filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.webp")])
        if not path:
            return
        self._run_input(f'/see "{path}"')

    def _choose_preview_file(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Choose a local file to preview",
            filetypes=[("Images and documents", "*.png *.jpg *.jpeg *.bmp *.webp *.gif *.pdf *.docx"), ("All files", "*.*")],
        )
        if not path:
            return
        self._run_input(f'/preview "{path}"')

    def _analyze_screen(self) -> None:
        self._run_input("/screen")

    def _toggle_voice(self) -> None:
        if not self.voice_stop.is_set() and getattr(self, "voice_running", False):
            self.voice_stop.set()
            self.voice_running = False
            self.aris.voice_enabled = False
            self.status_var.set("Stopping voice input...")
            return
        self.voice_stop = threading.Event()
        stop_event = self.voice_stop
        self.voice_running = True
        self.aris.voice_enabled = True
        self.status_var.set("Voice input active; say 'text mode' to stop.")
        def listen_loop() -> None:
            while not stop_event.is_set():
                try:
                    text = self.aris._listen_windows(announce=False)
                    if text:
                        if text.casefold() == "text mode":
                            break
                        self.events.put(("voice-submit", text))
                except Exception as exc:
                    self.events.put(("status", f"Voice input unavailable: {exc}"))
                    break
            if self.voice_stop is stop_event:
                self.voice_running = False
                self.aris.voice_enabled = False
                self.voice_stop.set()
                self.events.put(("status", "Voice input stopped"))
        threading.Thread(target=listen_loop, name="ARIS-voice", daemon=True).start()

    def _close_window(self) -> None:
        if self.tray_active:
            self.root.withdraw()
            self.status_var.set("ARIS is running in the system tray. Ctrl+Alt+Space opens it.")
        else:
            self._exit()

    def _exit(self) -> None:
        self.voice_stop.set()
        self.aris._reminder_stop.set()
        self.aris._reminder_wake.set()
        self.tray.stop()
        self.root.destroy()

    def run(self) -> None:
        self.tray_active = self.tray.start()
        if self.tray_active:
            self.status_var.set("Ready | tray icon active | Ctrl+Alt+Space opens ARIS")
        elif self.tray.error:
            self.status_var.set(f"Ready | hotkey/tray unavailable: {self.tray.error}")
        self.root.mainloop()


def main() -> None:
    ARISDesktop().run()


if __name__ == "__main__":
    main()
