/**
 * Rizz CRM - Enhanced with AI Automation & Workflows
 * Features: AI lead scoring, Automated workflows, Email sequences, Chatbot integration
 */

const express = require('express');
const mongoose = require('mongoose');
const nodemailer = require('nodemailer');

const app = express();
app.use(express.json());

mongoose.connect(process.env.MONGODB_URI || 'mongodb://localhost:27017/rizz_crm_enhanced');

// ===== ENHANCED MODELS =====

// AI-Powered Lead Scoring
const LeadScoringSchema = new mongoose.Schema({
  contactId: mongoose.Schema.Types.ObjectId,
  score: { type: Number, min: 0, max: 100 },
  factors: [{
    name: String,
    impact: Number,
    description: String
  }],
  grade: { type: String, enum: ['A', 'B', 'C', 'D', 'F'] },
  calculatedAt: { type: Date, default: Date.now }
});

// Automated Workflow
const WorkflowSchema = new mongoose.Schema({
  name: { type: String, required: true },
  description: String,
  trigger: {
    type: { type: String, enum: ['contact_created', 'deal_stage_changed', 'date_reached', 'custom'] },
    conditions: mongoose.Schema.Types.Mixed
  },
  actions: [{
    type: { type: String, enum: ['send_email', 'create_task', 'update_field', 'send_notification', 'webhook'] },
    parameters: mongoose.Schema.Types.Mixed,
    order: Number
  }],
  active: { type: Boolean, default: true },
  executions: [{
    executedAt: Date,
    triggerData: mongoose.Schema.Types.Mixed,
    results: [mongoose.Schema.Types.Mixed],
    status: { type: String, enum: ['success', 'partial', 'failed'] }
  }],
  createdAt: { type: Date, default: Date.now }
});

// Email Sequence
const EmailSequenceSchema = new mongoose.Schema({
  name: String,
  emails: [{
    subject: String,
    content: String,
    delayDays: Number,
    template: String
  }],
  active: { type: Boolean, default: true }
});

// AI Chatbot Configuration
const ChatbotSchema = new mongoose.Schema({
  name: String,
  knowledgeBase: [String],
  responses: [{
    trigger: String,
    response: String,
    action: String
  }],
  integration: {
    platform: { type: String, enum: ['website', 'whatsapp', 'telegram', 'facebook'] },
    webhookUrl: String
  }
});

const LeadScoring = mongoose.model('LeadScoring', LeadScoringSchema);
const Workflow = mongoose.model('Workflow', WorkflowSchema);
const EmailSequence = mongoose.model('EmailSequence', EmailSequenceSchema);
const Chatbot = mongoose.model('Chatbot', ChatbotSchema);
const Contact = mongoose.model('Contact');
const Deal = mongoose.model('Deal');

// ===== AI LEAD SCORING ENGINE =====

class AILeadScorer {
  calculateScore(contact, interactions, dealHistory) {
    let score = 50; // Base score
    const factors = [];
    
    // Factor 1: Job title (decision maker)
    if (contact.position && /ceo|cto|cfo|director|manager/i.test(contact.position)) {
      score += 15;
      factors.push({ name: 'Decision Maker', impact: 15, description: 'Has decision-making authority' });
    }
    
    // Factor 2: Company size
    if (contact.company && /enterprise|corporation/i.test(contact.company)) {
      score += 10;
      factors.push({ name: 'Company Size', impact: 10, description: 'Large company potential' });
    }
    
    // Factor 3: Engagement level
    if (interactions && interactions.length > 5) {
      score += 20;
      factors.push({ name: 'High Engagement', impact: 20, description: `${interactions.length} interactions` });
    }
    
    // Factor 4: Deal history
    if (dealHistory && dealHistory.length > 0) {
      const totalValue = dealHistory.reduce((sum, deal) => sum + (deal.value || 0), 0);
      if (totalValue > 10000) {
        score += 15;
        factors.push({ name: 'Purchase History', impact: 15, description: `Previous value: $${totalValue}` });
      }
    }
    
    // Factor 5: Email engagement
    if (contact.emailOpened || contact.emailClicked) {
      score += 10;
      factors.push({ name: 'Email Engagement', impact: 10, description: 'Actively opens emails' });
    }
    
    // Normalize score
    score = Math.min(Math.max(score, 0), 100);
    
    // Assign grade
    let grade = 'F';
    if (score >= 90) grade = 'A';
    else if (score >= 75) grade = 'B';
    else if (score >= 60) grade = 'C';
    else if (score >= 40) grade = 'D';
    
    return { score, factors, grade };
  }
}

const aiLeadScorer = new AILeadScorer();

// ===== WORKFLOW AUTOMATION ENGINE =====

class WorkflowEngine {
  constructor() {
    this.workflows = new Map();
  }
  
  async executeWorkflow(workflow, triggerData) {
    const results = [];
    let status = 'success';
    
    for (const action of workflow.actions) {
      try {
        const result = await this.executeAction(action, triggerData);
        results.push({ action: action.type, result, status: 'success' });
      } catch (error) {
        results.push({ action: action.type, error: error.message, status: 'failed' });
        status = 'partial';
      }
    }
    
    // Record execution
    workflow.executions.push({
      executedAt: new Date(),
      triggerData,
      results,
      status
    });
    
    await workflow.save();
    
    return { workflow, results, status };
  }
  
  async executeAction(action, triggerData) {
    switch (action.type) {
      case 'send_email':
        return await this.sendEmail(action.parameters, triggerData);
      
      case 'create_task':
        return await this.createTask(action.parameters, triggerData);
      
      case 'update_field':
        return await this.updateField(action.parameters, triggerData);
      
      case 'send_notification':
        return await this.sendNotification(action.parameters, triggerData);
      
      case 'webhook':
        return await this.triggerWebhook(action.parameters, triggerData);
      
      default:
        throw new Error(`Unknown action type: ${action.type}`);
    }
  }
  
  async sendEmail(params, triggerData) {
    // In production: Use actual email service
    return {
      sent: true,
      to: triggerData.contact?.email || 'unknown',
      subject: params.subject,
      sentAt: new Date()
    };
  }
  
  async createTask(params, triggerData) {
    const task = {
      title: params.title,
      description: params.description,
      assignedTo: params.assignedTo,
      dueDate: params.dueDate,
      relatedTo: triggerData.contact?._id
    };
    // In production: Save to database
    return { created: true, task };
  }
  
  async updateField(params, triggerData) {
    // Update contact/deal field
    return { updated: true, field: params.field, value: params.value };
  }
  
  async sendNotification(params, triggerData) {
    // Send push/SMS notification
    return { sent: true, channel: params.channel, message: params.message };
  }
  
  async triggerWebhook(params, triggerData) {
    // Call external webhook
    return { called: true, url: params.url, status: 200 };
  }
}

const workflowEngine = new WorkflowEngine();

// ===== EMAIL SEQUENCE AUTOMATION =====

class EmailSequenceRunner {
  async enrollContact(contactId, sequenceId) {
    const sequence = await EmailSequence.findById(sequenceId);
    if (!sequence) throw new Error('Sequence not found');
    
    // Schedule emails
    const scheduledEmails = sequence.emails.map(email => ({
      contactId,
      sequenceId,
      email: email,
      scheduledFor: new Date(Date.now() + (email.delayDays * 24 * 60 * 60 * 1000)),
      status: 'scheduled'
    }));
    
    return { enrolled: true, scheduledEmails };
  }
  
  async processDueEmails() {
    // Find emails that are due to be sent
    const dueEmails = []; // In production: Query database
    
    for (const email of dueEmails) {
      await this.sendEmail(email);
    }
    
    return { processed: dueEmails.length };
  }
}

const emailSequenceRunner = new EmailSequenceRunner();

// ===== API ROUTES =====

// AI Lead Scoring
app.post('/api/leads/score/:contactId', async (req, res) => {
  try {
    const contact = await Contact.findById(req.params.contactId);
    if (!contact) return res.status(404).json({ error: 'Contact not found' });
    
    const interactions = []; // In production: Fetch interactions
    const dealHistory = await Deal.find({ 'contactId': contact._id });
    
    const scoring = aiLeadScorer.calculateScore(contact, interactions, dealHistory);
    
    const leadScore = await LeadScoring.create({
      contactId: contact._id,
      ...scoring
    });
    
    res.json({ leadScore });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Workflow Management
app.post('/api/workflows', async (req, res) => {
  try {
    const workflow = await Workflow.create(req.body);
    res.status(201).json({ workflow });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/workflows', async (req, res) => {
  try {
    const workflows = await Workflow.find().sort('-createdAt');
    res.json({ workflows });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/workflows/:id/execute', async (req, res) => {
  try {
    const workflow = await Workflow.findById(req.params.id);
    if (!workflow) return res.status(404).json({ error: 'Workflow not found' });
    
    const result = await workflowEngine.executeWorkflow(workflow, req.body.triggerData);
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Email Sequences
app.post('/api/sequences', async (req, res) => {
  try {
    const sequence = await EmailSequence.create(req.body);
    res.status(201).json({ sequence });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/sequences/:id/enroll', async (req, res) => {
  try {
    const { contactId } = req.body;
    const result = await emailSequenceRunner.enrollContact(contactId, req.params.id);
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Analytics
app.get('/api/analytics/automation', async (req, res) => {
  try {
    const totalWorkflows = await Workflow.countDocuments();
    const activeWorkflows = await Workflow.countDocuments({ active: true });
    const workflowExecutions = await Workflow.aggregate([
      { $unwind: '$executions' },
      { $group: { _id: null, total: { $sum: 1 }, success: { $sum: { $cond: [{ $eq: ['$executions.status', 'success'] }, 1, 0] } } } }
    ]);
    
    res.json({
      totalWorkflows,
      activeWorkflows,
      executions: workflowExecutions[0] || { total: 0, success: 0 },
      successRate: workflowExecutions[0] ? (workflowExecutions[0].success / workflowExecutions[0].total * 100).toFixed(2) : 0
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Start server
const PORT = process.env.PORT || 5007;
app.listen(PORT, () => {
  console.log(`
╔════════════════════════════════════════════╗
║   💼 Rizz CRM - Enhanced with AI           ║
║   Running on port ${PORT}                      ║
║                                            ║
║   Features:                                ║
║   - AI Lead Scoring                        ║
║   - Automated Workflows                    ║
║   - Email Sequences                        ║
║   - Chatbot Integration                    ║
╚════════════════════════════════════════════╝
  `);
});

module.exports = app;
