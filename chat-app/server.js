/**
 * Rizz Chat Application - Enhanced Server
 * Features: WebSocket, JWT Auth, Message Encryption, File Sharing, Typing Indicators
 * Author: username9999
 */

const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcrypt');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const Redis = require('ioredis');
const mongoose = require('mongoose');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');
require('dotenv').config();

// ===== Configuration =====
const CONFIG = {
    port: process.env.PORT || 3010,
    jwtSecret: process.env.JWT_SECRET || 'change-me-in-production',
    redisUrl: process.env.REDIS_URL || 'redis://localhost:6379',
    mongoUrl: process.env.MONGO_URL || 'mongodb://localhost:27017/rizz-chat',
    uploadDir: process.env.UPLOAD_DIR || './uploads',
    maxFileSize: 10 * 1024 * 1024, // 10MB
    bcryptRounds: 10,
    socketPingInterval: 30000,
    messageRetention: 30 // days
};

// ===== Initialize Express =====
const app = express();
const server = http.createServer(app);

// ===== Socket.IO with Redis Adapter =====
const io = socketIo(server, {
    cors: {
        origin: process.env.CORS_ORIGIN || '*',
        methods: ['GET', 'POST']
    },
    pingTimeout: 60000,
    pingInterval: 25000
});

// Redis for pub/sub and caching
const redis = new Redis(CONFIG.redisUrl);
const pubClient = redis.duplicate();
const subClient = redis.duplicate();

// ===== Middleware =====
app.use(cors());
app.use(helmet({
    contentSecurityPolicy: false,
    crossOriginEmbedderPolicy: false
}));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Rate limiting
const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100 // limit each IP to 100 requests per windowMs
});
app.use('/api/', limiter);

// File upload configuration
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        if (!fs.existsSync(CONFIG.uploadDir)) {
            fs.mkdirSync(CONFIG.uploadDir, { recursive: true });
        }
        cb(null, CONFIG.uploadDir);
    },
    filename: (req, file, cb) => {
        const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
        cb(null, `${uniqueSuffix}-${file.originalname}`);
    }
});

const upload = multer({
    storage: storage,
    limits: { fileSize: CONFIG.maxFileSize },
    fileFilter: (req, file, cb) => {
        const allowedTypes = /jpeg|jpg|png|gif|pdf|doc|docx|txt|zip/;
        const extname = allowedTypes.test(path.extname(file.originalname).toLowerCase());
        const mimetype = allowedTypes.test(file.mimetype);
        
        if (extname && mimetype) {
            cb(null, true);
        } else {
            cb(new Error('Invalid file type'));
        }
    }
});

// ===== MongoDB Models =====
mongoose.connect(CONFIG.mongoUrl, {
    useNewUrlParser: true,
    useUnifiedTopology: true
}).then(() => {
    console.log('✅ MongoDB connected');
}).catch(err => {
    console.error('❌ MongoDB connection error:', err);
});

const UserSchema = new mongoose.Schema({
    username: { type: String, required: true, unique: true },
    email: { type: String, required: true, unique: true },
    password: { type: String, required: true },
    avatar: String,
    status: { type: String, enum: ['online', 'offline', 'away', 'busy'], default: 'offline' },
    lastSeen: Date,
    createdAt: { type: Date, default: Date.now }
});

const MessageSchema = new mongoose.Schema({
    sender: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
    receiver: { type: mongoose.Schema.Types.ObjectId, ref: 'User' },
    room: { type: String },
    content: { type: String, required: true },
    encrypted: { type: Boolean, default: false },
    type: { type: String, enum: ['text', 'file', 'image', 'system'], default: 'text' },
    fileUrl: String,
    fileName: String,
    fileSize: Number,
    read: { type: Boolean, default: false },
    readAt: Date,
    delivered: { type: Boolean, default: false },
    deliveredAt: Date,
    createdAt: { type: Date, default: Date.now }
});

const RoomSchema = new mongoose.Schema({
    name: { type: String, required: true },
    type: { type: String, enum: ['private', 'group', 'channel'], default: 'private' },
    members: [{ type: mongoose.Schema.Types.ObjectId, ref: 'User' }],
    admin: { type: mongoose.Schema.Types.ObjectId, ref: 'User' },
    lastMessage: { type: mongoose.Schema.Types.ObjectId, ref: 'Message' },
    createdAt: { type: Date, default: Date.now }
});

const User = mongoose.model('User', UserSchema);
const Message = mongoose.model('Message', MessageSchema);
const Room = mongoose.model('Room', RoomSchema);

// ===== Encryption Utility =====
const ENCRYPTION_KEY = crypto.randomBytes(32);
const IV_LENGTH = 16;

function encrypt(text) {
    const iv = crypto.randomBytes(IV_LENGTH);
    const cipher = crypto.createCipheriv('aes-256-cbc', Buffer.from(ENCRYPTION_KEY), iv);
    let encrypted = cipher.update(text);
    encrypted = Buffer.concat([encrypted, cipher.final()]);
    return iv.toString('hex') + ':' + encrypted.toString('hex');
}

function decrypt(text) {
    const textParts = text.split(':');
    const iv = Buffer.from(textParts.shift(), 'hex');
    const encryptedText = Buffer.from(textParts.join(':'), 'hex');
    const decipher = crypto.createDecipheriv('aes-256-cbc', Buffer.from(ENCRYPTION_KEY), iv);
    let decrypted = decipher.update(encryptedText);
    decrypted = Buffer.concat([decrypted, decipher.final()]);
    return decrypted.toString();
}

// ===== JWT Middleware =====
const authenticateToken = (req, res, next) => {
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1];
    
    if (!token) {
        return res.status(401).json({ error: 'Access token required' });
    }
    
    jwt.verify(token, CONFIG.jwtSecret, (err, user) => {
        if (err) {
            return res.status(403).json({ error: 'Invalid or expired token' });
        }
        req.user = user;
        next();
    });
};

// ===== Socket.IO Middleware =====
io.use(async (socket, next) => {
    const token = socket.handshake.auth.token;
    
    if (token) {
        try {
            const user = jwt.verify(token, CONFIG.jwtSecret);
            socket.user = user;
            next();
        } catch (err) {
            next(new Error('Invalid token'));
        }
    } else {
        next(new Error('Authentication required'));
    }
});

// ===== Socket.IO Event Handlers =====
io.on('connection', async (socket) => {
    console.log(`🔌 User connected: ${socket.user.username} (${socket.id})`);
    
    const userId = socket.user.id;
    
    // Update user status to online
    await User.findByIdAndUpdate(userId, { 
        status: 'online', 
        lastSeen: new Date() 
    });
    
    // Join user's personal room
    socket.join(`user:${userId}`);
    
    // Broadcast user online status
    io.emit('user_status', { 
        userId, 
        status: 'online',
        username: socket.user.username 
    });
    
    // ===== Chat Events =====
    
    socket.on('send_message', async (data) => {
        try {
            const { receiverId, content, roomId, type = 'text', fileUrl, fileName, fileSize } = data;
            
            // Encrypt message if private
            const isPrivate = !!receiverId && !roomId;
            const encryptedContent = isPrivate ? encrypt(content) : content;
            
            // Save message to database
            const message = await Message.create({
                sender: userId,
                receiver: receiverId,
                room: roomId,
                content: encryptedContent,
                encrypted: isPrivate,
                type,
                fileUrl,
                fileName,
                fileSize
            });
            
            // Populate sender info
            await message.populate('sender', 'username avatar');
            
            // Emit to receiver
            if (receiverId) {
                io.to(`user:${receiverId}`).emit('receive_message', {
                    ...message.toObject(),
                    content // Send unencrypted to receiver
                });
            }
            
            // Emit to room
            if (roomId) {
                io.to(`room:${roomId}`).emit('receive_message', message.toObject());
            }
            
            // Emit back to sender
            socket.emit('message_sent', message.toObject());
            
            // Store in Redis for caching
            await redis.lpush(`messages:${receiverId || roomId}`, JSON.stringify(message));
            await redis.ltrim(`messages:${receiverId || roomId}`, 0, 99);
            
            console.log(`📨 Message sent: ${message._id}`);
        } catch (error) {
            console.error('Error sending message:', error);
            socket.emit('error', { message: 'Failed to send message' });
        }
    });
    
    socket.on('typing', (data) => {
        const { receiverId, roomId, isTyping } = data;
        
        if (receiverId) {
            io.to(`user:${receiverId}`).emit('user_typing', {
                userId,
                username: socket.user.username,
                isTyping
            });
        }
        
        if (roomId) {
            socket.to(`room:${roomId}`).emit('user_typing', {
                userId,
                username: socket.user.username,
                isTyping
            });
        }
    });
    
    socket.on('read_message', async (data) => {
        const { messageId } = data;
        
        await Message.findByIdAndUpdate(messageId, {
            read: true,
            readAt: new Date()
        });
        
        socket.emit('message_read', { messageId, readAt: new Date() });
    });
    
    // ===== Room Events =====
    
    socket.on('join_room', async (roomId) => {
        socket.join(`room:${roomId}`);
        console.log(`User ${socket.user.username} joined room ${roomId}`);
    });
    
    socket.on('leave_room', async (roomId) => {
        socket.leave(`room:${roomId}`);
        console.log(`User ${socket.user.username} left room ${roomId}`);
    });
    
    // ===== File Upload Event =====
    
    socket.on('upload_file', async (data, callback) => {
        try {
            const { fileName, fileData, mimeType } = data;
            
            // Save file (in production, use cloud storage)
            const fileBuffer = Buffer.from(fileData, 'base64');
            const fileNameWithTimestamp = `${Date.now()}-${fileName}`;
            const filePath = path.join(CONFIG.uploadDir, fileNameWithTimestamp);
            
            fs.writeFileSync(filePath, fileBuffer);
            
            const fileUrl = `/uploads/${fileNameWithTimestamp}`;
            
            callback({ success: true, fileUrl, fileName });
        } catch (error) {
            console.error('File upload error:', error);
            callback({ success: false, error: 'Upload failed' });
        }
    });
    
    // ===== Disconnect =====
    
    socket.on('disconnect', async () => {
        console.log(`🔌 User disconnected: ${socket.user.username}`);
        
        await User.findByIdAndUpdate(userId, { 
            status: 'offline', 
            lastSeen: new Date() 
        });
        
        io.emit('user_status', { 
            userId, 
            status: 'offline',
            username: socket.user.username 
        });
    });
});

// ===== REST API Routes =====

// Register
app.post('/api/auth/register', async (req, res) => {
    try {
        const { username, email, password } = req.body;
        
        // Validate input
        if (!username || !email || !password) {
            return res.status(400).json({ error: 'All fields are required' });
        }
        
        // Check if user exists
        const existingUser = await User.findOne({ 
            $or: [{ username }, { email }] 
        });
        
        if (existingUser) {
            return res.status(400).json({ error: 'Username or email already exists' });
        }
        
        // Hash password
        const hashedPassword = await bcrypt.hash(password, CONFIG.bcryptRounds);
        
        // Create user
        const user = await User.create({
            username,
            email,
            password: hashedPassword
        });
        
        // Generate JWT token
        const token = jwt.sign(
            { id: user._id, username: user.username, email: user.email },
            CONFIG.jwtSecret,
            { expiresIn: '7d' }
        );
        
        res.status(201).json({
            message: 'User registered successfully',
            token,
            user: {
                id: user._id,
                username: user.username,
                email: user.email,
                avatar: user.avatar
            }
        });
    } catch (error) {
        console.error('Registration error:', error);
        res.status(500).json({ error: 'Registration failed' });
    }
});

// Login
app.post('/api/auth/login', async (req, res) => {
    try {
        const { username, password } = req.body;
        
        // Find user
        const user = await User.findOne({ username });
        
        if (!user) {
            return res.status(401).json({ error: 'Invalid credentials' });
        }
        
        // Verify password
        const isValid = await bcrypt.compare(password, user.password);
        
        if (!isValid) {
            return res.status(401).json({ error: 'Invalid credentials' });
        }
        
        // Generate JWT token
        const token = jwt.sign(
            { id: user._id, username: user.username, email: user.email },
            CONFIG.jwtSecret,
            { expiresIn: '7d' }
        );
        
        // Update last seen
        await User.findByIdAndUpdate(user._id, { lastSeen: new Date() });
        
        res.json({
            message: 'Login successful',
            token,
            user: {
                id: user._id,
                username: user.username,
                email: user.email,
                avatar: user.avatar,
                status: user.status
            }
        });
    } catch (error) {
        console.error('Login error:', error);
        res.status(500).json({ error: 'Login failed' });
    }
});

// Get users
app.get('/api/users', authenticateToken, async (req, res) => {
    try {
        const users = await User.find()
            .select('-password')
            .sort({ lastSeen: -1 });
        
        res.json({ users });
    } catch (error) {
        console.error('Get users error:', error);
        res.status(500).json({ error: 'Failed to get users' });
    }
});

// Get messages
app.get('/api/messages/:userId', authenticateToken, async (req, res) => {
    try {
        const { userId } = req.params;
        const limit = parseInt(req.query.limit) || 50;
        
        const messages = await Message.find({
            $or: [
                { sender: userId, receiver: req.user.id },
                { sender: req.user.id, receiver: userId }
            ]
        })
        .sort({ createdAt: -1 })
        .limit(limit)
        .populate('sender', 'username avatar')
        .populate('receiver', 'username avatar');
        
        // Decrypt private messages
        const decryptedMessages = messages.map(msg => {
            const obj = msg.toObject();
            if (obj.encrypted) {
                try {
                    obj.content = decrypt(obj.content);
                } catch (e) {
                    console.error('Decryption failed:', e);
                }
            }
            return obj;
        });
        
        res.json({ messages: decryptedMessages });
    } catch (error) {
        console.error('Get messages error:', error);
        res.status(500).json({ error: 'Failed to get messages' });
    }
});

// Upload file
app.post('/api/upload', authenticateToken, upload.single('file'), async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({ error: 'No file uploaded' });
        }
        
        const fileUrl = `/uploads/${req.file.filename}`;
        
        res.json({
            success: true,
            fileUrl,
            fileName: req.file.originalname,
            fileSize: req.file.size,
            mimeType: req.file.mimetype
        });
    } catch (error) {
        console.error('Upload error:', error);
        res.status(500).json({ error: 'Upload failed' });
    }
});

// Health check
app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        service: 'chat-app',
        version: '2.0.0',
        timestamp: new Date().toISOString(),
        connections: io.engine.clientsCount
    });
});

// Serve uploaded files
app.use('/uploads', express.static(CONFIG.uploadDir));

// ===== Cleanup Old Messages =====
setInterval(async () => {
    try {
        const cutoffDate = new Date();
        cutoffDate.setDate(cutoffDate.getDate() - CONFIG.messageRetention);
        
        const result = await Message.deleteMany({
            createdAt: { $lt: cutoffDate }
        });
        
        console.log(`🧹 Cleaned up ${result.deletedCount} old messages`);
    } catch (error) {
        console.error('Cleanup error:', error);
    }
}, 24 * 60 * 60 * 1000); // Run daily

// ===== Error Handling =====
process.on('unhandledRejection', (reason, promise) => {
    console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

// ===== Start Server =====
server.listen(CONFIG.port, () => {
    console.log(`
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║   🚀 Rizz Chat Server                                    ║
║   Version: 2.0.0 Enhanced                                ║
║                                                          ║
║   Port: ${CONFIG.port}                                    ║
║   WebSocket: Enabled                                     ║
║   Encryption: Enabled                                    ║
║   File Upload: Enabled                                   ║
║                                                          ║
║   Ready for connections!                                 ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    `);
});

module.exports = { app, server, io };
