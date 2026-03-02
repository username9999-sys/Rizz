/**
 * Rizz IoT Platform - Enterprise IoT Device Management
 * Features: Device management, telemetry, rules engine, alerts
 */

const express = require('express');
const mongoose = require('mongoose');
const { createServer } = require('http');
const { Server } = require('socket.io');
const mqtt = require('mqtt');
const jwt = require('jsonwebtoken');
require('dotenv').config();

const app = express();
const httpServer = createServer(app);
const io = new Server(httpServer, { cors: { origin: '*' } });

app.use(express.json());

// Database
mongoose.connect(process.env.MONGODB_URI || 'mongodb://localhost:27017/rizz_iot')
  .then(() => console.log('✅ MongoDB Connected'))
  .catch(err => console.error('❌ MongoDB Error:', err));

// MQTT Connection
const mqttClient = mqtt.connect(process.env.MQTT_BROKER || 'mqtt://localhost:1883');

mqttClient.on('connect', () => {
  console.log('✅ Connected to MQTT Broker');
  mqttClient.subscribe('iot/+/data');
  mqttClient.subscribe('iot/+/status');
  mqttClient.subscribe('iot/+/command');
});

// Models
const DeviceSchema = new mongoose.Schema({
  deviceId: { type: String, unique: true, required: true },
  name: { type: String, required: true },
  type: { type: String, enum: ['sensor', 'actuator', 'gateway', 'camera', 'meter'], required: true },
  manufacturer: String,
  model: String,
  firmwareVersion: String,
  hardwareVersion: String,
  
  // Connection
  protocol: { type: String, enum: ['MQTT', 'HTTP', 'CoAP', 'LoRaWAN', 'Zigbee'], default: 'MQTT' },
  connectionStatus: { type: String, enum: ['online', 'offline', 'error'], default: 'offline' },
  lastSeen: Date,
  
  // Location
  location: {
    name: String,
    latitude: Number,
    longitude: Number,
    altitude: Number
  },
  
  // Configuration
  config: mongoose.Schema.Types.Mixed,
  metadata: mongoose.Schema.Types.Mixed,
  
  // Security
  authToken: String,
  certificates: {
    public: String,
    private: String
  },
  
  // Organization
  groupId: mongoose.Schema.Types.ObjectId,
  ownerId: mongoose.Schema.Types.ObjectId,
  tags: [String],
  
  // Statistics
  totalMessages: { type: Number, default: 0 },
  totalUptime: { type: Number, default: 0 },
  
  createdAt: { type: Date, default: Date.now },
  updatedAt: Date
});

const TelemetrySchema = new mongoose.Schema({
  deviceId: { type: String, required: true, index: true },
  timestamp: { type: Date, default: Date.now, index: true },
  
  // Sensor data
  data: {
    temperature: Number,
    humidity: Number,
    pressure: Number,
    co2: Number,
    pm25: Number,
    pm10: Number,
    voltage: Number,
    current: Number,
    power: Number,
    energy: Number,
    light: Number,
    sound: Number,
    motion: Boolean,
    custom: mongoose.Schema.Types.Mixed
  },
  
  // Location at time of reading
  location: {
    latitude: Number,
    longitude: Number
  },
  
  // Quality
  quality: { type: Number, default: 1 },
  validated: { type: Boolean, default: true }
}, { timestamps: true });

// Index for time-series queries
TelemetrySchema.index({ deviceId: 1, timestamp: -1 });

const AlertRuleSchema = new mongoose.Schema({
  name: { type: String, required: true },
  description: String,
  deviceId: String,
  deviceGroup: String,
  
  // Condition
  metric: { type: String, required: true },
  operator: { type: String, enum: ['>', '<', '>=', '<=', '==', '!='], required: true },
  threshold: { type: Number, required: true },
  duration: Number, // seconds
  
  // Actions
  actions: [{
    type: { type: String, enum: ['email', 'sms', 'webhook', 'mqtt', 'command'] },
    target: String,
    message: String
  }],
  
  // Status
  enabled: { type: Boolean, default: true },
  triggered: { type: Boolean, default: false },
  triggeredAt: Date,
  
  createdAt: { type: Date, default: Date.now }
});

const AlertSchema = new mongoose.Schema({
  ruleId: mongoose.Schema.Types.ObjectId,
  deviceId: String,
  metric: String,
  value: Number,
  threshold: Number,
  severity: { type: String, enum: ['info', 'warning', 'critical'], default: 'warning' },
  message: String,
  status: { type: String, enum: ['active', 'acknowledged', 'resolved'], default: 'active' },
  acknowledgedBy: mongoose.Schema.Types.ObjectId,
  acknowledgedAt: Date,
  resolvedAt: Date,
  createdAt: { type: Date, default: Date.now }
});

const DeviceGroupSchema = new mongoose.Schema({
  name: { type: String, required: true },
  description: String,
  devices: [{ type: mongoose.Schema.Types.ObjectId, ref: 'Device' }],
  rules: [AlertRuleSchema],
  dashboard: mongoose.Schema.Types.Mixed,
  createdAt: { type: Date, default: Date.now }
});

const Device = mongoose.model('Device', DeviceSchema);
const Telemetry = mongoose.model('Telemetry', TelemetrySchema);
const AlertRule = mongoose.model('AlertRule', AlertRuleSchema);
const Alert = mongoose.model('Alert', AlertSchema);
const DeviceGroup = mongoose.model('DeviceGroup', DeviceGroupSchema);

// Auth Middleware
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

// Device auth (for IoT devices)
const deviceAuth = async (req, res, next) => {
  try {
    const { deviceId, authToken } = req.headers;
    if (!deviceId || !authToken) {
      return res.status(401).json({ error: 'Missing device credentials' });
    }
    
    const device = await Device.findOne({ deviceId, authToken });
    if (!device) {
      return res.status(401).json({ error: 'Invalid device credentials' });
    }
    
    req.device = device;
    next();
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

// ===== API ROUTES =====

// Register Device
app.post('/api/devices/register', auth, async (req, res) => {
  try {
    const { deviceId, name, type, manufacturer, model, protocol, location } = req.body;
    
    const device = new Device({
      deviceId,
      name,
      type,
      manufacturer,
      model,
      protocol: protocol || 'MQTT',
      authToken: crypto.randomBytes(32).toString('hex'),
      location,
      ownerId: req.user.userId
    });
    
    await device.save();
    
    // Publish to MQTT
    mqttClient.publish(`iot/${deviceId}/registered`, JSON.stringify({ status: 'registered' }));
    
    res.status(201).json({ device });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// List Devices
app.get('/api/devices', auth, async (req, res) => {
  try {
    const { status, type, group, search } = req.query;
    const query = { ownerId: req.user.userId };
    
    if (status) query.connectionStatus = status;
    if (type) query.type = type;
    if (search) query.name = { $regex: search, $options: 'i' };
    
    const devices = await Device.find(query).sort('-lastSeen');
    res.json(devices);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Get Device Details
app.get('/api/devices/:deviceId', auth, async (req, res) => {
  try {
    const device = await Device.findOne({ deviceId: req.params.deviceId, ownerId: req.user.userId });
    if (!device) return res.status(404).json({ error: 'Device not found' });
    
    res.json(device);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Receive Telemetry (from devices)
app.post('/api/telemetry', deviceAuth, async (req, res) => {
  try {
    const { data, location } = req.body;
    
    const telemetry = new Telemetry({
      deviceId: req.device.deviceId,
      data,
      location
    });
    
    await telemetry.save();
    
    // Update device last seen
    await Device.findOneAndUpdate(
      { deviceId: req.device.deviceId },
      { lastSeen: new Date(), connectionStatus: 'online' }
    );
    
    // Emit via socket
    io.emit('telemetry', { deviceId: req.device.deviceId, data, timestamp: telemetry.timestamp });
    
    // Check alert rules
    await checkAlerts(req.device.deviceId, data);
    
    res.json({ status: 'received', timestamp: telemetry.timestamp });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Get Telemetry History
app.get('/api/telemetry/:deviceId', auth, async (req, res) => {
  try {
    const { startTime, endTime, limit = 1000 } = req.query;
    const query = { deviceId: req.params.deviceId };
    
    if (startTime || endTime) {
      query.timestamp = {};
      if (startTime) query.timestamp.$gte = new Date(startTime);
      if (endTime) query.timestamp.$lte = new Date(endTime);
    }
    
    const telemetry = await Telemetry.find(query)
      .sort('-timestamp')
      .limit(parseInt(limit));
    
    res.json(telemetry);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Send Command to Device
app.post('/api/devices/:deviceId/command', auth, async (req, res) => {
  try {
    const { command, params } = req.body;
    const device = await Device.findOne({ deviceId: req.params.deviceId, ownerId: req.user.userId });
    
    if (!device) return res.status(404).json({ error: 'Device not found' });
    
    const commandData = {
      command,
      params,
      timestamp: new Date().toISOString()
    };
    
    // Publish via MQTT
    mqttClient.publish(`iot/${device.deviceId}/command`, JSON.stringify(commandData));
    
    res.json({ status: 'sent', command });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Create Alert Rule
app.post('/api/alerts/rules', auth, async (req, res) => {
  try {
    const rule = new AlertRule({
      ...req.body,
      ownerId: req.user.userId
    });
    
    await rule.save();
    res.status(201).json({ rule });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Get Alert Rules
app.get('/api/alerts/rules', auth, async (req, res) => {
  try {
    const rules = await AlertRule.find({ ownerId: req.user.userId });
    res.json(rules);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Get Active Alerts
app.get('/api/alerts', auth, async (req, res) => {
  try {
    const { status, severity } = req.query;
    const query = {};
    
    if (status) query.status = status;
    if (severity) query.severity = severity;
    
    const alerts = await Alert.find(query)
      .populate('ruleId')
      .sort('-createdAt')
      .limit(100);
    
    res.json(alerts);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Acknowledge Alert
app.post('/api/alerts/:id/acknowledge', auth, async (req, res) => {
  try {
    await Alert.findByIdAndUpdate(req.params.id, {
      status: 'acknowledged',
      acknowledgedBy: req.user.userId,
      acknowledgedAt: new Date()
    });
    
    res.json({ status: 'acknowledged' });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Dashboard Stats
app.get('/api/dashboard/stats', auth, async (req, res) => {
  try {
    const totalDevices = await Device.countDocuments({ ownerId: req.user.userId });
    const onlineDevices = await Device.countDocuments({ ownerId: req.user.userId, connectionStatus: 'online' });
    const offlineDevices = totalDevices - onlineDevices;
    
    const activeAlerts = await Alert.countDocuments({ status: 'active' });
    const totalTelemetry = await Telemetry.countDocuments();
    
    // Recent telemetry by device
    const recentTelemetry = await Telemetry.aggregate([
      { $sort: { timestamp: -1 } },
      { $limit: 1000 },
      { $group: { _id: '$deviceId', count: { $sum: 1 }, lastValue: { $first: '$data' } } }
    ]);
    
    res.json({
      totalDevices,
      onlineDevices,
      offlineDevices,
      activeAlerts,
      totalTelemetry,
      devicesByType: recentTelemetry
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// ===== Alert Rules Engine =====
async function checkAlerts(deviceId, data) {
  const rules = await AlertRule.find({ 
    $or: [{ deviceId }, { deviceGroup: { $exists: false } }],
    enabled: true
  });
  
  for (const rule of rules) {
    const value = data[rule.metric];
    if (value === undefined) continue;
    
    let triggered = false;
    switch (rule.operator) {
      case '>': triggered = value > rule.threshold; break;
      case '<': triggered = value < rule.threshold; break;
      case '>=': triggered = value >= rule.threshold; break;
      case '<=': triggered = value <= rule.threshold; break;
      case '==': triggered = value == rule.threshold; break;
      case '!=': triggered = value != rule.threshold; break;
    }
    
    if (triggered && !rule.triggered) {
      // Create alert
      const alert = new Alert({
        ruleId: rule._id,
        deviceId,
        metric: rule.metric,
        value,
        threshold: rule.threshold,
        severity: value > rule.threshold * 1.5 ? 'critical' : 'warning',
        message: `${rule.metric} ${rule.operator} ${rule.threshold} (current: ${value})`
      });
      
      await alert.save();
      
      // Execute actions
      for (const action of rule.actions) {
        executeAlertAction(action, alert);
      }
      
      // Update rule
      await AlertRule.findByIdAndUpdate(rule._id, { triggered: true, triggeredAt: new Date() });
      
      // Emit via socket
      io.emit('alert', alert);
    }
  }
}

function executeAlertAction(action, alert) {
  switch (action.type) {
    case 'email':
      // Send email (implement with nodemailer)
      console.log(`Sending email to ${action.target}: ${alert.message}`);
      break;
    case 'sms':
      // Send SMS (implement with Twilio)
      console.log(`Sending SMS to ${action.target}: ${alert.message}`);
      break;
    case 'webhook':
      // Call webhook
      require('axios').post(action.target, alert);
      break;
    case 'mqtt':
      mqttClient.publish(action.target, JSON.stringify(alert));
      break;
  }
}

// ===== MQTT Message Handler =====
mqttClient.on('message', async (topic, message) => {
  try {
    const data = JSON.parse(message.toString());
    const parts = topic.split('/');
    const deviceId = parts[1];
    
    if (parts[2] === 'data') {
      // Store telemetry
      await Telemetry.create({ deviceId, data: data });
      io.emit('telemetry', { deviceId, data });
    } else if (parts[2] === 'status') {
      // Update device status
      await Device.findOneAndUpdate(
        { deviceId },
        { connectionStatus: data.status, lastSeen: new Date() }
      );
      io.emit('device_status', { deviceId, status: data.status });
    }
  } catch (error) {
    console.error('MQTT message error:', error);
  }
});

// ===== Socket.io Real-time =====
io.on('connection', (socket) => {
  console.log(`Client connected: ${socket.id}`);
  
  socket.on('subscribe_device', (deviceId) => {
    socket.join(`device_${deviceId}`);
  });
  
  socket.on('subscribe_alerts', () => {
    socket.join('alerts');
  });
  
  socket.on('disconnect', () => {
    console.log(`Client disconnected: ${socket.id}`);
  });
});

const crypto = require('crypto');

// Start Server
const PORT = process.env.PORT || 5006;
httpServer.listen(PORT, () => {
  console.log(`
╔════════════════════════════════════════════╗
║   📡 Rizz IoT Platform                     ║
║   Running on port ${PORT}                      ║
║                                            ║
║   Features:                                ║
║   - Device Management                      ║
║   - Real-time Telemetry                    ║
║   - MQTT/HTTP/CoAP Support                 ║
║   - Rules Engine & Alerts                  ║
║   - Dashboard & Analytics                  ║
╚════════════════════════════════════════════╝
  `);
});

module.exports = { app, io, mqttClient };
