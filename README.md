# Sovereign AI Mic

A completely local, ultra-fast dictation engine featuring a modern web UI, Apple-like frosted glass floating indicators, native Windows text integration, and Google Gemini macro support.

## Overview
Sovereign AI Mic lets you transcribe your voice into any application instantly. By holding a hotkey (like `Right Alt`), your speech is recorded, aggressively transcribed locally using Whisper AI, and seamlessly inserted into your active window natively—bypassing the Windows clipboard altogether.

It bridges the gap between premium local speech-to-text dictation and modern, premium UI/UX design. The application features a decoupled Python backend paired with an Eel/HTML frontend wrapped in a stunning dark-mode interface.

## Key Features
- **Local Whisper AI Transcription:** Choose from Tiny, Base, or Small models. Everything runs offline for dictation.
- **Flawless Native Injection:** Bypasses clipboard buffering by natively streaming keyboard keystrokes to ensure 100% reliable insertion into every application (even slow browsers, Discord, or IDEs).
- **Stunning In-Game UI:** Displays an Apple "Frosted Glass" pill indicator with active volumetric equalizers anywhere on your screen.
- **Gemini Assistant Integration:** 
  - Say `"Assistant, [question]"` to drop a window on-screen and get AI responses.
  - Say `"Write a prompt, [idea]"` to format complex prompts automatically.
  - Custom Voice Macros to expand short phrases into entire blocks of text (like dropping your email or phone number).
- **Zero Privacy Loss:** `config.json`, `log.json`, and `stats.json` are stored locally and ignored by source control.

## Installation

### Prerequisites
- Python 3.10+
- FFMpeg available in system Path (needed for audio transcription)

### Setup
1. Clone the repository
2. Install Python dependencies:
   ```bash
   pip install faster-whisper sounddevice numpy pynput eel customtkinter pillow pyperclip
   ```
   *Note: If you plan on using TTS (Text-to-Speech) modules, you may also need `pyttsx3` and `edge-tts`.*
3. Run `install.bat` which can automatically install missing dependencies (depending on configuration).

## Usage
Simply launch the engine using:
```bash
run.bat
```

This will launch a beautiful Web UI Control Center in a Chromium shell. Your floating transcription tool is now active!
Just **Hold `Right Alt`** (or your mapped hotkey) and speak. Your voice is transcribed and instantly injected into any active window when you release. 

### Local config (`config.json`)
- Location: project root (for example, `<project-root>/config.json`, next to `dictation.py`).
- The app auto-creates this file on first run and updates it when you save settings in the UI.
- The file is intentionally gitignored, so your Gemini API key and personal macros stay local.

Example structure:
```json
{
  "hotkey_str": "Key.alt_r",
  "hotkey_display": "Right Alt",
  "gemini_api_key": "YOUR_GEMINI_API_KEY",
  "gemini_model": "gemini-2.0-flash",
  "ai_wake_word": "assistant",
  "write_prompt_phrase": "write a prompt",
  "ai_system_prompt": "You are a helpful voice assistant...",
  "voice_macros": {
    "my email": "name@example.com",
    "my phone": "555-0100"
  }
}
```

Notes:
- Get your Gemini key from [aistudio.google.com](https://aistudio.google.com), then save it in the app's AI page (or set `gemini_api_key` manually).
- Add any personal/internal info you want to keep private in `voice_macros` (or related settings) inside `config.json`.
