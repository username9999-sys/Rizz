/**
 * Rizz IoT Platform - Enhanced with Predictive Analytics & Edge Computing
 * Features: ML at edge, Predictive maintenance, Digital twins, Geo-fencing
 */

const express = require('express');
const mongoose = require('mongoose');
const mqtt = require('mqtt');
const { spawn } = require('child_process');

const app = express();
app.use(express.json());

// Database
mongoose.connect(process.env.MONGODB_URI || 'mongodb://localhost:27017/rizz_iot_enhanced');

// ===== ENHANCED MODELS =====

// Digital Twin - Virtual representation of physical device
const DigitalTwinSchema = new mongoose.Schema({
  deviceId: { type: String, unique: true, required: true },
  name: String,
  model: String,
  
  // Current state
  state: {
    temperature: Number,
    humidity: Number,
    pressure: Number,
    vibration: Number,
    powerConsumption: Number,
    operationalStatus: { type: String, enum: ['running', 'idle', 'error', 'maintenance'] }
  },
  
  // Historical state for ML
  stateHistory: [{
    timestamp: Date,
    temperature: Number,
    humidity: Number,
    vibration: Number,
    powerConsumption: Number
  }],
  
  // Predictive analytics
  predictions: {
    failureProbability: Number,
    remainingUsefulLife: Number, // hours
    nextMaintenanceDate: Date,
    confidenceScore: Number
  },
  
  // Simulation
  simulationMode: { type: Boolean, default: false },
  simulationParameters: mongoose.Schema.Types.Mixed,
  
  lastSyncAt: Date,
  createdAt: { type: Date, default: Date.now }
});

// Predictive Maintenance Model
const MaintenanceModelSchema = new mongoose.Schema({
  deviceId: String,
  modelType: { type: String, enum: ['regression', 'classification', 'anomaly_detection'] },
  features: [String],
  target: String,
  accuracy: Number,
  trainedAt: Date,
  modelPath: String,
  thresholds: {
    warning: Number,
    critical: Number
  }
});

// Geo-fencing
const GeoFenceSchema = new mongoose.Schema({
  name: String,
  deviceId: String,
  boundary: {
    type: { type: String, enum: ['circle', 'polygon'] },
    coordinates: [Number], // [lat, lng, radius] for circle
    polygon: [[Number]] // [[lat, lng], ...] for polygon
  },
  alerts: [{
    type: { type: String, enum: ['enter', 'exit'] },
    triggered: Boolean,
    timestamp: Date
  }],
  active: { type: Boolean, default: true }
});

// Edge Computing Node
const EdgeNodeSchema = new mongoose.Schema({
  name: String,
  location: String,
  capabilities: ['ml_inference', 'data_processing', 'local_storage'],
  connectedDevices: [String],
  processingLoad: Number, // percentage
  storageUsed: Number,
  storageTotal: Number,
  status: { type: String, enum: ['online', 'offline', 'busy'] }
});

const DigitalTwin = mongoose.model('DigitalTwin', DigitalTwinSchema);
const MaintenanceModel = mongoose.model('MaintenanceModel', MaintenanceModelSchema);
const GeoFence = mongoose.model('GeoFence', GeoFenceSchema);
const EdgeNode = mongoose.model('EdgeNode', EdgeNodeSchema);

// ===== PREDICTIVE ANALYTICS ENGINE =====

class PredictiveAnalytics {
  constructor() {
    this.models = new Map();
    this.anomalyThresholds = new Map();
  }
  
  // Train predictive maintenance model
  async trainModel(deviceId, historicalData) {
    // In production: Use TensorFlow.js or Python ML service
    // For now: Simulate ML training
    
    const model = {
      deviceId,
      type: 'anomaly_detection',
      features: ['temperature', 'vibration', 'powerConsumption'],
      thresholds: {
        temperature: { warning: 75, critical: 90 },
        vibration: { warning: 5.0, critical: 8.0 },
        powerConsumption: { warning: 1000, critical: 1500 }
      },
      accuracy: 0.92,
      trainedAt: new Date()
    };
    
    this.models.set(deviceId, model);
    
    return model;
  }
  
  // Predict failure probability
  async predictFailure(deviceId, currentData) {
    const model = this.models.get(deviceId);
    if (!model) return null;
    
    // Calculate anomaly score
    let anomalyScore = 0;
    
    if (currentData.temperature > model.thresholds.temperature.warning) {
      anomalyScore += 0.3;
    }
    if (currentData.temperature > model.thresholds.temperature.critical) {
      anomalyScore += 0.4;
    }
    
    if (currentData.vibration > model.thresholds.vibration.warning) {
      anomalyScore += 0.2;
    }
    
    if (currentData.powerConsumption > model.thresholds.powerConsumption.warning) {
      anomalyScore += 0.1;
    }
    
    const failureProbability = Math.min(anomalyScore, 1.0);
    const remainingUsefulLife = (1 - failureProbability) * 720; // hours
    const nextMaintenanceDate = new Date(Date.now() + (remainingUsefulLife * 60 * 60 * 1000));
    
    return {
      failureProbability,
      remainingUsefulLife: Math.round(remainingUsefulLife),
      nextMaintenanceDate,
      confidenceScore: 0.89,
      recommendations: this.generateRecommendations(failureProbability, currentData)
    };
  }
  
  // Generate maintenance recommendations
  generateRecommendations(probability, data) {
    const recommendations = [];
    
    if (probability > 0.8) {
      recommendations.push('IMMEDIATE: Schedule emergency maintenance');
      recommendations.push('Reduce operational load immediately');
    } else if (probability > 0.5) {
      recommendations.push('WARNING: Schedule maintenance within 48 hours');
      recommendations.push('Monitor closely for further degradation');
    } else if (probability > 0.3) {
      recommendations.push('CAUTION: Plan preventive maintenance');
    }
    
    if (data.temperature > 75) {
      recommendations.push('Check cooling system');
    }
    
    if (data.vibration > 5) {
      recommendations.push('Inspect mechanical components');
    }
    
    return recommendations;
  }
  
  // Detect anomalies in real-time
  detectAnomaly(deviceId, data) {
    const model = this.models.get(deviceId);
    if (!model) return null;
    
    const anomalies = [];
    
    if (data.temperature > model.thresholds.temperature.critical) {
      anomalies.push({
        metric: 'temperature',
        value: data.temperature,
        threshold: model.thresholds.temperature.critical,
        severity: 'critical'
      });
    }
    
    if (data.vibration > model.thresholds.vibration.critical) {
      anomalies.push({
        metric: 'vibration',
        value: data.vibration,
        threshold: model.thresholds.vibration.critical,
        severity: 'critical'
      });
    }
    
    return anomalies.length > 0 ? anomalies : null;
  }
}

const predictiveAnalytics = new PredictiveAnalytics();

// ===== GEO-FENCING ENGINE =====

class GeoFenceManager {
  constructor() {
    this.fences = new Map();
  }
  
  async createFence(config) {
    const fence = await GeoFence.create(config);
    this.fences.set(fence.deviceId, fence);
    return fence;
  }
  
  checkLocation(deviceId, location) {
    const fence = this.fences.get(deviceId);
    if (!fence || !fence.active) return null;
    
    const { lat, lng } = location;
    let triggered = false;
    let alertType = null;
    
    if (fence.boundary.type === 'circle') {
      const [centerLat, centerLng, radius] = fence.boundary.coordinates;
      const distance = this.calculateDistance(lat, lng, centerLat, centerLng);
      triggered = distance <= radius;
    } else if (fence.boundary.type === 'polygon') {
      triggered = this.pointInPolygon(lat, lng, fence.boundary.polygon);
    }
    
    if (triggered) {
      alertType = 'enter';
    }
    
    return { triggered, alertType, fence };
  }
  
  calculateDistance(lat1, lng1, lat2, lng2) {
    const R = 6371e3; // metres
    const φ1 = lat1 * Math.PI/180;
    const φ2 = lat2 * Math.PI/180;
    const Δφ = (lat2-lat1) * Math.PI/180;
    const Δλ = (lng2-lng1) * Math.PI/180;
    
    const a = Math.sin(Δφ/2) * Math.sin(Δφ/2) +
              Math.cos(φ1) * Math.cos(φ2) *
              Math.sin(Δλ/2) * Math.sin(Δλ/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    
    return R * c;
  }
  
  pointInPolygon(lat, lng, polygon) {
    // Ray casting algorithm
    let inside = false;
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
      const xi = polygon[i][0], yi = polygon[i][1];
      const xj = polygon[j][0], yj = polygon[j][1];
      
      const intersect = ((yi > lat) !== (yj > lat)) &&
          (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi);
      if (intersect) inside = !inside;
    }
    return inside;
  }
}

const geoFenceManager = new GeoFenceManager();

// ===== EDGE COMPUTING MANAGER =====

class EdgeComputingManager {
  constructor() {
    this.nodes = new Map();
  }
  
  async deployMLModel(nodeId, modelPath) {
    const node = await EdgeNode.findById(nodeId);
    if (!node) throw new Error('Node not found');
    
    // Simulate model deployment to edge
    // In production: Use Docker containers or model serialization
    
    return {
      status: 'deployed',
      nodeId,
      modelPath,
      deployedAt: new Date()
    };
  }
  
  async processAtEdge(nodeId, data) {
    const node = await EdgeNode.findById(nodeId);
    if (!node) throw new Error('Node not found');
    
    // Process data at edge (reduce latency)
    const processed = {
      nodeId,
      timestamp: new Date(),
      inputSize: JSON.stringify(data).length,
      processingTime: Math.random() * 50, // ms
      result: 'processed_at_edge'
    };
    
    return processed;
  }
  
  async optimizeLoad() {
    // Load balancing across edge nodes
    const nodes = await EdgeNode.find({ status: 'online' });
    
    // Find node with lowest load
    const optimalNode = nodes.reduce((min, node) => 
      node.processingLoad < min.processingLoad ? node : min
    );
    
    return optimalNode;
  }
}

const edgeComputingManager = new EdgeComputingManager();

// ===== API ROUTES =====

// Digital Twin endpoints
app.get('/api/digital-twins', async (req, res) => {
  try {
    const twins = await DigitalTwin.find().sort('-lastSyncAt');
    res.json({ twins });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/digital-twins/:deviceId', async (req, res) => {
  try {
    const twin = await DigitalTwin.findOne({ deviceId: req.params.deviceId });
    if (!twin) return res.status(404).json({ error: 'Digital twin not found' });
    res.json({ twin });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/digital-twins/:deviceId/state', async (req, res) => {
  try {
    const { state } = req.body;
    
    const twin = await DigitalTwin.findOneAndUpdate(
      { deviceId: req.params.deviceId },
      { 
        state,
        lastSyncAt: new Date(),
        $push: { stateHistory: { ...state, timestamp: new Date() } }
      },
      { new: true, upsert: true }
    );
    
    // Run predictive analytics
    const prediction = await predictiveAnalytics.predictFailure(req.params.deviceId, state);
    if (prediction) {
      twin.predictions = prediction;
      await twin.save();
    }
    
    // Check for anomalies
    const anomalies = predictiveAnalytics.detectAnomaly(req.params.deviceId, state);
    if (anomalies) {
      // Send alert
      console.log('ANOMALY DETECTED:', anomalies);
    }
    
    res.json({ twin, anomalies, prediction });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Predictive maintenance endpoints
app.post('/api/maintenance/train', async (req, res) => {
  try {
    const { deviceId, historicalData } = req.body;
    const model = await predictiveAnalytics.trainModel(deviceId, historicalData);
    res.json({ model });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/maintenance/predict/:deviceId', async (req, res) => {
  try {
    const twin = await DigitalTwin.findOne({ deviceId: req.params.deviceId });
    if (!twin) return res.status(404).json({ error: 'Device not found' });
    
    const prediction = await predictiveAnalytics.predictFailure(req.params.deviceId, twin.state);
    res.json({ prediction });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Geo-fencing endpoints
app.post('/api/geofences', async (req, res) => {
  try {
    const fence = await geoFenceManager.createFence(req.body);
    res.status(201).json({ fence });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/geofences/check', async (req, res) => {
  try {
    const { deviceId, location } = req.body;
    const result = geoFenceManager.checkLocation(deviceId, location);
    res.json({ result });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Edge computing endpoints
app.post('/api/edge/:nodeId/deploy', async (req, res) => {
  try {
    const { modelPath } = req.body;
    const result = await edgeComputingManager.deployMLModel(req.params.nodeId, modelPath);
    res.json({ result });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/edge/:nodeId/process', async (req, res) => {
  try {
    const { data } = req.body;
    const result = await edgeComputingManager.processAtEdge(req.params.nodeId, data);
    res.json({ result });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/edge/optimize', async (req, res) => {
  try {
    const optimalNode = await edgeComputingManager.optimizeLoad();
    res.json({ optimalNode });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Analytics dashboard
app.get('/api/analytics/overview', async (req, res) => {
  try {
    const totalDevices = await DigitalTwin.countDocuments();
    const activeAlerts = await DigitalTwin.find({ 'predictions.failureProbability': { $gt: 0.5 } }).count();
    const avgHealth = await DigitalTwin.aggregate([
      { $match: { predictions: { $exists: true } } },
      { $group: { _id: null, avg: { $avg: '$predictions.failureProbability' } } }
    ]);
    
    res.json({
      totalDevices,
      activeAlerts,
      averageHealthScore: avgHealth[0] ? 1 - avgHealth[0].avg : 1,
      edgeNodes: await EdgeNode.countDocuments()
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// MQTT Connection
const mqttClient = mqtt.connect(process.env.MQTT_BROKER || 'mqtt://localhost:1883');

mqttClient.on('connect', () => {
  console.log('✅ Connected to MQTT Broker');
  mqttClient.subscribe('iot/+/telemetry');
  mqttClient.subscribe('iot/+/location');
});

mqttClient.on('message', async (topic, message) => {
  try {
    const data = JSON.parse(message.toString());
    const parts = topic.split('/');
    const deviceId = parts[1];
    
    if (parts[2] === 'telemetry') {
      // Update digital twin
      const twin = await DigitalTwin.findOneAndUpdate(
        { deviceId },
        { 
          state: data,
          lastSyncAt: new Date(),
          $push: { stateHistory: { ...data, timestamp: new Date() } }
        },
        { upsert: true, new: true }
      );
      
      // Run predictions
      const prediction = await predictiveAnalytics.predictFailure(deviceId, data);
      if (prediction && prediction.failureProbability > 0.7) {
        // Send alert
        mqttClient.publish(`iot/${deviceId}/alert`, JSON.stringify({
          type: 'predictive_maintenance',
          prediction,
          timestamp: new Date()
        }));
      }
    } else if (parts[2] === 'location') {
      // Check geo-fencing
      const result = geoFenceManager.checkLocation(deviceId, data);
      if (result && result.triggered) {
        mqttClient.publish(`iot/${deviceId}/geofence_alert`, JSON.stringify(result));
      }
    }
  } catch (error) {
    console.error('MQTT message error:', error);
  }
});

// Start server
const PORT = process.env.PORT || 5006;
app.listen(PORT, () => {
  console.log(`
╔════════════════════════════════════════════╗
║   📡 Rizz IoT Platform - Enhanced          ║
║   Running on port ${PORT}                      ║
║                                            ║
║   Features:                                ║
║   - Digital Twins                          ║
║   - Predictive Maintenance (ML)            ║
║   - Anomaly Detection                      ║
║   - Geo-fencing                            ║
║   - Edge Computing                         ║
║   - Real-time Analytics                    ║
╚════════════════════════════════════════════╝
  `);
});

module.exports = { app, mqttClient, predictiveAnalytics, geoFenceManager, edgeComputingManager };
