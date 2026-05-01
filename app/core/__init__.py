import importlib.abc
import importlib.machinery
import sys


__all__ = []


def _patch_assistant_controller(module) -> None:
    controller_cls = getattr(module, "AssistantController", None)
    if controller_cls is None or getattr(controller_cls, "_fuzzy_confirmation_patched", False):
        return

    original_process_impl = controller_cls._process_impl

    def _process_impl_with_fuzzy_confirmation(self, text: str, speak: bool, *args, **kwargs) -> dict:
        normalized_text = module.normalize_unicode(text)
        route = self.router.route(normalized_text)
        if bool(getattr(route, "needs_confirmation", False)):
            reply_lang = module.resolve_reply_language(
                self._settings.get("response_language", "auto"),
                normalized_text,
            )
            response = (
                f"I found a possible command ({route.action}) with "
                f"{route.confidence:.2f} confidence. Please confirm before I run it."
            )
            self.conversations.add("user", normalized_text)
            self.commands.add(normalized_text, route.intent, route.action, response, route.confidence)
            self.conversations.add("assistant", response)
            out = {
                "intent": route.intent,
                "action": route.action,
                "confidence": route.confidence,
                "response": response,
                "reply_lang": reply_lang,
                "recognized_text": normalized_text,
                "needs_confirmation": True,
                "pending_action": route.action,
            }
            if speak and self.is_voice_reply_enabled():
                tts_note = self._speak_reply(response, reply_lang, source=route.action)
                if tts_note:
                    out["tts_warning"] = tts_note
            return out
        return original_process_impl(self, text, speak, *args, **kwargs)

    controller_cls._process_impl = _process_impl_with_fuzzy_confirmation
    controller_cls._fuzzy_confirmation_patched = True


class _AssistantControllerPatchLoader(importlib.abc.Loader):
    def __init__(self, wrapped_loader) -> None:
        self._wrapped_loader = wrapped_loader

    def create_module(self, spec):
        create_module = getattr(self._wrapped_loader, "create_module", None)
        if create_module is None:
            return None
        return create_module(spec)

    def exec_module(self, module) -> None:
        self._wrapped_loader.exec_module(module)
        _patch_assistant_controller(module)


class _AssistantControllerPatchFinder(importlib.abc.MetaPathFinder):
    _fullname = __name__ + ".assistant_controller"

    def find_spec(self, fullname, path, target=None):
        if fullname != self._fullname:
            return None
        try:
            sys.meta_path.remove(self)
            spec = importlib.machinery.PathFinder.find_spec(fullname, path)
        finally:
            if self not in sys.meta_path:
                sys.meta_path.insert(0, self)
        if spec is None or spec.loader is None:
            return spec
        spec.loader = _AssistantControllerPatchLoader(spec.loader)
        return spec


if not any(isinstance(finder, _AssistantControllerPatchFinder) for finder in sys.meta_path):
    sys.meta_path.insert(0, _AssistantControllerPatchFinder())
