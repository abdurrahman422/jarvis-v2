# Runtime Validation Report

Phase 11 runtime validation for the Jarvis command routing and action execution path.

Date: 2026-05-01

## Scope

Commands were executed through the real `AssistantController.process()` runtime path with `speak=False`.

Flow exercised:

```text
AssistantController.process()
-> CommandRouter.route()
-> RouteHandler.handle()
-> app/actions/*
-> existing executors/services
-> response dict returned to UI
```

This was not a microphone/STT test. The recognized text below is the command text injected into the controller.

## Runtime Notes

- The project `.venv` interpreter is not usable in this environment, so validation used the bundled Codex Python runtime.
- The bundled runtime is missing optional/live-action dependencies:
  - `pythoncom`
  - `pyautogui`
  - `requests`
  - `pyttsx3`
- Lightweight stubs were used only for startup-only optional imports such as `psutil` and `speech_recognition`, matching the existing routing test approach.
- Real Windows actions were still attempted by the existing executors. Actions that required missing packages returned executor errors instead of crashing.

## Bug Found And Fixed

Bug:
- `ভলিউম কম` and `ভলিউম বাড়` were eventually handled by legacy fallback, but `CommandRouter.route()` returned `None`.

Fix:
- Added short Bengali correction variants in `app/core/command_router.py`:
  - `কম` -> `decrease`
  - `বাড়` -> `increase`
  - `বাড়` -> `increase`

Result:
- Both commands now route as `system_action` before alias/web/fallback logic.

## Command Results

| Command | Recognized text | Normalized text | Route kind | Route source | Action executed | Target | Response returned | Real action worked? |
|---|---|---|---|---|---|---|---|---|
| ভলিউম কম | ভলিউম কম | ভলিউম কম | system_action | dataset_matcher | set_volume | volume_down | স্যার, pycaw/comtypes install করা নেই। | No. Missing `pythoncom`; pyautogui key fallback also unavailable. |
| ভলিউম বাড় | ভলিউম বাড় | ভলিউম বাড় | system_action | dataset_matcher | set_volume | volume_up | স্যার, pycaw/comtypes install করা নেই। | No. Missing `pythoncom`; pyautogui key fallback also unavailable. |
| মিউট | মিউট | মিউট | system_action | hard_rules | set_volume | mute | স্যার, pycaw/comtypes install করা নেই। | No. Missing `pythoncom`; pyautogui key fallback also unavailable. |
| আনমিউট | আনমিউট | আনমিউট | system_action | hard_rules | set_volume | unmute | স্যার, pycaw/comtypes install করা নেই। | No. Missing `pythoncom`. |
| ইউটিউব ওপেন | ইউটিউব ওপেন | youtube | alias_action | alias_matcher | open_url | https://youtube.com | ঠিক আছে স্যার, youtube খুলছি। | Yes. Alias executor reported success. |
| গুগলে সার্চ করো | গুগলে সার্চ করো | google search | web_action | web_actions | web.search |  | স্যার, ওয়েব সার্চ চালাতে প্রয়োজনীয় প্যাকেজ পাওয়া যায়নি। | No. Missing `requests`. |
| স্ক্রিনশট | স্ক্রিনশট | স্ক্রিনশট | system_action | hard_rules | window_control | screenshot | স্যার, screenshot নিতে pyautogui লাগবে। | No. Missing `pyautogui`; no screenshot path was created. |
| ডাউনলোড ফোল্ডার ওপেন | ডাউনলোড ফোল্ডার ওপেন | ডাউনলোড ফোল্ডার | system_action | hard_rules | open_folder | Downloads folder | ঠিক আছে স্যার, Downloads folder খুলছি। | Yes. Opened `C:\Users\Abdur Rahman\Downloads`. |
| আবহাওয়া | আবহাওয়া | আবহাওয়া | web_action | web_actions | web.search |  | স্যার, ইন্টারনেট কানেকশন সমস্যা হচ্ছে, তাই আবহাওয়ার তথ্য আনতে পারিনি। | No. Missing `requests`, so weather lookup could not run. |

## Detailed Observations

### Volume Commands

Routing is correct after the small correction-map fix:

```text
ভলিউম কম  -> system_action -> set_volume -> volume_down
ভলিউম বাড় -> system_action -> set_volume -> volume_up
মিউট      -> system_action -> set_volume -> mute
আনমিউট    -> system_action -> set_volume -> unmute
```

Execution did not change system volume in this runtime because `pythoncom` is not installed. The safe key fallback also could not run because `pyautogui` is not installed.

### Alias Command

`ইউটিউব ওপেন` routed correctly:

```text
alias_action -> open_url -> https://youtube.com
```

The alias executor returned success.

### Web And Weather

`গুগলে সার্চ করো` and `আবহাওয়া` routed correctly to `web_action`.

Execution failed because `requests` is missing in the validation interpreter. The app returned clear Bengali error responses instead of crashing.

### Screenshot

`স্ক্রিনশট` routed correctly:

```text
system_action -> window_control -> screenshot
```

Execution failed because `pyautogui` is missing. No screenshot file was created.

### Downloads Folder

`ডাউনলোড ফোল্ডার ওপেন` routed correctly:

```text
system_action -> open_folder -> Downloads folder
```

The executor returned success and resolved:

```text
C:\Users\Abdur Rahman\Downloads
```

## Validation Commands Run

Syntax/routing validation:

```text
python -m py_compile app/core/command_router.py
python scripts/test_command_routing.py
```

Runtime validation:

```text
AssistantController.process(command, speak=False, mode="chat")
```

## Summary

Routing status:
- Passed for all requested commands.
- No command fell to the generic hearing fallback in the final validation pass.

Runtime side-effect status:
- Worked: YouTube open, Downloads folder open.
- Blocked by missing environment dependencies: volume, mute, unmute, screenshot, Google search, weather.

Code changed:
- Only `app/core/command_router.py` was updated to fix the short Bengali volume variants.

No refactor, file deletion, TTS/STT change, or response-format change was made.
