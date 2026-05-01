import re
import smtplib
from email.message import EmailMessage


def _compact_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _extract_topic(user_text: str) -> str:
    text = _compact_whitespace(user_text)
    if not text:
        return "your request"
    text = re.sub(
        r"^(write|draft|send)\s+(a\s+)?(formal\s+)?(leave\s+)?(mail|email)\s*(to\s+[a-z0-9._ -]+)?",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip(" .,:;-")
    return text or "your request"


def _subject_from_topic(topic: str, is_leave: bool = False, is_formal: bool = False) -> str:
    t = _compact_whitespace(topic)
    if is_leave:
        if any(k in t.lower() for k in ("tomorrow", "today", "sick", "emergency", "medical")):
            return "Leave Request for Tomorrow"
        return "Leave Application"
    if is_formal:
        if t and len(t) > 8:
            return f"Formal Request: {t[:60]}"
        return "Formal Request"
    if t and len(t) > 8:
        return f"Regarding: {t[:70]}"
    return "Regarding your request"


def generate_email(user_text: str) -> tuple[str, str]:
    topic = _extract_topic(user_text)
    subject = _subject_from_topic(topic, is_leave=False, is_formal=False)
    body = (
        "Dear Sir/Madam,\n\n"
        "I hope you are doing well.\n"
        f"I am writing regarding {topic}.\n"
        "Please let me know if any additional information is required from my side.\n\n"
        "Best regards,\n"
        "Jarvis User"
    )
    return subject, body


def generate_formal_email(user_text: str) -> tuple[str, str]:
    topic = _extract_topic(user_text)
    subject = _subject_from_topic(topic, is_formal=True)
    body = (
        "Dear Sir/Madam,\n\n"
        "I hope this message finds you well.\n"
        f"I am writing to formally communicate that {topic}.\n"
        "I would be grateful for your kind consideration and approval.\n"
        "Please let me know if any further details are required.\n\n"
        "Sincerely,\n"
        "Jarvis User"
    )
    return subject, body


def generate_leave_email(user_text: str) -> tuple[str, str]:
    topic = _extract_topic(user_text)
    subject = _subject_from_topic(topic, is_leave=True)
    body = (
        "Dear Sir,\n\n"
        "I hope you are well.\n"
        f"I am writing to request leave as {topic}.\n"
        "I kindly request you to grant me leave for the mentioned time.\n"
        "I will remain available for urgent communication if needed.\n\n"
        "Sincerely,\n"
        "Jarvis User"
    )
    return subject, body


def preview_email(to: str, subject: str, body: str) -> str:
    return (
        "Email Draft Preview:\n"
        "-------------------\n"
        f"To: {to}\n"
        f"Subject: {subject}\n\n"
        f"{body}\n\n"
        "Reply with:\n"
        "- 'send' to confirm\n"
        "- 'edit ...' to revise\n"
        "- 'cancel' to abort\n\n"
        "Should I send this email?"
    )


def edit_email(subject: str, body: str, instruction: str) -> tuple[str, str]:
    note = _compact_whitespace(instruction)
    if not note:
        return subject, body
    low = note.lower()
    new_subject = subject
    new_body = body
    if low.startswith("subject:"):
        new_subject = note.split(":", 1)[1].strip() or subject
    elif low.startswith("body:"):
        new_body = note.split(":", 1)[1].strip() or body
    else:
        new_body = f"{body}\n\nAdditional note: {note}"
    return new_subject, new_body


def send_email(
    to: str,
    subject: str,
    body: str,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    use_tls: bool = True,
) -> str:
    if not to or "@" not in to:
        return "Recipient email is invalid."
    if not smtp_host or not smtp_user or not smtp_password:
        return "SMTP is not configured. Set email_smtp_host, email_smtp_user, email_smtp_password in settings."

    msg = EmailMessage()
    msg["From"] = smtp_user
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            if use_tls:
                server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        return f"Email sent successfully to {to}."
    except Exception as exc:
        return f"Email sending failed: {exc}"
