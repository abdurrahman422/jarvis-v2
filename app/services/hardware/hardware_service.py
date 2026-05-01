import subprocess
from pathlib import Path

from app.app_paths import SCRIPTS_DIR

HARDWARE_SCRIPTS_DIR = SCRIPTS_DIR / "hardware"


def list_hardware_scripts() -> list[str]:
    HARDWARE_SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for file in HARDWARE_SCRIPTS_DIR.iterdir():
        if file.is_file() and file.suffix.lower() in {".ps1", ".bat", ".cmd"}:
            out.append(file.name)
    return sorted(out)


def execute_hardware_stub(text: str) -> str:
    """
    Command format:
    hardware run <script_name.ps1>
    Scripts are resolved from scripts/hardware/
    """
    original = text.strip()
    cmd = original.lower()
    if cmd == "hardware list":
        scripts = list_hardware_scripts()
        if not scripts:
            return "No hardware scripts found in scripts/hardware."
        return "Available hardware scripts: " + ", ".join(scripts)
    if "hardware run" not in cmd:
        return "Hardware hook ready. Use: hardware run <script_name.ps1> or hardware list"
    lower_index = cmd.find("hardware run")
    script_name = original[lower_index + len("hardware run") :].strip()
    if not script_name:
        return "Provide a script name. Example: hardware run fan_on.ps1"
    script_path = HARDWARE_SCRIPTS_DIR / script_name
    if script_path.suffix.lower() not in {".ps1", ".bat", ".cmd"}:
        return "Unsupported script type. Allowed: .ps1, .bat, .cmd"
    if not script_path.exists():
        available = list_hardware_scripts()
        extra = f" Available: {', '.join(available)}" if available else ""
        return f"Hardware script not found: {script_path}.{extra}"
    try:
        if script_path.suffix.lower() == ".ps1":
            cmdline = ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script_path)]
        else:
            cmdline = [str(script_path)]
        subprocess.Popen(cmdline, creationflags=0)
        return f"Hardware script started: {script_name}"
    except OSError as exc:
        return f"Hardware hook failed: {exc}"
