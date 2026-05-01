from __future__ import annotations

import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _install_optional_dependency_stubs() -> None:
    if "psutil" not in sys.modules:
        psutil = types.ModuleType("psutil")
        psutil.sensors_battery = lambda: None
        psutil.cpu_percent = lambda interval=0: 1.0
        psutil.virtual_memory = lambda: types.SimpleNamespace(used=1, total=2, percent=50)
        sys.modules["psutil"] = psutil

    if "speech_recognition" not in sys.modules:
        sr = types.ModuleType("speech_recognition")

        class Recognizer:
            def __init__(self) -> None:
                self.dynamic_energy_threshold = True
                self.pause_threshold = 0.8
                self.phrase_threshold = 0.3
                self.non_speaking_duration = 0.5
                self.energy_threshold = 300

        class Microphone:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

        sr.Recognizer = Recognizer
        sr.Microphone = Microphone
        sr.AudioData = object
        sr.WaitTimeoutError = type("WaitTimeoutError", (Exception,), {})
        sr.UnknownValueError = type("UnknownValueError", (Exception,), {})
        sr.RequestError = type("RequestError", (Exception,), {})
        sys.modules["speech_recognition"] = sr


def main() -> None:
    _install_optional_dependency_stubs()

    from app.core import assistant_controller as controller_module
    from app.actions import alias_actions, system_actions
    from app.core import route_handler
    from app.core.action_executor import ActionExecutionResult
    from app.services.system.system_action_executor import SystemActionExecutionResult

    def fake_system(record, original_text: str = "", normalized_text: str = ""):
        return SystemActionExecutionResult(
            True,
            record.intent,
            record.action,
            record.target,
            f"SYSTEM:{record.target}",
            f"SYSTEM:{record.target}",
        )

    def fake_alias(action):
        return ActionExecutionResult(
            True,
            "alias_command",
            action.action,
            action.target,
            f"ALIAS:{action.name}:{action.target}",
        )

    controller_module.execute_dataset_action = fake_system
    controller_module.execute_alias_action = fake_alias
    system_actions.execute_system_route = fake_system
    alias_actions.execute_alias_route = lambda match: fake_alias(match.action)
    controller_module.execute_system_route = fake_system
    controller_module.execute_alias_route = lambda match: fake_alias(match.action)
    route_handler.execute_system_route = fake_system
    route_handler.execute_alias_route = lambda match: fake_alias(match.action)
    controller = controller_module.AssistantController()

    cases = [
        ("volume komao", "set_volume", "volume_down"),
        ("ভলিউম komao", "set_volume", "volume_down"),
        ("voliom komao", "set_volume", "volume_down"),
        ("ভলিউম", "volume.clarify", "volume"),
        ("utub open", "open_url", "https://youtube.com"),
        ("gogle kholo", "open_url", "https://google.com"),
        ("zoom kholo", "open_app", "zoom"),
    ]
    for text, expected_action, expected_target in cases:
        out = controller.process(text, speak=False)
        action = out.get("action")
        target = out.get("target")
        assert action == expected_action, f"{text!r}: action {action!r} != {expected_action!r}"
        assert target == expected_target, f"{text!r}: target {target!r} != {expected_target!r}"
        if text == "voliom komao":
            assert out.get("type") == "system_action", "voliom komao must not route to alias/Zoom"

    print("command routing tests passed")


if __name__ == "__main__":
    main()
