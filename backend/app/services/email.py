import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

log = logging.getLogger(__name__)


def email_enabled() -> bool:
    return bool(settings.smtp_host and settings.smtp_from)


def send_email(to: str, subject: str, body: str) -> bool:
    """Best-effort send. Never raises: a mail outage must not break the app or the jobs."""
    if not email_enabled():
        return False
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = settings.smtp_from, to, subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as s:
            s.starttls()
            if settings.smtp_user:
                s.login(settings.smtp_user, settings.smtp_password)
            s.send_message(msg)
        return True
    except Exception:  # noqa: BLE001
        log.exception("Failed to send email to %s", to)
        return False
