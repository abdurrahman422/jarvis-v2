from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.action_executor import execute_alias_action
from app.core.alias_command_matcher import match_alias_command
from app.core.alias_dataset_loader import load_alias_actions


CASES = (
    "yt kholo",
    "open google",
    "chrome kholo",
    "notepad kholo",
    "calculator open koro",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test bd_full_alias_dataset matching.")
    parser.add_argument("--execute", action="store_true", help="Actually execute high-confidence safe open_url/open_app actions.")
    parser.add_argument("commands", nargs="*", help="Commands to test instead of built-in smoke cases.")
    args = parser.parse_args()

    actions = load_alias_actions()
    print(f"loaded={len(actions)}")

    ok = True
    for command in args.commands or CASES:
        match = match_alias_command(command)
        if match is None:
            ok = False
            print(f"MISS command={command!r}")
            continue
        status = "execute" if match.should_execute else "confirm" if match.should_confirm else "fallback"
        print(
            f"command={command!r} id={match.action.id} action={match.action.action} "
            f"target={match.action.target} confidence={match.confidence:.3f} status={status}"
        )
        if args.execute and match.should_execute:
            result = execute_alias_action(match.action)
            print(f"  result success={result.success} response={result.response!r} error={result.error!r}")
            ok = ok and result.success
        else:
            ok = ok and match.confidence >= 0.65

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
