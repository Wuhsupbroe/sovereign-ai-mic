"""
platform_adapter.py — Cross-platform abstraction for Sovereign AI Mic.

Provides a unified interface for OS-specific operations:
  - Text injection into the focused window
  - Monitor enumeration
  - Window-handle discovery by PID
  - External-window placement
  - Native window styling (blur, rounded corners, taskbar icon)
  - Floating-window focus prevention
  - System font discovery
  - TTS voice backend labelling
  - Default hotkey recommendation

Usage:
    from platform_adapter import get_adapter
    _platform = get_adapter()
    _platform.inject_text("hello world")
"""

import os
import sys
import subprocess
import time

PLATFORM = sys.platform  # 'win32' | 'darwin' | 'linux'


# ─────────────────────────────────────────────────────────────────────────────
#  Base adapter (sensible no-ops / cross-platform fallbacks)
# ─────────────────────────────────────────────────────────────────────────────

class PlatformAdapter:
    """Base class — defines the cross-platform interface with safe fallbacks."""

    # ── Text injection ────────────────────────────────────────────────────────
    def inject_text(self, text: str) -> None:
        """Copy *text* to the clipboard and paste it into the focused window."""
        raise NotImplementedError

    # ── Display / monitor enumeration ─────────────────────────────────────────
    def get_monitors(self) -> list:
        """Return ``[(x, y, w, h), ...]`` for every connected monitor."""
        return [(0, 0, 1920, 1080)]

    # ── External application window management ────────────────────────────────
    def find_windows_by_pid(self, pid: int) -> list:
        """Return visible OS window handles belonging to *pid*."""
        return []

    def place_window(self, hwnd, x: int, y: int, w: int, h: int,
                     maximize: bool = False) -> None:
        """Move / resize window *hwnd* to the given rect."""
        pass

    # ── Native window chrome ──────────────────────────────────────────────────
    def apply_main_window_effects(self, root_hwnd: int) -> None:
        """Apply OS-native decoration (acrylic blur, rounded corners, etc.)."""
        pass

    def apply_taskbar_icon(self, hwnd: int, ico_path: str,
                           tk_root=None) -> None:
        """Force the app into the taskbar and set its icon."""
        self.set_app_icon(tk_root, ico_path)

    def set_app_icon(self, tk_root, icon_path: str) -> None:
        """Set the window icon via tkinter (cross-platform fallback)."""
        if tk_root is None or not icon_path or not os.path.exists(icon_path):
            return
        try:
            from PIL import Image, ImageTk
            ico = Image.open(icon_path).resize((32, 32), Image.LANCZOS)
            tk_root._app_icon = ImageTk.PhotoImage(ico)
            tk_root.iconphoto(True, tk_root._app_icon)
        except Exception:
            pass

    def prevent_pill_focus_steal(self, pill_toplevel) -> None:
        """Prevent a floating Toplevel from stealing keyboard focus."""
        pass  # No-op on non-Windows; pynput + OS handle focus correctly.

    # ── Default hotkey ────────────────────────────────────────────────────────
    def default_hotkey(self) -> tuple:
        """Return ``(pynput_key_str, display_name)`` for the default hotkey."""
        return ("Key.alt_r", "Right Alt")

    # ── Font discovery ────────────────────────────────────────────────────────
    def get_font_candidates(self) -> list:
        """Return prioritised list of font file paths suitable for PIL."""
        return []

    # ── TTS backend label ─────────────────────────────────────────────────────
    def pyttsx3_label(self) -> str:
        """Short description of the pyttsx3 voice engine on this platform."""
        return "System voices (pyttsx3)"


# ─────────────────────────────────────────────────────────────────────────────
#  Windows adapter
# ─────────────────────────────────────────────────────────────────────────────

class WindowsAdapter(PlatformAdapter):
    """Windows (Win10/11) implementation using ctypes / Win32 APIs."""

    def inject_text(self, text: str) -> None:
        """Paste *text* via Ctrl+V using low-level Win32 keybd_event."""
        import pyperclip
        import ctypes

        pyperclip.copy(text)
        time.sleep(0.15)

        VK_CONTROL      = 0x11
        VK_V            = 0x56
        VK_LWIN         = 0x5B
        VK_RWIN         = 0x5C
        VK_SHIFT        = 0x10
        KEYEVENTF_KEYUP = 0x0002

        try:
            # Release Shift/Win keys (don't release Alt — it would focus the menu bar)
            for mod in [VK_LWIN, VK_RWIN, VK_SHIFT]:
                ctypes.windll.user32.keybd_event(mod, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(0.02)
            # Ctrl+V
            ctypes.windll.user32.keybd_event(VK_CONTROL, 0, 0, 0)
            time.sleep(0.02)
            ctypes.windll.user32.keybd_event(VK_V, 0, 0, 0)
            time.sleep(0.02)
            ctypes.windll.user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(0.02)
            ctypes.windll.user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
        except Exception as exc:
            print(f"[WindowsAdapter] keybd_event paste failed: {exc}")

    def get_monitors(self) -> list:
        import ctypes
        import ctypes.wintypes

        class _RECT(ctypes.Structure):
            _fields_ = [("left",   ctypes.c_long), ("top",    ctypes.c_long),
                        ("right",  ctypes.c_long), ("bottom", ctypes.c_long)]

        monitors = []
        _PROC = ctypes.WINFUNCTYPE(
            ctypes.c_bool,
            ctypes.c_ulong, ctypes.c_ulong,
            ctypes.POINTER(_RECT), ctypes.c_long)

        def _cb(hMon, hDC, lpRect, _):
            r = lpRect.contents
            monitors.append((r.left, r.top, r.right - r.left, r.bottom - r.top))
            return True

        try:
            ctypes.windll.user32.EnumDisplayMonitors(None, None, _PROC(_cb), 0)
        except Exception:
            pass
        return monitors or [(0, 0, 1920, 1080)]

    def find_windows_by_pid(self, pid: int) -> list:
        import ctypes
        import ctypes.wintypes

        windows = []
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_ulong, ctypes.c_long)

        def _cb(hwnd, _):
            if ctypes.windll.user32.IsWindowVisible(hwnd):
                buf = ctypes.wintypes.DWORD()
                ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(buf))
                if buf.value == pid:
                    windows.append(hwnd)
            return True

        try:
            ctypes.windll.user32.EnumWindows(WNDENUMPROC(_cb), 0)
        except Exception:
            pass
        return windows

    def place_window(self, hwnd, x: int, y: int, w: int, h: int,
                     maximize: bool = False) -> None:
        import ctypes
        SWP_NOZORDER   = 0x0004
        SWP_SHOWWINDOW = 0x0040
        SW_RESTORE     = 9
        SW_MAXIMIZE    = 3
        try:
            u32 = ctypes.windll.user32
            u32.ShowWindow(hwnd, SW_RESTORE)
            time.sleep(0.05)
            u32.SetWindowPos(hwnd, 0, x, y, w, h,
                             SWP_NOZORDER | SWP_SHOWWINDOW)
            if maximize:
                time.sleep(0.05)
                u32.ShowWindow(hwnd, SW_MAXIMIZE)
        except Exception as exc:
            print(f"[WindowsAdapter] place_window failed: {exc}")

    def prevent_pill_focus_steal(self, pill_toplevel) -> None:
        import ctypes
        GWL_EXSTYLE      = -20
        WS_EX_NOACTIVATE = 0x08000000
        try:
            hwnd = pill_toplevel.winfo_id()
            for target in (hwnd, ctypes.windll.user32.GetParent(hwnd)):
                if target:
                    ex = ctypes.windll.user32.GetWindowLongW(target, GWL_EXSTYLE)
                    ctypes.windll.user32.SetWindowLongW(
                        target, GWL_EXSTYLE, ex | WS_EX_NOACTIVATE)
        except Exception as exc:
            print(f"[WindowsAdapter] prevent_pill_focus_steal failed: {exc}")

    def apply_taskbar_icon(self, hwnd: int, ico_path: str,
                           tk_root=None) -> None:
        import ctypes
        try:
            user32 = ctypes.windll.user32
            user32.GetAncestor.restype = ctypes.c_void_p
            real_hwnd = user32.GetAncestor(hwnd, 2) or hwnd

            GWL_EXSTYLE      = -20
            WS_EX_APPWINDOW  = 0x00040000
            WS_EX_TOOLWINDOW = 0x00000080
            SWP_FLAGS        = 0x0027

            ex = user32.GetWindowLongW(real_hwnd, GWL_EXSTYLE)
            ex = (ex & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
            user32.SetWindowLongW(real_hwnd, GWL_EXSTYLE, ex)
            user32.SetWindowPos(real_hwnd, 0, 0, 0, 0, 0, SWP_FLAGS)

            user32.LoadImageW.restype  = ctypes.c_void_p
            user32.SendMessageW.restype = ctypes.c_long
            IMAGE_ICON      = 1
            LR_LOADFROMFILE = 0x0010
            LR_DEFAULTSIZE  = 0x0040
            WM_SETICON      = 0x0080

            hbig = user32.LoadImageW(None, ico_path, IMAGE_ICON, 0, 0,
                                     LR_LOADFROMFILE | LR_DEFAULTSIZE)
            hsmall = user32.LoadImageW(None, ico_path, IMAGE_ICON, 16, 16,
                                       LR_LOADFROMFILE)
            if hbig:
                user32.SendMessageW(real_hwnd, WM_SETICON, 1, hbig)
            if hsmall:
                user32.SendMessageW(real_hwnd, WM_SETICON, 0, hsmall)

            self.set_app_icon(tk_root, ico_path)
        except Exception as exc:
            print(f"[WindowsAdapter] apply_taskbar_icon failed: {exc}")

    def default_hotkey(self) -> tuple:
        return ("Key.alt_r", "Right Alt")

    def get_font_candidates(self) -> list:
        return [
            r"C:\Windows\Fonts\segoeuib.ttf",
            r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\arialbd.ttf",
            r"C:\Windows\Fonts\arial.ttf",
        ]

    def pyttsx3_label(self) -> str:
        return "Windows SAPI voices (pyttsx3)"


# ─────────────────────────────────────────────────────────────────────────────
#  macOS adapter
# ─────────────────────────────────────────────────────────────────────────────

class MacAdapter(PlatformAdapter):
    """macOS 13+ implementation using pynput + osascript."""

    def inject_text(self, text: str) -> None:
        """Paste *text* via Cmd+V using pynput keyboard controller."""
        import pyperclip
        from pynput.keyboard import Controller as _KB, Key

        pyperclip.copy(text)
        time.sleep(0.15)

        kb = _KB()
        try:
            # Small delay to ensure clipboard is flushed before sending hotkey
            time.sleep(0.05)
            kb.press(Key.cmd)
            time.sleep(0.02)
            kb.press('v')
            time.sleep(0.02)
            kb.release('v')
            time.sleep(0.02)
            kb.release(Key.cmd)
        except Exception as exc:
            print(f"[MacAdapter] Cmd+V paste failed: {exc}")

    def get_monitors(self) -> list:
        """Return monitor rects via AppleScript (no extra dependencies)."""
        try:
            script = (
                'tell application "Finder"\n'
                '  set _b to bounds of window of desktop\n'
                'end tell'
            )
            out = subprocess.check_output(
                ["osascript", "-e", script],
                timeout=3, stderr=subprocess.DEVNULL
            ).decode().strip()
            # Output: "0, 0, 2560, 1440"  (left, top, right, bottom)
            coords = [int(c.strip()) for c in out.split(",")]
            if len(coords) == 4:
                return [(coords[0], coords[1],
                         coords[2] - coords[0], coords[3] - coords[1])]
        except Exception:
            pass
        # Tkinter-based fallback (requires the main tk root to already exist)
        try:
            import tkinter as tk
            tmp = tk.Tk()
            tmp.withdraw()
            sw, sh = tmp.winfo_screenwidth(), tmp.winfo_screenheight()
            tmp.destroy()
            return [(0, 0, sw, sh)]
        except Exception:
            return [(0, 0, 1920, 1080)]

    def find_windows_by_pid(self, pid: int) -> list:
        """On macOS, window handles aren't available without PyObjC."""
        return []

    def place_window(self, hwnd, x: int, y: int, w: int, h: int,
                     maximize: bool = False) -> None:
        """Window placement is not supported on macOS without accessibility APIs."""
        pass

    def default_hotkey(self) -> tuple:
        # Right Option key — same pynput key as Windows Right Alt
        return ("Key.alt_r", "Right Option")

    def get_font_candidates(self) -> list:
        return [
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial Bold.ttf",
            "/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
        ]

    def pyttsx3_label(self) -> str:
        return "macOS system voices (pyttsx3)"


# ─────────────────────────────────────────────────────────────────────────────
#  Linux adapter
# ─────────────────────────────────────────────────────────────────────────────

class LinuxAdapter(PlatformAdapter):
    """Linux fallback implementation using pynput Ctrl+V."""

    def inject_text(self, text: str) -> None:
        """Paste *text* via Ctrl+V using pynput keyboard controller."""
        import pyperclip
        from pynput.keyboard import Controller as _KB, Key

        pyperclip.copy(text)
        time.sleep(0.15)

        kb = _KB()
        try:
            time.sleep(0.05)
            kb.press(Key.ctrl)
            time.sleep(0.02)
            kb.press('v')
            time.sleep(0.02)
            kb.release('v')
            time.sleep(0.02)
            kb.release(Key.ctrl)
        except Exception as exc:
            print(f"[LinuxAdapter] Ctrl+V paste failed: {exc}")

    def get_monitors(self) -> list:
        """Detect monitors via xrandr; fall back to single 1920×1080."""
        try:
            out = subprocess.check_output(
                ["xrandr", "--query"], timeout=3,
                stderr=subprocess.DEVNULL
            ).decode()
            import re
            monitors = []
            for m in re.finditer(
                    r"(\d+)x(\d+)\+(\d+)\+(\d+)", out):
                w, h, x, y = int(m.group(1)), int(m.group(2)), \
                             int(m.group(3)), int(m.group(4))
                monitors.append((x, y, w, h))
            if monitors:
                return monitors
        except Exception:
            pass
        return [(0, 0, 1920, 1080)]

    def get_font_candidates(self) -> list:
        return [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans.ttf",
        ]

    def pyttsx3_label(self) -> str:
        return "System voices (pyttsx3 / espeak)"


# ─────────────────────────────────────────────────────────────────────────────
#  Factory
# ─────────────────────────────────────────────────────────────────────────────

def get_adapter() -> PlatformAdapter:
    """Return the correct adapter for the current operating system."""
    if sys.platform == "win32":
        return WindowsAdapter()
    if sys.platform == "darwin":
        return MacAdapter()
    return LinuxAdapter()
