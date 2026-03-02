"""
Posts Routes - CRUD operations for posts
Enterprise-grade post management with pagination, filtering, and search
"""

from flask import Blueprint, request, jsonify, g, current_app
from sqlalchemy import or_, and_
from ..models import db, Post, Comment, Tag
from ..auth import token_required, optional_token, get_current_user
from ..utils.validators import validate_post_title, validate_post_content
from ..utils.audit import log_action
import re

posts_bp = Blueprint('posts', __name__, url_prefix='/api/posts')


def generate_slug(title):
    """Generate URL-friendly slug from title"""
    slug = title.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug[:200]


@posts_bp.route('', methods=['GET'])
@optional_token
def get_posts():
    """Get all posts with pagination and filtering"""
    # Query parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', current_app.config['POSTS_PER_PAGE'], type=int)
    status = request.args.get('status', 'published')
    tag = request.args.get('tag', None)
    search = request.args.get('search', None)
    sort = request.args.get('sort', 'created_at')
    order = request.args.get('order', 'desc')
    
    # Base query
    query = Post.query
    
    # Filter by status
    if status == 'published':
        query = query.filter(Post.status == 'published')
    elif status == 'all' and hasattr(g, 'current_user_id'):
        # Show all posts for authenticated users (including drafts)
        pass
    elif status in ['draft', 'archived']:
        if not hasattr(g, 'current_user_id'):
            return jsonify({'error': 'Authentication required to view drafts', 'code': 'AUTH_REQUIRED'}), 401
        query = query.filter(and_(Post.status == status, Post.user_id == g.current_user_id))
    
    # Filter by tag
    if tag:
        query = query.join(Post.tags).filter(Tag.name == tag)
    
    # Search
    if search:
        search_term = f'%{search}%'
        query = query.filter(
            or_(
                Post.title.ilike(search_term),
                Post.content.ilike(search_term),
                Post.excerpt.ilike(search_term)
            )
        )
    
    # Sorting
    if sort in ['title', 'created_at', 'updated_at', 'published_at', 'view_count', 'like_count']:
        if order == 'desc':
            query = query.order_by(getattr(Post, sort).desc())
        else:
            query = query.order_by(getattr(Post, sort).asc())
    else:
        query = query.order_by(Post.created_at.desc())
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    posts = pagination.items
    
    # Serialize
    posts_data = [post.to_dict(include_author=True) for post in posts]
    
    return jsonify({
        'posts': posts_data,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total_pages': pagination.pages,
            'total_items': pagination.total,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev,
            'next_page': page + 1 if pagination.has_next else None,
            'prev_page': page - 1 if pagination.has_prev else None
        }
    })


@posts_bp.route('/<int:post_id>', methods=['GET'])
@optional_token
def get_post(post_id):
    """Get a single post by ID"""
    post = Post.query.get_or_404(post_id)
    
    # Check permissions
    if post.status != 'published':
        if not hasattr(g, 'current_user_id') or post.user_id != g.current_user_id:
            return jsonify({'error': 'Post not found', 'code': 'NOT_FOUND'}), 404
    
    # Increment view count
    post.view_count += 1
    db.session.commit()
    
    # Get comments
    comments_query = Comment.query.filter_by(post_id=post_id, is_approved=True)
    comments = [c.to_dict(include_author=True, include_replies=False) for c in comments_query.all()]
    
    post_data = post.to_dict(include_author=True)
    post_data['comments'] = comments
    
    return jsonify({'post': post_data})


@posts_bp.route('/slug/<slug>', methods=['GET'])
@optional_token
def get_post_by_slug(slug):
    """Get a single post by slug"""
    post = Post.query.filter_by(slug=slug).first_or_404()
    
    # Check permissions
    if post.status != 'published':
        if not hasattr(g, 'current_user_id') or post.user_id != g.current_user_id:
            return jsonify({'error': 'Post not found', 'code': 'NOT_FOUND'}), 404
    
    # Increment view count
    post.view_count += 1
    db.session.commit()
    
    return jsonify({'post': post.to_dict(include_author=True)})


@posts_bp.route('', methods=['POST'])
@token_required
def create_post():
    """Create a new post"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided', 'code': 'NO_DATA'}), 400
    
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    excerpt = data.get('excerpt', '').strip()
    tags = data.get('tags', [])
    status = data.get('status', 'draft')
    
    # Validate
    errors = {}
    if not validate_post_title(title):
        errors['title'] = 'Title is required (1-200 characters)'
    if not validate_post_content(content):
        errors['content'] = 'Content is required (min 10 characters)'
    
    if errors:
        return jsonify({'errors': errors, 'code': 'VALIDATION_ERROR'}), 400
    
    # Generate slug
    slug = generate_slug(title)
    counter = 1
    original_slug = slug
    while Post.query.filter_by(slug=slug).first():
        slug = f'{original_slug}-{counter}'
        counter += 1
    
    # Create post
    post = Post(
        title=title,
        content=content,
        excerpt=excerpt or content[:200] + '...',
        slug=slug,
        status=status,
        user_id=g.current_user_id
    )
    
    if status == 'published':
        from datetime import datetime
        post.published_at = datetime.utcnow()
    
    # Add tags
    for tag_name in tags:
        tag = Tag.query.filter_by(name=tag_name).first()
        if not tag:
            tag = Tag(name=tag_name, slug=tag_name.lower().replace(' ', '-'))
            db.session.add(tag)
        post.tags.append(tag)
    
    db.session.add(post)
    db.session.commit()
    
    log_action(g.current_user_id, 'POST_CREATED', 'Post', post.id)
    
    return jsonify({
        'message': 'Post created successfully',
        'post': post.to_dict()
    }), 201


@posts_bp.route('/<int:post_id>', methods=['PUT'])
@token_required
def update_post(post_id):
    """Update a post"""
    post = Post.query.get_or_404(post_id)
    
    # Check ownership
    if post.user_id != g.current_user_id:
        return jsonify({'error': 'Unauthorized', 'code': 'FORBIDDEN'}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided', 'code': 'NO_DATA'}), 400
    
    # Update fields
    if 'title' in data:
        title = data['title'].strip()
        if validate_post_title(title):
            post.title = title
            post.slug = generate_slug(title)
    
    if 'content' in data:
        content = data['content'].strip()
        if validate_post_content(content):
            post.content = content
    
    if 'excerpt' in data:
        post.excerpt = data['excerpt'].strip()
    
    if 'status' in data:
        post.status = data['status']
        if post.status == 'published' and not post.published_at:
            from datetime import datetime
            post.published_at = datetime.utcnow()
    
    if 'tags' in data:
        # Clear existing tags
        post.tags = []
        # Add new tags
        for tag_name in data['tags']:
            tag = Tag.query.filter_by(name=tag_name).first()
            if not tag:
                tag = Tag(name=tag_name, slug=tag_name.lower().replace(' ', '-'))
                db.session.add(tag)
            post.tags.append(tag)
    
    db.session.commit()
    
    log_action(g.current_user_id, 'POST_UPDATED', 'Post', post_id)
    
    return jsonify({
        'message': 'Post updated successfully',
        'post': post.to_dict()
    })


@posts_bp.route('/<int:post_id>', methods=['DELETE'])
@token_required
def delete_post(post_id):
    """Delete a post"""
    post = Post.query.get_or_404(post_id)
    
    # Check ownership
    if post.user_id != g.current_user_id:
        return jsonify({'error': 'Unauthorized', 'code': 'FORBIDDEN'}), 403
    
    # Delete comments first (cascade should handle this, but being explicit)
    Comment.query.filter_by(post_id=post_id).delete()
    
    db.session.delete(post)
    db.session.commit()
    
    log_action(g.current_user_id, 'POST_DELETED', 'Post', post_id)
    
    return jsonify({'message': 'Post deleted successfully'})


@posts_bp.route('/<int:post_id>/like', methods=['POST'])
@token_required
def like_post(post_id):
    """Like a post"""
    post = Post.query.get_or_404(post_id)
    post.like_count += 1
    db.session.commit()
    
    return jsonify({'message': 'Post liked', 'like_count': post.like_count})


@posts_bp.route('/<int:post_id>/comments', methods=['POST'])
@token_required
def create_comment(post_id):
    """Add a comment to a post"""
    post = Post.query.get_or_404(post_id)
    data = request.get_json()
    
    if not data or 'content' not in data:
        return jsonify({'error': 'Content is required', 'code': 'MISSING_CONTENT'}), 400
    
    content = data['content'].strip()
    if len(content) < 1:
        return jsonify({'error': 'Content cannot be empty', 'code': 'EMPTY_CONTENT'}), 400
    
    parent_id = data.get('parent_id', None)
    
    # If replying to a comment, verify parent exists
    if parent_id:
        parent_comment = Comment.query.get(parent_id)
        if not parent_comment or parent_comment.post_id != post_id:
            return jsonify({'error': 'Parent comment not found', 'code': 'PARENT_NOT_FOUND'}), 404
    
    comment = Comment(
        content=content,
        post_id=post_id,
        user_id=g.current_user_id,
        parent_id=parent_id,
        is_approved=True  # Could be False if moderation is enabled
    )
    
    db.session.add(comment)
    
    # Update comment count
    post.comment_count += 1
    db.session.commit()
    
    log_action(g.current_user_id, 'COMMENT_CREATED', 'Comment', comment.id)
    
    return jsonify({
        'message': 'Comment added successfully',
        'comment': comment.to_dict(include_author=True)
    }), 201
