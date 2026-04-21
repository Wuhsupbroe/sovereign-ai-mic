@echo off
title Dictation App - First-Time Setup
color 0A

echo ============================================================
echo   Dictation App  —  First-Time Setup
echo ============================================================
echo.
echo  Requires Python 3.9+ (https://www.python.org)
echo.
echo  Installing:
echo    customtkinter   modern Apple-style UI
echo    faster-whisper  local AI speech recognition
echo    sounddevice     microphone input
echo    pynput          global keyboard shortcut
echo    pyperclip       clipboard support
echo    numpy           audio processing
echo    pyttsx3         offline TTS fallback
echo    edge-tts        Microsoft Neural voices (online, free)
echo    pygame          audio playback for neural voices
echo.
echo  The Whisper model (~150 MB) downloads on first launch.
echo.
pause

echo.
echo [1/10] Upgrading pip...
python -m pip install --upgrade pip --quiet

echo.
echo [2/10] Installing customtkinter...
pip install customtkinter --quiet

echo.
echo [3/10] Installing faster-whisper...
pip install faster-whisper --quiet

echo.
echo [4/10] Installing sounddevice...
pip install sounddevice --quiet

echo.
echo [5/10] Installing pynput...
pip install pynput --quiet

echo.
echo [6/10] Installing pyperclip + numpy...
pip install pyperclip numpy --quiet

echo.
echo [7/10] Installing Pillow (image support)...
pip install Pillow --quiet

echo.
echo [8/10] Installing pyttsx3 (offline TTS fallback)...
pip install pyttsx3 --quiet

echo.
echo [9/10] Installing edge-tts (Microsoft Neural voices)...
pip install edge-tts --quiet

echo.
echo [10/10] Installing pygame (audio playback)...
pip install pygame --quiet

echo.
echo ============================================================
echo   Done! Run  run.bat  to start the app.
echo   Neural voices require an internet connection.
echo ============================================================
echo.
pause
