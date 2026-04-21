import eel
import tkinter as tk
import threading
import sys
import os
import dictation

# Initialize Web Folder
eel.init('web')

# Build the Tkinter instance that manages hotkeys & backend
app = dictation.DictationApp()
app.root.withdraw()   # Hide the legacy tkinter window — web UI is the real interface

# ── Pipe live amplitude data to the JS equalizer ──────────────────────────────
old_anim = app._animate_pill

def web_animate_pill():
    try:
        eel.update_equalizer(app.pill_bh)()
    except Exception:
        pass
    old_anim()

app._animate_pill = web_animate_pill


# ── Exposed functions callable from JavaScript ────────────────────────────────
@eel.expose
def get_state():
    """Return full live app state to the web UI."""
    try:
        cfg = app._config
        return {
            "is_recording":    app.recording,
            "is_transcribing": app.transcribing,
            "stats":           app.stats,
            "log":             app.log[-50:],
            "config": {
                "whisper_model":       app.current_model,
                "gemini_api_key_set":  bool(cfg.get("gemini_api_key", "")),
                "ai_wake_word":        cfg.get("ai_wake_word", "assistant"),
                "write_prompt_phrase": cfg.get("write_prompt_phrase", "write a prompt"),
                "edge_voice":          cfg.get("edge_voice", "en-US-AriaNeural"),
                "auto_punctuate":      cfg.get("auto_punctuate", False),
                "voice_macros":        cfg.get("voice_macros", {}),
                "gemini_model":        cfg.get("gemini_model", "gemini-2.0-flash"),
                "selected_mic":        cfg.get("mic_name", ""),
            }
        }
    except Exception as exc:
        return {"error": str(exc)}


@eel.expose
def get_mics():
    """Return list of available microphone names."""
    try:
        return app._query_mics()
    except Exception as exc:
        return ["Default Microphone"]


@eel.expose
def set_mic(name):
    """Set the active microphone by name."""
    try:
        # Update the StringVar used by the recording thread
        app._mic_var.set(name)
        # Persist to config
        app._config["mic_name"] = name
        app._save_config()
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@eel.expose
def update_setting(key, value):
    """Update a config value from the web UI."""
    try:
        if key == "whisper_model":
            app._config["whisper_model"] = value.lower()
            app.current_model = value.lower()
            app._save_config()
        elif key == "gemini_api_key":
            app._config["gemini_api_key"] = value.strip()
            app._save_config()
        elif key == "ai_wake_word":
            app._config["ai_wake_word"] = value.strip().lower() or "assistant"
            app._save_config()
        elif key == "write_prompt_phrase":
            app._config["write_prompt_phrase"] = value.strip().lower() or "write a prompt"
            app._save_config()
        elif key == "auto_punctuate":
            app._config["auto_punctuate"] = bool(value)
            app._save_config()
        elif key == "gemini_model":
            app._config["gemini_model"] = value
            app._save_config()
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@eel.expose
def add_voice_macro(trigger, expansion):
    """Add a voice macro from the web UI."""
    try:
        if not trigger.strip() or not expansion.strip():
            return {"ok": False, "error": "Both fields required"}
        app._config.setdefault("voice_macros", {})[trigger.strip().lower()] = expansion.strip()
        app._save_config()
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@eel.expose
def delete_voice_macro(trigger):
    """Remove a voice macro from the web UI."""
    try:
        app._config.get("voice_macros", {}).pop(trigger, None)
        app._save_config()
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


print("====================================")
print(" SOVEREIGN AI WEB ENGINE ACTIVE")
print("====================================")

# ── Start Eel in a daemon thread so tkinter can own the main thread ───────────
# This fixes "RuntimeError: main thread is not in main loop" — tkinter's
# root.after() requires mainloop() to be running on the actual main thread.
def _run_eel():
    try:
        eel.start('index.html', size=(1200, 800), port=0, block=True)
    except (SystemExit, KeyboardInterrupt):
        pass

eel_thread = threading.Thread(target=_run_eel, daemon=True)
eel_thread.start()

# Run tkinter's proper mainloop on the main thread
app.root.mainloop()
