# Sovereign AI Mic

A completely local, ultra-fast dictation engine featuring a modern web UI, Apple-like frosted glass floating indicators, native text integration, and Google Gemini macro support. Runs on **Windows** and **macOS**.

## Overview
Sovereign AI Mic lets you transcribe your voice into any application instantly. By holding a hotkey, your speech is recorded and transcribed locally using Whisper AI, then seamlessly inserted into your active window—bypassing the clipboard on Windows, and using Cmd+V paste on macOS.

It bridges the gap between premium local speech-to-text dictation and modern, premium UI/UX design. The application features a decoupled Python backend paired with an Eel/HTML frontend wrapped in a stunning dark-mode interface.

## Key Features
- **Local Whisper AI Transcription:** Choose from Tiny, Base, or Small models. Everything runs offline for dictation.
- **Native Text Injection:** Uses platform-native APIs — Win32 `keybd_event` on Windows and `Cmd+V` via pynput on macOS — for reliable insertion into every application.
- **Stunning In-App UI:** Displays an Apple "Frosted Glass" pill indicator with active volumetric equalizers anywhere on your screen.
- **Gemini Assistant Integration:** 
  - Say `"Assistant, [question]"` to drop a window on-screen and get AI responses.
  - Say `"Write a prompt, [idea]"` to format complex prompts automatically.
  - Custom Voice Macros to expand short phrases into entire blocks of text (like dropping your email or phone number).
- **Zero Privacy Loss:** Your `config.json` containing your Gemini keys, internal macros, logs, and statistics is never tracked by source control.

---

## Installation

### Windows

#### Prerequisites
1. **Python 3.10+** — download from [python.org](https://www.python.org). During installation, check **"Add Python to PATH"**.
2. **FFmpeg** — download from [ffmpeg.org](https://ffmpeg.org/download.html) and add its `bin` folder to your system `PATH`.
   - To verify: open a Command Prompt and run `ffmpeg -version`.

#### Setup
1. Clone or download this repository.
2. Open the repository folder in a Command Prompt or File Explorer.
3. Double-click **`install.bat`** (or run it from the terminal). It will automatically install all required Python packages:
   ```
   customtkinter, faster-whisper, sounddevice, pynput, pyperclip,
   numpy, Pillow, pyttsx3, edge-tts, pygame
   ```
   The first launch will also download the selected Whisper model (~150 MB).

#### Running
Double-click **`run.bat`** (or run it from a terminal):
```bat
run.bat
```
A Web UI Control Center opens in a Chromium shell. Your floating transcription indicator is now active.

**Hold `Right Alt`** and speak. Release the key to transcribe and inject text into the active window.

---

### macOS

#### Prerequisites
1. **Python 3.10+**
   - Install via [python.org](https://www.python.org) or with [Homebrew](https://brew.sh):
     ```bash
     brew install python
     ```
2. **FFmpeg** — install via Homebrew:
   ```bash
   brew install ffmpeg
   ```
   To verify: run `ffmpeg -version` in Terminal.
3. **Accessibility Permission for pynput** — macOS requires explicit permission for apps to monitor and inject keyboard input.
   - Go to **System Settings → Privacy & Security → Accessibility**.
   - Click the **+** button and add your Terminal app (e.g. Terminal, iTerm2, or VS Code) to the allowed list.
   - Without this, the hotkey listener and text injection will not function.

#### Setup
1. Clone or download this repository.
2. Open Terminal in the repository folder.
3. Install all required Python packages:
   ```bash
   pip3 install customtkinter faster-whisper sounddevice pynput pyperclip \
                numpy Pillow pyttsx3 edge-tts pygame eel
   ```
   > **Note:** If `pip3` is not found, try `pip` or `python3 -m pip install ...`.

   The first launch will download the selected Whisper model (~150 MB).

#### Running
Launch the app from Terminal:
```bash
python3 main.py
```
A Web UI Control Center opens. Your floating transcription indicator is now active.

**Hold `Right Option (⌥)`** and speak. Release the key to transcribe and inject text into the active application.

> **Tip:** If text injection does not work in a specific app, ensure that app (not just Terminal) also has Accessibility permission granted in System Settings → Privacy & Security → Accessibility.

---

## Usage Notes

| Feature | Windows | macOS |
|---|---|---|
| Default hotkey | `Right Alt` | `Right Option (⌥)` |
| Text injection method | Win32 `keybd_event` (Ctrl+V) | pynput `Cmd+V` |
| Quick launch | `run.bat` | `python3 main.py` |
| Installer script | `install.bat` | Manual `pip3 install` |
| Accessibility permission needed | No | **Yes** — see setup above |

The Web UI lets you change the Whisper model, configure your Gemini API key, set custom voice macros, and view live transcription logs.
