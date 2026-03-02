"""
Database Models
User, Task, and other core models
"""

from datetime import datetime
import bcrypt


class User:
    """User model"""

    def __init__(self, username, email, password, id=None):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt(rounds=12)
        ).decode('utf-8')
        self.created_at = datetime.utcnow()
        self.verified = False

    @staticmethod
    def verify_password(password, password_hash):
        """Verify password against hash"""
        return bcrypt.checkpw(
            password.encode('utf-8'),
            password_hash.encode('utf-8')
        )

    def to_dict(self):
        """Convert to dictionary (exclude password)"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat(),
            'verified': self.verified
        }


class Task:
    """Task model"""

    def __init__(self, title, description='', priority='medium',
                 category='general', user_id=None, id=None):
        self.id = id
        self.title = title
        self.description = description
        self.priority = priority
        self.category = category
        self.user_id = user_id
        self.status = 'pending'
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.completed_at = None

    def complete(self):
        """Mark task as completed"""
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'priority': self.priority,
            'category': self.category,
            'status': self.status,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


class Post:
    """Blog post model"""

    def __init__(self, title, content, author_id, slug=None, id=None):
        self.id = id
        self.title = title
        self.slug = slug or title.lower().replace(' ', '-').replace(',', '')
        self.content = content
        self.author_id = author_id
        self.published = False
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.views = 0

    def publish(self):
        """Publish the post"""
        self.published = True
        self.updated_at = datetime.utcnow()

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'content': self.content,
            'author_id': self.author_id,
            'published': self.published,
            'views': self.views,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
