/**
 * Rizz Social Media - Enhanced with Stories & Reels
 * Features: Stories, Reels, Live streaming, Shopping, Analytics
 */

const express = require('express');
const mongoose = require('mongoose');
const { createServer } = require('http');
const { Server } = require('socket.io');

const app = express();
const httpServer = createServer(app);
const io = new Server(httpServer, { cors: { origin: '*' } });

app.use(express.json());

mongoose.connect(process.env.MONGODB_URI || 'mongodb://localhost:27017/rizz_social_enhanced');

// ===== ENHANCED MODELS =====

// Stories (24hr expiry)
const StorySchema = new mongoose.Schema({
  user: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
  media: [{
    type: { type: String, enum: ['image', 'video'] },
    url: String,
    duration: Number,
    thumbnail: String
  }],
  captions: [{
    text: String,
    position: { x: Number, y: Number },
    style: String
  }],
  stickers: [{
    type: String,
    position: { x: Number, y: Number },
    data: mongoose.Schema.Types.Mixed
  }],
  views: [{
    user: mongoose.Schema.Types.ObjectId,
    viewedAt: { type: Date, default: Date.now }
  }],
  replies: [{
    user: mongoose.Schema.Types.ObjectId,
    text: String,
    createdAt: { type: Date, default: Date.now }
  }],
  expiresAt: Date,
  createdAt: { type: Date, default: Date.now }
});

// Auto-delete after 24 hours
StorySchema.index({ expiresAt: 1 }, { expireAfterSeconds: 0 });

// Reels (Short videos)
const ReelSchema = new mongoose.Schema({
  user: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
  video: {
    url: String,
    duration: Number, // seconds
    thumbnail: String,
    quality: [{
      resolution: String,
      url: String,
      bitrate: Number
    }]
  },
  audio: {
    title: String,
    artist: String,
    url: String,
    duration: Number
  },
  caption: String,
  hashtags: [String],
  mentions: [mongoose.Schema.Types.ObjectId],
  location: {
    name: String,
    coordinates: [Number] // [lng, lat]
  },
  
  // Engagement
  likes: [{ type: mongoose.Schema.Types.ObjectId, ref: 'User' }],
  comments: [{
    user: mongoose.Schema.Types.ObjectId,
    text: String,
    likes: Number,
    replies: [{
      user: mongoose.Schema.Types.ObjectId,
      text: String,
      createdAt: Date
    }],
    createdAt: { type: Date, default: Date.now }
  }],
  shares: [{
    user: mongoose.Schema.Types.ObjectId,
    sharedAt: { type: Date, default: Date.now }
  }],
  saves: [{ type: mongoose.Schema.Types.ObjectId, ref: 'User' }],
  
  // Analytics
  views: { type: Number, default: 0 },
  playCount: { type: Number, default: 0 },
  avgWatchTime: Number,
  completionRate: Number,
  
  // Effects & Filters
  effects: [String],
  filter: String,
  
  // Shopping tags
  productTags: [{
    product: mongoose.Schema.Types.ObjectId,
    position: { x: Number, y: Number },
    price: String
  }],
  
  createdAt: { type: Date, default: Date.now }
});

// Live Streaming Enhanced
const LiveStreamSchema = new mongoose.Schema({
  user: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
  title: { type: String, required: true },
  description: String,
  
  // Stream info
  rtmpKey: String,
  hlsUrl: String,
  status: { type: String, enum: ['scheduled', 'live', 'ended'], default: 'live' },
  
  // Viewers
  viewers: { type: Number, default: 0 },
  peakViewers: { type: Number, default: 0 },
  totalViews: { type: Number, default: 0 },
  
  // Live features
  chatEnabled: { type: Boolean, default: true },
  giftsEnabled: { type: Boolean, default: true },
  donationsEnabled: { type: Boolean, default: true },
  
  // Gifts & Donations
  gifts: [{
    user: mongoose.Schema.Types.ObjectId,
    gift: String,
    value: Number,
    timestamp: Date
  }],
  donations: [{
    user: mongoose.Schema.Types.ObjectId,
    amount: Number,
    message: String,
    timestamp: Date
  }],
  
  // Moderation
  moderators: [mongoose.Schema.Types.ObjectId],
  blockedUsers: [mongoose.Schema.Types.ObjectId],
  
  scheduledAt: Date,
  startedAt: Date,
  endedAt: Date,
  duration: Number,
  
  createdAt: { type: Date, default: Date.now }
});

// Shopping Post
const ShoppingPostSchema = new mongoose.Schema({
  user: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
  products: [{
    product: { type: mongoose.Schema.Types.ObjectId, ref: 'Product' },
    position: { x: Number, y: Number }
  }],
  media: [{
    type: String,
    url: String,
    thumbnail: String
  }],
  caption: String,
  
  // Shopping analytics
  clicks: Number,
  purchases: Number,
  revenue: Number,
  
  createdAt: { type: Date, default: Date.now }
});

const Story = mongoose.model('Story', StorySchema);
const Reel = mongoose.model('Reel', ReelSchema);
const LiveStream = mongoose.model('LiveStream', LiveStreamSchema);
const ShoppingPost = mongoose.model('ShoppingPost', ShoppingPostSchema);

// ===== API ROUTES =====

// Stories
app.post('/api/stories', async (req, res) => {
  try {
    const { userId, media, captions, stickers } = req.body;
    
    const story = new Story({
      user: userId,
      media,
      captions,
      stickers,
      expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000) // 24 hours
    });
    
    await story.save();
    
    // Notify followers via socket
    io.emit('new_story', { userId, storyId: story._id });
    
    res.status(201).json({ story });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/stories/:userId', async (req, res) => {
  try {
    const stories = await Story.find({
      user: req.params.userId,
      expiresAt: { $gt: new Date() }
    }).sort('-createdAt');
    
    res.json({ stories });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/stories/:id/view', async (req, res) => {
  try {
    const { userId } = req.body;
    
    const story = await Story.findById(req.params.id);
    if (!story) return res.status(404).json({ error: 'Story not found' });
    
    story.views.push({ user: userId });
    await story.save();
    
    res.json({ views: story.views.length });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/stories/:id/reply', async (req, res) => {
  try {
    const { userId, text } = req.body;
    
    const story = await Story.findById(req.params.id);
    if (!story) return res.status(404).json({ error: 'Story not found' });
    
    story.replies.push({ user: userId, text });
    await story.save();
    
    // Notify story owner
    io.to(`user_${story.user}`).emit('story_reply', {
      storyId: story._id,
      reply: { user: userId, text }
    });
    
    res.json({ reply: story.replies[story.replies.length - 1] });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Reels
app.post('/api/reels', async (req, res) => {
  try {
    const { userId, video, audio, caption, hashtags, mentions, effects } = req.body;
    
    const reel = new Reel({
      user: userId,
      video,
      audio,
      caption,
      hashtags,
      mentions,
      effects
    });
    
    await reel.save();
    
    res.status(201).json({ reel });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/reels', async (req, res) => {
  try {
    const { limit = 20, hashtag, userId } = req.query;
    const query = {};
    
    if (hashtag) query.hashtags = hashtag;
    if (userId) query.user = userId;
    
    const reels = await Reel.find(query)
      .populate('user', 'username avatar')
      .sort('-createdAt')
      .limit(parseInt(limit));
    
    res.json({ reels });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/reels/:id/like', async (req, res) => {
  try {
    const { userId } = req.body;
    
    const reel = await Reel.findById(req.params.id);
    if (!reel) return res.status(404).json({ error: 'Reel not found' });
    
    const likedIndex = reel.likes.indexOf(userId);
    if (likedIndex === -1) {
      reel.likes.push(userId);
    } else {
      reel.likes.splice(likedIndex, 1);
    }
    
    await reel.save();
    
    res.json({ likes: reel.likes.length });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Live Streaming
app.post('/api/live', async (req, res) => {
  try {
    const { userId, title, description, scheduledAt } = req.body;
    
    const liveStream = new LiveStream({
      user: userId,
      title,
      description,
      rtmpKey: Math.random().toString(36).substring(7),
      scheduledAt: scheduledAt ? new Date(scheduledAt) : null,
      status: scheduledAt ? 'scheduled' : 'live'
    });
    
    await liveStream.save();
    
    // Notify followers
    io.emit('live_stream_started', {
      userId,
      streamId: liveStream._id,
      title
    });
    
    res.status(201).json({ liveStream });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/live/:id/gift', async (req, res) => {
  try {
    const { userId, gift, value } = req.body;
    
    const liveStream = await LiveStream.findById(req.params.id);
    if (!liveStream) return res.status(404).json({ error: 'Stream not found' });
    
    liveStream.gifts.push({ user: userId, gift, value, timestamp: new Date() });
    await liveStream.save();
    
    // Notify streamer
    io.to(`live_${liveStream._id}`).emit('gift_received', {
      from: userId,
      gift,
      value
    });
    
    res.json({ message: 'Gift sent!' });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Shopping Posts
app.post('/api/shopping', async (req, res) => {
  try {
    const { userId, products, media, caption } = req.body;
    
    const post = new ShoppingPost({
      user: userId,
      products,
      media,
      caption
    });
    
    await post.save();
    
    res.status(201).json({ post });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/shopping/analytics/:id', async (req, res) => {
  try {
    const post = await ShoppingPost.findById(req.params.id)
      .populate('products.product');
    
    if (!post) return res.status(404).json({ error: 'Post not found' });
    
    res.json({
      clicks: post.clicks || 0,
      purchases: post.purchases || 0,
      revenue: post.revenue || 0,
      conversionRate: post.purchases / (post.clicks || 1) * 100
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// ===== WEBSOCKET HANDLERS =====

io.on('connection', (socket) => {
  console.log(`Client connected: ${socket.id}`);
  
  // Join user room
  socket.on('join_user', (userId) => {
    socket.join(`user_${userId}`);
  });
  
  // Join live stream
  socket.on('join_live', async (streamId) => {
    socket.join(`live_${streamId}`);
    
    const stream = await LiveStream.findById(streamId);
    if (stream) {
      stream.viewers += 1;
      if (stream.viewers > stream.peakViewers) {
        stream.peakViewers = stream.viewers;
      }
      await stream.save();
      
      io.to(`live_${streamId}`).emit('viewers_update', stream.viewers);
    }
  });
  
  // Live chat
  socket.on('live_chat', (data) => {
    io.to(`live_${data.streamId}`).emit('chat_message', {
      user: data.userId,
      message: data.message,
      timestamp: new Date()
    });
  });
  
  socket.on('disconnect', () => {
    console.log(`Client disconnected: ${socket.id}`);
  });
});

// Start server
const PORT = process.env.PORT || 4001;
httpServer.listen(PORT, () => {
  console.log(`
╔════════════════════════════════════════════╗
║   📱 Rizz Social Media - Enhanced          ║
║   Running on port ${PORT}                      ║
║                                            ║
║   Features:                                ║
║   - Stories (24hr)                         ║
║   - Reels (Short videos)                   ║
║   - Live Streaming                         ║
║   - Shopping Posts                         ║
║   - Gifts & Donations                      ║
╚════════════════════════════════════════════╝
  `);
});

module.exports = { app, io };
