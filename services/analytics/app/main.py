"""
Analytics Service - Enterprise Real-time Analytics Platform
Built with FastAPI, Pandas, and TimescaleDB
"""

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_wsgi_app, Counter, Histogram
from starlette.middleware import Middleware
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List
import asyncpg
import redis
import json
from contextlib import asynccontextmanager

# Metrics
REQUEST_COUNT = Counter('analytics_requests_total', 'Total analytics requests', ['endpoint', 'status'])
QUERY_LATENCY = Histogram('analytics_query_duration_seconds', 'Analytics query latency', ['query_type'])

# Database connection pool
db_pool = None
redis_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global db_pool, redis_client
    
    # Startup
    db_pool = await asyncpg.create_pool(
        'postgresql://analytics_user:analytics_pass@timescaledb:5432/analytics',
        min_size=5,
        max_size=20
    )
    
    redis_client = redis.Redis(
        host='redis',
        port=6379,
        db=1,
        decode_responses=True
    )
    
    yield
    
    # Shutdown
    await db_pool.close()
    redis_client.close()


app = FastAPI(
    title="Rizz Analytics Service",
    description="Enterprise Real-time Analytics Platform",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get('/health')
async def health_check():
    """Health check endpoint"""
    return {
        'status': 'healthy',
        'service': 'analytics',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat()
    }


@app.get('/metrics')
async def metrics():
    """Prometheus metrics endpoint"""
    return make_wsgi_app()


@app.get('/api/analytics/overview')
@QUERY_LATENCY.time()
async def get_analytics_overview(
    days: int = Query(default=7, ge=1, le=90)
):
    """Get overall analytics for the platform"""
    try:
        async with db_pool.acquire() as conn:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # User activity
            user_activity = await conn.fetch('''
                SELECT 
                    DATE_TRUNC('day', created_at) as date,
                    COUNT(*) as total_users,
                    COUNT(*) FILTER (WHERE is_verified = true) as verified_users
                FROM users
                WHERE created_at >= $1 AND created_at <= $2
                GROUP BY 1
                ORDER BY 1
            ''', start_date, end_date)
            
            # Post activity
            post_activity = await conn.fetch('''
                SELECT 
                    DATE_TRUNC('day', created_at) as date,
                    COUNT(*) as total_posts,
                    SUM(view_count) as total_views,
                    SUM(like_count) as total_likes
                FROM posts
                WHERE created_at >= $1 AND created_at <= $2
                GROUP BY 1
                ORDER BY 1
            ''', start_date, end_date)
            
            # Convert to pandas for analysis
            user_df = pd.DataFrame(user_activity)
            post_df = pd.DataFrame(post_activity)
            
            # Calculate metrics
            total_users = user_df['total_users'].sum() if not user_df.empty else 0
            total_posts = post_df['total_posts'].sum() if not post_df.empty else 0
            total_views = int(post_df['total_views'].sum()) if not post_df.empty else 0
            avg_engagement = float(post_df['total_likes'].mean()) if not post_df.empty else 0
            
            return {
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat(),
                    'days': days
                },
                'metrics': {
                    'total_users': int(total_users),
                    'total_posts': int(total_posts),
                    'total_views': total_views,
                    'avg_engagement_rate': round(avg_engagement, 2)
                },
                'trends': {
                    'user_growth': calculate_growth_rate(user_df['total_users']),
                    'post_growth': calculate_growth_rate(post_df['total_posts']),
                    'engagement_trend': calculate_trend(post_df['total_likes'])
                }
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/analytics/users')
async def get_user_analytics(
    group_by: str = Query(default='day', pattern='^(hour|day|week|month)$'),
    limit: int = Query(default=100, ge=1, le=1000)
):
    """Get detailed user analytics"""
    try:
        async with db_pool.acquire() as conn:
            query = f'''
                SELECT 
                    DATE_TRUNC('{group_by}', created_at) as period,
                    COUNT(*) as new_users,
                    COUNT(*) FILTER (WHERE is_active = true) as active_users,
                    COUNT(*) FILTER (WHERE is_verified = true) as verified_users
                FROM users
                GROUP BY 1
                ORDER BY 1 DESC
                LIMIT $1
            '''
            
            rows = await conn.fetch(query, limit)
            df = pd.DataFrame(rows)
            
            return {
                'data': df.to_dict('records'),
                'summary': {
                    'total_new_users': int(df['new_users'].sum()),
                    'avg_daily_signups': float(df['new_users'].mean()),
                    'peak_day': df.loc[df['new_users'].idxmax(), 'period'].isoformat() if not df.empty else None
                }
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/analytics/posts')
async def get_post_analytics(
    status: Optional[str] = None,
    min_views: int = 0,
    group_by: str = 'day'
):
    """Get post performance analytics"""
    try:
        async with db_pool.acquire() as conn:
            where_clause = 'WHERE 1=1'
            if status:
                where_clause += f" AND status = '{status}'"
            
            query = f'''
                SELECT 
                    p.id,
                    p.title,
                    p.status,
                    p.view_count,
                    p.like_count,
                    p.comment_count,
                    p.created_at,
                    u.username as author
                FROM posts p
                JOIN users u ON p.user_id = u.id
                {where_clause}
                AND p.view_count >= $1
                ORDER BY p.view_count DESC
                LIMIT 100
            '''
            
            rows = await conn.fetch(query, min_views)
            df = pd.DataFrame(rows)
            
            if df.empty:
                return {'data': [], 'summary': {}}
            
            # Calculate statistics
            stats = {
                'total_posts': len(df),
                'avg_views': float(df['view_count'].mean()),
                'median_views': float(df['view_count'].median()),
                'avg_likes': float(df['like_count'].mean()),
                'avg_comments': float(df['comment_count'].mean()),
                'top_performer': df.loc[df['view_count'].idxmax(), 'title']
            }
            
            return {
                'data': df.to_dict('records'),
                'summary': stats
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/analytics/realtime')
async def get_realtime_analytics():
    """Get real-time analytics from Redis"""
    try:
        # Get cached metrics from Redis
        active_users = redis_client.get('analytics:active_users') or 0
        requests_per_minute = redis_client.get('analytics:rpm') or 0
        avg_response_time = redis_client.get('analytics:avg_response_ms') or 0
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'metrics': {
                'active_users': int(active_users),
                'requests_per_minute': int(requests_per_minute),
                'avg_response_time_ms': float(avg_response_time)
            },
            'status': 'live'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/analytics/events')
async def track_event(event: dict):
    """Track custom analytics event"""
    try:
        event_with_timestamp = {
            **event,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Store in Redis for real-time analytics
        redis_client.lpush('analytics:events', json.dumps(event_with_timestamp))
        redis_client.ltrim('analytics:events', 0, 9999)  # Keep last 10000 events
        
        # Async: Store in database (would use Celery in production)
        async with db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO events (event_type, event_data, created_at)
                VALUES ($1, $2, $3)
            ''', event.get('type'), json.dumps(event), datetime.utcnow())
        
        return {'status': 'tracked', 'event_id': event.get('type')}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/analytics/reports/{report_type}')
async def generate_report(
    report_type: str,
    format: str = Query(default='json', pattern='^(json|csv)$'),
    days: int = 30
):
    """Generate analytics report"""
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        async with db_pool.acquire() as conn:
            if report_type == 'user_growth':
                data = await conn.fetch('''
                    SELECT 
                        DATE_TRUNC('day', created_at) as date,
                        COUNT(*) as users
                    FROM users
                    WHERE created_at >= $1 AND created_at <= $2
                    GROUP BY 1
                    ORDER BY 1
                ''', start_date, end_date)
            elif report_type == 'content_performance':
                data = await conn.fetch('''
                    SELECT 
                        p.id,
                        p.title,
                        p.view_count,
                        p.like_count,
                        p.comment_count,
                        u.username as author
                    FROM posts p
                    JOIN users u ON p.user_id = u.id
                    WHERE p.created_at >= $1 AND p.created_at <= $2
                    ORDER BY p.view_count DESC
                    LIMIT 100
                ''', start_date, end_date)
            else:
                raise HTTPException(status_code=400, detail='Invalid report type')
            
            df = pd.DataFrame(data)
            
            if format == 'csv':
                from io import StringIO
                output = StringIO()
                df.to_csv(output, index=False)
                return {'csv': output.getvalue()}
            
            return {
                'report_type': report_type,
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'data': df.to_dict('records')
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def calculate_growth_rate(series: pd.Series) -> float:
    """Calculate growth rate percentage"""
    if len(series) < 2:
        return 0.0
    recent = series.iloc[-1]
    previous = series.iloc[0]
    if previous == 0:
        return 100.0
    return round(((recent - previous) / previous) * 100, 2)


def calculate_trend(series: pd.Series) -> str:
    """Determine trend direction"""
    if len(series) < 2:
        return 'stable'
    recent_avg = series.tail(7).mean()
    previous_avg = series.head(7).mean()
    if recent_avg > previous_avg * 1.1:
        return 'increasing'
    elif recent_avg < previous_avg * 0.9:
        return 'decreasing'
    return 'stable'


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8001)
