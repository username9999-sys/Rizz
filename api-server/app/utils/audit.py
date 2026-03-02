"""
Audit Logging Utility
Track all important actions for security and compliance
"""

from flask import request
from datetime import datetime
from ..models import db, AuditLog


def log_action(user_id, action, entity_type=None, entity_id=None, 
               old_values=None, new_values=None):
    """
    Log an action to the audit trail
    
    Args:
        user_id: ID of the user performing the action
        action: Type of action (e.g., 'USER_LOGIN', 'POST_CREATED')
        entity_type: Type of entity affected (e.g., 'User', 'Post')
        entity_id: ID of the entity affected
        old_values: Previous values (dict)
        new_values: New values (dict)
    """
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_values=old_values,
        new_values=new_values,
        ip_address=request.remote_addr if request else None,
        user_agent=request.headers.get('User-Agent') if request else None
    )
    
    db.session.add(audit_log)
    db.session.commit()
    
    return audit_log


def get_user_audit_history(user_id, limit=100):
    """Get audit history for a specific user"""
    return AuditLog.query.filter_by(user_id=user_id)\
        .order_by(AuditLog.created_at.desc())\
        .limit(limit)\
        .all()


def get_entity_audit_history(entity_type, entity_id, limit=100):
    """Get audit history for a specific entity"""
    return AuditLog.query.filter_by(entity_type=entity_type, entity_id=entity_id)\
        .order_by(AuditLog.created_at.desc())\
        .limit(limit)\
        .all()
