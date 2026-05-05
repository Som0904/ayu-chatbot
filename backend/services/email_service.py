import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from config import settings

logger = logging.getLogger(__name__)


def send_email(to_email: str, subject: str, body: str, html_body: str = None) -> bool:
    to_email = (to_email or "").strip()
    if not to_email:
        logger.error("[EMAIL] Missing recipient email")
        return False

    if settings.SMTP_MOCK_MODE:
        logger.info("[EMAIL] MOCK MODE - Email would be sent:")
        logger.info(f"[EMAIL] To: {to_email}")
        logger.info(f"[EMAIL] Subject: {subject}")
        logger.info(f"[EMAIL] Body:\n{body}")
        return True

    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.info("[EMAIL] SMTP not configured. Logging email to console instead.")
        logger.info(f"[EMAIL] To: {to_email}")
        logger.info(f"[EMAIL] Subject: {subject}")
        logger.info(f"[EMAIL] Body:\n{body}")
        return True

    try:
        msg = MIMEMultipart("alternative")
        from_email = (settings.SMTP_FROM_EMAIL or settings.SMTP_USER).strip()
        msg["From"] = formataddr((settings.SMTP_FROM_NAME, from_email))
        msg["To"] = to_email
        msg["Subject"] = subject

        if html_body:
            msg.attach(MIMEText(body, "plain"))
            msg.attach(MIMEText(html_body, "html"))
        else:
            msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"[EMAIL] Sent to {to_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"[EMAIL] Failed to send to {to_email}: {e}")
        logger.info("[EMAIL] Logging to console instead:")
        logger.info(f"[EMAIL] To: {to_email}")
        logger.info(f"[EMAIL] Subject: {subject}")
        logger.info(f"[EMAIL] Body:\n{body}")
        return False


def send_welcome_email(to_email: str, username: str) -> bool:
    subject = "Welcome to Gemini Chatbot!"
    body = f"""
Hello {username},

Welcome to Gemini Chatbot! Your account has been successfully created.

You can now start chatting with our AI assistant and enjoy features like:
- Persistent memory across sessions
- Hospital finder tool
- Reminder notifications
- Personalized responses

Thank you for joining us!

Best regards,
Gemini Chatbot Team
"""
    html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #4A90E2;">Welcome to Gemini Chatbot!</h2>
    <p>Hello <strong>{username}</strong>,</p>
    <p>Welcome to Gemini Chatbot! Your account has been successfully created.</p>
    <p>You can now start chatting with our AI assistant and enjoy features like:</p>
    <ul>
        <li>Persistent memory across sessions</li>
        <li>Hospital finder tool</li>
        <li>Reminder notifications</li>
        <li>Personalized responses</li>
    </ul>
    <p>Thank you for joining us!</p>
    <p style="margin-top: 30px;">Best regards,<br><strong>Gemini Chatbot Team</strong></p>
</body>
</html>
"""
    return send_email(to_email, subject, body, html_body)


def send_notification_email(to_email: str, username: str, notification_message: str) -> bool:
    subject = "Reminder Notification"
    body = f"""
Hello {username},

You have a new notification:

{notification_message}

Best regards,
Gemini Chatbot Team
"""
    html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #4A90E2;">Reminder Notification</h2>
    <p>Hello <strong>{username}</strong>,</p>
    <p>You have a new notification:</p>
    <div style="background-color: #f4f4f4; padding: 15px; border-left: 4px solid #4A90E2; margin: 20px 0;">
        <p style="margin: 0;"><strong>{notification_message}</strong></p>
    </div>
    <p style="margin-top: 30px;">Best regards,<br><strong>Gemini Chatbot Team</strong></p>
</body>
</html>
"""
    return send_email(to_email, subject, body, html_body)


def send_password_reset_email(to_email: str, username: str, reset_token: str) -> bool:
    subject = "Password Reset Request"
    reset_link = f"http://localhost:3000/reset-password?token={reset_token}"
    body = f"""
Hello {username},

You requested a password reset for your account.

Click the link below to reset your password:
{reset_link}

This link will expire in 1 hour.

If you did not request this, please ignore this email.

Best regards,
Gemini Chatbot Team
"""
    html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #4A90E2;">Password Reset Request</h2>
    <p>Hello <strong>{username}</strong>,</p>
    <p>You requested a password reset for your account.</p>
    <p>Click the button below to reset your password:</p>
    <div style="margin: 30px 0;">
        <a href="{reset_link}" style="background-color: #4A90E2; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">Reset Password</a>
    </div>
    <p style="color: #666; font-size: 14px;">This link will expire in 1 hour.</p>
    <p style="color: #666; font-size: 14px;">If you did not request this, please ignore this email.</p>
    <p style="margin-top: 30px;">Best regards,<br><strong>Gemini Chatbot Team</strong></p>
</body>
</html>
"""
    return send_email(to_email, subject, body, html_body)
