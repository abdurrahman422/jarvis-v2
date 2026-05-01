from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.command_normalizer import normalize_voice_command

LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class AliasAction:
    id: str
    kind: str
    name: str
    target: str
    aliases: tuple[str, ...]
    normalized_aliases: tuple[str, ...]

    @property
    def action(self) -> str:
        return "open_url" if self.kind == "websites" else "open_app"


def dataset_path() -> Path:
    return Path(__file__).resolve().parents[1] / "generated" / "bd_full_alias_dataset.json"


@lru_cache(maxsize=1)
def load_alias_actions() -> tuple[AliasAction, ...]:
    path = dataset_path()
    if not path.exists():
        LOG.warning("[alias-dataset] missing: %s", path)
        return ()

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    actions: list[AliasAction] = []
    for kind in ("websites", "apps"):
        section = payload.get(kind) or {}
        if not isinstance(section, dict):
            continue
        for name, item in section.items():
            if not isinstance(item, dict):
                continue
            target = str(item.get("target") or "").strip()
            aliases = tuple(str(alias).strip() for alias in (item.get("aliases") or ()) if str(alias).strip())
            if not target or not aliases:
                continue
            normalized_aliases = tuple(_norm(alias) for alias in aliases if _norm(alias))
            actions.append(
                AliasAction(
                    id=f"{kind}.{name}",
                    kind=kind,
                    name=str(name),
                    target=target,
                    aliases=aliases,
                    normalized_aliases=normalized_aliases,
                )
            )

    LOG.info("[alias-dataset] loaded actions=%s path=%s", len(actions), path)
    print(f"[alias-dataset] loaded actions={len(actions)}")
    return tuple(actions)


def _norm(text: str) -> str:
    return normalize_voice_command(text, log=False).casefold().replace("য়", "য়")
