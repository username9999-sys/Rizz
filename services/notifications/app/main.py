"""
Notification Service - Multi-channel Notification Platform
Supports Email, SMS, Push Notifications, and Webhooks
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from celery import Celery
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
import redis
import json
import os

# Celery configuration
celery_app = Celery(
    'notifications',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    worker_prefetch_multiplier=10,
)

# Redis for caching and rate limiting
redis_client = redis.Redis(
    host='redis',
    port=6379,
    db=2,
    decode_responses=True
)

app = FastAPI(
    title="Rizz Notification Service",
    description="Multi-channel Notification Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== Pydantic Models =====

class EmailNotification(BaseModel):
    to: List[EmailStr]
    subject: str
    body: str
    html: Optional[str] = None
    template: Optional[str] = None
    template_data: Optional[Dict[str, Any]] = None
    priority: str = 'normal'  # low, normal, high, critical


class SMSNotification(BaseModel):
    to: List[str]  # Phone numbers
    body: str
    sender_id: Optional[str] = 'Rizz'


class PushNotification(BaseModel):
    user_ids: List[str]
    title: str
    body: str
    data: Optional[Dict[str, Any]] = None
    badge: Optional[int] = None
    sound: Optional[str] = 'default'
    category: Optional[str] = None


class WebhookNotification(BaseModel):
    url: str
    payload: Dict[str, Any]
    method: str = 'POST'
    headers: Optional[Dict[str, str]] = None
    retry_count: int = 3


class NotificationResponse(BaseModel):
    status: str
    message_id: str
    channel: str
    timestamp: str


# ===== Celery Tasks =====

@celery_app.task(bind=True, max_retries=3)
def send_email_task(self, notification: dict):
    """Send email notification (async)"""
    try:
        # In production: Use SendGrid/SES/Sendmail
        to = notification['to']
        subject = notification['subject']
        body = notification['body']
        
        # Simulate sending
        print(f"Sending email to {to}: {subject}")
        
        # Log to Redis
        redis_client.lpush('notifications:email:sent', json.dumps({
            'to': to,
            'subject': subject,
            'timestamp': datetime.utcnow().isoformat()
        }))
        
        return {'status': 'sent', 'recipients': to}
    except Exception as e:
        raise self.retry(exc=e, countdown=60)


@celery_app.task(bind=True, max_retries=3)
def send_sms_task(self, notification: dict):
    """Send SMS notification (async)"""
    try:
        # In production: Use Twilio/MessageBird
        to = notification['to']
        body = notification['body']
        
        print(f"Sending SMS to {to}: {body[:50]}...")
        
        redis_client.lpush('notifications:sms:sent', json.dumps({
            'to': to,
            'timestamp': datetime.utcnow().isoformat()
        }))
        
        return {'status': 'sent', 'recipients': to}
    except Exception as e:
        raise self.retry(exc=e, countdown=30)


@celery_app.task(bind=True, max_retries=3)
def send_push_task(self, notification: dict):
    """Send push notification (async)"""
    try:
        # In production: Use Firebase Cloud Messaging
        user_ids = notification['user_ids']
        title = notification['title']
        
        print(f"Sending push to {len(user_ids)} users: {title}")
        
        redis_client.lpush('notifications:push:sent', json.dumps({
            'user_ids': user_ids,
            'timestamp': datetime.utcnow().isoformat()
        }))
        
        return {'status': 'sent', 'user_count': len(user_ids)}
    except Exception as e:
        raise self.retry(exc=e, countdown=30)


@celery_app.task(bind=True, max_retries=3)
def send_webhook_task(self, notification: dict):
    """Send webhook notification (async with retries)"""
    try:
        import httpx
        
        url = notification['url']
        payload = notification['payload']
        method = notification.get('method', 'POST')
        headers = notification.get('headers', {'Content-Type': 'application/json'})
        
        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, json=payload, headers=headers)
            response.raise_for_status()
        
        redis_client.lpush('notifications:webhook:sent', json.dumps({
            'url': url,
            'status': response.status_code,
            'timestamp': datetime.utcnow().isoformat()
        }))
        
        return {'status': 'sent', 'status_code': response.status_code}
    except Exception as e:
        raise self.retry(exc=e, countdown=120)


# ===== API Endpoints =====

@app.get('/health')
async def health_check():
    """Health check"""
    return {
        'status': 'healthy',
        'service': 'notifications',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat()
    }


@app.post('/api/notifications/email', response_model=NotificationResponse)
async def send_email(notification: EmailNotification, background_tasks: BackgroundTasks):
    """Send email notification"""
    # Rate limiting check
    rate_key = f'rate:email:{notification.to[0]}'
    current_count = redis_client.get(rate_key) or 0
    
    if int(current_count) > 100:  # 100 emails per hour
        raise HTTPException(status_code=429, detail='Rate limit exceeded')
    
    # Queue email task
    task = send_email_task.delay(notification.dict())
    
    # Update rate limit
    redis_client.incr(rate_key)
    redis_client.expire(rate_key, 3600)
    
    return NotificationResponse(
        status='queued',
        message_id=task.id,
        channel='email',
        timestamp=datetime.utcnow().isoformat()
    )


@app.post('/api/notifications/sms', response_model=NotificationResponse)
async def send_sms(notification: SMSNotification):
    """Send SMS notification"""
    task = send_sms_task.delay(notification.dict())
    
    return NotificationResponse(
        status='queued',
        message_id=task.id,
        channel='sms',
        timestamp=datetime.utcnow().isoformat()
    )


@app.post('/api/notifications/push', response_model=NotificationResponse)
async def send_push(notification: PushNotification):
    """Send push notification"""
    task = send_push_task.delay(notification.dict())
    
    return NotificationResponse(
        status='queued',
        message_id=task.id,
        channel='push',
        timestamp=datetime.utcnow().isoformat()
    )


@app.post('/api/notifications/webhook', response_model=NotificationResponse)
async def send_webhook(notification: WebhookNotification):
    """Send webhook notification"""
    task = send_webhook_task.delay(notification.dict())
    
    return NotificationResponse(
        status='queued',
        message_id=task.id,
        channel='webhook',
        timestamp=datetime.utcnow().isoformat()
    )


@app.post('/api/notifications/broadcast')
async def broadcast_notification(
    channels: List[str] = ['email', 'push'],
    subject: Optional[str] = None,
    body: str = None,
    target_audience: str = 'all'
):
    """Broadcast notification to multiple channels"""
    
    tasks = []
    
    if 'email' in channels and subject:
        email_task = send_email_task.delay({
            'to': ['all@example.com'],  # Would fetch from DB
            'subject': subject,
            'body': body
        })
        tasks.append(email_task.id)
    
    if 'push' in channels:
        push_task = send_push_task.delay({
            'user_ids': ['all'],  # Would fetch from DB
            'title': subject,
            'body': body
        })
        tasks.append(push_task.id)
    
    return {
        'status': 'broadcast_initiated',
        'channels': channels,
        'task_ids': tasks,
        'timestamp': datetime.utcnow().isoformat()
    }


@app.get('/api/notifications/stats')
async def get_notification_stats():
    """Get notification statistics"""
    
    # Get counts from Redis
    email_sent = redis_client.llen('notifications:email:sent')
    sms_sent = redis_client.llen('notifications:sms:sent')
    push_sent = redis_client.llen('notifications:push:sent')
    webhook_sent = redis_client.llen('notifications:webhook:sent')
    
    return {
        'statistics': {
            'email': {'sent': email_sent},
            'sms': {'sent': sms_sent},
            'push': {'sent': push_sent},
            'webhook': {'sent': webhook_sent}
        },
        'timestamp': datetime.utcnow().isoformat()
    }


@app.get('/api/notifications/templates')
async def list_templates():
    """List available notification templates"""
    templates = {
        'welcome_email': {
            'subject': 'Welcome to Rizz Platform!',
            'body': 'Hi {{username}}, welcome to our platform...'
        },
        'password_reset': {
            'subject': 'Password Reset Request',
            'body': 'Click here to reset your password: {{reset_link}}'
        },
        'new_post_notification': {
            'subject': 'New post from {{author}}',
            'body': '{{author}} just published: {{title}}'
        }
    }
    
    return {'templates': templates}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8002)
