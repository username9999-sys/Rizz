/**
 * Rizz E-commerce - Enhanced Features
 * Advanced features: Reviews, Recommendations, Coupons, Inventory, Analytics
 */

const express = require('express');
const router = express.Router();
const mongoose = require('mongoose');

// ===== REVIEW & RATING SYSTEM =====
const ReviewSchema = new mongoose.Schema({
  product: { type: mongoose.Schema.Types.ObjectId, ref: 'Product', required: true },
  customer: { type: mongoose.Schema.Types.ObjectId, ref: 'Customer', required: true },
  rating: { type: Number, min: 1, max: 5, required: true },
  title: String,
  content: String,
  pros: [String],
  cons: [String],
  verified: { type: Boolean, default: false },
  helpful: { type: Number, default: 0 },
  images: [String],
  status: { type: String, enum: ['pending', 'approved', 'rejected'], default: 'pending' }
}, { timestamps: true });

ReviewSchema.index({ product: 1, createdAt: -1 });
ReviewSchema.index({ customer: 1 });

const Review = mongoose.model('Review', ReviewSchema);

// Calculate average rating
ReviewSchema.statics.calculateAverage = async function(productId) {
  const result = await this.aggregate([
    { $match: { product: productId, status: 'approved' } },
    { $group: { _id: '$product', average: { $avg: '$rating' }, count: { $sum: 1 } } }
  ]);
  return result[0] || { average: 0, count: 0 };
};

// ===== RECOMMENDATION ENGINE =====
class RecommendationEngine {
  constructor() {
    this.userPreferences = new Map();
    this.productSimilarity = new Map();
  }

  async getRecommendations(userId, limit = 10) {
    // Get user's purchase history
    const orders = await mongoose.model('Order').find({ 'customer.id': userId })
      .populate('items.product');
    
    // Get viewed products
    const viewedProducts = await this.getViewedProducts(userId);
    
    // Calculate preferences
    const preferences = this.calculatePreferences(orders, viewedProducts);
    
    // Get recommendations
    const recommendations = await this.findSimilarProducts(preferences, limit);
    
    return recommendations;
  }

  calculatePreferences(orders, viewedProducts) {
    const preferences = {
      categories: {},
      priceRange: { min: 0, max: 0 },
      brands: {}
    };
    
    // Analyze orders
    orders.forEach(order => {
      order.items.forEach(item => {
        if (item.product) {
          preferences.categories[item.product.category] = 
            (preferences.categories[item.product.category] || 0) + 1;
          preferences.brands[item.product.brand] = 
            (preferences.brands[item.product.brand] || 0) + 1;
        }
      });
    });
    
    return preferences;
  }

  async findSimilarProducts(preferences, limit) {
    // Find products matching preferences
    const Product = mongoose.model('Product');
    
    const query = {
      status: 'active',
      $or: [
        { category: { $in: Object.keys(preferences.categories) } },
        { brand: { $in: Object.keys(preferences.brands) } }
      ]
    };
    
    return await Product.find(query)
      .sort({ views: -1 })
      .limit(limit);
  }

  async getViewedProducts(userId) {
    // Implement viewed products tracking
    return [];
  }
}

const recommendationEngine = new RecommendationEngine();

// ===== COUPON & DISCOUNT SYSTEM =====
const CouponSchema = new mongoose.Schema({
  code: { type: String, unique: true, required: true },
  description: String,
  type: { type: String, enum: ['percentage', 'fixed', 'free_shipping'], required: true },
  value: { type: Number, required: true },
  minOrderValue: Number,
  maxDiscount: Number,
  usageLimit: Number,
  usedCount: { type: Number, default: 0 },
  validFrom: Date,
  validUntil: Date,
  applicableProducts: [mongoose.Schema.Types.ObjectId],
  applicableCategories: [String],
  firstTimeOnly: { type: Boolean, default: false },
  active: { type: Boolean, default: true }
});

const Coupon = mongoose.model('Coupon', CouponSchema);

Coupon.methods.isValid = function() {
  const now = new Date();
  return this.active && 
         (!this.validFrom || now >= this.validFrom) &&
         (!this.validUntil || now <= this.validUntil) &&
         (this.usageLimit === undefined || this.usedCount < this.usageLimit);
};

Coupon.methods.calculateDiscount = function(orderValue, items) {
  if (!this.isValid()) return 0;
  
  let discount = 0;
  
  if (this.type === 'percentage') {
    discount = (orderValue * this.value) / 100;
    if (this.maxDiscount) discount = Math.min(discount, this.maxDiscount);
  } else if (this.type === 'fixed') {
    discount = this.value;
  } else if (this.type === 'free_shipping') {
    discount = orderValue * 0.1; // Assume 10% shipping cost
  }
  
  return Math.min(discount, orderValue);
};

// ===== INVENTORY MANAGEMENT =====
const InventorySchema = new mongoose.Schema({
  product: { type: mongoose.Schema.Types.ObjectId, ref: 'Product', unique: true, required: true },
  quantity: { type: Number, default: 0, min: 0 },
  reserved: { type: Number, default: 0 },
  available: { type: Number, default: 0 },
  reorderPoint: Number,
  reorderQuantity: Number,
  warehouse: String,
  lastStockCheck: Date,
  stockHistory: [{
    type: { type: String, enum: ['restock', 'sale', 'return', 'adjustment'] },
    quantity: Number,
    reason: String,
    timestamp: { type: Date, default: Date.now }
  }]
});

InventorySchema.pre('save', function(next) {
  this.available = this.quantity - this.reserved;
  next();
});

const Inventory = mongoose.model('Inventory', InventorySchema);

// Low stock alert
Inventory.methods.checkLowStock = function() {
  return this.available <= this.reorderPoint;
};

// Reserve stock for order
Inventory.statics.reserveStock = async function(productId, quantity) {
  const inventory = await this.findOne({ product: productId });
  
  if (!inventory || inventory.available < quantity) {
    throw new Error('Insufficient stock');
  }
  
  inventory.reserved += quantity;
  inventory.stockHistory.push({
    type: 'sale',
    quantity: -quantity,
    reason: 'Reserved for order'
  });
  
  await inventory.save();
  return inventory;
};

// Release reserved stock
Inventory.statics.releaseStock = async function(productId, quantity) {
  const inventory = await this.findOne({ product: productId });
  
  if (!inventory) return null;
  
  inventory.reserved = Math.max(0, inventory.reserved - quantity);
  await inventory.save();
  return inventory;
};

// Confirm stock deduction
Inventory.statics.deductStock = async function(productId, quantity) {
  const inventory = await this.findOne({ product: productId });
  
  if (!inventory || inventory.available < quantity) {
    throw new Error('Insufficient stock');
  }
  
  inventory.quantity -= quantity;
  inventory.reserved = Math.max(0, inventory.reserved - quantity);
  inventory.stockHistory.push({
    type: 'sale',
    quantity: -quantity,
    reason: 'Order fulfilled'
  });
  
  await inventory.save();
  return inventory;
};

// ===== ANALYTICS & REPORTING =====
class EcommerceAnalytics {
  async getSalesReport(startDate, endDate) {
    const Order = mongoose.model('Order');
    
    const report = await Order.aggregate([
      {
        $match: {
          createdAt: { $gte: startDate, $lte: endDate },
          'payment.status': 'paid'
        }
      },
      {
        $group: {
          _id: { $dateToString: { format: '%Y-%m-%d', date: '$createdAt' } },
          totalSales: { $sum: '$pricing.total' },
          orderCount: { $sum: 1 },
          averageOrderValue: { $avg: '$pricing.total' }
        }
      },
      { $sort: { _id: 1 } }
    ]);
    
    return report;
  }

  async getProductPerformance(startDate, endDate) {
    const Order = mongoose.model('Order');
    
    const products = await Order.aggregate([
      {
        $match: {
          createdAt: { $gte: startDate, $lte: endDate },
          'payment.status': 'paid'
        }
      },
      { $unwind: '$items' },
      {
        $group: {
          _id: '$items.product',
          quantitySold: { $sum: '$items.quantity' },
          revenue: { $sum: '$items.total' }
        }
      },
      { $sort: { quantitySold: -1 } },
      { $limit: 20 }
    ]);
    
    return products;
  }

  async getCustomerInsights() {
    const Customer = mongoose.model('Customer');
    const Order = mongoose.model('Order');
    
    const insights = await Customer.aggregate([
      {
        $lookup: {
          from: 'orders',
          localField: '_id',
          foreignField: 'customer.id',
          as: 'orders'
        }
      },
      {
        $addFields: {
          totalOrders: { $size: '$orders' },
          totalSpent: { $sum: '$orders.pricing.total' },
          averageOrderValue: { $avg: '$orders.pricing.total' }
        }
      },
      {
        $project: {
          email: 1,
          name: 1,
          totalOrders: 1,
          totalSpent: 1,
          averageOrderValue: 1,
          lastOrderDate: { $arrayElemAt: ['$orders.createdAt', -1] }
        }
      },
      { $sort: { totalSpent: -1 } },
      { $limit: 100 }
    ]);
    
    return insights;
  }

  async getConversionFunnel() {
    // Implement conversion funnel analysis
    return {
      views: 0,
      addToCart: 0,
      initiatedCheckout: 0,
      completedPurchase: 0,
      conversionRate: 0
    };
  }
}

const analytics = new EcommerceAnalytics();

// ===== API ROUTES =====

// Get product reviews
router.get('/products/:id/reviews', async (req, res) => {
  try {
    const { page = 1, limit = 20, rating, verified } = req.query;
    const query = { product: req.params.id, status: 'approved' };
    
    if (rating) query.rating = parseInt(rating);
    if (verified === 'true') query.verified = true;
    
    const reviews = await Review.find(query)
      .populate('customer', 'name avatar')
      .sort('-createdAt')
      .limit(limit * 1)
      .skip((page - 1) * limit);
    
    const total = await Review.countDocuments(query);
    const average = await Review.calculateAverage(req.params.id);
    
    res.json({ reviews, average, totalPages: Math.ceil(total / limit), currentPage: page });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Add product review
router.post('/products/:id/reviews', async (req, res) => {
  try {
    const { rating, title, content, pros, cons, images } = req.body;
    
    const review = new Review({
      product: req.params.id,
      customer: req.user.id,
      rating,
      title,
      content,
      pros,
      cons,
      images,
      verified: await checkVerifiedPurchase(req.user.id, req.params.id)
    });
    
    await review.save();
    
    res.status(201).json({ review, message: 'Review submitted' });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Mark review as helpful
router.post('/reviews/:id/helpful', async (req, res) => {
  try {
    const review = await Review.findById(req.params.id);
    if (!review) return res.status(404).json({ error: 'Review not found' });
    
    review.helpful += 1;
    await review.save();
    
    res.json({ message: 'Review marked as helpful', helpful: review.helpful });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Get recommendations
router.get('/recommendations', async (req, res) => {
  try {
    const { limit = 10 } = req.query;
    const recommendations = await recommendationEngine.getRecommendations(req.user.id, limit);
    res.json({ recommendations });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Validate coupon
router.post('/coupons/validate', async (req, res) => {
  try {
    const { code, orderValue, items } = req.body;
    
    const coupon = await Coupon.findOne({ code });
    if (!coupon) return res.status(404).json({ error: 'Coupon not found' });
    
    if (!coupon.isValid()) {
      return res.status(400).json({ error: 'Coupon is not valid' });
    }
    
    const discount = coupon.calculateDiscount(orderValue, items);
    
    res.json({
      valid: true,
      code: coupon.code,
      description: coupon.description,
      type: coupon.type,
      discount
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Inventory management
router.get('/inventory', async (req, res) => {
  try {
    const { lowStock, warehouse } = req.query;
    const query = {};
    
    if (lowStock === 'true') {
      const inventories = await Inventory.find(query).populate('product');
      const lowStockItems = inventories.filter(inv => inv.checkLowStock());
      return res.json({ inventory: lowStockItems });
    }
    
    if (warehouse) query.warehouse = warehouse;
    
    const inventory = await Inventory.find(query).populate('product');
    res.json({ inventory });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Restock inventory
router.post('/inventory/:id/restock', async (req, res) => {
  try {
    const { quantity, reason } = req.body;
    
    const inventory = await Inventory.findById(req.params.id);
    if (!inventory) return res.status(404).json({ error: 'Inventory not found' });
    
    inventory.quantity += quantity;
    inventory.stockHistory.push({
      type: 'restock',
      quantity,
      reason: reason || 'Manual restock'
    });
    
    await inventory.save();
    
    res.json({ inventory, message: 'Stock updated' });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Analytics endpoints
router.get('/analytics/sales', async (req, res) => {
  try {
    const { startDate, endDate } = req.query;
    const report = await analytics.getSalesReport(new Date(startDate), new Date(endDate));
    res.json({ report });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

router.get('/analytics/products', async (req, res) => {
  try {
    const { startDate, endDate } = req.query;
    const performance = await analytics.getProductPerformance(new Date(startDate), new Date(endDate));
    res.json({ performance });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

router.get('/analytics/customers', async (req, res) => {
  try {
    const insights = await analytics.getCustomerInsights();
    res.json({ insights });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Helper functions
async function checkVerifiedPurchase(customerId, productId) {
  const Order = mongoose.model('Order');
  const order = await Order.findOne({
    'customer.id': customerId,
    'items.product': productId,
    'payment.status': 'paid'
  });
  return !!order;
}

module.exports = router;
