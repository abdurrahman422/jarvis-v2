# Jarvis Architecture Cleanup Plan

Generated for Phase 5: duplication audit and safe migration planning.

No files should be deleted in this phase. The goal is to identify what is duplicated, which code is still used, and how to migrate safely.

## Phase 10 Status Update

Phases 1-9 are now complete:

```text
Phase 1 - intent wrappers and initial CommandRouter: complete
Phase 2 - clean structured routing decisions: complete
Phase 3 - app/actions wrapper layer: complete
Phase 4 - RouteHandler extraction: complete
Phase 5 - duplication audit and cleanup plan: complete
Phase 6 - ResponseBuilder extraction: complete
Phase 7 - safe system action consolidation: complete
Phase 8 - safe file action consolidation: complete
Phase 9 - web action consolidation and final router cleanup: complete
```

Phase 10 adds documentation and verification only. No files are deleted and no runtime behavior is changed.

## Current Direction

The project is moving toward this architecture:

```text
app/
  core/
    assistant_controller.py   # public UI-facing coordinator
    command_router.py         # route decision only
    route_handler.py          # route execution bridge
    command_normalizer.py
    response_builder.py       # future target

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
    speech/
    ai/
    system/
```

The intended command flow remains:

```text
User input
-> normalize
-> voice correction
-> pending confirmation
-> volume clarification
-> hard rules
-> dataset match
-> alias match
-> action execution
-> fallback AI / old local flow
```

The current implementation path is:

```text
AssistantController.process()
-> CommandRouter.route()
-> RouteHandler.handle()
-> app/actions/*
-> ResponseBuilder
-> old _process_impl() fallback only when no route is selected
```

## Duplication Summary

Main duplicate areas:

- System actions are split across `system_action_executor.py`, `system_control.py`, and `system_tools.py`.
- File/folder/desktop behavior is split across `file_automation.py` and `windows_desktop.py`.
- Response formatting is split across `response_engine.py`, `AssistantController`, and `RouteHandler` calling controller response builders.
- `RouteHandler` is not duplicate by itself, but it still relies on controller private response methods as a compatibility bridge.

## File Audit

### app/services/system/system_action_executor.py

Current purpose:
- Canonical executor for dataset-backed system actions.
- Executes system records from `system_action_dataset_loader`.
- Handles open folders/apps/settings, volume, brightness, screenshot, media keys, power confirmation, time/date, and system info.

Who imports/calls it:
- `app/actions/system_actions.py`
- `app/core/command_router.py` imports `is_confirm_command`
- `app/core/assistant_controller.py` still imports `execute_confirmed_dataset_action`, `execute_dataset_action`, and `is_confirm_command` for legacy fallback methods.
- `scripts/test_command_routing.py` imports `SystemActionExecutionResult`.

Functions still used:
- `execute_dataset_action`
- `execute_system_action`
- `execute_confirmed_dataset_action`
- `is_confirm_command`
- `SystemActionExecutionResult`
- Internal executors such as `_execute_set_volume`, `_execute_get_system_info`, `_screenshot`, `_open_settings`.

Duplicate functions:
- Volume logic duplicates `system_control.execute_volume_target`.
- Screenshot, brightness, WiFi/settings, hotkey helpers duplicate similar functions in `system_control.py`.
- Some open app/folder behavior overlaps with `system_tools.py`, `file_automation.py`, and `windows_desktop.py`.

Risk level if removed:
- Very high. This is now the main executor for routed system actions.

Safe migration steps:
1. Keep as canonical implementation.
2. Move any still-needed confirmed action logic from `system_control.py` into this file or into `app/actions/system_actions.py`.
3. Update `AssistantController` legacy fallback methods to call `app/actions/system_actions.py`.
4. Add regression tests for volume, mute, screenshot, Bluetooth settings, CPU/RAM/internet status, and power confirmation.

Final recommendation:
- Keep. Treat as canonical system execution service.

### app/services/system/system_control.py

Current purpose:
- Legacy rule-based system matcher/executor.
- Provides confirmed action execution used by `system_action_executor.py`.

Who imports/calls it:
- `app/services/system/system_action_executor.py` imports `execute_confirmed_action`.
- `app/core/assistant_controller.py` imports `execute_system_action` and `match_system_action` for `_try_system_control_command`.

Functions still used:
- `execute_confirmed_action` is definitely used.
- `match_system_action` and `execute_system_action` are used by AssistantController legacy fallback.
- `is_confirm_command` may still be used by old paths.

Duplicate functions:
- `match_system_action` duplicates hard/dataset matching direction now owned by `CommandRouter` and `system_action_dataset_loader`.
- `_volume`, `execute_volume_target`, `_volume_key_fallback` duplicate `system_action_executor.py`.
- `_brightness`, `_screenshot`, `_hotkey`, `_wifi`, `_open_settings` duplicate system executor behavior.

Risk level if removed:
- High. Removing it now can break confirmed power actions and legacy fallback routing.

Safe migration steps:
1. Move or wrap `execute_confirmed_action` in `system_action_executor.py`.
2. Stop calling `_try_system_control_command` from `AssistantController._try_direct_command`.
3. Add tests for old commands that currently reach `_try_system_control_command`.
4. After no imports remain, keep a compatibility wrapper for one release.

Final recommendation:
- Merge useful confirmed-action pieces into `system_action_executor.py`, then deprecate. Do not delete yet.

### app/services/automation/system_tools.py

Current purpose:
- Legacy ActionRegistry functions for local system actions such as time, battery, notepad, Google, YouTube, greeting, system info, and unknown.

Who imports/calls it:
- `app/core/assistant_controller.py` imports many functions and registers them in `_register_actions`.

Functions still used:
- `get_time`
- `get_battery`
- `open_notepad`
- `system_status`
- `system_info`
- `open_google`
- `open_youtube`
- `youtube_search`
- `youtube_play`
- `greet`
- `unknown`
- `open_desktop_item_stub`

Duplicate functions:
- `get_time`, `get_battery`, `system_status`, `system_info` overlap with dataset system info/time actions.
- `open_notepad`, `open_google`, `open_youtube` overlap with alias/app/system action layers.
- `youtube_search` and `youtube_play` overlap with `youtube_multimodal.py` and alias web opening.

Risk level if removed:
- Medium to high. Local intent fallback still uses ActionRegistry mappings.

Safe migration steps:
1. Replace ActionRegistry registrations one by one with action-layer wrappers.
2. Keep function names as compatibility wrappers.
3. Add tests for greeting, time, battery, notepad, YouTube open/search/play.
4. Remove only after `AssistantController._register_actions` no longer imports this module.

Final recommendation:
- Convert into compatibility wrappers around `app/actions/system_actions.py`, `app/actions/app_actions.py`, and `app/actions/web_actions.py`; delete only after tests confirm no callers.

### app/services/system/file_automation.py

Current purpose:
- Focused file/folder automation for known folders, recent downloads, project folder, and filename search.

Who imports/calls it:
- `app/actions/file_actions.py`
- `app/core/assistant_controller.py` imports `handle_file_automation_command` and `is_file_automation_command` for `_try_direct_command`.

Functions still used:
- `is_file_automation_command`
- `handle_file_automation_command`
- `open_folder`
- `open_file`
- `open_recent_file`
- `find_file_by_name`
- `FileActionResult`

Duplicate functions:
- Folder opening overlaps with `windows_desktop.open_folder`.
- File opening overlaps with `windows_desktop.open_file`.
- File search overlaps with `windows_desktop.search_file` and recursive helpers.

Risk level if removed:
- High. Current direct command flow depends on it.

Safe migration steps:
1. Change `AssistantController._try_direct_command` to use `app/actions/file_actions.py`.
2. Decide whether `FileActionResult` should become the common file action result type.
3. Move shared folder aliases/search helpers into `app/actions/file_actions.py` or a new service.
4. Add tests for Downloads/Desktop/Documents, latest download, file search, ambiguous file result.

Final recommendation:
- Keep as focused implementation for now. Eventually merge selected `windows_desktop` capabilities into a single file action service.

### app/services/automation/windows_desktop.py

Current purpose:
- Broad Windows desktop resolver for apps, folders, drives, favorites, search, ambiguous picks, and legacy file commands.

Who imports/calls it:
- `app/actions/file_actions.py`
- `app/core/assistant_controller.py` imports `complete_pick`, `execute_file_control`, `get_latest_file`, `search_file`.
- `app/core/intent_router.py` imports `looks_like_desktop_launch`.

Functions still used:
- `looks_like_desktop_launch`
- `resolve_desktop_command`
- `complete_pick`
- `execute_file_control`
- `search_file`
- `get_latest_file`
- `open_folder`
- `open_file`

Duplicate functions:
- `open_folder`, `open_file`, latest file lookup, recursive search duplicate `file_automation.py`.
- App launch mapping overlaps with `app_launcher.py`.
- Known folder mapping overlaps with `file_automation.py` and `system_action_executor.py`.

Risk level if removed:
- High. IntentRouter and AssistantController still use pieces of it.

Safe migration steps:
1. Route all imports through `app/actions/file_actions.py`.
2. Split app-launch pieces away from file/folder pieces.
3. Preserve `DesktopOutcome` until UI ambiguity behavior has tests.
4. Add tests for desktop launch, ambiguous pick, drive/folder commands, and file control commands.

Final recommendation:
- Keep temporarily. Gradually split into app actions and file actions, then retire legacy broad helpers.

### app/core/response_engine.py

Current purpose:
- Small response phrasing helper for local route results.

Who imports/calls it:
- `app/core/assistant_controller.py` imports `ResponseEngine`.

Functions still used:
- Not fully confirmed from current scan whether `ResponseEngine.render_reply` is actively called. AssistantController imports it, but much response construction is inline.

Duplicate functions:
- Response wording overlaps with `AssistantController._finalize_response`, `_direct_action_response`, `_system_control_response`, `_alias_action_response`, `_apply_persona`, and locale response helpers.

Risk level if removed:
- Medium. Import exists and older code may still call it.

Safe migration steps:
1. Search for direct `ResponseEngine.render_reply` usage before changing.
2. Create `app/core/response_builder.py`.
3. Move response dict construction from AssistantController into ResponseBuilder.
4. Keep ResponseEngine as a thin compatibility wrapper around ResponseBuilder.

Final recommendation:
- Merge into a future `response_builder.py`; keep compatibility wrapper until no direct imports remain.

### app/core/route_handler.py

Current purpose:
- Executes `CommandRoute` decisions by calling action wrappers and the controller's existing response builders.

Who imports/calls it:
- `app/core/assistant_controller.py`
- `scripts/test_command_routing.py` monkeypatches its imported action functions for safe tests.

Functions still used:
- `RouteHandler.handle`
- `RouteHandler._handle_pending_confirmation`

Duplicate functions:
- Not a legacy duplicate yet, but it still depends on private controller methods:
  - `_try_volume_clarification`
  - `_system_control_response`
  - `_handle_alias_match`
  - `_alias_action_response`

Risk level if removed:
- High. It is now part of the new routing flow.

Safe migration steps:
1. Create `response_builder.py`.
2. Move response dict construction out of AssistantController.
3. Replace private controller method calls with ResponseBuilder calls.
4. Keep controller context only for repositories/settings/TTS until those are abstracted.

Final recommendation:
- Keep. It is a new bridge module, not something to delete.

## Recommended Final Architecture After Cleanup

```text
app/
  core/
    assistant_controller.py    # public UI API, history, TTS, settings facade
    command_router.py          # pure route decision
    route_handler.py           # executes route through action layer
    command_normalizer.py
    response_builder.py        # all response dict/text construction

  intents/
    hard_rules.py
    dataset_matcher.py
    alias_matcher.py

  actions/
    system_actions.py          # system-action public API
    alias_actions.py           # URL/app alias execution
    app_actions.py             # app launch/search wrappers
    file_actions.py            # single public file/desktop API
    web_actions.py             # search/weather API

  services/
    system/
      system_action_executor.py # canonical low-level Windows/system executor
      app_launcher.py
    automation/
      email_tools.py
      music_tools.py
      whatsapp_tools.py
      youtube_multimodal.py
    speech/
    ai/
    web/
    vision/
```

## Suggested Cleanup Order

1. Update AssistantController direct file calls to use `app.actions.file_actions`.
2. Update AssistantController legacy system calls to use `app.actions.system_actions`.
3. Create `app/core/response_builder.py`.
4. Move `_system_control_response`, `_alias_action_response`, `_direct_action_response`, and volume clarification response into ResponseBuilder.
5. Move `execute_confirmed_action` dependency out of `system_control.py`.
6. Convert `system_tools.py` functions into wrappers or replace ActionRegistry registrations.
7. Reduce `windows_desktop.py` to only desktop resolution until it can be merged safely.
8. Add regression tests before deleting any compatibility module.

## Completed Cleanup Items

The following items from the original cleanup order are now done:

- `app/core/response_builder.py` exists and is used by `RouteHandler`.
- `app/core/route_handler.py` executes structured routes outside `AssistantController`.
- `app/actions/system_actions.py` wraps canonical system execution.
- `app/actions/file_actions.py` is the public file/desktop facade.
- `app/actions/web_actions.py` is the public web/weather facade.
- `CommandRouter` now decides web/weather routes before falling back to old processing.
- `AssistantController` no longer needs to import low-level `web_search_service` details.

## Remaining Cleanup Tasks

Do these in later phases only, with tests added before removal:

- Move remaining direct-command fallback branches from `AssistantController._try_direct_command()` into a dedicated route/action layer.
- Replace remaining `system_tools.py` ActionRegistry registrations with action-layer wrappers.
- Finish reducing `system_control.py` into a pure compatibility module.
- Decide whether `file_automation.py` or `windows_desktop.py` should own the final low-level file search/opening implementation.
- Add regression tests for file ambiguity, confirmed power actions, Bluetooth settings, screenshot, and web/weather route responses.
- Remove old imports only after `rg` confirms there are no active callers.

## Safe Future Delete/Merge Candidates

These are candidates only after callers and tests are confirmed:

- `app/services/system/system_control.py`: merge remaining unique behavior into `system_action_executor.py`, then keep/deprecate as wrapper before deletion.
- `app/services/automation/system_tools.py`: replace ActionRegistry imports with action-layer functions, then deprecate.
- `app/services/system/file_automation.py`: either keep as the focused backend or merge into a single file service behind `app/actions/file_actions.py`.
- `app/services/automation/windows_desktop.py`: split app-launch behavior away from file/folder behavior, then reduce or merge.
- `app/core/response_engine.py`: delete only after no imports or old response paths depend on it.

## Do Not Delete Yet

- `system_control.py`
- `system_tools.py`
- `file_automation.py`
- `windows_desktop.py`
- `response_engine.py`

They still have imports or behavior that may be required by fallback paths.
