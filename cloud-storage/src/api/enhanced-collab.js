/**
 * Rizz Cloud Storage - Enhanced Collaboration Features
 * Features: Real-time collaboration, document editing, comments, version history
 */

const express = require('express');
const mongoose = require('mongoose');
const { Server } = require('socket.io');
const crypto = require('crypto');

const app = express();

// ===== ENHANCED MODELS =====

const FileSchema = new mongoose.Schema({
  name: { type: String, required: true },
  originalName: String,
  path: String,
  size: Number,
  mimeType: String,
  hash: String,
  
  // Organization
  parentFolder: { type: mongoose.Schema.Types.ObjectId, ref: 'Folder' },
  owner: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
  
  // Collaboration
  sharedWith: [{
    user: { type: mongoose.Schema.Types.ObjectId, ref: 'User' },
    permission: { type: String, enum: ['read', 'write', 'admin'], default: 'read' },
    sharedAt: { type: Date, default: Date.now },
    lastAccessedAt: Date
  }],
  publicLink: {
    enabled: { type: Boolean, default: false },
    token: String,
    password: String,
    expiresAt: Date,
    downloadCount: { type: Number, default: 0 },
    maxDownloads: Number,
    allowEdit: { type: Boolean, default: false }
  },
  
  // Version control
  version: { type: Number, default: 1 },
  versions: [{
    version: Number,
    path: String,
    size: Number,
    createdAt: Date,
    createdBy: mongoose.Schema.Types.ObjectId,
    changes: String
  }],
  
  // Comments
  comments: [{
    user: { type: mongoose.Schema.Types.ObjectId, ref: 'User' },
    content: String,
    resolved: { type: Boolean, default: false },
    replies: [{
      user: mongoose.Schema.Types.ObjectId,
      content: String,
      createdAt: Date
    }],
    createdAt: { type: Date, default: Date.now }
  }],
  
  // Activity
  views: { type: Number, default: 0 },
  downloads: { type: Number, default: 0 },
  lastViewedAt: Date,
  
  // Metadata
  description: String,
  tags: [String],
  starred: { type: Boolean, default: false },
  trashed: { type: Boolean, default: false },
  
  createdAt: { type: Date, default: Date.now },
  updatedAt: Date
});

// Real-time collaboration session
const CollaborationSessionSchema = new mongoose.Schema({
  file: { type: mongoose.Schema.Types.ObjectId, ref: 'File', required: true },
  users: [{
    user: mongoose.Schema.Types.ObjectId,
    joinedAt: { type: Date, default: Date.now },
    lastActiveAt: Date,
    cursor: { x: Number, y: Number },
    selection: { start: Number, end: Number }
  }],
  activeUsers: { type: Number, default: 0 },
  edits: [{
    user: mongoose.Schema.Types.ObjectId,
    operation: String,
    data: mongoose.Schema.Types.Mixed,
    timestamp: { type: Date, default: Date.now }
  }],
  createdAt: { type: Date, default: Date.now },
  endedAt: Date
});

const CollaborationSession = mongoose.model('CollaborationSession', CollaborationSessionSchema);

// Activity log
const ActivityLogSchema = new mongoose.Schema({
  user: { type: mongoose.Schema.Types.ObjectId, ref: 'User' },
  action: { 
    type: String, 
    enum: ['view', 'download', 'edit', 'share', 'delete', 'move', 'rename', 'comment', 'upload'] 
  },
  targetType: { type: String, enum: ['file', 'folder'] },
  target: mongoose.Schema.Types.ObjectId,
  targetName: String,
  metadata: mongoose.Schema.Types.Mixed,
  ipAddress: String,
  userAgent: String,
  createdAt: { type: Date, default: Date.now }
});

const ActivityLog = mongoose.model('ActivityLog', ActivityLogSchema);

const File = mongoose.model('File', FileSchema);
const Folder = mongoose.model('Folder');

// ===== COLLABORATION FEATURES =====

class CollaborationManager {
  constructor(io) {
    this.io = io;
    this.sessions = new Map();
    this.userCursors = new Map();
  }
  
  // Start collaboration session
  async startSession(fileId, userId) {
    let session = await CollaborationSession.findOne({ file: fileId, endedAt: null });
    
    if (!session) {
      session = new CollaborationSession({ file: fileId });
    }
    
    // Add user to session
    const userIndex = session.users.findIndex(u => u.user.toString() === userId.toString());
    if (userIndex === -1) {
      session.users.push({ user: userId });
    } else {
      session.users[userIndex].lastActiveAt = new Date();
    }
    
    session.activeUsers = session.users.filter(u => 
      new Date() - new Date(u.lastActiveAt) < 300000 // 5 minutes
    ).length;
    
    await session.save();
    this.sessions.set(fileId.toString(), session);
    
    return session;
  }
  
  // End collaboration session
  async endSession(fileId) {
    const session = await CollaborationSession.findOne({ file: fileId, endedAt: null });
    if (session) {
      session.endedAt = new Date();
      await session.save();
      this.sessions.delete(fileId.toString());
    }
  }
  
  // Track user cursor
  trackCursor(sessionId, userId, cursor) {
    const key = `${sessionId}:${userId}`;
    this.userCursors.set(key, cursor);
    
    // Broadcast to other users
    this.io.to(`session_${sessionId}`).emit('cursor_update', {
      userId,
      cursor
    });
  }
  
  // Track user selection
  trackSelection(sessionId, userId, selection) {
    this.io.to(`session_${sessionId}`).emit('selection_update', {
      userId,
      selection
    });
  }
  
  // Record edit operation
  async recordEdit(sessionId, userId, operation, data) {
    const session = await CollaborationSession.findById(sessionId);
    if (session) {
      session.edits.push({ user: userId, operation, data });
      await session.save();
      
      // Broadcast edit
      this.io.to(`session_${sessionId}`).emit('document_edit', {
        userId,
        operation,
        data,
        timestamp: new Date()
      });
    }
  }
  
  // Get active collaborators
  getActiveCollaborators(fileId) {
    const session = this.sessions.get(fileId.toString());
    if (!session) return [];
    
    return session.users
      .filter(u => new Date() - new Date(u.lastActiveAt) < 300000)
      .map(u => ({
        userId: u.user,
        lastActiveAt: u.lastActiveAt,
        cursor: this.userCursors.get(`${fileId}:${u.user}`)
      }));
  }
}

// ===== API ROUTES =====

// Enhanced sharing with permissions
app.post('/api/files/:id/share', async (req, res) => {
  try {
    const { email, permission, createLink, message } = req.body;
    
    const file = await File.findById(req.params.id);
    if (!file) return res.status(404).json({ error: 'File not found' });
    
    // Share with specific user
    if (email) {
      const user = await User.findOne({ email });
      if (!user) return res.status(404).json({ error: 'User not found' });
      
      const existingShare = file.sharedWith.find(s => s.user.toString() === user._id.toString());
      if (existingShare) {
        existingShare.permission = permission;
      } else {
        file.sharedWith.push({ user: user._id, permission, message });
      }
      
      await file.save();
      
      // Log activity
      await ActivityLog.create({
        user: req.user.id,
        action: 'share',
        targetType: 'file',
        target: file._id,
        targetName: file.name,
        metadata: { sharedWith: user._id, permission }
      });
      
      // Send notification (implement with notification service)
    }
    
    // Create public link
    if (createLink) {
      file.publicLink = {
        enabled: true,
        token: crypto.randomBytes(16).toString('hex'),
        expiresAt: req.body.expiresAt ? new Date(req.body.expiresAt) : null,
        password: req.body.password,
        maxDownloads: req.body.maxDownloads,
        allowEdit: req.body.allowEdit || false
      };
      await file.save();
    }
    
    res.json({ file });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Add comment to file
app.post('/api/files/:id/comments', async (req, res) => {
  try {
    const { content, parentId } = req.body;
    
    const file = await File.findById(req.params.id);
    if (!file) return res.status(404).json({ error: 'File not found' });
    
    if (parentId) {
      // Add reply to comment
      const comment = file.comments.id(parentId);
      if (comment) {
        comment.replies.push({
          user: req.user.id,
          content,
          createdAt: new Date()
        });
      }
    } else {
      // Add new comment
      file.comments.push({
        user: req.user.id,
        content
      });
    }
    
    await file.save();
    
    // Log activity
    await ActivityLog.create({
      user: req.user.id,
      action: 'comment',
      targetType: 'file',
      target: file._id,
      targetName: file.name
    });
    
    res.json({ message: 'Comment added' });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Resolve comment
app.put('/api/files/:fileId/comments/:commentId/resolve', async (req, res) => {
  try {
    const file = await File.findById(req.params.fileId);
    const comment = file.comments.id(req.params.commentId);
    
    if (!comment) return res.status(404).json({ error: 'Comment not found' });
    
    comment.resolved = true;
    await file.save();
    
    res.json({ message: 'Comment resolved' });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Get file activity log
app.get('/api/files/:id/activity', async (req, res) => {
  try {
    const { limit = 50 } = req.query;
    
    const activities = await ActivityLog.find({
      targetType: 'file',
      target: req.params.id
    })
      .populate('user', 'name email avatar')
      .sort('-createdAt')
      .limit(parseInt(limit));
    
    res.json({ activities });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Create new version
app.post('/api/files/:id/versions', async (req, res) => {
  try {
    const { path, size, changes } = req.body;
    
    const file = await File.findById(req.params.id);
    if (!file) return res.status(404).json({ error: 'File not found' });
    
    // Save current version
    file.versions.push({
      version: file.version,
      path: file.path,
      size: file.size,
      createdAt: file.updatedAt,
      createdBy: file.owner,
      changes: changes || `Version ${file.version}`
    });
    
    // Update to new version
    file.version += 1;
    file.path = path;
    file.size = size;
    file.updatedAt = new Date();
    
    await file.save();
    
    // Log activity
    await ActivityLog.create({
      user: req.user.id,
      action: 'edit',
      targetType: 'file',
      target: file._id,
      targetName: file.name,
      metadata: { version: file.version }
    });
    
    res.json({ 
      message: 'Version created', 
      version: file.version,
      versions: file.versions.slice(-10) // Last 10 versions
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Restore previous version
app.post('/api/files/:id/versions/:version/restore', async (req, res) => {
  try {
    const file = await File.findById(req.params.id);
    if (!file) return res.status(404).json({ error: 'File not found' });
    
    const version = file.versions.id(req.params.version);
    if (!version) return res.status(404).json({ error: 'Version not found' });
    
    // Save current as version
    file.versions.push({
      version: file.version,
      path: file.path,
      size: file.size,
      createdAt: new Date(),
      createdBy: req.user.id,
      changes: `Reverted from version ${file.version}`
    });
    
    // Restore to previous version
    file.version += 1;
    file.path = version.path;
    file.size = version.size;
    file.updatedAt = new Date();
    
    await file.save();
    
    res.json({ message: 'Version restored', version: file.version });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Get collaborators
app.get('/api/files/:id/collaborators', async (req, res) => {
  try {
    const file = await File.findById(req.params.id)
      .populate('sharedWith.user', 'name email avatar')
      .populate('owner', 'name email avatar');
    
    if (!file) return res.status(404).json({ error: 'File not found' });
    
    const collaborators = [
      { user: file.owner, permission: 'owner' },
      ...file.sharedWith.map(s => ({ user: s.user, permission: s.permission }))
    ];
    
    res.json({ collaborators });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Remove collaborator
app.delete('/api/files/:id/collaborators/:userId', async (req, res) => {
  try {
    const file = await File.findById(req.params.id);
    if (!file) return res.status(404).json({ error: 'File not found' });
    
    file.sharedWith = file.sharedWith.filter(
      s => s.user.toString() !== req.params.userId.toString()
    );
    
    await file.save();
    
    res.json({ message: 'Collaborator removed' });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Update collaborator permission
app.put('/api/files/:id/collaborators/:userId', async (req, res) => {
  try {
    const { permission } = req.body;
    
    const file = await File.findById(req.params.id);
    if (!file) return res.status(404).json({ error: 'File not found' });
    
    const share = file.sharedWith.find(
      s => s.user.toString() === req.params.userId.toString()
    );
    
    if (!share) return res.status(404).json({ error: 'Collaborator not found' });
    
    share.permission = permission;
    await file.save();
    
    res.json({ message: 'Permission updated' });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// ===== WEBSOCKET HANDLERS =====

function setupCollaborationSocket(io, collaborationManager) {
  io.on('connection', (socket) => {
    console.log(`Client connected: ${socket.id}`);
    
    // Join collaboration session
    socket.on('join_session', async ({ fileId, userId }) => {
      socket.join(`session_${fileId}`);
      
      const session = await collaborationManager.startSession(fileId, userId);
      
      socket.emit('session_joined', {
        sessionId: session._id,
        activeUsers: session.activeUsers,
        users: session.users
      });
      
      socket.to(`session_${fileId}`).emit('user_joined', { userId });
    });
    
    // Cursor update
    socket.on('cursor_update', ({ fileId, userId, cursor }) => {
      collaborationManager.trackCursor(fileId, userId, cursor);
    });
    
    // Selection update
    socket.on('selection_update', ({ fileId, userId, selection }) => {
      collaborationManager.trackSelection(fileId, userId, selection);
    });
    
    // Document edit
    socket.on('document_edit', async ({ fileId, userId, operation, data }) => {
      await collaborationManager.recordEdit(fileId, userId, operation, data);
    });
    
    // Typing indicator
    socket.on('typing', ({ fileId, userId }) => {
      socket.to(`session_${fileId}`).emit('user_typing', { userId });
    });
    
    // Leave session
    socket.on('leave_session', ({ fileId, userId }) => {
      socket.leave(`session_${fileId}`);
      socket.to(`session_${fileId}`).emit('user_left', { userId });
    });
    
    socket.on('disconnect', () => {
      console.log(`Client disconnected: ${socket.id}`);
    });
  });
}

// Start server
const PORT = process.env.PORT || 5003;
const server = app.listen(PORT, () => {
  console.log(`
╔════════════════════════════════════════════╗
║   ☁️ Rizz Cloud Storage - Enhanced         ║
║   Running on port ${PORT}                      ║
║                                            ║
║   Features:                                ║
║   - Real-time Collaboration                ║
║   - Document Editing                       ║
║   - Comments & Replies                     ║
║   - Version History                        ║
║   - Activity Logging                       ║
║   - Advanced Sharing                       ║
╚════════════════════════════════════════════╝
  `);
});

// Setup WebSocket
const io = new Server(server, { cors: { origin: '*' } });
const collaborationManager = new CollaborationManager(io);
setupCollaborationSocket(io, collaborationManager);

module.exports = { app, io, server, collaborationManager };
