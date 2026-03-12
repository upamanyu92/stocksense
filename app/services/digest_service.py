import os
import smtplib
import logging
from email.message import EmailMessage
from typing import List
from app.db.services.alert_service import list_notifications

SMTP_HOST = os.environ.get('SMTP_HOST')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587)) if os.environ.get('SMTP_PORT') else None
SMTP_USER = os.environ.get('SMTP_USER')
SMTP_PASS = os.environ.get('SMTP_PASS')
FROM_EMAIL = os.environ.get('FROM_EMAIL', 'noreply@stocksense.local')


def send_daily_digest(to_emails: List[str], subject: str, body: str) -> bool:
    """Send a daily digest email to a list of recipients. If SMTP not configured, just log."""
    if not SMTP_HOST or not SMTP_PORT:
        logging.warning('SMTP not configured; logging digest instead')
        logging.info(f'Digest to {to_emails}: {subject}\n{body}')
        return True

    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = FROM_EMAIL
        msg['To'] = ', '.join(to_emails)
        msg.set_content(body)

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            if SMTP_USER and SMTP_PASS:
                server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        logging.error(f'Failed to send digest email: {e}')
        return False


def build_daily_brief():
    # Create a simple brief from recent notifications
    notifs = list_notifications(0)[:10]
    lines = [f"{n['created_at']} - {n['symbol']} - {n['message']}" for n in notifs]
    return '\n'.join(lines)
