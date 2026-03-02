"""
ML Service - AI/ML Predictions Platform
Text classification, sentiment analysis, recommendations, and embeddings
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import redis
import json
import os

# Redis for caching
redis_client = redis.Redis(
    host='redis',
    port=6379,
    db=4,
    decode_responses=True
)

app = FastAPI(
    title="Rizz ML Service",
    description="AI/ML Predictions Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== Models =====

class TextClassificationRequest(BaseModel):
    text: str
    model: str = 'sentiment'


class TextClassificationResponse(BaseModel):
    label: str
    confidence: float
    all_scores: Dict[str, float]


class SimilarityRequest(BaseModel):
    text1: str
    text2: str


class SimilarityResponse(BaseModel):
    similarity_score: float
    is_similar: bool
    threshold: float


class RecommendationRequest(BaseModel):
    user_id: str
    limit: int = 10


class ContentEmbeddingRequest(BaseModel):
    texts: List[str]


class ContentEmbeddingResponse(BaseModel):
    embeddings: List[List[float]]
    dimensions: int


class MLModelInfo(BaseModel):
    name: str
    version: str
    description: str
    input_type: str
    output_type: str


# ===== Simple ML Models (In production: Load from HuggingFace or custom models) =====

class SentimentAnalyzer:
    """Simple rule-based sentiment analyzer"""
    
    POSITIVE_WORDS = {
        'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic',
        'awesome', 'love', 'best', 'happy', 'joy', 'beautiful', 'nice',
        'helpful', 'perfect', 'brilliant', 'outstanding', 'superb'
    }
    
    NEGATIVE_WORDS = {
        'bad', 'terrible', 'awful', 'horrible', 'worst', 'hate', 'poor',
        'disappointing', 'useless', 'waste', 'boring', 'difficult',
        'frustrating', 'annoying', 'sad', 'angry', 'wrong', 'error'
    }
    
    def predict(self, text: str) -> Dict[str, float]:
        words = set(text.lower().split())
        
        positive_score = len(words & self.POSITIVE_WORDS)
        negative_score = len(words & self.NEGATIVE_WORDS)
        
        total = positive_score + negative_score
        if total == 0:
            return {'positive': 0.5, 'neutral': 0.5, 'negative': 0.0}
        
        positive = positive_score / total
        negative = negative_score / total
        neutral = max(0, 1 - positive - negative)
        
        return {
            'positive': round(positive, 3),
            'neutral': round(neutral, 3),
            'negative': round(negative, 3)
        }


class TextClassifier:
    """TF-IDF based text classifier"""
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=1000)
        self.training_texts = []
        self.training_labels = []
    
    def fit(self, texts: List[str], labels: List[str]):
        self.training_texts = texts
        self.training_labels = labels
        self.vectorizer.fit(texts)
    
    def predict(self, text: str, k: int = 3) -> List[Dict[str, Any]]:
        if not self.training_texts:
            return [{'label': 'unknown', 'confidence': 1.0}]
        
        text_vec = self.vectorizer.transform([text])
        train_vecs = self.vectorizer.transform(self.training_texts)
        
        similarities = cosine_similarity(text_vec, train_vecs)[0]
        top_indices = np.argsort(similarities)[-k:][::-1]
        
        results = []
        for idx in top_indices:
            results.append({
                'label': self.training_labels[idx],
                'confidence': round(float(similarities[idx]), 3)
            })
        
        return results


# Initialize models
sentiment_analyzer = SentimentAnalyzer()
text_classifier = TextClassifier()

# Train with sample data (in production: load pre-trained models)
sample_texts = [
    "This is amazing and wonderful",
    "Terrible experience, very bad",
    "Great product, highly recommend",
    "Worst purchase ever made",
    "Excellent service and support"
]
sample_labels = ['positive', 'negative', 'positive', 'negative', 'positive']
text_classifier.fit(sample_texts, sample_labels)


# ===== API Endpoints =====

@app.get('/health')
async def health_check():
    """Health check"""
    return {
        'status': 'healthy',
        'service': 'ml',
        'version': '1.0.0',
        'models_loaded': True,
        'timestamp': datetime.utcnow().isoformat()
    }


@app.get('/api/ml/models')
async def list_models():
    """List available ML models"""
    models = [
        MLModelInfo(
            name='sentiment',
            version='1.0.0',
            description='Sentiment analysis for text',
            input_type='text',
            output_type='classification'
        ),
        MLModelInfo(
            name='similarity',
            version='1.0.0',
            description='Text similarity comparison',
            input_type='text_pair',
            output_type='similarity_score'
        ),
        MLModelInfo(
            name='embedding',
            version='1.0.0',
            description='Generate text embeddings',
            input_type='text_list',
            output_type='vectors'
        ),
        MLModelInfo(
            name='recommendation',
            version='1.0.0',
            description='Content recommendations',
            input_type='user_id',
            output_type='recommendations'
        )
    ]
    
    return {'models': [m.dict() for m in models]}


@app.post('/api/ml/classify', response_model=TextClassificationResponse)
async def classify_text(request: TextClassificationRequest):
    """Classify text (sentiment analysis)"""
    try:
        # Check cache
        cache_key = f'ml:classify:{request.model}:{hash(request.text)}'
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
        
        if request.model == 'sentiment':
            scores = sentiment_analyzer.predict(request.text)
            label = max(scores, key=scores.get)
            confidence = scores[label]
        else:
            predictions = text_classifier.predict(request.text)
            label = predictions[0]['label']
            confidence = predictions[0]['confidence']
            scores = {p['label']: p['confidence'] for p in predictions}
        
        response = TextClassificationResponse(
            label=label,
            confidence=confidence,
            all_scores=scores
        )
        
        # Cache for 1 hour
        redis_client.setex(cache_key, 3600, json.dumps(response.dict()))
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/ml/similarity', response_model=SimilarityResponse)
async def calculate_similarity(request: SimilarityRequest):
    """Calculate similarity between two texts"""
    try:
        # Check cache
        cache_key = f'ml:similarity:{hash(request.text1)}:{hash(request.text2)}'
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # Calculate TF-IDF similarity
        vectors = text_classifier.vectorizer.transform([request.text1, request.text2])
        similarity = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
        
        threshold = 0.5
        response = SimilarityResponse(
            similarity_score=round(float(similarity), 3),
            is_similar=similarity > threshold,
            threshold=threshold
        )
        
        # Cache for 24 hours
        redis_client.setex(cache_key, 86400, json.dumps(response.dict()))
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/ml/embedding', response_model=ContentEmbeddingResponse)
async def generate_embeddings(request: ContentEmbeddingRequest):
    """Generate text embeddings"""
    try:
        # Check cache
        embeddings = []
        for text in request.texts:
            cache_key = f'ml:embedding:{hash(text)}'
            cached = redis_client.get(cache_key)
            
            if cached:
                embeddings.append(json.loads(cached))
            else:
                # Generate simple TF-IDF based embedding
                vector = text_classifier.vectorizer.transform([text]).toarray()[0]
                embedding = vector.tolist()
                embeddings.append(embedding)
                redis_client.setex(cache_key, 86400, json.dumps(embedding))
        
        return ContentEmbeddingResponse(
            embeddings=embeddings,
            dimensions=len(embeddings[0]) if embeddings else 0
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/ml/recommend')
async def get_recommendations(request: RecommendationRequest):
    """Get content recommendations for user"""
    try:
        # Check cache
        cache_key = f'ml:recommend:{request.user_id}:{request.limit}'
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # In production: Use collaborative filtering or neural recommendations
        # For now: Return popular/trending content
        recommendations = [
            {'id': f'post_{i}', 'score': round(0.9 - i * 0.05, 2), 'reason': 'trending'}
            for i in range(1, request.limit + 1)
        ]
        
        response = {
            'user_id': request.user_id,
            'recommendations': recommendations,
            'algorithm': 'popularity_based',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Cache for 30 minutes
        redis_client.setex(cache_key, 1800, json.dumps(response))
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/ml/batch-classify')
async def batch_classify(texts: List[str], model: str = 'sentiment'):
    """Batch classify multiple texts"""
    try:
        results = []
        for text in texts:
            if model == 'sentiment':
                scores = sentiment_analyzer.predict(text)
                label = max(scores, key=scores.get)
            else:
                predictions = text_classifier.predict(text)
                label = predictions[0]['label']
                scores = {p['label']: p['confidence'] for p in predictions}
            
            results.append({
                'text': text[:100],  # Truncate for response
                'label': label,
                'scores': scores
            })
        
        return {
            'count': len(results),
            'results': results,
            'model': model
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/ml/stats')
async def get_ml_stats():
    """Get ML service statistics"""
    # Get cached predictions count
    predictions_count = redis_client.dbsize()
    
    return {
        'statistics': {
            'cached_predictions': predictions_count,
            'models_available': 4,
            'uptime': 'N/A'  # Would track in production
        },
        'timestamp': datetime.utcnow().isoformat()
    }


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8005)
