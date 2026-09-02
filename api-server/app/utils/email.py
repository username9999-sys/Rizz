# Email utility module
"""
Simple email sending utility used by the Rizz API server.
In production you would configure an SMTP server via environment variables.
For the purpose of this project the function logs the email content and returns True.
"""
import os
import logging

logger = logging.getLogger(__name__)

def send_email(to_address: str, subject: str, body: str) -> bool:
    """Send an email.

    In a real deployment this would use an SMTP server (e.g., via smtplib or a
    third‑party service). Here we simply log the email for visibility and return
    ``True`` to indicate success.
    """
    # Fetch SMTP configuration – placeholder values
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")

    # Log the email – useful for debugging and CI runs
    logger.info(
        "Sending email to %s – subject: %s – body: %s – smtp: %s:%s (user=%s)",
        to_address,
        subject,
        body,
        smtp_host,
        smtp_port,
        smtp_user,
    )
    # In a real implementation you would send via smtplib here.
    return True
