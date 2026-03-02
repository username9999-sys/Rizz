"""
WebSocket Gateway - Real-time Bidirectional Communication
Supports chat, notifications, live updates, and presence
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import socketio
import redis
import json
from datetime import datetime
from typing import Dict, List, Optional
import asyncio
from prometheus_client import Counter, Histogram, generate_latest
import os

# Prometheus metrics
WS_CONNECTIONS = Counter('websocket_connections_total', 'Total WebSocket connections')
WS_MESSAGES = Counter('websocket_messages_total', 'Total WebSocket messages', ['type'])
WS_LATENCY = Histogram('websocket_message_latency_seconds', 'WebSocket message latency')

# Redis for pub/sub and presence
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'redis'),
    port=6379,
    db=7,
    decode_responses=True
)

redis_pubsub = redis_client.pubsub()

# Socket.IO server
sio = socketio.AsyncServer(
    cors_allowed_origins="*",
    async_mode='asgi',
    logger=True,
    engineio_logger=True,
    ping_timeout=60,
    ping_interval=25
)

app = FastAPI(
    title="Rizz WebSocket Gateway",
    description="Real-time WebSocket Communication Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Socket.IO
socket_app = socketio.ASGIApp(sio, app)

# Connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.user_status: Dict[str, str] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        self.user_status[user_id] = 'online'
        
        # Store in Redis
        redis_client.hset(f'user:{user_id}:presence', mapping={
            'status': 'online',
            'last_seen': datetime.utcnow().isoformat(),
            'connections': len(self.active_connections[user_id])
        })
        
        # Broadcast presence
        await self.broadcast_presence(user_id, 'online')
        
        WS_CONNECTIONS.inc()
    
    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                self.user_status[user_id] = 'offline'
                
                # Update Redis
                redis_client.hset(f'user:{user_id}:presence', mapping={
                    'status': 'offline',
                    'last_seen': datetime.utcnow().isoformat()
                })
                
                # Broadcast presence
                asyncio.create_task(self.broadcast_presence(user_id, 'offline'))
    
    async def send_personal(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_json(message)
    
    async def broadcast(self, message: dict, room: Optional[str] = None):
        if room:
            await sio.emit('message', message, room=room)
        else:
            await sio.emit('message', message)
    
    async def broadcast_presence(self, user_id: str, status: str):
        await sio.emit('presence', {
            'user_id': user_id,
            'status': status,
            'timestamp': datetime.utcnow().isoformat()
        })

manager = ConnectionManager()


# ===== Socket.IO Events =====

@sio.event
async def connect(sid, environ, auth):
    """Handle new connection"""
    user_id = auth.get('user_id') if auth else None
    if user_id:
        await sio.enter_room(sid, f'user:{user_id}')
        redis_client.set(f'socket:{sid}', user_id)
        print(f"User {user_id} connected with socket {sid}")


@sio.event
async def disconnect(sid):
    """Handle disconnection"""
    user_id = redis_client.get(f'socket:{sid}')
    if user_id:
        await sio.leave_room(sid, f'user:{user_id}')
        redis_client.delete(f'socket:{sid}')
        print(f"User {user_id} disconnected")


@sio.event
async def join_room(sid, room):
    """Join a room"""
    await sio.enter_room(sid, room)
    await sio.emit('room_joined', {'room': room}, to=sid)


@sio.event
async def leave_room(sid, room):
    """Leave a room"""
    await sio.leave_room(sid, room)
    await sio.emit('room_left', {'room': room}, to=sid)


# ===== Message Handlers =====

@sio.on('chat_message')
async def handle_chat_message(sid, data):
    """Handle chat message"""
    with WS_LATENCY.time():
        user_id = redis_client.get(f'socket:{sid}')
        message = {
            'type': 'chat',
            'user_id': user_id,
            'content': data.get('content'),
            'room': data.get('room'),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Store in Redis
        redis_client.lpush(f'chat:{data.get("room", "global")}', json.dumps(message))
        redis_client.ltrim(f'chat:{data.get("room", "global")}', 0, 999)
        
        # Broadcast to room
        room = data.get('room', 'global')
        await sio.emit('chat_message', message, room=f'room:{room}')
        
        WS_MESSAGES.inc(labels={'type': 'chat'})


@sio.on('notification')
async def handle_notification(sid, data):
    """Send notification to specific user"""
    with WS_LATENCY.time():
        target_user = data.get('user_id')
        notification = {
            'type': 'notification',
            'from_user': redis_client.get(f'socket:{sid}'),
            'title': data.get('title'),
            'message': data.get('message'),
            'data': data.get('data'),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await sio.emit('notification', notification, room=f'user:{target_user}')
        
        WS_MESSAGES.inc(labels={'type': 'notification'})


@sio.on('typing')
async def handle_typing(sid, data):
    """Broadcast typing indicator"""
    user_id = redis_client.get(f'socket:{sid}')
    typing_data = {
        'type': 'typing',
        'user_id': user_id,
        'room': data.get('room'),
        'timestamp': datetime.utcnow().isoformat()
    }
    
    await sio.emit('typing', typing_data, room=f'room:{data.get("room", "global")}')


@sio.on('presence')
async def handle_presence(sid, data):
    """Handle presence update"""
    user_id = redis_client.get(f'socket:{sid}')
    await sio.emit('presence_update', {
        'user_id': user_id,
        'status': data.get('status'),
        'timestamp': datetime.utcnow().isoformat()
    })


# ===== REST API Endpoints =====

@app.get('/health')
async def health_check():
    """Health check"""
    return {
        'status': 'healthy',
        'service': 'websocket-gateway',
        'version': '1.0.0',
        'connections': len(manager.active_connections),
        'timestamp': datetime.utcnow().isoformat()
    }


@app.get('/metrics')
async def metrics():
    """Prometheus metrics"""
    return generate_latest(), 200, {'Content-Type': 'text/plain; charset=utf-8'}


@app.get('/api/ws/users/{user_id}/presence')
async def get_user_presence(user_id: str):
    """Get user presence status"""
    presence = redis_client.hgetall(f'user:{user_id}:presence')
    return {
        'user_id': user_id,
        'presence': presence or {'status': 'offline'}
    }


@app.get('/api/ws/rooms/{room}/messages')
async def get_room_messages(room: str, limit: int = 50):
    """Get recent messages from room"""
    messages = redis_client.lrange(f'chat:{room}', 0, limit - 1)
    return {
        'room': room,
        'messages': [json.loads(msg) for msg in messages],
        'count': len(messages)
    }


@app.post('/api/ws/broadcast')
async def broadcast_message(message: dict, room: Optional[str] = None):
    """Broadcast message to all or specific room"""
    message['timestamp'] = datetime.utcnow().isoformat()
    await manager.broadcast(message, room)
    return {'status': 'broadcasted', 'room': room}


@app.get('/api/ws/stats')
async def get_stats():
    """Get WebSocket statistics"""
    return {
        'active_connections': len(manager.active_connections),
        'online_users': len([u for u, s in manager.user_status.items() if s == 'online']),
        'total_sockets': redis_client.dbscan(match='socket:*')[1],
        'timestamp': datetime.utcnow().isoformat()
    }


# ===== Background Tasks =====

async def redis_listener():
    """Listen to Redis pub/sub for cross-instance communication"""
    await redis_pubsub.psubscribe('broadcast:*')
    
    async for message in redis_pubsub.listen():
        if message['type'] == 'pmessage':
            data = json.loads(message['data'])
            await manager.broadcast(data)


@app.on_event("startup")
async def startup_event():
    """Startup event"""
    asyncio.create_task(redis_listener())
    print("WebSocket Gateway started")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event"""
    await redis_pubsub.close()
    redis_client.close()
    print("WebSocket Gateway stopped")


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(socket_app, host='0.0.0.0', port=5002)
