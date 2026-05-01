import json
import os
import re
import time
from typing import Callable, Optional
from urllib.parse import quote_plus

try:
    import pyautogui
except Exception:
    pyautogui = None

from app.services.offline_guard import block_internet

_ContactGetter = Callable[[str], str]
_ContactResolver = Callable[[str], str]


def open_whatsapp(_: str) -> str:
    return block_internet("WhatsApp")


def _parse_contact_map(raw: str) -> dict[str, str]:
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in data.items():
        if isinstance(k, str) and isinstance(v, str):
            out[k.strip().casefold()] = v.strip()
    return out


def resolve_whatsapp_recipient(
    user_fragment: str,
    get_setting: _ContactGetter,
    get_contact_whatsapp: Optional[_ContactResolver] = None,
) -> Optional[str]:
    """Return E.164-like +digits if user gave a number or a known contact name."""
    raw = (user_fragment or "").strip()
    if not raw:
        return None
    embedded = re.search(r"(\+\d{10,15})", raw)
    if embedded:
        return embedded.group(1)
    compact = re.sub(r"[\s\-_.]", "", raw)
    digits = re.sub(r"\D", "", compact)
    if 10 <= len(digits) <= 15:
        return f"+{digits}"

    blob = get_setting("whatsapp_contacts_json")
    book = _parse_contact_map(blob)
    key = raw.casefold()
    value = book.get(key)
    if value:
        return value
    if get_contact_whatsapp is not None:
        db_hit = (get_contact_whatsapp(raw) or "").strip()
        if db_hit:
            return db_hit
    return None


def send_whatsapp_to(phone: str, message: str) -> str:
    """WhatsApp Web sending is disabled in offline mode."""
    phone = phone.strip()
    if not re.match(r"\+\d{10,15}$", phone):
        return "Valid phone not found. Use international format like +8801712345678."
    body = (message or "").strip()
    if not body:
        return "Message body is empty."
    return block_internet("WhatsApp message")


def send_whatsapp_message(contact: str, text: str) -> str:
    """Convenience alias used by controller flow."""
    return send_whatsapp_to(contact, text)


def send_whatsapp_file(contact: str, file_path: str) -> str:
    """
    Attempt Windows-friendly file send flow on WhatsApp Web.
    Requires pyautogui and user logged in on web.whatsapp.com.
    """
    phone = (contact or "").strip()
    path = (file_path or "").strip().strip('"')
    if not re.match(r"\+\d{10,15}$", phone):
        return "Valid WhatsApp contact/phone not found."
    if not path or not os.path.isfile(path):
        return f"File not found: {path}"
    if pyautogui is None:
        return "pyautogui is required for file send automation. Install it with: pip install pyautogui"

    return block_internet("WhatsApp file")


def send_whatsapp(text: str) -> str:
    """
    Command format:
    whatsapp send +911234567890 | your message
    """
    cmd = text.strip()
    if "|" not in cmd:
        return "Use: whatsapp send <phone_with_country_code> | <message>"
    left, message = cmd.split("|", 1)
    phone_match = re.search(r"(\+\d{10,15})", left)
    if not phone_match:
        return "Valid phone not found. Use international format like +911234567890."
    body = message.strip()
    return send_whatsapp_to(phone_match.group(1), body)


def send_whatsapp_stub(text: str) -> str:
    return send_whatsapp(text)
