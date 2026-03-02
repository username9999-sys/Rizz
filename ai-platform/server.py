#!/usr/bin/env python3
"""
Rizz AI Platform - ULTIMATE Enhanced
Features: ML Models, NLP, Computer Vision, Recommendations,
          AutoML, Model Serving, A/B Testing, Monitoring
Author: username9999
Version: 4.0.0 LEGENDARY
"""

from flask import Flask, request, jsonify, g, send_file
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from decimal import Decimal
import tensorflow as tf
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from PIL import Image
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import numpy as np
import pandas as pd
import scikit-learn as sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import redis
import pymongo
import cv2
import base64
import io
import os
import json
import uuid
import hashlib
from functools import lru_cache
import aiohttp
import asyncio

# ===== Configuration =====
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'ai-platform-secret-ultimate')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 
        'postgresql://user:pass@localhost:5432/rizz-ai-ultimate')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-ai')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017/rizz-ai')
    MODEL_PATH = os.environ.get('MODEL_PATH', './models')
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    GPU_ENABLED = os.environ.get('GPU_ENABLED', 'false').lower() == 'true'
    BATCH_SIZE = int(os.environ.get('BATCH_SIZE', '32'))
    RATE_LIMIT = os.environ.get('RATE_LIMIT', '100 per hour')

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
    default_limits=[Config.RATE_LIMIT],
    storage_uri=Config.REDIS_URL
)

redis_client = redis.from_url(Config.REDIS_URL)
mongo_client = pymongo.MongoClient(Config.MONGO_URL)
mongo_db = mongo_client['rizz-ai']

# ===== Device Configuration =====
if Config.GPU_ENABLED and torch.cuda.is_available():
    device = torch.device('cuda')
    print(f"✅ GPU Enabled: {torch.cuda.get_device_name(0)}")
else:
    device = torch.device('cpu')
    print("ℹ️  Using CPU")

# ===== Database Models =====

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_premium = db.Column(db.Boolean, default=False)
    api_calls = db.Column(db.Integer, default=0)
    api_quota = db.Column(db.Integer, default=1000)  # per day
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_premium': self.is_premium,
            'api_calls': self.api_calls,
            'api_quota': self.api_quota
        }


class MLModel(db.Model):
    __tablename__ = 'ml_models'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    type = db.Column(db.String(50))  # classification, detection, nlp, etc.
    framework = db.Column(db.String(50))  # tensorflow, pytorch, sklearn
    version = db.Column(db.String(20), default='1.0.0')
    path = db.Column(db.String(500))
    accuracy = db.Column(db.Float)
    size = db.Column(db.BigInteger)  # bytes
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    is_public = db.Column(db.Boolean, default=False)
    download_count = db.Column(db.Integer, default=0)
    inference_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    owner = db.relationship('User', backref=db.backref('models', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'type': self.type,
            'framework': self.framework,
            'version': self.version,
            'accuracy': self.accuracy,
            'size': self.size,
            'is_public': self.is_public,
            'download_count': self.download_count,
            'inference_count': self.inference_count
        }


class InferenceLog(db.Model):
    __tablename__ = 'inference_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    model_id = db.Column(db.Integer, db.ForeignKey('ml_models.id'))
    input_data = db.Column(db.Text)  # JSON
    output_data = db.Column(db.Text)  # JSON
    confidence = db.Column(db.Float)
    latency_ms = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('inferences', lazy=True))
    model = db.relationship('MLModel', backref=db.backref('inferences', lazy=True))


class Dataset(db.Model):
    __tablename__ = 'datasets'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    path = db.Column(db.String(500))
    size = db.Column(db.BigInteger)
    sample_count = db.Column(db.Integer)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    is_public = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    owner = db.relationship('User', backref=db.backref('datasets', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'size': self.size,
            'sample_count': self.sample_count,
            'is_public': self.is_public
        }


# ===== ML Model Classes =====

class ImageClassifier(nn.Module):
    """Custom Image Classification Model"""
    def __init__(self, num_classes=1000):
        super(ImageClassifier, self).__init__()
        self.backbone = torch.hub.load('pytorch/vision:v0.10.0', 'resnet50', pretrained=True)
        self.backbone.fc = nn.Linear(self.backbone.fc.in_features, num_classes)
    
    def forward(self, x):
        return self.backbone(x)


class TextAnalyzer:
    """NLP Text Analysis Pipeline"""
    def __init__(self):
        self.device = 0 if Config.GPU_ENABLED and torch.cuda.is_available() else -1
        
        # Load pre-trained models
        try:
            self.sentiment_pipeline = pipeline(
                'sentiment-analysis',
                model='distilbert-base-uncased-finetuned-sst-2-english',
                device=self.device
            )
            self.ner_pipeline = pipeline(
                'ner',
                model='dslim/bert-base-NER',
                device=self.device
            )
            self.summarization_pipeline = pipeline(
                'summarization',
                model='facebook/bart-large-cnn',
                device=self.device
            )
            print("✅ NLP models loaded")
        except Exception as e:
            print(f"⚠️  NLP models failed to load: {e}")
            self.sentiment_pipeline = None
            self.ner_pipeline = None
            self.summarization_pipeline = None
    
    def analyze_sentiment(self, text):
        if not self.sentiment_pipeline:
            return {'error': 'Model not loaded'}
        
        result = self.sentiment_pipeline(text[:512])[0]
        return {
            'sentiment': result['label'],
            'confidence': float(result['score'])
        }
    
    def extract_entities(self, text):
        if not self.ner_pipeline:
            return {'error': 'Model not loaded'}
        
        result = self.ner_pipeline(text[:512])
        entities = []
        for entity in result:
            entities.append({
                'text': entity['word'],
                'type': entity['entity'],
                'confidence': float(entity['score'])
            })
        return {'entities': entities}
    
    def summarize(self, text, max_length=130, min_length=30):
        if not self.summarization_pipeline:
            return {'error': 'Model not loaded'}
        
        result = self.summarization_pipeline(
            text[:1024],
            max_length=max_length,
            min_length=min_length,
            do_sample=False
        )[0]
        return {'summary': result['summary_text']}


class ImageProcessor:
    """Computer Vision Processing"""
    def __init__(self):
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                               std=[0.229, 0.224, 0.225])
        ])
        
        # Load ImageNet classes
        try:
            with open('imagenet_classes.json', 'r') as f:
                self.imagenet_classes = json.load(f)
        except:
            self.imagenet_classes = list(range(1000))
        
        print("✅ Image processor initialized")
    
    def classify_image(self, image_path):
        try:
            # Load and preprocess image
            image = Image.open(image_path).convert('RGB')
            input_tensor = self.transform(image).unsqueeze(0).to(device)
            
            # Load pre-trained model
            model = torch.hub.load('pytorch/vision:v0.10.0', 'resnet50', pretrained=True)
            model.to(device)
            model.eval()
            
            # Inference
            with torch.no_grad():
                output = model(input_tensor)
            
            # Get predictions
            _, predicted = torch.max(output, 1)
            probabilities = torch.nn.functional.softmax(output[0], dim=0)
            
            # Get top 5 predictions
            top5_prob, top5_idx = torch.topk(probabilities, 5)
            
            results = []
            for i in range(5):
                results.append({
                    'class': self.imagenet_classes[top5_idx[i].item()],
                    'confidence': float(top5_prob[i].item()),
                    'index': top5_idx[i].item()
                })
            
            return {'predictions': results}
        except Exception as e:
            return {'error': str(e)}
    
    def detect_objects(self, image_path):
        """Object Detection using pre-trained model"""
        try:
            # Load image
            image = cv2.imread(image_path)
            
            # Load pre-trained YOLO model
            net = cv2.dnn.readNet('yolov3.weights', 'yolov3.cfg')
            layer_names = net.getLayerNames()
            output_layers = [layer_names[i[0] - 1] for i in net.getUnconnectedOutLayers()]
            
            # Detect objects
            blob = cv2.dnn.blobFromImage(image, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
            net.setInput(blob)
            outs = net.forward(output_layers)
            
            # Process detections
            detections = []
            for out in outs:
                for detection in out:
                    scores = detection[5:]
                    class_id = np.argmax(scores)
                    confidence = scores[class_id]
                    if confidence > 0.5:
                        detections.append({
                            'class_id': int(class_id),
                            'confidence': float(confidence)
                        })
            
            return {'detections': detections}
        except Exception as e:
            return {'error': str(e)}


class RecommendationEngine:
    """Collaborative Filtering Recommendation System"""
    def __init__(self):
        self.user_item_matrix = None
        self.user_similarity = None
        self.item_similarity = None
    
    def train(self, ratings_data):
        """Train on user-item ratings"""
        # Create user-item matrix
        self.user_item_matrix = pd.DataFrame(ratings_data)
        
        # Calculate user similarity
        self.user_similarity = cosine_similarity(self.user_item_matrix)
        
        # Calculate item similarity
        self.item_similarity = cosine_similarity(self.user_item_matrix.T)
        
        print(f"✅ Trained on {self.user_item_matrix.shape[0]} users, "
              f"{self.user_item_matrix.shape[1]} items")
    
    def recommend_for_user(self, user_id, n_recommendations=10):
        """Get recommendations for a user"""
        if self.user_item_matrix is None:
            return {'error': 'Model not trained'}
        
        user_idx = user_id % self.user_item_matrix.shape[0]
        user_ratings = self.user_item_matrix.iloc[user_idx]
        
        # Predict ratings for unrated items
        predictions = np.dot(self.user_similarity[user_idx], self.user_item_matrix) / \
                     np.sum(np.abs(self.user_similarity[user_idx]))
        
        # Get top N recommendations
        unrated_items = user_ratings[user_ratings == 0].index
        recommendations = []
        
        for item_idx in unrated_items:
            recommendations.append({
                'item_id': item_idx,
                'predicted_rating': float(predictions[item_idx])
            })
        
        recommendations.sort(key=lambda x: x['predicted_rating'], reverse=True)
        return {'recommendations': recommendations[:n_recommendations]}


# Initialize ML services
text_analyzer = TextAnalyzer()
image_processor = ImageProcessor()
recommendation_engine = RecommendationEngine()

# ===== Helper Functions =====

def authenticate_token():
    """Manual token authentication"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header.split(' ')[1]
    try:
        payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=['HS256'])
        return payload['sub']
    except:
        return None


def log_inference(user_id, model_id, input_data, output_data, confidence, latency):
    """Log inference for analytics"""
    try:
        log = InferenceLog(
            user_id=user_id,
            model_id=model_id,
            input_data=json.dumps(input_data),
            output_data=json.dumps(output_data),
            confidence=confidence,
            latency_ms=latency
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Logging error: {e}")


# ===== API Routes =====

@app.route('/health')
def health():
    """Health check with model status"""
    return jsonify({
        'status': 'healthy',
        'service': 'ai-platform-ultimate',
        'version': '4.0.0',
        'timestamp': datetime.utcnow().isoformat(),
        'models': {
            'nlp': text_analyzer.sentiment_pipeline is not None,
            'vision': image_processor is not None,
            'recommendation': recommendation_engine.user_item_matrix is not None
        },
        'device': str(device),
        'gpu_available': torch.cuda.is_available() if Config.GPU_ENABLED else False
    })


@app.route('/api/v2/auth/register', methods=['POST'])
@limiter.limit("5 per minute")
def register():
    """Register new user"""
    data = request.get_json()
    
    if not all(k in data for k in ['username', 'email', 'password']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 409
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 409
    
    user = User(
        username=data['username'],
        email=data['email'],
        is_premium=data.get('is_premium', False),
        api_quota=data.get('api_quota', 1000)
    )
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    access_token = jwt.create_access_token(identity=str(user.id))
    
    return jsonify({
        'message': 'Registration successful',
        'user': user.to_dict(),
        'access_token': access_token
    }), 201


@app.route('/api/v2/auth/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    """Login user"""
    data = request.get_json()
    
    user = User.query.filter_by(username=data.get('username')).first()
    
    if not user or not user.check_password(data.get('password', '')):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    if not user.is_active:
        return jsonify({'error': 'Account is deactivated'}), 403
    
    access_token = jwt.create_access_token(identity=str(user.id))
    
    return jsonify({
        'message': 'Login successful',
        'user': user.to_dict(),
        'access_token': access_token
    })


@app.route('/api/v2/nlp/sentiment', methods=['POST'])
@jwt_required()
@limiter.limit("60 per minute")
def analyze_sentiment():
    """Analyze text sentiment"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    if user.api_calls >= user.api_quota:
        return jsonify({'error': 'API quota exceeded'}), 429
    
    data = request.get_json()
    text = data.get('text', '')
    
    if not text:
        return jsonify({'error': 'Text required'}), 400
    
    start_time = datetime.utcnow()
    result = text_analyzer.analyze_sentiment(text)
    latency = (datetime.utcnow() - start_time).total_seconds() * 1000
    
    # Update API calls
    user.api_calls += 1
    db.session.commit()
    
    # Cache result
    cache_key = f"sentiment:{hashlib.md5(text.encode()).hexdigest()}"
    redis_client.setex(cache_key, 3600, json.dumps(result))
    
    return jsonify({
        'result': result,
        'latency_ms': latency,
        'cached': False
    })


@app.route('/api/v2/nlp/entities', methods=['POST'])
@jwt_required()
@limiter.limit("60 per minute")
def extract_entities():
    """Extract named entities from text"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    if user.api_calls >= user.api_quota:
        return jsonify({'error': 'API quota exceeded'}), 429
    
    data = request.get_json()
    text = data.get('text', '')
    
    result = text_analyzer.extract_entities(text)
    
    user.api_calls += 1
    db.session.commit()
    
    return jsonify({'result': result})


@app.route('/api/v2/nlp/summarize', methods=['POST'])
@jwt_required()
@limiter.limit("20 per minute")
def summarize_text():
    """Summarize long text"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    if user.api_calls >= user.api_quota:
        return jsonify({'error': 'API quota exceeded'}), 429
    
    data = request.get_json()
    text = data.get('text', '')
    max_length = data.get('max_length', 130)
    min_length = data.get('min_length', 30)
    
    result = text_analyzer.summarize(text, max_length, min_length)
    
    user.api_calls += 1
    db.session.commit()
    
    return jsonify({'result': result})


@app.route('/api/v2/vision/classify', methods=['POST'])
@jwt_required()
@limiter.limit("30 per minute")
def classify_image():
    """Classify image content"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    if user.api_calls >= user.api_quota:
        return jsonify({'error': 'API quota exceeded'}), 429
    
    if 'image' not in request.files:
        return jsonify({'error': 'Image file required'}), 400
    
    file = request.files['image']
    
    # Save temporarily
    temp_path = f"/tmp/{uuid.uuid4()}.jpg"
    file.save(temp_path)
    
    start_time = datetime.utcnow()
    result = image_processor.classify_image(temp_path)
    latency = (datetime.utcnow() - start_time).total_seconds() * 1000
    
    # Clean up
    os.remove(temp_path)
    
    user.api_calls += 1
    db.session.commit()
    
    return jsonify({
        'result': result,
        'latency_ms': latency
    })


@app.route('/api/v2/vision/detect', methods=['POST'])
@jwt_required()
@limiter.limit("30 per minute")
def detect_objects():
    """Detect objects in image"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    if user.api_calls >= user.api_quota:
        return jsonify({'error': 'API quota exceeded'}), 429
    
    if 'image' not in request.files:
        return jsonify({'error': 'Image file required'}), 400
    
    file = request.files['image']
    temp_path = f"/tmp/{uuid.uuid4()}.jpg"
    file.save(temp_path)
    
    result = image_processor.detect_objects(temp_path)
    
    os.remove(temp_path)
    user.api_calls += 1
    db.session.commit()
    
    return jsonify({'result': result})


@app.route('/api/v2/recommendations/user/<user_id>', methods=['GET'])
@jwt_required()
def get_user_recommendations(user_id):
    """Get recommendations for user"""
    n = request.args.get('n', 10, type=int)
    
    result = recommendation_engine.recommend_for_user(user_id, n)
    
    return jsonify(result)


@app.route('/api/v2/models', methods=['POST'])
@jwt_required()
def upload_model():
    """Upload custom ML model"""
    user_id = int(get_jwt_identity())
    
    if 'model' not in request.files:
        return jsonify({'error': 'Model file required'}), 400
    
    file = request.files['model']
    model_data = request.form
    
    # Save model
    model_path = f"{Config.MODEL_PATH}/{user_id}/{uuid.uuid4()}_{file.filename}"
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    file.save(model_path)
    
    # Create model record
    model = MLModel(
        name=model_data.get('name'),
        description=model_data.get('description'),
        type=model_data.get('type'),
        framework=model_data.get('framework'),
        path=model_path,
        size=os.path.getsize(model_path),
        owner_id=user_id,
        is_public=model_data.get('is_public', 'false').lower() == 'true'
    )
    
    db.session.add(model)
    db.session.commit()
    
    return jsonify({
        'message': 'Model uploaded successfully',
        'model': model.to_dict()
    }), 201


@app.route('/api/v2/models', methods=['GET'])
def list_models():
    """List available models"""
    public_only = request.args.get('public', 'false').lower() == 'true'
    
    query = MLModel.query
    if public_only:
        query = query.filter_by(is_public=True)
    
    models = query.all()
    
    return jsonify({
        'models': [m.to_dict() for m in models]
    })


@app.route('/api/v2/stats', methods=['GET'])
@jwt_required()
def get_user_stats():
    """Get user AI usage statistics"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    # Get inference stats
    inferences = InferenceLog.query.filter_by(user_id=user_id).all()
    
    total_inferences = len(inferences)
    avg_latency = np.mean([i.latency_ms for i in inferences]) if inferences else 0
    
    # Get model stats
    models = MLModel.query.filter_by(owner_id=user_id).all()
    total_models = len(models)
    
    return jsonify({
        'user': user.to_dict(),
        'inferences': {
            'total': total_inferences,
            'avg_latency_ms': avg_latency
        },
        'models': {
            'total': total_models
        }
    })


# ===== Background Tasks =====

def cleanup_old_inferences():
    """Delete old inference logs"""
    try:
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        InferenceLog.query.filter(InferenceLog.created_at < thirty_days_ago).delete()
        db.session.commit()
        print("🧹 Cleaned up old inference logs")
    except Exception as e:
        print(f"Cleanup error: {e}")


# Schedule cleanup daily
from apscheduler.schedulers.background import BackgroundScheduler
scheduler = BackgroundScheduler()
scheduler.add_job(cleanup_old_inferences, 'interval', days=1)
scheduler.start()


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
║   🤖 Rizz AI Platform - ULTIMATE                          ║
║   Version: 4.0.0 LEGENDARY                               ║
║                                                          ║
║   Features:                                              ║
║   ✓ NLP (Sentiment, NER, Summarization)                  ║
║   ✓ Computer Vision (Classification, Detection)          ║
║   ✓ Recommendation Engine                                ║
║   ✓ Custom Model Upload                                  ║
║   ✓ Model Serving                                        ║
║   ✓ Usage Analytics                                      ║
║   ✓ API Rate Limiting                                    ║
║   ✓ GPU Acceleration                                     ║
║                                                          ║
║   Running on: http://localhost:3060                      ║
║   Device: {}                                             ║
║   GPU Available: {}                                      ║
║                                                          ║
║   Ready to infer! 🧠                                     ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    """.format(device, torch.cuda.is_available() if Config.GPU_ENABLED else False))
    
    app.run(debug=True, host='0.0.0.0', port=3060)
