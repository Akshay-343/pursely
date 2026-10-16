"""Transactional emails. Each returns (subject, plain_text, html). User-controlled values are HTML-escaped."""
from html import escape

from app.core.config import settings


def _wrap(title: str, body_html: str, button: tuple[str, str] | None = None) -> str:
    btn = ""
    if button:
        label, url = button
        btn = (f'<p style="margin:24px 0"><a href="{escape(url, quote=True)}" style="background:#0f766e;color:#ffffff;'
               f'padding:12px 20px;border-radius:8px;text-decoration:none;font-weight:600;display:inline-block">{escape(label)}</a></p>'
               f'<p style="color:#6b7280;font-size:13px">Button not working? Copy this link into your browser:<br>'
               f'<span style="word-break:break-all">{escape(url)}</span></p>')
    return (f'<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:520px;margin:0 auto;padding:24px;color:#14201d">'
            f'<h1 style="font-size:20px;margin:0 0 16px">{escape(title)}</h1>{body_html}{btn}'
            f'<p style="color:#9ca3af;font-size:12px;margin-top:32px">Pursely</p></div>')


def welcome(email: str) -> tuple[str, str, str]:
    url = settings.app_url.rstrip("/")
    subject = "Welcome to Pursely"
    text = (f"Welcome to Pursely!\n\nYour account ({email}) is ready. Log your first expense, add your subscriptions "
            f"and set a budget to see your dashboard come alive.\n\nOpen the app: {url}\n")
    html = _wrap("Welcome to Pursely", f"<p>Your account (<b>{escape(email)}</b>) is ready.</p>"
                 "<p>Log your first expense, add your subscriptions and set a budget to see your dashboard come alive.</p>",
                 ("Open Pursely", url))
    return subject, text, html


def password_reset(link: str, minutes: int, google_only: bool = False) -> tuple[str, str, str]:
    subject = "Reset your Pursely password"
    note = ("You signed up with Google, so you have no password yet. Setting one lets you also sign in with your email.\n\n"
            if google_only else "")
    text = (f"We received a request to reset your password.\n\n{note}Open this link within {minutes} minutes to choose a new one:\n"
            f"{link}\n\nIf you did not ask for this, ignore this email. Your password stays the same.\n")
    html = _wrap("Reset your password",
                 (f"<p>{escape(note.strip())}</p>" if note else "")
                 + f"<p>We received a request to reset your password. The link works for {minutes} minutes and only once.</p>"
                 "<p>If you did not ask for this, you can ignore this email. Your password stays the same.</p>",
                 ("Choose a new password", link))
    return subject, text, html


def password_changed() -> tuple[str, str, str]:
    subject = "Your Pursely password was changed"
    text = ("Your password was just changed. If this was you, no action is needed.\n\n"
            "If it was not you, reset your password right away from the login page.\n")
    html = _wrap("Password changed", "<p>Your password was just changed. If this was you, no action is needed.</p>"
                 "<p><b>If it was not you</b>, reset your password right away from the login page.</p>")
    return subject, text, html
