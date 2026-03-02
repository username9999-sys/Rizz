/**
 * Rizz CRM Platform - Enterprise Customer Relationship Management
 * Features: Contact management, deals pipeline, tasks, analytics
 */

const express = require('express');
const mongoose = require('mongoose');
const { createServer } = require('http');
const { Server } = require('socket.io');
const jwt = require('jsonwebtoken');
const Bull = require('bull');
require('dotenv').config();

const app = express();
const httpServer = createServer(app);
const io = new Server(httpServer, { cors: { origin: '*' } });

app.use(express.json());

// Database
mongoose.connect(process.env.MONGODB_URI || 'mongodb://localhost:27017/rizz_crm')
  .then(() => console.log('✅ MongoDB Connected'))
  .catch(err => console.error('❌ MongoDB Error:', err));

// Redis for queues
const emailQueue = new Bull('email-queue', {
  redis: process.env.REDIS_URL || 'redis://localhost:6379'
});

const taskQueue = new Bull('task-queue', {
  redis: process.env.REDIS_URL || 'redis://localhost:6379'
});

// ===== MODELS =====

const ContactSchema = new mongoose.Schema({
  firstName: { type: String, required: true },
  lastName: { type: String, required: true },
  email: { type: String, unique: true },
  phone: String,
  company: String,
  position: String,
  
  // Lead information
  source: { type: String, enum: ['website', 'referral', 'social', 'email', 'event', 'other'] },
  status: { type: String, enum: ['lead', 'prospect', 'customer', 'inactive'], default: 'lead' },
  leadScore: { type: Number, default: 0 },
  
  // Social media
  socialProfiles: {
    linkedin: String,
    twitter: String,
    facebook: String
  },
  
  // Address
  address: {
    street: String,
    city: String,
    state: String,
    zip: String,
    country: String
  },
  
  // Tags & notes
  tags: [String],
  notes: [{
    content: String,
    createdBy: mongoose.Schema.Types.ObjectId,
    createdAt: { type: Date, default: Date.now }
  }],
  
  // Custom fields
  customFields: mongoose.Schema.Types.Mixed,
  
  // Owner
  ownerId: mongoose.Schema.Types.ObjectId,
  assignedTo: mongoose.Schema.Types.ObjectId,
  
  // Activity
  lastContactedAt: Date,
  nextFollowUpAt: Date,
  
  createdAt: { type: Date, default: Date.now },
  updatedAt: Date
});

const DealSchema = new mongoose.Schema({
  title: { type: String, required: true },
  description: String,
  value: { type: Number, required: true },
  currency: { type: String, default: 'USD' },
  
  // Pipeline
  stage: { 
    type: String, 
    enum: ['new', 'contacted', 'qualified', 'proposal', 'negotiation', 'closed_won', 'closed_lost'],
    default: 'new'
  },
  probability: { type: Number, default: 0 }, // 0-100
  pipeline: String,
  
  // Related entities
  contactId: mongoose.Schema.Types.ObjectId,
  companyId: mongoose.Schema.Types.ObjectId,
  
  // Timeline
  expectedCloseDate: Date,
  closedDate: Date,
  closedReason: String,
  
  // Products/Services
  products: [{
    name: String,
    quantity: Number,
    price: Number,
    total: Number
  }],
  
  // Owner
  ownerId: mongoose.Schema.Types.ObjectId,
  assignedTo: mongoose.Schema.Types.ObjectId,
  
  // Activity
  tasks: [{
    title: String,
    completed: { type: Boolean, default: false },
    dueDate: Date,
    completedAt: Date
  }],
  
  tags: [String],
  notes: [{
    content: String,
    createdBy: mongoose.Schema.Types.ObjectId,
    createdAt: { type: Date, default: Date.now }
  }],
  
  createdAt: { type: Date, default: Date.now },
  updatedAt: Date
});

const CompanySchema = new mongoose.Schema({
  name: { type: String, required: true },
  domain: String,
  industry: String,
  size: { type: String, enum: ['1-10', '11-50', '51-200', '201-500', '500+'] },
  type: { type: String, enum: ['public', 'private', 'nonprofit', 'government'] },
  
  // Contact info
  email: String,
  phone: String,
  website: String,
  
  // Address
  address: {
    street: String,
    city: String,
    state: String,
    zip: String,
    country: String
  },
  
  // Social
  socialProfiles: {
    linkedin: String,
    twitter: String,
    facebook: String
  },
  
  // Revenue
  annualRevenue: Number,
  
  // Relationships
  contacts: [{ type: mongoose.Schema.Types.ObjectId, ref: 'Contact' }],
  deals: [{ type: mongoose.Schema.Types.ObjectId, ref: 'Deal' }],
  
  // Owner
  ownerId: mongoose.Schema.Types.ObjectId,
  assignedTo: mongoose.Schema.Types.ObjectId,
  
  tags: [String],
  notes: [{
    content: String,
    createdBy: mongoose.Schema.Types.ObjectId,
    createdAt: { type: Date, default: Date.now }
  }],
  
  createdAt: { type: Date, default: Date.now },
  updatedAt: Date
});

const TaskSchema = new mongoose.Schema({
  title: { type: String, required: true },
  description: String,
  type: { type: String, enum: ['call', 'email', 'meeting', 'task', 'follow_up'], default: 'task' },
  status: { type: String, enum: ['pending', 'in_progress', 'completed', 'cancelled'], default: 'pending' },
  priority: { type: String, enum: ['low', 'medium', 'high', 'urgent'], default: 'medium' },
  
  // Related entities
  contactId: mongoose.Schema.Types.ObjectId,
  dealId: mongoose.Schema.Types.ObjectId,
  companyId: mongoose.Schema.Types.ObjectId,
  
  // Timeline
  dueDate: Date,
  completedAt: Date,
  reminderAt: Date,
  
  // Owner
  ownerId: mongoose.Schema.Types.ObjectId,
  assignedTo: mongoose.Schema.Types.ObjectId,
  
  // Activity
  completedBy: mongoose.Schema.Types.ObjectId,
  
  createdAt: { type: Date, default: Date.now },
  updatedAt: Date
});

const ActivitySchema = new mongoose.Schema({
  type: { type: String, enum: ['call', 'email', 'meeting', 'note', 'task', 'deal_update', 'contact_update'] },
  subject: String,
  description: String,
  
  // Related entities
  contactId: mongoose.Schema.Types.ObjectId,
  dealId: mongoose.Schema.Types.ObjectId,
  companyId: mongoose.Schema.Types.ObjectId,
  
  // Owner
  ownerId: mongoose.Schema.Types.ObjectId,
  
  // Metadata
  metadata: mongoose.Schema.Types.Mixed,
  
  createdAt: { type: Date, default: Date.now }
});

const PipelineSchema = new mongoose.Schema({
  name: { type: String, required: true },
  description: String,
  stages: [{
    name: String,
    probability: Number,
    order: Number
  }],
  ownerId: mongoose.Schema.Types.ObjectId,
  isDefault: { type: Boolean, default: false },
  createdAt: { type: Date, default: Date.now }
});

const Contact = mongoose.model('Contact', ContactSchema);
const Deal = mongoose.model('Deal', DealSchema);
const Company = mongoose.model('Company', CompanySchema);
const Task = mongoose.model('Task', TaskSchema);
const Activity = mongoose.model('Activity', ActivitySchema);
const Pipeline = mongoose.model('Pipeline', PipelineSchema);

// ===== MIDDLEWARE =====

const auth = async (req, res, next) => {
  try {
    const token = req.headers.authorization?.split(' ')[1];
    if (!token) return res.status(401).json({ error: 'No token' });
    
    const decoded = jwt.verify(token, process.env.JWT_SECRET || 'secret');
    req.user = decoded;
    next();
  } catch (error) {
    res.status(401).json({ error: 'Invalid token' });
  }
};

// ===== API ROUTES =====

// Dashboard
app.get('/api/dashboard', auth, async (req, res) => {
  try {
    const ownerId = req.user.userId;
    
    const stats = {
      contacts: await Contact.countDocuments({ ownerId }),
      deals: await Deal.countDocuments({ ownerId }),
      companies: await Company.countDocuments({ ownerId }),
      tasks: await Task.countDocuments({ ownerId, status: 'pending' }),
      
      dealsValue: await Deal.aggregate([
        { $match: { ownerId: new mongoose.Types.ObjectId(ownerId) } },
        { $group: { _id: null, total: { $sum: '$value' } } }
      ]),
      
      dealsByStage: await Deal.aggregate([
        { $match: { ownerId: new mongoose.Types.ObjectId(ownerId) } },
        { $group: { _id: '$stage', count: { $sum: 1 }, value: { $sum: '$value' } } }
      ]),
      
      recentActivities: await Activity.find({ ownerId: new mongoose.Types.ObjectId(ownerId) })
        .sort('-createdAt')
        .limit(10)
    };
    
    res.json(stats);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Contacts
app.get('/api/contacts', auth, async (req, res) => {
  try {
    const { page = 1, limit = 20, search, status, tag } = req.query;
    const query = { ownerId: req.user.userId };
    
    if (search) {
      query.$or = [
        { firstName: { $regex: search, $options: 'i' } },
        { lastName: { $regex: search, $options: 'i' } },
        { email: { $regex: search, $options: 'i' } },
        { company: { $regex: search, $options: 'i' } }
      ];
    }
    
    if (status) query.status = status;
    if (tag) query.tags = tag;
    
    const contacts = await Contact.find(query)
      .sort('-createdAt')
      .limit(limit * 1)
      .skip((page - 1) * limit);
    
    const total = await Contact.countDocuments(query);
    
    res.json({ contacts, totalPages: Math.ceil(total / limit), currentPage: page, total });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/contacts', auth, async (req, res) => {
  try {
    const contact = new Contact({
      ...req.body,
      ownerId: req.user.userId
    });
    
    await contact.save();
    
    // Create activity
    await Activity.create({
      type: 'contact_update',
      subject: 'Contact created',
      contactId: contact._id,
      ownerId: req.user.userId
    });
    
    res.status(201).json(contact);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.put('/api/contacts/:id', auth, async (req, res) => {
  try {
    const contact = await Contact.findOneAndUpdate(
      { _id: req.params.id, ownerId: req.user.userId },
      { ...req.body, updatedAt: new Date() },
      { new: true }
    );
    
    if (!contact) return res.status(404).json({ error: 'Contact not found' });
    
    res.json(contact);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Deals
app.get('/api/deals', auth, async (req, res) => {
  try {
    const { page = 1, limit = 20, stage, search } = req.query;
    const query = { ownerId: req.user.userId };
    
    if (stage) query.stage = stage;
    if (search) query.title = { $regex: search, $options: 'i' };
    
    const deals = await Deal.find(query)
      .populate('contactId', 'firstName lastName')
      .sort('-createdAt')
      .limit(limit * 1)
      .skip((page - 1) * limit);
    
    const total = await Deal.countDocuments(query);
    
    res.json({ deals, totalPages: Math.ceil(total / limit), currentPage: page, total });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/deals', auth, async (req, res) => {
  try {
    const deal = new Deal({
      ...req.body,
      ownerId: req.user.userId
    });
    
    await deal.save();
    
    // Create activity
    await Activity.create({
      type: 'deal_update',
      subject: 'Deal created',
      dealId: deal._id,
      ownerId: req.user.userId
    });
    
    res.status(201).json(deal);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.put('/api/deals/:id', auth, async (req, res) => {
  try {
    const deal = await Deal.findOneAndUpdate(
      { _id: req.params.id, ownerId: req.user.userId },
      { ...req.body, updatedAt: new Date() },
      { new: true }
    );
    
    if (!deal) return res.status(404).json({ error: 'Deal not found' });
    
    res.json(deal);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Move deal to stage
app.post('/api/deals/:id/stage', auth, async (req, res) => {
  try {
    const { stage } = req.body;
    
    const deal = await Deal.findOneAndUpdate(
      { _id: req.params.id, ownerId: req.user.userId },
      { 
        stage,
        updatedAt: new Date(),
        ...(stage === 'closed_won' ? { closedDate: new Date() } : {})
      },
      { new: true }
    );
    
    if (!deal) return res.status(404).json({ error: 'Deal not found' });
    
    // Create activity
    await Activity.create({
      type: 'deal_update',
      subject: `Deal moved to ${stage}`,
      dealId: deal._id,
      ownerId: req.user.userId,
      metadata: { stage }
    });
    
    // Notify via socket
    io.emit('deal_stage_changed', { dealId: deal._id, stage });
    
    res.json(deal);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Companies
app.get('/api/companies', auth, async (req, res) => {
  try {
    const { page = 1, limit = 20, search, industry } = req.query;
    const query = { ownerId: req.user.userId };
    
    if (search) query.name = { $regex: search, $options: 'i' };
    if (industry) query.industry = industry;
    
    const companies = await Company.find(query)
      .sort('-createdAt')
      .limit(limit * 1)
      .skip((page - 1) * limit);
    
    const total = await Company.countDocuments(query);
    
    res.json({ companies, totalPages: Math.ceil(total / limit), currentPage: page, total });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/companies', auth, async (req, res) => {
  try {
    const company = new Company({
      ...req.body,
      ownerId: req.user.userId
    });
    
    await company.save();
    res.status(201).json(company);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Tasks
app.get('/api/tasks', auth, async (req, res) => {
  try {
    const { status, priority, type } = req.query;
    const query = { ownerId: req.user.userId };
    
    if (status) query.status = status;
    if (priority) query.priority = priority;
    if (type) query.type = type;
    
    const tasks = await Task.find(query)
      .sort('dueDate')
      .limit(100);
    
    res.json(tasks);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/tasks', auth, async (req, res) => {
  try {
    const task = new Task({
      ...req.body,
      ownerId: req.user.userId
    });
    
    await task.save();
    
    // Add to queue for reminder
    if (task.reminderAt) {
      await taskQueue.add(
        { taskId: task._id.toString(), type: 'reminder' },
        { delay: task.reminderAt - Date.now() }
      );
    }
    
    res.status(201).json(task);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.put('/api/tasks/:id/complete', auth, async (req, res) => {
  try {
    const task = await Task.findOneAndUpdate(
      { _id: req.params.id, ownerId: req.user.userId },
      { 
        status: 'completed',
        completedAt: new Date(),
        completedBy: req.user.userId
      },
      { new: true }
    );
    
    if (!task) return res.status(404).json({ error: 'Task not found' });
    
    res.json(task);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Activities
app.get('/api/activities', auth, async (req, res) => {
  try {
    const { type, limit = 50 } = req.query;
    const query = { ownerId: req.user.userId };
    
    if (type) query.type = type;
    
    const activities = await Activity.find(query)
      .sort('-createdAt')
      .limit(parseInt(limit));
    
    res.json(activities);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Pipelines
app.get('/api/pipelines', auth, async (req, res) => {
  try {
    const pipelines = await Pipeline.find({ ownerId: req.user.userId });
    res.json(pipelines);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/pipelines', auth, async (req, res) => {
  try {
    const pipeline = new Pipeline({
      ...req.body,
      ownerId: req.user.userId
    });
    
    await pipeline.save();
    res.status(201).json(pipeline);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Reports
app.get('/api/reports/sales', auth, async (req, res) => {
  try {
    const { startDate, endDate } = req.query;
    const query = { ownerId: req.user.userId };
    
    if (startDate && endDate) {
      query.createdAt = { $gte: new Date(startDate), $lte: new Date(endDate) };
    }
    
    const dealsClosed = await Deal.aggregate([
      { $match: { ...query, stage: 'closed_won' } },
      { $group: { _id: null, total: { $sum: '$value' }, count: { $sum: 1 } } }
    ]);
    
    const dealsByStage = await Deal.aggregate([
      { $match: query },
      { $group: { _id: '$stage', count: { $sum: 1 }, value: { $sum: '$value' } } }
    ]);
    
    const conversionRate = dealsClosed[0] 
      ? (dealsClosed[0].count / await Deal.countDocuments(query)) * 100 
      : 0;
    
    res.json({
      dealsClosed: dealsClosed[0] || { total: 0, count: 0 },
      dealsByStage,
      conversionRate,
      averageDealSize: dealsClosed[0] ? dealsClosed[0].total / dealsClosed[0].count : 0
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Export
app.get('/api/contacts/export', auth, async (req, res) => {
  try {
    const contacts = await Contact.find({ ownerId: req.user.userId });
    
    // Simple CSV export
    const csv = [
      ['First Name', 'Last Name', 'Email', 'Phone', 'Company', 'Status'].join(','),
      ...contacts.map(c => 
        [c.firstName, c.lastName, c.email, c.phone, c.company, c.status].join(',')
      )
    ].join('\n');
    
    res.setHeader('Content-Type', 'text/csv');
    res.setHeader('Content-Disposition', 'attachment; filename=contacts.csv');
    res.send(csv);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// ===== Socket.io Real-time =====
io.on('connection', (socket) => {
  console.log(`Client connected: ${socket.id}`);
  
  socket.on('join_dashboard', () => {
    socket.join('dashboard');
  });
  
  socket.on('disconnect', () => {
    console.log(`Client disconnected: ${socket.id}`);
  });
});

// ===== Background Jobs =====

emailQueue.process(async (job) => {
  const { to, subject, body } = job.data;
  
  // Send email (implement with nodemailer)
  console.log(`Sending email to ${to}: ${subject}`);
});

taskQueue.process(async (job) => {
  const { taskId, type } = job.data;
  
  if (type === 'reminder') {
    const task = await Task.findById(taskId);
    if (task) {
      // Send reminder notification
      io.emit('task_reminder', { task });
    }
  }
});

// Start Server
const PORT = process.env.PORT || 5007;
httpServer.listen(PORT, () => {
  console.log(`
╔════════════════════════════════════════════╗
║   💼 Rizz CRM Platform                     ║
║   Running on port ${PORT}                      ║
║                                            ║
║   Features:                                ║
║   - Contact Management                     ║
║   - Deal Pipeline                          ║
║   - Company Management                     ║
║   - Task Management                        ║
║   - Activity Tracking                      ║
║   - Reports & Analytics                    ║
╚════════════════════════════════════════════╝
  `);
});

module.exports = { app, io };
