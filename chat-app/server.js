/**
 * Real-time Chat Server with Socket.io
 * Features: Private messaging, group chats, AI chatbot, file sharing
 */

const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cors = require('cors');
const jwt = require('jsonwebtoken');
const { OpenAI } = require('openai');

const app = express();
app.use(cors());
app.use(express.json());

const server = http.createServer(app);
const io = new Server(server, {
  cors: {
    origin: process.env.CLIENT_URL || 'http://localhost:3000',
    methods: ['GET', 'POST'],
  },
});

// AI Chatbot setup
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// Store connected users
const users = new Map();
const typingUsers = new Map();

// Middleware
const authenticateToken = (req, res, next) => {
  const token = req.headers.authorization?.split(' ')[1];
  if (!token) return res.status(401).json({ error: 'No token' });
  
  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    req.user = decoded;
    next();
  } catch (error) {
    res.status(403).json({ error: 'Invalid token' });
  }
};

// REST API Routes
app.post('/api/auth/login', (req, res) => {
  const { username } = req.body;
  const token = jwt.sign({ username, id: Date.now() }, process.env.JWT_SECRET);
  res.json({ token, user: { username, id: Date.now() } });
});

app.get('/api/users', authenticateToken, (req, res) => {
  res.json({ users: Array.from(users.values()) });
});

// AI Chat endpoint
app.post('/api/chat/ai', authenticateToken, async (req, res) => {
  const { message, conversationHistory = [] } = req.body;
  
  try {
    const completion = await openai.chat.completions.create({
      model: 'gpt-3.5-turbo',
      messages: [
        { role: 'system', content: 'You are Rizz AI, a helpful assistant for the Rizz Project platform.' },
        ...conversationHistory,
        { role: 'user', content: message }
      ],
      max_tokens: 500,
    });
    
    res.json({ response: completion.choices[0].message.content });
  } catch (error) {
    res.status(500).json({ error: 'AI service unavailable' });
  }
});

// Socket.io Connection
io.on('connection', (socket) => {
  console.log(`User connected: ${socket.id}`);
  
  // User joins
  socket.on('user_join', (data) => {
    const user = { id: socket.id, ...data };
    users.set(socket.id, user);
    socket.broadcast.emit('user_online', user);
    socket.emit('users_list', Array.from(users.values()));
  });
  
  // Send message
  socket.on('send_message', (data) => {
    const message = {
      ...data,
      id: Date.now(),
      timestamp: new Date().toISOString(),
      from: socket.id,
    };
    
    // Send to room or user
    if (data.room) {
      io.to(data.room).emit('receive_message', message);
    } else if (data.to) {
      io.to(data.to).emit('receive_message', message);
    }
  });
  
  // Join room
  socket.on('join_room', (room) => {
    socket.join(room);
    socket.emit('room_joined', room);
  });
  
  // Leave room
  socket.on('leave_room', (room) => {
    socket.leave(room);
  });
  
  // Typing indicator
  socket.on('typing', (data) => {
    socket.to(data.room || data.to).emit('user_typing', {
      userId: socket.id,
      username: data.username,
    });
  });
  
  socket.on('stop_typing', (data) => {
    socket.to(data.room || data.to).emit('user_stop_typing', {
      userId: socket.id,
    });
  });
  
  // AI Chat request
  socket.on('ai_chat', async (data, callback) => {
    try {
      const completion = await openai.chat.completions.create({
        model: 'gpt-3.5-turbo',
        messages: [
          { role: 'system', content: 'You are Rizz AI, a helpful assistant.' },
          { role: 'user', content: data.message }
        ],
        max_tokens: 300,
      });
      
      callback({ response: completion.choices[0].message.content });
    } catch (error) {
      callback({ error: 'AI unavailable' });
    }
  });
  
  // Disconnect
  socket.on('disconnect', () => {
    const user = users.get(socket.id);
    if (user) {
      users.delete(socket.id);
      io.emit('user_offline', { id: socket.id, username: user.username });
    }
    console.log(`User disconnected: ${socket.id}`);
  });
});

// Start server
const PORT = process.env.PORT || 4000;
server.listen(PORT, () => {
  console.log(`🚀 Chat Server running on port ${PORT}`);
  console.log(`🤖 AI Chat: ${process.env.OPENAI_API_KEY ? 'Enabled' : 'Disabled'}`);
});
