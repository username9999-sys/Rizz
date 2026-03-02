#!/usr/bin/env python3
"""
Rizz E-commerce Platform - Enhanced API Server
Features: Products, Cart, Orders, Payments, Inventory, Reviews, Analytics
Author: username9999
"""

from flask import Flask, request, jsonify, g
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from decimal import Decimal
import stripe
import redis
import json
import os
from functools import wraps

# ===== Configuration =====
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 
        'postgresql://user:pass@localhost:5432/ecommerce')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-change-me')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
    STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')
    ITEMS_PER_PAGE = 20
    MAX_CART_ITEMS = 100

# ===== Initialize App =====
app = Flask(__name__)
app.config.from_object(Config)

# ===== Initialize Extensions =====
db = SQLAlchemy(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)
CORS(app)

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per hour"],
    storage_uri=Config.REDIS_URL
)

redis_client = redis.from_url(Config.REDIS_URL)

# ===== Database Models =====

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    addresses = db.relationship('Address', backref='user', lazy=True, cascade='all, delete-orphan')
    orders = db.relationship('Order', backref='user', lazy=True)
    reviews = db.relationship('Review', backref='user', lazy=True)
    cart_items = db.relationship('CartItem', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'created_at': self.created_at.isoformat()
        }


class Address(db.Model):
    __tablename__ = 'addresses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    address_line1 = db.Column(db.String(200), nullable=False)
    address_line2 = db.Column(db.String(200))
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100))
    postal_code = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(100), nullable=False, default='ID')
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'address_line1': self.address_line1,
            'address_line2': self.address_line2,
            'city': self.city,
            'state': self.state,
            'postal_code': self.postal_code,
            'country': self.country,
            'is_default': self.is_default
        }


class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    image_url = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Self-referential relationship for subcategories
    children = db.relationship('Category', backref=db.backref('parent', remote_side=[id]))
    products = db.relationship('Product', backref='category', lazy=True)
    
    def to_dict(self, include_children=False):
        data = {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'image_url': self.image_url,
            'parent_id': self.parent_id
        }
        if include_children:
            data['children'] = [child.to_dict() for child in self.children]
        return data


class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    short_description = db.Column(db.String(500))
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    price = db.Column(db.Numeric(10, 2), nullable=False)
    compare_price = db.Column(db.Numeric(10, 2))
    cost = db.Column(db.Numeric(10, 2))
    sku = db.Column(db.String(50), unique=True)
    barcode = db.Column(db.String(100))
    inventory = db.Column(db.Integer, default=0)
    low_stock_threshold = db.Column(db.Integer, default=10)
    images = db.Column(db.JSON, default=list)
    tags = db.Column(db.JSON, default=list)
    attributes = db.Column(db.JSON, default=dict)
    is_active = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)
    view_count = db.Column(db.Integer, default=0)
    sales_count = db.Column(db.Integer, default=0)
    rating_avg = db.Column(db.Numeric(3, 2), default=0)
    rating_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    reviews = db.relationship('Review', backref='product', lazy=True, cascade='all, delete-orphan')
    cart_items = db.relationship('CartItem', backref='product', lazy=True, cascade='all, delete-orphan')
    order_items = db.relationship('OrderItem', backref='product', lazy=True)
    
    # Indexes
    __table_args__ = (
        db.Index('idx_products_category', 'category_id'),
        db.Index('idx_products_price', 'price'),
        db.Index('idx_products_active', 'is_active'),
    )
    
    def to_dict(self, include_details=False):
        data = {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'short_description': self.short_description,
            'price': float(self.price),
            'compare_price': float(self.compare_price) if self.compare_price else None,
            'inventory': self.inventory,
            'images': self.images,
            'tags': self.tags,
            'rating_avg': float(self.rating_avg) if self.rating_avg else 0,
            'rating_count': self.rating_count,
            'is_active': self.is_active,
            'is_featured': self.is_featured
        }
        if include_details:
            data.update({
                'description': self.description,
                'category': self.category.to_dict() if self.category else None,
                'sku': self.sku,
                'attributes': self.attributes,
                'view_count': self.view_count,
                'sales_count': self.sales_count,
                'created_at': self.created_at.isoformat()
            })
        return data
    
    def is_in_stock(self):
        return self.inventory > 0
    
    def is_low_stock(self):
        return self.inventory <= self.low_stock_threshold


class ProductImage(db.Model):
    __tablename__ = 'product_images'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    alt_text = db.Column(db.String(200))
    position = db.Column(db.Integer, default=0)
    is_primary = db.Column(db.Boolean, default=False)


class CartItem(db.Model):
    __tablename__ = 'cart_items'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'product_id', name='unique_user_product'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'product': self.product.to_dict(),
            'quantity': self.quantity,
            'subtotal': float(self.product.price * self.quantity)
        }


class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='pending', index=True)
    
    # Address snapshot
    shipping_address = db.Column(db.JSON)
    billing_address = db.Column(db.JSON)
    
    # Financial
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    shipping_cost = db.Column(db.Numeric(10, 2), default=0)
    tax = db.Column(db.Numeric(10, 2), default=0)
    discount = db.Column(db.Numeric(10, 2), default=0)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='IDR')
    
    # Payment
    payment_method = db.Column(db.String(50))
    payment_status = db.Column(db.String(20), default='pending')
    payment_intent_id = db.Column(db.String(255))
    
    # Shipping
    shipping_method = db.Column(db.String(100))
    tracking_number = db.Column(db.String(100))
    shipped_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)
    
    # Notes
    customer_notes = db.Column(db.Text)
    internal_notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    
    # Indexes
    __table_args__ = (
        db.Index('idx_orders_user', 'user_id'),
        db.Index('idx_orders_status', 'status'),
        db.Index('idx_orders_created', 'created_at'),
    )
    
    def to_dict(self, include_items=False):
        data = {
            'id': self.id,
            'order_number': self.order_number,
            'status': self.status,
            'total': float(self.total),
            'currency': self.currency,
            'payment_status': self.payment_status,
            'created_at': self.created_at.isoformat()
        }
        if include_items:
            data['items'] = [item.to_dict() for item in self.items]
            data['shipping_address'] = self.shipping_address
            data['billing_address'] = self.billing_address
        return data
    
    def generate_order_number(self):
        """Generate unique order number"""
        date_str = datetime.utcnow().strftime('%Y%m%d')
        last_order = Order.query.filter(
            Order.order_number.like(f'ORD-{date_str}-%')
        ).order_by(Order.id.desc()).first()
        
        if last_order:
            last_num = int(last_order.order_number.split('-')[-1])
            new_num = last_num + 1
        else:
            new_num = 1
        
        return f'ORD-{date_str}-{new_num:04d}'


class OrderItem(db.Model):
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    product_name = db.Column(db.String(200), nullable=False)  # Snapshot
    product_sku = db.Column(db.String(50))  # Snapshot
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)  # Snapshot
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'product_name': self.product_name,
            'product_sku': self.product_sku,
            'quantity': self.quantity,
            'price': float(self.price),
            'subtotal': float(self.subtotal)
        }


class Review(db.Model):
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    is_verified_purchase = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)
    helpful_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('product_id', 'user_id', name='unique_product_user_review'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'rating': self.rating,
            'title': self.title,
            'content': self.content,
            'user': self.user.to_dict() if self.user else None,
            'is_verified_purchase': self.is_verified_purchase,
            'helpful_count': self.helpful_count,
            'created_at': self.created_at.isoformat()
        }


# ===== Helper Functions =====

def generate_slug(text):
    """Generate URL-friendly slug"""
    import re
    slug = text.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug


def calculate_product_rating(product_id):
    """Calculate average rating for a product"""
    result = db.session.query(
        db.func.avg(Review.rating),
        db.func.count(Review.id)
    ).filter(
        Review.product_id == product_id,
        Review.is_approved == True
    ).first()
    
    avg_rating = float(result[0]) if result[0] else 0
    count = result[1] or 0
    
    Product.query.filter_by(id=product_id).update({
        'rating_avg': Decimal(str(avg_rating)).quantize(Decimal('0.01')),
        'rating_count': count
    })
    db.session.commit()


# ===== API Routes =====

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'ecommerce-api',
        'version': '2.0.0',
        'timestamp': datetime.utcnow().isoformat()
    })


@app.route('/api/v1/auth/register', methods=['POST'])
@limiter.limit("5 per minute")
def register():
    """Register new user"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Validate required fields
    required = ['email', 'password', 'first_name', 'last_name']
    for field in required:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    # Check if email exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 409
    
    # Create user
    user = User(
        email=data['email'],
        first_name=data['first_name'],
        last_name=data['last_name'],
        phone=data.get('phone')
    )
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    # Generate JWT token
    from flask_jwt_extended import create_access_token
    access_token = create_access_token(identity=str(user.id))
    
    return jsonify({
        'message': 'Registration successful',
        'user': user.to_dict(),
        'access_token': access_token
    }), 201


@app.route('/api/v1/auth/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    """Login user"""
    data = request.get_json()
    
    if not all(k in data for k in ['email', 'password']):
        return jsonify({'error': 'Email and password required'}), 400
    
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    if not user.is_active:
        return jsonify({'error': 'Account is deactivated'}), 403
    
    from flask_jwt_extended import create_access_token
    access_token = create_access_token(identity=str(user.id))
    
    return jsonify({
        'message': 'Login successful',
        'user': user.to_dict(),
        'access_token': access_token
    })


@app.route('/api/v1/products', methods=['GET'])
def get_products():
    """Get products with filtering, sorting, and pagination"""
    # Query parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', Config.ITEMS_PER_PAGE, type=int)
    category = request.args.get('category')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    search = request.args.get('search')
    sort = request.args.get('sort', 'created_at')
    order = request.args.get('order', 'desc')
    featured = request.args.get('featured', type=bool)
    
    # Base query
    query = Product.query.filter_by(is_active=True)
    
    # Filter by category
    if category:
        cat = Category.query.filter_by(slug=category).first()
        if cat:
            query = query.filter_by(category_id=cat.id)
    
    # Filter by price
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    
    # Search
    if search:
        query = query.filter(
            db.or_(
                Product.name.ilike(f'%{search}%'),
                Product.description.ilike(f'%{search}%'),
                Product.tags.any(search)
            )
        )
    
    # Filter featured
    if featured:
        query = query.filter_by(is_featured=True)
    
    # Sorting
    sort_column = getattr(Product, sort, Product.created_at)
    if order == 'desc':
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    products = pagination.items
    
    return jsonify({
        'products': [p.to_dict() for p in products],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total_pages': pagination.pages,
            'total_items': pagination.total,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    })


@app.route('/api/v1/products/<slug>', methods=['GET'])
def get_product(slug):
    """Get single product by slug"""
    product = Product.query.filter_by(slug=slug).first_or_404()
    
    if not product.is_active:
        return jsonify({'error': 'Product not found'}), 404
    
    # Increment view count
    product.view_count += 1
    db.session.commit()
    
    # Get reviews
    reviews = Review.query.filter_by(
        product_id=product.id,
        is_approved=True
    ).order_by(Review.created_at.desc()).limit(10).all()
    
    return jsonify({
        'product': product.to_dict(include_details=True),
        'reviews': [r.to_dict() for r in reviews],
        'related_products': [
            p.to_dict() for p in Product.query.filter_by(
                category_id=product.category_id,
                is_active=True
            ).filter(Product.id != product.id).limit(4).all()
        ]
    })


@app.route('/api/v1/cart', methods=['GET'])
@jwt_required()
def get_cart():
    """Get user's cart"""
    user_id = int(get_jwt_identity())
    
    cart_items = CartItem.query.filter_by(user_id=user_id).all()
    
    total = sum(item.product.price * item.quantity for item in cart_items)
    
    return jsonify({
        'cart': [item.to_dict() for item in cart_items],
        'total_items': len(cart_items),
        'total_amount': float(total)
    })


@app.route('/api/v1/cart/add', methods=['POST'])
@jwt_required()
def add_to_cart():
    """Add item to cart"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    if not data or 'product_id' not in data:
        return jsonify({'error': 'Product ID required'}), 400
    
    product = Product.query.get(data['product_id'])
    if not product or not product.is_active:
        return jsonify({'error': 'Product not found'}), 404
    
    if not product.is_in_stock():
        return jsonify({'error': 'Product out of stock'}), 400
    
    quantity = data.get('quantity', 1)
    if quantity < 1 or quantity > Config.MAX_CART_ITEMS:
        return jsonify({'error': 'Invalid quantity'}), 400
    
    # Check if item already in cart
    cart_item = CartItem.query.filter_by(
        user_id=user_id,
        product_id=product.id
    ).first()
    
    if cart_item:
        cart_item.quantity += quantity
        cart_item.updated_at = datetime.utcnow()
    else:
        cart_item = CartItem(
            user_id=user_id,
            product_id=product.id,
            quantity=quantity
        )
        db.session.add(cart_item)
    
    db.session.commit()
    
    return jsonify({
        'message': 'Item added to cart',
        'cart_item': cart_item.to_dict()
    })


@app.route('/api/v1/orders', methods=['POST'])
@jwt_required()
def create_order():
    """Create new order"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    # Get cart items
    cart_items = CartItem.query.filter_by(user_id=user_id).all()
    
    if not cart_items:
        return jsonify({'error': 'Cart is empty'}), 400
    
    # Calculate totals
    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    shipping_cost = Decimal('15000')  # Fixed shipping
    tax = subtotal * Decimal('0.11')  # 11% tax
    total = subtotal + shipping_cost + tax
    
    # Create order
    order = Order(
        user_id=user_id,
        status='pending',
        subtotal=subtotal,
        shipping_cost=shipping_cost,
        tax=tax,
        total=total,
        payment_method=data.get('payment_method', 'stripe'),
        shipping_address=data.get('shipping_address'),
        billing_address=data.get('billing_address'),
        customer_notes=data.get('notes')
    )
    order.order_number = order.generate_order_number()
    
    db.session.add(order)
    db.session.flush()  # Get order ID
    
    # Create order items
    for cart_item in cart_items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=cart_item.product_id,
            product_name=cart_item.product.name,
            product_sku=cart_item.product.sku,
            quantity=cart_item.quantity,
            price=cart_item.product.price,
            subtotal=cart_item.product.price * cart_item.quantity
        )
        db.session.add(order_item)
        
        # Update product inventory
        cart_item.product.inventory -= cart_item.quantity
        cart_item.product.sales_count += cart_item.quantity
        
        # Update product rating
        calculate_product_rating(cart_item.product_id)
    
    # Clear cart
    CartItem.query.filter_by(user_id=user_id).delete()
    
    db.session.commit()
    
    # Process payment (Stripe integration)
    if order.payment_method == 'stripe' and Config.STRIPE_SECRET_KEY:
        try:
            stripe.api_key = Config.STRIPE_SECRET_KEY
            
            payment_intent = stripe.PaymentIntent.create(
                amount=int(total * 100),  # Convert to cents
                currency='idr',
                metadata={
                    'order_id': order.id,
                    'order_number': order.order_number
                }
            )
            
            order.payment_intent_id = payment_intent.id
            db.session.commit()
            
            return jsonify({
                'message': 'Order created',
                'order': order.to_dict(),
                'payment': {
                    'client_secret': payment_intent.client_secret,
                    'payment_intent_id': payment_intent.id
                }
            }), 201
        except Exception as e:
            return jsonify({'error': f'Payment failed: {str(e)}'}), 400
    
    return jsonify({
        'message': 'Order created successfully',
        'order': order.to_dict()
    }), 201


@app.route('/api/v1/orders/<int:order_id>', methods=['GET'])
@jwt_required()
def get_order(order_id):
    """Get order details"""
    user_id = int(get_jwt_identity())
    order = Order.query.filter_by(id=order_id, user_id=user_id).first_or_404()
    
    return jsonify({
        'order': order.to_dict(include_items=True)
    })


@app.route('/api/v1/reviews', methods=['POST'])
@jwt_required()
def create_review():
    """Create product review"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    if not all(k in data for k in ['product_id', 'rating']):
        return jsonify({'error': 'Product ID and rating required'}), 400
    
    # Check if user purchased the product
    has_order = OrderItem.query.join(Order).filter(
        Order.user_id == user_id,
        OrderItem.product_id == data['product_id'],
        Order.status == 'completed'
    ).first()
    
    if not has_order:
        return jsonify({'error': 'You can only review purchased products'}), 403
    
    # Check if already reviewed
    existing = Review.query.filter_by(
        product_id=data['product_id'],
        user_id=user_id
    ).first()
    
    if existing:
        return jsonify({'error': 'You already reviewed this product'}), 409
    
    review = Review(
        product_id=data['product_id'],
        user_id=user_id,
        rating=data['rating'],
        title=data.get('title'),
        content=data.get('content'),
        is_verified_purchase=True
    )
    
    db.session.add(review)
    db.session.commit()
    
    # Update product rating
    calculate_product_rating(data['product_id'])
    
    return jsonify({
        'message': 'Review submitted',
        'review': review.to_dict()
    }), 201


# ===== Admin Routes =====

@app.route('/api/v1/admin/products', methods=['POST'])
@jwt_required()
def admin_create_product():
    """Admin: Create new product"""
    # Check admin permission
    from flask_jwt_extended import get_jwt
    claims = get_jwt()
    if not claims.get('is_admin'):
        return jsonify({'error': 'Admin access required'}), 403
    
    data = request.get_json()
    
    product = Product(
        name=data['name'],
        description=data.get('description', ''),
        short_description=data.get('short_description'),
        price=Decimal(str(data['price'])),
        compare_price=Decimal(str(data['compare_price'])) if data.get('compare_price') else None,
        category_id=data.get('category_id'),
        inventory=data.get('inventory', 0),
        sku=data.get('sku'),
        tags=data.get('tags', []),
        attributes=data.get('attributes', {}),
        images=data.get('images', []),
        is_featured=data.get('is_featured', False)
    )
    product.slug = generate_slug(data['name'])
    
    db.session.add(product)
    db.session.commit()
    
    return jsonify({
        'message': 'Product created',
        'product': product.to_dict(include_details=True)
    }), 201


# ===== Error Handlers =====

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500


# ===== Create Tables =====

with app.app_context():
    db.create_all()
    print("✅ Database tables created")


# ===== Run Server =====

if __name__ == '__main__':
    print("""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║   🛒 Rizz E-commerce Platform                            ║
║   Version: 2.0.0 Enhanced                                ║
║                                                          ║
║   Features:                                              ║
║   ✓ Products & Categories                                ║
║   ✓ Shopping Cart                                        ║
║   ✓ Orders & Payments (Stripe)                           ║
║   ✓ Reviews & Ratings                                    ║
║   ✓ Inventory Management                                 ║
║   ✓ Admin Panel                                          ║
║                                                          ║
║   Running on: http://localhost:3020                      ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    app.run(debug=True, host='0.0.0.0', port=3020)
