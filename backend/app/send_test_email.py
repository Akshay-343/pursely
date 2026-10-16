"""Check your email settings: python -m app.send_test_email you@example.com

Sends one real message with the SMTP_* settings and prints exactly what went wrong if it fails.
"""
import smtplib
import sys

from app.core.config import settings
from app.services.email import deliver, email_enabled


def main() -> int:
    if len(sys.argv) != 2 or "@" not in sys.argv[1]:
        print("Usage: python -m app.send_test_email you@example.com")
        return 2
    if not email_enabled():
        print("Email is off: set SMTP_HOST, SMTP_FROM and (with SMTP_USER) SMTP_PASSWORD.")
        return 1
    print(f"Sending via {settings.smtp_host}:{settings.smtp_port} as {settings.smtp_user or '(no login)'} ...")
    try:
        deliver(sys.argv[1], "Pursely test email", "If you can read this, email is set up correctly.")
    except smtplib.SMTPAuthenticationError:
        print("FAILED: Gmail rejected the login. Use a 16-character App Password (not your normal password), "
              "with 2-Step Verification on, and paste it without spaces.")
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"FAILED: {type(e).__name__}: {e}")
        return 1
    print("Sent. Check the inbox (and spam folder).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
