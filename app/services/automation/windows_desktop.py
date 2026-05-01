"""
Windows desktop launching: apps, system tools, folders, drives, and light search.
Structured outcomes for Bangla TTS/UI and multi-match disambiguation.

Architecture note:
    This is a legacy broad Windows desktop resolver now wrapped by
    app.actions.file_actions. It overlaps with app.services.system.file_automation
    and should be split/merged only after route-level tests cover desktop,
    folder, file search, and ambiguous-pick behavior.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import datetime
from dataclasses import dataclass, field
from typing import Callable, Optional

_ContactGetter = Callable[[str], str]

# --- Optional user extras (settings key desktop_favorite_paths_json: list of folder paths) ---


def _favorites(getter: _ContactGetter) -> list[str]:
    raw = getter("desktop_favorite_paths_json") or "[]"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [str(x).strip() for x in data if isinstance(x, str) and str(x).strip()]


def _user_profile() -> str:
    return os.environ.get("USERPROFILE") or os.path.expanduser("~")


def _windir() -> str:
    return os.environ.get("WINDIR") or r"C:\Windows"


def _known_folder(name: str) -> Optional[str]:
    prof = _user_profile()
    mapping = {
        "desktop": os.path.join(prof, "Desktop"),
        "downloads": os.path.join(prof, "Downloads"),
        "documents": os.path.join(prof, "Documents"),
        "pictures": os.path.join(prof, "Pictures"),
        "videos": os.path.join(prof, "Videos"),
        "music": os.path.join(prof, "Music"),
    }
    return mapping.get(name)


_BN_FOLDER_WORDS: dict[str, str] = {
    "ডেস্কটপ": "desktop",
    "ডেস্কটপে": "desktop",
    "ডাউনলোড": "downloads",
    "ডাউনলোডস": "downloads",
    "ডকুমেন্ট": "documents",
    "ডকুমেন্টস": "documents",
    "নথি": "documents",
    "ছবি": "pictures",
    "ভিডিও": "videos",
    "গান": "music",
    "মিউজিক": "music",
}

_EN_FOLDER_PHRASES: tuple[tuple[str, str], ...] = (
    ("downloads folder", "downloads"),
    ("download folder", "downloads"),
    ("documents folder", "documents"),
    ("document folder", "documents"),
    ("desktop folder", "desktop"),
    ("pictures folder", "pictures"),
    ("videos folder", "videos"),
    ("music folder", "music"),
)


_STOPWORDS_EN = frozenset(
    {
        "my",
        "the",
        "a",
        "an",
        "open",
        "launch",
        "start",
        "folder",
        "file",
        "please",
        "to",
        "this",
        "that",
        "drive",
    }
)
_STOPWORDS_BN = frozenset({"আমার", "মাই", "ফোল্ডার", "খুল", "ওপেন", "করো", "দাও", "টি", "টা"})


@dataclass
class DesktopOutcome:
    """Result of a desktop launch attempt."""

    ok: bool
    log_en: str
    spoken_en: str
    spoken_bn: str
    candidates: list[str] = field(default_factory=list)
    error_key: str = ""  # not_found, access_denied, ambiguous, unsupported, empty_query

    def needs_pick(self) -> bool:
        return bool(self.candidates) and not self.ok


_OFFICE_EXES: dict[str, tuple[str, str, str]] = {
    "word": ("WINWORD.EXE", "Microsoft Word", "মাইক্রোসফট ওয়ার্ড"),
    "excel": ("EXCEL.EXE", "Microsoft Excel", "মাইক্রোসফট এক্সেল"),
    "powerpoint": ("POWERPNT.EXE", "Microsoft PowerPoint", "মাইক্রোসফট পাওয়ারপয়েন্ট"),
    "outlook": ("OUTLOOK.EXE", "Outlook", "আউটলুক"),
}

_OFFICE_ROOT_GLOBS = (
    "Microsoft Office\\root\\Office16",
    "Microsoft Office\\Office16",
    "Microsoft Office\\root\\Office15",
    "Microsoft Office\\Office15",
)


def _program_roots() -> list[str]:
    roots = []
    for key in ("ProgramFiles", "ProgramFiles(x86)"):
        v = os.environ.get(key)
        if v and os.path.isdir(v):
            roots.append(v)
    if not roots:
        roots = [r"C:\Program Files", r"C:\Program Files (x86)"]
    return roots


def _find_office_exe(exe_name: str) -> Optional[str]:
    for pf in _program_roots():
        for sub in _OFFICE_ROOT_GLOBS:
            cand = os.path.join(pf, sub, exe_name)
            if os.path.isfile(cand):
                return cand
    # Click-to-run under Office16 root only by name
    try:
        which = shutil.which(exe_name.lower().replace(".exe", ""))
        if which and os.path.isfile(which):
            return which
    except Exception:
        pass
    return None


def _try_startfile(path: str) -> None:
    os.startfile(path)


def _try_subprocess_exe(path: str) -> bool:
    try:
        subprocess.Popen([path], shell=False, cwd=os.path.dirname(path) or None)
        return True
    except OSError:
        return False


def _try_cmd_start(path: str) -> bool:
    try:
        subprocess.run(
            f'start "" "{path}"',
            shell=True,
            check=False,
            cwd=os.environ.get("WINDIR", "C:\\Windows"),
        )
        return True
    except OSError:
        return False


def _launch_path(path: str) -> bool:
    if not path or not os.path.exists(path):
        return False
    try:
        if os.path.isdir(path):
            subprocess.Popen(["explorer.exe", path], shell=False)
            return True
        _try_startfile(path)
        return True
    except OSError:
        pass
    if _try_subprocess_exe(path):
        return True
    return _try_cmd_start(path)


def _launch_exe_candidates(candidates: list[str], *, uri: Optional[str] = None) -> tuple[bool, str]:
    if uri:
        try:
            os.startfile(uri)
            return True, f"Opened URI {uri}"
        except OSError:
            pass
    for c in candidates:
        if not c:
            continue
        exp = os.path.expandvars(c)
        if shutil.which(os.path.basename(exp).replace(".exe", "")) and not os.path.isfile(exp):
            base = os.path.basename(exp).replace(".exe", "").lower()
            w = shutil.which(base)
            if w:
                try:
                    subprocess.Popen([w], shell=False)
                    return True, f"Opened {w}"
                except OSError:
                    continue
        if os.path.isfile(exp):
            if _try_subprocess_exe(exp):
                return True, f"Opened {exp}"
            try:
                _try_startfile(exp)
                return True, f"Opened {exp}"
            except OSError:
                if _try_cmd_start(exp):
                    return True, f"Started {exp}"
    for base in ["calc", "notepad", "mspaint", "cmd", "powershell", "taskmgr", "snippingtool"]:
        if any(base in os.path.basename(c).lower() for c in candidates if c):
            w = shutil.which(f"{base}.exe") or shutil.which(base)
            if w:
                try:
                    subprocess.Popen([w], shell=False)
                    return True, f"Opened {w}"
                except OSError:
                    continue
    return False, "No working launch method"


def _chrome_paths() -> list[str]:
    out: list[str] = []
    local = os.environ.get("LOCALAPPDATA", "")
    if local:
        out.append(os.path.join(local, "Google", "Chrome", "Application", "chrome.exe"))
    roots = _program_roots()
    if roots:
        out.append(os.path.join(roots[0], "Google", "Chrome", "Application", "chrome.exe"))
    return [p for p in out if p]


def _edge_paths() -> list[str]:
    pf = _program_roots()[0] if _program_roots() else r"C:\Program Files"
    return [
        os.path.join(pf, "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
    ]


def _vscode_paths() -> list[str]:
    out: list[str] = []
    local = os.environ.get("LOCALAPPDATA", "")
    if local:
        out.append(os.path.join(local, "Programs", "Microsoft VS Code", "Code.exe"))
    roots = _program_roots()
    if roots:
        out.append(os.path.join(roots[0], "Microsoft VS Code", "Code.exe"))
    return [p for p in out if p]


APP_MAP: dict[str, dict] = {
    "word": {"paths": [], "office": "word", "fallback": ["winword"]},
    "excel": {"paths": [], "office": "excel", "fallback": ["excel"]},
    "powerpoint": {"paths": [], "office": "powerpoint", "fallback": ["powerpnt"]},
    "office": {"paths": [], "office": "word", "fallback": ["winword"]},
    "microsoft word": {"paths": [], "office": "word", "fallback": ["winword"]},
    "notepad": {"paths": [os.path.join(_windir(), "notepad.exe")], "fallback": ["notepad"]},
    "calculator": {"paths": [os.path.join(_windir(), "System32", "calc.exe")], "fallback": ["calc"]},
    "calc": {"paths": [os.path.join(_windir(), "System32", "calc.exe")], "fallback": ["calc"]},
    "paint": {"paths": [os.path.join(_windir(), "System32", "mspaint.exe")], "fallback": ["mspaint"]},
    "cmd": {"paths": [os.path.join(_windir(), "System32", "cmd.exe")], "fallback": ["cmd"]},
    "command prompt": {"paths": [os.path.join(_windir(), "System32", "cmd.exe")], "fallback": ["cmd"]},
    "powershell": {"paths": [os.path.join(_windir(), "System32", "WindowsPowerShell", "v1.0", "powershell.exe")], "fallback": ["powershell"]},
    "vscode": {"paths": _vscode_paths(), "fallback": ["code"]},
    "visual studio code": {"paths": _vscode_paths(), "fallback": ["code"]},
    "chrome": {"paths": _chrome_paths(), "fallback": ["chrome"]},
    "google chrome": {"paths": _chrome_paths(), "fallback": ["chrome"]},
    "edge": {"paths": _edge_paths(), "fallback": ["msedge"]},
    "microsoft edge": {"paths": _edge_paths(), "fallback": ["msedge"]},
    "browser": {"paths": _chrome_paths() + _edge_paths(), "fallback": ["chrome", "msedge"]},
    "file explorer": {"paths": [], "explorer": "root", "fallback": ["explorer"]},
    "explorer": {"paths": [], "explorer": "root", "fallback": ["explorer"]},
    "this pc": {"paths": [], "explorer": "root", "fallback": ["explorer"]},
    "task manager": {"paths": [os.path.join(_windir(), "System32", "taskmgr.exe")], "fallback": ["taskmgr"]},
    "device manager": {"msc": os.path.join(_windir(), "System32", "devmgmt.msc")},
    "control panel": {"paths": [os.path.join(_windir(), "System32", "control.exe")]},
    "settings": {"uri": "ms-settings:"},
    "windows settings": {"uri": "ms-settings:"},
    "system settings": {"uri": "ms-settings:"},
    "snipping tool": {"paths": [
        os.path.join(_windir(), "System32", "SnippingTool.exe"),
        os.path.join(_windir(), "imaging", "SnippingTool.exe"),
    ], "uri": "ms-screenclip:", "fallback": ["snippingtool"]},
    "run": {"special": "run_dialog"},
}

_BN_APP_PHRASES: dict[str, str] = {
    "ওয়ার্ড": "word",
    "ওয়ার্ড": "word",
    "এক্সেল": "excel",
    "পাওয়ারপয়েন্ট": "powerpoint",
    "পাওয়ারপয়েন্ট": "powerpoint",
    "ক্যালকুলেটর": "calculator",
    "নোটপ্যাড": "notepad",
    "ফাইল এক্সপ্লোরার": "file explorer",
    "এক্সপ্লোরার": "file explorer",
    "কন্ট্রোল প্যানেল": "control panel",
    "টাস্ক ম্যানেজার": "task manager",
    "উইন্ডোজ সেটিংস": "windows settings",
    "ডিভাইস ম্যানেজার": "device manager",
}

_BN_LABEL: dict[str, str] = {
    "notepad": "নোটপ্যাড",
    "calculator": "ক্যালকুলেটর",
    "calc": "ক্যালকুলেটর",
    "paint": "পেইন্ট",
    "cmd": "কমান্ড প্রম্পট",
    "command prompt": "কমান্ড প্রম্পট",
    "powershell": "পাওয়ারশেল",
    "vscode": "ভিএস কোড",
    "visual studio code": "ভিএস কোড",
    "chrome": "ক্রোম",
    "google chrome": "গুগল ক্রোম",
    "edge": "মাইক্রোসফট এজ",
    "browser": "ব্রাউজার",
    "file explorer": "ফাইল এক্সপ্লোরার",
    "explorer": "ফাইল এক্সপ্লোরার",
    "task manager": "টাস্ক ম্যানেজার",
    "device manager": "ডিভাইস ম্যানেজার",
    "control panel": "কন্ট্রোল প্যানেল",
    "settings": "উইন্ডোজ সেটিংস",
    "windows settings": "উইন্ডোজ সেটিংস",
    "snipping tool": "স্নিপিং টুল",
    "office": "অফিস (ওয়ার্ড)",
}


def looks_like_desktop_launch(q: str, ql: str) -> bool:
    from app.services.automation.youtube_multimodal import mentions_youtube

    if mentions_youtube(q, ql):
        return False
    if re.search(r"\bopen\s+google\b", ql) or ql.strip() == "google":
        return False
    if "whatsapp" in ql or "হোয়াটস" in q or "মেসেজ পাঠ" in q:
        return False

    quick = (
        "task manager",
        "device manager",
        "control panel",
        "file explorer",
        "snipping tool",
        "command prompt",
        "powershell",
    )
    if any(t in ql for t in quick):
        return True

    verb = (
        any(h in q for h in ("খুল", "ওপেন", "চালু", "দাও", "করো", "খোল", "চালাও"))
        or bool(re.search(r"\b(open|launch|start)\b", ql))
        or bool(re.search(r"\b(kholo|koro|chalao)\b", ql))
    )
    appish = (
        "notepad",
        "calculator",
        "word",
        "excel",
        "powerpoint",
        "vscode",
        "chrome",
        "edge",
        "paint",
        "cmd",
        "microsoft word",
        "downloads",
        "desktop",
        "documents",
        "drive",
        "ড্রাইভ",
        "ডাউনলোড",
        "ডেস্কটপ",
    )
    if any(a in ql for a in appish):
        return True
    if any(b in q for b in _BN_APP_PHRASES):
        return True
    if "settings" in ql and verb and "voice" not in ql and "tab" not in ql:
        return True
    if "সেটিংস" in q and verb and "ভয়েস" not in q and "জারভিস" not in q and "ট্যাব" not in q:
        return True
    if verb and (
        "folder" in ql
        or "ফোল্ডার" in q
        or "project" in ql
        or "jarvis" in ql
        or "জারভিস" in q
        or "drive" in ql
        or "ড্রাইভ" in q
    ):
        return True
    return False


# Normalize query: lowercase, strip verbs
def _strip_open_verbs(text: str) -> str:
    s = text.strip()
    s = re.sub(r"^(open|launch|start|ওপেন|run)\s+", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+(খুলো|খুল|করো|করুন|দাও|দিন|chalao|kholo|koro)\s*$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^\s*amar\s+", "", s, flags=re.IGNORECASE)
    s = re.sub("^আমার\\s+", "", s)
    return s.strip(" .,।")


def _tokens_for_search(q: str) -> list[str]:
    ql = q.lower()
    parts = re.split(r"[^\w\u0980-\u09FF]+", ql)
    out = []
    for p in parts:
        if not p or p in _STOPWORDS_EN:
            continue
        out.append(p)
    return out[:6]


def _search_named_items(query: str, getter: _ContactGetter) -> list[str]:
    """Shallow search under profile known folders + favorites for path name tokens."""
    tokens = [t for t in _tokens_for_search(query) if t not in ("project", "folder", "ফোল্ডার")]
    if len(tokens) < 1:
        ql = query.lower()
        for raw, slug in _EN_FOLDER_PHRASES:
            if raw in ql:
                tokens = [slug]
                break
    if not tokens:
        return []
    roots: list[str] = []
    for name in ("desktop", "documents", "downloads"):
        p = _known_folder(name)
        if p and os.path.isdir(p):
            roots.append(p)
    roots.extend(_favorites(getter))
    seen: set[str] = set()
    matches: list[str] = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        try:
            for name in os.listdir(root):
                path = os.path.join(root, name)
                cmp = name.lower()
                if all(t in cmp for t in tokens):
                    if path not in seen:
                        seen.add(path)
                        matches.append(path)
        except OSError:
            continue
    return matches[:8]


_DRIVE_RE = re.compile(r"\b([a-z])\s*:?\s*(drive|ড্রাইভ)?\b", re.IGNORECASE)


def _parse_drive_token(text: str) -> Optional[str]:
    m = _DRIVE_RE.search(text.lower())
    if m:
        letter = m.group(1).upper()
        path = f"{letter}:\\"
        if os.path.exists(path):
            return path
    # Bangla এ ড্রাইভ
    if "ই ড্রাইভ" in text or "ই-ড্রাইভ" in text or "e ড্রাইভ" in text.lower():
        if os.path.exists("E:\\"):
            return "E:\\"
    if "ডি ড্রাইভ" in text or re.search(r"\bd\s+ড্রাইভ", text.lower()):
        if os.path.exists("D:\\"):
            return "D:\\"
    if "সি ড্রাইভ" in text:
        if os.path.exists("C:\\"):
            return "C:\\"
    return None


def _map_known_folder_query(q: str) -> Optional[str]:
    ql = q.lower()
    for phrase, slug in _EN_FOLDER_PHRASES:
        if phrase in ql:
            p = _known_folder(slug)
            return p if p and os.path.isdir(p) else None
    for bn, slug in _BN_FOLDER_WORDS.items():
        if bn in q:
            p = _known_folder(slug)
            return p if p and os.path.isdir(p) else None
    if "downloads" in ql or "download" in ql:
        p = _known_folder("downloads")
        if p and os.path.isdir(p):
            return p
    if "desktop" in ql:
        p = _known_folder("desktop")
        if p and os.path.isdir(p):
            return p
    if "documents" in ql:
        p = _known_folder("documents")
        if p and os.path.isdir(p):
            return p
    return None


def _resolve_alias_key(fragment: str) -> Optional[str]:
    f = fragment.lower().strip()
    if not f:
        return None
    for bn, key in _BN_APP_PHRASES.items():
        if bn in fragment:
            return key
    if f in APP_MAP:
        return f
    for key in sorted(APP_MAP.keys(), key=len, reverse=True):
        if key in f:
            return key
    return None


def _outcome_success(label_en: str, label_bn: str, log: str) -> DesktopOutcome:
    return DesktopOutcome(
        True,
        log,
        f"Opening {label_en}.",
        f"ঠিক আছে, আমি {label_bn} চালু করছি।",
    )


def _outcome_fail(key: str, hint_en: str, hint_bn: str) -> DesktopOutcome:
    return DesktopOutcome(
        False,
        f"Error:{key}:{hint_en}",
        hint_en,
        hint_bn,
        error_key=key,
    )


def _outcome_ambig(paths: list[str]) -> DesktopOutcome:
    lines_en = "Multiple matches:\n" + "\n".join(f"  {i+1}. {p}" for i, p in enumerate(paths))
    lines_bn = "আমি একাধিক জিনিস পেয়েছি—কোনটি খুলবে? নম্বর বলো:\n" + "\n".join(
        f"  {i+1}. {p}" for i, p in enumerate(paths)
    )
    return DesktopOutcome(
        False,
        f"AMBIG:{len(paths)}",
        lines_en,
        lines_bn,
        candidates=list(paths),
        error_key="ambiguous",
    )


def resolve_desktop_command(user_text: str, getter: _ContactGetter) -> DesktopOutcome:
    q = user_text.strip()
    ql = q.lower()
    if not q:
        return _outcome_fail("empty_query", "Say what to open.", "কী খুলবো বলো।")

    if re.search(r"this file|এই ফাইল", ql) or ("this file" in ql):
        return _outcome_fail(
            "unsupported",
            "Specify a file path to open.",
            "কোন ফাইল খুলবে—পুরো পাথ বলো বা ফাইল এক্সপ্লোরারে গিয়ে বেছে নাও।",
        )

    core = _strip_open_verbs(q)
    if not core:
        core = q

    # Drive
    drv = _parse_drive_token(q)
    if drv and (
        "drive" in ql
        or "ড্রাইভ" in q
        or "open" in ql
        or "launch" in ql
        or "খুল" in q
        or "ওপেন" in q
        or re.match(r"^[a-z]\s*:\s*$", core, re.I)
    ):
        if _launch_path(drv):
            return _outcome_success(f"{drv} drive", f"{drv} ড্রাইভ", f"Opened {drv}")

    # Known shell folder
    folder = _map_known_folder_query(q)
    if folder and _bangla_implies_folder_open(q, ql):
        if _launch_path(folder):
            bn = "ডাউনলোডস ফোল্ডার" if "download" in folder.lower() else "ফোল্ডার"
            if "Desktop" in folder:
                bn = "ডেস্কটপ ফোল্ডার"
            if "Documents" in folder:
                bn = "ডকুমেন্টস ফোল্ডার"
            return _outcome_success(folder, bn, f"Opened {folder}")

    # Named search (my jarvis project)
    if any(w in ql for w in ("my ", "project", "folder", "মাই ", "জারভিস", "jarvis")):
        found = _search_named_items(core or q, getter)
        if len(found) > 1:
            return _outcome_ambig(found)
        if len(found) == 1:
            if _launch_path(found[0]):
                return _outcome_success(found[0], found[0], f"Opened {found[0]}")

    # Raw path
    if re.match(r"^[a-z]:\\", core, re.I) or core.startswith("\\\\"):
        if os.path.exists(core):
            try:
                if _launch_path(core):
                    return _outcome_success(core, core, f"Opened {core}")
            except Exception:
                return _outcome_fail("access_denied", "Could not open that path.", "ওই পাথ খুলতে পারিনি—অনুমতি বা পাথ চেক করো।")
        return _outcome_fail("not_found", "Path not found.", "পাথ খুঁজে পাওয়া যায়নি।")

    alias = _resolve_alias_key(core)
    if alias is None:
        alias = _resolve_alias_key(q)

    if alias:
        spec = APP_MAP.get(alias)
        if not spec:
            parts = [p for p in (alias.split() if alias else []) if len(p) > 2]
            found2 = _search_named_items(" ".join(parts), getter) if parts else []
            if len(found2) > 1:
                return _outcome_ambig(found2)
            if len(found2) == 1 and _launch_path(found2[0]):
                return _outcome_success(found2[0], found2[0], f"Opened {found2[0]}")
            return _outcome_fail(
                "not_found",
                f"Could not find how to open '{core}'.",
                f"এই অ্যাপটি খুঁজে পাইনি—অন্য নামে চেষ্টা করবে? ({core})",
            )

        # special run dialog
        if spec.get("special") == "run_dialog":
            return _outcome_fail(
                "unsupported",
                "Run dialog needs Win+R from keyboard.",
                "রান ডায়ালগ সরাসরি খুলতে পারছি না—কীবোর্ডে Win+R চেপে চেষ্টা করো।",
            )

        if spec.get("msc"):
            msc = spec["msc"]
            if os.path.isfile(msc):
                try:
                    os.startfile(msc)
                    return _outcome_success("Device Manager", "ডিভাইস ম্যানেজার", f"Opened {msc}")
                except OSError:
                    pass

        if spec.get("uri"):
            ok, _ = _launch_exe_candidates([], uri=spec["uri"])
            if ok:
                labs = spec.get("label_bn") or ("সেটিংস" if "settings" in alias else alias)
                return _outcome_success("Settings", labs, "Opened ms-settings")

        office_key = spec.get("office")
        if office_key and office_key in _OFFICE_EXES:
            exe_name, en, bn = _OFFICE_EXES[office_key]
            pth = _find_office_exe(exe_name)
            if pth and _launch_path(pth):
                return _outcome_success(en, bn, f"Opened {pth}")
            fb = exe_name.replace(".EXE", "").replace(".exe", "").lower()
            w = shutil.which(fb) or shutil.which(f"{fb}.exe")
            if w and _launch_path(w):
                return _outcome_success(en, bn, f"Opened {w}")

        if spec.get("explorer") == "root":
            try:
                subprocess.Popen(["explorer.exe"], shell=False)
                return _outcome_success("File Explorer", "ফাইল এক্সপ্লোরার", "Opened explorer")
            except OSError:
                pass

        paths = list(spec.get("paths") or [])
        for fn in spec.get("fallback") or []:
            w = shutil.which(fn) or shutil.which(f"{fn}.exe")
            if w:
                paths.insert(0, w)
        ok, log = _launch_exe_candidates(paths, uri=spec.get("uri"))
        if ok:
            label_en = alias.replace("microsoft ", "").title()
            label_bn = _BN_LABEL.get(alias, label_en)
            if office_key and office_key in _OFFICE_EXES:
                _, label_en, label_bn = _OFFICE_EXES[office_key]
            return _outcome_success(label_en, label_bn, log)

        return _outcome_fail(
            "not_found",
            f"Could not launch {core}.",
            f"এই অ্যাপটি খুঁজে পাইনি বা চালু করতে পারিনি—অন্য নামে চেষ্টা করবে? ({core})",
        )

    # Final: try path as directory under profile
    guess = os.path.join(_user_profile(), core)
    if os.path.exists(guess):
        if _launch_path(guess):
            return _outcome_success(guess, guess, f"Opened {guess}")

    return _outcome_fail(
        "not_found",
        f"I don't know how to open '{core}'.",
        f"বুঝতে পারিনি কী খুলবো—আরেকটু স্পষ্ট করে বলবে? ({core})",
    )


def _bangla_implies_folder_open(q: str, ql: str) -> bool:
    if "open" in ql or "launch" in ql:
        return True
    bang = (
        "খুল",
        "ওপেন",
        "দেখ",
        "যা",
        "চালু",
        "ফোল্ডার",
        "ডাউনলোড",
        "ডেস্কটপ",
        "ডকুমেন্ট",
    )
    return any(b in q for b in bang)


def complete_pick(user_reply: str, candidates: list[str]) -> DesktopOutcome:
    t = user_reply.strip().lower()
    if t in ("cancel", "বাতিল", "থামো", "stop"):
        return DesktopOutcome(
            False,
            "Cancelled.",
            "Cancelled pick.",
            "ঠিক আছে, বাতিল করলাম।",
            error_key="cancelled",
        )
    # number
    if t.isdigit():
        i = int(t) - 1
        if 0 <= i < len(candidates):
            path = candidates[i]
            if _launch_path(path):
                return _outcome_success(path, path, f"Opened {path}")
            return _outcome_fail("access_denied", "Could not open selection.", "খুলতে পারিনি।")
    # Bangla numbers
    bn_map = {"১": 1, "২": 2, "৩": 3, "৪": 4, "৫": 5}
    for ch, n in bn_map.items():
        if ch in user_reply:
            i = n - 1
            if 0 <= i < len(candidates):
                path = candidates[i]
                if _launch_path(path):
                    return _outcome_success(path, path, f"Opened {path}")
    # substring match
    for path in candidates:
        leaf = os.path.basename(path).lower()
        if t and t in leaf:
            if _launch_path(path):
                return _outcome_success(path, path, f"Opened {path}")
    return _outcome_fail(
        "ambiguous",
        "Pick a number from the list.",
        "তালিকা থেকে একটা নম্বর বলো—যেমন ১ বা ২।",
    )


def extend_app_alias(alias: str, config: dict) -> None:
    """Merge extra alias -> launch config at runtime (optional)."""
    key = alias.strip().lower()
    if key:
        APP_MAP[key] = config


# ----------------------------- File control helpers -----------------------------

_LAST_FILE_REF: str = ""
_HOME = _user_profile()
_COMMON_FILE_ROOTS = (
    os.path.join(_HOME, "Downloads"),
    os.path.join(_HOME, "Desktop"),
    os.path.join(_HOME, "Documents"),
    os.getcwd(),
)


def _safe_existing_roots() -> list[str]:
    return [p for p in _COMMON_FILE_ROOTS if p and os.path.isdir(p)]


def open_folder(path: str) -> str:
    if not path or not os.path.isdir(path):
        return f"Folder not found: {path}"
    try:
        subprocess.Popen(["explorer.exe", path], shell=False)
        return f"Opened folder: {path}"
    except OSError as exc:
        return f"Could not open folder: {exc}"


def open_file(path: str) -> str:
    global _LAST_FILE_REF
    if not path or not os.path.isfile(path):
        return f"File not found: {path}"
    try:
        os.startfile(path)
        _LAST_FILE_REF = path
        return f"Opened file: {path}"
    except OSError as exc:
        return f"Could not open file: {exc}"


def get_latest_file(folder: str) -> Optional[str]:
    if not folder or not os.path.isdir(folder):
        return None
    newest: tuple[float, str] | None = None
    try:
        for name in os.listdir(folder):
            path = os.path.join(folder, name)
            if not os.path.isfile(path):
                continue
            mtime = os.path.getmtime(path)
            if newest is None or mtime > newest[0]:
                newest = (mtime, path)
    except OSError:
        return None
    return newest[1] if newest else None


def get_latest_file_by_extension(folder: str, ext: str) -> Optional[str]:
    if not folder or not os.path.isdir(folder):
        return None
    target_ext = ext.lower().strip()
    if target_ext and not target_ext.startswith("."):
        target_ext = f".{target_ext}"
    newest: tuple[float, str] | None = None
    try:
        for name in os.listdir(folder):
            path = os.path.join(folder, name)
            if not os.path.isfile(path):
                continue
            if not name.lower().endswith(target_ext):
                continue
            mtime = os.path.getmtime(path)
            if newest is None or mtime > newest[0]:
                newest = (mtime, path)
    except OSError:
        return None
    return newest[1] if newest else None


def search_file_recursive(root: str, query: str) -> list[str]:
    if not root or not os.path.isdir(root):
        return []
    q = (query or "").strip().lower()
    if not q:
        return []
    matches: list[str] = []
    try:
        for base, _, files in os.walk(root):
            for name in files:
                if q in name.lower():
                    matches.append(os.path.join(base, name))
                    if len(matches) >= 20:
                        return matches
    except OSError:
        return matches
    return matches


def search_file(query: str) -> list[str]:
    hits: list[str] = []
    seen: set[str] = set()
    for root in _safe_existing_roots():
        for item in search_file_recursive(root, query):
            if item not in seen:
                seen.add(item)
                hits.append(item)
            if len(hits) >= 20:
                return hits
    return hits


def _today_file_candidates(folder: str) -> list[str]:
    if not folder or not os.path.isdir(folder):
        return []
    out: list[str] = []
    today = datetime.now().date()
    try:
        for name in os.listdir(folder):
            path = os.path.join(folder, name)
            if not os.path.isfile(path):
                continue
            mdate = datetime.fromtimestamp(os.path.getmtime(path)).date()
            if mdate == today:
                out.append(path)
    except OSError:
        return []
    out.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return out


def _default_downloads() -> str:
    return os.path.join(_user_profile(), "Downloads")


def _resolve_folder_alias(user_text: str) -> Optional[str]:
    q = user_text.lower()
    if "download" in q:
        return _known_folder("downloads")
    if "desktop" in q:
        return _known_folder("desktop")
    if "document" in q:
        return _known_folder("documents")
    if "project folder" in q or ("project" in q and "folder" in q):
        return os.getcwd()
    return None


def _extract_ext(user_text: str) -> Optional[str]:
    m = re.search(r"\b(?:last|latest|open)\s+([a-z0-9]{2,6})\b", user_text.lower())
    if not m:
        return None
    token = m.group(1)
    if token in {"file", "download", "folder"}:
        return None
    return f".{token}"


def execute_file_control(user_text: str) -> str:
    global _LAST_FILE_REF
    q = user_text.strip()
    ql = q.lower()

    folder = _resolve_folder_alias(ql)
    if folder and any(k in ql for k in ("open", "খুল", "ওপেন")) and "file" not in ql:
        return open_folder(folder)

    if "open latest download" in ql or "open last download" in ql:
        latest = get_latest_file(_default_downloads())
        if not latest:
            return "No downloaded file found."
        return open_file(latest)

    if "open latest file" in ql or "open last file" in ql:
        for root in _safe_existing_roots():
            latest = get_latest_file(root)
            if latest:
                return open_file(latest)
        return "No recent file found."

    ext = _extract_ext(ql)
    if ext and ("latest" in ql or "last" in ql or "open" in ql):
        for root in _safe_existing_roots():
            latest_ext = get_latest_file_by_extension(root, ext)
            if latest_ext:
                return open_file(latest_ext)
        return f"No recent {ext} file found."

    if "today file" in ql:
        for root in _safe_existing_roots():
            cands = _today_file_candidates(root)
            if cands:
                return open_file(cands[0])
        return "No file from today found."

    if "last file" in ql and _LAST_FILE_REF:
        return open_file(_LAST_FILE_REF)

    if ql.startswith("find ") or ql.startswith("search "):
        query = re.sub(r"^(find|search)\s+", "", ql).strip()
        found = search_file(query)
        if not found:
            return f"No file found for: {query}"
        preview = " | ".join(found[:3])
        return f"Found {len(found)} file(s). Top matches: {preview}"

    # open explicit filename (e.g., open report.pdf)
    name_match = re.match(r"^open\s+(.+)$", ql)
    if name_match:
        name = name_match.group(1).strip().strip('"')
        if "\\" in name or ":" in name:
            return open_file(name) if os.path.isfile(name) else open_folder(name)
        found = search_file(name)
        if not found:
            return f"Could not find: {name}"
        return open_file(found[0])

    return "I could not map that file command yet."
