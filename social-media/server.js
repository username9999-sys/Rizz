/**
 * Rizz Social Media Platform
 * Features: Posts, Stories, Messages, Notifications, Live Streaming
 */

const express = require('express');
const mongoose = require('mongoose');
const { createServer } = require('http');
const { Server } = require('socket.io');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
require('dotenv').config();

const app = express();
const httpServer = createServer(app);
const io = new Server(httpServer, { cors: { origin: '*' } });

app.use(express.json());

// Database
mongoose.connect(process.env.MONGODB_URI || 'mongodb://localhost:27017/rizz_social')
  .then(() => console.log('✅ MongoDB Connected'))
  .catch(err => console.error('❌ MongoDB Error:', err));

// Models
const UserSchema = new mongoose.Schema({
  username: { type: String, unique: true, required: true },
  email: { type: String, unique: true, required: true },
  password: { type: String, required: true },
  displayName: String,
  bio: String,
  avatar: String,
  cover: String,
  verified: { type: Boolean, default: false },
  followers: [{ type: mongoose.Schema.Types.ObjectId, ref: 'User' }],
  following: [{ type: mongoose.Schema.Types.ObjectId, ref: 'User' }],
  posts: [{ type: mongoose.Schema.Types.ObjectId, ref: 'Post' }],
  saved: [{ type: mongoose.Schema.Types.ObjectId, ref: 'Post' }],
  privacy: {
    privateAccount: { type: Boolean, default: false },
    showActivity: { type: Boolean, default: true }
  }
}, { timestamps: true });

const PostSchema = new mongoose.Schema({
  author: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
  content: String,
  media: [{
    type: { type: String, enum: ['image', 'video', 'gif'] },
    url: String,
    thumbnail: String
  }],
  tags: [String],
  mentions: [{ type: mongoose.Schema.Types.ObjectId, ref: 'User' }],
  location: {
    name: String,
    coordinates: { type: [Number], index: '2dsphere' }
  },
  likes: [{ type: mongoose.Schema.Types.ObjectId, ref: 'User' }],
  comments: [{
    user: { type: mongoose.Schema.Types.ObjectId, ref: 'User' },
    content: String,
    likes: [{ type: mongoose.Schema.Types.ObjectId, ref: 'User' }],
    createdAt: { type: Date, default: Date.now }
  }],
  shares: [{ type: mongoose.Schema.Types.ObjectId, ref: 'Post' }],
  type: { type: String, enum: ['post', 'story', 'reel'], default: 'post' },
  visibility: { type: String, enum: ['public', 'friends', 'private'], default: 'public' },
  expiresAt: Date // For stories
}, { timestamps: true });

const MessageSchema = new mongoose.Schema({
  conversation: { type: mongoose.Schema.Types.ObjectId, ref: 'Conversation' },
  sender: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
  content: String,
  media: [{ type: String, url: String }],
  read: { type: Boolean, default: false },
  deleted: { type: Boolean, default: false }
}, { timestamps: true });

const ConversationSchema = new mongoose.Schema({
  participants: [{ type: mongoose.Schema.Types.ObjectId, ref: 'User' }],
  type: { type: String, enum: ['direct', 'group'], default: 'direct' },
  name: String,
  avatar: String,
  lastMessage: { type: mongoose.Schema.Types.ObjectId, ref: 'Message' },
  unreadCount: { type: Map, of: Number, default: {} }
}, { timestamps: true });

const NotificationSchema = new mongoose.Schema({
  recipient: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
  sender: { type: mongoose.Schema.Types.ObjectId, ref: 'User' },
  type: { type: String, enum: ['like', 'comment', 'follow', 'mention', 'message', 'share'] },
  post: { type: mongoose.Schema.Types.ObjectId, ref: 'Post' },
  read: { type: Boolean, default: false }
}, { timestamps: true });

const User = mongoose.model('User', UserSchema);
const Post = mongoose.model('Post', PostSchema);
const Message = mongoose.model('Message', MessageSchema);
const Conversation = mongoose.model('Conversation', ConversationSchema);
const Notification = mongoose.model('Notification', NotificationSchema);

// Auth Middleware
const auth = async (req, res, next) => {
  try {
    const token = req.headers.authorization?.split(' ')[1];
    if (!token) return res.status(401).json({ error: 'No token' });
    
    const decoded = jwt.verify(token, process.env.JWT_SECRET || 'secret');
    req.user = await User.findById(decoded.userId).select('-password');
    next();
  } catch (error) {
    res.status(401).json({ error: 'Invalid token' });
  }
};

// Routes

// Auth
app.post('/api/auth/register', async (req, res) => {
  try {
    const { username, email, password, displayName } = req.body;
    const hashedPassword = await bcrypt.hash(password, 10);
    
    const user = new User({ username, email, password: hashedPassword, displayName });
    await user.save();
    
    const token = jwt.sign({ userId: user._id }, process.env.JWT_SECRET || 'secret', { expiresIn: '7d' });
    res.status(201).json({ token, user });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/auth/login', async (req, res) => {
  try {
    const { username, password } = req.body;
    const user = await User.findOne({ $or: [{ username }, { email: username }] });
    
    if (!user || !(await bcrypt.compare(password, user.password))) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }
    
    const token = jwt.sign({ userId: user._id }, process.env.JWT_SECRET || 'secret', { expiresIn: '7d' });
    res.json({ token, user });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Feed
app.get('/api/feed', auth, async (req, res) => {
  try {
    const following = await User.findById(req.user._id).populate('following');
    const userIds = [req.user._id, ...following.following.map(u => u._id)];
    
    const posts = await Post.find({
      author: { $in: userIds },
      type: 'post',
      expiresAt: { $exists: false }
    })
      .populate('author', 'username displayName avatar verified')
      .sort('-createdAt')
      .limit(50);
    
    res.json(posts);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Create Post
app.post('/api/posts', auth, async (req, res) => {
  try {
    const { content, media, tags, mentions, type, visibility } = req.body;
    
    const post = new Post({
      author: req.user._id,
      content,
      media,
      tags,
      mentions,
      type: type || 'post',
      visibility: visibility || 'public'
    });
    
    if (type === 'story') {
      post.expiresAt = new Date(Date.now() + 24 * 60 * 60 * 1000); // 24 hours
    }
    
    await post.save();
    await User.findByIdAndUpdate(req.user._id, { $push: { posts: post._id } });
    
    // Notify followers
    const user = await User.findById(req.user._id);
    for (const followerId of user.followers) {
      await Notification.create({
        recipient: followerId,
        sender: req.user._id,
        type: 'post',
        post: post._id
      });
    }
    
    io.emit('new_post', { postId: post._id, authorId: req.user._id });
    res.status(201).json(post);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Like Post
app.post('/api/posts/:id/like', auth, async (req, res) => {
  try {
    const post = await Post.findById(req.params.id);
    if (!post) return res.status(404).json({ error: 'Post not found' });
    
    const likedIndex = post.likes.indexOf(req.user._id);
    if (likedIndex === -1) {
      post.likes.push(req.user._id);
      
      // Create notification
      await Notification.create({
        recipient: post.author,
        sender: req.user._id,
        type: 'like',
        post: post._id
      });
      
      io.to(`user_${post.author}`).emit('notification', { type: 'like', from: req.user._id });
    } else {
      post.likes.splice(likedIndex, 1);
    }
    
    await post.save();
    res.json(post);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Follow User
app.post('/api/users/:id/follow', auth, async (req, res) => {
  try {
    const targetUser = await User.findById(req.params.id);
    if (!targetUser) return res.status(404).json({ error: 'User not found' });
    
    const followingIndex = req.user.following.indexOf(targetUser._id);
    if (followingIndex === -1) {
      req.user.following.push(targetUser._id);
      targetUser.followers.push(req.user._id);
      
      await Notification.create({
        recipient: targetUser._id,
        sender: req.user._id,
        type: 'follow'
      });
      
      io.to(`user_${targetUser._id}`).emit('notification', { type: 'follow', from: req.user._id });
    } else {
      req.user.following.splice(followingIndex, 1);
      targetUser.followers.splice(targetUser.followers.indexOf(req.user._id), 1);
    }
    
    await req.user.save();
    await targetUser.save();
    res.json({ following: req.user.following });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Get Notifications
app.get('/api/notifications', auth, async (req, res) => {
  try {
    const notifications = await Notification.find({ recipient: req.user._id })
      .populate('sender', 'username displayName avatar')
      .populate('post', 'content media')
      .sort('-createdAt')
      .limit(50);
    
    await Notification.updateMany(
      { recipient: req.user._id, read: false },
      { read: true }
    );
    
    res.json(notifications);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Socket.io
io.on('connection', (socket) => {
  console.log(`User connected: ${socket.id}`);
  
  socket.on('user_online', (userId) => {
    socket.join(`user_${userId}`);
    io.emit('user_status', { userId, online: true });
  });
  
  socket.on('send_message', async (data) => {
    try {
      const { conversationId, senderId, content, media } = data;
      
      const message = new Message({
        conversation: conversationId,
        sender: senderId,
        content,
        media
      });
      
      await message.save();
      await Conversation.findByIdAndUpdate(conversationId, { lastMessage: message._id });
      
      const conversation = await Conversation.findById(conversationId).populate('participants');
      socket.to(`conversation_${conversationId}`).emit('new_message', {
        message,
        conversationId
      });
      
      // Notify recipients
      for (const participant of conversation.participants) {
        if (participant._id.toString() !== senderId) {
          io.to(`user_${participant._id}`).emit('notification', {
            type: 'message',
            from: senderId,
            conversationId
          });
        }
      }
    } catch (error) {
      console.error('Message error:', error);
    }
  });
  
  socket.on('join_conversation', (conversationId) => {
    socket.join(`conversation_${conversationId}`);
  });
  
  socket.on('typing', (data) => {
    socket.to(`conversation_${data.conversationId}`).emit('user_typing', {
      userId: data.userId,
      conversationId: data.conversationId
    });
  });
  
  socket.on('disconnect', () => {
    console.log(`User disconnected: ${socket.id}`);
  });
});

// Start Server
const PORT = process.env.PORT || 4001;
httpServer.listen(PORT, () => {
  console.log(`
╔════════════════════════════════════════════╗
║   📱 Rizz Social Media Platform            ║
║   Running on port ${PORT}                      ║
║                                            ║
║   Features:                                ║
║   - Posts & Stories                        ║
║   - Real-time Messaging                    ║
║   - Notifications                          ║
║   - Live Streaming Ready                   ║
╚════════════════════════════════════════════╝
  `);
});
