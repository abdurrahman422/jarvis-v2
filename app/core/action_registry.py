from collections.abc import Callable


ActionFn = Callable[[str], str]


class ActionRegistry:
    def __init__(self) -> None:
        self._actions: dict[str, ActionFn] = {}

    def register(self, name: str, handler: ActionFn) -> None:
        self._actions[name] = handler

    def call(self, name: str, user_text: str) -> str:
        handler = self._actions.get(name)
        if not handler:
            return f"Action '{name}' is not available yet."
        return handler(user_text)

    def names(self) -> list[str]:
        return sorted(self._actions.keys())
