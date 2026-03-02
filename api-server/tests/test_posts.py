"""
Test Suite - Posts API
Enterprise-grade testing for post operations
"""

import pytest
import json
from app import create_app
from app.models import db, User, Role, Post, Tag


@pytest.fixture
def app():
    """Create application for testing"""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        
        # Create default role and user
        user_role = Role(name='user', description='Regular user', permissions=['read:posts'])
        db.session.add(user_role)
        
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        user.roles.append(user_role)
        db.session.add(user)
        db.session.commit()
        
        yield app
        
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """Create client with authentication"""
    response = client.post('/api/auth/login', json={
        'username': 'testuser',
        'password': 'password123'
    })
    
    token = response.get_json()['tokens']['access_token']
    client.environ_base['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    
    return client


@pytest.fixture
def sample_post(app, auth_client):
    """Create a sample post"""
    post_data = {
        'title': 'Test Post',
        'content': 'This is test content for the post.',
        'tags': ['test', 'python']
    }
    
    response = auth_client.post('/api/posts', json=post_data)
    return response.get_json()['post']


class TestPosts:
    """Posts API tests"""
    
    def test_create_post(self, auth_client):
        """Test creating a new post"""
        response = auth_client.post('/api/posts', json={
            'title': 'New Post',
            'content': 'This is the content of the new post.',
            'tags': ['test', 'new']
        })
        
        assert response.status_code == 201
        data = response.get_json()
        assert 'post' in data
        assert data['post']['title'] == 'New Post'
        assert 'slug' in data['post']
    
    def test_create_post_missing_title(self, auth_client):
        """Test creating post without title"""
        response = auth_client.post('/api/posts', json={
            'content': 'Content without title'
        })
        
        assert response.status_code == 400
    
    def test_create_post_missing_content(self, auth_client):
        """Test creating post without content"""
        response = auth_client.post('/api/posts', json={
            'title': 'Title only'
        })
        
        assert response.status_code == 400
    
    def test_get_posts(self, client, sample_post):
        """Test getting all posts"""
        response = client.get('/api/posts')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'posts' in data
        assert len(data['posts']) >= 1
        assert 'pagination' in data
    
    def test_get_posts_pagination(self, client, app, auth_client):
        """Test posts pagination"""
        # Create multiple posts
        for i in range(25):
            auth_client.post('/api/posts', json={
                'title': f'Post {i}',
                'content': f'Content for post {i}'
            })
        
        response = client.get('/api/posts?page=1&per_page=10')
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['posts']) == 10
        assert data['pagination']['total_items'] == 26  # 25 + sample
        assert data['pagination']['has_next'] == True
    
    def test_get_single_post(self, client, sample_post):
        """Test getting a single post"""
        response = client.get(f"/api/posts/{sample_post['id']}")
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'post' in data
        assert data['post']['id'] == sample_post['id']
    
    def test_get_post_not_found(self, client):
        """Test getting non-existent post"""
        response = client.get('/api/posts/99999')
        
        assert response.status_code == 404
    
    def test_update_post(self, auth_client, sample_post):
        """Test updating a post"""
        response = auth_client.put(f"/api/posts/{sample_post['id']}", json={
            'title': 'Updated Title',
            'content': 'Updated content'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['post']['title'] == 'Updated Title'
    
    def test_update_post_unauthorized(self, auth_client, app):
        """Test updating another user's post"""
        # Create another user
        user2 = User(username='user2', email='user2@example.com')
        user2.set_password('password123')
        db.session.add(user2)
        db.session.commit()
        
        # Create post by user2
        post = Post(title='User2 Post', content='Content', user_id=user2.id)
        db.session.add(post)
        db.session.commit()
        
        # Try to update with auth_client (testuser)
        response = auth_client.put(f'/api/posts/{post.id}', json={
            'title': 'Hacked Title'
        })
        
        assert response.status_code == 403
    
    def test_delete_post(self, auth_client, sample_post):
        """Test deleting a post"""
        response = auth_client.delete(f"/api/posts/{sample_post['id']}")
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data
        
        # Verify deleted
        get_response = auth_client.get(f"/api/posts/{sample_post['id']}")
        assert get_response.status_code == 404
    
    def test_search_posts(self, client, app, auth_client):
        """Test searching posts"""
        # Create posts with different content
        auth_client.post('/api/posts', json={
            'title': 'Python Tutorial',
            'content': 'Learn Python programming'
        })
        
        auth_client.post('/api/posts', json={
            'title': 'JavaScript Guide',
            'content': 'Learn JavaScript programming'
        })
        
        response = client.get('/api/posts?search=Python')
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['posts']) == 1
        assert 'Python' in data['posts'][0]['title']
    
    def test_filter_posts_by_status(self, auth_client):
        """Test filtering posts by status"""
        # Create draft post
        auth_client.post('/api/posts', json={
            'title': 'Draft Post',
            'content': 'This is a draft',
            'status': 'draft'
        })
        
        # Create published post
        auth_client.post('/api/posts', json={
            'title': 'Published Post',
            'content': 'This is published',
            'status': 'published'
        })
        
        # Get only published
        response = auth_client.get('/api/posts?status=published')
        data = response.get_json()
        
        assert response.status_code == 200
        # Should only see published posts
        for post in data['posts']:
            assert post['status'] == 'published'
    
    def test_create_comment(self, auth_client, sample_post):
        """Test adding a comment to a post"""
        response = auth_client.post(f"/api/posts/{sample_post['id']}/comments", json={
            'content': 'Great post!'
        })
        
        assert response.status_code == 201
        data = response.get_json()
        assert 'comment' in data
        assert data['comment']['content'] == 'Great post!'
    
    def test_like_post(self, auth_client, sample_post):
        """Test liking a post"""
        response = auth_client.post(f"/api/posts/{sample_post['id']}/like")
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'like_count' in data
        assert data['like_count'] >= 1


class TestPostPermissions:
    """Post permission tests"""
    
    def test_unauthenticated_create_post(self, client):
        """Test creating post without authentication"""
        response = client.post('/api/posts', json={
            'title': 'Unauthorized Post',
            'content': 'This should fail'
        })
        
        assert response.status_code == 401
    
    def test_unauthenticated_delete_post(self, client, sample_post):
        """Test deleting post without authentication"""
        response = client.delete(f"/api/posts/{sample_post['id']}")
        
        assert response.status_code == 401
