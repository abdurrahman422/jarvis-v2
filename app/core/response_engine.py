from __future__ import annotations
"""Legacy response phrasing helper.

Architecture note:
    Response formatting is currently split between this class,
    AssistantController, and RouteHandler/controller response methods. Keep this
    module for compatibility until a dedicated response_builder.py owns all
    response dict/text construction.
"""


class ResponseEngine:
    """
    Human-style phrasing helpers (Bangla-first). Avoids robotic confirmations
    like 'Done.' for schedule-style results and low-confidence answers.
    """

    BN_ACK = (
        "ঠিক আছে",
        "একটু অপেক্ষা করো",
        "আমি চেষ্টা করছি",
        "আমি এখনই করছি",
        "চিন্তা করো না",
    )
    EN_ACK = (
        "Alright",
        "Give me a moment",
        "I'm on it",
        "Working on that",
        "No worries",
    )

    @classmethod
    def render_reply(
        cls,
        intent: str,
        result: str,
        confidence: float,
        lang: str,
        action: str = "",
    ) -> str:
        if lang == "bn":
            if confidence < 0.5:
                return f"একটু নিশ্চিত হতে হচ্ছে—{result}"
            if intent in {"alarm_create", "task_add", "focus_timer"}:
                return f"{result} লোকাল শিডিউলে সেভ করে রাখলাম।"
            return result
        if confidence < 0.5:
            return f"I'm not fully sure, but here is what I found: {result}"
        if intent in {"alarm_create", "task_add", "focus_timer"}:
            return f"{result} I've saved this in your local schedule tools."
        return result
