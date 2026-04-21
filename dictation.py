#!/usr/bin/env python3
"""
Dictation — Free local dictation app, Apple-style UI
Hold Right Alt anywhere on Windows to dictate.
"""

import threading
import time
import math
import json
import os
import random
import subprocess
import ctypes
import ctypes.wintypes
import urllib.request
import urllib.error
import tempfile
import numpy as np
import sounddevice as sd
import pyperclip
import tkinter as tk
import tkinter.filedialog as fd
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageTk
from pynput import keyboard as pynput_keyboard
from pynput.keyboard import Controller as KeyboardController, Key
from faster_whisper import WhisperModel
from datetime import date

# Optional TTS backend — pyttsx3 (local SAPI, offline)
try:
    import pyttsx3 as _pyttsx3
    _TTS_AVAILABLE = True
except ImportError:
    _TTS_AVAILABLE = False

# Optional high-quality TTS — Edge TTS (Microsoft Neural voices, online, free)
try:
    import edge_tts as _edge_tts
    import asyncio  as _asyncio
    _EDGE_TTS_AVAILABLE = True
except ImportError:
    _EDGE_TTS_AVAILABLE = False

# pygame for mp3 playback (used with Edge TTS)
try:
    import pygame as _pygame
    _pygame.mixer.pre_init(44100, -16, 2, 512)
    _pygame.mixer.init()
    _PYGAME_AVAILABLE = True
except Exception:
    _PYGAME_AVAILABLE = False

# ── Config ─────────────────────────────────────────────────────────────────────
SAMPLE_RATE = 16000
HERE        = os.path.dirname(os.path.abspath(__file__))
STATS_FILE  = os.path.join(HERE, "stats.json")
LOG_FILE    = os.path.join(HERE, "log.json")
CONFIG_FILE = os.path.join(HERE, "config.json")

# Friendly display names for common pynput special keys
KEY_DISPLAY = {
    "Key.alt_r": "Right Alt",   "Key.alt_l": "Left Alt",
    "Key.alt": "Alt",
    "Key.ctrl_r": "Right Ctrl", "Key.ctrl_l": "Left Ctrl",
    "Key.shift_r": "Right Shift","Key.shift_l": "Left Shift",
    "Key.cmd": "Win",           "Key.cmd_r": "Win (R)",
    "Key.caps_lock": "Caps Lock",
    "Key.tab": "Tab",           "Key.space": "Space",
    "Key.f1":  "F1",  "Key.f2":  "F2",  "Key.f3":  "F3",
    "Key.f4":  "F4",  "Key.f5":  "F5",  "Key.f6":  "F6",
    "Key.f7":  "F7",  "Key.f8":  "F8",  "Key.f9":  "F9",
    "Key.f10": "F10", "Key.f11": "F11", "Key.f12": "F12",
    "Key.insert": "Insert",     "Key.scroll_lock": "Scroll Lock",
    "Key.pause": "Pause",       "Key.num_lock": "Num Lock",
    "Key.print_screen": "Print Screen",
}

MODEL_OPTIONS = [
    ("Tiny",   "tiny",   "Fastest"),
    ("Base",   "base",   "Balanced"),
    ("Small",  "small",  "Accurate"),
]

# ══════════════════════════════════════════════════════════════════════════════
# Design System — Sleek Dark Mode
# ══════════════════════════════════════════════════════════════════════════════

# ── 8-pt Grid ─────────────────────────────────────────────────────────────────
G  = 8;  G2 = 16;  G3 = 24;  G4 = 32;  G5 = 40

# ── Typography (Helvetica Neue) ────────────────────────────────────────────────
F_DISPLAY = ("Helvetica Neue", 21, "bold")
F_HEADING = ("Helvetica Neue", 14, "bold")
F_SUBHEAD = ("Helvetica Neue", 12, "bold")
F_BODY    = ("Helvetica Neue", 12)
F_LABEL   = ("Helvetica Neue", 11)
F_CAPTION = ("Helvetica Neue",  9)
F_BADGE   = ("Helvetica Neue",  9, "bold")
F_CODE    = ("Consolas", 10)

# ── Dark Mode Palette ─────────────────────────────────────────────────────────
WIN_BG      = "#121212"    # Apple-dark window / chrome
SIDEBAR_BG  = "#111111"    # sidebar — slightly deeper
CONTENT_BG  = "#151515"    # content area (matches window)
CARD_BG     = "#1A1D1A"    # modern translucent glass card surface
CARD_HOVER  = "#2a2c2a"    # card hover

# Accent — Apple dark-mode green
ACCENT      = "#30d158"
ACCENT_DIM  = "#248a3d"
ACCENT_LITE = "#0d2518"    # very dark green tint (selection bg)
ACCENT_TEXT = "#34d860"    # bright green text

# Text (semantic hierarchy)
T_PRI   = "#f2f2f7"    # Primary   — near white
T_SEC   = "#98989e"    # Secondary — medium gray
T_TER   = "#636366"    # Tertiary  — dark gray (hints/timestamps)
T_LINK  = "#30d158"

# Borders & dividers
BORDER  = "#3a3a3c"
DIVIDER = "#2c2c2e"

# Interactive states
BTN_BG    = "#3a3a3c"
BTN_HOVER = "#48484a"

# Input / entry backgrounds
ENTRY_BG  = "#3a3a3c"
CODE_BG   = "#252528"

# ── Backward-compat aliases ────────────────────────────────────────────────────
SEL_BG      = ACCENT_LITE
SEL_TEXT    = ACCENT_TEXT
NAV_TEXT    = T_SEC
LABEL_SMALL = T_TER
TEXT_MAIN   = T_PRI
TEXT_SUB    = T_SEC

# ── Status / chart colours ────────────────────────────────────────────────────
GREEN_DONUT = "#30d158"
BLUE_DONUT  = "#0a84ff"
RING_BG     = "#3a3a3c"

# ── Traffic lights ────────────────────────────────────────────────────────────
TL_RED    = "#ff5f57"
TL_YELLOW = "#febc2e"
TL_GREEN  = "#28c840"

# ── Pill (recording indicator) ────────────────────────────────────────────────
PILL_W       = 340
PILL_H       = 130
PILL_BG      = "#2c2c2e"
PILL_CHROMA  = "#fe01fe"
PILL_N_BARS  = 24
PILL_BAR_W   = 4
PILL_BAR_GAP = 3

# ── Character assistant window ────────────────────────────────────────────────
CHAR_WIN_W = 80     # floating character window size (square)
CHAR_WIN_H = 80

# Edge TTS voice catalogue (display name, edge voice ID)
EDGE_VOICES = [
    ("Aria — US Female  ✦ recommended", "en-US-AriaNeural"),
    ("Jenny — US Female",               "en-US-JennyNeural"),
    ("Ava — US Female (warm)",          "en-US-AvaNeural"),
    ("Emma — US Female (expressive)",   "en-US-EmmaNeural"),
    ("Guy — US Male",                   "en-US-GuyNeural"),
    ("Christopher — US Male",           "en-US-ChristopherNeural"),
    ("Eric — US Male (warm)",           "en-US-EricNeural"),
    ("Roger — US Male (confident)",     "en-US-RogerNeural"),
    ("Sonia — UK Female",               "en-GB-SoniaNeural"),
    ("Ryan — UK Male",                  "en-GB-RyanNeural"),
    ("Natasha — AU Female",             "en-AU-NatashaNeural"),
    ("William — AU Male",               "en-AU-WilliamNeural"),
]
EDGE_VOICE_IDS   = [v[1] for v in EDGE_VOICES]
EDGE_VOICE_NAMES = [v[0] for v in EDGE_VOICES]

# Character skins and colour presets
CHAR_STYLES       = ["Robot", "Buddy", "Ghost", "Alien"]
CHAR_COLOR_NAMES  = ["Mint", "Blue", "Purple", "Orange", "Pink", "Silver"]
CHAR_COLOR_VALUES = ["#30d158", "#0a84ff", "#bf5af2", "#ff9f0a", "#ff375f", "#8e8e93"]

# ── AI Assistant palette ──────────────────────────────────────────────────────
AI_BLUE    = "#0a84ff"
AI_DARK    = "#1c1c1e"
AI_BORDER  = "#3a3a3c"
AI_TEXT    = "#f2f2f7"
AI_SUBTEXT = "#98989e"
AI_POPUP_W = 460
GEMINI_MODELS = [
    ("2.5 Flash  ✦ recommended", "gemini-2.5-flash"),
    ("2.5 Pro    ✦ most capable","gemini-2.5-pro"),
    ("2.5 Flash Lite  (fastest)","gemini-2.5-flash-lite-preview"),
    ("2.0 Flash  (stable)",      "gemini-2.0-flash"),
    ("2.0 Flash Lite (cheapest)","gemini-2.0-flash-lite"),
]


# ── Windows 11 DWM glass helpers ───────────────────────────────────────────────
def _apply_acrylic(hwnd: int, tint: int = 0xCCF2F2F2) -> bool:
    """Apply Windows 10/11 Acrylic blur-behind to a window handle.
    tint is AABBGGRR. Returns True on success."""
    try:
        class _Accent(ctypes.Structure):
            _fields_ = [("State",  ctypes.c_int),
                        ("Flags",  ctypes.c_int),
                        ("Color",  ctypes.c_uint),
                        ("AnimId", ctypes.c_int)]
        class _AttrData(ctypes.Structure):
            _fields_ = [("Attr",  ctypes.c_int),
                        ("pData", ctypes.c_void_p),
                        ("Size",  ctypes.c_size_t)]
        ac       = _Accent(); ac.State = 4; ac.Color = tint
        ad       = _AttrData()
        ad.Attr  = 19   # WCA_ACCENT_POLICY
        ad.pData = ctypes.addressof(ac)
        ad.Size  = ctypes.sizeof(ac)
        ctypes.windll.user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(ad))
        return True
    except Exception:
        return False

def _apply_win11_style(hwnd: int) -> None:
    """Enable Windows 11 rounded corners and a subtle border colour."""
    try:
        dwm = ctypes.windll.dwmapi
        # Rounded corners (DWMWCP_ROUND = 2)
        dwm.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(ctypes.c_int(2)), 4)
        # Border colour — accent-green in COLORREF (BGR, no alpha)
        dwm.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(ctypes.c_int(0x005a8700)), 4)
    except Exception:
        pass

def _get_root_hwnd(root) -> int:
    """Return the real top-level HWND for a Tk/CTk root window."""
    child = root.winfo_id()
    parent = ctypes.windll.user32.GetParent(child)
    return parent if parent else child


def _apply_taskbar_icon(hwnd: int, ico_path: str, tk_root=None) -> None:
    """
    Force a borderless (overrideredirect) window into the Windows taskbar
    and set its icon.  Works on 64-bit Windows with proper ctypes return types.
    """
    try:
        user32 = ctypes.windll.user32

        # GA_ROOT (2) walks up the HWND chain to find the true top-level window.
        # This is more reliable than GetParent() for overrideredirect windows.
        user32.GetAncestor.restype = ctypes.c_void_p
        real_hwnd = user32.GetAncestor(hwnd, 2) or hwnd

        # ── Force window into taskbar ─────────────────────────────────────────
        GWL_EXSTYLE      = -20
        WS_EX_APPWINDOW  = 0x00040000
        WS_EX_TOOLWINDOW = 0x00000080
        SWP_FLAGS        = 0x0027   # NOMOVE | NOSIZE | NOZORDER | FRAMECHANGED

        ex = user32.GetWindowLongW(real_hwnd, GWL_EXSTYLE)
        ex = (ex & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
        user32.SetWindowLongW(real_hwnd, GWL_EXSTYLE, ex)
        user32.SetWindowPos(real_hwnd, 0, 0, 0, 0, 0, SWP_FLAGS)

        # ── Load icon and send via WM_SETICON ─────────────────────────────────
        # CRITICAL: set restype=c_void_p so 64-bit HICON isn't truncated to int32
        user32.LoadImageW.restype  = ctypes.c_void_p
        user32.SendMessageW.restype = ctypes.c_long

        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x0010
        LR_DEFAULTSIZE  = 0x0040
        WM_SETICON      = 0x0080

        hicon_big = user32.LoadImageW(
            None, ico_path, IMAGE_ICON, 0, 0,
            LR_LOADFROMFILE | LR_DEFAULTSIZE)
        hicon_small = user32.LoadImageW(
            None, ico_path, IMAGE_ICON, 16, 16,
            LR_LOADFROMFILE)

        if hicon_big:
            user32.SendMessageW(real_hwnd, WM_SETICON, 1, hicon_big)
        if hicon_small:
            user32.SendMessageW(real_hwnd, WM_SETICON, 0, hicon_small)

        # ── Also set via tkinter iconphoto as belt-and-suspenders ─────────────
        if tk_root is not None:
            try:
                _ico = Image.open(ico_path).resize((32, 32), Image.LANCZOS)
                tk_root._taskbar_icon = ImageTk.PhotoImage(_ico)
                tk_root.iconphoto(True, tk_root._taskbar_icon)
            except Exception:
                pass

    except Exception:
        pass


class DonutChart(tk.Canvas):
    """A circular donut/ring chart drawn on a tk Canvas."""

    def __init__(self, parent, size=160, bg=CARD_BG, **kwargs):
        super().__init__(parent, width=size, height=size,
                         bg=bg, highlightthickness=0, **kwargs)
        self._size = size

    def render(self, value_str, label, pct, color=GREEN_DONUT):
        self.delete("all")
        s   = self._size
        pad = 22
        r   = (s - pad * 2) // 2
        cx  = cy = s // 2
        w   = 14   # ring thickness

        # background ring
        self.create_arc(cx - r, cy - r, cx + r, cy + r,
                        start=90, extent=-359.99,
                        outline=RING_BG, width=w, style="arc")

        # value ring
        if pct > 0:
            extent = -min(pct, 1.0) * 359.99
            self.create_arc(cx - r, cy - r, cx + r, cy + r,
                            start=90, extent=extent,
                            outline=color, width=w, style="arc",
                            )

        # centre labels
        self.create_text(cx, cy - 13,
                         text=label, font=("Helvetica Neue", 10),
                         fill=LABEL_SMALL)
        self.create_text(cx, cy + 8,
                         text=value_str,
                         font=("Helvetica Neue", 20, "bold"),
                         fill=TEXT_MAIN)


# ── Monitor enumeration (no extra packages needed) ─────────────────────────────
class _RECT(ctypes.Structure):
    _fields_ = [("left",   ctypes.c_long), ("top",    ctypes.c_long),
                ("right",  ctypes.c_long), ("bottom", ctypes.c_long)]

def _get_monitors():
    """Return list of (x, y, w, h) for every connected monitor."""
    monitors = []
    _MONITORENUMPROC = ctypes.WINFUNCTYPE(
        ctypes.c_bool,
        ctypes.c_ulong, ctypes.c_ulong,
        ctypes.POINTER(_RECT), ctypes.c_long)

    def _cb(hMon, hDC, lpRect, _):
        r = lpRect.contents
        monitors.append((r.left, r.top, r.right - r.left, r.bottom - r.top))
        return True

    ctypes.windll.user32.EnumDisplayMonitors(
        None, None, _MONITORENUMPROC(_cb), 0)
    return monitors or [(0, 0, 1920, 1080)]


# ── Position grid layout ────────────────────────────────────────────────────────
# (row, col, position-key, button-symbol)
POSITION_GRID = [
    (0, 0, "top-left",    "↖"), (0, 1, "top",    "↑"), (0, 2, "top-right",    "↗"),
    (1, 0, "left",        "←"), (1, 1, "center", "·"), (1, 2, "right",        "→"),
    (2, 0, "bottom-left", "↙"), (2, 1, "bottom", "↓"), (2, 2, "bottom-right", "↘"),
]


def _compute_rect(mx, my, mw, mh, position):
    """Return (x, y, w, h) for a named position inside a monitor rect."""
    w2, h2 = mw // 2, mh // 2
    return {
        "maximized":    (mx,       my,       mw,    mh),
        "top-left":     (mx,       my,       w2,    h2),
        "top":          (mx,       my,       mw,    h2),
        "top-right":    (mx + w2,  my,       w2,    h2),
        "left":         (mx,       my,       w2,    mh),
        "center":       (mx + mw // 4, my + mh // 4, w2, h2),
        "right":        (mx + w2,  my,       w2,    mh),
        "bottom-left":  (mx,       my + h2,  w2,    h2),
        "bottom":       (mx,       my + h2,  mw,    h2),
        "bottom-right": (mx + w2,  my + h2,  w2,    h2),
    }.get(position, (mx, my, mw, mh))


def _find_windows_by_pid(pid):
    """Return visible window handles belonging to a process ID."""
    windows = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_ulong, ctypes.c_long)

    def _cb(hwnd, _):
        if ctypes.windll.user32.IsWindowVisible(hwnd):
            buf = ctypes.wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(buf))
            if buf.value == pid:
                windows.append(hwnd)
        return True

    ctypes.windll.user32.EnumWindows(WNDENUMPROC(_cb), 0)
    return windows


# ── Codeword fullscreen animation ───────────────────────────────────────────────
class CodewordAnimation:
    """Epic particle + shockwave animation shown on one monitor."""

    DURATION = 4.2   # seconds
    FPS      = 60

    def __init__(self, root, x, y, w, h, word):
        self.root  = root
        self.win   = tk.Toplevel(root)
        self.win.geometry(f"{w}x{h}+{x}+{y}")
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg="black")

        self.cv = tk.Canvas(self.win, width=w, height=h,
                            bg="black", highlightthickness=0)
        self.cv.pack(fill="both", expand=True)

        self.w, self.h   = w, h
        self.cx, self.cy = w // 2, h // 2
        # Split long phrases into two balanced lines
        words = word.upper().split()
        if len(words) >= 3:
            mid = len(words) // 2
            self.line1 = " ".join(words[:mid])
            self.line2 = " ".join(words[mid:])
        elif len(words) == 2:
            self.line1, self.line2 = words[0], words[1]
        else:
            self.line1 = word.upper()
            self.line2 = ""
        self.word = word.upper()   # kept for subtitle
        self.start_time  = time.time()
        self.alive       = True

        # ── Particles ──────────────────────────────────────────────────────────
        self.parts = []
        COLORS = ["#30d158","#4ade80","#a3e635","#34d399","#6ee7b7","#ffffff","#bbf7d0"]
        for _ in range(150):
            ang   = random.uniform(0, 2 * math.pi)
            speed = random.uniform(3, 18)
            self.parts.append({
                "x": float(self.cx), "y": float(self.cy),
                "vx": math.cos(ang) * speed,
                "vy": math.sin(ang) * speed,
                "r":  random.uniform(2, 6),
                "col": random.choice(COLORS),
                "life": random.uniform(0.7, 1.0),
                "decay": random.uniform(0.008, 0.020),
            })
        self._tick()

    @staticmethod
    def _dim(hex_col, alpha):
        alpha = max(0.0, min(1.0, alpha))
        r = int(int(hex_col[1:3], 16) * alpha)
        g = int(int(hex_col[3:5], 16) * alpha)
        b = int(int(hex_col[5:7], 16) * alpha)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _tick(self):
        if not self.alive:
            return
        t = time.time() - self.start_time
        if t >= self.DURATION:
            self.win.destroy()
            return

        pct = t / self.DURATION
        cv  = self.cv
        cv.delete("all")

        # ── Background flash → dark ─────────────────────────────────────────────
        if t < 0.12:
            v   = int((1 - t / 0.12) * 255)
            bg  = f"#{v:02x}{v:02x}{v:02x}"
        elif pct > 0.82:
            v   = int((1 - (pct - 0.82) / 0.18) * 12)
            bg  = f"#{v:02x}{v:02x}{v:02x}"
        else:
            bg  = "#060606"
        cv.create_rectangle(0, 0, self.w, self.h, fill=bg, outline="")

        # ── Shockwave rings ─────────────────────────────────────────────────────
        for i in range(7):
            rt = t - i * 0.07
            if rt > 0:
                rad  = rt * 700
                alp  = max(0.0, 1.0 - rt * 0.55)
                if alp > 0 and rad < 3000:
                    col = self._dim("#30d158", alp)
                    wid = max(1, int(5 * alp))
                    cv.create_oval(self.cx - rad, self.cy - rad,
                                   self.cx + rad, self.cy + rad,
                                   outline=col, width=wid)

        # ── Scanlines (subtle CRT feel) ─────────────────────────────────────────
        for sy in range(0, self.h, 5):
            cv.create_line(0, sy, self.w, sy, fill="#000000", width=1)

        # ── Particles ──────────────────────────────────────────────────────────
        for p in self.parts:
            if p["life"] > 0:
                p["x"]  += p["vx"]
                p["y"]  += p["vy"]
                p["vy"] += 0.28   # gravity
                p["vx"] *= 0.982  # air drag
                p["life"] -= p["decay"]
                a = max(0.0, p["life"])
                r = p["r"] * a
                if r > 0.5:
                    col = self._dim(p["col"], a)
                    cv.create_oval(p["x"] - r, p["y"] - r,
                                   p["x"] + r, p["y"] + r,
                                   fill=col, outline="")

        # ── Display text ────────────────────────────────────────────────────────
        if t > 0.18:
            tt   = min(1.0, (t - 0.18) * 2.8)
            ease = 1 - (1 - tt) ** 3          # cubic ease-out
            fade = 1.0 if pct < 0.78 else max(0.0, (1 - pct) / 0.22)

            # Smaller base size when two lines so they both fit
            two_line = bool(self.line2)
            max_size  = min(self.w // (7 if two_line else 6), 90 if two_line else 110)
            size = int(14 + ease * (max_size - 14))

            if size > 0 and fade > 0:
                green    = self._dim("#30d158", fade)
                glow_col = self._dim("#a8ffc4", fade * 0.18)
                font     = ("Helvetica Neue", size, "bold")
                gap      = int(size * 1.15)   # line spacing

                # centres for one or two lines
                if two_line:
                    y1 = self.cy - gap // 2
                    y2 = self.cy + gap // 2
                else:
                    y1 = self.cy
                    y2 = None

                for line, ypos in [(self.line1, y1)] + ([(self.line2, y2)] if two_line else []):
                    # glow halo
                    for dx, dy in [(0,4),(0,-4),(4,0),(-4,0),(3,3),(-3,-3)]:
                        cv.create_text(self.cx + dx, ypos + dy,
                                       text=line, font=font, fill=glow_col)
                    # main text
                    cv.create_text(self.cx, ypos,
                                   text=line, font=font, fill=green)

                # "ACTIVATED" subtitle below
                if tt > 0.55 and size > 24:
                    sub_size = max(10, size // 5)
                    bottom_y = (y2 if two_line else y1) + int(size * 0.75)
                    cv.create_text(self.cx, bottom_y,
                                   text="ACTIVATED",
                                   font=("Helvetica Neue", sub_size, "bold"),
                                   fill=self._dim("#8e8e93", fade * 0.7))

        self.win.after(16, self._tick)

    def destroy(self):
        self.alive = False
        try:
            self.win.destroy()
        except Exception:
            pass


# ── Colour utilities (module-level) ──────────────────────────────────────────
def _hex_to_rgb(h: str) -> tuple:
    """'#rrggbb' → (r, g, b)"""
    return (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16))

def _hex_to_rgba(h: str, a: int = 255) -> tuple:
    r, g, b = _hex_to_rgb(h)
    return (r, g, b, a)

def _darken(hex_color: str, factor: float = 0.65) -> str:
    """Return a darker version of a hex colour."""
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return f"#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}"

def _blend_to_black(hex_color: str, frac: float) -> str:
    """Blend hex_color toward black by frac (0=full colour, 1=black)."""
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    a = max(0.0, 1.0 - frac)
    return f"#{int(r*a):02x}{int(g*a):02x}{int(b*a):02x}"


# ── PIL pill rendering helpers ────────────────────────────────────────────────
_pill_font_cache: dict = {}

def _get_pill_font(size: int) -> "ImageFont.FreeTypeFont":
    """Load a font for pill/overlay text rendering, cached by size."""
    if size in _pill_font_cache:
        return _pill_font_cache[size]
    candidates = [
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                fnt = ImageFont.truetype(p, size)
                _pill_font_cache[size] = fnt
                return fnt
            except Exception:
                pass
    fnt = ImageFont.load_default()
    _pill_font_cache[size] = fnt
    return fnt


def _pil_rrect(draw: "ImageDraw.ImageDraw", x0, y0, x1, y1, r,
               fill=None, outline=None, width=1):
    """Draw a filled and/or outlined rounded rectangle using PIL primitives."""
    # Clamp radius so it never exceeds half the smaller dimension
    r = max(0, min(r, (x1 - x0) // 2, (y1 - y0) // 2))
    if r == 0:
        if fill is not None:
            draw.rectangle([x0, y0, x1, y1], fill=fill)
        if outline is not None:
            draw.rectangle([x0, y0, x1, y1], outline=outline, width=width)
        return
    if fill is not None:
        draw.ellipse([x0, y0, x0+2*r, y0+2*r], fill=fill)
        draw.ellipse([x1-2*r, y0, x1, y0+2*r], fill=fill)
        draw.ellipse([x0, y1-2*r, x0+2*r, y1], fill=fill)
        draw.ellipse([x1-2*r, y1-2*r, x1, y1], fill=fill)
        draw.rectangle([x0+r, y0, x1-r, y1], fill=fill)
        draw.rectangle([x0, y0+r, x1, y1-r], fill=fill)
    if outline is not None:
        draw.arc([x0, y0, x0+2*r, y0+2*r], 180, 270, fill=outline, width=width)
        draw.arc([x1-2*r, y0, x1, y0+2*r], 270, 360, fill=outline, width=width)
        draw.arc([x0, y1-2*r, x0+2*r, y1], 90, 180, fill=outline, width=width)
        draw.arc([x1-2*r, y1-2*r, x1, y1], 0, 90, fill=outline, width=width)
        draw.line([x0+r, y0, x1-r, y0], fill=outline, width=width)
        draw.line([x0+r, y1, x1-r, y1], fill=outline, width=width)
        draw.line([x0, y0+r, x0, y1-r], fill=outline, width=width)
        draw.line([x1, y0+r, x1, y1-r], fill=outline, width=width)


def _draw_text_centered(draw, y, text, font, fill, canvas_w):
    """Draw text horizontally centered on canvas_w at given y."""
    try:
        bb = draw.textbbox((0, 0), text, font=font)
        tw = bb[2] - bb[0]
    except AttributeError:
        tw, _ = draw.textsize(text, font=font)
    draw.text(((canvas_w - tw) // 2, y), text, fill=fill, font=font)


class DictationApp:

    # ════════════════════════════════════════════════════════════════════════════
    def __init__(self):
        # ── App state ───────────────────────────────────────────────────────────
        self.model         = None
        self.model_loaded  = False
        self.recording     = False
        self.transcribing  = False
        self.audio_chunks  = []
        self.stream        = None
        self.amplitude     = 0.0
        self.kb            = KeyboardController()
        self.current_model = "base"
        self.anim_id       = None
        self.pill_bh       = [2.0] * PILL_N_BARS
        self.session_start = None
        self.mic_index_map = {}
        self._drag_x       = 0
        self._drag_y       = 0
        # mic test state
        self.testing_mic   = False
        self.test_stream   = None
        self.test_amp      = 0.0
        self.test_peak     = 0.0
        self.meter_anim_id = None
        # diagnostics
        self._last_key     = "— press any key —"
        self._diag_lines   = []
        self._diag_lbl     = None   # assigned after UI build
        self._lastkey_lbl  = None
        self._model_diag   = None
        # AI assistant
        self._ai_history      = []      # conversation turns for Gemini context
        self._ai_win          = None    # response popup Toplevel
        self._ai_popup_id     = None    # after() cancel handle
        self._ai_q_lbl        = None
        self._ai_a_lbl        = None
        self._ai_status_lbl   = None
        self._ai_speaking     = False
        self._tts_stop_event  = threading.Event()   # set to interrupt TTS
        self._tts_busy        = threading.Lock()    # prevents concurrent TTS calls
        self._ai_stop_btn     = None    # stop button widget (shown while speaking)
        # Character assistant
        self._char_win        = None    # floating character Toplevel
        self._char_canvas     = None
        self._char_anim_id    = None
        self._char_speaking   = False
        self._char_ripples    = []      # list of spawn timestamps for ripple rings
        self._char_last_ripple = 0.0
        self._char_blink_next  = 0.0   # set after UI builds
        # hotkey
        self._config          = self._load_config()
        self._hotkey_str      = self._config.get("hotkey_str",  "Key.alt_r")
        self._hotkey_display  = self._config.get("hotkey_display", "Right Alt")
        self.capturing_hotkey = False
        self._capture_btn     = None   # assigned after UI build

        # ── Persistence ─────────────────────────────────────────────────────────
        self.stats = self._load_stats()
        self.log   = self._load_log()

        # ── UI ──────────────────────────────────────────────────────────────────
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")
        self._build_root()
        self._build_pill()
        self._build_ai_popup()
        self._build_char_window()

        # ── Background work ─────────────────────────────────────────────────────
        threading.Thread(target=self._load_model, daemon=True).start()
        self._listener = pynput_keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release)
        self._listener.start()

        # Commented out for Eel integration (now called externally)
        # self.root.mainloop()

    # ════════════════════════════════════════════════════════════════════════════
    #  Persistence
    # ════════════════════════════════════════════════════════════════════════════
    def _load_stats(self):
        today = str(date.today())
        d = dict(date=today, words_today=0, sessions_today=0,
                 secs_today=0.0, words_total=0, sessions_total=0)
        try:
            with open(STATS_FILE) as f:
                s = json.load(f)
            if s.get("date") != today:
                s.update(date=today, words_today=0,
                         sessions_today=0, secs_today=0.0)
            return s
        except Exception:
            return d

    def _save_stats(self):
        try:
            with open(STATS_FILE, "w") as f:
                json.dump(self.stats, f)
        except Exception:
            pass

    def _load_log(self):
        try:
            with open(LOG_FILE) as f:
                return json.load(f)
        except Exception:
            return []

    def _save_log(self):
        try:
            with open(LOG_FILE, "w") as f:
                json.dump(self.log[-50:], f)
        except Exception:
            pass

    def _load_config(self):
        try:
            with open(CONFIG_FILE) as f:
                cfg = json.load(f)
        except Exception:
            cfg = {"hotkey_str": "Key.alt_r", "hotkey_display": "Right Alt"}

        # ── Migrate old apps format (list of strings → list of dicts) ───────────
        apps = cfg.get("codeword_apps", [])
        if apps and isinstance(apps[0], str):
            cfg["codeword_apps"] = [
                {"path": p, "monitor": 1, "position": "maximized"} for p in apps
            ]
        return cfg

    def _save_config(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self._config, f)
        except Exception:
            pass

    @staticmethod
    def _key_display(key):
        """Return a clean human-readable name for a pynput key."""
        s = str(key)
        if s in KEY_DISPLAY:
            return KEY_DISPLAY[s]
        # Regular character key — pynput wraps it in quotes e.g. "'a'"
        s = s.strip("'")
        return s.upper() if len(s) == 1 else s

    # ════════════════════════════════════════════════════════════════════════════
    #  Root window & layout
    # ════════════════════════════════════════════════════════════════════════════
    def _build_root(self):
        W, H = 740, 540
        self.root = ctk.CTk()
        self.root.title("AI Dictator")
        self.root.geometry(f"{W}x{H}")
        self.root.resizable(False, False)
        self.root.configure(fg_color=WIN_BG)
        self.root.overrideredirect(True)

        # Centre on screen
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")

        # Apply DWM glass + Win11 rounding + taskbar icon once window is mapped
        _icon_path = os.path.join(HERE, "icon.ico")

        def _glass_init():
            hwnd = _get_root_hwnd(self.root)
            # Dark acrylic — deep navy tint at 98% opacity
            _apply_acrylic(hwnd, tint=0xFA1C1C1E)
            _apply_win11_style(hwnd)
            # Force window into taskbar + set icon (overrideredirect hides it otherwise)
            if os.path.exists(_icon_path):
                _apply_taskbar_icon(hwnd, _icon_path)

        self.root.after(200, _glass_init)

        self._base_frame = self.root   # compatibility alias

        # ── Custom title bar ─────────────────────────────────────────────────────
        self._build_titlebar()

        # ── Body: sidebar + content ──────────────────────────────────────────────
        body = tk.Frame(self.root, bg=WIN_BG)
        body.pack(fill="both", expand=True)

        self._build_sidebar(body)
        self._build_content(body)

        # Start on Dashboard
        self._show_page("stats")

    def _build_titlebar(self):
        """Unified title bar — one clean horizontal plane (Rule 2)."""
        tb = tk.Frame(self._base_frame, bg=WIN_BG, height=44)
        tb.pack(fill="x")
        tb.pack_propagate(False)

        # ── Traffic lights (left, 14 px from edge) ───────────────────────────────
        tl = tk.Frame(tb, bg=WIN_BG)
        tl.place(x=G2, rely=0.5, anchor="w")

        def _make_tl(parent, color, cmd):
            cv = tk.Canvas(parent, width=13, height=13, bg=WIN_BG,
                           highlightthickness=0, cursor="hand2")
            cv.pack(side="left", padx=3)
            dot = cv.create_oval(1, 1, 12, 12, fill=color, outline="")
            # Dim on leave, restore on enter
            cv.bind("<Enter>", lambda e: cv.itemconfig(dot, fill=color))
            cv.bind("<Leave>", lambda e: cv.itemconfig(dot, fill=_dim_hex(color)))
            if cmd:
                cv.bind("<Button-1>", lambda e: cmd())
            return cv

        def _dim_hex(h):
            r, g, b = int(h[1:3],16), int(h[3:5],16), int(h[5:7],16)
            r, g, b = int(r*0.55), int(g*0.55), int(b*0.55)
            return f"#{r:02x}{g:02x}{b:02x}"

        _make_tl(tl, TL_RED,    self.root.destroy)
        _make_tl(tl, TL_YELLOW, None)
        _make_tl(tl, TL_GREEN,  None)

        # ── App name — vertically centred ────────────────────────────────────────
        tk.Label(tb, text="Sovereign AI v3.4 ACTIVE",
                 bg=WIN_BG, fg=T_TER,
                 font=("Helvetica Neue", 12, "bold")).place(relx=0.5, rely=0.5, anchor="center")

        # ── Status indicator (right side) — dot + badge text ─────────────────────
        status_row = tk.Frame(tb, bg=WIN_BG)
        status_row.place(relx=1.0, rely=0.5, anchor="e", x=-G2)

        self._dot_cv = tk.Canvas(status_row, width=9, height=9, bg=WIN_BG,
                                 highlightthickness=0)
        self._dot_cv.pack(side="left", padx=(0, 5))
        self._dot = self._dot_cv.create_oval(1, 1, 8, 8,
                                             fill=T_TER, outline="")

        self._st_title = tk.Label(status_row, text="Loading…",
                                  bg=WIN_BG, fg=T_PRI,
                                  font=("Helvetica Neue", 11, "bold"))
        self._st_title.pack(side="left")

        self._st_sub = tk.Label(status_row, text="",
                                bg=WIN_BG, fg=T_SEC,
                                font=F_CAPTION)
        self._st_sub.pack(side="left", padx=(4, 0))

        # Whisper model badge
        self._badge = tk.Label(tb, text="loading…",
                               bg=BTN_BG, fg=T_TER,
                               font=F_CAPTION,
                               padx=G, pady=2,
                               relief="flat")
        self._badge.place(relx=0.5, rely=0.5, anchor="center", y=0, x=140)

        # Thin bottom edge divider
        tk.Frame(self._base_frame, bg=BORDER, height=1).pack(fill="x")

        # Drag anywhere on the titlebar
        for w in (tb,):
            w.bind("<ButtonPress-1>",  self._drag_start)
            w.bind("<B1-Motion>",      self._drag_move)

    def _drag_start(self, e):
        self._drag_x = e.x_root - self.root.winfo_x()
        self._drag_y = e.y_root - self.root.winfo_y()

    def _drag_move(self, e):
        self.root.geometry(f"+{e.x_root - self._drag_x}+{e.y_root - self._drag_y}")

    # ════════════════════════════════════════════════════════════════════════════
    #  Sidebar — Source-List style (Rule 1 + Rule 6)
    # ════════════════════════════════════════════════════════════════════════════
    def _build_sidebar(self, parent):
        sb = tk.Frame(parent, bg=SIDEBAR_BG, width=188)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        # 1-px frosted divider on the right
        tk.Frame(parent, bg=BORDER, width=1).pack(side="left", fill="y")

        # Nav items: (page-key, Segoe MDL2 icon char, display label)
        nav_items = [
            ("stats",      "🧠", "Intelligence"),
            ("dictations", "🎤", "Vocalize"),
            ("ai",         "💾", "Archives"),
            ("codeword",   "🛡", "Protocols"),
            ("settings",   "⚙",  "Settings"),
        ]

        self._nav_btns    = {}
        self._nav_selected = None

        # Section micro-label
        tk.Frame(sb, bg=SIDEBAR_BG, height=G3).pack()
        tk.Label(sb, text="NAVIGATION",
                 bg=SIDEBAR_BG, fg=T_TER,
                 font=("Helvetica Neue", 8, "bold"),
                 anchor="w").pack(fill="x", padx=G3, pady=(0, G))

        for key, icon, label in nav_items:
            # Outer hitbox — full width, hand cursor
            outer = tk.Frame(sb, bg=SIDEBAR_BG, cursor="hand2")
            outer.pack(fill="x", padx=G, pady=1)

            # Rounded-rect "pill" — coloured when selected, transparent otherwise
            # Simulated via a padded inner frame (rounded look via ipadx/ipady)
            pill = ctk.CTkFrame(outer, fg_color=SIDEBAR_BG, corner_radius=12)
            pill.pack(fill="x", ipadx=0, ipady=4)

            # Left accent bar (3 px) — filled with ACCENT when selected
            bar = tk.Frame(pill, bg=SIDEBAR_BG, width=3)
            bar.pack(side="left", fill="y")

            # Icon — outlined when inactive, filled feel when selected
            icon_lbl = tk.Label(pill, text=icon, bg=SIDEBAR_BG,
                                fg=T_TER,
                                font=("Segoe UI Symbol", 14), width=2,
                                anchor="center")
            icon_lbl.pack(side="left", padx=(4, 4), pady=6)

            # Label text
            text_lbl = tk.Label(pill, text=label, bg=SIDEBAR_BG,
                                fg=T_SEC,
                                font=("Helvetica Neue", 12))
            text_lbl.pack(side="left", pady=6)

            all_w = [outer, pill, bar, icon_lbl, text_lbl]

            # Left-click — navigate
            for w in all_w:
                w.bind("<Button-1>", lambda e, k=key: self._show_page(k))

            # Right-click — context menu on nav item (Rule 9)
            def _nav_ctx(event, k=key, lbl=label):
                self._context_menu(event, [
                    (f"Open {lbl}", lambda k2=k: self._show_page(k2)),
                ])
            for w in all_w:
                w.bind("<Button-3>", _nav_ctx)

            # Hover-in: subtly highlight unselected items
            def _hov_in(e, k=key, ws=all_w):
                if k != self._nav_selected:
                    bg = "#3a3a3c"
                    for w in ws:
                        try: w.configure(bg=bg)
                        except Exception: pass

            # Hover-out: restore unselected state
            def _hov_out(e, k=key, ws=all_w):
                if k != self._nav_selected:
                    for w in ws:
                        try: w.configure(bg=SIDEBAR_BG)
                        except Exception: pass

            for w in all_w:
                w.bind("<Enter>", _hov_in)
                w.bind("<Leave>", _hov_out)

            self._nav_btns[key] = {
                "outer": outer, "pill": pill, "bar": bar,
                "icon": icon_lbl, "text": text_lbl, "all": all_w
            }

    def _select_nav(self, key):
        """Apply source-list selection: rounded highlight + accent bar (Rule 6)."""
        for k, item in self._nav_btns.items():
            sel = (k == key)
            bg      = ACCENT_LITE  if sel else SIDEBAR_BG
            bar_bg  = ACCENT       if sel else SIDEBAR_BG
            fg_icon = ACCENT       if sel else T_TER
            fg_text = ACCENT_TEXT  if sel else T_SEC
            font    = ("Helvetica Neue", 12, "bold") if sel else ("Helvetica Neue", 12)
            try:
                item["pill"].configure(fg_color=bg)
                for w in [item["outer"], item["bar"]]:
                    w.configure(bg=bg)
                item["bar"].configure(bg=bar_bg)
                item["icon"].configure(fg=fg_icon, bg=bg)
                item["text"].configure(fg=fg_text, bg=bg, font=font)
            except Exception:
                pass
        self._nav_selected = key

    # ════════════════════════════════════════════════════════════════════════════
    #  Content area
    # ════════════════════════════════════════════════════════════════════════════
    def _build_content(self, parent):
        self._content = tk.Frame(parent, bg=CONTENT_BG)
        self._content.pack(side="left", fill="both", expand=True)

        # Page frames (all stacked, only one visible at a time)
        self._pages = {}
        self._pages["stats"]      = self._make_stats_page()
        self._pages["dictations"] = self._make_dictations_page()
        self._pages["ai"]         = self._make_assistant_page()
        self._pages["codeword"]   = self._make_codeword_page()
        self._pages["settings"]   = self._make_settings_page()

    def _show_page(self, key):
        for k, frame in self._pages.items():
            frame.place_forget()
        self._pages[key].place(x=0, y=0, relwidth=1, relheight=1)
        self._select_nav(key)
        if key == "stats":
            self._refresh_stats_page()

    # ════════════════════════════════════════════════════════════════════════════
    #  Stats / Dashboard page
    # ════════════════════════════════════════════════════════════════════════════
    def _make_stats_page(self):
        page = ctk.CTkFrame(self._content, fg_color=CONTENT_BG)

        # ── 1. Integrated Pill Header ─────────────────────────────────────────────
        top_card = ctk.CTkFrame(page, fg_color=CARD_BG, corner_radius=25)
        top_card.pack(fill="x", padx=24, pady=(20, 14), ipady=20)

        ctk.CTkLabel(top_card, text="Awaiting Command", text_color="#ffffff", font=ctk.CTkFont("Helvetica Neue", 14, "bold")).pack(pady=(15, 0))
        
        # Audio Visualizer Canvas
        self._dash_pill_cv = tk.Canvas(top_card, width=PILL_W, height=PILL_H, bg=CARD_BG, highlightthickness=0)
        self._dash_pill_cv.pack(pady=5)
        self._dash_pill_bg_img = ImageTk.PhotoImage(Image.new("RGB", (PILL_W, PILL_H), _hex_to_rgb(CARD_BG)))
        self._dash_pill_cv_id = self._dash_pill_cv.create_image(0, 0, anchor="nw", image=self._dash_pill_bg_img)

        ctk.CTkLabel(top_card, text="MONITORING ACTIVE SESSION 092", text_color="#30d158", font=ctk.CTkFont("Helvetica Neue", 13, "bold")).pack(pady=(0, 15))

        # ── 2. Middle Row: Stats + Voice Profile ──────────────────────────────────
        mid_row = tk.Frame(page, bg=CONTENT_BG)
        mid_row.pack(fill="x", padx=24)

        # Words
        w_card = self._card(mid_row)
        w_card.pack(side="left", expand=True, fill="both", padx=(0, 8))
        self._donut_words = DonutChart(w_card, size=150, bg=CARD_BG)
        self._donut_words.pack(pady=20)

        # Sessions
        s_card = self._card(mid_row)
        s_card.pack(side="left", expand=True, fill="both", padx=(8, 8))
        self._donut_sessions = DonutChart(s_card, size=150, bg=CARD_BG)
        self._donut_sessions.pack(pady=20)

        # Active Voice Profile (Sovereign Theme)
        v_card = self._card(mid_row)
        v_card.pack(side="left", expand=True, fill="both", padx=(8, 0))
        tk.Frame(v_card, bg=CARD_BG, height=20).pack()  # Spacer
        ctk.CTkLabel(v_card, text="ACTIVE VOICE PROFILE", text_color="#98989e", font=ctk.CTkFont("Helvetica Neue", 12, "bold")).pack(anchor="w", padx=20)
        
        v_inner = tk.Frame(v_card, bg=CARD_BG)
        v_inner.pack(fill="both", expand=True, padx=20, pady=15)
        
        av_cv = tk.Canvas(v_inner, width=50, height=50, bg=CARD_BG, highlightthickness=0)
        av_cv.pack(side="left", padx=(0,14))
        av_cv.create_oval(2, 2, 48, 48, outline="#30d158", width=2)
        
        vtext = tk.Frame(v_inner, bg=CARD_BG)
        vtext.pack(side="left")
        ctk.CTkLabel(vtext, text="Ares Core", text_color="#e5e5e5", font=ctk.CTkFont("Helvetica Neue", 18, "bold")).pack(anchor="w")
        ctk.CTkLabel(vtext, text="Authoritative / Deep", text_color="#98989e", font=ctk.CTkFont("Helvetica Neue", 11)).pack(anchor="w")

        # ── 3. Bottom Row: Intercepts + Engine ────────────────────────────────────
        bot_row = tk.Frame(page, bg=CONTENT_BG)
        bot_row.pack(fill="both", expand=True, padx=24, pady=14)

        # Intercepts Left
        int_card = self._card(bot_row)
        int_card.pack(side="left", fill="both", expand=True, padx=(0, 8))
        tk.Frame(int_card, bg=CARD_BG, height=15).pack()
        ctk.CTkLabel(int_card, text="RECENT INTELLIGENCE INTERCEPTS", text_color="#98989e", font=ctk.CTkFont("Helvetica Neue", 12, "bold")).pack(anchor="w", padx=20, pady=5)
        self._log_inner = tk.Frame(int_card, bg=CARD_BG)
        self._log_inner.pack(fill="both", expand=True, padx=16, pady=5)

        # Engine Right
        eng_card = tk.Frame(bot_row, bg=CONTENT_BG)
        eng_card.pack(side="left", fill="both", padx=(8, 0))
        
        te_card = self._card(eng_card)
        te_card.pack(fill="x", pady=(0, 7))
        tk.Frame(te_card, bg=CARD_BG, height=10).pack()
        ctk.CTkLabel(te_card, text="TRANSCRIPTION ENGINE", text_color="#98989e", font=ctk.CTkFont("Helvetica Neue", 11, "bold")).pack(anchor="w", padx=16, pady=5)
        
        opts = tk.Frame(te_card, bg=CARD_BG)
        opts.pack(fill="x", padx=16, pady=(5,15))
        for o in ["Tiny", "Base", "Small", "Medium"]:
            bgc = "#30d158" if o == "Small" else "#2c2c2e"
            fgc = "#111111" if o == "Small" else "#a0a0a0"
            ctk.CTkLabel(opts, text=o, fg_color=bgc, text_color=fgc, font=ctk.CTkFont("Helvetica Neue", 11, "bold"), corner_radius=10).pack(side="left", padx=4)

        vm_card = self._card(eng_card)
        vm_card.pack(fill="x", pady=(7, 0), expand=True)
        tk.Frame(vm_card, bg=CARD_BG, height=10).pack()
        ctk.CTkLabel(vm_card, text="CORE VOICE MODULATION", text_color="#98989e", font=ctk.CTkFont("Helvetica Neue", 11, "bold")).pack(anchor="w", padx=16, pady=5)
        
        def _slider(parent, text, val):
            f = tk.Frame(parent, bg=CARD_BG)
            f.pack(fill="x", padx=16, pady=8)
            info = tk.Frame(f, bg=CARD_BG)
            info.pack(fill="x")
            ctk.CTkLabel(info, text=text, text_color="#e5e5e5", font=ctk.CTkFont("Helvetica Neue", 10, "bold")).pack(side="left")
            ctk.CTkLabel(info, text=f"{val}%", text_color="#30d158", font=ctk.CTkFont("Helvetica Neue", 10, "bold")).pack(side="right")
            # Custom slider visual
            bar = tk.Canvas(f, height=6, bg="#2c2c2e", highlightthickness=0)
            bar.pack(fill="x", pady=4)
            bar.bind("<Configure>", lambda e, v=val: bar.create_rectangle(0, 0, (e.width * v)//100, 6, fill="#30d158", width=0))
            
        _slider(vm_card, "AUTHORITY BIAS", 88)
        _slider(vm_card, "PITCH VARIANCE", 12)

        return page

    def _refresh_stats_page(self):
        # Donuts
        tw = self.stats.get("words_total", 0)
        max_w = max(tw, 11000)
        self._donut_words.render(f"{max(75, int((tw/max_w)*100))}%", "Words Today",
                                 0.75, "#30d158")

        ts = self.stats.get("sessions_total", 0)
        max_s = max(ts, 50)
        self._donut_sessions.render(f"45", "Session Length",
                                    0.45, "#30d158")

        # Recent log list
        for w in self._log_inner.winfo_children():
            w.destroy()

        entries = list(reversed(self.log[-4:]))
        if not entries:
            entries = [{"time":"12:45:01", "text":"Global Network Latency Check"}, 
                       {"time":"12:40:22", "text":"Whisper Model Fine-tuning Sync"}]
            
        for i, e in enumerate(entries):
            snippet = e["text"][:38] + ("…" if len(e["text"]) > 38 else "")
            cell = tk.Frame(self._log_inner, bg=CARD_BG)
            cell.pack(fill="x", pady=8, padx=4)
            
            # Green dot
            dot = tk.Canvas(cell, width=8, height=8, bg=CARD_BG, highlightthickness=0)
            dot.pack(side="left", padx=(0,10))
            dot.create_oval(0,0,8,8, fill="#30d158", outline="")
            
            ctk.CTkLabel(cell, text=snippet, text_color="#e5e5e5", font=ctk.CTkFont("Helvetica Neue", 12)).pack(side="left")
            ctk.CTkLabel(cell, text=e["time"], text_color="#555555", font=ctk.CTkFont("Helvetica Neue", 11)).pack(side="right")

    # ════════════════════════════════════════════════════════════════════════════
    #  Dictations page
    # ════════════════════════════════════════════════════════════════════════════
    def _make_dictations_page(self):
        page = tk.Frame(self._content, bg=CONTENT_BG)

        tk.Label(page, text="Dictations", bg=CONTENT_BG,
                 fg=TEXT_MAIN,
                 font=("Helvetica Neue", 22, "bold")).pack(
            anchor="w", padx=24, pady=(20, 14))

        # Scrollable list
        scroll_frame = ctk.CTkScrollableFrame(
            page, fg_color=CONTENT_BG,
            scrollbar_button_color=BTN_BG,
            scrollbar_button_hover_color=BTN_HOVER)
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self._dict_scroll = scroll_frame
        self._refresh_dictations_page()

        return page

    def _refresh_dictations_page(self):
        for w in self._dict_scroll.winfo_children():
            w.destroy()

        entries = list(reversed(self.log))
        if not entries:
            tk.Label(self._dict_scroll,
                     text="No dictations yet — hold your hotkey and speak!",
                     bg=CONTENT_BG, fg=T_TER,
                     font=F_LABEL).pack(pady=G5)
            return

        for idx, e in enumerate(entries):
            # ── Card ──────────────────────────────────────────────────────────────
            card = self._card(self._dict_scroll)
            card._shadow.pack(fill="x", pady=(0, G), padx=2)

            inner = tk.Frame(card, bg=CARD_BG)
            inner.pack(fill="x", padx=G2, pady=G)

            # Top row: timestamp (left)  +  action buttons (right, hidden by default)
            top_row = tk.Frame(inner, bg=CARD_BG)
            top_row.pack(fill="x")

            time_lbl = tk.Label(top_row, text=e["time"],
                                bg=CARD_BG, fg=T_TER, font=F_CAPTION)
            time_lbl.pack(side="left", anchor="w")

            # ── Action buttons — hover-to-reveal (Rule 8) ─────────────────────────
            actions = tk.Frame(top_row, bg=CARD_BG)
            actions.pack(side="right")

            def _copy(t=e["text"]):
                pyperclip.copy(t)

            def _delete(i=idx, entry=e):
                try:
                    self.log.remove(entry)
                except ValueError:
                    pass
                self._save_log()
                self.root.after(0, self._refresh_dictations_page)

            copy_btn = tk.Label(actions, text="⎘ Copy",
                                bg=ACCENT_LITE, fg=ACCENT_TEXT,
                                font=F_CAPTION, padx=G, pady=2, cursor="hand2")
            copy_btn.pack(side="left", padx=(0, 4))
            copy_btn.bind("<Button-1>", lambda ev, fn=_copy: fn())

            del_btn = tk.Label(actions, text="✕",
                               bg="#3d1515", fg="#cc2222",
                               font=F_CAPTION, padx=G, pady=2, cursor="hand2")
            del_btn.pack(side="left")
            del_btn.bind("<Button-1>", lambda ev, fn=_delete: fn())

            # Start hidden; reveal on card hover
            actions.pack_forget()

            # Body text
            text_lbl = tk.Label(inner, text=e["text"],
                                bg=CARD_BG, fg=T_PRI,
                                font=F_BODY,
                                wraplength=490, justify="left", anchor="w")
            text_lbl.pack(anchor="w", pady=(4, 0))

            # ── Hover-to-reveal (Rule 8) on entire card ────────────────────────────
            all_widgets = [card, inner, top_row, time_lbl, text_lbl]
            def _reveal(e, act=actions):
                act.pack(side="right")
            def _conceal(e, act=actions):
                act.pack_forget()
            for w in all_widgets:
                w.bind("<Enter>", _reveal, add="+")
                w.bind("<Leave>", _conceal, add="+")

            # ── Right-click context menu (Rule 9) ──────────────────────────────────
            def _ctx(event, cp=_copy, dl=_delete):
                self._context_menu(event, [
                    ("⎘  Copy text",   cp),
                    ("-", None),
                    ("✕  Delete",      dl),
                ])
            for w in all_widgets + [copy_btn, del_btn]:
                w.bind("<Button-3>", _ctx, add="+")

    # ════════════════════════════════════════════════════════════════════════════
    #  AI Assistant page
    # ════════════════════════════════════════════════════════════════════════════
    def _make_assistant_page(self):
        page = tk.Frame(self._content, bg=CONTENT_BG)

        tk.Label(page, text="🤖  AI Assistant", bg=CONTENT_BG,
                 fg=TEXT_MAIN,
                 font=("Helvetica Neue", 22, "bold")).pack(
            anchor="w", padx=24, pady=(20, 8))

        body = ctk.CTkScrollableFrame(
            page, fg_color=CONTENT_BG,
            scrollbar_button_color=BTN_BG,
            scrollbar_button_hover_color=BTN_HOVER)
        body.pack(fill="both", expand=True)

        # ── How it works ─────────────────────────────────────────────────────────
        info = self._card(body)
        info.pack(fill="x", padx=24, pady=(4, 12))
        ii = tk.Frame(info, bg=CARD_BG)
        ii.pack(fill="x", padx=16, pady=12)

        tk.Label(ii, text="HOW IT WORKS", bg=CARD_BG, fg=LABEL_SMALL,
                 font=("Helvetica Neue", 10, "bold")).pack(anchor="w")
        tk.Label(ii,
                 text='Hold your hotkey and speak your wake word followed by a question.\n'
                      'Example: "assistant, what\'s the capital of France?"\n\n'
                      '✍️  "write a prompt, [your idea]"  →  Gemini writes it and pastes at cursor\n'
                      '🛠  "fix that"  →  rewrites your last text for clarity/grammar\n'
                      '🎨  "make that formal/shorter/an email/bullet points"  →  rewrites clipboard\n'
                      '🔊  "read this"  →  reads whatever is in your clipboard aloud\n'
                      '⚡  Voice macros  →  say a saved word to instantly paste any text snippet',
                 bg=CARD_BG, fg=TEXT_SUB,
                 font=("Helvetica Neue", 11), justify="left").pack(
            anchor="w", pady=(6, 0))

        # ── Wake word ─────────────────────────────────────────────────────────────
        ww_card = self._card(body)
        ww_card.pack(fill="x", padx=24, pady=(0, 12))
        ww_inner = tk.Frame(ww_card, bg=CARD_BG)
        ww_inner.pack(fill="x", padx=16, pady=14)

        tk.Label(ww_inner, text="WAKE WORD", bg=CARD_BG, fg=LABEL_SMALL,
                 font=("Helvetica Neue", 10, "bold")).pack(anchor="w")
        tk.Label(ww_inner,
                 text="Say this at the start of your dictation to activate AI mode.",
                 bg=CARD_BG, fg=TEXT_SUB, font=("Helvetica Neue", 11)).pack(
            anchor="w", pady=(4, 10))

        ww_row = tk.Frame(ww_inner, bg=CARD_BG)
        ww_row.pack(fill="x")

        self._ai_ww_var = tk.StringVar(
            value=self._config.get("ai_wake_word", "assistant"))
        ww_entry = tk.Entry(
            ww_row, textvariable=self._ai_ww_var,
            font=("Helvetica Neue", 16, "bold"),
            fg=AI_BLUE, bg="#1c2a3a",
            relief="flat", bd=0,
            insertbackground=AI_BLUE, width=18)
        ww_entry.pack(side="left", ipady=8, ipadx=10)

        ww_save = tk.Label(ww_row, text="  Save  ",
                           bg="#1c2a3a", fg=AI_BLUE,
                           font=("Helvetica Neue", 12, "bold"),
                           cursor="hand2", padx=4, pady=8)
        ww_save.pack(side="left", padx=(10, 0))
        ww_save.bind("<Button-1>", lambda e: self._save_ai_settings())

        self._ai_ww_saved = tk.Label(ww_inner, text="", bg=CARD_BG, fg=GREEN_DONUT,
                                     font=("Helvetica Neue", 11))
        self._ai_ww_saved.pack(anchor="w", pady=(6, 0))

        # ── Gemini API key ────────────────────────────────────────────────────────
        api_card = self._card(body)
        api_card.pack(fill="x", padx=24, pady=(0, 12))
        api_inner = tk.Frame(api_card, bg=CARD_BG)
        api_inner.pack(fill="x", padx=16, pady=14)

        tk.Label(api_inner, text="GEMINI API KEY", bg=CARD_BG, fg=LABEL_SMALL,
                 font=("Helvetica Neue", 10, "bold")).pack(anchor="w")
        tk.Label(api_inner,
                 text="Free at aistudio.google.com → Get API key. Stored locally only.",
                 bg=CARD_BG, fg=TEXT_SUB, font=("Helvetica Neue", 11)).pack(
            anchor="w", pady=(4, 10))

        key_row = tk.Frame(api_inner, bg=CARD_BG)
        key_row.pack(fill="x")

        self._ai_key_var  = tk.StringVar(
            value=self._config.get("gemini_api_key", ""))
        self._ai_key_show = tk.BooleanVar(value=False)

        self._ai_key_entry = tk.Entry(
            key_row, textvariable=self._ai_key_var,
            show="•",
            font=("Helvetica Neue", 13),
            fg=TEXT_MAIN, bg="#3a3a3c",
            relief="flat", bd=0,
            insertbackground=TEXT_MAIN, width=28)
        self._ai_key_entry.pack(side="left", ipady=7, ipadx=8)

        def _toggle_key_vis():
            show = self._ai_key_show.get()
            self._ai_key_show.set(not show)
            self._ai_key_entry.configure(show="" if not show else "•")
            eye_btn.configure(text="🙈" if not show else "👁")
        eye_btn = tk.Label(key_row, text="👁", bg=CARD_BG,
                           font=("Segoe UI Emoji", 14), cursor="hand2")
        eye_btn.pack(side="left", padx=(6, 0))
        eye_btn.bind("<Button-1>", lambda e: _toggle_key_vis())

        key_save = tk.Label(key_row, text="  Save  ",
                            bg="#1c2a3a", fg=AI_BLUE,
                            font=("Helvetica Neue", 12, "bold"),
                            cursor="hand2", padx=4, pady=8)
        key_save.pack(side="left", padx=(8, 0))
        key_save.bind("<Button-1>", lambda e: self._save_ai_settings())

        self._ai_key_status = tk.Label(api_inner, text="", bg=CARD_BG,
                                       fg=TEXT_SUB, font=("Helvetica Neue", 11))
        self._ai_key_status.pack(anchor="w", pady=(6, 0))
        # Show status based on whether key exists
        if self._config.get("gemini_api_key", ""):
            self._ai_key_status.configure(text="✅  API key saved", fg=GREEN_DONUT)

        # ── Gemini model ──────────────────────────────────────────────────────────
        mdl_card = self._card(body)
        mdl_card.pack(fill="x", padx=24, pady=(0, 12))
        mdl_inner = tk.Frame(mdl_card, bg=CARD_BG)
        mdl_inner.pack(fill="x", padx=16, pady=14)

        tk.Label(mdl_inner, text="GEMINI MODEL", bg=CARD_BG, fg=LABEL_SMALL,
                 font=("Helvetica Neue", 10, "bold")).pack(anchor="w")

        mdl_btn_row = tk.Frame(mdl_inner, bg=CARD_BG)
        mdl_btn_row.pack(fill="x", pady=(10, 0))

        self._ai_model_btns = {}
        cur_model = self._config.get("gemini_model", "gemini-1.5-flash")
        for label, key in GEMINI_MODELS:
            active = (key == cur_model)
            frame = tk.Frame(mdl_btn_row,
                             bg="#1c2a3a" if active else BTN_BG,
                             relief="flat", bd=0,
                             highlightbackground="#a8c4f0" if active else DIVIDER,
                             highlightthickness=1,
                             cursor="hand2")
            frame.pack(side="left", padx=(0, 8), pady=2)

            lbl = tk.Label(frame, text=label,
                           bg="#1c2a3a" if active else BTN_BG,
                           fg=AI_BLUE if active else TEXT_MAIN,
                           font=("Helvetica Neue", 11,
                                 "bold" if active else "normal"),
                           padx=10, pady=6)
            lbl.pack()
            self._ai_model_btns[key] = (frame, lbl)

            def on_mdl(e, k=key):
                self._config["gemini_model"] = k
                self._save_config()
                for mk, (mf, ml) in self._ai_model_btns.items():
                    sel = (mk == k)
                    mf.configure(bg="#1c2a3a" if sel else BTN_BG,
                                 highlightbackground="#a8c4f0" if sel else DIVIDER)
                    ml.configure(bg="#1c2a3a" if sel else BTN_BG,
                                 fg=AI_BLUE if sel else TEXT_MAIN,
                                 font=("Helvetica Neue", 11,
                                       "bold" if sel else "normal"))
            frame.bind("<Button-1>", on_mdl)
            lbl.bind("<Button-1>", on_mdl)

        # ── Voice engine ──────────────────────────────────────────────────────────
        tts_card = self._card(body)
        tts_card.pack(fill="x", padx=24, pady=(0, 12))
        tts_inner = tk.Frame(tts_card, bg=CARD_BG)
        tts_inner.pack(fill="x", padx=16, pady=14)

        # Header row: label + status badge
        tts_hdr = tk.Frame(tts_inner, bg=CARD_BG)
        tts_hdr.pack(fill="x")
        tk.Label(tts_hdr, text="VOICE (TEXT-TO-SPEECH)", bg=CARD_BG,
                 fg=LABEL_SMALL, font=("Helvetica Neue", 10, "bold")).pack(side="left")
        if _EDGE_TTS_AVAILABLE and _PYGAME_AVAILABLE:
            tk.Label(tts_hdr, text=" ✦ Neural  ", bg=ACCENT, fg="#ffffff",
                     font=("Helvetica Neue", 9, "bold"), padx=4, pady=1).pack(
                side="left", padx=(8, 0))
        elif _TTS_AVAILABLE:
            tk.Label(tts_hdr, text=" SAPI ", bg=BTN_BG, fg=T_SEC,
                     font=("Helvetica Neue", 9), padx=4, pady=1).pack(
                side="left", padx=(8, 0))
        else:
            tk.Label(tts_hdr, text=" No TTS ", bg="#3d1515", fg="#ff6b6b",
                     font=("Helvetica Neue", 9), padx=4, pady=1).pack(
                side="left", padx=(8, 0))

        if _EDGE_TTS_AVAILABLE and _PYGAME_AVAILABLE:
            # ── Edge TTS voice picker ─────────────────────────────────────────
            tk.Label(tts_inner,
                     text="Microsoft Neural voices — crystal-clear, 100% free, requires internet.",
                     bg=CARD_BG, fg=TEXT_SUB,
                     font=("Helvetica Neue", 11)).pack(anchor="w", pady=(6, 10))

            cur_ev = self._config.get("edge_voice", "en-US-AriaNeural")
            # Map ID → display name for initial value
            cur_ev_name = next(
                (n for n, i in EDGE_VOICES if i == cur_ev), EDGE_VOICE_NAMES[0])
            self._edge_voice_var = ctk.StringVar(value=cur_ev_name)

            def _on_edge_voice(name):
                # Resolve display name → voice ID
                vid = next((i for n, i in EDGE_VOICES if n == name),
                           "en-US-AriaNeural")
                self._config["edge_voice"] = vid
                self._save_config()

            edge_menu = ctk.CTkOptionMenu(
                tts_inner, values=EDGE_VOICE_NAMES,
                variable=self._edge_voice_var,
                fg_color=BTN_BG,
                button_color=ACCENT_DIM,
                button_hover_color=ACCENT,
                dropdown_fg_color=CARD_BG,
                dropdown_hover_color=CARD_HOVER,
                text_color=TEXT_MAIN,
                font=ctk.CTkFont(size=12),
                corner_radius=10, height=36,
                command=_on_edge_voice
            )
            edge_menu.pack(fill="x", pady=(0, 10))

        elif _TTS_AVAILABLE:
            # ── pyttsx3 fallback voice picker ─────────────────────────────────
            tk.Label(tts_inner,
                     text="Windows SAPI voices. For richer neural voices install edge-tts.",
                     bg=CARD_BG, fg=TEXT_SUB,
                     font=("Helvetica Neue", 11)).pack(anchor="w", pady=(6, 10))

            voices = self._get_tts_voices()
            cur_voice = self._config.get("tts_voice", voices[0] if voices else "")
            self._tts_voice_var = ctk.StringVar(value=cur_voice)
            voice_menu = ctk.CTkOptionMenu(
                tts_inner, values=voices,
                variable=self._tts_voice_var,
                fg_color=BTN_BG,
                button_color="#1c2a3a",
                button_hover_color="#a8c4f0",
                dropdown_fg_color=CARD_BG,
                dropdown_hover_color="#1c2a3a",
                text_color=TEXT_MAIN,
                font=ctk.CTkFont(size=12),
                corner_radius=10, height=36,
                command=lambda v: self._save_ai_settings()
            )
            voice_menu.pack(fill="x", pady=(0, 10))

        else:
            tk.Label(tts_inner,
                     text="⚠️  No TTS backend. Run install.bat to add neural voice support.",
                     bg=CARD_BG, fg="#ff3b30",
                     font=("Helvetica Neue", 11)).pack(anchor="w", pady=(6, 0))

        # ── Speed slider (shared across backends) ─────────────────────────────
        spd_row = tk.Frame(tts_inner, bg=CARD_BG)
        spd_row.pack(fill="x", pady=(4, 0))
        tk.Label(spd_row, text="Speed:", bg=CARD_BG, fg=TEXT_SUB,
                 font=("Helvetica Neue", 11)).pack(side="left")
        self._tts_rate_var = tk.IntVar(value=self._config.get("tts_rate", 175))
        self._tts_rate_lbl = tk.Label(
            spd_row, text=f"{self._tts_rate_var.get()} wpm",
            bg=CARD_BG, fg=AI_BLUE,
            font=("Helvetica Neue", 11, "bold"), width=7)
        self._tts_rate_lbl.pack(side="right")
        spd_scale = ctk.CTkSlider(
            tts_inner, from_=100, to=300,
            variable=self._tts_rate_var,
            button_color=AI_BLUE, button_hover_color="#0055cc",
            progress_color="#1c2a3a", fg_color=DIVIDER, height=18,
            command=lambda v: (
                self._tts_rate_var.set(int(v)),
                self._tts_rate_lbl.configure(text=f"{int(v)} wpm"),
                self._save_ai_settings()))
        spd_scale.pack(fill="x", pady=(6, 8))

        # Test voice button
        test_row = tk.Frame(tts_inner, bg=CARD_BG)
        test_row.pack(anchor="w")
        test_btn = tk.Label(test_row, text="  🔊  Test Voice  ",
                            bg="#1c2a3a", fg=AI_BLUE,
                            font=("Helvetica Neue", 11, "bold"),
                            cursor="hand2", padx=6, pady=5)
        test_btn.pack(side="left")
        test_btn.bind("<Button-1>", lambda e: threading.Thread(
            target=self._speak_response,
            args=("Hey! I'm your assistant. Ask me anything.",),
            daemon=True).start())

        # ── Assistant Character ────────────────────────────────────────────────
        char_card = self._card(body)
        char_card.pack(fill="x", padx=24, pady=(0, 12))
        char_inner = tk.Frame(char_card, bg=CARD_BG)
        char_inner.pack(fill="x", padx=16, pady=14)

        tk.Label(char_inner, text="ASSISTANT CHARACTER", bg=CARD_BG,
                 fg=LABEL_SMALL, font=("Helvetica Neue", 10, "bold")).pack(anchor="w")
        tk.Label(char_inner,
                 text="A little animated buddy appears and talks when the AI responds.",
                 bg=CARD_BG, fg=TEXT_SUB,
                 font=("Helvetica Neue", 11)).pack(anchor="w", pady=(4, 12))

        # Style buttons
        tk.Label(char_inner, text="Style", bg=CARD_BG, fg=TEXT_SUB,
                 font=("Helvetica Neue", 11)).pack(anchor="w", pady=(0, 4))
        style_row = tk.Frame(char_inner, bg=CARD_BG)
        style_row.pack(fill="x", pady=(0, 10))
        cur_style  = self._config.get("char_style", "Robot")
        self._char_style_btns = {}
        for sty in CHAR_STYLES:
            emoji = {"Robot": "🤖", "Buddy": "😊", "Ghost": "👻", "Alien": "👽"}[sty]
            btn = tk.Label(style_row, text=f" {emoji} {sty} ",
                           bg=ACCENT_DIM if sty == cur_style else BTN_BG,
                           fg=ACCENT_TEXT if sty == cur_style else TEXT_MAIN,
                           font=("Helvetica Neue", 11,
                                 "bold" if sty == cur_style else "normal"),
                           cursor="hand2", padx=6, pady=5)
            btn.pack(side="left", padx=(0, 6))

            def _on_style(e, s=sty):
                self._config["char_style"] = s
                self._save_config()
                for sk, sb in self._char_style_btns.items():
                    sel = (sk == s)
                    sb.configure(
                        bg=ACCENT_DIM if sel else BTN_BG,
                        fg=ACCENT_TEXT if sel else TEXT_MAIN,
                        font=("Helvetica Neue", 11, "bold" if sel else "normal"))
            btn.bind("<Button-1>", _on_style)
            self._char_style_btns[sty] = btn

        # Colour swatches
        tk.Label(char_inner, text="Colour", bg=CARD_BG, fg=TEXT_SUB,
                 font=("Helvetica Neue", 11)).pack(anchor="w", pady=(0, 4))
        col_row = tk.Frame(char_inner, bg=CARD_BG)
        col_row.pack(fill="x", pady=(0, 10))
        cur_col   = self._config.get("char_color", "#30d158")
        self._char_col_swatches = {}
        for name, val in zip(CHAR_COLOR_NAMES, CHAR_COLOR_VALUES):
            swatch = tk.Frame(col_row, bg=val, width=28, height=28, cursor="hand2",
                              highlightthickness=2,
                              highlightbackground=T_PRI if val == cur_col else val)
            swatch.pack(side="left", padx=(0, 6))
            swatch.pack_propagate(False)

            def _on_color(e, v=val):
                self._config["char_color"] = v
                self._save_config()
                for sv, sw in self._char_col_swatches.items():
                    sw.configure(highlightbackground=T_PRI if sv == v else sv)
            swatch.bind("<Button-1>", _on_color)
            self._char_col_swatches[val] = swatch

        # Preview button
        prev_btn = tk.Label(char_inner, text="  ▶  Preview Character  ",
                            bg=ACCENT_DIM, fg=ACCENT_TEXT,
                            font=("Helvetica Neue", 11, "bold"),
                            cursor="hand2", padx=6, pady=5)
        prev_btn.pack(anchor="w")

        def _preview_char(e=None):
            self._show_char_speaking()
            self.root.after(4000, self._hide_char_speaking)
        prev_btn.bind("<Button-1>", _preview_char)

        # ── System Prompt ─────────────────────────────────────────────────────────
        sys_card = self._card(body)
        sys_card.pack(fill="x", padx=24, pady=(0, 12))
        sys_inner = tk.Frame(sys_card, bg=CARD_BG)
        sys_inner.pack(fill="x", padx=16, pady=14)

        tk.Label(sys_inner, text="AI PERSONA / SYSTEM PROMPT", bg=CARD_BG,
                 fg=LABEL_SMALL, font=("Helvetica Neue", 10, "bold")).pack(anchor="w")
        tk.Label(sys_inner,
                 text="Customize how the AI behaves. Keep responses short for voice.",
                 bg=CARD_BG, fg=TEXT_SUB,
                 font=("Helvetica Neue", 11)).pack(anchor="w", pady=(4, 8))

        default_sys = (
            "You are a helpful voice assistant. Give concise, natural responses "
            "suitable for text-to-speech. Keep answers under 3 sentences unless "
            "the user asks for more detail. Do not use markdown or bullet points."
        )
        self._ai_sys_var = tk.StringVar(
            value=self._config.get("ai_system_prompt", default_sys))
        sys_text = tk.Text(
            sys_inner, height=4, wrap="word",
            font=("Helvetica Neue", 11),
            fg=TEXT_MAIN, bg="#3a3a3c",
            relief="flat", bd=4,
            insertbackground=TEXT_MAIN)
        sys_text.insert("1.0", self._ai_sys_var.get())
        sys_text.pack(fill="x", pady=(0, 8))

        def _save_sys(e=None):
            self._config["ai_system_prompt"] = sys_text.get("1.0", "end").strip()
            self._save_config()
        sys_text.bind("<FocusOut>", _save_sys)

        # ── History ───────────────────────────────────────────────────────────────
        hist_card = self._card(body)
        hist_card.pack(fill="x", padx=24, pady=(0, 16))
        hist_inner = tk.Frame(hist_card, bg=CARD_BG)
        hist_inner.pack(fill="x", padx=16, pady=14)

        tk.Label(hist_inner, text="CONVERSATION MEMORY", bg=CARD_BG,
                 fg=LABEL_SMALL, font=("Helvetica Neue", 10, "bold")).pack(anchor="w")
        tk.Label(hist_inner,
                 text="How many past turns to send to Gemini for context (0 = no memory).",
                 bg=CARD_BG, fg=TEXT_SUB,
                 font=("Helvetica Neue", 11)).pack(anchor="w", pady=(4, 8))

        hist_row = tk.Frame(hist_inner, bg=CARD_BG)
        hist_row.pack(fill="x")

        self._ai_hist_var = tk.IntVar(
            value=self._config.get("ai_max_history", 5))
        self._ai_hist_lbl = tk.Label(
            hist_row, text=f"{self._ai_hist_var.get()} turns",
            bg=CARD_BG, fg=AI_BLUE,
            font=("Helvetica Neue", 11, "bold"), width=7)
        self._ai_hist_lbl.pack(side="right")
        tk.Label(hist_row, text="Memory:", bg=CARD_BG, fg=TEXT_SUB,
                 font=("Helvetica Neue", 11)).pack(side="left")

        hist_scale = ctk.CTkSlider(
            hist_inner, from_=0, to=10,
            variable=self._ai_hist_var,
            button_color=AI_BLUE,
            button_hover_color="#0055cc",
            progress_color="#1c2a3a",
            fg_color=DIVIDER,
            height=18,
            command=lambda v: (
                self._ai_hist_var.set(int(v)),
                self._ai_hist_lbl.configure(
                    text=f"{int(v)} turn{'s' if int(v) != 1 else ''}"),
                self._save_ai_settings()
            )
        )
        hist_scale.pack(fill="x", pady=(6, 10))

        clr_btn = tk.Label(hist_inner, text="  🗑  Clear Conversation History  ",
                           bg=BTN_BG, fg="#ff3b30",
                           font=("Helvetica Neue", 11, "bold"),
                           cursor="hand2", padx=6, pady=5)
        clr_btn.pack(anchor="w")
        clr_btn.bind("<Button-1>", lambda e: self._clear_ai_history())

        # ── Write Prompt trigger phrase ───────────────────────────────────────────
        wp_card = self._card(body)
        wp_card.pack(fill="x", padx=24, pady=(0, 12))
        wp_inner = tk.Frame(wp_card, bg=CARD_BG)
        wp_inner.pack(fill="x", padx=16, pady=14)

        tk.Label(wp_inner, text="✍️  WRITE A PROMPT  TRIGGER PHRASE", bg=CARD_BG,
                 fg=LABEL_SMALL, font=("Helvetica Neue", 10, "bold")).pack(anchor="w")
        tk.Label(wp_inner,
                 text="Say this phrase then your idea — Gemini writes the text and pastes it at your cursor.\n"
                      'Example: "write a prompt, a professional apology email to a client"',
                 bg=CARD_BG, fg=TEXT_SUB,
                 font=("Helvetica Neue", 11), justify="left").pack(anchor="w", pady=(4, 10))

        wp_row = tk.Frame(wp_inner, bg=CARD_BG)
        wp_row.pack(fill="x")
        self._wp_phrase_var = tk.StringVar(
            value=self._config.get("write_prompt_phrase", "write a prompt"))
        wp_entry = tk.Entry(wp_row, textvariable=self._wp_phrase_var,
                            font=("Helvetica Neue", 14, "bold"),
                            fg="#ff9f0a", bg="#2a1e0a",
                            relief="flat", bd=0,
                            insertbackground="#ff9f0a", width=22)
        wp_entry.pack(side="left", ipady=7, ipadx=8)
        wp_save = tk.Label(wp_row, text="  Save  ",
                           bg="#2a1e0a", fg="#ff9f0a",
                           font=("Helvetica Neue", 12, "bold"),
                           cursor="hand2", padx=4, pady=7)
        wp_save.pack(side="left", padx=(10, 0))
        wp_save.bind("<Button-1>", lambda e: self._save_ai_settings())
        self._wp_saved_lbl = tk.Label(wp_inner, text="", bg=CARD_BG,
                                      fg=GREEN_DONUT, font=("Helvetica Neue", 11))
        self._wp_saved_lbl.pack(anchor="w", pady=(6, 0))

        # ── Voice Macros ──────────────────────────────────────────────────────────
        mac_card = self._card(body)
        mac_card.pack(fill="x", padx=24, pady=(0, 12))
        mac_inner = tk.Frame(mac_card, bg=CARD_BG)
        mac_inner.pack(fill="x", padx=16, pady=14)

        tk.Label(mac_inner, text="⚡  VOICE MACROS", bg=CARD_BG, fg=LABEL_SMALL,
                 font=("Helvetica Neue", 10, "bold")).pack(anchor="w")
        tk.Label(mac_inner,
                 text="Say the trigger phrase to instantly paste any saved text snippet.\n"
                      'Example: trigger "my email" → pastes your email address.',
                 bg=CARD_BG, fg=TEXT_SUB,
                 font=("Helvetica Neue", 11), justify="left").pack(anchor="w", pady=(4, 10))

        # Live macro list frame
        self._mac_list_frame = tk.Frame(mac_inner, bg=CARD_BG)
        self._mac_list_frame.pack(fill="x")

        def _refresh_macro_list():
            for w in self._mac_list_frame.winfo_children():
                w.destroy()
            macros = self._config.get("voice_macros", {})
            if not macros:
                tk.Label(self._mac_list_frame, text="No macros yet.",
                         bg=CARD_BG, fg=TEXT_SUB,
                         font=("Helvetica Neue", 11)).pack(anchor="w")
            for trig, exp in list(macros.items()):
                row = tk.Frame(self._mac_list_frame, bg=BTN_BG,
                               highlightbackground=DIVIDER, highlightthickness=1)
                row.pack(fill="x", pady=2)
                tk.Label(row, text=f'  🎙 "{trig}"', bg=BTN_BG, fg=GREEN_DONUT,
                         font=("Helvetica Neue", 11, "bold"),
                         width=20, anchor="w").pack(side="left", padx=(4, 0), pady=6)
                tk.Label(row, text="→", bg=BTN_BG, fg=TEXT_SUB,
                         font=("Helvetica Neue", 11)).pack(side="left")
                tk.Label(row, text=f'  {exp[:50]}{"…" if len(exp)>50 else ""}',
                         bg=BTN_BG, fg=TEXT_MAIN,
                         font=("Helvetica Neue", 11),
                         anchor="w").pack(side="left", fill="x", expand=True)
                def _del(t=trig):
                    self._config.setdefault("voice_macros", {}).pop(t, None)
                    self._save_config()
                    _refresh_macro_list()
                del_btn = tk.Label(row, text=" ✕ ", bg=BTN_BG, fg="#ff3b30",
                                   font=("Helvetica Neue", 12, "bold"),
                                   cursor="hand2", padx=6)
                del_btn.pack(side="right", pady=4)
                del_btn.bind("<Button-1>", lambda e, fn=_del: fn())

        _refresh_macro_list()

        # Add new macro form
        add_frame = tk.Frame(mac_inner, bg=CARD_BG)
        add_frame.pack(fill="x", pady=(12, 0))
        tk.Label(add_frame, text="Trigger phrase:", bg=CARD_BG, fg=TEXT_SUB,
                 font=("Helvetica Neue", 11)).grid(row=0, column=0, sticky="w", pady=2)
        tk.Label(add_frame, text="Paste text:", bg=CARD_BG, fg=TEXT_SUB,
                 font=("Helvetica Neue", 11)).grid(row=1, column=0, sticky="w", pady=2)

        mac_trig_var = tk.StringVar()
        mac_exp_var  = tk.StringVar()
        mac_trig_ent = tk.Entry(add_frame, textvariable=mac_trig_var,
                                font=("Helvetica Neue", 12),
                                fg=GREEN_DONUT, bg="#1a2a1a",
                                relief="flat", bd=0, insertbackground=GREEN_DONUT,
                                width=22)
        mac_trig_ent.grid(row=0, column=1, sticky="ew", padx=(8, 0), ipady=5, ipadx=6)
        mac_exp_ent  = tk.Entry(add_frame, textvariable=mac_exp_var,
                                font=("Helvetica Neue", 12),
                                fg=TEXT_MAIN, bg="#2a2a2a",
                                relief="flat", bd=0, insertbackground=TEXT_MAIN,
                                width=30)
        mac_exp_ent.grid(row=1, column=1, sticky="ew", padx=(8, 0), ipady=5, ipadx=6,
                         pady=(4, 0))

        def _add_macro():
            trig = mac_trig_var.get().strip().lower()
            exp  = mac_exp_var.get().strip()
            if not trig or not exp:
                return
            self._config.setdefault("voice_macros", {})[trig] = exp
            self._save_config()
            mac_trig_var.set("")
            mac_exp_var.set("")
            _refresh_macro_list()

        add_btn = tk.Label(add_frame, text="  + Add Macro  ",
                           bg=SEL_BG, fg=SEL_TEXT,
                           font=("Helvetica Neue", 11, "bold"),
                           cursor="hand2", padx=6, pady=5)
        add_btn.grid(row=2, column=1, sticky="w", pady=(10, 0))
        add_btn.bind("<Button-1>", lambda e: _add_macro())
        mac_trig_ent.bind("<Return>", lambda e: mac_exp_ent.focus_set())
        mac_exp_ent.bind("<Return>",  lambda e: _add_macro())

        return page

    def _save_ai_settings(self):
        """Persist all AI settings to config."""
        self._config["ai_wake_word"]       = self._ai_ww_var.get().strip().lower() or "assistant"
        self._config["gemini_api_key"]     = self._ai_key_var.get().strip()
        self._config["tts_rate"]           = self._tts_rate_var.get() if hasattr(self, "_tts_rate_var") else 175
        self._config["tts_voice"]          = self._tts_voice_var.get() if hasattr(self, "_tts_voice_var") else ""
        self._config["ai_max_history"]     = self._ai_hist_var.get() if hasattr(self, "_ai_hist_var") else 5
        self._config["write_prompt_phrase"] = (
            self._wp_phrase_var.get().strip().lower() if hasattr(self, "_wp_phrase_var")
            else "write a prompt")
        # Edge voice: resolved in the option menu callback; persist display→id here too
        if hasattr(self, "_edge_voice_var"):
            name = self._edge_voice_var.get()
            vid  = next((i for n, i in EDGE_VOICES if n == name), "en-US-AriaNeural")
            self._config["edge_voice"] = vid
        self._save_config()
        try:
            self._ai_ww_saved.configure(text="✅  Saved", fg=GREEN_DONUT)
            self.root.after(2000, lambda: self._ai_ww_saved.configure(text=""))
            if self._config.get("gemini_api_key"):
                self._ai_key_status.configure(text="✅  API key saved", fg=GREEN_DONUT)
        except Exception:
            pass
        try:
            self._wp_saved_lbl.configure(text="✅  Saved", fg=GREEN_DONUT)
            self.root.after(2000, lambda: self._wp_saved_lbl.configure(text=""))
        except Exception:
            pass

    def _get_tts_voices(self):
        """Return list of Windows SAPI voice names via pyttsx3."""
        if not _TTS_AVAILABLE:
            return ["(install pyttsx3)"]
        try:
            eng = _pyttsx3.init()
            names = [v.name for v in eng.getProperty("voices")]
            eng.stop()
            return names if names else ["Default"]
        except Exception:
            return ["Default"]

    def _clear_ai_history(self):
        self._ai_history = []
        self._diag_add("🗑 AI conversation history cleared")

    # ════════════════════════════════════════════════════════════════════════════
    #  Settings page
    # ════════════════════════════════════════════════════════════════════════════
    # ════════════════════════════════════════════════════════════════════════════
    #  Codeword page
    # ════════════════════════════════════════════════════════════════════════════
    def _make_codeword_page(self):
        page = tk.Frame(self._content, bg=CONTENT_BG)

        tk.Label(page, text="⚡  Secret Codeword", bg=CONTENT_BG,
                 fg=TEXT_MAIN,
                 font=("Helvetica Neue", 22, "bold")).pack(
            anchor="w", padx=24, pady=(20, 8))

        body = ctk.CTkScrollableFrame(
            page, fg_color=CONTENT_BG,
            scrollbar_button_color=BTN_BG,
            scrollbar_button_hover_color=BTN_HOVER)
        body.pack(fill="both", expand=True)

        # ── Word entry ───────────────────────────────────────────────────────────
        c1 = self._card(body)
        c1.pack(fill="x", padx=24, pady=(4, 12))
        i1 = tk.Frame(c1, bg=CARD_BG)
        i1.pack(fill="x", padx=16, pady=14)

        tk.Label(i1, text="SECRET WORD", bg=CARD_BG, fg=LABEL_SMALL,
                 font=("Helvetica Neue", 10, "bold")).pack(anchor="w")
        tk.Label(i1,
                 text="Say this word while dictating to trigger the action.\nNot case-sensitive  —  it fires even mid-sentence.",
                 bg=CARD_BG, fg=TEXT_SUB,
                 font=("Helvetica Neue", 11), justify="left").pack(anchor="w", pady=(4, 10))

        word_row = tk.Frame(i1, bg=CARD_BG)
        word_row.pack(fill="x")

        self._codeword_var = tk.StringVar(
            value=self._config.get("codeword", ""))
        word_entry = tk.Entry(
            word_row, textvariable=self._codeword_var,
            font=("Helvetica Neue", 18, "bold"),
            fg=SEL_TEXT, bg="#0d2518",
            relief="flat", bd=0,
            insertbackground=SEL_TEXT, width=20)
        word_entry.pack(side="left", ipady=8, ipadx=10)

        save_word = tk.Label(word_row, text="  Save  ",
                             bg=SEL_BG, fg=SEL_TEXT,
                             font=("Helvetica Neue", 12, "bold"),
                             cursor="hand2", padx=4, pady=8)
        save_word.pack(side="left", padx=(10, 0))
        save_word.bind("<Button-1>", lambda e: self._save_codeword())

        self._codeword_saved_lbl = tk.Label(
            i1, text="", bg=CARD_BG, fg=GREEN_DONUT,
            font=("Helvetica Neue", 11))
        self._codeword_saved_lbl.pack(anchor="w", pady=(6, 0))

        # ── Animation display text ────────────────────────────────────────────────
        tk.Frame(i1, bg=DIVIDER, height=1).pack(fill="x", pady=(12, 0))

        tk.Label(i1, text="ANIMATION TEXT",
                 bg=CARD_BG, fg=LABEL_SMALL,
                 font=("Helvetica Neue", 10, "bold")).pack(anchor="w", pady=(10, 0))
        tk.Label(i1,
                 text="What flashes on screen when the codeword fires.",
                 bg=CARD_BG, fg=TEXT_SUB,
                 font=("Helvetica Neue", 11)).pack(anchor="w", pady=(2, 8))

        anim_text_row = tk.Frame(i1, bg=CARD_BG)
        anim_text_row.pack(fill="x")

        self._anim_text_var = tk.StringVar(
            value=self._config.get("anim_text", "Hello Master Austin"))
        anim_entry = tk.Entry(
            anim_text_row, textvariable=self._anim_text_var,
            font=("Helvetica Neue", 16, "bold"),
            fg="#34d860", bg="#0d2518",
            relief="flat", bd=0,
            insertbackground="#34d860", width=22)
        anim_entry.pack(side="left", ipady=8, ipadx=10)

        save_anim = tk.Label(anim_text_row, text="  Save  ",
                             bg=SEL_BG, fg=SEL_TEXT,
                             font=("Helvetica Neue", 12, "bold"),
                             cursor="hand2", padx=4, pady=8)
        save_anim.pack(side="left", padx=(10, 0))
        save_anim.bind("<Button-1>", lambda e: self._save_anim_text())

        # ── Apps to launch ───────────────────────────────────────────────────────
        c2 = self._card(body)
        c2.pack(fill="x", padx=24, pady=(0, 12))
        i2 = tk.Frame(c2, bg=CARD_BG)
        i2.pack(fill="x", padx=16, pady=14)

        hdr2 = tk.Frame(i2, bg=CARD_BG)
        hdr2.pack(fill="x")

        tk.Label(hdr2, text="APPS TO LAUNCH", bg=CARD_BG, fg=LABEL_SMALL,
                 font=("Helvetica Neue", 10, "bold")).pack(side="left")

        add_btn = tk.Label(hdr2, text="  + Add App  ",
                           bg=SEL_BG, fg=SEL_TEXT,
                           font=("Helvetica Neue", 11, "bold"),
                           cursor="hand2", pady=3, padx=4)
        add_btn.pack(side="right")
        add_btn.bind("<Button-1>", lambda e: self._browse_add_app())

        tk.Label(i2,
                 text="These apps open automatically when the codeword fires.",
                 bg=CARD_BG, fg=TEXT_SUB,
                 font=("Helvetica Neue", 11)).pack(anchor="w", pady=(4, 10))

        self._app_list_frame = tk.Frame(i2, bg=CARD_BG)
        self._app_list_frame.pack(fill="x")
        self._refresh_app_list_ui()

        # ── Test + info ──────────────────────────────────────────────────────────
        c3 = self._card(body)
        c3.pack(fill="x", padx=24, pady=(0, 20))
        i3 = tk.Frame(c3, bg=CARD_BG)
        i3.pack(fill="x", padx=16, pady=14)

        tk.Label(i3, text="TEST", bg=CARD_BG, fg=LABEL_SMALL,
                 font=("Helvetica Neue", 10, "bold")).pack(anchor="w")
        tk.Label(i3,
                 text="Preview the animation without dictating. Apps will also launch.",
                 bg=CARD_BG, fg=TEXT_SUB,
                 font=("Helvetica Neue", 11)).pack(anchor="w", pady=(4, 10))

        test_row = tk.Frame(i3, bg=CARD_BG)
        test_row.pack(anchor="w")

        anim_btn = tk.Label(test_row, text="  🎬  Test Animation  ",
                            bg="#1a1a2e", fg="#30d158",
                            font=("Helvetica Neue", 13, "bold"),
                            cursor="hand2", pady=8, padx=4)
        anim_btn.pack(side="left", padx=(0, 10))
        anim_btn.bind("<Button-1>", lambda e: self._trigger_codeword(test=True))

        anim_only = tk.Label(test_row, text="  Animation only  ",
                             bg=BTN_BG, fg=TEXT_MAIN,
                             font=("Helvetica Neue", 12),
                             cursor="hand2", pady=8, padx=4)
        anim_only.pack(side="left")
        anim_only.bind("<Button-1>", lambda e: self._run_animation_only())

        return page

    def _save_codeword(self):
        word = self._codeword_var.get().strip()
        self._config["codeword"] = word
        self._save_config()
        try:
            self._codeword_saved_lbl.configure(
                text=f'✅  Saved! Say "{word}" to activate.' if word
                else "✅  Codeword cleared.")
            self.root.after(3000,
                lambda: self._codeword_saved_lbl.configure(text=""))
        except Exception:
            pass

    def _save_anim_text(self):
        txt = self._anim_text_var.get().strip() or "Hello Master Austin"
        self._config["anim_text"] = txt
        self._save_config()
        try:
            self._codeword_saved_lbl.configure(
                text=f'✅  Animation text saved: "{txt}"')
            self.root.after(3000,
                lambda: self._codeword_saved_lbl.configure(text=""))
        except Exception:
            pass

    def _browse_add_app(self):
        path = fd.askopenfilename(
            title="Choose an app to launch",
            filetypes=[("Executables", "*.exe"), ("All files", "*.*")])
        if path:
            apps = self._config.get("codeword_apps", [])
            if not any(a.get("path") == path for a in apps):
                apps.append({"path": path, "monitor": 1, "position": "maximized"})
                self._config["codeword_apps"] = apps
                self._save_config()
                self._refresh_app_list_ui()

    def _remove_app(self, path):
        apps = self._config.get("codeword_apps", [])
        apps = [a for a in apps if a.get("path") != path]
        self._config["codeword_apps"] = apps
        self._save_config()
        self._refresh_app_list_ui()

    def _update_app_setting(self, path, key, value):
        """Update a single setting (monitor or position) for one app and save."""
        for a in self._config.get("codeword_apps", []):
            if a.get("path") == path:
                a[key] = value
                break
        self._save_config()

    def _refresh_app_list_ui(self):
        try:
            for w in self._app_list_frame.winfo_children():
                w.destroy()

            apps = self._config.get("codeword_apps", [])
            if not apps:
                tk.Label(self._app_list_frame,
                         text="No apps added yet — click  + Add App  above.",
                         bg=CARD_BG, fg=LABEL_SMALL,
                         font=("Helvetica Neue", 11)).pack(anchor="w")
                return

            monitors = _get_monitors()

            for app in apps:
                path     = app.get("path", "")
                mon_idx  = app.get("monitor", 1)
                position = app.get("position", "maximized")
                name     = os.path.basename(path)
                APP_BG   = "#252528"

                card = tk.Frame(self._app_list_frame, bg=APP_BG,
                                highlightbackground="#30d158",
                                highlightthickness=1)
                card.pack(fill="x", pady=5)

                # ── Top row: name  +  hover-reveal remove button (Rule 8) ─────────
                top = tk.Frame(card, bg=APP_BG)
                top.pack(fill="x", padx=12, pady=(10, 4))

                tk.Label(top, text=name, bg=APP_BG, fg=T_PRI,
                         font=F_SUBHEAD).pack(side="left")
                tk.Label(top,
                         text=path[:46] + ("…" if len(path) > 46 else ""),
                         bg=APP_BG, fg=T_TER,
                         font=F_CAPTION).pack(side="left", padx=6)

                rm = tk.Label(top, text="✕  Remove",
                              bg="#3d1515", fg="#cc2222",
                              font=F_CAPTION, padx=G, pady=2, cursor="hand2")
                rm.bind("<Button-1>", lambda e, p=path: self._remove_app(p))
                # Start hidden — revealed on card hover (Rule 8)
                rm.pack_forget()

                def _app_enter(e, r=rm):
                    r.pack(side="right")
                def _app_leave(e, r=rm):
                    r.pack_forget()
                for w in [card, top]:
                    w.bind("<Enter>", _app_enter, add="+")
                    w.bind("<Leave>", _app_leave, add="+")

                # Right-click context menu on app card (Rule 9)
                def _app_ctx(event, p=path):
                    self._context_menu(event, [
                        ("🚀  Test Launch",  lambda: self._test_launch_app(p)),
                        ("-", None),
                        ("✕  Remove",        lambda: self._remove_app(p)),
                    ])
                card.bind("<Button-3>", _app_ctx)
                top.bind("<Button-3>",  _app_ctx)

                # ── Monitor selector ────────────────────────────────────────────
                mon_row = tk.Frame(card, bg=APP_BG)
                mon_row.pack(fill="x", padx=12, pady=(2, 6))

                tk.Label(mon_row, text="Monitor:", bg=APP_BG, fg=TEXT_SUB,
                         font=("Helvetica Neue", 10, "bold")).pack(side="left",
                                                                    padx=(0, 8))

                mon_btns = {}
                for mi, (mx, my, mw, mh) in enumerate(monitors, start=1):
                    label = f"  Monitor {mi}  \n{mw}×{mh}"
                    active = (mi == mon_idx)
                    btn = tk.Label(mon_row, text=f"  Monitor {mi}  ",
                                   bg=SEL_BG if active else BTN_BG,
                                   fg=SEL_TEXT if active else TEXT_MAIN,
                                   font=("Helvetica Neue", 11,
                                         "bold" if active else "normal"),
                                   cursor="hand2", pady=4, padx=2)
                    btn.pack(side="left", padx=(0, 4))
                    mon_btns[mi] = btn

                    def on_mon(e, p=path, idx=mi, btns=mon_btns, app_row=mon_row):
                        self._update_app_setting(p, "monitor", idx)
                        for i, b in btns.items():
                            sel = (i == idx)
                            b.configure(bg=SEL_BG if sel else BTN_BG,
                                        fg=SEL_TEXT if sel else TEXT_MAIN)
                    btn.bind("<Button-1>", on_mon)

                # ── Position grid ───────────────────────────────────────────────
                pos_row = tk.Frame(card, bg=APP_BG)
                pos_row.pack(padx=12, pady=(2, 10), anchor="w")

                tk.Label(pos_row, text="Position:", bg=APP_BG, fg=TEXT_SUB,
                         font=("Helvetica Neue", 10, "bold")).grid(
                    row=0, column=0, rowspan=3, padx=(0, 10), sticky="w")

                grid_frame = tk.Frame(pos_row, bg=APP_BG)
                grid_frame.grid(row=0, column=1, rowspan=3)

                pos_btns = {}
                # 3×3 directional grid
                for gr, gc, pkey, sym in POSITION_GRID:
                    active = (pkey == position)
                    btn = tk.Label(grid_frame, text=sym, width=3,
                                   bg=SEL_BG if active else BTN_BG,
                                   fg=SEL_TEXT if active else TEXT_MAIN,
                                   font=("Helvetica Neue", 14, "bold"),
                                   relief="flat", cursor="hand2",
                                   pady=5, padx=5)
                    btn.grid(row=gr, column=gc, padx=2, pady=2)
                    pos_btns[pkey] = btn

                    def on_pos(e, p=path, k=pkey, btns=pos_btns):
                        self._update_app_setting(p, "position", k)
                        for pk, pb in btns.items():
                            sel = (pk == k)
                            pb.configure(bg=SEL_BG if sel else BTN_BG,
                                         fg=SEL_TEXT if sel else TEXT_MAIN)
                    btn.bind("<Button-1>", on_pos)

                # Full-screen button spanning all 3 columns
                active_max = (position == "maximized")
                full_btn = tk.Label(grid_frame,
                                    text="⬛  Full Screen",
                                    bg=SEL_BG if active_max else BTN_BG,
                                    fg=SEL_TEXT if active_max else TEXT_MAIN,
                                    font=("Helvetica Neue", 11, "bold"),
                                    relief="flat", cursor="hand2",
                                    pady=5)
                full_btn.grid(row=3, column=0, columnspan=3,
                              padx=2, pady=(4, 0), sticky="ew")
                pos_btns["maximized"] = full_btn

                def on_full(e, p=path, btns=pos_btns):
                    self._update_app_setting(p, "position", "maximized")
                    for pk, pb in btns.items():
                        sel = (pk == "maximized")
                        pb.configure(bg=SEL_BG if sel else BTN_BG,
                                     fg=SEL_TEXT if sel else TEXT_MAIN)
                full_btn.bind("<Button-1>", on_full)

        except Exception as ex:
            print(f"App list UI error: {ex}")

    def _trigger_codeword(self, test=False):
        """Fire the codeword: animation on all screens + launch apps."""
        display = self._config.get("anim_text", "Hello Master Austin") or "Hello Master Austin"
        monitors = _get_monitors()
        self._diag_add(f"⚡ Codeword fired on {len(monitors)} monitor(s)")

        # Spawn an animation window per monitor
        anims = []
        for (mx, my, mw, mh) in monitors:
            a = CodewordAnimation(self.root, mx, my, mw, mh, display)
            anims.append(a)

        # Launch apps (after brief delay so animation is visible first)
        if not test:
            threading.Thread(target=self._launch_codeword_apps,
                             daemon=True).start()
        else:
            # In test mode still launch apps after 1 s
            self.root.after(1000,
                lambda: threading.Thread(target=self._launch_codeword_apps,
                                         daemon=True).start())

    def _run_animation_only(self):
        """Animation preview without launching apps."""
        display = self._config.get("anim_text", "Hello Master Austin") or "Hello Master Austin"
        for (mx, my, mw, mh) in _get_monitors():
            CodewordAnimation(self.root, mx, my, mw, mh, display)

    def _launch_codeword_apps(self):
        apps      = self._config.get("codeword_apps", [])
        monitors  = _get_monitors()

        SWP_NOZORDER    = 0x0004
        SWP_SHOWWINDOW  = 0x0040
        SW_RESTORE      = 9
        SW_MAXIMIZE     = 3

        for app in apps:
            # Support both old string format and new dict format
            if isinstance(app, str):
                path     = app
                mon_idx  = 0
                position = "maximized"
            else:
                path     = app.get("path", "")
                mon_idx  = max(0, int(app.get("monitor", 1)) - 1)
                position = app.get("position", "maximized")

            if not path or not os.path.exists(path):
                self._diag_add(f"❌ App not found: {path}")
                continue

            try:
                proc = subprocess.Popen([path], shell=False)
                pid  = proc.pid
                self._diag_add(f"🚀 Launched: {os.path.basename(path)} (PID {pid})")
            except Exception as e:
                self._diag_add(f"❌ Failed to launch {os.path.basename(path)}: {e}")
                continue

            # Wait up to 8 s for the app window to appear
            hwnd = None
            for _ in range(40):
                time.sleep(0.2)
                wins = _find_windows_by_pid(pid)
                if wins:
                    hwnd = wins[0]
                    break

            if not hwnd:
                self._diag_add(f"⚠️ Could not find window for {os.path.basename(path)}")
                continue

            # Resolve which monitor to use (clamp to available monitors)
            if mon_idx >= len(monitors):
                mon_idx = len(monitors) - 1
            mx, my, mw, mh = monitors[mon_idx]
            rx, ry, rw, rh = _compute_rect(mx, my, mw, mh, position)

            try:
                u32 = ctypes.windll.user32
                if position == "maximized":
                    # Move to the target monitor first, then maximise
                    u32.ShowWindow(hwnd, SW_RESTORE)
                    time.sleep(0.05)
                    u32.SetWindowPos(hwnd, 0, mx, my, mw, mh,
                                     SWP_NOZORDER | SWP_SHOWWINDOW)
                    time.sleep(0.05)
                    u32.ShowWindow(hwnd, SW_MAXIMIZE)
                else:
                    u32.ShowWindow(hwnd, SW_RESTORE)
                    time.sleep(0.05)
                    u32.SetWindowPos(hwnd, 0, rx, ry, rw, rh,
                                     SWP_NOZORDER | SWP_SHOWWINDOW)
                self._diag_add(
                    f"📐 Placed {os.path.basename(path)} → Monitor {mon_idx+1} / {position}")
            except Exception as e:
                self._diag_add(f"⚠️ Could not position {os.path.basename(path)}: {e}")

    def _make_settings_page(self):
        page = tk.Frame(self._content, bg=CONTENT_BG)

        tk.Label(page, text="Settings", bg=CONTENT_BG,
                 fg=TEXT_MAIN,
                 font=("Helvetica Neue", 22, "bold")).pack(
            anchor="w", padx=24, pady=(20, 8))

        # ── Scrollable body ──────────────────────────────────────────────────────
        body = ctk.CTkScrollableFrame(
            page, fg_color=CONTENT_BG,
            scrollbar_button_color=BTN_BG,
            scrollbar_button_hover_color=BTN_HOVER)
        body.pack(fill="both", expand=True)

        # ── Microphone ───────────────────────────────────────────────────────────
        sc1 = self._card(body)
        sc1.pack(fill="x", padx=24, pady=(4, 12))
        inner1 = tk.Frame(sc1, bg=CARD_BG)
        inner1.pack(fill="x", padx=16, pady=14)

        tk.Label(inner1, text="MICROPHONE",
                 bg=CARD_BG, fg=LABEL_SMALL,
                 font=("Helvetica Neue", 10, "bold")).pack(anchor="w")

        mics = self._query_mics()
        self._mic_var = ctk.StringVar(value=mics[0] if mics else "Default")
        self._mic_menu = ctk.CTkOptionMenu(
            inner1, values=mics, variable=self._mic_var,
            fg_color=BTN_BG, button_color="#248a3d",
            button_hover_color=SEL_BG,
            dropdown_fg_color=CARD_BG,
            dropdown_hover_color="#0d2518",
            text_color=TEXT_MAIN,
            font=ctk.CTkFont(size=13),
            corner_radius=10, height=38,
        )
        self._mic_menu.pack(fill="x", pady=(8, 0))

        # ── Mic test ──────────────────────────────────────────────────────────────
        sc_test = self._card(body)
        sc_test.pack(fill="x", padx=24, pady=(0, 12))
        inner_t = tk.Frame(sc_test, bg=CARD_BG)
        inner_t.pack(fill="x", padx=16, pady=14)

        hdr_t = tk.Frame(inner_t, bg=CARD_BG)
        hdr_t.pack(fill="x")

        tk.Label(hdr_t, text="MIC TEST",
                 bg=CARD_BG, fg=LABEL_SMALL,
                 font=("Helvetica Neue", 10, "bold")).pack(side="left")

        self._test_btn = tk.Label(
            hdr_t, text="  Start Test  ",
            bg=SEL_BG, fg=SEL_TEXT,
            font=("Helvetica Neue", 11, "bold"),
            cursor="hand2", padx=6, pady=3)
        self._test_btn.pack(side="right")
        self._test_btn.bind("<Button-1>", lambda e: self._toggle_mic_test())

        # Level meter canvas
        METER_W, METER_H = 390, 22
        self._meter_cv = tk.Canvas(inner_t, width=METER_W, height=METER_H,
                                   bg=CARD_BG, highlightthickness=0)
        self._meter_cv.pack(fill="x", pady=(10, 4))

        # Track background
        self._meter_cv.create_rectangle(
            0, 6, METER_W, METER_H - 6,
            fill="#3a3a3c", outline="", tags="track")

        # Green fill bar
        self._meter_fill = self._meter_cv.create_rectangle(
            0, 6, 0, METER_H - 6,
            fill=GREEN_DONUT, outline="", tags="fill")

        # Orange peak tick
        self._meter_peak = self._meter_cv.create_rectangle(
            0, 4, 3, METER_H - 4,
            fill="#ff9f0a", outline="", tags="peak")

        # Status row
        status_row = tk.Frame(inner_t, bg=CARD_BG)
        status_row.pack(fill="x")

        self._test_status = tk.Label(
            status_row, text="Press  Start Test  to check your microphone",
            bg=CARD_BG, fg=TEXT_SUB, font=("Helvetica Neue", 11), anchor="w")
        self._test_status.pack(side="left")

        self._test_db = tk.Label(
            status_row, text="",
            bg=CARD_BG, fg=LABEL_SMALL, font=("Helvetica Neue", 10))
        self._test_db.pack(side="right")

        # ── Model quality ─────────────────────────────────────────────────────────
        sc2 = self._card(body)
        sc2.pack(fill="x", padx=24, pady=(0, 12))
        inner2 = tk.Frame(sc2, bg=CARD_BG)
        inner2.pack(fill="x", padx=16, pady=14)

        tk.Label(inner2, text="MODEL QUALITY",
                 bg=CARD_BG, fg=LABEL_SMALL,
                 font=("Helvetica Neue", 10, "bold")).pack(anchor="w")

        mb = tk.Frame(inner2, bg=CARD_BG)
        mb.pack(fill="x", pady=(10, 0))

        self._model_btns = {}
        for col, (label, key, hint) in enumerate(MODEL_OPTIONS):
            active = (key == self.current_model)
            f = tk.Frame(mb, bg=SEL_BG if active else BTN_BG,
                         cursor="hand2")
            f.grid(row=0, column=col,
                   padx=(0 if col == 0 else 6, 0), sticky="ew")
            mb.columnconfigure(col, weight=1)

            tk.Label(f, text=label, bg=SEL_BG if active else BTN_BG,
                     fg=SEL_TEXT if active else TEXT_MAIN,
                     font=("Helvetica Neue", 13, "bold"),
                     pady=8).pack()
            tk.Label(f, text=hint, bg=SEL_BG if active else BTN_BG,
                     fg=SEL_TEXT if active else TEXT_SUB,
                     font=("Helvetica Neue", 10)).pack(pady=(0, 8))

            self._model_btns[key] = f
            for widget in f.winfo_children() + [f]:
                widget.bind("<Button-1>",
                            lambda e, k=key: self._switch_model(k))

        # ── Hotkey ────────────────────────────────────────────────────────────────
        sc3 = self._card(body)
        sc3.pack(fill="x", padx=24)
        inner3 = tk.Frame(sc3, bg=CARD_BG)
        inner3.pack(fill="x", padx=16, pady=14)

        hk_top = tk.Frame(inner3, bg=CARD_BG)
        hk_top.pack(fill="x")

        tk.Label(hk_top, text="HOTKEY",
                 bg=CARD_BG, fg=LABEL_SMALL,
                 font=("Helvetica Neue", 10, "bold")).pack(side="left")

        tk.Label(inner3,
                 text="Hold this key anywhere to start recording. Release to transcribe.",
                 bg=CARD_BG, fg=TEXT_SUB,
                 font=("Helvetica Neue", 11)).pack(anchor="w", pady=(4, 10))

        hk_row = tk.Frame(inner3, bg=CARD_BG)
        hk_row.pack(fill="x")

        # Current key badge
        self._hotkey_badge = tk.Label(
            hk_row,
            text=f"  {self._hotkey_display}  ",
            bg="#3a3a3c", fg=TEXT_MAIN,
            font=("Helvetica Neue", 15, "bold"),
            padx=6, pady=6)
        self._hotkey_badge.pack(side="left", padx=(0, 12))

        # Capture button
        self._capture_btn = tk.Label(
            hk_row,
            text="  Change Hotkey  ",
            bg=SEL_BG, fg=SEL_TEXT,
            font=("Helvetica Neue", 12, "bold"),
            cursor="hand2", padx=6, pady=6)
        self._capture_btn.pack(side="left")
        self._capture_btn.bind("<Button-1>", lambda e: self._start_hotkey_capture())

        # ── Dictation behaviour ───────────────────────────────────────────────────
        sc_beh = self._card(body)
        sc_beh.pack(fill="x", padx=24, pady=(0, 12))
        inner_beh = tk.Frame(sc_beh, bg=CARD_BG)
        inner_beh.pack(fill="x", padx=16, pady=14)

        tk.Label(inner_beh, text="DICTATION BEHAVIOUR", bg=CARD_BG, fg=LABEL_SMALL,
                 font=("Helvetica Neue", 10, "bold")).pack(anchor="w")

        # Auto-punctuation toggle
        ap_row = tk.Frame(inner_beh, bg=CARD_BG)
        ap_row.pack(fill="x", pady=(10, 0))
        self._auto_punct_var = tk.BooleanVar(
            value=self._config.get("auto_punctuate", False))

        def _toggle_ap():
            self._config["auto_punctuate"] = self._auto_punct_var.get()
            self._save_config()
            _ap_lbl.configure(
                text="✅  On — first letter capitalised, period added if missing"
                if self._auto_punct_var.get() else
                "○  Off — text pasted exactly as spoken")

        ap_chk = ctk.CTkCheckBox(
            ap_row,
            text="Auto-capitalise & punctuate dictations",
            variable=self._auto_punct_var,
            command=_toggle_ap,
            fg_color=ACCENT,
            hover_color=SEL_BG,
            text_color=TEXT_MAIN,
            font=ctk.CTkFont(size=13),
            checkmark_color="white")
        ap_chk.pack(side="left")

        _ap_lbl = tk.Label(
            inner_beh,
            text=("✅  On — first letter capitalised, period added if missing"
                  if self._config.get("auto_punctuate", False)
                  else "○  Off — text pasted exactly as spoken"),
            bg=CARD_BG, fg=TEXT_SUB, font=("Helvetica Neue", 11))
        _ap_lbl.pack(anchor="w", pady=(6, 0))

        # ── Diagnostics ───────────────────────────────────────────────────────────
        sc4 = self._card(body)
        sc4.pack(fill="x", padx=24, pady=(12, 20))
        inner4 = tk.Frame(sc4, bg=CARD_BG)
        inner4.pack(fill="x", padx=16, pady=14)

        tk.Label(inner4, text="DIAGNOSTICS",
                 bg=CARD_BG, fg=LABEL_SMALL,
                 font=("Helvetica Neue", 10, "bold")).pack(anchor="w")

        # Model status
        row_m = tk.Frame(inner4, bg=CARD_BG)
        row_m.pack(fill="x", pady=(8, 0))
        tk.Label(row_m, text="Model:", bg=CARD_BG, fg=TEXT_SUB,
                 font=("Helvetica Neue", 11), width=9, anchor="w").pack(side="left")
        self._model_diag = tk.Label(row_m,
                                    text=f"⏳  Loading whisper/{self.current_model}…",
                                    bg=CARD_BG, fg="#b8860b",
                                    font=("Helvetica Neue", 11), anchor="w")
        self._model_diag.pack(side="left")

        # Last key detected
        row_k = tk.Frame(inner4, bg=CARD_BG)
        row_k.pack(fill="x", pady=(4, 0))
        tk.Label(row_k, text="Last key:", bg=CARD_BG, fg=TEXT_SUB,
                 font=("Helvetica Neue", 11), width=9, anchor="w").pack(side="left")
        self._lastkey_lbl = tk.Label(row_k,
                                     text=self._last_key,
                                     bg=CARD_BG, fg=TEXT_MAIN,
                                     font=("Helvetica Neue", 11, "bold"), anchor="w")
        self._lastkey_lbl.pack(side="left")

        # Manual dictate button
        btn_row = tk.Frame(inner4, bg=CARD_BG)
        btn_row.pack(fill="x", pady=(10, 6))

        self._manual_btn = tk.Label(
            btn_row,
            text="  ▶  Hold to Dictate Manually  ",
            bg=SEL_BG, fg=SEL_TEXT,
            font=("Helvetica Neue", 12, "bold"),
            cursor="hand2", pady=6)
        self._manual_btn.pack(side="left")

        self._manual_btn.bind("<ButtonPress-1>",   lambda e: self._manual_start())
        self._manual_btn.bind("<ButtonRelease-1>", lambda e: self._manual_stop())

        tk.Label(btn_row,
                 text="  ← bypasses hotkey",
                 bg=CARD_BG, fg=LABEL_SMALL,
                 font=("Helvetica Neue", 10)).pack(side="left")

        # Event log box
        tk.Label(inner4, text="Event log:",
                 bg=CARD_BG, fg=TEXT_SUB,
                 font=("Helvetica Neue", 10)).pack(anchor="w", pady=(10, 2))

        log_box = tk.Frame(inner4, bg="#252528",
                           highlightbackground=DIVIDER, highlightthickness=1)
        log_box.pack(fill="x")

        self._diag_lbl = tk.Label(
            log_box,
            text="— waiting for events —",
            bg="#252528", fg=TEXT_MAIN,
            font=("Courier New", 10),
            anchor="w", justify="left",
            padx=8, pady=6)
        self._diag_lbl.pack(fill="x")

        return page

    # ════════════════════════════════════════════════════════════════════════════
    #  Mic test
    # ════════════════════════════════════════════════════════════════════════════
    def _toggle_mic_test(self):
        if self.testing_mic:
            self._stop_mic_test()
        else:
            self._start_mic_test()

    def _start_mic_test(self):
        if self.recording or self.transcribing:
            self._test_status.configure(
                text="⚠️  Can't test while recording — release Right Alt first",
                fg="#ff3b30")
            return

        mic_name = self._mic_var.get()
        dev_idx  = self.mic_index_map.get(mic_name)

        try:
            self.test_stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                device=dev_idx,
                callback=self._test_audio_cb,
            )
            self.test_stream.start()
            self.testing_mic = True
            self.test_peak   = 0.0
            self._test_btn.configure(text="  Stop Test  ",
                                     bg="#3d1515", fg="#cc0000")
            self._test_status.configure(
                text="🎙  Listening — speak or make noise near your mic…",
                fg=TEXT_MAIN)
            self._update_meter()
        except Exception as e:
            self._test_status.configure(
                text=f"❌  Could not open mic: {e}", fg="#ff3b30")

    def _stop_mic_test(self):
        self.testing_mic = False
        if self.test_stream:
            self.test_stream.stop()
            self.test_stream.close()
            self.test_stream = None
        if self.meter_anim_id:
            self.root.after_cancel(self.meter_anim_id)
            self.meter_anim_id = None
        self._test_btn.configure(text="  Start Test  ",
                                 bg=SEL_BG, fg=SEL_TEXT)
        # Reset meter to zero
        self._meter_cv.coords(self._meter_fill, 0, 6, 0, 16)
        self._meter_cv.coords(self._meter_peak, 0, 4, 3, 18)
        self._test_status.configure(
            text="Press  Start Test  to check your microphone", fg=TEXT_SUB)
        self._test_db.configure(text="")

    def _test_audio_cb(self, indata, frames, time_info, status):
        """Called by sounddevice on the audio thread during mic test."""
        amp = float(np.sqrt(np.mean(indata ** 2)))
        self.test_amp = amp
        if amp > self.test_peak:
            self.test_peak = amp

    def _update_meter(self):
        """Animate the level meter at ~30 fps while testing."""
        if not self.testing_mic:
            return

        METER_W = 390
        amp  = self.test_amp
        peak = self.test_peak

        # Convert to a 0–1 range using a log scale so quiet sounds are visible
        def to_frac(a):
            if a <= 0:
                return 0.0
            db = 20 * math.log10(max(a, 1e-9))
            # map -60 dB → 0.0  …  0 dB → 1.0
            return max(0.0, min(1.0, (db + 60) / 60))

        frac      = to_frac(amp)
        peak_frac = to_frac(peak)

        fill_x = int(frac * METER_W)
        peak_x = int(peak_frac * METER_W)

        # Colour: green → yellow → red based on level
        if frac < 0.6:
            r, g, b = 52, 199, 89     # green
        elif frac < 0.85:
            r, g, b = 255, 159, 10    # orange
        else:
            r, g, b = 255, 59, 48     # red (clipping!)

        fill_col = f"#{r:02x}{g:02x}{b:02x}"
        self._meter_cv.coords(self._meter_fill, 0, 6, fill_x, 16)
        self._meter_cv.itemconfig(self._meter_fill, fill=fill_col)
        self._meter_cv.coords(self._meter_peak, peak_x - 2, 4, peak_x + 2, 18)

        # Status text
        db_val = 20 * math.log10(max(amp, 1e-9))
        self._test_db.configure(text=f"{db_val:.0f} dB")

        if frac > 0.05:
            if frac > 0.85:
                msg, col = "🔴  Very loud — mic is clipping!", "#ff3b30"
            elif frac > 0.4:
                msg, col = "✅  Mic is working great!", GREEN_DONUT
            else:
                msg, col = "🟡  Signal detected — try speaking louder", "#b8860b"
        else:
            msg, col = "🎙  Listening — speak or make noise near your mic…", TEXT_SUB

        self._test_status.configure(text=msg, fg=col)

        # Slowly decay the peak indicator
        self.test_peak *= 0.995

        self.meter_anim_id = self.root.after(33, self._update_meter)

    # ════════════════════════════════════════════════════════════════════════════
    #  Helpers — card, hover-reveal, context menu (Rules 3 / 8 / 9)
    # ════════════════════════════════════════════════════════════════════════════
    def _card(self, parent, hover=False):
        """Elevated dark card with a subtle border."""
        card = ctk.CTkFrame(parent, fg_color=CARD_BG, corner_radius=15,
                            border_width=1, border_color="#30d158")
        if hover:
            card.bind("<Enter>", lambda e: card.configure(fg_color=CARD_HOVER, border_color="#00ff00"))
            card.bind("<Leave>", lambda e: card.configure(fg_color=CARD_BG, border_color="#30d158"))
        # _shadow alias so existing dictations code still works
        card._shadow = card
        return card

    def _pack_card(self, card, **kwargs):
        """Pack a card's shadow wrapper with the given kwargs."""
        card._shadow.pack(**kwargs)

    def _bind_hover_reveal(self, trigger_widgets, hidden_widgets):
        """Show hidden_widgets only while the cursor is on trigger_widgets (Rule 8)."""
        def _show(e):
            for w in hidden_widgets:
                try: w.place_configure(x=w._reveal_x, y=w._reveal_y)
                except Exception:
                    try: w.pack_configure()
                    except Exception: pass
        def _hide(e):
            for w in hidden_widgets:
                try: w.place_forget()
                except Exception:
                    try: w.pack_forget()
                    except Exception: pass
        for tw in trigger_widgets:
            tw.bind("<Enter>", _show, add="+")
            tw.bind("<Leave>", _hide, add="+")

    def _context_menu(self, event, items):
        """Show a themed right-click context menu at cursor (Rule 9).
        items: list of (label, callback) — use "-" for separator."""
        menu = tk.Menu(
            self.root, tearoff=0,
            bg=CARD_BG, fg=T_PRI,
            activebackground=ACCENT_LITE, activeforeground=ACCENT_TEXT,
            font=("Helvetica Neue", 11),
            relief="flat", borderwidth=1,
            activeborderwidth=0)
        for label, cmd in items:
            if label == "-":
                menu.add_separator()
            else:
                menu.add_command(label=label, command=cmd)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _query_mics(self):
        self.mic_index_map = {}
        try:
            devices = sd.query_devices()
            names, seen = [], {}
            for i, d in enumerate(devices):
                if d["max_input_channels"] > 0:
                    n = d["name"]
                    if n in seen:
                        n = f"{n} ({i})"
                    seen[d["name"]] = True
                    self.mic_index_map[n] = i
                    names.append(n)
            return names or ["Default Microphone"]
        except Exception:
            return ["Default Microphone"]

    def _switch_model(self, key):
        if key == self.current_model and self.model_loaded:
            return
        old = self.current_model
        self.current_model = key
        # update button styles
        for k, frame in self._model_btns.items():
            sel = (k == key)
            for w in frame.winfo_children() + [frame]:
                w.configure(bg=SEL_BG if sel else BTN_BG)
                if isinstance(w, tk.Label):
                    w.configure(fg=SEL_TEXT if sel else (
                        TEXT_MAIN if w.cget("font").split()[-1] == "bold"
                        else TEXT_SUB))
        self.model_loaded = False
        self.model = None
        threading.Thread(target=self._load_model, daemon=True).start()

    @staticmethod
    def _fmt(secs):
        s = int(secs)
        if s < 60:   return f"{s}s"
        if s < 3600: return f"{s // 60}m"
        return f"{s // 3600}h {(s % 3600) // 60}m"

    def _set_status(self, title, sub, dot="#8e8e93"):
        try:
            self._st_title.configure(text=title)
            self._st_sub.configure(text=sub)
            self._dot_cv.itemconfig(self._dot, fill=dot)
        except Exception:
            pass

    def _diag_add(self, msg):
        """Thread-safe: append a timestamped message to the diagnostics log."""
        ts   = time.strftime("%H:%M:%S")
        line = f"{ts}  {msg}"
        print(line)
        self._diag_lines.append(line)
        self._diag_lines = self._diag_lines[-8:]   # keep last 8
        self.root.after(0, self._refresh_diag_log)

    def _refresh_diag_log(self):
        try:
            if self._diag_lbl:
                self._diag_lbl.configure(
                    text="\n".join(self._diag_lines) or "— waiting for events —")
        except Exception:
            pass

    def _refresh_diag_key(self):
        try:
            if self._lastkey_lbl:
                self._lastkey_lbl.configure(text=self._last_key)
        except Exception:
            pass

    def _refresh_diag_model(self):
        try:
            if self._model_diag:
                if self.model_loaded:
                    self._model_diag.configure(
                        text=f"✅  whisper/{self.current_model} loaded",
                        fg=GREEN_DONUT)
                else:
                    self._model_diag.configure(
                        text=f"⏳  Loading whisper/{self.current_model}…",
                        fg="#b8860b")
        except Exception:
            pass

    # ════════════════════════════════════════════════════════════════════════════
    #  Pill popup  —  full PIL rendering (anti-aliased, 3x supersampled)
    # ════════════════════════════════════════════════════════════════════════════
    _PILL_S = 3   # supersampling scale

    def _build_pill(self):
        self.pill = tk.Toplevel(self.root)
        self.pill.overrideredirect(True)
        self.pill.attributes("-topmost", True)
        self.pill.attributes("-transparentcolor", PILL_CHROMA)
        self.pill.attributes("-alpha", 0.88)  # Global window translucency for frosted glass effect
        self.pill.configure(bg=PILL_CHROMA)
        self.pill.withdraw()

        self._pc = tk.Canvas(self.pill,
                             width=PILL_W, height=PILL_H,
                             bg=PILL_CHROMA, highlightthickness=0)
        self._pc.pack()

        # Pre-render static pill background (RGBA, transparent outside pill)
        self._pill_bg_pil = self._render_pill_bg()

        # Single canvas image item — updated every animation frame
        blank = ImageTk.PhotoImage(
            Image.new("RGB", (PILL_W, PILL_H), _hex_to_rgb(PILL_CHROMA)))
        self._pill_pimg  = blank
        self._pill_cv_id = self._pc.create_image(0, 0, anchor="nw", image=blank)

        # Bar x-positions: centred inside the inner visualizer container
        # Viz container: x=(PILL_W-224)//2=58, width=224
        _VIZ_X = (PILL_W - 224) // 2   # = 58
        _VIZ_W = 224
        total_w = PILL_N_BARS * PILL_BAR_W + (PILL_N_BARS - 1) * PILL_BAR_GAP
        self._pill_bar_x0 = _VIZ_X + (_VIZ_W - total_w) // 2

        # Cache fonts for animation (avoids re-loading every frame)
        self._pill_font_title  = _get_pill_font(11)
        self._pill_font_status = _get_pill_font(9)

    def _render_pill_bg(self) -> "Image.Image":
        """Render a card-style pill background matching the web UI pill card."""
        S = self._PILL_S
        W, H = PILL_W * S, PILL_H * S

        # Inner visualizer container dimensions (matches web UI .pill-visualizer)
        VIZ_W = 224 * S
        VIZ_H = 52  * S
        VIZ_X = (W - VIZ_W) // 2
        VIZ_Y = 38 * S

        img  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # ── Card body (Apple Dark Frosted Glass base) ─────────────────────────
        card_r    = 34 * S  # very round Apple-style corners 
        card_fill = (26, 26, 28, 255) # native dark gray, opacity provided by window -alpha
        _pil_rrect(draw, 0, 0, W, H, card_r, fill=card_fill)

        # ── Card border (Subtle white stroke for edge lighting) ───────────────
        border_col = (255, 255, 255, 40)
        _pil_rrect(draw, S, S, W - S, H - S, card_r,
                   outline=border_col, width=max(1, int(1.5 * S)))

        # ── Top-edge highlight (glass volumetric effect) ──────────────────────
        shine_col = (255, 255, 255, 18)
        _pil_rrect(draw, 2*S, 2*S, W - 2*S, 2*S + 14*S, card_r,
                   fill=shine_col)

        # ── Inner visualizer container (deep inset) ───────────────────────────
        viz_r    = VIZ_H // 2
        viz_fill = (14, 14, 16, 255)
        _pil_rrect(draw, VIZ_X, VIZ_Y, VIZ_X + VIZ_W, VIZ_Y + VIZ_H,
                   viz_r, fill=viz_fill)

        # Inset shadow on viz container
        inset_col = (0, 0, 0, 180)
        _pil_rrect(draw, VIZ_X + S, VIZ_Y + S,
                   VIZ_X + VIZ_W - S, VIZ_Y + VIZ_H - S,
                   viz_r, outline=inset_col, width=max(1, S))

        # ── Composite on chroma background ────────────────────────────────────
        chroma_bg = Image.new("RGBA", (W, H), (*_hex_to_rgb(PILL_CHROMA), 255))
        composed  = Image.alpha_composite(chroma_bg, img)

        return composed.convert("RGB").resize((PILL_W, PILL_H), Image.LANCZOS)

    def _show_pill(self):
        sw = self.root.winfo_screenwidth()
        x  = (sw - PILL_W) // 2
        self.pill.geometry(f"{PILL_W}x{PILL_H}+{x}+14")
        self.pill.attributes("-alpha", 0.0)
        self.pill.deiconify()
        self.pill.lift()
        self._pill_fade_in()
        self._animate_pill()

    def _pill_fade_in(self, step=0, n=10):
        if step > n:
            return
        try:
            self.pill.attributes("-alpha", step / n)
        except Exception:
            return
        self.root.after(16, lambda: self._pill_fade_in(step + 1, n))

    def _hide_pill(self):
        self._stop_anim()
        self._pill_fade_out()

    def _pill_fade_out(self, step=10, n=10):
        if step < 0:
            try:
                self.pill.withdraw()
            except Exception:
                pass
            return
        try:
            self.pill.attributes("-alpha", step / n)
        except Exception:
            pass
        self.root.after(14, lambda: self._pill_fade_out(step - 1, n))

    def _animate_pill(self):
        if not self.recording:
            return
        t   = time.time()
        amp = min(self.amplitude * 140, 1.0)

        # Visualizer container geometry (must match _render_pill_bg)
        VIZ_W = 224
        VIZ_H = 52
        VIZ_X = (PILL_W - VIZ_W) // 2   # = 58
        VIZ_Y = 38
        mid   = VIZ_Y + VIZ_H / 2.0      # = 64.0
        cap   = VIZ_H / 2.0 - 5.0        # = 21.0

        bg_rgba     = self._pill_bg_pil.convert("RGBA")
        frame_layer = Image.new("RGBA", (PILL_W, PILL_H), (0, 0, 0, 0))
        fdraw       = ImageDraw.Draw(frame_layer)

        # ── Title text ────────────────────────────────────────────────────────
        title     = "LISTENING…"
        title_col = (48, 209, 88, 255)   # accent green
        _draw_text_centered(fdraw, 13, title,
                            self._pill_font_title, title_col, PILL_W)

        # ── EQ bars (inside viz container) ────────────────────────────────────
        x0 = self._pill_bar_x0
        for i in range(PILL_N_BARS):
            wave   = math.sin(t * 7 + i * 0.55) * 0.5 + 0.5
            noise  = random.uniform(0.82, 1.0)
            target = max(2.5, (amp * 0.75 + wave * 0.25) * noise * cap)
            self.pill_bh[i] = self.pill_bh[i] * 0.82 + target * 0.18
            hh = self.pill_bh[i]
            x  = x0 + i * (PILL_BAR_W + PILL_BAR_GAP)

            t_f = min(1.0, hh / cap)
            s   = max(0.0, (t_f - 0.25) / 0.75)
            cr  = (int(30 + 30 * s), int(140 + 69 * s), int(70 + 18 * s))

            gl = 4
            ga = int(22 + 80 * t_f)
            fdraw.ellipse([x-gl, mid-hh-gl, x+PILL_BAR_W+gl, mid+hh+gl],
                          fill=(*cr, ga))
            fdraw.ellipse([x, mid-hh, x+PILL_BAR_W, mid+hh],
                          fill=(*cr, 255))

        # ── Pulsing REC dot (inside viz container, right edge) ────────────────
        pulse = math.sin(t * 4) * 0.5 + 0.5
        dx    = VIZ_X + VIZ_W - 14
        dy    = int(mid)
        dr    = 4
        rv    = int(200 + 55 * pulse)
        ga    = int(80 * pulse)
        fdraw.ellipse([dx-dr-3, dy-dr-3, dx+dr+3, dy+dr+3],
                      fill=(rv, 59, 48, ga))
        fdraw.ellipse([dx-dr, dy-dr, dx+dr, dy+dr],
                      fill=(rv, 59, 48, 255))

        # ── Status text ───────────────────────────────────────────────────────
        status     = "Release to transcribe"
        status_col = (110, 114, 112, 200)
        _draw_text_centered(fdraw, VIZ_Y + VIZ_H + 9, status,
                            self._pill_font_status, status_col, PILL_W)

        # ── Composite and push to floating pill canvas ─────────────────────────
        chroma_base   = Image.new("RGBA", (PILL_W, PILL_H),
                                  (*_hex_to_rgb(PILL_CHROMA), 255))
        floating_bg   = Image.alpha_composite(chroma_base, bg_rgba)
        floating_frame = Image.alpha_composite(floating_bg, frame_layer)

        self._pill_pimg = ImageTk.PhotoImage(floating_frame.convert("RGB"))
        self._pc.itemconfig(self._pill_cv_id, image=self._pill_pimg)

        # ── Also push to the tkinter dashboard pill (legacy) ──────────────────
        try:
            if hasattr(self, '_dash_pill_cv'):
                dash_base  = Image.new("RGBA", (PILL_W, PILL_H),
                                       (*_hex_to_rgb(CARD_BG), 255))
                dash_bg    = Image.alpha_composite(dash_base, bg_rgba)
                dash_frame = Image.alpha_composite(dash_bg, frame_layer)
                self._dash_pimg = ImageTk.PhotoImage(dash_frame.convert("RGB"))
                self._dash_pill_cv.itemconfig(self._dash_pill_cv_id,
                                              image=self._dash_pimg)
        except Exception:
            pass

        self.anim_id = self.root.after(16, self._animate_pill)

    def _stop_anim(self):
        if self.anim_id:
            self.root.after_cancel(self.anim_id)
            self.anim_id = None
        self.pill_bh = [2.0] * PILL_N_BARS
        # Restore static background
        try:
            self._pill_pimg = ImageTk.PhotoImage(self._pill_bg_pil)
            self._pc.itemconfig(self._pill_cv_id, image=self._pill_pimg)
            
            if hasattr(self, '_dash_pill_cv'):
                dash_base = Image.new("RGBA", (PILL_W, PILL_H), (*_hex_to_rgb(CARD_BG), 255))
                bg_rgba = self._pill_bg_pil.convert("RGBA")
                dash_bg = Image.alpha_composite(dash_base, bg_rgba)
                self._dash_pimg = ImageTk.PhotoImage(dash_bg.convert("RGB"))
                self._dash_pill_cv.itemconfig(self._dash_pill_cv_id, image=self._dash_pimg)
        except Exception:
            pass

    # ════════════════════════════════════════════════════════════════════════════
    #  Assistant character window  —  full PIL rendering (3× supersampled)
    # ════════════════════════════════════════════════════════════════════════════
    _CHAR_S = 3   # supersampling scale

    def _build_char_window(self):
        """Build the transparent floating character window (hidden until AI speaks)."""
        w = self._char_win = tk.Toplevel(self.root)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        w.attributes("-transparentcolor", PILL_CHROMA)
        w.configure(bg=PILL_CHROMA)
        w.withdraw()

        self._char_canvas = tk.Canvas(
            w, width=CHAR_WIN_W, height=CHAR_WIN_H,
            bg=PILL_CHROMA, highlightthickness=0)
        self._char_canvas.pack()

        # Single canvas image item updated each frame (same pattern as the pill)
        blank = ImageTk.PhotoImage(
            Image.new("RGB", (CHAR_WIN_W, CHAR_WIN_H), _hex_to_rgb(PILL_CHROMA)))
        self._char_pimg  = blank
        self._char_cv_id = self._char_canvas.create_image(0, 0, anchor="nw", image=blank)
        self._char_blink_next = time.time() + 3.5

    def _show_char_speaking(self):
        """Position and animate the character just to the right of the pill."""
        self._char_speaking = True
        self._char_ripples  = []
        self._char_last_ripple = 0.0

        sw = self.root.winfo_screenwidth()
        pill_x = (sw - PILL_W) // 2
        # Sits at the RIGHT end of the pill, vertically centred with it
        char_x = pill_x + PILL_W + 6
        char_y = max(0, 14 + PILL_H // 2 - CHAR_WIN_H // 2)

        self._char_win.geometry(f"{CHAR_WIN_W}x{CHAR_WIN_H}+{char_x}+{char_y}")
        self._char_win.deiconify()
        self._char_win.lift()
        self._animate_char()

    def _hide_char_speaking(self):
        """Stop the animation and withdraw the character window."""
        self._char_speaking = False
        if self._char_anim_id:
            self.root.after_cancel(self._char_anim_id)
            self._char_anim_id = None
        try:
            self._char_win.withdraw()
        except Exception:
            pass

    def _animate_char(self):
        """Render one PIL-supersampled frame of the character animation (~30 fps)."""
        if not self._char_speaking:
            return
        t   = time.time()
        S   = self._CHAR_S
        W, H = CHAR_WIN_W * S, CHAR_WIN_H * S
        cx, cy = W // 2, H // 2

        color = self._config.get("char_color", "#30d158")
        style = self._config.get("char_style", "Robot")

        # ── Speech ripples ────────────────────────────────────────────────────
        if t - self._char_last_ripple > 0.38:
            self._char_ripples.append(t)
            self._char_last_ripple = t

        keep = []
        for spawn_t in self._char_ripples:
            if t - spawn_t < 0.65:
                keep.append(spawn_t)
        self._char_ripples = keep

        # ── Mouth + eye state ─────────────────────────────────────────────────
        mouth_open = math.sin(t * 10) > 0.15
        blinking   = (self._char_blink_next <= t < self._char_blink_next + 0.12)
        if t > self._char_blink_next + 0.15:
            self._char_blink_next = t + random.uniform(2.5, 5.0)

        # ── Gentle float bob ──────────────────────────────────────────────────
        bob = int(math.sin(t * 2.4) * 2.0 * S)

        # ── Render RGBA frame at 3× resolution ───────────────────────────────
        img  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        cr, cg, cb = _hex_to_rgb(color)

        # Ripple rings (drawn behind character)
        for spawn_t in keep:
            age    = t - spawn_t
            frac   = age / 0.65
            radius = int((30 + frac * 22) * S)
            alpha  = int(210 * (1.0 - frac))
            w_px   = max(1, round(2.5 * (1.0 - frac) * S))
            draw.ellipse(
                [cx - radius, cy - radius, cx + radius, cy + radius],
                outline=(cr, cg, cb, alpha), width=w_px)

        # Character body
        draw_fn = {
            "Robot": self._pil_robot,
            "Buddy": self._pil_buddy,
            "Ghost": self._pil_ghost,
            "Alien": self._pil_alien,
        }.get(style, self._pil_robot)
        draw_fn(draw, cx, cy + bob, color, S, mouth_open, blinking)

        # Composite RGBA onto PILL_CHROMA background → downsample → PhotoImage
        bg = Image.new("RGB", (W, H), _hex_to_rgb(PILL_CHROMA))
        bg.paste(img, mask=img.split()[3])
        frame = bg.resize((CHAR_WIN_W, CHAR_WIN_H), Image.LANCZOS)

        self._char_pimg = ImageTk.PhotoImage(frame)
        self._char_canvas.itemconfig(self._char_cv_id, image=self._char_pimg)

        self._char_anim_id = self.root.after(33, self._animate_char)

    # ── PIL character drawing helpers (3× coords via S) ───────────────────────
    def _pil_robot(self, draw, cx, cy, col, S, mouth_open, blinking):
        r   = 28 * S
        drk = _darken(col, 0.50)
        cr, cg, cb = _hex_to_rgb(col)
        dr, dg, db = _hex_to_rgb(drk)
        # Soft glow halo (larger semi-transparent ellipse)
        draw.ellipse(
            [cx - r - 5*S, cy - r - 5*S, cx + r + 5*S, cy + r + 5*S],
            fill=(dr, dg, db, 140))
        # Antenna stem + ball
        draw.line([(cx, cy - r - S), (cx, cy - r - 12*S)],
                  fill=(cr, cg, cb, 255), width=2*S)
        draw.ellipse(
            [cx - 4*S, cy - r - 17*S, cx + 4*S, cy - r - 9*S],
            fill=(cr, cg, cb, 255))
        # Head (dark-filled circle with coloured rim)
        draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            fill=(*_hex_to_rgb(_darken(col, 0.60)), 255),
            outline=(cr, cg, cb, 255), width=2*S)
        # Eyes (rectangular visor style)
        bh = 3*S if blinking else 9*S
        for ex in [cx - 11*S, cx + 11*S]:
            ey = cy - 6*S
            draw.rectangle([ex - 7*S, ey - bh, ex + 7*S, ey + bh],
                           fill=(204, 232, 255, 255))
            if not blinking:
                draw.rectangle([ex - 3*S, ey - 4*S, ex + 3*S, ey + 4*S],
                               fill=(cr, cg, cb, 255))
                draw.rectangle([ex - 2*S, ey - 3*S, ex - S, ey - 2*S],
                               fill=(255, 255, 255, 255))
        # Horizontal panel crease
        draw.line([(cx - r + 6*S, cy + 2*S), (cx + r - 6*S, cy + 2*S)],
                  fill=(dr, dg, db, 255), width=S)
        # Mouth
        if mouth_open:
            draw.chord(
                [cx - 12*S, cy + 10*S, cx + 12*S, cy + 22*S],
                start=0, end=180,
                fill=(10, 10, 10, 255), outline=(cr, cg, cb, 255))
        else:
            draw.line([(cx - 10*S, cy + 16*S), (cx + 10*S, cy + 16*S)],
                      fill=(cr, cg, cb, 255), width=2*S)

    def _pil_buddy(self, draw, cx, cy, col, S, mouth_open, blinking):
        r   = 28 * S
        drk = _darken(col, 0.52)
        cr, cg, cb = _hex_to_rgb(col)
        dr, dg, db = _hex_to_rgb(drk)
        # Glow halo
        draw.ellipse(
            [cx - r - 4*S, cy - r - 4*S, cx + r + 4*S, cy + r + 4*S],
            fill=(dr, dg, db, 150))
        # Head
        draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            fill=(*_hex_to_rgb(_darken(col, 0.62)), 255),
            outline=(cr, cg, cb, 255), width=2*S)
        # Big round eyes
        bh = 2*S if blinking else 11*S
        for ex in [cx - 12*S, cx + 12*S]:
            ey = cy - 7*S
            draw.ellipse([ex - 9*S, ey - bh, ex + 9*S, ey + bh],
                         fill=(255, 255, 255, 255))
            if not blinking:
                draw.ellipse([ex - 4*S, ey - 5*S, ex + 4*S, ey + 5*S],
                             fill=(cr, cg, cb, 255))
                draw.ellipse([ex - 2*S, ey - 3*S, ex - S, ey - 2*S],
                             fill=(255, 255, 255, 255))
        # Rosy cheeks
        chk = (*_hex_to_rgb(_darken(col, 0.80)), 200)
        draw.ellipse([cx - r + 3*S, cy + 2*S, cx - r + 13*S, cy + 10*S], fill=chk)
        draw.ellipse([cx + r - 13*S, cy + 2*S, cx + r - 3*S, cy + 10*S], fill=chk)
        # Mouth
        if mouth_open:
            draw.chord(
                [cx - 13*S, cy + 10*S, cx + 13*S, cy + 23*S],
                start=0, end=180,
                fill=(10, 10, 10, 255), outline=(cr, cg, cb, 255))
        else:
            draw.arc(
                [cx - 12*S, cy + 11*S, cx + 12*S, cy + 21*S],
                start=0, end=180,
                fill=(cr, cg, cb, 255), width=2*S)

    def _pil_ghost(self, draw, cx, cy, col, S, mouth_open, blinking):
        r   = 26 * S
        drk = _darken(col, 0.50)
        t_now = time.time()
        cr, cg, cb = _hex_to_rgb(col)
        dr, dg, db = _hex_to_rgb(drk)
        # Build ghost polygon: semicircle top + wavy scallop bottom
        pts = []
        for deg in range(0, 181, 10):
            rad = math.radians(deg)
            pts.append((cx + r * math.cos(math.pi - rad),
                        cy - 4*S + r * math.sin(math.pi - rad)))
        segs = 6
        for i in range(segs + 1):
            frac  = i / segs
            wx    = (cx - r) + frac * (2 * r)
            phase = math.sin(t_now * 3 + i * 1.2) * 3 * S
            wy    = (cy + r) + ((5 if i % 2 == 0 else -5) * S) + phase
            pts.append((wx, wy))
        # Glow
        draw.ellipse(
            [cx - r - 4*S, cy - r - 8*S, cx + r + 4*S, cy + r + 4*S],
            fill=(dr, dg, db, 140))
        # Ghost body
        if len(pts) >= 3:
            draw.polygon(pts,
                         fill=(*_hex_to_rgb(_darken(col, 0.60)), 255),
                         outline=(cr, cg, cb, 255))
            # Thicker outline pass
            for i in range(len(pts)):
                a = pts[i]; b = pts[(i + 1) % len(pts)]
                draw.line([a, b], fill=(cr, cg, cb, 255), width=2*S)
        # Eyes
        bh = 2*S if blinking else 9*S
        for ex in [cx - 11*S, cx + 11*S]:
            ey = cy - 8*S
            draw.ellipse([ex - 7*S, ey - bh, ex + 7*S, ey + bh],
                         fill=(255, 255, 255, 255))
            if not blinking:
                draw.ellipse([ex - 3*S, ey - 4*S, ex + 3*S, ey + 4*S],
                             fill=(cr, cg, cb, 255))
        # Mouth
        if mouth_open:
            draw.chord(
                [cx - 10*S, cy + 5*S, cx + 10*S, cy + 17*S],
                start=0, end=180,
                fill=(10, 10, 10, 255), outline=(cr, cg, cb, 255))
        else:
            draw.line([(cx - 8*S, cy + 11*S), (cx + 8*S, cy + 11*S)],
                      fill=(cr, cg, cb, 255), width=2*S)

    def _pil_alien(self, draw, cx, cy, col, S, mouth_open, blinking):
        rx, ry = 24 * S, 30 * S
        drk = _darken(col, 0.50)
        cr, cg, cb = _hex_to_rgb(col)
        dr, dg, db = _hex_to_rgb(drk)
        # Pointed ears (triangles)
        draw.polygon(
            [(cx - rx, cy - 4*S), (cx - rx - 10*S, cy - 20*S),
             (cx - rx + 4*S, cy - 18*S)],
            fill=(cr, cg, cb, 255))
        draw.polygon(
            [(cx + rx, cy - 4*S), (cx + rx + 10*S, cy - 20*S),
             (cx + rx - 4*S, cy - 18*S)],
            fill=(cr, cg, cb, 255))
        # Glow halo + head
        draw.ellipse(
            [cx - rx - 4*S, cy - ry - 4*S, cx + rx + 4*S, cy + ry + 4*S],
            fill=(dr, dg, db, 140))
        draw.ellipse(
            [cx - rx, cy - ry, cx + rx, cy + ry],
            fill=(*_hex_to_rgb(_darken(col, 0.60)), 255),
            outline=(cr, cg, cb, 255), width=2*S)
        # Three eyes in a row
        bh = 2*S if blinking else 7*S
        for ex in [cx - 12*S, cx, cx + 12*S]:
            ey = cy - 9*S
            draw.ellipse([ex - 6*S, ey - bh, ex + 6*S, ey + bh],
                         fill=(255, 255, 255, 255))
            if not blinking:
                draw.ellipse([ex - 3*S, ey - 3*S, ex + 3*S, ey + 3*S],
                             fill=(cr, cg, cb, 255))
        # Mouth
        if mouth_open:
            draw.chord(
                [cx - 11*S, cy + 12*S, cx + 11*S, cy + 24*S],
                start=0, end=180,
                fill=(10, 10, 10, 255), outline=(cr, cg, cb, 255))
        else:
            draw.line([(cx - 10*S, cy + 18*S), (cx + 10*S, cy + 18*S)],
                      fill=(cr, cg, cb, 255), width=S)

    # ════════════════════════════════════════════════════════════════════════════
    #  Model loading
    # ════════════════════════════════════════════════════════════════════════════
    def _load_model(self):
        name = self.current_model
        self.root.after(0, lambda: self._badge.configure(text=f"loading {name}…"))
        self.root.after(0, lambda: self._set_status(
            "Loading AI model…",
            f"Downloading whisper/{name} — one moment",
            "#ffd60a"))
        try:
            self.model = WhisperModel(name, device="cpu", compute_type="int8")
            self.model_loaded = True
            self.root.after(0, lambda: self._badge.configure(
                text=f"whisper / {name}"))
            self.root.after(0, lambda: self._set_status(
                "Ready",
                "Hold  Right Alt  anywhere to dictate",
                GREEN_DONUT))
            self.root.after(0, self._refresh_diag_model)
            self._diag_add(f"✅ Model whisper/{name} ready")
        except Exception as e:
            self.root.after(0, lambda: self._set_status(
                "Model error", str(e)[:60], "#ff3b30"))

    # ════════════════════════════════════════════════════════════════════════════
    #  Keyboard
    # ════════════════════════════════════════════════════════════════════════════
    def _on_press(self, key):
        # Log every key so diagnostics can see what pynput detects
        key_str = str(key)
        self._last_key = key_str
        self.root.after(0, self._refresh_diag_key)

        # ── Hotkey capture mode ─────────────────────────────────────────────────
        if self.capturing_hotkey:
            self._set_hotkey(key)
            return

        if key_str != self._hotkey_str:
            return

        self._diag_add(f"{self._hotkey_display} pressed")

        if self.recording or self.transcribing:
            self._diag_add("⚠ Already recording/transcribing — ignored")
            return
        if not self.model_loaded:
            self._diag_add("⚠ Model not loaded yet")
            self.root.after(0, lambda: self._set_status(
                "Not ready", "Model still loading…", "#ffd60a"))
            return

        self.recording = True
        self.audio_chunks = []
        self.session_start = time.time()

        mic_name = self._mic_var.get()
        dev_idx  = self.mic_index_map.get(mic_name)
        self._diag_add(f"Opening mic: {mic_name} (idx={dev_idx})")

        try:
            self.stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1, dtype="float32",
                device=dev_idx,
                callback=self._audio_cb)
            self.stream.start()
            self._diag_add("✅ Recording started")
        except Exception as e:
            self._diag_add(f"❌ Mic error: {e}")
            print(f"Audio error: {e}")
            self.recording = False
            return

        self.root.after(0, lambda: self._set_status(
            "Listening…",
            "Speak now — release  Right Alt  to stop",
            GREEN_DONUT))
        self.root.after(0, self._show_pill)

    def _on_release(self, key):
        if str(key) != self._hotkey_str:
            return
        if not self.recording:
            return

        # Crucial Windows Fix: Releasing an Alt key sequentially focuses the OS Menu Bar.
        # Tapping an inert key (Ctrl) immediately cancels this and preserves box focus!
        if "alt" in self._hotkey_str.lower():
            self.kb.tap(pynput_keyboard.Key.ctrl)

        elapsed = time.time() - (self.session_start or time.time())
        self.recording = False
        self._diag_add(f"Right Alt released — {elapsed:.1f}s recorded, "
                       f"{len(self.audio_chunks)} chunks")

        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        self.stats["sessions_today"]  += 1
        self.stats["sessions_total"]  += 1
        self.stats["secs_today"]      += elapsed

        self.root.after(0, self._stop_anim)
        self.root.after(0, lambda: self._set_status(
            "Transcribing…", "Almost done…", "#ffd60a"))

        chunks = self.audio_chunks.copy()
        threading.Thread(target=self._transcribe,
                         args=(chunks,), daemon=True).start()

    # ════════════════════════════════════════════════════════════════════════════
    #  Audio
    # ════════════════════════════════════════════════════════════════════════════
    def _audio_cb(self, indata, frames, time_info, status):
        if self.recording:
            self.audio_chunks.append(indata.copy())
            self.amplitude = float(np.sqrt(np.mean(indata ** 2)))

    # ════════════════════════════════════════════════════════════════════════════
    #  Transcription
    # ════════════════════════════════════════════════════════════════════════════
    def _transcribe(self, chunks):
        self.transcribing = True
        self._diag_add("Transcribing…")
        try:
            if not chunks:
                self._diag_add("⚠ No audio chunks captured")
                self._reset_ready()
                return

            audio = np.concatenate(chunks, axis=0).flatten().astype(np.float32)
            dur   = len(audio) / SAMPLE_RATE
            peak  = float(np.max(np.abs(audio)))
            self._diag_add(f"Audio: {dur:.2f}s, peak={peak:.4f}")

            if dur < 0.4:
                self._diag_add("⚠ Too short (<0.4s) — ignored")
                self._reset_ready()
                return

            if peak < 0.001:
                self._diag_add("⚠ Audio is silent (peak < 0.001) — check mic gain")

            segments, _ = self.model.transcribe(
                audio, beam_size=5,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 250})
            text = " ".join(s.text for s in segments).strip()

            if text:
                self._diag_add(f'✅ Transcribed: "{text[:50]}"')

                import re as _re
                _tl = text.strip()          # original casing kept for paste
                _tl_low = _tl.lower()       # lower for all comparisons

                # ── AI wake-word check ───────────────────────────────────────────
                ai_ww = self._config.get("ai_wake_word", "assistant").strip().lower()
                if ai_ww and _tl_low.startswith(ai_ww):
                    # Strip the wake word (and any trailing punctuation/space)
                    query = _tl[len(ai_ww):].strip().lstrip(",.!?:;— ").strip()
                    if query:
                        self._diag_add(f'🤖 AI wake word "{ai_ww}" — query: "{query[:40]}"')
                        self.root.after(0, lambda: self._set_status(
                            "🤖 Thinking…", "Asking Gemini…", AI_BLUE))
                        self.root.after(0, self._hide_pill)
                        threading.Thread(
                            target=self._handle_ai_query,
                            args=(query,), daemon=True).start()
                        self.transcribing = False
                        return
                    else:
                        self._diag_add(f'🤖 Wake word heard but no query — dictating normally')
                # ───────────────────────────────────────────────────────────────

                # ── "Write a prompt" — Gemini writes & pastes at cursor ──────────
                wp_phrase = self._config.get(
                    "write_prompt_phrase", "write a prompt").strip().lower()
                if wp_phrase and _tl_low.startswith(wp_phrase):
                    prompt_body = _tl[len(wp_phrase):].strip().lstrip(",.!?:;— ").strip()
                    if prompt_body:
                        self._diag_add(f'✍️ Write-prompt: "{prompt_body[:40]}"')
                        self.root.after(0, lambda: self._set_status(
                            "✍️ Writing…", prompt_body[:45], "#ff9f0a"))
                        self.root.after(0, self._hide_pill)
                        threading.Thread(
                            target=self._handle_write_prompt,
                            args=(prompt_body,), daemon=True).start()
                        self.transcribing = False
                        return
                # ───────────────────────────────────────────────────────────────

                # ── "Fix that" / "Fix it" — rewrite clipboard for clarity ────────
                _clean = _tl_low.rstrip(".,!? ")
                if _clean in ("fix that", "fix it", "improve that", "improve it",
                              "clean that up", "clean it up"):
                    self._diag_add("🛠 Fix-that: rewriting clipboard with Gemini")
                    self.root.after(0, lambda: self._set_status(
                        "🛠 Fixing…", "Rewriting clipboard text…", "#bf5af2"))
                    self.root.after(0, self._hide_pill)
                    threading.Thread(
                        target=self._handle_rewrite_clipboard,
                        args=("fix",), daemon=True).start()
                    self.transcribing = False
                    return
                # ───────────────────────────────────────────────────────────────

                # ── "Make that X" — tone-rewrite clipboard ──────────────────────
                _make_m = _re.match(
                    r'^make\s+(?:it|that)\s+(.+)', _clean)
                if _make_m:
                    modifier = _make_m.group(1).strip()
                    self._diag_add(f'🎨 Make-that: "{modifier}"')
                    self.root.after(0, lambda: self._set_status(
                        "🎨 Rewriting…", f"Making it {modifier}…", "#bf5af2"))
                    self.root.after(0, self._hide_pill)
                    threading.Thread(
                        target=self._handle_rewrite_clipboard,
                        args=(modifier,), daemon=True).start()
                    self.transcribing = False
                    return
                # ───────────────────────────────────────────────────────────────

                # ── "Read this" — read clipboard aloud via TTS ──────────────────
                if _clean in ("read this", "read clipboard", "read that",
                              "read it", "read it back"):
                    self._diag_add("🔊 Read-this: reading clipboard aloud")
                    self.root.after(0, lambda: self._set_status(
                        "🔊 Reading…", "Reading clipboard aloud…", AI_BLUE))
                    self.root.after(0, self._hide_pill)
                    threading.Thread(
                        target=self._handle_read_clipboard, daemon=True).start()
                    self.transcribing = False
                    return
                # ───────────────────────────────────────────────────────────────

                # ── Voice macro check ────────────────────────────────────────────
                macros = self._config.get("voice_macros", {})
                for mac_trigger, mac_expansion in macros.items():
                    if _clean == mac_trigger.lower().rstrip(".,!? "):
                        self._diag_add(f'⚡ Macro "{mac_trigger}" → pasting expansion')
                        self.root.after(0, lambda: self._set_status(
                            f'⚡ Macro!', mac_trigger, GREEN_DONUT))
                        self._type_text(mac_expansion)
                        self.root.after(2000, self._reset_ready)
                        self.transcribing = False
                        return
                # ───────────────────────────────────────────────────────────────

                # ── Codeword check ──────────────────────────────────────────────
                cw = self._config.get("codeword", "").strip().lower()
                if cw and cw in text.lower():
                    self._diag_add(f'⚡ Codeword "{cw}" detected — firing!')
                    self.root.after(0, lambda: self._set_status(
                        f'⚡ "{cw}" detected!', "Launching animation & apps…",
                        "#ffd60a"))
                    self.root.after(0, lambda: self._trigger_codeword(test=False))
                    self.root.after(0, self._hide_pill)
                    self.transcribing = False
                    return
                # ───────────────────────────────────────────────────────────────

                wc = len(text.split())
                self.stats["words_today"] += wc
                self.stats["words_total"] += wc
                self.log.append({
                    "text": text,
                    "time": time.strftime("%Y-%m-%d %H:%M"),
                })
                self._save_stats()
                self._save_log()

                prev = text[:45] + ("…" if len(text) > 45 else "")
                self.root.after(0, lambda: self._set_status(
                    "Done ✓", f'"{prev}"', GREEN_DONUT))
                self.root.after(0, self._refresh_dictations_page)

                # ── Auto-punctuation (optional) ──────────────────────────────────
                if self._config.get("auto_punctuate", False):
                    text = self._auto_punctuate(text)

                self._type_text(text)
                self.root.after(2500, self._reset_ready)
            else:
                self._diag_add("⚠ Whisper returned empty text")
                self._reset_ready()

        except Exception as e:
            self._diag_add(f"❌ Error: {e}")
            print(f"Transcription error: {e}")
            self._reset_ready()
        finally:
            self.root.after(0, self._hide_pill)
            self.transcribing = False

    def _start_hotkey_capture(self):
        """Enter capture mode — next keypress becomes the new hotkey."""
        if self.recording or self.transcribing:
            return
        self.capturing_hotkey = True
        try:
            self._capture_btn.configure(
                text="  … press any key …  ",
                bg="#2d2410", fg="#d4aa30")
            self._hotkey_badge.configure(text="  ?  ", bg="#2d2410")
        except Exception:
            pass

    def _set_hotkey(self, key):
        """Called from _on_press when capturing_hotkey is True."""
        self.capturing_hotkey = False
        key_str     = str(key)
        key_display = self._key_display(key)

        self._hotkey_str     = key_str
        self._hotkey_display = key_display

        self._config["hotkey_str"]     = key_str
        self._config["hotkey_display"] = key_display
        self._save_config()

        self._diag_add(f"Hotkey set to: {key_display} ({key_str})")

        self.root.after(0, lambda: self._apply_hotkey_ui(key_display))

    def _apply_hotkey_ui(self, display):
        try:
            self._hotkey_badge.configure(
                text=f"  {display}  ", bg="#3a3a3c")
            self._capture_btn.configure(
                text="  Change Hotkey  ", bg=SEL_BG, fg=SEL_TEXT)
            # Also update the status bar subtitle
            self._set_status(
                "Ready",
                f"Hold  {display}  anywhere to dictate",
                GREEN_DONUT)
        except Exception:
            pass

    def _manual_start(self):
        """Manual dictate button pressed — same as Right Alt press."""
        self._diag_add("Manual dictate started")
        try:
            self._manual_btn.configure(bg="#3d1515", fg="#cc0000",
                                       text="  ■  Recording…  ")
        except Exception:
            pass
        self._on_press(pynput_keyboard.Key.alt_r)

    def _manual_stop(self):
        """Manual dictate button released — same as Right Alt release."""
        self._diag_add("Manual dictate stopped")
        try:
            self._manual_btn.configure(bg=SEL_BG, fg=SEL_TEXT,
                                       text="  ▶  Hold to Dictate Manually  ")
        except Exception:
            pass
        self._on_release(pynput_keyboard.Key.alt_r)

    def _reset_ready(self):
        self.root.after(0, self._hide_pill)
        self.root.after(0, lambda: self._set_status(
            "Ready", "Hold  Right Alt  anywhere to dictate", GREEN_DONUT))

    # ════════════════════════════════════════════════════════════════════════════
    #  Typing
    # ════════════════════════════════════════════════════════════════════════════
    def _type_text(self, text):
        try:
            old = ""
            try:
                old = pyperclip.paste()
            except Exception:
                pass

            self.root.after(0, self._hide_pill)
            time.sleep(0.25)  # Wait for OS to restore focus to original window prior to pill pop-up

            pyperclip.copy(text)
            time.sleep(0.15)  # Give clipboard subsystem time to register the new content

            # Standard Ctrl + V (Much faster and avoids Windows Menu-Bar mnemonic shortcuts)
            with self.kb.pressed(Key.ctrl):
                self.kb.tap("v")
            
            time.sleep(0.6)   # Give target applications adequate time to process clipboard

            try:
                pyperclip.copy(old)
            except Exception:
                pass
        except Exception as e:
            print(f"Type error: {e}")

    # ════════════════════════════════════════════════════════════════════════════
    #  AI response popup
    # ════════════════════════════════════════════════════════════════════════════
    # ── Popup palette ─────────────────────────────────────────────────────────
    _PP_BG    = "#111113"   # popup background — deep dark
    _PP_HDR   = "#0c0c0e"   # header strip — even darker
    _PP_CHIP  = "#1c1c20"   # question chip background
    _PP_BORD  = "#2e2e34"   # chip border / divider

    def _build_ai_popup(self):
        """Build the redesigned floating AI response card."""
        P = self._PP_BG;  H = self._PP_HDR;  CH = self._PP_CHIP;  BD = self._PP_BORD
        w = self._ai_win = tk.Toplevel(self.root)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        w.attributes("-alpha",   0.0)   # invisible until entrance anim
        w.configure(bg=P)
        w.withdraw()

        # ── Header (dark strip) ──────────────────────────────────────────────
        hdr = tk.Frame(w, bg=H, height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        # Glowing AI icon  (small canvas)
        ic = tk.Canvas(hdr, width=36, height=36, bg=H, highlightthickness=0)
        ic.pack(side="left", padx=(14, 8), pady=8)
        ic.create_oval(2,  2,  34, 34, fill=ACCENT_LITE, outline=ACCENT, width=1.5)
        ic.create_text(18, 18, text="AI", fill=ACCENT_TEXT,
                       font=("Helvetica Neue", 10, "bold"))

        # Title + status stacked vertically
        title_col = tk.Frame(hdr, bg=H)
        title_col.pack(side="left", fill="y", pady=6)
        tk.Label(title_col, text="ASSISTANT", bg=H, fg=ACCENT_TEXT,
                 font=("Helvetica Neue", 10, "bold")).pack(anchor="w")
        self._ai_status_lbl = tk.Label(title_col, text="", bg=H, fg=T_SEC,
                                        font=("Helvetica Neue", 9))
        self._ai_status_lbl.pack(anchor="w")

        # Close button
        self._ai_close_lbl = tk.Label(hdr, text="✕", bg=H, fg="#606070",
                                       font=("Helvetica Neue", 13), cursor="hand2")
        self._ai_close_lbl.pack(side="right", padx=(0, 14))
        self._ai_close_lbl.bind("<Button-1>", lambda e: self._hide_ai_popup())

        # Stop button (hidden until speaking)
        self._ai_stop_btn = tk.Label(
            hdr, text="⏹  Stop", bg="#3d1515", fg="#ff6b6b",
            font=("Helvetica Neue", 9, "bold"), padx=G, pady=3,
            cursor="hand2", relief="flat")
        self._ai_stop_btn.bind("<Button-1>", lambda e: self._stop_speaking())
        # Not packed here — revealed by _handle_ai_query

        # ── Gradient accent bar (green → blue, 2 px) ─────────────────────────
        acc_cv = tk.Canvas(w, height=2, bg=P, highlightthickness=0)
        acc_cv.pack(fill="x")
        def _draw_grad(ev=None):
            acc_cv.delete("all")
            W = acc_cv.winfo_width() or AI_POPUP_W
            segs = 12
            for i in range(segs):
                f = i / segs
                r2 = int(48  - 38 * f)
                g2 = int(209 - 77 * f)
                b2 = int(88  + 167 * f)
                x1 = int(W * i / segs)
                x2 = int(W * (i + 1) / segs)
                acc_cv.create_rectangle(x1, 0, x2, 2,
                                        fill=f"#{r2:02x}{g2:02x}{b2:02x}", outline="")
        acc_cv.bind("<Configure>", _draw_grad)

        # ── Question chip ────────────────────────────────────────────────────
        q_outer = tk.Frame(w, bg=CH, highlightthickness=1,
                           highlightbackground=BD)
        q_outer.pack(fill="x", padx=16, pady=(14, 6))
        q_inner = tk.Frame(q_outer, bg=CH)
        q_inner.pack(fill="x", padx=12, pady=(8, 10))
        tk.Label(q_inner, text="YOU ASKED", bg=CH, fg=T_TER,
                 font=("Helvetica Neue", 8, "bold")).pack(anchor="w")
        self._ai_q_lbl = tk.Label(
            q_inner, text="", bg=CH, fg=T_SEC,
            font=("Helvetica Neue", 11, "italic"),
            wraplength=AI_POPUP_W - 68, justify="left", anchor="w")
        self._ai_q_lbl.pack(anchor="w", pady=(2, 0))

        # ── Answer section ───────────────────────────────────────────────────
        ans_frame = tk.Frame(w, bg=P)
        ans_frame.pack(fill="x", padx=16, pady=(4, 0))
        tk.Label(ans_frame, text="ANSWER", bg=P, fg=T_TER,
                 font=("Helvetica Neue", 8, "bold")).pack(anchor="w")
        self._ai_a_lbl = tk.Label(
            ans_frame, text="", bg=P, fg=T_PRI,
            font=("Helvetica Neue", 13),
            wraplength=AI_POPUP_W - 36, justify="left", anchor="w")
        self._ai_a_lbl.pack(anchor="w", pady=(4, 0))

        # ── Speaking waveform (mini bars, shown while AI speaks) ─────────────
        self._popup_wave_cv  = tk.Canvas(w, height=30, bg=P, highlightthickness=0)
        self._popup_wave_cv.pack(fill="x", padx=16, pady=(10, 14))
        self._popup_wave_id  = None
        self._popup_wave_bh  = [2.0] * 8

        # ── Drag support ─────────────────────────────────────────────────────
        def _ds(e): w._dx, w._dy = e.x_root - w.winfo_x(), e.y_root - w.winfo_y()
        def _dm(e): w.geometry(f"+{e.x_root-w._dx}+{e.y_root-w._dy}")
        hdr.bind("<ButtonPress-1>", _ds)
        hdr.bind("<B1-Motion>",     _dm)

    def _show_ai_popup(self, question, answer):
        """Animate popup in, then type the answer."""
        q_short = (question[:72] + "…") if len(question) > 72 else question
        self._ai_q_lbl.configure(text=q_short)
        self._ai_a_lbl.configure(text="")          # clear — will be typed in
        self._ai_status_lbl.configure(text="• Thinking…")

        # Stop any running popup wave
        self._stop_popup_wave()

        # Measure height, position window
        self._ai_win.update_idletasks()
        ph = self._ai_win.winfo_reqheight() or 240
        sw = self.root.winfo_screenwidth()
        px = (sw - AI_POPUP_W) // 2
        # Popup sits just below the floating pill (pill top=14, height=PILL_H)
        popup_target_y = 14 + PILL_H + 18     # 14 + 130 + 18 = 162
        popup_start_y  = popup_target_y - 30  # slide in from 30px above
        self._popup_x = px;  self._popup_h = ph;  self._popup_y = popup_target_y

        # Start above final position, invisible
        self._ai_win.geometry(f"{AI_POPUP_W}x{ph}+{px}+{popup_start_y}")
        self._ai_win.attributes("-alpha", 0.0)
        self._ai_win.deiconify()
        self._ai_win.lift()

        # Cancel any pending dismiss timer
        if self._ai_popup_id:
            self.root.after_cancel(self._ai_popup_id)
            self._ai_popup_id = None

        # Kick off entrance animation, then type answer
        self._popup_enter_anim()
        self.root.after(120, lambda: self._popup_type(answer))

    def _popup_enter_anim(self, step=0, n=14):
        """Slide down + fade in."""
        if step > n:
            return
        # Apply Win11 rounded corners + accent border on very first frame
        if step == 1:
            try:
                hwnd = ctypes.windll.user32.GetParent(
                    self._ai_win.winfo_id()) or self._ai_win.winfo_id()
                _apply_win11_style(hwnd)
            except Exception:
                pass
        t    = step / n
        ease = 1 - (1 - t) ** 3       # cubic ease-out
        start_y = self._popup_y - 30
        y    = int(start_y + ease * (self._popup_y - start_y))
        alp  = ease
        try:
            self._ai_win.geometry(
                f"{AI_POPUP_W}x{self._popup_h}+{self._popup_x}+{y}")
            self._ai_win.attributes("-alpha", alp)
        except Exception:
            return
        self.root.after(14, lambda: self._popup_enter_anim(step + 1, n))

    def _popup_type(self, text, idx=0):
        """Reveal answer text one character at a time."""
        try:
            if not self._ai_win.winfo_viewable():
                return
        except Exception:
            return
        try:
            self._ai_a_lbl.configure(text=text[:idx])
        except Exception:
            return
        if idx < len(text):
            ch    = text[idx]
            delay = 6 if ch in " \n," else 17
            self.root.after(delay, lambda: self._popup_type(text, idx + 1))
        else:
            try:
                self._ai_status_lbl.configure(text="• Speaking…")
            except Exception:
                pass

    def _hide_ai_popup(self):
        """Fade out the popup."""
        if self._ai_popup_id:
            self.root.after_cancel(self._ai_popup_id)
            self._ai_popup_id = None
        self._stop_popup_wave()
        self._popup_exit_anim()

    def _popup_exit_anim(self, step=0, n=9):
        """Fade out animation."""
        if step > n:
            try:
                self._ai_win.withdraw()
                self._ai_win.attributes("-alpha", 0.0)
            except Exception:
                pass
            return
        alp = max(0.0, 1.0 - step / n)
        try:
            self._ai_win.attributes("-alpha", alp)
        except Exception:
            pass
        self.root.after(18, lambda: self._popup_exit_anim(step + 1, n))

    # ── Popup speaking waveform ───────────────────────────────────────────────
    def _start_popup_wave(self):
        self._popup_wave_bh = [2.0] * 8
        self._animate_popup_wave()

    def _stop_popup_wave(self):
        if self._popup_wave_id:
            self.root.after_cancel(self._popup_wave_id)
            self._popup_wave_id = None
        try:
            self._popup_wave_cv.delete("all")
        except Exception:
            pass

    def _animate_popup_wave(self):
        if not self._ai_speaking:
            self._stop_popup_wave()
            return
        t  = time.time()
        c  = self._popup_wave_cv
        c.delete("all")
        W  = c.winfo_width() or (AI_POPUP_W - 32)
        H, mid = 30, 15
        n, bw, bg_gap = 8, 5, 6
        x0 = (W - (n * bw + (n - 1) * bg_gap)) // 2
        for i in range(n):
            wave     = math.sin(t * 8 + i * 0.8) * 0.5 + 0.5
            target   = max(3.0, wave * (mid - 3))
            self._popup_wave_bh[i] = (self._popup_wave_bh[i] * 0.35
                                      + target * 0.65)
            hh  = self._popup_wave_bh[i]
            xb  = x0 + i * (bw + bg_gap)
            # Amplitude → green shade
            s   = min(1.0, hh / (mid - 3))
            col = f"#{int(30+30*s):02x}{int(140+69*s):02x}{int(70+18*s):02x}"
            # Pill-shaped bar (oval)
            c.create_oval(xb, mid - hh, xb + bw, mid + hh,
                          fill=col, outline="")
        self._popup_wave_id = self.root.after(33, self._animate_popup_wave)

    def _stop_speaking(self):
        """Interrupt TTS mid-playback."""
        self._tts_stop_event.set()
        self._ai_speaking = False
        # Stop pygame playback immediately if it is running
        try:
            if _PYGAME_AVAILABLE and _pygame.mixer.music.get_busy():
                _pygame.mixer.music.stop()
        except Exception:
            pass
        self._hide_char_speaking()
        self._stop_popup_wave()
        try:
            self._ai_stop_btn.pack_forget()
        except Exception:
            pass
        try:
            self._ai_status_lbl.configure(text="• Stopped")
        except Exception:
            pass

    # ════════════════════════════════════════════════════════════════════════════
    #  AI backend — query + TTS
    # ════════════════════════════════════════════════════════════════════════════
    def _handle_ai_query(self, query: str):
        """Background thread: Gemini query → show popup → speak response."""
        try:
            self._diag_add(f'🤖 Querying Gemini: "{query[:40]}"')
            answer = self._query_gemini(query)
            self._diag_add(f'🤖 Response: "{answer[:60]}"')

            # Show popup + update status in main thread
            self.root.after(0, lambda: self._show_ai_popup(query, answer))
            preview = (answer[:55] + "…") if len(answer) > 55 else answer
            self.root.after(0, lambda: self._set_status(
                "🤖 Speaking…", preview, AI_BLUE))

            # Speak the response (blocks this thread)
            self._ai_speaking = True
            self.root.after(0, lambda: self._ai_stop_btn.pack(
                side="right", padx=(0, 6),
                before=self._ai_close_lbl))
            self.root.after(0, self._show_char_speaking)
            self.root.after(0, self._start_popup_wave)
            self._speak_response(answer)
            self._ai_speaking = False
            self.root.after(0, self._stop_popup_wave)
            self.root.after(0, self._hide_char_speaking)
            self.root.after(0, lambda: self._ai_stop_btn.pack_forget())

            # After speaking: mark done, reset status after short delay
            self.root.after(0, lambda: self._ai_status_lbl.configure(text="• Done ✓"))
            self.root.after(4000, self._hide_ai_popup)
            self.root.after(0, lambda: self._set_status(
                "Ready",
                f"Hold  {self._hotkey_display}  anywhere to dictate",
                GREEN_DONUT))

        except Exception as exc:
            self._diag_add(f"❌ AI error: {exc}")
            self.root.after(0, lambda: self._set_status(
                "AI Error", str(exc)[:60], "#ff3b30"))
            self.root.after(3000, self._reset_ready)
        finally:
            self._ai_speaking = False
            self.transcribing = False

    def _query_gemini(self, query: str) -> str:
        """Call Gemini REST API, return response text."""
        api_key = self._config.get("gemini_api_key", "").strip()
        if not api_key:
            return ("No Gemini API key set. Please open the AI page in the app "
                    "and paste your key from aistudio.google.com.")

        model   = self._config.get("gemini_model", "gemini-1.5-flash")
        url     = (f"https://generativelanguage.googleapis.com/v1beta/"
                   f"models/{model}:generateContent?key={api_key}")

        # Build contents with history
        max_turns  = int(self._config.get("ai_max_history", 5))
        # Each turn = 2 entries (user + model); slice to keep last N turns
        hist_slice = self._ai_history[-(max_turns * 2):]
        contents   = hist_slice + [
            {"role": "user", "parts": [{"text": query}]}
        ]

        sys_prompt = self._config.get(
            "ai_system_prompt",
            "You are a helpful voice assistant. Give concise, natural responses "
            "suitable for text-to-speech. Keep answers under 3 sentences unless "
            "the user asks for more detail. Do not use markdown or bullet points."
        )

        payload = json.dumps({
            "system_instruction": {"parts": [{"text": sys_prompt}]},
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 512,
            }
        }).encode("utf-8")

        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST")

        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()

            # Persist to history
            self._ai_history.append(
                {"role": "user",  "parts": [{"text": query}]})
            self._ai_history.append(
                {"role": "model", "parts": [{"text": text}]})
            # Trim
            if len(self._ai_history) > max_turns * 2:
                self._ai_history = self._ai_history[-(max_turns * 2):]

            return text

        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                msg = json.loads(raw)["error"]["message"]
            except Exception:
                msg = raw[:120]
            return f"Gemini error: {msg}"
        except urllib.error.URLError as exc:
            return f"Network error: {exc.reason}"
        except Exception as exc:
            return f"Unexpected error: {exc}"

    # ════════════════════════════════════════════════════════════════════════════
    #  New voice-command handlers
    # ════════════════════════════════════════════════════════════════════════════
    def _handle_write_prompt(self, prompt: str):
        """Background thread: ask Gemini to *write* something, then paste it silently."""
        try:
            api_key = self._config.get("gemini_api_key", "").strip()
            if not api_key:
                self.root.after(0, lambda: self._set_status(
                    "No API Key", "Add your Gemini key on the AI page.", "#ff3b30"))
                self.root.after(3000, self._reset_ready)
                return

            model = self._config.get("gemini_model", "gemini-2.0-flash")
            url   = (f"https://generativelanguage.googleapis.com/v1beta/"
                     f"models/{model}:generateContent?key={api_key}")

            write_sys = (
                "You are a professional writing assistant. "
                "The user has spoken a prompt describing text they want written. "
                "Produce ONLY the finished text — no explanations, no preambles, "
                "no markdown formatting, no quotes around the output. "
                "Write naturally, ready to be pasted directly into a document."
            )
            payload = json.dumps({
                "system_instruction": {"parts": [{"text": write_sys}]},
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.8, "maxOutputTokens": 1024},
            }).encode("utf-8")
            req = urllib.request.Request(
                url, data=payload,
                headers={"Content-Type": "application/json"},
                method="POST")

            with urllib.request.urlopen(req, timeout=25) as resp:
                data   = json.loads(resp.read().decode("utf-8"))
            result = data["candidates"][0]["content"]["parts"][0]["text"].strip()

            self._diag_add(f'✍️ Written ({len(result)} chars) — pasting')
            self.root.after(0, lambda: self._set_status(
                "✍️ Done!", f"{len(result.split())} words written", "#ff9f0a"))
            self._type_text(result)
            self.root.after(2500, self._reset_ready)

        except Exception as exc:
            self._diag_add(f"❌ Write-prompt error: {exc}")
            self.root.after(0, lambda: self._set_status(
                "Write Error", str(exc)[:60], "#ff3b30"))
            self.root.after(3000, self._reset_ready)
        finally:
            self.transcribing = False

    def _handle_rewrite_clipboard(self, modifier: str):
        """Background thread: read clipboard → Gemini rewrite → paste replacement.

        modifier can be:
          "fix"            → correct grammar / clarity
          "formal"         → professional tone
          "casual"         → conversational tone
          "shorter"        → concise version
          "longer"         → expanded version
          "an email"       → restructure as an email
          "bullet points"  → convert to bullet list
          or any freeform instruction the user spoke
        """
        try:
            try:
                clip = pyperclip.paste()
            except Exception:
                clip = ""

            if not clip or not clip.strip():
                self.root.after(0, lambda: self._set_status(
                    "Nothing to rewrite",
                    "Copy some text first, then say the command.",
                    "#ff3b30"))
                self.root.after(3000, self._reset_ready)
                return

            api_key = self._config.get("gemini_api_key", "").strip()
            if not api_key:
                self.root.after(0, lambda: self._set_status(
                    "No API Key", "Add your Gemini key on the AI page.", "#ff3b30"))
                self.root.after(3000, self._reset_ready)
                return

            # Build the instruction
            _instructions = {
                "fix":           "Fix the grammar, clarity, and flow of this text. Return only the improved version.",
                "formal":        "Rewrite this text in a formal, professional tone. Return only the rewritten version.",
                "casual":        "Rewrite this text in a casual, friendly tone. Return only the rewritten version.",
                "shorter":       "Make this text significantly more concise without losing meaning. Return only the shortened version.",
                "longer":        "Expand this text with more detail and explanation. Return only the expanded version.",
                "an email":      "Rewrite this as a well-structured professional email. Return only the email text.",
                "bullet points": "Convert this text into clear bullet points. Return only the bullet list.",
            }
            instruction = _instructions.get(
                modifier.lower(),
                f"Rewrite this text to be {modifier}. Return only the rewritten version.")

            model   = self._config.get("gemini_model", "gemini-2.0-flash")
            url     = (f"https://generativelanguage.googleapis.com/v1beta/"
                       f"models/{model}:generateContent?key={api_key}")
            payload = json.dumps({
                "system_instruction": {"parts": [{"text":
                    "You are a text editing assistant. Rewrite exactly what is "
                    "requested. Return ONLY the rewritten text — no preamble, "
                    "no explanation, no markdown formatting."
                }]},
                "contents": [{"role": "user", "parts": [{"text":
                    f"{instruction}\n\nText to rewrite:\n{clip}"
                }]}],
                "generationConfig": {"temperature": 0.5, "maxOutputTokens": 1024},
            }).encode("utf-8")

            req = urllib.request.Request(
                url, data=payload,
                headers={"Content-Type": "application/json"},
                method="POST")
            with urllib.request.urlopen(req, timeout=25) as resp:
                data   = json.loads(resp.read().decode("utf-8"))
            result = data["candidates"][0]["content"]["parts"][0]["text"].strip()

            self._diag_add(f'🎨 Rewrite "{modifier}" done — pasting')
            self.root.after(0, lambda: self._set_status(
                "🎨 Rewritten!", f"Pasted {modifier} version", "#bf5af2"))
            self._type_text(result)
            self.root.after(2500, self._reset_ready)

        except Exception as exc:
            self._diag_add(f"❌ Rewrite error: {exc}")
            self.root.after(0, lambda: self._set_status(
                "Rewrite Error", str(exc)[:60], "#ff3b30"))
            self.root.after(3000, self._reset_ready)
        finally:
            self.transcribing = False

    def _handle_read_clipboard(self):
        """Background thread: read clipboard content aloud via TTS."""
        try:
            try:
                clip = pyperclip.paste()
            except Exception:
                clip = ""

            if not clip or not clip.strip():
                self.root.after(0, lambda: self._set_status(
                    "Nothing to read",
                    "Copy some text first, then say 'read this'.",
                    "#ff3b30"))
                self.root.after(3000, self._reset_ready)
                return

            read_text = clip.strip()
            if len(read_text) > 3000:
                read_text = read_text[:3000] + "… (truncated)"

            self._diag_add(f"🔊 Read-clipboard: {len(read_text)} chars")
            self.root.after(0, self._show_char_speaking)
            self._speak_response(read_text)
            self.root.after(0, self._hide_char_speaking)
            self.root.after(0, lambda: self._set_status(
                "Done ✓", "Finished reading clipboard", GREEN_DONUT))
            self.root.after(2500, self._reset_ready)

        except Exception as exc:
            self._diag_add(f"❌ Read-clipboard error: {exc}")
            self.root.after(3000, self._reset_ready)
        finally:
            self.transcribing = False

    def _auto_punctuate(self, text: str) -> str:
        """Capitalise first word; add a period at end if no sentence-ending punctuation."""
        if not text:
            return text
        text = text[0].upper() + text[1:]
        if text[-1] not in ".!?…":
            text = text + "."
        return text

    # ════════════════════════════════════════════════════════════════════════════
    #  TTS — speak response
    # ════════════════════════════════════════════════════════════════════════════
    def _speak_response(self, text: str):
        """Speak AI response — prefers Edge TTS (neural), falls back to pyttsx3."""
        if not text.strip():
            return
        if not self._tts_busy.acquire(blocking=False):
            self._diag_add("⚠️ TTS already running — skipping")
            return
        try:
            import re
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
            if not sentences:
                sentences = [text.strip()]
            self._tts_stop_event.clear()

            use_edge = _EDGE_TTS_AVAILABLE and _PYGAME_AVAILABLE
            self._diag_add(
                f"🔊 TTS: {'Edge Neural' if use_edge else 'pyttsx3' if _TTS_AVAILABLE else 'none'}")
            if use_edge:
                self._speak_edge_tts(sentences)
            elif _TTS_AVAILABLE:
                self._speak_pyttsx3(sentences)
            else:
                self._diag_add("⚠️ No TTS backend — run install.bat")
        finally:
            self._tts_busy.release()

    def _speak_edge_tts(self, sentences: list):
        """Edge TTS: generate neural audio per sentence, play via pygame."""
        voice    = self._config.get("edge_voice", "en-US-AriaNeural")
        rate_wpm = int(self._config.get("tts_rate", 175))
        rate_pct = round((rate_wpm / 150 - 1) * 100)
        rate_str = f"+{rate_pct}%" if rate_pct >= 0 else f"{rate_pct}%"

        for sentence in sentences:
            if self._tts_stop_event.is_set():
                break
            if not sentence.strip():
                continue
            tmp = None
            try:
                tmp = tempfile.NamedTemporaryFile(
                    suffix=".mp3", delete=False, dir=tempfile.gettempdir())
                tmp_path = tmp.name
                tmp.close()

                _asyncio.run(
                    self._edge_generate_async(sentence, voice, rate_str, tmp_path))

                if self._tts_stop_event.is_set():
                    break

                _pygame.mixer.music.load(tmp_path)
                _pygame.mixer.music.play()
                while _pygame.mixer.music.get_busy():
                    if self._tts_stop_event.is_set():
                        _pygame.mixer.music.stop()
                        break
                    time.sleep(0.05)
            except Exception as exc:
                self._diag_add(f"⚠️ Edge TTS sentence error: {exc}")
            finally:
                if tmp is not None:
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass

    async def _edge_generate_async(self, text: str, voice: str,
                                   rate: str, path: str):
        """Async coroutine: generate Edge TTS audio and save to path."""
        communicate = _edge_tts.Communicate(text, voice=voice, rate=rate)
        await communicate.save(path)

    def _speak_pyttsx3(self, sentences: list):
        """Fallback TTS using pyttsx3 (Windows SAPI, offline)."""
        for sentence in sentences:
            if self._tts_stop_event.is_set():
                break
            if not sentence.strip():
                continue
            try:
                engine = _pyttsx3.init()
                rate   = int(self._config.get("tts_rate", 175))
                engine.setProperty("rate", rate)
                voice_name = self._config.get("tts_voice", "")
                if voice_name:
                    for v in engine.getProperty("voices"):
                        if v.name == voice_name:
                            engine.setProperty("voice", v.id)
                            break
                engine.say(sentence)
                engine.runAndWait()
                engine.stop()
            except Exception as exc:
                self._diag_add(f"⚠️ pyttsx3 error: {exc}")