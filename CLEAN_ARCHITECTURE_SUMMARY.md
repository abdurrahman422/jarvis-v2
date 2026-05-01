# Jarvis Clean Architecture Summary

This document summarizes the safer modular architecture introduced during Phases 1-10.

No legacy files were deleted. The refactor was intentionally done with wrappers, adapters, and compatibility methods so the UI and existing commands can continue working.

## Phase Status

```text
Phase 1  - intent wrapper modules and initial CommandRouter: complete
Phase 2  - structured route decisions moved into CommandRouter: complete
Phase 3  - public app/actions wrapper layer created: complete
Phase 4  - RouteHandler extracted from AssistantController: complete
Phase 5  - duplication audit and cleanup plan: complete
Phase 6  - ResponseBuilder extracted: complete
Phase 7  - system action consolidation with compatibility wrappers: complete
Phase 8  - file action facade consolidation: complete
Phase 9  - web/weather action facade and router cleanup: complete
Phase 10 - architecture documentation and verification: complete
```

## Final Command Flow

```text
User input
-> AssistantController.process()
-> CommandRouter.route()
   -> normalize text
   -> voice text correction
   -> pending confirmation check
   -> volume clarification
   -> hard system rules
   -> dataset system match
   -> alias app/site match
   -> web/weather match
   -> None if no deterministic route
-> RouteHandler.handle()
   -> app/actions/*
   -> ResponseBuilder
-> fallback to old _process_impl() when route is None
-> optional AI/brain fallback
-> history/logging/TTS through controller context
-> existing response dict returned to UI
```

The important rule is still preserved:

```text
hard system actions -> dataset system actions -> alias app/site actions -> web/weather -> fallback
```

This prevents commands like volume, screenshot, folders, Bluetooth, and mute from being accidentally captured by fuzzy app or website aliases.

## New Modules Added

### app/core/command_router.py

Role:
- Owns route decision order.
- Does not execute actions.
- Does not build UI response dicts.
- Returns a structured `CommandRoute` object so later layers know exactly what was matched and why.

It decides these route kinds:

```text
pending_confirmation
volume_clarification
system_action
alias_action
web_action
None fallback
```

This keeps the old critical ordering safe:

```text
system actions before alias matching before AI fallback
```

Current route fields include:

```text
kind
original_text
normalized_text
corrected_text
source
system_record
alias_match
pending confirmation metadata
```

### app/core/route_handler.py

Role:
- Executes a route selected by `CommandRouter`.
- Calls the public action layer in `app/actions`.
- Uses `ResponseBuilder` for route response dictionaries.
- Still receives the controller as context so repository logging, settings, and TTS behavior remain unchanged.

This is a bridge layer. It should become more independent after persistence/TTS concerns are separated.

### app/core/response_builder.py

Role:
- Builds response dictionaries in the same shape the UI already expects.
- Centralizes response construction for:
  - system action responses
  - alias action responses
  - alias confirmation responses
  - volume clarification responses
  - direct action responses
  - fallback responses

Compatibility methods still exist in `AssistantController`, but now delegate here where safe.

Response dict keys were intentionally preserved. UI code should continue reading the same fields such as:

```text
intent
action
response
speak_text
reply_lang
recognized_text
handled
success
confidence
```

### app/intents/

Role:
- Thin intent matching adapters.
- Wrap existing matchers without deleting old logic.

Files:

```text
app/intents/hard_rules.py
app/intents/dataset_matcher.py
app/intents/alias_matcher.py
```

Responsibilities:
- `hard_rules.py`: wraps hard system action matching.
- `dataset_matcher.py`: wraps dataset system action matching.
- `alias_matcher.py`: wraps alias app/site matching.

These modules are intentionally thin. Their job is to make the command flow readable without moving all legacy matcher logic at once.

### app/actions/

Role:
- Clean public action execution layer.
- Wraps old services while preserving behavior.

Files:

```text
app/actions/system_actions.py
app/actions/alias_actions.py
app/actions/file_actions.py
app/actions/web_actions.py
```

Responsibilities:
- `system_actions.py`: public system action wrapper around `system_action_executor.py`.
- `alias_actions.py`: public alias action wrapper around `app/core/action_executor.py`.
- `file_actions.py`: public file/desktop action facade around `file_automation.py` and `windows_desktop.py`.
- `web_actions.py`: public web/weather facade around `web_search_service.py`.

The action layer is now the preferred import target for route execution. Older services remain as implementation backends or compatibility modules.

## AssistantController Role Now

`AssistantController` is still large, but it is thinner than before.

It now mainly:
- receives UI/voice input
- calls `CommandRouter.route()`
- calls `RouteHandler.handle()`
- falls back to old `_process_impl()` if no deterministic route exists
- keeps public UI methods stable
- manages repositories, settings, TTS, STT, scheduler methods, and compatibility helpers

Important public methods were preserved:

```text
process()
listen_once_and_process()
preview_tts()
test_bangla_tts()
apply_speech_preferences()
scheduler/settings methods
```

## Legacy Files Still Kept

These files are intentionally still present:

```text
app/services/system/system_control.py
app/services/automation/system_tools.py
app/services/system/file_automation.py
app/services/automation/windows_desktop.py
app/core/response_engine.py
```

Why they remain:
- They still have active imports or fallback behavior.
- Some ActionRegistry routes still depend on them.
- Some file/desktop ambiguity behavior is not fully covered by tests yet.
- Deleting them now would be risky.

Compatibility status:
- `system_control.py`: legacy system wrapper; delegates safe confirmed/system behavior toward the canonical executor.
- `system_tools.py`: legacy ActionRegistry helper module; some functions now delegate safely, but registry callers still exist.
- `file_automation.py`: focused file automation backend used by `app/actions/file_actions.py`.
- `windows_desktop.py`: broad desktop/file resolver backend used by `app/actions/file_actions.py`.
- `response_engine.py`: older response phrasing helper; keep until imports are fully removed.

## Files That Should NOT Be Deleted Yet

Do not delete yet:

```text
app/services/system/system_control.py
app/services/automation/system_tools.py
app/services/system/file_automation.py
app/services/automation/windows_desktop.py
app/core/response_engine.py
app/core/system_action_dataset_loader.py
app/core/action_executor.py
app/core/alias_command_matcher.py
app/core/alias_dataset_loader.py
```

Also do not delete datasets/models/runtime state unless intentionally cleaning artifacts:

```text
assets/system_action_dataset_500.jsonl
assets/system_action_dataset.txt
app/generated/bd_full_alias_dataset.json
data/jarvis.db
app/models/*
```

These files may look old, but they still represent either active fallback paths, dataset loaders, execution backends, or persistent state.

## Current Safe Architecture

```text
app/
  core/
    assistant_controller.py
    command_router.py
    route_handler.py
    response_builder.py
    command_normalizer.py

  intents/
    hard_rules.py
    dataset_matcher.py
    alias_matcher.py

  actions/
    system_actions.py
    alias_actions.py
    file_actions.py
    web_actions.py

  services/
    system/
    speech/
    ai/
    automation/
    web/
    vision/
```

## Remaining Cleanup Work

Recommended future phases:

1. Move remaining direct command helpers from `AssistantController._try_direct_command()` into a dedicated direct-route/action layer.
2. Move more response side effects from `ResponseBuilder` context calls into explicit services.
3. Replace `system_tools.py` ActionRegistry functions with wrappers around `app/actions`.
4. Finish migrating old `system_control.py` fallback calls into `system_action_executor.py`.
5. Add tests for:
   - confirmed shutdown/restart/sleep
   - screenshot
   - Bluetooth settings
   - Downloads/Desktop folder commands
   - web/weather route responses
   - alias confirmation behavior
6. After tests pass, turn legacy files into thin wrappers or remove them in a separate cleanup phase.

## Verification Scope

Phase 10 verification checks:

```text
python -m py_compile app/core/assistant_controller.py app/core/command_router.py app/core/route_handler.py app/core/response_builder.py app/actions/system_actions.py app/actions/alias_actions.py app/actions/file_actions.py app/actions/web_actions.py
python scripts/test_command_routing.py
```

These checks verify imports, syntax, and the existing routing regression suite. They do not exercise live Windows side effects such as opening Notepad, changing volume, or taking screenshots.
