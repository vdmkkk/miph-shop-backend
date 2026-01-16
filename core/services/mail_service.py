from __future__ import annotations

import smtplib
from email.message import EmailMessage

from core.config import settings


def send_magic_link(email: str, token: str) -> None:
    link = f"{settings.frontend_base_url}/auth/finish?token={token}"
    if settings.mail_mode == "console":
        print(f"[MAIL] Magic link for {email}: {link}")
        return

    message = EmailMessage()
    message["Subject"] = "Your login link"
    message["From"] = settings.smtp_user or "no-reply@example.com"
    message["To"] = email
    message.set_content(f"Click to sign in: {link}")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        if settings.smtp_user and settings.smtp_password:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(message)
