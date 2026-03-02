"""
Audit Logging Module
Log security events and user actions
"""

import logging
from datetime import datetime
from pathlib import Path


class AuditLogger:
    """Security audit logger"""

    def __init__(self, log_file='logs/audit.log'):
        """Initialize audit logger"""
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger('audit')
        self.logger.setLevel(logging.INFO)

        # File handler
        handler = logging.FileHandler(log_file)
        handler.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)

        self.logger.addHandler(handler)

    def log_login(self, username, success, ip_address=None, user_agent=None):
        """Log login attempt"""
        status = 'SUCCESS' if success else 'FAILED'
        message = f"LOGIN {status} - username: {username}"
        if ip_address:
            message += f", ip: {ip_address}"
        if user_agent:
            message += f", ua: {user_agent}"

        self.logger.info(message)

    def log_registration(self, username, email, ip_address=None):
        """Log registration attempt"""
        message = f"REGISTRATION - username: {username}, email: {email}"
        if ip_address:
            message += f", ip: {ip_address}"

        self.logger.info(message)

    def log_logout(self, username, ip_address=None):
        """Log logout"""
        message = f"LOGOUT - username: {username}"
        if ip_address:
            message += f", ip: {ip_address}"

        self.logger.info(message)

    def log_password_change(self, username, success):
        """Log password change attempt"""
        status = 'SUCCESS' if success else 'FAILED'
        self.logger.info(f"PASSWORD_CHANGE {status} - username: {username}")

    def log_token_refresh(self, username, success):
        """Log token refresh attempt"""
        status = 'SUCCESS' if success else 'FAILED'
        self.logger.info(f"TOKEN_REFRESH {status} - username: {username}")

    def log_failed_auth(self, username, reason, ip_address=None):
        """Log failed authentication"""
        message = f"FAILED_AUTH - username: {username}, reason: {reason}"
        if ip_address:
            message += f", ip: {ip_address}"

        self.logger.warning(message)

    def log_suspicious_activity(self, activity_type, details):
        """Log suspicious activity"""
        message = f"SUSPICIOUS - type: {activity_type}, details: {details}"
        self.logger.warning(message)

    def log_data_access(self, username, resource, action):
        """Log data access"""
        message = f"DATA_ACCESS - user: {username}, resource: {resource}, action: {action}"
        self.logger.info(message)

    def log_admin_action(self, username, action, target=None):
        """Log admin action"""
        message = f"ADMIN_ACTION - user: {username}, action: {action}"
        if target:
            message += f", target: {target}"

        self.logger.info(message)


# Global audit logger instance
audit_logger = AuditLogger()


def get_audit_logger():
    """Get audit logger instance"""
    return audit_logger
