/**
 * Rizz E-commerce Platform - Main API Server
 * Microservices-ready architecture
 */

const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const { createServer } = require('http');
const { Server } = require('socket.io');
require('dotenv').config();

const app = express();
const httpServer = createServer(app);
const io = new Server(httpServer, { cors: { origin: '*' } });

// ===== Middleware =====
app.use(helmet());
app.use(cors());
app.use(compression());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 100,
  message: { error: 'Too many requests, please try again later' }
});
app.use('/api/', limiter);

// ===== Database Connection =====
mongoose.connect(process.env.MONGODB_URI || 'mongodb://localhost:27017/rizz_ecommerce')
  .then(() => console.log('✅ MongoDB Connected'))
  .catch(err => console.error('❌ MongoDB Error:', err));

// ===== Models =====
const ProductSchema = new mongoose.Schema({
  name: { type: String, required: true },
  slug: { type: String, unique: true },
  description: String,
  price: { type: Number, required: true },
  comparePrice: Number,
  cost: Number,
  sku: String,
  barcode: String,
  inventory: { type: Number, default: 0 },
  category: String,
  tags: [String],
  images: [String],
  variants: [{
    name: String,
    options: [String],
    price: Number,
    sku: String,
    inventory: Number
  }],
  status: { type: String, enum: ['draft', 'active', 'archived'], default: 'active' },
  publishedAt: Date,
  vendor: String,
  productType: String,
  weight: Number,
  dimensions: { length: Number, width: Number, height: Number },
  seo: { title: String, description: String },
  metadata: mongoose.Schema.Types.Mixed
}, { timestamps: true });

const OrderSchema = new mongoose.Schema({
  orderNumber: { type: String, unique: true },
  customer: {
    id: mongoose.Schema.Types.ObjectId,
    email: String,
    name: String,
    phone: String
  },
  items: [{
    product: mongoose.Schema.Types.ObjectId,
    variant: String,
    quantity: Number,
    price: Number,
    total: Number
  }],
  pricing: {
    subtotal: Number,
    shipping: Number,
    tax: Number,
    discount: Number,
    total: Number
  },
  shipping: {
    address: {
      street: String,
      city: String,
      state: String,
      zip: String,
      country: String
    },
    method: String,
    tracking: String,
    carrier: String
  },
  payment: {
    method: String,
    status: { type: String, enum: ['pending', 'paid', 'failed', 'refunded'] },
    transactionId: String,
    paidAt: Date
  },
  status: {
    type: String,
    enum: ['pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded'],
    default: 'pending'
  },
  notes: String,
  metadata: mongoose.Schema.Types.Mixed
}, { timestamps: true });

const CustomerSchema = new mongoose.Schema({
  email: { type: String, unique: true, required: true },
  password: String,
  name: String,
  phone: String,
  avatar: String,
  addresses: [{
    label: String,
    street: String,
    city: String,
    state: String,
    zip: String,
    country: String,
    isDefault: Boolean
  }],
  orders: [{ type: mongoose.Schema.Types.ObjectId, ref: 'Order' }],
  wishlist: [mongoose.Schema.Types.ObjectId],
  cart: {
    items: [{
      product: mongoose.Schema.Types.ObjectId,
      quantity: Number,
      variant: String
    }],
    updatedAt: Date
  },
  loyaltyPoints: { type: Number, default: 0 },
  tier: { type: String, enum: ['bronze', 'silver', 'gold', 'platinum'], default: 'bronze' },
  marketing: {
    emailOptIn: Boolean,
    smsOptIn: Boolean
  },
  metadata: mongoose.Schema.Types.Mixed
}, { timestamps: true });

const ReviewSchema = new mongoose.Schema({
  product: { type: mongoose.Schema.Types.ObjectId, ref: 'Product', required: true },
  customer: { type: mongoose.Schema.Types.ObjectId, ref: 'Customer', required: true },
  rating: { type: Number, min: 1, max: 5, required: true },
  title: String,
  content: String,
  images: [String],
  verified: { type: Boolean, default: false },
  helpful: { type: Number, default: 0 },
  status: { type: String, enum: ['pending', 'approved', 'rejected'], default: 'pending' }
}, { timestamps: true });

const Product = mongoose.model('Product', ProductSchema);
const Order = mongoose.model('Order', OrderSchema);
const Customer = mongoose.model('Customer', CustomerSchema);
const Review = mongoose.model('Review', ReviewSchema);

// ===== Routes =====

// Products API
app.get('/api/products', async (req, res) => {
  try {
    const { page = 1, limit = 20, category, search, sort = '-createdAt' } = req.query;
    const query = { status: 'active' };
    
    if (category) query.category = category;
    if (search) {
      query.$text = { $search: search };
    }
    
    const products = await Product.find(query)
      .sort(sort)
      .limit(limit * 1)
      .skip((page - 1) * limit);
    
    const count = await Product.countDocuments(query);
    
    res.json({ products, totalPages: Math.ceil(count / limit), currentPage: page, total: count });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/products/:id', async (req, res) => {
  try {
    const product = await Product.findById(req.params.id);
    if (!product) return res.status(404).json({ error: 'Product not found' });
    res.json(product);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Orders API
app.post('/api/orders', async (req, res) => {
  try {
    const { customer, items, shipping, payment } = req.body;
    
    // Calculate pricing
    let subtotal = 0;
    for (const item of items) {
      subtotal += item.price * item.quantity;
    }
    
    const shippingCost = shipping.method === 'express' ? 15 : 5;
    const tax = subtotal * 0.1;
    const total = subtotal + shippingCost + tax;
    
    // Generate order number
    const orderNumber = 'ORD-' + Date.now() + '-' + Math.random().toString(36).substr(2, 6).toUpperCase();
    
    const order = new Order({
      orderNumber,
      customer,
      items,
      shipping,
      payment: { ...payment, status: 'pending' },
      pricing: { subtotal, shipping: shippingCost, tax, discount: 0, total }
    });
    
    await order.save();
    
    // Emit real-time notification
    io.emit('order_created', { orderNumber, total });
    
    res.status(201).json({ message: 'Order created', order });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/orders/:id', async (req, res) => {
  try {
    const order = await Order.findById(req.params.id);
    if (!order) return res.status(404).json({ error: 'Order not found' });
    res.json(order);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Customers API
app.post('/api/customers/register', async (req, res) => {
  try {
    const { email, password, name } = req.body;
    
    const existingCustomer = await Customer.findOne({ email });
    if (existingCustomer) return res.status(400).json({ error: 'Email already registered' });
    
    const customer = new Customer({ email, password, name });
    await customer.save();
    
    res.status(201).json({ message: 'Customer registered', customer });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/customers/login', async (req, res) => {
  try {
    const { email, password } = req.body;
    const customer = await Customer.findOne({ email });
    
    if (!customer || customer.password !== password) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }
    
    const token = require('jsonwebtoken').sign(
      { id: customer._id, email: customer.email },
      process.env.JWT_SECRET || 'secret',
      { expiresIn: '7d' }
    );
    
    res.json({ token, customer });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Reviews API
app.post('/api/reviews', async (req, res) => {
  try {
    const { product, customer, rating, title, content } = req.body;
    const review = new Review({ product, customer, rating, title, content });
    await review.save();
    res.status(201).json({ message: 'Review submitted', review });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/products/:id/reviews', async (req, res) => {
  try {
    const reviews = await Review.find({ product: req.params.id, status: 'approved' })
      .populate('customer', 'name avatar')
      .sort('-createdAt');
    res.json(reviews);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Analytics API
app.get('/api/analytics/summary', async (req, res) => {
  try {
    const totalProducts = await Product.countDocuments();
    const totalOrders = await Order.countDocuments();
    const totalCustomers = await Customer.countDocuments();
    
    const revenue = await Order.aggregate([
      { $match: { 'payment.status': 'paid' } },
      { $group: { _id: null, total: { $sum: '$pricing.total' } } }
    ]);
    
    const recentOrders = await Order.find().sort('-createdAt').limit(10);
    
    res.json({
      totalProducts,
      totalOrders,
      totalCustomers,
      revenue: revenue[0]?.total || 0,
      recentOrders
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// ===== Socket.io Real-time Events =====
io.on('connection', (socket) => {
  console.log(`Client connected: ${socket.id}`);
  
  socket.on('join_order_updates', (orderNumber) => {
    socket.join(`order_${orderNumber}`);
  });
  
  socket.on('track_order', async (orderNumber) => {
    const order = await Order.findOne({ orderNumber });
    if (order) {
      socket.emit('order_status', { orderNumber, status: order.status });
    }
  });
  
  socket.on('disconnect', () => {
    console.log(`Client disconnected: ${socket.id}`);
  });
});

// ===== Error Handling =====
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Something went wrong!' });
});

// ===== Start Server =====
const PORT = process.env.PORT || 5001;
httpServer.listen(PORT, () => {
  console.log(`
╔════════════════════════════════════════════╗
║   🛒 Rizz E-commerce Platform              ║
║   Running on port ${PORT}                      ║
║                                            ║
║   Endpoints:                               ║
║   - /api/products     - Products catalog   ║
║   - /api/orders       - Order management   ║
║   - /api/customers    - Customer accounts  ║
║   - /api/reviews      - Product reviews    ║
║   - /api/analytics    - Analytics data     ║
╚════════════════════════════════════════════╝
  `);
});

module.exports = { app, io };
