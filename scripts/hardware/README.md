# Hardware Hook Scripts

Place your local hardware automation scripts in this folder.

Supported script types:
- `.ps1`
- `.bat`
- `.cmd`

Usage from Jarvis commands:
- `hardware list`
- `hardware run <script_name.ps1>`

Examples:
- `hardware run example_hardware_hook.ps1`
- `hardware run fan_on.ps1`

Notes:
- Keep scripts Windows-friendly and local-first.
- Test scripts manually in PowerShell before invoking through Jarvis.
- Avoid storing secrets directly in script files.
