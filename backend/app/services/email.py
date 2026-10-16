import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

log = logging.getLogger(__name__)


def email_enabled() -> bool:
    if settings.smtp_user and not settings.smtp_password:
        return False  # a login is configured but its password is not: treat email as off instead of failing every send
    return bool(settings.smtp_host and settings.smtp_from)


def deliver(to: str, subject: str, body: str, html: str | None = None) -> None:
    """Send one message and raise on any failure (used by the credential check command)."""
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = settings.smtp_from, to, subject
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")
    if settings.smtp_port == 465:
        client = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10)
    else:
        client = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)
    with client as s:
        if settings.smtp_port != 465 and settings.smtp_starttls:
            s.starttls()
        if settings.smtp_user:
            s.login(settings.smtp_user, settings.smtp_password)
        s.send_message(msg)


def send_email(to: str, subject: str, body: str, html: str | None = None) -> bool:
    """Best-effort send. Never raises: a mail outage must not break the app, signups or the jobs."""
    if not email_enabled():
        log.info("Email not configured; skipped %r to %s", subject, to)
        return False
    try:
        deliver(to, subject, body, html)
        return True
    except Exception:  # noqa: BLE001
        log.exception("Failed to send email to %s", to)
        return False
