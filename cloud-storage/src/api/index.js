/**
 * Rizz Cloud Storage - Enterprise Cloud Storage (Google Drive-like)
 * Features: File upload, sync, sharing, versioning, collaboration
 */

const express = require('express');
const mongoose = require('mongoose');
const { createServer } = require('http');
const { Server } = require('socket.io');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const jwt = require('jsonwebtoken');
const archiver = require('archiver');
const crypto = require('crypto');
require('dotenv').config();

const app = express();
const httpServer = createServer(app);
const io = new Server(httpServer, { cors: { origin: '*' } });

app.use(express.json());

// Database
mongoose.connect(process.env.MONGODB_URI || 'mongodb://localhost:27017/rizz_cloud')
  .then(() => console.log('✅ MongoDB Connected'))
  .catch(err => console.error('❌ MongoDB Error:', err));

// Storage configuration
const STORAGE_PATH = process.env.STORAGE_PATH || './storage/files';
if (!fs.existsSync(STORAGE_PATH)) {
  fs.mkdirSync(STORAGE_PATH, { recursive: true });
}

// Multer configuration
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const userId = req.user?._id || 'temp';
    const userPath = path.join(STORAGE_PATH, userId.toString());
    if (!fs.existsSync(userPath)) {
      fs.mkdirSync(userPath, { recursive: true });
    }
    cb(null, userPath);
  },
  filename: (req, file, cb) => {
    const uniqueName = `${Date.now()}-${crypto.randomBytes(8).toString('hex')}-${file.originalname}`;
    cb(null, uniqueName);
  }
});

const upload = multer({ 
  storage,
  limits: { fileSize: 10 * 1024 * 1024 * 1024 } // 10GB limit
});

// Models
const FileSchema = new mongoose.Schema({
  name: { type: String, required: true },
  originalName: String,
  path: String,
  size: Number,
  mimeType: String,
  hash: String, // For deduplication
  
  // Organization
  parentFolder: { type: mongoose.Schema.Types.ObjectId, ref: 'Folder', default: null },
  owner: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
  
  // Sharing
  sharedWith: [{
    user: { type: mongoose.Schema.Types.ObjectId, ref: 'User' },
    permission: { type: String, enum: ['read', 'write', 'admin'], default: 'read' },
    sharedAt: { type: Date, default: Date.now }
  }],
  publicLink: {
    enabled: { type: Boolean, default: false },
    token: String,
    expiresAt: Date,
    password: String,
    downloadCount: { type: Number, default: 0 },
    maxDownloads: Number
  },
  
  // Versioning
  version: { type: Number, default: 1 },
  versions: [{
    path: String,
    size: Number,
    version: Number,
    createdAt: Date,
    createdBy: mongoose.Schema.Types.ObjectId
  }],
  
  // Metadata
  description: String,
  tags: [String],
  starred: { type: Boolean, default: false },
  trashed: { type: Boolean, default: false },
  trashedAt: Date,
  
  // Sync
  synced: { type: Boolean, default: true },
  lastSyncedAt: Date,
  
  // Activity
  views: { type: Number, default: 0 },
  downloads: { type: Number, default: 0 },
  
  createdAt: { type: Date, default: Date.now },
  updatedAt: Date,
  deletedAt: Date
});

const FolderSchema = new mongoose.Schema({
  name: { type: String, required: true },
  parentFolder: { type: mongoose.Schema.Types.ObjectId, ref: 'Folder', default: null },
  owner: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
  color: String,
  icon: String,
  
  // Sharing
  sharedWith: [{
    user: { type: mongoose.Schema.Types.ObjectId, ref: 'User' },
    permission: { type: String, enum: ['read', 'write', 'admin'], default: 'read' }
  }],
  
  // Organization
  starred: { type: Boolean, default: false },
  trashed: { type: Boolean, default: false },
  
  createdAt: { type: Date, default: Date.now },
  updatedAt: Date
});

const UserSchema = new mongoose.Schema({
  email: { type: String, unique: true, required: true },
  password: { type: String, required: true },
  username: String,
  avatar: String,
  
  // Storage quota
  storageQuota: {
    total: { type: Number, default: 15 * 1024 * 1024 * 1024 }, // 15GB free
    used: { type: Number, default: 0 }
  },
  
  // Subscription
  subscription: {
    plan: { type: String, enum: ['free', 'basic', 'pro', 'business'], default: 'free' },
    storage: Number,
    expiresAt: Date
  },
  
  // Settings
  settings: {
    theme: { type: String, enum: ['light', 'dark', 'auto'], default: 'dark' },
    defaultView: { type: String, enum: ['list', 'grid'], default: 'grid' },
    autoSync: { type: Boolean, default: true },
    trashRetention: { type: Number, default: 30 } // days
  },
  
  // Activity
  lastActiveAt: Date,
  
  createdAt: { type: Date, default: Date.now }
});

const ActivitySchema = new mongoose.Schema({
  user: { type: mongoose.Schema.Types.ObjectId, ref: 'User' },
  action: { type: String, enum: ['upload', 'download', 'delete', 'share', 'move', 'rename', 'edit'] },
  targetType: { type: String, enum: ['file', 'folder'] },
  target: mongoose.Schema.Types.ObjectId,
  targetName: String,
  metadata: mongoose.Schema.Types.Mixed,
  createdAt: { type: Date, default: Date.now }
});

const File = mongoose.model('File', FileSchema);
const Folder = mongoose.model('Folder', FolderSchema);
const User = mongoose.model('User', UserSchema);
const Activity = mongoose.model('Activity', ActivitySchema);

// Auth Middleware
const auth = async (req, res, next) => {
  try {
    const token = req.headers.authorization?.split(' ')[1];
    if (!token) return res.status(401).json({ error: 'No token' });
    
    const decoded = jwt.verify(token, process.env.JWT_SECRET || 'secret');
    req.user = await User.findById(decoded.userId);
    next();
  } catch (error) {
    res.status(401).json({ error: 'Invalid token' });
  }
};

// ===== API ROUTES =====

// Auth
app.post('/api/auth/register', async (req, res) => {
  try {
    const { email, password, username } = req.body;
    const bcrypt = require('bcryptjs');
    const hashedPassword = await bcrypt.hash(password, 10);
    
    const user = new User({ email, password: hashedPassword, username });
    await user.save();
    
    const token = jwt.sign({ userId: user._id }, process.env.JWT_SECRET || 'secret', { expiresIn: '30d' });
    res.status(201).json({ token, user });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/auth/login', async (req, res) => {
  try {
    const { email, password } = req.body;
    const user = await User.findOne({ email });
    
    if (!user || !(await require('bcryptjs').compare(password, user.password))) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }
    
    const token = jwt.sign({ userId: user._id }, process.env.JWT_SECRET || 'secret', { expiresIn: '30d' });
    user.lastActiveAt = new Date();
    await user.save();
    
    res.json({ token, user });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// User storage info
app.get('/api/me/storage', auth, async (req, res) => {
  try {
    const user = await User.findById(req.user._id);
    
    const fileStats = await File.aggregate([
      { $match: { owner: user._id, trashed: false } },
      { $group: { _id: null, totalSize: { $sum: '$size' }, count: { $sum: 1 } } }
    ]);
    
    const used = fileStats[0]?.totalSize || 0;
    const count = fileStats[0]?.count || 0;
    
    res.json({
      used,
      total: user.storageQuota.total,
      available: user.storageQuota.total - used,
      fileCount: count,
      percentage: (used / user.storageQuota.total) * 100
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Files
app.get('/api/files', auth, async (req, res) => {
  try {
    const { folder, starred, trashed, search, sort = '-createdAt' } = req.query;
    const query = { owner: req.user._id, trashed: trashed === 'true' };
    
    if (folder) query.parentFolder = folder === 'root' ? null : folder;
    if (starred === 'true') query.starred = true;
    if (search) query.name = { $regex: search, $options: 'i' };
    
    const files = await File.find(query)
      .populate('parentFolder', 'name')
      .sort(sort);
    
    res.json(files);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Upload file
app.post('/api/files/upload', auth, upload.single('file'), async (req, res) => {
  try {
    const { parentFolder, description, tags } = req.body;
    
    if (!req.file) {
      return res.status(400).json({ error: 'No file uploaded' });
    }
    
    const file = new File({
      name: req.file.filename,
      originalName: req.file.originalname,
      path: req.file.path,
      size: req.file.size,
      mimeType: req.file.mimetype,
      owner: req.user._id,
      parentFolder: parentFolder === 'root' ? null : parentFolder,
      description,
      tags: tags ? tags.split(',').map(t => t.trim()) : []
    });
    
    await file.save();
    
    // Update user storage
    await User.findByIdAndUpdate(req.user._id, {
      $inc: { 'storageQuota.used': req.file.size }
    });
    
    // Log activity
    await Activity.create({
      user: req.user._id,
      action: 'upload',
      targetType: 'file',
      target: file._id,
      targetName: file.originalName
    });
    
    // Notify via socket
    io.to(`user_${req.user._id}`).emit('file_uploaded', { file });
    
    res.status(201).json(file);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Download file
app.get('/api/files/:id/download', auth, async (req, res) => {
  try {
    const file = await File.findById(req.params.id);
    
    if (!file || (file.owner.toString() !== req.user._id.toString() && 
        !file.sharedWith.some(s => s.user.toString() === req.user._id.toString()))) {
      return res.status(404).json({ error: 'File not found' });
    }
    
    file.downloads += 1;
    await file.save();
    
    res.download(file.path, file.originalName);
    
    await Activity.create({
      user: req.user._id,
      action: 'download',
      targetType: 'file',
      target: file._id,
      targetName: file.originalName
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Share file
app.post('/api/files/:id/share', auth, async (req, res) => {
  try {
    const { email, permission, createLink } = req.body;
    const file = await File.findById(req.params.id);
    
    if (!file || file.owner.toString() !== req.user._id.toString()) {
      return res.status(404).json({ error: 'File not found' });
    }
    
    if (email) {
      const user = await User.findOne({ email });
      if (!user) return res.status(404).json({ error: 'User not found' });
      
      file.sharedWith.push({ user: user._id, permission });
      await file.save();
      
      // Notify user
      io.to(`user_${user._id}`).emit('file_shared', { file: file._id, from: req.user._id });
    }
    
    if (createLink) {
      file.publicLink = {
        enabled: true,
        token: crypto.randomBytes(16).toString('hex'),
        expiresAt: req.body.expiresAt ? new Date(req.body.expiresAt) : null
      };
      await file.save();
    }
    
    res.json(file);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Create folder
app.post('/api/folders', auth, async (req, res) => {
  try {
    const { name, parentFolder, color, icon } = req.body;
    
    const folder = new Folder({
      name,
      parentFolder: parentFolder === 'root' ? null : parentFolder,
      owner: req.user._id,
      color,
      icon
    });
    
    await folder.save();
    res.status(201).json(folder);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Get folders
app.get('/api/folders', auth, async (req, res) => {
  try {
    const { parent, trashed } = req.query;
    const query = { owner: req.user._id, trashed: trashed === 'true' };
    
    if (parent) query.parentFolder = parent === 'root' ? null : parent;
    
    const folders = await Folder.find(query).sort('name');
    res.json(folders);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Download folder as ZIP
app.get('/api/folders/:id/download', auth, async (req, res) => {
  try {
    const folder = await Folder.findById(req.params.id);
    
    if (!folder || folder.owner.toString() !== req.user._id.toString()) {
      return res.status(404).json({ error: 'Folder not found' });
    }
    
    const files = await File.find({ parentFolder: folder._id, owner: req.user._id });
    
    const archive = archiver('zip', { zlib: { level: 9 } });
    
    res.attachment(`${folder.name}.zip`);
    archive.pipe(res);
    
    files.forEach(file => {
      if (fs.existsSync(file.path)) {
        archive.file(file.path, { name: file.originalName });
      }
    });
    
    archive.finalize();
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Activity log
app.get('/api/activity', auth, async (req, res) => {
  try {
    const activities = await Activity.find({ user: req.user._id })
      .sort('-createdAt')
      .limit(100);
    
    res.json(activities);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Search
app.get('/api/search', auth, async (req, res) => {
  try {
    const { q, type } = req.query;
    
    const query = { 
      owner: req.user._id,
      trashed: false,
      $or: [
        { name: { $regex: q, $options: 'i' } },
        { originalName: { $regex: q, $options: 'i' } },
        { description: { $regex: q, $options: 'i' } }
      ]
    };
    
    let results = [];
    
    if (!type || type === 'file') {
      const files = await File.find(query).limit(50);
      results.push(...files.map(f => ({ ...f.toObject(), type: 'file' })));
    }
    
    if (!type || type === 'folder') {
      const folders = await Folder.find({ 
        owner: req.user._id, 
        name: { $regex: q, $options: 'i' },
        trashed: false 
      }).limit(50);
      results.push(...folders.map(f => ({ ...f.toObject(), type: 'folder' })));
    }
    
    res.json(results);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// ===== Socket.io Real-time =====
io.on('connection', (socket) => {
  console.log(`Client connected: ${socket.id}`);
  
  socket.on('authenticate', (userId) => {
    socket.join(`user_${userId}`);
  });
  
  socket.on('file_operation', async (data) => {
    // Broadcast file changes to other devices
    socket.to(`user_${data.userId}`).emit('file_updated', data);
  });
  
  socket.on('disconnect', () => {
    console.log(`Client disconnected: ${socket.id}`);
  });
});

// Start Server
const PORT = process.env.PORT || 5003;
httpServer.listen(PORT, () => {
  console.log(`
╔════════════════════════════════════════════╗
║   ☁️ Rizz Cloud Storage                    ║
║   Running on port ${PORT}                      ║
║                                            ║
║   Features:                                ║
║   - File Upload (10GB limit)               ║
║   - Folder Organization                    ║
║   - File Sharing & Collaboration           ║
║   - Version Control                        ║
║   - Real-time Sync                         ║
║   - Activity Logging                       ║
╚════════════════════════════════════════════╝
  `);
});

module.exports = { app, io };
