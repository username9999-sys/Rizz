"""
Rizz API Server
A scalable REST API with authentication and database integration
"""

from flask import Flask, request, jsonify, g
from flask_cors import CORS
from functools import wraps
import sqlite3
import hashlib
import os
import jwt
import datetime
from pathlib import Path

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'rizz-secret-key-change-in-production')
app.config['DATABASE'] = Path.home() / '.rizz_api.db'

# Enable CORS
CORS(app)

# ===== Database Functions =====

def get_db():
    """Get database connection for current request"""
    if 'db' not in g:
        g.db = sqlite3.connect(str(app.config['DATABASE']))
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    """Close database connection"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize the database"""
    with app.app_context():
        db = get_db()
        
        # Users table
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Posts table
        db.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                published BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Comments table
        db.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES posts (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Create default user if not exists
        db.execute('''
            INSERT OR IGNORE INTO users (username, email, password_hash)
            VALUES (?, ?, ?)
        ''', ('admin', 'admin@rizz.dev', hashlib.sha256('admin123'.encode()).hexdigest()))
        
        db.commit()

# ===== Authentication =====

def token_required(f):
    """Decorator to require valid JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Get token from header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = data['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token is invalid'}), 401
        
        g.current_user = current_user
        return f(*args, **kwargs)
    
    return decorated

# ===== Auth Routes =====

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    if not all([username, email, password]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    db = get_db()
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    try:
        db.execute(
            'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
            (username, email, password_hash)
        )
        db.commit()
        return jsonify({'message': 'User registered successfully'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Username or email already exists'}), 409

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login and get JWT token"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    username = data.get('username')
    password = data.get('password')
    
    if not all([username, password]):
        return jsonify({'error': 'Missing credentials'}), 400
    
    db = get_db()
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    user = db.execute(
        'SELECT * FROM users WHERE username = ? AND password_hash = ?',
        (username, password_hash)
    ).fetchone()
    
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Generate token
    token = jwt.encode({
        'user_id': user['id'],
        'username': user['username'],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }, app.config['SECRET_KEY'], algorithm='HS256')
    
    return jsonify({
        'message': 'Login successful',
        'token': token,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'email': user['email']
        }
    })

@app.route('/api/auth/me', methods=['GET'])
@token_required
def get_current_user():
    """Get current user info"""
    db = get_db()
    user = db.execute(
        'SELECT id, username, email, created_at FROM users WHERE id = ?',
        (g.current_user,)
    ).fetchone()
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({'user': dict(user)})

# ===== Post Routes =====

@app.route('/api/posts', methods=['GET'])
def get_posts():
    """Get all posts"""
    db = get_db()
    published_only = request.args.get('published', 'false').lower() == 'true'
    
    if published_only:
        posts = db.execute('''
            SELECT p.*, u.username 
            FROM posts p 
            JOIN users u ON p.user_id = u.id 
            WHERE p.published = 1
            ORDER BY p.created_at DESC
        ''').fetchall()
    else:
        posts = db.execute('''
            SELECT p.*, u.username 
            FROM posts p 
            JOIN users u ON p.user_id = u.id 
            ORDER BY p.created_at DESC
        ''').fetchall()
    
    return jsonify({'posts': [dict(post) for post in posts]})

@app.route('/api/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    """Get a single post"""
    db = get_db()
    post = db.execute('''
        SELECT p.*, u.username 
        FROM posts p 
        JOIN users u ON p.user_id = u.id 
        WHERE p.id = ?
    ''', (post_id,)).fetchone()
    
    if not post:
        return jsonify({'error': 'Post not found'}), 404
    
    # Get comments
    comments = db.execute('''
        SELECT c.*, u.username 
        FROM comments c 
        JOIN users u ON c.user_id = u.id 
        WHERE c.post_id = ?
        ORDER BY c.created_at DESC
    ''', (post_id,)).fetchall()
    
    post_dict = dict(post)
    post_dict['comments'] = [dict(c) for c in comments]
    
    return jsonify({'post': post_dict})

@app.route('/api/posts', methods=['POST'])
@token_required
def create_post():
    """Create a new post"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    title = data.get('title')
    content = data.get('content')
    published = data.get('published', False)
    
    if not title or not content:
        return jsonify({'error': 'Title and content are required'}), 400
    
    db = get_db()
    cursor = db.execute(
        'INSERT INTO posts (user_id, title, content, published) VALUES (?, ?, ?, ?)',
        (g.current_user, title, content, published)
    )
    db.commit()
    
    return jsonify({
        'message': 'Post created successfully',
        'post': {
            'id': cursor.lastrowid,
            'title': title,
            'content': content,
            'published': published
        }
    }), 201

@app.route('/api/posts/<int:post_id>', methods=['PUT'])
@token_required
def update_post(post_id):
    """Update a post"""
    db = get_db()
    post = db.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    
    if not post:
        return jsonify({'error': 'Post not found'}), 404
    
    if post['user_id'] != g.current_user:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    title = data.get('title', post['title'])
    content = data.get('content', post['content'])
    published = data.get('published', post['published'])
    
    db.execute(
        'UPDATE posts SET title = ?, content = ?, published = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        (title, content, published, post_id)
    )
    db.commit()
    
    return jsonify({'message': 'Post updated successfully'})

@app.route('/api/posts/<int:post_id>', methods=['DELETE'])
@token_required
def delete_post(post_id):
    """Delete a post"""
    db = get_db()
    post = db.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    
    if not post:
        return jsonify({'error': 'Post not found'}), 404
    
    if post['user_id'] != g.current_user:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Delete comments first
    db.execute('DELETE FROM comments WHERE post_id = ?', (post_id,))
    db.execute('DELETE FROM posts WHERE id = ?', (post_id,))
    db.commit()
    
    return jsonify({'message': 'Post deleted successfully'})

# ===== Comment Routes =====

@app.route('/api/posts/<int:post_id>/comments', methods=['POST'])
@token_required
def create_comment(post_id):
    """Add a comment to a post"""
    db = get_db()
    post = db.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    
    if not post:
        return jsonify({'error': 'Post not found'}), 404
    
    data = request.get_json()
    content = data.get('content')
    
    if not content:
        return jsonify({'error': 'Content is required'}), 400
    
    cursor = db.execute(
        'INSERT INTO comments (post_id, user_id, content) VALUES (?, ?, ?)',
        (post_id, g.current_user, content)
    )
    db.commit()
    
    return jsonify({
        'message': 'Comment added successfully',
        'comment': {
            'id': cursor.lastrowid,
            'content': content
        }
    }), 201

@app.route('/api/comments/<int:comment_id>', methods=['DELETE'])
@token_required
def delete_comment(comment_id):
    """Delete a comment"""
    db = get_db()
    comment = db.execute('SELECT * FROM comments WHERE id = ?', (comment_id,)).fetchone()
    
    if not comment:
        return jsonify({'error': 'Comment not found'}), 404
    
    if comment['user_id'] != g.current_user:
        return jsonify({'error': 'Unauthorized'}), 403
    
    db.execute('DELETE FROM comments WHERE id = ?', (comment_id,))
    db.commit()
    
    return jsonify({'message': 'Comment deleted successfully'})

# ===== Health & Info Routes =====

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.datetime.utcnow().isoformat()
    })

@app.route('/api', methods=['GET'])
def api_info():
    """API information"""
    return jsonify({
        'name': 'Rizz API',
        'version': '1.0.0',
        'author': 'username9999',
        'endpoints': {
            'auth': {
                'POST /api/auth/register': 'Register new user',
                'POST /api/auth/login': 'Login user',
                'GET /api/auth/me': 'Get current user (requires auth)'
            },
            'posts': {
                'GET /api/posts': 'Get all posts',
                'GET /api/posts/<id>': 'Get single post',
                'POST /api/posts': 'Create post (requires auth)',
                'PUT /api/posts/<id>': 'Update post (requires auth)',
                'DELETE /api/posts/<id>': 'Delete post (requires auth)'
            },
            'comments': {
                'POST /api/posts/<id>/comments': 'Add comment (requires auth)',
                'DELETE /api/comments/<id>': 'Delete comment (requires auth)'
            },
            'health': {
                'GET /api/health': 'Health check'
            }
        },
        'default_credentials': {
            'username': 'admin',
            'password': 'admin123'
        }
    })

# ===== Error Handlers =====

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# ===== Main =====

if __name__ == '__main__':
    init_db()
    print("\n🚀 Rizz API Server")
    print("=" * 40)
    print("Starting server on http://localhost:5000")
    print("API docs: http://localhost:5000/api")
    print("=" * 40 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
