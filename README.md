# NethyTech-Inspired Jarvis (43-Day Fidelity Build)

This project recreates the NethyTech 43-day Jarvis progression as closely as possible using:

- Python
- PySide6
- SQLite
- Local-first modules
- Windows-friendly behavior

## What this app is

A local-first desktop Jarvis-style assistant with:
- A dark “Jarvis dashboard” UI (tabs for Home/Voice/Automation/Brain/Vision/Scheduler/Settings)
- Voice input (SpeechRecognition) with a clean provider/fallback structure for future offline STT
- TTS:
  - English: pyttsx3 / Microsoft SAPI5 on Windows
  - Bengali: free online Google gTTS, generated from the exact reply text
- Local persistence (SQLite) for logs, alarms, tasks, settings
- Optional modules (OCR/camera/WhatsApp/speedtest) that degrade gracefully if not installed/configured

## Day-to-Module Fidelity Matrix

### Days 1-8: Core Jarvis foundation
- Core loop: `app/core/assistant_controller.py`
- STT/TTS basics: `app/services/speech/stt_service.py`, `app/services/speech/tts_service.py`
- Desktop shell UI: `app/ui/main_window.py`, `app/ui/pages/home_page.py`, `app/ui/pages/voice_page.py`
- Base commands: `app/services/automation/system_tools.py`

### Days 9-13: Voice quality and feedback
- Voice profile tuning and test speaking: `app/ui/pages/voice_page.py`, `app/services/speech/tts_service.py`
- Feedback/history: `app/data/repositories/conversation_repository.py`, `app/data/repositories/command_repository.py`

### Days 14-21: Automation and Jarvis brain expansion
- Intent routing/action dispatch: `app/core/intent_router.py`, `app/core/action_registry.py`
- Music and battery tools: `app/services/automation/music_tools.py`, `app/services/automation/system_tools.py`
- Faster command path + confidence metadata: `app/core/response_engine.py`

### Days 22-30: Tools, time management, alarms, speed
- Time management + alarms: `app/ui/pages/scheduler_page.py`, `app/data/repositories/alarm_repository.py`
- Internet speed checks: `app/services/automation/network_tools.py`
- Tooling expansion: `app/ui/pages/automation_page.py`

### Days 31-40: Stabilization, vision, weather, WhatsApp, hardware
- Vision OCR/camera input: `app/services/vision/ocr_service.py`, `app/services/vision/camera_service.py`, `app/ui/pages/vision_page.py`
- Weather + WhatsApp automation: `app/services/automation/weather_tools.py`, `app/services/automation/whatsapp_tools.py`
- Hardware automation hooks: `app/services/hardware/hardware_service.py`

### Days 41-43: Advanced brain, source finalization, EXE build
- ML-assisted routing add-on: `app/core/advanced_brain.py`
- Full source integration and startup wiring: `app/main.py`
- `.py` -> `.exe` flow: `scripts/build_exe.ps1`

## Known Inferences (Not Fully Verifiable From Titles Alone)
- UI exact visuals are approximated into a dark Jarvis-style dashboard.
- Specific third-party APIs/services are implemented with local-first safe defaults.
- Deepfake-specific implementation is not included by default; voice profile control is included.

## Run

### 1) Windows prerequisites

- **Python**: Install Python 3.11+ from the official site and ensure **“Add python.exe to PATH”** is checked.
  - Verify:
    - `python --version`
    - `pip --version`
- **PowerShell** (recommended): you’re already on Windows, so use PowerShell for the commands below.

### 2) Create a venv and install dependencies

From the project root:

- Create venv:
  - `python -m venv .venv`
- Activate:
  - `.venv\Scripts\Activate.ps1`
- Upgrade pip:
  - `python -m pip install --upgrade pip`
- Install **core** requirements (app runs with these):
  - `pip install -r requirements.txt`
- Install **optional** features (recommended for full Jarvis parity):
  - `pip install -r requirements-optional.txt`

### 3) Start the app

- `python -m app.main`

### Clean old offline TTS packages

Jarvis no longer uses the old heavy offline Bengali voice stack. If those packages were installed while debugging voice output, remove them before reinstalling the current requirements:

- `python -m pip uninstall -y TTS torch torchaudio transformers tokenizers soundfile librosa spacy pandas matplotlib scipy numba llvmlite gruut trainer encodec`
- `python -m pip install -r requirements.txt`

## Voice output

### English TTS

English replies use the existing Windows voice path:
- `pyttsx3`
- Microsoft SAPI5 voices

Example:
- Chat reply: `I am opening YouTube sir.`
- Voice reply: `I am opening YouTube sir.`

### Bengali TTS

Bengali replies use free online Google gTTS:
- The actual Jarvis reply text is sent to gTTS with `lang="bn"`.
- The generated audio is saved to:
  - `app/runtime/audio/bangla_reply_latest.mp3`
- Jarvis plays that generated MP3 immediately.
- `assets/voices/bangla_voice.wav` is not played as a static reply.

Example:
- User: `ইউটিউব খোলো`
- Chat reply: `ঠিক আছে স্যার, ইউটিউব খুলছি।`
- Voice reply: `ঠিক আছে স্যার, ইউটিউব খুলছি।`

Quick Bengali TTS test:
- `python -c "from app.services.speech.tts_service import debug_bangla_gtts; debug_bangla_gtts()"`

## Feature setup (Windows)

### Microphone / STT (SpeechRecognition)

- **Provider**: currently uses **online Google STT** via `SpeechRecognition`.
- **Future offline hook**: an `offline_placeholder` provider exists for later local STT integration.
- If STT fails, Jarvis will show why (microphone unavailable / not understood / request failed) and the provider status.

**Optional dependency for microphone input**:
- `PyAudio` can be the hardest install on Windows. If `pip install PyAudio` fails:
  - Update pip and try again
  - Consider installing a compatible wheel for your Python version
  - The app remains usable via typed commands even without microphone capture

### OCR / Tesseract (Vision)

OCR needs **two things**:
1) Python packages (optional file):
- `pip install -r requirements-optional.txt`

2) **Tesseract-OCR binary** installed on Windows:
- Install to the default path if possible:
  - `C:\Program Files\Tesseract-OCR\tesseract.exe`
- Ensure it’s on PATH, or the app will auto-detect common install paths.

If OCR says **“Tesseract binary not found”**, install Tesseract and retry.

### Camera (OpenCV)

- Install optional dependencies:
  - `pip install -r requirements-optional.txt`
- If OpenCV isn’t installed, Vision capture will show a clear message instead of crashing.

### WhatsApp automation

- Install optional dependencies:
  - `pip install -r requirements-optional.txt`
- WhatsApp automation relies on **WhatsApp Web** in your browser being logged in.

Command format:
- `whatsapp send +911234567890 | Hello from Jarvis`

If it fails after retries, Jarvis outputs a **manual WhatsApp Web URL** you can open to send the message yourself.

### Internet speed tool

- Install optional dependencies:
  - `pip install -r requirements-optional.txt`
- Run command:
  - `internet speed`

## Smoke tests (quick reliability check)

From the project root (venv active):

- `python -m unittest -q`

## Build a Windows EXE (PyInstaller)

From the project root (venv active):

- `.\scripts\build_exe.ps1 -Clean`

Output:
- `dist\Jarvis43Day\Jarvis43Day.exe`

Important packaging notes:
- **Tesseract is not bundled by default** (OCR needs it installed on the target machine).
- WhatsApp automation depends on a browser + WhatsApp Web login state.
- Microphone input depends on PyAudio availability (typed commands still work without it).

## Troubleshooting

### “Python was not found…”
- Install Python from the official installer and enable **Add to PATH**.
- Restart your terminal after installing.

### PyAudio install fails
- You can still use Jarvis with typed commands.
- Try:
  - `python -m pip install --upgrade pip`
  - Install a wheel matching your Python version/architecture

### STT says “request failed”
- This is the online recognizer path failing (network or API).
- Typed commands remain available; later offline STT can be added via the provider hook.

### OCR says “Tesseract binary not found”
- Install Tesseract-OCR and make sure `tesseract.exe` is discoverable.
- Default expected install location:
  - `C:\Program Files\Tesseract-OCR\tesseract.exe`

### WhatsApp automation doesn’t send
- Confirm WhatsApp Web is logged in.
- If automation fails, use the fallback URL that Jarvis prints.

### Camera capture fails
- Ensure the camera isn’t in use by another app.
- Install OpenCV:
  - `pip install opencv-python`
